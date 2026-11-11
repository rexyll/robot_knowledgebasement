# Stäubli SERVO-902：CMake File API Collector 与双配置快照采集

- 节点：§9.3.319 / SERVO-902
- 日期：2026-11-11
- 仓库：rexyll/robot_knowledgebasement，main
- 上游固定基线：ICube-Robotics/staubli_driver_ros2@bd658e2d266e315d2ee35f985fb352ea88306b79
- 范围：知识库侧采集器、双配置脚本、fixture测试与schema；不修改上游源码。

## 新增交付
- scripts/collect_staubli_cmake_file_api.py：解析codemodel-v2配置、targets、target依赖、compile group include目录与定义。
- scripts/run_staubli_build_testing_matrix.sh：在独立构建目录配置BUILD_TESTING=OFF/ON，预先请求codemodel-v2，采集两份快照并调用SERVO-901 validator。
- tests/test_staubli_cmake_file_api.py：合成reply fixture覆盖依赖映射、include/define提取、install manifest、显式export列表和错误输入。
- docs/schemas/staubli-cmake-file-api-snapshot.schema.json：快照Schema。

## 数据合同
输出与SERVO-901 validator兼容：configuration_id、build_testing、targets[{name,type,dependencies,include_directories,compile_definitions}]、install_entries、exported_targets。依赖通过codemodel target ID映射；未知ID不猜测。Exported targets由显式文本文件提供，因为codemodel-v2不提供可移植的已安装export manifest。install_manifest.txt缺失时输出空列表，但附带限制，不能视为已验证没有安装内容。

## 执行方式
在具备项目依赖的ROS/CMake环境设置SOURCE_DIR、OUTPUT_DIR，再执行scripts/run_staubli_build_testing_matrix.sh。可选BUILD_ROOT。脚本只执行configure和采集，不执行编译、ctest、plugin加载或硬件测试。

## 验收状态
| 项目 | 状态 |
|---|---|
| codemodel-v2 Collector | IMPLEMENTED |
| BUILD_TESTING双配置脚本 | IMPLEMENTED |
| 合成fixture测试 | IMPLEMENTED；CI待确认 |
| Install Manifest采集 | IMPLEMENTED；缺失时明确限制 |
| Export target列表 | IMPLEMENTED；显式输入，不自动推断 |
| ROS Jazzy真实双配置 | NOT_RUN |
| 真实install/export验证 | NOT_RUN |
| C++/ROS/plugin/ABI/sanitizer/HIL | NOT_RUN |

Fixture测试只证明合成输入解析行为，不证明上游工程配置成功。未运行ROS Jazzy真实双配置、C++编译、header自包含、gtest、plugin load/unload、ABI、TSan/ASan或HIL。

下一节点：§9.3.320 / SERVO-903，补齐确定性configure环境合同、真实导出target采集策略与构建矩阵证据封装。TODO-EXT-001仍未授权，A1.1保持BLOCKED。
