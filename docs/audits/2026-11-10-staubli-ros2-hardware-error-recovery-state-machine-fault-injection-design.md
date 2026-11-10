# 2026-11-10 Stäubli ROS 2 硬件错误恢复状态机与故障注入验收设计

> 节点：§9.3.281 / SERVO-864。类型：恢复策略设计与测试规格，不是实现变更或测试报告。  
> 固定 Stäubli 基线：ICube-Robotics/staubli_driver_ros2@bd658e2d266e315d2ee35f985fb352ea88306b79  
> 固定 ros2_control 参考：Jazzy c6ef5a24e0cd21463edb99bded552a96f914b716（hardware_interface 4.50.0）

## 1. 目标与边界

把 §9.3.280 发现的硬件错误传播问题转化为可执行的恢复状态机、故障注入矩阵和验收准则。覆盖驱动内部、ROS 2 HardwareComponent、ResourceManager、ControllerManager、插件加载器以及操作员/独立安全系统之间的责任边界。

本报告只定义预期契约。没有修改 Stäubli 上游代码，没有构建或运行任何测试，也没有证明 CS9/VAL3 的实际停止行为。

## 2. 不可混淆的停止与安全结果

以下事件必须分别记录，不能将其中任一项推断为下一项：

1. STOP_REQUESTED：软件决定发出停止请求。
2. STOP_SEND_ACCEPTED_LOCAL：本地发送 API 明确报告数据报已交给本机网络栈/发送层；不代表远端收到。
3. STOP_CONTROLLER_ACKNOWLEDGED：只有协议存在可关联的控制器回执，并通过来源、会话、命令关联和新鲜度校验时才能成立。当前固定协议基线没有独立 STOP ACK/command ID，因此当前驱动不能声称达到此状态。
4. STOP_MOTION_OBSERVED：通过可信的新鲜状态数据观察到运动停止；这不等于安全功能确认或机械静止的独立测量。
5. SAFE_STATE_CONFIRMED：由经过风险评估、验证和适用安全等级设计的独立安全链确认。不得由 ROS 2、普通 UDP、VAL3 应用状态位或单一软件停止命令替代。

**硬性约束：** E-stop、保护停止、驱动安全功能、制动器/能量隔离等安全措施必须按具体机器人、控制器、风险评估和适用标准独立设计、验证。ROS/UDP STOP 仅是附加的软件控制请求，不是安全功能。故障处置期间不得自动重新使能动力或自动恢复运动。

## 3. 建议恢复状态机

### 3.1 状态定义

| 状态 | 含义 | 允许动作 / 退出条件 |
|---|---|---|
| RUNNING | 通信、状态和控制满足运行门禁 | 监测状态新鲜度、协议完整性、连接和错误 |
| ERROR_DETECTED | read/write ERROR、超时、畸形帧、异常或连接丢失 | 禁止新运动命令；记录首发原因和时间 |
| STOP_REQUESTED | 已发起软件 STOP 尝试 | 记录请求、发送结果和超时 |
| STOP_SEND_ACCEPTED_LOCAL | 本地发送层报告已接受发送 | 只记录本地发送事实，不宣称远端已停止 |
| STOP_UNCONFIRMED | 发送失败、结果未知、无 ACK、反馈过期或停止观测不可用 | 保持故障锁存；告警并要求独立安全处置/人工检查 |
| STOP_CONTROLLER_ACKNOWLEDGED | 控制器返回可验证且关联的 ACK（当前协议不支持，保留为未来状态） | 仍需独立验证运动状态与安全状态 |
| STOP_MOTION_OBSERVED | 有效新鲜状态显示运动已停止 | 仅为运动观测；不能自动清除故障或恢复动力 |
| INTERFACES_REVOKED | ResourceManager 已撤销故障硬件接口 | 控制器/客户端必须将接口不可用视为硬门禁 |
| RECOVERY_CLASSIFIED | 故障已分类，恢复路径和授权级别已确定 | 依据错误类别进入 UNCONFIGURED 或 FINALIZED 处理 |
| UNCONFIGURED | 错误回调成功后的生命周期状态 | 仅允许受控清理/配置；不得直接恢复 ACTIVE |
| FINALIZED | 错误处理失败或生命周期终止 | 普通 configure/activate 不可作为恢复方案；需要受控卸载/重载 |
| RECONNECTING | 执行显式断开、资源清理和重新连接 | 不复用旧会话状态或旧缓存 |
| SESSION_VALIDATING | 验证新连接首帧、协议、来源、会话和状态完整性 | 任一门禁失败均回到故障锁存，不得激活 |
| INACTIVE | 新会话已验证，硬件已配置但未允许运动 | 操作员/安全许可及控制器状态门禁通过后才可申请激活 |
| ACTIVE | 经明确授权重新进入运行态 | 重新建立控制器、接口和状态有效性；故障后禁止自动进入 |

### 3.2 关键状态转移

| 起始状态 | 事件/条件 | 目标状态 | 必须动作 |
|---|---|---|---|
| RUNNING | read/write ERROR 或关键输入失效 | ERROR_DETECTED | 锁存故障；拒绝新运动命令；保存错误快照 |
| ERROR_DETECTED | 发起软件停止请求 | STOP_REQUESTED | 有界尝试；不得阻塞实时控制线程 |
| STOP_REQUESTED | 本地发送明确成功 | STOP_SEND_ACCEPTED_LOCAL | 记录本地结果，不提升为远端确认 |
| STOP_REQUESTED | 发送失败/未知/超时 | STOP_UNCONFIRMED | 锁存并告警；启动独立安全处置 |
| STOP_SEND_ACCEPTED_LOCAL | 无协议 ACK 或反馈失效 | STOP_UNCONFIRMED | 当前协议无 ACK，不能假设停止成功 |
| 任一 STOP 状态 | ResourceManager 完成接口撤销 | INTERFACES_REVOKED | 验证接口不可用，控制器不能继续使用故障接口 |
| INTERFACES_REVOKED | 驱动清理成功 | UNCONFIGURED | 记录连接、线程、socket、缓存清理结果 |
| INTERFACES_REVOKED | 错误处理失败/组件 FINALIZED | FINALIZED | 阻止普通生命周期恢复；进入插件卸载/重载流程 |
| UNCONFIGURED | 已批准的重连流程 | RECONNECTING | 显式断开、取消异步操作、join线程、清缓存，再连接 |
| FINALIZED | 维护流程授权插件重载 | RECONNECTING | 卸载旧实例并确认资源释放，再加载新实例 |
| RECONNECTING | 新连接建立 | SESSION_VALIDATING | 丢弃旧 session、旧状态和旧命令；等待有效首帧 |
| SESSION_VALIDATING | 全部门禁通过 | INACTIVE | 新会话、首帧、序号和状态一致性成立 |
| SESSION_VALIDATING | 任一门禁失败 | STOP_UNCONFIRMED | 保持故障锁存并禁止激活 |
| INACTIVE | 操作员明确确认且独立安全许可成立 | ACTIVE | 重新执行 activation 前置检查；不得自动恢复 |

### 3.3 Jazzy 生命周期交互注意事项

- read()/write() 返回 hardware_interface::return_type::ERROR 会进入 HardwareComponent 错误处理；on_error() 返回值决定进入 UNCONFIGURED 或 FINALIZED。
- on_error() 返回 SUCCESS 不等于 STOP 成功，也不等于 socket、接收线程和缓存已清理。驱动必须显式定义清理契约。
- on_error() 返回 ERROR/FAILURE 导致 FINALIZED 时，普通生命周期服务不能视为可恢复方案；应提供经过验证的插件卸载/重载运维流程。
- ResourceManager 接口撤销之后，ControllerManager 后续 mode-switch 可能因接口已不可用而失败；不能依赖该路径向故障硬件补发 STOP。
- 故障控制器停用与物理机器人停止是两个不同验收对象，必须分别观测和记录。

## 4. 故障分类与恢复策略

| 故障类别 | 例子 | 默认分类 | 恢复策略 |
|---|---|---|---|
| 短暂状态超时 | 单次超时、状态年龄超阈值 | 可恢复候选，但不得保持旧状态有效 | 锁存状态失效；停止新命令；只有连续新鲜且一致的新帧才可重新验证 |
| 网络断开 | socket错误、状态持续丢失 | 严重故障 | STOP 结果标记未知；禁止运动；清理 socket/线程；显式重连和新会话验证 |
| 数据畸形 | 长度、版本、类型、枚举、NaN/Inf不合法 | 严重故障/输入完整性失败 | 丢弃帧；计数和日志；达到策略阈值后锁存；畸形帧不得刷新新鲜度 |
| 命令发送失败 | send false、would_block、短写或结果未知 | 严重故障 | 不得报告命令/STOP成功；禁止继续运动命令；启动独立停止处置 |
| 控制器报错 | 可信状态报告控制器错误/安全状态异常 | 严重故障 | 锁存错误；禁止软件自动清除；按厂商安全流程人工检查和复位 |
| 插件内部异常 | 回调异常、线程异常、资源释放失败 | 不可自动恢复候选 | 防止异常穿透控制循环；进入 FINALIZED 或受控进程故障处理；人工确认后卸载/重载 |

“可恢复”只描述软件能否重新建立通信和状态，不代表允许机器人自动恢复运动。任何运动恢复都需要独立许可、状态一致性检查和明确操作员授权。

## 5. 重连与会话完整性门禁

1. 旧 socket 已关闭；异步接收已取消；接收线程已 join；旧回调不得访问已释放对象。
2. 清空接收邮箱、状态缓存、有效标志、命令缓存、序号基线、时间戳、错误恢复标志和待处理请求。
3. 建立本地连接代次 generation；异步回调必须绑定 generation，旧代次回调不得写入新会话。
4. 对数据源地址/端口、magic/version/type/精确长度、字段范围和 finite 数值执行统一校验。
5. 只接受新会话建立后的有效首帧；重复帧、旧序号、乱序帧和超时帧不得刷新有效状态。
6. 协议若无 controller boot ID/session nonce，则跨控制器重启的会话真实性仍未解决；本地 generation 不等价于远端身份认证。
7. 至少连续 N 帧（N 必须由控制周期、网络特性和风险评估确定，不在本设计中臆定常数）满足序号单调性、时间新鲜度、字段完整性和状态一致性，才允许进入 INACTIVE。
8. 新会话验证完成后仍不得自动 ACTIVE；必须有操作员确认和独立安全许可。

## 6. 故障注入验收矩阵

以下条目全部为**未执行**。执行前必须在隔离 Mock/SIL 环境验证测试装置；涉及真实 CS9/机械臂的测试必须有批准的风险评估、受控速度/空间、急停与防护措施及现场负责人。

| ID | 注入/场景 | 预期结果 | 证据要求 |
|---|---|---|---|
| SERVO864-FI-01 | read() 返回 ERROR | 状态立即失效；进入错误回调；接口撤销可观测 | 日志、生命周期状态、接口列表 |
| SERVO864-FI-02 | write() 返回 ERROR | 不再发送后续运动命令；错误锁存 | 命令计数、日志、状态 |
| SERVO864-FI-03 | on_error 中 STOP send 返回 false | 不得把停止请求记为成功；错误仍锁存 | mock send 返回值、事件顺序 |
| SERVO864-FI-04 | UDP would_block / 丢包但底层错误被报告 | 上层识别发送失败或未知；不能返回虚假成功 | socket注入、发送计数、返回值 |
| SERVO864-FI-05 | STOP 数据报发送成功但远端丢弃 | 不能产生控制器 ACK/停止确认 | 网络代理抓包、控制器日志 |
| SERVO864-FI-06 | STOP 无 ACK / ACK 超时 | STOP_UNCONFIRMED；不自动恢复 | 超时日志、故障锁存 |
| SERVO864-FI-07 | 网络断开发生在 read/write 周期中 | 状态失效、接口撤销、控制器处置可观测 | 断网脚本、RM/CM日志 |
| SERVO864-FI-08 | 连续丢包和延迟抖动 | stale 门禁生效；旧缓存不能继续作为有效状态 | 注入参数、状态年龄轨迹 |
| SERVO864-FI-09 | 重复序号 UDP 帧 | 不刷新有效状态新鲜度，不推进有效序号 | PCAP、状态时间戳、计数 |
| SERVO864-FI-10 | 乱序/回退序号帧 | 不被误判为正常回绕，不覆盖新状态 | PCAP、序号轨迹 |
| SERVO864-FI-11 | 旧会话帧在重连后到达 | 被 generation/session 门禁拒绝 | 两代会话日志、帧序列 |
| SERVO864-FI-12 | 首帧缺字段/畸形 payload/NaN/Inf | 不完成 SESSION_VALIDATING，不导出有效快照 | 畸形帧集、解析结果 |
| SERVO864-FI-13 | on_error 后 socket/线程仍存活 | 测试暴露未清理资源；修复后确认取消和 join | 线程清单、socket状态、TSan日志 |
| SERVO864-FI-14 | configure 失败后重试 | 生命周期状态与连接资源一致；无重复线程/双 socket | 回调序列、资源计数 |
| SERVO864-FI-15 | on_error 返回 ERROR 导致 FINALIZED | 普通 configure/activate 不得恢复；插件重载路径可审计 | lifecycle服务响应、plugin日志 |
| SERVO864-FI-16 | ResourceManager 撤销接口 | 故障组件所有 command/state handles 不可再使用 | RM接口快照、控制器日志 |
| SERVO864-FI-17 | ControllerManager 后续 mode-switch | prepare/perform实际调用与拒绝原因可观测；不得依赖补发STOP | CM trace、调用计数、Issue #3620对照 |
| SERVO864-FI-18 | 依赖故障硬件的控制器处于 active | 控制器被框架停用/故障隔离；无后续命令写入 | controller state、命令计数 |
| SERVO864-FI-19 | 故障期间重复 read/write 错误 | 不重复创建清理线程，不清除首发故障，不出现状态振荡 | 时间线、线程/资源计数 |
| SERVO864-FI-20 | 生命周期服务与 read/write 错误并发 | 无数据竞争、死锁、重复释放或悬空回调 | TSan、线程追踪、超时 |
| SERVO864-FI-21 | 重连后连续有效首帧不足 N 帧 | 保持 SESSION_VALIDATING，不得激活 | 帧计数、状态机轨迹 |
| SERVO864-FI-22 | 操作员未确认或独立安全许可未成立 | 不得从 INACTIVE 转 ACTIVE | 权限/许可日志 |
| SERVO864-FI-23 | 运动状态反馈静止但安全链未确认 | 只能记 STOP_MOTION_OBSERVED，不得记 SAFE_STATE_CONFIRMED | 状态来源与安全链独立证据 |
| SERVO864-FI-24 | CS9控制器重启/VAL3应用重启 | 新会话重新验证；旧序号和旧缓存不得复用 | CS9日志、抓包、会话轨迹 |

## 7. 日志、可观测性与审计字段

每次故障至少记录：

- 单调时钟时间戳、ROS 时间（若启用）及时间源；
- hardware component 名称、生命周期前态/后态、触发回调；
- 故障类别、错误码、首发故障与后续重复故障计数；
- read/write 返回值、状态帧年龄、序号、帧完整性结果；
- socket发送结果的精确定义（未尝试/失败/本地接受/未知），禁止使用含糊的“STOP成功”；
- 控制器 ACK 状态（当前协议不支持时明确记录 unsupported）；
- ResourceManager 接口撤销时间和接口快照；
- ControllerManager prepare/perform调用、控制器停用结果及拒绝原因；
- socket、异步操作、接收线程、generation/session和缓存清理结果；
- 重连尝试次数、首帧时间、有效连续帧数、操作员授权和独立安全许可引用。

日志不得记录密钥等秘密；应有速率限制，避免故障风暴导致控制线程阻塞。

## 8. 验收准则

- AC-01：停止请求、本地发送、控制器确认、运动停止观测和安全状态确认是不同事件。
- AC-02：STOP 发送失败或未知时，系统进入锁存故障路径，不报告停止已确认。
- AC-03：read/write ERROR 后所有旧状态和命令缓存均失效；旧缓存不得继续作为有效状态。
- AC-04：UNCONFIGURED 与 FINALIZED 有不同、明确、可审计的恢复路径。
- AC-05：错误处理后 socket、异步操作、线程、缓存和会话代次具有确定清理契约。
- AC-06：重连必须完成新会话验证；旧帧、重复帧、乱序帧不能刷新新会话有效性。
- AC-07：ResourceManager 接口撤销和 ControllerManager 控制器处置在真实集成环境中可观测、可验证。
- AC-08：任何自动恢复都不能自动重新使能机器人运动。
- AC-09：独立安全链验证与 ROS/UDP 软件状态验证分开记录。
- AC-10：所有故障注入有可重复脚本、预期日志、失败判据和证据归档。

**本节点状态：** 恢复状态机、故障分类、24 项故障注入矩阵和 10 项设计验收准则已形成；上述运行时验收均未执行。不能据此宣称驱动已具备故障安全恢复能力。

## 9. 参考资料

- Stäubli 固定审查提交：https://github.com/ICube-Robotics/staubli_driver_ros2/commit/bd658e2d266e315d2ee35f985fb352ea88306b79
- ros2_control Jazzy 固定参考提交：https://github.com/ros-controls/ros2_control/commit/c6ef5a24e0cd21463edb99bded552a96f914b716
- Jazzy Hardware Component lifecycle：https://control.ros.org/jazzy/doc/ros2_control/hardware_interface/doc/lifecycle_of_a_hardware_component.html
- Jazzy read/write error handling：https://control.ros.org/jazzy/doc/ros2_control/hardware_interface/doc/handling_errors_during_read_write.html
- Stäubli driver README（项目自述仍属 prototype，非 industry-ready）：https://github.com/ICube-Robotics/staubli_driver_ros2

## 10. 未执行事项与下一步

本轮未执行 C++/ROS 2 构建、单元测试、ResourceManager/ControllerManager集成故障注入、网络注入/抓包、线程竞态测试、插件卸载重载、VAL3 Studio编译下载、CS9仿真/实机、SIL/HIL、FAT/SAT或物理停止测试。

下一节点建议：**§9.3.282 / SERVO-865：基于现有 RobotDriver/HardwareInterface 源码细化恢复状态机的实现映射与最小接口契约**。在不修改上游的前提下，逐项映射状态机到现有函数、数据成员、线程和生命周期回调，形成后续可授权实现的差异清单。
