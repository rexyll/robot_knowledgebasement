# Stäubli ROS 2—诊断数据通道、控制器状态反馈与安全状态语义审计

- 审计节点：§9.3.269 / SERVO-852
- 日期：2026-11-10
- 固定上游：`ICube-Robotics/staubli_driver_ros2@bd658e2d266e315d2ee35f985fb352ea88306b79`
- 审查方式：固定提交静态源码、VAL3工程文件、文档和现有测试代码审查；未执行动态测试。
- 范围：RobotDriver诊断连接/读取、RealTimeSocketSubscriber、DiagnosticDataMessage序列化、StaubliHardwareInterface状态导出与更新、VAL3 updateState/encodeRobotStateMsg/controlTask、diagnostics示例文档和RobotDriver/message serialization单元测试。

## 1. 主要结论

### 1.1 诊断socket“ready”不等于收到有效诊断帧

1. `RobotDriver::connect()`建立诊断UDP socket并创建`RealTimeSocketSubscriber<DiagnosticDataMessage>`；随后`is_ready()`只检查socket本地connected和接收线程running，不检查诊断帧是否已到达。
2. connect等待循环确实声明了`diagnostic_data_msg`，但`diag_interface_ready`被直接赋值为true；实际`read_diagnostic_data(diagnostic_data_msg)`调用被TODO注释。
3. 因此诊断数据缺失、诊断帧未到达或诊断内容陈旧都不会阻止connect成功。连接日志中的“diagnostic interface ready”不能解释为诊断数据有效。
4. connect随后打印`current_diagnostic_data_.robot_firmware_version`，但没有先填充该对象；其构造默认值为0.0.0。固定代码路径因此可能输出默认固件版本，而非控制器实测版本。控制器类型兼容性检查也被注释，VAL3版本兼容检查仍为TODO。
5. `read_diagnostic_data()`实现了message type和staleness检查，但connect没有调用它；本轮未发现StaubliHardwareInterface周期性调用该函数或将诊断数据发布到ROS diagnostics topic的路径。

### 1.2 固定VAL3工程未发现诊断帧生产端

1. 固定提交VAL3工程中，controlTask每周期调用`encodeRobotStateMsg`并通过control socket发送RobotState；未发现DiagnosticData序列化/发送任务、诊断socket周期发送调用或DiagnosticData数据库类型/程序文件。
2. C++单元测试fixture会通过mock diagnostics socket每4ms构造并发送DiagnosticData，以满足测试连接场景；这是测试桩行为，不证明固定VAL3工程能生产诊断数据。
3. `sphinx/demo_applications/diagnostics.rst`仅写有“Coming soon :)”。文档未提供真实诊断数据订阅、错误日志读取或控制器健康状态示例。
4. 因此固定提交的C++诊断协议模型、socket subscriber和mock测试不能证明CS9上存在可工作的诊断数据端到端链路。

### 1.3 DiagnosticData反序列化对报文头的检查顺序错误

1. `DiagnosticDataMessage::deserialize()`先检查当前对象的`header.payload_size`和`header.message_type`，随后才调用`header.deserialize(buffer,...)`读取网络报文头。
2. subscriber为每个UDP数据报新建默认构造的DiagnosticDataMessage；其默认header已经被构造函数设为本地预期的DIAGNOSTIC_DATA类型和固定payload长度。因此前置检查验证的是对象默认值，不是输入报文中的message_type/payload_size。
3. `FrameHeader::deserialize()`只检查magic number，不检查protocol_version、message_type或payload_size。DiagnosticData反序列化在读入报文头后没有重新验证这些字段。
4. 结果是诊断报文的类型/长度检查不能按当前实现证明对wire header生效；protocol_version也没有统一验证。该结论来自静态调用顺序，尚未通过畸形帧测试复现。
5. 这与既有SERVO-798协议帧审计中发现的统一header校验缺口相互印证；本节点进一步确认诊断数据通道本身未被connect实际消费。

### 1.4 RobotState中的安全状态字段存在语义压缩

1. VAL3 `updateState()`读取`esStatus()`到`nSafetyStatus`，注释列出0无安全停止、1等待安全重启、2 SS1、3 SS2、4等待WMS重启；随后设置`bEStopped = (nSafetyStatus != 0)`。
2. C++将该布尔位解码为`estop_pressed`，HardwareInterface又将其导出为supervision的`estop_pressed`状态接口。这样会把SS1、SS2及等待重启等不同安全状态全部表达成“急停已按下”，语义过宽，不能作为急停按钮实际状态的独立证据。
3. `bBrakeReleased`被直接赋值为`bDrivePowered`，没有独立制动器反馈采集；导出的`brakes_released`因此只是软件推断，不是制动释放传感器/控制器状态的独立反馈。
4. `bMotionPossible`只按驱动上电且`!bEStopped`计算；源码中考虑`nRobotStatus == 0`的条件被注释。该布尔值没有完整表达手动/自动模式、Hold或其他运动许可条件。
5. 普通RobotState字段不能替代控制器认证安全状态、硬接线安全回路或安全PLC反馈。不得把ROS的`estop_pressed`、`brakes_released`或`motion_possible`接口作为安全功能证明。

### 1.5 错误标志可能未形成稳定的ROS可观测故障记录

1. VAL3 controlTask将`l_bError`写入RobotState的`bInError`，并编码到状态标志；但错误处理路径随后执行运动停止/复位，并将`l_bError=false`后继续通信复位。
2. 对于在本周期状态帧发送之后才发生的接收/命令/执行错误，错误标志可能在下一次状态发送前已被清除；控制器日志与ROS周期状态字段不是等价的持久故障记录。
3. C++状态消息仅暴露一个`error_state`布尔量；诊断协议虽定义10条错误码/时间戳和`control_task_status`字段，但当前连接流程不读取诊断帧，HardwareInterface也未消费这些字段。
4. 不能依赖瞬时`in_error`接口作为完整故障历史或FRACAS数据源。

### 1.6 GPIO有效性缺失会使状态接口保留旧值

1. VAL3 `updateState()`固定将`bValidDigitalInputs`和`bValidAnalogInputs`设为false；`encodeRobotStateMsg`只有在有效标志为true时才置对应valid-field bit，数字输入位图写入仍为TODO。
2. C++ `StaubliHardwareInterface::update_state()`仅在输入valid flag为true时更新数字/模拟输入缓存；flag为false时不清零、不标记无效，也没有向ROS导出对应validity接口，随后仍可能返回true。
3. 因而一旦输入缓存曾经有值，后续帧报告无效时，ROS state interface可能继续暴露上一份值而没有年龄/有效性提示。固定VAL3当前持续报false意味着当前端到端GPIO输入并未得到证明；此处的“旧值保留”是接口更新策略的静态风险。
4. joint positions/velocities缺失会令update_state返回false；torque缺失则设零值。不同状态字段的无效处理策略不一致。

## 2. SERVO-852验收矩阵

| ID | 验收项 | 状态 |
|---|---|---|
| DS1 | 诊断socket连接及subscriber创建 | 固定提交静态审查完成 |
| DS2 | 诊断subscriber readiness语义 | 静态确认只代表socket/接收线程就绪 |
| DS3 | connect阶段真实诊断帧读取 | 静态确认调用仍为TODO，diag ready被硬编码true |
| DS4 | 固件版本/控制器型号兼容性检查 | 静态确认读取默认值路径、型号检查注释、VAL3兼容性TODO |
| DS5 | VAL3诊断帧生产与发送 | 固定工程树静态审查未发现实现；未进行控制器部署核验 |
| DS6 | DiagnosticData header type/length/version验证 | 静态确认校验时序错误，FrameHeader只校验magic |
| DS7 | RobotState安全状态字段语义 | 静态确认E-stop/SS1/SS2等待态被压缩为一个布尔值 |
| DS8 | 制动释放/运动许可反馈语义 | 静态确认brakes_released由drivePowered推导，motion_possible条件不完整 |
| DS9 | 错误标志持久性与诊断数据消费 | 静态确认错误标志复位路径及诊断数据未接入HardwareInterface |
| DS10 | GPIO invalid flag到ROS状态接口 | 静态确认无效输入保留旧缓存且无validity state interface |
| DS11 | 现有单元测试覆盖 | 静态确认mock诊断数据被发送，但connect未验证读取内容 |
| DS12 | 畸形诊断帧/版本/字段错误注入 | 未执行 |
| DS13 | CS9真实诊断数据与安全状态对照 | 未执行/缺现场证据 |
| DS14 | ROS diagnostics发布、报警与FRACAS端到端验证 | 未执行/当前未发现完整实现 |
| DS15 | SIL/HIL、FAT/SAT及实机安全验收 | 缺少证据，未执行 |

## 3. 整改建议

1. connect阶段必须等待真实诊断帧；对诊断帧类型、长度、magic、protocol version、序号和时间新鲜度进行统一校验。诊断数据缺失或无效时不得将diagnostics_ready置true。
2. 仅在有效诊断帧到达后打印固件版本和控制器型号；对支持的CS系列、固件、VAL3版本建立可追溯兼容矩阵。禁止以默认0.0.0代替未知值。
3. 在VAL3工程实现独立诊断采集与发送任务：错误码/时间戳、controlTask运行状态、任务周期/overrun计数、通信状态、控制器型号和固件版本；明确缓冲、刷新周期、丢包策略和错误历史保持策略。
4. 修正DiagnosticData反序列化顺序：先解析wire header，再统一验证magic、protocol_version、message_type、payload_size与实际datagram长度；所有消息类型复用同一header validator。补充wrong-type/wrong-size/wrong-version/truncated/trailing-byte畸形帧测试。
5. 将原始安全状态枚举与操作模式独立发布；“急停按钮按下”“安全停止类型”“等待复位”“运动许可”必须分离建模。若控制器不能提供真实按钮状态，不应将通用SafetyStatus映射成estop_pressed。
6. 只有取得明确制动反馈信号时才发布brakes_released；否则字段命名/文档必须标明它是基于drive power的推断值，不能当作物理反馈。
7. 定义持久故障ID/事件序号、首次/最近发生时间、确认/清除状态和错误历史；将瞬时控制错误与诊断日志分离，确保故障清除前已被可靠采集。
8. 为每个GPIO state interface同时提供validity与sample age；invalid时明确输出NaN/invalid flag或受控默认策略，不得静默保留旧值并表现为当前反馈。
9. 将诊断数据接入ROS diagnostics发布链和工程日志；验证断线、陈旧数据、错误码突发、任务overrun、控制器重启和安全状态转换的报警/恢复行为。
10. 对所有安全相关状态进行CS9控制器变量/官方手册映射、现场指示灯/安全回路独立对照和专业安全验证；普通UDP诊断及ROS状态接口不构成安全功能。

## 4. 验证边界与结论

本轮仅审查固定提交源码、VAL3工程文件、文档和现有测试源码。未运行ROS 2构建/单测、畸形帧注入、诊断UDP抓包、VAL3编译/下载、CS9仿真、控制器状态对照、ROS diagnostics发布验证、SIL/HIL、FAT/SAT或实机验证。诊断帧生产端未在固定VAL3工程树中发现属于静态审查结论，不等同于对目标控制器已部署文件的现场核验。DiagnosticData header校验时序缺陷及GPIO invalid旧值风险尚未通过动态测试复现。

未修改上游仓库，未应用PR。Stäubli工程级验收仍未通过；`TODO-EXT-001`未授权合并。根00-01与第21章21-02继续进行中。

**下一节点：§9.3.270 / SERVO-853。**
