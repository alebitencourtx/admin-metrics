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
