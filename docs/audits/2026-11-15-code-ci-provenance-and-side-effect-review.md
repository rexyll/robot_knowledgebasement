# 00-01｜新增源码、脚本、测试与 CI 来源/副作用审查（2026-11-15）

## 1. 审查对象与范围

基于 main 的完整资产 Tree，审查以下 35 项源码和自动化资产，并补充检查其直接执行的构建/测试工作流：

- `scripts/`：12 项（11 个 Python/Bash 工具和 1 个目录说明）
- `src/robot_knowledgebase/`：11 个 Python 包文件
- `tests/`：10 个 Python 测试文件
- `.github/workflows/`：2 个 CI 工作流

同时抽查既有 Python 锁文件、SBOM 生成器、OSV 扫描及外部工程集成策略。该轮为限定范围静态代码/配置审查，不等同于对全仓库其他知识文档逐条主张验收。

## 2. 主要结论

1. **核心 Python Toolkit 当前是小型本地数据处理层。** `src/robot_knowledgebase/` 的模块主要使用 Python 标准库，提供 Markdown 文件读取、元数据解析、文本切块、数据模型，以及 Embedding/Retrieval Protocol；没有发现该包自身发起网络连接、读取凭证、调用外部进程或访问机器人总线的代码。
2. **新增工具不是机器人运行时控制代码。** 多数脚本读取本地 JSON、Schema、CMake File API 或锁文件，写出规范化报告/证据；外部访问集中在 OSV API、Git/ROS/Ubuntu 软件源及固定 Stäubli 验证仓库的 CI 构建流程。
3. **工作流引用的 GitHub Actions 已固定到完整 commit SHA。** 初始审查确认 checkout v4、setup-python v5 和 upload-artifact v4 均为完整 SHA pin；CI 日志随后显示 GitHub runner 已强制 Node 24 运行这些仍声明 Node 20 的旧版本。已在本分支升级到 checkout v7.0.1、setup-python v6.2.0、upload-artifact v6.0.0，并将每个新版本继续固定为完整 SHA；三项新 pin 与官方 tag ref 一致且 commit verification 为 verified。setup-uv v10.3.3 保持原 pin。
4. **Stäubli 构建工作流固定了容器 digest 和源仓库 commit，并要求 clean checkout。** 但 apt 包版本、Ubuntu 软件源索引和 rosdep 依赖解析仍然动态，缺少完整系统依赖锁、系统包清单和系统级 SBOM，因此构建尚非完全可复现/ hermetic。
5. **Python SBOM 不是整个构建环境的 SBOM。** 根 CI 当前覆盖 Python runtime、development、SBOM generator 和 build-tools 等环境；它不自动覆盖 OSRF 容器镜像、Ubuntu apt 包、ROS 2 二进制/rosdep 依赖、第三方源码 checkout 或机器人固件。
6. **构建证据包提供哈希完整性，不提供身份认证。** `package_staubli_build_evidence.py` 对清单中列出的工件核对相对路径、字节数和 SHA-256，并拒绝路径逃逸；没有数字签名、可信时间戳或独立发布者认证。环境快照只采集有限 allowlist 和工具版本，未形成完整 dpkg/apt package inventory。
7. **代码文件权利来源仍未逐文件完全证明。** 根目录存在 MIT LICENSE；本轮检查的自有 Python 文件没有独立 SPDX/license header 或逐文件版权清单。未发现本轮这些 Python 文件直接 vendoring 第三方库源码，但无文件级权利人记录，不能把这一观察扩大为全仓库所有文件均由同一主体拥有。

## 3. 核心 Python 包静态审查

审阅的 11 个文件：

- `__init__.py`、`cli.py`
- `embeddings/__init__.py`、`embeddings/base.py`
- `ingest/__init__.py`、`ingest/chunker.py`、`ingest/markdown.py`
- `llm/__init__.py`
- `models.py`
- `retrieval/__init__.py`、`retrieval/base.py`

观察结果：

- Embedding 与 Retriever 是 Protocol 接口，不内置模型 SDK、HTTP 客户端或向量数据库客户端。
- Markdown loader 通过调用者提供的本地文件路径读取文件；未发现网络抓取或命令执行路径。调用方仍应限定可读路径，不能把该本地 loader 当作面向不可信用户的沙箱。
- Chunker 与模型层为纯 Python 数据逻辑；未发现系统级写入或设备访问。
- `pyproject.toml` 的 runtime dependencies 为空；运行时包实现使用标准库。开发/构建工具由锁文件和 CI 单独管理。

## 4. 脚本审查与执行边界

| 工具 | 主要输入/作用 | 本轮确认的边界 |
| --- | --- | --- |
| `audit_python_vulnerabilities.py` | 解析 uv/build lock 并查询 OSV API | 需要公开网络访问；对非精确 pin、空输入、OSV 分页/返回数量异常和请求失败采取失败关闭；输出扫描报告。不是 OS/ROS/固件漏洞审计 |
| `extract_python_license_metadata.py` | 读取四类 CycloneDX BOM 并提取 license metadata candidates | 本地文件处理；提取的是待人工复核候选，不是许可证适用性/分发法律结论 |
| `collect_staubli_cmake_file_api.py` | 读取 CMake File API 和安装导出文件 | 对 reply 相对路径、解析后路径归属和 export root 做边界检查；缺索引、配置或引用文件时拒绝继续 |
| `validate_staubli_fake_harness_target_graph.py` | 比较 BUILD_TESTING OFF/ON 的 target/dependency/install/export snapshots | 本地 JSON 校验与报告输出；不编译 C++，不执行 ROS/控制器 |
| `validate_staubli_lifecycle_manifest.py` | 校验自定义 Schema 关键词子集、资源 owner、状态和证据策略 | 不是完整通用 JSON Schema 实现；通过只证明输入满足本仓库实现的子集和策略 |
| `validate_staubli_runtime_evidence_bundle.py` | 校验运行证据身份、事件序列、快照与工件摘要 | 路径解析后必须仍位于证据根目录内；哈希/大小校验不证明测试真实性或签名身份 |
| `validate_staubli_test_case_catalog.py` | 校验 RACE/EXEC catalog 与 lifecycle Manifest 双向引用 | 检查映射完整性，不执行 catalog 中的测试 case |
| `validate_staubli_upstream_target_graph.py` | 检查 upstream build target 类型、依赖闭包、install/export 边界 | 消费 CMake collector 输出；不独立解析实时构建树、不运行 C++ 测试 |
| `package_staubli_build_evidence.py` | 收集 OFF/ON snapshot、validation report、命令日志和环境指纹 | 仅收集显式输入；限制环境变量采集范围；校验清单路径/大小/SHA-256；未签名、未记录完整系统包清单 |
| `run_staubli_build_testing_matrix.sh` | 执行 Stäubli ROS Jazzy 两种 BUILD_TESTING 配置的构建、安装、consumer smoke 和 gtest | 要求 Jazzy、精确 commit 和 clean source tree；把 build/install/log/consumer 写入指定输出目录；不对 upstream checkout 修改源文件 |
| `retry_apt_update.sh` | 刷新 apt 索引并重试必需包候选 | **会修改系统 APT 源文件并运行 apt-get update**；现已增加默认拒绝的显式 opt-in 门禁，仅在指定临时 CI 容器 step 设置变量后运行 |
| `scripts/README.md` | 工具目录说明 | 已增补网络、系统写入、证据范围和禁止使用场景 |

### 4.1 本轮修复：APT 系统级副作用门禁

原 `retry_apt_update.sh` 会对 `/etc/apt/sources.list`、`/etc/apt/sources.list.d/*.list` 和 `*.sources` 做原地替换，并运行 `apt-get update`；原执行路径没有显式 opt-in。现已在脚本最前部新增：

- 默认检查 `ALLOW_APT_SOURCE_REWRITE`，不是 `1` 时输出拒绝原因并以退出码 2 退出。
- 只有 Stäubli 工作流的 “Install explicit upstream CMake dependencies and build tools” step 显式注入 `ALLOW_APT_SOURCE_REWRITE: "1"`。
- 新增负向测试：在不提供 opt-in 时执行脚本，断言它在任何 APT 操作前退出码为 2；镜像配置测试同时确认 opt-in 门禁位于镜像修改函数之前。
- 脚本目录 README 已明确说明此工具只允许在 pinned、可丢弃的 CI 容器运行，不能用于个人开发机、生产主机或机器人控制器。

本修复限制了误用入口，不改变 APT/rosdep 本身的动态依赖解析，也没有声称系统包供应链已经锁定。

## 5. 测试资产与测试证据等级

审阅的 10 个测试文件：

- `test_chunker.py`、`test_markdown.py`
- Stäubli build evidence、CMake File API、fake target graph、lifecycle Manifest、ROS Jazzy build script、runtime evidence bundle、RACE/EXEC catalog、upstream target graph 等 8 个测试模块

主要测试模式使用 pytest `tmp_path`、合成 JSON/XML、临时目录和静态工作流/脚本检查。它们用于验证解析、边界、失败关闭、路径约束、证据清单及构建脚本合同。

**不应推导为：**

- 已执行所有 Manifest/RACE/EXEC 里的工程测试 case；
- 已在真实 Stäubli 驱动、CS9、VAL3、控制器或机器人上运行；
- 已完成 ROS 2 硬件接口 HIL、现场 FAT/SAT、运动安全验证；
- 已复现或排除外部 MoveIt/rclcpp 生命周期竞态。

PR #22 最新 head 在本轮 APT opt-in 代码变更前的 CI 已通过；本轮变更后的 head 必须等待新 CI 运行结束后再记录 PASS。

## 6. GitHub Actions 与外部构建来源

### 6.1 根 Python CI

`.github/workflows/ci.yml`：

- 声明 `permissions: contents: read`。
- Actions 引用固定完整 commit SHA：
  - `actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1`，与官方 `v7.0.1` tag ref 一致，commit verification verified；
  - `actions/setup-python@a309ff8b426b58ec0e2a45f0f869d46889d02405`，与官方 `v6.2.0` tag ref 一致，commit verification verified；
  - `astral-sh/setup-uv@68559e99cc807c1eb7e9238fd43a15bba460eec2`，与 `v10.3.3` tag ref 一致；
  - `actions/upload-artifact@b7c566a772e6b6bfb58ed0dc250532a479d7789f`，与官方 `v6.0.0` tag ref 一致，commit verification verified。
- 本轮通过官方仓库 Git ref/commit API 核对版本 tag 解析到对应 SHA；官方公告说明 GitHub Actions 已于 2026-09-23 移除 Node 20，相关新版本使用 Node 24（[GitHub Changelog](https://github.blog/changelog/2026-09-23-node-20-is-no-longer-available-in-github-actions/)）。
- 使用 `uv sync --locked`、哈希约束的 build-tools/SBOM-tools 安装、CycloneDX 1.7 产物、SHA256SUMS 和 OSV 查询。此覆盖范围为 Python 项目依赖。

### 6.2 Stäubli ROS Jazzy 构建工作流

`.github/workflows/staubli-ros-jazzy-build.yml`：

- `permissions: contents: read`。
- OSRF ROS 容器固定为 `osrf/ros@sha256:ae7ad3ac243da1dfd8bd402a2fa08e149ffbf7a385013bd8ef798d0800accdc8`。
- checkout action 固定到经核验的 `actions/checkout` commit SHA。
- clone 独立验证仓库 `rexyll/staubli_driver_ros2_from_org`，随后 detached checkout `9e617a9e323ef3342f5151a89239bfd93c089f8c` 并检查 HEAD 和 clean working tree。
- build matrix 使用独立 build/install/log/output 目录；对 BUILD_TESTING OFF/ON 做构建、安装目标图检查及安装空间 consumer；ON 路径要求预期 upstream gtest XML 报告全部存在且成功。
- 源仓库是临时 checkout，不把其源码复制进本知识库，也不修改其源文件。

### 6.3 尚未闭合的系统级供应链

即使 container digest 和 source commit 固定，以下输入仍是动态的：

- `apt-get update` 从配置的软件源刷新索引；apt 包未按完整精确版本和制品哈希锁定。
- `rosdep update` 从 ROS/rosdistro 数据源刷新规则；`rosdep install` 解析到的系统依赖随索引/发行版仓库变化。
- 目前环境指纹没有完整导出 `dpkg-query` 包版本清单或 apt source/index 快照，也没有对 Ubuntu/ROS 系统依赖生成 CycloneDX/SPDX SBOM。
- `package_staubli_build_evidence.py` 的 SHA256 清单用于事后完整性核验；未签名，因此不能证明产物来源身份或不可抵赖性。

因此，Stäubli workflow 的结论应写作“固定源码/容器下的构建与测试证据”，不能写作“完全可重现、全依赖锁定的产品软件供应链”。


### 6.4 Actions runtime compatibility remediation

PR #22 的第一次 APT opt-in 变更 CI 中，Python 3.11 job 在 Ruff lint 阶段因新测试断言 101 字符（项目上限 100）失败，pytest 随后被跳过；这是测试文件格式问题，不是 APT guard 逻辑失败。已拆分断言并提交修复，后续新 head 触发 CI。

同一次日志还显示 runner 将 checkout v4、setup-python v5、upload-artifact v4 从 Node 20 强制运行于 Node 24。GitHub 已公告 Node 20 于 2026-09-23 从 Actions runners 移除，并要求使用支持 Node 24 的最新 action 版本。已将两个工作流中的相关引用升级到：

- checkout v7.0.1：`3d3c42e5aac5ba805825da76410c181273ba90b1`
- setup-python v6.2.0：`a309ff8b426b58ec0e2a45f0f869d46889d02405`
- upload-artifact v6.0.0：`b7c566a772e6b6bfb58ed0dc250532a479d7789f`

新版本 tag ref 与完整 commit SHA 一致，且 GitHub commit verification 均为 verified。升级后的最新 head CI 仍待结果，不提前声明全部通过。

## 7. 许可证、权利人和来源缺口

- 根 LICENSE 文本为 MIT，且 `pyproject.toml` 的 Python package metadata 引用该 LICENSE；GitHub repository license detector 仍显示 `Other / NOASSERTION`。
- 本轮自有 Python 模块/脚本/测试没有看到独立 SPDX 标头或逐文件版权声明；需要明确根 MIT 对 Python Toolkit/工程脚本的预期覆盖范围和贡献者权利证据。
- 工作流调用的外部 actions、OSRF 镜像、Stäubli checkout、Ubuntu apt 和 ROS/rosdep 组件有独立来源与许可/供应链要求，不能被根 MIT 自动覆盖。
- 本轮未发现自有 Python 包直接嵌入第三方 Python 库源码；这只是对列定文件的静态观察，不替代锁文件、SBOM、NOTICE 和分发范围审查。

## 8. 后续行动与状态

### 已完成

- [x] 35 项源码/脚本/测试/工作流资产完成限定静态来源、依赖、网络、文件/系统写入和证据边界检查。
- [x] 验证 4 个 Actions 完整 SHA 与官方 release tag ref 一致，且 commit verification 为 verified。
- [x] 为 APT helper 增加显式 opt-in，更新工作流专用环境变量和负向测试。
- [x] 更新 `scripts/README.md`，披露工具用途、副作用和不应推导的证据等级。

### 继续进行

1. 明确 MIT 根许可证的代码/知识/项目资料覆盖边界和贡献者权利来源。
2. 形成 Stäubli ROS/Ubuntu 系统依赖精确版本清单、rosdep/apt 快照与系统级 SBOM；必要时将这些信息纳入环境指纹/工件。
3. 明确 apt/rosdep 动态索引的更新窗口和证据保留策略；动态解析结果必须与每次 build evidence 一起归档。
4. 为 build evidence 评估签名/attestation，而不是把 SHA256SUMS 误作来源身份认证。
5. 继续对新增的 79 项审计资产、26 项章节 TaskPlan 和全库 P0/P1 知识主张逐项完成来源/授权/内容核验。

## 9. 与合并延期门禁的关系

本轮只修改知识库自己的脚本、工作流、测试、README 和审计记录。没有修改 Stäubli 外部验证仓库、MoveIt/rclcpp、机器人驱动源码，也没有引入 `MotionControlAlgorithms` 代码或 submodule。

`14-EXT-02` 仍未关闭；KickCAT 差异/授权义务、ROS/Gazebo 包许可证意图、完整第三方依赖闭包/SBOM 与分发审查仍是门禁。目标仓库集成验证与具体导入 commit/范围/实施分支也未完成。MotionControlAlgorithms 合并继续延期。
