# Stäubli Robotics 软件与 ROS 生态静态审查（2026-11-06）

> 审查范围：Stäubli 官方 CS9/VAL 3/uniVAL 资料、ICube ROS 2 Jazzy 驱动、ROS-Industrial VAL3 历史驱动及 ROS Index 元数据。  
> 审查类型：公开资料与公开仓库静态审查；不是产品选型结论、供应商资格审查或工程验收。  
> 对应任务：根任务 00-01；第 21 章 21-02。  
> 来源：链接台账 #1413–#1421、#1481–#1549。

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


### 9.3.12 UDP发送成功语义、接收线程停止/重启与回调生命周期（新增，静态风险）

对固定main快照的UDPSocketImpl、RealTimeSocketSubscriber、RealTimeSocketInterface、RobotDriver及socket单元测试做跨层核对：

- **would_block丢包被报告为发送成功。** UDPSocketImpl::send调用非阻塞send_to(..., MSG_DONTWAIT, err)。遇到boost::asio::error::would_block时记录“Packet dropped”并保留TODO计数/阈值，但没有返回false；函数最终返回true。上层RealTimeSocketInterface::send_message据此返回true，RobotDriver::send_robot_command也可能将未发送的运动命令报告为成功。该行为是静态代码路径确认，不代表本轮实际触发了内核发送缓冲区满。来源#1546、#1548。
- **停止接收线程只停止io_service并join，没有显式取消socket上的异步接收。** stop_receive_thread执行io_service_.stop()、receive_thread_.join()，随后才把receiving_设为false；未见socket_.cancel()或关闭/重建socket的操作。Asio run循环停止不等于底层异步操作已取消。若调用方在不disconnect的情况下直接stop后restart，旧接收操作仍可能在io_service_.reset()后被重新派发，同时start_receive又提交新操作；两者复用同一个recv_buffer_和sender_endpoint_，存在重复接收链和共享缓冲区并发写风险。该重启序列未在目标Boost版本上运行复现，列为条件性生命周期风险。来源#1546。
- **重复start会先覆盖现有回调，再检查线程状态。** start_receive_thread在检查is_connected()和is_receiving()之前执行reception_callback_ = reception_callback。当接收线程已经运行时，第二次start最终返回false，但已经替换了当前活动回调；若另一线程正执行回调读取该std::function，还可能形成未同步读写。现有DoubleStart测试两次传入同一callback，只断言第二次返回false，未验证原callback保持不变，也未用不同回调并发验证。来源#1546、#1549。
- **接收回调捕获Subscriber裸this。** RealTimeSocketSubscriber::init_communication传入[this]回调并调用update_message；析构函数调用socket_->stop_receive_thread()。正常外部析构路径在join完成后可等待回调线程退出，但Socket公共接口没有表达“析构必须由非接收线程发起”的约束，也没有独立回调生命周期令牌；若未来回调内触发自析构/stop，可能产生线程自join或对象生命周期问题。当前仓库没有发现该调用路径，故只记录设计约束，不标记为已触发UAF。来源#1547。
- **RobotDriver关闭顺序有重复stop但可等待subscriber析构。** RobotDriver::disconnect先reset control_interface_/diagnostics_subscriber_（其基类析构停止接收线程），随后又按socket状态检查并再次stop，再disconnect socket。Socket stop对已停止线程返回true，常规单线程disconnect路径有join屏障；但RobotDriver整体connect/disconnect/send没有可见互斥保护，并发生命周期操作与周期命令发送的安全性未由此顺序证明。来源#1547–#1548。
- **测试覆盖不构成生命周期验收。** 现有测试覆盖单次start/stop、重复start/stop、正常回调、多包接收、disconnect后reconnect；没有stop→start但不disconnect、stop期间持续数据报、重复start时替换callback、并发send/disconnect、发送would_block返回值、销毁与回调同时发生等测试。来源#1549。

**建议修复/验收：**

1. would_block必须返回false或返回结构化发送结果（sent/dropped/error）；命令路径不得把已丢弃的数据报报告为成功。增加可观测drop counter、连续丢包阈值和上层安全降级策略；阈值/动作由系统安全需求定义，不能仅靠日志。
2. 将停止状态设为原子/受锁保护的“stopping”并先阻止handler重新投递；显式cancel socket outstanding operations，处理operation_aborted，再join；确保stop完成后没有遗留async operation，start只允许在明确清理完成后复用io_context/socket。
3. 在start_receive_thread中先完成连接/状态校验，再安全安装callback；对start/stop/connect/disconnect建立统一生命周期互斥或明确线程安全契约，避免并发访问socket、io_service、thread及std::function。
4. 增加不同callback的重复start测试，断言失败的第二次start不替换原callback；增加stop→start（无disconnect）、stop时持续收包、重复start/stop压力循环、callback触发析构边界测试。
5. 增加可控发送错误注入（包装socket/注入错误码）验证would_block、message_size、其他错误分别映射为明确结果；验证RobotDriver命令发送失败时不更新成功状态/命令序号。
6. 为disconnect/connect/send增加生命周期锁或由单一拥有者串行化，并在ThreadSanitizer构建下运行并发压力测试；实时路径锁策略需评估阻塞上界，不得直接在周期线程引入无界互斥等待。

**本节结论：** 已确认would_block路径“丢包但返回成功”这一静态缺陷；另确认stop不显式cancel异步接收、重复start先覆盖回调及并发生命周期缺少显式同步的设计风险。stop→restart造成旧操作重入/共享缓冲区竞争属于由代码控制流推导的条件性风险，仍需在锁定的Boost/Ubuntu版本下通过回归测试与TSan复现。没有执行上游构建、单测、网络压力或实机验证。

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
12. 修复UDP发送与生命周期：would_block丢包必须向上返回失败；停止接收时cancel异步操作并阻止handler重投递；保证stop/restart、重复start、disconnect/send并发和callback销毁有明确同步契约及TSan/压力测试。

本轮完成公开页面、上游GitHub元数据、源码和测试目录的静态核查；没有安装SRS/VAL Blocks、没有构建或运行ICube工作区、没有运行上游测试、没有连接CS9/机器人/PLC/安全回路，也没有执行实时测量、故障注入、HIL/FAT/SAT或功能安全验证。因此本次只能更新静态审查结论和工程验证清单；Stäubli档案与21-02节点继续保持未验收。

## 9.3.13 UDP发送缓冲区并发、RobotDriver共享状态与ros2_control生命周期（2026-11-07）

> 审查基线：ICube-Robotics/staubli_driver_ros2 固定源码commit `bd658e2d266e315d2ee35f985fb352ea88306b79`。本节为源码静态审查；不代表已通过目标Ubuntu/Boost版本的线程检测或CS9实机验证。

### A. UDP发送链的共享可变状态

1. **RealTimeSocketInterface::send_message复用单个data_out_，未见发送互斥。** 构造函数只预分配一个成员vector；每次send_message都将消息serialize到同一data_out_，随后交给socket_->send。类声明/实现没有mutex、strand或发送队列。若两个调用线程并发进入同一个接口实例，会对data_out_产生并发写/读，属于可由C++内存模型判定的数据竞争候选；是否存在具体并发调用取决于上层调度和错误处理调用时序。来源#1550。

2. **底层UDP socket也没有发送/关闭同步。** UDPSocketImpl::send先读取atomic is_connected_，随后访问非原子remote_endpoint_并调用socket_.send_to；disconnect可在另一路径stop接收线程后close同一socket。atomic连接标志只能提供该布尔值的原子访问，不能保护socket对象、remote_endpoint_或send与close之间的生命周期。没有发现统一锁或strand。若send与disconnect/connect并发，socket对象共享访问安全尚未建立；本轮未运行TSan或压力测试，不声称已观察到崩溃。来源#1550。

3. **多个上层命令入口可能汇聚到同一个发送对象。** RobotDriver::send_robot_command和send_stop_all_command均通过control_interface_->send_message发送；后者没有先检查control_interface_是否为空。HardwareInterface::write在周期线程发送常规命令，而on_error/on_shutdown等生命周期回调也可能发STOP。框架在特定生命周期转换期间是否保证write与这些回调绝不并发，需按锁定的ros2_control版本和executor/controller_manager调用路径验证；不能仅凭当前类实现假设线程互斥。来源#1551、#1552、#1553。

### B. RobotDriver对象内部状态的同步契约

4. **RobotDriver没有对象级同步。** 头文件虽包含mutex/condition_variable，但类成员未声明用于连接状态、接口指针、命令发送或状态快照的锁。connect/disconnect会创建、reset接口并操作socket；send/read/is_connected直接读取shared_ptr成员并访问current_robot_state_、current_diagnostic_data_和last_valid_sequence_id_。这些字段不是原子变量，也未被统一锁保护。若调用者允许并发connect/disconnect/read/send，shared_ptr成员本身的读写及状态对象访问可能构成数据竞争；这是缺少线程安全契约的静态发现，不是已经复现的竞态。来源#1552。

5. **序号读取与更新也依赖调用顺序。** read_robot_state更新last_valid_sequence_id_；HardwareInterface::write经get_current_message_sequence读取该值作为命令序号。该值是普通size_t，getter没有锁。如果read与write由同一个controller_manager更新线程按顺序调用，通常不会在这两个访问之间形成线程竞争；若另有线程调用读取/写入API，则需显式同步。当前API注释没有声明线程亲和性或禁止并发调用。来源#1552、#1553。

### C. ros2_control生命周期与停止行为

6. **on_deactivate没有在该插件中覆写。** StaubliHardwareInterface声明/实现覆写on_configure、on_activate、on_cleanup、on_shutdown和on_error，但未声明on_deactivate。因而插件自身没有在deactivate回调中明确将控制模式切为STOP、发送STOP或断开通信的动作。生命周期框架可能停止后续read/write调用，但这不等于向机器人控制器发送了停止命令；必须验证控制器端VAL3超时/失联策略是否会在失去新命令时安全停止。来源#1553。

7. **cleanup和shutdown的停止语义不一致。** on_cleanup直接调用robot_driver_->disconnect()，没有先发送STOP；on_shutdown仅在robot_driver_仍连接且state_msg_.control_state != STOP时尝试send_stop_all_command，再disconnect。on_error会尝试send_stop_all_command，但忽略其bool返回值，之后仍返回SUCCESS。故代码层面无法据此证明deactivate/cleanup/error/shutdown每条路径都成功发送并确认STOP；尤其UDP send曾发现would_block误报成功，STOP路径同样受其影响。来源#1550、#1552、#1553。

8. **on_activate只设置软件命令模式。** 它把current_control_mode_设为STOP并返回SUCCESS，没有显式等待新鲜状态、复核控制器安全状态/操作模式或验证通信链恢复。后续perform_command_mode_switch对位置模式检查error_state、motion_possible并警告operation_mode_status，但不能替代生命周期激活准入和安全回路验证。来源#1553。

### D. 测试缺口与建议

- 增加同一RealTimeSocketInterface并发send测试，使用TSan检查data_out_；明确发送API是单线程调用、内部序列化还是队列化。实时路径若加锁，必须测量锁等待上界和优先级反转。
- 增加send与disconnect/connect并发压力测试；为连接生命周期定义单一所有者/状态机，确保关闭socket前禁止新发送并等待在途发送退出。
- 为RobotDriver声明并实现线程安全契约：至少明确connect/disconnect只能在停止update循环后调用；若支持并发，则保护接口指针和共享状态，并避免在实时线程持有无界锁。
- 对send_stop_all_command增加空接口/未连接检查；生命周期回调必须检查STOP发送结果，通信失败时返回ERROR并进入明确的故障锁存/人工复位路径，不能把“尝试发送”当作已停止。
- 实现并测试on_deactivate行为；明确deactivate、cleanup、error、shutdown与VAL3侧命令超时之间的停止保证。STOP UDP报文不是安全额定急停，不能替代控制器安全功能、外部E-stop或风险评估。
- 对每个生命周期转换记录状态机前后状态、最后有效反馈时间、STOP命令发送结果、控制器ACK/停止状态及超时行为；覆盖deactivate期间持续运动、反馈丢失、send would_block、controller disconnect、重复转换和异常退出。
- 锁定ROS 2 Jazzy/ros2_control具体版本后，核实controller_manager在read/write与hardware lifecycle callbacks之间的调用/同步保证；再以TSan、ASan、故障注入和目标平台HIL验证，不将框架常见行为代替该版本证据。

### E. 本节结论与证据边界

本节确认的是：发送缓冲区与socket对象没有可见并发保护；RobotDriver接口指针和共享状态没有对象级同步；插件没有显式on_deactivate停止处理；cleanup不发送STOP，on_error不检查STOP发送结果。这些是静态代码事实。具体是否触发数据竞争，取决于运行时是否存在并发调用；本轮未执行构建、单元测试、TSan/ASan、并发压力、网络错误注入、ros2_control生命周期实验或CS9/VAL3实机测试。不得将风险候选写成已复现缺陷，也不得将STOP UDP命令视为安全功能验收。


## 9.3.14 VAL3控制循环、命令新鲜度看门狗与故障恢复锁存（2026-11-07）

> 审查基线：ICube-Robotics/staubli_driver_ros2 固定上游commit `bd658e2d266e315d2ee35f985fb352ea88306b79`。本节依据VAL3项目文件静态审查；没有在CS9控制器、VAL3 Studio或实际机器人上运行这些程序。关于sioGet的超时/队列行为、movejSync的实际停止时间和VAL3任务调度语义，仍须目标控制器实测。

### A. 控制任务的实际周期与收发顺序

1. **VAL3控制任务按4 ms同步周期启动。** `start.pgx`设置 `l_nCtrlPeriod = 0.004`，调用 `taskCreateSync "controlTask", l_nCtrlPeriod, bIsOverrun, controlTask()`。每轮controlTask先更新机器人状态、递增16位序号并发送状态，再读取命令、计算序号延迟、判断命令模式，最后更新位置/速度控制或执行STOP。状态报文因此是该轮命令接收/执行之前采集的状态，不是该轮新命令执行后的确认。来源#1556、#1561。

2. **接收函数最多执行两次非阻塞读取。** `readData`将最多尝试次数固定为2，重复调用`readDataOnce`；后者用`sioGet`读取固定长度数据，长度等于缓冲区才置new-data，非零但长度不符则报错。两次读取可以在一个控制周期内消费最多两个数据报，倾向于取较新的数据，但没有显式统计被覆盖/丢弃的中间命令数量，也没有按报文序号验证“只接受最新且单调递增”策略。零字节/无数据时不置错误。sioGet的具体队列语义和每次调用耗时仍需CS9/VAL3实测。来源#1557。

3. **源码自己标记了未完成的命令陈旧性检查。** controlTask在无新命令但已有有效命令时留有`TODO: staleness`；随后使用序号差计算delay作为间接新鲜度监测。没有独立的基于单调时钟的命令年龄计时器，也未看到对重复、倒退或重放序号的明确拒绝逻辑（负差仅在特定条件下转成回绕值，其余负差会触发错误）。来源#1556、#1561。

### B. 命令超时与movejSync看门狗

4. **控制任务使用按周期计数的两个阈值。** 当`l_bControlActive`为真，机器人正在运动且`l_nSequenceDelay > 5`时，置错误并切换STOP；机器人不在运动时，`l_nSequenceDelay > 25`才触发错误。周期名义值4 ms，对应严格大于阈值后的约24 ms和104 ms量级（实际时间会受任务超时/调度影响）。这不是精确墙钟超时。来源#1556、#1561。

5. **movejSync状态1的命令刷新超时目前只被注释掉。** `updateJointPositionControl`将状态1定义为“movejSync运行中，但上次命令未及时刷新”；读取到状态1时，相关warning日志被注释，代码不设置`x_bError`，继续返回正常。控制任务的序号延迟阈值可能随后触发STOP，但两者的时间关系和movejSync内部超时行为未由当前源码/仿真验证。应明确这两个看门狗的优先级、最坏停止响应时间和失效独立性，不能将movejSync状态1视为已安全处理。来源#1558。

6. **位置控制的运动准入检查不完整。** updateJointPositionControl检查`bMotionPossible`、命令有效性、命令类型和关节范围；“目标是否足够接近当前位姿”的检查仍为TODO。状态1（movejSync刷新超时）没有进入错误处理。来源#1558。

### C. 错误处理与自动恢复

7. **控制错误触发停止动作后，错误锁存被清除。** controlTask错误分支记录“hard stop and reset”，调用`stopMove()`和`resetMotion()`，把命令类型置0、控制模式置0，随后明确执行`l_bError = false`，使通信控制标志复位并调用`resetControlSocket`。该路径没有等待操作员确认、外部安全复位或显式重新使能授权。来源#1556。

8. **重新接受命令前的延迟仍是TODO。** 错误恢复分支末尾明确写有“add delay (e.g., 1000ms) before accepting new commands?”。当前控制循环在socket reset成功后会继续运行；后续有效命令到达时，代码没有由该TODO形成的等待锁存/人工确认门槛。因此，静态上存在“通信/控制错误后，恢复通信即可再次接受运动命令”的自动恢复路径。是否能在实际控制器上立即重新运动，取决于驱动端控制模式、VAL3状态、机器人安全状态和movejSync状态，尚未实机复现。此项应作为高优先级设计风险，不直接宣称机器人必然自动重启运动。来源#1556。

9. **控制任务中的“hard stop”不等于安全额定停止。** 该分支调用的是VAL3程序层的`stopMove()`、`resetMotion()`和停止同步运动控制的函数。源码没有证明这些动作具备安全等级、冗余监控或独立于普通应用任务的安全完整性。必须将其与CS9安全控制器、外部E-stop、STO/SS1等实际安全功能区分；本审查不对其安全等级作任何推定。来源#1556、#1558、#1559。

### D. 状态语义与安全门控

10. **bMotionPossible的计算没有纳入工作模式状态。** updateState将`bMotionPossible`定义为“驱动已上电且未检测到安全停止”，工作模式/状态另由`workingMode(x_state.nRobotStatus)`读取；文件中更严格地要求`nRobotStatus == 0`的表达式被注释。位置控制函数主要依赖bMotionPossible，故“自动/远程/本地/手动/hold状态是否允许当前控制命令”的策略没有在该布尔量内完整表达。是否由底层运动指令或CS9限制拒绝动作，需实机验证；建议把操作模式、状态和控制权准入写成明确的状态机。来源#1559。

11. **bEStopped把所有非零安全状态折叠成true。** updateState注释列出0无安全停止、1等待安全重启、2 SS1、3 SS2、4等待WMS重启，随后设置`bEStopped = (nSafetyStatus != 0)`。这对“禁止运动”可能是保守的，但字段名会把SS1/SS2/等待确认状态都映射成“急停已按下”，可能造成ROS上层诊断语义混淆。应分别暴露原始安全状态、急停输入状态与运动许可，避免把状态码压缩成单一急停布尔值。来源#1559。

### E. 修复与验证要求

- 将命令年龄改为基于单调时钟的超时，并同时检查序号单调性、重复/回放、丢包和回绕；明确控制周期超限时阈值换算与最坏响应时间。
- 为接收队列建立明确策略：每周期消费一个/最多N个数据报时，记录丢弃数和最后接受序号；验证sioGet非阻塞读取语义、队列深度和报文边界。
- 将movejSync状态1纳入明确的故障处理，验证其内部超时、停止动作及与序号看门狗之间的先后关系；给出最坏停止响应时间预算。
- 错误后采用故障锁存状态机：通信恢复不得自动等价于运动重新使能；需要操作员/安全系统确认、状态新鲜度检查、控制权验证和明确的重新使能步骤。具体设计必须遵循Stäubli/CS9安全手册及风险评估。
- 把`bMotionPossible`拆分为驱动上电、急停/安全状态、操作模式、远程控制权、机器人状态和最终运动许可；核实manual/test/automatic local/automatic remote/hold的行为。
- 建立故障注入测试：丢包、延迟、乱序、重复包、旧序号重放、突发多包、错误长度、UDP断连、控制周期overrun、movejSync状态1、机器人运动中错误、错误后立即恢复通信、操作模式切换及安全重启等待。
- 在VAL3仿真/离线验证后，再在受控测试单元、低速低加速度、独立安全防护和授权人员监督下进行HIL/CS9验证；不得把仿真或普通STOP动作替代安全认证。

### F. 结论与证据边界

固定源码明确存在：staleness TODO、movejSync状态1处理被注释、错误分支清除错误锁存、恢复前延迟TODO、工作模式状态未纳入bMotionPossible、多个安全状态折叠为bEStopped等设计缺口/语义风险。它们说明源码没有完整表达所需的失联安全停止与人工重新使能契约，但不等于已经在实机观察到自动恢复运动或停止失败。本轮未运行VAL3、CS9仿真、构建、测试、网络注入、控制周期测量或实机试验；Stäubli未验收。


## 9.3.15 ROS 2—VAL3端到端命令门控、STOP确认与故障矩阵（2026-11-07）

> 基线仍为ICube上游固定commit bd658e2d266e315d2ee35f985fb352ea88306b79。本节把ROS 2硬件接口、RobotDriver、VAL3控制循环和状态映射串联审查；仅为公开源码静态分析。未在CS9/VAL3环境执行，未推断Stäubli原生运动指令的物理停止特性。

### A. ROS 2侧命令准入与反馈语义

1. **位置模式切换时检查最近一次状态，但不是逐周期安全门控。** perform_command_mode_switch()在切换到JOINT_POSITION时检查缓存的state_msg_.error_state和motion_possible；operation_mode_status != 0只产生HOLD警告，仍继续完成模式切换。该检查依赖最近一次read取得的状态快照，没有在切换动作内重新请求新鲜状态，也没有校验状态时间戳在切换瞬间仍有效。来源#1562。

2. **write()不直接检查全部监督状态。** 每次写入会检查连接状态；非STOP模式下检查error_state及control_state == INVALID，但不直接检查motion_possible、estop_pressed或wait_for_ack。因此运行中安全/模式状态变化的实际阻断主要依赖VAL3位置控制函数每周期的bMotionPossible检查，以及控制器自身安全机制，而不是ROS write每周期重新门控。若read先返回错误，ros2_control调用顺序/错误传播如何影响同周期write，需锁定具体ros2_control版本验证。来源#1562、#1567。

3. **主机命令限位仍未形成完整防线。** RobotDriver::send_robot_command明确保留位置/速度限位TODO；HardwareInterface写入路径仅检查NaN（Inf不在该判断内），并把命令转换为度后发送。模式切换对operation_mode_status只警告。控制器端isInRange提供另一层位置范围检查，但主机侧应补finite、限位、最大单步变化、速度/加速度/jerk及工作模式准入。来源#1562、#1563、#1567。

4. **状态序号不是命令执行确认。** VAL3每轮先采集/发送RobotState，再读取并执行本轮命令；ROS端读取该状态序号作为下一命令的序号来源。它用于ping-pong延迟计算/通信同步，但没有看到带命令序号的执行结果ACK或STOP完成ACK。状态中control mode/in_motion可用于后续观察，但由于发送发生在本轮命令处理之前，不应把同一轮状态包当成本轮新命令执行后的确认。来源#1556、#1562、#1563、#1566。

5. **STOP是尽力发送的普通控制消息。** send_stop_all_command构造STOP命令并调用control_interface_->send_message，返回发送函数bool；未等待VAL3确认、停止状态或机器人静止状态。结合此前would_block分支丢包仍return true的静态发现，STOP调用返回true也不能作为数据报到达或机器人已停止的证据。on_error还忽略STOP返回值，cleanup直接disconnect。来源#1546、#1553、#1563。

### B. VAL3状态与停止处理链

6. **安全状态原始码与ROS布尔状态存在语义折叠。** updateState列出0无安全停止、1等待Safety Restart、2 SS1、3 SS2、4等待WMS重启；bEStopped对全部非零码置true，bWaitAck仅对码1置true。workingMode另写入机器人模式/状态；bMotionPossible仅由drive-powered与非bEStopped构成，未把工作模式状态纳入该布尔值。ROS导出这些监督字段，但不能将bEStopped解释为“急停按钮确实按下”。来源#1559、#1562、#1564。

7. **VAL3 STOP路径是应用层停止请求，不是已证明的安全功能。** controlTask在STOP/错误路径调用stopMove()/resetMotion()，位置控制停止函数还包含movejSync停止相关调用；但公开仓库没有提供足以证明这些原生VAL3指令停止类别、响应时间、制动器行为或PL/SIL能力的受控文档。不能推断stopMove等同E-stop、SS1、SS2或STO。具体原生语义必须以对应CS9/VAL3版本手册和Stäubli书面确认/实测为准。来源#1556、#1567。

8. **命令读取的队列语义仍未闭环。** readData每周期最多调用readDataOnce两次；readDataOnce通过sioGet返回字节数判断完整帧，正数短/长长度置错误、零字节视为无新数据。代码没有记录一个周期内覆盖/丢弃的命令数量。sioGet是否从UDP队列取最新包、是否可能阻塞、超长datagram如何表现以及队列溢出行为，不能仅凭源码假设，必须在目标控制器上测量。来源#1557、#1565。

### C. 端到端故障矩阵

| 故障/事件 | 当前可见响应 | 未闭环点/验收要求 |
|---|---|---|
| ROS节点崩溃或进程退出 | ROS端可能停止发送；VAL3序号延迟阈值可在控制任务仍运行且控制已激活时触发错误并进入STOP路径 | ROS退出是否必然触发UDP失联、何时触发、失联时机械臂实际停止时间、驱动重启后是否锁存，需故障注入/实机测量 |
| UDP丢包/延迟 | VAL3按序号差在运动中>5、静止>25触发错误；C++发送would_block存在丢包误报成功路径 | 乱序/重复/重放、突发多包、16位回绕和真实序号时钟关系未完整验证；阈值不是墙钟保证 |
| UDP断连/Socket异常 | VAL3读取错误置错误并进入stopMove/resetMotion及socket reset；ROS read可能因无新状态/陈旧返回ERROR | ROS lifecycle是否随后发STOP、断连期间STOP不可达、恢复后是否要求人工重新使能均未闭环 |
| VAL3任务overrun | 记录overrun并累计nOverruns | 未见按累计次数触发确定性降级/锁存策略；实际控制周期和最坏停止响应未测 |
| movejSync状态1 | 代码注释称上次命令刷新不及时，但warning/error处理被注释；序号看门狗可能后续触发 | 内部超时与外层序号看门狗先后、停止响应时间需仿真/HIL确认 |
| SS1/SS2/E-stop/等待重启 | bMotionPossible因非零安全状态变false；bEStopped统一为true，bWaitAck仅状态1 | 原始安全状态、E-stop输入、工作模式、控制权和最终运动许可应分别映射；不得将ROS状态当安全回路 |
| 故障后通信立即恢复 | 错误分支清除l_bError、重置socket；恢复前延迟/人工确认仍是TODO | 自动重新接收命令的锁存风险；必须实现故障锁存/授权复位并验证，不能由通信恢复单独触发运动 |
| ROS deactivate/cleanup/shutdown/error | deactivate未覆写；cleanup直接disconnect；shutdown条件性发STOP；error尝试STOP但不检查返回值 | 需要生命周期停止契约、STOP送达/执行反馈、控制器侧失联策略和失败时故障锁存 |

### D. 修复优先级与验证门槛

- **P0：STOP与失联必须可证实。** 定义命令接收ACK、命令执行/模式ACK、停止完成状态及超时；STOP失败或通信丢失时由独立安全链承担风险降低，不能依赖UDP bool。
- **P0：故障恢复必须锁存。** VAL3错误后进入明确FAULT_LATCHED；通信恢复仅恢复诊断，不得自动恢复运动。由操作者/安全系统确认、模式/控制权验证、状态新鲜度检查及显式重新使能组成状态机。
- **P0：明确模式和安全状态映射。** 分离E-stop输入、SS1、SS2、Safety Restart、WMS restart、manual/test/automatic local/remote/hold；由CS9安全功能与控制器许可决定运动，不由压缩后的布尔值替代。
- **P1：补主机实时准入。** 每周期验证状态年龄、motion_possible、safety status、operation mode/control ownership、finite命令、关节软限位和单步增量；验证read错误后同周期write的框架语义。
- **P1：确定UDP队列/序号策略。** 明确只接收最新命令或按序执行；拒绝重复、倒退/重放；记录每周期消费/丢弃数量、序号回绕和接收年龄；在目标VAL3上验证sioGet行为。
- **P1：停止函数语义证据。** 取得CS9/VAL3受控手册，确认stopMove/resetMotion/movejSyncEnd及stopJointPositionControl的行为、错误码、停止类别、可中断性和适用版本；无文档时在受控单元测量，不对安全等级作推断。
- **P1：生命周期测试。** 覆盖deactivate、cleanup、shutdown、error、controller_manager停止、进程崩溃、socket断连、反馈过期和重连；断言机器人停止反馈而非只断言API返回值。

### E. 证据边界

本节补充的是源码层面的端到端控制流和接口语义，未在目标ROS 2/ros2_control版本运行，未执行构建、测试、网络故障注入、TSan/ASan、VAL3仿真、CS9 HIL或实机验证；没有测得停止时间、停止距离、队列深度或movejSync响应。未取得stopMove/resetMotion原生指令受控手册，故不作物理停止类别或安全等级判断。Stäubli项目仍是公开prototype，不能作为生产级控制软件验收。

## 9.3.16 VAL3停止包装程序、错误清理顺序与ROS 2生命周期缺口（2026-11-07）

> 上游固定基线：ICube-Robotics/staubli_driver_ros2，commit bd658e2d266e315d2ee35f985fb352ea88306b79。以下为源码静态控制流结论，不代表VAL3原生运动指令的物理语义或实机停止结果。

### A. stopJointPositionControl()实际做了什么

1. 程序先读取$movejSyncState()；仅当状态不等于-1（注释定义为movejSync未启动）时调用$movejSyncEnd()。之后不再读取状态、不等待状态进入停止态、不检查任何返回值，直接设置x_bError=false。来源#1568。
2. 因此该包装函数的成功布尔值只代表程序走完了调用路径，不构成movejSync已停止、机器人已静止或停止动作已被控制器接受的证据。若movejSyncState()返回-2（错误态）或1/2（刷新超时/运动锁定），代码仍会尝试movejSyncEnd；实际可否调用及结果依赖VAL3原生API语义，不能由该包装代码确定。
3. updateJointPositionControl在motion不可能、命令无效、命令类型错误、位置越界及movejSync错误等路径调用stopJointPositionControl；但上层controlTask随后仍会执行stopMove()/resetMotion()。这些调用的先后关系是源码事实，停止类别、制动过程和响应时间仍未证实。来源#1567、#1568、#1569。

### B. controlTask错误恢复不是故障锁存

4. STOP/ERROR执行分支：当前命令模式小于等于1时，若上一模式为2则先调用stopJointPositionControl；随后无条件调用stopMove()和resetMotion()。错误处理块若当前l_nCmdMode仍为2，会再调用一次stopJointPositionControl，然后再次stopMove()/resetMotion()。该重复调用路径取决于错误发生位置和当轮模式变量，不应一概认定每次错误都调用两次。来源#1569。
5. 错误处理随后把命令类型置0、l_nCmdMode置0，**直接将l_bError清为false**，把序号清零、延迟设为1000、控制连接标志清零、命令置无效并重置控制socket；唯一的重置失败路径会重新置l_bError=true。最后保留的TODO仍是“在接受新命令前增加延迟”。静态上看，错误处理完成且socket重置成功后，没有独立FAULT_LATCHED状态、人工确认标志或重新使能token。来源#1569。
6. controlTask结束退出时也调用stopMove()/resetMotion()，但这仍是程序退出清理路径，不能替代外部安全回路。stopMove/resetMotion/movejSyncEnd均不能仅凭函数名推断为E-stop、SS1、SS2、STO或安全额定停止。来源#1568、#1569。

### C. ROS 2生命周期回调交叉核对

7. on_activate()仅把current_control_mode_设为STOP并返回SUCCESS，没有发送STOP消息，也没有验证控制器当前模式/静止状态。若上次退出时控制器仍保留活动状态，主机激活动作本身不构成机器人侧状态同步屏障。来源#1570。
8. on_cleanup()在robot_driver_存在时直接disconnect()，不先调用send_stop_all_command()；disconnect返回值也未用于回调结果。cleanup因而不能被视为有确认的停止序列。来源#1570。
9. on_shutdown()仅在driver connected且缓存的state_msg_.control_state != STOP时发送普通STOP，然后立即disconnect；不检查STOP发送bool，不等待新状态确认。若缓存状态已是STOP但机械臂仍有运动、缓存陈旧或状态不同步，则此条件本身不能证明物理静止。来源#1570。
10. on_error()在连接时发送普通STOP但忽略返回值，随后返回SUCCESS；未连接则返回ERROR。结合UDP would_block时发送接口可能丢包仍返回true的既有发现，这个回调没有可验证的停止成功条件。来源#1546、#1553、#1563、#1570。

### D. 由源码推导的具体验收用例

| ID | 注入/前置条件 | 必须观测的结果 | 当前代码证据/缺口 |
|---|---|---|---|
| STP-01 | movejSync状态分别为-1、-2、0、1、2时调用stopJointPositionControl | 记录原生API返回、状态转移、机器人速度/位置及错误传播 | 包装函数无停止后状态检查，所有分支最终x_bError=false（除调用异常未建模） |
| STP-02 | 正常运动中发送STOP | 记录STOP命令接收、movejSync结束、控制器停止状态、实际静止时间 | 当前没有命令级ACK或静止确认 |
| STP-03 | 在updateJointPositionControl各错误出口注入错误 | 记录stopJointPositionControl/stopMove/resetMotion调用次数和顺序 | 部分路径可能重复请求停止，需检查是否幂等及原生API允许性 |
| STP-04 | 控制任务错误后立即恢复UDP并发送新位置命令 | 验证保持故障锁存，只有授权复位后才允许运动 | 当前清除l_bError、reset socket，延迟TODO |
| STP-05 | ros2_control触发cleanup/on_error/on_shutdown，分别设置缓存状态STOP/非STOP/陈旧 | 验证停止命令送达、停止完成确认后才断连；失败时明确故障 | cleanup无STOP；shutdown不等ACK；error忽略bool |
| STP-06 | ROS进程崩溃/断电、网络中断 | 机器人由控制器独立看门狗/安全链进入定义的停止状态 | ROS生命周期回调无法在进程崩溃时保证执行，必须由机器人侧独立机制兜底 |

### E. 修复要求

- **P0：将停止请求与停止确认分离。** movejSyncEnd/stopMove调用结果、VAL3程序状态、机器人静止判据分别建模；增加带命令ID的STOP接收ACK与停止完成反馈，超时进入锁存故障。
- **P0：修复故障恢复状态机。** 错误时进入FAULT_LATCHED，不能在同一错误处理块自动清除；只有明确的安全复位条件、操作员授权、控制模式/权限检查、状态新鲜度和显式重新使能全部满足后才能恢复。
- **P0：定义VAL3本地失联策略。** 即使ROS主机崩溃或网络断开，机器人侧仍须按经风险评估验证的控制器/安全配置停止；不要依赖ROS on_error/on_shutdown回调。
- **P1：统一生命周期停止契约。** deactivate/cleanup/shutdown/error均应执行一致的停止请求、确认、超时与故障上报；确认失败时不应悄然断连并返回SUCCESS。
- **P1：停止API可观测性。** stopJointPositionControl应验证movejSync状态终态和错误码；区分“请求已发出”“控制器接受”“运动停止确认”，并记录停止请求序号、时间和原因。
- **P1：明确重复停止的幂等性。** 对controlTask中多路径重复调用stopJointPositionControl/stopMove/resetMotion进行VAL3模拟器与CS9测试，确定允许的调用顺序、异常条件和幂等保证。

### F. 证据边界

本节没有执行VAL3仿真、机器人仿真器、CS9 HIL/实机、构建、单元测试、网络注入或停止时间测量。$movejSyncEnd、stopMove、resetMotion为VAL3环境中的原生/系统函数，公开包装代码没有给出其底层实现与安全等级；本节只记录调用条件、顺序和上层反馈处理，不宣称物理停止性能。

## 9.3.17 状态反馈新鲜度、read/write错误传播与控制器停机契约（2026-11-07）

本节固定ICube上游commit `bd658e2d266e315d2ee35f985fb352ea88306b79`，并将其ros2_control运行语义与ROS 2 Jazzy对应文档/源码对照。结论分为上游驱动静态事实、框架版本行为和仍需目标环境验证的事项。

### A. ROS侧RobotState接收与新鲜度

1. `RobotDriver`构造时调用`set_state_staleness_timeout()`；头文件默认阈值为100 ms。每次`read_robot_state()`先检查control interface ready，再读取最新消息、校验消息有效性，并在`status.time_since_received >= state_staleness_timeout_`时返回false；只有全部通过后才更新输出state和`last_valid_sequence_id_`。因此，不能笼统声称ROS状态反馈完全没有staleness检查。来源#1571–#1572。
2. Subscriber在每个成功反序列化的数据报上设置`reception_timestamp=now()`并覆盖消息缓冲区。若没有新消息，`read_message()`会继续使用已有缓存并计算其接收年龄；初始没有任何有效消息时返回false。来源#1573。
3. 该100 ms检查衡量的是“最近一个可解析数据报的到达年龄”，不必然代表状态序号持续前进。§9.3.2已确认重复序号/重复帧仍可能被接收路径接受，而每个成功反序列化数据报都会刷新接收时间戳；因此重复/重放旧状态帧可能持续刷新时间年龄，使序号停滞与数据陈旧未被同一门槛识别。此处属于跨§9.3.2与本节的静态逻辑组合结论，尚未做网络注入复现。来源#1496–#1500、#1573。
4. 状态丢包统计在`read_robot_state()`中仅保留注释掉的warning，不作为错误门槛；100 ms阈值、重复序号接受和VAL3侧命令新鲜度是不同层次，不应混为一谈。来源#1572。
5. `StaubliHardwareInterface::read()`在未连接、状态读取失败（包括超时/无有效消息）或`update_state()`失败时返回`hardware_interface::return_type::ERROR`；成功时才返回OK。失败时没有把旧`state_msg_`当作本轮成功状态继续更新接口。来源#1574。

### B. ROS 2 Jazzy框架对read/write错误的处理

6. ROS 2 Jazzy官方文档明确：硬件组件`read()`或`write()`返回`return_type::ERROR`时，框架调用`on_error(previous_state)`；回调返回SUCCESS后硬件组件进入UNCONFIGURED，回调返回FAILURE/ERROR则进入FINALIZED。来源#1575–#1576。
7. 固定的ros2_control源码还显示，HardwareComponent在read/write调用后检测到ERROR会先执行`error()`，再向上返回该错误；`error()`暂停异步操作并执行插件`on_error()`。ControllerManager收到read/write错误后，会按受影响硬件组件查找关联控制器并执行停用。框架测试覆盖了read错误和write错误时关联控制器转为INACTIVE的行为。来源#1576–#1578。
8. 因而本驱动read错误并非仅打印日志：在该Jazzy框架路径下会进入on_error，硬件组件状态转为UNCONFIGURED（若on_error成功），ControllerManager随后停用关联控制器；处于UNCONFIGURED的HardwareComponent不再执行正常ACTIVE态write。这是框架源码/测试语义，不代表机器人端已经收到STOP或已静止。
9. 驱动`on_error()`在连接时调用`send_stop_all_command()`，但忽略其bool结果，随后无条件返回CallbackReturn::SUCCESS；只有未连接时才返回ERROR。它也没有在该回调中disconnect。因此框架会把回调视为成功并将组件置为UNCONFIGURED，即使STOP发送失败、被底层would_block路径丢弃或未得到机器人确认；同时socket/RobotDriver连接对象没有在on_error中显式释放。来源#1546、#1574、#1576。
10. `write()`对连接丢失、活动模式下的机器人error/INVALID状态、未知控制模式、NaN命令及`send_robot_command()`失败返回ERROR；机器人error/NaN路径会先尝试普通STOP，但未知模式和发送失败路径本身不先显式发STOP，之后依赖框架触发的on_error再次尝试。STOP发送bool仍未被检查。来源#1574。
11. ControllerManager停用关联控制器和HardwareComponent进入UNCONFIGURED，属于ROS框架层的命令源隔离/调度结果；它们不是CS9安全功能，不证明VAL3已处理STOP、驱动器已撤能、制动器已闭合或机械臂达到静止。STOP的端到端确认缺口仍由§9.3.15–§9.3.16覆盖。

### C. 新增风险边界与修复要求

- **P0｜区分报文到达新鲜度与状态进展新鲜度。** 将接收时间戳与单调递增/回绕安全的状态序号进展分开判断；重复帧不得无限刷新“状态正在前进”的健康判据。需定义重复、乱序、回绕和合法重连的独立策略。
- **P0｜on_error必须报告STOP结果并进入可观测故障状态。** 检查STOP发送返回值、传输错误、VAL3 ACK和停止完成反馈；不能在STOP结果未知时无条件返回SUCCESS并将硬件标记为可重新配置。普通UDP STOP不得替代独立安全链。
- **P1｜明确UNCONFIGURED资源所有权。** on_error进入UNCONFIGURED前，应定义socket/线程/RobotDriver资源是关闭、保留还是隔离；重新configure必须有确定的重连、状态重新同步和命令清空流程。
- **P1｜write错误分类。** 区分可恢复命令拒绝、数据无效、通信发送失败和硬件状态故障；所有需要停止的出口均需检查停止请求结果，并将“已请求”“已送达”“已停止”作为不同状态暴露。
- **P1｜版本锁定。** 项目目标为ROS 2 Jazzy，但公开仓库依赖版本与部署环境仍需冻结；本节框架语义依据ROS 2 Jazzy文档及对应ros2_control源码快照，不外推到其他发行版/自定义补丁。

### D. 可执行验收矩阵

| ID | 注入/前置条件 | 必须观测的结果 | 当前证据/缺口 |
|---|---|---|---|
| FB-01 | 状态帧静默超过100 ms | read返回ERROR；on_error调用次数/返回值、硬件生命周期状态和关联控制器状态符合锁定Jazzy版本 | 静态路径明确，未在目标工作区执行 |
| FB-02 | 连续发送相同序号、相同payload的有效状态帧 | 接收时间可刷新，但状态进展健康判据必须判定序号停滞；不得仅靠到达时间维持健康 | 现有接收逻辑可能刷新时间戳；未注入复现 |
| FB-03 | 发送旧序号/乱序帧及65535→0合法回绕帧 | 分别识别重放、乱序、回绕和新会话；状态进展计数无误 | §9.3.2已有静态问题，尚无UDP集成测试 |
| FB-04 | read超时后on_error的STOP发送触发would_block/硬错误 | on_error不得将失败伪装为成功恢复；记录发送错误、组件状态、控制器状态及VAL3反馈 | 既有would_block返回true问题；未注入 |
| FB-05 | read返回ERROR，随后执行ControllerManager完整update周期 | 验证组件转UNCONFIGURED、关联控制器INACTIVE、该组件不再向机器人发送活动命令 | 框架源码/测试已覆盖通用组件，ICube集成未测 |
| FB-06 | write因NaN/unsupported mode/send failure返回ERROR | 验证on_error停止请求、发送结果、控制器停用和硬件生命周期状态 | 插件静态路径已核对，未执行目标版本测试 |
| FB-07 | on_error成功后重新configure/activate | 验证旧socket资源清理、重新连接、首个新鲜状态、命令缓存清零、需人工重新使能且不会自动恢复旧轨迹 | 未做生命周期集成测试 |
| FB-08 | STOP发送成功但机器人状态仍显示in_motion，或状态缓存陈旧 | 系统不得将发送成功/缓存STOP等同静止；须等待独立停止完成判据 | 当前无STOP ACK/静止确认 |

### E. 验证边界

框架源码版本说明：ROS 2生命周期行为以ROS 2 Jazzy官方文档为依据；实现细节交叉检查ros2_control仓库`jazzy`分支文件快照，`hardware_component.cpp` blob SHA `feffb4063586d577db51cfdbaac86aed95e882f5`、`controller_manager.cpp` blob SHA `3a7a2ee84a7e81af458107fb3abdf24819c8724d`、硬件错误处理测试 blob SHA `a987ef03005913a52f1206e7649bc6b0fe6e52cf`。分支URL为可变引用；部署时仍须锁定实际安装的ros2_control包版本/补丁并复核，不把该分支快照冒充为目标设备已安装版本。

本节为固定上游commit、ROS 2 Jazzy官方文档及ros2_control对应源码/测试的静态交叉审查。没有在本环境构建ICube工作区，没有执行ROS 2 Jazzy ControllerManager集成测试、UDP重复/乱序/静默/缓冲区压力注入、TSan/ASan、VAL3仿真、CS9 HIL或真实机器人停止测量。重复帧刷新时间戳的风险尚未动态复现；框架通用测试不等于ICube插件集成通过。Stäubli仍保持静态审查未验收。


## 9.3.18 UDP控制/状态网络的本地绑定与发送方信任边界（2026-11-07）

本节继续固定上游提交 `ICube-Robotics/staubli_driver_ros2@bd658e2d266e315d2ee35f985fb352ea88306b79`，将ROS主机侧HardwareInterface参数解析、RobotDriver网络配置、Boost.Asio UDP socket实际绑定/接收行为，以及随附VAL3部署网络说明交叉核对。结论为静态网络暴露面审查，不代表已完成渗透测试或证明存在可远程利用的运动控制漏洞。

### A. ROS主机侧默认绑定行为

1. `RobotDriver::NetworkConfig`中`local_ip`默认空字符串，头文件注释明确说明空值表示绑定任意网络接口；`RobotDriver::connect()`把该值和本地控制/诊断端口传给两个UDP socket。来源#1580–#1581。
2. `StaubliHardwareInterface::on_configure()`只解析`robot_ip`、control/diagnostic远端端口及local_control/local_diagnostic端口，没有从硬件参数读取或设置`local_ip`。因此通过该HardwareInterface常规配置路径创建的NetworkConfig保留空`local_ip`默认值；除非上游其他调用方显式构造NetworkConfig指定地址，否则不会绑定到专用机器人网卡地址。来源#1581–#1582。
3. `UDPSocketImpl::connect()`对空地址或`0.0.0.0`选择`address_v4::any()`，再对本地端口执行bind；故常规HardwareInterface路径下控制与诊断接收socket分别监听本机所有IPv4接口上的配置端口（默认11000/11001）。这是由配置默认值与绑定实现共同推导出的静态行为，尚未在目标Ubuntu主机用`ss`/`getsockname`实测。来源#1579–#1582。
4. `UDPSocketImpl`保存`remote_endpoint_`用于`send_to()`，但没有调用UDP socket的peer-connect来约束接收对端；异步接收使用`async_receive_from(..., sender_endpoint_, ...)`。接收回调中“validate sender before processing”的代码仍为TODO，示例地址比较被注释，随后不论发送方均调用业务callback。因而配置的robot_ip当前是发送目的地址，不构成入站数据报的发送方认证/过滤。来源#1579。
5. VAL3 README指导将ROS主机接到CS9的J204端口、将主机地址设为`192.168.0.1/24`，并以控制器`192.168.0.254`部署；随附`sio.cfx`把控制和诊断UDP目的地址均设为`192.168.0.1`，端口分别为11000/11001。这说明文档示例预期使用专用链路，但不能抵消ROS主机socket在所有IPv4接口上绑定的实现事实。来源#1583–#1584。

### B. 安全影响与边界

- **P1｜非预期网络接口可达性。** 在常规HardwareInterface路径中，UDP端口监听所有IPv4接口；如果ROS主机还有办公网、Wi-Fi、VPN、容器桥或其他可路由接口，且主机防火墙未阻断，则这些网络上具备路由可达性的主机可能向控制/诊断接收端口发送数据报。实际可达性取决于OS路由、防火墙、网络命名空间和部署拓扑，本轮未探测。
- **P1｜入站来源未验证。** 接收代码已明确留下发送方校验TODO，并继续把数据报交给消息解析回调。结合已审查的序号/重复帧/staleness路径，伪造或重放的状态数据可能污染ROS侧反馈、序号跟踪和健康判断；伪造诊断数据的影响仅在诊断接收链路被外部发送端接通时适用。尚未构造数据报验证端到端影响。
- **安全协议边界。** 当前公开消息Header/字段布局没有显示应用层身份认证、消息完整性MAC或会话nonce字段；UDP校验和不提供发送方身份认证。不得据此宣称网络链路已加密或具备抗重放认证。若产品威胁模型要求跨不可信网络部署，应设计经过实时性评估的认证封装/隔离隧道，而不是仅依赖magic、version、sequence和固定robot_ip。
- **禁止过度推断。** 本节没有证明攻击者能够直接向CS9注入运动命令：当前ROS侧入站方向主要接收状态/诊断，运动命令由ROS主机发往配置的robot_ip；控制器端VAL3的SIO对端过滤/报文接收语义还需受控手册和CS9实验确认。当前可确认的是ROS主机接收面未在源码中验证发送方，以及所有接口绑定默认值扩大了可能的入站暴露范围。

### C. 修复与部署准入要求

1. **默认拒绝宽绑定：** 将`local_ip`纳入HardwareInterface必填参数，要求显式配置机器人专用NIC地址；空值/0.0.0.0在真实硬件模式下应fail-closed。若mock模式不需要socket，应避免误把mock路径作为真实网络安全证据。
2. **验证对端地址与端口：** 在任何消息解析、序号更新和接收时间戳刷新之前，校验`sender_endpoint_`的IP及端口与冻结的机器人端点一致；拒绝非预期来源并记录限速计数。若CS9可能使用多个合法源端口，必须从受控资料/抓包建立明确白名单，不可仅凭猜测放宽。
3. **网络隔离：** 将CS9控制链路放在专用物理接口/VLAN/受控子网；配置主机防火墙仅允许目标CS9 IP及必要UDP端口；禁止从办公网、访客Wi-Fi、VPN或公网路由到控制/诊断端口。网络隔离是纵深防御，不替代应用层发送方验证。
4. **协议抗伪造/重放：** 定义会话/重连标识、单调序号窗口及认证完整性机制；评估MAC/HMAC或受控安全隧道对4ms VAL3循环、主机实时调度和网络时延的影响。不得未经性能与安全验证就直接增加阻塞式加密操作到实时控制循环。
5. **可观测性：** 分开统计有效peer包、拒绝peer包、重复/乱序包、解析失败、staleness和网络接口；日志不得泄露凭据或使攻击者通过高频数据报触发无界日志/CPU开销。

### D. 新增可执行验收矩阵

| ID | 注入/前置条件 | 必须观测的结果 | 当前证据/缺口 |
|---|---|---|---|
| NS-01 | 在双网卡主机启动真实HardwareInterface并检查UDP 11000/11001绑定 | socket只绑定显式机器人NIC地址；不得出现0.0.0.0 wildcard | 源码默认推导；未在Ubuntu目标机检查 |
| NS-02 | 从非机器人网卡/第二主机向控制端口发送合法格式RobotState | 在解析前按peer IP/port拒绝；状态缓存、序号、接收时间戳均不变化 | sender检查仍为TODO；未注入 |
| NS-03 | 从非预期源发送重复/乱序/高频状态帧 | 不进入subscriber，不刷新staleness，不造成无界日志/CPU负载 | 未执行网络压力/资源观测 |
| NS-04 | 向诊断端口发送伪造DiagnosticData | 在来源验证失败时拒绝；诊断ready状态不得被伪造报文提升 | 随附VAL3诊断publisher未实现；外部发送路径未测 |
| NS-05 | 机器人IP正确但源UDP端口异常/变更 | 按已冻结的合法源端口策略处理，不能仅凭目的IP配置放行所有来源端口 | 端口契约尚待CS9受控资料/抓包确认 |
| NS-06 | 主机同时连接专用机器人网、办公网、VPN/容器桥 | 防火墙/路由验证无非授权路径可达11000/11001 | 依赖目标部署拓扑，未执行渗透/防火墙测试 |

### E. 验证边界

本节证据来自固定commit的`udp_socket_impl.hpp`、`robot_driver.hpp`、`robot_driver.cpp`、`staubli_hardware_interface.cpp`、VAL3 README及`sio.cfx`静态源码/配置。未构建驱动、未运行Ubuntu socket绑定检查、未执行双网卡/跨网段UDP注入、未做防火墙/渗透测试、未运行TSan/ASan、未连接CS9或真实机器人。所有安全影响均为基于源码和部署参数的风险分析，不是已复现攻击。Stäubli仍为静态审查未验收。


## 9.3.19 ROS 2硬件参数UDP端口解析与uint16边界（2026-11-07）

本节固定ICube上游commit `bd658e2d266e315d2ee35f985fb352ea88306b79`，检查`StaubliHardwareInterface::on_configure()`的硬件参数解析、端口类型转换、随附Xacro端口配置和现有单元测试夹具。结论是静态输入校验缺口，不代表当前默认11000/11001配置必然失败。

### A. 源码事实

1. `on_configure()`使用`std::stoi()`解析control_port、diagnostic_port、local_control_port、local_diagnostic_port到有符号`int`；解析后直接`static_cast<uint16_t>`写入NetworkConfig，没有在转换前验证端口范围，也没有验证端口非零。来源#1587。
2. 对于能被`int`解析的超范围数值，转换为uint16_t会按无符号16位模数结果折返：例如65536变为0，65537变为1，-1变为65535。若本地端口转换为0，UDP bind会请求临时端口；但控制器端VAL3配置仍向README指定的固定11000/11001端口发送，形成无法按预期收包的配置错配。远端端口为0或折返值则可能连接/发送到错误目的端口。该后果是语言转换与socket配置语义推导，未运行复现。
3. `std::stoi()`调用没有提供`pos`参数或检查已消费字符数，因此像`"11000junk"`这样的带合法数字前缀字符串可能被接受为11000，而不是作为整串非法配置拒绝。来源#1587。
4. 随附`staubli.r2c.xacro`将默认真实硬件控制/诊断远端及本地端口写死为11000/11001；这能覆盖官方示例，但HardwareInterface本身仍公开接受自定义硬件参数，端口输入校验不能只依赖示例Xacro。来源#1588。
5. 现有HardwareInterface测试夹具使用有效端口8001–8004，测试覆盖初始化、正常mock连接和无机器人失败；未发现负数、0、65535、65536、超大值、带后缀字符串或本地端口冲突的负向测试。来源#1589。

### B. 风险与范围

- **P1｜端口截断/折返造成静默配置偏离。** 配置错误可能转成另一个合法uint16端口，导致绑定错误端口、远端目标错误或连接超时，而不是在参数入口给出清晰诊断。
- **P1｜字符串前缀被静默接受。** 配置管理系统、URDF/Xacro模板或人工编辑出现尾随字符时，解析可能接受前缀数字，掩盖配置错误并使审计记录中的端口文本与实际端口不一致。
- **P2｜端口组合一致性未显式检查。** 当前示例端口对彼此不同；对自定义配置，应额外拒绝本地control与diagnostic端口冲突，并验证远端端口符合目标VAL3配置。是否允许使用非默认端口应由冻结的CS9部署配置决定。
- 本项不涉及UDP来源认证（已由§9.3.18覆盖），也不意味着默认11000/11001示例端口本身超范围。

### C. 修复与验收要求

1. 用严格解析函数（如`std::from_chars`并检查返回错误码及结束指针）解析整串十进制文本；拒绝空值、符号/尾随字符（按配置规范）、溢出和前后非法字符。
2. 在转换为`uint16_t`前要求每个端口满足1–65535；如产品明确允许0表示动态端口，必须仅对本地端口单独定义语义，并确保控制器端能获知/使用该端口，否则禁止0。
3. 校验本地control与diagnostic端口不相同；核对远端端口与VAL3 sio.cfx/受控配置一致；错误时在创建/绑定socket前返回ERROR并给出参数名和值。
4. 将端口配置纳入部署快照，记录实际绑定端口与目标端点；不要只记录URDF文本而忽略uint16转换后的运行值。

### D. 新增可执行验收矩阵

| ID | 输入/前置条件 | 必须结果 | 当前证据/缺口 |
|---|---|---|---|
| CV-01 | 端口值-1、0、1、65535、65536、65537 | 仅1和65535在通用端口规则下通过；其他值在socket创建前拒绝 | 现有代码未做范围校验；未运行测试 |
| CV-02 | 端口值2147483648或更大整数 | 严格解析报范围错误，不发生异常遗漏或截断 | stoi可能抛异常；现有catch返回ERROR，但未形成专门测试 |
| CV-03 | `11000junk`、`11000.0`、空字符串 | 全部拒绝，不接受数字前缀 | stoi未检查消费位置；未测试 |
| CV-04 | 本地control与diagnostic端口相同 | 配置阶段明确拒绝或按经批准的socket复用策略处理 | 当前没有组合校验；未测试 |
| CV-05 | 合法端口与目标VAL3 sio.cfx不一致 | 部署一致性检查明确告警/拒绝，不进入“连接成功”假象 | Xacro示例固定11000/11001；未测试自定义配置 |

### E. 验证边界

本节仅核对固定commit源码、Xacro和测试夹具；未修改ICube上游代码，未运行构建/单元测试、端口边界注入、socket绑定实验或CS9实机连接。默认Xacro端口仍为11000/11001；本节识别的是自定义HardwareInfo输入缺少严格解析和范围约束。Stäubli仍为静态审查未验收。


## 9.3.20 ROS 2 Lifecycle停用、清理与断开连接的停止语义（2026-11-07）

本节固定ICube上游commit `bd658e2d266e315d2ee35f985fb352ea88306b79`，逐项核对HardwareInterface头文件声明、生命周期回调实现，以及RobotDriver STOP发送与disconnect顺序。结论聚焦主机侧生命周期转换的显式停止保障，不推断CS9在失联后的实际物理停止时间。

### A. 生命周期回调覆盖

1. `StaubliHardwareInterface`头文件声明并实现`on_configure`、`on_activate`、`on_cleanup`、`on_shutdown`、`on_error`，没有声明或实现`on_deactivate`覆盖。因而组件从ACTIVE转INACTIVE时，该类没有自定义的显式STOP动作；具体基类默认回调语义需按所用ros2_control版本确认。来源#1590。
2. `on_cleanup()`仅调用`robot_driver_->disconnect()`，不先调用`send_stop_all_command()`，也不检查当前控制模式或机器人是否仍在运动。若生命周期流程进入cleanup时驱动仍连接，主机侧直接拆除通信资源。来源#1591。
3. `on_shutdown()`只有在`state_msg_.control_state != STOP`时才调用STOP，然后立即disconnect；该条件使用最近一次缓存的状态快照，且没有检查STOP发送返回值。若快照已过期或控制状态未正确刷新，可能跳过STOP；即使发送返回false，也继续断开连接。来源#1591–#1592。
4. `on_error()`在连接状态为true时调用STOP，但同样忽略`send_stop_all_command()`的bool返回值，随后无进一步验证便返回SUCCESS。来源#1591–#1592。
5. `RobotDriver::send_stop_all_command()`本身能返回false，且分别在准备STOP消息失败或send_message失败时报告失败；因此调用方忽略返回值会丢失可观测的STOP发送失败结果。该函数返回true只证明消息序列化并交给socket发送路径成功，不证明CS9已接收、执行或机器人已静止。来源#1592。

### B. 风险与限制

- **P1｜ACTIVE→INACTIVE没有驱动层显式停止保证。** 类本身没有on_deactivate override；停止行为可能依赖上层controller停止写入、VAL3命令超时/序列延迟保护和控制器自身行为。尚未在目标ros2_control版本或CS9上验证基类默认回调、控制器停用顺序以及真实停止响应。
- **P1｜cleanup先断链、不发STOP。** 如果cleanup在运动期间被调用，主机侧没有明确的STOP-before-disconnect顺序。不能仅凭disconnect完成推断机器人已停止。
- **P1｜shutdown/error吞掉STOP发送失败。** 调用方未检查bool结果，导致生命周期回调可能返回SUCCESS或继续断开，而STOP数据报实际未成功发送。UDP send成功本身也不是机器人停止确认。
- **状态快照条件风险：** shutdown仅在缓存control_state非STOP时发STOP；建议安全退出路径采用幂等、无条件的STOP请求（连接可用时），并对状态回读和停止确认设置独立超时。不要以旧缓存状态作为是否尝试STOP的唯一门槛。
- **边界：** 本节不是安全功能认证，也不替代CS9安全回路、急停或安全PLC；通信STOP不得被视为安全额定停止功能。

### C. 修复与验收要求

1. 实现明确的`on_deactivate()`，当连接仍可用时先发STOP，再等待受限时间内的状态回读/停止确认，然后释放活动控制资源；回调必须报告STOP请求失败或停止未确认。
2. 将`on_cleanup`、`on_shutdown`、`on_error`统一到幂等的安全退出辅助函数：记录触发原因、尝试STOP、检查返回值、按超时策略等待状态反馈，再disconnect；即使STOP失败也必须显式报告并保留故障原因，不得返回虚假的成功。
3. 对停止确认定义可测量条件（例如连续状态帧显示不在运动、控制模式STOP、状态新鲜度在阈值内），区分“命令已发送”“控制器已确认”“机器人已静止”三个层级。
4. 明确disconnect的职责只包括通信资源释放，不把它作为停止动作；若链路已失效，依赖控制器侧独立通信看门狗/安全机制，并在产品安全案例中单独验证。
5. 为生命周期回调加入mock与HIL测试，覆盖STOP发送成功/失败、状态快照过期、cleanup期间运动、重复调用、网络断开和控制器不响应。

### D. 新增可执行验收矩阵

| ID | 场景 | 必须结果 | 当前证据/缺口 |
|---|---|---|---|
| LC-01 | ACTIVE状态执行deactivate | 显式发STOP；记录请求结果；等待有界停止确认后转INACTIVE | 当前类无on_deactivate override；未执行 |
| LC-02 | 运动中直接执行cleanup | 先STOP并尝试确认，再释放socket；STOP失败需可见 | 当前cleanup只disconnect；未执行 |
| LC-03 | shutdown时缓存control_state误报STOP | 仍执行幂等STOP尝试，不因旧快照跳过 | 当前有状态条件；未模拟过期快照 |
| LC-04 | STOP发送接口返回false | lifecycle回调不能静默返回SUCCESS；记录故障并进入定义的降级路径 | 当前shutdown/error忽略返回值；未注入发送失败 |
| LC-05 | STOP数据报发送成功但机器人仍运动/状态未更新 | 区分发送成功与停止确认，超时告警/锁存 | 当前无显式等待确认；未HIL |
| LC-06 | 已断网时执行deactivate/cleanup/shutdown | 明确报告无法通过ROS链路STOP，验证CS9独立watchdog/安全策略 | 未执行断网HIL或CS9验证 |

### E. 验证边界

证据为固定commit的`staubli_hardware_interface.hpp/.cpp`与`robot_driver.hpp/.cpp`静态审查。未构建驱动，未验证ros2_control具体版本的默认on_deactivate行为，未运行lifecycle集成测试、UDP发送失败注入、CS9状态回读或真实机器人停止响应测量。不能宣称已经证明机器人会在cleanup/deactivate后继续运动；本节确认的是软件没有在这些路径上建立可审计的显式STOP与停止确认契约。Stäubli仍为静态审查未验收。


## 9.3.21 VAL3控制任务周期、overrun监测与命令流新鲜度（2026-11-07）

本节固定ICube上游commit `bd658e2d266e315d2ee35f985fb352ea88306b79`，审查VAL3启动程序、主控制循环、序号延迟计算、UDP读取循环和位置控制刷新逻辑。结论是源码中存在名义4 ms周期配置和基于序号差的通信延迟门限，但它们不能单独构成经过测量验证的实时性保证或完整的命令watchdog。

### A. 周期配置与overrun处理

1. `start.pgx`将`l_nCtrlPeriod`设为`0.004`，将`bIsOverrun`清零，并以`taskCreateSync "controlTask", l_nCtrlPeriod, bIsOverrun, controlTask()`创建同步控制任务。该值表示配置的4 ms周期（名义250 Hz），不是实测周期分布或最坏执行时间证明。来源#1593。
2. 启动程序读取`getMonitorSpeed()`；低于100%时只记录警告，等待/阻止启动的代码被注释。源码没有在该路径强制恢复100%或拒绝启动。来源#1593。
3. `controlTask`每轮检查`bIsOverrun`，若为真则记录日志、清零标志并增加`nOverruns`。该计数器在任务启动时重置；本轮未见基于连续/累计overrun阈值的STOP、故障锁存、对外诊断接口或降级策略。来源#1594。
4. 循环尾部调用`delay(0)`。其与`taskCreateSync`周期调度的精确调度语义、任务执行时间统计、优先级/抢占关系和overrun标志置位时机，仍需对应VAL3版本手册及CS9实测确认。源码配置不能证明每轮均在4 ms内完成。

### B. 序号差不是完整的时间watchdog

1. 每轮先更新机器人状态、递增16位状态序号并发送RobotState，然后才读取本轮UDP命令；因此状态报文反映的是本轮命令处理之前采集的状态，序号差反馈存在至少一个控制循环的采样/处理相位差。来源#1595。
2. `computeSequenceDelay`直接计算`lastSequenceSent - lastSequenceReceived`；仅当差值小于-60000时加65536处理16位回绕。它没有使用单调时钟测量真实报文年龄，也没有独立记录命令最后到达时间。来源#1596。
3. 控制任务在机器人运动时以`sequenceDelay > 5`触发错误，在静止时以`>25`触发错误；按名义4 ms折算，分别是序号差至少6和26个周期，约24 ms与104 ms的量级，而不是已经测得的实际超时。若任务周期抖动/overrun，真实时间阈值会随之变化。来源#1595。
4. 对负序号差另有错误分支，但没有看到严格的“新命令序号必须单调前进”校验、重复命令拒绝、会话epoch或发送时间戳校验。序号差阈值可以发现部分延迟/丢包情形，不能单独证明乱序、重放、重复和跨重启旧报文都被正确识别。16位回绕边界还应使用独立参考模型验证。来源#1596。
5. 主循环在无新报文时保留先前有效的`robot_command_msg`，并存在明确的命令staleness TODO；控制任务另有“staleness/lost pkg”等TODO。因此“连续没有收到新命令”目前主要通过序号差间接暴露，而不是由独立的命令年龄watchdog处理。来源#1595。

### C. UDP读取预算与movejSync刷新

1. `readData`每轮最多调用两次`readDataOnce`；后者以`sioGet`读取固定长度缓冲区，读满才视为新数据，正数但长度不匹配则报错。该逻辑没有在源码层面排空所有待处理数据报；当接收队列积压超过每周期读取预算时，可能跨周期继续处理队列中的旧命令。队列深度、sioGet是否严格非阻塞、零字节/错误码含义和溢出策略需目标VAL3/CS9验证。来源#1597。
2. 位置控制函数注释定义`movejSyncState()==1`为“上一条命令未及时刷新”；实际分支仅保留注释掉的日志，没有将该状态设为错误，也没有在该分支显式停止或锁存。故不能把movejSync内部刷新超时状态等同于应用层已执行安全停止。来源#1598。
3. 位置控制函数每次有效调用都会执行`$movejSync(l_jJointPositionCmd)`，但刷新周期是否稳定、VAL3内部超时边界、状态1持续多久、进入状态1后是否仍可能保持旧目标以及`movejSyncEnd`/停止动作的物理响应均需在受控环境验证。来源#1598。

### D. 风险与范围

- **P1｜实时性未建立证据闭环。** 4 ms是任务创建参数；没有周期抖动、执行时间、激活延迟、最大连续overrun和负载下统计。overrun目前只计数/日志，不见自动停机门槛。
- **P1｜命令新鲜度是序号代理量。** 序号差阈值受实际任务周期影响，不等价于墙钟超时；staleness TODO仍在，重复/乱序/重放及控制器重启后的序号epoch策略不完整。
- **P1｜接收队列积压风险待验证。** 每周期读取上限为2；如VAL3 socket队列保留多个数据报，控制任务可能处理滞后命令。不得在未确认sioGet队列语义前断言一定会积压或一定会丢弃旧包。
- **P1｜movejSync刷新超时没有应用层故障动作。** 状态1分支被注释；是否由底层运动系统自行停止及其停止等级/时间未知。
- 本节为固定源码静态审查；没有证明CS9实际4 ms调度失败，也没有复现丢包、乱序、队列积压、movejSync状态1或机器人持续运动。

### E. 修复与验收要求

1. 为控制任务增加周期/执行时间/激活延迟的可导出测量：记录每周期开始时间、执行时间、周期误差、最大/连续overrun、CPU负载和任务优先级；在额定负载与故障注入下定义可量化门限。
2. 将overrun从日志计数升级为明确策略：区分单次偶发与连续超限；按风险分析定义触发STOP、故障锁存、禁止自动恢复和人工复位的条件。不要仅依赖普通日志。
3. 引入独立单调时钟命令年龄watchdog，并校验命令序号单调性、重复、乱序、回绕和会话epoch；明确控制器/ROS任一侧重启后的重新同步握手。
4. 明确每周期UDP读取策略：排空队列并只采用最新有效命令，或通过协议/缓冲策略保证有界队列延迟；记录丢弃数量、最大队列深度和命令年龄。通过目标VAL3手册与CS9测试确定`sioGet`行为。
5. 对`movejSyncState()==1`定义正式策略：将刷新超时转为明确故障，执行经验证的停止路径并等待停止确认；不得只留注释。记录状态-2/-1/0/1/2的转移和恢复条件。
6. 明确控制周期预算：VAL3任务周期、状态编码/UDP发送、接收处理、运动命令刷新和系统其他任务的WCET预算；4 ms周期达不到时必须进入经验证的安全降级状态。

### F. 新增可执行验收矩阵

| ID | 场景 | 必须结果 | 当前证据/缺口 |
|---|---|---|---|
| RT-01 | CS9空载、额定负载、最大诊断/通信负载连续运行 | 记录周期抖动、WCET、激活延迟、overrun总数及连续次数；满足批准的实时预算 | 仅有4 ms配置；未测量 |
| RT-02 | 单次/连续任务overrun | 按批准策略告警、STOP或锁存；不得仅清标志并继续无限运行 | 当前只日志并累加nOverruns；未测试 |
| RT-03 | monitor speed低于100%启动 | 按安全策略拒绝启动或进入受控降级，不静默继续 | 当前仅警告；未测试 |
| RT-04 | 运动中命令停止更新、延迟和丢包阶梯 | 以单调时钟年龄触发有界停止；停止时间满足风险评估 | 现有序号阈值按名义4 ms估算；staleness TODO |
| RT-05 | 重复、乱序、回绕、重放及ROS/CS9重启后旧序号 | 严格拒绝旧会话/重复命令，合法回绕不误报，完成重新同步后才允许运动 | 当前未见完整单调序号/epoch策略 |
| RT-06 | 每周期0/1/2/3+数据报、突发队列积压 | 明确读取/丢弃策略，禁止执行过期排队命令；队列延迟有上界 | 每周期最多2次sioGet；队列语义未实测 |
| RT-07 | 强制触发movejSyncState()==1 | 明确报告刷新超时并进入经验证的停止/锁存路径 | 当前分支仅注释；未触发验证 |
| RT-08 | 控制任务在4 ms预算附近增加CPU/日志/通信负载 | 证明周期仍满足预算或进入预定义安全状态 | 未执行负载测试/VAL3监测 |

### G. 验证边界

本轮仅审查固定commit中的VAL3源码与随附README；未运行VAL3编译器、未连接CS9、未测量真实周期/overrun、未做UDP丢包乱序/队列注入、未触发movejSync状态1、未执行HIL或实机停止时间测试。Stäubli仍为静态审查未验收。


## 9.3.22 VAL3错误恢复、控制器/ROS重启与运动重新授权（2026-11-07）

本节固定审查ICube上游commit `bd658e2d266e315d2ee35f985fb352ea88306b79`（当前公开main解析到该提交）。检查VAL3的`start.pgx`、`stop.pgx`、`controlTask.pgx`、消息头/命令解码、`updateState.pgx`，以及ROS 2侧HardwareInterface和RobotDriver。结论：正常启动默认STOP，控制器安全状态参与运动许可；但应用层错误恢复没有明确的故障锁存/人工确认协议，也没有会话epoch/重连握手把新命令绑定到当前控制器任务实例。

### A. VAL3任务启动/停止行为

1. `start.pgx`启动时调用`stopMove()`、`resetMotion()`、`autoConnectMove(true)`，然后将4 ms周期任务`controlTask`创建运行。控制任务初始化时将本地命令模式与上一命令模式都设为1（STOP/Idle）、命令消息设为默认STOP但无效，并清零本地序号。启动程序没有独立的通信会话ID、随机挑战值或要求操作员确认后才接受第一条新运动命令的步骤。来源#1599–#1600。
2. `stop.pgx`调用`stopMove()`、`resetMotion()`并清空控制socket buffer。它没有记录可跨任务重启保留的故障锁存/授权状态；该程序也不能据此证明控制器掉电、VAL3应用停止或进程退出时的实际停止响应。来源#1600。

### B. 应用层错误处理存在“清错后重新接收”路径

1. `controlTask.pgx`在错误处理块中调用停止函数（对位置控制模式调用`stopJointPositionControl`）、随后调用`stopMove()`和`resetMotion()`；将命令类型和当前模式置为0（Invalid/Error），随后将`l_bError`清为false、清零状态序号和延迟、将`l_bControlActive`置false、将命令标记为无效，并调用`resetControlSocket`清理接收缓冲区。来源#1601。
2. 紧接着的源码注释明确写着“TODO: add delay (e.g., 1000ms) before accepting new commands?”；因此当前代码没有实施该等待，也没有操作员ACK、故障原因确认、授权令牌或独立恢复状态机。不能将软件错误清零视为安全故障已排除。
3. 错误后`l_nCmdMode`设为0，并在循环尾部赋给`l_nPreviousCmdMode`。下一轮若直接收到非STOP运动模式，模式转换检查会因前一模式0、当前运动模式非1而再次拒绝并触发错误；先收到STOP模式1，才会使后续从STOP到运动模式的转换满足该检查。该行为是代码控制流推导，尚未在VAL3上运行验证。
4. 对连续旧运动数据报，服务器错误处理会清空socket buffer，但没有会话epoch/nonce验证；清空瞬间之后抵达的延迟旧数据报是否会被接受，取决于UDP到达时序和socket队列行为，需故障注入确认。来源#1601–#1603。

### C. 协议层缺少会话绑定

1. 消息头包含magic number、protocol version、message type、16位sequence number和payload size；解码检查magic number与协议版本，但没有controller boot ID、VAL3 task generation、session nonce或握手阶段字段。来源#1602。
2. 命令解码成功后将`bIsValid=true`；未见在该函数中验证命令序号必须比上次有效序号更新，也未见重复命令拒绝或重放窗口。序号差计算和负值检查在控制循环其他位置，不能替代会话身份验证。来源#1601–#1603。
3. VAL3控制任务启动和应用层错误恢复都会把服务端序号归零；ROS Driver的`reset_data()`也将本地最后有效序号与缓存状态序号置零。两端均有重置行为，但没有跨重启epoch区分“新会话的序号0”与“旧会话延迟报文”的协议字段。来源#1601–#1603、#1606。

### D. CS9安全状态与应用层运动授权的边界

1. `updateState.pgx`读取`esStatus()`；任何非零安全状态都令`bEStopped=true`，进而令`bMotionPossible=false`。状态1表示等待Safety Restart，状态2/3分别标识SS1/SS2，状态4表示等待WMS重启。该逻辑为应用层运动许可提供了控制器安全状态门控。来源#1604。
2. ROS 2的`perform_command_mode_switch()`在切换到关节位置模式时检查`state_msg_.error_state`和`state_msg_.motion_possible`；`operation_mode_status!=0`目前只告警。Safety Restart状态通常会通过VAL3的`motion_possible=false`间接拒绝位置模式，但没有单独对`wait_for_ack`字段做授权状态机。来源#1605。
3. `on_activate()`只把ROS侧`current_control_mode_`设为STOP，不在该回调中发送STOP或等待控制器STOP确认；后续write周期才会发送当前STOP模式命令。不能将Lifecycle activate成功视为机器人已确认停止。来源#1605。
4. `RobotDriver::connect()`建立UDP接口并等待有效状态报文、检查协议版本；没有控制器启动epoch/会话挑战或显式“STOP确认后允许控制”握手。连接阶段诊断报文读取仍是TODO占位。来源#1606。

### E. 风险定性

- **P1｜应用层故障未锁存。** 错误处理执行停止动作后清除`l_bError`，没有持久故障原因、人工ACK或明确恢复许可状态。正常Safety Restart仍受CS9安全状态控制，但不能覆盖全部软件/通信故障。
- **P1｜恢复延迟/复位步骤未定义。** 1秒恢复等待是TODO；错误模式0会影响后续命令模式转换。需要定义明确的STOP确认、清错、序号同步、人工授权和重新使能顺序。
- **P1｜重启会话未绑定。** 消息头没有控制器启动ID或session nonce，序号重置后不能从协议层证明数据报属于当前会话；socket清空不能替代会话认证。
- **P2｜Lifecycle激活与机器人停止确认脱节。** ROS侧activate仅改软件模式，未在回调中发送STOP并等待控制器状态回读。
- 本节未证明任何实际机器人会在上述路径下意外运动；旧数据报被接受、故障后恢复到运动的具体时序均属于待验证风险，不是已复现漏洞。

### F. 修复与验收要求

1. 建立显式控制状态机：BOOT/UNSYNCED → STOP_REQUESTED → STOP_CONFIRMED → FAULT_LATCHED或READY_FOR_OPERATOR_ACK → SESSION_SYNCHRONIZED → MOTION_ENABLED。所有通信错误、协议错误、控制周期超限、机器人侧运行时错误均进入故障锁存；不能在同一错误处理块中无条件清除故障。
2. 错误恢复必须要求明确的操作员/上层安全监督授权（按系统风险评估确定），并且先确认机器人静止、Safety Restart完成、驱动上电状态有效，再进行会话握手；收到新运动命令本身不得等同授权。
3. 协议增加控制器启动epoch或随机session nonce；每条命令携带会话标识、单调序号和可验证年龄。控制器/ROS任一端重启、通信恢复、错误复位时先完成握手，旧epoch报文一律拒绝。
4. 错误恢复时先发送STOP并等待控制器状态回读确认；失败/超时保持锁存，不清除故障；明确VAL3任务崩溃、应用停止、控制器重启和网络断开时由哪一层独立执行停止/看门狗。
5. 把模式0（ERROR）与模式1（STOP/IDLE）分离成有定义的状态转移；补齐错误后必须STOP确认的转移，不依赖“下一条客户端STOP刚好先到”的隐含行为。
6. ROS 2 on_activate前执行STOP请求和状态确认；命令模式切换同时检查错误锁存、motion_possible、wait_for_ack、安全状态和新会话状态；任何状态未知或过期均拒绝使能。

### G. 新增故障注入/状态机验收矩阵

| ID | 场景 | 必须结果 | 当前证据/缺口 |
|---|---|---|---|
| RS-01 | VAL3启动、停止、重启及任务异常退出 | 启动默认为STOP；异常退出由独立安全机制停止；恢复前不得直接运动 | 仅静态见start/stop动作，未做控制器测试 |
| RS-02 | 运动中触发通信/协议/overrun错误 | STOP请求后进入持久故障锁存，等待停止确认和授权 | 当前清除l_bError；未见ACK锁存 |
| RS-03 | 错误后直接发送旧运动命令 | 必须拒绝；不能靠序号恰好对齐恢复 | 模式0转换会拒绝直接切换；未实测 |
| RS-04 | 错误后STOP→重新同步→授权→运动 | 只有完整流程成功后才能进入运动模式 | 目前无显式会话/授权握手 |
| RS-05 | 控制器重启后网络延迟注入旧epoch报文 | 所有旧会话命令拒绝 | header无boot ID/session nonce |
| RS-06 | ROS 2进程重启、驱动重新connect | 先取得新鲜状态、STOP确认、完成同步；不得继承旧控制授权 | connect等状态并校验协议，但无STOP确认/epoch握手 |
| RS-07 | ROS Lifecycle deactivate/cleanup/activate | STOP-before-disconnect；activate必须等待停止确认和授权 | on_activate仅改本地模式；未验证 |
| RS-08 | Safety Restart / wait_for_ack / SS1 / SS2 | 安全状态未恢复时拒绝运动；恢复后仍要求应用层会话同步 | motion_possible间接门控；无独立授权状态机 |
| RS-09 | UDP延迟旧包在clearBuffer之后到达 | 旧序号/旧epoch拒绝，且记录丢弃原因 | 当前无epoch；到达时序未注入 |

### H. 验证边界

本轮仅审查固定commit的VAL3与ROS 2源码；未运行VAL3编译器、未运行ROS 2构建/单测、未连接CS9、未执行网络重启/延迟旧包注入、未测STOP确认时间或实机恢复路径。不能据此宣称机器人存在已复现的意外运动漏洞，也不能宣称其恢复流程满足工业安全要求。


## 9.3.23 VAL3停止函数、运动授权恢复与自动连接运动纵深审查（2026-11-07）

### A. 审查基线与范围

- 上游固定基线：`ICube-Robotics/staubli_driver_ros2` commit `bd658e2d266e315d2ee35f985fb352ea88306b79`。
- 审查文件：`Control/stopJointPositionControl.pgx`、`Control/stopJointVelocityControl.pgx`、`Control/updateJointPositionControl.pgx`、`controlTask.pgx`、`start.pgx`、`stop.pgx`、`updateState.pgx`。
- 参考资料：公开VAL3参考手册（来源#1612）。手册版本较旧，具体CS9固件/VAL3版本适用性需Stäubli书面确认；此处仅将其作为指令语义线索，不替代目标控制器手册。

### B. 停止调用链的实际语义

1. **位置控制停止：** `stopJointPositionControl()`只在`movejSyncState()!=-1`时调用`$movejSyncEnd()`，随后无条件设置`x_bError=false`。函数没有等待movejSync停止完成、读取静止状态或确认控制器停止ACK的逻辑。来源#1607。
2. **速度控制停止：** `stopJointVelocityControl()`直接调用`resetMotion()`，随后无条件报告无错误。该函数存在不代表速度控制可用；同一上游README明确当前仅支持位置控制、速度控制尚未实现。来源#1608及上游README。
3. **普通STOP分支：** `controlTask`根据上一控制模式调用对应stopJoint函数，随后执行`stopMove()`再执行`resetMotion()`。同一调用对也出现在应用错误处理和任务循环退出cleanup中。来源#1609。
4. **错误停止分支：** 位置模式错误时先调用`stopJointPositionControl()`，随后再次执行`stopMove()/resetMotion()`。函数返回只表示代码路径继续，并没有构成“控制器已确认停止”或“机器人已静止”的证据。
5. **VAL3指令的异步性质：** 参考手册明确`stopMove()`和`resetMotion()`均立即返回，VAL3任务不等待机械臂停止。`resetMotion()`会取消已排队运动并重置运动ID；同时，如果程序运动授权此前被`stopMove()`暂停，`resetMotion()`会恢复该授权。来源#1612。
6. **重要组合效应：** 当前代码连续调用`stopMove(); resetMotion()`，因此不能将前一个`stopMove()`当作持续保持的运动禁止锁存；紧随其后的`resetMotion()`按手册语义会恢复程序运动授权。应用层命令模式仍可阻止控制任务主动下发新运动命令，但它不是独立于VAL3运动授权的安全锁，也不等于需要操作员确认的故障锁存。
7. **位置控制状态回报：** `updateState.pgx`以`!isSettled()`生成`bInMotion`，并通过`$getJntSpeedCmd`读取关节速度命令。它可作为软件状态监督信号，但不能仅凭这些字段认定独立安全静止监测、制动器状态或安全控制器已确认停止。来源#1611。

### C. 自动连接运动与重新启动风险

- `start.pgx`在应用启动时执行`stopMove()`、`resetMotion()`，随后显式调用`autoConnectMove(true)`，再创建控制任务。来源#1610。
- VAL3参考手册描述：远程模式下，当机械臂偏离原运动轨迹超过允许漂移范围时，启用autoConnectMove可使连接运动自动执行；默认通常为手动连接。手册还提示，急停场景下恢复可能存在自动重新启动运动的情形，不能把autoConnectMove配置视为急停后的人工重新授权屏障。来源#1612。
- 因此，启动时启用自动连接运动必须与机器人模式、Safety Restart、程序运动队列、轨迹状态、操作员确认和安全配置一起审查。当前代码未展示独立的应用层“安全复位完成 + 操作员授权 + 新会话握手 + 新轨迹提交”完整状态机。
- 这并不证明目标CS9必然在急停复位后自动运动；具体行为受控制器版本、运行模式、安全选件、轨迹状态和现场配置影响，必须在制造商认可的安全测试方案中验证。

### D. 停止类型必须分层，不得混称

| 层级 | 本审查中的含义 | 不能据此推断 |
|---|---|---|
| ROS/UDP STOP请求 | 上位机发出STOP数据报或切换本地命令模式 | 控制器已收到/执行 |
| VAL3应用停止调用 | movejSyncEnd、stopMove、resetMotion被执行 | 机械臂已停止、停止时间合格 |
| 控制器运动停止状态 | 控制器/驱动反馈表明运动队列或运动指令已停止 | 安全功能已触发或安全静止已确认 |
| 普通停止/程序停止 | 应用层停止运动命令 | 等同SS1/SS2或急停 |
| Safety Stop / SS1 / SS2 | 控制器安全系统报告的安全状态 | 仅凭ROS应用状态字段即可证明安全功能达到PL/SIL |
| Emergency Stop | 独立急停链触发的安全功能 | 可由普通UDP STOP、ROS lifecycle或VAL3程序调用替代 |

特别是，`stopMove/resetMotion`是程序运动控制指令，不是急停回路；ROS STOP是通信/应用层命令，也不是安全功能。SS1/SS2/E-stop的停止类别、停止时间、制动器动作和安全完整性必须以目标控制器安全手册、选件证书、风险评估和现场验证为准。

### E. 断网、任务退出和控制器异常时的安全边界

- **ROS进程/网络中断：** ROS侧STOP数据报可能无法送达；VAL3现有命令staleness仍有TODO（§9.3.21）。是否由CS9 socket超时、VAL3任务看门狗或控制器安全功能独立触发停止，当前公开代码不足以证明。
- **VAL3控制任务异常退出：** 正常while循环退出路径有stopMove/resetMotion，但异常崩溃、任务被强制终止或控制器资源异常时，不能假设cleanup代码必然执行。必须确认CS9任务调度/任务异常处理和独立安全监控的行为。
- **VAL3应用正常stop：** `stop.pgx`调用stopMove/resetMotion并清空socket buffer，但不等待静止；清空队列也不是对后续迟到报文或新会话的身份认证。
- **控制器重启/掉电：** 本次静态审查未取得目标CS9的掉电、制动器、抱闸、再上电运动恢复配置资料。不能推断机器人一定安全停住，也不能推断一定自动恢复运动。
- **独立安全链：** 急停、安全门、使能装置、SS1/SS2、安全速度/区域等功能是否独立于ROS/VAL3软件生效，必须按具体控制器SKU、安全模块、机器人配置和接线图核验；不能把应用层stop函数纳入安全功能信用计算。

### F. 修复与设计要求

1. 把“STOP请求”“停止执行中”“控制器已确认停止”“机器人静止已确认”“故障锁存”“允许重新运动”建成互斥、可追踪状态，不得用一个STOP枚举同时表达。
2. 不得在STOP路径中无条件以`resetMotion()`恢复运动授权后，就把应用命令模式视为安全锁。设计需明确何时允许恢复程序运动授权；恢复前必须经过静止确认、Safety Restart状态确认、轨迹清理/重新规划和操作员授权。
3. 评估并默认关闭`autoConnectMove(true)`，除非具体应用风险评估证明自动连接运动安全且有受控授权；急停恢复不得自动恢复旧轨迹，除非制造商定义的安全行为与系统风险评估明确允许。
4. 为位置控制停止增加movejSync结束状态超时、控制器状态回读和静止稳定时间；停止超时进入锁存故障，不可把函数无条件返回false/true之外的状态简化为成功。
5. 对速度控制停止路径明确标注未实现/不可用，避免将当前占位函数误当作已验证的速度控制停止实现。
6. 获取目标CS9版本对应的VAL3指令手册、安全功能手册、socket超时与任务异常行为资料；验证掉线、应用崩溃、控制器重启和安全复位时的实际响应。

### G. 新增停止链路故障注入与验收矩阵

| ID | 场景 | 必须结果 | 当前状态 |
|---|---|---|---|
| ST-01 | 位置控制运行中发送STOP | 有界停止请求、控制器回读、静止稳定判定；超时锁存 | 源码仅movejSyncEnd/stopMove/resetMotion；未实测 |
| ST-02 | movejSyncEnd未完成或返回异常 | 不得无条件报告停止成功；进入故障锁存 | 当前函数无等待/状态确认 |
| ST-03 | STOP路径连续执行stopMove/resetMotion | 明确resetMotion恢复运动授权的时序与后果；未获授权前不得新运动 | 静态调用链确认，目标控制器待验证 |
| ST-04 | ROS/UDP断网、数据包丢失 | CS9独立watchdog按安全需求停止；恢复后旧命令拒绝 | staleness仍有TODO，未做故障注入 |
| ST-05 | VAL3任务异常终止/应用被强制停止 | 由独立控制器安全机制进入定义的安全状态；不能依赖cleanup | 未取得任务崩溃测试证据 |
| ST-06 | 控制器重启/掉电/再上电 | 不自动执行旧轨迹；制动器/安全状态和重新授权按定义验证 | 未在CS9/HIL测试 |
| ST-07 | E-stop/SS1/SS2触发与Safety Restart | 区分安全停止与普通STOP；安全复位后仍按风险评估授权运动 | 仅静态读到esStatus映射；未实测 |
| ST-08 | autoConnectMove(true)且轨迹偏离/急停恢复 | 验证是否自动连接/重启；未经授权不得产生意外运动 | 手册揭示需重点验证；未做目标控制器测试 |
| ST-09 | isSettled与实际机械静止对照 | 建立速度/位置/制动器独立证据和静止稳定时间 | 软件状态映射已读；未做测量 |

### H. 验证边界

本轮只对固定commit源码和公开VAL3参考手册做静态交叉审查。未运行VAL3编译器、未执行ROS构建/单测、未连接CS9、未执行急停/SS1/SS2/断网/任务崩溃/掉电/自动连接运动故障注入，也未测量停止时间、静止稳定性或制动器动作。公开手册版本与目标CS9固件适用性尚待Stäubli确认。本节不构成安全认证、风险评估签署或实机工程验收。


## 9.3.24 CS9独立安全链、停止类别与断电供电边界审查（2026-11-07）

### A. 审查依据与适用边界

- 控制器资料：Stäubli《Contrôleur CS9 Manuel d'instruction》，文档号D.280.940.01-F，标注日期2020-03-03、版权2019；来源#1613–#1616。
- 本手册在前言明确指出：完整描述机器人还需要CS9安全手册、具体机械臂手册、电气图纸和软件手册。因此本节只能建立控制器级安全功能框架，不能代替目标机器人型号、CS9硬件修订、SRC/安全程序版本、接线和选件的逐项核对。
- 手册若干参数以默认安全程序200.x为前提；若现场使用定制安全程序、维护插头、LLI/uniVAL选件或不同固件，必须重新确认实际行为。

### B. 手册定义的停止类别：应用停止不等于安全停止

手册§6.2给出停止原因与停止行为的区分：

| 触发来源 | 手册描述的停止行为 | 本项目审查结论 |
|---|---|---|
| 应用程序执行`stop()` | 应用停止程序，沿轨迹停止（SS2） | 应用层停止动作；不能与急停等同 |
| `stopMove()`指令/释放运动保持键 | 沿轨迹停止，保持机械臂上电（SS2） | VAL3运动控制停止，不是独立急停输入 |
| MCP停止/用户安全停止 | 受控安全停止（如SS1，取决于输入和配置） | 由CS9安全控制器执行，需安全复位 |
| 控制器逻辑故障/安全故障 | 手册列为仅依靠制动器停止 | 不能假设VAL3 cleanup或ROS STOP仍能执行 |
| 主电源故障 | SS0 | 断电故障路径，不等于软件受控减速停止 |
| 驱动硬件故障 | 主动制动与制动器；故障轴可能仅由其制动器停止 | 轴级响应可能不同，必须结合驱动/机械臂手册 |
| 硬停止 | 主动制动与制动器，相关轴使用硬制动 | 需按具体轴和机器人型号验证 |

来源#1613。特别注意：表中`stopMove()`列在普通运动停止类别下，不应将其误认为用户安全输入触发的SS1。ROS数据报STOP、VAL3的stopMove/resetMotion、MCP急停、J100安全输入是不同层级的事件。

### C. CS9具备独立于ROS/VAL3应用层的安全控制资源

1. 控制器包含专用RSI9安全接口；手册描述J100具有可配置的双通道用户安全输入，J102具有安全输出，J101连接WMS9工作模式选择与安全重启确认。
2. 默认安全程序200.x下，USIA为急停输入；USIB/USIC/USID为按手动/自动模式或始终有效的保护停止输入。输入通道使用测试脉冲检测短路等故障。
3. 手册称默认配置下用户急停/保护停止会触发SIL3/PLe、Category 4安全停止功能；急停后由安全控制器要求重新启动确认。保护停止的重新启动行为则可能由应用承担，具体取决于功能配置。
4. 手册列出SS1、SS2、STO、SBC和SOS等功能；默认安全程序200.x的SS2预定延迟为0.5 s。该值不是任意停止路径的统一响应时间，也不能替代具体机械臂的停止时间/距离数据。
5. 默认程序的USI最大停止时间参数在手册表中为532 ms；这不是整机从任意速度到静止的总时间。实际停止距离和时间仍需按机械臂型号手册、负载、速度、安装和现场安全配置计算。

来源#1614–#1615。上述安全等级和功能仅能按手册所述的特定配置与假设理解，不能据此直接给集成后的机器人单元签发PL/SIL结论。

### D. 断电、独立24V与安全状态保持的边界

- 手册§3.1.5.5明确：控制器断电时，急停状态不再有效，相关安全输出被强制到急停状态。
- 对于要求控制器主电源断开后仍保持急停链状态的系统，手册允许通过J213为安全控制器提供独立24V PELV/SELV供电。
- 手册§5.2进一步说明外部24V供电的接口接线要求，并明确警告：如果机械臂带电运动期间外部24V也丢失，机械臂可能下落，因为这路外部供电的信号不由CPU管理。
- 因此，“独立24V”是保持特定安全控制器/急停链状态的设计选项，不等于控制器运动控制、驱动器和制动器都有独立冗余供电，也不自动保证掉电时机器人保持当前位置。
- 必须核对主电源失效、逻辑24V失效、制动器24V失效、外部安全24V失效的组合故障，以及末端负载/重力轴在失电时的下落风险。不能仅通过ROS状态字段判断这些电源域的健康状态。

来源#1616及控制器手册§2.2.2、§3.1.5.5、§5.2。

### E. 对本项目现有ROS/VAL3集成的影响

1. **网络断开：** ROS STOP不能保证送达。独立安全输入链在正确接线和配置时可由安全控制器响应，但网络断开本身是否映射为安全停止，当前代码和本手册摘录均未证明。需要单独设计通信watchdog，不能把普通UDP超时假定为安全功能。
2. **VAL3任务崩溃：** 应用cleanup可能不执行；CS9手册将控制器逻辑故障列为制动器停止路径，但没有证据表明普通VAL3任务异常必然被识别为该类控制器逻辑故障。必须通过Stäubli确认任务故障监控边界并进行认可的故障注入。
3. **ROS进程崩溃：** 不应依赖ROS生命周期回调或析构函数完成停止。系统必须由CS9端通信监控和独立安全回路覆盖其故障模式；当前上游应用协议的命令staleness仍有TODO（§9.3.21）。
4. **控制器逻辑/安全故障：** 手册给出的停止响应可能是仅依靠制动器停止，不能套用应用层受控减速的假设；必须按机器人型号和载荷确认该故障停止的制动距离、轴间差异和下落风险。
5. **主电源故障：** 手册分类为SS0；不得宣称普通STOP或VAL3轨迹停止能够覆盖主电源故障。
6. **安全复位：** 急停解除并不自动等于允许运动；手册要求安全重启确认。ROS on_activate设置本地STOP既不执行安全复位，也不构成操作员授权。
7. **维护插头：** 手册说明维护插头会禁用来自单元的USIA/USIB/USIC/USID安全停止信号。必须纳入现场配置盘点、钥匙/权限管理和投产前检查，严禁把维护插头状态当作正常生产安全链。

### F. 需要向Stäubli/系统集成方取得的证据

- 目标CS9序列号、硬件修订、SRC版本、RSI9版本和安全程序编号/校验值。
- 目标机器人型号的安全手册、停止时间/距离曲线、重力轴制动器数据和驱动故障处理说明。
- 当前安全配置导出文件、J100/J101/J102/J213实际接线图、WMS9/MCP/维护插头状态。
- 主电源、逻辑24V、制动器24V、RSI9外部24V的电源域图及掉电时序。
- ROS/VAL3通信丢失、任务异常、控制器CPU/安全控制器故障各自的检测机制、诊断码和安全响应定义。
- 安全输出与单元其他设备（夹具、输送线、外部轴等）的联锁方案及复位顺序。
- 由合格安全工程师批准的风险评估、PLr/SIL目标、验证计划和验证记录。

### G. 新增安全链故障注入/验收矩阵

| ID | 故障/配置场景 | 必须验证的结果 | 当前证据状态 |
|---|---|---|---|
| SC-01 | ROS进程强制终止/网线断开 | 通信watchdog按风险定义停止；独立安全回路仍可触发 | 代码未证明，未注入 |
| SC-02 | VAL3控制任务异常终止 | 识别任务故障并进入定义的安全状态；不依赖cleanup | 未确认任务异常是否等同控制器逻辑故障 |
| SC-03 | MCP急停、USIA急停、USIB/C/D保护停止 | 对照实际安全程序验证停止类别、复位锁存和输出状态 | 手册描述默认程序，现场配置未核 |
| SC-04 | 控制器主电源丢失 | 验证SS0/制动器响应、轴下落、外部设备联锁 | 未实测，需机器人型号资料 |
| SC-05 | 仅控制器主电源断开，外部安全24V保持 | 急停状态链是否保持有效、输出状态是否符合配置 | 手册支持该选项，现场接线未知 |
| SC-06 | 运动中外部安全24V丢失 | 验证安全状态、制动器和重力轴响应；不得出现危险下落 | 手册明确警告可能下落，严禁未经批准自行试验 |
| SC-07 | 控制器逻辑故障/安全故障 | 验证制动器停止路径、停止距离和诊断记录 | 手册仅给类别描述，目标配置待确认 |
| SC-08 | 维护插头安装/移除 | 验证用户安全输入是否被禁用、权限和复产检查是否有效 | 手册说明会禁用单元侧USI输入，现场待核 |
| SC-09 | 安全停止后仅清除触发条件、不做Restart ACK | 机器人必须保持安全停止 | 手册明确要求安全重启确认，现场待验证 |
| SC-10 | 不同停止路径对比 | 分别记录ROS STOP、VAL3 stopMove、MCP stop、USI、主电源故障的时间/距离/输出状态 | 尚未测量 |

### H. 结论与验证边界

- 已有充分手册依据说明CS9具有独立于ROS/VAL3应用层的安全控制接口和安全停止功能；但这些功能能否覆盖当前机器人单元的危险，取决于现场安全程序、输入接线、模式选择、外部电源、机械臂制动器和单元集成。
- 不能推断“ROS/VAL3崩溃必然触发CS9安全停止”；也不能推断“主电源或外部24V丢失时机器人一定保持静止/当前位置”。
- 本节仅审查2020版控制器说明书和固定上游源码，没有目标CS9配置导出、现场电气图、机器人型号安全手册或实机故障注入。未执行VAL3/ROS构建、HIL或安全功能验证；不构成PL/SIL评估、安全认证或工程验收。


## 9.3.25 ROS/VAL3安全状态映射、监督语义与运动授权门控审查（2026-11-07）

### A. 审查基线与文件范围

- 上游仓库：`ICube-Robotics/staubli_driver_ros2`，固定commit `bd658e2d266e315d2ee35f985fb352ea88306b79`；本轮重新读取GitHub `main` 分支，HEAD仍为该commit（分支提交日期2026-07-03），未发现相对固定基线的新源码提交。
- 核对文件：`staubli_hardware_interface.cpp/.hpp`、`messages.hpp/.cpp`、`types.hpp`、VAL3 `updateState.pgx`、`encodeRobotStateMsg.pgx`。
- 代码证据来源#1617–#1620。该审查是源码静态追踪，不代表CS9安全功能已实测。

### B. VAL3侧安全状态原始映射

1. `updateState.pgx`通过`esStatus()`读取安全状态，注释列出：0=无安全停止、1=等待Safety Restart、2=SS1、3=SS2、4=等待WMS重启；代码令`bEStopped = (nSafetyStatus != 0)`，即把所有非零安全状态统一折叠为EStopped标志。
2. `bWaitAck`仅在`nSafetyStatus == 1`时为真。状态4（等待WMS重启）并不进入该标志，因此ROS导出的`wait_for_ack`不能代表所有需要工作模式/安全重启确认的情形。
3. `bMotionPossible`当前计算为`bDrivePowered && !bEStopped`。相邻一行曾考虑加入`nRobotStatus == 0`的模式状态条件，但该条件目前被注释。由此，自动模式下HOLD状态（注释中status=2）可能仍得到`motion_possible=true`，只要驱动上电且没有安全停止；此为逻辑推导，尚未在CS9验证。
4. `bBrakeReleased`直接等于`isPowered()`，是软件映射而非制动器位置/夹紧状态的独立传感器反馈；`bInMotion`来自`!isSettled()`，不等于安全静止检测。
5. `updateState.pgx`明确把`bInError`留给调用者填充；必须继续追踪`controlTask`的赋值路径，不能把它误认为由`esStatus()`自动覆盖。

### C. ROS侧导出与授权门控

- HardwareInterface将`operation_mode`、`operation_mode_status`、`safety_status`、`motion_possible`、`estop_pressed`、`wait_for_ack`等导出为ros2_control监督状态接口，故这些字段并非完全没有暴露给ROS。
- `update_state()`将`state_msg.estop_pressed`复制到接口；但VAL3上游的`bEStopped`代表任意非零安全状态，而不只是急停按钮被按下。因此接口名`estop_pressed`存在语义过宽/误导风险，消费者应优先读取原始`safety_status`并依据目标安全程序解释。
- `perform_command_mode_switch()`在切换到位置模式时检查缓存的`error_state`和`motion_possible`；`operation_mode_status != 0`只发出HOLD警告，不拒绝切换。结合VAL3未把HOLD纳入`motion_possible`的当前公式，HOLD状态的运动授权边界存在缺口。
- `write()`在非STOP模式下检查`error_state`及`control_state == INVALID`，没有在每次写周期重新检查`motion_possible`、`safety_status`或`wait_for_ack`。因此ROS侧安全门控主要发生在模式切换时，运行中状态变化的最终响应依赖VAL3侧控制函数和CS9独立安全链；不得把ROS导出状态接口视为安全控制器输入。
- 当前源码能证明状态字段被采集/导出且部分参与位置模式切换；不能证明其形成完整、实时、锁存、抗陈旧的安全授权状态机。

### D. 主要风险与工程要求

1. **HOLD误授权风险：** 将`nRobotStatus == 0`条件恢复与否必须由Stäubli工作模式语义确认；若HOLD不允许新运动，应在VAL3端拒绝运动命令，并在ROS切换及周期写入路径保持一致。
2. **等待重启语义不完整：** 区分Safety Restart与WMS Restart，不能只用一个布尔`wait_for_ack`表达所有安全重启状态；增加原始状态码、原因和模式上下文。
3. **E-stop命名失真：** 将`estop_pressed`重命名/拆分为`safety_stop_active`与`emergency_stop_active`（后者只有在控制器能明确提供独立语义时才可使用）；在无法区分时保留原始状态码并标注兼容字段。
4. **状态新鲜度与原子性：** 授权决策应绑定状态报文序号、单调时钟接收年龄和控制器启动epoch；状态过期、乱序、重复、未知枚举值或字段不一致时应fail-closed。
5. **逐周期门控：** 运动期间每个控制周期应对安全停止、驱动状态、工作模式、错误状态和授权epoch进行一致性检查；任何失效都应转入经定义的停止/锁存流程，但ROS软件门控不得替代CS9安全回路。
6. **状态接口消费契约：** 对`safety_status`和`operation_mode_status`建立有版本的枚举表、未知值策略、ROS诊断映射和单元测试，避免消费者仅订阅一个布尔字段。

### E. 新增静态审查与后续验证矩阵

| ID | 场景 | 验收要求 | 当前状态 |
|---|---|---|---|
| SI-01 | 自动模式HOLD（operation_mode_status=2）尝试切换位置控制 | 必须按目标CS9模式语义拒绝或明确允许；VAL3与ROS结果一致 | 发现status条件被注释；未实测 |
| SI-02 | 位置模式运行中从MOVE切换至HOLD | 下一控制周期按定义停止/拒绝新命令，不依赖旧模式切换快照 | ROS write未逐周期检查；未注入 |
| SI-03 | safety_status=4（等待WMS重启） | ROS监督状态明确显示待确认，禁止未授权运动 | 当前wait_for_ack只覆盖状态1 |
| SI-04 | safety_status=2/3（SS1/SS2） | 保留原始状态码，不将其误报为急停按钮按下 | 当前estop_pressed折叠全部非零状态 |
| SI-05 | isPowered与真实制动器状态不一致 | 不把brakes_released软件推导值作为制动器独立反馈 | 当前由isPowered映射；未实测 |
| SI-06 | 未知/新增安全状态枚举值 | 未知状态默认禁止运动并上报诊断 | 当前枚举/消费者兼容策略需补测 |
| SI-07 | 状态报文陈旧、重复或乱序时进行模式切换 | 过期或无序状态不得授权运动 | 需结合§9.3.17、§9.3.18测试 |
| SI-08 | ROS write运行中安全状态改变 | 证明VAL3端与CS9安全链在ROS门控缺失时仍按风险分析响应 | 未执行受控故障注入 |

### F. 结论与边界

本轮确认：ROS驱动确实导出多项CS9监督状态，并在位置控制模式切换时使用`error_state`和`motion_possible`；但VAL3的`motion_possible`计算没有纳入HOLD状态条件，`wait_for_ack`未覆盖WMS重启状态4，`estop_pressed`将所有非零安全状态折叠，ROS `write()`不逐周期复核完整监督状态。上述问题说明监督状态接口与安全授权状态机并非同一概念。

未运行VAL3编译、ROS构建/单测、CS9仿真、HIL或实机HOLD/SS1/SS2/WMS Restart故障注入；未验证具体控制器配置和安全程序。不能据此宣称已发生危险运动，也不能以本节代替安全评估、功能安全验证或Stäubli书面确认。


## 9.3.26 VAL3错误标志生命周期、位置命令门控与故障可观测性审查（2026-11-07）

### A. 审查范围与固定基线

- 上游仓库：`ICube-Robotics/staubli_driver_ros2`，固定commit `bd658e2d266e315d2ee35f985fb352ea88306b79`；本轮重新核验`main`仍指向该commit。
- 核对文件：VAL3 `controlTask.pgx`、`updateState.pgx`、`Control/updateJointPositionControl.pgx`、`Control/updateJointVelocityControl.pgx`、`Serialization/encodeRobotStateMsg.pgx`；ROS消息解码文件`messages.cpp`。
- 来源#1621–#1624。仅源码静态审查，未运行VAL3、CS9或ROS测试。

### B. bInError的真实来源与生命周期

1. `updateState.pgx`注释明确将`bInError`留给调用者填充；`controlTask.pgx`在每轮开始更新状态后，将局部变量`l_bError`赋给`robot_state_msg.robotState.bInError`。
2. `l_bError`并非从CS9安全控制器读取的独立控制器故障位。它主要由VAL3任务内部的软件处理错误置位：初始化/Socket错误、命令接收/解码错误、命令模式无效、序号延迟超限、模式转换非法、位置/速度控制更新错误等。
3. 状态报文在接收新命令、执行本周期运动控制和错误处理之前发送。因此本周期稍后发生的错误不会进入本周期已发出的状态报文。
4. 错误处理分支调用停止相关函数、`stopMove()`和`resetMotion()`，随后无条件清除`l_bError=false`、清理命令与通信状态，并重置Socket。若重置Socket再次失败则重新置位。源码没有显示持久故障锁存或要求操作员明确重新授权的完整状态机。
5. 由此，`in_error`更接近任务内部瞬态诊断标志，而不是可依赖的安全故障锁存。特别是运动更新函数本周期置错、同周期错误处理清零后，后续状态报文可能看不到该错误；需要用状态发送/错误发生的精确时序测试确认所有分支。

### C. 位置控制函数确实有软件门控，但边界有限

- `updateJointPositionControl.pgx`每次调用首先检查传入的`x_robotState.bMotionPossible`。若为false，则尝试停止位置控制、置`x_bError=true`并返回；随后检查命令有效性和类型，再进行关节范围检查，最后才调用`$movejSync()`。
- 这意味着位置控制执行路径存在基于VAL3当前周期状态快照的命令门控；应修正任何“VAL3端完全没有运动可能性检查”的概括。
- 但`bMotionPossible`本身仍由`isPowered()`和`esStatus()`派生，未纳入HOLD状态条件；它不是独立安全输入或安全认证状态。状态采集与命令执行之间仍有程序周期/执行时序，且没有证明CS9安全链失效时该软件门控仍可靠。
- 位置目标“离当前姿态足够近”的检查仍为TODO；关节范围检查存在，但不能替代速度、加速度、工作空间、奇异点、碰撞、工具/工件和工艺安全约束。
- `movejSyncState()==1`的命令未及时刷新分支仍只有注释；`==2`（因eStop、moveHold、stopMove等运动停止而锁命令）也未明确置错或采取额外动作。不得将其解释为明确的安全确认。
- 速度控制函数同样检查`bMotionPossible`，但安全限制检查是TODO，实际速度命令仍未实现；不能把该分支视为可用的速度控制实现。

### D. controlTask中的显式未完成项与停止/恢复问题

1. `controlTask.pgx`在状态发送前有三个明确TODO：机器人不应运动却在运动时执行hard stop、急停按下时的告警处理、运行时错误处理。
2. 命令staleness/lost packet检查仍是TODO；超时判断目前主要基于序号延迟阈值，而非墙钟命令年龄。
3. 位置控制调用遇到`bMotionPossible=false`会返回错误，随后控制任务进入通用错误处理；但通用错误处理会清错误标志并重置通信，且重启等待延迟仍是TODO。
4. 通用错误路径调用`stopMove()`和`resetMotion()`不等于独立安全停止或停止完成确认；这一点与§9.3.23、§9.3.24保持一致。
5. 本轮未证明所有错误分支均能在目标CS9上可靠停止，也未证明清Socket后是否存在自动重新接收命令、轨迹恢复或不需要操作员确认的路径；需要实际控制器版本和配置验证。

### E. 新增错误与门控验证矩阵

| ID | 场景 | 验收要求 | 当前状态 |
|---|---|---|---|
| ER-01 | 位置命令执行中出现安全状态，导致motion_possible=false | VAL3命令路径阻断后续movejSync刷新；停止行为与CS9安全链协调 | 源码有门控；未运行验证 |
| ER-02 | updateJointPositionControl本周期置bInError | 同周期及后续RobotState报文应可观测错误，不得被同周期清零吞掉 | 发现状态先发送、错误后处理；待时序测试 |
| ER-03 | 错误处理清除l_bError并重置Socket | 证明错误锁存、重连、重新授权和恢复动作均有明确策略 | 当前无持久锁存；重启延迟TODO |
| ER-04 | E-stop/SS1/SS2变化且机器人非预期运动 | 由目标CS9独立安全链完成风险分析要求的停止；软件诊断正确报告 | hard-stop相关处理为TODO；未故障注入 |
| ER-05 | movejSyncState=1或2 | 定义命令未刷新/运动被锁时的超时、停止和恢复策略 | 关键动作仍为注释 |
| ER-06 | 位置目标远离当前姿态或逼近约束边界 | 目标增量、速度/加速度、工作空间、奇异点与碰撞约束均有验证 | 目标接近性检查TODO；本轮未评估全部规划约束 |
| ER-07 | ROS/UDP断连、丢包、旧命令残留后重新连接 | 不接受旧会话命令，必须完成STOP确认和新会话授权 | staleness/lost packet与重新授权仍需专门验证 |
| ER-08 | velocity控制接口被请求 | 明确拒绝未实现路径，不得向用户/系统宣称可用速度控制 | 源码分支未实现；与README声明一致 |

### F. 结论与边界

本轮发现应作双向、准确表述：VAL3位置控制函数确实逐次检查`bMotionPossible`，在其为false时停止位置控制并返回错误；因此不是完全缺少VAL3软件门控。但该门控依赖软件计算的状态快照，且上游`controlTask`明确把非预期运动hard-stop、急停告警、运行时错误处理留作TODO。内部`l_bError`在状态发送后才可能置位，并在同周期错误处理后清零，存在故障状态未被ROS状态报文观察到的时序风险；源码没有证明它是持久故障锁存或重新授权机制。

未执行VAL3编译/仿真、ROS构建/单测、CS9受控安全状态注入、HIL或实机停止测试。不能将本轮静态发现解释为已发生事故或证明安全链失效，也不能替代风险评估、功能安全验证或Stäubli书面确认。


## 9.3.27 VAL3故障可观测性与现有测试覆盖边界审查（2026-11-07）

### A. 审查基线与证据

- 上游仓库：`ICube-Robotics/staubli_driver_ros2`，固定commit `bd658e2d266e315d2ee35f985fb352ea88306b79`；本节未改变固定源码基线。
- 核对文件：`val3/userapp/ros2_server/controlTask.pgx`、`Control/updateJointPositionControl.pgx`、`test/unit_tests/test_robot_driver.cpp`、`test/unit_tests/communication/test_rt_socket_interface.cpp`、`test/unit_tests/communication/test_message_serialization.cpp`。
- 来源#1625–#1628。仅进行源码与测试用例静态检查，未执行上游测试、VAL3编译或控制器验证。

### B. 现有测试实际证明的内容

1. `RobotDriverTest.ReadRobotStateTest`通过mock robot持续发送RobotState，设置100ms状态staleness timeout；停止mock发送并等待后，`read_robot_state()`应失败；重新启动mock发送后应恢复读取。这证明的是C++驱动对状态接收时间年龄的局部处理，不证明VAL3命令staleness watchdog或机器人停止。
2. `RTSocketSubscriberTest.ReceiveMessage`验证收到新帧后可重复读取缓存帧，重复读取时`new_message=false`，并在等待超过测试设定时间后报告缓存消息陈旧。这里的“重复读取缓存”不是网络重复/重放帧注入；它不覆盖相同序号UDP数据报重新到达时接收时间戳是否刷新。
3. `LostPackageDetection`覆盖普通递增序号中的跳号计数；未覆盖16位65535→0边界、乱序下降、重复序号、重放风暴或跨控制器重启序号重置。
4. `MessageSerializationTest`主要做当前C++实现的序列化—反序列化往返；不能验证C++与VAL3的逐字节互操作，也不能发现双方以相同错误方式编码/解码造成的对称性问题。

### C. VAL3故障路径与测试隔离边界

- `controlTask.pgx`在每轮先采集并发送RobotState，再读取/解码命令、执行位置控制，最后才处理本轮错误。因此由本轮命令解码或运动更新触发的`l_bError`，不会出现在本轮已经发送的状态帧中；是否在下一轮稳定可见还受错误分支清除时序影响。
- `updateJointPositionControl.pgx`对`bMotionPossible`、命令有效性、命令类型和关节范围有软件检查；但目标接近性仍为TODO，`movejSyncState()==1`刷新超时分支仍是注释，状态2的处理也未明确置错。
- `controlTask.pgx`将非预期运动hard-stop、急停告警和runtime error处理留为TODO；通用错误处理调用停止相关函数后清除`l_bError`并重置通信。当前所审C++测试没有执行VAL3程序，也没有模型化这套错误状态机。
- 因此测试覆盖应分层陈述：ROS/C++ socket和消息单元测试、VAL3静态代码检查、VAL3/SRS仿真、CS9控制器在环、真实机器人安全验证。前一层通过不能代替后一层。

### D. 新增测试规格（不代表已实现或执行）

| ID | 测试目标 | 建议方法与通过条件 | 当前状态 |
|---|---|---|---|
| OBS-01 | 本周期运动更新错误的状态可观测性 | 在受控VAL3测试程序中触发updateJointPositionControl错误；记录发送帧、错误置位、错误处理、下一帧状态的时间顺序，确认错误不会被静默吞掉 | 未实现/未执行 |
| OBS-02 | 错误清除与重新授权 | 注入可恢复通信错误；验证错误锁存、人工ACK/重新授权条件、会话epoch变化和旧命令拒绝 | 未实现/未执行 |
| OBS-03 | 命令陈旧与丢包 | 在VAL3侧分别注入静默、丢包、重复、乱序、延迟及恢复；按命令实际年龄而非只按序号差验证停止/锁存 | 未实现/未执行 |
| OBS-04 | movejSync状态转换 | 对-2/-1/0/1/2分别建立受控状态测试，验证命令刷新超时、停止完成和错误传播 | 未实现/未执行 |
| OBS-05 | ROS状态重复/重放 | 发送新序号、重复序号、旧序号、回绕和重启后序号重置的真实UDP数据报；重复/旧帧不得刷新有效状态新鲜度或覆盖最新状态 | 未实现/未执行 |
| OBS-06 | C++/VAL3跨语言黄金帧 | 用独立规范fixture验证RobotState/RobotCommand每字节Header、payload、字段偏移、端序和长度；至少包含正确帧与畸形Header负例 | 未实现/未执行 |
| OBS-07 | 运动停止确认契约 | 将STOP请求、发送成功、VAL3接受、运动控制结束、CS9静止反馈分别作为独立事件记录；不能用UDP send成功替代停止确认 | 未实现/未执行 |
| OBS-08 | 故障后生命周期退出 | 覆盖deactivate/cleanup/shutdown/error、socket断开、VAL3任务异常和ROS进程终止；要求独立安全链与通信watchdog按已批准风险分析响应 | 未实现/未执行 |

### E. 结论与工程边界

本轮补充确认：现有测试能够覆盖C++侧状态反馈陈旧、缓存读取和普通序号丢包，但不覆盖VAL3控制任务的命令新鲜度、故障标志生命周期、错误恢复授权、movejSync状态机或CS9停止行为。尤其不能把`ReadRobotStateTest`中的mock发送停止称为“机器人停止测试”，也不能把普通round-trip测试称为VAL3互操作测试。

本节仍是固定公开源码与测试文件的静态审查。未运行ROS构建/单测、未运行VAL3编译或SRS仿真、未连接CS9/真实机器人、未执行HIL/FAT/SAT或安全功能验证。所有OBS测试均为后续验收规格，不表示缺陷已复现或测试已通过。


### 本节来源记录（#1625–#1628）

| 编号 | 固定来源 | 用途 |
|---|---|---|
| #1625 | [controlTask.pgx @ bd658e2](https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/val3/userapp/ros2_server/controlTask.pgx) | 状态先发、命令处理后置、错误处理和TODO路径 |
| #1626 | [updateJointPositionControl.pgx @ bd658e2](https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/val3/userapp/ros2_server/Control/updateJointPositionControl.pgx) | bMotionPossible/命令/关节范围门控及movejSync状态分支 |
| #1627 | [test_robot_driver.cpp @ bd658e2](https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/test/unit_tests/test_robot_driver.cpp) | mock状态反馈staleness测试边界 |
| #1628 | [test_rt_socket_interface.cpp @ bd658e2](https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/test/unit_tests/communication/test_rt_socket_interface.cpp)；[test_message_serialization.cpp @ bd658e2](https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/test/unit_tests/communication/test_message_serialization.cpp) | subscriber缓存/普通丢包及同实现round-trip测试边界 |

以上均为固定commit源码文件的访问快照；GitHub文件内容不构成编译、测试执行或真实控制器行为证据。


## 9.3.28 RobotDriver连接握手、双通道就绪判定与启动时延审查（2026-11-07）

### A. 审查基线与文件范围

- 上游仓库：`ICube-Robotics/staubli_driver_ros2`，固定commit `bd658e2d266e315d2ee35f985fb352ea88306b79`；本轮按固定commit读取，不改变源码基线。
- 核对文件：`staubli_robot_driver/src/robot_driver.cpp`、`src/real_time_socket_subscriber.cpp`、`include/staubli_robot_driver/real_time_socket_subscriber.hpp`、`test/unit_tests/test_robot_driver.cpp`、`src/staubli_hardware_interface.cpp`。
- 来源#1629–#1631。仅源码/测试静态检查；未执行ROS构建、单元测试、VAL3编译或控制器连接。

### B. connect()握手流程的实际行为

1. `RobotDriver::connect()`分别建立控制UDP socket和诊断UDP socket，并创建控制`RealTimeSocketInterface`及诊断`RealTimeSocketSubscriber`。
2. 两个接口的`is_ready()`语义均为socket已连接且接收线程正在运行；它不表示已经收到有效、最新、协议兼容的业务报文。
3. 随后的握手循环每轮调用`read_robot_state()`检查控制状态，但诊断侧原本应调用的`read_diagnostic_data()`仍是TODO；实际代码将`diag_interface_ready = true`硬编码。
4. 循环条件是`now - start_connect_time < timeout`，循环体内在一次状态有效后没有break/return，而是继续每500ms轮询直到超时窗口耗尽。成功条件取决于循环退出时最后一次`read_robot_state()`的结果，而非“首次达到就绪立即成功”。
5. 因此连接时延被人为拉长到接近timeout配置值（HardwareInterface当前传入5000ms；单测传入1000ms），且控制状态有效性只以500ms间隔被重新采样。若控制器在中间出现短暂有效后停止发送，最终一次采样仍可能使connect失败；具体时序需动态测试确认。
6. 循环退出后代码打印`current_diagnostic_data_.robot_firmware_version`，但握手循环没有读取诊断数据；`reset_data()`仅将诊断消息Header标为INVALID，没有填充来自控制器的固件信息。因此日志中的版本值不能作为已读取的真实控制器固件版本证据，默认值可能显示为0.0.0。
7. `is_connected()`随后检查socket及subscriber是否ready，仍只证明连接/接收线程状态，不证明诊断业务数据已到达。它也没有补上连接时缺失的诊断握手。

### C. 测试覆盖审查

- `RobotDriverTest.ConnectionTest`启动mock robot线程，并以1000ms timeout调用connect；mock线程同时发送RobotState与DiagnosticData，但connect代码没有消费DiagnosticData。该测试可以在mock状态流存在时验证控制通道握手，不证明诊断报文被接收、校验或固件版本读取。
- mock机器人以4ms sleep发送两类数据，但测试没有断言connect返回耗时、首次状态报文延迟、诊断通道业务就绪或无诊断数据时连接失败。
- 当前静态审查没有运行该测试；不能把测试源码视为测试已通过，也不能从mock双通道发送推断真实VAL3诊断发布端已实现。

### D. 风险与修正规格

| ID | 问题/场景 | 建议修正与验收条件 | 当前状态 |
|---|---|---|---|
| CONN-01 | 状态报文首次有效后仍等待完整timeout | 首次满足全部握手条件时立即退出；测量connect延迟应接近首次有效报文到达时间加有限处理开销，而非固定接近timeout | 静态确认无提前退出；未运行 |
| CONN-02 | 诊断就绪硬编码true | 诊断业务通道必须收到并校验真实DiagnosticData（类型、长度、协议版本、staleness、序号）；否则连接失败或明确降级为不具备诊断能力的受限模式 | 静态确认；未实现验证 |
| CONN-03 | is_ready与业务数据ready混淆 | 将transport_ready、control_data_ready、diagnostic_data_ready分层表示；is_connected命名/契约明确区分socket状态和业务握手状态 | 规格建议；未实现 |
| CONN-04 | 固件版本从未填充的诊断对象读取 | 仅在成功读取并验证诊断帧后打印版本；否则打印unknown并明确诊断未就绪，禁止把默认结构体值记录成设备版本 | 静态确认日志路径；未运行 |
| CONN-05 | 500ms轮询导致握手延迟/采样稀疏 | 使用条件变量/消息到达通知或短周期有界等待；deadline采用单调时钟；避免在连接握手期间无条件sleep 500ms | 静态确认500ms sleep；未运行 |
| CONN-06 | 诊断发送端缺失时mock仍可通过连接 | 增加仅控制通道有帧、仅诊断通道有帧、诊断帧畸形/陈旧/协议不匹配、诊断线程启动但无业务帧等负例 | 未实现/未执行 |
| CONN-07 | 握手中控制状态短暂有效后停止 | 在deadline内按消息事件更新ready状态；定义一旦达到ready后是否需连续稳定帧窗口；不得因等待剩余timeout而把先前有效性无意覆盖 | 未实现/未执行 |

### E. 推荐连接状态机

建议将连接过程显式建模，而不是用两个布尔值混合表示：

`DISCONNECTED → SOCKETS_OPEN → RECEIVERS_RUNNING → CONTROL_VALID → DIAGNOSTICS_VALID → SESSION_READY`

- 任一阶段失败均转入`CONNECT_FAILED`并清理已创建资源。
- 只有目标部署配置明确允许诊断降级时，才允许从`CONTROL_VALID`进入受限会话；必须将诊断能力标记为不可用，禁止伪造ready或伪造固件版本。
- 首帧校验至少包括消息类型、协议版本、固定长度/字段约束、有效接收时间；如需支持重启恢复，应另有session/boot epoch与序号重置策略。
- 连接deadline使用单调时钟，成功条件一旦满足立即完成；任何“连续稳定N帧”策略应有明确N值和超时预算，并单独验证。
- 即使连接握手成功，仍不能把网络连接状态当作机器人运动许可或CS9安全状态。

### F. 结论与工程边界

本轮确认的核心缺口是：当前connect()把诊断通道的业务就绪状态硬编码为成功；同时控制通道即使已收到有效RobotState也没有提前退出握手循环，持续以500ms间隔轮询至配置timeout附近。连接成功日志读取的固件版本对象在该流程中未被诊断帧填充，不能视为真实设备版本证据。现有ConnectionTest虽然mock发送诊断数据，但没有验证connect消费或验证它。

本节为固定公开源码静态审查，未执行ROS构建/单测、网络故障注入、VAL3编译/SRS仿真、CS9 HIL或实机测试；没有证明现场一定发生5秒延迟或诊断误报。不得将修正规格视为已实现，也不得据此宣称Stäubli工程验收完成。

### 本节来源记录（#1629–#1631）

| 编号 | 固定来源 | 用途 |
|---|---|---|
| #1629 | [robot_driver.cpp @ bd658e2](https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/src/robot_driver.cpp) | connect握手循环、诊断ready硬编码、固件版本日志、is_connected与reset_data |
| #1630 | [real_time_socket_subscriber.cpp @ bd658e2](https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/src/real_time_socket_subscriber.cpp)；[real_time_socket_subscriber.hpp @ bd658e2](https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/include/staubli_robot_driver/real_time_socket_subscriber.hpp) | is_ready只表示socket连接和接收线程运行 |
| #1631 | [test_robot_driver.cpp @ bd658e2](https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/test/unit_tests/test_robot_driver.cpp)；[staubli_hardware_interface.cpp @ bd658e2](https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/src/staubli_hardware_interface.cpp) | ConnectionTest的mock发送和1000ms timeout；生产HardwareInterface以5000ms调用connect |

以上来源均固定在同一上游commit；本轮没有修改ICube上游仓库。


## 9.3.29 HardwareInterface网络端口参数解析与窄化转换审查（2026-11-07）

### A. 审查范围

- 固定上游commit：`bd658e2d266e315d2ee35f985fb352ea88306b79`。
- 核对`staubli_robot_driver/src/staubli_hardware_interface.cpp`的`on_configure()`及`src/communication/udp_socket.cpp`、`src/communication/udp_socket_impl.hpp`。
- 来源#1632–#1633；静态审查，未执行构建或参数故障注入。

### B. 参数处理路径

1. `on_configure()`通过`std::stoi`解析control_port、diagnostic_port、local_control_port、local_diagnostic_port为有符号int。
2. 解析后直接`static_cast<uint16_t>`传入NetworkConfig，转换前没有检查端口范围、远端端口是否为0或本地端口是否符合部署约束。
3. 对超出uint16_t范围的正数或负数，窄化转换会按目标无符号16位类型转换；例如65536转换为0，-1转换为65535。最终socket层只接收到转换后的16位值，原始配置错误信息丢失。
4. `std::stoi`未提供`pos`参数并检查完整消费长度，因此像`"30001junk"`这样的字符串可能被解析为前缀数值而非严格拒绝。
5. UDP实现将remote_port/local_port直接构造为Asio endpoint/resolver输入；没有在HardwareInterface参数边界恢复原始数值或提供语义清晰的参数错误。
6. 本节只指出配置输入验证不足。实际绑定/解析结果还取决于操作系统、Asio和具体数值；不能推断每种非法输入都会成功启动或造成网络连接。

### C. 风险与修正规格

| ID | 场景 | 建议修正与验收条件 | 当前状态 |
|---|---|---|---|
| PORT-01 | 远端端口为0、负数或大于65535 | 在窄化前严格拒绝；远端端口必须为1–65535 | 源码未见范围检查 |
| PORT-02 | 本地端口超范围 | 明确本地端口策略；若允许0表示临时端口，应只对本地端口允许0，其余必须1–65535 | 源码未见策略校验 |
| PORT-03 | 数字后附带非数字字符/空白 | 使用严格解析并检查完整字符串消费；拒绝前后非法字符 | 当前stoi未检查pos |
| PORT-04 | 四个端口发生冲突或配置重复 | 按网络拓扑定义远端/本地控制与诊断端口约束；发现不合理重复时给出明确错误 | 未见跨字段校验 |
| PORT-05 | 参数边界回归 | 覆盖-1、0、1、65535、65536、INT_MAX、非数字、数字前后缀、空字符串；验证拒绝/接受策略和错误消息 | 未实现/未执行 |

### D. 结论与边界

当前HardwareInterface把端口字符串解析为int后直接窄化为uint16_t，没有在转换前进行严格范围及完整字符串验证。建议在配置层完成严格解析和语义校验，避免错误配置被转换成另一个有效数值后才进入socket层。未执行编译、单测、网络绑定或CS9连接测试；该发现属于静态输入验证缺口，不代表已经发生端口误连或现场故障。

### 本节来源记录（#1632–#1633）

| 编号 | 固定来源 | 用途 |
|---|---|---|
| #1632 | [staubli_hardware_interface.cpp @ bd658e2](https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/src/staubli_hardware_interface.cpp) | stoi解析及直接static_cast<uint16_t> |
| #1633 | [udp_socket.cpp @ bd658e2](https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/src/communication/udp_socket.cpp)；[udp_socket_impl.hpp @ bd658e2](https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/src/communication/udp_socket_impl.hpp) | 16位端口参数向Asio endpoint/resolver传递 |



## 9.3.30 UDP通信可靠性、异步接收错误与线程生命周期审查（2026-11-07）

### A. 审查基线与文件范围

- 上游仓库：`ICube-Robotics/staubli_driver_ros2`，固定commit `bd658e2d266e315d2ee35f985fb352ea88306b79`。
- 核对：`src/communication/udp_socket.cpp`、`src/communication/udp_socket_impl.hpp`、`include/staubli_robot_driver/communication/socket.hpp`、`src/real_time_socket_subscriber.cpp`、`include/staubli_robot_driver/real_time_socket_subscriber.hpp`、`src/real_time_socket_interface.cpp`及两组通信单测。
- 来源#1634–#1637。仅固定源码与测试源码静态审查；没有执行构建、单测、压力测试、网络故障注入或CS9连接。

### B. UDP发送语义与错误传播

1. `UDPSocketImpl::send()`先检查本地`is_connected`，随后调用`socket_.send_to(..., MSG_DONTWAIT, err)`。它检查了错误码，但没有检查实际发送字节数；对UDP而言，本地send调用成功不证明远端控制器收到、解析或执行了报文。
2. 更明确的缺口是：当错误码为`would_block`时，代码记录“Packet dropped”，但没有返回false，函数最终仍返回true。上层因此可能把“本次命令已发送”与“本地发送缓存满、报文已丢弃”混为一谈。
3. 其他非零错误码会返回false；当前没有发送丢包计数器、连续丢包阈值或从发送失败升级为硬件组件ERROR的明确机制（源码注释将计数/阈值列为TODO）。
4. `RealTimeSocketInterface::send_message()`只根据底层bool返回序列化/发送成功或失败。即使底层返回true，也只代表该函数未观察到被传播的本地错误，不是VAL3接收ACK、命令执行确认、运动停止确认或安全状态确认。

### C. 异步接收错误与发送方校验

1. `handle_data_received(error, bytes_transferred)`在error非零时记录日志，但仍继续调用`reception_callback_`；随后只要`receiving_`仍为true，就重新调用`start_receive()`。
2. 因而错误完成路径没有在调用业务回调前按错误类别过滤，也没有区分可恢复错误、取消操作和致命错误的重试策略。持续错误是否造成重复回调/重挂接或高CPU循环，必须通过受控错误注入确认，不能仅凭源码断言现场必然发生。
3. `async_receive_from`填充`sender_endpoint_`，但当前发送方地址/端口校验仍以TODO注释存在；收到数据报不等于已验证来源是配置的机器人控制器。需要明确预期peer的IP与端口策略，并在业务解析前拒绝不符合策略的数据报。
4. 接收缓冲区最大长度由`MAX_SOCKET_PACKET_SIZE=1024`限定。需要对超长UDP数据报的截断/错误行为建立显式测试，避免把缓冲区容量当成协议帧长度校验。

### D. stop/join、重启与对象生命周期

1. `stop_receive_thread()`调用`io_service_.stop()`后立即join线程，之后才将`receiving_`置false；该函数没有显式取消socket上的挂起异步接收操作。
2. 如果停止时已有接收handler正在执行，它在join完成前仍可能观察到`receiving_==true`并重新挂接下一次异步接收。停止后挂起操作是否残留、随后`io_service_.reset()`并启动新接收线程是否造成旧/新接收操作并存，需要专门的停止-重启测试验证。
3. `disconnect()`在停止接收线程后关闭socket，这条路径会由socket close影响挂起操作；但仅调用`stop_receive_thread()`并保持socket连接时，没有看到相同的显式cancel/close步骤。
4. `RealTimeSocketSubscriber`析构函数只调用`socket_->stop_receive_thread()`，不负责断开共享socket；socket资源最终关闭依赖拥有者后续disconnect或socket对象析构。调用方必须保证共享socket所有权和关闭顺序清晰。
5. `receive_once()`复用持续接收线程并用promise通知首个回调；回调本身没有“只执行一次”的门控。若在调用方停止线程前第二个数据报再次触发回调，重复`promise.set_value()`可能抛出`future_error`；接收线程入口没有本地异常捕获。该竞态需以高频连续数据报确定性复现测试确认。

### E. Subscriber缓存、新鲜度和线程语义

- `RealTimeSocketSubscriber::update_message()`对每个成功反序列化的数据报写入接收时间戳并覆盖thread-safe box中的最新消息；这是一槽latest-value缓存，不是逐帧队列。
- `read_message()`按读取时观察到的序号差计算丢包数；若生产速度高于读取速度，中间数据报会被最新值覆盖，序号差可估计缺口，但无法恢复每一帧或区分所有网络重排情形。
- 当前实现按序号回绕分支计算丢包；重复序号被标记为`new_message=false`，但消息的接收时间戳已在update阶段刷新。故“接收时间较新”不等价于“序号持续前进/状态持续更新”。此项与§9.3.7已记录的重复/重放新鲜度问题相互关联，不在本节重复定性为新缺陷。
- `first_read_`和`last_read_sequence_number_`不在subscriber内部加锁；源码接口没有声明多线程并发调用`read_message()`的支持契约。若实际存在多个读取线程，需增加调用约束或同步保护并用TSan验证；当前不能推断单线程ros2_control调用已发生数据竞争。

### F. 现有测试覆盖与缺口

现有`test_sockets.cpp`覆盖UDP loopback连接/断开、单次/多次接收、断开后重连、receive_once正常路径、断开状态发送、重复connect/disconnect及重复start/stop；`test_rt_socket_interface.cpp`覆盖subscriber初始化、正常接收、缓存重复读取/陈旧、普通递增序号跳号和双向接口通信。它们属于测试源码存在性证据，本轮没有运行测试。

| ID | 新增验收场景 | 通过条件 | 当前状态 |
|---|---|---|---|
| UDP-01 | 注入`would_block`发送结果 | 底层返回失败或独立可观测的明确丢弃状态；丢包计数递增，不得向上层伪报已发送 | 未实现/未执行 |
| UDP-02 | 注入其他发送错误及短发送结果 | 错误完整传播；诊断日志/计数可关联到周期与报文 | 未实现/未执行 |
| UDP-03 | 注入operation_aborted、network_unreachable等接收错误 | 取消/致命错误不进入业务解析；重试策略有界且分类明确 | 未实现/未执行 |
| UDP-04 | receive线程停止后、socket保持连接再启动 | 任意时刻仅有一个有效接收链；旧handler不重复投递、不覆盖新callback | 未实现/未执行 |
| UDP-05 | handler执行期间并发stop | stop返回后不再重挂接异步操作；线程可确定性join | 未实现/未执行 |
| UDP-06 | 接收中disconnect、重连及重复循环 | 无遗留线程/handler；重连后只消费新session数据 | 未实现/未执行 |
| UDP-07 | 从非预期IP/端口发送合法格式报文 | peer策略不匹配的数据报在反序列化/状态更新前被拒绝 | 未实现/未执行 |
| UDP-08 | receive_once超时、单包、连续多包及回调异常 | promise只完成一次；无未捕获线程异常、死锁或悬挂线程 | 未实现/未执行 |
| UDP-09 | 大于1024字节、零长度、截断及协议长度不符数据报 | 长度策略显式、拒绝路径可观测，缓存不被部分/畸形数据污染 | 未实现/未执行 |
| SUB-01 | 多生产/多读取速率、重复/乱序/回绕/重启序号 | 明确latest-value语义、丢包统计边界及session epoch处理 | 部分现有覆盖；扩展未执行 |
| SUB-02 | 多线程并发调用read_message与TSan | 若不支持多读者则契约明确并防误用；若支持则无数据竞争 | 未实现/未执行 |

### G. 结论与工程边界

本节确认一个明确的错误传播缺口：UDP发送遇到`would_block`并丢弃数据报时仍返回true。另有三类高优先级生命周期/可靠性待验证点：异步接收错误仍调用回调并尝试重挂接；stop仅停止io_service并join、没有显式取消挂起接收；停止与重启之间可能遗留异步操作。接收方身份校验仍是TODO。现有单测覆盖基本loopback与常规生命周期，但未覆盖上述错误注入和停止-重启竞态。

不得将UDP本地send返回true解释为VAL3收到命令；不得将STOP数据报本地发送成功解释为机器人已停止；不得将socket接收线程运行解释为控制器业务数据有效。建议先修复发送结果语义，再引入可注入socket/错误码的单测，随后进行ASan/TSan、长时间压力、断网/恢复、VAL3仿真和CS9 HIL分层验证。

本节仅为固定commit源码/测试静态审查；未执行ROS构建/单测、UDP错误注入、压力测试、VAL3编译/SRS仿真、CS9 HIL/实机或安全验收。未修改ICube上游代码。

### 本节来源记录（#1634–#1637）

| 编号 | 固定来源 | 用途 |
|---|---|---|
| #1634 | [udp_socket_impl.hpp @ bd658e2](https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/src/communication/udp_socket_impl.hpp) | would_block返回true、异步接收错误回调/重挂接、stop/join及receive_once promise路径、发送方校验TODO |
| #1635 | [udp_socket.cpp @ bd658e2](https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/src/communication/udp_socket.cpp)；[socket.hpp @ bd658e2](https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/include/staubli_robot_driver/communication/socket.hpp) | UDP接口转发、最大数据报缓冲区及抽象发送/接收契约 |
| #1636 | [real_time_socket_subscriber.cpp @ bd658e2](https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/src/real_time_socket_subscriber.cpp)；[real_time_socket_subscriber.hpp @ bd658e2](https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/include/staubli_robot_driver/real_time_socket_subscriber.hpp)；[real_time_socket_interface.cpp @ bd658e2](https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/src/real_time_socket_interface.cpp) | latest-value缓存、序号/时间戳处理、析构停止线程、send_message错误传播 |
| #1637 | [test_sockets.cpp @ bd658e2](https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/test/unit_tests/communication/test_sockets.cpp)；[test_rt_socket_interface.cpp @ bd658e2](https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/test/unit_tests/communication/test_rt_socket_interface.cpp) | 已有loopback、接收/重连/常规stop及subscriber缓存测试的覆盖边界 |



## 9.3.31 ros2_control生命周期回调、STOP责任与模式切换边界审查（2026-11-07）

### A. 审查基线

- 上游固定commit：`bd658e2d266e315d2ee35f985fb352ea88306b79`。
- 核对`staubli_hardware_interface.cpp/.hpp`、`robot_driver.cpp`及`test_staubli_hardware_interface.cpp/.hpp`。
- 来源#1638–#1640。仅静态审查源码与测试定义；未执行ROS构建、gtest、生命周期故障注入、VAL3仿真或CS9测试。

### B. 生命周期回调的实际动作

1. `on_configure()`负责解析网络参数并调用`robot_driver_->connect(..., 5000)`；连接失败返回CallbackReturn::ERROR。连接流程中的诊断ready与等待行为已在§9.3.28审查，端口输入边界见§9.3.29。
2. `on_activate()`仅将本地`current_control_mode_`设置为STOP并返回SUCCESS；没有在该回调内调用`send_stop_all_command()`或等待控制器确认。随后是否发送STOP取决于后续`write()`周期是否执行。
3. 类头文件声明并实现`on_init/on_configure/on_activate/on_cleanup/on_shutdown/on_error`，没有自定义`on_deactivate()`。因此本驱动没有显式的deactivate专属STOP、停止确认或disconnect步骤；基类默认行为不能替代本驱动的设备侧动作证据。
4. `on_cleanup()`调用`robot_driver_->disconnect()`，但忽略其bool结果并无条件返回SUCCESS；也没有在断开前显式发送STOP或确认机器人静止。
5. `on_shutdown()`只在driver仍connected时执行；其是否发送STOP由缓存的`state_msg_.control_state != CommandType::STOP`决定，而不是本地`current_control_mode_`。该判断前没有重新读取状态或验证状态新鲜度；STOP发送结果和disconnect结果均未检查，随后返回SUCCESS。
6. `on_error()`在driver connected时调用`send_stop_all_command()`，但忽略返回值并返回SUCCESS；只有driver未连接时才返回ERROR。因此生命周期回调成功并不能证明STOP数据报成功发出，更不能证明VAL3已接收、运动已停止或安全停止已完成。
7. 析构函数也仅调用`disconnect()`并忽略结果。普通断开、清理和析构均不能被当成具有停止确认语义的流程。
8. 与§9.3.30结合：UDP send遇到would_block且丢弃数据报仍返回true；因此即便上层检查STOP bool，当前底层返回值本身也尚不足以证明报文已被本地网络栈接受。

### C. 命令模式切换与生命周期耦合

- `prepare_command_mode_switch()`根据`start_interfaces`解析incoming mode；`stop_interfaces`未参与实际决策（outgoing mode代码被注释），源码TODO也明确指出尚未验证所有相关接口是否成组停止/启动及混合position/velocity接口。
- `resolve_mode()`按传入列表遍历并在首个匹配的position/velocity/effort/acceleration名称处返回；混合接口组合可能由列表中先出现的匹配项决定，缺少完整集合一致性校验。
- `perform_command_mode_switch()`在本地更新`current_control_mode_`；切换为STOP并不在该回调中同步发送停止命令，实际发送仍依赖后续write周期。切换为位置模式时使用缓存的`state_msg_`检查error_state/motion_possible，并对operation_mode_status非零仅告警；没有在该回调中重新读取控制器状态或检查报文年龄。
- 因此需要把“控制器管理器模式切换完成”“本地命令模式变量更新”“STOP报文发送”“VAL3确认停止”“安全系统进入安全停止状态”作为不同证据节点。

### D. 现有测试覆盖

`test_staubli_hardware_interface.cpp`包含Construction、Initialization、InitializationFailsWithEmptyInfo、Configuration、ConfigurationShouldFailWithoutRobot、PluginLoading、PluginLoadingAndInitialization、InterfaceExport和LifecycleTransitions。LifecycleTransitions测试实际执行init/configure/activate/read/write；未调用on_deactivate、on_cleanup、on_shutdown或on_error，也没有验证STOP报文数量/内容、发送失败传播、disconnect失败处理、重复生命周期转换或状态陈旧时的停止策略。配置失败用例虽存在，但不构成各生命周期回调的错误路径矩阵。

### E. 新增验收规格

| ID | 场景 | 通过条件 | 当前状态 |
|---|---|---|---|
| LIFE-01 | activate后立即deactivate，不安排后续write周期 | 驱动定义并执行明确的deactivate动作；若要求STOP，则必须验证发送及控制器侧确认，不依赖未来write | 未实现/未执行 |
| LIFE-02 | on_error中STOP发送失败/底层would_block | 回调不得把未确认的停止动作伪报为成功；错误升级与后续安全处置策略明确 | 未实现/未执行 |
| LIFE-03 | cleanup/shutdown期间disconnect失败或接收线程无法退出 | 检查并传播清理结果；资源残留可观测，重复清理幂等 | 未实现/未执行 |
| LIFE-04 | shutdown时缓存control_state为STOP但本地模式非STOP，或缓存状态陈旧 | 使用明确的新鲜状态/命令状态策略，不依赖单一旧缓存跳过停止流程 | 未实现/未执行 |
| LIFE-05 | on_activate后没有read/write调度、控制器仍有前一会话状态 | 明确激活准入、首个STOP/状态同步和session epoch；不能把本地STOP变量当作控制器已停止 | 未实现/未执行 |
| LIFE-06 | 同时启动/停止position、velocity、effort、acceleration接口的混合组合 | 对完整start/stop集合进行原子验证；拒绝不一致/混合模式，不依赖接口列表顺序 | 未实现/未执行 |
| LIFE-07 | STOP mode switch后不再调度write | STOP责任不依赖下一周期write；停止确认与超时故障路径可测 | 未实现/未执行 |
| LIFE-08 | 生命周期重复configure/activate/deactivate/cleanup/shutdown/error及异常注入 | 每条路径状态转移、线程、socket和命令权责明确；无资源泄漏/双重释放/错误成功 | 未实现/未执行 |

### F. 结论与边界

当前驱动的生命周期回调没有建立完整的停止确认闭环：deactivate没有驱动自定义实现；activate只设置本地STOP变量；cleanup直接disconnect；shutdown根据缓存的控制器control_state条件性发送STOP且忽略发送/断开结果；error回调同样忽略STOP发送结果却返回SUCCESS。模式切换将STOP写入本地状态，实际网络发送依赖后续write周期。以上结论是固定源码结构和返回路径的静态判断，不代表已复现现场故障。

普通UDP STOP命令不是CS9独立安全停止功能。任何应用层STOP验证都不能替代急停、SS1/SS2、STO/SBC及目标安全配置验证。未运行ROS构建/单测、Lifecycle故障注入、VAL3编译/SRS仿真、CS9 HIL/实机或安全验收；未修改ICube上游代码。

### 本节来源记录（#1638–#1640）

| 编号 | 固定来源 | 用途 |
|---|---|---|
| #1638 | [staubli_hardware_interface.cpp @ bd658e2](https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/src/staubli_hardware_interface.cpp) | init/configure/activate/cleanup/shutdown/error、read/write、mode-switch及本地STOP模式行为 |
| #1639 | [staubli_hardware_interface.hpp @ bd658e2](https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/include/staubli_robot_driver/staubli_hardware_interface.hpp) | 生命周期override集合，未声明自定义on_deactivate |
| #1640 | [test_staubli_hardware_interface.cpp @ bd658e2](https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/test/unit_tests/test_staubli_hardware_interface.cpp) | LifecycleTransitions只覆盖init/configure/activate/read/write及现有测试边界 |



## 9.3.32 ROS2—UDP—VAL3实时控制周期、反馈新鲜度与命令时序闭环审查（2026-11-07）

### A. 审查基线与证据范围

- 上游固定commit：`bd658e2d266e315d2ee35f985fb352ea88306b79`。
- 核对ROS HardwareInterface、RobotDriver、RealtimeSocketSubscriber/Interface、协议消息序列化、VAL3 `start.pgx`、`controlTask.pgx`、`Comm/readData*.pgx`、`Comm/computeSequenceDelay.pgx`、`Serialization/decodeRobotCommandMsg.pgx`、`Control/updateJointPositionControl.pgx`及现有通信/HardwareInterface测试。
- 来源#1641–#1647。仅源码和测试定义静态审查；未执行ROS构建、实时调度测量、VAL3编译、SRS仿真、UDP注入、CS9 HIL或实机测试。

### B. 4ms控制周期与实时性证据

1. VAL3 `start.pgx`将`l_nCtrlPeriod=0.004`并通过`taskCreateSync`创建`controlTask`；这只能证明代码配置目标周期为4ms，不能证明实际每次迭代严格4ms、抖动上界、WCET或调度优先级。
2. `controlTask`检查`bIsOverrun`时只记录日志、清除标志并累加`nOverruns`；未见连续超限门槛、锁存故障、停止动作或向ROS暴露超限计数的闭环。该问题与§9.3.21既有RT审查一致，本节从ROS端周期参数与端到端链路补充。
3. ROS `read()`忽略传入的`time/period`，仅调用`read_robot_state()`并更新接口状态；`write()`将ros2_control传入的`period.seconds()`乘1000写入command的`controller_period`字段。源码未对period是否为正、是否超出设计范围或周期突变进行校验。
4. VAL3 `decodeRobotCommandMsg`将该字段解码为`nRemoteCtrlPeriod`；固定commit中检索到该字段仅在类型声明、初始化和解码中使用，未见controlTask或位置控制程序据此调整轨迹、插补或控制周期。因此该字段当前不能视为VAL3已按ROS实际周期进行时间补偿。
5. `controlTask`循环末尾调用`delay(0)`，其4ms同步节拍由taskCreateSync配置；没有源码内的实际周期直方图、抖动分位数、每阶段执行耗时或最坏执行时间报告。Monitor speed低于100%仅告警的既有发现见§9.3.21。

### C. 反馈消息新鲜度与序号推进

1. `RealTimeSocketSubscriber::update_message()`对每个成功反序列化的RobotState数据报赋本地接收时间戳并覆盖latest-value缓存。它不是逐帧队列；快于读取速率的状态可能被覆盖。
2. `read_message()`会在序号相同的情况下设置`status.new_message=false`，但仍返回true并将消息复制给调用者；`RobotDriver::read_robot_state()`没有检查`status.new_message`，只验证message_type和本地接收年龄，然后将该帧序号写入`last_valid_sequence_id_`。
3. 因此重复序号报文仍可被当作一次成功的状态读取；只要重复报文持续抵达，其本地reception_timestamp持续刷新，100ms默认staleness timeout就不会单独识别“序号停滞”。本节不将其扩大解释为已发生现场故障，但它证明“收到新UDP数据报”“序号推进”“机器人状态实际更新”是三个不同条件。
4. `read_robot_state()`默认状态staleness timeout为100ms；控制器VAL3循环的序号延迟阈值在运动时为`>5`个名义周期、非运动时为`>25`个名义周期。按4ms配置仅可换算为约20ms/100ms的名义周期数量，不是经过实测的绝对时延上限；任务抖动、漏周期、序号重置/回绕都会影响其真实时间含义。
5. C++ outgoing command的header.sequence_number取`get_current_message_sequence()`，即最近一次被RobotDriver接受的状态序号，而不是独立生成的命令序号。VAL3以当前已发送状态序号减命令回显序号计算ping-pong delay。这是协议回显设计，但若C++反复接受相同序号，command也会反复携带旧序号；现有代码没有在RobotDriver层强制要求每次read都有序号前进。
6. `computeSequenceDelay`对负差值仅在小于-60000时按uint16回绕修正；其他负差值由controlTask判为异常并切入错误路径。该边界需要对边界值、乱序、控制器重启和会话切换进行系统测试。

### D. VAL3命令接收与执行时序

1. `controlTask`每轮先更新并发送RobotState，再调用`readData()`读取ROS命令，然后解码、计算序号延迟、检查模式转换，最后执行运动命令。因此状态帧是在本轮新命令执行前生成的；ROS收到的该帧不能当作对随后同轮命令执行结果的确认。
2. `readData()`最多调用两次`readDataOnce()`以尝试取出数据；当无数据时没有新命令标志，controlTask对上一条有效命令的staleness检查仍是TODO。其后虽通过状态序号回显延迟检查控制流，但这不是基于命令本地到达时间的独立超时。
3. `decodeRobotCommandMsg`解析header并检查message type及数据长度，但没有在该程序内验证命令header.sequence_number相对上一条命令单调递增、拒绝重复命令或校验会话epoch。控制task用序号差作延迟代理，不等同完整anti-replay/session校验。
4. 位置控制`updateJointPositionControl`读取`$movejSyncState()`，当状态为1（上次命令未及时刷新）时对应告警代码被注释；虽然controlTask有另一条基于序号延迟的停止路径，但movejSync的刷新超时没有独立的、明确的错误锁存和诊断闭环。该点与§9.3.21/§9.3.26关联。
5. `nRemoteCtrlPeriod`被解码但没有发现后续控制算法消费；因此不能假设VAL3根据ROS侧周期变化动态调整movejSync刷新期限或插补参数。
6. `send_robot_command()`返回true只表示序列化和本地socket发送路径没有报告错误；结合§9.3.30的would_block返回语义，不构成VAL3接收、解码、接受、执行或目标到位的确认。

### E. 新增端到端验收矩阵

| ID | 场景 | 通过条件 | 当前状态 |
|---|---|---|---|
| RT-09 | ROS control loop目标4ms，在CPU/网络负载阶跃下持续采样 | 同时输出ROS read/write、UDP收发、VAL3 task周期的P50/P95/P99/P99.9/max与missed-deadline；定义并验证预算 | 未实现/未执行 |
| RT-10 | VAL3 task overrun连续、间歇和突发注入 | 超限计数有上报、阈值/锁存/恢复策略明确；不得只依赖日志 | 未实现/未执行 |
| RT-11 | RobotState重复序号但每4ms重复发送 | RobotDriver识别序号停滞，即使本地接收时间刷新也不误判为持续新鲜状态 | 未实现/未执行 |
| RT-12 | 状态序号停止推进、网络延迟/丢包/乱序/回绕 | C++ staleness与VAL3 ping-pong判据边界一致；阈值按实际周期与模式验证 | 未实现/未执行 |
| RT-13 | ros2_control period为0、负值、4ms、抖动、跳变及异常长周期 | controller_period单位、范围和异常周期处理明确；VAL3是否消费该字段有可执行证据 | 未实现/未执行 |
| RT-14 | 命令重复、旧序号、乱序、跨重启旧命令 | 控制器拒绝重复/过期/旧session命令；boot/session标识与序号回绕策略明确 | 未实现/未执行 |
| RT-15 | VAL3发送状态后同轮收到并执行新命令 | 状态/命令时序可追踪，不能将前置状态帧误当作命令执行ACK；另有执行/停止确认 | 未实现/未执行 |
| RT-16 | movejSyncState持续为1、短暂为1、恢复和超时 | 明确刷新超时动作、故障锁存、状态上报及重新授权路径 | 未实现/未执行 |
| RT-17 | 多次read同一缓存消息后write | 同一反馈序号不能无限续发旧目标；序号无进展时进入可验证的降级/停止路径 | 未实现/未执行 |

### F. 结论与安全边界

当前固定源码展示了4ms VAL3同步任务配置、ROS周期字段传输和序号ping-pong延迟检测，但尚未形成可量化的端到端实时性保证。主要差距包括：无实际周期/WCET/抖动测量；overrun仅计数和日志；ROS subscriber把接收时间刷新与序号新鲜度分离，RobotDriver又忽略`status.new_message`；VAL3对无新命令时的上一命令staleness检查为TODO；命令周期字段虽被传输和解码，未见控制逻辑消费；movejSync刷新超时分支未形成明确故障动作。

建议先定义端到端时序预算和统一的状态/命令序号语义，再添加重复帧停滞检测、命令session/age校验、周期字段单位与范围验证、overrun阈值与故障上报，并为状态发布—命令接收—命令执行—反馈确认分别添加可关联trace ID/时间戳。STOP和安全动作仍必须独立验证，不能把序号延迟阈值、UDP发送成功或ROS硬件回调返回OK视为安全停止保证。

本节仅为固定commit源码与测试定义静态审查；未执行ROS构建/单测、4ms周期测量、VAL3编译/SRS仿真、网络注入、CS9 HIL/实机或安全验收；未修改ICube上游代码。

### 本节来源记录（#1641–#1647）

| 编号 | 固定来源 | 用途 |
|---|---|---|
| #1641 | [staubli_hardware_interface.cpp @ bd658e2](https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/src/staubli_hardware_interface.cpp) | read忽略time/period；write周期字段、状态门控、命令发送 |
| #1642 | [robot_driver.cpp @ bd658e2](https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/src/robot_driver.cpp)；[robot_driver.hpp @ bd658e2](https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/include/staubli_robot_driver/robot_driver.hpp) | 100ms默认staleness、read_message调用、状态序号更新和命令序号来源 |
| #1643 | [real_time_socket_subscriber.cpp @ bd658e2](https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/src/real_time_socket_subscriber.cpp) | 本地接收时间戳、latest-value缓存、相同序号new_message=false但仍返回true |
| #1644 | [start.pgx @ bd658e2](https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/val3/userapp/ros2_server/start.pgx)；[controlTask.pgx @ bd658e2](https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/val3/userapp/ros2_server/controlTask.pgx) | 4ms taskCreateSync、overrun处理、状态先发送后收命令、序号延迟阈值、命令staleness TODO |
| #1645 | [computeSequenceDelay.pgx @ bd658e2](https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/val3/userapp/ros2_server/Comm/computeSequenceDelay.pgx)；[getNextSequenceNumber.pgx @ bd658e2](https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/val3/userapp/ros2_server/Comm/getNextSequenceNumber.pgx) | 序号差计算、uint16回绕逻辑 |
| #1646 | [readData.pgx @ bd658e2](https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/val3/userapp/ros2_server/Comm/readData.pgx)；[readDataOnce.pgx @ bd658e2](https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/val3/userapp/ros2_server/Comm/readDataOnce.pgx)；[decodeRobotCommandMsg.pgx @ bd658e2](https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/val3/userapp/ros2_server/Serialization/decodeRobotCommandMsg.pgx) | 每轮最多两次读socket、消息解码、缺少重复/旧session命令门控 |
| #1647 | [updateJointPositionControl.pgx @ bd658e2](https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/val3/userapp/ros2_server/Control/updateJointPositionControl.pgx)；[messages.cpp @ bd658e2](https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/src/communication/messages.cpp) | movejSyncState==1处理、RemoteCtrlPeriod解码/序列化与消息字段边界 |



## 9.3.33 运动指令输入边界、关节限位与轨迹执行安全审查（2026-11-07）

### A. 审查基线与证据范围

- 上游固定commit：`bd658e2d266e315d2ee35f985fb352ea88306b79`。
- 核对ROS `StaubliHardwareInterface::write()`、模型Xacro关节生成逻辑、TX2-60L关节限位配置、MoveIt关节动态限位配置、VAL3 `decodeRobotCommandMsg` 与 `updateJointPositionControl`，以及现有HardwareInterface单元测试。
- 来源#1648–#1654。仅源码/配置/测试定义静态审查；未运行ROS构建、单测、MoveIt规划、VAL3编译、SRS仿真、CS9 HIL或实机轨迹/安全测试。

### B. ROS命令数值输入边界

1. `write()`将position接口的rad转换为degree后写入6元素`command_reference`；之后的数值检查只调用`std::isnan()`。因此NaN会触发STOP请求并返回ERROR，但正/负Inf没有被该检查拒绝；也未见对有限但极大数值、单周期目标跳变量或命令相对当前反馈偏差的HardwareInterface本地边界检查。
2. 数值检查遍历`i < num_joints_`，而`command_reference`固定6元素；前序命令填充循环虽限制`i < 6`，NaN检查循环未限制。若硬件描述错误配置超过6个joint，检查本身会越过数组边界。该风险与早先§9.3.1轴数边界发现相互印证；本节不声称已运行复现。
3. `write()`把ros2_control的周期转换成毫秒字段并发送，但本节未发现对周期非正、非有限或异常突变的二次校验；该周期字段的VAL3消费缺口已在§9.3.32记录。
4. ROS层未见`std::isfinite()`或对位置命令进行独立限位裁剪/拒绝的代码。不能仅凭URDF/MoveIt配置文件存在，就断言每一条直接写入HardwareInterface的命令都已被限幅；必须核验实际ControllerManager参数、JointLimiter启动日志及write入口收到的最终数值。

### C. URDF、ros2_control与MoveIt限位配置分层

1. TX2-60L模型的`joint_limits.yaml`为6个关节提供`min_position/max_position`、`max_velocity`、`max_acceleration`，位置限位标记为true；例如J1为±180°、J2为±127°、J3为±150°、J4为±270°、J5为±120°、J6为±270°。这些是随附模型配置值，不等同目标机器人铭牌/控制器安全参数已核实。
2. `staubli_helpers.xacro`将配置中的min/max position和max velocity写入URDF joint的`limit`；可选`safety_controller`再基于margin生成软限位。此处证明模型描述具有位置/速度边界，但是否在实际运行链路中对所有命令接口强制执行，仍取决于展开后的URDF、ros2_control限位启用配置及运行时JointLimiter行为。
3. R2C ros2_control关节宏导出position与velocity命令接口；可选acceleration接口仅用于向JointLimiter提供加速度限值，源码注释和文档明确它不是实际运动命令模式。HardwareInterface仍会导出velocity接口，但上游文档说明当前拒绝velocity控制模式；不得将导出接口误写为已实现速度控制。
4. MoveIt的`joint_limits.yaml`设置默认velocity/acceleration scaling为0.1，并为各关节设置速度/加速度上限；该文件未在本次核对中提供独立的min/max position覆盖。MoveIt规划缩放与HardwareInterface/VAL3执行侧保护属于不同层，不可相互替代。
5. ROS 2官方ros2_control文档说明命令限位可受ControllerManager全局`enforce_command_limits`、joint级或interface级配置控制；因此必须在实际启动配置和日志中确认限位器是否启用，而不是只检查YAML是否存在。

### D. VAL3控制器侧软件关节限位与目标跳变

1. VAL3 `updateJointPositionControl.pgx`将6个float命令字段映射为joint，并在调用`$movejSync()`之前执行`isInRange(l_jJointPositionCmd)`。越界时记录错误、调用`stopJointPositionControl`、置错误并返回。这构成独立于ROS规划层的控制器软件关节范围检查。
2. `isInRange()`检查的是机械臂软件关节限位范围；它不能单独证明目标速度、加速度、jerk、关节间耦合、碰撞、奇异性、制动距离或工具/工件负载均满足要求。真实安全能力仍受CS9/机器人型号/配置约束。
3. 同一位置控制程序紧接着保留“Check target is close enough to current position // TODO”，没有看到目标与当前关节位置差值的最大阈值/单周期跳变限制。因而任意一个仍处于合法关节范围内的远距离目标，不能仅凭`isInRange`判定为安全或可平滑执行。
4. 命令解码程序读取6个float字段并设置`bIsValid`，但没有对每个运动字段执行显式有限数检查；最终位置程序的`isInRange`是当前可见的关节位置门槛。NaN/Inf在VAL3比较、序列化和运动指令API中的实际行为必须通过目标VAL3版本仿真/控制器测试确认，不应推断其必然被安全拒绝。
5. `$movejSyncState()==1`表示上次命令没有及时刷新，对应日志分支仍被注释；该刷新超时风险已在§9.3.32 RT-16记录，本节将其纳入目标轨迹连续性与跳变验收，而不重复判定为已触发故障。

### E. 新增验收矩阵

| ID | 场景 | 通过条件 | 当前状态 |
|---|---|---|---|
| JNT-01 | ROS位置命令输入NaN、+Inf、-Inf | 所有非有限值在socket发送前被拒绝；STOP/ERROR路径和错误可观测性明确 | 未实现/未执行 |
| JNT-02 | ROS位置命令刚好等于min/max、略超限、远超限 | 边界包含性、限幅/拒绝策略一致；最终写入HardwareInterface的值可追踪 | 未实现/未执行 |
| JNT-03 | 有限但极大目标、单周期大幅跳变、跨多关节同步跳变 | 在控制器执行前按经验证的目标增量/速度/加速度约束拒绝或安全整形 | 未实现/未执行 |
| JNT-04 | num_joints为0、1、6、7及错误URDF | 配置准入明确限定支持DoF；固定6轴数组无越界访问 | 未实现/未执行 |
| JNT-05 | 对照URDF、ros2_control JointLimiter和MoveIt三层限位 | 生成后的URDF边界、ControllerManager enforce配置、启动日志和MoveIt参数一致且差异有说明 | 未实现/未执行 |
| JNT-06 | ControllerManager关闭/开启enforce_command_limits | 关闭时不得误宣称ROS限位仍生效；开启时验证每个position接口最终命令的边界行为 | 未实现/未执行 |
| JNT-07 | VAL3 isInRange下限/上限/刚好边界/越界及当前臂已在软件限位外 | 明确CS9目标版本边界语义；越界命令不进入movejSync，异常状态有可观测故障路径 | 未实现/未执行 |
| JNT-08 | 合法范围内远距离目标与当前反馈偏差 | 实现并验证TODO所指目标接近性阈值，阈值按速度/加速度/周期/负载工况定义 | 未实现/未执行 |
| JNT-09 | MoveIt规划目标与绕过MoveIt直接写position接口 | 两条入口都满足同一执行侧约束；不能依赖MoveIt缩放作为唯一保护 | 未实现/未执行 |
| JNT-10 | movejSync刷新延迟、跳变、丢帧后恢复 | 刷新超时进入明确停止/锁存路径；恢复需同步状态并重新授权 | 未实现/未执行 |

### F. 结论与安全边界

固定源码呈现了三层不同性质的约束：模型Xacro/URDF关节范围和速度描述、ros2_control可配置的JointLimiter、VAL3执行前的`isInRange()`软件关节范围检查。MoveIt另有规划速度/加速度缩放。但目前不能据此认定这些层已形成端到端、不可绕过的执行安全闭环：ROS HardwareInterface只显式拒绝NaN而未拒绝Inf；未见其本地位置/增量/周期硬限制；JointLimiter是否实际启用需检查运行时参数；VAL3目标接近性仍为TODO，且关节范围检查不等同轨迹动力学/碰撞/功能安全验证。

优先建议：先将支持轴数固定校验为6并修复所有固定数组索引边界；在ROS发送入口拒绝所有非有限数值；从目标型号官方规格和CS9配置生成唯一版本化限位数据；验证ControllerManager限位启用与启动日志；在VAL3端补目标增量/时间约束与刷新watchdog，并对movejSync拒绝/停止状态做故障锁存。所有阈值需按机器人型号、工具/负载、控制器版本和风险评估确认，不能直接把TX2-60L示例值推广到其他Stäubli型号。

本节仅为固定commit静态审查；未运行构建/单测、限位器实测、MoveIt轨迹执行、VAL3编译/SRS仿真、CS9 HIL/实机或功能安全验证；未修改ICube上游代码。

### 本节来源记录（#1648–#1654）

| 编号 | 固定来源 | 用途 |
|---|---|---|
| #1648 | [staubli_hardware_interface.cpp @ bd658e2](https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/src/staubli_hardware_interface.cpp) | rad→deg转换、NaN检查、固定6元素command_reference及write路径 |
| #1649 | [staubli_helpers.xacro @ bd658e2](https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_description/urdf/include/staubli_helpers.xacro)；[staubli_r2c_joints.xacro @ bd658e2](https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_description/r2c/include/staubli_r2c_joints.xacro) | YAML限位加载、URDF joint limit/soft limit、ros2_control接口生成 |
| #1650 | [TX2-60L joint_limits.yaml @ bd658e2](https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_description/config/tx2_60l/joint_limits.yaml) | 六轴位置、速度、加速度配置值 |
| #1651 | [MoveIt joint_limits.yaml @ bd658e2](https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_moveit_config/config/joint_limits.yaml) | MoveIt默认缩放及速度/加速度上限 |
| #1652 | [updateJointPositionControl.pgx @ bd658e2](https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/val3/userapp/ros2_server/Control/updateJointPositionControl.pgx) | VAL3 isInRange、目标接近性TODO、movejSync刷新状态 |
| #1653 | [decodeRobotCommandMsg.pgx @ bd658e2](https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/val3/userapp/ros2_server/Serialization/decodeRobotCommandMsg.pgx) | 运动float字段解码及有效位设置 |
| #1654 | [test_staubli_hardware_interface.cpp @ bd658e2](https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/test/unit_tests/test_staubli_hardware_interface.cpp) | 当前测试覆盖接口导出和常规mock write，缺少NaN/Inf/边界/跳变测试 |


## 9.3.34 轨迹执行状态、运动完成判定与反馈一致性审查（2026-11-07）

### A. 审查基线

- 上游固定commit：`bd658e2d266e315d2ee35f985fb352ea88306b79`。
- 核对VAL3 `updateState.pgx`、`RobotState.dtx`、`updateJointPositionControl.pgx`、`controlTask.pgx`，C++ `RobotDriver`、`StaubliHardwareInterface`、消息结构与单元测试，以及bringup的JointTrajectoryController配置、MoveIt控制器映射和官方示例文档。
- 来源#1655–#1664。仅固定源码、配置和文档静态审查；未运行ROS构建/测试、MoveIt执行、VAL3编译/SRS仿真、CS9 HIL或实机轨迹。

### B. VAL3状态字段的真实语义

1. `updateState.pgx`以`bInMotion = !isSettled()`生成全局运动标志；关节位置由`herej()`取得。代码没有将当前目标位置逐轴与`herej()`比较，也没有把某条ROS轨迹/目标ID写入RobotState。
2. `jointVelocities`来自`$getJntSpeedCmd()`，源码注释称其为速度“approximation”；不能将它直接等同于独立、经精度验证的编码器速度测量。关节力矩来自`getJointForce()`，源码明确声明无精度承诺。
3. `bValidPosition`、`bValidVelocity`、`bValidTorque`在`updateState`中被无条件设为true，随后`bIsValid`也设true；没有看到对herej/getJntSpeedCmd/getJointForce返回值、范围、有限性或采样质量的逐字段失败判定。
4. RobotState协议携带当前位置、速度、全局`in_motion`、控制模式、错误/安全标志及序号延迟，但不携带目标位置、轨迹ID、命令接受结果、movejSync状态或到位容差结果。C++ RobotDriver读取并校验消息类型/新鲜度后更新缓存；其返回true只说明读到符合这些条件的状态帧，不代表某个命令执行完成。

### C. VAL3 movejSync状态与完成确认缺口

1. `updateJointPositionControl.pgx`对`$movejSyncState()`的注释定义：-2错误停止、-1未启动、0运行无错误、1运行但上次命令未及时刷新、2因急停/hold/stopMove等运动停止而锁定命令。这些状态不是逐目标完成回执。
2. 程序将每个有效位置命令传给`$movejSync()`，随后读取状态；只对-2执行明确错误停止，状态1/2对应的告警和错误置位代码被注释。没有发现目标完成事件、目标ID确认或等待指定目标达到稳定状态的逻辑。
3. `stopJointPositionControl`调用`$movejSyncEnd()`后无条件返回`x_bError=false`，不等待或验证机器人已停止；该停止确认缺口已在前序章节记录，本节不重复展开。
4. `controlTask`每周期先采集并发布RobotState，再接收/处理当前命令。因此当周期发布的状态不能作为该周期后续处理命令的ACK。模式状态与序号延迟只能反映控制模式/通信往返代理，不能关联到具体目标的接受、执行或完成。
5. `bInMotion=false`仅反映VAL3的`isSettled()`结果；没有发现其与当前目标一致、达到目标位置容差、保持一定稳定时间三者的联合判断。不能把全局settled标志单独当作“本次轨迹成功”。

### D. ROS 2 JointTrajectoryController与MoveIt配置

1. bringup的`controllers.yaml`以250Hz运行ControllerManager，JointTrajectoryController使用position command、position/velocity state接口，`action_monitor_rate=20Hz`，`allow_partial_joints_goal=false`，`interpolate_from_desired_state=true`，`allow_nonzero_velocity_at_trajectory_end=true`，`stopped_velocity_tolerance=0.01`，`goal_time=0.0`。
2. Jazzy版ros2_control文档定义`interpolate_from_desired_state=true`时，新轨迹从上一条期望/命令状态插值起步，并忽略HardwareInterface状态接口作为该插值起点；这不等于关闭整个控制器的反馈/Action监视，但意味着轨迹衔接起点可能不是当前机器人真实状态。该参数应在真实机器人跟踪偏差、急停后偏差、轨迹抢占和控制器重激活场景重点验证。
3. 配置允许轨迹末端非零速度；同时设置`stopped_velocity_tolerance=0.01`，需要通过当前Jazzy实际控制器版本确认该停止阈值在允许非零末速度配置下的适用路径，不能仅凭参数同时存在就推断最终必须静止。
4. 配置显式设置`goal_time=0.0`，Jazzy文档将其定义为不允许额外到达宽限时间；但未显式设置每个关节的trajectory/goal位置容差。应检查MoveIt发送的FollowJointTrajectory目标是否携带显式容差，以及当前控制器版本的默认容差解析结果，不能假设默认值已形成有效位置验收。
5. MoveIt映射到`joint_trajectory_controller/follow_joint_trajectory` Action。ros2_control官方文档指出Action是推荐的可监控接口，支持path/goal tolerances；topic接口则是fire-and-forget，不能向发送方报告目标容差失败。当前示例使用Action映射，但必须动态确认Action服务活跃、成功/取消/中止结果均能正确传回MoveIt。
6. 上游`interpolate_from_desired_state=true`与VAL3速度反馈仅为近似值的组合，是需要特别验证的闭环一致性风险：新轨迹起点可能基于旧命令状态，而Action跟踪误差和完成判断仍依赖状态接口。不能将RViz中规划/执行显示正常当作真实机械臂到位证据。

### E. 新增验收矩阵

| ID | 场景 | 通过条件 | 当前状态 |
|---|---|---|---|
| TRJ-01 | 目标位置与herej逐轴对照 | 目标、实际位置、误差、单位、时间戳同帧可追踪；到位判断使用经确认的逐轴容差 | 未实现/未执行 |
| TRJ-02 | isSettled抖动、短暂停顿、低速爬行 | 明确VAL3 settled语义、滞回/稳定窗口和速度阈值；不把瞬时false→true当作轨迹成功 | 未实现/未执行 |
| TRJ-03 | movejSync状态-2/-1/0/1/2逐状态注入 | 每种状态有定义明确的ROS可见状态、错误/停止策略和恢复规则 | 未实现/未执行 |
| TRJ-04 | Action目标接受、执行、成功、拒绝、取消、超时、抢占 | MoveIt收到正确的GoalStatus/result；成功必须对应实际状态容差，失败不能被误报成功 | 未实现/未执行 |
| TRJ-05 | 缺省/显式path_tolerance、goal_tolerance、goal_time_tolerance | 记录MoveIt实际发送目标和JTC解析后的有效值；位置与速度容差均有明确工程依据 | 未实现/未执行 |
| TRJ-06 | goal_time=0、正宽限时间、执行延迟 | 验证按Jazzy版本实际超时行为；超时结果与机器人停止/保持策略一致 | 未实现/未执行 |
| TRJ-07 | allow_nonzero_velocity_at_trajectory_end开/关及末端非零速度 | 末端速度要求、停止判定和Action成功语义无冲突；测量实际末端速度 | 未实现/未执行 |
| TRJ-08 | interpolate_from_desired_state开/关、跟踪偏差后新轨迹 | 比较插值起点、实际herej和JTC desired/actual/error；抢占/重启无隐藏位置跳变 | 未实现/未执行 |
| TRJ-09 | VAL3 herej/getJntSpeedCmd/isSettled数据质量 | 对每个字段验证来源、更新周期、量纲、误差/噪声、无效值与故障传播；速度近似值不得被误称实测值 | 未实现/未执行 |
| TRJ-10 | UDP状态重复/延迟/乱序/断流与轨迹末端到位 | 重复帧不能刷新“完成”确认；状态新鲜度、序号推进、目标ID/会话关联均满足要求 | 未实现/未执行 |
| TRJ-11 | 轨迹成功后继续漂移、外力扰动、刹车/HOLD | 到位成功需规定稳定保持窗口和扰动后撤销/失效语义；明确非安全级监测边界 | 未实现/未执行 |
| TRJ-12 | 250Hz JTC、20Hz Action monitor与4ms VAL3周期的端到端时序 | 记录命令/状态时间戳、反馈延迟、完成确认延迟及P50/P95/P99/P99.9/max | 未实现/未执行 |

### F. 结论与优先建议

当前公开实现存在清晰的状态语义断层：VAL3提供全局`isSettled()`运动标志和`herej()`当前关节位置，但未形成目标ID关联的到位确认；movejSync状态仅描述执行器运行/错误/锁定状态；C++状态读取成功只说明有效类型和未过期报文已读到；ROS Action理论上可根据实际状态和容差返回结果，但配置未显式给出逐轴path/goal容差，且轨迹插值起点配置为上一条期望命令状态。

优先建议：定义端到端轨迹状态机（RECEIVED/ACCEPTED/EXECUTING/SETTLING/SUCCEEDED/ABORTED/CANCELED/STALE），为每个轨迹/命令分配可回显的ID和会话epoch；在VAL3或ROS监督层实现目标位置逐轴误差、速度阈值、稳定保持时间、状态新鲜度联合判定；明确JTC path/goal容差与goal_time参数，检查MoveIt真实Action目标；评估将`interpolate_from_desired_state`改为false是否更符合当前硬件闭环语义，任何变更需在仿真/HIL中比较，不能直接在实机启用；修正速度反馈来源/命名并为无效状态提供显式标志。

ROS轨迹完成状态仅作为应用层监督，不是安全功能；急停、SS1/SS2、STO、制动器和安全PLC仍须由经认证的独立安全链承担。未执行ROS构建/测试、MoveIt轨迹、VAL3编译/SRS仿真、CS9 HIL或实机测试；未修改ICube上游代码。

### 本节来源记录（#1655–#1664）

| 编号 | 固定来源 | 用途 |
|---|---|---|
| #1655 | [updateState.pgx @ bd658e2](https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/val3/userapp/ros2_server/updateState.pgx) | isSettled、herej、getJntSpeedCmd及状态有效位 |
| #1656 | [RobotState.dtx @ bd658e2](https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/val3/userapp/ros2_server/Types/RobotState/RobotState.dtx) | RobotState字段不含目标/轨迹ID及movejSync状态 |
| #1657 | [updateJointPositionControl.pgx @ bd658e2](https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/val3/userapp/ros2_server/Control/updateJointPositionControl.pgx) | movejSync状态语义、刷新异常处理和缺少目标完成回执 |
| #1658 | [controlTask.pgx @ bd658e2](https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/val3/userapp/ros2_server/controlTask.pgx) | 先发布状态后处理命令、模式状态和错误/停止流程 |
| #1659 | [robot_driver.cpp @ bd658e2](https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/src/robot_driver.cpp) | 状态读取成功语义、消息新鲜度和序号更新 |
| #1660 | [staubli_hardware_interface.cpp @ bd658e2](https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/src/staubli_hardware_interface.cpp) | ROS state/read/write和in_motion/关节反馈映射 |
| #1661 | [messages.hpp/messages.cpp @ bd658e2](https://github.com/ICube-Robotics/staubli_driver_ros2/tree/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/src/communication) | RobotState协议字段和C++状态反序列化 |
| #1662 | [controllers.yaml @ bd658e2](https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_bringup/config/controllers.yaml) | JTC周期、末端速度、插值和goal_time参数 |
| #1663 | [moveit_controllers.yaml @ bd658e2](https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_moveit_config/config/moveit_controllers.yaml)；[MoveIt demo @ bd658e2](https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_driver_ros2/sphinx/demo_applications/moveit2.rst) | FollowJointTrajectory Action映射及执行说明 |
| #1664 | [test_staubli_hardware_interface.cpp @ bd658e2](https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/test/unit_tests/test_staubli_hardware_interface.cpp)；[troubleshooting.rst @ bd658e2](https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_driver_ros2/sphinx/demo_applications/troubleshooting.rst) | 测试覆盖仅普通mock read/write；文档故障排查不构成轨迹到位验收 |

### 相关ROS 2控制器规范

- [Jazzy JointTrajectoryController用户文档](https://control.ros.org/jazzy/doc/ros2_controllers/joint_trajectory_controller/doc/userdoc.html)：Action接口、path/goal容差与topic fire-and-forget区别。
- [Jazzy JointTrajectoryController参数文档](https://control.ros.org/jazzy/doc/ros2_controllers/joint_trajectory_controller/doc/parameters.html)：`goal_time`、`stopped_velocity_tolerance`及`interpolate_from_desired_state`语义。


---

## 9.3.35 轨迹取消、抢占、停止与受控减速语义（2026-11-07）

### A. 审查基线

- 上游固定commit：`bd658e2d266e315d2ee35f985fb352ea88306b79`。
- 核对ROS 2 Jazzy JointTrajectoryController取消/抢占语义、当前`controllers.yaml`与MoveIt Action映射，并沿HardwareInterface::write、VAL3 `controlTask`、`updateJointPositionControl`、`stopJointPositionControl`追踪命令路径。
- 来源#1665–#1673。静态源码、配置和官方文档审查；未运行ROS构建/Action测试、VAL3编译/SRS仿真、CS9 HIL或实机停止测试。

### B. JTC Action取消：取消目标不等于停止模式

1. Jazzy JTC文档明确：默认取消/抢占时立即保持当前关节位置；启用`constraints.decelerate_on_cancel`后，才会读取关节速度状态、按每轴`max_deceleration_on_cancel`生成减速至零速度的轨迹，再保持停止位置。
2. 当前`staubli_bringup/config/controllers.yaml`只设置`stopped_velocity_tolerance`和`goal_time`，没有设置`decelerate_on_cancel`，也没有任何每轴`max_deceleration_on_cancel`。按Jazzy参数默认值，受控减速功能关闭；不能将当前Action cancel描述为受控减速。
3. 默认取消路径在JTC中将当前状态位置写入hold-position轨迹，并把当前Action标记为canceled。它是控制器位置命令保持策略，不是VAL3 STOP命令，不是`stopMove()`，也不是CS9安全停止。
4. 该JTC取消回调不直接调用Staubli HardwareInterface生命周期接口或`RobotDriver::send_stop_all_command()`。HardwareInterface仍依据本地`current_control_mode_`生成命令；若仍处于JOINT_POSITION，则发送位置参考，而不是CommandType::STOP。
5. 因此取消动作对机械臂的实际减速/停止响应取决于当前速度、JTC hold轨迹更新、HardwareInterface周期、UDP送达和VAL3运动控制行为。仅凭Action状态变为CANCELED，不能断言机器人已经静止或在规定距离内停止。

### C. Action抢占、新轨迹替换与旧轨迹语义

1. Jazzy JTC只允许一个Action goal处于活动状态。新的Action goal到达时，旧活动goal会被abort并通知客户端，新轨迹按JTC定义的trajectory replacement规则替换当前轨迹；这不是“先执行CS9 STOP、确认静止、再启动新轨迹”。
2. 当前配置`interpolate_from_desired_state=true`，新轨迹插值起点可能取上一条期望/命令状态，而不是HardwareInterface当前反馈位置。若上一轨迹存在跟踪误差，抢占后的轨迹衔接可能延续期望状态偏差；必须测量desired/actual/error和真实轨迹。
3. JTC文档另指出，向`joint_trajectory` topic发送空轨迹会覆盖当前Action目标，但不会abort该Action。MoveIt配置映射到`follow_joint_trajectory` Action，因此正常MoveIt路径应使用Action；其他直接topic客户端仍可能制造Action状态与实际执行轨迹不一致。
4. 未发现上游驱动为每个轨迹建立独立ID、VAL3回显该ID或对被抢占轨迹提供控制器侧取消确认。旧Action被abort只证明ROS Action生命周期结束，不构成VAL3运动队列已清空的证据。

### D. VAL3停止链路、命令缓存与重新启动

1. VAL3 `controlTask.pgx`仅在收到STOP/ERROR命令模式（或错误路径）时，才按上一模式调用`stopJointPositionControl`，随后执行`stopMove()`和`resetMotion()`。JTC Action cancel本身不会把HardwareInterface的控制模式切换为STOP，因此不能据此认定会进入这条VAL3停止链。
2. `stopJointPositionControl.pgx`在`$movejSyncState()!=-1`时调用`$movejSyncEnd()`，随后立即设置`x_bError=false`返回；没有等待运动停止、检查最终速度或确认`isSettled()`。其返回成功仅代表该程序路径没有报告错误，不是静止确认。
3. `controlTask.pgx`在未收到新命令但缓存命令仍有效时，将“上一命令staleness检查”留作TODO，随后仍依据缓存命令类型继续执行位置控制更新。由此，通信中断/停止刷新不能被视为可靠的命令撤销；旧位置目标可能继续被重复提交/刷新。该风险不同于JTC Action正常取消时的hold-position命令路径。
4. STOP/ERROR分支中的`stopMove()`和`resetMotion()`是普通VAL3程序控制调用；本次静态检查没有证明其具有经配置的减速曲线、停止距离上限、独立安全等级或完成确认。它们不能替代安全PLC、SS1/SS2、STO或经验证的急停功能。
5. `updateJointPositionControl.pgx`在首次进入位置控制时调用`resetMotion()`，随后在`movejSyncState==-1`时调用`$movejSyncBegin()`。没有发现针对普通Action取消/抢占的操作员重新授权握手、停止完成ACK或新轨迹显式arming状态。VAL3的`bMotionPossible`软件门控与CS9安全状态仍需按目标控制器配置验证，不能推断其等同于完整重新授权。
6. 当VAL3报告仍在运动时，`controlTask`对STOP→运动模式转换有一个`bInMotion`检查并拒绝立即启动；但该检查使用前一轮发布/采样状态，不是静止确认协议，也没有独立的停止超时锁存和操作者ACK流程。

### E. 新增验收矩阵

| ID | 场景 | 通过条件 | 当前状态 |
|---|---|---|---|
| CXL-01 | 低速/高速轨迹中取消Action | 分别记录cancel响应、JTC desired/actual、关节速度、停止时间/距离；Action canceled不得提前等同静止 | 未实现/未执行 |
| CXL-02 | 默认`decelerate_on_cancel=false` | 证实默认hold-position行为及其瞬态冲击、峰值误差和机械负载 | 未执行 |
| CXL-03 | 启用受控减速并配置逐轴减速度 | 验证速度反馈有效、减速度单位/限值、轨迹容量、同步停止时间和停止距离 | 未实现/未执行 |
| CXL-04 | cancel与UDP丢包/延迟/阻塞 | 丢包时不会持续重发旧目标；状态超时触发确定的停止/故障路径 | 未实现/未执行 |
| CXL-05 | Action新目标抢占旧目标 | 旧goal收到正确ABORTED结果，新轨迹替换起点与实际状态连续，无未授权跳变 | 未执行 |
| CXL-06 | 通过topic空轨迹覆盖活动Action | Action状态、实际轨迹与MoveIt状态不会出现静默不一致，或明确禁止该入口 | 未执行 |
| CXL-07 | cancel后立即提交新Action | 规定是否允许直接重启；如需静止/重新授权，必须有可验证的门控与超时 | 未实现/未执行 |
| CXL-08 | `movejSyncEnd()`执行中/异常/超时 | 验证调用结果、真实停止响应、错误传播和静止确认，不以函数返回代替停止 | 未执行 |
| CXL-09 | VAL3 STOP模式切换 | 验证stopMove/resetMotion真实响应、停止曲线、控制器状态和故障锁存 | 未执行 |
| CXL-10 | UDP断开但VAL3缓存命令有效 | 命令watchdog在有界时间内识别旧命令，禁止重复刷新旧目标并进入定义的故障态 | 未实现/未执行 |
| CXL-11 | 取消/抢占期间E-stop、HOLD、SS1/SS2 | 安全停止由独立安全链执行；ROS取消/抢占不得覆盖或复位安全状态 | 未执行 |
| CXL-12 | 取消后重新连接、Lifecycle deactivate/activate | 旧目标/旧epoch不复活；必须满足规定的安全状态、静止确认和授权条件 | 未执行 |

### F. 结论与优先建议

当前栈存在三个不同层次，不能混用：**JTC Action取消**默认将期望命令切换为当前位置保持；**VAL3 STOP模式**才调用`$movejSyncEnd()`、`stopMove()`和`resetMotion()`；**CS9安全停止**由独立安全链承担。当前MoveIt Action取消不会自动切换到VAL3 STOP，JTC配置未启用受控减速，VAL3缓存命令staleness仍为TODO，且停止函数不等待静止确认。

优先建议：为JTC明确选择经验证的取消策略（受控减速或hold-position），不能只启用参数而不验证速度反馈和每轴减速度；在驱动层定义明确的STOP/取消命令语义、命令epoch和超时watchdog；为VAL3停止流程增加有界等待、状态回执、静止判定和故障锁存；为Action cancel/preempt/MoveIt cancel/控制器重启定义一致的状态机与重新授权规则；禁止或显式监管绕过Action的topic轨迹入口。所有减速/停止距离和安全功能必须由目标CS9配置、风险评估及SIL/HIL/实机测试证据支持。

应用层取消、hold和停止监督不是安全功能；急停、SS1/SS2、STO、制动器和安全PLC仍须由经认证的独立安全链承担。未执行ROS构建/测试、Action取消/抢占测试、UDP故障注入、VAL3编译/SRS仿真、CS9 HIL或实机停止测试；未修改ICube上游代码。

### 本节来源记录（#1665–#1673）

| 编号 | 固定来源 | 用途 |
|---|---|---|
| #1665 | [Jazzy JointTrajectoryController用户文档](https://control.ros.org/jazzy/doc/ros2_controllers/joint_trajectory_controller/doc/userdoc.html) | Action cancel/preemption、topic空轨迹覆盖及Action状态语义 |
| #1666 | [Jazzy Decelerate on cancel](https://control.ros.org/jazzy/doc/ros2_controllers/joint_trajectory_controller/doc/decelerate_on_cancel.html) | 默认hold与受控减速的条件、速度反馈和逐轴减速度要求 |
| #1667 | [Jazzy JTC参数文档](https://control.ros.org/jazzy/doc/ros2_controllers/joint_trajectory_controller/doc/parameters.html) | decelerate_on_cancel/max_deceleration_on_cancel默认值 |
| #1668 | [controllers.yaml @ bd658e2](https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_bringup/config/controllers.yaml) | 当前JTC取消/减速参数未配置 |
| #1669 | [staubli_hardware_interface.cpp @ bd658e2](https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/src/staubli_hardware_interface.cpp) | write仍按本地控制模式发位置或STOP命令 |
| #1670 | [controlTask.pgx @ bd658e2](https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/val3/userapp/ros2_server/controlTask.pgx) | STOP模式调用链、缓存命令staleness TODO及错误路径 |
| #1671 | [updateJointPositionControl.pgx @ bd658e2](https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/val3/userapp/ros2_server/Control/updateJointPositionControl.pgx) | movejSync启动、刷新与状态处理 |
| #1672 | [stopJointPositionControl.pgx @ bd658e2](https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/val3/userapp/ros2_server/Control/stopJointPositionControl.pgx) | movejSyncEnd后无等待/静止确认 |
| #1673 | [moveit_controllers.yaml @ bd658e2](https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_moveit_config/config/moveit_controllers.yaml) | MoveIt使用FollowJointTrajectory Action而非topic映射 |


---

## 9.3.36 MoveIt取消传播、控制器故障与执行结果一致性（2026-11-07）

### A. 审查基线与范围

- Stäubli上游固定commit：`bd658e2d266e315d2ee35f985fb352ea88306b79`。
- MoveIt 2 Jazzy源码固定commit：`6ed6372a72ba9b121ed12ef574ea4ff4d3d92f09`。
- 核对Stäubli MoveIt launch/controller配置，并分别追踪`MoveGroup` Action与`ExecuteTrajectory` Action、PlanExecution、TrajectoryExecutionManager（TEM）、MoveItSimpleControllerManager和FollowJointTrajectory Action结果。
- 来源#1674–#1681。静态源码审查；未运行MoveIt/ROS构建、Action集成测试、控制器故障注入、SRS/CS9 HIL或实机测试。

### B. Stäubli配置与两条MoveIt执行入口

1. `staubli_moveit.launch.py`直接启动`move_group`，由`MoveItConfigsBuilder(...).to_moveit_configs()`提供MoveIt参数；本仓库`moveit_controllers.yaml`选择`moveit_simple_controller_manager/MoveItSimpleControllerManager`，控制器Action为`joint_trajectory_controller/follow_joint_trajectory`。
2. MoveIt存在不同的Action入口，不能把其取消逻辑混为一谈：
   - `MoveGroup` Action：组合规划与执行入口。
   - `ExecuteTrajectory` Action：执行已给定的RobotTrajectory；MoveGroupInterface的execute()路径使用该Action。
   - 两者最终均可能经TEM与MoveIt controller handle调用底层FollowJointTrajectory Action，但上游Action取消回调的接线不同。

### C. MoveGroup Action取消传播：存在明确的停止调用链

1. Jazzy `move_action_capability.cpp`的MoveGroup Action cancel回调调用`preemptMoveCallback()`，然后返回ACCEPT。
2. `preemptMoveCallback()`设置`preempt_requested_=true`并调用`PlanExecution::stop()`。
3. `PlanExecution::stop()`设置内部preempt标志；正在执行的`executeAndMonitor()`循环检查该标志，退出监控循环后调用`TrajectoryExecutionManager::stopExecution()`。
4. PlanExecution将结果设为`MoveItErrorCodes::PREEMPTED`；MoveGroup Action回调最终调用`goal->canceled(action_res)`。因此这条MoveGroup Action路径在静态源码中有完整的软件取消传播链。
5. 但TEM的stopExecution只向控制器Action请求cancel，并不发VAL3 STOP或CS9安全停止；取消响应不是机械臂静止证明。该路径的物理停止行为仍继承§9.3.35的JTC默认hold和VAL3停止确认缺口。

### D. ExecuteTrajectory Action取消：取消回调与停止函数未接线

1. `execute_trajectory_action_capability.cpp`创建ExecuteTrajectory Action server时，cancel回调只有`return CancelResponse::ACCEPT`，没有调用`preemptExecuteTrajectoryCallback()`或TEM的`stopExecution()`。
2. 类中确实声明并定义了`preemptExecuteTrajectoryCallback()`，其函数体会调用`trajectory_execution_manager_->stopExecution(true)`；但在该固定Jazzy源码中，全文搜索只发现声明和定义，没有找到任何调用点。它没有被传给Action server的cancel回调。
3. 执行回调调用`executePath()`后同步等待`waitForExecution()`。当前cancel回调只接受取消请求，不会使该等待路径主动停止TEM。由此存在高风险：客户端收到取消请求被接受的响应，但控制器轨迹仍可能继续执行；Action执行回调后续还会走正常结果终结代码。
4. 即使将停止函数接线，`executePath()`会把TEM的PREEMPTED映射为MoveIt PREEMPTED，但`executePathCallback()`只在SUCCESS时调用`goal->succeed()`，其余所有结果统一调用`goal->abort()`，没有对PREEMPTED调用`goal->canceled()`。这与Action取消的终态语义不一致。
5. 这是静态源码接线缺口；Action协议状态在运行时的具体表现（canceling状态能否保持、后续succeed/abort调用是否被拒绝或报错、客户端是否超时）尚未实测。不能将其写成已验证的运行时故障，但必须作为P1/P0集成验收项。

### E. TEM与ControllerHandle的取消确认、状态和等待问题

1. Jazzy TEM的`stopExecutionInternal()`遍历活动controller handles调用`cancelExecution()`，但忽略该函数返回的bool值，只捕获异常。随后`stopExecution()`提前设置`execution_complete_=true`并将`last_execution_status_`设置为PREEMPTED，再join执行线程。软件状态因此可能先于控制器真实取消结果被标记为PREEMPTED。
2. `ActionBasedControllerHandle::cancelExecution()`调用`async_cancel_goal(current_goal_)`并等待Cancel response；但只检查response指针是否为空，没有验证response的return_code或`goals_canceling`是否包含当前goal。只要response对象非空，就设置PREEMPTED、`done_=true`并返回true。取消被拒绝/未命中当前goal时存在误报PREEMPTED的风险。
3. `waitForExecution()`仍等待Action最终result；取消响应仅表示取消请求处理结果，不代表最终result已到达，更不代表机器人静止。控制器拒绝取消、Action server失联或不返回终态时，等待线程可能长期阻塞；TEM的stopExecution随后join该线程，停止调用也可能被拖住。需要有界等待、结果超时和明确的故障升级策略。
4. FollowJointTrajectory的`controllerDoneCallback()`会记录result payload中的`error_code/error_string`，但最终`finishControllerExecution()`只根据外层rclcpp Action `wrapped_result.code`更新ExecutionStatus，没有把payload的`error_code`纳入状态判定。对非标准或异常Action server，外层SUCCEEDED与payload非SUCCESSFUL可能产生状态不一致；标准JTC通常通过ABORTED表达执行错误，但仍应加入一致性测试。
5. TEM的`executeThread()`在last status为SUCCEEDED时调用`waitForRobotToStop()`，但忽略其bool返回值；即使状态采样失败或1秒内未观察到连续3次无运动，仍可能保留SUCCEEDED并通知完成。其“静止”判定是连续状态位置变化小于allowed start tolerance，并非基于独立速度阈值、目标位置误差或安全控制器静止信号。
6. 该等待仅位于成功完成路径；外部stopExecution设置`execution_complete_=true`后，executeThread不会进入成功等待分支。因此取消路径没有等价的机器人静止确认。另，成功路径调用waitForRobotToStop时持有`execution_state_mutex_`，并发stopExecution需等待该临界区结束，可能增加取消响应延迟。
7. 当前TEM默认执行时长监控开启，默认允许时长为预估轨迹时长乘1.1并增加0.5秒；但这只是MoveIt执行监控超时，不是机械停止时间/距离保证，也不能替代控制器Action结果和状态新鲜度检查。

### F. 故障传播与状态一致性结论

- **MoveGroup Action**：源码上有cancel→preempt flag→PlanExecution→TEM→controller Action cancel的链；Action最终可返回CANCELED/PREEMPTED，但TEM/ControllerHandle仍可能在取消未确认时提前报告PREEMPTED。
- **ExecuteTrajectory Action**：cancel回调只接受请求，没有调用现有preempt停止函数；停止调用链静态上未接通。即使TEM返回PREEMPTED，当前Action终结代码仍统一走ABORTED分支。
- **控制器Action**：MoveIt等待最终result；取消请求response、Action终态、FollowJointTrajectory payload error_code和机械臂静止是四种不同证据，不能互相替代。
- **执行成功**：TEM对waitForRobotToStop()失败不处理，存在“状态流未证明静止但执行结果仍SUCCEEDED”的风险。
- **节点/控制器故障**：需要注入move_group退出、JTC lifecycle deactivate/error、Action server失联、UDP断链、反馈停止更新和取消拒绝，确认MoveIt不将未知/失联状态误报成功，且有界超时后进入明确故障态。

### G. 新增验收矩阵

| ID | 场景 | 通过条件 | 当前状态 |
|---|---|---|---|
| MEX-01 | MoveGroup Action规划中取消 | cancel触发preempt标志，MoveGroup以CANCELED终结，无后续意外执行 | 未执行 |
| MEX-02 | MoveGroup Action执行中取消 | TEM stopExecution被调用；底层JTC收到cancel；Action结果与控制器终态一致 | 未执行 |
| MEX-03 | ExecuteTrajectory Action执行中取消 | cancel回调必须调用TEM stopExecution；当前源码接线缺口须先修复/验证 | 静态发现缺口 |
| MEX-04 | ExecuteTrajectory取消终态 | PREEMPTED映射为Action CANCELED，而不是统一ABORTED；无重复/非法终结 | 静态发现终态映射缺口 |
| MEX-05 | 控制器拒绝cancel | 检查Cancel response return_code和goals_canceling；不得无条件标记PREEMPTED | 静态发现确认不足 |
| MEX-06 | cancel response成功但result迟迟不返回 | 有界等待、超时诊断和故障升级；不得无限join或假报已停止 | 未执行 |
| MEX-07 | TEM controller handle返回false/抛异常 | 取消失败被传播为失败/未知状态，不得无条件PREEMPTED | 静态发现返回值被忽略 |
| MEX-08 | 外层Action SUCCEEDED但payload error_code非SUCCESSFUL | MoveIt报告控制失败/结果不一致，不得假报成功 | 未执行 |
| MEX-09 | waitForRobotToStop超时 | TEM将失败映射为TIMED_OUT/CONTROL_FAILED；不得保留SUCCEEDED | 静态发现返回值被忽略 |
| MEX-10 | joint state停止更新/时间戳陈旧 | 停止确认失败并进入STALE/FAULT，不以重复旧状态当作静止 | 未执行 |
| MEX-11 | cancel与成功收尾并发 | 验证execution_state_mutex竞争、取消延迟、Action结果唯一且无竞态 | 未执行 |
| MEX-12 | move_group/JTC退出、deactivate、UDP断链 | 有界检测、停止/安全链响应、MoveIt返回失败且不残留旧goal | 未执行 |
| MEX-13 | 取消完成后新目标提交 | 旧goal终态确认、控制器状态刷新、静止/授权条件满足后才允许重启 | 未执行 |
| MEX-14 | MoveGroup与ExecuteTrajectory双入口并发 | 单一执行仲裁；禁止两个入口对同一机械臂并行写入或状态错配 | 未执行 |

### H. 优先整改建议

1. 修复ExecuteTrajectory Action cancel回调，直接调用统一的取消/停止协调器；终态必须区分SUCCESS、CANCELED/PREEMPTED、ABORTED和UNKNOWN。
2. 为MoveGroup和ExecuteTrajectory共用一个执行状态机/仲裁层，明确每个goal UUID到控制器goal的映射，防止两个入口并行控制或取消错对象。
3. ControllerHandle必须校验Cancel response的return_code及goals_canceling；TEM必须检查cancelExecution()返回值并将取消拒绝、通信失败和Action超时传播为明确状态，不能先验设置PREEMPTED。
4. 为Action最终result等待设置单调时钟超时；超时后报告控制器失联/状态未知，触发独立故障策略，不能无限等待。
5. TEM必须处理waitForRobotToStop()的false结果；将“Action成功”“轨迹控制器成功”“机器人反馈静止”“目标位置误差合格”分开定义和报告。静止确认应使用新鲜状态、速度/位置增量阈值、连续稳定时间及明确超时。
6. 成功收尾和取消路径都需要相同的状态新鲜度及停止确认策略；不得仅在SUCCEEDED路径检查静止，也不得在取消时把PREEMPTED当作停止确认。
7. 所有软件路径都不是安全停止功能；E-stop、SS1/SS2、STO、制动器及安全PLC必须独立有效。

本轮只完成静态源码/配置审查及文档维护；未执行MoveIt/ROS构建、Action集成测试、取消拒绝/超时故障注入、JTC lifecycle故障、UDP断链、VAL3/SRS、CS9 HIL或实机测试。未修改MoveIt或ICube上游代码。

### 本节来源记录（#1674–#1681）

| 编号 | 固定来源 | 用途 |
|---|---|---|
| #1674 | [MoveGroup Action capability @ MoveIt Jazzy commit 6ed6372](https://github.com/moveit/moveit2/blob/6ed6372a72ba9b121ed12ef574ea4ff4d3d92f09/moveit_ros/move_group/src/default_capabilities/move_action_capability.cpp) | MoveGroup Action取消回调、PlanExecution stop和CANCELED终态 |
| #1675 | [PlanExecution @ MoveIt Jazzy commit 6ed6372](https://github.com/moveit/moveit2/blob/6ed6372a72ba9b121ed12ef574ea4ff4d3d92f09/moveit_ros/planning/plan_execution/src/plan_execution.cpp) | preempt flag、TEM stopExecution、PREEMPTED映射 |
| #1676 | [TrajectoryExecutionManager @ MoveIt Jazzy commit 6ed6372](https://github.com/moveit/moveit2/blob/6ed6372a72ba9b121ed12ef574ea4ff4d3d92f09/moveit_ros/planning/trajectory_execution_manager/src/trajectory_execution_manager.cpp) | stopExecution忽略cancel返回值、PREEMPTED设置、等待静止结果忽略 |
| #1677 | [ActionBasedControllerHandle @ MoveIt Jazzy commit 6ed6372](https://github.com/moveit/moveit2/blob/6ed6372a72ba9b121ed12ef574ea4ff4d3d92f09/moveit_plugins/moveit_simple_controller_manager/include/moveit_simple_controller_manager/action_based_controller_handle.hpp) | async_cancel_goal响应检查与PREEMPTED设置、Action result等待 |
| #1678 | [FollowJointTrajectoryControllerHandle @ MoveIt Jazzy commit 6ed6372](https://github.com/moveit/moveit2/blob/6ed6372a72ba9b121ed12ef574ea4ff4d3d92f09/moveit_plugins/moveit_simple_controller_manager/src/follow_joint_trajectory_controller_handle.cpp) | result payload错误日志与wrapped_result.code状态映射 |
| #1679 | [ExecuteTrajectory Action capability @ MoveIt Jazzy commit 6ed6372](https://github.com/moveit/moveit2/blob/6ed6372a72ba9b121ed12ef574ea4ff4d3d92f09/moveit_ros/move_group/src/default_capabilities/execute_trajectory_action_capability.cpp) | cancel回调仅ACCEPT、preempt函数无调用连接、PREEMPTED终态走abort |
| #1680 | [Stäubli MoveIt launch @ bd658e2](https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_moveit_config/launch/staubli_moveit.launch.py) | MoveGroup节点启动及MoveIt配置装载 |
| #1681 | [Stäubli MoveIt controllers @ bd658e2](https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_moveit_config/config/moveit_controllers.yaml) | SimpleControllerManager与FollowJointTrajectory Action映射 |


## 9.3.37 MoveIt / ros2_control 控制器生命周期、启动就绪与故障恢复（2026-11-07）

### A. 审查范围与版本边界

- ICube Stäubli ROS 2驱动固定commit：`bd658e2d266e315d2ee35f985fb352ea88306b79`。
- MoveIt 2 Jazzy固定commit：`6ed6372a72ba9b121ed12ef574ea4ff4d3d92f09`。
- 核对 `launch_robot_control.launch.py`、`launch_moveit.launch.py`、`launch_demo.launch.py`、`wait_for_robot_ready.py`、`controllers.yaml`、HardwareInterface生命周期回调，以及MoveItSimpleControllerManager/ActionBasedControllerHandle。
- ros2_control框架行为按ROS 2 Jazzy官方文档理解；JointStateBroadcaster QoS实现另以公开源码作线索。对SystemDefaultsQoS最终解析结果仍需在目标RMW/发行版运行时确认。
- 本节是静态源码与配置审查；未执行ROS构建、launch集成、QoS兼容性测试、控制器故障注入、MoveIt Action集成、UDP断链、VAL3/SRS、CS9 HIL或实机验证。

### B. 启动编排与控制器激活顺序

1. `launch_robot_control.launch.py`启动robot_state_publisher、ros2_control_node及RViz，并创建joint_state_broadcaster和joint_trajectory_controller两个spawner。
2. joint_state_broadcaster通过spawner加载并激活；JTC则由spawner带`--inactive`加载/配置。只有`start_controller`参数与控制器名匹配时，spawner进程退出事件才会触发`ros2 control set_controller_state ... active`。
3. `start_controller`默认值是`none`。因此单独运行该launch且不覆盖参数时，JTC会保持inactive；不能仅凭ros2_control_node和JTC spawner进程存在，就认为FollowJointTrajectory Action Server可接收目标。
4. `launch_demo.launch.py`显式把`start_controller`覆盖为`joint_trajectory_controller`，因此示例总启动路径有意激活JTC。独立启动文档也要求显式传入该参数。
5. 激活动作挂在spawner的OnProcessExit事件上，没有检查spawner退出码是否成功；事件处理本身也没有将`set_controller_state`的结果反馈给启动状态机。若spawner失败退出，后续激活命令仍可能被触发。应将“spawner成功完成且controller state确认为active”作为下一步前置条件。
6. LaunchDescription中的Node列表并不等价于严格的硬件就绪依赖图。spawner会等待controller_manager服务，但当前bringup没有建立覆盖硬件ACTIVE、joint_state_broadcaster ACTIVE、JTC ACTIVE和Action Server可用性的统一启动屏障。

### C. wait_for_robot_ready的检查范围与QoS风险

1. `launch_moveit.launch.py`先启动`wait_for_robot_ready.py`，并通过OnProcessExit在该进程退出后启动MoveIt launch。该设计意图是等待robot_description和joint_states可用。
2. 等待节点分别订阅`robot_description`和`joint_states`，两者都使用depth=1、durability=TRANSIENT_LOCAL；Future只在收到各自第一条消息后完成。没有检查消息时间戳、关节名称/数量、NaN/Inf、状态序号或连续更新。
3. 它没有查询controller_manager的hardware/controller lifecycle state，也没有检查`/joint_trajectory_controller/follow_joint_trajectory` Action Server是否可用。因此“Robot is ready”只代表两个主题各收到过至少一条消息，不代表机械臂控制链路可执行。
4. JointStateBroadcaster公开实现使用`rclcpp::SystemDefaultsQoS()`创建joint_states publisher；ROS 2默认QoS durability通常为VOLATILE，而本等待节点请求TRANSIENT_LOCAL。按ROS 2 QoS兼容规则，VOLATILE publisher与TRANSIENT_LOCAL subscriber不兼容，可能完全无法匹配，导致Future不完成、MoveIt launch一直等待。该结论是高优先级静态配置风险；最终需在目标Jazzy安装版本、RMW实现和实际publisher QoS上用`ros2 topic info --verbose`及集成测试确认，不能仅由源码默认值推断所有部署环境必然失败。
5. `OnProcessExit`没有检查waiter退出码。正常路径由Future完成后退出；若进程被外部终止/异常退出，事件仍可能启动MoveIt，形成“等待失败但继续启动”的风险。建议明确成功退出码/ready结果，不以任意进程退出作为ready信号。

### D. MoveIt对控制器active状态的认识与Action可用性

1. Stäubli的`moveit_controllers.yaml`使用`moveit_simple_controller_manager/MoveItSimpleControllerManager`，并映射到`joint_trajectory_controller/follow_joint_trajectory`。
2. 固定MoveIt Jazzy源码中，SimpleControllerManager初始化每个配置控制器后直接设置`state.active_=true`；`getActiveControllers()`返回全部配置控制器。源码注释明确说明该插件假设所有控制器已经active，且没有能力处理未激活情况。它不会向ros2_control controller_manager查询JTC真实生命周期状态。
3. ActionBasedControllerHandle构造时创建Action client并不保证Action Server存在；`isConnected()`实际调用`action_server_is_ready()`，FollowJointTrajectory的`sendTrajectory()`在发送前才检查这一点。JTC inactive、尚未启动或Action Server掉线时，MoveIt的静态控制器清单仍可能显示控制器active，而真正发送目标时失败。
4. 因此MoveIt规划可用、MoveIt控制器插件声明active、ros2_control JTC lifecycle active、Action Server ready是四种不同状态。当前启动ready节点没有把它们串成统一准入门槛。
5. MoveIt节点重启会重新创建静态SimpleControllerManager句柄；这并不意味着底层JTC已经active或机器人反馈已恢复。当前bringup没有对move_group异常退出建立自动重启、控制器状态重新同步或旧Action清理机制。

### E. 硬件错误、控制器停用与恢复路径

1. ros2_control Jazzy文档说明：硬件read/write返回ERROR时，ControllerManager会停止使用该硬件command/state interfaces的控制器；硬件组件进入错误生命周期处理。控制器update返回ERROR时，对应控制器/控制器链会被deactivate，并可尝试fallback controllers。硬件重启后需要重新走生命周期以重新配置并导出interfaces。
2. ICube HardwareInterface在driver未连接、RobotState读取失败或update_state失败时，read返回ERROR；write在连接丢失或机器人错误状态下也可返回ERROR。由此可触发框架层控制器停用，但这不是MoveIt Action cancel确认，更不是CS9安全停止确认。
3. ICube `on_error()`若driver仍连接会尝试`send_stop_all_command()`，但忽略其bool返回值并返回SUCCESS；该回调没有显式disconnect，也没有自动重连循环。若driver已断开则返回ERROR。它没有报告“STOP已确认/机器人静止”状态。
4. HardwareInterface `on_configure()`负责调用RobotDriver::connect；`on_activate()`仅把本地控制模式设为STOP。源码没有形成完整自动恢复状态机：断链检测→旧goal终结→停止确认/故障锁存→通信重新握手→反馈新鲜度确认→控制器重新配置/激活→操作员/上层重新授权。
5. 由于前序§9.3.22已发现协议没有controller boot ID/session nonce，且命令序号以状态序号为基础，恢复后必须额外处理旧UDP帧/旧目标与新连接会话的隔离。当前静态证据不足以断言旧轨迹会自动恢复执行；同样也不足以证明旧Action、缓存命令及MoveIt执行状态在重连后一定被安全清除。
6. 当前JTC重启、Action Server重新出现与MoveIt旧Action goal之间没有被本bringup统一协调。需要验证旧goal最终是ABORTED/CANCELED/UNKNOWN、客户端是否退出等待，以及恢复后是否必须提交全新轨迹。不得将Action Server重新上线等同于旧轨迹续跑，也不得假定它自动完成了重新授权。
7. 当前配置的`moveit_manage_controllers`未见显式启用，TEM初始化默认不负责管理控制器；Stäubli SimpleControllerManager本身也不管理ros2_control生命周期。控制器启动/恢复责任主要留在bringup/operator流程。

### F. 关键风险与分级

- **P1：启动就绪误判。** ready节点不检查JTC active和Action Server ready；MoveIt可能先启动、先规划，直到执行时才发现控制器不可用。
- **P1（条件性，需目标环境复现）：QoS durability不兼容。** wait_for_robot_ready请求TRANSIENT_LOCAL，而JointStateBroadcaster用SystemDefaultsQoS；默认VOLATILE场景下不会建立匹配，等待可能永久挂起。
- **P1：控制器状态虚报active。** MoveItSimpleControllerManager把所有已配置控制器标记active，不查询ros2_control；规划与执行准入状态不一致。
- **P1：spawner失败仍触发后续激活命令。** OnProcessExit不检查退出码；没有明确的失败分支与ready状态上报。
- **P1：故障恢复缺少统一协调。** Hardware ERROR可停用控制器，但MoveIt goal、Action Server、UDP会话、旧命令与重新授权没有统一状态机。
- **P0安全边界：** 以上ROS/MoveIt生命周期逻辑均不是安全功能。断网、进程退出、控制器deactivate或Action Server消失不能替代CS9安全停止、STO/SS1/SS2、安全PLC和制动器验证。

### G. 新增验收矩阵

| ID | 场景 | 通过条件 | 当前状态 |
|---|---|---|---|
| LFR-01 | 单独启动robot_control，start_controller默认none | JTC保持inactive；系统清晰报告不可执行，不误报控制ready | 静态确认默认none；未运行 |
| LFR-02 | spawner加载/配置失败 | 不触发激活命令；启动失败被上报且MoveIt不进入可执行ready | 静态发现OnProcessExit无退出码检查 |
| LFR-03 | spawner成功但controller activation失败 | 必须检查controller state与service结果；MoveIt保持执行禁止 | 未执行 |
| LFR-04 | wait_for_robot_ready QoS匹配 | 在目标Jazzy/RMW上验证publisher/subscriber durability兼容并成功收到joint_states | 静态发现条件性不兼容风险 |
| LFR-05 | joint_states只有单帧后停止 | ready不得长期保持；必须验证状态时间戳/连续更新/最大年龄 | 静态发现只检查首帧 |
| LFR-06 | robot_description/joint_states存在但JTC inactive | MoveIt readiness必须失败或标记不可执行 | 静态发现未检查JTC状态 |
| LFR-07 | JTC active但Action Server未ready | 不允许提交轨迹；提供有界等待和清晰诊断 | 静态发现缺少启动屏障 |
| LFR-08 | JTC执行中Hardware read/write返回ERROR | controller deactivate、Action终态、MoveIt结果和停止状态一致；无假成功 | 未执行 |
| LFR-09 | UDP断链后重新连接 | 旧goal/旧报文被隔离；状态刷新、STOP确认、控制器重新激活和新授权按序发生 | 未执行 |
| LFR-10 | move_group进程重启 | 重新读取当前控制器状态/Action server状态；旧goal有明确终态；不自动续跑旧目标 | 未执行 |
| LFR-11 | JTC lifecycle deactivate/activate | Action Server消失/恢复行为可预测；MoveIt不把静态active标记当作真实状态 | 未执行 |
| LFR-12 | wait_for_robot_ready异常退出 | 非成功退出不得触发MoveIt启动 | 静态发现OnProcessExit未检查退出码 |
| LFR-13 | 硬件ERROR后手动reconfigure/activate | driver连接状态幂等；重新导出接口；反馈新鲜且安全状态满足后才能启动控制器 | 未执行 |
| LFR-14 | 恢复后提交新轨迹 | 必须建立新执行ID/session epoch；旧轨迹不会被隐式恢复或混淆 | 未执行 |

### H. 整改建议

1. 把启动编排改为显式依赖状态机：ControllerManager服务ready→硬件ACTIVE→joint_state_broadcaster ACTIVE→JTC ACTIVE→JointState连续新鲜→FollowJointTrajectory Action Server ready→MoveIt execution ready。每一步均检查服务响应/状态，不使用仅凭进程退出的事件推断成功。
2. 修正wait_for_robot_ready QoS：对robot_description和joint_states分别采用与真实publisher兼容的QoS；joint_states通常应使用VOLATILE订阅，并增加持续更新时间/关节完整性检查。目标RMW需运行时确认。
3. 若继续使用MoveItSimpleControllerManager，增加外部执行准入监控并在Action Server不ready时阻止执行；更合适的方案是评估MoveIt ROS2ControlManager插件，让MoveIt读取真实controller_manager状态。无论哪种方案，都需要明确管理控制器是否由TEM负责。
4. Launch事件处理检查spawner和set_controller_state的返回码；失败时阻止后续MoveIt ready，提供有限超时和可诊断的失败状态。
5. 设计统一RecoveryCoordinator：任何Hardware ERROR/UDP断链/Action Server消失均使当前trajectory进入ABORTED或UNKNOWN，执行独立停止策略并锁存故障；恢复时重新握手、刷新反馈、验证CS9安全状态、清理旧goal/命令、重新激活控制器，再等待明确的新授权。
6. 将move_group/JTC进程监控、Action goal超时、状态新鲜度和恢复会话ID纳入集成测试。MoveIt进程重启不应隐式恢复旧运动目标。
7. 所有恢复步骤均不得替代独立安全链；真实机器人测试前应由具备资质的人员制定低速、限区、急停和风险评估方案。

### I. 本节来源记录（#1682–#1692）

| 编号 | 固定来源 | 用途 |
|---|---|---|
| #1682 | [ICube launch_robot_control.launch.py @ bd658e2](`https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_bringup/launch/launch_robot_control.launch.py`) | spawner顺序、JTC inactive加载、start_controller默认none、OnProcessExit激活 |
| #1683 | [ICube wait_for_robot_ready.py @ bd658e2](`https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_bringup/scripts/wait_for_robot_ready.py`) | 双topic Future、TRANSIENT_LOCAL QoS、只等首帧 |
| #1684 | [ICube launch_moveit.launch.py @ bd658e2](`https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_bringup/launch/launch_moveit.launch.py`) | MoveIt由waiter退出事件触发 |
| #1685 | [ICube launch_demo.launch.py @ bd658e2](`https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_bringup/launch/launch_demo.launch.py`) | 示例总启动覆盖start_controller为JTC |
| #1686 | [ICube controllers.yaml @ bd658e2](`https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_bringup/config/controllers.yaml`) | 250Hz控制器配置和JTC参数 |
| #1687 | [ICube HardwareInterface @ bd658e2](`https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/src/staubli_hardware_interface.cpp`) | read/write ERROR、on_error STOP、configure connect、activate本地STOP |
| #1688 | [MoveIt SimpleControllerManager @ 6ed6372](`https://github.com/moveit/moveit2/blob/6ed6372a72ba9b121ed12ef574ea4ff4d3d92f09/moveit_plugins/moveit_simple_controller_manager/src/moveit_simple_controller_manager.cpp`) | 控制器静态active假设、不查询ros2_control状态 |
| #1689 | [MoveIt ActionBasedControllerHandle @ 6ed6372](`https://github.com/moveit/moveit2/blob/6ed6372a72ba9b121ed12ef574ea4ff4d3d92f09/moveit_plugins/moveit_simple_controller_manager/include/moveit_simple_controller_manager/action_based_controller_handle.hpp`) | Action client创建不保证server存在、send前检查ready |
| #1690 | [ROS 2 Control Jazzy Controller Manager docs](`https://control.ros.org/jazzy/doc/ros2_control/controller_manager/doc/userdoc.html`) | Hardware ERROR停用关联控制器及硬件重启生命周期 |
| #1691 | [JointStateBroadcaster publisher source](`https://github.com/ros-controls/ros2_controllers/blob/c8d26930ff87bc819db1452af1d45da5bfa3d50d/joint_state_broadcaster/src/joint_state_broadcaster.cpp`) | joint_states使用SystemDefaultsQoS |
| #1692 | [ROS 2 Jazzy QoS compatibility docs](`https://docs.ros.org/en/jazzy/Concepts/Intermediate/About-Quality-of-Service-Settings.html`) | VOLATILE publisher与TRANSIENT_LOCAL subscriber不兼容规则 |



## 9.3.38 MoveIt Servo、JTC与直接关节命令的互斥仲裁（2026-11-07）

### A. 审查范围与版本边界

- ICube Stäubli驱动固定commit：`bd658e2d266e315d2ee35f985fb352ea88306b79`。
- MoveIt 2 Jazzy固定commit：`6ed6372a72ba9b121ed12ef574ea4ff4d3d92f09`。
- 检查Servo launch/config、MoveIt控制器映射、ros2_control控制器配置、URDF ros2_control关节接口、HardwareInterface命令模式切换、MoveIt Servo暂停/超时实现及资源claim规则。
- 本节为静态源码与配置审查；未运行Servo、JTC与硬件接口集成，也未执行模式切换、碰撞/急停、真实机器人动态响应测试。

### B. 当前Servo命令链路并未闭合

1. `staubli_moveit.launch.py`提供`launch_servo`参数，默认false；参数为true时会额外启动`moveit_servo/servo_node`。Servo与move_group是并列启动的Node，没有先完成控制器切换再启动Servo的依赖/仲裁逻辑。
2. `staubli_servo.yaml`配置`command_out_type: std_msgs/Float64MultiArray`、`publish_joint_positions: true`，输出topic为`/forward_position_controller/commands`。
3. 当前`staubli_bringup/config/controllers.yaml`只注册`joint_state_broadcaster`和`joint_trajectory_controller`，没有注册`forward_position_controller`；bringup launch的`controllers_to_load`也只有JTC。因此在仓库提供的默认控制栈中，没有已配置的订阅者消费Servo输出topic。Servo node可以启动并发布，但不能据此认为Servo控制链路能驱动Stäubli。
4. `staubli_moveit_config/package.xml`未声明`moveit_servo`为exec_depend，虽然launch文件可选启动该包的`servo_node`。从源码安装/二进制部署时，是否恰好由其他依赖带入不能代替显式运行时依赖声明。
5. MoveIt配置仍使用`MoveItSimpleControllerManager`，只配置`joint_trajectory_controller/follow_joint_trajectory`。Servo的ForwardCommandController并未纳入该控制器管理器；MoveItSimpleControllerManager也不负责ros2_control controller switching。
6. 因此当前状态应标注为“Servo可选启动入口存在，但输出控制器缺失且没有模式仲裁集成”，而不是“Servo已与JTC互斥切换”。

### C. 位置命令接口资源互斥：框架保护存在，但仅限正确配置的控制器

1. Stäubli URDF ros2_control宏为每个关节导出position、velocity命令接口；物理硬件还导出acceleration接口用于限幅支持，但HardwareInterface明确不接受acceleration作为控制模式。Servo当前发布位置命令，若使用ForwardCommandController，其应claim六个`joint_i/position`接口。
2. JTC的`controllers.yaml`同样声明六轴`command_interfaces: [position]`。若另行注册一个六轴ForwardCommandController并令其claim相同接口，两个控制器会争用完全相同的六个位置命令资源。
3. ros2_control ResourceManager规定一个command interface只能被单个实例claim；ControllerManager激活控制器时会检查资源是否已被其他控制器占用。因此正常配置下，JTC与ForwardCommandController不能同时active并持有相同`joint_i/position`接口。这是框架层资源互斥，不是Servo节点或MoveIt自身的互斥逻辑。
4. 资源claim只约束ros2_control控制器实例，不约束任意ROS topic发布者。若多个节点同时向同一个`/forward_position_controller/commands`发布Float64MultiArray，controller仍可能接收多个来源的交错命令；topic没有命令所有者、租约、会话ID或发布者授权机制。
5. 资源互斥也不保证切换过程已物理停止。controller_manager完成deactivate/activate不等于VAL3确认停止、关节速度归零或机器人到达稳定状态。

### D. HardwareInterface切换语义与剩余缺口

1. HardwareInterface导出position与velocity命令接口，但`prepare_command_mode_switch()`仅依据`start_interfaces`解析模式；`stop_interfaces`未参与验证，代码仍保留对outgoing_mode的注释/TODO。
2. `resolve_mode()`遇到第一个匹配的position/velocity/effort/acceleration关键字即返回，因此混合接口集合的结果依赖遍历顺序。当前Servo和JTC若都正确配置为position，模式解析结果相同，不会区分“轨迹控制来源”与“Servo来源”。
3. `perform_command_mode_switch()`忽略传入的start/stop列表，消费prepare阶段缓存的pending_mode；在切换到position模式时，把当前反馈位置复制到位置命令缓存，再将速度/加速度缓存清零，最后设置current_control_mode_。
4. 该初始化有助于避免切换瞬间复用未初始化的旧目标，但代码没有等待`state_msg_.in_motion == false`、关节速度稳定或VAL3运动状态确认；也没有命令来源标识、模式租约、旧模式命令epoch或重新授权。
5. 因此即使controller_manager成功完成接口claim切换，也不能仅凭其成功返回就认定物理机器人已停止或新模式安全就绪。切换的实际动态行为必须在仿真/HIL及风险受控的实机环境验证。
6. 前序§9.3.31已记录STOP模式切换只改变本地控制模式，实际STOP依赖后续write周期；本节进一步指出Servo↔JTC同属position命令模式，HardwareInterface不会从命令模式枚举中识别两种上层控制来源。

### E. Servo暂停、超时和节点退出并非统一停止机制

1. MoveIt Servo的`~/pause_servo`服务在pause时只设置`servo_paused_=true`并关闭Servo collision checking；servo loop随后跳过命令处理、重置smoothing并sleep。该pause回调没有调用controller_manager切换，也没有显式发布STOP或等待机器人静止。
2. unpause时，Servo重新读取当前RobotState、重置smoothing和command rolling window，再重新启用collision checking；没有与JTC active状态、硬件STOP确认或控制权重新授权握手。
3. Servo输入命令超时后，Servo会调用`smoothHalt()`并在仍需减速时继续产生平滑停止目标；当停止过程完成后不再持续产生新命令。该行为属于Servo算法输出，不是CS9安全停止，也不能替代controller/hardware的停止确认。
4. Servo析构函数设置stop_servo并join线程，没有显式向控制器发送STOP或执行控制器切换。若Servo进程退出时ForwardCommandController仍active，控制器侧最后一次接收的命令是否保持/如何被覆盖，需要在目标controller实现和运行时测试；静态源码不能把进程退出等同于机械臂停止。
5. 当前Servo config的`incoming_command_timeout=0.1s`、`num_outgoing_halt_msgs_to_publish=4`不构成安全功能证明。尤其pause service并不等同于触发timeout smoothHalt流程。

### F. 若改用JointTrajectory输出，必须防止Action旁路

1. MoveIt Servo支持`trajectory_msgs/JointTrajectory`输出；当前Stäubli配置选择的是Float64MultiArray，所以现阶段Servo不会直接向JTC topic发布轨迹。
2. 若未来把Servo输出改为JTC的`/joint_trajectory_controller/joint_trajectory` topic，则Servo直接topic输入与MoveIt的FollowJointTrajectory Action会汇入同一个JTC。JTC文档明确存在Action与topic两种命令入口；topic命令可能替换正在执行的Action轨迹，而Action客户端未必因此得到对应的取消/终态通知。
3. 因此不得把“改成JointTrajectory消息”视为自动解决Servo/JTC仲裁。必须有显式命令仲裁器，保证同一时刻只有一个已授权命令源，并把Servo接管/释放与Action取消/终态、控制器状态和物理停止确认关联起来。

### G. 风险分级

- **P1：Servo输出控制器缺失。** YAML输出指向forward_position_controller，但controllers.yaml和launch未定义/加载该控制器；当前可选Servo路径命令链不完整。
- **P1：Servo运行依赖缺失。** package.xml未显式声明moveit_servo exec_depend，部署依赖不完整。
- **P1：没有跨Servo/JTC统一仲裁。** 两者配置由不同节点/机制管理；SimpleControllerManager只管理JTC Action控制器，不会自动为Servo切换ForwardCommandController。
- **P1：暂停/退出语义不足。** Servo pause与析构不执行STOP/静止确认；控制器仍active时的最后命令行为需要动态验收。
- **P1：多发布者命令竞争。** 即便控制器已正确激活，直接Float64MultiArray topic没有来源授权和互斥锁；多个发布者可能交错更新目标。
- **P1：接口切换未做物理停止确认。** HardwareInterface切换只重置缓存并更新本地mode，没有确认运动停止/稳定/重新授权。
- **P0安全边界：** Servo碰撞检查、singularity处理、timeout smoothHalt、ros2_control资源claim均非安全额定保护，不能替代CS9安全链、STO/SS1/SS2、安全PLC、急停和制动器。

### H. 新增验收矩阵

| ID | 场景 | 通过条件 | 当前状态 |
|---|---|---|---|
| SERVO-01 | launch_servo:=true | Servo输出topic存在且有预期controller订阅；控制链完整 | 静态发现目标controller缺失 |
| SERVO-02 | package安装/依赖解析 | moveit_servo作为显式运行时依赖安装 | 静态发现exec_depend缺失 |
| SERVO-03 | JTC与ForwardCommandController同时激活 | 对同一position接口只能有一个claim成功，另一方明确失败 | 框架规则已确认；未运行 |
| SERVO-04 | JTC→Servo切换 | Action旧目标终结、JTC释放接口、机器人停止/稳定后才激活Servo并授权新命令 | 未执行 |
| SERVO-05 | Servo→JTC切换 | Servo命令源撤销、Servo平滑停止/停止确认、接口切换后新Action从当前状态开始 | 未执行 |
| SERVO-06 | pause_servo在运动中触发 | 验证暂停是否主动产生减速/停止；若不是，系统明确禁止将pause当急停 | 静态发现pause无STOP |
| SERVO-07 | Servo节点SIGINT/崩溃 | Servo退出后无旧目标持续驱动；控制器/硬件进入明确安全状态 | 未执行 |
| SERVO-08 | Servo输入超时 | smoothHalt输出与实际机器人停止状态一致，超时/反馈丢失时锁存故障 | 未执行 |
| SERVO-09 | 多发布者向commands topic发布 | 未授权发布者被拒绝或由单一mux仲裁；无交错目标 | 静态发现无来源仲裁 |
| SERVO-10 | JTC Action执行期间Servo topic注入 | 不得旁路Action控制权或造成Action结果与物理命令不一致 | 当前Servo输出非JTC topic；未执行 |
| SERVO-11 | position→position控制器切换 | 检查stop_interfaces/start_interfaces、pending_mode和位置缓存初始化；无跳变 | 静态发现缺少物理确认 |
| SERVO-12 | Servo/JTC切换期间UDP断链/硬件ERROR | 统一故障锁存；不得自动切回或恢复旧目标 | 未执行 |
| SERVO-13 | 重新连接后恢复Servo | 反馈新鲜、旧命令epoch失效、控制器状态确认、重新授权后才能输出 | 未执行 |
| SERVO-14 | 真实机器人低速接管测试 | 受控速度/区域下测量切换延迟、速度峰值、停止距离、位置跳变并由安全负责人验收 | 未执行 |

### I. 整改建议

1. 明确产品控制模式：`TRAJECTORY`、`SERVO`、`STOP/FAULT`，由唯一MotionModeArbiter持有运动控制权；禁止应用直接自行激活controller或绕过仲裁器向底层命令topic写入。
2. 为Servo增加真正的ForwardCommandController配置（六轴、position接口、正确controller plugin和topic remap），并加入bringup的load-only/inactive流程；Servo默认不启动，只有在JTC完成取消/停稳/释放接口后才允许激活。
3. 补充`moveit_servo`运行时依赖，增加launch验证：launch_servo=true时检查Servo node、输出topic、订阅controller、hardware interfaces和controller lifecycle全部匹配。
4. 设计原子切换流程：停止接收新输入→撤销当前命令源→按策略平滑减速→等待状态反馈新鲜且速度/运动标志满足稳定条件→取消/终结旧Action→deactivate旧controller并确认接口释放→activate新controller并确认claim→从当前反馈位置初始化→要求新session/新授权→开放新命令源。任何步骤失败均进入锁存STOP/FAULT，不自动恢复运动。
5. 将Servo pause定义为“暂停输入/伺服更新”的软件功能，不宣传为停止或急停；增加独立stop service/统一停止协调器，并明确其仍不是安全额定急停。
6. 对直接命令topic引入唯一命令mux/授权门控，包含source ID、session epoch、sequence、有效期和模式租约；拒绝过期/旧session/非owner命令。ROS topic本身不提供发布者身份认证，需在应用层设计访问控制或隔离命名空间/进程。
7. 若选择Servo JointTrajectory输出，必须验证JTC topic与Action并发覆盖行为；优先保留Action作为MoveIt规划执行通道，并通过统一仲裁器切换，不允许未授权topic覆盖正在执行的Action。
8. HardwareInterface模式切换应校验start/stop接口集合一致性、混合模式、当前状态和目标模式；但最终停止距离、停止时间及安全功能仍由独立安全系统验证。

### J. 本节来源记录（#1693–#1704）

| 编号 | 固定来源 | 用途 |
|---|---|---|
| #1693 | [ICube staubli_moveit.launch.py @ bd658e2](`https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_moveit_config/launch/staubli_moveit.launch.py`) | Servo可选启动、与move_group并列 |
| #1694 | [ICube staubli_servo.yaml @ bd658e2](`https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_moveit_config/config/staubli_servo.yaml`) | Float64MultiArray位置输出、forward_position_controller topic、timeout/smoothing参数 |
| #1695 | [ICube controllers.yaml @ bd658e2](`https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_bringup/config/controllers.yaml`) | 只注册JTC与joint_state_broadcaster |
| #1696 | [ICube moveit_controllers.yaml @ bd658e2](`https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_moveit_config/config/moveit_controllers.yaml`) | SimpleControllerManager只映射JTC Action |
| #1697 | [ICube staubli_r2c_joints.xacro @ bd658e2](`https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_description/r2c/include/staubli_r2c_joints.xacro`) | position/velocity/acceleration接口导出 |
| #1698 | [ICube HardwareInterface @ bd658e2](`https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/src/staubli_hardware_interface.cpp`) | prepare/perform mode switch、缓存初始化、忽略stop_interfaces |
| #1699 | [ICube staubli_moveit_config/package.xml @ bd658e2](`https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_moveit_config/package.xml`) | moveit_servo运行时依赖未显式声明 |
| #1700 | [MoveIt Servo servo_node.cpp @ 6ed6372](`https://github.com/moveit/moveit2/blob/6ed6372a72ba9b121ed12ef574ea4ff4d3d92f09/moveit_ros/moveit_servo/src/servo_node.cpp`) | command topic publisher、pause服务、timeout smoothHalt、loop与析构行为 |
| #1701 | [MoveIt Servo servo.cpp @ 6ed6372](`https://github.com/moveit/moveit2/blob/6ed6372a72ba9b121ed12ef574ea4ff4d3d92f09/moveit_ros/moveit_servo/src/servo.cpp`) | Servo算法/碰撞监控与平滑处理 |
| #1702 | [ros2_control Jazzy ResourceManager API](`https://control.ros.org/jazzy/doc/api/classhardware__interface_1_1ResourceManager.html`) | command interface单实例claim规则 |
| #1703 | [ros2_control Jazzy ControllerInterface API](`https://control.ros.org/jazzy/doc/api/classcontroller__interface_1_1ControllerInterfaceBase.html`) | ControllerManager按接口配置claim硬件命令接口 |
| #1704 | [MoveIt Ros2ControlManager README](`https://github.com/moveit/moveit2/blob/main/moveit_plugins/moveit_ros_control_interface/README.md`) | MoveIt ROS2ControlManager基于资源冲突执行controller switching；与当前SimpleControllerManager配置对比 |



## 9.3.39 Servo超时停止与ForwardCommandController命令保持语义（2026-11-07）

### A. 审查范围与版本边界

- MoveIt 2 Jazzy固定commit：`6ed6372a72ba9b121ed12ef574ea4ff4d3d92f09`。
- ros2_controllers固定源码快照：`c8d26930ff87bc819db1452af1d45da5bfa3d50d`；接口语义同时对照ROS 2 Control Jazzy官方API文档。
- 审查Servo输入消息时间戳、超时处理、平滑停止输出、pause分支，以及ForwardCommandController订阅回调、实时命令缓存、update循环和生命周期回调。
- 本节是固定源码静态审查；未启动Jazzy工作区、未运行控制器/Servo、未验证目标RMW和硬件驱动的实际命令保持行为。

### B. Servo超时处理的真实触发条件

1. Servo对JointJog、TwistStamped和PoseStamped分别读取消息Header stamp，并用`node_->now() - header.stamp >= incoming_command_timeout`判断命令是否过期；这不是由下游控制器检测发布者断流，也不是基于接收端单调时钟的独立watchdog。
2. 对已收到且当前命令类型匹配的消息，过期后调用`smoothHalt(last_commanded_state_)`。只要平滑停止尚未完成，Servo继续生成新的关节状态；停止完成后，该消息标志被清除，不再继续发布该命令的停止状态。
3. 当前Stäubli Servo配置采用Float64MultiArray位置输出，故平滑停止期间发布的是连续位置目标；超时处理结束后，Servo不再持续刷新最后一条位置目标。
4. Servo循环没有输入消息时，不会仅凭“从未收到过消息”进入某个已验证的停止状态；但此时Servo尚无已发出的新目标。必须区分“无命令启动”“收到命令后超时”和“运行中pause”三个状态。
5. 超时年龄取决于ROS节点时钟与消息Header stamp。仿真时间暂停/回跳、系统时间与ROS time切换、未来时间戳和上游发送端时钟偏差都应纳入测试，不能将0.1s参数直接解释为端到端物理停止时间。

### C. ForwardCommandController会持续应用最后一条有效命令

1. `ForwardControllersBase::on_configure()`创建`~/commands`的Float64MultiArray订阅；回调只在controller lifecycle为ACTIVE时接受命令，并拒绝含NaN/Inf的数组。
2. 收到有效消息后，回调将整条消息写入RealtimeThreadSafeBox；代码没有记录消息接收时间、命令年龄、来源身份、session epoch或sequence，也没有命令超时参数。
3. `update()`每个控制周期尝试从实时盒读取新命令；若没有新消息，保留成员变量`joint_commands_`中的旧值。只要该数组不是全NaN，控制器就继续把缓存值写入各command interface。
4. 因此，当controller保持ACTIVE且已接受过一条有限值命令时，发布者停止发送并不会自动令ForwardCommandController超时或清除目标；控制器会继续写入最后缓存的设定值，直到新命令覆盖、controller生命周期变化或发生其他控制器错误。
5. `on_activate()`与`on_deactivate()`会把内部命令缓存重置为NaN；全NaN时update不再写接口。该行为是控制器缓存/生命周期语义，不应未经目标硬件测试推断为机械臂已经停止或已进入安全状态。
6. 当Servo的smoothHalt完成并停止发布后，ForwardCommandController若仍active，会保留并重复写入最后一条停止位置目标。这个结果可能形成位置保持设定值，但并不提供独立的命令新鲜度监控、停止确认或安全锁存。
7. Servo的`pause_servo`分支直接跳过命令处理和发布；它不会触发smoothHalt。若ForwardCommandController仍active，底层控制器仍会持续应用缓存命令。故pause与输入timeout不是等价路径。

### D. 新发现的工程缺口与风险分级

- **P1：下游命令缓存无watchdog。** ForwardCommandController没有时间戳/年龄检查；上游发布者失联时，缓存的有限位置目标仍会在每周期写入硬件接口。
- **P1：Servo超时不是系统级停止闭环。** Servo仅在已接收命令的Header时间戳过期后计算smoothHalt；停止序列结束不代表底层controller停止写目标，也不代表机器人静止。
- **P1：pause不会进入smoothHalt。** pause时Servo循环不输出命令，若下游controller仍active则保持最后缓存值；不得把pause服务用作STOP/急停接口。
- **P1：消息时间基准依赖。** Header stamp与Servo node clock必须兼容；时钟跳变、时间源错误、future stamp及发送端时钟偏差可能改变超时触发时机。
- **P1：命令来源竞争。** ForwardCommandController的订阅回调不认证publisher身份；多个发布者向同一topic发布时，实时盒中的最后写入值获后续update使用，不能提供确定的owner仲裁。
- **安全边界：** 位置目标保持、Servo smoothHalt、controller deactivate和普通UDP STOP均不是CS9安全额定停止。停止距离、停止时间、制动器行为和安全功能必须由目标机器人/控制器独立安全链验证。

### E. 新增验收矩阵

| ID | 场景 | 通过条件 | 当前状态 |
|---|---|---|---|
| SERVO-15 | ForwardCommandController收到有限位置命令后publisher停止 | 需求明确规定命令租约/watchdog；过期后进入定义的受控故障状态，不无限期静默复用旧命令 | 静态确认无时间戳/超时检查 |
| SERVO-16 | Servo输入Header stamp为旧时间/未来时间 | 对旧戳、未来戳、发送端时钟偏差、ROS time暂停/回跳有确定策略和诊断 | 未执行 |
| SERVO-17 | Servo输入超时并完成smoothHalt | 记录最后发布目标；验证下游controller继续缓存该目标的行为及硬件响应 | 静态确认下游缓存持续写入；未集成验证 |
| SERVO-18 | 机器人运动中调用pause_servo | 明确pause不等于smoothHalt/STOP；确认缓存目标、硬件响应和恢复前重新授权 | 静态确认pause分支不发布；未执行 |
| SERVO-19 | ForwardCommandController deactivate→activate | 生命周期切换清空缓存；旧命令不被重新应用；只有新鲜且已授权命令才能恢复 | 静态确认缓存重置为NaN；未执行 |
| SERVO-20 | 两个publisher并发发送commands | 未授权源被拒绝；命令owner/epoch/sequence唯一，不能由最后到达消息隐式抢占 | 静态发现无来源认证/仲裁 |
| SERVO-21 | Float64MultiArray长度与关节接口数量不匹配 | 明确错误传播、controller lifecycle及硬件安全响应，不保留含糊的旧命令状态 | 静态发现update返回ERROR；未执行 |
| SERVO-22 | 命令包含NaN/Inf | 非有限值拒绝并产生可观测诊断，不改变现有有效目标；覆盖数组长度边界 | 静态确认回调拒绝；未执行 |
| SERVO-23 | controller inactive期间收到命令后再activate | inactive命令不进入活动缓存；activate后要求新命令，不接受旧消息残留 | 静态确认activate重置NaN；未执行 |
| SERVO-24 | UDP断链/硬件ERROR发生在最后目标保持期间 | 控制器错误、硬件模式、VAL3命令缓存、恢复授权一致；不得自动恢复旧目标 | 未执行 |

### F. 整改建议

1. 不应把通用ForwardCommandController直接当作具备命令超时保护的运动控制器。若用于Servo，应增加明确的上层命令mux/lease，或实现带时间戳、单调时钟年龄检查、来源授权、sequence/session epoch和超时故障策略的受控controller。
2. 命令watchdog触发后的策略必须由系统安全需求定义：是否请求平滑减速、锁存STOP、切换controller或请求独立安全系统；不得简单将缓存清零/写零速度等同于安全停止。
3. Servo输入超时与下游controller命令超时应分别配置和监控；两者的时间预算、时钟域、最大通信延迟、平滑停止时长和硬件响应需形成端到端预算。
4. pause应明确为“停止Servo更新/输入处理”的软件暂停；若产品需要运动中停止，应走独立停止协调器并等待可验证的控制器状态/静止反馈。安全急停仍走CS9安全回路。
5. 对多个发布者采用唯一owner仲裁；仅依赖ROS topic名称、DDS endpoint或“最后一条消息”不构成命令授权。考虑ROS 2 SROS2权限/隔离，但必须验证具体部署与身份配置。
6. 集成验收应同步记录Servo发布序列、controller订阅序列、command interface值、HardwareInterface write值、VAL3收到的命令序号、关节反馈及独立安全状态；使用统一时间基准或明确时钟映射。
7. 先在仿真/fake hardware验证生命周期和缓存语义，再在风险评估、限速限区和独立急停保障下执行HIL/FAT；不在未验证的真实机器人上以断流测试替代安全测试。

### G. 本节来源记录（#1705–#1710）

| 编号 | 固定来源 | 用途 |
|---|---|---|
| #1705 | [ros2_controllers ForwardControllersBase @ c8d2693](`https://github.com/ros-controls/ros2_controllers/blob/c8d26930ff87bc819db1452af1d45da5bfa3d50d/forward_command_controller/src/forward_controllers_base.cpp`) | commands订阅、ACTIVE检查、非有限值拒绝、RealtimeThreadSafeBox缓存、update持续写接口、activate/deactivate NaN重置 |
| #1706 | [ros2_controllers ForwardCommandController @ c8d2693](`https://github.com/ros-controls/ros2_controllers/blob/c8d26930ff87bc819db1452af1d45da5bfa3d50d/forward_command_controller/src/forward_command_controller.cpp`) | joints/interface_name参数生成命令接口列表 |
| #1707 | [ROS 2 Control Jazzy Forward Command Controller文档](`https://control.ros.org/jazzy/doc/ros2_controllers/forward_command_controller/doc/userdoc.html`) | 公开接口为~/commands Float64MultiArray及关节/接口参数 |
| #1708 | [ROS 2 Control Jazzy ForwardControllersBase API](`https://control.ros.org/jazzy/doc/api/classforward__command__controller_1_1ForwardControllersBase.html`) | 生命周期回调、command interface claim与update API契约 |
| #1709 | [MoveIt Servo servo_node.cpp @ 6ed6372](`https://github.com/moveit/moveit2/blob/6ed6372a72ba9b121ed12ef574ea4ff4d3d92f09/moveit_ros/moveit_servo/src/servo_node.cpp`) | Header stamp timeout、smoothHalt发布时序、pause时跳过输出及最后命令状态 |
| #1710 | [MoveIt Servo参数文档与实现 @ 6ed6372](`https://github.com/moveit/moveit2/blob/6ed6372a72ba9b121ed12ef574ea4ff4d3d92f09/moveit_ros/moveit_servo/src/servo_parameters.cpp`) | incoming_command_timeout参数说明及停止行为参数定义 |



## 9.3.40 Servo Float64MultiArray关节顺序与ForwardCommandController接口映射（2026-11-07）

### A. 审查范围与版本边界

- ICube Stäubli驱动固定commit：`bd658e2d266e315d2ee35f985fb352ea88306b79`。
- MoveIt 2 Jazzy固定commit：`6ed6372a72ba9b121ed12ef574ea4ff4d3d92f09`。
- ros2_controllers固定源码快照：`c8d26930ff87bc819db1452af1d45da5bfa3d50d`。
- 对照MoveIt SRDF group、机器人默认joint_names、ros2_control URDF接口生成顺序、Servo Float64MultiArray组包和ForwardCommandController命令接口顺序。
- 本节是源码/配置静态映射审查；未执行xacro展开、MoveIt RobotModel运行时枚举、ForwardCommandController集成或六轴实机命令测试。

### B. Servo消息采用隐式位置索引，不携带关节名

1. MoveIt Servo的`getNextJointState()`从`JointModelGroup::getActiveJointModelNames()`取得关节名序列，并将其写入目标KinematicState。
2. Stäubli当前Servo配置选择`std_msgs/Float64MultiArray`与`publish_joint_positions: true`。MoveIt的`composeMultiArrayMessage()`只按KinematicState的joint_names数量分配data数组，并按同一索引复制positions；Float64MultiArray本身不携带joint_names或接口名。
3. 因此，Servo数组第i个数值的含义完全依赖MoveIt活动关节组的joint order；接收端不能从消息本身识别关节名，也不能自动纠正排列差异。

### C. Stäubli默认TX2-60L静态配置的预期顺序

1. Stäubli机器人描述的`default_names.yaml`将joint_names依次定义为joint_1、joint_2、joint_3、joint_4、joint_5、joint_6。
2. SRDF宏将`arm`组定义为从base_link到tool0的chain；机器人描述URDF宏递归消费joint_names列表，并按列表顺序生成每个关节的ros2_control命令接口。
3. 当前JTC配置也按joint_1至joint_6顺序声明六个joints。以上静态资料在预期默认配置下呈现一致的六轴命名顺序。
4. 但当前controllers.yaml没有ForwardCommandController配置，故不存在已部署的Servo接收端joint list可供逐项对照；本节不能宣称Servo→ForwardCommandController轴映射已经集成或通过。
5. SRDF chain经xacro展开后MoveIt实际active joint顺序、前缀/型号变体及运行时加载的robot_description仍需在目标工作区解析验证，不能仅凭默认YAML认定所有型号/前缀都相同。

### D. ForwardCommandController按参数索引写入接口，等长但错序可能静默映射错误

1. `ForwardCommandController::read_parameters()`按`params_.joints`遍历并依次生成`joint/interface_name`命令接口名列表。
2. `ForwardControllersBase::update()`以数组下标i将`joint_commands_.data[i]`写入`command_interfaces_[i]`。它检查data长度与接口数量是否相等，但Float64MultiArray没有关节名，因此无法发现两个六元素数组的排列不同。
3. 若未来ForwardCommandController的joints参数顺序与Servo活动关节顺序不一致，即使长度都是6且所有值有限，也可能把一个关节的目标写入另一个关节的接口；这种错序不一定触发现有长度错误检查。
4. 当前未发现Stäubli默认YAML本身已发生错序；真正缺口是ForwardCommandController尚未配置，且缺少显式的启动期顺序一致性校验与端到端测试。将其定为P1集成准入要求，而非已复现的当前运行故障。

### E. 风险分级

- **P1：Float64MultiArray缺少关节名。** 数组语义由隐式索引决定；长度校验不能检测同长度错序。
- **P1：未来ForwardCommandController配置尚不存在。** 不能证明Servo active joint order与controller joints参数顺序一致。
- **P2：型号/前缀/模型展开差异。** 默认TX2-60L YAML与SRDF宏的静态一致性不能替代每个robot_model、robot_prefix和生成后robot_description的实际检查。

### F. 新增验收矩阵

| ID | 场景 | 通过条件 | 当前状态 |
|---|---|---|---|
| SERVO-25 | 解析目标型号SRDF/URDF | 运行时active joint names与预期六轴顺序逐项一致 | 静态默认配置可追溯；未展开验证 |
| SERVO-26 | Servo Float64MultiArray组包 | 记录joint_names→data索引映射；无名字丢失或隐式重排 | 静态确认按KinematicState索引组包 |
| SERVO-27 | ForwardCommandController joints参数配置 | joints顺序与Servo active joint names逐项相同，且与HardwareInterface接口名一致 | 控制器未配置，待实施 |
| SERVO-28 | 同长度六轴数组故意打乱顺序 | 启动期检查拒绝错序配置，不允许静默写入错误关节接口 | 当前无该检查；未执行 |
| SERVO-29 | 不同robot_model/robot_prefix组合 | 对每个受支持型号生成robot_description并验证关节名、顺序、接口数量 | 未执行 |

### G. 整改建议

1. 若继续使用Float64MultiArray，必须在启动时读取MoveIt RobotModel的active joint names和ForwardCommandController joints参数，逐项比较并拒绝任何顺序不一致；不能只比较数量。
2. 优先考虑带joint_names字段的消息接口或受控适配层；如果保留Float64MultiArray，需在接口契约中明确数组顺序、单位、维度和型号配置，并由CI从展开后的URDF/SRDF生成检查结果。
3. ForwardCommandController配置应显式声明六轴joints及position interface，并验证命令数组长度、接口列表、URDF导出列表和HardwareInterface joint order四者一致。
4. 为错序测试构造非对称六轴目标向量，逐关节比对Servo发布、controller订阅、command interface值、HardwareInterface write及VAL3接收数据；全零/对称向量不能发现轴交换。
5. 当前默认YAML命名顺序一致只能作为静态配置证据；在ForwardCommandController真正注册、启动并通过fake hardware/HIL验证之前，Servo链路继续标记未闭合。

### H. 本节来源记录（#1711–#1714）

| 编号 | 固定来源 | 用途 |
|---|---|---|
| #1711 | [Stäubli default_names.yaml @ bd658e2](`https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_description/urdf/include/default_names.yaml`) | 默认joint_names顺序joint_1至joint_6 |
| #1712 | [Stäubli SRDF macro @ bd658e2](`https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_moveit_config/srdf/staubli_macro.srdf.xacro`) | arm组按base_link到tool0定义chain |
| #1713 | [MoveIt Servo common.cpp @ 6ed6372](`https://github.com/moveit/moveit2/blob/6ed6372a72ba9b121ed12ef574ea4ff4d3d92f09/moveit_ros/moveit_servo/src/utils/common.cpp`) | Float64MultiArray按KinematicState.positions索引写入data，不附带joint_names |
| #1714 | [Stäubli ros2_control joint Xacro @ bd658e2](`https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_description/r2c/include/staubli_r2c_joints.xacro`) | 按joint_names列表顺序递归生成关节接口 |


## 9.3.41 MoveIt Servo与ForwardCommandController命令接口、命名空间及QoS契约（2026-11-07）

### A. 审查范围与固定版本

- Stäubli ICube驱动与配置固定commit：`bd658e2d266e315d2ee35f985fb352ea88306b79`。
- MoveIt 2 Jazzy固定commit：`6ed6372a72ba9b121ed12ef574ea4ff4d3d92f09`。
- ros2_controllers固定源码快照：`c8d26930ff87bc819db1452af1d45da5bfa3d50d`。
- 对照Stäubli Servo YAML、MoveIt controller映射、bringup controllers.yaml、Servo publisher创建、ForwardControllersBase subscription创建及ROS 2 SystemDefaultsQoS语义。
- 本节仅为固定源码和配置静态审查；未启动ROS graph、未运行ros2 topic info/endpoint QoS检查、未执行controller spawner或消息注入。

### B. 当前Stäubli配置的topic字符串表面一致，但接收端未部署

1. `staubli_servo.yaml`配置`command_out_type: std_msgs/Float64MultiArray`、位置输出启用、速度/加速度输出关闭，topic为绝对名称`/forward_position_controller/commands`。
2. `ForwardControllersBase::on_configure()`在控制器节点上创建`~/commands`订阅，消息类型同为`std_msgs::msg::Float64MultiArray`。对名为`forward_position_controller`且位于根命名空间的controller node，私有topic解析后预期为`/forward_position_controller/commands`，与Servo配置字符串一致。
3. 但Stäubli `controllers.yaml`只注册joint_state_broadcaster和joint_trajectory_controller，没有forward_position_controller；MoveIt controller manager也只映射JTC的FollowJointTrajectory Action。因此上述topic一致只是“未来拟配置时可对齐”的静态接口契约，不是当前运行时已存在的publisher-subscriber连接。
4. Servo节点名/命名空间与controller manager namespace必须作为同一部署配置审查。Servo输出写成绝对根路径；若未来将controller manager放入`/robot_X`等命名空间，`~/commands`会随controller节点命名空间解析，而Servo绝对topic不会自动跟随。此时即使controller名称相同，也会形成不同topic。应统一采用同一namespace参数化后的完整topic，或显式remap两端；不能依赖默认根命名空间假设。
5. ROS 2名称解析验收必须记录最终resolved topic name，而不是仅比较YAML中的原始字符串。还需确认controller node实际名称、namespace、ROS_DOMAIN_ID及remapping。

### C. 消息类型与数据语义

1. Servo publisher根据`command_out_type`创建`Float64MultiArray` publisher；ForwardControllersBase订阅同一消息类型。类型层面兼容。
2. 消息本身没有关节名、控制源身份、时间戳、session epoch或sequence。§9.3.40已确认数组索引依赖关节顺序；§9.3.39已确认下游没有命令年龄watchdog。本节将两者纳入接口准入条件，而不是将“类型相同”误判为端到端契约完整。
3. `publish_joint_positions: true`意味着当前Stäubli Servo配置发布位置值；未来ForwardCommandController必须配置`interface_name: position`，并确认机器人HardwareInterface确实导出同名position command interfaces。不能将Servo位置数组接到velocity/effort controller，也不能只以数组长度验证单位/语义。
4. Servo的`publish_period: 0.004`为250Hz目标发布周期；bringup controller_manager的`update_rate: 250`同为250Hz。频率数值相等不代表调度相位、网络延迟、DDS队列和controller update周期同步，也不构成实时期限保证。应测量实际发布间隔、接收间隔、update周期、丢帧和最坏延迟。

### D. QoS：两端均使用SystemDefaultsQoS，但实际策略由RMW决定

1. 固定MoveIt Servo源码以`rclcpp::SystemDefaultsQoS()`创建Float64MultiArray publisher；固定ros2_controllers源码也以`rclcpp::SystemDefaultsQoS()`创建`~/commands` subscriber。
2. 两端使用相同的SystemDefaultsQoS API，降低了应用代码显式设置不同QoS配置的风险；但SystemDefaultsQoS将策略交给底层RMW实现，不应直接写成“已证明Reliable、Volatile、KeepLast(10)”或“所有RMW必然兼容”。
3. ROS 2 QoS兼容性按request-versus-offered规则判断；不兼容的publisher/subscriber不会建立数据连接。不同RMW实现可能采用不同system defaults，必须在目标发行版、RMW、DDS XML/环境配置下读取实际endpoint QoS并检查匹配状态。
4. 因此当前审计结论是：源码层面两端均调用SystemDefaultsQoS；实际QoS策略与连接兼容性未在目标运行环境验证。不得把未观察到的QoS告警当作兼容证据。

### E. Lifecycle、启动时序与消息丢失窗口

1. ForwardCommandController在on_configure阶段创建订阅，但回调仅在controller lifecycle为ACTIVE时接收命令；非ACTIVE时消息被拒绝。controller在inactive状态下即使已创建订阅，也不代表命令会被缓存供激活后使用。
2. Servo节点构造时创建publisher并启动servo loop。若Servo先开始发布而ForwardController尚未ACTIVE，早期命令可能没有匹配订阅者，或被inactive回调丢弃；当前SystemDefaultsQoS没有应用层“激活后首条有效命令确认”协议。
3. ForwardControllersBase在activate时将命令缓存重置为NaN；这避免直接沿用此前缓存的有限值，但不能证明硬件物理停止，也不等于激活前命令会被保留。
4. 启动顺序应为：硬件状态与反馈新鲜度有效→controller配置成功→目标position接口claim成功并ACTIVE→核对topic/type/QoS匹配→显式命令owner授权→Servo进入可发布状态。任何一步失败都应保持禁止运动，而不是以节点进程存活或topic存在替代ready。
5. 停止/切换顺序应先撤销命令owner并执行经验证的停止策略，再停Servo/切换controller；单纯deactivate会释放接口并清空缓存，但不构成机械臂静止确认。

### F. 风险分级与整改要求

- **P1：当前链路未闭合。** ForwardCommandController未注册；不能声称Servo发布数据已到达controller或HardwareInterface。
- **P1：绝对topic与私有topic的namespace耦合。** 默认根namespace下名称预期一致；多机器人/命名空间部署可能分叉。应在launch层统一参数化并对resolved name做启动断言。
- **P1：SystemDefaultsQoS没有目标RMW实测证据。** 两端同用SystemDefaultsQoS不是QoS匹配报告；必须采集实际QoS和matched endpoint状态。
- **P1：生命周期窗口和授权未闭环。** 配置态/非ACTIVE期间消息不会被controller接受；激活时缓存清NaN。必须设计controller ACTIVE、接口claim、Servo发布使能和owner授权的互锁状态机。
- **P2：250Hz配置相等不代表端到端实时保证。** 必须通过运行测量确定频率、延迟、抖动、丢帧及控制周期预算。

### G. 新增验收矩阵

| ID | 场景 | 通过条件 | 当前状态 |
|---|---|---|---|
| SERVO-30 | topic名称解析 | 记录Servo publisher与controller subscriber的resolved name，完全一致 | 默认根命名空间静态字符串预期一致；未运行 |
| SERVO-31 | namespace/remapping | 根namespace及至少一个机器人namespace场景均解析到同一目标topic；错误配置启动失败 | 未执行 |
| SERVO-32 | 消息类型/接口语义 | 两端类型为Float64MultiArray；Servo位置输出与controller position interface匹配 | 静态配置相符；ForwardController未注册 |
| SERVO-33 | QoS endpoint核验 | 目标RMW下记录双方实际QoS、matched publisher/subscription数量和兼容结果 | 两端源码均SystemDefaultsQoS；未实测 |
| SERVO-34 | controller inactive消息 | inactive期间输入不导致接口写入；激活后必须收到新的、经授权的命令才允许更新 | 源码静态可追溯；未执行 |
| SERVO-35 | 启动/关闭时序 | controller ACTIVE、接口claim、反馈新鲜度、命令owner与Servo enable互锁；异常启动保持禁止运动 | 当前未实现/未验证 |
| SERVO-36 | 250Hz链路测量 | 统计发布/接收/update频率、最大延迟、抖动、丢帧和超限动作 | 仅配置目标均为250Hz；未测量 |

### H. 整改建议

1. 为机器人实例定义单一namespace参数，并由launch同时生成Servo `command_out_topic`和controller订阅最终名称；启动时通过ROS graph introspection断言topic名称、类型及publisher/subscriber数量。
2. 生产配置建议显式定义双方QoS，而不是长期依赖RMW system defaults；选择前须结合命令新鲜度、可靠性、队列深度、延迟预算和目标RMW做实验。即使Reliable也不能替代命令租约/watchdog。
3. controller manager启动后先配置并激活ForwardCommandController，确认position interfaces claim成功、hardware状态与joint_states新鲜；再由独立仲裁器授予Servo命令owner。未获得授权不得启动Servo输出。
4. 将接口契约固化为自动化测试：resolved topic、类型、QoS、关节顺序、单位、position接口、active状态、owner/epoch和端到端命令追踪全部一致。
5. 若采用250Hz，必须记录实测分布和最坏情况；不能以两个配置字段都写250Hz作为实时验收。

### I. 本节来源记录（#1715–#1720）

| 编号 | 固定来源 | 用途 |
|---|---|---|
| #1715 | [Stäubli staubli_servo.yaml @ bd658e2] (`https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_moveit_config/config/staubli_servo.yaml`) | Float64MultiArray位置输出、250Hz publish_period、绝对commands topic |
| #1716 | [Stäubli moveit_controllers.yaml @ bd658e2] (`https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_moveit_config/config/moveit_controllers.yaml`) | MoveIt仅映射JTC FollowJointTrajectory Action |
| #1717 | [Stäubli controllers.yaml @ bd658e2] (`https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_bringup/config/controllers.yaml`) | controller_manager 250Hz；未注册ForwardCommandController |
| #1718 | [MoveIt Servo servo_node.cpp @ 6ed6372] (`https://github.com/moveit/moveit2/blob/6ed6372a72ba9b121ed12ef574ea4ff4d3d92f09/moveit_ros/moveit_servo/src/servo_node.cpp`) | publisher使用SystemDefaultsQoS |
| #1719 | [ros2_controllers ForwardControllersBase @ c8d2693] (`https://github.com/ros-controls/ros2_controllers/blob/c8d26930ff87bc819db1452af1d45da5bfa3d50d/forward_command_controller/src/forward_controllers_base.cpp`) | ~/commands订阅使用SystemDefaultsQoS，ACTIVE检查和缓存生命周期 |
| #1720 | [ROS 2 QoS compatibility documentation] (`https://docs.ros.org/en/jazzy/Concepts/Intermediate/About-Quality-of-Service-Settings.html`) | system default由RMW解析；QoS request/offered兼容性与不兼容时不通信 |


## 9.3.42 Servo命令DDS QoS、队列积压、消息丢失与命令新鲜度（2026-11-07）

### A. 审查范围与固定版本

- Stäubli ICube驱动与配置固定commit：`bd658e2d266e315d2ee35f985fb352ea88306b79`。
- MoveIt 2 Jazzy固定commit：`6ed6372a72ba9b121ed12ef574ea4ff4d3d92f09`。
- ros2_controllers固定源码快照：`c8d26930ff87bc819db1452af1d45da5bfa3d50d`（`forward_command_controller`包版本6.10.1）。
- ROS 2 Jazzy RMW/RCLCPP与ros2_control/realtime_tools文档用于核对SystemDefaultsQoS展开、QoS兼容性/事件和实时线程缓存语义。
- 本节为固定源码/官方API文档静态审查；未在目标RMW、DDS vendor、网络条件和机器人工作区中运行ROS graph/QoS测试。

### B. SystemDefaultsQoS并未锁定队列深度或可靠性

1. MoveIt Servo的Float64MultiArray publisher与ForwardControllersBase的`~/commands` subscription均使用`rclcpp::SystemDefaultsQoS()`；两处没有显式传入KEEP_LAST depth、Reliable/BestEffort、Deadline、Lifespan或Liveliness配置，也没有传入QoS事件回调选项。
2. ROS 2 Jazzy的`rmw_qos_profile_system_default`将history、depth、reliability、durability和liveliness设为SYSTEM_DEFAULT；deadline、lifespan及liveliness lease duration为DEFAULT。实际history/depth和其他策略由底层RMW确定，不能仅从该C++调用推导出具体值。
3. 必须区分`rmw_qos_profile_default`和`rmw_qos_profile_system_default`：前者源码静态定义为KEEP_LAST(10)、RELIABLE、VOLATILE；后者各相关策略保留SYSTEM_DEFAULT/DEFAULT。Servo/ForwardController调用的是后者，不能套用前者的depth=10或Reliable结论。
4. 即使两端都写SystemDefaultsQoS，静态配置仍不能代替目标部署下对publisher/subscription endpoint实际QoS的采集。RMW、DDS XML、环境变量、容器镜像和发行版补丁均应作为部署基线的一部分记录。

### C. History/depth、250Hz与积压语义

1. Stäubli Servo YAML的`publish_period: 0.004`对应250Hz目标发布频率；bringup的controller_manager `update_rate: 250`也配置为250Hz。它们只是两个独立周期设定，并不保证严格相位同步、实际无抖动或每条消息都被对应的一次controller update消费。
2. ROS 2 KEEP_LAST(depth=N)只限制该endpoint历史样本缓存的数量；若目标RMW最终采用KEEP_LAST(10)，以250Hz名义间隔估算，10个样本对应约40ms的输入时间跨度，但这不是端到端最大延迟保证，也不能直接推定具体DDS writer/reader/executor总缓存。
3. Reliable用于提高样本传输可靠性，可能通过重传弥补丢包；它不等于时效性保证。网络恢复、接收端调度延迟或队列积压时，应用仍需拒绝超过控制时效预算的命令。BestEffort允许丢样本，可能更适合只消费最新设定值的连续流，但必须证明丢样后watchdog会在预算内触发。
4. KeepLast(1)可限制保留的历史样本数量并偏向最新样本，但不能替代接收后的命令年龄检查：在数据已进入订阅回调/应用缓存之后，DDS history策略不再自动撤销该命令。

### D. ForwardCommandController中间缓存是单槽位，不是命令FIFO

1. ForwardCommandController subscriber回调对每个有限值Float64MultiArray调用`rt_command_.set(cmd)`。头文件声明`rt_command_`为`RealtimeThreadSafeBox<CmdType>`，另有`joint_commands_`保存最后一次成功读取的引用值。
2. `RealtimeThreadSafeBox`是单对象Box，set覆盖当前值；update每周期调用try_get读取当前值，而非按序消费每一条topic消息。因此多个订阅回调在两次controller update之间到达时，中间值可能被后续值覆盖。这是“最新值”型接口特征，不是无损采集队列。
3. realtime_tools Jazzy文档将RealtimeThreadSafeBox描述为best-effort访问；若需要保留实时线程处理前到达的多个中间样本，建议使用LockFreeQueue并按topic速率和controller update速率配置容量。
4. 另一个边界是try_get锁获取失败：ForwardControllersBase只有在try_get返回value时才更新`joint_commands_`；如果本周期未能取得Box值，代码继续使用旧`joint_commands_`并照常写入command interfaces。因此即使callback已收到新命令，实时读取竞争也可能使本周期继续写旧值。该情形需通过压力/锁竞争测试量化，不能当作常态必现故障。
5. 即使Box成功读取最新值，若其值来自DDS队列中的迟到样本，Box无法识别消息产生时间；Float64MultiArray自身没有Header、发送时间、序号或session epoch，现有控制器也不做年龄检查。

### E. Deadline、Lifespan与Liveliness能力边界

1. 当前两端SystemDefaultsQoS均未显式配置Deadline。Deadline描述预期发布周期；发布端/订阅端的missed-deadline事件需要应用注册并处理相应回调。静态源码未见Servo publisher或ForwardController subscription注册QoS事件回调，不能把DDS deadline视为已启用的停止逻辑。
2. 当前两端未显式配置有限Lifespan。Lifespan表示样本从发布到接收允许的最大时长；过期样本由middleware丢弃，且不会送达订阅回调。它可约束传输/排队阶段的样本年龄，但一旦命令已经通过回调写入Box或controller缓存，Lifespan不会回溯清理应用缓存。
3. 当前未显式设置Liveliness/lease duration，也未注册Liveliness changed/lost事件处理。Liveliness用于判断publisher是否仍被middleware认为存活，不证明消息数值有效、更新周期符合预期或机器人正在正确响应。一个进程/节点仍存活但业务循环已卡住的情形，不能仅靠进程存活证明有新命令。
4. QoS兼容性采用request/offered规则；不兼容的Reliability、Durability、Deadline、Liveliness等组合会阻止endpoint建立通信。即使topic名称和类型完全一致，也必须检查实际endpoint QoS以及matched publisher/subscription状态。
5. QoS deadline miss、lifespan丢样、liveliness丢失和controller命令超时是不同事件。前三项属于middleware通信QoS层；最后一项必须由接收端应用/控制器基于命令年龄或最近接收时间独立实现。

### F. 风险分级

- **P1：传输可靠性与命令时效性未分离。** Reliable不能保证按控制周期及时到达；BestEffort可能丢帧。当前没有端到端命令年龄/序号校验。
- **P1：QoS配置全为SystemDefaults。** history/depth、reliability、durability和liveliness由RMW解析；未锁定部署QoS基线。
- **P1：没有显式Deadline/Lifespan和QoS事件处理。** middleware不能提供可验证的周期违约监视或传输年龄上限；即便补上也不能替代应用缓存watchdog。
- **P1：单槽位Box不保存每个中间样本。** 高于controller update吞吐的消息可能覆盖中间值；try_get失败时继续使用上次缓存值。
- **P1：Float64MultiArray不携带消息产生时间或序号。** 接收端无法区分最新命令、迟到旧命令和发送方重启后序号回退。

### G. 新增验收矩阵

| ID | 场景 | 通过条件 | 当前状态 |
|---|---|---|---|
| SERVO-37 | 目标RMW/DDS QoS盘点 | 归档Servo publisher与controller subscription实际history/depth/reliability/durability/deadline/lifespan/liveliness/lease | 仅源码可确认SystemDefaultsQoS；未采集 |
| SERVO-38 | 队列深度对照 | 在depth 1/候选depth及250Hz速率下测量积压、丢帧、旧样本年龄；明确只消费最新值还是保留中间样本 | 未执行 |
| SERVO-39 | Reliable断网/恢复 | 注入延迟、丢包、短时断连与恢复；不允许超过时效预算的旧样本驱动接口 | 未执行 |
| SERVO-40 | BestEffort丢帧 | 注入样本丢失，验证接收端命令年龄watchdog在预算内触发且不静默沿用旧目标 | 未执行 |
| SERVO-41 | Deadline事件 | 设定与周期预算一致的deadline，验证offered/requested missed事件可观测并触发降级策略 | 当前未配置/未注册回调 |
| SERVO-42 | Lifespan过期样本 | 设置有限lifespan，发布端到订阅端延迟超过阈值时确认样本不进入回调；同时验证已缓存旧命令仍由应用watchdog处理 | 当前未配置；未执行 |
| SERVO-43 | Liveliness丢失 | publisher进程退出/业务线程冻结，验证liveliness事件与应用命令watchdog各自触发时限 | 当前未配置/未注册回调 |
| SERVO-44 | Box最新值/中间样本行为 | 两个update周期之间注入多条带序号命令，记录覆盖、消费值及最大年龄；明确接口只承诺最新值 | 静态识别单槽位；未执行 |
| SERVO-45 | Box try_get竞争 | 注入锁竞争/高负载，确认try_get失败时旧值重写的次数、持续时间和安全降级动作 | 静态分支可追溯；未执行 |
| SERVO-46 | 端到端时效与重启隔离 | 通过带时间戳/序号/源ID/epoch的命令契约识别迟到、乱序、重复和publisher重启；超龄命令被拒绝 | 当前消息不含这些字段；未实施 |

### H. 整改建议

1. 为部署配置明确QoS合同，不再把SystemDefaultsQoS视为产品参数。候选基线可从KEEP_LAST(1)开始评估；Reliable或BestEffort应依据丢包/延迟/恢复实验和安全风险预算选择，不以“可靠”一词代替新鲜度证明。
2. 根据250Hz周期和端到端控制时效预算，显式评估Deadline、Lifespan和Liveliness lease。Deadline/Liveliness必须注册事件回调并形成状态机；Lifespan应约束DDS传输阶段，不应代替controller侧watchdog。
3. 在ForwardCommandController或专用命令适配层增加接收时刻（单调时钟）、最大命令年龄、source ID、session epoch和sequence检查；超龄、重复、回退、未授权源或epoch不符时拒绝命令并进入明确故障状态。
4. 将`Float64MultiArray`替换为带Header/时间戳和显式关节名/序号/来源身份的受控命令消息，或在其上游部署协议适配层。时钟同步若不具备可验证性，应将本地接收超时与DDS Lifespan组合使用，并明确其不能单独检测传输前已积压的远端旧值。
5. 若系统确实只需要最新设定值，单槽位覆盖可以作为明确的接口设计，但需增加sequence/age观测与过载测试；若需要每个采样点连续保留，则应使用有界队列并定义溢出策略，不能同时假定无丢样与严格实时。
6. 所有断流、DDS重连、QoS不匹配、队列积压和Box争用试验先在fake hardware/SIL中开展；真实机器人验收须在风险评估、限速限区和独立安全停止系统可用的前提下进行。

### I. 本节来源记录（#1721–#1725）

| 编号 | 固定来源 | 用途 |
|---|---|---|
| #1721 | [ROS 2 Jazzy rmw qos_profiles.h] (`https://github.com/ros2/rmw/blob/jazzy/rmw/include/rmw/qos_profiles.h`) | system_default与default profile字段差异；SystemDefaults各策略保留SYSTEM_DEFAULT/DEFAULT |
| #1722 | [ROS 2 Jazzy QoS settings文档] (`https://docs.ros.org/en/jazzy/Concepts/Intermediate/About-Quality-of-Service-Settings.html`) | reliability/history/depth、Deadline、Lifespan、Liveliness、compatibility与QoS事件语义 |
| #1723 | [ros2_control Jazzy realtime_tools文档] (`https://control.ros.org/jazzy/doc/realtime_tools/doc/index.html`) | RealtimeThreadSafeBox best-effort单值交换与LockFreeQueue保留中间样本的选型指引 |
| #1724 | [ros2_control Jazzy RealtimeThreadSafeBox API源码] (`https://control.ros.org/jazzy/doc/api/realtime__thread__safe__box_8hpp_source.html`) | try_get best effort与set覆盖Box当前值的实现；try_get锁不可得时返回空 |
| #1725 | [ros2_controllers ForwardControllersBase header/source @ c8d2693] (`https://github.com/ros-controls/ros2_controllers/tree/c8d26930ff87bc819db1452af1d45da5bfa3d50d/forward_command_controller`) | rt_command_为RealtimeThreadSafeBox；callback set、update try_get及旧joint_commands_保留路径 |


## 9.3.43 多发布者竞争、命令来源身份与运动控制授权隔离（2026-11-07）

### A. 审查范围与固定版本

- Stäubli ICube驱动与配置固定commit：`bd658e2d266e315d2ee35f985fb352ea88306b79`。
- MoveIt 2 Jazzy固定commit：`6ed6372a72ba9b121ed12ef574ea4ff4d3d92f09`。
- ros2_controllers固定源码快照：`c8d26930ff87bc819db1452af1d45da5bfa3d50d`。
- ROS 2 SROS 2 / DDS-Security官方设计与访问控制策略文档用于核对认证、加密、enclave和topic级授权能力。
- 本节为固定源码、仓库配置与官方安全设计静态审查；未部署SROS2 keystore、未生成/签署权限文件、未启动安全DDS网络，也未执行恶意/未授权publisher注入。

### B. 当前命令链没有应用层发布者身份与仲裁

1. Stäubli Servo的`Float64MultiArray`输出topic是`/forward_position_controller/commands`。消息只有数值数组，没有`source_id`、认证主体、命令租约、epoch或sequence。
2. ros2_controllers固定源码中的ForwardControllersBase创建普通topic subscription。callback只检查controller lifecycle ACTIVE以及数组中所有值有限，然后将消息写入`rt_command_`；没有检查publisher GID、ROS node name、enclave身份、授权token或source优先级。
3. 同一个topic允许多个匹配publisher时，subscription会收到来自各publisher的样本。callback按到达顺序覆盖单槽位Box；两次controller update之间最后写入Box的样本成为下一次可读取值。网络调度和executor调度决定到达顺序，不能保证业务优先级、发布者优先级或“Servo永远胜出”。
4. 即使某一发布者以更高频率发布，也不能认为它拥有控制权；另一个publisher的样本可能在其之后到达并覆盖槽位。控制器不会检测控制源切换，也不会对源身份变化执行平滑过渡、重新授权或安全停止。
5. MoveIt Servo的JointJog/Twist/Pose输入topic各自只有一个subscription对象，但ROS topic允许多个publisher。对应callback仅把收到的消息复制到`latest_joint_jog_`/`latest_twist_`/`latest_pose_`并置位标志；没有publisher身份校验或多源仲裁。若多个上游节点向同一输入topic发布，Servo处理的是executor最后更新的latest消息。
6. Servo内部会按当前CommandType处理一种输入类型，并清除另外两种类型的new-message标志；这不是多个publisher的授权隔离机制。任何能向当前有效输入topic发布的参与者都可能影响Servo命令。
7. 因而当前链路存在两处独立多源入口：上游Servo输入topic和下游ForwardController输出topic。只保护其中一端不能形成完整的命令授权边界。

### C. DDS/SROS2能提供什么，不能提供什么

1. ROS 2默认不启用DDS-Security；官方设计说明SROS2通过DDS-Security提供身份认证、通信加密和访问控制。部署需要每个安全参与者对应的身份材料、签名governance与permissions文件。
2. SROS2 access-control policy支持按topic限制publish/subscribe权限，亦支持service request/reply和action call/execute权限。可将Servo命令输出topic仅授权给Servo enclave发布，并仅授权ForwardController enclave订阅；对Servo的JointJog/Twist/Pose输入topic仅授权给指定上游命令网关发布。
3. 必须启用`ROS_SECURITY_ENABLE=true`并将`ROS_SECURITY_STRATEGY=Enforce`用于强制模式。官方设计说明默认是permissive：安全材料缺失时可无安全启动；strict Enforce模式下缺失材料应导致启动失败。仅生成keystore或设置enclave参数，不等于安全策略已启用。
4. Enclave权限是DDS participant/安全身份级别，不是应用消息中每条命令的业务授权token。若多个ROS节点/进程共用同一enclave或同一授权身份，它们会共享该身份权限；不能用“节点名称看起来可信”替代独立身份和密钥隔离。
5. SROS2 topic ACL控制哪些安全身份可以向topic发布/订阅，不提供应用层多源优先级、控制租约、授权交接、命令序号防重放、运动模式互锁或命令速率限制。获准publisher仍可能发布错误但格式合法的命令。
6. 安全配置应同时限制Servo的`~/pause_servo`、`~/switch_command_type`服务请求权限以及上游JointJog/Twist/Pose输入；否则攻击者即使不能直接写controller topic，也可能通过未授权输入或服务改变运动状态。实际resolved service/topic名称必须以部署namespace/remapping结果生成权限策略。
7. DDS-Security的认证与访问控制不是功能安全急停。证书泄漏、错误ACL、合法publisher失陷、策略签名/更新错误或安全基础设施故障仍需由独立安全控制系统和物理急停覆盖。

### D. 推荐授权与仲裁架构

1. 为每个机器人实例分配独立ROS_DOMAIN_ID/网络隔离域（是否拆域由系统架构决定），并为Servo、上游命令网关、controller_manager/ForwardController、监控/维护工具分配独立enclave和独立密钥，不共享高权限身份。
2. Servo输出命令topic只允许Servo enclave publish；ForwardController enclave只允许subscribe；其他应用、调试工具和遥操作端均拒绝直接publish该topic。
3. Servo输入topic只允许单一命令网关publish。遥操作、自动规划、示教、维护模式等多种来源先进入命令网关，由它实施显式仲裁；不允许多个源绕过网关直接争用同一Servo输入topic。
4. 命令网关/仲裁器必须实现单一active owner、优先级/模式策略、授权租约、心跳/租约到期、显式交接握手、切换期间停止或受控过渡，以及源撤销后旧命令失效。切换不能只靠两个publisher停止/启动的时序假设。
5. 对命令协议增加source identity、session epoch、monotonic sequence、接收端单调时钟年龄和有效期。拒绝未授权源、epoch回退、序号回退/重复、超龄、模式不匹配和越权关节命令；消息字段只是应用协议的一部分，身份真实性仍由安全通道/授权网关保证。
6. 如果短期保留Float64MultiArray，至少在DDS ACL层做到唯一publisher，并通过独立网关封装消息来源/租约/序号校验；不能仅凭Float64MultiArray数组有限且长度正确就视为已授权。
7. 权限策略应遵循最小权限：显式列出必要topic、service、action、parameter/event和发现通信所需权限；避免使用`*`宽泛匹配。对namespace remapping做负向测试，确保攻击者不能通过改名topic绕过权限范围。
8. 密钥/证书轮换、撤销、过期、权限文件签名、keystore备份、设备克隆、生产镜像注入和现场维护访问应纳入安全生命周期。生产环境禁止把开发keystore/私钥提交到公开仓库。

### E. 风险分级

- **P1：ForwardController没有发布者身份/授权检查。** 任何能够连接该topic的publisher都可能覆盖命令单槽位；目前没有应用层控制源仲裁。
- **P1：Servo输入topic同样允许多publisher竞争。** latest-message callback不区分来源，无法保证命令来源优先级。
- **P1：当前Stäubli配置未见SROS2部署/Enforce基线。** ROS 2默认不启用DDS-Security；不能声称topic受到身份认证或ACL保护。
- **P1：同一enclave身份共享权限。** 多个进程/节点若共用身份，不构成彼此隔离；获准身份的失陷会直接影响该身份权限范围。
- **P1：SROS2 ACL不等于业务控制授权。** 不具备控制租约、命令序号/防重放、模式互锁和安全停止语义。
- **P2：权限策略与namespace/remapping耦合。** 规则必须与resolved names同步，并验证改名/重映射后不会扩大权限。
- **P1：安全策略不能替代功能安全。** 必须保留独立安全PLC/安全驱动/急停及安全速度/空间限制等风险评估确定的保护层。

### F. 新增验收矩阵

| ID | 场景 | 通过条件 | 当前状态 |
|---|---|---|---|
| SERVO-47 | 双publisher竞争 | 两个不同身份同时向controller命令topic发布；未经授权publisher被拒绝，命令owner唯一且可追溯 | 未执行 |
| SERVO-48 | Servo输入多publisher | 两个上游publisher同时发送JointJog/Twist/Pose；非授权源不能改变Servo输出 | 未执行 |
| SERVO-49 | SROS2严格模式 | ROS_SECURITY_ENABLE=true且STRATEGY=Enforce；无证书/无enclave进程启动失败 | 未配置/未执行 |
| SERVO-50 | DDS topic ACL | 仅Servo enclave可publish commands，仅ForwardController enclave可subscribe；其他身份被拒绝 | 未配置/未执行 |
| SERVO-51 | 同enclave隔离负测 | 两个进程共用同一enclave时确认其共享权限风险；生产策略要求独立身份且密钥不共享 | 未执行 |
| SERVO-52 | Service权限 | 未授权主体不能调用Servo pause/unpause和switch_command_type服务 | 未配置/未执行 |
| SERVO-53 | Namespace/remap绕过 | 对topic/service重映射、namespace变化和通配符规则执行正反向访问测试，越权全部失败 | 未执行 |
| SERVO-54 | 控制权租约交接 | owner租约过期/撤销/切换时旧源命令失效；新源须完成握手后取得唯一控制权 | 未实现/未执行 |
| SERVO-55 | Replay/epoch/sequence | 注入重复、乱序、旧epoch、重启序号回退和超龄命令，全部被拒绝并可审计 | 当前Float64MultiArray不支持 |
| SERVO-56 | 密钥轮换与撤销 | 轮换、过期、撤销、丢失、镜像克隆和策略签名错误均按fail-closed策略处理 | 未配置/未执行 |
| SERVO-57 | 安全与功能安全独立 | 关闭DDS安全、失去授权网关或安全通信时，独立安全回路仍可执行风险评估规定的停止/限速动作 | 未验证 |

### G. 整改建议

1. 先绘制部署后的完整ROS通信图：所有Servo输入topic、输出topic、pause/switch服务、controller_manager服务、硬件接口和监控/维护通道，并标注每个endpoint所属进程、enclave、命名空间和用途。
2. 在fake hardware/SIL中先部署SROS2 Enforce与最小权限策略，确认启动/发现/参数/服务所需的辅助权限完整，同时验证未授权publisher无法发布。禁止先在实机上试错安全ACL。
3. 建立唯一命令网关/仲裁器，所有遥操作、规划和维护源都必须经它取得owner lease；Servo输出topic只允许Servo发布，ForwardController只允许Servo对应身份发布者通过DDS ACL连接。
4. 将控制owner状态、来源、epoch、sequence、接收时间、租约截止时间和切换原因写入诊断/审计日志；日志不得记录私钥、访问token或敏感凭据。
5. 把SROS2 ACL、应用仲裁、接收端新鲜度watchdog、controller lifecycle互锁和独立功能安全停止形成分层安全论证；任一层失效不应导致未授权运动。
6. 记录RMW/DDS厂商与版本、ROS_SECURITY相关环境变量、enclave路径、签名权限文件版本、证书有效期和launch remapping；启动时检查Enforce确实生效，不能仅依据环境变量配置文件宣称安全已启用。

### H. 本节来源记录（#1726–#1730）

| 编号 | 固定来源 | 用途 |
|---|---|---|
| #1726 | [MoveIt Servo servo_node.cpp @ 6ed6372] (`https://github.com/moveit/moveit2/blob/6ed6372a72ba9b121ed12ef574ea4ff4d3d92f09/moveit_ros/moveit_servo/src/servo_node.cpp`) | Servo输入订阅与latest消息回调、输出publisher和pause/switch服务 |
| #1727 | [ForwardControllersBase @ c8d2693] (`https://github.com/ros-controls/ros2_controllers/blob/c8d26930ff87bc819db1452af1d45da5bfa3d50d/forward_command_controller/src/forward_controllers_base.cpp`) | callback只检查ACTIVE和finite值、rt_command_.set，无来源身份校验 |
| #1728 | [ROS 2 DDS-Security integration / SROS 2 design] (`https://design.ros2.org/articles/ros2_dds_security.html`) | 默认安全关闭、身份认证/加密/访问控制、enclave材料、Enforce/Permissive |
| #1729 | [ROS 2 Access Control Policies] (`https://design.ros2.org/articles/ros2_access_control_policies.html`) | topic publish/subscribe及service/action权限策略 |
| #1730 | [ROS 2 Security deployment guidelines Jazzy] (`https://docs.ros.org/en/jazzy/Tutorials/Advanced/Security/Deployment.html`) | 安全部署、keystore/证书/权限策略生命周期与运行配置 |



## 9.3.44 硬件接口故障、Controller 错误传播与停止行为（2026-11-07）

### A. 审查基线与边界

本节固定 ICube Stäubli driver commit `bd658e2d266e315d2ee35f985fb352ea88306b79`，ROS 2 Jazzy ros2_control 分支源码，以及 Jazzy 官方错误处理文档。ICube 项目自身声明面向 CS9、仅支持 position control、仍属 prototype；因此以下是源码级失效路径审查，不是 Stäubli 安全功能认证或控制器手册解释。来源 #1731–#1736。

### B. ros2_control 的真实错误传播

1. **硬件 read()/write() 返回 ERROR：** ResourceManager 将失败硬件组件名称和错误结果返回 ControllerManager。Jazzy ControllerManager 在 read 或 write 路径中查找使用该硬件 command/state interfaces 的控制器，执行硬件 command mode change 并 deactivate 相关控制器；read 与 write 的硬件错误路径均有相应处理。硬件组件的错误处理遵循 lifecycle，调用硬件 `on_error(previous_state)`。成功恢复回调使硬件回到 UNCONFIGURED；若 on_error 返回 ERROR/FAILURE，组件进入 FINALIZED，ControllerManager 当前没有完整 plugin reload 服务。不能把“控制器被停用”理解成“硬件已重新配置并恢复”。来源 #1732、#1733。
2. **Controller update() 返回 ERROR：** ControllerManager 将出错控制器及其 controller chain group 加入停用列表；对配置的 fallback controller 计算所需接口，执行 command mode change、deactivate 故障链，再尝试按 STRICT 激活 fallback。fallback 未配置、接口不可用或激活失败时，不存在自动生成的安全控制器。该路径不同于硬件 read/write ERROR，不应混为同一种恢复状态。来源 #1732。
3. **异常：** Jazzy 默认 `handle_exceptions=true` 会捕获控制器/硬件异常并按错误路径处理；关闭后异常可能向上传播并导致 ControllerManager 退出。捕获异常不是故障安全保证。来源 #1732、#1734。
4. **停用/重启与命令缓存：** controller deactivate 释放资源并触发控制器自身 lifecycle；重新 activate 的命令初值、缓存清理和是否发出安全命令取决于具体 controller/plugin。硬件组件错误后需按 lifecycle 重新 configure/activate；不能只重新启动 controller 就假设硬件接口已恢复。必须针对所用 controller 和硬件插件实测重激活语义。来源 #1733。

### C. ICube Stäubli HardwareInterface 与通信失效路径

1. **read() 错误传播：** `StaubliHardwareInterface::read()` 在 RobotDriver 不存在/未连接、`read_robot_state()` 失败或 `update_state()` 失败时返回 `hardware_interface::return_type::ERROR`。RobotDriver 对状态消息执行协议有效性与 staleness timeout 检查；超龄消息返回失败，因而触发硬件 ERROR，而不是把旧位置当作新反馈继续使用。
2. **状态冻结：** `RealTimeSocketSubscriber::read_message()` 在没有新消息时会返回先前缓存消息并将 `new_message=false`；RobotDriver 随后通过接收时间检查 staleness。只要超过 state staleness timeout，read_robot_state 返回 false，HardwareInterface::read 返回 ERROR。故状态冻结不是无限期静默沿用，但停止检测时间受 timeout、调度周期和错误传播延迟影响；必须测量实际阈值和最坏延迟。
3. **UDP 连接状态边界：** 当前 RobotDriver 使用 UDP control/diagnostics socket；`is_connected()` 检查 socket connected 和接收线程 ready，并不等于 CS9 端到端仍在响应。网络中断、VAL3 server 停止或控制器故障可能先表现为状态包超龄，而不是本地 socket 立即报告断开。控制器诊断数据读取在当前连接路径中仍是 TODO，不能声称已经闭合 CS9 完整诊断通道。
4. **write() 错误传播：** socket 未连接、机器人状态 error/INVALID、NaN command、unsupported mode 或 `send_robot_command()` 失败时返回 ERROR。对 robot error 和 NaN 分支，代码先调用 `send_stop_all_command()`；但发送失败分支本身不再保证额外 STOP。UDP send 成功只代表本机发送调用成功，不证明 CS9 已收到、接受或完成停止。
5. **on_error() 的实际停止尝试：** 若 RobotDriver 仍报告 connected，`on_error()` 调用 `send_stop_all_command()`，但没有检查该函数的 bool 返回值，随后无条件返回 CallbackReturn::SUCCESS；若 driver 不 connected，则返回 ERROR。由此可确认“尝试发送 STOP”，不能确认“STOP 已送达/机器人已停止”。on_error 成功也只意味着 lifecycle 错误回调成功，不等于安全停止完成。
6. **生命周期重启：** on_configure 建立控制与诊断 UDP socket，并等待首批有效状态消息；on_activate 将 current_control_mode_ 设为 STOP；on_cleanup 断开连接；on_shutdown 在仍连接且控制状态非 STOP 时尝试发送 STOP 后断开。当前静态源码未显示运行中自动重连/自动重建会话、停止确认、控制权重新授权和旧命令清除的完整闭环。
7. **缓存/反馈语义：** read 错误前最后一次有效状态仍留在内部缓存，但错误传播应使相关控制器停用；在重新 configure/activate 前不得把缓存视为有效当前反馈。重新 activate 时控制模式设 STOP，但必须进一步验证命令接口值、VAL3 server会话和控制器状态是否同步复位。

### D. Controller 停用不等于机器人停止

- ros2_control deactivate 是软件生命周期/资源接口动作；它不会单独证明机器人机械臂已完成减速、停止或保持。
- ICube on_error 发送的是驱动协议层 STOP 命令，且发送结果未被检查；若 UDP 路径已失效，该命令可能无法抵达控制器。
- 当前源码不能证明该 STOP 对应某个经认证的安全停止类别、性能等级或安全完整性等级；也不能推断 CS9 安全控制器、驱动软件、机器人制动器和外部安全回路的响应时间。
- 因此必须把软件控制停止、控制器侧运行/保持/错误状态、驱动器/制动器行为、独立急停/防护停止和风险评估所要求的停止功能分别验证。安全停止能力应以目标机器人/CS9配置的受控安全手册、风险评估和验证报告为依据，不以 ROS 日志或 STOP 数据包替代。

### E. 故障注入与端到端停止验收矩阵

以下是待执行验收项，不是已通过测试。时间指标必须由项目风险评估/停止时间测量计划给出，不能在静态审查中臆造统一毫秒阈值。

| ID | 故障注入/场景 | 预期软件行为 | 必须测量/留存的证据 | 状态 |
|---|---|---|---|---|
| SERVO-58 | read() 收到 ERROR / 状态消息超龄 | ResourceManager触发on_error；相关控制器停用；硬件进入预期lifecycle状态 | 错误时间戳、控制器状态、硬件状态、STOP发送结果 | 未执行 |
| SERVO-59 | write() UDP发送失败 | write返回ERROR；相关控制器停用；不得假定STOP已送达 | socket错误、ControllerManager日志、CS9实际状态 | 未执行 |
| SERVO-60 | 断开控制UDP链路但保留本地socket对象 | 状态超龄最终触发read ERROR；控制器停用；安全回路独立有效 | 检测延迟、包龄、控制器停用延迟、机械停止时间 | 未执行 |
| SERVO-61 | VAL3 server停止/CS9重启 | 状态反馈失效触发错误；不沿用旧反馈作为有效值 | 断流到ERROR延迟、重启状态、旧会话拒绝 | 未执行 |
| SERVO-62 | 反馈冻结但网络接口仍存在 | staleness timeout触发ERROR；不得继续报告有效新状态 | 注入冻结时间、timeout配置、最坏检测延迟 | 未执行 |
| SERVO-63 | on_error时STOP发送成功/失败双分支 | 成功分支记录送出；失败分支显式告警并保持故障锁定，不宣称停止完成 | send_stop_all_command返回值、CS9确认/实际停止状态 | 未执行 |
| SERVO-64 | controller update() 返回ERROR | 仅故障controller/chain按配置停用；fallback按STRICT尝试，失败时保持安全状态 | controller chain、fallback激活结果、接口claim | 未执行 |
| SERVO-65 | fallback缺失/激活失败 | 不自动假定有替代控制；系统进入预定义故障锁定状态 | lifecycle、命令输出、操作员告警 | 未执行 |
| SERVO-66 | 控制器 deactivate后重新activate | 验证缓存、命令接口、控制模式和硬件状态全部重置；旧命令不能恢复运动 | 前后缓存值、接口值、会话epoch、首个输出命令 | 未执行 |
| SERVO-67 | read/write ERROR后硬件 lifecycle恢复 | 按UNCONFIGURED→configure→activate流程恢复；若FINALIZED则禁止假装自动恢复 | lifecycle转换记录、接口重新导出、恢复准入检查 | 未执行 |
| SERVO-68 | STOP数据包发出但丢包/CS9不响应 | ROS侧不得以send成功作为停止完成；独立安全停止有效 | 网络抓包、CS9状态、独立安全回路和机械停止测量 | 未执行 |
| SERVO-69 | 端到端停止时间 | 从故障发生到风险评估定义的停止状态，测量多个负载/速度/姿态/工具条件 | 同步采集故障触发、命令、CS9状态、关节速度/位移、停止时间 | 未执行 |

### F. 整改建议

1. 在 HardwareInterface 中对 STOP 发送结果进行显式处理；增加停止确认/状态闭环。若通信已经不可用，进入锁存故障状态并依赖独立安全功能，而不是继续尝试普通 UDP 命令后报告成功。
2. 明确区分“socket本地可用”“收到新鲜有效状态”“CS9应用层在线”“机器人可运动”“机器人已停止”五种状态；状态机必须包含反馈年龄、sequence、连接会话和控制器故障。
3. 为 read/write ERROR、on_error失败、硬件FINALIZED、controller fallback失败和重新激活失败定义统一故障锁存与人工复位/重新授权流程。
4. 为所有控制器建立明确的 deactivate/activate 缓存语义测试；禁止未验证的旧轨迹、旧命令或旧控制权在重启后恢复。
5. 建立 fake hardware/SIL故障注入；通过后再在受控CS9 HIL验证UDP丢包、反馈冻结、VAL3 server退出、CS9重启、STOP确认和重新握手。实机验证需风险评估、低速/限区、现场监护及独立急停可用。
6. 对端到端停止时间按机器人型号、负载、速度、姿态、工具和安全配置测量；按风险评估及受控厂商安全资料判定，不把ROS update周期或网络往返时间当作机械停止时间。

### G. 本节来源记录（#1731–#1736）

| 编号 | 固定来源 | 用途 |
|---|---|---|
| #1731 | [ICube Stäubli HardwareInterface @ bd658e2] (`https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/src/staubli_hardware_interface.cpp`) | read/write/on_error、生命周期、STOP调用与状态缓存 |
| #1732 | [ros2_control Jazzy ControllerManager源码] (`https://github.com/ros-controls/ros2_control/blob/jazzy/controller_manager/src/controller_manager.cpp`) | read/write硬件错误停用关联控制器、update ERROR停用chain及fallback尝试 |
| #1733 | [ros2_control Jazzy read/write错误处理文档] (`https://control.ros.org/jazzy/doc/ros2_control/hardware_interface/doc/handling_errors_during_read_write.html`) | on_error生命周期与FINALIZED恢复边界 |
| #1734 | [ros2_control Jazzy ResourceManager源码] (`https://github.com/ros-controls/ros2_control/blob/jazzy/hardware_interface/src/resource_manager.cpp`) | 硬件read/write错误结果与组件生命周期处理 |
| #1735 | [ICube RobotDriver/Subscriber @ bd658e2] (`https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/src/robot_driver.cpp`) | UDP socket ready、状态包age检查、STOP数据包发送与连接判定 |
| #1736 | [ICube RealTimeSocketSubscriber @ bd658e2] (`https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/src/real_time_socket_subscriber.cpp`) | 缓存消息复用、new_message与接收时间戳/staleness语义 |


## 9.3.45 Stäubli驱动重连握手、VAL3会话复位与旧命令隔离（2026-11-07）

### A. 审查范围

固定ICube driver commit `bd658e2d266e315d2ee35f985fb352ea88306b79`，重点审查RobotDriver UDP连接/断开、RealTimeSocketSubscriber、UDP发送实现、VAL3 `ros2_server` 的启动/控制循环/序号管理，以及已有mock单元测试。来源#1737–#1742。此处区分UDP socket本地配置、收到状态帧、协议版本兼容、VAL3控制循环工作、机器人运动许可和控制权授权；这些不是同一个“连接成功”状态。

### B. 连接流程并非完整会话握手

1. **UDP connect的语义：** `UDPSocketImpl::connect()` 只打开UDP socket、bind本地端口、解析并设置remote endpoint，随后将本地 `is_connected_` 设为true；UDP没有TCP式连接握手，也不验证对端VAL3程序或CS9应用状态。RobotDriver之后创建接收线程，并检查socket connected/receiving。
2. **控制通道首帧检查：** RobotDriver在最多给定timeout内（HardwareInterface传入5000ms）每500ms尝试读取RobotState；要求收到有效ROBOT_STATE且检查协议版本相同。该过程是“收到一个有效状态帧+协议版本匹配”，不是challenge-response，也没有随机nonce、session ID、client身份认证、会话租约或控制权授权。
3. **诊断通道假就绪：** 当前connect流程将 `diag_interface_ready = true` 硬编码，实际 `read_diagnostic_data()` 被TODO注释；因此诊断subscriber ready仅代表本地socket及接收线程已建立，不代表收到有效诊断帧。控制器类型检查代码被注释，VAL3版本兼容检查仍为TODO；connect日志中的firmware版本可能来自未更新的默认/缓存diagnostic对象，不能作为有效身份或兼容性证明。
4. **is_connected()不是机器人在线判据：** 该函数检查两个UDP socket本地标志和接收线程状态，不检查最近状态包age、诊断帧age、CS9应用健康或机器人可运动状态。RobotDriver头文件也明确注明不检查message staleness。
5. **连接后故障没有自动重连：** read/write错误会向ros2_control返回ERROR；源码没有常驻reconnect supervisor、指数退避、重连状态机或自动恢复后重新授权逻辑。再次连接依赖HardwareInterface lifecycle重新执行on_configure（或外部管理器触发恢复），不是read失败后自行恢复。on_configure的connect失败会返回CallbackReturn::ERROR。
6. **清理与重建：** disconnect销毁control interface/diagnostics subscriber，停止接收线程、关闭socket并调用reset_data将RobotDriver当前消息类型设为INVALID、序号归零。下一次connect重建RealTimeSocketSubscriber对象，其first_read和last_read_sequence_number重新初始化。该过程是客户端本地对象/缓存重建，不构成分布式会话协商。

### C. VAL3侧启动、错误复位和序号语义

1. **VAL3启动复位：** `start.pgx` 清空control socket buffer，调用stopMove()/resetMotion()，再以4ms周期创建controlTask。controlTask启动时把控制状态设为STOP/Idle，sequence number设为0，初始化消息并调用resetControlSocket清空socket缓冲。
2. **序号不是会话ID：** `getNextSequenceNumber.pgx` 仅将uint16 sequence递增并在65535后回绕到0。没有boot ID、session epoch、随机nonce或客户端generation；sequence只能用于当前循环的延迟/丢包估计，不能区分控制器重启前后或ROS客户端重启前后的命令会话。
3. **错误复位：** controlTask在错误/通信时延超限时尝试停止当前控制模式、调用stopMove()/resetMotion()、将command invalid、清除socket buffer、将sequence和控制活跃状态归零，再resetControlSocket。代码TODO明确写有“接受新命令前增加延迟”，目前未实现。因此错误复位后没有明确的冷却时间、操作员确认或新授权门槛。
4. **旧命令新鲜度：** VAL3循环对控制延迟基于state/command sequence差计算；运动中delay超过5个控制周期（注释约20ms）会进入STOP/error，静止时超过25个周期（注释约100ms）会进入STOP/error。但“无新命令且上一条命令有效”的staleness处理标为TODO；缺少显式命令age、session epoch、owner lease和重放防护。不能把序号延迟阈值视为完整旧命令隔离。
5. **错误后重新接受命令：** 错误处理将控制活跃状态和command validity清除并清socket buffer，但源码没有在复位后等待外部授权或新的会话挑战；注释反而将延迟/冷却机制留作TODO。应验证控制task错误恢复后是否立即接受下一条有效数据帧，以及该行为是否满足项目风险控制。
6. **服务器端安全边界：** 状态帧中包含安全状态、急停、运动可能性等观测字段，但VAL3控制循环中若干更深层故障检测仍标TODO（例如机器人非预期运动、急停/运行时错误处理）。ROS侧接收到状态字段不能代替CS9自身安全功能。

### D. UDP发送返回值的关键缺陷

`UDPSocketImpl::send()` 对 `boost::asio::error::would_block` 的处理是：日志明确表示packet dropped，但随后仍返回true。上层 `RealTimeSocketInterface::send_message()` 因此会把“内核发送缓冲区满、数据包已丢弃”报告为发送成功。它不是网络对端确认，甚至不是本机数据报已排队的可靠确认。该问题直接影响命令确认、STOP发送记录、通信恢复判断和SERVO-63/68故障注入的判定：必须新增明确的drop计数/失败返回/故障阈值，不能以当前bool结果作为STOP或运动命令送达证据。

### E. 当前测试覆盖及缺口

- `test_robot_driver.cpp` 已有ConnectionTest、DisconnectionTest、ReadRobotStateTest。ReadRobotStateTest在同一连接对象上停止mock状态发送超过600ms，验证staleness失败；再恢复mock发送并在同一socket/session内验证状态读取恢复。
- 该测试不是断开并重建UDP socket、不是VAL3/CS9重启，也不验证新旧session隔离、状态序号回绕、旧命令排空、命令重放或授权恢复。
- 当前未发现覆盖UDP `would_block` 被报告为成功、诊断帧缺失仍connect成功、协议版本错误、VAL3错误复位后立即接受新命令、客户端重连后首条命令门控的自动化测试。
- 因而已有测试只证明mock UDP状态流在单次会话中停止/恢复读取的部分行为；不能据此宣称CS9/VAL3重启重连和运动控制恢复已验收。

### F. 推荐会话状态机与整改

推荐显式状态机：`DISCONNECTED → SOCKETS_BOUND → CONTROL_STATE_VALID → DIAGNOSTICS_VALID → PROTOCOL_COMPATIBLE → ROBOT_SAFE_STATE_CONFIRMED → CONTROL_OWNER_GRANTED → ACTIVE`。任何状态帧超龄、序号/协议错误、CS9/VAL3重启迹象、UDP发送drop、控制器ERROR或生命周期异常，都进入 `FAULT_LATCHED`；故障锁存态不允许自动恢复运动。

1. 引入由CS9/VAL3启动时生成的boot/session epoch，并在状态与命令两向携带；每条命令含source identity、session epoch、monotonic sequence、产生时间/有效期和授权租约。重启/重连必须更换epoch，拒绝旧epoch及旧owner命令。
2. 增加明确握手：ROS客户端发起随机nonce/版本/客户端身份；VAL3回应自身boot ID、软件/协议版本、控制器类型和状态；客户端确认后建立session。诊断通道必须收到并验证有效帧，不能用本地socket ready代替。
3. 对UDP发送实现可靠的本地drop语义：would_block必须返回失败或独立的DROPPED状态，计数、告警并纳入故障阈值；关键命令需应用层确认和超时处理。UDP应用层ACK仍不等于机器人机械停止。
4. VAL3控制循环补齐无新命令时的staleness监控、明确复位冷却时间、故障锁存和操作员/上层重新授权；对旧epoch、重复/倒退sequence、过期命令拒绝执行。
5. reconnect成功后先确认CS9/VAL3新鲜状态、协议和版本兼容、控制模式、安全状态、运动停止/静止状态、工具/负载配置与owner lease；需要人工确认的故障不能自动跳过。
6. 建立Fake/SIL测试：丢弃UDP发送（含would_block模拟）、诊断帧缺失、CS9重启、VAL3 task restart、ROS客户端重启、socket重建、序号回绕、延迟/重放旧命令、双客户端竞争、恢复后第一帧运动命令；再进行受控CS9 HIL，最后按风险评估实机验收。

### G. 新增验收矩阵（均待执行）

| ID | 场景 | 预期结果 | 证据 | 状态 |
|---|---|---|---|---|
| SERVO-70 | UDP socket本地connect但CS9/VAL3未启动 | 不得判定robot connected；首个有效状态/握手超时后失败 | socket状态、状态帧、握手状态 | 未执行 |
| SERVO-71 | 控制状态通道有效、诊断通道无数据 | connect不得将diagnostics标记为有效 | 有效诊断帧/age/兼容检查 | 未执行 |
| SERVO-72 | CS9/VAL3重启，sequence从0重置 | 新boot epoch被识别；旧epoch命令拒绝 | boot ID、epoch、sequence日志 | 未执行 |
| SERVO-73 | ROS客户端重启并重建UDP socket | 新session必须重新握手/授权，不沿用旧owner | session状态、owner lease、首命令记录 | 未执行 |
| SERVO-74 | VAL3 controlTask错误复位并清空socket | 故障锁存/冷却/重新授权后才接受运动命令 | VAL3日志、首个有效命令、运动状态 | 未执行 |
| SERVO-75 | 延迟或重放上一session命令 | 旧epoch/过期/重复sequence命令拒绝 | 抓包、拒绝原因、机器人状态 | 未执行 |
| SERVO-76 | UDP send返回would_block | 明确报告DROPPED/ERROR，不能报告发送成功 | 注入错误码、API返回值、drop计数 | 未执行 |
| SERVO-77 | 诊断socket可建但无有效诊断帧 | 不得使用默认diagnostic数据报告固件版本/兼容 | 诊断帧有效性与connect结果 | 未执行 |
| SERVO-78 | 协议版本不匹配/未知VAL3版本 | fail closed，不允许进入可运动状态 | 握手拒绝、版本日志 | 未执行 |
| SERVO-79 | sequence 65534→65535→0及跨boot重置 | 同一session正确回绕，跨session由epoch区分 | 边界测试及状态日志 | 未执行 |
| SERVO-80 | 故障恢复后立即到达旧客户端运动命令 | 旧owner/session不得恢复控制权 | ACL/lease/epoch/运动状态 | 未执行 |

### H. 本节来源记录（#1737–#1742）

| 编号 | 固定来源 | 用途 |
|---|---|---|
| #1737 | [ICube RobotDriver @ bd658e2](`https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/src/robot_driver.cpp`) | connect/disconnect/is_connected、首帧/协议检查、诊断通道TODO与reset_data |
| #1738 | [ICube UDP socket implementation @ bd658e2](`https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/src/communication/udp_socket_impl.hpp`) | UDP connect无应用握手、would_block丢包却返回true |
| #1739 | [ICube RealTimeSocketSubscriber @ bd658e2](`https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/src/real_time_socket_subscriber.cpp`) | subscriber对象创建时序号追踪初始化、消息缓存与接收线程 |
| #1740 | [ICube VAL3 controlTask @ bd658e2](`https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/val3/userapp/ros2_server/controlTask.pgx`) | 4ms控制循环、序号delay门限、错误STOP/清缓存/复位、staleness TODO |
| #1741 | [ICube VAL3 sequence/start/reset programs @ bd658e2](`https://github.com/ICube-Robotics/staubli_driver_ros2/tree/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/val3/userapp/ros2_server`) | uint16序号回绕、启动/错误时归零、socket buffer清理及缺少session epoch |
| #1742 | [ICube RobotDriver unit tests @ bd658e2](`https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/test/unit_tests/test_robot_driver.cpp`) | 已有mock连接/断开/同会话staleness恢复覆盖及重连测试缺口 |


## 9.3.46 VAL3服务端命令接收、超时保护与运动控制模式切换（2026-11-07）

### A. 审查范围与结论边界

固定ICube Stäubli driver commit `bd658e2d266e315d2ee35f985fb352ea88306b79`，静态检查VAL3 `controlTask.pgx`、位置/速度控制启停程序、命令帧解码、UDP读取、序号延迟计算、ROS侧命令消息定义/序列化及现有RobotDriver单元测试。来源#1743–#1750。此节只确认代码路径与静态风险，不代表VAL3编译、CS9执行、SIL/HIL或实机验收。

**核心结论：** VAL3控制循环定义STOP(1)、关节位置(2)、关节速度(3)模式；位置模式有`movejSync`更新路径，速度更新函数当前明确记录“not yet implemented”并返回错误。因此速度控制模式虽然存在协议枚举和分支，不能视为可用功能。模式切换逻辑要求经过STOP，但STOP状态、运动静止确认、命令新鲜度和错误复位授权之间仍有缺口。

### B. 命令接收与解析路径

1. **接收缓存行为：** `readData`以非阻塞方式读取固定长度UDP数据；没有新数据时返回`x_bNewData=false`，不会主动使上一条`robot_command_msg.robotCommand.bIsValid`失效。控制循环在“无新消息且上一条命令仍有效”分支中标注staleness处理TODO，随后仍依据缓存命令计算模式并执行控制更新。故当前没有独立、完整的命令年龄/租约超时保护。
2. **消息帧校验：** `decodeHeader`检查magic number、protocol version及header尺寸；`decodeRobotCommandMsg`检查message type为2、数据长度和解码偏移。但它没有按会话维度验证客户端身份、session epoch，也没有显式拒绝重复或倒退sequence。
3. **序号仅用于延迟估算：** `computeSequenceDelay`用当前发送序号减收到的命令序号，并对uint16回绕做补偿。controlTask在控制活跃后对较大的delay设门限（运动中>5周期、静止>25周期）并转STOP/error；这不是严格的单调序号验证或防重放策略。重复/乱序包可能先被当作普通命令处理，只有差值达到阈值或出现负值时才触发错误路径。
4. **无新数据时继续使用旧命令：** controlTask的staleness分支仍是TODO；只要缓存命令保持valid，模式提取与控制更新会继续使用该对象。位置控制函数内部另有`movejSyncState`/命令刷新相关语义，但不能替代服务端明确的命令租约、过期拒绝与故障锁存。
5. **无效命令处理：** 解码失败会把消息设为无效并进入STOP/error路径；非法命令类型检查却只拒绝小于0或大于4的值。枚举定义实际只说明0–3，故值4会通过前置范围检查，之后落入“Unknown command mode”错误分支。建议将协议允许值收敛为0–3，并对未知值fail closed。
6. **头部和载荷边界：** VAL3解码器对magic/version/type/最终偏移有检查，但需补充畸形长度、payload size与实际数据、所有字段范围、NaN/Inf、远程控制周期合法性和跨版本兼容测试。当前静态代码不能证明所有异常帧均在任何字段访问前被安全拒绝。

### C. STOP与位置/速度模式切换

1. **模式定义：** controlTask注释定义0=Invalid/Error、1=STOP/Idle、2=Joint position、3=Joint velocity。主循环初始化`l_nCmdMode`和`l_nPreviousCmdMode`为1。
2. **位置模式启动/连续更新：** 从STOP进入位置模式时调用`updateJointPositionControl(..., true)`，后续同模式调用传false。位置更新函数检查`bMotionPossible`、命令有效性及命令类型，并使用`movejSync`路径。停止位置模式时调用`stopJointPositionControl`，若movejSync已启动则调用`$movejSyncEnd()`，随后主循环调用`stopMove()`和`resetMotion()`。
3. **速度模式尚未实现：** `updateJointVelocityControl`会检查motion possible、命令有效性和类型；首次调用仅resetMotion并留有速度参数配置注释，安全限位检查为TODO，实际`$setVelCmd`被注释，函数输出“not yet implemented”、设置错误并返回。故STOP→VELOCITY会立即进入错误复位，不能宣称速度模式可运行。
4. **位置↔速度直接切换被禁止：** 当新模式与前一模式不同且两者都不是STOP时，controlTask将当前模式改为STOP、置error并记录“requires a stop”。例如POSITION→VELOCITY或VELOCITY→POSITION不会直接调用新模式启动函数，而会先停止旧模式并执行错误复位。需要单独发送STOP并建立可确认的静止状态后才可能再次尝试新模式；但当前错误复位也会将命令invalid、清空socket buffer并把控制模式置为0，恢复路径还需要新的STOP帧/明确授权测试。
5. **STOP→POSITION/VELOCITY的静止条件：** 当previous mode为STOP而新命令请求运动时，若robot state仍报告`bInMotion`，则拒绝启动并置error。该判断依赖状态反馈字段，未证明反馈时间戳/新鲜度与实际机械静止一致；没有独立停止完成确认或安全静止证明。
6. **STOP动作不是安全停止认证：** `stopMove()`、`resetMotion()`及模式专用stop函数属于VAL3运动API调用路径。它们不自动证明安全类别、停止时间、制动保持或独立急停回路满足目标应用风险要求。

### D. 错误复位、超时与重启边界

- 控制循环遇到接收错误、解析错误、命令时延超限或控制函数错误，会尝试停止运动、把命令设invalid、清理UDP socket buffer并重置序号/控制活跃状态。错误处理末尾将`l_bError`清除以便循环继续，且`TODO: add delay ... before accepting new commands`明确表明冷却门控尚未实现。
- 运行时“机器人非预期运动”“急停按下”“runtime errors”等硬停止检查在controlTask中仍有TODO。不能把状态消息中的字段存在等同于VAL3服务端已实施相应保护。
- CS9/VAL3 task重启时controlTask会把模式设STOP并将sequence归零、清空socket buffer；但没有boot/session epoch或随机握手，因此旧客户端/旧会话命令无法仅靠sequence归零可靠区分。
- 当前没有明确命令源身份、单调序号窗口、过期时间、控制租约、错误锁存和人工/上层重新授权的完整状态机。建议错误后进入FAULT_LATCHED，只有完成新session握手、控制器/安全状态确认和显式授权才允许重新进入ACTIVE。

### E. 新增验收矩阵（均待执行）

| ID | 场景 | 预期结果 | 必须留存证据 | 状态 |
|---|---|---|---|---|
| SERVO-81 | POSITION→VELOCITY直接切换 | 拒绝直接切换；先完成受控STOP并确认静止 | VAL3模式、movejSync状态、关节速度 | 未执行 |
| SERVO-82 | VELOCITY→POSITION直接切换 | 同样要求STOP与静止确认，不保留速度命令 | 模式日志、命令缓存、关节速度 | 未执行 |
| SERVO-83 | STOP→POSITION但反馈仍in_motion | 不启动新运动，保持故障/等待状态 | 状态帧age、in_motion、控制输出 | 未执行 |
| SERVO-84 | STOP→VELOCITY | 当前版本应明确拒绝未实现模式，不得进入伪ACTIVE | 返回错误、控制模式、运动输出 | 未执行 |
| SERVO-85 | POSITION/VELOCITY运行中停止发送新包 | 命令租约超时后失效并锁存；不得无限复用旧命令 | 最后有效包时间、超时检测、停止行为 | 未执行 |
| SERVO-86 | 重复sequence命令 | 明确拒绝重复包，不执行重复目标 | 抓包、sequence窗口、执行计数 | 未执行 |
| SERVO-87 | 乱序/回退sequence命令 | 拒绝旧序号；仅允许当前session内定义的回绕 | 注入序列、拒绝原因、状态 | 未执行 |
| SERVO-88 | 命令模式值4及其他未知枚举 | 在解码/校验边界fail closed，不进入未知执行分支 | 帧内容、拒绝日志、模式输出 | 未执行 |
| SERVO-89 | 错误复位后立即发送运动命令 | 冷却、故障锁存和新授权未完成前拒绝 | reset时间、授权状态、首条命令结果 | 未执行 |
| SERVO-90 | VAL3/CS9重启后重放旧客户端命令 | 旧boot/session epoch命令全部拒绝 | boot ID、epoch、抓包与控制状态 | 未执行 |

### F. 整改建议

1. 将命令协议定义为严格枚举：STOP、POSITION；VELOCITY在实现与验证完成前从可用能力声明中移除或显式标记unsupported；拒绝4及所有未知值。
2. 在服务端增加命令有效期/租约与单调sequence窗口；重复、回退、过期、错误epoch和未知source一律拒绝。超时必须进入明确的故障锁存停止流程，而不是依赖movejSync内部刷新行为。
3. 将POSITION↔VELOCITY切换设计为独立状态机：请求STOP→调用当前模式停止函数→等待新鲜反馈证明静止→清理旧命令/目标→重新验证模式/安全条件→获取新控制授权→启动新模式。
4. 将错误复位后的“清socket buffer”与“新会话建立”分开；加入boot/session epoch、challenge-response、owner lease、冷却时间及人工/上层重新授权。
5. 补齐VAL3运行时安全状态检查、急停/运动许可/非预期运动监控；这些检查必须与独立安全系统边界清晰分离。
6. 对速度控制实现先完成限位、单位/坐标/采样周期定义、速度斜坡/加速度约束、停止策略、通信失联保护及测试，再单独做CS9 HIL与风险评估后的实机验收。

### G. 本节来源记录（#1743–#1750）

| 编号 | 固定来源 | 用途 |
|---|---|---|
| #1743 | [ICube VAL3 controlTask @ bd658e2](https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/val3/userapp/ros2_server/controlTask.pgx) | 模式状态机、STOP转换、序号延迟阈值、staleness/运行时检查TODO及错误复位 |
| #1744 | [ICube VAL3 position control @ bd658e2](https://github.com/ICube-Robotics/staubli_driver_ros2/tree/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/val3/userapp/ros2_server/Control) | 位置模式启动、连续更新、movejSync停止与输入检查 |
| #1745 | [ICube VAL3 velocity control @ bd658e2](https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/val3/userapp/ros2_server/Control/updateJointVelocityControl.pgx) | 速度模式当前未实现、限位检查TODO、返回错误 |
| #1746 | [ICube VAL3 command decoder @ bd658e2](https://github.com/ICube-Robotics/staubli_driver_ros2/tree/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/val3/userapp/ros2_server/Serialization) | magic/version/message type/尺寸解码及缺少epoch/严格sequence拒绝 |
| #1747 | [ICube VAL3 UDP read path @ bd658e2](https://github.com/ICube-Robotics/staubli_driver_ros2/tree/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/val3/userapp/ros2_server/Comm) | 非阻塞读、无新数据时保留上一条有效命令及staleness TODO |
| #1748 | [ICube VAL3 sequence delay @ bd658e2](https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/val3/userapp/ros2_server/Comm/computeSequenceDelay.pgx) | uint16序号差值与回绕处理，仅用于延迟估算 |
| #1749 | [ICube ROS command serialization @ bd658e2](https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/src/communication/messages.cpp) | ROS侧命令帧字段/序号与VAL3解码协议对应关系 |
| #1750 | [ICube RobotDriver unit tests @ bd658e2](https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/test/unit_tests/test_robot_driver.cpp) | 已有mock连接/断开/状态读取测试范围；未覆盖VAL3模式切换/旧命令防重放 |


## 9.3.46 VAL3服务端命令接收、超时保护与运动控制模式切换

**固定版本与范围：** ICube Stäubli driver commit `bd658e2d266e315d2ee35f985fb352ea88306b79`。本节检查VAL3 `controlTask.pgx`、命令/头部反序列化、UDP读取、位置/速度控制函数、停止函数及消息结构。该节为静态源码审查，不代表VAL3程序已在CS9上编译或执行。

### 9.3.46.1 模式定义和实际实现状态

- `controlTask`声明模式：0=Invalid/Error、1=STOP/Idle、2=Joint position、3=Joint velocity。主循环初始化当前/前一模式均为1（STOP）。
- README声明当前驱动仅支持position control，velocity为后续工作；源码与README一致：服务端虽保留模式3分支并调用`updateJointVelocityControl`，但该函数在检查motion_possible、命令有效性和类型后，安全限幅仍为TODO，实际`$setVelCmd`被注释，并明确记录“not yet implemented”，随后返回错误。因此模式3不是可用速度控制。
- 位置模式调用`updateJointPositionControl`，以`movejSyncBegin/movejSync`更新六轴目标；检查motion_possible、命令有效性、类型和`isInRange`关节位置范围，但“目标与当前关节位置距离是否足够近”仍为TODO。不能把关节范围检查等同于速度、加速度、jerk、工作空间/碰撞或安全限幅。
- `stopJointPositionControl`在movejSync非-1时调用`$movejSyncEnd()`；`stopJointVelocityControl`当前仅调用`resetMotion()`。通用STOP分支随后还会调用`stopMove()`和`resetMotion()`。这只是VAL3程序控制路径，停止类别、停止距离和安全完整性均未由本静态审查证明。

### 9.3.46.2 STOP与模式切换语义

- 运动模式之间不允许直接切换：若前一模式与当前模式不同，且新旧两者都不是STOP，程序强制当前模式回到STOP并置错误。故POSITION→VELOCITY、VELOCITY→POSITION均不能直接转换。
- 预期切换必须经过STOP：先结束前一模式，再执行`stopMove()/resetMotion()`；下一轮只有当前一模式为STOP且机器人反馈`bInMotion=false`时，才允许进入新运动模式。
- STOP→POSITION会在首次调用时再次`resetMotion()`，要求`$movejSyncState()==-1`后启动`$movejSyncBegin`；若movejSync仍运行则停止并置错。
- STOP→VELOCITY虽能进入模式3分支，但速度函数未实现，调用后置错，随后进入错误复位路径。不可描述为有效的STOP→VELOCITY切换。
- STOP→运动模式时若反馈仍为`bInMotion=true`，服务端保持STOP并置错，错误路径清理命令、重置socket和序号。该判据依赖反馈字段的真实性/新鲜度；不能据此证明机器人已物理静止。
- 模式切换期间没有独立的“STOP已完成且制动/驱动状态已确认”握手状态机；主要依据`bInMotion`布尔反馈。建议显式定义STOP_REQUESTED、STOPPING、STANDSTILL_CONFIRMED、MODE_PREPARED、ACTIVE等阶段，并要求反馈连续稳定、超时锁存及重新授权。

### 9.3.46.3 命令接收、重复/乱序与超时保护

- VAL3 `readData`最多尝试读取两次；`readDataOnce`以`sioGet`返回字节数是否等于固定缓冲区长度判定完整数据，非零短包作为通信错误。未见队列级命令仲裁或来源身份检查。
- `decodeHeader`检查最小头长度、magic number=43981和protocol version=1；`decodeRobotCommandMsg`检查消息类型=2及总长度与header+payload相符，再按固定布局解出remote control period、motion type、6个float、IO字段。没有在VAL3侧显式验证每个数值有限、remote control period处于允许范围，或命令目标的物理变化率。
- 命令头含uint16 sequence，但服务端没有保存“最近已接受的命令sequence”并逐条拒绝重复、回退或乱序包。当前`computeSequenceDelay`计算的是“最新服务端状态序号 - 收到命令的序号”，用于估计往返/滞后；不是严格的单调命令序号窗口或防重放机制。
- 新包到达时解码覆盖当前命令；没有新包时若上一命令仍有效，staleness检查仍是TODO。之后通过sequence delay阈值间接触发错误：运动中delay>5，静止时delay>25；负delay也触发错误。阈值依赖状态序号与控制周期，不能替代明确的命令deadline、接收时间戳、session epoch和owner lease。
- 运动期间若连续收到重复/旧包，delay可能逐步增大并最终触发阈值；但这不是即时拒绝重复包，且没有显式保证每个序号只消费一次。乱序包可能被当作最新接收命令覆盖当前目标，随后才由delay检查间接发现。必须通过故障注入确认实际行为，不能把现有阈值称为可靠的防重放保护。
- 主循环把`nMotionCmdType<0 or >4`视为非法，但4仍落入后续unknown mode分支并触发错误；有效执行模式实际只有1、2、3。0会被解释为错误/STOP相关路径。应在解析层严格白名单，仅允许1/2/3，并明确拒绝0及4。
- 错误处理会尝试停止、清空socket buffer、清除命令有效标志、重置sequence和control-active标志；随后代码注释明确提出“接受新命令前增加延迟（例如1000ms）”仍是TODO。故错误复位后没有可证明的冷却窗口、会话重协商或人工重新授权，旧客户端在socket重新可读后仍可能重新建立控制。
- 位置控制函数检查目标关节范围，但距离限制TODO；速度函数安全限制TODO且不执行运动。位置模式`$movejSyncState()==1`（上一命令未及时刷新）仅保留注释警告，不将其直接作为错误；全局sequence delay门限是另一路保护，两者的时间语义需要在CS9实测。

### 9.3.46.4 结论与工程建议

1. 当前可确认的有效运动路径仅为VAL3位置模式；速度模式仅有分支和停止函数占位，未实现速度命令执行。
2. 运动模式之间必须经过STOP；但STOP完成只由`bInMotion`反馈判定，没有独立的停止完成握手或稳定时间判据。
3. 服务端具有协议头检查、消息类型检查、长度检查、位置关节范围检查及序号滞后阈值；但缺少严格sequence单调性/重复包拒绝、显式命令age/deadline、session epoch、owner lease、数值有限性/物理变化率验证。
4. 超时/错误处理会尝试STOP、清缓存并重置序号，但冷却窗口和重新授权明确为TODO；不应视为安全锁存或安全重启。
5. 推荐在VAL3命令入口增加固定payload长度/字段范围/有限数检查、单调序号窗口、session epoch与命令deadline；故障进入锁存态，清除运动命令并要求状态确认+显式授权后才能回到ACTIVE。速度控制须在独立限幅、加速度/jerk约束、刷新超时和停止策略完成并测试后才开放。
6. 任何STOP/复位流程都必须与CS9安全功能、外部急停/防护装置及风险评估区分；ROS/UDP/VAL3普通命令不是安全功能。

### 9.3.46.5 新增验证矩阵（SERVO-81–SERVO-90）

| ID | 注入/场景 | 预期验收条件 | 证据 | 状态 |
|---|---|---|---|---|
| SERVO-81 | POSITION运行时直接发送VELOCITY | 拒绝直接切换，停止并锁存故障，不执行速度命令 | VAL3日志、运动状态、命令抓包 | 未执行 |
| SERVO-82 | VELOCITY运行时直接发送POSITION | 拒绝直接切换；不因模式分支存在而启动位置模式 | 同上 | 未执行 |
| SERVO-83 | POSITION→STOP→确认静止→POSITION | 仅在停止确认及授权后重新启动；目标状态连续 | 状态序列、movejSync日志 | 未执行 |
| SERVO-84 | STOP后仍报告bInMotion=true | 不得启动新模式；超时后故障锁存 | 状态反馈、VAL3日志 | 未执行 |
| SERVO-85 | 重复sequence命令持续注入 | 重复包应被显式拒绝，不得仅等待delay阈值 | 抓包、拒绝计数、目标轨迹 | 未执行 |
| SERVO-86 | 乱序/回退sequence命令 | 旧序号不得覆盖当前命令 | 抓包、序号窗口状态 | 未执行 |
| SERVO-87 | 运动中停止发送命令/延迟超过deadline | 在规定deadline内进入锁存停止；测量停止时间 | 抓包、状态、停止距离 | 未执行 |
| SERVO-88 | 非有限值、极端remote control period、异常payload长度 | 解析层拒绝，不能进入运动更新函数 | 解码结果、VAL3日志 | 未执行 |
| SERVO-89 | 故障复位后立即重放旧命令 | 冷却/新session/重新授权前拒绝 | session日志、首命令记录 | 未执行 |
| SERVO-90 | 速度模式命令3及保留值0/4 | 速度模式明确拒绝为未实现；0/4在解析层拒绝 | VAL3日志、命令状态 | 未执行 |

### 9.3.46.6 本节来源记录（#1743–#1750）

| 编号 | 固定来源 | 用途 |
|---|---|---|
| #1743 | [ICube VAL3 controlTask @ bd658e2](https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/val3/userapp/ros2_server/controlTask.pgx) | 模式枚举、STOP转换、bInMotion判据、sequence delay阈值、错误清缓存/重置与冷却TODO |
| #1744 | [ICube decodeRobotCommandMsg @ bd658e2](https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/val3/userapp/ros2_server/Serialization/decodeRobotCommandMsg.pgx) | 命令消息类型、长度与字段解码、payload字段布局 |
| #1745 | [ICube decodeHeader @ bd658e2](https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/val3/userapp/ros2_server/Serialization/decodeHeader.pgx) | magic number、protocol version、头部长度检查 |
| #1746 | [ICube updateJointPositionControl @ bd658e2](https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/val3/userapp/ros2_server/Control/updateJointPositionControl.pgx) | movejSync启动/更新、motion_possible、关节范围和距离TODO |
| #1747 | [ICube updateJointVelocityControl @ bd658e2](https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/val3/userapp/ros2_server/Control/updateJointVelocityControl.pgx) | 速度控制明确未实现、安全限幅TODO |
| #1748 | [ICube position/velocity stop functions @ bd658e2](https://github.com/ICube-Robotics/staubli_driver_ros2/tree/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/val3/userapp/ros2_server/Control) | 位置模式movejSyncEnd与速度模式resetMotion停止路径 |
| #1749 | [ICube readData/readDataOnce @ bd658e2](https://github.com/ICube-Robotics/staubli_driver_ros2/tree/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/val3/userapp/ros2_server/Comm) | UDP数据读取次数、固定缓冲长度与短包错误处理 |
| #1750 | [ICube VAL3 RobotCommand/MessageHeader types @ bd658e2](https://github.com/ICube-Robotics/staubli_driver_ros2/tree/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/val3/userapp/ros2_server/Types) | 命令字段、6轴数据、uint16序号和协议头结构 |

## 9.3.47 Stäubli VAL3状态遥测来源、有效性标志与物理语义边界（2026-11-07）

### A. 审查范围与固定版本

固定ICube `staubli_driver_ros2` commit `bd658e2d266e315d2ee35f985fb352ea88306b79`。本节交叉检查VAL3 `updateState.pgx`、`RobotState.dtx`、`encodeRobotStateMsg.pgx`，以及ROS侧 `RobotStateMessage` 数据模型和反序列化实现。重点区分直接读取、命令派生近似值、电机电流估算值、软件推导状态和未实现的可选传感器字段。此处为静态源码审查，不代表目标CS9/机器人已验证。

### B. 遥测字段的实际来源

| ROS/协议字段 | VAL3实现 | 可支持的解释 | 不可直接推导 |
|---|---|---|---|
| joint_positions | `herej()` | VAL3返回的当前关节位置值 | 独立外部测量精度、时间戳新鲜度或安全位置反馈 |
| joint_velocities | `$getJntSpeedCmd()` | 控制器提供的关节速度命令/近似值 | 独立实测关节速度、碰撞速度或安全速度 |
| joint_torques / effort | `getJointForce()` | 基于电机电流计算的关节力/力矩数量级估算 | 外部接触力、精密力控反馈、碰撞阈值或安全力矩 |
| brakes_released | `isPowered()`赋值 | 软件以驱动上电状态代理制动器状态 | 制动器线圈/机械释放机构的独立反馈或制动器健康状态 |
| in_motion | `!isSettled()` | VAL3运动/settled判据 | 由独立速度传感器证明的物理静止或安全静止 |
| motion_possible | `isPowered() && !bEStopped` | 软件层的简化运动许可条件 | 完整的CS9安全许可、远程模式、HOLD状态或外部防护条件确认 |
| F/T、数字输入、模拟输入 | `updateState`明确未实现并将valid标志置false | 当前实现不提供有效数据 | 不能因固定帧中存在对应字节区就认为传感器/IO已接入 |

`updateState.pgx`将`bValidPosition`、`bValidVelocity`、`bValidTorque`置true；速度来自`$getJntSpeedCmd`，力矩来自`getJointForce`。源码注释明确说明`getJointForce`结果只提供力的数量级，包含重力、摩擦、黏性、惯性、噪声和电流传感器/电机常数误差，并明确写明不承诺精度。因而valid只代表该软件字段由当前实现填充，不代表计量学意义上的精度、可追溯校准或适用于安全功能。

### C. 状态推导和模式门控风险

1. `bBrakeReleased = isPowered()`是状态代理，不是制动器独立反馈。驱动上电与制动器机械释放/保持能力不是同一物理量；在未取得目标机器人制动器反馈接线、CS9接口和VAL3变量语义前，不能把该字段作为制动器状态证明。
2. `bInMotion = !isSettled()`使用VAL3 settled判据。其可用于普通控制状态监视，但不能单独用来证明停止时间、制动保持或安全静止；尤其应与上一节的STOP/重新授权缺少独立静止握手问题合并看待。
3. `bMotionPossible`当前只由驱动上电和`bEStopped`计算。代码保留了一个被注释的更严格表达式，其中额外要求`nRobotStatus == 0`；而`workingMode`注释说明自动模式状态2表示Hold。当前表达式没有显式把Hold/运行模式状态作为该字段的门控条件。由于`nRobotStatus`含义依赖工作模式，必须按每个CS9工作模式验证枚举映射，不能仅凭注释推断所有模式下的行为。
4. 位置控制函数还会执行自己的motion_possible和其他检查；本节没有证明仅凭`bMotionPossible`为true就能绕过CS9/VAL3自身的所有限制。风险在于ROS上层看到的简化标志可能比真实控制器状态更宽松，需验证并修正字段契约。

### D. 固定帧布局与valid标志

- VAL3初始化RobotState payload为124字节；加8字节header后固定132字节。ROS `RobotStateMessage`按固定布局读取位置、速度、力矩、F/T、数字输入和模拟输入字段。
- `encodeRobotStateMsg.pgx`每帧都会写入固定字段区；可选F/T/IO字段的valid标志由RobotState结构产生，但当前`updateState`把F/T、数字输入和模拟输入valid标志置false，并把F/T数组清零。相应序列化代码中的F/T后3项、数字输入位图和模拟输入值仍为TODO/注释状态。当前实现不会提供这些字段的有效测量；协议固定长度不能作为功能已实现的证据。
- C++ `RobotStateMessage::deserialize`会按固定布局把各字段解码到数组，同时另行解析valid flags。调用方必须同时检查`has_joint_positions/velocities/torques/ft_sensor/digital_inputs/analog_inputs`，不能只看数组内容；无效字段的零值或残留值不得被当作有效测量。
- `has_joint_torques=true`目前对应的是VAL3估算值，不应因字段名或ROS的`effort`接口而误认为高精度力矩传感器读数。ROS状态接口的单位/语义说明必须保留“估算”限定。

### E. 结论与整改建议

1. 将状态接口元数据拆分为`source_kind`（直接读取/命令派生/模型估算/软件推导/未实现）、`valid`、`freshness`、`accuracy`和`safety_qualified`，避免单一valid布尔承担多种含义。
2. 将joint velocity明确标为command-derived estimate；若控制应用需要实际速度，必须确认控制器是否提供实际速度测量源，或通过经过验证的编码器反馈获取，不能静默复用命令速度。
3. 将joint torque/effort明确标为current-derived rough estimate，并记录厂商不承诺精度；禁止将其直接用于精密力控、碰撞检测或安全保护，除非另有传感器、标定、误差模型和独立验证。
4. 将brakes_released改名为或补充说明为`drive_powered_proxy`，除非能取得独立制动器状态反馈；将`in_motion`标注为VAL3 settled-derived状态，禁止作为安全静止确认。
5. 对`motion_possible`建立按Manual/Test/Automatic Local/Automatic Remote及Move/Connection Move/Hold/安全重启状态的真值表；Hold、非远程、未确认安全重启等状态必须有明确预期，不允许用简化布尔字段替代CS9安全链。
6. 对固定帧valid flags增加跨语言黄金向量与负向测试：valid=false时消费者不得使用数据；valid=true时字段来源、单位、精度和更新时间必须明确。F/T与IO字段在真正实现并验证前继续声明unsupported。

### F. 新增验证矩阵（SERVO-91–SERVO-100，均待执行）

| ID | 场景 | 预期验收条件 | 必须留存证据 | 状态 |
|---|---|---|---|---|
| SERVO-91 | 对照VAL3 joint velocity源与独立测量 | 明确区分命令速度和实际速度；偏差/延迟有测量报告 | 同步采样、控制器记录、时间基准 | 未执行 |
| SERVO-92 | 对照getJointForce与外部校准力矩传感器 | 只报告估算误差与适用工况，不宣称未支持精度 | 传感器校准证书、负载/姿态/速度、误差统计 | 未执行 |
| SERVO-93 | 驱动上电但制动器状态异常/反馈断开 | 软件不得把isPowered代理值描述为制动器已机械释放 | CS9状态、制动器独立反馈/接线、故障记录 | 未执行 |
| SERVO-94 | settled状态与外部速度测量对照 | in_motion仅作为VAL3状态；静止判定需新鲜、稳定且独立的验收条件 | VAL3状态、编码器/测量设备、时间序列 | 未执行 |
| SERVO-95 | Automatic Hold状态下检查motion_possible | Hold状态不得被上层误判为可执行运动；明确VAL3最终拒绝/接受行为 | workingMode/nRobotStatus、bMotionPossible、命令结果 | 未执行 |
| SERVO-96 | Manual/Test/Automatic Local/Remote逐模式枚举扫描 | nRobotMode/nRobotStatus映射有完整真值表，未知状态fail closed | CS9模式记录、状态帧、映射表 | 未执行 |
| SERVO-97 | Safety Restart/WMS Restart过渡与motion_possible | 安全状态未确认前不授予普通运动许可；与独立安全功能分开验收 | esStatus、wait_ack、控制输出和安全回路记录 | 未执行 |
| SERVO-98 | valid flag为false时消费状态数组 | ROS上层不得把无效F/T、IO或其他字段零值当作有效读数 | golden frame、订阅端日志、负向单测 | 未执行 |
| SERVO-99 | valid flag为true时检查字段来源/单位/更新时间 | 每个有效字段具备来源、单位、更新时间和精度限定 | 接口文档、测试数据、元数据 | 未执行 |
| SERVO-100 | 固定132B状态帧跨语言一致性 | VAL3编码与C++解码逐字段一致；valid flags与数据语义一致 | VAL3导出帧、C++ golden fixture、逐偏移比较 | 未执行 |

### G. 本节来源记录（#1751–#1755）

| 编号 | 固定来源 | 用途 |
|---|---|---|
| #1751 | [ICube VAL3 updateState @ bd658e2](https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/val3/userapp/ros2_server/updateState.pgx) | 位置/速度/力矩来源、valid标志、制动器和motion_possible推导、F/T与IO未实现 |
| #1752 | [ICube VAL3 RobotState.dtx @ bd658e2](https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/val3/userapp/ros2_server/Types/RobotState/RobotState.dtx) | 状态字段、valid flags及六轴/IO数据结构 |
| #1753 | [ICube VAL3 encodeRobotStateMsg @ bd658e2](https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/val3/userapp/ros2_server/Serialization/encodeRobotStateMsg.pgx) | 固定payload字段写入、valid flags及未实现字段占位 |
| #1754 | [ICube ROS RobotStateMessage @ bd658e2](https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/include/staubli_robot_driver/communication/messages.hpp) | ROS侧字段名称、单位注释、有效性标志与协议结构 |
| #1755 | [ICube ROS RobotStateMessage deserialize @ bd658e2](https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/src/communication/messages.cpp) | 固定帧解析和valid flags独立于数组内容的解码行为 |

## 9.3.48 VAL3命令帧Header长度字段的解析后校验缺口（2026-11-07）

### A. 审查范围与固定版本

固定ICube driver commit `bd658e2d266e315d2ee35f985fb352ea88306b79`。交叉检查VAL3 `initRobotCommandMsg.pgx`、`initHeader.pgx`、`decodeRobotCommandMsg.pgx`、`decodeHeader.pgx`，以及ROS侧`RobotCommandMessage::deserialize`。本节仅确认静态解析顺序与校验差异；不推断未执行的异常报文会造成越界、代码执行或机器人运动。

### B. VAL3解析顺序

1. `initHeader`将本地header size初始化为8字节；`initRobotCommandMsg`将payload size初始化为47字节，并将接收缓冲区resize为55字节。
2. `readData`将命令读入固定大小的`robot_command_msg.nSerializedData`。
3. `decodeRobotCommandMsg`首先执行`size(buffer) != header.nHeaderSize + header.nPayloadSize`检查。此时header字段仍是初始化时的8+47，而不是本次报文中的Header值。
4. 随后调用`decodeHeader`，从本次数据覆盖magic、protocol version、message type、sequence和payload size。该函数检查头缓冲区至少容纳本地header size、magic=43981和version=1，但不验证解码出的payload size与实际数据长度的关系。
5. 回到命令解码函数后，检查message type=2并按固定偏移读取remote control period、motion type、6个float、数字输出mask和4个模拟输出；最后只检查读取偏移是否等于固定缓冲区长度。没有再次检查`decoded payload_size == 47`。
6. 因此，若收到固定55字节帧且其Header payload_size字段不是47，前置检查仍可能使用初始化值8+47通过；后续固定偏移解码也不依赖该payload_size，末尾偏移检查仍可能通过。该异常字段不一致不会被当前这条校验路径明确拒绝。

### C. 与ROS C++解析器的差异

ROS侧`RobotCommandMessage::deserialize`先反序列化Header，然后明确检查：

`header.payload_size == get_serialized_size() - header.get_serialized_size()`

对当前命令消息，这一条件要求payload为47字节；不匹配时返回false。因而同一异常帧在C++客户端解析器与VAL3服务端解析器中的拒绝行为不对称。

### D. 风险判断与整改建议

- **已确认：** VAL3命令解析在Header解码前检查长度，解码后未验证payload size与固定命令结构的匹配关系。
- **未确认：** 该不一致是否会导致VAL3底层fromBinary异常、命令字段错读、任务错误或其他控制器行为；需要在SRS/受控测试环境验证，不能仅凭静态代码推断。
- 将解析顺序调整为：先验证接收缓冲区至少包含完整固定Header → 解码Header → 校验magic/version/type → 校验payload size严格等于当前协议版本的固定长度 → 校验实际datagram/frame长度严格等于header+payload → 再读取任何payload字段。
- 对未知版本、未知消息类型、短帧、长帧、payload size小于/大于预期、序号异常和字段非有限值统一fail closed；解析失败必须清除命令有效标志并进入定义明确的故障锁存/停止处理。
- 将协议固定长度、版本和字段偏移由单一协议定义生成或共享，避免VAL3与C++分别维护常量后漂移。

### E. 新增验证矩阵（SERVO-101–SERVO-108，均待执行）

| ID | 注入/场景 | 预期验收条件 | 证据 | 状态 |
|---|---|---|---|---|
| SERVO-101 | 正常55B命令帧，payload_size=47 | VAL3正确解码且与C++ golden fixture逐字段一致 | 抓包、解码日志、字段对照 | 未执行 |
| SERVO-102 | 55B帧但payload_size=46 | Header解码后明确拒绝，不进入payload读取 | 抓包、错误码、控制状态 | 未执行 |
| SERVO-103 | 55B帧但payload_size=48 | 明确拒绝，不因固定缓冲区长度而接受 | 同上 | 未执行 |
| SERVO-104 | 短于55B的UDP datagram | 在任何payload字段访问前拒绝；确认VAL3 sioGet实际返回语义 | 注入记录、返回长度、任务日志 | 未执行 |
| SERVO-105 | 长于55B的UDP datagram | 明确拒绝或按协议定义处理截断；不得静默当作合法55B帧 | 抓包、接收长度、解码结果 | 未执行 |
| SERVO-106 | Header magic/version/type任一非法且payload长度异常 | 拒绝原因稳定，不能因错误标志覆盖顺序而继续解码 | 抓包、错误码、字段快照 | 未执行 |
| SERVO-107 | 解析失败后立即发送合法/旧运动命令 | 旧命令无效；必须遵守故障锁存、冷却与重新授权策略 | 命令序列、状态机日志 | 未执行 |
| SERVO-108 | 对照C++与VAL3同一组畸形帧 | 两端对长度、payload、版本、类型和截断策略保持一致 | 双端测试报告、golden corpus | 未执行 |

### F. 本节来源记录（#1756–#1760）

| 编号 | 固定来源 | 用途 |
|---|---|---|
| #1756 | [ICube VAL3 initRobotCommandMsg @ bd658e2](https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/val3/userapp/ros2_server/Serialization/initRobotCommandMsg.pgx) | 固定payload=47与55B接收缓冲区初始化 |
| #1757 | [ICube VAL3 initHeader @ bd658e2](https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/val3/userapp/ros2_server/Serialization/initHeader.pgx) | Header固定8B初始化 |
| #1758 | [ICube VAL3 decodeRobotCommandMsg @ bd658e2](https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/val3/userapp/ros2_server/Serialization/decodeRobotCommandMsg.pgx) | 解码前长度检查、解码后未校验payload size及固定偏移读取 |
| #1759 | [ICube VAL3 decodeHeader @ bd658e2](https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/val3/userapp/ros2_server/Serialization/decodeHeader.pgx) | 从本次报文读取payload size但不校验与实际帧长度一致性 |
| #1760 | [ICube ROS RobotCommandMessage::deserialize @ bd658e2](https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/src/communication/messages.cpp) | C++侧Header解析后严格校验固定payload长度的对照实现 |

## 9.3.49 VAL3 sioGet UDP接收语义、非阻塞返回值与报文边界（2026-11-07）

### A. 审查范围与依据

固定ICube driver commit `bd658e2d266e315d2ee35f985fb352ea88306b79`。核对VAL3 `readDataOnce.pgx`、`readData.pgx`、`resetControlSocket.pgx`、`ros2_server.dtx`、`sio.cfx`及C++ UDP实现；并查阅Stäubli VAL3 Reference Manual D.280.935.01-F（2020）中`sioGet`说明。手册规定`sioGet`读取字符/数组，直到数组填满或输入读取缓冲区为空；socket timeout=-1时读取现有缓冲区，空缓冲区返回0，读取错误返回-1。手册没有在该API契约中承诺UDP datagram边界与数组读取边界一一对应。

### B. 当前配置和读取行为

1. `ros2_server.dtx`将控制socket链接到`UdpSocket\\control`；`sio.cfx`明确配置UDP，控制端口11000，timeout=-0.001，endOfString=10。VAL3 `resetControlSocket`又将timeout设为-1。
2. `readDataOnce`每次调用`sioGet(socket, fixed_array)`。返回值恰等于数组长度时标记新消息；正数但长度不匹配时标记通信错误；返回0或负数时都保持`x_bNewData=false,x_bError=false`。
3. 因而手册明确规定的`-1`读取错误被误归类为“本次没有新数据”。`readData`最多尝试两次；如果两次均为-1，最终仍向调用方返回无新数据且无通信错误。
4. `controlTask`在无新消息但旧命令有效时仍进入旧命令的sequence-delay/staleness路径；因此不能说负返回值必然导致旧命令无限执行，但底层读取错误没有被及时、明确地提升为通信故障，行为依赖后续sequence-delay门控和控制状态。
5. `sioGet`手册描述的是输入读取缓冲区，不是UDP datagram接收API契约。仅凭返回字节数无法证明多数据报不会被合并读取、单数据报不会被部分读取或接收队列不会覆盖/丢弃。上述情况必须在实际CS9/VAL3版本和SIO UDP配置上测量，不能套用Linux recvfrom语义。
6. `resetControlSocket`将timeout设为-1，符合手册所述的非阻塞读取缓冲区语义：缓冲区空时返回0。注意这与timeout=0（手册描述为无限等待）不是同一配置。

### C. 与C++ UDP实现的边界对照

ROS C++侧使用Boost.Asio UDP socket，`receive_once`的回调按`bytes_transferred`调整vector长度并复制本次接收内容；UDP socket API以单次接收操作报告一个数据报的传输长度。该边界语义不能自动推导到VAL3 SIO层。必须将同一数据报序列（单包、短包、连续包、超大包、乱序/丢包）分别注入C++与VAL3接收路径，比较每次返回长度和帧内容。

### D. 风险判断与整改建议

- **已确认缺陷：** `sioGet==-1`未设置错误状态，readData可能将两次底层读取错误当作正常无数据返回。
- **已确认接口限制：** VAL3手册定义sioGet按输入缓冲区/数组长度读取，没有承诺该函数提供UDP数据报边界语义。
- **待验证问题：** 当前CS9 UDP SIO在短数据报、连续数据报和队列拥塞时是否保留报文边界；是否存在跨报文聚合、分段、丢弃或截断；超出固定数组的datagram如何报告。
- 将读取结果显式建模为DATA / NO_DATA / IO_ERROR；`sioGet<0`立即进入IO_ERROR，不得与正常空缓冲区混淆。
- 若VAL3 SIO不保证datagram原子性，应增加明确的长度前缀/帧缓存状态机，或使用能保留datagram边界的受支持接口；不得仅通过固定长度数组和换行符配置假定边界正确。
- 为每次接收记录返回长度、错误码、帧序号、接收时间和队列丢弃计数；异常后清除旧命令有效状态，并按故障锁存/重新授权规则恢复。
- 明确timeout=-1的非阻塞读取语义，避免将其与timeout=0无限等待混淆。评估`clearBuffer`对Ethernet socket生命周期的影响时，应遵循手册关于socket deactivation的说明，不能把它简单视为纯内存flush。

### E. 新增验证矩阵（SERVO-109–SERVO-118，均待执行）

| ID | 场景 | 预期验收条件 | 证据 | 状态 |
|---|---|---|---|---|
| SERVO-109 | SIO UDP缓冲区空，timeout=-1 | `sioGet`返回0且不置通信错误 | VAL3版本、SIO配置、日志 | 未执行 |
| SERVO-110 | 注入底层读取错误/关闭或失效socket | `sioGet<0`映射为IO_ERROR，不得静默当作NO_DATA | SRS/CS9日志、错误返回值 | 未执行 |
| SERVO-111 | 注入短于固定帧长的单个UDP datagram | 确认返回长度、是否消费完整datagram及后续帧是否错位 | 抓包、VAL3逐次返回值 | 未执行 |
| SERVO-112 | 连续发送两个完整帧且间隔小于控制周期 | 每帧边界与序号可辨识；不得合并成一个伪帧 | 双端pcap、VAL3日志 | 未执行 |
| SERVO-113 | 一个短帧紧接一个完整帧 | 短帧被拒绝后，下一完整帧仍从正确边界开始解析 | 抓包、帧内容/序号 | 未执行 |
| SERVO-114 | 一个完整帧紧接另一个完整帧，读取数组已满 | 明确第二帧留在队列、被丢弃或可下一次读取；行为有文档 | 队列实验、逐次返回长度 | 未执行 |
| SERVO-115 | 注入超过固定接收数组的UDP datagram | 明确报告截断/长度异常，不接受其前缀为完整命令 | 最大长度扫描、抓包 | 未执行 |
| SERVO-116 | 高速突发使接收队列积压 | 明确测得队列深度/丢弃行为，控制端不执行过期命令 | 突发测试、序号与时间戳 | 未执行 |
| SERVO-117 | 对照VAL3 SIO与C++ Boost.Asio接收同一数据报语料 | 明确两侧边界/长度/截断策略差异并有一致性策略 | 同步pcap、golden corpus | 未执行 |
| SERVO-118 | IO_ERROR后恢复正常数据流 | 旧命令失效，须满足故障锁存、冷却和重新授权条件 | 状态机日志、命令序列 | 未执行 |

### F. 本节来源记录（#1761–#1766）

| 编号 | 固定来源 | 用途 |
|---|---|---|
| #1761 | [ICube VAL3 readDataOnce @ bd658e2](https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/val3/userapp/ros2_server/Comm/readDataOnce.pgx) | sioGet返回值分支，-1未处理 |
| #1762 | [ICube VAL3 readData @ bd658e2](https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/val3/userapp/ros2_server/Comm/readData.pgx) | 两次读取尝试及错误传播 |
| #1763 | [ICube VAL3 SIO config @ bd658e2](https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/val3/configs/sio.cfx) | UDP控制socket配置、timeout和端口 |
| #1764 | [ICube VAL3 socket binding @ bd658e2](https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/val3/userapp/ros2_server/ros2_server.dtx) | 控制任务SIO绑定 |
| #1765 | [ICube C++ UDP implementation @ bd658e2](https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/src/communication/udp_socket_impl.hpp) | Boost.Asio UDP单次接收长度与vector处理 |
| #1766 | [Stäubli VAL3 Reference Manual D.280.935.01-F (2020)](https://bvdp.inetdoc.net/files/iut/robotiqueBUT2/Manuel_de_ref_VAL3.PDF) | sioGet读取终止条件、timeout=-1/0及0/-1返回语义 |

## 9.3.50 VAL3 clearBuffer对Ethernet UDP Socket生命周期的影响（2026-11-07）

### A. 固定源码调用链

固定ICube driver commit `bd658e2d266e315d2ee35f985fb352ea88306b79`。调用关系如下：

1. `start.pgx`在创建controlTask之前调用`clearBuffer(siSocketControl)`。
2. `controlTask.pgx`启动后调用`resetControlSocket`。
3. `resetControlSocket.pgx`设置timeout=-1、endOfString=10，然后再次调用`clearBuffer(x_UdpSocket)`。
4. 控制循环先编码并通过`sendData`发送状态，再调用`readData`接收命令。
5. `stop.pgx`停止运动并调用`clearBuffer(siSocketControl)`。

### B. 手册语义与影响

Stäubli VAL3 Reference Manual D.280.935.01-F（2020）对`clearBuffer(sio)`说明：该函数清空输入读取缓冲区并返回清除的字符数；对于Ethernet socket，`clearBuffer`会使socket失效/关闭；若socket已经失效，则返回-1。手册同时说明Ethernet socket在VAL3程序首次读取或写入时激活，`sioGet`在socket未激活时会尝试建立连接。由此可确认：

- 当前注释“Clear socket buffers”不完整：调用不仅清理输入缓存，还会关闭/停用Ethernet socket。
- `start`和`resetControlSocket`在控制任务开始前后连续调用clearBuffer，第二次调用可能遇到socket已经停用而返回-1；当前代码忽略该返回值。
- 后续`sendData/sioSet`或`readData/sioGet`会触发socket重新激活（具体UDP配置和CS9固件上的实际行为仍需验证）。因此启动路径包含明确的停用—重新激活生命周期切换，而非单纯的队列清空。
- `stop`调用clearBuffer会关闭/停用socket；如果停止入口与控制任务并发执行，是否存在读写竞态、重开socket或任务未退出后继续访问的情况，必须检查任务调度和实机时序。当前静态代码不足以证明并发竞态实际发生。
- 对已停用socket再次调用clearBuffer的-1返回值没有被检查；这可能是预期的重复清理结果，但目前没有明确记录/验证。

### C. 整改建议

1. 将封装函数重命名/注释为`deactivateSocketAndClearInput`一类明确语义，区分纯清空数据与关闭socket。
2. 检查并记录clearBuffer返回值；对“已经停用”的-1按明确状态处理，不得与其他错误混淆。
3. 明确socket生命周期状态机：INACTIVE → ACTIVATING → ACTIVE → DEACTIVATING；只允许一个任务拥有socket生命周期管理权。
4. 在stop流程中先停止/等待controlTask退出，再关闭socket；若VAL3任务模型保证stop程序只在主任务退出后执行，应通过SRS/CS9证据记录该保证。
5. 启动流程只执行一次有定义的清理/停用操作；之后由明确的首次发送/接收路径激活socket，并确认首帧不会被丢弃或延迟。
6. 将“清空旧命令”与“关闭socket”拆成两个需求分别验收，避免为清理旧数据而无意引入通信中断。

### D. 新增验证矩阵（SERVO-119–SERVO-125，均待执行）

| ID | 场景 | 预期验收条件 | 证据 | 状态 |
|---|---|---|---|---|
| SERVO-119 | 对active UDP socket调用clearBuffer | 记录返回值、socket激活状态、远端可达性及队列清理效果 | VAL3日志、双端抓包 | 未执行 |
| SERVO-120 | 对inactive socket调用clearBuffer | 明确验证-1语义；调用方按预期处理，不误报其他故障 | 返回值、状态日志 | 未执行 |
| SERVO-121 | start与controlTask连续执行两次clearBuffer | 第二次调用行为明确，首次状态发送/命令接收能正常重新激活 | 启动时序、首帧抓包 | 未执行 |
| SERVO-122 | clearBuffer后由sioSet首次写入 | socket自动激活行为、首个状态帧送达及延迟可测 | 抓包、时间戳 | 未执行 |
| SERVO-123 | clearBuffer后由sioGet首次读取 | socket自动激活行为、首个命令帧不丢失且边界正确 | 抓包、VAL3日志 | 未执行 |
| SERVO-124 | stop与controlTask并发/任务退出边界 | 关闭socket前任务退出顺序确定，无关闭后访问或意外重开 | 任务状态、时序日志、SRS | 未执行 |
| SERVO-125 | 连续start/stop/restart与残留UDP包 | 重启后旧命令不可执行，socket状态与首帧握手一致 | 多轮循环、序号/抓包 | 未执行 |

### E. 本节来源记录（#1767–#1770）

| 编号 | 固定来源 | 用途 |
|---|---|---|
| #1767 | [ICube VAL3 start @ bd658e2](https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/val3/userapp/ros2_server/start.pgx) | 控制任务创建前调用clearBuffer |
| #1768 | [ICube VAL3 resetControlSocket @ bd658e2](https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/val3/userapp/ros2_server/Comm/resetControlSocket.pgx) | 设置SIO timeout/endOfString并再次clearBuffer |
| #1769 | [ICube VAL3 controlTask @ bd658e2](https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/val3/userapp/ros2_server/controlTask.pgx) | Socket初始化、发送状态、接收命令顺序 |
| #1770 | [ICube VAL3 stop @ bd658e2](https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/val3/userapp/ros2_server/stop.pgx) | 停止运动后调用clearBuffer |



## 9.3.51 VAL3/C++状态UDP发送完整性与失败恢复语义（2026-11-07）

本节固定审查上游 `ICube-Robotics/staubli_driver_ros2@bd658e2d266e315d2ee35f985fb352ea88306b79`。重点区分VAL3的显式写入长度校验、控制任务的故障处理，以及C++ UDP发送接口的返回值处理；本节是静态源码与手册契约审查，不代表已触发网络拥塞或真实CS9发送故障。

### A. VAL3发送路径

- `Comm/sendData.pgx`先拒绝空数组；随后调用`sioSet(x_UdpSocket, x_nData)`，并将返回值与`size(x_nData)`比较。任何返回值不等于完整数组长度（包括-1、0或正数短写）都会设置`x_bError=true`；只有完整长度才清除错误标志。该封装没有实现“从已发送偏移继续发送剩余字节”的重试。
- `controlTask.pgx`每个控制周期先更新状态、递增状态序号、编码RobotState并发送；若编码/发送失败，设置`l_bError=true`。随后仍会进入命令接收/处理段，但命令模式选择会因`l_bError`进入ERROR/STOP路径；本周期执行停止处理（`stopMove()`、`resetMotion()`），清除控制会话状态并调用`resetControlSocket()`。因此不能把VAL3端描述为“发送失败被忽略”；它具有错误置位与停止/重置路径。
- 但该路径没有对状态帧发送失败做独立计数、连续失败阈值或退避；发送失败会影响控制通道本身，主机可能同时失去状态反馈。错误处理后重新接受命令的冷却/重新授权仍是既有TODO（见§9.3.45–§9.3.46）。停止调用和socket重置也不构成独立安全停止证明。

### B. SIO手册契约与部分写入处理

- Stäubli VAL3 Reference Manual D.280.935.01-F（2020）说明`sioSet`返回实际写入字符数；Ethernet socket未激活时会尝试打开；输出等待超时返回-1；通信错误时返回数可能小于数组长度。
- Stäubli VAL3编程手册 D.280.935.01-G（2021）进一步说明：若内部缓冲区已满，`sioSet`返回数可能与请求数量不同，Socket不会因此关闭，调用方需要对未写入的剩余数据重新执行写入。
- 当前`sendData.pgx`仅检测长度不匹配并升级为控制错误，没有按手册描述的剩余字节偏移继续发送。因此存在两层需区分的问题：一是短写/超时会导致当前状态帧未完整输出；二是实现直接把它转为控制故障和socket reset，而不是尝试补写。不能仅凭手册“Socket不会关闭”推断当前UDP配置的线上数据报边界、短写后续补写是否能保持同一数据报；必须在目标CS9与对应VAL3版本确认SIO对UDP socket的具体行为。若协议设计要求一帧对应一个UDP datagram，不能未经验证地将剩余字节作为第二次`sioSet`追加发送。

### C. C++ UDP发送路径与跨端不对称

- 固定源码`udp_socket_impl.hpp`的`UDPSocketImpl::send()`调用Boost.Asio `socket_.send_to(..., MSG_DONTWAIT, err)`，但没有保存/检查其返回的`bytes_transferred`。
- 当`err == would_block`时，代码记录“Packet dropped”，但不返回false，而是继续返回true；注释说明这是为了避免阻塞实时线程，并明确TODO考虑丢包计数/阈值错误。因此发送缓冲区拥塞导致命令数据报被丢弃时，上层可能仍得到成功语义。该行为已在§9.3.45记录，本节进一步与VAL3发送端作跨语言语义对照。
- 对其他非零错误码，C++返回false；对无错误返回true。当前没有检查返回字节数是否等于输入vector长度。UDP常规数据报发送通常以完整数据报为单位，但这里不能把未检查的API返回值当作应用层完整性验收，也不能用VAL3的SIO字符写入数语义直接替代Boost.Asio UDP datagram语义。
- 因此两端语义不对称：VAL3把任何短写/超时作为错误并触发控制任务停止/重置；C++对would_block明确丢弃但返回成功，对其他错误返回失败，且未核对实际发送长度。两端均没有端到端确认机制；发送API成功不证明对端收到、解析或执行。

### D. 影响、修复方向与验证要求

1. 为VAL3发送封装定义明确的传输契约：若目标CS9的SIO允许对同一UDP datagram做部分写入续传，按返回数推进偏移并验证最终长度；若无法保证续传仍属于同一datagram，则将短写视为不可恢复帧错误并在协议层重新发送完整帧，不能把余量盲目作为独立UDP包发送。
2. 为C++ `send_to`保存并检查返回字节数；would_block必须向上层传播“本帧未发送”或通过明确的丢包状态/计数和控制器看门狗策略处理，不能继续返回无条件成功。实时线程不得因重试而无界阻塞。
3. 在两端统一定义发送失败的状态机：命令发送失败、状态遥测发送失败、连续丢包、超时、会话重置、恢复冷却和重新授权分别处理；不得把UDP本地发送成功视为控制器已接收确认。
4. 建立VAL3与C++跨端发送故障注入：满长度成功、SIO返回-1、SIO正数短写、内部缓冲区满后续写、Boost.Asio would_block、其他系统错误、返回字节数异常、连续丢帧、状态通道中断与控制通道恢复；记录原始抓包、VAL3日志、C++返回值、控制模式、机器人停止状态和重新授权过程。
5. 在SRS/CS9上确认UDP SIO短写是否可能发生、短写后续写的数据报边界、socket是否保持激活、resetControlSocket是否丢弃未发送余量，以及失败时机械运动停止的实际时间与安全回路独立性。

### E. 新增验证项（均未执行）

| ID | 验证场景 | 通过条件 | 证据 | 状态 |
|---|---|---|---|---|
| SERVO-126 | VAL3 sioSet完整长度返回 | 返回长度与帧长一致，抓包恰为一帧且内容正确 | VAL3日志/抓包 | 未执行 |
| SERVO-127 | VAL3 sioSet返回-1 | 识别发送失败，不将该帧标记成功；控制状态按设计进入受控故障处理 | SRS/CS9故障注入 | 未执行 |
| SERVO-128 | VAL3 sioSet正数短写 | 确认短写是否可发生及返回长度；不得静默丢弃未发送余量 | 手册版本/VAL3日志/抓包 | 未执行 |
| SERVO-129 | VAL3内部发送缓冲区满与剩余数据续写 | 确认续写是否仍属于同一UDP datagram；否则拒绝采用跨datagram拼帧 | CS9抓包 | 未执行 |
| SERVO-130 | VAL3状态帧发送失败后的控制任务路径 | 验证STOP/reset调用顺序、错误标志清理和socket重新激活 | 任务时序/日志/抓包 | 未执行 |
| SERVO-131 | 连续状态帧发送失败 | 有界计数/故障策略明确，不发生无限重启或无监督自动恢复 | 故障注入/状态机记录 | 未执行 |
| SERVO-132 | C++ UDP would_block | 上层明确收到未发送结果或可观测丢包状态，不返回无条件成功 | 单测/网络缓冲区注入 | 未执行 |
| SERVO-133 | C++ send_to返回字节数检查 | 对返回长度与帧长不一致的情形明确报错/计数 | 单测/Mock socket | 未执行 |
| SERVO-134 | C++其他发送系统错误 | 错误可靠传播至HardwareInterface，触发预期ERROR处理 | 单测/故障注入 | 未执行 |
| SERVO-135 | VAL3与C++同一故障语料对照 | 对成功、短写、超时、拥塞、断线的结果分类一致且有明确差异说明 | 跨端测试报告 | 未执行 |
| SERVO-136 | 发送失败后的恢复与重新授权 | 恢复需满足会话重建、状态新鲜、人工/上层授权及独立安全条件 | SRS/CS9/HIL记录 | 未执行 |

### F. 本节来源记录（#1771–#1775）

| 编号 | 固定来源 | 用途 |
|---|---|---|
| #1771 | [ICube VAL3 sendData @ bd658e2](https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/val3/userapp/ros2_server/Comm/sendData.pgx) | sioSet长度检查、短写直接置错、无剩余字节续写 |
| #1772 | [ICube VAL3 encodeRobotStateMsg @ bd658e2](https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/val3/userapp/ros2_server/Serialization/encodeRobotStateMsg.pgx) | 状态帧编码入口与固定序列化缓冲区 |
| #1773 | [ICube VAL3 controlTask @ bd658e2](https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/val3/userapp/ros2_server/controlTask.pgx) | 状态发送失败后置错、STOP/reset和socket重置路径 |
| #1774 | [ICube C++ UDP socket implementation @ bd658e2](https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/src/communication/udp_socket_impl.hpp) | send_to返回值忽略、would_block丢包仍返回true |
| #1775 | [Stäubli VAL3 Programming Manual D.280.935.01-G (2021)](https://fr.scribd.com/document/655664199/Doc-VAL3) | sioSet部分写入/内部缓冲区满时返回实际数量，Socket不关闭，需重写剩余数据 |



## 9.3.52 控制Socket双向通信时序、控制周期与接收窗口耦合（2026-11-07）

本节固定审查上游 `ICube-Robotics/staubli_driver_ros2@bd658e2d266e315d2ee35f985fb352ea88306b79`。关注VAL3单任务双向通信时序、ROS 2侧异步接收/同步发送、控制周期配置和序号延迟计量。以下为源码静态结论，不是CS9实时性能测量。

### A. VAL3端：一个任务串行完成发送、接收和命令执行

`controlTask.pgx`每轮主循环的实际顺序为：

1. 检查任务超限标志并更新overrun计数。
2. 读取机器人状态、递增状态序号并编码RobotState。
3. 通过同一个`siSocketControl`调用`sendData/sioSet`发送状态帧。
4. 紧接着通过同一个Socket调用`readData`接收命令。
5. 计算序号延迟、检查命令模式和状态，再执行位置/停止等控制动作。
6. 调用`delay(0)`后进入下一轮。

这意味着VAL3侧不是两个独立任务分别收发，而是一个控制任务顺序处理双向UDP。状态帧在本轮命令执行之前生成，因此遥测状态天然反映本轮命令应用前的状态；ROS侧观测到的状态和发出的命令之间存在至少一个任务阶段的流水关系。该顺序本身不等于故障，但协议和上层应用必须按此理解数据新鲜度。

### B. 接收窗口：非阻塞读取，但每轮最多尝试两次

- `resetControlSocket.pgx`将SIO timeout设置为-1。结合§9.3.49引用的VAL3手册语义，这使`sioGet`读取已有输入而不等待未来数据。
- `readData.pgx`每轮最多调用`readDataOnce`两次。收到一帧后，如果第二次没有新数据就退出；若连续收到两帧，则第二次读取会覆盖同一个输入数组，最终上层只解码最后一次读到的完整帧。
- 因而当前逻辑不是无限排空接收队列，也不是严格“每周期只处理一帧”：它最多执行两次SIO读取，并倾向保留两次尝试中最后一帧。若队列积压超过两帧，旧帧可能留待后续周期；具体SIO UDP缓冲区与datagram边界仍受§9.3.49的未决项约束。
- 当本轮状态发送失败时，代码置`l_bError`，但不会立即跳过接收步骤；仍调用`readData`。随后错误状态会使命令模式进入ERROR/STOP处理，并执行stop/reset。也就是说“发送失败后仍尝试读取”是源码事实，但并不表示本轮新命令仍可正常驱动运动。
- 未收到新命令时，旧命令有效性检查中的staleness分支仍为TODO；虽然序号延迟阈值会在控制激活后触发错误，但缺少基于时间戳的独立命令期限/看门狗。该缺口与§9.3.45–§9.3.46一致。

### C. ROS 2端：异步状态接收与控制更新线程同步发送

- `RealTimeSocketSubscriber`在独立接收线程中启动Boost.Asio异步UDP接收；每个数据报到达后先反序列化、打接收时间戳，再写入`RealtimeThreadSafeBox`。随后重新挂起下一次接收。
- 该缓冲结构提供最新消息快照，而不是面向应用的无界消息队列；高于读取速度的状态包可能被后续快照覆盖。读取端用序号差统计丢包，并按接收时间戳检查状态是否过期。
- `StaubliHardwareInterface::read()`在ros2_control更新线程中读取最新状态；`write()`在同一控制更新周期中构造并发送命令。命令发送经`RealTimeSocketInterface::send_message()`同步调用序列化与Socket send；底层Boost.Asio使用`MSG_DONTWAIT`，因此系统调用不等待内核发送缓冲区腾空，但函数本身仍在调用线程内执行，序列化、日志及调用开销仍占用控制更新预算。
- 接收线程优先级和CPU affinity仍标注TODO。由此可知接收回调与ControllerManager线程之间存在调度竞争可能性，但静态代码不能证明发生了实际优先级反转或丢帧。

### D. 控制周期配置与VAL3循环的时间基准不一致

- bringup的`controllers.yaml`设置`controller_manager.update_rate: 250`，即ROS 2侧目标更新周期4 ms；硬件接口将实际`period`写入命令帧的`controller_period`字段。
- `start.pgx`明确设置`l_nCtrlPeriod=0.004`并调用`taskCreateSync`创建4 ms同步任务；`controlTask`末尾的`delay(0)`是同步任务主动让出当前执行片段的调度点，不是唯一的周期来源。此前“没有明确4 ms周期定时器/VAL3没有固定周期声明”的表述撤回。源码配置4 ms不等于已实测证明周期抖动、WCET或长期稳定性。
- Stäubli CS9 2021实时配置文档§4.2说明同步任务按创建周期调度，每次最多执行3000行；若执行超过周期，当前周期正常结束但下一周期被取消，并置位任务创建时绑定的overrun bool。故overrun会形成调度周期缺口，而不是仅代表普通日志事件。
- 当前`controlTask`检测`bIsOverrun`时仅日志、清标志并递增`nOverruns`；该分支不直接置`l_bError`、切换STOP或调用停止函数。它仍继续处理状态、通信和命令。monitor speed低于100%也只warning，随后仍创建任务。
- ROS 2 `controller_manager.update_rate=250`与VAL3 4 ms同步任务名义上同为250 Hz，但两者独立调度，静态代码未显示相位锁定/时钟同步。VAL3序号延迟5/25在无跳周期且稳定4 ms时才近似20/100 ms；overrun取消周期时，序号差可能低估真实墙钟命令年龄。

### E. 整改建议

1. 将VAL3控制任务改为显式、可配置且有界的周期调度，采用单调时间基准测量每轮开始/结束、发送/接收/命令应用时间；周期超限应有计数、阈值和明确故障策略，不能只依赖`delay(0)`和序号差。
2. 将命令时效性从“循环序号差”扩展为带会话标识/发送时间或明确deadline的协议字段，并在VAL3端实现独立staleness watchdog；序号差保留用于丢包/流水诊断，不代替真实时间。
3. 明确每轮最多处理多少命令、积压时保留最新还是按序处理，以及旧命令如何丢弃。对位置命令需定义“最新目标覆盖”策略；对边沿触发/离散IO命令需定义不能被覆盖的可靠传输语义。
4. ROS 2端为发送路径定义最大执行时间预算；将序列化、系统调用、日志和接收回调分别做延迟分布统计。对接收线程设置经系统验证的实时调度策略/CPU亲和性，而不是直接假定线程天然具备实时优先级。
5. 通过统一抓包时钟或硬件时间戳测量状态发出、ROS接收、命令发出、VAL3接收、命令应用和下一状态发出的端到端时序；对网络延迟、丢包、乱序、突发积压和CPU负载分别测量P50/P95/P99/P99.9及最大值。

### F. 新增验证项（均未执行）

| ID | 验证场景 | 通过条件 | 证据 | 状态 |
|---|---|---|---|---|
| SERVO-137 | VAL3单周期完整双向时序 | 状态采样、发送、命令接收、执行顺序及各阶段耗时可追溯 | VAL3时间戳/抓包 | 未执行 |
| SERVO-138 | 状态发送失败后仍接收命令 | 证实接收调用发生，但本轮命令不越过错误STOP门控 | 故障注入/任务日志 | 未执行 |
| SERVO-139 | readData连续0/1/2/3帧积压 | 明确两次读取上限、最终保留帧和后续周期残留行为 | SRS/CS9抓包 | 未执行 |
| SERVO-140 | VAL3命令长期缺失 | 以真实时间期限触发确定性安全状态，不依赖未校准循环计数 | 时间注入/运动记录 | 未执行 |
| SERVO-141 | VAL3 delay(0)循环周期与抖动 | 测得周期分布、最大周期、overrun率及负载相关性 | CS9周期测量 | 未执行 |
| SERVO-142 | ROS 2 250 Hz read/write周期 | 在目标CPU负载下验证read/write耗时及周期抖动预算 | ros2_tracing/系统跟踪 | 未执行 |
| SERVO-143 | 异步接收线程调度延迟 | 记录接收线程优先级、CPU亲和性、唤醒延迟及回调耗时 | OS调度跟踪 | 未执行 |
| SERVO-144 | ROS状态快照覆盖与序号丢失 | 高速突发输入下最新消息、丢包统计和staleness判定符合定义 | 网络注入/单测 | 未执行 |
| SERVO-145 | VAL3与ROS 2时基偏差 | 同步时间戳后能区分网络延迟、排队延迟和任务调度延迟 | 双端抓包/时钟同步 | 未执行 |
| SERVO-146 | 双向拥塞与CPU压力联合测试 | P99.9/最大延迟在预算内，超限触发确定性故障而非旧命令持续执行 | 压力测试/SRS/HIL | 未执行 |
| SERVO-147 | 命令队列积压后的策略 | 明确位置目标覆盖、离散IO不丢失/去重及旧会话帧隔离 | 协议测试/抓包 | 未执行 |

### G. 本节来源记录（#1776–#1783）

| 编号 | 固定来源 | 用途 |
|---|---|---|
| #1776 | [ICube VAL3 controlTask @ bd658e2](https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/val3/userapp/ros2_server/controlTask.pgx) | 状态先发送、再读取命令、处理控制与delay(0)循环顺序 |
| #1777 | [ICube VAL3 resetControlSocket @ bd658e2](https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/val3/userapp/ros2_server/Comm/resetControlSocket.pgx) | SIO timeout=-1配置 |
| #1778 | [ICube RealTimeSocketInterface @ bd658e2](https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/src/real_time_socket_interface.cpp) | ROS线程内同步序列化与send调用 |
| #1779 | [ICube RealTimeSocketSubscriber @ bd658e2](https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/src/real_time_socket_subscriber.cpp) | 独立异步接收线程、时间戳、最新消息快照与序号丢包统计 |
| #1780 | [ICube UDP socket implementation @ bd658e2](https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/src/communication/udp_socket_impl.hpp) | async_receive_from、回调后重挂接收、MSG_DONTWAIT发送 |
| #1781 | [ICube ros2_control controllers.yaml @ bd658e2](https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_bringup/config/controllers.yaml) | ControllerManager update_rate=250 Hz |
| #1782 | [ICube StaubliHardwareInterface @ bd658e2](https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/src/staubli_hardware_interface.cpp) | read/write在控制更新线程内执行，命令帧携带实际period |
| #1783 | [ICube VAL3 computeSequenceDelay @ bd658e2](https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/val3/userapp/ros2_server/Comm/computeSequenceDelay.pgx) | 以状态/命令序号差估算循环延迟 |


## 9.3.53 VAL3同步任务周期、Overrun跳周期与故障门控（2026-11-07）

本节用于纠正§9.3.52对VAL3周期调度的错误表述，并进一步核对同步任务超周期后的实际控制策略。固定上游仍为 `ICube-Robotics/staubli_driver_ros2@bd658e2d266e315d2ee35f985fb352ea88306b79`。结论来自固定版本源码与Stäubli CS9官方实时调度文档，不代表已在目标CS9上测得周期或触发过overrun。

### A. 源码明确创建4 ms VAL3同步任务

- `start.pgx`先设置 `l_nCtrlPeriod = 0.004`，随后执行 `taskCreateSync "controlTask", l_nCtrlPeriod, bIsOverrun, controlTask()`。因此控制循环不是仅靠 `delay(0)` 自由运行的异步while循环；它被创建为周期4 ms的VAL3同步任务。
- `ros2_server.dtx`将 `bIsOverrun` 声明为公开全局bool，初值true；`start.pgx`在创建任务前将其设为false。任务入口又将 `nOverruns=0`，用于本次控制任务运行期间的累计计数。
- `controlTask.pgx`每轮末尾调用 `delay(0)`。结合Stäubli《CS9 Real Time Val3/Fieldbus configuration》§4.2，这条指令用于主动结束本次同步任务片段、让调度器继续执行下一个VAL3任务；周期本身由 `taskCreateSync` 的4 ms参数决定，而不是由 `delay(0)` 决定。
- §9.3.52中“没有明确4 ms周期定时器/绝对时间调度”“VAL3没有对应固定周期声明”的结论撤回。准确表述应为：源码明确请求4 ms同步周期，但本次静态审查没有取得目标控制器实测的周期分布、抖动、WCET或长期稳定性证据。

### B. CS9同步任务的调度与Overrun语义

Stäubli 2021年CS9实时配置文档§4.2说明：同步VAL3任务按创建时指定的周期调度；每次调度最多执行3000条VAL3指令行；实践中常用 `delay(0)` 主动结束本次执行片段；同周期同步任务按创建顺序执行。若同步任务执行时间超过指定周期，当前周期正常结束，但下一个周期会被取消；任务创建时绑定的bool overrun变量被置true，用于向应用报告上一轮调度未完整完成。

据此应区分：

1. 4 ms是本项目显式配置的同步任务请求周期，不是已经实测证明的端到端控制延迟上限。
2. overrun的调度后果不是简单“日志警告后照常补跑所有周期”，而是至少会取消下一次周期调度；发生超限时可能形成一个或多个实际更新间隔缺口。
3. `delay(0)`是同步任务让出/结束当前执行片段的调度点，不是把同步任务改成异步任务，也不提供WCET保证。
4. CS9系统任务、IO刷新、其他VAL3同步任务及CPU资源都会影响可用执行预算。文档指出同步任务消耗较多CPU资源；是否在当前CS9配置下稳定满足4 ms必须测量，不能从源码参数直接推导。

### C. 当前Overrun处理只记录，不触发STOP

固定 `controlTask.pgx` 在主循环开头执行：若 `bIsOverrun` 为true，则记录“Task overrun detected”，将标志清false，并令 `nOverruns = nOverruns + 1`。该分支本身没有设置 `l_bError`、没有将 `l_nCmdMode` 切换为STOP/ERROR、没有调用 `stopMove()` 或 `resetMotion()`，也没有阈值锁存、连续超限退避或任务停用逻辑。

因此，静态证据支持的判断是：**当前代码把同步任务overrun作为日志和累计计数事件处理，而不是直接的运动停止条件。** 不能据此声称发生过实际超周期；也不能把后续其他命令延迟/通信错误可能触发的STOP等同于overrun专属保护。控制循环在处理该标志后仍继续状态更新、收发和命令处理。

另外，`start.pgx`在monitor speed低于100%时只记录warning，随后仍继续创建4 ms同步任务；源码没有在该条件下拒绝启动或调整任务周期。该警告不等于实时性能验证。

### D. 对序号延迟与ROS 2 250 Hz的影响

- ROS 2 `controller_manager.update_rate=250` 与VAL3 `taskCreateSync(...,0.004,...)` 名义上均为250 Hz/4 ms，但它们由不同执行环境调度。静态源码没有显示二者之间存在相位锁定、时钟同步或周期反馈闭环。
- ROS侧将本周期 `period` 写入命令帧，但固定VAL3控制逻辑未见使用该字段来校正同步任务周期或补偿调度偏差；因此不能把ROS发送的period字段视为VAL3周期控制器。
- VAL3序号差门限5/25按名义4 ms周期可解释为约20/100 ms，但在overrun跳过周期、网络丢包或任务调度间隔变化时，序号差不再与真实墙钟时间一一对应。特别是被调度器取消的周期不会执行该轮控制代码及其序号递增，单靠序号差可能低估真实经过时间。
- 目前命令无新帧staleness分支仍为TODO，故overrun计数不能替代独立的命令年龄watchdog。建议保留序号用于顺序/丢包诊断，同时在协议中加入会话epoch、单调时间戳或明确deadline，并以真实时间判定命令失效。

### E. 整改与验收建议

1. 为overrun建立明确的分级策略：单次超限可诊断记录，连续/窗口化超限应触发确定性降级或停止策略；阈值、动作和复位授权须经风险评估及CS9安全验证确定，不能直接把普通VAL3 STOP当作安全功能。
2. 记录每次同步任务进入/退出时间、发送/接收/命令处理阶段耗时、周期抖动、最大执行时间、overrun次数和连续超限长度；同时记录控制器CPU负载、monitor speed、其他同步任务与IO刷新配置。
3. 验证 `bIsOverrun` 的置位/清除时序，尤其在连续超限时是否可能合并事件或被应用清标志操作覆盖；将累计计数和最新overrun状态提供给ROS诊断通道，避免仅存在VAL3全局变量而主机不可见。
4. 在同一时基或经校准的双端时间戳下比较ROS update、UDP发送/接收、VAL3同步任务开始/结束及命令应用时刻；分别统计正常、CPU压力、网络压力和混合压力下P50/P95/P99/P99.9与最大值。
5. 保留ROS 250 Hz与VAL3 4 ms两个独立周期的明确配置和监测，若要求相位/采样同步，需设计并验证专用同步机制，不能仅凭相同的名义周期认定同步。

### F. 新增验证项（SERVO-148–SERVO-160，均未执行）

| ID | 验证场景 | 通过条件 | 证据 | 状态 |
|---|---|---|---|---|
| SERVO-148 | CS9上controlTask同步任务创建 | 实际任务类型、请求周期4 ms、启动/退出状态与源码配置一致 | VAL3任务清单、控制器版本 | 未执行 |
| SERVO-149 | 正常负载下同步任务周期测量 | 记录周期分布、抖动、最大执行时间与CPU负载 | CS9时间戳/跟踪记录 | 未执行 |
| SERVO-150 | 人为制造单次任务overrun | 验证被取消的后续周期、bIsOverrun置位时刻及恢复调度 | CS9任务跟踪/日志 | 未执行 |
| SERVO-151 | 连续overrun与标志清除竞态 | 每次超限事件不被静默合并或覆盖，计数与调度器事件可对账 | 注入记录、nOverruns、任务时间线 | 未执行 |
| SERVO-152 | 单次overrun后的控制门控 | 明确验证当前代码不会仅因该标志直接STOP，并评估是否满足风险要求 | 安全受控SRS/HIL记录 | 未执行 |
| SERVO-153 | 连续/窗口化overrun策略 | 达到经风险评估确定的阈值时触发规定降级/停止与重新授权 | 故障注入、状态机记录 | 未执行 |
| SERVO-154 | overrun与序号延迟相关性 | 测得跳周期后sequence delay与真实墙钟命令年龄的偏差 | 双端同步时间戳/抓包 | 未执行 |
| SERVO-155 | ROS 250 Hz与VAL3 4 ms相位/频率漂移 | 量化两套调度时基偏差、长期漂移和网络往返延迟 | ros2_tracing/CS9跟踪 | 未执行 |
| SERVO-156 | controller_period字段消费核验 | 证明VAL3是否消费该字段；若未消费，协议与文档明确其仅为遥测/预留 | 源码追踪/协议测试 | 未执行 |
| SERVO-157 | monitor speed低于100%启动行为 | 明确warning后任务是否仍启动及周期性能变化，不把warning当作保护 | CS9配置与日志 | 未执行 |
| SERVO-158 | 其他VAL3同步任务/IO刷新竞争 | 评估同周期创建顺序、CPU预算、IO刷新及任务间干扰 | 系统任务配置/跟踪 | 未执行 |
| SERVO-159 | overrun诊断可观测性 | ROS侧能区分累计overrun、连续超限、计数复位和通信失联 | 诊断接口/故障注入 | 未执行 |
| SERVO-160 | stop/restart后overrun状态与计数生命周期 | bIsOverrun、nOverruns初始化/复位行为确定，旧会话统计不污染新会话 | 多轮启停日志 | 未执行 |

### G. 本节来源记录（#1784–#1787）

| 编号 | 固定来源 | 用途 |
|---|---|---|
| #1784 | [ICube VAL3 start @ bd658e2](https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/val3/userapp/ros2_server/start.pgx) | l_nCtrlPeriod=0.004与taskCreateSync创建4 ms同步任务；monitor speed低于100%仅warning |
| #1785 | [ICube VAL3 controlTask @ bd658e2](https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/val3/userapp/ros2_server/controlTask.pgx) | bIsOverrun只日志、清标志、nOverruns递增；循环末尾delay(0)，无overrun专属STOP |
| #1786 | [ICube VAL3 database @ bd658e2](https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/val3/userapp/ros2_server/ros2_server.dtx) | bIsOverrun、nOverruns全局变量声明与初值 |
| #1787 | [Stäubli CS9 Real Time Val3/Fieldbus configuration TSS.000.014.04-A (2021), §4.2](https://bvdp.inetdoc.net/files/iut/staubliiut/doc/Real%20Time%20Val3-Fieldbus%20Synchronization%20TSS00001404A.pdf) | 同步任务周期、3000行执行上限、delay(0)让出、超周期取消下一周期及overrun bool语义 |


## 9.3.54 CS9系统任务、IO刷新与VAL3同步任务CPU预算（2026-11-08）

本节继续固定审查ICube上游 `bd658e2d266e315d2ee35f985fb352ea88306b79`，重点区分VAL3用户任务周期与CS9系统扫描/IO刷新调度。重要边界：Stäubli《CS9 Real Time Val3/Fieldbus configuration》TSS.000.014.04-A（2021）说明了系统任务调度机制，但当前ICube仓库未包含目标单元的 `usr/configs/cell.cfx`、UserIORefresh配置、IO模块清单或CS9运行时跟踪。因此不能推断目标设备实际使用默认cyclicRatio、jitter或noJitter模式，也不能把文档时序图当作本项目实测结果。

### A. CS9单扫描周期不是VAL3独占窗口

Stäubli文档§3.1–§3.2描述CS9每个CPU扫描周期的基本顺序：

1. Synchro system task：处理机器人轨迹及系统IO板刷新，包括CpuIO、DsiIO、FastIO、PowerSupplyIO、Rsi9IO、StarcIO。
2. IO Refresh task：刷新用户IO板，包括J206 EtherCAT master、J207/J208 Real Time Ethernet及Hilscher CIFX PCIe现场总线卡。
3. 用户VAL3同步任务。
4. 用户VAL3异步任务。

文档明确指出CS9单处理器一次只执行一个任务；用户同步VAL3任务会消耗较多CPU资源。系统任务与用户任务按上述扫描顺序竞争同一处理器时间。因此，`taskCreateSync(...,0.004,...)`表达的是任务调度周期请求，并不意味着每4ms都有完整4ms供该VAL3程序执行，也不意味着它能越过系统轨迹与IO刷新任务。

### B. 3000行限制不是CPU时间预算或WCET

§4.2规定每次同步VAL3任务调度最多执行3000条VAL3指令行；遇到不能立即完成的指令（例如运行时错误、等待信号、任务停止等）时，调度器会转向下一个任务。实践中使用`delay(0)`主动让出本次任务片段。该规则是每次同步任务序列的指令行数上限，不是“3000行必定在4ms内执行完”的时间保证，也不是CPU总预算百分比。

当前`controlTask.pgx`包含状态采样、序列号处理、消息编码、SIO UDP发送/接收、命令解码、延迟检查、运动控制调用、错误恢复和日志等路径。源码行数本身无法估算实际执行时间；SIO读写等指令也可能使当前同步任务片段提前让出。必须按不同命令模式、正常/异常路径和IO规模测量每轮执行时间及尾部延迟。

### C. User IO刷新周期比与Jitter模式是未决配置项

§3.3说明用户IO数量很大时，IO Refresh task可能无法在一个CPU scan内刷新全部IO；可通过`usr/configs/cell.cfx`中的`UserIORefresh/cyclicRatio`设置刷新周期比。默认值为1；设置为2表示IO刷新任务可用最多两个CPU scan完成一轮刷新。文档建议只在必要时增大该值，因为数值越大，VAL3程序与用户IO刷新的时间差越大。

§3.4描述两种刷新组织方式：

- 默认jitter模式：单独运行IO Refresh task。
- `noJitter`模式：不再单独运行IO Refresh task，用户IO在Synchro system task中刷新。若用户板刷新时间过长导致Synchro system task overrun，文档指出机器人会停止且需要重启。

noJitter下cyclicRatio仍有效；例如ratio=2时，用户IO在同步系统任务中隔一扫描周期刷新。该模式把用户IO刷新与系统同步任务耦合，不能简单理解为“抖动更低且没有代价”。本次未取得目标CS9的`cell.cfx`和IO配置，因此无法判断ICube部署使用哪种模式、ratio为何值、用户板有哪些或是否存在刷新周期缺口。

### D. 对本项目4ms控制路径的影响

1. `start.pgx`配置VAL3 controlTask周期0.004s，但本任务位于系统同步轨迹/系统IO和用户IO刷新之后；4ms不是本任务独占CPU预算。
2. 如果User IO Refresh采用cyclicRatio>1，VAL3控制任务可能每4ms执行，而部分用户IO的刷新周期更长。若未来把GPIO命令实现为现场总线输出，必须在协议和控制语义中区分“命令已被VAL3接受”“IO已写入VAL3变量”“物理IO模块已刷新”三个时刻。
3. 若采用noJitter，用户IO刷新过载的后果可能升级为同步系统任务overrun和机器人停止/重启；这与用户VAL3 controlTask自身的overrun标志不是同一层级、也不是同一故障处理路径。
4. 当前`controlTask.pgx`中的GPIO数字/模拟输出处理仍是TODO；因此现阶段不能声称ROS命令已经具备物理GPIO输出时序保证，也不能把尚未实现的GPIO路径纳入已验证的4ms控制预算。
5. Stäubli文档§4.1说明CS9单处理器通过任务序列模拟并发，异步任务的执行片段受优先级和系统空闲时间影响；网络通信、屏幕刷新和文件访问等低优先级系统工作会利用剩余CPU时间。不能将“有多个VAL3任务”解释为多核并行执行。
6. Stäubli文档§5.3.1给出的示例中，同步VAL3采集到的位置通过用户IO刷新任务在后续CPU scan才送到现场总线；4ms scan时示例延迟为4ms。该例证明IO采样与物理刷新之间可能存在一个周期级延迟，但不是ICube当前UDP状态通道的测量结果。

### E. 配置核验和工程整改

- 获取与机器人型号、CS9软件版本匹配的实际`cell.cfx`、IO模块/总线配置、CPU scan time、UserIORefresh cyclicRatio及jitter mode；保存配置文件哈希和控制器版本。
- 记录Synchro system task、IO Refresh task、VAL3同步任务及异步任务的实际执行时间线；同步记录系统CPU负载、VAL3任务状态、IO刷新耗时和overrun计数。
- 分别在ratio=1、目标配置ratio及最大IO负载下测量IO更新年龄、刷新周期、抖动和任务overrun；任何ratio/noJitter更改必须在隔离测试单元中按Stäubli流程验证，不直接对生产机器人试错。
- 对controlTask拆分测量updateState、序列化、SIO发送、SIO接收、解码、运动控制及错误恢复的时间预算；覆盖位置/速度控制、停止、首帧、拥塞和异常日志路径。
- 将“VAL3同步任务overrun”和“同步系统任务/IO刷新overrun”设计为不同诊断类别；后者可能影响机器人系统级运行状态，不可只通过nOverruns计数推断。
- 在GPIO输出实现前定义物理IO生效确认方式（反馈输入、现场总线周期计数或硬件时间戳），不要把软件变量赋值当作物理输出已刷新。

### F. 新增验证项（SERVO-161–SERVO-174，均未执行）

| ID | 验证场景 | 通过条件 | 证据 | 状态 |
|---|---|---|---|---|
| SERVO-161 | 获取目标CS9实际cell.cfx | 文件版本、哈希、UserIORefresh配置可追溯 | 原始配置/版本记录 | 未执行 |
| SERVO-162 | 核对目标CS9系统任务顺序 | 运行时轨迹符合Synchro system→IO Refresh→VAL3 sync→VAL3 async | CS9跟踪/厂商诊断 | 未执行 |
| SERVO-163 | 4ms任务CPU执行预算测量 | 在目标负载下得到controlTask各阶段耗时、最大值及剩余CPU预算 | 高分辨率跟踪 | 未执行 |
| SERVO-164 | 3000行同步任务调度上限行为 | 验证达到行数上限、遇等待/阻塞指令时的切换语义 | 隔离测试程序/跟踪 | 未执行 |
| SERVO-165 | cyclicRatio配置核验 | 实际配置值与用户IO完整刷新周期及延迟一致 | cell.cfx/IO跟踪 | 未执行 |
| SERVO-166 | jitter与noJitter模式识别 | 运行时刷新组织方式与配置一致，模式切换有记录 | 配置与周期跟踪 | 未执行 |
| SERVO-167 | noJitter用户IO过载保护 | 在安全隔离测试环境确认系统同步任务overrun、机器人停止及恢复要求 | 故障注入/控制器日志 | 未执行 |
| SERVO-168 | 用户IO采样到物理刷新延迟 | 测得VAL3写入、IO任务刷新、外部端子变化三个时刻的延迟分布 | 示波器/逻辑分析仪/总线跟踪 | 未执行 |
| SERVO-169 | 同周期多个VAL3同步任务排序 | 实际执行顺序与创建顺序规则一致，累计耗时不超周期 | 任务创建记录/跟踪 | 未执行 |
| SERVO-170 | SIO读写指令的任务让出行为 | 明确发送/接收调用对同步任务片段执行与下一任务调度的影响 | CS9任务跟踪/网络注入 | 未执行 |
| SERVO-171 | monitor speed与真实周期预算相关性 | 记录monitor speed、CPU负载、同步任务执行时间及overrun的关联 | 多工况运行日志 | 未执行 |
| SERVO-172 | CPU与IO联合压力测试 | 最大用户IO负载、UDP双向压力和VAL3计算负载下，周期/刷新延迟满足经批准的预算 | 压力测试报告 | 未执行 |
| SERVO-173 | 系统级与用户级overrun诊断区分 | 可区分同步系统任务overrun、IO Refresh问题与VAL3 controlTask overrun | 诊断记录/故障注入 | 未执行 |
| SERVO-174 | GPIO命令到物理IO反馈闭环 | 输出命令、总线刷新、端子变化及反馈输入的时序可追溯 | HIL/逻辑分析仪记录 | 未执行 |

### G. 本节来源记录（#1788–#1792）

| 编号 | 固定来源 | 用途 |
|---|---|---|
| #1788 | [ICube VAL3 start @ bd658e2](https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/val3/userapp/ros2_server/start.pgx) | 0.004s周期配置、monitor speed低于100%仅warning、任务创建路径 |
| #1789 | [ICube VAL3 project @ bd658e2](https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/val3/userapp/ros2_server/ros2_server.pjx) | 项目包含的用户VAL3程序清单；仓库未提供cell.cfx/UserIORefresh配置 |
| #1790 | [Stäubli CS9 Real Time Val3/Fieldbus configuration TSS.000.014.04-A (2021), §§3.1–3.3](https://bvdp.inetdoc.net/files/iut/staubliiut/doc/Real%20Time%20Val3-Fieldbus%20Synchronization%20TSS00001404A.pdf) | 系统同步任务、用户IO刷新任务、单CPU扫描顺序、cyclicRatio语义 |
| #1791 | [Stäubli CS9 Real Time Val3/Fieldbus configuration TSS.000.014.04-A (2021), §3.4](https://bvdp.inetdoc.net/files/iut/staubliiut/doc/Real%20Time%20Val3-Fieldbus%20Synchronization%20TSS00001404A.pdf) | jitter/noJitter模式及noJitter用户IO刷新过载后果 |
| #1792 | [Stäubli CS9 Real Time Val3/Fieldbus configuration TSS.000.014.04-A (2021), §§4.1–4.2、5.3.1](https://bvdp.inetdoc.net/files/iut/staubliiut/doc/Real%20Time%20Val3-Fieldbus%20Synchronization%20TSS00001404A.pdf) | 单处理器任务序列、同步任务3000行限制、delay(0)、IO刷新引入的周期延迟 |


## 9.3.55 VAL3同步任务中的SIO网络读写、错误折叠与4ms周期预算

### A. 固定审查基线与代码路径

- 上游仓库：ICube-Robotics/staubli_driver_ros2
- 固定提交：bd658e2d266e315d2ee35f985fb352ea88306b79
- 本节直接核对：Comm/resetControlSocket.pgx、Comm/readDataOnce.pgx、Comm/readData.pgx、Comm/sendData.pgx、controlTask.pgx、Control/updateJointPositionControl.pgx、start.pgx。

### B. SIO接收调用的实际控制流

1. resetControlSocket.pgx通过sioCtrl(x_UdpSocket, "timeout", -1)设置SIO超时，并在注释中明确称为“Non-blocking socket”；随后调用clearBuffer。这是项目的配置意图和源码证据，不等于已测得CS9上每次SIO调用的固定执行上界。
2. readDataOnce.pgx每次先将x_bNewData和x_bError清为false，再调用sioGet：
   - 返回值等于目标数组长度：标记收到完整帧；
   - 返回值大于0但长度不符：标记通信错误并返回；
   - 返回0或负值：没有进入任何错误分支，函数以“无新数据、无错误”返回。
3. readData.pgx每轮最多连续调用readDataOnce两次，两个调用之间没有显式等待或让出。第一次收到有效帧后，第二次若无新数据，则保留第一次的x_bNewData=true并退出；如果底层返回-1，第二次也会被当成“没有新数据”。若两次均返回0/-1，则上层只看到无新数据。
4. 因此，上一节关于SIO读取错误可能被折叠为“无新数据”的发现，在本节控制循环中有明确调用路径：底层负返回值不会通过l_bError上报，可能延迟暴露或完全丢失本次错误信息。不能把“没有新命令”与“读取成功但缓冲区为空”视为同一种已验证状态。
5. 两次调用使用同一个目标数据数组；若连续读取两帧，后一次可能覆盖前一次。该行为与接收窗口/最新帧策略相关，不能假设两帧都会逐条处理。

### C. SIO发送调用与超时边界

- sendData.pgx检查待发送数组非空，然后调用一次sioSet。只有返回字节数严格等于数组长度才认为成功；短写或负返回均置x_bError=true，没有循环续写剩余字节的逻辑。
- 这与VAL3 SIO手册关于sioSet返回实际写入字符数、可能少于请求长度的定义相吻合；本节不将“短写”推断为已发生的CS9网络故障。UDP datagram在目标控制器上是否允许按剩余片段继续写、是否会改变数据报边界，仍需SRS/CS9实测，不能照搬TCP字节流续写策略。
- resetControlSocket将timeout设置为-1，源码注释称non-blocking；据此可确认项目意图是不等待未来数据/不使用常规正超时等待。但不能仅凭该注释推断socket首次激活、内部复制、缓冲区处理、协议栈调度和错误返回在所有CS9版本上均具有确定且足够小的WCET。
- 前序§9.3.50已确认clearBuffer对Ethernet socket具有停用/关闭语义；因此socket生命周期与读写调用必须共同验证。启动、错误恢复后的首个sioGet/sioSet是否触发重新激活、其执行时间和失败语义，不可从普通已激活socket路径外推。

### D. SIO操作在4ms同步任务中的预算位置

start.pgx请求4ms同步任务；controlTask.pgx每次同步序列依次包含：

1. overrun标志检查与日志；
2. updateState采集机器人状态；
3. 序号更新和状态结构填充；
4. encodeRobotStateMsg序列化；
5. sendData/sioSet发送状态帧；
6. readData/readDataOnce/sioGet最多两次接收；
7. 命令帧解码、序号延迟和模式检查；
8. 位置/速度控制函数及运动API调用，或STOP/reset路径；
9. GPIO占位分支、错误恢复、日志和socket重置；
10. 最后执行delay(0)让出当前同步任务片段。

- 这些步骤位于同一VAL3同步任务控制路径；SIO读写不是独立的异步用户任务。即使timeout=-1意图避免等待数据，序列化、内存复制、socket系统调用、错误日志、运动API和CS9系统任务竞争仍会占用任务执行预算。
- delay(0)在控制循环尾部调用，不能缩短本轮之前已经执行的SIO/运动/日志路径，也不能作为每个网络阶段的超时保护。
- 状态发送失败后，controlTask先置l_bError，仍继续进入命令读取调用；后续模式选择会因错误转入STOP/ERROR处理。因此“发送失败仍读命令”不代表失败状态下会正常执行新运动命令，但会增加错误路径的本轮工作量。
- 当接收返回-1被折叠成无新数据时，控制循环可能继续使用上一条有效命令；源码中无新命令staleness分支仍为TODO。该点与§9.3.49、§9.3.52的命令新鲜度风险相互叠加。
- 4ms是任务调度周期目标，不是允许SIO调用独占的4ms窗口。CS9系统同步任务和用户IO刷新先于VAL3同步任务执行；CPU资源还受其他同步任务和系统任务影响。参见§9.3.54及Stäubli CS9实时配置文档§§3–4。

### E. 当前可下结论与不可下结论

静态代码可确认：
- SIO timeout被设置为-1，且注释明确表达non-blocking意图；
- 每轮最多连续调用两次sioGet；
- 0和负返回值在readDataOnce中均未置通信错误；
- sioSet必须一次返回完整帧长，否则报告发送错误；当前无重试/续写；
- 状态更新、SIO发送、SIO接收、命令处理、运动控制及错误日志都在同一同步控制任务路径；
- delay(0)只出现在本轮末尾。

不能据此宣称：
- CS9上的sioGet/sioSet实际执行时间恒定或有已知WCET；
- timeout=-1意味着所有内部操作绝不阻塞或永不触发运行时错误；
- 发生了4ms周期超限、丢包、socket死锁或机械运动异常；
- UDP部分写入可安全按TCP方式续写；
- 当前驱动具备完整的命令超时、网络故障诊断和恢复策略。

### F. 建议的可测量预算与整改

- 在隔离SRS/CS9单元中对控制循环各阶段记录开始/结束时间：状态采集、序列化、SIO发送、SIO接收（分别记录两次尝试）、解码、序号检查、运动API、日志、错误复位；同时记录总周期、最大值、P99/P99.9、overrun计数和任务状态。
- 分别测量socket已激活、首次调用/重新激活、无数据、单帧、连续两帧、错误返回、短写、缓冲区压力、网络断开和恢复场景；将发送与接收调用分别统计，不以单一“通信耗时”掩盖差异。
- 为sioGet返回值建立三态以上结果：有效完整帧、无数据、底层错误/异常长度；负返回不得默认为无数据。错误必须进入独立诊断计数和可观测故障状态。
- 对UDP固定帧协议，不应未经控制器手册和SRS验证就实现短写余量续传；应先确定sioSet在目标CS9 UDP socket上的数据报原子性/边界语义，再决定重试策略。
- 把本轮时间预算拆分为系统同步任务/IO刷新、VAL3控制任务、通信与运动处理、异步及系统后台任务；通过运行时跟踪确认尾部余量，不把3000行指令上限或4ms任务周期当作WCET证明。
- 将命令新鲜度改为真实时间deadline/watchdog，并在网络读取错误、无数据、旧命令、序号异常和socket重置后定义不同状态转移；避免用“未收到新帧”掩盖SIO错误。

### G. 新增验收任务（SERVO-175–SERVO-187）

| 编号 | 验收项 | 通过标准 | 验收证据 | 状态 |
|---|---|---|---|---|
| SERVO-175 | SIO timeout=-1运行语义 | 目标CS9/SRS确认无数据读取、首次socket激活和错误时的实际等待/返回行为 | SRS/CS9时间戳与任务跟踪 | 未执行 |
| SERVO-176 | sioGet返回值三态覆盖 | 0、-1、正数短读、完整帧均产生明确且不同的诊断结果 | VAL3测试记录/故障注入 | 未执行 |
| SERVO-177 | readData双次读取窗口 | 确认两次连续读取的缓冲区覆盖、帧顺序及队列行为 | 连续UDP帧注入与抓包 | 未执行 |
| SERVO-178 | 无数据与读取错误区分 | 底层错误不会被折叠为普通无新命令 | 错误注入和状态机日志 | 未执行 |
| SERVO-179 | sioSet完整写/短写行为 | 明确目标UDP socket上的返回字节数、超时和数据报边界 | CS9/SRS发送测试与抓包 | 未执行 |
| SERVO-180 | socket首次激活耗时 | 首次读写/clearBuffer后重激活的最大耗时及错误路径有记录 | CS9任务跟踪 | 未执行 |
| SERVO-181 | 4ms控制循环分阶段耗时 | 每阶段最大值、P99/P99.9及总预算有可复现测量 | 带时间戳的运行时报告 | 未执行 |
| SERVO-182 | 双次sioGet最坏路径 | 无数据、两帧连续到达、第二次错误等路径的总耗时满足批准预算 | 网络注入与周期报告 | 未执行 |
| SERVO-183 | SIO与运动API联合压力 | 网络读写、状态更新和movejSync压力下无未解释周期超限 | CS9联合压力报告 | 未执行 |
| SERVO-184 | 错误日志对周期的影响 | 高频错误/限流日志不会导致不可接受的同步任务超限 | 日志压力与任务跟踪 | 未执行 |
| SERVO-185 | 发送失败后控制状态门控 | 发送错误后读取/解码路径不会导致旧或新命令继续驱动运动 | SRS/HIL状态机测试 | 未执行 |
| SERVO-186 | 读取错误后的命令新鲜度 | 网络错误、无数据和旧命令分别触发经批准的deadline/watchdog策略 | 故障注入与命令年龄记录 | 未执行 |
| SERVO-187 | 4ms预算与CS9系统任务联合验收 | 纳入系统同步任务、IO刷新、VAL3同步任务及后台任务后仍满足批准的周期/抖动限值 | 目标CS9运行时验收报告 | 未执行 |

### H. 本节来源记录（#1793–#1797）

| 编号 | 固定来源 | 用途 |
|---|---|---|
| #1793 | [ICube readDataOnce.pgx @ bd658e2](https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/val3/userapp/ros2_server/Comm/readDataOnce.pgx) | sioGet返回值分支与0/负值未置错误 |
| #1794 | [ICube readData.pgx @ bd658e2](https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/val3/userapp/ros2_server/Comm/readData.pgx) | 每轮最多两次连续读取、缓冲区复用和返回标志 |
| #1795 | [ICube sendData.pgx @ bd658e2](https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/val3/userapp/ros2_server/Comm/sendData.pgx) | sioSet必须完整写入、无部分写重试 |
| #1796 | [ICube resetControlSocket/controlTask/start @ bd658e2](https://github.com/ICube-Robotics/staubli_driver_ros2/tree/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/val3/userapp/ros2_server) | timeout=-1配置、控制循环顺序、4ms同步任务与delay(0)位置 |
| #1797 | [Stäubli VAL3 Reference Manual D.280.935.01-G (2021)](https://fr.scribd.com/document/655664199/Doc-VAL3) | SIO读写返回值、socket等待/错误语义的手册交叉核对；目标CS9 UDP运行行为仍需验证 |


## 9.3.56 ROS 2 UDP最新消息快照、发送背压与命令年龄传播

### A. 固定审查基线

- 上游：ICube-Robotics/staubli_driver_ros2
- 固定提交：bd658e2d266e315d2ee35f985fb352ea88306b79
- 代码：real_time_socket_subscriber.hpp/.cpp、real_time_socket_interface.cpp、communication/udp_socket_impl.hpp、robot_driver.cpp/.hpp、staubli_hardware_interface.cpp。
- VAL3交叉核对：Comm/computeSequenceDelay.pgx、Comm/getNextSequenceNumber.pgx、Serialization/decodeRobotCommandMsg.pgx。

### B. ROS 2接收路径是最新值快照，不是逐条消息队列

1. UDP接收线程通过async_receive_from收取数据；每个完整消息反序列化成功后，写入单个RealtimeThreadSafeBox<MessageType>。后到的有效帧会替换快照中的前一帧，消费者未及时读取时，中间帧不会逐条排队等待处理。
2. read_message()从快照try_get最新消息，按header.sequence_number与上次读取序号计算lost_packages。序号差能显示消费者观察到的跳号，但不能单独证明这些帧在网络中丢失：也可能是内核接收队列积压后应用层只取到最新快照、接收线程/消费者调度不均或真实网络丢包。
3. RobotDriver::read_robot_state()收到lost_packages后，相关告警日志目前被注释；该函数继续做staleness检查。因而序号跳跃没有成为可见的运行告警/故障计数。
4. 当没有新帧时，read_message仍可把之前的msg返回，并根据其reception_timestamp计算time_since_received；只要未达到state_staleness_timeout_，RobotDriver::read_robot_state()就继续返回成功。硬件接口read()因此可能连续多个控制周期重复使用同一RobotState，而不是每周期都获得一条新状态帧。
5. 这并非天然错误：状态接口可允许消费者读取最近已知状态；但对闭环运动控制必须明确区分“有有效缓存状态”和“本周期收到了新状态”，并将消息年龄作为显式安全输入，而非只检查一个较宽松的过期阈值。

### C. 命令序号传播与时间年龄信息

- StaubliHardwareInterface::write()将RobotCommand.header.sequence_number设置为RobotDriver::get_current_message_sequence()；该函数返回last_valid_sequence_id_，而last_valid_sequence_id_在read_robot_state()成功时更新为最近有效RobotState的sequence_number。
- 因此ROS命令序号不是独立递增的命令发送计数器，而是引用最近一次被ROS侧接受的机器人状态帧序号。若ROS控制更新多次发生在同一状态帧之间，多个命令可能复用相同状态序号；若状态接收跳号，命令序号会直接跳到新的状态序号。
- VAL3端computeSequenceDelay计算“本地最近发送的状态序号 - 最近接收的命令序号”，并处理uint16回绕。该值更接近命令相对状态帧进度的滞后量，不是单调时钟测得的命令年龄；当ROS复用同一状态序号时，滞后量会随机器人端状态序号推进而增大。
- RobotCommand序列化内容包含controller_period，但没有独立命令生成时间戳/发送时间戳。controller_period描述控制周期，不足以表示命令在ROS线程、内核发送缓冲、网络、VAL3接收缓冲中已经等待多久。
- 因此当前协议不能在跨端直接计算真实命令年龄，也无法单靠sequence_delay严格替代deadline/watchdog。需要新增单调时钟域的时间戳或明确的相对deadline语义，并处理ROS主机与CS9时钟不同步问题；若不做时钟同步，应采用可验证的握手/年龄测量协议，而不是直接比较两个无关时钟值。

### D. UDP发送背压存在明确的返回值语义缺陷

1. UDPSocketImpl::send()使用send_to(..., MSG_DONTWAIT, err)，注释说明内核发送缓冲区满时立即返回would_block，并主动丢弃当前数据包。
2. would_block分支只记录WARN并保留TODO“增加丢包计数/阈值故障或异步发送”；函数在该分支后仍返回true。
3. RealTimeSocketInterface::send_message()只根据socket_->send(data_out_)的bool结果判断发送成功；RobotDriver::send_robot_command()和StaubliHardwareInterface::write()继续把true解释为成功。
4. 因此在send_to返回would_block的明确分支上，命令已被丢弃，但上层接口报告成功；这不是推测性的网络风险，而是固定源码可确认的错误返回语义。当前没有累计丢包数、连续丢包阈值或触发STOP/ERROR的策略。
5. 其它非would_block的socket错误会返回false并向上层传播；因此would_block反而成为“静默成功”路径。应将发送结果改为明确枚举（sent / would_block_dropped / fatal_error），或至少在丢包时返回false并由实时安全策略处理；同时记录可观测计数。不能为了重试而无界阻塞实时控制线程。
6. 发送路径还在实时调用线程执行序列化、日志和同步send_to；MSG_DONTWAIT只限制内核发送等待，不意味着整个C++函数、序列化和日志有确定WCET。高频WARN日志自身也需要节流或异步化评估。

### E. 接收线程和来源验证的相关边界

- receive thread的优先级/CPU affinity TODO尚未实现；线程通过io_service_.run()运行，接收回调反序列化并更新最新值快照。
- handle_data_received遇到error会记录错误，但仍调用reception_callback_，随后继续安排下一次接收；需验证错误时bytes_transferred和缓冲区内容是否会导致重复错误日志/无效回调。
- sender_endpoint校验仍是TODO。注释明确指出未验证来源地址可能允许非预期主机注入状态帧并扰乱序号追踪。目标部署应限制控制网络访问，并验证源IP/端口；不能仅依赖UDP远端endpoint配置推断接收端已过滤发送者。
- 现有单元测试通过固定间隔发送和loopback收发验证基本通信、staleness和序号跳号；没有覆盖高速突发发送、消费者慢读、send buffer饱和、would_block后返回值、连续丢包故障门控、非预期发送源及端到端命令年龄。

### F. 整改建议与可验收机制

1. **发送返回值闭环：** would_block必须明确表示“本帧未发送”；增加total_tx、would_block_drop、fatal_error、consecutive_drop计数；按经风险分析批准的阈值进入受控故障状态。不要在控制线程中无限重试。
2. **最新状态与新鲜状态分离：** read_message保留latest snapshot语义，但向硬件接口明确暴露new_message、sequence gap和age；在控制模式下定义允许重复读取的最大年龄与最大连续重复周期数。
3. **命令身份独立化：** 为RobotCommand分配独立单调序号，不复用RobotState序号；同时保留state_reference_sequence用于关联状态样本。序号回绕、重复、乱序、重启复位均需有协议定义。
4. **命令deadline/年龄：** 增加发送时间/相对deadline字段，或定义跨时钟安全的年龄测量方式；VAL3在应用运动命令前检查命令新鲜度。超过期限后进入经安全分析批准的STOP/ERROR状态，不继续使用最后一条旧命令。
5. **诊断：** 将sequence gap、接收年龄、无新消息周期数、would_block丢包、fatal send error、receive error、unexpected sender分别计数并可查询；告警与故障门控分级，不把它们混为一个lost packet数。
6. **网络安全：** 校验发送源地址/端口，配置机器人控制专用网络/VLAN/ACL；对异常源、重复帧和序号回退执行拒绝与审计。
7. **压力验证：** 注入高于250Hz的命令突发、消费者暂停/慢读、内核发送缓冲饱和、网络延迟/乱序/丢包/断连恢复；对比ROS发送序号、抓包、VAL3接收序号和实际执行序号，证明每种异常路径的诊断及故障门控。

### G. 新增验收任务（SERVO-188–SERVO-202）

| 编号 | 验收项 | 通过标准 | 验收证据 | 状态 |
|---|---|---|---|---|
| SERVO-188 | RealtimeThreadSafeBox突发覆盖 | 明确消费者慢读时覆盖行为和可观测跳号 | 突发发送/慢读测试 | 未执行 |
| SERVO-189 | ROS状态重复读取年龄 | 无新帧时age单调增长，控制模式按批准阈值响应 | 硬件接口单测与时间记录 | 未执行 |
| SERVO-190 | sequence gap诊断 | lost_packages可见、可累计、可导出，不仅存在于临时status | 单测/诊断接口 | 未执行 |
| SERVO-191 | would_block返回值 | 模拟发送缓冲满时send_message与write不能报告成功发送 | socket故障注入/单测 | 未执行 |
| SERVO-192 | 发送丢包计数和门控 | 连续/窗口丢包达到批准阈值后进入定义的受控状态 | 压力测试和状态机日志 | 未执行 |
| SERVO-193 | 250Hz相位偏差与突发 | 评估ROS 250Hz与VAL3 4ms不同相位下的命令覆盖/重复率 | 双端时序记录 | 未执行 |
| SERVO-194 | 命令序号独立性 | 命令序号独立递增，状态引用序号单独表达 | 协议测试/VAL3互操作 | 未执行 |
| SERVO-195 | 序号回绕/重启恢复 | 0xffff回绕、进程重启、控制器重启后不误判旧帧 | 边界单测/HIL | 未执行 |
| SERVO-196 | 端到端命令年龄 | 可测量生成、发送、接收、应用各阶段年龄并验证deadline | 同步时钟或相对时间协议测试 | 未执行 |
| SERVO-197 | 旧命令禁止继续执行 | 超deadline时VAL3不再沿用旧运动命令，进入批准的安全状态 | 故障注入/HIL | 未执行 |
| SERVO-198 | UDP接收错误恢复 | 错误回调不会错误更新快照，接收循环恢复可诊断 | 错误注入/线程跟踪 | 未执行 |
| SERVO-199 | UDP发送源身份校验 | 非允许源IP/端口的数据帧被拒绝且计数 | 多主机注入/抓包 | 未执行 |
| SERVO-200 | 实时线程优先级与CPU亲和性 | 线程调度配置有依据，压力下接收延迟分布可复现 | OS调度跟踪 | 未执行 |
| SERVO-201 | 高频日志对实时性的影响 | 丢包/错误洪泛时日志不会造成控制线程预算失控 | 日志压力与周期跟踪 | 未执行 |
| SERVO-202 | 端到端网络故障矩阵 | 丢包、乱序、重复、突发、慢读、背压、断连恢复均有确定诊断和控制状态 | ROS/网络/CS9联合验收报告 | 未执行 |

### H. 本节来源记录（#1798–#1803）

| 编号 | 固定来源 | 用途 |
|---|---|---|
| #1798 | [ICube real_time_socket_subscriber.cpp @ bd658e2](https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/src/real_time_socket_subscriber.cpp) | 单最新消息快照、reception timestamp、序号差和staleness计算 |
| #1799 | [ICube udp_socket_impl.hpp @ bd658e2](https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/src/communication/udp_socket_impl.hpp) | MSG_DONTWAIT、would_block丢包却返回true、无丢包计数、sender校验TODO |
| #1800 | [ICube robot_driver.cpp @ bd658e2](https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/src/robot_driver.cpp) | lost_packages告警注释、staleness检查和最近有效状态序号更新 |
| #1801 | [ICube staubli_hardware_interface.cpp @ bd658e2](https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/src/staubli_hardware_interface.cpp) | write将最近有效状态序号写入命令序号、controller_period字段 |
| #1802 | [ICube VAL3 computeSequenceDelay/getNextSequenceNumber @ bd658e2](https://github.com/ICube-Robotics/staubli_driver_ros2/tree/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/val3/userapp/ros2_server/Comm) | VAL3状态/命令序号差和uint16回绕 |
| #1803 | [ICube test_rt_socket_interface.cpp @ bd658e2](https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/test/unit_tests/communication/test_rt_socket_interface.cpp) | 现有测试覆盖staleness/序号跳号，但未覆盖慢读/突发/背压/丢包门控 |


## 9.3.57 ROS 2状态新鲜度计时的时钟源、时间跳变与超时语义

### A. 固定审查基线

- 上游仓库：ICube-Robotics/staubli_driver_ros2
- 固定提交：`bd658e2d266e315d2ee35f985fb352ea88306b79`
- 重点文件：`real_time_socket_subscriber.cpp/.hpp`、`robot_driver.cpp`、`staubli_hardware_interface.cpp`。
- ROS发行版基线：ROS 2 Jazzy；时钟API以Jazzy `rclcpp::Clock` 文档为准。

### B. 接收时间戳与年龄计算使用默认System Time

1. `RealTimeSocketSubscriber::update_message()`在UDP接收线程成功反序列化后，执行`msg.reception_timestamp = rclcpp::Clock().now()`。
2. `read_message()`再次构造默认`rclcpp::Clock()`并计算`now() - msg.reception_timestamp`；Jazzy API明确默认构造参数为`RCL_SYSTEM_TIME`。因此这不是单调时钟计时，而是系统墙钟时间差。
3. `RobotDriver::read_robot_state()`将该差值与`state_staleness_timeout_`比较；达到阈值才拒绝状态。ROS硬件`read()`进一步把失败映射为`hardware_interface::return_type::ERROR`。
4. 当前接收和读取两侧使用相同默认时钟类型，未发现时钟类型不匹配导致的比较异常；问题在于该时钟可受系统时间校准/手动调整影响，不能提供严格单调的经过时间。
5. 若系统墙钟向后跳，计算出的消息年龄可能变小甚至为负，`age >= timeout`在更长时间内不成立，旧状态可能被继续接受；若墙钟向前跳，则可能提前判定状态过期并触发硬件ERROR。这是由计时实现推导出的风险路径，不代表已经在目标机发生。
6. `RobotDriver::connect()`的连接超时循环同样使用默认`rclcpp::Clock().now()`与开始时间作差，因此连接超时也受墙钟跳变影响；其等待间隔另由`rclcpp::sleep_for`执行，不能据此认为超时计时已改用steady clock。

### C. 与ROS时间、仿真时间和控制周期的边界

- 当前代码直接构造独立的`rclcpp::Clock()`，而非从Node获取已绑定TimeSource的`get_clock()`；Jazzy文档指出默认类型是System Time。不能因为系统启用了`use_sim_time`就假定这些独立Clock自动跟随`/clock`。
- ROS 2时钟类型语义区分：`RCL_SYSTEM_TIME`对应系统时钟，`RCL_STEADY_TIME`为单调递增时钟，`RCL_ROS_TIME`可受ROS时间源影响。超时、消息年龄、watchdog和性能预算应选用明确且一致的单调时间基准；仿真/rosbag时间则应作为独立语义处理，不能混用。
- 此处的`reception_timestamp`是本机接收时刻，不是控制器生成时间，也不是跨网络端到端命令年龄。改为steady clock只能可靠计算本机接收后的驻留时间，不能替代§9.3.56提出的跨端命令生成/接收/应用年龄协议。
- `StaubliHardwareInterface::write()`收到的`period`被换算成毫秒写入`controller_period`；VAL3消费与否、周期偏差和端到端命令deadline仍按§9.3.32、§9.3.56相关验收项处理，不在本节重复推断。

### D. 整改建议

1. 为接收消息附加本机`std::chrono::steady_clock::time_point`或明确标注为`RCL_STEADY_TIME`的接收时间；在读取侧使用同一时钟域计算age。优先通过可注入时钟接口实现，避免每次临时构造时钟对象。
2. 对连接超时、状态/诊断staleness、重连冷却和本机watchdog统一使用steady clock；墙钟仅用于日志展示和可追溯的UTC事件时间。
3. 若需要仿真时间，应显式区分ROS时间与steady elapsed time：仿真暂停/回拨不得意外使真实通信超时无限延长，也不得把仿真时间戳直接与steady time相减。
4. 定义负年龄处理策略。采用单调时钟后仍应检测异常时间戳、未初始化值和时钟实例不一致；不应把负年龄默认当作“新鲜”。
5. 连接超时、状态新鲜度和诊断新鲜度应各自配置阈值，并记录当前时钟类型、年龄、阈值、重复帧周期数和拒绝原因。
6. 此项只提出驱动软件计时整改，不替代VAL3命令deadline、CS9独立安全链或机械停止确认；任何故障门控策略须经风险分析与目标控制器验证。

### E. 新增验收任务（SERVO-203–SERVO-212）

| 编号 | 验收项 | 通过标准 | 验收证据 | 状态 |
|---|---|---|---|---|
| SERVO-203 | 接收时间戳时钟类型 | 明确记录接收时间使用的clock type，并与读取侧一致 | 单测/诊断输出 | 未执行 |
| SERVO-204 | 墙钟向后跳变 | 状态age不因系统时间回拨而变小或负值 | 可控时钟注入测试 | 未执行 |
| SERVO-205 | 墙钟向前跳变 | 墙钟校准不导致状态被误判过期 | 可控时钟注入测试 | 未执行 |
| SERVO-206 | steady-clock年龄单调性 | 无新帧时age持续单调增加，跨线程读写安全 | 单测/压力测试 | 未执行 |
| SERVO-207 | 连接超时单调性 | connect timeout不受墙钟前跳/回拨影响 | 假时钟/超时测试 | 未执行 |
| SERVO-208 | ROS use_sim_time隔离 | /clock暂停、回拨、快进不会破坏真实通信watchdog | 仿真时钟集成测试 | 未执行 |
| SERVO-209 | 负年龄与无效时间戳 | 未初始化、异常或不一致时间戳被显式拒绝并诊断 | 边界单测 | 未执行 |
| SERVO-210 | 重复帧与消息年龄 | 相同序号重复读取时age仍按steady time增长，不重置接收时刻 | 单测/突发测试 | 未执行 |
| SERVO-211 | staleness到硬件ERROR传播 | 达到配置阈值时read返回ERROR，故障恢复和重新授权符合定义 | ros2_control集成测试 | 未执行 |
| SERVO-212 | 时间跳变故障矩阵 | 前跳、回拨、NTP校准、仿真暂停/回拨均有确定行为 | ROS集成测试报告 | 未执行 |

### F. 本节来源记录（#1804–#1807）

| 编号 | 固定来源 | 用途 |
|---|---|---|
| #1804 | [ICube real_time_socket_subscriber.cpp @ bd658e2](https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/src/real_time_socket_subscriber.cpp) | 接收线程使用默认`rclcpp::Clock().now()`记录本机接收时间；读取时再次使用默认Clock计算age |
| #1805 | [ICube robot_driver.cpp @ bd658e2](https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/src/robot_driver.cpp) | connect timeout与state staleness均依赖默认Clock时间差 |
| #1806 | [ICube real_time_socket_subscriber.hpp @ bd658e2](https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/include/staubli_robot_driver/real_time_socket_subscriber.hpp) | MessageStatus仅保存Duration年龄，接口未显式表达时钟域 |
| #1807 | [ROS 2 Jazzy rclcpp::Clock API](https://api.nav2.org/jazzy/html/classrclcpp_1_1Clock.html) | 默认构造参数为RCL_SYSTEM_TIME；与RCL_STEADY_TIME单调时钟语义区分 |



## 9.3.58 RobotDriver::connect 首帧就绪等待与诊断通道旁路

### A. 固定审查基线

- 上游：`ICube-Robotics/staubli_driver_ros2`
- 固定提交：`bd658e2d266e315d2ee35f985fb352ea88306b79`
- 文件：`staubli_robot_driver/src/robot_driver.cpp`、`staubli_robot_driver/src/staubli_hardware_interface.cpp`
- 重点函数：`RobotDriver::connect(const NetworkConfig&, int timeout_ms)`、`read_robot_state()`、`read_diagnostic_data()`。

### B. 首帧等待循环存在的控制流问题

1. connect先检查control_interface与diagnostics_subscriber的`is_ready()`，随后进入“Wait for the first valid messages”循环。
2. 循环条件为`rclcpp::Clock().now() - start_connect_time < timeout`。循环体读取一次机器人状态，随后执行`rclcpp::sleep_for(500ms)`。
3. 即使`cmd_interface_ready`已经为true，循环也没有`break`或成功退出条件；因此成功获得首帧后仍持续等待，直至超时条件不成立。默认硬件接口传入5000ms，正常连接路径可能额外等待接近整个timeout窗口，而不是首帧到达即完成。
4. 若timeout_ms小于500ms，循环体仍会完整执行一次500ms sleep，连接等待实际时长可能超过请求timeout；一般情况下，固定500ms sleep也会造成最多一个sleep周期量级的超时超调，具体受调度和Clock影响。
5. 循环终止后仅检查最后一次循环留下的`cmd_interface_ready`。若状态曾有效但最后一次检查因状态过期/读取失败变为false，connect会失败；反之，若最终一次读成功则成功。该语义把“曾经收到有效首帧”错误地实现为“循环退出前最后一次采样必须有效”。
6. 当前`rclcpp::sleep_for(500ms)`是固定轮询等待；没有基于首帧到达的事件通知，也没有将剩余timeout作为sleep上限。

### C. 诊断通道就绪检查被旁路

1. 同一循环中明确保留TODO：`implement diagnostic data reading once available`。
2. `diag_interface_ready`被直接赋值为`true`，实际的`read_diagnostic_data(diagnostic_data_msg)`调用被注释。
3. 因此连接成功条件`cmd_interface_ready && diag_interface_ready`中的诊断项恒为true；此前is_ready()只能证明订阅器/socket层就绪，不能证明已收到有效诊断帧、诊断帧新鲜或诊断内容有效。
4. 不能据此宣称驱动已经验证诊断通道端到端可用。当前代码把诊断首帧验证明确留作TODO。

### D. 影响与风险边界

- 可直接确认：首帧状态读取成功不会提前结束等待循环；诊断有效性在connect首帧等待阶段被硬编码为true。
- 可推导风险：启动时间被无谓延长；timeout边界被500ms sleep粒度超调；状态短暂有效后在退出采样点过期会导致连接失败；诊断UDP通道虽已创建并检查subscriber ready，但没有端到端诊断首帧门槛。
- 尚不能确认：目标现场实际连接延迟、首帧丢失概率、诊断通道是否持续可用，以及上层生命周期管理是否对该延迟有额外容忍。
- 此问题不等同于机器人安全停止失效；不得将connect失败或连接延迟直接描述为运动中故障。

### E. 整改建议

1. 将连接等待改为明确状态机：控制状态首帧有效即锁存`control_state_seen=true`；若产品要求诊断首帧，则诊断有效也独立锁存，两个必需条件满足后立即退出。
2. 诊断首帧是否为连接硬门槛必须由产品需求/安全分析确定；若不是硬门槛，应明确标记为degraded/diagnostics unavailable，而不是伪造ready=true。
3. 用条件变量/事件通知或有界短周期等待代替固定500ms轮询；等待时长必须受剩余deadline约束，且不得因最后一次采样覆盖此前成功状态。
4. 连接超时统一使用steady clock deadline；每次等待按`min(poll_interval, remaining)`限时，避免sleep越过deadline。
5. 增加连接阶段结构化诊断：socket连接、subscriber启动、首个有效控制帧、首个有效诊断帧、协议版本校验分别记录耗时和失败原因。
6. 修复后必须测试：首帧立即到达、延迟到达、控制帧缺失、诊断帧缺失、首帧后中断、timeout<500ms、墙钟前跳/回拨、disconnect并发取消等待。

### F. 新增验收任务（SERVO-213–SERVO-222）

| 编号 | 验收项 | 通过标准 | 验收证据 | 状态 |
|---|---|---|---|---|
| SERVO-213 | 控制首帧成功即退出 | 有效控制首帧到达后不再等待完整timeout | 单测/集成测试 | 未执行 |
| SERVO-214 | 首帧状态锁存 | 曾有效的首帧不会被后续一次采样失败覆盖为“从未就绪” | 状态机单测 | 未执行 |
| SERVO-215 | 诊断首帧门槛 | 诊断是否必需由配置/需求决定，不得硬编码ready=true | 需求追踪与集成测试 | 未执行 |
| SERVO-216 | 诊断通道真实读取 | 若诊断为必需，首个有效且新鲜诊断帧才置ready | UDP集成测试 | 未执行 |
| SERVO-217 | timeout小于轮询间隔 | timeout=1/50/100/499ms时不因固定sleep产生500ms等待 | 假时钟/单测 | 未执行 |
| SERVO-218 | timeout deadline边界 | 等待不超过deadline加明确调度容差 | 单测/时间测量 | 未执行 |
| SERVO-219 | 控制帧缺失 | 到期返回失败并明确指出控制首帧缺失 | 故障注入 | 未执行 |
| SERVO-220 | 诊断帧缺失 | 按已定义策略失败或进入明确降级状态，不伪报ready | 故障注入 | 未执行 |
| SERVO-221 | 首帧后中断 | 首帧有效后连接判定和后续staleness策略分离 | 集成测试 | 未执行 |
| SERVO-222 | disconnect取消等待 | 连接等待期间disconnect/生命周期取消可及时退出且资源释放完整 | 并发/生命周期测试 | 未执行 |

### G. 本节来源记录（#1808–#1811）

| 编号 | 固定来源 | 用途 |
|---|---|---|
| #1808 | [ICube robot_driver.cpp @ bd658e2](https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/src/robot_driver.cpp) | connect首帧等待循环、500ms sleep、没有成功break、诊断ready硬编码 |
| #1809 | [ICube staubli_hardware_interface.cpp @ bd658e2](https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/src/staubli_hardware_interface.cpp) | on_init调用connect并传入5000ms timeout |
| #1810 | [ROS 2 design: Clock and Time](https://github.com/ros2/design/blob/gh-pages/articles/130_ros_time.md) | Steady Time适用于硬件超时；System/ROS time与steady time用途不同 |
| #1811 | [ICube RobotDriver API/header](https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/include/staubli_robot_driver/robot_driver.hpp) | connect timeout及控制/诊断状态接口定义的交叉核对入口 |


## 9.3.59 连接、断开与重连线程生命周期、资源释放及并发竞态

**审查基线：** ICube-Robotics/staubli_driver_ros2 固定提交 `bd658e2d266e315d2ee35f985fb352ea88306b79`。本节为静态源码控制流审查；没有执行并发压力测试、线程消毒器、网络故障注入或CS9实机测试。

### A. 源码事实

1. `RobotDriver::connect()`按控制socket连接、创建控制接口、诊断socket连接、创建诊断subscriber的顺序建立资源。诊断socket连接失败等后续显式错误路径会调用`disconnect()`；但控制socket首次连接失败直接返回，且subscriber构造/线程创建抛出异常的路径没有在connect层统一捕获并回滚。普通的`make_shared`分配失败也不在该函数内转化为受控连接失败。
2. `RealTimeSocketSubscriber::init_communication()`将捕获裸`this`的lambda注册给socket接收线程。subscriber析构函数直接调用`socket_->stop_receive_thread()`；当前实现依赖析构时同步join，保证正常完成的回调不再访问subscriber后才释放对象。
3. `UDPSocketImpl::start_receive_thread()`先写入`reception_callback_`，调用`io_service_.reset()`、启动一次`async_receive_from`，再把`receiving_`置true并创建线程执行`io_service_.run()`。线程状态标志为atomic，但`receive_thread_`、`reception_callback_`、Asio socket、接收buffer及endpoint没有共同的状态互斥锁。
4. `stop_receive_thread()`只调用`io_service_.stop()`、`receive_thread_.join()`，随后把`receiving_`置false；该函数没有显式调用socket.cancel，也没有在停止阶段排空/消费取消完成回调。Boost.Asio文档说明`io_context::stop()`使run尽快返回并放弃未完成操作的分发；这不等同于关闭socket或完成socket级取消。
5. `disconnect()`先reset控制interface和诊断subscriber（析构间接停止接收线程），然后在socket仍connected时调用disconnect/close，最后reset_data。UDP实现的`disconnect()`若检测到receiving仍为true，会再次调用stop_receive_thread；随后close socket。该路径正常顺序上先join再close，但取消/关闭的完成处理器如何跨下一次`io_service_.reset()`处理，没有显式隔离连接代际。
6. `handle_data_received(error, bytes_transferred)`在error非零时只记录日志，仍然调用当前`reception_callback_`，并在`is_receiving()`为true时再次提交接收操作。没有对`operation_aborted`、持续性socket错误、零字节或关闭状态建立不同分支。
7. `RobotDriver`的`control_interface_`、`diagnostics_subscriber_`等shared_ptr成员在connect/disconnect中直接赋值/reset；read/write/is_connected路径也直接读取这些成员。头文件没有为这些成员声明生命周期互斥锁，类中也没有连接状态机/操作代际字段。atomic socket标志不保护同一个shared_ptr成员的并发读写。
8. `StaubliHardwareInterface`在`on_cleanup()`和析构函数调用disconnect；`on_shutdown()`只在`is_connected()`为true时尝试STOP并disconnect；`on_activate()`仅设置控制模式为STOP。本实现没有显式覆盖`on_deactivate()`。因此代码没有在deactivate回调中明确停止/释放通信资源；是否由上层生命周期顺序先停止控制循环，必须在ros2_control集成层确认，不能从此文件推断。
9. `RobotDriver::~RobotDriver()`为空函数体，底层socket析构函数会在仍connected时调用disconnect；硬件接口析构函数另行调用RobotDriver::disconnect。顺序析构时多次清理大体依赖各层的状态判断实现幂等；并发调用disconnect则没有同等保证。

### B. 风险分析（静态推导，尚非已复现故障）

- **高优先级：控制循环与disconnect并发访问成员指针。** 若read/write/is_connected与disconnect/connect并发，可能对同一shared_ptr成员发生无同步读写，形成C++数据竞争；即使底层socket的connected/receiving是atomic，也不能保证接口对象不会在调用期间被reset和析构。风险成立的前提是调用方没有在生命周期外部串行化这些API；当前RobotDriver本身没有建立该契约或防护。
- **高优先级：并发stop/disconnect/start不具备完整串行化。** atomic布尔值只保护标志，不保护对同一个std::thread执行多次join、callback替换、io_service reset/stop及socket close/open的复合操作。两个线程同时stop，或stop与start/connect交叠，可能造成线程对象并发操作、状态错配或未定义行为。
- **中高优先级：socket错误处理可能形成重试风暴。** 持续性接收错误时，handler仍调用业务callback并重新提交async_receive_from；如果错误立即完成且receiving仍为true，可能反复触发错误回调并消耗CPU/日志资源。是否出现紧密循环取决于具体错误和Asio平台行为，需故障注入测量。
- **中高优先级：停止/关闭/重连之间缺少连接代际隔离。** stop只停止io_context事件循环，disconnect随后close socket，下一次start会reset同一io_service并覆盖callback。旧操作的取消完成、重新启动后处理器的行为需要在目标Boost版本上验证；当前代码没有generation token或显式取消完成屏障，不能证明旧代回调绝不会污染新代接收状态。
- **中优先级：异常安全回滚不完整。** subscriber构造或线程创建异常可能在诊断socket已连接后逃出connect；thread创建异常还可能发生在receiving置true之后。需以RAII和统一rollback保证所有部分初始化路径都回到可重试状态。
- **中优先级：deactivate资源策略不明确。** 当前硬件接口没有显式on_deactivate；若产品期望deactivate即停收/断链，现实现缺少对应逻辑。若设计选择保持链路，仅停止控制命令，则必须以需求明确，并验证状态数据不会在inactive阶段被错误使用。
- **安全边界：** 上述分析不证明机器人已发生意外运动、STOP失效或真实现场线程崩溃；也不证明ROS 2生命周期管理器必然与read/write并发。它指出类内缺少并发安全契约，需由调用方串行化证据或代码内同步机制证明。

### C. 整改建议

1. 为RobotDriver建立单一生命周期状态机（Disconnected/Connecting/Connected/Disconnecting/Failed），用互斥锁或专用strand串行化connect/disconnect及接口对象替换；不要只依赖atomic标志。
2. 读写路径使用受控的对象生命周期策略：在锁内取得稳定的局部shared_ptr快照，或让所有操作通过同一strand/生命周期门闩；disconnect先禁止新操作，再等待在途操作退出，最后销毁接口和socket。
3. 将UDP接收线程的start/stop/close封装为可重复且线程安全的状态转换；禁止两个线程同时join同一个thread对象；对self-join、未join的joinable线程、线程创建失败分别处理。
4. 停止时先禁止重新arm，再cancel/close异步socket操作，等待取消完成处理器退出并确认没有未完成操作；重连时创建新io_context/socket或使用generation token隔离旧回调。明确处理`operation_aborted`，禁止错误回调继续重启接收。
5. 接收handler遇到非零error时按错误类别处理；只有成功接收且长度/来源/协议有效时才调用业务回调。对可恢复错误采用有界退避、计数和状态转移，禁止无界立即重试。
6. connect使用scope guard/RAII分阶段登记资源，所有失败和异常统一rollback；线程启动成功后再发布Connected状态，且失败路径保证socket、subscriber、thread全部回到可重试基线。
7. 明确on_deactivate、on_cleanup、on_shutdown、on_error各自的资源语义；deactivate是否断链由产品需求决定，但必须先停命令生产者、等待控制循环退出，再释放或保留接收链路。
8. 对外提供连接代际ID、线程退出状态、未完成异步操作数、最后错误码、连接/断开耗时和资源计数，支持长期重连观测。

### D. 新增验收任务（SERVO-223–SERVO-232）

| 编号 | 验收项 | 通过标准 | 验收证据 | 状态 |
|---|---|---|---|---|
| SERVO-223 | read/write与disconnect并发 | ThreadSanitizer无shared_ptr/对象生命周期数据竞争；断开后无悬空访问 | TSAN压力测试 | 未执行 |
| SERVO-224 | connect/disconnect并发串行化 | 多线程重复调用只产生合法状态迁移，无重复join/双重close | 并发单测 | 未执行 |
| SERVO-225 | stop/cancel/close顺序 | 所有异步操作均完成取消并退出，join返回后无旧handler访问旧subscriber | Asio handler跟踪/单测 | 未执行 |
| SERVO-226 | 错误回调停止重试 | operation_aborted不调用业务回调；持续错误触发有界退避/故障状态 | 网络故障注入 | 未执行 |
| SERVO-227 | stop与start交叠 | 同一thread对象不被并发join/重建；状态机无非法跃迁 | TSAN/并发单测 | 未执行 |
| SERVO-228 | 断开后立即重连 | 多轮重连无旧代回调、双重接收、端口占用或残留线程 | 1000轮循环测试 | 未执行 |
| SERVO-229 | 连接中途异常回滚 | socket已连接后subscriber/线程构造失败，所有资源回到Disconnected | 故障注入/异常单测 | 未执行 |
| SERVO-230 | deactivate语义 | deactivate后命令生产者停止；资源保留/释放行为与需求一致且可重复activate | ros2_control生命周期集成测试 | 未执行 |
| SERVO-231 | shutdown/error清理 | STOP发送失败、socket断开、重复shutdown等路径有明确结果和资源状态 | 生命周期故障注入 | 未执行 |
| SERVO-232 | 长期连接抖动恢复 | 断网/恢复、CS9重启、ROS节点重启后无资源泄漏、线程泄漏或旧命令复用 | HIL/长稳测试 | 未执行 |

### E. 本节来源记录（#1812–#1816）

| 编号 | 固定来源 | 用途 |
|---|---|---|
| #1812 | [ICube robot_driver.cpp @ bd658e2](https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/src/robot_driver.cpp) | connect/disconnect资源顺序、shared_ptr reset、空析构函数 |
| #1813 | [ICube real_time_socket_subscriber.cpp @ bd658e2](https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/src/real_time_socket_subscriber.cpp) | 裸this回调、subscriber析构stop、接收回调入口 |
| #1814 | [ICube udp_socket_impl.hpp @ bd658e2](https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/src/communication/udp_socket_impl.hpp) | io_service stop/reset、thread join、socket close、错误回调重arm |
| #1815 | [ICube staubli_hardware_interface.cpp @ bd658e2](https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/src/staubli_hardware_interface.cpp) | on_activate/on_cleanup/on_shutdown/on_error及未显式覆盖on_deactivate |
| #1816 | [Boost.Asio io_context reference](https://www.boost.org/doc/libs/1_84_0/doc/html/boost_asio/reference/io_context.html) | stop使run退出并放弃未完成操作的分发；stop不等同于socket close/cancel |


## 9.3.60 控制状态与诊断状态的一致性、有效性及时间关联

**审查基线：** ICube-Robotics/staubli_driver_ros2 固定提交 `bd658e2d266e315d2ee35f985fb352ea88306b79`。本节为静态源码审查；未执行双通道抓包、协议仿真、网络延迟/乱序注入或CS9实机验证。

### A. 源码事实

1. `RobotDriver::connect()`同时建立控制与诊断UDP socket，并启动各自subscriber；但首帧等待阶段只调用`read_robot_state()`。诊断读取仍是TODO，`diag_interface_ready`被直接赋值true，因此连接成功条件实际上只证明控制状态读取成功，并不证明诊断通道收到过有效数据。
2. 连接后的协议版本检查只针对`current_robot_state_.header.protocol_version`。控制器类型CS9检查代码被整段注释；固件版本仅从`current_diagnostic_data_.robot_firmware_version`打印，且没有先调用`read_diagnostic_data()`来填充和验证该缓存，也没有实现VAL3固件版本兼容性检查（保留TODO）。因此日志中的固件字段不能视为已验证的诊断信息，CS9兼容性也没有由当前连接路径证明。
3. `read_diagnostic_data()`实现了诊断消息类型校验、接收驻留时间检查和丢包计数，但本固定提交中connect等待处的唯一调用被注释；硬件接口的周期性`read()`只调用`read_robot_state()`，`write()`也不读取诊断数据。由此可见，诊断数据读取API存在，但没有接入正常硬件读写周期或连接成功门槛。
4. 控制和诊断分别使用不同的`RealTimeSocketSubscriber<MessageType>`实例、不同的message buffer、各自的`last_read_sequence_number_`和`first_read_`状态。每个通道各自计算丢包与接收年龄；代码没有跨通道sequence比较、共同采样周期ID、配对时间窗或一致性快照机制。
5. 两类消息的本机接收时间均在各自subscriber的`update_message()`中独立写入`rclcpp::Clock().now()`；各自`read_message()`独立计算`time_since_received`。这只能表明两路数据在本机的接收驻留时间，不能证明控制与诊断样本来自同一机器人采样周期，也不能直接测得机器人端生成时间或两路网络传输延迟差。
6. `read_robot_state()`和`read_diagnostic_data()`分别只验证各自消息类型与各自staleness timeout；没有比较两路序列号、关联ID、机器人端时间戳或相互最大允许时间差。两路各自新鲜并不等于两路彼此同步。
7. `reset_data()`将两个缓存的message_type设为INVALID、sequence_number清零，但没有在可见代码中建立连接代际标识，也没有为两个通道维护一对“已验证首帧”的联合状态。subscriber自己的first_read/last sequence生命周期需要结合每次subscriber重新构造确认；RobotDriver层没有暴露联合代际证据。
8. 公开的`get_current_message_sequence()`只返回控制状态最后一次有效读取的序列号；硬件接口在发送命令时用该控制序列号填入命令头。诊断序列号没有参与命令授权、状态/诊断关联或控制数据完整性门禁。
9. 硬件接口周期性read把控制状态中的operation_mode、safety_status、in_error、estop_pressed、brakes_released等字段映射到supervision接口；诊断数据没有相应的周期性状态映射。因此上层看到控制状态可用，并不能推导诊断通道健康。

### B. 风险分析（静态推导，尚非已复现故障）

- **高优先级：连接成功会掩盖诊断通道未验证。** connect把诊断ready硬编码true，后续CS9类型检查又被注释；在控制状态有效但诊断数据缺失/无效时，连接仍可能返回成功。若系统或运维人员将“connected”解释为控制器身份、固件兼容性和诊断健康均已验证，会形成错误健康认知。
- **高优先级：控制/诊断两路独立新鲜不等于同一时刻状态。** 例如控制状态刚更新而诊断状态仍是此前缓存，或者诊断状态更新而控制状态延迟；两个独立的100ms类驻留时间门槛即使分别通过，也不能证明两者属于同一控制周期。对涉及安全状态、故障原因和运动许可的判断，不能把两路数据无条件拼成原子快照。
- **中高优先级：诊断链路失效无法通过周期read及时暴露。** 当前硬件周期read/write不调用diagnostic读取API，诊断socket接收线程即使停止、数据过期或诊断报文无效，也没有从这两个周期入口形成持续的诊断健康状态。具体外部监控是否补足此能力，需检查集成部署，不能从当前driver源码推断。
- **中优先级：连接阶段固件信息可能不是本次连接的新数据。** connect在reset缓存后未读取诊断帧便打印固件版本；当前缓存内容没有通过本次连接的有效性和新鲜度检查。不得把该日志当成固件版本识别/兼容性验收证据。
- **中优先级：各通道序列号不能直接相互比较。** 两个subscriber独立维护序列统计，代码没有证明协议定义的两个sequence共享计数域、复位点和采样时刻。直接比较数字可能错误地把正常独立计数解释为丢帧或配对成功。
- **边界：** 目前证据不能断言VAL3端两类报文是否天然同周期产生，也不能断言诊断包中是否有未被当前客户端解析的设备时间戳/采样计数。需要核对VAL3服务端协议定义和抓包；本节只确认ROS2客户端没有实现跨通道关联门禁。

### C. 整改建议

1. 明确诊断能力等级：若诊断属于连接硬门槛，必须等待真实诊断首帧并校验消息类型、控制器类型、固件版本白名单和新鲜度；若诊断允许降级，则显式发布`diagnostics_degraded/unavailable`，不得伪报ready。
2. 将连接结果拆成`control_connected`、`control_state_valid`、`diagnostics_transport_ready`、`diagnostics_sample_valid`、`controller_identity_verified`、`firmware_compatible`等独立状态；总体状态按产品安全需求明确组合，日志不能把传输层ready混为应用层ready。
3. 周期性读取诊断数据，并提供独立的诊断健康状态/错误码/最后有效接收时间；诊断缺失时按安全需求决定降级、ERROR或禁止运动，不能悄悄沿用旧缓存。
4. 若需控制/诊断联合判断，优先在VAL3协议中提供共同的机器人端采样计数/时间戳/连接epoch；两路消息均携带同一关联ID。ROS2端验证ID一致、单调性、最大允许时间差和丢包/重启复位规则。
5. 若上游协议无法提供共同ID，明确承认只能做“时间窗近似关联”：使用统一steady-clock接收时间，设定最大接收时间差，输出关联质量/不确定度，不得声称原子一致性；安全关键判断不得仅依赖这种近似配对。
6. 对每一路分别保存最近有效消息、最近接收时间、最近有效序列、数据源/连接代际、错误计数；无效新包不得覆盖最后有效数据，但必须更新健康状态，避免旧值继续被误当作当前值。
7. 补齐CS9类型与VAL3固件兼容性策略；未知控制器/固件必须明确拒绝或进入受限降级，不能只打印未验证的缓存字段。
8. 对连接重建清空两个通道的配对状态和有效性历史；新代连接必须重新完成控制首帧与诊断首帧校验，旧代数据不能满足新代就绪。

### D. 新增验收任务（SERVO-233–SERVO-242）

| 编号 | 验收项 | 通过标准 | 验收证据 | 状态 |
|---|---|---|---|---|
| SERVO-233 | 诊断首帧真实门槛 | 诊断缺失时连接结果按需求拒绝或明确降级，不再硬编码ready | 双UDP通道故障注入 | 未执行 |
| SERVO-234 | CS9控制器身份验证 | 非CS9/未知类型按兼容策略拒绝或受限运行 | 协议模拟与CS9 HIL | 未执行 |
| SERVO-235 | VAL3固件版本校验 | 支持版本通过，未知/不兼容版本明确拒绝或降级 | 版本矩阵测试 | 未执行 |
| SERVO-236 | 诊断周期读取与过期 | 诊断断流/无效/过期能在规定期限内进入明确健康状态 | 周期集成测试 | 未执行 |
| SERVO-237 | 双通道错位注入 | 控制新、诊断旧及反向错位均被识别，不产生伪一致快照 | 延迟/乱序注入 | 未执行 |
| SERVO-238 | 共同采样ID关联 | 若协议支持共同ID，跨通道配对、丢失、回绕、重启规则正确 | 协议仿真/抓包 | 未执行 |
| SERVO-239 | 时间窗近似关联边界 | 无共同ID时最大接收差、时钟误差与不确定度有明确定义 | 时间偏移/延迟测试 | 未执行 |
| SERVO-240 | 连接代际隔离 | 重连后旧诊断/控制缓存不能满足新连接ready或配对 | 重连故障注入 | 未执行 |
| SERVO-241 | 诊断降级对上层传播 | diagnostics unavailable/degraded被明确暴露，上层策略符合安全需求 | ros2_control集成测试 | 未执行 |
| SERVO-242 | 状态/诊断联合故障矩阵 | 两路断流、单路重启、序列回绕、无效包、固件不兼容均有确定结果 | HIL与长期故障注入 | 未执行 |

### E. 本节来源记录（#1817–#1821）

| 编号 | 固定来源 | 用途 |
|---|---|---|
| #1817 | [ICube robot_driver.cpp @ bd658e2](https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/src/robot_driver.cpp) | 诊断首帧TODO/ready硬编码、协议/CS9/固件检查、两路读取与新鲜度 |
| #1818 | [ICube real_time_socket_subscriber.cpp @ bd658e2](https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/src/real_time_socket_subscriber.cpp) | 两个subscriber独立接收时间、序列丢包跟踪 |
| #1819 | [ICube staubli_hardware_interface.cpp @ bd658e2](https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/src/staubli_hardware_interface.cpp) | 周期read/write只读取控制状态及supervision映射 |
| #1820 | [ICube robot_driver.hpp @ bd658e2](https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/include/staubli_robot_driver/robot_driver.hpp) | 独立状态缓存、timeout和控制序列接口 |
| #1821 | [ROS 2 diagnostic_msgs/DiagnosticArray](https://github.com/ros2/common_interfaces/blob/rolling/diagnostic_msgs/msg/DiagnosticArray.msg) | 诊断数据表达应包含明确header时间语义的通用参考；不代表Stäubli协议已采用该消息 |


## 9.3.61 ROS 2 lifecycle转换、停机语义与命令门控（固定上游提交 bd658e2）

**审查范围：** `StaubliHardwareInterface` 的 `on_init/on_configure/on_activate/on_deactivate/on_cleanup/on_shutdown/on_error/read/write`，`RobotDriver::connect/disconnect/send_stop_all_command/send_robot_command`，以及UDP资源关闭路径。固定上游提交：[`bd658e2d266e315d2ee35f985fb352ea88306b79`](https://github.com/ICube-Robotics/staubli_driver_ros2/commit/bd658e2d266e315d2ee35f985fb352ea88306b79)。

### 源码事实

1. `StaubliHardwareInterface` 头文件声明并实现 `on_init`、`on_configure`、`on_activate`、`on_cleanup`、`on_shutdown`、`on_error`，但没有声明或实现 `on_deactivate`。Active→Inactive没有该类自定义的动作停止、命令模式复位或资源策略。
2. `on_configure()`解析网络参数并调用 `robot_driver_->connect(net_config, 5000)`；connect失败时返回CallbackReturn::ERROR。成功后保留通信连接，符合“配置阶段建立通信”的常见生命周期分工，但诊断首帧虚假ready问题已在§9.3.60单独记录。
3. `on_activate()`只将本地 `current_control_mode_` 设置为 `CommandType::STOP` 并返回SUCCESS；没有主动发送STOP，没有重新读取/验证新鲜状态，也没有检查诊断、控制器身份或固件状态。
4. `on_cleanup()`调用 `disconnect()`，但忽略其bool返回值，随后无条件返回SUCCESS。若接收线程停止或socket关闭失败，上层仍会认为cleanup成功。
5. `on_shutdown()`仅在 `robot_driver_->is_connected()` 为真时处理；若缓存的 `state_msg_.control_state != STOP` 则调用 `send_stop_all_command()`，但忽略STOP发送结果，随后调用disconnect且同样忽略其结果。若状态缓存过期或从未有效读取，停机决策可能依据旧缓存；该情形需结合上层调用顺序验证。
6. `on_error()`在driver连接时调用STOP但忽略返回值，并返回SUCCESS；若driver不连接则返回ERROR。该回调不执行disconnect或缓存失效处理。ROS 2 ros2_control文档说明read/write返回ERROR会触发on_error；on_error成功与失败会影响组件回到UNCONFIGURED或进入FINALIZED，故错误恢复策略不能只依赖日志。
7. `read()`和`write()`只检查 `robot_driver_ && is_connected()`，没有检查组件当前生命周期状态。write在本地控制模式STOP时仍会构造并发送STOP命令；非STOP时依赖最近一次 `state_msg_` 的错误标志和control_state。是否在Inactive时仍被调用及接口是否可用，依赖具体ros2_control发行版和Controller Manager调度，不能仅凭该源码断言必然发生。
8. `perform_command_mode_switch()`可改变本地 `current_control_mode_`，但没有独立的生命周期状态门闩；切换前检查使用缓存的状态字段。需要确保deactivate与mode switch并发/交错时不会重新进入运动模式。
9. 硬件接口析构函数调用disconnect；RobotDriver析构函数为空。disconnect会reset接口对象、停止接收线程、关闭socket并reset数据；它是资源清理路径，不等价于向机器人发送STOP。
10. `RobotDriver::disconnect()`重复调用在多数已断开路径上趋于幂等，但底层UDP disconnect在未连接时返回true并发出warning；完整的重复configure/cleanup/错误恢复仍需要状态序列测试。connect失败路径多处调用disconnect回滚，但各个失败点、异常抛出及并发读写下的原子性尚未得到验证。
11. `send_stop_all_command()`调用 `control_interface_->send_message()`，而非先验证指针非空；正常单线程连接状态下由is_connected间接约束接口存在，但生命周期并发下仍依赖调用方串行化，需与§9.3.59的共享指针竞态合并验证。
12. 上游ROS 2 Jazzy文档把on_configure作为建立硬件通信的阶段、on_activate作为允许运动/启用硬件的阶段、on_deactivate作为禁用运动的阶段、on_cleanup作为撤销配置通信的阶段；其生命周期文档同时提醒Inactive阶段命令接口的具体处理不能假设由框架自动阻断，硬件实现必须明确行为。

### 风险判断（静态推导，尚未复现）

- Active→Inactive缺少显式停止和模式门控，无法从本驱动源码证明deactivate成功返回后机器人端已收到STOP，或后续write不再发送运动命令。
- activate只复位本地模式，不能证明机器人端控制状态与驱动本地模式同步；本地STOP不等于控制器已确认停止。
- cleanup/shutdown忽略底层失败结果，可能造成上层生命周期状态与实际socket/接收线程资源状态不一致。
- on_error返回SUCCESS的前提仅是调用路径进入已连接分支，而STOP发送结果未作为成功条件；可能出现“错误恢复回调成功”但停止命令未成功发送的状态不一致。
- on_error在未连接时返回ERROR，按ros2_control错误转换语义可能使组件进入FINALIZED，自动恢复能力有限；应设计明确的故障锁存与人工/受控重新加载策略。
- 旧的 `state_msg_` 被用于shutdown STOP判断及write错误门控；生命周期切换前应检查其有效性、新鲜度和连接代际。
- 本节不证明机器人实际发生未停止、非Active运动或资源泄漏；需要控制器端命令确认、生命周期集成和故障注入证据。

### 整改建议

1. 显式实现 `on_deactivate()`：先关闭运动命令入口/锁存deactivating，再发送STOP并检查结果，确认策略后复位本地控制模式；若STOP失败，应返回明确错误并保留故障状态，不得伪报成功。
2. 在硬件接口内维护生命周期/命令许可状态（如UNCONFIGURED/INACTIVE/ACTIVE/ERROR及连接代际）；read/write/mode-switch统一检查许可，非ACTIVE禁止位置/速度等运动命令。STOP与安全停机路径应单独定义，避免被普通命令门控误挡。
3. `on_activate()`需重新验证控制状态有效且新鲜、机器人无错误、运动许可条件满足；若产品策略要求诊断/身份/固件为硬门槛，还应纳入激活门槛。只在状态确认后开放运动模式。
4. `on_cleanup()`、`on_shutdown()`和析构路径应检查并记录disconnect结果；停止接收线程、取消异步操作、关闭socket、清理缓存的顺序与失败回滚应明确，避免生命周期状态先于资源清理完成。
5. `on_error()`应验证STOP实际发送结果，并定义连接不可用时的独立安全策略；区分“STOP命令已发送”“控制器确认停止”“安全回路触发”，不得将它们合并为一个success标志。
6. 对生命周期转换加串行化/门闩，与§9.3.59共享指针并发问题一起处理；每次configure建立新generation，deactivate/cleanup/shutdown使旧generation失效。
7. 在目标ROS 2 Jazzy版本上核对实际Controller Manager调用时序及Inactive接口可用性；不要将Rolling/Humble文档的细节未经验证直接移植到Jazzy。
8. 设计停机状态缓存策略：停止判断必须使用有效、新鲜、属于当前连接代际的状态；缓存无效时走显式故障策略，而不是静默跳过STOP。

### 新增验收任务（均未执行）

| 编号 | 验收项 | 通过标准 | 验收证据 | 状态 |
|---|---|---|---|---|
| SERVO-243 | deactivate停止门槛 | Active→Inactive关闭运动命令入口并执行经确认的停止策略 | Jazzy生命周期集成+控制器日志 | 未执行 |
| SERVO-244 | Inactive写入门控 | Inactive期间位置/速度等运动命令不能发出；STOP/安全路径定义明确 | write调用跟踪与UDP抓包 | 未执行 |
| SERVO-245 | activate重新校验 | 激活前检查当前代际控制状态新鲜、有效及运动许可 | 过期/错误/刹车状态注入 | 未执行 |
| SERVO-246 | cleanup失败传播 | disconnect/线程停止/socket关闭失败不能被伪报cleanup成功 | socket故障注入 | 未执行 |
| SERVO-247 | shutdown STOP结果 | STOP发送失败、状态缓存过期/无效时按安全策略处理并可审计 | 停机故障矩阵 | 未执行 |
| SERVO-248 | on_error恢复语义 | STOP结果、断链策略与SUCCESS/ERROR生命周期结果一致 | read/write错误集成测试 | 未执行 |
| SERVO-249 | configure/cleanup重复转换 | 重复configure、cleanup、shutdown及失败重试无残留线程/socket | 生命周期循环与资源计数 | 未执行 |
| SERVO-250 | 生命周期与mode-switch竞态 | deactivate与prepare/perform mode switch交错时不能重新开放运动模式 | 并发/TSAN测试 | 未执行 |
| SERVO-251 | 连接代际状态隔离 | 重连后旧state_msg不能通过activate或shutdown安全判定 | 重连+缓存过期注入 | 未执行 |
| SERVO-252 | Jazzy实际调用顺序 | 记录目标Jazzy ros2_control版本下read/write与各回调的真实调用时序 | Controller Manager trace | 未执行 |

### E. 本节来源记录（#1822–#1826）

| 编号 | 固定来源 | 用途 |
|---|---|---|
| #1822 | [ICube staubli_hardware_interface.cpp @ bd658e2](https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/src/staubli_hardware_interface.cpp) | 生命周期回调、read/write门控、模式切换和状态缓存 |
| #1823 | [ICube staubli_hardware_interface.hpp @ bd658e2](https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/include/staubli_robot_driver/staubli_hardware_interface.hpp) | 生命周期回调声明；缺少on_deactivate覆盖 |
| #1824 | [ICube robot_driver.cpp @ bd658e2](https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/src/robot_driver.cpp) | connect/disconnect/STOP发送与回滚 |
| #1825 | [ICube udp_socket_impl.hpp @ bd658e2](https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/src/communication/udp_socket_impl.hpp) | 接收线程停止、socket关闭及异步资源生命周期 |
| #1826 | [ros2_control Jazzy hardware lifecycle](https://control.ros.org/jazzy/doc/ros2_control/hardware_interface/doc/lifecycle_of_a_hardware_component.html) | on_configure/on_activate/on_deactivate/on_cleanup职责及Inactive行为说明；具体行为须按目标Jazzy版本集成确认 |


## 9.3.62 控制模式切换、接口组合与命令状态一致性（固定上游提交 bd658e2）

**审查范围：** `resolve_mode()`、`prepare_command_mode_switch()`、`perform_command_mode_switch()`、`export_command_interfaces()`、`write()`及RobotDriver命令发送接口。固定上游提交：[`bd658e2d266e315d2ee35f985fb352ea88306b79`](https://github.com/ICube-Robotics/staubli_driver_ros2/commit/bd658e2d266e315d2ee35f985fb352ea88306b79)。

### 源码事实

1. `resolve_mode(start_interfaces)`按遍历顺序返回第一个匹配的position、velocity、effort或acceleration模式，不汇总全部接口集合，也不检测position与velocity等互斥模式是否同时出现。因此混合请求的解析结果依赖传入顺序。
2. `prepare_command_mode_switch()`显式将`switch_prepared_`清false，然后只解析`start_interfaces`；`stop_interfaces`参数未使用，代码中原本计算outgoing mode的逻辑已注释。当前模式退出集合与新模式进入集合没有成对校验。
3. prepare拒绝velocity、effort模式，但仅当解析结果首先命中它们时才拒绝。若同一批start接口同时包含position和velocity，position先出现时可被接受；反向顺序则因velocity先命中而拒绝。
4. `export_command_interfaces()`对每个关节导出position、velocity和acceleration接口；其中velocity/effort切换被拒绝，acceleration-only请求被解析为INVALID后当作STOP接受。源码注释称acceleration用于joint-limiter support，但它仍是被导出的command interface，需明确控制器管理器/限幅器对它的claim语义。
5. `export_command_interfaces()`还导出GPIO digital/analog输出接口；这些接口不参与`resolve_mode()`。GPIO-only启动时incoming mode为STOP并被接受，但`write()`无论STOP或运动模式都会把当前GPIO输出数组写入命令包。故STOP运动模式不等价于“所有IO输出归零”；底层`send_stop_all_command()`的语义则是motion+IOs置零，二者不同。
6. prepare成功后只缓存一个`pending_mode_`和`switch_prepared_`布尔值，不保存start/stop接口集合、请求指纹、控制器切换代次或状态样本序列。perform不核对其参数（两个参数均未命名/使用），直接消费缓存；如果prepare未调用或标志为false，则默认执行STOP切换。
7. prepare失败会留下`switch_prepared_=false`，但没有清理/记录失败原因或上次pending mode的代际信息。当前接口串行调用预期依赖Controller Manager协议，若外部调用并发/交错，单一pending槽可能被覆盖；需要集成和TSAN测试确认。
8. perform对JOINT_POSITION检查缓存`state_msg_.error_state`、`motion_possible`和`operation_mode_status`。未检查状态消息是否新鲜、是否属于当前连接代际、是否与prepare时同一状态快照；HOLD只记录WARN仍提交position模式。
9. perform在位置模式检查失败时将`current_control_mode_`设为STOP并返回ERROR，但没有在回调内发送STOP；后续周期write可能发送STOP，但这一安全效果依赖Controller Manager后续调度，不能视为perform已完成控制器STOP确认。
10. perform成功切换时将位置命令初始化为最近读取的关节位置，并清零速度/加速度命令数组；未证明缓存位置新鲜，也未检查position命令接口是否完整覆盖全部关节。
11. `write()`按`current_control_mode_`决定STOP或position/velocity消息，但不校验当前已claim的完整接口集合；STOP分支将运动参考清零，仍会附带GPIO命令。NaN检查遍历`num_joints_`，而command_reference固定容量，需对超出协议轴数的配置做独立边界验证。
12. `send_robot_command()`目前没有实现position/velocity限位检查（源码TODO）；STOP参考非零只记录WARN，不拒绝发送。该方法发送成功只表示本地通信接口接受发送，不等于机器人控制器确认执行/停止。

### 风险判断（静态推导，尚未复现）

- 混合接口集合可能因顺序不同而产生不同接受结果，控制器切换结果不具备集合语义上的确定性。
- 忽略stop_interfaces会弱化“旧模式退出+新模式进入”的一致性验证；模式状态可能与Controller Manager实际claim集合脱节。
- acceleration接口导出但单独启动解析为STOP，GPIO接口启动也解析为STOP，二者都可能产生“接口已claim但控制模式仍STOP”的语义歧义。
- pending mode单槽缺少接口集合/代际绑定，无法在源码层证明prepare与perform严格对应同一请求。
- 基于旧/过期state_msg_开放position模式可能将不再有效的brake/error状态作为许可依据。
- perform失败后仅修改本地模式，不代表机器人端已确认STOP；STOP与普通write的GPIO行为不同，必须明确其I/O副作用。
- 这些是代码结构风险，不证明Controller Manager一定会发出错误模式、机器人一定运动或IO一定切换；需在目标Jazzy版本进行控制器管理器集成与通信抓包。

### 整改建议

1. 将start/stop接口解析为规范化集合：逐关节校验接口覆盖、禁止互斥position/velocity/effort混合、定义partial joint claims和GPIO-only策略；不依赖vector顺序。
2. 对stop_interfaces与start_interfaces共同计算旧模式/目标模式，验证合法转换；明确position→STOP、position→position重启、GPIO独立claim、acceleration limiter接口的语义。
3. prepare缓存完整规范化请求（start/stop集合、resolved mode、连接generation、状态sequence/有效时间、请求token）；perform核对调用参数与缓存完全一致，拒绝无prepare、重复perform、过期prepare及跨代请求，不静默默认STOP。
4. 对acceleration接口明确为内部限幅器接口还是外部可claim command interface；若不支持独立控制，调整导出策略或明确组合约束并提供控制器管理器测试。
5. 将GPIO输出与运动模式解耦：定义STOP时保持、归零或独立写入的产品语义；区分运动STOP、全部IO安全复位和急停/安全回路，不混为一类。
6. position模式激活前检查当前连接代际、状态有效/新鲜、关节数和motion_possible；HOLD是否允许模式切换应成为显式策略，而非仅WARN。
7. perform失败时保持命令门闩关闭并通过独立安全路径处理STOP；不能依赖下一周期write作为唯一停止保证。实时回调内避免阻塞网络等待。
8. 在RobotDriver发送层补充按型号/协议明确的关节位置/速度/加速度限值与范围检查，并对固定长度数组与num_joints配置不一致作硬错误。
9. 与§9.3.59并发生命周期、§9.3.61 lifecycle gate合并设计，避免mode switch和deactivate并发时重新开放运动模式。

### 新增验收任务（均未执行）

| 编号 | 验收项 | 通过标准 | 验收证据 | 状态 |
|---|---|---|---|---|
| SERVO-253 | 混合接口顺序不变性 | position+velocity/effort混合请求无论排列顺序均一致拒绝 | 单元测试排列/随机置换 | 未执行 |
| SERVO-254 | stop/start集合合法性 | 校验旧模式退出与新模式进入组合，拒绝非法转换 | Controller Manager集成测试 | 未执行 |
| SERVO-255 | acceleration接口claim语义 | limiter/控制器claim行为与驱动模式定义一致 | URDF+controller配置实测 | 未执行 |
| SERVO-256 | GPIO-only与STOP语义 | 明确GPIO claim、运动STOP及IO复位的独立行为 | UDP命令包抓取与IO仿真 | 未执行 |
| SERVO-257 | prepare/perform请求绑定 | 参数集合、token、状态序列与generation一致；过期/重复调用拒绝 | 回调序列测试/TSAN | 未执行 |
| SERVO-258 | position模式状态新鲜度 | 过期、错误、刹车/许可变化不能开放position模式 | 状态延迟与故障注入 | 未执行 |
| SERVO-259 | perform失败停止闭环 | 模式提交失败时命令门闩保持关闭并验证控制器STOP策略 | 控制器模拟器/抓包 | 未执行 |
| SERVO-260 | 多关节接口完整性 | 缺关节、超协议轴数及不一致claim均明确拒绝 | URDF参数边界测试 | 未执行 |
| SERVO-261 | GPIO与运动命令隔离 | GPIO输出策略不因运动STOP语义产生非预期副作用 | 数字/模拟IO故障矩阵 | 未执行 |
| SERVO-262 | Jazzy模式切换端到端 | 目标Jazzy Controller Manager切换顺序、接口claim和write命令一致 | 版本锁定的系统集成测试 | 未执行 |

### E. 本节来源记录（#1827–#1831）

| 编号 | 固定来源 | 用途 |
|---|---|---|
| #1827 | [ICube staubli_hardware_interface.cpp @ bd658e2](https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/src/staubli_hardware_interface.cpp) | 接口导出、模式解析、prepare/perform、write与GPIO行为 |
| #1828 | [ICube staubli_hardware_interface.hpp @ bd658e2](https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/include/staubli_robot_driver/staubli_hardware_interface.hpp) | pending/current mode及prepare标志成员 |
| #1829 | [ICube robot_driver.cpp @ bd658e2](https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/src/robot_driver.cpp) | STOP与普通命令发送、限位TODO |
| #1830 | [ICube robot_driver.hpp @ bd658e2](https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/include/staubli_robot_driver/robot_driver.hpp) | Driver命令接口契约 |
| #1831 | [ros2_control Jazzy HardwareComponentInterface API](https://control.ros.org/jazzy/doc/api/classhardware__interface_1_1HardwareComponentInterface.html) | prepare为非实时准备，perform在实时更新循环执行且应快速完成 |


## 9.3.63 运动命令float32线格式数值边界、控制周期与STOP/IO校验（2026-11-08）

### A. 审查基线与证据范围

- 上游固定提交：`bd658e2d266e315d2ee35f985fb352ea88306b79`。
- 本节是对§9.3.1、§9.3.32和§9.3.33的增量审查，不重复认定已记录的DoF越界、NaN/Inf、关节限位或周期字段缺少策略；本轮聚焦这些double值进入固定float32 wire字段时的二次边界，以及STOP/IO字段是否经过同一校验链。
- 核对`serialization.hpp`、`messages.cpp`、`messages.hpp`、`staubli_hardware_interface.cpp`、`robot_driver.cpp`及固定协议字段布局。来源#1832–#1836。仅静态源码审查；未执行构建、单测、数值注入、VAL3编译、SRS/CS9仿真、HIL或实机测试。

### B. 关键源码事实

1. **double到float32缩窄没有线级防护。** `serialize_type(const double&)`直接执行`static_cast<float>(value)`后写入4字节；没有在转换前检查有限性、float32可表示范围、转换后是否仍有限，也没有拒绝溢出或报告精度损失。即使上层某字段曾检查double有限性，有限但超出float32可表示范围的值仍可能在缩窄阶段失去有效数值表示；接近float32精度分辨率的不同double也可能编码成相同wire值。不得将double内存精度当作控制器实际收到的精度。
2. **RobotCommand存在多个共享该缩窄函数的字段。** `controller_period`、6个`command_reference`和4个`analog_outputs`均按float32写入。当前序列化函数不对这些字段实施统一有限性/范围检查；HardwareInterface的NaN检查只针对运动参考数组，且在此前章节已记录其不覆盖Inf和其他数值字段。
3. **周期字段的有效范围未在序列化边界定义。** `write()`将ROS period转换为毫秒double后赋给`controller_period`；消息成员默认值为-1.0。RobotCommand serializer直接缩窄并写出，没有拒绝负值、零、非有限值或超出协议/控制器允许范围的周期。该项是线级字段校验缺口，不据此推断VAL3必然按异常周期运动；VAL3消费语义及超时策略仍需目标版本验证。
4. **模拟输出没有数值范围/有限性门控。** HardwareInterface将配置的模拟输出命令直接复制到4元素数组，serializer再转换为float32；本轮可见写入路径没有对NaN、Inf、float32溢出或硬件电压/电流量程进行拒绝。具体模拟量程必须按CS9 I/O模块、接线和用户配置确认，不能凭通用协议猜测。
5. **STOP参考检查不等于完整STOP报文校验。** `send_robot_command()`只在command_type为STOP时遍历command_reference；若任一项非零仅WARN，仍继续发送。它没有在发送入口统一检查command_type合法枚举、controller_period、analog_outputs或digital_outputs的安全策略。HardwareInterface的STOP分支会清零运动参考，但之后仍将GPIO输出命令写入同一消息；因此STOP运动模式本身不等于模拟/数字IO归零。专用`send_stop_all_command()`与普通STOP write路径必须继续保持语义区分。
6. **消息注释与实际单位仍有契约冲突。** `RobotCommandMessage`注释把position/velocity reference描述为rad和rad/s，而HardwareInterface在写入command_reference前执行`rad2deg()`。§9.3.33已记录单位映射和VAL3关节限位问题；本轮补充要求将“ROS接口单位、C++内存单位、float32 wire单位、VAL3解码后单位”定义为一份唯一协议契约，并用独立黄金向量验证，不能仅靠局部注释推断。
7. **STOP与普通命令必须采用不同但完整的验证策略。** STOP应允许明确规定的安全周期/参考值，但不能因STOP而跳过报文类型、线级数值和IO安全策略；普通运动命令必须在double层和float32转换后都验证。任何校验失败都应在发送前拒绝，并明确是否触发独立安全停止路径，不能将“本地send函数返回true”视为控制器接受或执行。

### C. 风险判断（静态推导，尚未复现）

- double→float32缩窄可能引入不可表示值或量化；目前没有代码层的转换后验证及精度预算。
- controller_period、模拟输出与运动参考共用缩窄器，但校验覆盖不一致，可能出现运动参考已过初筛而其他字段携带非有限/超范围数值的报文。
- STOP普通写入路径允许GPIO字段继续生效，且发送层对非零STOP参考仅告警；若上层把STOP误当作“所有输出归零”，可能产生控制语义误判。
- 协议注释单位与硬件接口转换不一致，会使独立客户端、VAL3实现、日志和测试黄金向量对同一数值产生不同解释。
- 以上为源码可确认的校验缺口和风险推导，不证明实际CS9已接收异常数值、发生输出变化或产生机械运动。

### D. 整改建议

1. 将wire序列化改为显式受检转换：先检查double有限性，再检查float32可表示范围，转换后再次检查有限性；为位置、速度、周期、模拟输出定义字段级允许范围。
2. 建立float32量化误差预算，覆盖典型小增量、最大关节角、最大速度、极值与边界邻域；对不能满足控制分辨率的协议值应拒绝或调整线格式，而非静默舍入。
3. 明确controller_period合法区间、单位、默认值和STOP专用语义；拒绝负值、零（若不允许）、非有限值和超控制器范围值，并由VAL3端重复校验。
4. 按具体I/O模块定义模拟输出物理量程、单位、缩放、饱和值及断线策略；数字输出NaN/Inf的转换行为也需显式定义，不能依赖浮点比较结果。
5. 在RobotDriver统一发送入口校验命令枚举、运动参考、控制周期和全部IO字段；普通STOP参考非零应拒绝或由明确兼容策略处理，不能仅WARN。将运动STOP、IO保持、IO归零、急停/安全回路定义为不同操作。
6. 修正文档单位契约，给出rad↔deg转换责任边界，并建立C++/VAL3独立逐字节黄金向量，验证边界值、符号、精度和拒绝行为。
7. 将校验失败、停止请求发送失败、控制器确认停止失败分别记录；不得将UDP本地发送成功视为安全动作已完成。

### E. 新增验收任务（均未执行）

| 编号 | 验收项 | 通过标准 | 验收证据 | 状态 |
|---|---|---|---|---|
| SERVO-263 | double→float32有限性与范围 | NaN、±Inf、float32上溢边界在序列化前/转换后均按策略拒绝 | 序列化单测与逐字节结果 | 未执行 |
| SERVO-264 | float32量化误差预算 | 关节位置/速度典型增量和边界值的量化误差满足控制精度预算 | 独立数值分析与黄金向量 | 未执行 |
| SERVO-265 | controller_period线级校验 | 负、零、非有限、极小/极大周期按协议策略拒绝或明确定义 | ROS→C++→VAL3字段测试 | 未执行 |
| SERVO-266 | analog_outputs数值和物理量程 | 非有限、上溢、越模块量程值在发送前拒绝/按批准策略限幅 | I/O模块配置与仿真/台架测试 | 未执行 |
| SERVO-267 | STOP完整报文契约 | STOP参考、周期、数字/模拟IO均满足独立STOP策略；非法报文不发送 | 发送入口单测与UDP抓包 | 未执行 |
| SERVO-268 | STOP与IO语义隔离 | motion STOP、IO保持、IO归零和安全急停行为分别定义并验证 | CS9 I/O仿真及安全评审 | 未执行 |
| SERVO-269 | 命令单位契约一致性 | ROS rad、C++内部表示、wire float32及VAL3解码单位唯一且一致 | C++/VAL3独立黄金向量 | 未执行 |
| SERVO-270 | 非有限值跨层拒绝 | 运动参考、周期、模拟输出在硬件接口和Driver发送入口均有防御性检查 | 单元测试/故障注入 | 未执行 |
| SERVO-271 | 序列化失败的发送门控 | 任一字段校验失败时不调用UDP send，错误原因可观测 | mock socket调用次数与负向测试 | 未执行 |
| SERVO-272 | CS9端到端边界验收 | 认可型号/固件下验证数值边界、STOP/IO行为与控制器反馈 | SRS/HIL/FAT/SAT记录 | 未执行 |

### F. 本节来源记录（#1832–#1836）

| 编号 | 固定来源 | 用途 |
|---|---|---|
| #1832 | [ICube serialization.hpp @ bd658e2](https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/include/staubli_robot_driver/communication/serialization.hpp) | double缩窄为float32、无转换后校验及量化路径 |
| #1833 | [ICube messages.cpp @ bd658e2](https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/src/communication/messages.cpp) | RobotCommand 55字节布局、字段序列化及STOP默认值 |
| #1834 | [ICube messages.hpp @ bd658e2](https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/include/staubli_robot_driver/communication/messages.hpp) | command_reference单位注释、controller_period与IO字段契约 |
| #1835 | [ICube staubli_hardware_interface.cpp @ bd658e2](https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/src/staubli_hardware_interface.cpp) | ROS周期、运动参考及GPIO字段写入路径 |
| #1836 | [ICube robot_driver.cpp @ bd658e2](https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/src/robot_driver.cpp) | STOP参考仅警告、发送入口缺少字段级统一校验 |


## 9.3.64 VAL3命令接收解码、序列新鲜度与控制器侧执行门控（2026-11-08）

### A. 审查基线与范围

- 上游固定提交：`bd658e2d266e315d2ee35f985fb352ea88306b79`。本节审查同一提交中的CS9/VAL3服务端源文件，而非仅审查ROS 2客户端。
- 上游VAL3 README声明目标为CS9、VAL3 8.x.x及以上，测试机型为TX2-60L，并称可能兼容多数6DoF机型；这不是所有机型/固件的认证结论。
- 核对UDP读取、消息头/命令payload解码、序列延迟、controlTask状态机、joint position控制、velocity控制和RobotCommand数据定义。来源#1837–#1843。
- 本轮为固定提交的静态源码审查；未执行VAL3 Studio编译、CS9仿真、机器人控制器部署、网络故障注入、HIL或实机测试。VAL3运行时函数（如`isInRange`、`fromBinary`、`sioGet`）的边界行为未由该源码仓库完整定义，相关结论不作推断。

### B. 控制器侧已有保护（源码事实）

1. **UDP读取固定长度。** `initRobotCommandMsg`初始化8字节header、47字节payload，总计55字节；`readDataOnce`仅在`sioGet`返回字节数等于缓冲区长度时标记新消息，正数但长度不匹配时报告通信错误；零字节读取表示本轮无新消息。
2. **消息头校验。** `decodeHeader`检查缓冲区至少有header长度、magic number=43981（0xABCD）、protocol version=1和header解码偏移=8；`decodeRobotCommandMsg`检查message type=2，并在payload解码结束时检查索引是否等于接收buffer长度。
3. **命令类型门控。** `controlTask`先检查motion command type是否在0..4，再按STOP=1、position=2、velocity=3分派；未知模式最终进入错误路径。position子程序再次检查命令有效标志、motion possible和command type=2。
4. **位置范围检查。** `updateJointPositionControl`将6个解码值写入`jointRx`，调用VAL3的`isInRange()`；若返回false则停止movejSync并置错误。注意源码没有定义`isInRange`对NaN/Inf的行为，不能声称它已可靠拒绝非有限值。
5. **命令延迟门控。** controlTask用本机发出的state sequence和接收command sequence计算延迟；机器人正在运动时延迟大于5个循环触发STOP错误，静止时大于25触发STOP错误；负延迟也触发错误。序列差值小于-60000时按uint16回绕增加65536。
6. **错误恢复路径。** 解码错误会设置错误标志并切到STOP模式；控制任务错误处理调用停止/复位运动并重置控制socket。此为软件请求路径，不等于安全回路动作或机械停止已被外部确认。

### C. 发现的缺口与风险

1. **声明payload长度没有在解码后与固定协议长度核对。** `decodeRobotCommandMsg`先用已初始化的header字段（8+47）核对当前buffer大小，随后才调用`decodeHeader`覆盖接收包中的`nPayloadSize`；之后没有显式断言接收header声明的payload size必须等于47。后续解析固定字段并检查最终偏移等于buffer长度，因此当前固定55字节缓冲区可约束实际解码长度，但header中的payload length字段未被独立验证。该缺口会削弱协议自描述字段一致性检查；不能据此直接断言存在越界读取。
2. **解码后缺少字段级数值验证。** `fromBinary`直接把4字节float32写入VAL3 num字段；可见解码路径没有对`nRemoteCtrlPeriod`、6个`nMotionCmdData`或4个`nAnalogOutputs`执行显式finite、范围、物理单位或转换后合理性检查。position路径只有`isInRange`，其非有限输入行为未经验证；velocity子程序的安全限值仍是TODO，且运动执行尚未实现。
3. **位置目标接近性仍是TODO。** position控制已调用`isInRange`检查关节范围，但“target is close enough to current position”仍标记TODO。范围内的远距离目标是否允许、最大单周期位置增量/速度/加速度如何限制，不能从现有代码确认。
4. **接收数据无新消息时沿用上一条有效命令。** readData返回无新数据时，controlTask保留上一条`bIsValid`命令并继续按序列差计算延迟；运动中延迟阈值和静止阈值提供一定超时门控，但源码中还有明确的staleness TODO。重复序列（delay=0）没有被单独拒绝；未建立严格的单调递增/重复包策略。小幅倒退会产生负延迟错误，大幅负差按uint16回绕解释，旧包跨回绕边界可能被误判为新鲜，需边界测试确认。
5. **序列延迟与命令时间不是同一概念。** 延迟以控制器每周期生成的state sequence和接收command sequence差计算，单位是控制循环数而非真实毫秒；阈值注释中的20ms/100ms依赖实际循环周期。控制周期抖动、任务overrun、序列更新频率改变时，固定循环阈值不必然等于固定真实时间。
6. **GPIO数据目前未执行。** decoder读取16位digital output mask，但把mask转为boolean数组的代码注释掉；controlTask中的digital/analog输出写入均为TODO。虽解码了4路模拟输出，但没有可见的物理输出调用。故不能把ROS侧发送GPIO命令描述成控制器已应用；反过来，当前代码也没有提供GPIO命令有效性和物理量程验收证据。
7. **速度控制是占位实现。** controlTask支持识别模式3并调用velocity子程序，但该子程序的安全限值为TODO，`$setVelCmd`注释掉，明确记录not yet implemented并返回错误。ROS侧宣称/导出的接口不能等同于控制器侧已实现该模式。
8. **错误复位与重新接入缺少冷却/人工确认门控。** controlTask错误分支清理运动、清除错误标志、重置sequence并重置socket；源码对“重新接受新命令前增加延迟（如1000ms）”明确标记TODO。需要确认错误原因是否锁存、重新连接是否需要重新使能/人工确认，以及连续故障是否会形成快速重连循环。
9. **STOP语义不是独立安全功能。** 程序错误分支调用VAL3运动停止API并resetMotion；未由该代码证明安全PLC、急停、STO、保护停止等独立安全功能的状态、诊断覆盖或性能等级。软件STOP不能替代风险评估和安全回路。

### D. 整改建议

1. 在header解码后校验magic、version、message type、header size、payload size和实际datagram长度之间的完整一致性；对固定协议版本明确payload必须为47字节，拒绝额外/缺失字段。
2. 为每个float字段建立接收端白名单：有限性、量纲、单位、上下限、最大变化率、控制周期关系；在VAL3调用运动API前再次校验，不能依赖ROS端防护。
3. 明确`isInRange`对NaN/±Inf、边界相等、机型/工具/用户坐标和软限位的真实语义；通过VAL3编译和CS9台架测试确认，必要时先做显式有限性检查。
4. 增加目标与当前关节位置的单周期增量、速度、加速度和jerk门控；将控制器配置、机器人型号、负载/工具参数及限位来源纳入可追溯配置。
5. 以uint16模运算定义序列新鲜度，区分新包、重复包、乱序包、回绕、重启新代际和远端重放；增加连接nonce/epoch或握手机制，避免重启后旧包被误认为新包。
6. 将序列循环阈值转换为明确的真实时间预算，并纳入任务周期、overrun、接收时刻与命令时间戳；超时策略应按运动模式和风险分析确定。
7. 在GPIO功能正式开放前完成digital mask映射、analog物理量程、断线默认状态和STOP时IO保持/归零策略；在当前未实现状态下，接口应明确禁用并返回可观测错误。
8. 未实现的velocity/torque/acceleration模式应在ROS导出、控制器解码和控制器执行三层一致拒绝，避免“可识别但不可执行”的接口契约。
9. 对通信/解码/运动错误采用锁存故障、明确复位条件、重新使能门控和重连冷却；将普通软件STOP与安全急停/STO分开验收。

### E. 新增验收任务（均未执行）

| 编号 | 验收项 | 通过标准 | 验收证据 | 状态 |
|---|---|---|---|---|
| SERVO-273 | VAL3 header/payload长度一致性 | 错误header size、payload size、实际datagram长度均拒绝；固定版本payload=47 | VAL3单测/网络注入 | 未执行 |
| SERVO-274 | float32解码非有限值拒绝 | NaN、±Inf、极端有限值在VAL3运动API前拒绝 | CS9仿真与负向测试 | 未执行 |
| SERVO-275 | isInRange边界语义 | 各型号关节上下限、NaN/Inf、工具/用户坐标行为经验证 | VAL3运行测试与机型限位矩阵 | 未执行 |
| SERVO-276 | 位置单周期增量门控 | 范围内超大目标跳变按速度/加速度/jerk约束拒绝或安全规划 | CS9台架/HIL轨迹记录 | 未执行 |
| SERVO-277 | uint16序列回绕/重放/乱序 | 重复、乱序、跨回绕、控制器重启旧包均按代际策略处理 | 65535→0边界注入 | 未执行 |
| SERVO-278 | 命令超时真实时间语义 | 不同任务周期/overrun下，运动和静止超时满足经批准的ms预算 | 周期测量与断包故障注入 | 未执行 |
| SERVO-279 | GPIO接收与安全状态 | digital mask正确映射，analog量程有效，STOP/故障状态符合IO策略 | CS9 I/O仿真与台架 | 未执行 |
| SERVO-280 | 未实现模式端到端拒绝 | velocity/torque等未实现模式在ROS导出和VAL3执行层一致拒绝 | 接口枚举测试及控制器日志 | 未执行 |
| SERVO-281 | 错误锁存与重连门控 | 故障原因可追踪，复位/重新使能/冷却条件可验证，无自动危险重启 | 故障注入与状态机测试 | 未执行 |
| SERVO-282 | 安全功能独立性验证 | 软件STOP与急停/保护停止/STO边界清晰，安全功能按适用标准验证 | 风险评估、安全回路图与认证证据 | 未执行 |

### F. 本节来源记录（#1837–#1843）

| 编号 | 固定来源 | 用途 |
|---|---|---|
| #1837 | [VAL3 decodeRobotCommandMsg.pgx @ bd658e2](https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/val3/userapp/ros2_server/Serialization/decodeRobotCommandMsg.pgx) | header/payload解码、字段映射、消息长度和有效标志 |
| #1838 | [VAL3 decodeHeader.pgx @ bd658e2](https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/val3/userapp/ros2_server/Serialization/decodeHeader.pgx) | magic/version/header校验 |
| #1839 | [VAL3 readData.pgx @ bd658e2](https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/val3/userapp/ros2_server/Comm/readData.pgx) 与 [readDataOnce.pgx](https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/val3/userapp/ros2_server/Comm/readDataOnce.pgx) | UDP固定长度读取及无数据/长度错误分支 |
| #1840 | [VAL3 controlTask.pgx @ bd658e2](https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/val3/userapp/ros2_server/controlTask.pgx) | 序列延迟、命令模式、超时、STOP和错误恢复 |
| #1841 | [VAL3 updateJointPositionControl.pgx @ bd658e2](https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/val3/userapp/ros2_server/Control/updateJointPositionControl.pgx) | isInRange、目标接近TODO、movejSync控制 |
| #1842 | [VAL3 computeSequenceDelay.pgx @ bd658e2](https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/val3/userapp/ros2_server/Comm/computeSequenceDelay.pgx) 与 [getNextSequenceNumber.pgx](https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/val3/userapp/ros2_server/Comm/getNextSequenceNumber.pgx) | uint16序列生成、回绕和延迟计算 |
| #1843 | [VAL3 RobotCommand.dtx @ bd658e2](https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/val3/userapp/ros2_server/Types/RobotCommand/RobotCommand.dtx)、[updateJointVelocityControl.pgx](https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/val3/userapp/ros2_server/Control/updateJointVelocityControl.pgx) 与 [VAL3 README](https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/val3/README.md) | 6轴命令/IO结构、velocity未实现、控制器版本与测试机型范围 |


## 9.3.65 VAL3同步控制循环的采样率对齐、命令刷新与overrun处置（2026-11-08）

### A. 审查基线与范围

- 上游固定提交：`bd658e2d266e315d2ee35f985fb352ea88306b79`。
- 本节在§9.3.53、§9.3.55与§9.3.64基础上，进一步把VAL3同步任务周期、机器人型号采样周期、ros2_control更新周期、MoveIt Servo发布周期和movejSync刷新状态放在同一时序链路中核对。
- 另对照Stäubli CS9实时VAL3/Fieldbus技术文档TSS.000.014.04-A（2021-07-06）。该文件描述CS9扫描顺序、同步任务周期与overrun语义；其配置/固件适用性仍须以目标机器人实际版本和交付文档复核。
- 来源#1844–#1849。仅固定提交与配置的静态审查；未进行VAL3实时跟踪、周期抖动测量、CPU预算测量、控制器日志/状态采集、CS9 HIL或实机测试。

### B. 采样周期配置链

1. **默认三层均为4ms，但依赖人工维护。** VAL3 `start.pgx`将`l_nCtrlPeriod=0.004`并通过`taskCreateSync`创建controlTask；`controllers.yaml`的Controller Manager `update_rate=250`，即4ms；MoveIt Servo配置`publish_period=0.004`，即4ms。TX2-60L文档采样时间亦为4ms（250Hz），这组默认参数在名义周期上相互匹配。
2. **MR型号未自动继承更快采样周期。** `available_models.rst`将TX2-60L MR列为1ms（1kHz）机器人采样时间；同时说明当前VAL3 app默认250Hz，需要手动改`start.pgx`并同步修改ROS 2 control参数，文档仅指出MR在2ms（500Hz）下有成功测试记录。当前launch无基于`robot_model`选择不同Controller Manager rate的逻辑，仍加载同一份250Hz `controllers.yaml`；VAL3源码也固定4ms。因此选择MR型号并不会自动完成采样周期对齐。
3. **Servo发布周期是独立配置项。** 即使按文档将MR的VAL3周期和Controller Manager周期改成2ms，当前`staubli_servo.yaml`仍为4ms发布周期（low_latency_mode=false）。启用MoveIt Servo时，命令源仍按4ms节拍发布，而硬件更新循环可能为2ms；这不一定构成安全故障，但会改变每个硬件周期是否有新命令、插值/保持与端到端延迟，需要被明确设计和测试。文档要求同步调整ROS控制参数，却没有把Servo发布周期纳入型号适配清单。
4. **机器人伺服周期与VAL3/ROS周期不是同一参数。** MR机器人内部1ms采样、VAL3应用2ms测试周期、ROS控制器更新周期和Servo发布周期应分别记录；频率数值相同也不证明相位同步、时钟同步或每周期数据交换成功。需要指定允许的整数分频/倍频关系与端到端最大延迟，不得用单一`update_rate`代表完整控制链。
5. **启动时序没有执行周期配置一致性检查。** `start.pgx`读取VAL3版本并记录Boxcar delay，检查monitor speed低于100%时只告警并继续；未见对机器人型号采样时间、VAL3 task period、ROS update rate或Servo publish period进行协商/校验。Boxcar delay只被记录，没有在该程序中与控制周期或命令年龄预算形成计算关系。

### C. 单周期内的执行顺序与反馈延迟

1. `controlTask`每轮按固定顺序执行：检查上轮overrun标志→读取机器人状态→递增本机状态sequence→将上一轮`l_nSequenceDelay`写入状态→编码并发送RobotState→读取最多两次UDP命令→解码与计算序列延迟→校验命令模式/模式切换→调用位置/速度控制例程→处理错误→更新previous mode→`delay(0)`让出当前任务片段。
2. **状态发送早于本轮命令接收和运动更新。** 本轮RobotState中的物理状态由开头的`updateState()`取得，`nControlMode`和`nSequenceDelay`也在接收新命令前写入；当前轮随后接受的命令和`movejSync`更新，要到下一轮状态报文才反映其新的模式/运动结果。因此状态反馈是周期流水线，不是本轮命令执行后的同步确认；按默认4ms周期，单是这一调度顺序就引入最多一个控制周期量级的状态呈现滞后（实际端到端值仍需测量）。
3. **没有新UDP命令时仍使用上次有效命令。** `readData`未报错且本轮无新帧时，`controlTask`保留`robot_command_msg.robotCommand.bIsValid`，后续仍按该缓存命令模式调用运动例程；staleness分支与stream检查仍留有TODO。当前用状态sequence差和阈值间接检测旧命令，不是基于命令时间戳/lease的独立失效机制。
4. **接收队列单轮最多读取两次。** `readData`将`l_nMaxAttempts`固定为2；一次周期内至多调用两次`sioGet`，有新数据后再读到空缓冲区则退出。它不是排空直到无数据的循环，也没有对已读到的多个命令按时间戳/代际选取的显式策略；突发流量或生产速率持续高于消费速率时是否累积排队/扩大命令年龄需通过目标CS9 UDP行为和压力测试确认，不能仅凭静态代码断言已发生积压。

### D. movejSync刷新状态与overrun处置

1. **movejSync自身的刷新超时状态没有被上层升级。** `updateJointPositionControl`将`movejSyncState()==1`定义为movejSync仍在运行但上一命令未按时刷新；然而对应日志语句被注释，代码没有设置`x_bError`或转入停止分支。状态2被注释为因急停、moveHold或stopMove导致命令锁定，对应日志与错误设置也均被注释。当前仅`-2`会在本函数内明确触发stopJointPositionControl并返回错误。
2. `controlTask`另有基于sequence delay的阈值（运动中>5、静止时>25）可触发错误/STOP，但它与movejSync内部状态机是两条不同检测路径。movejSync状态1/2未被显式采纳，不能把sequence阈值视为已完整覆盖底层刷新超时和命令锁定状态。
3. **overrun被观测但不直接触发控制降级。** CS9文档说明同步任务每指定周期运行一次；若任务执行超过周期，当前周期结束，下一周期取消，并在后续执行周期通过创建任务时绑定的布尔值报告overrun。应用在controlTask循环顶部只记录日志、清除`bIsOverrun`并累加`nOverruns`，未因overrun本身设置错误、切换STOP或禁止继续提交运动参考。
4. **运行计数不会反映被取消的扫描次数。** 状态sequence在controlTask每次实际执行时才递增；被调度器取消的周期没有执行该递增语句。序列延迟以本机已执行的状态sequence和命令sequence作差，因而不能天然表示墙钟经过时间；overrun期间被跳过的扫描可能不体现在sequence差中，形成时间年龄低估。该机制性风险与§9.3.53相互关联，本节补充其对状态回报、刷新判定及周期配置对齐的影响。
5. `nOverruns`只在VAL3端计数，当前RobotState字段没有专用overrun计数/时间戳，诊断任务仍为TODO；故没有可见的ROS实时overrun遥测通道。日志/控制器文件可作为事后证据，但不能替代在线故障门控和可量化的连续性能指标。
6. **实时预算尚未建立。** Stäubli CS9文档说明CPU扫描顺序为系统同步任务、IO Refresh任务、VAL3同步任务、VAL3异步任务；同步任务每次最多执行3000行VAL3指令，且同步任务消耗较多CPU资源。3000行是任务序列执行行数上限，不是本应用的WCET、CPU利用率或4ms预算证明。当前controlTask把状态采集、序列化、UDP发送/接收、解码、日志、模式切换和运动命令刷新放在同一同步任务路径，没有分阶段耗时、最坏执行时间、余量或抖动统计。
7. `start.pgx`只在monitor speed低于100%时输出Warning，随后仍会创建同步控制任务；是否会影响该机型控制算法/性能必须按控制器配置测量，不能把warning等同于task周期已被强制保持或校验。

### E. 风险判断（静态推导，尚未复现）

- 对TX2-60L MR直接使用随附默认配置，会让1ms机器人采样时间与4ms VAL3/ROS/Servo名义节拍不同；手动修改其中一层后，其他层可能仍保留旧周期。
- 命令接收、模式改变、运动命令更新发生在本轮状态发送之后，ROS观察到的模式/运动反馈滞后于该轮输入；上层不能将同一轮状态帧当作本轮命令的执行确认。
- movejSyncState的刷新超时和锁定状态没有上升到控制任务错误门控；仅依赖另外一条sequence-delay路径不足以证明所有刷新异常都能触发STOP。
- overrun路径记录与计数但不立即门控运动；跳过的任务周期不会递增应用sequence，序列差不能代替真实elapsed-time watchdog。
- 没有执行时间分解和周期余量证据，无法从源码证明当前状态/通信/运动控制/日志在所有支持机型及I/O配置下都能满足周期deadline。
- 上述均为配置/源码与官方时序文档的组合分析，不表示本轮已经测得周期超限、发生movejSync刷新故障或机器人未停止。

### F. 整改建议

1. 将机器人型号及伺服周期、VAL3 task周期、Controller Manager更新率、MoveIt Servo发布率、DDS/UDP延迟预算组成版本化配置矩阵；启动时比对配置并拒绝未知/不兼容组合，避免仅依赖人工修改。
2. 对MR等不同伺服周期机型提供型号专用参数/launch配置；如果使用500Hz硬件更新，应同步评估并配置MoveIt Servo publish_period、JTC/Controller Manager以及下游VAL3周期；明确2ms测试结果不等于1ms全链路运行已验收。
3. 定义命令接收与状态回报的周期相位：增加命令sequence/epoch、执行接受/拒绝状态、状态采样sequence与实际采样时间；明确当前周期先发状态后处理命令的流水线延迟。
4. 对movejSyncState==1与==2建立明确、可验证的状态机：刷新超时按安全要求转入错误/停止或受控降级；命令锁定必须识别E-stop/Hold/stopMove来源并禁止继续误报正常刷新，恢复需重新验证运动许可。
5. overrun应进入独立安全策略：至少记录真实遗漏周期数/时间、停止或禁止提交陈旧运动命令、要求重新同步；不能只清除布尔值后继续照常运行。在线遥测需暴露overrun计数、最近事件时间、连续事件和任务执行余量。
6. 以单调时间或控制器真实时钟测量接收、解码、状态采样、发送和运动API阶段耗时；将sequence差仅作为辅助计数，不作为唯一的墙钟命令年龄证明。
7. 建立WCET/周期预算和压力工况矩阵，覆盖最大I/O刷新配置、网络正常/异常、日志节流、最坏状态数据量、运动命令、overrun连续发生以及不同CS9硬件/固件版本；记录高分位与最坏值并保留deadline margin。
8. 明确controlTask创建/应用停止/重启的任务生命周期：验证停止流程是否终止同步任务、socket和运动调用是否存在在途执行；通过taskStatus/受控任务终止与资源屏障确认无旧任务跨重启运行。

### G. 新增验收任务（均未执行）

| 编号 | 验收项 | 通过标准 | 验收证据 | 状态 |
|---|---|---|---|---|
| SERVO-283 | 型号/VAL3/ROS/Servo周期矩阵 | 每个支持型号都有完整周期与分频关系，启动配置自动校验 | 机型参数矩阵、启动负向测试 | 未执行 |
| SERVO-284 | TX2-60L MR默认配置适配 | MR型号不再静默沿用不匹配的默认周期；1ms/2ms方案和限制明确 | MR配置测试、目标控制器测量 | 未执行 |
| SERVO-285 | MoveIt Servo周期联动 | 修改硬件/VAL3更新率时，Servo publish_period同步配置或显式验证分频 | ROS graph与端到端频率跟踪 | 未执行 |
| SERVO-286 | movejSync刷新超时状态1门控 | 状态1触发明确告警/停止/降级，不继续当作正常刷新 | 刷新延迟故障注入与运动记录 | 未执行 |
| SERVO-287 | movejSync锁定状态2门控 | E-stop/Hold/stopMove下状态2被识别，恢复需重新授权 | 安全模式/锁定状态矩阵 | 未执行 |
| SERVO-288 | overrun安全处置与在线遥测 | overrun可锁存、计数、测时并触发批准的门控策略 | 连续overrun注入与ROS诊断记录 | 未执行 |
| SERVO-289 | 漏失扫描的墙钟年龄计算 | 任务overrun/跳周期不会低估命令真实年龄 | 可控周期跳变和时钟/序列对照 | 未执行 |
| SERVO-290 | 状态/命令流水线延迟 | 状态sequence、命令接收、模式提交和运动API时间线可关联，最大滞后有预算 | 报文抓包与控制器时间戳跟踪 | 未执行 |
| SERVO-291 | CS9控制循环WCET与抖动 | 最坏工况下阶段耗时、周期余量及连续运行deadline符合批准指标 | CS9实时跟踪、压力测试及报告 | 未执行 |
| SERVO-292 | VAL3同步任务停止/重启屏障 | 应用stop/重启后无旧controlTask继续访问socket或运动API | task状态跟踪、反复启停故障注入 | 未执行 |

### H. 本节来源记录（#1844–#1849）

| 编号 | 固定来源 | 用途 |
|---|---|---|
| #1844 | [VAL3 start.pgx @ bd658e2](https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/val3/userapp/ros2_server/start.pgx)；[stop.pgx @ bd658e2](https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/val3/userapp/ros2_server/stop.pgx) | task period、taskCreateSync、monitor speed、Boxcar delay及应用停止逻辑 |
| #1845 | [VAL3 controlTask.pgx @ bd658e2](https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/val3/userapp/ros2_server/controlTask.pgx) | 单周期执行顺序、状态先发/命令后收、overrun处理、序列和STOP逻辑 |
| #1846 | [VAL3 updateJointPositionControl.pgx @ bd658e2](https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/val3/userapp/ros2_server/Control/updateJointPositionControl.pgx) | movejSync状态1/2/−2与刷新处理 |
| #1847 | [controllers.yaml @ bd658e2](https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_bringup/config/controllers.yaml)；[staubli_servo.yaml @ bd658e2](https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_moveit_config/config/staubli_servo.yaml) | ROS Controller Manager与MoveIt Servo周期配置 |
| #1848 | [available_models.rst @ bd658e2](https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_driver_ros2/sphinx/quickstart/available_models.rst) | TX2-60L 4ms、MR 1ms、MR 500Hz测试说明 |
| #1849 | [Stäubli CS9 Real Time Val3/Fieldbus TSS.000.014.04-A (2021-07-06)](https://bvdp.inetdoc.net/files/iut/staubliiut/doc/Real%20Time%20Val3-Fieldbus%20Synchronization%20TSS00001404A.pdf) | CS9单scan任务顺序、同步任务周期、3000行限制与overrun跳过下一周期的厂商技术说明 |
