手柄震动增强（Windows SDL3）

入口：启动器 → 控制 → 手柄震动。强度 0/25/50/75/100%，默认 100%。
更改强度后下次启动游戏生效；测试按钮立即使用所选强度。
测试须先退出游戏，依次测试低频、高频、双马达各 250ms。
测试成功仅表示驱动接受指令，实际震感需用户确认。

实现
  bin/SDL3.dll：本地转发组件，仅拦截 SDL_OpenGamepad、SDL_RumbleGamepad。
  bin/SDL3-real.dll：当前官方包未经修改的 SDL3.dll。
  bin/rumble-test.exe：独立测试，不访问游戏或存档。
  bin/rumble-installed.json：官方 DLL、组件哈希及导出数量。
  所有其他 SDL 导出名称和序号均经过检查并转发到官方 DLL。
  bb-probe.exe 未因该功能而修改，保留原生菜单汉化。
  BB_RUMBLE_PERCENT=0..100 控制双马达等比例缩放。

日志
  默认 user/rumble.log，指定 BB_USER_DIR 时写入对应用户目录。
  记录 PID、系统计时、手柄名称、震动能力、强度、马达输入输出、时长和错误。
  记录前 20 次及此后每 300 次调用；错误记录前 10 次及之后每 300 次，避免每帧写盘。
  有 open 而没有 call：仅说明没有经过此接口的震动调用，不能据此认定具体原因。
  success=1 表示驱动接受，success=0 时查看 error。
  保留游戏自身的震动时机，不按攻击按键额外合成震动。

维护
  tools/build_native_rumble.py 由本地更新器对每个官方包重新构建。
  不得把旧 SDL3-real.dll 覆盖到新版；构建器拒绝把本地组件当成官方 DLL。
  构建使用 tools-local/zig 和 launcher-build 中的 pefile。
  tools/test_native_rumble.py 用模拟驱动测试强度、停止和失败传递，不驱动物理手柄。
  临时撤销：先退出游戏，以 SDL3-real.dll 的副本恢复 SDL3.dll，再重开游戏。
