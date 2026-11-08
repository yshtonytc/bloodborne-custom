"""Chinese rumble controls; motor tests run in a separate SDL process."""
import subprocess
import threading

def add_controls(app, parent, port_dir, environment):
    app.section(parent, '手柄震动')
    app.row(parent, '震动强度', app.choice(parent, 'rumble_percent', 'app',
            [(str(n), (('关闭' if n == 0 else f'{n}%'),)) for n in (0, 25, 50, 75, 100)]),
            '100% 为游戏原始强度；0% 关闭。更改后下次启动游戏生效。')
    button = app.ttk.Button(parent, text='测试手柄震动')
    app.row(parent, '震动测试', button,
            '短震依次测试低频、高频和双马达，使用上方强度。请先退出游戏；测试不会读写存档。')
    app.note(parent, '诊断日志：用户目录下的 rumble.log。记录手柄能力、游戏震动指令和驱动错误。')

    def start():
        # Also catch games launched outside this launcher, without touching them.
        running = subprocess.run(['tasklist', '/FI', 'IMAGENAME eq bb-probe.exe', '/FO', 'CSV', '/NH'],
                                 capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW)
        if app.process or b'bb-probe.exe' in running.stdout.lower():
            app.messagebox.showinfo('手柄震动', '请先正常退出游戏，再测试手柄震动。')
            return
        app.collect()
        button.configure(state='disabled')

        def finish(message):
            if button.winfo_exists():
                button.configure(state='normal')
                app.messagebox.showinfo('手柄震动', message)

        def worker():
            try:
                result = subprocess.run([str(port_dir / 'bin/rumble-test.exe')],
                    env=environment(app.app), capture_output=True, text=True, encoding='utf-8', errors='replace',
                    timeout=15, creationflags=subprocess.CREATE_NO_WINDOW)
                if result.returncode == 2:
                    message = '未检测到手柄，请检查连接。'
                elif result.returncode:
                    message = '震动测试失败。\n' + result.stdout + result.stderr
                else:
                    message = '驱动已接受三组震动指令，请确认手柄是否实际震动。\n' + result.stdout
            except (OSError, subprocess.TimeoutExpired) as error:
                message = '无法完成震动测试：' + str(error)
            app.ui_calls.put(lambda: finish(message))
        threading.Thread(target=worker, daemon=True).start()
    button.configure(command=start)
