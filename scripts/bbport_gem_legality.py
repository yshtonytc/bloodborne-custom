"""Whole-gem validation against documented vanilla table variants.
The stored source is retained as provenance, not an arbitrary editing lock.
Match complete effect tuples and shapes, never independent global maxima.
"""
from bbport_gem_table_data import PROFILES, EXCLUSIONS

EMPTY = 0xffffffff


def _valid(profile, effects):
    if len(effects) != 6 or any(type(value) is not int for value in effects):
        return False
    excluded = set()
    for index, value in enumerate(effects):
        if value not in profile['pools'][index]:
            return False
        if value == EMPTY:
            continue
        group = EXCLUSIONS[value]
        # Fixed-secondary duplicates are documented, e.g. Labyrinth Spirit.
        if group and group in excluded and not (index == 1 and profile['fixed_secondary']):
            return False
        if group:
            excluded.add(group)
    return True


def available(gem):
    return tuple(key for key, p in PROFILES.items() if gem['shape'] in p['shapes'])


def match(gem, effects, selected=None):
    if selected is not None:
        profile = PROFILES.get(selected)
        return selected if profile and gem['shape'] in profile['shapes'] and _valid(profile,effects) else None
    return next((key for key in available(gem) if _valid(PROFILES[key],effects)), None)


def policy(gem):
    key = gem.get('table_profile')
    if key is None:
        key = match(gem,gem['effects'])
    profile = PROFILES.get(key)
    if profile is None or gem['shape'] not in profile['shapes']:
        return {'editable':False,'pools':None,'profile':None,
                'reason':'原宝石保持不变。请选择主词条类别和档位，再选择负面词缀；不锁原来源或原档位。'}
    return {'editable':True,'pools':profile['pools'],'profile':key,
            'reason':f'按表校验：{profile["label"]}；主副效果、诅咒和评级联动。'}


def validate(gem,effects,rules=None):
    if len(effects) != 6 or any(type(value) is not int for value in effects):
        raise ValueError('必须提供六个有效词条槽。')
    selected = gem.get('table_profile')
    if rules is not None:
        selected = rules.get('profile')
    key = match(gem,effects,selected)
    if key is None:
        raise ValueError('整颗宝石不符合所选表项：请核对主副效果、诅咒、评级和形状，不能混拼不同类型的最高值。')
    return key


def candidates(gem,index,current=None):
    rules = policy(gem)
    if rules['pools'] is None or not 0 <= index < 6:
        return ()
    values = list(current if current is not None else gem['effects'])
    result=[]
    for value in rules['pools'][index]:
        if value == EMPTY:
            continue
        proposed=list(values)
        proposed[index]=value
        try:
            validate(gem,proposed,rules)
        except ValueError:
            continue
        result.append(value)
    return tuple(result)
