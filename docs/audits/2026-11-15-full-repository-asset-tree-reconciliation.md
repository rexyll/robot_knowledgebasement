# 00-01｜全仓库 Git Tree 资产基线差异重建（2026-11-15）

## 1. 审计结论

本次对 `rexyll/robot_knowledgebasement` 的 `main` 分支执行完整递归 Git Tree 对账，修复了原资产清单只覆盖部分仓库文件、且部分 Blob 元数据过期的问题。

- 基线提交：[`aac8e081ca733265f34b08000647473d02e23e72`](https://github.com/rexyll/robot_knowledgebasement/commit/aac8e081ca733265f34b08000647473d02e23e72)
- Tree SHA：`de8987f4d90924de1937bcc62efe38804c255fda`
- Git Tree API：`recursive=1`，响应 `truncated=false`
- 当前仓库文件对象：**386 个 blob**
- 对账前资产清单：**187 条有效路径记录**
- 新发现并补录：**199 个文件资产**
- 已有路径不存在：**0 条**
- Blob SHA 或字节数与当前 main 不一致：**13 条**，已同步修正
- 对账后资产清单：**386 条唯一文件路径记录**，与本次 Tree 中的 386 个 blob 一一对应

本轮只完成**仓库对象和文件元数据基线重建**。不代表 386 个文件已经完成内容、主张级来源、授权、许可证、重复性或工程验证审查，也不改变任何章节任务的验收状态。

## 2. 新增资产分布

199 个新增路径按仓库路径和文件类型做初始归类如下：

| 资产类别 | 新增数量 | 初步覆盖范围 |
| --- | ---: | --- |
| 章节 TaskPlan 与 TaskPlan 导航 | 26 | `docs/TaskPlan/` |
| 审计记录与审计数据 | 79 | `docs/audits/` |
| 源码、脚本与自动化测试 | 31 | `scripts/`、`src/`、`tests/` |
| 参考项目文件 | 12 | `knowledge/projects/` |
| 工程模板 | 12 | `docs/templates/` |
| JSON Schema | 7 | `docs/schemas/` |
| 每日 TaskPlan 历史 | 13 | `TaskPlan_History/` |
| 其他文档 | 8 | `docs/` 其余文件 |
| 工作流 | 1 | `.github/workflows/` |
| 数据目录占位或资产 | 3 | `data/` |
| 根目录与工作区元数据 | 7 | `LICENSE`、`README.md`、`.gitignore`、`.obsidian/` 等 |
| **合计** | **199** | |

其中的新增文档、审计文件、程序源码、测试、Schema、模板、参考项目数据和配置具有不同的授权与验收要求。上表是路径级归类，不是内容成熟度或优先级的最终评定。

## 3. 已有资产元数据修正

以下 13 个已有记录的 Blob SHA 和/或文件大小与当前 `main` 不一致，已按 Tree 元数据刷新；没有因元数据变更而将其内容审查状态升级为完成：

1. `knowledge/algorithms/轨迹优化与运动控制.md`
2. `knowledge/ecosystem/主要厂商.md`
3. `knowledge/ecosystem/知识生态兼容矩阵.md`
4. `pyproject.toml`
5. `.github/workflows/ci.yml`
6. `docs/audits/README.md`
7. `TaskPlan.md`
8. `docs/TaskPlan/21-产业生态厂商与市场/TaskPlan.md`
9. `docs/链接台账.md`
10. `docs/audits/2026-11-06-staubli-robotics-ecosystem-review.md`
11. `docs/TaskPlan/00-知识治理与分类体系/TaskPlan.md`
12. `docs/audits/2026-11-03-baseline-inventory.md`
13. `docs/audits/2026-11-09-staubli-moveit-mesh-filter-lifecycle-addendum.md`

清单字段 `metadata_reconciled_date`、`metadata_reconciliation_scope` 和 `metadata_reconciliation_history` 已记录本次基线提交与“仅元数据刷新”的范围。

## 4. 资产审计边界与发现

### 4.1 已完成

- 用未截断的完整 Git Tree 替代基于旧 TaskPlan 统计和零散目录列表的推算。
- 对每个 Git 文件对象记录路径、字节数、Blob SHA、初步领域、资源类型、待审查状态和元数据对账信息。
- 逐一检查旧清单路径：本次快照中无失效路径。
- 保留原有资产的 `audit_scope`、`priority`、`initial_status` 和 `targeted_review` 结论；只更新确实发生漂移的 Git 元数据。
- 为 199 个首次登记的文件显式设置“内容、主张、来源和授权审查待完成”，没有将文件存在或被纳入清单视为验收。

### 4.2 未完成，不能由 Git Tree 元数据推断

- **来源与授权**：文件内容的作者、上游来源、复制/改编关系、版权持有人、第三方许可、NOTICE 和再分发权。
- **主张级事实核验**：文章中的每条技术主张是否有一手来源，版本/适用范围/工况/单位是否正确，引用是否真正打开并核实。
- **成熟度与可信度**：正式知识、索引、设计草案、测试规格、用户确认、CI 报告、仿真结果和实机证据必须区分。
- **重复与交叉映射**：相同知识是否多处重复，是否有稳定主归属和正确双链。
- **代码/配置供应链**：新增源码、脚本、工作流与依赖是否有可复现版本、许可证闭包、哈希、SBOM、漏洞扫描和测试覆盖。
- **项目案例授权**：`knowledge/projects/` 中的参考项目文件是否含有需进一步确认来源或适用范围的资料。
- **时效性**：Git 提交时间仅说明版本变动，不等于事实重新验证日期、来源发布日期或产品/标准当前状态。

特别注意：本次 199 个新增文件中包含 31 个源码/脚本/测试资产、12 个参考项目资产、26 个章节计划和 79 个审计资产。它们仍需按各自资源类型开展授权、来源、质量和证据等级审查。对于 `LICENSE`，本轮只登记文件对象，未据此推断它覆盖所有文件、第三方依赖、项目案例或外部代码。

## 5. 后续工作顺序

继续保持根计划最高优先级 `00-01`，不得因本轮元数据对账完成而提前关闭节点。

1. **P0：新资产风险分流**。先审查新增的 `LICENSE`、源码/脚本/测试、CI 工作流、项目数据与配置；识别可能包含第三方代码、外部来源、敏感信息或不适合公开的内容。
2. **P0：主张级来源审计**。为现有 142 个明确标记为 claim-level review pending 的资产继续逐条核验；对新增知识文档、专题审计和技术资产建立主张—来源—适用范围映射。
3. **P1：文档质量与重复治理**。完成章节 TaskPlan、审计报告、模板、Schema、参考项目数据的内容成熟度、职责边界、链接和重复项检查。
4. **P1：供应链和授权核验**。把代码/工作流/依赖/第三方来源分别纳入外部项目治理、许可证、NOTICE、SBOM、漏洞和构建来源审查。
5. **验收门槛**：资产清单与章节映射完整、主张有可追溯来源、授权边界清楚、缺口报告可复核；未经审查的项目继续标为待审或阻塞。

## 6. 本记录与数据文件

- 完整资产清单：[2026-11-03-knowledge-asset-inventory.csv](2026-11-03-knowledge-asset-inventory.csv)（本轮已扩展到 386 条唯一路径）
- 章节任务计划：[00 章 TaskPlan](../TaskPlan/00-知识治理与分类体系/TaskPlan.md)
- 根任务计划：[TaskPlan.md](../../TaskPlan.md)

## 7. 执行限制

本轮只修改知识库审计清单和治理记录；没有导入或修改 `MotionControlAlgorithms`、Stäubli driver、MoveIt、rclcpp 或其他外部工程源码，没有新增 submodule，没有运行硬件/仿真测试，也没有作法律意见或产品合规结论。

`MotionControlAlgorithms` 合并仍然延期。待 `00-01` 正式验收、`14-EXT-02` 第三方来源/许可证/SBOM 门禁关闭、目标仓库子目录/submodule/独立 CI 集成验证完成，并明确导入 commit、文件范围和实施分支后，才可重新评估。
