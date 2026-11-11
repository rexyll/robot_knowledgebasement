# Stäubli SERVO-901：Fake Harness Header 与 Target Graph 静态验收设计

- 节点：§9.3.318 / SERVO-901
- 日期：2026-11-11
- 仓库：rexyll/robot_knowledgebasement，main
- 上游基线：ICube-Robotics/staubli_driver_ros2@bd658e2d266e315d2ee35f985fb352ea88306b79
- 范围：知识库侧validator、schema、测试和CI接入；不修改上游driver，不宣称执行C++/ROS测试。

## 1. 本节点交付

新增：
- \`scripts/validate_staubli_fake_harness_target_graph.py\`：校验BUILD_TESTING双配置的归一化CMake target快照。
- \`tests/test_staubli_fake_harness_target_graph.py\`：正向与负向validator测试。
- \`docs/schemas/staubli-fake-harness-target-graph.schema.json\`：快照输入合同。

## 2. 验收规则

1. BUILD_TESTING=OFF时，Fake test-support和unit-test targets必须不存在。
2. BUILD_TESTING=ON时，production targets和test-only targets均应按合同出现。
3. 从production core与plugin根节点计算传递依赖闭包，禁止FakeClock、Barrier/Latch、DeterministicExecutor、FaultInjector及test-support target。
4. install manifest不得包含测试头文件、库或Fake标识。
5. exported targets不得包含test-support。
6. plugin传递依赖闭包不得包含Fake/test-only组件。
7. 输入target名称重复、依赖字段格式错误或快照结构错误时fail closed。

## 3. 输入快照与限制

Validator消费由外部CMake File API collector生成的归一化JSON快照。快照需分别来自BUILD_TESTING=OFF和ON的独立构建目录。该工具不自行运行CMake，也不从源码文本猜测target graph；快照必须记录configuration_id、build_testing、targets/dependencies、install_entries及exported_targets。

当前CI只可运行知识库Python validator测试；在真实ROS/CMake环境接入collector之前，不能把合成快照测试称为真实target graph PASS。

## 4. Header 自包含编译合同

未来每个Fake public test header必须单独作为首个include编译，使用C++17并启用-Wall -Wextra -Wpedantic；测试translation unit不得预先include其他项目头文件来掩盖缺失include。至少覆盖FakeClock、Barrier、Latch、DeterministicExecutor、FaultInjector。该步骤需要真实C++编译器与头文件实现，本节点未执行，状态NOT_RUN。

## 5. 状态

| 项目 | 状态 |
|---|---|
| 快照Schema | SPECIFIED |
| Validator实现 | IMPLEMENTED（知识库Python工具） |
| 负向/正向单测 | IMPLEMENTED；CI结果待触发确认 |
| CMake File API collector | NOT_IMPLEMENTED |
| 真实BUILD_TESTING双配置 | NOT_RUN |
| C++ header self-containment | NOT_RUN |
| install/ament export实测 | NOT_RUN |
| plugin dependency graph实测 | NOT_RUN |
| C++/ROS/plugin/ABI/TSan/ASan/HIL | NOT_RUN |

## 6. 安全边界与下一节点

没有修改固定上游源码，没有创建、应用或合并上游PR；TODO-EXT-001仍未授权，A1.1保持BLOCKED。SERVO-901仅完成知识库侧验收工具骨架，不能替代真实CMake File API collector或C++编译。

下一节点：§9.3.319 / SERVO-902，设计并实现独立CMake File API snapshot collector及可复现双配置构建脚本；先在知识库CI中验证collector对合成codemodel的解析，再明确ROS Jazzy外部执行要求。
