# Stäubli RobotDriver connect/disconnect 回滚路径故障注入矩阵

- 审查节点：§9.3.289 / SERVO-872
- 日期：2026-11-10
- 上游基线：ICube-Robotics/staubli_driver_ros2@bd658e2d266e315d2ee35f985fb352ea88306b79
- 范围：RobotDriver 双 Socket connect、部分初始化、失败回滚、disconnect、析构与 SD-07/SD-08/SD-10
- 方法：固定提交源码静态审查；不代表构建、测试或运行时行为已验证

## 1. 结论摘要

本轮确认当前 connect 失败处理不是统一事务式回滚。失败分支存在三类不同语义：

1. **直接返回且不清理**：空 IP、control socket 未初始化、control socket connect 返回 false。
2. **调用 disconnect 但忽略清理结果**：diagnostics socket 未初始化/连接失败、接口 readiness 失败、首帧 timeout、protocol version 不匹配。
3. **异常向外传播且没有 catch/rollback**：control interface 或 diagnostics subscriber 的构造抛出异常（例如 Subscriber 的 start_receive_thread 返回 false 时构造函数抛 runtime_error；make_shared 分配失败也会抛异常）。

因此，当前 SD-07 的“失败一律 connect 返回 false”断言不成立：Subscriber 初始化失败应按当前源码预期捕获异常；FakeSocket connect 返回 false 也不能假设 socket 必然保持 disconnected，Socket 抽象没有规定失败后的状态回滚契约。

另一个确定性问题是 connect 等待循环不在首帧成功时提前退出：循环条件只由连接开始时间和 timeout 决定，每轮读取后固定 sleep 500 ms。即使首帧很早到达，也会继续等待到 timeout 窗口结束；最后一次 read 的 freshness 结果决定连接是否成功。测试需覆盖“首帧早到但 connect 仍持续等待”以及 timeout 边界，不应把它误写成首帧到达即返回。

## 2. 固定源码证据

| 文件 | 固定提交 blob SHA | 本轮核对点 |
|---|---|---|
| staubli_robot_driver/src/robot_driver.cpp | ede48a314856a455df9d8434f354aaf9fbc47bff | connect 分支、disconnect 顺序、空析构、500ms 等待 |
| staubli_robot_driver/include/staubli_robot_driver/robot_driver.hpp | 62c87a6741aa082db4599bb2c048aec0fcd7a464 | 双 socket / interface 成员声明顺序 |
| staubli_robot_driver/src/real_time_socket_subscriber.cpp | e2cd8fc50b2b13d9e31b2c024e90f9da76107622 | 构造失败抛异常、callback 注册、析构 stop |
| staubli_robot_driver/include/staubli_robot_driver/real_time_socket_subscriber.hpp | 330839cb25e53fe961541f29f634722bec4a47c4 | Subscriber API 与成员 |
| staubli_robot_driver/src/real_time_socket_interface.cpp | eda0a830cfe0118e07bc3423ad0f455bd50d610c | Interface 构造委托 Subscriber、析构、send |
| staubli_robot_driver/include/staubli_robot_driver/real_time_socket_interface.hpp | e4d4650f59d2eb95133f5e948431ebe2073a6667 | Interface 继承关系 |
| staubli_robot_driver/include/staubli_robot_driver/communication/socket.hpp | 230af198337e5d047b29b2bbf6354a698fb3a390 | Socket bool API；失败后状态无契约 |

## 3. connect 阶段与双 Socket 状态转换矩阵

状态缩写：
- C：control socket；D：diagnostics socket。
- Conn：is_connected；Recv：is_receiving。
- CI：control interface；DS：diagnostics subscriber。
- “可能部分成功”表示 Socket 抽象没有规定 connect/start 返回 false 时实现内部必须回到初始状态；Fake 应显式脚本化并断言状态，不得自行假设。

| 阶段 / 失败点 | C / D 可能状态 | CI / DS | 当前回滚动作 | 返回/异常 | 风险与测试断言 |
|---|---|---|---|---|---|
| 保存 config 后 robot_ip 为空 | C、D 保持进入前状态 | 保持进入前状态 | 无 | false | 配置已覆盖为新 config；不执行清理。断言无 connect/stop/disconnect 事件 |
| 旧会话：C connected | 进入 disconnect | 见 disconnect 矩阵 | 调用 disconnect；若返回 false，connect 立即 false | false | 清理失败时不继续新连接；disconnect 已 reset interface/data，但 socket 可能仍 connected |
| 旧会话：C 未连接、D connected | 进入 disconnect | 见 disconnect 矩阵 | 第二个旧会话检查调用 disconnect | false 若清理失败 | 单独覆盖 diagnostics-only 旧会话 |
| C socket 为 null | C 不存在；D 可能保留旧状态 | 不保证清理 | 无 | false | D 未连接时不会触发前置旧会话清理；不能假设统一 rollback |
| C connect 返回 false | C 状态由 adapter 决定；D 不调用 connect | CI/DS 不创建 | **无** | false | 关键缺口：若 connect false 后 C 仍 connected/receiving，函数直接返回；Fake 需测试 false + residual-connected 状态 |
| C connect 成功，创建 CI 成功 | C connected，Subscriber start 成功时 receiving；D 尚未连接 | CI 存在且 ready；DS 不存在 | 继续 | — | CI 构造立即注册 callback；其 callback 捕获 this |
| CI 构造失败（start_receive_thread false） | C connected；C receiving 状态取决于 Socket 对 false 的实际副作用 | CI 构造抛异常，不完成成员赋值；DS 不存在 | **无 catch、无 disconnect** | runtime_error 向外传播 | 资源回滚缺口；必须断言异常和残余 C 状态；若 start 返回 false 但留下 callback，需独立验证 |
| CI make_shared 分配失败 | C connected | CI 不存在 | 无 catch/rollback | bad_alloc 等异常 | 分配异常不是普通 null 返回；源码中的 if (!control_interface_) 对标准 make_shared 正常语义不可达 |
| D socket 为 null | C connected；D 不存在 | CI 存在 | 调用 disconnect | false（清理返回值被忽略） | CI reset 先 stop，再断开 C；D 无对象 |
| D connect 返回 false | C connected；D 失败后状态由 adapter 决定 | CI 存在；DS 不存在 | 调用 disconnect | false（清理结果被忽略） | C 应 stop/disconnect；若 D connect false 后仍 connected，则 disconnect 会尝试处理；若 adapter 报 disconnected 但仍有接收资源，driver 看不到 |
| D connect 成功，创建 DS 成功 | C、D connected；两侧接收线程启动 | CI、DS ready | 继续 | — | DS 构造立即启动接收 callback |
| DS 构造失败（start_receive_thread false） | C connected；D connected；D receiving 状态由 start 失败副作用决定 | CI 已存在；DS 构造抛异常 | **无 catch、无 disconnect** | runtime_error 向外传播 | CI callback 可能持续运行，C/D socket 保持连接；需覆盖半初始化泄漏 |
| DS make_shared 分配失败 | C、D connected | CI 存在；DS 不存在 | 无 catch/rollback | bad_alloc 等异常 | make_shared 后 null 检查不可作为异常处理 |
| CI/DS readiness 检查失败 | 两 socket 可能 connected | 对应 interface/subscriber 不 ready | 调用 disconnect | false | disconnect 清理结果忽略；ready 通常由 socket connected && receiving 决定 |
| 首帧 timeout | C、D connected | CI、DS 已创建；诊断 readiness 被硬编码 true | 调用 disconnect | false | 只有 RobotState 真正被读取、有效且未 stale 才能通过；诊断首帧不是门禁 |
| protocol version mismatch | C、D connected | CI、DS 已创建 | 调用 disconnect | false | protocol mismatch 使用 current_robot_state_；清理失败不改变 false 返回 |
| firmware/compatibility 区段 | C、D connected | CI、DS 已创建 | 当前没有有效的型号/VAL3 拒绝门禁；仅日志 firmware 版本 | 继续成功 | 不能把该段描述为已实现完整兼容性检查 |
| 成功返回 | C、D connected | CI、DS ready | 无 | true | diag 首帧未验证；诊断缓存仍可能是 reset 后默认内容 |

### 3.1 两个特别重要的异常语义

- Subscriber 构造函数在 init_communication 返回 false 时直接 throw runtime_error。对象未完整构造，因此其析构函数不会执行；RobotDriver::connect 没有 try/catch，之前已经创建的 CI 也不会由 connect 自动 reset。
- make_shared 失败通过异常表达，不会返回空 shared_ptr。因此源码中 interface/subscriber 创建后的 null 检查并不是正常分配失败处理路径，不能作为 rollback 证据。

## 4. disconnect 清理矩阵

当前 disconnect 顺序固定为：

1. reset control_interface_。其派生析构为空，基类 Subscriber 析构无条件调用 control socket 的 stop_receive_thread()，忽略 bool 结果。
2. reset diagnostics_subscriber_；其 Subscriber 析构同样无条件 stop，忽略 bool 结果。
3. 若 C connected：若 C receiving，再调用 stop；stop false 只 warning，仍继续调用 disconnect。
4. 若 D connected：若 D receiving，再调用 stop；stop false 只 warning，仍继续调用 disconnect。
5. reset_data() 无条件执行。
6. 返回 control_disconnect_result && diagnostics_disconnect_result。

| 场景 | Subscriber 析构 stop | driver 显式 stop | socket disconnect | 返回值语义 |
|---|---|---|---|---|
| 两通道均 connected + receiving | C、D 各一次 | C、D 各再一次（若析构 stop 后仍报告 receiving） | C、D 各一次 | 两个 disconnect bool 的 AND |
| interface 析构 stop 后 receiving=false | C、D 各一次 | 不再 stop | C、D 各 disconnect | stop 析构结果被忽略 |
| stop 返回 false 但 receiving 仍 true | 析构 stop 一次；忽略 false | 再 stop 一次；warning | 仍尝试 disconnect | stop 失败不直接令 disconnect 返回 false |
| stop 返回 false 且 receiving=false | 析构 stop 一次 | 不再 stop | 仍 disconnect | stop false 不进入返回值 |
| socket connected=false | Subscriber 仍会无条件 stop | 不执行 driver 层 stop/disconnect | 不调用 disconnect | 对该通道 disconnect result 保持 true |
| C disconnect false、D disconnect true | 依据状态分别处理 | 同上 | 两者均尝试 | false |
| C disconnect true、D disconnect false | 依据状态分别处理 | 同上 | 两者均尝试 | false |
| 重复 disconnect | interface/subscriber 已 reset；socket 若仍 connected 则继续清理 | 仅对仍 receiving 的 socket stop | 对仍 connected 的 socket 重试 | 具备重试机会，但真实 adapter 幂等性仍需测试 |

注意：control 与 diagnostics 是两个独立 Fake。各自本地事件序号不能直接比较跨 socket 的全序。SD-08 应使用共享 recorder 或明确 barrier/happens-before 关系：两个 callback 退出屏障均完成后，才允许观察到对应 socket disconnect；不要以 C 的 seq=5 小于 D 的 seq=4 推断先后。

## 5. 析构与旧会话清理

### 5.1 RobotDriver 析构

RobotDriver::~RobotDriver() 函数体为空。头文件成员声明顺序为：logger、network_config、control socket、diagnostics socket、control interface、diagnostics subscriber、状态和 timeout。C++ 成员按声明逆序析构，因此 diagnostics subscriber 与 control interface 先于两个 socket 成员销毁；Subscriber 析构会 stop 接收线程，但 RobotDriver 析构没有主动调用 disconnect，也没有执行 reset_data。

由此：
- 仅销毁 driver 不等同于显式 disconnect。
- 不能断言析构会调用 Socket::disconnect。
- 若 socket 对象析构本身会关闭底层资源，那是 adapter 自身析构语义，不是 RobotDriver 显式 disconnect 的证据。
- SD-09 应分别记录 explicit disconnect 与 destructor-only 两条路径。

### 5.2 connect 入口旧会话清理

connect 先检查 control connected，若为 true 就调用 disconnect；随后再检查 diagnostics connected，若为 true 再调用 disconnect。若 C connected，第一次 disconnect 已处理两个通道，第二个检查通常变为 false；若只有 D connected，则第二个条件触发清理。

disconnect 返回 false 时 connect 立即失败，不尝试新的 connect。若两个 socket 都报告 disconnected，但仍有遗留 interface/subscriber（属于异常/不一致状态），这两个前置条件都不会触发 disconnect，后续可能出现旧 interface 覆盖或重复 start 的风险；建议增加显式 invariant 检查或无条件清理旧 interface，而非仅凭 socket connected 判断是否存在旧会话。

## 6. SD-07 / SD-08 / SD-10 精确 AAA 规格

### SD-07A：control connect 返回 false，且 Fake 残留 connected

- Arrange：C Fake 的 connect 脚本返回 false，但状态刻意保留 connected=true；D Fake 默认脚本设为 fail-on-unexpected-call；记录共享事件。
- Act：调用 driver.connect(config, timeout)。
- Assert：返回 false；C connect 恰好一次；D connect=0；CI/DS 均未构造；当前实现不会调用 C/D disconnect 或 stop。此用例锁定当前回滚缺口，而非期望行为。

### SD-07B：diagnostics connect 失败后的普通回滚

- Arrange：C connect=true；C start_receive=true；D connect=false 且最终状态 disconnected；C/D 事件写入共享 recorder。
- Act：driver.connect。
- Assert：返回 false；CI 已构造后被销毁；C Subscriber stop 屏障先于 C disconnect；C disconnect 一次；D disconnect=0（D 报告 disconnected）；C active callback=0。验证 disconnect 的返回值被 connect 忽略：即使 C disconnect=false，connect 仍返回 false，且事件中留下 C connected=true。

### SD-07C：control Subscriber 初始化失败抛异常

- Arrange：C connect=true；C start_receive_thread=false；D connect 配置为 unexpected；记录 start 返回前后的 receiving/callback 状态。
- Act：调用 driver.connect 并捕获 runtime_error。
- Assert：异常传播；D connect=0；driver 未调用 disconnect；C 仍 connected（除非 Fake 明确模拟 start 失败的副作用）；不得将该路径写成 connect 返回 false。若 Fake 的失败 start 仍保留 callback，另行记录为接口失败副作用，不得由测试 fixture 隐式清理掩盖生产缺陷。

### SD-07D：diagnostics Subscriber 初始化失败抛异常

- Arrange：C connect/start 成功；D connect 成功；D start_receive_thread=false。
- Act：driver.connect 并捕获 runtime_error。
- Assert：异常传播；C interface 仍存在且 callback 活跃；C/D socket 未由 RobotDriver 清理；D subscriber 对象未完整构造。Teardown 需要显式、可审计地清理测试 Fake，不能把 fixture 清理误记为生产 rollback。

### SD-07E：首帧 timeout / protocol mismatch

- Arrange：两通道 connect/start 成功；无有效 state 或投递 protocol_version 不兼容的 RobotState；诊断消息不投递。
- Act：connect。
- Assert：timeout 或 protocol mismatch 分别返回 false；disconnect 顺序符合第4节；diagnostics 无首帧仍不阻止 connect 进入 state 检查；所有清理 bool 另行记录，不推断成功。

### SD-08：disconnect callback barrier 与跨通道 happens-before

- Arrange：C、D 两个 Fake 分别持有一个已 admission 且阻塞在 gate 的 callback；driver 的 CI/DS 均已构造；使用共享 recorder。
- Act：独立线程调用 disconnect；测试线程确认两个 stop 已进入等待，再分别释放 C/D gate。
- Assert：两个 callback 各自退出后，才出现对应 socket disconnect；reset_data 发生在清理收尾阶段（可通过 test seam/状态读取观测，当前无直接事件 seam）；disconnect 尝试两个通道，即使 C disconnect=false 也继续 D disconnect；返回值为两个 disconnect 结果 AND。不得比较两个 Fake 的本地序号。
- 额外断言：析构 stop 与 driver 显式 stop 可能各出现一次；不固定 stop 恰好一次。

### SD-10A：首帧及时到达但 connect 不提前返回

- Arrange：Fake C callback 注册后立即投递一帧合法且 freshness 足够的 RobotState；D connect/start 成功；采用 ManualClock 与可推进 wait seam。
- Act：调用 connect。
- Assert：当前实现仍持续执行 while 直到 start_connect_time + timeout 窗口结束；没有首帧即 break。此行为应以虚拟时钟精确锁定，避免真实 sleep。

### SD-10B：首帧未到 / 到达后变 stale / protocol mismatch

- Arrange：分别配置无帧、timeout 窗口末尾才投递、首帧较早但时间推进至 stale、protocol mismatch 四个 scenario。
- Act：推进 clock/wait 并调用 connect。
- Assert：分别记录最后一次 read_robot_state 的结果；超时/过期返回 false 并执行 disconnect；协议不匹配在首帧被读到后返回 false 并执行 disconnect。diagnostics 首帧不参与当前门禁。

## 7. 测试夹具 teardown 与异常安全

双 Fake RobotDriver fixture 的 TearDown 建议顺序：

1. 关闭测试侧 producer admission，释放所有 callback gate。
2. join 所有 connect worker、deliver worker、mock robot worker；不得只用 future.wait_for timeout 代替取消/join。
3. 若 driver 仍存在，显式尝试 disconnect 并记录返回值/异常；此步骤是 fixture 的安全兜底，不得算作被测 connect rollback 成功。
4. reset driver，让 Subscriber 析构 stop 屏障完成。
5. 对 Fake 做状态快照，断言 active callback=0、callback 已清空、worker 已 join。
6. 对仍 connected 的 Fake 执行 fixture 专用强制清理并单独记录为 fixture cleanup；若测试对象正是 rollback 缺陷，先保存被测状态快照，再执行兜底清理。
7. 最后释放 Fake。

异常安全要点：
- Subscriber 构造抛异常时，RobotDriver 已经持有的前序成员不会自动按 connect 语义回滚；必须由调用方 catch 或 driver 级 scope guard 才能保证。
- Fake 的 start_receive_thread(false) 默认不应偷偷残留 callback；但应提供单独故障模式模拟“返回 false 但底层已部分启动”，用于证明接口契约不足。
- Fixture 的 RAII 只能确保测试环境最终清理，不能替代对生产 rollback 行为的断言。
- callback 捕获裸 this；所有 producer/callback 必须在 Subscriber 销毁前停止并 join。不要从 callback 自身调用 disconnect 或销毁 RobotDriver。

## 8. 最小修正建议（仅设计，不修改上游）

优先级建议：
1. 为整个 connect 主体建立明确的 rollback guard：任何返回失败或异常都清理已建立的 CI/DS、停止回调、断开两个 socket；保留原始失败原因和每项清理结果。
2. 对 Socket::connect 与 start_receive_thread 定义失败后状态契约：返回 false 是否保证 disconnected/not receiving；若不能保证，必须在调用方做 best-effort cleanup 并保留 residual state。
3. 将 Subscriber 初始化异常转换为有类型的连接错误或保证异常安全 rollback；不要依赖 make_shared 后的 null 检查。
4. 旧会话判断同时检查 interface/subscriber 指针、socket connected/receiving 和 session generation，不只检查 connected。
5. 将 connect 等待改为“收到有效 state 即退出”的条件等待；若出于协议要求必须等完整窗口，应明确说明。使用 steady clock deadline 与可唤醒 condition variable；避免每轮固定 sleep 500ms 和 timeout 超调。
6. 诊断数据应有独立首帧策略：若非必需，明确不纳入 readiness；若必需，实际 read/validate，而不是 diag_interface_ready=true。
7. disconnect 返回结构化 CleanupResult，区分 stop failure、disconnect failure、callback drain timeout 和仍存活资源；当前 bool AND 丢失细节。
8. destructor 是否主动 disconnect 应形成明确 API 决策；如果析构清理，需保证不抛异常并遵守 callback join；如果要求调用者显式 disconnect，则文档与测试必须明确未 disconnect 的后果。

## 9. 验收矩阵与当前状态

| ID | 内容 | 状态 |
|---|---|---|
| SRC-01 | RobotDriver connect/disconnect 源码路径核对 | 静态审查完成 |
| SRC-02 | Subscriber 构造异常与裸 this callback 生命周期 | 静态审查完成 |
| RB-01 | 双 Socket connect 阶段/失败状态矩阵 | 规格完成；测试 NOT_RUN |
| RB-02 | control connect false residual-state 场景 | NOT_RUN |
| RB-03 | control Subscriber start 失败异常路径 | NOT_RUN |
| RB-04 | diagnostics connect false 回滚路径 | NOT_RUN |
| RB-05 | diagnostics Subscriber start 失败异常路径 | NOT_RUN |
| RB-06 | 首帧 timeout / protocol mismatch 回滚 | NOT_RUN |
| RB-07 | disconnect stop/disconnect 顺序与失败传播 | NOT_RUN |
| RB-08 | destructor-only 与 explicit disconnect 对照 | NOT_RUN |
| SD-07A–E | connect rollback 调用方测试 | NOT_RUN |
| SD-08 | 双 callback barrier / happens-before | NOT_RUN |
| SD-10A–B | 首帧等待、timeout、staleness 与 clock | NOT_RUN |
| TSan/ASan | callback 生命周期与竞态 | NOT_RUN |
| Real UDP loopback | adapter/Asio 真实清理 | NOT_RUN |
| ROS 2 Control integration | ResourceManager/ControllerManager | NOT_RUN |
| SIL/HIL/VAL3/CS9/FAT/SAT/实机 | 系统与安全验收 | NOT_RUN |

## 10. 本轮边界与下一节点

- 本轮只对固定上游源码进行静态审查并形成故障矩阵/测试规格。
- 未修改 Stäubli 上游或 ros2_control 上游；未创建、应用或合并 PR。
- 未实现双 Socket 注入、FakeSocket、ManualClock、wait strategy、rollback guard 或新 fixture。
- 未运行 build、gtest、loopback、TSan/ASan、ROS 2 Control 集成、SIL/HIL、VAL3/CS9、FAT/SAT或实机测试。
- RB/SD 全部运行时用例 NOT_RUN；工程级验收未通过；TODO-EXT-001 仍未授权。

**下一节点建议 §9.3.290 / SERVO-873：将 connect 的异常安全与事务式 rollback guard 转化为最小可审查补丁设计，逐个定义清理顺序、失败原因保留、异常传播策略和资源残留检测；仍不修改上游，除非获得明确授权。**
