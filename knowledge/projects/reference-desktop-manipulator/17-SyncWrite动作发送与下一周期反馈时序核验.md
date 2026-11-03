# 17-SyncWrite动作发送与下一周期反馈时序核验

> 状态：进行中
> 目的：核实当前 LeRobot teleoperate 控制循环中，`get_observation()`、`send_action()` 与下一控制周期的关系，明确动作发送后的反馈究竟属于当前命令的同步确认，还是下一周期观测。

## 1. 证据范围

本轮核对当前公开 LeRobot `lerobot_teleoperate.py`、Robot API 与 SO-Follower/通用硬件接口说明。仍属于源码与官方文档静态核验，没有运行 LeRobot、没有连接 SO-101，也没有做实机时序抓包或动作延迟测量。

## 2. 标准 teleoperate 主循环顺序

当前 `teleop_loop()` 每个控制周期的顺序是：

1. `timer.tick()`；
2. `robot.get_observation()`；
3. `teleop.get_action()`；
4. teleop action processor；
5. robot action processor；
6. `robot.send_action(robot_action_to_send)`；
7. 可选 telemetry/显示；
8. `timer.wait()`，等待到目标 FPS；
9. 进入下一次循环。citeturn217368search0

因此，**当前周期读取的 `obs` 发生在当前周期动作发送之前**。当前周期没有在 `send_action()` 返回后强制再执行一次 `get_observation()` 作为 post-action readback。

## 3. 下一周期才读取新的机器人观测

由于下一轮循环再次从 `robot.get_observation()` 开始，所以在标准 teleoperate 路径下，动作发送后的机器人位置反馈通常会在**下一控制周期的 observation 阶段**才被读取。这个读取是周期性观测，不是 Sync Write 的同步 ACK。citeturn217368search0turn217368search3

对于 SO-Follower，前序核验已经确认其常规 `get_observation()` 主要读取 `Present_Position`；因此它能够形成的自然闭环更接近：

`上一周期观测 → 当前目标发送 → 下一周期位置观测`

而不是：

`当前目标发送 → 当前命令逐轴 ACK → 当前命令执行确认`。

## 4. send_action() 返回值不能改变这个语义

LeRobot Robot API 对 `send_action()` 的定义是返回“实际发送到电机的 action”，例如经过安全限制后实际发送的目标值；它不是舵机反馈确认值。citeturn217368search7

因此即使调用方接收返回值，也不能把它解释成 `Present_Position`、Torque Enable、Status 或逐轴执行成功矩阵。

## 5. 控制周期的实际含义

标准循环在发送动作后进入 `timer.wait()`。如果 `get_observation()`、动作处理或 `send_action()` 本身已经耗时较长，等待时间会相应减少；如果本周期已经超过目标周期，则不会额外等待到完整 FPS 周期。源码注释也明确说明该循环以目标 FPS 为上限/节拍，并报告实际循环耗时。citeturn217368search0

因此，**不能仅从配置的 FPS 推断“发送后已经经过固定的舵机执行确认时间”**。真正的反馈延迟需要实机测量，包括串行往返时间、舵机内部更新周期和机械响应。

## 6. 故障传播边界

标准 teleoperate loop 没有在 `send_action()` 后增加独立的逐轴确认步骤。如果 `get_observation()` 或 `send_action()` 抛出未处理异常，当前 `teleop_loop()` 本身没有通用的“捕获通信异常 → 自动重连 → 重新使能扭矩 → 从原状态继续”的逻辑；外层主要处理 `KeyboardInterrupt`，最终执行 disconnect。citeturn217368search0

因此，本项目建议把以下状态严格区分：

- `OBSERVED_PRE_ACTION`：本周期动作发送前读到的机器人状态；
- `COMMAND_SENT`：本周期发送路径返回；
- `NEXT_CYCLE_OBSERVED`：下一周期重新读到的位置等反馈；
- `FEEDBACK_CONFIRMED`：只有在定义并验证了明确的逐轴确认条件后才能使用；
- `FAULT_LATCHED`：通信、报警或反馈不满足安全条件时进入锁存故障。

其中 `NEXT_CYCLE_OBSERVED` **不能默认等同于** `FEEDBACK_CONFIRMED`：需要进一步定义位置误差阈值、允许的响应延迟、状态/报警条件和连续帧判据。

## 7. 当前可建立的最小软件闭环

基于现有调用链，可以建立的最小证据链是：

`OBS(t)` → `COMMAND(t)` → `OBS(t+1)`

其中 `OBS(t+1)` 可以用于观察上一命令造成的状态变化，但不能单独证明上一命令“被六轴全部接受”。如果要形成工程上可审计的动作确认，应增加：

1. 命令序列号或时间戳；
2. 每轴发送记录；
3. 下一周期每轴 `Present_Position`；
4. 每轴 `Status` / error field（若底层 API 路径允许）；
5. Torque Enable / 必要健康寄存器；
6. 位置误差与允许响应时间判据；
7. 缺失反馈时的故障锁存和停止发送策略。

这些是本项目建议的安全闭环设计，不是当前 LeRobot SO-Follower 已经实现的功能。

## 8. 与其他 LeRobot 控制循环的一致性

当前 `lerobot_teleoperate.py` 的通用循环和其他示例也采用“先观测、后动作”的结构。例如 Isaac SO-101 示例也是每周期先 `robot.get_observation()`，再计算 action，随后 `robot.send_action(action)`，然后按 FPS 等待。citeturn217368search1

这进一步支持：标准控制循环的 observation 是动作计算/发送前的状态采样，而不是动作发送后的同步确认。

## 9. 实机验收计划

后续必须通过实机时间戳/抓包验证：

- `Present_Position` 读回相对 `Goal_Position` 写入的最小/典型/最大延迟；
- 六轴是否在同一控制周期内均完成可观测响应；
- 单轴掉线时下一周期 observation 如何表现；
- Status/error field 是否能与对应命令时间关联；
- 连续控制周期中发送频率与读回频率的实际抖动；
- 是否存在“上一周期命令尚未达到机械响应稳定状态，下一周期已发送新命令”的情况；
- 故障出现后是否按预定策略停止后续动作，而不是继续发送下一帧。

## 10. 当前结论

可以确认：**标准 LeRobot teleoperate 路径是“先读 observation，再发送 action，再等待进入下一周期”；没有默认的 post-action Sync Read，因此当前 SO-Follower 的下一次 `Present_Position` 读取最多构成下一周期反馈，不构成当前 Sync Write 的同步逐轴 ACK。** citeturn217368search0turn217368search7

这使本项目在 25-14 中必须继续区分“发送成功”“下一周期观察到变化”和“逐轴执行确认”，不能把三者合并。

## 11. 未完成项

- 目标 SO-101 实际运行环境与 lockfile 固化；
- 实机控制周期、串行往返和动作反馈延迟测量；
- Sync Write 抓包与六轴逐轴响应关联；
- Status/error field 与动作时间戳关联验证；
- 单轴异常后停止发送、故障锁存与人工恢复实测；
- 控制板 SKU / PCB Rev / 固件及供应商资料确认。

因此 25-14 继续保持“进行中”。
