# Windows 完整部署与迁移

## 1. 工作台包含什么

这是部署编排仓库，不把四个 Git 仓库做破坏性覆盖。下载的原始源码位于 `<Root>\sources\<id>\<commit>`，每次部署的插件/技能合成产物在 `<Root>\deployments\<时间-随机号>`。Git 仓库本身只有脚本、锁定清单和文档，不含你的密钥、会话、样本、IDA 二进制或许可证。

```text
<Root>\
  active.json                 当前部署的路径和选项，无 API key
  sources\                    四个来源，按完整 commit 固定
  runtimes\                   npm lock 对应的独立 DSH + JS MCP
  python\                     本机创建的 Python venv（不能跨设备直接复制）
  deployments\                每次部署的 Seep/Purge 插件与技能覆盖层
  dsh-home\profiles\web\     Web 包登记与 cordis.patch.yml
  dsh-home\profiles\desktop\ 桌面包登记与 cordis.patch.yml
  desktop-user-data\          独立 Electron 用户数据与单实例目录
  snapshots\                  配置和包依赖快照，可能含私人配置，别上传
  reports\                    本机诊断报告，分享前人工检查
  tools\                      可选外部工具和各技能的自定义工具目录
  samples\                    用户样本，不进 Git
  workspace\                  分析产物，不进 Git
```

Seep 原生 `seep-lab` 提供面板、会话 lab 闸门、skills、Seep MCP 和 JS MCP；APK/EXE 仓库提供自包含技能，不是假设存在的独立 MCP。插件使用 `contentRoot` 接入合成技能层，同名 `apk-reverse` / `exe-reverse` 优先采用你指定的 Angel-Gril 仓库，Seep 原版仍保留在源码和部署备份中。其他重名技能导致安装失败，需要审查，不能悄悄覆盖。

Seep接线包没有声明全部宿主import依赖，单纯link登记可能出现“已安装但schemastery找不到、插件未激活”。工作台在部署副本内创建指向受管runtime/node_modules的junction，安装/doctor实际import插件；不会复制另一设备的node_modules。实时Loader与面板仍需单独验收。

## 2. 目标电脑准备

1. Windows 10/11 x64，预留至少 5 GB（完整外部工具、浏览器、Android SDK 需要更多）。使用普通用户安装；驱动和部分系统工具可能需要管理员。
2. 安装 Git、Python 3.11+、Node 22.18+、npm、Java 17 JDK。`bootstrap.ps1 -InstallPrerequisites` 通过 winget 安装 Git、当前 Node LTS、Python 3.12、Temurin 17；检查安装退出码，重开终端解决旧 PATH。离线机器必须先准备这些安装包与源/依赖缓存，当前脚本不是离线分发包。
3. GitHub 在 Git Credential Manager 登录，保证能访问四个源。不要把 PAT 填进 URL、README、命令历史或 profile。私有源无权限时先给目标帐号权限，安装不会降级成“成功但少两个技能”。
4. 设置正确时间、时区；核对 `Get-Date`、`w32tm /query /status`。此前曾将时间改到两个月前导致访问/TLS失效；部署脚本不改系统时间。
5. 查看代理是否仍然有效。网络、npm、pip、Git 和模型网关分别测试，不用“浏览器能开网页”证明它们都可用。
6. 关闭正在运行的旧桌面客户端，保存会话。桌面可能是单实例：新启动器遇到旧进程时，环境变量可能被旧实例忽略。

可先逐个执行 `git ls-remote <仓库URL> HEAD` 验证权限；不输出 Git 凭据。安装使用 Git 自身的认证，不依赖 `gh` 必须在 PATH。

## 3. 完整安装命令

```powershell
git clone https://github.com/Angel-Gril/DSH-Purge-Windows.git 'C:\AI\DSH-Purge-Windows'
cd 'C:\AI\DSH-Purge-Windows'
powershell -NoProfile -ExecutionPolicy Bypass -File .\install.ps1 -Root 'C:\AI\WindowsWorkbench' -InstallDesktop -ApplyPurge -InstallCapabilities
powershell -NoProfile -ExecutionPolicy Bypass -File .\doctor.ps1 -Root 'C:\AI\WindowsWorkbench' -ProbeMcp -Deep
```

已有兼容桌面：省略 `-InstallDesktop`，自定义安装目录通过 `-DesktopExe` 指定。下载器只接受 Authenticode 验证通过的官方来源安装器；运行图形安装器，完成安装后读取 `resources/app.asar` 的 package.json 检查版本。Seep 原生插件最低要求 0.2.2-rc.1，本工作台进一步要求桌面与受管 CLI 同为锁定的 0.2.2-rc.3；0.2.1-rc.5 和其他未适配版本明确阻断。官方 latest 将来变化时也会停下来，不能绕过检查。桌面和 CLI 的版本分别记录，不能混为同一个宿主。

安装到不同盘、用户名包含空格或非 ASCII 字符时，始终为路径加引号；脚本进程间使用参数数组。

Web 通过受管 Node CLI 管理；desktop 必须通过选定客户端的 Electron 管理入口，支持 ASAR、展开树及新版 node-entry wrapper。普通 npm CLI 会拒绝管理 desktop profile，不能用手写 package.json 绕过。工作台复用锁定 Purge 的实例定位器，不扫描其他全局安装作为替代。

首次部署时，若独立 DSH_HOME 还没有 desktop profile，脚本会打开客户端。完成欢迎页，再彻底退出窗口，安装脚本会继续登记插件。仅运行官方安装器不代表工作台自己的 profile 已初始化。客户端后续启动统一传入 `<Root>\desktop-user-data`，将 Electron 单实例和界面状态也与旧环境分开。请勿在首次初始化未退出时另开第二个部署。

源码缓存会在各自仓库启用Git的core.longpaths，不改全局Git设置。仍遇到Windows长路径限制时，优先选择较短Root（例如C:\AI\WB）；Python/系统层长路径支持需在目标机确认。

`-ApplyPurge` 的作用包括两个不同宿主：Web 的受管 npm 树、指定桌面安装的 ASAR/展开树。桌面可能需要解包/换包及重新启动。Purge 自己保留逐文件/宿主备份，配置快照不能代替宿主补丁回滚。默认不自动应用、不自动追随上游最新版，避免宿主更新后版本混杂。

不带 `-ApplyPurge` 只安装并启用插件，不能宣称宿主补丁已全部生效。只需要先测试 Web 时用 `-WebOnly`，之后重跑完整安装补桌面；它是明确的部分部署。

## 4. 环境能力安装与人工组件

`capabilities.ps1` 调用锁定 Seep 版本自己的安装器，指定本工作台 ToolboxRoot，且不改永久系统 PATH。工作台独立检查被选中的工具，缺失会非零退出；不会把未选择的可选组混入本次安装结果。路径检查后还需跑 Deep 验证实际能力。

`install.ps1 -InstallCapabilities` 在核心安装成功后自动执行全部组。单独重试：`capabilities.ps1 -Root <同一Root> -Components all`；核心工作台和外部能力分别报告，不因某个可选下载失败删除已安装的 profile。

| 组 | 内容 | 仍需现场验收 |
| --- | --- | --- |
| aotopsy | 仓库自带 Flutter/Dart AOT 工具与 shims | 目标 ABI、样本版本 |
| web | ffmpeg、ffprobe | 浏览器访问环境、实际取证目标 |
| android | 独立工具箱 venv，frida/objection/APKiD 等 | 设备 adb、frida-server 版本/ABI、root/模拟器状态 |
| scanners | nuclei、ffuf | 模板更新与可访问测试环境 |

先运行 `capabilities.ps1 -Components all -CheckOnly` 可只检查。工具箱下载按锁定 Seep 安装脚本的策略执行，其外部二进制未全部做本仓库级版本锁定；安装后实际版本以目标机 doctor 为准。

Seep 仓库自带 radare2、jadx、apktool 等程序。APK/EXE 技能通过 `APKREV_TOOLS` / `EXEREV_TOOLS` 和 PATH 发现它们，也会保留调用者已有工具目录。不要只复制 SKILL.md，references/scripts/evidence 都是技能的一部分。JDK、Android SDK build-tools 的 apksigner/zipalign、Android platform-tools/adb、Frida 服务端各有独立用途，发现 Java 不代表已经能重打包签名。

以下组件按设备补齐，不从源电脑整目录复制：

- **Android SDK**：安装 Android Studio SDK Manager 或官方 command-line tools，选择 platform-tools 与所需 build-tools，设置目标机 `ANDROID_HOME`。把实际工具目录纳入 APKREV_TOOLS；跑 APK doctor 核对签名/对齐/smali 能力。
- **IDA Pro / idalib**：目标机安装自己的授权版本。设置 `SEEP_IDA_ROOT` 到该安装目录，按 Seep 的 IDA 接线文档在相应 Python 中安装 `ida_pro_mcp`，然后重跑 `install.ps1 -WithIda`。只安装 venv 不代表 IDA license/idalib 可用；用只读会话握手验收。不要复制他人许可证。
- **浏览器**：`-WithPlaywright` 注册固定 `@playwright/mcp@0.0.85`；首次运行需要 npm 下载及浏览器。JS MCP 固定 3.0.9，从本机受管 npm 目录直接启动。浏览器二进制/自动化连接仍需现场测试。
- **Npcap**：Windows 原始网卡工具（如 ksubdomain）依赖驱动。PATH 识别 16/16 不能证明驱动已装；安装官方 Npcap 后实测。
- **硬件调试/虚拟化/管理员能力**：EXE doctor 会报告所需特权和硬件条件，脚本不会把不可用硬件标为通过。

## 5. 模型、网关、提示词与 preset

启动 `start-web.ps1 -Root ...` 或 `start-desktop.ps1 -Root ...` 后，在设置配置目标机 provider、base URL、model 与凭据环境引用。不要复制旧机器的 API key，也不要默认声称某个 `20200610.shop` 等网关会一直可用。API 最小请求应使用目标机用户授权的现有配置，只记录 HTTP 状态/耗时/模型名，不记录 key。

新工作台默认独立 DSH_HOME，旧环境不自动迁入；若确需接入既有环境，显式 `-DshHome 'C:\Users\<user>\.dsh'`。先备份并关闭宿主。脚本保留用户 YAML 外部文本、provider/model 和 !!js，只管理 `BEGIN DSH-WINDOWS-WORKBENCH` 标记块；不覆盖其他插件配置。发现旧 Seep 生成块会阻断，先迁移移除旧 MCP 条目以防双挂载。旧 dsh-purge 包会迁移为新版 dsh-purge-community；新版 bundle 禁用旧独立 redteam 条目。

`unknown prompt variable "{{cwd}}" in deployment:persona-suffix` 是宿主在该阶段仅注册 provider/model，而配置引用了 cwd。新 Purge bundle 已将 personaSuffix 留空，不再把 cwd 模板写入该字段。手写旧配置仍可能覆盖默认值：在备份后仅修复那个具体字段，不删除全体模型设置。动态 cwd 应由支持它的运行阶段提供。

本机旧版“Seep 逆向工作台”提示词来自用户级 AGENTS.md、MCP/skills 连接和额外启动器，不是安装 Purge 自动附赠。新方案采用 Seep 原生 lab 闸门：新会话关闭，`lab：` 开启，`退出实验` 关闭；不要为了“看起来一样”把旧 system-reminder 或全局强制指令复制过去。

Purge 的侧栏、redteam、preset、prompt injection 必须在当前 Loader 运行。确认设置 → 插件列表里 Purge 与 Seep 在当前 profile 启用且无错误，不能只看到文件就判断成功。`default: standard`、`selectedDefault: cordis` 等 preset 差异应看当前会话实际选中项，不强制替换用户偏好。

## 6. 更新、回滚、故障恢复

```powershell
cd 'C:\AI\DSH-Purge-Windows'
powershell -NoProfile -ExecutionPolicy Bypass -File .\update.ps1 -Root 'C:\AI\WindowsWorkbench' -ApplyPurge
```

更新只 `git pull --ff-only` 本工作台仓库，源版本以最新清单为准，不每次跟随四个上游 main。工作台有未提交修改时停止。源目录已有受跟踪修改时不 reset，不丢弃用户数据。新部署保留旧目录供快照引用。

配置阶段失败自动恢复 package/lock/YAML，并重新安装旧依赖；新建失败 profile 会改名保留。Purge 应用阶段失败则保留已配置工作台和宿主自己的备份，给出失败状态，分别运行 purge revert。进程中断遗留 `deployment.lock` 时，检查文件 PID 的进程已退出再手工移除锁；不要在另一个部署还运行时解锁。

```powershell
# 查真实宿主定位，Web/desktop 分开
.\purge.ps1 -Root 'C:\AI\WindowsWorkbench' -Surface web -Action host-status
.\purge.ps1 -Root 'C:\AI\WindowsWorkbench' -Surface desktop -Action selfcheck
# 撤回宿主补丁
.\purge.ps1 -Root 'C:\AI\WindowsWorkbench' -Surface desktop -Action revert
# 恢复最近一次配置快照；可传 -Snapshot 指定旧快照
.\rollback.ps1 -Root 'C:\AI\WindowsWorkbench' -RevertPurge
```

宿主自动升级后需要重新检查版本与补丁，不能用升级前状态作证。`na` / `skipped` 是分类，`missing_file` 需要查看宿主是否确实应该有该模块；不制造假文件凑86/86。Claude Code/Codex hooks 针对的宿主模块没安装时不适用，并不等于 Seep MCP、DSH 插件生命周期或通用 hook 全部缺失。

CLI自检的 `unknown` 也需要分层看：若宿主、注入、磁盘布局均通过，待应用/文件缺失均为0，而“当前profile的权限选择”未知，代表离线命令还没有当前会话的实际权限证据。安装保留补丁已写入的结果并明确提示现场验收；doctor将其标为 `UNVERIFIED` 并非零退出。不要为让报告变绿而擅自改用户权限。请在运行中的Purge面板重测，必要时核对当前会话preset与权限。真正的宿主故障、缺失或待应用仍会阻断。

Web自动验收使用 `--no-open`，直接访问本机端口，并从私有启动日志获取官方bootstrap URL建立认证cookie；不禁用认证，也不将token写入验收报告。手工排障别把原始启动日志直接贴到公开仓库，日志里的本机访问token也需脱敏。

## 7. 给另一台电脑传什么

首选只发本 GitHub 仓库地址和 `docs/AI-HANDOFF.md`，由目标机拉取源码/依赖。若有未发布的本地定制，先审查并提交到对应来源仓库，再更新 sources.lock.json；别靠复制未知目录让两台机器产生分叉。

ZIP导出包可以解压后运行install.ps1，但不含.git。要在线更新工作台代码，使用正式git clone的目录；update/package会核对Git根目录和origin，防止解压到另一个项目下面时误操作父仓库。`update.ps1 -SkipGitPull` 只重部署当前文件中的锁定版本，不拉取新工作台代码。

可另传：你自己有权分享的 prompt 模板（先删用户名、绝对路径和凭据）、工具清单、脱敏 preset 配置、目标设备可用的离线依赖包及校验和。

不传：`.env`、Git 凭据、API key、完整 `.dsh`/会话历史、snapshots、samples/workspace、IDA 授权、整份 node_modules/Python venv、未审查日志、体积数百 MB 的旧部署 tar。已有工具要在新机重新解析路径和验证依赖，不能把 `C:\Users\Admin` / `E:\DSH-Purge` 硬编码复制过去。
