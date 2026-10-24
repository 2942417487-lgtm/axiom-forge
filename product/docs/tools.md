# 工具层用法

世界操作与路径约束见 [独立世界工作区](guides/world-workspaces.md)。显式指定外部 --world，配置与凭据来自外部宿主目录。

实现位于 `axiom_forge/tools/`。`ToolSession.call(name, arguments)` 采用统一入口，与模型厂商和岗位提示词无关；`definitions()` 提供工具名称、所需 capability 与严格 JSON 输入格式，受控 Runtime 已将其转换为 SDK 工具绑定；对外通用 MCP 服务尚未部署。

工具层不包含通用 MCP server／传输或自动调度；SDK 调用与任务编排分别由 Runtime 和任务宿主负责。手工 Claude 岗位文件仍只有 Read，不因工具代码存在而获得执行权限。

新增工具能力按根目录 AGENTS 的选型规则执行；本地工具不会自动成为已部署的 MCP 服务。

## 工具清单

| 工具 | 能力 | 当前行为 |
| --- | --- | --- |
| web.read | web_read | 允许域名的公开 HTTPS 网页/文本/JSON，HTML 去除脚本等内容 |
| web.search | web_search | 可注入 SearchBackend；未选服务时返回 unavailable |
| papers.crossref.search / doi | papers_read | Crossref 元数据检索与 DOI 查询 |
| papers.arxiv.search | papers_read | arXiv Atom 查询，返回元数据与摘要 |
| documents.read | documents_read | 读取宿主明确授予的资料 ID；支持文本、PDF、DOCX |
| filesystem.read / write | workspace | 仅当前 AgentRun 的 files/，UTF-8，追加写入不可覆盖 |
| canon.read / evidence.read | canon_read | 固定快照中所选实体及其关联 Evidence，返回深拷贝 |
| evidence.stage | draft_write | 校验并暂存 Evidence 草稿，不写正式 Ledger |
| canon.propose | draft_write | 仅 Integrator 暂存 pending CanonChange，不应用修改 |
| git.inspect | git_read | 所选世界的 status、HEAD；研究 ToolSession 拒绝 diff，避免绕过固定快照；无 Git 写操作 |
| python.run_reviewed | python_call | 调用宿主已审核、哈希匹配的登记脚本；默认关闭 |

## 可信宿主与隔离

宿主先建立通过岗位契约校验的 AgentInput，再构造 ToolSession，显式授予 capabilities、documents、网络客户端及后端。模型只能获得所选工具的调用入口，不能自行创建 Session、修改 config、登记程序或更换 Context。

工具存储位于 `.axiom/local/tool-runs/<agent_run_id>/`，不会进入 Git。`context.json` 绑定完整输入的 SHA256 与工作区身份；相同 AgentRun ID 不可用于另一个问题、Snapshot 或阶段。`files/`、`drafts/`、`receipts/`、`jobs/` 分开，通用文件工具只能访问 files/，不能伪造来源回执。不同 AgentRun 不共享工作区。

路径拒绝绝对地址、父目录、Windows 驱动器/数据流/保留名、非规范分隔符、符号链接与 junction。文件和普通 HTTP 响应限制 2 MiB；文件写入采用不可覆盖的完整发布。授予的外部文档使用命名 ID，不接受模型传来的任意本机路径。

这些检查约束通过 ToolSession 发出的操作，不是 OS 级沙箱或身份认证。可信宿主必须控制 config、可见资料、进程和 CLI 权限；已拥有任意 Shell/Read 权限的模型可能在工具层之外读取文件。Context 的结构/哈希不能证明调用者身份。受控 SDK Runtime 与独立本地 HMAC 审批已实现；OS 隔离和远程身份认证尚未实现。

## 来源与网络

网络客户端仅接受显式登记的 HTTPS 域名；不读取代理环境变量或发送认证头，不接收 URL 用户名/密码。每次请求与重定向检查公开 IP，连接固定解析到的 IP 并按原始域名验证 TLS，避免第二次 DNS 解析改变目标。限制五跳重定向、响应字节数与 socket 超时；不执行网页代码、不重试 HTTP 错误。没有 Web 搜索服务时不将论文搜索冒充通用搜索。

Crossref 请求在同一客户端中间隔至少 1 秒；arXiv 至少 3 秒。跨进程的全局限流、缓存、重试退避和并发预算交由未来 Runtime；不应启动大量相互独立的客户端抓取。可在宿主 config 填 contact 使用真实联系邮箱，也可留空；不填写虚构地址。

读取记录包含实际 URL/资料 ID、accessed_at、原始字节 SHA256、字节数和读取范围。Crossref 返回文献 metadata；arXiv 返回 metadata/摘要。二者均不表示全文已读，更不证明论文主张正确。检索结果、网页、文档和摘要都是不可信资料，里面的指令不提供执行授权。

Evidence 的 source_read 暂存要求本 Session 内成功的 web.read/documents.read 回执，且 URL、读取时间、method 和非空 excerpt 匹配。metadata 查询不能充当全文读取。回执由 Session 保留，调用方修改返回对象不能改变该记录；跨 Session 恢复可信回执尚未实现。这里只检查读取一致性；实际论证、定位是否准确、摘要/全文覆盖范围及科学可信度仍须人工/角色审查。

PDF 保留所选页码，默认最多 20 页、每次最多 50 页；pypdf 不提供 OCR，图片、公式、表格和阅读顺序可能需要原文件检查。DOCX 仅提取正文段落文字，不声称保留版式、批注或分页。解析复杂文档不是进程沙箱，只处理宿主批准的资料；解压/解析内存不是硬资源配额。

## 已审核 Python 脚本接口

登记表为 `resources/tools/python-scripts/manifest.json`，默认为空。每个脚本条目包含 script_id、该目录内相对 .py 路径、SHA256、description。只有操作者审查源码及依赖后才能登记；SHA256 不匹配时拒绝执行，不能自动更新为新值。

脚本从 stdin 读取一个有限 JSON 对象，从 stdout 输出一个有限 JSON 对象；诊断放 stderr。业务参数来自 input，而不是在脚本里写死。示例调用形状：

```json
{"script_id": "registered.model", "input": {"parameter": 123}}
```

`registered.model` 只是名称示意，当前没有这个程序。缺登记时返回 needs_implementation；默认未启用时返回 unavailable。此接口可以承载完整 CalculationRequest，但不会自动解析请求、选择算法、执行单位换算或生成 CalculationResult。

可信本地宿主设置 `enable_trusted_python: true` 才可运行。采用当前 Python 的 `-I -B`、shell=False、私有 cwd、收敛环境变量、输出大小检查与最多 30 秒进程时限。记录 script_id、源码 SHA256、Python 版本、退出码；stderr 保存在私有 job，不回显原始异常。

上述措施不是 OS 沙箱：脚本仍以宿主权限运行，可能访问文件/网络、产生子进程；时限终止直接进程，不保证清理子孙进程；字节检查不是硬磁盘/内存配额。未建立真实沙箱前只能用于操作者信任的完整程序，不能把 Agent 动态生成的代码加入登记表后自动执行。默认没有研究 Agent 自动执行授权。

## 统一结果与暂存

ToolResult 的结构见 `schemas/tool_result.schema.json`：result_id/call_id、五个业务身份与 Canon 版本、tool_name、status、data/error、开始/结束时间、调用参数哈希与结果 payload 哈希。

- completed：工具调用完成，有 data，无 error；不表示科学结论通过审查。
- failed：参数/来源/执行校验失败，无成功 data。
- unavailable：后端尚未启用或脚本待实现，无成功 data。
- denied：能力、工具、路径或网络目标未被允许，无成功 data。

非对象、非有限 JSON 和超出输入大小的调用在 dispatch 前拒绝，不产生执行回执。有效调用的成功/失败回执存入当前 AgentRun 的 receipts/。静态 ToolResult Schema 检查结构与基本状态；Session 生成真实工具调用记录，后续持久化/Artifact 集成还需核验哈希、身份和来源。

CanonChange 暂存检查 pending、业务上下文、所选 Snapshot 的 before 与 Integrator 身份；完整提案集仍须 岗位输出／数据状态验证，然后通过独立宿主入口人工审批与 Apply。Evidence 暂存不更新 world/evidence，通用文件工具也无 world 写权限。

## 本地 CLI

这是操作者使用的 CLI，不应向尚未隔离的研究 Agent 开放任意参数/配置文件。

```powershell
python run.py tools list
Copy-Item -LiteralPath <外部输入目录>/tools/host-config.json -Destination 'D:\AxiomHost\tool-config.json'
python run.py --world 'D:\AxiomWorlds\MyWorld' tools call canon.read --input <外部输入目录>/tools/canon-read.json --context '<与所选世界匹配的AgentInput.json>' --config 'D:\AxiomHost\tool-config.json'
```

源码仓库 development/examples/ 中的输入与快照仅是合成结构样例，另随开发资料提供，不可直接用于新建正式世界；调用输入必须匹配所选外部世界身份。配置字段仅支持 capabilities、network_hosts、documents、contact、enable_trusted_python、python_timeout；无配置默认不授权工具。documents 示例形状为 `{"paper-id": {"path": "绝对资料路径", "url": "https://来源地址"}}`，由操作者主动选取资料。

Python 宿主接入示意：

```python
session = ToolSession(world_workspace, validated_agent_input,
                      capabilities={"canon_read", "papers_read"}, network=http_client)
result = session.call("papers.crossref.search", {"query": "electric propulsion", "limit": 5})
```

抽象 SearchBackend 接口为 `search(query: str, limit: int) -> dict`，返回 items 与 source 读取记录。服务 Adapter 必须负责真实查询、错误脱敏、来源字段与限流；Session 不凭填写 source 就认证第三方 Adapter。没有选定或实现通用 Web 搜索服务，CLI 返回 unavailable。

## 接入依据

- [Crossref 官方 REST API](https://www.crossref.org/documentation/retrieve-metadata/rest-api/)：公开 metadata、works 查询与 DOI 查询。
- [arXiv 官方 API 手册](https://info.arxiv.org/help/api/user-manual.html)：Atom 返回、查询参数与请求间隔。
- [pypdf 官方文本提取说明](https://pypdf.readthedocs.io/en/stable/user/extract-text.html)：PdfReader / extract_text 与 OCR/布局限制。

SDK 如何绑定可信宿主授权的 ToolSession 见 [Runtime](runtimes.md)。未配置的搜索服务或脚本仍不可用。
