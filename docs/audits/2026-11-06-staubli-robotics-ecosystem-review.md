# Stäubli Robotics 软件与 ROS 生态静态审查（2026-11-06）

> 审查范围：Stäubli 官方 CS9/VAL 3/uniVAL 资料、ICube ROS 2 Jazzy 驱动、ROS-Industrial VAL3 历史驱动及 ROS Index 元数据。  
> 审查类型：公开资料与公开仓库静态审查；不是产品选型结论、供应商资格审查或工程验收。  
> 对应任务：根任务 00-01；第 21 章 21-02。  
> 来源：链接台账 #1413–#1420。

## 1. 控制器与产品接口

- Stäubli 官方 CS9 页面列出 CS9 SE/LP/MP/HP 形态，并按控制器规格列出适配机器人产品线；本轮可见产品映射包含 TS2-40/60/80/100、TX2-40/60/L/90/L/XL/140/160/L/200/L。不得仅凭“CS9”系列名推定任一具体机械臂、控制柜尺寸、固件或选件组合兼容。采购前须冻结完整机器人型号、控制器完整订货号/硬件版本、软件版本和地区配置。来源#1413。
- CS9 官方页面列出标准接口及可选通信配置：EtherCAT、EtherCAT FSoE、EtherNet/IP、PROFINET、Sercos III、POWERLINK、Modbus 等；OPC UA Server及部分主站/扫描器角色属于可选项。协议名称出现于目录不等于目标控制器已购买、启用或通过互操作验证；须核对选件、设备角色、固件和PLC端配置。来源#1413。
- CS9 产品页公开列出模块化安全功能可能性，包括 Safe speed、Safe stop、Safe tool、Safe zone，并列出SP2/SP2+手持单元的三位置使能器和急停。页面未提供目标SKU证书、参数、固件/安全模块适用矩阵或整机风险评估结果；不得把控制器功能名称当作整机PL/SIL结论。来源#1413。
- VAL 3 是控制器侧专用机器人编程语言/环境，官方说明其支持机器人功能、DIO/AIO和现场总线连接。它与外部PC SDK、ROS 2 HardwareInterface、PLC功能块不是同一层接口。来源#1414。

## 2. 官方控制路线：uniVAL plc 与 uniVAL drive

- uniVAL plc：官方描述为在工业PLC侧安装功能块库（client），机器人侧运行server，通过标准现场总线交换；轨迹可在Stäubli示教器上示教并由机器人侧数据库保存/管理。该路线是PLC通过功能块驱动机器人，不应误写成ROS驱动或通用实时关节伺服API。来源#1415。
- uniVAL drive：官方描述为使用通用工业多轴控制器控制Stäubli四轴/六轴机器人，采用EtherCAT、POWERLINK、PROFINET、Sercos等实时现场总线/drive profile；页面列出Sercos drive profile与CANopen CiA 402，并宣称uniVAL drive实现ISO 13849 Cat.3/PL d安全功能。该等级目前只作为厂商公开声明记录；在取得具体版本证书、适用型号、配置/集成手册及验证条件前，不将其外推为整机或应用安全等级。来源#1416。
- uniVAL plc 与 uniVAL drive 的主控责任、轨迹执行方式、现场总线角色和安全责任不同。必须依据项目选型确定唯一运动控制权威，禁止让PLC、ROS 2和外部多轴控制器同时对同一运动轴拥有未仲裁的命令写入权。

## 3. ROS 2 Jazzy 驱动（ICube-Robotics）

### 3.1 项目状态与兼容范围

- ICube-Robotics/staubli_driver_ros2 使用ros2_control，公开README声明当前开发基于ROS 2 Jazzy / Ubuntu 24.04 LTS，面向CS9控制器，不支持旧代控制器；截至该README快照只实现position控制，velocity和hand-guiding及diagnostics被列为后续工作。仓库当前页面显示main分支、71 commits、Apache-2.0 License，但GitHub Releases区没有列出正式Release对象。来源#1417–#1418。
- README明确声明：该驱动仍处于开发状态；项目因资金中断，在2025年11月初始POC后曾暂停主动开发；页面称计划于2026年恢复，但本次静态检查未找到可据以确认恢复、正式发布或工业化验收的证据。因此不得把“预计恢复”改写为“已恢复”，也不得将项目标注为Stäubli官方支持的生产级驱动。来源#1417。
- 文档站当前标识版本0.1.4，但这只是文档版本快照，不代表GitHub正式Release、软件包发行或厂商认证。来源#1418。

### 3.2 软件分层与接口语义

- 文档将软件分为文档meta-package、主驱动包（ROS 2 Hardware Interface + 控制器侧VAL3程序）、机器人描述（URDF/Xacro）、MoveIt 2配置和bringup。控制器侧VAL3 server与ROS 2侧Hardware Interface构成客户端/服务端结构。来源#1418。
- State interface包含position、velocity、effort；文档明确effort由电流估算而非直接测量。Supervision状态包含operation mode/status、safety status、控制序列延迟周期数、制动器释放、motion_possible、in_motion、in_error、estop_pressed和wait_for_ack。状态字段可用于监控/联锁逻辑设计，但不自动构成功能安全认证通道。来源#1418。
- 当前可用joint command interface为position；velocity接口虽在接口列表中出现，但文档标注尚未实现，Hardware会拒绝velocity控制模式。acceleration接口是Joint Limiter参数的副产物，不是可执行命令模式，尝试使用会被拒绝。不得仅依据ros2_control introspection显示接口就宣称该模式可用。来源#1418–#1419。
- 文档列出机器人侧control_port默认11000、diagnostic_port默认11001，ROS侧local_control_port/local_diagnostic_port也默认11000/11001；必须检查端口绑定、主机网络、安全域和防火墙，避免与旧驱动或其他服务冲突。来源#1418。
- Mock hardware默认启用，不发UDP包，状态由最近一次命令计算，不能反映真实机器人动力学；mock bringup通过只证明软件安装/控制器逻辑的局部可运行，不证明真实控制器连接、机器人动力学、通信时序或安全状态。来源#1419。

### 3.3 安全与恢复边界

- 上游README要求先在MANUAL模式测试；切换AUTO后保持监督并让急停可触及；MoveIt测试使用很低的速度/加速度缩放并先在RViz检查预期运动。这些是项目维护者给出的测试警示，不是安全认证或现场风险评估。来源#1417。
- 必须进一步核验VAL3 server的命令许可/模式检查、E-stop/SS1/SS2与Safety Restart确认流程、通信丢失时机器人侧行为、命令超时/残留、制动器状态、急停/防护门恢复和人工确认。普通ROS topic/service及Supervision状态不得作为唯一安全链。
- 不允许在无人监督的真实机器人上直接运行来自mock或仿真环境的轨迹；任何自动重启/重新激活必须由外部安全系统状态、操作者授权和独立风险控制策略共同约束。

## 4. ROS-Industrial 历史VAL3驱动（ROS 1）

- ros-industrial/staubli_val3_driver是VAL3侧simple_message服务器，与industrial_robot_client配套，向ROS 1暴露FollowJointTrajectory action；GitHub README称兼容CS8/CS9，但这不代表ROS 2支持。来源#1420。
- ROS Index当前元数据只显示Indigo发行版、版本0.1.0、CATKIN、UNRELEASED，仓库last updated为2018-04-06；ROS Index中的发行版记录和仓库README的CS8/CS9描述需并列保留，不能将Indigo包条目当作Humble/Jazzy支持。来源#1421。
- ROS Index说明旧实现使用VAL3 s7.7.2及以上（依赖sioGet返回值），需要配置Motion TCP 11000与Feedback TCP 11002；手动/自动模式下还涉及人工电机使能和Move按钮/保持动作。该驱动的控制器侧VAL3应用与ROS 1客户端不应与ICube ROS 2驱动的端口、诊断接口和软件版本混用。来源#1421。
- 两个公开仓库都声明Apache-2.0，但许可证声明不代表第三方依赖/VAL3制品/控制器SDK已完成完整SBOM或法律审查；本项目仅链接，不复制代码。来源#1417、#1420。

## 5. 版本/兼容性结论

| 路线 | 控制器 | ROS/运行环境 | 当前可确认能力 | 证据等级/限制 |
|---|---|---|---|---|
| ICube ROS 2 driver | CS9 | ROS 2 Jazzy / Ubuntu 24.04 | position命令；mock与真实连接bringup文档 | 上游明确为prototype；无正式Release对象；未实机验证 |
| ROS-Industrial VAL3 | CS8/CS9（README）；ROS Index历史包偏CS8测试 | ROS 1 Indigo历史包 | simple_message / FollowJointTrajectory | 旧版历史路线；ROS Index最后更新2018-04-06；不是ROS 2 |
| uniVAL plc | CS8/CS9代际（厂商声明） | PLC + 厂商功能块/现场总线 | PLC侧功能块与机器人侧server | 选件、PLC厂商库、协议和SKU需逐项确认 |
| uniVAL drive | Stäubli四轴/六轴机器人范围（厂商声明） | 外部多轴控制器 + 实时现场总线 | drive profile / 外部全关节控制 | Cat.3/PL d为厂商页面声明，须取得证书与集成条件 |

## 6. 工程准入与待补证

1. 冻结目标机器人准确型号、轴数、CS9 SE/LP/MP/HP完整订货号、硬件修订、控制器软件/固件、VAL3版本、SP2/SP2+型号及地区。
2. 获取CS9受控操作/维护/安全手册、机器人型号—控制器矩阵、VAL3语言参考、uniVAL plc/drive选件订货号、PLC功能块/现场总线手册、选件许可和EOL/备件支持承诺。
3. 对ICube ROS 2仓库固定commit、依赖版本、包版本和完整许可证清单；核验后续恢复开发的commit/Release/CI证据，构建Jazzy工作区并记录编译器、ros2_control、MoveIt、VAL3 server和机器人描述版本。
4. 逐型号核对URDF/Xacro、关节方向/零位、软硬限位、负载/惯量、速度/加速度/jerk约束、工具坐标与基坐标；校验位置/速度/effort估算与实测反馈差异。
5. 对真实CS9测量control/diagnostic通信周期、控制序列延迟、抖动、WCET、网络丢包、断线恢复、命令队列/残留、急停/安全停止、Safety Restart确认和多客户端连接行为。
6. 在受控实验室执行mock→SRS/虚拟控制器（如适用）→HIL→真实机器人分阶段验证；再执行FAT/SAT、现场节拍/重复精度/负载热稳定性及安全验证。
7. 取得uniVAL drive具体版本的Cat.3/PL d证书、适用型号和集成手册；按整机风险评估验证外围安全回路、停止时间/距离和故障响应。
8. 评估旧ROS 1驱动迁移路径，不允许把ROS Index历史发行版支持描述为现代ROS 2支持。

## 7. 本轮未执行事项

未下载/安装Stäubli Robotics Suite、VAL3开发环境或商业选件；未构建ICube ROS 2工作区；未运行mock或SRS仿真；未连接真实CS9、机器人、PLC或安全回路；未测量实时性、轨迹误差、节拍、故障恢复或安全功能；未取得证书原件、受控兼容矩阵或地区供货/生命周期书面资料。因此Stäubli档案仅完成公开资料静态审查，工程验收和供应商资格仍未完成。
