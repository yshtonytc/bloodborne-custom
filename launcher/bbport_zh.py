"""Supplemental Simplified Chinese UI translations for the Windows 1.7.1 launcher."""

TRANSLATIONS = {
    'Frame generation': '帧生成', 'Fit to display refresh': '匹配显示器刷新率',
    'Multiplier': '倍数', 'Not loaded: {}: {}': '未加载：{}：{}',
    'FSR 3.1 makes one frame (2×); DLSS on a GeForce RTX 50 up to three (4×).':
        'FSR 3.1 每两帧间插入 1 帧（2 倍）；RTX 50 系列的 DLSS 最多插入 3 帧（4 倍）。',
    "Frames made between two of the game's: 60 FPS on screen becomes 120. Needs a display with that refresh rate (120 Hz or more at 60 FPS); it pauses when the display cannot show the extra frames. Adds a little input latency. Menus and movies are not generated. DLSS needs a GeForce RTX 40 or newer, otherwise FSR 3.1 is used.":
        '在游戏渲染帧之间生成额外画面，例如将 60 帧显示为 120 帧。显示器需支持相应刷新率（游戏 60 帧时需至少 120 Hz）；无法显示额外帧时会暂停插帧。会增加少量输入延迟，菜单和过场影片不插帧。DLSS 需要 RTX 40 或更新显卡，否则使用 FSR 3.1。',
    'On: no more frames than the display shows (an uncapped game gets fewer generated frames, and the GPU does less). Off: the multiplier as chosen.':
        '开启：生成帧数不超过显示器刷新率，减少多余插帧和显卡开销。关闭：按所选倍数生成帧。',
    'Offline maps (F10)': '离线地图（F10）',
    'Enable offline maps while playing (F10)': '游戏中启用离线地图（F10）',
    'HUD position (ultrawide)': '界面位置（超宽屏）',
    '21:9 outputs: health, items and Blood Echoes at the screen edges, or in the centred 16:9 area as on a 16:9 screen.': '21:9 输出时，可将血量、物品和血之回响放在屏幕边缘，或像普通屏幕一样放在中央的 16:9 区域。',
    'Screen edges': '屏幕边缘', 'Halfway': '中间位置', 'Centred (16:9)': '居中（16:9）',
    'Quit to Desktop in the title menu and in the System menu': '在标题菜单和系统菜单中添加“退出到桌面”',
    'Online (SuperMedo Server)': '在线联机（SuperMedo 服务器）',
    'SuperMedo Server': 'SuperMedo 服务器', 'SuperMedo Server account': 'SuperMedo 服务器账户',
    'Sign up for SuperMedo Server': '注册 SuperMedo 服务器账户',
    'SuperMedo Server could not be reached. Check your internet connection and try again.': '无法连接 SuperMedo 服务器，请检查网络连接后重试。',
    'The account you made at supermedo.com.': '在 supermedo.com 注册的账户。',
    "The connection to The Hunter's Dream is Awaken's port of bbhost's network code; bbhost and The Hunter's Dream are by droogie.": '猎人梦境连接使用 Awaken 移植的 bbhost 网络代码；bbhost 和猎人梦境由 droogie 开发。',
    'To play on SuperMedo Server, enter your supermedo.com username and password on the Online co-op page (Sign up there if you have no account).': '连接 SuperMedo 服务器前，请在“在线合作”页面输入 supermedo.com 用户名和密码；没有账户可在该页面注册。',
    'Username': '用户名',
    'Your eboot.bin is not the clean 1.09 one (modified, or from another dump). The port cannot patch it: the game runs at 30 FPS, the Game & effects options do nothing, and some scenes (like the cutscene after Rom) can freeze.\n\nReplace eboot.bin with the one from an unmodified 1.09 update.': '你的 eboot.bin 不是原始 1.09 版本（可能经过修改，或来自其他转储）。移植版无法应用补丁：游戏将以 30 帧运行，“游戏与效果”选项不会生效，部分场景（如罗姆战后的过场动画）可能卡死。\n\n请用未修改的 1.09 更新中的 eboot.bin 替换。',
    'shadNet: a shadNet server and its account. SuperMedo Server uses an account from supermedo.com.': 'shadNet：使用对应服务器及其账户。SuperMedo 服务器：使用 supermedo.com 账户。',
    'Mouse buttons and the scroll wheel are bound in the Buttons section above: press Set… and click or turn the wheel. They work while the mouse is captured (mouse look on).':
        '在上方“按键”区域点击“设置…”，再按鼠标按键或滚动滚轮即可绑定。鼠标被捕获时（启用鼠标视角）这些绑定才会生效。',
    'Press a key, a mouse button or turn the wheel…': '请按键盘、鼠标按键或滚动滚轮…',
    '(none)': '（未设置）',
    'Achievements': '成就', 'All': '全部', 'Earned': '已获得', 'Locked': '未获得',
    'Platinum': '白金', 'Gold': '金', 'Silver': '银', 'Bronze': '铜',
    'Controls': '控制设置', 'Buttons': '按键', 'Sticks': '摇杆',
    'Keyboard only': '仅支持键盘', 'Mouse look': '鼠标视角',
    'Enable mouse look': '启用鼠标视角', 'Mouse controls': '鼠标控制',
    'Camera (right stick)': '视角（右摇杆）', 'Movement (left stick)': '移动（左摇杆）',
    'Sensitivity': '灵敏度', 'Minimum turn speed': '最低转向速度',
    'How fast the camera turns for a given mouse movement.': '控制移动鼠标时视角转动的速度。',
    'A constant added on top of sensitivity; raises the floor for slow movements without affecting fast ones as much.':
        '在灵敏度基础上增加固定偏移量，提高缓慢移动时的转向速度，对快速移动的影响较小。',
    'F7 also toggles this in-game, instantly; F8 reloads these settings without restarting.':
        '游戏中按 F7 可立即切换鼠标视角，按 F8 可重新加载设置，无需重启。',
    'Changes apply the next time the game starts, or press F8 in-game to reload input.ini without restarting.':
        '更改会在下次启动游戏时生效；也可在游戏中按 F8 重新加载 input.ini，无需重启。',
    'Keyboard and mouse-button bindings. The controller keeps working side by side; edit its lines in input.ini directly — see docs/INPUT.md.':
        '设置键盘和鼠标按键映射，手柄仍可同时使用。手柄映射需直接编辑 input.ini，详见 docs/INPUT.md。',
    'Click "Set…" on a button row to bind a mouse button instead of a key — left, middle, right, or the side buttons (back/forward), if the mouse has them. Stick directions stay keyboard-only.':
        '点击按键旁的“设置…”可绑定键盘或鼠标左键、中键、右键及侧键（后退／前进）。摇杆方向仅支持键盘。',
    'Reserved: Insert/Escape (the port\'s menu), F9 (route recording), and whichever key toggles mouse look or reloads input.ini (F7/F8 by default). A key or button already used elsewhere is simply bound to both actions (hold it to trigger both) — this page does not warn about that.':
        '保留快捷键：Insert/Escape（菜单）、F9（路线录制），以及鼠标视角切换和配置重载键（默认 F7/F8）。重复绑定会同时触发多个动作，此页面不会提示冲突。',
    'The scroll wheel is configured in input.ini directly (see docs/INPUT.md) — mouse buttons are bound from the Buttons section above.':
        '鼠标滚轮需在 input.ini 中配置（详见 docs/INPUT.md）；鼠标按键可在上方“按键”区域设置。',
    'Set…': '设置…', 'Press a key or mouse button…': '请按键盘或鼠标按键…',
    'Press a key…': '请按键…', 'Reserved': '保留快捷键', 'Unsupported key': '不支持的按键',
    'A stick direction can only be bound to a key, not a mouse button.': '摇杆方向只能绑定键盘按键，不能绑定鼠标按键。',
    'That key has no bbport name; pick another one.': 'bbport 不支持此按键，请选择其他按键。',
    '{} is reserved (menu, recording, or a hotkey) and cannot be bound to a game action.': '{} 是保留快捷键（菜单、录制或其他功能），不能绑定游戏动作。',
    'Cross': '叉键（×）', 'Circle': '圆圈键（○）', 'Square': '方块键（□）', 'Triangle': '三角键（△）',
    'R3 (lock-on)': 'R3（锁定目标）', 'Options': '选项键',
    'D-pad up': '方向键：上', 'D-pad down': '方向键：下', 'D-pad left': '方向键：左', 'D-pad right': '方向键：右',
    'Touchpad (left click)': '触摸板左侧', 'Touchpad (right click)': '触摸板右侧',
    'Move left': '向左移动', 'Move right': '向右移动', 'Move forward': '向前移动', 'Move back': '向后移动',
    'Camera left': '视角向左', 'Camera right': '视角向右', 'Camera up': '视角向上', 'Camera down': '视角向下',
    'Text language': '游戏文字语言', 'Voice language': '语音语言',
    'As in the game uses the original voice setting; other choices use available tracks.': '“跟随游戏”使用游戏原有语音设置；其他选项使用已有的对应语音资源。',
    'Native AA (×1.0)': '原生抗锯齿（×1.0）', 'Quality (×1.5)': '质量（×1.5）',
    'Balanced (×1.7)': '平衡（×1.7）', 'Performance (×2)': '性能（×2）', 'Ultra Performance (×3)': '超高性能（×3）',
    'Precise': '精确', 'FIFO (VSync)': 'FIFO（垂直同步）', 'FIFO Relaxed': '自适应 FIFO',
    'No limit': '不限制',
    'No trophies yet. They appear here as soon as the game unlocks them.': '尚未获得奖杯。游戏解锁后会显示在这里。',
    'Every trophy is earned. Hail, good hunter.': '已获得全部奖杯。向你致敬，优秀的猎人。',
    'Trophies the game unlocks while you play; updated live, kept with your saves.': '显示游戏中解锁的奖杯，实时更新，并与存档一同保存。',
    "You've earned a trophy.": '你获得了一个奖杯。', 'Trophy {}': '奖杯 {}', '{} of {} trophies earned': '已获得 {} / {} 个奖杯',
    'The Old Hunters': '老猎人',
    'Co-op pool': '联机平台', 'Play with': '联机对象',
    'Co-op service {0}': '联机服务 {0}', 'Game server {0}': '游戏服务器 {0}',
    'Not signed in': '未登录', 'Not signed in: use "Sign in with Discord" above.': '尚未登录，请点击上方“使用 Discord 登录”。',
    'Sign in with Discord': '使用 Discord 登录', 'Sign-in failed: {}': '登录失败：{}',
    'Signed in as {}': '已登录：{}', 'Starting the sign-in…': '正在准备登录…',
    'In the page that opened ({0}), sign in with Discord and enter this code:': '在打开的页面（{0}）中使用 Discord 登录，并输入以下代码：',
    "Online (The Hunter's Dream)": '在线联机（猎人梦境）',
    "The Hunter's Dream (with bbhost players)": '猎人梦境（与 bbhost 玩家联机）',
    "The Hunter's Dream account": '猎人梦境账户', 'shadNet server': 'shadNet 服务器',
    "shadNet: the server and account below. The Hunter's Dream: the players of bbhost, the PC port by The Hunter's Dream's team; sign in with Discord below.":
        'shadNet：使用下方的服务器和账户。猎人梦境：与该团队的 PC 移植版 bbhost 玩家联机，请在下方使用 Discord 登录。',
    "To play online with The Hunter's Dream, sign in with Discord first.": '通过猎人梦境联机前，请先使用 Discord 登录。',
    "The bridge to The Hunter's Dream is bbbridge by MaskZeus; bbhost and The Hunter's Dream are by droogie.":
        '猎人梦境连接工具 bbbridge 由 MaskZeus 开发；bbhost 和猎人梦境由 droogie 开发。',
    'Show me on the live map': '在实时地图上显示我的位置',
    'thehuntersdream.com/map shows where players are and which bells ring: the game sends your position more often while you play.':
        'thehuntersdream.com/map 显示玩家位置和鸣钟情况；启用后，游戏会更频繁地上传你的位置。',
    'bbbridge-cli.exe is missing from this installation.': '安装目录中缺少 bbbridge-cli.exe。',
    '{0}: not reachable ({1})': '{0}：无法连接（{1}）', '{0}: reachable': '{0}：连接正常',
    'co-op test build': '联机测试版',
}

# IDs are stable; only display strings change, never unlock records.
TROPHIES = [
    ('血源诅咒', '获得所有奖杯。向你致敬！'),
    ('雅南日出', '熬过狩猎之夜，迎来新的一天。'),
    ('继承意志', '受月之魔物所困，立誓守望猎人梦境。'),
    ('童年开端', '成为幼年的上位者，引领人类进入新的童年。'),
    ('苏美鲁女王雅南', '击败古老迷宫的血之女王雅南。'),
    ('猎人精髓', '获得所有猎人武器。'),
    ('猎人工艺', '获得所有特殊猎人工具。'),
    ('武器大师', '获得一件强化至最高等级的武器。'),
    ('血宝石大师', '获得一颗极其珍贵的血宝石。'),
    ('符文大师', '获得一个极其珍贵的卡里尔符文。'),
    ('该隐赫斯特', '进入失落而荒废的该隐赫斯特城堡。'),
    ('圣歌团', '进入治愈教会高层组织圣歌团的领域。'),
    ('梦境之源', '发现废弃的旧工坊——猎人梦境的源头。'),
    ('噩梦教学楼', '进入漂浮于噩梦领域的拜尔金沃斯教学楼。'),
    ('加斯科因神父', '击败曾是加斯科因神父的野兽。'),
    ('主教阿梅利亚', '击败曾是主教阿梅利亚的野兽。'),
    ('雅南之影', '击败雅南之影。'),
    ('愚笨蜘蛛罗姆', '击败上位者：愚笨蜘蛛罗姆。'),
    ('重生古神', '击败重生古神。'),
    ('噩梦之主米科拉什', '击败噩梦之主米科拉什。'),
    ('梅高的奶妈', '击败上位者：梅高的奶妈。'),
    ('神职人员野兽', '击败神职人员野兽。'),
    ('渴血兽', '击败渴血兽。'),
    ('汉威克女巫', '击败汉威克女巫。'),
    ('黑兽帕尔', '击败黑兽帕尔。'),
    ('亚弥达拉', '击败上位者：亚弥达拉。'),
    ('殉道者洛加留斯', '击败殉道者洛加留斯。'),
    ('天界使者', '击败上位者：天界使者。'),
    ('宇宙之女伊碧塔丝', '击败上位者：宇宙之女伊碧塔丝。'),
    ('血宝石接触', '获得能赋予猎人武器特殊力量的血宝石。'),
    ('符文接触', '获得能赋予猎人特殊力量的卡里尔符文。'),
    ('苏美鲁圣杯', '获得封印雅南地下迷宫的苏美鲁圣杯。'),
    ('衰弱罗伦圣杯', '获得封印沙海中悲惨失落之地的衰弱罗伦圣杯。'),
    ('伊兹圣杯', '获得封印宇宙眷族故乡的伊兹大圣杯。'),
    ('老猎人的精髓', '获得所有老猎人武器。'),
    ('科斯的孤儿', '击败上位者：科斯的孤儿。'),
    ('圣剑路德维希', '击败曾是圣剑路德维希的野兽。'),
    ('星辰钟塔的玛利亚女士', '击败星辰钟塔的玛利亚女士。'),
    ('失败者', '击败尝试成为上位者的失败造物。'),
    ('初代主教劳伦斯', '击败曾是初代主教劳伦斯的野兽。'),
]


TRANSLATIONS.update({' (installed)': '（已安装）', ' (latest)': '（最新）', 'Button prompts': '按键提示', 'Camera': '镜头', 'Click a slot, then press a key, click a mouse button or turn the wheel; Esc cancels. Right-click a slot to clear it. Movement and camera directions take keys only.': '点击槽位后按下键盘按键、鼠标按钮或滚动滚轮；Esc 取消。右键点击槽位可清除绑定。移动和镜头方向仅支持键盘按键。', 'Close': '关闭', 'Combinations: hold Shift, Ctrl or Alt while pressing the key or mouse button (up to three inputs, such as Shift + left click). A held combination wins over the bindings on its parts, so left click and Shift + left click can be two actions. ⚠ marks an input another action uses too. A key that is both an action of its own and part of a combination is pressed on the way into it: with Shift on Circle, Shift + left click starts a sprint that ends as a dodge.': '组合键：按住 Shift、Ctrl 或 Alt，再按其他按键或鼠标按钮，最多三个输入，例如 Shift + 鼠标左键。组合键优先于其中的单键绑定，因此左键与 Shift + 左键可以执行不同动作。⚠ 表示其他动作也使用了此输入。如果组合键的一部分同时绑定了独立动作，按下时仍会触发该动作：例如 Shift 绑定圆圈时，Shift + 左键会先开始冲刺，松开时翻滚。', 'Could not load the list of versions: {}': '无法加载版本列表：{}', 'Dark Souls III layout': '黑暗之魂 3 布局', 'Direct (1:1, like a PC game)': '直接控制（1:1，类似 PC 游戏）', "Direct turns the game's camera by exact angles: no stick acceleration or turn-speed cap. It falls back to the stick while locked on.": '直接控制按精确角度转动镜头，没有摇杆加速和转速上限。锁定目标时会回退到摇杆模拟。', 'Field of view': '视野', 'How far the direct camera turns per mouse movement (1.00 = 900 counts per radian).': '直接控制模式下，每次鼠标移动对应的镜头转角（1.00 = 每弧度 900 个鼠标计数）。', 'How fast the camera turns for a given mouse movement in stick emulation.': '摇杆模拟模式下，鼠标移动对应的镜头转速。', 'Install': '安装', 'Install another version of the port, newer or older (back to {}). Saves, settings and mods are kept.': '安装其他版本，可升级或回退（最低 {}）。保留存档、设置和模组。', 'Install the older version {} now? The launcher closes, installs it and opens again. Saves and settings are kept. To stay on it, switch off "Check for updates when the launcher opens".': '现在安装旧版本 {}？启动器将关闭，安装后重新打开，并保留存档和设置。若要停留在此版本，请关闭“启动器打开时检查更新”。', 'Installed: v{}': '已安装：v{}', 'Invert horizontal': '水平反转', 'Invert vertical': '垂直反转', 'Keyboard and mouse bindings, up to three per action. The controller keeps working side by side; edit its lines in input.ini directly — see docs/INPUT.md.': '键鼠绑定，每个动作最多三个绑定。手柄可同时使用；手柄绑定请直接编辑 input.ini，参见 docs/INPUT.md。', 'Layout': '布局', 'Loading the list of versions…': '正在加载版本列表…', 'Minimum turn speed (stick)': '最低转速（摇杆）', 'Mouse buttons and the scroll wheel are bound in the slots above: click a slot, then click or turn the wheel. They work while the mouse is captured (mouse look on).': '鼠标按钮和滚轮可在上方槽位绑定：点击槽位后按鼠标按钮或滚动滚轮。仅在鼠标被捕获（鼠标控制镜头开启）时生效。', 'Mute when the game is in the background': '游戏在后台时静音', 'No versions found.': '未找到可用版本。', 'Other versions': '其他版本', 'Other versions…': '其他版本…', 'Press…': '请按键…', 'Replace your keyboard and mouse bindings with the Dark Souls III layout? Controller bindings stay as they are.': '将键鼠绑定替换为黑暗之魂 3 布局？手柄绑定保持不变。', "Reserved: Insert/Escape (the port's menu), F9 (route recording), and whichever key toggles mouse look or reloads input.ini (F7/F8 by default).": '保留按键：Insert/Escape（游戏内菜单）、F9（路线记录），以及切换鼠标控制镜头和重新加载 input.ini 的按键（默认 F7/F8）。', 'Sensitivity (direct)': '灵敏度（直接控制）', 'Sensitivity (stick)': '灵敏度（摇杆）', 'Stick emulation': '摇杆模拟', "The game's button icons: your keyboard and mouse keys while you play with them, the controller's (PlayStation, Xbox or Switch) while you use it.": '游戏中的按键图标：使用键鼠时显示键鼠按键，使用手柄时显示对应的 PlayStation、Xbox 或 Switch 图标。', 'Up and down as a multiple of left and right (1.00 = the same).': '垂直转动相对于水平转动的倍数（1.00 表示相同）。', 'Use the Dark Souls III layout': '使用黑暗之魂 3 布局', 'Version {} is already installed.': '版本 {} 已安装。', 'Vertical sensitivity': '垂直灵敏度', 'Vertical sensitivity and inverting apply to both camera modes.': '垂直灵敏度和反转设置对两种镜头模式均生效。', 'Vertical, in degrees. Every camera of the game is widened by the same amount.': '垂直视野，单位为度。游戏中所有镜头按相同幅度扩大视野。', 'WASD, Space to dodge, left click / Shift + left click to attack, right click / Shift + right click (or Ctrl) for the off hand, E interact, R item, F vial, Q lock on, Tab or Esc menu, and the 1:1 mouse camera. Replaces the keyboard and mouse bindings; the controller keeps its own.': 'WASD 移动，空格闪避，左键／Shift + 左键攻击，右键／Shift + 右键（或 Ctrl）使用副手，E 互动，R 使用道具，F 使用血瓶，Q 锁定，Tab 或 Esc 打开菜单，并启用 1:1 鼠标镜头。替换键鼠绑定，手柄绑定保持不变。', 'also {}': '另有 {}'})

def install(language_module, trophy_module):
    additions = dict(TRANSLATIONS)
    for trophy in trophy_module.TROPHIES:
        name, description = TROPHIES[trophy[0]]
        additions[trophy[1]] = name
        additions[trophy[2]] = description
    language_module.EXTRA_TRANSLATIONS.setdefault('zh', {}).update(additions)
    language_module._tables.pop('zh', None)

TRANSLATIONS.update({'Choose a backup to restore…': '选择备份恢复…', 'Save backups': '存档备份', 'Select a backup first.': '请先选择一份备份。', 'Close the game before restoring saves.': '恢复存档前请先退出游戏。', 'Backup: {}': '备份路径：{}', 'Close': '关闭', 'Backing up current saves and verifying restoration…': '正在备份当前存档并校验恢复结果…', 'Choose a backup by time and game ID. Restoring preserves the current saves in a separate verified safety copy.': '按时间和游戏编号选择备份；恢复前会单独备份当前存档，并校验复制结果。', 'Open backup folder': '打开备份目录', 'Reading save backups…': '正在读取存档备份…', 'Could not read backups: {}': '无法读取备份：{}', 'Restored and verified {} files.': '已恢复并校验 {} 个文件。', 'Previous saves preserved at: {}': '恢复前的存档已保存在：{}', '{} backups available.': '找到 {} 份可用备份。', 'Restore selected backup': '恢复选中备份', 'Restore backup {}?\n\nCurrent saves: {}\nBackup: {}\n\nThe current saves will be preserved first.': '恢复 {} 的备份？\n\n当前存档：{}\n备份路径：{}\n\n操作前会先保留当前存档。', 'Browse available save backups.': '查看可用的存档备份。', 'Restore saves': '恢复存档', 'Select a backup, then restore. No backup is deleted by this operation.': '选择备份后点击恢复；本次操作不会删除任何已有备份。', 'Warning: this backup has a different game ID and may be incompatible.': '注意：此备份的游戏编号与当前存档不同，可能不兼容。', 'Could not restore: {}': '无法恢复：{}', 'Current saves: {}': '当前存档：{}', 'Game exit backup': '退出时备份', 'Manual copy': '手动存档副本', 'Before-restore safety copy': '恢复前安全副本', 'Files': '文件数', 'Refresh': '刷新'})

TRANSLATIONS.update({'Safety copy': '安全副本'})

TRANSLATIONS.update({'Import saves from another version…': '导入其他版本存档…'})

TRANSLATIONS.update({'Backup time':'备份时间','Backup source':'备份来源','Game ID':'游戏编号','Size':'大小'})
