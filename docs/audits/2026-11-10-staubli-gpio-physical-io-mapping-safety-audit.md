# Stäubli GPIO物理IO API、型号通道映射与异常输出状态审计

- 审计节点：§9.3.266 / SERVO-849
- 日期：2026-11-10
- 固定上游：`ICube-Robotics/staubli_driver_ros2@bd658e2d266e315d2ee35f985fb352ea88306b79`
- 本仓库目标分支：`main`
- 审计类型：固定提交源码、VAL3工程配置、型号YAML与文档静态审查
- 边界：不修改上游、不应用PR；未执行VAL3 Studio导入/编译/下载、CS9运行或现场IO测试

## 1. 本轮审查问题

承接SERVO-848，检查GPIO是否从ROS接口真正到达控制器物理IO，具体包括：
- VAL3程序是否调用数字/模拟输入读取及输出写入API；
- 是否声明物理IO模块、信号/通道地址或IO映射；
- TX2-60L与TX2-60L MED模型中的数量配置是否能映射到控制器端子；
- STOP、ERROR、通信错误、应用停止、生命周期关闭时是否定义GPIO安全状态；
- 文档与配置是否提供可复现的接线/配置/验收说明。

## 2. 固定提交证据

- [VAL3工程项目 ros2_server.pjx](https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/val3/userapp/ros2_server/ros2_server.pjx)
- [VAL3应用 README](https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/val3/README.md)
- [VAL3通信配置 sio.cfx](https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/val3/configs/sio.cfx)
- [VAL3 controlTask.pgx](https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/val3/userapp/ros2_server/controlTask.pgx)
- [VAL3 updateState.pgx](https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/val3/userapp/ros2_server/updateState.pgx)
- [VAL3 start.pgx](https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/val3/userapp/ros2_server/start.pgx)
- [VAL3 stop.pgx](https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/val3/userapp/ros2_server/stop.pgx)
- [GPIO示例文档](https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_driver_ros2/sphinx/demo_applications/gpios.rst)
- [TX2-60L robot_model.yaml](https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_description/config/tx2_60l/robot_model.yaml)
- [TX2-60L MED robot_model.yaml](https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_description/config/tx2_60l_med/robot_model.yaml)
- [R2C GPIO Xacro](https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_description/r2c/include/staubli_r2c_gpios.xacro)
- [C++ hardware interface](https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/src/staubli_hardware_interface.cpp)

## 3. VAL3物理IO API与工程配置

### 3.1 工程内没有物理GPIO读写调用证据

对固定提交的VAL3 ROS2 server项目程序和数据库进行逐文件检查：
- `updateState.pgx`在“Fill IOs state”区将数字、模拟输入valid flag设为false；未见从控制器IO读取值的API调用。
- `controlTask.pgx`在“Execute GPIO commands”区仍只有数字/模拟输出TODO，没有物理输出写入调用。
- `decodeRobotCommandMsg.pgx`虽读出数字输出mask，但bitmask到`nDigitalOutputs[]`的转换代码被注释；模拟输出只进入RobotCommand数据数组。
- `ros2_server.pjx`将VAL3 Libraries声明为空列表；固定项目内未看到单独GPIO/IO addon库或物理IO映射数据库被引入。
- 对全部48个VAL3程序、类型、数据库及项目文件的本轮检索，没有发现明确的数字/模拟物理IO读写API调用或端子地址配置。

因此，SERVO-848确认的协议层TODO向下延伸到物理IO层：固定提交没有可审计的VAL3 GPIO采集/写入实现。此结论限定于仓库提交；不能排除用户现场另有未纳入仓库的VAL3程序、系统配置或厂商专有IO配置。

### 3.2 SIO配置是网络通信配置，不是GPIO端子映射

`sio.cfx`配置了control和diagnostics两个UDP socket，端口分别为11000、11001，远端地址192.168.0.1，并包含串口配置。该文件没有定义数字输入/输出模块、模拟输入/输出模块、机柜IO槽位、通道索引或端子编号。

VAL3 README说明该文件用于配置控制与诊断通信socket；不能将文件名中的SIO误读为已经配置了物理GPIO模块。

### 3.3 SIO配置文件存在待验证的XML闭合问题

固定提交的`sio.cfx`文本末尾为`<sio>`，而不是根元素闭合标签`</sio>`。按标准XML语法这是疑似不完整的根元素闭合。当前仅做文本静态观察，没有运行XML parser、VAL3 Studio导入或控制器配置导入；应先用实际支持的配置导入器确认文件是否可接受，再判断是否为真实部署阻断项。

## 4. 型号数量配置不等于物理通道映射

TX2-60L与TX2-60L MED的robot_model.yaml均声明：
- digital inputs：16
- digital outputs：16
- analog inputs：2
- analog outputs：2

这些数量经Xacro传递后决定ROS 2导出的接口数量；它们没有说明：
- 控制器IO模块型号、槽位/总线位置；
- 每个逻辑GPIO编号映射到哪个VAL3 IO变量或设备地址；
- 端子编号、公共端、电气类型、输入输出方向；
- 模拟量电压/电流制式、量程、单位、缩放与断线诊断；
- 现场可用通道数是否受机器人选件、控制柜配置或末端工具影响。

两种型号使用相同的数量参数，不能据此推断两种控制柜的IO硬件、选件和端子接线完全相同。配置目前是“ROS接口数量声明”，不是“硬件IO资源清单”。

## 5. STOP、ERROR、通信丢失与生命周期行为

### 5.1 VAL3任务层

- `controlTask.pgx`进入STOP/ERROR路径时执行运动停止相关函数（如`stopMove()`、`resetMotion()`），但GPIO输出执行区仍是TODO。
- 通信读取/解码/序号延迟错误会设置错误状态并走运动停止、清理通信状态和重置socket流程；没有对应GPIO输出复位、保持、断电或安全默认态逻辑。
- `start.pgx`启动任务前执行`stopMove()`和`resetMotion()`；未见GPIO初始化。
- `stop.pgx`退出应用时停止运动并清理socket buffer；未见GPIO输出复位。
- 应用停止/通信异常时物理GPIO的实际电气状态不能从仓库代码确定。由于输出写入本身未实现，不能将“TODO未执行”描述为“输出已安全置零”。

### 5.2 ROS 2 hardware interface层

C++ `write()`无论当前joint control mode是否为STOP，都会把GPIO命令缓存写入RobotCommand消息；STOP分支只将运动command_reference清零，没有显式将GPIO输出数组强制置零。生命周期`on_activate()`只重置joint control mode；`on_cleanup()`断开driver；`on_shutdown()`和`on_error()`发送stop-all命令，但没有专门的GPIO安全态/反馈确认。

结合SERVO-847的缓存审计，ROS侧输出命令可能在STOP时仍随命令帧发送；但VAL3当前未实现数字/模拟GPIO物理写入，因此不能据此推断控制器端子会跟随变化。未来补齐物理输出前，必须同时定义命令缓存生命周期策略和VAL3端失联安全策略。

### 5.3 普通GPIO不得替代安全回路

急停、保护停止、门锁、STO、SS1/SS2及其他安全功能必须使用经过风险评估、认证和验证的安全架构。普通ROS GPIO状态接口、UDP控制消息或通用VAL3任务不能作为安全功能的唯一实现或证明。

## 6. 文档成熟度

`staubli_driver_ros2/sphinx/demo_applications/gpios.rst`的GPIO示例章节内容仅为“Coming soon :)”。因此固定上游没有提供可执行的GPIO用户指南、IO模块配置示例、端子图、变量映射或GPIO现场验收步骤。

VAL3 README提供的是控制器网络socket配置与应用部署步骤；不能代替GPIO硬件配置和调试说明。

## 7. 整改建议

1. **建立物理IO配置清单：** 按机器人型号、CS9控制柜版本、IO选件和模块型号建立版本化配置，列出模块/槽位/通道、VAL3变量/设备API、ROS逻辑通道、端子编号、电气类型及量程。
2. **实现VAL3 IO适配层：** 将厂商API封装为明确的read/write程序，处理API错误、模块离线、通道越界、质量/有效性标志和采样时间；在没有对应硬件的型号上禁用相关ROS接口。
3. **补齐GPIO数据链路：** 完成SERVO-848列出的输入采集/编码、数字位图映射和物理输出执行，并对每个通道建立双向映射测试。
4. **定义安全输出策略：** 为正常STOP、ERROR、通信超时、UDP断连、VAL3任务异常、应用stop、CS9重启分别定义输出状态；明确哪些输出保持、复位或由独立硬件安全逻辑处理，且不得未经风险评估自动将所有输出清零。
5. **补齐文档与配置验证：** 提供GPIO部署示例、CS9 IO配置步骤、接线图、通道表、调试方法和验收表；使用实际VAL3导入工具验证`sio.cfx`语法和兼容性。
6. **现场验收：** 逐点执行输入电平/输出负载测试、模拟量量程和精度测试、断线/短路/模块掉线/通信中断测试；验证状态反馈与独立安全回路。记录控制器序列号、固件、VAL3版本、模块料号、端子图版本和测试仪器校准信息。

## 8. SERVO-849验收矩阵

| ID | 验收项 | 状态 |
|---|---|---|
| PH1 | VAL3程序是否实现数字/模拟输入物理采集 | 固定提交静态审查：未发现实现 |
| PH2 | VAL3程序是否实现数字/模拟输出物理写入 | 固定提交静态审查：未发现实现；controlTask为TODO |
| PH3 | VAL3项目是否声明GPIO addon/library及IO资源映射 | 固定项目Libraries为空；未发现仓库内物理IO映射 |
| PH4 | SIO配置是否包含GPIO硬件通道 | 静态确认只见UDP/串口通信配置，不含GPIO端子映射 |
| PH5 | TX2-60L与MED通道数量配置 | 静态确认均为16/16/2/2；不能证明硬件映射 |
| PH6 | 逻辑GPIO到模块/槽位/端子逐点映射 | 未提供；需厂商硬件资料及现场配置 |
| PH7 | STOP/ERROR/通信丢失时GPIO安全态 | 固定代码未定义；实际端子状态未知 |
| PH8 | start/stop/lifecycle时GPIO输出初始化与复位 | 未发现专门逻辑；需实现并动态验证 |
| PH9 | SIO配置文件XML/VAL3导入合法性 | 文件尾疑似缺少闭合标签；未运行导入器 |
| PH10 | GPIO用户文档和现场验收流程 | 文档仅Coming soon；未完成 |
| PH11 | 模块掉线、通道故障、断线/短路注入 | 未执行 |
| PH12 | CS9端子逐点、模拟量量程与负载测试 | 未执行；缺现场证据 |

## 9. 结论

**固定上游提交中没有形成可审计的VAL3物理GPIO端到端实现或型号级端子映射。** C++和Xacro定义了ROS逻辑接口数量，VAL3消息结构也声明了数组，但VAL3应用没有实际IO采集/写入API调用，SIO配置仅定义网络通信socket，型号YAML没有模块/槽位/端子映射，GPIO文档仍未编写。STOP/ERROR/通信异常时的GPIO电气安全状态也未定义。

本轮仅完成固定提交静态源码、工程配置、型号YAML和文档审查；未执行VAL3 Studio导入/编译/下载、CS9仿真、UDP/IO故障注入、模块通道测试、SIL/HIL、FAT/SAT或实机验证。SIO XML闭合问题仅为静态疑点，待实际导入器确认。Stäubli工程级验收仍未通过，`TODO-EXT-001`未授权合并。
