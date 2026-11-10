# Stäubli SocketV2 public header / ABI surface 与 UDP Core ownership 设计审查

- 审查节点：§9.3.293 / SERVO-876
- 日期：2026-11-10
- 固定上游基线：ICube-Robotics/staubli_driver_ros2@bd658e2d266e315d2ee35f985fb352ea88306b79
- 前序：SERVO-873 事务式 connect rollback guard；SERVO-874 Socket / Subscriber 生命周期契约；SERVO-875 SocketV2 兼容迁移与 UDP 状态观测切片
- 性质：公共头文件、ABI 面和所有权设计审查；未修改上游源码

## 1. 审查结论

建议将 SocketV2 的 public API 限定为少量稳定 façade 类型，内部状态、Asio 对象、线程、callback、handler 计数和错误采集全部留在非安装的 private Core。推荐 public `SocketV2` 使用纯虚接口 + private implementation 的稳定约定，具体 UDP 实现 `UDPSocketV2` 只暴露前置声明的 `UdpSocketV2Impl`/opaque handle；`SocketV2` 通过 `std::shared_ptr<SocketV2>` 由 `SocketFactoryV2` 创建。Core 由单一 shared ownership control block 管理，legacy facade 和 v2 facade 不得各自独立持有同一个原生 socket。

当前上游没有专用 visibility/export macro，也没有显式 ABI version namespace。CMake 将 include/ 整目录安装，主库为 SHARED，并导出 CMake target。新增 public header 会自然进入安装面；但不能仅凭 target export 推断 Windows DLL 符号导出或跨编译器 ABI 稳定。应在实现前确定平台导出宏、符号可见性策略和 ABI policy。

## 2. 固定上游文件与 blob SHA

| 路径 | Blob SHA | 与本节点相关事实 |
|---|---|---|
| include/staubli_robot_driver/communication/socket.hpp | 230af198337e5d047b29b2bbf6354a698fb3a390 | Socket 为纯虚接口；SocketFactory 静态 create 返回 shared_ptr<Socket>；无导出宏 |
| include/staubli_robot_driver/communication/udp_socket.hpp | 31eb5e2e9218e17160fc10dfbd72d77be4b3b0e5 | UDPSocket 公开继承 Socket，头文件中 unique_ptr<UDPSocketImpl>；PIMPL impl 类型仅前置声明 |
| src/communication/udp_socket_impl.hpp | 1309a8f2d59e8295869e178af82a66868bb911ff | Asio socket、io_service、thread、buffer、callback 和 atomic flag 全部在 private 实现类 |
| src/communication/udp_socket.cpp | c74fe82be22b378273e29b6aba10f9aaccf1f2d8 | legacy façade 只转发至 unique_ptr PIMPL；UDPSocketFactory 返回 shared_ptr<Socket> |
| src/communication/socket_factory.cpp | dbbc85d6f036e8d1fc035336022a499830f58686 | legacy factory UDP 分支创建 UDP；TCP 分支 unsupported |
| CMakeLists.txt | b21608627b53d66f9910d9a836b053cd7d7fd6bf | C++17；SHARED 主库；install(DIRECTORY include/)；导出 export_staubli_robot_driver target；无显式 visibility macro |
| package.xml | 50ad11f1336aab87a9afca6b9751de9fb6766595 | 版本 0.1.4；ROS 2 ament_cmake 包；未声明独立 ABI version contract |

## 3. Public header 建议布局

建议新增下列安装头文件，避免改动既有 socket.hpp / udp_socket.hpp 的类布局和 virtual set：

    include/staubli_robot_driver/communication/socket_v2.hpp
    include/staubli_robot_driver/communication/socket_v2_types.hpp
    include/staubli_robot_driver/communication/socket_factory_v2.hpp

实现文件保持 private：

    src/communication/socket_v2_impl.hpp
    src/communication/udp_socket_v2.cpp
    src/communication/udp_socket_core.hpp
    src/communication/udp_socket_core.cpp
    src/communication/udp_socket_core_internal.hpp

其中 Core private header 不得安装，不得被 public header include，不得把 Boost.Asio 类型暴露到 public signatures。若 Core 未来拆为单独库，也应通过窄的 internal interface 连接，而不是让业务层直接持有 Asio socket/thread。

## 4. Public symbol / ABI surface 逐符号建议

| 符号 | 可见性 | 建议 | ABI / 生命周期约束 |
|---|---|---|---|
| SocketV2 | public exported abstract class | 仅声明 virtual destructor 与 v2 operation contract；禁止添加到 legacy Socket | 新 API 独立版本；一旦发布 virtual set 即视为 ABI surface |
| SocketV2::connect_detailed | public virtual | 接收 EndpointConfig const ref，返回 OperationResult | 不暴露 boost::system 类型；结果对象 ABI policy 需先定 |
| SocketV2::disconnect_detailed | public virtual | 返回 OperationResult | disconnect 需要可重复调用并报告 residual |
| SocketV2::snapshot | public virtual 或非 virtual façade | 返回 SocketSnapshot value | snapshot 语义标记 observational/quiescent |
| SocketV2::start_receive | public virtual | 接收 Callback value / move | callback admission 与对象生命周期由 Core 保证 |
| SocketV2::stop_receive | public virtual | 接收 StopOptions，返回 OperationResult | timeout 不释放 Core owner，不 detach |
| UDPSocketV2 | public concrete type, optional | 优先不要求调用方直接构造；若公开，构造函数应隐藏依赖并保持 PIMPL | 不在头文件中放置 Core 成员、Asio 类型或 thread |
| SocketFactoryV2 | public static factory | create(ProtocolType) -> Result<shared_ptr<SocketV2>> | 不抛出 unsupported protocol 作为正常控制流；错误可观测 |
| EndpointConfig | public value type | local/remote address、port、bind mode | 需校验端口/地址；不得包含 Asio endpoint |
| OperationResult | public value type | success/code/operation id/native error/after snapshot | std::string/vector 使 ABI 受编译器/标准库 ABI 约束；见第5节 |
| SocketSnapshot | public value type | 资源状态、阶段、计数、generation | 标注快照一致性等级；不得暴露 native socket handle 作为所有权入口 |
| SocketErrorCode / TransportState / ReceiveState | public enum class | 显式固定 underlying type，如 uint32_t | enum 数值发布后不可重排复用；新增值仅 append |
| NativeError | public value type | category id/value/message | 原生错误类别字符串作为诊断，不暴露 Boost 类型 |

建议 public API 的第一版只保证 source compatibility（同一 toolchain / build），不要在没有 ABI CI 和版本承诺前宣称跨 ROS 发行版、跨编译器或跨 libstdc++ ABI 稳定。若确需长期二进制 ABI，优先考虑 opaque C ABI 或稳定 handle + C functions；C++ STL value types 不适合作为跨工具链稳定 ABI。

## 5. Result / Snapshot 的 ABI 策略

SERVO-875 的直观 struct 伪代码含 std::string 与多个 STL 成员，便于设计但不能自动视为稳定 ABI。实现前必须二选一：

**策略 A：C++ source-level API（推荐当前仓库短期采用）**
- 在包版本 0.x 范围明确 ABI 不承诺跨 compiler / standard library / build flags；同一工作区源码重编译。
- public value types 可以使用 std::string、std::vector，但不允许跨 DLL/不同 CRT 分配释放对象。
- 所有返回对象在调用方编译单元构造/析构；库边界只传值或 const reference，不提供由库分配且要求调用方 delete 的裸指针。
- 发布后 enum 数值不重排；虚函数顺序不改；不在已发布 struct 中间插字段。

**策略 B：稳定二进制 ABI（如未来需要第三方插件独立升级）**
- public façade 使用 opaque handle / pImpl，类对象不暴露 STL 成员和布局。
- 使用固定宽度整数、调用方提供 buffer 或 size-query API 传输字符串；错误文本可选。
- 定义 ABI version、struct_size、reserved 字段、显式导出宏和跨平台 ABI CI。
- 采用 C ABI 或经过严格 ABI policy 管理的接口；所有分配/释放在同一模块内完成。

禁止混用两种策略：不能一方面暴露含 STL 的 public struct，一方面宣称稳定跨编译器 ABI。

## 6. UDP Core 单一所有权图

推荐结构（概念图）：

    RobotDriver / Subscriber
             | shared_ptr<SocketV2>
             v
        UDPSocketV2 façade
             | shared_ptr<UdpSocketCore>  (唯一 control block)
             v
        UdpSocketCore  [private]
          |-- asio::udp::socket
          |-- io_context / work guard
          |-- receive worker thread
          |-- endpoint + connect stage
          |-- callback admission gate
          |-- pending handler counter
          |-- active callback counter
          |-- lifecycle mutex / state mutex
          |-- generation + last native error
             ^
             | optional internal adapter, not independent ownership
        Legacy UDPSocket facade

这里的 legacy facade 不应在默认方案中与 v2 facade 同时操控同一个 Core，因为 legacy bool API 无法表达 v2 residual contract。优先策略是：legacy UDPSocket 继续保留现有独立 impl，v2 facade 创建自己的 Core；两者共享算法/低层 helper 可以，但不共享活动 socket 实例。只有未来经过明确迁移并验证的 adapter 场景，才允许 legacy façade 持有 shared_ptr<Core>，且 Core 仍是唯一 native resource owner。

更安全的兼容边界：
- legacy UDPSocket 保持其 unique_ptr<UDPSocketImpl>、符号与行为不变；不做热切换或隐式转接。
- UDPSocketV2 新建 private shared_ptr<UdpSocketCore>，Core 析构前必须已满足 stopped/joined/closed，不能靠 Core 析构替代显式 stop。
- shared_ptr 只解决 Core 对象内存寿命，不自动解决线程与 callback 生命周期；worker 与 handler 不得捕获 owning shared_ptr 造成 self-cycle，也不得只捕获裸 Core this 而没有 join barrier。
- worker 可以捕获 weak_ptr 并在 handler 入口 lock；但最终 shutdown 必须在非 worker 控制线程完成 drain/join。禁止 worker 自己释放最后一个 owner 并触发自身 join/destructor。
- `SocketSnapshot` 不得返回可复制、可关闭的原生 handle；原生句柄只供 Core 内部使用。

## 7. Callback / worker 生命周期顺序

规定唯一 shutdown 顺序：

1. 在 Core lifecycle mutex 下从 RUNNING 转 STOPPING，关闭 callback admission 并递增/冻结 generation。
2. cancel socket receive operation，记录 cancel error；不能因 cancel 失败就跳过后续清理。
3. 等待 pending handler 完成或被取消并销毁；handler RAII 递减 pending count。
4. 已进入 callback 的任务完成，active callback count 归零；新 callback 被 gate 拒绝。
5. 停止 io_context 并 join worker；禁止 self-join / detach。
6. close native socket，读取 final snapshot。
7. 只有 handle closed、handler/callback 计数为零、worker 不 joinable，才能返回 quiescent STOPPED。

若 stop timeout：返回 FAILED_RESIDUAL，Core owner 和 worker 状态必须仍由上层生命周期管理器保留；调用方不能 reset 最后一个 shared_ptr。需要 retry-stop 或显式 quarantine owner API。析构 noexcept best-effort 仅为最后防线，不能被视为成功清理证明。

## 8. Factory / Result API 的具体约束

推荐签名形状（仅设计伪代码）：

    class SocketFactoryV2 final {
    public:
      static FactoryResult create(ProtocolType type);
    };

    struct FactoryResult {
      std::shared_ptr<SocketV2> socket;
      SocketErrorCode error;
      bool success() const noexcept;
    };

不建议直接返回 `std::shared_ptr<SocketV2>` 并用异常表达 TCP unsupported；factory 正常失败应为结果值。若采用 `std::expected`，必须确认 C++ 标准版本（当前项目 C++17，std::expected 不属于标准 C++17），或引入经批准的兼容 Result 类型。Factory 不得偷偷 fallback 到 legacy Socket，因为那会使调用方误以为拥有 snapshot/drain 能力。

## 9. CMake、安装、导出和符号可见性

固定上游 CMake 目前 `install(DIRECTORY include/ DESTINATION include)` 会自动安装新增 public header；`add_library(staubli_robot_driver SHARED ...)` 构建共享库，并 `ament_export_targets(export_staubli_robot_driver HAS_LIBRARY_TARGET)` 导出 target。当前没有专门的 visibility header、`*_PUBLIC` 导出宏或显式 `CXX_VISIBILITY_PRESET`。

实施时建议：
- 新增 source 显式加入 `LIBRARY_SOURCES`，不要仅因 header 已安装就认为实现已链接。
- 新增 `visibility_control.hpp`，定义 `STAUBLI_ROBOT_DRIVER_PUBLIC` / `STAUBLI_ROBOT_DRIVER_LOCAL`，覆盖 GCC/Clang visibility 与 Windows `__declspec(dllexport/dllimport)`；先盘点当前公共符号再逐步应用，避免一次性隐藏现有符号。
- 头文件声明的 public class/static factory 标记 PUBLIC；private Core 类和 helper 标记 LOCAL 或保持 TU 内部。
- 若采用 `CXX_VISIBILITY_PRESET hidden`，必须同时设置 `VISIBILITY_INLINES_HIDDEN` 并逐个导出 API；此改动属于全库 ABI/符号变更，不应与 SocketV2 首个实现切片捆绑。
- 用 `ament_export_targets` 和 package dependency export 检查消费方链接；当前 CMake `ament_export_dependencies` 未列 Boost，但 public headers 不暴露 Boost 后，Boost 可继续是实现私有依赖，仍需验证导出目标的链接接口。
- 加入 nm/readelf（Linux）与 dumpbin（Windows，如支持）符号清单基线；对比 legacy symbols 未消失，v2 symbols 只新增。
- `package.xml` 版本 0.1.4 没有 ABI policy；若 public ABI 真正变化，必须决定 package semantic version / ABI versioning 方案，不能默认为 patch release。

## 10. 实施顺序与变更隔离

| Slice | 变更 | 禁止混入 | 通过门禁 |
|---|---|---|---|
| ABI-0 | 记录 legacy exported symbols、头文件签名、编译器/平台 ABI policy | 不改旧 Socket、UDPSocket、factory | 基线报告与 consumer compile fixture |
| ABI-1 | 新增 visibility_control.hpp、socket_v2_types.hpp、socket_v2.hpp、socket_factory_v2.hpp | 不开启全库 hidden visibility | public header standalone compile、symbol export smoke |
| ABI-2 | 新增 UdpSocketCore private PIMPL，UDPSocketV2 façade 独占 Core | 不让 legacy facade 双重持有 Core | ownership review、lifetime test |
| ABI-3 | 增加 v2 factory 与 UDP create 路径；TCP unsupported result | 不 fallback legacy socket | factory result / unsupported test |
| ABI-4 | 接入 connect snapshot、stop drain、cleanup report | 不同时重构 RobotDriver/Subscriber | fault-injection matrix + TSAN |
| ABI-5 | 调用方逐步迁移、legacy deprecation（另行审批） | 不删除 legacy API | ROS integration + downstream consumer build |

## 11. 验收规格（全部 NOT_RUN）

| ID | 验收项 | 状态 |
|---|---|---|
| ABI-01 | legacy socket.hpp 预处理后签名与 virtual slot 清单保持不变 | NOT_RUN |
| ABI-02 | legacy UDPSocket layout / constructor / destructor / factory symbols 不被移除 | NOT_RUN |
| ABI-03 | public v2 headers 可独立 include，不需要 Boost.Asio include path | NOT_RUN |
| ABI-04 | v2 public headers 不泄露 Asio、thread、mutex、Core private type | NOT_RUN |
| ABI-05 | visibility macro 在 Linux shared library 导出 v2 symbols | NOT_RUN |
| ABI-06 | Windows DLL 导出/导入编译 smoke（若平台受支持） | NOT_RUN |
| ABI-07 | nm/readelf 符号 diff：legacy symbols 不减少、v2 symbols 只新增 | NOT_RUN |
| ABI-08 | FactoryResult 对 TCP 返回明确 UNSUPPORTED_PROTOCOL，不创建 legacy fallback | NOT_RUN |
| ABI-09 | Core 只有一个 native socket owner/control block，不出现双重 close | NOT_RUN |
| ABI-10 | callback/worker 不形成 shared_ptr self-cycle，最后 owner 不在 worker 线程销毁 | NOT_RUN |
| ABI-11 | stop timeout 后 Core owner 保留、worker joinable 状态真实反映 | NOT_RUN |
| ABI-12 | shutdown 顺序满足 admission close -> cancel -> handler drain -> callback drain -> join -> close | NOT_RUN |
| ABI-13 | snapshot 不暴露可被调用方关闭的 native handle | NOT_RUN |
| ABI-14 | CMake target/export/install 下游消费方可链接 v2 API | NOT_RUN |
| ABI-15 | package version / ABI policy 与 public surface 变更保持一致 | NOT_RUN |
| ABI-16 | legacy 与 v2 facade 不会并发操控同一底层 UDP Core | NOT_RUN |

## 12. 风险、非目标与验收边界

- 本报告是静态源码与接口设计审查，不证明 GCC/Clang/MSVC 的实际符号导出、类布局、链接或运行时行为。
- 未新增任何 public header、visibility macro、SocketV2 类、factory、Core、adapter 或 CMake source。
- ABI-01 至 ABI-16 全部 NOT_RUN；未运行编译、gtest、nm/readelf、Windows DLL smoke、TSan、loopback 或 ROS 2 Control 集成。
- 未执行 SIL/HIL、VAL3/CS9、FAT/SAT 或实机验证；工程级验收未通过。
- 未修改固定上游源码，未应用/合并 PR；TODO-EXT-001 仍未授权。

## 13. 下一节点

§9.3.294 / SERVO-877：SocketV2 header dependency closure、public type layout 与 factory Result API 的 C++17 编译契约设计。重点逐头文件列出 include closure、forward declaration、incomplete-type destructor placement、C++17 Result/Expected 方案、enum underlying value 固定策略和 standalone consumer fixture；仍先做设计，不修改上游。
