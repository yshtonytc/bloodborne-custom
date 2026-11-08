"""Settings and load-order checks for the loose-file gem drop tuning mod."""
import hashlib
import json
import math
from pathlib import Path

NAME = 'GemDropTuning'
PARAM = Path('dvdroot_ps4/param/gameparam/gameparam.parambnd.dcx')
FAMILIES = (
    'Physical ATK UP', 'Blunt ATK UP', 'Thrust ATK UP', 'Blood ATK UP', 'Arcane ATK UP',
    'Fire ATK UP', 'Bolt ATK UP', 'ATK UP', 'Add physical ATK', 'Add blood ATK',
    'Add arcane ATK', 'Add fire ATK', 'Add bolt ATK', 'STR scaling', 'SKL scaling',
    'Bloodtinge scaling', 'Arcane scaling', 'ATK vs beasts UP', 'ATK vs the kin UP',
    'Add slow poison effect', 'Add rapid poison effect', 'ATK vs open foes UP',
    'Reduces stamina costs', 'Charge ATKs UP', 'HP continues to recover',
    'Boosts rally potential', 'WPN durability UP', 'Phys. UP at full HP',
    'Phys. UP near death', 'ATK UP at full HP', 'ATK UP near death',
    'ATK DOWN', 'ATK vs beasts DOWN', 'ATK vs the kin DOWN', 'Increases stamina costs',
    'HP gradually depletes', 'WPN durability DOWN',
)


def validate(value):
    if not isinstance(value, dict) or set(value) - {'schema', 'max_roll', 'weights'}:
        raise ValueError('掉落配置格式错误。')
    if value.get('schema', 1) != 1 or type(value.get('max_roll', True)) is not bool:
        raise ValueError('掉落配置版本或满档开关无效。')
    weights = value.get('weights', {})
    if not isinstance(weights, dict) or set(weights) - set(FAMILIES):
        raise ValueError('存在未知词条类别。')
    result = {}
    for key in FAMILIES:
        number = weights.get(key, 1.0)
        if isinstance(number, bool) or not isinstance(number, (float, int)) or not math.isfinite(number) or not .01 <= number <= 10:
            raise ValueError('权重必须在 0.01～10 倍之间，且不能是空值或无限值。')
        result[key] = float(number)
    return {'schema': 1, 'max_roll': value.get('max_roll', True), 'weights': result}


def read(path):
    return validate(json.loads(Path(path).read_text(encoding='utf-8'))) if Path(path).is_file() else validate({})


def check_layers(layers):
    """Reject a later parameter override instead of silently losing tuning or blood rocks."""
    for index, (name, folder) in enumerate(layers):
        if name != NAME:
            continue
        folder = Path(folder)
        report = json.loads((folder/'validation.json').read_text(encoding='utf-8'))
        if hashlib.sha256((folder/PARAM).read_bytes()).hexdigest() != report['output_sha256']:
            raise ValueError('宝石掉落 MOD 校验失败，请重新生成。')
        for other, location in layers[index+1:]:
            if (Path(location)/PARAM).is_file():
                raise ValueError(f'{other} 在宝石掉落 MOD 后覆盖参数包，请把 {NAME} 移到最后。')
        for other, location in layers[:index]:
            if other == 'ChaliceClearBloodRock':
                original = hashlib.sha256((Path(location)/PARAM).read_bytes()).hexdigest()
                if original != report.get('blood_rock_sha256'):
                    raise ValueError('血岩 MOD 已变化，请重新生成宝石掉落 MOD 以合并。')
            elif (Path(location)/PARAM).is_file():
                raise ValueError(f'{other} 也修改游戏参数，需要先合并，不能直接叠加宝石掉落 MOD。')
