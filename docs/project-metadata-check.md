# 项目元数据只读检查

日期：2026-10-10。实现范围：[四字段契约](project-metadata-contract.md) 的格式检查、PRJ 标识生成，以及与世界元数据的身份关联；工程检查记录见 [实施任务](tasks/project-metadata-implementation.md)。

## 命令与检查范围

在系统项目目录运行：

```powershell
# 合成示例：只检查文件格式，不检查世界关联。
.\.venv\Scripts\python.exe -m axiom_forge validate project_metadata examples/project_metadata.json

# 对操作者显式选择的外部目录，检查 project.json 与 world/world.json。
.\.venv\Scripts\python.exe -m axiom_forge --world 'D:\AxiomWorlds\MyWorld' project check

# 显式生成一个 PRJ 标识；只输出字符串，不创建或改写项目文件。
.\.venv\Scripts\python.exe -m axiom_forge new-id project
```

示例路径是用法说明，没有据此操作正式世界。`project check` 必须显式给出外部目录，拒绝系统目录及上下级重叠、链接／重解析路径。它只读两个固定文件，不创建 WorldWorkspace、.axiom/local、登记或审批 Key，不执行 Git、来源程序或模型调用。

这是格式和身份检查，不要求为了检查而创建 Git，也不证明所选目录已经是合格世界 Git 仓库。Git 对象／历史／配置、完整核心知识、现有本机绑定、敏感内容及人工接受仍由后续宿主流程检查；成功不能作为登记、外发或更新许可。原来的 world create／world check／validate-world 继续沿用核心世界规则，不自动创建或强制加入 project.json。

## 字段和读取规则

project_metadata Schema 的顶层恰有 project_format_version、project_id、world_id、display_version，全部必填；仅展示标签可为 null。PRJ／WLD 使用小写 UUID v4，标签为 1–64 个 Unicode 标量，拒绝控制字符、代理码点及首尾 U+0020。不补默认值，不 trim／归一化，不将标签解释为 SemVer 或 Canon 版本。

文件使用严格 UTF-8／无 BOM JSON，拒绝重复键、非有限数字、非 object 顶层、未知字段和不合法 Unicode；继续沿用现有 2 MiB 单文件读取上限，超限停止，不截断。Schema 来自可信 EngineResources 的离线 Registry，不从世界加载规范。

`project check` 额外用既有 world Schema 检查 world/world.json，再核对两个 world_id 精确一致。第二次读取发现字节变化时返回 baseline_changed；这是有限变化检测，不能防止 ABA 变化或证明两个文件的无锁读取为原子快照。

## 输出与诊断

成功退出 0，输出 JSON：status=metadata_valid、scope 及实际输入字节 SHA-256。单文件 scope 为 project_metadata_format；关联检查为 project_metadata_and_world_identity，并额外给出 world_sha256。它们不是 Canon 哈希、Git OID 或仓库宿主回执。

失败退出 1，向 stderr 输出固定诊断 JSON：status、location、message；stdout 无成功结果。location 仅使用固定相对文件／已知字段，不回显来源原值、未知字段名或验证器错误原文。成功也不输出展示标签。未做敏感预检，结构合法的输入仍可能含秘密，不因 metadata_valid 批准外发。

| status | 本步含义 |
| --- | --- |
| metadata_invalid | 格式、必填、类型、ID或标签无效 |
| project_format_unsupported | 字符串格式版本不是精确 1.0 |
| project_fields_unsupported | 存在未知字段或别名 |
| legacy_metadata_missing | 世界元数据文件有效，但 project.json 缺失；不证明完整核心知识已验收，不自动生成 ID／文件 |
| identity_conflict | 两个文件的世界身份不同 |
| inspection_incomplete | 世界元数据无效／未知，路径、权限、缺失或读取限额阻止检查 |
| baseline_changed | 实际重复读取发现输入字节变化 |

检查不改写原件、用户文件、Git、被忽略私人状态或宿主配置。已有源 ID 保留；`new-id project` 仅供操作者显式请求新身份，不能用于检查时自动修复冲突或给既有项目重新分配身份。

## 兼容与尚未实现

新增 Schema 会改变现行可信资源指纹；旧 checkpoint 失配时仍停止，不自动迁移、补签或宣称恢复兼容。现行 Canon 哈希不增加 project.json，展示标签变化不改变核心知识版本。

尚未实现完整产品项目／对话登记、宿主回执／人工接受／更新、安全研究档案、敏感预检、自动元数据创建／迁移及 GitHub 接续；CanonHost 提交批准 metadata 的已知缺口也未在本步修复。本文的只读检查不绕过这些条件。
