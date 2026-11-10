# Stäubli SocketV2 header dependency closure、public type layout 与 factory Result API C++17 编译契约审查

- 审查节点：§9.3.294 / SERVO-877
- 日期：2026-11-10
- 固定上游基线：ICube-Robotics/staubli_driver_ros2@bd658e2d266e315d2ee35f985fb352ea88306b79
- 前序：SERVO-875 SocketV2迁移切片；SERVO-876 public header/ABI surface 与 UDP Core ownership
- 性质：基于固定基线文件清单和既有源码事实的静态接口设计审查；不代表已在上游工作区编译

## 1. 审查目标与结论

本节点把 SERVO-876 的 public ABI 方向收敛为可执行的 C++17 头文件与类型契约。短期只承诺同一工具链/同一构建配置下的 source-level API；不承诺跨编译器、跨标准库 ABI、跨 CRT 或跨 ROS 发行版的二进制兼容。旧 Socket/UDPSocket/SocketFactory 保持原样；V2 使用新增头文件和独立 private Core。

关键结论：
1. public headers 必须自包含，且其 include closure 不得依赖 Boost.Asio、线程、mutex、socket 或 private Core 头文件。
2. public API 可以使用 C++17 的 std::string、std::vector、std::shared_ptr、std::optional，但这明确属于源码级 API，不是稳定二进制 ABI。
3. C++17 没有标准 std::expected；不得将其写入接口。采用自定义、显式错误码的 Result value type，或经批准的 std::variant 组合；本节点推荐简单 Result struct，以降低调用复杂度。
4. 所有 public enum 固定 uint32_t underlying type 和显式数值；已发布值不得重排/复用。
5. PIMPL 的 unique_ptr 实现类必须在 private implementation translation unit 中定义 façade 析构函数；public header 只前置声明 impl，禁止内联 default destructor 触发 incomplete-type 删除要求。
6. standalone consumer fixture、每个 public header 单独编译、跨头文件 include-order 编译和 C++17 feature gate 都是必须验收项；本轮没有执行编译，全部保持 NOT_RUN。

## 2. 固定事实与证据边界

SERVO-876 已记录固定上游文件及 blob：
- include/staubli_robot_driver/communication/socket.hpp（legacy纯虚接口）
- include/staubli_robot_driver/communication/udp_socket.hpp（UDPSocket持有 unique_ptr PIMPL）
- src/communication/udp_socket_impl.hpp（Asio、线程、缓冲区和回调位于private实现）
- src/communication/udp_socket.cpp（legacy façade转发）
- src/communication/socket_factory.cpp（legacy factory）
- CMakeLists.txt（C++17、SHARED库、include目录安装、ament target export）
- package.xml（版本0.1.4，未声明独立ABI承诺）

本轮未能通过当前 GitHub 连接读取上游仓库固定 commit 的文件正文；因此不声称重新逐行验证这些文件。本报告沿用 SERVO-876 已记录的路径、blob SHA 和事实，并把具体编译/预处理验证列为未执行项。不得把文档中的接口建议表述为上游已实现。

## 3. Public header dependency closure

建议的安装头文件：
- socket_v2_types.hpp：仅包含 <cstdint>、<memory>、<string>、<vector>、<optional>（仅在实际使用 optional 时）及必要的标准头；定义 enum、EndpointConfig、NativeError、SocketSnapshot、OperationResult、FactoryResult。
- socket_v2.hpp：包含 socket_v2_types.hpp 和 <functional>/<memory>（仅按签名需要）；声明 SocketV2 抽象 façade。不得包含 Boost.Asio、thread、mutex、condition_variable 或 Core。
- socket_factory_v2.hpp：包含 socket_v2.hpp；声明 SocketFactoryV2::create。
- visibility_control.hpp：仅提供平台宏，不引入通信实现依赖。

private headers/source：
- udp_socket_core.hpp / *_internal.hpp 仅在 src/ 内可见；不得安装。
- udp_socket_v2_impl.hpp（如需要）只在 src/ 内前置声明或定义。
- 所有 Asio include 仅位于 .cpp/private headers。

禁止：
- public header include src/ 路径；
- public signature 暴露 boost::system::error_code、asio endpoint/socket、std::thread、mutex、atomic 或 private Core；
- 依赖调用方先 include 某个“先决头文件”才能编译；
- 用全局 using namespace 或宏污染调用方。

## 4. 类型布局与不完整类型规则

建议的 public value types（源码级 ABI）：
- enum class ProtocolType : std::uint32_t：UDP=1；TCP=2（即使暂不支持，也保留显式unsupported结果，不做静默fallback）。
- enum class SocketErrorCode : std::uint32_t：NONE=0、UNSUPPORTED_PROTOCOL=1、INVALID_ARGUMENT=2、RESOLVE_FAILED=3、OPEN_FAILED=4、BIND_FAILED=5、CONNECT_FAILED=6、ALREADY_RUNNING=7、NOT_CONNECTED=8、STOP_TIMEOUT=9、CANCEL_FAILED=10、INTERNAL_ERROR=11。数值仅为本设计建议，尚非上游协议或已发布 ABI。
- enum class TransportState / ReceiveState：显式底层类型，列出状态转换表；不得通过 bool 混合“socket已连接”“接收线程已启动”“callback仍活动”。
- EndpointConfig：地址字符串、端口、bind mode；构造后仍须在 factory/connect 边界校验地址格式和端口范围。
- NativeError：整数 category/value 加诊断字符串；不暴露 Boost error category 对象。
- SocketSnapshot：generation、transport/receive state、local endpoint文本、native handle open布尔观察值、worker joinable、pending handler与active callback计数、snapshot consistency level；不返回可操作的native handle。
- OperationResult：success、error code、operation id、message、after snapshot；不得以 success=true 掩盖 dropped/would_block 或 residual resource。
- FactoryResult：socket shared_ptr、error code、diagnostic；success() 必须要求 socket非空且error==NONE，失败时socket必须为空。

对 PIMPL：
- 若 UDPSocketV2 持有 std::unique_ptr<UdpSocketV2Impl>，头文件只前置声明 class UdpSocketV2Impl;，析构函数只声明，不在头文件 inline = default。
- 在 .cpp 中先包含完整 impl 定义，再定义 UDPSocketV2::~UDPSocketV2() noexcept = default。
- 若 public value type 直接持有 std::shared_ptr<Core>，会泄露所有权/生命周期策略；不建议。shared_ptr incomplete pointee 本身可用于句柄，但 Core owner 应留在 façade/private state。
- 禁止 unique_ptr<incomplete> 的 inline destructor、inline reset 或需要完整类型的 inline deleter。

## 5. Factory Result 与 C++17 合约

C++17可用：std::variant、std::optional、std::string、std::vector、std::shared_ptr、std::function。C++17不可假设：std::expected（标准化于C++23）。不得为了Result接口把项目语言标准提升到C++23。

推荐简化接口形状（伪代码，不是已实现声明）：

    struct FactoryResult {
      std::shared_ptr<SocketV2> socket;
      SocketErrorCode error{SocketErrorCode::INTERNAL_ERROR};
      std::string diagnostic;
      bool success() const noexcept {
        return socket != nullptr && error == SocketErrorCode::NONE;
      }
    };

    class SocketFactoryV2 final {
    public:
      static FactoryResult create(ProtocolType type) noexcept;
    };

契约：
- UDP成功：socket非空、error=NONE。
- TCP当前不支持：socket为空、error=UNSUPPORTED_PROTOCOL；不调用legacy factory、不创建legacy对象。
- 非法枚举值：socket为空、error=INVALID_ARGUMENT。
- 分配失败/内部异常：按项目异常策略捕获并映射；若 API 标记 noexcept，所有可能抛出的字符串分配/构造也必须纳入异常安全设计，不能仅在函数体最外层随意 noexcept。
- create失败不得留下 socket、worker、native handle 或 callback；如失败清理不完全，必须通过独立 residual owner/cleanup report 暴露，不能返回“干净失败”。

因此实现时可考虑不标 noexcept，或者使用不分配的错误值并谨慎构造诊断文本；本节点不允许未经异常路径审计就加 noexcept。

## 6. Enum 与状态兼容策略

- 每个 enum 显式指定 uint32_t underlying type，并给每个 enumerator 显式整数。
- 数值一经发布不得重排、复用；新增值只追加。
- 不把内部状态值与 wire protocol enum 混用；SocketV2状态是库内API，不改变既有ICube UDP wire format。
- 对未知枚举值 fail-closed，返回 INVALID_ARGUMENT/UNKNOWN_STATE，不默认映射 UDP、STOP 或成功。
- 所有状态转换需定义非法转换的返回码；幂等 stop/disconnect 的重复调用可成功，但必须返回真实 residual snapshot。

## 7. Standalone consumer fixture 设计

在上游测试工程之外建立独立 consumer fixture（后续实施，不在本轮执行）：
1. translation unit A 只 include socket_v2_types.hpp。
2. translation unit B 只 include socket_v2.hpp。
3. translation unit C 只 include socket_factory_v2.hpp。
4. translation unit D 以不同顺序 include 所有 public headers，检查宏/声明污染。
5. 对每个 TU 使用 -std=c++17 -Wall -Wextra -Werror（编译器支持时），只链接导出的 ament target，不添加 src/ 私有 include path。
6. 通过 install-space 而非 build-tree include 路径编译；验证包安装后 public headers 真正可消费。
7. 对不支持 TCP、非法 ProtocolType、UDP create 成功/失败路径建立 gtest；不把编译通过当作运行时生命周期通过。
8. 对 Linux 至少记录 nm -D --defined-only 与 readelf -Ws；Windows若声明支持则运行 DLL import/export smoke。

## 8. 测试矩阵

| ID | 验收项 | 状态 |
|---|---|---|
| HDR-01 | socket_v2_types.hpp 独立 include | NOT_RUN |
| HDR-02 | socket_v2.hpp 独立 include | NOT_RUN |
| HDR-03 | socket_factory_v2.hpp 独立 include | NOT_RUN |
| HDR-04 | include 顺序变化无编译差异 | NOT_RUN |
| HDR-05 | public headers 不包含 Asio/线程/锁/Core/private路径 | NOT_RUN |
| HDR-06 | install-space consumer 可仅依赖导出 target 编译 | NOT_RUN |
| HDR-07 | C++17 feature gate，无 std::expected/C++20/23 API | NOT_RUN |
| TYPE-01 | PIMPL incomplete-type destructor 在 .cpp 定义 | NOT_RUN |
| TYPE-02 | unique_ptr incomplete type 不触发 inline destructor 编译失败 | NOT_RUN |
| TYPE-03 | enum underlying type 与显式值静态断言 | NOT_RUN |
| TYPE-04 | 未知 enum fail-closed | NOT_RUN |
| RES-01 | UDP factory success 结果字段一致 | NOT_RUN |
| RES-02 | TCP 返回 UNSUPPORTED_PROTOCOL 且无 legacy fallback | NOT_RUN |
| RES-03 | 非法 protocol enum 返回 INVALID_ARGUMENT | NOT_RUN |
| RES-04 | create失败不遗留资源，失败清理残留可观察 | NOT_RUN |
| ABI-17 | Result/enum/value type policy 与 source-only ABI 声明一致 | NOT_RUN |
| ABI-18 | consumer compile fixture 使用安装空间与导出 target | NOT_RUN |

## 9. 实施顺序

1. ABI-0：先确认包的 ABI policy 和目标平台，不改变旧 API。
2. HDR-0：创建独立 consumer compile fixture，证明当前 legacy public headers 的 include/install 现状。
3. HDR-1：新增 visibility_control.hpp 与 socket_v2_types.hpp，单独编译。
4. HDR-2：新增 socket_v2.hpp、socket_factory_v2.hpp，确认 public closure 无 Asio。
5. TYPE-0：实现PIMPL析构和Result类型；先不创建UDP Core。
6. FACTORY-0：只实现 UDP/TCP unsupported/invalid enum factory 结果；再进入Core接入。
7. 每一步独立提交并保存 compiler、CMake、install-space、symbol evidence；不得把编译设计写成动态测试通过。

## 10. 风险、非目标与状态

- 本节点未新增 public headers、Result、visibility macro、fixture 或任何上游源码。
- 未执行 C++ 编译、CMake configure/build、gtest、install-space consumer、nm/readelf、Windows DLL、TSan、loopback 或 ROS 2 Control。
- 未执行 VAL3/CS9、SIL/HIL、FAT/SAT 或实机验收。
- HDR-01至HDR-07、TYPE-01至TYPE-04、RES-01至RES-04、ABI-17至ABI-18全部 NOT_RUN。
- 未修改固定上游；未应用/合并 PR；TODO-EXT-001 未授权。
- 本节点只把 SERVO-876 的头文件/ABI方向细化为C++17可编译契约，不能将其标记为接口实现完成或工程验收通过。

## 11. 下一节点

§9.3.295 / SERVO-878：SocketV2 Result 错误分类、异常安全与资源残留/quarantine owner 生命周期契约。重点审查 create/connect/stop 失败与异常路径如何传递 primary error、cleanup error、residual resource ownership，定义 noexcept边界、失败返回值不变量和可重试清理接口；仍以固定上游基线静态设计为主，不修改上游。
