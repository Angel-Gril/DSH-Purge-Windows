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
