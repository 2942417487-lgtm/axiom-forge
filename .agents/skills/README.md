# 项目工程技能

本目录是 [mattpocock/skills](https://github.com/mattpocock/skills) 的项目内适配副本，使用 af-dev 前缀，与全局同名插件区分。仅处理 Axiom Forge 系统软件开发；适用范围、调用方式及任务跟踪见 [工程技能用法](../../docs/development/skills/README.md)。

## 调用

显式输入 `$af-dev-writing-for-agents` 或 `$af-dev-code-review` 等名称；有匹配描述的技能也可在软件任务中按需选用。上游要求用户显式调用的技能保留该限制，不自动运行整个工作流。

| 技能 | 入口 |
| --- | --- |
| af-dev-ask-matt | [SKILL.md](af-dev-ask-matt/SKILL.md) |
| af-dev-code-review | [SKILL.md](af-dev-code-review/SKILL.md) |
| af-dev-codebase-design | [SKILL.md](af-dev-codebase-design/SKILL.md) |
| af-dev-diagnosing-bugs | [SKILL.md](af-dev-diagnosing-bugs/SKILL.md) |
| af-dev-domain-modeling | [SKILL.md](af-dev-domain-modeling/SKILL.md) |
| af-dev-grill-me | [SKILL.md](af-dev-grill-me/SKILL.md) |
| af-dev-grill-with-docs | [SKILL.md](af-dev-grill-with-docs/SKILL.md) |
| af-dev-grilling | [SKILL.md](af-dev-grilling/SKILL.md) |
| af-dev-handoff | [SKILL.md](af-dev-handoff/SKILL.md) |
| af-dev-implement | [SKILL.md](af-dev-implement/SKILL.md) |
| af-dev-implement-spec | [SKILL.md](af-dev-implement-spec/SKILL.md) |
| af-dev-improve-codebase-architecture | [SKILL.md](af-dev-improve-codebase-architecture/SKILL.md) |
| af-dev-pr | [SKILL.md](af-dev-pr/SKILL.md) |
| af-dev-prototype | [SKILL.md](af-dev-prototype/SKILL.md) |
| af-dev-research | [SKILL.md](af-dev-research/SKILL.md) |
| af-dev-retro | [SKILL.md](af-dev-retro/SKILL.md) |
| af-dev-setup-matt-pocock-skills | [SKILL.md](af-dev-setup-matt-pocock-skills/SKILL.md) |
| af-dev-tdd | [SKILL.md](af-dev-tdd/SKILL.md) |
| af-dev-teach | [SKILL.md](af-dev-teach/SKILL.md) |
| af-dev-to-questionnaire | [SKILL.md](af-dev-to-questionnaire/SKILL.md) |
| af-dev-to-spec | [SKILL.md](af-dev-to-spec/SKILL.md) |
| af-dev-to-tickets | [SKILL.md](af-dev-to-tickets/SKILL.md) |
| af-dev-triage | [SKILL.md](af-dev-triage/SKILL.md) |
| af-dev-wait-what | [SKILL.md](af-dev-wait-what/SKILL.md) |
| af-dev-wayfinder | [SKILL.md](af-dev-wayfinder/SKILL.md) |
| af-dev-wizard | [SKILL.md](af-dev-wizard/SKILL.md) |
| af-dev-writing-for-agents | [SKILL.md](af-dev-writing-for-agents/SKILL.md) |

## 来源与维护

固定上游提交、许可证、上游／本地文件哈希及适配项见 [manifest.json](manifest.json)；MIT 许可全文见 [LICENSE.mattpocock](LICENSE.mattpocock)。项目复制工程和 productivity 发布目录；in-progress 与不相关 misc 专项脚本不在安装范围。

项目适配限于工程用途描述／提示、af-dev 名称及相互调用、开发文档路径与 Codex 调用策略。上游模板不自动执行，也未登记为研究计算程序。更新时审查固定版本与本地约束，不自动覆盖全局安装。

Codex 的项目技能发现及调用策略参考 [官方技能文档](https://learn.chatgpt.com/docs/build-skills)；仓库内采用 `.agents/skills/`，不会向研究 Adapter 注册这些技能。这些文字范围不是 OS 级隔离，实际权限仍由 Runtime、ToolSession、宿主及用户授权约束。
