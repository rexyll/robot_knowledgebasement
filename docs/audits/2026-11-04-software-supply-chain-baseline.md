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
- 构建依赖：`setuptools>=68`、`wheel`；uv build constraints 固定为 setuptools 84.2.1、wheel 0.48.0、packaging 26.3，均含 SHA-256。
- 开发可选依赖：`pytest>=8.0`、`ruff>=0.6`。
- CI：Python 3.10/3.11/3.12 测试矩阵均通过；独立 Python 3.12 SBOM job 分别对 runtime/dev venv 生成 CycloneDX 1.7 并上传 artifact。
- 根目录 `uv.lock` 已由 uv 0.13.7 生成并提交；记录 11 个 Python package 项及 registry artifact SHA-256，适用 Python `>=3.10`。其他根目录锁文件（requirements/poetry/Pipfile/package-lock）在初始审计时未发现。
- GitHub Actions 的 checkout、setup-python 和 upload-artifact 已固定到完整 commit SHA；具体版本见 CI 流水线记录。另一个远程 Rust 源文件使用完整 commit SHA `7aa85e13143594ea4fd4ed9f29e3e29d39b5de85` 下载，并对 7,434-byte 源文件执行 SHA-256 strict check。
- 根许可证文件声明 MIT；该结论只适用于该许可证文件所覆盖的仓库软件，不自动覆盖索引中列出的第三方项目、模型、数据集、固件、SDK 或产品资产。

**重要区分：** `knowledge/ecosystem/开源项目与工具链.md` 中列出的 ROS 2、PLC、EtherCAT、视觉、SLAM 等项目属于调研候选/生态参考，并非当前 Python 工具包的实际依赖。没有产品 BOM、目标 ROS workspace、容器镜像、目标板卡软件清单和锁定构建产物时，不把这些候选项目写入“已安装/已交付组件”。

## 2. 声明式依赖清单

详见 [软件依赖清单 CSV](2026-11-04-software-dependency-inventory.csv)。每一项都区分依赖作用域、原始声明和解析状态。版本约束（如 `>=8.0`）不是已安装版本；不得将其当作准确版本或 CVE 扫描输入。

| 范围 | 声明 | 当前状态 |
|---|---|---|
| Python 运行时 | 无第三方运行时依赖 | 由 `pyproject.toml` 声明；尚未对所有入口做动态依赖扫描 |
| 构建 | setuptools、wheel | 已由 uv build-constraint-dependencies 精确锁定并提供 hashes |
| 开发/测试 | pytest、ruff | 仅有最低版本约束，未锁定解析版本 |
| CI Action | checkout、setup-python、upload-artifact | 已固定完整 commit SHA；仍需建立升级复核机制 |
| CI 外部源码 | rustypot 指定 commit 的 STS3215 源文件 | commit 与 SHA-256 已固定，CI strict checksum 校验通过；许可证适用性审查仍待完成 |
| ROS/PLC/现场总线候选 | 生态索引中的外部仓库/包 | 仅研究参考；不属于当前 Python package 的 resolved dependency graph |

## 3. SBOM 格式与生成策略

采用 CycloneDX 1.7（ECMA-424）作为本仓库后续 SBOM 的首选交换格式；SPDX 3.0 作为需要更丰富许可证、来源、构建与软件供应链语义时的补充评估格式。CycloneDX 支持组件、服务、依赖关系、许可证及软件/硬件等 BOM 场景；具体输出版本应由工具显式指定并验证。

Python 项目使用 CycloneDX 官方 Python 工具 `cyclonedx-py` 从**实际虚拟环境**生成 BOM。已在 [.github/workflows/ci.yml](../../.github/workflows/ci.yml) 实施 runtime/dev/generator/build-tools 四环境流水线：四个隔离环境分别输出 CycloneDX 1.7 JSON，工具内 schema 校验成功，环境 freeze、许可证元数据候选 CSV 与 SHA256SUMS 一并上传。首次成功运行与下载复核见 [Python SBOM CI 生成流水线记录](2026-11-04-python-sbom-ci-pipeline.md)。

Python 项目 runtime/dev 依赖由 uv.lock 锁定，CI 通过 `uv sync --locked` 验证；CycloneDX generator 的直接和传递依赖由 `requirements-sbom-tools.txt` hash-lock，并通过 `uv pip sync --require-hashes` 验证；PEP 517 build isolation 的 setuptools/wheel 及其传递依赖通过 pyproject.toml 的 `build-constraint-dependencies` 精确约束并记录 SHA-256，uv.lock 同步包含哈希。run #585 的 Python 3.10/3.11/3.12 `uv build --require-build-hashes` 全部通过。运行环境、开发/测试环境、生成器工具、构建隔离依赖、CI Actions 和外部下载源分别建账，避免将一个 Python 环境 SBOM 误称为整个仓库/产品 SBOM。

## 4. 主要缺口与风险

| ID | 风险/缺口 | 优先级 | 关闭条件 |
|---|---|---|---|
| SBOM-001 | Python 项目与 SBOM 工具依赖缺少可复现锁定 | P1 | **已关闭（限定范围）：** 项目 runtime/dev 使用 uv.lock，generator 使用 requirements-sbom-tools.txt 哈希锁，PEP 517 build backend 使用 build constraints + SHA-256；run #551/#566/#585 均通过。产品级依赖不在此范围 |
| SBOM-002 | CI Action 升级与供应链变更缺少定期复核机制 | P2 | checkout/setup-python/upload-artifact 已固定完整 commit SHA；建立版本升级审查与自动提醒后关闭 |
| SBOM-003 | 尚无真实 CI 虚拟环境生成的 CycloneDX JSON | P1 | **已关闭（限定范围）：** CI run #41780128626 生成 runtime/dev/generator/build-tools 四份 CycloneDX 1.7，artifact #13297629985 下载并核对 digest 与 9 项 SHA256SUMS；依赖图完整性 warning 和范围限制见专项报告 |
| SBOM-004 | 上游 rustypot 文件来源完整性与许可证审查 | P2 | **完整性部分已完成：** 固定 URL/commit、7,434-byte 源文件 SHA-256 并纳入 CI 强校验；仓库级 Apache-2.0 LICENSE 已留证。逐文件许可适用性、NOTICE/贡献者与再分发审查、升级责任人仍待完成 |
| SBOM-005 | 生态索引含大量第三方候选项目，未按具体产品配置确认哪些真正集成 | P1 | 形成产品级软件配置清单，逐项标注实际部署、版本、许可证和来源 |
| SBOM-006 | 根目录 MIT 许可不能代表第三方 ROS 包、SDK、模型、数据集和固件许可 | P1 | 对每个实际分发组件完成许可证与再分发条件审查 |
| SBOM-007 | Python 锁定依赖 OSV 匹配已完成一次修复复扫，但首轮 CVE 可利用性/VEX、恶意包/来源风险与产品级扫描未完成 | P2 | 对首轮 6 个 CVE 完成人工可利用性分析/VEX；补充恶意包/来源风险审查，并对真实产品 BOM 扫描 |
| SBOM-008 | PEP 517 build isolation 的 setuptools/wheel 及其传递依赖未 hash-lock | P2 | **已关闭（当前项目构建范围）：** pyproject.toml 精确 pin+SHA-256 build constraints，uv.lock 刷新；run #585 Python 3.10/3.11/3.12 `uv build --require-build-hashes` 均通过 |

## 5. 下一阶段执行顺序

1. **已完成项目 Python runtime/dev 与 PEP 517 build backend 锁定：** uv.lock 记录 runtime/dev package 和 build constraint hashes；pyproject.toml 开启 `require-build-hashes`，run #585 三版本 `uv build --require-build-hashes` 成功；详见 [构建依赖锁定记录](2026-11-04-pep517-build-dependency-lock.md)。
2. **已完成 Python SBOM 自动化与工具链哈希锁定：** runtime/dev/generator/build-tools 四环境 CycloneDX 1.7 生成、schema 校验、artifact 下载复核均成功；generator 34 个 Python 包通过 `--require-hashes` 安装。
3. 已将 checkout/setup-python/upload-artifact 固定为完整 commit SHA；需建立 Action 升级复核机制。
4. 已记录 rustypot STS3215 上游文件 SHA-256，并在 CI 下载后强制校验；许可证适用性审查仍待完成。对 ROS 2 workspace 单独采集 `package.xml`、rosdep 解析、vcs import 清单、系统 apt 包、SDK/固件和构建产物；Python SBOM 不覆盖这些内容。
5. 选定一个真实目标机器人配置，汇总 ROS、PLC、EtherCAT、相机、雷达、GPU/BSP、容器和第三方二进制，形成产品级组合 BOM。
6. 在锁定组件上做漏洞与许可证扫描，区分已知漏洞、可利用性、修复版本和分发义务。

## 6. 审计边界

本轮已实际执行 GitHub Actions run #515、#551、#566、#585、#41780128626、#41780597481 和 OSV 漏洞扫描/复扫 run #41779173369、#41779562839：项目 runtime/dev、generator、PEP 517 build backend 分别采用锁定策略；run #585 Python 3.10/3.11/3.12 的 `uv build --require-build-hashes`、测试和 SBOM job 全部成功。OSV 首轮覆盖 45 个 package/version，发现 generator pip 25.0.1 的 6 个 CVE；升级至 pip 26.3 后复扫返回 0 advisory/0 finding，artifact 已下载核验。首轮 CVE 可利用性/VEX 和第三方许可证法律审查仍未完成，也未对 ROS/PLC/硬件产品配置建立完整 BOM。run #41780128626/#41784066050 的四环境 BOM 与许可证候选 CSV 已下载核验；run #41784066050 修复并直接验证 SHA256SUMS 9 项全部通过。10 条待审 component-scope 记录中，9 条取得版本 tag/commit 与 LICENSE 证据，sortedcontainers 2.4.0 仍缺精确 sdist-to-commit 映射。许可证法律审查均未完成，详见 [Python 许可证元数据审计](2026-11-04-python-license-metadata-audit.md)。详见 [Python 锁定依赖漏洞扫描基线](2026-11-04-python-vulnerability-scan.md)、[Python SBOM CI 流水线](2026-11-04-python-sbom-ci-pipeline.md) 和 [PEP 517 构建隔离依赖哈希锁定记录](2026-11-04-pep517-build-dependency-lock.md)。该记录不构成安全认证或产品发布放行结论。

## 8. 参考资料

- [CycloneDX / ECMA-424 规范与版本概览](https://ecma-international.org/publications-and-standards/standards/ecma-424/)（链接台账 #632）
- [CycloneDX Python 工具用法](https://github.com/CycloneDX/cyclonedx-python/blob/main/docs/usage.rst)（#633）
- [GitHub Actions 安全使用参考](https://docs.github.com/en/actions/reference/security/secure-use)（#634）
- [SPDX 3.0 正式规范入口](https://www.omg.org/spec/SPDX/3.0)（#635）


## 7. Python 锁定依赖漏洞扫描

已新增 [Python 锁定依赖漏洞扫描基线](2026-11-04-python-vulnerability-scan.md) 与标准库脚本 `scripts/audit_python_vulnerabilities.py`。CI 使用独立 job 查询 OSV，覆盖 uv.lock package entries、manifest build constraints、requirements-sbom-tools.txt 和 requirements-build-tools.txt。首轮 OSV 扫描在 45 个 package/version 中发现 generator pip 25.0.1 的 6 个 CVE（12 条 GHSA/PYSEC advisory 记录），已升级至 pip 26.3；复扫已完成，45 个 package/version 返回 0 advisory/0 finding。首轮发现的人工可利用性分诊/VEX、许可证复核及产品级非 Python 组件扫描仍未完成。


## 8. Python 许可证元数据候选审计

run #41780128626 已为 runtime、development、SBOM generator 和 PEP 517 build-tools 四个 CI 环境生成 CycloneDX 1.7 BOM，并从 license metadata 提取 45 条候选记录。10 条包含 classifier/free-text 或 OR expression 的记录已进入人工复核队列；其余 SPDX ID 候选也不能替代逐包上游 LICENSE/NOTICE 核验。CycloneDX 输出存在 root dependency graph incomplete warning，不能将这些环境快照解释为完整依赖图。SBOM-005/006 的产品集成组件/第三方许可证法律审查仍未完成。
