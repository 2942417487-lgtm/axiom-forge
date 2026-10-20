# 工程文档约定

系统为单仓库 Python 工程，保留 `axiom_forge/`、`schemas/`、`agents/`、`tools/`、`runtimes/` 等既有功能布局。工程技能只处理系统开发。

- 产品业务概念以 `docs/contracts/`、实际 Schema 和岗位契约为准；不从开发日志重新定义 Canon、Evidence 或审批含义。
- 使用说明放在模块 README 与 `docs/guides/`。
- 当前状态、开发任务、历史和变更索引统一放在 `docs/development/`。
- 如果任务确需新增工程术语，按需创建 `docs/development/GLOSSARY.md`；实际设计决策按需放入 `docs/development/decisions/`。不要为安装技能生成空白 glossary／ADR 或重复现有业务规范。

需要这些术语／决策时才读取对应文件；没有文件表示尚未建立，不补造已决定事项。正式世界的研究历史与事实不在这个工程目录内记录。
