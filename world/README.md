# World 数据层

`world.json` 保存项目自行生成的 world_id、名称和创建时间。当前知识库为空；没有预置设定、人物、历史或现实科学 Evidence。

## 保存规则

每个实体为一个 UTF-8 JSON 文件，直接放入所属目录，文件名等于实体 ID；不在域目录内继续嵌套文件夹。所有 JSON 禁止重复键与 NaN/Infinity。时间使用带时区的 ISO 日期时间（如 `2026-10-03T00:00:00Z`），来源日期使用 `YYYY-MM-DD`，未知来源日期明确为 null。

| 目录 | ID 前缀 | Schema |
| --- | --- | --- |
| canon/physics | PHY | canon_entry |
| canon/astronomy | AST | canon_entry |
| canon/technology | TECH | canon_entry |
| canon/engineering | ENG | canon_entry |
| canon/economy | ECO | canon_entry |
| canon/society | SOC | canon_entry |
| canon/politics | POL | canon_entry |
| canon/history | HIS | canon_entry |
| timeline | TML | timeline_event |
| actors | ACT | actor |
| assumptions | ASM | assumption |
| evidence | EVD | evidence |
| audits | AUD | audit |
| decisions | DEC | decision |
| snapshots | CANON 内容哈希文件名 | canon_snapshot |

实体支持 `TECH-001` 这类人工分配的序号，必须全域唯一且与所属域前缀一致。自动生成使用 `TECH-<UUIDv4>`，避免并行分配序号冲突。不得重复利用已存在或已被快照引用的实体 ID。

## Canon 状态

| 状态 | 含义 |
| --- | --- |
| Hard Canon | 经作者确认的重要设定；变更必须人工批准 |
| Soft Canon | 暂定设定，仍须显式提出重要变更 |
| Assumption | 推演中明确声明的假设 |
| Derived Fact | 从已有事实和明确假设推导，必须保留 Evidence 与推理 |
| Speculation | 世界观推测，不能当作现实事实 |
| Open Question | 信息不足，保留待研究问题 |
| Contradiction | 发现冲突，等待审查或处理 |

Canon 状态与输出事实类别是不同维度：Hard Canon 可以是作者批准的虚构前提，并不自动成为现实 FACT。`status` 不替代来源与证据分层。

条目字段：`entity_id`、`domain`、`title`、`statement`、`status`、`source`、`dependencies`、`implications`、`conflicts`、`evidence_ids`、`claims`、`last_updated`。引用必须存在；Claim 使用的 Evidence 必须同时列入条目的 evidence_ids。Derived Fact 至少有一个 Claim 和 Evidence。

## 快照

执行 `python -m axiom_forge snapshot create`：验证当前世界数据，然后把 world metadata、全部 Canon、Timeline、Actors、Assumptions、Evidence、Audits、Decisions 作为自包含数据保存到 `snapshots/CANON-<SHA256>.json`。

每个文件的规范化 JSON 哈希进入按路径排序的 manifest；world_id 与 manifest 决定 canon_version。创建时间与随机 snapshot_id 不参与内容版本，所以相同数据复用同一快照文件。JSON 键顺序和排版变化不改变版本；条目文本、时间或 metadata 改变则产生新版本。

快照先完整写入临时文件并同步，再原子发布，已有文件验证后复用，不覆盖。遇到损坏旧快照报错，交由人工修复；不要静默重写。验证只读取嵌入数据，不依赖当前 live world，所以历史版本仍可独立使用。

任务的 canon_version 必须与嵌入快照一致。哈希检查用于发现数据变化，不是签名或人工批准证明；当前尚无 Canon 写入与人工审批 Runtime。

模板见 `examples/`，其中所有科研内容均明确为测试样例。不得将测试样例直接导入正式知识库。
