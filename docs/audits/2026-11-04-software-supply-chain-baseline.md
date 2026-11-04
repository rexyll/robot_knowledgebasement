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
- 根目录 `uv.lock` 已由 uv 0.13.7 生成并提交；记录 11 个 Python package 项及 registry artifact SHA-256，适用 Python `>=3.10`。其他根目录锁文件（requirements/poetry/Pipfile/package-lock）在初始审计时未发现。
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

Python 项目依赖锁定策略已选择 uv 0.13.7 / uv.lock，决策记录见 [Python 依赖锁定策略](2026-11-04-python-lockfile-decision.md)。当前仍处于锁文件生成和 CI 接入前阶段，不能把策略选择记作 SBOM-001 已关闭。项目 runtime/dev 依赖已由 `uv.lock` 锁定，CI 通过 `uv sync --locked` 验证；CycloneDX generator 的直接和传递依赖已由 `requirements-sbom-tools.txt` hash-lock，并通过 `uv pip sync --require-hashes` 验证。PEP 517 build isolation 的 setuptools/wheel 及其传递依赖仍需单独约束。运行环境、开发/测试环境、生成器工具、构建隔离依赖、CI Actions 和外部下载源分别建账，避免将一个 Python 环境 SBOM 误称为整个仓库/产品 SBOM。

## 4. 主要缺口与风险

| ID | 风险/缺口 | 优先级 | 关闭条件 |
|---|---|---|---|
| SBOM-001 | Python 项目与 SBOM 工具依赖缺少可复现锁定 | P1 | **已关闭（限定范围）：** 项目 runtime/dev 使用 uv.lock；generator 使用 requirements-sbom-tools.txt 哈希锁；run #551/#566 locked sync 均通过。PEP 517 build-system 单列 SBOM-008 |
| SBOM-002 | CI Action 升级与供应链变更缺少定期复核机制 | P2 | checkout/setup-python/upload-artifact 已固定完整 commit SHA；建立版本升级审查与自动提醒后关闭 |
| SBOM-003 | 尚无真实 CI 虚拟环境生成的 CycloneDX JSON | P1 | **已关闭（限定范围）：** CI run #515 成功生成/校验 runtime 与 dev 两份 CycloneDX 1.7，并下载核对 SHA256SUMS；仅覆盖仓库 Python 环境 |
| SBOM-004 | 上游 rustypot 文件来源完整性与许可证审查 | P2 | **完整性部分已完成：** 固定 URL/commit、7,434-byte 源文件 SHA-256 并纳入 CI 强校验；仓库级 Apache-2.0 LICENSE 已留证。逐文件许可适用性、NOTICE/贡献者与再分发审查、升级责任人仍待完成 |
| SBOM-005 | 生态索引含大量第三方候选项目，未按具体产品配置确认哪些真正集成 | P1 | 形成产品级软件配置清单，逐项标注实际部署、版本、许可证和来源 |
| SBOM-006 | 根目录 MIT 许可不能代表第三方 ROS 包、SDK、模型、数据集和固件许可 | P1 | 对每个实际分发组件完成许可证与再分发条件审查 |
| SBOM-007 | 未执行漏洞匹配、VEX、恶意包/来源完整性和构建溯源审查 | P2 | 对锁定 BOM 运行扫描，人工判定可利用性并保存 VEX/处置记录 |
| SBOM-008 | PEP 517 build isolation 的 setuptools/wheel 及其传递依赖未 hash-lock | P2 | 建立独立 build constraints/lock，配置 require-build-hashes，并在 CI 验证干净构建 |

## 5. 下一阶段执行顺序

1. **已完成项目 Python runtime/dev 锁定：** uv 0.13.7 生成并提交 uv.lock，CI run #551 三版本 `uv sync --locked` 成功；决策与验证见 [文档](2026-11-04-python-lockfile-decision.md)。
2. 已在 CI 增加 runtime/dev 双环境 CycloneDX 1.7 生成与 artifact 上传；待首次实际运行、下载和复核后关闭 SBOM-003。生成器顶层版本已固定，但传递依赖尚未 hash-lock。
3. 已将 checkout/setup-python/upload-artifact 固定为完整 commit SHA；需建立 Action 升级复核机制。
4. 已记录 rustypot STS3215 上游文件 SHA-256，并在 CI 下载后强制校验；许可证适用性审查仍待完成。对 ROS 2 workspace 单独采集 `package.xml`、rosdep 解析、vcs import 清单、系统 apt 包、SDK/固件和构建产物；Python SBOM 不覆盖这些内容。
5. 选定一个真实目标机器人配置，汇总 ROS、PLC、EtherCAT、相机、雷达、GPU/BSP、容器和第三方二进制，形成产品级组合 BOM。
6. 在锁定组件上做漏洞与许可证扫描，区分已知漏洞、可利用性、修复版本和分发义务。

## 6. 审计边界

本轮已实际执行 GitHub Actions run #515 和 #551：#515 建立初始 SBOM 流水线；#551 使用 uv.lock 锁定 runtime/dev 环境，Python 3.10/3.11/3.12 测试、源文件摘要校验、CycloneDX 1.7 生成/校验均成功，artifact 已下载且 SHA256SUMS 全部通过。未扫描 CVE、未对第三方许可证形成法律意见，PEP 517 build isolation 仍未锁定，也未对 ROS/PLC/硬件产品配置建立完整 BOM。首次 CI 运行报告见 [Python SBOM CI 生成流水线记录](2026-11-04-python-sbom-ci-pipeline.md)；外部源码摘要和许可证证据见 [rustypot 外部源码完整性记录](2026-11-04-external-source-integrity.md)。该记录不构成安全认证或产品发布放行结论。

## 7. 参考资料

- [CycloneDX / ECMA-424 规范与版本概览](https://ecma-international.org/publications-and-standards/standards/ecma-424/)（链接台账 #632）
- [CycloneDX Python 工具用法](https://github.com/CycloneDX/cyclonedx-python/blob/main/docs/usage.rst)（#633）
- [GitHub Actions 安全使用参考](https://docs.github.com/en/actions/reference/security/secure-use)（#634）
- [SPDX 3.0 正式规范入口](https://www.omg.org/spec/SPDX/3.0)（#635）
