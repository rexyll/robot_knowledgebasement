# Stäubli SocketV2 Production/Test Isolation、Plugin Unload Lifecycle 与 Legacy ABI Architecture Decision

- 节点：§9.3.310 / SERVO-893
- 日期：2026-11-10
- 固定上游：`ICube-Robotics/staubli_driver_ros2@bd658e2d266e315d2ee35f985fb352ea88306b79`
- 固定Tree：`257face41970c91f95890ddf47db40b168eca331`
- 关联设计：SERVO-874（init/stop契约）、SERVO-875（V2兼容迁移）、SERVO-877（public header/ABI）、SERVO-879（plugin/callback生命周期）、SERVO-884（资源owner/DAG）、SERVO-885（F01–F16故障矩阵）、SERVO-886（Fake seam）、SERVO-887（private interface/PIMPL与test-only wiring）、SERVO-891/892（clean Jazzy、install/export/plugin artifact）
- 性质：架构决策与验收追踪；只读固定commit源码审查，不代表实现、构建、ABI或运行测试完成。

## 1. 决策摘要

本专项建议冻结以下架构方向，作为未来Slice A1实现的设计准入条件：

1. **生产/测试分离：** production plugin只依赖production driver/core与Asio backend；FakeTransport、FaultScript、DeterministicExecutor、test factory仅进入`BUILD_TESTING=ON`下的test-only target，不安装、不导出、不被plugin链接。
2. **单一生命周期核心：** Asio与Fake驱动同一份SocketCore、状态机、generation fencing和CleanupCoordinator源代码；不允许Fake复制另一套清理逻辑。
3. **Plugin卸载屏障：** 先停止新的callback admission，再cancel/close异步接收源，drain已进入的callback，等待worker退出并join，确认所有callback lease和plugin code lease归零，最后才释放SocketCore、HardwareInterface实例与plugin DSO。任何步骤超时/失败都必须保留owner并返回明确失败，不得detach线程后释放对象。
4. **ABI保护：** 不改变legacy Socket纯虚接口、SocketFactory既有签名、既有public类数据布局/vtable/inline析构语义；不将private seam、Fake或内部Core放入安装头文件和ament export。现有HardwareInterface/RobotDriver等public类若需要增加实例状态，必须先证明不改变布局，或明确转入ABI major-change审批；当前无此授权。
5. **证据门禁：** 依赖图、install manifest、导出符号、ABI structural diff、consumer、plugin load/unload与sanitizer均须有真实工件。静态方案不计为PASS；A1.1继续BLOCKED。

推荐对象边界：

```text
plugin loader / host
  └─ StaubliHardwareInterface (existing plugin ABI; no layout change)
      └─ RobotDriver (legacy public ABI preserved)
          └─ SocketV2 facade (new stable public API, PIMPL)
              └─ SocketCore (single lifecycle/state machine owner)
                  ├─ ITransportBackend (private, non-installed)
                  │   ├─ AsioUdpBackend (production only)
                  │   └─ FakeBackend (test-only variant)
                  ├─ CleanupCoordinator
                  ├─ CallbackAdmissionGate / CallbackLease
                  └─ WorkerState + NativeResourceOwner
```

这是设计结构，不是固定上游现状。不能因图中出现shared owner就默认允许多方拥有native handle；native resource仍必须只有一个可追踪owner。

## 2. 固定上游新核验事实与生命周期风险

### 2.1 UDP Impl 与异步回调

固定文件 `staubli_robot_driver/src/communication/udp_socket_impl.hpp`，blob `1309a8f2d59e8295869e178af82a66868bb911ff`：

- `start_receive_thread`保存callback，设置receiving标志，发起async receive，再启动worker执行`io_service_.run()`。
- async handler以`[this]`捕获UDPSocketImpl，并进入`handle_data_received`；该方法直接调用`reception_callback_`，之后依据receiving标志决定是否继续发起接收。
- `stop_receive_thread`执行`io_service_.stop()`、`receive_thread_.join()`，再将receiving置false；没有显式返回callback drain计数、pending handler数或join阶段结构化报告。join异常也没有在该函数内转换成OperationResult。
- `disconnect`在connected为true时尝试stop，随后close；即使close抛异常，也会把`is_connected_`设为false。这样逻辑连接标志可能与native socket真实open状态分离。后续再次disconnect若看到connected=false，会走“not connected”分支并返回默认all_ok=true，不能证明此前close失败的native资源已经清理。
- `UDPSocketImpl::~UDPSocketImpl`仅在`is_connected()`为true时调用disconnect；若connected标志与native open状态不一致，析构重试可能被跳过。

上述是代码控制流风险，不代表本轮复现了close失败或资源泄漏。

### 2.2 Subscriber callback对象生命周期

固定文件：
- `src/real_time_socket_subscriber.cpp` blob `e2cd8fc50b2b13d9e31b2c024e90f9da76107622`
- `include/staubli_robot_driver/real_time_socket_subscriber.hpp` blob `330839cb25e53fe961541f29f634722bec4a47c4`

构造期间自动调用init；接收lambda以`[this]`捕获Subscriber并调用update_message；析构调用`socket_->stop_receive_thread()`。现有stop/join在正常线程路径上会等待worker退出，但接口没有独立callback admission/active lease/drain结果，也没有明确处理从worker callback自身触发stop导致self-join的策略。不能把“析构里调用stop”视为完整、可诊断的生命周期协议。

### 2.3 RobotDriver与HardwareInterface teardown

固定文件：
- `src/robot_driver.cpp` blob `ede48a314856a455df9d8434f354aaf9fbc47bff`
- `src/staubli_hardware_interface.cpp` blob `4ae2b8c8d91857e5e32558bfcd16e2c391b9c3d0`
- `include/staubli_robot_driver/staubli_hardware_interface.hpp` blob `a84d0c63b15db168ea453a15571ab1494b8f9e99`

发现：
- RobotDriver析构函数为空；disconnect先reset control interface和diagnostics subscriber，再分别stop与disconnect两个socket。stop失败只记录warning，后续仍尝试disconnect；状态重置后返回合并bool。
- HardwareInterface析构调用RobotDriver::disconnect但忽略返回值。
- on_cleanup调用disconnect但忽略返回值，始终返回SUCCESS。
- on_shutdown仅在`robot_driver_->is_connected()`为true时发送STOP（如需要）并disconnect；若逻辑连接状态为false但底层资源残留未知，该分支不会主动检查残留。
- on_error只尝试发送STOP，不执行disconnect；这是error lifecycle的现有策略，不应误称为完整teardown。
- plugin class使用现有导出宏注册；本轮没有实际plugin unload/load循环证据。

这些行为说明现有生命周期接口没有向ROS lifecycle/plugin host完整传播清理结果；并不证明plugin unload已发生use-after-free。

## 3. Architecture Decision Record

### ADR-01：Private transport seam + PIMPL

**决定：** 采用private abstract backend interface + PIMPL + 单一SocketCore。

- interface只存在于src/private/detail目录，不进入include安装树。
- 新V2 public facade只暴露稳定值类型、明确错误域和PIMPL句柄；不暴露Asio、thread、mutex、Core或Fake类型。
- AsioUdpBackend是production唯一默认backend；生产factory不读取环境变量/ROS参数切换Fake。
- FakeBackend只能通过测试构建私有builder注入同一SocketCore逻辑。
- 不使用模板policy作为默认方案；只有性能剖析证明virtual dispatch是瓶颈才重新评估。
- 不使用function table作为当前同模块C++内部默认方案；跨DSO/C ABI需求另行立项。

状态：DESIGN_DECIDED；实现NOT_RUN。

### ADR-02：Production/Test target boundary

建议target层次：

| Target | 内容 | 链接关系 | install/export |
|---|---|---|---|
| `staubli_robot_driver` | 既有生产driver/API与production SocketV2 facade | 依赖production core/backend | 既有生产库按批准API导出 |
| `staubli_robot_driver_hardware_interface` | ROS2 control plugin | 仅链接生产driver/core | 生产plugin照常安装/注册 |
| `staubli_socket_core_test_variant` | 同一SocketCore源码 + Fake backend/test injection | 仅供测试可执行文件 | 不安装、不导出 |
| `staubli_socket_test_support` | FaultScript、DeterministicExecutor、barrier/latch helpers | 仅测试目标 | 不安装、不导出 |
| `test_socket_core_fake` | 对相同Core源码的确定性故障测试 | 链接test variant + gtest | 不安装 |
| `test_socket_core_asio` | 生产Asio backend loopback/integration测试 | 链接生产库 + gtest | 不安装 |

关键构建约束：
- production core/plugin不得链接gtest、FakeBackend、FaultScript、DeterministicExecutor或test_support。
- Fake测试变体编译同一份Core实现源文件，但不能与production shared library在同一测试进程中重复链接同名Core定义；Fake单元测试和Asio生产集成测试分成独立可执行文件。
- 若采用object/static library共享Core对象，必须通过target graph证明最终每个进程只有一份权威Core定义；不得让production DSO与test variant同时提供同一组全局符号。
- BUILD_TESTING=OFF时不存在Fake/test_support/test-only factory目标；BUILD_TESTING=ON时只增加测试目标，不改变production target的PUBLIC/INTERFACE属性。
- 测试宏仅PRIVATE传播到测试变体/可执行文件；禁止改变跨translation unit共享类型定义。
- Fake/private headers不得被`install(DIRECTORY include/)`无过滤地收录；未来实现需建立明确public header allowlist或将private headers放在include目录之外。
- test-only targets不进入`ament_export_targets`、package.xml export或plugin dependency。
- 不允许“先把Fake编进production，再依赖dead-strip/链接器优化去掉”的做法。

状态：TARGET-ADR-01 SPECIFIED；CMake graph未执行。

### ADR-03：Callback admission、drain与plugin unload屏障

定义必须分开的状态：

- `AdmissionState`: OPEN / CLOSING / CLOSED
- `PendingHandlerCount`: 已排队但尚未进入用户callback的handler数
- `ActiveCallbackCount`: 已取得lease并进入callback的数量
- `WorkerState`: NOT_STARTED / RUNNING / EXIT_REQUESTED / EXITED / JOINED / JOIN_FAILED
- `NativeResourceState`: OPEN / CLOSE_PENDING / CLOSED / CLOSE_OUTCOME_UNKNOWN
- `PluginCodeLeaseCount`: 仍可能执行plugin text、析构器、vtable、custom deleter或回调目标代码的lease数量

Callback合同：
1. callback入口必须先尝试获取CallbackLease；admission关闭后，新callback不得进入用户代码。
2. Lease使用RAII计数，所有正常/异常/取消路径都必须归还。
3. close admission与cancel receive必须有明确顺序，避免在关闭窗口新handler重新排队。
4. CleanupCoordinator等待pending handler完成/取消、active callback归零；等待必须有deadline和可观测失败结果。
5. callback执行期间不允许同步等待自身lease归零；worker线程发起stop必须采用拒绝并转交控制线程，或只发出stop request，不得self-join。
6. drain超时或join失败时，保留Core、backend、callback target和plugin code owner；报告RESIDUAL，不detach后释放。
7. 所有引用plugin代码的回调、析构器、虚表、custom deleter必须在卸载DSO前完成；只确认对象析构开始不够。

推荐关闭序列：

```text
Host stops new hardware read/write and command admission
  -> close callback admission gate
  -> request cancellation / stop async receive source
  -> account for queued handlers (run-to-completion or explicit cancel completion)
  -> drain active callback leases to zero
  -> request worker exit
  -> join worker (never detach-and-free)
  -> reconcile native socket close and residual ownership
  -> destroy subscriber/interface/core and callback targets
  -> verify plugin-code leases == 0
  -> destroy plugin instance / release class-loader DSO
```

若某一步失败：停止推进到“释放owner/卸载DSO”，保存CleanupReport和ResidualResourceHandle，交由唯一Quarantine/Reconcile owner处理；不把逻辑connected=false当作native close证据。

**重要安全边界：** STOP命令/机械停止请求与软件资源teardown是不同操作。on_error中的STOP命令不能替代callback drain、worker join或socket close。机械安全停止仍须遵循机器人安全架构与现场安全流程，不能由软件卸载屏障代替。

状态：LIFECYCLE-ADR-01 SPECIFIED；没有运行时屏障实现。

### ADR-04：ROS lifecycle callback contract

未来适配层需对每个ROS callback显式定义：
- on_cleanup：执行完整teardown transaction；所有资源终态确认后才返回SUCCESS；任何未知残留必须返回ERROR并保留诊断报告。
- on_shutdown：尽力执行STOP（若通信仍可用），随后无条件进入teardown检查，不能只用is_connected短路资源盘点。
- on_error：按批准安全策略尝试STOP并记录结果；是否继续disconnect需由安全需求明确规定，但必须报告资源状态，不能把STOP成功视为teardown成功。
- destructor：noexcept best-effort最后防线，不承担唯一的可观测清理责任；必须避免在worker线程自销毁或卸载plugin code仍被callback引用时释放对象。
- lifecycle与host卸载编排必须保证先停止read/write调用，再drain后台callback，最后释放plugin实例/DSO。

由于现有HardwareInterface类是public plugin ABI的一部分，不允许在未完成ABI评估前新增成员、改变基类、vtable或布局来保存新的gate。优先评估source-local/private implementation与既有对象内部owner方案；若不可行，先提交ABI major-change选项，不得偷偷改变布局。

状态：LIFECYCLE-ROS-01 SPECIFIED；当前上游实现不符合上述完整结果传播合同（STATIC_REVIEWED）。

## 4. Legacy ABI Guard Matrix

### 4.1 不可变合同

- 不新增/重排legacy Socket virtual成员，不改变纯虚函数签名或析构语义。
- 不改变SocketFactory现有工厂签名、参数/返回类型与既有行为合同。
- 不改变legacy UDPSocket、RobotDriver、StaubliHardwareInterface等已安装public类的sizeof/alignof/数据成员顺序/vtable，除非先批准major ABI变更。
- 不把private ITransportBackend、SocketCore、Fake、FaultScript、CallbackLease或test factory安装/导出。
- 新V2符号与legacy ABI diff分开报告；新增V2符号不能抵消legacy符号丢失。
- 所有ABI比较必须使用同架构、同编译器、同C++标准、同visibility、同宏定义、同依赖版本和构建参数的baseline/candidate。

### 4.2 守护追踪表

| ID | 守护项 | 方法/工件 | 状态 |
|---|---|---|---|
| ABI-G01 | legacy public header/API snapshot | 预处理签名/API dump | NOT_RUN |
| ABI-G02 | legacy vtable/virtual order | ABI structural diff + review | NOT_RUN |
| ABI-G03 | public class layout | sizeof/alignof/layout probe | BLOCKED（baseline未构建） |
| ABI-G04 | exported legacy symbols | nm -D/readelf -Ws diff | NOT_RUN |
| ABI-G05 | ABI structural comparison | abi-dumper/abi-compliance-checker或等价工具 | BLOCKED |
| ABI-G06 | installed public header allowlist | install manifest/header diff | NOT_RUN |
| ABI-G07 | include closure与export target | 独立consumer A/B + generated CMake export | NOT_RUN |
| ABI-G08 | plugin XML/ament index | 安装后resource index/plugin metadata diff | NOT_RUN |
| ABI-G09 | plugin runtime load/unload | repeated load/unload + lease assertions | NOT_RUN |
| ABI-G10 | legacy consumer link/run | 只使用旧SocketFactory/Socket API的consumer | NOT_RUN |
| ABI-G11 | V2 symbol partition | legacy/V2 symbol allowlist与diff | NOT_RUN |
| ABI-G12 | test-only leakage | install manifest、DT_NEEDED、nm、target graph | NOT_RUN |
| ABI-G13 | plugin DSO dependencies | readelf -d、RPATH/RUNPATH、依赖解析 | NOT_RUN |
| ABI-G14 | sanitizer lifecycle stress | ASan/UBSan/TSan及重复卸载压力 | NOT_RUN |

## 5. Plugin unload验收矩阵

| ID | 场景 | 必须证明 | 状态 |
|---|---|---|---|
| PLUG-L01 | 正常cleanup | admission关闭、callback归零、worker joined、native资源closed | NOT_RUN |
| PLUG-L02 | shutdown且is_connected=false但native状态未知 | 仍执行资源盘点/reconcile，不短路 | NOT_RUN |
| PLUG-L03 | on_error STOP失败 | STOP结果与teardown结果分离；不伪装安全完成 | NOT_RUN |
| PLUG-L04 | callback执行中请求unload | unload等待lease归零；无UAF | NOT_RUN |
| PLUG-L05 | pending handler在cancel期间完成 | 不重新进入已关闭的用户callback | NOT_RUN |
| PLUG-L06 | callback触发stop | 不self-join；stop请求转交非worker控制路径 | NOT_RUN |
| PLUG-L07 | worker join失败/超时 | owner保留、返回RESIDUAL；不detach/free | NOT_RUN |
| PLUG-L08 | native close抛异常 | connected flag不冒充native closed；owner保留 | NOT_RUN |
| PLUG-L09 | callback持有plugin-defined deleter/vtable | 所有plugin code lease在DSO unload前归零 | NOT_RUN |
| PLUG-L10 | 反复plugin load/unload | 多轮后无线程、fd、callback、symbol残留 | NOT_RUN |
| PLUG-L11 | 两通道部分清理 | control/diagnostics独立状态和重试 | NOT_RUN |
| PLUG-L12 | lifecycle callback重复/乱序 | 幂等且保留未知资源状态 | NOT_RUN |

## 6. Test-only target acceptance

| ID | 检查 | 通过条件 | 状态 |
|---|---|---|---|
| ISO-G01 | BUILD_TESTING=OFF | Fake/test_support/test factory目标不存在 | NOT_RUN |
| ISO-G02 | BUILD_TESTING=ON | test-only targets存在且仅由测试消费 | NOT_RUN |
| ISO-G03 | production target graph | production core/plugin无gtest/Fake依赖 | NOT_RUN |
| ISO-G04 | test variant source identity | Core实现源文件与production一致，差异仅backend binding/test injection | NOT_RUN |
| ISO-G05 | no duplicate Core ODR | 每个测试进程只有一个权威Core定义 | NOT_RUN |
| ISO-G06 | install/export allowlist | 无Fake/private/test-support头、库、target | NOT_RUN |
| ISO-G07 | plugin DSO scan | DT_NEEDED无test support，动态符号无Fake/FaultScript | NOT_RUN |
| ISO-G08 | test macros | test-only compile definitions不传播到production/public headers | NOT_RUN |
| ISO-G09 | production default | 默认factory只创建Asio backend | NOT_RUN |
| ISO-G10 | same state machine | Fake/Asio对同一Core生命周期合同执行相同断言 | NOT_RUN |

## 7. 分阶段实现与准入门

| 阶段 | 内容 | 先决条件 | 本节点结论 |
|---|---|---|---|
| A1.1 | private seam、PIMPL与单Core边界 | ABI边界/owner模型批准；Asio来源和baseline证据可用 | BLOCKED |
| A1.2 | Asio backend adapter与production路径 | A1.1通过；legacy行为映射清楚 | NOT_AUTHORIZED |
| A1.3 | test variant/Fake/FaultScript | target隔离与ODR策略冻结 | NOT_AUTHORIZED |
| A1.4 | callback gate/worker/cleanup transaction | 生命周期状态机与失败owner已审查 | NOT_AUTHORIZED |
| A1.5 | plugin lifecycle/unload integration | host调用顺序、结果传播与DSO lease合同 | NOT_AUTHORIZED |
| A1.6 | ABI/install/export/consumer guards | 可复现baseline和SERVO-892风险闭合 | NOT_AUTHORIZED |
| A1.7 | 验收与上游变更 | 所有适用静态、构建、运行、ABI和安全门通过且取得用户授权 | NOT_AUTHORIZED |

准入禁止条件：
- `asio_SOURCE_DIR` provenance未解决；
- clean Jazzy build/rosdep依赖闭包未验证；
- ABI baseline未建立；
- install-space consumer与plugin export未通过；
- test-only隔离没有target graph和二进制证据；
- callback drain/worker join/native close的失败残留没有唯一owner；
- 用户未授权上游实现（`TODO-EXT-001`仍未授权）。

## 8. 本节点验收状态

| ID | 项目 | 状态 |
|---|---|---|
| SRC-LIFE-01 | UDP callback/stop/disconnect源码控制流 | STATIC_REVIEWED |
| SRC-LIFE-02 | Subscriber捕获与析构stop路径 | STATIC_REVIEWED |
| SRC-LIFE-03 | RobotDriver/HardwareInterface lifecycle传播 | STATIC_REVIEWED |
| ADR-01 | Private interface + PIMPL + single Core | DESIGN_DECIDED |
| ADR-02 | production/test target隔离 | SPECIFIED |
| ADR-03 | callback admission/drain/plugin unload屏障 | SPECIFIED |
| ADR-04 | ROS lifecycle teardown结果合同 | SPECIFIED |
| ABI-G01至G14 | ABI/install/export/consumer/DSO守护 | NOT_RUN/BLOCKED |
| PLUG-L01至L12 | plugin unload运行验收 | NOT_RUN |
| ISO-G01至G10 | test-only target验收 | NOT_RUN |
| A1.1-GATE | Slice A1实现准入 | BLOCKED |

## 9. 限制与下一节点

本节点只读取固定commit源码并整合既有设计；未运行CMake/colcon/gtest、Fake故障注入、callback并发、plugin load/unload、readelf/nm、ABI工具、sanitizer、SIL/HIL或实机测试。未修改固定上游、未创建/应用/合并PR；`TODO-EXT-001`仍未授权。§9.3.281–§9.3.294历史同步缺口继续透明保留。

**下一节点：§9.3.311 / SERVO-894：基于SERVO-893矩阵构建“生命周期事件—资源状态—owner转移—失败残留—测试用例”五维追踪表，逐一映射F01–F16与PLUG-L01–L12，并检查每条失败路径是否存在唯一reconcile owner；仍不修改上游。**
