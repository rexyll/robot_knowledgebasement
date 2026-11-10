# Stäubli GPIO协议端到端映射、有效性标志与VAL3执行链审计

- 审计节点：§9.3.265 / SERVO-848
- 日期：2026-11-10
- 被审查上游：`ICube-Robotics/staubli_driver_ros2`
- 固定上游提交：`bd658e2d266e315d2ee35f985fb352ea88306b79`
- 本仓库分支：`main`
- 审计性质：固定提交源码、协议结构、VAL3数据库及现有测试代码静态审查
- 本轮未修改上游；未应用PR；未将源码推断表述为动态或现场测试结论

## 1. 审计范围与证据文件

本轮追踪ROS 2 C++消息结构与序列化、VAL3状态采集/状态编码、命令解码、VAL3数据库数组以及控制任务GPIO执行位置。

主要文件（均固定在上述上游提交）：

- [messages.hpp](https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/include/staubli_robot_driver/communication/messages.hpp)
- [messages.cpp](https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/src/communication/messages.cpp)
- [serialization.hpp](https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/include/staubli_robot_driver/communication/serialization.hpp)
- [protocol.hpp](https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/include/staubli_robot_driver/communication/protocol.hpp)
- [VAL3 updateState.pgx](https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/val3/userapp/ros2_server/updateState.pgx)
- [VAL3 encodeRobotStateMsg.pgx](https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/val3/userapp/ros2_server/Serialization/encodeRobotStateMsg.pgx)
- [VAL3 decodeRobotCommandMsg.pgx](https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/val3/userapp/ros2_server/Serialization/decodeRobotCommandMsg.pgx)
- [VAL3 controlTask.pgx](https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/val3/userapp/ros2_server/controlTask.pgx)
- [RobotState.dtx](https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/val3/userapp/ros2_server/Types/RobotState/RobotState.dtx)
- [RobotCommand.dtx](https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/val3/userapp/ros2_server/Types/RobotCommand/RobotCommand.dtx)
- [test_message_serialization.cpp](https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/test/unit_tests/communication/test_message_serialization.cpp)

## 2. 协议静态结构

### 2.1 固定帧长度和字段

C++消息定义：

- RobotState：132 bytes（8-byte header + 124-byte payload）。
- RobotCommand：55 bytes（8-byte header + 47-byte payload）。
- FrameHeader：8 bytes，字段为magic(2)、protocol version(1)、message type(1)、sequence(2)、payload size(2)。
- 数字GPIO以16-bit位图传输；模拟GPIO固定4个float32值。
- C++序列化层将double转换为float32后写入4字节；编译时要求little-endian。VAL3编码/解码代码也使用`2l`和`4.0l`格式，静态意图为little-endian。

RobotState payload中的GPIO布局：
- 有效字段标志位：digital inputs为bit 4（值16），analog inputs为bit 5（值32）。
- 数字输入位图：16 bits，通道0对应bit 0，通道15对应bit 15。
- 模拟输入：4个float32，顺序为通道0至3（文档使用A_in_1至A_in_4命名）。

RobotCommand payload中的GPIO布局：
- 数字输出位图：16 bits，通道0对应bit 0，通道15对应bit 15。
- 模拟输出：4个float32，顺序为通道0至3。
- C++命令消息长度固定55 bytes；VAL3初始化命令消息时payload size固定47 bytes，与C++声明相符。

### 2.2 不能将固定帧空间理解为GPIO功能已实现

C++消息类总是按固定长度读写GPIO字段，valid flag用于说明状态字段是否有效。即使valid flag为false，反序列化仍然会解析数字位图和4个模拟值；上层硬件接口是否消费这些数值取决于valid flag。命令消息没有对应的GPIO有效性标志，C++会把当前输出命令数组编码进固定payload。

## 3. 状态方向：ROS 2 ← VAL3

### 3.1 输入有效性标志被VAL3每周期明确置为false

`updateState.pgx`在每次状态更新时执行：

- `bValidDigitalInputs = false`
- `bValidAnalogInputs = false`

固定提交中没有后续将这两个标志设为true的GPIO采集逻辑。VAL3 RobotState数据库虽然定义了16路`nDigitalInputs`和4路`nAnalogInputs`，但本轮检索到的状态更新程序没有从控制器/IO模块读取这些数组，也没有填充输入值。

因此，当前固定源码呈现的是“GPIO输入无效”，不是“协议允许偶尔省略GPIO字段”。报文仍固定包含相应字段位置，但有效标志明确关闭。

### 3.2 状态编码器没有写入GPIO payload

`encodeRobotStateMsg.pgx`：

- 生成valid-field flags时按`bValidDigitalInputs`和`bValidAnalogInputs`设置bit 4/5。
- `l_nDigitalInputFlags`被初始化为0，但后面只有`TODO: implement when needed`，没有从`nDigitalInputs`构造位图。
- 数字输入位图的`toBinary`调用被注释，仅将offset前移2 bytes。
- 四个模拟输入的`toBinary`调用均为TODO/注释，仅逐项前移4 bytes。
- 该函数在offset到达固定帧尾后仍可报告编码成功。

因此当前VAL3状态编码路径没有实际序列化GPIO输入数据。由于buffer是消息对象中复用的数组，保留字段没有被本函数写入；不应假设这些字节每次都会被清零。valid flags当前为false，C++硬件接口按设计不会把这些无效值更新到GPIO输入缓存，但原始消息字段仍会被反序列化。

### 3.3 C++消费行为与SERVO-847发现的关系

C++ `RobotStateMessage::deserialize`会无条件读取16-bit数字输入位图和4个模拟值，并独立解析valid flags。硬件接口的状态更新逻辑只有在`has_digital_inputs`或`has_analog_inputs`为true时才更新对应GPIO输入缓存。

结合VAL3状态端实现，当前静态路径为：
1. VAL3每周期把两个GPIO有效标志设为false；
2. 状态编码器发送valid flags关闭的固定长度帧，GPIO payload槽位未被填充；
3. C++解码后`has_*_inputs=false`；
4. hardware interface跳过GPIO输入缓存更新，ROS GPIO state interface不会获得来自此VAL3实现的新鲜输入值。

这比“在某些报文缺字段时可能保留旧值”更具体：固定上游当前没有实现有效GPIO输入采集/编码链路。SERVO-847中的旧值保留风险仍成立，但本轮静态证据显示固定VAL3实现会持续将GPIO输入标为无效；是否会出现曾经有效后再失效的现场序列，仍需运行时/固件证据。

## 4. 命令方向：ROS 2 → VAL3

### 4.1 C++输出编码

C++ `RobotCommandMessage::serialize`：
- 将16路数字输出按通道索引打包到uint16位图，bit i对应digital_outputs[i]。
- 将4路模拟输出按数组顺序写入float32。
- C++构造函数默认将数字输出设false、模拟输出设0。
- 硬件接口从ros2_control command interface读取数字输出阈值化（>0.5为true），模拟输出直接复制到4元素数组上限内。

这是ROS侧到UDP payload的静态编码路径；不证明控制器已经执行输出。

### 4.2 VAL3解码只完成部分数据搬运

`decodeRobotCommandMsg.pgx`：
- 从payload读取数字输出16-bit mask到局部变量`l_nDigitalOutputCmdMask`。
- 数字位图到`RobotCommand.nDigitalOutputs[0..15]`的转换代码整段被注释。
- 四个模拟输出值被解码到`RobotCommand.nAnalogOutputs[0..3]`。
- RobotCommand数据库确实声明16路数字输出数组与4路模拟输出数组，但初始化程序未在本轮固定源码中建立数字位图到数组的赋值逻辑。

所以数字输出位图虽然抵达VAL3解码局部变量，但没有形成有效的VAL3数字输出数组更新；模拟输出值进入数据库数组，但还需后续物理执行链路。

### 4.3 controlTask没有执行GPIO物理输出

`controlTask.pgx`在“Execute GPIO commands”区块明确保留：
- `TODO: write digital outputs based on command`
- `TODO: write analog outputs based on command`

本轮固定提交中未发现该控制任务将解码后的数字/模拟输出数组写入VAL3 IO API或已配置物理通道的实现。由此可以确认：即使ROS侧C++成功序列化并通过UDP发送命令，当前仓库内VAL3服务端仍没有完成GPIO物理输出执行。

这是软件功能实现缺口，不是仅靠调整ROS接口名称、消息长度或缓存生命周期即可解决的问题。不能将UDP send成功、VAL3 decode成功或RobotCommand有效标志置true解释为IO已输出。

## 5. 现有测试覆盖与证据边界

`test_message_serialization.cpp`包含RobotState和RobotCommand的C++序列化/反序列化往返测试，覆盖了：
- C++状态消息valid flags的往返；
- C++数字输入位图往返；
- C++数字输出位图和模拟输出数组往返；
- 基本消息字段的C++编码/解码一致性。

但该测试没有运行VAL3代码，也没有把C++生成的golden frame交给VAL3解码，更没有把VAL3生成的状态帧交给C++解码。它不能发现VAL3中数字mask转换被注释、状态GPIO payload未写入、GPIO valid flags始终false或controlTask没有物理输出执行等跨语言问题。本轮仅审阅测试源代码，没有执行测试二进制。

## 6. 主要风险与整改建议

1. **输入链路缺失：** 明确目标CS9/VAL3版本中实际IO采集API、模块配置、通道编号与读取时序；实现输入数组采集、有效标志置位、位图/模拟数据序列化。若某型号不支持某类IO，应在型号配置中明确禁用并让ROS接口生成阶段拒绝暴露，而不是仅把valid flag永久置false。
2. **输出数字位图未映射：** 实现bit 0..15到VAL3数组索引0..15的转换，定义bit序、通道编号、输出默认态和写入失败处理。
3. **输出模拟值未执行：** 明确4通道的物理量、单位、工程范围、量化/缩放、硬件模块和VAL3 API；实现输出写入和错误传播。
4. **输出执行策略不完整：** 定义STOP、ERROR、deactivate、cleanup、通信丢失、重连、控制器重启时数字/模拟输出的安全默认态、保持或复位策略。不得由未验证的缓存重放决定物理输出。
5. **跨语言黄金帧：** 建立固定字节级golden vectors，分别覆盖digital bit 0、bit 15、交替位、全0、全1；analog channel 0/3及正负/边界值；验证C++→VAL3和VAL3→C++双向完全一致。
6. **valid flag与payload一致性：** 当valid flag为false时，建议payload槽位确定性写零；当flag为true时，必须验证采集数据有效、有限且通道映射已配置。加入false→true→false序列测试，验证上层缓存/有效性暴露策略。
7. **端到端验收：** 先在隔离mock/仿真环境捕获UDP帧和VAL3 IO API调用，再到CS9受控测试台逐点核对模块、端子、接线图和通道清单。普通GPIO不得承担急停、SS1/SS2或任何安全功能。

## 7. SERVO-848验收矩阵

| ID | 验收项 | 状态 |
|---|---|---|
| GP1 | 固定帧长：RobotState 132 B / RobotCommand 55 B | 固定提交静态确认 |
| GP2 | C++与VAL3对GPIO位图/模拟数组字段顺序 | 静态代码意图一致；未运行跨语言黄金帧 |
| GP3 | 数字IO bit 0..15映射规则 | C++ bit i静态确认；VAL3解码转换被注释，未实现 |
| GP4 | VAL3数字输入采集与valid flag | 静态确认每周期valid flag设false；采集未实现 |
| GP5 | VAL3模拟输入采集与valid flag | 静态确认每周期valid flag设false；采集未实现 |
| GP6 | VAL3状态编码器数字输入payload | 静态确认位图序列化被注释/未实现 |
| GP7 | VAL3状态编码器模拟输入payload | 静态确认4个模拟值序列化均为TODO/注释 |
| GP8 | ROS 2侧GPIO输入缓存更新 | 静态确认仅消费valid=true字段；结合VAL3路径无法获得有效输入 |
| GP9 | VAL3数字输出位图到数组映射 | 静态确认转换代码被注释，未实现 |
| GP10 | VAL3模拟输出数组解码 | 静态确认payload解析到4元素数组；未执行运行时测试 |
| GP11 | VAL3数字/模拟物理输出写入 | controlTask中两项均为TODO，未实现于固定提交 |
| GP12 | C++消息序列化单测 | 测试源含C++往返断言；本轮未执行测试 |
| GP13 | C++↔VAL3跨语言黄金帧 | 未执行；未发现覆盖该边界的现有测试 |
| GP14 | CS9模块、VAL3变量、ROS接口和现场端子逐点映射 | 缺配置/接线/现场签核证据，未执行 |
| GP15 | STOP/ERROR/断线/重连GPIO输出安全策略 | 设计与实机证据不足，未验收 |

## 8. 验收结论

**GPIO端到端功能当前不能判定为已实现或已验收。** 固定上游的C++协议类具备16路数字与4路模拟GPIO字段的序列化/反序列化能力，但VAL3状态输入采集与编码未实现，命令数字位图解码未映射到数据库数组，控制任务中的数字/模拟物理输出写入仍为TODO。现有C++ round-trip单测不足以证明跨语言或实机功能。

本轮完成的是固定上游静态源码与测试代码审查；未运行ROS 2构建/单测、VAL3编译/下载、CS9仿真、UDP抓包/注入、mock IO、SIL/HIL、FAT/SAT或实机端子逐点测试。所有动态、控制器版本、物理IO模块和现场证据仍保持未完成。Stäubli工程级验收未通过，`TODO-EXT-001`未授权合并。
