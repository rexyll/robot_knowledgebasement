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
- [x] 跨pipeline取消动态门禁：Run #160与#161分别10/10通过。A=OMPL真实active并通过真实public wrapper触发terminate；B=Pilz真实PlanningContext保持存活；每轮创建context指针、Pilz terminate this指针及target solve指针完全相同；terminated_由false变true；同一context后续solve为PLANNING_FAILED；新建Pilz context负对照为SUCCESS。详见下方2026-11-17 Run #160/#161证据记录。
- [ ] 覆盖取消时序：B context创建前、创建并存活但未solve、solve已进入、solve完成后；覆盖A→B与B→A，并区分“context被标记terminated”与“正在运行的solve被中断”两种语义。
- [ ] 基于动态证据设计pipeline/request级取消所有权；在门禁关闭前不得移除`isActive()` gate、不得把`active_`简单替换为计数器、不得把临时callback-group候选合并进上游或产品。
- [x] Run #160/#161各完成10轮跨pipeline动态探针及10轮原有无插桩teardown回归；两轮xUnit均9 tests/0 errors/0 failures/0 skipped，GDB inferior exit=0；artifact与SHA-256已归档。另有pal_statistics publisher shutdown期间invalid context sleep日志，单独列为待分析项。

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

**当前任务指针：** 21-01 / B / 设计pipeline/request级取消所有权隔离，补测Pilz solve已运行时的terminate语义，并排查pal_statistics shutdown日志。  
**全局最高优先级：** 根TaskPlan 00-01；21-01仅并行推进。MotionControlAlgorithms集成保持DEFERRED。


### 2026-11-17 SERVO-908 workflow现状复核（补充门禁）

- [x] 检查既有实验分支 `.github/workflows/experiment-moveit-shutdown-order.yml` 的实际注入与断言：`STAUBLI_ACTIVE_PROBE` 位于 `PlanningPipeline::generatePlan()` 的 `active_=true` 后、request adapter及 `getPlanningContext()` 前，故该barrier并不代表PlanningContext已创建或进入solve。
- [x] 检查当前terminate测试客户端：PlanService与SequenceService均指定 `pipeline_id="ompl"`；慢请求在fast请求结束后被停放，此时pipeline已 `active=0`；随后调用 `MoveItCpp::terminatePlanningPipeline("ompl")`，断言wrapper `active_before=0 result=1`，并断言底层 `PlanningPipeline::terminate()` marker不存在。该测试只证明inactive窗口的wrapper漏取消行为，不构成跨pipeline terminate证据。
- [ ] 不得将现有同pipeline overlap测试或Run #157 pipeline map枚举通过，作为SERVO-908跨pipeline动态验证。
- [ ] 首轮Pilz实验需持有由真实Pilz pipeline PlannerManager创建的PlanningContext，记录pipeline/manager/context指针；确保其在A=OMPL terminate调用前仍存活，并在临时Pilz overlay记录terminate的this与terminated_ false→true；随后验证同一context solve被拒绝及未污染负对照。
- [ ] OMPL自身PTC实验另行执行：barrier必须位于 `ModelBasedPlanningContext::solve()` 的 `registerTerminationCondition(ptc)` 之后，证明PTC已注册；不可用generatePlan入口barrier替代。
- [ ] 在实现可确定性复现的跨pipeline测试前，不改 `isActive()` gate、不将 `active_` 简单替换为计数器、不改上游或产品源码；仅使用既有实验分支的CI-only临时overlay + stock Jazzy rclcpp + Stäubli mock。


### 2026-11-17 SERVO-908跨pipeline动态探针实现状态

- [x] 在既有实验分支提交 `d81a2db1050002025bb7ba3a0460334658e8c1d2`，仅修改实验workflow中的CI-only MoveIt/Pilz临时overlay和launch-test注入，不修改上游仓库文件、正式Stäubli产品源码或rclcpp。
- [x] 新增A=OMPL active barrier（请求allowed_planning_time=7.733），测试服务在barrier期间创建真实B=Pilz PlanningContext并持有shared_ptr，记录manager/context指针；通过真实MoveItCpp public wrapper触发terminate；临时Pilz terminate marker记录this和terminated_ before/after；目标context solve要求PLANNING_FAILED；终止后新建的Pilz context作为负对照，solve要求SUCCESS。
- [x] 新增独立launch test、环境开关、release timeout和日志指针/事件顺序断言；原有active=0 wrapper漏取消测试与10轮teardown regression继续保留。
- [ ] Run #158（Actions 44008227253，job 133788637425）当前处于Set up ROS Jazzy，尚未进入MoveIt构建和mock动态测试；需等CI最终结果并核验原始日志、xUnit和artifact。若Pilz context创建或负对照solve失败，先判定测试不充分/配置不匹配，不得直接写成跨pipeline污染已被证实。
- [ ] 通过Run #158单轮跨pipeline门禁后，再决定是否把跨pipeline测试纳入10轮重复；需保留原有10/10 teardown门禁。


### 2026-11-17 SERVO-908 Run #159失败复盘与探针控制通道修正

- [x] Run #159（Actions [44010559893](https://github.com/rexyll/staubli_driver_ros2_from_org/actions/runs/44010559893)，commit `5cbb667712292d24d3ea670240ce5fcec41c1346`）已通过stock Jazzy rclcpp构建、MoveIt/Pilz临时overlay静态校验、patched move_group构建及Stäubli mock workspace构建。
- [x] 失败定位：动态阶段OMPL请求进入`generatePlan()`屏障，日志明确`A_OMPL_HELD ... active=1`；但测试线程调用默认`/move_group/get_parameters`查询held参数时超时。原same-pipeline slow barrier也因相同问题无法被测试客户端观测，10轮回归均未通过。该问题属于控制/观测服务与被测执行回调的调度隔离缺陷，不构成Pilz跨pipeline terminate的动态证据。
- [x] 修正探针控制面：新增专用`/staubli_test_probe_status` Trigger服务；status、inactive terminate及cross-pipeline terminate服务统一放入独立Reentrant callback group，避免测试端依赖被阻塞的默认参数服务；增加status service显式销毁与静态校验。
- [x] 修正提交：`352142d202425e68f42d4c25ca36eac7c5aa164c`（reentrant control channel）及`56cf7cff8064bd5a996382bc41c682114436d042`（status service teardown assertion）；均在既有实验分支，不创建新分支。
- [ ] Actions Run `44019468358`（commit `352142d...`）和Run `44019503341`（commit `56cf7cff...`）截至当前更新仍在ROS Jazzy环境准备阶段；等待后续静态校验、编译、mock动态测试及10轮回归结果。
- [ ] 跨pipeline动态验收仍要求：A=OMPL真实active；B=Pilz context真实创建并持有；wrapper实际进入底层terminate；Pilz terminate this指针与B context一致；terminated_ false→true；同一B后续solve拒绝；新建B负对照solve成功；OMPL请求释放并完成。
- [ ] 不得把Run #159的held-state服务超时解释为MoveIt跨pipeline terminate失败；也不得把`active=1`单一日志当作跨pipeline terminate已发生。若新控制通道仍失败，先检查回调组、executor线程和服务响应时序。
- [ ] 只有跨pipeline单轮动态门禁通过后，才考虑将该探针加入10轮重复；原10轮teardown回归必须保留并独立通过。

**当前任务指针：** 21-01 / B / 使用Reentrant callback group和专用status service修复确定性barrier的控制/观测隔离；随后继续A=OMPL→B=Pilz持久终止标记动态验收。全局00-01仍最高优先级，MotionControlAlgorithms保持DEFERRED。


### 2026-11-17 SERVO-908跨pipeline动态验证通过（Run #160 / #161）

- [x] Run #160（[Actions 44019468358](https://github.com/rexyll/staubli_driver_ros2_from_org/actions/runs/44019468358)，commit `352142d202425e68f42d4c25ca36eac7c5aa164c`）完成；artifact ID `14301417866`，SHA-256 `573c29bc334431b52d87365f0b50c67838b8921c04934495a8e60ba15f42b0d6`。
- [x] Run #161（[Actions 44019503341](https://github.com/rexyll/staubli_driver_ros2_from_org/actions/runs/44019503341)，commit `56cf7cff8064bd5a996382bc41c682114436d042`）完成；artifact ID `14300977823`，SHA-256 `4a8403b97a0194ff667860324a421b44b5cc6a40b543cb520ad193d119b52bb0`。
- [x] 两轮均通过stock ROS 2 Jazzy rclcpp无插桩构建、CI-only MoveIt/Pilz临时overlay构建及Stäubli mock workspace构建；跨pipeline动态探针各10/10通过；原有无插桩teardown回归各10/10通过。
- [x] 每轮10次均记录A=OMPL `active=1`；B=Pilz真实PlanningContext已创建并持有；真实 `MoveItCpp::terminatePlanningPipeline("ompl")`调用返回后，Pilz terminate的this指针与B context地址完全相同；`terminated_`由false变true；同一B context后续solve返回`PLANNING_FAILED`（code=-1）；新建Pilz context负对照solve返回`SUCCESS`（code=1）；释放后的OMPL请求恢复。
- [x] 两轮每轮xUnit汇总均为9 tests/0 errors/0 failures/0 skipped；GDB inferior exit code=0。
- [x] 对日志逐轮核对，10个B context地址、10个Pilz terminate this地址和10个target solve地址逐一匹配，无pointer mismatch。
- [ ] 继续覆盖Pilz solve已经运行时收到terminate的行为。Pilz源码的terminated latch仅阻止后续solve，不应推断为中断正在运行的solve。
- [ ] 设计pipeline/request级取消所有权隔离，避免一个pipeline的terminate影响其他pipeline仍存活的PlanningContext；在设计与测试通过前不改active gate、不把active_简单替换为计数器。
- [ ] 追查两轮日志中controller_manager.pal_statistics publisher在ROS context shutdown期间出现的`context cannot be slept with because it's invalid`异常；该日志未导致当前xUnit或GDB进程退出失败，但仍需独立定位。
- [ ] 后续所有测试继续保留stock rclcpp、mock与CI-only overlay边界；不修改MoveIt/rclcpp上游或正式Stäubli产品源码，不连接CS9，不执行HIL/SAT/实机动作。

**当前任务指针：** 21-01 / B / pipeline/request级取消所有权隔离设计 + Pilz in-flight solve行为测试 + pal_statistics shutdown日志排查。全局00-01仍最高优先级，MotionControlAlgorithms保持DEFERRED。


### 2026-11-17 Pilz运行中solve语义探针（Run #162待验收）

- [x] 固定MoveIt Jazzy源码审计：planning_interface::PlanningContext::terminate()基类注释要求终止正在运行的solve；Pilz PlanningContextBase::terminate()只设置atomic terminated_；solve()只在入口检查该标志，随后进入generator_.generate()，没有运行中取消检查或中断信号。
- [x] 在既有实验分支提交CI-only临时overlay测试 d0070d4ec571577b4968b9019b8b1b7c1df21f09；增加临时StaubliSolveBarrierProbe接口和Pilz solve入口屏障，未修改MoveIt/rclcpp上游、Stäubli正式产品源码。
- [x] 新探针在Pilz solve通过terminated_入口检查后停住；随后A=OMPL经真实public wrapper terminate；记录B solve仍未完成且terminated_=true；释放屏障后要求当前solve成功返回；同一context下一次solve要求PLANNING_FAILED；terminate后新建context负对照要求SUCCESS。
- [ ] Run #162（Actions 44024976831，job 133843014101）当前处于ROS Jazzy环境准备阶段；需等待临时overlay静态检查、编译、10轮动态测试、teardown回归和artifact。
- [ ] 若测试通过，结论限于“Pilz terminate不打断已越过入口检查的solve，但会阻止同一context后续solve”；不得等同于机器人停止运动或安全停止。
- [ ] 若测试失败，先检查动态屏障是否确实位于terminated_检查之后、solve线程是否完成/超时、异常退出和清理路径；不能将测试屏障超时直接当作产品行为。
- [ ] 下一阶段基于跨pipeline已证实的全局ActiveContexts影响，设计pipeline/request级取消所有权隔离；禁止直接移除isActive() gate或将active_简单改为计数器。
- [ ] 继续排查Run #160/#161的controller_manager.pal_statistics publisher shutdown期间invalid-context异常。

**当前任务指针：** 21-01 / B / 验收Pilz in-flight solve动态语义（Run #162），随后进行pipeline/request级取消所有权隔离设计。全局00-01仍最高优先级，MotionControlAlgorithms保持DEFERRED。
