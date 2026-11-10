# 2026-11-10 Stäubli ROS 2 UDP 发送结果契约与状态帧接纳门禁专项设计

> 节点：§9.3.283 / SERVO-866。类型：固定上游源码审查、接口契约和测试规格；不是上游修复或测试报告。  
> Stäubli 固定基线：`ICube-Robotics/staubli_driver_ros2@bd658e2d266e315d2ee35f985fb352ea88306b79`  
> ros2_control 参考：Jazzy `ros-controls/ros2_control@c6ef5a24e0cd21463edb99bded552a96f914b716`

## 1. 目标与结论

本节点细化 §9.3.282 的两个高优先级缺口：

1. `UDPSocketImpl::send()` 在 `would_block` 分支记录 packet dropped，却落到函数末尾返回 `true`；`RealTimeSocketInterface::send_message()`、`RobotDriver::send_robot_command()` 和 `send_stop_all_command()` 因此可能把未发送的数据报报告为成功。
2. UDP 接收数据尚未建立统一接纳门禁：来源 endpoint 检查是 TODO；异步接收错误仍进入用户回调；subscriber 对重复序号只将 `status.new_message` 设为 false，但函数仍返回 true；序号回退被按回绕处理；缓存接收时间可能因重复帧刷新。

**本轮只定义可实施契约和确定性测试。未修改 Stäubli 上游代码，未运行构建或测试。** 不得把本设计表述为问题已修复。

## 2. 固定源码事实

### 2.1 UDP 发送路径

固定提交中的调用链：

`UDPSocketImpl::send(vector<uint8_t>&)`
→ `RealTimeSocketInterface::send_message()`
→ `RobotDriver::send_robot_command()` / `send_stop_all_command()`
→ `StaubliHardwareInterface::write()` / `on_error()`。

`UDPSocketImpl::send()` 使用 Asio `send_to(..., MSG_DONTWAIT, err)`。当 `err == boost::asio::error::would_block` 时，日志明确报告 packet dropped，但未返回 false，最终返回 true。函数也没有检查返回的字节数。上层 bool 链会继承这一错误成功语义。

### 2.2 UDP 接收路径

- `UDPSocketImpl::handle_data_received()` 在 `error` 非空时只记录日志，随后仍调用 reception callback，并按 receiving 状态重新提交接收。
- `sender_endpoint_` 与 `remote_endpoint_` 的地址/端口比较仍是注释 TODO。
- `RealTimeSocketSubscriber::read_message()` 从 latest-message box 取值；没有新值时可以继续使用调用方传入的旧消息，并用该消息的 reception timestamp 计算年龄。
- subscriber 在重复序号时设置 `status.new_message=false`，但并不因此返回 false；序号小于上次读取值时被直接按 uint16 回绕估算丢包。
- `RobotDriver::read_robot_state()` 没有把 `status.new_message` 作为新状态接纳条件；仅检查读取 bool、message type 和 stale age。
- `RobotStateMessage::deserialize()` 当前只检查最小长度，未统一检查 header 的 protocol version、message type、payload size 和精确 datagram 长度；其他消息类型校验也不完全一致。该节点要求把通用帧头校验前移为共同接纳门禁，而不是继续在各消息类中散落不一致检查。

## 3. 发送结果接口契约

### 3.1 推荐结果类型

建议把 socket 到 RobotDriver 的 bool 发送接口逐层替换为显式结果类型：

| 结果 | 精确定义 | 可否称为发送成功 |
|---|---|---|
| `NOT_SENT` | 在调用发送系统调用前已知未发送，或系统调用明确以 would_block 等确定性错误拒绝该数据报 | 否 |
| `LOCAL_ACCEPTED` | UDP send API 无错误，且返回字节数严格等于完整 datagram 长度 | 仅可称“本地发送层接受” |
| `UNKNOWN` | 发送结果不能可靠归类，例如异常返回/长度异常或 socket 状态在结果判定期间失效 | 否；必须按未确认故障处理 |

约束：

- `LOCAL_ACCEPTED` 不代表网络已送达、CS9 已接收、VAL3 已解析、控制器接受/执行或机械臂停止。
- UDP datagram 不应被应用层拆分重试。对 `would_block` 不在实时线程中忙等、不无限重试；按 deadline 丢弃并报告 `NOT_SENT`。
- disconnected、序列化失败属于命令尚未交给 UDP 发送层，归类 `NOT_SENT`；异常/不确定结果归类 `UNKNOWN`。
- UDP API 若返回成功但字节数不等于 datagram 长度，不可当作完整接受；归类 `UNKNOWN` 并触发故障记录。
- `send_stop_all_command()` 返回或记录 `LOCAL_ACCEPTED` 只能说明本地发送层接受；当前协议没有独立 STOP ACK/command ID，因此控制器确认状态必须记录为 `UNSUPPORTED`，不能合成 ACK。
- 不得为得到“可靠 STOP”而在周期线程中同步重试、阻塞等待网络或新增未经风险评估的 STOP 发送线程。

### 3.2 计数器与事件记录

建议至少暴露单调计数器：

- `udp_tx_attempt_total`
- `udp_tx_local_accepted_total`
- `udp_tx_not_sent_total{reason}`
- `udp_tx_unknown_total{reason}`
- `udp_rx_datagram_total`
- `udp_rx_rejected_total{reason}`
- `udp_rx_accepted_total{message_type}`
- `udp_rx_duplicate_total`
- `udp_rx_reordered_total`
- `udp_rx_unexpected_endpoint_total)

实时线程只做有界计数、保存定长事件摘要或向无阻塞队列写入；日志格式化、磁盘 I/O 和慢速诊断不得阻塞控制周期。计数器必须定义生命周期（进程累计还是连接代次累计），建议两者都保留：进程累计用于运维，generation 计数用于诊断单次会话。

STOP 尝试记录至少包含本地 event ID、连接 generation、请求时间、序列化结果、发送结果、错误码、控制器 ACK 状态（当前 unsupported）及后续状态观测引用。event ID 仅是本地关联 ID，不得伪装为协议 command ID。

## 4. 统一状态帧接纳算法

状态帧必须按以下顺序接纳。任何步骤失败均不得更新 latest-message box、有效接收时间、last accepted sequence 或硬件状态快照。

1. **接收完成状态：** 异步接收 `error` 非空时不得把 buffer 作为有效 datagram 交给解析器。将 operation_aborted 与真实 I/O 错误区分；按接收线程/关闭状态决定是否重新投递下一次 receive。
2. **数据报边界：** `bytes_transferred` 不得超过缓冲区；必须与对应消息类型的精确预期总长度一致。短帧、超长帧和截断帧全部拒绝。
3. **来源 endpoint：** sender address 与配置的 remote address 匹配，sender port 与对应控制/诊断 remote port 匹配。若部署允许 NAT 或多地址，必须显式配置允许列表，不得退化为“任意来源”。
4. **帧头完整性：** 检查 magic、协议版本、message type、payload size 与精确总长度；header 声明长度必须与实际 datagram 长度和该 message schema 一致。
5. **字段完整性：** 检查枚举值、标志位保留位、必需 valid-field flags、浮点数 finite 性和适用物理范围。机型范围必须来自可追溯规格，不能在本设计中臆造。
6. **序号接纳：** 在当前连接 generation 中，对 16-bit sequence 使用模数前向差值规则（见 5 节）；重复、回退/乱序和歧义跳变不得提交。
7. **时间新鲜度：** 使用本机单调时钟记录接收时刻；只有通过前述全部检查的新帧才更新 freshness。重复或畸形帧不得续新鲜度。
8. **原子提交：** 解析后的 message、sequence、receive timestamp、endpoint、generation 和 validity 作为一个一致快照提交。消费者不能观察到部分字段已更新、其他字段仍来自旧帧的混合快照。

来源地址过滤不是消息认证。即使 endpoint 匹配，UDP 数据仍可能被伪造或重放；当前协议没有密码学认证与远端 session epoch，不能宣称已解决网络身份认证或抗重放。

## 5. 16-bit 序号策略

对同一 message stream、同一连接 generation 维护 `last_accepted_seq`。候选序号 `candidate` 与上次序号之间按 16-bit 模数计算：

`delta = uint16_t(candidate - last_accepted_seq)`

| 条件 | 判定 | 动作 |
|---|---|---|
| 尚无本代次基线 | 首帧候选 | 仅在 endpoint、帧头、payload、字段和会话门禁全部通过后建立基线 |
| `delta == 0` | 重复帧 | 拒绝；不更新 timestamp、不更新 mailbox、不刷新状态有效性 |
| `1 <= delta < 0x8000` | 前向帧（含合法模数回绕） | 接纳；丢包估算为 `delta - 1` |
| `delta == 0x8000` | 半空间歧义 | 拒绝并记为 ambiguous jump；不能推断前进或回退 |
| `delta > 0x8000` | 回退/乱序/旧帧候选 | 拒绝；不更新基线和 freshness |

注意：

- 该规则是对同一连续发送序列的本地接纳策略，不是远端身份认证。
- 控制器重启后序号归零而本地 generation 未变化时，无法仅靠 16-bit 序号可靠区分重启新流和旧帧；应锁存 session discontinuity，要求显式重建连接/会话基线，并在系统层阻止自动恢复运动。
- 若协议允许任意长度的中断后继续接收，半空间规则可能拒绝合法大跳变；这属于明确的安全取舍，不能放宽为无条件接受回退。需要由正式协议规范定义最大可接受间隔/重启识别方式。
- 控制状态、诊断状态和其他不同 stream 必须独立维护序号基线。

## 6. 连接 generation 与缓存提交

- 每次开始新连接事务分配新的本地 generation；connect 部分失败也不得复用旧 generation。
- 接收操作、回调、解析结果和快照都携带 generation；generation 不匹配的迟到回调不得提交。
- disconnect 必须先阻止新回调提交，再取消/停止接收并 join 线程，关闭 socket，最后清空缓存与序号基线；资源清理结果逐项记录。
- 新 generation 的状态快照初始为 invalid；只有有效首帧和序号策略建立后才变为 valid。
- 远端 boot/session ID 不存在时，generation 只隔离本地旧回调，不能证明远端会话唯一性。
- `read_message()` 应明确区分“返回已有快照”和“本周期收到新帧”；调用者不得把同一快照重复消费误认为新状态。建议 API 返回 `ReadResult{snapshot, is_new, age, generation}`，并让硬件 read 根据 age/validity 明确处理。

## 7. 确定性测试规格

以下测试全部**未执行**。推荐先在纯单元测试与 loopback mock socket 完成，再进入 ResourceManager/ControllerManager 集成和 SIL。

### 7.1 发送测试

| ID | 注入 | 预期 |
|---|---|---|
| SERVO866-TX-01 | 正常 UDP send，返回完整长度且无错误 | `LOCAL_ACCEPTED`，accepted 计数 +1 |
| SERVO866-TX-02 | socket 未连接 | `NOT_SENT`，不得调用系统发送 |
| SERVO866-TX-03 | `would_block` | `NOT_SENT`，dropped/not_sent 计数 +1；上层不得返回成功 |
| SERVO866-TX-04 | 其他明确 socket error | `NOT_SENT` 或按 API 语义明确的失败分类；错误码保留 |
| SERVO866-TX-05 | 异常/不一致返回长度 | `UNKNOWN`，故障事件可观测 |
| SERVO866-TX-06 | 序列化失败 | `NOT_SENT`，socket send 调用次数为 0 |
| SERVO866-TX-07 | STOP send would_block | STOP 记录为未发送/未确认；不得记录 ACK 或停止确认 |
| SERVO866-TX-08 | 正常本地 STOP send | 只记录 LOCAL_ACCEPTED；controller ACK 保持 UNSUPPORTED |
| SERVO866-TX-09 | 连续 would_block 达到配置阈值 | 计数与故障升级符合明确阈值；控制线程无忙等/阻塞 |

### 7.2 接收接纳测试

| ID | 注入 | 预期 |
|---|---|---|
| SERVO866-RX-01 | 配置 endpoint 的合法首帧 | 建立本 generation 首帧和序号基线 |
| SERVO866-RX-02 | 错误来源 IP | 拒绝，不更新 mailbox/freshness |
| SERVO866-RX-03 | 正确 IP、错误端口 | 拒绝，不更新 mailbox/freshness |
| SERVO866-RX-04 | 短帧、超长帧、payload_size 不符 | 拒绝，不解析/不提交 |
| SERVO866-RX-05 | magic/version/type 不符 | 拒绝并记录具体原因 |
| SERVO866-RX-06 | 非法枚举、保留标志位、NaN/Inf | 拒绝，不刷新状态 |
| SERVO866-RX-07 | 合法前向序号 | 接纳并更新 sequence/freshness |
| SERVO866-RX-08 | 重复序号 | 拒绝；timestamp 不得刷新 |
| SERVO866-RX-09 | 合法 65535→0 回绕 | 接纳，delta=1 |
| SERVO866-RX-10 | 回退/乱序序号 | 拒绝，不回退 last accepted sequence |
| SERVO866-RX-11 | delta=0x8000 | 拒绝为歧义跳变 |
| SERVO866-RX-12 | 新 generation 到达旧 generation 迟到回调 | 拒绝旧回调提交 |
| SERVO866-RX-13 | receive operation_aborted / socket close | 不把错误 buffer 送入 callback，不意外重启接收 |
| SERVO866-RX-14 | 合法帧后连续畸形/重复帧 | 最后有效快照保留但 age 持续增长，超阈值后对消费者报告 invalid/stale |
| SERVO866-RX-15 | 控制器重启、序号重置但本地连接未重建 | 标记 session discontinuity；禁止自动运动恢复 |

### 7.3 跨层测试

| ID | 场景 | 预期 |
|---|---|---|
| SERVO866-IT-01 | write 正常命令遇到 would_block | 硬件 write 不得返回成功 |
| SERVO866-IT-02 | on_error STOP 遇到 would_block | STOP 发送结果可见，生命周期返回值不伪装停止确认 |
| SERVO866-IT-03 | 重复状态帧反复到达 | 不延长状态有效期；最终 stale/read ERROR |
| SERVO866-IT-04 | 非预期来源连续发送伪造状态 | 不更新 ROS state interfaces |
| SERVO866-IT-05 | 旧帧/乱序帧在 reconnect 后到达 | generation/sequence 门禁拒绝 |
| SERVO866-IT-06 | 发送和接收故障同时发生 | 事件顺序可追溯，故障锁存不被后续成功帧清除 |

## 8. 验收准则

- AC-866-01：UDP would_block 不再通过任何上层 bool 被表示为发送成功。
- AC-866-02：发送结果能区分 NOT_SENT、LOCAL_ACCEPTED 和 UNKNOWN。
- AC-866-03：本地发送接受不被表述为控制器 ACK、执行确认或物理停止。
- AC-866-04：接收错误、非预期 endpoint、长度/帧头/字段不合法的数据报均不能进入状态缓存。
- AC-866-05：重复、乱序、回退和歧义序号不更新 last accepted sequence 或 freshness。
- AC-866-06：合法序号回绕按模数前向规则接受，且丢包估算可复核。
- AC-866-07：所有接纳字段、时间戳、序号、endpoint、generation 和 validity 原子提交。
- AC-866-08：disconnect/reconnect 后旧 generation 回调不能污染新状态。
- AC-866-09：发送/接收计数和拒绝原因可观测且不阻塞实时线程。
- AC-866-10：故障后运动恢复仍需显式授权与独立安全许可，不由网络恢复自动触发。

## 9. 未执行项与边界

- 本节点为固定源码静态核对与设计规格；未修改 Stäubli 上游。
- SERVO866-TX-01 至 TX-09、RX-01 至 RX-15、IT-01 至 IT-06 全部未执行。
- 未运行 C++/ROS 2 构建、单元测试、loopback fault injection、网络代理/抓包、TSan/ASan、ResourceManager/ControllerManager 集成、SIL/HIL、VAL3/CS9、FAT/SAT 或实机测试。
- 未修改 ros2_control 上游，未应用/合并 Stäubli PR；`TODO-EXT-001`仍未授权。
- 来源 endpoint 过滤不等于密码学认证；本地 generation 不等于远端 session epoch；软件 STOP 不是安全功能。

## 10. 参考源码

- [udp_socket_impl.hpp](https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/src/communication/udp_socket_impl.hpp)
- [real_time_socket_subscriber.cpp](https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/src/real_time_socket_subscriber.cpp)
- [real_time_socket_interface.cpp](https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/src/real_time_socket_interface.cpp)
- [robot_driver.cpp](https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/src/robot_driver.cpp)
- [messages.cpp](https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/src/communication/messages.cpp)

## 11. 下一节点

**§9.3.284 / SERVO-867：发送/接收门禁测试夹具、Mock Socket seam 与确定性故障注入架构设计。** 在不修改上游的前提下，确定最小可测试边界、注入点、测试数据构造器、时钟控制、回调代次隔离和证据归档结构。
