# 本次发布验证

环境：Windows 11 x64，Node.js 24.21.0，Python 3.13，Windows PowerShell 5.1。测试使用独立 `C:\AI\RD-1\_workbench-test`，未改动现用 `.dsh` 或桌面宿主。

已验证：

- 四个 Git 来源均通过本机 Git 凭据实际拉取，完整 SHA 与锁定清单一致。
- Windows PowerShell 5.1 解析全部本仓库 `.ps1` 脚本通过。
- 受管DSH CLI实际返回版本 `0.2.2-rc.3`；锁文件包含必需的DSH peer闭包，修复了npm成功但缺cordis-plugin-group的问题。
- 使用本工作台独立 Python 环境，实际完成 Seep MCP initialize、tools/list（38个工具）和只读 seep_status 调用。
- JS MCP实际完成initialize、tools/list，返回23个工具；未操作真实浏览器内容。
- 18 项Python回归测试通过，覆盖YAML用户内容/!!js保留、幂等、空序列、损坏标记、失败恢复、并发锁、技能重名、桌面版本/管理入口/初始化约束、实例越界、补丁状态分类、ASAR读取、源清单及必需peer依赖。
- 3项独立Git夹具验证通过：拒绝误用父仓库、拒绝无关origin、接受目标仓库。测试临时目录已清理。
- Seep插件通过新建宿主依赖junction后实际Node import成功；此前link登记但缺schemastery的问题已修复，并加入安装/doctor导入检查。
- 独立Web运行时实际执行Purge apply；22组必要宿主检查通过，待应用0、目标文件缺失0。离线profile权限仍需运行面板确认，不能等同于模型请求成功。本版Purge包含88条定义，不能沿用旧版86条作为固定分母。
- 只读检查本机已安装桌面版 `0.2.1-rc.5` 及已展开的 `resources/app/dsh/node_modules/@deepseek-ai` 路径；这个版本会被新Seep基线的安装器拒绝，不作为新桌面运行验证。
- 通过该旧客户端的真实Electron管理入口，确认未初始化的独立desktop profile会被官方拒绝；因此正式安装增加了首次GUI初始化步骤。没有手写profile冒充完成，也没有启动或修补旧桌面环境来做正向验收。
- 官方Windows安装器经Range只读读取PE版本为 `0.2.2-rc.3`；这只证明当时的版本元数据，不代表完整安装器签名、安装或GUI功能已实测。

已从正式安装入口在同一独立Root完成幂等重部署及Purge应用，退出码0。随后实际启动Web进程，完成宿主认证，并验证首页、`/seep-workbench/api?skills=1`、`/dsh-purge/status` 均返回HTTP 200；两个插件接口均 `ok=true`。测试通过后只关闭本测试进程树。

启动期间端口会先绑定、前端路由随后挂载，短暂404不等于资源缺失。自动验收已等待启动就绪，并使用正常bootstrap cookie；前端dist文件存在，没有关闭认证或伪造HTTP结果。

最终 `doctor --probe-mcp` 中，四个来源、Python依赖、两插件实际导入、Web profile、APK/EXE完整技能及两个MCP握手均通过。Purge离线权限为唯一 `UNVERIFIED` 检查，故doctor按保守规则退出1；这不是MCP或宿主补丁失败。测试安装显式选择WebOnly，报告另有desktop未安装标记，不代表完整双宿主验收。

本次不具备的证据：新版本官方桌面GUI全链路、目标设备的模型网关请求、IDA授权/idalib、Android真机/Frida服务端、Npcap驱动以及全部外部扫描器/浏览器能力。这些需按ACCEPTANCE.md在目标设备逐项验收。

CI只运行语法和回归检查，不访问私有来源，也不代表两宿主功能自动验收。部署时生成的本机reports不进入Git。

## 2026.11.17.2：DSH 主入口与可选 PI

本轮保持 DSH + Purge 为默认主入口，新增按模块安装和 PI 独立入口。只读参考 `C:\AI\RD\setup\launch-pi.py` 与本机包元数据，确认本机使用项目内 `@earendil-works/pi-coding-agent@1.4.0`，不是依赖全局 pi 命令。没有读取本机 .env/auth.json/会话，也没有复制旧请求改写扩展或全局强制提示词。

本轮新增证据：

- 全部 PowerShell 5.1 语法、27 项 Python 回归、1 项 Node 扩展状态测试、3 项 Git 边界检查通过。包含组件依赖、PI 配置保留、会话开关、工具目录保留、DSH 目标隔离、PI 配置快照恢复及 MCP 失败诊断脱敏。
- 正式 installer 在独立 `C:\AI\RD-1\_workbench-pi-test` 完成 `pi,apk,exe` 部署：没有 DSH runtime、profile、插件或桌面，不创建 dsh-home。PI 实际返回 1.4.0。
- PI 实际 SDK ResourceLoader 接受 coding/APK/EXE/all：分别加载 0/1/1/2 个技能，扩展 1 个，技能诊断 0。APK/EXE 均来自指定完整技能目录；未用模拟资源加载器代替。
- 实际 PI CLI RPC 会话返回 lab/exit-lab 命令，并在本地处理 `/lab` 与 `/exit-lab`，没有模型请求。`start-apk.ps1 -PiArgs --version` 真实入口返回 1.4.0。
- 自定义 models 模板通过 PI `--list-models` 接受，使用合成占位环境值，只检验模型元数据；没有访问模型服务，临时模板已删除。
- 原独立 DSH 测试 Root 通过正式 installer 附加 PI；实际 Web 首页、Seep 技能 API、Purge 状态 API 均 HTTP200。DSH/PI 配置共存。
- DSH + PI doctor 中所有已选来源、两插件 import、profile、技能、PI 各模式资源、PI 原生 MCP list 和 Seep/JS MCP 探针通过。Purge 离线会话权限仍为唯一 UNVERIFIED，因此 doctor 保持退出1；未修改权限以改变报告。
- 正式 installer 将原隔离 DSH Root 裁剪为 dsh,purge 后，实际 profile 中 seep-lab bundle 与受管 Seep overlay 均移除；正式 rollback 恢复了完整 DSH + PI 状态、Seep bundle 与 overlay。
- PowerShell 模块参数同时接受列表和 CSV；实际非法列表请求在部署前失败，未创建安装 Root。Windows PowerShell 5.1 解析再次通过。
- 在原 PI-only Root 通过正式 installer 增加 Seep，实际创建独立 Python MCP venv 和 JS MCP npm runtime，仍无 DSH runtime/profile/插件。各模式资源、Seep/JS 协议探针，以及 PI 原生 MCP list 均有成功证据；原生连接实际返回38/23工具。完整 doctor 复检退出0，未用模拟服务器替代。

独立 Seep 初始两次 doctor 的 PI 原生 MCP list 非零，但两个单独协议探针均通过；多次独立命令及随后完整诊断均通过。捕获完整失败输出的诊断运行未再复现，根因未确认，不能声称已经修复某种超时或缺包。原失败报告保留于测试 Root，未改成通过。当前 doctor 改为解析 PI 的原生 JSON 结果，核对受管服务及非空工具列表；失败时只公开服务状态和超时/入口缺失/连接分类，不暴露私人 transport 参数和原始错误。目标机若再出现非零，应按 USAGE 中的命令继续定位，不靠反复重试作验收。

本轮新测试源码使用上一轮已经联网拉取并校验 SHA 的本地 Git 缓存。一次 GitHub443连接失败已明确非零退出；没有漏装后报告成功。新的 PI/npm 依赖由锁文件实际安装。新设备仍需独立验证 GitHub 权限与网络。

未验证项继续包括兼容版本的桌面 GUI/ASAR 正向全链路、真实模型请求、人工操作 PI TUI，以及 IDA/Android设备/驱动/浏览器等外部能力。上述 SDK/RPC/MCP 证据不能替代这些现场验收。
