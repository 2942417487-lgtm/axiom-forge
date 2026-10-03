# 合约测试样例

此处 21 个 JSON 文件是人工生成的合约演示数据，没有实际调用 Agent、搜索来源或进行科学计算。

唯一 Evidence 明确为 `test_fixture` / `synthetic`，Claim 为 OPEN QUESTION。内嵌的世界只用于测试，不是 `world/` 的生产知识库；不得把样例作为真实证据或作者设定。

`task_state.json` 展示一次 Task、一个 Run、六个 Agent Run 与六份输出 Artifact 的关联，以及 pending CanonChange。它是字段和完整性校验案例，不证明 Phase 4–11 的 Runtime 或审批流程已经实现。

检查：

```powershell
.\.venv\Scripts\python.exe -m axiom_forge validate task_state examples/task_state.json
```
