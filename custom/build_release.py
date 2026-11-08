"""Build the custom distribution from an authenticated official package and tracked source.

Never read a playable installation, saves, settings or game resources.
"""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import urllib.request
import zipfile

ROOT = Path(__file__).resolve().parents[1]

def sha(path):
    with Path(path).open('rb') as f:
        return hashlib.file_digest(f,'sha256').hexdigest()

def fetch(url, path, expected=None):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    if not path.exists() or expected and sha(path)!=expected:
        temp=path.with_suffix(path.suffix+'.pending')
        with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'bloodborne-custom'}),timeout=120) as r,temp.open('wb') as f:
            shutil.copyfileobj(r,f)
        if expected and sha(temp)!=expected:
            temp.unlink();raise ValueError('Download SHA-256 mismatch: '+url)
        temp.replace(path)
    return path

def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    result=importlib.util.module_from_spec(spec);spec.loader.exec_module(result);return result

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--out',type=Path,default=ROOT/'dist/custom')
    parser.add_argument('--cache',type=Path,default=ROOT/'out/custom-cache');args=parser.parse_args()
    out=args.out.resolve();out.mkdir(parents=True,exist_ok=True);cache=args.cache.resolve();cache.mkdir(parents=True,exist_ok=True)
    config=json.loads((ROOT/'custom/upstream.json').read_text())
    release=json.load(urllib.request.urlopen(urllib.request.Request(
        'https://api.github.com/repos/'+config['repository']+'/releases/tags/'+config['tag'],headers={'User-Agent':'bloodborne-custom'}),timeout=30))
    asset=next(a for a in release['assets'] if a['name']=='Bloodborne-Windows.zip')
    digest=asset.get('digest','')
    if digest!=config['package_sha256'] or not digest.startswith('sha256:'):
        raise ValueError('Official release digest changed; review and sync its metadata before building')
    archive=fetch(asset['browser_download_url'],cache/(config['tag']+'.zip'),digest.split(':')[1])
    work=ROOT/'out/custom-build'
    if work.exists():
        if not work.resolve().is_relative_to((ROOT/'out').resolve()) or any(p.is_symlink() or p.is_junction() for p in [work,*work.rglob('*')]):
            raise ValueError('Unsafe build directory')
        shutil.rmtree(work)
    work.mkdir(parents=True)
    with zipfile.ZipFile(archive) as z:
        for item in z.infolist():
            if not (work/item.filename).resolve().is_relative_to(work.resolve()):raise ValueError('Unsafe archive member')
            if item.external_attr>>16&0o170000==0o120000:raise ValueError('Archive contains symlink')
        z.extractall(work)
    package=work/'bbport-windows'
    for relative in ('run.py','scripts','patches'):
        source=ROOT/relative;target=package/relative
        if source.is_dir():shutil.copytree(source,target,dirs_exist_ok=True,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
        else:shutil.copy2(source,target)
    font=json.loads((ROOT/'custom/font.json').read_text())
    for name,info in font['files'].items():fetch(info['url'],cache/name,info['sha256'])
    os.environ['BBPORT_CHINESE_FONT']=str(cache/'NotoSansSC[wght].ttf')
    native=module('custom_native',ROOT/'tools/native_overlay_zh.py')
    assets=work/'font-assets';assets.mkdir()
    shutil.copy2(ROOT/'gpu/third_party/fonts/DejaVuSans.ttf',assets/'original-font.ttf')
    shutil.copy2(ROOT/'local-customizations/native-overlay/strings-zh.json',assets/'strings-zh.json')
    native.ASSETS=assets
    overlay=(ROOT/'gpu/shim/bbport_overlay.cpp').read_text(encoding='utf-8')
    if not all(text in overlay for text in ('ranges.AddRanges(io.Fonts->GetGlyphRangesCyrillic());','ranges.BuildRanges(&picker_glyphs);','&font_config, picker_glyphs.Data')):
        raise ValueError('Upstream native font layout changed; review before releasing')
    probe=package/'bin/bb-probe.exe'
    report=native.patch_overlay(probe,probe,work/'native.json',picker_glyph_ranges=True)
    licenses=package/'licenses';licenses.mkdir(exist_ok=True)
    shutil.copy2(cache/'OFL.txt',licenses/'NotoSansSC-OFL.txt')
    shutil.copy2(ROOT/'local-customizations/gem-editor/LICENSE.txt',licenses/'gem-editor-GPL-3.0.txt')
    shutil.copy2(ROOT/'local-customizations/gem-editor/THIRD_PARTY.txt',licenses/'gem-editor-THIRD-PARTY.txt')
    rumble=module('custom_rumble',ROOT/'tools/build_native_rumble.py').install_rumble(package)
    # The public package does not rely on this maintainer's local Python venv.
    subprocess.run([sys.executable,'-m','PyInstaller','--noconfirm','--log-level','WARN',
        '--collect-all','soulstruct','--console','--name','gem-drop-builder','--distpath',str(work/'mod-tools'),
        '--workpath',str(work/'mod-pyi'),'--specpath',str(work),
        '--paths',str(ROOT/'scripts'),'--paths',str(ROOT/'launcher'),
        str(ROOT/'tools/build_gem_drop_tuning.py')],check=True)
    shutil.copytree(work/'mod-tools/gem-drop-builder',package/'tools/gem-drop-builder')
    command=[sys.executable,'-m','PyInstaller','--noconfirm','--log-level','WARN','--windowed','--name','Bloodborne',
        '--contents-directory','_internal-zh','--icon',str(ROOT/'launcher/bloodborne.ico'),
        '--distpath',str(work/'frozen'),'--workpath',str(work/'pyi'),'--specpath',str(work),
        '--paths',str(ROOT/'scripts'),'--add-data',str(ROOT/'launcher/assets')+';assets']
    for hidden in ('argparse','base64','bisect','collections','contextlib','hashlib','json','re','shutil','struct','tempfile','xml.etree.ElementTree','urllib.request','ctypes.wintypes'):
        command.extend(['--hidden-import',hidden])
    subprocess.run(command+[str(ROOT/'launcher/bbport_launcher_win.py')],check=True)
    shutil.copy2(work/'frozen/Bloodborne/Bloodborne.exe',package/'Bloodborne.exe')
    shutil.copytree(work/'frozen/Bloodborne/_internal-zh',package/'_internal-zh',dirs_exist_ok=True)
    subprocess.run([sys.executable,str(ROOT/'scripts/package_files.py'),'--write',str(package),config['tag'].removeprefix('windows-v')],check=True)
    commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    (package/'CUSTOM-BUILD.json').write_text(json.dumps({'repository':config['custom_repository'],'source_commit':commit,
        'upstream':config,'font':font,'native':report,'rumble':rumble},ensure_ascii=False,indent=2),encoding='utf-8')
    # Source and exact upstream provider-source archives accompany our binary.
    subprocess.run(['git','archive','--format=zip','--output',str(out/'Bloodborne-Custom-Source.zip'),'HEAD'],cwd=ROOT,check=True)
    for a in release['assets']:
        if 'src' in a['name'].lower() or 'source' in a['name'].lower():
            expected=a.get('digest','')
            if not expected.startswith('sha256:'):raise ValueError('Source asset lacks SHA-256')
            fetch(a['browser_download_url'],out/a['name'],expected.split(':')[1])
    shutil.make_archive(str(out/'Bloodborne-Windows'),'zip',work,'bbport-windows')
    (out/'SHA256SUMS.txt').write_text(''.join(sha(p)+'  '+p.name+'\n' for p in sorted(out.glob('*.zip'))),encoding='utf-8')
    print('Built verified public package:',out/'Bloodborne-Windows.zip',flush=True)

if __name__=='__main__':main()
