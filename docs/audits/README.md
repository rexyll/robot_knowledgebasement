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






- [2026-11-06 Stäubli Robotics CS9/VAL3/ICube ROS 2生态专项审查](2026-11-06-staubli-robotics-ecosystem-review.md)：固定ICube commit静态审查至§9.3.29；新增连接握手/诊断双通道ready审查（§9.3.28，CONN-01–CONN-07）和UDP端口参数严格解析/uint16_t窄化边界（§9.3.29，PORT-01–PORT-05）。未运行构建/单测、参数/网络故障注入、VAL3编译/SRS仿真或CS9 HIL/实机验证。
