# 项目任务总表

核对日期：2026-10-24。集成基线：PR #13，`43d4e7299206acca5011c3500a1f642c62a9b918`。本表保存已找到的历史任务及后续事项，补齐此前遗漏的语言策略和产品化整体架构；来源覆盖与复查结果见[本轮记录](tasks/2026-10-24-task-inventory-audit.md)。当前正在执行的范围见 [CURRENT](CURRENT.md)。

状态按已交付能力填写：“已集成”只对应所述范围；“部分完成”列出已有基础与剩余工作；“待实施”表示已有方向或规范；“待决策”表示方案或范围尚需确定；“可选／延期”保留原计划强度。所有未执行项都是跟踪记录，实施前仍须取得具体范围授权。表内“下一步”不是新的执行指令。

## 已交付范围

| ID | 事项与当前成果 | 状态／依据 |
| --- | --- | --- |
| DONE-01 | Phase 0：系统仓库、隐私／忽略规则、分支与人工审查约定 | 已集成 PR #1；[阶段记录](history/phases/phase-0.md)。服务端强制保护另见 OPT-06 |
| DONE-02 | Phase 1–3：知识领域、状态／业务 ID、实体关系、Evidence、Schema 与固定 Canon Snapshot | 已集成 PR #2；[任务](tasks/phase-1-3.md)、[Evidence 契约](../../product/docs/contracts/evidence.md) |
| DONE-03 | Phase 4：七岗位、受限输入、独立首轮、后续审查／综合与输出校验 | 已集成 PR #3；[任务](tasks/phase-4.md) |
| DONE-04 | Phase 5：可信 ToolSession、本地读工具、任务内暂存与来源读取回执 | 已集成 PR #4；[任务](tasks/phase-5.md)、[工具](../../product/docs/tools.md)。通用搜索与计算执行器仍待实施 |
| DONE-05 | Phase 6：官方 SDK 单岗 Runtime、输入投影、输出校验／Artifact，Codex 限软件工程 | 已集成 PR #5；[任务](tasks/phase-6.md)。真实合成接入测试与离线研究验收分别记录 |
| DONE-06 | Phase 7–9：模型登记、宿主路由与有界升级选择接口、四模式协议及单次模式流程 | 已集成 PR #6；[任务](tasks/phase-7-9.md)。自动评估后重新派发见 RUN-02 |
| DONE-07 | Phase 10：Python TaskManager、固定快照、研究／审查流程、审查包及独立人工 Canon 批准／分支提交 | 已集成 PR #7；[任务](tasks/phase-10.md) |
| DONE-08 | Phase 11：原子 checkpoint／事件、预算预留、显式恢复及 Canon 恢复复验 | 已集成 PR #8；[任务](tasks/phase-11.md)、[恢复指南](../../product/docs/guides/recovery.md) |
| DONE-09 | 每个世界创建时即有独立本地 Git；EngineResources／WorldWorkspace／外部宿主分离，本机状态绑定 | 已集成 PR #9；[任务](tasks/separate-world-workspaces.md)。产品登记、GitHub 与迁移另列 |
| DONE-10 | 标准世界 Git 为主载体、目录／接续与导入分层规范；项目元数据和宿主回执的文档设计 | 文档已集成 PR #10–#11；[载体任务](tasks/world-portability-contract.md)、[元数据设计](tasks/project-metadata-contract.md)、[回执设计](tasks/repository-host-receipts.md) |
| DONE-11 | 四字段 project_metadata Schema、PRJ 标识与只读格式／world_id 检查 | 最小实现已集成 PR #11；[实施记录](tasks/project-metadata-implementation.md) |
| DONE-12 | 项目专用工程技能、集中开发日志、文档迁移／导航与隐私发布检查 | 已集成 PR #12；[整理任务](tasks/2026-10-20-docs-and-skills.md)、[发布记录](tasks/2026-10-20-privacy-and-publish.md) |
| DONE-13 | 开发日志接续补记 `401aa51`、四类回执 Schema／RPO／RRC／离线链验证、SQLite 单份原字节存储及复读 | 已集成 PR #13；[发布与合并记录](tasks/2026-10-24-receipts-storage-pr.md)、[回执实现](tasks/2026-10-23-repository-receipt-foundations.md)、[存储实现](tasks/2026-10-23-repository-content-store.md) |
| DONE-14 | SQLite 内容后端的真实检索、复用评估与选型 | 已完成并随 PR #13 集成；[选型记录](tasks/2026-10-23-repository-content-store-research.md)。后续其他宿主能力仍须各自选型 |
| DONE-15 | CalculationRequest／Result／Model 结构、研究岗位请求规则与可复用程序交付协议 | 规范基础已集成；[任务](tasks/reusable-calculations.md)、[计算协议](../../product/resources/calculations/README.md)。尚无通用执行器 |

PR、提交与完整历史入口见 [CHANGELOG](CHANGELOG.md)；各阶段历史测试按原批次保留，不相加成一次“全套通过”。

## 语言、规则与整体架构

| ID | 事项 | 当前状态与下一步 | 来源 |
| --- | --- | --- | --- |
| GOV-01 | **机器规则语言策略** | 待决策、未全量转换。明确执行层、岗位／模式 Markdown、机器标识与中文／多语言用户内容各自语言范围，再决定翻译和兼容验证 | H07 §2、§6；[覆盖记录](tasks/2026-10-24-task-inventory-audit.md#来源覆盖) |
| GOV-02 | 规则作用域分离 | 实现与遗漏修复已验证：外部 AGENTS.md／CLAUDE.md 归开发侧，内部规则实际加载及手工计算入口已补齐，共同规则已收敛；独立复核无剩余发现，未提交／集成 | [修复及复审](tasks/2026-10-24-separation-reaudit.md)、[实施](tasks/2026-10-24-product-development-separation.md)、[原计划](tasks/rule-scope-separation.md)。与 GOV-01 分别决策 |
| GOV-03 | **产品化整体架构** | 部分落地：产品／开发主目录已分离，源仓库边界检查和现行说明修复已验证，尚未集成。Domain／Tools／Runtime／Orchestration／Interaction 分层保留；TypeScript＋Rust＋Python 分工、跨语言协议、完整 UI／宿主产品、持久化和版本迁移仍待设计，技术栈未选定 | [本轮实施](tasks/2026-10-24-product-development-separation.md)、[遗漏修复](tasks/2026-10-24-separation-reaudit.md)；H07 §2、§6；原始设计总纲 §2、§13，见[来源覆盖](tasks/2026-10-24-task-inventory-audit.md#来源覆盖) |
| GOV-04 | 跨语言内容哈希兼容 | 待设计／验证。现行 Python canonical_bytes 保留；如引入 TS／Rust，单独验证键排序、数值／Unicode 序列化、语义哈希及版本迁移，不能把默认 stringify 当作同一算法 | [主契约 §13](../../product/docs/contracts/world-portability-contract.md#13-哈希与版本原则)、[元数据契约 §8](../../product/docs/contracts/project-metadata-contract.md#8-版本的独立含义) |

## 仓库宿主与接续执行

已有回执数据校验与单份 SQLite 内容存储。以下仍是宿主产品能力缺口，不能从 Schema 接受一份文件推导出真人批准或操作完成。

| ID | 事项 | 当前状态与下一步 | 来源 |
| --- | --- | --- | --- |
| HOST-01 | 分块内容与完整覆盖 | 待实施：分块根、完整有序清单、逐块绑定及最终覆盖验证，处理超限／缺块，不截断后宣称完整 | [回执契约 §3、§5](../../product/docs/contracts/repository-host-receipts.md) |
| HOST-02 | 完整回执／控制面耐久保存 | 部分完成：原字节内容已存；补回执发布、外部登记、跨记录一致性及崩溃后可判定结果 | [回执契约 §8](../../product/docs/contracts/repository-host-receipts.md#8-失败取消保存与人工核对)、[存储边界](../../product/docs/guides/repository-content-store.md) |
| HOST-03 | 独立宿主人工接受 | 待选型／实施：受信入口与身份验证、整份内容绑定、操作／目标／范围核对、防重放及耐久记录 | [回执契约 §6](../../product/docs/contracts/repository-host-receipts.md#6-独立人工接受-payload) |
| HOST-04 | 隔离取得与 Git 对象检查 | 待选型／实施：受限 clone／fetch／对象读取；检查全部实际收到的对象、历史、headers／metadata、自动执行入口与来源覆盖 | [Git 接续规范](../../product/docs/contracts/world-git-sync.md)、[回执契约 §5](../../product/docs/contracts/repository-host-receipts.md#5-校验回执-payload-与覆盖) |
| HOST-05 | 完整检查／人工审阅视图 | 待实施：同时展示源与目标知识、Git 基线／差异、项目身份、未提交内容、媒体／LFS／外部引用取得情况、排除项及冲突 | [回执契约 §5、§9](../../product/docs/contracts/repository-host-receipts.md) |
| HOST-06 | 本机项目登记／打开 | 部分完成：已有工作区与元数据只读检查；补本机登记表、显式世界／项目／路径绑定与重复／冲突处理，不串用执行状态 | [元数据契约 §7](../../product/docs/contracts/project-metadata-contract.md#7-本机登记与跨机重复处理)、[回执契约](../../product/docs/contracts/repository-host-receipts.md) |
| HOST-07 | 接受后的更新执行器 | 待实施：写前意图、跨资源锁／并发比较、明确允许的快进更新、写后核对；保留未提交／未跟踪／分叉内容和本机状态 | [回执契约 §7](../../product/docs/contracts/repository-host-receipts.md#7-结果-payload状态与真实副作用)、[Git 规范](../../product/docs/contracts/world-git-sync.md) |
| HOST-08 | 失败、取消与不确定结果处置 | 待实施：失败证据／拒绝结果持久化、中断恢复及未知副作用的人工核对，不覆盖用户分支或盲目重试 | [回执契约 §8](../../product/docs/contracts/repository-host-receipts.md#8-失败取消保存与人工核对) |
| HOST-09 | Canon 提交中的批准 metadata | 已知源码缺口：CanonHost 将包括 MAC 的完整批准 metadata 写入提交说明；跨机共享前需设计安全历史表示并验证，原批准仍独立保存 | [既有审计记录](tasks/2026-10-20-handoff-audit.md)。未检查或断言私人世界已经泄露，不自动重写历史 |
| HOST-10 | H01–H26 产品行为验收 | 待实施后逐项验收；当前离线结构／链测试不替代真实取得、人工接受、并发、执行及故障结果验证 | [完整矩阵](../../product/docs/contracts/repository-host-receipts.md#94-正反验收矩阵未来实现条件未运行) |
| HOST-11 | 其余宿主工具能力选型 | 后续各阶段先真实检索现成 MCP／skills，核对覆盖、兼容、维护、许可、依赖、权限与费用；仅对明确缺口自研。SQLite 选型只覆盖内容记录 | [项目规则](../../AGENTS.md)、[已完成选型](tasks/2026-10-23-repository-content-store-research.md) |

## 项目、资料、研究档案与协作产品

| ID | 事项 | 当前状态与下一步 | 来源 |
| --- | --- | --- | --- |
| DATA-01 | 项目与多对话身份 | 部分完成：PRJ／WLD 只读关联已实现；补 CNV／Conversation 机器格式、一项目一世界多对话、无世界的准备状态及后续显式绑定 | [元数据契约 §4–§6](../../product/docs/contracts/project-metadata-contract.md)、[目录规范 §2](../../product/docs/contracts/world-project-structure.md#2-项目逻辑布局) |
| DATA-02 | 项目元数据写入与版本 | 待实施：创建／更新 project.json、display_version 捕获／修改、格式兼容与迁移，保留项目展示版本／Canon 版本／Git 标识的不同含义 | [元数据契约 §8–§11](../../product/docs/contracts/project-metadata-contract.md) |
| DATA-03 | 安全研究档案生成 | 待设计／实施：选择并保存可共享内容、原文与工具结果出处、排除清单和只读映射；不复制 .axiom/local 的密钥、MAC、continuation、游标或恢复权限 | [目录规范 §2.1、§2.5](../../product/docs/contracts/world-project-structure.md)、[主契约](../../product/docs/contracts/world-portability-contract.md) |
| DATA-04 | 档案浏览、检索、引用与新任务 | 待实施：Conversation／Task 多对多关联、原文定位；从所选历史问题／资料启动新任务并绑定当前固定快照，旧档案不注册为可恢复调用 | [目录规范 §2.5](../../product/docs/contracts/world-project-structure.md#25-对话档案与任务档案) |
| DATA-05 | 文稿、计算与来源记录 | 待细化字段／接口：documents 作者文稿、问题／模型／参数／程序文本／结果的计算记录、Source 与 Evidence／正文关联；保留路径和原件身份 | [目录规范 §2](../../product/docs/contracts/world-project-structure.md#2-项目逻辑布局)、[主契约](../../product/docs/contracts/world-portability-contract.md) |
| DATA-06 | assumptions／audits／decisions | 部分完成：已有通用知识实体及目录用途；专用字段／工作流、与 Evidence／提案／Canon 的关联待设计。自动依赖重算尚未实现 | [目录规范 §2.4](../../product/docs/contracts/world-project-structure.md#24-假设审计决策与知识快照) |
| DATA-07 | 附件、媒体、LFS 与索引 | 待实施：assets／indexes、关系与外部引用、附件实际取得／缺失、分批读取与覆盖验证；用户安全自建文件也须保留 | [目录规范](../../product/docs/contracts/world-project-structure.md)、[主契约 §12](../../product/docs/contracts/world-portability-contract.md#12-文件安全媒体与工具边界) |
| DATA-08 | 输入敏感预检与安全副本 | 待实施：在任何模型 API／外部 OCR／转录前本地检查可检查范围，安全定位、暂停外发、列明未检查项；脱敏副本作为新输入复审，原件由用户控制 | [主契约 §11](../../product/docs/contracts/world-portability-contract.md#11-敏感内容检查与处置) |
| DATA-09 | 容器与不可信媒体处理 | 待设计／实施：路径／成员碰撞／链接／额外字节／资源耗尽检查；HTML 不自动执行脚本或外联，附件脚本不登记执行；与用户介绍 HTML 导出分别处理 | [主契约 §12](../../product/docs/contracts/world-portability-contract.md#12-文件安全媒体与工具边界) |
| DATA-10 | ImportAnalysis 与资料解析 | 待设计／实施：本地／在线／混合输入、来源定位、对象／模块映射、缺失／冲突／排除／候选差异及用户审查；先做工具选型，不由模型重写原生 Git 接续 | [主契约](../../product/docs/contracts/world-portability-contract.md) |
| DATA-11 | 接受分层与知识应用映射 | 待实施：输入接受、映射结果接受、仓库同步接受、Canon 批准分别绑定内容与基线；审查材料持久化，正文／附件／档案映射补齐，不能沿用旧批准 | [主契约 §10–§15](../../product/docs/contracts/world-portability-contract.md)、[回执契约](../../product/docs/contracts/repository-host-receipts.md) |
| DATA-12 | 世界 GitHub 产品接入 | 待选型／实施：显式选择 remote／认证、创建或连接世界仓库、上传内容／完整历史／自动执行检查、预览、分支／PR、自检与人工复查；与系统开发 origin 区分 | [Git 规范](../../product/docs/contracts/world-git-sync.md)、H07 §6、H09 §4，见[来源覆盖](tasks/2026-10-24-task-inventory-audit.md#来源覆盖) |
| DATA-13 | A／B 与多人仓库接续 | 方向已确认，产品未实现：A clone 后打开／登记／检查，B fetch 比较并接受明确合并版本；冲突与本地私有状态保留，依赖 HOST 系列 | [Git 规范](../../product/docs/contracts/world-git-sync.md) |
| DATA-14 | 显式工作区／格式迁移 | 待设计／实施：复制、移动、跨机及旧格式的显式映射与兼容处置；旧路径绑定、执行状态、审批与厂商 Session 不自动迁移或重签 | [工作区指南](../../product/docs/guides/world-workspaces.md)、[元数据契约](../../product/docs/contracts/project-metadata-contract.md) |
| DATA-15 | 介绍导出 MD／PDF／HTML | 方向已确认，详细规范与功能待实施；图文包含简介＋故事梗概、设定／角色／历史、逻辑链、计算原理与过程、版本号和日期；HTML 包含上述内容并支持动画／音视频／侧边栏跳转目录，各格式可含公共参考链接。媒体离线可用性／嵌入外链／隐私／播放与许可细节待定；现有规范仍为 0 字节占位 | H09 §4.1；[占位文件](../../product/docs/contracts/world-introduction-export.md)、[主契约 §2.1](../../product/docs/contracts/world-portability-contract.md#21-介绍文件规范占位) |

## 工具、计算与模型运行

| ID | 事项 | 当前状态与下一步 | 来源 |
| --- | --- | --- | --- |
| TOOL-01 | 通用 Web 搜索后端 | 接口基础已有、后端尚未启用；真实检索现成方案并核对许可、调用／隐私边界、费用与失败语义后接入 | [工具说明](../../product/docs/tools.md)、[Phase 5](tasks/phase-5.md) |
| TOOL-02 | 论文与专业数据库扩展 | Crossref／arXiv 基础已有；Semantic Scholar／NASA ADS／PubMed／IEEE 按领域需求可选接入，不视为全部必须部署 | 原始实施清单 Phase 5，见[来源覆盖](tasks/2026-10-24-task-inventory-audit.md#来源覆盖) |
| TOOL-03 | 工具运行治理 | 待实施：跨进程全局限流、缓存、重试退避与并发预算；分别验证真实后端行为与任务预算，不能只依赖单次进程配置 | [工具说明](../../product/docs/tools.md) |
| TOOL-04 | 跨 ToolSession 的可信读取回执 | 待设计／实施；与 Phase 11 已有 Artifact／任务恢复区分，新的 source_read Evidence 当前仍要求本 Session 真实读取暂存回执 | [工具说明](../../product/docs/tools.md) |
| CALC-01 | 通用计算执行器 | 待实施：统一请求入口、model_id／version 分派、宿主授权脚本与依赖检查、请求／结果身份和哈希、单位／边界／矩阵／情景覆盖／输出全集与语义验收、当前 AgentRun 绑定及 Artifact 核验 | [可复用计算任务](tasks/reusable-calculations.md)、[完整协议](../../product/resources/calculations/README.md) |
| CALC-02 | 可复用模型／程序库 | 待按问题构建并审查登记：参数化程序、模型适用条件、锁定依赖、边界测试、示例与结果来源。当前 Python 登记为空且默认关闭，Agent 生成代码不自动执行 | [计算协议](../../product/resources/calculations/README.md)、[工具说明](../../product/docs/tools.md) |
| CALC-03 | MATLAB Adapter | 已延期，后续按同一请求／结果协议与宿主权限接入；不影响当前离线协议使用 | [可复用计算任务](tasks/reusable-calculations.md) |
| RUN-01 | 候选模型与 Adapter | 已有启用模型的历史真实合成接入记录；Fable／Astra／DeepSeek 等未启用项及 DeepSeek Adapter 须先核对当时可用性、配额／费用与接入测试，不能由旧型号分工直接启用 | [Runtime 任务](tasks/phase-6.md)、[路由任务](tasks/phase-7-9.md)、[路由配置说明](../../product/resources/routing/README.md) |
| RUN-02 | 自动结果评估与升级重派 | 部分完成：已有 select／escalate；补不确定／分歧／未解信号的可信评估、预算内升级、重新派发及跨家族独立审查，不将模型 metadata 当授权 | [路由说明](../../product/resources/routing/README.md) |
| RUN-03 | 完整真实研究流程验收 | 待按具体研究题目、证据与额度明确范围后执行；历史真实合成模型接入和离线 TaskManager／模式验收保留各自结论 | [Runtime 记录](tasks/phase-6.md)、[Phase 10](tasks/phase-10.md)、[Phase 11](tasks/phase-11.md) |

## 原始 Phase 12–15 与产品工程

原始计划中的具体模型型号是当时的候选分工。能力与路由应由实际接入和 Eval 决定；当前实现状态按上表和现行代码／任务记录核对。

| ID | 事项 | 当前状态与下一步 | 来源 |
| --- | --- | --- | --- |
| PHASE-12 | LangGraph 编排 | 未实施。待既有契约稳定后设计 State／Routing／Parallelism／Retry／Loop／Checkpoint／Human Gate／失败恢复；节点复用统一 Runtime，不重写模型内部 agent loop；并行岗位和循环修订仍待实现 | 原始实施清单 Phase 12、设计总纲 §13；[现有恢复边界](../../product/docs/guides/recovery.md) |
| PHASE-13 | 软件工程需求交接工作流 | 部分完成：本仓库已有本地任务→开发→测试→独立审查→人工 PR 集成；研究系统提出软件需求后形成可审查 engineering issue 的产品交接仍待细化。廉价 coding worker／DeepSeek 为可选接入，依赖 RUN-01 | 原始实施清单 Phase 13；[工程任务约定](skills/issue-tracker.md) |
| PHASE-14 | 项目 Eval | 未实施：research／engineering／creativity／consistency／redteam／coding 六类；用真实历史任务构建 10–20 个以上 benchmark，记录事实准确、幻觉、反驳、数量级、工程／经济合理性、长上下文一致性、创意与不确定性，以及成本／tokens／latency，依据结果更新路由 | 原始实施清单 Phase 14；[历史路线图](history/readme-development-notes.md) |
| PHASE-15 | 成熟系统目标与动态路由 | 部分完成：角色／厂商解耦、追溯、恢复与人工控制已有基础；结合 Eval 动态选模、低成本优先／有界升级和高价值独立审查仍需集成验收。新模型通过 registry／eval／routing 接入，保持 Domain 稳定 | 原始实施清单 Phase 15；与 RUN-02／PHASE-14 联动 |
| PROD-01 | 产品交互与 UI | 待设计／实施：项目／多对话、知识／档案、资料候选审查、宿主接受与执行状态；前端方案由 GOV-03 决定 | H07／H09；[目录与协作规范](../../product/docs/contracts/world-project-structure.md) |
| PROD-02 | 安装／发行与可信资源布局 | 部分完成：product 源发行的 EngineResources／resources 布局及独立启动入口已建立；安装器、更新机制和旧任务兼容迁移仍待设计 | [工作区指南](../../product/docs/guides/world-workspaces.md)、[本轮实施](tasks/2026-10-24-product-development-separation.md) |
| PROD-03 | 大型世界与长历史性能 | 尚未验收。选择代表性世界／历史／媒体规模，测量路径检查与实体读取成本，再决定批量对象读取等优化；不是当前小规模功能的失败项 | [工作区指南](../../product/docs/guides/world-workspaces.md) |

## 可选、延期与覆盖说明

| ID | 事项 | 状态及触发条件 | 来源 |
| --- | --- | --- | --- |
| OPT-01 | 完整离线备份／迁移包 | 用户已推迟；未来可选。若启动，再设计容器／manifest／稳定 ID／自包含 Git 历史／附件／版本与覆盖。正常 clone／多人协作不依赖包 | [主契约](../../product/docs/contracts/world-portability-contract.md)、[Git 规范](../../product/docs/contracts/world-git-sync.md) |
| OPT-02 | 对外通用 MCP 包装／服务 | 现有本地工具与 SDK 内进程绑定已存在；公开通用服务未部署，未来有需求再选型／包装 | [历史说明](history/readme-development-notes.md)、[Phase 5](tasks/phase-5.md) |
| OPT-03 | 多用户服务 | 现有本机任务与人工宿主无该能力，后续产品需求确定后另立权限／并发／身份边界任务 | [恢复指南](../../product/docs/guides/recovery.md) |
| OPT-04 | OS 文件／网络隔离与远程身份认证 | 尚未实现，当前工具接口与 HMAC 属应用边界。若产品要求强隔离或远程操作者，另行设计与验收 | [工具边界](../../product/docs/tools.md)、[任务管理](../../product/docs/guides/task-management.md) |
| OPT-05 | 外部审计锚定 | 尚未实现；是否需要由部署与审计要求决定 | [恢复指南](../../product/docs/guides/recovery.md) |
| OPT-06 | 服务端分支保护／强制 CI | 工程约定已执行，服务端强制保护未配置；如要求平台强制门禁，单独实施并核验 | [历史 Git 说明](history/readme-development-notes.md) |
| OPT-07 | 手工 Claude 岗位文件加载补验 | 历史覆盖说明：`.claude/agents/` 手工加载未单独联调；受控 SDK 岗位加载／接入另有测试。需要该手工路径时再补验 | [历史记录](history/readme-development-notes.md) |

历史 Windows 符号链接跳过／补验按各任务原批次保留。测试覆盖条件不自动升级为新功能任务或强制硬件故障验收。已解决的权限、代理与测试夹具问题保留在过程记录，未重复列为当前待办。

## 维护方式

新增任务时分配本表 ID，附来源、状态和下一步；发现旧资料新增范围时先补来源覆盖，再确定是否属于当前授权。交付或合并后同时更新对应任务、CURRENT 和本表状态，保留原始验收批次。没有追溯来源的建议写明“本轮建议”，不混作用户既定要求。

本表覆盖本轮实际找到的资料，不声称恢复未保存在本地或可读聊天中的内容。被忽略交接书与外部原始计划的实质待办已归入表内，来源摘要及文件校验指纹保存在[复查记录](tasks/2026-10-24-task-inventory-audit.md#来源覆盖)，新窗口无需依赖这些私人路径才能找到任务。
