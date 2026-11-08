"""Snapshot only savedata after the native game process has exited."""
from datetime import datetime
import hashlib
import json
from pathlib import Path
import shutil
import tempfile


def file_hashes(folder):
    result = {}
    for path in sorted(Path(folder).rglob('*')):
        if path.is_symlink() or (hasattr(path, 'is_junction') and path.is_junction()):
            raise ValueError(f'Save backup cannot follow links: {path}')
        if path.is_file():
            digest = hashlib.sha256()
            with path.open('rb') as stream:
                for block in iter(lambda: stream.read(1024 * 1024), b''):
                    digest.update(block)
            result[path.relative_to(folder).as_posix()] = digest.hexdigest()
    return result


def backup_on_exit(user_dir, exit_code, game_pid):
    user_dir = Path(user_dir).resolve()
    source = user_dir / 'savedata'
    if not source.is_dir():
        return None
    expected = file_hashes(source)
    if not expected:
        return None
    backup_root = user_dir / 'exit-save-backups'
    backup_root.mkdir(parents=True, exist_ok=True)
    # Stage the entire snapshot, then publish it only after every file is verified.
    staging = Path(tempfile.mkdtemp(prefix='.pending-', dir=backup_root))
    try:
        shutil.copytree(source, staging / 'savedata')
        if file_hashes(staging / 'savedata') != expected or file_hashes(source) != expected:
            raise RuntimeError('Save changed during backup or copied files differ')
        now = datetime.now().astimezone()
        metadata = {'created_at': now.isoformat(), 'trigger': 'game_process_exited',
                    'game_pid': int(game_pid), 'exit_code': int(exit_code),
                    'source': str(source), 'file_count': len(expected), 'sha256': expected}
        (staging / 'backup.json').write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding='utf-8')
        name = now.strftime('%Y%m%d-%H%M%S-%f') + f'-pid{game_pid}'
        target = backup_root / name
        staging.rename(target)
        return target
    finally:
        if staging.exists():
            if staging.resolve().parent != backup_root.resolve() or not staging.name.startswith('.pending-'):
                raise ValueError('Unexpected backup staging path')
            shutil.rmtree(staging)


def safe_backup_on_exit(user_dir, exit_code, game_pid):
    try:
        target = backup_on_exit(user_dir, exit_code, game_pid)
        if target:
            print(f'Exit save backup: {target}', flush=True)
        else:
            print('Exit save backup: no save data found; skipped', flush=True)
        return target
    except Exception as error:
        # A failed backup must not hide or change the game's own exit status.
        message = f'Exit save backup failed: {type(error).__name__}: {error}'
        print(message, flush=True)
        try:
            with (Path(user_dir) / 'exit-save-backup-errors.log').open('a', encoding='utf-8') as stream:
                stream.write(f'{datetime.now().astimezone().isoformat()} {message}\n')
        except OSError:
            pass
        return None
