# 系统开发变更索引

集成记录由本地 Git 第一父链核对，日期沿用提交中的 +08:00 时间；验收细节按对应任务／历史记录读取，不能用合并状态代替功能或科学验收。

## 本地接续补记

2026-10-20：[开发日志接续核对](tasks/2026-10-20-handoff-audit.md)，补齐 PR #10–#12 的收尾状态与当前导航。交付分支为 `codex/development-handoff-audit`，用户已授权提交并推送；尚未合入 main，不列为已集成变更，提交及同步状态以现场 Git 为准。

## 已集成索引

| 日期 | PR | 内容与记录 | 合并提交 |
| --- | --- | --- | --- |
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

PR #11 合入文档与元数据实现，不代表宿主回执已实现；PR #10 的 Git 载体方向继续有效。规则作用域分离计划及其他待实现项集中在 CURRENT，不在模块 README 累积里程碑。
