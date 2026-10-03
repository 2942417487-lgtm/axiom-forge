# Axiom Forge

硬科幻世界观研究、工程推演、事实验证与一致性审查系统。

本项目服务于长期世界观设计：验证现实依据，检查物理与工程约束，推演技术、经济、制度和历史之间的因果关系，并保存可以追溯的证据与决策。

## 当前进度

当前仅搭建 Phase 0：项目与安全基础。世界观数据层、Evidence Ledger、Schema、Agent Runtime、模型路由和工作流尚未实现。

本阶段没有应用程序入口，不需要安装依赖或配置真实 API Key，也没有模型调用或费用。

## 本地使用

在项目目录中阅读 `AGENTS.md` 和 `CLAUDE.md`，了解研究与开发边界。需要 API 接入时，再从模板创建本地配置：

```powershell
Copy-Item -LiteralPath .env.example -Destination .env
```

真实密钥只保存在本地 `.env` 或系统 Secret Store。`.env.example` 只包含变量名与空值。不得在文件、日志、聊天或 Git 中披露凭据。

Phase 0 的检查命令：

```powershell
git status --short --branch
git diff --check
git check-ignore .env .env.local .venv/ignore-check node_modules/ignore-check tmp/ignore-check
git ls-files .env.example
```

尚无业务代码与测试套件；后续实现软件功能时必须添加与风险相称的验证，并记录结果。

## 当前目录

```text
.
├── .env.example       # 空值的 API 环境变量模板
├── .gitattributes     # 文本换行规范
├── .gitignore         # 密钥、缓存、环境、日志与临时文件的排除规则
├── AGENTS.md          # 所有 Agent 的项目总则
├── CLAUDE.md          # Claude Runtime 操作说明
├── README.md          # 项目定位、使用方式和目录说明
└── docs/
    └── phase-0.md     # 本阶段交付与检查记录
```

## 后续目录规划

以下为设计规划，按后续阶段逐步创建：`world/`、`schemas/`、`agents/`、`.claude/agents/`、`tools/`、`runtimes/`、`routing/`、`workflows/`、`evals/`、`tests/`。

业务角色与具体模型解耦；厂商模型名称、API 标识、价格和能力必须在接入时查证。先验证简单 Python V1，再评估引入 LangGraph。

## Git 与人工审查

GitHub 仓库使用 Private 可见性。私有仓库仍需严格排除凭据。

AI 的重要系统或世界观修改必须在功能分支上完成，经验证、人工审查后再合并至 `main`。初始 `main` 仅建立空提交作为分支基线；Phase 0 文件放在 `bootstrap/phase-0`，等待人工审查。

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
