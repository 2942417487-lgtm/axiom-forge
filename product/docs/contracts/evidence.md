# Evidence Ledger 与 provenance

Evidence Ledger 是 `world/evidence/EVD-<UUIDv4>.json` 文件集合，便于 Git 审查。每条记录保存 source claim ID、实际证明内容、适用条件、未证明内容、可信度及理由、支持的 Claim/实体 ID、来源读取记录和更新时间。

## 来源字段

`source` 包含 `source_type`、`title`、`url`、`authors`、`journal_or_conference`、`year`、`doi`、`date`。来源 URL 必须是绝对 HTTP(S) 地址。论文必须有作者、期刊或会议和年份；DOI 可以明确为 null，但来源 URL 不能省略。来源日期不明确时为 null，不凭猜测填入。

`what_was_actually_demonstrated` 限定直接结果；`applicable_conditions` 描述适用环境；`what_it_does_not_demonstrate` 记录不可延伸结论。`confidence` 是 0–1 的人工/研究者判断，必须同时给出理由，不表示仪器统计置信区间。

## 来源读取状态

| verification.status | 意义 |
| --- | --- |
| unverified | 尚未通过工具读取原始来源，不可支撑 FACT/INFERENCE |
| source_read | 已记录真实读取：accessed_at、method、locator、excerpt 均需填写 |
| synthetic | 测试资料，永远不可支撑 FACT/INFERENCE |

`method` 描述实际使用的搜索/读取工具；`locator` 定位页码、节号、表格或段落；`excerpt` 为简短直接摘录或精确结果描述，应遵守来源版权限制。不要只填论文标题或说“模型记得”。模型未执行工具时不得标记 source_read。

验证器检查记录格式与关联，并不能证明网页被实际访问或内容真实。记录的 source_read 不自动使所有结论成为 FACT：研究者与独立审查仍需判断来源是否直接支持 claim、适用条件是否相同、推导是否合理。真正的搜索与来源抓取在 Phase 5 接入。

## 输出类别

| category | 使用条件 |
| --- | --- |
| FACT | 来源直接支持；必须引用记录过来源读取的 Evidence |
| INFERENCE | 从 FACT 与明确假设推导；必须引用记录过来源读取的 Evidence |
| ENGINEERING ASSUMPTION | 工程尚未实现，但合理条件明确 |
| SPECULATION | 世界观推测 |
| CONFLICT | 与 Canon 或 Evidence 存在冲突 |
| OPEN QUESTION | 资料不足，保持开放 |

每个 Claim 保存 `claim_id`、`category`、`statement`、`evidence_ids`、`entity_ids`、`reasoning`、`assumptions`、`uncertainty`、`counterexamples`。完整链条为：结论 → Evidence → Source → Reasoning → Assumptions → Uncertainty → Counterexamples。

引用 Evidence 时，该 Claim ID 必须出现在 Evidence 的 supported_claims 中。Evidence 的 claim_id 本身也须在 supported_claims 中；来源主张可以先进入 Ledger，再被 Canon Claim 引用，不要求所有 source claim ID 已进入 Canon。生产 Ledger 的 supported_entities 引用的实体必须存在；任务内可以引用提案集中明确给出的新实体。

任务内 ResearchResult 可以提供新的 Evidence，无需先写回固定快照。相同 evidence_id 对应不同记录会被拒绝；研究结果与快照合并的有效 Evidence 只用于该任务校验，不自动改写正式 Ledger。
