# Stäubli Socket v2 兼容迁移与 UDP 状态观测实现切片设计

- 审查节点：§9.3.292 / SERVO-875
- 日期：2026-11-10
- 固定上游基线：ICube-Robotics/staubli_driver_ros2@bd658e2d266e315d2ee35f985fb352ea88306b79
- 关联前序：SERVO-873（事务式 connect rollback guard）、SERVO-874（Socket / Subscriber 生命周期契约）
- 性质：实现前迁移方案与切片设计；未修改上游源码

## 1. 本轮决策摘要

本节点不建议直接在现有 Socket 抽象中增加 virtual 函数，也不建议将现有 bool 方法改签名。推荐采用独立版本化接口 SocketV2 + 新工厂 create_v2()，让旧 Socket 与旧 SocketFactory 保持原样；新调用方显式选择 v2 能力。UDP v2 adapter 通过内部共享 Core 读取 Asio 真实状态，避免从旧 bool 标志反推资源事实。

重要源码发现：当前 CMake 的 LIBRARY_SOURCES 只列入 src/communication/udp_socket.cpp，未列入 tcp_socket.cpp；socket_factory.cpp 对 TCP 明确抛出“TCP protocol not implemented yet”。现有 socket 单测参数也只实例化 UDP。因此 TCP enum/header 的存在不等于 TCP 实现可用，SERVO-875 的第一期范围必须限定 UDP，TCP 单独立项。

## 2. 固定源码核对与 blob SHA

| 路径 | Blob SHA | 观察 |
|---|---|---|
| include/staubli_robot_driver/communication/socket.hpp | 230af198337e5d047b29b2bbf6354a698fb3a390 | Socket 是纯虚基类，connect/disconnect/start/stop 均为 bool；直接增加 virtual 会改变基类 vtable |
| include/staubli_robot_driver/communication/udp_socket.hpp | 31eb5e2e9218e17160fc10dfbd72d77be4b3b0e5 | UDPSocket 公开继承 Socket，持有 unique_ptr<UDPSocketImpl> PIMPL |
| include/staubli_robot_driver/communication/tcp_socket.hpp | 55790bb891cb5a4e7c3faefda9ba5d25a7f76909 | 存在 TCPSocket 声明，但声明不证明实现进入构建 |
| src/communication/udp_socket_impl.hpp | 1309a8f2d59e8295869e178af82a66868bb911ff | Asio UDP socket、atomic flags、std::thread、io_service、endpoint 均在 impl 内 |
| src/communication/udp_socket.cpp | c74fe82be22b378273e29b6aba10f9aaccf1f2d8 | UDPSocket 仅转发到 PIMPL；析构函数为空 |
| src/communication/tcp_socket.cpp | cdb18d03b0413cd9d88758c63fefaae51e3f5e29 | wrapper 引用 TCP PIMPL，但未列入当前主库 LIBRARY_SOURCES |
| src/communication/socket_factory.cpp | dbbc85d6f036e8d1fc035336022a499830f58686 | UDP 返回 UDPSocketFactory；TCP 直接抛 runtime_error |
| CMakeLists.txt | b21608627b53d66f9910d9a836b053cd7d7fd6bf | 主库 sources 含 udp_socket.cpp，不含 tcp_socket.cpp；已有 test_sockets |
| test/unit_tests/communication/test_sockets.cpp | 4fd06a9da38157a543766669c1cdda4bdb698029 | 参数化 fixture 只实例化 UDP；注释中的 TCP case 未启用 |

## 3. 为什么不能直接修改旧 Socket

现有 Socket 是抽象纯虚接口。给其新增 virtual 会改变 vtable 布局，已编译的外部派生类/插件可能出现 ABI 不兼容；把 bool connect/disconnect 改成结构化返回类型则同时破坏 source/API 与 ABI。即使仓库内当前主要通过 factory 创建，仍不能假设外部用户没有自定义 Socket 实现。

### 3.1 推荐版本化边界

保留原有 Socket.hpp 中 Socket 与 SocketFactory 的签名不变。新增独立头文件 socket_v2.hpp：

    class SocketV2 : public Socket {
    public:
      virtual SocketOperationResult connect_detailed(const EndpointConfig&) = 0;
      virtual SocketOperationResult disconnect_detailed() = 0;
      virtual ReceiveOperationResult start_receive_detailed(Callback) = 0;
      virtual ReceiveOperationResult stop_receive_detailed(StopPolicy) = 0;
      virtual SocketSnapshot snapshot() const = 0;
    };

新增 SocketFactoryV2::create(ProtocolType) -> std::shared_ptr<SocketV2>，旧 SocketFactory::create() 不改变。v2 对象仍可向上转换为 std::shared_ptr<Socket>，所以旧调用点可继续使用 bool API；只有显式依赖详细结果的调用方才依赖 SocketV2。

注意：不得把旧 UDPSocket 类直接改为继承 SocketV2 并声称 ABI 保证。更稳妥的是新增独立 UDPSocketV2 façade，内部持有共享 UDP Core；旧 UDPSocket façade 与新 façade 各自实现旧/新契约，Core 是唯一底层状态所有者。v2 façade 的新 ABI 作为显式新 API 发布，旧类型、旧工厂、旧符号保持不变。若项目没有稳定 ABI 承诺，也仍应按版本化迁移而不是隐式更改公共基类。

### 3.2 能力发现与 fallback

- 新代码直接通过 SocketFactoryV2 创建 SocketV2，不对任意旧 Socket 做未经验证的 static_cast。
- 如果调用方收到的是外部注入的 legacy Socket，必须显式判断能力是否具备；缺少 v2 能力时返回 CAPABILITY_UNAVAILABLE，不得构造虚假的 native snapshot。
- 不推荐只在旧 Socket 上增加可选 dynamic_cast diagnostics interface 作为最终方案：它能发现能力，但不能保证 diagnostics 与旧 socket 内部资源来自同一 owner，也不能保证旧实现提供真实状态。
- v2 工厂必须对 UDP 提供真实 v2 实现；TCP 在 factory 中继续明确报告 UNSUPPORTED_PROTOCOL，直到独立实现和测试门禁完成。

## 4. UDP Core 的状态观测落点

### 4.1 真实状态与逻辑标志分离

当前 UDPSocketImpl 已直接持有 boost::asio::ip::udp::socket、io_service、receive_thread、local/remote endpoint、is_connected_、receiving_。这些成员是最小侵入的状态采集位置；不要在 UDPSocket façade 层用 bool 重新拼凑快照。

建议 Core 只维护必要的逻辑状态和生命周期同步；底层句柄事实直接查询 Asio 对象：

| snapshot 字段 | 采集位置/方法 | 语义与限制 |
|---|---|---|
| native_handle_open | socket_.is_open() | Asio handle 是否 open；不等同于 UDP peer connection |
| local_endpoint_valid / local_address / local_port | socket_.local_endpoint(error_code) | 只有成功取得 endpoint 才声明 bound；保留查询错误 |
| remote_endpoint_configured / remote_address / remote_port | remote_endpoint_ 是否已由 resolve 成功赋值 | 这是发送目标配置，不是 UDP 握手/对端在线证明 |
| receive_thread_joinable | receive_thread_.joinable() | 必须在 lifecycle synchronization 下读取 |
| receive_flag | receiving_.load() | 仅是逻辑标志，不替代 joinable |
| receive_state | 由状态机及 handler/callback 计数构成 | 不允许只依据 receiving_ |
| pending_handlers | Core 显式登记/递减的异步 handler 数 | Asio 没有通用公开 API 可直接查询 io_service 内部 pending handler 数 |
| active_callbacks | callback admission guard 计数 | 由 RAII enter/leave 维护 |
| last_native_error | 每个失败操作保存的 boost::system::error_code | 必须和 operation id 绑定，不能被后续清理覆盖 |
| generation | Core 生命周期递增计数 | 防止旧 callback/旧 session 污染新会话 |

### 4.2 connect 阶段观测

UDP connect 当前顺序为 open -> set_option(reuse_address) -> 解析 local address -> bind -> local_endpoint -> resolver.resolve -> 写 remote_endpoint -> is_connected=true。建议每一步都保存阶段标记：

    enum class ConnectStage { NONE, OPENED, OPTIONS_SET, LOCAL_ADDRESS_PARSED,
      BOUND, LOCAL_ENDPOINT_CAPTURED, REMOTE_RESOLVED, READY, ROLLBACK };

- open/set_option/bind/resolve 尽量使用 error_code overload，并在失败点保存原始错误类别和值。
- `local_address` 解析失败发生在 socket open 之后，因此属于 open-handle residual 场景；不能把它与 open 前参数校验失败混为一类。
- bind 失败时句柄可能仍 open；resolver 失败时句柄通常已 open 且已 bind；每个阶段都必须 snapshot 后再执行 rollback。
- `socket_.local_endpoint(ec)` 失败不能把 local_endpoint_valid 设 true；不能用之前缓存的 endpoint 证明当前句柄绑定状态。
- UDP remote resolve 只配置发送目标；UDP 无连接握手，is_connected 应定义为本地 transport ready，而不是远端在线。
- rollback close 也必须用 error_code overload；close 失败保留 handle open 状态和 close error。只有 socket_.is_open()==false 且 receive worker 已清理，才可声明资源 CLOSED。

### 4.3 stop / cancel / join 观测

当前 stop_receive_thread 以 receiving_ 为唯一早退条件；`io_service_.stop()` 后 join，再把 receiving_ 清零。改造时至少必须：

1. 在 lifecycle mutex 下关闭 callback admission，记录 STOPPING。
2. 若 socket open，调用 socket_.cancel(ec) 取消异步 receive；记录 cancel error，但不能因此跳过 join/close 的后续步骤。
3. 处理 io_service 的停止/重启和 aborted handler 生命周期：必须通过确定性测试证明所有已登记 handler 都已完成或销毁，不能把 io_service.stop() 当作 pending handler 已 drain。
4. 如果 receive_thread_.joinable()，检查是否为当前线程；self-join 返回 SELF_JOIN_FORBIDDEN，不得 detach。
5. 只有 active_callbacks==0、pending_handlers==0 且 thread 已 join 后，才可把 ReceiveState 设为 STOPPED。
6. stop 超时不得 detach，也不得释放唯一 Core/Subscriber owner；返回 CALLBACK_DRAIN_TIMEOUT / WORKER_NOT_JOINED，并保留 FAILED_RESIDUAL。上层生命周期管理器必须继续持有 owner 并安排重试/隔离。

标准 std::thread 没有 timed join。timeout 只约束 callback drain / worker 退出等待；超时后不能声称 thread 已结束，也不能销毁包含该 thread 所引用状态的 Core。可选设计是 stop 请求与 wait completion 分离，但仍必须由 owner 保留线程和对象，直到最终 join。

## 5. 结构化错误与快照的最小类型

    enum class SocketErrorCode {
      OK, INVALID_ARGUMENT, INVALID_STATE, CAPABILITY_UNAVAILABLE,
      UNSUPPORTED_PROTOCOL, OPEN_FAILED, OPTION_FAILED, ADDRESS_PARSE_FAILED,
      BIND_FAILED, LOCAL_ENDPOINT_QUERY_FAILED, RESOLVE_FAILED,
      CANCEL_FAILED, CALLBACK_DRAIN_TIMEOUT, SELF_JOIN_FORBIDDEN,
      WORKER_NOT_JOINED, CLOSE_FAILED, INTERNAL_ERROR
    };

    struct NativeError {
      std::string category;     // e.g. boost.system category name
      int value;                // error_code.value()
      std::string message;
    };

    struct SocketSnapshot {
      TransportState transport;
      ReceiveState receive;
      ConnectStage connect_stage;
      bool native_handle_open;
      bool local_endpoint_valid;
      std::string local_address;
      uint16_t local_port;
      bool remote_endpoint_configured;
      std::string remote_address;
      uint16_t remote_port;
      bool receive_thread_joinable;
      size_t pending_handlers;  // application-maintained counter
      size_t active_callbacks;
      uint64_t generation;
      NativeError last_error;
    };

    struct SocketOperationResult {
      bool success;
      SocketErrorCode code;
      bool operation_attempted;
      NativeError error;
      SocketSnapshot after;
    };

该类型是设计伪代码，不是已经提交的可编译接口。snapshot 应在 Core 的生命周期锁/状态锁规则下采集；若返回的是并发瞬时视图，必须显式标记 consistency=OBSERVATIONAL。经过 stop barrier 后才可返回 quiescent=true 的稳定终态快照。

## 6. 分阶段实现切片与依赖

| 切片 | 范围 | 输出 | 退出门禁 |
|---|---|---|---|
| V2-0 | 只加新头文件/类型/错误码/工厂声明；旧 Socket 不变 | socket_v2.hpp、v2 result/snapshot 类型 | 旧 API 编译面不变；API diff 与 ABI 基线记录 |
| V2-1 | 抽离 UDP Core 的状态快照与阶段跟踪，不改变旧 bool 行为 | Core snapshot、connect stage、native error capture | Fake Asio seam 或受控 adapter 测试覆盖 open/bind/resolve/close 故障 |
| V2-2 | 实现独立 UDPSocketV2 façade 与 SocketFactoryV2 | v2 factory 可创建 UDP；TCP 明确 unsupported | legacy Socket tests 仍可编译；v2 snapshot 字段真实可观测 |
| V2-3 | 结构化 disconnect/cancel/stop、callback admission/drain、thread join | Detailed operation results、residual snapshot | 重复 stop、cancel failure、self-stop、callback blocked timeout、retry 全覆盖 |
| V2-4 | RobotDriver/Subscriber 适配到显式 v2 能力 | 调用方可读取 CleanupReport，不丢 primary error | 双通道 rollback fault matrix 全覆盖；legacy injected Socket 明确 fail closed |
| V2-5 | TCP 独立实现与协议测试（不在本轮范围） | TCP v2 实现与构建目标 | CMake sources、factory、TCP loopback、连接超时、关闭残留均通过 |

建议按 V2-0 -> V2-1 -> V2-2 -> V2-3 顺序推进；不要一次性同时重写 Subscriber、RobotDriver 和 transport。V2-4 依赖 SERVO-873/874 契约先落地；V2-5 不得因为 enum 中有 TCP 而提前标记完成。

## 7. CMake / 测试影响

- 新增 `socket_v2.hpp` 为 public installed header（现有 install DIRECTORY include/ 会覆盖安装，无需另加单文件 install）。
- 新增 `src/communication/udp_socket_v2.cpp` 或 Core source 后，必须明确加入 `LIBRARY_SOURCES`；当前 CMake 对 TCP 的遗漏与 factory unsupported 事实应保留为独立跟踪项。
- 增加 `test_socket_v2_contract`，与现有 `test_sockets` 分离，避免旧 bool contract 与 v2 structured contract 互相掩盖。
- 旧 `test_sockets` 的 TCP 参数不得启用，直到 factory 不再抛 unsupported 且 TCP 实际源文件加入目标。
- 固定端口 loopback 测试需迁移到 OS 分配端口或受控端口 fixture，避免并行测试碰撞；本节点不宣称现有测试已修复。
- native error 注入必须可确定性复现，不能依赖真实端口占用/网络故障来证明 bind/resolve/close 错误路径。

## 8. 验收规格（全部尚未执行）

| ID | 规格 | 状态 |
|---|---|---|
| V2-API-01 | 旧 Socket 头文件签名、纯虚函数集合、SocketFactory 符号保持不变 | NOT_RUN |
| V2-API-02 | 旧第三方 Socket 派生类无需实现新增 virtual 即可编译 | NOT_RUN |
| V2-API-03 | SocketFactoryV2 创建 UDP v2；旧 SocketFactory 创建 legacy UDP | NOT_RUN |
| V2-API-04 | SocketFactoryV2 请求 TCP 返回明确 UNSUPPORTED_PROTOCOL，不产生假对象 | NOT_RUN |
| V2-OBS-01 | open 成功后 address parse 失败，snapshot 显示 open handle 并记录 rollback | NOT_RUN |
| V2-OBS-02 | bind 失败，snapshot 区分 handle open 与 local endpoint not bound | NOT_RUN |
| V2-OBS-03 | resolve 失败，snapshot 反映已绑定本地 endpoint 与 remote 未配置 | NOT_RUN |
| V2-OBS-04 | local_endpoint 查询失败，不能误报 bound endpoint | NOT_RUN |
| V2-OBS-05 | close 失败保留 open residual 和 native error；重试 close 后状态转 CLOSED | NOT_RUN |
| V2-OBS-06 | UDP snapshot 不把 remote endpoint resolve 成功描述为远端在线 | NOT_RUN |
| V2-RX-01 | receiving=false 但 thread joinable 时 stop 仍执行 join/报告状态 | NOT_RUN |
| V2-RX-02 | cancel error 不短路 join/close 后续清理 | NOT_RUN |
| V2-RX-03 | callback 阻塞时 stop timeout 保留 Core owner、thread joinable 和 FAILED_RESIDUAL | NOT_RUN |
| V2-RX-04 | callback 退出后 retry stop 成功 drain 并 join | NOT_RUN |
| V2-RX-05 | self-stop/self-join 返回专用错误，不 detach | NOT_RUN |
| V2-RX-06 | pending handler 计数在 success/operation_aborted/exception 路径准确归零 | NOT_RUN |
| V2-RX-07 | generation 变化后旧 handler 不得调用新 session callback | NOT_RUN |
| V2-CMAKE-01 | 新 v2 source 被加入主库，legacy targets 仍正常配置 | NOT_RUN |
| V2-CMAKE-02 | TCP 在实现前保持明确 unsupported，不能因头文件存在而启用测试 | NOT_RUN |

## 9. 实施风险与停止条件

1. **ABI 风险**：任何改动旧 Socket vtable、旧 factory 符号或旧 UDPSocket 对象布局的方案，必须先走显式 breaking-change 审批；本建议不授权此类改动。
2. **Core 所有权风险**：legacy/v2 façade 不能分别拥有同一个底层 socket；必须唯一 Core owner，防止重复 close、重复 join 和 snapshot 与实际句柄分离。
3. **Asio handler drain 风险**：io_service.stop() 仅停止事件循环，不等于 handler 已经执行/销毁。必须以 application-maintained pending count 和确定性测试证明生命周期。
4. **callback timeout 风险**：超时后不得 detach；必须保留 owner、thread 与 callback state，禁止析构穿越仍运行的 callback。
5. **UDP 语义风险**：UDP 的“connected”是本地 socket 配置状态，不代表远端握手成功或设备在线。
6. **TCP 范围风险**：factory 当前明确不支持 TCP；TCP v2 必须作为独立实现切片，不得从声明推断实现。
7. **静态审查边界**：本报告不证明 Boost.Asio 在所有目标平台上的错误码/close 行为；具体行为需通过目标 ROS 2 Jazzy 构建和 loopback/故障注入验证。

## 10. 本轮结论与执行边界

- SERVO-875 完成 Socket v2 兼容边界、UDP 状态观测落点和实施切片设计。
- 未新增 socket_v2.hpp、SocketV2、SocketFactoryV2、UDP Core 或 adapter；未修改任何上游代码。
- V2-API-01 至 V2-CMAKE-02 全部 NOT_RUN；未运行 build、gtest、loopback、TSan/ASan 或 ROS 2 Control 集成。
- 未执行 SIL/HIL、VAL3/CS9、FAT/SAT 或实机验证；工程级验收未通过。
- 未应用或合并任何 PR；TODO-EXT-001 仍未授权。

## 11. 下一节点

§9.3.293 / SERVO-876：SocketV2 public header / ABI surface 的逐符号设计审查与 UDP Core ownership 拆分图。重点审查 v2 类型的可见符号、工厂生命周期、Core 单一所有权、legacy/v2 wrapper 共享实现边界、CMake 导出与安装面；继续只做设计，未获得明确授权前不修改 Stäubli 上游。
