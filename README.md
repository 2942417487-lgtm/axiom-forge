# Axiom Forge

硬科幻世界观研究、工程推演、事实验证与一致性审查系统。系统仓库保存软件、岗位规则、Schema、模板与合成测试资料；正式世界使用外部独立 Git 仓库。

## 安装

需要 Python 3.11+ 与主解释器中的 pip 22.3+。在仓库根目录建立隔离环境：

```powershell
python -m venv --without-pip .venv
python -m pip --python .venv install -r requirements-lock.txt
```

模型 SDK 按 [Runtime 说明](runtimes/README.md) 另装。需要凭据时，将 [.env.example](.env.example) 复制到系统与世界仓库之外的宿主路径，由用户自行填写；不提交、打印或发送真实值。

## 使用

```powershell
.\.venv\Scripts\python.exe -m axiom_forge --help
.\.venv\Scripts\python.exe -m axiom_forge check-schemas
.\.venv\Scripts\python.exe -m axiom_forge --world 'D:\AxiomWorlds\MyWorld' validate-world
.\.venv\Scripts\python.exe -m axiom_forge validate project_metadata examples/project_metadata.json
.\.venv\Scripts\python.exe -m axiom_forge --world 'D:\AxiomWorlds\MyWorld' project check
```

示例目录由操作者替换。先用 `world create --path <外部空目录> --name <名称>` 创建新世界；全局参数 `--world`、`--engine-root`、`--host-root` 放在子命令之前。旧 `--repo` 不再使用，从其他目录启动时须保证 axiom_forge 可导入。

| 目的 | 使用说明 |
| --- | --- |
| 创建／校验世界与固定快照 | [世界工作区](docs/guides/world-workspaces.md) |
| 检查项目元数据 | [只读检查](docs/guides/project-metadata-check.md) |
| 校验仓库回执格式与数据链 | [回执数据校验](docs/guides/repository-receipt-validation.md) |
| 保存宿主操作的内容引用 | [宿主内容存储](docs/guides/repository-content-store.md) |
| 运行研究任务与人工 Canon 审批 | [任务管理](docs/guides/task-management.md) |
| 检查日志并显式恢复 | [恢复指南](docs/guides/recovery.md) |
| 岗位输入输出、工具、SDK、路由与模式 | [文档导航](docs/README.md) |

结构检查不证明科学结论正确，也不授予模型调用、审批或发布权限。真实调用需要操作者明确选择宿主配置、凭据、预算及 `--allow-live`。`examples/` 为合成测试资料，不导入正式世界。

## 目录导航

| 目录 | 职责 |
| --- | --- |
| axiom_forge/ | CLI、数据校验、快照、工具、Runtime、任务和宿主实现 |
| schemas/、agents/ | 机器契约与厂商无关研究岗位 |
| tools/、runtimes/、routing/、modes/、calculations/ | 各模块用法、配置及必要限制 |
| templates/、examples/、tests/ | 模板、合成示例及验证 |
| docs/guides/、docs/contracts/ | 操作指南与设计规范 |
| docs/development/ | 系统开发日志、任务、历史与跨窗口接续 |
| .agents/skills/ | 本项目工程专用技能，不向研究 Runtime 注册 |

## 开发与验证

开发前阅读 [AGENTS.md](AGENTS.md)，从 [开发日志入口](docs/development/README.md) 接续；[CLAUDE.md](CLAUDE.md) 补充 Claude 操作方式。现状与历史只在开发日志维护，README 负责使用说明。

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe -m axiom_forge check-system-boundary
git diff --check
git status --short --branch
```

重要变更使用工作分支，经验证、独立审查及用户明确通过后合并。系统软件 PR 与外部世界的 Canon 审批属于不同流程；发布、合并及正式世界操作均遵守当前用户授权。
