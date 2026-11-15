# MotionControlAlgorithms 第三方依赖许可证、来源与 SBOM 第一轮审计

- 日期：2026-11-15
- 仓库：[`rexyll/MotionControlAlgorithms`](https://github.com/rexyll/MotionControlAlgorithms)
- 基线：`c11091bd2bb3ce001eb09f2664c1ff5076f8a73b`
- 范围：许可证文件、NOTICE、README、Git submodule、CMake/Conan/Python 依赖声明、ROS 2/Gazebo package metadata、GitHub Actions workflow 与仓库树。
- 方法：静态文件/仓库树审查；未安装依赖或构建可选目标。

## 执行摘要

发现四项 P1 风险：

1. 仓库嵌入 KickCAT 源码并附 CeCILL-C v1.0 许可证，但未记录其精确上游 commit/tag 或本地修改差异。
2. KickCAT vendor 中存在 MIT 与 WTFPL-2.0 组件；argparse 子模块有固定 commit，但其许可尚未核验。
3. 四个 ROS 2/Gazebo package.xml 标注 MIT，与根 README 的 Apache-2.0 项目声明不一致；尚不能仅据元数据判定真实许可。
4. 仓库树未发现提交的 SBOM 或专用生成/验证 workflow，依赖来源分散，缺少统一锁定和第三方通知清单。

## 证据与发现

| 对象 | 仓库证据 | 结果 | 后续动作 |
|---|---|---|---|
| 根项目 | `LICENSE`, `NOTICE`, `README.md` | Apache-2.0；NOTICE 仅作通用第三方许可声明 | 建立组件级 notices |
| KickCAT | `scripts/ethercat_sil/KickCAT/LICENSE` | CeCILL-C v1.0；源码目录不是 Git submodule | 追溯上游 tag/commit、校验差异和修改状态 |
| imgui_stdlib | `scripts/ethercat_sil/KickCAT/vendor/imgui_stdlib/LICENSE.txt` | MIT，版权 Omar Cornut | 保留原始声明并列入 notices |
| portable-file-dialogs | `scripts/ethercat_sil/KickCAT/vendor/portable-file-dialogs/COPYING` | WTFPL Version 2 | 保留许可文本并列入 notices |
| argparse | 根 `.gitmodules` + gitlink | URL 为 p-ranav/argparse，固定 commit `7d093f8e1201db2dded2eee94de77665698ee9dc` | 获取该 commit 的 LICENSE 并记录版本/版权 |
| KickCAT Conan | `scripts/ethercat_sil/KickCAT/conan/conanfile.py` | 条件依赖 GTest 1.15.0、tinyxml2 11.0.0、nlohmann_json 3.12.0、argparse 3.2、imgui 1.92.6、Windows Npcap 1.70 | 与真实 build options 对照，生成解析后依赖树 |
| KickCAT Python tooling | `tools/diagnosticsHelpers/requirements.txt` | matplotlib 3.5.3、networkx 2.8.6、scipy 1.9.1 | 纳入工具链依赖清单与 Python SBOM |
| 根构建依赖 | 根 `CMakeLists.txt`、CI workflow | Eigen3、GoogleTest、Google Benchmark；可选 IgH、SocketCAN、ROS 2、Gazebo | 分 profile 解析依赖与许可证 |
| ROS/Gazebo 包 | 4 个 `package.xml` | 全部标注 MIT，与根 README Apache-2.0 声明不一致 | 权利人确认后统一包级元数据/许可证文件 |
| SBOM | 仓库树与 8 个 workflow 路径 | 未发现提交 SBOM 或专用 SBOM 生成/校验步骤 | 建立 CycloneDX/SPDX 生成、schema 校验和策略扫描 |

## CeCILL-C 义务提示

KickCAT LICENSE 中 CeCILL-C 第 5.3.2/5.3.3 条区分修改软件与衍生组合的分发条件；对 KickCAT 源码的集成修改可能要求修改软件继续受 CeCILL-C 约束、明确记录集成贡献并按协议提供修改源码。第 6.4 条要求保留知识产权声明，并在衍生软件易于访问的位置说明许可状态。应按具体修改和分发形态由权利人/法律顾问确认；本报告不是法律意见，也不认定当前仓库已违反许可。

## 建议整改次序

1. 追溯 KickCAT 上游 commit/tag，生成本地 diff/原样副本证明；核验 argparse 固定提交许可证。
2. 确认 ROS/Gazebo 四个包的真实许可意图，不自动替换 MIT 或 Apache-2.0 声明。
3. 建立第三方通知清单，至少包括组件、来源、精确版本、SPDX 许可证标识、许可证文本、版权人、修改状态、分发方式和义务。
4. 生成仓库源代码 SBOM 与各构建 profile 的解析依赖/制品 SBOM；区分构建、运行、测试和开发依赖。
5. 对 Linux/Windows、ROS 2/Gazebo、SocketCAN、IgH、KickCAT 可选配置执行 SBOM schema 校验、许可证策略扫描、漏洞扫描并归档构建 provenance。

## 验证边界

未运行 CMake/Conan/ROS/Gazebo 构建，未解析完整依赖闭包，未生成/验证 SBOM，未扫描 CVE，未做 HIL 或法律意见。未修改上游 MotionControlAlgorithms 的任何文件。