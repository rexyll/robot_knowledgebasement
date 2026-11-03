---
tags: [SO-101, STS3215, rustypot, 寄存器, 只读白名单, 软件审计]
创建日期: 2026-11-03
更新日期: 2026-11-03
状态: 静态源码基线
---

# STS3215 / rustypot v1.13.1 只读寄存器白名单

## 1. 目的与适用边界

本文件把 FEETECH STS3215 的公开控制表定义转换为**只读采集程序可调用的字段白名单**。它约束的是程序只发起读操作；表中标记为 RW 的寄存器仍然只允许读取，不允许本采集器写入。

本文件不是 SKU 专属默认值表，不代表 C001/C018/C047 实机固件一定具有相同初始值，也不授权上电、运动或任何配置写入。

## 2. 可复核的软件源码基线

| 项目 | 本文件采用的源码基线 | 证据边界 |
|---|---|---|
| LeRobot | 版本字段 0.6.2；源码 commit `154fdfb595573ae9c7e0b3b48102b0318235e306` | 固定 main 源码快照，不是已确认的稳定发行安装包或目标设备版本 |
| LeRobot Python 要求 | `>=3.12` | 来自该 commit 的 `pyproject.toml` |
| LeRobot Feetech 依赖声明 | `rustypot>=1.13.1,<2.0.0` | 这是允许范围，不是 lockfile 解析出的精确安装版本 |
| rustypot | tag `v1.13.1`；commit `7aa85e13143594ea4fd4ed9f29e3e29d39b5de85` | 本文件固定的控制表定义审查版本；不能推断目标机器安装了该版本 |

选择 rustypot v1.13.1 是为了把控制表审查固定到 LeRobot 依赖下限对应的可追溯版本。后续若锁定的实际环境使用更高版本，必须重新导出 ServoDefinition 并比较差异。

仓库根目录的 `pyproject.toml` 属于 robot-knowledgebase 知识库自身，不包含 LeRobot 或 rustypot 依赖，因此不构成 SO-101 运行环境锁定文件。

## 3. STS3215 只读字段白名单

字段名按 rustypot ServoDefinition 定义；LeRobot `read()` / `sync_read()` 会将名称转为小写。地址和宽度来自 rustypot v1.13.1 的 STS3215 定义。

| 字段名（API） | 地址 | 宽度 | ServoDefinition 权限 | 解码/类型 | 采集用途 |
|---|---:|---:|---|---|---|
| `firmware_major_version` | 0 | 1 | R | u8 | 固件主版本 |
| `firmware_minor_version` | 1 | 1 | R | u8 | 固件次版本 |
| `model_number` | 3 | 2 | R | u16 | 驱动型号响应；不能单独识别 C001/C018/C047 |
| `id` | 5 | 1 | RW | u8 | 总线 ID 读回 |
| `baudrate` | 6 | 1 | RW | u8 | 波特率代码读回 |
| `max_temperature_limit` | 13 | 1 | RW | u8 | 温度保护配置 |
| `max_voltage_limit` | 14 | 1 | RW | u8 | 过压配置 |
| `min_voltage_limit` | 15 | 1 | RW | u8 | 欠压配置 |
| `max_torque_limit` | 16 | 2 | RW | u16 | 扭矩上限配置 |
| `unloading_condition` | 19 | 1 | RW | u8 | 卸载条件位配置；保留原始值 |
| `led_alarm_condition` | 20 | 1 | RW | u8 | LED 报警条件配置；保留原始值 |
| `protection_current` | 28 | 2 | RW | u16 | 保护电流配置 |
| `protective_torque` | 34 | 1 | RW | u8 | 保护后的保持扭矩比例字段 |
| `protection_time` | 35 | 1 | RW | u8 | 过载保护计时配置 |
| `overload_torque` | 36 | 1 | RW | u8 | 过载扭矩比例字段 |
| `over_current_protection_time` | 38 | 1 | RW | u8 | 过流保护计时配置 |
| `torque_enable` | 40 | 1 | RW | bool | 当前扭矩使能状态读回 |
| `lock` | 55 | 1 | RW | bool | EEPROM 锁状态读回；禁止解锁 |
| `present_position` | 56 | 2 | R | i16；sign-magnitude(15) | 当前位置寄存器值 |
| `present_speed` | 58 | 2 | R | u16；sign-magnitude(15) | 当前速度寄存器值 |
| `present_load` | 60 | 2 | R | u16；sign-magnitude(10) | 当前负载寄存器值 |
| `present_voltage` | 62 | 1 | R | u8 | 当前电压寄存器值 |
| `present_temperature` | 63 | 1 | R | u8 | 当前温度寄存器值 |
| `status` | 65 | 1 | R | u8 | STS 状态寄存器原始数值 |
| `moving` | 66 | 1 | R | bool | 运动状态 |
| `present_current` | 69 | 2 | R | u16 | 当前电流寄存器值 |

说明：

1. `R` / `RW` 是 ServoDefinition 的寄存器访问属性。对本采集程序而言，上表所有字段均只调用读 API；`RW` 不代表允许写。
2. 表中数值是地址、宽度和寄存器解码类型，不是所有字段的工程单位换算。位置/速度/负载的符号位按 STS sign-magnitude 编码解码；单位换算必须另列公式、型号和固件适用条件。
3. `model` 与 `model_number` 是同一地址/宽度的别名，只保留 `model_number` 一个采集键；`baud_rate` 与 `baudrate` 也是别名。
4. `present_position`、`present_speed`、`present_load` 在 rustypot API 返回的是按定义解码的整数，不是原始串口字节流。
5. 对于当前公开 LeRobot `SerialMotorsBus.read()`，返回寄存器值；`sync_read()` 返回同一字段的多电机值。二者均不提供完整原始 Status Packet 字节。

## 4. 必须隔离的字段语义冲突

FEETECH 通用 STS Wiki 将地址3和地址4分别描述为 Servo Major 与 Servo Minor 两个 1 字节字段；rustypot v1.13.1 的 STS3215 ServoDefinition 则将 `model` / `model_number` 定义为地址3、宽度2字节的只读字段。

这意味着本白名单不能同时把地址3/4拆成两个独立 API 字段，也不能仅凭 `model_number` 的整数值反推 C001/C018/C047。必须取得 FEETECH 对准确 SKU/固件的正式映射，并与实物铭牌交叉核验。该冲突继续由 TODO HW-002 跟踪。

此外，`firmware_major_version` / `firmware_minor_version` 分别位于地址0/1；不要把地址0误写为 Model Number。

## 5. LeRobot / rustypot 公开读取行为

固定源码快照中的 LeRobot `SerialMotorsBus.read()` 调用 rustypot `read_register_with_error()`，并依据对应 ServoDefinition 的 `refuses(status)` 判别是否拒绝读取；`sync_read()` 调用 `sync_read_register_with_error()`。rustypot 读取接口返回解码后的整数及 StatusError，而不是完整原始字节数组。

因此，采集器的数据契约应区分：

- `register_value_decoded`：公开读 API 返回的整数/布尔值；
- `status_register_65`：通过字段 `status` 另行读取的 STS 地址65数值；
- `status_packet_error`：LeRobot 普通 `read/sync_read` 不直接暴露的状态包 error field；
- `wire_bytes`：当前上述公开 API 不提供，不得伪造或由整数重新包装成“原始响应字节”。

Feetech STS3215 定义启用 `status_alarms_only`。报警状态不等同于协议拒绝；不能只因 read 成功就推断无报警。若必须取得 Status Packet error field，应另行评估 rustypot 的受支持公开 API 和版本锁定，不得访问 LeRobot 私有 `_bus` / `_connected_bus`。

## 6. 采集程序硬约束

允许：
- 对已审核字段名调用 `read(name, motor, normalize=False, num_retry=0)`；
- 对已审核字段名调用 `sync_read(name, motors, normalize=False, num_retry=0)`；
- 每次调用记录 UTC 时间、单调时钟耗时、motor ID、joint 映射版本、字段名、结果或异常；
- 退出时若必须保持严格不发送扭矩写入，显式调用 `disconnect(disable_torque=False)`，并记录该动作不证明电机已处于扭矩关闭状态。

禁止：
- `write`、`sync_write`、`setup_motor`、`set_baudrate`、`configure_motors`、`set_operating_mode`；
- `enable_torque`、`disable_torque`、`set_torque`；
- `read_calibration` / `write_calibration` / 校准写入流程；
- 私有成员 `_bus`、`_connected_bus`，自造任意地址读接口或把读值包装成原始字节；
- 自动重连、自动配置、自动清报警或任何未批准的状态恢复。

**重要：** `connect(handshake=True)` 会执行型号/固件握手读取；它不是“仅打开串口”。连接前仍须由硬件负责人完成供电、机械固定、端口占用和风险评审。本文不授权任何实际连接或上电操作。

## 7. 离线验收建议

1. 将本表转为机器可读的只读字段清单，并在启动时拒绝任何白名单外字段。
2. 用 fake bus 验证只调用 read/sync_read，且所有字段名均在白名单。
3. 用 AST/静态检查禁止出现写 API、校准 API、私有总线成员和默认 `disconnect()`。
4. 验证每个 motor 的字段读取独立记录成功/失败，不用 0 填补缺失值。
5. 验证多轴 `sync_read` 的时间语义：不得标记为跨字段或全轴原子快照。
6. 以上离线测试通过只证明软件约束，不证明硬件、SKU、供电或寄存器实值安全。

## 8. 来源

- LeRobot 固定源码：`pyproject.toml` 与 `src/lerobot/motors/motors_bus.py`，commit `154fdfb595573ae9c7e0b3b48102b0318235e306`。
- rustypot STS3215 定义：tag `v1.13.1`，commit `7aa85e13143594ea4fd4ed9f29e3e29d39b5de85`，`src/servo/feetech/sts3215.rs`。
- rustypot 读取/解码实现：同一 tag 的 `src/servo/definition.rs`、`src/servo/info.rs`。
- FEETECH 官方 STS 通用内存表：https://ftservo.github.io/ftservo-wiki/reference/parameter/memory-sts/

本文件仅为静态源码字段审计；未安装依赖、未运行采集程序、未连接实机、未读取或写入任何舵机寄存器。
