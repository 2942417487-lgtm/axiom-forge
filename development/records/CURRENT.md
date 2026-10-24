# 系统开发当前状态

核对日期：2026-10-24。本文件是开发接续摘要；启动时仍须核对现场 Git 和用户消息，不把它当作自动执行授权。

## 最新集成与当前接续

- 当前为[分离遗漏修复与文件职责复审](tasks/2026-10-24-separation-reaudit.md)。基线 359 文件无整文件遗失；复审确认的 A1–A5 已修复，共同规则与工具配置已收敛。当前全部 294 个测试 ID 分三组联跑，292 项通过、2 项既有权限跳过；Standards／Spec 均无剩余发现，工作集交付分支审阅，尚未合并。
- 当前任务为[产品／开发目录与规则作用域分离](tasks/2026-10-24-product-development-separation.md)，分支 `codex/product-development-separation`，基线仍为下述 PR #13。产品内容已归 `product/`，开发资料归 `development/`，研究指令改用内部规则；实现、组合验收与独立审查完成，改动未提交。
- 最新集成为 [PR #13](https://github.com/2942417487-lgtm/axiom-forge/pull/13)，由用户合并，合并提交 `43d4e7299206acca5011c3500a1f642c62a9b918`。2026-10-24 GitHub API 确认 merged；fetch 后本地 main／origin/main 均同步至该提交。合并树与 PR 最终 head `0f88dee` 的树相同。
- [工程技能与文档整理](tasks/2026-10-20-docs-and-skills.md)及其[隐私检查与发布](tasks/2026-10-20-privacy-and-publish.md)均已完成并随 PR #12 集成。原内容提交为 `48ba3f0e7d7ceb71631f8ae0d2139379135035a4`；没有因文档整理修改源码、Schema、Runtime 或功能布局。
- 用户授权的隐私检查、推送、远端复核和合并已经执行；新提交使用 noreply，历史作者 metadata 按用户选择保留。既有授权不自动延伸到新任务。
- [开发日志接续核对](tasks/2026-10-20-handoff-audit.md)提交 `401aa51b3e797e4c3c2f228379ee141cb6095bdc`、[回执数据基础](tasks/2026-10-23-repository-receipt-foundations.md)、[宿主内容存储](tasks/2026-10-23-repository-content-store.md)均已随 PR #13 集成。发布、测试与合并依据见[发布记录](tasks/2026-10-24-receipts-storage-pr.md)。
- 前次[任务清单补齐与遗漏复查](tasks/2026-10-24-task-inventory-audit.md)已完成，分支 `codex/task-inventory-audit`，固定基线为上述合并提交。该阶段清单、文档检查与双轴独立复查已完成，工作集未提交；完整任务、状态及来源集中在 [TASKS.md](TASKS.md)。
- 随后用户确认现有 AGENTS.md／CLAUDE.md 归开发侧，再明确授权本次同时完成目录与规则分离。原决定记录见[规则分离任务](tasks/rule-scope-separation.md)，本轮实际结果以当前实施记录为准。
- 原 `codex/project-metadata-contract` 分支保留在 `75daed57caef3d2fea7e0a59f0a6096b64de6368`，`codex/world-portability-contract` 保留在 `6221d552e37c74b8937e04db7752f3b7d50354c9`。旧 worktree 5723 为干净的 detached HEAD，位于 `d2604248ff5e97ec1f1e5e85407c279861fec6db`；忽略缓存保留，不 reset／clean。

## 功能结构与证据边界

| 功能 | 已有实现／实际边界 | 使用与依据 |
| --- | --- | --- |
| 数据、实体关联与快照 | 严格 Schema、知识校验与自包含固定 Canon Snapshot | [Schema](../../product/resources/schemas/README.md)、[世界工作区](../../product/docs/guides/world-workspaces.md) |
| Evidence 与岗位契约 | 七个厂商无关岗位；输入投影、首轮隔离条件与后续审查／综合约束 | [岗位](../../product/resources/agents/README.md)、[Evidence](../../product/docs/contracts/evidence.md) |
| 本地工具层 | 可信 ToolSession、来源读取回执和任务内暂存；不是 OS 沙箱 | [工具](../../product/docs/tools.md) |
| Runtime | 官方 SDK 单岗调用、输入投影、结果验证与 Artifact；真实调用须显式授权 | [Runtime](../../product/docs/runtimes.md) |
| 路由与四种模式 | 宿主策略选择；固定四岗位独立首轮后交叉审查、草案、Red Team 与综合 | [路由](../../product/resources/routing/README.md)、[模式](../../product/resources/modes/README.md) |
| TaskManager 与人工 Canon 宿主 | 固定快照检索、审查包、独立人工批准及世界 Canon 分支 | [任务管理](../../product/docs/guides/task-management.md) |
| 持久化／显式恢复 | checkpoint、事件、输入／Artifact 复验与预算预留；不恢复厂商会话 | [恢复](../../product/docs/guides/recovery.md) |
| 外部世界工作区 | 系统／世界／宿主分离，显式 --world，本机私人状态及独立世界 Git | [工作区](../../product/docs/guides/world-workspaces.md)、[PR #9 任务](tasks/separate-world-workspaces.md) |
| 项目元数据 | 四字段 Schema、PRJ 生成、严格文件检查及 world_id 只读关联；不登记或更新仓库 | [只读检查](../../product/docs/guides/project-metadata-check.md)、[PR #11 实施记录](tasks/project-metadata-implementation.md) |
| 仓库回执数据基础 | PR #13 已集成四类 Schema、RPO／RRC、原字节引用与链校验；提供离线数据验证，无宿主执行权限 | [校验接口](../../product/docs/guides/repository-receipt-validation.md)、[实施记录](tasks/2026-10-23-repository-receipt-foundations.md) |
| 宿主内容存储 | PR #13 已集成 sqlite3／SQLite 原字节与类型／操作元数据同事务提交、独立连接复读 | [存储接口](../../product/docs/guides/repository-content-store.md)、[实施记录](tasks/2026-10-23-repository-content-store.md) |
| 工程技能／开发接续 | PR #12 已接入项目专用 af-dev 技能与集中开发日志，不向研究 Runtime 注册 | [整理任务](tasks/2026-10-20-docs-and-skills.md)、[技能用法](skills/README.md) |

模型真实合成接入测试与研究流程离线验收分别记录，均不等于完整真实科学研究已验收。手工 Claude 岗位加载不等于受控 SDK 工具授权。

## 未完成与已知缺口

完整清单及逐项来源见 [TASKS.md](TASKS.md)；这里仅保留接续重点。

1. [仓库宿主回执](../../product/docs/contracts/repository-host-receipts.md)的数据基础与单份内容存储已集成。回执本身的持久化／外部登记、分块、防重放、人工验证与仓库登记／更新执行器尚未实现；H01–H26 产品行为矩阵仍待后续宿主验收。
2. 安全研究档案、Conversation／ImportAnalysis、敏感预检、附件／索引、GitHub 产品接续、导入／介绍导出尚未实现；标准 Git 世界仓库仍为首版主载体，完整包是未来可选离线备份。
3. CanonHost 当前将完整批准 metadata（包括 MAC）写入 Git 提交说明，跨机共享前需单独处理。仅核对源码发现此缺口，未扫描或断言个人世界已有泄露，未修改提交或重写历史。
4. 通用搜索后端、计算执行器、MATLAB Adapter、Eval、UI 和 Phase 12 未实现；Python 程序登记为空、默认关闭。Phase 13 的产品工程需求交接与 Phase 15 的 Eval 驱动动态路由仍有缺口，见总表 PHASE-12–15。
5. [规则作用域分离实施](tasks/2026-10-24-product-development-separation.md)及[复审遗漏修复](tasks/2026-10-24-separation-reaudit.md)已完成验证，尚未合并，用户已授权提交并推送 PR。机器规则语言策略和跨语言产品化整体设计仍另定，见总表 GOV-01–03。

## 最近验收记录

遗漏修复后的当前 294 个测试 ID 分三组联跑（242／38／14），292 项通过、2 项既有 Windows 符号链接权限跳过，0 失败／错误／缺失；每组先通过源仓库边界检查。47 Schema、7 岗位契约、12 路由登记与产品边界检查通过。原 A1–A5 及复核追加的两项 P3 均关闭，Standards／Spec 无剩余发现，详见[最终修复记录](tasks/2026-10-24-separation-reaudit.md#后续修复与最终验证)。

此前目录与规则分离的完整 discovery 运行 276 项，修正测试后相关 43 项通过；当时 284 个测试 ID 中 282 项有通过记录、2 项既有权限跳过。这是历史批次，详见[原分离记录](tasks/2026-10-24-product-development-separation.md)。

PR #11 的新增 20 项测试均已取得通过结果，其中真实符号链接用例在 2026-10-18 由 Windows 管理员进程单独补验，0 跳过。结合首轮全套与失败项修正复验，218 项中 217 项有通过记录，1 项旧符号链接测试仍保留该轮跳过记录；不是第二次完整 discovery 全通过。详见 [实施记录](tasks/project-metadata-implementation.md)。

PR #12 文档／技能检查与独立审查结果见[整理任务](tasks/2026-10-20-docs-and-skills.md)，隐私及合并结果见[发布任务](tasks/2026-10-20-privacy-and-publish.md)。开发日志核对见[原接续任务](tasks/2026-10-20-handoff-audit.md)。回执基础阶段完整回归运行 248 项，无失败，2 项既有符号链接测试因 OS 权限跳过；审查修正后 31 项回执测试另行通过。该阶段双轴各 1 项发现均已关闭，见[实施记录](tasks/2026-10-23-repository-receipt-foundations.md)。

内容存储阶段，存储、回执与基础校验联合回归 96 项全部通过，0 跳过；Spec 指出的裸库路径缺口修正后，27 项存储测试另行通过。Standards 无发现，Spec 1 项 P2 已复核关闭。该阶段未重跑全套 discovery；验证顺序与范围见[实施记录](tasks/2026-10-23-repository-content-store.md)。

2026-10-24 发布准备版本重新联跑 97 项相关测试，全部通过、0 跳过；功能提交后源码未再变化。候选树与实际功能提交对象的脱敏扫描通过，详见[发布记录](tasks/2026-10-24-receipts-storage-pr.md)。

前次清单整理检查九份开发文档、211 个本地链接、23 处标题引用、69 个唯一任务 ID、忽略规则与系统边界，均通过。Standards 0 项，Spec 1 项 P2 修正后复核关闭，未重跑业务测试；详见[复查记录](tasks/2026-10-24-task-inventory-audit.md)。

## 接续注意

产品系统版本为 0.3.0；指纹覆盖内部 policies、岗位／模式、计算协议、Schema、路由与程序登记，开发入口和操作者 README 不再进入研究指令／指纹。旧 checkpoint 因版本或资源不匹配而停止，保留原记录，不迁移或补签。安装器仍未实现。

当前授权范围的目录／规则分离及 A1–A5 遗漏修复已完成，原清单和分离工作集保留，分支仍为 `codex/product-development-separation`。产品用法从 product/README.md 进入，开发用法从 development/README.md 进入。介绍规范保持 0 字节，用户已授权提交并推送 PR，等待用户审阅合并。
