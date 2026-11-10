# Stäubli ROS 2—UDP接收缓存、序号回绕与重复/乱序数据报新鲜度专项审计

- **审计编号：** SERVO-860
- **章节节点：** §9.3.277
- **日期：** 2026-11-10
- **审查基线：** `ICube-Robotics/staubli_driver_ros2@bd658e2d266e315d2ee35f985fb352ea88306b79`
- **目标分支：** `rexyll/robot_knowledgebasement:main`
- **审计性质：** 固定提交静态源码、VAL3通信流程与现有单元测试源码审查；未执行网络注入、构建、VAL3/CS9或实机测试。

## 1. 审计目标与范围

本节点承接SERVO-851/SERVO-859，专门检查UDP数据报从内核接收队列到C++/VAL3消费端的缓存语义与序号判定：

1. C++异步接收线程是否按数据报顺序接收、验证来源并保留队列；
2. `RealtimeThreadSafeBox`使用方式是否保留所有帧，还是只保留最新帧；
3. 序号重复、倒退、回绕和重放是否能被区分；
4. 状态新鲜度时间戳是在数据源前进时更新，还是任何成功解码帧都会刷新；
5. VAL3 `readData/readDataOnce` 每个控制周期的接收次数、缓存覆盖与序号校验；
6. 现有测试是否覆盖真实重复UDP包、乱序、回绕、突发包和意外来源。

核对文件：
- C++：`src/communication/udp_socket_impl.hpp`、`udp_socket.cpp`、`real_time_socket_subscriber.cpp/.hpp`、`communication/protocol.hpp`、`robot_driver.cpp`。
- VAL3：`controlTask.pgx`、`Comm/readData.pgx`、`Comm/readDataOnce.pgx`、`Comm/getNextSequenceNumber.pgx`、`Comm/computeSequenceDelay.pgx`。
- 测试：`test_rt_socket_interface.cpp`、`test_robot_driver.cpp`。

## 2. C++ UDP接收与缓存事实

### 2.1 异步UDP接收回调每次接收一个数据报

`UDPSocketImpl::start_receive()` 调用Boost.Asio `async_receive_from`，完成后进入 `handle_data_received()`；回调处理结束后再安排下一次接收。接收线程使用单个 `recv_buffer_`，大小为 `MAX_SOCKET_PACKET_SIZE=1024`。该实现按UDP数据报回调，不是把字节流拆帧的TCP解析器。

`handle_data_received()` 在error非空时记录错误，但仍继续调用用户回调，没有在错误分支直接丢弃本次数据。来源地址验证代码明确以TODO注释保留，当前没有比较 `sender_endpoint_` 与配置的 `remote_endpoint_`。因此，静态实现没有证明只有配置的机器人IP可以向状态订阅器注入数据。

### 2.2 接收缓存是单个最新值槽，而不是有界帧队列

`RealTimeSocketSubscriber::update_message()` 对每个成功反序列化的UDP数据报：
1. 创建一个消息对象；
2. 设置本地 `reception_timestamp=now()`；
3. 调用 `message_buffer_.set(msg)` 覆盖缓存。

消费者 `read_message()` 调用 `message_buffer_.try_get()` 获取缓存中的可用消息。订阅器没有维护按序号排列的帧队列，也没有在写入槽前比较序号、拒绝重复/旧帧或保存每个帧的接收队列。因此，在两次read之间收到多个数据报时，消费者可能只看到最后一个缓存值；中间帧不会由本类逐帧交付。序号跳号计数只能基于消费者上次读取与本次取得的两个序号估算遗漏量，不能恢复被覆盖的帧内容。

这里的结论仅针对驱动对RealtimeThreadSafeBox的调用方式；没有把第三方库内部实现细节或实时调度行为推断为已验证事实。

### 2.3 任意成功解码的数据报都会刷新接收时间

`update_message()` 在deserialize成功后立即刷新本地接收时间，再写入最新值槽；刷新动作发生在序号检查之前。之后 `read_message()` 计算 `time_since_received`，再以 `last_read_sequence_number_` 比较序号。相同序号会被标记 `new_message=false`，但仍返回true并使用刚刷新过的时间戳。

因此，真实网络重复投递同一旧RobotState帧时，订阅器可能把它显示为“最近刚收到”，尽管状态源序号没有前进。RobotDriver此前未要求 `new_message=true`，故仅用本地接收年龄不能证明状态源持续产生新状态。这与SERVO-851/SERVO-859发现一致，本节点进一步定位到缓存覆盖前不做序号门禁这一根因位置。

### 2.4 序号下降被无条件按回绕处理，并更新比较基线

`read_message()` 的序号逻辑：
- 新序号大于上次序号：按普通递增，计算差值减一；
- 新序号小于上次序号：按uint16回绕计算丢包数；
- 相等：标记 `new_message=false`。

该逻辑没有采用半区间模序比较（例如对16位序号计算差值，并区分小幅前进与大幅倒退），也没有最大允许前进窗口。更重要的是，无论序号是合法回绕还是旧乱序帧，函数最后都会把 `last_read_sequence_number_` 更新为当前读到的序号。

示例：
- 正常回绕：65535 → 0，应该被接受为前进1；
- 旧帧倒退：100 → 99，当前实现也走“回绕”分支，估算出65534个丢包，并把比较基线改成99；
- 随后到达101时，驱动又以99为基线计算，先前的异常帧已污染序号状态。

因此，当前实现能计算一种形式的跳号量，但不能可靠区分合法回绕、延迟乱序、历史重放或设备重启后序号重置。实际UDP网络是否发生特定重排/重放，需要动态注入验证。

### 2.5 UDP来源端点检查明确尚未实现

`handle_data_received()` 中有一段注释掉的sender endpoint检查，TODO说明意图是丢弃非预期主机的数据，避免恶意来源注入状态或干扰序号跟踪。当前代码没有启用该检查。UDP socket使用 `async_receive_from` 接收并获得 `sender_endpoint_`，但未将其与配置的远端地址进行比较。

**风险：** 在网络隔离、ACL、防火墙或机器人专网之外，驱动本身不能提供来源认证/过滤保证。该问题属于网络输入信任边界，不应只通过序号检查解决；建议同时使用网络层隔离、来源校验和消息完整性/认证机制。

## 3. C++发送路径的附带关键发现

本节点虽然聚焦接收缓存，但核对UDP实现时发现一个直接影响STOP和所有命令的发送结果问题：

`UDPSocketImpl::send()` 调用 `socket_.send_to(..., MSG_DONTWAIT, err)`。当 `err == boost::asio::error::would_block` 时，代码明确记录“Packet dropped”，并注释TODO考虑丢包计数或阈值错误；但该分支没有返回false，函数最终仍返回true。

上层 `RealTimeSocketInterface::send_message()` 将socket `send()` 的true作为发送成功并返回true。因此，当内核发送缓冲区满/不可立即发送时，命令数据报实际被丢弃，但上层仍可能报告成功。这比“UDP send成功不代表远端收到”更早一层：该分支连本地发送调用完成数据报发送都没有证明。

这也修正SERVO-859对本地发送成功语义的概括：准确说，`send_message()==true` 表示序列化成功且底层send接口没有报告硬错误；对于would_block分支，底层明确丢弃数据报却仍返回true。它绝不代表远端接收、接受或执行。

## 4. VAL3接收与序号事实

### 4.1 每个controlTask周期最多执行两次sioGet尝试

`readData.pgx` 将最大尝试次数设为2，每次调用 `readDataOnce.pgx`。`readDataOnce` 通过 `sioGet()` 读取一个UDP数据报：
- 读到与固定数组长度相同的数据，置 `x_bNewData=true`；
- 读到非零但长度不符的数据，报告通信错误；
- 未读到数据则保持false。

如果两次尝试均读到数据，第二次读取会覆盖同一 `x_nData` 数组，最终控制任务只解码最后一次读取保留的内容。该函数不是无界清空接收队列，也没有对两份数据逐帧解码、逐帧验证序号或逐帧执行命令。超过两次尝试的剩余数据报是否积压、丢弃或由控制器网络栈后续交付，需在CS9/VAL3运行环境动态确认。

### 4.2 VAL3序号生成与delay计算不是接收窗口

`getNextSequenceNumber.pgx` 每周期加一，超过65535回到0。该逻辑正确覆盖简单uint16回绕生成。

`computeSequenceDelay.pgx` 计算 `nLastSequenceSent - nLastSequenceReceived`；只有结果小于-60000时才加65536修正回绕。其余负值保持负数，由 `controlTask` 后续将负delay视为错误。该函数没有维护命令序号接收窗口、最近已接受序号、重复命令缓存或session epoch。

大幅负差值会被当成回绕修正，因此单凭该delay函数不能区分真实回绕与某些跨回绕的旧序号/重放场景。小幅负差值会在控制任务后续触发错误，但这仍是延迟异常处理，不是严格的乱序拒绝与事务去重协议。

### 4.3 VAL3命令缓存与过期检查仍有TODO

`controlTask.pgx` 在没有新命令但上次命令有效时，进入“检查previous message staleness”的分支，但实际内容仍为TODO；主循环末尾也保留staleness/lost package TODO。接收流程没有显式last accepted command ID、去重窗口或跨重启session epoch。

## 5. 现有测试覆盖边界

### 5.1 已覆盖内容

- `test_rt_socket_interface.cpp::ReceiveMessage`：发送一帧RobotState，读取后再次读取同一缓存，验证第二次read的 `new_message=false`，并等待时间戳staleness。
- `LostPackageDetection`：序号7后跳至9，检查丢包计数1；随后发送10、11、12再读取，检查估算遗漏数量。
- `BidirectionalCommunication`：验证基本RobotState/RobotCommand双向收发。
- `test_robot_driver.cpp::ReadRobotStateTest`：验证正常状态读取、停止mock发送后的staleness失败，以及重新发送后恢复读取。

### 5.2 未覆盖内容

- 未发现再次通过UDP网络发送相同序号/相同payload，验证新接收时间是否被刷新。
- 未发现序号倒退（例如100→99）后是否被错误接受并污染比较基线的测试。
- 未发现65534→65535→0→1回绕边界及回绕附近历史帧的测试。
- 未发现消费者读取间隔内大量UDP帧覆盖缓存时，丢包计数与最新状态是否正确的边界测试。
- 未发现VAL3每周期两次sioGet遇到三帧以上突发包时的队列/覆盖实验。
- 未发现非配置sender endpoint的数据报注入测试。
- 未发现would_block时send()返回值与实际发包情况一致性的测试。
- 现有ReceiveMessage第二次read是再次读取同一个缓存值，不是网络层重复UDP包；两者不可混为一谈。

## 6. 主要发现

### RX1｜C++最新值缓存覆盖中间帧，不具备逐帧交付语义

订阅器每次解码后以 `message_buffer_.set(msg)` 覆盖单值槽，消费者以 `try_get()` 取值，没有队列或逐帧确认。

**风险：** 两次read之间的中间状态帧可能被覆盖；lost_packages只是基于最后一次消费的序号差估算，不提供中间状态、逐帧事件或时间序列证据。

### RX2｜重复序号在缓存写入前不被拒绝，重复帧可刷新状态新鲜度

序号比较在read侧进行，而时间戳已在update_message侧刷新；重复帧被标记new_message=false但仍可返回并更新age。

**风险：** 重放/重复数据报可能维持状态表面新鲜；新鲜度不等于状态源推进。

### RX3｜序号倒退被误认为回绕，且异常帧污染比较基线

当前逻辑对任何小于last_read_sequence_number_的值都按uint16 wrap计算，并无条件更新last_read_sequence_number_。

**风险：** 旧乱序帧、历史帧和真实回绕不可区分；一次异常帧即可改变后续丢包统计基线。

### RX4｜UDP接收端没有启用来源地址校验

接收回调获取sender_endpoint_，但地址比较仅以TODO注释保留。

**风险：** 在网络层未隔离时，其他主机可能向状态端口注入格式合法的数据报，影响状态缓存、序号与新鲜度。是否能到达目标端口取决于实际网络配置，尚未动态验证。

### RX5｜would_block丢包时UDP send仍返回true

底层代码明确记录数据包已丢弃，但未返回false；上层send_message据此报告成功。

**风险：** STOP或运动命令可能在本地发送缓冲区拥塞时静默丢弃，并被上层误判为成功。必须修复返回值并增加丢包计数/错误门限。

### RX6｜VAL3每周期两次读取可能覆盖同周期第一帧，且没有序号接收窗口

readData最多两次sioGet，第二帧可覆盖第一帧；controlTask没有last accepted command ID或严格staleness窗口。

**风险：** 突发命令的逐帧处理顺序和积压行为没有明确协议保证；需结合CS9的sioGet队列语义与周期运行数据验证。

### RX7｜现有测试未覆盖实际重复、乱序、回绕、来源注入和would_block

测试覆盖的是同一缓存重复读取、跳号估算、基本收发与staleness，并非网络重复数据报、倒退帧、回绕或内核发送拥塞。

**风险：** 当前测试通过不能证明UDP序号过滤、接收缓存保序、来源认证或发送失败传播正确。

## 7. 建议整改与验收设计

### 7.1 C++接收侧

1. 在接收回调/缓存写入前校验来源端点、magic/version/type/payload长度和当前session。
2. 对uint16序号采用模差半区间比较：`delta=(new-last) mod 65536`；delta=0判重复，1..32767判前进，32768..65535判旧帧/乱序（窗口边界需协议明确）。
3. 只有被接受的新鲜前进帧才能更新last_fresh_timestamp和状态缓存；重复、乱序、旧会话帧单独计数并丢弃。
4. 明确选择最新值语义或有界队列语义。若控制只需最新状态，需保留累计丢帧计数/最大接收间隔；若需要事件或ACK逐帧关联，则必须使用队列并定义溢出策略。
5. 接收缓存增加session epoch、source timestamp/sequence、accepted/rejected reason与last fresh receive time；重连/重启时重新握手。
6. 避免在无认证UDP上只依赖16位序号防重放；优先考虑受控网络隔离和带认证的会话标识/消息完整性。

### 7.2 VAL3接收侧

1. 对每个完整数据报先解析并校验序号/会话，再更新有效命令缓存。
2. 明确readData每周期最多两次的设计意图；若要排空积压，应有受控上限、超时与丢弃策略，避免无限循环挤占控制周期。
3. 对重复、旧序号、跨会话命令拒绝或按幂等规则处理，并记录计数和原因。
4. 将命令staleness从TODO转为明确的周期/时间阈值，阈值按控制模式和安全分析确定，不以delay单指标替代。
5. 将接收队列积压、丢包和周期overrun作为独立诊断量，不混用sequence delay。

### 7.3 UDP发送侧

1. `would_block`发生时必须返回false或明确的DROPPED状态，禁止返回true。
2. 记录send_attempted、kernel_accepted、would_block_dropped、hard_error计数。
3. STOP发送失败进入STOP_UNKNOWN/故障锁存；不可由bool true/回调SUCCESS推断控制器收到STOP。
4. 增加可注入socket mock，验证would_block、硬错误和正常发送的返回值传播。

## 8. 建议验收矩阵

以下为待执行测试设计，不是已执行结果：

| ID | 级别 | 测试动作 | 通过判据/证据 |
| --- | --- | --- | --- |
| RX-01 | 单元 | 同序号同payload通过真实UDP连续发送两次 | 第二帧被判重复，不刷新last_fresh_timestamp |
| RX-02 | 单元 | 序号100后发送99 | 99被判旧/乱序，不覆盖当前缓存、不更新基线 |
| RX-03 | 单元 | 65534、65535、0、1连续到达 | 全部按合法回绕接受，丢包计数正确 |
| RX-04 | 单元 | 回绕后注入65534等历史帧 | 判旧帧，不误判成下一次回绕 |
| RX-05 | 单元 | 单次read间隔内发送多帧 | 明确最新值/队列契约，丢帧数和接收间隔准确 |
| RX-06 | 单元 | 发送端点非配置robot IP | 数据报拒绝并计数，不污染状态缓存 |
| RX-07 | 单元 | socket mock返回would_block | send返回DROPPED/false，send_message不报告成功 |
| RX-08 | 单元 | socket mock返回硬错误/正常发送 | 错误与成功分别正确传播，计数准确 |
| RX-09 | 集成mock | 重复、乱序、延迟重放与合法回绕混合序列 | 接受/拒绝序列符合模序窗口，状态时间线可审计 |
| RX-10 | 集成mock | 接收突发超过每周期两帧 | 驱动记录积压/覆盖/丢弃，周期与状态新鲜度符合约定 |
| RX-11 | VAL3仿真/CS9 | readData同周期收到0/1/2/3+数据报 | 记录sioGet返回、最终解码序号、剩余队列与周期耗时 |
| RX-12 | VAL3仿真/CS9 | 旧命令、重复命令和序号回绕 | 旧/重复命令不执行；回绕合法命令不误拒 |
| RX-13 | SIL/HIL | UDP丢包、重复、乱序、来源伪造、网络拥塞 | 记录pcap、源端点、序号、缓存状态和错误传播 |
| RX-14 | CS9/FAT/SAT | 控制周期负载、UDP拥塞与STOP发送拥塞 | STOP发送丢弃能被检测并触发规定故障路径；由现场安全程序验证 |

## 9. 验证边界与结论

- 已完成：固定提交C++ UDP异步接收实现、RealtimeSocketSubscriber缓存与序号代码、VAL3 readData/getNextSequenceNumber/computeSequenceDelay/controlTask、相关协议常量和现有测试源码核对。
- 未执行：C++构建/单测、网络重复/乱序/回放/来源注入、socket发送缓冲区would_block故障注入、pcap抓包、VAL3 Studio编译下载、CS9 sioGet队列实验、SIL/HIL、FAT/SAT或实机STOP测试。
- 未证明：真实现场网络一定发生乱序/重放；非预期来源能够穿透用户网络ACL；CS9 sioGet队列在突发下的精确行为；任何机器人收到或执行了某条命令。

**结论：** C++接收端采用异步UDP单值缓存，缓存写入前不校验序号/来源，重复帧会刷新本地接收时间，乱序倒退会被当作回绕并污染比较基线；VAL3每周期最多尝试两次sioGet，第二帧可覆盖第一帧且缺少严格序号窗口。额外发现UDP发送遇到would_block时虽然明确丢弃数据报却仍返回true，使上层可能把未发送的STOP/命令报告为成功。以上为固定提交静态源码事实与风险推导，不等同于动态网络或CS9现场复现。

未修改上游仓库、未创建/应用PR；`TODO-EXT-001`未授权合并。

## 10. 下一节点

**§9.3.278 / SERVO-861：** UDP协议输入可信边界与状态数据完整性审计。重点核对发送端点绑定、VAL3/ROS网络配置、协议magic/version/type/length校验顺序、来源认证/完整性保护、重连后旧会话帧拒绝，以及ROS状态接口如何暴露通信来源/新鲜度与异常计数。
