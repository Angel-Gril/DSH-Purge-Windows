# 工作台维护约定

本仓库统一编排 Windows 部署，不是四个上游项目的源码镜像。

1. 先读 README.md、sources.lock.json 和 docs/DEPLOYMENT.md。检查现有 active.json 所指安装；不要读取或输出 .env、API key、模型配置全文。
2. 三步以上任务列出清单。只在独立 Root/DSH_HOME 做自动测试，禁止以开发验证为理由修改用户的全局 npm 运行时、当前桌面 app.asar 或现用 profile。
3. 依赖入口为 sources.lock.json、runtime/pi-runtime/mcp-runtime 各自的 package.json 与 package-lock.json、requirements.txt。升级要审查所选来源提交、上游许可证、原生插件接口、严格匹配的适配锚点；不得只改显示版本。
4. 保持 Seep lab 会话开关的上游设计。不要把任何设备的强制提示词或授权声明写入所有设备的全局 AGENTS.md。
5. APK/EXE 是完整技能目录；Seep 是 MCP + 原生插件；Purge 是独立插件 + 宿主补丁。不要把这些误称为同一种安装项。
6. 保留用户 provider/model、preset 和 !!js。安装、Web 运行、桌面运行、注入、MCP 握手和实际模型请求各自记录证据；文件存在不能证明运行成功。
7. 安装失败必须非零退出。不要把 na/skipped 算待应用，也不要隐藏 pending/missing_file。桌面没有实测就写未验证。
8. 提交前运行 tests/run.ps1；变更部署流程需独立安装和 MCP 握手。检查所有 staged 文件，排除凭据、用户样本、日志、私有配置、大工具包和第三方二进制。
9. 主入口是 DSH + Purge，PI 可选、独立配置启动。-Modules 是完整组件选择，capabilities 的 -Components 是工具组。PI-only 不下载 DSH/Purge/桌面；APK/EXE 无独立 GUI，由 PI 加载完整技能。具体契约以 docs/USAGE.md 和 resolve_modules 为准。
