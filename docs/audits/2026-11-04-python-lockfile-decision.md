---
tags: [Python, 依赖锁定, uv, 软件供应链, 可复现构建]
创建日期: 2026-11-04
更新日期: 2026-11-04
状态: uv.lock 已由 CI 生成并提交；三版本 --locked CI 与 SBOM 产物已验证
---

# Python 依赖锁定策略决策（2026-11-04）

## 1. 决策

仓库根 Python 项目采用 **uv 项目锁文件 `uv.lock`** 管理 `pyproject.toml` 中声明的 Python runtime 与开发可选依赖。保留 `pyproject.toml` 中面向开发者的兼容版本范围，不将其改成一串精确版本；通过受版本约束的锁文件记录具体解析结果。

- 锁文件生成器：uv `0.13.7`（2026-11-03 发布）。
- 项目约束：在 `pyproject.toml` 中设置 `tool.uv.required-version = "==0.13.7"`。
- 锁文件：根目录 `uv.lock`，由 uv 生成和维护，不手工编辑。
- CI 安装：使用固定完整 commit SHA 的 `astral-sh/setup-uv`，并明确指定 uv `0.13.7`。
- CI 校验：运行 `uv lock --check` 或 `uv sync --locked`；锁文件缺失或与项目元数据不一致时失败，不允许 CI 静默改写锁文件。
- 测试环境：按 Python 3.10/3.11/3.12 矩阵同步同一 universal lock，并安装 `dev` extra。
- SBOM：从 uv 同步后的 runtime/dev 环境分别生成 CycloneDX 1.7 BOM。

## 2. 选择理由

uv 的 universal resolution 会为项目声明的 Python 版本范围及不同平台解析依赖；锁文件包含具体版本和分发文件哈希，适合提交版本控制并跨机器复现。uv 文档建议将锁文件纳入版本控制，且 `uv sync --locked` 在锁文件需要更新时失败；`uv lock --check` 可独立检查元数据一致性。

选择它而不是仅维护人工编写的 requirements 清单，是因为当前项目已有标准 `pyproject.toml`，依赖范围集中且较少，uv 可直接读取项目元数据和 optional dependencies。

## 3. 范围与例外

`uv.lock` 仅覆盖本仓库 Python 项目的解析依赖，不是完整构建供应链或产品 BOM。以下内容单独管理：

1. PEP 517 build isolation 中的 `setuptools`/`wheel` 及其传递依赖：需要进一步评估 uv build constraints / build hashes，不能假定普通项目依赖锁自动覆盖所有构建隔离安装。
2. CycloneDX generator 工具环境：独立锁定，避免混入目标 runtime/dev BOM。
3. GitHub Actions：继续使用完整 commit SHA。
4. rustypot 上游源文件：使用固定 commit + SHA-256 校验。
5. ROS/OS apt 包、容器、GPU/CUDA、BSP、固件、PLC runtime、厂商 SDK：必须在具体产品配置下另建 BOM。

## 4. 执行与验收

策略决策不等于锁文件已生成。必须完成以下证据后才能关闭 SBOM-001：

- uv 0.13.7 在 CI 实际生成根目录 `uv.lock`，并检查版本、平台/Python marker、包版本和哈希记录。
- 将 `uv.lock` 提交版本控制。
- CI 使用 `uv sync --locked`，三版本矩阵测试通过。
- Runtime/dev CycloneDX BOM 从锁定环境重新生成，组件集合与锁文件解析结果可解释。
- 明确 build-system 与 SBOM generator 环境仍有哪些独立未锁依赖。

## 5. 官方依据

- [uv lockfile 与项目布局](https://docs.astral.sh/uv/concepts/projects/layout/)
- [uv universal resolution](https://docs.astral.sh/uv/concepts/resolution/)
- [uv locking and syncing / --locked](https://docs.astral.sh/uv/concepts/projects/sync/)
- [uv package index hash algorithm](https://docs.astral.sh/uv/concepts/indexes/)
- [uv 0.13.7 release](https://github.com/astral-sh/uv/releases/tag/0.13.7)
- [setup-uv v10.3.3 release](https://github.com/astral-sh/setup-uv/releases/tag/v10.3.3)

## 6. 实际生成与 CI 验证结果

- 锁文件由 GitHub Actions bootstrap run #548 使用 uv 0.13.7 生成；根目录 `uv.lock` 已提交，Git Blob SHA `cb8709dfd8c9cdcaa5e7265cca404d795387553d`，UTF-8 32,892 bytes，203 行。
- 锁文件适用 Python `>=3.10`，记录 11 个 package 项（含本项目、pytest 9.2.0、ruff 0.17.3 和其传递依赖）；registry artifacts 带 SHA-256。
- CI run #551 最终 `completed / success`。Python 3.10/3.11/3.12 均通过 `uv sync --locked --extra dev`、lint、固定上游源码摘要校验和 pytest；SBOM job 的 runtime `uv sync --locked`、development `uv sync --locked --extra dev`、CycloneDX 1.7 生成校验及 artifact 上传全部通过。
- SBOM artifact #13296277606，ZIP 4,330 bytes，digest `sha256:c02bc03264123e5b47151b32b3f11410ce6950fd88d4ff8b1132142a1f37de25`。下载后两份 JSON 均可解析，runtime BOM 1 component/2 dependency entries，development BOM 7 components/8 dependency entries；SHA256SUMS 中 5 个文件全部通过。
- uv 环境使用 `uv pip freeze` 归档，避免 pip 未安装时 freeze 失败；CycloneDX generator 仍独立使用 pip venv。

**范围限制：** 本次可关闭 SBOM-001 对项目 Python runtime/dev 依赖锁定的缺口。PEP 517 build-system 的 setuptools/wheel 解析版本不在这份 uv.lock 的 package graph 内；CycloneDX generator 目前仅固定顶层 `cyclonedx-bom==7.6.0`，传递依赖尚未独立 hash-lock。这两类工具链仍须单独处理。

当前策略与锁文件已落地并通过 CI 验证；构建隔离依赖与 SBOM generator 工具环境仍待锁定。
