# 00-01｜Python Toolkit wheel/sdist 发布范围与许可证元数据审查（2026-11-15）

## 1. 审查范围与证据

本轮把根目录 `LICENSE` 和 `pyproject.toml` 的声明范围具体化到 Python 实际构建的分发物，而不是根据包名或目录结构推测。

- PR 源提交：`46050ad0d812d231f47b9e8a3f121b7fa88e131a`
- PR base：`main@aac8e081ca733265f34b08000647473d02e23e72`
- GitHub Actions： [Run #43709474246](https://github.com/rexyll/robot_knowledgebasement/actions/runs/43709474246)，结论 success；Python 3.10/3.11/3.12、OSV 和 Python SBOM 五个 job 全部成功。
- 构建命令：`uv build --require-build-hashes`；清单由 Python 3.12.16 对本次生成的 wheel/sdist 归档成员逐一计算 SHA-256。
- Artifact ID：`14159916866`；GitHub artifact digest：`sha256:c9970ad3235158372cb7a3ee83cd0381581ef4052bf805281719db505665a2dc`。
- 可复核清单： [python-distribution-file-manifest.json](2026-11-15-python-distribution-file-manifest.json)。

PR 事件的 workflow SHA 与源分支 HEAD SHA 是两个不同概念：清单保存 PR head、base 和 workflow revision 三者，避免把 GitHub pull-request merge ref 误当源分支提交。

## 2. 精确构建结果

| 分发物 | 大小 | SHA-256 | 文件成员 |
| --- | ---: | --- | ---: |
| `robot_knowledgebase-0.1.0-py3-none-any.whl` | 10,772 bytes | `44c089a2712d9a27b85745d75cff5f768fac7813f52b240ebb1575616d52da1f` | 17 |
| `robot_knowledgebase-0.1.0.tar.gz` | 11,840 bytes | `1db1633b687e004032625a3bf2a3488908bcaead015e21aa06ffee7901c89021` | 25 files + 9 directories |

### 2.1 Wheel 内容

Wheel 的 17 个文件由 11 个 `robot_knowledgebase` Python 源文件和 6 个 `.dist-info` 元数据/许可证文件组成。包括 `robot_knowledgebase-0.1.0.dist-info/licenses/LICENSE`。

不包含：

- `knowledge/`、`docs/`、`scripts/`；
- 根 `tests/`；
- `.github/` 工作流；
- 根 `README.md`。

因此该 wheel 并非整个 Knowledge Vault 的发布包；它只分发 Python Toolkit 运行时包和许可证/安装元数据。

### 2.2 sdist 内容

修改 `MANIFEST.in` 前的实测结果发现 sdist 自动包含 10 个根目录测试，其中 8 个测试引用 `scripts/` 或 `.github/` 路径，而这些路径并不在 sdist 中。此类仓库级 Stäubli 构建、生命周期、测试目录验证不是 Python Toolkit 的独立包测试，将其随包发布会产生不完整测试套件并扩大不必要的发布范围。

已新增 `MANIFEST.in`：

- `prune tests`
- 重新包含 `tests/test_chunker.py`
- 重新包含 `tests/test_markdown.py`

Run #43709474246 已验证新的 sdist：41 个成员（32 个普通文件、9 个目录）的旧分发快照收窄为 34 个成员（25 个普通文件、9 个目录）；仅保留两个直接测试 Python Toolkit 功能的测试文件。wheel 仍为 17 个成员，未受影响。

当前 sdist 包含根 `LICENSE`、`MANIFEST.in`、`PKG-INFO`、`README.md`、`pyproject.toml`、构建生成的 `setup.cfg` 和 egg-info 元数据、11 个 Python 包源文件及两个 Toolkit 测试。它不含 `knowledge/`、`docs/`、`scripts/`、`.github/` 或仓库级 Stäubli 集成测试。

**未执行从解包 sdist 环境重新安装并运行测试的独立 smoke test。** 本次 CI 的 pytest 测试仍在完整仓库 checkout 中运行；清单只证明构建包内容与哈希，不将其说成 sdist 安装验收。

## 3. 许可证元数据发现

实际 wheel 和 sdist 的 Core Metadata 都是 2.4，观察到：

- `License`：旧式自由文本字段，包含完整 MIT 文本；
- `License-File: LICENSE`；
- **没有** `License-Expression`；
- `pyproject.toml` 仍使用旧式 `license = { file = "LICENSE" }`，并保留 `License :: OSI Approved :: MIT License` classifier。

Python Packaging Authority 的 Core Metadata 规范说明：Metadata 2.4 中旧式 `License` 字段已弃用，建议改用 SPDX `License-Expression`；`License ::` classifier 同样弃用。PEP 639 的 `License-Expression` 只适用于包含该 metadata 的 distribution archive，不会自动覆盖项目中其它文件或其他分发物。

- [PyPA Core Metadata：License、License-Expression 和 License-File](https://packaging.python.org/en/latest/specifications/core-metadata/)
- [PyPA：Writing pyproject.toml / license and license-files](https://packaging.python.org/en/latest/guides/writing-pyproject-toml/)
- [setuptools：Migrating to PEP 639 License Expressions](https://setuptools.pypa.io/en/stable/userguide/license_migration.html)

**当前处理：** 暂不把 `license` 改成 SPDX `MIT`，也不移除 classifier。虽然现有 build backend 已能构建包，但在 11 个包源文件、两个保留测试及其作者/权利授权尚未确认之前，主动把 distribution metadata 改成标准化 MIT expression 会扩大或强化尚未获得权属证据的许可主张。待权利人确认 Python Toolkit 发布范围后，再迁移至 `license = "MIT"` 和 `license-files = ["LICENSE"]` 并重新构建验证。

## 4. 权利边界与当前结论

1. **已确认的分发范围：** wheel 只有 Python Toolkit 源码和包元数据；sdist 另含根 README、项目构建配置与两个 Toolkit 单元测试。两个分发物均不包含知识库文章、厂商/标准资料、参考项目资料和仓库级 Stäubli 脚本。
2. **尚未确认的权属：** 根许可证中的 `Robot Knowledge Basement Contributors` 仍不能替代 11 个 Python 源文件和两个测试文件的实际作者/权利人名册或授权证据。
3. **不得推导：** 构建成功、文件被打入 wheel/sdist、元数据写有 MIT 或 Git Blob/SHA-256 匹配，都不是权利人授权证明。
4. **与全库许可矩阵的关系：** 本轮只确认 Python Toolkit 具体分发物；不覆盖其余 386 个 main 基线资产，也不改变知识文章/第三方资料的权利审查状态。
5. **根 LICENSE 未修改：** 不宣称全部仓库内容均为 MIT，不批量添加 SPDX 头，不向第三方内容扩展 MIT 许可。

## 5. 后续动作

- 取得 Python Toolkit 11 个源文件和两个保留测试文件的作者/权利确认及发布授权；
- 根据确认后的发布范围迁移到 PEP 639 SPDX 表达式，重新生成 wheel/sdist 并核验 metadata；
- 评估把仓库总览 README 用作 PyPI 包 README 的适用性：目前 sdist README 链接指向未随分发物打包的 `knowledge/` 和 `docs/` 页面，未来可为 Toolkit 提供独立 README；
- 可在后续 CI 增加从 sdist 解包、安装并运行两项 Toolkit 测试的 smoke test；
- 将 Python Toolkit 权利确认与全仓库 386 项资产权利登记分开维护。

**状态：** wheel/sdist 文件成员和哈希已通过 CI 生成并人工核对；根 MIT 对 Python Toolkit 的权利人授权及文件级再分发许可仍未关闭。00-01 保持进行中。

