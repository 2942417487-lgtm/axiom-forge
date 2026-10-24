# Phase 11：持久化、事件日志与显式恢复

当前版本的路径与兼容性以 [独立世界工作区](../../../../product/docs/guides/world-workspaces.md) 为准。世界操作显式指定外部 --world；配置与凭据来自外部宿主目录。以下历史验收保留原日期和当时结果。

Phase 10 已合并。Task Manager 2.0 在既有 Workspace 和 Runtime 上加入 checkpoint、业务事件和恢复入口；没有新增依赖、数据库或研究工具权限。现成 MCP 的实际检索与缺口见 [任务说明](../../tasks/phase-11.md)。本阶段采用离线模型和临时 Git 仓库验收。

## 查看任务与恢复研究

`tasks run` 用法沿用 [Phase 10](../../../../product/docs/guides/task-management.md)。新任务的控制台回执含 Task ID；中断导致回执缺失时，可查看本地 `.axiom/local/tasks/TSK-*` 目录，使用其中的 TSK 名称。检查命令不读取 API 凭据：

```powershell
.\.venv\Scripts\python.exe -m axiom_forge --world <外部世界目录> --host-root <外部宿主目录> tasks inspect --task-id <TSK-UUID>
.\.venv\Scripts\python.exe -m axiom_forge --world <外部世界目录> --host-root <外部宿主目录> tasks events --task-id <TSK-UUID>
```

研究阶段中断后，由操作者显式恢复：

```powershell
.\.venv\Scripts\python.exe -m axiom_forge --world <外部世界目录> --host-root <外部宿主目录> tasks resume --task-id <TSK-UUID> --config <原配置.json> --credentials <外部.env> --allow-live
```

此命令可产生新的 API 费用；本轮验收未运行真实模型。它保留 Task/Run、原始问题和固定 Canon Snapshot，核对原配置、路由策略、岗位规则、契约和 Schema 内容哈希。先验证全部已保存输入、完成回执、结果 Artifact、工具回执和计算请求，再创建新 Runtime。任何不匹配都会停止，不能用改配置、换快照或增加预算的方式偷偷续跑。

**完成岗位直接复用原 ARN/ART 和结果；未完成或失败岗位自动生成新 ARN/ART 尝试一次。** 没有后台恢复、定时重试或无限循环。重试仍失败时停止，下一次由你再运行恢复命令。首轮不会看到他人答案；交叉审查仍使用完整且相同的首轮结果集。每次新调用前先落盘输入与费用预留；失败、超时或未知费用的旧预留不退回，复用完成结果不新增预留。预算不够时返回 OPEN QUESTION，实际扣费仍须以服务商账单为准。

若 Runtime 已保存有效 `completion.json`、checkpoint 尚未写入，恢复会重新验证并接回结果，记录 ArtifactRecovered。只保存了一半结果、没有有效完成回执的调用视为未完成，保留旧预留后以新 ID 重试。厂商 Session/Thread 不用于恢复。

完成、待审、已批准、提交中、已拒绝或已提交任务不会重跑研究；`tasks resume --task-id <TSK>` 可不提供配置、凭据或 `--allow-live`，返回现状/审查包。该入口不批准或应用 Canon；提交恢复使用下面的独立命令。Phase 10 旧研究任务缺少预留和冻结输入日志，不能补造历史后恢复，需要另建研究任务。

## 人工审批与提交恢复

批准、拒绝、Apply 仍使用原本的独立人工 CLI、内容确认、专用 Key 和 HMAC。原 waiting 状态、模型输出和 pending 提案保持原样。批准回执写入与日志写入之间中断，或 Apply 在 prepared commit/分支/最终状态之间中断，可运行：

```powershell
.\.venv\Scripts\python.exe -m axiom_forge --world <外部世界目录> --host-root <外部宿主目录> canon recover --bundle <外部世界目录>/.axiom/local/canon-reviews/<SHA256>/bundle.json
```

宿主验证原审查包、Artifact、批准 HMAC、提交父节点、完整 Git tree、批准消息和 Canon 版本。如果只有有效批准，会修复缺失事件并返回 approved，之后仍需单独 `canon apply`。拒绝只能恢复 rejected。若已有有效 prepared commit：分支缺失时，核对原 Git/Canon 基线后原子创建该分支；分支已指向同一提交时，仅补齐状态与日志，此时允许 main 已向前推进。分支指向其他提交、未批准、Key 丢失或内容被改动都会拒绝。重复恢复不重复批准、建分支或追加 CanonCommitted；重复 Apply 仍拒绝。不会 checkout、push、merge 或覆盖分支。

当前拒绝旧混合布局的签名审查包/准备提交，不自动迁移或重签；Schema 对旧结构样例的兼容不等于恢复授权。

## 存储与审计边界

```text
.axiom/local/tasks/<TSK>/
  created.json                 原始固定任务
  inputs/<ARN>.json            调用前保存的显式输入
  journal/00000001.json ...     原子追加 checkpoint + 同批事件
  operator.lock                OS 进程锁；退出后自动释放
  canon-retrieval.json          固定快照检索
  waiting/completed/rejected/committed.json
  failures/<ART>.json           每次失败的独立宿主回执
.axiom/local/runtime-runs/<ARN>/      原 Runtime 的输出、工具/请求引用和完成回执
.axiom/local/mode-runs/<RUN>/         首次与后续恢复的独立模式回执
.axiom/local/canon-reviews/<SHA>/     人工审查包、批准与准备提交
```

每个 checkpoint 使用 CKP-UUID，每个事件使用 EVT-UUID；保存完整、通过语义校验的 TaskState、生命周期、累计预留、调用游标和内容哈希。Lead、四类独立/交叉结果、草案、Red Team、最终综合都保留原 Artifact。草案对应 ANALYZING，随后 REDTEAM、SYNTHESIS、WAITING_APPROVAL、COMMITTED；拒绝另存终态，不重写待审文件。

事件包括 TaskCreated、RunStarted、ResearchStarted、AgentRunReserved/Completed/Failed、EvidenceAdded、RedTeamRaisedConflict、CanonChangeProposed、TaskInterrupted/Resumed/Completed、HumanApproved/Rejected、CanonPrepared/Committed、ArtifactRecovered、LifecycleChanged。没有新 Evidence 或冲突时不生成对应事件。EvidenceAdded 表示任务内暂存，不能当作 Canon 发布或科学事实认证；拟应用的提案取最终综合。

checkpoint 和其事件在同一个原子追加 JSON 中发布，带序号、前项哈希和状态哈希；读入拒绝断号、损坏内容、倒退生命周期或丢弃预留。跨锁读取的语义验证缓存只复用重新读取并逐字节哈希相同的已验证前缀，不信任文件时间或大小；持锁执行内复用本次已验证记录。同一任务的运行、恢复和审批/提交共享进程锁；不同任务独立。中断遗留的未发布 `.tmp` 不作为 checkpoint。

这些文件不是抵抗同一 OS 用户恶意改写的独立审计服务：拥有同等文件权限者可以重写整条哈希链或删除未被外部锚定的尾部。HMAC 仍依赖专用 Key 权限。单次文件上限为 2 MiB；超限停止，需要缩小任务，不偷偷截断证据。Workspace 刷新文件后原子发布，验收覆盖进程退出；未承诺所有硬件、网络盘或突然断电下的存储耐久性。请在受控本地磁盘保存完整 `.axiom/local`；它含私人研究资料，Git 默认忽略，不能自动当作共享备份上传。

尚未实现 Phase 12 LangGraph、并行岗位、循环修订、通用计算执行器、多用户服务和外部审计锚定。

## 离线验收

`tests/test_recovery.py` 使用真实子进程直接退出、实际 Runtime 文件和临时 Git 仓库；覆盖已完成岗位复用、输出/日志间隙、未知与失败调用的新 ID/累计预留、损坏与上下文变化、锁、终态复用、批准间隙，以及分支发布前后恢复。`examples/offline_recovery.py` 是仅限系统外临时 `axiom-forge-test-runs/` 下隔离仓库的中断测试夹具，不能用于正式任务。

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

2026-10-06 验收覆盖 **176 项不同离线用例，均取得通过结果**。全量 discovery 运行 175 项（765.920 秒），其中 173 项通过；两个新增夹具的工具授权/预算设置修正后定向复验通过。另新增运行期间规则变更保护用例，最终三项定向复验全部通过（41.914 秒）。没有遗留已知测试失败。41 个 Schema、7 个岗位契约、12 个模型登记、两个新增样例、编译、差异与敏感文件忽略检查均通过。正式 world 仍只有 world/world.json，正式审批 Key 未初始化，没有新增 API 调用或正式 Canon Apply。
