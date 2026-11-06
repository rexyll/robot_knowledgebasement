# Doosan Robotics（斗山机器人）软件与 ROS 2 / DRFL 生态静态审查（2026-11-06）

> 审查范围：DART-Suite / DART-Platform / DRL / DRFL / DRCF v2-v3、Doosan ROS 2 Driver（Humble/Jazzy）、ros2_control、MoveIt 2、Gazebo Harmonic、MuJoCo、实时UDP控制及安全功能。  
> 审查类型：官方公开文档、官方GitHub仓库与代码静态审查；不构成目标型号兼容认证、驱动构建验收、真实机器人实时性验收或整机安全认证。  
> 对应任务：根任务00-01；第21章21-02。  
> 来源：链接台账#1438–#1452。

## 1. 机器人产品族与功能差异

- Doosan官方ROS 2文档将机器人族分为A/M/H/E/P系列，并声称ROS 2 Humble与Jazzy驱动覆盖全部系列；具体型号、控制柜、DRCF固件和选件仍须按SKU确认，不能把系列覆盖声明直接视为所有型号的全部功能均相同。来源#1439–#1440。
- 各系列力/扭矩传感基础不同：A/E主要使用关节电机电流；A-S系列增加末端FTS（Force Torque Sensor）；M/H/P系列采用关节扭矩传感器JTS。直接示教、约束示教、碰撞检测、安装姿态测量、工具/工件重量测量、力控和柔顺控制的可用性存在系列差异。尤其A/E的force/compliance在官方表中受限于平移方向，不能将M/H/P的六轴能力外推到所有型号。来源#1445。
- 官方目录和手册分别列出A/As/E/M/H/P系列及型号配置；采购前需核对机器人本体、控制柜、传感器版本、末端工具、额定负载/重心和安装姿态，不以系列名称推断选件或安全功能。

## 2. DART软件生态与开发路径

- DART-Suite由DART-IDE、DART-SDK、DART-Store、DART-Platform和开发者/论坛等服务组成；DART-IDE用于开发机器人应用模块，DART-SDK提供DART API和User Component，DART-Store用于上传/分发模块，DART-Platform 3负责安装和执行模块。OTA在早期产品资料中曾标为Coming soon，实际状态须核对当前产品版本/地区。来源#1450。
- DART-Platform是Windows桌面端/示教器侧机器人操作软件；官方手册说明连接控制器后可访问示教器功能。DART-Platform 3采用模块化Store机制，部分TCP/Modbus/工业以太网/串口模块需从Store另行安装，不能把传统平台内置模块清单套用到所有版本。来源#1451。
- DART Developer LAB提供Web App Builder，合作伙伴开发者可配置I/O、Skill和Task Template并在DART-Simulator中测试；提交Doosan审核后可能取得Doosan Mate认证。此App Builder、DART-SDK、DRL程序、ROS 2 Driver和DRFL C++ API是不同开发层，不应混为同一个SDK。来源#1452。
- DRL是机器人控制器侧编程/任务语言；官方API/编程手册还提供TCP客户端/服务端、Modbus、工业以太网和设备模块集成。设备模块是否预装/需下载取决于DART-Platform版本和模块授权。来源#1451。

## 3. ROS 2 Driver：Humble与Jazzy两条维护分支

### 3.1 发行版与仓库快照

- 官方仓库`DoosanRobotics/doosan-robot2`存在`humble`和`jazzy`两个分支。Humble README声明ROS 2 Humble，Jazzy README声明ROS 2 Jazzy；官方手册分别要求Ubuntu 22.04/Humble与Ubuntu 24.04/Jazzy，并都要求虚拟DRCF emulator使用Docker。不可将Humble依赖包、Gazebo Classic/旧Ignition依赖和Jazzy/Gazebo Harmonic依赖混装。来源#1438–#1441。
- 本轮检索到仓库默认Humble分支最新提交为`d276f9f9712118a18bad1d9ee1d7d4eab10a4ea8`（2026-11-02，修复连接失败后关闭连接再重试）；最近release提交为`5638b8ca34a8c077d64ef5163f7ccef42bc42323`（2026-10-30，release 20261029）。Jazzy分支存在，但本次未获得可核验的分支HEAD commit SHA，因此不伪造其快照SHA。来源#1438。
- ROS 2软件栈包含`dsr_bringup2`（启动/编排）、`dsr_common2`（DRFL通信与工具）、`dsr_controller2`（ROS controller插件）、`dsr_description2`（URDF/Xacro/mesh/SRDF）、`dsr_hardware2`（ros2_control SystemInterface）、`dsr_msgs2`（Doosan自定义消息/服务）、`dsr_moveit_config_* `、`dsr_gazebo2`、`dsr_mujoco`和`dsr_tests`。这些包各自承担不同职责，需逐包锁定版本。来源#1440。
- Humble分支示例package.xml版本：`dsr_controller2 2.33.0`、`dsr_description2 1.1.0`、`dsr_bringup2 1.1.0`，而`dsr_hardware2`仍标`0.0.0`；包版本字段不等于整体驱动release版本。Jazzy迁移文档明确硬件层从ControllerInterface迁移至SystemInterface，且采用生命周期钩子、动态DoF和新的参数映射。来源#1440–#1441。
- Jazzy迁移文档列出重要不兼容点：DRCF >=3.0使用`rt_host`而不是仅使用`host`；RT输出配置和启动函数仅在真实机器人模式执行、模拟器不支持；监控回调由硬件层管理；SRDF robot name必须与URDF name精确匹配；ROS 2 Jazzy的xacro不接受旧式原始`{2*pi}`表达式。迁移时需按官方说明改造，不能只替换ROS_DISTRO。来源#1441。

### 3.2 硬件接口与命令语义

- `dsr_hardware2`在Jazzy分支实现`hardware_interface::SystemInterface`，从DRFL读取机器人状态并向控制器发送关节命令；源码中真实模式调用`read_data_rt()`读取实时UDP数据，虚拟模式从DRCF emulator读取姿态。来源#1440–#1441。
- 代码为真实模式配置DRFL RT输出版本`v1.0`、周期`0.001 s`、丢包容忍参数`losscount=4`，经UDP 12347建立RT连接；真实控制器上执行`servoj_rt`。虚拟模式不建立RT UDP通道，而调用`amovej`。因此模拟器的成功启动不能证明真实RT数据通道、1kHz控制或实机运动性能。来源#1441、#1444。
- DRCF v3的RT网络地址与DRCF版本相关：官方迁移文档要求DRCF >=3.0使用`rt_host`；驱动源码注释区分v3.0–3.3默认RT IP与v3.4之后的寻址行为。必须按控制器固件/网络拓扑配置host和rt_host，不能固定套用一个IP。来源#1441。
- 真实模式`write()`按controller_manager周期过滤异常dt：仅接受目标周期的0.3–1.5倍窗口；超窗周期跳过写命令。代码以实际循环间隔乘以margin生成servo_time，并在位置命令变化时调用`servoj_rt`。这意味着controller_manager频率、Linux调度、CPU负载、网络延迟和RT UDP周期之间存在耦合，必须测量真实抖动、丢周期、命令延迟和故障响应。
- 源码导出position、velocity、effort等接口，但effort状态/命令路径标有TODO；velocity路径也标有TODO支持说明，且write路径以位置命令变化作为触发门控。接口被导出不代表每种command mode均已完整实现；需通过`ros2_control`接口激活、实际轨迹和故障测试逐一确认。来源#1441。
- 驱动读取RT数据时包含时间戳不变/陈旧数据检测，但该逻辑不能替代通信失联后的安全状态机、控制器侧watchdog、外部安全回路或独立故障注入验证。源码注释中的周期过滤和stale detection属于软件健壮性措施，不是功能安全认证。来源#1441。

## 4. DRFL C++ API与实时外部控制

- `API-DRFL`是Doosan Robot Framework Library的公开C++接口仓库；README说明DRFL支持Windows与Linux，x86为主要架构，Arm64仅支持Linux。仓库中的`.a/.dll`是示例版本，README要求从RobotLab下载当前版本；因此ROS工作区中预置的静态库不能不经核验就视为最新DRFL。来源#1443。
- 本轮GitHub仓库最新提交为`2ff5f7d4c363d05592b140813e71cecf051b4a24`（2026-11-04，release GL013305/v1.33.5），而当前公开API文档页面检索到GL013304/v1.33.4。需要确认1.33.5与文档1.33.4之间的API/行为变化，避免把旧文档直接当成新库的精确契约。来源#1443–#1444。
- DRFL RT Control是独立UDP/IP接口，与普通TCP/IP API分开；官方说明RT通道最高可配置到1kHz，并提供`servoj_rt`、`servol_rt`、`speedj_rt`、`speedl_rt`和`torque_rt`等命令。普通TCP监控频率较低：DRCF v2及DRCF v3<3.5约10Hz，DRCF 3.5及以后约50Hz。不要把TCP监控频率当作RT UDP采样频率。来源#1444。
- 官方实时示例采用1ms周期、五次多项式轨迹和Linux/Pthread或Xenomai实时线程；示例要求真实机器人IP，RT监控/控制不支持模拟器；每台控制器同一时间只允许一个RT UDP客户端。示例中的SCHED_FIFO高优先级线程配置不是WCET或硬实时验收证据。来源#1445。
- `start_rt_control()`只表示启动请求已发送，不等待控制器确认；控制器拒绝可能通过RT日志回调上报。应用必须注册常规log alarm和RT log alarm、监控控制器状态/序列号/时间戳、实现超时和断线策略，不能把函数返回true当作命令已执行。来源#1444–#1446。
- `servol_rt`为异步命令：返回1只表示UDP数据报已发送，不保证控制器接收/应用。官方文档指出通信延迟或网络抖动会导致运动顿挫；`fTargetTime`是目标插补时长，不是发送周期；DRCF v2.12.x/v3.3.x最小值0.001s，DRCF v3.4.0及以后小于0.025s的值会被提升至0.025s，且命令持续时间变为`fTargetTime + 0.005s`。`servol_rt`当前实现不与Operation Speed [%]关联，且与force/compliance control或奇异点附近的DR_VAR_VEL不兼容。所有这些行为必须按目标DRCF版本验证。来源#1446。
- DRFL仓库README和静态库版本应与控制器固件DRCF v2/v3配对；ROS 2构建参数`-DDRCF_VER=3`切换API兼容宏，但不能替代真实控制器软件版本检测、头文件/静态库一致性核验和网络测试。来源#1438、#1443–#1446。

## 5. DRCF模拟器、Gazebo与真实机器人验证边界

- DRCF虚拟模式由Docker emulator提供，ROS 2手册示例默认TCP host 127.0.0.1、端口12345；真实模式示例默认控制器地址192.168.137.100、TCP端口12345。虚拟模式下每台机器人启动独立emulator实例，多机器人必须区分namespace、端口和Gazebo位姿；Jazzy README提示每个emulator实例需4个专用CPU核，CPU资源不足会影响模拟稳定性。来源#1438–#1440。
- 官方API手册明确虚拟模式只逻辑模拟运动、I/O和安全状态，不产生真实力矩/电流/反馈；力/扭矩和柔顺API返回模拟数据，数字/模拟I/O与Modbus不会驱动真实设备；实时控制仅支持真实机器人。不能用模拟器验收力控、负载估计、校准、1kHz RT或安全回路。来源#1447。
- Gazebo Harmonic用于动态仿真和规划/碰撞场景；MoveIt 2需控制器版本>=2.12。MuJoCo是另一独立仿真包。三种仿真器与DRCF emulator的控制接口、动力学模型、I/O和安全语义不同，不能统称为“与实机等价仿真”。来源#1439–#1440。
- 推荐验证层级：静态URDF/SRDF/模型映射→Mock/launch测试→DRCF emulator→Gazebo/MuJoCo动力学场景→真实机器人低速单步→真实RT UDP/力控/IO→PLC/外设HIL→FAT/SAT/停止时间距离和安全功能验证。每一级只能证明其实际覆盖的属性。

## 6. 安全功能与型号边界

- Doosan官方手册列出安全停止类型STO、SS1、SS2及碰撞反向恢复RS1；急停和保护停机的触发端、允许停止模式和复位流程不同。急停通过示教器或外部急停端子触发；保护停机由连接到Protective Stop端子的外部保护设备触发。来源#1448。
- P系列Safety-rated Monitoring Function页面列出SOS、SLP、SLS、SLT、Collision Detection、TCP/Robot Position、TCP Orientation、TCP Speed、TCP Force、Momentum和Power等安全监控功能，并在该P系列页面给出PL d Category 3 / SIL 2及PFHd数值。该证据仅支持该页面对应的P系列/手册版本范围；不得未经型号级安全手册/证书核验外推到A/E/M/H系列或所有控制器代际。来源#1449。
- 安全限值触发后实际停止位置/外力可能超过设置阈值；需按手册核验停止时间/距离、外部安全设备、工具/工件、碰撞风险和保护区。ROS安全状态topic、DRFL回调、RT UDP和普通I/O不是安全额定保护链。来源#1448–#1449。
- M/H/P的JTS、A-S的FTS、A/E电流估算机制会影响碰撞检测、力控、柔顺控制、负载识别和示教功能。应按准确型号和传感器类型选用API，不能仅凭“Doosan支持force control”做通用结论。来源#1445。

## 7. 许可证、软件供应链与版本冻结

| 组件 | 本轮确认快照 | 公开许可/版本声明 | 待核风险 |
|---|---|---|---|
| doosan-robot2 Humble | 默认分支最新提交d276f9f（2026-11-02）；release提交20261029 | Humble README同时出现Apache-2.0与BSD-3-Clause徽章；根LICENSE为BSD-3-Clause；部分package.xml标BSD、部分Apache | 文件级/包级许可声明不完全一致，需逐文件清单 |
| doosan-robot2 Jazzy | jazzy分支存在；README blob SHA 644b6d… | 根LICENSE为Apache-2.0；多个package.xml标Apache-2.0 | 不应将Humble分支的LICENSE判断直接套到Jazzy |
| API-DRFL | main HEAD 2ff5f7d（2026-11-04，GL013305/v1.33.5） | 仓库LICENSE为BSD-3-Clause；README称仓库内库文件为示例版本 | RobotLab下载的最新DRFL静态库、二进制再分发条款和版本需另行核验 |
| ROS 2 docs | Humble/Jazzy均有独立手册 | 文档版本v1.0 | API文档GL013304/v1.33.4与API-DRFL release v1.33.5有版本差异 |
| DART-Suite / DART-SDK | DART-Platform 3、IDE、Store、SDK及Developer LAB | 商业/开发者服务和模块商店 | SDK/模块许可、Store依赖、认证和OTA服务状态需按合同/地区确认 |

- Humble分支根LICENSE为BSD-3-Clause，但README徽章同时出现Apache-2.0/BSD-3-Clause，package.xml又存在BSD与Apache混用；Jazzy分支根LICENSE和相关package.xml则声明Apache-2.0。此处只记录公开声明不一致，不做法律解释；发布或二次分发前必须完成逐文件/第三方组件/静态库许可证审查。来源#1438、#1443。
- `dsr_common2/CMakeLists.txt`按`ROS_DISTRO`和`x86_64/arm64`选择预编译`libDRFL.a`，README又将仓库中的二进制称为示例版本；应锁定DRFL header、静态库、Poco依赖、ROS distro、架构、编译器和DRCF固件，保存SHA/SBOM/许可证清单。来源#1438、#1443。

## 8. 工程准入与待补证

1. 冻结机器人型号/序列号、A/As/E/M/H/P系列、末端FTS/JTS/电流传感器类型、控制柜/集成控制器型号、DRCF v2/v3完整固件、示教器/DART-Platform版本和地区。
2. 固定doosan-robot2的Humble/Jazzy分支commit、包版本、ROS distro、Ubuntu版本、ros2_control/MoveIt/Gazebo/MuJoCo版本；核对Jazzy迁移差异和真实模型列表。
3. 固定API-DRFL release/commit、DRFL header与libDRFL.a哈希、架构、Poco版本及DRCF_VERSION编译宏；确认RobotLab下载库的许可/再分发边界。
4. 审查URDF/Xacro/SRDF、关节数量/映射/方向/零位、joint limits、工具/用户坐标、payload/CoG、FTS/JTS标定、碰撞几何和机器人模型对应关系。
5. 测量controller_manager周期、read/write耗时、1kHz RT UDP周期/抖动/WCET、丢包/重传/数据时间戳、stale detection、watchdog、RT控制权争用和断线恢复。
6. 验证`servoj_rt`/`servol_rt`的插补时间、最小fTargetTime、网络抖动、速度/加速度限制、Operation Speed联动、奇异点、force/compliance兼容性及异步命令拒绝路径。
7. 对真实机器人验证控制权移交、Servo On/Off、急停/保护停机、STO/SS1/SS2/RS1、外部安全I/O、复位权限、停止时间/距离和安全参数锁定。
8. 按型号核验PL/SIL/PFHd证书、安全功能范围、适用软件版本和安全手册；完成ISO 12100风险评估、整机集成安全验证及当地法规要求。
9. 对DART-Platform/SDK/Store/App Builder模块检查软件版本、Store依赖、开发者认证、模块许可、SBOM和更新机制；OTA状态不引用旧产品宣传页作为当前已交付能力证明。

## 9. 本轮未执行事项

未安装DART-Platform/IDE/SDK/Store、未下载RobotLab最新DRFL、未构建Humble/Jazzy ROS 2工作区、未运行DRCF/Gazebo/MuJoCo、未连接真实Doosan控制器/机器人/PLC/外部安全设备；未测1kHz周期/抖动/WCET/轨迹误差/力控/负载估计/停止距离/故障恢复；未执行HIL/FAT/SAT或安全验证。Doosan档案仅为公开资料和代码静态审查，工程验收及供应商资格审查未完成。
