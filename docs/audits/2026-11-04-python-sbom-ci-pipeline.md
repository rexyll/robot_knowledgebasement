# Python SBOM CI 生成流水线记录

> 日期：2026-11-04  
> 状态：工作流配置已提交；首次 GitHub Actions 运行与产物核验待执行。  
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

## 4. 验证状态与关闭条件

**已完成：** 工作流文件静态审查、动作 SHA 来源核对、runtime/dev/generator 环境隔离设计、输出文件与 artifact 路径配置。

**待完成：** 在 GitHub Actions 实际运行；确认两个 CycloneDX 1.7 JSON 成功生成并通过工具内 schema 校验；下载 artifact；复核 SBOM 组件范围、依赖图、SHA256SUMS 与 freeze 清单一致性。若首次运行失败，应记录失败日志并修正后重新执行。

在首次成功运行和 artifact 复核前，SBOM-003 只能标记为“CI 已实现、运行待验证”，不能标记为关闭。

## 5. 参考资料

- [CycloneDX Python 7.6.0 release](https://github.com/CycloneDX/cyclonedx-python/releases)
- [CycloneDX Python environment usage](https://github.com/CycloneDX/cyclonedx-python/blob/main/docs/usage.rst)
- [GitHub Actions secure use](https://docs.github.com/en/actions/reference/security/secure-use)
- [GitHub Actions artifact upload](https://github.com/actions/upload-artifact)
