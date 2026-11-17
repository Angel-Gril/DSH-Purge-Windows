# DSH 主工作台与 PI 独立入口

默认主入口是 **DSH + Purge**。Seep、APK、EXE 接入 DSH 后，作为同一助手的工具与技能使用；需要独立工作台或日常编程时，选装 **PI**。APK/EXE 仓库提供完整技能和脚本，本身没有需要启动的独立 GUI/MCP 服务，PI 是它们的交互入口。

## 安装选择

以下命令在仓库根目录的 PowerShell 中执行。`-Modules` 支持 PowerShell 列表或带引号的逗号分隔字符串；没有该参数时安装完整 DSH 工作台，不安装 PI。

| 目标 | install.ps1 参数 | 实际安装 |
| --- | --- | --- |
| 推荐完整工作台，含独立入口 | `-InstallDesktop -ApplyPurge -WithPi` | DSH Web/Desktop、Purge、Seep、APK、EXE、PI |
| 默认完整 DSH | `-InstallDesktop -ApplyPurge` | 上述组件，不含 PI |
| DSH + Purge 基础环境 | `-Modules dsh -InstallDesktop -ApplyPurge` | DSH + Purge，不拉 Seep/APK/EXE |
| 纯 PI 编程 | `-Modules pi` | 只有受管 PI，不拉四个源，不安装 DSH/venv/Desktop |
| 独立 Seep | `-Modules pi,seep` | PI、Seep、Python MCP、JS MCP |
| 独立 APK | `-Modules pi,apk` | PI、完整 APK 技能与脚本；工具需自备 |
| 独立 EXE | `-Modules pi,exe` | PI、完整 EXE 技能与脚本；工具需自备 |
| 三套独立工作台 | `-Modules pi,seep,apk,exe` | PI、Seep MCP/工具、完整 APK/EXE 技能，不安装 DSH/Purge |
| DSH 接入指定技能 | `-Modules dsh,apk -InstallDesktop -ApplyPurge` | 自动补 Purge 和 Seep 原生技能连接器，不拉 EXE 源 |

PI 最低 Node **22.19.0**，锁定 `@earendil-works/pi-coding-agent@1.4.0`，与本机 `C:\AI\RD` 使用的包及版本一致。DSH 仍为 0.2.2-rc.3。PI 自带原生 MCP，不重复安装旧 `pi-mcp-extension`；那类扩展可能替换内置 MCP，造成“配置存在但会话不接入”。

建议完整安装命令：

```powershell
.\install.ps1 -Root 'C:\AI\WindowsWorkbench' -InstallDesktop -ApplyPurge -WithPi -InstallCapabilities
.\doctor.ps1 -Root 'C:\AI\WindowsWorkbench' -ProbeMcp -Deep
```

默认需要兼容桌面宿主，`-WebOnly` 明确只部署 Web。独立 PI 安装不检查桌面，不需要加 WebOnly。`-ApplyPurge` 只能用于含 DSH 的安装。`-WithIda`、`-WithPlaywright` 和外部能力组安装需要 Seep。

所有命令使用同一个 Root。再次运行 install 的 Modules 表示新的完整选择，不是增量追加；给现有默认 DSH 安装加 PI 使用 `install.ps1 -WithPi` 并保留原有 Root/Desktop/WebOnly 等选项。已有自选组件应显式列全。update 会保留已选组件，旧版本没有 modules 字段时按原有默认完整 DSH 处理。不同用途可用不同 Root，避免误切换。

变更选择前关闭该 Root 的运行入口。未选组件的旧缓存/profile保留供恢复，启动器只允许当前所选入口；变更选择不会终止旧进程或撤回已经写入的宿主补丁。要移除 DSH/Purge，应先在原部署运行两端 purge revert，再切换，或直接给独立 PI 使用新的 Root。

`shortcuts.ps1 -Root <目录>` 可创建当前所选 DSH/PI 工作台的桌面快捷方式；已有同名快捷方式保留。

## DSH 内使用

1. 用 `start-desktop.ps1 -Root 'C:\AI\WindowsWorkbench'` 或 `start-web.ps1` 进入受管 profile。旧桌面快捷方式和全局 `dsh` 可能进入另一环境。
2. 在设置配置本机模型和网关。在“插件列表”核对 Purge 与 Seep 的实时状态；Purge 侧栏和 Seep 面板应能打开。分别检查 Web 和桌面，不能相互代替。
3. 新会话发 `lab：` 开启 Seep 实验上下文，发 `退出实验` 关闭。普通开发会话按日常助手使用。
4. 示例：“读取 softseep，给 samples 中的测试 APK 判型，先检查工具和授权范围，再只做静态画像。”APK 使用完整 `apk-reverse`，Windows 程序使用 `exe-reverse`。要求先读技能，再运行其中实际支持的脚本。
5. Seep 工具先发现 schema，再限范围调用；IDA 可选并需本机后端与许可证。工具存在、MCP 握手、实际样本分析分别验收。

Purge 分两层：profile 插件运行提供面板、preset 等；宿主补丁提供运行时变化。二者都要检查。`purge.ps1 -Surface desktop -Action selfcheck` 检查桌面；Web 用 `-Surface web`。`unknown` 中的当前会话权限未知不能靠离线命令强行改为通过，详见部署文档。

## PI 独立工作台

```powershell
# 日常编程，指定自己的源码目录；不加载工作台技能/MCP
.\start-pi.ps1 -Root 'C:\AI\WindowsWorkbench' -Project 'D:\Code\MyApp'
# Seep、APK、EXE 独立交互入口
.\start-seep.ps1 -Root 'C:\AI\WindowsWorkbench'
.\start-apk.ps1  -Root 'C:\AI\WindowsWorkbench'
.\start-exe.ps1  -Root 'C:\AI\WindowsWorkbench'
# 同一 PI 会话使用全部已选能力
.\start-pi.ps1 -Root 'C:\AI\WindowsWorkbench' -Mode all
```

不传 Project 时使用 `<Root>\projects\coding|seep|apk|exe|all`；不会在锁定上游源码中写开发文件。传 Project 时目录必须已存在。PI 配置共同存放在 `<Root>\pi\agent`，会话按入口放到 `pi\sessions\<模式>`，与 DSH 分开。项目自己的 `.pi` 配置仍遵守 PI 的项目信任规则。

Seep/APK/EXE 入口发 `lab：` 或 `/lab` 开启本会话工作台上下文，`退出实验` 或 `/exit-lab` 关闭。新会话默认关闭。PI 使用本仓库的小型适配扩展；不会照搬本机旧全局提示词、请求改写扩展或权限覆盖。APK/EXE 入口只显式加载对应技能，Seep/all 加载合成技能集。若选择了 Seep，这些分析入口可用 Seep、JS MCP；没有 Seep 时仍可运行技能自带脚本，但所需二进制须另装。

PI 内 `/skill:apk-reverse`、`/skill:exe-reverse` 可明确选技能。`/mcp` 查看实时连接及工具，`/reload` 在改配置后刷新。单独诊断不用模型：

```powershell
.\start-pi.ps1 -Root 'C:\AI\WindowsWorkbench' -PiArgs @('--version')
.\start-seep.ps1 -Root 'C:\AI\WindowsWorkbench' -PiArgs @('mcp','list')
```

第二条会连接独立 PI 配置中启用的 MCP；并不因 coding 默认关闭 MCP 而跳过诊断。检查成功不等于模型请求成功。普通 PI 编程入口不加载 MCP；分析入口会加载用户另行配置的 MCP，因此请检查自己的 mcp.json。

若 doctor 的 PI MCP 检查非零，先用这条 `mcp list` 分别核对 Seep/JS 的状态和错误，再与协议探针结果比较。复测正常时也保留首次失败记录；不要把“文件存在”或某次重试成功直接当作故障根因已修复。诊断输出可能含私人服务地址，分享前脱敏。

## PI 模型与凭据

本机 Seep 启动器的可移植做法是：项目内 PI、独立 agent 目录、环境引用密钥、完整技能路径和 MCP 接线。本工作台沿用这些结构，不复制旧模型的超大压缩参数、不绑定源电脑网关。

内置 provider 可以在 PI 界面登录或用官方 provider 的环境变量。自定义 OpenAI 兼容网关：

```powershell
$wbRoot = 'C:\AI\WindowsWorkbench'
Copy-Item .\config\pi-models.example.json (Join-Path $wbRoot 'pi\agent\models.json')
notepad (Join-Path $wbRoot 'pi\agent\models.json')
# 在文件内填 baseUrl、模型ID和实际上下文/输出限制；apiKey保留环境变量引用。
# 通过本机私有启动器/凭据机制提供 WORKBENCH_API_KEY，不要把值写进仓库或命令历史。
.\start-seep.ps1 -Root $wbRoot -PiArgs @('--list-models','workbench-gateway')
.\start-seep.ps1 -Root $wbRoot -PiArgs @('--provider','workbench-gateway','--model','YOUR-MODEL-ID')
```

Copy-Item 仅用于首次创建；已有 models.json 时手工合并。安装器不读取或复制 models.json/auth.json，不会从 DSH 自动拿密钥。PI 默认权限按 PI 自身设置；启动器不添加 `--approve`。

## 开发、更新与恢复

在自己的源码目录配合 `start-pi.ps1 -Project ...` 开发；修改本部署编排仓库可用独立 Root 测试。不要在 `sources/<sha>` 或 generation 副本中长期开发：前者修改会被下一次校验拒绝，后者是生成物。需要改上游时另建源码 checkout，提交、审查后按 MAINTENANCE 更新锁定 SHA。

```powershell
.\update.ps1 -Root 'C:\AI\WindowsWorkbench' -ApplyPurge
# PI-only 更新省略 ApplyPurge
.\update.ps1 -Root 'C:\AI\PiWorkbench'
.\rollback.ps1 -Root 'C:\AI\PiWorkbench'
```

更新保留 PI 模型、凭据、用户 settings 与非受管 MCP；受管服务器若被手改会阻断，避免静默覆盖。保留自定义条目时先换为用户自己的名称。配置快照包含 PI settings/mcp/受管登记与 DSH profile；不覆盖模型、凭据和会话。回滚不卸载依赖或删除分析产物。
