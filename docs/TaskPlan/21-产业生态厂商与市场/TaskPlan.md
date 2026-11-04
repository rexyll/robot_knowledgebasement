# 21｜产业生态厂商与市场 — 章节任务计划

> 本文件统一继承仓库根目录 `TaskPlan.md` 的 Guide、Limit、状态和验收要求；本章不另设 Guide/Limit。特殊例外尚未获用户批准。
>
> 目标知识目录：`knowledge/ecosystem/`  
> 依赖章节：01–20；为选型、BOM、采购和路线规划提供情报  
> 现有基础：已有主要厂商、产业链与市场、发展趋势、标准法规和硬件厂商资源汇总  
> 初始状态：待执行；现有内容需按本计划逐项复核。

## 1. 本章目标与边界

建立机器人产业链、供应商、产品线、开源/学术生态和市场变化的代表性、可追溯资料库。

**覆盖范围：** 核心零部件供应链、机器人本体厂商、系统集成商、工业软件、芯片/传感器/执行器厂商、云平台、开源项目、研究机构、标准组织、专利和论文、市场规模、商业模式、应用渗透和技术趋势。

**边界说明：** 具体 BOM 报价由 18 章维护；精确硬件参数由对应硬件章节维护；法规条文由 20 章负责。

## 2. 交付物

- 机器人产业链地图
- 按领域和技术路线的代表厂商/产品线矩阵
- 开源生态与许可证索引
- 市场与技术趋势的时间快照报告

## 3. 任务节点

### 21-01｜产业链与价值链地图

- **任务范围：** 按核心材料、零部件、模组、本体、软件、集成、运营和服务拆解产业链。
- **必做：** 说明上下游关系、价值来源、关键技术依赖、供应集中度和地域差异。
- **严格禁止：** 不得将单一市场报告的口径当作行业统一事实；不得把宣传稿当作独立第三方研究。
- **依赖：** 先完成本章资产盘点；其余依赖按根计划第 6 章执行。
- **交付物与验收：** 产业链地图和术语定义有来源与统计口径。
- **状态：** 进行中（已用 IFR World Robotics 2026 核验工业机器人新增装机/在役存量，并更新专业服务机器人和物流应用数据；全产业链各环节价值/供应集中度与区域分布仍需原始统计/报告支持，已删除无口径 BOM 占比）

### 21-02｜代表厂商与产品线档案

- **任务范围：** 覆盖机器人本体、传感器、计算平台、执行器、运动控制、软件和云平台代表厂商。
- **必做：** 按技术路线/地区/产品线选代表样本，收录官网、手册、SDK、支持生命周期和代表型号。
- **严格禁止：** 不得无限枚举厂商；不得以广告排名或未验证榜单作为选型结论。
- **依赖：** 先完成本章资产盘点；其余依赖按根计划第 6 章执行。
- **交付物与验收：** 厂商档案有选择标准、来源和最后核验日期。
- **状态：** 进行中（已完成代表性硬件供应商入口及主要机器人本体厂商的 P1 定向审查，覆盖工业/协作、仓储 AMR/ACR、清洁和人形机器人，并区分官方产品目录、厂商自报量产、客户到场/案例与独立部署证据；仍需逐型号取得受控手册、SDK/固件、生命周期/PCN、地区供货和供应商书面资料，并补审国产协作机器人、无人叉车、服务/医疗及软件厂商；未完成供应商资格审查或采购选型）

### 21-03｜开源项目、论文与标准生态

- **任务范围：** 建立 ROS、仿真、SLAM、规划、控制、具身智能和工具链开源项目索引。
- **必做：** 记录上游仓库、维护状态、许可证、依赖、适用范围、引用论文和社区活跃度。
- **严格禁止：** 不得因 GitHub Star 数高就判断工程成熟；不得复制许可证不清的代码。
- **依赖：** 先完成本章资产盘点；其余依赖按根计划第 6 章执行。
- **交付物与验收：** 关键生态项目有许可证地图和维护风险说明。
- **状态：** 进行中（已新增代表性开源项目与工具链索引，扩展至 Ouster/Livox/RealSense/DepthAI 驱动、robot_localization、launch_testing、rosbag2、ros2_tracing、industrial_ci、micro-ROS、ROS 2 CANopen 和 open62541；另建立 Humble/Jazzy/Kilted/Lyrical 与 Gazebo/传感器驱动/测试/工业互操作兼容矩阵。本轮继续补充 MoveIt Servo 机械臂伺服、Velodyne 与 Hesai LiDAR 驱动，并将 VDA5050 Connector（仅 Galactic/2022 年更新）和 ROS-Industrial industrial_core（ROS 1/社区尽力维护）标为历史/维护风险；已扩展兼容矩阵。本轮继续补充 Basler pylon、Zivid、SICK 工业视觉/激光雷达驱动，IgH EtherLab 与 SOEM EtherCAT 主站实现，以及 Open-RMF rmf_fleet_adapter 和 VDA 5050 v3.0 协议；明确 SOEM v2.0.0 GPLv3/商业双许可、IgH GPL-2.0 与 EtherCAT 工业产权分开评估，记录 SICK 与 Open-RMF 包版本/总览文档不一致。本轮继续补充 Beremiz IEC 61131-3 PLC IDE/runtime、ethercat_driver_ros2（ros2_control Hardware Interface；Jazzy 分支与 Humble 安装步骤存在文档冲突）、industrial_calibration_ros2/industrial_calibration、camera_calibration、robot_calibration，并加入端到端集成关系图，区分相机内参、手眼外参、机器人/底盘几何参数和控制总线职责。仍未完成全依赖许可证/SBOM、PLC/ROS2 协议桥实际实现、更多视觉/现场总线项目筛查、OEM 车队适配、目标硬件构建/长稳测试和完整兼容性验收）

### 21-04｜市场数据与商业模式

- **任务范围：** 梳理出货、装机、收入、行业应用、单机成本、RaaS、服务化和系统集成模式。
- **必做：** 标明报告发布者、数据期间、地域、市场定义、币种和预测/实际口径。
- **严格禁止：** 不得把预测当成实际发生；不得将不同机构定义不同的 TAM/SAM 直接相加。
- **依赖：** 先完成本章资产盘点；其余依赖按根计划第 6 章执行。
- **交付物与验收：** 市场数据卡片可追溯原报告并注明局限。
- **状态：** 进行中（已用 IFR 2026 更新工业机器人、专业服务机器人、运输物流和全尺寸人形机器人 2025 年统计，并区分实际/预测、销量/存量/产能；中国 AGV/AMR 细分市场、收入/价格/RaaS 等仍待原始报告与统计口径）

### 21-05｜技术趋势与成熟度判断

- **任务范围：** 评估人形、具身智能、协作、移动操作、软体、群体机器人和新型传感/执行路线。
- **必做：** 区分论文、实验室原型、试点、商业部署和规模化量产证据。
- **严格禁止：** 不得把融资、发布会演示或单次视频当作规模化能力证据。
- **依赖：** 先完成本章资产盘点；其余依赖按根计划第 6 章执行。
- **交付物与验收：** 趋势分析有成熟度分级、证据和不确定性说明。
- **状态：** 进行中（已将发展趋势页改为统计和公司自报证据分级，移除无来源价格/份额、固定时间预测和“已经成为主流/已解决”等断言；其他算法/软件/传感器趋势仍需论文、产品实测和部署证据逐项补足）

### 21-06｜情报更新与失效审计

- **任务范围：** 维护厂商产品换代、停产、并购、开源许可证变化、标准组织和市场数据更新。
- **必做：** 建立周期/事件触发检查、历史版本和链接有效性记录。
- **严格禁止：** 不得静默覆盖旧产品资料或把已停产产品列为现役主推。
- **依赖：** 先完成本章资产盘点；其余依赖按根计划第 6 章执行。
- **交付物与验收：** 更新台账、过期标记和复核流程通过抽查。
- **状态：** 未开始（存量待审计）



## 4. 本章完成条件

1. 产业链和代表厂商按统一维度组织。
2. 市场数字和趋势判断能回到原始来源与统计口径。
3. 开源项目包含许可证、维护状态和工程风险信息。

## 5. 缺口与待确认事项

新发现的内容缺口以新 ID 追加在本文件末尾，并注明证据、影响和依赖。遇到本章无法遵循根目录 Guide/Limit 的特殊情形，必须先暂停并向用户说明冲突和拟议例外，取得确认后才可添加章节专属规则。

## 6. 本章执行记录（只追加）

| 日期 | 节点 | 记录与证据 |
| --- | --- | --- |
| 2026-11-03 | 21-01/21-02/21-04/21-05 | P1 定向核验产业链/市场、人形机器人和代表厂商：IFR 2026 工业机器人/专业服务机器人/人形机器人数据；Tesla Q3 2026 Optimus 生产状态；AGIBOT 5000 台工厂下线声明；UBTECH Walker S2 量产交付声明；Unitree G1/H2 与 Figure 03 产品资料。更新四篇知识页，来源台账 #175–#185；原报告不可得的市场份额、BOM 比例和其他厂商数据保持待审，不作独立排名/采购结论。 |

## 7. 补充节点（只追加）

> 后续新增节点使用本章未使用的新序号；不得删除、复用或静默重排既有 ID。


| 2026-11-04 | 21-02/21-06 | 对硬件厂商资源汇总开展首批官方入口/生命周期复核：覆盖 SLAMTEC、Livox、Hesai、RealSense、Orbbec、Stereolabs、Bosch、ADI、SICK、OMRON、Oriental Motor、Inovance、Harmonic Drive、Nabtesco、EVE、MiR、Hikrobot、NVIDIA、Rockchip、Raspberry Pi；发现 SICK S300 订购截止窗口、Orin 模组可供期限及 CM4/CM5 最低供货声明并记录日期；补充官方文档登录限制和下载入口差异。链接台账 #497–#520。节点仍进行中，未完成全型号资料归档、供应商资格评审、价格/交期确认或实机验证。 |


| 2026-11-04 | 21-02/21-05/21-06 | 对《主要厂商名录》开展 P1 公司产品线、产品生命周期线索、交易主体和商业化证据定向核验：补充 ABB、FANUC、KUKA、Yaskawa、Universal Robots 工业/协作产品线；Geek+、Quicktron、Hai Robotics、MiR、Hikrobot、ForwardX 仓储/移动机器人矩阵；Gaussian Robotics 与 Tennant 清洁产品入口；Tesla、Figure、Unitree、AGIBOT、UBTECH 人形/具身机器人状态。纠正 ABB–SoftBank 交易未在已检查页面确认交割、AGIBOT 15,000 台是公司机器人组合下线数而非人形机器人客户交付数、Figure 02/03 客户案例归属及 Tesla 生产线启动不等同交付；新增链接台账 #521–#540。节点继续进行中：仍有多家国产协作/服务机器人和核心供应商未逐型号审查，所有厂商自报量产/部署统计未独立审计。 |


| 2026-11-04 | 21-03/21-06 | 新增《开源项目与工具链》代表性生态索引：覆盖 ROS 2 Lyrical、Nav2、MoveIt 2、ros2_control、BehaviorTree.CPP、Open-RMF、Gazebo Jetty/Harmonic、Isaac Sim/Lab/ROS、slam_toolbox、RTAB-Map、KISS-ICP、Cartographer、evo、OMPL、PX4、ArduPilot、LeRobot 和 Isaac GR00T；逐项区分上游版本/ROS Index 包版本、稳定版/预发布、仓库/包/模型权重/数据集/资产许可证与维护状态。特别记录 Cartographer 上游不再积极维护、Nav2 多许可证、Isaac Sim 附加条款和 Omniverse Kit 再分发边界、PX4 RC 与稳定版区别。来源台账 #541–#562，生态 README 已更新。节点仍进行中：未生成全依赖 SBOM/法律意见，未在目标硬件完整构建/运行，也未完成算法/实时/安全实测。 |


| 2026-11-04 | 21-03/21-06 | 扩展开源生态索引，补充 Ouster、Livox、RealSense、Luxonis DepthAI 传感器驱动，robot_localization 状态估计，launch_testing/rosbag2/ros2_tracing/industrial_ci 测试与可观测性工具，micro-ROS、ROS 2 CANopen、open62541 工业互操作组件；新增《知识生态兼容矩阵》，按 Humble/Jazzy/Kilted/Lyrical 核对 Gazebo 官方配对、驱动支持、ROS Index 发布、源码构建线索和工程限制。记录 Livox Driver 2 不建议未经修改直接用于量产、ROS 2 CANopen 仍未生产就绪、DepthAI 在 Kilted 起更改包名、Zenbedded 示例的 Lyrical/Jazzy/Kilted 支持等级差异。来源台账 #563–#580。节点继续进行中：本轮仅静态资料核验，未在目标传感器、MCU、底盘、GPU 载板或飞控上构建/运行，也未生成完整 SBOM 或验证产品级实时/安全表现。 |

| 2026-11-04 | 21-03/21-06 | 继续扩展开源项目与兼容性证据：新增 MoveIt Servo（机械臂笛卡尔/关节伺服，区分 Humble 包页与 Jazzy/Kilted 稳定分支证据）、Velodyne ROS 2 Driver（Humble/Jazzy/Lyrical ROS Index 记录）和 Hesai LiDAR ROS 2（Humble/Jazzy/Lyrical 厂商源码构建路线）；将 VDA5050 Connector 限定为 Galactic/2022 年旧项目参考，并指出 ROS-Industrial industrial_core 为 ROS 1 历史包、社区尽力维护。扩展兼容矩阵与资产 CSV，链接台账 #581–#590。节点继续进行中：本轮仅上游/ROS Index 静态检查，未执行任何目标平台构建、设备接线、运动伺服、传感器实测、硬实时或功能安全验证；全依赖 SBOM、许可证审查和完整工业协议一致性测试仍未完成。 |

| 2026-11-04 | 21-03/21-06 | 补充工业视觉、现场总线和车队互操作生态：新增 Basler pylon ROS 2 Jazzy driver（厂商不提供该开源项目技术支持、BCD License）、Zivid ROS driver（SDK/driver release 文档版本边界差异、OpenCL GPU 依赖）、SICK sick_scan_xd（Humble ROS Index 已发布，Jazzy/Kilted 有上游发布流程，但版本字段不一致）；新增 IgH EtherCAT Master（stable-1.6、GPL-2.0，另有 EtherCAT 技术/商标权边界）与 SOEM v2.0.0（GPLv3/商业双许可、legacy API 移除）；扩展 Open-RMF fleet adapter（ROS Index Lyrical 2.14.0 与总览 README 发行版列表口径差异）和 VDA 5050 v3.0.0（自由导航路径/zone、MQTT/JSON、安全配置边界）。新增链接台账 #591–#607，更新开源索引、兼容矩阵及资产 CSV。节点继续进行中：本轮仅静态上游核验，未连接工业相机、SICK 雷达、EtherCAT 从站或 AMR 车队，也未做总线周期/实时性、VDA5050 一致性或现场任务互操作测试；未生成完整 SBOM/许可证法律意见。 |

| 2026-11-04 | 21-03/21-06 | 补充 PLC/ROS 2 运动控制接口及机器人标定生态：加入 Beremiz v1.6.0（IEC 61131-3/PLCopen XML；IDE/CLI、Python runtime、C++ runtime 按 GPLv2/LGPLv2.1/GPLv3 分组件审查；ERPC 默认未加密）、ethercat_driver_ros2（Apache-2.0、以 IgH 为基础的 ros2_control Hardware Interface；Jazzy 分支与 INSTALL.md 的 Ubuntu 22.04/Humble 步骤存在版本冲突）；加入 industrial_calibration core/ROS 2 wrapper（RGB、点云、TF、target finder、RViz 数据采集）、camera_calibration（单/双目内参）、robot_calibration（相机、关节偏置、底盘几何），并将 moveit_calibration 归类为 ROS 1 历史工具。新增端到端集成 Mermaid 图和阶段顺序/总线主站责任规则；来源链接台账 #608–#621。节点继续进行中：本轮仅静态资料与接口关系核验，未运行 PLC runtime、EtherCAT 主站/从站、ros2_control 硬件接口、相机/手眼标定或现场协议桥；无硬件实时性/功能安全/标定不确定度实测，未完成全依赖 SBOM 与许可证法律审查。 |
| 2026-11-04 | 21-03/21-06 | 补充 PLC/ROS 2 协议桥实现：新增 b-robotized/ros2_opc_ua（OPC UA Client 型 ros2_control SystemInterface，README 要求 Jazzy+，示例接口范围有限）、Capacites/ros2_modbus（MIT，Modbus TCP I/O 状态 topic，未声明完整 ROS distro 支持矩阵）及 Mariunil/ros2-opcua（open62541 PubSub hybrid node，列为实验性参考）。兼容矩阵区分 Jazzy+ 文档门槛、源码构建入口和未证实发行版支持；补充 ICD、NodeId/寄存器映射、质量位/时间戳、权限、超时/重连、幂等性、PLC/网络故障注入及抓包/rosbag 证据要求。来源链接台账 #622–#624。21-03 继续进行中：本轮仅静态仓库 README 核验，未连接 PLC、未执行 OPC UA/Modbus 互操作、证书/身份验证、网络分区/重连或现场安全测试；全依赖 SBOM 与许可证法律审查未完成。 |
