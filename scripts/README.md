# Scripts

本目录存放知识库维护、数据审计、构建辅助和证据校验脚本。它们不是机器人运行时控制程序；除非脚本说明另有授权，不得连接真实机器人、总线或执行运动。

## 分类与副作用

| 文件/类别 | 作用 | 外部访问或写入边界 |
| --- | --- | --- |
| `audit_python_vulnerabilities.py` | 从项目锁文件读取精确 Python 包版本，并查询 OSV API | 需要访问公开 OSV API；结果写入指定报告文件；不是完整系统/产品漏洞扫描 |
| `extract_python_license_metadata.py` | 从本地 CycloneDX JSON 提取许可证元数据候选 | 只读本地 SBOM，写入指定 CSV；候选不等于法律复核或分发批准 |
| `collect_staubli_cmake_file_api.py` | 读取 CMake File API / 安装导出文件，归一化目标信息 | 只读指定构建/安装目录，写入指定 JSON；输入路径与导出文件边界校验失败时拒绝 |
| `validate_staubli_*.py` | 校验 Stäubli 目标图、Manifest、RACE/EXEC 目录和证据包 | 读取显式 JSON/Schema/证据路径并写入报告；不连接机器人、不运行被测 C++ 代码 |
| `package_staubli_build_evidence.py` | 收集构建报告、环境指纹与 SHA-256 清单 | 调用显式版本命令和 Git 查询；复制指定输入并写入证据目录；SHA-256 是完整性校验，不是数字签名 |
| `run_staubli_build_testing_matrix.sh` | 在隔离目录执行固定 Stäubli 源码的 ROS Jazzy build/install/test 矩阵 | 运行 colcon/CMake/rosdep；要求指定 ROS Jazzy、精确源码 commit 和 clean checkout；输出写入 OUTPUT_DIR；不修改上游源码 |
| `retry_apt_update.sh` | 重试系统包索引刷新并确认必要包候选存在 | **会写入 `/etc/apt/sources.list*` 并执行 `apt-get update`。必须显式设置 `ALLOW_APT_SOURCE_REWRITE=1`；只允许在 pinned、可丢弃的 GitHub Actions ROS 容器内使用，禁止在个人开发机、生产主机或机器人控制器上运行** |

## 执行证据边界

- 根 `.github/workflows/ci.yml` 覆盖 Python 测试、静态检查、Python 运行/开发/工具依赖 SBOM 与 OSV 审计；不代表 Ubuntu/ROS 系统包、固件、第三方驱动或整机产品的完整 SBOM。
- Stäubli ROS Jazzy 工作流固定容器镜像 digest 和源码 commit，但 apt/rosdep 索引仍从外部仓库动态解析；该工作流的构建环境尚非完全 hermetic。
- JSON validator 通过只表示给定文件满足所实现的字段/关系/证据策略；不表示 Manifest 中声明的测试已执行，更不表示 HIL、CS9 或实机验收通过。
- 证据包中的 SHA-256 用于检测文件变动，不提供签名、发布者身份认证或可信时间戳。

如需新增脚本，必须在对应审计记录中说明来源、许可证、输入范围、外部访问、文件/系统写入副作用、失败关闭行为、测试证据和适用边界。
