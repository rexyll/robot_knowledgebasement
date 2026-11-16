# TaskPlan｜机器人行业全域知识体系建设总计划

> **本文件是整个仓库的最高级任务治理文件。** 所有知识章节的任务都必须遵守本文件的 Guide 与 Limit。章节级任务只定义本章节的范围、节点、交付物、验收证据和依赖，不得自行降低或替换全局约束。
>
版本：v12.74  
> 建立日期：2026-11-03  
> 适用范围：整个 Robot Knowledge Basement 仓库  
> 当前状态：执行中；根当前任务章节00（知识治理与分类体系），主任务节点00-01（全仓库资产基线已完成386/386路径与Blob/字节数对账；claim-level和许可/授权审计未完成；Python Toolkit 13项权利人及再分发授权待确认；IMU模型/公式与BMI088、ADIS16470数据表P0定向复核已完成，目标IMU实测和权利审计仍待完成；LiDAR的ROS 2消息时序、型号条件参数及普通/安全扫描仪输出边界P0复核已完成，目标点云/去畸变和安全链测试仍待完成）；第21章21-02并行推进（医疗/康复/腔镜机器人注册与标准证据继续补充，原始电子证照和适用范围附件仍有缺口；柏惠维康重庆生产许可、生产范围/地址及自述8张注册证的完整清单待监管原件）。Stäubli专项更新：Run #113 5/5确定性复现TEM stopExecution check-lock-recheck漏join；Run #117 always-join CI overlay 5/5通过（artifact 14149782675，SHA-256 78e0d6e22d49bffeff7f983f2b528d056b0d2fcf84bdddd44c909fd8538a8f43），五轮join_performed=1、execution_thread_joinable=0、active_handles=0。MoveGroup teardown 共同背景K下完整A/B 2×2矩阵已完成：K-only #121、K+A #118、K+B #119均5/5 FAIL，K+A+B #107 5/5 PASS。源码已确定实际链：MoveItSimpleControllerManager 逆序销毁 controllers_ map 中的 FollowJointTrajectory handles；Action Client custom deleter 在 strong count 归零后尝试 remove_waitable，原 weak_ptr.lock() 失败导致 expired entry 留存；后续没有新的 add_waitable 清理时，该control block延迟到controller_mgr_node_的default CallbackGroup析构释放。TEM成员逆序析构又使controller-manager loader/DSO先于controller node/group清理而卸载。control-block destroy/vtable地址是否落在该DSO仍待Run #122 GDB映射验证。Run #122已完成：5/5 mock plan-and-execute SUCCEEDED、5/5 teardown PASS；五轮诊断均显示 controller node 的 NodeBase/default CallbackGroup expired weak Waitables 在 controller-manager DSO unload 前清理（Actions 43791758924，artifact 14192853671，SHA-256 6958f483320fff3c93b3d432d0ca61f5d2f8d19030f28f8c6055a76cef5e5266）。Run #122未输出 control-block vtable/destroy 地址映射，因此不能据此确认控制块释放函数归属插件 DSO。K-only（A=OFF/B=OFF）+ rclcpp CallbackGroup::remove_waitable expired-entry pruning 单点反证已在既有隔离分支实施；Run #123 因内嵌 Python SyntaxError、#124/#125 因跨 Actions step 变量 NameError 均在 mock test 前配置失败，不计入功能性实验结果；Run #126（Actions 43794655028）已通过 rclcpp overlay、patched MoveIt 与 Stäubli mock workspace 构建；但测试 step 未切换到 /tmp/staubli_ws，colcon 五次均忽略未知包并报告 0 packages/0 tests，pruning=0；属无效空跑，不计入反证。已在既有分支修复测试 step 工作目录并加 ros2 pkg prefix/colcon list 预检；Run #127（Actions 43798751700，commit 2c578fa670b0d5c9bf845c53591cbc334f952438）已完成：K-only + CallbackGroup expired-entry pruning 虽每轮日志出现18条pruning marker；去除`colcon test-result --verbose`重复打印后每轮9条不同记录，五轮共45条、5/5 mock plan-and-execute SUCCEEDED，但group地址尚未映射到controller_mgr_node_的default CallbackGroup，目标组覆盖未证实；5/5均在TEM private Executor的WaitSet/DynamicStorage WeakWaitableEntry weak-control-block释放阶段SIGSEGV（-11），故不能把该轮作为目标CallbackGroup pruning的有效单点反证。Run #136（Actions https://github.com/rexyll/staubli_driver_ros2_from_org/actions/runs/43832589348）已完成：10/10在PSM析构调用链中的Node/NodeBase/CallbackGroup析构weak_ptr<ServiceBase>时收到SIGSEGV；Run #136/#137没有输出该Node与pnode_的指针对应关系，故不能认定为pnode_；故障PC仍在librclcpp映射区，但间接调用所用vptr地址不在当前进程映射中；librclcpp、libmoveit_planning_scene_monitor及MoveGroup capability相关DSO在故障时仍映射，故不能归因于这些关键库已卸载。每轮mock执行与launch断言本身通过；另发现验收脚本从错误日志文件读取7项汇总，造成次级误报，已修正。Run #136/#137的GDB栈均显示PSM析构链中Node/NodeBase/CallbackGroup释放时，单个weak_ptr<ServiceBase>控制块weak-count release发生SIGSEGV；#136 vector析构区间0x5b24d96db600–0x5b24d96db610仅1项。此前将该Node直接归属pnode_的判断撤回：Run #136/#137均未打印Node身份和实际vector size。新源码候选进一步收敛并确认了实际构造重载：MoveIt Jazzy PlanningSceneMonitor构造函数在`planning_scene_monitor.cpp`第120行调用`std::make_shared<tf2_ros::TransformListener>(*tf_buffer_)`，使用的正是TF listener自行创建Node的简化构造重载；该重载创建`optional_default_node_`，显式关闭parameter services/event publisher，但未关闭ROS 2 Jazzy NodeTypeDescriptions默认启用的start_type_description_service，故其default CallbackGroup可仅含`~/get_type_description`这一项ServiceBase weak entry。PSM成员顺序使tf_listener_先于pnode_销毁。Node::~Node()函数体没有显式reset node_type_descriptions_，该成员在隐式成员逆序析构时先于node_base_释放；随后NodeBase销毁默认CallbackGroup并释放最后weak引用，正好解释单元素vector和weak_ptr析构栈。该生命周期链是强静态候选，运行时仍需Run #138把dying Node/NodeBase/CallbackGroup地址与PSM tf_listener_->optional_default_node_、服务名关联确认；故障vptr失效的根因仍未确定。Run #137（Actions 43836147761，commit 4aa4539a9adfd5efe0adea52753ba1847abf8a53）第8/9步构建成功；第10步10/10均SIGSEGV，10轮汇总均为7 tests、0 errors、2 failures；GDB脚本第22行x/8gx $rax读取未映射地址而中断，service_ptrs_.size()/[GDB-WEAK]循环未执行，故没有服务身份/vptr结论。Run #138（Actions 43839729557，commit 8680810cfe15152ce5b9cd6ed21cbc196e2baaad）未进入源码构建或GDB测试：ROS Jazzy setup成功后第4步rosdep update访问raw.githubusercontent.com/ros/rosdistro/base.yaml遭遇Connection reset by peer并失败，后续步骤全部跳过，不计为代码/teardown结果。已在原实验分支给rosdep update加5次有限重试（每次间隔8秒，最终仍fail-closed）；Run #139（Actions 43840240632，commit 5332c79ead53d811bc7b5820d10e269eeaddff66）已完整完成环境准备、stock rclcpp无插桩overlay、MoveIt构建和Stäubli mock workspace构建；10/10次mock plan-and-execute与每轮7项launch assertions通过，但10/10次move_group teardown SIGSEGV。GDB首次明确dying Node==PSM node_、非pnode_；CallbackGroup service_ptrs_ size=23；index 22为/plan_sequence_path，service创建日志、Service对象地址、weak control block地址逐轮对应。每轮libsequence_capability.so在SIGSEGV前卸载，但本轮未直接捕获加载时section范围，故其vptr归属仍待地址映射确证。MoveIt源码固定commit f11204b8a9b98e4ba28e564721d24a7077f5f969：MoveGroupSequenceService::initialize()在MoveItCpp节点创建/plan_sequence_path service，lambda捕获capability this；plugin loader卸载顺序与PSM node_晚于plugin清理析构的链吻合。Run #140（Actions 43851082807，commit 7b1dd647f0c6725e57f6918937e8d44fdccfd949）10/10仍复现同一SIGSEGV，且每轮7项测试通过；诊断脚本尝试调用GDB Python Objfile.sections()，但当前GDB Objfile API不存在该方法，未采集任何section，Run #140的NO-MATCH不具备排除vptr属于该DSO的效力。已在同一隔离分支改用GDB maintenance info sections ALLOBJ解析加载时ELF section区间，并在fault site比较vptr；Run #141（Actions 43855570879，commit 81cc2ba6148310f2760dc9623c4cc916703cd225）已完成ROS/Jazzy、stock rclcpp无插桩overlay和MoveIt依赖安装，当前第8步patched MoveIt move_group构建中；该版section regex后续发现仍存在转义问题，待日志确认section采集结果。Run #142（Actions 43856000696，commit 4921da033766cf4c69f43ba78cd8c8a285f5ad4b）因新增Python多行字符串中两行缩进不足YAML run块边界而产生0个job，未运行任何构建/测试，不计功能性结果。已修正缩进并在workflow中新增临时MoveIt overlay单变量处理：MoveGroupSequenceService改用自身MutuallyExclusive callback group，析构时先reset /plan_sequence_path service再reset group，并要求从source overlay构建Pilz插件、运行前检查实际加载的sequence_capability.so路径；同一版本修正GDB section正则转义。Run #143（Actions 43856138236，commit 9d3878210f82a43f715bedc278cfe5d50c598c9b）已完成stock rclcpp无插桩overlay构建，但第6步临时MoveIt补丁静态注入失败：old_sequence_create多行字符串续行缩进未恢复原始源码空格，未匹配到SequenceService create_service源码锚点；MoveIt/Pilz构建与测试均跳过，不计teardown结果。已把回调response续行的嵌入缩进从YAML块内13格修正为23格，使YAML剥离10格后还原源文件13格，并触发Run #144（Actions 43856829744，commit 849c5fe69b6d6fa17aefe832f18500f61de32260），当前容器初始化中。Run #141（Actions 43855570879）仍在第8步patched MoveIt构建中。仍不修改MoveIt/rclcpp upstream、不修改Stäubli产品源码、不连接CS9、不发送真实运动命令、不宣称HIL/实机验收。MotionControlAlgorithms源码集成继续DEFERRED，待00-01验收、14-EXT-02第三方许可/来源/SBOM及目标仓库兼容性门禁关闭并取得具体导入授权。

> **2026-11-16 Stäubli 最新状态更正（Run #141–147 最终状态）：**
> Run #141（Actions 43855570879）10/10 mock execution及7项launch assertions本体通过，但10/10 teardown SIGSEGV；其GDB section parser未采集到Sequence DSO section，NO-MATCH不构成反证。
> Run #144（Actions 43856829744）完成ROS/Jazzy、stock rclcpp、MoveIt和Pilz source-overlay构建及插件路径预检；SequenceService专属MutuallyExclusive callback group及析构先reset service再reset group的临时候选，10/10轮均走到GDB inferior正常退出、未观察到真实SIGSEGV；但旧GDB脚本在正常退出后无条件执行bt full，触发No stack并使GDB进程退出1，导致launch test 10/10失败。
> Run #145（Actions 43859018027，commit 3a857b2c7fdaad9d948c5a24cb1a6ef7450a0ddc）10/10个inferior正常退出、无真实SIGSEGV，但section parser每轮均报告no sequence capability sections parsed，未获得可用section行；GDB同样因正常退出后的No stack导致10/10 launch测试失败。
> Run #146（Actions 43859201450，commit aba0eaaa5b0af51bde0ae60eb010dca2aaa40326）10/10轮均在NodeServices::add_service与CallbackGroup::add_service处捕获到/plan_sequence_path control-block；10/10轮的GDB info symbol均将vptr解析为GetMotionSequence Service control-block vtable，位置是临时source overlay的libsequence_capability.so之.data.rel.ro；10/10个inferior正常退出、0真实SIGSEGV。该结果直接确认control-block vtable来自Sequence capability DSO，填补DSO归属证据缺口；Actions整体仍因旧GDB No stack处理失败。
> Run #147（Actions 43862172486，commit a4e8a321bd8185dc5c2039fba02d39c8c374e777）已完成有效10/10无插桩mock回归：10/10 mock plan-and-execute成功，10/10 GDB inferior exit code=0，每轮7 tests/0 errors/0 failures/0 skipped，K+A+B teardown marker顺序通过，聚合失败0/10。GDB maintenance info sections解析器仍报告未采集到Sequence DSO section，不作为section-range证据；但每轮info symbol均直接将GetMotionSequence control-block vtable定位到临时source-overlay libsequence_capability.so的.data.rel.ro。这关闭的是单线程mock teardown回归，不代表并发/取消门禁完成。
> 已在既有实验分支 experiment/moveit-main-owner-lifetime-only 提交同一OMPL pipeline并发探针（`b0bad196b7328c19bf24a2cabc58c8781f2c279e`），并修正新增unittest后的包级汇总验收门槛（`031478a961bb62ded1231e5288055ae4b8cf7961`，期望8项xUnit测试、pre-shutdown suite 3项）。两个提交均只改CI workflow。当前尚未取得该分支push对应Actions run ID/日志，动态并发结果未定；需核验五个barrier marker、同pipeline地址、fast退出时slow仍in-flight、两项service response及clean teardown，再执行terminate门禁。未关闭动态并发与停止语义门禁前，Sequence callback-group拆分不得合并。全部仍限CI临时MoveIt/Pilz overlay + stock rclcpp + Stäubli mock，不修改MoveIt/rclcpp upstream及Stäubli正式产品源码，不连接CS9、不宣称HIL/SAT/实机验收。全局00-01仍为最高优先级，MotionControlAlgorithms集成继续DEFERRED。

> **2026-11-16 Stäubli Run #135 最终定位与 #136 GDB 取证：** Run #135（Actions https://github.com/rexyll/staubli_driver_ros2_from_org/actions/runs/43823418805，workflow commit `ac87221956b3d946d93fb1732fb12ea4e59e8094`）构建/静态校验全部通过，10/10 mock execution成功但10/10 teardown SIGSEGV。每轮PSM dtor body完整走到BODY-END；末尾计数node_use=2、pnode_use=1；main的PSM reset END没有实际运行时marker。GDB stack显示PlanningSceneMonitor析构后的隐式成员shared_ptr释放进入rclcpp::Node::~Node() → NodeBase::~NodeBase() → CallbackGroup::~CallbackGroup()，最终在vector<weak_ptr<ServiceBase>>的weak control-block `_M_destroy()`崩溃。MoveIt源码确认pnode_是PSM构造时创建的private Node，private executor已reset后use_count=1，按成员逆序它先于node_销毁；该轮据node_use=2、pnode_use=1和成员逆序曾推断故障边界为pnode_最终释放；但Run #136后续观测到vector仅1个weak_ptr，与pnode_静态预期至少7项不符，且未建立Node指针对应，故该归属现已撤回并降为历史候选。control-block manager/vtable是否属于已卸载DSO仍未证明。Run #136（Actions https://github.com/rexyll/staubli_driver_ros2_from_org/actions/runs/43832589348，commit `337bf6c6f40b4982629e690d1a5748f94d914053`）正在相同mock条件下用GDB采集fault PC、寄存器、已加载共享库及进程映射；资源清理顺序不变。全局00-01仍为最高优先级，MotionControlAlgorithms集成继续DEFERRED。


> **2026-11-16 Stäubli pnode_ ServiceBase 候选收窄（Run #136 取证中）：** MoveGroupGetPlanningSceneService::initialize()调用PSM::providePlanningSceneService()；PSM把`GetPlanningScene` service存入`get_scene_service_`，service创建于私有`pnode_`。ROS 2 Jazzy `Node::create_service()`默认group参数为nullptr，NodeServices::add_service()因此使用该Node的default CallbackGroup，并调用CallbackGroup::add_service()把ServiceBase登记为weak_ptr。PSM的`get_scene_service_`强引用在pnode_隐式销毁前已随PSM成员析构释放，故该weak_ptr成为pnode_ CallbackGroup在NodeBase析构期间要清理的精确候选。Run #135 GDB证明崩溃位于此weak_ptr vector的`_M_destroy()`；control-block manager/vtable地址归属仍待Run #136的PC/DSO映射确认，不能认定插件卸载为根因。

> 2026-11-15 00-01增量（09-03电子电气设计P0证据复核）：已按 IEC 60204-1 公开目录/条款主题增量核验 PE/FE、移动机器车载电源保护联结端子、供电隔离、过电流保护、SCCR 和验证，并对照 IEC 60947-2/-3/-4-1、IEC 61439-2 及 ABB 说明区分断路器 Icu/Ics、隔离器件条件额定值和整机 SCCR。仅为资料/条款边界审查，无项目原理图、短路电流计算或实验室测试；详见 09-03 §10 与专项报告。

> 2026-11-15 00-01增量（减速器P0证据复核）：已对照 Harmonic Drive CSG-GH/CSF-GH、Nabtesco RV-Original 和 Norelem 蜗轮蜗杆目录，区分连续额定/重复峰值/平均负载/瞬时冲击/加减速扭矩与专属负载谱算法，明确蜗轮蜗杆自锁不能作为安全制动器。详见《减速器》§7 和专项报告；仅为公开资料增量审计，不代表本项目减速器选型或耐久验证已完成。

> 2026-11-15 00-01增量（自动充电系统P0证据复核）：已核对 EN 1175:2025 对无人驾驶工业车辆自动运行功能的范围排除、ISO 3691-4 第三版 DIS 的自动充电条款/系统组成预览，并对照 ABB F702 2025 手册补充在线充电刷板短路/触电残余风险和停靠/CAN/接触器时序。仅为公开资料增量审计，不代表本项目充电系统符合标准或通过现场验证；详见充电知识页 §8 与专项报告。

> 2026-11-15 00-01增量（电机与驱动器P0证据复核）：已补充 STO/SS1/SS2/SOS/SBC/SLS 等驱动安全子功能与机器级急停、机械制动、电气隔离边界，核验 IEC 61800-5-1、IEC 60204-1、ISO 13850 版本状态及 Siemens S120/ABB ACS880 产品配置示例，详情见知识页 §9–§10 和专项报告。仅为公开来源增量审计；整篇 claim-level、准确器件 SKU/证书/参数和实际机器验证仍未完成。

> 2026-11-15 00-01增量（安全防护器件P0证据复核）：已交叉核验 ANSI/A3 R15.06-2025 三部分发布状态、OSHA 对共识标准的说明、ISO/DIS 3691-4 生命周期字段、OS32C/SICK microScan3 配置响应、3SK1/G9SE/PSENmlock 的型号和时间语义；知识页 §12 与专项报告记录页面冲突和验证边界。仅为公开资料审计，不代表目标机器人器件适用、现场验证或整机安全通过。

> 2026-11-15 00-01增量（功能安全标准生命周期复核）：已对《功能安全体系》增加 ISO/IEC 生命周期与适用边界、欧盟《机械法规》(EU) 2023/1230 适用日期的公开来源快照，详情见知识页 §11 和功能安全增量审计报告。该轮仅完成官方目录/摘要核验，整篇 claim-level、标准全文、目标市场法律适用性和产品验证仍未完成；00-01 继续进行中。

> 2026-11-15 00-01增量：已完成 Python Toolkit 实际 wheel/sdist 的 13 个发布源码/测试文件 Git 路径历史与静态内容复核。17 条路径历史 commit 均显示 rexyll 为 author/committer，但均为 unsigned；chunker.py 存在与两个更早公开项目相似的重叠分块控制流程/说明文字线索，尚未确认来源关系。13/13 权利人仍未验证、再分发状态仍未确定；根 LICENSE 与 PEP 639 metadata 暂不变更，00-01 继续执行。

> 2026-11-16 Stäubli teardown增量（Run #127反证与下一最小变量实验）：#127已完成真实测试工作区预检、每轮1次 launch test执行；5/5 mock轨迹均SUCCEEDED，CallbackGroup expired-entry pruning每轮出现18条日志（`colcon test-result --verbose`重复打印同一输出）；去重后每轮9条、五轮45条，但5/5 move_group 在析构TEM private Executor的WaitSet/DynamicStorage::WeakWaitableEntry时SIGSEGV（exit -11）。崩溃栈为 WaitSetTemplate → DynamicStorage::WeakWaitableEntry → std::weak_ptr::_M_weak_release → _M_destroy；栈定位在与CallbackGroup::waitable_ptrs_分离的Executor WaitSet weak-entry vector；但#127的group地址未与controller_mgr_node_的default group建立映射，不能据此判断目标group pruning是否实际命中，也不能仅凭栈帧认定control block销毁函数来自插件DSO。现已在原隔离分支启动 A=ON、K=ON、B-core=ON最小切片：先join/remove/reset private executor/WaitSet，再reset controller-manager instance、controller node，最后reset loader；暂不reset event subscription、parameter callback或event callback group，并在WaitSet WeakWaitableEntry destructor中分别标记 associated_entity 与 waitable 两份weak reference的释放。#128（Actions 43803282990）和#129（Actions 43803323983）均在MoveIt patch step因Python字符串SyntaxError退出，未进入MoveIt build/mock测试；#130（Actions 43803660660，commit 9d9f33b8281fdf7d412153100666318470d0b9af）已完成：A=ON、K固定、B-core=ON；5/5 mock execution与7项launch assertions通过，private executor/WaitSet先于controller manager、controller node和loader释放，5/5无SIGSEGV。临时rclcpp析构插桩尚可能影响时序，已在同一分支启动stock rclcpp无插桩10次复核。仍仅限临时CI overlay/mock，不修改upstream/产品源码、不连接CS9、不发送真实运动指令、不宣称HIL/SAT/实机验收。

> 2026-11-16 Stäubli增量（A+K+B-core正向结果）：Run #130（[Actions](https://github.com/rexyll/staubli_driver_ros2_from_org/actions/runs/43803660660)，commit `9d9f33b8281fdf7d412153100666318470d0b9af`）rclcpp overlay、patched MoveIt及Stäubli mock workspace均构建成功；A=ON、K固定、B-core=ON五轮均真实执行mock plan-and-execute（5/5 SUCCEEDED），每轮launch test 7 tests/0 errors/0 failures，teardown和顺序检查均exit 0，无SIGSEGV。每轮private_executor_.reset()区间都有8次WaitSet WeakWaitableEntry析构入口、8次associated_entity reset END、8次waitable reset END；其中5个Waitable weak ref已expired/use_count=0，3个仍live（use_count 1或4），8个associated_entity weak ref均expired/use_count=0。随后controller manager reset、controller node reset（begin前use_count=1）、loader reset按序完成。该轮说明A+K下B-core清理候选5/5通过mock CI，但rclcpp WeakWaitableEntry手工析构插桩可能改变时序，尚不作为最终充分性结论。Artifact `14198705205`，SHA-256 `de8eea001b5b3718e5bfd39bb5d94439faa2a7a43bf10815a6c6aef89d8a5be7`。原实验分支现已启动stock rclcpp无插桩10轮复核；不新建分支，不修改upstream或Stäubli产品源码，不连接CS9、不执行实机动作。

> 2026-11-16 Stäubli ownership-order复核：A中的`planning_scene_monitor.reset()`、`moveit_cpp.reset()`、`nh.reset()`只释放main()局部shared owner，不应直接等同于对象当场析构。MoveGroupExe::context_持有MoveGroupContext；MoveGroupContext又持有MoveItCpp、PSM和TEM；MoveItCpp自身持有node_、PSM_和TEM_。最后析构需沿MoveGroupExe capabilities/context → MoveGroupContext成员 → MoveItCpp成员逆序链追踪。Run #131（Actions 43808189052）为 stock rclcpp 无插桩复核的静态校验逻辑冲突，未进入测试；修复后 Run #132（Actions 43812432706，commit 4d58b7e6）在 stock rclcpp、无插桩条件下 A+K+B-core 10/10 通过，10/10 mock 执行成功、每轮7项launch assertions全通过、B-core teardown顺序检查成功、无SIGSEGV（artifact 14201681819，SHA-256 1bd5c27cbf3803dc8565d24b73c06b7b9b99edda64874b57dc42db0c3664cb0e）；随后 A-PSM-retained 单变量实验 Run #133 因 workflow YAML 缩进错误创建了0个job，不计功能结果，已在同一分支修复并触发 Run #134（Actions 43816245159），等待10轮结果；后续A因子拆分继续以weak_ptr/use_count及真实析构作用域为依据。


> 2026-11-16 诊断插桩风险补充：Run #130在`DynamicStorage::WeakWaitableEntry`新增用户声明析构函数；该操作会抑制编译器隐式move constructor，可能改变`std::vector<WeakWaitableEntry>`扩容时的move/copy选择及weak-count时序。尽管显式reset顺序与原成员逆序析构顺序一致，仍不能将#130视为无插桩复现。Run #131已改回stock rclcpp source，并提高到10轮。


> v11.29补充：CMake File API index.reply结构与codemodel/target jsonFile引用已加入路径边界保护；对应collector、负向测试及普通CI结果见文末2026-11-11记录。


---

## 1. 项目使命与最终目标

### 1.1 项目使命

建设一个面向**整个机器人行业与机器人全生命周期**的长期、系统化、可验证、可追溯、可持续更新的知识体系。它不只是技术资料库，而是一套面向非机器人行业学习者的**自学教材、工程设计手册、研发工作台、量产交付指南和持续更新的行业知识底座**。

**核心使用者：没有机器人行业背景的人。** 知识库不能默认读者已经会 ROS、机械设计、电子电路、嵌入式开发或机器人算法；必须从必要的数学、物理、编程、机械、电学和工程常识开始，说明先修知识、学习目标、工具准备和能力检查，再逐步进入机器人专业知识。读者应能沿着明确的学习路线理解知识，并通过练习、计算示例、设计任务、代码和测试逐步建立实际能力。

**最终目标：让一个愿意学习、能够投入合理时间与资源的非行业人士，能够依靠知识库，从需求和产品定义开始，逐步完成一类具体机器人的方案论证、系统设计、零部件选型、机械/电气/软件开发、样机集成、测试验证、合规准备、生产工艺导入、供应链和 BOM 管理、试产、量产爬坡、客户交付及售后维护。** 不要求一个人独自具备所有专业资质；知识库必须明确哪些工作可以自学和动手，哪些工作需要专业人员、实验室、工厂、检测机构、认证机构、预算或团队协作。

“全行业知识”是持续扩展的覆盖目标，不表示一次性穷尽所有机器人、零件、型号、论文、参数或厂商。项目以稳定的知识分类、代表性深度、可验证来源和持续补缺机制逼近完整覆盖；不得以篇数或字数代替知识质量。

### 1.2 覆盖边界

知识体系至少覆盖以下维度，并允许在审计中发现遗漏后新增子主题：

1. **机器人类型与应用**：工业、协作、移动、AGV/AMR、仓储物流、清洁、配送、服务、医疗、康复、人形、双足/四足、无人机、水下、特种、农业、建筑、矿业、能源巡检、空间机器人、软体机器人、外骨骼、远程操作、群体/集群机器人等。
2. **需求与系统工程**：应用场景、利益相关方、任务流程、运行设计域（ODD）、产品需求、系统需求、约束、架构权衡、需求追踪和产品生命周期。
3. **机械结构、材料与制造**：构型、刚度/强度/疲劳、运动副、轴承、紧固、密封、防护、热/振动、材料、表面处理、加工、装配、可制造性和可维护性。
4. **运动机构、传动与执行器**：轮式/履带/足式/飞行/水下运动机构、机械臂关节、减速器、齿轮、丝杠、直线模组、电机、驱动器、制动器、末端执行器。
5. **电子、电路与能源**：电源树、模拟/数字电路、PCB、线束、连接器、接地、隔离、EMC/ESD、BMS、电池、充电、热管理、功能安全链。
6. **传感器与感知硬件**：2D/3D LiDAR、RGB/双目/深度/热成像/事件相机、毫米波/超声波、IMU、编码器、力/力矩、触觉、GNSS、UWB、磁/电流/温度/压力等传感器及标定。
7. **计算平台与硬件外设**：SoC、CPU、GPU、NPU、FPGA、MCU、MPU、工控机、边缘服务器、内存/存储、网卡、显示、音频、USB/PCIe/CAN 等外设和扩展板。
8. **操作系统与实时计算**：Linux 发行版、内核、RTOS、实时调度、虚拟化、容器、启动链、系统裁剪、可靠性和安全加固。
9. **嵌入式软件、固件与驱动**：Bootloader、BSP、HAL、设备树、MCU 固件、外设驱动、总线驱动、传感器/执行器驱动、诊断、升级和故障恢复。
10. **通信、网络与中间件**：UART/SPI/I²C/USB、CAN/CANopen、EtherCAT、串口、工业以太网、TSN、Wi-Fi、蜂窝网络、网络安全、时间同步、DDS、MQTT、HTTP/gRPC、ROS 通信机制。
11. **机器人软件架构与工程体系**：分层/组件/插件/微服务架构、接口和数据模型、状态机、行为树、配置管理、构建、测试、CI/CD、仿真、部署、日志、可观测性和 DevSecOps。
12. **数学基础与通用算法**：线性代数、几何、概率统计、优化、数值方法、坐标变换、状态估计、运动学、动力学和实时算法基础。
13. **感知、定位与建图**：标定、目标检测/跟踪、点云、视觉、SLAM、VIO/LIO、多传感器融合、定位、地图表达、语义理解和环境建模。
14. **规划、控制与操作**：任务/路径/运动规划、避障、轨迹优化、底盘控制、机械臂控制、抓取、力控、阻抗/导纳控制和人机协作。
15. **上层应用与人机交互**：任务应用、业务流程、HMI、语音/视觉交互、遥操作、权限、用户体验、可访问性和行业应用集成。
16. **云平台、IoT 与远程运维**：设备身份、注册、遥测、数字孪生、设备管理、OTA、远程诊断、日志采集、数据闭环和云边协同。
17. **多机器人调度与车队管理**：任务分配、交通管制、路径协调、充电调度、车队健康度、WMS/MES/ERP 对接和多机协同。
18. **BOM、供应链与成本工程**：层级 BOM、替代料、采购、供应商、交期、成本、制造损耗、备件、生命周期和 EOL 风险。
19. **性能指标、测试与验证**：性能定义、测试方法、仿真/SIL/HIL/实机测试、可靠性、环境适应、可用性、回归、验收和量产质量。
20. **安全、规范、法规与伦理**：机械/电气/功能安全、网络安全、无线/EMC、隐私、行业准入、产品认证、AI 治理和伦理。
21. **产业、厂商与市场生态**：产业链、核心厂商、产品线、代表型号、开源生态、标准组织、专利/论文、市场结构和趋势。
22. **项目、系统集成与全生命周期**：项目架构、接口集成、部署调试、生产制造、交付、运维、维修、返厂、退役和案例复盘。
23. **数据工程、AI 与具身智能**：数据采集/标注/治理、仿真数据、模型训练与评估、强化/模仿学习、VLA、基础模型、Sim2Real 和边缘推理。
24. **知识治理与知识库工具链**：分类体系、术语、来源台账、版本、双链、质量审计、导入、检索、Embedding、向量库、RAG、Agent 接口和自动化维护。

### 1.3 成功标准

最终成果不是“写满目录”，而是形成以下闭环：

- 主题覆盖：每个章节有分类树、核心概念、关键技术、代表实现、上下游依赖和明确的未覆盖项。
- 内容质量：关键事实有来源；数据有单位、版本、工况和日期；工程方法可复核；不确定性被明确标注。
- 工程可用：选型、设计、集成、测试、部署、运维问题能从知识库找到依据和操作边界。
- 关系完整：硬件、驱动、OS、中间件、算法、应用、云端和管理链路可以互相追溯。
- 可持续：有章节负责人/维护入口、更新触发条件、过期内容标识、变更记录和自动化检查。
- 可检索：文档结构、元数据、术语和来源满足后续全文检索、语义检索和 RAG 的需要。
- 零基础可进入：关键知识点有先修要求、术语解释、循序渐进的讲解、例题/示例、练习和能力检查；不以“读者已经懂机器人”为前提。
- 从学习到实战：有基础学习路径、分层课程、工具/设备清单、练习项目和阶段成果，不只给出链接列表。
- 从样机到量产：有跨章节端到端主线，覆盖需求、概念验证、工程样机、设计验证、工艺验证、试产、量产爬坡、客户验收、售后和退役。
- 工程交付可复用：每个阶段都有输入条件、决策依据、输出文档/图纸/代码/BOM/测试记录、评审要点、准入/退出标准和常见失败处理。
- 代表项目可贯通：至少建立一条从需求到批量交付的完整参考项目链，并为不同机器人类型设计差异化分支，避免把 AMR 的路径误当成所有机器人的唯一路线。

---

## 2. 计划文件拆分结构

根目录的本文件只规定全局 Guide、Limit、任务治理规则、章节边界和总体验收。各章节具体节点见对应文件：

| 章节 | 主题 | 知识内容目标目录 | 章节任务计划 |
| --- | --- | --- | --- |
| 00 | 知识治理、分类与质量体系 | `docs/`、`knowledge/maps/` | [TaskPlan](docs/TaskPlan/00-知识治理与分类体系/TaskPlan.md) |
| 01 | 机器人类型与应用场景 | `knowledge/robots/` | [TaskPlan](docs/TaskPlan/01-机器人类型与应用场景/TaskPlan.md) |
| 02 | 需求定义与系统工程 | `knowledge/system-engineering/` | [TaskPlan](docs/TaskPlan/02-需求定义与系统工程/TaskPlan.md) |
| 03 | 机械结构、材料与制造 | `knowledge/mechanics/` | [TaskPlan](docs/TaskPlan/03-机械结构材料与制造/TaskPlan.md) |
| 04 | 运动机构、传动与执行器 | `knowledge/actuators/`、`knowledge/mechanics/` | [TaskPlan](docs/TaskPlan/04-运动机构传动与执行器/TaskPlan.md) |
| 05 | 电子电气与能源系统 | `knowledge/electronics/`、`knowledge/power/` | [TaskPlan](docs/TaskPlan/05-电子电气与能源系统/TaskPlan.md) |
| 06 | 传感器与感知硬件 | `knowledge/sensors/` | [TaskPlan](docs/TaskPlan/06-传感器与感知硬件/TaskPlan.md) |
| 07 | 计算平台与硬件外设 | `knowledge/computing/` | [TaskPlan](docs/TaskPlan/07-计算平台与硬件外设/TaskPlan.md) |
| 08 | 操作系统与实时计算 | `knowledge/software/operating-systems/` | [TaskPlan](docs/TaskPlan/08-操作系统与实时计算/TaskPlan.md) |
| 09 | 嵌入式软件、固件与驱动 | `knowledge/embedded/` | [TaskPlan](docs/TaskPlan/09-嵌入式软件固件与驱动/TaskPlan.md) |
| 10 | 通信网络与中间件 | `knowledge/networking/` | [TaskPlan](docs/TaskPlan/10-通信网络与中间件/TaskPlan.md) |
| 11 | 软件架构与工程体系 | `knowledge/software/` | [TaskPlan](docs/TaskPlan/11-软件架构与工程体系/TaskPlan.md) |
| 12 | 数学基础与通用算法 | `knowledge/algorithms/foundations/` | [TaskPlan](docs/TaskPlan/12-数学基础与通用算法/TaskPlan.md) |
| 13 | 感知、定位与地图构建 | `knowledge/perception/`、`knowledge/navigation/` | [TaskPlan](docs/TaskPlan/13-感知定位与地图构建/TaskPlan.md) |
| 14 | 规划、控制与机器人操作 | `knowledge/algorithms/`、`knowledge/manipulation/` | [TaskPlan](docs/TaskPlan/14-规划控制与机器人操作/TaskPlan.md) |
| 15 | 上层应用与人机交互 | `knowledge/applications/` | [TaskPlan](docs/TaskPlan/15-上层应用与人机交互/TaskPlan.md) |
| 16 | 云平台、IoT 与远程运维 | `knowledge/cloud/` | [TaskPlan](docs/TaskPlan/16-云平台物联网与远程运维/TaskPlan.md) |
| 17 | 多机器人调度与车队管理 | `knowledge/fleet-management/` | [TaskPlan](docs/TaskPlan/17-多机器人调度与车队管理/TaskPlan.md) |
| 18 | BOM、供应链与成本工程 | `knowledge/bom/` | [TaskPlan](docs/TaskPlan/18-BOM供应链与成本工程/TaskPlan.md) |
| 19 | 性能指标、测试与验证 | `knowledge/validation/` | [TaskPlan](docs/TaskPlan/19-性能指标测试与验证/TaskPlan.md) |
| 20 | 安全、规范、法规与伦理 | `knowledge/safety/`、`knowledge/standards/` | [TaskPlan](docs/TaskPlan/20-安全规范法规与伦理/TaskPlan.md) |
| 21 | 产业、厂商与市场生态 | `knowledge/ecosystem/` | [TaskPlan](docs/TaskPlan/21-产业生态厂商与市场/TaskPlan.md) |
| 22 | 项目、集成部署与全生命周期 | `knowledge/projects/`、`knowledge/operations/` | [TaskPlan](docs/TaskPlan/22-项目集成部署与全生命周期/TaskPlan.md) |
| 23 | 数据工程、AI 与具身智能 | `knowledge/data-ai/` | [TaskPlan](docs/TaskPlan/23-数据工程AI与具身智能/TaskPlan.md) |
| 24 | 知识管理、检索与工具链 | `src/robot_knowledgebase/`、`docs/` | [TaskPlan](docs/TaskPlan/24-知识管理检索与工具链/TaskPlan.md) |
| 25 | 零基础到量产的端到端产品化路线 | `knowledge/getting-started/`、跨章节 | [TaskPlan](docs/TaskPlan/25-零基础到量产端到端路线/TaskPlan.md) |

章节计划目录索引见 [docs/TaskPlan/README.md](docs/TaskPlan/README.md)。知识内容目录在章节执行过程中按需建立；不能因为计划中出现目录名，就把该目录视为已有知识或已完成交付。

---

## 3. 全局 Guide（所有任务节点必须做）

以下 Guide 对根计划、章节计划、知识文章、数据表、代码示例、测试记录和自动化工具统一生效。

### G-01｜先分类、再写作、持续维护

先检查现有目录与文章，再决定新增、扩展、拆分或迁移。每个知识主题必须有唯一主归属；跨领域内容用链接建立关系，避免多份正文各自演化。新增一级板块必须在目录索引中说明必要性、边界、与相邻板块的区别。

### G-02｜以工程生命周期组织知识

知识不仅解释“是什么”，还要尽可能覆盖：使用场景 → 需求/约束 → 原理 → 分类/选型 → 设计计算 → 实现/接口 → 集成 → 测试验证 → 安全规范 → BOM/成本 → 部署运维 → 故障诊断 → 生命周期与退役。与主题无关的章节可标记“不适用”，并说明原因。

### G-03｜每篇技术文档使用统一结构

技术文档按需采用以下结构；无需为了凑格式编造内容：

1. 标题、摘要、一句话定位、适用范围/不适用范围。
2. 分类与术语、原理、关键组成、工作流程。
3. 架构图/接口图/数据流，必要时给出状态机、时序或拓扑。
4. 关键参数、公式、单位、变量定义、假设和计算示例。
5. 选型方法、设计步骤、工程实践、权衡和典型应用。
6. 接口与兼容性：机械、电气、通信、软件、数据和版本。
7. 测试方法、评价指标、边界条件、失败模式和排障。
8. 安全、法规、网络安全、隐私和环境约束（适用时）。
9. BOM/供应链/厂商/代表型号（适用时）。
10. 代码、仿真、工具、开源项目与许可证（适用时）。
11. 上游板块、下游板块、关联章节。
12. 来源、发布日期/访问日期、适用版本、更新记录和待确认项。

### G-04｜来源优先级与事实核验

事实和参数优先使用：标准/法规原文与官方机构资料、制造商数据手册/硬件手册/SDK、官方软件文档与源代码仓库、同行评审论文/学术教材、正式测试报告。技术博客、论坛、视频和社区回答可用于解释经验或发现问题，但不能单独支撑安全关键结论、法规结论和精确规格。多个来源冲突时并列记录差异，不擅自选取有利数字。

### G-05｜外链必须有来源记录

每个外链记录 URL、标题/资源类型、所属文档、来源机构、访问日期、验证状态、适用版本/地区、备注。验证状态至少区分“已访问可用”“跳转后可用”“需登录/反爬无法确认”“失效”“内容已迁移”“待人工确认”。无法访问时必须如实标注；不得仅凭搜索摘要宣称验证通过。

### G-06｜参数、性能和成本数据必须可比较

参数表统一单位和字段定义，说明测量条件、配置、环境、固件/软件版本、测试方法、容差/误差范围与快照日期。不同厂商的“最大值”“典型值”“额定值”“实验室值”不能直接视为同一口径。没有可靠来源的字段写“未检索到可靠来源”，不估算伪精确值。

### G-07｜BOM 和供应商资料结构化

BOM 至少考虑：位号/层级、物料名称、制造商、型号/订货号、规格、数量、单位、版本/替代关系、关键参数、单价/币种/税费口径、价格快照日、供应商/来源、MOQ、交期、生命周期状态、关键性、风险和备注。未取得的报价必须标“待询价”，不得虚构采购价。成本模型要区分样机、小批量和量产口径。

### G-08｜代码和开源项目合规

优先链接上游仓库和官方示例；代码摘录控制在必要范围并注明来源、版本/commit、许可证、用途和访问日期。只有在许可证明确允许、来源可追溯且满足 NOTICE/版权义务时才纳入可再分发代码。GPL/AGPL、非商业许可、商业 SDK、专利或许可证不明内容必须先做许可证审查；不确定时只链接、不复制。所有原创示例要有运行环境、构建步骤和测试说明。

### G-09｜标准、法规和认证单独管理适用性

每项标准/法规记录：发布机构、正式编号与标题、版本/发布日期/生效日期、适用地区、适用产品/风险、强制或自愿属性、引用关系、官方来源和核验日期。必须区分标准、法规、认证方案、行业指南和企业规范。不能把“参考某标准”写成“符合/通过认证”。

### G-10｜安全关键内容必须显式说明边界

机械、电气、功能安全、医疗、无人机、移动机器人、人机协作和网络安全等内容，要列明危险源、使用前提、适用标准、验证证据和专业审核需求。安全相关计算、保护距离、制动距离、载荷和风险等级必须可追溯到依据和工况。

### G-11｜硬件、软件、算法与应用建立上下游关系

硬件文档说明驱动、OS、中间件和算法如何消费其数据；软件/驱动说明对应硬件、总线、OS、接口和版本；算法说明输入传感器、计算资源、实时约束、输出接口和评价指标；应用说明依赖的能力模块、云端服务和安全约束。每篇文档必须有适用的上游/下游链接。

### G-12｜图示保存可维护源文件

架构图、状态图、时序图、数据流、网络拓扑、机械原理图和电气框图优先保存 Mermaid、SVG 源文件、绘图源文件或可重建描述；图中标注边界、方向、单位、版本和来源。第三方图片须注明许可和来源。

### G-13｜厂商和产品以“代表性覆盖”为原则

按技术路线、应用领域和市场位置选代表性厂商/产品线/型号；为每个代表型号记录依据、数据手册、SDK/驱动、兼容性和快照日期。厂商清单是有选择标准的代表样本，不宣称穷尽所有厂商。

### G-14｜术语统一、中英文对照

新增缩写、术语、单位、接口名和标准术语进入术语表；首次出现给出中英文全称。保持同一概念的命名一致，必要时记录别名和容易混淆的概念。

### G-15｜先审计现有内容，再决定增补方式

对已存在文档做内容盘点、质量分级和差距分析。相同主题优先在原文中增补或拆分，不复制出新的平行正文；历史事实、项目分析和引用内容要保留来源与时间语境。

### G-16｜任务节点必须可验收

每个任务节点必须写清：任务范围、必须完成事项、严格禁止事项、依赖、交付物、验收标准、证据位置和状态。完成状态必须附文件/测试/来源核验/评审等证据；只创建目录或标题不能算完成。

### G-17｜版本和时效透明

软件版本、OS 生命周期、芯片/产品状态、厂商、价格、法规和标准可能变化，均要记录快照日期与适用版本。过期资料应标“历史版本/已停止维护/待更新”，保留历史背景，不静默当作当前建议。

### G-18｜以可检索和可复用为目标

文档使用稳定文件名、清晰标题、统一 front matter、短而明确的主题边界。关键表格尽量结构化；扫描件/OCR 文本必须标注解析质量并抽查。数据集、日志、标注和示例配置要记录 Schema 与单位。

### G-19｜按依赖分阶段推进

先完成分类与治理，再建设系统工程和硬件基础，然后 OS/驱动/通信/软件，继而算法、应用、云和车队，最后完成供应链、验证、安全、案例和 AI 深化。无依赖冲突的章节可并行，但共享文档的修改必须协调。

### G-20｜保留审计轨迹

根计划和各章节计划使用稳定任务 ID。任务状态更新、范围变更、节点追加、来源更正和结构迁移都要记录日期、原因、操作者/来源及证据。修订不得抹去历史结论。

### G-21｜面向零基础学习者设计内容

每个关键知识主题必须让非行业读者能找到入口：说明先修知识、需要掌握的术语、学习目标、概念解释、分步讲解、图示/例题、可动手练习、检查题/验收标准和下一步链接。先解释“为什么需要”和“解决什么问题”，再进入公式、代码和专业术语。对于需要专业数学/编程/工具能力的内容，提供前置学习路径和能力门槛，不得假装零基础读者可以跳过先修知识。

### G-22｜从需求到量产必须有阶段门

全流程主线必须覆盖产品机会/需求、可行性、概念方案、系统需求与架构、详细设计、工程样机、EVT、DVT、PVT/试生产、量产准备、量产爬坡、客户交付、售后维护和退役。各阶段明确输入、设计/验证活动、交付物、评审问题、准入/退出标准、责任角色和风险。不同机器人类型允许阶段名称不同，但必须建立等效阶段映射；不能把“能运行的样机”视为“可量产产品”。

### G-23｜工程知识必须配套实际成果物

对适用的主题，知识必须连接到真实工程成果物和模板，例如需求规格书、系统框图、CAD/图纸、材料清单、原理图/PCB、接口控制文件、固件/驱动、软件架构、算法参数、风险分析、DFMEA/PFMEA、BOM、工艺流程、作业指导书、测试规范、控制计划、检验记录、认证技术文件、安装调试记录和售后手册。每个模板说明填写方法、版本关系、审核人和使用阶段。

### G-24｜用代表性端到端项目验证知识链

至少选取一个具备可验证资料的参考机器人项目贯通全流程，并建立与其他类型的差异分支。参考项目应从需求、方案、设计、BOM、实现、测试走到生产与交付；每个阶段回链相关知识章节。案例必须区分教学示例、仿真结果、实验室样机、工程验证、试生产和真实量产证据，不得把教学样例伪装成商业量产案例。

### G-25｜外部工程项目与知识资产分离治理

外部工程仓库默认保持独立维护；知识库优先吸收独立撰写的原理、架构、接口、测试方法、适用边界和可追溯证据摘要，不默认复制或整体合并源码。每个外部项目须在 `docs/audits/External-Project-Registry.md` 登记仓库 URL、精确版本、关联章节、许可证、依赖、验证等级、阻塞、允许/禁止动作和下一步。源码引入必须逐文件完成许可证/NOTICE/专利、依赖/SBOM、目标平台兼容、测试和维护策略审查，并取得用户对具体范围和分支的明确授权；测试通过、submodule 或链接均不能替代准入审查。治理规范见 `docs/engineering/External-Project-Integration-Policy.md`，登记模板见 `docs/templates/External-Project-Intake.md`。

---

## 4. 全局 Limit（所有任务节点严格禁止）

1. **禁止声称一次性穷尽行业全部知识。** 不得将覆盖目录、文章数量或字数包装成“行业知识全部完成”；必须持续保留缺口清单。
2. **禁止编造事实、参数、公式、链接、厂商、型号、法规版本、报价、测试结果和引用。** 查不到就写明未知、待验证或暂无可靠来源。
3. **禁止混淆概念和数据口径。** 不得将理论值、厂商典型值、额定值、实验值或第三方评测值不加说明地横向比较。
4. **禁止伪造验证和来源状态。** 没访问过的 URL 不得标记已验证；没有跑过的代码/测试不得宣称通过。
5. **禁止把“参考标准”写成“符合标准/取得认证”。** 不得替代认证机构、专业工程师或法律顾问作结论。
6. **禁止发布未经审查的安全关键操作指令。** 涉及人身、机械、电气、化学、电池、高压、医疗、无人机或危险环境的程序，必须明确风险与专业审核要求。
7. **禁止复制不允许再分发的资料和代码。** 不得整篇复制付费文章、标准全文、商业手册、受限 SDK、GPL/AGPL 等受限代码；遵守版权和许可证。
8. **禁止提交秘密或敏感数据。** 包括密钥、Token、密码、客户隐私、个人信息、未脱敏日志、内部网络信息和未获授权的项目资料。
9. **禁止把大体积二进制资料直接塞入知识库。** 不提交安装包、固件镜像、完整数据集、原始录音/视频、商业 PDF 手册；只登记来源和受控存储位置。
10. **禁止无边界爬取、批量镜像或违反站点条款的采集。** 采集方式必须合法、合规、可追溯，遵守访问频率和许可。
11. **禁止无意义重复。** 不得为同一概念创建多个没有明确边界的主文档；跨章重复内容应摘要+链接。
12. **禁止随意改变目录、任务 ID 和历史状态。** 不删除已登记节点、不复用 ID、不静默改写已验收结论；结构变更必须追加迁移记录。
13. **禁止把待办、目录骨架、占位符或未经审计的旧文档标成完成。** 已有内容只能标“已有基础，待审计”，通过本计划验收后才可转为完成。
14. **禁止自行给章节计划另设、弱化或覆盖全局 Guide/Limit。** 若某个特殊章节确实无法采用全局约束，必须先向用户说明冲突、影响和建议例外，取得确认后才能在其子计划中增加补充规则；当前版本没有批准任何例外。
15. **禁止将营销材料、供应商宣传或社区传闻当作独立事实。** 必须与技术数据、实测证据或权威来源区分。
16. **禁止无日期使用时效性信息。** 价格、法规、标准、软件支持状态、芯片供货和产品生命周期等必须标明快照日期。
17. **禁止未经测试就宣称性能。** 不得把单次演示、仿真结果或实验室最佳值推广为量产可靠性和真实运行能力。
18. **禁止擅自修改真实项目源码或生产环境。** 案例研究默认只读；需要代码变更必须获得明确授权并在独立分支进行。
19. **禁止将个人经验写成普遍规律。** 经验结论必须注明机器人平台、工况、样本范围和限制。
20. **禁止在章节子计划中复制一套独立 Guide/Limit。** 子计划仅引用本文件；章节任务的“必做/禁止”只能细化任务边界，不得形成与全局冲突的新制度。
21. **禁止承诺“只读知识即可无条件造出并量产任何机器人”。** 不得掩盖真实项目所需的资金、人员、工具、工厂、实验室、供应链、专业安全审核和法定认证；必须标明知识指导与现实资源/专业责任的边界。

---

## 5. 任务节点、状态与变更治理

### 5.1 节点状态

- **未开始**：尚未启动。
- **进行中**：正在执行，有明确负责人/执行记录和开始日期。
- **阻塞**：缺少外部输入、权限、资料或依赖；必须写解除条件。
- **待验收**：内容已提交，尚未完成来源、技术、链接或测试复核。
- **已完成**：所有验收条件通过并附证据。
- **暂缓**：有明确原因、风险和重启条件。
- **不适用**：经说明确认与该章范围无关，不得用于规避未完成任务。

章节计划可以进一步记录优先级 P0/P1/P2，但不能改变上述含义。

### 5.2 任务节点最低字段

每个节点必须具备：

| 字段 | 要求 |
| --- | --- |
| ID | 全仓库唯一，建立后不复用 |
| 任务范围 | 说明主题边界和不包含的内容 |
| 必做 | 该节点必须产出的具体内容/动作 |
| 禁止 | 本节点特有的风险边界；同时继承全部全局 Limit |
| 依赖 | 先决章节/节点；无依赖写“无” |
| 交付物 | 文件、表格、图、代码、数据 Schema 或测试报告 |
| 验收标准 | 可客观核验的条件 |
| 证据 | 文件路径、来源、测试命令/结果、评审记录 |
| 状态 | 按 5.1 状态机维护 |

### 5.3 ID 与计划变更

1. ID 格式为章节号-两位序号，例如 `06-03`；一个节点只代表一个可验收结果。
2. 已发布的节点 ID 不删除、不复用、不随意改序；拆分、扩展、纠正时追加新节点并注明关联。
3. 计划发生实质变更时，在根计划“变更日志”与对应章节计划追加记录。原节点保留，状态和证据不被抹去。
4. 若需更改章节分类或合并目录，先更新迁移映射，再迁移文件并执行双链/引用检查。
5. 章节可并行，但同一文件/数据源不得由多个任务未经协调地同时改写。

### 5.4 验收规则

- 文章：内容完整、来源可追溯、无明显重复、上游/下游关系建立、待确认点显式标注。
- 参数/BOM：单位、型号、适用版本、价格日期、来源和口径完整。
- 代码：许可证、构建环境、运行方式、测试结果和来源完整。
- 标准/法规：官方来源、适用范围、版本/日期、强制性和状态已核对。
- 流程/架构：边界、角色、接口、数据流、异常路径和安全约束齐备。
- 章节：章节索引、术语、链接、来源台账、缺口清单和验收记录齐备。

---

## 6. 建设阶段与依赖顺序

| 阶段 | 重点 | 章节 |
| --- | --- | --- |
| Phase 0：治理与盘点 | 建立分类、Schema、来源与质量规则；审计现有资料 | 00 |
| Phase 1：机器人与系统基线 | 类型、需求、机械、运动、电子电气、传感器、计算平台 | 01–07 |
| Phase 2：底层软件栈 | OS、固件驱动、通信、中间件、软件架构 | 08–11 |
| Phase 3：算法链路 | 数学基础、感知定位建图、规划控制操作 | 12–14 |
| Phase 4：产品运行系统 | 应用交互、云端管理、多机器人车队 | 15–17 |
| Phase 5：工程化与合规 | BOM、性能测试、安全法规、产业生态 | 18–21 |
| Phase 6：系统交付和智能化 | 项目全生命周期、数据与具身智能 | 22–23 |
| Phase 7：检索和持续演进 | 文档治理、索引、Embedding、RAG、质量自动化 | 24 |
| Phase 8：零基础到量产端到端贯通 | 先修课程、参考项目、全阶段交付物与产品化阶段门 | 25（横向贯穿 00–24） |

主要依赖关系：
- 02 需求与系统工程为后续设计与验收提供需求基线。
- 03–07 提供机械、电气、传感和计算基础；04/05/06/07 之间必须建立接口关系。
- 08–11 建立 OS、固件、总线、中间件和软件运行底座。
- 12 为 13–14 提供数学和算法基础；13 的传感/定位输出应与 14 的规划控制接口闭合。
- 15–17 依赖 11 的软件架构、13–14 的机器人能力，并与 20 的安全约束关联。
- 18–21 横向支撑所有产品章节；22 汇总设计、制造、交付、运维经验。
- 24 的检索系统以各章节稳定的元数据、术语和质量控制为前提，但其治理规范从 Phase 0 即开始执行。

---

## 7. 项目级最终验收

1. 00–25 每个章节计划均有明确范围、节点、依赖、交付物和验收标准。
2. 每个章节都有知识地图/索引、核心知识文章、术语、来源记录、上下游关系和未覆盖项。
3. 机器人全生命周期的需求—设计—实现—集成—测试—交付—运维—退役链路可追踪。
4. 关键技术与接口链路可追踪：部件 → 驱动 → OS → 中间件 → 算法 → 应用 → 云端/调度。
5. BOM、参数、性能、厂商、标准法规均有来源、口径和日期。
6. 代码和数据符合版权、隐私、安全与许可证约束。
7. 自动化检查覆盖 Markdown 格式、元数据、链接、引用、目录、重复文件、术语和 RAG 数据质量。
8. 所有“已完成”节点均有证据；阻塞与缺口公开保留；不以文档数量作为唯一完成标准。
9. 完成一次跨章节系统级审查，验证不同章节之间不存在关键接口、术语、单位或版本口径冲突。
10. 非机器人行业的新手能按学习入口理解先修要求，完成基础知识检查后找到下一步学习和实操任务。
11. 至少有一条经审计的参考产品路径从产品需求贯通到量产准备、试产、放行、交付和售后；每个阶段的成果物、阶段门和责任角色明确。
12. 对量产流程中的工艺能力、供应链、质量控制、追溯、变更、可靠性、法规认证和售后要求有独立知识与证据路径。

---

## 8. 根计划变更日志（只追加）

| 日期 | 版本 | 变更 | 依据 |
| --- | --- | --- | --- |
| 2026-11-16 | v12.74 | 更新Stäubli terminate wrapper gate进度：Actions #150/#151/#152均已通过ROS Jazzy setup与workspace tooling，进入stock rclcpp overlay build；运行job日志暂不可读取，MoveIt构建/测试和terminate动态结果均未定。静态源码结论与CI-only public wrapper gate继续有效；00-01最高优先级、MotionControlAlgorithms DEFERRED保持不变。 | Actions #43880623915/#43880751582/#43880873865最新job状态；当日历史v83 |
| 2026-11-16 | v12.73 | 基于MoveIt Jazzy固定commit f11204b8a9b98e4ba28e564721d24a7077f5f969静态确认MoveItCpp terminate wrapper受isActive()/atomic bool门控，新增CI-only真实MoveItCpp wrapper terminate回归门禁；slow请求在active_=false时暂停，调用公开wrapper并检查底层PlanningPipeline::terminate()入口marker。工作流提交c58d1c8、0b218b9、ee8d1a8；Actions #150/#151/#152已触发但仍处ROS Jazzy setup阶段，动态结果未定。 | 固定MoveIt source commit f11204b8a9b98e4ba28e564721d24a7077f5f969；Actions #43880623915/#43880751582/#43880873865；workflow branch commit ee8d1a819d6e269b921b729039905c8d53648db4；当日历史v82 |
| 2026-11-16 | v12.72 | 完成Stäubli same-OMPL PlanService/SequenceService并发门禁动态验证：Run #148测试本体10/10轮通过但因旧验收器期待7项而失败；Run #149修正为8项后完整CI 10/10通过。确认每轮同一pipeline并发重叠时fast退出后active_=false而仍有slow请求in-flight；两服务成功、GDB clean exit、无SIGSEGV。新增terminate漏取消验证待办；00-01优先级和MotionControlAlgorithms DEFERRED不变。 | Actions #43868030841/#43873768855；workflow commits b0bad196b7328c19bf24a2cabc58c8781f2c279e、031478a961bb62ded1231e5288055ae4b8cf7961；当日历史v81 |
| 2026-11-16 | v12.71 | 修正Stäubli同OMPL pipeline并发mock测试新增unittest后的CI验收计数：pre-shutdown suite要求3项，colcon test-result汇总要求8项；记录修正提交和Actions动态结果待核验状态。 | staubli_driver_ros2_from_org workflow commit 031478a961bb62ded1231e5288055ae4b8cf7961；当日历史v80 |
| 2026-11-16 | v12.70 | 更新Stäubli Run #147最终状态：stock rclcpp无插桩mock teardown 10/10 PASS、GDB clean exit和7项测试均通过；记录same-OMPL PlanService/SequenceService active_并发探针已在既有实验分支提交，动态Actions结果待核验；保持00-01最高优先级及MotionControlAlgorithms DEFERRED。 | Run #147 Actions 43862172486；staubli_driver_ros2_from_org commit b0bad196b7328c19bf24a2cabc58c8781f2c279e；当日历史v79与第21章21-01状态补充 |
| 2026-11-16 | v12.61 | 更新Run #139最新进度：rosdep重试/工具安装成功，stock rclcpp overlay构建、MoveIt补丁和依赖安装完成，第8步patched move_group构建中，第9/10步尚未执行。 | Run #139 Actions 43840240632 job 133206807886 steps 1–8 |
| 2026-11-16 | v12.60 | 核对MoveIt Jazzy PSM构造函数第120行，确认实际调用TransformListener(BufferCore&)简化重载并创建optional_default_node_，使TF listener内部Node的单一TypeDescription service成为有实际构造路径支持的强静态解释；运行时地址和服务名仍待Run #139确认。 | MoveIt Jazzy planning_scene_monitor.cpp；geometry2 Jazzy TransformListener；rclcpp Jazzy NodeTypeDescriptions/Node destructor |
| 2026-11-16 | v12.59 | 纠正根计划残留的Run #135/136将故障Node确定归属pnode_的旧表述；故障Node现记为PSM析构链中的Node身份待定，pnode_七项服务路径保留为静态候选，单元素vector优先核验TF listener内部Node TypeDescription路径。 | Run #136/#137 GDB栈；ROS 2 Jazzy PSM/TransformListener/Node/NodeTypeDescriptions源码 |
| 2026-11-16 | v12.58 | 记录Run #138未进入构建/测试、仅因rosdep base.yaml连接重置而失败；在既有实验分支为rosdep update增加5次有限重试并保留最终fail-closed，触发Run #139。 | Run #138 Actions日志；Run #139 Actions 43840240632；workflow commit 5332c79ead53d811bc7b5820d10e269eeaddff66 |
| 2026-11-16 | v12.57 | 核对ROS 2 Jazzy Node::~Node()显式接口reset与成员逆序析构，确认node_type_descriptions_未在函数体reset且先于node_base_释放；结合TF TransformListener内部Node的默认type-description service和PSM成员销毁顺序，建立可解释单元素weak_ptr vector的强静态生命周期候选；Run #138运行时地址/服务名比对仍为待执行。 | ROS 2 Jazzy rclcpp node.cpp/node.hpp/node_type_descriptions.cpp；geometry2 Jazzy TransformListener；MoveIt Jazzy PlanningSceneMonitor成员布局 |
| 2026-11-16 | v12.56 | 记录Run #137 10/10 teardown SIGSEGV及GDB第22行非法解引用造成诊断中止；撤回将故障Node直接归属pnode_的结论；补充TF TransformListener内部Node的NodeTypeDescriptions默认get_type_description单元素候选；记录Run #138安全GDB取证、service创建归属日志与Node指针关联诊断已提交并启动。 | Run #137 Actions日志；ROS 2 Jazzy NodeTypeDescriptions/TransformListener/NodeServices/CallbackGroup源码；Run #138 Actions 43839729557 |
| 2026-11-16 | v12.55 | 补充Run #136 GDB vector析构区间仅1个weak_ptr、与源码预期7项冲突的证据；更正Run #137进度至第8步MoveIt构建中，并要求通过实际service_ptrs_长度、节点/group地址及逐项control block/vptr输出核实身份，不把静态预期当作运行时事实。 | Run #136原始GDB栈；ROS 2 Jazzy NodeOptions/NodeParameters/ParameterService/CallbackGroup源码；Run #137 Actions状态；第21章Stäubli专项补充 |
| 2026-11-16 | v12.54 | 登记Run #136真实10/10 pnode_弱引用析构SIGSEGV、fault vptr未映射而关键依赖DSO仍映射的证据，修正test-result汇总解析错误，并启动Run #137逐项读取service_ptrs_ control block/vtable与DSO unload事件；全局00-01优先级不变。 | Stäubli Actions Run #136原始GDB/job logs、workflow commit 4aa4539a9adfd5efe0adea52753ba1847abf8a53；第21章21-01补充 |
| 2026-11-16 | v12.53 | 修正每日归档索引，登记当日历史v57–v62与pnode_ ServiceBase弱引用候选、Run #136故障vptr映射和Run #137逐项控制块/DSO诊断。 | `TaskPlan_History/TaskPlan-2026-11-16.md` v57–v62；第21章21-01状态补充 |
| 2026-11-16 | v12.49 | 将Run #135 pnode_ CallbackGroup中的weak_ptr<ServiceBase>候选收窄为PSM get_scene_service_注册的GetPlanningScene service；确认NodeServices默认使用pnode_ default CallbackGroup并追加weak owner，Run #136继续取证实际控制块/DSO归属。 | MoveGroupGetPlanningSceneService、PlanningSceneMonitor、rclcpp Node/NodeServices/CallbackGroup Jazzy源码；Run #135原始GDB栈 |
| 2026-11-16 | v12.50 | 从Run #135每轮运行日志确认`MoveGroupGetPlanningSceneService`实际加载，强化PSM get_scene_service_作为pnode_ CallbackGroup expired weak ServiceBase候选的运行时路径证据；Run #136 GDB映射仍待。 | Run #135原始日志capability loading marker；MoveIt/rclcpp Jazzy源码；Run #136进行中 |
| 2026-11-16 | v12.51 | 扩展pnode_ CallbackGroup ServiceBase候选：ROS 2 NodeOptions默认start_parameter_services=true，NodeParameters构造6个ParameterService服务，PSM另创建GetPlanningScene service；7个服务均通过NodeServices默认callback group路径留weak refs。具体崩溃entry未知，Run #136计划读取service_ptrs_数量/地址和DSO映射。 | ROS 2 Jazzy NodeOptions/NodeParameters/ParameterService/NodeServices/CallbackGroup源码；MoveIt PSM源码；Run #135 GDB栈 |


| 2026-11-16 | v12.48 | 根据Run #135 GDB堆栈将PSM teardown崩溃定位到隐式pnode_ Node/NodeBase/CallbackGroup析构中的weak_ptr<ServiceBase> control-block _M_destroy；新增Run #136 GDB共享库/映射取证。尚未证明control block属于已卸载DSO。 | Run #135原始10轮日志/栈、MoveIt Jazzy PSM源码、ROS 2 Jazzy Node/NodeBase/CallbackGroup源码；Run #136 Actions在执行 |
| 2026-11-16 | v12.47 | 补充PSM持有Node至NodeBase/CallbackGroup最终销毁的静态对象链，明确weak ServiceBase entries可能在capability DSO卸载后释放的待证机制；Run #135仍进行中。 | MoveIt Jazzy PSM/MoveGroupContext/MoveGroupExe源码；ROS 2 Jazzy Node/NodeBase/CallbackGroup源码；尚无control-block DSO地址映射 |
| 2026-11-16 | v12.46 | 更新 Stäubli A-PSM-retained 消融结果：Run #132 无插桩 10/10 PASS，Run #134 10/10 teardown SIGSEGV；纠正 colcon test-result verbose 造成的执行次数重复统计，并启动 Run #135 PSM 析构边界诊断。根计划最高优先级 00-01 不变。 | Stäubli Actions Run #132/#134/#135、原始 job log、workflow commit `ac87221956b3d946d93fb1732fb12ea4e59e8094`；mock/CI-only 证据 |
| 2026-11-15 | v12.22 | 合并PR #18–#22的治理与审计成果，并补齐第21章21-02医疗/康复/腔镜机器人注册证与标准的分层复核：天智航天玑1.0延续状态待官方个案材料，迈步新旧证与型号映射未闭环，傅利叶按长沙/广州/上海注册主体拆分，翔宇产品证据按型号区分，安杰莱急停不合格事件列供应商CAPA审查且不外推至其他设备；新增腔镜手术机器人注册动态与适用标准范围。所有监管/临床/采购结论维持证据边界，不将公开线索写成监管级证照确认 | PR #19、NMPA/地方药监目录与送达记录、企业官方资料及各专项审查报告；详细历史见 TaskPlan_History/TaskPlan-2026-11-15.md |
| 2026-11-15 | v12.23 | 第21章21-02补齐柏惠维康重庆迁址专项：区分媒体/企业“已获三类生产许可、迁移8张注册证”主张、重庆药监局2025-08及2026年许可公告附件、涪陵经营许可申请公示和产品注册证变更；目前仅识别7个候选注册证，生产许可证原件、范围/地址/有效期、完整8证清单及逐证变更附件未取得。补充重庆药监局生产许可（备案）查询入口但未完成企业个案查询；明确产品注册、生产许可和经营许可不可互相替代。新增天智航、柏惠维康、迈步机器人专项档案及对应来源记录；所有结论维持公开证据边界。 | PR #20专项报告、重庆药监局公告/查询目录、NMPA送达记录、企业官网及第三方动态信息分级核验 |
| 2026-11-15 | v12.24 | 00-01新增IMU P0公开来源/模型数学定向审查：核验Kalibr白噪声与Brownian bias单位、抗混叠抽取前提、Allan overlapping/读图口径、二维Qd与OU公式；对BMI088产品页和Rev.1.9数据手册按轴/通道对照，对ADIS16470 ARW、rate noise density、bias stability与DEC_RATE采样语义分层记录。目标IMU配置、原始数据、Allan/PSD、ESKF与实机验证仍缺，IMU保持claim-level pending。 | 专项审查报告、官方产品页/数据手册、NXP AN5087、ETH Zürich Kalibr Wiki；来源台账#1808–#1813 |
| 2026-11-15 | v12.25 | 00-01新增LiDAR P0公开来源/接口/安全边界定向审查：按ROS 2 Jazzy官方消息定义明确LaserScan首束时间戳、角度坐标、time_increment/scan_time分工及PointCloud2二进制字段/点内时间边界；核对Livox Mid-360量程反射率、精度脚注/近距离限制；以SICK TiM1xx与nanoScan3 I/O对比普通数字检测输出和OSSD安全输出，说明nanoScan3以太网导航测量数据本身非安全数据；核验IEC 60825-1与IEC 61496-3范围/生命周期。目标雷达配置、原始点云、deskew和整机安全链仍未验证。 | ROS 2 Jazzy消息定义、Livox/SICK官方资料、IEC官方出版物；来源台账#1814–#1820 |
| 2026-11-15 | v11.94 | 完成 CANopen Bus-Off/restart 与 SDO/NMT 会话恢复专项复核：SocketCAN Restarted→Online 不等于应用会话恢复；virtual node bus recovery 未清分段 SDO/NMT/CiA-402 状态，现有测试缺少中断会话与运行态恢复组合。新增知识页 §26、更新 EXT-001、第14章记录和每日归档。仅修改知识库文档，未修改上游源码/测试/CI | MotionControlAlgorithms main `c11091b` 的 socketcan_transport.hpp、canopen.hpp、CANopen tests 与 P12_SOCKETCAN 文档静态核对 |
| 2026-11-14 | v11.93 | 完成 EtherCAT CSP rearm latch 状态变化专项复核：确认 staging 对 slave/scan 异常拒绝新命令，但 latch 置位条件缺少 online/operational/AL=OP 与 scan 完整性，可能不 inhibit stale 0x6040；新增知识页 §25、更新 EXT-001、第14章记录和每日归档。仅修改知识库文档，未修改上游源码/测试/CI | MotionControlAlgorithms main `c11091b` 的 receive_process、CSP staging/rearm、fake IgH API 与现有回归测试静态对照 |
| 2026-11-14 | v11.92 | 完成 EtherCAT IgH adapter Distributed Clocks 专项复核：确认通用 DC 元数据/状态机未连接到 adapter 的配置、IgH 周期同步 API、runtime health 或 CSP interlock；准确标记当前 adapter 不支持/未暴露 DC，新增知识页 §24、更新 EXT-001、第14章记录与每日归档。仅修改知识库文档，未修改上游源码/CI | MotionControlAlgorithms main `c11091b` 的 IgH adapter/header、通用 EtherCAT domain/state model、fake IgH API 与 PDO mapping 测试静态核对 |
| 2026-11-14 | v11.91 | 完成 RelativeDegreeTwoCbfFilter 标准二阶 exponential CBF 级联公式复核；确认实现漏掉 alpha2*h_dot，并以非零导数解析反例证明现有零导数测试会漏检；知识页新增 §23，更新外部项目登记、第14章任务记录和每日归档。仅修改知识库工作分支，未修改上游算法源码 | MotionControlAlgorithms main `c11091b` 的 relative_degree_two_cbf_filter.hpp、multi_input_cbf_filter.hpp 与测试；级联公式手工推导及解析数值反例 |
| 2026-11-14 | v11.90 | 完成 MotionControlAlgorithms EtherCAT/CANopen 驱动执行链路静态审查，覆盖 CiA 402、PDO/MDP、IgH adapter、SocketCAN、health/mailbox 和虚拟设备；新增 §22 审查结论。识别 DC 同步、CSP rearm、CANopen bus-off 会话恢复和 provenance 绑定等 P0/P1 项；未连接真实硬件、未导入源码 | 上游 main `c11091b`、CI Run #2827、17个测试源文件/235个 TEST case；Fake IgH/vcan 证据不等同物理 HIL |
| 2026-11-14 | v11.89 | 完成 MotionControlAlgorithms legged 全身控制与接触/QP 模块静态审查，覆盖状态/接触/步态/质心、ZMP、locomotion MPC、QP/task hierarchy、接触 wrench 和 joint impedance；新增 §21 审查结论和 P0/P1/P2 清单。确认当前仍是基础组件，不是完整 contact-constrained floating-base WBC；未导入源码 | 上游 main `c11091b`、CI Run #2827、15个测试源文件/75个 TEST case；遵守 G-25 与源码导入授权边界 |
| 2026-11-14 | v11.88 | 完成 MotionControlAlgorithms MPC/QP/CBF 与鲁棒控制模块静态审查，覆盖 NonlinearMpc、ConstrainedQp、GenericMpc、连续/离散/鲁棒/多输入/相对阶二 CBF、slew-rate、ReferenceGovernor、RobustAdaptive、SlidingMode；新增 §20 审查结论和 P0/P1/P2 清单。发现 RelativeDegreeTwoCbfFilter 的 h_dot 系数需数学复核；未导入源码 | 上游 main `c11091b`、CI Run #2827、12个测试源文件/95个 TEST case；遵守 G-25 与源码导入授权边界 |
| 2026-11-14 | v11.87 | 完成 MotionControlAlgorithms 移动底盘与机械臂控制模块静态审查，覆盖差速/Mecanum、轮速分配、Pure Pursuit/Stanley/LQR/MPC、Cartesian PD/impedance/admittance 和 null-space；新增 §19 审查结论与 P0/P1/P2 改进清单，更新外部项目登记表、第14章和每日归档。识别 Cartesian 姿态 frame 和 Pure Pursuit lookahead 优先复核项；未导入源码 | 上游 main `c11091b`、CI Run #2827、11个测试源文件/67个 TEST case；遵守 G-25 与源码导入授权边界 |
| 2026-11-14 | v11.86 | 完成 MotionControlAlgorithms 状态估计/里程计模块静态审查，覆盖 StateObserver、DiscreteKalman/LQG、DisturbanceObserver 与 PlanarOdometry；新增 §18 审查结论和 P0/P1/P2 改进清单，更新外部项目登记表、第14章和每日归档。确认当前没有完整 IMU/编码器融合定位栈；未导入源码 | 上游 main `c11091b`、CI Run #2827、4个测试源文件/21个 TEST case；遵守 G-25 与源码导入授权边界 |
| 2026-11-14 | v11.85 | 完成 MotionControlAlgorithms 运动学与动力学模块静态审查，覆盖 DH/URDF、FK、数值/DLS IK、Jacobian、奇异性指标、质量矩阵/Coriolis/重力、重力补偿和 computed torque；新增 §17 审查结论与 P0/P1/P2 改进清单，更新外部项目登记表、第14章和每日归档。未导入源码 | 上游 main `c11091b`、CI Run #2827、9个测试源文件/38个 TEST case；遵守 G-25 与源码导入授权边界 |
| 2026-11-14 | v11.84 | 完成 MotionControlAlgorithms 轨迹生成/时间参数化模块静态审查，覆盖 scalar、polynomial、S-curve 与 CSP bridge；新增 §16 审查结论和 P0/P1/P2 改进清单，更新外部项目登记表、第14章和每日归档。确认当前实现是基础单轴轨迹组件，不是完整多轴同步/路径时间参数化系统；未导入源码 | 上游源码基线 `472e0ee`、许可更新 main `c11091b`、CI Run #2827 和对应测试文件；遵守 G-25 与源码导入授权边界 |
| 2026-11-14 | v11.83 | MotionControlAlgorithms 经用户确认原创后，在上游 main 添加 Apache-2.0 LICENSE、NOTICE 并更新 README；更新外部项目登记表、第14章 14-EXT-01、运动控制知识页和每日归档。许可证未知阻塞解除，但逐文件来源/第三方依赖许可/SBOM及兼容性审查仍待完成；未导入源码 | 用户明确授权为原创项目添加许可证；Apache 官方文本与上游 main 提交 `c11091b` 为依据；遵守 G-25 的逐文件准入与单独授权要求 |
| 2026-11-14 | v11.82 | 新增 G-25 外部工程项目与知识资产分离治理；建立外部工程项目集成规范、登记表和档案模板；登记 MotionControlAlgorithms 与 staubli_driver_ros2_from_org，明确知识化优先、源码准入门和独立仓库策略；第14章 MotionControlAlgorithms 待办更新为基本测试证据复核阶段 | 用户确认 robot_knowledgebasement 为目标项目，并授权按“外部项目保持独立、知识与证据纳入知识库”的建议继续推进；依据 G-08、G-11、G-15、G-20 与 G-25 |
| 2026-11-03 | v1.0 | 建立机器人行业全域知识体系建设总计划；拆分 00–24 共 25 个章节计划；所有章节统一继承本文件 Guide/Limit | 用户明确项目目标、知识范围和 TaskPlan 分层要求 |
| 2026-11-03 | v1.1 | 将零基础学习、端到端阶段门、工程成果物和参考项目要求纳入使命与全局 Guide；新增 25 章跨章节产品化主线 | 用户明确知识库最终验收目标 |
| 2026-11-03 | v1.2 | 逐章复核 00–25 子计划节点状态；将有明确成果但未满足整节点验收条件的节点标记为进行中，未实际启动者保持未开始；设置当前主节点 00-01，并继续推进桌面机械臂参考项目的方案比较、负载预算与初始风险登记 | 仓库 TaskPlan 与项目/审计成果交叉核对；不把局部修订视为整节点完成 |
| 2026-11-03 | v1.3 | 对四份 P1 产业/市场/人形机器人资产开展官方来源定向主张复核，更新知识页与链接台账 #175–#185；第 21 章相关节点标记为进行中，根计划当前主节点继续保持 00-01 | IFR World Robotics 2026 与厂商官方资料；生产/下线/交付/现场运行口径严格区分 |
| 2026-11-03 | v1.4 | 对 ROS 2 QoS、实时性、组件组合、进程内通信、Zenoh RMW、Fast DDS、REP 2000 平台支持及 Noetic EOL 开展 P1 定向复核，修订知识页并新增来源台账 #186–#194；00-01 继续进行中 | ROS 2 官方文档、RMW 仓库、REP 2000 与 ROS PMC 公告；不把局部主张复核视为全文验收或目标系统测试 |
| 2026-11-03 | v1.5 | 第 25 章新增 25-13 成品教学臂与模块化关节产品基准调研；建立 SO-101（补充 leader/follower BOM 与接口配置核验）、myCobot 280、UFACTORY Lite 6、CubeMars AK60-6 V3.0、ROBOTIS XH430-W350-T 官方公开资料对照，并在参考项目中新增调研报告；25-04/25-12/25-13 保持进行中 | 厂商官方产品页与官方文档；仅完成公开资料初筛，准确 SKU、动态曲线、报价、生命周期和项目任务输入仍待核验 |
| 2026-11-03 | v1.6 | 第 25 章新增 25-14 官方手册与接口深度核验；建立 CubeMars AK60-6 V3.0、ROBOTIS XH430-W350-T、UFACTORY Lite 6、myCobot 280 M5 的手册/接口/控制表核验记录；修复参考项目 README 导航分隔符；25-04/25-12/25-13/25-14 保持进行中 | 厂商官方手册目录、e-Manual、产品规格页；仅核验公开资料入口与部分字段，原始文件归档、实机测试、热/动态曲线、供应商书面确认待完成 |
| 2026-11-03 | v1.7 | 25-14 补充 SO-101 leader/follower 配置深度核验，明确两臂 12 个 STS3215 的齿比 BOM 差异、7.4 V/12 V 供电边界、MotorBus/ID/1 Mbps 配置和 LeRobot 标定流程；链接台账新增 #205–#207；25-14 继续进行中 | Hugging Face LeRobot 官方文档与 TheRobotStudio SO-ARM100/SO-101 官方仓库；未取得完整舵机/控制板数据手册，未做实机总线、热、负载与安全验证 |

---
| 2026-11-04 | v6.9 | 00-01/21-03 继续补充 PLC 与 ROS 2 协议桥：新增 b-robotized/ros2_opc_ua（Jazzy+、OPC UA Client 型 ros2_control SystemInterface、示例能力有限）、Capacites/ros2_modbus（Modbus TCP I/O topic、未声明发行版矩阵）及 Mariunil/ros2-opcua（实验性 PubSub hybrid nodes）；兼容矩阵将“README 版本门槛”“源码构建入口”“发行版包发布证据”分开，并增加 PLC tag/寄存器/NodeId 映射、权限、质量位/时间戳、超时/重连、幂等性、故障注入和抓包/rosbag 验收门。链接台账新增 #622–#624，更新开源索引、兼容矩阵、资产 CSV 和 00/21 子计划。根计划当前主章节仍为00、主任务仍为00-01；本轮仅静态仓库核验，未连接 PLC、未验证 OPC UA/Modbus 互操作、证书安全、网络分区恢复、硬实时或现场安全功能，不生成完整 SBOM/法律意见，不提前验收。 | b-robotized/ros2_opc_ua、Capacites/ros2_modbus、Mariunil/ros2-opcua 上游 README；静态快照截至 2026-11-04，项目维护、发行版构建和 PLC 型号互操作仍待验证 |
| 2026-11-04 | v6.10 | 00-01/21-03 补充 PLC 厂商生态与 ROS 2 接口：Beckhoff ADS ROS 2 Hardware Interface（ROS Index Jazzy 1.0.0、RELEASED/MAINTAINED、ros2_control；底层 ADS MIT 库支持 Linux 客户端，但 driver 仅有 Jazzy 包级证据）；Siemens SIMATIC/Industrial Edge OPC UA/S7 connector（厂商数据接入，不是 ROS driver；匿名无安全配置仅用于测试）；CODESYS OPC UA Server/Client/PubSub 与 EtherCAT/Modbus/CANopen 能力（依 runtime/设备/license）；ros2_medkit_opcua（SOVD/REST 诊断插件，不作运动控制链路）。更新开源索引、兼容矩阵、链接台账 #625–#631、资产清单及 00/21 子计划。根计划主章节仍为00、主任务仍为00-01；本轮仅静态资料核验，未进行 PLC 实物互操作、周期性能、断线恢复、FAT/HIL 或安全验证，不提前验收。 | Beckhoff ADS ROS Index/官方库、Siemens OPC UA/Industrial Edge 官方文档、CODESYS 官方通信/现场总线资料、ROS Index ros2_medkit_opcua；静态快照截至 2026-11-04 |
| 2026-11-04 | v6.11 | 00-01/21-03 将 PLC—ROS 2 接口控制文件（ICD）模板纳入工程交付：新增 docs/templates/PLC-ROS2-ICD.md，覆盖 PLC/ROS/安全控制责任分配、ADS/OPC UA/S7/Modbus 网络与证书配置、PLC tag/NodeId/寄存器到 ROS 接口映射、命令确认/幂等/超时、周期与延迟预算、故障注入、SIL/HIL/FAT/SAT 证据及变更控制；开源项目索引增加模板入口，兼容矩阵增加 5.7.1 工程准入清单，资产清单登记模板。根计划当前主章节仍为00、主任务仍为00-01，21-03 继续进行中；模板未绑定具体 PLC 型号/项目变量，未连接 PLC 或完成互操作、性能、FAT/HIL/SAT 和安全验证；全依赖 SBOM、许可证法律审查及全库 claim-level 验收未完成，不提前验收。 | ROS 2 Jazzy SystemInterface、Beckhoff ADS 官方库/AMS route 资料、Siemens Industrial Edge OPC UA connector；静态设计快照截至 2026-11-04 |
| 2026-11-04 | v6.12 | 00-01/21-03 开始建立软件供应链与 SBOM 基线：静态审查根 pyproject.toml、LICENSE、CI workflow 与 Python 工具包入口；确认 robot-knowledgebase 0.1.0/Python>=3.10，声明式 runtime dependencies 为空，build requirements 为 setuptools>=68/wheel，dev extras 为 pytest>=8.0/ruff>=0.6；CI 覆盖 Python 3.10–3.12，使用 actions/checkout@v4、setup-python@v5 标签，另从 rustypot 固定 commit 下载 STS3215 源文件。核对根目录未发现 requirements/poetry/uv/Pipenv/npm 锁文件；版本范围未解析、未生成真实环境 SBOM。新增软件依赖清单 CSV 与 SBOM 初始审计报告，记录 CycloneDX 1.7、cyclonedx-py 生成策略、SPDX 3.0 补充评估及 Actions SHA pinning 风险；链接台账 #632–#635。根计划当前主章节仍为00、主任务仍为00-01；本轮仅静态审查，未安装依赖、构建/运行测试、生成/验证 CycloneDX JSON、扫描 CVE 或形成法律意见；ROS/PLC/硬件产品级 BOM、完整依赖闭包和许可证审查仍未完成，不提前验收。 | 根 pyproject.toml/LICENSE/CI workflow；Ecma ECMA-424、CycloneDX Python usage、GitHub Actions Secure Use、OMG SPDX 3.0；静态快照截至 2026-11-04 |

## 9. 当前任务节点与执行队列

### 9.1 当前主任务

- **当前主章节序号：00｜知识治理与分类体系。**
- **当前主任务节点：00-01｜知识资产基线与主张级审计。**
- **选择原因：** 资产路径、文件结构和代表性内容已建立基线，但 120+ 项知识资产仍处于 `unaccepted_claim_level_review_pending`；定向修订和结构扫描不能替代逐条主张、参数、标准版本、来源和适用边界审查。该治理工作是后续章节验收和知识可靠性的前置条件。
- **横向产品化主线：** 第 25 章同步推进 25-03（产品机会确认）、25-04（系统需求/可行性）、25-12（参考项目贯通）和 25-13（成品教学臂/模块化关节产品基准调研）、25-14（官方手册/接口深度核验，已补 Feetech STS3215 规格书核验）。第 25 章不取代 00–24 的专业验收。

### 9.2 当前进行中的章节节点

| 章节 | 进行中节点 | 当前工作与未关闭项 |
|---|---|---|
| 00 知识治理 | 00-01、00-07、00-08、00-09、00-10 | 资产主张级审计（新增 ROS 2 QoS/实时性/中间件、KF、SLAM、融合定位、激光 SLAM/LIO、视觉 SLAM/VIO、学习型算法与 VLA、路径规划/局部避障、多机协同、视觉感知、轨迹优化与运动控制、算法目录索引、Nav2、实时系统与嵌入式、DDS专题、ROS1迁移定向复核）；零基础课程与能力测评；阶段门跨章映射；教学成熟度抽样；许可/事实授权和隐私复核；新增外部工程项目登记与知识化治理（MotionControlAlgorithms、Stäubli ROS 2 driver），保持源码/知识资产边界 |
| 04 运动机构与执行器 | 04-02、04-03、04-04 | 减速器、电机/驱动器专题已纠正无条件通用参数；准确型号数据、工况计算、接口兼容和实测待补 |
| 05 电子电气与能源 | 05-01、05-03、05-04 | 电源预算、电池/BMS、自动充电页面已做定向修订；项目级电源树、器件接口、热/保护/充电验证待补 |
| 06 传感器 | 06-01、06-02、06-03 | 分类、空间传感器及运动/位置传感器页面已定向修订；完整标定、驱动兼容和环境可靠性验证待补 |
| 07 计算平台 | 07-01、07-02、07-04、07-05 | 官方算力口径、开发套件/生产模组边界、生命周期已复核；目标任务基准、工业环境与安全启动/替代验证待补 |
| 10 通信与中间件 | 10-07 | 已核验 ISO 21423:2026 官方范围；标准正式文本映射和多厂商互操作测试待做 |
| 14 规划控制与操作 | 14-04、14-05 | 已有零基础机械臂教材；完整 3D 运动学/动力学、冗余求解、控制接口和硬件实测待补 |
| 17 多机器人调度 | 17-07 | 已建立 ISO 21423:2026 标准入口；对象/消息映射、异常和多供应商互操作测试待做 |
| 18 BOM/供应链/成本 | 18-07、18-08 | 桌面机械臂 NPI 草案包含 EBOM/MBOM 与供应商质量流程；真实 BOM、报价、供应商审核和来料记录待补 |
| 21 产业生态/厂商/市场 | 21-01、21-02、21-04、21-05 | Stäubli Sequence teardown：Run #139/#140/#141累计30/30真实teardown SIGSEGV；Run #144/#145/#146累计30/30 GDB inferior正常退出、未观察到真实SIGSEGV，但旧GDB正常退出后No stack导致30/30 launch test误判失败。Run #146 10/10创建时/plan_sequence_path control-block vtable由info symbol直证位于source-overlay libsequence_capability.so的.data.rel.ro。Run #147（Actions 43862172486）有效完成10/10 stock-rclcpp无插桩mock回归：10/10执行成功、GDB inferior exit 0、每轮7 tests/0 failures、teardown断言通过。Run #148（Actions 43868030841）并发探针10/10轮测试本体通过但旧脚本仍期待7项、实际8项导致验收失败；Run #149（Actions 43873768855）修正为8项后完整CI 10/10通过。动态日志每轮确认同一OMPL pipeline上PlanService/SequenceService重叠，fast退出时及slow恢复时active_=false且probe_inflight=1，两服务SUCCESS、GDB exit 0、无SIGSEGV。固定MoveIt Jazzy commit f11204b8a9b98e4ba28e564721d24a7077f5f969源码确认：MoveItCpp::terminatePlanningPipeline仅在isActive()==true时调用PlanningPipeline::terminate()，而isActive()直接读取atomic bool active_；并发门禁已证明active_=false时仍可有slow generatePlan调用在途。已在既有实验分支增加MoveItCpp真实wrapper terminate gate（提交c58d1c8/0b218b9/ee8d1a8），要求slow在active_=false暂停、触发公开wrapper、验收wrapper是否跳过底层terminate；Actions #150/#151/#152均已通过ROS Jazzy setup及workspace tooling，当前均进入stock ROS 2 Jazzy rclcpp overlay构建步骤；截至本次核对仍in_progress，日志接口对运行中job返回BlobNotFound，尚无MoveIt构建或mock运行结果。未关闭terminate门禁前不合并Sequence callback-group拆分。仅CI mock，不修改MoveIt/rclcpp upstream或Stäubli正式源码，不连接CS9，不宣称HIL/SAT/实机验收。
| 19 测试与验证 | 19-06、19-08 | 故障诊断/FRACAS/CAPA 方法和模板已建立；真实产品故障库、量产质量统计和案例待补 |
| 20 安全与法规 | 20-03、20-07 | 初始危险源清单已建立，标准声明定向复核已进行；正式风险估计、专业评审和逐项主张核验待做 |
| 22 项目集成与生命周期 | 22-05、22-07、22-08、22-09 | 故障闭环及 NPI/质量/交付流程草案已建立；真实工厂、批次、良率、放行和客户交付数据待补 |
| 25 零基础到量产路线 | 25-03、25-04、25-12、25-13、25-14 | 桌面机械臂教学参考项目已建；新增成品教学臂/关节模组官方资料基准及手册/接口核验；SO-101 leader/follower BOM、供电配置、STS3215/C044/C046/C047 型号规格、Feetech STS 通用保护寄存器映射、LeRobot 夹爪保护参数写入与健康观测缺口、WaveShare ST 协议/控制表及 LeRobot/rustypot 驱动源码已进一步核对；新增 C047 A/0（2023-07-20）规格书副本并确认铜齿、12V、1:345、过流>2A持续2s、过热>70℃等型号级数据；纠正 STS 地址0–4版本字段、地址19卸载位定义及地址28/34/35/36/38字段映射；硬件型号/BOM/寄存器默认值/板卡身份/实机测试等9项缺口已移入项目TODO.md（HW-001–HW-009），不阻塞可独立推进的软件与文档工作；新增 LeRobot SerialMotorsBus 只读API边界审查，确认disconnect默认会卸扭矩写入并定义只读采集约束；真实任务输入、原始文件归档、动态参数/热曲线、报价/生命周期、实机与方案评审待补 |

### 9.3 状态核对结论

- 本次逐章核对了 00–25 共 26 个章节计划中的全部任务节点，并对本轮存在明确成果的节点更新状态。
- **当前没有节点标记为“已完成”。** 这不是遗漏：截至本次核对，没有任何节点同时具备其计划要求的完整交付物、验收证据和必要专业/项目评审。已建立文章、模板、来源入口或局部内容修订只足以支持“进行中”。
- 未实际开展且没有可核验证据的节点保持“未开始”；已经在做但存在范围、来源、测试或评审缺口的节点标记为“进行中”。不得为了推进根计划章节序号而把不完整节点改为完成。
- 子计划中记录更细的状态、证据和阻塞；本节是全局当前队列快照。每次任务状态变化时，应同步更新对应子计划和本节，并在根计划变更日志追加记录。
- 下一步继续 00-01 的逐条主张级审计；《特种机器人》已完成本轮全文复核，但具体产品证书、目标市场法规矩阵和任务实测仍待核验；《云平台与IoT通信》已完成全文主张边界审查和正文修订，但Broker部署/压测、弱网与断电恢复、证书/ACL渗透及端到端OTA仍待实测；《仿真平台》已完成全文主张边界审查和正文修订，但平台安装、模型运行、PIL/HIL和实机对照仍待验证；《构建与CI工具链》已完成全文主张边界审查和正文修订，但仓库CI执行、交叉编译、SBOM生成/覆盖、制品签名验证及目标硬件OTA仍待验证；《视觉软件栈》与《09-10 系统联调与测试》已完成P1全文静态主张边界审查，厂商目录README及项目档案入口/项目BZ、清洁机器人档案也已完成相应静态审查；后续按资产清单和风险优先级继续推进，最近第21章21-02已追加Yaskawa MOTOMAN传统DX200/YRC控制器及MOTOMAN NEXT/YNX1000+ACU双平台增量审查，覆盖MotoSim/MotoROS2/YMConnect/MotoPlus/INFORM/MotoLogix和ACU服务、YNX仿真边界；下一轮按21-02尚未覆盖的P1厂商/软件路线及医疗、服务机器人注册证原始证据缺口继续；已对 KF、SLAM 总览、多传感器融合定位、激光 SLAM/LIO、视觉 SLAM/VIO、学习型算法/VLA、路径规划、局部避障、多机协同、视觉感知、轨迹优化/运动控制、算法目录索引、Nav2、实时系统/嵌入式、DDS、ROS1 迁移、标准法规、工业机器人、协作机器人、移动机器人、仓储物流机器人和医疗机器人做定向复核，但不得视为全文验收；路径规划与局部避障测试执行状态已由用户于2026-11-03确认完成，测试报告/原始数据尚待归档和证据核对；标准法规尚待具体产品/市场适用性矩阵、正式标准全文条款审查和认证路径核验；工业机器人尚待目标型号/工艺性能与现场安全实测；协作机器人尚待具体工具/工件/工位的应用级风险评估、SSM/PFL 安全性能与现场 SAT；移动机器人尚待目标车辆/载荷/现场路线风险评估、制动距离/人员检测/定位对接/续航/车队故障恢复测试；仓储物流机器人尚待目标仓库订单/SKU 数据、吞吐/排队仿真、货架/消防/人机共域风险评估、系统联调及 FAT/SAT；医疗机器人尚待具体产品分类/注册路径、临床评价/试验策略、目标性能/基本安全/可用性/软件网络安全和临床证据验证；柏惠维康（重庆）机器人股份有限公司迁址/证照迁移审查新增地方监管经营许可申请公示、官网当前主体及第三方注册证变更记录，媒体所称三类生产许可证和8张注册证迁移仍待官方逐证核验；天智航新增骨科手术计划软件国械注准20263211672（2026-08-07公司公告，III类、有效期至2031-08-03），仅限与特定导航系统联合进行术前计划；不代表导航机器人本体证书。其国械注准20163012280第三方列示有效期2026-11-13，续证原件仍待查；本轮新增华科精准Q300 2026-07-06出口证明与北京市药监局2026-06-05创新名单快照差异核验，逐证主体沿革仍待电子注册证及变更备案原件；华科精准国家级注册证公开检索存在验证码，电子注册证与技术要求/说明书附件依NMPA规则由注册人法人空间取得；逐证索取清单已补入第21章厂商档案，SR1/NS1/Q300/X1000/SinoPlan当前证照包与历史纠错/变更原件均待注册人授权或官方核验；并行推进桌面机械臂 25-14 的原始手册归档/接口差异核验和 25-04 的真实任务输入收集准备；不能仅凭公开资料或教学假设决定产品选型、负载、器件、电压、成本或安全等级。

所有章节任务的最新状态以对应 `docs/TaskPlan/<章节>/TaskPlan.md` 为准；全项目范围、统一约束、当前主章节和最终验收以本文件为准。

---

## 10. 按日归档的推进记录

自 `2026-11-03 / v1.8` 起，原本追加在根计划末尾的日期/版本推进记录已按自然日拆分为独立文件。每日文件保留当日全部版本记录和详细补充，根计划不再承载长篇历史日志。

| 日期 | 每日子 TaskPlan | 记录条目数 |
| --- | --- | ---: |
| 2026-11-03 | [TaskPlan-2026-11-03.md](TaskPlan_History/TaskPlan-2026-11-03.md) | 36 |
| 2026-11-04 | [TaskPlan-2026-11-04.md](TaskPlan_History/TaskPlan-2026-11-04.md) | 89 |
| 2026-11-05 | [TaskPlan-2026-11-05.md](TaskPlan_History/TaskPlan-2026-11-05.md) | 48 |
| 2026-11-06 | [TaskPlan-2026-11-06.md](TaskPlan_History/TaskPlan-2026-11-06.md) | 39 |
| 2026-11-07 | [TaskPlan-2026-11-07.md](TaskPlan_History/TaskPlan-2026-11-07.md) | 47 |
| 2026-11-08 | [TaskPlan-2026-11-08.md](TaskPlan_History/TaskPlan-2026-11-08.md) | 87 |
| 2026-11-09 | [TaskPlan-2026-11-09.md](TaskPlan_History/TaskPlan-2026-11-09.md) | 82 |
| 2026-11-10 | [TaskPlan-2026-11-10.md](TaskPlan_History/TaskPlan-2026-11-10.md) | 57 |
| 2026-11-11 | [TaskPlan-2026-11-11.md](TaskPlan_History/TaskPlan-2026-11-11.md) | 76 |
| 2026-11-12 | [TaskPlan-2026-11-12.md](TaskPlan_History/TaskPlan-2026-11-12.md) | 35 |
| 2026-11-13 | [TaskPlan-2026-11-13.md](TaskPlan_History/TaskPlan-2026-11-13.md) | 记录持续追加 |
| 2026-11-14 | [TaskPlan-2026-11-14.md](TaskPlan_History/TaskPlan-2026-11-14.md) | 14 |
| 2026-11-15 | [TaskPlan-2026-11-15.md](TaskPlan_History/TaskPlan-2026-11-15.md) | 记录持续追加（已汇总 PR #18–#21 专项记录及 v35 IMU / v36 LiDAR 审计） |
| 2026-11-16 | [TaskPlan-2026-11-16.md](TaskPlan_History/TaskPlan-2026-11-16.md) | 持续追加（v37–v80；Run #147 10/10 teardown PASS、Sequence DSO control-block vtable 10/10符号直证、same-OMPL active_并发门禁实现、验收计数修正与待运行状态） |

后续新增推进记录应追加到对应日期的 `TaskPlan-YYYY-MM-DD.md`；跨日时新建当日文件并在本索引中登记。根目录 `TaskPlan.md` 继续作为全局治理、Guide/Limit、章节目录、当前任务状态和总体验收入口。


> 2026-11-16 Stäubli增量（Run #131 workflow配置错误与无插桩复核重跑）：Run #131（Actions https://github.com/rexyll/staubli_driver_ros2_from_org/actions/runs/43808189052，workflow commit 4154ebdd00d04c98d510aedb3fd1e15ed3e18823）在第6步最终静态校验处失败。第5步已通过 git diff --exit-code，并明确输出 stock rclcpp 无 Executor/CallbackGroup/NodeBase/DynamicStorage 插桩；第6步却沿用Run #130诊断overlay旧条件，要求 dynamic_storage.hpp 包含 WaitSet WeakWaitableEntry dtor BEGIN，和无插桩目标互相矛盾。步骤7–10（MoveIt依赖、MoveIt构建、Stäubli mock构建、10轮测试）均跳过，因此#131不构成功能性PASS/FAIL。已在同一既有隔离分支修正检查：显式拒绝该marker存在，并只保留A/B cleanup token静态检查；workflow commit 4d58b7e6d3b83363d6e595400a1bb1a5e1ea6a72。Run #132（Actions https://github.com/rexyll/staubli_driver_ros2_from_org/actions/runs/43812432706）已由该提交自动触发；最近一次核验仍在执行，10轮无插桩结果待定。未新建分支，未改MoveIt/rclcpp上游或Stäubli产品源码，不连接CS9、不发送真实运动命令、不宣称HIL/SAT/实机验收。全局最高优先级仍为00-01；MotionControlAlgorithms合并继续延期。


> 2026-11-16 Stäubli 无插桩确认与 A 因子第一项消融：Run #132（Actions https://github.com/rexyll/staubli_driver_ros2_from_org/actions/runs/43812432706，commit 4d58b7e6d3b83363d6e595400a1bb1a5e1ea6a72）在 stock ROS 2 Jazzy rclcpp、无诊断析构插桩条件下，A=ON、K固定、B-core=ON 共10轮均通过。原始日志确认10/10 mock plan-and-execute SUCCEEDED、每轮launch summary为7 tests/0 errors/0 failures/0 skipped、B-core marker顺序完整、各轮colcon_test=0/test_result=0/lifecycle_order=0，无SIGSEGV；artifact 14201681819，SHA-256 1bd5c27cbf3803dc8565d24b73c06b7b9b99edda64874b57dc42db0c3664cb0e。此结果表明A+K+B-core组合不依赖Run #130的rclcpp析构探针，结论仍限临时MoveIt patch + stock rclcpp + Stäubli mock CI。

> 2026-11-16 Stäubli A-PSM-retained 实验：固定K与B-core，单独取消main()中planning_scene_monitor.reset()，保留moveit_cpp.reset()和nh.reset()；通过不持有强引用的weak_ptr在MoveGroupExe/executor作用域退出后检查PSM是否仍存活并报告use_count。workflow commit 4d664f184820bf5f536e205742a50d20cb4a004c（Run #133）因多行Python字符串的缩进行为越过YAML run块边界而产生0个job，不计功能结果。已在同一分支修复为正确缩进的拼接字符串，同时修正weak-probe换行转义；commit 5abf808424049dec78e2dc6247f453af59be0e29触发Run #134（Actions https://github.com/rexyll/staubli_driver_ros2_from_org/actions/runs/43816245159），当前为in_progress。全局最高优先级仍为00-01，MotionControlAlgorithms合并继续延期。


> 2026-11-16 MoveIt Jazzy 执行状态/取消路径并发静态审计：新增 `docs/audits/2026-11-16-moveit-jazzy-execution-state-thread-safety-audit.md`，基于 MoveIt Jazzy commit `f11204b8a9b98e4ba28e564721d24a7077f5f969` 审查 `MoveGroupMoveAction::preempt_requested_`、TEM `execution_complete_` / `last_execution_status_` / `execution_thread_`。静态路径显示 detached action worker 与cancel callback共享普通bool但无同步；TEM完成标志在 Jazzy 为普通bool且读写锁域不一致，状态成员与线程指针也有锁覆盖缺口。MoveIt main 快照 `5815c90b36ba028a42f49aa7f2364067093b21c0` 已将 `execution_complete_` 改为 atomic，但last status、thread owner和Action preempt bool仍需审查。当前仅完成静态审查，未运行TSAN、动态竞态复现或HIL；不得将其表述为运行时数据竞争报告。Run #134（Actions 43816245159）已通过stock rclcpp无插桩构建、MoveIt patch静态校验，当前停留于MoveIt依赖安装；PSM-retained 10轮测试尚未开始。根计划最高优先级仍为00-01；第21章Stäubli专项并行推进，MotionControlAlgorithms合并继续DEFERRED。


> 2026-11-16 MoveIt shutdown生命周期审计补充：对照 `move_group.cpp`、`MoveGroupMoveAction` 与 `MoveGroupCapability` 后发现 accepted callback 使用捕获裸`this`的 detached worker，未在该capability类中找到join/worker-count屏障；`MoveGroupExe`析构按`capabilities_.clear()` → `context_.reset()` → `capability_plugin_loader_.reset()`执行。活动goal与shutdown重叠时存在capability/context/插件代码先于worker退出被销毁的高优先级静态风险。已在 `docs/audits/2026-11-16-moveit-jazzy-execution-state-thread-safety-audit.md` §2.4与§5增加worker drain/barrier确定性测试及ASan/TSAN分离验证要求。该项仍未动态复现；不修改产品源码。Run #134已通过MoveIt依赖安装并进入patched move_group构建，mock/10轮测试尚未开始。


> 2026-11-16 MoveGroup action 多goal并发补充：源码中的goal callback对每个goal都返回ACCEPT_AND_EXECUTE，并为每个accepted goal启动独立detached worker；但 `MoveGroupMoveAction` 实例仅有一份 `goal_`、`move_state_`、`preempt_requested_` 成员。没有从该源码路径看到single-active-goal门禁，故两个goal重叠时存在共享成员并发访问、feedback/result关联串扰及一个goal取消影响另一个goal的静态风险候选。已加入审计报告§2.5及双goal确定性mock测试要求；是否会被rclcpp_action或外部调用约束排除仍需实测，不能直接认定生产环境必然并发接纳。
