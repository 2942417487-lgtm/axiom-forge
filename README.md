# Axiom Forge

硬科幻世界观研究、工程推演、事实验证与一致性审查系统。

本项目服务于长期世界观设计：验证现实依据，检查物理与工程约束，推演技术、经济、制度和历史之间的因果关系，并保存可以追溯的证据与决策。

## 当前进度

Phase 0–11 已合并，PR #8 完成持久化、审计与显式恢复。本轮基础分离改造将正式世界移到外部独立 Git 仓库，系统仓库只保留代码、规则、模板与合成测试资料。每个世界创建时就建立本地版本管理；GitHub 连接、标准导出/导入和前端另行实施。具体设计与命令见 [独立世界工作区](docs/world-workspaces.md)。

已有官方 SDK Runtime、受限工具、模型路由、四种模式、Task Manager 和人工 Canon 审批。四款模型的真实合成接入测试与研究流程的离线验收分别记录，不代表完整科学研究已通过真实模型验收。通用 Web 搜索与计算执行器尚未实现。

## 本地使用

在项目目录中阅读 `AGENTS.md` 和 `CLAUDE.md`，了解研究与开发边界。需要 API 接入时，将空值模板复制到系统与世界仓库之外的宿主目录，再填写本地配置：

```powershell
Copy-Item -LiteralPath .env.example -Destination 'D:\AxiomHost\.env'
```

真实密钥只保存在本地 `.env` 或系统 Secret Store。`.env.example` 只包含变量名与空值。不得在文件、日志、聊天或 Git 中披露凭据。

需要 Python 3.11+ 与主解释器中的 pip 22.3+。在项目根目录搭建隔离环境（本机避免了 ensurepip 的路径兼容问题）：

```powershell
python -m venv --without-pip .venv
python -m pip --python .venv install -r requirements-lock.txt
```

运行与验证：

```powershell
.\.venv\Scripts\python.exe -m axiom_forge check-schemas
.\.venv\Scripts\python.exe -m axiom_forge --world 'D:\AxiomWorlds\MyWorld' validate-world
.\.venv\Scripts\python.exe -m axiom_forge validate task_state examples/task_state.json
.\.venv\Scripts\python.exe -m axiom_forge check-contracts
.\.venv\Scripts\python.exe -m axiom_forge validate-agent-output examples/agent_input.json examples/lead_plan.json
.\.venv\Scripts\python.exe -m axiom_forge new-id task
.\.venv\Scripts\python.exe -m axiom_forge new-id entity --domain technology
.\.venv\Scripts\python.exe -m axiom_forge --world 'D:\AxiomWorlds\MyWorld' snapshot create
.\.venv\Scripts\python.exe -m axiom_forge tools list
.\.venv\Scripts\python.exe -m axiom_forge routing check
.\.venv\Scripts\python.exe -m axiom_forge routing select --request examples/routing-request.json
.\.venv\Scripts\python.exe examples/offline_modes.py
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

快照创建命令返回文件路径；用 `snapshot verify <返回的文件路径>` 独立验证。相同数据复用已验证的同一内容版本，禁止覆盖旧快照。新世界先使用 `world create --path <外部空目录> --name <名称>` 创建。参数 `--world <目录>` 和可选 `--engine-root`、`--host-root` 位于命令之前；旧 `--repo` 明确拒绝。从其他目录启动时须保证 axiom_forge 可导入。

Git 基础检查：

```powershell
git status --short --branch
git diff --check
git check-ignore .env .env.local .venv/ignore-check node_modules/ignore-check tmp/ignore-check
git ls-files .env.example
```

本地基础、角色契约和工具层的测试与真实接口联调记录见 [Phase 5 交付记录](docs/phase-5.md)；完整真实科学研究验收尚未进行。使用说明：[世界观工作区](docs/world-workspaces.md)、[Evidence 规范](docs/evidence.md)、[业务接口](schemas/README.md)、[Agent 契约](agents/README.md)、[可复用计算请求与接口](calculations/README.md)、[工具层](tools/README.md)。

## 当前目录

```text
.
├── .env.example       # 空值的 API 环境变量模板
├── .gitattributes     # 文本换行规范
├── .gitignore         # 密钥、缓存、环境、日志与临时文件的排除规则
├── AGENTS.md          # 所有 Agent 的项目总则
├── CLAUDE.md          # Claude Runtime 操作说明
├── .claude/agents/    # 七个 Claude 专项岗位文件，当前仅 Read
├── agents/            # 厂商无关岗位规则与七个 JSON Contract
├── README.md          # 项目定位、使用方式和目录说明
├── requirements.txt / requirements-lock.txt
├── axiom_forge/       # 校验、ID、快照、Contract、tools/ 与 runtimes/ 实现
├── schemas/           # 41 个 JSON Schema 与接口说明
├── tools/             # 工具接口说明与空的已审核 Python 脚本登记表
├── runtimes/          # 官方 SDK Adapter 说明与独立锁定依赖
├── routing/           # 模型登记、岗位分配、路由与有界升级策略
├── modes/             # 四种模式的指导规则与运行说明
├── calculations/      # 通用计算请求、模型与结果协议；执行器待实现
├── templates/         # 新世界模板与历史空脚手架；正式 world 位于外部仓库
├── examples/          # Schema/岗位/计算/工具样例、路由配置与离线模式演示
├── tests/             # 完整性与失败边界测试
└── docs/              # Evidence 规范、阶段记录与工程任务说明
```

## 后续目录规划

以下为设计规划，按后续阶段逐步创建：`workflows/`、`evals/`。Runtime 提供单次调用，模式入口组合有界研究会话；Claude 使用 SDK 内进程 MCP 绑定，尚未部署对外通用 MCP 服务。

业务角色与具体模型解耦；厂商模型名称、API 标识、价格和能力必须在接入时查证。先验证简单 Python V1，再评估引入 LangGraph。

## Git 与人工审查

GitHub 仓库使用 Private 可见性。私有仓库仍需严格排除凭据。

仓库地址：[2942417487-lgtm/axiom-forge](https://github.com/2942417487-lgtm/axiom-forge)。`origin` 已连接该仓库，默认分支为 `main`。

AI 的重要系统或世界观修改必须在功能分支上完成，经验证、人工审查后再合并至 `main`。Phase 0 的 [PR #1](https://github.com/2942417487-lgtm/axiom-forge/pull/1)、Phase 1–3 的 [PR #2](https://github.com/2942417487-lgtm/axiom-forge/pull/2)、Phase 4 的 [PR #3](https://github.com/2942417487-lgtm/axiom-forge/pull/3) 与 Phase 5 的 [PR #4](https://github.com/2942417487-lgtm/axiom-forge/pull/4) 已经用户审查并授权合并；main 包含 Phase 0–5。

PR #5–#8 已按用户授权合并，main 包含 Phase 0–11。本轮在 `codex/separate-world-workspaces` 交付基础分离改造，等待人工审查。系统开发 PR 与世界 Canon 分支属于不同仓库；Canon Apply 只创建世界分支，发布与合并仍由操作者控制。

本机的 GitHub CLI 便携版与认证配置位于 `.cache/`，不会进入 Git。本仓库单独配置了 CLI credential helper；全局 Git 认证配置保持原状。更换电脑时需要自行配置 GitHub 认证，本地 `.cache/` 不可作为共享文件上传。

```powershell
git switch -c codex/short-description
# 完成修改并执行相关检查
git diff --check
git add -- <明确指定的文件>
git commit -m "Describe the change"
git push -u origin HEAD
# 在 GitHub 发起 Pull Request，人工审查后合并。
```

Hard Canon 修改还必须经过 `ProposedCanonChange → Validation → Human Approval → Apply → Git Commit`。仓库私有可见性与文档规则不等于服务端分支保护；后续若要配置强制规则，应单独实施并核验。
