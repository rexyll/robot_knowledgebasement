# Stäubli Robotics 软件与 ROS 生态静态审查（2026-11-06）

> 审查范围：Stäubli 官方 CS9/VAL 3/uniVAL 资料、ICube ROS 2 Jazzy 驱动、ROS-Industrial VAL3 历史驱动及 ROS Index 元数据。  
> 审查类型：公开资料与公开仓库静态审查；不是产品选型结论、供应商资格审查或工程验收。  
> 对应任务：根任务 00-01；第 21 章 21-02。  
> 来源：链接台账 #1413–#1421、#1481–#1510。

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

本轮完成公开页面、上游GitHub元数据、源码和测试目录的静态核查；没有安装SRS/VAL Blocks、没有构建或运行ICube工作区、没有运行上游测试、没有连接CS9/机器人/PLC/安全回路，也没有执行实时测量、故障注入、HIL/FAT/SAT或功能安全验证。因此本次只能更新静态审查结论和工程验证清单；Stäubli档案与21-02节点继续保持未验收。