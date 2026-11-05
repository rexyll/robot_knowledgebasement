---
tags: [软件, ROS2, 导航, Nav2, 移动机器人]
aliases: [Nav2, navigation2, ROS2导航框架, 导航框架]
创建日期: 2026-11-01
更新日期: 2026-11-05
---

# Nav2 导航框架（ROS 2 Navigation）

> Nav2 是 ROS 2 生态的模块化导航框架。它提供导航任务接口、行为树编排、全局规划、局部控制、Costmap、恢复行为和可选的定位/地图/路网/停靠等组件。Nav2 是一套可扩展的导航软件框架，不是完整的机器人产品：传感器驱动、底盘控制、地图标定、车队调度、设施控制和安全功能仍需要系统集成与验证。

## 1. Nav2 能解决什么，不能替代什么

**适合承载的功能**：
- 已有地图/目标点条件下的点到点导航；
- 多 waypoint 导航与任务行为树编排；
- 全局路径规划与局部路径跟踪；
- Costmap 融合静态地图和传感器障碍；
- 可配置恢复行为、路径平滑、速度平滑；
- 根据版本和插件扩展路网导航、覆盖导航、自动停靠或其他任务。

**并非内置自动完成的功能**：
- 不自动完成传感器驱动、相机/LiDAR 标定、时间同步和可靠定位；
- 不自动给所有机器人提供正确的运动学模型、footprint、速度/加速度/制动参数；
- 不等于 WMS/RMS/车队交通管理，不会自动解决多机器人电梯/窄道预约；
- Costmap、碰撞监控和普通导航控制器不等同于安全额定保护功能；
- 不保证规划路径一定能被真实底盘跟踪，也不保证某个配置在所有 ROS 2 发行版上都相同。

Nav2 应作为单机导航子系统集成进产品系统，向上接受任务/目标，向下连接机器人定位、传感器、底盘控制与安全链路。

## 2. 架构：服务节点、插件和行为树

Nav2 不应简单概括为固定的“四大服务器”。不同 ROS 2 发行版、bringup 配置和产品需求可以启用不同组件。当前官方配置指南列出的常见组件包括：

| 组件 | 职责 | 常见接口/关系 |
|---|---|---|
| BT Navigator | 运行行为树并实现导航任务接口，例如 NavigateToPose、NavigateThroughPoses | 任务层 action server；调用 Planner/Controller/Behavior 等 action |
| Planner Server | 管理全局规划插件，根据起点/终点生成路径 | 提供 ComputePathToPose 等规划 action；输出 nav_msgs/Path |
| Controller Server | 管理局部控制器、progress checker、goal checker，根据路径生成速度命令 | 提供 FollowPath action；发布底盘速度命令 |
| Behavior Server | 托管 Spin、BackUp、Wait、DriveOnHeading 等基础行为插件 | 行为 action server；常被 BT 作为行为/恢复步骤调用 |
| Costmap 2D | 维护全局/局部二维代价地图及 footprint | 由静态地图和传感器观测层组成，供 planner/controller/behavior 等消费 |
| Lifecycle Manager | 按配置顺序管理 lifecycle 节点 configure/activate/deactivate/shutdown | node_names 定义待管理节点及顺序；bond 监控用于发现管理节点/服务器状态异常 |
| Map Server | 加载、发布/保存静态地图 | 通常与 AMCL/全局定位、Static Layer 配合 |
| Waypoint Follower | 依次执行多个 waypoint，并可在 waypoint 间调用任务插件 | 位于单机多点任务层，不等同于跨机器人任务分配 |
| Smoother Server | 管理路径平滑插件，对规划路径进行后处理 | 路径平滑 action；平滑结果仍需碰撞/运动约束检查 |
| Velocity Smoother | 对速度命令进行加速度/死区平滑或插值 | 位于 Controller Server 与机器人控制接口之间；其约束必须与控制器/底盘限制协调 |
| Collision Monitor | 根据传感器/区域模型监控近场碰撞风险，可独立于 costmap 对速度命令做限速/停止干预 | 软件层碰撞监控；不应当作安全认证或安全额定扫描仪/控制器替代品 |
| Route Server | 在 waypoint/lane 路网图上做路线查询或路线相关操作 | 路网级导航能力，图数据和路段语义需要项目配置 |
| Docking Server | 管理停靠任务与 dock 插件 | 需配置充电桩/工位位置、识别与接近策略、硬件交互 |
| 可选 Navigator/扩展 | 例如覆盖导航、FollowPoint 或项目自定义导航任务 | 由 navigator 插件、BT 节点和任务接口扩展 |

上述是按官方组件职责整理的架构视图，并非每个 Nav2 bringup 都会启用全部模块。配置指南会随版本增加/调整组件和插件，部署时必须对照目标发行版文档和源码。

### 2.1 常见单机导航数据流

~~~text
任务层 / 上层 FSM / RMS
        │ NavigateToPose / NavigateThroughPoses
        ▼
BT Navigator（选择任务树、重试、恢复、条件分支）
        │
        ├── Planner Server ── Planner Plugins ── nav_msgs/Path
        │
        ├── Smoother Server ── Path Smoother Plugins
        │
        ├── Controller Server ── Controller Plugins ── cmd_vel
        │                                  │
        │                                  ▼
        │                             Velocity Smoother
        │                                  │
        │                                  ▼
        │                         ros2_control / 厂商底盘驱动
        │
        ├── Behavior Server ── Spin / BackUp / Wait 等动作
        │
        └── Costmap / TF / 定位 / 传感器观测
                     │
                     └── 可选 Collision Monitor / Route / Docking
~~~

数据流中还有状态反馈：定位位姿、里程计、Costmap、路径反馈、控制器进度和故障状态会影响 BT 条件判断与重规划。话题、action、service 的名称和消息类型以目标版本与参数配置为准；不能将“每个组件都是 action server”作为统一接口描述。

## 3. 全局规划器（Planner Plugins）

Planner Server 负责规划请求与插件管理；具体搜索算法由 planner plugin 提供。当前 Nav2 文档包括：

| 插件/算法 | 主要特点 | 使用边界 |
|---|---|---|
| NavFn | 栅格上的 wavefront 扩展，可配置 A* 或 Dijkstra | 常用于圆形差速/全向底盘的二维栅格路线；路径是否可跟踪仍由控制器与运动约束决定 |
| Smac 2D | 代价感知二维 A* | 适用于可近似为二维圆形足迹/平面运动的移动平台 |
| Smac Hybrid-A* | 在含朝向的状态空间搜索，并按运动学模型/运动原语扩展 | 适合阿克曼/汽车式等有转弯半径、不能原地旋转的模型；参数取决于 motion model、离散化和 footprint |
| Smac State Lattice | 按预定义状态/运动原语搜索 | 适合需要配置运动学约束、非圆形足迹或特定原语的底盘；原语覆盖与碰撞检查需要设计 |
| Theta Star Planner | 在栅格搜索中利用视线连接产生 any-angle 路径 | 路径仍需按 footprint/栅格碰撞规则验证；不等于任意连续空间最短路 |

Planner Server 的 action 输出通常是路径位姿序列，而不是完整时间参数化轨迹。若下游控制器对曲率、倒车、方向和速度有要求，需使 planner 的输出模型与 controller 的可跟踪能力保持一致。

不要把某个 planner plugin 设成所有 AMR/叉车的默认选项。差速/全向、阿克曼、窄巷道叉车和具有非圆形 footprint 的机器人应按实际运动模型选择，并对规划成功率、路径代价、最小障碍间隙、耗时和控制器可跟踪性测试。

## 4. 局部控制器（Controller Plugins）

Controller Server 接收路径、当前状态和局部环境信息，再由 controller plugin 生成速度命令。官方插件列表随版本演进，常见选项包括：

| 插件 | 方法 | 官方文档描述的典型适用范围 | 关键注意点 |
|---|---|---|---|
| DWB | Dynamic Window Approach 风格的速度/轨迹采样 + critic 评分 | 差速、全向平台；可配置轨迹生成和 critic | 需要按机器人模型、速度/加速度、critic 与采样参数调试 |
| MPPI | 采样式模型预测控制，按运动模型前向模拟并优化控制序列 | 差速、全向、阿克曼及部分足式模型 | 算力取决于样本量、预测时域、模型和 critic；Nav2 上游实现是 CPU 优化路径，不应写成默认 GPU 加速 |
| Regulated Pure Pursuit（RPP） | Pure Pursuit + 曲率/障碍距离调速、可选碰撞投影 | 更精确地跟踪给定路径的差速/阿克曼/部分足式平台 | 主要是路径跟踪器；不能视为所有动态障碍条件下都能主动大幅绕行的局部重规划器 |
| Rotation Shim | 路径跟踪前/过程中辅助对齐目标方向的控制策略 | 某些差速/全向底盘的起步转向和路径方向对齐 | 不是通用全局规划器，也不替代 footprint 和障碍检测 |
| VP 等其他插件 | 根据版本增加的路径跟踪控制器 | 以目标发行版插件列表为准 | 插件存在、维护状态、适用模型与接口需按版本锁定 |

**TEB 不应写成 Nav2 原生官方 controller plugin。** 上游 rst-tu-dortmund/teb_local_planner 原始包使用 ROS 1/catkin 与 base_local_planner/nav_core 接口；若采用 ROS 2 port/fork，必须独立检查仓库、接口、维护状态和依赖。

控制器选型时要同时考虑全局规划器产生的路径模型、footprint、定位质量、动态障碍、底盘动力学、速度/加速度约束、执行器延迟和真实算力；不能套用“重载 RPP、动态密集 MPPI、倒车 TEB”作为不带条件的选型口诀。

## 5. 行为树（BT）与恢复策略

BT Navigator 通过 BehaviorTree.CPP 执行 XML 行为树，将多个 action、condition、control、decorator 节点组合成导航任务。常见行为包括：

- 计算/更新全局路径（ComputePathToPose / ComputePathThroughPoses）；
- 跟踪路径（FollowPath）；
- 监控目标更新、路径过期、机器人是否 stuck、定位/TF 是否可用；
- 失败后按 BT 节点设计执行清理 Costmap、重规划、Spin、Wait、BackUp 等动作；
- 通过 PipelineSequence、RecoveryNode、RoundRobin 等控制节点决定并行/顺序和重试策略。

BT XML 可以改变已有节点的调用顺序、重试逻辑和条件策略；若要增加新的业务动作、设备 API 或新的 BT node 类型，通常需要实现/注册自定义插件或通过其他受支持接口对接，不是仅改 XML 就能获得任意功能。官方示例 BT 不是产品安全策略；重试次数、后退距离、旋转动作和等待时间需根据场地、机器人状态和风险评估配置。

### 5.1 Behavior Server 与恢复逻辑

Behavior Server 默认插件（例如 Spin、BackUp、DriveOnHeading、Wait）由版本/参数的 behavior_plugins 列表决定。恢复行为的编排通常在 BT 中完成，而不是由一个固定“Recovery Server”自动按清 Costmap → 旋转 → 后退的顺序执行。

任何后退、旋转、清图或再次规划动作，都应检查机器人周边空间、定位质量、实际 footprint 和安全保护状态。清除 Costmap 只是更新软件环境表示，不会清除现实障碍；恢复循环需要超时/次数限制与故障上报。

## 6. Costmap 2D：环境代价与传感器融合

Nav2 Costmap2D 是二维栅格环境代价表达。每个 cell 表示未知、自由、占据或膨胀代价。它供 planner/controller 等模块使用，不是原始传感器数据的完整替代，也不是安全保护装置。

常见 layers：

| Layer | 作用 | 注意点 |
|---|---|---|
| Static Layer | 把静态 OccupancyGrid 地图加载为基础层 | 地图分辨率、未知区域语义、坐标系和版本必须明确 |
| Obstacle Layer | 从 LaserScan/PointCloud2 等观测标记障碍，并按 raytrace 设置清除自由空间 | 要核对 observation source、marking/clearing、range、height、TF 和时间戳 |
| Voxel Layer | 以体素方式维护三维障碍观测并投影进二维 costmap | 体素分辨率、高度、投影和内存需按传感器/场景配置 |
| Range Layer | 使用 Range 消息概率性标记障碍 | 声呐/IR 的视锥、量程、概率模型和噪声特性需核验 |
| Inflation Layer | 对 lethal obstacle 周边施加指数衰减代价，设置内切半径内的致命区域 | 代价扩张不是按速度自动变化的安全制动距离 |

常见 Costmap Filters：

- **Keepout Filter**：将掩码中的区域标记为禁止通行；
- **Speed Filter**：在指定区域施加速度限制；
- **Binary/Zone Parameter 等 Filters**：按掩码/区域执行其他空间规则。

当配置没有覆盖 plugins 参数时，官方文档描述的默认层为 Static、Obstacle、Inflation；Voxel、Range、Denoise 等是可选层。Filters 也需要单独配置，不应和普通 layer 混为一谈。

Costmap 分辨率、inflation_radius、footprint、obstacle range 和 clearing 行为都依目标传感器、机器人尺寸、地图误差和通道几何确定。不要把“inflation_radius=对角半径+5cm”或固定停靠容差写成所有产品的工程默认。

## 7. 定位、TF 与时序

Nav2 本身并不替所有机器人生成定位结果。常见移动机器人会使用已有来源提供：

- map → odom：AMCL、SLAM 定位模式或其他全局定位估计；
- odom → base_link：轮里程计、局部 EKF/VIO 等连续局部估计；
- base_link → sensor frames：静态/动态外参变换。

实际 TF 的发布者必须唯一且符合 REP-105 语义；不能让 AMCL 与全局 EKF 同时发布同一条 map→odom 边。若采用其他坐标系命名或定位结构，需要在配置、BT 节点、Costmap 和控制器中保持一致。

启动前核对 /scan、/odom、/tf、/tf_static、初始位姿、map frame、base frame、时间戳和 use_sim_time。数据延迟、TF 外参错误或定位跳变会传播到 Costmap/规划/控制；不要只通过改 controller frequency 或 inflation 参数来掩盖上游数据问题。

## 8. Lifecycle Manager、Bringup 与 ROS 2 发行版

Lifecycle Manager 对指定的 lifecycle nodes 执行受控 configure/activate/shutdown 流程。管理节点的列表及顺序由 node_names 参数定义，启动按所配置顺序推进，关闭则按相反顺序处理；它还可通过 bond 机制监测节点健康。并不存在所有 Nav2 产品都必须采用同一条固定节点序列。

nav2_bringup 提供可修改的示例启动系统，而非所有产品的唯一 launch 配置。官方 README 描述了可选 component composition；实际是否使用同进程组合、是否 respawn、是否 autostart、仿真时间和 namespace，应按目标资源、部署方式和 ROS 2 发行版设置。

必须固定：
- ROS 2 发行版（如 Humble/Jazzy/Kilted/Lyrical/Rolling 中实际部署的版本）；
- Nav2 包版本/二进制构建或源码 commit；
- RMW/DDS 实现、QoS、通信网络和多机 namespace；
- robot_description、footprint、costmap 插件、TF frame 和传感器 topic；
- planner/controller/BT plugin 参数、地图版本与定位方式。

Rolling 文档用于了解开发版当前功能；它不能直接作为 Humble/Jazzy/Kilted/Lyrical 部署配置，也不能用开发分支默认值代替已发布版本参数。具体迁移应查相应发行版的 migration guide 与 package release。

## 9. 调试与工程验证

### 9.1 常见问题定位

| 现象 | 优先检查 | 不要先做的事 |
|---|---|---|
| Lifecycle 激活失败 | node_names、配置文件、插件加载、bond 状态、节点 lifecycle state | 反复重启而不看状态/日志 |
| Planner 无路径 | 起终点 frame、地图/未知区、footprint、costmap lethal 区、插件 ID/模型 | 盲目减小 inflation_radius |
| Controller 不动/频繁报错 | 路径是否存在、TF/odom、goal checker、progress checker、速度/加速度限值、局部 costmap | 只提高 controller_frequency |
| 机器人贴障碍/擦碰 | footprint 与外参、地图/感知盲区、控制延迟、真实停止距离、costmap marking/clearing | 仅增加膨胀或降低 goal tolerance |
| BT 不断恢复/重规划 | BT XML、错误码、condition/blackboard、定位跳变、传感器数据新鲜度、恢复动作结果 | 盲目增加重试次数 |
| 速度命令抖动 | Controller 输出与 Velocity Smoother 输入/输出、加速度约束、里程计闭环反馈 | 单独调一个控制器参数而不看命令链 |

### 9.2 验收测试建议

1. **组件与接口**：检查 planner/controller/BT/behavior/lifecycle action、service 和 topic 接口，锁定插件、参数与 ROS 发行版。
2. **地图与 TF**：验证 map/odom/base_link、sensor frames、地图版本、初始位姿、时间同步和 TF 唯一发布者。
3. **规划/控制**：直线、曲线、窄道、倒车、目标接近、动态障碍和无路径场景；记录路径可跟踪性、控制耗时、重规划和失败状态。
4. **Costmap**：marking/clearing、遮挡/玻璃/低矮障碍、未知区域、Keepout/Speed filter、地图更新与坐标变换。
5. **故障恢复**：传感器失联、定位丢失、控制器/服务器崩溃、BT 超时、地图更新失败和资源冲突。
6. **安全边界**：测量最坏工况时延与停止距离；验证独立安全扫描仪、急停、制动链和人工接管。Collision Monitor 与 Costmap 属于导航软件功能，不构成安全认证。

## 10. 与自研导航和车队系统的关系

- **Nav2 单机导航 + 自研上层任务系统**：上层 RMS/FSM 分配任务与目标，Nav2 负责单机器人地图导航和局部控制。这种分层便于替换业务策略，但任务 API、状态语义、超时/取消、地图版本和恢复状态必须明确定义。
- **覆盖清扫/专用操作任务**：可用 Nav2 的 planner/controller/BT 插件复用单机能力；清扫覆盖、刷盘/吸水、机械臂操作或精确停靠仍需应用层任务逻辑与设备控制。
- **多机器人交通管理**：Nav2 不负责跨机器人冲突消解和共享电梯/窄道资源预约；可与 Open-RMF 或项目自研 Fleet Manager 对接。见 [[多机协同与调度算法]]。
- **安全架构**：Nav2 输出的速度/路径命令应受到独立安全控制和驱动限幅监督，不能让 BT 恢复策略绕过安全链。

## 11. 上下游关系

**上游**：[[ROS与ROS2]] · [[DDS专题]] · [[SLAM总览]] · [[多传感器融合定位]] · [[09-04-传感器选型与标定]]

**单机算法**：[[路径规划算法]] · [[局部规划与避障]] · [[轨迹优化与运动控制]]

**系统与车队**：[[调度系统RMS]] · [[导航流程]] · [[多机协同与调度算法]] · [[云平台与IoT通信]]

**安全与验收**：[[安全防护器件]] · [[功能安全体系]] · [[性能指标体系]] · [[09-10-系统联调与测试]]

## 12. 本轮定向复核与未关闭事项（2026-11-03）

本轮纠正：

- 将固定“四大服务器”改为按官方配置指南区分 BT Navigator、Planner/Controller/Behavior Server、Costmap、Lifecycle Manager、Map Server、Waypoint Follower、Smoother/Velocity Smoother、Collision Monitor、Docking/Route 等按版本和项目选择的组件。
- 删除“所有服务器都是 Action/Service 服务端”的笼统表述，按组件职责说明 action、service、topic 混合接口。
- 将 NavFn、Smac 2D/Hybrid-A*/State Lattice、Theta Star 作为 Planner plugins 区分；将 DWB/MPPI/RPP/Rotation Shim 等作为 Controller plugins 说明；纠正 TEB 不是 Nav2 原生官方 Controller plugin。
- 删除固定 controller_frequency=20Hz、inflation_radius=对角半径+5cm、xy_goal_tolerance ±5–10cm、满载降速 30% 和 3 轮恢复等产品级通用参数。
- 纠正“BT XML 改变所有行为无需改代码”：已有节点编排可通过 XML 调整；新增自定义 BT node 或设备 API 可能仍需要插件/接口开发。
- 修正 Lifecycle Manager 固定序列示例：实际 node_names 顺序由参数定义，启动与关闭按配置顺序/逆序进行，并通过 bond 检测管理节点状态。
- 更新 Costmap 默认 layer 与可选 layer/filter 的边界；明确 Inflation 不是速度相关制动距离，Collision Monitor/Costmap 不等于安全认证。
- 删除旧版 DWB 固定 20Hz、Recovery 固定清图→旋转→后退顺序；恢复逻辑由 BT 和已加载 Behavior plugins 配置。
- 将 Rolling 文档和目标发行版部署区分；要求固定 ROS 2 distro、Nav2 package version/commit、RMW、插件和参数。

### 本轮核验来源

1. Nav2 Configuration Guide（Jazzy/Rolling）：https://docs.nav2.org/jazzy/configuration_and_development/configuration_guide/；https://docs.nav2.org/rolling/configuration_and_development/configuration_guide/
2. Nav2 Navigation Plugins：https://docs.nav2.org/rolling/configuration_and_development/navigation_plugins/
3. Nav2 Behavior Trees 与 BT XML Nodes：https://docs.nav2.org/rolling/getting_started/nav2_behavior_trees/；https://docs.nav2.org/rolling/configuration_and_development/configuration_guide/core_servers/bt_plugins/
4. Nav2 Lifecycle Manager：https://ros-navigation.github.io/mkdocs.nav2.org/rolling/configuration_and_development/configuration_guide/core_servers/configuring_lifecycle_manager/
5. Nav2 Costmap2D/Environmental Representation：https://docs.nav2.org/rolling/configuration_and_development/configuration_guide/core_servers/costmap_2d/；https://docs.nav2.org/rolling/getting_started/navigation_concepts/environmental_representation/
6. Nav2 Behavior Server、Velocity Smoother、Smoother Server 与 Docking Server：https://docs.nav2.org/rolling/configuration_and_development/configuration_guide/core_servers/configuring_behavior_server/；https://docs.nav2.org/rolling/configuration_and_development/configuration_guide/core_servers/configuring_velocity_smoother/；https://docs.nav2.org/rolling/configuration_and_development/configuration_guide/core_servers/configuring_smoother_server/；https://docs.nav2.org/rolling/configuration_and_development/configuration_guide/core_servers/configuring_docking_server/
7. Nav2 官方仓库 README/LICENSE 与 Planner/Controller/Lifecycle/Bringup 包 README：https://github.com/ros-navigation/navigation2
8. 本地来源台账：[[链接台账]] #363–#378（访问日期：2026-11-03）

**未关闭事项：** 未在目标机器人运行 Nav2 bringup、BT 或插件；未确认本项目最终 ROS 2 发行版、Nav2 包版本/commit、RMW、硬件驱动、地图/TF 配置和插件清单；未执行目标地图上的规划/控制/恢复/多机 namespace/故障注入测试。本文仅完成官方文档与上游接口的定向主张审查，不构成目标平台部署验收、实时性/安全性能验证或产品批准。


## 13. Lyrical 发行版增量核验（2026-11-05）

Nav2 已提供 Humble、Jazzy、Kilted、Lyrical 等发行版文档入口；选型时必须把 ROS 2 发行版与 Nav2 对应分支/二进制包绑定，而不是只写“ROS 2 + Nav2”。截至本次核验，ROS Index 的发行版包索引分别列出 Jazzy 的 navigation2 1.3.14 与 Lyrical 的 navigation2 1.5.3；这是仓库索引的快照，不代表用户目标系统已安装该版本，也不替代 apt 仓库、目标架构和依赖解析结果。

### 13.1 Kilted → Lyrical 的迁移边界

Nav2 官方迁移指南将 Kilted → Lyrical 的变化概括为新增 `nav2_ros_common` 包及 `LifecycleNode` 重构。迁移项目至少应逐项检查：

- **构建依赖**：检查自定义包的 package.xml、CMakeLists.txt、ament 依赖导出与 include 路径；不能因本机已有传递依赖就省略直接依赖声明。
- **Lifecycle 节点**：检查自定义 Nav2 server、插件宿主和派生节点对 LifecycleNode 类型、头文件、命名空间、初始化/状态转换及回调接口的使用；依据 Lyrical 分支 API 编译，不把旧发行版源码机械复制后视为兼容。
- **插件与参数**：检查 pluginlib 导出、插件类名、参数声明/默认值、BT XML 节点注册、action/service/message 接口和启动文件；逐项对照 Lyrical API 文档与 migration guide。
- **部署矩阵**：将 ROS 2 distro、Nav2 包版本、源码 commit、RMW、操作系统/架构、编译器和第三方依赖作为同一配置基线记录；Jazzy 与 Lyrical 不共用未经验证的二进制或工作区。
- **回归验证**：在目标发行版重新执行干净构建、插件加载、Lifecycle configure/activate/deactivate/shutdown、BT XML 加载、规划/控制 action、Costmap 与传感器输入、仿真和故障恢复测试。

官方文档页面可同时展示当前发行版插件/API，但插件列表和配置参数会随分支演进。引用 Rolling 文档时必须明确它是开发分支资料；对 Lyrical 项目应优先引用 Lyrical 文档/API与对应源码分支。

### 13.2 Collision Monitor 的安全语义再确认

Nav2 Collision Monitor 的上游说明明确指出，它在 CPU 软件层处理传感器输入并过滤速度命令，不具备硬实时安全认证。即使配置了 Stop/Slowdown/Approach 区域，也不能据此将其等同于安全激光扫描仪、安全控制器、认证停止功能或整机功能安全验证。产品若将其纳入风险降低措施，必须由整机风险评估确定安全功能是否另有独立、经验证的实现；软件监控可作为附加防护或运行监测，不能替代所需的安全额定链路。

### 13.3 本轮来源与验证边界

本轮核验来源：

1. Nav2 官方 Lyrical 文档入口：https://docs.nav2.org/lyrical/
2. Nav2 官方发行版迁移指南（Kilted → Lyrical）：https://docs.nav2.org/rolling/configuration_and_development/migration_guides/
3. ROS Index navigation2 发行版包索引：https://index.ros.org/p/navigation2/
4. Nav2 Collision Monitor 上游包说明：https://index.ros.org/p/nav2_collision_monitor/

本轮为公开官方文档/包索引支持的发行版迁移与安全语义增量审查，不是对本文所有算法、参数和接口再次全文审查。未在目标工作区进行 Lyrical 构建、源码/API差异编译、插件加载、Lifecycle/BT/规划控制回归、目标硬件实时性测量或实机停止距离测试；未确认用户项目实际采用的发行版、Nav2包版本、RMW、平台架构和自定义插件。资产仍保持未验收状态。
