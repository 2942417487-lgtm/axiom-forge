# 宿主内容存储基础

日期：2026-10-23。状态：实现、验证与独立审查完成，未提交，待人工 review。

## 授权与起点

用户确认本轮先检索现成方案，再实现不可变记录保存、记录类型与操作归属校验、写后复读及损坏检测，并完成测试与独立审查。分块存储、人工身份验证和 Git 登记／更新执行器留到后续。

当前分支 `codex/repository-receipt-foundations`，HEAD 为 `401aa51b3e797e4c3c2f228379ee141cb6095bdc`。起始工作集包含上一阶段已审查、未提交的 23 份回执基础文件；原内容保留，在同一非 main 工作分支继续。上一阶段验收见[原任务](2026-10-23-repository-receipt-foundations.md)。本轮不提交、推送或创建／合并 PR。

## 范围与验收

- 真实检索官方或可信维护的 MCP／现成后端；记录功能、运行依赖、维护／许可证、权限、费用及采用理由。选型笔记保存在本目录，不作为世界 Evidence。
- 以可信宿主选定的外部目录和操作 ID 为入口，不创建 WorldWorkspace。内容以原字节保存，ContentRef 仍仅包含 record_id 与 sha256；类型和操作归属由宿主存储元数据维护。
- 只提供创建、打开、追加和按明确引用读取；拒绝覆盖、错误归属／类型、缺失、损坏、超限和不安全路径。单份记录上限 2 MiB；大对象明确拒绝，等待后续分块接口。
- 只有持久提交及独立连接复读验证完成才返回保存成功。初始化失败或提交／复读失败保留已有材料并报具体状态；不自动重试写入或清理数据库／原件。
- 以公开 API 测试原字节往返、重开、错误引用／类型／操作、内容和元数据损坏、路径边界、并发／重复、进程中断及复读失败；按改动范围运行回归与静态检查。
- 分别执行只读 Standards／Spec 独立审查，包含上一阶段未跟踪文件和本轮明确新增清单，区分累计差异与本轮变化。

## 实现边界

本轮存储适用于宿主本机可信私人目录。SQLite／文件系统同步依赖操作系统和存储设备；软件测试记录正常提交、可检测损坏及进程中断行为，不冒充物理断电试验或 OS 隔离。

不接入研究 Agent 工具，不读取真实凭据，不产生人工接受或授权记录，不操作正式世界。普通存储类型标签、哈希和本机记录均不授予执行权限。现有回执数据校验、研究 Runtime、Canon 审批和恢复接口保留。

## 选型、验证与审查记录

### 选型与实现

真实检索与来源见[选型记录](2026-10-23-repository-content-store-research.md)。复用 Python 标准库 `sqlite3`／SQLite，增加宿主专用 Adapter；不安装或接入 MCP。当前环境实测 Python 3.14.7、SQLite 3.50.4 可用。官方 Filesystem MCP 的覆盖写和通用目录接口、已归档 SQLite MCP 的修改 SQL 工具均不能直接满足本轮类型／操作归属与不可变规则。

`axiom_forge/repository_content.py` 为新模块；构造器打开已有库，`create` 独占创建，`put` 事务追加，`read` 按预期类型和 ContentRef 校验。元数据绑定 RPO、随机库身份与本机路径；字节长度和 SHA-256 由实际原字节计算。每份记录 2 MiB，不设总配额，宿主须控制调用与容量。模块未接入研究工具、CLI 或既有 Runtime。

写连接设置并核对 EXTRA，同步检查 DELETE；所有连接关闭 trusted_schema。SQLite 自身事务和锁处理数据库内一致性，独立只读连接复读原始字节。打开已有库允许 SQLite 恢复自身未提交日志；本轮没有仓库任务或人工接受的重放逻辑。

用法和错误处理见[宿主内容存储](../../guides/repository-content-store.md)。

### 实际验证

1. 首轮 `python -m unittest tests.test_repository_content -v` 在测试初始化时被沙箱临时目录 WinError 5 阻止；按平台权限机制在沙箱外重跑。26 项中仅安全诊断测试误报：测试把合成敏感值直接写在调用源码行，Python traceback 将该行展示。改用变量传入，并保留错误链的安全诊断检查；再跑 26 项全部通过，0 跳过。
2. `python -m unittest tests.test_repository_content tests.test_repository_receipts tests.test_foundations -v`：96 项全部通过，0 跳过。覆盖新增存储、前阶段回执及共享 Schema／ID／快照基础。随后只修正独立模块的裸库路径检查，新增一项回归；最终 `python -m unittest tests.test_repository_content -v`：27 项全部通过，0 跳过。
3. 进程中断用例在子进程中分别于 COMMIT 前、COMMIT 后立即退出：前者的新记录不可读取，后者的新记录可按预定原字节引用读取，原记录均保留。提交后复读失败用例返回 `write_unconfirmed` 及尝试引用，之后可显式复读确认；没有自动再次插入。以上为进程退出／故障注入测试，物理断电未测。
4. 覆盖真实 SQLite 原字节往返、2 MiB 边界、并发创建／追加、ID 冲突、锁竞争、记录类型／操作、内容／元数据／格式／位置损坏、缺失记录、硬链接及日志路径。符号链接拒绝使用路径检测注入，未新增需要管理员符号链接权限的用例。裸库拒绝在创建前和每次访问时验证，并检查目录清单或数据库字节不变。
5. `check-schemas`：47 份 Schema 及引用通过；`check-contracts`：七岗位通过；`check-system-boundary` 在沙箱外退出 0。未新增 Schema、依赖包、Agent 工具或 CLI 命令，未修改共享验证模块，所以本轮使用上述定向联合回归，没有重跑完整 discovery 或真实模型流程。
6. 累计工作集 28 文件，其中本轮新增五份文件，仅修改前阶段四份导航／状态文档。十份 Markdown 的代码块与本地链接、全部工作集 UTF-8／无 BOM、结尾换行、尾空白、Python／JSON 语法及 `git diff --check` 通过。凭据、私人状态、缓存和临时目录忽略规则通过；`.env.example` 变量为空，介绍规范为 0 字节。

### 独立审查

两个只读 Agent 按 `af-dev-code-review` 分别检查 Standards／Spec，固定基线为 `401aa51b3e797e4c3c2f228379ee141cb6095bdc`；使用累计 Git diff 加明确的 18 份未跟踪文件，并用起点字节清单区分前阶段依赖和本轮变更。

| 轴 | 结果 | 修正与复核 |
| --- | --- | --- |
| Standards | 初次无 actionable findings | 裸库修正后的定向复核仍无新增问题 |
| Spec | 1 项 P2：只查祖先 `.git`，遗漏裸 Git 仓库 | 按[官方布局](https://git-scm.com/docs/gitrepository-layout)增加祖先 HEAD／objects／refs 检测，在建目录前及每次连接前拒绝；新增无副作用回归，原审查 Agent 复核关闭 |

最终源码审查无未关闭问题。审查未扩展为人工身份验证、完整回执保存或物理断电验收。

### 保留状态与后续

本轮仅新增模块、测试、用法、任务及选型记录；前阶段源码、Schema、示例、测试与原任务均与本轮起点字节一致。原工作集中的四份文档变化为 README、回执契约、CURRENT 和 CHANGELOG。没有改 `.agents`、AGENTS、Runtime、CanonHost、恢复逻辑或世界绑定。

分支仍为 `codex/repository-receipt-foundations`，HEAD 为 `401aa51`，暂存区为空；main／本地 origin/main 仍为 `a50e0ce`。没有提交、推送、PR、合并、远端查询、真实凭据读取或正式世界操作。

后续候选是内容分块、回执链的持久发布及控制面、人工验证和仓库执行后端，需另行确定范围。本轮单份内容存储已交付，可供宿主后续集成。
