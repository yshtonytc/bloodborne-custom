"""Merge a published Windows upstream tag; conflicts stop before any push/release."""
import argparse
import json
from pathlib import Path
import re
import subprocess
import urllib.request

ROOT=Path(__file__).resolve().parents[1]
def git(*args,**kwargs):return subprocess.check_output(['git',*args],cwd=ROOT,text=True,**kwargs).strip()

def main():
    p=argparse.ArgumentParser();p.add_argument('--tag',default='latest');p.add_argument('--push',action='store_true');a=p.parse_args()
    if git('status','--porcelain'):raise SystemExit('Commit or stash local changes before syncing.')
    config_path=ROOT/'custom/upstream.json';config=json.loads(config_path.read_text())
    if git('branch','--show-current')!=config['custom_branch']:raise SystemExit('Use the custom branch.')
    endpoint='latest' if a.tag=='latest' else 'tags/'+a.tag
    with urllib.request.urlopen(urllib.request.Request('https://api.github.com/repos/'+config['repository']+'/releases/'+endpoint,
            headers={'User-Agent':'bloodborne-custom'}),timeout=30) as r:release=json.load(r)
    tag=release['tag_name']
    if not re.fullmatch(r'windows-v[0-9][0-9A-Za-z.+-]*',tag) or release.get('prerelease'):
        raise SystemExit('Only stable Windows release tags can be synced.')
    asset=next(x for x in release['assets'] if x['name']=='Bloodborne-Windows.zip')
    if not asset.get('digest','').startswith('sha256:'):raise SystemExit('Upstream package has no SHA-256 digest.')
    url='https://github.com/'+config['repository']+'.git'
    git('fetch',url,'refs/tags/'+tag)
    commit=git('rev-parse','FETCH_HEAD^{commit}')
    # Keep all local changes. Git reports conflicting files instead of overwriting them.
    subprocess.run(['git','merge','--no-edit',commit],cwd=ROOT,check=True)
    config.update(tag=tag,commit=commit,package_sha256=asset['digest'])
    config_path.write_text(json.dumps(config,indent=2)+'\n',encoding='utf-8')
    git('add','custom/upstream.json')
    if git('diff','--cached','--name-only'):git('commit','-m','Record verified upstream '+tag)
    if a.push:
        git('push','origin',commit+':refs/heads/upstream-windows','HEAD:refs/heads/'+config['custom_branch'])
    print('Merged '+tag+'. Run tests/build before publishing. Conflicts are never auto-resolved.')

if __name__=='__main__':main()
