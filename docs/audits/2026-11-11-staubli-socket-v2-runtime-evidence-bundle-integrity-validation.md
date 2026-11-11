# Stäubli SocketV2 Runtime Evidence Bundle 深度完整性校验

> SERVO-899 / §9.3.316  
> 状态：VALIDATOR_HARDENED；合成 RUN_PASS/RUN_FAIL fixture 仅用于验证器测试，不是 Stäubli 执行记录。  
> 固定上游审查基线：`ICube-Robotics/staubli_driver_ros2@bd658e2d266e315d2ee35f985fb352ea88306b79`。

## 1. 本节点目标

在 SERVO-898 的 Evidence Bundle Schema 和基础 validator 上补齐字节级工件完整性、环境身份占位值拦截、跨工件一致性和执行状态门禁；建立可重复生成的合成 RUN_PASS / RUN_FAIL 测试数据，验证状态机分支但绝不伪装成真实 Stäubli 运行结果。

## 2. Schema 变更

新增必需字段 `evidence_origin`：

- `synthetic_fixture`：仅供Schema/validator测试的合成数据。
- `observed_execution`：来自实际执行的观测证据，仍需通过工件完整性、环境和状态门禁。

验证报告必须输出 `validation_scope`。合成来源固定报告为 `SYNTHETIC_FIXTURE_ONLY_NOT_RUNTIME_EVIDENCE`；CLI成功消息也明确打印“SYNTHETIC FIXTURE ONLY — NOT RUNTIME EVIDENCE”。任何使用者不得将合成 RUN_PASS/RUN_FAIL 解释为 Stäubli 软件、机器人或硬件测试结论。

## 3. 字节级 Artifact Integrity

当状态为 RUN_PASS 或 RUN_FAIL 时，必须传入 `--bundle-root`，否则 fail closed。对每个artifact：

1. 路径必须是规范化相对路径；拒绝绝对路径、反斜线、空路径段、`.`、`..`。
2. 逐级拒绝符号链接；解析后路径必须仍位于bundle root之内。
3. 文件必须存在且为普通文件。
4. 实际字节数必须等于 `size_bytes`。
5. 对实际归档字节计算 SHA-256，并与记录完全相等。
6. 同一路径或同一role重复出现均拒绝。

这比仅校验64位十六进制格式更强；没有bundle root时，不会把声明的hash当作已经验证的hash。

## 4. 环境身份与状态一致性

RUN_PASS / RUN_FAIL 均拒绝以下身份占位值：全零源码commit、全零依赖锁digest、全零OCI digest，以及 `NOT_CAPTURED` / `UNKNOWN` / `UNSET` 等环境字段。Schema仍负责commit/digest格式，validator补充占位值策略。

RUN_PASS 必须同时具备：

- 非空事件轨迹和资源快照；
- before 与 after 快照；
- 所有断言均为 PASS；
- test_log、environment_manifest、event_trace、state_snapshot 四类工件；
- 不含 failure phase、UNKNOWN 或 RESIDUAL 资源状态；
- 可验证的完整环境与源码身份。

RUN_FAIL 必须至少包含一个 FAIL 断言、test_log、非空trace以及 before/failure 快照。失败现场允许保留 UNKNOWN/RESIDUAL，不能被“清理成功”覆盖。NOT_RUN/BLOCKED 不得携带已评估的PASS/FAIL断言；BLOCKED必须提供明确 blockers。

## 5. 跨工件关联

要求三个结构化工件携带完全一致的 `bundle_id`、`test_id` 和 `attempt`：

- environment_manifest：同时绑定 source_identity 与 environment；
- event_trace：其 events 必须与 bundle 内联 event_trace 完全一致；
- state_snapshot：其 snapshots 必须与 bundle 内联 resource_snapshots 完全一致。

对比在实际文件完成路径、大小和SHA-256验证后进行。这样可检测“bundle.json声称一个结果，但独立环境/轨迹/快照文件属于另一次运行”的错配。

## 6. 合成 RUN_PASS / RUN_FAIL fixtures

`tests/test_staubli_runtime_evidence_bundle.py` 中的 `make_synthetic_bundle()` 使用固定输入和临时目录生成四类工件及其真实字节级SHA-256：

- 合成 RUN_PASS：完整 before/after 快照、全PASS断言、四类工件和匹配的跨工件身份。
- 合成 RUN_FAIL：FAIL断言、before/failure快照，并保留UNKNOWN native handle状态。
- 两者均使用 `evidence_origin=synthetic_fixture`，测试只验证validator是否正确接受/拒绝证据结构。
- 不写入真实执行工件目录、不连接Stäubli控制器、不调用ROS或硬件，也不改变RACE/EXEC Catalog执行状态。

负向覆盖包括hash/size篡改、跨工件bundle身份错配、占位环境、路径穿越、符号链接、trace时序错误、barrier提前释放、RUN_PASS缺少证据和BLOCKED缺少原因。

## 7. 验收状态

| 检查项 | 状态 |
| --- | --- |
| evidence_origin来源标记与报告范围 | IMPLEMENTED |
| 工件实际字节数与SHA-256核验 | IMPLEMENTED |
| 路径规范化、symlink与bundle root逃逸防护 | IMPLEMENTED |
| 环境身份占位值拦截 | IMPLEMENTED |
| environment/trace/snapshot跨工件关联 | IMPLEMENTED |
| RUN_PASS/RUN_FAIL状态门禁 | IMPLEMENTED |
| 合成PASS/FAIL fixture生成器与负向测试 | CI_PASS（Python 3.10/3.11/3.12） |
| Stäubli Fake/C++/ROS/Plugin/TSan/ASan/HIL真实运行 | NOT_RUN |

## 8. CI验收\n\nGitHub Actions CI #3518 / Run ID `42945227762` / head `c520c91146635664c2c18acbbc69c875d913764c` SUCCESS。Python 3.10/3.11/3.12均通过Evidence Bundle validator、Manifest/Catalog校验和Ruff；每个版本81项pytest通过；OSV与SBOM作业成功。[CI运行记录](https://github.com/rexyll/robot_knowledgebasement/actions/runs/42945227762)。本CI验证的是知识库侧Schema/validator/测试，不是Stäubli C++/ROS运行时。\n\n## 9. 信任边界与未完成事项

- SHA-256证明文件字节与manifest记录一致，不证明文件来源真实、签名身份真实或执行环境可信。真实执行流程仍需可信runner、签名/可归属记录、不可变工件存储与访问审计。
- `observed_execution`是来源声明，不是密码学签名；本validator不能自行认证外部执行者。
- 本validator实现仓库Schema使用的受限关键词子集，不是完整通用Draft 2020-12引擎。
- RACE-01–16与EXEC-01–04仍全部NOT_RUN；SERVO-897 Catalog不升级。
- 未修改固定上游、未创建/应用/合并上游PR；`TODO-EXT-001`未授权，A1.1保持BLOCKED；历史TaskPlan同步缺口继续透明保留。

## 10. 下一节点

§9.3.317 / SERVO-900：定义可执行Fake Harness的C++17 test-only target边界与最小FakeClock/Barrier/DeterministicExecutor API header草案；建立编译目标隔离和生产target零依赖约束。只进行知识库侧规格与可授权范围评审，不触碰上游driver，不执行未授权A1.1。
