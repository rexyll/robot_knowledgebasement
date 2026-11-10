# 2026-11-10 Stäubli FakeSocket 状态机伪代码与 AAA 测试矩阵

> 节点：§9.3.287 / SERVO-870。实现级测试规格审查，不代表代码已实现或测试已运行。  
> 固定 Stäubli 基线：`ICube-Robotics/staubli_driver_ros2@bd658e2d266e315d2ee35f985fb352ea88306b79`  
> 固定 ros2_control 参考：`ros-controls/ros2_control@c6ef5a24e0cd21463edb99bded552a96f914b716`

## 1. 本轮结论

本轮将 SERVO-869 的概念契约收敛为可直接指导测试 helper 编码的状态、线性化点、锁规则、异常处理和 22 项 Arrange/Act/Assert（AAA）用例。建议 FakeSocket 只作为 test-only helper，首版采用手动 dispatch，不创建后台线程；如果后续必须验证真正并发，则使用显式 gate/thread test driver，而不是把 Fake 的默认行为改成非确定性异步调度。

核心设计决策：

1. 一个 mutex 保护 Fake 的连接/接收状态、callback、活动 callback 计数、脚本队列、pending 队列和事件日志；condition_variable 只用于等待活动 callback 归零。
2. callback 在锁外执行；进入 callback 前在锁内增加 active count 并取得 callback 副本，退出时通过 RAII 减少计数并 notify。
3. stop 的线性化点是锁内将 accepting_callbacks 和 receiving 同时设为 false。在线性化点之前已登记的 callback 可以完成；之后的 deliver 必须失败。stop 返回前必须等到 active count 为零。
4. stop 的脚本失败只影响返回值，不跳过清理。即使返回 false，也必须关闭投递、取消 pending、等待活动 callback、清除 callback，避免 teardown 泄漏。
5. callback 异常不能吞掉。RAII 先恢复 active count，再让异常传播给调用者/测试框架；测试需显式验证下一次 stop 不会永久等待。
6. 禁止 callback 对同一 FakeSocket 同步调用 stop/disconnect，防止等待自身退出。首版以可检测的失败返回/断言诊断实现，不允许死锁。
7. 事件序号只保证单 FakeSocket 内部递增；control 与 diagnostics 两个 Fake 之间不宣称全序。
8. Fake 测试只验证 Fake 自身契约或调用方与 Socket 抽象的交互，不覆盖真实 UDP、Asio cancellation、error_code、sender endpoint、内核队列或 CS9 行为。

## 2. 状态模型与转换

### 2.1 状态变量

建议以状态变量组合表达，而不是使用单一枚举掩盖正在执行的 callback：

- connection_state：DISCONNECTED / CONNECTED
- receive_state：STOPPED / ACCEPTING / STOPPING
- accepting_callbacks：bool
- active_callbacks：非负计数
- callback：可空 callback handle
- pending_deliveries：手动投递队列；首版可选择不排队，若保留队列则只允许在锁内入队/取消
- event_sequence：单实例 uint64 单调递增
- 每个操作各自独立的 FIFO script queue

### 2.2 合法状态转换

```text
DISCONNECTED + connect(true)  -> CONNECTED
DISCONNECTED + connect(false) -> DISCONNECTED
CONNECTED + start(true)       -> ACCEPTING
CONNECTED + start(false)      -> STOPPED
ACCEPTING + stop(request)     -> STOPPING (linearization point)
STOPPING + active_callbacks=0 -> STOPPED
CONNECTED + disconnect       -> STOPPING -> DISCONNECTED
STOPPED + reconnect           -> CONNECTED -> ACCEPTING (new callback)
```

不变量：

- DISCONNECTED 不得处于 ACCEPTING。
- STOPPING/STOPPED 不接受新 callback 登记。
- active_callbacks 只能在持锁区递增/递减，且永不为负。
- callback 执行期间不持有 Fake mutex。
- stop 返回时 active_callbacks 必须为 0、callback 为空、pending 队列为空。
- connect 成功不能隐式恢复旧 callback；每轮 start 必须显式提供新 callback。
- disconnect 即使其结果脚本返回失败，也必须先完成接收线程/回调清理；连接状态如何反映 disconnect 失败需与 Socket 实际语义对齐并通过单测固定，建议保留 CONNECTED 以反映底层断开未获确认，但接收必须已停止。

## 3. 实现级伪代码

以下是伪代码，刻意省略具体 C++ 类型、异常类型和 ABI 细节；不能直接当作可编译补丁。

### 3.1 事件追加与脚本消费

```text
record_event_locked(operation, fields):
    assert mutex is held
    event.sequence = ++event_sequence
    event.operation = operation
    event.thread_id = current_thread_id
    event.fields = value_copy(fields)
    events.push_back(event)

consume_script_locked(queue, fail_closed_value):
    assert mutex is held
    if queue.empty():
        return fail_closed_value
    step = queue.front()
    queue.pop_front()
    return step
```

脚本只在 idle/configuration 阶段装载；若运行中修改，必须拒绝或明确记录配置边界。每种操作使用独立 FIFO，避免某类调用意外消费另一类故障步骤。事件记录本身不得触发 callback 或外部代码。

### 3.2 connect 两种重载

```text
connect_A(remote, remote_port, local_port):
    lock(mutex)
    if receive_state != STOPPED or active_callbacks != 0:
        record rejected connect_A
        return false
    result = consume(connect_A_script, false)
    record connect_A parameters + result
    if result:
        connection_state = CONNECTED
    return result

connect_B(remote, remote_port, local, local_port):
    same guard and independent connect_B_script
    record overload=B and every endpoint/port argument
    update connection_state only on success
```

两种 overload 必须独立记录与消费脚本；不允许把地址参数只记录为模糊字符串而丢失 overload/端口信息。重复 connect 的语义须明确：首版若已 CONNECTED 则拒绝，不暗中覆盖既有连接。

### 3.3 send

```text
send(payload):
    payload_copy = copy(payload)       // caller buffer 不被持锁访问
    lock(mutex)
    result = consume(send_script, false)
    append attempted payload_copy to sent_attempts
    record send(size, payload digest or opt-in bytes, result, script_step)
    return result
```

这里的 sent_attempts 表示“调用尝试”，不是网络发送成功证据。若需要保存完整 payload，应限制测试数据规模或显式开启，避免日志无界增长。Fake 返回 true 仅表示脚本化 Socket 接口返回 true。

### 3.4 receive_once

```text
receive_once(timeout, out):
    lock(mutex)
    step = consume(receive_script, {false, empty})
    record timeout, result, byte_count
    if !step.result:
        return false                 // 不改写 out 为伪造成功数据
    local_bytes = step.bytes
    unlock(mutex)
    copy exactly local_bytes into out according to documented buffer contract
    return true
```

实际实现必须先确认上游 Socket::receive_once 的 out 参数容量/长度约定；不得从伪代码推断可任意扩容。若 API 没有显式容量，测试 helper 需遵循现有调用方预分配约定并在越界时安全拒绝。

### 3.5 start_receive_thread

```text
start(callback):
    if callback is empty: return false
    lock(mutex)
    if connection_state != CONNECTED or receive_state != STOPPED
       or active_callbacks != 0:
        record start rejected
        return false
    step = consume(start_script, false)
    record start result
    if !step.result:
        return false
    callback_ = callback
    accepting_callbacks = true
    receive_state = ACCEPTING
    return true
```

start 成功的线性化点是锁内 callback_ 安装且 accepting_callbacks=true 的状态提交。start 失败不留下 callback 或 receiving 状态。

### 3.6 deliver：手动 callback dispatch

```text
deliver(bytes, bytes_transferred):
    if bytes_transferred > bytes.size():
        record invalid length under lock
        return false

    lock(mutex)
    if connection_state != CONNECTED
       or receive_state != ACCEPTING
       or !accepting_callbacks
       or callback_ is empty:
        record delivery rejected
        return false

    local_callback = callback_       // copy handle under lock
    local_buffer = copy(bytes[0:bytes_transferred])
    ++active_callbacks               // callback admission linearization point
    record CallbackBegin
    unlock(mutex)

    RAII guard:
        lock(mutex)
        --active_callbacks
        record CallbackEnd
        if active_callbacks == 0: notify_all()
        unlock(mutex)

    local_callback(local_buffer, bytes_transferred)
    return true
```

callback 抛异常时，RAII guard 必须先析构；异常再传播给测试调用栈。不得 catch 后静默返回 true，也不得在 RAII 之外手动减计数导致 double decrement。若要在 Fake 内记录异常，可在 catch 中记录后 rethrow，但 guard 仍须保证所有路径清理。

### 3.7 stop_receive_thread

```text
stop():
    if current thread is executing this socket's callback:
        record self-stop rejected
        return false

    lock(mutex)
    receive_state = STOPPING
    accepting_callbacks = false    // stop linearization point
    canceled = pending_deliveries.size()
    pending_deliveries.clear()
    record StopRequested(canceled)
    stop_step = consume(stop_script, default_success)
    unlock(mutex)

    lock(mutex)
    condition.wait(lock, active_callbacks == 0)
    callback_ = empty
    receive_state = STOPPED
    record StopJoined(result=stop_step.result)
    unlock(mutex)

    return stop_step.result
```

清理不受 stop_step.result 控制：脚本返回 false 仍必须完成 wait、清空 callback 与状态收敛。若实现包含 pending queue，deliver 与 stop 的竞态由同一 mutex 决定：deliver 先登记 active count 则 stop 等待它；stop 先关闭 accepting 则 deliver 被拒绝。不存在“stop 已返回但 callback 后启动”的第三种结果。

### 3.8 disconnect

```text
disconnect():
    if called from own callback: reject self-disconnect
    stop_result = stop()             // always performs cleanup
    lock(mutex)
    disconnect_step = consume(disconnect_script, fail_closed)
    if disconnect_step.result:
        connection_state = DISCONNECTED
    record Disconnect(stop_result, disconnect_step.result)
    unlock(mutex)
    return disconnect_step.result
```

即使 disconnect 脚本失败，receive callback 也已停止。返回值只反映接口 disconnect 结果；测试分别断言 cleanup 与 connection_state，不能仅凭返回值推断底层网络状态。

### 3.9 callback guard / wait predicate

```text
CallbackGuard(socket):
    destructor:
        lock(socket.mutex)
        assert socket.active_callbacks > 0
        --socket.active_callbacks
        if socket.active_callbacks == 0:
            socket.cv.notify_all()

wait_for_callbacks():
    unique_lock(mutex)
    cv.wait(lock, active_callbacks == 0)
```

不得在 condition_variable wait 时持有另一个会被 callback 访问的测试锁。所有并发测试使用 promise/future、barrier 或 condition_variable 建立先后关系；sleep 不能作为竞态同步证据。

## 4. stop 与 deliver 的线性化/竞态矩阵

| 交错 | 必须发生的结果 | 断言证据 |
|---|---|---|
| deliver 先取得锁并登记 active，stop 后取得锁 | callback 可运行；stop 等到 callback 退出 | CallbackBegin < StopJoined；stop future 在 gate 释放前未完成 |
| stop 先关闭 accepting，deliver 后取得锁 | deliver 拒绝，不调用 callback | StopRequested 之后无新的 CallbackBegin |
| callback 已执行，stop 开始 | 不取消正在执行的 callback；等待其退出 | active count 最终归零，stop 返回后 callback 已退出 |
| stop 完成后 deliver | 拒绝 | callback 调用次数不变 |
| callback 抛异常 | active count 归零；异常传播 | 调用端捕获异常；随后 stop 在限定时间内完成 |
| stop 脚本返回 false | 清理仍完成，返回 false | callback/pending 清空；active=0；StopJoined.result=false |
| callback 内 self-stop | 明确拒绝，不能等待自身 | 返回 false/诊断事件；测试在超时内结束 |

## 5. 事件日志数据结构与快照语义

建议事件字段：

- sequence：每个 FakeSocket 独立的 uint64_t 递增序号。
- operation：ConnectA、ConnectB、Disconnect、Send、ReceiveOnce、Start、StopRequested、DeliveryRejected、CallbackBegin、CallbackEnd、StopJoined。
- thread_id：执行该操作的线程 ID。
- result：仅对具有返回结果的操作填写。
- script_step：本次消费的脚本步骤编号；无脚本消费则为空。
- payload_size 与可选 payload bytes/digest。
- endpoint/timeout/bytes_transferred 等适用参数。
- label：control 或 diagnostics，仅用于可读诊断。

events() 必须在锁内复制 vector，再返回值快照；外部清空/修改快照不得影响内部日志。若两个 Fake 需要组合 trace，必须由测试显式提供共享 recorder 并通过同步建立 happens-before；不能比较两个各自 sequence 值来推断跨 socket 先后。

## 6. FS-01 至 FS-22：Arrange / Act / Assert

所有条目当前均为设计规格，状态统一为 NOT_RUN。以下每项均需将断言失败输出与测试 run-id、构建配置、commit 和日志归档关联。

| ID | Arrange（准备） | Act（执行） | Assert（断言与失败证据） |
|---|---|---|---|
| FS-01 | 创建 Fake；分别装载 connect-A/B 成功步骤及不同端口参数 | 依次调用两种 connect overload | 两次均 true；事件分别标记 A/B 且参数无串位；任一参数/overload 错误即 FAIL |
| FS-02 | DISCONNECTED；connect-A 脚本 false | 调用 connect-A | 返回 false、仍 DISCONNECTED；不得出现成功状态事件 |
| FS-03 | connect 队列为空 | 调用 connect | fail-closed 返回 false；记录 script-exhausted，不得默认成功 |
| FS-04 | send 队列设为 true,false；准备两个不同 payload | 连续 send 两次 | 返回序列 true,false；attempt payload 与调用顺序逐字节匹配 |
| FS-05 | send 队列为空；准备 payload | 调用 send | 返回 false；attempt 仍记录 payload/长度，避免把未调用与失败调用混淆 |
| FS-06 | 配置 receive 成功与固定 bytes；按上游 buffer 约定准备输出区 | 调用 receive_once(timeout) | true；输出有效长度和内容精确匹配；不得读写越界 |
| FS-07 | 配置 receive false；输出区预填 sentinel | 调用 receive_once | false；输出遵循约定且不得伪造脚本数据；失败时是否保持原 buffer 由实现契约固定 |
| FS-08 | 保持 DISCONNECTED；设置 callback | 调用 start_receive_thread | 返回 false；receiving=false、callback 未安装；deliver 被拒绝 |
| FS-09 | CONNECTED；第一次 start 成功，第二次配置成功步骤 | 第二次 start 使用不同 callback | 第二次拒绝；原 callback 不被覆盖；仅第一次 callback 可被 deliver 调用 |
| FS-10 | CONNECTED + ACCEPTING；注册 callback 捕获 bytes 和长度 | deliver 一份带前后哨兵的 buffer | callback 仅收到指定切片的独立副本；调用次数=1；原始 buffer 后续改写不影响已捕获副本 |
| FS-11 | 从未 start 或已 stop；stop 默认成功 | 调用 stop | true；状态 STOPPED；active=0；重复调用仍幂等 |
| FS-12 | ACCEPTING；若有 pending queue 则先登记待处理投递 | 调用 stop，再调用 deliver | pending 清空；后续 deliver false；不再出现 CallbackBegin |
| FS-13 | callback 进入后在 gate 阻塞；创建 stop future | 启动 stop，确认 stop 未完成，再释放 gate | gate 释放前 stop 不完成；释放后 stop 完成；CallbackEnd 先于 StopJoined |
| FS-14 | ACCEPTING；callback 抛出测试异常 | 调用 deliver 并在测试端捕获异常，随后调用 stop | 异常可见且未吞掉；active=0；stop 在限定时间内完成；无残留 callback |
| FS-15 | CONNECTED + ACCEPTING；callback gate 可控制；disconnect 脚本成功 | callback 进入后调用 disconnect，再释放 gate | disconnect 等待 callback；返回后 receiving=false、active=0、CONNECTED=false |
| FS-16 | 完成一轮 start/stop；准备新 callback | reconnect 后 start 新 callback，再 deliver | 只调用新 callback；旧 callback 不再触发；事件可区分两轮生命周期 |
| FS-17 | 创建 control 与 diagnostics 两个 Fake，装载不同脚本 | 交错调用 connect/send/deliver | 各自脚本、payload、event sequence 独立；无跨实例状态污染 |
| FS-18 | CONNECTED；多线程并发 send；另线程反复读取 events() 快照 | 并发执行 send 与快照读取 | 无崩溃/容器失效；每份快照内部序号严格递增；该用例需 TSan 才能提供数据竞争证据 |
| FS-19 | callback gate 控制；安排 deliver 与 stop 两种线程交错 | 通过 barrier 重复执行两种锁顺序 | 只允许“先登记则 stop 等待”或“stop 先关闭则 deliver 拒绝”；不允许 stop 返回后 callback 新启动 |
| FS-20 | callback 中尝试对同一 Fake 调用 stop/disconnect | deliver callback | self-stop/self-disconnect 按契约拒绝并记录诊断；测试有限时间结束，无死锁 |
| FS-21 | 产生至少两条事件，获取 events() 快照 | 修改/清空返回的快照，再次读取 events() | 内部日志仍完整；第二次快照内容不受外部修改影响 |
| FS-22 | CONNECTED + ACCEPTING；准备 bytes 长度 N | deliver(bytes, N+1) | 返回 false；callback 不调用；记录 invalid-length；ASan/边界检查无越界 |

### 6.1 测试层级标记

- Fake 自身契约：FS-01 至 FS-22。FS-18/19 还需 TSan 才能形成动态并发证据；普通 gtest 通过不足以证明无数据竞争。
- 与生产调用方组合：上述 FS 用例本身不验证 RobotDriver/Subscriber 的业务行为。后续必须另设调用方测试：RobotDriver connect 回滚、send false 传播、双 socket 隔离；Subscriber callback 投递、解析失败、freshness 时钟与析构屏障。
- 真实 adapter：loopback UDP 测试覆盖真实 datagram、socket 错误和 endpoint；仍不能替代目标 CS9 网络行为。
- 系统集成：ResourceManager/ControllerManager 生命周期、SIL/HIL、VAL3/CS9、FAT/SAT 与实机属于独立验收层。

## 7. 失败证据与运行记录要求

每个用例至少记录：

1. 测试 ID、测试名称、结果 PASS/FAIL/NOT_RUN/SKIPPED。
2. 仓库 commit、上游固定 commit、ROS 发行版、编译器、构建类型和依赖版本。
3. 测试 run-id、开始/结束时间、命令行和退出码。
4. 失败时保存 gtest 输出、结构化 Fake 事件快照、线程栈/超时诊断；并发失败另存 TSan 报告。
5. 不得只保存“测试通过”文字；证据必须能关联到实际运行配置与源码版本。
6. 未执行的测试保持 NOT_RUN；设计审查、代码审查、构建成功与测试通过是不同证据类型。

## 8. 设计缺口与需在实现前冻结的决策

- receive_once 的输出 buffer 容量/长度语义须按固定 Socket 头文件和所有调用点确认；不能按示意伪代码擅自扩容。
- disconnect 脚本失败后 connection_state 如何反映需明确。建议接收已停止、callback 已清空，但保留连接状态以表示断开未获确认。
- stop 脚本失败仍完成清理，是 test helper 的 teardown 保证；它不代表真实 Asio stop/join 在所有错误条件下均能成功。
- callback 内 self-stop 的检测方式依赖线程局部执行标记或 thread ID；首版需避免把诊断锁与 Fake mutex 反向嵌套。
- 若首版不实现 pending queue，则 FS-12 的“取消待投递”改为验证尚未 admission 的 delivery 在 stop 后被拒绝；不得把不存在的队列写成已覆盖。
- 手动 dispatch 不能证明真实后台线程的调度/取消行为。需另行通过真实 adapter tests、TSan 和目标环境验证。
- 当前 Socket bool send 无法表达 NOT_SENT/LOCAL_ACCEPTED/UNKNOWN；Fake 不得在 helper 层私自扩展并声称生产代码已获得三态契约。

## 9. 当前状态与下一节点

- FS-01 至 FS-22：全部 NOT_RUN；本报告是 AAA 规格，不是测试结果。
- FakeSocket、RAII guard、事件日志、ManualClock、RobotDriver 注入构造：均未实现。
- 未运行 CMake/build、gtest、TSan/ASan、ROS 2 Control 集成、loopback 新测试、SIL/HIL、VAL3/CS9、FAT/SAT 或实机测试。
- 未修改 Stäubli 或 ros2_control 上游；未应用/合并 PR；`TODO-EXT-001`仍未授权。
- 工程级验收未通过。

**下一节点 §9.3.288 / SERVO-871：将 FS-01 至 FS-22 与 RobotDriver / RealTimeSocketSubscriber 现有生产调用点逐项映射，设计真实 fixture 生命周期、双 Socket 注入和析构/回调屏障集成测试。**
