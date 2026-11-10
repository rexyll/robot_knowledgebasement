# Stäubli SocketV2 cleanup transaction 幂等性、generation fencing、partial-step recovery 与 native resource close ordering formalization

- **节点：** §9.3.299 / SERVO-882
- **日期：** 2026-11-10
- **固定上游基线：** `ICube-Robotics/staubli_driver_ros2@bd658e2d266e315d2ee35f985fb352ea88306b79`
- **前置节点：** SERVO-879至SERVO-881。
- **性质：** 静态事务与资源关闭顺序设计；不是实现或验证报告。

## 1. 目标与不可破坏的不变量

清理事务必须在重复调用、部分成功、异常返回、超时、shutdown竞争和generation替换下保持资源所有权可追踪。核心不变量：

1. 每个资源句柄只有一个明确owner；close责任在一个原子状态转换中从owner移交给cleanup transaction。
2. 每个cleanup transaction由稳定的transaction ID、Core ID、generation和plan revision标识；同一generation相同plan的重复请求合并，不创建并行close。
3. 每个step最多有一个执行者；完成结果只允许由持有当前step token的执行者提交。
4. step已完成后不得再次执行具有破坏性的native close/free/unregister；重复cleanup只能读取既有结果或执行明确声明幂等的观察操作。
5. 旧generation的late completion不得写入新generation的状态，也不得触碰新generation复用的fd、socket、callback或object。
6. 发生“调用可能已产生副作用但结果未知”的情况时进入UNKNOWN/QUARANTINED；禁止将UNKNOWN等价于FAILED并盲目重试。
7. 所有依赖资源必须在被依赖资源之前解除；任何close顺序必须由资源依赖图导出，而不是依赖析构顺序偶然性。
8. 超时不等于操作已取消；不能因deadline到达而释放仍被运行中任务使用的owner。

## 2. Cleanup transaction identity 与 journal

建议事务身份：
```cpp
struct CleanupTransactionId {
  std::uint64_t core_id;
  std::uint64_t generation;
  std::uint64_t plan_revision;
  std::uint64_t transaction_sequence;
};

enum class StepState : std::uint8_t {
  not_started, claimed, in_progress, succeeded,
  failed_retryable, failed_terminal, outcome_unknown, skipped
};

struct StepRecord {
  std::uint32_t step_id;
  std::uint64_t attempt_token;
  StepState state;
  std::uint32_t attempt_count;
  std::int32_t result_code;
  std::uint64_t dependency_mask;
};

struct CleanupJournalSnapshot {
  CleanupTransactionId id;
  std::uint64_t revision;
  bool owner_retained;
  bool terminal;
  // step records are copied into an immutable snapshot
};
```
这是接口草案，不代表已写入源代码。Journal是进程内事务状态账本，不宣称跨进程崩溃持久化。若未来要求crash recovery，必须另行定义持久化格式、fsync/原子替换、native handle不可恢复语义和启动时orphan扫描，不能把内存journal称为durable log。

Transaction key按(core_id,generation,plan_revision)索引。transaction_sequence用于区分同一key下明确授权的新事务，不得被旧任务猜测或复用。重复调用若key匹配且事务未终结，返回既有事务snapshot/handle；若终结则返回终结结果，不自动重新执行close。重新建立连接必须分配新generation。

## 3. Step状态机与幂等规则

允许状态转换：
- NOT_STARTED -> CLAIMED -> IN_PROGRESS
- IN_PROGRESS -> SUCCEEDED
- IN_PROGRESS -> FAILED_RETRYABLE
- IN_PROGRESS -> FAILED_TERMINAL
- IN_PROGRESS -> OUTCOME_UNKNOWN
- CLAIMED -> NOT_STARTED（执行前取消且确认未产生副作用）
- 任意非终结状态 -> SKIPPED（仅当依赖证明该step不再适用）
- FAILED_RETRYABLE -> CLAIMED（仅在retry policy许可、generation与token仍有效时）

SUCCEEDED、FAILED_TERMINAL、OUTCOME_UNKNOWN、SKIPPED为本step的终结/封存状态；UNKNOWN只能通过专门的reconcile/probe事务转换，不得直接回到NOT_STARTED。

幂等分类：
- **观察型：** 查询状态、读取close标志，可重复执行。
- **幂等设置型：** 将逻辑状态设为STOP_REQUESTED、关闭admission，可重复执行，但需revision校验。
- **一次性副作用型：** unregister、shutdown、join、native close、free、释放plugin lease。必须有唯一claim token和完成记录；不能仅因函数返回错误就假设副作用未发生。
- **可探测副作用型：** 操作后可独立检查资源是否仍存在；先probe，再决定重试。
- **结果不确定型：** API/系统调用语义不能证明是否已完成；保留handle身份并隔离，直到平台专用reconcile策略作出结论。

所有step实现必须声明副作用类别、成功判据、重试安全性、超时语义、可观测探测方式和资源owner转移点。

## 4. Generation fencing 与 stale work rejection

每次成功建立新的transport session分配严格递增generation。所有异步任务捕获：
- Core ID；
- generation；
- transaction ID；
- step ID；
- attempt token；
- expected journal revision。

提交结果时必须同时校验以上身份。只比较裸指针、fd数值或Core地址不足以防止ABA，因为native descriptor和内存地址可能被复用。

资源句柄应携带generation tag或由独立不可复用的ResourceId间接引用。close worker不得从“当前Core”重新读取待关闭fd；必须使用transaction在claim时捕获并拥有的旧资源对象。新generation不得继承旧generation的cleanup owner。

Generation counter溢出策略需明确：采用足够宽的无符号计数并在达到上限时拒绝复用/重建Core identity，不能静默wrap。generation分配和Core替换必须在同一Core lifecycle serialization domain中完成。

## 5. Partial-step recovery

当步骤序列部分成功：
1. 冻结当前transaction plan revision，防止同一事务中途换步骤依赖。
2. 将成功步骤保留为SUCCEEDED，不再重跑。
3. 仅对FAILED_RETRYABLE且副作用已证明未发生/可安全重复的步骤申请新attempt token。
4. OUTCOME_UNKNOWN进入隔离态，等待独立probe或平台明确的reconciliation。
5. 依赖某个未完成step的后续步骤保持blocked；不得越过依赖边继续关闭。
6. 重试预算耗尽后将事务标记RESIDUAL_RETAINED，owner仍由QuarantineManager或显式ResidualResourceHandle持有。
7. 恢复动作必须是同一transaction的continuation或新的显式reconcile transaction；不得通过重新调用disconnect隐式创建第二套close流程。

若进程退出导致journal丢失，native资源的进程级回收由操作系统承担，但这不证明ROS callback、线程、外部控制器会话或远端状态已被正确终止；报告必须区分process-local reclaim与remote/session cleanup。

## 6. Native resource dependency graph 与建议关闭顺序

最终顺序须依据实际实现中的资源依赖和平台API确认。建议依赖图（箭头表示“左侧先解除，右侧才可销毁”）：

1. **Admission / command source：** 禁止新connect、send、subscribe和新cleanup admission。
2. **Callback ingress：** 停止接收新回调，unregister订阅/事件源；保留callback target和其代码映像，直到active callback归零。
3. **Async operation：** 取消未启动任务；对in-flight send/receive设置协作cancel并等待其完成或明确残留。
4. **Worker / poller：** 通知退出、唤醒阻塞poll/condition、等待worker退出并由外部owner join；不得持有manager/Core锁join。
5. **Protocol/session state：** 在transport仍可用且协议要求时执行有界graceful session shutdown；若不可用则记录明确失败，不伪造成功。
6. **Socket/transport handle：** 逻辑owner先原子摘除并转移至唯一close token，再执行平台适配的close；close outcome不确定时隔离descriptor identity，避免fd复用造成误关。
7. **Buffer/decoder/encoder：** 确认无worker/callback引用后释放；不得先释放仍被异步I/O引用的buffer。
8. **ROS entities/node-facing adapters：** 解除与executor关联的subscription/timer/service等，并确保callback lease归零后销毁target。
9. **Plugin lease/code image：** 所有plugin callback、custom deleter、vtable调用、线程入口和析构均不再依赖plugin image后才允许unload。
10. **CoreControlBlock / lifecycle metadata：** 最后释放Core owner与事务journal；ResidualResourceHandle存在时不得销毁其依赖的owner control block。

此序列是依赖导出的候选拓扑，不代表所有driver资源都必然按此线性顺序。实现时应以DAG表达独立步骤，并在静态审查中验证无环、所有引用边都有对应barrier。

### POSIX close特别注意

不得跨平台假设close在EINTR/错误返回时的fd状态一致。不同平台对close错误后descriptor是否仍打开的语义可能不同。必须建立平台适配层并查阅目标OS文档；不能在通用逻辑中对同一整数fd盲目重试close，否则descriptor可能已释放并被复用，导致关闭无关资源。推荐将逻辑handle先标记CLOSING并从可用资源表摘除；close结果按平台策略进入CLOSED或OUTCOME_UNKNOWN，UNKNOWN期间不重新暴露fd数值。

## 7. C++接口草案（非实现）

```cpp
struct StepClaim {
  CleanupTransactionId transaction;
  std::uint32_t step_id;
  std::uint64_t attempt_token;
  std::uint64_t expected_revision;
};

class ICleanupBackend {
public:
  virtual ~ICleanupBackend() = default;
  virtual StepOutcome execute(const StepClaim&) = 0;
  virtual ProbeOutcome probe(const StepClaim&) = 0;
};

class CleanupTransaction {
public:
  ClaimResult claim_next();
  CommitResult commit(const StepClaim&, const StepOutcome&);
  ReconcileResult reconcile(const StepClaim&, const ProbeOutcome&);
  CleanupJournalSnapshot snapshot() const;
};
```
接口语义约束：
- backend调用在所有内部锁释放后执行；
- commit只接受当前token与revision；
- backend必须对每个step声明是否可能在返回错误时已产生副作用；
- destructor不得隐式执行阻塞native cleanup；
- transaction销毁不等于resource owner释放，owner由显式owner slot管理；
- StepOutcome不能携带裸Core指针作为跨线程身份。

## 8. 验收矩阵（全部NOT_RUN）

| ID | 场景 | 断言 | 状态 |
|---|---|---|---|
| TX-IDEM-01 | 同一key重复disconnect | 返回同一事务，不重复close | NOT_RUN |
| TX-IDEM-02 | SUCCEEDED step再次调度 | backend调用次数不增加 | NOT_RUN |
| TX-IDEM-03 | FAILED_RETRYABLE重试 | 仅该step重跑，成功步骤不重跑 | NOT_RUN |
| TX-IDEM-04 | OUTCOME_UNKNOWN | 禁止盲目重复native close | NOT_RUN |
| TX-IDEM-05 | 两worker同时claim同一步骤 | 只有一个token获准 | NOT_RUN |
| GEN-FENCE-01 | 旧generation迟到completion | 不修改新generation | NOT_RUN |
| GEN-FENCE-02 | fd数值被系统复用 | 旧transaction不关闭新fd | NOT_RUN |
| GEN-FENCE-03 | plan revision更新 | 旧revision提交被拒绝 | NOT_RUN |
| GEN-FENCE-04 | generation计数接近上限 | 不发生静默wrap | NOT_RUN |
| PART-REC-01 | 前两步成功、第三步可重试失败 | 只恢复第三步 | NOT_RUN |
| PART-REC-02 | step outcome unknown | 进入隔离并先probe | NOT_RUN |
| PART-REC-03 | 依赖step失败 | 后继step保持blocked | NOT_RUN |
| PART-REC-04 | retry预算耗尽 | owner保留且报告residual | NOT_RUN |
| CLOSE-ORD-01 | callback仍active | 不销毁callback target/plugin image | NOT_RUN |
| CLOSE-ORD-02 | worker仍引用buffer | 不释放buffer | NOT_RUN |
| CLOSE-ORD-03 | poller阻塞 | wake、退出、join后才close依赖资源 | NOT_RUN |
| CLOSE-ORD-04 | POSIX close返回EINTR/错误 | 按目标平台策略处理，不盲目重试 | NOT_RUN |
| CLOSE-ORD-05 | ROS entity teardown | callback drain前不释放target | NOT_RUN |
| CLOSE-ORD-06 | plugin unload | callback/deleter/vtable/线程入口无残留 | NOT_RUN |
| CLOSE-ORD-07 | ResidualResourceHandle持有 | Core owner不提前析构 | NOT_RUN |
| CLOSE-ORD-08 | cleanup中途进程shutdown | journal snapshot保留已完成步骤 | NOT_RUN |
| CLOSE-ORD-09 | 重复close/free/unregister | 无double free/double close | NOT_RUN |
| CLOSE-ORD-10 | native close结果不可探测 | 隔离资源身份并报告UNKNOWN | NOT_RUN |

## 9. 实施门禁与待决策项

建议实施顺序：
1. 确认实际SocketV2资源清单、所有权图和平台close语义；
2. 固定transaction identity、step journal与generation fencing；
3. 以scripted backend验证幂等和partial recovery；
4. 以fake clock/manual executor验证deadline与shutdown交错；
5. 在目标OS上验证native close错误语义；
6. 进行ASan/UBSan/TSan、fd leak、double-close与fault injection；
7. ROS component/plugin unload集成；
8. ROS 2 Control、VAL3/CS9、SIL/HIL、FAT/SAT和实机门禁。

待决策：journal是否需要进程崩溃持久化；各native close API错误结果可否探测；graceful protocol shutdown预算；ROS entity与transport资源的真实依赖图；Core generation的分配/溢出策略；每step retry policy与error taxonomy。

## 10. 状态与下一节点

- **已完成：** cleanup transaction身份、step状态机、幂等分类、generation fencing、partial-step recovery、native resource依赖图与候选close顺序。
- **未完成：** 事务journal、backend、reconciliation、平台close adapter及资源DAG均未实现。
- **验收状态：** TX-IDEM-01至05、GEN-FENCE-01至04、PART-REC-01至04、CLOSE-ORD-01至10全部NOT_RUN。
- **未执行：** C++17编译、CMake、gtest、fake backend、fault injection、fd leak/double-close检查、ASan/UBSan/TSan、ROS component/plugin集成、ROS 2 Control、VAL3/CS9、SIL/HIL、FAT/SAT或实机测试。
- **上游边界：** 未修改固定上游、未创建/应用/合并PR；`TODO-EXT-001`仍未授权。
- **历史同步：** 第21章TaskPlan正文仍存在§9.3.281–§9.3.294逐节点同步缺口；本轮不伪造回填。
- **下一节点：** §9.3.300 / SERVO-883：SocketV2 cleanup dependency DAG validation、platform-specific native close semantics evidence matrix 与 residual resource reconciliation policy。
