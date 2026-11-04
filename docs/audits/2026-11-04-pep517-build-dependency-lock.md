---
tags: [PEP517, setuptools, wheel, uv, build-isolation, SHA-256, SBOM]
创建日期: 2026-11-04
更新日期: 2026-11-04
状态: 已锁定并由 CI 干净构建验证
---

# PEP 517 构建隔离依赖哈希锁定记录（2026-11-04）

## 1. 目标与边界

项目的 `pyproject.toml [build-system]` 声明 `setuptools>=68` 和 `wheel`。PEP 517 build isolation 会在隔离环境安装构建后端依赖；项目 runtime/dev 的 `uv.lock` 本身不能被误当作完整 build backend 锁。本次通过 uv build constraints 将实际 build requirements 固定到确切版本并校验制品哈希。

## 2. 锁定输入和解析结果

- 输入：`requirements-build-tools.in`（`setuptools>=68`、`wheel`）。
- 锁：`requirements-build-tools.txt`，由 uv 0.13.7 的 `uv pip compile --generate-hashes` 生成。
- 解析结果：
  - `setuptools==84.2.1`
  - `wheel==0.48.0`
  - `packaging==26.3`（wheel 的传递依赖）
- 三个包共记录 6 个 SHA-256 distribution hashes（sdist/wheel）。
- `pyproject.toml [tool.uv]` 同时配置 `build-constraint-dependencies`，为上述三个包精确 pin 并嵌入对应 hashes；开启 `require-build-hashes = true`。
- `uv.lock` 已刷新，包含上述 build constraint requirement 与 hashes。不要只依赖独立 requirements 文件而忽略项目构建时的 uv 配置。

## 3. CI 强制验证

CI 测试矩阵在 `uv sync --locked --extra dev` 后执行：

```bash
uv build --require-build-hashes
```

该步骤对项目实际生成 source distribution 和 wheel 时的隔离构建依赖执行哈希校验。SBOM job 的 runtime/dev `uv sync --locked` 也使用同一项目构建哈希策略。

GitHub Actions [run #585](https://github.com/rexyll/robot_knowledgebasement/actions/runs/41777632096)，run ID `41777632096`，head commit `ee5d38b3cb57df40addfb448b411d10ffc2e777f`，最终 `completed / success`：

- Python 3.10/3.11/3.12 测试矩阵全部通过。
- 三个版本均成功执行 `uv build --require-build-hashes`。
- runtime/dev locked sync、lint、pytest 全部通过。
- CycloneDX 1.7 runtime/dev SBOM 生成与校验、artifact 上传成功。

Artifact：`python-sbom-cyclonedx-1.7`，ID `13298086142`，ZIP 4,328 bytes，digest `sha256:706a8bd3be5cde5d2fc34aa47b7c129354f694abae458b832107dab78046742b`。下载后两份 CycloneDX JSON 均可解析，runtime BOM 1 component/2 dependency entries，development BOM 7 components/8 dependency entries；5 项 SHA256SUMS 全部通过。

## 4. 仍需注意

- `require-build-hashes` 是 uv 文档标注的实验性构建依赖校验功能；本仓库已 pin uv 0.13.7，并以 CI 真实构建作为当前验证证据。升级 uv 时必须重新验证该行为。
- 哈希用于验证从索引下载的 distribution archive，不代表源码构建过程、GitHub runner image、系统工具链或所有构建输入都已完全可复现。
- 构建 backend 锁只覆盖本项目当前 PEP 517 声明的 setuptools/wheel 及其解析传递依赖；第三方项目、ROS workspace、系统包、容器、GPU/BSP、固件和 PLC runtime 不在此范围。
- 尚未完成 CVE/VEX 扫描与第三方许可证法律审查。

## 5. 参考

- [uv: Building distributions / Build constraints](https://docs.astral.sh/uv/concepts/projects/build/)
- [uv settings: build-constraint-dependencies / require-build-hashes](https://docs.astral.sh/uv/reference/settings/)

状态：当前仓库 PEP 517 build backend requirements 已固定版本及 SHA-256，并由 Python 3.10/3.11/3.12 CI 的真实隔离构建验证通过。
