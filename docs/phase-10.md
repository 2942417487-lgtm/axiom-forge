# Phase 10：任务运行与人工 Canon 审批

本阶段复用现有 Runtime、Router 和四种模式，实现简单 Python Task Manager。没有引入 LangGraph。新增 CLI 是宿主控制入口，研究岗位的工具集合没有增加审批、Canon Apply 或 Git 写入能力。

## 使用流程

问题文件使用 UTF-8。正式世界观应先由用户审查并提交至当前 Git 分支；任务创建和审批要求当前 Canon 与 Git 基线一致。`--entity` 指定关联实体，可重复。没有指定时关联集合为空，不凭模型猜选实体；完整固定快照仍提供给全部岗位。

```powershell
# 问题写入 .cache/question.txt；配置须按任务长度、输出和费用另行调整。
.\.venv\Scripts\python.exe -m axiom_forge tasks run --question-file .cache/question.txt --mode court --entity TECH-001 --config examples/mode-host.json --credentials .env --allow-live
```

这个命令会调用真实模型，必须显式 `--allow-live`；本轮没有运行，也没有新增付费授权。示例中的输出上限和模型单次费用上限主要用于小规模接入测试，不能保证完整科学研究能在相同参数内完成。模型与工具仍由可信宿主配置，Lead 不能更改模型、预算、工具权限或 Canon 快照。

执行次序为：用户问题 → Lead Planning → 固定 Canon 检索 → 四岗位独立研究/审计 → 四岗位交叉审查 → 综合草案 → Red Team → 最终综合。Lead 必须覆盖全部四个审计岗位，其 question、required_checks 和 entity_ids 通过 `planning_assignment` 明确传给相应 Specialist；每个首轮输入在任何首轮答案产生前构建，交叉审查读取同一份首轮结果。计划不能删除审计领域。检索从固定快照读取指定实体的依赖/冲突闭包及附带 Evidence，保存带哈希 Artifact；全部岗位仍持有同一完整快照。科学真实性必须另外审查。

成功任务在 `.cache/tasks/<TSK>/` 保存 `created.json`，以及 `completed.json`（无 Canon 提案）或 `waiting.json`（有最终提案）。状态包含 Run、12 次 AgentRun、结果和 Artifact 引用；Lead 与综合草案可通过其 Artifact 读取。最终提案集取自最终综合，草案不是同时待应用的另一份变更。失败保存 `failed.json` 和真实 Runtime 回执，不伪造失败 Agent 的完成 Artifact、不运行后续阶段；`created.json` 是初始有效状态，不代表失败阶段的完整 checkpoint。

有提案时生成 `.cache/canon-reviews/<内容 SHA-256>/bundle.json` 与 `review.md`，控制台返回路径。审查内容包括完整 add/update/delete 前后值、新增 Evidence、来源、假设、不确定性、反例、Red Team、综合和未解决问题，以及一起提交的审批记录模板。**批准整份包**，不支持部分批准或编辑后沿用旧审批；需要调整时应产生新的研究结果/审查包。没有提案不发布仅发现的新 Evidence。

CanonChange 继续沿用已有 canon_entry 类型；actor、timeline 等专用记录的扩展修改接口不在本轮。审查文本被修改时会拒绝审批，规范 JSON 是完整内容依据。

首次由本地操作者初始化专用审批凭据；不使用模型 API Key 代替审批 Key：

```powershell
.\.venv\Scripts\python.exe -m axiom_forge canon init-approval
```

该命令在被 Git 忽略的 `.env.approval` 写入随机 Key，不打印、不覆盖、不提交。POSIX 使用 0600 权限；Windows 继承当前用户目录权限，须使用独立系统账号/ACL 管理需要更强隔离的场景。丢失 Key 后旧批准不能验证；本阶段不提供轮换或自动恢复。不要把 `.env.approval`、`.env`、`.cache` 上传或发给模型。

读取 `review.md` 和规范 JSON 后，在交互终端运行：

```powershell
.\.venv\Scripts\python.exe -m axiom_forge canon approve --bundle .cache/canon-reviews/<SHA256>/bundle.json --reviewer "你的名字"
# 或明确拒绝：
.\.venv\Scripts\python.exe -m axiom_forge canon reject --bundle .cache/canon-reviews/<SHA256>/bundle.json --reviewer "你的名字"
```

终端要求键入完整内容 SHA-256，随后写入带 reviewer、时间、提案哈希、任务哈希与 HMAC 的 `approval.json`。拒绝会另外保存 `rejected.json`，不能 Apply；同一包的决定不可覆盖。原始 waiting 状态与模型输出保持原样。直接编辑 JSON 的 `approval_status` 或 `CanonChange.approval` 不能代替宿主审批。

批准后应用：

```powershell
.\.venv\Scripts\python.exe -m axiom_forge canon apply --bundle .cache/canon-reviews/<SHA256>/bundle.json
```

宿主再次校验任务/Artifact/审查包/HMAC、Git HEAD 和 Canon 基线，校验包含全部 Evidence 与实体引用的目标世界。通过临时 Git 索引和 Git 提交对象创建 `canon/<RUN>` 分支，当前分支、工作区和暂存区保持原状。提交只包含包中列出的 `world/` 变更；审批者、时间、包哈希及签名回执记录在提交消息，world/decisions 同时增加“人工批准不证明现实 FACT”的记录。不会自动 push、checkout 或 merge。你可先查看分支差异，再按照正常 PR 流程发布和合并：

```powershell
git diff HEAD canon/<RUN> -- world
git push origin canon/<RUN>
```

本地 TaskState 的 `canon_commit` 单独保存批准与提交信息，COMMITTED 的原始 pending 模型提案和输出 Artifact 哈希保持不变。Canon 版本仍指分析基线，`canon_commit.new_canon_version` 指分支提交后的内容版本。通用 TaskState 校验验证结构和内容绑定；**不使用 Key 验签，也不证明 Git 分支已创建**。真正 Apply 的签名验证和原子分支发布在 CanonHost。

## 边界与失败处理

HMAC 防止没有宿主 Key 的调用者伪造或篡改批准；它不是远程身份认证，也不能证明持有 Key、拥有同等 OS 文件权限的其他进程一定是人。安全边界是可信本地操作者/宿主与研究 ToolSession 的隔离。不能声称 CLI 或进程权限本身隔离了所有同用户程序。

Git 命令使用参数列表，不执行 shell、模型生成脚本、用户 hooks、外部 diff、签名程序或全局 Git 配置；Git 作者身份使用本仓库 user.name/user.email。临时索引不会采集当前暂存区；拒绝知识库链接/重解析路径、过大或非有限 JSON，拒绝过期 HEAD/Canon、内容篡改、重复 Apply 和覆盖已有分支。创建分支时校验基线引用并要求新分支尚不存在。失败可能留下不可达 Git 对象，现有分支和 world 文件保持原状。

`commit-prepared.json` 先于分支发布保存。若进程在分支发布与 `committed.json` 写入之间中断，分支可能已创建；先人工查看该回执和分支。禁止盲目重试或覆盖分支。本阶段没有 Phase 11 的全量事件日志、崩溃恢复、checkpoint 重放、多用户审批服务或并发任务派发。

## 离线验收

```powershell
.\.venv\Scripts\python.exe examples/offline_task_manager.py
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

演示在临时仓库使用显式 SYNTHETIC Adapter，执行真实 Runtime 契约、文件保存、审批签名和 Git 分支创建；不会读取真实 `.env`，不会调用 API，也不会导入正式 world。测试身份批准仅用于隔离测试，不代表用户对正式设定的批准。三个 `examples/canon_{review,approval,commit}.json` 是结构样例，MAC 和 Git SHA 为占位值，不能用于 Apply。

现成 MCP 能力的检索、采用方式与缺口见 [本轮任务说明](tasks/phase-10.md)。

2026-10-06 实际验收：全量 **162 项离线测试通过**（298.826 秒）；独立临时仓库演示成功创建 Canon 分支且 main 不变；39 个 Schema、7 个岗位契约、12 个模型登记均通过校验，正式 world 仅包含 world/world.json。编译检查、Git 差异检查与敏感文件忽略检查通过；没有初始化正式审批 Key、没有正式 Canon Apply、没有新增 API 调用。
