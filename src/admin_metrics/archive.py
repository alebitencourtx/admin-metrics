"""Bounded, checksummed state transport. Never extract arbitrary ZIP paths."""
import json
import os
from pathlib import Path
import re
import uuid
import zipfile

from .analysis import SUPPORTED_MODEL_VERSIONS
from .storage import atomic, encoded, load, sha, sha_file

HEX = re.compile(r'^[0-9a-f]{64}$')
MAX_ARCHIVE = 300 * 1024**2
MAX_EXPANDED = 512 * 1024**2
MAX_STATE = 512 * 1024**2
MAX_OBJECT = 16 * 1024**2
MAX_ENTRIES = 4096


def validate_entries(entries):
    if len(entries) > MAX_ENTRIES or sum(entries.values()) > MAX_EXPANDED:
        raise ValueError('Limites de expansão / entradas inválidos')
    for name, size in entries.items():
        if name not in ('state.json', 'manifest.json') and not re.fullmatch(r'bronze/[0-9a-f]{64}\.json', name):
            raise ValueError('Caminho não permitido no pacote')
        if size > (MAX_STATE if name == 'state.json' else MAX_OBJECT):
            raise ValueError('Entrada fora dos limites: ' + name)


def recent_objects(state):
    return {p['source_sha'] for run in state['runs'][-2:] for report in run['reports']
            for p in report['probes'] if p.get('source_sha')}


def validate(state):
    if state.get('version') != 1 or any(not isinstance(state.get(k), list) for k in ('runs','observations','incidents','latest_rows')):
        raise ValueError('Contrato de estado inválido')
    if not state['runs']:
        raise ValueError('Estado sem execuções')
    for run in state['runs']:
        model = run.get('model_version')
        if model is not None and (type(model) is not int or model not in SUPPORTED_MODEL_VERSIONS):
            raise ValueError('Modelo de estado incompatível: ' + str(model))
    run_ids = [r['run_id'] for r in state['runs']]
    runs = set(run_ids)
    if len(run_ids) != len(runs):
        raise ValueError('Execuções duplicadas')
    identities = [(r['run_id'],r['entity_id']) for r in state['observations']]
    if len(identities) != len(set(identities)) or any(r not in runs for r,_ in identities):
        raise ValueError('Identidades ou referências inválidas')
    if any(r['run_id'] not in runs for r in state['latest_rows']):
        raise ValueError('Referências atuais inválidas')
    ids=[i['id'] for i in state['incidents']]
    if len(ids)!=len(set(ids)):
        raise ValueError('Ocorrência duplicada')
    for digest in recent_objects(state):
        if not isinstance(digest,str) or not HEX.fullmatch(digest):
            raise ValueError('Hash bronze inválido')
    return state


def pack(root, output):
    root, output = Path(root),Path(output)
    state=validate(load(root))
    files={'state.json':encoded(state)}
    for digest in recent_objects(state):
        raw=(root/'bronze'/(digest+'.json')).read_bytes()
        if sha(raw)!=digest:
            raise ValueError('Bronze corrompido')
        files['bronze/'+digest+'.json']=raw
    manifest={'version':1,'run_id':state['runs'][-1]['run_id'], 'files':{name:sha(raw) for name,raw in files.items()}}
    files['manifest.json']=encoded(manifest)
    validate_entries({name: len(raw) for name, raw in files.items()})
    output.parent.mkdir(parents=True,exist_ok=True)
    temporary = output.with_name('.' + output.name + '.' + uuid.uuid4().hex)
    try:
        with zipfile.ZipFile(temporary,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as archive:
            for name,raw in sorted(files.items()):
                archive.writestr(name,raw)
        if temporary.stat().st_size>MAX_ARCHIVE:
            raise ValueError('Arquivo excede limite')
        os.replace(temporary, output)
    finally:
        temporary.unlink(missing_ok=True)
    atomic(output.parent/'SHA256SUMS',(sha_file(output)+'  '+output.name+'\n').encode())
    return manifest


def restore(package, checksum, root):
    package,checksum,root=Path(package),Path(checksum),Path(root)
    if (root/'state.json').exists() or any((root/'bronze').glob('*')):
        raise ValueError('Restaure em diretório de dados vazio')
    if package.stat().st_size>MAX_ARCHIVE:
        raise ValueError('Arquivo excede limite')
    fields=checksum.read_text().strip().split()
    if len(fields)!=2 or fields[1]!=package.name or sha_file(package)!=fields[0]:
        raise ValueError('Checksum externo inválido')
    with zipfile.ZipFile(package) as archive:
        items=archive.infolist()
        names=[i.filename for i in items]
        if len(names)!=len(set(names)):
            raise ValueError('Limites de expansão / entradas inválidos')
        validate_entries({i.filename: i.file_size for i in items})
        for item in items:
            if item.flag_bits&1:
                raise ValueError('Entrada fora dos limites')
        manifest=json.loads(archive.read('manifest.json'))
        if manifest.get('version')!=1 or set(manifest.get('files',{}))!=set(names)-{'manifest.json'}:
            raise ValueError('Manifesto incompatível')
        files={name:archive.read(name) for name in manifest['files']}
        if any(sha(raw)!=manifest['files'][name] for name,raw in files.items()):
            raise ValueError('Checksum interno inválido')
        state=validate(json.loads(files['state.json']))
        if state['runs'][-1]['run_id']!=manifest['run_id']:
            raise ValueError('Run do manifesto divergente')
        expected={'bronze/'+s+'.json' for s in recent_objects(state)}
        if set(files)-{'state.json'}!=expected:
            raise ValueError('Referências bronze não conciliadas')
        if any(sha(files['bronze/'+s+'.json'])!=s for s in recent_objects(state)):
            raise ValueError('Hash de origem divergente')
    # All checks precede mutation; the state pointer is committed last and
    # files written in this attempt are rolled back if the commit fails.
    written=[]
    try:
        for name,raw in files.items():
            if name!='state.json':
                target=root/name
                atomic(target,raw)
                written.append(target)
        atomic(root/'state.json',files['state.json'])
    except Exception:
        for path in reversed(written):
            path.unlink(missing_ok=True)
        raise
    return manifest
