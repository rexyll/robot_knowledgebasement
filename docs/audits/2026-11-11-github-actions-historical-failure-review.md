# GitHub Actions 历史失败记录审查与修复验收

- 审查日期：2026-11-11
- 仓库：rexyll/robot_knowledgebasement
- 分支：main
- 最新验收提交：c481ff0849f0cd442a1d0e9052856e325ef5283e
- 最新验收运行：[CI #3560 / Run ID 42951823527](https://github.com/rexyll/robot_knowledgebasement/actions/runs/42951823527)

## 1. 审查范围与统计

GitHub Actions workflow-runs API分页读取并在客户端按UTC日期与conclusion过滤后，2026-11-03至2026-11-11期间共确认182条失败运行记录。逐条索引见[历史失败run CSV](github-actions-failure-run-index-2026-11-03-to-11-11.csv)。按失败运行创建日期统计：

| 日期 | 失败运行数 |
| --- | ---: |
| 2026-11-03 | 48 |
| 2026-11-04 | 40 |
| 2026-11-05 | 1 |
| 2026-11-08 | 5 |
| 2026-11-09 | 5 |
| 2026-11-11 | 83 |
| **合计** | **182** |

这些是workflow run次数，不等于164个独立缺陷。连续小提交会重复触发同一故障。所有失败run均纳入历史索引，并按日期、失败job/step及代表性日志聚类。历史run是不可变审计记录，不会因后续修复而被改写为成功；修复效果以当前main的新运行结果判定。

## 2. 失败类别、影响与修复状态

### 2.1 Ruff Lint阻断矩阵测试

- 代表运行：[CI #3556](https://github.com/rexyll/robot_knowledgebasement/actions/runs/42948282668)。
- 日志报告113项Ruff错误，覆盖6个Stäubli脚本/测试文件。
- 规则分布：E701 37项、E501 38项、E702 31项、I001 4项、E401 2项、F841 1项。
- 影响：Lint失败后pytest被跳过；默认matrix fail-fast会取消其他Python版本，无法得到完整矩阵结论。
- 修复：格式化6个文件、拆分单行语句和分号语句、修正导入、删除未使用的plugin_deps；对两个future导入按仓库既有规则添加I001例外。CI #3558确认Ruff通过。

### 2.2 pytest测试模块导入路径错误

- 代表运行：[CI #3558](https://github.com/rexyll/robot_knowledgebasement/actions/runs/42951576750)。
- Ruff已通过，但三个新增测试模块在收集阶段报ModuleNotFoundError: No module named 'scripts'。
- 修复：pyproject.toml的pytest pythonpath加入仓库根目录；matrix设置fail-fast: false，避免单一Python版本失败时取消其他版本。

### 2.3 CMake File API测试错误依赖target列表位置

- 代表运行：[CI #3559](https://github.com/rexyll/robot_knowledgebasement/actions/runs/42951705050)。
- 测试假设targets[1]为plugin、targets[0]为core，但collector按target名称排序，导致断言错误。
- 修复：测试改为按稳定target name建立映射，再检查plugin依赖和core include/compile metadata，不再依赖数组位置。

### 2.4 Runtime Evidence Bundle早期负向测试失败

- 代表运行：[CI #3514](https://github.com/rexyll/robot_knowledgebasement/actions/runs/42944975572)。
- 两项测试曾在路径穿越拒绝、RUN_PASS证据完整性门禁处失败。
- 修复状态：后续实现与测试迭代已覆盖相关门禁；CI #3560三个Python版本的pytest全部通过。

### 2.5 Python 3.10下载HTTP 504

- 代表运行：[CI #2433](https://github.com/rexyll/robot_knowledgebasement/actions/runs/42471181009)。
- 2026-11-08和11-09共10条失败运行，均定位到actions/setup-python下载Python 3.10.22发行包时连续收到HTTP 504。
- 影响：Python 3.10 job在安装/测试前失败，不能证明该次提交的3.10兼容性。
- 修复状态：归类为GitHub Python发行包下载端点的外部服务/网络故障，不通过降低Python版本或绕过矩阵来掩盖。CI #3560的Python 3.10 job已成功，98项测试通过。

### 2.6 SBOM Artifact上传ECONNRESET

- 代表运行：[CI #1497](https://github.com/rexyll/robot_knowledgebasement/actions/runs/42033165380)。
- SBOM生成和校验成功，但FinalizeArtifact阶段发生ECONNRESET。
- 影响：该次运行的SBOM工件未能可靠归档，不是SBOM生成逻辑失败。
- 修复状态：按外部上传链路故障处理；后续SBOM归档及CI #3560均成功。

### 2.7 uv.lock与locked模式不一致

- 代表运行：[CI #583](https://github.com/rexyll/robot_knowledgebasement/actions/runs/41777566714)。
- uv sync --locked报告uv.lock需要更新，严格锁定模式拒绝继续。
- 修复状态：后续更新锁文件并保持locked校验；当前三个Python版本安装/构建和SBOM job成功。

### 2.8 OSV历史安全告警

- 代表运行：[CI #617](https://github.com/rexyll/robot_knowledgebasement/actions/runs/41779301081)。
- OSV审计曾对45个锁定包版本报告12条advisory/findings；工作流配置fail-on-findings，有发现时按设计失败。
- 影响：当时依赖锁定集合存在需要处置的安全告警，不能简单视为CI误报。
- 修复状态：后续执行依赖升级、锁文件与审计记录更新；当前CI #3560的OSV job成功。此结论只针对当前锁文件扫描结果。

### 2.9 上游源码SHA-256校验脚本变量引用错误

- 代表运行：[CI #533](https://github.com/rexyll/robot_knowledgebasement/actions/runs/41773801926)。
- 校验命令将RUNNER_TEMP变量放在单引号中，导致变量作为字面路径传给sha256sum。
- 修复状态：当前ci.yml已使用双引号展开shell变量；CI #3560的源码校验步骤成功。

### 2.10 浮点精度断言与早期导入排序问题

- 代表运行：[CI #220](https://github.com/rexyll/robot_knowledgebasement/actions/runs/41644398759)和[CI #1](https://github.com/rexyll/robot_knowledgebasement/actions/runs/41584650043)。
- 早期测试使用浮点精确相等比较，因二进制浮点表示差异失败；早期Ruff也报告collections/typing导入排序问题。
- 修复状态：浮点断言改用pytest.approx；导入问题在后续提交修正。当前三版本pytest和Ruff均通过。

### 2.11 本轮新增 target-validator/fixture 的 Ruff 回归

- 运行：[CI #3574](https://github.com/rexyll/robot_knowledgebasement/actions/runs/42954009005)、[#3575](https://github.com/rexyll/robot_knowledgebasement/actions/runs/42954098089)、[#3576](https://github.com/rexyll/robot_knowledgebasement/actions/runs/42954101038)、[#3577](https://github.com/rexyll/robot_knowledgebasement/actions/runs/42954139354)。
- 原因：新增 ament export fixture 与 upstream target graph validator 后，Ruff E501 检出测试字符串及validator limitations文案超出100字符；三个Python版本的Lint步骤均因此失败，pytest未启动。
- 修复：提交 `0a7359c` 拆分测试fixture字符串；提交 `f00c383` 拆分validator文案。CI #3578 / Run ID 42954198499 SUCCESS，确认格式门禁恢复。
- 影响：仅本轮新增知识库Python代码的Lint阻断，不涉及上游driver运行行为；四条失败run已加入逐条CSV索引，历史记录保持failure，不改写。

## 3. 本轮修复提交

| 提交 | 修复内容 |
| --- | --- |
| 1e1680b16780151bc99de1af270c4d029e10c844 | 修复6个Stäubli工具/测试文件的格式、单行语句、导入与未使用变量问题 |
| 6abc8bf947a5c6ce3462eef72ee509521794311c | 处理两个future导入的Ruff I001规则 |
| aa68929a56b535852cdbcdeb3be2d2a159280598 | pytest加入仓库根pythonpath；matrix设置fail-fast关闭 |
| c481ff0849f0cd442a1d0e9052856e325ef5283e | CMake File API测试按target name而非排序索引断言 |

## 4. 当前CI验收结果

[CI #3560 / Run ID 42951823527](https://github.com/rexyll/robot_knowledgebasement/actions/runs/42951823527) **PASS**

- Python 3.10：Ruff通过，pytest **98 passed**。
- Python 3.11：Ruff通过，pytest **98 passed**。
- Python 3.12：Ruff通过，pytest **98 passed**。
- Python SBOM生成/校验/归档：成功。
- OSV锁定依赖漏洞审计：成功。
- fail-fast: false已生效，三个Python版本均独立完成。

## 5. 尚存非阻断事项与验收边界

- GitHub Actions仍输出Node.js 20 deprecation warning：当前checkout/setup-python/upload-artifact action pin会被runner强制使用Node.js 24；本轮运行正常。该警告不是本轮失败原因，后续应核对官方兼容版本后单独升级固定commit。
- 历史失败run仍显示failure，这是不可变审计记录；修复效果以当前main的CI #3560结果判定。
- 本报告只证明知识库Python工具、Lint、pytest、OSV和SBOM CI通过；不证明Stäubli真实ROS Jazzy/CMake/colcon/C++编译、install-space consumer、plugin load/unload、ABI、TSan/ASan、硬件或HIL验收通过。
- 固定上游基线仍为ICube-Robotics/staubli_driver_ros2@bd658e2d266e315d2ee35f985fb352ea88306b79；未修改上游、未创建/应用/合并上游PR。TODO-EXT-001未授权，A1.1保持BLOCKED；RACE-01–16与EXEC-01–04仍NOT_RUN。

## 6. 结论与下一节点

历史Actions失败记录已完成盘点和分类；当前main上可修复的Lint、pytest导入路径、测试断言、锁文件和源码校验脚本问题已修复，历史外部网络/Artifact故障不再影响当前运行。当前完整CI #3560已通过。

**CI-HIST-001状态：COMPLETED。**

下一节点恢复§9.3.321 / SERVO-904：审阅现有GitHub Actions workflow，设计真实ROS Jazzy/CMake双配置证据采集的最小CI接入方案；真实外部构建/consumer/plugin/ABI/HIL状态继续保持NOT_RUN，除非实际运行并取得证据。


### 2.11 SERVO-906新增测试文件的Ruff导入排序回归

- 代表运行：[CI #3587](https://github.com/rexyll/robot_knowledgebasement/actions/runs/42955299858)、[CI #3597](https://github.com/rexyll/robot_knowledgebasement/actions/runs/42955621883)。
- 2026-11-11新增 `tests/test_staubli_ros_jazzy_build_script.py` 时，标准库导入块排序/空行格式与仓库Ruff/isort规则不一致，导致CI #3587–#3593、#3595–#3597共10条push触发run的Lint步骤失败；Python 3.10/3.11/3.12均在Lint处停止，pytest未执行。OSV与SBOM job保持成功。
- 影响：仅知识库新增测试文件的Lint门禁失败，不涉及固定上游Stäubli C++代码，也没有真实ROS构建执行。
- 修复：调整导入顺序与空行，后续CI运行用于验证。10条历史失败run保留原始failure，不改写为成功；这些run属于同一导入排序缺陷的重复触发，不代表10个独立缺陷。


### 2.12 ROS Jazzy workflow测试断言行宽回归

- 运行：[CI #3598](https://github.com/rexyll/robot_knowledgebasement/actions/runs/42955635997)。
- 新增手动ROS Jazzy workflow的测试中，完整镜像digest字符串直接写入单行断言，触发Ruff E501；三个Python版本均在Lint阶段失败，OSV/SBOM成功。
- 修复：将镜像digest拆分为相邻字符串常量；后续CI #3599已成功，证明本次Ruff修复生效。#3598保留为历史failure，并新增到CSV索引。


## 5. ROS Jazzy workflow环境来源记录

- 手动workflow：`.github/workflows/staubli-ros-jazzy-build.yml`，仅由 `workflow_dispatch` 触发，不自动作为每次Python CI的阻断门禁。
- 容器：`osrf/ros@sha256:ae7ad3ac243da1dfd8bd402a2fa08e149ffbf7a385013bd8ef798d0800accdc8`，Docker Hub页面标注linux/amd64，Ubuntu 24.04/Noble。来源：[OSRF ROS Jazzy desktop-full image digest](https://hub.docker.com/layers/osrf/ros/jazzy-desktop-full/images?tab=layers)。
- `backward_ros`：ROS Index显示Jazzy发行版包含backward_ros 1.0.8；来源：[ROS Index backward_ros](https://index.ros.org/r/backward_ros/)。
- Ubuntu Noble包：`libboost-system-dev` 与 `libasio-dev` 均有Noble发行包记录；来源：[libboost-system-dev](https://packages.ubuntu.com/noble/libboost-system-dev)、[libasio-dev](https://packages.ubuntu.com/noble/libasio-dev)。
- 状态：workflow已提交但尚未触发。镜像digest和包来源已核对；apt/rosdep实时解析、colcon双配置build/install、gtest和consumer仍待手动运行产出真实证据。


### 2.13 后续SERVO-907 target-export测试合同冲突（2026-11-11复核）

- 复核代表失败run日志：CI #3587 / Run ID `42955299858`的Python 3.10/3.11/3.12三个Lint job均因Ruff `I001`失败，Test step被跳过；OSV与SBOM jobs成功。CI #3598 / Run ID `42955635997`的三个Python Lint job均因Ruff `E501`（105 > 100）失败，OSV与SBOM成功。两项均是此前已修复并在后续CI中复验的格式回归，历史failure不改写。
- CI #3559 / Run ID `42951705050`三个Python Test job均因 `tests/test_staubli_cmake_file_api.py:76`断言依赖collector target排序位置而失败（97 passed, 1 failed）；修复为按稳定target name映射。CI #3558 / Run ID `42951576750`因pytest导入路径导致三个模块 `ModuleNotFoundError: No module named 'scripts'`，修复pytest pythonpath及fail-fast策略。CI #3560 / Run ID `42951823527`五个jobs全部成功，三个Python版本各98 passed。
- CI #3611 / Run ID `42955926260`已通过Actions jobs接口复核：`test (3.10)`、`test (3.11)`、`test (3.12)`、`Generate Python runtime and development SBOMs`、`Audit locked Python dependencies against OSV`五个jobs均completed/success；所有job步骤均success。
- 后续target-export namespace精确性修复发现旧测试 `test_gtest_name_substrings_do_not_count_as_installed_or_exported`要求未知非gtest target通过，与生产导出集合严格等于两个namespaced库的合同冲突。已将其改为验证整体应因未知导出失败、但不误报gtest泄漏。修复提交 `987b769cd18dd38e1c44f241a21bc9d4a0e24f08`。
- 当前连接器对commit workflow runs的读取仅返回pull_request事件；main push触发run不能由该接口列出，combined status为空。因此提交 `987b769`及文档提交的CI状态保持CI_RESULT_UNVERIFIED。必须从GitHub Actions页面或具备push run/check-run查询能力的接口核验后，才能宣布修复后的CI通过。不要重跑旧SHA的历史失败run来代替当前HEAD验证。


### 2.14 CI #3795–#3806：target-export测试断言冲突的完整定位与修复验证

- 通过GitHub Actions workflow-runs集合接口直接查询 `main` 的push运行，纠正§2.13末尾关于无法读取push run的旧结论：当前连接器的专用commit-run包装器只返回PR事件，但通用GitHub只读fetch接口可读取 `/repos/rexyll/robot_knowledgebasement/actions/runs?branch=main`。该能力可读取run列表、Job和Job步骤；不具备workflow_dispatch触发能力。
- CI #3795（Run `43004014039`）、#3796（`43004018886`）、#3797（`43004155139`）、#3798（`43004165607`）、#3799（`43004293157`）、#3800（`43004583860`）、#3801（`43004620881`）、#3802（`43004650944`）均失败。逐个读取代表Python job日志，均指向同一旧测试 `test_gtest_name_substrings_do_not_count_as_installed_or_exported`：断言期望 `PASS`，validator因未知生产导出target按精确集合规则返回 `FAIL`。Python 3.10/3.11/3.12均受影响；八次run不是八个独立根因。SBOM和OSV jobs均成功。
- 修复提交 `987b769cd18dd38e1c44f241a21bc9d4a0e24f08` 对应CI #3803 / Run `43004987153`，总结果SUCCESS。已逐项读取五个Job及全部步骤：Python 3.10/3.11/3.12测试（包括Lint和Test）、SBOM生成、OSV依赖审计全部SUCCESS，无失败步骤。三个Python job中的Stäubli生命周期、RACE/EXEC双向追踪、Runtime Evidence Bundle校验、wheel/sdist构建、STS3215元数据验证均通过。
- 后续文档提交CI #3804 / Run `43005027551`与#3805 / Run `43005036547`均SUCCESS，五个Job和所有步骤均SUCCESS。最新审计文档提交CI #3806 / Run `43005115690`的workflow结论SUCCESS。由此本轮修复及其后续文档提交均有main push CI成功证据。
- 历史失败run保留原始failure，不重写；其根因已由修复提交和后续成功运行形成闭环。Node.js 20 deprecation提示为warning，不是本批run失败原因，也未作为本轮阻断项。
- 本节修正§2.13末尾关于当前无法核验push run的结论：该结论在当时所用专用包装器范围内成立，但通用只读fetch接口可读取push run；以本节实际读取的GitHub Actions记录为准。


### 2.15 CI #3807–#3809：修复后连续文档提交的完整CI复验（2026-11-11）

- 在前一节记录时，#3807–#3809仍处于运行中；本轮重新查询Actions列表，三者均已completed/success，事件均为push，分别对应审计报告提交 `a8198f1`、第21章计划提交 `e9aa654`、根计划提交 `958aa18`。
- 逐个读取三次run的Job和每个Job的步骤：每次均有Python 3.10/3.11/3.12测试Job、CycloneDX SBOM Job、OSV审计Job，全部SUCCESS，所有步骤SUCCESS，无失败步骤。测试Job中的Lint、Test、Stäubli lifecycle traceability、RACE/EXEC双向追踪、Runtime Evidence Bundle、wheel/sdist构建及STS3215元数据验证均成功。
- 复查main push运行列表中#3803–#3809：7次连续运行全部completed/success，未发现新的失败run。#3795–#3802仍保留历史failure，其共同根因已由#3803修复并验证。
- 本节只关闭本批Python CI失败；不代表ROS Jazzy手动workflow已运行，也不代表SERVO-907动态验收通过。固定上游不变，A1.1仍BLOCKED，`TODO-EXT-001`未授权。


### 2.16 CI #3810–#3812：后续三次文档提交的Job、步骤与工件复验（2026-11-11）

- 三次main push运行均已完成：#3810 / Run `43006777912`（审计报告提交 `61ad009`）、#3811 / Run `43006785943`（第21章提交 `5c740b0`）、#3812 / Run `43006791890`（根计划提交 `cff79df`）。三者均为completed/success。
- 逐个读取三个run的全部Job及Job步骤：Python 3.10/3.11/3.12测试、CycloneDX SBOM、OSV审计共五个Job全部SUCCESS，所有步骤均为success或skipped，无failure/incomplete步骤。
- 逐个读取三次run的artifact清单：均成功归档Python SBOM、OSV报告，以及三个Python版本对应的Stäubli lifecycle、test-catalog、Runtime Evidence Bundle验证报告；工件均未过期。该批artifact属于Python静态验证/供应链证据，不是ROS/C++构建证据。
- 对应提交后的main连续push运行#3803–#3812全部completed/success；本轮没有发现新普通CI失败。历史失败记录继续保留原始状态。
- 专用 `.github/workflows/staubli-ros-jazzy-build.yml` 仍只声明 `workflow_dispatch`。当前连接器提供的GitHub Actions读取能力为GET-only，未提供workflow_dispatch写入/触发动作；因此本轮未触发该workflow，也未伪造运行结果。真实OFF/ON colcon build/install、install-space consumer、gtest、证据manifest与SHA-256仍NOT_RUN，SERVO-907继续BLOCKED。


### 2.17 CI #3813–#3815：v11.47文档提交后的三次完整CI复验（2026-11-11）

- #3813 / Run `43007378346`、#3814 / `43007387076`、#3815 / `43007394986`均已completed/success，分别对应审计报告、第21章计划、根计划v11.47提交。
- 逐个读取全部Job和步骤：三次运行的Python 3.10/3.11/3.12、CycloneDX SBOM、OSV五个Job全部SUCCESS，无失败或未完成步骤。
- 逐个检查三次run的工件清单：SBOM、OSV报告，以及Python 3.10/3.11/3.12的Stäubli lifecycle、test-catalog、Runtime Evidence Bundle验证报告均已归档，未过期。
- 因此#3803–#3815连续13次main push均completed/success。此结论只覆盖普通Python CI与供应链任务；不覆盖ROS Jazzy/C++动态构建。
- ROS Jazzy专用workflow仍为手动workflow_dispatch；当前GitHub连接器没有触发写入动作，本轮未运行。OFF/ON colcon build/install、install-space consumer、gtest、manifest/SHA-256仍NOT_RUN；SERVO-907继续BLOCKED。
