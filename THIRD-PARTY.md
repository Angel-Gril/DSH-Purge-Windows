# 来源、许可证与改动边界

本仓库只发布部署编排代码、锁定清单和文档。四个项目由目标设备从各自 Git 远程拉取，没有把用户的私有源码或二进制镜像到这里。

| 来源 | 许可证 | 整合方式 |
| --- | --- | --- |
| angusdevgo/Seep-Reverse-Lab | GPL-3.0-or-later（以锁定源码LICENSE为准） | 保留完整源码；使用原生seep-lab，部署副本严格适配JS MCP启动命令与Playwright版本 |
| Angel-Gril/apk-reverse-new | MIT | 完整skills/apk-reverse覆盖层，保留许可证和references/scripts/evidence |
| Angel-Gril/exe-reverse | MIT | 完整skills/exe-reverse覆盖层，保留许可证和references/scripts/evidence |
| Angel-Gril/dsh-purge-harness | MIT | 完整插件部署副本，实际包名dsh-purge-community，不通过其bootstrap切换到别的fork |
| DeepSeek Harness | MIT（npm与官方宿主各自声明为准） | npm包独立安装；桌面从官方地址下载/目标机已有安装 |
| JS reverse MCP | Apache-2.0 | npm固定3.0.9，保留依赖包许可证 |
| @earendil-works/pi-coding-agent | MIT | 可选npm固定1.4.0；独立运行时，使用内置MCP；不复制本机上游扩展或全局提示词 |

Seep自带的各工具/知识库/再分发组件还有自己的许可证。分发离线工具包或公开修改版时需逐个核对，不能用本仓库的编排代码许可证覆盖它们。IDA等商业软件及许可证由每台设备自行安装。

上游内容在目标机本地合成时仍保留原始文件和许可证。工作台的Seep适配包括严格锚定的启动命令替换，以及本机宿主依赖junction，源码见scripts/workbench.py；上游接口变化时会停止安装，要求审查更新。
