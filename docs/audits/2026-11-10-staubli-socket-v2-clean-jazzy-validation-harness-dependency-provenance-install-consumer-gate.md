# Stäubli SocketV2 Clean Jazzy Validation Harness、Dependency Provenance 与 Install Consumer Gate

- 节点：§9.3.308 / SERVO-891
- 日期：2026-11-10
- 固定上游：`ICube-Robotics/staubli_driver_ros2@bd658e2d266e315d2ee35f985fb352ea88306b79`
- 性质：验证方案与外部执行包；本节点没有运行 ROS、Docker、apt、rosdep、colcon 或 ABI 工具。

## 1. 本节点交付与关键结论

SERVO-890取得了完整、未截断的固定 Git Tree；本节点将尚缺的运行证据拆解为可执行的 clean Jazzy harness、依赖来源采集、install-space consumer、ABI归档和准入门禁。

**重要执行环境发现：** 固定上游 `.docker/Dockerfile` 在 `colcon build` 后执行：
```sh
rm -rf /opt/ros/staubli/staubli_robot_driver/include/
```
因此该 Docker 镜像的最终运行文件系统主动删除了 driver 安装头文件。它不能作为 public-header/install-space consumer 的验证基线。Consumer 必须针对未裁剪的 colcon install space（或独立安装前缀）执行；不能在该 Dockerfile 最终镜像中执行后宣称头文件导出验证通过。

固定上游相关 blob：
- Dockerfile：`52f7a4fce898a33ca5dfb6155eb396bf1dd6592c`
- CI workflow：`7073f620d30f10cf595c4211188d349f279ef16e`
- driver CMake：`b21608627b53d66f9910d9a836b053cd7d7fd6bf`
- package.xml：`50ad11f1336aab87a9afca6b9751de9fb6766595`
- installed public header `real_time_socket_subscriber.hpp`：`330839cb25e53fe961541f29f634722bec4a47c4`

## 2. 当前依赖/构建风险矩阵

| 项目 | 固定源码事实 | 需要的运行证据 |
|---|---|---|
| `asio_SOURCE_DIR` | CMake PUBLIC include path使用变量；完整树未发现定义或Asio子树 | configure trace/cache、最终 include directories、路径存在性 |
| Boost.Asio | UDP Impl include `boost/asio.hpp`；CMake REQUIRED Boost system并链接 `Boost::system` | rosdep结果、apt包版本、编译器实际 include与链接记录 |
| backward_ros | CMake REQUIRED查找；package.xml未显式声明 | rosdep能否从干净镜像安装、CMake package config来源 |
| realtime_tools | package.xml/ament_target_dependencies声明；未列入 ament_export_dependencies；已安装 public header直接include realtime_tools头 | 下游独立 consumer是否需要显式 find_package/ament dependency，导出 metadata 是否闭合 |
| TCP façade | Impl header不存在，tcp cpp不进主库target，factory拒绝TCP | 本轮不做TCP运行测试；在实现范围外明确不可用 |
| ABI | 无固定环境构建产物 | so/debug info/compile_commands/ABI dump与工具链锁定 |

静态风险不能直接推断干净构建一定失败。任何实际 PASS 必须绑定 runner、镜像 digest、依赖版本、源码 SHA 和原始日志。

## 3. Clean Jazzy runner 规格

### 3.1 不可变输入

外部 CI/开发者执行前必须创建 evidence manifest，至少记录：
- 上游 repository URL 与固定 commit SHA；
- runner OS/architecture、kernel；
- OCI image 的完整 repository@sha256 digest（禁止只记录 `ubuntu-noble-latest` 或 `jazzy-desktop-full`）；
- ROS apt repository snapshot 时间戳/快照地址；
- 所有 apt 包的精确版本（尤其 GCC/G++、binutils、CMake、Boost、ROS Jazzy相关包、backward_ros、realtime_tools）；
- Python、colcon、rosdep、vcstool 版本；
- locale、timezone、环境变量、CMake/colcon参数；
- 工作区干净状态、源码 commit、子模块/外部源清单；
- build/test/install 产物的 SHA256。

固定上游当前 CI 使用 `ubuntu-latest` runner、`rostooling/setup-ros-docker:ubuntu-noble-latest` 和 `ros-tooling/action-ros-ci@0.4.8`；Dockerfile基于可变 `osrf/ros:${ROS_DISTRO}-desktop-full` 并运行 apt-get update/upgrade。该配置适合持续集成，不是可复现 ABI 基线。

### 3.2 Clean build 最小复现命令

以下命令是给固定 digest 的 Ubuntu 24.04 / ROS 2 Jazzy runner 的执行模板，不是本轮已运行结果。镜像与 apt snapshot 必须由执行方填入并锁定：

```bash
set -euo pipefail
export ROS_DISTRO=jazzy
export WS="$PWD/staubli-jazzy-evidence"
export SRC="$WS/src/staubli_driver_ros2"
export INSTALL="$WS/install"

mkdir -p "$WS/src" "$WS/evidence"
git clone https://github.com/ICube-Robotics/staubli_driver_ros2.git "$SRC"
git -C "$SRC" checkout --detach bd658e2d266e315d2ee35f985fb352ea88306b79
test "$(git -C "$SRC" rev-parse HEAD)" = "bd658e2d266e315d2ee35f985fb352ea88306b79"
git -C "$SRC" status --porcelain=v1 | tee "$WS/evidence/source-status.txt"
git -C "$SRC" ls-tree -r HEAD > "$WS/evidence/source-tree.txt"

source /opt/ros/jazzy/setup.bash
printenv | sort > "$WS/evidence/environment.txt"
uname -a > "$WS/evidence/uname.txt"
cat /etc/os-release > "$WS/evidence/os-release.txt"
dpkg-query -W -f='${binary:Package}\t${Version}\n' | sort > "$WS/evidence/dpkg-packages.tsv"
gcc --version > "$WS/evidence/gcc-version.txt"
g++ --version > "$WS/evidence/gxx-version.txt"
cmake --version > "$WS/evidence/cmake-version.txt"
colcon version-check > "$WS/evidence/colcon-version.txt" 2>&1 || true
rosdep --version > "$WS/evidence/rosdep-version.txt"

cd "$WS"
rosdep update
rosdep install --from-paths src --ignore-src --rosdistro jazzy -r -y 2>&1 | tee evidence/rosdep-install.log

colcon build --event-handlers console_direct+ \
  --build-base build --install-base "$INSTALL" --log-base log \
  --cmake-args -DCMAKE_BUILD_TYPE=RelWithDebInfo \
               -DCMAKE_EXPORT_COMPILE_COMMANDS=ON \
  2>&1 | tee evidence/colcon-build.log

colcon test --event-handlers console_direct+ --return-code-on-test-failure \
  2>&1 | tee evidence/colcon-test.log
colcon test-result --verbose 2>&1 | tee evidence/colcon-test-result.log

find build -name compile_commands.json -print -exec cp --parents {} evidence/ \;
find "$INSTALL" -type f -print | sort > evidence/install-manifest.txt
find "$INSTALL" -type f \( -name '*.so' -o -name '*.so.*' -o -name '*.a' \) -print0 \
  | sort -z | xargs -0 -r sha256sum > evidence/library-sha256.txt
```

**Asio provenance must be observed, not guessed.** 在该 workspace 中另行保存 driver CMake configure trace/cache/verbose build 记录；确认 `asio_SOURCE_DIR` 的实际值、变量由谁注入、最终 include path是否存在，以及编译命令是否实际使用该目录。若变量为空或路径不存在，记录完整 CMake诊断；不得通过随意设置变量把问题“修好”后再声称验证了原始固定提交。任何修正实验必须另开独立 patch/实验分支并保留前后差异。

建议附加诊断命令（在单独诊断配置目录执行，保留原始 build）：
```bash
cmake -LAH -N build/staubli_robot_driver 2>&1 | tee evidence/cmake-cache-list.txt
grep -RIn -- 'asio_SOURCE_DIR\|Boost_DIR\|backward_ros_DIR\|realtime_tools_DIR' build/staubli_robot_driver evidence \
  | tee evidence/dependency-config-search.txt
grep -RIn -- 'boost/asio.hpp\|asio/include' build/staubli_robot_driver \
  | tee evidence/asio-include-search.txt
```
若 colcon生成目录名不同，按实际目录调整并记录，不得静默省略。

## 4. Install-space 独立 consumer fixture

### 4.1 验证原则

- 使用上一步未经 Dockerfile 删除头文件的 `$INSTALL`。
- 在全新 workspace 中创建独立 ament_cmake package；不得把 Staubli 源码目录、build目录或原 workspace 的 build include 路径加入 consumer。
- 只 source ROS Jazzy 与被测 install prefix；consumer 自己声明依赖。
- 至少编译包含 public headers 的 TU，并归档 CMake configure、compile command、install prefix和失败日志。
- 分两轮测试：A. consumer 只声明 `staubli_robot_driver`；B. 按公共头文件实际依赖显式声明 `realtime_tools`。若 A 失败、B 通过，说明 export dependency closure存在问题/consumer必须显式补依赖；不得把 B 通过误报成 A 通过。

### 4.2 Fixture package.xml

```xml
<?xml version="1.0"?>
<package format="3">
  <name>staubli_install_consumer_probe</name>
  <version>0.0.1</version>
  <description>Install-space public-header consumer probe</description>
  <maintainer email="validation@example.invalid">Validation</maintainer>
  <license>Apache-2.0</license>
  <buildtool_depend>ament_cmake</buildtool_depend>
  <depend>staubli_robot_driver</depend>
  <export><build_type>ament_cmake</build_type></export>
</package>
```

### 4.3 Fixture CMakeLists.txt

```cmake
cmake_minimum_required(VERSION 3.8)
project(staubli_install_consumer_probe)
find_package(ament_cmake REQUIRED)
find_package(staubli_robot_driver REQUIRED)
add_library(public_header_probe OBJECT src/public_header_probe.cpp)
ament_target_dependencies(public_header_probe staubli_robot_driver)
install(TARGETS public_header_probe DESTINATION lib)
ament_package()
```

第二轮（显式 realtime_tools）在 package.xml 添加 `<depend>realtime_tools</depend>`，CMake添加 `find_package(realtime_tools REQUIRED)` 并将它加入 `ament_target_dependencies`；两轮结果必须分别记录。

### 4.4 Fixture translation unit

```cpp
#include <staubli_robot_driver/communication/socket.hpp>
#include <staubli_robot_driver/communication/udp_socket.hpp>
#include <staubli_robot_driver/real_time_socket_subscriber.hpp>

void staubli_public_header_probe() {}
```

### 4.5 执行

```bash
source /opt/ros/jazzy/setup.bash
source "$INSTALL/setup.bash"
mkdir -p "$WS/consumer_ws/src/staubli_install_consumer_probe"
# 将上述 package.xml、CMakeLists.txt、translation unit 放入对应路径
cd "$WS/consumer_ws"
colcon build --event-handlers console_direct+ --cmake-args -DCMAKE_EXPORT_COMPILE_COMMANDS=ON \
  2>&1 | tee "$WS/evidence/consumer-build-no-extra-realtime-tools.log"
```

上述第一轮预期作为诊断探针，不预设成功或失败。再执行显式 realtime_tools 第二轮并单独归档。检查安装前缀中 `include/staubli_robot_driver`、ament index、`share/staubli_robot_driver`、导出 CMake config/targets、`package.xml`、libraries 与 plugin description metadata。注意：consumer TU 只证明头文件/依赖可用，不证明 ABI 或 plugin 可加载。

## 5. ABI / plugin 证据包

必须与 clean build 使用完全相同的镜像 digest、apt snapshot、工具链和 CMake参数，并归档：
- `compile_commands.json`、完整构建日志、CMakeCache及target属性；
- 主库和 hardware interface 的共享库、未剥离 debug symbols、SHA256；
- `readelf -d`、`readelf -Ws`、`nm -D --defined-only` 输出；
- `abi-dumper` / `abi-compliance-checker`（或组织批准的等价工具）版本、命令、输入与输出；
- install manifest、导出 targets/config、ament dependency metadata、plugin XML；
- 独立 consumer build日志与生成的 compile command；
- 基线 commit、镜像 digest、包版本和所有工件 hash。

当前没有同环境的旧版/新版二进制对照物，因此本节点不生成 ABI PASS/FAIL 结论。单次构建产物只能成为候选 baseline，需保存后再用于后续变更比较。

## 6. Evidence manifest 最小字段

每次运行创建 `evidence-manifest.yaml`：
```yaml
upstream:
  repository: https://github.com/ICube-Robotics/staubli_driver_ros2
  commit: bd658e2d266e315d2ee35f985fb352ea88306b79
  tree: 257face41970c91f95890ddf47db40b168eca331
runner:
  os_image: REQUIRED_IMMUTABLE_IMAGE_REFERENCE
  image_digest: REQUIRED_SHA256
  architecture: REQUIRED
  kernel: REQUIRED
  apt_snapshot: REQUIRED
toolchain:
  gcc: REQUIRED_EXACT_VERSION
  gxx: REQUIRED_EXACT_VERSION
  cmake: REQUIRED_EXACT_VERSION
  boost: REQUIRED_EXACT_VERSION
  ros_distro: jazzy
  colcon: REQUIRED_EXACT_VERSION
results:
  rosdep: NOT_RUN
  colcon_build: NOT_RUN
  colcon_test: NOT_RUN
  install_consumer_minimal: NOT_RUN
  install_consumer_with_realtime_tools: NOT_RUN
  abi_baseline: BLOCKED
artifacts:
  manifest_sha256: REQUIRED
  logs_sha256: REQUIRED
  compile_commands_sha256: REQUIRED
  shared_libraries_sha256: REQUIRED
```
不得将模板中的 REQUIRED 字段保留为已完成值；没有数据就标记 NOT_CAPTURED。

## 7. A1.1 Gate Checklist

| Gate | 通过条件 | 当前状态 |
|---|---|---|
| G-01 Source pin | 固定 commit/tree与干净工作区可复核 | STATIC_REVIEWED |
| G-02 OCI/apt pin | 镜像 digest、apt snapshot、精确包版本完整 | NOT_RUN |
| G-03 Asio provenance | `asio_SOURCE_DIR`来源和实际 include path已证明 | BLOCKED |
| G-04 Dependency closure | Boost/backward_ros/realtime_tools的rosdep、CMake、ament export闭合 | NOT_RUN |
| G-05 Clean build | 干净 Jazzy rosdep、colcon build成功且日志归档 | NOT_RUN |
| G-06 Tests | colcon test与test-result成功，失败项解释完整 | NOT_RUN |
| G-07 Install consumer | 原始 install space独立consumer通过，A/B差异已解释 | NOT_RUN |
| G-08 ABI baseline | so/debug info/compile commands/ABI dump可复现归档 | BLOCKED |
| G-09 Plugin/export | plugin metadata、DT_NEEDED、导出符号与consumer验证 | NOT_RUN |
| G-10 Test isolation | BUILD_TESTING ON/OFF及Fake/test-only不污染生产/install/export | NOT_RUN |
| G-11 Scope authorization | 不越权修改上游；TODO-EXT-001仍需单独授权 | BLOCKED |

**A1.1 当前仍 BLOCKED。** 只有全部适用 Gate 有可审计证据，才可提交新的准入评审；本报告不授权实现、不授权上游 PR，也不把验证计划视为验证通过。

## 8. 本轮状态与下一步

- HARNESS-01：SPECIFIED（clean Jazzy命令模板与证据字段）。
- DEPS-01：SPECIFIED（Asio/Boost/backward_ros/realtime_tools采集方案）。
- CONSUMER-01：SPECIFIED（独立install-space consumer A/B fixture）。
- DOCKER-01：STATIC_REVIEWED（Dockerfile会删除已安装driver include目录）。
- BUILD-01、TEST-01、CONSUMER-RUN-01、ABI-01、PLUGIN-01：NOT_RUN。
- GATE-01：BLOCKED。

未执行 Docker、apt、rosdep、CMake configure、colcon build/test、consumer、ABI工具、plugin load/unload、sanitizer或硬件测试；未修改固定上游、未创建/应用/合并PR；`TODO-EXT-001`仍未授权。历史同步缺口 §9.3.281–§9.3.294继续保留。

**下一节点：§9.3.309 / SERVO-892**：对固定commit的安装导出与plugin packaging做逐项静态核验（exported CMake targets/config、ament index、plugin XML安装路径、PUBLIC header闭包与动态库依赖清单），并把SERVO-891的外部运行证据需求转换为CI artifact acceptance schema；未获得真实运行日志前，所有运行状态保持NOT_RUN。
