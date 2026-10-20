# 系统模板与历史空脚手架

templates/world/world.json 是新世界创建模板，其占位身份和时间由 world create 替换。

templates/legacy-world/world 保留此前已提交的空世界脚手架，用于历史追溯和离线测试。它不是正式世界，不自动导入，也不承载研究状态。正式世界必须放在系统仓库之外，使用见 docs/guides/world-workspaces.md。
