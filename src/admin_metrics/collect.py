"""Read only the public Admin reports, never the customer endpoints they describe."""
import asyncio
from datetime import datetime, timezone
import email.utils
import json
import random
import ssl
import time
from urllib.parse import urlsplit

import httpx
import truststore

from .storage import now, put, sha, encoded
from .contracts import endpoint_parts
from .health import outcome


def validate_reporter(reporter):
    url = urlsplit(reporter['url'])
    expected = reporter['id'] + '.api.santander.com.br'
    if (url.scheme != 'https' or url.hostname != expected or url.port not in (None, 443)
            or url.username or url.password or url.query or url.fragment
            or url.path != '/open-banking/admin/v2/metrics'):
        raise ValueError('URL fora do catálogo permitido: ' + reporter['id'])


def delay(value, attempt):
    try:
        seconds = float(value)
    except (TypeError, ValueError):
        try:
            seconds = (email.utils.parsedate_to_datetime(value) - datetime.now(timezone.utc)).total_seconds()
        except (TypeError, ValueError):
            seconds = 2 ** attempt + random.random()
    return min(15, max(0, seconds))


async def fetch(client, reporter, root, page, retries=2):
    probes = []
    for attempt in range(retries + 1):
        started = time.perf_counter()
        probe = {'page': page, 'attempt': attempt + 1, 'observed_at': now(), 'status': 0,
                 'source_sha': None, 'http_date': None, 'error': None,
                 'url': str(httpx.URL(reporter['url'], params={'page': page, 'page-size': 1000, 'period': 'ALL'}))}
        wait = None
        transport_failed = False
        try:
            async with client.stream('GET', reporter['url'], params={'page': page, 'page-size': 1000, 'period': 'ALL'}) as response:
                probe.update(status=response.status_code, http_date=response.headers.get('date'), url=str(response.url))
                raw = bytearray()
                async for part in response.aiter_bytes():
                    raw.extend(part)
                    if len(raw) > 16 * 1024 * 1024:
                        raise ValueError('response_size_limit')
                raw = bytes(raw)
                probe['source_sha'] = put(root, raw)
                probe['bytes'] = len(raw)
                if response.status_code != 200:
                    probe['error'] = 'http_' + str(response.status_code)
                wait = response.headers.get('retry-after')
        except httpx.TransportError as error:
            transport_failed = True
            probe['error'] = str(error)[:300] or type(error).__name__
            raw = None
        except (httpx.HTTPError, ValueError) as error:
            probe['error'] = str(error)[:300] or type(error).__name__
            raw = None
        probe['duration_ms'] = round((time.perf_counter() - started) * 1000, 2)
        probes.append(probe)
        if (transport_failed or probe['status'] in (408, 429, 500, 502, 503, 504, 529) or probe['status'] == 0) and attempt < retries:
            await asyncio.sleep(delay(wait, attempt))
            continue
        return raw, probes


async def capture(client, reporter, root, max_pages=20, retries=2):
    validate_reporter(reporter)
    result = {**reporter, 'observed_at': now(), 'probes': [], 'issues': [], 'rows': [],
              'complete': False, 'coverage_reconciled': False, 'coverage': 'unknown', 'status': 0, 'http_date': None}
    unique = {}
    for page in range(1, max_pages + 1):
        raw, probes = await fetch(client, reporter, root, page, retries)
        result['probes'].extend(probes)
        last = probes[-1]
        result.update(status=last['status'], http_date=last['http_date'])
        if last['error']:
            result['issues'].append(last['error'])
            break
        try:
            payload = json.loads(raw)
            if not isinstance(payload, dict) or not isinstance(payload.get('data'), list):
                raise ValueError('data_not_array')
            meta = payload.get('meta', {})
            if not isinstance(meta, dict):
                raise ValueError('meta_not_object')
            total = meta.get('totalRecords')
            pages = meta.get('totalPages')
            if any(v is not None and (type(v) is not int or v < 0) for v in (total, pages)):
                raise ValueError('invalid_totals')
            if page == 1 and not payload['data']:
                result['issues'].append('empty_report')
            added = 0
            for index, row in enumerate(payload['data']):
                if not isinstance(row, dict) or endpoint_parts(row.get('endpoint')) is None:
                    result['issues'].append('invalid_endpoint_record')
                    continue
                key = row['endpoint']
                if key in unique:
                    result['issues'].append('duplicate_endpoint')
                    old = {k: v for k, v in unique[key]['record'].items() if k != 'requestTime'}
                    new = {k: v for k, v in row.items() if k != 'requestTime'}
                    if sha(encoded(old)) != sha(encoded(new)):
                        result['issues'].append('conflicting_endpoint')
                        unique[key]['ambiguous'] = True
                    continue
                unique[key] = {'record': row, 'source_sha': last['source_sha'], 'json_path': f'$.data[{index}]'}
                added += 1
            if len(unique) > 10000:
                raise ValueError('record_limit')
            if total is not None and len(unique) >= total:
                result['coverage_reconciled'] = len(unique) == total
                result['complete'] = bool(unique) and result['coverage_reconciled'] and not {'invalid_endpoint_record', 'conflicting_endpoint'}.intersection(result['issues'])
                result['coverage'] = 'reported_total_reconciled' if result['complete'] else 'total_mismatch'
                if not unique and 'empty_report' in result['issues']:
                    result['coverage'] = 'empty_response'
                if pages and page < pages:
                    result['issues'].append('page_metadata_conflict')
                break
            if not added:
                result['issues'].append('pagination_no_new_identity')
                result['coverage'] = 'unconfirmed'
                break
            if pages and page >= pages:
                result['issues'].append('total_mismatch' if total is not None else 'missing_total')
                result['coverage'] = 'unconfirmed'
                break
        except (ValueError, TypeError) as error:
            result['issues'].append(str(error))
            break
    else:
        result['issues'].append('page_limit')
    result['rows'] = list(unique.values())
    result['issues'] = sorted(set(result['issues']))
    result['probe_ms'] = result['probes'][-1]['duration_ms'] if result['probes'] else None
    result['data_status'] = outcome(result)
    result['usable'] = result['data_status'] == 'valid'
    return result


async def collect(reporters, root, transport=None, previous_ids=None, empty_retry_delays=(10, 30)):
    semaphore = asyncio.Semaphore(4)
    context = truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    async with httpx.AsyncClient(verify=context, timeout=20, http2=True, follow_redirects=False,
                                transport=transport, limits=httpx.Limits(max_connections=4),
                                headers={'User-Agent': 'SantanderAdminMetrics/1.0'}) as client:
        async def worker(reporter):
            attempts = []
            delays = empty_retry_delays if reporter['id'] in (previous_ids or set()) else ()
            for capture_attempt in range(len(delays) + 1):
                async with semaphore:
                    result = await capture(client, reporter, root)
                attempts.extend({**p, 'capture_attempt': capture_attempt + 1,
                                 'data_status': result['data_status'] if p is result['probes'][-1]
                                 else 'transport_error' if p['status'] == 0 or (p.get('error') and p['status'] == 200)
                                 else 'http_error' if p['status'] != 200 else 'received'}
                                for p in result['probes'])
                if result['data_status'] != 'empty' or capture_attempt == len(delays):
                    break
                # Waiting for a source must not occupy another source's capture slot.
                await asyncio.sleep(delays[capture_attempt])
            result['probes'] = attempts
            result['empty_retry_count'] = capture_attempt
            if capture_attempt and result['usable']:
                result['issues'] = sorted(set(result['issues']) | {'empty_response_recovered'})
            print(json.dumps({'event': 'report', 'reporter': reporter['id'], 'status': result['status'],
                              'records': len(result['rows']), 'data_status': result['data_status'],
                              'empty_retries': result['empty_retry_count'], 'issues': result['issues']}), flush=True)
            return result
        return await asyncio.gather(*(worker(r) for r in reporters))
