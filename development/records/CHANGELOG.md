# 系统开发变更索引

集成记录由本地 Git 第一父链核对，日期沿用提交中的 +08:00 时间；验收细节按对应任务／历史记录读取，不能用合并状态代替功能或科学验收。

## 本地接续补记

2026-10-24：[分离遗漏修复](tasks/2026-10-24-separation-reaudit.md#后续修复与最终验证)，补齐 A1–A5：手工计算读取清单、实际研究指令、源仓库前置检查及现行文档；共享工具配置与共同规则收敛。当前 294 项分三组联跑，292 通过、2 项既有 Windows 链接权限跳过，无失败或缺失；两轴复核无剩余发现。工作集未提交。

2026-10-24：[分离后的遗漏与文件职责复审](tasks/2026-10-24-separation-reaudit.md)，359 个基线文件无整文件遗失；确认 3 处迁移覆盖遗漏和 2 类现行信息过时，另列职责重复候选。该阶段仅审查／记录，后续修复见上条。

2026-10-24：[产品／开发目录与规则作用域分离](tasks/2026-10-24-product-development-separation.md)，迁移到 product／development，系统版本 0.3.0，研究规则、资源路径与恢复指纹切换；组合验收与独立审查完成，尚未提交。完整 276 项与修正后定向 43 项分别记录，当前 282 项有通过结果，2 项既有链接权限跳过。

2026-10-24：[规则归属确认](tasks/rule-scope-separation.md)，用户确定现有 AGENTS.md／CLAUDE.md 放在外部开发侧，系统内部规则以后通过作用域分离另行补齐；本次只更新计划、总表与导航，尚未修改规则加载或移动文件。

2026-10-24：[任务清单补齐与遗漏复查](tasks/2026-10-24-task-inventory-audit.md)，新增 [TASKS.md](TASKS.md)，核对交接书、原始 Phase 0–15 和现行契约，并同步 PR #13 合并状态；本轮文档工作尚未提交。

2026-10-23：[宿主内容存储基础](tasks/2026-10-23-repository-content-store.md)，在当时未提交的回执基础之上完成类型／操作绑定、事务保存与复读及双轴审查；联合回归 96 项、审查修正后存储 27 项均通过。现成方案见[选型记录](tasks/2026-10-23-repository-content-store-research.md)。后随 PR #13 集成。

2026-10-23：[仓库宿主回执数据基础](tasks/2026-10-23-repository-receipt-foundations.md)，用户确认四类 Schema、标识、引用与链验证、测试及独立审查。原工作分支 `codex/repository-receipt-foundations`，基线 `401aa51`；后随 PR #13 集成，验收以任务实录为准。

2026-10-20：[开发日志接续核对](tasks/2026-10-20-handoff-audit.md)，补齐 PR #10–#12 的收尾状态与当前导航。原交付分支为 `codex/development-handoff-audit`，提交 `401aa51` 后随 PR #13 合入 main。

## 已集成索引

| 日期 | PR | 内容与记录 | 合并提交 |
| --- | --- | --- | --- |
| 2026-10-24 | [#13](https://github.com/2942417487-lgtm/axiom-forge/pull/13) | [回执数据基础与 SQLite 单份内容存储](tasks/2026-10-24-receipts-storage-pr.md)，包含 `401aa51` 开发日志接续补记；用户合并 | `43d4e7299206acca5011c3500a1f642c62a9b918` |
| 2026-10-20 | [#12](https://github.com/2942417487-lgtm/axiom-forge/pull/12) | [工程技能、集中开发日志与文档导航](tasks/2026-10-20-docs-and-skills.md)；[隐私复核与发布](tasks/2026-10-20-privacy-and-publish.md) | `a50e0cee3c37db1250e114ba3c94e9e3e3d9f136` |
| 2026-10-20 | [#11](https://github.com/2942417487-lgtm/axiom-forge/pull/11) | [项目元数据最小实现与宿主回执契约草案](tasks/project-metadata-implementation.md) | `5958e41ffd64c0d3c69b266e0061203df2fe25ac` |
| 2026-10-09 | [#10](https://github.com/2942417487-lgtm/axiom-forge/pull/10) | [标准世界 Git 主载体、目录与接续契约](tasks/world-portability-contract.md) | `ab4fe75728d2ea48a75cc227edf432fe0ff28563` |
| 2026-10-07 | [#9](https://github.com/2942417487-lgtm/axiom-forge/pull/9) | [系统／外部世界／宿主基础分离](tasks/separate-world-workspaces.md) | `61a0c87e503e46a47d4376f3241caaa4690747a2` |
| 2026-10-06 | [#8](https://github.com/2942417487-lgtm/axiom-forge/pull/8) | [持久化、事件与显式恢复](tasks/phase-11.md) | `ea418921317ae16e04fc4b265b1112bbfa8dc95a` |
| 2026-10-06 | [#7](https://github.com/2942417487-lgtm/axiom-forge/pull/7) | [任务运行与独立人工 Canon 宿主](tasks/phase-10.md) | `557f98f1dd1fba229edc15ad6d44546208089550` |
| 2026-10-06 | [#6](https://github.com/2942417487-lgtm/axiom-forge/pull/6) | [模型路由与四种工作模式](tasks/phase-7-9.md) | `620c8b29511b3cb93b2f750aa94c0271c4666e75` |
| 2026-10-06 | [#5](https://github.com/2942417487-lgtm/axiom-forge/pull/5) | [官方 SDK 单岗 Runtime](tasks/phase-6.md) | `ab881bdd7812f21d0ea34d89a38a599f40479d78` |
| 2026-10-04 | [#4](https://github.com/2942417487-lgtm/axiom-forge/pull/4) | [可信宿主本地工具层](tasks/phase-5.md) | `d7e8e29571c7500b269b59cd2d7369ba4e4735f8` |
| 2026-10-04 | [#3](https://github.com/2942417487-lgtm/axiom-forge/pull/3) | [岗位输入投影与输出契约](tasks/phase-4.md) | `2d17554c6e2bbbf63ab729153cbc577e0baa029b` |
| 2026-10-03 | [#2](https://github.com/2942417487-lgtm/axiom-forge/pull/2) | [数据、Evidence 与业务接口基础](tasks/phase-1-3.md) | `dce14228814bc25c6a7db1b41ecf205651753fc2` |
| 2026-10-03 | [#1](https://github.com/2942417487-lgtm/axiom-forge/pull/1) | [项目、安全与 Git 基础](history/phases/phase-0.md) | `95e30044e0cef217202a4bb1471e24161ab9dd16` |

PR #11 合入文档与元数据最小实现，PR #13 再集成回执数据基础及单份内容存储；完整宿主执行器仍待实施。PR #10 的 Git 载体方向继续有效。后续事项集中在 TASKS，CURRENT 仅保留接续重点。
