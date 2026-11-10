"""Bounded, checksummed state transport. Never extract arbitrary ZIP paths."""
import json
from pathlib import Path
import re
import zipfile

from .storage import atomic, encoded, load, sha

HEX = re.compile(r'^[0-9a-f]{64}$')
MAX_ARCHIVE = 300 * 1024**2
MAX_EXPANDED = 512 * 1024**2


def recent_objects(state):
    return {p['source_sha'] for run in state['runs'][-2:] for report in run['reports']
            for p in report['probes'] if p.get('source_sha')}


def validate(state):
    if state.get('version') != 1 or any(not isinstance(state.get(k), list) for k in ('runs','observations','incidents','latest_rows')):
        raise ValueError('Contrato de estado inválido')
    if not state['runs']:
        raise ValueError('Estado sem execuções')
    runs = [r['run_id'] for r in state['runs']]
    if len(runs) != len(set(runs)):
        raise ValueError('Execuções duplicadas')
    identities = [(r['run_id'],r['entity_id']) for r in state['observations']]
    if len(identities) != len(set(identities)) or any(r not in runs for r,_ in identities):
        raise ValueError('Identidades ou referências inválidas')
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
    if sum(map(len,files.values()))>MAX_EXPANDED:
        raise ValueError('Estado excede limite de transporte')
    output.parent.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(output,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as archive:
        for name,raw in sorted(files.items()):
            archive.writestr(name,raw)
    if output.stat().st_size>MAX_ARCHIVE:
        raise ValueError('Arquivo excede limite')
    atomic(output.parent/'SHA256SUMS',(sha(output.read_bytes())+'  '+output.name+'\n').encode())
    return manifest


def restore(package, checksum, root):
    package,checksum,root=Path(package),Path(checksum),Path(root)
    if (root/'state.json').exists() or any((root/'bronze').glob('*')):
        raise ValueError('Restaure em diretório de dados vazio')
    if package.stat().st_size>MAX_ARCHIVE:
        raise ValueError('Arquivo excede limite')
    fields=checksum.read_text().strip().split()
    if len(fields)!=2 or fields[1]!=package.name or sha(package.read_bytes())!=fields[0]:
        raise ValueError('Checksum externo inválido')
    with zipfile.ZipFile(package) as archive:
        items=archive.infolist()
        names=[i.filename for i in items]
        if len(items)>4096 or len(names)!=len(set(names)) or sum(i.file_size for i in items)>MAX_EXPANDED:
            raise ValueError('Limites de expansão / entradas inválidos')
        for item in items:
            if item.filename not in ('state.json','manifest.json') and not re.fullmatch(r'bronze/[0-9a-f]{64}\.json',item.filename):
                raise ValueError('Caminho não permitido no pacote')
            limit=256*1024**2 if item.filename=='state.json' else 16*1024**2
            if item.file_size>limit or item.flag_bits&1:
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
    # All checks precede mutation; the state pointer is committed last.
    for name,raw in files.items():
        if name!='state.json':
            atomic(root/name,raw)
    atomic(root/'state.json',files['state.json'])
    return manifest
