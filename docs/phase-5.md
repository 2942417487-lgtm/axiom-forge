# Phase 5 交付记录

用户授权继续 Phase 5，并明确选择：只接入已审核 Python 脚本调用接口，通用计算执行器后续再建；通用 Web 搜索先建立可配置接口，服务选定后再启用。本阶段基于已合并的 PR #3，在 `feat/phase-5-tool-layer` 上实现并交付独立待审查 PR。

## 清单与范围

- [x] Web 读取：允许域名的公开 HTTPS、HTML/文本/JSON、真实字节哈希与访问时间。
- [x] 通用 Web 搜索的 SearchBackend 注入接口；按用户选择，未接具体服务，返回 unavailable。
- [x] Crossref 文献检索、DOI 查询；arXiv Atom 查询与摘要读取。
- [x] PDF、DOCX、UTF-8 文本文档读取；资料须由宿主显式授予，PDF 返回选中页码及 OCR/布局限制。
- [x] Python 已审核脚本接口：默认关闭，登记表为空；核对 SHA256、冻结已审核源码字节、JSON stdin/stdout、真实进程与失败状态。
- [x] 当前 AgentRun 的 Filesystem 读写、完整发布、不可覆盖、路径与链接限制。
- [x] 固定快照的所选 Canon/关联 Evidence 读取；Evidence 草稿和 Integrator 的 pending CanonChange 私有暂存。
- [x] 只读 Git status、HEAD 和限定路径 diff；不提供 Git mutation。
- [x] 统一工具定义、参数校验、五个业务上下文/版本、ToolResult、开始/结束时间和参数/payload 哈希。
- [x] 保留关键数值须真实程序化计算的规则；脚本接口未就绪时继续交付 CalculationRequest，不脑算冒充工具结果。

实现与限制见 [工具层](../tools/README.md)，授权范围见 [工程任务](tasks/phase-5.md)。NASA ADS、Semantic Scholar、PubMed、IEEE 等按实际需求后续接入，不声称本轮完成。

## 已执行验证

110 项 unittest：109 项通过，1 项因本机受限测试环境中实际 junction 创建不可用而跳过。新增 36 项工具层测试覆盖闭合参数结构、缺权限/未知工具、Windows/POSIX 路径、符号链接/junction 检查、AgentRun 间隔离与输入不可重绑定、追加写入、真实来源回执匹配、metadata 不冒充全文、pending 提案与岗位限制、PDF/DOCX/HTML 解析、公开 IP/重定向限制、后端缺失与异常脱敏、Python 复用/哈希/缺登记/超时/错误/环境变量、只读 Git、ToolResult 状态及 CLI。实际 junction 创建之外的链接/reparse 拒绝逻辑有独立测试。

29 个 Schema / 本地引用、7 个岗位契约、28 个根 Schema 样例及工具 CLI 检查通过。生产 world 校验仍只有 world.json；没有导入测试设定、修改 Canon 或正式 Evidence。Git 差异、忽略规则与空值密钥模板检查通过。

真实接口联调于本机 2026-10-04（Asia/Shanghai）完成；先在受限 sandbox 中失败，经用户授权网络访问后成功运行新工具：

| 工具与请求 | 实际返回 | 原始内容 SHA256 |
| --- | --- | --- |
| Crossref DOI `10.1038/nphys1170` | 1 条 metadata，4918 bytes | `921770fcba28cbfe695a01a42af0cd9df9a59ed07842e665e16e455983aa456f` |
| arXiv `all:"electric propulsion"`，limit=1 | 1 条记录，2630 bytes | `424393bf3449ffbd41c1f93eb7fa25aee27c71ce535b0fdfc857387fb820f33d` |
| Crossref 官方 REST 文档网页 | HTML 70857 bytes，提取文字 13650 字符 | `4fb3ea03c2372eed4ad9b23c09f411402745915167aab0584b594f0a9c737624` |

实际访问时间为 UTC 2026-10-03 18:07:45–18:07:47。本地真实回执保存在忽略的 `.cache/tool-runs/`，联调摘要在 `.cache/phase5-smoke-result.json`。上表仅证明接口响应与来源读取，不证明论文主张、技术可行性或科学计算正确。

Python 的真实 subprocess 测试使用合成 JSON 回传脚本和失败样例，不是成本/推进等模型程序。PDF 测试使用程序生成的测试页和正文文字；未宣称所有实际论文版式都能准确解析。静态 examples/tool_result.json 为 unavailable 的 TEST FIXTURE，不是上述真实联调回执。

## 尚未实现与权限边界

Phase 6 Runtime、SDK Adapter、MCP server/传输、将工具绑定到真实 Agent、调度/恢复、审批认证与 Canon Apply 均未实现。Claude 专项岗位保持 Read；ToolSession 是可信宿主操作的本地接口，其配置和业务身份不能由模型自行提供。

已审核 Python 接口是受信本地进程调用，环境收敛、哈希与时限不是 OS 沙箱。它不隔离所有文件/网络权限或子孙进程，不能自动执行 Agent 新生成代码。通用计算执行器、物理/经济模型、单位语义校验、CalculationResult 生成与 MATLAB Adapter 均按用户选择留待后续。

Canon/Evidence 的写入能力限于私有暂存：结构/上下文/读取回执一致性检查不认证科学内容或完整拟议状态；进入正式知识库仍须验证与人工审批。工具层也不声称强制隔离其外部的任意 Shell/文件系统权限。

本阶段 PR 待用户审查；PR #3 的合并授权不适用于本阶段，不自动合并或推进 Phase 6。
