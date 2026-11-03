# 16-SyncWrite动作发送与逐轴确认边界核验

> 状态：进行中
> 目的：核实 SO-Follower 的 Goal_Position Sync Write 在单轴不响应、状态报警和写入拒绝场景下到底能确认什么，避免把“函数返回成功”误写成“六轴均已执行”。

## 1. 证据范围

本轮核对当前公开 LeRobot SO-Follower、Motors API 与 rustypot 1.13.1 Changelog/README。仍属于静态源码与官方文档核验，没有运行 LeRobot、没有连接 SO-101，也没有进行掉线、坏包或写入拒绝注入。

## 2. SO-Follower 当前动作路径

当前 `SOFollower.send_action()` 在需要时先通过 `sync_read("Present_Position", num_retry=...)` 获取当前位置，然后直接调用 `self.bus.sync_write("Goal_Position", goal_pos)`；方法本身没有把 Sync Write 包装成逐轴确认流程。citeturn175298search0

因此，当前应用层动作路径的语义是“把一组目标位置发送到总线”，不是“发送后逐轴读取确认每个舵机已经接受并执行目标”。

## 3. Sync Write 的核心信息边界

LeRobot Motors API 明确说明 `sync_write` 不等待电机应答；与单电机 `write` 不同，Sync Write 的优势是速度快，但丢包会被忽略。其 `num_retry` 参数即使使用，也是在端口失败后重新发送整个 group，而不是获得每个舵机的逐轴确认。citeturn175298search1

因此必须区分：

- **发送路径成功**：本地总线调用没有报告端口失败；
- **报文到达**：不能从 Sync Write 返回值直接证明；
- **舵机接受**：不能从 Sync Write 返回值逐轴证明；
- **舵机执行**：更不能从 Sync Write 返回值证明；
- **动作后的实际位置/扭矩/报警状态**：必须通过后续读取或独立反馈获得。

## 4. 写入拒绝与报警不能混为一谈

rustypot 1.13.0/1.13.1 对带状态错误字段的写操作进行了更细的区分：电机真正拒绝写入时可以报告 `StatusPacketError`/Python `RuntimeError`；但 Feetech 的 alarm-only 状态字节只报告报警，不应直接解释为写入拒绝。citeturn175298search2

这意味着即便使用带 error field 的底层 API，也应把“报警”“通信失败”“写入拒绝”分别记录。当前 SO-Follower 的普通 `sync_write` 路径并没有把这些逐轴状态反馈纳入动作发送返回值。citeturn175298search0turn175298search1

## 5. rustypot 的重试边界

rustypot 的通用 retry 语义针对总线层失败，例如 timeout 或损坏状态包；版本说明明确指出，电机带故障响应而非通信失败时不会按同一机制重试。citeturn175298search2

对本项目而言，应避免把 `sync_write` 的 retry 解释成“确认写入成功”。它最多降低一次总线发送失败造成的丢动作概率；如果需要确认某轴实际接受/执行目标，必须增加独立读回或状态确认机制。

## 6. 单轴异常下的安全含义

如果六轴 Sync Write 中某个轴没有收到、没有接受或者因保护状态没有执行目标，其他轴仍可能已经执行目标。当前 Sync Write 返回路径不能提供完整的逐轴成功矩阵。因此在有人在环的控制系统中，不能仅依据 Sync Write 返回成功继续推导“机械臂状态一致”。

建议故障策略至少区分：

`COMMAND_SENT` → `FEEDBACK_CONFIRMED` / `FEEDBACK_MISSING` / `SERVO_ALARM` / `SERVO_REFUSED` → `FAULT_LATCHED`

其中 `COMMAND_SENT` 不应自动升级为 `FEEDBACK_CONFIRMED`。

## 7. 建议的实机验收项目

后续实机测试应覆盖：

- 单轴断开后执行六轴 Sync Write，记录返回值、总线波形/抓包和各轴实际位置；
- 单轴产生 Feetech alarm-only 状态时执行 Sync Write，确认是否继续动作以及报警是否可被独立观测；
- 构造真实写入拒绝场景，确认底层带 error API 与普通 Sync Write 的差异；
- Sync Write 后立即逐轴读取 `Present_Position`、`Status` 和必要的 Torque/健康寄存器，建立动作反馈延迟；
- 测量重试次数、通信耗时与控制周期抖动；
- 验证单轴异常后是否仍继续发送下一控制帧；
- 验证故障后人工复位与重新使能流程，而非自动恢复。

## 8. 当前结论

可以确认：**SO-Follower 当前 Goal_Position 路径使用 Sync Write，而 Sync Write 本身不等待舵机应答；因此其返回成功不能证明六轴逐轴收到、接受并执行目标。** LeRobot 文档明确把这一点描述为 Sync Write 的速度/可靠性边界。citeturn175298search0turn175298search1

同时，rustypot 已具备更细的错误字段与写入拒绝判别能力，但这些能力没有自动变成当前 SO-Follower 的逐轴动作确认机制。citeturn175298search2turn175298search3

## 9. 未完成项

- 目标 SO-101 实际安装版本与 lockfile 固化；
- 控制板 SKU / PCB Rev / 固件确认；
- 单轴掉线、报警、拒写实测；
- Sync Write 抓包及逐轴执行确认；
- 动作反馈时序和控制周期抖动测量；
- 故障后的硬件断能与人工复位验证。

因此 25-14 仍保持“进行中”。
