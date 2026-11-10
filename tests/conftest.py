from copy import deepcopy
import json
from pathlib import Path

import pytest

from admin_metrics.storage import encoded, put


@pytest.fixture
def rules():
    return json.loads(Path('config/rules.json').read_bytes())


@pytest.fixture
def reporter():
    return json.loads(Path('config/reporters.json').read_bytes())[0]


def record(calls=1000, errors=100, mean=300, endpoint='https://service.example/open-banking/accounts/v2/accounts'):
    result={'endpoint':endpoint,'requestTime':'2026-11-10T18:00:00Z',
            'availability':{'uptime':{'uptimeRate':'1.0','generalUptimeRate':'1.0'},
                            'downtime':{'partialDowntime':0,'generalDowntime':0,'scheduledOutage':0}}}
    for k,v in [('invocations',calls),('errors',errors),('rejections',0),('averageResponse',mean),('averageTps',2),('peakTps',3)]:
        result[k]={'currentDay':v,'previousDays':[v,v,v]}
    return result


def report(reporter, root, records=None, observed='2026-11-10T18:00:00+00:00', status=200, complete=True):
    records=records if records is not None else [record()]
    raw=encoded({'data':records,'meta':{'totalRecords':len(records),'totalPages':1}})
    digest=put(root,raw)
    return {**deepcopy(reporter),'observed_at':observed,'status':status,'complete':complete,
            'coverage':'reported_total_reconciled' if complete else 'unknown','issues':[] if status==200 else ['http_'+str(status)],
            'http_date':None,'probe_ms':10,'probes':[{'source_sha':digest,'status':status,'duration_ms':10,'page':1,'attempt':1}],
            'rows':[{'record':r,'source_sha':digest,'json_path':f'$.data[{i}]'} for i,r in enumerate(records)]}
