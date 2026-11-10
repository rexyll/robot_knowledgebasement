# Stäubli GPIO 型号配置校验与 Xacro 递归边界审计追加件

- 日期：2026-11-10
- 审计编号：§9.3.263 / SERVO-846
- 固定上游：`ICube-Robotics/staubli_driver_ros2@bd658e2d266e315d2ee35f985fb352ea88306b79`
- 范围：GPIO 数量字段在 robot_model.yaml → Xacro 配置加载/校验 → ros2_control GPIO 接口递归生成 → C++ hardware parameter 解析之间的输入约束一致性。
- 方法：固定提交静态源码与现有测试审查；未运行 Xacro 或 ROS 2 测试。

## 主要发现

1. **现有模型配置校验没有覆盖 GPIO 数量字段。** `load_robot_model_config` 从 `robot_model['io']` 直接读取四个数量键（`staubli_robot_description/urdf/include/staubli_helpers.xacro`，约49–52行），之后调用 `check_robot_model_config`。该检查宏只验证关节/连杆数组非空、连杆数量关系和末端执行器父连杆合法性（约226–252行），没有验证 `io` 映射是否存在、四个键是否齐全、值是否为整数、是否非负或是否在协议容量内。当前两套TX2 YAML提供16/16/2/2，因此未证明现有型号配置失效；缺失/错误字段的实际Xacro报错形式尚未执行确认。

2. **Xacro GPIO递归宏使用“相等”作为终止条件，缺少单调边界保护。** `add_numbered_gpios` 在 `current_idx != num_gpios` 时生成接口并递归调用，下一轮只将 `current_idx` 加1（`r2c/include/staubli_r2c_gpios.xacro`，约8–30行）。正常非负整数可到达相等终点；负数、非整数或非数值类型若进入该宏，递增整数可能永远无法与目标值相等，导致递归持续展开直至Xacro/Python递归限制或处理失败。该风险是由控制流静态推导的边界风险，不代表当前TX2配置含有非法值，也未通过运行Xacro复现。

3. **C++与Xacro对同一字段的解析/约束并不等价。** `StaubliHardwareInterface::on_init` 对四个字段调用 `std::stoul`，捕获异常后检查数字IO≤16、模拟IO≤4，再resize向量（`staubli_robot_driver/src/staubli_hardware_interface.cpp`，约100–133行）。未传入/检查 `pos`，因此 `16junk` 这类有合法数字前缀的字符串可能被按前缀解析并通过上限检查；`2.5` 可能被解析为2。该行为需在目标编译器/标准库测试确认，本轮没有运行参数注入。C++的上限检查也不能阻止单独Xacro展开阶段先处理非法数值。

4. **Xacro与C++目前缺少统一的GPIO schema。** 型号YAML直接承载四个数量，Xacro将其传入硬件参数并用于生成接口，C++再次解析并按相同数量创建缓存。没有单一、显式的约束定义说明0是否允许、数字/模拟输入输出各自的产品选件范围、字段类型及协议上限。当前TX2 16/16/2/2在静态容量上相符；这不等于现场模块、VAL3变量、CS9映射和端子接线已验证。

5. **现有测试没有覆盖异常数量配置的拒绝行为。** `test_staubli_hardware_interface.cpp` 的fixture固定使用16/16/2/2；`InterfaceExport`主要断言接口总数和部分关节/监督接口名称，没有看到0、最大值+1、负数、浮点、尾随字符、缺键及Xacro接口生成物专项测试。测试代码审查不等于本轮执行测试。

## SERVO-846 验收矩阵

| ID | 验收项 | 状态 |
|---|---|---|
| GPIOV1 | 固定提交与两套TX2型号GPIO配置核对 | 静态核对完成：均为16/16/2/2 |
| GPIOV2 | Xacro配置加载字段路径核对 | 静态核对完成：直接读取四个io键 |
| GPIOV3 | check_robot_model_config覆盖范围 | 静态核对完成：未检查GPIO数量schema |
| GPIOV4 | Xacro递归终止条件 | 静态核对完成：使用相等判断；非法类型/范围未执行 |
| GPIOV5 | C++ std::stoul完整字符串消费 | 静态核对完成：未检查pos |
| GPIOV6 | Xacro与C++容量约束一致性 | 静态核对完成：插件有16/4上限，Xacro端未见等价上限门禁 |
| GPIOV7 | 缺失、空值、负数、浮点、尾随字符注入 | 未执行 |
| GPIOV8 | Xacro展开失败/终止边界验证 | 未执行 |
| GPIOV9 | 参数化C++单测及生成接口断言 | 未执行；现有测试未见专项覆盖 |
| GPIOV10 | VAL3/CS9实际IO模块、变量与端子映射 | 缺现场配置/接线清单与签核证据，未执行 |

## 整改建议

- 定义唯一GPIO配置schema：四个字段必填、类型严格为整数，明确0值语义、数字/模拟容量、型号选件范围，并由Xacro和C++共同遵循。
- 在Xacro加载阶段先校验io对象及四个字段的存在性、整数性、有限性、非负性和上限；使用明确的 `current_idx < num_gpios` 递归条件，并对负数/非整数 fail-fast，避免以“永远不相等”作为控制流。
- C++改用严格整数解析并检查完整字符串消费；拒绝尾随字符、小数文本、负数、溢出和缺失字段，统一输出字段名与允许范围。
- 将同一组边界用例用于Xacro与C++：0、1、最大值、最大值+1、负数、浮点、字符串、空值、缺失键、`16junk`、超大整数；对有效配置断言接口名称/数量与缓存大小完全一致。
- 增加两型号的Xacro展开回归测试；之后在隔离环境核对ROS接口、VAL3数据库、CS9选件模块和现场端子映射。普通GPIO不得承担急停或其他安全功能。

## 证据与边界

- [hardware_interface.cpp](https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/src/staubli_hardware_interface.cpp)：约100–133行。
- [staubli_helpers.xacro](https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_description/urdf/include/staubli_helpers.xacro)：约49–52、156–157、226–252行。
- [staubli_r2c_gpios.xacro](https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_description/r2c/include/staubli_r2c_gpios.xacro)：约8–30行。
- [hardware interface tests](https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/test/unit_tests/test_staubli_hardware_interface.cpp)：初始化fixture与InterfaceExport测试。

本轮仅完成固定上游提交的静态YAML/Xacro/C++/测试代码审查；未执行Xacro展开、参数注入、ROS 2构建/单测、协议黄金帧、VAL3编译/下载、CS9配置读取、端子逐点测试、SIL/HIL、FAT/SAT或实机验证。未修改上游、未应用PR。工程级验收仍未通过，`TODO-EXT-001`未授权合并。
