# Stäubli SERVO-903：确定性构建环境与证据封装

- 节点：§9.3.320 / SERVO-903
- 日期：2026-11-11
- 仓库：rexyll/robot_knowledgebasement，main
- 固定上游基线：ICube-Robotics/staubli_driver_ros2@bd658e2d266e315d2ee35f985fb352ea88306b79
- 变更范围：仅知识库采集工具、证据封装工具、测试、Schema和文档；不修改上游源码。

## 本节点交付

1. scripts/collect_staubli_cmake_file_api.py 增加 --export-root。仅扫描指定安装前缀下的 lib/cmake/**/**Targets.cmake 和 share/**/cmake/**Targets.cmake，从 add_library(... IMPORTED) / add_executable(... IMPORTED) 声明提取目标名，并记录来源文件。显式导出清单与扫描根目录互斥。此扫描是静态提取，不替代 install-space consumer 编译或 plugin load 测试。
2. scripts/package_staubli_build_evidence.py 提供 fingerprint、package、verify 三个动作。环境指纹记录OS/架构、Python、CMake、编译器、colcon、ROS_DISTRO、受控环境变量白名单及源码Git commit/dirty状态。无法读取的字段统一写 UNKNOWN，不根据预期规格伪造版本。
3. 证据包将 BUILD_TESTING OFF/ON快照、SERVO-901 validator报告、环境指纹和可选命令日志复制到独立目录，生成含文件大小和SHA-256的 evidence_manifest.json。verify 对缺失文件、大小/哈希不匹配及路径越界 fail closed。
4. 新增合成测试覆盖UNKNOWN环境字段、正常打包校验、文件篡改、文件缺失及路径穿越。

## 可复现环境合同

每次真实采集应保存：
- 固定上游源码commit及dirty状态；
- OS发行版/架构、Python、CMake、C/C++编译器、ROS发行版和colcon版本；
- CMake generator、toolchain file、CMAKE_PREFIX_PATH、AMENT_PREFIX_PATH、COLCON_PREFIX_PATH、PKG_CONFIG_PATH；
- BUILD_TESTING模式、configure命令、退出码和完整stdout/stderr；
- OFF/ON各自的codemodel快照、install manifest、导出目标来源文件、validator报告；
- 每个归档文件的SHA-256、大小和UTC采集时间。

本仓库只记录实际捕获值。UNKNOWN 表示当前环境未提供或工具不可用；在外部CI中应通过锁定容器镜像digest、依赖快照和工具链版本进一步实现环境固定。当前工具采集指纹但不强制某个未经用户确认的版本号。

## 使用示例

python3 scripts/package_staubli_build_evidence.py fingerprint --source-dir "$SOURCE_DIR" --output "$OUTPUT_DIR/environment-fingerprint.json"

python3 scripts/package_staubli_build_evidence.py package --output-dir "$OUTPUT_DIR/evidence" --build-off "$OUTPUT_DIR/build-testing-off.json" --build-on "$OUTPUT_DIR/build-testing-on.json" --validator-report "$OUTPUT_DIR/servo-901-validation-report.json" --source-dir "$SOURCE_DIR" --command-log "$OUTPUT_DIR/configure.log"

python3 scripts/package_staubli_build_evidence.py verify --manifest "$OUTPUT_DIR/evidence/evidence_manifest.json"

## 验收状态

| 项目 | 状态 |
|---|---|
| export-root限定扫描与来源记录 | IMPLEMENTED；合成测试待CI |
| 环境指纹采集与UNKNOWN策略 | IMPLEMENTED；未采集真实ROS Jazzy环境 |
| evidence manifest与SHA-256校验 | IMPLEMENTED；合成测试待CI |
| 缺失/篡改/路径穿越负向测试 | IMPLEMENTED；CI待确认 |
| 真实BUILD_TESTING OFF/ON configure | NOT_RUN |
| 真实install/export consumer验证 | NOT_RUN |
| C++/ROS/plugin/ABI/TSan/ASan/HIL | NOT_RUN |

SERVO-902的configure脚本当前不自动生成证据包；本节点提供独立封装命令，调用者需将真实configure命令及输出日志一并传入。未观察到CI执行结果，不能宣称新增测试通过。A1.1继续BLOCKED；RACE-01–16与EXEC-01–04均未执行；TODO-EXT-001未授权。

下一节点：§9.3.321 / SERVO-904，围绕证据包接入CI矩阵并建立可追溯的真实外部运行记录；先审阅现有workflow，再决定最小集成范围。
