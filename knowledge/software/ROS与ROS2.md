---
tags: [软件, ROS2, 中间件]
aliases: [ROS, ROS2, Robot Operating System]
创建日期: 2026-11-01
更新日期: 2026-11-05
---

# ROS 与 ROS 2

> ROS/ROS 2 是机器人领域广泛使用的开源软件框架与通信生态，但不是所有机器人产品都必须采用的行业强制标准。ROS 1 最后一个官方支持发行版 Noetic 已于 **2025-05-31** EOL。新项目通常应优先评估 ROS 2，但仍须依据实时性与安全隔离、算力/存储、目标 OS/BSP、驱动和第三方包、团队维护能力及产品生命周期作出决定；“新项目一律 ROS 2”不是无条件规则。本库两个内部项目（[[项目-amr]] · [[项目-清洁机器人]]）均为 ROS 2 工程。

## ROS 2 发行版与维护窗口（快照 2026-11-05）

ROS 2 发行版是有版本边界的软件集合；LTS 表示长期维护窗口，不代表每个第三方驱动、BSP、仿真器和机器人厂商 SDK 都已支持该版本。

| 发行版 | 发布日期 | 类型 | 官方支持到 | 2026-11-03 状态 |
|---|---|---|---|---|
| Humble Hawksbill | 2022-05-23 | LTS | 2027-05 | 仍受支持，但已进入生命周期后段 |
| Iron Irwini | 2023-05-23 | 非 LTS | 2024-12-04 | 已 EOL |
| Jazzy Jalisco | 2024-05-23 | LTS | 2029-05 | 仍受支持，生态成熟度需按项目核验 |
| Kilted Kaiju | 2025-05-23 | 非 LTS | 2026-12 | 接近 EOL，不宜作为长生命周期新产品默认基线 |
| **Lyrical Luth** | **2026-05-22** | **LTS** | **2031-05** | 当前最新 LTS；按官方平台支持等级核对目标OS/架构 |

> **选型建议：** 新项目优先评估 Lyrical Luth，但必须按官方平台支持等级、OS/CPU架构、RMW、BSP、传感器驱动、Nav2/MoveIt及关键第三方包逐项核验。官方发行版支持不等于厂商 BSP/第三方包支持；Tier 3平台需源码构建，且平台支持等级会限制对应中间件的实际支持等级。若供应链或生态尚未就绪，可选仍受支持的 Jazzy，并形成明确迁移计划。不要因“最新 LTS”跳过集成与回归验证。

产品基线应同时锁定 ROS 发行版、OS 发行版/内核、CPU 架构、RMW/DDS 实现、驱动与关键应用包版本。发行版支持期限不等于厂商 BSP 或第三方包的支持期限。

## 核心概念（ROS1→ROS2 变化）

| 概念 | ROS1 | ROS2 |
|---|---|---|
| 通信中间件 | TCPROS/UDPROS + ROS Master | DDS 是常见 RMW 路线；也有 Zenoh 等替代 RMW；ROS 2 无 ROS Master |
| 发现机制 | ROS Master 注册 | DDS 常用发现机制由中间件完成；组播/静态发现等行为受 RMW、网络拓扑与配置影响 |
| 实时性 | 无统一实时保证 | 提供实时友好设计与工具；executor 或 ROS 2 本身不自动构成硬实时保证，需系统级确定性设计与实测（配 [[实时系统与嵌入式]]） |
| 进程部署/进程内通信 | nodelet | Component 可按部署需要同进程组合；进程内通信需显式配置，零拷贝只在特定类型/所有权/API 条件下成立 |
| 客户端库 | roscpp/rospy 等 | 官方核心客户端库以 rclcpp/rclpy 为主；其他语言客户端的维护主体、发行版支持和API成熟度需逐项核验 |
| 生命周期 | 通常由应用自行管理节点生命周期 | 可选 Lifecycle Node，含 configure/activate/deactivate/cleanup/shutdown/error 等受控转换；普通节点不会自动获得生命周期管理 |
| 构建工具 | catkin（常配合 catkin_tools） | **colcon** 常用于工作区构建/测试编排，包本身仍使用 ament 等构建系统（→ [[构建与CI工具链]]） |
| 平台 | 以 Linux 为主 | OS、CPU 架构和 RMW 的支持等级按具体发行版核验；RTOS 需核对具体客户端库、RMW 与集成实现，不能视为通用平台保证 |

## 通信原语

| 原语 | 模型 | 典型用途 | QoS 要点 |
|---|---|---|---|
| Topic | 发布/订阅（异步流） | 传感器数据、控制指令 | SensorData QoS（BestEffort）vs Reliable |
| Service | 请求/响应 | 短时、可快速完成的请求/响应操作 | API可同步或异步调用；不适合承载长时间任务，不能把客户端超时等同服务端未执行 |
| Action | Goal、Feedback、Result及取消状态机 | 导航 goToPose、需要反馈/取消语义的长任务 | 客户端可请求取消，但取消请求不等于任务已停止；必须检查终态与设备实际状态。OTA升级安全与回滚另行设计 |
| Parameter | 节点参数接口/服务 | 节点配置、标定参数、运行时可调项 | 可在运行时设置，但节点可通过只读描述符、类型/范围约束和回调拒绝修改；不等于全局配置中心或跨节点事务 |

**QoS兼容性必须按全部适用策略检查发布者 OFFERED 与订阅者 REQUESTED。** Reliability 的关键组合为：BestEffort 发布者 → Reliable 订阅者不兼容；Reliable 发布者 → BestEffort 订阅者兼容。Durability 也影响连接：Volatile 发布者不能满足 Transient Local 订阅者；若要实现类似 ROS 1 latched topic 的晚加入读取，发布者和订阅者都需选择 Transient Local。Deadline、Liveliness及Lease Duration也有请求/提供兼容规则；History/Depth影响缓存行为，Lifespan决定过期样本处理。SensorData QoS是预定义配置，不应只概括为BestEffort；应记录目标发行版对应profile的全部策略。默认profile通常为 Reliable + Volatile，但具体实体可覆盖。Reliable表示中间件传输层可靠性，不是业务事务、执行器动作完成或安全保证。瞬时运动命令需评估晚加入/重连后的旧样本问题，并使用命令有效期、序列号、幂等和独立安全链。

## 生态全家桶（按用途）

| 用途 | 包 |
|---|---|
| 导航 | Nav2 → [[Nav2导航框架]] |
| 机械臂 | MoveIt2、ros2_control（硬件抽象+控制器管理器） |
| SLAM | slam_toolbox（2D）、Cartographer、rtabmap → [[激光SLAM]] |
| 仿真 | Gazebo（gz-sim）、Isaac ROS → [[仿真平台]] |
| 传感器驱动 | velodyne/livox 驱动、OpenNI/RealSense 相机包 |
| 中间件扩展 | Fast DDS/Cyclone DDS 等 DDS RMW；rmw_zenoh_cpp 是映射到 Zenoh 的替代 RMW 实现，不是 DDS 实现 |
| 视觉 | image_pipeline（标定）、vision_opencv → [[视觉软件栈]] |

## DDS 实现选择

- **Fast DDS**（eProsima）：官方常见安装中的默认 RMW 为 rmw_fastrtps_cpp；仍应核对目标发行版、软件包清单和运行时 RMW_IMPLEMENTATION。
- **Cyclone DDS**（Eclipse）：常用替代 DDS RMW。不能笼统断言它在多机或 Wi-Fi 环境中必然更稳定；必须在目标网卡、交换机、VLAN、组播策略、负载和版本上做对照测试。
- **RTI Connext**：商业 DDS/RMW 选项；许可证、平台支持、功能/性能、质量等级和供应商支持需按具体项目核验，不以行业标签替代验证。
- **Zenoh / rmw_zenoh_cpp**：可作为替代 RMW 路线评估。当前设计文档描述了 Router 参与发现信息转发的架构；要核对目标版本、Router 部署/故障恢复、网络安全、QoS 语义和互操作测试。
- 调优点：`RMW_IMPLEMENTATION` 环境变量、发现流量与网卡选择；区分 ROS 2 intra-process communication（同一进程内路径）与 DDS/RMW shared-memory transport（同机不同进程间共享内存传输），两者配置、适用条件和性能收益不同。点云大数据需按实际RMW、消息类型、内存所有权和部署拓扑基准测试。

## 工程实践要点（项目案例与待复现经验）

1. **多机通信**：跨子网/VPN 时，组播可能被路由器、防火墙、无线 AP 或 VPN 策略过滤。先检查网卡绑定、VLAN/路由、防火墙端口、组播转发、ROS_DOMAIN_ID 与 DDS discovery 配置，再比较 DDS Discovery Server/静态 peer 或符合目标版本要求的 rmw_zenoh_cpp。任何路线都要实测发现时间、丢包、断线恢复、时延和安全配置。
2. **点云带宽**：不要把“每秒点数”直接换算为固定 MB/s。应根据实际 PointCloud2 字段布局、每点字节数、发布频率、序列化/传输开销和网络封装计算数据率；再决定是否体素降采样、裁剪 ROI、压缩、共享内存或进程内传递，并确认不损害任务所需的检测/定位精度。
3. **包组织**：接口包（msg/srv/action）与实现包分离，IDL/消息字段变更要版本化并测试兼容性 → [[项目-amr]] 的 CONTRACT_VERSIONING 实践。
4. **测试**：用 launch_testing 做集成，用 rosbag2 回放做回归；把记录时的 QoS、时间戳、丢包、存储吞吐和回放速率纳入测试记录 → [[构建与CI工具链]]。
5. **容器化部署与 OTA**：容器镜像固化依赖并记录 digest、权限和设备访问配置；OTA 不应仅等同“差分推送”，还需设备身份、签名验证、原子切换/回滚、断电恢复、版本兼容和审计 → [[云端协同与OTA流程]]。

> 本节所述跨子网、点云、接口包、launch_testing/rosbag2与容器化建议属于工程检查线索。当前文档未附目标项目的可复现测试报告、固定commit、拓扑、原始bag、性能测量或CI记录；不得将标题或历史项目记录理解为本轮重新验证了内部项目。

## 上游板块
- [[09-06-操作系统选型与内核裁剪]] —— ROS 发行版、Ubuntu/RHEL 版本、内核和 BSP 必须作为联合基线评估（软件）
- [[DDS专题]] —— rmw 层下的通信内核（软件）

## 下游板块
- [[Nav2导航框架]] · [[仿真平台]] · [[视觉软件栈]] —— 生态功能包（软件）
- [[09-07-软件栈搭建]] —— 从0搭建的安装与工作区实操（流程）
- [[ROS1与迁移]] —— 存量 ROS1 的迁移路径（软件）
- [[项目-amr]] · [[项目-清洁机器人]] —— 两内部项目均为 Jazzy 工程（项目）

## 细节加深（版本快照 2026-11-05）
- **Lyrical 平台矩阵**：官方支持表将 Ubuntu Resolute 26.04 的 amd64/arm64列为Tier 1；Ubuntu Noble 24.04列为Tier 3，Tier 3需源码构建。C++最低要求为C++20；默认RMW为rmw_fastrtps_cpp。Lyrical所列rmw_zenoh_cpp等中间件支持等级仍受操作系统/架构平台等级约束。Jazzy的Ubuntu 24.04二进制安装路线不能直接套用到Lyrical。
- **维护策略**：Humble 将于 2027-05 到期，Jazzy 到 2029-05，Lyrical 到 2031-05；把升级验证安排纳入产品生命周期，而不是等 EOL 才迁移。
- **官方版本证据**：[ROS 2发行版维护列表](https://github.com/ros2/ros2_documentation/blob/rolling/source/Releases.rst)；[Lyrical Luth发布说明](https://github.com/ros2/ros2_documentation/blob/rolling/source/Releases/Release-Lyrical-Luth.rst)；[Lyrical支持平台矩阵](https://github.com/ros2/ros2_documentation/blob/rolling/source/Releases/lyrical/supported-platforms.rst)。
- **rosbag2**（官方文档台账 #83）：可用于 `ros2 bag record/play` 与 `ros2 bag info`，适合故障取证和回归；是否常态录制、录哪些topic及保留周期需依据隐私、存储、性能和产品运维策略决定。
- **ros2 doctor**：可辅助收集ROS环境和配置诊断信息；它不是完整网络连通性、QoS匹配、DDS发现或端到端链路验收工具。
- **组件组合（composable nodes）**：多个组件可装载到同一进程，减少部分进程间开销，但会共享进程故障域和资源权限。Composition不自动启用intra-process communication；需按目标发行版和组件容器配置显式启用。特定消息类型、所有权与API路径可实现避免部分数据拷贝的优化，不能推断所有消息或所有RMW均为零拷贝。性能收益需按目标消息尺寸、频率、executor、RMW、CPU/内存和线程配置基准测试。`ros2 component list`可查看组件管理器加载的组件。

## 代码实例与开源项目
| 项目 | 语言 | 许可证 | 说明 | 链接 |
|---|---|---|---|---|
| ROS2 Jazzy 安装文档 | — | — | 官方 Debian 路线 | https://docs.ros.org/en/jazzy/Installation/Ubuntu-Install-Debs.html |
| rosbag2 文档 | Python/C++ | Apache-2.0 | 录包/回放/离线分析 | https://docs.ros.org/en/rolling/p/rosbag2/ |
| ros1_bridge | C++ | Apache-2.0 | ROS1/ROS2 图互通（渐进迁移） | https://github.com/ros2/ros1_bridge |

> 历史安装/rosbag2链接快照见 [[链接台账]] #16/#18/#83；发行版维护窗口核验见 #160–#161；此前QoS、实时性、组件组合、进程内通信、Zenoh RMW、Fast DDS、平台支持和Noetic EOL定向复核见 #186–#194（2026-11-03）。本轮2026-11-05补充核验Lyrical发布/平台矩阵、QoS兼容性和rmw_zenoh默认路由器架构；新增URL列于下方，本轮未更新链接台账。

## 相关链接
- 上位：[[软件地图]]
- 下游框架：[[Nav2导航框架]] · [[仿真平台]] · [[视觉软件栈]]
- 系统底座：[[实时系统与嵌入式]] · [[构建与CI工具链]]
- 项目实例：[[项目-amr]]（terminal2_ROS2） · [[项目-清洁机器人]]（Terminal_ros2）
- 官方文档：https://docs.ros.org


## 本轮全文主张边界审查与未关闭事项（2026-11-05）

本轮对本文全文进行P1静态主张边界审查，并按ROS 2 Lyrical当前官方文档更新发行版、平台和中间件支持信息。

### 修订重点

- 更新ROS 2发行版快照：Lyrical Luth于2026-05-22发布，是当前LTS，支持至2031-05；Kilted预计2026-12 EOL，Humble至2027-05，Jazzy至2029-05。发行版维护窗口不等于全部生态包和厂商BSP支持窗口。
- 按Lyrical官方支持平台矩阵补充Ubuntu Resolute 26.04与Ubuntu Noble 24.04的不同支持等级、Tier 3源码构建要求、C++20最低要求及默认RMW；明确平台支持等级会约束对应RMW实际支持等级。
- 修正ROS 2语言客户端描述：核心官方客户端库以rclcpp/rclpy为主，其他语言绑定应核验维护主体、发行版支持和API成熟度，避免将社区客户端统称为等价官方支持。
- 修正Lifecycle Node描述，说明它是可选受控生命周期节点，不是所有ROS 2节点自动具备的生命周期；补充完整转换边界。
- 修正Service为请求/响应模型，区分同步/异步API和客户端超时与服务端副作用；补充Action取消请求不等于动作已停止，必须检查终态和设备状态。
- 修正参数动态修改表述，增加只读描述符、范围/类型约束和节点回调拒绝修改的情况。
- 补全QoS兼容性：Reliability、Durability、Deadline、Liveliness/Lease Duration均需检查请求/提供关系；解释Transient Local两端配置、History/Depth/Lifespan及默认profile的边界。
- 区分ROS 2 intra-process communication与DDS/RMW shared-memory transport；Composition不自动启用进程内通信，组合部署也会改变故障隔离边界。
- 将“内部项目验证过的经验”“rosbag2刚需”“ros2 doctor第一步”等绝对化表达改为项目经验线索、按策略使用的工具和诊断辅助，不把工具存在当成测试证据。
- 补充rmw_zenoh_cpp默认需要Zenoh router参与发现转发、默认关闭UDP multicast scouting的架构边界；必须按目标发行版分支、路由器部署和故障恢复验证。

### 本轮核验来源（URL已在正文列示，未登记链接台账）

1. ROS 2发行版维护列表：https://github.com/ros2/ros2_documentation/blob/rolling/source/Releases.rst
2. ROS 2 Lyrical发布说明：https://github.com/ros2/ros2_documentation/blob/rolling/source/Releases/Release-Lyrical-Luth.rst
3. ROS 2 Lyrical支持平台矩阵：https://github.com/ros2/ros2_documentation/blob/rolling/source/Releases/lyrical/supported-platforms.rst
4. ROS 2 QoS策略与兼容性：https://docs.ros.org/en/rolling/Concepts/Intermediate/About-Quality-of-Service-Settings.html
5. rmw_zenoh设计与路由器发现机制：https://github.com/ros2/rmw_zenoh/blob/rolling/docs/design.md

**未关闭事项：** 未对目标机器人执行ROS发行版安装、编译、驱动兼容、RMW互操作、QoS负向匹配、实时性/执行器时延、intra-process/shared-memory性能、Zenoh路由器失效恢复、多机网络、SROS2安全或实机测试。未审查内部项目源码与CI原始记录，不能确认“内部项目验证”历史陈述；本轮已将其降级为待复现经验线索。本文完成的是公开官方资料支持的静态全文审查，不构成目标产品集成验收、实时性保证、安全认证或量产放行。
