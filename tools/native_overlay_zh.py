"""Localize native bbport ImGui text references and its embedded font.

No string is overwritten in its original slot. Translations live after a smaller
Chinese font in the existing embedded-font allocation. Only verified LEA RIP
displacements, relocated string pointers, and compiler relative-string tables
are redirected. No instructions are inserted and no branch targets are changed.
"""
import argparse
from io import BytesIO
import hashlib
import json
import os
from pathlib import Path
import re
import struct

from capstone import Cs, CS_ARCH_X86, CS_MODE_64
from capstone.x86 import X86_OP_MEM, X86_REG_RIP
from fontTools import subset
from fontTools.ttLib import TTFont
import pefile

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / 'local-customizations/native-overlay'


def checksum(data):
    return hashlib.sha256(data).hexdigest()


def make_font(translations):
    characters = set(''.join(translations.values())) | set(chr(c) for c in range(32, 256))
    characters.update('↑↓←→×−—…□■℃°')
    path = os.environ.get('BBPORT_CHINESE_FONT', 'C:/Windows/Fonts/msyh.ttc')
    font = TTFont(path, fontNumber=0 if path.lower().endswith('.ttc') else -1)
    if 'fvar' in font:
        from fontTools.varLib.instancer import instantiateVariableFont
        font = instantiateVariableFont(font, {'wght':400}, inplace=True)
    required = {ord(c) for c in ''.join(translations.values()) if not c.isspace()}
    if required - set(font.getBestCmap()):
        raise RuntimeError('System font lacks required translated characters')
    options = subset.Options()
    sub = subset.Subsetter(options=options)
    sub.populate(unicodes={ord(c) for c in characters})
    sub.subset(font)
    stream = BytesIO()
    font.save(stream)
    result = stream.getvalue()
    assert required <= set(TTFont(BytesIO(result)).getBestCmap())
    return result


def patch_overlay(source, destination, report_path=None, *, picker_glyph_ranges=False):
    source, destination = Path(source), Path(destination)
    original = source.read_bytes()
    if report_path and Path(report_path).is_file():
        previous = json.loads(Path(report_path).read_text(encoding='utf-8'))
        if previous.get('localized_sha256') == checksum(original):
            if source.resolve() != destination.resolve():
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_bytes(original)
            return previous
    translations = json.loads((ASSETS / 'strings-zh.json').read_text(encoding='utf-8'))
    token = re.compile(r'%(?:[-+ #0]*\d*(?:\.\d+)?(?:ll|l|z)?[sdifuxXpc])')
    for english, chinese in translations.items():
        if token.findall(english) != token.findall(chinese):
            raise RuntimeError(f'Format placeholders differ: {english}')
        if '###' in english and english.split('###', 1)[1] != chinese.split('###', 1)[1]:
            raise RuntimeError('ImGui widget ID changed')
    original_font = (ASSETS / 'original-font.ttf').read_bytes()
    if original.count(original_font) != 1:
        raise RuntimeError('Native font signature differs; refusing an unverified native patch')
    font_offset = original.index(original_font)
    localized_font = make_font(translations)
    string_start = (len(localized_font) + 15) & ~15
    pe = pefile.PE(data=original)
    base = pe.OPTIONAL_HEADER.ImageBase
    font_rva = pe.get_rva_from_offset(font_offset)
    font_section = pe.get_section_by_rva(font_rva)
    if font_section.Characteristics & 0x20000000:
        raise RuntimeError('Embedded font unexpectedly lies in executable memory')
    data = bytearray(original)
    data[font_offset:font_offset + len(original_font)] = localized_font.ljust(len(original_font), b'\0')
    pool = bytearray()
    mapping, names, references, missing = {}, {}, {}, []
    for english, chinese in translations.items():
        encoded = chinese.encode('utf-8') + b'\0'
        translated_va = base + font_rva + string_start + len(pool)
        found = False
        for section in pe.sections:
            if section.Characteristics & 0x20000000 or not section.SizeOfRawData:
                continue
            start = section.PointerToRawData
            raw = original[start:start + section.SizeOfRawData]
            needle = english.encode('utf-8') + b'\0'
            position = 0
            while (position := raw.find(needle, position)) >= 0:
                va = base + section.VirtualAddress + position
                mapping[va], names[va], references[va] = translated_va, english, 0
                found = True
                position += len(needle)
        if found:
            pool.extend(encoded)
        else:
            missing.append(english)
    glyph_key = None
    if picker_glyph_ranges:
        # New upstream builds use an explicit Cyrillic range plus FSR picker text.
        # Redirect the uniquely identified range reference to exact translated
        # glyphs, rather than loading every CJK character from Windows fonts.
        signature = struct.pack('<9H',0x20,0xff,0x400,0x52f,0x2de0,0x2dff,0xa640,0xa69f,0)
        if original.count(signature) != 1:
            raise RuntimeError('Native Cyrillic glyph-range signature differs')
        offset = original.index(signature)
        section = pe.get_section_by_rva(pe.get_rva_from_offset(offset))
        if section.Characteristics & 0x20000000:
            raise RuntimeError('Native glyph ranges unexpectedly executable')
        # Keep the original ranges and add individual translation glyphs; the
        # builder unions them into its own persistent sorted range vector.
        codes = sorted({ord(c) for text in translations.values() for c in text if ord(c)>255})
        if any(code>0xffff for code in codes):
            raise RuntimeError('Native translation contains unsupported non-BMP glyphs')
        words = [0x20,0xff,0x400,0x52f,0x2de0,0x2dff,0xa640,0xa69f]
        for code in codes:
            words.extend((code,code))
        words.append(0)
        if (string_start+len(pool))%2:
            pool.append(0)
        glyph_key = base+pe.get_rva_from_offset(offset)
        mapping[glyph_key] = base+font_rva+string_start+len(pool)
        references[glyph_key] = 0
        pool.extend(struct.pack('<'+'H'*len(words),*words))
    if string_start + len(pool) > len(original_font):
        raise RuntimeError('Chinese font and translation pool exceed embedded allocation')
    pool_offset = font_offset + string_start
    data[pool_offset:pool_offset + len(pool)] = pool

    disassembler = Cs(CS_ARCH_X86, CS_MODE_64)
    disassembler.detail = True
    disassembler.skipdata = True
    data_bases = set()
    instruction_edits = []
    for section in pe.sections:
        if not section.Characteristics & 0x20000000:
            continue
        for instruction in disassembler.disasm(section.get_data(), base + section.VirtualAddress):
            if instruction.mnemonic != 'lea' or instruction.disp_size != 4:
                continue
            operands = [op for op in instruction.operands if op.type == X86_OP_MEM and op.mem.base == X86_REG_RIP]
            if not operands:
                continue
            target = instruction.address + instruction.size + operands[0].mem.disp
            target_section = pe.get_section_by_rva(target - base) if target >= base else None
            if target_section and not target_section.Characteristics & 0x20000000:
                data_bases.add(target)
            if target not in mapping:
                continue
            offset = pe.get_offset_from_rva(instruction.address - base)
            relative = mapping[target] - (instruction.address + instruction.size)
            struct.pack_into('<i', data, offset + instruction.disp_offset, relative)
            reread = next(disassembler.disasm(bytes(data[offset:offset + instruction.size]), instruction.address, 1))
            assert reread.mnemonic == instruction.mnemonic and reread.size == instruction.size
            assert reread.address + reread.size + reread.operands[1].mem.disp == mapping[target]
            references[target] += 1
            instruction_edits.append(offset + instruction.disp_offset)

    pointer_edits = 0
    pointer_offsets = []
    for block in getattr(pe, 'DIRECTORY_ENTRY_BASERELOC', []):
        for entry in block.entries:
            if entry.type != 10:  # IMAGE_REL_BASED_DIR64
                continue
            offset = pe.get_offset_from_rva(entry.rva)
            value = struct.unpack_from('<Q', original, offset)[0]
            if value in mapping:
                struct.pack_into('<Q', data, offset, mapping[value])
                references[value] += 1
                pointer_edits += 1
                pointer_offsets.append(offset)

    def printable_string(va):
        if va < base:
            return False
        section = pe.get_section_by_rva(va - base)
        if not section or section.Characteristics & 0x20000000:
            return False
        try:
            offset = pe.get_offset_from_rva(va - base)
            end = original.index(b'\0', offset, min(offset + 1024, len(original)))
            value = original[offset:end]
            return bool(value) and all(32 <= c < 127 for c in value)
        except (ValueError, pefile.PEFormatError):
            return False

    # Clang may encode arrays of strings as signed offsets from a RIP-relative
    # table base instead of relocatable 64-bit pointers. Identify only tables
    # with at least two consecutive entries resolving to real text strings.
    table_edits = 0
    seen = set()
    for table_base in data_bases:
        table_offset = pe.get_offset_from_rva(table_base - base)
        items = []
        for index in range(64):
            offset = table_offset + 4 * index
            if offset + 4 > len(original):
                break
            target = table_base + struct.unpack_from('<i', original, offset)[0]
            if not printable_string(target):
                break
            items.append((offset, target))
        if len(items) < 2:
            continue
        for offset, target in items:
            if target in mapping and offset not in seen:
                struct.pack_into('<i', data, offset, mapping[target] - table_base)
                references[target] += 1
                table_edits += 1
                seen.add(offset)

    if glyph_key is not None and not references[glyph_key]:
        raise RuntimeError('Native glyph-range reference was not resolved')
    translated = {name for address, name in names.items() if references[address]}
    required = {'Upscaler', 'Preset', 'Sharpness', 'Frame generation', 'Output resolution',
                'Close', 'Quit game###bb_quit', 'Off', 'On', 'Quality', 'Balanced'}
    if not required <= translated:
        raise RuntimeError(f'Unresolved required menu labels: {sorted(required - translated)}')
    # Permit byte changes only within the font allocation and the verified
    # address operands/data references recorded above. No file size changes.
    assert len(data) == len(original)
    allowed = [(font_offset, font_offset + len(original_font))]
    allowed += [(offset, offset + 4) for offset in instruction_edits]
    allowed += [(offset, offset + 8) for offset in pointer_offsets]
    allowed += [(offset, offset + 4) for offset in seen]
    cursor = 0
    for start, end in sorted(allowed):
        if start > cursor:
            assert data[cursor:start] == original[cursor:start], 'Unexpected byte change'
        cursor = max(cursor, end)
    assert data[cursor:] == original[cursor:], 'Unexpected trailing byte change'
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(destination.suffix + '.new')
    temporary.write_bytes(data)
    temporary.replace(destination)
    report = {'original_sha256': checksum(original), 'localized_sha256': checksum(data),
              'font_bytes_original': len(original_font), 'font_bytes_chinese': len(localized_font),
              'translated_labels': sorted(translated), 'missing_literals': missing,
              'lea_string_references': len(instruction_edits), 'absolute_string_pointers': pointer_edits,
              'relative_string_table_entries': table_edits,
              'picker_glyph_ranges':picker_glyph_ranges,
              'glyph_range_references':references.get(glyph_key,0),
              'unreferenced_literals': sorted(set(translations) - translated - set(missing))}
    if report_path:
        Path(report_path).write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('destination', type=Path)
    parser.add_argument('--report', type=Path)
    args = parser.parse_args()
    print(json.dumps(patch_overlay(args.source, args.destination, args.report), ensure_ascii=False, indent=2))
