---
tags: [算法, SLAM, 激光SLAM]
aliases: [激光SLAM, LIO, LiDAR SLAM, Cartographer]
创建日期: 2026-11-01
更新日期: 2026-11-01
---

# 激光 SLAM

> 以 [[激光雷达]] 为主传感的 SLAM。2D 用于室内 AMR 主航，3D LIO（LiDAR-Inertial Odometry）是 2023-2026 的工程主力形态。

## 2D 激光 SLAM 三代表

| 系统 | 核心方法 | 状态 | 适用 |
|---|---|---|---|
| **Gmapping** | RBPF 粒子滤波（粒子=轨迹假设） | 经典/维护模式 | 低算力小场景 |
| **Cartographer** | 子图(submap)+扫描匹配 + 分支定界回环 + 位姿图优化 | 谷歌开源，工业验证多 | 中大型室内，2D 首选之一 |
| **slam_toolbox** | 优化式（Ceres）+ 地图序列化/续图 | ROS2 生态默认 | ROS2 项目标配，支持终身建图 |

2D 前端核心：**扫描匹配**——相关性匹配（CSM，暴力搜索初值）→ 精配准（高斯牛顿）。子图思想：一段帧构成局部一致子图，子图完成后冻结进全局优化。

## 3D LIO 谱系（重点）

| 系统 | 机制 | 特点 | 弱点 |
|---|---|---|---|
| LOAM（2014） | 特征（边缘/平面点）提取+高低频分离（odometry/mapping 两线程） | 开山之作 | 无回环 |
| LeGO-LOAM | +地面分割+分段优化+回环 | 地面机器人友好 | 只支持 VLP 型 |
| LIO-SAM | **因子图（GTSAM）**：IMU 预积分+里程计+GPS+回环 多源因子；滚动优化 | 可融合 GPS、回环好，室外大场景利器 | 需 9 轴 IMU；静止初始化易崩；参数敏感 |
| **FAST-LIO2** | 紧耦合 **迭代误差状态卡尔曼滤波（iEKF）** + **ikd-Tree 增量地图**直接在地图上做残差 | 快（P4 级 CPU 实时）、内存增量管理、免特征提取（直接点-面） | 无原生回环；快速旋转长时漂移 |
| **Point-LIO** | 点级高频状态估计（无帧概念）+IMU 退化和运动补偿 | 剧烈运动/高动态最鲁棒；退化场景强 | 算力要求高于 FAST-LIO2 |
| FAST-LIVO2 / R3LIVE | LiDAR-视觉-惯性紧耦合 | 纹理+几何互补，巡检退化场景 | 工程复杂度高 |

> 2025-2026 工程共识：**通用机器人选 FAST-LIO2**（配 Mid-360 类半固态雷达是黄金组合）；**剧烈动态/退化场景选 Point-LIO**；**室外大场景需回环/GPS 选 LIO-SAM**；三者之上补 FAST-LIVO2 类多路融合（来源：多组开源实测对比，详见 [[SLAM总览]]）。

## 回环检测（3D）

- Scan Context：极坐标描述子+距离检索（KISS-ICP 时代仍常用）
- STD（Stable Triangle Descriptor）：三角形描述子，稳定
- 分支定界（Cartographer 3D 模式）：全局精搜
- 回环接受门槛：几何验证（ICP 残差）+ 位姿一致性，误回环比不回环更致命（整图扭曲）

## 2D 占据栅格地图（AMR 导航的直接消费格式）

```
P(occ|x) ∈ [0,1] 每格 5-10cm; log-odds 更新:
l_t = l_{t-1} + log(p/(1-p)) - l_0   (射线投射 ray casting)
发布: nav_msgs/OccupancyGrid → costmap Static Layer → [[Nav2导航框架]]
```

## 工程要点（踩坑清单）

1. **时间同步**：LiDAR-IMU 时延 >5ms LIO 就抖 → 标定 + 驱动层硬件时间戳（→ [[视觉软件栈]]）
2. **外参**：雷达-IMU 旋转外参 0.5° 误差=可感知漂移 → 靶标/运动激励标定
3. **降采样参数**：Mid-360 点频 20 万点/s，Voxel 0.25-0.5m 常用
4. **多机共享地图**：地图库版本化 + 各机差异（安装位姿）→ 地图分发走云 → [[云平台与IoT通信]]
5. **终身建图**：环境变化（货架挪动）→ slam_toolbox 地图序列化增量更新 vs 定期重扫

## 上游板块
- [[激光雷达]] · [[IMU]] —— 硬件输入（硬件）
- [[卡尔曼滤波]] —— iEKF 数学内核（算法）
- [[09-04-传感器选型与标定]] —— 时延/外参标定（流程）

## 下游板块
- [[建图流程]] —— 作业化落地（流程）
- [[Nav2导航框架]] —— 地图→costmap（软件）
- [[SLAM总览]] · [[多传感器融合定位]] —— 体系与运行期（算法）

## 细节加深（V2）
- **仓库许可证地图**（台账 #50-#52，快照 2026-11-01）：FAST-LIO2/Point-LIO = **GPL-2.0**（商用闭源需注意）；LIO-SAM = BSD-3（可商用闭源）；选型时把许可证当第一参数。
- **Patchwork++**（#54，BSD-2）：3D 地面分割标准件，FAST-LIO2 前置地面滤除的常用搭档。
- **FAST-LIO2 补回环的社区做法**：接 SC-PGO / 或直接选 Point-LIO+独立回环模块——纯 FAST-LIO2 长时漂移问题要有预案（与 V1 结论呼应）。

## 代码实例与开源项目
| 项目 | 语言 | 许可证 | 说明 | 链接 |
|---|---|---|---|---|
| FAST-LIO2 | C++ | GPL-2.0 | 紧耦合 iEKF+ikd-Tree | https://github.com/hku-mars/FAST_LIO |
| Point-LIO | C++ | GPL-2.0 | 点级高频 LIO | https://github.com/hku-mars/Point-LIO |
| LIO-SAM | C++ | BSD-3 | 因子图 LIO（可融 GPS） | https://github.com/TixiaoShan/LIO-SAM |
| Patchwork++ | C++/ROS | BSD-2 | 3D 地面分割 | https://github.com/url-kaist/patchwork-plusplus |

> 链接验证：[[链接台账]] #50-#54（快照 2026-11-01）。

## 相关链接
- 上位：[[SLAM总览]] · [[算法地图]]
- 硬件：[[激光雷达]] · [[IMU]]
- 数学地基：[[卡尔曼滤波]] · [[多传感器融合定位]]
- 流程：[[建图流程]]
- 项目：[[项目-amr]]（localization_slam 目录）
