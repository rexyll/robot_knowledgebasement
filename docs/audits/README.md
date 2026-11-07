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
- [2026-11-03 知识资产清单](2026-11-03-knowledge-asset-inventory.csv)：逐项列出 knowledge/ 下 142 份 Markdown 的路径、Git Blob SHA、大小、文件类型、抽样深度、优先级和验收状态。
- [2026-11-03 机器人硬件与安全专项来源补充台账](2026-11-03-robot-safety-source-register.md)：记录标准组织、制造商官方规格页和版本边界。

## 审计状态

- 00-01 全库资产盘点：进行中。
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
