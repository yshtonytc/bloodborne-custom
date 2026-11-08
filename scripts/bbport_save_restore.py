"""Selectable save snapshots with verified copies and rollback; no in-game writes."""
from datetime import datetime
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import uuid

SAVE_REL = Path('savedata/1/CUSA01363/SPRJ0005')

def save_dir(user): return Path(user) / SAVE_REL

def _link(path):
    return path.is_symlink() or (hasattr(path, 'is_junction') and path.is_junction())

def _validate(path, root):
    path, root = Path(path), Path(root).resolve()
    if not path.resolve().is_relative_to(root):
        raise ValueError('Path is outside the save directory: ' + str(path))
    for item in [path, *path.parents]:
        if _link(item): raise ValueError('Linked save paths are not supported: ' + str(item))
        if item.resolve() == root: break
    if path.exists() and any(_link(p) for p in path.rglob('*')):
        raise ValueError('Save tree contains a symbolic link or junction: ' + str(path))
    return path

def inventory(path):
    path = Path(path)
    _validate(path, path)
    result = {}
    for file in sorted(path.rglob('*')):
        if file.is_file():
            digest = hashlib.sha256()
            with file.open('rb') as stream:
                for block in iter(lambda: stream.read(1024 * 1024), b''): digest.update(block)
            result[file.relative_to(path).as_posix()] = {'size': file.stat().st_size, 'sha256': digest.hexdigest()}
    return result

def describe(path):
    path = Path(path)
    _validate(path, path)
    files = [p for p in path.rglob('*') if p.is_file()]
    return {'files': len(files), 'bytes': sum(p.stat().st_size for p in files),
            'titles': ['CUSA01363'] if (path / 'userdata0000').is_file() else [],
            'modified': max((p.stat().st_mtime for p in files), default=0)}

def discover(user_dir, port_dir):
    user, port = Path(user_dir).resolve(), Path(port_dir).resolve()
    roots = [(user / 'exit-save-backups', 'exit'), (port.parent.parent / 'save-copies', 'manual'),
             (user / 'save-restore-safety', 'safety')]
    seen, entries = set(), []
    for root, kind in roots:
        if not root.is_dir(): continue
        _validate(root, root)
        for folder in root.iterdir():
            if not folder.is_dir() or folder.name.startswith('.'): continue
            candidates = [folder / SAVE_REL]
            if kind == 'manual': candidates.insert(0, folder / 'SPRJ0005')
            path = next((p for p in candidates if (p / 'userdata0000').is_file()), None)
            if path is None or str(path.resolve()) in seen: continue
            seen.add(str(path.resolve()))
            try:
                info = describe(path)
                if not info['files']: continue
            except (OSError, ValueError):
                continue
            stamp = re.search(r'[0-9]{8}-[0-9]{6}', folder.name)
            try: when = datetime.strptime(stamp[0], '%Y%m%d-%H%M%S') if stamp else datetime.fromtimestamp(info['modified'])
            except ValueError: when = datetime.fromtimestamp(info['modified'])
            manifest = folder / 'backup.json'
            entries.append({'path': str(path), 'name': folder.name, 'kind': kind,
                            'manifest': str(manifest) if manifest.is_file() else None,
                            'time': when.strftime('%Y-%m-%d %H:%M:%S'), **info})
    return sorted(entries, key=lambda e: (e['time'], e['name']), reverse=True)

def verify_record(entry, actual):
    """Exit snapshots already have SHA-256 records; reject corruption before touching current saves."""
    if not entry.get('manifest'): return
    record = json.loads(Path(entry['manifest']).read_text(encoding='utf-8'))
    if 'sha256' in record:
        prefix = '1/CUSA01363/SPRJ0005/'
        expected = {name[len(prefix):]: value for name, value in record['sha256'].items() if name.startswith(prefix)}
        if expected != {name: value['sha256'] for name, value in actual.items()}:
            raise ValueError('备份与原始 SHA-256 记录不一致，已停止恢复。')
    elif 'files' in record:
        if record['files'] != actual: raise ValueError('安全副本校验失败，已停止恢复。')
    else:
        raise ValueError('无法识别备份的校验记录，已停止恢复。')

def assert_game_closed(port_dir):
    if os.name != 'nt': raise RuntimeError('This restore helper supports Windows only')
    code = "$p=@(Get-CimInstance Win32_Process | Where-Object {$_.ExecutablePath -like ($env:SP_SAVE_PORT+'\\*') -and $_.Name -match '^bb-probe\\.exe$'}); if($p.Count){Write-Output 'GAME_RUNNING'}"
    result = subprocess.run(['powershell.exe', '-NoProfile', '-Command', code],
        env=dict(os.environ, SP_SAVE_PORT=str(Path(port_dir).resolve())), capture_output=True, text=True,
        timeout=15, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    if result.returncode: raise RuntimeError('Could not check the game process: ' + result.stderr.strip())
    if 'GAME_RUNNING' in result.stdout: raise RuntimeError('Close the game before restoring saves.')

def _remove(path, root):
    _validate(path, root)
    if path.exists(): shutil.rmtree(path)

def _safety_copy(user, savedata):
    if not savedata.exists(): return None
    original = inventory(savedata)
    if not original: return None
    root = user / 'save-restore-safety'
    root.mkdir(exist_ok=True)
    _validate(root, user)
    name = datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    pending = root / ('.pending-' + name)
    final = root / name
    try:
        shutil.copytree(savedata, pending / SAVE_REL)
        if inventory(pending / SAVE_REL) != original: raise OSError('Safety backup checksum mismatch')
        (pending / 'backup.json').write_text(json.dumps({'type': 'before-restore', 'created': datetime.now().isoformat(),
            'files': original}, ensure_ascii=False, indent=2), encoding='utf-8')
        pending.rename(final)
        return final
    finally:
        if pending.exists(): _remove(pending, user)

@contextmanager
def _restore_lock(user):
    import msvcrt
    path = _validate(user / '.save-restore.lock', user)
    with path.open('a+b') as stream:
        if stream.tell() == 0:
            stream.write(b'0')
            stream.flush()
        stream.seek(0)
        try:
            msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
        except OSError:
            raise RuntimeError('Another save restoration is already running.') from None
        try:
            yield
        finally:
            stream.seek(0)
            msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)

def restore(user_dir, port_dir, source, check_closed=None):
    user = Path(user_dir).resolve()
    closed = check_closed or (lambda: assert_game_closed(port_dir))
    closed()
    user.mkdir(parents=True, exist_ok=True)
    with _restore_lock(user):
        return _restore(user, port_dir, source, closed)

def _restore(user_dir, port_dir, source, check_closed):
    user, port = Path(user_dir).resolve(), Path(port_dir).resolve()
    closed = check_closed or (lambda: assert_game_closed(port))
    source = Path(source).resolve()
    allowed = {Path(e['path']): e for e in discover(user, port)}
    if source not in allowed: raise ValueError('The selected backup is no longer available')
    expected = inventory(source)
    if not expected: raise ValueError('The selected backup contains no save files')
    verify_record(allowed[source], expected)
    user.mkdir(parents=True, exist_ok=True)
    savedata = _validate(save_dir(user), user)
    safety = _safety_copy(user, savedata)
    token = uuid.uuid4().hex
    stage = user / ('.restore-' + token)
    previous = user / ('.save-before-restore-' + token)
    try:
        shutil.copytree(source, stage / 'SPRJ0005')
        if inventory(stage / 'SPRJ0005') != expected: raise OSError('Restore staging checksum mismatch')
        closed()  # Catch games started while the verified copies were being prepared.
        savedata.parent.mkdir(parents=True, exist_ok=True)
        if savedata.exists(): savedata.rename(previous)
        try:
            (stage / 'SPRJ0005').rename(savedata)
        except Exception:
            if previous.exists() and not savedata.exists(): previous.rename(savedata)
            raise
        if inventory(savedata) != expected:
            raise OSError('Final verification failed; original saves remain at ' + str(previous))
        if previous.exists(): _remove(previous, user)
        return {'source': str(source), 'safety': str(safety) if safety else None, 'files': len(expected)}
    finally:
        if stage.exists(): _remove(stage, user)
