from copy import deepcopy
from datetime import datetime, timedelta, timezone

from admin_metrics.analysis import apply
from admin_metrics.panorama import presentation
from admin_metrics.storage import empty_state
from conftest import report, record


def cycle(state, root, reporters, rules, hour, modes=None, mixed_day=False):
    instant = datetime(2026, 11, 12, 20, tzinfo=timezone.utc) + timedelta(hours=hour)
    sources = []
    for index, reporter in enumerate(reporters):
        mode = (modes or {}).get(reporter['id'], 'valid')
        source = report(reporter, root, [] if mode in ('empty', 'http') else [record()],
                        observed=instant.isoformat(), status=503 if mode == 'http' else 200,
                        complete=mode != 'http')
        if mode == 'empty': source['issues'] = ['empty_report']
        if mixed_day:
            source['http_date'] = 'Fri, 13 Nov 2026 03:01:00 GMT' if index else 'Fri, 13 Nov 2026 02:59:00 GMT'
        sources.append(source)
    apply(state, sources, rules, instant.isoformat(), 'r'+str(hour))


def test_total_failure_preserves_a_coherent_panorama_and_actual_attempt_health(tmp_path, reporter, rules):
    reporters = [reporter, {**reporter, 'id':'other', 'label':'Other'}]
    state = empty_state()
    cycle(state, tmp_path, reporters, rules, 0)
    first = deepcopy(state['observations'])
    cycle(state, tmp_path, reporters, rules, 1, {reporter['id']:'empty', 'other':'http'})
    view = presentation(state, reporters)
    assert view['health']['status'] == 'unavailable' and view['health']['valid_sources'] == 0
    assert view['snapshots']['all']['run_id'] == 'r0'
    assert all(not r['fresh'] for r in view['snapshots']['all']['rows'])
    assert {r['observed_at'] for r in view['snapshots']['all']['rows']} == {r['observed_at'] for r in first}
    assert len(state['observations']) == len(first)


def test_partial_failure_does_not_mix_runs_and_selected_healthy_source_can_advance(tmp_path, reporter, rules):
    reporters = [reporter, {**reporter, 'id':'other', 'label':'Other'}]
    state = empty_state()
    cycle(state, tmp_path, reporters, rules, 0)
    cycle(state, tmp_path, reporters, rules, 1, {'other':'http'})
    view = presentation(state, reporters)
    assert view['health']['status'] == 'partial'
    assert view['snapshots']['all']['run_id'] == 'r0'
    assert view['snapshots'][reporter['id']]['run_id'] == 'r1'
    assert view['snapshots']['other']['run_id'] == 'r0'


def test_midnight_mixed_reference_days_cannot_replace_complete_panorama(tmp_path, reporter, rules):
    reporters = [reporter, {**reporter, 'id':'other', 'label':'Other'}]
    state = empty_state()
    cycle(state, tmp_path, reporters, rules, 0)
    cycle(state, tmp_path, reporters, rules, 4, mixed_day=True)
    view = presentation(state, reporters)
    assert view['health']['status'] == 'healthy'
    assert view['snapshots']['all']['run_id'] == 'r0'
    assert view['snapshots'][reporter['id']]['run_id'] == view['snapshots']['other']['run_id'] == 'r4'


def test_recovery_replaces_the_panorama_with_real_new_rows(tmp_path, reporter, rules):
    state = empty_state()
    cycle(state, tmp_path, [reporter], rules, 0)
    cycle(state, tmp_path, [reporter], rules, 1, {reporter['id']:'empty'})
    cycle(state, tmp_path, [reporter], rules, 2)
    view = presentation(state, [reporter])
    assert view['health']['status'] == 'healthy'
    assert view['snapshots']['all']['run_id'] == 'r2'
    assert len(state['observations']) == 2
