# 分离后的遗漏、规则与文件职责复审

日期：2026-10-24。状态：复审发现的 A1–A5 已修复，重复配置与共同规则已收敛；最终回归及 Standards／Spec 独立复核完成，工作集交付分支审阅，尚未合并。

最终结果：基线 359 个受 Git 管理文件均有当前对应位置，没有整文件遗失。手工计算入口、实际加载的研究指令和源仓库检查三处遗漏已补齐；现行路径及能力说明已校准。当前全部 294 个测试 ID 分三组联跑，292 项通过、2 项既有 Windows 符号链接权限跳过，0 失败、0 缺失。两轴独立复核均无剩余发现。

原复审为只读阶段；随后用户要求“弄好了就继续刚刚的进度”，授权继续修复 A1–A5，并收敛工具配置装配与共同规则的重复维护。保留历史、样例、契约和暂未确认外部调用者的旧 diff 分支，未提交、推送或合并。修复及最终验证见本文末节；下文审查起点的计数与发现保留原批次含义。

用户要求重新加载 zh-work-expression，并审查相对刚合入 GitHub 的版本是否遗漏内容／功能，解释规则分离的具体改动，复核全项目中功能定位相似的冗余重复和过时文件。

## 范围与固定基线

GitHub 本次读取确认 main 仍为 PR #13 的合并提交 `43d4e7299206acca5011c3500a1f642c62a9b918`，PR #13 为 merged；本地 HEAD／main／origin/main 同为该提交。当前工作分支 `codex/product-development-separation` 的分离实现尚未提交，审查需包含 product／development 的未跟踪文件，不能把 Git 删除项直接判成文件遗失。

需求依据为[分离实施任务](2026-10-24-product-development-separation.md)、[规则作用域计划](rule-scope-separation.md)及本聊天本轮要求。比较使用 `git diff 43d4e7299206acca5011c3500a1f642c62a9b918 --`，并按[迁移清单](../layout-migration.json)逐项比较基线原文件和当前目标；基线之后的提交列表为空。

原复审阶段只审查与保存结论，不修改产品实现／规则。后续修复按开头所述授权执行；原有未提交实现与文档全部保留。

## 检查要求

- 覆盖基线全部受 Git 管理文件及迁移前的未提交文档；检查目标存在、内容差异、实际加载路径与行为，不只统计文件。
- 逐条追溯原 AGENTS.md／CLAUDE.md 的规则去向，区分开发、通用、研究、宿主和产品操作；检查加载与恢复指纹的实际代码。
- 全项目源码、产品资源／指南／规范、开发指引／记录、技能、模板、示例及测试按职责核查；相同字节／文本只作候选，结合调用与维护来源判断冗余。
- 区分现行错误与有明确时间范围的历史记录；缓存只核对目录角色／既有工程回执，不读取认证目录、真实凭据、私人世界或未知用户资料。
- 按 Standards／Spec 分别独立只读审查；结论给出文件位置、影响、当前证据和处理建议，未经验证的风险标为推断。

## 覆盖与文件保留

GitHub 本轮读取的 main 与 PR #13 合并提交一致。基线 359 文件中，270 个迁移到新路径，89 个保留原路径；228 个当前字节不变，131 个有内容变化。迁移表的 273 个目标还包括三份基线外的新增任务／清单文件，全部存在且审查起点哈希匹配。

迁移前工程备份共 11 份，含原十份未提交文档和分离任务草稿；均匹配清单 before_sha256，未发现丢失。源码／资源／文档／技能／示例／测试等 375 个项目候选文件已列入检查；本机依赖库、认证缓存和私人世界不作内容扫描。

33 份原 Python 产品模块中，23 份字节不变，10 份改动已按迁移对照检查。47 份 Schema、4 份路由 YAML、4 份依赖文件与基线字节一致。CanonHost、Git 宿主、TaskManager、Recovery、Modes、Snapshot、validation 与 OpenAI／Claude Adapter 本体保留。

## 原复审发现（修复前）

| ID | 优先级／来源 | 复审时问题与证据 | 影响与建议 |
| --- | --- | --- | --- |
| A1 | P2，分离新增 | product/.claude/agents/engineering-auditor.md:14、economic-auditor.md:16 仍指 schemas/、calculations/README.md；产品根下两旧路径不存在，实际为 resources/。两入口的允许读取清单也未纳入完整计算协议 | 同步手工入口到 resources/schemas/、resources/calculations/protocol.md，并明确允许读取；保留 Read 权限。受控 SDK 已加载新协议 |
| A2 | P2，分离新增 | product/axiom_forge/rules.py:9 停止加载岗位 README 后，“回答 planning_assignment、完成 required_checks，分工不能覆盖原问题”的要求只留在 resources/agents/README.md:3。实际组装四 Specialist 指令均无这两个字段 | 将必要研究行为迁入实际加载规则并增加指令覆盖检查；现有契约只验证分工身份／实体范围，不能证明回答完成了 required_checks |
| A3 | P2，分离新增 | product/axiom_forge/__main__.py:155–159 仍仅在 engine.root/.git 存在时检查跟踪文件；当前 engine.root 为 product/，.git 在父目录。实际 mock 检查返回 0，Git 检查调用为 0，仍输出无被跟踪私人状态 | 保留产品检查，在开发入口另补明确的源仓库检查；影响源仓库自检，独立世界与 Canon 防护仍保留 |
| A4 | P2，迁移路径未同步 | docs/runtimes.md:11、65 的依赖／示例定位，resources/modes/README.md:23 的 examples/mode-host.json，docs/guides/world-workspaces.md:76 的旧模板位置仍未更新 | 改为实际 dependencies／resources 路径，开发示例显式指向源码 development/examples，独立产品指南使用外部输入说明 |
| A5 | P2，基线已有、迁移保留 | docs/contracts/project-metadata-contract.md:19、world-portability-contract.md:214 仍笼统称回执验证／保存未实现；repository-host-receipts.md:13 又称研究 git.inspect 支持 diff | 按 PR #13 已有 Schema／链校验／SQLite 单份存储及仍缺的完整宿主执行能力分别写状态；研究 Session 实际拒绝 diff，规范应一致 |

上述路径均位于 product/ 下，A1–A3 为本次分离的功能／规则覆盖遗漏。另一个相同来源的文字遗漏是 Integrator 修订／撤回初稿、以最终 proposed_changes 为最终提案集合的说明仍仅在岗位 README:43；当前综合指令不含该条。应随 A2 一起核对必要协议，原输出引用校验仍保留，未用离线夹具推断真实模型已产生错误结论。

## 原分离改动及复审时缺口

| 对象 | 原方式 | 当前方式与适用范围 |
| --- | --- | --- |
| 外部开发入口 | AGENTS.md／CLAUDE.md 混合开发与研究要求 | 留在仓库根目录，负责开发任务、测试、工程技能、代码 review、Git 人工控制及中文沟通 |
| 共同可信原则 | 散在根总则与岗位说明中 | resources/policies/common.md：真实性、授权范围、原件保护、秘密、来源非指令、业务身份和宿主工具权限 |
| 研究规则 | 根 AGENTS＋岗位 README＋岗位正文，模式另加 | resources/policies/research.md＋岗位正文＋可选模式；保留科学分类、Evidence、实算／请求、固定快照、独立首轮、Red Team 与 pending 提案；A2 的详细要求仍待补齐 |
| 宿主／产品操作 | 与开发、岗位要求混放 | resources/policies/host.md 集中可信资源、SDK／ToolSession、人工批准、恢复、预算及产品接受分层。文件是规范，不表示新增了未实现的宿主能力 |
| 计算协议 | README 同时包含业务协议与操作者命令 | protocol.md 保存业务协议并由两 Auditor 的受控 Runtime 加载；README 保留操作检查，手工入口 A1 未完整同步 |
| 资源与恢复 | 引用旧根目录，指纹包含外部 AGENTS 与岗位 README | 改用产品内部资源，指纹覆盖 policies／protocol／岗位／模式／Schema／路由／登记；不含开发入口及操作者 README。系统 0.3.0 拒绝不兼容旧 checkpoint，未自动迁移、补签或改 Canon 哈希算法 |

## 冗余、过时与合理保留

| 分类 | 文件／范围 | 判断与处理建议 |
| --- | --- | --- |
| 可合并的实现重复 | product/axiom_forge/__main__.py:218–227 与 tools/host.py:13–24 | 两套配置白名单及网络／Python／Session 组装。已有 dict／bool 验证差异；优先让 CLI 复用 session_from_config，不维护第二份逻辑 |
| 可收敛的共性规则 | 七份 resources/agents/*.md 的共同边界与 policies；Claude 模板中的重复段 | 产品中有五组长段落重复，其中三组各出现七次。建议共性完整规则集中维护，岗位保留职责、引用与必要安全摘要；不机械删除安全要求 |
| 现行措辞过时 | 七岗位共同段的“未来 Apply”，部分 Claude 入口“Phase 5/6 后再接入” | CanonHost／受控 SDK 已存在；应明确“独立宿主已实现，研究岗位仍无权”及“手工入口仍只有 Read”，避免用旧阶段描述当前能力 |
| 旧分支清理候选 | product/axiom_forge/tools/git_read.py:11–17 | diff 分支保留旧系统目录白名单，当前唯一产品 Session 调用入口拒绝 diff。先确认外部直接调用者，再决定删除或重定范围；不得借清理放开研究 diff |
| 合理保留 | 岗位 JSON 契约、岗位 Markdown、Claude 入口 | 分别服务机器登记、业务指令、手工入口，使用者不同；本身不是三份无用重复文件 |
| 合理保留 | development/examples/agent_contract.json 与产品 lead.json | 417 字节完全相同，但前者由逐 Schema 样例测试读取，后者由产品契约登记读取；可用测试约束同步，不能仅按哈希删除 |
| 合理保留 | 介绍规范空占位与 tests/__init__.py 两个空文件 | 前者为用户保留的待设计规范，后者为测试包入口；零字节相同不表示职责重复 |
| 合理保留 | legacy-world、history、工程技能副本与调用别名 | 历史夹具有测试引用；历史目录明确时间范围；技能有固定来源、许可证和本地适配，别名有路由用途。可按使用情况再简化，不能据名称相近认定误复制 |

## Standards

独立只读审查发现 3 项 P2：Claude Auditor 路径／读取清单遗漏、现行指南旧定位、现行规范能力状态矛盾。对应 A1、A4、A5。另给出配置装配重复、共同规则维护与旧 diff 支路的判断性精简候选；没有删除或修复产品文件。

## Spec

独立只读审查发现 3 项 P2：手工计算入口漏迁、分工指令没有完整迁入实际研究加载、原源仓库跟踪文件检查被跳过。对应 A1、A2、A3。审批、Canon、快照、任务与恢复核心实现未见弱化，文件和迁移前修改的保留核对通过。

双轴各 3 项 P2，其中 A1 重合，合并为 5 个待修问题。本轮没有把上轮已关闭的 3 项发现重复算作新发现。

## 原只读复审的验证与交付

- GitHub main／PR #13 元数据已真实读取；359 个基线文件逐一查找，273 个迁移目标和 11 份明确工程备份核对通过。
- 实际调用指令组装函数，四 Specialist 的分工字段要求和 Integrator 的上述修订条款未进入指令；确认了 A2，不调用真实模型。
- 实际运行当前边界检查并记录 mock Git 调用数，确认 A3；没有扫描真实凭据内容或假设源仓库已经发生泄露。
- 本轮四项产品离线检查（47 Schema、7 契约、12 模型登记与产品边界）通过，但未检出这些遗漏。未重跑耗时全套，也不把前轮 282 项组合通过记录算成本轮验收。
- 只新增本记录并更新开发导航／任务状态和迁移元数据；产品代码、产品规则、开发测试及工程技能保持本轮审查起点字节。建议下一步先修 A1–A3，再校准 A4–A5，最后按职责收敛重复维护；不批量删除文件。

## 后续修复与最终验证

### 已修复问题与文件

以下改动叠加在原有未提交分离工作集上，Git 基线与分支保持本文前述值。迁移前后路径及内容哈希仍保存于[逐文件清单](../layout-migration.json)。

| 范围／类型 | 变更文件 | 具体变化与目的 |
| --- | --- | --- |
| A1，修改 | product/.claude/agents/ 下七份岗位入口 | 同步内部规则和岗位路径，区分手工 Read 入口与已实现的 SDK ToolSession；两 Auditor 的允许读取清单补齐计算协议及四份相关 Schema。保留原 YAML 工具／权限设置 |
| A2，修改 | product/resources/policies/research.md | 将 planning_assignment.question、required_checks、独立首轮与所选岗位条件、Integrator 修订／撤回及最终 proposed_changes 集合要求迁入实际加载的研究规则 |
| 共性规则，修改 | product/resources/agents/ 下七份岗位正文 | 保留各岗位职责、输入和输出，把长篇共同边界收敛为内部 common／research 规则引用及必要权限摘要；不重复维护“未来 Apply”等旧阶段描述 |
| A3，新增／修改 | development/source_boundary.py、development/check.py；product/axiom_forge/__main__.py | 开发入口先查明确的源仓库根及 Git 跟踪文件，再运行测试；禁止私人状态、秘密文件和正式 world 进入源码边界，检查失败即返回错误。增加 --boundary-only。产品命令如实只报告产品检查，不再把父目录 Git 检查跳过称为通过 |
| 配置重复，修改 | product/axiom_forge/__main__.py | CLI 复用 tools.host.session_from_config，与 Runtime 共用严格配置校验和 Session 组装；删除 CLI 第二套白名单／网络／Python 配置逻辑 |
| A4，修改 | product/docs/runtimes.md、product/resources/modes/README.md、product/docs/guides/world-workspaces.md | 改正 dependencies、resources 与模板路径；明确 development/examples 属源码开发资料，独立产品使用外部输入；区分源仓库和无需 .git 的独立产品资源 |
| A5，修改 | product/docs/contracts/project-metadata-contract.md、world-portability-contract.md、repository-host-receipts.md | 准确记录已有回执数据／链校验和 SQLite 单份内容存储，保留未实现宿主能力；研究 git.inspect 的说明改为 status／HEAD，明确拒绝 diff |
| 说明校准，修改 | product/README.md、development/README.md、product/docs/tools.md、product/resources/schemas/README.md、product/resources/agents/README.md、product/resources/calculations/README.md | 说明产品／源仓库检查分工、已实现 SDK 与手工 Read 入口、实际资源／示例位置；业务计算规则链接直达 protocol.md |
| 回归，新增 | development/tests/test_repair_scope.py | 10 项针对性用例覆盖源仓库检查和失败阻断、实际指令内容、手工协议读取清单、CLI 共享配置与非法配置拒绝 |
| 开发接续，修改 | 本记录、CURRENT.md、TASKS.md、CHANGELOG.md、原分离实施／规则计划记录及 layout-migration.json | 同步已修状态、当前验证批次和逐文件哈希；原历史任务与验收记录保留 |

### 最终验证批次

冻结本轮代码、内部规则和岗位入口后，把当前 discovery 的全部测试 ID 划分为互不重叠的三组。检查三组结果的并集恰好等于当前 294 个测试 ID，未遗漏或重复计算；这是三组完整覆盖的联合回归。

| 组 | 运行 | 通过 | 跳过 | 失败／错误 | 耗时 |
| --- | --- | --- | --- | --- | --- |
| 其他模块（含新增修复回归） | 242 | 241 | 1 | 0 | 173.216 秒 |
| 任务与项目模块 | 38 | 37 | 1 | 0 | 298.624 秒 |
| 恢复模块 | 14 | 14 | 0 | 0 | 177.625 秒 |
| 合计 | 294 | 292 | 2 | 0 | 各组分别记录 |

每组均先通过源仓库边界检查，检查到 359 个当前 index 路径。两项跳过为原有真实符号链接用例：tests.test_project_metadata.ProjectMetadataTests.test_linked_project_cannot_read_outside_selected_directory、tests.test_workspaces.WorkspaceTests.test_nested_git_ref_link_rejected_before_external_ref_write；当前 Windows 进程缺少创建符号链接权限（WinError 1314）。本轮未声称这两项取得执行通过结果。

复现完整套件使用 `.\.venv\Scripts\python.exe development/check.py -v`；单查源仓库使用 `.\.venv\Scripts\python.exe development/check.py --boundary-only`。本次三组启动器及各组结果保存在被忽略的 .cache/run-repair-suite.py、repair-*-tests.log、repair-*-results.json，汇总为 repair-verification-summary.json。

最终四项产品检查均通过：47 份 Schema 离线引用、7 个岗位契约／正文、12 个路由模型登记和产品边界。三组回归后只修改操作者文档与开发记录，未再改执行代码、内部 policies 或岗位入口。最终 .cache/check-separated-layout.py 检查 374 个候选文件、560 个本地链接、273 个迁移目标和 79 个技能文件哈希，0 错误；其中四处上游示意链接逐一核对为基线原文。格式、Python 编译、JSON、私密／临时路径忽略、空值 .env.example、介绍规范零字节及 git diff --check 均通过；暂存区为空。

### 独立复核及保留项

Standards 复核关闭原 A1、A4、A5，Spec 复核关闭原 A1、A2、A3。修复复核各追加 1 项 P3：Schema README 的内文定位、世界工作区资源表。两项已改正并分别复核关闭；最终两轴均为 0 项剩余发现。上轮分离审查的三项关闭结果仍按原批次保存。

保留旧 git_read.py 的底层 diff 分支，原因是外部直接调用者尚未确认；研究 ToolSession 继续拒绝 diff。岗位 JSON／Markdown／手工入口、测试样例／legacy-world、历史资料和本地适配技能各有不同读取者，均未按内容相同机械删除。未进行手工原生 Claude CLI 的真实联调，也未调用付费模型、操作正式世界或变更 Canon。

## PR 发布授权

用户于 2026-10-24 明确要求“推送PR”，授权提交当前已审查工作集、推送 codex/product-development-separation 并创建面向 main 的 PR；合并仍由用户决定。发布前复核全部候选文件、差异、忽略规则及隐私扫描，新增提交使用 GitHub noreply 邮箱；保留既有历史作者 metadata。历史只读／未提交阶段的记录按原时间范围保留。
