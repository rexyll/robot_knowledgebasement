# P1 Mitsubishi Electric MELFA：工业机器人软件与ROS 2生态厂商审查

- 日期：2026-11-06
- 分支：main
- 对应任务：根任务 00-01；第21章 21-02
- 目标资产：`knowledge/ecosystem/主要厂商.md` §124
- 交叉资产：`knowledge/ecosystem/知识生态兼容矩阵.md`
- 审查类型：厂商官方产品/手册/软件更新信息及官方GitHub仓库静态审查
- 状态：**定向静态审查已记录；未完成软件安装、控制器联调和工程验收**

## 1. 审查范围

本轮从Yaskawa MOTOMAN / MOTOMAN NEXT档案之后继续，审查Mitsubishi Electric MELFA软件生态。重点区分RT ToolBox3不同版本、RT VisualBox、MELFA API for Linux、MELFA ROS2 Driver、MELFA ROS2 Monitor、CR800网络功能和Robot Safety Option。

## 2. 关键核验结果

### 2.1 RT ToolBox3版本与功能分层

- Mitsubishi官方更新信息列出2026-11-03发布RT ToolBox3 Ver.2.80J Update和Trial。
- 官方手册目录列RT ToolBox3/mini User's Manual BFP-A3495 Ver.Y，发布日期2026-11。
- RT ToolBox3分mini、标准版、Pro：mini无仿真；标准版支持仿真/3D/节拍；Pro增加MELFA-Works/SolidWorks CAD路径能力。官方手册明确Movemaster命令模式下仿真功能不可用。
- 另一区域下载入口仍显示2.60N（2025-10-09），因此不能把某地区旧下载页当成全球统一最新版本，也不能将2.80J公告自动推断为所有区域/授权均可下载。

### 2.2 RT VisualBox

官方软件页列RT VisualBox 1.12N（2025-11-26），目标产品为RV-5AS-D、CR800-05VD，Windows 11；输入产品ID可启用产品版，否则为功能受限试用版。它是ASSISTA特定组合的触控式程序与外围设备设置工具，不是通用RT ToolBox3 Pro替代品。

### 2.3 MELFA API for Linux

Mitsubishi于2026-02发布MELFA API for Linux，推荐Ubuntu 22.04 LTS，支持C++17/Python 3.10并提供ROS 2 Humble示例。它通过Ethernet访问CR800/CR860-D/R/Q，控制器版本A1或更高；支持读取信息/变量、启动/停止/复位程序、Override和直接执行MELFA-BASIC VI。该API是程序/数据级Linux接口，不等同于实时外部运动控制API。

### 2.4 MELFA ROS2 Driver

- 官方GitHub仓库默认分支为humble，非main；本轮核验分支HEAD为72a0430e2190f4e7ef243e4bc91ca0afbd01ced6（2026-10-22）。
- 最新Release为v1.1.1（2026-03-26），melfa_driver包版本1.1.1，许可证Apache-2.0。
- Driver使用ros2_control、rtexc API和MXT指令，目标控制器为CR800/CR860-R/Q/D；官方列R/D控制器286 Hz、Q控制器141 Hz。
- README只列Tier 1 Supported Robots具体型号/控制器组合，不能将控制器家族支持扩大为全部MELFA型号支持。

### 2.5 MELFA ROS2 Monitor

官方仓库同样默认humble分支。Monitor使用UDP/rtmon API读取CR800/CR860控制器遥测，官方列R/D 286 Hz、Q 141 Hz，覆盖关节、伺服、I/O、温度、电流、TCP位姿和力/力矩数据。它以监控/遥测为主，同时包含GPIO控制器；不是关节实时运动命令驱动，GPIO写入也不能视作安全功能。

### 2.6 网络与安全边界

- CR800 Ethernet Function Manual BFP-A3379-H于2026-01-30修订并加入Modbus TCP；CR800支持，CR750/CR751不支持，且控制器版本需满足手册条件。
- CR800 Robot Safety Option 4F-SF002-01有独立手册BFP-A3531-Q（2025-11-14修订），说明需与安全开关/光幕等外部设备配合。不能将其推断为所有控制器默认包含，也不能让普通ROS/API/Modbus通道承担安全链唯一功能。

## 3. 对正文的修改

已在《主要厂商》新增第124节：
- RT ToolBox3 mini/标准版/Pro的功能和授权边界；
- MELFA-BASIC语言与控制器兼容矩阵；
- RT VisualBox的ASSISTA限定；
- MELFA API for Linux与实时ROS2 Driver的职责区分；
- ROS2 Driver与Monitor的协议、频率、支持型号和ROS发行版边界；
- CR800 Modbus TCP和Robot Safety Option的版本/选件约束；
- 工程部署阶段门与未完成事项。

已在《知识生态兼容矩阵》补充MELFA ROS2 Driver / Monitor的Humble静态兼容基线，明确未核验的其他ROS发行版不标记支持。

## 4. 证据来源

- RT ToolBox3产品页：<https://www.mitsubishielectric.com/fa/products/rbt/robot/smerit/rt3/>
- RT ToolBox3 2.80J更新公告：<https://fa-faq.mitsubishielectric.com/fa/products/update/index.html>
- MELFA手册目录（含RT ToolBox3 Ver.Y、RT VisualBox Ver.F、Robot Safety Option等）：<https://www.mitsubishielectric.com/fa/download/search.page?kisyu=%2Frobot&mode=manual>
- RT VisualBox软件页：<https://www.mitsubishielectric.com/fa/sg_en/download/software/detailsearch.page?infostatus=1_6_4&kisyu=%2Frobot&lang=2&mode=software&select=0&shiryoid=1000000194&softid=1&viewpos=&viewradio=0&viewstatus=>
- MELFA API for Linux发布公告：<https://www.mitsubishielectric.com/fa/document/technews/robot/bfp-a6079-0408e/bfp-a6079_0408e.pdf>
- MELFA API for Linux手册：<https://dl.mitsubishielectric.com/dl/fa/document/manual/robot/bfp-a3938/bfp-a3938a.pdf>
- MELFA ROS2 Driver：<https://github.com/MitsubishiElectric/melfa_ros2_driver/tree/humble>
- MELFA ROS2 Driver Releases：<https://github.com/MitsubishiElectric/melfa_ros2_driver/releases>
- MELFA ROS2 Monitor：<https://github.com/MitsubishiElectric/melfa_ros2_monitor/tree/humble>
- CR800 Ethernet Function Manual：<https://dl.mitsubishielectric.com/dl/fa/document/manual/robot/bfp-a3379/bfp-a3379h.pdf>
- CR800 Robot Safety Option Manual：<https://www.mitsubishielectric.com/dl/fa/document/manual/robot/bfp-a3531/bfp-a3531q.pdf>

来源台账编号：#1363–#1373。

## 5. 未完成项与验收边界

本轮未安装RT ToolBox3 2.80J/RT VisualBox，未安装或运行MELFA API for Linux、ROS2 Driver/Monitor，未构建目标MoveIt工作空间，未连接真实CR800/CR860、PLC、手爪、相机或安全回路；未实测周期/延迟/抖动、跟踪误差、通信断线恢复、节拍、负载、力觉、视觉、故障注入、HIL/FAT/SAT或安全性能。

因此：
1. 本报告只证明官方资料和官方GitHub仓库的静态审查已完成。
2. Mitsubishi MELFA档案仍为工程验收未完成。
3. 根任务00-01和第21章21-02继续进行中。
4. TODO-EXT-001（MotionControlAlgorithms合并）继续保持未授权；本轮没有复制或合并其代码。
