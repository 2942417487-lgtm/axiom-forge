# 工程技能与文档整理

日期：2026-10-20。整理阶段状态：本地整理、检查与双轴独立审查完成。当时尚未提交、发布或合并；后续用户已授权隐私检查、发布及合并，单独记录于 [隐私及发布任务](2026-10-20-privacy-and-publish.md)。以下保留整理阶段的实际记录。

## 请求与范围

用户要求接入 https://github.com/mattpocock/skills.git 的技能，仅用于 Axiom Forge 系统开发；随后使用适用技能优化项目文件及说明，将进度、历史开发和改动记录集中为跨窗口开发日志，让 README 专注使用说明。用户进一步选择：只整理文档与目录导航，保持功能及源码布局。

基线为 main／HEAD／origin/main 的 5958e41ffd64c0d3c69b266e0061203df2fe25ac，PR #11 已合并，开始时工作目录干净。工作分支为 codex/development-docs-and-skills。保留旧分支、worktree、.cache 接续材料和介绍规范 0 字节占位。

## 交付

- 项目内固定版本的工程技能、来源／许可证及本地适配清单；不改全局技能安装，不给研究 Runtime 增加技能或工具。
- docs/development/ 作为开发日志唯一入口，包含当前状态、变更索引、任务及历史记录；事实保留来源和实际验收范围。
- README 与模块 README 保留安装、命令、接口、目录及必要限制；历史结果和阶段叙述迁入开发日志，规范与设计文档继续承担契约职责。
- 更新所有受影响本地链接、Agent 接续指引及文档导航；不改源码、Schema、Runtime 配置或功能结构，不实施仓库回执功能。
- 文档／技能静态检查、系统边界检查及双轴独立审查；记录实际结果，不重复宣称付费模型或完整研究验收。

## 执行约束

按 skill-installer 安装流程读取用户指定上游；按 writing-for-agents 组织单一事实来源和按需读取，按 code-review 区分 Standards 与 Spec 审查。本地工程任务说明作为本次 spec，固定审查基线为 5958e41ffd64c0d3c69b266e0061203df2fe25ac。本地文件继续作为工程任务跟踪器；PR 发布和合并仍按用户单独授权。

开发日志是项目版本化的工程记忆，不是研究 Evidence、批准回执或可执行恢复记录，不写入全局 Codex Memory，不复制真实凭据或私人 .axiom/local。缓存原件继续保留，汇总状态必须与实际 Git／代码核对。

## 执行记录

- 已完整读取项目规则、技能安装器及适用写作／审查技能；核对当前目录、Git、worktree 和用户范围。
- 上游 main 经 GitHub 官方 API 固定为 5beb35b040e3de97e54fa9e386d7e42d15c295c2；技能及许可证内容在安装前静态检查，不执行其包安装脚本。
- 官方 skill-installer 将 engineering／productivity 两目录的 27 个技能下载到忽略缓存，再制作为 .agents/skills/af-dev-* 项目副本。保留 MIT 许可证及 79 个上游资源的原始／本地 SHA-256；适配仅涉及命名、用途提示、开发文档路径及显式调用策略。in-progress 和不相关 misc 专项技能不引入，全局插件不改。两个 Bash 模板只复制、静态读取，未执行或登记为研究程序。
- 使用项目内 af-dev-writing-for-agents 的单一事实来源、按需读取和去重原则：README 专注用法与限制；docs/guides 放操作指南，docs/contracts 放规范，docs/development 集中 CURRENT、CHANGELOG、任务和历史。31 份文档迁移记录见 migration-map.json；历史阶段和任务保留原验收语义，旧 README／指南／契约的执行说明另存历史，不改写成当前验收。
- CHANGELOG 按实际 Git 第一父链整理 PR #1–#11 的合并日期与提交；CURRENT 核对 PR #11 已合入、元数据实现范围和未实现项。没有把本轮草稿列为已集成版本，缓存原件未复制进 Git，也未写全局 Memory。
- 首轮只读检查修正历史片段迁移产生的 13 处相对链接，再复核 174 份文档／技能文件：363 个本地链接无断链，JSON／YAML、UTF-8／无 BOM、换行、尾空白及代码块检查通过；27 个技能、79 个来源哈希和 31 条迁移记录一致。所有原有非 Markdown 跟踪文件与基线逐字节相同，源码、Schema、Runtime 配置和测试没有改动。
- check-schemas（42 个及离线引用）、check-contracts（7 个岗位）、check-system-boundary 和 git diff --check 均退出 0；介绍规范在 docs/contracts/world-introduction-export.md 保持 0 字节。没有重新运行全套 unittest 或真实模型／世界流程，历史测试次数未当作本轮结果。
- AGENTS 及被信任的模块 Markdown 改变会改变现行资源指纹；旧 checkpoint 失配仍停止，不迁移、补签或修改恢复代码。这个限制已写入 CURRENT。

## 审查修正

Standards 首轮发现 1 处硬性冲突及 1 处命名判断项：上游 handoff 仍要求接续只放 OS 临时目录，部分 Skill tool 调用仍用原名。已改为持久交接／工程笔记归入当前开发任务，临时预览仅留忽略缓存；实际调用统一 af-dev 前缀，同时保留 research 任务类型等普通领域值及上游 URL 原样。问卷、架构结论与实现过程笔记也按相同规则归档，79 个原始来源哈希保留，本地哈希与适配清单已更新。

Spec 首轮指出路由 README 将尚未接入的自动评估／升级重派写成已有能力。已实际核对 modes.py 的 select 调用和全仓库无 escalate 调用方，明确区分固定流程／预算预留／操作者显式恢复与未实现的自动升级重派；未修改代码或夸大实现范围。

## Standards

最终复核：0 剩余 findings。先前的接续文档保存位置冲突、旧技能调用名均已修正。持久工程记录归入 docs/development/，临时预览与研究权限边界清楚；wayfinder 保留 research 领域类型，实际调用为 af-dev-research。本地 manifest 哈希一致，原始来源哈希保留。审查 Agent 全程只读，未运行测试、模板或申请权限。

## Spec

最终复核：原 1 项 P2 已修复，剩余 0 findings。路由说明准确区分模式仅选择模型、失败即停，自动评估／升级／重派未接入，TaskManager 已有固定编排、预算预留和显式恢复。交接／工程笔记归档、临时 HTML 留缓存及技能前缀适配符合本轮范围。审查 Agent 只读复核，未运行测试、申请权限或修改文件。

Standards：0 剩余问题；Spec：0 剩余问题。两轴分别报告，不以一轴通过抵消另一轴问题。

## 最终验证与交付边界

修正后复核 174 份文档／技能文件，全部本地链接有效；27 个技能、79 个资源哈希、31 条迁移记录一致。另逐一核对 22 份旧阶段／任务记录，除导航路径外文字保持原意；原有非 Markdown 文件逐字节不变。有限凭据模式、空值 .env.example、敏感／私人／缓存忽略规则及 Git 差异格式检查通过；有限模式不代表任意秘密均可识别。

42 个 Schema、7 个岗位契约及系统边界检查均已实际通过。没有运行上游 Bash 模板、全套业务 unittest、真实研究 API 或正式世界操作，没有读取真实凭据／审批 Key。缓存源材料及旧 worktree 保留，介绍规范仍为 0 字节。

本轮在 codex/development-docs-and-skills 留待复查，HEAD／main／origin/main 的集成基线仍为 5958e41ffd64c0d3c69b266e0061203df2fe25ac。新日志和技能为本地工作集，未提交之前不会随 clone 携带；没有自行发布、合并或开始仓库回执工程。收尾记录和历史导航更新后再次检查文档／技能工作集。
