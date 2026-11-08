"""One-session watcher for a game already running when the backup feature was installed."""
import argparse
import ctypes
from ctypes import wintypes
from datetime import datetime
from pathlib import Path

from exit_save_backup import safe_backup_on_exit


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--pid', type=int, required=True)
    parser.add_argument('--user', type=Path, required=True)
    args = parser.parse_args()
    kernel = ctypes.windll.kernel32
    kernel.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    kernel.OpenProcess.restype = wintypes.HANDLE
    kernel.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
    kernel.GetExitCodeProcess.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD)]
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    handle = kernel.OpenProcess(0x00100000 | 0x1000, False, args.pid)
    args.user.mkdir(parents=True, exist_ok=True)
    log_path = args.user / 'exit-backup-watcher.log'
    with log_path.open('a', encoding='utf-8', buffering=1) as log:
        if not handle:
            log.write(f'{datetime.now().isoformat()} Could not watch process {args.pid}; no backup made\n')
            return 1
        try:
            log.write(f'{datetime.now().isoformat()} Watching game PID {args.pid}; no snapshot until exit\n')
            if kernel.WaitForSingleObject(handle, 0xffffffff) != 0:
                raise OSError('Failed waiting for game exit')
            code = wintypes.DWORD()
            if not kernel.GetExitCodeProcess(handle, ctypes.byref(code)):
                raise OSError('Failed reading game exit status')
            target = safe_backup_on_exit(args.user, code.value, args.pid)
            log.write(f'{datetime.now().isoformat()} Exit backup: {target}\n')
        finally:
            kernel.CloseHandle(handle)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
