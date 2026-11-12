# Stäubli SERVO-906：ROS Jazzy 双配置真实 build/install 驱动

- 日期：2026-11-11
- 仓库：rexyll/robot_knowledgebasement
- 固定上游：ICube-Robotics/staubli_driver_ros2@bd658e2d266e315d2ee35f985fb352ea88306b79
- 范围：知识库侧可复现驱动脚本、安装空间 consumer smoke test、静态安全测试
- 未修改固定上游；本节点未在 ROS Jazzy 容器中实际执行构建。

## 1. 依赖闭包复核

固定上游 `.docker/Dockerfile` 使用 `osrf/ros:jazzy-desktop-full`，执行 `rosdep install --from-paths src --ignore-src -r -y`，然后在整个工作区执行 `colcon build`。本节点以此作为真实工作区构建入口依据，不把目标包根目录直接交给 CMake。

`staubli_robot_driver/CMakeLists.txt` 还显式使用：
- `find_package(backward_ros REQUIRED)`
- `find_package(Boost REQUIRED COMPONENTS system)`
- `${asio_SOURCE_DIR}/asio/include` include 路径

但对应 `package.xml` 没有声明 backward_ros、Boost 或 standalone Asio 依赖。新脚本在 rosdep check 之外显式检查 backward_ros 可发现性、`libboost-system-dev`、`libasio-dev` 和 `/usr/include/asio.hpp`。这避免把 package.xml 的 rosdep 结果误认为完整 CMake 依赖闭包。上游的 `asio_SOURCE_DIR` 仍未在固定 commit 的包 CMake 中定义；系统 include 检查只验证 standalone Asio header 存在，不宣称该 CMake 变量已修复。

## 2. 驱动脚本变更

更新 `scripts/run_staubli_build_testing_matrix.sh`：
- 要求 ROS_DISTRO=jazzy、ROS setup 存在、固定上游 commit 精确匹配且工作树 clean；
- 对 BUILD_TESTING=OFF/ON 使用独立 build/install/log 根目录；
- 预先建立 CMake File API codemodel-v2 query；
- 使用 colcon 对固定上游工作区执行 build/install，而非仅 cmake configure；
- 要求目标包 install_manifest.txt 非空及 install/setup.bash 存在；
- 从每个安装前缀采集真实 ament export target 文件；
- 生成独立下游 ament consumer 并在 OFF/ON 安装空间分别构建；
- ON 配置额外执行目标包 colcon test 和 test-result；
- 改为调用 SERVO-905 的 `validate_staubli_upstream_target_graph.py`，不再调用 Fake Harness validator；
- 通过 SERVO-903 evidence packager 生成并验证 SHA-256 manifest，包含环境指纹、双配置快照、validator报告和完整命令日志。

## 3. 测试与验收边界

新增 `tests/test_staubli_ros_jazzy_build_script.py`，对脚本关键合同进行静态回归检查：固定commit/clean checkout、Jazzy guard、colcon build/install、正确validator、双配置 consumer、test-result。

这些测试只证明脚本合同未被意外删改，不证明 ROS 构建成功。实际执行需要具备 ROS Jazzy、colcon、rosdep、backward_ros、Boost.System 和 standalone Asio 的 Ubuntu 24.04 环境。

| 项目 | 状态 |
|---|---|
| 上游 Dockerfile 构建入口核对 | STATIC_REVIEWED |
| CMake/package.xml依赖差异 | FINDINGS_RECORDED |
| 双配置 colcon build/install 驱动 | IMPLEMENTED_NOT_EXECUTED |
| CMake File API 双配置采集 | IMPLEMENTED_NOT_EXECUTED |
| 固定上游 target graph validator 接线 | IMPLEMENTED_NOT_EXECUTED |
| 双配置 install-space consumer | IMPLEMENTED_NOT_EXECUTED |
| BUILD_TESTING=ON colcon test | IMPLEMENTED_NOT_EXECUTED |
| 证据包 SHA-256 package/verify | IMPLEMENTED_NOT_EXECUTED |
| ROS Jazzy真实build/install/gtest/consumer | NOT_RUN |
| plugin load/unload、ABI、TSan/ASan、HIL | NOT_RUN |

**结论：** 真实构建/安装驱动已在知识库侧实现，但当前环境未执行 ROS Jazzy 构建，因此不得标记为构建 PASS。固定上游 CMake/package.xml 的依赖声明缺口未被本仓库擅自修补；下一节点应在固定 digest 的 ROS Jazzy 环境运行脚本，处理真实构建暴露的问题后再接入手动 workflow。

## 4. 安全边界

仅修改知识库 main；不修改、分叉写回或提交固定上游；不创建/应用/合并上游 PR。TODO-EXT-001 未授权，A1.1 保持 BLOCKED。脚本要求固定 commit 与 clean checkout，拒绝对来源不明或被修改的上游源码生成证据。

## 5. SERVO-906 后续静态复核（2026-11-11）

- **证据包命名修正：** `scripts/package_staubli_build_evidence.py` 原先将本节点validator报告归档为 `servo-901-validation-report.json`，已修正为 `servo-906-validation-report.json`；新增回归测试防止编号漂移。提交：`d8478f6`、`8d63b0d`。
- **下游依赖导出风险：** 固定上游 `CMakeLists.txt` 将 `Boost::system` 链接到 `staubli_robot_driver`，但 `ament_export_dependencies()` 未导出 Boost。ROS 2 ament 官方文档说明该宏用于向下游导出依赖，使consumer无需自行再次find_package。该缺口因此列为待真实验证的install-space集成风险；当前consumer未主动find_package(Boost)，不会用测试配置掩盖上游导出问题。依据：[ROS 2 ament CMake documentation](https://github.com/ros2/ros2_documentation/blob/rolling/source/Developer-Tools/Build/Ament-CMake-Documentation.rst)。
- **不可夸大的结论：** 该静态证据不能单独证明consumer必然失败；必须由固定digest ROS Jazzy workflow的实际consumer build确定。未修改固定上游。
- **CI复验：** CI #3620 / Run ID `42958035088` 与 CI #3621 / Run ID `42958041757` 均SUCCESS；Python 3.10/3.11/3.12、OSV、SBOM全部成功。仅验证知识库Python/静态测试，不代表ROS/C++ build/install/gtest/consumer通过。
- **当前状态：** SERVO-906 `IMPLEMENTED_NOT_EXECUTED`；SERVO-907仍未发现独立workflow run；真实ROS Jazzy验收继续 `NOT_RUN`。


## 6. 专用 workflow Run #5/#6：安装导出缺陷动态证据（2026-11-11）

### Run #5

- Run ID：`43027974929`；提交：`5102e31ca2c51a5875b108efceb3287f2f02ce07`；结果：`failure`。
- 固定上游 checkout、ROS Jazzy依赖准备、BUILD_TESTING=OFF构建与安装均推进成功；失败出现在独立 install-space consumer。
- CMake报告导入target `staubli_robot_driver::staubli_robot_driver` 的链接接口引用 `Boost::system`，但该target未定义；同时导出include路径包含不存在的 `/asio/include`。
- 两项错误分别对应固定上游缺少Boost下游依赖导出，以及将未定义的 `asio_SOURCE_DIR` 展开为错误绝对路径。该consumer未预先调用 `find_package(Boost)`，因此Run #5保留了Boost导出缺陷的直接动态证据。

### Run #6

- Run ID：`43031245835`；提交：`0fc60dfd911837bbe9e544676f0a4df3671c345e`；结果：`failure`。
- ROS Jazzy容器、固定上游checkout、rosdep、BUILD_TESTING=OFF/ON构建与安装、CMake File API快照均已推进；两个模式的consumer均在CMake生成阶段因导入target包含不存在的 `/asio/include` 而失败。
- target-graph validator在OFF/ON快照中均检测到 `/asio/include`，对应检查 `EXPORT-EXCLUDES-UNRESOLVED-ASIO-INCLUDE-OFF/ON` 均FAIL。证据工件已上传：`13860064639`。
- 对Run #6脚本进行复核时发现consumer夹具增加了 `find_package(Boost REQUIRED COMPONENTS system)`。这会预先创建 `Boost::system`，从而掩盖Run #5已实际暴露的上游Boost依赖导出缺陷；该测试夹具改动方向错误，不能保留。

### 知识库侧纠正

- 提交 `1f698152ebfa41ef82f2efe7389cdb33e26ec851`：移除consumer中的预先 `find_package(Boost)`，让独立消费者直接加载上游安装包，不再人为补齐上游未导出的Boost target。
- 提交 `ad6220b6e6f5cf89e1bbcba31f532928f7ef6349`：新增回归测试，明确禁止consumer夹具预先定义 `Boost::system` 或调用 `find_package(Boost)`。
- 两个提交触发的普通CI Run `43032513964`、`43032558011`在本记录写入时仍未完成，结果待逐Job复核；不得提前标记PASS。
- 固定上游 `ICube-Robotics/staubli_driver_ros2@bd658e2d266e315d2ee35f985fb352ea88306b79`保持只读。本仓库不通过创建空目录、伪造include目录、改写已安装导出文件或consumer手工补依赖来绕过缺陷。

### 当前结论与下一步

- **已由真实ROS Jazzy运行确认的上游安装导出缺陷：**
  1. `asio_SOURCE_DIR`未定义，导致导出接口包含无效路径 `/asio/include`，OFF/ON均失败。
  2. `Boost::system`出现在生产库的导出链接接口，但上游没有通过 `ament_export_dependencies(Boost)` 或等效配置确保下游target存在；Run #5的consumer直接失败，Run #6曾被测试夹具预先find_package掩盖，现已撤销该掩盖。
- 不能通过只改consumer夹具让该包通过。若要使上游安装包真正可消费，需要上游修复CMake依赖/导出合同；但本项目明确禁止修改固定上游或未经授权创建上游PR。
- SERVO-906与SERVO-907继续BLOCKED；完整gtest七项报告、consumer编译链接运行、manifest/SHA-256动态验收均未通过。A1.1保持BLOCKED；`TODO-EXT-001`未授权。


## 7. Consumer夹具回归测试修复与普通CI闭环

- 移除Boost预查找后，普通CI先后暴露了测试合同未同步（Run `43032513964`）以及断言错误地扫描注释文本（Run `43032558011`、`43032661039`、`43032712680`、`43032785783`）。上述失败均为Python静态测试断言问题，不是ROS Jazzy构建失败；SBOM/OSV jobs均成功。
- 首轮测试仍断言旧的 `find_package(Boost)` 存在；更新后测试又因脚本注释中出现 `Boost::system` 字样而误判。已将断言收窄为只检查consumer CMake命令行是否执行 `find_package(Boost...)`，不扫描注释。
- 最终测试修复提交：`962b4194d832c281b019aa164ca9d86e90e23cd1`。
- 普通CI Run `43032966478`（该提交）completed/success；Python 3.10/3.11/3.12测试、Lint、Stäubli lifecycle/test-catalog/runtime evidence静态验证、SBOM、OSV五个Job及全部步骤均SUCCESS。
- 结论边界：普通CI回归已闭环；它不改变Run #5/#6的真实ROS Jazzy失败结论。consumer已不再预先定义Boost target，后续专项运行将重新暴露上游Boost导出缺口；无效 `/asio/include` 仍是确定性阻塞项。


## 8. 专用workflow Run #7：Ubuntu apt镜像DNS故障与依赖索引重试修复（2026-11-11）

### Run #7失败证据

- Run ID：`43033695957`；提交：`324e387d74fecab496b63baad9c07e92e302bdbd`；结果：`failure`。
- 失败步骤：`Install explicit upstream CMake dependencies and build tools`。在固定上游checkout之前失败，后续checkout、rosdep和build/install矩阵均SKIPPED。
- 日志显示ROS仓库索引下载成功，但Ubuntu Noble的`archive.ubuntu.com`和`security.ubuntu.com`多次DNS解析失败；`apt-get update`虽打印部分索引失败警告，仍返回成功，后续apt install因`ros-jazzy-backward-ros`依赖`libdw-dev`无候选版本而失败（exit 100）。
- 因此Run #7不是上游源码构建或ASIO/Boost导出验证失败；该run没有产生新的上游安装导出结论。

### 已实施的知识库侧修复

- 新增`scripts/retry_apt_update.sh`：最多5轮刷新，启用APT Acquire retries和HTTP(S)超时；每轮刷新后通过`apt-cache policy`检查调用方指定的全部关键包是否有Candidate，只有索引满足依赖才返回成功。APT更新命令非零或部分镜像失败时继续重试；耗尽重试仍缺包则明确失败，绝不带着不完整索引进入安装。
- 专项workflow的显式工具安装前，检查`git`、`libboost-system-dev`、`libdw-dev`、colcon、rosdep及`ros-jazzy-backward-ros`候选包；rosdep安装前再次刷新并检查`libdw-dev`。
- 新增静态回归测试，验证两处调用、候选包门控、重试参数和bash语法；同步调整原先依赖直接`apt-get update`文本的顺序测试。
- 相关提交：`aaede3be13f052836dcf1babeb4e55a409c990c1`（重试脚本）、`b25200410b1f25511e7350c1bdd3e759e4b3b2d2`（workflow集成）、`d8b995b0d69325f27baa527ef43dc52c80493257`（确保非零update也可重试）、`817e0d0b02116566611e14841c7581cc7a6293e6`（回归测试）、`fd4b2d71ac4f0eee2d876659b832f157926201a9`（更新旧apt顺序断言）。
- 普通CI中间提交曾因旧断言仍寻找`apt-get update`而失败（Run `43034337272`），后续提交修正了断言。最终提交对应Run `43034476816`在审计写入时仍运行，待后续读取所有Job结果。
- 固定上游commit `bd658e2d266e315d2ee35f985fb352ea88306b79`未修改。该修复只处理CI环境的APT索引完整性与瞬时DNS故障，不改变上游依赖关系，也不绕过ASIO/Boost consumer检查。

### 下一步与验收边界

- 先确认普通CI Run `43034476816`所有Job通过；若失败，按日志继续修复。
- 随后用户需在最新main手动重新触发专用workflow。Run #7不能rerun旧SHA替代新提交验证。
- 新一轮若成功完成依赖安装，应继续检查真实OFF/ON构建、安装空间consumer、ASIO/Boost导出错误、七份gtest XML及manifest/SHA-256。
- SERVO-906/907仍BLOCKED；A1.1仍BLOCKED；`TODO-EXT-001`未授权。


## 9. 专用workflow Run #8：APT重试识别出持续性Ubuntu镜像DNS故障（2026-11-11）

- Run ID：`43035899689`；SHA：`4b4b201dfda5745475269c430f3b509289964a3b`；结果：`failure`。
- APT重试脚本按预期执行5轮，并在每轮检查关键包Candidate；ROS仓库索引均可访问，但Ubuntu Noble的`archive.ubuntu.com`与`security.ubuntu.com`每轮均DNS解析失败，`libdw-dev`始终无Candidate。脚本以明确错误退出，没有让不完整索引进入apt install。
- 失败步骤仍为显式依赖安装；固定上游checkout、rosdep、OFF/ON build/install、consumer和gtest均SKIPPED。此次失败没有新增上游CMake/安装导出证据。
- **根因修正方向：** 重试只能处理瞬时故障，不能改变不可达的软件源端点。GitHub-hosted runner运行在Azure托管环境；Microsoft Azure官方Ubuntu镜像配置文档明确建议Ubuntu 24.04及更新版本将`archive.ubuntu.com`和`security.ubuntu.com`改为`azure.archive.ubuntu.com`。参考：[Microsoft Learn：Create and upload an Ubuntu Linux VHD in Azure](https://learn.microsoft.com/en-us/azure/virtual-machines/linux/create-upload-ubuntu)。
- 知识库侧新增`configure_ubuntu_apt_mirror()`，在APT刷新前幂等改写Ubuntu传统`.list`与Noble deb822 `.sources`文件中的官方archive/security域名为Azure官方Ubuntu archive；保留原有签名校验、Candidate完整性门控和最多5轮重试，不添加第三方源、不跳过依赖、不伪造Candidate。新增静态回归测试与bash语法检查。
- 此策略基于GitHub runner所处Azure环境及Microsoft官方文档，但**尚未由新的ROS Jazzy专项运行验证**。下一次手动workflow必须确认Azure镜像可解析、Noble/security pocket可获取，且`libdw-dev`有真实Candidate；否则继续按日志定位，不得降低依赖门禁。
- 普通CI Run `43034734598`（SHA `4b4b201dfda5745475269c430f3b509289964a3b`）completed/success；这只证明知识库静态测试通过，不代表镜像策略或ROS构建动态通过。
- 固定上游commit `bd658e2d266e315d2ee35f985fb352ea88306b79`未修改；SERVO-906/907继续BLOCKED；A1.1保持BLOCKED；`TODO-EXT-001`未授权。


## 10. Azure Ubuntu镜像切换静态回归与普通CI验收

- 镜像配置实现提交 `b27f2ff9ee0065c7887c8f65a3e0c7819322cfc0` 对应普通CI Run `43130777043` completed/success；该次CI未包含后续新增镜像回归测试。
- 首次镜像测试提交 `30341263aeb60559ffcab1f607c445884c59552a` 对应Run `43130786960`失败，原因是测试把shell正则中的转义点写成了双重字面反斜杠，断言未匹配脚本中的正确`.`；不是镜像脚本执行失败。后续提交 `ad2f339619e2daaaee3648c34827e978fb35da22`和`e180f5a68ec86f8e16a2caf0e1f3d6cf0fcf37d5`继续修正断言及调用顺序检查。
- 最终测试修复提交 `e1e5741eea3c187689936943a2b5c60380878df2`对应CI Run `43130887111` completed/success；Python 3.10/3.11/3.12测试、SBOM、OSV五个Job全部SUCCESS。
- 结论边界：普通CI验证了镜像改写合同和脚本语法，不证明容器内Azure镜像DNS/下载可用。新的ROS Jazzy手动Run仍是必要动态验证。
- 当前main SHA为`e1e5741eea3c187689936943a2b5c60380878df2`；等待用户在此最新main上手动启动Run #9。SERVO-906/907继续BLOCKED。

## 11. 专用workflow Run #9：Azure APT恢复后完成真实OFF/ON构建，安装consumer暴露固定上游导出缺陷（2026-11-12）

### 运行身份与证据完整性

- Run ID：`43133529247`；结果：`failure`；SHA：`b594fd3b20827c269d9cf460c70c2126671d8ebb`；workflow：`Stäubli ROS Jazzy build/install evidence`。运行链接：https://github.com/rexyll/robot_knowledgebasement/actions/runs/43133529247。
- Run #8后加入的Azure官方Ubuntu archive配置已在真实ROS Jazzy容器中生效：APT依赖安装步骤SUCCESS，固定上游commit checkout SUCCESS，ROS依赖解析SUCCESS。此前Ubuntu archive/security DNS和`libdw-dev` Candidate阻塞解除。
- 固定上游检出并校验的commit仍为`bd658e2d266e315d2ee35f985fb352ea88306b79`，工作树干净；未修改上游源码。
- OFF/ON两种`BUILD_TESTING`配置均完成构建和安装。ON配置执行七份上游gtest XML，分别为6、7、7、3、5、9、9个测试，共46项；所有XML均为`failures=0`、`errors=0`，CTest日志报告`100% tests passed, 0 tests failed out of 7`。
- Artifact ID：`13906750810`，名称`staubli-ros-jazzy-build-install-evidence`，SHA-256：`763b18cca96e95153341f3992b7080143849a38133f7bfc4cef80aae26a0df32`；已下载ZIP并核对本地SHA-256与GitHub artifact digest一致。证据含OFF/ON快照、安装清单、安装导出、consumer两种配置日志、七份gtest XML及validator报告。
- target graph validator共49项检查，47 PASS、2 FAIL；两项失败均为OFF/ON导出target含未解析`/asio/include`。独立安装空间consumer在OFF/ON两种配置均于CMake configure阶段失败。

### 两项固定上游安装导出缺陷（证据互相印证）

1. **无效ASIO include路径。** 固定上游`staubli_robot_driver/CMakeLists.txt`的主库`target_include_directories()`把`${asio_SOURCE_DIR}/asio/include`作为PUBLIC include目录导出，但该CMakeLists只调用`find_package(Boost REQUIRED COMPONENTS system)`，没有定义`asio_SOURCE_DIR`。因此安装导出文件的`INTERFACE_INCLUDE_DIRECTORIES`出现绝对路径`/asio/include`；consumer日志明确报该路径不存在。固定上游`staubli_robot_driver/src/communication/udp_socket_impl.hpp`实际包含`<boost/asio.hpp>`，不是独立`asio/...`头文件。建议上游维护者移除错误的`${asio_SOURCE_DIR}/asio/include`并只保留正确的Boost include依赖；不得在本知识库CI创建伪目录或改写已安装导出文件。
2. **Boost::system未随包导出。** 固定上游CMakeLists调用`find_package(Boost REQUIRED COMPONENTS system)`，并把`Boost::system`加入主库链接接口；但`ament_export_dependencies()`列表没有Boost，`staubli_robot_driver/package.xml`也没有声明Boost依赖。独立consumer刻意不提前`find_package(Boost)`，加载`staubli_robot_driver`导出目标时报告链接接口含`Boost::system`但target不存在。建议上游维护者根据Boost是否属于公开接口决定将其改为PRIVATE（当前Boost.Asio仅见于`src/communication/udp_socket_impl.hpp`实现头）或完整导出Boost依赖及package manifest；最终做法须由上游维护者确认。
- 两项缺陷在OFF和ON安装前缀中均复现；consumer的CMake configure失败，因此不应宣称consumer build/link成功。两项缺陷均来自固定上游源码的安装导出合同，不是本地CI夹具预定义target造成的假阳性。

### 当前结论与下一步

- **已通过：** Azure APT依赖准备、固定上游commit校验、ROS依赖解析、OFF/ON生产构建与安装、ON配置七份gtest（46/46通过）、证据artifact完整性及SHA-256。
- **未通过：** OFF/ON独立安装空间consumer configure；target graph validator的两项ASIO路径检查。故SERVO-906/907仍BLOCKED，不得以构建和gtest通过替代安装consumer验收。
- 上游源码保持只读。下一步为形成可提交给上游维护者的最小修复建议/patch草案，但在用户明确授权前不修改上游、不创建PR；若不允许上游修复，则记录为上游阻塞项，继续补充静态审查与其他不依赖该修复的验证。
- A1.1保持BLOCKED；`TODO-EXT-001`未授权。

## 12. 上游安装导出修复建议草案（知识库内审查文件，未提交上游）

- 新增本地审查提案：`docs/audits/staubli-upstream-install-export-fix-proposal.md`，基于Run #9 artifact与固定上游CMakeLists/package.xml源码证据整理。
- 建议方向：移除未定义的`${asio_SOURCE_DIR}/asio/include` PUBLIC include；确认Boost仅用于`src/communication/udp_socket_impl.hpp`后将`Boost::system`作为PRIVATE链接依赖；在package.xml声明适当Boost rosdep依赖。若上游维护者确认Boost属于公共接口，则必须采用完整导出Boost target依赖的替代方案。
- 提案包含OFF/ON clean build/install/consumer/gtest验收门槛，并明确禁止consumer预先find_package Boost、伪造include目录或安装后改写export文件。
- 该文件只存在于知识库仓库，**没有修改上游、没有创建上游分支或PR**。等待用户明确授权后才可向上游提交。SERVO-906/907继续BLOCKED。

## 13. 用户授权后在个人 fork 实施最小修复；上游 PR 创建受集成权限限制（2026-11-12）

### Fork 权限与基线

- 用户明确授权向上游提交修复，并提供个人 fork：`https://github.com/rexyll/staubli_driver_ros2`。
- GitHub连接可读取 fork 的文件与分支；fork 的 `main` HEAD 经 Git ref API核验，精确等于固定上游基线 `bd658e2d266e315d2ee35f985fb352ea88306b79`，没有 fork-only 漂移。
- 已在 fork 成功创建分支 `fix/install-export-boost-asio`，基于上述固定 commit。分支可写权限已通过实际创建分支及文件提交验证。

### 已实施的修复提交

- 提交 `679cc4dd939484eeb9c72fb12c163a2b53b407b2`：从主库 PUBLIC include directories 移除未定义的 `\${asio_SOURCE_DIR}/asio/include`，并将 `Boost::system` 链接声明改为 `PRIVATE`。
- 提交 `6bbddecaaf9567bd463eacb7a04f6c2295b10bee`：在 `staubli_robot_driver/package.xml` 增加 `<depend>boost</depend>`。
- 分支 HEAD 已核验为 `6bbddecaaf9567bd463eacb7a04f6c2295b10bee`；与固定基线比较为 ahead 2 / behind 0，只有上述两个文件被修改。重新读取分支文件确认错误ASIO路径已移除、Boost链接为PRIVATE、manifest已声明Boost。
- fork的CI workflow在pull_request事件上运行；当前连接未提供workflow dispatch操作，因此尚无该分支的ROS Jazzy CI运行证据。不得将代码写入成功视为编译或consumer验收成功。

### 上游PR权限边界与当前结论

- 已尝试从 `rexyll:fix/install-export-boost-asio` 向 `ICube-Robotics/staubli_driver_ros2:main` 创建PR；GitHub返回HTTP 403 `Resource not accessible by integration`。这不影响已验证的fork写权限，但说明当前集成连接不能在上游仓库创建PR。
- 没有创建指向fork自身main的替代PR，也没有尝试绕过权限。修复分支与两个提交均保留在用户fork，可直接从该分支向上游main发起PR。
- **状态：** 修复已提交到用户fork；上游PR尚未创建；PR CI、OFF/ON clean build/install、独立consumer configure/build和gtest矩阵均待验证。SERVO-906/907继续BLOCKED；A1.1保持BLOCKED；`TODO-EXT-001`未授权。
- 下一步：由用户在GitHub网页上从fork分支 `fix/install-export-boost-asio` 向 `ICube-Robotics/staubli_driver_ros2:main` 创建PR；PR建立后，本连接可继续检查PR状态、review意见和Actions结果，并据失败证据修复fork分支。


## 14. 上游PR #9建立与CI等待授权（2026-11-12）

- 用户已确认PR建立。GitHub核验PR：[#9 Fix/install export boost asio](https://github.com/ICube-Robotics/staubli_driver_ros2/pull/9)，状态OPEN，base为`ICube-Robotics:main`，head为`rexyll:fix/install-export-boost-asio`。
- PR head SHA：`6bbddecaaf9567bd463eacb7a04f6c2295b10bee`；base SHA仍为固定基线`bd658e2d266e315d2ee35f985fb352ea88306b79`。PR包含2个commit、2个文件、2 additions/2 deletions；与此前候选修复一致。
- GitHub API确认PR `mergeable=true`，但`mergeable_state=blocked`，尚未合并。当前无review submission、无inline review thread、无PR评论。
- PR触发两个workflow：Format Run `43158192705`、CI Run `43158192776`。两者均为`completed/action_required`，jobs列表为空，commit status为pending且0个checks。此状态不是测试失败，也不是成功；说明GitHub尚未实际执行这些fork PR workflow（需要仓库维护者批准/允许该fork workflow运行）。
- PR检查入口：Format https://github.com/ICube-Robotics/staubli_driver_ros2/actions/runs/43158192705；CI https://github.com/ICube-Robotics/staubli_driver_ros2/actions/runs/43158192776。请仓库维护者在GitHub Actions界面批准来自fork的workflow运行；获批后再读取全部jobs/steps与check结果。
- PR仓库现有CI只有Format和通用CI；目前没有证据表明其覆盖本项目要求的ROS Jazzy OFF/ON colcon build/install、无预先Boost查找的独立install-space consumer、七份gtest XML及证据manifest。因此即使上游PR通用CI后续变绿，仍须另行完成专项ROS Jazzy动态验收。
- 当前结论：修复已提交并通过PR提交链路送达上游维护者审查，但尚未获CI执行、尚未合并、尚未在修复分支完成真实ROS Jazzy验收。SERVO-906/907继续BLOCKED；A1.1保持BLOCKED；`TODO-EXT-001`未授权。

## 12. 独立镜像验收：绿色workflow中的consumer失败被发现并纠正（2026-11-12）

### 12.1 Run #17结果复核：workflow绿色不等于consumer验收通过

- 专项Run #17：`43163545728`，知识库SHA `4eba82f1794020154ee0b6b4a73e1d09f392d702`，结论`success`。工作流步骤全部显示SUCCESS，证据工件ID `13919775021`，名称`staubli-ros-jazzy-build-install-evidence`，大小约46.5 MiB，GitHub digest / 下载ZIP SHA-256均为 `ffd0bb178950db12c10dec63852a5cc7a2dec576319540a42bd01d59c4839dad`。
- 独立下载并检查artifact内的 `logs/servo-906-build-install.log`、OFF/ON consumer logs及 `servo-906-validation-report.json` 后，发现矩阵脚本将consumer失败仅写入 `install-consumer-findings.txt`，随后继续打包并以0退出；因此GitHub workflow的绿色状态是脚本门禁缺陷造成的假绿。
- 两个consumer均已找到安装包、并解析到Boost 1.83.0，但在加载导出目标时失败：`staubli_robot_driver::staubli_robot_driver`的link interface含`Boost::system`，该imported target尚未定义。consumer没有预先`find_package(Boost)`，符合验收要求。错误栈指向安装空间中的`export_staubli_robot_driverExport.cmake`。
- 同一artifact的target graph validator为49/49 PASS、0 errors；ON模式7份gtest XML全部通过，`colcon test-result`报告53 tests、0 errors、0 failures、0 skipped。但validator范围仅覆盖target graph、install manifest及ament exports，不覆盖consumer configure/build；不能用49项静态检查和53项gtest替代consumer验收。

### 12.2 根因与代码修复

- 新镜像`rexyll/staubli_driver_ros2_from_org`的`staubli_robot_driver/CMakeLists.txt`确实仍以plain signature链接`Boost::system`，且调用`ament_export_dependencies(Boost)`。但该宏只触发普通`find_package(Boost)`，不会转发`system`组件；因此downstream没有创建`Boost::system` imported target。
- 已在新仓库main新增 `staubli_robot_driver/cmake/BoostDependencies.cmake`，内容为`find_package(Boost REQUIRED COMPONENTS system)`，并将包末尾改为`ament_package(CONFIG_EXTRAS cmake/BoostDependencies.cmake)`。依据ament_cmake的`ament_package(CONFIG_EXTRAS)`合同，CONFIG_EXTRAS在生成的export-target extras之前被加载，使Boost::system先行定义。新仓库修复提交：`c8fb9a800ff5520a1342590a5b5e8de52a90bf07`、`1a5f61b59fe1f47dfa8f0e118ceaca7f92b1ef5f`；新仓库main固定SHA为`1a5f61b59fe1f47dfa8f0e118ceaca7f92b1ef5f`。
- 知识库矩阵脚本已改为：保留consumer失败日志和证据包，但在manifest verify之后遇到任何OFF/ON consumer失败即`exit 1`，不再允许失败项被包装为成功。提交`96288096a766d22340ace9bf93387372e3fbc939`；随后将源码checkout及脚本默认expected SHA更新到新镜像修复提交，并同步workflow pin：`50b82b657cbe430d4bc5544f6203ec63c470f12a`、`ca0dd6bbea8fd1d859f86deb4325c4e44bc41bfb`。
- 知识库普通CI因旧测试仍断言旧源码SHA而失败（Run `43167591777`、`43167587321`）；已把三处旧SHA断言更新为新固定SHA，新增consumer失败必须使矩阵退出非零的回归测试。相关提交`41a7dc974fc3f54c52eb706c510ef1811eac9fa0`、`9ff45c00629d5e0f839c5ef751c9bacde1b11b20`、`ef19c0d9a6bd6c097ab195694683b2d3568285cb`。知识库CI Run `43167960215`与 `43167818175` completed/success，覆盖pin测试与fail-closed测试；专用ROS Jazzy Run `43167568313`使用旧源码SHA `1847c945b83cb4a111a3799b2b10b5e7cf2b9885`，OFF/ON consumer均失败后矩阵以`SERVO-906 ERROR: install-space consumer acceptance failed`非零退出，Run结论failure，证明fail-closed门禁已生效。最新固定源码 `1a5f61b59fe1f47dfa8f0e118ceaca7f92b1ef5f` 的ROS Jazzy Run `43167967353`已通过容器初始化、工具checkout、显式依赖安装和源码pin校验，目前处于rosdep依赖解析阶段；后续独立并发组Run `43168080087`已排队。新Boost组件导出修复尚未取得OFF/ON consumer PASS。

### 12.3 验收边界与下一步

- 新仓库普通CI/Format/Documentation在较早提交`863d478c815083ef7f0eaa78f967ee7f818180ed`均SUCCESS；含Boost component CONFIG_EXTRAS的最新源码提交`1a5f61b59fe1f47dfa8f0e118ceaca7f92b1ef5f`的三个Actions运行仍需逐一核验。
- 下一轮ROS Jazzy验收必须在新固定SHA上证明：OFF/ON build和install成功；两个独立consumer均configure/build成功并实际运行可执行文件；七份gtest XML均存在且通过；validator与manifest/SHA-256通过；矩阵脚本对consumer失败fail-closed。
- Run #17必须保留为历史`success`记录，但审计结论标注其consumer OFF/ON均FAIL，不能倒改历史run状态或引用为验收通过。
- SERVO-906/907继续BLOCKED；A1.1保持BLOCKED；`TODO-EXT-001`未授权。上游`ICube-Robotics/staubli_driver_ros2`未被修改；新镜像仅用于独立修复与验证。

- **Format修复补充：** 最新Boost CONFIG_EXTRAS文件首次Format运行因缺少Apache版权头失败（Format Run `43167553362`，step `ament_copyright`）。已为 `staubli_robot_driver/cmake/BoostDependencies.cmake`补充Apache-2.0版权头，提交 `1a5f61b59fe1f47dfa8f0e118ceaca7f92b1ef5f`。新固定源码SHA已同步到知识库矩阵脚本、workflow及pin回归测试；最新源码Format/CI及ROS Jazzy run `43167893738`等待结果。

## 13. 独立消费者执行路径修复与最新固定源码复验排队（2026-11-12）

- Run `43168282713`确认：Boost CONFIG_EXTRAS修复已让OFF/ON两个独立consumer都完成CMake configure和build（日志出现`Build files have been written`及`Built target staubli_install_consumer`）；但消费者程序执行路径仍错误，矩阵按fail-closed返回失败。
- 根因是colcon isolated install布局：实际二进制位于`install-<mode>/staubli_install_consumer/lib/staubli_install_consumer/staubli_install_consumer`，旧脚本误用`install-<mode>/lib/staubli_install_consumer/staubli_install_consumer`。
- 已修复`scripts/run_staubli_build_testing_matrix.sh`，并同步`tests/test_staubli_ros_jazzy_build_script.py`对路径的回归断言。提交`9260f516ba1d11c4a5bfdb8fbf83c57921c1386a`；最新main为`320735c2517588e5da7c4bbd4f2b9c8208ef6e47`。
- 该中间提交的CI Run `43169591442`曾因回归断言未同步更新而失败；测试断言已更新，最新CI Run `43169612005`在SHA `320735c`上SUCCESS。
- 专项Run `43169591434`基于旧脚本提交`9260f51`，已完成容器初始化、工具checkout、依赖安装及固定源码checkout，当前停留在rosdep解析；它不包含最新consumer路径修复，不可作为最终验收。最新SHA对应专项Run `43169611943`处于pending，因相同concurrency group等待前一run释放。
- 下一步必须等待Run `43169611943`启动并完成OFF/ON完整矩阵，重点核对consumer configure/build/run，七份gtest XML、validator、manifest和SHA-256。SERVO-906/907继续BLOCKED；A1.1继续BLOCKED；TODO-EXT-001未授权。

## 15. 最新固定源码ROS Jazzy OFF/ON build-install-consumer验收通过（2026-11-12）

### 15.1 Run与源码可追溯性

- 专项Run：[ #43169946221 ](https://github.com/rexyll/robot_knowledgebasement/actions/runs/43169946221)，workflow结论 completed / success，唯一job Pinned ROS Jazzy build/install matrix及全部steps均成功。
- 知识库main SHA：0e1c33b578222ea31e0d23b46a74003ab7618da0。
- 验收源码来自用户镜像 rexyll/staubli_driver_ros2_from_org，固定SHA：1a5f61b59fe1f47dfa8f0e118ceaca7f92b1ef5f；workflow执行checkout后验证HEAD精确匹配且工作树干净。
- 镜像该SHA的Format、Documentation、CI三项Actions均SUCCESS（Runs 43167866958、43167867013、43167866900）。上游PR #9仍为OPEN、未合并；其head 6bbddecaaf9567bd463eacb7a04f6c2295b10bee，base固定上游SHA bd658e2d266e315d2ee35f985fb352ea88306b79。本次专项验证针对镜像修复，不代表上游PR已合并或其分支已通过同等专项测试。

### 15.2 实际验收结果

- BUILD_TESTING=OFF：colcon build/install完成；clean独立install-space consumer configure/build/install及可执行文件运行通过，日志标记 INSTALL_SPACE_CONSUMER_PASS BUILD_TESTING=OFF。
- BUILD_TESTING=ON：colcon build/install完成；clean独立install-space consumer configure/build/install及可执行文件运行通过，日志标记 INSTALL_SPACE_CONSUMER_PASS BUILD_TESTING=ON。consumer未预先 find_package(Boost)，验证依赖由被测包的安装导出配置正确提供。
- gtest：7/7 suites通过；逐套测试数为7、6、9、5、3、7、9，总计46个gtest断言。colcon test-result总结为53 tests、0 errors、0 failures、0 skipped（其中包含ament测试结果汇总，不应将53误写为53个gtest断言）。
- target graph validator：49 PASS、0 FAIL、0 errors；覆盖OFF/ON目标存在性、测试target隔离、生产依赖闭包、install manifest与导出include/target合同。
- 证据manifest：5个核心artifact条目（OFF构建快照、ON构建快照、SERVO-906 validator报告、commands.log、环境指纹）逐一通过size及SHA-256核验；manifest显示 execution_status=PACKAGED，最终核验 execution_status=PASS、checked_artifact_count=5、0 errors。
- workflow明确输出 SERVO-906_BUILD_INSTALL_EVIDENCE_PASS。GitHub artifact：ID 13921209585，名称 staubli-ros-jazzy-build-install-evidence，大小48,839,334 bytes，保留30天；上传ZIP SHA-256：51a7f99cd3ab829c52f0e1c4c24eb212b8924d61ed69b585981bc543ea115664。[打开证据工件](https://github.com/rexyll/robot_knowledgebasement/actions/runs/43169946221/artifacts/13921209585)

### 15.3 结论、限制与后续

- 结论：之前发现的Boost::system imported target导出顺序问题已由CONFIG_EXTRAS修复；此前colcon isolated install consumer执行路径错误也已修复。最新固定镜像SHA的OFF/ON生产构建、安装、独立consumer运行、7套gtest、49项validator和5项证据哈希检查全部通过。此前Run #17假绿、Run #43168282713/中间consumer路径失败均保留为历史失败，不覆盖或改写。
- 验收范围限制：本次只证明ROS Jazzy容器中的build/install/export/downstream consumer及现有测试通过；不覆盖真实Stäubli控制器、CS9/VAL3、硬件在环、现场网络、机器人运动安全、长时间运行、ABI兼容矩阵、sanitizer、plugin真实加载/卸载及工业现场验收。硬件/运行时验证不可由本次CI推断。
- SERVO-906的“ROS Jazzy build/install + independent consumer evidence”子门槛可标记PASS；若SERVO-906总项或SERVO-907还包含硬件/运行时/上游合并条件，则整体保持BLOCKED，不能据此宣布机器人驱动产品级验收完成。A1.1保持BLOCKED；TODO-EXT-001未授权。
- 下一步：将本次专项证据链接、镜像SHA与范围限制同步到TaskPlan；继续审查上游PR #9的维护者review/CI批准和合并状态，并单独规划不连接真实机器人时可完成的仿真/runtime验证。不得擅自将本次镜像验收冒充上游main验收。

## 16. Runtime与仿真验证范围审查：现有测试的覆盖边界（2026-11-12）

基于固定镜像SHA 1a5f61b59fe1f47dfa8f0e118ceaca7f92b1ef5f的源码只读审查：

- README声明当前面向ROS 2 Jazzy/Ubuntu 24.04及CS9控制器；项目仍处于prototype/development状态，作者说明主动开发曾暂停；README只明确称position control当前受支持，velocity/hand-guiding及diagnostics为后续功能。不得将接口导出或mock单测存在解释为所有运动模式均已产品化。
- URDF测试 test_default_urdf.py 覆盖tx2_60l与tx2_60l_med、空prefix与staubli_ prefix、use_mock_hardware true/false的XACRO生成与check_urdf解析；这属于模型描述结构验证，不是ros2_control controller manager运行验证。
- MoveIt SRDF测试 test_default_srdf.py 仅覆盖tx2_60l及两个prefix的URDF/XACRO解析；它没有启动move_group、执行规划或检查规划轨迹。
- staubli_robot_description/test/test_launch_mocked.py目前只有TODO“launch mocked hardware for tests”，没有实际launch integration test。
- 硬件接口C++单测已具备MockRobotServer loopback UDP路径，覆盖mock robot配置、hardware interface初始化、pluginlib加载/初始化和接口导出；这是进程内/组件级模拟，不等于完整bringup launch graph端到端测试。
- launch_robot_control.launch.py串联robot_state_publisher、ros2_control_node、joint_state_broadcaster、joint_trajectory_controller spawner和RViz；launch_demo.launch.py默认use_mock_hardware=true并串联MoveIt。它们提供可行的无真实控制器仿真入口，但当前检查到的测试目录尚无对应launch_testing覆盖。
- README明确提醒真实AUTO模式需监督、E-stop随时可用，MoveIt首次执行应使用很低的速度/加速度比例并先在RViz检查。此类真实机器人测试不能在通用CI中自动执行。

### 建议的无真实硬件下一阶段门槛

1. 在固定ROS Jazzy环境中补齐mock bringup launch_testing：启动robot_state_publisher与ros2_control_node（use_mock_hardware=true、gui=false），等待controller_manager服务可用，断言hardware component状态、joint_state_broadcaster和joint_trajectory_controller生命周期状态；超时应收集节点日志并失败。
2. 补齐launch_demo headless启动测试（RViz/GUI关闭），验证MoveIt move_group与robot_description/semantic/kinematics参数可加载；若无合适的规划场景则只验证节点就绪与planning pipeline配置，不伪称完成运动规划验收。
3. 增加明确的模拟轨迹测试：只向mock hardware发送低幅度、有限时长的joint trajectory，验证控制器接受/完成动作并检查joint state反馈；必须确认mock硬件确实不加载真实Stäubli plugin/不打开真实机器人IP。
4. 分开记录：URDF/SRDF静态解析、driver UDP mock单测、controller bringup integration、MoveIt planning integration、真实CS9/HIL。不得合并成一个含糊的“仿真通过”。
5. 在实施前检查mock hardware插件来源、controller YAML、launch arguments、launch_testing依赖与节点退出/清理策略；测试只在loopback/mock模式执行，禁止自动连接192.168.0.254等默认真实机器人地址。

**当前结论：** ROS Jazzy build/install与独立consumer子门槛已通过；端到端mock bringup与MoveIt launch integration尚未证明。SERVO-906/907整体仍保持BLOCKED，直到其定义的所有非硬件与硬件验收项分别有证据；A1.1 BLOCKED；TODO-EXT-001未授权。

## 17. Mock bringup与MoveIt readiness gate细节审查（2026-11-12）

固定源码：`rexyll/staubli_driver_ros2_from_org`，当前main SHA `1a5f61b59fe1f47dfa8f0e118ceaca7f92b1ef5f`（本节只读审查，不修改该源码）。

### 17.1 Mock模式的网络边界

- `staubli_robot_description/r2c/staubli.r2c.xacro`在`use_mock_hardware=true`时加载`mock_components/GenericSystem`，不加载`staubli_robot_driver/StaubliHardwareInterface`；只有false分支才把`robot_ip`、UDP端口参数交给真实Stäubli硬件插件。
- `launch_robot_control.launch.py`默认`use_mock_hardware=true`，但`robot_ip`默认仍为`192.168.0.254`。从当前Xacro分支可确认mock分支不会把该IP传给真实驱动插件；不过自动化测试仍应显式指定mock true，并把robot_ip覆盖为loopback/不可路由测试地址，以形成纵深防御，且在运行时检查加载的hardware plugin确为GenericSystem。
- `controllers.yaml`定义250 Hz controller_manager、joint_state_broadcaster和6关节position command的joint_trajectory_controller；controller还请求position/velocity state interfaces。

### 17.2 MoveIt readiness gate风险

- `wait_for_robot_ready.py`等待transient-local `robot_description`及`joint_states`两个topic；两者都收到后正常结束，未设置超时，也未处理rclpy spin异常的显式退出策略。
- `launch_moveit.launch.py`使用`OnProcessExit(target_action=wait_for_robot_ready, on_exit=[launch_moveit])`。事件处理器未检查进程returncode；如果等待进程异常退出，仍会执行MoveIt include。更常见的缺消息场景则会无限等待，导致launch永不完成，也没有清晰的失败结果。
- `launch_robot_control.launch.py`在spawner进程退出后也无条件注册/触发后续状态切换命令；应检查spawner returncode，避免失败后继续执行activate命令。
- `staubli_robot_description/test/test_launch_mocked.py`仅包含TODO注释；`staubli_bringup/test`目前只有占位文件。当前不存在可证明controller_manager与控制器生命周期就绪的launch_testing集成测试。

### 17.3 修复与验收建议

1. 给wait节点增加有限超时参数（默认值需明确），超时返回非零；同时校验robot_description非空、joint_states至少包含期望的6个关节名称，而非仅收到任意消息。
2. 将MoveIt include改为仅在readiness process returncode==0时启动；非零退出应触发launch Shutdown并保留错误原因。对controller spawner也采用相同的成功退出门控。
3. 新增headless launch_testing：显式传入`use_mock_hardware=true`、`robot_ip=127.0.0.1`、`gui=false`、`start_controller=joint_trajectory_controller`；断言URDF ros2_control hardware plugin是GenericSystem，controller_manager服务可用，joint_state_broadcaster与joint_trajectory_controller进入预期状态。
4. 用ROS graph/系统socket观测或隔离网络命名空间证明测试不访问真实机器人网段；仅设置robot_ip loopback不足以证明没有其他旁路网络请求。
5. 在mock hardware上执行有限幅度、短时轨迹并验证action成功及joint_states反馈；若仅验证控制器启动而没有轨迹action结果，不能标记trajectory execution PASS。
6. 将MoveIt readiness超时/异常退出、spawner失败、controller manager启动失败纳入负向测试，确保整个launch以非零/明确shutdown失败，而不是静默挂起或继续启动下游节点。

**当前状态：** 以上为源码审查得到的明确缺口和待实施项，不代表已修复或已运行ROS launch测试。build/install与独立consumer子门槛仍PASS；runtime bringup与MoveIt readiness子门槛仍BLOCKED。SERVO-906/907整体保持BLOCKED。

## 18. 最新main触发的第二次ROS Jazzy OFF/ON矩阵复验通过（2026-11-12）

- Run [#43171335488](https://github.com/rexyll/robot_knowledgebasement/actions/runs/43171335488) completed / success；唯一job `Pinned ROS Jazzy build/install matrix`成功，基于知识库main SHA `9e50a8a04d1e63893c3c30830a5dba7091fc7dda`执行。
- 固定Stäubli镜像源码SHA仍为`1a5f61b59fe1f47dfa8f0e118ceaca7f92b1ef5f`，source checkout/dependency resolution成功。
- OFF/ON独立install-space consumer均实际运行成功：日志分别包含`INSTALL_SPACE_CONSUMER_PASS BUILD_TESTING=OFF`和`...ON`。
- 7/7 gtest suites通过；colcon汇总53 tests、0 errors、0 failures、0 skipped。Target graph validator报告`check_count=49`、`error_count=0`、`execution_status=PASS`；49项检查全部PASS。
- 证据manifest最终`execution_status=PASS`、`checked_artifact_count=5`；artifact ID `13922711625`，名称`staubli-ros-jazzy-build-install-evidence`，大小48,836,333 bytes；上传ZIP SHA-256：`0636c276135f618e8523a9487865eece113b7fca6108a50687e93dd9e6e9f1ca`。[打开证据工件](https://github.com/rexyll/robot_knowledgebasement/actions/runs/43171335488/artifacts/13922711625)
- 同一知识库SHA的普通CI Run `43171335549`也SUCCESS（Python 3.10/3.11/3.12、OSV审计、SBOM任务均完成）。
- 这是第二次独立专项run通过，增强固定镜像SHA下build/install/consumer矩阵的可重复性；不增加本次测试范围，不证明真实控制器/HIL/现场运动安全，也不解决§17所述runtime readiness/launch integration缺口。
- 结论：SERVO-906 build/install与独立consumer证据子门槛继续PASS；runtime/MoveIt子门槛仍BLOCKED，SERVO-906/907整体仍BLOCKED。A1.1 BLOCKED；TODO-EXT-001未授权。

## 19. Mock readiness gate第一轮修复与CI状态（2026-11-12）

### 19.1 已提交到用户镜像main的修改

用户镜像 `rexyll/staubli_driver_ros2_from_org` 已提交以下改动，当前HEAD为`abd75ff956b4fb07a76705abcb8fd506b2985aaa`：

- `wait_for_robot_ready.py`增加30秒有限等待超时，超时返回非零退出码；robot_description为空时忽略；joint_states必须包含默认六个关节名才视为ready。
- 修正QoS：robot_description订阅保留TRANSIENT_LOCAL；joint_states订阅改为BEST_EFFORT + VOLATILE。原代码对joint_states使用TRANSIENT_LOCAL，可能与默认VOLATILE发布端不兼容，造成永远收不到joint_states。
- `launch_moveit.launch.py`仅在readiness进程returncode为0时启动MoveIt；失败记录错误并Shutdown。
- `launch_robot_control.launch.py` controller spawner非零退出时Shutdown，不再继续执行后续激活命令。
- bringup package.xml补充rclpy、sensor_msgs、std_msgs、ament_cmake_pytest依赖；CMake注册readiness pytest。
- 新增`test_wait_for_robot_ready.py`：发布transient-local robot_description与volatile joint_states，检查不完整关节列表不会通过、完整六关节列表才ready；另增加超时非零退出测试。

### 19.2 已观察到的验证结果与未决项

- Format在中间提交`5d7bcb1d...`失败，原因是Black自动重排两个launch文件以及测试导入E402；已手动修复并提交。
- Format在提交`169987322f1cc6f3393a3f85d36f32ad13fa0076` SUCCESS；Documentation同一SHA SUCCESS。
- CI在较早提交`8beb536fbfa6875c453cce8d0f09ccb55c002cb9` SUCCESS，日志确认新增readiness QoS/六关节正向pytest 1/1通过；该SHA早于后续增加的timeout subprocess test和明确VOLATILE durability提交。
- 最新HEAD `abd75ff956b4fb07a76705abcb8fd506b2985aaa` 的Format、Documentation、CI分别为Run `43173412955`、`43173412938`、`43173412883`，截至记录时均仍IN_PROGRESS。timeout负向测试及最终源码版本尚未获得最终CI结论。
- 因此不能把早期SHA测试通过扩大解释为最新HEAD全部测试通过；必须等待最新SHA三项workflow全部结束，特别核验timeout测试是否通过。

### 19.3 下一步

1. 等待并检查最新镜像SHA三项Actions。
2. 若CI通过，将知识库专项workflow与矩阵脚本的固定源码SHA更新为`abd75ff956b4fb07a76705abcb8fd506b2985aaa`，运行完整ROS Jazzy OFF/ON build/install/consumer矩阵并归档新证据。
3. 再补headless ros2_control mock bringup launch_testing，验证GenericSystem、controller_manager、两个controller生命周期；之后补MoveIt headless启动/配置测试和mock trajectory action测试。
4. 对真实CS9/VAL3、HIL、网络隔离及运动安全另行设门槛。

**状态：** readiness逻辑第一轮修复已提交；最新镜像SHA的CI仍待完成；launch级端到端bringup/MoveIt/trajectory测试尚未完成。build/install/consumer子门槛仍PASS（旧固定SHA的证据）；SERVO-906/907整体BLOCKED。


## 20. Readiness修复CI通过并更新ROS Jazzy验证源码固定版本（2026-11-12）

### 20.1 镜像最新源码CI证据

- 用户镜像 `rexyll/staubli_driver_ros2_from_org` HEAD `abd75ff956b4fb07a76705abcb8fd506b2985aaa` 的CI Run [43173412883](https://github.com/rexyll/staubli_driver_ros2_from_org/actions/runs/43173412883) completed / success。
- 唯一job `build_and_test`（job ID `131031848855`）SUCCESS；新增 `test_wait_for_robot_ready.py` 两项pytest均通过，其中包含完整六关节QoS readiness正向场景及timeout非零退出负向场景。
- colcon汇总68 tests、0 errors、0 failures、0 skipped；新增readiness测试报告2 passed。Format Run `43173412955`与Documentation Run `43173412938`也均SUCCESS。
- 日志中的 `geninfo` 无`.gcno/.gcda`及coverage.info缺失属于覆盖率采集/报告问题；不影响本次Actions结论，但覆盖率报告本身仍不可用。另有mock硬件测试输出预期的模拟连接错误日志，不等同于测试失败。

### 20.2 知识库验证源码pin更新

- 已将以下三个文件中旧固定SHA `1a5f61b59fe1f47dfa8f0e118ceaca7f92b1ef5f`替换为新镜像SHA `abd75ff956b4fb07a76705abcb8fd506b2985aaa`：
  - `.github/workflows/staubli-ros-jazzy-build.yml`：checkout SHA及HEAD一致性断言；
  - `scripts/run_staubli_build_testing_matrix.sh`：默认EXPECTED_UPSTREAM_COMMIT；
  - `tests/test_staubli_ros_jazzy_build_script.py`：源码pin回归断言。
- 变更提交依次为 `344c13fcd0718ccf9facf09c7641f9a675a2d494`、`fee2c972a2ad92897dbed2ddf3c115e120119d58`、`8025ca10b5826241cd684982416855a4df7a69e3`；当前main HEAD为最后一个提交。
- push触发知识库CI Run `43175490804`（进行中）及ROS Jazzy专项Run `43175490783`（排队中）。前两个中间提交也触发了workflow，其中较早的专项run出现cancelled；这些中间run不作为最终验收依据。必须以最终HEAD对应run为准。
- 本节记录的是pin更新与workflow触发，不是新SHA下ROS Jazzy矩阵通过。待最终专项run成功后，才可把build/install/consumer证据子门槛更新为新SHA有效。

### 20.3 下一步与状态边界

1. 检查最终HEAD `8025ca10b5826241cd684982416855a4df7a69e3`对应普通CI与ROS Jazzy专项Run；如失败，先修知识库workflow/脚本，再重跑。
2. 专项成功后核验OFF/ON build/install、独立consumer实际执行、7/7 gtest、validator、evidence manifest和artifact SHA-256。
3. 之后实施headless mock bringup launch_testing，确认GenericSystem、controller_manager及两个controller lifecycle；再做MoveIt headless与mock-only trajectory action。
4. 上游PR #9仍OPEN且未合并；镜像CI不等于上游main修复。无真实控制器/HIL/现场运动测试。

**状态：** readiness逻辑在用户镜像SHA `abd75ff...`上的CI子门槛PASS；知识库source pin已更新，但新pin下ROS Jazzy专项矩阵仍待最终HEAD workflow完成。runtime launch integration仍BLOCKED；SERVO-906/907整体BLOCKED；A1.1 BLOCKED；TODO-EXT-001未授权。


## 21. 新源码SHA的ROS Jazzy build/install/consumer矩阵通过（2026-11-12）

### 21.1 最终HEAD与工作流结论

- 知识库main HEAD：`f79ca6ae7e89e021ef9900f4687c84d5fd884bfd`。
- ROS Jazzy专项Run [43175652104](https://github.com/rexyll/robot_knowledgebasement/actions/runs/43175652104) completed / success；job `Pinned ROS Jazzy build/install matrix` ID `131039357412` SUCCESS。
- 本次矩阵检出的镜像源码SHA为 `abd75ff956b4fb07a76705abcb8fd506b2985aaa`，即前节通过mirror CI的runtime/readiness修复版本。

### 21.2 结果

- BUILD_TESTING=OFF和ON两种配置的build/install均成功。
- 两种配置均构建独立install-space consumer，并实际执行成功：日志分别出现 `INSTALL_SPACE_CONSUMER_PASS BUILD_TESTING=OFF` 与 `INSTALL_SPACE_CONSUMER_PASS BUILD_TESTING=ON`。
- 7/7 upstream gtest XML suites通过；colcon汇总 `53 tests, 0 errors, 0 failures, 0 skipped`。
- Validator `execution_status=PASS`，manifest检查 `checked_artifact_count=5` 且五项均PASS；日志输出 `SERVO-906_BUILD_INSTALL_EVIDENCE_PASS`。
- 证据Artifact [13924820027](https://github.com/rexyll/robot_knowledgebasement/actions/runs/43175652104/artifacts/13924820027)，名称 `staubli-ros-jazzy-build-install-evidence`，大小48,847,855 bytes；ZIP SHA256 `2526ae1b3e1d9a5580e7afda4ee67d7aaa957c7b3b5ffa76cacc932260caf37a`。

### 21.3 解释与边界

- 本次日志中mock server/硬件接口测试出现若干ERROR级模拟日志（如未连接控制端口、缺少关节描述），但对应gtest均明确PASSED，colcon零失败；不得将预期mock负向场景日志误记为CI失败。
- build/install/Boost exported-target/独立consumer子门槛在当前pin SHA上PASS。此结果不等同于bringup launch、controller lifecycle、MoveIt规划/执行或真实机器人运动通过。
- 后续需新增并运行headless mock bringup launch_testing：验证xacro生成、GenericSystem、controller_manager、joint_state_broadcaster、joint_trajectory_controller的加载/激活和状态；再验证MoveIt headless planning及mock trajectory action/feedback。不能在launch tests中连接真实机器人。
- PR #9仍OPEN且未合并；真实控制器/HIL/现场运动安全验收未执行。

**状态：** SERVO-906 build/install/consumer gate PASS（当前镜像SHA `abd75ff...`）；runtime bringup/MoveIt integration仍BLOCKED；SERVO-906/907整体BLOCKED；A1.1 BLOCKED；TODO-EXT-001未授权。


## 22. 开始headless mock bringup集成测试（2026-11-12）

- 在镜像main新增 `staubli_bringup/test/test_mock_bringup.launch.py`：只使用TX2-60L的GenericSystem mock硬件、robot_ip=127.0.0.1、gui=false；等待controller_manager的ListControllers服务，要求joint_state_broadcaster与joint_trajectory_controller均为active，并验证`/joint_states`包含六个预期关节。
- `staubli_bringup/CMakeLists.txt`注册`add_launch_test(... TIMEOUT 120)`；package.xml新增launch_testing相关test依赖。此测试不连接真实控制器，不发送真实机器人运动命令。
- 镜像最新提交SHA `e1124f29c726a06074bf2f97d23c949a72249fcd`；对应CI Run `43176950518`、Format Run `43176950462`、Documentation Run `43176950570`正在运行。尚无launch test通过证据。
- 新增测试存在真实集成风险：spawner启动时序、controller_manager robot_description订阅、controller activation CLI及joint_states发布均需在Jazzy容器里实测。若失败，依据日志修复，不能仅凭静态代码宣称通过。
- 本次launch test新增提交发生在此前矩阵源码pin `abd75ff...`之后；待镜像CI通过后，应将ROS Jazzy workflow/script/test pin推进至新镜像SHA并重新跑完整OFF/ON矩阵，才能把当前源码版本纳入证据范围。

**状态：** §21 build/install/consumer gate仍对SHA `abd75ff...`有效；headless mock bringup integration新测试已提交、CI待验证。SERVO-906/907整体仍BLOCKED。


### §22补充：Format首轮失败及修复

- 首轮Format Run `43176950462`在Black步骤失败，日志明确指出仅`test_mock_bringup.launch.py`需要重新格式化；clang-format通过，Documentation Run `43176950570`成功。
- 已按Black输出调整测试文件，修复提交SHA `49d720fde6e95586026e888b583f7f68ecef9400`。
- 修复SHA对应CI Run `43177314945`、Format Run `43177315000`、Documentation Run `43177314966`仍在运行。以修复SHA的结果为准，首轮Format失败保留为历史记录，不作为最终通过证据。


## 23. Jazzy launch运行时导入错误修复（2026-11-12）

### 23.1 首轮集成测试发现的问题

- 镜像SHA `e1124f29c726a06074bf2f97d23c949a72249fcd`的CI Run `43176950518`失败：新launch test执行时，`launch_robot_control.launch.py`导入`LogError`失败，ROS Jazzy的`launch.actions`中不存在该符号。
- 失败发生在launch解析/导入阶段，controller_manager尚未启动，不能把它归因为控制器状态或mock硬件问题。
- 同时检查发现`launch_moveit.launch.py`也引用同一个无效`LogError`，会在MoveIt路径触发相同问题。
- 原有`test_wait_for_robot_ready`两项pytest在该run中通过；launch integration测试失败。该run的colcon汇总存在失败项，整体CI为FAIL。

### 23.2 修复

- 已在`staubli_bringup/launch/launch_robot_control.launch.py`和`staubli_bringup/launch/launch_moveit.launch.py`移除不受支持的`LogError`导入及调用，改用Jazzy支持的`LogInfo`输出明确的`ERROR:`前缀，再通过`EmitEvent(Shutdown(...))`执行失败关闭。
- 修复提交：`cd8f6446888554f4d9c0485d751ac2ff04e586e3`及`755a710b8f5348b14f2f65e47cd882200ffdc877`。
- 最新镜像SHA `755a710b8f5348b14f2f65e47cd882200ffdc877`的CI Run `43177972372`、Format Run `43177972439`、Documentation Run `43177972523`仍在运行。修复尚未取得CI通过证据。
- 先前Format修复链也出现Black行宽配置未按仓库`--line-length=99`执行导致的重复失败；当前测试文件已按仓库99字符配置调整，最终应以SHA `755a710...`检查为准。

**状态：** Jazzy launch import问题已提交修复，验证待最新镜像CI完成；headless mock bringup仍BLOCKED。不得更新知识库ROS Jazzy源码pin至新SHA，直到镜像Format/CI/Documentation通过。


### §23.3 后续静态检查反馈

- SHA `755a710...` Format Run `43177972439`：Black已通过，flake8发现MoveIt launch文件使用`LogInfo`但未导入（F821）。已补充导入，修复提交 `5b2196f2961a027fabc4c16ae9bfd70b0c73d47b`。
- 当前最新SHA `5b2196f2961a027fabc4c16ae9bfd70b0c73d47b`的CI/Format/Documentation Runs分别为 `43178262257`/`43178262221`/`43178262304`，均待完成。
- 因此，LogError替换方案的最终静态检查尚未通过，且mock bringup launch还未重新走到controller启动断言。后续必须以最新SHA结果为准。


### §23.4 mock bringup首轮真实运行结果

- 镜像SHA `755a710b8f5348b14f2f65e47cd882200ffdc877`的ROS CI Run `43177972372` SUCCESS。
- 新增`test_test_mock_bringup.launch.py`实际启动成功：日志确认controller_manager收到`/robot_description`，加载`mock_components/GenericSystem`，硬件成功初始化；`joint_state_broadcaster`成功激活，`joint_trajectory_controller`成功加载并激活。
- launch test报告1 test、0 errors、0 failures；整个colcon汇总70 tests、0 errors、0 failures、0 skipped。原有readiness pytest也通过。
- 测试期间验证`/joint_states`发布包含六个预期关节；controller lifecycle断言通过。此结果仅对mock GenericSystem成立，不代表真实Stäubli硬件。
- 日志在测试结束/launch shutdown时出现`ros2 control set_controller_state`子进程被SIGINT（exit -2）及controller_manager统计线程shutdown噪声；测试本身仍PASS。需要后续评估是否添加CLI退出等待/优雅关闭断言，避免把shutdown竞态作为已完全清理。
- 该SHA的Format Run `43177972439`因MoveIt launch文件缺少`LogInfo`导入而失败；已在最新SHA `5b2196f...`补齐。最新SHA CI/Format/Documentation待完成，因此不可将上一SHA的CI结果当成最新HEAD整体通过。

**状态：** headless mock bringup的核心启动、GenericSystem初始化、两个controller active和六关节joint_states断言在SHA `755a710...`通过；最新HEAD完整门槛仍待验证。MoveIt launch import静态修复已提交，MoveIt实际启动/规划尚未测试。
