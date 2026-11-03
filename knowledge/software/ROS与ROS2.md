---
tags: [软件, ROS2, 中间件]
aliases: [ROS, ROS2, Robot Operating System]
创建日期: 2026-11-01
更新日期: 2026-11-03
---

# ROS 与 ROS 2

> 机器人软件事实标准。ROS1 已 EOL（Noetic 2025.5 停止支持），新项目一律 ROS2。本库两个内部项目（[[项目-amr]] · [[项目-清洁机器人]]）均为 ROS2 工程。

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
| 通信中间件 | 自研 TCPROS/UDPROS + Master 节点 | **DDS**（去中心化，无 Master） |
| 发现机制 | roscore 集中注册 | DDS 组播自动发现 |
| 实时性 | 无 | 支持 executor 级实时（配 [[实时系统与嵌入式]]） |
| 进程内通信 | nodelet | Intra-process composition（零拷贝） |
| 语言支持 | C++/Python 为主 | rclcpp/rclpy + Rust/Java 等多绑定 |
| 生命周期 | 手工管理 | Lifecycle Node（配置→激活→去激活 受控状态机） |
| 构建工具 | catkin | **colcon**（→ [[构建与CI工具链]]） |
| 平台 | Linux 为主 | Linux/Windows/macOS/RTOS |

## 通信原语

| 原语 | 模型 | 典型用途 | QoS 要点 |
|---|---|---|---|
| Topic | 发布/订阅（异步流） | 传感器数据、控制指令 | SensorData QoS（BestEffort）vs Reliable |
| Service | 请求/响应（同步一次） | 配置查询、地图保存 | 不适合高频 |
| Action | 目标-反馈-结果（长任务） | 导航 goToPose、OTA 升级 | 可取消、可监控进度 |
| Parameter | 节点参数服务 | 标定参数、开关 | 动态可改 |

**DDS QoS 是 ROS2 第一坑**：不匹配（如发布 Reliable + 订阅 BestEffort）直接收不到数据；传感器话题常用 `best_effort + volatile`，关键指令用 `reliable + transient_local`。

## 生态全家桶（按用途）

| 用途 | 包 |
|---|---|
| 导航 | Nav2 → [[Nav2导航框架]] |
| 机械臂 | MoveIt2、ros2_control（硬件抽象+控制器管理器） |
| SLAM | slam_toolbox（2D）、Cartographer、rtabmap → [[激光SLAM]] |
| 仿真 | Gazebo（gz-sim）、Isaac ROS → [[仿真平台]] |
| 传感器驱动 | velodyne/livox 驱动、OpenNI/RealSense 相机包 |
| 中间件扩展 | zenoh（DDS 替代，弱网）、Fast DDS/Cyclone DDS 实现 |
| 视觉 | image_pipeline（标定）、vision_opencv → [[视觉软件栈]] |

## DDS 实现选择

- **Fast DDS**（eProsima）：Jazzy 的常见默认 RMW；具体默认实现与包版本应以目标发行版安装清单为准
- **Cyclone DDS**（Eclipse）：多机发现更稳，Wi-Fi 组网推荐切它
- **RTI Connext**：商业级，车规/航天
- 调优点：`RMW_IMPLEMENTATION` 环境变量、发现流量（组播风暴）、shared memory（进程内大数据如点云）

## 工程实践要点（内部项目验证过的经验）

1. **多机通信**：不同子网/VPN 下 DDS 组播失效 → zenoh-bridge 或 DDS Discovery Server 模式
2. **点云话题带宽**：3D LiDAR 原始 20 万点/s ≈ 20MB/s → 传前 VoxelGrid 降采样，或 intra-process
3. **包组织**：接口包（msg/srv）独立小包先行，IDL 版本化 → [[项目-amr]] 的 CONTRACT_VERSIONING 实践
4. **测试**：launch_testing 做集成、rosbag2 回放回归 → [[构建与CI工具链]]
5. **容器化部署**：Docker 镜像固化依赖，OTA 只推差分 → [[云端协同与OTA流程]]

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
- **组合节点（composable nodes）**：把多个节点编进一个进程共享内存零拷贝——点云管线的 3-5 倍吞吐提升来源；`ros2 component list` 查看已加载组件。

## 代码实例与开源项目
| 项目 | 语言 | 许可证 | 说明 | 链接 |
|---|---|---|---|---|
| ROS2 Jazzy 安装文档 | — | — | 官方 Debian 路线 | https://docs.ros.org/en/jazzy/Installation/Ubuntu-Install-Debs.html |
| rosbag2 文档 | Python/C++ | Apache-2.0 | 录包/回放/离线分析 | https://docs.ros.org/en/rolling/p/rosbag2/ |
| ros1_bridge | C++ | Apache-2.0 | ROS1/ROS2 图互通（渐进迁移） | https://github.com/ros2/ros1_bridge |

> 历史安装/rosbag2 链接快照见 [[链接台账]] #16/#18/#83；本次发行版维护窗口核验见 #160–#161（2026-11-03）。

## 相关链接
- 上位：[[软件地图]]
- 下游框架：[[Nav2导航框架]] · [[仿真平台]] · [[视觉软件栈]]
- 系统底座：[[实时系统与嵌入式]] · [[构建与CI工具链]]
- 项目实例：[[项目-amr]]（terminal2_ROS2） · [[项目-清洁机器人]]（Terminal_ros2）
- 官方文档：https://docs.ros.org
