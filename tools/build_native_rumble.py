"""Build an SDL forwarding shim against the exact staged official DLL."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import struct
import tempfile
import pefile

ROOT = Path(__file__).resolve().parent.parent

def install_rumble(package):
    package = Path(package).resolve()
    binary = package / 'bin'
    official = binary / 'SDL3.dll'
    real = binary / 'SDL3-real.dll'
    if real.exists():
        # An existing shim must never become the next forwarding target.
        pe = pefile.PE(str(official))
        is_shim = any(e.forwarder and b'SDL3-real.' in e.forwarder for e in pe.DIRECTORY_ENTRY_EXPORT.symbols)
        pe.close()
        if is_shim:
            raise RuntimeError('Rumble shim is already installed; stage a fresh official SDL3.dll first')
    pe = pefile.PE(str(official))
    symbols = pe.DIRECTORY_ENTRY_EXPORT.symbols
    names = {s.name.decode('ascii') for s in symbols if s.name}
    pe.close()
    required = {'SDL_OpenGamepad', 'SDL_RumbleGamepad', 'SDL_GetGamepadProperties', 'SDL_GetBooleanProperty'}
    if not required <= names or any(not s.name for s in symbols):
        raise RuntimeError('Unexpected SDL export ABI; refusing installation')
    source = ROOT / 'local-customizations/native-rumble'
    zig = ROOT / 'tools-local/zig/ziglang/zig.exe'
    with tempfile.TemporaryDirectory(prefix='rumble-build-') as temporary:
        work = Path(temporary)
        definition = work / 'SDL3.def'
        lines = ['LIBRARY SDL3', 'EXPORTS']
        for s in symbols:
            name = s.name.decode('ascii')
            target = '' if name in required & {'SDL_OpenGamepad', 'SDL_RumbleGamepad'} else '=SDL3-real.' + name
            lines.append(f'{name}{target} @{s.ordinal}')
        definition.write_text('\n'.join(lines) + '\n', encoding='ascii')
        common = [str(zig), 'cc', '-target', 'x86_64-windows-gnu', '-O2']
        subprocess.run(common + ['-shared', str(source / 'rumble.c'), str(definition), '-o', str(work / 'SDL3.dll')], check=True)
        subprocess.run(common + [str(source / 'test.c'), '-o', str(work / 'rumble-test.exe')], check=True)
        built_path = work / 'SDL3.dll'
        built = pefile.PE(str(built_path))
        actual = {s.name.decode('ascii'): s for s in built.DIRECTORY_ENTRY_EXPORT.symbols if s.name}
        # LLD assigns fresh ordinals to forwarded exports even with explicit .def
        # ordinals. Reorder the parsed PE export tables; no fixed binary offsets.
        export = built.DIRECTORY_ENTRY_EXPORT.struct
        base = min(s.ordinal for s in symbols)
        span = max(s.ordinal for s in symbols) - base + 1
        if span > export.NumberOfFunctions:
            built.close()
            raise RuntimeError('Insufficient export table capacity to preserve SDL ordinals')
        addresses = [0] * span
        original_ordinals = {s.name.decode('ascii'): s.ordinal for s in symbols}
        for s in symbols:
            addresses[s.ordinal - base] = actual[s.name.decode('ascii')].address
        built.set_bytes_at_rva(export.AddressOfFunctions, struct.pack('<' + 'I' * span, *addresses))
        for index in range(export.NumberOfNames):
            name_rva = built.get_dword_at_rva(export.AddressOfNames + index * 4)
            name = built.get_string_at_rva(name_rva).decode('ascii')
            built.set_bytes_at_rva(export.AddressOfNameOrdinals + index * 2,
                                   struct.pack('<H', original_ordinals[name] - base))
        export.Base = base
        export.NumberOfFunctions = span
        data = built.write()
        built.close()
        built_path.write_bytes(data)
        built = pefile.PE(str(built_path))
        actual = {s.name.decode('ascii'): s for s in built.DIRECTORY_ENTRY_EXPORT.symbols if s.name}
        built.close()
        if set(actual) != names:
            raise RuntimeError('SDL export set changed')
        for s in symbols:
            name = s.name.decode('ascii')
            assert actual[name].ordinal == s.ordinal
            if name not in {'SDL_OpenGamepad', 'SDL_RumbleGamepad'}:
                assert actual[name].forwarder == ('SDL3-real.' + name).encode('ascii')
        shutil.copy2(official, real)
        shutil.copy2(work / 'SDL3.dll', official)
        shutil.copy2(work / 'rumble-test.exe', binary / 'rumble-test.exe')
    report = {'official_sha256': hashlib.sha256(real.read_bytes()).hexdigest(),
              'shim_sha256': hashlib.sha256(official.read_bytes()).hexdigest(), 'exports': len(names)}
    (binary / 'rumble-installed.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    return report

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('package', type=Path)
    print(install_rumble(parser.parse_args().package))
