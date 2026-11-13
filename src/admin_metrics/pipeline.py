import asyncio
from datetime import datetime, timezone
import json
from pathlib import Path
import uuid

from .analysis import apply
from .archive import validate, HEX
from .build import build
from .collect import collect, validate_reporters
from .rules import validate_rules
from .storage import load, lock, now, write, sha, encoded


def run(root=Path('data'), output=Path('site'), config=Path('config'), refresh=True, transport=None, execution_url=None, execution_links=None):
    root = Path(root)
    reporters = validate_reporters(json.loads((config / 'reporters.json').read_bytes()))
    rules = validate_rules(json.loads((config / 'rules.json').read_bytes()))
    with lock(root):
        state = load(root)
        # Authoritative release receipts can restore missing legacy trace links.
        for cycle in state['runs']:
            if cycle['run_id'] in (execution_links or {}):
                cycle['execution_url'] = execution_links[cycle['run_id']]
        if refresh:
            observed_at = now()
            run_id = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ') + '-' + uuid.uuid4().hex[:8]
            previous_ids = {r['reporter_id'] for r in state['latest_rows'] if r['source_complete']}
            reports = asyncio.run(collect(reporters, root, transport, previous_ids, rules['empty_retry_delays_seconds']))
            state = apply(state, reports, rules, observed_at, run_id)
            if execution_url:
                state['runs'][-1]['execution_url'] = execution_url
        if not state['runs']:
            raise ValueError('Nenhuma observação; execute collect primeiro')
        validate(state)
        payload = build(state, root / 'gold', output, rules, reporters)
        # State only advances after the full artifact and marts have been generated.
        write(root / 'state.json', state)
        keep = {p.get('source_sha') for r in state['runs'][-2:] for report in r['reports'] for p in report['probes'] if p.get('source_sha')}
        # Logical retention; package excludes older objects. Local GC removes only known hash files.
        for path in (root / 'bronze').glob('*.json'):
            if path.stem not in keep and HEX.fullmatch(path.stem):
                path.unlink()
        return payload
