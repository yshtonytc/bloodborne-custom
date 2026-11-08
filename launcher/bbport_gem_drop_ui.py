"""Configure a loose-file drop mod; heavy PARAM work stays in the retained MOD environment."""
import json
import os
from pathlib import Path
import queue
import subprocess
import tempfile
import threading

import bbport_gem_drop_config as config
import bbport_gem_save as gems
from bbport_dialog_ui import bind_modal_wheel


def build_controls(app, parent, port):
    holder = app.ttk.Frame(parent)
    app.ttk.Button(holder, text='配置宝石掉落…', command=lambda: open_settings(app, port)).pack(side='left')
    app.row(parent, '宝石掉落调校', holder, '已识别来源最高生成档＋词条相对权重；通过 MOD 生效，不改背包里已有的宝石。')


def open_settings(app, port):
    previous = getattr(app, 'gem_drop_window', None)
    if previous is not None and previous.winfo_exists():
        previous.lift()
        return previous
    port = Path(port).absolute()
    root = port.parent.parent
    python = root/'tools-local/mod-build/Scripts/python.exe'
    tool = root/'tools/build_gem_drop_tuning.py'
    portable = port/'tools/gem-drop-builder/gem-drop-builder.exe'
    try:
        settings = config.read(port/'mods'/config.NAME/'settings.json')
    except Exception as error:
        app.messagebox.showerror('宝石掉落调校', str(error), parent=app.root)
        return
    tk, ttk = app.tk, app.ttk
    window = app.gem_drop_window = tk.Toplevel(app.root)
    window.title('宝石掉落调校')
    window.transient(app.root)
    window.geometry(f'{min(app.px(820), window.winfo_screenwidth()-80)}x{min(app.px(850), window.winfo_screenheight()-100)}')
    window.configure(bg=app.root.cget('background'))
    window.grab_set()
    frame = ttk.Frame(window, padding=14)
    frame.pack(fill='both', expand=True)
    maximum = tk.BooleanVar(value=settings['max_roll'])
    ttk.Checkbutton(frame, text='固定已识别来源的最高生成档（不突破原来源上限）', variable=maximum).pack(anchor='w')
    ttk.Label(frame, text='保留原版生成器加成、形状、掉落数量和词条槽数。负面词条仍按原版档位曲线生成。\n'
        '通用 1～100 范围及无法确认的来源保持原样；实战掉落效果尚待验证。', wraplength=740).pack(anchor='w', pady=(4, 8))
    ttk.Label(frame, text='权重是相对倍率，不是掉落百分比：1＝原版，0.1＝原权重的十分之一，2＝两倍。\n'
        '为避免候选池变空，仅允许 0.01～10 倍；固定词条和原本零权重的类别不因此解锁。', wraplength=740).pack(anchor='w')
    box = ttk.Frame(frame)
    box.pack(fill='both', expand=True, pady=10)
    canvas = tk.Canvas(box, bg=app.root.cget('background'), highlightthickness=0)
    scroll = ttk.Scrollbar(box, orient='vertical', command=canvas.yview)
    rows = ttk.Frame(canvas)
    item = canvas.create_window((0, 0), window=rows, anchor='nw')
    rows.bind('<Configure>', lambda _e: canvas.configure(scrollregion=canvas.bbox('all')))
    canvas.bind('<Configure>', lambda e: canvas.itemconfigure(item, width=e.width))
    canvas.configure(yscrollcommand=scroll.set)
    scroll.pack(side='right', fill='y')
    canvas.pack(side='left', fill='both', expand=True)
    weights = {}
    for index, name in enumerate(config.FAMILIES):
        ttk.Label(rows, text=gems._PHRASES.get(name, name)).grid(row=index, column=0, sticky='w', padx=8, pady=3)
        weights[name] = tk.StringVar(value=f'{settings["weights"][name]:g}')
        ttk.Spinbox(rows, from_=.01, to=10, increment=.1, textvariable=weights[name], width=10).grid(row=index, column=1, padx=10)
    rows.columnconfigure(0, weight=1)
    status = tk.StringVar(value='只调整未来新生成的宝石。保存后下次启动游戏生效。')
    ttk.Label(frame, textvariable=status, wraplength=740).pack(anchor='w')
    buttons = ttk.Frame(frame)
    buttons.pack(fill='x', pady=(10, 0))
    state = {'busy': False}
    results = queue.Queue()

    def reset():
        for variable in weights.values():
            variable.set('1')

    def close():
        if not state['busy']:
            window.destroy()

    def finish():
        try:
            report, error = results.get_nowait()
        except queue.Empty:
            window.after(80, finish)
            return
        state['busy'] = False
        for button in (apply, reset_button, close_button):
            button.configure(state='normal')
        if error:
            status.set('生成失败，未发布半成品。')
            app.messagebox.showerror('宝石掉落调校', str(error), parent=window)
            return
        app.mod_order = []
        app.mod_vars = {}
        app.refresh_lists()
        app.var('mods_enabled', 'app').set(True)
        app.collect()
        status.set(f'已生成并启用：{len(report["source_rank_changes"])} 个来源范围、'
                   f'{report["changed_category_weights"]} 个类别权重。血岩开关保持原设置。')
        app.messagebox.showinfo('宝石掉落调校', status.get()+'\n下次启动生效；可在模组列表关闭 GemDropTuning。', parent=window)

    def commit():
        if state['busy']:
            return
        try:
            value = config.validate({'max_roll':maximum.get(), 'weights':{name:float(var.get()) for name, var in weights.items()}})
            if app.process is not None:
                raise ValueError('请先完全退出游戏。')
            gems.saves.assert_game_closed(port)
            custom = app.var('mods_dir', 'app').get()
            if custom and Path(custom).absolute() != port/'mods':
                raise ValueError('此功能目前使用安装目录下的 mods；请先在模组页恢复默认模组目录。')
            if not portable.is_file() and (not python.is_file() or not tool.is_file()):
                raise ValueError('找不到保留的 MOD 构建环境或构建工具。')
            game = Path(app.var('game_dir', 'app').get())
            if not (game/config.PARAM).is_file():
                raise ValueError('请先设置正确的原游戏目录。')
        except Exception as error:
            app.messagebox.showerror('无法生成', str(error), parent=window)
            return
        if not app.messagebox.askyesno('确认生成宝石掉落 MOD', '生成并启用 GemDropTuning？\n'
                '权重从原版参数重新计算，不会叠乘上次修改。\n同时开启模组加载，其他模组按当前勾选状态生效。\n血岩 MOD 的现有开关保持不变，已有宝石和存档不修改。', parent=window):
            return
        app.collect()  # Persist the visible mod switches before the builder merges its selection.
        state['busy'] = True
        for button in (apply, reset_button, close_button):
            button.configure(state='disabled')
        status.set('正在构建并校验参数覆盖层…')
        def worker():
            try:
                with tempfile.TemporaryDirectory(prefix='gem-drop-') as temporary:
                    path = Path(temporary)/'settings.json'
                    path.write_text(json.dumps(value), encoding='utf-8')
                    run = subprocess.run(([str(portable)] if portable.is_file() else [str(python), str(tool)]) + ['--port',str(port),'--game',str(game),'--config',str(path)],
                        capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=180,
                        creationflags=getattr(subprocess, 'CREATE_NO_WINDOW',0), env=dict(os.environ,PYTHONUTF8='1'))
                    if run.returncode:
                        raise RuntimeError((run.stderr or run.stdout)[-3000:])
                report = json.loads((port/'mods'/config.NAME/'validation.json').read_text(encoding='utf-8'))
                results.put((report,None))
            except Exception as error:
                results.put((None,error))
        threading.Thread(target=worker,daemon=True).start()
        window.after(80, finish)

    reset_button = ttk.Button(buttons,text='全部恢复原权重',command=reset)
    reset_button.pack(side='left')
    apply = ttk.Button(buttons,text='生成并启用',command=commit)
    apply.pack(side='right')
    close_button = ttk.Button(buttons,text='关闭',command=close)
    close_button.pack(side='right',padx=8)
    window.protocol('WM_DELETE_WINDOW', close)
    bind_modal_wheel(window, fallback=canvas)
    window.gem_drop_controls = {'maximum':maximum,'weights':weights,'commit':commit,'state':state}
    return window
