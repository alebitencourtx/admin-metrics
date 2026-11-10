import asyncio
from datetime import datetime, timezone
import json
from pathlib import Path
import uuid

from .analysis import apply
from .archive import validate
from .build import build
from .collect import collect
from .storage import load, lock, now, write, sha, encoded


def run(root=Path('data'), output=Path('site'), config=Path('config'), refresh=True, transport=None):
    root = Path(root)
    reporters = json.loads((config / 'reporters.json').read_bytes())
    rules = json.loads((config / 'rules.json').read_bytes())
    if len({r['id'] for r in reporters}) != len(reporters) or not reporters:
        raise ValueError('Catálogo vazio ou duplicado')
    with lock(root):
        state = load(root)
        if refresh:
            observed_at = now()
            run_id = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ') + '-' + uuid.uuid4().hex[:8]
            reports = asyncio.run(collect(reporters, root, transport))
            state = apply(state, reports, rules, observed_at, run_id)
        if not state['runs']:
            raise ValueError('Nenhuma observação; execute collect primeiro')
        validate(state)
        payload = build(state, root / 'gold', output, rules, reporters)
        # State only advances after the full artifact and marts have been generated.
        write(root / 'state.json', state)
        keep = {p['source_sha'] for r in state['runs'][-2:] for report in r['reports'] for p in report['probes'] if p['source_sha']}
        # Logical retention; package excludes older objects. Local GC removes only known hash files.
        for path in (root / 'bronze').glob('*.json'):
            if path.stem not in keep and len(path.stem) == 64:
                path.unlink()
        return payload
