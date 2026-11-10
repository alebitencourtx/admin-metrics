from copy import deepcopy
from html.parser import HTMLParser
import json
from pathlib import Path
import zipfile

import httpx
import pytest

from admin_metrics.archive import pack,restore,validate
from admin_metrics.pipeline import run
from admin_metrics.storage import empty_state,write,sha,load,lock
from conftest import record


class Inventory(HTMLParser):
    def __init__(self):super().__init__();self.ids=[];self.assets=[];self.links=[]
    def handle_starttag(self,tag,attrs):
        a=dict(attrs)
        if 'id' in a:self.ids.append(a['id'])
        if tag in ('script','img','link','iframe'):self.assets.append((tag,a))
        if tag=='a' and a.get('href','').startswith('#'):self.links.append(a['href'][1:])


def transport():
    return httpx.MockTransport(lambda request:httpx.Response(200,json={'data':[record(endpoint='https://customer.example/open-banking/accounts/v2/accounts')],'meta':{'totalRecords':1,'totalPages':1}}))


def test_end_to_end_eight_sources_marts_archive_and_standalone_manual(tmp_path):
    root=tmp_path/'data';site=tmp_path/'site'
    payload=run(root,site,transport=transport())
    assert len(payload['latest'])==8 and len(payload['report_summary'])==8
    assert all(r['error_pct']==10 for r in payload['report_summary'])
    assert len(list((root/'gold').glob('*.parquet')))==5
    index=(site/'index.html').read_text(encoding='utf-8');inv=Inventory();inv.feed(index)
    assert '<main id="content"' in index and 'location.replace' not in index and 'http-equiv="refresh"' not in index
    assert len(set(inv.ids))==len(inv.ids) and set(inv.links)<=set(inv.ids)
    for tag,a in inv.assets:
        if a.get('src'):assert (site/a['src']).is_file()
        if tag=='link' and a.get('rel')=='stylesheet':assert (site/a['href']).is_file()
    manual=(site/'documentacao.html').read_text(encoding='utf-8');inv=Inventory();inv.feed(manual)
    assert {'solution-svg','flow-svg','er-svg','search'}<=set(inv.ids)
    assert len(set(inv.ids))==len(inv.ids) and set(inv.links)<=set(inv.ids)
    assert not any(a.get('src') or (tag=='link' and a.get('href')) for tag,a in inv.assets)
    assert payload['meta']['run_id'] in manual
    package=tmp_path/'package'/'state.zip';manifest=pack(root,package)
    dest=tmp_path/'restored';assert restore(package,package.parent/'SHA256SUMS',dest)==manifest
    assert load(dest)==load(root)
    assert run(dest,tmp_path/'replay',refresh=False)['meta']['run_id']==payload['meta']['run_id']


def test_partial_failure_keeps_last_good_but_excludes_it_from_current_marts(tmp_path):
    root=tmp_path/'data';site=tmp_path/'site';first=run(root,site,transport=transport())
    bad=httpx.MockTransport(lambda request:httpx.Response(403,text='Forbidden'))
    current=run(root,site,transport=bad)
    assert len(current['latest'])==8 and all(not r['fresh'] for r in current['latest'])
    assert current['report_summary']==[] and len(current['runs'])==2
    assert len([i for i in current['incidents'] if i['rule']=='collection'])==8
    assert {r['run_id'] for r in current['latest']}=={first['meta']['run_id']}


def test_failed_build_preserves_published_index_and_state(tmp_path,monkeypatch):
    root=tmp_path/'data';site=tmp_path/'site';run(root,site,transport=transport())
    state=(root/'state.json').read_bytes();index=(site/'index.html').read_bytes()
    import admin_metrics.documentation as doc
    def fail(*args):raise RuntimeError('structural failure')
    monkeypatch.setattr(doc,'generate',fail)
    with pytest.raises(RuntimeError):run(root,site,transport=transport())
    assert (root/'state.json').read_bytes()==state and (site/'index.html').read_bytes()==index


def test_bronze_retains_two_cycles_and_rebuild_adds_no_observation(tmp_path):
    root=tmp_path/'data';site=tmp_path/'site'
    for n in range(3):
        raw=record(calls=1000+n)
        run(root,site,transport=httpx.MockTransport(lambda request:httpx.Response(200,json={'data':[raw],'meta':{'totalRecords':1}})))
    assert len(list((root/'bronze').glob('*.json')))==2
    before=load(root);run(root,site,refresh=False);assert before==load(root)


@pytest.mark.parametrize('attack',['checksum','path','inner','duplicate','missing'])
def test_restore_rejects_corruption_before_state_commit(tmp_path,attack):
    root=tmp_path/'data';run(root,tmp_path/'site',transport=transport())
    package=tmp_path/'state.zip';pack(root,package);checksum=tmp_path/'SHA256SUMS'
    if attack=='checksum':checksum.write_text('0'*64+'  state.zip\n')
    else:
        with zipfile.ZipFile(package) as z:files={name:z.read(name) for name in z.namelist()}
        if attack=='path':files['../outside.txt']=b'evil'
        if attack=='inner':files['state.json']=b'{}'
        if attack=='missing':files.pop(next(n for n in files if n.startswith('bronze/')))
        with zipfile.ZipFile(package,'w') as z:
            for name,raw in files.items():z.writestr(name,raw)
            if attack=='duplicate':z.writestr('state.json',files['state.json'])
        checksum.write_text(sha(package.read_bytes())+'  state.zip\n')
    with pytest.raises((ValueError,KeyError)):restore(package,checksum,tmp_path/'dest')
    assert not (tmp_path/'dest'/'state.json').exists() and not (tmp_path/'outside.txt').exists()


def test_exclusive_writer_and_state_contract(tmp_path):
    with lock(tmp_path):
        with pytest.raises(RuntimeError):
            with lock(tmp_path):pass
    assert not (tmp_path/'.writer.lock').exists()
    with pytest.raises(ValueError):validate(empty_state())
