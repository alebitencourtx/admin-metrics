import httpx
import pytest

from admin_metrics.analysis import apply, normalize
from admin_metrics.collect import capture,validate_reporter,validate_reporters,delay
from admin_metrics.storage import empty_state
from conftest import record


@pytest.mark.asyncio
async def test_repeated_conflicting_pages_dedup_and_keep_both_bronzes(tmp_path,reporter):
    requests=[]
    def handler(request):
        page=int(request.url.params['page']);requests.append(page)
        return httpx.Response(200,json={'data':[record(errors=100 if page==1 else 101)],'meta':{'totalRecords':2,'totalPages':3}})
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        result=await capture(client,reporter,tmp_path)
    assert requests==[1,2] and len(result['rows'])==1 and not result['complete']
    assert result['rows'][0]['record']['errors']['currentDay']==100
    assert {'duplicate_endpoint','conflicting_endpoint','pagination_no_new_identity'}<=set(result['issues'])
    assert len(list((tmp_path/'bronze').glob('*.json')))==2


@pytest.mark.asyncio
async def test_total_reconciled_ignores_phantom_pages(tmp_path,reporter):
    calls=[]
    def handler(request):
        calls.append(request)
        return httpx.Response(200,json={'data':[record()],'meta':{'totalRecords':1,'totalPages':2}})
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:result=await capture(client,reporter,tmp_path)
    assert len(calls)==1 and result['complete'] and 'page_metadata_conflict' in result['issues']
    assert result['rows'][0]['json_path']=='$.data[0]'


@pytest.mark.asyncio
async def test_retry_transient_and_no_retry_for_access_denied(tmp_path,reporter,monkeypatch):
    import admin_metrics.collect as module
    async def noop(_):pass
    monkeypatch.setattr(module.asyncio,'sleep',noop)
    statuses=[503,429,200];seen=[]
    def handler(request):
        status=statuses[len(seen)];seen.append(status)
        return httpx.Response(status,json={'data':[record()],'meta':{'totalRecords':1}},headers={'Retry-After':'999'})
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:r=await capture(client,reporter,tmp_path)
    assert seen==statuses and len(r['probes'])==3 and r['complete']
    assert delay('999',0)==15
    seen.clear()
    def denied(request):seen.append(request);return httpx.Response(403,text='Forbidden')
    async with httpx.AsyncClient(transport=httpx.MockTransport(denied)) as client:r=await capture(client,reporter,tmp_path)
    assert len(seen)==1 and not r['complete'] and r['status']==403


@pytest.mark.parametrize('body',[{}, {'data':{}}, {'data':[],'meta':{'totalRecords':True}}, {'data':[{'endpoint':42}],'meta':{'totalRecords':1,'totalPages':1}}])
@pytest.mark.asyncio
async def test_malformed_payload_observed_as_failure(tmp_path,reporter,body):
    async with httpx.AsyncClient(transport=httpx.MockTransport(lambda r:httpx.Response(200,json=body))) as client:r=await capture(client,reporter,tmp_path,retries=0)
    assert not r['complete'] and r['issues']


@pytest.mark.parametrize('url',['http://ccvm.api.santander.com.br/open-banking/admin/v2/metrics','https://ccvm.api.santander.com.br/private','https://evil.example/open-banking/admin/v2/metrics','https://ccvm.api.santander.com.br/open-banking/admin/v2/metrics?target=private'])
def test_catalog_prevents_customer_calls(reporter,url):
    with pytest.raises(ValueError):validate_reporter({**reporter,'url':url})


class InterruptedBody(httpx.AsyncByteStream):
    async def __aiter__(self):
        yield b'{'
        raise httpx.ReadError('body interrupted after HTTP 200')


@pytest.mark.asyncio
async def test_retry_transport_failure_after_success_headers(tmp_path, reporter, monkeypatch):
    import admin_metrics.collect as module
    async def noop(_): pass
    monkeypatch.setattr(module.asyncio, 'sleep', noop)
    requests = []
    def handler(request):
        requests.append(request)
        if len(requests) == 1:
            return httpx.Response(200, stream=InterruptedBody())
        return httpx.Response(200, json={'data': [record()], 'meta': {'totalRecords': 1}})
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        result = await capture(client, reporter, tmp_path)
    assert len(requests) == 2 and result['complete']
    assert result['probes'][0]['status'] == 200 and 'interrupted' in result['probes'][0]['error']
    assert result['probes'][1]['error'] is None


@pytest.mark.asyncio
async def test_conflicting_identity_cannot_be_reconciled_as_complete(tmp_path, reporter):
    body = {'data': [record(errors=0), record(errors=900)], 'meta': {'totalRecords': 1}}
    async with httpx.AsyncClient(transport=httpx.MockTransport(lambda _: httpx.Response(200, json=body))) as client:
        result = await capture(client, reporter, tmp_path)
    assert not result['complete'] and 'conflicting_endpoint' in result['issues']
    assert result['rows'][0]['ambiguous']


@pytest.mark.parametrize('endpoint', ['https://[invalid', 'https://example.com:bad/path', '', 'garbage', 'https://example.com/a b'])
@pytest.mark.asyncio
async def test_invalid_endpoint_is_source_quality_failure(tmp_path, reporter, endpoint):
    body = {'data': [record(endpoint=endpoint), record()], 'meta': {'totalRecords': 2, 'totalPages': 1}}
    async with httpx.AsyncClient(transport=httpx.MockTransport(lambda _: httpx.Response(200, json=body))) as client:
        result = await capture(client, reporter, tmp_path)
    assert not result['complete'] and len(result['rows']) == 1
    assert 'invalid_endpoint_record' in result['issues']


@pytest.mark.asyncio
async def test_reconciled_empty_response_is_not_usable(tmp_path, reporter):
    async with httpx.AsyncClient(transport=httpx.MockTransport(lambda _: httpx.Response(200, json={
            'data': [], 'meta': {'totalRecords': 0, 'totalPages': 0}}))) as client:
        result = await capture(client, reporter, tmp_path)
    assert result['coverage_reconciled'] and not result['complete'] and not result['usable']
    assert result['data_status'] == 'empty' and result['coverage'] == 'empty_response'


@pytest.mark.parametrize('recover', [False, True])
@pytest.mark.asyncio
async def test_empty_retries_preserve_every_attempt_without_new_observations(tmp_path, reporter, monkeypatch, recover):
    import admin_metrics.collect as module
    waits, requests = [], []
    async def sleep(seconds): waits.append(seconds)
    monkeypatch.setattr(module.asyncio, 'sleep', sleep)
    def handler(request):
        requests.append(request)
        rows = [record()] if recover and len(requests) == 2 else []
        return httpx.Response(200, json={'data': rows, 'meta': {'totalRecords': len(rows), 'totalPages': bool(rows)*1}})
    reports = await module.collect([reporter], tmp_path, httpx.MockTransport(handler), {reporter['id']}, [10,30])
    result = reports[0]
    assert len(requests) == (2 if recover else 3)
    assert waits == ([10] if recover else [10,30])
    assert [p['capture_attempt'] for p in result['probes']] == list(range(1, len(requests)+1))
    assert result['usable'] is recover
    assert result['data_status'] == ('valid' if recover else 'empty')
    if recover: assert 'empty_response_recovered' in result['issues']


@pytest.mark.asyncio
async def test_bootstrap_empty_is_not_retried_without_previous_valid_source(tmp_path, reporter):
    from admin_metrics.collect import collect
    requests = []
    def handler(request):
        requests.append(request)
        return httpx.Response(200, json={'data': [], 'meta': {'totalRecords': 0}})
    result = (await collect([reporter], tmp_path, httpx.MockTransport(handler)))[0]
    assert len(requests) == 1 and result['empty_retry_count'] == 0


@pytest.mark.asyncio
async def test_pages_use_their_own_http_date_for_day(tmp_path, reporter):
    pages = {
        1: {'data': [record(endpoint='https://a.example/open-banking/accounts/v2/accounts')],
            'meta': {'totalRecords': 2, 'totalPages': 2}},
        2: {'data': [record(endpoint='https://b.example/open-banking/accounts/v2/accounts')],
            'meta': {'totalRecords': 2, 'totalPages': 2}},
    }
    dates = {1: 'Tue, 10 Nov 2026 02:59:00 GMT', 2: 'Tue, 10 Nov 2026 03:01:00 GMT'}
    def handler(request):
        page = int(request.url.params['page'])
        return httpx.Response(200, json=pages[page], headers={'Date': dates[page]})
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        result = await capture(client, reporter, tmp_path, retries=0)
    rows = normalize(result, 'run')
    assert [row['day'] for row in rows] == ['2026-11-09', '2026-11-10']
    assert all(row['day_basis'] == 'HTTP Date / America_Sao_Paulo' for row in rows)


@pytest.mark.asyncio
async def test_pages_across_midnight_make_capture_incomplete(tmp_path, reporter, rules):
    pages = {
        1: {'data': [record(endpoint='https://a.example/open-banking/accounts/v2/accounts')],
            'meta': {'totalRecords': 2, 'totalPages': 2}},
        2: {'data': [record(endpoint='https://b.example/open-banking/accounts/v2/accounts')],
            'meta': {'totalRecords': 2, 'totalPages': 2}},
    }
    dates = {1: 'Tue, 10 Nov 2026 02:59:00 GMT', 2: 'Tue, 10 Nov 2026 03:01:00 GMT'}
    def handler(request):
        page = int(request.url.params['page'])
        return httpx.Response(200, json=pages[page], headers={'Date': dates[page]})
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        result = await capture(client, reporter, tmp_path, retries=0)
    state = apply(empty_state(), [result], rules, result['observed_at'], 'mixed')
    stored = state['runs'][0]['reports'][0]
    assert stored['complete'] is False and stored['coverage'] == 'mixed_reference_day'
    assert 'page_day_changed' in stored['issues']
    assert all(not row['source_complete'] for row in state['observations'])
    assert all('page_day_changed' in row['quality'] for row in state['observations'])


@pytest.mark.asyncio
async def test_record_limit_is_effective(tmp_path, reporter):
    def handler(request):
        page = int(request.url.params['page'])
        rows = [record(endpoint=f'https://e{page}-{index}.example/open-banking/accounts/v2/accounts')
                for index in range(1000)]
        return httpx.Response(200, json={'data': rows,
                                         'meta': {'totalRecords': 50000, 'totalPages': 50}})
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        result = await capture(client, reporter, tmp_path, retries=0)
    assert len(result['rows']) == 10000
    assert result['complete'] is False and result['coverage'] == 'record_limit'
    assert 'record_limit' in result['issues']


def test_reporter_catalog_requires_identity_fields(reporter):
    assert validate_reporters([reporter]) == [reporter]
    for key in ('id', 'label', 'company', 'cnpj', 'url'):
        bad = {**reporter}
        del bad[key]
        with pytest.raises(ValueError):
            validate_reporters([bad])
    with pytest.raises(ValueError):
        validate_reporters([reporter, reporter])
    with pytest.raises(ValueError):
        validate_reporters([{**reporter, 'cnpj': '123'}])


def test_invalid_reporter_url_is_structural(reporter):
    with pytest.raises(ValueError):
        validate_reporters([{**reporter, 'url': 'https://evil.example/open-banking/admin/v2/metrics'}])
