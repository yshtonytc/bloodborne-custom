# 血源中文定制分支

维护仓库：`yshtonytc/bloodborne-custom`，默认分支 `custom`。
`upstream-windows` 保存最近同步的官方发布源码，`custom` 在其上维护本地功能。
不需要每次重新 Fork，不改原作者仓库，也不依赖其合并 PR。

## 更新到作者新版

默认由 **Bloodborne custom Windows** 每 6 小时检查一次上游正式版。
没有新版本且已有成品时跳过；有新版时合并、检查新增中文、回归测试、构建并验证字体和程序清单，
全部成功后才推送维护分支并发布。冲突、缺翻译和任何构建失败均不会发布。

手动检查可运行工作流并勾选 `check_only`，不启动 Windows 构建。
人工修复后发布：`upstream_tag` 填准确目标（或留空使用当前基线），勾选 `publish`。
不勾选 publish 的试构建不会推送临时合并；后续发布需再次指定同一目标标签。

本机使用 `update-local.cmd`，也可双击工作区的 `升级两个游戏.cmd`。
只下载校验后的成品，不重新合并或编译；已最新立即结束。
GUI 检查已在发布 CI 完成，排障时用准确 `--tag` 加 `--verify-gui` 在本机重做。

有冲突时流程会停止，既不覆盖定制源码，也不发布半成品。在本地执行：

```powershell
git checkout custom
python custom/sync_upstream.py --tag latest
# 如有冲突：逐一解决，git add 对应文件，再 git commit。
# 再运行相同命令记录版本和哈希，推送定制分支。
python custom/sync_upstream.py --tag latest --push
```

发布后，定制启动器只检查本仓库 Release，使用上游的安全安装器。
不直接覆盖为原作者的未定制包。所有游戏文件、存档、缓存和设置均留在用户本机。

## 构建

Windows、Python 3.12；安装 pyinstaller、pillow、fonttools、capstone、pefile，
`pip install --target tools-local/zig ziglang==0.13.0`。
运行 `python custom/build_release.py`、`python custom/verify_package.py`。
输出在 `dist/custom`；首次需要下载已固定哈希的官方包、字体及第三方源码。
运行时修改只针对移植版程序和模组覆盖层，不自动替换原游戏 eboot.bin。

宝石描述索引来自 GPL-3.0 项目，保留原作者署名和许可证；组合发布遵循 GPL-3.0，
上游源码仍保留原有许可及著作权声明。中文字体为 SIL OFL 1.1 的 Noto Sans SC，
来源提交和 SHA-256 在 `custom/font.json`。不发布本机微软雅黑子集。
离线地图服务保留，地图数据由用户自行准备并保留 GameGene 来源署名。
