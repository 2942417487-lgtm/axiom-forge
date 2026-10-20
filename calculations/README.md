# 可复用计算请求与程序接口

本目录定义参数化计算请求、模型和结果协议。通用计算执行器及 MATLAB Adapter 未提供；缺工具／模型／参数时交付完整请求，不能冒充已实算结果。

[已审核 Python 脚本宿主接口](../tools/README.md) 默认关闭且登记表为空；它不会自动解析 CalculationRequest、分发模型、核验单位或生成 CalculationResult。

## 两条工作路径

1. 角色识别计算需求，输出 `CalculationRequest`。
2. 若未来 Runtime 已接入且授权计算后端，并且有符合请求模型/版本的程序，调用 `CalculationBackend.execute(request) -> CalculationResult`。
3. 否则交付同一个请求文件给作者，供 Codex、DSH 或其他编程工具构建/调用程序。缺少工具、模型或必要参数时保持 OPEN QUESTION，不产生伪造数值。
4. 程序交付并审查后登记版本化模型；后续请求可改变参数/情景并复用该程序。

手工 Claude 岗位入口只有 Read。两岗位在 calculation_requests 数组交付完整请求；受控 Runtime 验证后保存独立请求文件和 Artifact。通用分发与计算执行仍须另外实现，请求文件不是计算结果。

## 通用文件格式

权威格式为 UTF-8 JSON，Schema 是 [calculation_request.schema.json](../schemas/calculation_request.schema.json)。建议文件名 `<request_id>.request.json`；请求本身是一份 Artifact，因此 request_id 使用现有 ART-UUIDv4，可用 `new-id artifact` 生成。

| 字段 | 内容 |
| --- | --- |
| schema_version、request_id | 协议版本与本次请求 Artifact 身份 |
| world_id、task_id、run_id、agent_run_id、canon_version、role | 请求对应的业务执行与固定 Canon 版本 |
| problem | 问题标题、详细描述和工程/经济领域 |
| model | model_id 和 model_version；选取可复用算法，不是厂商模型名 |
| method | 计算方式、公式、参考资料和适用限制；这些文本不直接执行 |
| parameters | 名称、数据类型、值、单位、含义、是否必需、来源、上下界与不确定性 |
| expected_outputs | 要求的变量名、类型、单位与意义 |
| assumptions、cost_basis | 前提、币种、价格基年、时间范围、实质/名义折现、税费/残值口径 |
| scenarios | 命名情景及参数覆盖值；不修改模型算法 |
| acceptance_checks | 指定输出的有限性、范围或参考值与绝对/相对误差要求 |
| execution_policy | 有可用工具时自动执行或只交付请求；期望与允许的后端 |
| requested_deliverables | 参数化源码、模型描述、依赖、测试、示例、结构化结果和执行回执 |
| created_at、metadata | 请求时间与扩展信息；不得存密钥 |

支持 scalar、integer、vector、matrix、text、boolean 参数。数值与单位分离：数量可用 `kg`，无量纲用 `1`，成本示例用 `USD_2026` / `USD_2026/year`。字符串不含待求值代码；数组不写成待解析的自然语言。缺值用 null 并说明缺口，不能擅自填零。matrix 必须是规则矩阵，尺寸约束由后续模型校验落实。

现实依据使用 source.reference_ids 关联 Evidence/Canon/Claim；没有依据时显式标为 assumption 或 user_input。派生参数必须说明上游计算。来源记录不证明真实搜索已发生，单位也不因写在文件里自动正确。

成本请求必须有 cost_basis；非成本请求可为 null。不混用币种/价格基年或实际/名义现金流；转换方法与输入必须明确。工程和经济样例分别见 [制造成本请求](../examples/calculation_request.json)、[生命周期成本请求](../examples/calculations/economic-cost-request.json)。样例没有现实成本依据，且保留缺失参数，没有实际计算。

## 可复用程序的接口要求

后续实现必须提供同格式请求入口，例如 `calculator run <request.json> --output <result.json>`（这是接口规划，当前没有该命令）。用户把请求文件作为命令/应用输入即可启动解析；可另做拖放入口，但拖放 UI 本轮也未实现。

程序流程必须是：解析 JSON → 结构校验 → 查找 model_id/version → 按模型契约匹配参数/单位/尺寸 → 检查必要输入与情景 → 执行真实算法 → 验收检查 → 输出结构化结果与回执。

“自动识别”指读取明确字段并分发到已登记模型，不代表程序能凭任意自然语言自动发明算法。不能确定模型、单位或参数含义时返回缺口，禁止静默改算法、降精度、填默认成本、替换模型版本或执行请求中的任意代码。

模型结构由 [calculation_model.schema.json](../schemas/calculation_model.schema.json) 定义。一个 model_id/version 声明输入/输出类型与单位，登记 Python、MATLAB 或其他后端。planned 表示没有程序；ready 必须有 entrypoint、源码 Artifact 与 SHA256。单纯填写 ready 字段不证明可执行，后续 Runtime 还必须核对文件、依赖、测试和运行权限。

Python 接口规划为 `execute(request: Mapping) -> Mapping`；MATLAB 接口规划为 `result = execute(request)`，在外层用 UTF-8 JSON 输入/输出。后端均遵守同一请求和结果结构，语言选择不改变业务身份、模型版本、参数意义与验证规则。此处没有实际函数实现，也没有要求本机安装 MATLAB。

模型算法与具体参数分离，不在代码里写死本次输入；模型版本不可静默改变。传入同一模型版本的新参数或多个 scenarios 时复用同一程序。每次输出包含请求的规范化 JSON SHA256、程序版本与源码 SHA256、运行环境/依赖 Artifact 以及执行时间。重复运行应可复现；随机模型必须显式记录种子、数值精度和算法参数。

交给 Codex/DSH 的编程要求应包含：按照请求字段实现通用入口；检查单位/边界/矩阵维度/缺参；未知模型返回待实现状态；源码参数化；交付模型描述、锁定依赖、边界测试、示例与使用方法；不覆盖 Canon 或读取未授权数据。程序化计算不保证输入来源或模型适用性正确，仍需角色与 Red Team 审查。

## 结果与错误状态

[calculation_result.schema.json](../schemas/calculation_result.schema.json) 定义结果文件。result_id 使用独立 ART-UUIDv4；request_id、request_sha256 与五个任务上下文字段关联原请求。cases 保存每个情景的 typed outputs 和检查结果；receipt 保存真实后端、模型/版本、程序与环境 Artifact、源码 SHA256 和执行时间。

- completed：程序真实执行完毕且所有请求的验收条件通过；有结果与回执，无 issues。
- failed：实际执行或验收失败，issues 说明原因；不提供可误认成成功结果的 cases。
- needs_input：缺必要参数、单位/尺寸不匹配、情景或条件不明确。
- needs_implementation：模型或所需程序尚未构建。
- unsupported_engine：当前没有请求允许的可执行后端。

后三项不得携带已执行回执或计算结果。缺工具时交付请求本身与问题说明；CalculationResult 样例为 needs_implementation，不是实算记录。

completed 结果只有通过后续调用方的语义与 Artifact 核验，才能写入既有 `EngineeringResult/EconomicResult.calculations`。待执行请求放 calculation_requests，不放 calculations，不伪造 executable receipt。后续 Runtime 还需绑定输出与当前 AgentRun、防止篡改和首轮他人结果泄露。

## 目前能验证什么

现有 `validate <schema> <file>` 能检查新增三类 JSON 的结构、类型与基本状态约束。能拒绝把缺工具请求写成 completed 却没有回执，也能拒绝 planned 模型携带虚假源码定位。

现有校验不包含通用计算协议语义执行器：request/result 之间的身份与哈希关联、参数名唯一性、矩阵规则性、上下界关系、单位转换、模型版本匹配、情景覆盖、输出全集与所有验收条件的执行，须在后续实现中检查。request 内声明 auto_if_available_else_handoff 不提供工具授权，也不能突破项目权限。

```powershell
.\.venv\Scripts\python.exe -m axiom_forge validate calculation_request examples/calculation_request.json
.\.venv\Scripts\python.exe -m axiom_forge validate calculation_request examples/calculations/economic-cost-request.json
.\.venv\Scripts\python.exe -m axiom_forge validate calculation_model examples/calculation_model.json
.\.venv\Scripts\python.exe -m axiom_forge validate calculation_result examples/calculation_result.json
```
