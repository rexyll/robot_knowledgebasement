# 审计与资产盘点

- [2026-11-04 Python 锁定依赖漏洞扫描基线](2026-11-04-python-vulnerability-scan.md)：OSV API 批量查询 uv.lock、PEP 517 build constraints、SBOM generator 与 build-tools 锁；首轮扫描发现 SBOM generator pip 25.0.1 的 6 个 CVE，已升级 pip 26.3；run #41779562839 对 45 个 package/version 复扫为 0 advisory/0 finding，扫描范围不等于机器人产品级漏洞审计。

本目录记录 Robot Knowledge Basement 的仓库资产、内容质量、来源和公开发布审查。

## 当前记录

- [2026-11-06 FANUC ROS 2 Driver / Stream Motion 1 ms与数据包可靠性增量审计](2026-11-06-fanuc-ros2-stream-motion-reliability-review.md)：对照FANUC Open Platform 1 ms宣传与实际ROS 2控制器/选件/URDF矩阵；静态核对v2.4.0 main Stream Motion序列处理、open Issue #67乱序UDP状态包、轨迹加速度/jerk约束、position-only command接口和ros2_control API迁移风险；未构建、未运行网络注入或连接实机。

- [2026-11-06 Techman Robot TMflow/ROS 2/EIH Camera生态静态审查](2026-11-06-techman-robot-software-ros2-ecosystem-review.md)：区分传统TM与S系列驱动、Humble/Jazzy、Ethernet Slave/Listen Node、MoveIt/Gazebo模型、EIH gRPC客户端及S系列安全/网络安全声明；未构建、未连接实机或执行安全/HIL/FAT/SAT验证。

- [2026-11-06 Doosan Robotics DART/DRFL/ROS 2生态静态审查](2026-11-06-doosan-robotics-software-ros2-ecosystem-review.md)：区分Humble/Jazzy、DRCF v2/v3、ros2_control与DRFL 1kHz RT UDP；记录DART-Suite、系列传感器差异、P系列安全声明和许可版本差异，未构建或连接实机。

- [2026-11-06 Universal Robots PolyScope/URCap/ROS 2生态静态审查](2026-11-06-universal-robots-software-ros2-ecosystem-review.md)：区分PolyScope X内置ROS 2、外部ur_robot_driver、ur_client_library和URCapX；记录g-series主分支支持、PSX 10.7/Humble与10.15/Jazzy、运动控制器和安全责任边界；未构建或连接实机。


- [2026-11-06 Epson Robotics RC+ 8.0/RTMC/ROS 2生态审查](2026-11-06-epson-robotics-ecosystem-review.md)：核对RC+ 8.0/SPEL+、RC800 RTMC、官方ROS 2 Humble驱动、AX6/AX Portal独立栈、Lifecycle自动重启风险、1 kHz/2 ms时基与buffer默认值差异，以及安全功能型号/固件矩阵；仅静态审查，未构建或连接实机。

- [DENSO WAVE软件生态审计](2026-11-06-denso-wave-robotics-ecosystem-review.md)：WINCAPS、VRC、ORiN2、ROS 2及控制器支持边界的静态审查。

- [2026-11-06 Mitsubishi Electric MELFA软件与ROS 2生态审查](2026-11-06-mitsubishi-melfa-ecosystem-review.md)：核对RT ToolBox3/RT VisualBox、MELFA API for Linux、官方ROS 2 Driver/Monitor、CR800网络与安全选件；仅完成官方资料静态审查，未安装软件或实机验证。
- [2026-11-06 安全防护器件安全门联锁与防护锁定主张定向复核](2026-11-06-safety-guard-interlock-review.md)：依据 ISO 14119:2024 及 Pilz、Schmersal、EUCHNER 具体产品资料，核对联锁/锁定边界、编码、防篡改、失电和逃生风险；未执行门体/锁定/现场验证，整篇资产仍待 claim-level 验收。
- [2026-11-06 安全防护器件急停功能与安全继电器配置主张定向复核](2026-11-06-emergency-stop-safety-relay-review.md)：核对 ISO 13850 生命周期、急停复位/启动边界，以及 Siemens 3SK1、OMRON G9SE、Pilz PNOZ X3 的配置/反馈/响应时间资料；未进行设备或整机验证，整篇资产仍待 claim-level 验收。
- [2026-11-06 电池与电源 IEC 62619 / IEC 63056 / UN 38.3 版次定向复核](2026-11-06-battery-IEC62619-UN383-review.md)：更新 UNECE Rev.8 Amendment 1（2025）运输手册入口，区分工业电池与固定式储能系统标准范围；未审读标准全文或验证具体电池/整机，整篇资产仍待 claim-level 验收。
- [2026-11-06 Kawasaki Robotics软件与ROS 2生态静态审查](2026-11-06-kawasaki-robotics-ecosystem-review.md)：核对AS/KRNX、K-ROSET/neoROSET、F系列A/B安全单元、官方ROS 2 Jazzy驱动、500 Hz/2 ms RTC配置、Lifecycle恢复与KRNX专有许可；未安装软件/连接控制器或执行实时、安全、HIL/FAT/SAT验证，厂商档案保持静态审查未验收。
- [2026-11-06 安全防护器件安全激光扫描仪配置主张定向复核](2026-11-06-safety-scanner-configuration-claim-review.md)：依据 OMRON OS32C 与 SICK microScan3 Core I/O 官方规格/操作说明，复核配置依赖、响应时间、OSSD边界及 ISO 3691-4 版次状态；未进行设备或整机验证，整篇资产仍待 claim-level 验收。

- [2026-11-06 功能安全体系 ISO 13849-1 / IEC 62061 范围主张定向复核](2026-11-06-functional-safety-ISO13849-IEC62061-scope-review.md)：核对两项机械功能安全标准的公开范围、运行模式、版次与排除边界；未审读标准全文或验证具体产品，整篇资产仍待 claim-level 验收。
- [2026-11-06 电机与驱动器 IEC 61800-5-2 范围主张定向复核](2026-11-06-motor-drive-IEC61800-5-2-scope-claim-review.md)：P0 专项审查，仅覆盖《电机与驱动器》§8 的公开标准范围、应用集成排除项和低需求模式边界；整篇资产仍待完整 claim-level 审查。
- [2026-11-04 Python SBOM 许可证元数据候选审计](2026-11-04-python-license-metadata-audit.md)：四环境 45 条 CycloneDX license metadata 候选；10 条记录均已取得版本级 tag/commit 或 PyPI provenance/release 许可证证据；法律复核仍未完成；SBOM artifact SHA256SUMS 路径修复已由 CI 下载验证。
- [许可证元数据人工复核队列 CSV](2026-11-04-python-license-metadata-review-queue.csv)：7 条 classifier/free-text 组件记录及 3 条 packaging OR expression 记录。
- [2026-11-04 PEP 517 构建隔离依赖哈希锁定记录](2026-11-04-pep517-build-dependency-lock.md)：setuptools/wheel/packaging 版本及 SHA-256 锁定，Python 3.10/3.11/3.12 `uv build --require-build-hashes` 通过。
- [2026-11-04 SBOM generator 工具链锁定记录](2026-11-04-sbom-generator-toolchain-lock.md)：uv 0.13.7 生成带 SHA-256 的工具依赖锁，pip 26.3 修复首轮 OSV 命中，CI 复扫无匹配；generator/build-tools SBOM 与 license metadata 候选已归档。
- [2026-11-04 Python 依赖锁定策略决策](2026-11-04-python-lockfile-decision.md)：选择 uv 0.13.7 与 uv.lock，记录 runtime/dev universal lock、CI --locked 验收及 build/generator 例外；uv.lock 已生成提交，三版本 `uv sync --locked` 与 SBOM 产物复核通过；build/generator 工具链已分别 hash-lock 并由 CI 验证。
- [2026-11-04 rustypot 外部源码完整性记录](2026-11-04-external-source-integrity.md)：固定 STS3215 源文件 commit、7,434-byte SHA-256、CI run #534 已在 Python 3.10/3.11/3.12 全矩阵通过摘要校验；上游 Apache-2.0 LICENSE 证据已记录，法律范围仍待审。
- [2026-11-04 Python SBOM CI 生成流水线记录](2026-11-04-python-sbom-ci-pipeline.md)：记录 runtime/dev/generator/build-tools 四环境 CycloneDX 1.7 生成、许可证元数据候选提取、工具环境隔离、Actions SHA pinning 与 CI 产物核验。
- [ROS 2 产品级 SBOM 采集模板](../templates/ROS2-Product-SBOM-Intake.md)：面向实际机器人产品配置，覆盖 ROS workspace、rosdep/OS、容器、GPU/BSP、固件、厂商 SDK 与 PLC；配套 CSV 为空白采集表，不代表已采集产品 BOM。
- [2026-11-04 软件供应链与 SBOM 初始基线](2026-11-04-software-supply-chain-baseline.md)：记录 Python 工具包的声明式依赖、CI Actions、版本锁定缺口与后续 CycloneDX 生成流程。
- [2026-11-04 软件依赖清单](2026-11-04-software-dependency-inventory.csv)：按运行时、构建、开发、CI、外部源码和生态候选范围登记依赖及解析状态；不是 resolved SBOM。

- [2026-11-06 知识资产 Git Tree 对账与清单刷新](2026-11-06-knowledge-asset-tree-reconciliation.md)：按 main Git Tree 对账 253 个 Blob、205 份 Markdown、142 份 knowledge Markdown；补入漏登的 17 份知识文件并刷新 17 条过期 SHA/大小。仅为元数据对账，不是正文或主张级审查。
- [2026-11-03 基线盘点与抽样审计](2026-11-03-baseline-inventory.md)：记录初始基线、代表性内容抽样、历史缺口和优先级队列。
- [2026-11-03 知识资产清单](2026-11-03-knowledge-asset-inventory.csv)：逐项列出 knowledge/ 下 142 份 Markdown 的路径、Git Blob SHA、大小、文件类型、抽样深度、优先级和验收状态。2026-11-08对《主要厂商.md》同一资产行随§128.62–§128.64两轮内容更新刷新Blob SHA与UTF-8大小元数据；不代表全清单元数据均已刷新或该文档主张级验收完成。
- [2026-11-03 机器人硬件与安全专项来源补充台账](2026-11-03-robot-safety-source-register.md)：记录标准组织、制造商官方规格页和版本边界。

## 审计状态

- 00-01 全库资产盘点：进行中。2026-11-08交叉核查发现Stäubli专项记录在根计划、专项报告、厂商档案、本索引及第00章日志之间未同步；详见[专项审计记录同步性核查](2026-11-08-staubli-audit-record-synchronization.md)。在完成逐节同步和来源复核前，不以根计划摘要替代专项报告正文。
- 结构统计：已建立，清单可从 Git Tree 复算；当前 main Git Tree 快照为 260 个 Blob、212 份 Markdown、142 份 knowledge Markdown、67 份 docs Markdown、26 份章节 TaskPlan；详见 Git Tree 对账报告。
- 标题/结构检查：原 112 份知识文件保留历史标题、章节结构和开篇检查记录；当前 142 份资产的统一结构扫描覆盖率尚未重新计算。后续新增文件存在专题审查/结构检查记录，但尚未统一汇总为当前覆盖率。
- 全文结构扫描：96/120 是旧快照统计，不能作为当前 142 份资产的覆盖率；本轮只做 Git Tree/Blob 元数据对账，当前统一结构扫描需重新执行。结构扫描不等于专业审稿或 claim-level 验收。
- README 最近一次扫描：既有目录 README 的正文结构检查记录保留；本轮只刷新清单涉及文件的 Git 元数据，不重新判定 README 正文质量。
- 高风险 P0 定向处理：20/20 份资产已完成边界纠偏或内容修订；具体范围见基线审计第 14–16 节。定向处理不等于全文 claim-level 验收。
- Claim-level 验收：142/142 份知识资产在当前清单中均保持未完成完整主张级验收；逐项来源、参数、法规和安全审查仍待完成。专题定向修订不等于整篇通过。
- 外链、参数、标准/法规和安全关键结论：仍需逐项核验。
- 项目公开披露：已对项目案例和首页中的本地绝对路径做首轮脱敏；代码许可证、项目授权和组织关系仍需核验。

## 状态纪律

清单中的未审文件不代表质量不合格，只表示尚无验收证据。抽样不能替代逐篇审查；文件存在、标题完整、链接数量或文章长度均不能单独作为完成证明。审计完成状态以根目录 TaskPlan 的 00-01 任务验收为准。






- [2026-11-06 Stäubli Robotics CS9/VAL3/ICube ROS 2生态专项审查](2026-11-06-staubli-robotics-ecosystem-review.md)：固定ICube commit静态审查至§9.3.38；新增MoveIt Servo/JTC命令仲裁、Servo输出控制器缺失、资源claim边界与pause非停止语义审查（§9.3.38，SERVO-01–SERVO-14）；新增控制器启动就绪、QoS兼容性、MoveIt静态active状态与硬件故障恢复审查（§9.3.37，LFR-01–LFR-14）、MoveIt取消传播及执行结果一致性（§9.3.36，MEX-01–MEX-14）；新增MoveIt取消传播、ExecuteTrajectory取消接线、TEM/ControllerHandle取消确认和静止结果处理（§9.3.36，MEX-01–MEX-14）、轨迹取消/抢占/受控减速与VAL3 STOP调用链（§9.3.35，CXL-01–CXL-12）、轨迹完成语义/反馈一致性/MoveIt Action容差（§9.3.34，TRJ-01–TRJ-12）、运动命令NaN/Inf输入边界及URDF/ros2_control/MoveIt/VAL3限位分层（§9.3.33，JNT-01–JNT-10）、ROS2—UDP—VAL3端到端实时控制周期/反馈新鲜度/命令时序闭环（§9.3.32，RT-09–RT-17）、ros2_control生命周期STOP责任与模式切换边界（§9.3.31，LIFE-01–LIFE-08）、连接握手/诊断双通道ready（§9.3.28，CONN-01–CONN-07）、UDP端口参数严格解析/uint16_t窄化边界（§9.3.29，PORT-01–PORT-05），以及UDP发送错误传播、接收错误回调、stop/start线程生命周期和peer校验缺口（§9.3.30，UDP-01–UDP-09、SUB-01–SUB-02）。未运行构建/单测、参数/网络故障注入、VAL3编译/SRS仿真或CS9 HIL/实机验证。


- [2026-11-06 Stäubli Robotics CS9/VAL3/ICube ROS 2生态专项审查](2026-11-06-staubli-robotics-ecosystem-review.md)：固定ICube/MoveIt/ros2_controllers源码快照静态审查已推进至§9.3.39；本轮新增Servo输入Header stamp超时与ForwardCommandController下游命令缓存/周期重复写入语义（SERVO-15–SERVO-24），指出Servo smoothHalt完成后下游仍可能保持最后位置目标、ForwardCommandController无命令年龄watchdog，pause不触发smoothHalt。此前§9.3.38记录Servo输出controller缺失与JTC资源claim仲裁边界。未执行ROS构建/集成、断流/时间跳变/多发布者注入、VAL3/SRS、CS9 HIL或实机安全验证。


- [2026-11-06 Stäubli Robotics CS9/VAL3/ICube ROS 2生态专项审查](2026-11-06-staubli-robotics-ecosystem-review.md)：固定ICube/MoveIt/ros2_controllers源码静态审查已推进至§9.3.42；本轮补充Servo输入超时与ForwardCommandController命令缓存（§9.3.39，SERVO-15–SERVO-24），以及Float64MultiArray无关节名、Servo active joint order与ForwardController joints参数必须逐项一致的六轴映射契约（§9.3.40，SERVO-25–SERVO-29）。默认Stäubli静态配置预期joint_1至joint_6一致，但ForwardCommandController未注册，实际集成映射未验证。未执行xacro展开、ROS集成、fake hardware、VAL3/SRS、CS9 HIL或实机安全验证。


- [2026-11-06 Stäubli Robotics CS9/VAL3/ICube ROS 2生态专项审查](2026-11-06-staubli-robotics-ecosystem-review.md)：固定ICube/MoveIt/ros2_controllers源码静态审查已推进至§9.3.41；本轮新增Servo与ForwardCommandController topic/type/namespace/QoS/lifecycle契约（SERVO-30–SERVO-36），确认默认根namespace下绝对topic与controller私有topic预期一致但多机器人namespace可能分叉，两端SystemDefaultsQoS需目标RMW实测，ForwardController未注册且inactive期间拒收命令。未执行ROS graph/QoS/namespace/remapping/实时链路或生命周期测试。


- [2026-11-06 Stäubli Robotics CS9/VAL3/ICube ROS 2生态专项审查](2026-11-06-staubli-robotics-ecosystem-review.md)：固定ICube/MoveIt/ros2_controllers/ROS 2 Jazzy QoS/realtime_tools/SROS2静态审查推进至§9.3.43；新增DDS QoS队列、Reliable/BestEffort新鲜度、Deadline/Lifespan/Liveliness能力边界、ForwardController RealtimeThreadSafeBox单槽位覆盖和try_get失败旧值保留风险（SERVO-37–SERVO-46）。未运行目标RMW/DDS、网络故障注入、QoS事件、实时锁竞争、HIL或实机验证。


- [2026-11-06 Stäubli Robotics CS9/VAL3/ICube ROS 2生态专项审查](2026-11-06-staubli-robotics-ecosystem-review.md)：静态审查推进至§9.3.43；新增Servo输入/输出多发布者竞争、ForwardController无publisher身份校验、SROS2默认关闭/Enforce/独立enclave/topic-service ACL能力边界及业务控制租约不足（SERVO-47–SERVO-57）。未部署keystore/ACL，未执行双publisher、越权、remapping绕过、密钥生命周期或HIL/实机验证。


- [2026-11-06 Stäubli Robotics CS9/VAL3/ICube ROS 2生态专项审查](2026-11-06-staubli-robotics-ecosystem-review.md)：静态审查推进至§9.3.44；新增ros2_control Jazzy硬件read/write ERROR、controller update ERROR、controller chain/fallback与hardware lifecycle恢复路径；核对ICube read反馈超龄检测、UDP本地连接状态、on_error STOP发送未检查返回值及STOP不等于机械/安全停止。新增SERVO-58–SERVO-69。未执行故障注入、SIL/HIL、CS9实机或端到端停止时间验收。


- [2026-11-06 Stäubli Robotics CS9/VAL3/ICube ROS 2生态专项审查](2026-11-06-staubli-robotics-ecosystem-review.md)：静态审查推进至§9.3.45；新增UDP本地connect不构成应用握手、诊断帧未验证却标记ready、无自动重连监督器、VAL3 uint16序号复位无session epoch、错误恢复缺少冷却/授权门控，以及UDP would_block丢包仍返回true等发现（SERVO-70–SERVO-80）。现有mock测试仅覆盖同一会话内staleness恢复；未执行跨重启/重连、旧命令重放、SIL/HIL或CS9实机测试。


- [2026-11-06 Stäubli Robotics CS9/VAL3/ICube ROS 2生态专项审查](2026-11-06-staubli-robotics-ecosystem-review.md)：静态审查推进至§9.3.46；本轮核对VAL3服务端STOP中转模式切换、bInMotion启动门控、position/velocity函数实际实现、命令解析和sequence滞后检查。确认velocity分支仍未实现、无严格重复/乱序命令拒绝和显式deadline，无包staleness及故障后冷却/重新授权仍为TODO（SERVO-81–SERVO-90）。未执行VAL3编译运行、CS9、SIL/HIL或实机停止验证。

- [2026-11-06 Stäubli Robotics CS9/VAL3/ICube ROS 2生态专项审查](2026-11-06-staubli-robotics-ecosystem-review.md)：静态审查推进至§9.3.47；新增状态遥测来源/valid flags与物理语义边界：速度为命令速度近似、力矩为无精度承诺的电流估算、制动器状态为驱动上电代理、in_motion来自VAL3 settled判据、motion_possible未显式纳入Automatic Hold，F/T和IO仍未实现（SERVO-91–SERVO-100）。未执行独立测量、CS9模式扫描、跨语言运行测试或HIL/实机验证。

- [2026-11-06 Stäubli Robotics CS9/VAL3/ICube ROS 2生态专项审查](2026-11-06-staubli-robotics-ecosystem-review.md)：静态审查推进至§9.3.48；新增VAL3命令帧payload长度字段解析后未复核的问题：前置长度检查使用初始化Header的8+47，随后解码报文payload_size但未再核验47B固定payload；C++侧则在Header解码后严格校验（SERVO-101–SERVO-108）。未执行异常UDP注入、VAL3/SRS、CS9/HIL或实机验证。

- [2026-11-06 Stäubli Robotics CS9/VAL3/ICube ROS 2生态专项审查](2026-11-06-staubli-robotics-ecosystem-review.md)：静态审查推进至§9.3.49；新增VAL3 SIO UDP接收语义与错误返回问题：sioGet按输入缓冲区/数组读取，timeout=-1时0为空缓冲区、-1为读取错误；readDataOnce未处理-1，readData可能静默上报无新数据。SIO手册未保证UDP datagram边界语义，需目标CS9/SRS注入验证（SERVO-109–SERVO-118）。未执行仿真、HIL或实机验证。

- [2026-11-06 Stäubli Robotics CS9/VAL3/ICube ROS 2生态专项审查](2026-11-06-staubli-robotics-ecosystem-review.md)：静态审查推进至§9.3.50；新增VAL3 clearBuffer的Socket生命周期语义：Ethernet socket上的clearBuffer会停用/关闭socket，inactive时返回-1，后续读写尝试激活。start与controlTask启动路径连续调用clearBuffer且忽略返回值，stop也关闭socket；任务退出时序与重启首帧行为待SRS/CS9验证（SERVO-119–SERVO-125）。未执行HIL或实机验证。

- [2026-11-06 Stäubli Robotics CS9/VAL3/ICube ROS 2生态专项审查](2026-11-06-staubli-robotics-ecosystem-review.md)：静态审查推进至§9.3.51；新增VAL3 sioSet短写/超时处理、手册要求剩余数据续写与当前实现差异、controlTask发送失败STOP/reset路径，以及C++ Boost.Asio send_to忽略字节数、would_block丢包仍返回true的跨端不对称（SERVO-126–SERVO-136）。未执行SRS/CS9网络注入、VAL3编译、HIL或实机验证。

- [2026-11-06 Stäubli Robotics CS9/VAL3/ICube ROS 2生态专项审查](2026-11-06-staubli-robotics-ecosystem-review.md)：静态审查推进至§9.3.54；§9.3.52–§9.3.53审查双向UDP时序、4ms同步任务与overrun；§9.3.54审查CS9系统轨迹/系统IO、用户IO刷新、VAL3同步/异步任务的单CPU扫描顺序，澄清3000行限制并非WCET，分析cyclicRatio与noJitter刷新过载后果。目标cell.cfx/IO模块配置未提供，实际刷新模式未知；GPIO仍为TODO（SERVO-161–SERVO-174）。所有CS9 CPU/IO跟踪、过载注入、HIL/实机验证未执行。


- [2026-11-06 Stäubli Robotics CS9/VAL3/ICube ROS 2生态专项审查](2026-11-06-staubli-robotics-ecosystem-review.md)：静态审查推进至§9.3.55；本轮核对VAL3 SIO timeout=-1、readData双次连续sioGet、0/负返回值错误折叠、sioSet完整帧写入要求，以及状态采集/序列化/发送/接收/运动API/日志共用4ms同步任务片段。源码注释的non-blocking意图不等于CS9实测WCET；未测量SIO调用、socket激活和控制循环尾部延迟（SERVO-175–SERVO-187）。所有SRS/CS9网络注入、任务跟踪、HIL或实机验证未执行。


- [2026-11-06 Stäubli Robotics CS9/VAL3/ICube ROS 2生态专项审查](2026-11-06-staubli-robotics-ecosystem-review.md)：静态审查推进至§9.3.56；本轮核对ROS UDP最新消息快照覆盖、消费者慢读时序号跳跃、旧状态staleness策略、RobotCommand复用最近RobotState序号，以及MSG_DONTWAIT遇would_block后数据包被丢弃但send仍返回true的错误语义。sender身份校验和接收线程优先级/CPU affinity仍有TODO；新增SERVO-188–SERVO-202。突发/慢读/背压/故障注入及CS9/HIL/实机验证均未执行。

- [2026-11-08 Stäubli专项审计记录同步性核查](2026-11-08-staubli-audit-record-synchronization.md)：记录首轮发现的根计划、专项报告、厂商档案、审计索引与00章日志进度差异及各载体SHA；后续已同步专项追加件至§9.3.114、厂商档案至§128.65、审计README及00-01日志，并记录厂商资产清单元数据的两轮单行刷新。附带记录Build Farm/生产APT证据边界；文档同步不代表Stäubli工程验收完成，也不改变00-01进行中状态。

- [2026-11-08 Stäubli MoveIt Servo Jazzy 2.12.4-1发布供应链审计追加件](2026-11-08-staubli-moveit-servo-release-chain-addendum.md)：专项审计已推进至§9.3.120；除rosdistro release ref与上游tag package.xml文件级关联外，新增两架构Jazzy状态页生成时间复核及production main pool源包/二进制目录元数据交叉核对。M仍为10月6日构建；Debian工件正文/哈希、APT签名、testing工件和Jenkins构建日志仍未取得。



- [2026-11-08 Stäubli MoveIt Servo Jazzy 2.12.4-1发布供应链审计追加件](2026-11-08-staubli-moveit-servo-release-chain-addendum.md)：专项审计推进至§9.3.121；补充moveit2-release README发布批次声明、ROS Jazzy双架构状态页再核验及Debian源包读取失败边界。发布声明与release ref关联已核实；源包正文/签名/校验和、Jenkins真实构建日志、APT完整索引与二进制元数据仍未取得。

- [2026-11-08 Stäubli MoveIt Servo Jazzy 2.12.4-1发布供应链审计追加件](2026-11-08-staubli-moveit-servo-release-chain-addendum.md)：专项审计推进至§9.3.122；新增Build Farm Jenkins平台视图存在性核验、source/binary候选job命名公式及具体job访问失败边界；更正production main目录`.orig.tar.gz`大小为65,705 bytes。平台视图可见不等于moveit_servo具体job或构建成功，APT签名/Packages/deb哈希仍未取得。

- [2026-11-08 Stäubli MoveIt Servo Jazzy 2.12.4-1发布供应链审计追加件](2026-11-08-staubli-moveit-servo-release-chain-addendum.md)：专项审计推进至§9.3.123；重读ROS Jazzy amd64/arm64规范状态页，amd64页面刷新至04:56:18 -0800、arm64为04:43:04 -0800；两架构moveit_servo的B/T/M版本字段未变化，Main仍为10月6日旧构建。该记录不代表取得APT正文/验签、deb哈希或Jenkins package job日志。

- [2026-11-08 Stäubli MoveIt Servo Jazzy 2.12.4-1发布供应链审计追加件](2026-11-08-staubli-moveit-servo-release-chain-addendum.md)：专项审计推进至§9.3.124；核对Noble Debian packaging分支的control/changelog/rules/gbp.conf与package.xml依赖映射（25/25）；发现debian/rules可通过nocheck关闭测试，并以dh_auto_test || true容忍测试失败，因此Build Farm构建成功不能作为测试全通过证据。真实deb字段及Jenkins测试日志仍缺。

- [2026-11-08 Stäubli MoveIt Servo Jazzy 2.12.4-1发布供应链审计追加件](2026-11-08-staubli-moveit-servo-release-chain-addendum.md)：新增§9.3.125，记录Noble Debian规则精确行号：rules 20–21通过nocheck关闭BUILD_TESTING，47/53行的dh_auto_test || true吞掉测试命令非零退出；control第5行将若干测试依赖标记<!nocheck>。真实Build Farm环境和console log仍缺，不能判断实际是否运行或通过测试。

- [2026-11-08 Stäubli MoveIt Servo Jazzy 2.12.4-1发布供应链审计追加件](2026-11-08-staubli-moveit-servo-release-chain-addendum.md)：新增§9.3.126，核对build.ros2.org实际部署的ros2/ros_buildfarm_config分支，确认Jazzy Noble amd64/arm64 release配置均关闭package tests；追踪到Build Farm `skip_tests`→`nocheck`→`dpkg-buildpackage -Pnocheck`，并确认MoveIt Servo 2.12.4的三个CMake测试目标由BUILD_TESTING控制。具体job XML/console log及上游其他CI结果仍缺。

- [2026-11-08 Stäubli MoveIt Servo Jazzy 2.12.4-1发布供应链审计追加件](2026-11-08-staubli-moveit-servo-release-chain-addendum.md)：新增§9.3.127，区分ROS Build Farm正式release binary禁测配置与MoveIt上游GitHub Actions/industrial_ci测试路径；记录2.12.4精确源码SHA对应CI run 19975338753整体成功、两个CI矩阵job成功，但逐测试XML未归档。

- [2026-11-08 Stäubli MoveIt Servo Jazzy 2.12.4-1发布供应链审计追加件](2026-11-08-staubli-moveit-servo-release-chain-addendum.md)：新增§9.3.128，记录2.12.4同SHA的5个Actions run与关键job状态；两个industrial_ci CI job及4个其他相关job的日志下载接口均HTTP 410，steps/artifacts不可用，三个Servo测试独立结果仍未取得。

- [2026-11-08 Stäubli MoveIt Servo Jazzy 2.12.4-1发布供应链审计追加件](2026-11-08-staubli-moveit-servo-release-chain-addendum.md)：新增§9.3.129，重新核对Jazzy amd64/arm64状态页（05:56:04/05:43:04 -0800），B/T仍为11月5/6日构建、Main仍为10月6日旧构建；生产main pool仍只列旧二进制。未取得APT索引正文/验签、deb control/SHA256或具体Jenkins job日志，任务状态不变。

- [2026-11-08 Stäubli MoveIt Servo Jazzy 2.12.4-1发布供应链审计追加件](2026-11-08-staubli-moveit-servo-release-chain-addendum.md)：新增§9.3.130，审查MoveIt 2.12.4上游issue #3897与固定源码`stopWorldGeometryMonitor()`的if/else if订阅释放逻辑；静态对应已完成，目标环境复现和Stäubli现场调用链确认仍未执行。另记录Jazzy 2.12.5+发布跟踪issue #3887仍open，不代表新版本已发布。

- [2026-11-08 Stäubli MoveIt Servo Jazzy 2.12.4-1发布供应链审计追加件](2026-11-08-staubli-moveit-servo-release-chain-addendum.md)：新增§9.3.131，核对MoveItCpp通用初始化路径会启动world geometry monitor、当前main stop实现仍保留if/else if缺陷；未发现可确认修复#3897的当前可见PR。仓库缺少ICube应用源码与部署参数，SERVO-722保持未执行/阻塞；补充SERVO-721实验规程但未执行，新增SERVO-724跟踪修复与Jazzy正式发行证据。



- [2026-11-08 Stäubli MoveIt Servo Jazzy 2.12.4-1发布供应链审计追加件](2026-11-08-staubli-moveit-servo-release-chain-addendum.md)：新增§9.3.132，发现MoveIt PR #3907明确Fixes #3897且包含双subscriber单次stop的修复和topic-list回归测试；PR仍open/未合并，Formatting与CI workflow失败且jobs明细不可用。当前上游main仍为旧if/else if实现，Jazzy生产main仍为2.12.4-1，未证明修复进入main/backport/正式deb。

- [2026-11-08 Stäubli MoveIt Servo Jazzy 2.12.4-1发布供应链审计追加件](2026-11-08-staubli-moveit-servo-release-chain-addendum.md)：新增§9.3.131，核对MoveItCpp默认world-geometry启动路径、当前main仍存在的双订阅stop问题及针对#3897的PR搜索；知识库缺少ICube现场源码/部署配置，SERVO-722保持未执行/阻塞，并补齐SERVO-721实验规程和SERVO-724上游修复跟踪。


- [2026-11-08 Stäubli MoveIt Servo Jazzy发布供应链审计追加件](2026-11-08-staubli-moveit-servo-release-chain-addendum.md)：新增§9.3.133，固定MoveIt 2.12.4源码确认startWorldGeometryMonitor先调用stop；初始双topic后restart为`planning_scene_world_topic=""`时旧world subscriber可能保留。澄清对象析构后成员会销毁，不扩大描述为永久泄漏；新增SERVO-725配置切换矩阵，尚未执行动态测试。

- [2026-11-08 Stäubli MoveIt Servo Jazzy 2.12.4-1发布供应链审计追加件](2026-11-08-staubli-moveit-servo-release-chain-addendum.md)：新增§9.3.134，复核候选修复PR #3907仍open且behind，Formatting/CI workflow失败、jobs明细与review approval缺失；未发现Jazzy backport，正式Main二进制仍为2.12.4-1，SERVO-724持续跟踪。

- [2026-11-08 Stäubli MoveIt Servo Jazzy发布供应链审计追加件](2026-11-08-staubli-moveit-servo-release-chain-addendum.md)：新增§9.3.135，通过GitHub连接器独立复核PR #3907的Formatting与CI workflow均completed/failure，两个jobs查询均为空、reviews为空；只确认workflow级失败，具体job/step/原因未知，PR仍Open。SERVO-724继续跟踪，动态验证与现场适用性核验仍未完成。

- [2026-11-08 Stäubli MoveIt Servo Jazzy发布供应链审计追加件](2026-11-08-staubli-moveit-servo-release-chain-addendum.md)：新增§9.3.136，逐行复核PR #3907新增双topic单次stop回归测试：topic-list断言覆盖subscriber移除，但未覆盖发布后回调静默、重复stop、restart、单topic/空topic及octomap矩阵；这些动态验证仍未执行。

- [2026-11-08 Stäubli MoveIt Servo Jazzy发布供应链审计追加件](2026-11-08-staubli-moveit-servo-release-chain-addendum.md)：新增§9.3.137，复核PR #3907仍Open，CodeRabbit提示含Docstring Coverage warning但非维护者审批；Formatting/CI仍失败，Jazzy backport未发现；MoveIt main仍保留双subscriber if/else if stop缺陷。

- [2026-11-08 Stäubli MoveIt Servo Jazzy发布供应链审计追加件](2026-11-08-staubli-moveit-servo-release-chain-addendum.md)：新增§9.3.138，Formatting/CI失败run的jobs与artifacts接口均无可读数据，失败原因未知；不得猜测故障类型，SERVO-724继续跟踪。

- [2026-11-08 Stäubli MoveIt Servo Jazzy发布供应链审计追加件](2026-11-08-staubli-moveit-servo-release-chain-addendum.md)：新增§9.3.139，细化PR #3907修复源码与测试覆盖，并区分双topic活动时直接重配置和显式stop后restart两条生命周期路径；发现当前main在直接切换为仅CollisionObject/双空topic时可能保留旧PlanningSceneWorld subscriber（静态推导，未动态复现）。补充ROS graph与回调计数测试要求，SERVO-725仍未完成动态验证。

- [2026-11-08 Stäubli MoveIt Servo Jazzy发布供应链审计追加件](2026-11-08-staubli-moveit-servo-release-chain-addendum.md)：新增§9.3.140，核对OccupancyMapMonitor初始化顺序、#3902初始化失败被忽略及PR #3909候选修复，并发现#3901接口契约文档与内置插件node_依赖顺序冲突；梳理PointCloud/DepthImage stop实现与U1-U10测试矩阵。现场Octomap配置未确认，动态验证未执行。


- [2026-11-08 Stäubli MoveIt Servo Jazzy发布供应链审计追加件](2026-11-08-staubli-moveit-servo-release-chain-addendum.md)：新增§9.3.141，审查PR #3909将public MiddlewareHandle纯虚接口从void改为bool的下游源码迁移要求，区分源码兼容性与未验证的二进制ABI；补充initialize(false)/setParams(false)后的资源回收契约缺口及SERVO-727 U11-U15验证矩阵。静态审查完成，编译/ABI/动态资源测试未执行。


- [2026-11-08 Stäubli MoveIt Servo Jazzy发布供应链审计追加件](2026-11-08-staubli-moveit-servo-release-chain-addendum.md)：新增§9.3.142，审查PR作者维护的外部MoveIt 2.12.4复现工程，确认两个OccupancyMap场景目录共用同一份旧void签名MiddlewareHandle fixture，并以安装的moveit_ros_occupancy_map_monitor包构建；将其作为U11源码迁移样例，明确不属于独立商业部署或Stäubli现场证据。独立C++17最小override探针已复现conflicting return type；完整fixture迁移编译及ABI测试未执行。


- [2026-11-08 Stäubli MoveIt Servo Jazzy发布供应链审计追加件](2026-11-08-staubli-moveit-servo-release-chain-addendum.md)：新增§9.3.143，核对PR #3909失败初始化测试的shared_ptr所有权，确认测试函数自身保留强引用，故不能证明updater析构/资源回收；fake updater不创建ROS异步资源，且未覆盖setParams(false)。细化SERVO-727 U13/U14测试要求，明确这是覆盖缺口而非已证实泄漏。


- [2026-11-08 Stäubli MoveIt Servo Jazzy发布供应链审计追加件](2026-11-08-staubli-moveit-servo-release-chain-addendum.md)：新增§9.3.144，进一步识别PR #3909失败测试中GMock \`Return(updater)\`动作也可能保留shared_ptr，提出Invoke临时创建对象、weak_ptr/析构计数的U13/U14测试改造，并建立对象、RAII、ROS graph、回调静默、ASan/TSan五层验收；失败原子性/rollback契约仍待上游定义。


- [2026-11-09 Stäubli MoveIt MeshFilter/OpenGL worker生命周期审计追加件](2026-11-09-staubli-moveit-mesh-filter-lifecycle-addendum.md)：新增§9.3.156，静态核查MeshFilter worker初始化/job异常边界、GLRenderer/GLEW失败回滚、FilterJob异常等待和OpenGL context线程归属；新增SERVO-739/J1-J9，全部未执行，不代表Stäubli现场复现或工程验收。


- [2026-11-09 Stäubli DepthImage异步输入缓冲区生命周期审计追加件](2026-11-09-staubli-moveit-mesh-filter-lifecycle-addendum.md)：新增§9.3.157，确认默认异步裸指针与NaN CameraInfo提前return构成条件性悬空指针风险；正常内参路径有后续同步队列屏障。新增SERVO-740/K1-K7，尚未ASan复现或现场验证。


- [2026-11-09 Stäubli MoveIt PointCloud/Octomap生命周期与输入校验审计追加件](2026-11-09-staubli-moveit-mesh-filter-lifecycle-addendum.md)：新增§9.3.158，静态核查PointCloud updater采样参数、PointCloud2字段/行布局、ShapeMask变换失败语义、stop回调静默和OctoMap写异常一致性；新增SERVO-741/L1-L12，全部未执行，未证明Stäubli现场启用或触发。


- [2026-11-09 Stäubli MoveIt OctoMap更新回调与地图服务生命周期审计追加件](2026-11-09-staubli-moveit-mesh-filter-lifecycle-addendum.md)：新增§9.3.159，静态审查OccMapTree回调同步/并发/异常边界、save/load服务捕获this及析构顺序、stopMonitor服务语义、地图锁与磁盘I/O、server序列化失败发布；新增SERVO-742/M1-M12，全部未执行。


- [2026-11-09 Stäubli MoveIt PlanningSceneMonitor OctoMap场景更新与事件回调审计追加件](2026-11-09-staubli-moveit-mesh-filter-lifecycle-addendum.md)：新增§9.3.160，审查scene/tree锁顺序、scene callback递归锁与vector重入、异常通知遗漏、双订阅stop清理缺口和OctoMap回调析构屏障；新增SERVO-743/N1-N12，全部未执行。



- [2026-11-09 Stäubli MoveIt PlanningSceneWorld/CollisionObject失败原子性审计追加件](2026-11-09-staubli-moveit-mesh-filter-lifecycle-addendum.md)：新增§9.3.161，审查CollisionObject ADD/MOVE部分提交、PlanningSceneWorld逐项失败处理、OctoMap错误类型下scene/monitor tree一致性及full/diff空地图语义；新增SERVO-744/M1-M12，全部未执行。



- [2026-11-09 Stäubli MoveIt PlanningSceneMonitor发布线程与订阅端同步审计追加件](2026-11-09-staubli-moveit-mesh-filter-lifecycle-addendum.md)：新增§9.3.162，审查首帧全量快照锁、pending event清零竞态、condition_variable丢唤醒、事件mask与diff累积语义及订阅端恢复；新增SERVO-745/N1-N12，全部未执行。


- [2026-11-09 Stäubli MoveIt GetPlanningScene服务与全量场景同步审计追加件](2026-11-09-staubli-moveit-mesh-filter-lifecycle-addendum.md)：新增§9.3.163，审查GetPlanningScene组件掩码/快照、requestPlanningSceneState返回值、full scene非事务式应用、service/topic乱序及executor同步等待；新增SERVO-746/O1-O12，全部未执行。


- [2026-11-09 Stäubli MoveIt GetPlanningScene调用方与初始化门禁审计追加件](2026-11-09-staubli-moveit-mesh-filter-lifecycle-addendum.md)：新增§9.3.164，审查Servo/RViz/OMPL/场景打印工具/Python绑定调用方的返回值处理、PSM private executor生命周期及同线程同步重入风险；新增SERVO-747/C1-C12，全部未执行。


- [2026-11-09 Stäubli MoveIt Servo碰撞监测启动门禁与场景新鲜度审计追加件](2026-11-09-staubli-moveit-mesh-filter-lifecycle-addendum.md)：新增§9.3.165，沿GetPlanningScene调用方继续审查Servo启动门禁、PSM任意monitor更新时间、CollisionMonitor首轮检查竞态、场景新鲜度缺口、pause恢复及OctoMap默认配置；新增SERVO-748/D1-D14，全部未执行。


- [2026-11-09 Stäubli MoveIt Servo停止状态与下游控制器命令接收边界审计追加件](2026-11-09-staubli-moveit-mesh-filter-lifecycle-addendum.md)：新增§9.3.166，审查HALT_FOR_COLLISION命令发布抑制、ServoStatus与command无确认关联、Trajectory旧轨迹/MultiArray停止语义、pause静默分支；新增SERVO-749/E1-E15，全部未执行。


- [2026-11-09 Stäubli Servo—ros2_control—ICube—VAL3跨层命令生命周期审计追加件](2026-11-09-staubli-moveit-mesh-filter-lifecycle-addendum.md)：新增§9.3.167，使用ICube公开Jazzy/CS9原型源码追踪JTC活动轨迹、controller_manager硬件write、StaubliHardwareInterface UDP发送及VAL3 sequence-delay watchdog。发现Servo topic静默不必然触发机器人端通信看门狗；新增SERVO-750/F1-F16，动态/HIL/现场部署核验均未执行，公开原型不代表现场版本。


- [2026-11-09 Stäubli ICube UDP状态新鲜度、序号单调性与would_block丢包审计追加件](2026-11-09-staubli-moveit-mesh-filter-lifecycle-addendum.md)：新增§9.3.168，发现重复状态报文可刷新本地接收时间但不推进序号，RobotDriver忽略new_message=false；序号倒退被一律当作uint16回绕；UDP would_block丢弃报文却返回true；接收端来源地址校验留有TODO。新增SERVO-751/G1-G16，全部未执行。


- [2026-11-09 Stäubli ICube VAL3同步控制任务overrun与序号延迟看门狗审计追加件](2026-11-09-staubli-moveit-mesh-filter-lifecycle-addendum.md)：新增§9.3.169，审查4 ms `taskCreateSync`、`bIsOverrun`/`nOverruns`仅日志计数、状态序号递增与命令序号回显、sequence_delay非墙钟指标及状态遥测一轮滞后；新增SERVO-752/H1-H16，全部未执行，现场版本/CS9/HIL证据缺失。


- [2026-11-09 Stäubli ICube VAL3 controlTask退出/停止入口与ROS硬件生命周期审计追加件](2026-11-09-staubli-moveit-mesh-filter-lifecycle-addendum.md)：新增§9.3.170，审查stop.pgx未显式停止controlTask、退出标志未发现true赋值、初始化失败直接return、旧命令staleness仍为TODO，以及ROS cleanup/shutdown/error回调停止确认缺口；新增SERVO-753/I1-I16，全部未执行，现场版本/安全链证据缺失。

- [2026-11-09 Stäubli ICube VAL3安全状态来源、运动许可与ROS状态接口语义审计追加件](2026-11-09-staubli-moveit-mesh-filter-lifecycle-addendum.md)：新增§9.3.171，审查isPowered到brakes_released代理映射、esStatus到estop_pressed的非零映射、motion_possible未包含机器人模式门禁及bInError仅为应用本地错误标志；新增SERVO-754/J1-J16，全部未执行，现场安全链证据缺失。

- [2026-11-09 Stäubli ICube VAL3安全状态采样时序、控制周期竞态与ROS状态快照审计追加件](2026-11-09-staubli-moveit-mesh-filter-lifecycle-addendum.md)：新增§9.3.172，审查4 ms同步任务周期配置、状态先采样再收命令/执行、位置控制复用旧安全状态快照、ROS read/write状态年龄门禁缺失及速度控制未实现；新增SERVO-755/K1-K16，全部未执行，现场证据缺失。


- [2026-11-09 Stäubli ICube VAL3停止API语义、movejSync结束调用与停止完成条件审计追加件](2026-11-09-staubli-moveit-mesh-filter-lifecycle-addendum.md)：新增§9.3.173，审查movejSync专用结束API、stopMove/resetMotion立即返回语义、controlTask/stop.pgx复合停止顺序及ROS STOP本地发送与停止确认边界；新增SERVO-756/L1-L16，L1-L15全部未执行，L16现场证据缺失。


- [2026-11-09 Stäubli VAL3控制任务错误锁存、模式转换与故障遥测可见性审计追加件](2026-11-09-staubli-moveit-mesh-filter-lifecycle-addendum.md)：新增§9.3.174，确认controlTask先发送旧错误/模式快照，再处理本轮命令；部分错误可在同周期错误处理后清除，导致RobotState不保证呈现瞬态故障；控制模式切换会进入错误与socket重置路径。新增SERVO-757/M1-M10，M1-M9全部未执行，M10现场证据缺失。


- [2026-11-09 Stäubli控制报文序号重启、旧命令残留与通信重置边界审计追加件](2026-11-09-staubli-moveit-mesh-filter-lifecycle-addendum.md)：新增§9.3.175，审查VAL3错误复位时16位序号归零、ROS订阅器将序号下降视为自然回绕、无新报文时上一命令保持有效、序号差陈旧保护和resetControlSocket不检查操作结果；新增SERVO-758/N1-N10，N1-N9全部未执行，N10现场证据缺失。


- [2026-11-09 Stäubli VAL3应用启动/停止入口、controlTask生命周期与ROS硬件生命周期解耦审计追加件](2026-11-09-staubli-moveit-mesh-filter-lifecycle-addendum.md)：新增§9.3.176，审查VAL3 start.pgx以4 ms周期创建controlTask、stop.pgx未显式等待任务退出，以及ROS connect/disconnect和hardware lifecycle不调用VAL3 start/stop的边界；新增SERVO-759/P1-P10，P1-P9全部未执行，P10现场证据缺失。


- [2026-11-09 Stäubli VAL3工作模式编码、ROS OperationMode枚举与运动许可状态一致性审计追加件](2026-11-09-staubli-moveit-mesh-filter-lifecycle-addendum.md)：新增§9.3.177，识别VAL3 workingMode 0-4与ROS OperationMode 0-3枚举语义不一致、operation_mode_status通用HOLD告警、motion_possible未纳入运行模式、movejSync状态2错误处理被注释及WAIT_FOR_WMS未置位wait_for_ack；新增SERVO-760/Q1-Q10，Q1-Q9未执行，Q10现场证据缺失。


- [2026-11-09 Stäubli VAL3状态快照与命令执行先后、ROS read/write陈旧状态传播审计追加件](2026-11-09-staubli-moveit-mesh-filter-lifecycle-addendum.md)：新增§9.3.178，审查VAL3先发布状态再接收/执行命令、序号延迟和错误遥测跨周期、ROS read拒绝陈旧状态但不显式使缓存失效、write缺少状态年龄/序号二次门禁；新增SERVO-761/R1-R10，R1-R9未执行，R10现场证据缺失。


- [2026-11-09 Stäubli ROS UDP发送成功、VAL3命令接收/执行与状态反馈确认边界审计追加件](2026-11-09-staubli-moveit-mesh-filter-lifecycle-addendum.md)：新增§9.3.179，审查send_robot_command成功仅代表本地序列化/socket send成功、STOP辅助路径使用缓存状态序号且无停止完成确认、VAL3旧命令缓存与序号差陈旧保护、movejSync状态1刷新超时处理被注释，以及速度控制未实现；新增SERVO-762/S1-S10，S1-S9未执行，S10现场证据缺失。


- [2026-11-09 Stäubli ROS关节命令非有限数值、六轴数组边界与限位配置一致性审计追加件](2026-11-09-staubli-moveit-mesh-filter-lifecycle-addendum.md)：新增§9.3.180，审查write()仅拒绝NaN、固定六元素命令数组与num_joints_边界、模型YAML/URDF/MoveIt/R2C接口限值分层、VAL3 isInRange调用及目标距离检查TODO；新增SERVO-763/T1-T10，T1-T9全部未执行，T10现场证据缺失。


- [2026-11-09 Stäubli ROS—VAL3命令float32精度收窄、非有限数值与解码错误传播审计追加件](2026-11-09-staubli-moveit-mesh-filter-lifecycle-addendum.md)：新增§9.3.181，检查double→float32转换、NaN/Inf及溢出门禁、VAL3精确payload长度检查时序、解码后有效标志与STOP/ERROR路径；新增SERVO-764/U1-U10，U1-U8未执行，U9现场IO路径未确认，U10现场证据缺失。


- [2026-11-09 Stäubli VAL3 UDP接收批处理、旧命令缓存与错误恢复边界审计追加件](2026-11-09-staubli-moveit-mesh-filter-lifecycle-addendum.md)：新增§9.3.182，检查每周期双次读取及后报文覆盖、无新报文时旧命令有效标志、sioGet返回值分支、序号陈旧门禁和clearBuffer恢复边界；新增SERVO-765/V1-V10，V1-V9未执行，V10现场证据缺失。


- [2026-11-09 Stäubli ROS/VAL3重启、状态缓存与16位序号会话边界审计追加件](2026-11-09-staubli-moveit-mesh-filter-lifecycle-addendum.md)：新增§9.3.183，审查ROS命令序号回显、disconnect数据重置、latest-message单槽缓存、重复序号处理、16位回绕与控制器重启边界；新增SERVO-766/W1-W10，W1-W9未执行，W10现场证据缺失。


- [2026-11-09 Stäubli ROS UDP接收错误、状态Header校验与latest-message缓存新鲜度审计追加件](2026-11-09-staubli-moveit-mesh-filter-lifecycle-addendum.md)：新增§9.3.184，确认UDP receive error仍进入上层回调、来源地址过滤未实现、反序列化失败保留旧缓存且不刷新时间戳；RobotState解码仅作最小长度与magic校验，未逐帧校验protocol_version/message_type/payload_size及浮点有限性，部分异常帧可刷新缓存后才被上层拒绝。新增SERVO-767/X1-X10，X1-X9全部未执行，X10现场证据缺失。


- [2026-11-09 Stäubli RobotState数值质量、ros2_control状态接口与位置命令初始化审计追加件](2026-11-09-staubli-moveit-mesh-filter-lifecycle-addendum.md)：新增§9.3.185，追踪RobotState非有限关节测量进入硬件状态缓存/导出接口、位置模式切换时状态复制为命令初值、digital/analog valid flag缺失时旧值保留、状态更新非事务性及监督GPIO初始值边界；新增SERVO-768/Y1-Y10，Y1-Y9未执行，Y10现场证据缺失。


- [2026-11-09 Stäubli ros2_control命令模式切换、混合接口解析与GPIO输出缓存生命周期审计追加件](2026-11-09-staubli-moveit-mesh-filter-lifecycle-addendum.md)：新增§9.3.186，审查start_interfaces首项模式解析、stop_interfaces未参与决策、acceleration-only映射STOP与头文件注释差异，以及常规STOP write携带GPIO缓存、cleanup/reconfigure不重置输出命令；固定VAL3原型GPIO执行仍为TODO。新增SERVO-769/Z1-Z10，Z1-Z9未执行，Z10现场证据缺失。

- [2026-11-09 Stäubli VAL3命令序号延迟门禁、STOP/ERROR模式覆盖与通信复位语义审计追加件](2026-11-09-staubli-moveit-mesh-filter-lifecycle-addendum.md)：新增§9.3.187，确认延迟超限/负延迟分支虽记录并赋值STOP，但统一模式提取因l_bError将最终模式覆盖为ERROR，继而触发命令失效、序号复位、控制活动清除及socket重置；新增SERVO-770/AA1-AA10，AA1-AA8未执行，AA9-AA10现场证据缺失。

- [2026-11-09 Stäubli VAL3通信复位、重新接入门禁与旧报文可达性审计追加件](2026-11-09-staubli-moveit-mesh-filter-lifecycle-addendum.md)：新增§9.3.188，审查resetControlSocket仅执行本地SIO参数设置/clearBuffer、controlTask首条完整可解码命令即重新激活、缺少会话epoch/握手/静默等待，以及ROS disconnect/connect仅重建本地socket/subscriber与状态缓存；新增SERVO-771/AB1-AB10，AB1-AB8未执行，AB9-AB10现场证据缺失。

- [2026-11-09 Stäubli VAL3通信复位错误传播、控制任务存活与恢复状态一致性审计追加件](2026-11-09-staubli-moveit-mesh-filter-lifecycle-addendum.md)：新增§9.3.189，确认resetControlSocket正常返回路径无条件清除错误输出，调用方复位失败检查无法捕获其内部操作失败；start.pgx中的监督/诊断任务仍为TODO。新增SERVO-772/AC1-AC10，AC1-AC7和AC10未执行，AC8-AC9现场证据缺失。

- [2026-11-09 Stäubli VAL3启动前置条件、monitor speed与boxcar delay性能门禁审计追加件](2026-11-09-staubli-moveit-mesh-filter-lifecycle-addendum.md)：新增§9.3.190，确认monitor speed低于100时仅记录Warning且等待动作被注释，boxcar delay只读取/记录且滤波器频率设置被注释；固定4 ms控制周期没有与上述前置条件建立显式预算/准入关联。新增SERVO-773/AD1-AD10，动态测试未执行，现场API/配置证据缺失。

- [2026-11-09 Stäubli VAL3控制任务退出条件可达性、重复启动与启停残留状态审计追加件](2026-11-09-staubli-moveit-mesh-filter-lifecycle-addendum.md)：新增§9.3.191，确认controlTask的停止标志是局部变量且固定程序内没有后续置true写入点；stop.pgx未显式终止/等待任务，start.pgx未见同名任务防重入门禁。taskCreateSync同名任务语义及stop→start竞态须目标CS9/VAL3受控验证；新增SERVO-774/AE1-AE10，动态测试未执行，目标版本API和现场编排证据缺失。

- [2026-11-09 Stäubli VAL3启动初始化、overrun计数器与诊断字段可观测性审计追加件](2026-11-09-staubli-moveit-mesh-filter-lifecycle-addendum.md)：新增§9.3.192，确认start.pgx在taskCreateSync前清除bIsOverrun，而nOverruns仅在controlTask主体入口清零并在消费overrun标志时递增；nErrorCode/nInError在固定程序中无读写点，nOverruns也未进入公开RobotState报文。新增SERVO-775/AF1-AF10，AF1固定仓库静态检索完成但现场部署包未核对，AF2目标版本API证据缺失，AF5诊断工具/权限证据缺失，AF9现场证据缺失，其余动态验收未执行。

- [2026-11-09 Stäubli VAL3超周期标志计数语义与ROS控制周期匹配审计追加件](2026-11-09-staubli-moveit-mesh-filter-lifecycle-addendum.md)：新增§9.3.193，确认VAL3默认4ms/250Hz与ROS controller_manager默认250Hz相匹配；TX2-60L MR文档采样周期为1ms，并记录VAL3/ROS同步调整和500Hz/2ms参考。nOverruns仅在循环开头观察到布尔bIsOverrun=true时递增，不能直接代表调度器原生超周期事件数；多次事件是否在布尔标志上合并待目标VAL3动态验证。新增SERVO-776/AG1-AG10，动态验收未执行，目标版本调度器语义及现场型号/配置证据缺失。

- [2026-11-09 Stäubli VAL3控制循环周期预算组成与运动模式分支路径审计追加件](2026-11-09-staubli-moveit-mesh-filter-lifecycle-addendum.md)：新增§9.3.194，沿controlTask调用链审查状态更新/编码发送、UDP收发、位置控制movejSync API、速度控制未实现路径及STOP/ERROR复位分支；确认同一4ms任务内串行执行且分支调用组成不同，源码没有阶段耗时/WCET证据。新增SERVO-777/AH1-AH10，AH1固定提交静态审查完成，AH2目标VAL3 API契约证据缺失，AH3-AH8/AH10未执行，AH9现场证据缺失。


- [2026-11-09 Stäubli CS9同步VAL3任务调度、delay(0)与SIO超时边界审计追加件](2026-11-09-staubli-moveit-mesh-filter-lifecycle-addendum.md)：新增§9.3.195，依据CS9实时任务文档和VAL3参考手册核对4ms同步任务调度、delay(0)让出语义、CPU/IO刷新对周期预算的影响，以及resetControlSocket将运行期socket timeout设为-1后sioGet的非阻塞读取语义；sioSet最大执行时间及目标版本契约仍缺证。新增SERVO-778/AI1-AI10，AI1固定源码静态审查完成；AI2/AI3/AI8需目标版本或现场证据；AI4-AI7、AI10未执行；AI9现场证据缺失。
