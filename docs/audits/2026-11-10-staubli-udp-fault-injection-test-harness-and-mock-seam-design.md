# 2026-11-10 Stäubli UDP 故障注入测试夹具与 Mock Socket seam 架构设计

> 节点：§9.3.284 / SERVO-867。测试架构与验证规格，不是代码实现或测试报告。  
> Stäubli 固定基线：`ICube-Robotics/staubli_driver_ros2@bd658e2d266e315d2ee35f985fb352ea88306b79`  
> ros2_control 参考：Jazzy `ros-controls/ros2_control@c6ef5a24e0cd21463edb99bded552a96f914b716`

## 1. 目标与边界

为 §9.3.282–283 已识别的 UDP 发送结果、接收帧接纳、连接 generation、freshness 与生命周期故障恢复缺口，设计可重复、无真实 CS9 依赖的确定性测试夹具。

本报告只定义测试边界、接口 seam、fixture 结构、注入场景、时钟和证据格式。**不修改 Stäubli 上游，不实现生产代码，不声称任何测试已执行。** 下列接口名称均为建议的测试架构，不代表固定上游已经存在这些抽象。

测试分层：
1. 纯单元测试：序列化、帧头、长度、字段、序号、freshness、发送结果映射。
2. Socket adapter 测试：真实 loopback UDP + 可控发送/接收故障适配器。
3. RobotDriver 集成测试：状态缓存、generation、session validation、错误锁存。
4. ROS 2 Control 集成测试：HardwareComponent、ResourceManager、ControllerManager 生命周期与接口撤销。
5. 系统验证：SIL、VAL3/CS9、HIL、FAT/SAT、实机。前四层通过不替代第五层。

## 2. 推荐测试架构

```text
TestCase
  ├── ManualTestClock (steady/manual clock)
  ├── FaultScenario (deterministic event script)
  ├── RawDatagramBuilder / ProtocolFrameBuilder / RobotStateBuilder
  ├── MockUdpTransport OR LoopbackUdpTransport
  │     ├── SendResult injection
  │     ├── Receive completion injection
  │     └── Endpoint / datagram boundary injection
  ├── RobotDriver under test
  │     ├── StateAdmission
  │     ├── ConnectionGeneration
  │     ├── StateSnapshot
  │     └── FaultLatch / StopAttemptRecord
  ├── ROS 2 Control integration fixture (later layer)
  └── EvidenceRecorder
        ├── inputs + expected outcome
        ├── observed result + counters
        ├── logs + timing trace
        └── source/build/test environment manifest
```

测试必须控制时间、输入数据、socket 结果和回调顺序；不得依赖真实网络拥塞、操作系统调度时机或墙上时钟碰运气复现故障。

## 3. Socket seam 设计

### 3.1 最小抽象

建议在 UDP socket 使用处引入窄接口：

```cpp
struct Endpoint { Address address; uint16_t port; };

enum class SendDisposition { NOT_SENT, LOCAL_ACCEPTED, UNKNOWN };

struct SendOutcome {
  SendDisposition disposition;
  std::error_code error;
  size_t bytes_transferred;
};

struct ReceiveEvent {
  Endpoint sender;
  std::span<const uint8_t> datagram;
  std::error_code error;
  uint64_t connection_generation;
};

class IUdpTransport {
public:
  virtual ~IUdpTransport() = default;
  virtual SendOutcome send(
    std::span<const uint8_t> datagram,
    const Endpoint& destination) = 0;
  virtual void start_receive(ReceiveHandler handler) = 0;
  virtual void cancel_receive() = 0;
  virtual void close() = 0;
};
```

约束：
- 生产 adapter 只负责 Asio 与 OS socket 语义映射；不负责控制器 ACK、机器人运动状态或安全确认。
- Mock adapter 只实现确定性注入；不得在测试中复制一份生产算法来“证明”生产算法正确。
- 业务层依赖接口而非具体 socket；seam 尽量小，避免把整个 Asio API 暴露给 RobotDriver。
- `LOCAL_ACCEPTED` 必须对应系统调用无错误且完整 datagram 字节数；`would_block` 映射为 `NOT_SENT`；异常/无法判断映射为 `UNKNOWN`。
- 发送端和接收端都传递 endpoint、generation 与错误码。
- 若短期无法重构，可先使用现有 socket wrapper 的构造注入/函数对象 seam；禁止为测试大量增加 public API。

### 3.2 两种传输 fixture

| Fixture | 适用范围 | 优点 | 限制 |
|---|---|---|---|
| `MockUdpTransport` | 单元与确定性集成测试 | 精确控制 send disposition、错误码、回调顺序、endpoint、generation | 不验证 OS/Asio 行为 |
| `LoopbackUdpTransport` | adapter 与协议集成测试 | 验证真实 UDP 编码、端口、datagram 边界、收发接线 | 无法稳定制造真实 would_block/丢包 |

两者组合使用，不以其中一种取代另一种。

## 4. 确定性故障脚本

建议采用有序事件脚本；每个事件明确触发点和预期观察，不使用 sleep 作为同步机制：

```cpp
struct FaultStep {
  Event trigger;            // SendCall(3), ReceiveCall(5), AdvanceClock(20ms)
  InjectedOutcome outcome;  // would_block, io_error, malformed_datagram
  ExpectedObservation expected;
};
```

脚本事件：
- `SendCall(n)`：第 n 次发送返回 NOT_SENT / LOCAL_ACCEPTED / UNKNOWN。
- `ReceiveCall(n)`：注入合法帧、短帧、错误 endpoint、重复/乱序帧或异步错误。
- `DeliverCallback(generation)`：控制回调投递次序，复现 disconnect 后迟到回调。
- `AdvanceClock(duration)`：推进单调时钟，不等待真实时间。
- `Disconnect()` / `Reconnect()`：显式改变连接 generation。
- `InvokeLifecycle(callback)`：安排 configure/activate/deactivate/cleanup/error 回调。
- `ConcurrentBarrier(name)`：在明确屏障位置协调线程，不以概率竞争替代确定性竞态测试。

测试断言覆盖返回值、状态快照、generation、sequence、timestamp、计数器、日志事件和调用次数；只断言“没有崩溃”不够。

## 5. 可控时钟与 freshness 测试

建议业务层依赖只读单调时钟：

```cpp
class IMonotonicClock {
public:
  using time_point = std::chrono::steady_clock::time_point;
  virtual time_point now() const noexcept = 0;
};
```

`ManualTestClock` 初始时间可固定，通过 `advance(Δt)` 推进；不允许回拨。墙上时钟只用于证据记录，不参与 stale 判定。

必要测试：
1. 首个合法帧建立时间戳；重复帧不得刷新。
2. 非法 endpoint、错误帧头、解析失败、重复/乱序帧均不得刷新。
3. 推进到 stale threshold 前后，状态有效性精确转换。
4. 断开后旧 generation 回调即使携带较新时间戳也不能提交。
5. reconnect 后新 generation 在首帧验证前保持 invalid。
6. 时间阈值边界（阈值前一 tick、恰好阈值、阈值后一 tick）定义明确。
7. 使用 duration/tick 比较，不依赖 wall clock、NTP 或时区。

## 6. Datagram 与消息构造器

分离三层 builder：
- `RawDatagramBuilder`：任意 bytes、长度、截断、尾随垃圾、header 字节扰动。
- `ProtocolFrameBuilder`：合法 magic/version/type/payload_size/sequence 组合；可单独覆写字段。
- `RobotStateBuilder`：合法状态 payload、枚举边界、valid flags、有限/非有限浮点数、物理范围边界。

每个 builder 支持从合法基准帧仅改变一个目标字段、显式设定 sequence/type/endpoint/generation、生成 golden byte vector、保存负向用例输入摘要。不得臆测 CS9 私有协议字段；协议字段与数值范围须来自固定源码或正式规格。Fuzzing 作为补充，固定 seed、限制时间/输入长度并保存失败 seed；不得替代确定性边界测试。

## 7. 并发与回调代次测试

使用屏障和可控 executor，而不是 `sleep_for`：

| 用例 | 事件顺序 | 断言 |
|---|---|---|
| H-01 | receive callback 已排队 → disconnect → callback 执行 | 旧 generation 不得提交 |
| H-02 | callback 进入 → generation invalidation → callback commit | commit 原子失败 |
| H-03 | read snapshot 与新帧 commit 并发 | 只看到完整旧快照或完整新快照 |
| H-04 | disconnect 与 cancel completion 并发 | 不重复关闭、不复活 receive loop |
| H-05 | 两个 lifecycle 操作并发 | 串行化或明确拒绝，无未定义行为 |
| H-06 | 故障锁存与有效帧同时发生 | 新帧不能清除故障锁存/授权恢复 |
| H-07 | send 与 close 并发 | 结果确定分类，不访问已释放 socket |

TSan/ASan 属于后续执行层证据，不是设计阶段的通过证据；屏障测试也不能取代压力测试与 sanitizer。

## 8. ROS 2 Control 集成夹具

后续集成层应装载真实 Stäubli HardwareInterface 插件（或测试专用 plugin fixture），并连接固定版本 Jazzy ResourceManager/ControllerManager；不得用纯 mock 代替框架本身来宣称生命周期联调完成。

最低场景：
- read/write ERROR 后 HardwareComponent 的 error/on_error 状态结果；
- ResourceManager 确认接口撤销，controller command/state interface 可用性变化；
- ControllerManager mode-switch prepare 失败及 perform 调用路径/短路行为；
- UNCONFIGURED 再 configure、FINALIZED unload/reload；
- reconnect 首帧/session validation 前不得 activate；
- 故障锁存未解除时，即使收到合法新帧也不得恢复运动；
- STOP send NOT_SENT / UNKNOWN 不得报告控制器停止确认。

每项保存实际状态枚举、接口列表、controller lifecycle state、日志和精确 ROS 2/ros2_control 二进制版本。

## 9. 测试分组与优先级

| Group | 内容 | 优先级 | 前置条件 |
|---|---|---|---|
| UT-TX | send disposition、would_block、完整 datagram 长度 | P0 | IUdpTransport seam |
| UT-RX | endpoint、length、header、field、sequence admission | P0 | builder + admission unit |
| UT-TIME | freshness、manual clock、stale boundary | P0 | IMonotonicClock |
| UT-GEN | generation、late callback、atomic snapshot | P0 | deterministic executor |
| UT-THREAD | close/cancel/read/write/lifecycle concurrency | P1 | barriers + sanitizer |
| IT-UDP | Asio loopback adapter、实际 datagram 交互 | P1 | socket adapter |
| IT-DRIVER | RobotDriver、状态缓存与错误锁存 | P1 | mock transport + clock |
| IT-ROS2 | HardwareComponent/ResourceManager/ControllerManager | P1 | 固定 Jazzy 运行环境 |
| SYS-SIL | 控制器/机器人软件在环 | P1 | 已批准的安全仿真环境 |
| SYS-CS9 | VAL3/CS9/HIL/FAT/SAT/实机 | P0 safety gate | 厂商接口、风险评估、现场安全程序 |

P0 是后续实施/评审阻断要求，不代表当前测试已通过。

## 10. 证据归档规范

每次运行创建不可覆盖的 run directory：

```text
test-evidence/
  SERVO-867/
    <run-id>/
      manifest.yaml
      test-results.xml
      stdout.log
      stderr.log
      event-trace.jsonl
      inputs/
        datagrams/
        fault-scripts/
      environment/
        git-revisions.txt
        ros-distro.txt
        package-versions.txt
        compiler-and-flags.txt
      artifacts/
        sanitizer/
        packet-capture/
        core-dumps/
      verdict.md
```

manifest 记录 test ID、层级、预期/实际结果、PASS/FAIL/NOT_RUN、仓库与上游 commit、OS/ROS/RMW/编译器/依赖精确版本、构建选项、seed、clock 推进序列、故障脚本、输入 datagram hash、命令、退出码、日志路径、执行者/审查者与偏差。

未执行统一标记 `NOT_RUN`，不得将设计完成写成 PASS。失败重跑必须产生新 run-id，不覆盖旧证据。环境或源码变化后旧证据不自动适用。packet capture/core dump 归档前执行访问控制与脱敏。

## 11. 实施顺序与退出条件

1. 在独立测试分支实现窄 `IUdpTransport` 与 `IMonotonicClock` seam，保持生产行为不变。
2. 为现有 socket wrapper 写 adapter contract tests。
3. 实现纯函数帧校验/序号接纳单测，再连接 RobotDriver 状态缓存。
4. 加入 generation 与 callback executor 屏障测试。
5. 执行 UT-TX/UT-RX/UT-TIME/UT-GEN，再执行 UT-THREAD 与 sanitizer。
6. 执行 loopback UDP adapter、RobotDriver 集成。
7. 执行真实 ROS 2 Control ResourceManager/ControllerManager 集成。
8. SIL/CS9/HIL/FAT/SAT 另立安全验证计划和现场授权，本报告不自动授权。

退出条件：P0 单测全部有可追溯 PASS；P1 集成测试逐项有结果；未解决缺陷有风险接受人与缓解措施；ROS 2 二进制版本锁定；独立安全链与恢复授权经责任工程师批准。即便如此，也只代表对应测试层级通过，不自动代表实机安全或产品认证。

## 12. 本轮状态

- 测试架构、Mock Socket seam、Manual Clock、确定性故障脚本、builder、并发屏障、ROS 2 Control 集成层和证据目录规范：设计完成。
- 尚未实现 `IUdpTransport`、`IMonotonicClock`、Mock/Loopback adapter 或测试夹具。
- 所有 UT/IT/SYS 测试：`NOT_RUN`。
- 未运行构建、单测、集成测试、TSan/ASan、SIL/HIL、VAL3/CS9、FAT/SAT 或实机测试。
- 未修改 Stäubli/ros2_control 上游，未应用或合并 PR；`TODO-EXT-001`仍未授权。
- ROS/UDP STOP 不是安全功能；本地 UDP 发送接受不代表 CS9 收到或机械臂停止。

## 13. 下一节点

**§9.3.285 / SERVO-868：将 Mock Socket seam 与 Manual Clock 映射到现有 CMake/gtest 测试结构，制定最小增量实施方案。** 下一节点先核对固定提交中的 CMakeLists、测试注册和构造依赖，列出可无行为变更引入的接口边界与文件级实施顺序；未经授权仍不修改 Stäubli 上游。
