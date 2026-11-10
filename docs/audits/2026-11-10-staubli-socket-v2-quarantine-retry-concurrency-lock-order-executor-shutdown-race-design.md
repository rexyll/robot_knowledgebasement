# Stäubli SocketV2 QuarantineManager / RetryScheduler concurrency model、lock ordering、executor integration 与 deterministic shutdown race test design

- **节点：** §9.3.298 / SERVO-881
- **日期：** 2026-11-10
- **固定上游基线：** `ICube-Robotics/staubli_driver_ros2@bd658e2d266e315d2ee35f985fb352ea88306b79`
- **前置节点：** SERVO-878、SERVO-879、SERVO-880。
- **性质：** 静态并发设计和测试规格；不是实现，也不是测试通过证据。

## 1. 并发目标与安全不变量

本节点将QuarantineManager和RetryScheduler的并发职责收敛为可验证的协议。设计必须保证：

1. 同一Core generation至多存在一个cleanup transaction；重复触发只能合并/返回既有任务状态。
2. 任意线程竞争下，ResidualResourceHandle的owner transfer必须原子提交或完全失败；失败时源handle仍有效。
3. manager shutdown关闭admission后，不得再创建新entry或新retry任务；已入场操作必须可计数、可drain。
4. 锁持有期间不得执行用户callback、ROS executor dispatch、阻塞socket操作、join、等待condition variable或日志sink调用。
5. 不允许在持有manager/entry/Core锁时等待executor future；executor callback不得反向同步调用并等待manager锁。
6. executor停止与manager shutdown竞态时，未完成任务必须回到可查询状态，owner不能随task object析构而丢失。
7. generation与sequence校验阻止旧任务覆盖新一代Core状态。
8. 所有线程退出由其明确owner join；不detach，不self-join，不允许worker线程析构最后一个Core owner。

## 2. 执行角色与数据模型

建议角色：
- **Control Plane：** 外部lifecycle thread执行register/transfer/shutdown/administrative retry请求。
- **Scheduler：** 计算next eligible time、attempt预算和并发槽位；不直接持有Core内部锁。
- **Cleanup Worker：** 执行一个已claim的cleanup transaction；worker数量固定或复用受控executor。
- **Completion Dispatcher：** 将结果写回entry状态；若executor已经停止，使用manager内部同步completion path，不依赖已关闭的ROS executor。
- **Observer：** 只读取不可变snapshot，不获取Core锁，不触发cleanup。

Entry采用稳定ID + generation + revision：
```cpp
struct EntryKey {
  std::uint64_t core_id;
  std::uint64_t generation;
};

enum class EntryState : std::uint32_t {
  retry_pending, claimed, cleaning, retryable_residual,
  exhausted, complete, owner_transferred, stale, blocked
};

struct EntrySnapshot {
  EntryKey key;
  std::uint64_t revision;
  EntryState state;
  std::uint32_t attempt_count;
  std::uint32_t last_error_code;
  bool owner_retained;
  bool in_flight;
};
```
以上为接口草案，字段类型和ABI仍需冻结；snapshot不得包含指针、native handle或Core owner。

## 3. 锁域与全局锁顺序

建议锁域：
- **M：** manager registry/admission/shutdown state。
- **E：** 单个entry状态、generation、attempt计数与owner slot。
- **C：** Core内部资源状态。
- **S：** scheduler队列与并发槽位。
- **L：** callback lease计数（若独立于entry）。

首选策略是减少嵌套锁：M只保护registry和manager状态；E只保护单entry；S只保护队列/槽位；C仅由cleanup worker在无M/E/S锁时短暂获取；L通过原子计数或独立短临界区管理。

若不得不嵌套，唯一允许的顺序为：
`M -> E -> S`。
禁止：
- 持有M/E/S时获取C；
- 持有C时回调manager并获取M/E；
- 持有任何上述锁时等待future、join、condition variable或callback drain；
- 从日志sink、ROS callback或用户回调中持锁调用manager API。

所有需要跨锁域的动作采用两阶段协议：在当前锁下claim并复制稳定key/revision；释放锁后执行外部动作；再次获取目标锁并校验key、generation、revision后提交结果。revision不匹配时丢弃过期结果并记录STALE_COMPLETION，不能覆盖更新状态。

## 4. 原子claim与owner transfer协议

### 4.1 retry claim

1. Scheduler在S锁下选取到期候选key，释放S。
2. Manager按M->E顺序确认manager仍ACCEPTING或允许该阶段retry、entry仍RETRY_PENDING、generation匹配且无in_flight。
3. 在E锁下设置CLAIMED/in_flight=true、递增revision和attempt token；随后释放锁。
4. Worker执行cleanup，不持有M/E/S锁。
5. Worker以key+attempt token提交结果；只有token/revision仍匹配才更新entry。
6. 任意失败或取消路径必须清除in_flight并保留owner；如果manager关闭，状态进入SHUTDOWN_PENDING/RETRY_EXHAUSTED而非丢弃entry。

### 4.2 owner transfer

owner transfer采用prepare/commit：
- prepare阶段在源handle确认有效、manager admission允许、容量预留成功后创建不可见reservation；源handle仍是owner。
- commit阶段在短临界区把owner移动到entry并标记reservation committed；源handle置空必须与entry owner安装处于同一原子提交协议。
- 若中途失败，撤销reservation并保持源handle完整。
- 不允许通过shared_ptr临时复制“解决”原子性；资源owner语义需单一且可追踪。
- shutdown关闭admission与transfer reservation竞争时，关闭点之后不得commit新reservation；若已进入commit临界区，则shutdown必须等待该事务完成并纳入drain计数。

## 5. Executor integration

Executor是执行资源，不是资源所有权容器。推荐把Scheduler与ROS executor解耦：
- Manager有自己的轻量状态机与pending work队列；可以由应用控制线程或受控executor pump。
- ROS executor只负责调用外部节点/driver callback；不能成为QuarantineManager唯一生命周期owner。
- executor提交任务返回拒绝、executor取消、context shutdown、worker异常等情况都必须转为显式task outcome；entry保持owner retained。
- 若executor已停止，manager仍须可同步seal并生成snapshot/report；不得向已销毁Node投递completion。
- 不允许在ROS callback中同步调用shutdown并等待该callback所在executor线程完成自身drain。
- 若使用专用worker，线程数固定、启动和join由TransportLifecycleOwner负责；不为每个entry创建线程。

### Executor stop与manager shutdown顺序

1. manager关闭新task admission；
2. 停止scheduler产生新claim；
3. 取消尚未开始的queued task，并将entry还原为RETRY_PENDING/SHUTDOWN_PENDING；
4. 对已开始task设置cancel request（仅作为协作提示，不代表native syscall已取消）；
5. drain已claim任务至shutdown deadline；
6. deadline后保留仍在运行任务的Core owner与线程owner，报告SHUTDOWN_INCOMPLETE；
7. executor可停止dispatch，但不得销毁仍可能被task访问的manager/Core；
8. lifecycle owner在可安全join后完成线程回收，或明确报告进程级forced-exit。

## 6. Deadlock与竞态风险目录

| 风险 | 触发路径 | 预防规则 |
|---|---|---|
| M/E反向锁 | entry回调持E再注册M | 仅M->E；回调移出锁外 |
| E/C反向锁 | cleanup持C同步写E | cleanup释放C后提交E |
| M/S互锁 | scheduler持S同步调用manager | 选候选后释放S再claim |
| executor future死锁 | 持M等待ROS callback，callback等M | 锁外等待；禁止同步future链 |
| self-join | worker调用manager shutdown | 检测线程身份并拒绝 |
| duplicate cleanup | 两个scheduler同时claim | E锁+attempt token单次claim |
| stale completion | 旧generation晚到 | key+generation+revision CAS式提交 |
| owner loss | transfer与shutdown交错 | reservation/commit事务和drain计数 |
| executor stopped | completion投递被拒绝 | 内部同步fallback并保留owner |
| shutdown starvation | retry持续占满槽位 | shutdown专用预算和公平队列 |
| callback re-entry | callback中重入stop/disconnect | callback不持内部锁，API返回ASYNC/WOULD_DEADLOCK |
| ABA | entry slot复用，旧任务提交 | generation+monotonic revision |

## 7. Deterministic race test设计

测试必须使用可控barrier/latch、fake executor、fake monotonic clock、fault injection hook，不依赖sleep猜测时序。所有测试均为设计规格，未运行。

| ID | 确定性步骤 | 必须断言 | 状态 |
|---|---|---|---|
| RACE-01 | 两个worker同时claim同一EntryKey | 仅一个attempt token成功 | NOT_RUN |
| RACE-02 | retry claim与shutdown admission close同时屏障释放 | 关闭点后无新claim；已claim被计入drain | NOT_RUN |
| RACE-03 | transfer prepare后、commit前触发shutdown | transfer失败或shutdown等待事务；owner恰有一个 | NOT_RUN |
| RACE-04 | cleanup执行中generation递增并替换entry | 旧completion不得覆盖新generation | NOT_RUN |
| RACE-05 | executor拒绝已排队task | entry恢复pending且owner保留 | NOT_RUN |
| RACE-06 | executor shutdown发生于task提交与确认之间 | 不丢task状态，不重复执行 | NOT_RUN |
| RACE-07 | cleanup在释放C锁后提交E时触发第二次retry | token/revision拒绝重复提交 | NOT_RUN |
| RACE-08 | 两个entry交叉执行M/E/S操作 | 不出现锁顺序反转或死锁 | NOT_RUN |
| RACE-09 | fake clock推进至attempt deadline | 状态可超时但Core owner仍保留 | NOT_RUN |
| RACE-10 | retry flood与shutdown drain并发 | shutdown预算获得公平执行，不无限饥饿 | NOT_RUN |
| RACE-11 | worker callback重入stop/shutdown | 明确返回WOULD_DEADLOCK/ASYNC，不self-join | NOT_RUN |
| RACE-12 | completion dispatcher已销毁 | 内部fallback完成状态记账 | NOT_RUN |
| RACE-13 | callback active计数与plugin unload gate并发 | gate不早于active/pending归零开放 | NOT_RUN |
| RACE-14 | 最后一个外部handle在worker执行期间释放 | worker/lifecycle owner仍持有Core至安全终态 | NOT_RUN |
| RACE-15 | 同一key重复complete/retry请求 | 幂等，不重复close/join/free | NOT_RUN |
| RACE-16 | manager达到entry/queue容量边界 | 拒绝新任务，既有owner不被淘汰 | NOT_RUN |
| LOCK-01 | lock instrumentation记录所有获取序列 | 不存在逆序嵌套 | NOT_RUN |
| LOCK-02 | callback中尝试调用阻塞API | 返回非阻塞结果，无内部锁跨调用 | NOT_RUN |
| EXEC-01 | executor停止后manager seal | snapshot/report仍可生成 | NOT_RUN |
| EXEC-02 | queued task取消与running task完成竞争 | queued不执行，running结果仅提交一次 | NOT_RUN |
| EXEC-03 | ROS executor context shutdown与node destruction交错 | 无悬空Node/callback target | NOT_RUN |
| EXEC-04 | worker线程退出 | 所有join由外部owner完成，无detach | NOT_RUN |

## 8. 可观测性与故障诊断

每个事件至少记录sequence、EntryKey、revision、attempt token、thread role、old/new state、reason code和monotonic elapsed offset。禁止将地址、native handle或任意payload作为稳定诊断ID。应能从事件序列重建：
- 谁claim了entry；
- owner何时transfer；
- executor何时接受/拒绝任务；
- cleanup何时开始/结束；
- shutdown admission close与drain barrier何时发生；
- 最终entry为何残留、exhausted或stale。

日志调用必须在锁外；日志失败不能改变状态提交。若事件队列容量有限，优先保留最终状态和错误摘要，并计数报告丢失事件数。

## 9. 实施与验收门禁

建议分层实现顺序：
1. 纯状态机 + fake clock + 单线程模型测试；
2. Entry claim/revision/generation与move-only owner transfer单元测试；
3. fake executor拒绝/取消/shutdown竞态测试；
4. lock-order instrumentation与deterministic barrier race tests；
5. 固定worker pool、join与native cleanup fault injection；
6. TSan/ASan/UBSan与长时间压力测试；
7. ROS component executor与plugin load/unload集成；
8. ROS 2 Control、SIL/HIL、VAL3/CS9、FAT/SAT和实机验证。

实施前待冻结：是否采用M->E->S的严格锁顺序或完全避免嵌套；executor pump的归属；shutdown deadline后运行中cleanup如何保活；revision/token位宽与溢出处理；回调重入API错误码；事件队列满时的降级策略。

## 10. 状态与下一节点

- **已完成：** 并发角色、锁域、允许锁顺序、两阶段claim/transfer、executor stop协议、deadlock风险目录和确定性race test规格。
- **未完成：** 所有manager/scheduler/worker/executor桥接与状态机均未实现。
- **验收状态：** RACE-01至16、LOCK-01至02、EXEC-01至04全部NOT_RUN。
- **未执行：** C++17编译、CMake、gtest、fake clock测试、barrier race tests、lock instrumentation、TSan/ASan/UBSan、压力测试、ROS component/plugin测试、ROS 2 Control、VAL3/CS9、SIL/HIL、FAT/SAT或实机测试。
- **上游边界：** 未修改固定上游、未创建/应用/合并PR；`TODO-EXT-001`仍未授权。
- **历史同步：** 第21章TaskPlan正文仍存在§9.3.281–§9.3.294逐节点同步缺口；本轮不伪造回填。
- **下一节点：** §9.3.299 / SERVO-882：SocketV2 cleanup transaction idempotency、generation fencing、partial-step recovery 与 native resource close ordering formalization。
