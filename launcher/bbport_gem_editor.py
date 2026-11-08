"""Chinese offline gem editor for the local launcher; save only on explicit confirmation."""
import queue
import threading

import bbport_gem_save as backend
from bbport_save_manager import _user_dir
from bbport_dialog_ui import bind_modal_wheel


def concise(value):
    return backend.effect_text(value).split('  [', 1)[0]


def build_controls(app, parent, port):
    holder = app.ttk.Frame(parent)
    app.ttk.Button(holder, text='编辑存档宝石…', command=lambda: open_editor(app, port)).pack(side='left')
    app.row(parent, '宝石词条编辑', holder, '退出游戏后修改已有宝石；保存前自动备份，备份可在“选择备份恢复”中找回。')


def open_editor(app, port):
    previous = getattr(app, 'gem_editor_window', None)
    if previous is not None and previous.winfo_exists():
        previous.lift()
        return previous
    user = _user_dir(app, port).absolute()
    try:
        if app.process is not None:
            raise RuntimeError('请先完全退出游戏。')
        backend.saves.assert_game_closed(port)
        found = backend.list_characters(user)
        if not found:
            raise ValueError('没有找到可编辑的角色存档。')
    except Exception as error:
        app.messagebox.showerror('宝石词条编辑', str(error), parent=app.root)
        return
    tk, ttk = app.tk, app.ttk
    window = app.gem_editor_window = tk.Toplevel(app.root)
    window.title('存档宝石词条编辑')
    window.transient(app.root)
    window.configure(bg=app.root.cget('background'))
    window.geometry(f'{min(app.px(1150), window.winfo_screenwidth()-80)}x{min(app.px(820), window.winfo_screenheight()-100)}')
    window.grab_set()
    frame = ttk.Frame(window, padding=14)
    frame.pack(fill='both', expand=True)
    ttk.Label(frame, text='选择主词条类别、伤害档位和负面词缀；选项按原版掉落组合联动。确认保存前不修改存档。',
              wraplength=1000).pack(anchor='w')
    ttk.Label(frame, text=str(backend.saves.save_dir(user)), style='Muted.TLabel').pack(anchor='w', pady=(2, 8))
    selector = ttk.Frame(frame)
    selector.pack(fill='x')
    ttk.Label(selector, text='角色：').pack(side='left')
    character = ttk.Combobox(selector, state='readonly', width=40, values=[
        f'槽位 {slot+1} · {info["character"]["name"]} · 等级 {info["character"]["level"]}' for slot, info in found])
    character.pack(side='left')
    type_row = ttk.Frame(frame)
    type_row.pack(fill='x',pady=(8,0))
    ttk.Label(type_row,text='主词条类别：').pack(side='left')
    category_choice = ttk.Combobox(type_row,state='disabled',width=20)
    category_choice.pack(side='left')
    ttk.Label(type_row,text='  主词条档位：').pack(side='left')
    tier_choice = ttk.Combobox(type_row,state='disabled',width=65)
    tier_choice.pack(side='left',fill='x',expand=True)
    effect_row = ttk.Frame(frame)
    effect_row.pack(fill='x',pady=(6,0))
    ttk.Label(effect_row,text='副词缀：').pack(side='left')
    secondary_choice = ttk.Combobox(effect_row,state='disabled',width=36)
    secondary_choice.pack(side='left',fill='x',expand=True)
    ttk.Label(effect_row,text='  负面词缀：').pack(side='left')
    curse_choice = ttk.Combobox(effect_row,state='disabled',width=40)
    curse_choice.pack(side='left',fill='x',expand=True)
    # Internal profile identity remains for full-combination validation/audit;
    # users select effects directly, never a whole-gem preset.
    profile_keys = [None]
    direct = {'categories': [], 'tiers': [], 'secondary': [], 'curses': [], 'curse_slot': None}
    status = tk.StringVar(value='选择宝石，再选择主词条档位和负面词缀。')
    body = ttk.Panedwindow(frame, orient='horizontal')
    body.pack(fill='both', expand=True, pady=10)
    left, right = ttk.Frame(body), ttk.Frame(body)
    body.add(left, weight=2)
    body.add(right, weight=3)
    gem_tree = ttk.Treeview(left, columns=('shape', 'effect'), show='headings', selectmode='browse', height=12)
    gem_tree.heading('shape', text='形状 / 实例')
    gem_tree.heading('effect', text='当前主词条')
    gem_tree.column('shape', width=app.px(150), minwidth=app.px(120), stretch=False)
    gem_tree.column('effect', width=app.px(240), minwidth=app.px(180))
    scroll = ttk.Scrollbar(left, command=gem_tree.yview)
    gem_tree.configure(yscrollcommand=scroll.set)
    scroll.pack(side='right', fill='y')
    horizontal = ttk.Scrollbar(left, orient='horizontal', command=gem_tree.xview)
    gem_tree.configure(xscrollcommand=horizontal.set)
    horizontal.pack(side='bottom', fill='x')
    gem_tree.pack(fill='both', expand=True)
    ttk.Label(right, text='词条预览（左边原值 → 右边修改值）').pack(anchor='w')
    preview_box = ttk.Frame(right)
    preview_box.pack(fill='x', pady=(4, 8))
    slots = ttk.Treeview(preview_box, columns=('slot', 'old', 'new'), show='headings', selectmode='browse', height=6)
    for name, label, width in [('slot', '效果槽', 60), ('old', '原词条', 230), ('new', '修改后', 230)]:
        slots.heading(name, text=label)
        slots.column(name, width=app.px(width), minwidth=app.px(55 if name == 'slot' else 170), stretch=name != 'slot')
    preview_scroll = ttk.Scrollbar(preview_box, orient='horizontal', command=slots.xview)
    slots.configure(xscrollcommand=preview_scroll.set)
    slots.pack(fill='x')
    preview_scroll.pack(fill='x')
    detail = tk.StringVar(value='选中效果槽可查看完整词条。')
    detail_label = ttk.Label(right, textvariable=detail, justify='left', wraplength=app.px(560))
    detail_label.pack(fill='x', pady=(0, 8))
    right.bind('<Configure>', lambda event: detail_label.configure(wraplength=max(180, event.width-12)))
    search_row = ttk.Frame(right)
    search_row.pack(fill='x')
    ttk.Label(search_row, text='搜索词条：').pack(side='left')
    query = tk.StringVar()
    search = ttk.Entry(search_row, textvariable=query)
    search.pack(side='left', fill='x', expand=True)
    count = ttk.Label(right, text='')
    count.pack(anchor='w')
    catalog_box = ttk.Frame(right)
    catalog_box.pack(fill='both', expand=True)
    catalog = ttk.Treeview(catalog_box, columns=('effect', 'rating', 'id'), show='headings', selectmode='browse', height=9)
    for name, label, width in [('effect', '候选词条', 340), ('rating', '档位', 55), ('id', 'ID', 85)]:
        catalog.heading(name, text=label)
        catalog.column(name, width=app.px(width), minwidth=app.px(180 if name == 'effect' else width), stretch=name == 'effect')
    scrollbar = ttk.Scrollbar(catalog_box, command=catalog.yview)
    catalog.configure(yscrollcommand=scrollbar.set)
    scrollbar.pack(side='right', fill='y')
    catalog_scroll = ttk.Scrollbar(catalog_box, orient='horizontal', command=catalog.xview)
    catalog.configure(xscrollcommand=catalog_scroll.set)
    catalog_scroll.pack(side='bottom', fill='x')
    catalog.pack(fill='both', expand=True)
    edit_row = ttk.Frame(right)
    edit_row.pack(side='bottom', fill='x', pady=(8, 0), before=catalog_box)
    bottom = ttk.Frame(frame)
    bottom.pack(side='bottom', fill='x', before=body)
    ttk.Label(bottom, textvariable=status, wraplength=900).pack(anchor='w', pady=(0, 6))
    state = {'info': None, 'slot': None, 'gem': None, 'effects': [], 'busy': False, 'poll': None}
    results = queue.Queue()
    labels = {key: backend.effect_text(key) for key in backend.EFFECTS}
    searchable = {key: (label + ' ' + ' '.join(str(v) for v in backend.EFFECTS[key])).lower()
                  for key, label in labels.items()}

    def show_detail(_event=None):
        selected = slots.selection()
        if not state['gem'] or not selected:
            detail.set('选中效果槽可查看完整词条。')
            search_effects()
            return
        index = int(selected[0])
        detail.set(f'原词条：{backend.effect_text(state["gem"]["effects"][index])}\n'
                   f'修改后：{backend.effect_text(state["effects"][index])}')
        search_effects()

    def refresh_preview():
        sync_direct()
        selected = slots.selection()
        slots.delete(*slots.get_children())
        if state['gem']:
            for i, (old, new) in enumerate(zip(state['gem']['effects'], state['effects'])):
                slots.insert('', 'end', iid=str(i), values=(f'{i+1}'+(' 主' if i == 0 else ''),
                    concise(old), concise(new)))
            slots.selection_set(selected[0] if selected else '0')
        enabled = state['gem'] is not None and state['effects'] != state['gem']['effects'] and not state['busy']
        save.configure(state='normal' if enabled else 'disabled')
        editable = state['gem'] is not None and backend.legality.policy(state['gem'])['editable'] and not state['busy']
        assign_button.configure(state='normal' if editable else 'disabled')
        clear_button.configure(state='normal' if editable else 'disabled')
        show_detail()

    def family(value):
        text = concise(value)
        return text.split(' +', 1)[0].split(' -', 1)[0]

    def tier_options(category):
        return [(key,value) for key in profile_keys[1:]
                for value in backend.legality.PROFILES[key]['pools'][0] if family(value) == category]

    def fill_effect_choice(combo, name, values, current):
        direct[name] = list(values)
        combo.configure(values=[concise(value) for value in values],
                        state='readonly' if len(values)>1 and not state['busy'] else 'disabled')
        if current in values:
            combo.current(direct[name].index(current))
        else:
            combo.set(concise(current))

    def sync_direct():
        gem = state['gem']
        if not gem:
            for combo in (category_choice,tier_choice,secondary_choice,curse_choice):
                combo.configure(state='disabled',values=[])
                combo.set('')
            return
        direct['categories'] = list(dict.fromkeys(family(value) for key in profile_keys[1:]
            for value in backend.legality.PROFILES[key]['pools'][0]))
        current_family = family(state['effects'][0])
        category_choice.configure(values=direct['categories'],state='disabled' if state['busy'] else 'readonly')
        category_choice.set(current_family)
        direct['tiers'] = tier_options(current_family)
        tier_choice.configure(values=[concise(value)+' · '+backend.legality.PROFILES[key]['label']
            for key,value in direct['tiers']],state='disabled' if state['busy'] else 'readonly')
        key = gem.get('table_profile')
        pair = (key,state['effects'][0])
        if pair in direct['tiers']:
            tier_choice.current(direct['tiers'].index(pair))
        else:
            tier_choice.set(concise(state['effects'][0])+' · 当前值（未修改）')
        profile = backend.legality.PROFILES.get(key)
        if profile is None:
            direct['curse_slot'] = None
            fill_effect_choice(secondary_choice,'secondary',(),state['effects'][1])
            fill_effect_choice(curse_choice,'curses',(),backend.EMPTY)
            curse_choice.set('先选择主词条档位')
            return
        # Negative effects are after the optional secondary in these verified recipes.
        curse_slot = next((i for i in (1,2) if any(value != backend.EMPTY and
            backend.EFFECTS[value][1].startswith(('ATK DOWN','ATK vs the kin DOWN','ATK vs beasts DOWN',
                'Increases stamina costs','HP gradually depletes','WPN durability DOWN'))
            for value in profile['pools'][i])),None)
        direct['curse_slot'] = curse_slot
        secondary = backend.legality.candidates(gem,1,state['effects']) if curse_slot != 1 and profile['pools'][1] != (backend.EMPTY,) else (backend.EMPTY,)
        fill_effect_choice(secondary_choice,'secondary',secondary,
            state['effects'][1] if curse_slot != 1 else backend.EMPTY)
        curses = backend.legality.candidates(gem,curse_slot,state['effects']) if curse_slot is not None else (backend.EMPTY,)
        fill_effect_choice(curse_choice,'curses',curses,
            state['effects'][curse_slot] if curse_slot is not None else backend.EMPTY)

    def set_tier(key,value):
        profile = backend.legality.PROFILES[key]
        proposed = list(profile['default'])
        # Preserve independently rolled negatives/secondaries whenever still allowed.
        for i in range(1,6):
            if state['effects'][i] in profile['pools'][i]:
                proposed[i] = state['effects'][i]
        proposed[0] = value
        gem = dict(state['gem'],table_profile=key)
        backend.legality.validate(gem,proposed)
        state['gem'] = gem
        state['effects'] = proposed
        status.set('已更新预览；仅在点击“备份并保存修改”并确认后写入。'+profile['label'])
        refresh_preview()

    def choose_category(_event=None):
        if state['busy'] or not state['gem']:
            return
        options = tier_options(category_choice.get())
        if options:
            set_tier(*options[0])

    def choose_tier(_event=None):
        if not state['busy'] and state['gem'] and tier_choice.current() >= 0:
            set_tier(*direct['tiers'][tier_choice.current()])

    def choose_effect(name,combo,index):
        if state['busy'] or not state['gem'] or index is None or combo.current()<0:
            return
        proposed = list(state['effects'])
        proposed[index] = direct[name][combo.current()]
        try:
            backend.legality.validate(state['gem'],proposed)
        except ValueError as error:
            app.messagebox.showwarning('不符合原版规则',str(error),parent=window)
            sync_direct()
            return
        state['effects'] = proposed
        refresh_preview()

    def choose_gem(_event=None):
        if state['busy']:
            return
        selection = gem_tree.selection()
        found_gem = next((g for g in state['info']['gems'] if str(g['handle']) == (selection[0] if selection else '')), None)
        state['gem'] = dict(found_gem) if found_gem else None
        state['effects'] = list(state['gem']['effects']) if state['gem'] else []
        if state['gem']:
            profile_keys[:] = [None,*backend.legality.available(state['gem'])]
            current = backend.legality.match(state['gem'],state['effects'])
            if current:
                state['gem']['table_profile'] = current
            status.set(backend.legality.policy(state['gem'])['reason'])
        refresh_preview()

    def choose_character(_event=None):
        slot, info = found[character.current()]
        state.update(slot=slot, info=info, gem=None, effects=[])
        gem_tree.delete(*gem_tree.get_children())
        for gem in info['gems']:
            gem_tree.insert('', 'end', iid=str(gem['handle']), values=(
                f'{gem["location"]} · {backend.SHAPES[gem["shape"]]} · {gem["handle"] & 0xffff}', concise(gem['effects'][0])))
        status.set(f'读取到 {len(info["gems"])} 颗宝石（含已镶嵌和仓库记录）。')
        refresh_preview()

    def search_effects(*_args):
        words = query.get().lower().split()
        selected = slots.selection()
        allowed = backend.legality.candidates(state['gem'], int(selected[0]), state['effects']) if state['gem'] and selected else ()
        matches = [key for key in allowed if all(word in searchable[key] for word in words)]
        catalog.delete(*catalog.get_children())
        for key in matches[:300]:
            catalog.insert('', 'end', iid=str(key), values=(concise(key), backend.EFFECTS[key][2], key))
        enabled = bool(allowed) and not state['busy'] and backend.legality.policy(state['gem'])['editable']
        assign_button.configure(state='normal' if enabled else 'disabled')
        count.configure(text=f'原版校验通过 {len(allowed)} 项；搜索匹配 {len(matches)} 项。')

    def assign(value=None):
        if state['busy'] or state['gem'] is None or not slots.selection():
            return
        if value is None:
            if not catalog.selection():
                return
            value = int(catalog.selection()[0])
        index = int(slots.selection()[0])
        if index == 0 and value == backend.EMPTY:
            app.messagebox.showwarning('宝石词条编辑', '主词条不能为空。', parent=window)
            return
        proposed = list(state['effects'])
        proposed[index] = value
        try:
            backend.legality.validate(state['gem'], proposed)
        except ValueError as error:
            app.messagebox.showwarning('不符合原版规则', str(error), parent=window)
            return
        state['effects'] = proposed
        refresh_preview()

    def reload():
        if state['busy']:
            return
        try:
            backend.saves.assert_game_closed(port)
            updated = backend.list_characters(user)
            found[:] = updated
            character.configure(values=[f'槽位 {s+1} · {i["character"]["name"]} · 等级 {i["character"]["level"]}' for s, i in found])
            if not found:
                raise ValueError('没有可编辑角色，请关闭窗口后重新打开。')
            character.current(0)
            choose_character()
        except Exception as error:
            app.messagebox.showerror('读取失败', str(error), parent=window)
            state.update(gem=None, effects=[])
            refresh_preview()

    def saving(value):
        state['busy'] = value
        character.configure(state='disabled' if value else 'readonly')
        for widget in (refresh, assign_button, clear_button, close):
            widget.configure(state='disabled' if value else 'normal')
        refresh_preview()

    def finish():
        try:
            result, error = results.get_nowait()
        except queue.Empty:
            state['poll'] = window.after(50, finish)
            return
        state['poll'] = None
        saving(False)
        if error:
            app.messagebox.showerror('保存失败', str(error), parent=window)
            status.set('保存失败，请重新读取；原存档或安全副本均保留。')
            state.update(gem=None, effects=[])
            refresh_preview()
        else:
            app.messagebox.showinfo('宝石已保存', '词条已写入存档。重新进入游戏查看效果。\n安全副本：\n'+result['safety'], parent=window)
            reload()
            status.set('保存完成。安全副本：'+result['safety'])

    def commit():
        if state['busy'] or not state['gem']:
            return
        try:
            backend.check_effects(state['gem']['effects'], state['effects'], state['gem'])
            if app.process is not None:
                raise RuntimeError('请先完全退出游戏。')
        except Exception as error:
            app.messagebox.showerror('无法保存', str(error), parent=window)
            return
        changes = '\n'.join(f'槽 {i+1}：{backend.effect_text(old)}\n    → {backend.effect_text(new)}'
            for i, (old, new) in enumerate(zip(state['gem']['effects'], state['effects'])) if old != new)
        question = f'角色：{character.get()}\n主词条：{tier_choice.get()}\n宝石实例：{state["gem"]["handle"]}\n\n{changes}\n\n先备份完整存档，再保存以上修改？'
        if not app.messagebox.askyesno('确认修改宝石', question, parent=window):
            return
        args = (user, port, state['slot'], state['info']['sha256'], state['gem']['handle'], list(state['effects']))
        selected_profile = state['gem'].get('table_profile')
        saving(True)
        status.set('正在备份、校验并保存，请稍候…')
        def worker():
            try:
                results.put((backend.apply(*args,table_profile=selected_profile), None))
            except Exception as error:
                results.put((None, error))
        threading.Thread(target=worker, daemon=True).start()
        state['poll'] = window.after(50, finish)

    def destroy():
        if not state['busy']:
            window.destroy()
    window.protocol('WM_DELETE_WINDOW', destroy)
    assign_button = ttk.Button(edit_row, text='替换选中效果槽', command=assign)
    assign_button.pack(side='left')
    clear_button = ttk.Button(edit_row, text='放弃此宝石修改', command=choose_gem)
    clear_button.pack(side='left', padx=8)
    refresh = ttk.Button(selector, text='重新读取（放弃未保存修改）', command=reload)
    refresh.pack(side='left', padx=10)
    save = ttk.Button(bottom, text='备份并保存修改', command=commit, state='disabled')
    save.pack(side='right')
    close = ttk.Button(bottom, text='关闭', command=destroy)
    close.pack(side='right', padx=8)
    gem_tree.bind('<<TreeviewSelect>>', choose_gem)
    character.bind('<<ComboboxSelected>>', choose_character)
    category_choice.bind('<<ComboboxSelected>>',choose_category)
    tier_choice.bind('<<ComboboxSelected>>',choose_tier)
    secondary_choice.bind('<<ComboboxSelected>>',lambda _event: choose_effect('secondary',secondary_choice,1))
    curse_choice.bind('<<ComboboxSelected>>',lambda _event: choose_effect('curses',curse_choice,direct['curse_slot']))
    catalog.bind('<Double-1>', lambda _event: assign())
    slots.bind('<<TreeviewSelect>>', show_detail)
    query.trace_add('write', search_effects)
    character.current(0)
    choose_character()
    search_effects()
    bind_modal_wheel(window)
    # GUI regression uses these callbacks with isolated fixtures, never actual saves.
    window.gem_editor = {'state': state, 'gems': gem_tree, 'slots': slots, 'catalog': catalog,
                         'query': query, 'assign': assign, 'save': commit, 'reload': reload,
                         'category_choice':category_choice,'tier_choice':tier_choice,'curse_choice':curse_choice,
                         'secondary_choice':secondary_choice,'direct':direct,'choose_tier':choose_tier,
                         'choose_effect':choose_effect,'choose_category':choose_category}
    return window
