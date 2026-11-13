import importlib.util
import json
from pathlib import Path

import pytest


def module():
    spec=importlib.util.spec_from_file_location('cloud',Path('scripts/cloud_pipeline.py'))
    result=importlib.util.module_from_spec(spec);spec.loader.exec_module(result);return result


def test_promotion_requires_successful_matching_deploy(monkeypatch):
    m=module()
    def fake(*args):
        if args[:2]==('release','view'):return json.dumps({'body':json.dumps({'workflow_run_id':'77','data_run_id':'obs','source_sha':'abc','purpose':'approved-monitor-state'}),'isDraft':True})
        if args[0]=='api':return json.dumps({'jobs':[{'name':'deploy','status':'completed','conclusion':'failure'}]})
        pytest.fail('Mutation before successful deploy evidence')
    monkeypatch.setattr(m,'gh',fake)
    with pytest.raises(ValueError,match='recibo'):m.promote('state-77-1')


def test_promotion_retains_two_owned_states_only(monkeypatch):
    m=module();calls=[]
    def fake(*args):
        calls.append(args)
        if args[:2]==('release','view'):return json.dumps({'body':json.dumps({'workflow_run_id':'77','data_run_id':'obs','source_sha':'abc','purpose':'approved-monitor-state'}),'isDraft':True})
        if args[0]=='api':return json.dumps({'jobs':[{'name':'deploy','id':123,'completed_at':'now','status':'completed','conclusion':'success'}]})
        return ''
    monkeypatch.setattr(m,'gh',fake)
    monkeypatch.setattr(m,'releases',lambda:[{'tag_name':f'state-{n}','draft':False,'prerelease':False,'published_at':str(n),'id':n} for n in [1,2,3]]+[{'tag_name':'unrelated','draft':False,'prerelease':False,'published_at':'0','id':0}])
    m.promote('state-77-1')
    assert ('release','delete','state-1','--yes','--cleanup-tag') in calls
    assert not any('unrelated' in c for c in calls)


def test_summary_distinguishes_unavailable_collection_from_publication(tmp_path, monkeypatch, capsys):
    m = module()
    summary, output = tmp_path/'summary.md', tmp_path/'output'
    monkeypatch.setenv('GITHUB_STEP_SUMMARY', str(summary))
    monkeypatch.setenv('GITHUB_OUTPUT', str(output))
    payload = {'collection_health': {'status':'unavailable', 'valid_sources':0, 'total_sources':8,
                'last_attempt_at':'now', 'last_valid_at':'yesterday'}, 'runs':[{'reports':[]}]}
    m.summarize_health(payload, True)
    assert 'SEM DADOS VÁLIDOS' in summary.read_text(encoding='utf-8')
    assert '0/8' in summary.read_text(encoding='utf-8')
    assert 'collection_status=unavailable' in output.read_text()
    assert '::warning' in capsys.readouterr().out


def test_execution_links_use_owned_release_receipts_not_guessed_timestamps():
    m = module()
    releases = [{'body': json.dumps({'purpose':'approved-monitor-state', 'data_run_id':'observation', 'workflow_run_id':'123'})},
                {'body':'not JSON'}, {'body':'{}'}]
    assert m.execution_links(releases, 'owner/repo') == {'observation':'https://github.com/owner/repo/actions/runs/123'}
