---
tags: [算法, SLAM]
aliases: [SLAM, 同步定位与建图, SLAM总览]
创建日期: 2026-11-01
更新日期: 2026-11-03
---

# SLAM 总览（同步定位与建图）

> Simultaneous Localization And Mapping：在未知环境中**同时**估计自身位姿并构建地图——"鸡生蛋"问题：定位需要地图，建图需要定位。SLAM 是 [[移动机器人]] 的技术底座。

## 问题形式化

```
已知: 传感器观测 z_{1:t}(LiDAR 扫描/图像特征), 运动输入 u_{1:t}(IMU/里程计)
求解: 位姿序列 x_{1:t} + 地图 m  → 后验 P(x_{1:t}, m | z_{1:t}, u_{1:t})
两大流派:
  滤波器派: EKF-SLAM/粒子滤波(Gmapping) — 增量, 只保留当前+边缘化历史
  图优化派(现代主流): 因子图/位姿图, 前端给约束+后端非线性最小二乘(Ceres/g2o/GTSAM)
```

## 技术分支地图

| 分支 | 传感器 | 代表 | 深入页 |
|---|---|---|---|
| 2D 激光 SLAM | 2D LiDAR(+IMU/里程计) | Gmapping、Hector、**Cartographer**、slam_toolbox | [[激光SLAM]] |
| 3D 激光 SLAM / LIO | 3D LiDAR+IMU | LOAM、LIO-SAM、FAST-LIO2、Point-LIO（代表性研究/实现，需按数据与平台评估） | [[激光SLAM]] |
| 视觉 SLAM | 单目/双目/RGB-D | ORB-SLAM3、VINS-Fusion | [[视觉SLAM]] |
| 激光-视觉-惯性融合 | LiDAR+相机+IMU | FAST-LIVO2、R3LIVE | [[多传感器融合定位]] |
| 语义/稠密/神经场景表示 | 语义特征、NeRF/3D Gaussian Splatting 等 | 代表系统随研究方向演进，需区分定位建图与场景重建目标 | [[学习型机器人算法]] |

## SLAM 系统五要素（任何 SLAM 拆开都是这五块）

1. **前端（数据关联）**：扫描匹配（ICP/NDT/相关性扫描匹配 CSM）或视觉特征跟踪 → 产生帧间约束
2. **后端（优化）**：因子图 + 非线性最小二乘（Levenberg-Marquardt/GN），增量式（iSAM2/GTSAM）或分批
3. **回环检测（Loop Closure）**：识别"回到老地方"消除累积漂移——2D 用扫描上下文/分支定界（Cartographer 分支定界）；3D 用 Scan Context/STD；视觉用词袋 DBoW2
4. **地图表示**：2D 栅格（占据概率）、点云、体素地图（ikd-Tree/VDB）、TSDF/ESDF（规划用）、3D Gaussian Splatting、NeRF 等显式/隐式场景表示（并非传统占据地图或定位后端的直接替代品）
5. **图管理/长期运行**：位姿图剪枝、地图合并、重定位（AMR 7×24 的实际难点）

## 关键指标（→ [[性能指标体系]]）

| 指标 | 含义 | 优秀水平 |
|---|---|---|
| 建图一致性 | 回环前后位姿图残差 | 2D <5cm；3D <10cm |
| 回环检出率 | 应检出的回环被检出比例 | >95% |
| 重定位成功率 | 丢失后重新定位 | >99%（含瞬时光照变化） |
| 建图速度 | 实时性 | 按目标输入频率和系统 deadline 实测 |
| 长廊/退化场景表现 | 几何约束少的场景 | 配语义/外部约束 |

## 退化场景（SLAM 的死亡地带）

- **长直走廊**：前方点云相似，平移不可观 → 加 IMU/视觉/增加斜向特征
- **玻璃幕墙**：LiDAR 穿透 → 超声波/毫米波兜底 → [[毫米波雷达与超声波]]
- **空旷大平地**：无结构 → 二维码/反光板辅助 → [[移动机器人]] 导航分级
- **动态人流**：静态假设破产 → 动态物体滤除（语义分割）→ [[视觉感知算法]]
- **重复纹理仓库**：视觉回环误匹配 → 几何校验 + 多传感器一致性

## 工程选型决策树

```
室内 2D 结构化(仓库/写字楼)? → slam_toolbox / Cartographer 2D
室内 3D 需求(叉车举升/立体障碍)? → FAST-LIO2 + 3D costmap
强动态/剧烈运动? → Point-LIO
室外大场景+回环? → LIO-SAM(+GPS 约束)
视觉主导(纹理好/便宜)? → ORB-SLAM3 / VINS-Fusion
需语义/对接 LLM 导航? → 3DGS 语义 SLAM(新兴)
```

## 上游板块
- [[激光雷达]] · [[深度相机]] · [[IMU]] —— 数据来源（硬件）
- [[09-04-传感器选型与标定]] —— 标定决定 SLAM 上限（流程）

## 下游板块
- [[建图流程]] —— 部署期作业（流程）
- [[导航流程]] —— 运行期定位消费（流程）
- [[激光SLAM]] · [[视觉SLAM]] · [[多传感器融合定位]] —— 分支深入（算法）
- [[性能指标体系]] —— 回环精度/重定位率 KPI（参数）

## 细节加深（V2）
- **选型决策依据**：slam_toolbox 官方文档列出 2D pose-graph、地图序列化/续图和 localization mode；Cartographer 上游 README 标注不再积极维护，但 ROS fork 与发行版包需单独核对；FAST-LIO2、Point-LIO、LIO-SAM 不设通用排名，需按目标传感器、数据集、平台、功能和许可证比较。
- **SLAM 入门中文路线**（两篇高赞已验证）：计算机视觉life《学习 SLAM 如何避免从入门到放弃》（#85）+ Sky Shaw《SLAM 技术综述》（#86）。
- **评测工具**：evo（#82，GPL-3.0）算 APE/RPE——SLAM 论文与验收的通用语言；数据格式 TUM/KITTI/EuRoC。

## 代码实例与开源项目
| 项目 | 语言 | 许可证 | 说明 | 链接 |
|---|---|---|---|---|
| slam_toolbox | C++ | LGPL-2.1 | ROS2 2D SLAM 事实标准 | https://github.com/SteveMacenski/slam_toolbox |
| evo | Python | GPL-3.0+ | 轨迹评测（APE/RPE） | https://github.com/MichaelGrupp/evo |
| KISS-ICP | C++/Python | MIT | 免调参 LiDAR 里程计（学配准好教材） | https://github.com/PRBonn/kiss-icp |

> 链接验证：[[链接台账]] #48/#49/#53/#82/#85/#86（快照 2026-11-01）。

## 相关链接
- 上位：[[算法地图]]
- 分支深入：[[激光SLAM]] · [[视觉SLAM]] · [[多传感器融合定位]] · [[卡尔曼滤波]]（数学地基）
- 流程落地：[[建图流程]] · [[导航流程]]
- 传感器：[[激光雷达]] · [[深度相机]] · [[IMU]]
- 项目：[[项目-amr]]（localization_slam/mapping 目录） · [[项目-清洁机器人]]（vSLAM）


## 2026-11-03｜P1 SLAM 总览主张定向复核

本轮对本页算法成熟度、通用性能阈值、3DGS 与 NeRF 关系及选型结论做定向纠偏：

- 删除“2025 工程主力”“通用机器人选 FAST-LIO2”“黄金组合”等无法由统一行业证据支持的普遍性推荐。算法选择必须受传感器、运动、场景、计算平台、地图/回环需求、ROS 发行版和许可证约束。
- 删除建图一致性 5/10cm、回环检出率 95%、重定位成功率 99% 等脱离数据集、真值、成功判据和工况的“优秀水平”；改为要求定义 APE/RPE、Precision/Recall、首次定位时间和端到端延迟等指标及测试口径。
- 纠正“3DGS 取代 NeRF”的表述。3DGS/NeRF 属于场景表示与重建方向，不能未经任务验证就视为传统占据栅格、点云地图或 SLAM 定位后端的替代品。
- Cartographer 上游仓库 README 明确称其不再积极维护；ROS 包索引中仍有发行版/分支状态信息，需区分上游与 ROS fork，不能只写“停止维护”而忽略实际分支和目标发行版。
- slam_toolbox ROS 包索引列示 Lyrical/Humble 等发行版的维护与发布状态，且官方项目文档说明其 2D pose-graph、地图序列化/续图和 localization mode 能力；具体能力仍应按版本和配置验证。
- ORB-SLAM3 论文支持其单目/双目/RGB-D、视觉/视觉惯性、多地图/多会话能力，但论文基准精度不应直接外推到任意相机、环境或机器人。

### 核验来源（访问日期：2026-11-03）

1. Cartographer upstream README：<https://github.com/cartographer-project/cartographer/blob/master/README.rst>。
2. ROS Index：Cartographer <https://index.ros.org/p/cartographer/>；slam_toolbox <https://index.ros.org/p/slam_toolbox/>。
3. ORB-SLAM3，IEEE T-RO 2021：<https://doi.org/10.1109/TRO.2021.3075644>。
4. FAST-LIO2，IEEE T-RO 2022：<https://doi.org/10.1109/TRO.2022.3141876>。
5. FAST-LIVO2，IEEE T-RO 2025：<https://doi.org/10.1109/TRO.2024.3502198>。

**未关闭事项：** 本轮没有运行任何 SLAM 软件，没有在目标传感器/机器人上测试，也未逐一核验本页所有算法仓库的 commit、许可证、依赖与 ROS 发行版兼容性；本页仍未通过全文 claim-level 验收。
