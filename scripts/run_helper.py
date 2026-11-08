# SPDX-License-Identifier: GPL-2.0-or-later
"""Run a preparation helper with a consistent UTF-8 pipe protocol.

PyInstaller can ignore PYTHONIOENCODING. Set the streams explicitly even when
using the existing packaged launcher, whose LossyStream swallows encoding errors.
"""
import runpy
import sys


def main():
    for stream in (sys.stdout, sys.stderr):
        if stream is not None and hasattr(stream, 'reconfigure'):
            stream.reconfigure(encoding='utf-8', errors='strict', line_buffering=True)
    if len(sys.argv) < 2:
        raise SystemExit('Usage: run_helper.py SCRIPT [ARGS...]')
    sys.argv = sys.argv[1:]
    runpy.run_path(sys.argv[0], run_name='__main__')


if __name__ == '__main__':
    main()
