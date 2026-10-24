# 仓库宿主回执：数据基础实现

日期：2026-10-23。当前状态：已随 PR #13 集成；用户于 2026-10-24 合并，见[发布与合并核对](2026-10-24-receipts-storage-pr.md)。下文保留本阶段原执行、验证与授权范围。

## 授权与基线

用户确认本轮实现四类回执 Schema、标识与引用校验、回执链验证及测试，并交付独立审查。需求依据为[回执契约](../../../product/docs/contracts/repository-host-receipts.md)第 3–7 节。任务开始时工作目录干净，HEAD 为 `401aa51b3e797e4c3c2f228379ee141cb6095bdc`；新工作分支为 `codex/repository-receipt-foundations`。保留原接续分支及 main。

## 范围与完成条件

- 四类回执精确封套、必填字段、类型、可空值及三类引用 Schema；登记 RPO／RRC 标识生成。
- 纯离线 API：严格 UTF-8 原始 JSON 字节解析、单份回执校验、显式提供内容字节的 ContentRef 哈希校验、GitCommitRef 形状校验，以及按输入顺序的回执链验证。诊断不回显来源值或未知键名。
- 链验证检查同操作、唯一 ID、连续序号、合法阶段、原字节哈希、准备／校验／接受／结果引用及跨阶段内容绑定。支持尚未结束的有效链前缀，返回是否终态；终态后追加必须失败。
- JSON Schema 的 integer 接受 `1.0`，本契约要求 sequence 必须是实际 JSON 整数，因此单份 API 另做严格类型校验。记录时间使用现行日期时间规则并要求 UTC Z，不用时间推导授权。
- 复用现有 `validate <schema> <file>` 作为单份回执检查入口；链验证通过 Python API，新增接口不写文件、不创建 WorldWorkspace、不调用 Git／模型／网络。所有示例为合成测试数据。
- 测试通过公开接口覆盖合法链、早停、拒绝、篡改、重排、跨操作／阶段引用、错误类型／编码、绑定漂移及安全诊断；运行全套测试及必要静态检查，分别记录 Standards／Spec 独立审查。

## 本轮边界

ContentRef 验证器只核对显式传入字节的 SHA-256；不读取路径、不解析外部内容记录或分块根清单。链验证不读取 ContentRef 指向的宿主记录，也不判断其登记类型、权限、覆盖真实性或执行效果。GitCommitRef 只检查格式，不检查实际 Git 对象。成功报告固定标明数据校验范围与 `execution_authorized=false`。

宿主身份／人工接受验证器、可靠保存、分块存储、防重放控制面、Git 取得／登记／更新执行器不在本轮；H01–H26 产品行为矩阵仍待宿主实现验收。保留 CanonHost 与审批／恢复协议，不操作正式世界、不读取凭据、不调用付费模型。本轮不提交、推送或创建／合并 PR。

本轮增加数据校验模块，未新增工具／Adapter／外部服务能力；直接复用已有 jsonschema 与本地 Registry。后续宿主后端的 MCP／skills 选型仍按 AGENTS 真实检索。

## 实际验证与审查

### 交付内容

- `schemas/repository_{preparation,inspection,acceptance,operation}_receipt.schema.json` 及共享 `repository_receipt_common.schema.json`：精确字段、可空值、阶段、UTC Z 时间、严格 ID／哈希／OID 形状。
- `axiom_forge/repository_receipts.py`：严格单份字节解析、有界文件入口、显式内容字节校验及原字节回执链检查。`ids.py`／公共 Schema 增加独立 RPO／RRC 命名空间；通用 `validate` 接入安全读取和诊断。
- 四份完整合成示例可组成链；新增 31 项公开接口测试，原基础覆盖检查纳入新增 Schema。用法见[回执数据校验](../../../product/docs/guides/repository-receipt-validation.md)。
- 接续／变更索引、Schema 说明、根目录导航及契约中两个过时实现状态同步。没有改研究工具目录、Runtime、CanonHost、恢复实现、可信岗位、AGENTS 或工程技能。

### 测试与静态检查

1. 定向首轮 `python -m unittest tests.test_repository_receipts tests.test_foundations -v` 的纯数据用例通过，涉及临时目录的用例因沙箱 WinError 5 失败；按平台权限机制在沙箱外重跑，68 项全部通过，无跳过。没有为通过测试弱化路径检查。
2. `python -m unittest discover -s tests -v` 在沙箱外运行，248 项，退出 0，`OK (skipped=2)`，耗时 639.181 秒。两项跳过为既有 `test_linked_project_cannot_read_outside_selected_directory` 和 `test_nested_git_ref_link_rejected_before_external_ref_write`，当前 OS 权限不允许创建合成符号链接；未作管理员补验。本次离线回归含合成外部世界的 `validate-world` CLI 用例，不使用正式世界。
3. 全套运行期间完成 Spec 审查修正：移除结果 `before_ref` 必须复用 inspection 同一记录 ID 的额外限制，并新增正例。全套进程已经载入修正前模块／测试，因此上述 248 项不能称为最终版本的第二次全套验证。修正后独立运行 `python -m unittest tests.test_repository_receipts -v`，31 项全部通过，0 跳过；其他模块代码未再变化。
4. `check-schemas`：47 份 Schema 及本地引用通过；`check-contracts`：七岗位通过；`routing check`：12 个登记模型的离线路由策略通过；`validate task_state examples/task_state.json` 通过。首次将 Lead 输入误配研究输出时按契约拒绝，改用匹配的 `examples/lead_plan.json` 后 `validate-agent-output` 通过。上述检查未调用真实模型。
5. `check-system-boundary` 首次因沙箱临时 hooks 目录 WinError 5 失败，按平台权限机制重跑后退出 0，确认系统资源没有正式 world 或被跟踪私人执行状态。
6. 最终工作集为 23 份修改／未跟踪文件；UTF-8／无 BOM、结尾换行、尾空白、Python／JSON 语法、七份 Markdown 代码块及本地链接检查通过，`git diff --check` 无诊断。`.env.approval`、`.env.local`、secrets、`.axiom/local`、`.cache`、tmp、`.venv`、node_modules 忽略规则通过，`.env.example` 变量仍全部为空值，介绍规范仍为 0 字节。没有读取真实密钥。

### 独立审查

依据 `af-dev-code-review` 和工程技能本地适配，两个只读 Agent 分别以 `401aa51b3e797e4c3c2f228379ee141cb6095bdc` 为固定基线，使用 `git diff <基线> --`，并完整读取明确列出的未跟踪模块、Schema、示例、测试和任务／指南。

| 轴 | 初次／追加发现 | 修正与复核 |
| --- | --- | --- |
| Standards | 1 项 P2：CURRENT 沿用“本轮保持源码与校验协议不变”的旧说明 | 更新为本轮新增回执 Schema／模块及既有研究／审批／恢复实现保留的实际状态；原审查 Agent 复核关闭，剩余 0 项 |
| Spec | 初次未报问题；针对结果基线的追加检查复现 1 项 P2：契约未要求结果 before_ref 复用 inspection 同一 ContentRef | 移除额外身份约束；新增相同哈希、新记录 ID 的正例，指南交由宿主核对实际基线；原审查 Agent 复核关闭，剩余 0 项 |

接受回执的严格内容绑定仍保留。审查结论覆盖本轮数据基础，不替代宿主权限、持久化或真实仓库操作验收。审查后契约仅补充已经实现的 ID／校验接口导航，开发记录按实际测试结果收尾。

### Git 与后续范围

当前分支为 `codex/repository-receipt-foundations`；HEAD 仍为起始基线 `401aa51`，暂存区为空。main／本地 origin/main 保留 `a50e0ce`；原分支、worktree、忽略缓存及私人状态保留。没有提交、推送、创建 PR、合并、查询远端或操作正式世界。

后续候选是宿主记录／分块与可靠保存、宿主人工验证及仓库执行后端，需分别明确范围与真实检索现成工具方案。本轮代码与文档等待用户人工 review；数据校验成功始终不授予执行权限。
