# 宿主内容存储

`RepositoryContentStore` 为一次 RPO 操作保存不可变的 ContentRef 内容。原始字节、记录类型、操作归属、长度和 SHA-256 在同一 SQLite 事务提交，再通过独立连接复读后返回引用。选型依据见后端比较（开发记录随源码仓库提供），实现验收见开发任务（开发记录随源码仓库提供）。

## 创建与读取

调用者应是可信宿主程序，显式提供本机私人目录和已选择的世界目录。世界目录须已存在；存储目录与系统、世界目录互不包含，且不能位于 Git 仓库中。数据位置为 `<host>/repository-operations/<RPO>/content.sqlite3`。

```python
from pathlib import Path
from axiom_forge.ids import new_id
from axiom_forge.repository_content import RepositoryContentStore

# 由操作者替换为独立的本机路径，不从来源内容或世界文件读取。
host = Path(r"D:\AxiomHost")
world = Path(r"D:\AxiomWorlds\Example")
operation_id = new_id("repository_operation")
store = RepositoryContentStore.create(host, operation_id, world_root=world)
reference = store.put("checks", b'{"synthetic":true}\n')

# 构造器只打开已有库；不会初始化缺失的库。
reopened = RepositoryContentStore(host, operation_id, world_root=world)
raw = reopened.read(reference, expected_kind="checks")
assert raw == b'{"synthetic":true}\n'
```

代码中的内容为合成示例。接口不会构造 WorldWorkspace、读取世界资料、初始化审批 Key 或调用研究工具；没有新增 Agent 工具或 CLI 存储命令。

| 接口 | 完成条件 |
| --- | --- |
| `create(host_root, operation_id, *, world_root, engine=None)` | 独占创建文件；Schema／操作／本机位置元数据事务提交，独立连接复核通过 |
| `RepositoryContentStore(host_root, operation_id, *, world_root, engine=None)` | 打开已有文件，检查 SQLite 结构、精确表定义、版本、操作及位置绑定 |
| `put(record_kind, raw)` | 新生成 UUID，提交类型／操作／字节及哈希，关闭写连接并复读成功后返回 ContentRef |
| `read(reference, *, expected_kind)` | 核对引用形状、期望类型、本操作归属、长度及实际原字节 SHA-256，返回 `bytes` |

`engine` 沿用现有可信 EngineResources 入口。类型由代码中的 `RECORD_KINDS` 固定，涵盖回执各 ContentRef 对应的记录类别。`checks`、`host_verification` 等只是类型标签，接口不解释其 JSON，也不验证其中的真实检查或人工决定。

## 不可变与错误处理

每次追加生成新记录 ID，相同字节可保存成不同记录；已有 ID 冲突会失败。没有替换、删除、迁移或自动重试接口。复制到其他路径或操作下的库会因位置／归属失配停止，不自动重绑。

单份原字节上限为 2 MiB，超限直接拒绝；本阶段不提供分块和总存储配额。宿主应控制调用数量、磁盘空间及 OS 私人目录权限。引用不接受来源路径；创建前及每次访问时检查祖先链接、重解析点、硬链接、日志路径、目录重叠，以及普通 Git／裸库布局。

`ContentStoreError.code` 是固定状态，`cause_code` 在保存不确定时给出固定原因；错误消息不包含内容、所选私人路径或 SQLite 原始诊断。

| 状态 | 调用者处理 |
| --- | --- |
| `record_size_or_type_invalid`／`record_kind_invalid`／`record_reference_invalid` | 修正请求；尚未开始本次追加 |
| `store_exists` | 原库保留，确认归属后用构造器打开 |
| `store_path_invalid`／`store_context_mismatch`／`store_format_unsupported` | 检查路径、位置绑定或格式；不迁移、不重签 |
| `record_missing`／`record_context_mismatch`／`record_corrupt`／`store_corrupt` | 保存现状，核对引用、类型、操作及备份；不补造记录 |
| `store_unavailable` | 检查文件、权限、锁或 SQLite 可用性；接口未自动重试 |
| `initialization_unconfirmed` | 初始化／复读失败，可能留下空库或已提交的库；保留文件并单独核对 |
| `write_unconfirmed` | 本次追加未取得完整保存确认；用异常的 `reference` 显式读取核对，不直接重复追加 |

数据库锁等待配置为一秒。读操作使用只读连接；打开已有库时允许 SQLite 恢复自身未提交的 rollback journal，范围仅为这份存储，不重放仓库任务、回执或人工接受。日志由 SQLite 管理，接口不手工清理。

## 验证与部署条件

每个写连接核对 DELETE 日志模式、EXTRA 同步；所有连接关闭并核对 `trusted_schema`。结构检查和按引用哈希检查分别检测库结构与所读记录损坏，不用 mtime／文件大小代替内容校验。提交后复读确认当前实际可读取的结果。

适用于可靠本机文件系统；物理断电、存储设备故障、网络文件系统和活跃库备份方案未验收。路径检查依赖宿主 OS 权限，同权限进程可改写未被外部锚定的库；记录和普通哈希均不提供人工身份验证。分块、回执持久化、人工接受、防重放和世界登记／更新仍由后续阶段完成。
