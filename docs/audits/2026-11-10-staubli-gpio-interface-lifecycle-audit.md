# Stäubli GPIO 接口导出、状态更新与生命周期缓存一致性审计追加件

- 日期：2026-11-10
- 审计编号：§9.3.264 / SERVO-847
- 固定上游：`ICube-Robotics/staubli_driver_ros2@bd658e2d266e315d2ee35f985fb352ea88306b79`
- 范围：Xacro GPIO 声明与 C++ state/command interface 导出映射、GPIO状态更新语义、hardware lifecycle期间GPIO缓存行为及现有测试覆盖。
- 方法：固定提交静态源码与测试代码审查；未运行Xacro、ROS 2构建或测试。

## 主要发现

1. **正常配置下Xacro与C++的GPIO接口类别/命名规则静态一致。** `r2c_gpios_control_description`声明数字/模拟输入为state interface，数字/模拟输出为command interface；GPIO资源名为`${robot_prefix}gpio`，通道名为`digital_input_N`、`digital_output_N`、`analog_input_N`、`analog_output_N`。C++导出函数使用同一资源名规则和通道前缀，输入从`hw_*_inputs_`导出为state，输出从`hw_*_output_commands_`导出为command。两边均未将robot_prefix拼入通道名，而是拼入GPIO资源名。本轮为源码静态比对，未执行生成URDF与ResourceManager加载验证。

2. **输出反馈state interface被有意注释，不属于当前Xacro接口契约。** C++ `export_state_interfaces`中数字/模拟输出state导出代码处于注释块；Xacro也仅为输出声明command interface，没有声明输出state interface。当前state导出仅含数字/模拟输入及10个supervision状态。因此当前代码的输出命令/状态类别静态一致，但不能将命令缓存误认为实际输出反馈；若未来要提供物理输出回读，必须同步修改Xacro、C++、协议/状态消息和测试。

3. **输入状态字段缺失时，GPIO缓存保留旧值且read仍可能返回OK。** `update_state`仅在`has_digital_inputs`或`has_analog_inputs`为true时更新相应向量；标志为false时不清零、不报错，也不阻止函数最终返回true。只要关节位置和速度字段有效，`read`即可返回OK，而对应GPIO state interface继续暴露上一次成功更新的值或初始化0.0。对消费者而言，该数值没有新鲜度标记，可能被误认为当前输入状态。是否允许机器人固件按需省略IO字段需由协议规范确认；在未确认前应将“缺失字段保持旧值但read成功”列为状态有效性风险。

4. **on_activate仅将关节控制模式设为STOP，没有显式重置GPIO输出命令缓存。** 输出命令向量在`on_init`时resize并以0.0初始化；`on_activate`仅设置`current_control_mode_ = STOP`。而`write`无论STOP还是关节位置模式，都会把数字/模拟输出命令缓存复制到命令消息并发送。因而若一次停用/清理/重新激活流程中输出缓存仍保留先前值，后续write可能再次发送旧GPIO输出命令。ROS 2 controller manager的接口释放/重新分配和具体硬件周期行为尚未运行验证，因此这是由缓存生命周期与无条件输出序列化推导出的潜在重放风险，不宣称已在真实设备复现。建议明确安全默认值/保持策略，在激活、停用、错误和重连边界进行显式策略处理，并以mock协议捕获测试验证。

5. **现有InterfaceExport测试只验证总数和少量接口名称，且fixture固定空robot_prefix。** fixture使用16/16/2/2与空前缀；测试断言命令接口总数36、状态接口总数46，并只检查少数joint/supervision名称。没有逐通道断言GPIO输入/输出的完整名称集合、索引连续性、不同数量组合或非空robot_prefix。测试注释将命令接口数量描述为42但断言为36，文字算式与实际导出数量不一致；状态接口注释也仅说明假设输出反馈时为64，当前实际断言46。该注释问题不影响代码本身，但降低测试说明可读性。

6. **现有生命周期/IO测试没有覆盖GPIO缓存语义。** 生命周期测试使用mock server，主要检查关节位置/速度读回及position命令write成功；fixture默认没有设置`has_digital_inputs`和`has_analog_inputs`，也没有对GPIO缓存进行断言。未发现缺失IO字段、先有效后缺失、重连后缓存、停用再激活后输出缓存、STOP模式输出发送行为等专项用例。本轮未执行测试。

## SERVO-847 验收矩阵

| ID | 验收项 | 状态 |
|---|---|---|
| IF1 | Xacro GPIO资源名与C++资源名 | 静态一致：均为robot_prefix + gpio |
| IF2 | 四类GPIO通道命名 | 静态一致：数字/模拟输入输出通道名规则相同 |
| IF3 | 输入state/输出command类别 | 静态一致；输出反馈state未声明/未导出 |
| IF4 | 非空robot_prefix接口导出 | 未执行；现有fixture仅空前缀 |
| IF5 | 全部通道名称/数量/连续索引断言 | 未执行；现有测试仅总数和少量名称 |
| IF6 | 缺失数字/模拟输入字段时缓存行为 | 静态发现保留旧值且update_state仍可成功；未动态验证 |
| IF7 | GPIO输入数据新鲜度/缺失字段策略 | 未执行；需协议规范与运行时证据 |
| IF8 | on_activate/on_cleanup/on_error GPIO缓存重置策略 | 静态发现on_activate未重置GPIO输出命令；未运行生命周期边界 |
| IF9 | STOP模式下GPIO输出命令发送语义 | 静态发现write仍序列化输出；安全/产品语义待确认 |
| IF10 | 停用/重新激活/重连后的旧输出命令重放 | 潜在风险；mock捕获与实机验证未执行 |

## 整改建议

- 将接口契约以可测试的清单定义：每种型号、每个robot_prefix下，期望GPIO资源名、通道名、接口类别、数量和索引均由单一配置生成；用Xacro展开结果与C++导出结果做集合差异断言。
- 为非空前缀（例如`cell_a/`）增加完整导出测试，断言GPIO资源名为`cell_a/gpio`，通道名不重复添加前缀；同时覆盖零、部分和最大通道数。
- 明确协议对数字/模拟输入字段缺失的语义。若字段缺失表示本周期无有效样本，则应返回读取错误或暴露有效性/时间戳，不应静默将旧值当作当前值；若协议保证每帧必带，则缺失应被视为协议异常并测试。
- 为GPIO状态加入有效性策略：缺失字段不能在无标识的情况下继续呈现为新鲜状态；可选做法包括严格拒绝该状态帧、保留值同时暴露stale标志/时间戳，或按已确认协议语义明确置为无效值。
- 定义GPIO输出在STOP、deactivate、cleanup、error、shutdown和reconnect时的保持/复位策略；避免未经设计的缓存重放。若要求复位，必须同时确认控制器管理器接口写入顺序、控制器安全状态和控制器侧默认值，不能仅靠盲目清零制造输出瞬变。
- 增加mock server输出捕获测试：设置非零数字/模拟输出，触发生命周期切换，确认下一次write是否发送旧值；覆盖STOP和运动模式，并按批准的输出安全策略断言结果。
- 修正InterfaceExport测试注释算式，拆分成关节命令、GPIO命令、关节状态、GPIO输入状态、supervision状态的逐项期望值。

## 证据与边界

- [staubli_r2c_gpios.xacro](https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_description/r2c/include/staubli_r2c_gpios.xacro)：约4–73行。
- [staubli.r2c.xacro](https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_description/r2c/staubli.r2c.xacro)：约23–43、65–92行。
- [staubli_hardware_interface.cpp](https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/src/staubli_hardware_interface.cpp)：约98–133、188–243、246–393、395–496、624–686行。
- [test_staubli_hardware_interface.cpp](https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/test/unit_tests/test_staubli_hardware_interface.cpp)：约135–225、230–285行。
- [test_staubli_hardware_interface.hpp](https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/test/unit_tests/test_staubli_hardware_interface.hpp)：fixture默认空前缀、16/16/2/2，mock状态未置GPIO输入有效标志。

本轮仅完成固定上游提交静态Xacro/C++/测试代码审查；未执行Xacro展开、ROS 2构建/单测、ResourceManager加载、mock GPIO缺失字段注入、输出命令捕获、停用/重新激活/重连测试、VAL3/CS9、SIL/HIL、FAT/SAT或实机验证。未修改上游、未应用PR。工程级验收仍未通过，`TODO-EXT-001`未授权合并。
