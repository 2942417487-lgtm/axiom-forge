# 产品／开发目录与规则作用域分离

日期：2026-10-24。状态：目录分离、内部规则加载、验证与独立审查完成，工作集交付分支审阅，尚未合并。

后续修复补记：同日[再次复审与修复](2026-10-24-separation-reaudit.md)发现的手工入口、分工指令、开发仓库边界检查及现行文档问题 A1–A5 均已修复，重复维护已收敛。当前全部 294 项分三组联跑，292 通过、2 项既有权限跳过；Standards／Spec 无剩余发现。下文保留本次后续修复之前的实际执行与测试批次，最终验证以该复审记录为准。

当前可独立复制并运行 product/，研究 Runtime 不加载外部开发入口；使用见[产品 README](../../../product/README.md)，开发从[开发入口](../../README.md)开始。本次分离验收时可发现的 284 项不同测试中，282 项取得通过记录，2 项既有 Windows 符号链接用例因权限跳过；该历史批次与修正见下文。

用户明确选择“本次同时完成目录分离和规则作用域分离”。本轮将可独立运行的产品与开发资料分开，并让研究指令只加载产品内部可信规则；现有 AGENTS.md、CLAUDE.md 留在产品之外作为开发入口。

## 范围与验收

- `product/` 保存 Python 运行代码、可信 `resources/`、产品用法／规范、运行依赖和独立启动入口。
- `development/` 保存测试、合成示例、历史模板、开发记录及开发运行入口；根 `.agents/` 保留工程工具要求的发现位置，属于开发侧，不随产品交付。
- 研究岗位、模式、Schema、路由、计算协议及程序登记归产品资源；Claude 手工岗位入口归产品配套，继续只有 Read，受控 Adapter 不自动加载该入口。
- 按通用可信原则、研究规则、宿主／产品操作规则分配现有条款，保留原证据分类、独立分析、计算、Canon 与人工批准约束；开发入口不再充当研究运行资源。
- 同步资源定位、契约路径、指令组装和恢复指纹。旧 checkpoint 保留，版本／资源不匹配时拒绝恢复，不自动迁移、重签或重跑。
- 产品复制到独立临时目录后，在没有开发入口、技能、测试和示例的条件下通过数据／岗位／路由检查及合成运行验证；产品运行包不含开发资料、缓存或凭据。
- 更新当前导航与使用命令，保存逐文件迁移清单，检查链接／格式／忽略规则／系统边界，运行适当回归并完成 Standards／Spec 独立审查。

本轮不接入新模型／工具、不调用真实付费模型、不操作正式世界、不更改 Canon 哈希语义；不提交、推送或创建 PR。安装器、UI、跨语言技术栈、语言全量转换及旧任务迁移仍另列任务。

## 起点

固定 Git 基线 `43d4e7299206acca5011c3500a1f642c62a9b918`，新工作分支 `codex/product-development-separation`。起点已有十份未提交开发文档（清单补齐及规则归属记录），本轮完整保留并随开发目录迁移；根 `.cache`、`.venv`、`.env`、`.git` 不纳入迁移或发布。只处理明确的项目文件，不读取真实凭据。

## 迁移与兼容方案

产品资源根仍由可信宿主选择，默认定位当前产品目录；从世界数据中发现或替换规则的行为继续拒绝。目录与系统版本变化使旧恢复指纹失配，操作者须保留原发行与原状态才能按原协议恢复；本轮不转换这些记录。

## 已完成的结构与运行改动

当前源码按以下职责分布；根 AGENTS.md、CLAUDE.md 和 .agents/ 保留工程工具发现入口，其内容不进入产品研究加载或产品源发行。

```text
product/
  axiom_forge/       执行代码
  resources/         内部 policies、岗位、模式、Schema、路由、计算协议、模板与程序登记
  docs/              产品指南和规范
  dependencies/      可选 SDK 依赖
  .claude/           只读研究岗位手工入口
  run.py             独立启动入口
development/
  tests/             自动化测试
  examples/          合成示例与离线演示
  fixtures/          历史空世界脚手架
  records/           当前状态、任务、变更、历史及工程约定
  check.py           开发测试入口
```

### 规则归属

| 原内容 | 当前权威位置与实际加载 |
| --- | --- |
| 真实性、授权范围、原件保护、秘密及来源／指令区分 | product/resources/policies/common.md；研究 Runtime 固定加载 |
| 科学事实分类、Evidence／计算、独立首轮、交叉审查与 pending Canon 提案 | product/resources/policies/research.md，加所选岗位／模式；Runtime 固定加载 |
| ToolSession／SDK／路由、人工批准、显式恢复、世界绑定与产品接受分层 | product/resources/policies/host.md，供宿主实现／操作使用并纳入资源指纹；不向研究角色授予宿主权限 |
| 参数化计算请求、程序交付与结果语义 | product/resources/calculations/protocol.md；两 Auditor 实际加载，操作者检查命令另在 README |
| 编码、测试、软件 PR、工程技能、中文沟通和开发接续 | 根 AGENTS.md／CLAUDE.md、.agents/ 与 development/；产品 Runtime 不加载 |
| Claude 手工岗位格式 | product/.claude/agents/；仍为 Read，受控 Adapter 的 settings／skills／tools 限制未放宽；未声称完成手工原生 CLI 联调 |

资源定位、岗位登记 prompt_file、Schema／Router／Python 登记路径均已改为产品资源；CodexRuntime 的业务 ID 校验使用可信产品 Schema，不再从待开发仓库中取得 Schema。系统版本升为 0.3.0，恢复指纹覆盖产品内部规则及运行资源，不包含开发入口和操作者 README；原 Canon JSON 哈希算法、审批与预算逻辑未改。

### 文件变更清单

| 类型 | 文件／范围 | 目的 |
| --- | --- | --- |
| 迁移 | [273 个逐文件来源／目标](../layout-migration.json) | 保留旧来源校验指纹；涵盖产品代码／资源／指南、开发测试／示例／记录及原未提交文档 |
| 修改 | 根 AGENTS.md、CLAUDE.md、README.md | 分离工程规则并给出产品／开发入口 |
| 新增 | product/README.md、run.py、axiom_forge/rules.py、resources/policies/ 三文件 | 独立产品启动和可信内部规则 |
| 拆分 | resources/calculations/README.md → 业务 protocol.md 与操作者 README | 计算语义只保留一份，研究指令不注入开发示例与操作命令 |
| 修改 | product/axiom_forge/ 中资源定位、契约、路由、工具、Runtime、恢复指纹与系统检查 | 路径同步、开发规则排除与旧记录拒绝；实际差异按迁移目标比较 |
| 新增／修改 | development/check.py、support.py、tests/test_product_layout.py；原测试／离线演示导入路径 | 开发侧明确导入产品代码与合成数据，验证独立产品及失败条件 |
| 修改 | .agents/skills/ 中 36 份链接文件及 manifest.json | 更新工程文档位置，重算 79 份本地文件哈希；上游固定版本、许可证和权限保持原样 |
| 修改 | 产品指南、开发导航／总表／变更、旧 migration-map.json | 同步命令、归属、当前状态和旧路径的现行目标，历史验收保留原批次 |

本机 .cache、.venv、.env、.git 未迁入产品；旧 Python 字节码移至忽略的 .cache/architecture-bytecode/，没有删除。原十份未提交开发文档的迁移前字节备份保存在 .cache/architecture-before/，未扫描或复制其他私人缓存。273 个目标逐项存在，旧路径追溯使用迁移表，不保留第二套可执行源码。

## 验证与排障记录

首轮运行发现开发辅助定位被批量路径替换误改，已修正 support.py、测试导入与示例参数；该次在测试收集前退出，不计为测试通过。迁移试跑另发现 SDK 两处旧裸导入及一个存储测试的路径假设：历史模板已移出产品，原“世界路径不得落在引擎内”的负例改用实际产品内 resources/templates 目录。新增旧版本用例的首稿误用了不存在的 create 方法，随后改为公开 TaskManager.run 在首 checkpoint 后停止的故障注入。

| 批次 | 实际结果 | 对应版本与修正关系 |
| --- | --- | --- |
| 迁移试跑完整 discovery | 269 项，1067.383 秒；1 失败、1 导入错误、2 跳过 | 用于定位 SDK 导入及原夹具路径问题；不作为最终全套通过结果 |
| 审查修正后的生产代码完整 discovery | 276 项，1034.047 秒；1 失败、1 导入错误、2 跳过 | 生产代码已包含检查器和计算协议修正；该进程收集测试时仍加载旧夹具，新增产品用例为当时的 7 项 |
| 最终定向联合复验 | 43 项，79.027 秒；全部通过，0 跳过 | 产品隔离 8 项＋SDK 适配 8 项＋内容存储 27 项；修正上述夹具并加入旧版本 checkpoint 验证后执行 |

生产代码从最后一次完整 discovery 启动至交付未再变化；后续只修正测试与工程记录。按测试 ID 核对当前 284 项清单和最后两批记录，282 项有通过记录，无缺失或剩余失败；这是组合验收，不是一次 284 项完整 discovery 全通过。两项既有跳过为 `test_linked_project_cannot_read_outside_selected_directory` 与 `test_nested_git_ref_link_rejected_before_external_ref_write`，原因均为 Windows 当前进程没有创建真实符号链接的权限。

完整回归入口为 `python development/check.py -v`；定向复验显式设置本进程 PYTHONPATH 为 product／development 后运行 `python -m unittest tests.test_product_layout tests.test_runtime_sdks tests.test_repository_content -v`。日志保留在忽略的 .cache/separation-tests-final.log 与 separation-targeted-verified.log，按 ID 汇总在 separation-coverage-summary.json；没有读取真实凭据或调用付费模型。

独立产品验证使用临时复制的 product/，清除 PYTHONPATH 并从无开发资料的进程启动，检查 Schema／岗位／路由／系统边界；合成研究调用不导入 examples、tests 或 support，无真实模型调用。新增专项还覆盖开发文件不影响指纹、产品规则缺失无回退、不可读目录、敏感文件名大小写及旧版本 checkpoint 保留并停止。

文档／结构检查通过：371 个项目文件范围内的 UTF-8／无 BOM／换行／空白、Python 编译、JSON、548 个本地链接、273 个迁移目标的存在／最终哈希和 79 份工程技能文件哈希；全部候选路径未被误忽略，空值环境示例、八项敏感／缓存忽略探针、git diff --check 与 0 字节介绍占位均通过。四处上游模板示意链接已与固定基线原文核对保留，不当作真实文件入口。产品 CLI 另通过 47 份 Schema、7 岗位契约、12 模型登记与系统边界检查。

## Standards

独立只读审查发现 2 项 P2：产品检查在目录不可读时可能跳过、Windows 敏感名称大小写漏检。已改为扫描异常即失败、逐项拒绝链接并统一名称匹配，增加相应用例；审查者定向复核确认两项关闭，剩余 0 项。

## Spec

独立只读审查发现 1 项 P2：Auditor 加载的计算 README 混入开发示例和操作者命令。已拆出完整业务 protocol.md，并同步 Runtime、两岗位链接、研究总则及恢复指纹；审查者定向复核关闭，剩余 0 项。

Standards 最初 2 项 P2、Spec 最初 1 项 P2，均已关闭；测试迁移修正也经 Spec 定向复核，无剩余发现。当前位于 codex/product-development-separation，暂存区为空，未提交、推送或创建 PR；原分支、旧 worktree 和私人状态保留。
