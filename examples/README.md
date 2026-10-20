# 合约测试样例

根目录的 JSON 文件为各非公共 Schema 的演示数据，`agents/` 另有 6 个岗位输入样例，`calculations/` 有经济成本请求和两个携带待执行请求的岗位结果，`tools/` 提供宿主配置与 Canon 读取参数。全部是人工生成的测试数据，没有实际调用 Agent、搜索来源或进行科学计算。

tool_result 展示 unavailable，不是搜索成功回执。宿主配置示例不包含真实凭据/资料路径，Python 默认关闭；其中 capability 授权仅用于操作者调用演示，不是可由模型提交的权限申请。工具真实联调记录位于本地忽略的 .cache/，不混入这些静态样例。

calculation_request、calculation_model、calculation_result 展示未执行请求、planned 模型和 needs_implementation 返回结构；不能用这些文件声称已有计算程序或真实成本结果。

唯一 Evidence 明确为 `test_fixture` / `synthetic`，Claim 为 OPEN QUESTION。内嵌的世界只用于测试，不是 `world/` 的生产知识库；不得把样例作为真实证据或作者设定。

`task_state.json` 展示一次 Task、一个 Run、六个 Agent Run 与六份输出 Artifact 的关联，以及 pending CanonChange。`agent_input.json` / `lead_plan.json` 展示 Lead 规划；`agents/` 展示独立首轮、Red Team 与最终综合输入。stage、完成回执和 Artifact 哈希均为模拟数据，不证明真实执行、隔离或审批流程。

检查：

```powershell
.\.venv\Scripts\python.exe -m axiom_forge validate task_state examples/task_state.json
```
