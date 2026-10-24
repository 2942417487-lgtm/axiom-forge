# 仓库宿主回执、人工接受与完成判定（文档设计草案）

本文件维护行为与数据约束；实现范围、合入状态和工程验收统一见 [开发当前状态](../development/CURRENT.md)。规范、合成示例及未来验收条件不授予执行权限。

本文承接已通过用户复查的 [项目元数据契约](project-metadata-contract.md)、[主契约](world-portability-contract.md) 与 [Git 接续规范](world-git-sync.md)。标准世界 Git 仓库为主载体，同一项目跨机保留 project_id／world_id，本机 workspace_id、凭据、审批和恢复独立。仓库操作由可信宿主完成，不需要模型重写数据、生成 ImportAnalysis 或取得完整包。

## 1. 已核对能力及缺口

| 依据 | 可以支持的现状 | 不能推导的能力 |
| --- | --- | --- |
| [WorldWorkspace](../../axiom_forge/workspaces.py) | 外部普通 Git、路径／配置／本机绑定与核心知识检查 | 构造可能写入绑定，不是只读准备入口；没有产品项目登记、隔离接收和同步接受 |
| [git_host](../../axiom_forge/git_host.py) | 受控环境、配置／链接检查、禁用 hooks／部分外部驱动、超时与输出限制 | 接受可信调用者参数，不是研究命令白名单或 OS 沙箱；没有安全 clone／fetch／多资源更新事务 |
| [研究 git.inspect](../../axiom_forge/tools/git_read.py) | status、HEAD 及限定目录 unstaged diff | status 不列未跟踪文件，不足以证明整个目标干净；不能检查全部历史对象或更新世界 |
| [Workspace 存储](../../axiom_forge/tools/storage.py) | 严格 JSON、受限相对路径、链接拒绝、append-only 文件原子发布；单文件 2 MiB | 不保证 Git refs、index、工作树、登记与多个文件的跨资源原子性或断电耐久性 |
| [CanonHost](../../axiom_forge/canon_host.py)、[快照](../../axiom_forge/snapshots.py) | 人工 Canon 批准、精确基线、受批准的分支创建、核心知识版本 | CanonApproval 不等于仓库登记／同步接受；不是原生仓库取得／更新接口 |
| [TaskJournal](../../axiom_forge/journal.py)、[Phase 11](../guides/recovery.md) | 单任务进程锁、checkpoint／事件及显式恢复 | 单任务锁不覆盖项目整体同步；不能自动复用任务恢复或把旧执行状态跨机启用 |

特别缺口：CanonHost 在提交说明中写入完整批准 JSON，其中包含 mac_sha256。因此审批 metadata 可能进入 Git commit 对象，即使 .axiom/local 和审批文件被忽略。没有检查任何个人正式世界，不能据此宣称实际泄露；未来取得／共享检查必须覆盖这种对象，发现禁止共享的 MAC／批准状态即停止，不自动重写历史。本阶段不修改 CanonHost 或其恢复验证。

内容引用的小记录存储已选用 SQLite，见[本次真实检索与选型](../development/tasks/2026-10-23-repository-content-store-research.md)及[宿主存储接口](../guides/repository-content-store.md)。受限取得／对象读取、敏感预检、宿主人工验证、完整回执保存与跨资源并发控制仍须分别确定后端；内容存储的选型不替代这些后续检索与验收。

## 2. 操作、阶段与权限

拟议 requested_action 为 inspect、register 或 update：

- inspect：取得并检查已授权范围，交付比较／诊断，不登记或更新目标。
- register：检查原生仓库及元数据，经独立人工接受后建立本机登记／绑定；保留原生历史，不新建替代世界。
- update：取得明确候选，经比较和独立人工同步接受后，只处理干净且允许快进的目标；分叉／合并／迁移另行审查。

source 可以是用户选择的已有本地仓库，或宿主明确获准取得的远端候选。远端选择、网络权限、认证和准备范围来自可信宿主，不从项目 remote、模型结果、URL 或回执字段取得权限。本文不实现 GitHub 连接。

| 阶段 | 产物 | 允许的作用 |
| --- | --- | --- |
| 准备 | RepositoryPreparationReceipt | 固定选择／策略和私人准备上下文；不写目标绑定、不外发未检查材料 |
| 取得与校验 | RepositoryInspectionReceipt | 在受限准备中取得候选、核对实际对象／文件、身份、基线、差异和覆盖；不更新正式 refs／工作树 |
| 独立人工接受 | RepositoryAcceptanceReceipt | 操作者复查准确内容后，由可信宿主入口产生并验证；不等于执行已完成 |
| 登记／更新及核对 | RepositoryOperationReceipt | 如实记录实际副作用、结果与完成条件；失败／取消也使用此结果类型 |

这些名字是文档中的数据契约，不是可执行工具。模型、世界文件、历史档案、普通 JSON 或自报 issuer=trusted_host 均不能制造权限。许可必须由可信宿主保有的操作上下文、入口验证和策略决定；内容哈希只提供内容绑定。

## 3. 共同封套、引用与存放

所有回执的顶层恰为以下八项，全部必填；各类 payload 也恰为第 4–7 节对应表列字段，只有明确标出的值可为 null。字段名区分大小写，不接受隐藏默认值、别名或未知字段。UTF-8／无 BOM、严格 JSON、拒绝重复键及非有限数值，规则沿用项目元数据契约；诊断不回显秘密值。

| 字段 | 拟议类型／规则 |
| --- | --- |
| receipt_format_version | string，本文只定义精确值 "1.0"；未知版本停止执行 |
| receipt_kind | preparation／inspection／acceptance／operation_result |
| operation_id | RPO-UUID v4，由宿主为一次操作创建，不使用 TSK／RUN 或厂商 Session |
| receipt_id | RRC-UUID v4，每份不可变回执独立生成 |
| sequence | integer，1 至 9007199254740991；同操作严格连续递增，不能是 bool或浮点 |
| recorded_at | 带 UTC Z 的时间字符串，使用现行日期时间校验规则；时间不能证明先后授权或代替序号／内容身份 |
| predecessor | 首份为 null；其余为前一份 ReceiptRef，必须同 operation_id、sequence 减一 |
| payload | 对应阶段的 object，字段集合及语义见第 4–7 节 |

同一 operation_id 只对应一次固定捕获和决定：第一份必须是 sequence=1 的 preparation；inspection、acceptance、operation_result 各至多一份，按阶段顺序保存，operation_result 为终态，后面不得追加回执。合法链为 preparation → operation_result（早期停止）、preparation → inspection → operation_result，或 preparation → inspection → acceptance → operation_result（仅 register／update）。acceptance 必须引用本操作 eligible 的 inspection。重新捕获、比较或接受需新建 operation_id，并以 retry_of_operation_id 关联旧操作；不能在旧链中追加新决定来覆盖旧结果。

RPO／RRC 的格式分别为对应前缀加标准小写 UUID v4：8-4-4-4-12 个十六进制字符，版本位置为 4，variant 首字符为 8／9／a／b。不自动转换大小写、改名或复用 ID；数据基础接口支持 `new-id repository_operation`／`new-id repository_receipt`，见[校验用法](../guides/repository-receipt-validation.md)。

- ReceiptRef 恰为 receipt_id、sha256；前者为 RRC，后者是实际已保存回执字节的 64 位小写十六进制 SHA-256。读入还须核对原封套、操作和阶段，不能只看哈希。
- ContentRef 恰为 record_id、sha256；record_id 为无前缀小写 UUID v4，定位宿主私人内容记录，sha256 校验实际保存字节。其登记类型、operation_id、完整分块清单和可读权限由可信宿主核对，不从来源路径解析。
- GitCommitRef 恰为 object_format、commit_oid。object_format 为宿主明确支持的 sha1／sha256；OID 分别为 40／64 位小写十六进制，来自实际 Git。未知格式停止执行，不迁移对象格式。
- 回执不存自身哈希；引用或宿主私人清单记录原字节哈希。不得先用另一语言重新序列化再称与原回执相同。这里不新定义 Canon 哈希或 RFC 8785 profile。

拟议操作记录保存在外部可信宿主私人目录，例如 `<host>/repository-operations/<RPO>/`；绝对路径和认证映射仅由宿主掌握，不上传到项目 Git。世界 .axiom/local 及旧记录保留，回执链不是共享研究档案或可移植恢复包。

当前 ContentRef 存储在该操作目录的 `content.sqlite3`，原字节与类型／操作元数据同事务保存、独立连接复读。接口只保存单份不超过 2 MiB 的内容记录；回执链本身的持久发布、控制面、防重放及下述分块清单另行实现。

回执、比较、清单和诊断可能分块保存：ContentRef 指向完整分块根清单，根清单列出有序片段、字节校验、类型、总项数与读取范围。缺块、超限、损坏或未检查范围不能报完整；不把大型对象塞入单个 2 MiB 文件。限额及分块实现须由未来可信宿主策略明确启用。

原字节哈希和序列只能发现内容／关联不一致；同 OS 权限者可以改写未被外部锚定的记录。本文不承诺 OS 强隔离、远程身份认证或独立审计锚定。

## 4. 准备回执 payload

以下字段全部必填；可为 null 的位置明确列出。ContentRef 的被引用记录类型须由宿主登记验证，不能由模型填一个同名记录替代。

| 字段 | 内容／约束 |
| --- | --- |
| requested_action | inspect／register／update，来自操作者本次请求 |
| source_selection_ref | ContentRef：local／remote、宿主选定位置／仓库身份、所选 refs、请求精确提交（未知时明确 null）、local_revision／merged_revision 来源要求；不含认证地址 |
| target_selection_ref | 非空 ContentRef：所选目标位置、预期 project_id／world_id、本机 workspace_id、接受基线及目标协作 ref；inspect 可只有宿主选定的检查位置／边界，未有登记时上述身份、绑定、接受基线及协作 ref可明确 null并记录原因；未登记 register 目标也可明确 null未知项。update 全部须已知，不为补齐准备字段创建绑定 |
| host_context_ref | ContentRef：本机操作上下文及授权范围，由独立可信宿主控制面核对，数据本身不提供权限 |
| policy_ref | ContentRef：本次受信策略，包括取得、文件／网络、秘密、refs、资料覆盖及允许副作用 |
| engine_resources_ref | ContentRef：可信资源／校验契约版本和指纹；不加载世界提供的规则／Schema |
| limits_ref | ContentRef：字节、对象、时间、分块等已启用限额；缺少可用限额时不得取得或执行 |
| sensitive_preflight_ref | ContentRef：外发前实际方法／覆盖／未检查项；未到该阶段可为 null，null不代表无秘密或允许外发 |
| retry_of_operation_id | null或旧 RPO；只作来源关联，新操作必须重查输入／目标，不继承旧接受权 |

准备回执不声明来源真实、检查完成或目标已登记。只有宿主验证授权、策略和外发前条件后，才允许相应取得动作。登记／更新目标使用独立普通世界 Git；系统开发仓库的 worktree 许可不扩大为世界工作区许可。

远端新对象、metadata、响应和候选文件先留在受限准备范围。已有本地仓库只读选择范围内内容；不复制源 .git 配置／hooks／credential，不沿源文件路径寻找秘密、不读取审批 Key。登记前不能调用会自动建立绑定的现行 WorldWorkspace 构造器充当准备检查。

## 5. 校验回执 payload 与覆盖

| 字段 | 内容／约束 |
| --- | --- |
| preparation_ref | ReceiptRef，绑定本操作的有效准备回执 |
| source_capture_ref | ContentRef：实际仓库身份、GitCommitRef、所选 refs及对象集合、project／world 原件身份、元数据结果、有效核心知识版本／快照；未知部分明确列出 |
| target_before_ref | ContentRef：目标路径／登记／绑定、HEAD／协作 ref、index、工作树及冲突检测输入；无已登记目标也须记录目标位置检查，不能整体为 null |
| coverage_ref | ContentRef：下述实际覆盖与必要／可选范围，不以单个 complete=true 代替 |
| checks_ref | ContentRef：方法／可信版本、实际输入、结果及安全诊断；没有执行的方法不得记 passed |
| comparison_ref | ContentRef：完整安全差异、完整知识／Hard Canon 审查视图、关系变化和未解决项；单独摘要不能替代完整视图 |
| write_projection_ref | register／update 为 ContentRef，列预期 refs／文件／登记／绑定及保护范围；inspect 为 null，不生成隐含写计划 |
| merge_verification_ref | 需要 merged_revision 时为 ContentRef，绑定同一仓库与精确提交的真实合并依据；其余可为 null；分支名 main 或项目自报不证明已合并 |
| inspection_status | eligible／blocked／incomplete；仅 eligible 可以进入对应人工接受 |

### 5.1 必须逐类记录的覆盖

coverage 记录每类请求范围、实际取得／读取范围、缺失／排除／仅引用项、检查方法／版本及适用限制，区分：

1. Git 来源、精确提交、实际所选 refs、父关系、浅历史／过滤／对象缺失及未取得 refs。
2. 实际接收的全部对象、headers、metadata 和字节；与所登记 refs 闭包／现有基线对应，不仅遍历最新树或声明 refs。未登记额外对象／数据必须报告并按受信策略拒绝，不能转入正式目标后才检查。
3. 来源提交中的核心 world、项目元数据、完整项目文件和用户自建文件；工作树草稿与已提交内容分别捕获。
4. 文件路径、链接／重解析点、大小写或规范化碰撞、配置及执行入口，包含 hooks／filters／驱动和 .github 等输入文本。读取不授予执行或上传权。
5. LFS 指针与实际内容、普通附件、外部引用、权限受限资源、未获取媒体；仅有指针／URL不报字节已取得或可离线使用。
6. 边界内安全研究档案与本机未归档记录的覆盖区别；不复制 .axiom/local、厂商会话或可执行批准／恢复字段。
7. 敏感检查的实际对象／metadata／文件与未检查编码、容器／媒体范围；疑似秘密及禁止共享批准字段用安全位置／类别诊断，不输出原值、认证参数或可还原补丁。

安全必须覆盖实际收到的对象和 metadata，不能通过缩小所选 refs／清单规避。浅历史、缺失附件或只读摘要的已知局限必须显示：若属于请求的必要范围则 incomplete；若操作者明确选择仅外部引用等受限资料范围，可以在展示局限后接受该范围，但不能宣称完整接续／全远端备份。必要核心知识、身份与实际接收数据的安全门禁不能因这种范围选择而豁免。

CanonHost 提交说明中的批准 JSON／MAC 按禁止共享状态处理，即使目标机器的旧批准不能执行，也不成为可共享理由。停留在隔离准备，交用户处理；不自动改提交、裁剪历史、复制批准或 force push。回执只给安全对象定位，不复写该原文。

### 5.2 捕获与比较约束

- 同一来源提交的 project.json、world.json、核心知识及媒体／历史关联一致捕获。运行中变化、缺失或只读了一部分时停止；不能拼多个时点为一个基线。
- 元数据缺失／未知格式／身份冲突沿用元数据契约诊断；新 ID／迁移候选另审，不在校验中自动写入。历史 source_read 状态不升级为本次重新读取科学来源。
- target_before 必须区分 tracked 的暂存／未暂存差异、未跟踪文件、被忽略文件及计划写入路径占用。现行 git.inspect 的 status 不足以完成这项检查；不列忽略文件不代表没有冲突。
- 来源知识／Hard Canon、目标原基线和未接受候选有完整可审查关系。敏感 before 值隐藏并阻止接受，不为“完整 diff”回显秘密。
- register 可保留与身份一致的未提交文稿／知识候选，并明确登记的正式基线来自已检查提交；候选不成为已批准 Canon。若本机世界身份／项目身份被改、核心不可核对或目标未知，先停止。研究是否可运行另须满足现行 Git／知识基线要求。
- update 仅在目标身份相同、所选 ref关系允许快进、目标干净且没有未跟踪／忽略路径冲突、必要覆盖和安全门禁完成时 eligible。分叉、缺失、旧绑定或潜在覆盖先 blocked／incomplete，保留双方。

## 6. 独立人工接受 payload

| 字段 | 内容／约束 |
| --- | --- |
| inspection_ref | ReceiptRef，最新 eligible 校验回执，不能引用旧操作或非当前捕获 |
| acceptance_scope | register_baseline／sync_baseline，严格对应 requested_action；inspect 不产生接受回执 |
| decision | accepted／rejected，由独立人工宿主入口产生；模型和来源不能填写为执行许可 |
| review_view_ref | ContentRef，与 inspection 的 comparison_ref 同一完整审查投影 |
| source_capture_ref | 必须与 inspection 同一 ContentRef及源身份 |
| target_before_ref | 必须与 inspection 同一 ContentRef及当前目标基线 |
| coverage_ref | 必须与 inspection 同一 ContentRef，不能接受时删去局限或秘密项 |
| write_projection_ref | 必须与 inspection 同一非空 ContentRef |
| policy_ref | 与准备回执相同的有效策略；变化使原接受失效 |
| actor_ref | ContentRef，宿主本机操作者标识／入口记录，不存登录凭据，不证明远程身份 |
| host_verification_ref | ContentRef，由受信宿主控制面验证本次交互、上述全内容绑定、上下文和是否已使用；没有可用验证器时禁止执行 |

操作者必须能审阅完整内容／Hard Canon及差异、来源、覆盖、禁止项和影响，再明确接受这一份投影。打开项目、接受资料映射、CanonApproval、PR 通过或旧对话一句确认不能替代这个步骤。

host_verification_ref 不是一个“填 hash即可批准”的字段。验证器必须由外部受信策略启用，读真实宿主入口产生并保存在私人控制面的记录，核对操作／目标／内容／行为范围及防重复状态。数据文件、模型自报 profile／issuer、旧 HMAC 或来源签名不能注册验证器。**验证器、身份控制与耐久存储实现尚未选定／实现；缺少它们时即使 decision=accepted 也不能执行。** 不默认复用 Canon 审批 Key或它的 schema。

accepted 允许后续在所有门禁仍满足时执行明确登记／同步范围，不表示已完成；rejected 不写目标，保存拒绝结果，不自动删除已取得候选。同步接受建立已检查的当前知识基线，不证明科学主张正确、不执行旧批准，也不允许研究岗位绕过 Canon 变更流程。后续新 Canon 修改仍走独立 ProposedCanonChange／批准／Apply。

接受后来源捕获、目标／refs／index／工作树、策略、审查视图、覆盖或写投影任一变化均停止。重新捕获、比较与人工接受，不靠相同 ID、时间较新或旧接受文件继续写。

## 7. 结果 payload、状态与真实副作用

| 字段 | 内容／约束 |
| --- | --- |
| requested_action | 与准备回执一致 |
| inspection_ref | 有完成校验时为 ReceiptRef；早期失败可为 null，并记录未完成检查 |
| acceptance_ref | 实际人工接受／拒绝时为 ReceiptRef，否则 null；null不能支持登记／更新成功 |
| execution_intent_ref | 已可靠保存的写前意图为 ContentRef，即使尚未开始目标写入；未生成／未可靠保存时 null。是否尝试写入由 effects_ref 表达，不以有意图推导已写；无此有效记录不允许开始写 |
| before_ref | 实际写前／只读比较基线 ContentRef；未取得时 null及缺口诊断 |
| after_ref | 实际核对的结果 ContentRef；未知或未核对时 null，不用期望值填入 |
| effects_ref | ContentRef，分别列私人候选取得、目标 refs／HEAD、index、工作树、登记、本机绑定及其他实际修改；每类标 not_attempted／verified／unknown |
| preservation_ref | ContentRef，对已存在文件、未跟踪／忽略内容、私人状态及宿主配置的保护与实际核对；不能只凭命令退出码说原件未变 |
| saved_records_ref | ContentRef，列实际已保存／未完成记录、私人位置标识、字节身份、未发布临时文件及保留范围 |
| outcome | inspected／registered／updated／already_current／rejected／blocked／cancelled／failed／interrupted_unknown |
| diagnostics_ref | 有问题为 ContentRef，否则 null；含安全位置、类别、检查局限，不能携带秘密原值 |
| followup | none／needs_input／new_inspection／manual_reconcile；不是自动执行指令 |

saved_records_ref 记录此前实际保存的内容，不把当前结果回执自身字节哈希加入这个被引用清单，避免循环引用。当前结果的实际持久发布与字节身份由宿主外部登记和最终完成核对记录；保存失败时不得对外报告完整成功。

| outcome | 完成条件 |
| --- | --- |
| inspected | 请求范围的校验和可读交付已可靠保存；不登记、不更新，无接受也不冒称已经打开产品项目 |
| registered | 接受验证有效；原生仓库及知识基线符合投影，本机登记／workspace 持久保存并复读核对；来源 Git与已有文件／私人状态保留；不自动初始化审批 Key |
| updated | 接受与写前复核有效，目标精确提交／所选 ref、index／工作树、知识基线及登记结果均符合投影，保护与保存核对完成；不仅是取回成功或 HEAD已变 |
| already_current | 精确提交及所请求实际内容／覆盖与已经接受基线一致，经核对无需修改；没有现存有效接受不能以此完成首次登记或豁免新的资料接受 |
| rejected／blocked | 不尝试受拒绝或未获准的目标写入，分别记录决定或门禁原因；候选取得及私人保存仍如实列出 |
| cancelled | 按第 8 节停止，明确实际修改及保存情况；若曾写目标，不用该状态暗示所有变化撤回 |
| failed | 已确认失败点与目标实际影响；非目标取得／暂存的未知范围如实列出，不能推导原件未变；目标写入未知时必须改用 interrupted_unknown |
| interrupted_unknown | 命令超时／崩溃／保存缺口导致目标写入或结果不可确定；禁止自动重放接受、重试写入或回滚，交人工核对 |

任何不可确定的目标写入使整体 outcome 为 interrupted_unknown。必要的结果／保护／保存后置核对未完成时，不得报 registered／updated。已写完目标但回执保存失败也不能只在终端声称完整成功。

### 7.1 写入与核对顺序

1. 在宿主私人范围可靠保存准备／校验和完整审查投影，验证引用；不得写入目标 `.axiom/local` 来冒充准备完成。
2. 人工入口完成接受并可靠保存／验证决定。写前意图绑定精确 before、候选与期望 after、写路径／refs、已有私人保护范围和接受引用；保存失败则不开始写。
3. 协调世界写入及本机登记的锁，复核身份／路径／ref／index／工作树／忽略占用和策略。现行每 TSK锁不足以覆盖项目更新；外部非协作进程不被承诺隔离。
4. 只执行投影中允许的登记／快进更新；不 reset／clean／默认 rebase／新建合并、不触碰旧恢复／签名或偷偷覆盖路径。Git ref前值须条件验证，不能只靠早期检查；文件及登记另有写前保护。
5. 持锁复读实际提交／数据／绑定和保留项，保存真实 effects、after、结果，再标宿主控制面的操作完成。refs、工作树、多个文件、登记不承诺一个原子事务。

register 的新 workspace.json 仅可作为经审查投影的新本机绑定创建；不能覆写已有旧绑定或复制源绑定。审批 Key仍需现行独立显式初始化步骤；登记接受不自动创建、读取或授权它。

对于已确认完成且回执存在的操作，重复请求先验证该结果与当前状态，只读返回实际状态，不再次写。控制面缺失／被篡改、接受已使用或基线改变时停止；哈希文件本身不能提供防重放保证。

## 8. 失败、取消、保存与人工核对

| 时间点 | 必须报告和保护的事项 |
| --- | --- |
| 取得前取消／失败 | 已保存的准备／诊断和未完成读取；不能说检查完成，也不产生接受 |
| 已取得但未接受 | 列出私人候选／对象及保存范围，目标未尝试写；不外发未经检查内容，不自动删除原件或整个准备目录 |
| 接受后、写前取消／失败 | 保留决定和意图（若已保存），让控制面将操作停止且不可自动重放；输入／目标变化后重试要新操作／接受 |
| 写入中取消／崩溃／超时 | 安全停止后尽可能记录实际影响；未知为 interrupted_unknown，不能报全部取消或保证自动复原 |
| 写入完成、结果保存／复读失败 | 保留可验证记录；人工核对精确 refs／index／工作树／登记和意图，不能直接再次写 |

恢复是操作者显式发起的核对：读取真实记录、检查完整引用、策略和来源／目标，判断目标是 before、after、部分变化或另有用户编辑。未能确认则保留并交用户处理；任何修复写入都要独立可审查范围和有效新许可。本文不提供自动 resume、补签、目标回滚或重放旧接受接口，不套用 tasks resume／canon recover。

可能的备份／前状态只保存安全且明确需要的受影响数据，位于宿主私人范围，不复制整个 .axiom/local、源 .git或审批 Key。内容安全无法确认时先停止，不能为恢复而保存秘密副本或在 diff公开原值。未来实施需明确保护／暂存策略及耐久能力；本阶段不声称已满足跨资源事务或断电恢复。

安全诊断和隔离候选的保留／清理由操作者选择；取消不授权递归删除原件、旧缓存／私人持久记录。新操作关联旧 RPO仅用于追溯，重查输入、基线、范围和权限，不恢复厂商 Session／研究调用。

## 9. 合成片段与验收目标

以下为说明字段关系的片段，不是完整回执、实际哈希／提交或工具结果，不生成文件／注册接口。所有 ID及重复字符校验值均是合成夹具；真实值必须由宿主实际读取／计算。

### 9.1 GitCommitRef 形状片段

```json
{
  "object_format": "sha1",
  "commit_oid": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
}
```

### 9.2 无权限的“接受”负例片段

```json
{
  "decision": "accepted",
  "acceptance_scope": "sync_baseline",
  "inspection_ref": {
    "receipt_id": "RRC-11111111-1111-4111-8111-111111111111",
    "sha256": "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"
  },
  "host_verification_ref": null
}
```

该片段字段不完整、无可信人工入口验证；即使语法有效、声称 accepted，也必须拒绝执行，不能当作真正批准或有效 acceptance 回执。

### 9.3 中断结果片段

```json
{
  "outcome": "interrupted_unknown",
  "after_ref": null,
  "followup": "manual_reconcile"
}
```

这只说明不能确认 after 时的结果，不证明发生过真实写入，也不授权回滚／重试。

### 9.4 正反验收矩阵（未来实现条件，未运行）

| 编号 | 输入／事件 | 可核对结果及限制 |
| --- | --- | --- |
| H01 | 已有本地有效项目，requested_action=inspect | 保存检查／覆盖结果，不创建 workspace或登记，不称更新成功 |
| H02 | A 接续同一 PRJ／WLD，经完整检查及人工接受登记 | 保留共享身份／历史；新本机绑定，旧执行批准／checkpoint不启用 |
| H03 | 同路径既有有效登记、精确提交及请求内容／覆盖已一致 | 只读核对并返回 already_current；不是首次登记或新资料免审 |
| H04 | B 干净、同身份、允许快进且有真实已合并来源依据 | 比较完整差异／Hard Canon并验证同步接受后更新；后置核对全部条件后才 updated |
| H05 | 相同文件树但提交 OID不同 | 保留精确提交／历史差异，不只按树或展示标签报已一致 |
| H06 | 取得成功／检查 eligible，尚无人工接受 | 只能检查交付，不能登记／改正式 ref／工作树 |
| H07 | 负例片段、自报 issuer／哈希／profile或旧 CanonApproval | 不授予写权限，不注册验证器、不复用 Key或批准 |
| H08 | 操作者拒绝或写前取消 | 目标不尝试写，候选和已保存记录实际覆盖列明，不自动清理原件 |
| H09 | 接受后 target HEAD、ref、index、工作树、绑定或策略变化 | 停止；重新捕获／比较／接受，不复用旧决定 |
| H10 | 校验期间混入另一时点 project.json或world文件 | 拒绝伪基线，记录实际读取缺口，不模型补全 |
| H11 | 身份缺失／相同 PRJ不同WLD／旧绑定移动 | 元数据／绑定诊断，保留原件，不生成ID／重签来继续 |
| H12 | 暂存、未暂存或未跟踪文件会被覆盖 | blocked，列安全冲突位置，不 reset／clean／覆盖 |
| H13 | git status 看似干净，但被忽略路径已有目标写入占用 | blocked，保护该文件；status不是完整干净证明 |
| H14 | 本地分叉、独立提交或快进条件不满足 | 保留双方，交付另审方案，不默认 rebase／merge或丢弃提交 |
| H15 | 浅历史／过滤对象／缺失 refs／读取截断 | 列真实范围；必要范围未达则 incomplete，不自报完整历史 |
| H16 | LFS指针在，实际媒体／外部资源未取得 | 分别记录指针与字节；按请求必要性阻止或明确受限接受，不声称离线完整 |
| H17 | 只扫描最新树，收到额外对象／metadata未检查 | 不允许 eligible／接受；覆盖实际接收集合，不转入正式目标后再扫 |
| H18 | 历史提交说明含禁止共享 MAC／批准字段或假秘密 | inspection_status=blocked，诊断 blocked_sensitive；安全对象定位、不回显值，不改历史／force push |
| H19 | 来源 hooks／filters／脚本／世界AGENTS或Schema请求执行 | 不执行／不加载为规则，只作数据；权限未知停止相关动作 |
| H20 | refs已改变、工作树或登记只写了一部分，且中断后实际结果不可确定 | interrupted_unknown／manual_reconcile，不报 updated或自动回滚；实际影响已全部确认时按失败／取消规则报告 |
| H21 | 意图／接受保存失败或缺块／引用损坏 | 写前不开始；写后不能报完成，保留真实状态交人工核对 |
| H22 | 重复接受／旧操作被重放，控制面已使用或缺失 | 不重复写；验证已知完成结果或停止人工核对 |
| H23 | 更新时任务在运行、其他对话接受新知识 | 协调世界写入，原固定研究快照不漂移；旧批准失配停止，不重签 |
| H24 | 回执被放入世界Git或历史档案当作执行许可 | 不加载／恢复；共享历史视图另定，不复制私人控制面 |
| H25 | 分块／超限／编码未知或仅摘要可读 | 如实记录实际范围及未检查项，不截断后 complete或先外发再检查 |
| H26 | 操作完成后，新操作者编辑了目标再请求恢复旧操作 | 保留新编辑，停止旧计划重放；修复范围另审 |

## 10. 实现与权限边界

本设计约束宿主取得、检查、人工接受和完成判定，不产生真实回执或执行权限。四类 Schema、标识及离线数据／链校验用法见[回执数据校验](../guides/repository-receipt-validation.md)，单份内容记录接口见[宿主内容存储](../guides/repository-content-store.md)。宿主验证器、完整回执／控制面可靠保存、分块、执行后端和 H01–H26 产品验收仍待实现，准确进展见 [CURRENT](../development/CURRENT.md)。安全研究档案应承接实际覆盖、来源引用与回执去执行化；宿主后端、工具选型和保护／事务能力按独立工程范围推进，不因文档合入自动启动。
