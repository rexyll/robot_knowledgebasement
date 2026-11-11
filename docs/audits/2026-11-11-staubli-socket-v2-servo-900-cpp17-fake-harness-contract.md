# Stäubli SERVO-900：C++17 Deterministic Fake Harness 契约与 Target 隔离规范

- 节点：§9.3.317 / SERVO-900
- 审查日期：2026-11-11
- 仓库分支：`main`
- 知识库基线：`35284fed5c32a68a8a3b1b2d32e66c64cdb1ce8d`
- 固定上游审查基线：`ICube-Robotics/staubli_driver_ros2@bd658e2d266e315d2ee35f985fb352ea88306b79`
- 范围：仅知识库侧接口契约、target边界和静态策略；不修改上游driver，不实现或运行真实Fake Harness，不启动A1.1。

## 1. 决策摘要

本节点把SERVO-898的抽象Fake Harness概念收敛为C++17接口草案和构建隔离要求。接口仅作为未来实现的设计输入，不宣称已存在可编译库。

核心约束：

1. Fake Harness只能存在于显式启用的test-only target及测试二进制中。
2. Production target不得链接、安装、导出或公开Fake实现、FaultScript、DeterministicExecutor或测试控制接口。
3. Fake与production可共享状态机/算法实现，但必须通过窄的clock/executor/backend seam注入依赖；不得复制两套生命周期状态机。
4. 所有调度、推进和故障触发必须由测试显式驱动；不得用sleep、随机延迟或真实墙钟等待来制造竞态。
5. 拒绝、取消、shutdown与失败残留必须可观测；不得把“任务已请求取消”解释为“任务已停止”。
6. 当前仅有接口草案与静态验收条款；C++编译、gtest、TSan/ASan及ROS/插件运行仍为NOT_RUN。

## 2. Target 隔离契约

建议未来构建图（名称为规范性占位，不代表当前仓库已有这些target）：

- `staubli_socket_core`：production核心；仅链接production依赖。
- `staubli_socket_test_support`：仅在`BUILD_TESTING`下创建；包含FakeClock、Barrier/Latch、DeterministicExecutor、FaultInjector和测试适配器。
- `staubli_socket_unit_tests`：仅链接test_support与被测核心。
- `staubli_driver_plugin`：production plugin；不得链接test_support。

### 2.1 CMake 约束草案

```cmake
# Illustrative contract only; not applied to the upstream project.
add_library(staubli_socket_core ...)
target_compile_features(staubli_socket_core PUBLIC cxx_std_17)

if(BUILD_TESTING)
  add_library(staubli_socket_test_support STATIC
    test/fakes/fake_clock.cpp
    test/fakes/deterministic_barrier.cpp
    test/fakes/deterministic_executor.cpp
    test/fakes/fault_injector.cpp)
  target_compile_features(staubli_socket_test_support PUBLIC cxx_std_17)
  target_link_libraries(staubli_socket_unit_tests PRIVATE
    staubli_socket_core staubli_socket_test_support)
endif()

# Forbidden:
# target_link_libraries(staubli_driver_plugin PRIVATE staubli_socket_test_support)
# install(TARGETS staubli_socket_test_support ...)
# ament_export_targets(staubli_socket_test_support ...)
```

必须满足：
- test support仅在`BUILD_TESTING=ON`时定义；OFF配置中target不存在。
- Fake头文件不得进入production install include目录或ament export set。
- production target的LINK_LIBRARIES/INTERFACE_LINK_LIBRARIES闭包不得包含test support及其任何传递依赖。
- plugin链接图不得出现Fake、FaultInjector、DeterministicExecutor或测试专用宏。
- 测试专用编译定义不得传播到production target；禁止通过全局`add_compile_definitions`污染生产目标。
- 不得通过安装目录、导出target、公共头文件、插件XML或运行时注册表间接暴露test support。
- CI应分别生成BUILD_TESTING=OFF与ON的target graph，并检查production target闭包、install manifest、ament export和plugin依赖；静态grep不能代替真实CMake生成结果。

## 3. C++17 API 草案

以下签名用于冻结语义，不是已提交的头文件或已验证的ABI。实现可调整命名，但不得削弱行为约束。

### 3.1 FakeClock

```cpp
namespace staubli::testing {
using Tick = std::chrono::nanoseconds;
class FakeClock final {
public:
  explicit FakeClock(Tick initial = Tick{0});
  Tick now() const noexcept;
  void advance(Tick delta);       // delta must be >= 0; overflow fails closed
  void set_for_test(Tick value);  // only before any observer is registered
};
}
```

契约：
- 仅表示单调逻辑时间，不伪装为`std::chrono::steady_clock`的真实时钟源。
- advance仅允许非负增量；负数和溢出必须返回明确错误或抛出文档化异常。
- 读操作线程安全；推进操作必须串行化并产生可追踪事件。
- 生产代码不得直接依赖FakeClock类型；通过窄Clock interface/模板参数在test seam注入。
- 禁止回拨时间；禁止以FakeClock推进隐式触发未登记的任意回调。

### 3.2 DeterministicBarrier / Latch

```cpp
namespace staubli::testing {
enum class WaitResult { released, cancelled, timed_out, invalid };
class DeterministicBarrier final {
public:
  explicit DeterministicBarrier(std::size_t participants);
  bool arrive(std::string participant_id);
  bool release();                 // succeeds only after all participants arrive
  void cancel() noexcept;
  WaitResult wait_for_release();  // test scheduler controlled; no wall-clock sleep
};
class DeterministicLatch final {
public:
  explicit DeterministicLatch(std::size_t count);
  bool count_down(std::string participant_id);
  WaitResult wait();
  void cancel() noexcept;
};
}
```

契约：
- participant ID非空且唯一；重复到达不得重复计数。
- release/count达到零之前不得提前唤醒；release/cancel只能终态一次。
- 取消后所有等待者得到cancelled；对象销毁前必须确认等待者退出。
- 不允许以真实时间超时作为竞态编排手段；若外部测试框架提供watchdog，只能作为死锁保护，不得决定测试顺序。
- 参与者集合、到达顺序、释放事件均进入Event Trace。

### 3.3 DeterministicExecutor

```cpp
namespace staubli::testing {
using TaskId = std::uint64_t;
enum class SubmitResult { accepted, rejected_shutdown, rejected_capacity, invalid };
enum class TaskState { queued, running, completed, cancelled, failed };
class DeterministicExecutor final {
public:
  SubmitResult submit(TaskId id, std::function<void()> task);
  bool run_one();                 // executes exactly one accepted queued task
  std::size_t run_until_idle(std::size_t max_steps);
  bool cancel(TaskId id);
  void begin_shutdown() noexcept;
  bool finish_shutdown();         // true only when no queued/running task remains
  TaskState state(TaskId id) const;
};
}
```

契约：
- 任务ID非零且唯一；重复ID拒绝。
- submit与shutdown线性化：shutdown开始后新任务必须拒绝。
- 容量有界；容量满时明确返回rejected_capacity，不得静默丢弃。
- cancel只对尚未开始的queued任务成功；running任务取消结果必须明确为不可取消/协作式请求，不能伪报已停止。
- run_one只执行一个已接受任务；异常必须记录为failed并继续维持executor可观测状态。
- finish_shutdown仅当queued=0且running=0时成功；不得detach worker或隐藏未完成任务。
- 每次accept/reject/start/complete/fail/cancel/shutdown均写入事件记录。

### 3.4 FaultInjector

```cpp
namespace staubli::testing {
struct FaultRule {
  std::string fault_id;
  std::string target;
  std::string trigger_event;
  std::uint64_t occurrence;       // 1-based
  std::string outcome;
};
class FaultInjector final {
public:
  explicit FaultInjector(std::vector<FaultRule> immutable_rules);
  std::optional<std::string> on_event(
      std::string_view target, std::string_view event,
      std::uint64_t occurrence);
  const std::vector<FaultRule>& rules() const noexcept;
};
}
```

契约：
- 构造后规则不可变；同一输入事件序列必须产生相同注入结果。
- fault_id唯一；target/event/outcome非空；occurrence从1开始。
- 默认不注入；未匹配规则不改变执行流。
- 规则冲突必须在构造时拒绝，不允许依赖容器遍历顺序决定注入结果。
- 注入事件必须记录fault_id、target、trigger、occurrence、outcome及关联attempt/generation。
- 不允许注入器直接释放资源或绕过被测状态机；它只能返回预定义故障结果，由被测代码走正常错误路径。

## 4. 统一并发与生命周期约束

- 所有异步动作必须有稳定task/event ID及generation/revision/attempt-token上下文。
- 所有barrier等待都必须有明确参与者和释放/取消终态。
- executor shutdown不得在queued/running任务仍存在时报告STOPPED。
- 资源释放与测试调度分离；Fake不得持有或释放生产native handle。
- FaultInjector不得改变唯一Owner、CleanupCoordinator或generation fencing规则。
- 对未知native handle、callback、worker、remote session状态必须保留UNKNOWN/RESIDUAL，不得由测试框架自动归零。
- Event Trace采用单调sequence和逻辑时间；同一输入脚本要求可重复事件顺序。

## 5. 最小验收矩阵

| ID | 验收项 | 静态/规格状态 | 编译/运行状态 |
|---|---|---|---|
| TARGET-ISO-01 | test support仅在BUILD_TESTING时存在 | SPECIFIED | NOT_RUN |
| TARGET-ISO-02 | production target依赖闭包零Fake依赖 | SPECIFIED | NOT_RUN |
| TARGET-ISO-03 | install/ament export无test support | SPECIFIED | NOT_RUN |
| TARGET-ISO-04 | plugin依赖图零Fake/FaultInjector | SPECIFIED | NOT_RUN |
| CLOCK-01 | FakeClock单调推进、拒绝回拨/溢出 | SPECIFIED | NOT_RUN |
| BARRIER-01 | 全员到达前不可release，重复参与者拒绝 | SPECIFIED | NOT_RUN |
| BARRIER-02 | cancel唤醒全部等待者且可证明退出 | SPECIFIED | NOT_RUN |
| EXEC-API-01 | submit/shutdown线性化与有界拒绝 | SPECIFIED | NOT_RUN |
| EXEC-API-02 | cancel/complete/fail状态准确且无隐式丢弃 | SPECIFIED | NOT_RUN |
| EXEC-API-03 | queued/running清零前不得finish_shutdown | SPECIFIED | NOT_RUN |
| FAULT-01 | 规则不可变、冲突拒绝、触发确定性 | SPECIFIED | NOT_RUN |
| TRACE-01 | 事件记录包含task/generation/revision/attempt | SPECIFIED | NOT_RUN |

## 6. 最小编译验证方案（尚未执行）

未来在获准的独立test harness实现中，至少应执行：
1. C++17 standalone header self-containment compile：每个Fake public test header单独include。
2. BUILD_TESTING=OFF配置：确认test-support target不存在且production target可配置/构建。
3. BUILD_TESTING=ON配置：确认测试target可构建，production plugin依赖闭包不变。
4. install-space检查：Fake headers/targets不安装、不导出。
5. consumer fixture：仅链接production install-space，不能解析Fake symbols/headers。
6. gtest正向与负向测试；之后再执行TSan/ASan与ROS/plugin生命周期测试。

当前没有新增C++源码、CMake target或gtest用例，因此以上全部为NOT_RUN；本节点的文档交付不得被描述为compile PASS。

## 7. 风险与开放问题

- 现有上游Socket接口与private seam如何接入仍需在授权后基于固定commit设计；本节点不改变既有public ABI。
- Fake时钟如何被Asio timer等第三方时间源消费，必须先设计可注入timer adapter；不能声称只替换now()就能控制Asio内部定时器。
- Barrier wait API需要未来选定具体调度模型；本文禁止wall-clock编排，但不规定生产线程原语的具体实现。
- executor是否inline/queued应作为测试配置，不得让inline执行语义泄漏到production executor。
- FaultInjector规则的序列化格式与Evidence Bundle字段映射需后续节点细化。

## 8. 结论与下一节点

SERVO-900完成的是接口语义和target隔离规格，不是C++实现。TARGET-ISO、CLOCK、BARRIER、EXEC、FAULT各项均为SPECIFIED；所有C++编译、gtest、TSan/ASan、ROS、plugin及硬件运行仍NOT_RUN。

下一节点 §9.3.318 / SERVO-901：建立Fake Harness C++ header草案的独立编译与target-graph静态验收设计，包括header自包含、test-only target install/export泄漏扫描、BUILD_TESTING双配置对照和production dependency closure报告；仅在知识库侧定义/验证工具，不触碰上游driver，不启动A1.1。
