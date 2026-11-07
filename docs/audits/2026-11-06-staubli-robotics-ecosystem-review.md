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
