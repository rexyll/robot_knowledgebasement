# 2026-11-10 Stäubli FakeSocket 接口契约与生命周期/线程安全设计

> 节点：§9.3.286 / SERVO-869。固定上游源码静态审查与测试替身设计；不代表 FakeSocket 已实现或测试已执行。  
> Stäubli 基线：ICube-Robotics/staubli_driver_ros2@bd658e2d266e315d2ee35f985fb352ea88306b79

## 1. 目标与边界

为后续测试实现定义仅供 gtest 使用的 FakeSocket : public Socket，覆盖当前 Socket 的全部纯虚函数，并提供可重复的 connect/send/receive/start/stop 结果脚本、手动回调投递、线程安全事件日志及 teardown 屏障。

FakeSocket 不是 UDP 协议模拟器，不模拟内核发送队列、源 endpoint、Boost.Asio error_code 或真实网络时序。它验证调用方如何处理 Socket 接口当前可表达的行为。真实 UDP adapter 仍由 loopback/独立 adapter tests 验证。

## 2. 上游 Socket 接口逐项契约

固定提交 include/staubli_robot_driver/communication/socket.hpp 定义以下纯虚接口，Fake 必须逐项 override：

| Socket 方法 | Fake 行为 | 事件记录 |
|---|---|---|
| connect(remote, remote_port, local_port) | 从 connect 脚本取下一结果；成功才置 connected=true | overload=A、地址/端口、结果 |
| connect(remote, remote_port, local, local_port) | 使用独立脚本队列，不混淆参数重载 | overload=B、地址/端口、结果 |
| disconnect() | 若 receiving，先执行 stop 语义；按 disconnect 脚本结果返回；成功后 connected=false | disconnect、stop 关联事件、结果 |
| is_connected() const | 返回受锁保护的连接状态快照 | 默认不记录高频查询 |
| send(vector<uint8_t>&) | 每次调用复制保存完整 payload，再取 send 脚本结果 | payload 长度/内容、结果、序号 |
| receive_once(timeout, data) | 按脚本返回 false 或成功数据；成功时仅复制有效字节 | timeout、返回值、字节数 |
| start_receive_thread(callback) | 仅在 connected 且未 receiving 且脚本允许时保存 callback 并置 receiving | 启动结果、状态 |
| stop_receive_thread() | 禁止新投递、清空待投递队列、等待正在执行的回调归零 | stop 请求、取消数量、join 完成 |
| is_receiving() const | 返回受锁保护的 receiving 状态快照 | 默认不记录高频查询 |

重要接口限制：
- 当前 send 只有 bool，Fake 不得伪造 NOT_SENT / LOCAL_ACCEPTED / UNKNOWN 三态能力。
- 当前异步回调只有 (vector<uint8_t>&, size_t)，没有 error_code、sender endpoint 或 generation 参数。Fake 不能通过测试 helper 偷偷扩展生产契约。
- 当前 receive_once 返回 bool；即使注释描述“0/-1”，Fake 也必须遵循真实 bool 签名。
- Socket 没有虚拟化事件循环/线程执行器接口。Fake 的确定性投递是测试辅助方法，不应暴露到生产 Socket API。

## 3. FakeSocket 测试辅助 API 草案

以下是测试支持代码的概念接口，不是上游现有 API，也不是可直接编译的完整实现：

    class FakeSocket final : public Socket {
    public:
      struct ConnectStep { bool result; };
      struct SendStep { bool result; };
      struct ReceiveStep { bool result; std::vector<uint8_t> bytes; };
      struct ThreadStep { bool result; };

      void script_connect(std::vector<ConnectStep>);
      void script_send(std::vector<SendStep>);
      void script_receive_once(std::vector<ReceiveStep>);
      void script_start_receive(std::vector<ThreadStep>);
      void script_stop_receive(std::vector<ThreadStep>);
      void script_disconnect(std::vector<ConnectStep>);

      bool deliver(std::vector<uint8_t> bytes);
      size_t pending_delivery_count() const;
      std::vector<SocketEvent> events() const;
      std::vector<std::vector<uint8_t>> sent_payloads() const;
      bool wait_until_idle(std::chrono::milliseconds timeout);
    };

### 3.1 脚本队列规则

- 每类操作独立 FIFO 队列，按调用顺序消费；不能用单一全局结果队列，否则额外状态查询/操作会改变后续故障注入含义。
- 队列耗尽时采用 fail-closed：connect/send/start/receive_once 返回 false；stop 在未运行时返回 true；disconnect 按明确状态契约处理。不得静默默认成功。
- 每次消费记录 operation、per-socket event sequence、参数、结果和脚本 step index。
- 脚本在被测动作前装载；运行中修改脚本应拒绝或明确下一次消费点。首版建议只允许 idle 状态配置脚本。
- 两个 FakeSocket 实例有独立日志与脚本；测试层可用标签区分 control/diagnostics，不用全局共享静态状态。

### 3.2 状态机

Fake 内部状态由一个 mutex 保护：
- connected_
- receiving_
- accepting_callbacks_
- active_callbacks_
- callback_
- 待投递队列（若选择 enqueue 再 dispatch）
- 各脚本队列与事件日志

合法状态约束：
1. disconnected 状态不能成功 start_receive_thread。
2. receiving 状态不能再次成功 start_receive_thread。
3. stop 后不接受新的 callback delivery。
4. disconnect 不能留下 receiving=true。
5. callback 不得在 stop 已确认完成后仍执行。
6. reconnect 必须使用新一轮 start_receive_thread；不得意外复用上次 callback。
7. 所有状态读写都经过同一同步策略，禁止测试线程直接读写内部字段。

## 4. 回调投递、取消和 join 语义

### 4.1 首选：手动确定性 dispatch

Fake 不自动创建后台线程。测试通过 deliver(bytes) 显式投递一帧：
1. 锁内检查 connected、receiving、accepting_callbacks 和 callback 存在。
2. 复制输入 bytes 到本次投递的局部 buffer，检查 bytes_transferred 不超过 buffer 长度。
3. 锁内增加 active_callbacks，并复制 callback handle。
4. 解锁后执行 callback，避免持锁调用用户代码造成死锁。
5. 使用 scope guard/RAII 在所有退出路径 decrement active_callbacks 并 notify condition_variable。
6. 返回 callback 是否被接受/执行；不要把 callback 内部业务结果误当成 UDP 发送结果。

手动 dispatch 保证默认测试不依赖 sleep，也不需要真实线程调度。它验证同步回调路径，但本身不能证明生产 Asio 线程安全。

### 4.2 stop / cancellation / join

stop_receive_thread() 的 Fake 契约：
- 在 mutex 下先将 accepting_callbacks=false、receiving=false，防止新的 delivery 开始。
- 清除尚未开始执行的 queued deliveries，并记录 canceled count。
- 等待 active_callbacks==0 后清空 callback，记录 join-complete 事件。
- 若本来未启动，返回 true（与当前 UDPSocketImpl “not running => true”的幂等行为对齐）。
- 不能在持锁状态下等待 active_callbacks，也不能持锁调用 callback。
- 当前正在执行的 callback 允许完成；stop 返回后不允许还有 callback 正在执行。
- 若 stop 失败脚本用于模拟异常，必须定义它是否仍完成取消/清理。首版建议“清理动作仍执行，返回值由脚本决定”，避免 fake 在 teardown 中留下活跃回调；同时将失败事件显式记录。

### 4.3 自身回调中调用 stop 的限制

若 callback 同步调用同一 FakeSocket 的 stop，等待 active_callbacks==0 会等待自身退出，形成自等待死锁。首版明确规定：禁止从该 FakeSocket 的 callback 调用 stop/disconnect；debug 模式可记录 callback 执行线程 ID 并检测 self-stop，返回 false/触发测试失败，而不是阻塞。生产 UDPSocketImpl 的线程 join 自身同样不应被假定安全。后续若产品需求要求 callback 自停，应先设计异步 stop 请求，不在 Fake 中单独发明语义。

### 4.4 并发竞态的确定性测试

要测试 stop 与 callback 并发：
- callback 进入时通过 promise/condition_variable 通知测试线程，并在 gate 上等待。
- 测试线程调用 stop；确认 stop 尚未完成（用独立 future 或 barrier，而不是 sleep）。
- 释放 callback gate；等待 callback 退出，再断言 stop 完成。
- stop 返回后再次 deliver 必须被拒绝；pending count=0、active count=0。
- 每个等待设置有限超时，避免失败测试永久挂起；超时只作为测试失败保护，不用于模拟业务时序。

## 5. 事件日志与断言模型

建议 SocketEvent 是值对象：
- uint64_t sequence：单个 FakeSocket 单调递增；
- Operation：ConnectA/ConnectB/Disconnect/Send/ReceiveOnce/Start/Stop/Deliver/CallbackBegin/CallbackEnd；
- std::thread::id thread_id；
- bool result（仅适用事件）；
- size_t payload_size；
- 可选 payload copy（只在测试显式开启，默认不重复保存大数据）；
- size_t script_step；
- std::string label（control/diagnostics）。

日志追加必须在 mutex 下完成；events() 返回拷贝快照，不能返回内部 vector 引用。不要在测试中依赖两个不同 FakeSocket 的全局 event sequence 严格先后，除非测试用共享 trace recorder 并显式同步；两个独立 socket 的并发操作天然没有可推断的全序。

推荐断言：
- 单 socket：调用顺序、脚本 step、payload 完整相等、状态转换、stop/join 屏障。
- 双 socket：分别断言每个通道事件，不把跨通道线程调度先后当作协议保证。
- 故障回滚：断言 control/diagnostics 各自 disconnect 调用与结果，不仅检查最终 connected bool。
- 禁止使用日志输出文本作为唯一断言；使用结构化事件字段。

## 6. FakeSocket 与生产 UDPSocket 行为对应

| 主题 | Fake 可验证 | 必须由真实 UDP/其他层验证 |
|---|---|---|
| connect 失败/成功 | 调用方错误传播、状态转换 | DNS、bind、端口占用、真实连接配置 |
| send false | 上层不把失败当成功 | would_block 当前实现仍返回 true 的缺陷与内核行为 |
| receive_once true/false | 超时/成功分支处理 | 实际 datagram、网络超时与错误码 |
| 回调数据投递 | Subscriber 解析与状态更新 | Asio 缓冲区、socket 取消及内核事件顺序 |
| stop/join | 调用方 teardown 不越过回调完成屏障 | 真实 Asio handler cancellation 与线程退出 |
| reconnect | 上层重新启动接收路径 | 真实端口重绑定、迟到网络包、sender endpoint |
| callback generation | 只能测调用方显式实现的 generation seam | 当前生产 callback 没有 generation 字段，不能声称已验证 stale-generation 防护 |

固定上游 UDPSocketImpl::handle_data_received() 当前在 error 非空时记录日志，但仍继续调用 user callback，然后在 receiving 时重新安排下一次 receive。FakeSocket 的接口无法传递 error_code，因此该错误路径需单独在后续 adapter seam 设计；不能用 deliver({}) 假装等价于 socket error。

## 7. 最小测试用例清单

所有用例目前均为设计状态、NOT_RUN。

| ID | 场景 | 关键断言 |
|---|---|---|
| FS-01 | 两种 connect overload 成功 | 参数与 overload 记录准确，connected=true |
| FS-02 | connect scripted false | 返回 false，connected=false |
| FS-03 | connect 队列耗尽 | fail-closed，不意外成功 |
| FS-04 | send true/false 序列 | 每次 payload 均被记录，结果按 FIFO 消费 |
| FS-05 | send 队列耗尽 | 返回 false，仍记录 attempted payload |
| FS-06 | receive_once 成功 | 输出 buffer 精确等于脚本 bytes |
| FS-07 | receive_once false | 输出不被伪造为成功数据 |
| FS-08 | start 未连接 | 返回 false，receiving=false |
| FS-09 | 重复 start | 第二次拒绝，不覆盖原 callback |
| FS-10 | 手动 deliver | callback 收到独立、长度正确的数据副本 |
| FS-11 | stop 未启动 | 幂等返回 true |
| FS-12 | stop 取消待投递 | pending queue 清空，后续 delivery 被拒绝 |
| FS-13 | stop 等待活动 callback | callback gate 释放前 stop 不完成，释放后 join 完成 |
| FS-14 | callback 退出抛异常 | active_callbacks 通过 RAII 归零，异常不污染下一测试 |
| FS-15 | disconnect 时 receiving | 先停止并等待 callback，再断开；状态无残留 |
| FS-16 | stop 之后 reconnect/restart | 新 callback 生效，旧 callback 不再调用 |
| FS-17 | 两个 Fake 独立 | scripts/events/payload 不串扰 |
| FS-18 | 并发 send 与事件快照 | 无数据竞争，快照结构有效 |
| FS-19 | stop 与 deliver 竞态 | 要么 delivery 被拒绝，要么已进入的 callback 被 stop 等待完成 |
| FS-20 | self-stop 防护 | 不发生自等待死锁，按明确策略失败 |
| FS-21 | event log snapshot | 返回副本，外部修改不影响内部日志 |
| FS-22 | 超长 bytes_transferred | deliver 拒绝无效长度，不越界访问 |

## 8. 推荐测试文件与实施顺序

建议测试支持文件：
- test/test_helpers/fake_socket.hpp：接口、脚本步骤、事件类型、状态快照声明。
- test/test_helpers/fake_socket.cpp：同步、状态机、事件日志和回调屏障实现（若只被单个 target 使用，可先 header-only）。
- test/unit_tests/communication/test_fake_socket.cpp：FS-01至FS-22，验证 Fake 自身契约。
- test/unit_tests/test_robot_driver_fault_injection.cpp：只验证 RobotDriver 与 Fake 的组合，不重复测试 Fake 内部实现。
- CMake：首轮复用现有 add_unit_test(test_fake_socket ...) 和 add_unit_test(test_robot_driver_fault_injection ...)。

实施顺序：
1. 先实现并单独验证 FakeSocket 状态机与线程屏障。
2. 先接入 Subscriber 测试，验证 callback teardown 和数据副本。
3. 再接入 RobotDriver 双 Socket 注入，逐项测试 connect/send/diagnostics 故障组合。
4. 再补 loopback UDP adapter tests，检查 Fake 无法模拟的真实网络行为。
5. 最后进入真实 ros2_control integration、TSan/ASan 与系统级验证；这些不得被 FakeSocket 测试替代。

## 9. 风险控制与验收边界

- Fake 默认不启动后台线程；手动 dispatch 的确定性优势与生产异步线程的并发覆盖边界必须同时写入测试报告。
- stop 语义以“禁止新回调、取消排队事件、等待活动回调完成”为契约；不得只设置 receiving=false 就声称 join 完成。
- callback 不持锁执行；所有 active callback 计数必须通过 RAII 归零。
- 所有等待有超时保护，所有脚本 FIFO 有明确耗尽行为。
- 不能把 Fake 的 send(true) 解读为远端 CS9 已收到，更不能解读为机器人已停止。
- 不能用 Fake 验证 sender endpoint、socket error_code、真实 UDP 丢包、内核缓冲区和 Asio cancellation。
- FakeSocket 仅是 test helper，不安装、不导出、不改变产品 ABI。
- 不修改固定 Stäubli 上游或 ros2_control 上游；未获授权不应用任何 PR。

## 10. 当前验证状态与下一节点

本轮仅静态读取固定 commit 的 Socket/UDPSocket 接口、UDP Asio 实现及现有 gtest 结构，定义 FakeSocket 契约。

- FS-01至FS-22：全部 NOT_RUN。
- FakeSocket、事件日志、callback gate、ManualClock：均未实现。
- 未运行构建、gtest、TSan/ASan、ROS 2 Control 集成、SIL/HIL、VAL3/CS9、FAT/SAT 或实机测试。
- 未修改 Stäubli/ros2_control 上游，未应用或合并 PR。
- TODO-EXT-001 仍未授权；工程级验收未通过。

**下一节点 §9.3.287 / SERVO-870：FakeSocket 状态机与事件日志的实现级伪代码审查，并将 FS-01 至 FS-22 细化为 Arrange/Act/Assert 测试表。** 仍先在知识库中完成实现规格，不擅自改动 Stäubli 上游。
