# Stäubli SocketV2 Traceability Schema v1.0.0 与 CI Policy Contract

- 节点：§9.3.312 / SERVO-895
- 日期：2026-11-10
- 上游基线：`ICube-Robotics/staubli_driver_ros2@bd658e2d266e315d2ee35f985fb352ea88306b79`
- 输入：SERVO-894 五维追踪报告；F01–F16、PLUG-L01–L12；SERVO-881 RACE/EXEC目录。
- 范围：知识库内定义机器可检查的数据契约与CI策略；不修改上游源码、不授权A1.1实现。

## 1. 交付物

1. JSON Schema：`docs/schemas/staubli-lifecycle-traceability.schema.json`，Draft 2020-12，版本`1.0.0`。
2. 规范化manifest：`docs/audits/2026-11-10-staubli-socket-v2-lifecycle-traceability-manifest-v1.json`，包含F01–F16与PLUG-L01–L12共28条记录。
3. CI policy：`docs/ci/staubli-lifecycle-traceability-policy.yml`，定义状态、证据、Owner、Coordinator、引用解析和fail-closed规则。
4. 本报告定义边界、静态检查结果与后续执行门禁。

## 2. 数据模型与稳定ID

- `schema_version`固定为`1.0.0`；破坏性字段/语义变化必须升级主版本，不得静默重解释既有manifest。
- 记录ID稳定且唯一：F01–F16、PLUG-L01–L12；竞态引用使用RACE-01–RACE-16、EXEC-01–EXEC-04。
- 每条记录必须有event、resource、failure_states、required_evidence、evidence、status和test_refs。
- manifest固定上游仓库与commit，避免审查对象漂移。

## 3. Owner cardinality 与清理执行权

- 每条资源记录使用单值`resource_owner`和单值`reconcile_coordinator`字段；在数据结构上拒绝零个或多个Owner/Coordinator。
- Resource Owner保证对象/handle生命周期不提前结束；Reconcile Coordinator唯一串行化cancel/drain/join/close/session reconcile。二者允许不同。
- 跨generation资源不得共用含糊Owner；Owner handoff必须prepare/commit原子转移，commit失败时源Owner仍有效。
- QuarantineManager仅接管、登记和有界排程，不成为第二套native close执行者。

## 4. 状态与证据合同

状态词汇：`SPECIFIED`、`STATIC_REVIEWED`、`DESIGN_REVIEWED`、`RUN_PASS`、`RUN_FAIL`、`NOT_RUN`、`BLOCKED`。

| 状态 | 最低证据 |
|---|---|
| SPECIFIED | design_spec |
| STATIC_REVIEWED | design_spec + source_review |
| DESIGN_REVIEWED | design_spec + source_review |
| RUN_PASS / RUN_FAIL | test_log + environment_manifest + artifact_hash |
| NOT_RUN | 不要求运行证据；必须保留未执行事实，不得映射为PASS |
| BLOCKED | 必须给出明确blocker；不得从汇总中隐藏 |

运行PASS必须有不可变环境身份、命令/退出码、原始日志URI、工件SHA256、测试范围与结果。硬件验收还必须记录控制器/机器人型号、固件/配置版本、安全链与模式、测量值/验收限值及可归属记录。

## 5. Cross-reference 与 CI policy

CI依次执行JSON parse、JSON Schema、稳定ID唯一性、Owner/Coordinator cardinality、状态—证据兼容性、引用解析、URI/hash验证。任何错误fail closed。

- 重复record ID或reference ID：ERROR。
- test_refs不在reference_catalog：ERROR。
- 缺少该状态必需证据：ERROR。
- RUN_PASS缺少环境/日志/hash：ERROR。
- BLOCKED缺少blocker：ERROR。
- NOT_RUN不得被自动升级；UNKNOWN/RESIDUAL不得自动清除。
- plugin code lease非零时禁止unload；Quarantine接管不构成DSO卸载证明。
- A1.1 gate保持BLOCKED，直到外部clean Jazzy build/test、install consumer、ABI、plugin和授权门禁均取得证据。

## 6. 本轮静态一致性检查

针对生成的manifest执行了静态检查：
- 记录数：`28`（预期28）。
- record ID唯一：通过。
- reference catalog ID唯一：通过（`20`项）。
- 每条记录恰有一个resource_owner字段和一个reconcile_coordinator字段：通过。
- 所有test_refs均可在reference_catalog解析：通过。
- SPECIFIED记录均包含PRESENT design_spec证据：通过。

此处是对manifest结构与引用集合的静态检查，不等于已运行JSON Schema validator、CI pipeline或任何C++/ROS测试；不得把它标记为CI PASS。

## 7. 状态与限制

| 项目 | 状态 |
|---|---|
| Schema v1.0.0定义 | SPECIFIED |
| 28条manifest规范化 | SPECIFIED |
| CI policy contract | SPECIFIED |
| 本轮静态一致性检查 | STATIC_REVIEWED |
| 独立JSON Schema validator/CI执行 | NOT_RUN |
| 自动化交叉引用检查器实现 | NOT_RUN |
| C++编译、gtest、故障注入、TSan/ASan | NOT_RUN |
| ROS lifecycle/plugin load-unload | NOT_RUN |
| clean Jazzy/install consumer/ABI | NOT_RUN或BLOCKED |
| VAL3/CS9、SIL/HIL、FAT/SAT、实机 | NOT_RUN |
| A1.1 | BLOCKED |

未修改固定上游、未创建/应用/合并上游PR；`TODO-EXT-001`仍未授权。SERVO-894报告指出的§9.3.281–§9.3.294历史同步缺口继续透明保留。

**下一节点：§9.3.313 / SERVO-896：定义独立manifest validator与CI最小实现规格（JSON Schema validator、cross-reference/owner/evidence policy checks、负向fixture与CI退出码）；先在知识库侧实现并自测，不触碰上游driver。**
