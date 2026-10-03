# 合约测试样例

根目录 24 个 JSON 文件为各非公共 Schema 的演示数据，`agents/` 另有 6 个岗位输入样例。全部是人工生成的测试数据，没有实际调用 Agent、搜索来源或进行科学计算。

唯一 Evidence 明确为 `test_fixture` / `synthetic`，Claim 为 OPEN QUESTION。内嵌的世界只用于测试，不是 `world/` 的生产知识库；不得把样例作为真实证据或作者设定。

`task_state.json` 展示一次 Task、一个 Run、六个 Agent Run 与六份输出 Artifact 的关联，以及 pending CanonChange。新增 `agent_input.json` / `lead_plan.json` 展示 Lead 规划；`agents/` 展示独立首轮、Red Team 与最终综合输入。stage、完成回执和 Artifact 哈希均为模拟数据，不证明真实执行、隔离或审批流程。

检查：

```powershell
.\.venv\Scripts\python.exe -m axiom_forge validate task_state examples/task_state.json
```
