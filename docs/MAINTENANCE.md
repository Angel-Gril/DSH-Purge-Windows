# 维护与版本升级

日常设备只运行 `update.ps1 -ApplyPurge`，不要各自在四个来源的 main 上直接 pull，造成无法复现的混装。

PI-only 设备更新省略 ApplyPurge；update 保留 active.json 的 modules。主入口保持 DSH + Purge，独立入口由 PI 启动。`pi-runtime/package-lock.json` 与 `mcp-runtime/package-lock.json` 分别锁定可选 PI 和独立 Seep 所需 JS MCP；它们不能依赖全局 npm 安装。更新时在对应目录运行 `npm install --package-lock-only --ignore-scripts`，不手写 integrity。

PI 新入口验证包括 `tests/integration_pi.py --root <独立新Root> --modules pi,apk,exe`、实际 PI SDK 资源加载、PI 原生 `mcp list`（选 Seep）、配置保留和负向请求。可用 `--source-cache <已验证工作台Root>` 从已有锁定源码复制 Git 对象，仍核对 SHA 与 origin；这不替代新设备的联网拉取验收。不要为自动测试读取真实模型凭据。

维护者为工作台更新基线时：

1. 在干净分支运行 `python scripts/refresh_sources.py --cache C:\AI\Workbench-Source-Review`，它通过目标机 Git 凭据拉源并生成 `sources.candidate.json`，不会自动改现有安装或发布版本。
2. 审查四个提交差异、包名、DSH兼容条件、Seep原生插件/内容层接口、Purge宿主定位和ASAR处理、APK/EXE同名技能。核对许可证；不要下载/上传用户配置。
3. 审查后替换sources.lock.json，更新release。若更新DSH/JS/YAML版本，修改runtime/package.json，并在该目录运行 `npm install --package-lock-only --legacy-peer-deps --ignore-scripts` 生成lock；不要手写integrity。Python核心依赖遵守Seep要求的mcp范围，必要时更新requirements.txt并检查实际依赖记录。
4. 执行 `tests/run.ps1`，在新的Root做 `install -WebOnly` + MCP握手、真实Web启动，再在兼容桌面宿主上分别验证插件、补丁、lab闸门、skills和模型请求。不能拿npm声明替代宿主实测。
5. 更新docs/VALIDATION.md，记录通过项和未验证项。逐文件审查git diff/staged内容并扫描凭据、大文件；提交并推送后各设备才通过update.ps1获得新基线。

Seep部署适配在scripts/workbench.py的build_generation中：把JS MCP的浮动npx替换成本地锁定Node入口，固定可选Playwright版本，并为link安装的插件创建指向受管宿主node_modules的本机junction。安装和doctor都会实际import插件，防止“YAML可组合但插件缺宿主依赖”。源码锚点变化会阻断，需要明确审查。不要把上游新版和旧适配代码混用。

Purge源码中可能仍指向它自己的npm/更新仓库；工作台保持autoUpdateOnStart=false。统一更新以Angel-Gril来源和本仓库锁定清单为准，不使用上游下载安装脚本切换fork。

已保存的旧源码/部署目录供回滚使用，不自动清理。手工清理前确认当前active.json和保留快照都不引用该目录。不要把snapshots/reports作为公开issue附件直接上传。
