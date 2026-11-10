# Stäubli ROS 2—控制错误传播、停止路径与恢复授权审计

- 审计节点：§9.3.273 / SERVO-856
- 日期：2026-11-10
- 固定上游：`ICube-Robotics/staubli_driver_ros2@bd658e2d266e315d2ee35f985fb352ea88306b79`
- 方法：固定提交C++/VAL3源码与现有测试、文档静态审查；未执行动态测试。
- 重点文件：VAL3 `controlTask.pgx`、`Comm/resetControlSocket.pgx`、`Control/stopJointPositionControl.pgx`、`Control/stopJointVelocityControl.pgx`；C++ `robot_driver.cpp`、`staubli_hardware_interface.cpp`；官方仓库日志与troubleshooting文档。

## 1. 核心发现

### 1.1 VAL3运行时错误标志的发布时序导致状态消息可能看不到错误

`controlTask`每轮顺序为：`updateState` → 填充并编码/发送RobotState（其中`bInError = l_bError`）→ 接收/解码命令 → 计算序号延迟/模式切换 → 执行运动 → 错误处理。

多数运行时错误（接收错误、解码错误、序号延迟超限、模式切换错误、运动更新错误、发送状态错误）是在本轮RobotState发送之后产生。随后同一轮错误处理分支执行`stopMove()`、`resetMotion()`并将`l_bError = false`，然后进入下一轮。

因此，对在本轮错误处理分支内被清除的错误，下一轮发布RobotState时`bInError`已经是false。状态消息存在运行时错误标志丢失/不可观测风险；错误日志可能保留，但ROS侧`error_state`/supervision in_error不保证看到该瞬时错误。只有错误处理尾部socket reset失败后再次置位等特殊路径，才可能跨轮保留该标志。该发现是源码控制流推导，需通过逐周期日志与ROS topic实测确认。

### 1.2 错误处理清除故障标志早于恢复条件确认

错误处理分支在执行`stopMove()`和`resetMotion()`后，将命令类型置为0、模式置为0，并立即清除`l_bError`；随后重置序号、通信标志、控制活动状态和命令有效标志，再调用`resetControlSocket`。代码注释明确提出“是否增加恢复延迟（例如1000ms）”仍为TODO。

代码确实要求从STOP模式切换到运动模式，且若上一周期仍在运动会拒绝新运动命令；但没有独立的故障锁存、人工确认/安全重启确认、恢复等待时间、重新授权token或新的session epoch。STOP模式转换规则不等同于故障复位授权。不能据此认定存在安全级恢复互锁。

### 1.3 resetControlSocket不检查底层配置/清缓冲调用结果

`resetControlSocket.pgx`依次调用：
- `sioCtrl(socket, "timeout", -1)`
- `sioCtrl(socket, "endOfString", 10)`
- `clearBuffer(socket)`

程序不检查调用结果，最后无条件设置`x_bError = false`。因此调用者无法从输出参数判断超时设置、行结束配置或缓冲清理是否失败。controlTask中的调用方虽检查`l_bErrorTmp`，但该值被被调函数无条件清零，检查形同虚设。该结论不推断具体VAL3 API在所有运行时异常下的返回机制，需目标控制器API文档和故障注入确认。

### 1.4 STOP/ERROR执行分支没有统一验证每个运动模式的停止结果

1. 正常进入STOP分支时，若上一命令模式为位置2，会调用`stopJointPositionControl`；若为速度3，会调用`stopJointVelocityControl`。随后调用`stopMove()`和`resetMotion()`。
2. 但若在当前速度模式3的命令更新函数中发生错误，错误处理专用分支只在`l_nCmdMode == 2`时调用`stopJointPositionControl`；没有对应的`stopJointVelocityControl`调用。之后虽调用通用`stopMove()`/`resetMotion()`，但速度模式专用停止状态、API调用完成与零速确认均未被显式核验。
3. `stopJointPositionControl`仅在`$movejSyncState() != -1`时调用`$movejSyncEnd()`，随后无条件将`x_bError=false`；固定源码没有停止后静止/速度阈值回读确认。
4. 这不是安全停止性能或安全等级证明；普通VAL3运动API、STOP命令和`resetMotion`不能替代CS9安全功能及独立安全回路。

### 1.5 C++硬件错误回调忽略STOP命令发送结果

`StaubliHardwareInterface::on_error`在driver已连接时调用`robot_driver_->send_stop_all_command()`，但忽略返回值，随后返回`CallbackReturn::SUCCESS`。因此生命周期错误回调报告成功只代表回调路径返回成功，不证明STOP命令已经成功发送或机器人已停止。若driver未连接则返回ERROR；两条路径都没有对STOP后的机器人静止状态进行回读确认。

### 1.6 ROS 2 read/write错误与VAL3内部错误恢复是不同层次

`StaubliHardwareInterface::read`在driver未连接、读取状态失败或状态更新失败时返回`hardware_interface::return_type::ERROR`；`write`在未连接、状态错误/INVALID或命令发送失败时也返回ERROR，并可能尝试发送STOP。硬件组件的`on_error`回调随后尝试发送STOP，但忽略发送结果。该生命周期处理与VAL3 controlTask内部清除`l_bError`、重置UDP socket并重新接收命令是两个独立状态机；固定代码未见跨层恢复握手或确认闭环。

## 2. SERVO-856验收矩阵

| ID | 验收项 | 状态 |
|---|---|---|
| ER1 | RobotState发布与错误处理顺序 | 静态确认：先发布、后处理错误 |
| ER2 | bInError瞬态可见性 | 静态控制流推导存在漏报风险；需ROS topic验证 |
| ER3 | 错误锁存与复位授权 | 未发现独立故障锁存/人工确认/重新授权机制 |
| ER4 | 恢复延迟 | 源码TODO，未实现/未验证 |
| ER5 | resetControlSocket调用结果 | 静态确认未检查，输出无条件false |
| ER6 | 位置/速度错误停止分支对称性 | 静态确认速度错误分支缺少专用stop函数调用 |
| ER7 | 停止完成/静止回读确认 | 固定代码未发现 |
| ER8 | C++ on_error STOP结果 | 静态确认返回值被忽略 |
| ER9 | ROS2 lifecycle与VAL3错误恢复联动 | 未发现端到端握手/确认 |
| ER10 | 断链、错误、恢复、重授权故障注入 | 未执行 |
| ER11 | CS9停止响应、静止回读及安全链验证 | 未执行 |
| ER12 | SIL/HIL、FAT/SAT、实机验收 | 未执行/缺现场证据 |

## 3. 整改建议

1. 将错误事件锁存到至少一个明确可观察的RobotState周期，或引入独立单调递增error counter、latched fault code和时间戳；只有在错误已被ROS侧确认/记录后才能清除可观测事件。
2. 将“通信恢复”“运动停止”“控制器故障复位”“安全系统允许重启”“ROS重新授权”拆分为不同状态；恢复默认禁止运动。
3. 引入显式恢复握手：控制器故障/安全状态满足条件、机器人静止确认、operator safety restart完成、通信session重新建立、STOP/空命令同步、上位控制器重新激活后，才允许运动命令。
4. 对resetControlSocket每个调用检查可用的错误/返回状态；若API无可检查返回值，使用可验证的后置条件（socket状态、缓冲状态、收发探测）并在失败时保持故障锁存，不得无条件返回成功。
5. 统一位置/速度停止路径，明确每种模式的停止API、错误处理、超时、静止判据和失败后的升级路径；任何停止失败必须保持故障锁存。
6. C++ on_error检查send_stop_all_command返回值；失败应记录独立故障、保留生命周期错误，并不得将回调成功解释为机器人已停止。STOP发送后应等待新的、有效且新鲜的静止状态证据。
7. 明确ROS2 hardware lifecycle状态、VAL3控制状态和CS9安全状态的转换表，测试每条转换的前置条件、失败回退和重新激活条件。
8. 安全停止与安全重启必须依据CS9安全功能文档、风险评估和经验证的安全回路进行独立验收；不得将普通软件STOP、GPIO或ROS lifecycle回调当作安全功能。

## 4. 验证边界

本轮仅对固定提交源码、现有测试及仓库文档作静态审查。未运行C++构建/单测、VAL3 Studio编译/下载、网络故障注入、STOP API失败注入、ROS topic逐周期观测、CS9实际停止/静止回读、操作员安全重启验证、SIL/HIL、FAT/SAT或实机测试。VAL3 API返回语义、CS9具体停止行为、错误标志在真实任务调度中的可见性及安全恢复要求，均需目标控制器版本文档和现场证据补齐。

未修改上游仓库，未应用PR。Stäubli工程级验收仍未通过；`TODO-EXT-001`未授权合并。根00-01与第21章21-02继续进行中。

**下一节点：§9.3.274 / SERVO-857。**
