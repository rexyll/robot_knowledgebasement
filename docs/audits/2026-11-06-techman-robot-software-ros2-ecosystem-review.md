# Techman Robot（达明机器人）软件与 ROS 2 生态静态审查（2026-11-06）

> 审查范围：TMflow / TMscript / TMcraft / TMvision、TM ROS Driver（传统 TM 系列与 TM AI Cobot S 系列两条路线）、TM ROS 2、MoveIt 2、Gazebo、独立机器人描述仓库、EIH Camera gRPC ROS 2 client、产品安全与网络安全合规声明。
> 审查类型：官方产品页、技术支持页、官方 GitHub 仓库/分支/源码元数据和 package.xml 静态审查；不构成目标 SKU 兼容认证、软件构建验收、真实机器人实时性验收或整机安全认证。
> 对应任务：根任务 00-01；第21章 21-02。
> 来源：链接台账 #1454–#1467。

## 1. 产品与软件代际

- Techman 产品生态至少应区分传统 TM Robot/TM AI Cobot 系列与 TM AI Cobot S 系列；还要冻结控制箱硬件版本、TMflow主版本、TMvision/EIH相机配置、机器人型号和选件。官方将 S 系列独立列入 `tm2_ros2` / `tm2_ros1` 仓库，旧 `tmr_ros2` 明确声明不支持新 S 系列。不能用“TM机器人”泛称推断所有代际共用一个驱动或软件包。来源 #1454–#1458。
- TMflow 是控制器侧图形化 HMI / Flow 项目环境；TMscript 可用于 Flow 项目 Script Node 和独立 Script Project。TMflow还包含视觉、力相关节点、TMcraft自定义套件开发和ROS集成入口。TMcraft面向 C# / WPF 扩展开发；其SDK、授权、API和运行时兼容仍需以具体版本文档为准。来源 #1461–#1462。
- 官方 Download Center 同时列出 TMflow 1.76–1.88、2.12–2.26 等多个版本、TMvision、TMscript、EIH Camera API、Embedded TM ROS Driver、硬件/系统手册与 Safety Manual。目录显示可供筛选的版本，不代表每个地区、账号或SKU均可下载；Safety Manual当前页面显示会员访问限制。采购前应从控制器导出的系统信息和受控下载包确定准确版本。来源 #1466。

## 2. ROS 2 驱动分支与版本快照

### 2.1 传统 TM Robot：`tmr_ros2`

- 官方仓库 `TechmanRobotInc/tmr_ros2` 的描述明确为传统 TM Robots ROS 2 driver，注明实验性且“不支持新的 TM AI Cobot S Series”。默认分支为 `humble`；当前可见分支包括 `foxy` 和 `humble`。本轮核对的 Humble HEAD 为 `c40bfc0d296337311f311c837861fd6318b00407`（2026-06-17，README链接迁移，仓库标注1.4.2）；`tm_driver/package.xml` 为 1.3.0 / BSD-3-Clause。分支/包版本字段并非同一版本号。来源 #1457–#1459。
- 官方仓库README及Techman ROS Repository页面将传统路线对应 TMflow 1.76–1.88；旧 ROS 2 仓库提供状态采集、脚本/事件/I/O/位置服务和 MoveIt FollowJointTrajectory action。历史页面列出的 Dashing/Foxy/Humble 与当前仓库分支列表并不完全一致，Dashing不能仅凭旧页面视为当前仍可构建/维护的分支。来源 #1454、#1458。

### 2.2 TM AI Cobot S 系列：`tm2_ros2`

- 官方仓库 `TechmanRobotInc/tm2_ros2` 明确面向 TM AI Cobot S Series，默认分支为 `humble`；当前分支列表为 `foxy`、`humble`、`jazzy`。本轮核对 Humble HEAD `9c087f600e06f7bbaf96ec0f3844fca47b843262`（2026-06-17，README链接迁移，仓库README标注1.4.12）；Jazzy HEAD `6fb95cc5977d648c1ceb652822d4bd37b5067c1e`（2026-10-22，README标注1.1.10）。两分支 `tm_driver/package.xml` 分别为 Humble 2.3.1、Jazzy 2.4.0。GitHub Releases API当前未返回正式Release条目，因此README/commit消息中的应用版本号不应误称为GitHub Release。来源 #1455–#1457。
- README要求 TMflow 2.14 或以上，主要适配 HW5.0；驱动经 TMflow Ethernet Slave 读取状态，并同时连接 Flow 项目内运行的 Listen Node，控制命令以 TM Robot Expression / TMscript 形式发送。若目标项目没有启动并运行相应 Listen Node，ROS服务端虽已启动也不等于运动命令链路已就绪。来源 #1455。
- 三类ROS接口的职责不同：Topic Publisher发布 `/feedback_states`、`/joint_states`、`/tool_pose`；Service Server提供 `send_script`、`set_event`（Stop/Pause/Resume）、`set_io`、`set_positions`；Action Server提供 `/follow_joint_trajectory` 以连接MoveIt。普通ROS服务/Action和Ethernet Slave通信不是安全额定通道，也不代表实时伺服或功能安全接口。来源 #1455。
- Techman官网的ROS Repository汇总页仍将 `tm2_ros2` 版本表列为 Foxy/Humble，而官方仓库README已列出 Jazzy 分支；独立描述仓库则要求 Jazzy 或更高版本。该文档差异应作为版本门禁处理：Jazzy仓库存在不等于所有型号、Gazebo插件、描述包和EIH相机接口均已完成官方发行支持。来源 #1454–#1456、#1460。

## 3. ROS 2 包、模型描述与仿真

- `tm2_ros2` Humble源码树包含 `tm_driver`、`tm_msgs`、`tm_description`、`tm_gazebo`、MoveIt配置、示例和图像订阅等包。Humble的 `tm_gazebo/package.xml` 为 1.0.5，描述为 TM AI Cobot S-Series 的 Gazebo Fortress 仿真，依赖 `ign_ros2_control`、`ros_gz_sim`、`ros_gz_bridge`、controller_manager和TM描述包。仿真包版本不等于机器人驱动版本；需锁定Gazebo/ROS发行版、控制器插件和模型参数。来源 #1455。
- 独立仓库 `TM_Cobots_ROS2_Description` 提供TM AI Cobot S及传统TM AI Cobot系列的URDF/Xacro/mesh，覆盖RViz2、Gazebo和MoveIt 2配置；README要求ROS 2 Jazzy或更高版本，并区分Standard、Standard-X、FT、FT-X等配置。其型号矩阵列出S系列TM5S/TM6S/TM7S/TM12S/TM14S/TM20S/TM25S/TM30S，以及传统TM5-700/TM5-900/TM12/TM14/TM16/TM20及X版本。仓库标注experimental，不能把模型存在等同于已对每个SKU完成仿真或实机验证。来源 #1460–#1461。
- 独立描述仓库最新可见提交 `377e2aacd95318903bc293bf694a044801e78128`（2026-10-27，修正TM6S LINK3的CoG参数）。这说明惯量/质心参数仍可能在更新；在MoveIt碰撞检查、Gazebo动力学、负载估计和轨迹规划中，必须以具体型号/变体/工具的受控参数为准，并核验模型commit与真实机器人配置。来源 #1461。
- 独立描述仓库README还提供从该仓库迁移/加载模型到 `tm2_ros2` workspace的脚本流程，并提示默认基线只带少数模型配置，其余模型配置需加载。与不同分支树中实际存在的模型文件相比，模型文件存在、安装脚本可获取、launch可运行和目标SKU受支持属于不同状态；应逐个型号检查模型目录、package.xml、launch和mesh资产，不要用一个README矩阵推断所有变体已经装入工作区。来源 #1460。
- TMflow官方产品页宣传可在PC上模拟和控制虚拟机器人；此功能应与ROS/Gazebo模型仿真分开记录。未取得目标TMflow版本的虚拟控制器说明、模型精度、支持型号及与真实控制柜通信边界前，不能将TMflow虚拟机器人当作Gazebo动力学、控制器固件仿真或安全回路HIL。来源 #1463。

## 4. EIH相机与视觉软件链

- 官方仓库 `tm_eih_cam_client` 是独立ROS 2包，将TMflow >=2.20的EIH Camera gRPC API桥接到ROS 2；发布 `/eih_camera/image_raw`、压缩图像和 `/eih_camera/camera_info`，并允许通过ROS参数运行时配置相机参数。README明确要求ROS 2 Humble、gRPC和OpenCV；应将它视为相机数据/参数桥，而非机器人运动驱动。来源 #1464。
- `tm_eih_cam_client` package.xml版本为0.1.0，声明BSD-3-Clause；仓库元数据未识别出标准SPDX许可证（GitHub API返回NOASSERTION），需要核对完整LICENSE/NOTICE、第三方gRPC/protobuf/OpenCV依赖和相机API授权。其最新可见main commit为 `5457210d1cccaf09926bbf0d1545f07bb2fa587e`（2026-06-01，更新API手册链接）。README只声明Humble，不能推断Jazzy兼容。来源 #1464。
- 视觉系统还包括TMvision、内置EIH相机、外部相机/检测节点和TMflow Vision Node。必须核对相机固件、TMflow版本、API Server是否启用、gRPC端点/网络ACL、相机标定与图像时间戳/坐标系；ROS topic可接收图像不等于完成手眼标定或视觉引导精度验收。来源 #1454、#1464、#1466。

## 5. 安全、法规与网络安全声明

- Techman官方产品合规页面（更新2026-10-05）对TM AI Cobot S Series作出以下厂商声明：TMflow 2.24及以上与ISO 10218-1:2011的符合性；TRSS 5.3获TÜV NORD的ISO 13849-1:2023认证，页面列35项PL d Cat.3安全功能及1项PL b Cat.B功能。以上是厂商页面摘要，尚未取得证书原件、适用型号/控制箱/固件范围和完整Safety Manual，不能直接作为某一采购SKU或整机应用的认证证据。来源 #1465。
- 同一页面称S系列TMflow 2.24及以上“目标在2026年底前”取得ISO 10218-1:2025 TÜV NORD符合性；截至本次审查日2026-11-06，该目标仍是未来计划，不可写成已经取得认证。ISO 10218-1:2025的条款适用性、地区法规生效日期和整机集成要求应由第20章单独审查。来源 #1465。
- 页面另称Techman于2025-08获Bureau Veritas IEC 62443-4-1:2018 SDL ML2认证；TM AI Cobot S Series HW5.04及以上、TMflow 3及以上于2026-09获DEKRA IEC 62443-4-2:2019 SL2认证。该范围不可外推到旧HW、旧TMflow或传统TM系列；采购时应取得证书和安全加固指南，确认产品版本、组件边界、证书持有人及生命周期。来源 #1465。
- Download Center列出System 5.3 Safety Manual Rev1.02并标注2026-10-30更新，但当前下载项显示Members Only。不能以产品合规网页的摘要替代完整安全手册、证书附件、停止时间/距离、外部安全接口和安全参数配置验证。来源 #1466。
- 厂商页面还声明S系列HW5.04+/TMflow3使用数字签名更新包、防回滚、工程身份验证和不可变日志等安全控制。此类网络安全声明应落实为产品威胁模型、固件签名验证、更新/回滚测试、账户权限、审计日志和漏洞响应证据；不应把网页摘要当作渗透测试或CRA符合性评估。来源 #1465。

## 6. 许可证、维护状态与工程准入

- `tmr_ros2` 与 `tm2_ros2` 的仓库LICENSE文件包含BSD 3-Clause主体及ROS 2/MoveIt第三方许可文本；`tm_driver/package.xml`声明BSD-3-Clause。GitHub仓库API的许可证识别对 `tm2_ros2` 返回Other/NOASSERTION，与LICENSE正文可识别的BSD 3-Clause不一致；应逐文件、子包、第三方源码、模型mesh和二进制SDK核验LICENSE/NOTICE，不应只依据仓库徽章或API字段。来源 #1455、#1458。
- `TM_Cobots_ROS2_Description`仓库LICENSE为BSD 3-Clause；`tm_eih_cam_client` package.xml声明BSD-3-Clause，但仓库API元数据为NOASSERTION。TMflow、TMvision、TMcraft、EIH Camera API、控制器软件和下载中心中的商业/受控组件仍受各自EULA或授权条款约束，不能因ROS仓库含BSD LICENSE就推断整套软件栈可自由再分发。来源 #1460、#1464、#1466–#1467。
- GitHub提交对象未签名（本轮所查commit verification标记unsigned）；这不自动意味着代码恶意，但软件供应链应固定commit、下载来源、校验哈希、审核变更和第三方依赖，不能仅以厂商组织名代替制品真实性验证。
- 采购/部署前冻结机器人SKU、硬件版本（特别是HW5.x / HW5.04+）、控制箱、TMflow/TMvision版本、ROS发行版、Ubuntu、tm2_ros2/tmr_ros2分支和commit、package.xml版本、URDF/Xacro/mesh commit、MoveIt/Gazebo版本、EIH API版本、相机型号/标定、末端工具与安全配置。
- 先在离线工作区审查模型、依赖和许可证；再进行colcon build、lint、URDF/Xacro检查、RViz可视化、MoveIt规划、Gazebo仿真和日志/时间戳检查；最后在受控实机环境验证Ethernet Slave/Listen Node连接、反馈频率、命令超时/停止/恢复、I/O映射、轨迹误差、负载/重心、视觉标定、网络故障、保护停机和急停。所有运动测试必须先进行风险评估、限速/限位和可触及急停准备。
- 必须把ROS普通接口与安全链分离：`set_event Stop`、ROS action cancel、普通I/O和状态topic都不能替代安全额定急停/防护停机。对具体集成单元完成ISO 12100风险评估、适用机器人/机械/功能安全标准评审和外部安全回路验证。

## 7. 本轮未执行的验证

本轮未下载TMflow/TMvision/TMcraft安装包或受控Safety Manual，未安装Windows TMflow Client，未下载/构建任何Techman ROS 2工作区，未运行RViz/MoveIt/Gazebo/TMflow虚拟机器人，未连接真实TM控制器、机器人、EIH相机、PLC或安全设备；未执行ROS通信周期/延迟/抖动、轨迹精度、负载/惯量、相机标定、网络故障注入、急停/保护停机、HIL/FAT/SAT或安全认证测试。Techman档案仅为官方公开资料和GitHub静态审查，工程验收保持未完成。

## 8. 主要未决事项

1. 获取目标地区/型号完整产品兼容矩阵、控制箱硬件修订、TMflow/TMvision版本和软件生命周期/PCN/EOL承诺。
2. 获取S系列与传统系列对应的受控Safety Manual、ISO 13849证书、ISO 10218声明/证书、停止时间数据和外部安全接口手册。
3. 对比 `tmr_ros2`、`tm2_ros2` 的Ethernet Slave协议、Listen Node脚本接口、连接/重连/超时/停止语义，核对ROS2 Jazzy分支与官方支持页版本差异。
4. 取得TMflow 3与ROS2驱动、独立模型仓库、EIH Camera API之间的正式兼容声明；当前公开ROS driver README主要写TMflow 2.14+，EIH客户端只声明Humble/TMflow>=2.20。
5. 审核TM2 ROS模型的关节限位、零位、惯量/CoG、FT模块、工具坐标、碰撞网格和Gazebo物理参数；对模型版本更新建立自动差异检测。
6. 对所有仓库逐文件生成SBOM，核对BSD/Apache/其他第三方许可及商业软件EULA；固定release/tag/commit和制品哈希。
7. 在目标控制器和真实机器人上执行ROS接口、时序、轨迹、视觉、故障恢复与安全验证，并保留原始日志和测试记录。

