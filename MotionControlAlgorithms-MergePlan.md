# MotionControlAlgorithms 合并计划

- 计划状态：**延期（DEFERRED）**
- 当前优先级：**非当前最高优先级**
- 当前项目主线：根任务 `00-01｜全库资产盘点与基线`
- 上游项目：<https://github.com/rexyll/MotionControlAlgorithms>
- 目标项目：<https://github.com/rexyll/robot_knowledgebasement>
- 本计划建立日期：2026-11-15
- 计划性质：集成前置条件、实施方案与验收门禁；**不是源码导入授权，也不是合并执行记录**

> **决策摘要：目前不适合把 MotionControlAlgorithms 源码合并进 robot_knowledgebasement，也不应将合并计划提升为当前最高优先级。** 现阶段继续以根计划 00-01 为最高优先级，完成全库资产基线、主张级审计和许可/事实边界治理；同时按第14章 14-EXT-02 关闭第三方依赖、来源和 SBOM 门禁。达到本文件第6节的重新启动条件后，再将本计划提升为最高优先级并进入实际集成。

---

## 1. 历史任务来源与计划演变

已逐份检查 `TaskPlan_History/TaskPlan-2026-11-03.md` 至 `TaskPlan-2026-11-15.md` 共13份每日 TaskPlan。与本项目合并直接相关的历史节点如下：

| 日期 / 记录 | 原计划或进展 | 对当前计划的约束 |
|---|---|---|
| 2026-11-03 至 11-05 | 当日归档未出现 MotionControlAlgorithms 源码合并任务；根主线持续为 00-01 | 不将后续任务倒填为更早已批准的合并决定 |
| 2026-11-06 v7.35 | 首轮纳入审查发现上游根目录没有 LICENSE/LICENSE.md；按 G-08 暂停复制/合并源码，只允许链接和独立知识化 | 许可证缺失是最初的明确阻塞 |
| 2026-11-06 v7.36 | 建立 `TODO-EXT-001` 延期待办：等待上游最后验证完成，再由用户与助手讨论；上游验证完成不自动授权合并 | 合并一直是待讨论任务，不是正在执行的代码合并 |
| 2026-11-07 | 将 TODO-EXT-001 展开为启动条件：用户确认上游验证完成、讨论具体合并范围、重新核验许可证/第三方依赖/目标仓库兼容性/NOTICE/供应链，并形成逐文件清单和可回滚方案；明确不得复制源码、测试、脚本或 benchmark | 保留“范围先确定、准入门先通过、然后授权”的流程 |
| 2026-11-08 至 11-13 | 每日记录多次重申 TODO-EXT-001 未授权合并；知识库根主线仍为 00-01，Stäubli 工程任务作为并行专项推进 | 没有历史证据表明曾批准直接导入或改变根主线优先级 |
| 2026-11-14 | 确认目标仓库为 robot_knowledgebasement；新增 G-25 外部工程项目与知识资产分离治理。用户确认 MotionControlAlgorithms 为原创项目后，上游加入 Apache-2.0 LICENSE、NOTICE 和 README 许可说明；核验 Run #2827 的 Linux、Windows、benchmarks jobs 成功 | 上游根许可证未知阻塞已解除；这不代表第三方依赖、目标仓库兼容性或源码准入门全部通过 |
| 2026-11-15 | 依赖/SBOM 与 KickCAT 来源专项审查：KickCAT 固定上游基线已追溯，argparse MIT 已核验；仍发现 KickCAT 10个文件差异和1个新增文件、ROS/Gazebo package.xml 许可元数据冲突、第三方依赖闭包和 SBOM 缺口 | 仍有实质性合规及集成阻塞；当前不得整体导入 |

主要历史定位：
- `TaskPlan_History/TaskPlan-2026-11-06.md`：v7.35–v7.38。
- `TaskPlan_History/TaskPlan-2026-11-07.md`：TODO-EXT-001 的完整启动条件和执行边界。
- `TaskPlan_History/TaskPlan-2026-11-08.md` 至 `TaskPlan-2026-11-13.md`：延期待办未授权的连续记录。
- `TaskPlan_History/TaskPlan-2026-11-14.md`：G-25、上游 Apache-2.0、Run #2827 和逐模块审查记录。
- `TaskPlan_History/TaskPlan-2026-11-15.md`：KickCAT 来源、依赖许可和 SBOM 审查记录。

## 2. 合并目标与范围定义

### 2.1 目标

将 MotionControlAlgorithms 作为一个**可独立构建、可独立测试、可追溯上游版本、可持续同步**的工程子项目纳入 robot_knowledgebasement，使知识库的理论内容、上游控制算法实现、测试、仿真适配器和工程证据能互相链接。

合并的目的不是把算法代码混入 Python 知识库包，也不是用上游项目替代本项目已有知识文章。知识正文仍以本项目独立编写、适用边界清晰的内容为准；上游实现作为有版本边界的工程资产。

### 2.2 推荐集成形态

推荐在目标仓库中建立独立子目录：

`projects/MotionControlAlgorithms/`

采用 **Git subtree / 带上游历史的目录级集成**，保留上游仓库提交历史和子目录边界。不要将上游 `main` 直接与知识库根目录做无前缀的 unrelated-history merge，也不要把上游根目录的 README、LICENSE、NOTICE、CMakeLists.txt、.github 等文件覆盖到知识库根目录。

理由：
1. 目标仓库根目录已有 MIT LICENSE、Python `pyproject.toml`、`src/robot_knowledgebase`、`tests/` 和根级 CI。
2. 上游是独立的 C++17/CMake 工程，使用独立的 `include/`、`src/`、`tests/`、`ros2/`、`gazebo/`、`benchmarks/` 等目录。
3. 将上游保留在独立子目录，能够避免两个项目根级构建、依赖、CI、测试和许可证边界混杂，也便于未来按上游 commit 同步。
4. 仅把源代码放在子目录并不会自动启用其 GitHub Actions；必须另外设计根级 workflow，在独立工作目录中构建和测试该子项目。

### 2.3 预计纳入内容

通过准入审核后，评估完整导入上游选定 commit 的工程目录，包括算法头文件/实现、单元测试、CMake 配置、仿真和 ROS 2/Gazebo 适配、benchmark、构建脚本、文档和项目级 LICENSE/NOTICE。具体路径和文件清单必须在导入前冻结。

不得默认导入临时文件、未跟踪产物、凭证、个人数据、无关缓存或不适合公开的日志。上游 `.gitmodules` 需要迁移成目标仓库根级 submodule 声明：当前上游只有 `scripts/ethercat_sil/KickCAT/argparse`，导入后路径应带 `projects/MotionControlAlgorithms/` 前缀，并保留 gitlink 的精确 commit；不能把嵌套的 `.gitmodules` 当作会自动生效的根级配置。

## 3. 当前准备度评估

| 门槛 | 当前证据 | 状态 | 对合并的影响 |
|---|---|---|---|
| 用户项目归属 | 用户已确认 MotionControlAlgorithms 为其原创开发项目 | 已确认 | 解决项目原创主体确认；不覆盖第三方依赖 |
| 上游根许可证 | 上游 main `c11091bd2bb3ce001eb09f2664c1ff5076f8a73b` 已有 Apache-2.0 LICENSE、NOTICE、README 许可声明 | 已通过基础门 | 可继续做准入评估，不能把第三方代码自动变成 Apache-2.0 |
| 基础上游 CI | Run #2827（commit `472e0ee76684d4e567caed1a40467af650d7fa9a`）Linux、Windows、benchmarks jobs 均成功 | 部分通过 | 不是目标仓库集成测试、目标平台 WCET、物理 EtherCAT HIL 或安全验收；也不能替代导入后 CI |
| KickCAT 第三方来源 | 固定基线 `cb2e1a192ac11ffaa58f08945053b8129abf94cb` 已定位；当前快照相对基线有10个文件差异和1个本地新增文件 | 未通过 | 需逐文件 patch/provenance、作者/贡献和 CeCILL-C 分发义务评估 |
| 第三方许可证与 NOTICE | KickCAT 为 CeCILL-C；`imgui_stdlib` 为 MIT；`portable-file-dialogs` 为 WTFPL-2.0；argparse 固定 commit 为 MIT | 部分通过 | 需逐项归属、版权与再分发义务清单；不能仅依根 LICENSE 判断 |
| ROS 2/Gazebo 包许可 | 四个 `package.xml` 标记 MIT，与项目根 Apache-2.0 声明不一致；真实许可意图尚未得到权利人确认 | 未通过 | 必须由权利人确认，之后才可更新包元数据或引入 |
| 依赖闭包与 SBOM | 未发现上游完整 SBOM/统一依赖锁定；Conan、Python、CMake、可选 IgH/SocketCAN/ROS 2/Gazebo 依赖分散 | 未通过 | 必须完成分构建 profile 依赖解析、SBOM 生成/校验和漏洞扫描 |
| 目标仓库集成兼容性 | 已确认目标仓库有独立 Python 包、根级测试/CI；尚未进行子目录导入、路径冲突、submodule、CMake 和 workflow 集成测试 | 未通过 | 必须在隔离分支验证，不得直接进入 main |
| 知识库当前主线 | 根计划仍为 00-01；第00章 00-01 仍进行中，剩余全库逐项主张审计/授权核验未完成；根计划状态核对称当前无节点同时满足完整交付与验收 | 未通过 | 不宜打断现行治理主线，合并不能升为当前最高优先级 |
| 精确导入授权 | 当前请求批准建立合并计划和优先级判断；未冻结最终文件范围、目标目录/commit 和实施分支授权 | 未通过 | 实际导入前仍须确认具体范围和实施授权 |

**当前结论：不适合立即合并。** 上游项目已有基础 CI 与根许可证，但当前仍有多个 P1 级第三方许可证、供应链和兼容性门槛未关闭；目标知识库主线 00-01 也尚未达到节点验收条件。继续扩大源码集成范围会增加治理负担，且可能让上游子项目的构建/许可问题污染当前知识库主线。

## 4. 必须先关闭的阻塞与验收门

### G1｜KickCAT 与全部第三方来源/许可证

- 对 KickCAT 相对固定上游基线的10个差异文件和1个新增文件逐项生成可复核 diff/patch，记录引入 commit、作者/日期、用途、测试和是否能由脚本重放。
- 区分 DS402 fault injection 与 LRW/network simulator/link-down 修改；形成可重放 patch series。
- 由权利人/法律顾问确认 KickCAT CeCILL-C 下修改、集成贡献、衍生模块和分发方式的义务；本计划不替代法律意见。
- 核验所有 vendor、submodule、测试夹具、benchmark、模型、脚本和文档的来源与许可；完整保留第三方 LICENSE/版权文本。
- 由项目权利人澄清四个 ROS 2/Gazebo `package.xml` 的 MIT 声明是否准确；未经确认不得擅自统一成 Apache-2.0 或 MIT。

### G2｜依赖闭包、SBOM 与软件供应链

- 建立 source SBOM，并对 Linux、Windows、ROS 2、Gazebo、SocketCAN、IgH、KickCAT、benchmark、工具脚本等实际可构建 profile 分别解析依赖。
- 生成 CycloneDX 或 SPDX SBOM，执行 schema 校验、许可证策略检查和漏洞扫描；归档 lock/解析结果、构建 provenance 和工具版本。
- 明确构建/测试/运行/开发依赖边界；对未解析或不可复现的可选依赖标为阻塞，而不是填入推测版本。

### G3｜目标仓库目录、许可证和构建边界

- 在隔离分支中验证 `projects/MotionControlAlgorithms/` 子树方案；保留子目录内 Apache-2.0 LICENSE 和 NOTICE，不替换目标仓库根 MIT LICENSE。
- 正确迁移 argparse submodule 的根级 `.gitmodules` 声明，并验证 gitlink commit 能检出。
- 检查路径、文件名、工具依赖和构建产物是否与现有知识库脚本/测试冲突。
- 单独设计根级 GitHub Actions workflow；工作目录指向集成子目录，独立构建 CMake、运行 CTest，并按平台/可选 profile 明确 skip 条件和证据。
- 明确知识库 Python CI 与 C++ 项目 CI 的隔离关系，避免默认用户安装知识库时必须安装 ROS 2/Gazebo/IgH 等重量级依赖。

### G4｜导入后验收与回滚

- 固定待导入上游 commit，建立文件清单和 Git tree 比对报告。
- 子目录 CMake build、CTest、benchmark smoke、Linux/Windows 基础矩阵及可选依赖 profile 按实际可用环境执行；失败项原样记录。
- 运行目标仓库原有 Python tests、Markdown/链接/知识库检查，确认没有回归。
- 对 LICENSE/NOTICE、submodule、CI、SBOM、文件数量/哈希和上游同步点进行复核。
- 提交独立 PR；在 review、CI 和用户确认后才允许合并。保留可回滚提交/版本标签。

## 5. 分阶段执行计划与任务状态

| 节点 | 任务 | 当前状态 | 完成条件 |
|---|---|---|---|
| MCA-M0 | 历史计划回溯、范围定义、当前适宜性判断 | **已完成（本计划）** | 13份每日 TaskPlan 已审阅；历史 TODO-EXT-001 与当前阻塞已归纳 |
| MCA-M1 | 完成 KickCAT 文件差异/第三方来源/包许可确认 | **进行中（对应14-EXT-02）** | 10个差异+1个新增文件有逐项可重放来源；所有组件许可及包声明有权利人证据 |
| MCA-M2 | 完成依赖闭包、SBOM 与漏洞扫描 | **未完成（对应14-EXT-02）** | source/profile SBOM 可复现、schema通过、许可证策略和漏洞扫描报告归档 |
| MCA-M3 | 确定 subtree 导入清单、submodule/CI/许可证方案 | **未开始** | 文件路径、上游 SHA、目标目录、submodule、workflow、许可证清单和回滚步骤经审查 |
| MCA-M4 | 在隔离分支试导入并运行目标仓库集成验收 | **阻塞：等待M1–M3** | 原有 Python CI 与导入后的 C++ 项目 CI 均通过，失败/不适用项有证据 |
| MCA-M5 | 用户确认具体导入范围并提交集成 PR | **阻塞：等待M4及明确授权** | 用户确认 commit、文件范围、目标目录和分支；PR review 与 CI 证据完整 |
| MCA-M6 | 合并至目标项目 main 并发布上游同步规则 | **未开始** | 仅在批准的 PR 合并后标记完成；记录 merge commit、上游 pin 与后续更新方式 |

## 6. 何时可以提升为最高优先级

只有同时满足以下条件，才从“延期”改为“可启动”：

1. 根主线 00-01 达到其章节 TaskPlan 的正式验收条件并由根 TaskPlan 记录，不以局部文章复核代替完成。
2. 第14章 14-EXT-02 的第三方来源/许可证/SBOM 阻塞全部关闭，特别是 KickCAT 10+1 文件差异、CeCILL-C义务、ROS/Gazebo包许可意图、完整依赖闭包和构建 profile SBOM。
3. 项目治理层面批准子目录 subtree 方案、上游同步策略、目标仓库根级 CI 和回滚策略。
4. 导入试验分支证明不会破坏知识库 Python、文档和现有 CI；上游 C++ build/test 有当前固定 commit 的可复核结果。
5. 用户再次确认具体导入 commit、目录、文件范围和实施分支授权。

满足以上条件后，更新根 `TaskPlan.md` 的“当前主任务”与优先级队列，将本计划提升为最高优先级，并按 MCA-M3→M6 执行。**在这些条件满足前，根任务 00-01 继续保持最高优先级，本计划只作延期跟踪，不得因用户要求建立计划而提前启动源码复制。**

## 7. 当前明确不执行的事项

- 不将 MotionControlAlgorithms 的 `main` 与知识库根目录直接合并。
- 不把其代码复制进现有 `src/robot_knowledgebase`，不改变现有 Python 包的功能或依赖。
- 不修改上游 MotionControlAlgorithms 的源代码、LICENSE、NOTICE、package.xml、CI 或第三方目录。
- 不提前导入 KickCAT、argparse、ROS 2/Gazebo、benchmark、测试夹具或仿真器。
- 不把 Run #2827 或静态代码审查描述为目标机器人实时性、EtherCAT HIL、功能安全或实机验收。
- 不直接修改目标仓库 main；计划后续实施也必须通过隔离分支和 PR。

## 8. 依据与关联文件

- 根治理：`TaskPlan.md`（当前主线 00-01；G-08、G-25）。
- 原始合并待办：`TaskPlan_History/TaskPlan-2026-11-06.md` v7.35–v7.38；`TaskPlan_History/TaskPlan-2026-11-07.md` TODO-EXT-001。
- 外部项目治理：`docs/engineering/External-Project-Integration-Policy.md`。
- 外部项目登记：`docs/audits/External-Project-Registry.md`，EXT-001。
- 第14章任务：`docs/TaskPlan/14-规划控制与机器人操作/TaskPlan.md`，14-EXT-01 / 14-EXT-02。
- 首轮仓库审查：`docs/audits/MotionControlAlgorithms-main-review-2026-11-06.md`。
- 依赖许可/SBOM：`docs/audits/MotionControlAlgorithms-dependency-license-sbom-audit-2026-11-15.md`。
- 当前上游基线：`rexyll/MotionControlAlgorithms@c11091bd2bb3ce001eb09f2664c1ff5076f8a73b`。
- 现有文档审查 PR：#13、#14 已合并；#18 是仍处于 Draft 的文档审查 PR，不是源码合并 PR。

---

**状态复核规则：** 每次上游 main、第三方依赖、许可证、SBOM、目标仓库 TaskPlan 或相关 PR 状态发生变化时，更新本文件的“准备度评估”和任务状态。历史结论只追加，不静默覆盖。
