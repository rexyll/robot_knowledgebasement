---
tags: [CycloneDX, SBOM, uv, pip, SHA-256, 工具链锁定]
创建日期: 2026-11-04
更新日期: 2026-11-04
状态: 已生成、提交并由 CI 哈希模式安装验证
---

# CycloneDX SBOM 生成器工具链锁定记录（2026-11-04）

## 1. 锁定对象

SBOM 生成器运行在独立 Python 3.12 Linux 工具环境，不与被扫描的 runtime/dev 环境混合。输入清单：

`requirements-sbom-tools.in`
- `cyclonedx-bom==7.6.0`
- `pip==26.3`

使用 uv 0.13.7 生成 `requirements-sbom-tools.txt`，命令：

```bash
uv pip compile requirements-sbom-tools.in \
  --generate-hashes \
  --output-file requirements-sbom-tools.txt
```

输出文件包含精确版本与 PyPI distribution SHA-256 hashes，包含完整传递依赖图。锁文件由 CI bootstrap run #564 生成后提交，不手工编辑。

## 2. 安装策略

CI 在单独目录创建不带 pip 的虚拟环境，再使用已固定 SHA 的 uv action 和 uv 0.13.7 安装：

```bash
python -m venv --without-pip "${RUNNER_TEMP}/sbom-generator"
uv pip sync --require-hashes \
  --python "${RUNNER_TEMP}/sbom-generator/bin/python" \
  requirements-sbom-tools.txt
```

`--require-hashes` 强制所有 requirement 都有哈希，`uv pip sync` 使工具环境与锁文件精确一致。该环境生成器版本、传递依赖与 pip installer 本身都纳入锁文件；生成器 venv 的 freeze 作为 SBOM artifact 的独立证据归档。

## 3. 实际验证

GitHub Actions [run #566](https://github.com/rexyll/robot_knowledgebasement/actions/runs/41774740672)，run ID `41774740672`，head commit `f9ec8b866876edfeb7f25a7b1a27d7066cc68adb`，最终 `completed / success`：

- Python 3.10/3.11/3.12 测试矩阵均通过。
- SBOM job 的 uv runtime/dev locked sync 成功。
- SBOM generator 的 `uv pip sync --require-hashes` 成功。
- 两份 CycloneDX 1.7 BOM 生成与工具内 schema 校验成功。
- Artifact 上传成功并下载复核。

工具环境 freeze 共 34 个 package（包含 `cyclonedx-bom==7.6.0`、`cyclonedx-python-lib==11.12.0`、`pip==26.3` 等），完整包版本见 artifact 中的 `generator-tool-freeze.txt`。

Artifact：`python-sbom-cyclonedx-1.7`，ID `13296392548`，ZIP 4,328 bytes，digest `sha256:53096815cf1963cc624aaebb495218ddd30124e19bdb64a9551ded206d7c2306`。下载后 runtime BOM 为 1 component/2 dependency entries，development BOM 为 7 components/8 dependency entries；两份 JSON 均可解析，5 个 SHA256SUMS 项全部通过。

## 4. 漏洞扫描反馈与剩余范围

首次 OSV 扫描（run #41779173369）覆盖 45 个去重 package/version，返回 12 个 advisory 记录，对应 6 个 CVE，全部命中 generator venv 的 `pip==25.0.1`。已将该工具链升级到 `pip==26.3`，其 PyPI release 于 2026-11-02 发布，文件 SHA-256 已写入 requirements hash lock；复扫已由 run #41779562839 完成：45 个 package/version、0 advisory/0 finding；artifact #13298332580 下载核验通过。

- PEP 517 build isolation 的 `setuptools==84.2.1`、`wheel==0.48.0` 和 `packaging==26.3` 已由独立锁文件/pyproject build constraints hash-lock，见构建依赖审计记录。
- GitHub Actions 本身使用完整 commit SHA，但其 runner 镜像、系统工具与托管服务不在 Python package lock 内。
- 该工具链 BOM 只描述 SBOM generator 环境，不应混入产品 runtime/dev BOM，也不代表 ROS/PLC/硬件产品 BOM。

## 5. 参考

- [uv pip compile 与哈希生成](https://docs.astral.sh/uv/pip/compile/)
- [uv pip sync](https://docs.astral.sh/uv/pip/sync/)
- [pip secure installs / --require-hashes](https://pip.pypa.io/en/stable/topics/secure-installs/)

状态：CycloneDX generator 的直接和传递 Python 包已 hash-lock 并由 CI 实测安装；pip 25.0.1 的 6 个 CVE 已触发升级至 26.3，复扫完成且当前 OSV 未再命中；PEP 517 build isolation 已单独 hash-lock。
