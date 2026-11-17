# DSH Purge Windows 工作台

主入口是 **DSH Web + 官方桌面端 + Purge**，集成 Seep + APK/EXE 完整技能；**PI 可选**，用于日常编程或独立启动 Seep/APK/EXE 工作台。支持按组件安装。四个项目按 Git commit 拉取，工作台生成接线配置；不需要传整份本机目录。

| 组件 | 固定来源 | 本版基线 |
| --- | --- | --- |
| DSH CLI / Web | npm `@deepseek-ai/dsh` | `0.2.2-rc.3`，独立运行时 |
| DSH Desktop | DeepSeek 官方 Windows 安装器或本机指定路径 | 要求与受管 CLI 一致：`0.2.2-rc.3`；现场读取 ASAR 版本 |
| Seep | [angusdevgo/Seep-Reverse-Lab](https://github.com/angusdevgo/Seep-Reverse-Lab) | `1.15.0`，`1ea9399ccb4d` |
| APK 技能 | [Angel-Gril/apk-reverse-new](https://github.com/Angel-Gril/apk-reverse-new) | `56fee1319b0a` |
| EXE 技能 | [Angel-Gril/exe-reverse](https://github.com/Angel-Gril/exe-reverse) | `426e994ce5b5` |
| Purge | [Angel-Gril/dsh-purge-harness](https://github.com/Angel-Gril/dsh-purge-harness) | `dsh-purge-community 1.7.18`，`639c8934b429` |
| PI（选装） | npm `@earendil-works/pi-coding-agent` | `1.4.0`，独立运行时/配置/会话；与本机 Seep PI 基线一致 |

完整 SHA 在 [sources.lock.json](sources.lock.json)。桌面官方 latest 链接会变化，安装器记录下载 SHA256、验证 Authenticode 签名并检查已安装版本；它不是锁定的二进制镜像。新的宿主版本需要另行兼容验证。

## 快速部署

要求 Windows 10/11 x64、PowerShell 5.1+、Git、Python 3.11+、Node.js 22.18+（推荐 Node 22/24 LTS）、npm。Java 17 JDK 用于 Android 工具。Git 必须能访问全部四个源，**APK/EXE 私有仓库需要目标设备的 GitHub 访问权限**。

在 PowerShell 运行：

```powershell
git clone https://github.com/Angel-Gril/DSH-Purge-Windows.git "$env:USERPROFILE\DSH-Purge-Windows"
cd "$env:USERPROFILE\DSH-Purge-Windows"
powershell -NoProfile -ExecutionPolicy Bypass -File .\install.ps1 -InstallDesktop -ApplyPurge -WithPi -InstallCapabilities
```

`-WithPi` 附加独立 PI 入口（需要 Node 22.19+），省略时仍是默认完整 DSH 部署。`-InstallDesktop` 下载并打开官方图形安装器，按界面完成后继续。已有兼容桌面宿主时省略它，或传 `-DesktopExe 'D:\Apps\DeepSeek Harness\DeepSeek Harness.exe'`。应用桌面补丁前保存会话并退出客户端；补丁会改动该客户端的宿主文件，使用 `purge.ps1 -Surface desktop -Action revert` 回滚。

独立 desktop profile 首次使用还会打开客户端初始化：完成欢迎页后彻底退出，脚本继续安装两插件。桌面用户数据也独立存放，后续用 `start-desktop.ps1` 进入同一工作台。

缺基础环境时，可先下载本仓库 `bootstrap.ps1`，运行：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\bootstrap.ps1 -InstallPrerequisites -InstallDesktop -ApplyPurge -WithPi -InstallCapabilities
```

也可用一条 PowerShell 命令下载引导器并部署（官方桌面安装器仍可能需要界面操作）：

```powershell
$p = Join-Path $env:TEMP 'DSH-Workbench-bootstrap.ps1'; Invoke-WebRequest 'https://raw.githubusercontent.com/Angel-Gril/DSH-Purge-Windows/main/bootstrap.ps1' -OutFile $p; powershell -NoProfile -ExecutionPolicy Bypass -File $p -InstallPrerequisites -InstallDesktop -ApplyPurge -WithPi -InstallCapabilities
```

raw引导器适用于能直接下载脚本的仓库。若部署仓库为私有，使用上面的Git clone方式；Git Credential Manager的登录不会自动提供给Invoke-WebRequest。

默认安装到 `%LOCALAPPDATA%\DSH-Windows-Workbench`，使用该目录内独立 `dsh-home`。**直接打开旧快捷方式可能仍然进入旧环境**；使用本仓库启动脚本。已有模型/provider 不会自动从别机复制；首次启动后在设置中配置自己的网关、模型及凭据。

`-InstallCapabilities` 接着安装全部四组外部能力；可省略以先完成核心部署，再运行 `capabilities.ps1`。外部工具阶段失败会明确报错，已完成的核心安装保留，修复网络/依赖后可单独重试。

可运行 `shortcuts.ps1` 创建明确命名的 `DSH Workbench web/desktop` 桌面快捷方式。`package.ps1 -OutputZip D:\DSH-Workbench.zip` 可导出已提交的部署脚本包；源代码和依赖仍需在目标机拉取。

```powershell
# 补充外部工具：Flutter、Web 取证、Android 动态工具、可选扫描器
powershell -NoProfile -ExecutionPolicy Bypass -File .\capabilities.ps1 -Components all
# 检查文件、profile、宿主补丁、技能、MCP；Deep 会列出工具/设备/驱动缺口
powershell -NoProfile -ExecutionPolicy Bypass -File .\doctor.ps1 -ProbeMcp -Deep
# 启动二选一（不要用旧 dsh 命令测试新工作台）
powershell -NoProfile -ExecutionPolicy Bypass -File .\start-web.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File .\start-desktop.ps1
```

Seep 新版实验纪律按会话切换：发 `lab：` 开启，`退出实验` 关闭，新会话默认关闭。不会再复制旧机器 `~/.dsh/AGENTS.md` 中的强制常驻提示词。

## 独立使用与组件选择

```powershell
# 默认 DSH 完整安装加 PI 后，可分别启动独立工作台
.\start-seep.ps1
.\start-apk.ps1
.\start-exe.ps1
# 普通编程，不加载工作台技能/MCP
.\start-pi.ps1 -Project 'D:\Code\MyApp'
# 只部署 PI + 三套独立工作台，不安装 DSH/Purge/Desktop
.\install.ps1 -Root 'C:\AI\PiWorkbench' -Modules pi,seep,apk,exe
# 只部署 PI + APK，工具按目标机需要补充
.\install.ps1 -Root 'C:\AI\ApkWorkbench' -Modules pi,apk
```

完整选项表、模型接线、工作流和开发方式见 [具体使用指南](docs/USAGE.md)。更新保留安装时选择的组件。`-Modules` 表示完整选择；`capabilities.ps1 -Components` 是外部工具组，二者用途不同。

## 更新和恢复

```powershell
# 只快进本仓库，再部署仓库中锁定的版本；保留旧源码和配置快照
powershell -NoProfile -ExecutionPolicy Bypass -File .\update.ps1 -ApplyPurge
# 分别查看两个宿主，不能用 Web 的结果代替桌面
powershell -NoProfile -ExecutionPolicy Bypass -File .\purge.ps1 -Surface web -Action selfcheck
powershell -NoProfile -ExecutionPolicy Bypass -File .\purge.ps1 -Surface desktop -Action selfcheck
# 配置回滚；同时撤回宿主补丁要显式带 RevertPurge
powershell -NoProfile -ExecutionPolicy Bypass -File .\rollback.ps1 -RevertPurge
```

自定义 `-Root` 后所有命令都传同一 Root。`-WebOnly` 只做 Web，报告会明确标记桌面未安装，不能作为完整工作台验收。默认安装启用插件；只有 `-ApplyPurge` 才主动套用宿主补丁。Purge 自动应用/自动更新关闭，由统一更新命令负责。

请继续阅读 [具体使用指南](docs/USAGE.md)、[完整部署、迁移与故障处理](docs/DEPLOYMENT.md)、[交给其他 AI 的任务说明](docs/AI-HANDOFF.md)、[验收清单](docs/ACCEPTANCE.md)、[来源与许可证](THIRD-PARTY.md)。测试的实际覆盖范围记录在 [验证记录](docs/VALIDATION.md)。
