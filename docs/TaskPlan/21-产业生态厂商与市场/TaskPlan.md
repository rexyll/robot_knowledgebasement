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


### 2026-11-17 pipeline/request取消所有权隔离候选设计（待实现与验证）

- [x] 明确拒绝仅将PlanningPipeline::active_从bool替换为计数器作为完整修复：它只能改善并发active状态表达，不能解决全局ActiveContexts跨pipeline广播terminate，也不能处理context创建/attach与terminate之间的竞态。
- [x] 候选设计采用pipeline-owned active request token集合：每个generatePlan请求在创建PlanningContext之前注册唯一token；token保存sticky cancel_requested和当前context引用；pipeline terminate只标记本pipeline token并对已attach的context调用terminate；context晚于terminate创建/attach时必须读取token取消状态并立即传递；solve结束/异常通过RAII注销token；isActive()由本pipeline活动token集合是否为空导出。
- [ ] 验证token注册必须早于任何可能被terminate观察到的工作；覆盖context创建前terminate、context创建后attach前terminate、attach后solve入口前terminate、solve入口后terminate。
- [ ] 覆盖同一pipeline两个或多个并发request：一个先完成时，另一个仍活动，isActive()仍为true；terminate应作用于所有该pipeline当前token，不误清理其他request。
- [ ] 覆盖A=OMPL terminate不得触及B=Pilz context，反向B terminate不得触及A=OMPL context；跨pipeline测试继续使用真实context pointer与terminate marker。
- [ ] 明确取消能力分层：pipeline请求被标记取消、planner context收到terminate、当前solve实际退出、控制器执行停止、安全停止是不同状态；Pilz当前实现不能保证已越过入口检查的solve被中断。
- [ ] 先在CI-only MoveIt临时overlay中验证设计，再考虑上游修复提案；未通过完整并发与竞态矩阵前，不修改上游、不合入Stäubli产品。

### 2026-11-17 pal_statistics shutdown日志源码归因

- [x] Run #160/#161出现的controller_manager.pal_statistics日志与pal_statistics StatisticsRegistry::publisherThreadCycle()代码路径匹配：后台publisher thread使用rclcpp::WallRate::sleep()，捕获std::exception并记录“Exception in publisher thread: ... Aborting!”。
- [x] ROS 2 Control Jazzy ControllerManager构造期间启动introspection和controller-manager statistics publisher threads；context在shutdown阶段失效时WallRate::sleep()抛异常，异常被publisher loop捕获；外层rclcpp::ok()为false后线程退出，Registry析构join线程。Run #160/#161的进程与GDB均正常退出，因此该日志不是进程实际abort的证据。
- [x] 公开realtime_tools Issue #480报告同样日志；维护者要求提供stack trace，并指出Jazzy并未使用RealtimeClock。当前不把该日志归因为RealtimeClock或MoveIt teardown。
- [ ] 将该已捕获shutdown异常作为非致命日志噪声独立治理；如需进一步确认安装包精确版本或异常抛出栈，后续增加仅诊断的publisher thread栈跟踪/版本pin证据。

**当前任务指针：** 21-01 / B / Run #162 Pilz in-flight solve动态验收；随后在CI-only overlay验证pipeline-owned request token取消所有权方案。全局00-01仍最高优先级，MotionControlAlgorithms保持DEFERRED。


### Run #162失败记录与修正

- [x] Run #162（Actions 44024976831，commit d0070d4ec571577b4968b9019b8b1b7c1df21f09）stock ROS 2 Jazzy rclcpp overlay构建通过。
- [x] Run #162在MoveIt临时overlay静态patch校验阶段失败：Python NameError，planning_interface_source尚未定义即被MoveGroup service校验块引用；尚未进入MoveIt编译和动态测试。因此该结果不能用于判断C++实现或Pilz terminate行为。
- [x] artifact 14302159156，SHA-256 019618f5967a9e2a45ae9f2915b9aee633ef91fca0d41638a4165ce863857b94。
- [x] 已在同一既有分支提交修正 af6a715d60d60ae1755a24711a1773a93c96c06d：把PlanningContext测试接口与Pilz barrier静态校验移到相关源码变量创建及patch完成之后。
- [ ] 等待修正提交触发Run #163；重新检查静态patch、C++编译、mock workspace、10轮in-flight动态测试、teardown回归和artifact。
- [ ] 不将Run #162归类为产品/算法失败；它是workflow静态校验脚本顺序错误。

**当前任务指针：** 21-01 / B / Run #163验收Pilz in-flight solve语义探针。全局00-01仍最高优先级，MotionControlAlgorithms保持DEFERRED。


### Run #163：Pilz in-flight cross-pipeline terminate动态验收通过

- [x] Run #163（[Actions 44025533230](https://github.com/rexyll/staubli_driver_ros2_from_org/actions/runs/44025533230)，job 133844827019，commit af6a715d60d60ae1755a24711a1773a93c96c06d）stock ROS 2 Jazzy rclcpp、MoveIt Jazzy临时overlay和Stäubli mock workspace均构建通过。
- [x] 日志中10次跨pipeline探针客户端均PASS。每轮均确认A=OMPL active=1；B=Pilz context的solve已越过terminated_入口检查并进入屏障；真实MoveItCpp::terminatePlanningPipeline("ompl")返回后，B terminated=1且solve_done=0；释放屏障后当前solve success=1；同context后续solve返回PLANNING_FAILED；terminate后新建context负对照SUCCESS。
- [x] 10/10 GDB inferior正常退出；另有A-PSM-retained + K + B-core无插桩teardown regression 10/10通过；每轮xUnit 9 tests、0 errors、0 failures、0 skipped；mock controller plan-and-execute成功。
- [x] Artifact ID 14303838124，SHA-256 716b8436e881f1e0be3d08dc2bff9d23811ac109015e7bf758babefa34deab73。
- [x] 结论：跨pipeline terminate确实会影响其他pipeline仍存活的context；对Pilz而言，terminate在solve入口检查后发生，不会中断当前solve，只会使后续同context solve失败。该行为存在取消语义与PlanningContext::terminate()接口文档不一致的问题。
- [ ] 证据边界：Run #163是CI mock + 临时MoveIt overlay，不是上游源码修复、HIL/SAT或实机安全验证；不代表机器人运动会停止。
- [ ] 下一步CI-only overlay实现pipeline-owned request cancellation token：token注册先于request adapter和PlanningContext创建；每request token具有sticky cancel_requested及context shared_ptr；context attach与terminate通过token mutex串行化；terminate先发生则attach时立即terminate；pipeline terminate仅取消本pipeline token集合；generatePlan所有return/异常路径RAII注销；isActive从token集合派生。
- [ ] 竞态矩阵：OMPL→Pilz与Pilz→OMPL双向隔离；同pipeline多个并发request；terminate发生在token注册前后、context创建前后、attach前后、solve入口前后；一个request完成而另一个仍活动；异常和提前return注销；超时/释放与销毁。
- [ ] 未完成矩阵前不修改MoveIt/rclcpp上游或Stäubli正式产品源码；不得将request取消、context terminate、solve退出、控制器停止、安全停止混为一谈。

**当前任务指针：** 21-01 / C / CI-only pipeline-owned request token原型与竞态测试。全局00-01仍最高优先级，MotionControlAlgorithms保持DEFERRED。


### 2026-11-17 pipeline-owned request token CI-only原型（等待Run #164–#167）

- [x] 在既有实验分支提交初始原型：`3a5bb2c9af424402f42103f4342ce6d42ba4c13c`。
- [x] 将跨pipeline测试改为由Pilz真实`PlanningPipeline::generatePlan()`创建request token并attach真实context；OMPL terminate时验证Pilz context未被污染、当前solve成功返回。
- [x] 同pipeline并发测试改为验证：快request完成后慢request仍使pipeline active；terminate取消慢request token；释放入口屏障后慢request返回PLANNING_FAILED。
- [x] 原型采用每request token、sticky cancel_requested、当前context shared_ptr、token mutex协调attach/cancel；pipeline terminate只取消本pipeline token集合；isActive从活动token集合派生；RAII负责函数退出注销；不再从PlanningPipeline调用PlannerManager::terminate()全局ActiveContexts广播。
- [x] 相关修正提交：`58f6045b25589cde67b6144b56364e588e0d6d69`、`1da783511c29ce917e7f937abbc7601624b720e7`、`eef52d6b5806cc26578ed34010429c1766d80968`。
- [ ] Run #164 [Actions 44037399349]、Run #165 [44037456726]、Run #166 [44037490607]、Run #167 [44037588033] 当前均未完成；Run #167对应最新workflow提交。等待静态patch、MoveIt编译、Stäubli mock构建和动态测试结果。
- [ ] 当前原型未覆盖token complete与terminate之间的线性化竞态；需引入completed状态/finish操作，使请求完成与terminate在token mutex下有明确先后顺序。
- [ ] 继续覆盖OMPL→Pilz、Pilz→OMPL双向隔离；同pipeline 2+并发request；context创建前/attach前后/solve入口前后取消；response adapter阶段取消；异常和提前return RAII清理。
- [ ] 当前仅CI临时overlay；无论单轮通过与否，不得直接视为产品修复，不修改上游或Stäubli产品源码。

**当前任务指针：** 21-01 / C / pipeline-owned request token原型CI验收与取消完成竞态修正。


### request token原型剩余边界补充

- [ ] 当前CI-only原型仅改变`PlanningPipeline::terminate()`，不改变`planning_interface::PlannerManager::terminate()`本身；后者仍遍历进程级ActiveContexts。审计MoveIt及本项目所有绕过PlanningPipeline直接调用PlannerManager::terminate()的调用点；发现调用点时单独处理，不得宣称全局API已修复。
- [ ] RequestGuard在函数退出时才注销token，最后一次cancel检查到token注销之间存在竞态。增加token completed状态和finish操作，使finish与requestCancel通过同一token mutex线性化；迟到terminate不得取消已完成请求，先到terminate必须让finish返回cancelled。
- [ ] Run #164–#167验收前暂停继续提交，避免并行CI继续扩散；以最新Run #167为唯一当前候选基线。

**当前任务指针：** 21-01 / C / Run #167静态校验与编译；通过后完成token finish线性化，再做双向隔离/并发矩阵。


### 2026-11-21 SERVO-908双活动OMPL请求取消验证与被测版本边界（Run #44894004665）

- [x] 在既有实验分支 `experiment/moveit-main-owner-lifetime-only` 将SequenceService路由诊断marker限定为专用7.732请求；双token场景的7.736 SequenceService请求继续走真实pipeline选择和 `CommandListManager::solve()`，但不再污染旧版“仅一个route marker”的断言。修正commit：`f53d9d3ac82cb4b1cef5a56bbd47c0847dffada5`。
- [x] 对照当前workflow源码，确认已纳入PlanService + SequenceService两个OMPL请求的双活动token测试：两个请求分别使用7.735/7.736，在各自真实PlanningContext attach后停在solve前屏障；同一次OMPL pipeline terminate应分别取消两个token并向两个context各dispatch一次terminate；两个请求内部错误码为PLANNING_FAILED(-1)，服务外部错误码为FAILURE(99999)，最后registry恢复idle。checker还保留两个context/token地址唯一性、同pipeline指针、事件区间归属、cross-pipeline与原teardown门禁。
- [ ] Run #44894004665（[Actions](https://github.com/rexyll/staubli_driver_ros2_from_org/actions/runs/44894004665)，HEAD `f53d9d3ac82cb4b1cef5a56bbd47c0847dffada5`，job `136815647387`）最近核对仍在步骤8 `Build patched MoveIt move_group`；步骤1–7成功，Stäubli mock workspace build和10轮测试尚未开始，当前没有功能性结论或artifact。GitHub UI步骤10名称沿用旧“A-PSM-retained + K + B-core”字样，但当前workflow内容已经纳入上述multi-token与其他回归断言；以后须以实际源码/日志/xUnit为准。
- [ ] **被测源码pin差异必须保留：** 本章先前固定验证pin为 `9e617a9e323ef3342f5151a89239bfd93c089f8c`；当前workflow实际checkout为 `7d9fa0d715db46060199eeca541514ddeed9c4c1`。Git compare显示 `7d9fa0d` 相对 `9e617a9` ahead 17、behind 0，区间涉及6个文件，其中包括 `staubli_bringup/launch/launch_robot_control.launch.py` 和 `staubli_moveit_config/launch/staubli_moveit.launch.py` 等产品入口配置，以及package.xml、测试和CI文件。因此本轮结果只能归属到 `7d9fa0d` fork集成快照，不是 `9e617a9` 同版本复验，也不是ICube上游main/实机证据。需要完成逐文件差异归属后，再决定是否更新正式验证pin或对旧pin单独复验。
- [ ] 当前双token屏障位于 `context->solve()` 之前，覆盖两个已attach、未进入solve的请求取消；不得将它表述为中断两个正在运行的OMPL solve。Pilz→OMPL反向隔离、直接调用 `PlannerManager::terminate()` 的调用点审计和完整同HEAD 10轮回归仍未关闭。
- [ ] 本轮成功后仍不得合入上游/产品代码；继续仅在CI-only MoveIt/Pilz overlay + stock ROS 2 Jazzy rclcpp + Stäubli mock中验证。不得连接CS9或执行HIL/SAT/实机动作。

**当前任务指针（覆盖本文件较早的Run #164–#167历史指针）：** 21-01 / SERVO-908 / 首先验收Run #44894004665；随后按固定pin边界完善Pilz→OMPL反向隔离与直接PlannerManager调用审计。全局00-01仍最高优先级，MotionControlAlgorithms继续DEFERRED。
