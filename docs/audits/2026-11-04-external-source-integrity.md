---
tags: [外部源码, SHA-256, 来源完整性, rustypot, 供应链]
创建日期: 2026-11-04
更新日期: 2026-11-04
状态: 源码快照哈希已记录并纳入 CI 校验；法律范围与持续更新策略待审
---

# 外部源码完整性记录：rustypot STS3215（2026-11-04）

## 1. 目标与用途

仓库 CI 为核验 STS3215 寄存器定义、编码与转换元数据，会从 rustypot 项目下载单个 Rust 源文件。该文件不是 Python 包运行时依赖，也不等于将 rustypot 整个项目打包或分发。

- 上游仓库：[pollen-robotics/rustypot](https://github.com/pollen-robotics/rustypot)
- 固定 commit：`7aa85e13143594ea4fd4ed9f29e3e29d39b5de85`
- commit 页面：[7aa85e1](https://github.com/pollen-robotics/rustypot/commit/7aa85e13143594ea4fd4ed9f29e3e29d39b5de85)
- 源文件：`src/servo/feetech/sts3215.rs`
- 原始下载地址：[raw source](https://raw.githubusercontent.com/pollen-robotics/rustypot/7aa85e13143594ea4fd4ed9f29e3e29d39b5de85/src/servo/feetech/sts3215.rs)
- 文件 UTF-8 大小：7,434 bytes
- SHA-256：`4dbb829228d13492e7dcf80bfbd3d48642a9bbc58c8158e6bdcec1cc35811fa7`

## 2. 来源与完整性校验

本次从固定 commit 的 raw URL 读取源文件，按 UTF-8 原始字节计算 SHA-256。CI 的每个 Python 测试矩阵任务在下载后立即运行 `sha256sum --check --strict`，只有内容与上述摘要完全一致才继续执行寄存器审计脚本。该校验防止固定 URL 返回内容意外变化或下载内容被替换；它不证明上游源码本身无缺陷。

## 3. 许可证证据边界

在相同 commit 下读取上游仓库根目录 `LICENSE`，文本声明 Apache License, Version 2.0；commit API 的 GitHub verification 字段显示该 commit 的签名验证状态为 `verified`。记录的证据链接：

- [rustypot commit](https://github.com/pollen-robotics/rustypot/commit/7aa85e13143594ea4fd4ed9f29e3e29d39b5de85)
- [该 commit 的 LICENSE](https://raw.githubusercontent.com/pollen-robotics/rustypot/7aa85e13143594ea4fd4ed9f29e3e29d39b5de85/LICENSE)

这是仓库级许可证文件的来源证据，不构成法律意见，也未独立确认该文件是否覆盖每个历史贡献或第三方子组件。若未来复制、修改或再分发该源文件，仍需完成 NOTICE、版权声明、修改标记和适用专利条款的合规审查。

## 4. 更新与失效规则

- 不得只更新 commit 而不同时重新计算并审查 SHA-256。
- 上游版本升级时，必须同时审查寄存器定义差异、许可证文件变化和 commit 签名状态。
- 若摘要校验失败，CI 应失败关闭；不得静默覆盖预期摘要。
- 该源文件仅用于 CI 对照检查，不应被误列为 Python runtime dependency 或产品已部署组件。

## 5. 当前状态

已完成：固定 commit、原始文件大小与 SHA-256、仓库级 Apache-2.0 LICENSE 证据、CI 摘要校验步骤。

仍未完成：对上游许可证适用范围的法律审查、第三方贡献/NOTICE 逐项审查、上游升级责任人与周期策略。SBOM-004 仅完成来源完整性证据部分，不关闭全部许可证审查。

## 6. CI 实际校验结果（补记）

GitHub Actions [run #534](https://github.com/rexyll/robot_knowledgebasement/actions/runs/41773862412)（run ID `41773862412`，head commit `4bb611aac8dbb0b2079c09eed2ba595b5a68477b`）最终 `completed / success`。Python 3.10、3.11、3.12 三个测试 job 中的源文件 SHA-256 校验步骤均为 success，随后寄存器审计和 pytest 也通过；SBOM job 同样成功。

校验配置迭代中，早期 run #528/#533 曾失败：先是 checksum 行换行格式错误，随后单引号阻止 `${RUNNER_TEMP}` 展开。通过改用双引号展开临时路径后，run #534 验证通过。失败原因属于 CI shell 命令格式，不是源文件摘要不匹配。今后更改源文件 commit 或摘要时，必须重新运行三版本矩阵。
