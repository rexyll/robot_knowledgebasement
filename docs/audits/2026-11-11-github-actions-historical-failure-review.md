# GitHub Actions 历史失败记录审查与修复验收

- 审查日期：2026-11-11
- 仓库：rexyll/robot_knowledgebasement
- 分支：main
- 最新验收提交：c481ff0849f0cd442a1d0e9052856e325ef5283e
- 最新验收运行：[CI #3560 / Run ID 42951823527](https://github.com/rexyll/robot_knowledgebasement/actions/runs/42951823527)

## 1. 审查范围与统计

GitHub Actions失败筛选在2026-11-03至2026-11-11期间返回164条失败运行记录。按失败运行创建日期统计：

| 日期 | 失败运行数 |
| --- | ---: |
| 2026-11-03 | 46 |
| 2026-11-04 | 40 |
| 2026-11-05 | 1 |
| 2026-11-08 | 5 |
| 2026-11-09 | 5 |
| 2026-11-11 | 67 |
| **合计** | **164** |

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
