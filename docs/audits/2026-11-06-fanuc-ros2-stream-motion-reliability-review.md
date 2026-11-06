# FANUC ROS 2 Driver / Stream Motion 1 ms性能宣传、模型支持与数据包可靠性增量审计

- 审计日期：2026-11-06
- 关联厂商档案：《主要厂商》§119
- 审计性质：官方公开资料、官方仓库源码与公开Issue静态审查
- 新增来源：#1468–#1480
- 结论状态：静态审查已完成；构建、网络注入、仿真与真实机器人验证未执行

## 1. 本轮重点

本轮针对FANUC于2026年公开强化的Open Platform三支柱声明，重新核对官方ROS 2 Driver的1 ms通信、支持机型/控制器矩阵、Stream Motion数据包序列处理、运动规划动态约束和ROS 2/ros2_control未来兼容性。重点区分：控制器平台能力、特定配置下ROS 2 Driver暴露的能力、目标SKU/工程配置的端到端验收。三者不能互相替代。

## 2. 1 ms宣传与当前ROS 2产品化兼容矩阵

- FANUC Open Platform官方页面将ROS 2支持、控制器内Python和Stream Motion列为三大支柱。页面称官方ROS 2 Driver支持1 ms高速通信，产品覆盖从CRX到3 kg小型机和最大2,300 kg大型机；另称Stream Motion支持PC端高频位置命令，并可直接控制位置、速度和扭矩参数。该页面未在同一处给出逐SKU、控制柜、固件、软件选件、ROS分支、Driver tag、控制模式和可用命令接口的完整配对矩阵。来源#1468。
- 官方ROS 2 Driver系统要求页明确列出Ubuntu 22.04/Humble与Ubuntu 24.04/Jazzy；控制器为R-30iB Plus/Mate Plus/Mini Plus或R-50iA/R-50iA Mate；要求J519 Stream Motion+R912 Remote Motion，或同时包含两者的S636 External Control Package。页面特别指出J568/J570名称含“ROS 2”并不意味着它们是该驱动所需外部运动选件。控制器最低软件版本分别为R-30iB Plus/Mate Plus V9.40P/81+、Mini Plus V9.40P/77+、R-50iA V10.10P/26+。来源#1473。
- 官方supported URDF models文档覆盖CRX、LR Mate、R-1000、M-10、M-20、M-710、M-800、M-810、R-2000、P-350 Paint和CR系列中的具体模型映射；这是一份公开描述/配置支持清单，不等于全部FANUC机器人目录均有相同驱动能力、实时性能或已验证状态。来源#1472。
- FANUC官方驱动概览把1 kHz描述限定于R-50iA + S647 STMO/HSPD COMM ADD-ON等特定配置，并要求控制器通信周期1 ms、主机更新率至少1 kHz及足够实时调度能力；页面警告主机jitter会引起漂移/振动，协作速度夹紧也会增加路径误差。R-30iB Mini Plus上的Stream Motion Issue #60则记录其工程配置通信周期为8 ms。故Open Platform的1 ms页面不能被解释为所有R-30iB/R-50iA控制器、所有型号、所有ROS 2驱动配置均提供1 kHz闭环。来源#1474、#1477。
- 结论：对外资料可记录“FANUC宣传平台级1 ms能力”；工程兼容表必须逐项标注S647、控制器代际/固件、机器人型号、驱动tag、ROS发行版、主机内核/网卡/网络拓扑、更新率和测量方法。没有对应组合的端到端测量报告时，性能状态只能标记“厂商声明/待实测”，不得标记为“已验收1 kHz”。

## 3. Stream Motion UDP序列处理的静态源码核验

- 本轮读取FANUC官方fanuc_driver main分支当前HEAD：da5db3f611cdc9dffe687e056c4e79bea584bf5c，提交信息为2026-10-01合并v2.4.0 release；main与jazzy分支指向同一commit，humble分支HEAD为8f9f22e50f02042ded000440e305c7f6c820d5a2。v2.4.0 release增加payload schedule/value/compensation查询服务与pick-and-place示例。来源#1469–#1471。
- 对当前main的fanuc_libs/stream_motion/src/stream.cpp（blob 57675b92b520e6a9a7ef03a563c05ac115d39627）进行只读源码检查：getStatusPacket()在成功接收状态包后先递增本地status_sequence_no_，若与收到包的status.sequence_no不一致，则直接将本地计数器赋值为收到的序号；没有在该分支区分“向前跳号”与“旧包/重复包”。随后若command_sequence_no_ > status_sequence_no_，函数报错并返回false，导致硬件接口读周期可失败。源码逻辑与公开Issue #67所描述的序列回退路径相符。来源#1480。
- 官方main现有fanuc_libs/stream_motion/test/stream_test.cpp（blob baead6b1ae3d68effd72477f1d961c61d31790cf）可见FakeRobot与状态包发送辅助函数；本次静态检查没有发现针对乱序/重复状态包、uint32序号回绕和“旧包之后仍有新包排队”这一场景的明确回归测试。此为对当前可见测试源码的检查结论，不代表仓库所有测试均已运行。来源#1479。
- Issue #67（2026-10-13创建，当前open）报告者称在真实CRX-10iA上观察到状态包序列380161之后收到380160，导致状态计数器回退、命令计数器超过状态计数器、后续读失败和ros2_control停用硬件/控制器；报告同时给出以未修改上游源码和fake UDP socket编译运行的确定性复现表。报告者明确说明尚未抓取网络流量，因此包乱序的根因未确定。来源#1476。
- FANUC维护者在Issue #67回复称，高速驱动依赖可靠通信，乱序UDP环境可能难以稳定运行；即使驱动容忍乱序，命令包本身也可能不稳定，建议检查带宽限制和PC—机器人之间是否存在多条网络路径。该回复属于厂商维护者的Issue讨论，不等于对驱动端序列处理缺陷已修复或对目标网络环境完成诊断。Issue仍为open。来源#1476。
- 本轮对main当前源码的检查显示上述序列处理逻辑仍存在；因此Issue #67应继续列为未解决风险线索。建议后续工程验证至少覆盖：乱序、重复、丢包、突发延迟、序号回绕、旧包之后新包仍在队列、单次read deadline、断线重连、ros2_control lifecycle错误恢复；并分别记录“驱动是否安全拒绝/恢复”和“网络是否满足实时控制前提”。本轮没有修改或运行上游代码，也未进行真实UDP注入。

## 4. 轨迹动态约束、位置/速度/扭矩接口边界

- Issue #60（当前open）报告CRX-25iA通过Stream Motion执行MoveIt轨迹时在末端减速出现振动/超调；报告者指出驱动会读取机器人逐轴动态加速度/jerk阈值表，但getLimits()未被驱动其它代码调用。FANUC维护者回复确认控制器会自动平滑，但MoveIt规划不一定充分考虑机器人实际加速度/jerk限制；若希望高速轨迹避免振荡，外部规划器仍应生成满足这些限制的足够平滑轨迹。来源#1477。
- 当前ROS 2硬件接口源码仅导出joint position command interfaces；joint velocity是state interface，不是velocity command interface。该边界与Issue #40的用户报告相符。FANUC Open Platform网页的“position, velocity and torque parameters”是平台层Stream Motion能力描述，不能据此推断当前ros2_control硬件插件已经导出velocity/effort命令接口。来源#1475、#1478。
- 因此，当前ROS 2 Driver的轨迹控制应理解为“上层生成位置目标/轨迹，由控制器和Stream Motion执行”，不能把Open Platform平台宣传等同于ROS 2 Driver已提供任意速度/扭矩闭环接口。若需外部速度/力矩/阻抗控制，必须取得具体控制器协议、选件、API、驱动接口和安全功能支持矩阵，并单独验证控制模式切换、限幅、时序和失效行为。

## 5. ros2_control版本兼容性观察

- Issue #64（当前open）指出硬件插件仍使用已弃用的raw-pointer Handle构造及export_state_interfaces()/export_command_interfaces()覆盖；报告者提供了一个外部fork修复方案。FANUC维护者回复称按其理解该API只会在Rolling/Lyrical路线移除、Jazzy仍保留，因此将其作为未来兼容增强跟踪，而非当前Jazzy已知故障。来源#1478。
- 当前main hardware_interface.cpp静态源码仍可见旧式export_state_interfaces()和export_command_interfaces()实现。由于当前官方文档仅声明Humble/Jazzy组合，本项应标记为未来ROS 2/ros2_control兼容监视项，不应误报为Jazzy当前不兼容。来源#1478。
- Issue #63（当前open）报告在Isaac ROS容器、CRX-25iA、控制器V9.40P/86和驱动v2.2.0上，报警后motion control接管/释放服务失败或超时；维护者要求补充驱动日志/控制器报警并建议用v2.3.0复测。该Issue是历史版本问题线索，不得直接推断v2.4.0仍有同一故障；也没有证据证明已经关闭。来源#1478。

## 6. 工程配置与验证门禁

建议把FANUC ROS 2/Stream Motion部署基线至少拆为以下字段：

1. Robot SKU/机械版本、负载/惯量/工具、Group数量；
2. 控制柜家族、控制器软件版本、运动选件J519/R912/S636/S647；
3. ROS 2发行版、Ubuntu版本、PREEMPT_RT状态、内核/CPU governor/IRQ亲和性；
4. fanuc_driver分支/tag/commit、fanuc_description tag/commit、MoveIt配置与URDF版本；
5. 主机网卡型号/驱动/固件、直连或交换机拓扑、VLAN/QoS/防火墙、MTU、双网卡/多路径；
6. Stream Motion通信周期、controller_manager更新率、轨迹采样周期、控制器动态限幅/平滑设置；
7. 乱序/丢包/延迟/jitter/队列拥塞/断线/重连测试结果；
8. 轨迹位置/速度/加速度/jerk、终点超调/振动、力传感器和安全停止测试结果。

建议的验证分层：
- 源码审查与静态分析；
- Humble/Jazzy分别构建、lint、单元测试；
- 使用fake UDP socket做确定性乱序/重复/丢包/序号回绕回归；
- ROBOGUIDE Virtual Robot验证协议连通、启动/停止、I/O和异常恢复；
- 受控真实机器人低速测试并测量周期/jitter/轨迹误差；
- 独立评估网络故障时的状态反馈、命令安全终止、控制权恢复；
- 目标工艺下进行节拍/精度/耐久、HIL/FAT/SAT和功能安全验收。

网络侧建议使用专用隔离控制网络、单一路径和明确的QoS/带宽规划，测量双向UDP延迟分布、乱序、丢包和jitter；不能只凭ping平均时延判定Stream Motion满足1 ms。不得因厂商维护者建议就直接在生产网络关闭防火墙；应采用最小权限端口规则、白名单和分区。

## 7. 本轮未执行项目与结论

- 未安装FANUC ROS 2 Driver/ROBOGUIDE；未下载/安装S647等选件；未构建Humble/Jazzy工作区；未运行单元测试或Fake UDP复现；未连接真实FANUC控制器、PLC或网络。
- 未测量1 ms周期、端到端jitter、轨迹误差、速度/加速度/jerk、网络乱序/丢包、终点振动或控制权恢复；未进行HIL/FAT/SAT、功能安全或网络安全测试。
- 当前可确认的工程风险是：公开Open Platform 1 ms宣传范围宽于公开驱动配置矩阵的细化程度；当前main的状态包序号逻辑与open Issue #67所述回退场景一致；当前硬件接口仅导出position command接口；动态轨迹限制仍要求上层规划充分考虑。风险均需要工程复现/厂商书面矩阵进一步确认。
- 本报告不对FANUC产品作采购结论，不代表全系列不支持ROS 2，也不代表Issue #67在所有网络环境下都会发生。FANUC档案保持“静态审查完成、工程验收未完成”。
