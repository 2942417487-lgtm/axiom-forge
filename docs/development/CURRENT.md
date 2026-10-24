# 系统开发当前状态

核对日期：2026-10-24。本文件是开发接续摘要；启动时仍须核对现场 Git 和用户消息，不把它当作自动执行授权。

## 最新集成与当前接续

- 最新集成为 [PR #12](https://github.com/2942417487-lgtm/axiom-forge/pull/12)，合并提交 `a50e0cee3c37db1250e114ba3c94e9e3e3d9f136`。2026-10-20 核对时，HEAD／main／本地 origin/main／远端 main 一致，原工作目录干净；GitHub API 确认已合并。该状态是新建本次工作分支前的实测，不代表后续窗口可免除现场核对。
- [工程技能与文档整理](tasks/2026-10-20-docs-and-skills.md)及其[隐私检查与发布](tasks/2026-10-20-privacy-and-publish.md)均已完成并随 PR #12 集成。原内容提交为 `48ba3f0e7d7ceb71631f8ae0d2139379135035a4`；没有因文档整理修改源码、Schema、Runtime 或功能布局。
- 用户授权的隐私检查、推送、远端复核和合并已经执行；新提交使用 noreply，历史作者 metadata 按用户选择保留。既有授权不自动延伸到新任务。
- [开发日志接续核对](tasks/2026-10-20-handoff-audit.md)已提交至 `401aa51b3e797e4c3c2f228379ee141cb6095bdc`；2026-10-23 现场确认原分支与本地远端跟踪引用一致、工作目录干净，本轮未查询远端。
- [仓库宿主回执数据基础](tasks/2026-10-23-repository-receipt-foundations.md)和[宿主内容存储基础](tasks/2026-10-23-repository-content-store.md)已完成实现、测试及独立审查。用户于 2026-10-24 授权发布，功能提交 `f287f3b` 已推送至 `codex/repository-receipt-foundations`，[PR #13](https://github.com/2942417487-lgtm/axiom-forge/pull/13) 已创建，包含两阶段实现及此前日志接续提交；远端初次核对的 head／base、描述和 35 文件清单一致。当前等待用户审阅，main 尚未集成，本次不合并。发布检查及文档收尾见[当前任务](tasks/2026-10-24-receipts-storage-pr.md)。
- 原 `codex/project-metadata-contract` 分支保留在 `75daed57caef3d2fea7e0a59f0a6096b64de6368`，`codex/world-portability-contract` 保留在 `6221d552e37c74b8937e04db7752f3b7d50354c9`。旧 worktree 5723 为干净的 detached HEAD，位于 `d2604248ff5e97ec1f1e5e85407c279861fec6db`；忽略缓存保留，不 reset／clean。

## 功能结构与证据边界

| 功能 | 已有实现／实际边界 | 使用与依据 |
| --- | --- | --- |
| 数据、实体关联与快照 | 严格 Schema、知识校验与自包含固定 Canon Snapshot | [Schema](../../schemas/README.md)、[世界工作区](../guides/world-workspaces.md) |
| Evidence 与岗位契约 | 七个厂商无关岗位；输入投影、首轮隔离条件与后续审查／综合约束 | [岗位](../../agents/README.md)、[Evidence](../contracts/evidence.md) |
| 本地工具层 | 可信 ToolSession、来源读取回执和任务内暂存；不是 OS 沙箱 | [工具](../../tools/README.md) |
| Runtime | 官方 SDK 单岗调用、输入投影、结果验证与 Artifact；真实调用须显式授权 | [Runtime](../../runtimes/README.md) |
| 路由与四种模式 | 宿主策略选择；固定四岗位独立首轮后交叉审查、草案、Red Team 与综合 | [路由](../../routing/README.md)、[模式](../../modes/README.md) |
| TaskManager 与人工 Canon 宿主 | 固定快照检索、审查包、独立人工批准及世界 Canon 分支 | [任务管理](../guides/task-management.md) |
| 持久化／显式恢复 | checkpoint、事件、输入／Artifact 复验与预算预留；不恢复厂商会话 | [恢复](../guides/recovery.md) |
| 外部世界工作区 | 系统／世界／宿主分离，显式 --world，本机私人状态及独立世界 Git | [工作区](../guides/world-workspaces.md)、[PR #9 任务](tasks/separate-world-workspaces.md) |
| 项目元数据 | 四字段 Schema、PRJ 生成、严格文件检查及 world_id 只读关联；不登记或更新仓库 | [只读检查](../guides/project-metadata-check.md)、[PR #11 实施记录](tasks/project-metadata-implementation.md) |
| 仓库回执数据基础（工作分支） | 四类 Schema、RPO／RRC、原字节引用与链校验完成；离线验证及双轴独立审查完成，待人工 review，无宿主执行权限 | [校验接口](../guides/repository-receipt-validation.md)、[实施记录](tasks/2026-10-23-repository-receipt-foundations.md) |
| 宿主内容存储（工作分支） | 复用 sqlite3／SQLite，原字节与类型／操作元数据同事务提交、独立连接复读；测试与双轴审查完成，待人工 review | [存储接口](../guides/repository-content-store.md)、[当前任务](tasks/2026-10-23-repository-content-store.md) |
| 工程技能／开发接续 | PR #12 已接入项目专用 af-dev 技能与集中开发日志，不向研究 Runtime 注册 | [整理任务](tasks/2026-10-20-docs-and-skills.md)、[技能用法](skills/README.md) |

模型真实合成接入测试与研究流程离线验收分别记录，均不等于完整真实科学研究已验收。手工 Claude 岗位加载不等于受控 SDK 工具授权。

## 未完成与已知缺口

1. [仓库宿主回执](../contracts/repository-host-receipts.md)的数据基础与单份内容存储已在工作分支完成。回执本身的持久化／外部登记、分块、防重放、人工验证与仓库登记／更新执行器尚未实现；内容保存不能代替这些步骤。H01–H26 产品行为矩阵仍待后续宿主验收。
2. 安全研究档案、Conversation／ImportAnalysis、敏感预检、附件／索引、GitHub 产品接续、导入／介绍导出尚未实现；标准 Git 世界仓库仍为首版主载体，完整包是未来可选离线备份。
3. CanonHost 当前将完整批准 metadata（包括 MAC）写入 Git 提交说明，跨机共享前需单独处理。仅核对源码发现此缺口，未扫描或断言个人世界已有泄露，未修改提交或重写历史。
4. 通用搜索后端、计算执行器、MATLAB Adapter、Eval、UI 和 Phase 12 未实现；Python 程序登记为空、默认关闭。
5. [规则作用域分离计划](tasks/rule-scope-separation.md) 未实施。现有工程技能已限定用途，研究规则加载、权限和恢复协议仍沿用原实现。

## 最近验收记录

PR #11 的新增 20 项测试均已取得通过结果，其中真实符号链接用例在 2026-10-18 由 Windows 管理员进程单独补验，0 跳过。结合首轮全套与失败项修正复验，218 项中 217 项有通过记录，1 项旧符号链接测试仍保留该轮跳过记录；不是第二次完整 discovery 全通过。详见 [实施记录](tasks/project-metadata-implementation.md)。

PR #12 文档／技能检查与独立审查结果见[整理任务](tasks/2026-10-20-docs-and-skills.md)，隐私及合并结果见[发布任务](tasks/2026-10-20-privacy-and-publish.md)。开发日志核对见[原接续任务](tasks/2026-10-20-handoff-audit.md)。回执基础阶段完整回归运行 248 项，无失败，2 项既有符号链接测试因 OS 权限跳过；审查修正后 31 项回执测试另行通过。该阶段双轴各 1 项发现均已关闭，见[实施记录](tasks/2026-10-23-repository-receipt-foundations.md)。

本轮内容存储、回执与基础校验联合回归 96 项全部通过，0 跳过；Spec 指出的裸库路径缺口修正后，27 项存储测试另行通过。Standards 无发现，Spec 1 项 P2 已复核关闭。本轮未重跑全套 discovery；验证顺序与范围见[当前任务](tasks/2026-10-23-repository-content-store.md)。

2026-10-24 发布准备版本重新联跑 97 项相关测试，全部通过、0 跳过；功能提交后源码未再变化。候选树与实际功能提交对象的脱敏扫描通过，详见[发布记录](tasks/2026-10-24-receipts-storage-pr.md)。

## 接续注意

AGENTS、Schema、研究模块 README 或模式说明属于现行可信资源指纹范围，相关字节变化会使旧 checkpoint 失配并停止，不自动迁移或补签。当前累计差异包含上一阶段新增的回执 Schema；本轮内容存储未修改既有研究岗位、Canon 审批或恢复校验实现。

当前接续为两阶段实现的 PR 交付；后续分块、人工验证及执行后端仍须另定范围。介绍规范保持 0 字节。发布与远端结果见[当前发布任务](tasks/2026-10-24-receipts-storage-pr.md)；同目录从 `codex/repository-receipt-foundations` 接续，核对实际工作集和提交。main 的本地集成基线仍是 PR #12。
