# Stäubli SocketV2 RACE/EXEC Test Case Catalog 与双向追踪验收

- 节点：§9.3.314 / SERVO-897
- 日期：2026-11-11
- 仓库：`rexyll/robot_knowledgebasement`，分支`main`
- 固定上游基线：`ICube-Robotics/staubli_driver_ros2@bd658e2d266e315d2ee35f985fb352ea88306b79`
- 输入：SERVO-894五维生命周期追踪、SERVO-881并发/锁顺序/Executor竞态设计、SERVO-896 Manifest Schema/Validator/CI。
- 范围：知识库侧机器可读测试目录、目录Schema、Manifest双向引用Validator、负向测试与CI；不修改Stäubli上游driver。

## 1. 交付物

1. **机器可读测试目录：** `docs/audits/2026-11-11-staubli-socket-v2-race-exec-test-case-catalog-v1.json`。
2. **目录Schema：** `docs/schemas/staubli-race-exec-test-case-catalog.schema.json`，Draft 2020-12声明，针对当前使用关键词的专用子集校验。
3. **双向追踪Validator：** `scripts/validate_staubli_test_case_catalog.py`。
4. **负向测试：** `tests/test_staubli_test_case_catalog.py`。
5. **Manifest映射：** 为原先未被任何F/PLUG记录引用的RACE-01、RACE-04、RACE-08、RACE-10、RACE-12和EXEC-02补齐关联；每个Catalog test case反向列出其Manifest record IDs。
6. **CI：** `.github/workflows/ci.yml`在Python 3.10/3.11/3.12矩阵中执行Catalog schema和双向追踪检查，并归档JSON报告。
7. **Policy：** `docs/ci/staubli-lifecycle-traceability-policy.yml`增加Manifest/Catalog双向映射规则。

## 2. 20项稳定测试引用

所有测试用例均包含title、scenario、preconditions、stimulus、expected assertions、test harness、manifest_record_ids、execution_state与evidence_contract。

| ID | 测试主题 | 关键断言 |
|---|---|---|
| RACE-01 | 同一Entry重复claim | 同一generation最多一个attempt token |
| RACE-02 | retry claim与shutdown admission close | close线性化点后不再新claim，既有任务计入drain |
| RACE-03 | owner transfer prepare与shutdown | 原子提交或完全回滚，恰有一个owner |
| RACE-04 | generation替换后的stale completion | 旧generation结果不得覆盖新generation |
| RACE-05 | Executor拒绝任务 | 恢复可查询pending状态并保留owner |
| RACE-06 | Executor shutdown与submit/accept握手 | 不丢任务、不重复执行 |
| RACE-07 | completion提交时重复retry | token/revision防止重复提交 |
| RACE-08 | 跨Entry锁顺序 | 不发生逆序嵌套或死锁 |
| RACE-09 | retry deadline到期 | 超时不释放Core owner、不等同清理成功 |
| RACE-10 | retry flood与shutdown drain公平性 | shutdown获得有界进展，不无限饥饿 |
| RACE-11 | worker callback重入stop/shutdown | 明确ASYNC/WOULD_DEADLOCK，不self-join |
| RACE-12 | completion dispatcher消失 | 内部fallback记账一次且owner保留 |
| RACE-13 | active callback与plugin unload gate | callback/pending/worker/code lease清零前不得unload |
| RACE-14 | worker执行时释放最后外部handle | worker/lifecycle owner持续保活Core |
| RACE-15 | 同一key重复complete/retry | 幂等，无double close/join/free |
| RACE-16 | Manager容量满时owner handoff | 拒绝新handoff，源owner保持有效 |
| EXEC-01 | Executor停止后seal Manager | 可生成snapshot/report且保留residual owner |
| EXEC-02 | queued取消与running完成竞态 | queued不执行，running结果仅提交一次 |
| EXEC-03 | ROS context shutdown与Node销毁 | 无悬空Node/callback target |
| EXEC-04 | worker退出与外部join | 外部owner join，无detach/self-join |

SERVO-881原设计中的LOCK-01/LOCK-02仍保留为锁顺序/回调阻塞补充验证项；它们不是当前Manifest稳定引用目录中的RACE/EXEC ID，因此本Catalog不擅自扩展既有20项稳定引用集合。

## 3. 双向映射合同

### 3.1 Manifest → Catalog

- Manifest `reference_catalog`必须精确覆盖RACE-01–RACE-16和EXEC-01–EXEC-04。
- 每条Manifest记录的`test_refs`必须解析到Catalog中的同名`test_id`。
- 20个引用均至少关联一条Manifest记录，不允许悬空、未使用引用。

### 3.2 Catalog → Manifest

- 每个Catalog case必须至少声明一个`manifest_record_ids`。
- 每个声明的record ID必须存在于28条Manifest记录中。
- Catalog反向映射集合必须与Manifest按`test_refs`计算出的正向集合完全相等；不接受单向存在或部分映射。
- Catalog与Manifest的reference catalog集合必须完全一致；重复ID和缺失ID均fail closed。

本轮将原先在reference catalog中存在、但未被任何记录使用的6项引用补齐到相关故障/生命周期记录，消除了“引用存在但没有具体场景追踪”的空洞。

## 4. Evidence contract与执行状态

每个测试case要求的证据包：
- `test_log`
- `environment_manifest`
- `artifact_hash`
- `state_snapshot`
- `event_trace`

Hash算法为SHA-256。证据必须能够复现测试环境、测试ID、attempt token、resource generation/revision、前后状态、owner保留/清理结果和确定性事件序列。

**全部20项`execution_state`固定为`NOT_RUN`。** Schema使用`const: NOT_RUN`，静态CI只验证目录结构和追踪完整性，不得将测试执行状态升级为RUN_PASS。设计规格、schema validation和Python仓库测试都不是Stäubli C++运行时测试证据。

## 5. CI实际结果

- **Workflow：** CI #3477
- **Run ID：** `42938097270`
- **Head commit：** `299ead52fcf6b84ad307ede18e2e4fc0a9c6b9fd`
- **结果：** SUCCESS
- **Python矩阵：** 3.10、3.11、3.12全部成功。
- **每个版本：**
  - Lifecycle Manifest Validator：28 records / 20 references PASS。
  - RACE/EXEC Catalog Validator：28 Manifest records / 20 cases / 20 references PASS，全部NOT_RUN。
  - Ruff：PASS。
  - Pytest：67 passed。
- **其他作业：** OSV锁定依赖扫描与CycloneDX SBOM生成均成功。
- **报告：** 每个Python矩阵版本归档Manifest验证报告和Catalog双向追踪报告，保留14天。

运行记录：[GitHub Actions CI #3477](https://github.com/rexyll/robot_knowledgebasement/actions/runs/42938097270)。

### CI修正记录

中间提交的CI曾按预期失败：
1. 首次lint发现两处validator和四处test fixture超出Ruff行宽，已格式化修复。
2. 随后两个负向测试把Schema层拒绝的非法record ID误当作Policy层unknown ID断言，并错误假设RACE-01映射包含F01。已将测试改为验证Schema pattern拒绝非法ID，并从实际reverse mapping移除一个已声明ID验证双向差异。
3. 最终Run #3477全矩阵通过；上述中间失败均已由最终提交修正，不隐藏失败历史。

## 6. 验收状态与边界

| 项目 | 状态 |
|---|---|
| 20项RACE/EXEC机器可读Catalog | IMPLEMENTED |
| Catalog JSON Schema当前关键词子集 | CI_PASS |
| Manifest 28条记录 ↔ Catalog 20项用例双向追踪 | CI_PASS |
| 每项必需字段与Evidence contract | CI_PASS |
| 全部20项execution_state保持NOT_RUN | CI_PASS |
| Validator负向测试与CLI路径 | CI_PASS |
| Python 3.10/3.11/3.12仓库测试 | CI_PASS（每版本67 passed） |
| Ruff / OSV / SBOM | CI_PASS |
| LOCK-01/LOCK-02补充用例正式纳入稳定Catalog | NOT_IN_SCOPE，仍待后续节点决定 |
| Fake executor/barrier/fault injection真实运行 | NOT_RUN |
| Stäubli C++/ROS/ABI/plugin DSO/TSan/ASan | NOT_RUN |
| VAL3/CS9/SIL/HIL/FAT/SAT/实机 | NOT_RUN |
| A1.1 | BLOCKED |

本轮只验证知识库侧JSON数据、Schema子集、双向引用、Python工具和CI；不代表C++/ROS driver已实现这些测试，更不代表资源释放安全或工业验收通过。未修改固定上游，未创建/应用/合并上游PR；`TODO-EXT-001`仍未授权；A1.1继续BLOCKED。§9.3.281–§9.3.294历史TaskPlan同步缺口继续透明保留。

**下一节点：§9.3.315 / SERVO-898：定义确定性Fake Harness接口与统一Runtime Evidence Bundle schema（clock/barrier/executor/fault injector、event trace、state snapshot、environment identity、artifact hashing），形成可供未来上游测试实现消费的接口规格；本阶段仍不修改上游driver，不执行或伪造runtime PASS。**
