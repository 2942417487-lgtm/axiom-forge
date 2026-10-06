# Phase 7–9 交付与验收

基于已合并 PR #5 的 main，功能分支 `feat/phase-7-9-routing-modes`。用户授权继续至 Phase 9，启用并联调 Luna、Sol、Sonnet、Opus；Fable、Astra、DeepSeek 暂不启用。用户确认 Phase 6 累计实际费用 $0.1049，本次与 Phase 6 合计 API 上限为 2 美元。四种模式实现有界运行入口，整轮采用离线验收，未调用真实模型执行整轮研究。

## 实现

- Model Registry 登记七款当前设计模型与五个 legacy 条目，记录家族、供应商、档次、成本类别、上下文/输出、SDK 可绑定的工具、偏好、弱项、验证状态/回执和来源日期。
- 路由/升级/岗位分工分别配置；严格、有限 YAML 与闭合 Schema。选择记录过滤原因和策略哈希，廉价档次优先，岗位排序可编辑。复杂/重要/重大 Canon 约束不能静默降档。
- 跨家族主分析/Red Team 配对；有界升级接口 0→1→2→3，候选缺失或最高档仍不可靠时保留 OPEN QUESTION。自动评估与重新派发不在此阶段。
- 四种模式使用固定 Snapshot 与已有 Runtime，固定四领域首轮独立、同集合交叉审查、综合草案、Red Team、最终综合，共 12 次岗位调用。LeadPlan 为可审查建议，未接入完整 TaskManager 派发。
- ModeAnalysis 闭合结构与 Evidence 引用校验：情景三阶因果链、直接质疑前提/隐含条件/潜在反例、圆桌四岗位证据比较、法庭四领域举证及裁决理由。模式协议最终结果必填；旧单岗接口保持兼容。
- 可信宿主模式配置、逐调用额度预留、失败/取消停止、追加保存模式摘要与岗位回执；不读取 Agent metadata 选择凭据或地址，不审批、不写 Canon、不修改 TaskState。
- CLI 路由检查/选择、模式运行入口与明确合成的离线演示；沿用官方 SDK，无新增网关或模型执行循环。YAML 复用 PyYAML 6.0.3（MIT），相关选型与来源见任务说明及 routing/README.md。

## 离线验证

模式专项测试已通过：四种模式各完成 12 次真实 AgentRuntime 的合成 Adapter 调用，检查相同 Snapshot、无首轮答案泄露、交叉审查输入一致、新业务 ID、追加保存、无生产 world 写入和未请求审批。另验证失败停止、预算不足、无不同家族审查者、模型/profile 不一致、配置中夹带密钥、因果跳阶、重复岗位/领域、未知 Evidence 与必填最终 ModeAnalysis 拒绝。

路由验证覆盖禁用/未验证/legacy、廉价档次与可编辑偏好、容量/工具/预算/延迟、不同家族、升级终止和危险 YAML。新旧 Schema 样例与配置的覆盖检查按实际集合验证，不再固定旧 Schema 数量。当前共 36 个 Schema、七个岗位契约。

2026-10-06 最终执行全套 146 项 unittest，全部通过；新模式及回归均通过真实本地文件存储/契约校验，SDK 测试使用假模型，不调用付费 API。验证 36 个 Schema 的离线引用、七个岗位契约、12 条模型登记、路由 CLI、未启用真实模式拒绝、Python AST、样例 JSON、空值 .env.example、忽略规则和 git diff --check。生产 world 仍仅 world.json。

独立执行 `examples/offline_modes.py` 也完成四种模式，回执分别为 RUN-221cfca2-0d76-4f29-81fb-5ec8639c6988、RUN-ba13674d-d648-4125-b0f0-8cdf54352f5c、RUN-1d0c2401-783d-408b-96b4-6b083ee1730f、RUN-432d23d6-4698-48b2-8ae4-d0b60dd0d288。Windows sandbox 会阻止 asyncio 的本地 socket 初始化，测试与离线演示在获准的 sandbox 外运行，没有关闭校验或跳过协议测试。

测试全部为离线协议验收，不能作为真实科学结论或四种模式的真实研究质量验收。初次全套测试只有旧 Schema 数量固定断言失败，更新为实际样例/配置覆盖集合后整套通过；失败未计入通过记录。

## 真实模型接入

通过 ZenMux 原生 Responses / Anthropic Messages，使用既有本地 `.env`。只读 `/api/v1/models` 确认四款 Slug 与 `pricings` 中 USD/perMTokens 条件费率；未将厂商直连价格当作网关价格。Claude 使用本机忽略配置中的显式代理，未提交个人代理默认值。

每次为合成 Canon 的 Researcher smoke：真实调用一次 canon.read，然后返回空事实/Evidence 集的 ResearchResult，六个业务身份、Schema、工具与结果 Artifact 校验通过。工具回执不是科学 Evidence。

| 模型 | 成功 AgentRun | 输入/输出 token | 结果 SHA256 |
| --- | --- | --- | --- |
| GPT-6 Luna | ARN-3eeaa263-4b16-42f8-8b74-3354b526de0f | 15536 / 322 | 52e67ef58c5c07df88c02324ce1f63b0d0dddfd01cf0c9c16f3bc568cabbf4d0 |
| Opus 5.5 | ARN-99cbc203-8987-4325-87f8-1834d5c8b64e | 26448 / 576 | 9cb8998f4180fa5a023bd62ec84fd1cb613b34e1a410105b3cd5945539731851 |
| GPT-6.1 Sol | ARN-8e21fee2-5c8d-409e-a75b-93a3da82077c | 15535 / 331 | fdc3a9005e406817c0b99993a717c6c1c50d4de30ba6fc42a5f6f38a9c02a54e |
| Sonnet 5.5 | ARN-7d839051-58e1-4ecd-a9f6-78bfde33fa4e | 27504 / 390 | 76c54ea4c902099059886c459186a32eb548786d96594be0d90b507c1abd8038 |

本批 Sonnet 首次 ARN-6889b5b3-b942-48c1-bd0d-024709050fc0 已真实读取工具，但最终输出未通过校验，记录 failed、无结果 Artifact。SDK 费用报告 $0.0425942；失败原因不从模型用量推断，未保留首次候选文本。之后仅重试该模型一次，附明确 JSON 模板，成功；不把第一次失败改写成成功。

费用预留含 Phase 6 为 $1.9049，低于 $2。各单次额度：Luna $0.05、Opus $0.35、Sol $0.8、Sonnet 两次各 $0.3；预留不因失败/未知用量退款。Opus SDK 报告 $0.17910375，Sonnet 重试 $0.055916。采用公开最高文本/缓存写入费率估算 OpenAI 两次，再加已确认 Phase 6 和 Claude 三次 SDK 报告，通过 Decimal 脚本得到累计参考 $0.46927945；这是混合账单确认与保守估价，并非最终 ZenMux 实扣金额。没有整轮模式调用、Fable/Astra/DeepSeek 调用或自动追加付费重试。

真实原始岗位、工具、完成记录保存在忽略的本地缓存，文档仅保存业务身份、用量与哈希；密钥不进入 Git。上述成功证明模型/SDK/工具/JSON 接入，不证明所有岗位、模式、长上下文、真实科研或初始模型分工的质量已经完成模型评测。

## 留给后续

Phase 10 完整 TaskManager、自动计划派发与结果升级、人工审批和 Canon Apply；Phase 11 重试/恢复与执行认证；后续 LangGraph 与项目评测。通用计算执行器、MATLAB、通用 Web 搜索服务选型、工具对外 MCP 包装仍未实施。重要审查若需要 Tier 2 且 Opus 是唯一该档家族，或要求禁用 Tier 3，将保留 OPEN QUESTION，需要操作者启用并验证适用候选后继续。
