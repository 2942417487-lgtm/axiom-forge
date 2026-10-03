# Axiom Forge

硬科幻世界观研究、工程推演、事实验证与一致性审查系统。

本项目服务于长期世界观设计：验证现实依据，检查物理与工程约束，推演技术、经济、制度和历史之间的因果关系，并保存可以追溯的证据与决策。

## 当前进度

已建立 Phase 0–4 的项目基础、世界观数据层、Evidence Ledger、统一业务 Schema 与七个 Agent 角色契约。提供离线数据校验、业务 ID、Canon Snapshot、受限输入投影与角色输入/输出校验。

当前生产 world 为空；Agent Runtime、模型路由、完整任务工作流和 Canon 应用尚未实现。本阶段不调用模型 API，不需要真实 API Key。

## 本地使用

在项目目录中阅读 `AGENTS.md` 和 `CLAUDE.md`，了解研究与开发边界。需要 API 接入时，再从模板创建本地配置：

```powershell
Copy-Item -LiteralPath .env.example -Destination .env
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
.\.venv\Scripts\python.exe -m axiom_forge validate-world
.\.venv\Scripts\python.exe -m axiom_forge validate task_state examples/task_state.json
.\.venv\Scripts\python.exe -m axiom_forge check-contracts
.\.venv\Scripts\python.exe -m axiom_forge validate-agent-output examples/agent_input.json examples/lead_plan.json
.\.venv\Scripts\python.exe -m axiom_forge new-id task
.\.venv\Scripts\python.exe -m axiom_forge new-id entity --domain technology
.\.venv\Scripts\python.exe -m axiom_forge snapshot create
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

快照创建命令返回文件路径；用 `snapshot verify <返回的文件路径>` 独立验证。相同数据复用已验证的同一内容版本，禁止覆盖旧快照。参数 `--repo <目录>` 位于命令之前；从其他目录启动时须保证 axiom_forge 可导入。

Git 基础检查：

```powershell
git status --short --branch
git diff --check
git check-ignore .env .env.local .venv/ignore-check node_modules/ignore-check tmp/ignore-check
git ls-files .env.example
```

已实现本地基础工具与 68 项 unittest；完整研究工作流留到后续阶段。使用说明：[世界观数据](world/README.md)、[Evidence 规范](docs/evidence.md)、[业务接口](schemas/README.md)、[Agent 契约](agents/README.md)、[Phase 4 交付记录](docs/phase-4.md)。

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
├── axiom_forge/       # 本地校验、ID、快照与 Agent Contract 工具
├── schemas/           # 25 个 JSON Schema 与接口说明
├── world/             # 分域知识库、生产 world_id 与初始空快照
├── examples/          # 24 个 Schema 样例及 6 个角色输入包，全部为测试数据
├── tests/             # 完整性与失败边界测试
└── docs/              # Evidence 规范、阶段记录与工程任务说明
```

## 后续目录规划

以下为设计规划，按后续阶段逐步创建：`tools/`、`runtimes/`、`routing/`、`workflows/`、`evals/`。

业务角色与具体模型解耦；厂商模型名称、API 标识、价格和能力必须在接入时查证。先验证简单 Python V1，再评估引入 LangGraph。

## Git 与人工审查

GitHub 仓库使用 Private 可见性。私有仓库仍需严格排除凭据。

仓库地址：[2942417487-lgtm/axiom-forge](https://github.com/2942417487-lgtm/axiom-forge)。`origin` 已连接该仓库，默认分支为 `main`。

AI 的重要系统或世界观修改必须在功能分支上完成，经验证、人工审查后再合并至 `main`。Phase 0 的 [PR #1](https://github.com/2942417487-lgtm/axiom-forge/pull/1) 与 Phase 1–3 的 [PR #2](https://github.com/2942417487-lgtm/axiom-forge/pull/2) 已经用户审查并授权合并；main 包含 Phase 0–3。

Phase 4 使用 `feat/phase-4-agent-contracts`，基于 main 提交独立 PR，等待新一轮审查。此前的合并授权不自动适用于本阶段 PR。

本机的 GitHub CLI 便携版与认证配置位于 `.cache/`，不会进入 Git。本仓库单独配置了 CLI credential helper；全局 Git 认证配置保持原状。更换电脑时需要自行配置 GitHub 认证，本地 `.cache/` 不可作为共享文件上传。

```powershell
git switch -c feat/short-description
# 完成修改并执行相关检查
git diff --check
git add -- <明确指定的文件>
git commit -m "Describe the change"
git push -u origin HEAD
# 在 GitHub 发起 Pull Request，人工审查后合并。
```

Hard Canon 修改还必须经过 `ProposedCanonChange → Validation → Human Approval → Apply → Git Commit`。仓库私有可见性与文档规则不等于服务端分支保护；后续若要配置强制规则，应单独实施并核验。
