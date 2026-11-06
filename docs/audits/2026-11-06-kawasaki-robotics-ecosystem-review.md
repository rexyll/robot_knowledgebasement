# Kawasaki Robotics 软件、控制器与 ROS 2 生态静态审查

- 审查日期：2026-11-06
- 范围：Kawasaki Robotics 控制器与 AS/KRNX 编程接口、K-ROSET/neoROSET、F 系列控制器安全选件、官方 ROS 2 Jazzy 驱动仓库
- 证据类型：制造商公开资料与 Kawasaki-Robotics 官方 GitHub 仓库静态审查
- 结论等级：P1 厂商软件生态定向审查；不构成软件安装、机器人集成、性能验收、供应商资格或安全合规结论

## 1. 产品与控制器边界

Kawasaki 官方控制器资料将 E 系列与 F 系列分开；F 系列包括 F60、F01/F02/F03/F04，且官方页面按地区列出的机器人适配型号并不完全相同。ROS 2 仓库支持表应被视为单独的软件兼容范围，而不是完整的机器人产品目录。F01产品页公开列出RS013N、RS020N、BA006N、BA006L、YF002N、YF003N等适配型号；亚洲区域页面另列不同型号，说明地区目录和SKU必须逐项核验。来源#1405、#1406。

官方F系列控制器手册说明，F0x控制器分A/B型：A型面向Cubic-S，B型面向CoreCubic-S；F60也有A/B型，且两者安全功能平台不兼容。仅凭“F系列”或“F60”名称不能选定安全单元，必须读取控制器铭牌完整型号并取得目标配置手册。来源#1406、#1407。

## 2. 编程语言、控制API与软件工具

- Block-Step是面向初学操作人员的基础编程方式；AS Language用于更复杂的运动路径和控制逻辑，官方资料称其为Kawasaki机器人标准编程语言。
- KRNX是面向高级开发者的API，使外部生成的运动程序能够控制机器人。它是外部实时运动接口，不等同于AS程序语言、普通状态监控API或通用ROS消息接口。
- K-ROSET是离线编程与仿真软件，可在PC上使用机器人/工件/设备3D模型进行程序编制和模拟，并可从仿真输出机器人程序。K-ROSET Lite为面向Kawasaki客户的免费基础版本，功能范围低于购买完整许可的版本。
- neoROSET是较新的机器人编程支持软件，官方介绍其虚拟控制器技术用于更准确复现运动轨迹和节拍，并支持多机器人、不同控制器、外部轴和干涉/布局检查。上述功能声明不等于整站虚拟调试或现场节拍验收。
- 官方软件目录还列KRTerm（控制器状态/变量/备份工具）、KCONG（自动示教）及K-SPARC（码垛软件）。这些是不同用途的软件产品，不应混称为单一IDE或统一许可包。来源#1402–#1404、#1408。

## 3. 官方 ROS 2 驱动：KHI ROS2 Driver

官方仓库：Kawasaki-Robotics/khi_ros2，默认分支main。本轮固定HEAD为32a34658cd80343bfe7b7fb82cabce3bfd2b4381，提交日期2026-04-17，提交说明为增加Jazzy支持。仓库当前没有GitHub Release对象；khi_hardware/package.xml版本为1.0.0。不能把仓库包版本1.0.0误作正式产品发布或长期支持承诺。来源#1409–#1411。

README明确支持ROS 2 Jazzy与Ubuntu 24.04实时内核，并要求配置实时用户权限；建议rtprio/priority 99及memlock限制。若未正确启用实时调度，启动时会提示无法启用FIFO调度策略。此为驱动运行前置条件，不代表任何通用PC都已满足硬实时或WCET要求。

README列出的控制器软件最低版本为：
- F01A/F02A：高于ASF_01010200E；
- F01B/F02B/F60B：高于ASF_01040200A；
- F60A：高于ASF_010000020；
- F61：高于ASF_06000000T。

明确列出的机器人型号为RS007L-B001、RS013N-A001、RS015X-A001、RS025N-A001、RS080N-A001、BX300L-B001、BXP135X-A001、BXP210L-A001及WD003H-F502（duAro2）。没有列出的机器人型号、E系列控制器或其他软件版本不得推定兼容。来源#1410。

仓库包含khi_description、khi_gz、khi_hardware、khi_moveit和khi_msgs等包，覆盖URDF/Xacro、Gazebo Sim仿真、ros2_control SystemInterface、MoveIt配置及Kawasaki专用消息/服务。Gazebo仿真路径与真实控制器路径分开；mock/loopback或Gazebo运行成功不能证明真实控制器、现场总线和安全链工作正常。

## 4. 控制周期、缓冲与状态反馈

F系列更新率配置文件将controller_manager update_rate设为500 Hz，khi_controller状态发布率也设为500 Hz。硬件接口将周期按1000/update_rate换算为毫秒，并通过KRNX SetRtcInfo配置控制器RTC周期；当前配置对应2 ms。此处只能确认软件配置意图，不能据此推导端到端抖动、控制器内部采样、通信延迟或轨迹跟踪误差。

KRNX驱动设置RTC位置命令缓冲容量为4。源码明确记录机器人控制器与ros2_control周期存在轻微差异，位置命令缓冲可能累积；当命令保持不变且缓冲达到设定条件时，驱动会跳过继续发送位置命令，以防缓冲溢出。该实现提示时钟偏差、队列占用和静止/运动切换需要重点测试，不能仅看500 Hz参数宣称确定性实时性能。来源#1411。

状态读取将控制器位置和速度转换为ROS关节状态；源码把每个关节的effort状态明确写为0。因此该effort接口不能当作实测关节力矩或电机电流。ATI力/力矩传感器数据是单独的可选周期数据路径，且需要启用对应配置并核对传感器型号、标定与单位换算。khi_msgs文档称F控制器的实际电流publisher可按2 ms间隔发布，但这不是关节控制循环频率，也不代表所有遥测字段均为2 ms或经过实测。来源#1411。

## 5. Lifecycle与故障恢复风险

硬件Lifecycle的Active状态意味着“机器人操作可能”，Inactive状态意味着“不可操作”；官方文档使用SetHardwareComponentState切换状态。KHI驱动的activate路径包括检查通信和ROS要求、Reset错误、Motor ON、必要时Hold正在运行的程序、再次Reset、清除RTC补偿数据、设置Home位置、将监控速度设为100%，最后启动RTC程序。deactivate路径等待1秒，再执行Hold、Kill程序和Motor OFF。shutdown/error路径也会尝试Hold、Kill、Motor OFF和断开连接。来源#1411。

README要求启动前确认安全围栏内无人、控制器处于REPEAT、Teach Lock关闭、机器人非Hold且无错误。README还警告控制器处于real-time control模式时，其状态等同REPEAT模式；多进程同时连接同一控制器不受支持。Troubleshooting文档对通信丢失、RTC SWITCH关闭、程序未运行和速度限制错误给出Lifecycle重新激活步骤。重新激活可能涉及复位/上电/重新启动RTC程序，必须由系统集成方增加独立安全状态确认、人员清场确认、人工授权、残余命令清除/校验和可审计重启流程；不得将文档步骤直接包装成自动安全复位策略。来源#1410–#1411。

## 6. 许可证与可再分发边界

仓库LICENSE明确分层：除KRNX外的其他组件采用Apache License 2.0；KRNX头文件和lib目录下二进制适用KRNX专有许可。该许可允许在与仓库中所有其他组件组合使用时复制、修改、分发或使用KRNX，但不授权将KRNX单独提取、独立使用或脱离该组合再分发。khi_hardware/package.xml声明Apache License 2.0不能覆盖仓库LICENSE对KRNX的特别限制。对该仓库做镜像、拆包、SDK抽取、容器化或二次分发前，必须保留LICENSE/NOTICE并进行文件级许可审查。来源#1412。

## 7. 功能安全与外围接口边界

F系列产品页对控制器安全电路给出ISO 13849-1 PLe、Category 4及IEC 61508 SIL 3声明；可选Cubic-S空间/速度监控功能页面给出PLd、Category 3、SIL 2等级。F0x/F60 A/B型安全单元互不兼容；CoreCubic-S Lite页面称F0x B型及F60B B型默认配备该功能。以上均是制造商对特定控制器/选件的声明，不是目标机器人应用或整机安全认证，也不意味着可省略ISO 12100风险评估、外围防护、停止时间/距离计算和验证。具体证书、适用型号、固件、选件和地区配置仍需取得原件核验。来源#1405–#1407。

ROS 2、KRNX、MoveIt、Gazebo、普通I/O及控制器遥测都不是安全回路的替代品。任何急停、保护停止、门锁、区域监控和安全速度功能必须依据完整控制器/安全单元SKU、证书和现场风险评估设计，并通过独立安全验证。

## 8. 工程准入与待验证项

1. 冻结机器人完整型号、控制器完整订货号及A/B型、控制器软件版本、KRNX版本、Teach Pendant版本、选件板/安全单元、地区和许可。
2. 取得目标控制器的受控操作/维护/AS Language/KRNX/安全手册与K-ROSET/neoROSET发行说明，确认软件与固件兼容矩阵、授权、备份/恢复和生命周期。
3. 在Ubuntu 24.04目标实时内核上构建Jazzy工作区；固定ROS包、MoveIt、Gazebo Sim、编译器、KRNX库和依赖版本，检查CMake对未知CPU架构回退到x86_64的风险。
4. 测量500 Hz控制器管理周期、2 ms RTC周期、read/write执行时间、FIFO调度、线程优先级、抖动、WCET、网络时延、RTC buffer占用/欠载/溢出和轨迹跟踪误差。
5. 验证Lifecycle状态转换、Reset/PowerOn/Hold/Kill/MotorOff顺序、断线恢复、控制器错误、急停/防护触发、命令残留、人工复位授权和恢复后机器人是否发生非预期运动。
6. 核验effort状态为0的接口语义；如应用需要力矩/电流/力控反馈，应使用正确的控制器数据项/传感器路径并进行标定、单位、带宽和时间戳测试。
7. 对目标安全功能进行证书、参数、接线、响应时间、停止距离、诊断覆盖和整机风险评估；执行SIL/HIL/FAT/SAT及现场验证。
8. 对KRNX专有许可进行法务/供应链审查，禁止从仓库单独提取KRNX组件并作为通用SDK分发。

## 9. 本轮未执行的验证

未下载/安装K-ROSET、neoROSET或其他商业软件；未安装Ubuntu 24.04实时内核；未构建ROS 2工作区；未运行Gazebo、MoveIt或真实机器人驱动；未连接Kawasaki控制器、PLC、现场总线或安全回路；未测控制周期、抖动、WCET、buffer行为、轨迹精度、节拍或故障恢复；未执行HIL/FAT/SAT、功能安全验证或许可证法律意见。因此本报告只记录公开资料和官方仓库静态审查，Kawasaki厂商档案保持未验收状态。

## 10. 主要来源

- Kawasaki Robotics官方编程工具、控制器、K-ROSET、neoROSET与安全功能页面：来源#1402–#1408。
- Kawasaki-Robotics/khi_ros2官方仓库及README、Lifecycle、驱动源码、Troubleshooting、LICENSE：来源#1409–#1412。
