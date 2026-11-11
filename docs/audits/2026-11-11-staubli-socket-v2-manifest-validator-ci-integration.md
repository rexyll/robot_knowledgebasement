# Stäubli SocketV2 Lifecycle Manifest Validator 与 CI 自动化验收

- 节点：§9.3.313 / SERVO-896
- 日期：2026-11-11
- 仓库：`rexyll/robot_knowledgebasement`
- 上游审查基线：`ICube-Robotics/staubli_driver_ros2@bd658e2d266e315d2ee35f985fb352ea88306b79`
- 输入：SERVO-894 生命周期五维追踪、SERVO-895 Schema v1.0.0、28条Manifest及CI Policy Contract。
- 范围：仅实现知识库侧校验器、负向测试与GitHub Actions接入；不修改Stäubli上游driver，不授权A1.1。

## 1. 交付物

1. **Validator：** `scripts/validate_staubli_lifecycle_manifest.py`。
2. **测试：** `tests/test_staubli_lifecycle_manifest_validator.py`，包含正向、负向及CLI退出码测试。
3. **CI：** 修改`.github/workflows/ci.yml`，在现有Python 3.10/3.11/3.12矩阵中运行validator，并归档每个Python版本的JSON验证报告。
4. **Schema：** `docs/schemas/staubli-lifecycle-traceability.schema.json`增加必需字段`resource_key`和`ownership_phase`。
5. **Manifest：** `docs/audits/2026-11-10-staubli-socket-v2-lifecycle-traceability-manifest-v1.json`的28条记录全部补齐资源分组字段，并统一冲突角色。
6. **Policy：** `docs/ci/staubli-lifecycle-traceability-policy.yml`增加资源分组一致性、必需引用和validator退出码规范。

## 2. Validator覆盖范围

### 2.1 Schema约束

Validator使用Python标准库，不增加项目或开发依赖。它支持当前checked-in schema实际使用的Draft 2020-12关键词：`type`、`additionalProperties`、`required`、`properties`、`const`、`enum`、`minLength`、`pattern`、`minItems`、`items`、`uniqueItems`、`allOf`、`if`、`then`。

发现Schema声明了未支持的关键词时会fail closed。**该工具是针对本仓库Schema关键词子集的专用校验器，不是通用完整Draft 2020-12 JSON Schema实现。** 新增Schema关键词必须先扩展校验器和对应测试，不得静默忽略。

### 2.2 稳定ID与引用完整性

- Record ID限制为F01–F16和PLUG-L01–L12，重复ID报错。
- Reference catalog必须包含RACE-01–RACE-16和EXEC-01–EXEC-04共20个基础引用；重复引用报错。
- 每条test_refs必须满足ID格式且可解析到reference_catalog；悬空引用报错。
- 每条RUN_PASS/RUN_FAIL记录必须至少关联一个测试引用。

### 2.3 Resource Owner与Reconcile Coordinator

- 使用`resource_key + ownership_phase`作为资源代际/持有阶段分组键。
- 每个分组必须解析到唯一的`resource_owner`和唯一的`reconcile_coordinator`。
- 字段均为单值字符串；空字符串和含斜杠的复合角色字符串均拒绝。
- 不同ownership_phase允许显式表示Owner handoff；同一分组出现两个不同Owner/Coordinator组合即失败。
- F07与PLUG-L07标记为`RESIDUAL_TRANSFERRED`；其余当前记录使用`ACTIVE`。Quarantine排程仍不形成第二套close执行者。

本轮首轮真实CI发现PLUG-L06的Coordinator被写为“外部LifecycleThread/CleanupCoordinator”复合角色，与同一worker generation的其他记录冲突。Validator按预期返回exit code 1，失败报告成功归档；随后将其规范化为唯一`CleanupCoordinator`，修正后通过。

### 2.4 Status与Evidence policy

| 状态 | 必需证据 |
|---|---|
| SPECIFIED | design_spec |
| STATIC_REVIEWED | design_spec + source_review |
| DESIGN_REVIEWED | design_spec + source_review |
| RUN_PASS / RUN_FAIL | test_log + environment_manifest + artifact_hash |
| NOT_RUN | 不得声称已有运行日志/环境/硬件验收证据 |
| BLOCKED | 必须提供非空blocker |

所有记录声明的required_evidence都必须有对应PRESENT证据。Repo-relative PRESENT URI必须指向仓库内真实文件，禁止路径逃逸；test_log、environment_manifest、artifact_hash、hardware_acceptance必须提供64位小写SHA-256。NOT_RUN不能携带PRESENT的运行期test log、environment manifest或hardware acceptance。

### 2.5 CLI退出码

| 退出码 | 含义 |
|---|---|
| 0 | Schema子集及Policy检查通过 |
| 1 | Schema或Policy发现验证错误 |
| 2 | 文件读取、JSON解析或报告写入失败 |

验证器可使用`--manifest`、`--schema`指定输入，并用`--report`输出机器可读JSON结果。CI直接依据退出码fail closed。

## 3. 测试覆盖

新增测试覆盖：
- canonical manifest正向验证；
- Record ID/reference ID重复；
- 缺少必需reference；
- dangling test reference；
- 同资源代际Owner冲突；
- 复合Coordinator角色；
- Static review缺source evidence；
- required_evidence声明与PRESENT证据不匹配；
- RUN_PASS缺少test/environment/hash；
- BLOCKED缺少原因；
- NOT_RUN错误声称存在运行证据；
- 未知Manifest字段；
- CLI成功、Policy失败和JSON解析失败三类退出码。

## 4. GitHub Actions实际结果

- **Workflow：** CI #3462
- **Run ID：** `42936950000`
- **Head commit：** `458db41519cde057f2c158d5e96b6b0587eba439`
- **结果：** SUCCESS
- **执行矩阵：** Python 3.10、3.11、3.12
- **每个版本：** Manifest validator PASS（28 records / 20 references）、Ruff PASS、Pytest 58 passed。
- **其他CI作业：** Python OSV依赖审计与CycloneDX SBOM生成作业均在该workflow中成功。
- **验证报告工件：** `staubli-lifecycle-validation-py3.10`、`staubli-lifecycle-validation-py3.11`、`staubli-lifecycle-validation-py3.12`，均已归档且未过期。

运行记录：[GitHub Actions CI #3462](https://github.com/rexyll/robot_knowledgebasement/actions/runs/42936950000)。

## 5. 验收状态与限制

| 项目 | 状态 |
|---|---|
| Validator实现 | IMPLEMENTED |
| 当前Schema关键词子集校验 | CI_PASS |
| 28条Manifest与20项基础引用 | CI_PASS |
| Owner/Coordinator分组一致性 | CI_PASS |
| Evidence/Status policy | CI_PASS |
| 负向fixture与CLI退出码测试 | CI_PASS |
| Python 3.10/3.11/3.12完整仓库测试 | CI_PASS（每个版本58 passed） |
| Ruff | CI_PASS |
| OSV / SBOM现有CI作业 | CI_PASS |
| 通用完整Draft 2020-12兼容性 | NOT_IMPLEMENTED |
| 外部URI实际内容真实性与签名验证 | NOT_RUN |
| Stäubli C++/ROS构建、故障注入、TSan/ASan | NOT_RUN |
| Plugin DSO真实load/unload | NOT_RUN |
| Clean Jazzy/install consumer/ABI | NOT_RUN或BLOCKED |
| VAL3/CS9、SIL/HIL、FAT/SAT、实机 | NOT_RUN |
| A1.1 | BLOCKED |

本轮CI PASS只证明仓库Manifest/Schema子集/Policy/测试工具链通过，**不代表Stäubli driver工程安全性、资源释放正确性或实机安全验收通过**。未修改固定上游、未创建/应用/合并上游PR；`TODO-EXT-001`仍未授权。§9.3.281–§9.3.294历史TaskPlan同步缺口继续透明保留。

**下一节点：§9.3.314 / SERVO-897：建立机器可读RACE/EXEC测试用例目录（Test Case Catalog），为20个稳定引用补齐title、scenario、preconditions、stimulus、expected assertions、test harness、execution state与evidence contract，并验证Manifest引用和测试目录双向完整性；仍不触碰上游driver。**
