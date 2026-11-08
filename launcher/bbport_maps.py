"""Offline regional maps shown in a separate window above the game (F10)."""
import ctypes
from ctypes import wintypes
from datetime import datetime
import hashlib
import json
import os
import queue
from pathlib import Path
import sys
import time
import threading
import tkinter as tk
from tkinter import ttk
import webbrowser
import uuid

from PIL import Image, ImageTk

TITLE = '血源地图 · F10 隐藏'
HOTKEY_ID = 0xBB10
WM_HOTKEY = 0x0312

def log(port, message):
    try:
        path = Path(port) / 'user/maps.log'
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open('a', encoding='utf-8') as stream:
            stream.write(f'{datetime.now().isoformat(timespec="seconds")} {message}\n')
    except OSError:
        pass


def open_process(pid):
    kernel = ctypes.windll.kernel32
    kernel.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    kernel.OpenProcess.restype = wintypes.HANDLE
    return kernel.OpenProcess(0x00100000, False, pid)


def read_control(path):
    try:
        return json.loads(Path(path).read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return {}


def write_control(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + f'.{os.getpid()}.new')
    temporary.write_text(json.dumps(value), encoding='utf-8')
    os.replace(temporary, path)


def process_alive(pid):
    if not isinstance(pid, int) or pid <= 0:
        return False
    handle = open_process(pid)
    if not handle:
        return False
    kernel = ctypes.windll.kernel32
    kernel.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    try:
        return kernel.WaitForSingleObject(handle, 0) == 0x102
    finally:
        kernel.CloseHandle(handle)


def foreground_is_game():
    user, kernel = ctypes.windll.user32, ctypes.windll.kernel32
    user.GetForegroundWindow.restype = wintypes.HWND
    user.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
    hwnd = user.GetForegroundWindow()
    pid = wintypes.DWORD()
    user.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    if pid.value == os.getpid():
        return True, hwnd
    kernel.OpenProcess.restype = wintypes.HANDLE
    handle = kernel.OpenProcess(0x1000, False, pid.value)
    if not handle:
        return False, hwnd
    try:
        size = wintypes.DWORD(32768)
        name = ctypes.create_unicode_buffer(size.value)
        kernel.QueryFullProcessImageNameW.argtypes = [wintypes.HANDLE, wintypes.DWORD,
                                                     wintypes.LPWSTR, ctypes.POINTER(wintypes.DWORD)]
        success = kernel.QueryFullProcessImageNameW(handle, 0, name, ctypes.byref(size))
        return bool(success and Path(name.value).name.lower() == 'bb-probe.exe'), hwnd
    finally:
        kernel.CloseHandle.argtypes = [wintypes.HANDLE]
        kernel.CloseHandle(handle)


class HotkeyListener:
    """Own the Windows hotkey queue on a thread that Tk cannot drain or block."""
    def __init__(self, port):
        self.port = port
        self.events = queue.SimpleQueue()
        self.stopping = threading.Event()
        self.thread = threading.Thread(target=self.listen, daemon=True)
        self.thread.start()

    def listen(self):
        user = ctypes.windll.user32
        registered = False
        last_error = None
        message = wintypes.MSG()
        user.PeekMessageW(ctypes.byref(message), None, 0, 0, 0)
        try:
            while not self.stopping.is_set():
                active, _hwnd = foreground_is_game()
                if active and not registered:
                    registered = bool(user.RegisterHotKey(None, HOTKEY_ID, 0x4000, 0x79))
                    if not registered:
                        error = ctypes.windll.kernel32.GetLastError()
                        if error != last_error:
                            log(self.port, f'F10 registration failed: Windows error {error}')
                            last_error = error
                elif not active and registered:
                    user.UnregisterHotKey(None, HOTKEY_ID)
                    registered = False
                while user.PeekMessageW(ctypes.byref(message), None, WM_HOTKEY, WM_HOTKEY, 1):
                    if message.wParam == HOTKEY_ID and active:
                        self.events.put('toggle')
                self.stopping.wait(.01)
        except Exception as error:
            log(self.port, f'F10 listener failed: {type(error).__name__}: {error}')
        finally:
            if registered:
                user.UnregisterHotKey(None, HOTKEY_ID)

    def close(self):
        self.stopping.set()
        self.thread.join(timeout=1)


class MapWindow:
    def __init__(self, root, port, service=False, watch_pid=0, event=None):
        self.root, self.port = root, Path(port)
        self.root.withdraw()
        self.manifest = json.loads((self.port / 'maps/maps.json').read_text(encoding='utf-8'))
        self.entries = self.manifest['maps']
        if not self.entries:
            raise ValueError('地图目录为空')
        self.state_file = self.port / 'user/map-view.json'
        try:
            self.selected = int(json.loads(self.state_file.read_text(encoding='utf-8')).get('selected', 0))
        except (OSError, ValueError, TypeError):
            self.selected = 0
        self.selected = max(0, min(len(self.entries) - 1, self.selected))
        self.visible = self.closed = self.has_shown = False
        self.hotkeys = None
        self.game_hwnd = None
        self.event, self.watch_pid = event, watch_pid
        self.service_file = self.port / 'user/map-service.json'
        self.command_file = self.port / 'user/map-command.json'
        self.parent_handle = open_process(watch_pid) if watch_pid else None
        self.scale, self.x, self.y = 1.0, 0.0, 0.0
        self.drag_start = None
        self.image = self.photo = None
        self.pending = None
        self.root.title(TITLE)
        self.root.configure(bg='#151210')
        self.root.attributes('-topmost', True)
        width = min(1400, int(root.winfo_screenwidth() * .88))
        height = min(950, int(root.winfo_screenheight() * .84))
        self.root.geometry(f'{width}x{height}+60+60')
        self.root.minsize(760, 520)
        self.root.option_add('*Font', ('Microsoft YaHei UI', 10))
        style = ttk.Style(root)
        style.theme_use('clam')
        style.configure('.', font=('Microsoft YaHei UI', 10))
        toolbar = ttk.Frame(root, padding=8)
        toolbar.pack(fill='x')
        self.region = ttk.Combobox(toolbar, state='readonly', width=25,
                                  values=[entry['title'] for entry in self.entries])
        self.region.current(self.selected)
        self.region.pack(side='left', padx=(0, 10))
        self.region.bind('<<ComboboxSelected>>', lambda _e: self.select(self.region.current()))
        for label, command in [('－', lambda: self.zoom(.8)), ('＋', lambda: self.zoom(1.25)),
                               ('适应窗口', self.fit), ('原图', self.original),
                               ('来源网页', self.open_source), ('隐藏（F10）', self.hide),
                               ('退出地图', self.close)]:
            ttk.Button(toolbar, text=label, command=command).pack(side='left', padx=3)
        self.canvas = tk.Canvas(root, bg='#211e19', highlightthickness=0, width=1100, height=700)
        self.canvas.pack(fill='both', expand=True)
        self.canvas.bind('<Configure>', lambda _e: self.schedule_render())
        self.canvas.bind('<MouseWheel>', self.wheel)
        self.canvas.bind('<ButtonPress-1>', self.begin_drag)
        self.canvas.bind('<B1-Motion>', self.drag)
        self.canvas.bind('<ButtonRelease-1>', lambda _e: setattr(self, 'drag_start', None))
        self.canvas.bind('<Double-Button-1>', lambda _e: self.fit())
        self.status = tk.StringVar()
        ttk.Label(root, textvariable=self.status, padding=(8, 4)).pack(fill='x')
        ttk.Label(root, text='滚轮缩放 · 左键拖动 · 双击适应窗口 · F10 / Esc 隐藏 · 地图不会暂停游戏',
                  padding=(8, 3)).pack(fill='x')
        ttk.Label(root, text=self.manifest['credit'], padding=(8, 3)).pack(fill='x')
        # Closing a manually opened window must not remove F10 during a later game.
        self.root.protocol('WM_DELETE_WINDOW', self.hide if service else self.close)
        self.root.bind('<Escape>', lambda _e: self.hide())
        self.root.bind('<plus>', lambda _e: self.zoom(1.25))
        self.root.bind('<minus>', lambda _e: self.zoom(.8))
        self.select(self.selected)
        if service:
            self.hotkeys = HotkeyListener(self.port)
            self.root.after(20, self.poll)

    def select(self, index):
        path = (self.port / 'maps' / self.entries[index]['file']).resolve()
        if path.parent != (self.port / 'maps').resolve():
            raise ValueError('地图路径无效')
        with Image.open(path) as image:
            self.image = image.convert('RGB')
        self.selected = index
        self.fit()

    def dimensions(self):
        return max(1, self.canvas.winfo_width()), max(1, self.canvas.winfo_height())

    def fit(self):
        if self.image is None:
            return
        self.root.update_idletasks()
        width, height = self.dimensions()
        if width < 20 or height < 20:
            width, height = 1100, 700
        self.scale = min(width / self.image.width, height / self.image.height) * .97
        self.x = (width - self.image.width * self.scale) / 2
        self.y = (height - self.image.height * self.scale) / 2
        self.schedule_render()

    def original(self):
        self.zoom(1 / self.scale)

    def zoom(self, factor, x=None, y=None):
        width, height = self.dimensions()
        x = width / 2 if x is None else x
        y = height / 2 if y is None else y
        new_scale = max(.01, min(8.0, self.scale * factor))
        ratio = new_scale / self.scale
        self.x = x - (x - self.x) * ratio
        self.y = y - (y - self.y) * ratio
        self.scale = new_scale
        self.schedule_render()

    def wheel(self, event):
        self.zoom(1.2 if event.delta > 0 else 1 / 1.2, event.x, event.y)
        return 'break'

    def begin_drag(self, event):
        self.drag_start = (event.x, event.y, self.x, self.y)

    def drag(self, event):
        if self.drag_start:
            x, y, previous_x, previous_y = self.drag_start
            self.x, self.y = previous_x + event.x - x, previous_y + event.y - y
            self.schedule_render()

    def schedule_render(self):
        if self.pending is None:
            self.pending = self.root.after(12, self.render)

    def render(self):
        self.pending = None
        width, height = self.dimensions()
        if width < 2 or height < 2:
            return
        # Crop to the visible viewport before resizing; huge maps never allocate huge zoomed images.
        left = max(0, int(-self.x / self.scale))
        top = max(0, int(-self.y / self.scale))
        right = min(self.image.width, int((width - self.x) / self.scale) + 1)
        bottom = min(self.image.height, int((height - self.y) / self.scale) + 1)
        self.canvas.delete('map')
        if right > left and bottom > top:
            crop = self.image.crop((left, top, right, bottom))
            size = (max(1, round((right - left) * self.scale)),
                    max(1, round((bottom - top) * self.scale)))
            self.photo = ImageTk.PhotoImage(crop.resize(size, Image.Resampling.BILINEAR), master=self.root)
            self.canvas.create_image(self.x + left * self.scale, self.y + top * self.scale,
                                     image=self.photo, anchor='nw', tags='map')
        self.status.set(f'{self.entries[self.selected]["title"]} · {self.scale:.0%} · '
                        f'原图 {self.image.width} × {self.image.height} · 手动选区，无实时定位')

    def show(self):
        self.visible = True
        self.root.deiconify()
        self.root.lift()
        self.root.focus_force()
        self.root.update_idletasks()
        user = ctypes.windll.user32
        user.GetAncestor.argtypes = [wintypes.HWND, wintypes.UINT]
        user.GetAncestor.restype = wintypes.HWND
        hwnd = user.GetAncestor(self.root.winfo_id(), 2)  # Tk's outer top-level window
        user.SetForegroundWindow.argtypes = [wintypes.HWND]
        user.SetForegroundWindow(hwnd)
        if not self.has_shown:
            self.root.after(80, self.fit)
            self.has_shown = True
        else:
            self.schedule_render()
        log(self.port, 'Map shown')

    def hide(self):
        self.visible = False
        self.save_state()
        self.root.withdraw()
        log(self.port, 'Map hidden')
        if self.game_hwnd:
            ctypes.windll.user32.SetForegroundWindow.argtypes = [wintypes.HWND]
            ctypes.windll.user32.SetForegroundWindow(self.game_hwnd)

    def open_source(self):
        url = self.entries[self.selected]['page']
        if url.startswith('https://gamegene.cn/wiki/'):
            webbrowser.open(url)

    def save_state(self):
        try:
            self.state_file.parent.mkdir(parents=True, exist_ok=True)
            self.state_file.write_text(json.dumps({'selected': self.selected}), encoding='utf-8')
        except OSError:
            pass

    def poll(self):
        try:
            self.poll_once()
        except Exception as error:
            log(self.port, f'Hotkey check failed: {type(error).__name__}: {error}')
        if not self.closed:
            self.root.after(20, self.poll)

    def poll_once(self):
        kernel, user = ctypes.windll.kernel32, ctypes.windll.user32
        kernel.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
        # Process handoff before checking the old parent, including during restart.
        if self.event and kernel.WaitForSingleObject(self.event, 0) == 0:
            command = read_control(self.command_file)
            new_parent = command.get('watch_pid')
            if isinstance(new_parent, int) and new_parent > 0 and new_parent != self.watch_pid:
                if self.parent_handle:
                    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
                    kernel.CloseHandle(self.parent_handle)
                self.watch_pid = new_parent
                self.parent_handle = open_process(new_parent)
                log(self.port, f'Map service attached to game PID {new_parent}')
            if command.get('show'):
                self.show()
            write_control(self.service_file, {'owner_pid': os.getpid(), 'watch_pid': self.watch_pid,
                                              'request_id': command.get('request_id')})
        if self.watch_pid and (not self.parent_handle or kernel.WaitForSingleObject(self.parent_handle, 0) == 0):
            self.close()
            return
        active, hwnd = foreground_is_game()
        if active and not self.visible:
            self.game_hwnd = hwnd
        if self.hotkeys:
            while True:
                try:
                    self.hotkeys.events.get_nowait()
                except queue.Empty:
                    break
                self.hide() if self.visible else self.show()

    def close(self):
        self.closed = True
        if self.hotkeys:
            self.hotkeys.close()
        self.save_state()
        if self.parent_handle:
            ctypes.windll.kernel32.CloseHandle(self.parent_handle)
        self.root.destroy()
        if read_control(self.service_file).get('owner_pid') == os.getpid():
            self.service_file.unlink(missing_ok=True)
        log(self.port, 'Map viewer exited')


def run(port, watch_pid=0, show=False):
    kernel = ctypes.windll.kernel32
    kernel.CreateEventW.restype = wintypes.HANDLE
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    key = hashlib.sha256(str(Path(port).resolve()).lower().encode()).hexdigest()[:16]
    event = kernel.CreateEventW(None, False, False, f'Local\\bbport-maps-{key}')
    exists = kernel.GetLastError() == 183
    if exists:
        service_file = Path(port) / 'user/map-service.json'
        # An older viewer may be closing after its previous game. Wait for an
        # acknowledgement or take over if its process has already ended.
        owner = read_control(service_file).get('owner_pid')
        if process_alive(owner):
            request_id = uuid.uuid4().hex
            write_control(Path(port) / 'user/map-command.json',
                          {'watch_pid': watch_pid, 'show': show, 'request_id': request_id})
            kernel.SetEvent.argtypes = [wintypes.HANDLE]
            kernel.SetEvent(event)
            deadline = time.monotonic() + 3
            while time.monotonic() < deadline:
                reply = read_control(service_file)
                if reply.get('request_id') == request_id:
                    kernel.CloseHandle(event)
                    return 0
                if not process_alive(owner):
                    break
                time.sleep(.03)
            if process_alive(owner):
                log(port, 'Existing map viewer did not acknowledge command')
                kernel.CloseHandle(event)
                return 1
    try:
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except (AttributeError, OSError):
            pass
        root = tk.Tk()
        window = MapWindow(root, port, service=True, watch_pid=watch_pid, event=event)
        write_control(window.service_file, {'owner_pid': os.getpid(), 'watch_pid': watch_pid})
        log(port, f'Map viewer started; dedicated F10 listener; watch_pid={watch_pid}')
        if show:
            root.after(100, window.show)
        root.mainloop()
    finally:
        kernel.CloseHandle(event)
    return 0
