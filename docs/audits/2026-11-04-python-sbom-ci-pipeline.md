# Python SBOM CI 与依赖锁定流水线记录

> 日期：2026-11-04  
> 状态：项目 Python runtime/dev、CycloneDX generator 与 PEP 517 build backend 已分别锁定；四环境 CycloneDX 1.7 BOM 与许可证元数据候选抽取 CI 实测通过。  
> 范围：仓库 Python 包及 CI Python 工具链，不代表 ROS 2/机器人产品 BOM。

## 1. CI 工作流

`.github/workflows/ci.yml` 包含 Python 3.10/3.11/3.12 测试矩阵与独立 Python 3.12 SBOM job。

测试矩阵执行：
1. 使用固定 SHA 的 checkout/setup-python/setup-uv Actions。
2. `uv sync --locked --extra dev` 按根目录 uv.lock 安装项目及开发依赖。
3. `uv build --require-build-hashes` 实际构建 sdist/wheel，并强制校验 PEP 517 隔离构建依赖哈希。
4. 执行 ruff、固定 commit 的 rustypot 源码 SHA-256 校验和 pytest。

SBOM job 分别创建 runtime、development、generator 和 PEP 517 build-tools 四个独立环境：
- runtime/dev：uv 0.13.7 + `uv sync --locked`，各自生成 CycloneDX 1.7 JSON。
- generator：无 pip 初始 venv，通过 `uv pip sync --require-hashes` 安装独立哈希锁定的 CycloneDX 工具链（pip 26.3）。
- build-tools：无 pip 初始 venv，通过 `uv pip sync --require-hashes` 安装 PEP 517 build 工具锁。
- 对四份 BOM 运行标准库提取器，生成 45 条许可证元数据候选 CSV；归档四个环境的 freeze、四份 BOM、候选 CSV 和 SHA256SUMS，artifact 保留 30 天。

主要产物：
- `robot-knowledgebase-runtime.cdx.json`
- `robot-knowledgebase-development.cdx.json`
- `robot-knowledgebase-generator.cdx.json`
- `robot-knowledgebase-build-tools.cdx.json`
- `python-license-metadata-candidates.csv`
- `runtime-python-freeze.txt`
- `development-python-freeze.txt`
- `generator-tool-freeze.txt`
- `build-tool-freeze.txt`
- `SHA256SUMS`

## 2. 锁定策略与文件

| 作用域 | 锁文件/配置 | 锁定范围 | CI 验证 |
|---|---|---|---|
| 项目 runtime/dev | `uv.lock` | Python >=3.10；项目和开发依赖精确版本、registry artifact hashes | `uv sync --locked --extra dev`，Python 3.10/3.11/3.12 |
| SBOM generator | `requirements-sbom-tools.in/.txt` | 34 个包，含 cyclonedx-bom 7.6.0、pip 26.3 及传递依赖的 SHA-256 | `uv pip sync --require-hashes` |
| PEP 517 build backend | `requirements-build-tools.in/.txt`、`pyproject.toml`、`uv.lock` | setuptools 84.2.1、wheel 0.48.0、packaging 26.3；6 个 distribution SHA-256 | `uv build --require-build-hashes`，Python 3.10/3.11/3.12 |

`pyproject.toml [tool.uv]` 设置 `require-build-hashes = true`，并通过 `build-constraint-dependencies` 记录精确版本和 hashes。uv.lock 已刷新并包含这些 build constraint hashes。升级 uv 时必须重新验证该功能，因为 uv 文档将 require-build-hashes 标注为实验性。

## 3. 固定的 GitHub Actions

| Action | 固定 commit SHA |
|---|---|
| actions/checkout | `11d5960a326750d5838078e36cf38b85af677262` |
| actions/setup-python | `a26af69be951a213d495a4c3e4e4022e16d87065` |
| astral-sh/setup-uv | `68559e99cc807c1eb7e9238fd43a15bba460eec2` |
| actions/upload-artifact | `ea165f8d65b6e75b540449e92b4886f43607fa02` |

uv 二进制版本固定为 0.13.7。升级 Actions 时应重新解析官方 tag/ref 并审查发布说明、权限范围。

## 4. CI 运行与下载产物证据

### Run #515：初始 SBOM 流水线

[GitHub Actions run #515](https://github.com/rexyll/robot_knowledgebasement/actions/runs/41773062051)，最终 success。Python 3.10/3.11/3.12 测试矩阵、CycloneDX 1.7 BOM 生成与校验、artifact 上传均通过。Artifact #13295617233，ZIP 4,602 bytes，digest `sha256:5e3a760bfb1ec34f7cd9bc4ac646e2983291270499efc94a70dc3db7361f8393`。

### Run #551：项目 runtime/dev uv.lock 接入

[GitHub Actions run #551](https://github.com/rexyll/robot_knowledgebasement/actions/runs/41774325434)，最终 success。Python 3.10/3.11/3.12 的 locked sync、lint、测试及 SBOM job 均通过。uv.lock 包含 11 个项目/runtime/dev package 项和 PyPI artifact SHA-256。Artifact #13296277606，ZIP 4,330 bytes，digest `sha256:c02bc03264123e5b47151b32b3f11410ce6950fd88d4ff8b1132142a1f37de25`。

### Run #566：SBOM generator 传递依赖哈希锁定

[GitHub Actions run #566](https://github.com/rexyll/robot_knowledgebasement/actions/runs/41774740672)，最终 success。generator venv 使用 `uv pip sync --require-hashes` 安装 34 个包，包含 CycloneDX generator、pip 和传递依赖。Artifact #13296392548，ZIP 4,328 bytes，digest `sha256:53096815cf1963cc624aaebb495218ddd30124e19bdb64a9551ded206d7c2306`。

### Run #585：PEP 517 build isolation 哈希锁定

[GitHub Actions run #585](https://github.com/rexyll/robot_knowledgebasement/actions/runs/41777632096)，最终 `completed / success`。Python 3.10/3.11/3.12 均通过 `uv sync --locked --extra dev`、`uv build --require-build-hashes`、ruff、rustypot 源文件 SHA-256 校验及 pytest；SBOM job 也成功。Artifact #13298086142，ZIP 4,328 bytes，digest `sha256:706a8bd3be5cde5d2fc34aa47b7c129354f694abae458b832107dab78046742b`。

Run #585 artifact 已实际下载：
- Runtime BOM：CycloneDX 1.7，1 component、2 dependency entries。
- Development BOM：CycloneDX 1.7，7 components、8 dependency entries。
- 两份 JSON 均可解析，metadata root 均为 `robot-knowledgebase`。
- ZIP 内 SHA256SUMS 的 5 个文件全部校验通过。

### Run #41780128626：四环境 SBOM 与许可证元数据候选抽取

[GitHub Actions run #41780128626](https://github.com/rexyll/robot_knowledgebasement/actions/runs/41780128626)，最终 success；Python 3.10/3.11/3.12 测试矩阵、OSV 复扫、四环境 SBOM job 全部通过。Artifact #13297629985，12,856 bytes，digest `sha256:4df21e05e03904055ebcf53c1756842c8f93aff50f59670d566f37fe56e12ed5`。下载后 ZIP SHA-256 与 GitHub digest 一致。后续对新 artifact 的独立检查发现：上传时 artifact 将 `sbom/` 目录扁平化，但 `SHA256SUMS` 仍写入 `sbom/` 前缀，故在解压目录直接运行 `sha256sum -c SHA256SUMS` 会因路径不存在失败；逐项去除该前缀后，9 个文件的实际 SHA-256 均与清单一致。已修复 CI 清单生成路径，见 run #41783904623 后续修复记录。

- Runtime BOM：1 component / 2 dependency entries。
- Development BOM：7 components / 8 dependency entries。
- Generator BOM：34 components / 35 dependency entries。
- PEP 517 build-tools BOM：3 components / 4 dependency entries。
- `python-license-metadata-candidates.csv`：45 条 component-scope 记录，覆盖四个环境；35 条 SPDX ID 候选、3 条 SPDX expression、3 条 classifier/free-text、4 条 SPDX ID 与 classifier 混合，0 条缺少 license metadata。
- 提取器与人工复核队列见 [Python SBOM 许可证元数据候选审计](2026-11-04-python-license-metadata-audit.md)。

CycloneDX CLI 对部分环境 BOM 输出 root component 缺少直接依赖、dependency graph 不完整的 warning。四份 JSON 均通过 1.7 schema validation；本次将其作为环境组件与许可证 metadata 快照，不将其解释为完整依赖关系图。

### Run #41783904623：许可证证据更新后的 CI 与 artifact 复核

[GitHub Actions run #41783904623](https://github.com/rexyll/robot_knowledgebasement/actions/runs/41783904623)，最终 success；Python 3.10/3.11/3.12、OSV 与四环境 SBOM jobs 全部通过。Artifact #13300332133，12,856 bytes，GitHub digest `sha256:03f9310578c31ea8f9d7e9678fe44a7bad9366f098c44305dd4c0c53adc9f377`。已下载，ZIP SHA-256 与 digest 一致；四份 CycloneDX 1.7 JSON 可解析，component/dependency entries 分别为 runtime 1/2、development 7/8、generator 34/35、build-tools 3/4；许可证候选 CSV 45 行，0 条缺失。

此次独立验证发现 artifact flattening 与 checksum 路径不一致：ZIP 中文件位于根目录，而 `SHA256SUMS` 内路径仍为 `sbom/<file>`。直接 `sha256sum -c SHA256SUMS` 因路径不匹配失败；逐项去除 `sbom/` 前缀后，9 个实际文件摘要全部匹配。该问题是清单路径错误，不是文件内容摘要不一致。

已在 CI workflow 提交修复：由 `sha256sum sbom/* > sbom/SHA256SUMS` 改为 `(cd sbom && sha256sum * > SHA256SUMS)`，使归档根目录中的 `SHA256SUMS` 使用相对文件名。修复提交 `6c35218571d5b1dbf24fdeb6727980474a936ce7`；该提交触发的直接校验运行待完成，修复尚不标记为 CI 验收通过。
## 5. 解释限制

- Runtime BOM 只描述该 CI Python 3.12 Linux 环境；项目声明的 Python runtime dependencies 为空，不能据此推断产品系统无依赖。
- Development BOM 包含 pytest、ruff 等开发依赖，不得与 runtime BOM 混用。
- Generator BOM/freeze 和 build-tools BOM/freeze 分别描述 SBOM 工具与 PEP 517 构建环境，不纳入产品 runtime BOM。
- PEP 517 build lock 描述当前仓库 setuptools/wheel build backend 及其传递依赖，不覆盖第三方 ROS workspace 或产品构建链。
- 当前 CI 未扫描 ROS workspace、apt/dpkg 全量系统包、C/C++ 静态链接库、容器镜像、GPU/CUDA、BSP、内核模块、固件、PLC runtime、厂商 SDK 或设备预装软件。
- 已对 Python 锁定依赖接入 OSV 匹配；首轮命中 generator pip 25.0.1 的 6 个 CVE，升级至 26.3 后 run #41779562839 复扫 45 个 package/version 返回 0 advisory/0 finding。首轮发现的人工可利用性处置/VEX 和第三方许可证法律审查仍待完成。

## 6. 关闭状态

- SBOM-001：**已关闭（限定范围）**。项目 runtime/dev 使用 uv.lock，generator 使用独立 hash-locked requirements，build backend 使用 pyproject build constraints + uv.lock hashes。
- SBOM-003：**已关闭（限定范围）**。仓库 Python runtime/dev、generator、PEP 517 build-tools 四个 CI 环境的 CycloneDX 1.7 BOM 生成、校验、artifact 归档和下载复核完成；artifact checksum 路径修复已提交，待修复后 CI 直接验证；依赖图完整性限制见本报告。
- SBOM-008：**已关闭（当前项目 build-system 范围）**。Python 3.10/3.11/3.12 的 `uv build --require-build-hashes` 全部通过。
- SBOM-004：上游文件 commit/SHA-256 校验已实施；许可证适用性审查仍待完成。
- SBOM-005/006：产品实际集成组件和第三方许可证审查未完成。
- SBOM-007：Python 锁定依赖 OSV 扫描已完成；首轮发现 generator `pip==25.0.1` 对应 6 个 CVE，升级至 `pip==26.3` 后复扫 45 个 package/version 返回 0 advisory/0 finding。首轮发现的人工可利用性分诊/VEX、恶意包/来源风险处置及产品级组件扫描仍待完成。

详细 build backend 证据见 [PEP 517 构建隔离依赖哈希锁定记录](2026-11-04-pep517-build-dependency-lock.md)，generator 证据见 [SBOM generator 工具链锁定记录](2026-11-04-sbom-generator-toolchain-lock.md)，项目依赖策略见 [Python 依赖锁定策略](2026-11-04-python-lockfile-decision.md)。

## 7. 参考资料

- [CycloneDX Python 7.6.0 release](https://github.com/CycloneDX/cyclonedx-python/releases)
- [CycloneDX Python environment usage](https://github.com/CycloneDX/cyclonedx-python/blob/main/docs/usage.rst)
- [GitHub Actions secure use](https://docs.github.com/en/actions/reference/security/secure-use)
- [GitHub Actions artifact upload](https://github.com/actions/upload-artifact)
- [uv build constraints](https://docs.astral.sh/uv/concepts/projects/build/)
- [uv settings](https://docs.astral.sh/uv/reference/settings/)
