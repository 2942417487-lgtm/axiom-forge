# Claude 系统开发入口

本文件位于产品之外，仅补充 Claude 的软件工程操作方式。先读根 AGENTS.md，再读 development/records/CURRENT.md 和当前任务，保留实际工作集并遵守测试、独立审查、秘密保护和人工 Git 控制。

产品运行使用 product/run.py；测试使用 development/check.py。工程技能位于根 .agents/skills/，用法见 development/records/skills/README.md。

研究岗位规则与只读 Claude 手工入口位于 product/resources/ 和 product/.claude/agents/；受控 Adapter 使用产品内部规则和宿主 ToolSession，不读取本文件，也不继承工程技能、审批或 Shell 权限。研究边界见 product/resources/policies/，具体使用见 product/docs/runtimes.md。
