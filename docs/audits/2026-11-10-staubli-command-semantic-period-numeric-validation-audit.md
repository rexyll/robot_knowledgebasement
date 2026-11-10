# Stäubli ROS 2—VAL3命令语义、控制周期与数值边界校验审计

- 审计节点：§9.3.272 / SERVO-855
- 日期：2026-11-10
- 固定上游：`ICube-Robotics/staubli_driver_ros2@bd658e2d266e315d2ee35f985fb352ea88306b79`
- 审查方式：固定提交静态源码与现有测试代码审查；未执行动态测试。
- 范围：VAL3 `decodeRobotCommandMsg`、`controlTask`、`updateJointPositionControl`、`updateJointVelocityControl`、RobotCommand数据库；C++ `CommandType`、`RobotCommandMessage`、`StaubliHardwareInterface::write`及消息序列化测试。

## 1. 主要结论

### 1.1 controller_period被解码，但没有形成控制周期校验/执行闭环

1. C++ `StaubliHardwareInterface::write`将ROS控制周期通过`1e3 * period.seconds()`转换为毫秒后写入`RobotCommandMessage::controller_period`；头文件也将该字段注释为毫秒。
2. VAL3 `decodeRobotCommandMsg`将payload首个4字节解码到`robotCommand.nRemoteCtrlPeriod`，RobotCommand数据库保留该字段。
3. 在固定VAL3工程的`controlTask`、位置控制和速度控制调用链中，未发现对`nRemoteCtrlPeriod`的范围/有限性检查，也未发现将该字段用于调度、超时、运动参数或控制器周期一致性校验的消费路径。
4. 因此该字段当前是被传输和存储的元数据，不能证明CS9控制循环与ROS控制周期一致，也不能据此推断控制器会按远端周期调整执行。
5. 现有C++序列化测试设置`controller_period = 0.008`，注释却写`8 ms`。按照生产发送路径的毫秒转换，8 ms应编码为8.0，而0.008表示0.008 ms；测试仅验证往返一致，未验证单位语义。

### 1.2 VAL3命令类型检查范围与真实执行分支不一致

1. C++ `CommandType`枚举为INVALID=0、STOP=1、JOINT_POSITION=2、JOINT_VELOCITY=3、JOINT_TORQUE=4，另有VAL3内部DECELERATION类型0x0A/0x0B。
2. VAL3 `controlTask`只检查`nMotionCmdType < 0 or > 4`。因此0和4均通过该范围检查：0随后因`l_nCmdMode <= 1`进入STOP/idle路径；4则未匹配位置/速度分支，进入Unknown command mode错误路径。
3. 位置控制函数明确要求类型2，速度控制函数明确要求类型3；固定提交中没有扭矩执行函数/调用路径。C++枚举公开JOINT_TORQUE不代表控制器已实现扭矩控制。
4. 现有逻辑最终可能将未支持命令导向错误/停止路径，但入口校验没有使用显式允许列表，INVALID=0也没有在解码入口直接拒绝。应将“协议枚举合法”与“当前固件/机型支持并可执行”分层处理。

### 1.3 运动命令数值检查存在模式差异

1. 位置控制将6个解码值直接赋给`jointRx`，调用`isInRange`检查关节位置范围；目标与当前关节位置之间的跳变/接近度检查仍为TODO。
2. 固定位置路径未见显式逐元素finite检查；不能仅凭`isInRange`调用推断NaN、正负Infinity及边界值在目标VAL3运行时均按预期拒绝，需目标版本API契约和注入测试。
3. 速度控制中的安全限值检查仍为TODO，`$setVelCmd`调用被注释，函数记录“not yet implemented”并返回错误。当前不能将JOINT_VELOCITY视为已实现闭环控制能力。
4. STOP命令的6个运动参考值没有在VAL3入口统一要求为零或明确忽略；其语义需在协议规范中固定，避免不同实现对无意义字段产生分歧。

### 1.4 模拟输出数值缺少VAL3入口约束

1. VAL3解码器将4个float32模拟输出值写入`nAnalogOutputs[0..3]`，但未发现finite检查、通道启用检查、工程量程/电压电流制式校验。
2. controlTask中的数字/模拟物理输出仍是TODO；因此本轮只能确认数据进入VAL3数据库，不能声称数值已经作用于物理端子。
3. TX2-60L/MED静态配置为2路模拟输出，而协议固定4路；具体通道映射、量程、单位和未配置通道处理仍需型号/选件/现场资料确认。

### 1.5 C++消息层往返成功不代表命令语义安全

1. `RobotCommandMessage::deserialize`验证固定payload长度和message type，但随后将命令字节直接static_cast为`CommandType`，未拒绝未定义枚举/当前机型不支持类型。
2. C++序列化/反序列化测试只验证正常数据往返和缓冲区过短；没有控制周期单位断言、非法命令枚举、NaN/Inf、float32溢出、位置跳变、模拟输出越界或VAL3端到端测试。
3. HardwareInterface、C++消息层和VAL3执行层的数值校验职责尚未形成可追踪的统一契约；任何一层的局部检查都不能替代其余层。

## 2. SERVO-855验收矩阵

| ID | 验收项 | 状态 |
|---|---|---|
| SM1 | C++控制周期生成与单位 | 静态确认write将period.seconds()乘1000，单位为ms |
| SM2 | VAL3 remote period字段解码 | 静态确认写入nRemoteCtrlPeriod |
| SM3 | remote period消费/范围检查 | 固定控制链未发现消费或校验路径 |
| SM4 | 控制周期测试数据与注释 | 静态确认0.008与“8 ms”不一致 |
| SM5 | CommandType枚举定义 | 静态确认0..4及内部0x0A/0x0B定义 |
| SM6 | VAL3入口命令类型门禁 | 静态确认范围门禁0..4，未使用明确支持列表 |
| SM7 | STOP/INVALID/TORQUE分支 | 静态确认0落入STOP类路径、4进入未知模式错误；无扭矩执行路径 |
| SM8 | 位置命令数值/范围检查 | 静态确认isInRange；目标跳变检查TODO；finite边界未证实 |
| SM9 | 速度命令限值和执行 | 静态确认安全限值TODO、setVelCmd注释、功能未实现 |
| SM10 | 模拟输出finite/量程检查 | 固定VAL3解码入口未发现相应检查 |
| SM11 | C++枚举/数值语义测试 | 现有测试仅正常往返，未覆盖异常边界 |
| SM12 | VAL3命令周期/枚举/NaN/Inf注入 | 未执行 |
| SM13 | CS9实际控制周期、位置/速度边界与模拟输出验证 | 未执行/缺现场证据 |
| SM14 | SIL/HIL、FAT/SAT及实机验收 | 未执行/缺证据 |

## 3. 整改建议

1. 明确协议controller_period单位、有效范围和容差；VAL3接收端验证有限性及允许范围，并明确该字段是仅用于监测还是参与控制。若控制周期固定由VAL3任务决定，应明确拒绝/告警不匹配周期，不能静默忽略。
2. 将命令入口改为显式允许列表：仅接受已实现且当前机型/模式允许的STOP、JOINT_POSITION等命令；INVALID、JOINT_TORQUE及内部专用类型必须明确拒绝，不得依赖后续默认分支处理。
3. 对6轴命令值在执行前统一执行finite、物理范围、速度/加速度/jerk及目标跳变检查；限值必须来自受控型号/工具/负载配置，并记录单位、坐标系和版本。
4. 在速度控制真正实现并完成限值、停止/超时和CS9验证前，将其明确标记为不可用能力，禁止把协议枚举存在等同于产品功能可用。
5. 对模拟输出逐通道验证是否配置、finite、量程、工程单位和失效默认策略；物理IO未实现前，不得宣称模拟输出功能通过。
6. 修正测试中0.008与“8 ms”不一致问题；增加毫秒换算断言、边界/异常枚举/NaN/Inf/float32溢出/跳变/模拟输出越界参数化测试。
7. 建立同一组命令黄金向量，覆盖C++编码、VAL3解码、控制器拒绝原因和状态反馈；在隔离CS9环境验证周期不匹配、非法命令、非有限值和限值边界。
8. 普通STOP、运动API错误返回及GPIO输出均不构成安全停止证明；安全功能必须由经验证的CS9安全架构及独立安全证据支撑。

## 4. 验证边界与结论

本轮仅审查固定提交中的C++协议/硬件接口/测试源码与VAL3命令解码、控制任务和运动控制程序。未运行C++构建/单测、VAL3 Studio导入/编译/下载、协议注入、周期压力测试、CS9运动/IO验证、停止时间测量、SIL/HIL、FAT/SAT或实机验证。finite检查是否由特定VAL3 API隐式完成、isInRange对NaN/Infinity的具体行为、CS9周期配置及模拟输出物理量程均需目标版本/现场证据确认。

未修改上游仓库，未应用PR。Stäubli工程级验收仍未通过；`TODO-EXT-001`未授权合并。根00-01与第21章21-02继续进行中。

**下一节点：§9.3.273 / SERVO-856。**
