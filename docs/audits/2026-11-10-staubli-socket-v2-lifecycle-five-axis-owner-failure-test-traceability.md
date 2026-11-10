# Stäubli SocketV2 生命周期五维追踪：事件—资源状态—Owner转移—失败残留—测试用例

- 节点：§9.3.311 / SERVO-894
- 日期：2026-11-10
- 固定上游：`ICube-Robotics/staubli_driver_ros2@bd658e2d266e315d2ee35f985fb352ea88306b79`
- 固定Tree：`257face41970c91f95890ddf47db40b168eca331`
- 输入：SERVO-879 CleanupReport/ResidualHandle；SERVO-880 QuarantineManager shutdown/bounded retry；SERVO-881 concurrency/lock-order/executor race；SERVO-885 F01–F16；SERVO-893 PLUG-L01–L12与架构决策。
- 方法：将既有故障/卸载场景映射到资源状态、唯一reconcile责任和确定性测试；不修改上游。
- 重要：下表中的owner均为**建议的逻辑责任归属**，不是当前源码已实现的对象/强引用关系。

## 1. 总体结论

SERVO-885定义的F01–F16与SERVO-893定义的PLUG-L01–L12可映射到五维追踪，但“一个资源一个当前reconcile owner”必须细分为两个概念：

1. **Resource owner**：持有最后一个强生命周期所有权、保证对象/handle不会提前析构的实体。
2. **Reconcile coordinator**：对该资源的cancel/drain/join/close/session确认执行唯一串行化事务的实体。

两者可由同一个CoreControlBlock/CleanupCoordinator实现，但不能由多个Facade、RobotDriver、QuarantineManager同时各自关闭同一native handle。Owner转移必须是原子move-only handoff；转移失败时源owner仍有效。

推荐分层：
- 活跃socket/worker/callback/native handle：每个generation一个`CoreControlBlock`，由`SocketCore`持有唯一native resource，`CleanupCoordinator`是唯一reconcile执行者。
- RobotDriver control/diagnostics两个通道：两个独立Core generation，各自独立cleanup；RobotDriver只协调顺序和聚合报告，不直接竞争close。
- ROS/plugin callback target与DSO lease：由`PluginUnloadCoordinator`持有，QuarantineManager不得强持有plugin对象/Node。
- Residual Core handoff：`TransportLifecycleOwner`持有QuarantineManager；entry持有move-only CoreControlBlock owner；manager不是native close的第二执行者，而是排程/状态管理者。
- 进程最终退出：`ProcessLifecycleOwner`决定CLEAN、RESIDUAL_RETAINED、PLUGIN_UNLOAD_BLOCKED或FORCED_PROCESS_EXIT；不得把OS回收等同于协议/设备安全关闭。

## 2. 状态词汇与终态规则

| 资源维度 | 状态集合（建议） | 允许标记为完成的必要条件 |
|---|---|---|
| admission | OPEN / CLOSING / CLOSED | CLOSED且不会再准入新用户callback |
| async handlers | PENDING / DRAINING / ZERO / UNKNOWN | pending=0且取消/完成结果已核对 |
| callbacks | ACTIVE(n) / DRAINING / ZERO / UNKNOWN | active=0且所有lease归还 |
| worker | NOT_STARTED / RUNNING / EXIT_REQUESTED / EXITED / JOINED / JOIN_FAILED | JOINED；不能用stop请求代替 |
| native handle | OPEN / CLOSE_PENDING / CLOSED / CLOSE_OUTCOME_UNKNOWN | 通过backend postcondition确认CLOSED |
| remote session | ACTIVE / STOP_REQUESTED / ACKED / UNKNOWN | 协议要求确认时必须有ACK；UNKNOWN不得映射为CLOSED |
| plugin code | REFERENCED / QUIESCING / ZERO / UNLOAD_BLOCKED / UNLOADED | callback、handler、vtable、deleter、thread entry均不再引用plugin image |
| owner | FACADE / TRANSFER_PENDING / QUARANTINE / PROCESS_RETAINED / RELEASED | 任何时刻恰有一个逻辑强owner；只有稳定终态才能RELEASED |

**禁止推断：** connected=false不等于native CLOSED；worker stop requested不等于JOINED；callback admission closed不等于active callbacks=0；Core已转交Quarantine不等于plugin code lease归零；shutdown deadline到期不等于清理成功。

## 3. F01–F16 五维追踪矩阵

| ID / 事件 | 资源状态与成功后置条件 | 唯一Owner / Reconcile coordinator | 失败残留及转移 | 必须测试 |
|---|---|---|---|---|
| F01 open失败 | native handle应为NOT_OPEN；generation仍可观测 | CoreControlBlock / CleanupCoordinator | OPEN_OUTCOME_UNKNOWN时保留Core，转TransportLifecycleOwner；不得伪造空资源 | Fake open error；确认无handle或明确UNKNOWN；重复cleanup幂等 |
| F02 option/bind/resolve失败 | 分阶段初始化；每一步资源状态独立 | CoreControlBlock / CleanupCoordinator | 回滚中close失败保留NativeResourceState=CLOSE_OUTCOME_UNKNOWN；不能只返回首个异常 | 每阶段故障注入+rollback journal；验证primary failure不被cleanup error覆盖 |
| F03 async启动后立即stop | handler PENDING→CANCELLED/COMPLETED；active=0 | CoreControlBlock / CleanupCoordinator | pending未知/非零时保留Core和worker owner；转Quarantine仅在handoff成功后 | barrier控制handler排队/执行与stop竞态；断言无late use-after-free |
| F04 callback中销毁Subscriber | Subscriber admission CLOSED；active lease=0才允许销毁 | Plugin/Subscriber lifetime owner；Core协调transport；Subscriber receive lease单独归还 | Subscriber callback lease未归零时保留Subscriber/plugin code lease；不得仅转移socket owner | latch阻塞callback，另线程销毁；断言析构等待或明确RESIDUAL |
| F05 callback抛异常 | callback lease必须RAII归还；worker不因异常意外终止 | CoreControlBlock / Callback trampoline + CleanupCoordinator | 记录CALLBACK_EXCEPTION；若worker状态未知则保留worker/Core owner | throwing callback；异常不得逃逸线程入口，active计数归零 |
| F06 worker self-stop | worker不能join自身；stop request与join分离 | CoreControlBlock / CleanupCoordinator（join由外部lifecycle线程） | 返回WOULD_DEADLOCK/ASYNC_STOP_REQUESTED；worker与Core owner保留 | callback中调用stop；确认无self-join、无detach、外部join完成 |
| F07 join超时/卡死 | worker仍RUNNING或JOIN_FAILED，不是JOINED | TransportLifecycleOwner / Core CleanupCoordinator | THREAD_RESIDUAL；Quarantine保留Core和thread owner；deadline只终止等待 | fake worker barrier + monotonic deadline；验证owner不释放 |
| F08 native close异常 | native=CLOSE_OUTCOME_UNKNOWN；connected flag不得替代 | CoreControlBlock / CleanupCoordinator | NATIVE_CLOSE_RESIDUAL；转Quarantine后只由同一Core coordinator重试 | close throw；snapshot保留UNKNOWN；后续retry确认close后才COMPLETE |
| F09 stop失败但close成功 | worker可能仍存活；native CLOSED不能代表整个Core clean | CoreControlBlock / CleanupCoordinator | THREAD_RESIDUAL与NATIVE_CLOSED并存；保留Core，禁止整体COMPLETE | stop failure + close success；assert close与worker结果分列 |
| F10 control成功/diagnostics失败 | 两个channel分别有generation和terminal state | 每个channel自己的CoreControlBlock / CleanupCoordinator；RobotDriver只聚合 | 仅diagnostics残留转Quarantine；control不重复close | 双通道差异化故障脚本；只重试残留channel |
| F11 重复disconnect | 每个generation必须保持幂等且不丢失UNKNOWN | CoreControlBlock / CleanupCoordinator | 首次失败状态必须持续存在；第二次retry不可由connected=false短路 | first close fail / second success；检查无double close及状态误清 |
| F12 lifecycle cleanup/shutdown/error | lifecycle result需与资源终态一致；STOP与teardown分离 | TransportLifecycleOwner；每个Core各自coordinator；ROS lifecycle仅编排 | cleanup失败返回ERROR/RESIDUAL；进程owner接管前不得销毁Node相关callback依赖 | on_cleanup/on_shutdown/on_error各阶段注入；验证结果传播与顺序 |
| F13 plugin unload时callback活跃 | pending=0、active=0、worker joined、plugin code lease=0 | PluginUnloadCoordinator（DSO gate）；Core owner仍负责transport | PLUGIN_UNLOAD_BLOCKED，保持DSO加载；不能靠Quarantine持有plugin object | callback latch与反复load/unload竞态；确认DSO不早卸载 |
| F14 mock server第二通道初始化失败 | 第一通道rollback/terminal state独立确认 | MockServer instance owner / per-socket Core coordinator | 第一通道rollback失败则保留server/Core owner；不销毁仍有资源的实例 | 第二通道connect失败，第一通道close也注入失败；验证residual handoff |
| F15 native handle复用/重复close | 只允许关闭该generation绑定的handle；旧generation不得操作复用后的新handle | CoreControlBlock / platform NativeSocketOps adapter | HANDLE_IDENTITY_UNKNOWN时保留owner并停止自动close；禁止按裸整数/FD重新定位 | 平台handle reuse、generation stale、重复close测试；真实OS测试后置 |
| F16 远端session未确认 | local native与remote session状态分离；REMOTE_SESSION_UNKNOWN | RobotDriver session-state owner；本地native仍归CoreControlBlock | 本地资源可关闭但remote UNKNOWN单独报告；不得把STOP发送成功当ACK | fake protocol无ACK/超时/迟到ACK；确认本地close不清除remote UNKNOWN |

## 4. PLUG-L01–L12 Plugin Unload 追踪矩阵

| ID / 事件 | 资源状态/完成条件 | 唯一Owner | 失败残留/处理 | 必须测试 |
|---|---|---|---|---|
| PLUG-L01 正常cleanup | admission CLOSED、pending=0、active=0、worker JOINED、native CLOSED | PluginUnloadCoordinator负责DSO gate；Core coordinator负责transport | 任一状态未知即UNLOAD_BLOCKED | 正常全序列与最终snapshot断言 |
| PLUG-L02 is_connected=false但native未知 | 必须主动核对native状态，不允许短路 | CoreControlBlock / CleanupCoordinator | CLOSE_OUTCOME_UNKNOWN保留Core | 构造connected=false/native open组合 |
| PLUG-L03 on_error STOP失败 | STOP结果与teardown结果独立 | RobotDriver负责协议状态；Core coordinator负责本地清理 | REMOTE_SESSION_UNKNOWN与native residual分开上报 | STOP失败后继续执行批准的本地teardown策略 |
| PLUG-L04 callback执行中unload | active lease归零前禁止卸载 | PluginUnloadCoordinator | 保持plugin image loaded；报告PLUGIN_UNLOAD_BLOCKED | callback latch阻塞时发起unload |
| PLUG-L05 cancel期间pending handler完成 | admission已关；handler不得进入用户callback | CoreControlBlock / CallbackAdmissionGate | pending无法归零则保留Core与DSO lease | barrier控制cancel completion与admission close竞态 |
| PLUG-L06 callback触发stop | worker线程不得self-join | Core CleanupCoordinator；外部lifecycle thread join | 异步stop request，保留worker owner | callback内stop，外部线程join |
| PLUG-L07 join失败/超时 | Worker=JOIN_FAILED/RUNNING，不能宣称quiescent | TransportLifecycleOwner | THREAD_RESIDUAL；不detach、不释放 | fake join failure与deadline |
| PLUG-L08 native close异常 | Native=CLOSE_OUTCOME_UNKNOWN | CoreControlBlock | 保留Core owner并有界reconcile | close异常后重复disconnect/retry |
| PLUG-L09 plugin deleter/vtable仍被引用 | PluginCodeLeaseCount必须为0 | PluginUnloadCoordinator | DSO保持加载；Quarantine不能代替代码lease | 自定义deleter、vtable、handler跨卸载边界 |
| PLUG-L10 反复load/unload | 每轮所有lease/worker/FD归零 | PluginUnloadCoordinator；各Core独立coordinator | 某轮残留阻止该DSO卸载和后续不安全重载 | N轮load/unload + leak/thread/fd/sanitizer |
| PLUG-L11 双通道部分清理 | control/diagnostics独立终态 | 各channel Core owner；RobotDriver聚合 | 仅残留channel交Quarantine | control成功、diagnostics失败和反向组合 |
| PLUG-L12 lifecycle重复/乱序 | transition generation与cleanup operation idempotent | TransportLifecycleOwner / Core coordinator | stale generation拒绝；不重复释放 | 重复cleanup/shutdown/error乱序与并发调用 |

## 5. Owner唯一性检查与禁止的责任冲突

| 资源 | 唯一逻辑Owner | 唯一Reconcile执行者 | 不得成为第二Owner/第二执行者 |
|---|---|---|---|
| UDP native socket | CoreControlBlock | Core CleanupCoordinator | UDPSocket facade、RobotDriver、QuarantineManager不得各自close |
| io_context/worker | CoreControlBlock | Core CleanupCoordinator；外部lifecycle thread负责join调度 | worker不得销毁最后Core owner；不detach |
| callback target/Subscriber | Subscriber/plugin lifetime owner | CallbackAdmissionGate/PluginUnloadCoordinator | transport manager不得强持有plugin object |
| control channel | control Core generation | control CleanupCoordinator | diagnostics channel不得替它清理 |
| diagnostics channel | diagnostics Core generation | diagnostics CleanupCoordinator | control channel不得替它清理 |
| residual Core | TransportLifecycleOwner下的Quarantine entry（原子接管后） | 原Core CleanupCoordinator，按entry调度 | QuarantineManager不再实现第二套close逻辑 |
| plugin DSO | PluginUnloadCoordinator/host class loader | PluginUnloadCoordinator | QuarantineManager不能以持有Core为由推断DSO可卸载 |
| remote session | RobotDriver session state owner | protocol/session reconciler | native socket close不能清除远端session状态 |
| process exit | ProcessLifecycleOwner | ProcessLifecycleOwner编排，不直接多头close | 静态析构/泄漏singleton/局部Node不得决定最终策略 |

**发现的架构缺口（需后续解决）：**
1. Residual Core若仍持有plugin-defined callback/deleter/vtable，转给进程级Quarantine并不能让plugin卸载安全；必须先解除plugin code dependency或保持DSO加载。
2. Quarantine entry的owner transfer与manager shutdown必须采用prepare/commit和in-flight drain；容量满、shutdown race、executor停止时源handle必须保持有效。
3. deadline/attempt耗尽只能进入SEALED_RESIDUAL/RETRY_EXHAUSTED；不能自动释放owner。
4. F16远端会话是协议状态，不是native handle；必须由独立session owner追踪。
5. F15 handle reuse必须依赖平台adapter与generation identity；只比较裸FD/SOCKET数值不足以证明身份。

## 6. 与SERVO-881并发竞态测试的映射

| 竞态测试 | 关联追踪项 | 关键断言 |
|---|---|---|
| RACE-02 manager admission close vs retry claim | F07/F08/F10/F11、PLUG-L07/L08/L11 | 关闭点后无新claim，既有任务计入drain |
| RACE-03 transfer prepare vs shutdown | F07/F10/F13、PLUG-L07/L09 | 无半提交，owner恰一个 |
| RACE-05 executor拒绝task | F07/F08/F10 | entry恢复pending，owner保留 |
| RACE-06 executor shutdown vs task submit | F07/F12 | 无任务状态丢失，不依赖已关闭ROS executor |
| RACE-07 duplicate retry/revision | F08/F11 | 同generation单一cleanup transaction |
| RACE-09 deadline | F07/F08 | timeout后owner保留 |
| RACE-11 worker callback reentrant stop | F06/F07、PLUG-L06/L07 | 不self-join，返回异步/拒绝 |
| RACE-13 callback active vs plugin unload | F04/F13、PLUG-L04/L05/L09 | active/pending/code lease归零前不卸载 |
| RACE-14 last external handle release | F07/F13 | worker/lifecycle owner保活Core |
| RACE-15 duplicate complete/retry | F08/F11 | 不double close/join/free |
| RACE-16 capacity full | F07/F10 | 拒绝新handoff，源owner不失效 |
| EXEC-01 executor stopped then manager seal | F07/F12 | 仍可生成snapshot/report |
| EXEC-03 ROS context shutdown vs node destruction | F04/F12/F13 | 无悬空Node/callback |
| EXEC-04 worker exit | F06/F07 | 外部owner join，无detach |

## 7. 推荐最小测试切片与通过门槛

1. **T1 State/Owner unit tests：** F01/F02/F08/F11/F15/F16；状态快照区分connected/native/remote/worker。
2. **T2 Callback barrier：** F03/F04/F05、PLUG-L04/L05/L09；确定性barrier/latch，不用sleep猜时序。
3. **T3 Worker lifecycle：** F06/F07/F09、PLUG-L06/L07；self-join拒绝、deadline residual、无detach。
4. **T4 Multi-channel reconcile：** F10/F11/F14、PLUG-L11；per-generation cleanup、部分成功重试。
5. **T5 Lifecycle/plugin integration：** F12/F13、PLUG-L01–L03/L10/L12；真实plugin DSO load/unload与ROS lifecycle。
6. **T6 Platform/protocol：** F15/F16；真实OS handle reuse与协议ACK/timeout仿真。
7. **T7 Manager/executor races：** SERVO-881 RACE-01–16、EXEC-01–04；fake monotonic clock、fake executor、锁顺序与TSan。

**总通过条件：** 每个资源在每个generation恰有一个owner；每项reconcile最多一个in-flight事务；任何UNKNOWN/RESIDUAL都不能进入COMPLETE；任何plugin code lease非零都不能unload；所有失败路径都有可查询报告与唯一下一责任人；测试必须在固定环境实际执行并归档日志/工件/hash。

## 8. 状态与边界

| 项目 | 状态 |
|---|---|
| F01–F16 五维映射 | SPECIFIED |
| PLUG-L01–L12 五维映射 | SPECIFIED |
| owner/reconcile唯一性静态核验 | DESIGN_REVIEWED |
| SERVO-881竞态测试关联 | STATIC_MAPPED |
| 真实owner transfer与manager实现 | NOT_RUN |
| Fake failure injection / callback barrier | NOT_RUN |
| plugin load/unload与DSO lease | NOT_RUN |
| native handle reuse / remote ACK仿真 | NOT_RUN |
| TSan/ASan/UBSan及ROS集成 | NOT_RUN |
| A1.1 | BLOCKED |

本节点没有执行CMake/colcon/gtest、Fake测试、线程竞态、plugin load/unload、平台handle reuse、协议仿真、sanitizer、VAL3/CS9、SIL/HIL、FAT/SAT或实机测试。没有修改固定上游、没有创建/应用/合并PR；`TODO-EXT-001`仍未授权。§9.3.281–§9.3.294历史TaskPlan同步缺口继续透明保留。

**下一节点：§9.3.312 / SERVO-895：把本矩阵转成可机器检查的 YAML/JSON traceability schema 与CI policy contract（schema version、stable IDs、owner cardinality、required evidence、status vocabulary、cross-reference integrity）；先定义schema和静态一致性检查，不创建上游实现PR。**
