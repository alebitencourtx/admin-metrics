"""Choose one complete cycle and one reference day per executive scope."""
from collections import defaultdict

from .health import outcome, collection_health


def presentation(state, reporters):
    required = {r['id'] for r in reporters}
    by_run = defaultdict(list)
    for row in state['observations']:
        if row['source_complete'] and row['reporter_id'] in required:
            by_run[row['run_id']].append(row)
    snapshots = {}
    scopes = {'all': required, **{key: {key} for key in required}}
    for run in reversed(state['runs']):
        reports = {r['id']: r for r in run['reports']}
        available = {key for key, report in reports.items() if outcome(report) == 'valid'}
        for scope, identities in scopes.items():
            if scope in snapshots or not identities <= available:
                continue
            selected = [{**row, 'fresh': row['run_id'] == state['runs'][-1]['run_id']}
                        for row in by_run[run['run_id']] if row['reporter_id'] in identities]
            # Completeness requires the exact normalized count, not just HTTP success.
            if (not selected or len({row['day'] for row in selected}) != 1
                    or any(sum(row['reporter_id'] == key for row in selected) != reports[key]['records'] for key in identities)):
                continue
            snapshots[scope] = {'run_id': run['run_id'], 'observed_at': run['observed_at'],
                                'day': selected[0]['day'], 'rows': selected}
        if len(snapshots) == len(scopes):
            break
    last = state['runs'][-1]
    sources = []
    for report in last['reports']:
        snap = snapshots.get(report['id'])
        sources.append({'id': report['id'], 'status': outcome(report),
                        'last_attempt_at': report['observed_at'],
                        'last_valid_at': max(r['observed_at'] for r in snap['rows']) if snap else None,
                        'last_valid_run_id': snap['run_id'] if snap else None})
    coherent = snapshots.get('all')
    return {'snapshots': snapshots, 'health': {**collection_health(last['reports']),
            'last_attempt_at': last['observed_at'],
            'last_valid_at': coherent['observed_at'] if coherent else None, 'sources': sources}}
