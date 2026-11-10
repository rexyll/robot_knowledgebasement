# Stäubli SocketV2 Private Transport Seam 实现策略、Legacy ABI Guard 与 Test-only CMake Wiring Review

- **节点：** §9.3.304 / SERVO-887
- **日期：** 2026-11-10
- **固定上游基线：** `ICube-Robotics/staubli_driver_ros2@bd658e2d266e315d2ee35f985fb352ea88306b79`
- **关联节点：** SERVO-875（V2兼容迁移）、SERVO-877（public header与ABI边界）、SERVO-884（真实资源所有权）、SERVO-885（F01–F16测试矩阵）、SERVO-886（fake transport seam合同）
- **性质：** 实现策略与构建/ABI防护静态审查；不代表实现、编译、ABI比较或测试已完成。

## 1. 目标

冻结 Slice A1 的实现策略，回答四个工程问题：

1. transport seam 放在哪一层，如何避免进入 public/install header 和 plugin ABI；
2. production Asio backend 与 test-only fake 如何共享同一套状态机与资源所有权逻辑；
3. CMake 如何保证 FakeTransport、fault script、deterministic executor 仅被测试目标使用；
4. 如何通过构建产物、导出符号、安装消费测试和ABI基线比较，证明旧接口未被意外改变。

本节点不实施上游改动，不声称已有V2实现，不推定固定commit之外的文件状态。

## 2. 约束与决策原则

- **ABI优先：** 不修改legacy Socket纯虚接口、既有SocketFactory签名、旧类布局或既有vtable；不在legacy public class中新增virtual、数据成员或改变inline析构语义。
- **PIMPL隔离：** 新V2 facade若实施，应将Core/backend指针置于private Impl；public header只保留必要前置声明与稳定值类型。
- **单一状态机：** Fake与Asio backend必须驱动同一个SocketCore/cleanup coordinator；禁止维护两套独立生命周期逻辑。
- **测试替换私有化：** 注入构造入口只存在于private/detail或test-support，不安装、不导出、不被ROS plugin依赖。
- **默认生产路径固定：** 用户调用正常生产factory时，必须创建Asio backend；不得通过环境变量、ROS参数或运行时配置意外切换Fake。
- **异常语义一致：** fake不得吞掉生产实现会传播的异常；backend错误必须保留错误域、阶段、副作用状态。
- **可证伪：** ABI、install/export、符号、依赖闭包与测试隔离均须由实际产物检查，不能仅凭CMake源文件阅读判定通过。

## 3. 三种 seam 策略的深入比较

### 3.1 Private abstract interface（私有抽象接口）

形态候选：

```cpp
namespace staubli::detail {
class ITransportBackend {
public:
  virtual ~ITransportBackend() = default;
  virtual BackendResult open(const Endpoint&) = 0;
  virtual BackendResult bind(const Endpoint&) = 0;
  virtual BackendResult start_receive(ReceiveCompletion) = 0;
  virtual BackendResult cancel_pending() noexcept = 0;
  virtual BackendResult close_native() noexcept = 0;
  virtual NativeSnapshot snapshot() const noexcept = 0;
};
}
```

优点：
- Asio与Fake可在运行时替换，容易复用SocketCore与状态机。
- 测试可以按generation注入不同backend行为。
- private interface不属于稳定public ABI时，内部实现可独立演进。
- 类型边界清晰，便于fake记录operation journal。

风险：
- 每次backend操作增加一次间接调用；通常远小于UDP/系统调用成本，但必须通过benchmark确认关键热路径影响。
- interface对象、completion和Core的销毁顺序必须明确。
- 若detail header被安装或符号默认可见，仍可能意外扩大ABI面。
- 不应把callback生命周期交给backend隐式管理。

控制措施：
- interface放在未安装的私有头文件。
- 使用PIMPL持有backend，Core拥有唯一backend owner。
- 默认hidden visibility；只导出既有public API。
- backend destructor不得自行绕过CleanupCoordinator关闭资源。
- interface不暴露ROS类型、裸handle owner或业务callback target。

### 3.2 Template policy

形态候选：`BasicSocketCore<BackendPolicy>`，生产实例化Asio policy，测试实例化Fake policy。

优点：
- 可内联，避免virtual dispatch。
- 编译期限制backend能力与类型。
- 无需为每次操作进行虚函数分派。

风险：
- Core与cleanup状态机容易因模板分支而分叉。
- 头文件暴露与编译依赖增加，PIMPL边界更复杂。
- 运行时factory、测试注入和插件构造更难组织。
- 多种policy实例化可能增加编译时间和二进制体积。
- 测试模板实例与生产模板实例可能意外产生不同代码路径，降低验证代表性。

适用条件：
- 经性能剖析证明virtual dispatch确实成为瓶颈；
- backend类型集合固定且编译期选择足够；
- 模板实现可保持同一状态机与同一测试合同。

当前不建议作为Slice A1默认方案。

### 3.3 Function table + opaque context

形态候选：

```cpp
struct TransportOps {
  BackendResult (*open)(void*, const Endpoint&);
  BackendResult (*bind)(void*, const Endpoint&);
  BackendResult (*start_receive)(void*, ReceiveCompletion);
  BackendResult (*cancel_pending)(void*) noexcept;
  BackendResult (*close_native)(void*) noexcept;
  NativeSnapshot (*snapshot)(const void*) noexcept;
};
struct TransportBinding {
  void* context;
  const TransportOps* ops;
  void (*destroy)(void*) noexcept;
};
```

优点：
- 调用边界显式，函数指针开销低。
- ops表可保持只读静态存储，backend context独立管理。
- 可作为C ABI或跨模块插件边界的候选。

风险：
- context生命周期、destroy顺序、空指针与函数表版本必须逐项检查。
- 手工函数表容易遗漏操作或错误映射noexcept。
- completion捕获context时，可能出现use-after-free。
- 函数表版本演进和错误处理协议需额外治理。
- 对当前同一C++模块内的私有backend替换，抽象层收益有限。

当前不建议作为Slice A1默认方案；若未来确需跨DSO或C ABI边界，再单独立项。

## 4. 策略冻结建议

**建议Slice A1采用 Private abstract interface + PIMPL + 单一SocketCore。**

原因：
1. 当前主要需求是测试时替换backend，而不是跨进程/跨语言ABI。
2. seam位于private实现层，虚表不构成对外ABI承诺。
3. Asio与Fake可以共用完全相同的Core、generation、cleanup transaction和snapshot采集逻辑。
4. 不必把模板策略传播到public header。
5. 比手工function table更容易审查对象所有权、异常和completion路径。

建议对象关系：

```text
Public SocketV2 facade
  └── unique_ptr<Impl>                 [public ABI boundary]
        └── shared_ptr<SocketCore>     [one lifecycle owner]
              ├── unique_ptr<ITransportBackend>
              │     ├── AsioUdpBackend [production]
              │     └── FakeBackend   [test-only]
              ├── CleanupCoordinator
              ├── SnapshotCollector
              └── callback/worker state
```

以上是候选关系图，不授权Core随意shared ownership。SERVO-884/SERVO-879定义的ResidualResourceHandle/Quarantine owner仍须保持唯一、可追踪的资源所有权；shared_ptr仅可用于明确的短期观察或已定义的共享Core引用，不能成为失败后丢失owner的替代机制。最终owner转移必须遵守SERVO-881/882的prepare/commit与generation fencing合同。

### 4.1 构造入口

生产路径：
- public factory只创建生产Asio backend。
- public header不出现ITransportBackend或Fake类型。
- 生产构造不读取测试环境变量或隐藏开关。

测试路径：
- 测试专用factory放入未安装的detail/test_support头文件或内部测试target。
- 通过私有构造/内部builder把Fake backend交给相同SocketCore。
- 测试入口不作为shared library导出符号，不进入plugin XML或ament export。
- 不通过修改legacy factory接口注入Fake。

## 5. Legacy ABI Guard 设计

### 5.1 保护对象

建立基线清单，至少包含：
- legacy Socket及其派生类的public/protected virtual函数集合与顺序；
- SocketFactory及其工厂函数签名、参数、返回类型和异常合同；
- 对外可见类的sizeof/alignof（仅适用于平台/编译器/配置完全匹配的基线）；
- public exported symbol名称、类型、版本与可见性；
- 安装头文件路径、include closure和导出CMake target；
- plugin XML class/type/base_class_type与library path；
- ROS plugin对外注册的类名和依赖库集合。

### 5.2 ABI验证层次

| 检查层 | 方法 | 可发现的问题 | 限制 |
|---|---|---|---|
| Header/API | install consumer编译、API dump | include破坏、签名缺失 | 不足以证明二进制ABI |
| Symbol | nm/readelf或平台对应工具 | 符号新增/删除/可见性变化 | 不完整表达类布局 |
| ABI diff | abi-dumper + abi-compliance-checker或等价工具 | 类型、布局、函数ABI差异 | 需相同编译器/flags/依赖 |
| Layout probe | sizeof/alignof与必要offset probe | 类布局变化 | 只对相同平台构建有效 |
| Plugin metadata | XML/ament/plugin描述差异 | 插件注册名/库路径变化 | 不覆盖运行时加载 |
| Runtime consumer | 独立install-space consumer和plugin load test | 安装消费、动态加载失败 | 不替代ABI diff |

### 5.3 基线与比较规则

- 基线必须从固定上游commit的可复现构建产物生成；若缺少可复现环境/依赖，状态记为 BLOCKED，不可伪造基线。
- 新旧构建使用相同编译器版本、架构、C++标准、visibility、宏定义、依赖版本和构建类型。
- 先比较legacy ABI，再单独评估新增V2符号；不能因新增V2符号而忽略legacy symbol删除或布局变化。
- 对无法获得稳定布局信息的类型，记录为“ABI证据不足”，而非默认兼容。
- ABI工具报告的差异必须逐条分类：intentional addition、legacy break、tool noise、environment mismatch。
- 任何legacy break均阻断合并，除非用户明确批准新的major ABI策略；当前专项没有此授权。

### 5.4 ABI Guard 测试项

- ABI-LEG-01：legacy public header签名快照。
- ABI-LEG-02：legacy vtable/virtual成员变更审查。
- ABI-LEG-03：导出符号清单diff。
- ABI-LEG-04：ABI工具结构/函数比较。
- ABI-LEG-05：关键public类layout probe。
- ABI-LEG-06：install header清单与include closure diff。
- ABI-LEG-07：plugin XML和导出target diff。
- ABI-LEG-08：独立consumer链接旧factory并调用既有API。
- ABI-LEG-09：V2新增符号与legacy符号分组审查。
- ABI-LEG-10：不同平台/编译器配置分别保存基线，不跨平台直接比较。

以上全部NOT_RUN。

## 6. CMake test-only dependency wiring

### 6.1 Target分层建议

候选结构：

```text
staubli_driver_core (existing production target)
  ├── existing public headers
  ├── SocketV2 facade
  ├── SocketCore
  └── AsioUdpBackend

staubli_driver_plugin (existing plugin target)
  └── links production core only

staubli_socket_test_support (new test-only target)
  ├── FakeTransportBackend
  ├── FaultScript
  ├── DeterministicDriver
  └── private test factory

test_socket_v2 (test executable)
  ├── links production core
  ├── links test_support
  └── links gtest
```

重要：若Fake要替换Core内部backend，test-support必须使用私有注入入口，但不能把Fake实现编译进生产core/plugin。可选实现是将backend interface留在private internal header、test-support提供builder实现，并让Core测试构造路径只在测试构建中可见。最终链接图需验证没有双重定义、ODR冲突或生产符号泄漏。

### 6.2 CMake属性合同

建议：
- 生产target的`target_link_libraries`不包含test_support/gtest。
- test_support仅在`BUILD_TESTING`且测试依赖可用时创建。
- fake头文件位于test/private目录，不进入`install(DIRECTORY ...)`。
- fake target不加入`ament_export_targets`、`ament_export_dependencies`或plugin依赖。
- production target的`PUBLIC_HEADER`、`INSTALL_INTERFACE`、导出target保持生产API闭包。
- 使用target级include directories与compile features，避免全局include path泄漏。
- 测试专用宏只作用于test_support/test executable，不通过PUBLIC compile definitions传播到production consumers。
- 测试target与production target分别检查静态/动态链接依赖，避免静态库被意外打包进plugin。
- CMake选项默认行为必须明确；关闭BUILD_TESTING时，不应生成Fake相关目标或安装Fake文件。

### 6.3 目标依赖断言

构建图必须满足：
- plugin -> production core：允许。
- production core -> test_support：禁止。
- production core -> gtest：禁止。
- install/export -> fake headers/symbols：禁止。
- test executable -> production core + test_support + gtest：允许。
- test_support -> private interface/test utilities：允许。
- production public header -> fake type：禁止。

### 6.4 CMake检查实现方向

不在本节点声称已写入CMake；实施时建议：
1. 使用`cmake --graphviz`或File API导出target依赖图。
2. 检查`install_manifest.txt`，确保无Fake头文件/库。
3. 检查`ament_export_targets`和生成的package config，确保无test target。
4. 使用`readelf -d`/平台等价工具检查plugin动态依赖。
5. 使用`nm -D`/平台等价工具检查plugin导出符号无Fake/FaultScript/TestExecutor符号。
6. 在独立干净目录执行install-space consumer build。
7. 在`BUILD_TESTING=OFF`配置中确认测试目标不存在，生产target仍可构建。
8. 在`BUILD_TESTING=ON`配置中确认测试target存在且Fake仅由测试程序引用。

## 7. ODR、生命周期与回调边界

- backend interface的定义只能有一个权威private header；不得由生产和测试各自复制结构定义。
- `TransportOps`或interface版本不能靠不同宏改变类布局；禁止同一类型在不同translation unit出现不同定义。
- Fake的completion必须遵守与Asio backend相同的取消/完成合同。
- backend析构不得与CleanupCoordinator并行关闭同一native资源。
- fake task queue销毁前，必须drain或显式取消所有捕获Core/context的任务。
- test factory不得返回裸context指针或无owner的callback。
- plugin unload前仍须满足SERVO-879定义的callback target、worker、custom deleter/vtable/plugin code依赖解除条件。
- 测试支持库不能在plugin unload后仍执行指向plugin text segment的回调。

## 8. 实施顺序与验收门

| 顺序 | 任务 | 交付 | 准入条件 |
|---|---|---|---|
| A1.1 | 确认private interface位置与PIMPL所有权 | 设计决策记录 | public/install边界明确 |
| A1.2 | 建立Asio backend adapter | 生产默认构造路径 | legacy API不变 |
| A1.3 | 建立test-only builder与Fake backend | test_support target | Fake不进生产依赖 |
| A1.4 | 共用SocketCore与状态机 | production/fake共享Core | 无重复cleanup owner |
| A1.5 | ABI/header/install guard | baseline与diff报告 | legacy差异为零或有批准解释 |
| A1.6 | CMake dependency graph guard | 依赖图与安装清单 | test-only隔离成立 |
| A1.7 | Slice A1验收 | 编译、链接、consumer证据 | A1验收全部通过 |

不得跳过A1.1直接向上游添加实现。不得把FakeTransport先合入生产库再依赖链接器dead-strip隐藏。

## 9. 风险与缓解

| 风险 | 后果 | 缓解 |
|---|---|---|
| private header被安装 | 内部接口变成事实ABI | install manifest与header allowlist |
| test宏传播到production | 不同TU类型定义不一致 | PRIVATE compile definitions、ODR检查 |
| fake静态库进入plugin | 测试代码生产泄漏 | target graph、dynamic deps、symbols检查 |
| 双Core/双cleanup owner | double close或残留资源 | 单一Core与owner invariant |
| 只做nm不做ABI diff | 漏掉类布局/vtable变化 | ABI工具+header+layout+consumer组合 |
| 缺少固定基线产物 | ABI结论不可复现 | BLOCKED并补齐同配置构建 |
| Fake与Asio路径分叉 | 测试通过但生产失败 | 同一Core、同一状态机 |
| plugin卸载后callback执行 | use-after-unload | PluginLease与callback drain gate |

## 10. 验收矩阵（本节点全部NOT_RUN）

| ID | 验收项 | 通过条件 | 状态 |
|---|---|---|---|
| STRAT-01 | strategy selection | private virtual + PIMPL为默认候选，替代方案条件明确 | SPECIFIED |
| STRAT-02 | one-core rule | Fake/Asio共用Core与cleanup状态机 | SPECIFIED |
| ABI-LEG-01 | legacy header snapshot | public签名与基线一致 | NOT_RUN |
| ABI-LEG-02 | legacy vtable review | 无新增/重排legacy virtual | NOT_RUN |
| ABI-LEG-03 | exported symbol diff | legacy符号无删除/意外变化 | NOT_RUN |
| ABI-LEG-04 | ABI structural diff | 同环境ABI工具报告无未批准破坏 | NOT_RUN |
| ABI-LEG-05 | layout probe | 关键类型layout与基线一致 | NOT_RUN |
| ABI-LEG-06 | install header closure | 无private/fake头文件泄漏 | NOT_RUN |
| ABI-LEG-07 | plugin metadata | plugin注册和依赖无非预期变化 | NOT_RUN |
| ABI-LEG-08 | legacy consumer | 独立consumer编译链接并调用旧API | NOT_RUN |
| ABI-LEG-09 | V2 symbol partition | 新V2符号与legacy ABI报告分离 | NOT_RUN |
| CMAKE-ISO-01 | test_support target | 仅BUILD_TESTING时生成 | NOT_RUN |
| CMAKE-ISO-02 | production dependency graph | core/plugin不依赖gtest/fake | NOT_RUN |
| CMAKE-ISO-03 | install manifest | 不安装fake/test-support文件 | NOT_RUN |
| CMAKE-ISO-04 | ament export | 不导出test target/dependency | NOT_RUN |
| CMAKE-ISO-05 | plugin dynamic dependency | plugin不依赖test_support | NOT_RUN |
| CMAKE-ISO-06 | plugin symbol scan | 无Fake/FaultScript/TestExecutor导出符号 | NOT_RUN |
| CMAKE-ISO-07 | BUILD_TESTING=OFF | 测试目标不存在，生产构建正常 | NOT_RUN |
| CMAKE-ISO-08 | BUILD_TESTING=ON | 测试目标链接fake与production core | NOT_RUN |
| CMAKE-ISO-09 | install-space consumer | 独立目录消费安装包成功 | NOT_RUN |
| ODR-01 | one-definition rule | 无宏导致的跨TU类型定义差异 | NOT_RUN |
| LIFE-01 | backend destruction | 单一cleanup owner且无双重close | NOT_RUN |
| LIFE-02 | callback/plugin lifetime | unload gate覆盖回调与backend完成事件 | NOT_RUN |

## 11. 状态与下一节点

- **已完成：** 三种策略比较；建议private abstract interface + PIMPL + 单一SocketCore；定义legacy ABI guard层次、test-only CMake target边界、ODR与plugin callback生命周期约束、A1.1–A1.7实施门。
- **未完成：** 方案尚未在固定上游代码中实现；private header位置、CMake target wiring和实际ABI baseline仍需源码/构建环境验证。
- **未执行：** C++17编译、CMake configure/build、ABI工具、nm/readelf、layout probe、install-space consumer、ament export检查、plugin load/unload、Fake backend、fault injection、TSan/ASan/UBSan、VAL3/CS9、SIL/HIL、FAT/SAT和实机测试。
- **上游边界：** 未修改固定上游；未创建、应用或合并PR；`TODO-EXT-001`仍未授权。
- **历史同步：** 第21章§9.3.281–§9.3.294逐节点同步缺口继续透明保留，不伪造回填。
- **下一节点：** §9.3.305 / SERVO-888：Fixed-commit CMake/source inventory、private seam placement proof 与 reproducible ABI baseline feasibility audit（先核验真实源码与可复现构建条件，再决定是否进入A1实现）。
