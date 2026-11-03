---
tags: [算法, SLAM, 激光SLAM, LIO]
aliases: [激光SLAM, LiDAR SLAM, LIO]
创建日期: 2026-11-01
更新日期: 2026-11-03
---

# 激光 SLAM 与 LiDAR-Inertial Odometry（LIO）

> 激光 SLAM 使用 LiDAR 扫描与运动信息估计轨迹、构建地图；LIO（LiDAR-Inertial Odometry）进一步融合 IMU。算法的输入要求、地图形式、回环能力、传感器支持和 ROS 兼容性差异很大，不能按“2D/3D”或论文排名直接选型。

## 1. 先区分几个任务

- **LiDAR odometry**：估计相邻扫描或局部时间窗口间的相对运动，重点是连续轨迹；不一定维护可长期复用的全局地图。
- **LIO**：将 LiDAR 与 IMU 紧耦合或松耦合，用 IMU 运动信息辅助预测、去畸变或状态估计。具体耦合方式按实现定义。
- **LiDAR SLAM**：除里程计外，通常还要管理地图、回环/全局约束及长期漂移；不同项目包含的模块并不相同。
- **已知地图定位**：在预先建立的地图中估计位姿。它不等同于建图模式或纯里程计模式。
- **2D 栅格建图与 3D 点云/体素建图**：输出地图形式和下游接口不同。3D LIO 输出点云地图，不会自动变成 Nav2 可直接使用的 2D OccupancyGrid；投影、过滤和地图维护需单独设计。

## 2. 2D 激光 SLAM 的代表实现

| 系统 | 核心思路/能力 | 维护与部署边界 | 使用前检查 |
|---|---|---|---|
| GMapping | Rao-Blackwellized Particle Filter（RBPF）路线的经典 2D 激光 SLAM | 常见于 ROS 1 历史项目；是否有适用包/持续维护需按目标发行版确认 | 激光与里程计模型、地图范围、粒子参数、运行平台 |
| Cartographer | 2D/3D SLAM；子图、扫描匹配、约束搜索和位姿图优化 | 上游 README 声明不再积极维护；ROS 发行版中的 fork 仅有限维护，不能只看“能安装”就认为仍有完整维护 | 区分 upstream 与 ROS fork，锁定分支/commit、发行版、补丁和构建环境 |
| slam_toolbox | ROS 2 生态常用的 2D pose-graph SLAM；支持地图序列化、继续建图、lifelong mapping 和基于 pose graph 的 localization mode | 官方仓库提供 ROS 2 分支；具体发行版支持、包版本和插件需逐项确认 | mode、序列化格式、优化插件、地图更新策略、定位 API 与部署版本 |

2D 扫描匹配可以使用相关性匹配、ICP/NDT 或其他优化方法。具体算法会受分辨率、初值、搜索窗口、环境几何、动态物体和计算预算影响；不能将某个方法描述成所有场景的固定“首选”。

## 3. 3D LiDAR 与 LIO 代表实现

| 系统 | 公开资料所示的核心特征 | 重要限制/边界 |
|---|---|---|
| LOAM | 经典特征式 LiDAR odometry and mapping，将不同频率的里程计/建图任务分开处理 | 研究与历史实现为理解特征提取、扫描匹配和运动估计的参考；实际传感器/驱动和软件环境需按代码版本检查 |
| LeGO-LOAM | 面向地面车辆的轻量化、地面优化 LiDAR odometry；上游示例以水平安装的 Velodyne VLP-16 为主，并假设扫描中存在地面 | 不是任意 LiDAR 即插即用；点云投影、ring/线束信息、地面分割和传感器安装必须适配 |
| LIO-SAM | 因子图平滑与建图；使用 IMU 预积分去畸变/提供初值，并可整合 LiDAR 里程计、GPS 和回环因子 | 上游原始实现是 ROS 1/catkin，仓库另有 ROS 2 分支；README 对原始配置说明 9 轴 IMU 假设，6 轴 IMU 需要不同初始化/实现条件，不能直接视为默认支持 |
| FAST-LIO / FAST-LIO2 | 紧耦合迭代 Kalman filter；FAST-LIO2 的论文描述了直接将原始点注册到地图、使用 ikd-Tree 增量维护地图 | 上游仓库依赖 catkin/ROS 1 组件；ROS 2 port 需单独审查。基础仓库与相关 FAST-LIO-LOCALIZATION 扩展项目要区分；没有统一 CPU/帧率保证 |
| Point-LIO | 点级/高带宽 LIO，官方 README 描述了高输出频率和激烈运动场景能力 | 上游 README 的测试环境以 Ubuntu 20.04、ROS Noetic、catkin 和 Livox 驱动为主；依赖逐点时间戳的 Livox CustomMsg 数据路径，不能外推为任意 LiDAR/ROS 2 环境 |
| LVI-SAM / FAST-LIVO 系列 | 融合 LiDAR、视觉和 IMU，利用几何与视觉观测互补 | 相机模型、LiDAR 类型、时间同步、标定、曝光/光照、算力和数据接口显著增加系统复杂度；具体能力必须对应论文与代码版本 |

**不要使用“通用机器人选 FAST-LIO2”“剧烈运动就选 Point-LIO”“有回环就选 LIO-SAM”这类单条件决策。** 算法的实验结果只适用于论文/仓库明确描述的数据、传感器、环境和实现版本。选型时必须检查任务是否需要纯里程计、局部建图、回环、全局重定位、跨会话地图或已知地图定位。

### 3.1 如何理解几种典型架构

- **FAST-LIO2**：论文描述的直接点到地图注册与增量 ikd-Tree 是其核心设计；不能据此推断任意点云驱动、任意时钟精度或任意计算平台都能达到相同表现。
- **LIO-SAM**：官方 README 说明其维护两个因子图：一个持续进行地图/位姿优化，另一个以 IMU 和 LiDAR 里程计实现高频里程计估计。GPS 和回环作为因子接入的条件取决于配置与数据可用性。
- **Point-LIO**：官方示例要求 Livox 驱动提供包含逐点时间信息的 CustomMsg；README 指出普通 Livox 点云消息路径无法提供其当时所需的逐点时间信息。部署必须先核对驱动版本和消息结构。
- **LeGO-LOAM**：代码假设可将点云投影到 range image 并正确识别地面；上游对 VLP-16 的参数有明确配置示例，同时说明适配其他传感器需要正确的线束/ring 与投影参数。
- **slam_toolbox**：它是 2D pose-graph SLAM/定位方案，不应与 3D LIO 的局部点云地图或全局点云图优化混作同一任务类别。

## 4. 回环、地图与长期运行

### 4.1 回环检测

回环检测试图识别机器人重新到达已访问区域，并为历史轨迹添加全局约束。常见思路包括扫描描述子检索、视觉地点识别、几何匹配和位姿图一致性检查。

示例方法：

- Scan Context：将点云按环形/扇区等结构编码为描述子，再进行候选检索。
- STD（Stable Triangle Descriptor）：通过局部几何结构生成描述子以检索候选回环。
- 几何验证：对候选回环进一步做 ICP/NDT 等匹配与位姿一致性检查。

**误回环可能比漏回环更危险**：错误约束会扭曲整个优化图。不能只根据描述子距离就接受回环；阈值、几何验证、环境动态性和地图坐标一致性均需在目标场景评估。

### 4.2 地图表达

| 地图形式 | 常见用途 | 设计要点 |
|---|---|---|
| 2D OccupancyGrid | 平面导航、Nav2 costmap 静态层 | 栅格分辨率按障碍尺寸、定位误差、地图范围、传感器能力和内存预算确定；不能固定采用某个厘米数 |
| 3D 点云地图 | 点云匹配、可视化、三维环境表达 | 考虑坐标系、点密度、动态物体、地图裁剪/分块、压缩与更新策略 |
| 体素/占据结构 | 3D 障碍表达、近邻查询或规划 | 明确体素尺寸、占据更新、未知空间语义和内存/算力开销 |
| TSDF/ESDF 等距离场 | 表面重建、碰撞距离/规划 | 明确截断距离、融合策略、更新频率与下游规划约束 |

3D LIO 输出 `PointCloud2` 或内部地图数据，并不自动满足 Nav2 `OccupancyGrid` 的坐标、语义和更新要求。若要用于 2D 导航，需要定义地面/障碍高度范围、投影策略、动态障碍过滤和地图更新边界。

### 4.3 长期建图与地图复用

区分局部滑动地图、全局位姿图、序列化地图和可持续更新的地图。slam_toolbox 的 lifelong mapping 与 serialized pose-graph 面向 2D pose graph 工作流；不能把它简单等同于 3D LIO 的点云地图增量维护。环境变化时应明确：哪些新观测可更新地图、如何保留历史、怎样处理移动障碍、如何回滚错误更新，以及如何发布地图版本。

## 5. 工程集成与调试重点

1. **时间同步与逐点时间**：旋转式/非重复扫描 LiDAR 在一帧扫描期间持续运动；若驱动丢失逐点时间或 IMU/LiDAR 时钟偏差未建模，去畸变和匹配会受影响。不要使用固定“超过某毫秒就必然抖动”的阈值；应按角速度、线速度、扫描周期、点时间字段和允许误差预算测量。
2. **LiDAR–IMU 外参**：核对平移/旋转方向、坐标轴、单位和变换应用顺序。外参误差的影响随运动、安装位置、传感器视场和场景变化；不要把固定角度误差写成通用漂移阈值。
3. **点云格式与驱动**：核对 ring/line、每点时间戳、强度、坐标轴、扫描模式、frame_id、时间基准和消息类型。算法 README 中的驱动要求不是可互换建议。
4. **去畸变与运动补偿**：检查 IMU 频率/噪声、扫描内时间、点云排序、初始姿态、重力方向和时间偏移。异常时同时检查数据采集和驱动，不要只调滤波参数。
5. **降采样与地图尺寸**：Voxel size、点云保留率、最大地图范围和近邻数，应基于目标传感器点密度、测距、运动速度、环境结构、误差预算和实时性测试确定；不引用某款 LiDAR 的固定点频或固定体素大小作为通用参数。
6. **2D/3D 输出接口**：明确建图结果是 OccupancyGrid、点云、体素还是 pose graph；如要接 Nav2，说明投影/转换、地图分辨率、坐标系、更新频率和 costmap 接口。
7. **多机器人地图共享**：除地图版本外，还需定义 datum、坐标变换、传感器外参、时间基准、地图更新冲突及回滚策略；仅把文件上传云端不能解决多机器人地图一致性。

## 6. 算法评测与验收

任何“精度更高”“实时”“抗退化”“高动态鲁棒”等结论都必须绑定测试口径。建议至少记录：

| 维度 | 指标示例 | 必须注明 |
|---|---|---|
| 轨迹精度 | APE/RPE、绝对/相对误差 | 数据集/场地、真值系统、轨迹对齐方式、统计量、单位 |
| 连续跟踪 | 失跟次数、失跟时长、恢复时间 | 运动速度/角速度、遮挡/动态场景、初始化与重置方式 |
| 回环质量 | Precision/Recall、误回环率、漏检率 | 候选检索、几何验证、真值标注和样本分布 |
| 实时性 | 端到端延迟、吞吐、CPU/GPU/内存 | 传感器模式、点数/帧、计算平台、线程配置、温度与持续负载 |
| 地图质量 | 几何误差、完整度、地图一致性 | 评测对象、地图分辨率/体素大小、对齐方式与动态物体处理 |
| 可靠性 | 运行时长、异常退出、恢复能力 | 软件版本、驱动版本、数据丢包、断连、温度与故障注入 |

数据集成绩、单次演示视频和论文中的最大频率，不足以证明某个目标产品达到实时性、可靠性或安全要求。产品验收还需要目标传感器、计算平台、安装结构和运行环境下的重复测试。

## 7. 软件、版本与许可证核验

| 项目 | 上游公开环境/入口 | 当前可确认的许可/兼容性边界 |
|---|---|---|
| FAST-LIO / FAST-LIO2 | https://github.com/hku-mars/FAST_LIO | 仓库 LICENSE 文件为 GPL-2.0；package.xml 的 `<license>` 字段却写 BSD，存在声明冲突，需向维护者确认并按实际分发文件审查。主仓库构建定义使用 catkin/ROS 组件，不能假定原仓库是 ROS 2 原生包 |
| Point-LIO | https://github.com/hku-mars/Point-LIO | 上游 README 测试 Ubuntu 20.04/ROS Noetic/catkin，并依赖 Livox 驱动和逐点时间 CustomMsg；当前 LICENSE 文件文本为 BSD 3-Clause，部署仍需锁定 commit 并检查依赖许可证 |
| LIO-SAM | https://github.com/TixiaoShan/LIO-SAM | README 指向独立 ROS 2 分支；原始实现使用 catkin/ROS 1。仓库 LICENSE 文件为 BSD 3-Clause，但 package.xml 写 TODO，需分别记录，不能把 package.xml 当作最终许可声明 |
| slam_toolbox | https://github.com/SteveMacenski/slam_toolbox | 仓库 LICENSE 为 LGPL-2.1；ROS 2 分支/发行版包需核对实际 commit 和依赖 |
| KISS-ICP | https://github.com/PRBonn/kiss-icp | README 提供 ROS 2 构建入口，ROS 1 官方支持已弃用；LICENSE 为 MIT。它是 LiDAR odometry 基线，不是 LIO（不应误列为 LiDAR–IMU 融合算法） |
| Cartographer | https://github.com/cartographer-project/cartographer | 上游 README 声明不再积极维护，ROS fork 仅有限维护；需要核对目标发行版 fork、补丁与依赖状态 |
| LeGO-LOAM | https://github.com/RobustFieldAutonomyLab/LeGO-LOAM | 上游面向 ROS 兼容地面车辆，默认配置以水平 VLP-16 为主；迁移到其他 LiDAR 需适配点云投影与地面分割，原始仓库构建示例为 catkin |

软件选型必须进一步固定 repo URL、tag/commit、编译器、ROS 发行版、OS、依赖版本和许可证副本。仓库主页显示的 license badge、package.xml 的声明、实际 LICENSE 文件及第三方依赖可能不一致；出现冲突时先登记为待澄清，不以单一字段宣称合规。

## 8. 上下游关系

**上游输入**：[[激光雷达]] · [[IMU]] · [[09-04-传感器选型与标定]] · 时间同步与外参标定

**算法基础**：[[卡尔曼滤波]] · [[多传感器融合定位]] · [[SLAM总览]]

**下游输出**：[[建图流程]] · [[导航流程]] · [[Nav2导航框架]] · [[性能指标体系]] · [[多机器人调度与车队管理]]

## 9. 本轮定向复核与未关闭事项（2026-11-03）

本轮处理：

- 删除“2023–2026 工程主力”“通用机器人黄金组合”等无统一证据支撑的算法排名。
- 纠正 LeGO-LOAM 只支持“VLP 型”的过度概括，明确其上游默认以水平 VLP-16/地面车辆为设计目标，其他 LiDAR 需适配点云投影。
- 纠正 LIO-SAM 的架构描述，按上游 README 区分持续地图/位姿图与 IMU 里程计因子图，并标出原始 ROS 1 与 ROS 2 分支。
- 将 FAST-LIO2 的直接点注册和 ikd-Tree 特征写成论文/仓库所支持的设计，不再引用通用 P4 CPU、固定频率或“绝无回环”等未经目标版本核验的断言。
- 限定 Point-LIO 对 Livox CustomMsg 逐点时间、ROS Noetic/catkin 环境的上游依赖，避免把单一仓库实现扩展成任意传感器兼容结论。
- 将固定 5–10cm 地图分辨率、5ms 同步阈值、0.5° 外参阈值、Mid-360 点频和固定 voxel 范围移除，改成测量/设计/测试字段。
- 发现 FAST-LIO LICENSE 与 package.xml 许可声明冲突；LIO-SAM LICENSE 与 package.xml TODO 状态不一致。分别记录，不替项目作法律结论。

### 本轮核验来源

1. FAST-LIO2 论文：Xu et al., IEEE Transactions on Robotics, 2022. https://doi.org/10.1109/TRO.2022.3141876
2. FAST-LIO 官方仓库及 package.xml / LICENSE：https://github.com/hku-mars/FAST_LIO
3. Point-LIO 官方 README / LICENSE：https://github.com/hku-mars/Point-LIO
4. LIO-SAM 官方 README / LICENSE / package.xml：https://github.com/TixiaoShan/LIO-SAM
5. LIO-SAM 论文：Shan et al., IROS 2020. https://doi.org/10.1109/IROS45743.2020.9341176
6. LeGO-LOAM 官方 README：https://github.com/RobustFieldAutonomyLab/LeGO-LOAM
7. slam_toolbox 官方 README / LICENSE：https://github.com/SteveMacenski/slam_toolbox
8. Cartographer 上游维护声明：https://github.com/cartographer-project/cartographer/blob/master/README.rst
9. KISS-ICP 官方 README / LICENSE：https://github.com/PRBonn/kiss-icp

**未关闭事项：** 未构建或运行任何 SLAM/LIO 实现；未用目标 LiDAR/IMU/计算平台测试时间同步、外参、去畸变、定位精度、回环、地图质量或热稳态；未固定本项目所需 ROS 发行版、repo commit 和依赖锁定。FAST-LIO 与 LIO-SAM 的许可声明冲突需维护者澄清；第三方 SDK/驱动/子模块许可尚未完整审查。本文仍为局部主张定向复核，不代表全文 claim-level 验收、产品安全批准或量产放行。
