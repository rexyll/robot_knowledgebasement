# 14-LeRobot故障传播与断连恢复控制边界核验

> 状态：进行中
> 
> 目的：在 25-14 官方手册、接口与保护机制深度核验中，继续确认 LeRobot SO-Follower 从电机总线异常到上层控制循环的异常传播路径，重点回答“通信失败后是否自动继续发送动作”“disconnect 是否必然卸载扭矩”“是否存在自动重连/自动重新使能扭矩”。

## 1. 本轮证据范围

本轮核对的是 LeRobot 当前公开 `main` 源码，包括：

- `SOFollower.send_action()` / `get_observation()` / `disconnect()`；
- `SerialMotorsBus.disconnect()` / `disable_torque()` / `enable_torque()`；
- 当前 `lerobot-teleoperate` 控制循环的异常与 `finally` 结构；
- Isaac → SO-101 示例中的异常处理和最终断开路径。

本轮仍属于静态源码核验：**没有运行 LeRobot，没有连接 SO-101，没有进行故障注入、扭矩卸载或自动恢复实测。**

## 2. SO-Follower 的直接调用边界

当前 `SOFollower.get_observation()` 直接调用 `bus.sync_read("Present_Position")`；`send_action()` 在需要相对目标限幅时先调用 `sync_read("Present_Position")`，随后调用 `bus.sync_write("Goal_Position", goal_pos)`。这些调用没有在 `SOFollower` 方法内部包裹一个“吞掉异常并继续控制”的 `try/except`。因此，如果底层总线调用向上抛出异常，`send_action()` / `get_observation()` 本身不会把该异常转换成“继续下一帧”的成功路径。citeturn758599search3

这意味着必须把“底层失败后控制循环是否继续”放到具体上层脚本/运行时分析，不能仅根据 `SOFollower` 类判断。

## 3. 当前 teleoperate 主循环的结论

当前公开 `lerobot_teleoperate.py` 的控制循环在每个周期执行处理后的动作发送；其正常控制路径没有围绕 `robot.send_action()` 建立一个“通信异常 -> 忽略 -> 下一周期继续发送”的通用恢复分支。源码的 `finally` 用于结束会话后的清理。citeturn948599search3

因此，在当前已核对的标准 teleoperate 路径中，**不能把通信异常解释为会自动继续发送动作**。相反，若 `send_action()` 的底层异常未在更高层捕获，它会沿调用栈退出当前控制循环，最终进入清理路径。

需要注意：不同任务脚本、rollout 策略和用户自定义控制循环可能有不同异常策略；不能把一个入口脚本的行为泛化成整个 LeRobot 框架的统一故障状态机。

## 4. disconnect 与扭矩卸载边界

`SOFollower.disconnect()` 将 `disable_torque_on_disconnect` 配置传给 `bus.disconnect()`。默认配置为 `True`。citeturn948599search1turn948599search2

`SerialMotorsBus.disconnect(disable_torque=True)` 的实现是：如果已连接，先尝试 `disable_torque(num_retry=5)`，然后在 `finally` 中关闭串口。其文档明确指出：即使禁扭矩失败，串口仍会释放；而无响应的电机可能仍处于 torque-enabled。citeturn948599search0

因此：

1. `disconnect()` **默认尝试**卸载扭矩；
2. `disconnect()` **不保证**所有电机实际已卸载；
3. 失联轴无法通信时，软件无法仅凭串口关闭证明其物理扭矩已经为 0；
4. 因此 `disconnect()` 不能作为独立硬件急停/安全断能回路的替代品。

## 5. disable_torque 的失败语义

`SerialMotorsBus.disable_torque()` 调用底层 `_set_torque(..., False, num_retry)`；如果存在无法到达的电机，底层失败列表会被转换为 `ConnectionError`，错误信息包含电机名称、ID 和失败原因。其文档同时明确指出：失败电机可能仍保持 torque-enabled。citeturn948599search0

因此建议安全状态机继续保留：

`NORMAL → DEGRADED → FAULT_LATCHED → SAFE_OFF_UNCONFIRMED → MANUAL_RESET_REQUIRED`

其中 `SAFE_OFF_UNCONFIRMED` 的含义是：软件已经发出关闭扭矩的请求，但尚未通过逐轴有效反馈证明全部执行完成。

## 6. 是否存在自动重连 / 自动重新使能扭矩

在本轮核对的 `SOFollower` 与标准 teleoperate 路径中，没有发现“电机通信异常后自动 reconnect，再自动 enable_torque，然后继续控制”的内建路径。`SOFollower.disconnect()` 是结束连接的清理动作，而不是自动恢复动作。citeturn758599search3turn948599search3

同时需要特别区分 `SerialMotorsBus.torque_disabled()`：该 context manager 是**配置期间临时关闭扭矩并在退出时重新 enable**的工具，不应被解释成“故障恢复机制”。citeturn948599search0

## 7. 异常分类继续保持三层分离

后续验证继续按以下三层记录：

1. **总线/传输异常**：I/O、timeout、无响应、坏包、CRC 等；
2. **Status Packet error byte**：状态包中的错误/报警字段；
3. **STS 地址 65 `Status`**：独立的状态寄存器。

其中 Feetech 的 alarm-only 行为不能简化成“写入一定被拒绝”，同样不能把普通 `sync_write()` 成功当成六轴已经逐轴确认执行。上述结论需与实际安装的 rustypot 版本共同锁定。

## 8. 对安全需求的直接影响

对于 SO-101 这类有人在环的桌面机械臂，建议项目验收至少要求：

- 控制循环遇到单轴通信失败时进入可观测故障态，而不是依赖“异常自然退出”作为完整安全策略；
- 故障后不得自动重新使能扭矩，除非经过明确的人工复位/恢复状态机；
- 软件 disconnect 只作为软件层清理，不能替代硬件急停/断能；
- 需要逐轴记录 disable-torque 的结果，特别是“命令已发出”与“已确认卸载”必须分开；
- 对异常退出后的实际舵机状态，需要通过受控实验确认，而不是从 Python 返回值推断。

## 9. 未完成项

以下仍未完成，因此本节点不能标记“已完成”：

- 真实 SO-101 控制板 SKU / PCB Rev / 固件确认；
- 目标环境实际 `lerobot` / `rustypot` 版本和 lockfile 固化；
- 实机单轴掉线、坏包、状态报警、地址 65、disable-torque 失败测试；
- 故障后物理扭矩状态确认；
- 自动恢复/人工复位策略的实机验证；
- 控制板供电、保险丝、TVS、过流/欠压/掉电行为验证。

## 10. 结论

本轮可以确认一个重要的软件边界：**当前 SO-Follower 自身不会把底层 `sync_read/sync_write` 异常静默转换成“继续下一帧发送动作”；标准 teleoperate 路径也没有被本轮源码证据证明存在故障后的自动重连和自动重新使能扭矩。**

但这仍然不是“发生异常后一定物理安全”的证明。`disconnect()` 的默认卸扭矩是尽力而为，失联轴可能无法确认卸载；最终安全性仍必须由硬件断能设计、故障状态机和实机测试共同闭环。
