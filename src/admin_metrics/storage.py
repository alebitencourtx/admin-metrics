import contextlib
import hashlib
import json
import os
from pathlib import Path
import uuid
from datetime import datetime, timezone


def now():
    return datetime.now(timezone.utc).isoformat(timespec='seconds')


def encoded(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def sha_file(path, chunk_size=1024 * 1024):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(chunk_size), b''):
            digest.update(chunk)
    return digest.hexdigest()


def atomic(path, raw):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name('.' + path.name + '.' + uuid.uuid4().hex)
    try:
        with temporary.open('xb') as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def write(path, value):
    atomic(path, encoded(value))


@contextlib.contextmanager
def lock(root):
    path = Path(root) / '.writer.lock'
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError as error:
        raise RuntimeError('Escritor ativo ou lock abandonado: ' + str(path)) from error
    try:
        os.write(fd, encoded({'pid': os.getpid(), 'started_at': now()}))
        os.close(fd)
        yield
    finally:
        path.unlink(missing_ok=True)


def put(root, raw):
    digest = sha(raw)
    path = Path(root) / 'bronze' / (digest + '.json')
    if path.exists():
        if sha(path.read_bytes()) != digest:
            raise ValueError('Bronze corrompido: ' + digest)
    else:
        atomic(path, raw)
    return digest


def empty_state():
    return {'version': 1, 'runs': [], 'observations': [], 'incidents': [], 'latest_rows': []}


def load(root):
    path = Path(root) / 'state.json'
    if not path.exists():
        return empty_state()
    result = json.loads(path.read_bytes())
    if result.get('version') != 1:
        raise ValueError('Versão de estado incompatível')
    for key in ('runs', 'observations', 'incidents', 'latest_rows'):
        if not isinstance(result.get(key), list):
            raise ValueError('Estado inválido: ' + key)
    return result
