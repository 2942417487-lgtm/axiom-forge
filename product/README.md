# Axiom Forge 产品

本目录包含独立运行所需的代码、可信资源、产品指南及依赖声明。复制本目录不需要开发记录、测试、合成示例或外部 AGENTS.md／CLAUDE.md；本机虚拟环境和凭据不属于产品。

需要 Python 3.11+ 和已安装的锁定依赖。于本目录执行：

```powershell
python -m pip install -r requirements-lock.txt
python run.py check-schemas
python run.py check-contracts
python run.py routing check
python run.py check-system-boundary
```

也可从其他目录指定 run.py 的路径启动。可选模型 SDK 依赖见 [Runtime 指南](docs/runtimes.md)与 dependencies/runtimes/requirements-lock.txt；没有安装器或自动依赖下载功能。

check-system-boundary 检查当前产品目录。源码仓库的 Git 跟踪文件检查由开发入口 development/check.py 承担，产品不会向父目录搜索或依赖开发仓库。

世界先以 world create --path <外部空目录> --name <名称> 创建，再用 --world <外部世界目录> 显式操作；全局 --world／--engine-root／--host-root 放在子命令之前。--engine-root 指本产品根目录，其中必须包含 resources/，不兼容旧混合资源布局。

详情见[文档导航](docs/README.md)、[世界工作区](docs/guides/world-workspaces.md)、[任务管理](docs/guides/task-management.md)、[恢复](docs/guides/recovery.md)。规则归属见 [common](resources/policies/common.md)、[research](resources/policies/research.md)、[host](resources/policies/host.md)。

系统版本 0.3.0 使用新的目录与规则指纹；旧任务保留，资源或版本不匹配时拒绝恢复，不自动迁移、重签或补写批准。运行根／规则与开发资料分离是应用和交付边界，不是 OS 文件隔离。
