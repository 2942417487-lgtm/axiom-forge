# 项目元数据与身份／版本契约：文档设计任务

日期：2026-10-09；2026-10-10 补记用户复查。状态：本阶段文档设计及独立工程审查已完成，用户已复查通过；未开始 Schema、代码或产品功能实现。

## 授权与基线

用户要求接续项目，先完整读取 AGENTS.md、最新交接及六份规范，核对 Git，并等待下一阶段确认。另已完整读取被忽略的 `.cache/memory-summary-2026-10-09.md`；总结与 PDF 是参考，不授予额外执行权限，也不更新长期 Memory。

本阶段建议经用户“按照你的建议推进”确认：只细化项目元数据与身份／版本的文档契约，交付本地任务说明、字段级设计、合成示例、兼容处理和验收矩阵，进行独立工程文档审查及文档检查。

用户本阶段进一步明确：**跨机接续同一世界 Git 仓库时随仓库保留 project_id，各机只新建 workspace_id**。此前关于载体、目录和共享边界的决定继续有效，不重新要求选择。

开始前实际核对：

- 原项目目录、分支 `main`；HEAD／main／本地 origin/main 均为 `ab4fe75728d2ea48a75cc227edf432fe0ff28563`，工作区干净。
- PR #9 基础分离与 PR #10 六份规范均在本地提交图中已合并，不重复发布或合并。
- 源分支 `codex/world-portability-contract` 及其远端跟踪引用保留在 `6221d552e37c74b8937e04db7752f3b7d50354c9`；旧 detached worktree 保留。
- 六份规范与 HEAD 字节一致，介绍规范占位为 0 字节；交接／启动提示词被 `.cache` 忽略。
- 本阶段在原目录建立 `codex/project-metadata-contract` 工作分支。创建分支第一次因沙箱禁止写 Git refs 失败，按平台批准机制重跑成功；没有 reset、clean 或改动旧 worktree。

以上 origin/main 是本地已取得的引用，本阶段不因接续自动 fetch 或访问 GitHub。

## 已读取的实现依据

| 依据 | 支持的现状／限制 |
| --- | --- |
| [世界 Schema](../../../schemas/world.schema.json) | 世界身份、名称、描述、创建时间和 metadata；现行 schema_version 为 1.0，没有专用展示版本字段 |
| [业务 ID](../../../axiom_forge/ids.py)、[通用 Schema](../../../schemas/common.schema.json) | WLD／TSK／RUN 等现行标识；没有 project／conversation ID 登记 |
| [工作区](../../../axiom_forge/workspaces.py) | 本机 workspace_id 为无前缀 UUID v4，绑定 world_id、路径哈希和 layout_version；移动旧绑定拒绝自动续用 |
| [快照](../../../axiom_forge/snapshots.py)、[校验](../../../axiom_forge/validation.py) | 现行 Canon 内容版本与严格 JSON 规则；项目字段不在核心 collect_world 范围中 |
| [世界工作区规范](../../guides/world-workspaces.md) | 外部普通 Git、可信资源分离、审批与恢复边界及已有验收记录 |
| [主契约](../../contracts/world-portability-contract.md)、[目录规范](../../contracts/world-project-structure.md)、[Git 规范](../../contracts/world-git-sync.md) | 已确认项目职责、原生 Git 主路径、接受分层及尚未实现的产品入口 |

本阶段的读取是设计核对，不是完整代码审计、一次全量测试或真实研究验收。

## 范围与交付

1. 新增 [项目元数据契约](../../contracts/project-metadata-contract.md)：拟议 `project.json` 最小字段、严格 JSON／字段约束、权威来源及内容变更规则。
2. 定义 project／world／workspace／conversation 的身份归属和跨机处理；补充未绑定准备状态、重复登记、身份缺失／冲突等设计结果。只描述必要绑定，不实现宿主回执或完整对话格式。
3. 区分展示版本、项目结构格式版本、现行核心 Schema 版本、Canon 内容版本、Git 提交、本机布局版本及系统版本；保留现行哈希实现，不承诺跨语言哈希已经兼容。
4. 文档内嵌合成 JSON 示例、兼容表和正反验收矩阵。示例不注册 Schema，不保存为正式 `project.json`，不导入世界。
5. 对主契约、目录规范和 Git 协作规范作必要的指向性同步，替换已被本阶段细化的“跨机映射待定”措辞；保留历史任务说明。
6. 独立只读工程文档审查，修正具体问题，检查差异、格式、链接、嵌入 JSON、忽略边界及空值 `.env.example`，记录真实结果和限制。

字段名、PRJ／CNV 前缀、字符串边界等作为本阶段文档设计已于 2026-10-10 通过用户复查；不能称为已安装或已运行的机器接口。跨机保留 project_id 已获得用户明确决定。

## 范围之外

- 不新增／修改 Schema、业务代码、Runtime、AGENTS、岗位规则或恢复指纹。
- 不实现仓库打开／登记／同步接受、ImportAnalysis、安全档案整理、附件／索引或介绍导出。
- 不操作正式世界，不生成审批 Key，不读取真实凭据，不调用真实模型。
- 不 fetch、配置 GitHub、提交、push、创建 PR 或合并；本地工作分支上的文档留待用户复查。
- 不写介绍规范正文，保持 [占位文件](../../contracts/world-introduction-export.md) 为 0 字节。
- 不创建完整包、manifest、bundle、空扩展目录，不进入 Phase 12、工具后端、计算执行器、Eval、UI 或语言迁移。
- 不重新实施 PR #9 基础分离，不改写 PR #10 或既有历史记录，不删除分支／worktree。

## 验收约定

- 世界身份以 `world/world.json` 为准；拟议 project.json 的关联只能一致校验，不能独立重定世界。
- 同一仓库在不同机器／路径上保留共享 project_id 和 world_id，私人工作区、凭据、审批／恢复不共享。
- 展示版本只有一个存储归属，与机器内容身份分开；不自动按标签、时间或名称接受新版。
- 未绑定、旧仓库缺字段、不同世界、重复 ID、同 ID 不同内容、未知格式和本机绑定不匹配均有明确结果；不静默改 ID、补字段或覆盖。
- 格式约束能被未来 Python／TypeScript／Rust 实现；不使用默认 stringify 代替现行 Canon 哈希，不新增未经验证的哈希 profile。
- 示例与矩阵一致，成功仅表示拟议数据条件满足，不表示用户接受、Canon 批准、仓库登记或迁移已经完成。
- 独立审查与文档检查只验本阶段文档，不冒充新功能测试或真实科研验收。

## 执行与审查记录

2026-10-09：完成上述读取和基线核对，建立工作分支，记录用户跨机 project_id 决定，先形成本任务说明。契约编写、独立审查及最终检查将在实际完成后追加结果。

2026-10-09 交付补充：已编写字段级草案，提出四个最小字段及 PRJ／CNV 格式，明确未绑定准备记录与共享已绑定元数据、跨机／多工作区及缺失／冲突处理、版本权威与哈希边界。新增两个内嵌合成 JSON 示例、11 类诊断语义及 25 项未来验收案例；它们没有注册为 Schema 或现行 CLI 行为。三份已有规范仅同步本阶段身份决定、草案链接和未实现状态，历史任务说明未改写。

独立只读工程文档审查通过，未发现 actionable findings。审查核对两份新增文档、三份配套差异及必要的现行工作区／快照／JSON 校验／ID／Schema 依据，确认身份与版本、准备状态、权限和验收一致，无超范围实现或误报。审查不是完整代码审计、产品运行验收或真实科学研究；审查 Agent 没有写入文件、派发其他 Agent、操作正式世界、调用真实模型或执行 Git 写操作。

文档检查结果：

- 五份指定文档的 UTF-8／无 BOM、结尾换行、尾空白、代码块和 47 个本地链接通过；两个 JSON 示例解析及拟议四字段／ID／标签约束核对通过。
- 25 项矩阵编号完整、唯一、有序；标量计数例子的 64 个补充平面字符／128 个 UTF-16 code units 已用 Python 核对。只是文档示例检查，没有运行 M01–M25 对应的产品功能测试。
- `git diff --check` 无诊断；两份新文档的 `git diff --no-index --check -- NUL <文件>` 无格式诊断，退出 1 表示新文件与空输入不同，不记成用例失败或功能测试。
- 介绍占位为 0 字节；`.env.approval`、`.env.local`、secrets、.axiom/local、三份 .cache 接续资料、tmp、.venv、node_modules 的忽略检查通过；`.env.example` 全部变量为空值。
- 对明确五文件进行有限凭据模式检查，未发现匹配项；这不保证任意形式秘密均可识别，也不代表未来宿主敏感预检已实现。没有读取或输出真实凭据。
- `check-system-boundary` 在沙箱内因临时 Git hooks 目录 WinError 5 失败；按平台批准机制重跑后通过，实际输出确认系统资源没有正式 world 或被跟踪私人执行状态。
- 纯文档变更未运行全套 unittest、研究流程／模型联调或正式世界验收；历史通过记录没有改写为本轮测试结果。

最终清单为本契约、本任务说明及主契约／目录／Git 规范，共五份 docs；本地工作分支保留未提交文件供用户复查。HEAD／main／本地 origin/main 仍为原合并基线，暂存区无改动；无 fetch、提交、push、PR 或 merge。本阶段不更新被忽略的交接材料或长期 Memory。

2026-10-10 用户复查：用户明确答复“没问题”。随后进一步确认只继续 [仓库宿主回执契约文档设计](repository-host-receipts.md)，不写代码、不发布。项目元数据文档设计已通过，不把这项确认扩大为 Schema／产品实现、Git 发布或正式世界接受权限；上述五文档继续保留在当前工作分支。

2026-10-10 后续授权：用户在了解分段实施建议后答复“那快执行吧”，明确进入 [项目元数据最小工程任务](project-metadata-implementation.md)。本记录仍描述原文档阶段及其验收；后续代码／Schema／只读检查的实际结果另记，不将原文档通过改写为工程验收。
