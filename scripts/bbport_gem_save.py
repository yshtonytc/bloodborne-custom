"""Offline Bloodborne 1.09 gem edits. Never scan-and-replace arbitrary byte patterns.

Layout research: Noxde/Bloodborne-save-editor (GPL-3.0), upgrades.rs/offsets.rs.
Only six effect IDs inside a validated, existing 40-byte gem record are writable.
"""
import hashlib
import json
from pathlib import Path
import shutil
import struct
import uuid

import bbport_respec as characters
import bbport_save_restore as saves
from bbport_gem_catalog import EFFECTS
import bbport_gem_legality as legality

EMPTY = 0xffffffff
SHAPES = {1: '放射', 2: '三角', 4: '月牙', 8: '圆形', 63: '水滴'}
SAVE_SIZE = 0x140000


def digest(data):
    return hashlib.sha256(data).hexdigest()


def parse(data):
    """Read the leading GA upgrade table; stop at its equipment section, never resync."""
    if not data or not any(data):
        return None
    if len(data) != SAVE_SIZE or struct.unpack_from('<I', data, 12)[0] != 84:
        raise ValueError('不支持的存档格式：需要移植版未加密的 1.09 角色存档。')
    blocks = characters.find_blocks(data)
    if not blocks:
        raise ValueError('无法验证角色信息，拒绝编辑。')
    who = characters.read_block(data, blocks[0])
    if any(characters.read_block(data, at) != who for at in blocks):
        raise ValueError('角色数据副本不一致，拒绝编辑。')
    records, seen, at = [], set(), 84
    limit = min(blocks)
    while at + 40 <= limit:
        record = struct.unpack_from('<10I', data, at)
        handle, source, kind, shape, *effects = record
        if kind not in (1, 2):
            break  # weapon/armor table follows the upgrades
        if shape not in (SHAPES if kind == 1 else (1, 2)):
            raise ValueError('宝石／符文表形状异常，拒绝编辑。')
        if handle >> 24 != 0xc0 or handle in seen or source >> 28 != 8:
            raise ValueError('宝石／符文实例标识异常或重复，拒绝编辑。')
        seen.add(handle)
        if kind == 1:
            records.append({'handle': handle, 'source': source, 'shape': shape,
                            'effects': effects, 'offset': at, 'record': data[at:at+40].hex()})
        at += 40
    if at + 40 > limit:
        raise ValueError('无法确认宝石表边界，拒绝编辑。')
    # Location is display-only. Never use a guessed inventory offset for writes.
    locations = {g['handle']: [] for g in records}
    by_handle = {g['handle']: g for g in records}
    inventory_start = blocks[0] + characters.NAME + 468
    for start, label in ((inventory_start, '背包'), (inventory_start+34268, '仓库')):
        if start+1984*16 > len(data):
            continue
        for pos in range(start, start+1984*16, 16):
            _, handle, source, count = struct.unpack_from('<4I', data, pos)
            gem = by_handle.get(handle)
            if gem is not None and source == gem['source'] and count > 0:
                locations[handle].append(label)
    for pos in range(at, max(at, limit-60), 4):
        handle, source = struct.unpack_from('<II', data, pos)
        if handle >> 24 not in (0x80, 0x90, 0xa0) or source >> 28 not in (0, 1, 2):
            continue
        if struct.unpack_from('<I', data, pos+16)[0] != 1:
            continue
        pairs = [struct.unpack_from('<II', data, pos+20+8*i) for i in range(5)]
        if all(shape in (*SHAPES, 0x80000000) for shape, _ in pairs):
            for shape, gem_handle in pairs:
                if shape != 0x80000000 and gem_handle in locations:
                    locations[gem_handle].append('已镶嵌')
    for gem in records:
        gem['location'] = ' / '.join(dict.fromkeys(locations[gem['handle']])) or '未定位'
    return {'character': who, 'gems': records, 'sha256': digest(data)}


def load(user, slot):
    if type(slot) is not int or not 0 <= slot < 10:
        raise ValueError('角色槽位无效。')
    folder = saves._validate(saves.save_dir(user), Path(user))
    path = saves._validate(folder / f'userdata{slot:04d}', folder)
    result = parse(path.read_bytes())
    if result is None:
        raise ValueError('这个槽位没有角色。')
    return result


def list_characters(user):
    folder = saves._validate(saves.save_dir(user), Path(user))
    result = []
    for slot in range(10):
        path = folder / f'userdata{slot:04d}'
        if not path.is_file():
            continue
        try:
            info = load(user, slot)
        except ValueError as error:
            if any(path.read_bytes()):
                raise ValueError(f'角色槽位 {slot+1}：{error}') from error
            continue
        result.append((slot, info))
    return result


def check_effects(old, new, gem=None):
    if len(new) != 6 or any(type(v) is not int for v in new):
        raise ValueError('必须提供六个词条槽。')
    if new[0] == EMPTY:
        raise ValueError('主词条不能为空。')
    for before, after in zip(old, new):
        # Unknown existing values may be preserved, but never introduced elsewhere.
        if after != before and after != EMPTY and after not in EFFECTS:
            raise ValueError(f'未验证的宝石效果 ID：{after}')
    if list(old) == list(new):
        raise ValueError('词条没有变化。')
    if gem is None or list(gem['effects']) != list(old):
        raise ValueError('缺少原始宝石来源，无法校验原版组合。')
    return legality.validate(gem, new)


def rewrite(data, handle, old_record, effects, table_profile=None):
    info = parse(data)
    if info is None:
        raise ValueError('角色槽位为空。')
    matches = [g for g in info['gems'] if g['handle'] == handle]
    if len(matches) != 1 or matches[0]['record'] != old_record:
        raise ValueError('所选宝石已变化，请重新读取。')
    gem = matches[0]
    if table_profile is not None:
        gem['table_profile'] = table_profile
    check_effects(gem['effects'], effects, gem)
    at = gem['offset'] + 16
    output = bytearray(data)
    struct.pack_into('<6I', output, at, *effects)
    output = bytes(output)
    # A second parser pass and exact outside-range equality constrain every write.
    changed = next(g for g in parse(output)['gems'] if g['handle'] == handle)
    if changed['effects'] != list(effects) or output[:at] != data[:at] or output[at+24:] != data[at+24:]:
        raise OSError('宝石修改校验失败。')
    return output


def apply(user, port, slot, expected_hash, handle, effects, check_closed=None, table_profile=None):
    """Verified full-directory staging + rollback, sharing the restore operation's lock."""
    user = Path(user).absolute()
    saves._validate(user, user)
    closed = check_closed or (lambda: saves.assert_game_closed(port))
    closed()
    with saves._restore_lock(user):
        info = load(user, slot)
        if info['sha256'] != expected_hash:
            raise ValueError('存档自读取后已变化，请重新读取后再编辑。')
        gem = next((g for g in info['gems'] if g['handle'] == handle), None)
        if gem is None:
            raise ValueError('没有找到所选宝石。')
        if table_profile is not None:
            gem['table_profile'] = table_profile
        witness = check_effects(gem['effects'], effects, gem)
        folder = saves._validate(saves.save_dir(user), user)
        original = saves.inventory(folder)
        filename = f'userdata{slot:04d}'
        updates = {filename: rewrite((folder/filename).read_bytes(), handle, gem['record'], effects,table_profile)}
        backup_name = f'backup{slot:04d}'
        backup = folder / backup_name
        if backup.is_file():
            backup_info = parse(backup.read_bytes())
            if backup_info and backup_info['character'] == info['character']:
                same = [g for g in backup_info['gems'] if g['handle'] == handle and g['record'] == gem['record']]
                if same:
                    updates[backup_name] = rewrite(backup.read_bytes(), handle, gem['record'], effects,table_profile)
        safety = saves._safety_copy(user, folder)
        if safety is None:
            raise OSError('未能创建完整安全副本，未修改存档。')
        audit = {'type': 'gem-edit', 'slot': slot, 'handle': handle, 'table_profile':witness,
                 'before': gem['effects'], 'after': list(effects), 'updated_files': list(updates)}
        (safety / 'gem-edit.json').write_text(json.dumps(audit, ensure_ascii=False, indent=2), encoding='utf-8')
        token = uuid.uuid4().hex
        stage = user / ('.gem-stage-' + token)
        previous = user / ('.gem-before-' + token)
        published = False
        try:
            shutil.copytree(folder, stage)
            if saves.inventory(stage) != original:
                raise OSError('暂存副本校验失败。')
            for name, data in updates.items():
                (stage/name).write_bytes(data)
            expected = dict(original)
            for name, data in updates.items():
                expected[name] = {'size': len(data), 'sha256': digest(data)}
            if saves.inventory(stage) != expected:
                raise OSError('修改后的暂存副本校验失败。')
            closed()
            if saves.inventory(folder) != original:
                raise ValueError('准备期间存档发生变化，已停止。')
            folder.rename(previous)
            try:
                stage.rename(folder)
                published = True
                if saves.inventory(folder) != expected:
                    raise OSError('发布后校验失败。')
            except Exception:
                if published:
                    saves._remove(folder, user)
                previous.rename(folder)
                raise
            saves._remove(previous, user)
            return {'safety': str(safety), **audit}
        finally:
            if stage.exists():
                saves._remove(stage, user)


_PHRASES = {
    'Physical ATK UP': '物理攻击提高', 'Blunt ATK UP': '钝击攻击提高',
    'Thrust ATK UP': '突刺攻击提高', 'Blood ATK UP': '血质攻击提高',
    'Fire ATK UP': '火焰攻击提高', 'Bolt ATK UP': '雷电攻击提高', 'Arcane ATK UP': '秘法攻击提高',
    'Add physical ATK': '附加物理攻击', 'Add blood ATK': '附加血质攻击',
    'Add fire ATK': '附加火焰攻击', 'Add bolt ATK': '附加雷电攻击', 'Add arcane ATK': '附加秘法攻击',
    'ATK vs the kin DOWN': '对眷族攻击降低', 'ATK vs beasts DOWN': '对野兽攻击降低',
    'ATK vs the kin UP': '对眷族攻击提高', 'ATK vs kin UP': '对眷族攻击提高',
    'ATK vs beasts UP': '对野兽攻击提高', 'ATK vs open foes UP': '对破绽敌人攻击提高',
    'ATK UP at full HP': '满血时攻击提高', 'Phys. UP at full HP': '满血时物理攻击提高',
    'ATK UP near death': '濒死时攻击提高', 'Phys. UP near death': '濒死时物理攻击提高',
    'ATK DOWN': '攻击降低', 'ATK UP': '全攻击提高', 'Charge ATKs UP': '蓄力攻击提高',
    'STR scaling': '力量补正', 'SKL scaling': '技巧补正', 'Bloodtinge scaling': '血质补正',
    'Arcane scaling': '秘法补正', 'HP continues to recover': '生命持续恢复',
    'HP gradually depletes': '生命持续减少', 'Boosts rally potential': '虚血回复量提高',
    'Reduces stamina costs': '体力消耗降低', 'Increases stamina costs': '体力消耗增加',
    'WPN durability DOWN': '武器耐久降低', 'WPN durability UP': '武器耐久提高',
    'Add slow poison effect': '附加慢性毒素', 'Add rapid poison effect': '附加剧毒',
}


def effect_text(value):
    if value == EMPTY:
        return '无词条'
    row = EFFECTS.get(value)
    if row is None:
        return f'未知效果（保留原值） #{value}'
    text = row[1]
    percent = ('Physical ATK UP', 'Blunt ATK UP', 'Thrust ATK UP', 'Blood ATK UP',
               'Fire ATK UP', 'Bolt ATK UP', 'Arcane ATK UP', 'ATK UP', 'ATK DOWN',
               'ATK vs ', 'Charge ATKs UP', 'Phys. UP', 'Increases stamina costs',
               'Reduces stamina costs')
    if '%' not in text and text.startswith(percent):
        text = text.rstrip() + '%'
    for english, chinese in sorted(_PHRASES.items(), key=lambda item: -len(item[0])):
        if text.startswith(english):
            text = chinese + text[len(english):]
            break
    return f'{text}  [效果档位 {row[2]} / ID {value}]'
