# 机器人知识库 | Knowledge Vault

本目录是仓库的知识内容主入口。原 `local` 分支中的 Obsidian 知识笔记已按主题迁移到下列板块；原文标题、正文和 Obsidian 双链尽可能保留。已有 `main` 内容不覆盖，新增内容作为补充归档。

## 核心知识板块

| 板块 | 路径 | 内容 |
| --- | --- | --- |
| 机器人分类 | [robots/](robots/) | 工业、移动、仓储、清洁、服务、人形、特种、医疗等机器人类型 |
| 传感器 | [sensors/](sensors/) | LiDAR、相机、IMU、毫米波、超声波、编码器、传感器参数与校验 |
| 执行器 | [actuators/](actuators/) | 电机、驱动器、减速器及执行机构 |
| 导航 | [navigation/](navigation/) | 定位、导航实践与里程计标定 |
| 操作 | [manipulation/](manipulation/) | 运动操作、抓取与末端执行器知识（后续扩展） |
| 故障排查 | [troubleshooting/](troubleshooting/) | 故障现象、诊断、恢复与验证（后续扩展） |

## 新增知识板块

| 板块 | 路径 | 新增原因与内容 |
| --- | --- | --- |
| 机械与底盘 | [mechanics/](mechanics/) | 底盘、运动机构、机械结构和材料选型 |
| 电源与能源 | [power/](power/) | 电池、电源系统、充电桩与自动回充 |
| 功能安全 | [safety/](safety/) | 安全防护器件、功能安全体系 |
| 计算平台 | [computing/](computing/) | SoC、MCU、工控机和机器人计算平台 |
| 软件系统 | [software/](software/) | ROS/ROS 2、Nav2、仿真、RMS、云端、实时系统、DDS 与 ROS 迁移 |
| 算法 | [algorithms/](algorithms/) | SLAM、融合定位、规划、避障、控制、视觉感知、学习与多机协同 |
| 系统架构与流程 | [architecture/](architecture/) | AMR 总体架构、建图、导航、调度、OTA 和安全流程 |
| 核心参数 | [parameters/](parameters/) | 传感器、底盘、系统性能指标及对比 |
| 产业与生态 | [ecosystem/](ecosystem/) | 厂商、产业链、标准法规和行业趋势 |
| 项目案例 | [projects/](projects/) | AMR、清洁机器人、视觉框架项目梳理 |
| 从零搭建指南 | [getting-started/](getting-started/) | 从需求定义、机械、电气到软件、算法、联调和学习路径 |
| 代码实例 | [examples/](examples/) | 可运行代码示例、代码来源与许可证信息 |
| 知识地图 | [maps/](maps/) | 首页、分类地图、硬件/软件/算法/流程地图 |

## 快速入口

- [知识地图索引](maps/README.md)
- [首页](maps/首页.md)
- [术语表](术语表.md)
- [知识库编写规范](../docs/编写规范.md)
- [知识 Schema](../docs/knowledge-schema.md)
- [任务规划与历史记录](../docs/TaskPlan.md)
- [来源链接台账](../docs/链接台账.md)
- [分支迁移映射](../docs/migration-map.md)

## 分类原则

1. 以 `main` 现有目录为基线，保留 robots、sensors、actuators、navigation、manipulation、troubleshooting 六类。
2. 当原始知识具有独立主题边界、跨多篇文档且无法合理归入既有板块时，新建一级知识板块。
3. 地图/MOC、术语、编写规范、任务台账与来源台账属于知识库治理资料，不混入技术主题正文。
4. 原始文档内容优先保留；只在索引、元数据、分类和必要的重复内容整合处做编辑。
5. `data/raw/` 用于原始导入，`data/processed/` 和 `data/embeddings/` 用于生成数据，均不作为知识正文目录。
