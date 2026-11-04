---
tags: [许可证, SPDX, CycloneDX, Python, 软件供应链]
创建日期: 2026-11-04
更新日期: 2026-11-04
状态: 已完成首轮上游许可证证据采集；人工法律复核未完成
---

# Python SBOM 许可证元数据候选审计

## 1. 输入与证据

CI 已将 SBOM 生成范围扩展为四个独立 Python 环境：项目 runtime、项目 development、CycloneDX generator、PEP 517 build-tools。GitHub Actions [run #41780128626](https://github.com/rexyll/robot_knowledgebasement/actions/runs/41780128626) 成功生成并校验四份 CycloneDX 1.7 JSON，并由标准库脚本 `scripts/extract_python_license_metadata.py` 提取 license metadata candidate CSV。

Artifact `python-sbom-cyclonedx-1.7`：ID `13297629985`，12,856 bytes，ZIP SHA-256 `4df21e05e03904055ebcf53c1756842c8f93aff50f59670d566f37fe56e12ed5`。已下载后续 run #41783904623 的同结构 artifact #13300332133（12,856 bytes），ZIP SHA-256 与 GitHub digest 一致；四份 CycloneDX 1.7 JSON 均可解析，组件/依赖计数与上述环境快照一致，license CSV 45 行。发现 ZIP 扁平化后 SHA256SUMS 中的 `sbom/` 路径前缀失配：直接 `sha256sum -c` 失败，但去除前缀后 9 项实际文件摘要均匹配。已提交 CI 修复 `6c35218571d5b1dbf24fdeb6727980474a936ce7`，使 checksum 清单使用归档根目录相对路径；修复后 CI 直接验证待完成。CSV 共 45 个 component-scope 记录，42 个去重 name/version 组合。

| BOM scope | 组件记录 | Dependency entries |
|---|---:|---:|
| Python runtime | 1 | 2 |
| Python development | 7 | 8 |
| SBOM generator | 34 | 35 |
| PEP 517 build tools | 3 | 4 |

这些是四个 Python 3.12 Linux CI 环境的观察快照。它们不等同于 uv.lock 全平台所有 marker/环境组合，也不覆盖 ROS、apt/dpkg、容器、原生系统库、固件、PLC、SDK 或实际机器人产品配置。

## 2. 元数据形态统计

45 条记录的 CycloneDX license metadata 形态：

- 35 条为 SPDX ID 候选。
- 3 条为 SPDX expression 候选（`packaging==26.3` 的 `Apache-2.0 OR BSD-2-Clause`，在三个环境中各出现一次）。
- 3 条仅提供自由文本/许可证 classifier。
- 4 条同时提供 SPDX ID 与 classifier 文本。
- 0 条缺少 license metadata。

需复核的 10 条 component-scope 记录见 [许可证元数据人工复核队列 CSV](2026-11-04-python-license-metadata-review-queue.csv)。本轮已为 9 条记录采集到版本对应的上游 tag/commit 和 LICENSE 文件证据（包括 packaging 在三个 scope 的重复记录）；sortedcontainers 2.4.0 仅取得 PyPI 版本页嵌入的 Apache-2.0 许可文本和当前上游 LICENSE，尚未将 2021 年 sdist 与确切上游 commit 对应。**所有 10 条的法律复核状态仍未完成。** classifier 如 `License :: OSI Approved :: BSD License` 不能自动推断为 BSD-2-Clause 或 BSD-3-Clause；混合字段也不能假定 classifier 与 SPDX ID 完全一致。

CycloneDX 的 `acknowledgement=declared` 仅出现在 packaging 的三个环境记录中；其他记录未提供该字段。元数据缺少 acknowledgement 不代表许可证不存在，也不代表已经人工核实。

## 3. 上游许可证证据采集结果（2026-11-04）

本轮逐一核对了人工复核队列中的 8 个不同包版本。证据优先使用版本 tag/commit 下的上游 LICENSE、pyproject 声明和 PyPI 对应版本页；证据 URL 与 revision 已写入 CSV。采集到许可证文本不等于完成许可证法律审查。

| 包 / 版本 | 上游证据 | 当前判断 | 剩余事项 |
|---|---|---|---|
| arrow 1.4.0 | [release tag commit 2c1f518](https://github.com/arrow-py/arrow/tree/2c1f5185ad66bf3b1cf8c0812f4b4fe65ac46656)；该版本 pyproject 指向 LICENSE，LICENSE 为 Apache 2.0 | 与 PyPI classifier 一致 | 核查分发场景、版权/NOTICE 要求 |
| cyclonedx-bom 7.6.0 | [PyPI 7.6.0 provenance](https://pypi.org/project/cyclonedx-bom/7.6.0/) 指向发布 commit [bb678472](https://github.com/CycloneDX/cyclonedx-python/tree/bb67847232d9034c2fb0ce858cb7d1177d97162a)；该 commit 的 LICENSE 为 Apache 2.0 | 版本发布 provenance 与上游许可证文件互相印证 | 检查工具链内部使用与再分发边界 |
| cyclonedx-python-lib 11.12.0 | [tag v11.12.0 commit 52cb3c9](https://github.com/CycloneDX/cyclonedx-python-lib/tree/52cb3c94f023df887ac65a6125bce4d63ab7857e)；LICENSE 为 Apache 2.0 | 与 PyPI 版本声明一致 | 检查工具链内部使用与再分发边界 |
| jsonpointer 3.8 | [commit 7c78531](https://github.com/stefankoegl/python-json-pointer/tree/7c78531542c81ee0d308cb044244c0b1adf37b39) 的提交信息为 bump version to 3.8；LICENSE.txt 与源码均声明 Modified BSD License | 上游三条款文本包含 source/binary notice 保留和禁止未经许可背书条款；不自动转换为 SPDX 标识 | 需人工确认 SPDX 对应关系、版权声明和 notice |
| py-serializable 2.1.0 | [tag v2.1.0 commit 85628fd](https://github.com/madpah/serializable/tree/85628fd392101627993bb69732630a6e66dd63be)；LICENSE 为 Apache 2.0 | 与 PyPI 声明一致 | 检查工具链内部使用与再分发边界 |
| sortedcontainers 2.4.0 | [tag v2.4.0 commit a1f52d6](https://github.com/grantjenks/python-sortedcontainers/tree/a1f52d6713dd2c2713a881d4f4d86ed68ff71cab)；该 commit 的 `sortedcontainers/__init__.py` 声明 2.4.0，`setup.py` 声明 Apache 2.0，LICENSE 为 Apache 2.0 | 精确 release tag、版本源码与 LICENSE 一致 | 核对分发场景和 Apache NOTICE/版权义务 |
| webcolors 25.10.0 | [tag 25.10.0 commit e6392ba](https://github.com/ubernostrum/webcolors/tree/e6392ba6eeba81b02e666eb3ed02ef2e006344c0)；pyproject 明确 BSD-3-Clause，LICENSE 含三条款文本 | 与 CycloneDX SPDX 候选一致 | 核对 BSD notice 在未来分发包中的保留 |
| packaging 26.3（3 个 scope） | [tag 26.3 commit 929fd4b](https://github.com/pypa/packaging/tree/929fd4b1410ac7ef61ef3f45b2f5d7e87711a9b5)；LICENSE 指向 LICENSE.APACHE 或 LICENSE.BSD；两份许可文件均已读取 | 上游明确声明二选一；贡献者贡献条款则声明 under both，保留 Apache-2.0 OR BSD-2-Clause | 项目是否需要选定并记录分发时采用的许可，须由法务/合规决定 |

### 证据分级与状态

- 10/10 个 component-scope 队列行（8 个不同 package/version，其中 packaging 占 3 行）已取得对应版本 tag/commit 或 PyPI provenance/release 级 LICENSE 证据。
- sortedcontainers 2.4.0 已定位 tag v2.4.0 和 commit `a1f52d6713dd2c2713a881d4f4d86ed68ff71cab`；同一 commit 中的版本声明、setup.py 许可声明和 LICENSE 相互一致。
- 10/10 行仍为法律复核待办；没有任何记录被标记为“许可证审查完成”或“允许再分发”。
- jsonpointer 的 “Modified BSD” 保留上游名称，不因三条款结构而擅自重写成 SPDX ID。
- packaging 的 OR expression 保持上游原意；不替用户选择 Apache 或 BSD 许可。
- 本次仅审查 generator/build-tools 环境中队列所列包，不构成 runtime 产品许可批准，也不覆盖其传递依赖、产品集成组件或最终交付物。
## 4. 自动化限制

四份 BOM 均通过 CycloneDX 1.7 schema validation。生成日志同时出现 root component 未定义直接依赖、dependency graph 不完整的 warning。因此本轮将 BOM 用作环境组件与许可证元数据清单，不宣称依赖关系图完整。环境 freeze、BOM JSON、候选 CSV 与 SHA256SUMS 一并归档，便于复核。

提取器只转录 CycloneDX `licenses` 字段，不推断许可证、不把自由文本转换为 SPDX ID、不选择 OR expression 的许可选项，也不生成法律结论。CSV 中所有记录均标记 `pending_manual_review`。

## 6. Artifact 校验修正记录

run #41783904623 的 artifact #13300332133 下载后，ZIP digest 与 GitHub artifact digest `sha256:03f9310578c31ea8f9d7e9678fe44a7bad9366f098c44305dd4c0c53adc9f377` 一致。四份 BOM 均为 CycloneDX 1.7 且可解析，45 条许可证候选 CSV 记录可解析。独立执行 `sha256sum -c SHA256SUMS` 时发现归档扁平化导致清单仍带 `sbom/` 路径前缀；将路径前缀去除后，9 项文件摘要全部匹配。

已修复 `.github/workflows/ci.yml`：在 `sbom/` 目录内生成 basename-only 的 `SHA256SUMS`，而不是写入 `sbom/<filename>`。修复 commit `6c35218571d5b1dbf24fdeb6727980474a936ce7` 由 [run #41784066050](https://github.com/rexyll/robot_knowledgebasement/actions/runs/41784066050) 验证成功；artifact #13300800214 下载后，在解压目录直接执行 `sha256sum -c SHA256SUMS`，9 项全部 OK。四份 BOM 均为 CycloneDX 1.7、JSON 可解析，license CSV 45 行。

## 7. 后续审查要求

1. 对 10 条复核队列逐项查阅对应 release/tag 的 LICENSE、COPYING、NOTICE、项目声明和再分发条件。
2. 对其余 SPDX ID 候选也抽查上游 license text 与 metadata 一致性；不能仅凭 SPDX ID 自动视为法律审核完成。
3. 确认 SBOM generator/build tools 是否仅用于开发和 CI，是否会随产品或交付物再分发；区分内部使用与对外分发义务。
4. 对项目实际集成的 ROS 2、PLC、固件、SDK、容器与系统包重复建立产品级 BOM 和许可证清单。
5. 未完成法务/合规复核前，SBOM-005/006 保持未完成，不出具许可兼容性或再分发批准结论。
