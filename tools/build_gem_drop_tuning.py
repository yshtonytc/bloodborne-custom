"""Build a reversible parameter overlay; originals and saves are never modified."""
import argparse
import hashlib
import json
import logging
from pathlib import Path
import re
import shutil
import struct
import sys
import uuid

ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT/'scripts'), str(ROOT/'launcher')]
import bbport_gem_drop_config as config
import bbport_save_restore as safety
from bbport_gem_catalog import EFFECTS
from soulstruct.containers import Binder
from soulstruct.bloodborne.params import GameParamBND


def sha(data):
    return hashlib.sha256(data).hexdigest()


def family(description):
    name = re.split(r'\s+[+-]?\d', description)[0]
    return 'ATK vs the kin UP' if name == 'ATK vs kin UP' else name


def raw_rows(raw):
    count = struct.unpack_from('<H', raw, 10)[0]
    start = struct.unpack_from('<Q', raw, 48)[0]
    if start != 64+24*count:
        raise ValueError('Unsupported PARAM layout')
    result = []
    for i in range(count):
        ident, offset, _ = struct.unpack_from('<qQQ', raw, 64+24*i)
        if not start <= offset < len(raw):
            raise ValueError('Invalid PARAM row offset')
        result.append((ident, offset))
    return result


def patch_table(raw, changes, field, fmt):
    """Patch only known fields at every matching pointer; retain duplicate IDs and all names."""
    out = bytearray(raw)
    seen = set()
    allowed = set()
    for ident, offset in raw_rows(raw):
        if ident not in changes:
            continue
        old, new = changes[ident]
        if struct.unpack_from(fmt, raw, offset+field)[0] != old:
            raise ValueError(f'PARAM schema mismatch for row {ident}')
        struct.pack_into(fmt, out, offset+field, new)
        allowed.update(range(offset+field, offset+field+struct.calcsize(fmt)))
        seen.add(ident)
    if seen != set(changes):
        raise ValueError('Missing parameter rows')
    if any(a != b and i not in allowed for i, (a, b) in enumerate(zip(raw, out))):
        raise ValueError('Unexpected parameter modification')
    return bytes(out)


def plan(params, settings):
    settings = config.validate(settings)
    doping = params.params['GemDropDopingParam'].rows
    ranks = {}
    skipped = []
    if settings['max_roll']:
        for ident, row in doping.items():
            # ID 0 / 99... test fallbacks cover 1..100. Never turn those into "rank 100".
            # 900... are already fixed-rank test entries, not source ranges.
            known_source = 6000 <= ident < 7000 or 21000000 <= ident <= 36000000
            if known_source and 1 <= row.MinimumRank < row.MaximumRank <= 20:
                ranks[ident] = (row.MinimumRank, row.MaximumRank)
            elif row.MinimumRank != row.MaximumRank:
                skipped.append(ident)
    categories = params.params['GemCategoryParam'].rows
    families = {}
    for ident, row in params.params['GemeffectParam'].rows.items():
        if ident in EFFECTS and row.CategoryID > 0 and row.CategoryID in categories:
            families.setdefault(row.CategoryID, set()).add(family(EFFECTS[ident][1]))
    weights = {}
    counts = {key: 0 for key in config.FAMILIES}
    for ident, names in families.items():
        if len(names) != 1 or next(iter(names)) not in settings['weights']:
            continue
        key = next(iter(names))
        row = categories[ident]
        counts[key] += 1
        multiplier = settings['weights'][key]
        if row.ManifestRate > 0 and multiplier != 1:
            # Preserve zero-weight/unused categories. A strictly positive floor avoids empty pools.
            value = struct.unpack('<f', struct.pack('<f', row.ManifestRate*multiplier))[0]
            weights[ident] = (row.ManifestRate, value)
    return ranks, weights, skipped, counts


def build(game, destination, settings, rock=None):
    """Build in a caller-owned staging directory. Never enable mods or write config here."""
    game, destination = Path(game), Path(destination)
    original = game/config.PARAM
    original_data = original.read_bytes()
    binder = Binder.from_bytes(original_data)
    original_members = {e.name: e.get_uncompressed_data() for e in binder.entries}
    rock_hash = None
    if rock and Path(rock).is_file():
        data = Path(rock).read_bytes()
        candidate = Binder.from_bytes(data)
        if {e.name for e in candidate.entries} != set(original_members):
            raise ValueError('Blood rock binder members changed')
        for entry in candidate.entries:
            if entry.name != 'ItemLotParam.param' and entry.get_uncompressed_data() != original_members[entry.name]:
                raise ValueError('血岩参数包还包含其他修改，需人工合并。')
        # Require the established blood-rock builder's local hash report.
        metadata = json.loads((Path(rock).parents[3]/'validation.json').read_text(encoding='utf-8'))
        hashes = {key.replace('\\', '/'): value for key, value in metadata['mod_sha256'].items()}
        if hashes[config.PARAM.as_posix()] != sha(data):
            raise ValueError('血岩参数包与本地校验记录不符。')
        rock_hash = sha(data)
        binder = candidate
    params = GameParamBND.from_path(original)
    ranks, weights, skipped, counts = plan(params, settings)
    edits = {'GemDropDopingParam.param': (ranks, 0, '<i'), 'GemCategoryParam.param': (weights, 4, '<f')}
    before = {e.name: e.get_uncompressed_data() for e in binder.entries}
    for entry in binder.entries:
        if entry.name in edits:
            changes, offset, fmt = edits[entry.name]
            entry.set_uncompressed_data(patch_table(before[entry.name], changes, offset, fmt))
    output = destination/config.PARAM
    output.parent.mkdir(parents=True, exist_ok=True)
    binder.write(output)
    reread = Binder.from_path(output)
    for entry in reread.entries:
        if entry.name not in edits and entry.get_uncompressed_data() != before[entry.name]:
            raise ValueError('Unrelated binder member changed')
    parsed = GameParamBND.from_path(output)
    for ident, (old, maximum) in ranks.items():
        row = parsed.params['GemDropDopingParam'].rows[ident]
        if row.MinimumRank != maximum or row.MaximumRank != maximum:
            raise ValueError('Source rank verification failed')
    for ident, (_, value) in weights.items():
        if parsed.params['GemCategoryParam'].rows[ident].ManifestRate != value:
            raise ValueError('Category weight verification failed')
    if sha(original.read_bytes()) != sha(original_data):
        raise ValueError('Original parameter file changed externally')
    report = {'schema': 1, 'source_sha256': sha(original_data), 'blood_rock_sha256': rock_hash,
        'output_sha256': sha(output.read_bytes()), 'source_rank_changes': {str(k): list(v) for k, v in ranks.items()},
        'changed_category_weights': len(weights), 'family_category_counts': counts,
        'unbounded_sources_unchanged': skipped,
        'unchanged_binder_members': len(binder.entries)-len(edits),
        'validation': 'Exact PARAM field and binder preservation, reparse and bounds checks. In-game drops not verified.'}
    (destination/'validation.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    (destination/'settings.json').write_text(json.dumps(config.validate(settings), ensure_ascii=False, indent=2), encoding='utf-8')
    (destination/'bbport-mod.json').write_text(json.dumps({'name':config.NAME,
        'description':'已识别来源最高生成档＋词条相对权重；兼容额外血岩，未改原游戏或已有宝石。',
        'ignore_legacy_overlay':True}, ensure_ascii=False, indent=2), encoding='utf-8')
    return report


def install(port, game, settings):
    port = Path(port).absolute()
    root = safety._validate(port/'mods', port)
    user = safety._validate(port/'user', port)
    safety.assert_game_closed(port)
    with safety._restore_lock(user):
        token = uuid.uuid4().hex
        stage = user/('.gem-build-'+token)
        previous = user/('.gem-old-'+token)
        target = root/config.NAME
        settings_path = port/'mods.json'
        pending = port/('.gem-profile-'+token)
        old_config = settings_path.read_bytes() if settings_path.is_file() else None
        profile = json.loads(old_config) if old_config else {'order': [], 'disabled': []}
        rock = root/'ChaliceClearBloodRock'/config.PARAM
        try:
            stage.mkdir()
            report = build(game, stage, settings, rock if rock.is_file() else None)
            sys.path.insert(0, str(ROOT/'scripts'))
            import mods
            selected = [(n, root/n) for n in mods.selected(root, settings_path) if n != config.NAME and not n.startswith('.')]
            config.check_layers([*selected, (config.NAME, stage)])
            safety.assert_game_closed(port)
            if settings_path.is_file() and settings_path.read_bytes() != old_config:
                raise ValueError('准备期间模组选择发生变化，请重试。')
            if target.exists():
                safety._validate(target, root).rename(previous)
            try:
                stage.rename(target)
                all_names = [*profile.get('order', []), *mods.discover(root)]
                profile['order'] = list(dict.fromkeys(n for n in all_names if n != config.NAME))+[config.NAME]
                profile['disabled'] = [n for n in profile.get('disabled', []) if n != config.NAME]
                pending.write_text(json.dumps(profile, ensure_ascii=False, indent=2), encoding='utf-8')
                pending.replace(settings_path)
            except Exception:
                if target.exists():
                    safety._remove(target, root)
                if previous.exists():
                    previous.rename(target)
                if old_config is not None:
                    settings_path.write_bytes(old_config)
                raise
            if previous.exists():
                safety._remove(previous, user)
            return report
        finally:
            pending.unlink(missing_ok=True)
            if stage.exists():
                safety._remove(stage, user)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', type=Path, default=ROOT/'windows-v1.7/bbport-windows')
    parser.add_argument('--game', type=Path, required=True)
    parser.add_argument('--config', type=Path)
    parser.add_argument('--out', type=Path, help='Build only; do not enable/install the mod')
    args = parser.parse_args()
    logging.disable(logging.CRITICAL)
    settings = config.read(args.config or args.port/'mods'/config.NAME/'settings.json')
    if args.out:
        report = build(args.game, args.out, settings, args.port/'mods/ChaliceClearBloodRock'/config.PARAM)
    else:
        report = install(args.port, args.game, settings)
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        print(f'宝石掉落调校失败：{error}', file=sys.stderr)
        sys.exit(1)
