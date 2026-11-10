from copy import deepcopy

import pytest

from admin_metrics.analysis import apply, normalize, interval, signals
from admin_metrics.storage import empty_state
from conftest import record,report


@pytest.mark.parametrize('calls,errors,expected',[(0,0,None),(10,20,None),(100,None,None),(True,2,None),(100,-1,None),(100,5,5.0),(2**65,1,None)])
def test_invalid_and_zero_rates_are_not_zero(tmp_path,reporter,calls,errors,expected):
    row=normalize(report(reporter,tmp_path,[record(calls,errors)]),'r')[0]
    assert row['error_pct']==expected


def test_clock_and_day_are_not_silently_corrected(tmp_path,reporter):
    source=report(reporter,tmp_path,observed='2026-11-11T01:00:00+00:00')
    source['http_date']='Wed, 11 Nov 2026 01:00:00 GMT'
    source['rows'][0]['record']['requestTime']='2026-11-10T22:00:00Z'
    row=normalize(source,'r')[0]
    assert row['day']=='2026-11-10' and row['request_time']=='2026-11-10T22:00:00Z'
    assert row['clock_offset_seconds']==10800 and 'reported_clock_skew' in row['quality']


def test_quality_history_and_baseline(tmp_path,reporter):
    raw=record();raw['peakTps']['currentDay']=1;raw['availability']['downtime']['partialDowntime']=1
    raw['averageResponse']['previousDays']=[100,300,200,None]
    row=normalize(report(reporter,tmp_path,[raw]),'r')[0]
    assert row['baseline_mean_ms']==200 and row['recurrent_days']==3
    assert {'average_tps_above_peak','history_lengths_differ','uptime_downtime_conflict','mean_ms_history_value_invalid'}<=set(row['quality'])


@pytest.mark.parametrize('change,state',[(dict(day='2026-11-11'),'day_changed'),(dict(calls=900),'counter_reset_or_revision'),(dict(source_complete=False),'incomplete_source'),(dict(calls=None),'invalid_counter'),(dict(errors=2000),'invalid_counter'),(dict(calls=1001,errors=102),'inconsistent_delta'),(dict(calls=1100,errors=105),'valid')])
def test_deltas_reject_resets_days_and_impossible_counters(tmp_path,reporter,change,state):
    previous=normalize(report(reporter,tmp_path),'r')[0]
    current={**previous,**change,'fingerprint':'new','observed_at':'2026-11-10T19:00:00+00:00'}
    delta=interval(current,previous)
    assert delta['interval_state']==state
    assert delta['interval_calls']==(100 if state=='valid' else None)
    assert delta['interval_error_pct']==(5 if state=='valid' else None)
    assert delta['interval_seconds']==3600


def test_unchanged_is_not_interval_traffic(tmp_path,reporter):
    row=normalize(report(reporter,tmp_path),'r')[0]
    assert interval({**row,'observed_at':'2026-11-10T19:00:00+00:00'},row)['interval_state']=='unchanged_report'
    assert interval(row,row)['interval_state']=='observation_time_not_increasing'


def step(state, reporter, root, rules, n, raw=None, status=200, complete=True):
    source=report(reporter,root,[raw or record()],observed=f'2026-11-10T{12+n:02}:00:00+00:00',status=status,complete=complete)
    return apply(state,[source],rules,source['observed_at'],'r'+str(n))


def test_incident_recovery_needs_evaluable_consecutive_samples(tmp_path,reporter,rules):
    state=empty_state();step(state,reporter,tmp_path,rules,0)
    inc=state['incidents'][0];assert not inc['confirmed']
    step(state,reporter,tmp_path,rules,1);assert inc['confirmed']
    step(state,reporter,tmp_path,rules,2,record(1200,100));assert inc['status']=='open'
    step(state,reporter,tmp_path,rules,3,record(5000,100));assert inc['status']=='recovering'
    step(state,reporter,tmp_path,rules,4,record(5000,None));assert inc['status']!='resolved' and inc['recovery_samples']==0
    step(state,reporter,tmp_path,rules,5,record(6000,100));assert inc['status']=='recovering'
    step(state,reporter,tmp_path,rules,6,record(7000,100));assert inc['status']=='recovering'
    step(state,reporter,tmp_path,rules,7,record(8000,100));assert inc['status']=='resolved'
    step(state,reporter,tmp_path,rules,8,record(9000,1000))
    assert len(state['incidents'])==2 and state['incidents'][0]['id']!=state['incidents'][1]['id']


def test_missing_or_low_traffic_cannot_resolve(tmp_path,reporter,rules):
    state=empty_state();step(state,reporter,tmp_path,rules,0)
    for n in (1,2):step(state,reporter,tmp_path,rules,n,record(0,0))
    assert state['incidents'][0]['status']=='open'
    for n in (3,4):step(state,reporter,tmp_path,rules,n,record(),status=403,complete=False)
    assert state['incidents'][0]['status']=='open'
    collection=[i for i in state['incidents'] if i['rule']=='collection'][0]
    assert collection['severity']=='critical'


def test_collection_streak_resets_and_preserves_last_good(tmp_path,reporter,rules):
    state=empty_state();step(state,reporter,tmp_path,rules,0)
    initial=deepcopy(state['latest_rows'])
    step(state,reporter,tmp_path,rules,1,status=403,complete=False)
    assert state['latest_rows']==initial
    incident=next(i for i in state['incidents'] if i['rule']=='collection')
    assert incident['severity']=='attention'
    step(state,reporter,tmp_path,rules,2)
    step(state,reporter,tmp_path,rules,3,status=403,complete=False)
    assert incident['severity']=='attention' and incident['consecutive_samples']==1


def test_history_retention_and_run_idempotency(tmp_path,reporter,rules):
    state=empty_state();step(state,reporter,tmp_path,rules,0)
    source=report(reporter,tmp_path,observed='2026-12-15T12:00:00+00:00')
    apply(state,[source],rules,source['observed_at'],'future')
    assert len(state['runs'])==len(state['observations'])==1
    with pytest.raises(ValueError,match='já aplicada'):apply(state,[source],rules,source['observed_at'],'future')
