# 系统开发资料

本目录保存测试、合成示例、历史夹具与工程记录，不随 product/ 产品源发行复制。根 AGENTS.md／CLAUDE.md 与 .agents/skills/ 也是开发侧入口；保留工具要求的发现位置。

先读[当前状态](records/CURRENT.md)、[任务总表](records/TASKS.md)及当前任务，再按[工程技能说明](records/skills/README.md)工作。用户既有修改与私人恢复状态必须保留。

```powershell
.\.venv\Scripts\python.exe development/check.py -v
```

check.py 明确配置 product/ 与 development/ 的导入路径。tests/ 是离线回归，examples/ 是合成数据／临时世界演示，fixtures/legacy-world/ 是历史空脚手架，records/ 保存开发过程。产品代码不导入这些资料。

测试开始前，check.py 必须先检查明确的源仓库 Git 索引和根 world/，失败即停止；只读文件名，不读取凭据值。只做这项检查可运行 `python development/check.py --boundary-only`。产品自己的目录检查仍由 product/run.py check-system-boundary 提供。

逐文件目录迁移见 [layout-migration.json](records/layout-migration.json)；旧开发文档位置通过 records/migration-map.json 和该清单追溯，不重建旧目录。模型真实接入与离线回归分别记录。
