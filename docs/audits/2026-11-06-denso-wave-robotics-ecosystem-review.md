# DENSO WAVE 工业机器人软件与 ROS 2 生态静态审查（2026-11-06）

> 本报告仅依据 DENSO WAVE 官方公开产品/支持页面及 DENSORobot 官方 GitHub 仓库静态审查。未下载或安装商业软件，未构建 ROS 2 工作区，未连接控制器、PLC或真实机器人；不构成采购推荐、供应商资格结论或安全认证。

## 1. 软件栈分层

- WINCAPS III：PAC/PacScript编程、PC端离线仿真、3D姿态/干涉/轨迹/节拍检查、控制器数据备份和在线调试。
- VRC/VRC9：RC8A/RC9控制器虚拟环境；VRC产品页要求ORiN2 SDK。仿真链还涉及WINCAPS III、VRC kernel和各自许可证。
- ORiN2 SDK：基于Provider的设备/控制器通信中间件，官方Provider矩阵覆盖DENSO RC5/RC7/RC8/RC9及多个第三方设备；不等同实时伺服接口。
- ROS 2：DENSORobot/denso_robot_ros2的humble分支提供b-CAP、ORiN2和MoveIt 2相关包；README当前列RC8/RC8A/COBOTTA支持，RC9仍为under construction。
- WINCAPS Plus、EMU、RC Vision、Robot Tools等为独立应用/仿真/视觉/维护工具，不应合并为单一控制接口。

## 2. WINCAPS III许可与功能

官方页面区分Full Function、Light、Trial。Full Function包含仿真、调试和3D CAD导入；Light不含仿真/调试/3D CAD导入，监控采样间隔1秒；Trial存在程序数量/程序库限制。仿真可检查运动、姿态、干涉、轨迹和循环时间；在线调试还可调速、复位程序、启动/停止特权任务。RC9项目要求Windows 10/11 64-bit。不得把软件名称当作仿真许可证明，也不得把PC循环时间视为实机节拍或安全验证。来源#1374–#1375。

## 3. VRC与ORiN2

VRC/VRC9提供RC8A/RC9虚拟控制器环境、虚拟示教器GUI、位置/变量/I/O/错误日志及Simulation Link。VRC要求ORiN2 SDK；ROS 2仓库README指出WINCAPS仿真机器人需WINCAPS III、ORiN2 SDK、VRC kernel及WINCAPS III产品版许可。官方Provider表列NetwoRC（RC7/RC5）、RC8（RC8/COBOTTA/VRC）、RC9（RC9）等Provider；官方FAQ列RC8 V1.2.4+、RC7 V2.330+、RC5 V1.998+。ROS 2 README中的ORiN2 command属于高层目标点命令，最终轨迹由控制器内部生成，不暴露给ROS节点；不能等同外部实时轨迹流。来源#1376–#1380。

## 4. ROS 2仓库支持边界

- 仓库默认分支humble；本轮核验HEAD为2805694999b0375861e632426b5abc484d9a9936，最后提交2025-03-14。仓库元数据updated_at不能代替代码维护证据。
- README列RC8、RC8A和COBOTTA（非OSS类型）为当前支持，RC9仍标注under construction。标准URDF/MoveIt 2配置只提供COBOTTA和VS-060；其他型号需自行创建/验证描述和运动参数。
- 包含b-CAP command、ORiN2 command、slaveMode三种控制模式；slaveMode需要控制器侧b-CAP Slave许可/注册。bcap_slave_control_cycle_msec=8.0是配置参数，不是端到端实时性或抖动保证。
- 仿真需Windows端启动b-CAP server；真实机器人步骤在README限定RC8/RC8A/COBOTTA，RC9操作仍在建设中。
- package.xml声明MIT与Apache-2.0，根LICENSE含MIT、Apache-2.0和BSD文本；应逐文件/依赖建立许可映射，不能将仓库简化为单一SPDX许可。来源#1379–#1380。

## 5. 旧ROS工具与服务状态

官方ROS Tools 2.0.1（2021-10-26）包含ROSConverter和AcquireVelAcc，页面明确标注不受支持。COBOTTA Linux驱动最新列1.2.1，ROS Melodic/Ubuntu 18.04，2021-01-21更新，且仅适用于COBOTTA OSS Type。DENSO与RT的ROS支持合作于2025年3月底结束，后续咨询由DENSO WAVE受理。不能把旧工具、COBOTTA OSS驱动和当前ROS 2仓库混为一谈。来源#1381–#1383。

## 6. 安全、现场总线与生命周期

RC8A Safety Motion为可选规格；RC9/CRC9页面列急停、保护停止、监控速度、轴限制、监控静止和Safety Virtual Fence等功能，具体功能仍需按控制器SKU、证书、软件版本、外部传感器和风险评估核验。RC8A可选板卡涉及DeviceNet、CC-Link、PROFIBUS、EtherNet/IP、PROFINET IO、EtherCAT；RC9/CRC9页面列EtherCAT、IO-Link和DIO接口/选项。ROS 2、ORiN2、b-CAP和普通I/O不得承担安全链唯一通道。停产产品页按型号列销售结束/维护结束日期，并说明备件供应/维修原则上持续至停产后10年；不可外推为无条件承诺。来源#1384–#1387。

## 7. 未完成与工程验收边界

仍需获取目标地区商业软件安装包、受控手册、许可证SKU/并发/虚拟机/离线规则；建立机器人型号+控制器+固件+WINCAPS/VRC/ORiN2版本矩阵；构建ROS 2工作区并核验依赖/许可；测试b-CAP/ORiN2/slaveMode权限、停止/复位、超时、断线恢复、周期、抖动、轨迹误差和节拍；核对安全证书、现场总线板卡和备件生命周期。

未下载/安装WINCAPS III、VRC/VRC9、ORiN2 SDK；未构建ROS 2工作区；未连接真实机器人/控制器、PLC、现场总线或安全回路；未执行SIL/HIL/WCET、实时/故障注入/FAT/SAT或功能安全验证。因此仅为官方资料与公开仓库静态审查，工程验收未完成。
