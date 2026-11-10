import json
from pathlib import Path
import shutil
import tempfile

import duckdb
import pyarrow as pa

from . import __version__
from .storage import atomic, encoded, sha

HERE = Path(__file__).parent
SCHEMA = pa.schema([(k, pa.string()) for k in ('run_id', 'entity_id', 'observed_at', 'day', 'reporter_id', 'reporter', 'endpoint', 'path', 'family')]
                   + [(k, pa.int64()) for k in ('calls', 'errors', 'rejections', 'mean_ms')]
                   + [(k, pa.float64()) for k in ('error_pct', 'rejection_pct', 'uptime')]
                   + [('source_complete', pa.bool_()), ('fresh', pa.bool_())])


def rows(db, query):
    result = db.execute(query)
    names = [c[0] for c in result.description]
    return [dict(zip(names, row)) for row in result.fetchall()]


def build(state, root, output, rules, reporters):
    root, output = Path(root), Path(output)
    root.mkdir(parents=True, exist_ok=True)
    output.mkdir(parents=True, exist_ok=True)
    run = state['runs'][-1] if state['runs'] else {'run_id': '', 'observed_at': None, 'reports': []}
    latest = [{**r, 'fresh': r['run_id'] == run['run_id']} for r in state['latest_rows']]
    db_path = root / 'warehouse.duckdb'
    db_path.unlink(missing_ok=True)
    db = duckdb.connect(str(db_path))
    try:
        db.execute("SET memory_limit='1GB'; SET threads=2")
        for name, data in [('current_rows', latest), ('observations', state['observations'])]:
            table = pa.Table.from_pylist(data, schema=SCHEMA)
            db.register('incoming', table)
            db.execute(f'CREATE TABLE {name} AS SELECT * FROM incoming')
        db.execute((HERE / 'marts.sql').read_text(encoding='utf-8'))
        payload = {name: rows(db, f'SELECT * FROM {name}') for name in ('report_summary', 'family_summary', 'observation_trends')}
        for name in ('current_rows', 'observations', 'report_summary', 'family_summary', 'observation_trends'):
            path = str(root / (name + '.parquet')).replace("'", "''")
            db.execute(f"COPY {name} TO '{path}' (FORMAT PARQUET, COMPRESSION ZSTD)")
    finally:
        db.close()
    # The previousDays arrays remain separate from our measured observation series.
    history = []
    for row in latest:
        for i, calls in enumerate(row['previous']['calls']):
            def value(key):
                return row['previous'][key][i] if i < len(row['previous'][key]) else None
            history.append({'entity_id': row['entity_id'], 'reporter_id': row['reporter_id'], 'position': i + 1,
                            'calls': calls, 'errors': value('errors'), 'rejections': value('rejections'), 'mean_ms': value('mean_ms')})
    payload.update(meta={'version': __version__, 'run_id': run['run_id'], 'observed_at': run['observed_at'],
                         'history_days': rules['retention_days'], 'schedule': '17 */2 * * * UTC',
                         'partial_day': True, 'stale_after_hours': rules['stale_after_hours']},
                   latest=latest, runs=state['runs'], incidents=state['incidents'], reported_history=history,
                   rules=rules, reporters=reporters)
    # Full observation points for endpoint drill-down, not repeated daily sums.
    payload['points'] = [{k: r.get(k) for k in ('entity_id', 'observed_at', 'day', 'calls', 'errors', 'error_pct', 'mean_ms', 'source_complete', 'interval_state', 'interval_error_pct')}
                         for r in state['observations']]
    from .documentation import generate
    with tempfile.TemporaryDirectory(dir=output.parent, prefix='.admin-stage-') as temporary:
        stage = Path(temporary)
        for source in (HERE / 'web').iterdir():
            if source.is_file():
                shutil.copyfile(source, stage / source.name)
        raw = encoded(payload)
        atomic(stage / 'data.js', b'window.ADMIN_DATA=' + raw + b';\n')
        atomic(stage / 'dashboard.json', raw)
        generate(payload, stage / 'documentacao.html')
        asset_id = sha(b''.join(p.read_bytes() for p in sorted(stage.iterdir())))[:20]
        destination = output / 'assets' / asset_id
        destination.parent.mkdir(exist_ok=True)
        if not destination.exists():
            stage.rename(destination)
            stage.mkdir()
        html = (destination / 'index.html').read_text(encoding='utf-8')
        for asset in ('app.js', 'styles.css', 'data.js'):
            html = html.replace('"' + asset + '"', '"assets/' + asset_id + '/' + asset + '"')
        atomic(output / 'documentacao.html', (destination / 'documentacao.html').read_bytes())
        atomic(output / 'dashboard.json', raw)
        atomic(output / '.nojekyll', b'')
        atomic(output / 'index.html', html.encode())
    return payload
