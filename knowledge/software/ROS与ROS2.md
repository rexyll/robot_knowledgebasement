---
tags: [软件, ROS2, 中间件]
aliases: [ROS, ROS2, Robot Operating System]
创建日期: 2026-11-01
更新日期: 2026-11-03
---

# ROS 与 ROS 2

> ROS/ROS 2 是机器人领域广泛使用的开源软件框架与通信生态，但不是所有机器人产品都必须采用的行业强制标准。ROS 1 最后一个官方支持发行版 Noetic 已于 **2025-05-31** EOL。新项目通常应优先评估 ROS 2，但仍须依据实时性与安全隔离、算力/存储、目标 OS/BSP、驱动和第三方包、团队维护能力及产品生命周期作出决定；“新项目一律 ROS 2”不是无条件规则。本库两个内部项目（[[项目-amr]] · [[项目-清洁机器人]]）均为 ROS 2 工程。

## ROS 2 发行版与维护窗口（快照 2026-11-03）

ROS 2 发行版是有版本边界的软件集合；LTS 表示长期维护窗口，不代表每个第三方驱动、BSP、仿真器和机器人厂商 SDK 都已支持该版本。

| 发行版 | 发布日期 | 类型 | 官方支持到 | 2026-11-03 状态 |
|---|---|---|---|---|
| Humble Hawksbill | 2022-05-23 | LTS | 2027-05 | 仍受支持，但已进入生命周期后段 |
| Iron Irwini | 2023-05-23 | 非 LTS | 2024-12-04 | 已 EOL |
| Jazzy Jalisco | 2024-05-23 | LTS | 2029-05 | 仍受支持，生态成熟度需按项目核验 |
| Kilted Kaiju | 2025-05-23 | 非 LTS | 2026-12 | 接近 EOL，不宜作为长生命周期新产品默认基线 |
| **Lyrical Luth** | **2026-05-22** | **最新 LTS** | **2031-05** | 新发布 LTS，须核对目标硬件与第三方包支持 |

> **选型建议：** 新项目先评估 Lyrical Luth 是否已获得目标 CPU 架构、操作系统、厂商 BSP、传感器驱动、Nav2/MoveIt 及关键第三方包的完整支持；若供应链或生态尚未就绪，可选仍在维护期内的 Jazzy，并形成明确迁移计划。不要因为“最新 LTS”就跳过集成与回归验证，也不要把旧文档中的 Jazzy 默认选择视为所有产品的强制答案。

产品基线应同时锁定 ROS 发行版、OS 发行版/内核、CPU 架构、RMW/DDS 实现、驱动与关键应用包版本。发行版支持期限不等于厂商 BSP 或第三方包的支持期限。

## 核心概念（ROS1→ROS2 变化）

| 概念 | ROS1 | ROS2 |
|---|---|---|
| 通信中间件 | TCPROS/UDPROS + ROS Master | DDS 是常见 RMW 路线；也有 Zenoh 等替代 RMW；ROS 2 无 ROS Master |
| 发现机制 | ROS Master 注册 | DDS 常用发现机制由中间件完成；组播/静态发现等行为受 RMW、网络拓扑与配置影响 |
| 实时性 | 无统一实时保证 | 提供实时友好设计与工具；executor 或 ROS 2 本身不自动构成硬实时保证，需系统级确定性设计与实测（配 [[实时系统与嵌入式]]） |
| 进程部署/进程内通信 | nodelet | Component 可按部署需要同进程组合；进程内通信需显式配置，零拷贝只在特定类型/所有权/API 条件下成立 |
| 语言支持 | C++/Python 为主 | rclcpp/rclpy + Rust/Java 等多绑定 |
| 生命周期 | 手工管理 | Lifecycle Node（配置→激活→去激活 受控状态机） |
| 构建工具 | catkin | **colcon**（→ [[构建与CI工具链]]） |
| 平台 | 以 Linux 为主 | OS、CPU 架构和 RMW 的支持等级按具体发行版核验；RTOS 需核对具体客户端库、RMW 与集成实现，不能视为通用平台保证 |

## 通信原语

| 原语 | 模型 | 典型用途 | QoS 要点 |
|---|---|---|---|
| Topic | 发布/订阅（异步流） | 传感器数据、控制指令 | SensorData QoS（BestEffort）vs Reliable |
| Service | 请求/响应（同步一次） | 配置查询、地图保存 | 不适合高频 |
| Action | 目标-反馈-结果（长任务） | 导航 goToPose、需要反馈/取消语义的长任务 | 可取消、可监控进度；OTA 只有在任务模型确实需要反馈/取消时才考虑用 Action，升级安全与回滚另行设计 |
| Parameter | 节点参数服务 | 标定参数、开关 | 动态可改 |

**QoS 兼容性先看发布者 OFFERED 与订阅者 REQUESTED，而不是只看两个名字是否相同。** Reliability 的关键组合为：BestEffort 发布者 → Reliable 订阅者不兼容；Reliable 发布者 → BestEffort 订阅者兼容。传感器数据常用 SensorData QoS（BestEffort、较小队列）；默认发布/订阅通常是 Reliable + Volatile。`transient_local` 用于有意保留历史样本供晚加入订阅者读取，不应把它当作所有“关键指令”的默认选项：对瞬时运动命令，必须评估晚加入或重连时重放旧命令的风险。QoS 还应结合 history/depth、deadline、lifespan、liveliness 和系统级 watchdog 一起设计。

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
- 调优点：`RMW_IMPLEMENTATION` 环境变量、发现流量（组播风暴）、shared memory（进程内大数据如点云）

## 工程实践要点（内部项目验证过的经验）

1. **多机通信**：跨子网/VPN 时，组播可能被路由器、防火墙、无线 AP 或 VPN 策略过滤。先检查网卡绑定、VLAN/路由、防火墙端口、组播转发、ROS_DOMAIN_ID 与 DDS discovery 配置，再比较 DDS Discovery Server/静态 peer 或符合目标版本要求的 rmw_zenoh_cpp。任何路线都要实测发现时间、丢包、断线恢复、时延和安全配置。
2. **点云带宽**：不要把“每秒点数”直接换算为固定 MB/s。应根据实际 PointCloud2 字段布局、每点字节数、发布频率、序列化/传输开销和网络封装计算数据率；再决定是否体素降采样、裁剪 ROI、压缩、共享内存或进程内传递，并确认不损害任务所需的检测/定位精度。
3. **包组织**：接口包（msg/srv/action）与实现包分离，IDL/消息字段变更要版本化并测试兼容性 → [[项目-amr]] 的 CONTRACT_VERSIONING 实践。
4. **测试**：用 launch_testing 做集成，用 rosbag2 回放做回归；把记录时的 QoS、时间戳、丢包、存储吞吐和回放速率纳入测试记录 → [[构建与CI工具链]]。
5. **容器化部署与 OTA**：容器镜像固化依赖并记录 digest、权限和设备访问配置；OTA 不应仅等同“差分推送”，还需设备身份、签名验证、原子切换/回滚、断电恢复、版本兼容和审计 → [[云端协同与OTA流程]]。

## 上游板块
- [[09-06-操作系统选型与内核裁剪]] —— ROS 发行版、Ubuntu/RHEL 版本、内核和 BSP 必须作为联合基线评估（软件）
- [[DDS专题]] —— rmw 层下的通信内核（软件）

## 下游板块
- [[Nav2导航框架]] · [[仿真平台]] · [[视觉软件栈]] —— 生态功能包（软件）
- [[09-07-软件栈搭建]] —— 从0搭建的安装与工作区实操（流程）
- [[ROS1与迁移]] —— 存量 ROS1 的迁移路径（软件）
- [[项目-amr]] · [[项目-清洁机器人]] —— 两内部项目均为 Jazzy 工程（项目）

## 细节加深（版本快照 2026-11-03）
- **Jazzy 安装路线**：Jazzy 的官方 Ubuntu Debian 安装文档以 Ubuntu 24.04 为基线；服务器与桌面安装包按用途选择。Lyrical 是新的 LTS，必须以其官方 supported platforms 页面确认 OS/架构，不可沿用 Jazzy 的 Ubuntu 24.04 假设。
- **维护策略**：Humble 将于 2027-05 到期，Jazzy 到 2029-05，Lyrical 到 2031-05；把升级验证安排纳入产品生命周期，而不是等 EOL 才迁移。
- **官方版本证据**：[ROS 2 发行版维护列表](https://github.com/ros2/ros2_documentation/blob/rolling/source/Releases.rst)；[Lyrical Luth 发布说明与支持平台入口](https://github.com/ros2/ros2_documentation/blob/rolling/source/Releases/Release-Lyrical-Luth.rst)。
- **rosbag2 是调试刚需**（官方文档台账 #83）：`ros2 bag record/play` + `ros2 bag info`；机器人系统的"录屏回放"——异常必录，回归必放。
- **ros2 doctor**：内置自检（网络/环境/版本），多机联调第一步先跑它。
- **组件组合（composable nodes）**：多个 C++ component 可装载到同一进程，降低部分进程间通信与部署开销，但会牺牲一部分进程隔离/故障隔离能力。Composition 与 intra-process communication 是相关但不同的概念；需要显式启用 `use_intra_process_comms`。ROS 2 的演示说明在特定 C++ `std::unique_ptr` 发布/订阅路径可实现零拷贝；不能据此推断所有消息、所有类型或所有组合方式均零拷贝。没有通用“3–5 倍吞吐提升”保证，性能收益必须在目标消息尺寸、频率、executor、RMW、CPU/内存和线程配置下基准测试。`ros2 component list` 可查看由组件管理器加载的组件。

## 代码实例与开源项目
| 项目 | 语言 | 许可证 | 说明 | 链接 |
|---|---|---|---|---|
| ROS2 Jazzy 安装文档 | — | — | 官方 Debian 路线 | https://docs.ros.org/en/jazzy/Installation/Ubuntu-Install-Debs.html |
| rosbag2 文档 | Python/C++ | Apache-2.0 | 录包/回放/离线分析 | https://docs.ros.org/en/rolling/p/rosbag2/ |
| ros1_bridge | C++ | Apache-2.0 | ROS1/ROS2 图互通（渐进迁移） | https://github.com/ros2/ros1_bridge |

> 历史安装/rosbag2 链接快照见 [[链接台账]] #16/#18/#83；发行版维护窗口核验见 #160–#161；本轮 QoS、实时性、组件组合、进程内通信、Zenoh RMW、Fast DDS、平台支持和 Noetic EOL 定向复核见 #186–#194（2026-11-03）。

## 相关链接
- 上位：[[软件地图]]
- 下游框架：[[Nav2导航框架]] · [[仿真平台]] · [[视觉软件栈]]
- 系统底座：[[实时系统与嵌入式]] · [[构建与CI工具链]]
- 项目实例：[[项目-amr]]（terminal2_ROS2） · [[项目-清洁机器人]]（Terminal_ros2）
- 官方文档：https://docs.ros.org
