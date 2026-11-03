---
tags: [软件, ROS1, ROS2, 迁移, ros1_bridge]
aliases: [ROS1与迁移, ROS1, ROS迁移, Noetic EOL, ros1_bridge]
创建日期: 2026-11-01
更新日期: 2026-11-03
---

# ROS 1 与 ROS 2 迁移

> ROS 1 的最后一个官方发行版 Noetic Ninjemys 已于 **2025-05-31** 结束官方支持；ROS 1 上游仓库已归档。迁移不只是把 roscpp 改成 rclcpp，还涉及构建系统、消息接口、时间/时钟、参数、执行模型、QoS、发现机制、驱动与第三方软件兼容。对存量系统，可短期隔离/桥接维持；对新功能与长期维护，应制定明确的 ROS 2 目标版本和退出 ROS 1 的计划。

## 1. ROS 1 生命周期与迁移动因

- **ROS Noetic EOL：2025-05-31**。ROS 1 最后官方发行版结束官方维护后，不应再把上游社区包更新、漏洞修复或供应商支持视为持续可用。
- **Ubuntu 20.04 标准支持：2025-05 结束**。Ubuntu Pro/ESM 可为 Ubuntu 基础系统提供延长安全维护，但这不会恢复 ROS Noetic 上游项目的官方支持，也不会自动维护所有 ROS 包、驱动和第三方依赖。
- **Ubuntu 24.04** 不支持 ROS 1，因此不能将 ROS 1 Noetic + Jazzy + ros1_bridge 当成通用同机安装组合。
- 迁移是否完成必须按依赖闭环判断：ROS 包、厂商驱动、相机/LiDAR SDK、内核模块、GPU/CUDA、仿真器、构建工具、消息接口、部署脚本和运维工具均要有目标 ROS 2 版本支持。

Noetic 与 Ubuntu Focal 的时间线接近，但它们是两个独立的生命周期：基础 OS 延长支持不等于 ROS 1 工作负载仍获得安全补丁。对无法立即迁移的设备，应记录风险、隔离边界、网络暴露、补丁策略、备份/恢复方案及退役期限，而不是笼统声称 Docker 化即可“合法/安全”。<Cite refs={["turn603515search3","turn603515search8","turn949004search0","turn949004search6"]}/>

## 2. 核心架构差异

| 维度 | ROS 1 | ROS 2 | 迁移影响 |
|---|---|---|---|
| 图发现 | ROS Master/roscore，节点向 Master 注册名称与地址 | 通常由 DDS RMW 或其他 RMW 实现进行发现；无 ROS Master | 需重新设计域 ID、网络、组播/单播、网卡和多机发现 |
| 通信接口 | roscpp/rospy，TCPROS/UDPROS | rclcpp/rclpy，经 RMW 连接 DDS 或其他实现 | topic/service/action API 不只是协议替换，传输和 QoS 也需验证 |
| QoS | ROS 1 通信接口策略较少，TCPROS/UDPROS 等行为由传输实现决定 | Reliability、Durability、History/Depth、Deadline、Liveliness、Lifespan 等 QoS | 发布/订阅两端必须兼容；传感器消息、地图、命令和状态不能一概使用同一 profile |
| 参数 | Master 参数服务器 | 每节点参数接口和参数事件 | 需明确参数所有者、启动顺序、动态修改回调和持久化 |
| 构建 | catkin / catkin_tools | ament_cmake / ament_python + colcon | 包清单、依赖声明、导出、测试和安装布局均需迁移 |
| C++ 节点 | ros::NodeHandle、roscpp spinner | rclcpp::Node、executor、callback groups | 回调并发、生命周期、时间源与内存行为需重审 |
| Python 节点 | rospy | rclpy | callback group、executor、异步 service/action 和生命周期语义需验证 |
| Launch | roslaunch XML | launch 文件可由 Python、XML 等方式描述 | 参数、事件处理器、进程监控和组合节点的写法变化 |
| 进程内组合 | nodelet | composable nodes / component container | 组件装载与 intra-process 通信是不同机制；需要配置和测试 |
| 导航 | move_base、costmap_2d、ROS 1 planner/controller plugin | Nav2、Behavior Tree、Planner/Controller Server 与插件 | 插件接口和行为树架构变化，通常不是直接替换包名 |
| 控制/硬件 | ros_control | ros2_control | controller、hardware_interface、transmission、lifecycle 和参数均需迁移/重新验证 |
| 实时性 | ROS 1 本身不提供实时保证 | ROS 2 提供更可配置的执行/中间件结构，但不自动成为硬实时 | 需要单独设计 PREEMPT_RT/RTOS、执行器接口和时序验证，见 [[实时系统与嵌入式]] |

ROS 2 不是“天然硬实时”或“所有 OS/RTOS 都同等级支持”。目标发行版、RMW、操作系统、内核、驱动与应用回调共同决定实际时序和可用功能。通信和 QoS 细节见 [[DDS专题]]。

## 3. 迁移前的资产与依赖盘点

建议先建立可复现的 ROS 1 基线，而不是直接开始逐包改代码。

### 3.1 资产清单

- **包和节点**：package.xml、CMakeLists.txt、launch、scripts、动态库、nodelet、pluginlib 插件、消息/服务/action 定义；
- **硬件和驱动**：电机/伺服器、CAN、串口、EtherCAT、IMU、编码器、相机、LiDAR、BMS、急停/安全设备接口；
- **模型和标定**：URDF/Xacro、SRDF、mesh、TF、相机内外参、LiDAR/IMU 外参、底盘运动学、footprint；
- **导航资产**：地图、地图格式、costmap 参数、planner/controller plugin、恢复行为、move_base 参数和自定义导航逻辑；
- **运行环境**：Ubuntu 版本、内核、CUDA/GPU、第三方 SDK、环境变量、网络拓扑、systemd/Supervisor、容器镜像；
- **接口契约**：topic/service/action 名称、消息字段、单位、坐标系、时间戳、QoS/频率要求、错误码和取消语义；
- **运维与安全**：升级/回滚、日志与录包、设备权限、网络暴露、用户权限、急停/保护停止链及现场恢复流程。

### 3.2 迁移优先级

| 资产类别 | 一般策略 | 关键验证 |
|---|---|---|
| 与 ROS 无关的纯算法库 | 优先提取为独立 C++/Python 库复用 | API、数值结果、依赖、线程安全和平台兼容 |
| 消息/服务接口 | 先迁移并建立版本化契约 | 字段语义、单位、序列化、映射规则和上下游兼容 |
| URDF/Xacro/mesh/地图/标定 | 评估复用，避免无目的重画 | TF、坐标系、collision geometry、单位、标定和地图基准 |
| 驱动与硬件接口 | 优先寻找厂商 ROS 2 驱动或支持版本，再考虑自研适配 | 设备状态、故障码、启动/停止、时序、重连、固件和安全状态 |
| 算法节点 | 按依赖和接口拆分迁移 | 消息、时间、参数、QoS、callback concurrency 和测试 |
| 任务/状态机/导航 | 根据 ROS 2 架构重构 | 取消/重试、BT/FSM、恢复行为、地图和任务状态机 |
| 构建/部署/运维 | 最后形成可重复交付 | CI、容器、安装包、日志、监控、升级和回滚 |

不要假设所有 ROS 1 资产可零成本复用：URDF 和部分消息结构可能保留，但插件 ABI、驱动、launch、参数、导航栈和硬件控制接口均可能需要实质改造。

## 4. 代码与工程迁移映射

| ROS 1 | ROS 2 常见替代 | 迁移时检查 |
|---|---|---|
| catkin / catkin_make | ament_cmake / colcon | package.xml format、依赖导出、install/export、测试和 overlay |
| roscpp NodeHandle | rclcpp::Node | node options、参数声明、logging、clock、lifecycle |
| rospy | rclpy | executor、callback group、async API、Python packaging |
| ros::spin / AsyncSpinner | rclcpp executor | callback concurrency、阻塞回调、锁、优先级和线程预算 |
| roslaunch | ROS 2 launch | substitutions、event handlers、参数/YAML、remapping、namespace |
| dynamic_reconfigure | ROS 2 parameters + on-set callbacks | 参数原子性、范围检查、运行中切换状态和回滚 |
| parameter server | per-node parameter services/events | 参数所有者、命名、启动顺序和持久化 |
| nodelet | composable nodes | component registration、container、进程隔离和 intra-process 设置 |
| actionlib | ROS 2 Actions | goal/feedback/result/cancel 状态与取消语义、server/client 生命周期 |
| tf / tf_prefix | tf2 / frame IDs / namespace 策略 | frame 名、静态变换、时间戳、缓存和跨机器人命名 |
| move_base | Nav2 | BT、planner/controller plugins、costmap、恢复和参数需要重新设计 |
| ros_control | ros2_control | hardware interface、controller manager、lifecycle、command/state interfaces |

迁移时需测试 ROS 1/ROS 2 的不同执行模型：ROS 2 的 executor 与 callback groups 会改变并发调度和回调执行顺序；阻塞式 service、锁竞争、共享状态、定时器、参数更新都可能产生与 ROS 1 不同的行为。不能把 NodeHandle API 的语法替换视为迁移完成。

## 5. ros1_bridge：定位、限制与兼容性

### 5.1 它是什么

ros1_bridge 是一个 dual-homed 进程：同一进程同时作为 ROS 1 node 与 ROS 2 node，从一侧订阅消息/服务请求，再向另一侧发布/调用。它适合过渡期的接口互通，不是整个 ROS 1/ROS 2 图的透明协议隧道，也不是任意消息类型的自动转换器。

上游 README 明确：
- 桥接支持的 ROS 1 / ROS 2 message/service 类型在 bridge 编译时确定；
- 预编译二进制仅包含常用接口类型；
- 自定义 message/service 类型需要先分别构建 ROS 1 与 ROS 2 接口包，再在能同时找到两侧接口的环境中构建 bridge；
- dynamic_bridge 会根据两侧实际存在的 publisher/subscriber pair 动态创建桥接，因此仅运行 topic echo 未必能触发桥接；
- --bridge-all-2to1-topics 等选项会改变桥接范围，需理解其流量和安全影响。<Cite refs={["turn603515search3"]}/>

### 5.2 自定义消息映射条件

默认映射依赖包名、消息名、字段名和字段类型匹配。官方映射文档给出的规则大致是：

1. ROS 1 *_msgs 包与 ROS 2 *_msgs 或 *_interfaces 包进行关联；
2. 对应包内同名消息进行匹配；
3. 再匹配消息字段名与字段类型；
4. 一侧含有另一侧没有的字段时，字段映射可能被忽略；若两侧结构无法建立完整映射，则不创建该关联；
5. custom mapping rules 可通过 YAML 显式定义 package/message/field mapping，并通过 package.xml/CMakeLists 安装/导出；
6. service mapping 规则与消息类似，但官方文档指出当前不支持 service 字段的任意自定义重命名映射。

对机器人业务接口，不能只检查“字段同名同类型”：还要核对单位、坐标系、frame_id、时间基准、枚举值、数组语义、默认值、可选字段、错误码和状态机语义。即使字段可序列化，语义不一致也会产生危险的数据误读。<Cite refs={["turn603515search3","turn603515search5"]}/>

### 5.3 自定义接口的构建工作区

典型源码构建会分为三个相互隔离的工作区：

~~~text
ROS 1 workspace（catkin）
  └── 自定义 ROS 1 .msg/.srv 包

ROS 2 workspace（ament/colcon）
  └── 对应 ROS 2 .msg/.srv/.action interface 包

ros1_bridge workspace（colcon）
  └── 同时 source ROS 1 + ROS 2 interface 环境后构建 bridge
~~~

重要细节：
- 先分别构建并 source ROS 1 与 ROS 2 消息/服务接口工作区；
- 再在自己的 bridge workspace 中构建 ros1_bridge，使其编译时发现这些类型；
- build ROS 2 包时，避免把 ROS 1 路径错误混入 ROS 2 的 CMAKE_PREFIX_PATH；
- 修改任意一侧接口或映射规则后，需重新构建 bridge 并做正/反向测试；
- 不要在一个 shell 中不加控制地反复 source 两侧 setup 文件；建立独立脚本/容器/构建环境，并明确各工作区路径与 overlay 次序。

bridge 的预编译包不等于自动支持项目所有自定义接口。项目必须保留 build logs、生成的桥接类型列表和消息转换契约测试。

### 5.4 版本与操作系统兼容性

ros1_bridge 上游 README 当前给出的兼容表包括：

| Ubuntu | ROS 1 | ROS 2（README 所列） | ros1_bridge 上游兼容说明 |
|---|---|---|---|
| 20.04 Focal | Noetic | Foxy（EOL）、Galactic（EOL）、Humble | README 标为 full support；实际需锁定对应 branch/tag 与包版本 |
| 22.04 Jammy | ROS 1 支持部分且官方不支持 | Humble、Iron（EOL） | README 标为需源码构建，兼容性需逐项验证 |
| 24.04 Noble | ROS 1 不可用 | Jazzy、Kilted | README 标为不支持 ros1_bridge |

这张表是 ros1_bridge 上游 README 的当前兼容快照，不应被误读为所有发行版持续受支持的承诺。尤其是 Ubuntu 24.04 不支持 ROS 1，因此不能执行“安装 ros-jazzy-ros1-bridge 并 source Noetic”这种通用示例。上游还明确指出混合不受支持的 OS/ROS 版本可能导致构建失败或依赖缺失。<Cite refs={["turn603515search3"]}/>

### 5.5 运行期常见问题

- **ROS 1 Master**：ROS 1 侧仍需要 roscore/ROS_MASTER_URI；ROS 2 侧仍需其 RMW discovery/network 正常。ros1_bridge 不会消除两侧各自的网络依赖。
- **动态桥接条件**：没有匹配 publisher/subscriber 时，dynamic_bridge 可能不创建 topic bridge；调试工具本身也可能需要显式类型或全量桥接选项。
- **ROS_DOMAIN_ID 与网络**：ROS 2 domain、DDS 组播/单播、网卡和防火墙与 ROS 1 Master 的 URI/TCPROS 网络是两套配置，必须同时检查。
- **时间与时钟**：ROS 1 时间、ROS 2 clock、use_sim_time、bag 回放和系统时钟同步需明确；不可假设桥接自动统一两边时间语义。
- **QoS**：ROS 1 没有 ROS 2 这样可配置的 publisher/subscription QoS 匹配模型；ROS 2 侧 reliability/durability/deadline/liveliness 与 ROS 1 侧传输行为不对称，需按接口逐条测试。
- **Service/Action**：ros1_bridge 对服务有编译时类型支持和映射规则；ROS 1 actionlib 与 ROS 2 Action 在协议、状态和取消语义上不同，不应假定能自动透明桥接。若要跨系统传输长任务，设计专门的任务适配器/状态机。
- **高频控制**：桥接会引入进程、序列化、网络和调度链路；对电机/伺服闭环、急停、保护停止和安全相关状态，不应把 ros1_bridge 当作唯一实时或安全通信路径。

## 6. 迁移策略：分阶段替换，而不是长期双栈无界共存

### 阶段 0：冻结并建立可复现基线
锁定 Noetic 源码、apt 包、容器/虚拟机镜像、驱动、固件、地图/标定、网络配置、rosbag 和关键业务接口；记录版本与许可证。若暂时继续运行 Noetic，隔离网络、限制外部暴露、制定漏洞应对/维护和退役期限。

### 阶段 1：接口与纯算法先行
定义 ROS 1/ROS 2 对照接口、消息语义和版本管理；将不依赖 ROS 的数学/算法库拆成独立模块；搭建 bridge 契约测试。不要在这一阶段让主控命令、驱动器安全状态和保护停止链无条件经过 bridge。

### 阶段 2：硬件驱动与单机闭环
先迁移或替换底盘、编码器、IMU、LiDAR/相机等关键驱动，验证时间戳、TF、丢包、速度/力矩限制、制动和故障状态；再迁移定位、导航、控制与操作节点。对无法迁移的厂商闭源驱动，评估独立适配服务或隔离设备边界。

### 阶段 3：任务系统、监控与运维
迁移状态机、任务编排、日志、诊断、参数管理、bag 录制、升级/回滚与现场工具。ROS 1/ROS 2 共存期间必须明确谁是状态/任务权威，避免两侧同时控制同一执行器或发布冲突 TF。

### 阶段 4：减少桥接并退出 ROS 1
逐个 topic/service/设备切换到 ROS 2 原生实现；每条接口完成正确性、时序、异常恢复和负载测试后再关闭对应 bridge。建立 Noetic 退役清单和最后回滚日期，不把临时 bridge 当成永久系统边界。

## 7. 迁移验收矩阵

| 项目 | 必须验证 |
|---|---|
| 消息/服务 | 类型映射、字段、单位、坐标系、时间戳、枚举和错误码；正/反向数据一致性 |
| Topic 行为 | publisher/subscriber 是否匹配、dynamic bridge 创建条件、QoS、消息频率和队列积压 |
| Service/Action | 请求/响应类型、超时、取消、反馈、结果和重复请求语义 |
| 时钟/TF | ROS time/system time/use_sim_time、frame 名、TF 发布权、bag 回放和仿真 |
| 网络/发现 | ROS_MASTER_URI、ROS_DOMAIN_ID、RMW、组播/单播、防火墙、跨网段和断线重连 |
| 性能 | 端到端时延 P50/P95/P99/max、丢失/重复、CPU/内存、网络带宽、资源竞争 |
| 安全/控制 | 不让 bridge 代替硬件安全链；验证过期命令、失联、执行器超时、保护停止、人工接管和复位 |
| 维护与退出 | 版本冻结、许可证、漏洞监控、升级/回滚、bridge 移除计划和遗留依赖列表 |

测试报告应包含 ROS 1/ROS 2 发行版、Ubuntu/内核、bridge commit、消息接口版本、RMW/DDS、网络拓扑、QoS、数据集、统计口径、持续时长和故障注入步骤。一次正常 demo 不等于迁移验收。

## 8. 许可证与维护边界

- ROS 1 ros1_bridge 上游仓库 LICENSE 为 Apache-2.0，但 ROS 1 节点、驱动、消息包、厂商 SDK 和桥接依赖的许可证需要分别审查。
- ROS Noetic EOL 后的第三方 fork、内部 backport 或私有补丁需要明确维护责任、安全修复来源与审计记录；上游 EOL 不是说软件突然不能运行，而是上游维护/支持责任结束。
- Ubuntu Pro/ESM 对操作系统包的延长维护，不自动覆盖 ROS Noetic、外部 PPA、源码构建包、驱动厂商 SDK 或自研组件。
- 迁移时还要检查旧版 C++/Python 依赖、OpenSSL、Boost、PCL、OpenCV、CUDA、驱动和第三方库的生命周期；不能仅以 ROS 包已编译成功作为供应链风险关闭。

## 9. 上下游关系

**目标态**：[[ROS与ROS2]] · [[DDS专题]] · [[Nav2导航框架]] · [[实时系统与嵌入式]]

**工程迁移**：[[构建与CI工具链]] · [[视觉软件栈]] · [[仿真平台]]

**项目实例**：[[项目-amr]] · [[项目-清洁机器人]]

**安全与运维**：[[功能安全体系]] · [[系统故障诊断与闭环处理]] · [[云平台与IoT通信]]

## 10. 本轮定向复核与未关闭事项（2026-11-03）

本轮纠正：

- 将 Noetic EOL 日期明确为 2025-05-31；区分 ROS 发行版 EOL 与 Ubuntu Focal 标准支持结束，说明 Ubuntu Pro/ESM 不会恢复 ROS Noetic 上游支持。
- 删除“新项目一律 ROS 2”“ROS 1 冻结 Docker 即安全/合法”等绝对判断，改为按供应链、产品生命周期、网络暴露和退役期限评估。
- 纠正 Ubuntu 24.04 安装 ros-jazzy-ros1-bridge 的错误示例：bridge 上游 README 明确 Noble 24.04 不支持 ROS 1/ros1_bridge；Ubuntu 22.04 只有部分/源码构建路径；Ubuntu 20.04 兼容矩阵也必须按精确版本核对。
- 纠正 ros1_bridge “同名同类型就自动桥接所有消息”的说法：bridge 在编译时确定支持类型；预编译二进制仅含常见接口；自定义类型需 ROS 1/ROS 2 两侧接口工作区与单独 bridge workspace。
- 增加 ros1_bridge 自动映射的 package/message/field 规则与 YAML custom mapping；明确 service 自定义字段映射能力限制。
- 补充 dynamic_bridge 只在检测到匹配 publisher/subscriber 后按需创建 topic bridge，以及全量桥接选项和显式 topic type 的排障边界。
- 纠正“source 两边环境并同机就自动全桥”的暗示，增加独立工作区、CMAKE_PREFIX_PATH、ROS Master 与 ROS 2 RMW 网络双侧依赖。
- 删除迁移工作量“每包半天/一两人月”经验数字；改为分阶段迁移和接口/硬件/控制/任务/运维验收矩阵。
- 明确 ROS 1 actionlib 与 ROS 2 Action 不能假设由 ros1_bridge 无损透明互通；控制/安全路径不应把 bridge 当作唯一实时或安全链。

### 本轮核验来源

1. ROS 1 Noetic 官方 EOL/归档说明：https://github.com/ros/ros/blob/noetic-devel/README
2. REP-0003 Noetic 维护窗口：https://reps.openrobotics.org/rep-0003/
3. Ubuntu Release Cycle（Focal 标准支持与 Ubuntu Pro/ESM 区别）：https://ubuntu.com/about/release-cycle
4. ros1_bridge 官方 README（兼容矩阵、双环境构建、dynamic_bridge 行为）：https://github.com/ros2/ros1_bridge
5. ros1_bridge 官方接口映射文档（消息/服务自动匹配和 YAML 规则）：https://github.com/ros2/ros1_bridge/blob/master/doc/index.rst
6. ros1_bridge LICENSE：https://github.com/ros2/ros1_bridge/blob/master/LICENSE
7. 本地来源台账：[[链接台账]] #408–#413（访问日期：2026-11-03）

**未关闭事项：** 未获取本项目实际 ROS 1 workspace、包清单、Noetic/Focal 镜像、厂商驱动和自定义消息；未构建项目自定义 ros1_bridge；未逐 topic/service/action 做消息映射、时间、TF、QoS、网络断连和端到端时延验证；未形成迁移计划的包级工作量/风险基线。本文仅完成公开资料主张定向复核，不构成具体项目迁移完成、运行性能、安全或产品验收。
