"""Save snapshot picker for the local Windows launcher."""
from datetime import datetime
from pathlib import Path
import threading
import bbport_save_restore as saves
import os
from bbport_dialog_ui import bind_modal_wheel

def _size(value):
    return f'{value / 1048576:.1f} MB' if value >= 1048576 else f'{value / 1024:.1f} KB'

def build_controls(app, parent, port, tr):
    holder = app.ttk.Frame(parent)
    app.save_restore_summary = app.ttk.Label(holder, text=tr('Browse available save backups.'))
    app.save_restore_summary.pack(side='left')
    app.ttk.Button(holder, text=tr('Choose a backup to restore…'),
        command=lambda: open_manager(app, port, tr)).pack(side='left', padx=(12, 0))
    app.row(parent, tr('Restore saves'), holder,
        tr('Choose a backup by time and game ID. Restoring preserves the current saves in a separate verified safety copy.'))

def refresh_summary(app, port, tr):
    # Scanning large legacy trees belongs to the picker worker, not a Tk redraw.
    if hasattr(app, 'save_restore_summary'):
        app.save_restore_summary.configure(text=tr('Browse available save backups.'))

def _user_dir(app, port):
    return Path(app.var('user_dir', 'app').get() or Path(os.environ.get('BB_DATA_DIR', port)) / 'user')

def open_manager(app, port, tr):
    previous = getattr(app, 'save_restore_window', None)
    if previous is not None and previous.winfo_exists():
        previous.lift()
        return
    tk, ttk = app.tk, app.ttk
    window = app.save_restore_window = tk.Toplevel(app.root)
    window.title(tr('Restore saves'))
    window.transient(app.root)
    window.configure(bg=app.root.cget('background'))
    window.geometry(f'{min(app.px(920), window.winfo_screenwidth()-80)}x{min(app.px(500), window.winfo_screenheight()-120)}')
    window.grab_set()
    frame = ttk.Frame(window, padding=16)
    frame.pack(fill='both', expand=True)
    user = _user_dir(app, port).resolve()
    ttk.Label(frame, text=tr('Current saves: {}').format(saves.save_dir(user)), wraplength=840).pack(anchor='w')
    ttk.Label(frame, text=tr('Select a backup, then restore. No backup is deleted by this operation.'),
              style='Muted.TLabel', wraplength=840).pack(anchor='w', pady=(4, 10))
    # Reserve the action area before the expanding list at all DPI scales.
    buttons = ttk.Frame(frame)
    buttons.pack(side='bottom',fill='x',pady=(8,0))
    information = ttk.Frame(frame)
    information.pack(side='bottom',fill='x')
    box = ttk.Frame(frame)
    box.pack(fill='both', expand=True)
    tree = ttk.Treeview(box, columns=('time', 'kind', 'titles', 'files', 'size'), show='headings', selectmode='browse')
    for column, label, width in [('time', 'Backup time', 180), ('kind', 'Backup source', 130),
                                 ('titles', 'Game ID', 155), ('files', 'Files', 65), ('size', 'Size', 95)]:
        tree.heading(column, text=tr(label))
        tree.column(column, width=app.px(width), minwidth=50, stretch=column in ('time', 'titles'))
    scroll = ttk.Scrollbar(box, orient='vertical', command=tree.yview)
    tree.configure(yscrollcommand=scroll.set)
    scroll.pack(side='right', fill='y')
    tree.pack(side='left', fill='both', expand=True)
    detail = ttk.Label(information, text='', style='Muted.TLabel', wraplength=840)
    detail.pack(anchor='w', pady=(8, 0))
    status = ttk.Label(information, text=tr('Reading save backups…'), wraplength=840)
    status.pack(anchor='w', pady=8)
    information.bind('<Configure>',lambda event:(detail.configure(wraplength=max(180,event.width-8)),
                                                status.configure(wraplength=max(180,event.width-8))))
    entries, state = {}, {'busy': False}

    def alive(): return bool(window.winfo_exists())
    def selected():
        selection = tree.selection()
        return entries.get(selection[0]) if selection else None
    def selection_changed(_event=None):
        entry = selected()
        detail.configure(text=(tr('Backup: {}').format(entry['path']) if entry else ''))
    tree.bind('<<TreeviewSelect>>', selection_changed)

    def busy(value):
        state['busy'] = value
        for button in (refresh, restore): button.configure(state='disabled' if value else 'normal')

    def loaded(found, error=None):
        if not alive(): return
        entries.clear()
        tree.delete(*tree.get_children())
        for index, entry in enumerate(found):
            key = str(index)
            entries[key] = entry
            kind = tr({'exit': 'Game exit backup', 'manual': 'Manual copy', 'safety': 'Safety copy'}[entry['kind']])
            tree.insert('', 'end', iid=key, values=(entry['time'], kind, ', '.join(entry['titles']) or '—',
                                                   entry['files'], _size(entry['bytes'])))
        if found:
            tree.selection_set('0')
            selection_changed()
        status.configure(text=(tr('Could not read backups: {}').format(error) if error else
                               tr('{} backups available.').format(len(found))))
        busy(False)

    def reload():
        busy(True)
        status.configure(text=tr('Reading save backups…'))
        def worker():
            try:
                found = saves.discover(user, port)
                app.ui_calls.put(lambda: loaded(found))
            except Exception as error:
                app.ui_calls.put(lambda error=error: loaded([], error))
        threading.Thread(target=worker, daemon=True).start()

    def finished(result, error):
        if not alive(): return
        busy(False)
        if error:
            app.messagebox.showerror(tr('Restore saves'), tr('Could not restore: {}').format(error), parent=window)
        else:
            message = tr('Restored and verified {} files.').format(result['files'])
            if result['safety']: message += '\n\n' + tr('Previous saves preserved at: {}').format(result['safety'])
            app.messagebox.showinfo(tr('Restore saves'), message, parent=window)
            app.refresh_status()
        reload()

    def restore_selected():
        entry = selected()
        if not entry:
            app.messagebox.showinfo(tr('Restore saves'), tr('Select a backup first.'), parent=window)
            return
        if app.process:
            app.messagebox.showwarning(tr('Restore saves'), tr('Close the game before restoring saves.'), parent=window)
            return
        question = tr('Restore backup {}?\n\nCurrent saves: {}\nBackup: {}\n\nThe current saves will be preserved first.').format(
            entry['time'], saves.save_dir(user), entry['path'])
        current = saves.describe(saves.save_dir(user))['titles'] if (saves.save_dir(user)).exists() else []
        if current and entry['titles'] and set(current).isdisjoint(entry['titles']):
            question += '\n\n' + tr('Warning: this backup has a different game ID and may be incompatible.')
        if not app.messagebox.askyesno(tr('Restore saves'), question, parent=window): return
        busy(True)
        status.configure(text=tr('Backing up current saves and verifying restoration…'))
        def worker():
            try:
                result = saves.restore(user, port, entry['path'])
                app.ui_calls.put(lambda: finished(result, None))
            except Exception as error:
                app.ui_calls.put(lambda error=error: finished(None, error))
        # Finishing the copy safely takes priority if the launcher window is closed.
        threading.Thread(target=worker, daemon=False).start()

    def open_folder():
        entry = selected()
        if entry: app.open_path(str(Path(entry['path']).parent))
    def close():
        if not state['busy']: window.destroy()
    refresh = ttk.Button(buttons, text=tr('Refresh'), command=reload)
    refresh.pack(side='left')
    ttk.Button(buttons, text=tr('Open backup folder'), command=open_folder).pack(side='left', padx=8)
    ttk.Button(buttons, text=tr('Close'), command=close).pack(side='right')
    restore = ttk.Button(buttons, text=tr('Restore selected backup'), command=restore_selected)
    restore.pack(side='right', padx=8)
    window.protocol('WM_DELETE_WINDOW', close)
    bind_modal_wheel(window)
    reload()
