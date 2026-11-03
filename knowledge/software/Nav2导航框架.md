---
tags: [软件, 导航, Nav2]
aliases: [Nav2, navigation2, 导航框架]
创建日期: 2026-11-01
更新日期: 2026-11-01
---

# Nav2 导航框架（navigation2）

> ROS2 官方导航栈：行为树驱动的模块化导航系统。是 [[项目-amr]] / [[项目-清洁机器人]] 自研导航之外的对照与基础件。

## 架构（四大服务器 + 行为树）

```
BT Navigator(行为树总指挥)
 ├─ Planner Server   全局路径 → ComputePathToPose/ThroughPoses
 │    ├─ NavFn(A*/Dijkstra)   经典栅格
 │    ├─ Smac Planner  ★SE2/Hybrid-A*/2D，运动学可行路径（清洁机弓字形也用它扩展）
 │    └─ Theta*       任意角
 ├─ Controller Server 局部控制 → FollowPath
 │    ├─ DWB / RPP(Regulated Pure Pursuit) ★稳健直线速度控制
 │    ├─ TEB / MPPI(2024 起官方主打, 采样式 MPC)
 │    └─ Rotation Shim(窄道原地转向外壳)
 ├─ Recovery/Behavior Server 恢复行为：旋转清除、等待、后备
 ├─ Waypoint Follower  巡点任务编排
 └─ Costmap 2D ×2(全局/局部) ← 静态地图 + LiDAR/相机/超声波 多层叠加
```

- **行为树（BT）**：把"规划失败→重规划→清代价区→旋转→后退→超时失败"的策略写成 XML 树，可热换策略不用改代码
- 所有服务器都是 ROS2 **Action/Service 服务端**，可独立调用 → 与自研调度/FSM 对接容易（→ [[调度系统RMS]] · [[项目-清洁机器人]] 的 fsm_core）

## 代价地图（Costmap）分层——避障的核心数据结构

| 层 | 作用 |
|---|---|
| Static Layer | 静态地图（SLAM 输出） |
| Obstacle Layer | LiDAR/超声波实时障碍 |
| Voxel Layer | 3D 体素（深度相机低矮障碍） |
| Range Layer | 声呐/红外锥形投影 |
| Inflation Layer | 按机器人半径膨胀（代价随距离衰减） |

## 典型调参地图（AMR 工程痛点）

| 参数 | 位置 | 典型值/坑 |
|---|---|---|
| inflation_radius | costmap | =对角半径+5cm，太小贴墙擦碰 |
| xy_goal_tolerance | BT | 停靠精度 ±5-10cm，对接任务另用精对齐 |
| controller_frequency | controller | 20Hz（MCU 心跳 10Hz 以上配套） |
| max_vel_x / acc_lim | 控制器 | 满载降 30%；加速度决定甩货风险 |
| recovery behaviors | BT XML | 死循环兜底：最多 3 轮重规划→clearing→失败上报 |
| Keepout/Polygon 过滤器 | costmap | 电子围栏/单向道/限速区 → 与 [[多机调度流程]] 的区域规则一致 |

## 与自研栈的取舍

- 用 Nav2：标准生态、免费；代价：深度定制（如覆盖式清扫、走廊让行协议）要写插件
- 自研（两项目路线）：流程可控、可注入公司语义（Capability/FSM）；代价：维护成本
- 常见折中：Nav2 做单机导航 + 自研上层做调度与业务 → 参考 [[项目-amr]] 架构评估

## 上游板块
- [[ROS与ROS2]] · [[DDS专题]] —— 运行时与 QoS（软件）
- [[SLAM总览]] —— 静态地图供给（算法）
- [[09-04-传感器选型与标定]] —— /scan /odom 驱动就绪（流程）

## 下游板块
- [[09-08-算法集成与调参]] —— 集成与调参实操主战场（流程）
- [[导航流程]] —— 单机导航时序（流程）
- [[多机协同与调度算法]] —— Keepout/限速区与交管规则同源（算法）

## 细节加深（V2）
- **官方调参指南是唯一权威**（台账 #27，旧路径 /tuning/ 已 404）：含控制器对比（RPP vs DWB vs MPPI）与 RMW 性能数据。核心选型结论：直道重载 → RPP（#66）；动态密集 → MPPI（#65）；需倒车/窄位 → TEB 或 Smac Hybrid。
- **全局规划三插件**（台账 #64）：Smac 2D / Hybrid-A*（运动学可行）/ State Lattice——叉车类必须 Hybrid-A*，普通 AMR 用 2D 足够。
- **BT Navigator 的行为树 XML 是策略层**：改恢复顺序/失败重试策略改 XML 即可，不碰 C++——自研上层与 Nav2 解耦的关键抓手。
- **中文详解参考**：文火冰糖《Nav2 超详细完整详解》（台账 #45）。

## 代码实例与开源项目
| 项目 | 语言 | 许可证 | 说明 | 链接 |
|---|---|---|---|---|
| Nav2 官方文档 | C++ | Apache-2.0 | 全组件/bringup/调参 | https://docs.nav2.org |
| Nav2 Tuning Guide | — | Apache-2.0 | 官方调参（本页权威依据） | https://docs.nav2.org/rolling/configuration_and_development/tuning_guide/ |
| teb_local_planner | C++ | BSD-3 | TEB 插件官方仓库 | https://github.com/rst-tu-dortmund/teb_local_planner |

> 链接验证：[[链接台账]] #26/#27/#45/#64-#67（快照 2026-11-01）。

## lifecycle 编排与协同全景（V3 · 附件整合）

> 来源：用户附件 PDF（DeepSeek 会话，2026-11-01 导出）。

**lifecycle_manager 是这条链的"总调度"**：按**固定顺序**把 `map_server → amcl → planner_server → controller_server → bt_navigator` 等节点从 `unconfigured` 逐个推进到 `active`——避免下游节点在上游未就绪时收到无效数据（这是"起了车但导航抽风"的第一排查点：查 lifecycle 状态 `ros2 lifecycle get <node>`）。

**一条数据链上的六层协同**：

| 层级 | 核心动作 | 关键输入/输出 |
|---|---|---|
| 硬件驱动层 | 雷达/IMU/编码器/电机驱动启动，数据转 ROS 消息 | `/scan` `/imu/data` `/wheel_ticks`；订阅 `/cmd_vel` |
| TF 与里程计层 | 构建 `map→odom→base_link→sensor` 坐标链 | 静态 TF、轮计、EKF 融合输出（→ [[导航流程]] TF 专节） |
| 定位层 | 在已知图上估计 map 系位姿 | AMCL/EKF 输出 `map→odom` |
| 代价地图层 | 地图+实时障碍+膨胀半径合成"危险网格" | 全局/局部两张 costmap |
| 规划与控制层 | 全局低频规划"走哪条路"，局部高频控制"这一秒怎么动" | `nav_msgs/Path` · `geometry_msgs/Twist` |
| 行为编排层 | 行为树调用规划/控制/恢复 | NavigateToPose action 的 feedback/result |

**DWB 局部控制器的四步循环（约 20Hz，在局部代价地图上）**：
1. **速度采样**：当前速度附近动态窗口内采多组 (v,ω) 候选（受加速度限制）
2. **前向仿真**：按运动模型推演每组候选未来一小段轨迹
3. **代价评分**：碰撞风险 + 对全局路径贴合度 + 目标接近度等加权
4. **选优输出**：代价最低的 (v,ω) 发到 `/cmd_vel`

> **DWB 的本质不是"跟踪全局路径的每一个点"，而是持续选择"在当前局部感知下安全且朝目标推进"的速度指令**——障碍层标记出新障碍时，采样评分自动把撞轨迹筛掉，机器人因此绕行（即使全局静态图并不知道该障碍）。

**全局/局部失败语义不同**：全局规划失败（起终点在致命区）→ 立即返回失败；**局部控制失败（当前路段被堵）→ 先触发恢复行为**，不是立刻放弃。恢复行为按"代价从低到高"排序：**清代价地图 → 原地旋转 → 后退重规划**。频繁触发恢复行为是系统健康警示——通常指向定位漂移、传感器噪声或膨胀参数不当。

**CLI 直接下发目标（调试神器）**：

```bash
ros2 action send_goal /navigate_to_pose nav_msgs/action/NavigateToPose \
  "{pose: {header: {frame_id: map}, pose: {position: {x: 2.0, y: 0.5, z: 0.0},
   orientation: {x: 0.0, y: 0.0, z: 0.0, w: 1.0}}}}" --feedback
# 终端持续回传 distance_remaining / number_of_recoveries 等 feedback——
# 调试导航问题最直接的观测点（不依赖 RViz 点击）
```

**最小化启动**（TurtleBot3 仿真）：`ros2 launch nav2_bringup tb3_simulation_launch.py headless:=False slam:=False map:=~/tb3_map.yaml`——一条命令拉起 map_server/AMCL/planner/controller/bt_navigator 并由 lifecycle_manager 自动激活；自研 launch 封装要点：`map`/`use_sim_time`/`params_file`/`autostart:=true` 四参数（→ [[09-08-算法集成与调参]]）。

## 相关链接
- 上位：[[ROS与ROS2]] · [[软件地图]]
- 算法细节：[[路径规划算法]] · [[局部规划与避障]] · [[轨迹优化与运动控制]]
- 流程：[[导航流程]] · [[建图流程]]（上游静态地图）
- 官方：https://docs.nav2.org
