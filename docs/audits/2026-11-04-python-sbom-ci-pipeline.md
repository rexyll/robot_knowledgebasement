# Python SBOM CI 生成流水线记录

> 日期：2026-11-04  
> 状态：Python SBOM 已切换到 uv.lock 锁定环境；run #551 全矩阵通过，最新 artifact 已下载、解析，内部 SHA256SUMS 全部校验通过。  
> 范围：仓库 Python 包的 runtime 与 development 两个 Python 3.12 环境，不代表 ROS 2/机器人产品 BOM。

## 1. 本次变更

更新 `.github/workflows/ci.yml`，增加独立的 `python-sbom` job：

1. 创建独立 runtime venv，执行 `pip install .`，仅采集项目运行时安装环境。
2. 创建独立 development venv，执行 `pip install -e ".[dev]"`，采集开发/测试环境。
3. 在第三个隔离的 generator venv 安装 `cyclonedx-bom==7.6.0`，避免将 SBOM 生成器及其依赖误算进被扫描的产品环境。
4. 对两个目标解释器分别执行 `cyclonedx-py environment`，指定 CycloneDX 1.7、`--validate`、`--output-reproducible` 和项目元数据。
5. 导出三个环境的 `pip freeze --all`：runtime、development、generator tool。
6. 对 SBOM 和环境清单生成 SHA-256 文件。
7. 上传名为 `python-sbom-cyclonedx-1.7` 的 GitHub Actions artifact，保留 30 天。

预期主要产物：

- `robot-knowledgebase-runtime.cdx.json`
- `robot-knowledgebase-development.cdx.json`
- `runtime-python-freeze.txt`
- `development-python-freeze.txt`
- `generator-tool-freeze.txt`
- `SHA256SUMS`

## 2. Actions 固定版本

工作流中使用的 Actions 已从浮动 major tag 改为官方仓库 tag 当前解析到的完整 commit SHA：

| Action | 原引用 | 固定 commit SHA |
|---|---|---|
| actions/checkout | v4 | `11d5960a326750d5838078e36cf38b85af677262` |
| actions/setup-python | v5 | `a26af69be951a213d495a4c3e4e4022e16d87065` |
| actions/upload-artifact | v4 | `ea165f8d65b6e75b540449e92b4886f43607fa02` |

这些 SHA 是本次查询官方 Git ref 时 v4/v5 标签指向的 commit。升级时应重新读取官方 tag/ref，核验发布说明和权限范围，再更新固定 SHA；不能把标签名称本身当作不可变标识。

## 3. 范围与解释限制

- runtime BOM 只描述在本 job 的 Python 3.12 Linux runner 中安装的 Python 项目环境。
- development BOM 额外包含当前 `.[dev]` 依赖，不能与 runtime BOM 混用。
- 生成器自身的依赖由 `generator-tool-freeze.txt` 记录，不纳入被扫描环境。
- `cyclonedx-bom` 顶层版本固定为 7.6.0；当前仍未提交其传递依赖的完整 hash-locked lockfile。冻结清单记录本次实际解析结果，但不保证未来运行解析完全一致。
- 项目声明的 runtime dependencies 当前为空；runtime BOM 仍用于记录项目安装元数据与实际 Python 环境，不应夸大为完整软件供应链清单。
- Python 3.10/3.11/3.12 测试矩阵仍在 test job；本次 SBOM job 只在 Python 3.12 生成。若需跨解释器 BOM，应另行扩展。
- 当前 CI 不扫描 ROS workspace、apt/dpkg 全量系统包、C/C++ 静态链接库、容器镜像、GPU/CUDA、BSP、内核模块、固件、PLC runtime、厂商 SDK 或设备预装软件。

## 4. 首次运行与产物核验

**GitHub Actions：** [CI run #515](https://github.com/rexyll/robot_knowledgebasement/actions/runs/41773062051)，run ID `41773062051`，head commit `15db2c04c42eca8fde5e67299e98183af8f9374e`，最终状态 `completed / success`。Python 3.10、3.11、3.12 三个测试矩阵均通过；SBOM job 的安装、生成器安装、两个 BOM 生成/校验、环境归档和 artifact 上传步骤均成功。

**Artifact：** `python-sbom-cyclonedx-1.7`，artifact ID `13295617233`，ZIP 大小 4,602 bytes，GitHub artifact digest `sha256:5e3a760bfb1ec34f7cd9bc4ac646e2983291270499efc94a70dc3db7361f8393`，保留至 2026-12-04 04:25:30 UTC。

**下载后复核：**

| 文件 | 结果 |
|---|---|
| `robot-knowledgebase-runtime.cdx.json` | CycloneDX 1.7；JSON 可解析；1 个 environment component，2 个 dependency entries；metadata root component 为 `robot-knowledgebase` 0.1.0 |
| `robot-knowledgebase-development.cdx.json` | CycloneDX 1.7；JSON 可解析；8 个 components，9 个 dependency entries；包含 pytest、ruff 及其 Python 依赖 |
| 三份 `pip freeze --all` | runtime、development、generator tool 环境分别归档；生成器环境未混入目标 BOM |
| `SHA256SUMS` | 5 个 BOM/freeze 文件校验全部通过 |

`cyclonedx-py` 的 `--validate` 在 CI 生成步骤中成功；下载后另行执行 JSON 解析与 SHA-256 校验。runtime 环境没有声明的第三方运行时依赖，因此 BOM 只呈现项目 metadata root 与 runner 基础 pip 组件，不应误读为产品完整依赖闭包。

**关闭判定：** SBOM-003 对“仓库 Python runtime/dev 两种环境的 CycloneDX 1.7 CI 生成、校验与 artifact 归档”已完成。它不关闭 SBOM-001（传递依赖 hash-lock）、SBOM-004（外部源文件内容哈希）、SBOM-005/006（产品实际组件与许可证）、SBOM-007（漏洞/VEX）。

## 5. 参考资料

- [CycloneDX Python 7.6.0 release](https://github.com/CycloneDX/cyclonedx-python/releases)
- [CycloneDX Python environment usage](https://github.com/CycloneDX/cyclonedx-python/blob/main/docs/usage.rst)
- [GitHub Actions secure use](https://docs.github.com/en/actions/reference/security/secure-use)
- [GitHub Actions artifact upload](https://github.com/actions/upload-artifact)

## 6. 锁文件接入后的复验（2026-11-04）

GitHub Actions [run #551](https://github.com/rexyll/robot_knowledgebasement/actions/runs/41774325434)，run ID `41774325434`，head commit `72064325982fe2c73e3df25249e34edde88876a6`，最终 `completed / success`。Python 3.10/3.11/3.12 测试矩阵均通过 `uv sync --locked --extra dev`、ruff、上游源码 SHA-256 校验和 pytest；SBOM job 的 runtime/dev 锁定同步、CycloneDX 1.7 生成/校验、环境 freeze 与 artifact 上传均成功。

- `uv.lock`：11 个 package 项，Python `>=3.10`，包含 PyPI artifact SHA-256；Git Blob SHA `cb8709dfd8c9cdcaa5e7265cca404d795387553d`，32,892 bytes。
- 新 artifact：`python-sbom-cyclonedx-1.7`，ID `13296277606`，ZIP 4,330 bytes，digest `sha256:c02bc03264123e5b47151b32b3f11410ce6950fd88d4ff8b1132142a1f37de25`。
- 下载复核：runtime BOM 1 component/2 dependency entries；development BOM 7 components/8 dependency entries；两份 JSON 的 `specVersion` 均为 1.7，metadata root 均为 `robot-knowledgebase`；SHA256SUMS 的 5 个文件全部通过。
- 新 runtime/dev 环境由 uv 创建，freeze 使用 `uv pip freeze`；SBOM generator 仍处于独立 pip 环境。

SBOM-001 可在项目 runtime/dev 依赖图范围内关闭。构建隔离 setuptools/wheel 与 SBOM generator 的传递依赖仍未 hash-lock，不能把这次锁文件扩大解释为整个 CI 工具链锁定。
