# Stäubli ROS 2—协议字段映射、枚举语义、单位与边界值一致性审计

- 审计节点：§9.3.270 / SERVO-853
- 日期：2026-11-10
- 固定上游：`ICube-Robotics/staubli_driver_ros2@bd658e2d266e315d2ee35f985fb352ea88306b79`
- 审查方式：固定提交静态源码、VAL3数据库/程序、机器人模型配置及现有单元测试代码审查；未执行动态测试。
- 范围：C++协议消息/序列化/枚举、VAL3 MessageHeader/RobotState/RobotCommand、encodeHeader/decodeHeader、状态/命令编码解码、HardwareInterface单位转换、关节限制配置、GPIO数量配置及现有序列化测试。

## 1. 主要结论

### 1.1 VAL3 RobotState帧头payload_size被序号覆盖

1. `initRobotStateMsg.pgx`将RobotState的payload size初始化为124字节（总帧132字节）。
2. `encodeHeader.pgx`写入8字节帧头时，偏移4处写入`nMsgSequenceNumber`，偏移6处本应写入`nPayloadSize`，实际再次写入`nMsgSequenceNumber`。
3. 因此VAL3发出的RobotState帧头payload_size字段不是124，而是当前sequence number。该错误每次调用encodeHeader都会发生。
4. C++ `RobotStateMessage::deserialize()`解析header后留有空白的“Validate header fields”区段，不检查message_type、payload_size或protocol_version；固定132字节数据仍会继续按偏移解码。这可能掩盖VAL3帧头错误，而不是证明帧头正确。
5. C++通用FrameHeader解析仅检查magic number；RobotState固定帧长依赖本地类定义，不依赖wire payload_size。尚未做UDP抓包验证该错误对当前部署数据流的具体表现。

### 1.2 OperationMode枚举在VAL3与C++之间错位

VAL3 `updateState.pgx`读取`workingMode()`并原样写入RobotState的operation_mode字节；C++ `OperationMode`枚举却使用不同语义：

| 数值 | VAL3 workingMode语义 | C++ OperationMode语义 | 风险 |
|---:|---|---|---|
| 0 | 无效/安全转换 | UNKNOWN | 一致 |
| 1 | MANUAL | MANUAL | 一致 |
| 2 | TEST | AUTOMATIC | 测试模式被误读为自动 |
| 3 | AUTOMATIC-LOCAL | REMOTE | 自动本地被误读为远程 |
| 4 | AUTOMATIC-REMOTE | 未定义枚举值 | 未知值进入ROS状态接口 |

C++ `RobotStateMessage::deserialize()`直接static_cast为OperationMode，没有拒绝非法枚举值；HardwareInterface再将数值导出为supervision.operation_mode。因此控制器工作模式显示可能错误，且4会成为未定义的枚举数值。需要建立统一协议枚举映射表，不能直接透传VAL3原始数值。

### 1.3 控制模式、安全状态和状态标志映射部分一致

1. VAL3 nControlMode与C++ CommandType的STOP=1、JOINT_POSITION=2、JOINT_VELOCITY=3数值一致；JOINT_TORQUE=4虽在C++枚举中存在，但本固定VAL3工程未见对应执行路径。
2. VAL3 SafetyStatus 0–4与C++ SafetyStatus 0–4数值/名称对应。
3. VAL3状态flags bit0–bit5与C++ StatusFlag POWER_ON、BRAKES_RELEASED、MOTION_POSSIBLE、IN_MOTION、ERROR_STATE、ESTOP_PRESSED一致。
4. VAL3 valid-field flags bit0–bit5与C++ ValidFieldFlag的位置/速度/扭矩/F-T/数字输入/模拟输入一致。
5. C++对control_state、safety_status和operation_mode均直接static_cast，未统一验证枚举值范围；未知/未来版本枚举值可能静默进入上层状态。
6. `operation_mode_status`是模式相关的原始byte，VAL3注释只对自动模式定义0 programmed move、1 connection move、2 Hold；C++以同一字段直接导出，没有附带其适用模式或枚举版本。

### 1.4 关节位置/速度单位转换路径有明确的度/弧度换算

1. C++ HardwareInterface的write路径将ROS关节位置和速度从rad/rad·s⁻¹乘以180/π后发送；代码注释明确Staubli使用degree。
2. update_state路径将收到的关节位置和速度乘以π/180转换回ROS rad/rad·s⁻¹。
3. VAL3位置控制将收到的6个float直接赋给jointRx，再用`isInRange()`做位置范围检查；这一链路与C++显式度制转换方向一致。
4. 本轮未发现独立的角加速度命令编码/VAL3消费路径；HardwareInterface中存在acceleration command storage，但控制协议仅含6个command_reference，没有独立加速度字段。
5. 现有源码支持位置/速度角度单位的静态映射判断，但仍需在CS9控制器和实际TX2型号上用已知角度点位验证正负方向、零位、各轴限位与速度单位。

### 1.5 浮点数在线路上统一压缩为IEEE float32，但精度/范围契约不完整

1. C++消息对象使用double数组；`serialization.hpp`明确将double转换为float序列化，反序列化时从float转换回double。
2. VAL3使用`toBinary/fromBinary(...,"4.0l")`，即little-endian单精度float32。固定RobotState 132字节、RobotCommand 55字节的帧长与该布局一致。
3. C++ primitive测试验证double按float大小写入，但仅使用普通有限值；没有覆盖float32最大/最小值、溢出、NaN、正负Inf、次正规数、精度误差和拒绝策略。
4. HardwareInterface关节命令只检查`std::isnan`，没有拒绝正负Inf；模拟输出命令未见finite检查或量程裁剪。double转换float可能产生Inf或丢失精度。
5. 协议没有声明所有浮点字段的有效数值范围、非有限值处理、舍入误差预算或单位量程契约。

### 1.6 F/T、GPIO字段虽占用固定帧空间，但VAL3写入不完整

1. RobotState协议固定含6个F/T float、16-bit digital input mask和4个analog input float；C++序列化/反序列化都按固定布局读写。
2. VAL3 `updateState()`将F/T有效标志设为false、值初始化为0；`encodeRobotStateMsg()`只写前三个F/T float，后三个只推进offset而不写数据。由于valid flag为false，C++当前应忽略F/T数据，但固定帧仍可能携带旧缓冲区字节，未明确逐帧清零。
3. VAL3 digital input mask转换和写入被注释；analog inputs四个值的写入仍为TODO，valid flags也持续为false。
4. RobotCommand中C++包含16位digital output mask和4路analog outputs；VAL3 decode解析mask到局部变量，但mask转换到`nDigitalOutputs`数组的代码被注释；4路analog outputs则被解析到VAL3数据库。
5. TX2-60L与TX2-60L MED的robot_model.yaml均声明16 DI、16 DO、2 AI、2 AO，而通信帧固定预留16 DI、16 DO、4 AI、4 AO；HardwareInterface允许最多4路模拟IO。协议容量、软件配置数量和实际柜内硬件选件必须区分，不能由帧容量推断物理通道可用。
6. 模拟IO未见电压/电流制式、量程、工程单位、分辨率或逐通道映射；不能把无单位float当作可安全使用的工程值。

### 1.7 命令范围和边界值检查不完整

1. VAL3位置控制有`isInRange()`关节位置限位，但“目标与当前值是否足够接近”的检查仍为TODO。
2. VAL3速度控制的安全限值检查为TODO，`$setVelCmd`执行也被注释；程序直接记录not yet implemented并报错。
3. C++ CommandType包含JOINT_TORQUE，但本固定VAL3控制任务未见扭矩命令执行。
4. C++ HardwareInterface只检查关节命令NaN，未检查Infinity；模拟输出不检查NaN/Inf、物理量程或斜率。VAL3 command decoder把任意float读入后主要检查消息长度/类型，未做数值finite与单位范围校验。
5. controller_period在线路上为float32毫秒；VAL3解码到nRemoteCtrlPeriod，但固定控制任务尚未证明该字段参与命令过期/刷新监督（SERVO-835已有此缺口）。
6. ROS joint limits YAML使用`!degrees`声明位置/速度/加速度限值，但VAL3执行端仅有位置`isInRange()`，速度限值与加速度接口没有形成完整控制器侧约束闭环。

## 2. SERVO-853验收矩阵

| ID | 验收项 | 状态 |
|---|---|---|
| FM1 | RobotState/RobotCommand固定帧长与float32布局 | 固定源码静态核对完成 |
| FM2 | VAL3 RobotState header payload_size写入 | 静态确认序号被重复写入payload_size字段 |
| FM3 | C++ RobotState header验证 | 静态确认解析后未验证type/size/version |
| FM4 | OperationMode跨语言映射 | 静态确认数值2/3/4语义错位 |
| FM5 | CommandType/SafetyStatus/flags映射 | 固定源码静态核对完成，非法枚举边界未验证 |
| FM6 | ROS弧度与VAL3角度换算 | 静态确认HardwareInterface显式rad↔deg转换 |
| FM7 | float32精度、溢出与非有限值 | 静态确认double转float；边界注入未执行 |
| FM8 | F/T六轴字段写入完整性 | 静态确认后三轴未写入且valid=false |
| FM9 | GPIO输入/输出字段映射 | 静态确认数字mask转换TODO、模拟输入编码TODO |
| FM10 | 模拟IO数量/单位/量程配置 | 配置静态核对完成；物理制式/端子映射缺失 |
| FM11 | 位置/速度/扭矩命令范围 | 位置限位存在；目标跳变TODO、速度限值/执行TODO、扭矩路径未证实 |
| FM12 | 现有跨语言测试 | 仅C++自身序列化往返测试；无VAL3 wire互操作测试 |
| FM13 | CS9现场数值点位、限位与单位对照 | 未执行 |
| FM14 | 畸形header、非法枚举、NaN/Inf、float边界注入 | 未执行 |
| FM15 | SIL/HIL、FAT/SAT与实机验证 | 未执行/缺证据 |

## 3. 整改建议

1. 修正VAL3 `encodeHeader()`末字段，将payload_size正确编码为`nPayloadSize`；增加header黄金测试，明确验证sequence_number和payload_size各自独立。
2. 建立协议版本化的跨语言字段表，列明字段偏移、宽度、符号、端序、单位、枚举数值、有效标志、边界值、保留值与未知值策略。
3. 统一OperationMode映射：VAL3 TEST、AUTOMATIC_LOCAL、AUTOMATIC_REMOTE分别映射到独立的协议枚举；若ROS层没有对应概念，应显式映射为UNSUPPORTED/UNKNOWN并保留原始VAL3 mode，而非错位解释。
4. C++ RobotState反序列化必须在消费payload前验证magic、protocol version、message type、payload_size、实际datagram精确长度及所有枚举合法性；RobotCommand/DiagnosticData也复用统一validator。
5. 为所有浮点字段定义float32量化误差和工程量程；序列化前拒绝NaN/Inf及越界值，明确double→float溢出策略，模拟输出必须按硬件制式/量程做安全校验。
6. F/T字段应写满6个float或在无效时逐帧明确清零；未实现的传感器必须保持valid=false并在接口层标注不可用，禁止残留缓冲数据伪装成读数。
7. 完成VAL3数字输入/输出mask转换、模拟输入/输出编码和通道配置映射；统一协议四路容量与机型两路配置的策略，并按控制柜硬件选件生成映射表。
8. 明确OperationModeStatus只在对应mode下解释；ROS diagnostics保留raw mode/status与映射状态，避免信息丢失。
9. 在CS9隔离环境执行0/±角度、轴限位内外、速度边界、Float32极值、NaN/Inf、无效枚举、payload长度、sequence边界和IO逐通道测试。
10. 速度/扭矩/加速度接口在控制器侧真正实现并经过限值/安全验证前，不应对外宣称具备相应控制能力。

## 4. 验证边界与结论

本轮只审查固定提交源码、VAL3数据库/程序、模型配置与现有测试源码。未执行C++构建/单测、VAL3 Studio编译/导入/下载、控制器UDP抓包、畸形帧/枚举/float边界注入、CS9限位/速度/单位实测、GPIO端子测试、SIL/HIL、FAT/SAT或实机验证。帧头payload_size重复序号、OperationMode错位及F/T/IO未完整写入均为静态代码证据，尚未在真实控制器数据流复现。

未修改上游仓库，未应用PR。Stäubli工程级验收仍未通过；`TODO-EXT-001`未授权合并。根00-01与第21章21-02继续进行中。

**下一节点：§9.3.271 / SERVO-854。**
