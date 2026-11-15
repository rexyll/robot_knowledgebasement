# 00-01｜新增参考项目资产与许可证边界抽样审查（2026-11-15）

## 1. 审查范围与结论

本轮在完整 Git Tree 资产基线之后，对新增资产中的桌面型物料分拣机械臂参考项目数据和 STS3215 软件工具进行定向内容审查，并检查仓库根许可证、Python 包许可证元数据及 CI 测试发现范围。

本轮是**限定范围的内容/来源审查**，不是全仓库主张级验收，也不是法律意见、产品风险评估或硬件验收。

重点结论：

1. 根目录 `LICENSE` 文本为 MIT，`pyproject.toml` 的 `license = { file = "LICENSE" }` 和 MIT classifier 与之匹配；但 GitHub repository API 当前返回 `key=other / spdx_id=NOASSERTION`。该自动识别元数据与实际文件/包配置不一致，应作为仓库元数据缺口继续处理。
2. 根许可证没有给出清晰的资产范围映射，不能仅凭一个 MIT 文件就推定所有知识文章、厂商资料、第三方代码、模型/数据、引用摘录和外部项目案例都由仓库贡献者拥有并可按 MIT 再分发。
3. 参考项目新增的 4 个 CSV 是草案/输入模板：需求验收判据、方案选型证据、负载数值、风险评级均保留 Draft/TBD/Open，没有被包装成已批准需求、实测性能或完成的风险评估。
4. 参考项目新增的 8 个软件/配置资产采用明确的外部来源基线：rustypot v1.13.1 固定 commit、LeRobot 版本提示和 FEETECH 通用教程来源。只读采集器限定为注入的 `read()` 接口，未提供连接、配置、写入或断开能力；但这不等于真实总线或硬件安全验收。
5. FEETECH 官方通用 STS 教程 PDF 的链接已在旧来源台账 #253 登记为曾经读取；本轮重新访问时未能从官网取回，因此此处不把它提升为本轮重新核验通过。通用单位换算继续标记为未校准、非 SKU 专属。
6. 现有 CI 的 pytest 配置明确包含根 `tests/` 与 `knowledge/projects/reference-desktop-manipulator/software/tests/` 两个 testpaths；PR #22 当前 Python 3.10/3.11/3.12 矩阵通过，故参考项目的三组测试位于该测试发现范围内。此项仍只是软件测试证据，不是实机、SKU 校准或串口协议验收。

## 2. 许可证与再分发边界

### 2.1 仓库根许可证

- `LICENSE`：MIT License，版权字段为 “Robot Knowledge Basement Contributors”，年份 2026。
- `pyproject.toml`：Python 项目使用该 LICENSE 文件，并包含 MIT License classifier。
- GitHub repository API 的 license detector 返回 `Other / NOASSERTION`，并未将仓库识别为 MIT。

需要补齐的治理证据：

- 明确 MIT 声明覆盖哪些由贡献者原创的代码/文档，以及哪些内容单独适用来源方许可。
- 确认所有贡献者对声明覆盖范围拥有相应权利或授权；不能把组织性版权字段视为完整的作者/权利人名册。
- 对外部代码、厂商手册、标准摘录、模型/数据、第三方项目案例建立独立来源与许可记录；必要时保留原始 NOTICE、版权和链接。
- 核实 GitHub 仓库许可元数据为何仍为 `NOASSERTION`，不要通过修改知识资产文本掩盖元数据状态。

**当前判断：** 根许可证文件和 Python 包元数据均已存在且文本一致；整个知识库内容的逐资产许可覆盖范围尚未建立，因此“全库 MIT”不是已验证结论。

### 2.2 rustypot / LeRobot / FEETECH 来源链

- `sts3215_readonly_fields.json` 记录 LeRobot 0.6.2 作为静态审查上下文，并固定 rustypot commit `7aa85e13143594ea4fd4ed9f29e3e29d39b5de85`；文件明确说明这是源码审查基线，不是设备运行时锁定。
- `register_definition_audit.py` 读取用户提供/固定的 rustypot 源文件文本并与白名单比较；该审计代码声明无需网络访问或 Rust 运行时。
- 来源台账 #640 记录上述 rustypot 固定源文件的原始大小和 SHA-256；#641 记录同一 commit 的仓库级 Apache-2.0 LICENSE。该许可证证据不自动证明所有历史贡献或第三方子组件的许可范围。
- 来源台账 #253 记录 FEETECH 2022-06-18 通用 STS 教程及负载、电压、温度、电流比例。本轮官网 PDF 重新访问失败，所以相应单位依据继续作为“已有历史来源记录、待本轮重新取回”的项目，不提升为新通过。
- 通用 STS 单位比例不是 C001/C018/C047 等具体 SKU 的校准数据，也不是测量精度或实际硬件行为的证明。

**禁止推导：** 根项目 MIT 不会自动覆盖 rustypot 的 Apache-2.0、FEETECH 的资料权利或 LeRobot 的许可；本参考代码也不能因为引用其接口就等同于完整引入或再分发该上游项目。

## 3. 新增参考项目数据资产审查

| 文件 | 本轮观察 | 不得误判为 |
| --- | --- | --- |
| `05-需求追踪矩阵.csv` | 需求来源多为用户任务假设、流程或风险分析；状态为 Draft，部分验收标准 TBD | 已批准 PRD/SYS、经测试的功能/性能结论 |
| `06-方案比较矩阵.csv` | 对成品教学臂、模块化关节、分立电机方案作定性比较；开放接口、维护、供应链与精确型号证据仍待核实，未预选方案 | 供应商横向实测比较或已完成选型 |
| `07-任务负载谱与输入模板.csv` | 质量、几何、节拍、速度、加速度、供电、热、成本和寿命等均为 TBD，且列出建议采集方法/责任角色 | 已取得的负载谱、器件额定工况或设计输入 |
| `09-初始风险登记.csv` | 已列出机械、电气、运动、控制、维护与网络风险源；严重度、暴露、避免可能性和风险等级仍 TBD，状态 Open | 经专业人员确认的风险评估或安全等级分配 |

该批 CSV 目前更适合作为**待输入的工程模板与决策记录**；应保留 TBD、Draft、Open，等待用户需求、实物、供应商资料和专业评审形成证据后再更新。

## 4. 新增软件资产的限定审查

本次审阅的 8 个软件资产包括：

- `engineering_units.py`、`readonly_capture.py`、`register_definition_audit.py`、`__init__.py`
- `sts3215_readonly_fields.json`
- `test_engineering_units.py`、`test_readonly_capture.py`、`test_register_definition_audit.py`

### 4.1 只读边界

`readonly_capture.py` 只要求注入一个提供 `read()` 方法的对象，代码自身不创建/连接/配置/断开总线，也没有写操作入口；其测试含 AST 检查，拒绝出现 write、sync_write、配置舵机、断开和访问私有 bus 等调用。

这是**代码接口和测试的只读约束**，并不证明任意调用者注入的对象必然安全，也不证明真实串口、供电、ID、固件、控制板和机器人已通过检查。采集是逐字段读取，不是多轴同步快照；失败记录也不得被补成 0 或当作有效读数。

### 4.2 工程单位转换

`engineering_units.py` 仅对已解码整数提供通用负载、电压、温度和电流比例换算；原始解码整数保留，超范围拒绝或告警，输出显式标记 `not_calibrated`。位置和速度转换被有意排除，因模式/编码语义尚未形成充分一致的转换契约。

这避免了将通用比例包装成具体型号测量精度，但 FEETECH PDF 仍需重新取得并逐项核对地址、单位、符号、量程和型号适用边界。

### 4.3 白名单和寄存器定义对照

JSON 白名单固定了 rustypot 版本/commit，并区分可读字段、地址/宽度、编码和转换器说明；`register_definition_audit.py` 用来比对白名单与固定上游源文件。来源台账 #640/#641 提供源码摘要和仓库许可证证据；这不等于设备实际安装该版本，也不等于供应商已确认确切 SKU/固件的寄存器语义。

### 4.4 测试与工程证据边界

根 `pyproject.toml` 的 pytest `testpaths` 显式包括上述参考项目软件测试目录。PR #22 的 Python 3.10、3.11、3.12 测试矩阵已通过。该结果只说明仓库内可执行的软件测试范围通过，不证明真实设备通信、寄存器读值、单位校准、故障安全或实机抓取动作通过。

## 5. 尚未解决的资产缺口与行动

### P0

1. 给仓库所有内容资产建立许可范围矩阵：贡献者原创、第三方改编、事实性数据、标准/厂商资料、模型/数据、示例和外部代码分别标注权利来源、允许用途、是否可再分发和证据。
2. 明确根 MIT LICENSE 的预期覆盖边界，并处理 GitHub API `NOASSERTION` 元数据不一致；在权利范围未明时保持原文件，不擅自扩张许可证。
3. 对参考项目使用的 FEETECH 官方教程重新取得可稳定访问的原始资料，核对单位比例、字段地址和适用范围；精确 SKU/固件仍需供应商资料及实物核验。

### P1

1. 审查其余新增源码/脚本/测试、工作流与依赖的作者/来源、版权、许可证、NOTICE、外部下载固定点和执行副作用；本次对它们仅作初步抽样，尚未完成逐文件 provenance 审查。
2. 对 05/06/07/09 的 Draft/TBD 输入等待正式需求、测量和专业评审；不得提前将参考项目任务计划标为设计冻结。
3. 持续审查外部依赖与知识引用的版本、来源和许可证；把技术主张与源文件行/章节、适用 SKU/版本和测试证据关联。

## 6. 与 MotionControlAlgorithms 延期门禁的关系

本轮没有修改 MotionControlAlgorithms 上游、没有复制或引入其代码，也没有更改 `14-EXT-02` 的状态。

`14-EXT-02` 仍为进行中：KickCAT CeCILL-C 与本地差异文件的逐项处理、MIT/WTFPL-2.0 第三方通知、ROS/Gazebo package.xml MIT 元数据来源/许可意图、完整可选构建依赖闭包、CycloneDX/SBOM 生成/校验和分发场景审查均未全部关闭。目标仓库子目录/submodule/独立 CI 集成验证也没有在本轮执行，导入 commit、精确文件范围和实施分支尚未形成最终批准基线。

因此，用户规定的所有前置条件未满足，合并继续延期。

## 7. 证据入口

- [全仓库资产 Tree 对账](2026-11-15-full-repository-asset-tree-reconciliation.md)
- [资产清单 CSV](2026-11-03-knowledge-asset-inventory.csv)
- [参考项目 README](../../knowledge/projects/reference-desktop-manipulator/README.md)
- [STS3215 只读白名单说明](../../knowledge/projects/reference-desktop-manipulator/24-STS3215-rustypot-v1.13.1只读寄存器白名单.md)
- [外部源码完整性审计：rustypot](2026-11-04-external-source-integrity.md)
- [外部项目集成治理策略](../engineering/External-Project-Integration-Policy.md)

