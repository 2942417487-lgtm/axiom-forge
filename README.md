# Axiom Forge

硬科幻世界观研究、工程推演、事实验证与一致性审查系统。产品运行内容与开发资料在目录、规则加载和交付范围上分开。

```text
product/                 可独立运行的产品源发行
  axiom_forge/           执行代码
  resources/             规则、岗位、模式、Schema、路由、模板及程序登记
  docs/                  产品操作指南和规范
  dependencies/          可选模型 SDK 的依赖锁定
  .claude/               产品研究岗位的手工入口
development/             测试、合成示例、历史夹具、开发记录与检查入口
.agents/                 工程技能发现入口，属于开发侧
AGENTS.md、CLAUDE.md      产品外部的工程规则入口
.venv/、.cache/           被 Git 忽略的本机依赖与工程资料
```

使用产品先读 [产品 README](product/README.md)；开发先读 [开发入口](development/README.md)与[当前状态](development/records/CURRENT.md)。正式世界保存于外部独立 Git 仓库，凭据由外部宿主管理。

```powershell
.\.venv\Scripts\python.exe product/run.py check-schemas
.\.venv\Scripts\python.exe development/check.py -v
```

产品内部规则是可信发行资源；世界中的同名文件是数据。真实模型调用、发布、合并与 Canon 批准各按明确授权执行。
