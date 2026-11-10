"""Explicit nulls, bounded history, cumulative-counter deltas and stateful incidents."""
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
import math
from statistics import median
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo

from .storage import sha, encoded

FIELDS = {'invocations': 'calls', 'errors': 'errors', 'rejections': 'rejections',
          'averageResponse': 'mean_ms', 'averageTps': 'average_tps', 'peakTps': 'peak_tps'}


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


def normalize(report, run_id):
    rows = []
    acquired = stamp(report['observed_at'])
    date_valid = True
    try:
        reference = parsedate_to_datetime(report['http_date'])
    except (ValueError, TypeError, OverflowError):
        reference = acquired
        date_valid = False
    if reference.tzinfo is None:
        reference = acquired
        date_valid = False
    day = reference.astimezone(ZoneInfo('America/Sao_Paulo')).date().isoformat()
    for item in report['rows']:
        raw = item['record']
        flags = []
        endpoint = raw['endpoint']
        parsed = urlsplit(endpoint)
        path = parsed.path if parsed.path else endpoint
        family = path.split('/open-banking/', 1)[-1].split('/')[0]
        row = {'run_id': run_id, 'observed_at': report['observed_at'], 'day': day,
               'day_basis': 'HTTP Date / America_Sao_Paulo' if date_valid else 'observed_at / America_Sao_Paulo', 'reporter_id': report['id'], 'reporter': report['label'],
               'entity_id': sha(encoded([report['id'], endpoint]))[:24], 'endpoint': endpoint, 'path': path,
               'family': family, 'source_sha': item['source_sha'], 'json_path': item['json_path'],
               'request_time': raw.get('requestTime'), 'source_complete': report['complete'], 'previous': {}}
        reported = stamp(raw.get('requestTime'))
        row['clock_offset_seconds'] = (acquired - reported).total_seconds() if reported else None
        if not reported:
            flags.append('request_time_invalid')
        elif abs(row['clock_offset_seconds']) > 900:
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
            if not isinstance(previous, list) or len(previous) > 7:
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
            try:
                value = float(uptime.get(source))
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
        row['baseline_mean_ms'] = median(previous_means) if len(previous_means) >= 3 else None
        recurrent = 0
        for calls, errors in zip(row['previous']['calls'], row['previous']['errors']):
            value = ratio(errors, calls)
            if calls is not None and calls >= 100 and value is not None and value >= 5:
                recurrent += 1
        row['recurrent_days'] = recurrent
        row['quality'] = sorted(set(flags))
        row['fingerprint'] = sha(encoded({k: row[k] for k in (*FIELDS.values(), 'uptime', 'downtime_seconds', 'previous')}))
        rows.append(row)
    return rows


def interval(current, previous):
    result = {'interval_calls': None, 'interval_errors': None, 'interval_rejections': None,
              'interval_error_pct': None, 'interval_rejection_pct': None, 'interval_state': 'first_observation'}
    if not previous:
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


def signals(row, rules):
    calls = row['calls'] or 0
    result = []
    if calls >= rules['minimum_calls']:
        if row['error_pct'] is not None and row['error_pct'] >= rules['error_attention_pct']:
            level = 'critical' if calls >= rules['critical_minimum_calls'] and row['error_pct'] >= rules['error_critical_pct'] else 'attention'
            result.append(('error_rate', level, f"{row['errors']} erros / {calls} chamadas ({row['error_pct']:.2f}%)"))
        if row['rejection_pct'] is not None and row['rejection_pct'] >= rules['rejection_attention_pct']:
            result.append(('rejection_rate', 'attention', f"{row['rejections']} rejeições / {calls} chamadas; causa não identificável"))
        if row['mean_ms'] is not None and row['mean_ms'] >= rules['latency_attention_ms']:
            result.append(('mean_latency', 'critical' if row['mean_ms'] >= rules['latency_critical_ms'] else 'attention', f"Média declarada {row['mean_ms']} ms; não é p95"))
        if row['mean_ms'] and row['baseline_mean_ms'] and row['mean_ms'] >= rules['regression_multiplier'] * row['baseline_mean_ms']:
            result.append(('latency_regression', 'attention', f"Média {row['mean_ms']} ms / baseline {row['baseline_mean_ms']} ms"))
    return result


def update_incidents(state, run, rows, rules):
    existing = {(i['entity_id'], i['rule']): i for i in state['incidents'] if i['status'] != 'resolved'}
    detected = {}
    eligible = set()
    for report in run['reports']:
        key = 'source:' + report['id']
        eligible.add((key, 'collection'))
        if report['status'] != 200 or not report['complete'] or not report['records']:
            detected[(key, 'collection')] = ('attention', '; '.join(report['issues']) or 'Reporte incompleto', report['label'], None)
    for row in rows:
        if not row['source_complete']:
            continue
        if row['interval_state'] in ('counter_reset_or_revision', 'inconsistent_delta', 'invalid_counter'):
            continue
        # Absence of a signal is recovery only when that rule was evaluable.
        if (row['calls'] or 0) >= rules['minimum_calls']:
            for rule, valid in [('error_rate', row['error_pct'] is not None),
                                ('rejection_rate', row['rejection_pct'] is not None),
                                ('mean_latency', bool(row['mean_ms'])),
                                ('latency_regression', bool(row['mean_ms'] and row['baseline_mean_ms']))]:
                if valid:
                    eligible.add((row['entity_id'], rule))
        for rule, severity, evidence in signals(row, rules):
            detected[(row['entity_id'], rule)] = (severity, evidence, row['reporter'], row['endpoint'])
    # Apply each observation once, including same-cycle multiple rule detections.
    for (entity, rule), (severity, evidence, label, endpoint) in detected.items():
        key = (entity, rule)
        incident = existing.get(key)
        if incident is None:
            incident = {'id': sha(encoded([entity, rule, run['run_id']]))[:24], 'entity_id': entity, 'rule': rule, 'reporter': label, 'endpoint': endpoint,
                        'opened_at': run['observed_at'], 'opened_run': run['run_id'], 'samples': 0,
                        'consecutive_samples': 0, 'recovery_samples': 0, 'status': 'open'}
            state['incidents'].append(incident)
            existing[key] = incident
        streak = incident['consecutive_samples'] + 1
        incident.update(last_seen=run['observed_at'], evaluated_at=run['observed_at'], evidence=evidence,
                        samples=incident['samples'] + 1, consecutive_samples=streak,
                        recovery_samples=0, status='open', severity='critical' if rule == 'collection' and streak >= 2 else severity)
        incident['confirmed'] = streak >= 2
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
    if any(r['run_id'] == run_id for r in state['runs']):
        raise ValueError('Execução já aplicada')
    run = {'run_id': run_id, 'observed_at': observed_at, 'reports': [], 'rules': dict(rules), 'model_version': 1}
    previous = {r['entity_id']: r for r in state['observations']}
    current = []
    latest = {r['entity_id']: r for r in state['latest_rows']}
    for report in reports:
        run['reports'].append({k: report[k] for k in ('id', 'label', 'url', 'cnpj', 'observed_at', 'status', 'complete', 'coverage', 'issues', 'probes', 'probe_ms')})
        run['reports'][-1]['records'] = len(report['rows'])
        normalized = normalize(report, run_id)
        for row in normalized:
            row.update(interval(row, previous.get(row['entity_id'])))
        current.extend(normalized)
        if report['complete'] and normalized:
            latest = {key: row for key, row in latest.items() if row['reporter_id'] != report['id']}
            latest.update({r['entity_id']: r for r in normalized})
        elif not any(r['reporter_id'] == report['id'] for r in latest.values()):
            latest.update({r['entity_id']: r for r in normalized})
    state['latest_rows'] = list(latest.values())
    update_incidents(state, run, current, rules)
    state['observations'].extend(current)
    state['runs'].append(run)
    cutoff = (stamp(observed_at) - timedelta(days=rules['retention_days'])).isoformat(timespec='seconds')
    state['observations'] = [r for r in state['observations'] if r['observed_at'] >= cutoff]
    state['runs'] = [r for r in state['runs'] if r['observed_at'] >= cutoff]
    state['latest_rows'] = [r for r in state['latest_rows'] if r['observed_at'] >= cutoff]
    state['incidents'] = [i for i in state['incidents'] if i['status'] != 'resolved' or i.get('resolved_at', '') >= cutoff]
    return state
