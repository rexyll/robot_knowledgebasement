# Stäubli ROS 2—VAL3通信故障传播、任务调度与恢复闭环审计

- 审计节点：§9.3.267 / SERVO-850
- 日期：2026-11-10
- 固定上游：`ICube-Robotics/staubli_driver_ros2@bd658e2d266e315d2ee35f985fb352ea88306b79`
- 审查方式：固定提交静态源码、配置和现有测试代码审查；未执行动态测试。
- 范围：VAL3 `controlTask.pgx`、`Comm/readData.pgx`、`readDataOnce.pgx`、`sendData.pgx`、`resetControlSocket.pgx`、`start.pgx`、`stop.pgx`；C++ `RobotDriver`、`RealTimeSocketSubscriber`、`RealTimeSocketInterface`、UDP socket实现及`StaubliHardwareInterface`生命周期/读写路径。

## 1. 主要结论

### 1.1 VAL3接收路径没有形成完整的超时/失联判定

1. `readDataOnce`调用`sioGet`后，仅在返回字节数等于缓冲区长度时置新数据；正数但长度不匹配时置错误。返回0或负数时没有进入错误分支，表现为“本次无新数据”。这是代码分支事实；负返回值在目标CS9/VAL3版本中的精确定义仍需官方API契约和目标运行验证。
2. `readData`每个控制周期最多尝试两次读取。若第一次读到完整报文、第二次无新数据，则返回并保留第一次读到的最新报文；若连续无数据，则本轮不更新命令。
3. `controlTask`在没有新报文但旧命令仍有效时，专门检查旧命令staleness的代码仍为TODO。现有序号延迟检查不能等同于独立的wall-clock heartbeat/watchdog。
4. 现有序号延迟门禁仅在`l_bControlActive`为true且命令有效时运行：延迟大于3个周期仅告警；运动中大于5触发错误/STOP；静止时大于25触发错误/STOP；负延迟也触发错误。注释将其解释为运动中约20ms、静止时约100ms，控制周期在`start.pgx`设为4ms。门禁依赖状态帧序号和命令序号，未发现独立心跳计时器、明确失联阈值配置或任务周期健康监控闭环。
5. `l_bPreviousRxError`在控制循环中赋值，但固定程序中未发现其参与恢复决策；启动阶段的监督/诊断任务仍是TODO。

### 1.2 VAL3发送错误有检测，但socket复位成功状态不可被可靠确认

1. `sendData`检查`sioSet`返回字节数是否等于发送缓冲区长度；不相等时将错误标志置true。
2. 状态帧发送失败会令`l_bTxError`为true，随后置`l_bError`。但本周期仍会继续接收/解析命令及执行后续模式分支，错误处理在本周期后段才统一运行；状态帧又是在命令处理前发布，因此当前周期故障不保证出现在同一帧状态反馈中。
3. `resetControlSocket`依次调用`sioCtrl(timeout,-1)`、设置行结束符、`clearBuffer`，随后无条件写`x_bError=false`。没有检查这些调用的结果，也没有返回可验证的复位阶段状态。调用方的`l_bErrorTmp`失败检查因此不能证明底层复位操作成功。
4. 错误处理将运动置STOP、调用`stopMove`/ `resetMotion`，使命令无效、重置序号与控制活动标志，再清理socket缓冲区。错误标志随后被清除；仅当复位调用报告错误时才重新置位。代码还留有“接受新命令前增加延时”的TODO，没有显式静默期、握手或会话epoch。
5. `start.pgx`在启动时清除control socket buffer并创建4ms同步任务；监控/诊断任务未实现。`stop.pgx`只执行停止运动、resetMotion和清除socket buffer，没有显式等待controlTask退出或证明任务已终止。该任务启停问题在既有任务审计中已出现，本轮将其纳入恢复闭环，不将其误报为首次发现。

### 1.3 ROS 2侧将连接就绪与状态新鲜度分开处理，但没有自动重连闭环

1. `RobotDriver::is_connected()`检查控制/诊断socket已连接且接口/接收线程ready；该函数不检查RobotState时间戳是否新鲜。故“connected”不等于控制器持续在线或状态有效。
2. `read_robot_state`从latest-message缓存取状态，检查消息类型和staleness timeout（默认100ms）；状态过期时返回false。硬件`read()`据此返回hardware_interface::ERROR。错误帧反序列化失败时subscriber只记录日志、不覆盖有效消息缓存；旧消息仍留在缓存，随后由staleness检查拒绝。
3. `connect()`等待首个有效RobotState并在连接阶段检查一次协议版本；诊断数据读取仍为TODO且`diag_interface_ready`被硬编码为true。连接成功后未见持续协议版本/会话epoch门禁。
4. `disconnect()`停止接收线程、断开socket并重置本地状态序号/消息类型；未发现自动重连调度器。硬件`on_configure()`连接失败返回ERROR；`on_cleanup()`断开；`on_error()`在仍连接时尝试发送STOP；`on_shutdown()`按缓存控制状态决定是否发送STOP后断开。相关STOP发送结果没有形成控制器停止确认。
5. `on_activate()`只将运动控制模式设为STOP；未发现重新握手、等待新鲜首帧、会话代次检查或清除GPIO输出缓存的完整恢复步骤。此前SERVO-847/849已记录GPIO缓存生命周期和VAL3物理GPIO执行缺口，本轮不重复计为新发现。
6. UDP异步接收错误仍会进入回调并尝试重新投递接收；来源地址过滤仍为TODO。该风险在既有UDP审计中已记录，本轮将其作为故障传播依赖项，而非新增发现。

### 1.4 STOP与普通GPIO状态不能构成安全恢复证明

1. ROS侧`send_stop_all_command()`是软件通信命令；发送函数成功最多表示本地接口接受了发送路径，不代表控制器已接收、执行或机器人已静止。
2. VAL3错误路径明确停止运动，但数字/模拟GPIO物理输出仍为TODO。故障、STOP、socket reset或任务停止均不能据此推断物理端子进入零值、保持值或任何预定义安全态。
3. 普通GPIO及ROS/UDP软件STOP不能替代急停、保护停止、STO、SS1/SS2、安全PLC或经认证的安全链路。

## 2. SERVO-850验收矩阵

| ID | 验收项 | 状态 |
|---|---|---|
| RC1 | VAL3单次接收完整帧/短帧/无数据分支 | 固定提交静态审查完成；SIO返回值真实语义未验证 |
| RC2 | 每周期双次读取与新旧命令缓存行为 | 静态确认最多两次读取；动态覆盖/时序未执行 |
| RC3 | 无新命令时旧命令staleness/watchdog | 静态确认专用检查为TODO |
| RC4 | 序号延迟门禁、阈值和触发条件 | 静态确认3/5/25周期门槛；物理时间和丢帧行为未测 |
| RC5 | VAL3发送字节数错误传播 | 静态确认`sioSet`长度比较 |
| RC6 | resetControlSocket错误传播 | 静态确认无结果检查且无条件清除错误标志 |
| RC7 | 错误处理STOP、序号/命令状态复位 | 静态确认代码顺序；目标控制器执行效果未测 |
| RC8 | ROS socket readiness与状态新鲜度区分 | 静态确认`is_connected`不检查staleness，read单独检查 |
| RC9 | connect首帧/协议检查与断开后恢复 | 静态确认连接阶段门禁；未发现自动重连/会话握手 |
| RC10 | ROS lifecycle错误/关闭/清理STOP行为 | 静态确认回调路径；未注入生命周期故障 |
| RC11 | UDP异步接收错误与来源验证 | 固定提交静态确认错误回调/来源校验TODO；与既有审计交叉引用 |
| RC12 | GPIO故障默认态与STOP端到端效果 | 未实现/未证明；SERVO-848/849已记录VAL3物理IO缺口 |
| RC13 | VAL3任务启停、重复启动与恢复竞态 | 静态代码边界已检查；目标VAL3任务语义/运行竞态未验证 |
| RC14 | 网络故障注入、重连、旧帧/旧命令重放 | 未执行 |
| RC15 | CS9、SIL/HIL、FAT/SAT及实机安全验证 | 缺少证据，未执行 |

## 3. 整改建议

1. 将VAL3通信状态显式建模为DISCONNECTED、INITIALIZING、READY、STALE、FAULT、RESETTING、RECOVERING；所有转移记录原因、时间戳、序号和复位结果。错误不得在未确认复位成功时清除。
2. 为命令流加入独立heartbeat/接收超时（按控制模式分别设定），不只依赖状态序号差；旧命令超过阈值必须明确失效，且恢复后必须收到新会话/新鲜命令。
3. 复位函数逐项检查并传播`sioCtrl`、`clearBuffer`及任务状态错误；复位失败进入锁存故障，不得报告恢复成功。定义可验证的静默期、握手、session/boot epoch和序号重新同步。
4. 对状态帧发送失败、命令帧接收错误、畸形帧、序号回退、控制器重启、socket重建、任务退出失败分别定义故障响应、日志/诊断码和人工复位条件。
5. ROS 2侧区分transport-ready、valid-state-ready、fresh-state-ready、control-authorized；read超时应使状态有效性显式失效。自动重连必须先清除旧缓存/输出命令，重新验证协议版本、机器人型号/固件、状态新鲜度和控制权，不得自动恢复运动命令。
6. 对on_error/on_shutdown中的STOP发送结果、控制器停止回执和机器人静止确认建立独立记录；任何网络不可达场景都不能把发送失败伪装成停止成功。
7. 补充VAL3任务监督/watchdog、controlTask退出确认、重复启动保护、stop→start同步和控制周期超限诊断。目标VAL3版本API行为需厂商文档及CS9验证。
8. 在VAL3物理GPIO尚未实现前，禁止把软件GPIO接口用于现场执行；GPIO输出安全默认态必须依据真实模块、电气负载和风险分析定义并现场验证。安全功能保持独立认证链路。

## 4. 必须补充的验证

- VAL3/SIO：无数据、0字节、负返回、短帧、长帧、连续突发、socket断开、发送部分失败、clearBuffer失败和sioCtrl失败。
- 故障注入：丢包、延迟、重复、乱序、旧帧重放、非法帧、控制器重启、ROS进程重启、网络恢复、接收线程异常退出。
- 状态机：错误发生在状态发送前/后、运动中/静止、停止模式、重复错误、复位失败、复位后旧命令到达、新会话首帧和首次新命令。
- 生命周期：configure失败、activate/deactivate、read/write返回ERROR、on_error、cleanup、shutdown及重复configure；验证停止回执、缓存清零、状态新鲜度门禁和无自动运动重启。
- 实机：在隔离测试单元由Stäubli授权人员执行CS9/VAL3任务时序、真实IO模块及端子、停止行为、断网恢复和风险评估后的FAT/SAT；安全链路由合格安全人员独立验收。

## 5. 本轮边界与结论

本轮仅对固定上游提交进行静态源码和现有测试代码审查。未运行ROS 2构建/单测、VAL3 Studio导入/编译/下载、CS9仿真、SIO API动态测试、UDP抓包/故障注入、重连/任务启停测试、GPIO端子测试、SIL/HIL、FAT/SAT或实机验证。没有证明目标控制器上的实际故障响应时间、停止距离、任务调度时序或IO端子状态。

未修改上游仓库，未应用PR。Stäubli工程级验收仍未通过；`TODO-EXT-001`未授权合并。根00-01与第21章21-02继续进行中。

**下一节点：§9.3.268 / SERVO-851。**
