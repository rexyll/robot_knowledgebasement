# Epson Robotics 软件与 ROS 2 生态静态审查（2026-11-06）

> 范围：Epson RC+ 8.0/SPEL+、RC800/RTMC、Epson官方ROS 2仓库、AX6/AX Portal独立仓库、控制器安全功能与选件。
>
> 证据范围：Epson官方手册目录/支持页面/软件归档，以及Epson-Robots官方GitHub仓库的README、CHANGELOG、package.xml、launch、配置和代表性源文件。未下载或安装商业软件，未构建RTMC/ROS 2工作区，未连接真实机器人、控制器、PLC或安全回路；本报告不是供应商认证、实时性能证明或安全验收。

## 1. 关键结论

1. Epson有官方ROS 2工业机器人驱动，不应归类为“只有第三方适配”：epson-robot-ros2通过ros2_control、MoveIt 2、URDF和Epson RTMC Client Library控制RC800系列，但要求单独启用RTMC控制器选件、Windows端RC+ 8.0配置、Linux端Ubuntu 22.04/Humble及型号/固件匹配。
2. RTMC是独立外部轨迹控制接口。Epson不提供外部路径/轨迹规划；外部规划器须负责模型、速度/加速度/负载限制、轨迹有效性和故障策略。RTMC的Exec_RTMC缓冲区满时会等待，不能不经测量就当作非阻塞硬实时接口。
3. 官方ROS 2 README的支持范围不是整个Epson产品线：当前版本矩阵以RC800控制器、明确列出的GX4/GX8/RS4/RS6/C8/C12/CX4/CX7型号为边界；没有声明RC800L、RC700、RC90、LA/LS/N/VT/T或所有Epson型号支持。推荐环境为Ubuntu 22.04/Humble。
4. 静态代码审查发现需专项验证的时基与默认值差异：控制器配置update_rate=1000 Hz，Epson定制JointTrajectoryController以固定2 ms推进轨迹时间；README将buffer_size默认值写为5，而launch默认值为10。此处登记为待验证的调度/文档差异，不在无实测情况下断言为缺陷。
5. ROS 2硬件Lifecycle激活路径包含Reset、MotorOn、PowerHigh和启用RTMC；README异常恢复示例明确警告重新激活后机器人可能自动恢复运动。生产系统必须设置独立安全互锁、人工授权和可审计的重启状态机。
6. AX6/AX Portal有单独的ROS 2消息和模型描述仓库，不等同于RC800工业机器人RTMC驱动，也不能把AX6 URDF/RViz描述包当成完整硬件驱动。
7. RC800安全功能必须按机械臂型号、控制器型号、RC+版本和Safety Board固件矩阵核验；Force Guide、RTMC、OPC UA、普通ROS I/O均不是人员防护安全功能。

## 2. RC+ 8.0与SPEL+软件栈

- 官方手册目录分别列出RC800-A、RC800L、RC700-E/D、RC700和RC90控制器，以及SCARA/六轴多个机器人系列。目录提示部分产品并非所有地区销售，停产产品手册需联系经销商获取。
- RC+ 8.0为机器人IDE与集成软件环境；SPEL+语言参考和错误码手册按RC800与RC700/RC90/T/VT系列区分。RC+ 8.0统一软件品牌不等于跨控制器指令、固件、选件或运行时完全兼容。
- RC+ API 8.0、GUI Builder、PLC Function Block、Remote Control、Conveyor Tracking、Vision Guide、Part Feeding、Force Guide、Fieldbus I/O、OPC UA Server、SRCI等为独立选项/扩展或控制器选件。必须按SKU、控制器代际、固件、软件许可和地区核验。
- RC+ 8.0激活资料描述许可证密钥、在线认证和离线认证流程。隔离网、虚拟机、产线备机与灾备环境须预先确认许可转移/重激活政策。
- Epson欧洲下载归档快照同时出现8.1.1.1安装手册包、8.1.2.0 Web Manual、8.1.4.0 Installed Manual，以及名为“RC+ 8 Ver 2.0.0.0”的压缩包。它们是不同类型文件/地区目录条目，不构成软件兼容矩阵；不能仅凭文件名推断2.0.0.0是所有地区的正式最新软件版本。
- Force Guide 8.0支持力控制、力触发、力监控、力运动限制、力引导等操作能力，但其官方手册明确说明这些功能不是用于确保安全的功能。

## 3. RTMC Client Library

### 3.1 依赖与运行前置条件

- RTMC用于外部设备将路径/轨迹规划结果转化为运动控制值，发送至Epson控制器；Epson明确说明其不提供路径规划/轨迹规划。
- 支持前置条件：RC800控制器8.1.1.0或更高、单独购买并启用Real-time Motion Control控制器选项、Windows PC通过USB运行RC+ 8.0完成控制器配置、Linux PC通过Ethernet连接控制器。
- RTMC 1.1.0支持表中大部分型号要求ROS 2包1.1.0+、客户端库1.1.0+、RC800固件8.1.2.0+；带星号的特定型号可用1.0.0+和8.1.1.0+。
- 官方列出的SCARA系列为GX4、GX8、RS4、RS6；六轴系列为C8、C12、CX4、CX7，必须按README完整型号表逐型号比对。不得外推至RC800L、RC700、RC90、LA/LS/N/VT/T或未列型号。
- 推荐Linux环境Ubuntu 22.04 LTS、Intel Core i7或更高、16GB内存；Epson明确不保证所有PC都可运行。ROS 2驱动推荐Humble。
- 客户端库依赖Fast DDS 2.14.4和OpenSSL；构建说明要求Fast DDS SECURITY开启，并使用固定的本地Fast DDS安装路径/静态库。移植到不同目录、CPU架构、编译器或发行版需修订构建配置并实际验证。

### 3.2 API状态机与运动数据语义

- RTMC_Connect建立通信并认证控制器密码。
- RBCheck核对外部程序请求的机器人型号与控制器设定；成功后才允许MotorOn、MotorOff、PowerHigh/Low、RTMC模式启停、Exec_RTMC及负载参数设置。
- Exec_RTMC输入关节运动值（rad或mm），可选同步标准I/O输出，并返回当前关节值/I/O状态。控制器先把运动值放入内部缓冲区，再按控制器运动周期消费。
- 当缓冲区已满，Exec_RTMC会等待缓冲空间；调用延迟与阻塞行为必须纳入上层实时性预算。buffer_size是控制器侧缓冲容量，不是控制器伺服周期或端到端延迟指标。
- Exec_RTMC的接受条件包括通信已建立、操作模式AUTO、RBCheck完成、RTMC模式已启用、Safeguard关闭、急停关闭、控制器无错误。
- RTMC模式在控制器错误、急停、Safeguard触发、通信断开或显式禁用时自动关闭。
- Set_Weight与Set_Inertia/偏心距会影响运动参数优化；这些值会保留在控制器中，必须确认末端工具、工件和负载变化后更新。
- Reset会复位控制器错误/急停状态并关闭标准I/O输出位。Reset不是急停/安全复位回路，不得自动调用以绕过人工检查或安全联锁。

## 4. 官方ROS 2驱动仓库

### 4.1 版本与支持范围

- 仓库：https://github.com/Epson-Robots/epson-robot-ros2
- 默认分支：main；本轮核验HEAD：7ead19a7189e052ab7fb49fdc6922f484f893cdd，提交日期2026-01-08。
- package版本1.1.0；CHANGELOG记录v1.1.0于2025-12-26发布；GitHub Releases未列正式Release对象。代码最近push快照为2026-01-08；仓库metadata更新时间不可代替push/发布证据。
- README要求Ubuntu 22.04 + ROS 2 Humble、RC800控制器及RTMC选件；MoveIt 2和ros2_control不是Epson仓库提供的软件。
- 仓库包含控制器通信节点、ros2_control HardwareInterface、Epson定制JointTrajectoryController、URDF/Xacro、MoveIt配置、RViz和demo。不能把源码仓库的存在理解为所有型号/ROS发行版均获支持。

### 4.2 Lifecycle与重新启动风险

静态代码路径：
- on_configure：建立RTMC连接并完成准备。
- on_activate：Robot_Activate顺序包含Reset、获取当前关节值、读取控制器状态、MotorOn、PowerHigh、Set_RTMCModeEnable。
- on_deactivate：Set_RTMCModeDisable后MotorOff。
- on_cleanup：断开RTMC通信。

README的异常恢复流程要求将硬件组件切换到INACTIVE，处理控制器错误/急停/防护门事件后，再切换为ACTIVE；README明确警告此流程可能使机器人自动重新开始运行。因此生产系统需要外部安全状态确认、人工授权、清空/验证残留命令和可审计的重启状态机；不得照搬demo形成自动复位/自动再启动。

### 4.3 时基、缓冲区与文档差异

- 机器人型号配置YAML中的controller_manager update_rate为1000 Hz，joint_state_broadcaster state_publish_rate为125 Hz。
- Epson定制JointTrajectoryController注释和实现使用固定2 ms轨迹时间步进（scaled_time每次推进2,000,000 ns）。此常量与1 kHz controller_manager更新配置构成需要验证的时基契约；不得直接推断实际运动刷新率、抖动或WCET。
- RTMC README说明控制器缓冲区满时Exec_RTMC等待；因此必须测量ros2_control update周期、轨迹时间推进、Exec_RTMC阻塞时间、buffer占用/欠载、网络延迟、反馈时间戳和跟踪误差。
- README参数表写buffer_size默认值5，而bringup launch默认值10；必须确认文档/代码哪个值为准，并在产品配置显式设置。
- README参数表出现log_lovel，launch参数和硬件接口读取的是log_level；文档需修订或向Epson确认。
- launch默认security=false；只有控制器侧和Linux端正确配置安全通信、CA/客户端证书、governance与permissions文件并启用security参数后才会启用安全通信。编译Fast DDS Security与运行时开启安全通信是不同条件。
- RTMC与ROS 2 README中的命令行示例把password作为launch参数传递。生产部署需定义密钥注入/轮换/权限和shell history/process list暴露风险的处理方式，不得使用示例口令。

## 5. AX6与AX Portal独立生态

- Epson-Robots/epson-ax-ros2 README说明generic_msgs兼容AX Portal 2.6.3，提供执行AX Portal功能的ROS action消息。仓库当前HEAD 203b50e4e9c8dbd723eff862a94e48365903cd29（2026-06-18），Apache-2.0。
- Epson-Robots/epson-ax-descriptions提供AX6 URDF/Xacro、STL、RViz和简单joint_state_publisher；可独立可视化，也可接收AX Portal发布的joint_states。它不是完整真实机器人硬件驱动或安全控制系统。当前HEAD 147c4bdf113919c5ae1874de68052e49bea45279（2026-05-28），Apache-2.0。
- AX6/AX Portal与RC800/RTMC工业机器人驱动是不同的产品/控制器软件栈，需分开维护版本和兼容矩阵。

## 6. 控制器安全功能、现场总线与选件

- Epson官方Robot Controller Safety Function Manual Rev.14按操纵器型号、控制器、RC+版本和Safety Board固件列出安全功能适用矩阵。例如GX4-C/GX8-C + RC800-A要求RC+ 8.0.0.3+与Safety Board FW 02.01.00.0009+；C8-C/C12-C + RC800-A要求RC+ 8.1.0.0+；CX4-A/CX7-A + RC800-A要求RC+ 8.1.2.0+与Safety Board FW 02.03.00.0018+。
- RC800-A控制器手册列STO、Emergency Stop、Safety Input/SS1-r/SS1-t、Safeguard/Protective Stop、Enable Switch Stop、Soft Axis Limiting/SLP、Safety Output、SLS等功能名称，部分功能是收费选项。具体安全等级、证书、接线、外部设备和适用型号必须按完整订货号与Safety Board版本核验。
- 官方手册目录列Fieldbus I/O、OPC UA Server、SRCI、RC+ API、PLC Function Block等；这些是控制/数据集成能力，不等于安全通道或实时运动控制保证。普通ROS 2、RTMC、OPC UA、Fieldbus和标准I/O不得成为急停、STO或人员防护安全链唯一通道。
- Force Guide是工艺力控能力，不是安全功能。

## 7. 待办与验收矩阵

| 项目 | 静态审查结论 | 仍需完成 |
|---|---|---|
| RC+ 8.0 | IDE、SPEL+、模拟器/扩展和许可入口已梳理 | 获取目标地区安装包/受控手册；确认8.x文件命名与实际软件版本；验证许可激活、离线和灾备 |
| RTMC | 外部规划器—RTMC Client Library—RC800的路径、前置条件和缓冲行为已梳理 | 目标控制器/型号版本确认；构建依赖复现；单位/负载校验；阻塞/超时/断线/缓冲欠载测试 |
| ROS 2 | Humble/Ubuntu 22.04和官方支持型号矩阵已记录 | 实际构建；MoveIt/ros2_control依赖锁定；1 kHz与2 ms时基测量；周期/抖动/WCET/轨迹精度/节拍 |
| Lifecycle安全 | 发现激活路径包含Reset/MotorOn/PowerHigh/RTMC Enable，README提示自动重启风险 | 设计独立授权与安全联锁；测试急停/门开/控制器错误恢复；防止自动再启动 |
| 许可证/供应链 | ROS 2/RTMC声明Apache-2.0，含NOTICE；依赖清单已识别 | Fast DDS/foonathan_memory/OpenSSL/修改的ros2_controllers逐文件许可证和SBOM |
| AX6/AX Portal | 官方ROS消息和AX6描述包已区分 | 获取AX Portal完整手册/版本矩阵；确认消息执行语义、硬件控制路径和安全边界 |
| 安全功能/现场总线 | Safety Function Manual Rev.14与控制器选件目录已记录 | 型号/Safety Board/固件/证书核验；保护停止、停止时间/距离、现场总线和整机风险评估 |

## 8. 本轮未执行事项

- 未下载/安装RC+ 8.0商业软件；未构建RTMC Client Library或Epson ROS 2工作区；未运行仿真或MoveIt demo。
- 未连接真实RC800控制器/机器人、PLC、现场总线或安全回路。
- 未执行周期/抖动/WCET、轨迹跟踪误差、节拍、断线恢复、故障注入、HIL/FAT/SAT或功能安全验证。
- 因此本报告仅为官方资料与官方仓库静态审查，不能标记为工程验收完成。

## 9. 来源索引

- #1389 Epson Robot Manuals官方目录
- #1390 Epson RC+ 8.0官方产品资料
- #1391 Epson RC+ 8.0支持/Force Guide资料
- #1392 Epson RC+ 8.0用户指南及SPEL+参考入口
- #1393 Epson RC+ 8.0激活指南
- #1394 Epson Europe RC+ 8.x软件下载归档
- #1395 Epson官方ROS 2仓库
- #1396 Epson官方ROS 2 README
- #1397 Epson RTMC Client Library仓库
- #1398 Epson RTMC Client Library README/API
- #1399 Epson Robot Controller Safety Function Manual Rev.14
- #1400 Epson AX Portal ROS 2消息仓库
- #1401 Epson AX6描述仓库
