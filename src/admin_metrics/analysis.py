"""Explicit nulls, bounded history, cumulative-counter deltas and stateful incidents."""
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
import math
from statistics import median
from zoneinfo import ZoneInfo

from .storage import sha, encoded
from .contracts import endpoint_parts
from .rules import DEFAULT_RULES, validate_rules
from .health import outcome, collection_health

FIELDS = {'invocations': 'calls', 'errors': 'errors', 'rejections': 'rejections',
          'averageResponse': 'mean_ms', 'averageTps': 'average_tps', 'peakTps': 'peak_tps'}
MODEL_VERSION = 3
SUPPORTED_MODEL_VERSIONS = frozenset({1, 2, 3})


def stamp(value):
    try:
        result = datetime.fromisoformat(value.replace('Z', '+00:00'))
        return result if result.tzinfo else None
    except (ValueError, AttributeError, TypeError):
        return None


def integer(value):
    return value if type(value) is int and 0 <= value <= 9223372036854775807 else None


def ratio(numerator, denominator):
    if numerator is None or denominator is None or denominator <= 0 or numerator > denominator:
        return None
    return 100 * numerator / denominator


def normalize(report, run_id, rules=None):
    rules = rules or DEFAULT_RULES
    rows = []
    acquired = stamp(report['observed_at'])

    def day_for(item):
        if isinstance(item, dict) and 'http_date' in item:
            value = item.get('http_date')
        else:
            value = report.get('http_date')
        basis = 'HTTP Date / America_Sao_Paulo'
        try:
            reference = parsedate_to_datetime(value)
        except (ValueError, TypeError, OverflowError):
            reference = acquired
            basis = 'observed_at / America_Sao_Paulo'
        if reference is None or reference.tzinfo is None:
            reference = acquired
            basis = 'observed_at / America_Sao_Paulo'
        return reference.astimezone(ZoneInfo('America/Sao_Paulo')).date().isoformat(), basis

    for item in report['rows']:
        day, day_basis = day_for(item)
        raw = item['record']
        flags = []
        endpoint = raw['endpoint']
        parsed = endpoint_parts(endpoint)
        if parsed is None:
            continue
        path = parsed.path if parsed.path else endpoint
        family = path.split('/open-banking/', 1)[-1].split('/')[0]
        row = {'run_id': run_id, 'observed_at': report['observed_at'], 'day': day,
               'day_basis': day_basis, 'reporter_id': report['id'], 'reporter': report['label'],
               'entity_id': sha(encoded([report['id'], endpoint]))[:24], 'endpoint': endpoint, 'path': path,
               'family': family, 'source_sha': item['source_sha'], 'json_path': item['json_path'],
               'request_time': raw.get('requestTime'), 'source_complete': report['complete'], 'previous': {}}
        reported = stamp(raw.get('requestTime'))
        row['clock_offset_seconds'] = (acquired - reported).total_seconds() if reported else None
        if not reported:
            flags.append('request_time_invalid')
        elif abs(row['clock_offset_seconds']) > rules['clock_skew_seconds']:
            flags.append('reported_clock_skew')
        lengths = []
        for source, target in FIELDS.items():
            values = raw.get(source)
            if not isinstance(values, dict):
                values = {}
            row[target] = integer(values.get('currentDay'))
            if row[target] is None:
                flags.append(target + '_invalid')
            previous = values.get('previousDays')
            if not isinstance(previous, list) or len(previous) > rules['reported_history_days']:
                flags.append(target + '_history_invalid')
                previous = []
            lengths.append(len(previous))
            row['previous'][target] = [integer(v) for v in previous]
            if any(integer(v) is None for v in previous):
                flags.append(target + '_history_value_invalid')
        if len(set(lengths)) > 1:
            flags.append('history_lengths_differ')
        availability = raw.get('availability') if isinstance(raw.get('availability'), dict) else {}
        uptime = availability.get('uptime') if isinstance(availability.get('uptime'), dict) else {}
        downtime = availability.get('downtime') if isinstance(availability.get('downtime'), dict) else {}
        for source, target in [('uptimeRate', 'uptime'), ('generalUptimeRate', 'general_uptime')]:
            raw_uptime = uptime.get(source)
            try:
                if isinstance(raw_uptime, bool):
                    raise TypeError('boolean_uptime')
                value = float(raw_uptime)
                row[target] = value if math.isfinite(value) and 0 <= value <= 1 else None
            except (ValueError, TypeError):
                row[target] = None
            if row[target] is None:
                flags.append(target + '_invalid')
        for source, target in [('partialDowntime', 'downtime_seconds'), ('generalDowntime', 'general_downtime'), ('scheduledOutage', 'scheduled_outage')]:
            row[target] = integer(downtime.get(source))
        if row['uptime'] == 1 and (row['downtime_seconds'] or 0) > 0:
            flags.append('uptime_downtime_conflict')
        if row['calls'] == 0 and row['uptime'] == 0:
            flags.append('zero_uptime_without_traffic')
        if row['average_tps'] is not None and row['peak_tps'] is not None and row['average_tps'] > row['peak_tps']:
            flags.append('average_tps_above_peak')
        row['error_pct'] = ratio(row['errors'], row['calls'])
        row['rejection_pct'] = ratio(row['rejections'], row['calls'])
        if row['calls'] is not None and any(row[k] is not None and row[k] > row['calls'] for k in ('errors', 'rejections')):
            flags.append('counter_above_invocations')
        if row['calls'] and row['mean_ms'] == 0:
            flags.append('zero_mean_with_traffic')
        previous_means = [x for x in row['previous']['mean_ms'] if x is not None and x > 0]
        row['baseline_mean_ms'] = median(previous_means) if len(previous_means) >= rules['baseline_minimum_days'] else None
        recurrent = 0
        for calls, errors in zip(row['previous']['calls'], row['previous']['errors']):
            value = ratio(errors, calls)
            if calls is not None and calls >= rules['minimum_calls'] and value is not None and value >= rules['error_attention_pct']:
                recurrent += 1
        row['recurrent_days'] = recurrent
        if item.get('ambiguous'):
            flags.append('conflicting_endpoint')
        row['quality'] = sorted(set(flags))
        row['fingerprint'] = sha(encoded({k: row[k] for k in (*FIELDS.values(), 'uptime', 'downtime_seconds', 'previous')}))
        rows.append(row)
    return rows


def counter_state(current, previous, metric):
    """A discontinuity in rejections must not invalidate a valid error counter."""
    if not previous:
        return 'first_observation'
    if stamp(current['observed_at']) <= stamp(previous['observed_at']):
        return 'observation_time_not_increasing'
    if current['day'] != previous['day']:
        return 'day_changed'
    if not current['source_complete'] or not previous['source_complete']:
        return 'incomplete_source'
    if any(r[k] is None for r in (current, previous) for k in ('calls', metric)):
        return 'invalid_counter'
    if any(r[metric] > r['calls'] for r in (current, previous)):
        return 'invalid_counter'
    calls = current['calls'] - previous['calls']
    value = current[metric] - previous[metric]
    if calls < 0 or value < 0:
        return 'counter_reset_or_revision'
    if value > calls:
        return 'inconsistent_delta'
    return 'valid'


def interval(current, previous):
    result = {'interval_calls': None, 'interval_errors': None, 'interval_rejections': None,
              'interval_error_pct': None, 'interval_rejection_pct': None, 'interval_state': 'first_observation',
              'interval_from': previous['observed_at'] if previous else None, 'interval_to': current['observed_at'],
              'interval_seconds': None,
              'interval_error_state': counter_state(current, previous, 'errors'),
              'interval_rejection_state': counter_state(current, previous, 'rejections')}
    if not previous:
        return result
    result['interval_seconds'] = (stamp(current['observed_at']) - stamp(previous['observed_at'])).total_seconds()
    if result['interval_seconds'] <= 0:
        result['interval_state'] = 'observation_time_not_increasing'
        return result
    if previous['day'] != current['day']:
        result['interval_state'] = 'day_changed'
        return result
    if not previous['source_complete'] or not current['source_complete']:
        result['interval_state'] = 'incomplete_source'
        return result
    if previous['fingerprint'] == current['fingerprint']:
        result['interval_state'] = 'unchanged_report'
        return result
    if any(current[k] is None or previous[k] is None for k in ('calls', 'errors', 'rejections')):
        result['interval_state'] = 'invalid_counter'
        return result
    if any(row[k] > row['calls'] for row in (current, previous) for k in ('errors', 'rejections')):
        result['interval_state'] = 'invalid_counter'
        return result
    delta = {k: current[k] - previous[k] for k in ('calls', 'errors', 'rejections')}
    if min(delta.values()) < 0:
        result['interval_state'] = 'counter_reset_or_revision'
        return result
    if delta['errors'] > delta['calls'] or delta['rejections'] > delta['calls']:
        result['interval_state'] = 'inconsistent_delta'
        return result
    result.update(interval_state='valid', interval_calls=delta['calls'], interval_errors=delta['errors'],
                  interval_rejections=delta['rejections'], interval_error_pct=ratio(delta['errors'], delta['calls']),
                  interval_rejection_pct=ratio(delta['rejections'], delta['calls']))
    return result


def evaluable_rules(row, rules):
    if (not row['source_complete'] or (row['calls'] or 0) < rules['minimum_calls']
            or row.get('interval_state') == 'observation_time_not_increasing'):
        return set()
    eligible = set()
    if row['mean_ms'] is not None and row['mean_ms'] > 0:
        eligible.add('mean_latency')
        if row['baseline_mean_ms']:
            eligible.add('latency_regression')
    # Counter discontinuities suspend counter-based rules, not valid latency metrics.
    blocked = {'counter_reset_or_revision', 'inconsistent_delta', 'invalid_counter'}
    for rule, metric, counter in [('error_rate', 'error_pct', 'error'), ('rejection_rate', 'rejection_pct', 'rejection')]:
        if row[metric] is not None and row.get('interval_' + counter + '_state', row.get('interval_state')) not in blocked:
            eligible.add(rule)
    return eligible


def signals(row, rules):
    calls = row['calls'] or 0
    eligible = evaluable_rules(row, rules)
    result = []
    if calls >= rules['minimum_calls']:
        if 'error_rate' in eligible and row['error_pct'] >= rules['error_attention_pct']:
            level = 'critical' if calls >= rules['critical_minimum_calls'] and row['error_pct'] >= rules['error_critical_pct'] else 'attention'
            result.append(('error_rate', level, f"{row['errors']} erros / {calls} chamadas ({row['error_pct']:.2f}%)"))
        if 'rejection_rate' in eligible and row['rejection_pct'] >= rules['rejection_attention_pct']:
            result.append(('rejection_rate', 'attention', f"{row['rejections']} rejeições / {calls} chamadas; causa não identificável"))
        if 'mean_latency' in eligible and row['mean_ms'] >= rules['latency_attention_ms']:
            result.append(('mean_latency', 'critical' if row['mean_ms'] >= rules['latency_critical_ms'] else 'attention', f"Média declarada {row['mean_ms']} ms; não é p95"))
        if 'latency_regression' in eligible and row['mean_ms'] >= rules['regression_multiplier'] * row['baseline_mean_ms']:
            result.append(('latency_regression', 'attention', f"Média {row['mean_ms']} ms / baseline {row['baseline_mean_ms']} ms"))
    return result


def update_incidents(state, run, rows, rules):
    identities = {r['entity_id']: r['reporter_id'] for r in (*state['observations'], *state['latest_rows'], *rows)}
    names = {r['id']: r['label'] for r in run['reports']}
    old_names = {r['label']: r['id'] for cycle in (*state['runs'], run) for r in cycle['reports']}
    for incident in state['incidents']:
        reporter_id = (incident.get('reporter_id') or identities.get(incident['entity_id'])
                       or (incident['entity_id'][7:] if incident['entity_id'].startswith('source:') else None)
                       or old_names.get(incident['reporter']))
        if reporter_id:
            incident['reporter_id'] = reporter_id
            incident['reporter'] = names.get(reporter_id, incident['reporter'])
    existing = {(i['entity_id'], i['rule']): i for i in state['incidents'] if i['status'] != 'resolved'}
    detected = {}
    eligible = set()
    for report in run['reports']:
        key = 'source:' + report['id']
        eligible.add((key, 'collection'))
        if report['status'] != 200 or not report['complete'] or not report['records']:
            detected[(key, 'collection')] = ('attention', '; '.join(report['issues']) or 'Reporte incompleto', report['label'], None, report['id'])
    for row in rows:
        # Absence of a signal is recovery only when that rule was evaluable.
        eligible.update((row['entity_id'], rule) for rule in evaluable_rules(row, rules))
        for rule, severity, evidence in signals(row, rules):
            detected[(row['entity_id'], rule)] = (severity, evidence, row['reporter'], row['endpoint'], row['reporter_id'])
    # Apply each observation once, including same-cycle multiple rule detections.
    for (entity, rule), (severity, evidence, label, endpoint, reporter_id) in detected.items():
        key = (entity, rule)
        incident = existing.get(key)
        if incident is None:
            incident = {'id': sha(encoded([entity, rule, run['run_id']]))[:24], 'entity_id': entity, 'rule': rule, 'reporter': label, 'reporter_id': reporter_id, 'endpoint': endpoint,
                        'opened_at': run['observed_at'], 'opened_run': run['run_id'], 'samples': 0,
                        'consecutive_samples': 0, 'recovery_samples': 0, 'status': 'open'}
            state['incidents'].append(incident)
            existing[key] = incident
        streak = incident['consecutive_samples'] + 1
        incident.update(last_seen=run['observed_at'], evaluated_at=run['observed_at'], evidence=evidence,
                        samples=incident['samples'] + 1, consecutive_samples=streak,
                        recovery_samples=0, status='open', severity='critical' if rule == 'collection' and streak >= rules['confirmation_samples'] else severity,
                        reporter=label, reporter_id=reporter_id)
        incident['confirmed'] = streak >= rules['confirmation_samples']
    for incident in existing.values():
        key = (incident['entity_id'], incident['rule'])
        if key not in detected:
            incident['consecutive_samples'] = 0
        if key in eligible and key not in detected:
            incident['recovery_samples'] += 1
            incident.update(status='recovering', evaluated_at=run['observed_at'])
            if incident['recovery_samples'] >= rules['recovery_samples']:
                incident.update(status='resolved', resolved_at=run['observed_at'])
        elif key not in detected:
            # Unknown/absent/partial samples break the recovery streak.
            incident['recovery_samples'] = 0


def apply(state, reports, rules, observed_at, run_id):
    validate_rules(rules)
    if any(r['run_id'] == run_id for r in state['runs']):
        raise ValueError('Execução já aplicada')
    run = {'run_id': run_id, 'observed_at': observed_at, 'reports': [], 'rules': dict(rules), 'model_version': MODEL_VERSION}
    previous = {r['entity_id']: r for r in state['observations']}
    current = []
    latest = {r['entity_id']: r for r in state['latest_rows']}
    for report in reports:
        valid_rows = [item for item in report['rows'] if isinstance(item.get('record'), dict)
                      and endpoint_parts(item['record'].get('endpoint')) is not None]
        if len(valid_rows) != len(report['rows']):
            report = {**report, 'rows': valid_rows, 'complete': False, 'coverage_reconciled': False,
                      'coverage': 'invalid_records',
                      'issues': sorted(set(report['issues']) | {'invalid_endpoint_record'})}
        normalized = normalize(report, run_id, rules)
        if len({row['day'] for row in normalized}) > 1:
            report = {**report, 'complete': False, 'coverage': 'mixed_reference_day',
                      'issues': sorted(set(report['issues']) | {'page_day_changed'})}
            for row in normalized:
                row['source_complete'] = False
                row['quality'] = sorted(set(row['quality']) | {'page_day_changed'})
        run['reports'].append({k: report[k] for k in ('id', 'label', 'url', 'cnpj', 'observed_at', 'status', 'complete', 'coverage', 'issues', 'probes', 'probe_ms')})
        run['reports'][-1]['records'] = len(report['rows'])
        run['reports'][-1].update(coverage_reconciled=report.get('coverage_reconciled', report['complete']),
                                 data_status=outcome(report), usable=outcome(report) == 'valid',
                                 empty_retry_count=report.get('empty_retry_count', 0))
        for row in normalized:
            row.update(interval(row, previous.get(row['entity_id'])))
        current.extend(normalized)
        if report['complete'] and normalized:
            latest = {key: row for key, row in latest.items() if row['reporter_id'] != report['id']}
            latest.update({r['entity_id']: r for r in normalized})
        elif normalized and not any(r['reporter_id'] == report['id'] and r['source_complete'] for r in latest.values()):
            # A source that never completed keeps the most recent usable partial context,
            # not the first partial capture forever.
            latest = {key: row for key, row in latest.items() if row['reporter_id'] != report['id']}
            latest.update({r['entity_id']: r for r in normalized})
    state['latest_rows'] = list(latest.values())
    run['collection_health'] = collection_health(run['reports'])
    update_incidents(state, run, current, rules)
    state['observations'].extend(current)
    state['runs'].append(run)
    cutoff = stamp(observed_at) - timedelta(days=rules['retention_days'])
    # Keep/remove whole cycles: source captures can begin seconds after their parent run.
    state['runs'] = [r for r in state['runs'] if stamp(r['observed_at']) >= cutoff]
    retained = {r['run_id'] for r in state['runs']}
    state['observations'] = [r for r in state['observations'] if r['run_id'] in retained]
    state['latest_rows'] = [r for r in state['latest_rows'] if r['run_id'] in retained]
    state['incidents'] = [i for i in state['incidents'] if i['status'] != 'resolved' or stamp(i.get('resolved_at')) >= cutoff]
    return state
