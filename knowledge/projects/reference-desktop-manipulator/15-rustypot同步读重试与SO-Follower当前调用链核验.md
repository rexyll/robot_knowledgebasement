# 15-rustypot同步读重试与SO-Follower当前调用链核验

> 状态：进行中
> 目的：补充 25-14 对 rustypot 同步读错误定位、重试语义，以及当前 SO-Follower 是否已经把瞬态 Feetech 状态包错误纳入重试的核验。

## 1. 本轮核验范围

本轮核对当前公开 LeRobot 与 rustypot 资料，重点关注：

- SO-Follower `get_observation()` / `send_action()` 对 `num_read_retries` 的传递；
- MotorsBus 同步读的重试边界；
- rustypot 1.12.0 以后 Sync Read 的逐轴错误定位；
- status packet error byte 与通信失败的区别；
- 重试成功是否等价于故障已解除。

仍为静态源码/文档核验，没有运行 LeRobot、没有连接 SO-101、没有做实际掉线或坏包注入。

## 2. 当前 SO-Follower 已存在同步读重试配置

当前 `SOFollower.get_observation()` 调用 `bus.sync_read("Present_Position", num_retry=self.config.num_read_retries)`；当 `max_relative_target` 开启时，`send_action()` 中用于读取当前位姿的 `sync_read` 也传递相同的 `num_read_retries`。当前测试文件明确验证了该参数会被转发。citeturn513855search3turn513855search4

当前 SO-Follower 配置默认 `num_read_retries=2`，即一次同步读失败后最多再尝试两次；这是针对 Feetech 偶发错误状态包导致控制循环中止而加入的应用层缓解措施。该配置不是“无限重连”，也不是故障恢复状态机。citeturn513855search2

## 3. rustypot 的 Sync Read 错误定位已经细化

rustypot 1.12.0 的 Changelog 明确记录：失败的 Sync Read 会报告 `SyncReadError { id, cause }`，能够指出未返回、超时、错误 ID、截断、乱序或 CRC 等原因；快速同步读同样会识别缺失/截短/乱序/CRC 等情况。citeturn513855search0

因此，当前软件栈已经具备比“总线整体失败”更细的逐轴故障定位基础。但这仍是**诊断信息**，不能直接推导某一轴已经进入安全卸载状态。

## 4. status packet error byte 与重试必须分开记录

rustypot 1.12.0 增加了 `*_with_error` API，使调用方能够看到状态包中的 error field；同时保留普通 `read`/`write`/`sync_read` API 的既有语义。1.13.0/1.13.1 又进一步区分“报警”和“电机拒绝写入”：Feetech 的 alarm-only 状态字节不应直接解释为写入拒绝。citeturn513855search0

因此项目测试日志至少应分别记录：

1. 是否收到状态包；
2. 状态包是否完整且 CRC 正确；
3. error byte 原始值及解释；
4. rustypot 是否将此次访问判定为 refusal；
5. 是否触发 `num_retry`；
6. 重试最终是否成功；
7. 成功后该轴的实际 Torque Enable / Status / 位置等状态。

不能只记录“sync_read 最终成功”，否则无法判断中间发生过瞬态报警、坏包还是掉线。

## 5. 重试的安全边界

`num_read_retries=2` 只能降低偶发通信异常直接中止控制循环的概率。它不能证明：

- 电机一直在线；
- 电机没有产生报警；
- 电机没有发生过过温、过压、过载等保护事件；
- 总线没有发生瞬态 CRC/乱序/截断；
- 故障后的扭矩状态一定安全。

因此建议将“读重试成功”定义为 `COMM_RECOVERED` 类事件，而不是 `FAULT_CLEARED`。任何进入保护/报警的事件仍应按安全状态机要求记录和决定是否锁存。

## 6. Sync Write 与逐轴确认仍存在信息边界

当前 SO-Follower 的动作发送路径调用 `bus.sync_write("Goal_Position", goal_pos)`；普通同步写的成功返回不能等价于每个舵机都已经逐轴应答并执行。rustypot 的错误状态 API虽然可以提供带 error 的接口，但项目当前 SO-Follower 动作发送路径仍应单独设计“命令发送结果”和“逐轴执行确认”的差异。citeturn513855search3turn513855search0

这意味着未来故障注入测试必须至少覆盖：

- 单轴不响应时 sync write 的返回语义；
- 一轴报警但仍回状态包时的返回语义；
- 一轴拒绝写入时的返回语义；
- 写后读回目标/当前位置及状态的时序；
- 发生故障后控制循环是否仍发送下一帧。

## 7. 当前结论

当前 LeRobot 已经针对 SO-Follower 的 Feetech 瞬态同步读错误加入了默认 2 次应用层重试；rustypot 也已经能够给出较细的 Sync Read 失败轴与原因。citeturn513855search0turn513855search2

但“重试机制”不应被写成“自动恢复机制”。本项目仍需要在真实 SO-101 环境中确认实际安装的 LeRobot/rustypot 版本、实际错误字节、实际掉线行为，以及重试期间的控制输出和扭矩状态。

## 8. 未完成项

- 真实环境版本与 lockfile 固化；
- SO-101 控制板 SKU / PCB Rev / 固件确认；
- 单轴掉线、坏包、CRC、状态报警和写入拒绝实测；
- 重试次数、耗时和控制周期抖动实测；
- 故障期间 Goal_Position 是否继续发送的实测；
- 重试成功后是否允许继续控制的安全策略评审；
- 硬件断能、保险丝、TVS、过流/欠压等保护验证。
