# Stäubli ROS 2—VAL3命令帧入口校验与无效命令处理审计

- 审计节点：§9.3.271 / SERVO-854
- 日期：2026-11-10
- 固定上游：`ICube-Robotics/staubli_driver_ros2@bd658e2d266e315d2ee35f985fb352ea88306b79`
- 审查方式：固定提交静态源码与现有测试代码审查；未执行动态测试。
- 范围：VAL3 `initHeader`、`initRobotCommandMsg`、`decodeHeader`、`decodeRobotCommandMsg`、`controlTask`；C++ RobotCommandMessage序列化/反序列化；现有消息序列化测试。

## 1. 主要结论

### 1.1 VAL3命令解码先检查旧header，再读取wire header

1. `initRobotCommandMsg()`将本地header初始化为8字节，payload_size=47，并分配55字节序列化缓冲区。
2. `decodeRobotCommandMsg()`第27–31行在调用`decodeHeader()`前，先用当前对象的`header.nHeaderSize + header.nPayloadSize`与缓冲区长度比较。此时header字段仍是初始化时的本地值，而不是当前数据报内的wire header。
3. 随后`decodeHeader()`读取wire header并覆盖`nPayloadSize`；其实现只验证magic number和protocol version，不验证消息类型或payload_size。消息类型在调用方单独检查，但没有在读取header后重新检查payload_size是否为47。
4. 因此，当实际数据报仍为55字节、但wire header声明的payload_size错误时，前置长度检查仍可按本地初始化值通过；decodeHeader又不验证新读入的payload_size；解码器随后按固定字段偏移解析，最终只检查offset是否等于实际缓冲区长度。静态代码路径表明，这类header声明错误可能被接受并把命令标记为有效。
5. 这不是SERVO-853中RobotState帧头编码错误的重复描述，而是接收方向的独立缺口：发送帧头长度可能写错，VAL3命令接收端又没有对wire payload_size进行可靠拒绝。

### 1.2 header/长度错误分支未立即清除旧命令有效标志

1. `decodeRobotCommandMsg()`在header解析失败或message type错误时，将motion command type设为STOP后直接return，但该分支没有显式将`robotCommand.bIsValid=false`。
2. 只有后续offset与实际buffer size不一致的分支才明确将命令置为invalid并设置STOP。
3. `controlTask`收到`l_bErrorTmp`后会设置`l_bError=true`、将命令模式转STOP，并在后续错误复位流程中清除`robotCommand.bIsValid`。因此当前主任务有一层延迟的错误收敛，但decoder本身并不保证所有失败出口都立即失效；未来独立调用、早退路径或任务流程调整可能暴露旧有效状态。
4. 对于上一帧有效、下一帧header错误的序列，不能仅凭decoder早退路径证明`bIsValid`立即失效。该风险尚未通过VAL3运行时复现。

### 1.3 C++与VAL3对命令payload的验证强度不一致

1. C++ `RobotCommandMessage::deserialize()`读取wire header后，明确验证payload_size等于固定命令payload长度47，并验证message_type为ROBOT_COMMAND。
2. VAL3 `decodeRobotCommandMsg()`只在解析header前按旧对象字段检查总缓冲区长度；读取header后只检查message type，未验证wire payload_size等于47。
3. C++路径仍存在protocol_version未统一验证的问题（已在SERVO-798/853记录），但对payload_size的检查比VAL3命令入口完整。
4. C++单元测试覆盖C++消息自己的serialize/deserialize往返和buffer过短情况，不覆盖VAL3 decodeHeader/decodeRobotCommandMsg的实际逻辑，也没有wire header payload_size错误、错误版本、错误类型、截断/尾随数据的定向测试。

### 1.4 命令错误处理并不等同于安全停止证明

1. `controlTask`在decode失败后设置错误并将命令模式转STOP；错误处理路径调用停止/复位函数并重置socket。
2. 该路径没有证明物理停止时间、静止反馈、驱动安全状态或GPIO安全输出；GPIO数字/模拟输出写入仍为TODO。
3. 因此，错误帧触发软件STOP不能被描述为安全停止功能，也不能替代CS9安全回路、STO或经认证的安全控制链路。

## 2. SERVO-854验收矩阵

| ID | 验收项 | 状态 |
|---|---|---|
| CI1 | VAL3命令初始化长度与固定协议长度 | 静态确认header 8 B、payload 47 B、总帧55 B |
| CI2 | decode前长度检查使用字段来源 | 静态确认使用旧对象初始化header，而非wire header |
| CI3 | decodeHeader wire字段验证 | 静态确认验证magic/version，未验证payload_size |
| CI4 | 解码后payload长度校验 | 静态确认缺少wire payload_size=47检查 |
| CI5 | message type校验 | 静态确认VAL3调用方单独校验type=2 |
| CI6 | 字段偏移与最终buffer长度检查 | 静态确认按固定偏移解析，最后比较offset与实际buffer size |
| CI7 | 解码错误时命令有效标志处理 | 静态确认header/type早退不显式清除bIsValid；offset失败分支会清除 |
| CI8 | controlTask错误后的STOP/复位路径 | 静态确认软件STOP、运动停止/复位、清除有效标志并reset socket |
| CI9 | C++ RobotCommand payload_size校验 | 静态确认C++检查固定47 B payload及message type |
| CI10 | C++/VAL3跨语言畸形帧测试 | 未执行；现有测试不运行VAL3解码器 |
| CI11 | wire payload_size错误但实际长度55 B注入 | 未执行 |
| CI12 | 旧命令有效后注入错误header的有效标志测试 | 未执行 |
| CI13 | CS9控制器上的无效帧/STOP响应和静止反馈 | 未执行/缺现场证据 |
| CI14 | SIL/HIL、FAT/SAT及实机验证 | 未执行/缺证据 |

## 3. 整改建议

1. 先解析固定8字节wire header，再验证magic、protocol version、message type、sequence number、payload_size和实际datagram长度；禁止在解析wire header前用旧对象字段判断当前报文长度。
2. 对RobotCommand严格要求wire payload_size=47、总长度=55，并拒绝短帧、长帧、尾随字节、声明长度不一致和未知版本；长度检查必须在任何字段解码前完成。
3. 所有decoder失败出口统一执行：`bIsValid=false`、命令类型STOP、清除/隔离旧命令缓存，并返回明确错误码；不要依赖controlTask后续路径补做失效处理。
4. 在controlTask中将解析错误、命令语义错误、过期命令、运动执行错误分别编码为可诊断故障事件；错误清除前保存事件ID、时间戳和触发字段。
5. 对命令类型、controller period、6轴命令数据、16-bit数字IO mask及4路模拟输出执行合法枚举、finite、设备范围、配置范围和运行模式检查。
6. 建立C++与VAL3共用的协议测试向量/黄金报文；对每个字段偏移、payload size、端序、sequence边界和异常输入做双端一致性测试。
7. 将软件STOP和安全停止严格区分。安全相关动作必须由经验证的CS9安全架构执行；不得把普通UDP命令、VAL3 stopMove/resetMotion或普通GPIO当作STO/SS1/SS2证明。
8. 在隔离CS9环境进行错误payload长度、错误type/version、截断/尾随、上一帧有效后下一帧非法、重复帧和过期命令注入；记录命令接受/拒绝、状态回读、停止时间和安全链路独立证据。

## 4. 验证边界与结论

本轮仅审查固定提交的VAL3程序、C++消息实现、controlTask及现有单元测试源码。未运行C++构建/单测、VAL3 Studio导入/编译/下载、UDP报文注入/抓包、CS9仿真、停止时间测量、SIL/HIL、FAT/SAT或实机验证。wire payload_size错误但datagram长度正确的接受路径是静态控制流推断，尚未动态复现；decoder失败出口旧有效标志问题也未运行时复现。

未修改上游仓库，未应用PR。Stäubli工程级验收仍未通过；`TODO-EXT-001`未授权合并。根00-01与第21章21-02继续进行中。

**下一节点：§9.3.272 / SERVO-855。**
