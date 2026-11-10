# Stäubli SocketV2 安装导出、Plugin Packaging 与 CI Artifact Acceptance 审查

- 节点：§9.3.309 / SERVO-892
- 日期：2026-11-10
- 固定上游：`ICube-Robotics/staubli_driver_ros2@bd658e2d266e315d2ee35f985fb352ea88306b79`
- 固定上游 Tree：`257face41970c91f95890ddf47db40b168eca331`（递归树284 entries，未截断）
- 性质：只读静态源码/构建声明审查与CI证据契约；未运行CMake、colcon、ROS、pluginlib、readelf或动态加载。

## 1. 本节点结论

本节点确认了安装导出与plugin声明的静态结构，同时发现至少三类需要在clean install-space consumer和plugin运行验证中闭合的风险：

1. `real_time_socket_subscriber.hpp`是安装public header，并直接include `realtime_tools/realtime_thread_safe_box.hpp`；包已在`ament_target_dependencies`和package.xml声明realtime_tools，但`ament_export_dependencies`遗漏它。消费者依赖闭包不能仅凭producer自身构建推定完整。
2. 主库PUBLIC include目录含裸的`${asio_SOURCE_DIR}/asio/include`，不是BUILD_INTERFACE/INSTALL_INTERFACE隔离项。该路径可能进入导出的INTERFACE_INCLUDE_DIRECTORIES；其值与导出后是否存在必须由CMake生成的export target/config及独立consumer实测确认。固定树未发现该变量的定义来源，仍UNRESOLVED。
3. CMake REQUIRED查找并链接Boost::system、REQUIRED查找backward_ros，但package.xml未显式声明boost/backward_ros；`ament_export_dependencies`也未导出Boost/backward_ros。是否导致rosdep或consumer失败需由干净环境验证，不将静态不对称直接判为必然失败。

Plugin XML与hardware interface target的静态名称链条一致：XML library为`staubli_robot_driver_hardware_interface`，与CMake实际target名一致；class type/base_class_type与源文件中的`PLUGINLIB_EXPORT_CLASS`一致。CMake使用`pluginlib_export_plugin_description_file(hardware_interface staubli_hardware_interface.xml)`委托pluginlib/ament安装与索引登记；固定源码没有手写XML install destination。实际ament index内容、安装路径、pluginlib发现及dlopen均未验证。

## 2. 固定源码证据

| 文件 | Blob SHA | 关键事实 |
|---|---|---|
| `staubli_robot_driver/CMakeLists.txt` | `b21608627b53d66f9910d9a836b053cd7d7fd6bf` | 两个SHARED targets；install export set；ament export targets/dependencies；plugin macro |
| `staubli_robot_driver/package.xml` | `50ad11f1336aab87a9afca6b9751de9fb6766595` | format 3，ament_cmake；声明realtime_tools，未声明boost/backward_ros |
| `real_time_socket_subscriber.hpp` | `330839cb25e53fe961541f29f634722bec4a47c4` | public header直接include realtime_tools |
| `socket.hpp` | `230af198337e5d047b29b2bbf6354a698fb3a390` | 旧Socket纯虚接口及SocketFactory public API |
| `udp_socket.hpp` | `31eb5e2e9218e17160fc10dfbd72d77be4b3b0e5` | UDPSocket façade/PIMPL public API |
| `staubli_hardware_interface.xml` | `eb946e450ef8546b13e1be50836918236fc47966` | plugin library/class/type/base class声明 |
| `staubli_hardware_interface.cpp` | `4ae2b8c8d91857e5e32558bfcd16e2c391b9c3d0` | `PLUGINLIB_EXPORT_CLASS(StaubliHardwareInterface, hardware_interface::SystemInterface)` |

## 3. CMake targets 与安装导出

### 3.1 Target graph

- 主库target：`staubli_robot_driver`，类型SHARED；源文件清单包含protocol/messages/socket_factory/udp_socket/real_time_socket_subscriber/real_time_socket_interface/robot_driver/mock_robot_server；不包含tcp_socket.cpp。
- Hardware target：`staubli_robot_driver_hardware_interface`，类型SHARED；源文件为staubli_hardware_interface.cpp；链接主库target。
- 主库链接Boost::system；hardware target链接主库。ament dependencies列表含rclcpp、std_msgs、sensor_msgs、geometry_msgs、control_msgs、realtime_tools、hardware_interface、pluginlib、rclcpp_lifecycle。
- 两个库共同安装到lib（LIBRARY/ARCHIVE/RUNTIME destinations），并加入`export_staubli_robot_driver`导出集合。
- `INCLUDES DESTINATION include`，并通过`install(DIRECTORY include/ DESTINATION include)`安装整个include目录。
- `ament_export_targets(export_staubli_robot_driver HAS_LIBRARY_TARGET)`存在；没有显式`ament_export_include_directories`或`ament_export_libraries`。这不是自动缺陷：include路径可由导出的target携带；但最终导出config/target内容需安装后检查。
- `ament_export_dependencies`导出rclcpp、std_msgs、sensor_msgs、geometry_msgs、control_msgs、hardware_interface、pluginlib、rclcpp_lifecycle；漏掉target依赖/公共头闭包中重要的realtime_tools、Boost及backward_ros。
- package.xml build_type为ament_cmake。ament_package()负责生成ament package metadata/index marker与包配置；静态声明不能证明实际install tree生成内容。

### 3.2 Public header 与 include closure

`install(DIRECTORY include/ DESTINATION include)`无过滤规则，意味着include树内所有头文件都会进入install prefix。已核实的public header `real_time_socket_subscriber.hpp`直接include realtime_tools头文件。应在install-space中检查：
- 完整头文件清单与源include目录逐项一致；
- 是否意外安装仅供内部使用的头文件；
- public headers在独立translation unit中自包含；
- 每个外部头文件所属包都由消费者可发现的ament/CMake依赖提供；
- 安装导出的include路径不泄漏源码树、build树或不存在的外部Asio目录。

`asio_SOURCE_DIR`裸PUBLIC路径尤其需要CMake export属性检查：记录configure时变量值、target的INTERFACE_INCLUDE_DIRECTORIES、安装后导出的Targets文件内容，以及consumer实际编译命令。不可仅因为头文件未直接include Asio就忽略该导出路径污染风险。

### 3.3 需要安装后确认的ament artifacts

对未裁剪colcon install prefix保存以下精确清单：
- `share/ament_index/resource_index/packages/staubli_robot_driver` marker；
- `share/ament_index/resource_index/hardware_interface__pluginlib__plugin/staubli_robot_driver`（或该ROS发行版pluginlib宏实际生成的resource-index类型/文件名，以真实manifest为准）；
- `share/staubli_robot_driver/package.xml`；
- `share/staubli_robot_driver/cmake/*`导出配置与targets；
- `include/staubli_robot_driver/**`；
- `lib/libstaubli_robot_driver.so`及`lib/libstaubli_robot_driver_hardware_interface.so`；
- plugin XML的实际安装位置和resource-index中指向该XML的内容。

不要在报告中把上面列出的候选路径当成已观测结果。尤其pluginlib resource-index精确路径应以安装产物为准。

## 4. Plugin packaging 审查

XML声明：
- library path：`staubli_robot_driver_hardware_interface`
- class name：`staubli_robot_driver/StaubliHardwareInterface`
- type：`staubli_robot_driver::StaubliHardwareInterface`
- base_class_type：`hardware_interface::SystemInterface`

CMake调用pluginlib导出宏，源代码使用同一具体类和base class调用PLUGINLIB_EXPORT_CLASS。静态名称对应关系一致，没有发现library basename与target basename不一致。

尚未验证：
- plugin XML是否实际安装在宏期望的share路径；
- ament resource index是否登记正确package与XML路径；
- XML解析及pluginlib class discovery；
- 动态库实际DT_NEEDED、RPATH/RUNPATH与依赖库可解析性；
- 插件工厂实例化、初始化、卸载与重复加载；
- class factory symbols、visibility与ABI兼容性。

当前CMake没有显式设置`CXX_VISIBILITY_PRESET hidden`或可见性宏。仅从源码不能判断实际导出符号集合、默认编译器/ROS宏效果或动态符号表；必须以真实so的readelf/nm输出为准。

## 5. CI Artifact Acceptance Schema

每次验证运行必须产生一个不可变run目录，建议命名：
`artifacts/staubli-driver/<upstream-commit>/<runner-id>/<run-id>/`

必需文件：
1. `evidence-manifest.yaml`：schema版本、上游commit/tree、工作区状态、runner/OCI digest、apt snapshot、架构/内核、ROS distro、编译器/CMake/Boost/colcon/rosdep精确版本、构建参数、UTC时间。
2. `source/`：固定commit校验结果、递归tree清单、submodule/vcs来源清单。
3. `logs/`：rosdep、CMake configure trace、colcon build、colcon test、test-result、consumer A/B、plugin discovery/load/unload的原始stdout/stderr和退出码。
4. `install/`：install manifest、头文件清单、ament index、package.xml、导出CMake config/targets、plugin XML及resource-index内容。
5. `build/`：compile_commands、CMakeCache、target property dump、完整构建日志。
6. `binaries/`：两份共享库、未剥离debug symbols、SHA256、readelf -d/-Ws、nm -D输出。
7. `abi/`：工具版本、命令、基线/候选输入hash、ABI dump与比较报告；无可比基线时状态BLOCKED，不得造出空PASS。
8. `consumers/`：A仅声明staubli_robot_driver；B显式增加realtime_tools；两个独立workspace、package.xml/CMake/source、compile command和结果。
9. `checksums.sha256`：对所有工件生成稳定相对路径排序的SHA256清单；manifest记录自身hash的方式须避免循环（例如由外层run-index记录manifest hash）。

### 5.1 Manifest schema（字段契约示例）

```yaml
schema: staubli-ci-evidence/v1
run:
  id: REQUIRED
  started_at_utc: REQUIRED
  completed_at_utc: REQUIRED
source:
  repository: https://github.com/ICube-Robotics/staubli_driver_ros2
  commit: bd658e2d266e315d2ee35f985fb352ea88306b79
  tree: 257face41970c91f95890ddf47db40b168eca331
  worktree_clean: REQUIRED_BOOLEAN
runner:
  os_release: REQUIRED
  architecture: REQUIRED
  kernel: REQUIRED
  oci_image: REQUIRED_IMMUTABLE_REFERENCE
  oci_digest: REQUIRED_SHA256
  apt_snapshot: REQUIRED_IMMUTABLE_REFERENCE
toolchain:
  ros_distro: jazzy
  gcc: REQUIRED_EXACT_VERSION
  cmake: REQUIRED_EXACT_VERSION
  boost: REQUIRED_EXACT_VERSION
  colcon: REQUIRED_EXACT_VERSION
  rosdep: REQUIRED_EXACT_VERSION
build:
  cmake_args: REQUIRED_LIST
  build_exit_code: REQUIRED_INTEGER
  test_exit_code: REQUIRED_INTEGER
checks:
  rosdep: NOT_RUN
  clean_build: NOT_RUN
  unit_tests: NOT_RUN
  install_consumer_minimal: NOT_RUN
  install_consumer_realtime_tools: NOT_RUN
  plugin_index_discovery: NOT_RUN
  plugin_load_unload: NOT_RUN
  abi_comparison: BLOCKED
artifacts:
  install_manifest: REQUIRED_PATH_AND_SHA256
  compile_commands: REQUIRED_PATH_AND_SHA256
  shared_libraries: REQUIRED_PATHS_AND_SHA256
  debug_symbols: REQUIRED_PATHS_AND_SHA256
  readelf_nm: REQUIRED_PATHS_AND_SHA256
  raw_logs: REQUIRED_PATHS_AND_SHA256
  checksums_file: REQUIRED_PATH_AND_SHA256
```

### 5.2 Acceptance rules

- 每个检查状态只能是`PASS`、`FAIL`、`NOT_RUN`、`BLOCKED`或`NOT_APPLICABLE`；PASS必须引用工件路径、SHA256、退出码和判定脚本版本。
- 缺少日志、退出码、输入版本、工件hash或源码固定信息时，不得PASS。
- Consumer A/B必须分开运行并分别归档；B通过不能覆盖A失败。
- plugin discovery与plugin load/unload是两个独立检查；仅有XML不构成plugin PASS。
- ABI comparison必须有同工具链、同构建参数的可比较baseline；缺少baseline为BLOCKED。
- 工件必须保留失败日志，不得只上传成功摘要；重跑必须生成新run-id，禁止覆盖原始run。
- 汇总门禁不得把NOT_RUN/BLOCKED折算成PASS；A1.1保持BLOCKED，直到所有适用门禁有可复核证据。

## 6. 状态矩阵

| 项目 | 状态 | 说明 |
|---|---|---|
| TARGET-01 | STATIC_REVIEWED | 两个SHARED targets、主库依赖hardware interface、安装export set |
| EXPORT-01 | STATIC_REVIEWED | ament_export_targets存在；导出依赖清单存在遗漏风险 |
| HEADER-01 | STATIC_REVIEWED | include目录整体安装；subscriber public header include realtime_tools |
| ASIO-EXPORT-01 | BLOCKED | 裸PUBLIC Asio路径的导出值/路径有效性未取得 |
| PACKAGE-DEP-01 | STATIC_REVIEWED | realtime_tools声明存在；boost/backward_ros package.xml声明缺失 |
| PLUGIN-STATIC-01 | STATIC_REVIEWED | XML library/type/base class与target/source注册名称一致 |
| AMENT-INDEX-01 | NOT_RUN | 未生成/检查install tree |
| CONSUMER-A/B | NOT_RUN | 未运行独立install-space consumer |
| PLUGIN-DISCOVERY/LOAD | NOT_RUN | 未运行pluginlib discovery/load/unload |
| DT_NEEDED/SYMBOLS | NOT_RUN | 无二进制产物，未运行readelf/nm |
| ABI-01 | BLOCKED | 无同环境可比ABI baseline |
| ARTIFACT-SCHEMA-01 | SPECIFIED | 定义CI evidence manifest与artifact acceptance规则 |
| GATE-01 | BLOCKED | A1.1不得启动 |

## 7. 限制与下一节点

本节点只审查固定commit源码和静态构建声明；没有实际install prefix、CMake export files、shared libraries或plugin runtime结果。未运行Docker/apt/rosdep/CMake/colcon/gtest/consumer/pluginlib/readelf/nm/ABI/sanitizer/硬件测试。未修改固定上游、未创建/应用/合并上游PR；`TODO-EXT-001`仍未授权。历史同步缺口§9.3.281–§9.3.294继续透明保留。

**下一节点：§9.3.310 / SERVO-893**：将SocketV2 production/test target隔离、plugin unload与异步callback生命周期屏障、legacy ABI守护矩阵合并为一份可审查的架构决策与验收追踪矩阵；不进入上游实现，除非另行授权。
