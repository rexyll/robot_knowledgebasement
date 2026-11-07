# Stäubli Robotics 软件与 ROS 生态静态审查（2026-11-06）

> 审查范围：Stäubli 官方 CS9/VAL 3/uniVAL 资料、ICube ROS 2 Jazzy 驱动、ROS-Industrial VAL3 历史驱动及 ROS Index 元数据。  
> 审查类型：公开资料与公开仓库静态审查；不是产品选型结论、供应商资格审查或工程验收。  
> 对应任务：根任务 00-01；第 21 章 21-02。  
> 来源：链接台账 #1413–#1421、#1481–#1545。

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

- ICube-Robotics/staubli_driver_ros2 使用ros2_control，公开README声明基于ROS 2 Jazzy / Ubuntu 24.04 LTS、面向CS9控制器，不支持旧代控制器；其已公开能力仍以joint position命令为主，velocity、hand-guiding和diagnostics列为后续工作。更正本报告初始版本的遗漏：GitHub Releases 实际列有 0.1.3（prerelease）及 0.1.4（非预发布）两个 Release 对象；0.1.4 于2026-06-09发布。这里的“正式”仅指GitHub非预发布Release对象，不代表Stäubli官方发布、ROS发行版二进制包或产品认证。来源#1483–#1484。
- README明确声明该驱动仍为prototype；项目因资金中断，在2025年11月初始POC后曾暂停主动开发，页面曾称计划于2026年恢复。0.1.4之后至当前main HEAD（bd658e2d266e315d2ee35f985fb352ea88306b79，2026-07-03）仅见两次CI依赖更新，未见驱动功能提交；因此截至本次检查，仍无证据证明其已恢复持续功能开发或完成工业化验收。不得将项目标注为Stäubli官方支持的生产级驱动。来源#1417、#1485。
- 文档站标识版本0.1.4，与GitHub非预发布Release 0.1.4同号；但版本标识本身不能证明具体安装介质、目标控制器固件适配或Stäubli厂商认证。来源#1418、#1483–#1484。

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
| ICube ROS 2 driver | CS9 | ROS 2 Jazzy / Ubuntu 24.04 | 0.1.4 GitHub非预发布Release；position命令；mock与真实连接bringup文档 | Prototype；0.1.4之后main仅有CI依赖更新；velocity/hand-guiding/diagnostics未完成；未实机验证 |
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

## 8. Stäubli官方软件工程工具：Robotics Suite 与 VAL Blocks

- **Stäubli Robotics Suite（SRS）**是Windows PC端工程工具，面向机器人单元布局、机器人/工具/工件三维配置、碰撞检查、节拍估算及项目生命周期数据。官方页面区分Demo、Development、Maintenance和Optimize能力：Demo不能保存项目或导入3D对象；完整开发/仿真由Development Studio解锁，Maintenance Studio远程维护能力依赖Development Studio，Optimize Studio记录分析能力也依赖Development Studio。许可可采用本机或网络USB dongle。不能把Demo演示能力当作完整仿真验收。来源#1481。
- SRS官方页面公开提示有新版本，但本轮未取得可核验的具体数字版本号、安装包校验值或版本化发行说明；不得自行补写版本号。也未安装SRS或验证其模型/控制器版本兼容性。来源#1481。
- **VAL Blocks**是CS9机器人侧的图形化/积木式程序编辑能力，可与VAL3程序共存并支持自定义功能块。官方前置条件为CS9控制器软件不低于8.20、机器人上有效VAL Blocks许可证及SP2+示教器；相关演示可在SRS中体验。对输送带跟踪、主动柔顺等实时轨迹变化，Stäubli公开说明建议优先采用VAL3而非VAL Blocks。该能力不是ROS SDK，也不等于通用PC实时伺服接口。来源#1482。
- ICube仓库中的VAL3应用README另要求CS9及VAL3 8.x.x或以上，测试记录为TX2-60L；依赖motion、velocity addons，并使用alter、advCtrlFunctions。若后两项许可证处于demo模式，README提示应用运行2小时后停止；安装说明要求将addon库复制到控制器/usr/app，部署userapp和sio.cfx网络配置并在示教器启动。上述是该社区项目自己的部署说明，不代表Stäubli官方对该ROS驱动提供支持；应在目标机器人/许可证上逐项确认。来源#1492。

## 9. ICube ROS 2驱动源码静态审查（main快照）

> 本节仅为源代码阅读结果；没有运行故障注入，也没有证明下列路径已在真实控制器上触发。将“源码语义/待验证风险”与“已复现缺陷”严格区分。

### 9.1 UDP传输与协议校验

- **发送缓冲区满时可能丢弃命令但向上层报告成功。** udp_socket_impl.hpp使用MSG_DONTWAIT发送；当返回would_block时记录“Packet dropped”，但不返回失败，而是继续返回true。同一函数中的TODO也提出增加丢包计数及阈值错误；因此该丢包可沿send_message/send_robot_command传播为成功语义，硬件接口有可能继续返回OK。这是一条明确的源码语义风险，尚未通过人为填满内核发送缓冲区复现。来源#1488。
- **接收端未校验数据报发送方。** 同文件handle_data_received()保留TODO，明确指出应在处理前校验sender endpoint，防止非预期主机注入state数据或干扰sequence tracking；当前回调仍会处理收到的数据报。部署上应把机器人控制/诊断网络隔离并配置ACL；在修复并测试来源校验前，不应将控制UDP暴露到不受信任或可路由网络。此项为静态网络面风险，不等于已完成可利用性验证。来源#1488。
- FrameHeader::deserialize()检查magic number；RobotStateMessage::deserialize()对固定大小buffer反序列化，但“Validate header fields”处没有实际校验逻辑；当前可见代码没有在该路径校验声明的payload长度。RobotDriver::read_robot_state()随后检查message type和staleness；协议版本只在首次connect时检查，而非每个状态包重复校验。建议逐包验证sender、message type、protocol version、payload length、序列新旧关系及数值有限性，并为错误包建立独立计数/降级策略。来源#1488。
- 与之相比，VAL3端decodeRobotCommandMsg.pgx检查总长度、magic number、protocol version和message type，并在解码失败时把命令类型设为STOP；但通信读取、超时和状态处理仍有其他未完成项。来源#1489、#1493。

### 9.2 控制循环、通信失效与安全状态

- VAL3 start.pgx配置4 ms同步任务周期（250 Hz名义周期），并在监视速度低于100%时提示控制算法可能不能正常工作；这不是已测得的实际控制周期、最坏执行时间或抖动保证。controlTask.pgx检查task overrun并累计nOverruns，但本轮没有运行目标控制器测量。来源#1489、#1493。
- 控制循环按命令序列延迟做门控：机器人运动时延迟超过5个周期触发STOP/error；静止时超过25个周期触发STOP/error。它还要求不同控制模式切换前经过STOP，并在故障时stopMove()、resetMotion()和重置通信socket。不能把这些机制描述成“完全没有丢包/超时处理”。但同一文件对“没有新命令时旧命令的staleness检查”（elseIf分支）、额外staleness/lost-packet规则，以及故障复位后等待时间仍留有TODO；阈值是否足以覆盖所有控制器状态/网络故障，需要实测和故障注入。来源#1489、#1493。
- controlTask.pgx把运动中非预期移动、E-stop警告和runtime errors的硬停检查留作TODO；VAL3循环里的数字/模拟输出写入也留有TODO。因此即使ROS硬件接口导出了数字/模拟输出命令，不能据此认为控制器端I/O命令链已完成。来源#1489、#1493。
- updateState.pgx独立读取working mode/status及safety_status，但motion_possible当前表达式为isPowered() && !isEStopped，另一个包含robot status条件的表达式被注释。ROS perform_command_mode_switch()对operation_mode_status != 0只发HOLD警告；不能把这个软件字段视为安全额定联锁或完整的MANUAL/AUTO/REMOTE许可条件。现场仍必须由独立安全回路和风险评估约束运动授权。该发现属于模式/状态门控审查项，不在静态检查中认定为安全违规。来源#1490。
- updateJointPositionControl.pgx检查motion_possible、命令有效性和isInRange()关节范围；但目标与当前关节位置距离检查仍是TODO。ROS主机侧send_robot_command()对位置/速度上下限检查留有TODO，硬件写入路径只显式检查NaN；须在控制器限制之外建立主机侧配置限位、finite数值和边界测试。来源#1488、#1490。
- updateJointVelocityControl.pgx虽有模式分支与状态检查，但$setVelCmd仍为注释占位，日志明确称not yet implemented，函数返回error；ROS prepare_command_mode_switch()也拒绝velocity模式。不能将velocity state interface或VAL3速度控制函数文件的存在写成可用速度控制。来源#1490。
- VAL3状态里的joint velocity来自$getJntSpeedCmd，属于命令/速度估计路径；joint torque由getJointForce()基于电机电流估算，源文件明确说明只提供大致量级、并非外力/外部扭矩的准确测量且没有精度承诺。F/T传感器状态未实现，digital/analog input有效标志为false。来源#1490。

### 9.3 诊断兼容性与接口语义

- RobotDriver::connect()在等待首次有效报文时将diag_interface_ready直接置为true，旁边标注diagnostic data reading待实现；controller type检查被注释掉，VAL3版本适配检查仍是TODO。虽然类中存在read_diagnostic_data()，但当前connect路径没有用它验证实际CS9型号/固件/VAL3兼容性。不能仅凭默认目标CS9配置视为已完成型号确认。来源#1488。
- StaubliHardwareInterface导出position、velocity以及acceleration相关接口；但command-mode switch拒绝velocity和effort，acceleration接口仅用于JointLimiter参数。位置控制才是当前明确支持的关节命令模式。来源#1490。
- 对effort不能简单写成“可用力控/力矩反馈”；现有值是电流估算的粗略状态，且ROS接口没有据此实现effort命令模式。来源#1418、#1490。

### 9.3.1 DoF与命令数值边界（新增）

- StaubliHardwareInterface::on_init()仅检查URDF关节数不为0，没有将关节数限制为协议实现的6轴；HardwareInterface写入命令时，位置/速度填充循环使用num_joints_且以i<6截断，但随后NaN检查循环仅使用i<num_joints_，直接索引固定6元素的command_reference。**若URDF配置超过6个关节，存在越界访问/未定义行为的静态路径**；少于6轴时协议剩余轴默认保持零，也必须确认是否允许。推荐在初始化阶段明确要求与目标机器人一致的轴数（当前VAL3消息及位置控制为6轴），或实现经过验证的可变DoF消息协议。来源#1494。
- 写命令仅调用std::isnan()；正负Inf不会被该检查拒绝。应对每个活动关节命令及controller_period/模拟输出等数值字段执行isfinite与范围校验，并对NaN、+Inf、-Inf、极大有限值添加拒绝测试。此为输入校验缺口，不代表本轮已观察到机器人执行异常。来源#1494。
- test_staubli_hardware_interface.cpp当前可见测试覆盖Construction、Initialization、空配置失败、mock Configuration、PluginLoading、InterfaceExport及LifecycleTransitions；测试夹具/生命周期用例采用6个关节。未发现>6轴、0轴以外轴数限制、NaN/Inf、command_reference越界和固定协议轴数不匹配的回归测试。来源#1495。

### 9.3.2 UDP序号回绕、乱序与重复帧（新增）

- **16位回绕丢包计数存在+1偏差：** protocol.hpp将MAX_FRAME_SEQUENCE_NUMBER定义为uint16_t最大值65535；VAL3 getNextSequenceNumber.pgx在序号大于65535时回到0。C++ subscriber在新序号小于上一序号时计算lost=(65535-last)+current+1。因此正常无丢包的65535→0会报告lost_packages=1；65534→0也会比实际丢包数多1。应先定义模65536的前向差值，再以delta-1计算丢包。来源#1496–#1497、#1500。
- **任意下降序号被当成回绕并接受：** read_message()没有半区间/窗口判定；只要新序号小于last_read_sequence_number_，就按wrap分支计算丢包，并最终把last_read_sequence_number_更新为这个较小值。旧UDP包、乱序包或意外回退的流可能被接受为当前状态，并使比较基准回退；当前代码没有丢弃旧包的分支。该风险与VAL3在应用错误复位时把序号重置为0的行为还需区分：真正的新会话/复位应有明确重同步语义，不能将所有回退都默认当作自然回绕。来源#1496、#1500。
- **重复帧仍可刷新staleness：** update_message()每次成功反序列化都会重新写入本地reception_timestamp；read_message()发现相同序号时将status.new_message设为false，但仍返回true。RobotDriver::read_robot_state()只检查read_message()返回值、消息类型和time_since_received，不检查status.new_message；lost_packages处理也仅保留注释。重复/重放数据报因此可能刷新接收时间戳，却不带来新的状态序号，削弱单纯按接收时间判断状态新鲜度的有效性。来源#1496、#1498。
- **测试覆盖不足：** 当前LostPackageDetection只测试序号7→9的普通递增丢包及连续未读取包，不包含65535→0回绕、回绕时的丢包数、重复序号、乱序旧包和重复帧持续刷新接收时间的场景。来源#1499。
- **建议算法与验证：** 定义uint16序号模65536差值delta=(uint16_t)(new_seq-last_seq)：delta==0为重复；在协议规定的前向窗口内（例如0<delta<32768）视作新数据，lost=delta-1；超出窗口的逆向数据按旧包/乱序处理并丢弃，不更新last_seq和last_valid_timestamp。若控制器错误复位导致序号清零，应通过重连/显式会话重置或epoch标识同步，不得伪装成自然回绕。新增测试覆盖正常回绕、跨回绕丢包、重复、乱序、序号复位及重复帧洪泛下的watchdog行为。

### 9.3.3 VAL3状态帧Header的payload_size编码缺陷（高优先级）

- initRobotStateMsg.pgx把状态报文nPayloadSize设为124，并将序列化缓冲区分配为nHeaderSize+nPayloadSize=8+124=132字节；C++ RobotStateMessage::message_size()同样返回132字节（payload 124字节）。来源#1502、#1486。
- 但是encodeHeader.pgx在写完2字节nMsgSequenceNumber后，最后2字节再次调用toBinary(x_header.nMsgSequenceNumber, 2, "2l", ...)，没有写入x_header.nPayloadSize。decodeHeader.pgx在相同偏移将2字节解码到nPayloadSize，MessageHeader.dtx定义了这一字段，且C++ FrameHeader也将该位置作为payload_size。因此该位置正是payload_size字段。encodeRobotStateMsg.pgx是仓库内检索到的唯一encodeHeader调用点，调用前只验证缓冲区长度，不会修正错误字段。来源#1501–#1503、#1505–#1506。
- 因此VAL3发出的RobotState UDP帧，其真实payload仍为124字节，但头部payload_size被序号替代；除序号偶然等于124外，头部字段与实际长度不一致。当前C++ RobotState反序列化只检查最小缓冲区长度，header字段验证处留空，因而本驱动可能继续接受该错误帧；严格校验payload_size的第三方客户端或未来修复后的C++解析器则可能拒绝。此为代码静态证据，不代表本轮已连接CS9抓到线上数据。来源#1501–#1503、#1486。
- 当前test_message_serialization.cpp验证的是C++ FrameHeader/RobotStateMessage自身序列化再由同一套C++代码反序列化；没有看到VAL3生成状态帧的黄金字节样本、C++读取VAL3 fixture或跨语言双向互操作测试。因此现有C++ round-trip不能覆盖这条缺陷。来源#1504。
- **修复/验收要求：** VAL3编码最后字段应使用nPayloadSize；同时对VAL3→C++、C++→VAL3建立固定黄金报文，断言magic/version/type/sequence/payload_size=124/总长132和字段逐一一致；再用非偶然序号（如1、123、125、65535、0）验证payload_size始终为124，并为畸形payload长度增加拒绝测试。修复前不要把当前VAL3服务端状态帧当作已通过完整协议一致性验收。

### 9.3.4 VAL3命令帧payload_size校验时序缺陷（协议输入校验）

- C++ RobotCommandMessage固定总长55字节，其中Header为8字节、payload为47字节；构造函数初始化payload_size=47，serialize()也会先校验payload_size是否等于47后才写出命令帧。VAL3 initRobotCommandMsg同样设置nPayloadSize=47并分配55字节缓冲区。来源#1508–#1509。
- decodeRobotCommandMsg.pgx在调用decodeHeader前，先执行`size(nSerializedData) != nHeaderSize + nPayloadSize`；此时x_msg.header仍是上一次保留的头字段（首次调用时为initRobotCommandMsg设定的8+47）。随后decodeHeader.pgx解析当前数据包并在头部长度、magic、protocol version正确时将x_bError置为false，覆盖掉前面的长度声明检查结果。decodeRobotCommandMsg后续按固定字段解析55字节并只验证最终读取偏移等于数组长度；没有在当前报文头解码后检查`nPayloadSize == 47`或`buffer_length == header_size + decoded_payload_size`。来源#1505、#1507–#1508。
- 因此，若收到实际长度仍为55字节、但头部payload_size字段被改成非47的报文，现有命令解码路径可能仍将固定位置的命令字段解析并标记为valid。readDataOnce.pgx确实会拒绝UDP数据报实际长度与预分配数组长度不一致的情况，所以本项不是短包越界读取结论；它是对当前报文Header声明未作一致性校验。正常C++驱动发送的命令帧携带47，不代表对畸形/第三方报文的校验已完成。来源#1507、#1509–#1510。
- **修复/验收要求：** 先检查实际datagram最小头长度，再解析Header；解码后立即校验magic/version/type、payload_size==47及实际帧长==8+payload_size，不得让decodeHeader清除此前的输入长度错误；之后才读取命令字段。新增测试覆盖payload_size=0/46/48/65535但实际长度55、实际datagram短/长、错误magic/version/type以及正常55字节命令帧，并断言畸形头不会设置bIsValid=true或保留旧命令。

### 9.3.5 DiagnosticData Header校验顺序与覆盖缺口（新增，静态发现）

- `DiagnosticDataMessage::message_size()`固定返回74字节，即8字节Header与66字节payload。其`deserialize()`先检查缓冲区至少74字节，随后立即用对象当前`header.payload_size`和`header.message_type`校验，之后才调用`header.deserialize()`读取当前数据报的Header；读取后没有再次检查当前`payload_size==66`。因此这段前置校验没有验证输入数据报自己的Header字段。来源#1511。
- **对象复用边界需准确区分：** `RealTimeSocketSubscriber::update_message()`每收到一个数据报都会先构造新的局部`MessageType msg`再反序列化，所以正常订阅回调中该前置校验读到的是构造函数默认值（DIAGNOSTIC_DATA/66），不是上一数据报遗留的Header。默认值恰好使前置检查通过，随后当前Header被读取但其payload_size没有复核。若调用方直接复用同一个`DiagnosticDataMessage`实例调用`deserialize()`，则前置检查还会依赖该对象此前保留的Header；这属于直接复用调用的额外状态依赖，不应误写为subscriber常规路径。来源#1512。
- `FrameHeader::deserialize()`读取magic、protocol version、message type、sequence和payload_size，但其内部只验证magic number；`DiagnosticDataMessage::deserialize()`未在当前Header解码后补上固定payload长度检查。实际datagram短于74字节会被该类开头的最小长度检查拒绝；本项限定为长度至少74字节、但当前Header声明payload_size错误时仍缺少一致性校验，不是短包越界读取结论。来源#1511、#1514。
- `RobotDriver::read_diagnostic_data()`在读取后另行检查消息类型与staleness，但没有检查payload_size；另一方面，`RobotDriver::connect()`中的诊断读取仍是TODO，`diag_interface_ready`被直接设为true。因此不能据此声称诊断报文已经成为连接准入门槛，或当前握手已被该问题影响。该函数路径若被显式调用，payload_size验证仍缺失。来源#1513。
- 可见`test_message_serialization.cpp`包含合法`DiagnosticDataMessage`序列化/反序列化往返测试，但未看到payload_size畸形、错误type/version、74字节外实际长度或同一对象重复调用的回归用例；本轮没有运行该测试。来源#1515。
- **修复/验收要求：** 先在临时Header中解析当前报文，再验证magic、protocol version、message type=DIAGNOSTIC_DATA、payload_size=66及固定帧长=74，之后才解析payload并提交对象状态；避免校验失败时部分更新对象。增加payload_size=0/65/67/65535、错误type/version/magic、datagram长度73/74/75、合法连续帧及同一对象复用的用例，并在subscriber实际回调路径验证畸形帧不会进入message buffer。未确认目标CS9当前是否发送该诊断帧，本发现仅为C++解析器静态校验缺口。


### 9.3.6 随附VAL3应用的诊断数据发布链路未实现/未接通（高优先级集成缺口）

- **socket配置存在，但应用对象没有绑定诊断socket。** staubli_robot_driver/val3/configs/sio.cfx定义了control与diagnostics两个UDP endpoint，后者端口为11001且描述为发布诊断信息；但随附ros2_server.dtx只声明siSocketControl并链接到UdpSocket\control，没有siSocketDiagnostics数据对象或对应绑定。配置文件中的socket声明不等于VAL3程序已打开并发送数据。来源#1518、#1520。
- **应用工程清单没有诊断报文的数据类型/编码器/发送程序。** 固定commit的ros2_server.pjx注册的程序包含controlTask、encodeRobotStateMsg、encodeRobotCommandMsg等；类型只有ThrottleLogMsg、MessageHeader、RobotState、RobotStateMsg、RobotCommand、RobotCommandMsg，未见DiagnosticDataMsg或对应初始化/编码程序。来源#1519。
- **启动入口明确把诊断任务留作TODO。** start.pgx在“Setup supervision/diagnostics task”后只有TODO，随后仅创建4 ms同步controlTask。controlTask.pgx只初始化RobotState/RobotCommand，通过encodeRobotStateMsg编码并调用sendData(siSocketControl,...)发布RobotState；没有向诊断socket发送DiagnosticData的调用。来源#1516–#1517。
- 因此，在本次固定的公开仓库快照中，随附VAL3 userapp没有发现能向11001发布C++ DiagnosticDataMessage的发送链路。该结论限于仓库随附应用；不能排除集成方另行部署自定义VAL3任务/程序或其他外部诊断服务。README与sio.cfx确实要求配置diagnostics socket，但配置要求本身不能证明发布功能已经实现。来源#1520–#1521。
- **C++测试的诊断数据来自mock，不是随附VAL3应用。** MockRobotServer::send_mock_diagnostic_data()在C++侧构造并序列化DiagnosticDataMessage后直接发UDP；test_robot_driver.cpp另用原始socket每4 ms发送合成诊断帧，并明确说明诊断通道没有专门publisher interface。硬件接口测试夹具也周期调用mock诊断发送函数。此类测试证明C++接收端可以与测试mock互通，不证明VAL3端到端互操作。来源#1522–#1523。
- **连接准入目前会掩盖缺失的数据生产端。** RobotDriver::connect()会绑定诊断UDP socket并创建subscriber；is_ready()只确认socket/接收线程处于工作状态。其等待首包循环把diag_interface_ready直接设为true，诊断读取调用仍为TODO，所以即使没有任何诊断数据报也可能通过诊断接口readiness步骤。调用read_diagnostic_data()时若尚未收到有效数据则会返回失败。来源#1524、#1513。
- **影响与证据边界：** 当前实现不能据此宣称真实CS9可以通过该随附VAL3应用提供控制器型号、固件版本、错误日志和控制任务状态；C++数据结构、mock测试与网络端口配置只证明接收端/模拟端存在。若目标项目依赖诊断数据做型号/固件准入、故障记录或维护功能，应先将诊断发布链路纳入交付范围。尚未在CS9上运行程序、抓包或验证外部自定义配置。
- **修复/验收要求：** 在VAL3端增加与C++ 74字节帧一致的诊断数据类型/编码器/发送程序，并将siSocketDiagnostics绑定到UdpSocket\diagnostics；确认字段顺序和宽度与C++一致（payload 66字节：controller type 1、firmware版本3、10个error_code共20、10个timestamp共40、control_task_status 2）；在独立诊断UDP socket上按定义的周期或事件策略发送。C++连接准入应明确诊断通道为必需或可选：必需时等待首个合法、当前且型号/固件受支持的诊断帧，超时fail-closed；可选时显式报告degraded状态，不能把“socket已绑定”称为“diagnostics ready”。增加VAL3黄金帧、mock与真实发送端互操作、无包/断线/重复/乱序/过期/错误版本/错误payload故障测试。以上均为待实施项，本轮未修改上游驱动代码或VAL3应用。

### 9.3.7 DiagnosticData读取路径未拒绝重复序号帧（条件性静态风险）

- RobotDriver::read_diagnostic_data()调用diagnostics_subscriber_->read_message()后检查消息类型与time_since_received，但没有检查status.new_message。RealTimeSocketSubscriber的接口明确允许“此前收到过消息、这次没有新消息”时仍返回true，并将new_message设为false。来源#1525、#1527。
- RealTimeSocketSubscriber::update_message()对每个成功反序列化的数据报都会更新reception_timestamp；read_message()遇到相同sequence number时会把status.new_message设为false，但仍返回true。若同序号重复/重放的数据报持续进入接收回调，其本地接收时间戳会持续刷新，read_diagnostic_data()仍可能把未更新的诊断内容返回为成功且不触发staleness拒绝。来源#1526。
- 当前测试test_rt_socket_interface.cpp对通用RobotState subscriber验证了第二次读取会返回true且new_message=false，之后没有新数据时按接收时间变陈旧；但没有发现针对RobotDriver::read_diagnostic_data()忽略new_message、或重复序号诊断帧洪泛刷新staleness的集成回归测试。来源#1527。
- **作用范围限定：** 这是C++诊断接收调用路径的静态缺陷候选，只有当真实CS9集成或其他发送端提供DiagnosticData数据报时才会进入该路径；本报告§9.3.6已指出固定公开VAL3 userapp尚无诊断发布链路。因此不能声称随附VAL3应用目前会产生该重复诊断帧，也没有通过UDP注入证明可利用性。
- **修复/验收要求：** read_diagnostic_data()必须区分“收到新消息”和“缓存中有旧消息”，在status.new_message=false时不得将其作为一次新的诊断更新成功返回；订阅器只应在通过序号前向性/会话重置校验的新帧上更新时间戳。增加正常新帧、同序号重复、重放洪泛、乱序旧帧、序号回绕、断流及超时测试，并断言重复帧不能延后staleness watchdog或覆盖最近一次有效诊断数据。未运行测试或网络故障注入。

### 9.3.8 三类报文固定字段布局与大小端对照（协议基线补充）

本节基于固定上游提交 `ICube-Robotics/staubli_driver_ros2@bd658e2d266e315d2ee35f985fb352ea88306b79` 对 C++ 序列化辅助函数、三类消息 serializer/deserializer、VAL3 状态编码器及状态有效标志做静态对照。以下偏移均为**整帧绝对字节偏移**，包含 8 字节 Header。

**字节序和数值宽度：**

- C++ `serialization.hpp` 在编译期要求 little-endian 主机；`uint16_t`、`uint32_t` 和 `float` 通过 `memcpy` 原样写入/读出。宿主 API 中使用的 `double` 会先显式转换为 `float` 再序列化，因此线上宽度为 IEEE-754 binary32（4 字节），不可按 C++ 成员的 `sizeof(double)` 推导帧长。未知或非 little-endian 编译目标会触发预处理错误。
- VAL3 encoder/decoder 注释及实现显式使用 `2l`（uint16 little-endian）和 `4.0l`（single precision little-endian）；单字节字段使用 `1`。就当前支持的小端 C++ 主机与随附 VAL3 源码而言，没有发现独立的大小端约定冲突。来源#1528–#1530、#1532。
- 8 字节 Header 的通用字段为：偏移0–1 magic `0xABCD`；偏移2 protocol_version；偏移3 message_type；偏移4–5 sequence_number；偏移6–7 payload_size。小端下 magic `0xABCD` 的线上字节为 `CD AB`。C++ FrameHeader 与 VAL3 encode/decodeHeader 的字段顺序相同；但 VAL3 encodeHeader 将 sequence_number 再写入偏移6–7而非 payload_size 的已知错误仍成立，详见§9.3.3（状态帧实际调用该函数）。来源#1503、#1505–#1506、#1529–#1530。

**RobotState（message_type=1，payload=124，整帧=132）：**

| 整帧偏移 | 宽度 | 字段 |
| --- | ---: | --- |
| 0–7 | 8 | Header |
| 8–9 | 2 | sequence_delay（uint16） |
| 10 | 1 | control_state |
| 11 | 1 | safety_status |
| 12 | 1 | operation_mode |
| 13 | 1 | operation_mode_status |
| 14–15 | 2 | status_flags（uint16） |
| 16–17 | 2 | valid_fields_flags（uint16） |
| 18–41 | 24 | joint_positions：6 × float32 |
| 42–65 | 24 | joint_velocities：6 × float32 |
| 66–89 | 24 | joint_torques：6 × float32 |
| 90–113 | 24 | F/T sensor：6 × float32 |
| 114–115 | 2 | digital_inputs_flags（uint16，bit0对应输入0） |
| 116–131 | 16 | analog_inputs：4 × float32 |

C++ 对应 serializer 对四组 double 数组逐项转成 float32；VAL3 `encodeRobotStateMsg.pgx` 对关节位置、速度、扭矩及F/T数据使用 `4.0l`，字段主顺序与上述布局一致。需注意：随附 `updateState.pgx` 当前将 `bValidFtSensor`、`bValidDigitalInputs`、`bValidAnalogInputs` 设为false；编码器虽然预留了F/T后3项和I/O的字节位置，但这些写入仍为注释/TODO。当前有效字段标志明确声明这些值无效，不能把预留字节解释为已实现的F/T或I/O采集。来源#1528、#1531–#1534。

**RobotCommand（message_type=2，payload=47，整帧=55）：**

| 整帧偏移 | 宽度 | 字段 |
| --- | ---: | --- |
| 0–7 | 8 | Header |
| 8–11 | 4 | controller_period：float32（宿主成员为double） |
| 12 | 1 | command_type |
| 13–36 | 24 | command_reference：6 × float32 |
| 37–38 | 2 | digital_outputs_flags（uint16） |
| 39–54 | 16 | analog_outputs：4 × float32 |

C++ `RobotCommandMessage` serializer 和 VAL3 `decodeRobotCommandMsg.pgx` 对 payload 字段次序、宽度及小端浮点格式相符；既有§9.3.4记录的 VAL3 当前Header payload_size校验时序缺陷不因字段布局相符而消失。来源#1507–#1510、#1528、#1531。

**DiagnosticData（message_type=3，payload=66，整帧=74）：**

| 整帧偏移 | 宽度 | 字段 |
| --- | ---: | --- |
| 0–7 | 8 | Header |
| 8 | 1 | robot_controller_type |
| 9–11 | 3 | firmware major/minor/patch |
| 12–31 | 20 | 10个error_code，逐个uint16 |
| 32–71 | 40 | 10个timestamp，逐个uint32（毫秒） |
| 72–73 | 2 | control_task_status（uint16） |

特别注意：C++ 内存结构 `ErrorLogEntry` 的成员声明顺序是 timestamp、error_code，但 wire serializer 并非按10条结构体逐条交错编码；它先遍历一次写出全部10个 error_code，再遍历一次写出全部10个 timestamp。未来任何 VAL3 诊断发送器都必须遵循此线格式。当前固定的公开 VAL3 userapp没有诊断发送器（§9.3.6），所以本节只能定义C++侧参考契约，不能声称VAL3已实现或通过互操作。来源#1531；诊断发送链路边界见#1516–#1524。

**74字节 DiagnosticData 参考黄金向量（源码派生，非实测抓包）：**

下列字段样例：sequence=0x1234、CS9、固件1.2.3、error_code依次为0x1000–0x1009、timestamp依次为0x01020304–0x0102030D（毫秒）、control_task_status=0x1234。它按 C++ serializer字段顺序及 little-endian 宽度逐字节推导，可作为后续 C++/VAL3 fixture 的固定预期值；本轮未执行 C++ serializer、未由 VAL3 生成，也未抓取控制器数据报。

```text
CD AB 01 03 34 12 42 00 02 01 02 03 00 10 01 10
02 10 03 10 04 10 05 10 06 10 07 10 08 10 09 10
04 03 02 01 05 03 02 01 06 03 02 01 07 03 02 01
08 03 02 01 09 03 02 01 0A 03 02 01 0B 03 02 01
0C 03 02 01 0D 03 02 01 34 12
```

**验证边界与后续动作：** 当前核对证明的是源码声明/逐字段偏移，不证明 VAL3 编译器对每种数据类型的实际运行行为，也不证明真实 CS9 线上数据。下一步应将上述向量固化为 C++ golden test；在修复 Header 错误后，分别建立 RobotState（132字节）、RobotCommand（55字节）跨语言双向 fixture，并验证负数/边界浮点值、uint16回绕及有效标志位；DiagnosticData 则须等发送端实现后再验证。此处未运行任何上游测试、未编译 VAL3、未做 UDP 注入或实机验证。

### 9.3.9 三类消息序列化校验不对称与黄金向量测试缺口

固定上游提交的 `messages.cpp` 与 `test_message_serialization.cpp` 对照发现，三类消息的Header校验路径并不一致：

- **RobotState：** `serialize()` 在调用 `header.serialize()` 前未校验 `payload_size`、`message_type` 或 `protocol_version`；`deserialize()` 虽有“Validate header fields”注释，但该处没有实际校验语句。帧长度满足132字节即可继续解析payload。由此，错误类型/错误payload_size/不支持版本的Header可能被接受或原样发出；FrameHeader::deserialize实际只检查magic；protocol_version/type/payload_size仍需消息层校验。FrameHeader::serialize本身也不验证这些字段，详见§9.3.10。
- **RobotCommand：** serializer在写Header前检查payload_size及message_type；deserializer先解Header再检查payload_size及message_type。当前片段未见对protocol_version的一致性检查。
- **DiagnosticData：** serializer先写出Header，再检查payload_size及message_type；校验失败时会返回false，但调用者提供的输出buffer此时已被写入Header。deserializer则在调用`header.deserialize()`读取输入Header之前，先用对象当前Header字段校验payload_size/type，之后读取当前Header并未复核输入Header的payload_size/type。正常subscriber每包创建新消息对象的影响边界已在§9.3.5说明。
- **现有测试缺口：** `test_message_serialization.cpp` 对FrameHeader及三种消息有serialization/deserialization round-trip，对RobotState vector API和小buffer有检查；未发现独立的固定逐字节golden fixture，也未发现分别针对三种消息的错误message_type、payload_size、protocol_version、magic和输入长度正/负向矩阵；FrameHeader通用层的实际检查范围及测试buffer长度语义详见§9.3.10。Round-trip由同一实现编码再由同一实现解码，不能独立证明wire layout正确；三类serializer/decoder共享同一偏差时测试仍可能通过。来源#1535–#1537。
 
**建议的测试规格（尚未实施）：**

1. 为三种消息分别建立不可变的十六进制golden fixture，按§9.3.8字段偏移表逐字段验证；fixture必须由独立脚本/第二实现生成并经人工复核，不能直接调用待测serializer生成期望值。
2. 对每类消息分别测试：正确magic/版本/type/payload_size；错误magic；错误/未知type；版本不匹配；payload_size少1、多1、极值；整帧短1、精确长度、长1。明确协议是否拒绝尾随字节，不能让“缓冲区至少够长”默认为允许任意尾随数据。
3. 对RobotState重点验证Header四字段与132字节长度的一致性；当前实现缺少Header字段校验，应先确定兼容性策略再修复，避免静默改变既有协议。
4. 对RobotCommand验证serializer/deserializer对type和payload_size的对称拒绝行为，并补protocol_version策略。
5. 对DiagnosticData先修复“校验旧对象Header而不是输入Header”的顺序问题，再验证输入Header与实际datagram长度一致；serializer应在写buffer前完成全部可失败校验，或明确保证失败时buffer不会被消费者使用。
6. 用非对称字段值检查端序和字段顺序；float32样例覆盖正数、负数、+0/-0、有限极值和精度舍入；对NaN/Inf是否允许应成为显式协议策略，而不是由平台偶然决定。
7. 测试必须包含独立验证结果：逐字节diff、字段级解码结果、拒绝原因和测试运行环境/编译器/架构。当前没有执行这些测试，也没有通过VAL3生成fixture。

**本节结论：** 当前C++ round-trip覆盖证明基本自洽，不等于协议互操作正确。RobotState Header字段缺少实际校验是新增静态发现；RobotCommand与DiagnosticData虽有部分校验，但时序和覆盖仍不对称。此发现限于固定公开上游commit，不代表真实CS9运行时行为。

## 9.3.10 FrameHeader通用校验范围与长度参数语义

进一步将三类消息实现与 protocol.cpp 的 FrameHeader 实现、protocol.hpp 的协议定义及测试fixture逐项对照，发现消息层问题之外还存在一个共同的Header校验边界：

- **FrameHeader::deserialize：** 按固定8字节顺序读取magic、protocol_version、message_type、sequence_number、payload_size，但返回前仅验证magic_number等于 MAGIC_NUMBER；没有验证protocol_version是否等于当前 PROTOCOL_VERSION，也没有对message_type或payload_size施加通用约束。具体消息类必须自行完成其类型和长度校验，而RobotState当前没有完成；RobotCommand/DiagnosticData虽校验type/payload_size，但都没有补protocol_version校验。来源#1538。
- **FrameHeader::serialize：** 只检查buffer至少有8字节，随后按字段原样写出；不验证magic_number、protocol_version、message_type或payload_size。因而RobotState可将无效Header直接写出；RobotCommand/DiagnosticData的消息层检查只覆盖type/payload_size，不覆盖magic/version。来源#1538。
- **版本校验是全局缺口：** protocol.hpp将PROTOCOL_VERSION=1定义为当前协议版本，FrameHeader注释也称version应为该值，但固定上游commit的FrameHeader读写函数均未实施版本一致性校验。此结论是源码行为描述，不推断上层部署是否另有网络隔离或外部校验。来源#1538、#1540。
- **长度参数语义：** FrameHeader及三类消息反序列化入口均采用“buffer_size至少达到固定长度”判断，未要求buffer_size必须恰好等于8/132/55/74字节；解析器随后只读取已定义的固定字段。若调用方传入的是实际datagram长度，超长报文的尾随字节不会被这些函数消费或拒绝；若传入的是接收缓冲区容量，则该参数并不等于实际datagram长度，不能仅凭此API断言网络端已接受超长UDP帧。必须在socket接收层明确传递实际接收字节数，并单独定义尾随字节策略。来源#1535、#1538。
- **测试证据边界：** test_message_serialization.cpp的fixture在SetUp中将通用buffer resize为1024字节；FrameHeader及三类消息的round-trip均以该buffer调用指针/长度API。测试只验证正常数据可往返，不验证精确长度策略；唯一小buffer负向样例为10字节RobotState。文件中没有对magic/version/type/payload_size错误值或超长datagram尾随字节的断言。1024字节是测试缓冲区长度，不能将它误写成测试已构造并验证了1024字节网络报文。来源#1539。
- **失败时对象/缓冲区状态：** FrameHeader::deserialize在读取全部字段后才检查magic；magic错误会返回false，但Header成员已被输入内容覆盖。DiagnosticData serializer在消息层校验前已将8字节Header写入输出buffer；失败返回不等于输出buffer保持原样。调用方必须把false视为整个帧无效，不能继续发送或解析部分结果。来源#1535、#1538。

**补充测试规格（尚未实施）：**

1. 增加独立FrameHeader单元测试：正确/错误magic、当前/未知protocol_version、合法/未知message_type、payload_size边界；分别验证serialize和deserialize行为及失败后对象/缓冲区状态。
2. 为三种消息建立版本策略矩阵：当前版本1接受；未知高版本、旧版本和0版本如何处理必须显式规定。不能只在RobotCommand/DiagnosticData测试中补局部断言而保留RobotState差异。
3. 明确 buffer_size 的契约：区分接收缓冲区capacity与socket实际datagram length；对8/132/55/74字节精确帧、短1字节、长1字节及含任意尾随数据的帧逐项测试。若API仅接收capacity，应在调用层传入实际接收长度或新增独立长度参数。
4. 对所有失败路径验证“不消费、不发布、不刷新接收时间戳、不更新sequence基准”；若解析失败可能修改对象字段，建议采用临时Header/临时消息解析后提交，或明确调用方必须丢弃失败对象。
5. 将协议版本、magic、消息类型、payload长度和实际datagram长度的校验收敛到可复用的单一入口，避免三种消息各自实现产生不对称。

**本节结论：** §9.3.9所述三类消息差异成立，并可进一步确认FrameHeader通用层只校验magic、不校验协议版本；序列化端也不校验Header字段。当前API按最小缓冲区长度工作，不能单凭buffer_size推断网络超长帧已被接受。需要把实际datagram长度、版本兼容策略和失败原子性列为协议契约。以上均为固定上游commit的静态源码审查，未运行测试或故障注入。

### 9.3.11 UDP接收错误处理、1024字节缓冲区与截断数据报边界（新增，静态风险）

对固定main快照的UDP socket实现、抽象接口、subscriber回调和消息解析器做端到端核对：

- **接收缓冲区固定为1024字节。** `MAX_SOCKET_PACKET_SIZE`在`socket.hpp`定义为1024，`UDPSocketImpl`构造及启动接收线程时均按该值分配`recv_buffer_`。注释称其为最大UDP包长，但该常量实际上是本驱动接收缓冲区上限，而不是UDP协议最大包长。来源#1541–#1542。
- **异步接收错误仍会进入业务回调。** `handle_data_received(error, bytes_transferred)`在`error`非零时只记录日志，没有return/丢弃；随后无条件调用`reception_callback_(recv_buffer_, bytes_transferred)`。subscriber回调将该长度传给`update_message`，后者只依据消息反序列化结果决定是否写入最新消息缓冲区。来源#1541、#1543。
- **超长数据报的截断风险需要运行时确认。** 当发送端发来大于1024字节的UDP数据报，底层接收操作可能以message_size类错误报告缓冲区不足；当前上层忽略error，仍把bytes_transferred交给解析器。若特定OS/Boost组合在此错误路径上返回的字节数达到RobotState/RobotCommand/DiagnosticData固定帧长，且截断前缀恰好构成可通过现有校验的合法帧，解析器采用“至少固定长度”策略，理论上可能把截断数据报前缀当成完整消息接收。**本轮没有在目标OS/Boost版本上发送超长UDP数据报，不能断言该分支实际返回的bytes_transferred值，也不能将此项写成已复现缺陷。**来源#1541、#1543–#1544。
- **错误包来源校验与本问题相互叠加。** `sender_endpoint_`由`async_receive_from`填充，但处理函数中来源地址校验仍为TODO；因此不能依靠发送方地址过滤阻止非预期数据报进入解析链。来源#1541。
- **现有socket测试没有覆盖该边界。** 可见loopback测试使用128字节数据，验证回调收发和多包接收；未发现1024字节边界、1025字节及更大数据报、message_size错误、错误回调不得提交消息或截断前缀伪装成固定长度帧的用例。来源#1545。

**建议修复/验收：**

1. 在`handle_data_received`中对非零error实行明确策略：除可恢复且语义明确的情况外，不得把错误接收交给业务解析器；message_size必须计数、丢弃并触发可观测告警。
2. 为每次接收保留实际数据报长度和接收错误状态；若协议仅允许固定长度帧，socket/subscriber入口应按消息类型精确校验132/55/74字节，明确拒绝超长尾随数据和截断数据，不能只依赖解析器的最小长度检查。
3. 保留并实现发送方IP/端口白名单校验；在网络层ACL之外，应用层仍需拒绝非预期endpoint。
4. 增加loopback集成测试：1023、1024、1025、1472、65507字节；错误状态注入；合法帧前缀加超长尾随字节；畸形/截断帧；断言错误报文不更新message_buffer、不刷新reception_timestamp、不改变sequence基准。
5. 在目标Ubuntu 24.04/Jazzy、Boost版本和实际网卡路径上记录`error`与`bytes_transferred`，再决定本项风险等级；测试必须包含实际CS9网络拓扑下的抓包/故障注入，但不能在未隔离的生产运动状态下执行。

**本节结论：** 新增一项UDP接收错误传播与缓冲区边界风险候选。静态证据足以确认1024字节固定接收缓冲区、错误回调仍被调用及subscriber继续尝试解析；超长数据报是否在特定运行环境中形成可接受的截断前缀，尚待复现。该结论不改变既有协议Header/诊断链路发现，也不代表已经进行网络注入或实机验证。

### 9.4 测试覆盖范围

- 公开单元测试含UDP loopback/mock：连接/断开、state序列化/反序列化、消息序列丢失计数、状态staleness检测及恢复、HardwareInterface初始化/配置/接口导出/Lifecycle和位置命令写入路径。测试代码可证明存在这些测试用例，不代表本轮已执行。CI在2026-11-01有一次Jazzy build_and_test成功记录；它只代表该次工作流成功，不能替代真实机器人、网络故障注入或安全验证。来源#1487、#1491。
- 本轮查看的staubli_robot_driver/test/launch和staubli_bringup/test目录只有.gitkeep，没有可见launch集成测试文件。静态检查也未找到针对UDP错误发送返回语义、发送方伪造/错误来源、payload长度不一致、Infinity命令、>6轴command_reference越界、模式边界、真实I/O链路和控制器故障恢复的对应测试。此结论限定于本轮所检查的目录/快照。来源#1491。
- 单元测试、仿真、HIL、FAT/SAT和实机测试均未由本轮执行。不能把“有mock测试代码”或“CI绿色”提升为生产级可靠性结论。

## 10. 结论更新与下一轮验证优先级

1. 先修复并验证UDP发送返回语义：对would_block丢包返回失败，或提供可读的累计丢包/连续丢包阈值并触发上层安全降级；测试必须确认硬件接口不会把被丢弃的运动命令报告为成功。
2. 对每个UDP数据报做来源地址/端口校验；状态消息逐包校验magic/type/version/payload长度/sequence新旧关系和有限数值；命令解码在解析当前Header后校验payload_size=47与实际帧长，避免旧Header参与当前包预检；对状态/命令使用错误包、乱序、重复、回绕及payload字段畸形注入测试。
3. 把控制器诊断读取真正纳入连接准入：验证CS9型号、固件、VAL3版本和必需addons/许可证；对诊断链不可用时保持fail-closed，不要把diagnostic-ready硬编码为true。
4. 明确VAL3旧命令失效策略：对无新命令、接收错误、时钟/sequence异常、task overrun分别定义停止动作、超时阈值、锁存/复位和重新授权；对每条路径做故障注入。
5. 在ROS主机端强制校验目标DoF（当前协议/VAL3实现为6轴），修复num_joints_对固定6元素command_reference的越界访问路径；对NaN、正负Inf和极端值使用isfinite及逐关节位置/速度/加速度/jerk限值检查；确认Controller/VAL3二次限位、模型单位、零位、负载和工具坐标一致。
6. 补齐I/O与控制模式闭环：实现并测试VAL3数字/模拟输出写入、输入采集；明确remote/auto/manual/hold与安全状态的命令许可矩阵；未完成速度控制前不要暴露为可用command interface。
7. 固定Jazzy依赖、CS9控制器软件、VAL3版本和addons/license；在SRS/模拟控制器、HIL和实际TX2/CS9上分阶段测量周期、jitter、WCET、序列延迟、丢包、停止响应、重复精度和负载变化。
8. 取得Stäubli受控文档、SRS/VAL Blocks具体版本、目标型号/控制器选件矩阵、驱动器兼容与安全证书原件；按产品SKU/固件/地区核验，不以产品页面能力名称代替证据。
9. 将§9.3.8的固定字段偏移表和74字节DiagnosticData参考向量固化为C++ golden tests；修复Header字段缺陷后再建立RobotState 132字节、RobotCommand 55字节的VAL3↔C++双向fixture，覆盖端序、float32舍入、字段顺序、有效标志和畸形Header。
10. 统一FrameHeader与三类消息的magic/version/type/payload_size校验，并明确buffer容量和实际datagram长度的区别；对解析失败时对象状态、输出buffer原子性、序号基准和接收时间戳开展负向测试。\n11. 修复UDP接收错误传播：错误码非零时不得调用业务解析器；在目标Ubuntu/Boost组合复现1024字节边界和超长数据报行为，补充精确帧长、发送方endpoint及错误报文不刷新状态的集成测试。

本轮完成公开页面、上游GitHub元数据、源码和测试目录的静态核查；没有安装SRS/VAL Blocks、没有构建或运行ICube工作区、没有运行上游测试、没有连接CS9/机器人/PLC/安全回路，也没有执行实时测量、故障注入、HIL/FAT/SAT或功能安全验证。因此本次只能更新静态审查结论和工程验证清单；Stäubli档案与21-02节点继续保持未验收。