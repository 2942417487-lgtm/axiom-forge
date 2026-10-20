# 系统开发技能用法

项目技能位于 [.agents/skills](../../../.agents/skills/README.md)，使用 `af-dev-` 前缀。仅在本系统仓库的软件工程、工程文档与工程审查任务中使用；研究岗位及正式世界任务继续使用原有岗位契约与受控 ToolSession。

## 选择与调用

- 编辑工程文档或 Agent 指引：`$af-dev-writing-for-agents`。
- 评估源码模块接口：`$af-dev-codebase-design`；只有用户授权重构时才改源码。
- 调查软件缺陷：`$af-dev-diagnosing-bugs`；工程资料检索用 `$af-dev-research`，其笔记不是世界观 Evidence。
- 评审当前工作：`$af-dev-code-review`，分别审查 Standards 与 Spec。
- 生成开发接续说明：`$af-dev-handoff`，保存到本目录所属的开发日志范围。

其他技能及原名见 [项目技能清单](../../../.agents/skills/README.md)。项目副本与已存在的全局插件可同时可见；本项目优先明确选择 `af-dev-` 副本，避免重复执行同一流程。安装后的技能会在下一轮自动发现；当前轮可直接读取对应 SKILL.md 使用。

## 与项目约定的衔接

任务跟踪沿用 [本地任务文件](issue-tracker.md)，术语与设计记录按 [文档约定](domain.md)，状态词见 [任务分类](triage-labels.md)。这是对既有本地工作方式的整理，没有自动创建 GitHub Issue、label 或外部消息。

技能中的示范命令、分支发布、外部写入和手工脚本都须服从根目录 AGENTS 及当前用户授权。它们不授予审批、Canon 写入、Git 合并、凭据读取或真实模型调用权限。Bash 模板仅供审查和按任务改写，不原样执行示例中的凭据配置；需要凭据时使用外部宿主 Secret Store／.env，并由用户自行填写，不通过聊天收集。

未提交工作集的审查使用任务已经记录的固定基线：`git diff <基线> --` 加上明确的未跟踪文件清单；只有审查已提交分支时才使用上游的三点 diff。任务说明即本轮 spec，已核对的基线／需求不重复询问。code-review 仍分别派发只读 Standards／Spec 审查，不用空的 HEAD diff 冒充工作集审查。

上游 user-invoked 技能保留显式调用限制；其他技能仅在软件开发任务匹配时按需使用。这里只建立工程流程范围，不声称文档是 OS 沙箱；现有研究 Adapter 的 settings／skills 禁用及工具边界保持原实现，不向它们注册本目录。

## 更新

来源、固定提交、原始与本地哈希、适配项见 [.agents/skills/manifest.json](../../../.agents/skills/manifest.json)，MIT 许可证随副本保留。更新须重新核查上游，保留本地范围约束并审查差异，不自动跟随 main，不修改全局插件安装。
