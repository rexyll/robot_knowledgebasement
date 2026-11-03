---
tags: [项目, AMR, ROS2]
aliases: [项目-amr, amr项目, GenRobo AMR]
路径: Z:\GeneralPurpose_Robot\amr
创建日期: 2026-11-01
更新日期: 2026-11-01
---

# 项目：amr（GenRobo AMR 全栈系统）

> **定位**：一套多机型 AMR（潜伏/牵引/叉举系列，models/ 下 d1/d2/ft2/ft4 等机型）的**整机全栈软件**：机端 ROS2 + 调度通信 + 云端 + 上位机，已完成"能力插件化"重构。
> **路径**：`Z:\GeneralPurpose_Robot\amr`　**梳理基线**：项目内 `doc/ARCHITECTURE.md`（2026-10-30 基线，16 篇 arch 文档）

## 1. 系统构成（三端 + 一套机型资产）

| 端 | 技术 | 内容 |
|---|---|---|
| **机端** | **ROS2 Jazzy** + rclcpp | `terminal2_ROS2/src` 下 94 个包（16 能力族 + 41 个 `gen_*` + 38 个 `aic_*` 旧副本） |
| **云端** | Spring Boot 2.3.4 + Spring Cloud Hoxton + **Nacos + Dubbo** + MyBatis-Plus + RabbitMQ + Netty + JeroMQ；另有 Go backend | `cloud/`：AICCMS、api-server、backend、gen-cloud、gen-cloud-build、gen-cloud-scene、wms-boss（RCS/WMS 分离） |
| **上位机** | Qt5.15（qmake）+ libzmq + protobuf；Web：React + umi | `app/`：robot_hmi、management、web_ui、customers、tools |
| **机型资产** | ROS1 URDF/SRDF + 运动学 | `models/genmodel_{d1_1,d2_1,d2_3,ft2_1,ft4_0…}`（D=潜伏?，FT=叉举? 系列） |

## 2. 机端四层能力架构（本项目的架构灵魂）

```
契约层  gen_capability_msgs(gen_msgs)     IDL 契约 + CONTRACT_VERSIONING + SHA256 指纹
核心层  gen_capability_core                能力注册/发现/会话管理/容错
宿主层  gen_capability_host                对外固定端点(见下), 会话所有权
插件层  gen_plugin_{navigation_nav2, navigation_legacy, docking_autodock2,
        follow_basic, perception_basic, traffic_basic, traffic_zmq, example, template}
适配器  gen_adapter_{nav2, autodock, traffic}(进程级桥接) + gen_map_transport(地图搬运)
```

**能力端点（宿主对外固定接口）**：
- 3 个 Action：`navigate_to` / `follow_target` / `dock_robot`
- 6 个业务 Service + 2 个管理 Service + 3 类 Topic

**设计语义**：插件可**热切换**（如 nav2 实现与 legacy 实现并存）、可**故障注入测试**（capability_fault_injection.md）、有明确**降级路径**（fault → 降级 → 恢复）。

## 3. 既有业务包全景（gen_* 41 个，按域分组）

| 域 | 包 | 知识库对应 |
|---|---|---|
| 导航 | gen_nav_core、gen_path_plan、gen_obs_avoid_strategy、gen_obstacle_detect、gen_mr_nav、gen_multi_floor_navigation、gen_multi_map_navigation、gen_map_server、gen_field_detector | [[导航流程]] · [[路径规划算法]] |
| 定位 | gen_robot_pose_ekf、gen_kalman_filters、gen_ar_tag | [[多传感器融合定位]] · [[卡尔曼滤波]] |
| 感知 | gen_leg_tracker(+detector)、gen_people_tracking、gen_wing_detector、gen_laser_feature_line_extraction | [[视觉感知算法]]（行人腿检测=LIO 融合鲁棒方案） |
| 对接 | gen_auto_dock、gen_dock_param、gen_follow_base、gen_uwb_follower、aic_auto_dock | [[充电桩与自动充电]] |
| 任务/交管 | gen_task_center、gen_traffic_management(+utils)、gen_dispatch_bridge | [[多机调度流程]] |
| 驱动 | gen_serial、gen_sick_s300（**SICK S300 LiDAR**）、gen_driver_core、gen_robot_interface、gen_robot_communication | [[激光雷达]] · [[实时系统与嵌入式]] |
| GUI | gen_gui(+base/wt210)、gen_mr_gui | HMI |
| 记录 | gen_rosbag_record | 数据闭环 → [[构建与CI工具链]] |
| 仿真 | genrobo_simulations | [[仿真平台]] |

> 品牌迁移两轮完成：`ws→gen`、`aic_→gen_`（aic_* 副本仍在 src 下可被全量构建选中——已知 P1 技术债，见项目 doc/24-gaps）。

## 4. 跨端通信（与云端）

- **机端↔调度**：**ZeroMQ + protobuf3** 统一总线（不是 ROS2 DDS 跨机！），交管双通道（basic 插件 / zmq 插件，端口 10002）
- **云端内部**：Nacos 注册配置（8848）+ Dubbo RPC + RabbitMQ（5672）+ MySQL（3306）+ Redis（6379）
- 体现行业趋势：**弱网/跨机场景不用 DDS**，用 ZMQ/HTTP → [[ROS与ROS2]] · [[云平台与IoT通信]]

## 5. 质量门禁（可复用的工程实践）

```
scripts/ci_capability.sh 六步: 构建 → 测试(92 例) → plugins.xml 校验
  → 契约 lint → 版本冻结 → 文档链接检查(43 md/225 链接全绿)
test/capability_smoke_stability.sh 3 150 → 3 轮×150s 稳定冒烟, RESULT PASS 3/3
构建入口: scripts/package_terminal.sh
台账: TaskPlan.md(39 节点重构台账, 38 完成) — 单一事实源模式
```
→ 模式分析见 [[构建与CI工具链]]

## 6. 文档资产（doc/ 16 篇 + 6 篇能力文档）

`arch/00-overview`（入口）→ `01-terminal-ros2`（机端五层）→ `02-dispatch-cloud`（ZMQ/云）→ `10/11-flows`（主流程+能力子流程：热切换/导航/对接/跟随/交管/感知/建图切图）→ `12-flows-ops`（故障注入/契约变更/CI）→ `20-modules`（依赖图/交互矩阵/数据所有权）→ `21-interfaces`（端点总表）→ `24-gaps`（P0/P1/P2 技术债 14 条）→ `90-facts`（事实基线）。

## 7. 知识库映射（本项目 ↔ 通用知识）

| 项目实现 | 通用知识页 |
|---|---|
| 能力插件四层架构 | [[AMR整体架构]]（SOA 化趋势实例） |
| navigate_to/dock_robot | [[导航流程]] · [[充电桩与自动充电]] |
| gen_traffic_management | [[多机协同与调度算法]] |
| gen_sick_s300 | [[激光雷达]]（安全扫描仪双重身份 → [[安全防护器件]]） |
| gen_kalman_filters/gen_robot_pose_ekf | [[卡尔曼滤波]] |
| ZMQ+protobuf 总线 | [[云平台与IoT通信]] |
| TaskPlan 台账 | [[构建与CI工具链]] |

## 相关链接
- 同族项目：[[项目-清洁机器人]]（同公司、同 ROS2 Jazzy 基线） · [[项目-Bozlin视觉框架]] · [[三项目关系总览]]
- 架构母版：[[AMR整体架构]] · [[调度系统RMS]] · [[云端协同与OTA流程]]
