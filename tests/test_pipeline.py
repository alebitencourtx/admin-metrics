from copy import deepcopy
from html.parser import HTMLParser
import json
from pathlib import Path
import zipfile
from datetime import datetime, timedelta, timezone

import httpx
import pytest

from admin_metrics.archive import pack,restore,validate
from admin_metrics.pipeline import run
from admin_metrics.storage import empty_state,write,sha,load,lock
from conftest import record, report
from admin_metrics.analysis import apply
from admin_metrics.build import build


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


def test_rebuild_tolerates_probe_without_source_sha(tmp_path):
    root=tmp_path/'data';site=tmp_path/'site'
    run(root,site,transport=transport())
    state=load(root)
    del state['runs'][-1]['reports'][0]['probes'][0]['source_sha']
    write(root/'state.json',state)
    payload=run(root,site,refresh=False,transport=transport())
    assert payload['meta']['run_id']==state['runs'][-1]['run_id']


def test_archive_rejects_unknown_model_version(tmp_path):
    root=tmp_path/'data';run(root,tmp_path/'site',transport=transport())
    state=load(root);state['runs'][-1]['model_version']=99
    write(root/'state.json',state)
    with pytest.raises(ValueError,match='Modelo'):
        pack(root,tmp_path/'rejected.zip')


def test_restore_rolls_back_files_when_state_commit_fails(tmp_path,monkeypatch):
    import admin_metrics.archive as archive
    root=tmp_path/'data';run(root,tmp_path/'site',transport=transport())
    package=tmp_path/'state.zip';pack(root,package)
    destination=tmp_path/'restored'
    original=archive.atomic
    def failing(path,raw):
        if Path(path).name=='state.json':
            raise OSError('simulated state commit failure')
        return original(path,raw)
    monkeypatch.setattr(archive,'atomic',failing)
    with pytest.raises(OSError):
        restore(package,tmp_path/'SHA256SUMS',destination)
    assert not (destination/'state.json').exists()
    assert not list((destination/'bronze').glob('*'))
    archive.atomic=original
    assert restore(package,tmp_path/'SHA256SUMS',destination)


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


def test_build_prunes_previous_content_addressed_assets(tmp_path):
    root=tmp_path/'data';site=tmp_path/'site'
    run(root,site,transport=transport())
    first={p.name for p in (site/'assets').iterdir() if p.is_dir()}
    run(root,site,transport=transport())
    second={p.name for p in (site/'assets').iterdir() if p.is_dir()}
    assert len(second)==1 and first!=second


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


@pytest.mark.parametrize('kind', ['state', 'object', 'entries', 'expanded'])
def test_pack_and_restore_enforce_identical_limits(tmp_path, monkeypatch, kind):
    import admin_metrics.archive as archive
    root = tmp_path/'data'
    run(root, tmp_path/'site', transport=transport())
    package = tmp_path/'state.zip'
    pack(root, package)
    limits = {'state': ('MAX_STATE', 1), 'object': ('MAX_OBJECT', 1),
              'entries': ('MAX_ENTRIES', 1), 'expanded': ('MAX_EXPANDED', 1)}
    key, value = limits[kind]
    monkeypatch.setattr(archive, key, value)
    with pytest.raises(ValueError, match='limites|Limites'):
        restore(package, tmp_path/'SHA256SUMS', tmp_path/'restored')
    with pytest.raises(ValueError, match='limites|Limites'):
        pack(root, tmp_path/'rejected'/'state.zip')
    assert not (tmp_path/'rejected'/'SHA256SUMS').exists()


def test_thirty_day_hourly_retention_and_three_day_static_history(tmp_path, reporter, rules):
    state = empty_state()
    origin = datetime(2026, 10, 10, 12, tzinfo=timezone.utc)
    # Cross the actual 30-day boundary, with source capture starting after the run.
    for n in range(31*24+1):
        instant = origin + timedelta(hours=n)
        captured = (instant + timedelta(seconds=3)).isoformat()
        source = report(reporter, tmp_path, [record((n % 24+1)*1000, 0)], observed=captured)
        apply(state, [source], rules, instant.isoformat(), 'hour-'+str(n))
        validate(state)
    assert len(state['runs']) == len(state['observations']) == 721
    payload = build(state, tmp_path/'gold', tmp_path/'site', rules, [reporter])
    assert payload['meta']['retained_runs'] == 721
    assert payload['meta']['dashboard_history_days'] == 3
    assert len(payload['runs']) == len(payload['points']) == 72
    assert {r['run_id'] for r in payload['observation_trends']} == {r['run_id'] for r in payload['runs']}
    assert len(payload['reported_history']) == 3
    assert datetime.fromisoformat(payload['meta']['history_window_end']) - datetime.fromisoformat(payload['meta']['history_window_start']) == timedelta(days=3)
    # The reduced Pages payload must not reduce the persistent state.
    assert len(state['runs']) == 721


def test_conflicting_payload_keeps_previous_metrics_out_of_current_kpis(tmp_path):
    root = tmp_path/'data'
    first = run(root, tmp_path/'site', transport=transport())
    conflict = httpx.MockTransport(lambda _: httpx.Response(200, json={
        'data': [record(errors=0), record(errors=900)], 'meta': {'totalRecords': 1}}))
    current = run(root, tmp_path/'site', transport=conflict)
    assert current['report_summary'] == []
    assert all(not row['fresh'] for row in current['latest'])
    assert all(row['run_id'] == first['meta']['run_id'] for row in current['latest'])
    assert all(not row['source_complete'] for row in load(root)['observations'][-8:])
