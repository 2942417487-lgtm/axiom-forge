# Phase 0：项目与安全基础

历史交付记录；PR #1 已于后续会话经用户审查并授权合并。当前进度见 README.md 与 docs/development/history/phases/phase-4.md，下文描述 Phase 0 交付时的状态。

本轮授权范围：仅 Phase 0。项目名：Axiom Forge；GitHub 仓库名：`axiom-forge`，要求 Private。

## 本地交付

- 已创建 `.gitignore`：排除真实环境配置、缓存、虚拟环境、`node_modules`、日志和临时文件；保留 `.env.example`。
- 已创建 `.env.example`：仅包含 `ANTHROPIC_API_KEY=`、`OPENAI_API_KEY=`、`DEEPSEEK_API_KEY=`。
- 已创建 `README.md`：说明定位、本阶段使用方式、当前目录与后续规划。
- 已创建 `AGENTS.md`：所有 Agent 的事实、计算、Canon、独立分析、安全与人工控制规则。
- 已创建 `CLAUDE.md`：Claude 的读取、工作、验证与交付流程。
- 已制定重要修改通过 branch、review、merge 的规则。
- 已创建 `.gitattributes`：统一文本文件换行。

## Git 与 GitHub 状态

本地 Git 已初始化，提交署名使用用户提供的 GitHub 账号名 `2942417487-lgtm`，仅设置于本仓库。`main` 的初始提交只保存空基线；Phase 0 文件在 `bootstrap/phase-0` 分支交付审查。

已创建并核验 GitHub 私有仓库：[2942417487-lgtm/axiom-forge](https://github.com/2942417487-lgtm/axiom-forge)。远端 `origin` 为 `https://github.com/2942417487-lgtm/axiom-forge.git`，默认分支为 `main`。

`main` 空基线和 `bootstrap/phase-0` 已上传，并建立本地跟踪关系。Phase 0 内容通过 Pull Request 交付人工审查；合并尚待人工决定。

GitHub CLI 便携版位于已忽略的 `.cache/github-cli/`，已校验官方发布资产 SHA256；CLI 登录由用户独立授权。认证配置使用已忽略的 `.cache/gh-auth/`，本仓库的 credential helper 指向该 CLI；未更改全局 Git credential helper。

## 检查记录

已核验：17 个敏感文件、缓存、环境、日志和临时路径被忽略；5 个项目文档和模板路径可被跟踪；`.env.example` 的 3 个变量全部为空值；7 个交付文件齐全。

已通过 Git 差异空白检查。已核验远端 `isPrivate=true`、默认分支为 `main`、两个分支上传成功。

## 后续阶段

Phase 1 及以后尚未实施。本轮没有创建世界观数据、Evidence、Schema、Runtime、模型注册表、LangGraph 或应用入口。
