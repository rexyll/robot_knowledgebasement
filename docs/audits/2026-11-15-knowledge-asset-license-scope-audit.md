# 00-01｜知识资产许可证范围与逐路径权利登记基线（2026-11-15）

## 1. 范围与方法

本轮针对全仓库资产盘点中长期未关闭的 P0 许可证/权属缺口，建立逐路径登记基线，不试图以目录或统一许可证替代文件级审查。

- 固定基线：`main@aac8e081ca733265f34b08000647473d02e23e72`
- Git Tree：`de8987f4d90924de1937bcc62efe38804c255fda`（完整递归 Tree，上一轮已确认 `truncated=false`）
- 资产范围：既有 CSV 中的 386 个唯一文件路径。
- 方法：复用原资产 CSV 的 path、Blob SHA、大小、资源类型、域和既有内容审查范围；为每个资产补充许可证据状态、权利人状态、再分发状态和下一步审查动作。
- 新增的 PR 审计报告、策略文件和登记表本身不属于该历史 main 基线的 386 项，不能混入基线计数。

这是一个治理和元数据工作底稿，不构成法律意见、授权证明、完整开源许可审计或再分发批准。

## 2. 结果摘要

登记表覆盖 386/386 个基线路径，统计如下：

| 登记状态 | 数量 | 解释 |
| --- | ---: | --- |
| 根 `LICENSE` 中存在 MIT 文本 | 1 | 仅确认许可证文件文本存在；权利人和覆盖范围未证实 |
| Python 包元数据引用根 MIT | 1 | 仅确认 `pyproject.toml` 声明；实际分发文件清单与逐文件权利待核 |
| 已做有限源码/CI 静态来源审查 | 35 | 复核过部分来源和执行副作用；不是逐文件许可放行 |
| 已做有限参考软件来源审查 | 8 | 已记录 rustypot/LeRobot/FEETECH 来源线索；不是完整 NOTICE/授权或再分发审查 |
| 未记录资产级许可审查 | 341 | 不代表文件必然侵权；表示没有足够证据作许可判断 |

**关键统计：** 386 项中，当前权利人状态全部登记为 `UNVERIFIED`，再分发状态全部为 `UNDETERMINED`；本登记没有将任何一项标记为 `REDISTRIBUTION_APPROVED`。已有技术主张的 P0/P1 定向审查、源码静态审查或 CI 通过记录，不自动构成权利审查。

## 3. 已确定与未确定的事项

### 3.1 已确定

- 根 `LICENSE` 的文本是 MIT License。
- `pyproject.toml` 通过 `license = { file = "LICENSE" }` 引用根文件，并设置 MIT classifier。
- 根 README 将 Knowledge Vault 与 Python Toolkit 描述为两个组成部分，但没有逐资产说明许可证覆盖边界。
- 既有审查记录 GitHub repository API license detector 返回 `Other / NOASSERTION`。它是仓库自动识别/元数据状态，不能单独解释为法律结论。
- 先前对 35 个核心源码/脚本/测试/CI 文件和 8 个参考项目软件资产做过限定范围静态审查；其来源线索不等于逐文件作者权利、NOTICE、专利、第三方例外和分发授权全部关闭。

### 3.2 仍未确定（P0）

1. `Robot Knowledge Basement Contributors` 署名对应的实际权利人、各贡献者提交内容的作者身份，以及维护者是否取得了适用于 MIT 声明范围的授权。
2. 根 MIT 的预期路径覆盖范围：Python Toolkit、全部 Markdown 知识文章、项目案例、模板、TaskPlan 历史、图片/图表、数据集和模型是否都在同一授权内。
3. Python wheel/sdist 的实际文件清单，以及包发布物中各文件对应的版权/第三方许可。
4. 知识文章内引用的厂商手册、标准、论文、产品图表和数据表的逐项转载权限。
5. 代码和工作流中的外部片段、生成代码、上游 NOTICE、依赖子组件和第三方贡献的逐文件核验。
6. 用户/组织/客户项目资料、BOM、测试日志和历史记录的发布授权与保密范围。

因此不修改根 `LICENSE`，不批量新增 `SPDX-License-Identifier: MIT`，也不向外宣称整个仓库所有内容均按 MIT 发布。

## 4. 风险分层与处理

- **P0：权利人/范围未知。** 根 MIT 覆盖意图、贡献者权属、项目/客户材料授权、第三方源码或非公开资料。未解决前不扩大复制/分发范围。
- **P1：逐文件来源与条款核对。** 代码片段、厂商图表、标准/论文摘录、图片/CAD/模型/数据集；逐项记录原始来源、许可证/条款、NOTICE 和改动。
- **P2：发布元数据和自动化。** 在文件级记录稳定后再评估 REUSE/SPDX 或脚本检查；不以机器识别标签代替实际权利核验。

## 5. 文件登记表的解释

`2026-11-15-knowledge-asset-license-rights-register.csv` 以 386 个历史 main 基线对象逐条登记：

- `prior_content_audit_scope` 只复用既有资产盘点中的内容审查记录；
- `license_evidence_status` 描述目前已有的许可证据强度，不是“合规评分”；
- `rights_holder_status` 和 `redistribution_status` 保持未知，除非后续取得具体证据；
- `blob_sha` 和 `baseline_commit` 用于固定审查对象身份，不是作者身份/签名或授权证明；
- `next_rights_review_action` 给出下一步，不表示该动作已经执行。

所有 386 行均需随文件内容/上游来源变化重新检查。基线资产清单本身不覆盖 PR 分支新增文件；新增文件应在后续审查时加入本登记表或新的快照版本。

## 6. 后续执行顺序

1. 先建立贡献者/权利人名册和授权证据：区分用户原创、助手生成/协助、第三方改编和外部摘录；没有可验证授权时保留 UNKNOWN。
2. 生成 Python Toolkit 的 wheel 与 sdist 文件清单，对每个打包文件追踪权利来源；不得用包元数据反推知识库正文许可。
3. 完成 35 项核心代码/CI 文件与 8 项参考软件文件的逐文件 provenance、版权、许可证、NOTICE、专利及第三方依赖审查。
4. 按 P0 安全/硬件、项目案例、标准法规、厂商资料和外部代码优先级，逐篇审核知识文章中的第三方文字、图片、表格和数据。
5. 核对 GitHub repository license metadata；若需更改根许可证或其范围，先由权利人确认后再变更。
6. 只有完成必要证据后，才可逐项将登记状态升级到 `REDISTRIBUTION_APPROVED`；保持 `00-01` 进行中。

## 7. 外部项目合并门禁

本轮没有改变 `14-EXT-02` 状态，没有复制或引入 `MotionControlAlgorithms` 代码，没有创建 submodule，也没有开始目标仓库集成。第三方依赖来源/许可/SBOM、目标仓库子目录/子模块与独立 CI 验证、导入 commit/文件范围/分支及用户明确授权仍为独立前置门。此登记不替代也不关闭这些门禁。

## 8. 证据与关联资料

- [全仓库 Git Tree 资产基线重建](2026-11-15-full-repository-asset-tree-reconciliation.md)
- [参考项目资产与许可证边界抽样审查](2026-11-15-reference-project-content-and-license-boundary-review.md)
- [源码、脚本、测试与 CI 来源/副作用审查](2026-11-15-code-ci-provenance-and-side-effect-review.md)
- [知识资产许可证与权利来源治理规范](../engineering/Knowledge-Asset-License-and-Rights-Policy.md)
- [原始资产清单](2026-11-03-knowledge-asset-inventory.csv)
