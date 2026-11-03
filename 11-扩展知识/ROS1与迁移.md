---
tags: [软件, ROS1, 迁移]
aliases: [ROS1与迁移, ROS1, ROS迁移]
创建日期: 2026-11-01
更新日期: 2026-11-01
---

# ROS1 与迁移（ROS1 → ROS2）

> **重要事实**：ROS1 最后一版 Noetic 已于 **2025-05-31 EOL**（官方 Wiki 转入存档状态，台账 #17）。新项目一律 ROS2；本页回答两个问题：① 存量 ROS1 系统怎么理解与维护；② 怎么迁移到 ROS2。

## 1. ROS1 速览（读懂存量代码用）

| 概念 | ROS1 | ROS2 对照 |
|---|---|---|
| 中心节点 | **roscore/Master**（单点故障源） | 无（DDS 自动发现）→ [[DDS专题]] |
| 通信 | TCPROS/UDPROS 自研协议 | DDS（QoS/发现/安全） |
| 构建 | catkin / catkin_tools | colcon + ament → [[构建与CI工具链]] |
| C++ API | roscpp（NodeHandle） | rclcpp（组合式节点） |
| launch | XML | XML/Python/YAML（Python 可编程） |
| 实时 | 无 | executor+alloc 实时友好 |
| 平台 | 仅 Linux | Linux/Windows/macOS/RTOS(micro-ROS) |

> 内部项目 [[项目-amr]] 的机型资产（models/ URDF）仍为 ROS1 时代产物——迁移的第一步往往是**资产先行**（URDF/SRDF 兼容性最好）。

## 2. 迁移决策树（官方指南路线，台账 #18）

```
存量系统怎么办?
 ├─ 只读资产(URDF/地图/标定) → 直接复用, 无需迁移
 ├─ 存量维护(不新增功能) → 冻结在 Noetic 虚拟机/容器, 与 ROS2 桥接共存
 └─ 活跃开发 → 按包迁移:
      1. 接口包先行: .msg/.srv 语法兼容度高, 先迁+契约测试
      2. 纯算法库(无 ros 依赖) → 零成本复用
      3. roscpp 节点 → rclcpp 重写(NodeHandle→this->create_*)
      4. launch XML → 事件驱动重写(响应处理器模型变了)
```

## 3. 桥接共存期（渐进迁移的标准姿势）

```bash
# ros1_bridge: 让 ROS1/ROS2 图互通(同机双环境)
sudo apt install ros-jazzy-ros1-bridge   # 需同时安装 ROS1 Noetic 环境
# 用法: 同名同类型话题自动桥接; .msg 字段类型需一一对应
source /opt/ros/noetic/setup.bash && source /opt/ros/jazzy/setup.bash --prepend
export ROS_MASTER_URI=http://localhost:11311
ros2 run ros1_bridge dynamic_bridge --bridge-all-topics
```

> 迁移期踩坑（社区共识）：① bridge 消息类型不匹配静默不桥接——先 `ros2 run ros1_bridge message_type_conversions` 对照表；② 时间源两套（ROS Time vs ROS2 clock）在 bridge 场景要手动对齐；③ 参数系统完全不同（全局参数服务器 → 每节点参数服务），旧参数文件不能直搬。

## 4. 上游板块
- [[ROS与ROS2]] —— ROS2 目标态知识（软件）
- [[DDS专题]] —— 迁移后通信栈的底座（软件）

## 5. 下游板块
- [[项目-amr]] —— 机型资产 ROS1→ROS2 迁移实例（项目）
- [[构建与CI工具链]] —— catkin→colcon 工程迁移（软件）

## 6. 细节加深（V2）
- **为什么 ROS1 必须迁**：EOL 后无安全补丁；Ubuntu 20.04 本身 2025-04 标准支持终止——双 EOL 叠加，安全审计过不了（→ [[功能安全体系]]）。
- **迁移工作量经验比**：接口包 1 周 / 纯算法节点 0.5-1 天·个 / 重状态机节点 1-2 周·个（回调模型差异）。全仓 40 包团队级迁移通常 1-2 人月起步。
- **不迁移的合法姿势**：把 ROS1 系统整体 Docker 化（ros:noetic 镜像）当"设备"隔离，对外只暴露 REST/MQTT——工业现场常见的过渡方案（→ [[云平台与IoT通信]]）。

## 7. 代码实例与开源项目
| 项目 | 语言 | 许可证 | 说明 | 链接 |
|---|---|---|---|---|
| ROS1 Noetic 安装（存档） | — | — | 官方安装页（Wiki 存档态） | https://wiki.ros.org/noetic/Installation |
| 官方迁移指南 | — | — | Migrating from ROS1（Jazzy） | https://docs.ros.org/en/jazzy/How-To-Guides/Migrating-from-ROS1.html |

> 链接验证：[[链接台账]] #17/#18（快照 2026-11-01）。

## 相关链接
- [[ROS与ROS2]] · [[DDS专题]] · [[术语表]]
