"""Frozen-window smoke test with isolated settings; never a user's save files."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT=Path(__file__).resolve().parents[1]

def inside():
    frame=sys._getframe()
    while frame and 'Launcher' not in frame.f_globals:frame=frame.f_back
    assert frame
    g=frame.f_globals
    import tkinter as tk
    from tkinter import ttk,filedialog
    from types import SimpleNamespace
    events=[]
    messages=SimpleNamespace(showerror=lambda *a,**k:events.append(a),showinfo=lambda *a,**k:None,
                             showwarning=lambda *a,**k:None,askyesno=lambda *a,**k:False)
    with tempfile.TemporaryDirectory() as temporary:
        g['DATA_DIR']=Path(temporary);g['CONFIG_FILE']=Path(temporary)/'settings.json';g['LANG']='zh'
        g['CONFIG_FILE'].write_text(json.dumps({'ui_language':'zh','language':'10','check_updates':False,
            'setup_done':True,'auto_graphics':False,'auto_backup':False,'game_dir':'',
            'fps_mode':'60','frame_cap':'60'}),encoding='utf-8')
        original=g['threading'].Thread.start
        def start(thread):
            if getattr(getattr(thread,'_target',None),'__name__','') in ('detect_gpu','check_update'):return
            return original(thread)
        g['threading'].Thread.start=start
        root=tk.Tk();root.withdraw();app=g['Launcher'](root,tk,ttk,filedialog,messages)
        for page in app.pages:app.show(page);root.update_idletasks()
        assert app.app['fps_mode']=='60' and app.app['frame_cap']=='60'
        assert app.app['exit_backup'] and not app.app['auto_backup'] and not app.app['auto_graphics']
        assert app.app['language']=='10'
        assert 'yshtonytc/bloodborne-custom' in g['RELEASES_API']
        assert g['game_environment'](app.app)['BB_EXIT_BACKUP']=='1'
        assert hasattr(app,'save_import_view') and not app.save_import_view.winfo_manager()
        assert not events,events
        root.destroy()
    return {'passed':True,'version':g['VERSION'],'pages':list(app.pages),'isolated_settings':True}

def main():
    if '--inside' in sys.argv:
        result=inside();Path(sys.argv[sys.argv.index('--result')+1]).write_text(json.dumps(result,indent=2),encoding='utf-8');return
    package=ROOT/'out/custom-build/bbport-windows'
    result=ROOT/'out/custom-build/gui.json'
    subprocess.run([str(package/'Bloodborne.exe'),'--script',str(Path(__file__).resolve()),'--inside','--result',str(result)],check=True,timeout=60)
    assert json.loads(result.read_text())['passed']
    sys.path.insert(0,str(ROOT/'scripts'));import package_files
    version,differ=package_files.check(package);assert not differ,differ
    metadata=json.loads((package/'CUSTOM-BUILD.json').read_text(encoding='utf-8'))
    assert metadata['font']['license']=='SIL Open Font License 1.1'
    assert metadata['native']['glyph_range_references']>0
    assert (package/'licenses/NotoSansSC-OFL.txt').is_file()
    assert not (package/'user').exists(), 'Release contains user data'
    subprocess.run([str(package/'tools/gem-drop-builder/gem-drop-builder.exe'),'--help'],check=True,timeout=30,
                   stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
    print('Frozen GUI, isolated settings, native glyph ranges, font license and program manifest verified:',version)

if __name__=='__main__':main()
