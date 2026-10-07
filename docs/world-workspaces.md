# 系统与世界观工作区分离

本轮采用方案 A：每个世界观创建时就建立独立本地 Git 仓库。系统开发仓库保存代码、Schema、岗位/模式规则、模板和合成测试资料；正式世界内容、研究输出与 Canon 分支属于对应的外部世界仓库。

## 三个路径与职责

| 路径 | 内容 | Git 管理 |
| --- | --- | --- |
| 系统资源根目录 | axiom_forge、schemas、agents、modes、routing、已审核程序登记、templates | 系统自己的开发分支与 PR |
| 外部世界根目录 | world/world.json、Canon、Evidence、时间线、决策、快照 | 世界自己的 main 与 canon/... 分支 |
| 外部宿主配置目录 | 运行配置、API 凭据、工作区专用审批 Key | 不进入上述两个仓库 |

世界目录与系统目录不能互相包含，也不能嵌套在其他 Git 仓库中。当前仅支持拥有独立 `.git/` 的普通本地仓库，拒绝 linked worktree、共享对象目录、Git 内部链接/重解析点、配置 include、filter、外部 merge/diff driver 与 worktree 配置。系统开发本身仍可使用 Codex 的 Git worktree。

EngineResources 默认定位当前源码发行的资源目录；可信宿主可显式指定 `--engine-root`。安装包资源布局尚未实现。大型世界与长 Git 历史的性能尚未验收；当前每次 Git 命令检查完整 Git 内部路径，后续应评估批量对象读取。世界目录中的 AGENTS.md、岗位文件、模式规则、Schema 或程序登记不会成为执行规则。显式运行配置与凭据路径也必须位于系统和世界目录之外；外部路径本身仍需由可信操作者选择。

## 创建与检查

以下是操作示例，需要将路径替换为自己的外部空目录。本轮验收只使用临时合成世界，没有创建个人正式世界或审批 Key。

```powershell
$worldPath = 'D:\AxiomWorlds\MyWorld'
$hostPath = 'D:\AxiomHost'
python -m axiom_forge --host-root $hostPath world create --path $worldPath --name '我的世界'
python -m axiom_forge --world $worldPath --host-root $hostPath world check
python -m axiom_forge --world $worldPath --host-root $hostPath validate-world
python -m axiom_forge --world $worldPath --host-root $hostPath snapshot create
python -m axiom_forge check-system-boundary
```

创建会生成新的 world_id、有效空知识库、初始快照、忽略规则和独立 main 基线。可用 `--author-name`、`--author-email` 设置该世界的本地 Git 作者；默认使用 Axiom Forge 的本地占位身份。没有 remote、GitHub 连接或自动批准。非空目标会被拒绝；Git 初始化失败时保留已写文件并报告错误，不覆盖重试、不宣称创建成功。

所有世界操作必须显式传入 `--world`；不会按当前目录猜测目标。全局参数位于子命令之前。旧 `--repo` 混合布局入口明确报错。

## 持久化与身份绑定

```text
<外部世界>/
  .git/
  .gitignore
  world/                       可提交的知识数据
  .axiom/local/                被 Git 忽略的持久执行状态
    workspace.json
    tasks/<TSK>/
    runtime-runs/<ARN>/
    mode-runs/<RUN>/
    tool-runs/<ARN>/
    canon-reviews/<SHA>/
```

`.axiom/local/` 是恢复所需状态，不应当作为普通缓存清理。它含研究输入、输出、工具回执、计算请求、费用预留和审批记录；备份时需按私人资料处理，默认不随世界 Git 共享。可提交的 world 数据与这部分本机状态具有不同用途。

workspace.json 记录 world_id、随机 workspace_id、规范绝对路径哈希和布局版本。任务、Runtime 回执、审查包与 checkpoint 绑定该工作区；审批签名同时覆盖包内容。即使两个目录具有相同 world_id 和 Git HEAD，也不能串用任务、审批或恢复。复制、移动工作区后拒绝沿用旧绑定；显式迁移工具尚未实现，不能通过手改描述文件续用旧审批。

研究恢复还核对系统版本、资源/契约/Schema/路由/程序登记哈希、配置、快照和 Artifact。当前系统版本为 0.2.0；兼容迁移尚未提供。系统版本与世界 Canon 内容版本分别保存。

宿主配置默认位于 Windows `%LOCALAPPDATA%\AxiomForge\host`，其他平台为 `~/.axiom-forge/host`；可用 `--host-root` 指定。首次显式 `canon init-approval` 才生成 `<host>/world-approvals/<工作区绑定哈希>/.env.approval`。研究工具不能调用批准或读取审批 Key。

这些检查属于应用边界，不能隔离拥有相同 OS 权限的任意进程，也不能代替 Secret Store、操作系统权限或远程身份认证。

## 审批与恢复

Phase 10–11 的岗位独立性、Evidence 暂存、预算预留和人工审批流程继续使用。命令必须选择外部世界；运行配置、凭据保存在外部宿主目录。

```powershell
python -m axiom_forge --world $worldPath --host-root $hostPath tasks run --question-file '<问题.txt>' --mode court --config '<外部宿主配置.json>' --credentials '<外部.env>' --allow-live
python -m axiom_forge --world $worldPath --host-root $hostPath tasks inspect --task-id '<TSK-UUID>'
python -m axiom_forge --world $worldPath --host-root $hostPath tasks resume --task-id '<TSK-UUID>' --config '<原外部配置.json>' --credentials '<外部.env>' --allow-live
python -m axiom_forge --world $worldPath --host-root $hostPath canon init-approval
python -m axiom_forge --world $worldPath --host-root $hostPath canon approve --bundle '<世界目录>/.axiom/local/canon-reviews/<SHA>/bundle.json' --reviewer '<姓名>'
python -m axiom_forge --world $worldPath --host-root $hostPath canon apply --bundle '<世界目录>/.axiom/local/canon-reviews/<SHA>/bundle.json'
```

`--allow-live` 允许可能计费的模型调用，离线测试没有这项授权。终态任务恢复无需模型配置或 live 开关。Approve 仍要求交互确认完整内容哈希；Apply/Recover 只在世界 Git 中创建经批准的 Canon 分支，不 checkout、push、merge，也不修改系统 Git。

旧混合布局的 `.cache/tasks`、Runtime 记录与旧审查包保留原文件，但不自动搬移、重签或恢复。Schema 保留旧静态样例的结构验证，不等于旧状态可执行。原先空 world 脚手架已保存在 templates/legacy-world/world，Git 历史没有重写；新世界使用 templates/world/world.json 生成新身份。

## 后续范围

世界 GitHub remote 配置、发布操作、标准导出包与重新导入映射、多机迁移、UI 与安装包属于后续独立工作。本轮只建立这些能力所需的系统/世界/宿主边界，不把目录复制称为标准导出或自动导入。

## 验证记录

2026-10-07：全量 discovery 运行 197 项（532.791 秒），193 项通过，3 项工具夹具仍使用旧路径/目录假设而失败，1 项因 Windows 缺少创建符号链接权限跳过。修正夹具后，完整工具模块 36 项复验通过（50.408 秒）；业务实现没有因此修改。

最后补强的工厂隔离用例使用相同 world_id、不同工作区，并确认实际进入工厂，以验证 ModeRunner 在调用 Adapter 前拒绝错误存储目标。暂停后经用户重新授权，最新版本单项复验通过（8.903 秒）。综合全量与修正后的定向复验，197 项不同用例中 196 项取得通过结果，1 项因 Windows 符号链接权限跳过；没有遗留已知测试失败，不将这些分次结果表述为一次全量运行全部通过。

41 个 Schema、7 个岗位契约、12 个模型登记、结构样例、编译、系统仓库边界、Git 差异格式与忽略规则检查通过；.env.example 全部为空值。独立代码、文档和最新加强用例的静态审查已通过，执行验收完成。本轮没有读取/迁移真实凭据、初始化正式审批 Key、创建个人正式世界或新增 API 调用。

同步到原项目目录时，补充验证并修正了开发仓库的 worktree 配置兼容性：仅系统边界检查允许受限的 Git 已跟踪文件清单读取，世界仓库的配置拒绝规则保持原样。新增用例及三个相关 Git 防护用例定向复验通过（11.358 秒）。综合累计 198 项不同用例，197 项取得通过结果、1 项因符号链接权限跳过；这仍是全量运行与定向复验的合并记录。

验收使用离线 Adapter 和临时仓库，覆盖跨工作区审批重放、规则注入、独立 Git、恢复与旧布局拒绝；不代表真实模型科学研究验收。改动在 codex/separate-world-workspaces 工作分支交付，发布和合并由操作者控制。
