---
tags: [SBOM, 软件供应链, 依赖审计, CycloneDX, SPDX]
创建日期: 2026-11-04
更新日期: 2026-11-04
状态: 初始静态基线，非完整 SBOM
---

# 软件供应链与 SBOM 初始基线（2026-11-04）

## 1. 结论与范围

本次建立的是仓库 Python 知识工具包的**声明式依赖基线**，不是产品发布版 SBOM，也不是完整软件物料清单。静态核验对象为根目录 `pyproject.toml`、`LICENSE`、`.github/workflows/ci.yml`、README 与 Python 工具包入口代码。

- 项目：`robot-knowledgebase`，版本 `0.1.0`，Python `>=3.10`。
- 项目声明的运行时依赖：空列表（`dependencies = []`）；当前核心 Markdown loader 使用 Python 标准库。
- 构建依赖：`setuptools>=68`、`wheel`。
- 开发可选依赖：`pytest>=8.0`、`ruff>=0.6`。
- CI：Python 3.10/3.11/3.12 测试矩阵均通过；独立 Python 3.12 SBOM job 分别对 runtime/dev venv 生成 CycloneDX 1.7 并上传 artifact。
- 已检查根目录未找到 `requirements.txt`、`requirements-dev.txt`、`poetry.lock`、`uv.lock`、`Pipfile.lock`、`package-lock.json`。版本范围尚未解析成可复现的确切版本集合。
- GitHub Actions 的 checkout、setup-python 和 upload-artifact 已固定到完整 commit SHA；具体版本见 CI 流水线记录。另一个远程 Rust 源文件使用完整 commit SHA `7aa85e13143594ea4fd4ed9f29e3e29d39b5de85` 下载。
- 根许可证文件声明 MIT；该结论只适用于该许可证文件所覆盖的仓库软件，不自动覆盖索引中列出的第三方项目、模型、数据集、固件、SDK 或产品资产。

**重要区分：** `knowledge/ecosystem/开源项目与工具链.md` 中列出的 ROS 2、PLC、EtherCAT、视觉、SLAM 等项目属于调研候选/生态参考，并非当前 Python 工具包的实际依赖。没有产品 BOM、目标 ROS workspace、容器镜像、目标板卡软件清单和锁定构建产物时，不把这些候选项目写入“已安装/已交付组件”。

## 2. 声明式依赖清单

详见 [软件依赖清单 CSV](2026-11-04-software-dependency-inventory.csv)。每一项都区分依赖作用域、原始声明和解析状态。版本约束（如 `>=8.0`）不是已安装版本；不得将其当作准确版本或 CVE 扫描输入。

| 范围 | 声明 | 当前状态 |
|---|---|---|
| Python 运行时 | 无第三方运行时依赖 | 由 `pyproject.toml` 声明；尚未对所有入口做动态依赖扫描 |
| 构建 | setuptools、wheel | 仅有最低版本约束，未锁定解析版本 |
| 开发/测试 | pytest、ruff | 仅有最低版本约束，未锁定解析版本 |
| CI Action | checkout、setup-python、upload-artifact | 已固定完整 commit SHA；仍需建立升级复核机制 |
| CI 外部源码 | rustypot 指定 commit 的 STS3215 源文件 | 已固定 commit；下载内容仍需校验哈希并归档 |
| ROS/PLC/现场总线候选 | 生态索引中的外部仓库/包 | 仅研究参考；不属于当前 Python package 的 resolved dependency graph |

## 3. SBOM 格式与生成策略

采用 CycloneDX 1.7（ECMA-424）作为本仓库后续 SBOM 的首选交换格式；SPDX 3.0 作为需要更丰富许可证、来源、构建与软件供应链语义时的补充评估格式。CycloneDX 支持组件、服务、依赖关系、许可证及软件/硬件等 BOM 场景；具体输出版本应由工具显式指定并验证。

Python 项目使用 CycloneDX 官方 Python 工具 `cyclonedx-py` 从**实际虚拟环境**生成 BOM。已在 [.github/workflows/ci.yml](../../.github/workflows/ci.yml) 实施独立 runtime/dev/generator 三环境流水线：runtime 与 development 分开扫描，生成器版本固定为 `cyclonedx-bom==7.6.0`，输出 CycloneDX 1.7 JSON，工具内 schema 校验成功，环境 freeze 与 SHA256SUMS 一并上传。首次成功运行与下载复核见 [Python SBOM CI 生成流水线记录](2026-11-04-python-sbom-ci-pipeline.md)。

生成器顶层版本已固定，但其传递依赖仍未使用 hash-locked lockfile；freeze 文件记录本次实际解析版本，不能保证未来解析完全相同。运行环境、开发/测试环境、生成器工具、构建隔离依赖、CI Actions 和外部下载源分别建账，避免将一个 Python 环境 SBOM 误称为整个仓库/产品 SBOM。

## 4. 主要缺口与风险

| ID | 风险/缺口 | 优先级 | 关闭条件 |
|---|---|---|---|
| SBOM-001 | 没有锁文件，依赖仅有下限版本；不同时间构建可能解析出不同版本 | P1 | 选择并提交锁定策略，CI 按锁文件安装，记录哈希 |
| SBOM-002 | CI Action 以 v4/v5 标签引用，未固定完整 commit SHA | P1 | **本轮已实现：** checkout/setup-python/upload-artifact 均固定完整 commit SHA；后续需建立定期升级复核 |
| SBOM-003 | 尚无真实 CI 虚拟环境生成的 CycloneDX JSON | P1 | **已关闭（限定范围）：** CI run #515 成功生成/校验 runtime 与 dev 两份 CycloneDX 1.7，并下载核对 SHA256SUMS；仅覆盖仓库 Python 环境 |
| SBOM-004 | 上游 rustypot 文件虽固定 commit，但未在仓库内记录下载内容 SHA-256/来源快照 | P2 | 记录源 URL、commit、文件 SHA-256、许可与更新责任 |
| SBOM-005 | 生态索引含大量第三方候选项目，未按具体产品配置确认哪些真正集成 | P1 | 形成产品级软件配置清单，逐项标注实际部署、版本、许可证和来源 |
| SBOM-006 | 根目录 MIT 许可不能代表第三方 ROS 包、SDK、模型、数据集和固件许可 | P1 | 对每个实际分发组件完成许可证与再分发条件审查 |
| SBOM-007 | 未执行漏洞匹配、VEX、恶意包/来源完整性和构建溯源审查 | P2 | 对锁定 BOM 运行扫描，人工判定可利用性并保存 VEX/处置记录 |

## 5. 下一阶段执行顺序

1. 确定 Python 依赖锁定工具和 lockfile 策略；不要在未评估兼容性的情况下直接引入新包管理器。
2. 已在 CI 增加 runtime/dev 双环境 CycloneDX 1.7 生成与 artifact 上传；待首次实际运行、下载和复核后关闭 SBOM-003。生成器顶层版本已固定，但传递依赖尚未 hash-lock。
3. 已将 checkout/setup-python/upload-artifact 固定为官方 tag 当前解析到的完整 commit SHA；仍需建立 Action 升级复核机制。
4. 对 ROS 2 workspace 单独采集 `package.xml`、rosdep 解析、vcs import 清单、系统 apt 包、SDK/固件和构建产物；Python SBOM 不覆盖这些内容。
5. 选定一个真实目标机器人配置，汇总 ROS、PLC、EtherCAT、相机、雷达、GPU/BSP、容器和第三方二进制，形成产品级组合 BOM。
6. 在锁定组件上做漏洞与许可证扫描，区分已知漏洞、可利用性、修复版本和分发义务。

## 6. 审计边界

本轮已实际执行 GitHub Actions run #515：Python 3.10/3.11/3.12 测试矩阵均通过，runtime/dev CycloneDX 1.7 生成与 schema 校验成功，artifact 已下载且内部 SHA256SUMS 全部通过。未扫描 CVE、未对第三方许可证形成法律意见，也未对 ROS/PLC/硬件产品配置建立完整 BOM。首次 CI 运行报告见 [Python SBOM CI 生成流水线记录](2026-11-04-python-sbom-ci-pipeline.md)。该记录不构成安全认证或产品发布放行结论。

## 7. 参考资料

- [CycloneDX / ECMA-424 规范与版本概览](https://ecma-international.org/publications-and-standards/standards/ecma-424/)（链接台账 #632）
- [CycloneDX Python 工具用法](https://github.com/CycloneDX/cyclonedx-python/blob/main/docs/usage.rst)（#633）
- [GitHub Actions 安全使用参考](https://docs.github.com/en/actions/reference/security/secure-use)（#634）
- [SPDX 3.0 正式规范入口](https://www.omg.org/spec/SPDX/3.0)（#635）
