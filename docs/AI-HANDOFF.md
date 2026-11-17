# 发给目标设备 AI 的任务

复制下面整段给另一台 Windows 上能够运行命令的 AI；把安装目录按实际需要替换。不要把本机密钥填进这段话。

```text
请实际部署 https://github.com/Angel-Gril/DSH-Purge-Windows.git，不要只给我步骤。
先读仓库 README.md、AGENTS.md、sources.lock.json、docs/DEPLOYMENT.md 和 docs/ACCEPTANCE.md。
安装目录使用 C:\AI\WindowsWorkbench，工作台仓库放 C:\AI\DSH-Purge-Windows。
我授权你拉取全部四个源、安装本地依赖、注册 Web/desktop 两个 profile，并应用两端 Purge 宿主补丁。
关闭宿主前保存会话；不要改系统时间；别修改其他无关软件和项目。

必须包含 Seep-Reverse-Lab、apk-reverse-new、exe-reverse、dsh-purge-harness；
APK/EXE 使用指定源的完整技能目录，Seep 负责 MCP 和 lab 闸门，Purge 必须在当前 Loader 中实际运行。
四个源的固定提交以清单为准。GitHub 私有源没权限要明确报错，不能漏装后说成功。
检查并补齐基础 Git/Python/Node/npm/Java 环境。桌面要实际安装并检查版本，不能只装 CLI/Web。
已有桌面若为0.2.1-rc.5，应先升级到清单对应的0.2.2-rc.3；不要绕过版本检查强装新Seep。
运行 install.ps1 -Root C:\AI\WindowsWorkbench -InstallDesktop -ApplyPurge -InstallCapabilities；
已有兼容桌面可省InstallDesktop并指定DesktopExe。运行capabilities.ps1 -Components all补外部能力。
使用独立DSH_HOME，保留现有模型配置。provider/model/API key由目标机设置提供，不读出或上传密钥。
不要复制源电脑整个 .dsh、node_modules、venv、IDA许可证、样本或强制常驻system-reminder。
Seep新会话默认非lab，lab：开启、退出实验关闭，不把“没有旧强制提示词”误判为没部署。

运行doctor.ps1 -ProbeMcp -Deep，逐项记录实际结果。
分别用start-web.ps1和start-desktop.ps1启动，检查两个profile的实时插件状态、Purge侧栏、Seep面板、技能。
核实Seep/JS MCP握手及只读状态调用，检查lab开关；以本机授权配置做一次最小模型请求。
如果需IDA，先安装本机授权版本及ida_pro_mcp，再设置SEEP_IDA_ROOT并-WithIda，验证只读会话。
Android SDK/设备/Frida服务端、Npcap驱动、浏览器、硬件/管理员能力各自验收，不能只以PATH存在判成功。
补丁na/skipped与pending/missing_file分开报告，不为追求86/86制造不存在的文件。

发现错误请在独立环境修复并复测，提供命令、实际版本、提交、运行证据和剩余依赖。
只有Web测试完成时写“Web已验证，桌面未验证”；没有模型请求/GUI证据时不要写“全部可用”。
最终留下本机脱敏验收记录、更新命令、回滚命令和未验证项。
```

目标机的 AI 仍可能需要你在官方图形安装器完成点击、登录 GitHub，或提供本机 API 配置。这些是目标机自己的凭据/设备条件，不应从源机器打包过去。
