# 机器人知识库 | Knowledge Vault

本目录是仓库的知识内容主入口。原 local 分支中的 Obsidian 知识笔记已按主题迁移到下列板块；原文标题、正文和 Obsidian 双链尽可能保留。已有 main 内容不覆盖，新增内容作为补充归档。

## 当前已有知识板块

| 板块 | 路径 | 内容 |
| --- | --- | --- |
| 机器人分类 | [robots/](robots/) | 工业、移动、仓储、清洁、服务、人形、特种、医疗等机器人类型 |
| 传感器 | [sensors/](sensors/) | LiDAR、相机、IMU、毫米波、超声波、编码器、传感器参数与校验 |
| 执行器 | [actuators/](actuators/) | 电机、驱动器、减速器及执行机构 |
| 导航 | [navigation/](navigation/) | 定位、导航实践与里程计标定 |
| 操作 | [manipulation/](manipulation/) | 运动操作、抓取与末端执行器（当前主要是目录占位） |
| 故障排查 | [troubleshooting/](troubleshooting/) | 故障现象、诊断、恢复与验证（当前主要是目录占位） |
| 机械与底盘 | [mechanics/](mechanics/) | 底盘、运动机构、机械结构和材料选型 |
| 电源与能源 | [power/](power/) | 电池、电源系统、充电桩与自动回充 |
| 功能安全 | [safety/](safety/) | 安全防护器件、功能安全体系 |
| 计算平台 | [computing/](computing/) | SoC、MCU、工控机和机器人计算平台 |
| 软件系统 | [software/](software/) | ROS/ROS 2、Nav2、仿真、RMS、云端、实时系统、DDS 与 ROS 迁移 |
| 算法 | [algorithms/](algorithms/) | SLAM、融合定位、规划、避障、控制、视觉感知、学习与多机协同 |
| 系统架构与流程 | [architecture/](architecture/) | AMR 总体架构、建图、导航、调度、OTA 和安全流程 |
| 核心参数 | [parameters/](parameters/) | 传感器、底盘、系统性能指标及对比 |
| 产业与生态 | [ecosystem/](ecosystem/) | 厂商、产业链、标准法规和行业趋势 |
| 项目案例 | [projects/](projects/) | AMR、清洁机器人、视觉框架项目梳理（公开前仍需披露审查） |
| 从零搭建指南 | [getting-started/](getting-started/) | 零基础学习、AMR 教学样机和从零到量产主线 |
| 代码实例 | [examples/](examples/) | 可运行代码示例、代码来源与许可证信息 |
| 知识地图 | [maps/](maps/) | 首页、分类地图、硬件/软件/算法/流程地图 |

## 计划建设、尚未形成实质内容的领域

以下目录是全行业 TaskPlan 的目标分类，不代表目录或内容已经存在。先在相邻现有板块中整理存量，再按 00-02 的分类边界逐步建立。

| 领域 | 目标路径 | 主要内容 |
| --- | --- | --- |
| 系统工程 | system-engineering/ | 产品定义、需求工程、系统架构、接口与追踪 |
| 电子电气 | electronics/ | 电路、PCB、线束、EMC/ESD、电源分配 |
| 嵌入式 | embedded/ | Bootloader、BSP、HAL、固件、设备驱动 |
| 通信网络 | networking/ | 工业总线、网络拓扑、无线、时间同步、中间件 |
| 上层应用 | applications/ | HMI、业务工作流、人机交互和行业系统集成 |
| 云平台 | cloud/ | 设备身份、遥测、OTA、云边协同和远程运维 |
| 车队管理 | fleet-management/ | RMS/FMS、任务分配、交通管制、车队运营 |
| BOM 与供应链 | bom/ | EBOM/MBOM/SBOM、采购、替代料、成本和 EOL |
| 测试验证 | validation/ | DVP&R、SIL/HIL、可靠性、产测和验收 |
| 标准法规 | standards/ | 规范、法规、认证路径和合规证据 |
| 数据与 AI | data-ai/ | 数据工程、训练评测、Sim2Real、VLA 与具身智能 |
| 制造与运营 | operations/ | NPI、工艺、质量、量产、交付、售后与退役 |

## 快速入口

- [零基础学习路径](getting-started/00-零基础学习路径.md)
- [从零到量产端到端路线](getting-started/端到端产品化路线总览.md)
- [知识地图索引](maps/README.md)
- [首页](maps/首页.md)
- [术语表](术语表.md)
- [知识库编写规范](../docs/编写规范.md)
- [工程与知识文档模板](../docs/templates/README.md)
- [审计与资产清单](../docs/audits/README.md)
- [知识 Schema](../docs/knowledge-schema.md)
- [根 TaskPlan](../TaskPlan.md) · [章节 TaskPlan 索引](../docs/TaskPlan/README.md)
- [来源链接台账](../docs/链接台账.md)
- [分支迁移映射](../docs/migration-map.md) · [旧版 TaskPlan 归档](../docs/TaskPlan/archive/local-v2-history.md)

## 分类原则

1. 以 main 现有目录为基线，保留已有主题与文件名，避免破坏 Obsidian 双链。
2. 每个知识主题设置唯一正文主归属；跨领域内容通过链接建立关系，避免平行正文。
3. 地图/MOC、术语、编写规范、任务台账与来源台账属于治理资料，不混入技术主题正文。
4. 原始文档内容优先保留；内容修订要记录理由、来源和日期，不能将未经审计的内容标记为完成。
5. 计划中的目录在建立实质内容和分类入口之前，只记录为缺口，不作为知识覆盖成果。
