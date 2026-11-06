# Universal Robots（UR）软件与 ROS 2 生态静态审查（2026-11-06）

> 审查范围：PolyScope 5 / PolyScope X、URCap / URCapX、URScript、ur_robot_driver、ur_client_library、URSim、ros2_control、URInterfaces及协作机器人安全边界。  
> 审查类型：官方网页、官方文档和官方公开仓库静态审查；不构成目标型号采购选型、软件构建验收、实机验收或整机安全认证。  
> 对应任务：根任务00-01；第21章21-02。  
> 来源：链接台账#1422–#1436。

## 1. 产品与软件平台边界

- UR官方当前产品页和驱动README涵盖CB3、e-Series及UR Series；ROS 2驱动README的模型列表包括ur3/ur3e、ur5/ur5e、ur7e、ur10/ur10e、ur12e、ur16e、ur8long、ur15、ur18、ur20、ur30，以及g-series ur10g-1750、ur17g-1300、ur18g-950。2026-11-06主分支新增g-series启动支持；该新增提交仍需按发行分支、包版本、模拟器镜像和实际控制器验证，不可仅凭main README将所有型号认定为同一软件基线。来源#1422。
- 控制器代际必须区分CB3 / PolyScope 3、CB5 / PolyScope 5和PolyScope X / PolyScope 10。软件接口、URCap包格式、Robot API / Dashboard、URScript和RTDE变量均有代际差异；“支持UR机器人”不是充分的兼容规格。来源#1423、#1434。
- 驱动仓库当前main HEAD固定为`e55b899066caffbceda80662d63b61c80f56719a`（2026-11-06 08:30 UTC，新增g-series launch支持）；`ur_robot_driver/package.xml`版本字段为7.2.0，BSD-3-Clause。main HEAD晚于7.2.0版本提交（2026-10-20），因此7.2.0包版本不能代表main所有最新代码。来源#1422。
- 仓库README列出Humble、Jazzy、Kilted、Lyrical和Rolling分支/ROS buildfarm状态入口；Foxy、Galactic、Iron明确标为EOL。发行版分支存在、CI badge存在或源码可编译均不等于目标操作系统/控制器固件/机器人SKU的官方产品级支持。驱动要求Linux，不支持其他OS。来源#1422。
- ROS 2 driver仓库包含`ur` meta-package、`ur_calibration`、`ur_controllers`、`ur_dashboard_msgs`、`ur_moveit_config`和`ur_robot_driver`；控制库`ur_client_library`独立维护并作为ROS 2驱动底层。不要把URDF/MoveIt配置、控制器接口、控制器端软件和SDK视作同一层。来源#1422、#1433。

## 2. 三条ROS 2集成路线必须分开

### 2.1 PolyScope X控制器内置ROS 2

- PolyScope X 10.7起提供控制器内置ROS 2节点和URScript ROS接口；它可以发布机器人状态、提供部分服务/I/O接口，并允许URScript发布/订阅topic、调用服务和action。此路线不是外部`ur_robot_driver`的替代品，也不等同于控制器开放完整ROS 2应用开发权限。来源#1428。
- PolyScope X v10.7文档说明控制器运行ROS 2 Humble；截至本次检索，PolyScope X v10.15文档说明控制器已运行ROS 2 Jazzy、默认Fast DDS。必须按准确PolyScope版本选择对应ROS消息库、RMW/DDS、QoS和接口版本；不可把10.7的Humble结论套用到10.15，也不可假设跨发行版DDS互通没有风险。来源#1428。
- `urinterfaces`是UR自定义ROS 2消息类型库；官方说明每个公开PolyScope版本对应一个tag，底层ROS发行版升级可能引入不兼容变化。同一ROS 2版本下承诺保持向后兼容的范围不能外推至ROS发行版切换。应把PolyScope、urinterfaces tag、ROS distro和消息定义一起锁定。来源#1429。
- PolyScope X ROS 2 QoS必须核对publisher/subscriber兼容；默认profile含Keep Last、depth 1、Reliable、Volatile等策略，QoS不兼容会导致通信失败。应逐topic确认频率、QoS、命名空间、ROS_DOMAIN_ID、防火墙和跨网段发现，不能只用`ros2 topic list`成功作为端到端通信验收。来源#1428。
- v10.15文档为当前本次核对的版本快照；较早v10.7/v10.12页面明确提示已过时。文档内容和实际设备固件应以目标机器人随附版本和受控发布资料为准。来源#1428。

### 2.2 外部ROS 2 + ur_robot_driver

- UniversalRobots/Universal_Robots_ROS2_Driver是UR维护的开源驱动，使用`ros2_control`和`ur_client_library`；README声明覆盖CB3、e-Series、PolyScope X，提供MoveIt集成和UR专用控制器。该范围是仓库声明，目标型号仍需与具体发行分支、控制器软件和控制柜版本交叉核对。来源#1422。
- 驱动支持Teach Pendant模式与Headless模式；机器人Local/Remote control是另一组控制模式。Teach Pendant模式需安装External Control URCap并由示教器启动程序；Headless模式需启用Remote Control，e-Series及更新平台不能把本地模式当作Headless前提。示教器触发运动相关操作或另一个程序被加载，可能终止当前External Control程序，需按文档恢复。来源#1423。
- Teach Pendant模式的script_sender_port默认50002，必须与URCap连接配置和ROS主机IP一致；网络隔离、路由、端口防火墙、机器人入站连接安全设置需核验。不要为了“连通”而无差别开放所有控制器端口。来源#1423。
- `scaled_joint_trajectory_controller`将机器人速度缩放（示教器speed slider、安全限速、保护停机/程序暂停等）纳入轨迹进度；`passthrough_trajectory_controller`将完整轨迹交给机器人控制器插补，降低ROS PC实时要求；`motion_primitive_forward_controller`把moveJ/moveL/moveC等运动原语交由控制器执行。运动控制器争用相同硬件命令接口时互斥，必须保证单一活动命令控制器。来源#1424。
- Streaming position/velocity/twist控制不等同于规划轨迹执行。上游文档明确用户必须保证命令安全且可达；速度安全缩放不会像轨迹控制器一样自动补偿，应用必须监控speed_scaling并处理限速，否则轨迹时间/目标点可能偏离。来源#1424。
- Force/torque路径包括关节effort/直接扭矩控制、Cartesian force_mode、摩擦补偿和重力向量更新。直接扭矩控制要求PolyScope 5.23.0 / PolyScope X 10.10.0及以上；关节扭矩状态读取要求PS 5.23.0 / PSX 10.11.0及以上。旧版本effort可能报告电机电流而不是关节扭矩；需核对`actual_current_as_torque`和`use_currents_as_efforts`参数。URSim对effort控制没有真实机器人等效效果。来源#1425、#1427。
- Force/Torque传感器为相对传感器，官方建议在force mode前、工具接触环境前执行zero；不能把其输出直接当作经过绝对力标定的计量数据。tool_contact功能与安全额定保护装置不是同一概念，必须按应用功能和安全手册边界使用。来源#1425。
- 校准信息应从真实机器人提取并保存到目标配置。官方明确未提取校准时，ROS侧末端位姿可能出现厘米量级误差；该步骤虽不是驱动启动的硬性条件，却是准确TCP/视觉标定/碰撞检查的工程前置。每台机器人、每次更换控制器/关键校准数据后应保留校准文件及哈希。来源#1426。
- 仿真路径包括官方URSim（CB3、PolyScope 5、PolyScope X Docker镜像）、ros2_control MockSystem及Gazebo/GZ Sim。Mock仅验证接口管线和控制器描述；URSim更接近控制器软件行为，但不是机械臂真实动力学/安全回路/负载工况的HIL替代。文档列出mock若干功能不工作（TCP pose broadcaster、passthrough trajectory、force mode、GPIO状态验证）；URSim effort命令也不产生真实机器人等效动作。来源#1427。

### 2.3 独立C++ ur_client_library

- `ur_client_library`提供远程C++接口，驱动可访问RTDE、Dashboard/Robot API、Primary、Reverse Interface、Script Sender、Trajectory Point Interface等；它是协议/通信库，不是ROS 2硬实时调度器或功能安全控制器。来源#1433。
- README称RTDE接口完整支持，而PrimaryClient仅实现部分功能；不能把“Primary接口可连接”推断为所有Primary消息已解析/支持。该库要求CB3 PolyScope >=3.14.3、e-Series >=5.9.4、PolyScope X >=10.7.0；更老版本需要回退到兼容tag。来源#1433–#1434。
- PolyScope X与PolyScope 5能力不完全对等：Dashboard Server在PSX由Robot API逐步替代；10.11提供状态控制及程序加载/播放，10.12扩展程序管理与模式信息，10.14增加弹窗、机器人信息、系统控制和日志等；接口能力须按具体PSX版本核对。来源#1434。
- PolyScope X External Control使用独立URCapX，不应沿用PolyScope 5的`.urcap`安装包。当前ExternalControl_URCapX README列明10.8.0及以上要求；10.7仅可用0.1.0；兼容表显示10.15与1.2.x组合为支持项，且不同版本之间并非全兼容。GitHub Releases页面显示1.2.0为Latest，不能将“URCapX可安装”推断为URSim、驱动和真实控制器组合已经验收。来源#1431–#1432。
- PolyScope X SDK 0.22文档说明URCap以`.urcapx`打包，支持自定义Program Node、Application Node和Docker container contributions；样例包含RTDE、ROS 2 node、serial device、REST/WebSocket、gripper等。构建过程使用Node/NPM，容器贡献在ARM64开发环境中默认产物可能是AMD64镜像，必须显式处理目标架构和容器manifest。来源#1430。

## 3. 控制器、安全和系统集成边界

- ROS driver能读取机器人安全模式、运行模式、External Control程序状态和速度缩放；这些状态有助于应用诊断与轨迹同步，但普通ROS topic/action/service不是安全额定信号通道，不得作为唯一急停、防护停机、人员检测或安全复位链。来源#1423–#1425。
- UR官方安全FAQ（2026-05-06更新）声明其机器人安全功能经TÜV评估/认证为PL d Category 3，并说明机器人本体与完整应用的标准/责任边界；该网页对ISO 10218-1:2025认证仍写为计划于2027-01推进，不能将计划写成已经取得的证书或新标准合规。证书原件、具体机器人型号、控制柜、PolyScope版本和地区声明仍需逐项核验。来源#1436。
- UR官方风险评估手册明确机器人是部分完成机械，集成方负责应用风险评估，需考虑末端工具、工件、障碍物、相邻设备、教学/维护/故障排除及正常运行等全生命周期工况；必须按ISO 12100与ISO 10218-2评估并决定安全配置和额外防护。协作机器人身份不意味着整站免围栏或免风险评估。来源#1435–#1436。
- 对UR安全功能的实际使用必须依据准确型号的Safety Manual、控制柜/安全I/O/外部保护设备连接图、已验证的安全配置备份、风险评估和停止时间/距离测试；不能用ROS驱动中的speed scaling、tool_contact或软件限位替代安全PLC、急停回路或安全额定保护设备。

## 4. 软件供应链、许可和版本冻结

| 组件 | 本轮确认快照 | 许可证/状态 | 主要限制 |
|---|---|---|---|
| ur_robot_driver | main HEAD `e55b899066caffbceda80662d63b61c80f56719a`；package.xml 7.2.0 | BSD-3-Clause；UR维护 | main HEAD晚于7.2.0 release commit；按分支/包版本/型号核验 |
| ur_client_library | main HEAD `c094c990c8a225f22854eefa0f8b53c4ebfd8b45` | Apache-2.0为主，第三方queue/semaphore有BSD-2-Clause/zlib声明 | Primary接口不完整；PSX与PS5功能不完全对等 |
| ExternalControl URCapX | README兼容矩阵含0.1.0/1.0.0/1.1.0/1.2.x；Releases Latest 1.2.0 | 需逐组件核对URCapX包和前端/后端依赖 | PSX 10.7只支持0.1.0；10.15表列1.2.x；不同版本不能混装 |
| PolyScope X内置ROS 2 | v10.7/Humble；v10.15/Jazzy | 控制器随版本提供 | urinterfaces tag、QoS、DDS、ROS_DOMAIN_ID和消息ABI需锁定 |
| PolyScope X SDK | 文档快照0.22 | 官方SDK/URCap开发工具 | Docker容器目标架构、Node/NPM依赖和模拟器版本需锁定 |

- 驱动README声明BSD-3-Clause；Client Library README声明主体Apache-2.0并标注队列/信号量第三方组件许可证。ExternalControl URCapX仓库需单独检查其LICENSE、npm lockfile和生成SBOM；不能仅凭driver许可推断所有URCap/SDK/容器依赖许可相同。来源#1422、#1430–#1433。
- 每个项目需锁定ROS distro、Ubuntu版本、内核、RMW/DDS、ros2_control、MoveIt、驱动branch/tag/commit、ur_client_library commit、URCap/URCapX版本、PolyScope版本、机器人型号、控制柜代际和固件；对main与正式Release差异建立明确变更记录。

## 5. 工程准入与待补证

1. 冻结机器人型号/序列号、CB3/CB5.0–5.6、PolyScope 3/5/10完整版本、UR Series/e-Series/g-series具体SKU、软件选件、末端工具和安全配置。
2. 建立型号—控制柜—PolyScope—URCap/URCapX—ROS distro—driver release—client library tag的兼容矩阵；核验main中新g-series型号的发行版和URSim支持证据。
3. 在目标Ubuntu/ROS distro上分别构建驱动release与main snapshot，保留colcon日志、依赖锁、包来源、编译器/内核、CI结果、SBOM和许可证扫描。
4. 对真实机器人提取并复核kinematics calibration，验证TCP、tool frame、base frame、joint offsets、payload/CoG、URDF和控制器配置一致。
5. 分别验证Teach Pendant/Headless/Local/Remote模式切换、程序抢占/重启、Remote Control权限、网络中断、RTDE超时、控制器重启、急停/保护停机后状态恢复和命令残留。
6. 对joint trajectory、passthrough、motion primitives、streaming position/velocity/twist、force mode、direct torque、freedrive、GPIO和tool contact分别执行仿真、SIL、HIL和实机测试；记录周期、抖动、延迟、轨迹误差、速度缩放、停止时间、负载与温升。
7. 对PolyScope X内置ROS 2测量topic频率、端到端延迟、QoS匹配、DDS发现、CPU负载、ROS_DOMAIN_ID隔离和跨网段行为；检查URScript调用ROS API时的阻塞和程序周期影响。
8. 按目标应用完成ISO 12100风险评估、ISO 10218-2整机集成验证、功能安全回路验证和当地法规合规；获取适用的TÜV证书/声明、Safety Manual和配置备份。
9. 核验g-series、CB7、URCapX 1.2.x、PolyScope 10.15与UR driver 7.2.0/main的真实型号组合；将README、文档站、Release、ROS buildfarm、URSim镜像之间的版本差异登记为兼容性问题。

## 6. 本轮未执行事项

未下载或安装PolyScope、URSim、URCap/URCapX或SDK；未构建ROS 2驱动/client library；未运行mock/URSim/Gazebo；未连接真实UR机器人、控制柜、末端工具、PLC或安全回路；未采集真实机器人校准文件；未测通信周期、抖动、WCET、轨迹误差、力控误差、停止时间/距离、故障恢复或网络安全；未执行HIL/FAT/SAT/功能安全验收。故本档案仅为公开资料静态审查，工程验证与供应商资格审查均未完成。
