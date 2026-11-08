# SPDX-License-Identifier: GPL-2.0-or-later
"""Check compressed shaders before launch; ported from upstream scripts/game_check.py.

Based on deadinside28/bloodborne_pc at 3c57da41 (issue #81). Only resource
integrity is checked here; Windows retains its existing non-1.09 fallback.
Unknown compression formats are left to the game's decoder.
"""
from pathlib import Path
import struct
import zlib

CHECKED_FOLDER = 'dvdroot_ps4/shader'


def dcx_broken(path):
    data = Path(path).read_bytes()
    if data[:4] != b'DCX\0':
        return False
    if len(data) < 0x2C:
        return True
    if data[0x18:0x1C] != b'DCS\0' or data[0x28:0x2C] != b'DFLT':
        return False
    if len(data) < 0x4C:
        return True
    size, packed = struct.unpack_from('>II', data, 0x1C)
    if packed > len(data) - 0x4C:
        return True
    decoder = zlib.decompressobj()
    payload = data[0x4C:0x4C + packed]
    total = 0
    try:
        # Count output in bounded chunks instead of allocating the decompressed shader bundle.
        while payload:
            total += len(decoder.decompress(payload, 1024 * 1024))
            if total > size:
                return True
            payload = decoder.unconsumed_tail
        return not decoder.eof or bool(decoder.unused_data) or total != size
    except zlib.error:
        return True


def broken_files(game):
    root = Path(game)
    folder = root / CHECKED_FOLDER
    return [f.relative_to(root).as_posix() for f in sorted(folder.rglob('*'))
            if f.is_file() and f.suffix.lower() == '.dcx' and dcx_broken(f)]
