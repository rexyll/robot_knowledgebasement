---
tags: [软件, ROS2, DDS, RTPS, RMW, 中间件, QoS]
aliases: [DDS专题, DDS, ROS2中间件, RMW, RTPS, Quality of Service]
创建日期: 2026-11-01
更新日期: 2026-11-03
---

# DDS / RTPS / RMW 专题（ROS 2 Middleware）

> ROS 2 通信栈不是简单的“ROS 2 = 某一个 DDS”。需要区分 **ROS 2 RMW 抽象层、具体中间件实现、DDS/RTPS 协议、网络传输和 ROS 2 QoS 配置**。不同 RMW 可在同一 ROS 2 应用接口下提供通信实现，但发现、传输、共享内存、配置文件、默认 QoS、性能和许可证均存在实现与版本差异。

## 1. 概念层次：不要把 DDS、RTPS、RMW 混成一个词

| 层次 | 是什么 | 典型例子 | 主要职责 |
|---|---|---|---|
| ROS 2 应用 API | 节点、topic、service、action、参数等上层接口 | rclcpp、rclpy | 定义应用编程接口和 ROS 图语义 |
| RMW（ROS Middleware） | ROS 2 的中间件抽象接口 | rmw_fastrtps_cpp、rmw_cyclonedds_cpp、rmw_connextdds、rmw_zenoh_cpp | 将 ROS 2 的发布订阅、服务等接口映射到具体通信实现 |
| DDS 实现 | 实现 OMG DDS 规范的中间件 | eProsima Fast DDS、Eclipse Cyclone DDS、RTI Connext、GurumDDS | DomainParticipant、Publisher/Subscriber、DataWriter/Reader、QoS、发现等 |
| DDSI-RTPS | DDS Interoperability Wire Protocol | RTPS over UDP 等 | DDS 实现之间用于互操作的数据线协议 |
| 传输与网络 | 实际承载数据包的链路和机制 | UDP/IP、TCP、共享内存、厂商传输扩展 | 连接、发送、缓冲、重传和网络接口选择 |

ROS 2 通过 RMW 屏蔽了应用层与某个具体 middleware implementation 的直接耦合。DDS 是 ROS 2 默认采用的通信模型/标准体系，但 RMW 并非只能对接 DDS；例如 rmw_zenoh_cpp 是基于 Zenoh 的非 DDS RMW。

“DDS 无 Broker、全靠组播发现、发现后永远 P2P 直连”过于绝对。DDS/RTPS 常见部署使用参与者发现和端点发现，并可利用组播、单播或静态 peer 配置；Fast DDS Discovery Server 可集中协调发现信息。实际用户数据是否组播、单播、共享内存或使用其他传输路径，取决于中间件、QoS、配置、拓扑和接收者数量。

## 2. ROS 2 的 RMW 实现与发行版边界

ROS 2 文档列出的 DDS 实现包括 eProsima Fast DDS、Eclipse Cyclone DDS、RTI Connext DDS 和 GurumDDS；当前 ROS 2 文档还将 Eclipse Zenoh 列为新发行版可用的 RMW 选项。具体可用 RMW、Tier 级别、平台/架构支持与默认实现，必须按目标 ROS 2 发行版的 REP-2000 和 release package 核验。

| 实现 | 类型 | 主要特点 | 使用前核验 |
|---|---|---|---|
| Fast DDS（eProsima） | DDS | ROS 2 常见默认实现；支持 UDP、共享内存/数据共享相关能力、XML 配置与 Discovery Server | Fast DDS 与 rmw_fastrtps 的配套版本、publication mode、共享内存/数据共享配置、发现拓扑 |
| Cyclone DDS（Eclipse） | DDS | ROS 2 常用实现；提供接口选择、组播/单播发现与数据通信配置 | Cyclone DDS 和 rmw_cyclonedds 的版本组合、网络接口选择、multicast/peer 配置与接收缓冲 |
| RTI Connext DDS | DDS | RTI 提供商业 DDS 实现与支持 | 许可、产品/版本、ROS RMW 包、目标平台和厂商支持合同 |
| GurumDDS | DDS | ROS 2 文档列出的其他 DDS 实现 | 目标发行版支持状态、软件包、平台和 QoS/传输能力 |
| Zenoh / rmw_zenoh_cpp | 非 DDS RMW | 以 Zenoh session/router/gossip 等方式提供 ROS 2 通信；在指定 ROS 2 发行版上提供 RMW 包 | 发行版分支、router/session 拓扑、发现配置、ROS graph 行为、功能/工具兼容和安全配置 |

### 2.1 切换 RMW：它不会自动替你完成互操作验证

指定 RMW 的常见方式：

~~~bash
# 查看当前环境及 ROS 信息
ros2 doctor --report

# 为当前 shell 选择一个已经安装的 RMW
export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp

# Fast DDS RMW
export RMW_IMPLEMENTATION=rmw_fastrtps_cpp

# Zenoh RMW（需先安装目标发行版对应的包）
export RMW_IMPLEMENTATION=rmw_zenoh_cpp
~~~

注意：
- 目标 RMW 必须安装、构建并正确 source；环境变量只选择实现，不会安装软件包。
- 同一通信图中的进程通常需要使用兼容的 RMW/DDS 实现和配置；是否能跨供应商互通，必须按具体 DDSI-RTPS 版本、类型支持、QoS、Security、传输和厂商扩展实际验证。
- 修改 RMW 后要考虑 ROS 2 CLI daemon 已经启动并缓存了旧环境；切换时停止并重启 daemon，避免 CLI 图信息仍来自旧 RMW。
- 多 RMW 同时安装不等于多个实现能在任何 ROS 发行版、平台和通信场景中无缝混用。官方多 RMW 使用指南和对应发行版包表是部署依据。

### 2.2 Zenoh RMW 与 Zenoh bridge 不是同一个东西

- rmw_zenoh_cpp：直接作为 ROS 2 RMW 实现，ROS 2 节点通过 RMW API 使用 Zenoh。
- zenoh-bridge-ros2dds：桥接 ROS 2 DDS/RTPS 图与 Zenoh 网络的桥接程序；它并不等同于把 ROS 2 进程切换到 rmw_zenoh_cpp。
- Zenoh router：在 rmw_zenoh 的默认部署方式中可承载 session 的发现/路由服务；具体拓扑、autoconnect/gossip、router 故障恢复与跨网段转发由配置决定。

因此不能把“弱网直接上 Zenoh 桥”写成通用选型规则。需要先决定是保留 DDS RMW 并通过 bridge/路由互联，还是整个 ROS 2 通信图使用 Zenoh RMW；再验证 ROS 2 工具、发现、QoS、服务/action、网络隔离和故障恢复。

## 3. ROS 2 QoS：Request vs Offered

ROS 2 publisher 和 subscription 可以独立设置 QoS。建立连接采用 Request vs Offered 模型：subscription 请求最低可接受的服务质量，publisher 提供其能够提供的服务质量；请求不能比提供的条件更严格。必须同时满足所有影响匹配的兼容策略。QoS 不兼容时，即使 topic 名称和消息类型相同，也不会传递消息。

### 3.1 八类 QoS 策略

| 策略 | 主要取值/意义 | 主要影响 |
|---|---|---|
| History | KEEP_LAST / KEEP_ALL | 缓存策略；KEEP_LAST 配合 depth 限制保留的样本数量 |
| Depth | KEEP_LAST 的队列深度 | 决定样本缓存数量；不是“传输可靠性等级” |
| Reliability | RELIABLE / BEST_EFFORT | 是否要求中间件按可靠传输语义处理样本 |
| Durability | VOLATILE / TRANSIENT_LOCAL | late-joining subscriber 是否可从 publisher 的历史缓存收到样本 |
| Deadline | 期望连续样本之间的最大时间间隔 | 可检测发布/接收是否超过约定更新周期 |
| Lifespan | 单条样本的有效期 | 过期消息不再被交付；依赖时间戳语义/时钟等实现条件 |
| Liveliness | AUTOMATIC / MANUAL_BY_TOPIC 等 | publisher 如何声明其仍在活动 |
| Lease Duration | liveliness 的有效期窗口 | 多久未收到 liveliness 断言后，subscriber 可判定其失活 |

History/Depth 与可靠性是不同维度。KEEP_ALL 不等于永不丢消息：仍可能受资源限制、队列满、应用处理慢、网络丢包、进程崩溃或中间件实现限制影响。

### 3.2 关键兼容矩阵

**Reliability**

| Publisher 提供 | Subscription 请求 | 兼容 |
|---|---|---|
| BEST_EFFORT | BEST_EFFORT | 是 |
| BEST_EFFORT | RELIABLE | 否 |
| RELIABLE | BEST_EFFORT | 是 |
| RELIABLE | RELIABLE | 是 |

**Durability**

| Publisher 提供 | Subscription 请求 | 兼容 | 数据行为 |
|---|---|---|---|
| VOLATILE | VOLATILE | 是 | 新消息 |
| VOLATILE | TRANSIENT_LOCAL | 否 | 不建立通信 |
| TRANSIENT_LOCAL | VOLATILE | 是 | 只接收新消息 |
| TRANSIENT_LOCAL | TRANSIENT_LOCAL | 是 | 可接收 publisher 历史缓存中的新/旧消息 |

“地图 latched/迟加入者可获取历史数据”通常需要 publisher 与 subscriber 两端都设置 TRANSIENT_LOCAL；仅 publisher 设置 transient local、subscriber 仍是 volatile，连接可能兼容，但不会收到历史样本。

**Deadline**

publisher 的 offered deadline 必须小于或等于 subscriber requested deadline（更强的周期承诺才能满足较宽松或相同的请求）。例如 publisher 提供 20ms，subscriber 请求 50ms，匹配兼容；publisher 只承诺 100ms，而 subscriber 请求 50ms，则不兼容。

**Liveliness 与 Lease Duration**

- AUTOMATIC publisher 不能满足 MANUAL_BY_TOPIC subscriber 的更严格要求。
- MANUAL_BY_TOPIC publisher 可满足 AUTOMATIC subscriber。
- publisher 提供的 liveliness lease duration 应小于或等于 subscriber 请求的 lease duration，才能满足其活性检测要求。

某一策略不兼容即可导致整个 endpoint pair 无法匹配。ROS 2 提供 incompatible QoS、deadline missed、liveliness changed/lost 等事件供应用监控；出现“topic 看得到但没有消息”时应检查两端实际 QoS 和事件，不要先认定是网络故障。

### 3.3 常见默认 QoS Profile

ROS 2 RMW 的常用默认 profile（具体目标发行版/实现仍应核对）包括：

| Profile | History / Depth | Reliability | Durability | 典型场景 |
|---|---|---|---|---|
| Default | KEEP_LAST / 10 | RELIABLE | VOLATILE | 普通 topic 默认 profile |
| Sensor Data | KEEP_LAST / 5 | BEST_EFFORT | VOLATILE | 高频传感器观测，优先新鲜数据 |
| Services Default | KEEP_LAST / 10 | RELIABLE | VOLATILE | service 请求/响应 |
| Parameters | KEEP_LAST / 1000 | RELIABLE | VOLATILE | 参数服务相关通信 |
| System Default | 由 RMW 实现决定 | SYSTEM_DEFAULT | SYSTEM_DEFAULT | 需要依赖中间件默认值时 |

例如 ROS 2 RMW 的 qos_profiles.h 当前源码定义 Sensor Data 为 KEEP_LAST(5)/BEST_EFFORT/VOLATILE，Default 为 KEEP_LAST(10)/RELIABLE/VOLATILE。这个源码快照不能代替目标发行版实际安装版本的检查。

**排障第一步**：检查两端真实 QoS，而不是只看你在代码里写的 profile。

~~~bash
ros2 topic info /scan --verbose
ros2 topic info /map --verbose
ros2 doctor --report
~~~

## 4. 发现机制与多机网络

DDSI-RTPS 常见发现过程包括：
- **SPDP（Simple Participant Discovery Protocol）**：发现 DomainParticipant；
- **SEDP（Simple Endpoint Discovery Protocol）**：交换 DataWriter/DataReader 等 endpoint 信息；
- 之后按匹配的 endpoint、locator、QoS 和传输配置建立数据通信路径。

Cyclone DDS 官方文档描述默认 SPDP multicast 地址和 discovery peers 配置；如果禁用 multicast，可配置 unicast peer，但可能比正常 multicast discovery 慢，并对不响应的 peer/reader 带来额外风险。

### 4.1 常见发现失败原因

| 现象 | 可能原因 | 检查方向 |
|---|---|---|
| 同网段节点互相不可见 | multicast 被交换机/AP/防火墙抑制，网卡选错，ROS_DOMAIN_ID 不同 | 检查网卡、域 ID、组播、VLAN、IGMP snooping、防火墙和 RMW 配置 |
| Wi-Fi 下发现不稳定 | AP 对 multicast 降速/过滤，网络漫游、节能或丢包 | 对比有线/无线，检查 AP multicast/broadcast 策略；不要仅凭 Wi-Fi 就认定必须切 Zenoh |
| 跨 VLAN/VPN/NAT 发现失败 | multicast 默认不会自动路由通过边界网络，advertised locator 可能不可达 | 设计静态 peer、Discovery Server、路由/桥接或应用层代理，并验证端点实际数据路径 |
| 多网卡/容器错误寻址 | DDS 选择了管理网、Docker bridge、VPN/loopback 等接口 | 显式选择网卡/地址并抓包确认 advertised locator |
| 节点发现成功但无消息 | QoS 不兼容、TypeSupport/类型不一致、endpoint locator/防火墙问题 | 查看实际 QoS、incompatible QoS events、RTPS 抓包与日志 |

### 4.2 Fast DDS Discovery Server

Fast DDS Discovery Server 可让 DomainParticipant 以 client/server 模式向 Discovery Server 注册和发现对等 participant/endpoints，减少某些规模化拓扑中参与者之间的发现流量。它改变的是 discovery 架构，不应简单理解为一个 ROS topic 数据 Broker；应用数据路径、server redundancy、client 配置、服务器故障和启动顺序都需按 Fast DDS 版本/部署架构验证。

### 4.3 Cyclone DDS 网络接口与发现配置

Cyclone DDS 可通过 XML 配置接口选择、multicast 使用范围、peer 列表、SPDP 周期和传输方式。常用环境入口为 CYCLONEDDS_URI，指向配置文件。官方文档特别指出：
- 可选择指定网卡名或地址；
- 可按接口配置 multicast；
- 可只允许 SPDP multicast，而对 endpoint/user data 使用 unicast；
- peer 列表能用于受限网络，但静态 peer 并不等于更高可靠性；
- 多网卡、IPv4/IPv6 和 advertised address 需要一致配置。

例子（具体 XML schema/字段依目标 Cyclone DDS 版本）：

~~~bash
export CYCLONEDDS_URI=file://$PWD/cyclonedds.xml
~~~

不要在不了解网络拓扑时直接关闭所有组播、硬编码对端 IP 或复制网上 XML。先用配置日志和抓包确认 DDS 实际选用的 interface、SPDP/SEDP locator 和 data transport。

## 5. 数据路径、共享内存与进程内通信

### 5.1 传输不等于 QoS

Fast DDS、Cyclone DDS 等实现可能支持 UDP、TCP、共享内存或其他传输配置；但这些能力是否被编译、启用以及何时被选中，取决于 RMW/中间件版本、数据类型、部署拓扑和 XML 配置。

需要区分三件事：
1. **DDS Shared Memory Transport**：中间件在同一主机进程间或参与者间使用共享内存传输；
2. **DDS Data Sharing Delivery**：在满足类型/内存/共享条件时使用数据共享机制减少序列化/复制；
3. **ROS 2 intra-process communication**：rclcpp 进程内 publisher/subscription 传递路径，通常与组件组合、unique_ptr/shared_ptr ownership 等有关。

它们不是同一种功能，也不能因为启用了 component composition 就推断所有跨进程 DDS 传输都自动零拷贝。当前 rmw_fastrtps README 记录其默认设置中 Data Sharing 为 OFF；需要根据 Fast DDS 版本及配置单独启用并验证。

### 5.2 大消息、点云和图像

大消息排障应分层验证：
- 消息大小和频率；
- 序列化/反序列化耗时；
- publication mode（synchronous/asynchronous）；
- history memory policy 与队列积压；
- UDP socket buffer、MTU/fragmentation、网卡 offload；
- 接收端 executor、回调耗时和消费速率；
- 多播/单播选择、SHM transport 与数据共享能力；
- CPU/内存、页错误、线程优先级和网络负载。

rmw_fastrtps 允许通过配置/环境变量调整 Fast DDS publication mode 和 XML QoS 来源；其同步/异步模式会改变 write 调用线程与后台发送线程之间的工作分配。异步不保证端到端延迟更低，同步也不保证总吞吐更高，需按负载和消息分布实测。

不要将 net.core.rmem_max=8388608 等 sysctl 命令写成所有 Linux 机器人必须执行的默认值。缓冲区大小、丢包和延迟应由抓包、socket 统计、中间件日志与端到端测试确定。

## 6. Zenoh：RMW 与 DDS Bridge 的两条集成路线

| 方案 | 节点应用使用 | 网络角色 | 需要验证的重点 |
|---|---|---|---|
| rmw_zenoh_cpp | ROS 2 节点通过 Zenoh RMW API | Zenoh session/router/gossip 等 | 目标 ROS 发行版支持、router/session 启动、服务/action/graph 行为、配置和故障恢复 |
| zenoh-bridge-ros2dds | ROS 2 节点仍使用 DDS RMW | 桥接 DDS/ROS 2 与 Zenoh 网络 | bridge 版本、DDS discovery、ROS namespace/topic 映射、消息类型、跨网段 QoS 和数据路由 |

rmw_zenoh 的官方 README 提供发行版分支安装方法，并指出默认配置下节点会通过 Zenoh router 获得发现信息；启动 router/节点的具体步骤和是否需要手动 router 取决于目标版本。rmw_zenoh_cpp 是 RMW 实现，而 bridge 是另一个程序，不能混作同一个部署选项。

Zenoh 并不是“只要弱网就一定优于 DDS”。选择前应定义网络拓扑、数据类型/大小、pub-sub 与服务需求、权限/安全、断连重连、桥接边界和工具链，再做同一场景下对照试验。

## 7. 安全、域隔离与通信边界

ROS 2/DDS 的安全能力必须按信任边界、参与者身份、权限策略和实际部署模式配置。不能把 ROS_DOMAIN_ID、VLAN、VPN、DDS-Security 或 SROS2 中任何单项能力当作完整的机器人网络安全方案。

### 7.1 DDS-Security 与 SROS2 的能力边界

ROS 2 的 DDS-Security 集成（通常通过 SROS2 工具链和 RCL 配置暴露）基于 DDS-Security 插件模型。ROS 2 设计资料说明其集成使用以下核心能力：

| 能力 | 机制/材料 | 主要保护目标 | 仍需处理的问题 |
|---|---|---|---|
| 身份认证 | 每个 DDS participant/security context 的证书和私钥；证书链由受信任 Identity CA 验证 | 确认参与者身份，降低未授权参与者冒充风险 | CA保护、签发/轮换/吊销、设备离线、私钥泄露和主机入侵 |
| 访问控制 | Governance 文件定义域级安全策略；Permissions 文件约束身份可执行的 DDS 操作 | 限制 participant 对 domain、topic 等资源的读写权限 | 策略最小化、节点/进程边界、namespace/remap、service/action展开后的实际端点 |
| 加密与完整性 | DDS Cryptographic 插件处理加密、签名/哈希等；设计资料描述内建 AES-GCM 类机制 | 保护受策略覆盖的 DDS 通信机密性和消息真实性/完整性 | 算法/实现配置、密钥管理、性能开销、未经过该 DDS 安全路径的接口 |

ROS 2 设计文档指出，DDS-Security 规范还定义 Logging 与 Data Tagging 插件，但 ROS 2 集成资料所述实现使用身份认证、访问控制和加密三类核心插件；不能据此宣称 ROS 2 自动提供完整安全审计日志或数据标签能力。审计日志、主机审计、命令业务记录和安全事件响应仍需另行设计。

### 7.2 安全默认值与 fail-closed 启动

ROS 2 的 DDS-Security 集成资料明确指出：安全功能默认未启用；在启用安全后，如果参与者缺少可用的 enclave 安全文件，RCL 的 permissive 策略可尝试以未启用安全的方式启动；strict 策略则应拒绝启动。相关配置入口包括：

- `ROS_SECURITY_ENABLE`：显式启用 ROS 2 security 功能；
- `ROS_SECURITY_KEYSTORE`：指定安全 keystore 根目录；
- `ROS_SECURITY_STRATEGY=Enforce`：要求严格执行安全配置，安全材料缺失时不应静默降级；
- enclave：为参与者提供身份、权限和治理材料的安全上下文路径。

以上是 ROS 2 设计资料中描述的环境变量和策略语义；具体目标发行版、RCL/RMW、DDS 实现及启动封装必须以该版本官方文档和实测为准。产品启动脚本应显式设置安全开关与策略，启动后验证安全状态；不能仅凭 keystore 文件存在或 launch 命令未报错，就认定加密/授权已生效。

### 7.3 Enclave、进程隔离与最小权限

- ROS 2 安全资料将 security context 与进程内的 middleware context 关联。若多个节点被组合进同一进程，它们可能共享同一安全上下文和凭据边界；需要不同身份或不同权限的组件应评估拆分进程/enclave，而不是只按 node 名称设计权限。
- 每个参与者应只获得完成职责所需的 topic/service/action 权限；特别审查运动命令、轨迹、驱动使能、参数服务、诊断、地图、传感器和远程管理接口。
- 访问策略应覆盖实际 ROS 图端点。namespace、remapping、composition、参数服务和 action 所展开的隐藏 topic/service 端点，均需在目标发行版生成的策略中核验。
- Identity CA 与 Permissions CA 可分离；私钥不应随源码仓库、容器镜像或通用部署包明文分发。需要定义密钥注入、权限文件签名、轮换、吊销、备份和设备报废流程。
- 节点权限文件不能代替操作系统进程隔离。对不同信任级别的节点，还需评估用户/组、容器或 sandbox、文件系统权限、Linux capabilities、调试接口和主机 root 权限。
- 对不支持 DDS-Security 的 RMW、Zenoh RMW 或 bridge 路径，应按各自安全机制单独配置和测试；DDS-Security 权限文件不会自动保护 Zenoh router、bridge 的另一侧或其他网络协议。

### 7.4 威胁模型：安全机制不能覆盖的风险

ROS 2 官方威胁模型列出未授权发布/订阅、消息篡改、窃听、参与者枚举、凭据窃取、节点被攻陷、通信泛洪和远程链路攻击等风险。SROS2/DDS-Security 可以降低部分未授权访问、窃听和篡改风险，但不是所有攻击的完整缓解措施。

| 威胁/失效 | DDS-Security/SROS2 的作用 | 仍需的系统级控制 |
|---|---|---|
| 未授权节点发布控制消息或订阅敏感数据 | 身份认证与 Permissions 策略可限制参与者权限 | 负向授权测试、网络分区、主机加固、控制命令语义校验 |
| 链路窃听/消息篡改 | 对策略覆盖的 DDS 流量提供加密与真实性/完整性保护 | 其他协议/串口/桥接路径单独保护；密钥安全存储 |
| 合法凭据被窃取或合法节点被攻陷 | 认证本身无法判断已获授权节点是否恶意 | 进程隔离、密钥保护/撤销、运行时监控、最小权限和恢复预案 |
| DoS、组播风暴、允许节点滥发 | 访问控制可限制未授权参与者，但不能消除网络/CPU/队列耗尽 | 网络限流、资源配额、速率限制、异常检测、故障隔离和安全降级 |
| 主机 root/容器逃逸 | DDS-Security 不构成主机可信执行环境 | Secure Boot、OS加固、权限分离、补丁与主机完整性保护 |
| 通过 ROS bridge、Zenoh、WebSocket、MQTT 或诊断接口绕行 | 仅覆盖被配置并实际经过 DDS-Security 的通信边界 | 逐跳认证授权、网关白名单、网络分区、审计和端到端命令校验 |
| 恶意或错误的已授权节点发送语义合法但危险的命令 | 传输层认证/加密不判断业务意图或物理安全 | 独立安全控制、命令限幅/状态机、授权审批和现场风险控制 |

ROS_DOMAIN_ID 用于区分 DDS domain 和常规发现范围，不提供身份认证、加密、topic 授权或抗攻击能力。VLAN、子网、防火墙和 VPN 是网络分区/链路保护手段，也不能替代 participant 身份与应用级权限。反过来，DDS-Security 也不能替代网络分区、DoS 防护和主机安全。

### 7.5 机器人安全职责边界

- DDS QoS 的 RELIABLE、Deadline、Liveliness 或 Security 的认证/加密都不等于确定性实时保证，也不构成功能安全认证。
- 安全停止、急停、保护停止、STO、制动器控制和安全扫描仪保护链，不应只依赖普通 ROS topic、DDS domain 或 SROS2 权限策略。
- DDS-Security 加密、签名和访问控制会引入 CPU、内存、握手/发现和数据路径开销；必须在目标硬件、负载和网络下测量，不得沿用未启用安全时的时延/吞吐结果。
- 网络中断、证书过期、权限文件缺失或认证失败时，设备应按产品风险分析进入预定义的通信降级/安全状态；不能为了“保持通信”而自动关闭安全或退回 permissive 模式。
- 控制命令还应在应用层验证目标设备、命令 ID、时效、状态前置条件、限幅、幂等和审计；DDS participant 身份不等于操作者授权或业务事务完成。

### 7.6 安全配置验收清单

目标产品至少应保留以下验证证据：

1. 安全关闭/开启状态核对；未设置密钥、无效证书、错误 CA、权限文件缺失时的启动行为；确认生产配置 fail-closed。
2. 未授权 participant 加入、未授权 topic 发布/订阅、service/action 请求、参数访问和 remapping 后访问的负向测试。
3. 有效身份、过期/吊销身份、错误签名、权限策略版本变化和密钥轮换/恢复测试。
4. 不同 enclave/进程之间的隔离测试；验证同进程组件是否共享权限边界。
5. bridge/router、Zenoh、MQTT、WebSocket、SSH、串口和诊断接口的逐跳安全审查，确认无绕行路径。
6. 组播/流量泛洪、合法节点滥发、CPU/内存/队列耗尽和网络分区测试。
7. 启用安全前后的 CPU、内存、发现时间、端到端延迟、吞吐、丢样和恢复时间对比。
8. 证书/权限文件分发、存储、备份、撤销、轮换和事件响应演练；日志中不得泄露私钥或敏感载荷。

这些检查是产品验证计划，不表示本知识库已经执行上述测试。

## 8. 性能基准与互操作性验收

比较 RMW/DDS 前必须锁定：
- ROS 2 distro、RMW 包版本/commit、DDS 厂商版本和配置文件；
- OS、kernel、RMW、网卡、CPU/NUMA、容器/虚拟化和网络交换设备；
- 数据类型、序列化类型支持、payload size、频率、发布者/订阅者数量；
- QoS profile、可靠性、历史深度、deadline/liveliness；
- 单机/跨机/跨 VLAN/Wi-Fi/有线/多网卡/多播受限等拓扑；
- 测量时间戳位置、系统时钟同步、预热期、持续时间、CPU/内存和网络背景负载。

建议至少测量：
- participant/endpoint discovery 时间；
- endpoint match 成功率与 QoS incompatibility 事件；
- 发布到接收端到端延迟 P50/P95/P99/max；
- 吞吐、丢样/重复、重传、队列积压和 deadline miss；
- CPU/内存/线程数量、网络带宽、socket drops；
- 网络断开/恢复、router/discovery server 故障和节点重启后的收敛时间；
- 同一 RMW 和跨 DDS vendor 的实际互操作性。

单次 ros2 topic hz、单机 ping 或厂商 benchmark 不能证明目标车队端到端实时性。ROS 2 应用层的 executor 排队和回调耗时也应纳入测量，不要将 DDS 底层性能等同于机器人命令响应性能。

## 9. 常用诊断命令

~~~bash
# 确认 ROS 2 环境及 RMW
echo $ROS_DISTRO
echo $RMW_IMPLEMENTATION
ros2 doctor --report

# 查看 topic 双端 endpoint/QoS
ros2 topic info /scan --verbose

# 检查 multicast 功能（需两台主机在同一可达网络测试）
ros2 multicast receive
ros2 multicast send

# 更换 RMW 前停止 ROS 2 CLI daemon，避免 daemon 保留旧环境
ros2 daemon stop

# Cyclone DDS 配置入口
export CYCLONEDDS_URI=file://$PWD/cyclonedds.xml

# Fast DDS Discovery Server 的具体变量和配置按所用版本文档设置
~~~

同时可使用 tcpdump/Wireshark 的 RTPS 过滤器查看 SPDP/SEDP、用户数据 locator、组播/单播和碎片；使用对应实现的日志/统计工具分析 QoS、发现和传输行为。

## 10. 软件、版本与许可证

| 组件 | 公开许可证/边界 | 备注 |
|---|---|---|
| Fast DDS | 仓库 LICENSE 为 Apache-2.0 | 相关工具、第三方依赖和 rmw_fastrtps 单独锁版本 |
| rmw_fastrtps_cpp | package.xml 当前声明 Apache-2.0 | 不应将 RMW 包许可与底层 Fast DDS 依赖许可混作一项 |
| Cyclone DDS | 仓库 LICENSE 声明 EPL-2.0 或 Eclipse Distribution License 1.0 | 按具体发行文件及再分发方式审查 |
| rmw_cyclonedds_cpp | package.xml 当前声明 Apache-2.0 | 与底层 Cyclone DDS 的双许可证声明需分别记录 |
| RTI Connext | 商业/厂商许可 | 需审查开发、运行、部署节点数、维护和支持条款 |
| GurumDDS | 厂商许可 | 以目标产品/版本合同为准 |
| rmw_zenoh_cpp | package.xml 声明 Apache-2.0，并列 BSD 子文件 | Zenoh 核心有 Apache-2.0/EPL-2.0 文件，需结合依赖版本审查 |
| zenoh-bridge-ros2dds | 单独仓库/版本/许可证 | 不得用 rmw_zenoh 的许可证直接覆盖 bridge 或全部 Zenoh 依赖 |

许可证结论应基于目标 tag/commit、package.xml、根 LICENSE、第三方依赖、动态/静态链接方式和最终分发包。不能因 ROS 2 上层 API 开源或 RMW 包 Apache-2.0，就推断整个 DDS/Zenoh middleware 栈均采用同一种许可证。

## 11. 上下游关系

**上游网络/系统**：[[ROS与ROS2]] · [[实时系统与嵌入式]] · [[云平台与IoT通信]] · [[09-09-网络通讯设计]]

**下游功能**：[[Nav2导航框架]] · [[多机协同与调度算法]] · [[构建与CI工具链]] · [[系统故障诊断与闭环处理]]

## 12. 定向复核记录与未关闭事项（2026-11-03、2026-11-05）

本轮纠正：

- 将 DDS、DDSI-RTPS、ROS 2 RMW 和实际传输层拆开；明确 ROS 2 当前支持多个 DDS RMW，也支持 Zenoh 等非 DDS RMW，不能将所有 ROS 2 通信概括为“DDS”。
- 删除“全靠组播发现、发现后一定 P2P 直连、无 Broker/中心组件”等绝对表述；增加 SPDP/SEDP、静态 peer、Fast DDS Discovery Server 与 Zenoh router 的职责边界。
- 更新 RMW 厂商/发行版边界：Fast DDS、Cyclone DDS、Connext、GurumDDS 等按 REP-2000/目标发行版核验；Zenoh RMW 在新发行版有官方包支持，不能把 Zenoh 仅写作 bridge。
- 补齐 Request vs Offered QoS 兼容性矩阵，纠正 Reliable/Best Effort、Transient Local/Volatile、Deadline、Liveliness/Lease 的方向性；指出 History/Depth 不等于可靠性。
- 按 RMW 源码核验 common QoS profiles：Default KEEP_LAST(10)/RELIABLE/VOLATILE；Sensor Data KEEP_LAST(5)/BEST_EFFORT/VOLATILE；参数相关 profile 单独说明。
- 删除“Wi-Fi/VPN/跨网段直接上 Zenoh 桥”、Cyclone 一定更稳、Fast DDS 固定 discovery mode 等未经目标网络验证的选型口号。
- 区分 Fast DDS SHM transport、DDS Data Sharing Delivery 和 rclcpp intra-process communication；指出 rmw_fastrtps 当前 README 中 Data Sharing 默认 OFF。
- 删除固定 rmem_max=8388608 作为通用配置，改为依据 socket drops、队列、RTPS 抓包与端到端延迟测量调优。
- 分开记录 Fast DDS、Cyclone DDS、RMW wrapper、rmw_zenoh 和 Zenoh 核心许可；不把上层 RMW 包许可证外推到全部依赖。


### 2026-11-05 安全边界补充复核

- 依据 ROS 2 DDS-Security 集成资料，补充身份认证、访问控制、加密插件的职责与限制；区分 Identity CA、Permissions CA、enclave 与实际进程安全上下文。
- 明确 ROS 2 安全默认未启用，以及 permissive/strict（Enforce）启动策略差异；要求生产部署显式启用安全并验证缺少安全材料时 fail-closed，不能静默退回明文通信。
- 依据 ROS 2 官方威胁模型补充凭据窃取、节点被攻陷、DoS/流量泛洪、主机 root、桥接绕行和恶意授权节点等风险；指出 DDS-Security 不自动解决这些问题。
- 明确 ROS_DOMAIN_ID 仅划分 DDS domain，不提供身份认证/加密/访问控制；DDS-Security 不保护未经过其安全路径的 Zenoh、bridge、MQTT、WebSocket、串口或诊断接口。
- 补充同进程组合节点的安全上下文共享风险、最小权限策略、密钥生命周期、负向授权测试、跨网关逐跳保护和安全开销基准。
- 本次为公开资料和文档主张边界审查；未执行本项目 keystore 生成、RMW/DDS 安全启动、权限策略负向测试、密钥轮换、网络攻击、DoS、性能基准或目标机器人安全验收。

本轮核对了 ROS 2 官方 DDS-Security 集成、Access Control Policies 与 Robotic Systems Threat Model 设计资料；来源台账新增记录未写入（平台安全检查阻止），不得将其记为已登记。全文技术验收仍未完成。

### 本轮核验来源

1. ROS 2 QoS Compatibility / Request vs Offered：https://docs.ros.org/en/rolling/Concepts/Intermediate/About-Quality-of-Service-Settings.html
2. ROS 2 DDS implementations / different middleware vendors：https://docs.ros.org/en/rolling/Installation/RMW-Implementations.html；https://docs.ros.org/en/rolling/Concepts/Intermediate/About-Different-Middleware-Vendors.html
3. ROS 2 multiple RMW implementations：https://docs.ros.org/en/rolling/How-To-Guides/Working-with-multiple-RMW-implementations.html
4. ROS 2 QoS design（Deadline/Liveliness/Lifespan）：https://design.ros2.org/articles/qos_deadline_liveliness_lifespan.html
5. RMW common QoS profiles source：https://github.com/ros2/rmw/blob/rolling/rmw/include/rmw/qos_profiles.h
6. rmw_fastrtps README 与配置说明：https://github.com/ros2/rmw_fastrtps
7. Fast DDS Discovery Server 文档：https://fast-dds.docs.eprosima.com/en/latest/fastdds/discovery/discovery_server.html
8. Cyclone DDS 配置 / multicast / network interfaces / discovery：https://cyclonedds.io/docs/cyclonedds/latest/config/config_file_reference.html；https://cyclonedds.io/docs/cyclonedds/latest/config/multicasting.html；https://cyclonedds.io/docs/cyclonedds/latest/config/network_interfaces.html；https://cyclonedds.io/docs/cyclonedds/latest/config/discovery-config.html
9. Cyclone DDS RMW README：https://github.com/ros2/rmw_cyclonedds
10. rmw_zenoh README/package.xml/LICENSE：https://github.com/ros2/rmw_zenoh
11. Fast DDS LICENSE：https://github.com/eProsima/Fast-DDS/blob/master/LICENSE
12. Cyclone DDS LICENSE：https://github.com/eclipse-cyclonedds/cyclonedds/blob/master/LICENSE
13. Zenoh LICENSE：https://github.com/eclipse-zenoh/zenoh/blob/main/LICENSE
14. 本地来源台账：[[链接台账]] #391–#407（访问日期：2026-11-03）

**未关闭事项：** 未在本项目目标 ROS 2 发行版/硬件/网络拓扑测试 Fast DDS、Cyclone DDS 或 Zenoh RMW；未验证目标 topic/action/service 的实际 QoS、Discovery Server/router 故障恢复、跨厂商 wire interoperability、共享内存/数据共享、网络分区与安全访问策略；未完成目标应用端到端时延/丢包/资源占用基准。本文仅完成公开资料支持的技术主张定向复核，不构成项目通信栈部署验收、实时性/安全验证或软件许可法律意见。
