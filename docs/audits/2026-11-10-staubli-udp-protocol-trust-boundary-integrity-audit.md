# Stäubli ROS 2—UDP协议输入可信边界与状态数据完整性审计

- 审计节点：§9.3.278 / SERVO-861
- 日期：2026-11-10
- 固定上游：`ICube-Robotics/staubli_driver_ros2@bd658e2d266e315d2ee35f985fb352ea88306b79`
- 范围：C++ UDP socket接收端点、协议FrameHeader、RobotState/RobotCommand/DiagnosticData反序列化、RobotDriver有效性/新鲜度门禁、VAL3 decodeHeader/readDataOnce/decodeRobotCommandMsg、ROS状态接口与现有测试。
- 方法：固定提交源码、配置结构和测试源码静态审查；未运行构建、测试或网络注入。

## 1. 执行摘要

本轮确认UDP输入可信边界尚未形成端到端闭环。接收端获得了数据报来源端点，但来源过滤仍是TODO；C++协议头公共解析器只检查magic number，消息版本、类型、payload长度的验证分散且不一致；状态消息缺少wire header完整校验；诊断消息在解析wire header之前检查对象默认header字段；VAL3端会检查magic/version，但没有检查wire payload_size。协议没有消息认证/完整性标签，也没有controller boot/session epoch，无法在协议层验证发送者身份或隔离旧会话数据。

因此，“UDP数据报到达”“反序列化返回true”“RobotDriver返回有效状态”并不等价于“数据来自当前可信控制器且内容完整”。该结论为源码静态审查结论；伪造来源、畸形包及跨重连旧包的可利用性仍需在隔离网络中动态验证。

## 2. 主要发现

### F1—UDP来源端点未校验（高）

`UDPSocketImpl::handle_data_received()`可访问`sender_endpoint_`与配置的`remote_endpoint_`，但来源地址比较仅保留为注释TODO，随后直接调用用户接收回调。当前没有在回调前强制要求数据报来源IP匹配配置的机器人IP；来源端口也没有实际校验。NetworkConfig虽包含robot_ip、remote ports及本地绑定地址/端口，但配置值没有转化为入站数据报的身份门禁。

影响：在网络可达且攻击者能够向本地UDP端口注入数据报的条件下，非预期主机可能污染状态/诊断缓存、影响序号跟踪或触发状态读取逻辑。仅按IP白名单仍不能抵御同网段主机伪造、IP冲突或会话重放；应同时验证预期端点并增加密码学消息认证。

### F2—接收错误路径仍调用数据回调（中/高）

`handle_data_received(error, bytes_transferred)`在error非空时只记录错误，未立即返回，随后仍将接收缓冲区交给`reception_callback_`。异步接收错误并不保证本次缓冲区与bytes_transferred构成一份有效新数据报。当前控制流可能把错误回调路径中的缓冲区内容继续交给反序列化器。是否能导致旧缓冲数据被消费，取决于具体Asio错误与bytes_transferred语义，属于需要故障注入确认的条件性风险。

整改：只有`!error`且字节数在合法范围内时才调用消息回调；错误路径应计数、记录错误类型并按接收线程生命周期策略决定是否重投递。

### F3—C++公共FrameHeader解析器只校验magic（高）

`FrameHeader::deserialize()`读取magic、protocol_version、message_type、sequence_number和payload_size，但仅拒绝magic number不匹配；不统一校验协议版本、允许的消息类型、payload长度及总帧长。消息反序列化器自行补充校验，导致不同消息类型的信任边界不一致。

- RobotState：反序列化后header validation区段为空；RobotDriver后续只检查message_type，连接成功路径另有一次protocol_version检查，但运行期每帧没有统一版本门禁。
- RobotCommand：检查payload_size与固定payload长度、检查message_type；未检查protocol_version。
- DiagnosticData：在调用`header.deserialize()`之前，先用当前对象的`header.payload_size`与`header.message_type`检查长度/类型。新建对象的这些字段是默认值，因此该检查没有验证收到的wire header；随后解析wire header，但没有再对wire payload_size作等价校验。
- 三类消息的长度判断均采用“至少达到固定长度”的模式，未统一要求datagram长度与header声明长度及固定消息长度完全一致；尾随字节可能被忽略。

### F4—VAL3与C++协议头验证不对称（高）

VAL3 `decodeHeader.pgx`解析8字节header并检查magic number=43981及protocol version=1，但没有检查payload_size是否与消息类型对应的固定长度一致。C++ RobotCommand路径有47字节payload检查，VAL3命令入口没有等价的wire payload_size校验；此前SERVO-854已记录VAL3命令解码在解析wire header前使用旧对象header字段判断缓冲区长度。本轮将其纳入跨语言输入完整性矩阵，不重复声称已动态复现。

### F5—缺少消息认证、完整性保护与会话身份（高）

FrameHeader只有magic/version/type/uint16 sequence/payload_size；没有MAC、数字签名、密钥标识、controller boot ID、session nonce或epoch。UDP校验和只能检测部分传输错误，不能提供发送者身份认证或抗恶意篡改。序号本身不能证明数据报来自当前控制器实例，也不能可靠地区分控制器重启、驱动重连与旧会话重放。

整改方向：在协议兼容性评估后引入带密钥的消息认证（覆盖header与payload）、随机会话挑战/应答、controller boot/session epoch及严格的重放窗口；密钥配置、轮换、失效与恢复必须纳入部署安全设计。不可仅靠magic number、固定源端口或uint16序号替代认证。

### F6—状态有效性与来源/完整性诊断没有向ROS层完整暴露（中/高）

`RobotDriver::read_robot_state()`在消息反序列化后检查message_type与staleness，并更新状态及last_valid_sequence_id；没有向上层暴露已验证的sender endpoint、协议校验失败原因、来源拒绝计数、认证状态、session epoch或状态帧接收时间。现有RobotState/DiagnosticData消息和HardwareInterface状态接口也没有为这些信息提供可审计的独立字段。状态新鲜度只基于本地接收时间，不能替代来源身份或完整性验证。

诊断读取路径同样依赖subscriber与本地staleness；连接循环中诊断read仍为TODO且diag ready被硬编码true（已在SERVO-852记录），本轮不将其重复计为新发现。

## 3. 现有测试覆盖评估

固定提交测试包含FrameHeader/消息序列化往返、缓冲区大小基本检查、UDP loopback双向收发、subscriber基本缓存读取/丢包/staleness以及RobotDriver mock状态/诊断发送。静态审阅未发现以下负向/安全测试：

- 非预期源IP与源端口的数据报必须在反序列化前拒绝；
- 伪造来源、同网段注入与端点变化；
- 错误magic、未知/旧protocol_version、非法message_type；
- RobotState/RobotCommand/DiagnosticData错误payload_size、短包、超长包及尾随字节；
- 诊断帧wire header错误，而对象header仍为默认值的回归测试；
- 接收错误回调、零字节/异常长度回调不得污染旧缓存；
- MAC错误、密钥轮换、认证失败、重放及跨session旧帧；
- 控制器重启后旧会话状态帧/命令帧被拒绝；
- ROS状态接口对无效、过期、未认证状态的明确失效传播。

现有round-trip测试证明同一C++实现的序列化与反序列化路径可相互兼容，不证明VAL3跨语言兼容、消息真实性或负向安全属性。

## 4. 风险与整改优先级

| 优先级 | 整改项 | 验收条件 |
|---|---|---|
| P0 | UDP入站来源端点校验及错误回调隔离 | 错误IP/端口与接收错误不进入消息反序列化/状态缓存；拒绝计数可观测 |
| P0 | 统一wire header与精确帧长校验 | 所有消息先解析wire header，再校验magic/version/type/payload_size/总长度；任何不匹配均拒绝且不污染旧状态 |
| P0 | 消息认证与会话抗重放 | 未认证、错误MAC、旧session、重复/过期nonce报文全部拒绝；合法新会话需显式握手 |
| P1 | C++/VAL3共同协议黄金向量与畸形向量 | 两端对有效帧字节完全一致，对相同畸形输入给出一致拒绝结果 |
| P1 | ROS状态有效性/来源/新鲜度可观测 | 上层能区分valid、stale、unauthenticated、wrong-source、malformed、replay等状态 |
| P1 | 网络故障与重启恢复测试 | 源端点变化、重连、控制器重启、乱序/重放不会续新鲜度或复用旧会话数据 |

安全架构建议：优先使用隔离控制网/VLAN与防火墙限制UDP端口作为纵深防御；协议层仍需认证与完整性保护。不要把网络隔离视为密码学身份认证，也不要把ROS状态有效标志视为安全功能。

## 5. 验收矩阵

| ID | 验收内容 | 预期结果 | 本轮状态 |
|---|---|---|---|
| UT-01 | 非预期源IP注入 | 回调前拒绝，不更新状态 | 未执行 |
| UT-02 | 正确IP但错误源端口 | 按配置端点策略拒绝 | 未执行 |
| UT-03 | 接收回调error非空 | 不调用消息回调、不更新缓存 | 未执行 |
| UT-04 | 错误magic | C++/VAL3均拒绝 | 未执行 |
| UT-05 | 旧/未知protocol_version | 所有消息类型均拒绝 | 未执行 |
| UT-06 | 非法message_type | 拒绝且不改变既有有效状态 | 未执行 |
| UT-07 | payload_size与类型固定长度不符 | 拒绝 | 未执行 |
| UT-08 | 短包、超长包、尾随字节 | 精确长度策略一致，全部不合规包拒绝 | 未执行 |
| UT-09 | DiagnosticData默认对象header与恶意wire header | 必须按wire header校验 | 未执行 |
| UT-10 | 伪造MAC/篡改payload | 认证失败，不进入状态缓存 | 未执行 |
| UT-11 | 旧session/控制器重启后重放 | 拒绝旧会话帧 | 未执行 |
| UT-12 | 合法握手与新session首帧 | 仅握手成功后接受 | 未执行 |
| UT-13 | 无效/未认证/过期状态向ROS传播 | 明确置invalid并暴露原因/计数 | 未执行 |
| UT-14 | C++/VAL3有效与畸形黄金向量 | 字节布局及拒绝行为一致 | 未执行 |
| UT-15 | SIL/HIL/CS9隔离网络与安全验收 | 通过批准的安全测试计划 | 未执行 |

## 6. 证据边界

已完成：固定提交源码、NetworkConfig、协议头/消息反序列化、VAL3 header/command decode及现有测试源码静态审查。

未执行：C++构建/单测、VAL3 Studio导入/编译/下载、源地址伪造/端口注入、畸形帧与尾随字节注入、接收错误注入、MAC/密钥/会话原型、抓包、CS9仿真、SIL/HIL、FAT/SAT及实机测试。没有目标网络拓扑、防火墙配置、密钥管理方案或控制器重启抓包证据。

因此本报告不是渗透测试报告、网络安全认证、功能安全评估或产品验收结论。未修改上游源码，未提交上游PR，未合并或关闭`TODO-EXT-001`。

## 7. 参考源码路径

- `staubli_robot_driver/src/communication/udp_socket_impl.hpp`
- `staubli_robot_driver/src/communication/protocol.cpp`
- `staubli_robot_driver/include/staubli_robot_driver/communication/protocol.hpp`
- `staubli_robot_driver/src/communication/messages.cpp`
- `staubli_robot_driver/src/communication/real_time_socket_subscriber.cpp`
- `staubli_robot_driver/src/robot_driver.cpp`
- `staubli_robot_driver/include/staubli_robot_driver/robot_driver.hpp`
- `staubli_robot_driver/val3/userapp/ros2_server/Serialization/decodeHeader.pgx`
- `staubli_robot_driver/val3/userapp/ros2_server/Serialization/decodeRobotCommandMsg.pgx`
- `staubli_robot_driver/val3/userapp/ros2_server/Comm/readDataOnce.pgx`
- `staubli_robot_driver/test/unit_tests/communication/test_message_serialization.cpp`
- `staubli_robot_driver/test/unit_tests/communication/test_rt_socket_interface.cpp`
- `staubli_robot_driver/test/unit_tests/test_robot_driver.cpp`

## 8. 节点状态

SERVO-861固定提交静态审查完成；UT-01至UT-15全部未执行。P0来源过滤、wire header统一校验、消息认证/会话抗重放仍未解决。下一节点：§9.3.279 / SERVO-862，专项审查ROS状态有效性与通信安全诊断接口的端到端暴露、失效传播及恢复门禁。
