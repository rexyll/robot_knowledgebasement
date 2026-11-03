---
tags: [项目, SO-101, LeRobot, rustypot, 版本锁定, 依赖审计, 故障诊断]
创建日期: 2026-11-03
更新日期: 2026-11-03
状态: 进行中-公开资料核验
---

# 13｜LeRobot 版本锁定与运行时依赖审计

## 0. 目的与证据边界

本补充文件用于解决 25-14 的一个关键证据缺口：前一轮结论引用了 LeRobot main 与 rustypot latest/develop 的行为，但 SO-101 实际部署必须以真实安装版本、依赖锁定文件和运行时包元数据为准。

本轮只完成公开仓库/官方 API 的版本关系核验，未读取用户本地 Python 环境，未运行 LeRobot，未连接 SO-101。

## 1. 当前公开依赖基线

LeRobot 当前 main 的 `pyproject.toml` 声明项目版本为 0.6.2；其 `rustypot-dep` 为 `rustypot>=1.13.1,<2.0.0`，Feetech extra 通过 serial-motors 使用该依赖。官方 Motors API 说明 `SerialMotorsBus` 由 rustypot 管理舵机型号元数据、控制表和串行 I/O，而 LeRobot 负责归一化、标定和推荐设置。

因此，当前 main 的代码审查至少可以建立如下版本下限：

- LeRobot：main 当前声明 0.6.2；main 本身仍是可变开发分支。
- rustypot：允许版本范围 `>=1.13.1,<2.0.0`；实际安装版本不能从依赖范围反推出。
- Feetech：通过 LeRobot `feetech`/`serial-motors` extra 接入。

## 2. 为什么必须锁定实际版本

上一轮涉及的 `status_alarms_only`、`ServoDefinition.refuses()`、`*_with_error`、Sync Read 错误定位、`set_torque()` 应答检查等行为是在 rustypot 不同版本逐步增加的。rustypot 1.13.1 Changelog 明确记录：

- 1.8.0 增加带 error byte 的 `*_with_error` API；
- 1.12.0 改进 Sync Read 错误，包含具体 motor ID 和原因；
- 1.13.0 对 set_torque 等操作检查应答 error field，并区分“电机拒绝写入”和“报警”；
- 1.13.1 为 Python 暴露 `ServoDefinition.refuses(status)`。

因此，不能把“当前 main 源码行为”直接写成“任何历史 LeRobot/SO-101 环境都如此”。

## 3. SO-101 实际环境必须保存的证据

在真实机器上执行诊断前，应保存：

1. `lerobot` 版本号；
2. `rustypot` 版本号；
3. Python 版本；
4. LeRobot git commit（若从源码安装）；
5. `pyproject.toml`/lockfile 或等价依赖解析结果；
6. SO-101 配置文件及 leader/follower 电机列表；
7. 每个电机 ID、准确型号、固件版本；
8. 控制板准确 SKU、PCB Rev 和固件版本；
9. 串口设备路径、波特率、启动配置；
10. 标定文件、零位/方向配置及配置变更记录。

## 4. 运行时诊断最小验收集

建议首先做非运动、只读诊断：

- `rustypot`/LeRobot 版本打印；
- 六轴 ID/model 扫描；
- 读取准确型号对应的只读状态寄存器；
- 读取 STS 地址65 Status 原始值并保存；
- 记录通信超时、坏包和错误状态字节的原始诊断；
- 验证单轴 `read()` 与批量 `sync_read()` 的错误定位行为；
- 在无负载、机械安全状态下确认 `disconnect(disable_torque=True)` 的逐轴返回结果。

上述步骤只是诊断方案，不代表已经执行。

## 5. 证据结论

**当前结论：** LeRobot main 已经把 rustypot 作为 Feetech 总线的核心实现，并把依赖下限设为 1.13.1；但 SO-101 实际部署版本仍未知。因此，前述状态报警/拒绝判别结论可以作为当前公开软件基线，却不能升级为“目标机器当前运行时已验证”。

**25-14 状态：进行中。** 尚未运行目标环境、读取实际依赖、连接硬件或进行故障注入。

## 来源

1. Hugging Face LeRobot main `pyproject.toml`：https://github.com/huggingface/lerobot/blob/main/pyproject.toml
2. Hugging Face LeRobot Motors API：https://huggingface.co/docs/lerobot/main/en/api/motors
3. LeRobot `SerialMotorsBus` 源码：https://github.com/huggingface/lerobot/blob/main/src/lerobot/motors/motors_bus.py
4. rustypot Changelog：https://docs.rs/crate/rustypot/latest/source/Changelog.md

访问日期：2026-11-03。


## 6. 固定源码快照与稳定发行版的区分（2026-11-03）

进一步核验后，将本项目的版本基线分为“公开稳定发行版”和“固定源码审查快照”，不得混称：

- LeRobot 官方文档首页当前标示稳定版为 v0.6.1；v0.6.1 tag 对应 commit `7e241bd630a3719a56157a497ce5d08f244784f1`，该 tag 的 `pyproject.toml` 使用 Feetech Python SDK extra，而不是 rustypot。
- 前序审查的 LeRobot commit `154fdfb595573ae9c7e0b3b48102b0318235e306` 中，`pyproject.toml` 声明版本0.6.2、Python `>=3.12`，并将 `rustypot>=1.13.1,<2.0.0` 作为串行电机 extra 的依赖。该提交适合复核当前 SerialMotorsBus/rustypot 调用链，但不能写成 v0.6.1 稳定发行版。
- 本项目将该固定 LeRobot commit 与 rustypot v1.13.1 tag（commit `7aa85e13143594ea4fd4ed9f29e3e29d39b5de85`）作为静态源码审查配对基线；这不是经依赖解析生成的完整 lockfile，也不是用户设备的安装清单。
- LeRobot commit 的依赖声明只给出 rustypot 版本范围；本轮没有取得目标设备 `pip freeze`、uv/pip lock 或安装元数据。精确运行时版本仍为未知。
- 当前公开 main 可能继续变化，所有 API/寄存器结论必须绑定上述 SHA/tag；若将来选择正式发行版或其他 commit，需重新审查 API、控制表和读写调用链。

**后续策略：** 只读白名单先以固定源码配对基线推进离线实现；真实设备连接前，必须从目标环境导出 LeRobot、rustypot、Python 版本和依赖解析文件，并对照本文件及项目文档24复核差异。当前没有运行 LeRobot 或连接硬件。
