# 宿主内容存储基础：现成方案与后端选型

检索日期：2026-10-23。对应[本轮任务](2026-10-23-repository-content-store.md)及[回执契约第 3 节](../../../product/docs/contracts/repository-host-receipts.md#3-共同封套引用与存放)。本文件是软件工程选型记录。

**工程选择：复用 Python `sqlite3`／SQLite，以同一事务保存类型、操作归属、字节身份和原始 BLOB，再由独立连接复读。** 增加薄宿主 Adapter，公开创建、打开、追加和按明确引用读取。采用 `journal_mode=DELETE`、`synchronous=EXTRA`；本轮每份记录上限 2 MiB，分块另做。现成 MCP 提供通用文件或 SQL 能力，仍需本项目的类型、归属和不可变规则；直接接入会增加工具及进程接口。

## 已核对的候选

表中 FACT 来自本次读取的上游页面或本仓库源码；运行兼容性为接口与依赖判断，候选 MCP 未安装或联调。

| 候选 | FACT：覆盖、兼容与维护 | 权限及当前缺口 | 结论 |
| --- | --- | --- | --- |
| 官方 Filesystem MCP | 提供读取、写入、编辑和移动等文件工具；`write_file` 可覆盖已有文件，写入内容参数为字符串。当前源码包要求 Node.js ≥24，并依赖 MCP Server、diff、glob、minimatch、zod。官方仍维护当前开发线，旧版本不回补安全修复。[接口](https://github.com/modelcontextprotocol/servers/blob/main/src/filesystem/README.md)、[包依赖](https://github.com/modelcontextprotocol/servers/blob/main/src/filesystem/package.json)、[维护策略](https://github.com/modelcontextprotocol/servers/security) | 通过启动目录或 MCP Roots 限定访问范围；Python 宿主还需 MCP 客户端及 Node 子进程。通用文件工具没有本项目的 operation_id／record_kind 绑定和跨元数据、原字节的提交契约。 | 本轮不引入。接口允许覆盖，与仅追加要求不同；包装它仍需实现主要业务约束。 |
| 官方归档 SQLite MCP | 提供 SELECT、INSERT／UPDATE／DELETE、建表和业务摘要等工具。包声明 Python ≥3.10，运行依赖 `mcp[cli]>=1.6.0`，构建依赖 hatchling。仓库页面显示 2025-05-29 归档，官方明确停止维护及安全修复。[接口](https://github.com/modelcontextprotocol/servers-archived/tree/main/src/sqlite)、[依赖](https://github.com/modelcontextprotocol/servers-archived/blob/main/src/sqlite/pyproject.toml)、[归档声明](https://github.com/modelcontextprotocol/servers-archived) | 宿主指定 `--db-path`，工具可运行修改 SQL；这不是仅追加、按引用读取的专用接口。Python 版本声明符合本项目使用方向，当前 SDK／Runtime 组合未联调。 | 不采用已归档服务；保留复用其底层 SQLite 的方向。 |
| Python `sqlite3`／SQLite | Python 标准库接口；SQLite 不需要独立服务器，`bytes` 与 BLOB 可直接往返，有事务与明确提交控制。模块是 CPython 的可选构建项，部署仍需核对实际可导入性及所链接 SQLite 版本。SQLite 官方发布记录在检索日仍有更新。[Python 3.14 接口](https://docs.python.org/3.14/library/sqlite3.html)、[SQLite 发布记录](https://sqlite.org/changes.html) | 宿主进程直接访问数据库及 journal 所在目录，不引入通用 SQL 工具。由 Adapter 限制路径、固定 SQL、操作归属和类型，拒绝覆盖及错误引用。 | 首选。复用已有事务后端，新增代码集中在本项目的数据契约。 |
| 现有 `Workspace.write` | [本仓库源码](../../../product/axiom_forge/tools/storage.py)使用受限路径、链接检查、临时文件、flush／fsync，再以 Windows rename 或 POSIX link 发布；已有路径拒绝覆盖，单文件上限 2 MiB。 | 当前接口服务 AgentRun，返回路径；没有 ContentRef、类型及 RPO 元数据，也没有这些数据和原字节的共同事务或独立连接复读。 | 复用路径与限额经验；若按多个文件补齐上述功能，还需自行设计多文件恢复，代价高于单库方案。 |

## 许可证、依赖和费用

**FACT：** 当前 Filesystem 所在仓库的 [LICENSE](https://github.com/modelcontextprotocol/servers/blob/main/LICENSE)处于 MIT 向 Apache-2.0 的过渡：新代码／规范使用 Apache-2.0，已同意重许可的旧贡献采用 Apache-2.0，尚未同意的旧贡献保留 MIT，非规范文档贡献采用 CC-BY-4.0。包内许可证字段要求查看 LICENSE，因此本记录不把当前整个仓库统称为 MIT。归档 SQLite MCP 的[仓库许可证](https://github.com/modelcontextprotocol/servers-archived/blob/main/LICENSE)为 MIT。

**FACT：** [Python 许可说明](https://docs.python.org/3/license.html)列出 PSF 许可及随发行版保留的其他许可；[SQLite 交付代码与文档](https://sqlite.org/copyright.html)属于公有领域，构建辅助脚本可能另有许可证。本轮直接调用已提供的库，不复制 MCP 源码。

**工程判断：** 这些本地代码方案不需要额外远程服务调用或按次 API 计费；开源／公有领域许可不等于部署运营成本为零。运行、磁盘、备份及所选商业支持由宿主承担。没有为本轮购买服务或安装候选 MCP。

## 采用方案与必要 Adapter

**INFERENCE：** 将原始 BLOB 与其 record_id、operation_id、record_kind、字节长度及 sha256 放在同一数据库事务，可避免“字节文件已发布、独立清单尚未更新”的应用层窗口。SQLite 提供[事务原子性](https://sqlite.org/transactional.html)，具体写入和错误处理仍由本项目验证；数据库事务不覆盖未来 Git refs、世界文件或登记操作。

**工程选择：** Adapter 接收可信宿主提供的私人目录和操作 ID；ContentRef 继续仅含 record_id／sha256，不接收来源指定的绝对记录路径。固定 SQL 使用参数绑定，创建与打开分开；只追加记录，重复标识、跨操作、错误类型、超限、链接路径、缺失及损坏都报具体错误。提交后关闭写连接，以独立连接读取并核对原始字节和登记元数据，再返回 ContentRef。提交结果或复读未知时保留材料、报告状态，交调用者核对。

**FACT：** SQLite 官方 [synchronous](https://sqlite.org/pragma.html#synchronous)说明：DELETE 模式下 EXTRA 在 journal 删除后增加目录同步；FULL 在 rollback 模式下是否耐断电取决于文件系统。官方 [PRAGMA 总则](https://sqlite.org/pragma.html)还说明未知设置可能被静默忽略，因此设置后须查询实际值。`trusted_schema` 默认开启，官方建议每条连接关闭。

**工程选择：** 写连接设置并核对 DELETE／EXTRA；所有连接将 trusted_schema 设为 OFF 并查询核对，固定自身 Schema，不加载数据库扩展或任意调用者 SQL。读入核对 Schema 和登记数据；SQLite 的结构检查结合原字节 sha256、类型及归属检查使用。同期可写进程通过事务／唯一标识冲突给出确定错误，不自动重复提交。

## 验证范围与待办

**FACT：** [SQLite 原子提交说明](https://sqlite.org/atomiccommit.html)以操作系统同步和底层存储行为等条件为前提。独立连接复读能验证当前可读取的提交结果；物理断电能力仍需针对宿主设备另行验证。

**OPEN QUESTION：** 本笔记完成资料与接口核对；实现验收在[本轮任务](2026-10-23-repository-content-store.md)记录。下一步须实测公开 API 的原字节往返、重开、并发／重复拒绝、类型／操作错误、内容及元数据损坏、进程中断和提交后复读失败。候选 MCP 未安装／联调；网络文件系统、跨机共享、多文件事务、分块和物理断电均未作为本轮验收。私人目录访问依赖宿主 OS 权限；同权限者可改写未被外部锚定的库，普通哈希不能替代人工身份或接受验证。
