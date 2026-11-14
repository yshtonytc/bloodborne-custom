"""Plan a stable-only update before provisioning the Windows build runner."""
import json
import os
from pathlib import Path
import re
import urllib.error
import urllib.request


def version(tag):
    if not re.fullmatch(r'(?:windows-v)?\d+(?:\.\d+){2,3}', tag):
        raise ValueError('Unrecognized version: ' + tag)
    values = tuple(map(int, tag.removeprefix('windows-v').split('.')))
    return values + (0,) * (4 - len(values))


def get(path, optional=False):
    headers = {'User-Agent': 'custom-stable-updates'}
    if os.environ.get('GH_TOKEN'):
        headers['Authorization'] = 'Bearer ' + os.environ['GH_TOKEN']
    try:
        with urllib.request.urlopen(urllib.request.Request(
                'https://api.github.com/' + path, headers=headers), timeout=45) as response:
            return json.load(response)
    except urllib.error.HTTPError as error:
        if optional and error.code == 404:
            return None
        raise


def plan(config, upstream, published):
    if upstream.get('draft') or upstream.get('prerelease'):
        raise ValueError('Stable endpoint returned an unpublished or preview release')
    tag = upstream['tag_name']
    # A manually selected preview must never be downgraded to an older stable.
    if version(tag) < version(config['tag']):
        return {'build': 'false', 'sync_tag': '', 'reason': 'Pinned version is newer than stable'}
    newer = version(tag) > version(config['tag'])
    if not newer and config.get('prerelease'):
        # Promotion of this same tag still needs the stable flag and digest refreshed.
        newer = True
    if not newer and published:
        if published.get('draft') or published.get('prerelease'):
            raise ValueError('Expected stable custom release is not stable')
        return {'build': 'false', 'sync_tag': '', 'reason': 'Stable custom package already published'}
    return {'build': 'true', 'sync_tag': tag if newer else '',
            'reason': 'New stable source or missing tested custom package'}


def main():
    config = json.loads(Path(__file__).with_name('upstream.json').read_text(encoding='utf-8'))
    upstream = get('repos/' + config['repository'] + '/releases/latest')
    tag = upstream['tag_name']
    custom_tag = (config.get('custom_version', tag) if tag == config['tag']
                  else tag if tag.startswith('windows-v') else tag + '.1')
    published = get('repos/' + config['custom_repository'] + '/releases/tags/' + custom_tag, optional=True)
    result = plan(config, upstream, published)
    print(json.dumps(result))
    if os.environ.get('GITHUB_OUTPUT'):
        with open(os.environ['GITHUB_OUTPUT'], 'a', encoding='utf-8') as output:
            for key, value in result.items():
                output.write(f'{key}={value}\n')


if __name__ == '__main__':
    main()
