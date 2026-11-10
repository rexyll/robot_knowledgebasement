# 2026-11-10 Stäubli CMake/gtest 测试结构与最小 seam 增量实施方案

> 节点：§9.3.285 / SERVO-868。固定提交静态文件审查与实施计划；不是上游代码修改，也不是测试执行报告。  
> Stäubli 固定基线：`ICube-Robotics/staubli_driver_ros2@bd658e2d266e315d2ee35f985fb352ea88306b79`

## 1. 结论摘要

固定提交已经具备可复用的通信抽象：`staubli_robot_driver/communication/socket.hpp` 中的 `Socket` 是纯虚接口，涵盖连接、发送、一次接收、异步接收线程启停。因此，第一阶段不应另造一个平行的 `IUdpTransport` 并大规模改写 Asio；更小的 seam 是把现有 `Socket` 注入 `RobotDriver`，用 FakeSocket 实现确定性发送/接收故障。

但 `RobotDriver` 当前只有默认构造函数，构造体内直接通过 `SocketFactory::create(UDP)` 创建 control 与 diagnostics sockets。真正的阻碍是构造依赖无法替换，而不是缺少 Socket 抽象。

时间 seam 需覆盖 `RealTimeSocketSubscriber`：`src/real_time_socket_subscriber.cpp` 在接收回调和读取时分别直接构造 `rclcpp::Clock().now()`。只向 RobotDriver 注入时钟不能控制消息接收时间戳。建议先用窄 `IClock` 或可复制的时钟函数对象覆盖该订阅类，再让 RobotDriver 的连接超时使用同一时间源；不要将 ROS 时间和 steady-clock freshness 混用而不定义时钟类型。

## 2. 固定提交中确认的工程事实

### 2.1 CMake 与测试注册

`staubli_robot_driver/CMakeLists.txt`：
- C++17；主库 `staubli_robot_driver` 为 SHARED，源文件包含 `udp_socket.cpp`、`real_time_socket_subscriber.cpp`、`real_time_socket_interface.cpp`、`robot_driver.cpp` 和 `mock_robot_server.cpp`。
- 主库依赖 ROS 2、hardware_interface、pluginlib、rclcpp_lifecycle、Boost::system；Asio include 来自 `${asio_SOURCE_DIR}/asio/include`。
- `BUILD_TESTING` 下使用 `ament_cmake_gtest`，定义 `add_unit_test(TEST_NAME TEST_SOURCE)`，自动包含项目 include 并链接主库。
- 已注册 serialization、socket、real-time socket interface、RobotDriver、MockRobotServer 测试；HardwareInterface 测试单独注册并链接 hardware-interface library。
- 因此纯 Mock Socket 单测可复用 `add_unit_test`，无需引入新测试框架或新运行依赖。

### 2.2 现有 Socket seam

文件：`include/staubli_robot_driver/communication/socket.hpp`
- `Socket` 是抽象类，所有方法均为 virtual。
- `send(std::vector<uint8_t>&)` 仅返回 bool，无法区分 NOT_SENT / LOCAL_ACCEPTED / UNKNOWN；首轮 Mock 可以确定性返回 true/false，但 richer disposition 需要后续单独评估 API 兼容性。
- 接收回调只提供 buffer 与 bytes_transferred，没有 sender endpoint、error_code 或 connection generation；不能假装 Mock 已覆盖这些生产层语义。
- `SocketFactory` 是静态工厂，不是当前可替换的对象 seam。

文件：`include/.../communication/udp_socket.hpp` 与 `src/communication/udp_socket.cpp`
- `UDPSocket` 是 `Socket` 的 PIMPL wrapper。
- 实现细节在 `src/communication/udp_socket_impl.hpp`，由 `udp_socket.cpp` include；并非单独编译单元。
- 该结构允许未来在 wrapper 内部做 adapter 测试，但不适合首轮为 Mock 直接暴露 Boost.Asio 类型。

### 2.3 RobotDriver 构造依赖

文件：`include/staubli_robot_driver/robot_driver.hpp`、`src/robot_driver.cpp`
- 当前只有 `RobotDriver()`。
- 构造函数创建两个 UDP sockets，再初始化 staleness timeout 和状态。
- `connect()` 之后用 control socket 构造 `RealTimeSocketInterface<RobotStateMessage, RobotCommandMessage>`，用 diagnostics socket 构造 `RealTimeSocketSubscriber<DiagnosticDataMessage>`。
- 推荐最小注入形态：保留默认构造函数并委托到一个接收 control/diagnostics `std::shared_ptr<Socket>` 的构造函数；默认路径仍调用现有 SocketFactory，测试路径传 FakeSocket。必须拒绝 null socket，并定义对象所有权与重连后 subscriber 的销毁/重建顺序。
- 不建议将生产构造函数改成只接受任意 socket factory lambda，除非后续确实需要动态创建多个 socket；两个明确 socket 参数更易审查。

### 2.4 Subscriber 与时间依赖

文件：`include/staubli_robot_driver/real_time_socket_subscriber.hpp`、`src/real_time_socket_subscriber.cpp`
- Subscriber 构造函数接收 `std::shared_ptr<Socket>`，立即调用 `init_communication()` 并启动接收线程；因此 FakeSocket 必须能按测试脚本投递回调，并且析构时安全响应 `stop_receive_thread()`。
- `update_message()` 对成功反序列化的消息设置 `reception_timestamp = rclcpp::Clock().now()`。
- `read_message()` 再次调用 `rclcpp::Clock().now()` 计算 elapsed duration。
- 推荐最小 seam：一个只读时钟依赖注入 Subscriber；默认构造路径仍使用当前 ROS clock 行为。测试时使用 manual clock，并确保 now() 与消息 timestamp 使用兼容的 ROS clock type/time source。
- 若改用 `std::chrono::steady_clock`，应作为明确的后续语义变更评审，不能直接与 `rclcpp::Time` 相减或混用 system/ROS/sim time。

### 2.5 当前测试的可复用性和限制

- `test_sockets.cpp`：已经使用 loopback UDP socket pair，可复用为真实 UDP adapter smoke/contract tests；当前 fixture 使用固定端口，未来并行执行有端口冲突风险。
- `test_robot_driver.cpp`：已经建立 control/diagnostics loopback server，能复用协议端到端测试；但它不是确定性故障注入器。
- `test_staubli_hardware_interface.hpp`：MockRobotServer 以独立线程持续发送状态/诊断数据；适用于现有硬件接口基本路径，不等价于 ResourceManager/ControllerManager 故障生命周期集成。
- Subscriber 构造即启线程，测试 teardown 必须先停止生产者/回调，再销毁被测对象；不要让 FakeSocket 回调在对象析构后执行。

## 3. 推荐最小增量架构

第一轮只引入两个可注入依赖，不引入新的通用网络框架：

```cpp
// Illustrative interface only; not present in upstream.
class IClock {
public:
  virtual ~IClock() = default;
  virtual rclcpp::Time now() const = 0;
};

class FakeSocket final : public Socket {
  // scripted connect/send/receive/start/stop outcomes
};
```

建议实现顺序：
1. 新增 FakeSocket 测试 helper（优先放在 `test/test_helpers/`，不安装、不导出为公共库 API）。
2. 给 RobotDriver 增加双 Socket 注入构造函数，默认构造委托现有 SocketFactory；先不改变生产 socket 的类型与行为。
3. 将 clock seam 注入 Subscriber，默认行为与原先 `rclcpp::Clock().now()` 等价；把时钟依赖传递到 control 与 diagnostics subscriber。
4. 在确认所有时间戳时钟类型一致后，再覆盖 RobotDriver connect timeout；若不需要测试连接超时，则首轮不改这段代码。
5. 先写 FakeSocket contract tests，再增加 RobotDriver 发送失败/断线/接收超时测试。
6. 后续另立 adapter 层工作包，才评估把 bool send 升级为 SendOutcome、为接收事件传递 endpoint/error/generation；此类 API 变更不属于“无行为变更”的首轮 seam。

## 4. 文件级变更建议（未来获批实施，不是本轮修改）

| 文件 | 最小改动建议 | 首轮是否必要 |
|---|---|---|
| `include/staubli_robot_driver/robot_driver.hpp` | 声明双 Socket 注入构造函数；保留默认构造 | 是 |
| `src/robot_driver.cpp` | 默认构造委托 SocketFactory；注入构造保存依赖 | 是 |
| `include/staubli_robot_driver/real_time_socket_subscriber.hpp` | 声明时钟依赖/默认时钟策略 | 是（freshness 确定性测试需要） |
| `src/real_time_socket_subscriber.cpp` | 将两处直接 clock 构造替换为依赖调用 | 是（同上） |
| `test/test_helpers/fake_socket.hpp/.cpp` | 实现可脚本化 Socket fake | 是 |
| `test/unit_tests/test_robot_driver_fault_injection.cpp` | send false、connect fail、接收回调、重连场景 | 是 |
| `test/unit_tests/test_subscriber_clock.cpp` | manual clock、freshness 边界、重复读取 | 是 |
| `CMakeLists.txt` | 用既有 `add_unit_test` 注册新增测试 | 是 |
| `udp_socket.hpp/.cpp`、`udp_socket_impl.hpp` | 仅在后续 adapter contract 阶段调整 | 否 |
| `real_time_socket_interface.*` | 只有当 send outcome 需要跨层传播时再改 | 否 |
| `staubli_hardware_interface.*` | 本轮不改；真实 RM/CM 集成另行规划 | 否 |

实现前必须检查实际构造、复制、模板显式实例化和 ABI 约束；表中是拟议路径，不是对上游源码的修改承诺。

## 5. 首轮测试矩阵（设计，全部 NOT_RUN）

| ID | 层级 | 注入 | 预期断言 |
|---|---|---|---|
| SEAM-01 | 单测 | 默认 RobotDriver 构造 | 仍创建两个 UDP Socket，行为兼容 |
| SEAM-02 | 单测 | 注入两个 FakeSocket | control/diagnostics 通道分别使用指定对象 |
| SEAM-03 | 单测 | control socket null | 明确拒绝/抛出定义好的异常，不进入半初始化状态 |
| SEAM-04 | 单测 | diagnostics socket null | 同上 |
| FS-01 | RobotDriver | control connect false | connect 失败，不启动 subscriber |
| FS-02 | RobotDriver | diagnostics connect false | control socket 被正确回滚断开 |
| FS-03 | RobotDriver | send false | command/STOP 上层返回失败，不记录为已发送 |
| FS-04 | RobotDriver | 接收线程启动失败 | connect 失败且已建立 socket 被清理 |
| CLK-01 | Subscriber | manual clock t0 投递有效帧 | reception timestamp=t0 |
| CLK-02 | Subscriber | t0 读取、推进阈值前一 tick | 状态 freshness 符合阈值定义 |
| CLK-03 | Subscriber | 推进到阈值及后一 tick | stale 判定边界确定 |
| CLK-04 | Subscriber | 无新帧重复读取 | 时间差随 clock 推进；不伪造新帧 |
| CLK-05 | Subscriber | 析构与回调排队竞态 | stop/join 后无 use-after-free |
| IT-UDP-01 | Adapter | loopback socket pair | 实际 datagram 边界与序列化兼容 |

所有测试必须记录 PASS/FAIL/NOT_RUN；首轮 seam 只验证可注入性，不覆盖真实 CS9 协议完整性或 ROS 2 Control 组件错误传播。

## 6. CMake/gtest 最小注册方案

沿用既有 helper：

```cmake
add_unit_test(test_robot_driver_fault_injection
  test/unit_tests/test_robot_driver_fault_injection.cpp)

add_unit_test(test_subscriber_clock
  test/unit_tests/test_subscriber_clock.cpp)
```

若 FakeSocket 只由一个测试使用，可先做 header-only helper，避免增加测试 helper library 的链接复杂度；多个测试复用后再考虑单独 test-support target。不得把 FakeSocket 安装或导出为产品 API。

现有 HardwareInterface 测试目标单独链接硬件接口库，首轮 RobotDriver/Subscriber tests 不应无必要地链接 `staubli_robot_driver_hardware_interface`。

## 7. 风险与决策门

- `Socket::send` 仍为 bool：Mock 可测失败传播，但无法区分本地接受与未知发送结果。后续应评估向上兼容的 richer result API。
- 接收回调不暴露 endpoint/error/generation：当前 FakeSocket 不能验证生产 UDP adapter 的来源校验和迟到 callback 语义；需要独立 adapter seam。
- Subscriber 构造时启动线程：对象析构、Fake 回调和生命周期管理需明确；测试不能以 sleep 代替同步屏障。
- `rclcpp::Clock().now()` 的默认 clock type 与 ROS time 设置有关；ManualClock 必须与消息 timestamp 类型匹配。建议 freshness 内部最终采用单调时钟，但这属于语义审查，不是简单替换。
- `SocketFactory` 静态工厂不易 mock，但通过 RobotDriver 构造注入可绕过，不需要首轮重构工厂。
- 当前 loopback tests 固定端口，新增并行测试应分配动态可用端口或集中管理端口。
- 真正的 ResourceManager/ControllerManager error propagation 必须在真实 ros2_control integration fixture 中验证，不能用 FakeSocket 单测代替。
- 本报告不授权修改 Stäubli 上游；若后续要在上游仓库实现，须遵循用户授权与分支/PR审查流程。

## 8. 验证与当前状态

本轮只读取固定 commit 的 CMake、Socket、UDPSocket、RobotDriver、Subscriber 和现有 gtest 文件并形成静态实施方案。没有修改 Stäubli 上游文件，也没有在该仓库创建分支或 PR。

- 本报告中的所有 SEAM/FS/CLK/IT 测试：`NOT_RUN`。
- 未执行 Stäubli 构建、gtest、ROS 2 launch、ResourceManager/ControllerManager 集成、TSan/ASan、SIL/HIL、VAL3/CS9、FAT/SAT 或实机验证。
- 未修改 `ICube-Robotics/staubli_driver_ros2` 或 `ros-controls/ros2_control`；未应用/合并任何 PR。
- `TODO-EXT-001` 仍未获授权。
- 不能据此宣称 UDP 故障注入测试夹具已实现，或工程级安全验收通过。

## 9. 下一节点

**§9.3.286 / SERVO-869：FakeSocket 最小测试替身的接口契约与生命周期/线程安全设计。** 下一步先精确覆盖 Socket 所有虚函数的脚本行为、回调投递/取消/join 语义、测试事件记录与断言接口，再决定是否进入上游实现；仍不擅自修改 Stäubli 上游。
