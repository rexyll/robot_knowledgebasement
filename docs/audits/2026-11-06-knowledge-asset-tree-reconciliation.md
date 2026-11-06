# 2026-11-06 知识资产 Git Tree 对账与清单刷新

- 审计日期：2026-11-06
- 对象：`rexyll/robot_knowledgebasement` 的 `main` 分支
- 方法：读取 GitHub Git Trees API 的递归文件树；按仓库实际 Blob SHA、文件大小对照知识资产清单
- 性质：仓库结构/元数据对账，不是正文专业审查、主张级验收或代码运行测试

## 1. 当前仓库结构快照

| 指标 | 当前数量 |
|---|---:|
| Git Tree Blob（全部文件对象） | 254 |
| Markdown 文件 | 206 |
| `knowledge/` 下 Markdown | 142 |
| `docs/` 下 Markdown | 61 |
| `docs/TaskPlan/` 下章节 TaskPlan | 26 |

本次最终快照包含本报告自身：以 Git Tree 为文件存在性和 Blob 元数据的唯一对账依据；目录名/旧 TaskPlan 统计不作为当前文件数证据。

## 2. 旧资产清单差异

刷新前的 `2026-11-03-knowledge-asset-inventory.csv` 有 151 条有效记录，其中 125 条属于知识文件。另发现并移除了 1 条空白/无路径记录。

- 清单中原有路径均可在当前 main Git Tree 找到；未发现清单路径已删除或无法解析。
- 24 条已有记录的 Blob SHA 和/或文件大小已过期，已按当前 Git Tree 更新。
- 当前有 17 份 `knowledge/` Markdown 未进入旧清单；本轮逐一补入。
- 新增资产的优先级和类型只用于排队，不表示其技术主张已审定；所有新增知识文件状态均设为 `unaccepted_claim_level_review_pending`。
- 刷新后清单共 168 条有效资产记录，其中 `knowledge/` Markdown 142 条，与当前 Git Tree 的 142 条一致。

### 2.1 本轮新增的知识资产

- `knowledge/manipulation/全身控制与接触动力学.md`
- `knowledge/projects/reference-desktop-manipulator/10-成品教学臂与模块化关节基准调研.md`
- `knowledge/projects/reference-desktop-manipulator/11-官方手册与接口深度核验.md`
- `knowledge/projects/reference-desktop-manipulator/12-控制板供应商澄清与电气验证计划.md`
- `knowledge/projects/reference-desktop-manipulator/13-LeRobot版本锁定与运行时依赖审计.md`
- `knowledge/projects/reference-desktop-manipulator/14-LeRobot故障传播与断连恢复控制边界核验.md`
- `knowledge/projects/reference-desktop-manipulator/15-rustypot同步读重试与SO-Follower当前调用链核验.md`
- `knowledge/projects/reference-desktop-manipulator/16-SyncWrite动作发送与逐轴确认边界核验.md`
- `knowledge/projects/reference-desktop-manipulator/17-SyncWrite动作发送与下一周期反馈时序核验.md`
- `knowledge/projects/reference-desktop-manipulator/18-SO-Follower最小健康反馈读取闭环核验.md`
- `knowledge/projects/reference-desktop-manipulator/19-STS3215-Status位与保护报警语义核验.md`
- `knowledge/projects/reference-desktop-manipulator/20-SO101控制板与LeRobot宿主边界核验.md`
- `knowledge/projects/reference-desktop-manipulator/21-STS3215保护寄存器单位与阈值逻辑核验.md`
- `knowledge/projects/reference-desktop-manipulator/22-C046保护规格与STS通用寄存器证据矩阵.md`
- `knowledge/projects/reference-desktop-manipulator/23-STS3215准确型号绑定与实机只读基线方案.md`
- `knowledge/projects/reference-desktop-manipulator/24-STS3215-rustypot-v1.13.1只读寄存器白名单.md`
- `knowledge/projects/reference-desktop-manipulator/TODO.md`

### 2.2 Blob SHA/文件大小已刷新的旧记录

- `knowledge/algorithms/README.md`
- `knowledge/algorithms/轨迹优化与运动控制.md`
- `knowledge/ecosystem/manufacturers/README.md`
- `knowledge/getting-started/09-03-电子电气设计.md`
- `knowledge/getting-started/09-04-传感器选型与标定.md`
- `knowledge/manipulation/README.md`
- `knowledge/projects/README.md`
- `knowledge/projects/三项目关系总览.md`
- `knowledge/projects/项目-amr.md`
- `knowledge/robots/工业机器人.md`
- `knowledge/safety/安全防护器件.md`
- `knowledge/sensors/IMU.md`
- `knowledge/software/advanced-topics/11-扩展知识.md`
- `knowledge/software/advanced-topics/README.md`
- `knowledge/software/advanced-topics/ROS1与迁移.md`
- `knowledge/software/ROS与ROS2.md`
- `knowledge/software/视觉软件栈.md`
- `knowledge/software/调度系统RMS.md`
- `knowledge/manipulation/机械臂操作与抓取基础.md`
- `knowledge/projects/reference-desktop-manipulator/README.md`
- `knowledge/ecosystem/知识生态兼容矩阵.md`
- `docs/audits/2026-11-04-sbom-generator-toolchain-lock.md`
- `TaskPlan.md`
- `docs/链接台账.md`

## 3. 清单字段与解释

清单新增字段：

- `metadata_reconciled_date`：最近一次 Git Tree 元数据对账日期。
- `metadata_reconciliation_scope`：本轮只刷新路径对应的 Blob SHA 和字节数，不代表读取正文或验证技术主张。

原有 `latest_scan_date` / `latest_scan_scope` 保留其历史正文扫描/定向审查语义，不用元数据刷新覆盖历史审查记录。CSV 已统一为标准双引号转义格式，并移除空白记录。

## 4. 验证边界与后续工作

- Git Tree 对账可以证明文件路径存在、Blob SHA/文件大小与快照一致；不能证明内容正确、来源有效、链接存活、许可证允许或产品/安全结论适用。
- 本轮未对 142 份知识文件重新进行统一全文结构扫描，也未进行 142 份逐句 claim-level 审查；已有专题审计记录仍按各自范围解释。
- 00-01 继续进行中。下一步应按 P0/P1/P2 和内容风险对新增/变更资产做分批 claim-level 审查，并对历史 96/120 结构扫描口径重新计算当前覆盖率。
- 不因清单更新、文件数量增长或专题文章增补，将任何未完成验收节点改为完成。
