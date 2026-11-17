# 必须逐层验收

把每项写为 `通过 / 失败 / 未验证 / 不适用（原因）`，不要把未验证写通过。

| 层 | 通过证据 |
| --- | --- |
| 来源 | 四个完整 SHA 匹配 sources.lock.json；APK/EXE 权限与完整脚本目录存在 |
| 基础环境 | 实际 Python / Node / npm / Git / Java 版本，不是 PATH 名称 |
| Web 安装 | web/package.json 同时登记 seep-lab、dsh-purge-community bundles，YAML合法，dump-config成功 |
| Desktop 安装 | 真正的官方 exe + ASAR/展开树元数据版本合格；desktop profile 登记两插件 |
| Web 运行 | start-web 使用 active.json 的 DSH_HOME，Web实时插件列表显示两者运行，无启动异常 |
| Desktop 运行 | 先退出旧实例，再start-desktop；桌面当前Loader里两插件运行，不用Web结果代替 |
| Purge 功能 | 两端分别看状态/selfcheck，侧栏可用；没有prompt变量错误，注入状态与实际预期一致 |
| Seep 功能 | 两端面板能返回状态；普通会话不注入lab纪律，lab：开启、退出实验关闭，新会话关闭 |
| 技能来源 | apk-reverse、exe-reverse 指向指定来源合成层，其他Seep技能无重名遮蔽 |
| MCP | MCP initialize、tools/list、Seep只读seep_status调用成功；JS MCP有非空工具列表 |
| 工具能力 | doctor -Deep结果与APK/EXE各自doctor逐项核对，缺JDK/签名工具/驱动/硬件明确列出 |
| 真实模型 | 使用本机配置发一次最小消息，得到正常响应；只记模型、耗时、状态，不记录key |
| 更新/恢复 | 更新只快进；重复安装不重复配置块；快照可恢复；宿主补丁单独可revert |

命令示例（每条都传你自己的 Root）：

```powershell
.\doctor.ps1 -Root C:\AI\WindowsWorkbench -ProbeMcp -Deep
.\purge.ps1 -Root C:\AI\WindowsWorkbench -Surface web -Action selfcheck
.\purge.ps1 -Root C:\AI\WindowsWorkbench -Surface desktop -Action selfcheck
.\start-web.ps1 -Root C:\AI\WindowsWorkbench
.\start-desktop.ps1 -Root C:\AI\WindowsWorkbench
```

Web运行时可在同源/已登录浏览器里检查 `/seep-workbench/api?skills=1`、`/dsh-purge/status`、`/dsh-purge/selfcheck`。服务若有认证，沿用当前宿主认证，不关闭认证来跑检查。不要将整个插件响应/配置转发到公开issue，先脱敏。

`doctor` 的机器报告位于 Root/reports，安装配置检查通过不代表两端GUI和模型请求已验收；报告中的 `runtimeVerified=false` 是保守标记。深度检查可能返回失败，因为某些可选能力确实未满足；根据用户实际需要补齐或记录不适用。
