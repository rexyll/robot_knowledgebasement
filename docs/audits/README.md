# 审计与资产盘点

- [2026-11-04 Python 锁定依赖漏洞扫描基线](2026-11-04-python-vulnerability-scan.md)：OSV API 批量查询 uv.lock、PEP 517 build constraints、SBOM generator 与 build-tools 锁；首轮扫描发现 SBOM generator pip 25.0.1 的 6 个 CVE，已升级 pip 26.3；run #41779562839 对 45 个 package/version 复扫为 0 advisory/0 finding，扫描范围不等于机器人产品级漏洞审计。

本目录记录 Robot Knowledge Basement 的仓库资产、内容质量、来源和公开发布审查。

## 当前记录

- [2026-11-11 Stäubli SocketV2 RACE/EXEC Test Case Catalog 与双向追踪验收](2026-11-11-staubli-socket-v2-race-exec-test-case-catalog.md)：新增RACE-01–16与EXEC-01–04共20项机器可读测试规格及Schema；为28条Manifest记录补齐所有20项测试引用的正向/反向映射，新增fail-closed双向校验器、负向测试和CI报告归档。CI #3477在Python 3.10/3.11/3.12全部通过，每个版本67项测试通过；所有测试case仍为NOT_RUN，C++/ROS/plugin/HIL/实机未执行。

- [2026-11-11 Stäubli SocketV2 Lifecycle Manifest Validator 与 CI 自动化验收](2026-11-11-staubli-socket-v2-manifest-validator-ci-integration.md)：新增依赖零的专用JSON Schema关键词子集校验器、28项Manifest资源代际Owner/Coordinator分组约束、20项RACE/EXEC引用完整性、Status/Evidence policy、负向测试与CLI退出码；GitHub Actions CI #3462在Python 3.10/3.11/3.12全部通过，每个版本58项测试通过并归档校验报告。该校验器不是通用完整Draft 2020-12实现；Stäubli C++/ROS/插件/HIL/实机验证仍NOT_RUN。

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


- [2026-11-09 Stäubli ROS—UDP—VAL3双向报文名义流量与MTU边界审计追加件](2026-11-09-staubli-moveit-mesh-filter-lifecycle-addendum.md)：新增§9.3.196，基于RobotState 132 B、RobotCommand 55 B及双向名义250 Hz建立单会话500 datagrams/s、46.75 kB/s应用层负载模型；按IPv4/UDP/Ethernet II并计FCS、前导码/SFD与IFG估算约638 kbit/s线速占用，理论数据报160 B/83 B低于常见1500 B MTU。明确不代表现场网络性能；新增SERVO-779/AJ1-AJ10，AJ1静态算术基线完成，AJ2/AJ4-AJ5/AJ9待配置/现场证据，AJ3/AJ6-AJ8/AJ10未执行。


- [2026-11-09 Stäubli ROS 2 C++ API默认UDP端口与VAL3部署配置一致性审计追加件](2026-11-09-staubli-moveit-mesh-filter-lifecycle-addendum.md)：新增§9.3.197，核对C++ API默认端口8080/8081与VAL3 SIO、Xacro及文档端口11000/11001差异；标准Xacro路径显式注入11000/11001，直接使用RobotDriver便捷重载/默认NetworkConfig存在配置错配风险。新增SERVO-780/AK1-AK10，AK1-AK7静态核对完成，AK8未执行，AK9/AK10缺部署/现场证据。

- [2026-11-09 Stäubli RobotDriver首次状态就绪、连接等待循环与超时边界审计追加件](2026-11-09-staubli-moveit-mesh-filter-lifecycle-addendum.md)：新增§9.3.198，区分UDP socket/接收线程ready与首个有效新鲜RobotState；确认连接循环每500ms采样、首次成功后不提前退出、最终只看末次采样，HardwareInterface配置路径传入5000ms，现有mock测试没有连接时延断言。新增SERVO-781/AL1–AL10，AL1–AL8静态审查完成，AL9未执行，AL10缺现场证据。


- [2026-11-09 Stäubli状态新鲜度、控制模式准入与诊断通道首帧验证审计追加件](2026-11-09-staubli-moveit-mesh-filter-lifecycle-addendum.md)：新增§9.3.199，核对is_connected不检查RobotState新鲜度、read失败保留旧状态缓存、on_activate仅设STOP并成功返回、JOINT_POSITION切换读取缓存状态但无独立时间戳门禁；诊断subscriber仅检查socket/接收线程ready，connect将diag_interface_ready硬编码true且不读取首个诊断帧，固件版本日志不能证明诊断有效。新增SERVO-782/AM1–AM10，AM1–AM7静态核对完成，AM8未执行，AM9缺部署配置，AM10缺现场/HIL证据。


- [2026-11-09 Stäubli RobotDriver状态新鲜度阈值API取值与并发更新审计追加件](2026-11-09-staubli-moveit-mesh-filter-lifecycle-addendum.md)：新增§9.3.200，核对state/diagnostic staleness setter默认100ms但无零/负值/超大值范围校验；零/负值会使所有消息判stale，过大值可能放宽旧缓存接受窗口，duration字段无mutex/atomic使运行期并发修改成为条件性数据竞争。新增SERVO-783/AN1–AN10，AN1–AN6静态核对完成，AN7–AN9未执行，AN10缺现场证据。


- [2026-11-09 Stäubli RobotDriver 16位序号回绕、乱序帧与重连重同步审计追加件](2026-11-09-staubli-moveit-mesh-filter-lifecycle-addendum.md)：新增§9.3.201，发现16位序号回绕丢包公式多计1；较小序号未区分回绕和乱序，旧帧可能覆盖新缓存并回退RobotDriver状态序号；disconnect/reconnect会重置本地跟踪，但协议缺少session/boot epoch。新增SERVO-784/AO1–AO10，AO1–AO7静态核对完成，AO8–AO9未执行，AO10缺目标部署/现场证据。

- [2026-11-09 Stäubli RobotDriver消息状态输出初始化与订阅器线程安全契约审计追加件](2026-11-09-staubli-moveit-mesh-filter-lifecycle-addendum.md)：新增§9.3.202，确认MessageStatus无首帧失败路径未初始化lost_packages且可能保留旧time_since_received；read_message虽声明thread-safe，但first_read_/last_read_sequence_number_未同步，多读者并发属于条件性API风险。新增SERVO-785/AP1–AP10，AP1–AP6静态核对完成，AP7–AP8未执行，AP9–AP10缺部署/现场证据。

- [2026-11-09 Stäubli UDP接收线程停止、重启与异步接收生命周期审计追加件](2026-11-09-staubli-moveit-mesh-filter-lifecycle-addendum.md)：新增§9.3.203，确认stop只停止io_service而未显式取消挂起接收，重启时可能叠加异步接收；接收error仍无条件进入用户回调并可能继续重投递。新增SERVO-786/AQ1–AQ10，AQ1–AQ7静态核对完成，AQ8–AQ9未执行，AQ10缺目标部署/现场证据。


- [2026-11-09 Stäubli UDP来源验证、报文长度与协议头字段边界审计追加件](2026-11-09-staubli-moveit-mesh-filter-lifecycle-addendum.md)：新增§9.3.204，核对UDP sender_endpoint_来源过滤、RobotState/RobotCommand/DiagnosticData长度与头字段校验。发现接收端未验证来源IP/端口；反序列化未统一要求精确帧长；RobotState缺类型/版本/payload_size校验，RobotCommand缺协议版本校验，DiagnosticData在解析网络头前校验默认header字段，FrameHeader只检查magic。新增SERVO-787/AR1–AR10，AR1–AR9静态核对完成，AR10缺目标部署网络配置及隔离验证证据。


- [2026-11-09 Stäubli UDP数值合法性、枚举范围与状态缓存污染审计追加件](2026-11-09-staubli-moveit-mesh-filter-lifecycle-addendum.md)：新增§9.3.205，核对float/NaN/Inf反序列化、状态/命令/诊断枚举范围、未知状态位、subscriber缓存提交及硬件状态更新。发现浮点解码无finite检查、枚举直接static_cast、监督状态直接导出、硬件层无机型物理范围校验；update_state可能先写位置后因速度字段缺失返回false而留下部分更新。新增SERVO-788/AS1–AS10，AS1–AS8静态核对完成，AS9需机型限值依据，AS10缺隔离验证。

- [2026-11-09 Stäubli状态新鲜度、控制许可与读写周期一致性审计追加件](2026-11-09-staubli-moveit-mesh-filter-lifecycle-addendum.md)：新增§9.3.206。发现状态过期时read返回ERROR但硬件state_msg_保留旧值；is_connected不检查staleness，write无独立状态年龄/read成功门禁；活动模式write只检查error_state和control_state INVALID，mode switch无新鲜度门禁且HOLD仅警告。新增SERVO-789/AT1–AT10，AT1–AT8静态核对完成，AT9–AT10需隔离运行时及现场安全证据。

- [2026-11-09 Stäubli控制命令生成、限幅、接口映射与异常发送审计追加件](2026-11-09-staubli-moveit-mesh-filter-lifecycle-addendum.md)：新增§9.3.207。发现驱动发送路径无显式关节限值校验；write仅检查NaN不覆盖Inf；轴数未限制为协议6轴且超6时NaN检查存在固定数组越界路径；混合接口按第一个匹配项决定模式；模拟IO和controller_period缺少驱动侧范围/有限性门禁；STOP非零参考仅warning后仍发送。新增SERVO-790/AU1–AU10，AU1–AU9静态核对完成，AU10需隔离边界验证。

- [2026-11-09 Stäubli命令UDP发送可靠性审计追加件](2026-11-09-staubli-moveit-mesh-filter-lifecycle-addendum.md)：新增§9.3.208。发现UDP would_block时数据报被丢弃但UDPSocketImpl::send仍返回true，导致send_message/send_robot_command及硬件write可能误报成功；无背压计数/阈值；RealTimeSocketInterface复用data_out_且无发送互斥（并发调用尚未证实）；blocking文档与MSG_DONTWAIT实现不一致；命令序号沿用最近有效状态序号，协议意图待CS9确认。新增SERVO-791/AV1–AV10，AV1–AV9静态核对完成，AV10需错误注入及CS9/HIL验证。

- [2026-11-09 Stäubli命令序号关联与确认闭环审计追加件](2026-11-09-staubli-moveit-mesh-filter-lifecycle-addendum.md)：新增§9.3.209。发现hardware write命令序号复用最近一次有效机器人状态序号；协议MessageType未定义独立ACK/command-result，send_robot_command不等待控制器接收/接受/执行确认；状态subscriber只跟踪状态帧序号，不关联待确认命令；未发现命令ACK超时、重发、去重或重连清理状态机。命令序号协议意图需CS9/VAL3规范确认。新增SERVO-792/AW1–AW10，AW1–AW9静态核对完成，AW10需协议规范及CS9/HIL证据。

- [2026-11-10 Stäubli GPIO型号配置校验与Xacro递归边界审计追加件](2026-11-10-staubli-gpio-configuration-validation-addendum.md)：新增§9.3.263 / SERVO-846，确认Xacro模型配置校验未覆盖GPIO数量schema、GPIO递归宏以相等作为终止条件、C++ std::stoul未检查完整字符串消费；非法输入边界及Xacro展开未执行。

- [2026-11-10 Stäubli GPIO接口导出、状态更新与生命周期缓存一致性审计追加件](2026-11-10-staubli-gpio-interface-lifecycle-audit.md)：新增§9.3.264 / SERVO-847，静态核对Xacro与C++接口命名/类别一致；发现GPIO输入字段缺失时保留旧值且read仍可能成功、生命周期激活未重置GPIO输出命令缓存而write在STOP模式仍发送输出；需mock与生命周期测试验证。

- [2026-11-10 Stäubli GPIO协议端到端映射、有效性标志与VAL3执行链审计](2026-11-10-staubli-gpio-protocol-end-to-end-audit.md)：新增§9.3.265 / SERVO-848，确认VAL3每周期将数字/模拟输入valid flag设为false、状态GPIO payload序列化未实现；命令方向数字位图到VAL3数组转换被注释，controlTask数字/模拟物理输出仍为TODO。C++往返单测不覆盖跨语言协议；未执行golden frame、VAL3/CS9、SIL/HIL或实机验证。

- [2026-11-10 Stäubli GPIO物理IO API、型号通道映射与异常输出状态审计](2026-11-10-staubli-gpio-physical-io-mapping-safety-audit.md)：新增§9.3.266 / SERVO-849，固定VAL3工程未见数字/模拟IO读写API，Libraries为空；SIO配置仅含UDP/串口，TX2-60L与MED仅声明16/16/2/2数量而无模块/槽位/端子映射；STOP/ERROR/断线及应用停止未定义GPIO安全态，GPIO文档仍为Coming soon。sio.cfx文本末尾疑似XML未闭合，待VAL3导入器验证；未执行CS9、SIL/HIL或实机测试。

- [2026-11-10 Stäubli ROS 2—VAL3通信故障传播、任务调度与恢复闭环审计](2026-11-10-staubli-control-communication-fault-recovery-audit.md)：新增§9.3.267 / SERVO-850，确认VAL3旧命令staleness检查仍为TODO、序号延迟门禁仅在控制活动时运行、resetControlSocket不检查底层复位结果却清除错误标志；ROS连接就绪与状态新鲜度分离，未发现自动重连/会话握手闭环；软件STOP无停止回执，VAL3 GPIO物理输出仍未实现。仅静态审查，未执行CS9/网络故障注入或SIL/HIL/FAT/SAT。

- [2026-11-10 Stäubli ROS 2—断线恢复、会话重同步与命令/状态序号新鲜度审计](2026-11-10-staubli-reconnect-session-sequence-freshness-audit.md)：新增§9.3.268 / SERVO-851，确认Subscriber对每份成功解码数据报刷新接收时间，相同序号的new_message=false未被RobotDriver作为状态拒绝门禁；较小序号一律按uint16回绕处理，缺少乱序/重放窗口和会话epoch；断开重连重置本地subscriber序号基线但无会话连续性握手；现有恢复测试未执行driver disconnect/reconnect。重复帧刷新新鲜度为静态推断，未动态复现。

- [2026-11-10 Stäubli ROS 2—诊断数据通道、控制器状态反馈与安全状态语义审计](2026-11-10-staubli-diagnostic-state-feedback-audit.md)：新增§9.3.269 / SERVO-852，确认connect阶段诊断ready被硬编码为true、未调用read_diagnostic_data且固件版本打印读取默认值；固定VAL3工程未发现诊断帧发送端；DiagnosticData header校验顺序错误；SafetyStatus被压缩为estop_pressed、制动释放由drive power推导，GPIO invalid时保留旧缓存。仅静态审查，未执行畸形帧/CS9/现场验证。

- [2026-11-10 Stäubli ROS 2—协议字段映射、枚举语义、单位与边界值一致性审计](2026-11-10-staubli-protocol-field-mapping-enum-units-audit.md)：新增§9.3.270 / SERVO-853，确认VAL3 encodeHeader将序号重复写入payload_size、OperationMode跨语言数值错位、float64转float32及NaN/Inf边界缺口、F/T与GPIO字段未完整编码。HardwareInterface的rad↔deg转换静态一致；CS9互操作与边界测试未执行。

- [2026-11-10 Stäubli ROS 2—VAL3命令帧入口校验与无效命令处理审计](2026-11-10-staubli-val3-command-frame-ingress-validation-audit.md)：新增§9.3.271 / SERVO-854，确认VAL3 decodeRobotCommandMsg在解析wire header前使用旧对象字段检查长度，decodeHeader未校验wire payload_size，55 B实际帧携带错误payload声明时可能仍被接受；header/type错误早退未在decoder内立即清除旧bIsValid。C++端有47 B payload检查而VAL3端缺失；未执行畸形帧/CS9动态验证。

- [2026-11-10 Stäubli ROS 2—VAL3命令语义、控制周期与数值边界校验审计](2026-11-10-staubli-command-semantic-period-numeric-validation-audit.md)：新增§9.3.272 / SERVO-855，确认remote control period虽解码但未进入控制周期校验/执行闭环；VAL3命令类型范围门禁与真实支持分支不一致；位置目标跳变检查、速度限值/执行仍未实现；模拟输出入口缺少finite/量程检查；现有控制周期测试值0.008与“8 ms”注释不一致。仅静态审查，未执行构建、异常注入、CS9/SIL/HIL或实机验证。

- [2026-11-10 Stäubli ROS 2—控制错误传播、停止路径与恢复授权审计](2026-11-10-staubli-control-error-recovery-authorization-audit.md)：新增§9.3.273 / SERVO-856，确认VAL3运行时错误在状态发布后产生并在同轮清除，存在bInError不可观测风险；resetControlSocket不检查底层调用结果且无条件返回成功；速度模式更新错误分支缺少专用停止调用；恢复等待/人工确认/重新授权仍为TODO；C++ on_error忽略STOP发送结果。仅静态审查，未执行ROS逐周期观测、CS9停止/恢复注入或安全验证。


- [2026-11-10 Stäubli ROS 2—控制状态反馈、模式语义与故障恢复一致性审计](2026-11-10-staubli-state-feedback-recovery-consistency-audit.md)：新增§9.3.274 / SERVO-857，核对VAL3状态位→C++ RobotState→ROS supervision接口映射；发现状态快照先于本轮命令处理、无有效命令可出现INVALID与in_error=false并存、错误复位后直接运动模式重入可能被守卫拦截而需要先STOP重武装、重复序号仍可能刷新接收时间、stale read未向状态接口提供显式invalid标志。仅静态审查，未执行跨语言golden frame、恢复故障注入、CS9/安全链、SIL/HIL/FAT/SAT或实机验证。


- [2026-11-10 Stäubli ROS 2—状态有效性、STOP确认与跨层生命周期故障恢复验收设计](2026-11-10-staubli-lifecycle-stop-confirmation-acceptance-audit.md)：新增§9.3.275 / SERVO-858，确认on_error返回SUCCESS后生命周期按Humble契约进入UNCONFIGURED，但插件未disconnect/reset缓存；STOP发送结果与回调成功脱钩；cleanup/shutdown缺少可靠停止确认；位置模式切换未检查状态新鲜度；read失败不失效缓存。更正现有HardwareInterface测试覆盖边界：LifecycleTransitions未调用prepare/perform，write仍走STOP路径且没有mock命令回读。新增LFA-01至LFA-14验收设计；所有测试未执行。


- [2026-11-10 Stäubli ROS 2—STOP命令接收确认与状态反馈关联协议审计](2026-11-10-staubli-stop-command-ack-sequence-correlation-audit.md)：新增§9.3.276 / SERVO-859，确认本地send成功不是远端ACK；RobotCommand序号回显最近RobotState序号而非独立command ID；协议无STOP ACK/命令结果字段；VAL3未见去重、乱序拒绝和session epoch；重复状态数据报会刷新接收时间，可能续新鲜度。新增ACKT-01至ACKT-13验收矩阵，均未执行。


- [2026-11-10 Stäubli ROS 2—UDP接收缓存、序号回绕与重复/乱序数据报新鲜度专项审计](2026-11-10-staubli-udp-cache-sequence-freshness-audit.md)：新增§9.3.277 / SERVO-860，确认C++ Subscriber使用单值最新缓存、重复序号帧仍刷新本地接收时间、序号倒退被无条件当作uint16回绕并污染基线、UDP来源地址检查仍为TODO；VAL3 readData每周期最多两次sioGet且第二帧可能覆盖第一帧；另发现UDP send遇到would_block明确丢包却返回true，可能导致上层误报STOP/命令成功。新增RX-01至RX-14验收矩阵，均未执行。


- [2026-11-10 Stäubli ROS 2—UDP协议输入可信边界与状态数据完整性审计](2026-11-10-staubli-udp-protocol-trust-boundary-integrity-audit.md)：新增§9.3.278 / SERVO-861，确认UDP sender_endpoint来源过滤未启用、接收error仍进入回调；C++ FrameHeader只校验magic，RobotState/RobotCommand/DiagnosticData的版本/类型/payload长度校验不统一，DiagnosticData解析前使用对象默认header字段；VAL3检查magic/version但不校验payload_size；协议缺少消息认证与session epoch/抗重放机制，ROS状态层未暴露来源认证和协议拒绝原因。新增UT-01至UT-15验收矩阵，全部未执行。


- [2026-11-10 Stäubli ROS 2—状态有效性与通信安全诊断接口端到端审计](2026-11-10-staubli-ros2-state-validity-diagnostic-propagation-audit.md)：新增§9.3.279 / SERVO-862，确认RobotDriver读失败/过期时不统一失效内部状态对象；HardwareInterface::read返回ERROR但不清除已导出的joint/supervision缓存；update_state可能部分写入形成混合周期快照；模式切换与write未独立检查状态新鲜度；supervision接口缺少validity/source/auth/error诊断字段；诊断ready仍硬编码true。新增SV-01至SV-16验收矩阵，全部未执行。


### §9.3.280｜SERVO-863：ros2_control硬件错误传播、Controller Manager与生命周期状态转换契约审计

- **固定审查基线：** Stäubli `ICube-Robotics/staubli_driver_ros2@bd658e2d266e315d2ee35f985fb352ea88306b79`；ros2_control Jazzy `c6ef5a24e0cd21463edb99bded552a96f914b716`。
- **审计报告：** [2026-11-10-staubli-ros2-control-manager-error-lifecycle-contract-audit.md](2026-11-10-staubli-ros2-control-manager-error-lifecycle-contract-audit.md)。
- **范围：** Stäubli HardwareInterface生命周期回调、read/write错误返回、RobotDriver连接/STOP路径；ros2_control HardwareComponent、ResourceManager、ControllerManager及现有测试。
- **静态结论：**
  1. read/write ERROR触发HardwareComponent error/on_error，并由ResourceManager撤销故障硬件接口。
  2. Stäubli on_error在driver connected时忽略STOP发送返回值并返回SUCCESS，硬件进入UNCONFIGURED；driver断线时返回ERROR，硬件进入FINALIZED。
  3. on_error未disconnect或执行cleanup；UNCONFIGURED后socket/接收线程可能保持连接，下一次configure时connect才先断开旧连接。
  4. ResourceManager撤销接口后，ControllerManager仍尝试故障组件mode switch；接口不可用及组件生命周期状态不满足，导致prepare阶段因接口不可用而拒绝；perform通常因逻辑AND短路不执行，其生命周期门禁也不允许UNCONFIGURED/FINALIZED组件。该顺序与ros2_control上游Issue #3620记录一致，属于框架交互边界。
  5. Stäubli现有测试没有覆盖真实ResourceManager/ControllerManager错误传播、接口撤销、控制器停用、FINALIZED和恢复重载。
- **LC-01至LC-15状态：** 验收矩阵已建立，全部未执行。
- **整改要求：** 明确可恢复/不可恢复错误分级；让STOP尝试结果和生命周期结果可观测但不把UDP STOP当作安全功能；定义on_error后的socket/线程/缓存/session清理；验证目标Jazzy二进制版本和ControllerManager故障路径。
- **状态：** 固定提交静态审计完成；断线FINALIZED恢复策略、STOP发送结果与生命周期SUCCESS脱钩、on_error资源清理和故障mode-switch交互存在P0/P1缺口；未修改上游、未应用PR；`TODO-EXT-001`未授权合并。
- **下一节点：** §9.3.281 / SERVO-864。


### §9.3.281｜SERVO-864：硬件错误恢复状态机与故障注入验收设计

- [2026-11-10 Stäubli ROS 2 硬件错误恢复状态机与故障注入验收设计](2026-11-10-staubli-ros2-hardware-error-recovery-state-machine-fault-injection-design.md)：在固定 Stäubli 与 ros2_control Jazzy 提交上，设计 RUNNING→ERROR_DETECTED→STOP_REQUESTED→接口撤销→UNCONFIGURED/FINALIZED→重连→SESSION_VALIDATING→INACTIVE→ACTIVE 恢复状态机；区分本地 STOP 发送、控制器 ACK、运动停止观测和独立安全链安全确认。当前协议无独立 STOP ACK/command ID，ROS/UDP STOP 不得视为安全功能。新增 SERVO864-FI-01 至 FI-24 故障注入矩阵及 AC-01 至 AC-10 验收准则；全部运行时项目未执行，未修改上游或应用 PR。


### §9.3.282｜SERVO-865：硬件错误恢复实现映射与最小接口契约

- [2026-11-10 Stäubli ROS 2 硬件错误恢复实现映射与最小接口契约](2026-11-10-staubli-ros2-hardware-error-recovery-implementation-mapping.md)：固定 Stäubli commit `bd658e2d266e315d2ee35f985fb352ea88306b79` 静态映射 RobotDriver、StaubliHardwareInterface、UDP socket、实时收发接口及现有测试。确认 UDP send 遇到 `would_block` 时日志报告 packet dropped 却仍返回 true，属于优先修正的 P0 发送结果语义缺口；并识别重复/乱序序号未拒绝、来源 endpoint 校验 TODO、on_error 不 disconnect、STOP 依赖缓存状态、状态快照未整体失效、诊断首帧未实际读取和并发契约不足。定义最小接口契约及 UT/IT 测试映射。仅静态分析，未修改上游、未执行任何测试。


### §9.3.283｜SERVO-866：UDP 发送结果契约与状态帧接纳门禁专项设计

- [2026-11-10 Stäubli ROS 2 UDP 发送结果契约与状态帧接纳门禁专项设计](2026-11-10-staubli-udp-send-result-and-state-frame-admission-contract.md)：固定 Stäubli commit `bd658e2d266e315d2ee35f985fb352ea88306b79` 静态核对 UDP `would_block` 丢包却返回 true 的发送路径、异步接收错误回调、sender endpoint TODO、重复/乱序序号及消息反序列化校验。定义 `NOT_SENT` / `LOCAL_ACCEPTED` / `UNKNOWN` 发送结果；定义 endpoint、精确长度、帧头/字段、16-bit 半空间序号、freshness、generation 和原子快照接纳契约。新增 TX-01至TX-09、RX-01至RX-15、IT-01至IT-06测试规格及 AC-866-01至AC-866-10。仅静态审查和设计，所有测试未执行，未修改上游、未应用 PR。


### §9.3.284｜SERVO-867：UDP 故障注入测试夹具与 Mock Socket seam 架构设计

- [2026-11-10 Stäubli UDP 故障注入测试夹具与 Mock Socket seam 架构设计](2026-11-10-staubli-udp-fault-injection-test-harness-and-mock-seam-design.md)：定义窄 `IUdpTransport` / `IMonotonicClock` seam、Mock 与 loopback UDP fixture、确定性事件脚本、datagram/frame/state builder、并发屏障、ROS 2 Control 集成层及不可覆盖的证据归档。所有 UT/IT/SYS 均 NOT_RUN，seam 未实现；未修改上游或应用 PR。下一节点 §9.3.285 / SERVO-868。


### §9.3.285｜SERVO-868：CMake/gtest 测试结构与最小 seam 增量实施方案

- [2026-11-10 Stäubli CMake/gtest 测试结构与最小 seam 增量实施方案](2026-11-10-staubli-cmake-gtest-seam-minimal-increment-plan.md)：基于固定 commit 核对现有 `Socket` 抽象、RobotDriver 构造依赖、Subscriber 时钟调用、UDPSocket PIMPL 与 CMake/gtest 注册。建议首轮复用 `Socket` 注入 FakeSocket，不另建平行 UDP 抽象；为 Subscriber 注入可控时钟；沿用 `add_unit_test`。列出文件级方案和 SEAM/FS/CLK/IT 矩阵。仅静态审查和设计，所有测试 NOT_RUN，未修改上游或应用 PR。下一节点 §9.3.286 / SERVO-869。


### §9.3.286｜SERVO-869：FakeSocket 接口契约与生命周期/线程安全设计

- [2026-11-10 Stäubli FakeSocket 接口契约与生命周期/线程安全设计](2026-11-10-staubli-fake-socket-contract-lifecycle-thread-safety.md)：覆盖 Socket 全部虚函数、独立 FIFO 脚本、fail-closed 默认、手动 callback dispatch、stop/cancel/join 屏障、事件日志快照和 FS-01至FS-22 测试矩阵。明确当前 Socket 接口无法模拟 error_code、sender endpoint 和真实 Asio cancellation。仅静态审查与设计，所有测试 NOT_RUN，Fake 尚未实现，未修改上游或应用 PR。下一节点 §9.3.287 / SERVO-870。


### §9.3.287｜SERVO-870：FakeSocket 状态机伪代码与 AAA 测试矩阵

- [2026-11-10 Stäubli FakeSocket 状态机伪代码与 AAA 测试矩阵](2026-11-10-staubli-fakesocket-pseudocode-and-aaa-test-matrix.md)：将 FakeSocket 状态变量、合法转换、connect/send/receive/start/stop/disconnect 伪代码、锁与 RAII callback guard、stop/deliver 线性化点、事件日志快照和 FS-01至FS-22 Arrange/Act/Assert 逐项细化。明确 stop 失败仍须清理、callback 异常清理后传播、self-stop 拒绝及测试层级边界。全部测试 NOT_RUN，Fake 未实现，未修改上游或应用 PR。下一节点 §9.3.288 / SERVO-871。


### §9.3.288｜SERVO-871：RobotDriver / Subscriber fixture 生命周期与集成测试映射

- [2026-11-10 Stäubli RobotDriver / Subscriber fixture 生命周期与集成测试映射](2026-11-10-staubli-robotdriver-subscriber-fixture-lifecycle-integration-map.md)：基于固定 Stäubli commit 核对 RobotDriver 双 Socket 所有权、connect/disconnect 顺序、Subscriber 构造启动接收、裸 this callback、析构 stop 屏障及现有测试 fixture。将 FS-01至FS-22映射到生产路径，设计 F0至F4 fixture 分层并新增 SD-01至SD-10调用方测试规格。仅静态审查与设计，全部测试 NOT_RUN，未修改上游或应用 PR。下一节点 §9.3.289 / SERVO-872。


### §9.3.289｜SERVO-872：RobotDriver connect/disconnect 回滚路径故障注入矩阵

- [2026-11-10 Stäubli RobotDriver connect/disconnect 回滚路径故障注入矩阵](2026-11-10-staubli-robotdriver-connect-disconnect-rollback-fault-matrix.md)：固定上游 `bd658e2d266e315d2ee35f985fb352ea88306b79` 静态核对双 Socket connect 阶段、control connect false 直接返回、Subscriber 构造异常无 rollback、diagnostics 失败路径、disconnect stop/disconnect 顺序、空析构及旧会话清理。新增 RB-01至RB-08、SD-07A至E、SD-08、SD-10A至B 精确故障注入规格。仅静态审查与设计，全部运行时测试 NOT_RUN，未修改上游或应用 PR。下一节点 §9.3.290 / SERVO-873。


### §9.3.290｜SERVO-873：RobotDriver 事务式 connect rollback guard 最小补丁设计

- [2026-11-10 Stäubli RobotDriver 事务式 connect rollback guard 最小补丁设计](2026-11-10-staubli-robotdriver-transactional-connect-rollback-guard-design.md)：固定上游 `bd658e2d266e315d2ee35f985fb352ea88306b79` 静态核对 RobotDriver/Subscriber/Interface/Socket，定义 ConnectAttempt 状态、attempt-before-side-effect、commit/fail/exception、统一 cleanup 顺序、CleanupReport、异常优先级和 residual 检查。提出 Socket false/partial-state 与幂等契约、Subscriber 两阶段 factory、旧 session/并发/generation/destructor 策略；GUARD-01至GUARD-10、P0至P7 全部 NOT_RUN/NOT_IMPLEMENTED。仅设计，未修改上游或应用 PR。下一节点 §9.3.291 / SERVO-874。


### §9.3.291｜SERVO-874：Socket / Subscriber 初始化与清理契约 API 设计

- [2026-11-10 Stäubli Socket / Subscriber 初始化与清理契约 API 设计](2026-11-10-staubli-socket-subscriber-init-cleanup-contract-api.md)：固定上游静态复核 Socket bool API、UDP PIMPL、Subscriber 构造启动线程/裸 this callback/析构 stop。明确 API 操作结果与资源快照分离；TransportState/ReceiveState 独立建模；connect/disconnect/stop 失败与残留状态语义；幂等 stop 的 callback admission、pending handler、active callback、worker join 屏障；Subscriber 两阶段 start/stop、析构 noexcept best-effort、CleanupReport 和旧 API 兼容迁移策略。新增 API-01至API-18，全部 NOT_RUN；接口未实现，未修改上游或应用 PR。下一节点 §9.3.292 / SERVO-875。


### §9.3.292｜SERVO-875：Socket v2 兼容迁移与 UDP 状态观测实现切片设计

- [2026-11-10 Stäubli Socket v2 兼容迁移与 UDP 状态观测实现切片设计](2026-11-10-staubli-socket-v2-compatibility-and-udp-observability-slice-design.md)：确认旧 Socket 是纯虚接口，增加 virtual 会改变 vtable；建议保留旧接口/工厂并新增 SocketV2/SocketFactoryV2 与独立 UDPSocketV2 façade、唯一 UDP Core。确认当前 CMake 主库仅编译 UDP wrapper，TCP factory 明确 unsupported，测试仅实例化 UDP。设计 Asio native handle/local endpoint/thread joinable 与应用侧 handler/callback 计数快照、connect 阶段记录、cancel/drain/join、timeout owner 保留及 V2-0至V2-5迁移切片。V2-API-01至V2-CMAKE-02全部NOT_RUN；未实现、未修改上游或应用PR。下一节点 §9.3.293 / SERVO-876。


### §9.3.293｜SERVO-876：SocketV2 public header / ABI surface 与 UDP Core ownership 设计审查

- [2026-11-10 Stäubli SocketV2 public header / ABI surface 与 UDP Core ownership 设计审查](2026-11-10-staubli-socket-v2-public-header-abi-and-udp-core-ownership-design.md)：逐符号审查 legacy Socket/UDPSocket public API、PIMPL、CMake install/export 与 package metadata。提出独立 v2 public headers、private Core、visibility/export macro 与 ABI policy；区分同工具链 C++ source API 和稳定 binary ABI；默认 legacy facade 保持独立，v2 façade 独占 Core，明确 callback/worker shutdown、timeout owner 保留和 factory Result 契约。ABI-0至ABI-5切片、ABI-01至ABI-16全部NOT_RUN；未实现、未修改上游或应用PR。下一节点 §9.3.294 / SERVO-877。


- [2026-11-10 Stäubli SocketV2 header dependency closure、public type layout 与 factory Result API C++17 编译契约审查](2026-11-10-staubli-socket-v2-header-dependency-result-contract-audit.md)：新增§9.3.294 / SERVO-877，细化public headers自包含与include closure、C++17自定义FactoryResult（不使用std::expected）、固定uint32_t enum值、PIMPL incomplete-type析构位置及install-space standalone consumer fixture。HDR-01至HDR-07、TYPE-01至TYPE-04、RES-01至RES-04、ABI-17至ABI-18全部NOT_RUN；本轮未读取上游文件正文，沿用SERVO-876已记录的固定文件清单与blob事实；未执行编译/测试、未修改上游或应用PR。


- [2026-11-10 Stäubli SocketV2 Result 错误分类、异常安全与资源残留 / Quarantine Owner 生命周期契约审查](2026-11-10-staubli-socket-v2-result-error-exception-safety-residual-owner-lifecycle-audit.md)：新增§9.3.295 / SERVO-878，定义primary failure与cleanup failure分离、native error/exception记录、FAILED_RESIDUAL owner保留、quarantine owner、按generation串行化的retry_cleanup、noexcept边界及RobotDriver/Subscriber集成约束。ERR-01至ERR-24全部NOT_RUN；仅静态设计，未实现或修改上游，未运行编译/测试/实机验证。


### §9.3.296｜SERVO-879：SocketV2 CleanupReport / ResidualResourceHandle API surface 与 quarantine ownership 实施边界设计

- [2026-11-10 Stäubli SocketV2 CleanupReport / ResidualResourceHandle API surface 与 quarantine ownership 实施边界设计](2026-11-10-staubli-socket-v2-cleanup-report-residual-handle-api-quarantine-boundary-design.md)：提出C++17 public/private类型边界、纯值FailureRecord/NativeError/Snapshot/CleanupReport DTO、move-only ResidualResourceHandle、显式TransportLifecycleOwner/QuarantineManager、generation retry状态机、Core清理串行化及RobotDriver/ROS lifecycle/plugin unload门禁。API-OWN-01至10、RETRY-01至06、ROS-01至05、ERR-ALLOC-01至02全部NOT_RUN；仅静态设计，未实现或修改上游，未执行编译/测试。下一节点 §9.3.297 / SERVO-880。


### §9.3.297｜SERVO-880：SocketV2 QuarantineManager shutdown contract、有界重试调度与 process/plugin teardown 资源释放策略设计

- [2026-11-10 Stäubli SocketV2 QuarantineManager shutdown contract、有界重试调度与 process/plugin teardown 资源释放策略设计](2026-11-10-staubli-socket-v2-quarantine-manager-shutdown-bounded-retry-process-plugin-teardown-design.md)：定义manager关闭状态机、entry/manager双层有界重试预算、monotonic deadline、容量/并发/队列上限、ProcessLifecycleOwner进程关闭协议、residual/forced-exit分类及ROS component/plugin unload屏障。QM-SHUT、RETRY-BND、PROC-SHUT、PLUGIN、THREAD-EXIT验收矩阵全部NOT_RUN；仅静态设计，未实现或修改上游，未执行编译/测试。下一节点 §9.3.298 / SERVO-881。


### §9.3.298｜SERVO-881：SocketV2 QuarantineManager / RetryScheduler concurrency model、lock ordering、executor integration 与 deterministic shutdown race test design

- [2026-11-10 Stäubli SocketV2 QuarantineManager / RetryScheduler concurrency model、lock ordering、executor integration 与 deterministic shutdown race test design](2026-11-10-staubli-socket-v2-quarantine-retry-concurrency-lock-order-executor-shutdown-race-design.md)：定义并发角色、M/E/S/C/L锁域与M->E->S唯一嵌套顺序、锁外cleanup/callback/executor/join、attempt token与generation/revision fencing、owner transfer prepare/commit、executor停止与completion fallback，以及RACE-01至16、LOCK-01至02、EXEC-01至04确定性测试规格。所有验收NOT_RUN；仅静态设计，未实现或修改上游，未执行编译/测试。下一节点 §9.3.299 / SERVO-882。


### §9.3.299｜SERVO-882：SocketV2 cleanup transaction 幂等性、generation fencing、partial-step recovery 与 native resource close ordering formalization

- [2026-11-10 Stäubli SocketV2 cleanup transaction 幂等性、generation fencing、partial-step recovery 与 native resource close ordering formalization](2026-11-10-staubli-socket-v2-cleanup-transaction-idempotency-generation-fencing-partial-recovery-native-close-ordering.md)：定义transaction identity与step journal、幂等副作用分类、generation/revision/attempt-token fencing、partial-step recovery、UNKNOWN隔离/reconcile策略、native资源依赖关闭候选顺序及POSIX close平台语义边界。TX-IDEM-01至05、GEN-FENCE-01至04、PART-REC-01至04、CLOSE-ORD-01至10全部NOT_RUN；仅静态设计，未实现或修改上游，未执行编译/测试。下一节点 §9.3.300 / SERVO-883。


### §9.3.300｜SERVO-883：SocketV2 cleanup dependency DAG validation、platform-specific native close semantics evidence matrix 与 residual resource reconciliation policy

- [2026-11-10 Stäubli SocketV2 cleanup dependency DAG validation、platform-specific native close semantics evidence matrix 与 residual resource reconciliation policy](2026-11-10-staubli-socket-v2-cleanup-dag-platform-close-semantics-residual-reconciliation.md)：定义资源依赖DAG节点/边、owner/barrier完整性、环检测/可达性/版本绑定；整理Linux close、POSIX标准版本、Apple历史文档和Windows Winsock closesocket语义差异；定义residual状态分类、平台probe与owner保留/升级reconciliation策略。DAG-01至04、LINUX-01至04、POSIX-01至02、MAC-01、WIN-01至04、RES-01至06全部NOT_RUN；真实driver DAG尚未从源码提取，平台adapter未实现。下一节点 §9.3.301 / SERVO-884。


### §9.3.301｜SERVO-884：SocketV2源码级资源所有权、close-site追踪与真实依赖DAG

- [2026-11-10 Stäubli SocketV2源码级资源所有权、close-site追踪与真实依赖DAG](2026-11-10-staubli-socket-v2-source-resource-ownership-close-site-traceability-real-dag.md)：固定上游commit逐文件提取RobotDriver双Socket shared ownership、UDPSocket unique_ptr PIMPL、Asio socket/io_service/buffer/thread/callback、两层裸this回调及HardwareInterface/plugin teardown关系；定位open/close/disconnect/destructor/stop/join sites。发现close异常后connected标志仍清零、析构/RobotDriver可能跳过显式close重试、Subscriber析构忽略stop结果、join无timeout/self-join检查；TCP实现文件未出现在固定tree且CMake不编译TCP wrapper。SRC-OWN/CLOSE-TRACE/DAG-REAL静态项已核对，运行时项目全部NOT_RUN；Boost.Asio内部native close细节UNKNOWN。未修改上游或应用PR。


### §9.3.302｜SERVO-885：SocketV2 source-to-test coverage gap、teardown failure-path matrix与最小验证切片

- [2026-11-10 Stäubli SocketV2 source-to-test coverage gap、teardown failure-path matrix与最小验证切片](2026-11-10-staubli-socket-v2-source-to-test-coverage-teardown-failure-matrix-minimal-slices.md)：固定上游commit测试映射覆盖CMake、UDP socket loopback、RT subscriber/interface、RobotDriver、HardwareInterface/plugin及MockRobotServer测试。确认正常收发/connect/disconnect/reconnect/double start-stop/lifecycle基础路径已有测试；close失败注入、native状态核验、callback并发销毁/异常、self-join/timeout、双通道partial teardown、ROS cleanup/shutdown/error失败矩阵及plugin unload竞态均无覆盖。定义F01–F16故障矩阵和Slice A–F最小验证顺序。静态映射已完成；FAIL-MATRIX与SLICE-ORDER为SPECIFIED；RUN-01至RUN-08全部NOT_RUN，未修改上游。


### §9.3.315｜SERVO-898：确定性 Fake Harness 与 Runtime Evidence Bundle

- [2026-11-11 Stäubli SocketV2 确定性 Fake Harness 接口与 Runtime Evidence Bundle 设计](2026-11-11-staubli-socket-v2-deterministic-fake-harness-runtime-evidence-bundle-design.md)：定义FakeClock、Barrier/Latch、DeterministicExecutor、FaultScript、Event Trace、Resource Snapshot、环境身份和SHA-256工件契约；新增Runtime Evidence Bundle Schema与NOT_RUN示例、专用fail-closed validator及CI报告归档。Fake/C++/ROS运行测试仍NOT_RUN，未修改上游或应用PR；A1.1仍BLOCKED。下一节点§9.3.316 / SERVO-899。
