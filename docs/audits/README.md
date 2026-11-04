# 审计与资产盘点

本目录记录 Robot Knowledge Basement 的仓库资产、内容质量、来源和公开发布审查。

## 当前记录
- [2026-11-04 SBOM generator 工具链锁定记录](2026-11-04-sbom-generator-toolchain-lock.md)：uv 0.13.7 生成带 SHA-256 的工具依赖锁，CI 使用 `uv pip sync --require-hashes` 安装并通过 run #566。
- [2026-11-04 Python 依赖锁定策略决策](2026-11-04-python-lockfile-decision.md)：选择 uv 0.13.7 与 uv.lock，记录 runtime/dev universal lock、CI --locked 验收及 build/generator 例外；uv.lock 已生成提交，三版本 `uv sync --locked` 与 SBOM 产物复核通过；build/generator 工具链仍需单独锁定。
- [2026-11-04 rustypot 外部源码完整性记录](2026-11-04-external-source-integrity.md)：固定 STS3215 源文件 commit、7,434-byte SHA-256、CI run #534 已在 Python 3.10/3.11/3.12 全矩阵通过摘要校验；上游 Apache-2.0 LICENSE 证据已记录，法律范围仍待审。
- [2026-11-04 Python SBOM CI 生成流水线记录](2026-11-04-python-sbom-ci-pipeline.md)：记录 runtime/dev 双环境 CycloneDX 1.7 生成、工具环境隔离、Actions SHA pinning 与首次 CI 产物核验。
- [ROS 2 产品级 SBOM 采集模板](../templates/ROS2-Product-SBOM-Intake.md)：面向实际机器人产品配置，覆盖 ROS workspace、rosdep/OS、容器、GPU/BSP、固件、厂商 SDK 与 PLC；配套 CSV 为空白采集表，不代表已采集产品 BOM。
- [2026-11-04 软件供应链与 SBOM 初始基线](2026-11-04-software-supply-chain-baseline.md)：记录 Python 工具包的声明式依赖、CI Actions、版本锁定缺口与后续 CycloneDX 生成流程。
- [2026-11-04 软件依赖清单](2026-11-04-software-dependency-inventory.csv)：按运行时、构建、开发、CI、外部源码和生态候选范围登记依赖及解析状态；不是 resolved SBOM。

- [2026-11-03 基线盘点与抽样审计](2026-11-03-baseline-inventory.md)：记录初始基线、代表性内容抽样、当前缺口和优先级队列。
- [2026-11-03 知识资产清单](2026-11-03-knowledge-asset-inventory.csv)：逐项列出 knowledge/ 下 120 份 Markdown 的路径、Git Blob SHA、大小、文件类型、抽样深度、优先级和验收状态。
- [2026-11-03 机器人硬件与安全专项来源补充台账](2026-11-03-robot-safety-source-register.md)：记录标准组织、制造商官方规格页和版本边界。

## 审计状态

- 00-01 全库资产盘点：进行中。
- 结构统计：已建立，清单可从 Git Tree 复算；本轮扫描基线为提交 c00ef1088998c2ac2c2c78778e09f787f64397e4。
- 标题/结构检查：原 112 份知识文件已完成标题、章节结构和开篇检查；此后新增的机械臂入门、故障诊断和桌面机械臂参考项目 7 篇非 README 文档已完成全文结构扫描。
- 全文结构扫描：96/120 份非 README 知识文件已读取并扫描章节、链接、代码、先修、计算/示例、验证、成果物和来源等结构指标；不等于专业审稿或 claim-level 验收。
- README 最近一次扫描：2/24 份目录 README（manipulation、troubleshooting）另做正文结构检查；新增项目 README 已完成内容/结构检查；其余 21 份 README 本轮只刷新 Git 元数据，既有标题/开篇审查历史保留。
- 高风险 P0 定向处理：20/20 份资产已完成边界纠偏或内容修订；具体范围见基线审计第 14–16 节。定向处理不等于全文 claim-level 验收。
- Claim-level 验收：120/120 份知识资产仍未通过完整验收；逐项来源、参数、法规和安全审查仍待完成。
- 外链、参数、标准/法规和安全关键结论：仍需逐项核验。
- 项目公开披露：已对项目案例和首页中的本地绝对路径做首轮脱敏；代码许可证、项目授权和组织关系仍需核验。

## 状态纪律

清单中的未审文件不代表质量不合格，只表示尚无验收证据。抽样不能替代逐篇审查；文件存在、标题完整、链接数量或文章长度均不能单独作为完成证明。审计完成状态以根目录 TaskPlan 的 00-01 任务验收为准。
