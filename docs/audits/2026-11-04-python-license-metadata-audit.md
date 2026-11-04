---
tags: [许可证, SPDX, CycloneDX, Python, 软件供应链]
创建日期: 2026-11-04
更新日期: 2026-11-04
状态: 元数据候选清单已生成，人工法律复核未完成
---

# Python SBOM 许可证元数据候选审计

## 1. 输入与证据

CI 已将 SBOM 生成范围扩展为四个独立 Python 环境：项目 runtime、项目 development、CycloneDX generator、PEP 517 build-tools。GitHub Actions [run #41780128626](https://github.com/rexyll/robot_knowledgebasement/actions/runs/41780128626) 成功生成并校验四份 CycloneDX 1.7 JSON，并由标准库脚本 `scripts/extract_python_license_metadata.py` 提取 license metadata candidate CSV。

Artifact `python-sbom-cyclonedx-1.7`：ID `13297629985`，12,856 bytes，ZIP SHA-256 `4df21e05e03904055ebcf53c1756842c8f93aff50f59670d566f37fe56e12ed5`。已下载，ZIP digest 与 GitHub artifact metadata 一致；SHA256SUMS 中 9 项全部通过。CSV 共 45 个 component-scope 记录，42 个去重 name/version 组合。

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

需人工复核的 10 条 component-scope 记录见 [许可证元数据人工复核队列 CSV](2026-11-04-python-license-metadata-review-queue.csv)：7 条包含非 SPDX classifier/free-text 的 generator 组件记录，以及 3 条 packaging 的 OR 表达式记录。classifier 如 `License :: OSI Approved :: BSD License` 不能自动推断为 BSD-2-Clause 或 BSD-3-Clause；混合字段也不能假定 classifier 与 SPDX ID 完全一致。

CycloneDX 的 `acknowledgement=declared` 仅出现在 packaging 的三个环境记录中；其他记录未提供该字段。元数据缺少 acknowledgement 不代表许可证不存在，也不代表已经人工核实。

## 3. 自动化限制

四份 BOM 均通过 CycloneDX 1.7 schema validation。生成日志同时出现 root component 未定义直接依赖、dependency graph 不完整的 warning。因此本轮将 BOM 用作环境组件与许可证元数据清单，不宣称依赖关系图完整。环境 freeze、BOM JSON、候选 CSV 与 SHA256SUMS 一并归档，便于复核。

提取器只转录 CycloneDX `licenses` 字段，不推断许可证、不把自由文本转换为 SPDX ID、不选择 OR expression 的许可选项，也不生成法律结论。CSV 中所有记录均标记 `pending_manual_review`。

## 4. 后续审查要求

1. 对 10 条复核队列逐项查阅对应 release/tag 的 LICENSE、COPYING、NOTICE、项目声明和再分发条件。
2. 对其余 SPDX ID 候选也抽查上游 license text 与 metadata 一致性；不能仅凭 SPDX ID 自动视为法律审核完成。
3. 确认 SBOM generator/build tools 是否仅用于开发和 CI，是否会随产品或交付物再分发；区分内部使用与对外分发义务。
4. 对项目实际集成的 ROS 2、PLC、固件、SDK、容器与系统包重复建立产品级 BOM 和许可证清单。
5. 未完成法务/合规复核前，SBOM-005/006 保持未完成，不出具许可兼容性或再分发批准结论。
