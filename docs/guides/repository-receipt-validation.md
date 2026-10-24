# 仓库宿主回执数据校验

本接口检查[回执契约](../contracts/repository-host-receipts.md)的数据格式与链内关联。调用者提供可信引擎 Schema 及原始字节；成功结果固定包含 `execution_authorized=false`。宿主人工验证、可靠保存、登记／更新执行器另行实现，进度见[当前任务](../development/tasks/2026-10-23-repository-receipt-foundations.md)。

## 单份文件

```powershell
.\.venv\Scripts\python.exe -m axiom_forge validate repository_preparation_receipt examples/repository_preparation_receipt.json
.\.venv\Scripts\python.exe -m axiom_forge validate repository_inspection_receipt examples/repository_inspection_receipt.json
.\.venv\Scripts\python.exe -m axiom_forge validate repository_acceptance_receipt examples/repository_acceptance_receipt.json
.\.venv\Scripts\python.exe -m axiom_forge validate repository_operation_receipt examples/repository_operation_receipt.json
.\.venv\Scripts\python.exe -m axiom_forge new-id repository_operation
.\.venv\Scripts\python.exe -m axiom_forge new-id repository_receipt
```

`repository_operation_receipt` 对应 `receipt_kind=operation_result`。文件读取使用现有路径／链接检查及 2 MiB 上限，要求 UTF-8、无 BOM、唯一键、有限数值和有效 Unicode；错误不回显来源值、未知键名或所选文件路径。单份检查只报告格式结果与实际原字节哈希，不解析其外部引用。`sequence=1.0` 即使符合 JSON Schema integer 也会被业务检查拒绝。

示例均为合成数据，包含虚构的接受与结果字段，只用于离线测试。修改前一份示例的空白也会改变原字节哈希；后续 ReceiptRef 必须随实际字节更新。不要对已保存回执重新序列化后继续沿用旧哈希。

## Python 接口

```python
from pathlib import Path
from axiom_forge.validation import SchemaStore
from axiom_forge.repository_receipts import (
    parse_receipt, validate_receipt_chain,
    validate_content_reference, validate_git_commit_reference,
)

# 指向操作者选择的可信系统资源，不从世界文件取 Schema。
engine = Path.cwd()
schemas = SchemaStore(engine / "schemas")
names = ("preparation", "inspection", "acceptance", "operation")
raw = [(engine / "examples" / f"repository_{name}_receipt.json").read_bytes()
       for name in names]
data = parse_receipt(raw[0], schemas)
report = validate_receipt_chain(raw, schemas)
assert report["terminal"] is True
assert report["execution_authorized"] is False
```

| 接口 | 检查内容 | 返回 |
| --- | --- | --- |
| `parse_receipt(raw, schemas)` | 严格字节解析、对应 Schema、单份数据语义 | 回执 dict；字段仍是待宿主验证的数据 |
| `validate_receipt_chain(raw_receipts, schemas)` | 按输入顺序检查 1–4 份回执、阶段／ID／序号、ReceiptRef 原字节哈希及内容绑定 | 范围明确的报告，`terminal` 表示末项是否为结果回执 |
| `validate_content_reference(reference, raw, schemas)` | ContentRef 形状和显式提供字节的 SHA-256；字节上限 2 MiB | 通过返回 `None`，失败抛 `DataError` |
| `validate_git_commit_reference(reference, schemas)` | sha1／40 位或 sha256／64 位小写 OID 形状 | 通过返回 `None`，失败抛 `DataError` |

链可停在 preparation、inspection 或 acceptance，作为未结束的前缀；结果回执为终态。链验证拒绝重复身份、断序、跳过阶段、跨操作、错误前驱、缺失／替换的阶段引用，以及同 ContentRef 身份对应不同哈希。

接受回执须匹配本链 eligible 校验、请求类型、完整审查投影、来源捕获、目标基线、覆盖、写投影与准备策略。结果须引用本链实际存在的校验／决定；登记／更新成功还须有 accepted 决定、写前意图和 before／after 引用。停止结果可记录已变化的实际基线，未知结果要求诊断与 `manual_reconcile`。

结果的 `before_ref` 可以指向宿主复核时新保存的实际基线记录，不要求复用 inspection 的记录 ID；其实际内容是否仍符合已接受基线，由宿主核对。

`already_current` 可以引用宿主原有的已接受基线，而无需本链新建接受回执；是否存在有效基线须由未来宿主核对。此数据接口不读取 ContentRef 的宿主记录／分块清单，不核实登记类型、权限、检查覆盖、实际 Git 对象、保存完成或目标副作用。`terminal=true` 仅说明数据链已结束。
