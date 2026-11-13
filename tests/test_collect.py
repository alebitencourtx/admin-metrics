import httpx
import pytest

from admin_metrics.collect import capture,validate_reporter,delay
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
