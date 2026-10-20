# 系统开发当前状态

核对日期：2026-10-20。本文件是开发接续摘要；启动时仍须核对现场 Git 和用户消息，不把它当作自动执行授权。

## 本轮起始基线与交付

- 本轮起始集成基线：PR #11，`5958e41ffd64c0d3c69b266e0061203df2fe25ac`；最新集成状态另核对现场 Git 第一父链与对应 PR。
- 本轮交付：[工程技能与文档整理](tasks/2026-10-20-docs-and-skills.md)，分支 `codex/development-docs-and-skills`，本地整理及双轴独立审查完成。仅整理文档／目录导航，源码、Schema、Runtime 与功能布局保持。
- 用户随后明确授权隐私检查、推送 PR、远端复核后合并，并确认本次按 PR 范围处理、保留既有历史作者信息，新提交使用 GitHub noreply。检查与发布记录见 [隐私及发布任务](tasks/2026-10-20-privacy-and-publish.md)；不把本文件中的授权摘要当作未来任务的自动授权。
- 原 `codex/project-metadata-contract` 分支保留在 `75daed57caef3d2fea7e0a59f0a6096b64de6368`，旧 worktree 与被忽略接续缓存保留；不为对齐记录 reset／clean。

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
| 工程技能／开发接续 | 本轮接入项目专用 af-dev 技能与集中开发日志，不向研究 Runtime 注册 | [本轮任务](tasks/2026-10-20-docs-and-skills.md)、[技能用法](skills/README.md) |

模型真实合成接入测试与研究流程离线验收分别记录，均不等于完整真实科学研究已验收。手工 Claude 岗位加载不等于受控 SDK 工具授权。

## 未完成与已知缺口

1. [仓库宿主回执](../contracts/repository-host-receipts.md) 为已合入的设计草案；完整 Schema／链校验、宿主验证、可靠保存、登记／接受／更新执行器尚未实现。合入文档不代表回执已可执行。
2. 安全研究档案、Conversation／ImportAnalysis、敏感预检、附件／索引、GitHub 产品接续、导入／介绍导出尚未实现；标准 Git 世界仓库仍为首版主载体，完整包是未来可选离线备份。
3. CanonHost 当前将完整批准 metadata（包括 MAC）写入 Git 提交说明，跨机共享前需单独处理。仅核对源码发现此缺口，未扫描或断言个人世界已有泄露，未修改提交或重写历史。
4. 通用搜索后端、计算执行器、MATLAB Adapter、Eval、UI 和 Phase 12 未实现；Python 程序登记为空、默认关闭。
5. [规则作用域分离计划](tasks/rule-scope-separation.md) 未实施。本轮只限定工程技能用途及接续指引，不改研究规则加载、权限或恢复协议。

## 最近验收记录

PR #11 的新增 20 项测试均已取得通过结果，其中真实符号链接用例在 2026-10-18 由 Windows 管理员进程单独补验，0 跳过。结合首轮全套与失败项修正复验，218 项中 217 项有通过记录，1 项旧符号链接测试仍保留该轮跳过记录；不是第二次完整 discovery 全通过。详见 [实施记录](tasks/project-metadata-implementation.md)。

本轮文档／技能检查与独立审查结果写入 [当前任务](tasks/2026-10-20-docs-and-skills.md)，不能沿用上述测试次数当成本轮执行结果。研究工具、付费模型和正式世界操作均未因此新增授权。

## 接续注意

AGENTS、研究模块 README 或模式说明属于现行可信资源指纹范围。即使本轮只改说明和链接，也会改变相关字节哈希；旧 checkpoint 失配仍停止，不自动迁移或补签。本轮保持源码与校验协议不变。

本轮交付后的下一候选仍为仓库宿主回执基础实现，须按后续授权开展。介绍规范保持 0 字节，缓存不会自动随 clone 或新 worktree 携带；开发日志与工程技能作为版本化文件随 Git 接续。
