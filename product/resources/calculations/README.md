# 计算协议与操作者检查

研究岗位使用 [完整计算协议](protocol.md)，Runtime 只加载该协议，不加载本页的命令示例。

合成计算示例另在源码开发资料 development/examples/ 中提供，产品运行不依赖这些文件。

## 目前能验证什么

现有 `validate <schema> <file>` 能检查新增三类 JSON 的结构、类型与基本状态约束。能拒绝把缺工具请求写成 completed 却没有回执，也能拒绝 planned 模型携带虚假源码定位。

现有校验不包含通用计算协议语义执行器：request/result 之间的身份与哈希关联、参数名唯一性、矩阵规则性、上下界关系、单位转换、模型版本匹配、情景覆盖、输出全集与所有验收条件的执行，须在后续实现中检查。request 内声明 auto_if_available_else_handoff 不提供工具授权，也不能突破项目权限。

```powershell
python run.py validate calculation_request <外部输入目录>/calculation_request.json
python run.py validate calculation_request <外部输入目录>/calculations/economic-cost-request.json
python run.py validate calculation_model <外部输入目录>/calculation_model.json
python run.py validate calculation_result <外部输入目录>/calculation_result.json
```
