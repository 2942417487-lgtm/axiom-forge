# 文档导航

## 操作指南

| 用途 | 入口 |
| --- | --- |
| 安装、基本命令与目录 | [根 README](../README.md) |
| 创建／校验外部世界、快照和宿主路径 | [世界工作区](guides/world-workspaces.md) |
| 项目元数据的只读格式／身份检查 | [项目元数据检查](guides/project-metadata-check.md) |
| 研究任务、审查包、人工审批与 Canon 分支 | [任务管理](guides/task-management.md) |
| 检查事件、显式恢复研究或 Canon 提交 | [恢复](guides/recovery.md) |

## 模块接口

[业务 Schema](../schemas/README.md) · [研究岗位](../agents/README.md) · [工具](../tools/README.md) · [Runtime](../runtimes/README.md) · [路由](../routing/README.md) · [工作模式](../modes/README.md) · [计算协议](../calculations/README.md) · [合成示例](../examples/README.md) · [模板](../templates/README.md)

## 规范与设计

- [Evidence 与可靠性](contracts/evidence.md)
- [标准世界项目目录](contracts/world-project-structure.md)
- [项目接续与资料导入主契约](contracts/world-portability-contract.md)
- [Git 接续与协作](contracts/world-git-sync.md)
- [项目元数据、身份与版本](contracts/project-metadata-contract.md)
- [仓库宿主回执与人工接受](contracts/repository-host-receipts.md)

规范中的目标、示例和验收矩阵不表示对应功能已经实现。介绍导出详细规范仍为 [0 字节占位](contracts/world-introduction-export.md)，不是使用入口。

## 系统开发

[开发日志用法](development/README.md) · [当前状态](development/CURRENT.md) · [变更索引](development/CHANGELOG.md) · [工程技能](development/skills/README.md) · [历史阅读说明](development/history/README.md)

开发进度、测试与联调结果、变更经过统一在 development 中维护；规范维护行为约束，指南和模块 README 维护使用方法及必要限制。
