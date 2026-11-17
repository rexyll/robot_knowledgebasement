# TaskPlan｜第21章：产业、厂商与市场生态

版本：v1.0  
适用范围：`knowledge/ecosystem/`  
全局约束：遵循根目录 `TaskPlan.md` 的 Guide 与 Limit；本计划不得降低全局来源、授权、安全和验收要求。

## 21-01｜Stäubli 机器人生态与 ROS 2 驱动专项

**当前状态：进行中。** 当前并行专项节点：MoveIt Jazzy执行/取消语义与Stäubli ROS 2 mock集成边界审查。所有动态结论必须标明固定源码版本、CI环境、测试对象、轮数和证据；CI mock不等于产品现场验收。

### A. 固定基线与来源治理

- [x] 固定上游审查对象：`ICube-Robotics/staubli_driver_ros2`，固定commit `bd658e2d266e315d2ee35f985fb352ea88306b79`；禁止未经授权修改上游源码。
- [x] 固定专项验证pin：`9e617a9e323ef3342f5151a89239bfd93c089f8c`；构建/安装/consumer及53项测试通过证据已记录。
- [ ] ROS Jazzy镜像main独立MoveIt测试异常（曾出现SIGSEGV -11及Ran 0 tests）须以真实非空测试报告重新验收；不能用固定pin测试替代。
- [ ] 逐项完成Stäubli驱动功能、通信、控制器、MoveIt集成、异常恢复、安全边界、版本兼容和许可来源的claim-level审计。

### B. MoveIt / ROS 2生命周期与teardown验证

- [x] 建立CI-only隔离实验，保持stock ROS 2 Jazzy rclcpp无插桩，使用临时MoveIt/Pilz overlay和Stäubli mock。
- [x] Run #147完成10/10无插桩teardown回归，Sequence capability control-block vtable归属由10/10符号证据定位到临时overlay的`libsequence_capability.so` .data.rel.ro。
- [x] Run #149完成同一OMPL pipeline并发PlanService/SequenceService探针10/10回归；动态记录active_=false时仍有slow请求in-flight。
- [x] Run #153动态确认public terminate wrapper在active_=0时返回成功但跳过底层terminate；该证据仅证明漏取消窗口，不证明跨pipeline误取消。
- [x] Run #155与#157直接枚举四个独立runtime pipeline；Run #157 10/10轮每轮四个不同对象地址、mock执行成功、GDB inferior exit=0、8项xUnit断言全通过、teardown failures=0/10。Run #157 artifact ID 14291409424，SHA-256 `2cdac1331bd26379aa447cd4e64f2113398252e6faa9fe83b217262ca0f2ca37`。
- [x] 固定MoveIt Jazzy源码调用链已闭合：`ompl_planner_manager.cpp`中的`OMPLPlannerManager`直接继承`planning_interface::PlannerManager`且未override `terminate()`；基类`PlannerManager::terminate()`遍历`ActiveContexts`静态集合并调用全部存活context的虚函数`terminate()`；Pilz `PlanningContextBase::terminate()`将`terminated_`置true。故OMPL pipeline真正进入terminate时，存活Pilz context被调用是源码调用链的直接结果；动态探针用于确认运行时对象地址、实际调用及状态变化，不再把此问题描述成纯假设。
- [ ] 跨pipeline取消动态门禁：让pipeline A（OMPL）保持active并通过真实public wrapper触发terminate，同时持有pipeline B（Pilz）的真实PlanningContext；按context pointer验证B context->terminate()确实被调用、terminated_由false变true及后续solve拒绝执行；加入未触发A取消的B context负对照。随后再单独评估B正在solve时的运行中行为。
- [ ] 覆盖取消时序：B context创建前、创建并存活但未solve、solve已进入、solve完成后；覆盖A→B与B→A，并区分“context被标记terminated”与“正在运行的solve被中断”两种语义。
- [ ] 基于动态证据设计pipeline/request级取消所有权；在门禁关闭前不得移除`isActive()` gate、不得把`active_`简单替换为计数器、不得把临时callback-group候选合并进上游或产品。
- [ ] 完成至少10轮stock-rclcpp无插桩回归、原始日志、xUnit、GDB退出码及artifact SHA-256归档。

### C. 工业控制与真实部署验收

- [ ] ROS 2 Jazzy真实构建、安装、consumer、gtest与证据包完整性独立验收。
- [ ] UDP/网络异常、超时、断连、重连、控制器状态和故障恢复注入测试。
- [ ] VAL3/SRS、CS9控制器、驱动器固件、机器人型号与软件版本兼容矩阵核验。
- [ ] 安全停止、保护停止、急停、限速/限位及恢复流程的系统级验证。
- [ ] SIL/HIL、SAT和真实机器人测试；取得设备、现场、测试程序、原始记录及责任人签署证据后方可标记完成。

### D. 证据和交付门禁

- [ ] 每项结论关联固定源码commit、配置、环境、命令、原始日志、测试报告、artifact和SHA-256。
- [ ] 明确区分静态源码结论、CI mock动态证据、SIL/HIL证据、SAT/实机证据。
- [ ] 任何未执行、无原始证据或测试对象不匹配的节点保持未完成；失败实验须记录失败原因且不得计入有效PASS/反证。
- [ ] 同步更新本章TaskPlan、根TaskPlan当前状态和每日TaskPlan历史。

## 21-02｜医疗、康复与腔镜机器人生态

**状态：进行中。** 按根TaskPlan第21章当前审计队列推进；注册证、生产许可、适用范围、变更记录和标准证据须以监管原件或可核验官方来源为准。媒体报道及企业自述不得单独作为注册/许可结论。

- [ ] 补齐目标厂商注册证、生产许可、产品技术要求、说明书和变更备案原始证据。
- [ ] 建立产品型号—注册人—适用范围—证书有效期—目标市场的逐项关联表。
- [ ] 完成医疗机器人法规/标准适用性矩阵及证据缺口关闭。

---

**当前任务指针：** 21-01 / B / 基于进程级ActiveContexts的A=OMPL→B=Pilz context持久终止标记单轮探针。  
**全局最高优先级：** 根TaskPlan 00-01；21-01仅并行推进。MotionControlAlgorithms集成保持DEFERRED。
