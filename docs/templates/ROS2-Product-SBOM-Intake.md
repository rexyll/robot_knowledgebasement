---
tags: [软件供应链, SBOM, ROS2, 产品配置, 机器人系统工程]
创建日期: 2026-11-04
更新日期: 2026-11-04
---

# ROS 2 机器人产品级软件物料清单（SBOM）采集模板

> **用途：** 在具体机器人型号、硬件配置和软件发布版本确定后，采集可复现的产品软件组成。此模板不是现成 SBOM，也不表示本仓库已部署或验证任何 ROS 2 产品。
>
> **基线原则：** 以“实际交付/运行的产品配置”为对象；每条组件记录必须能追溯到设备、镜像、包、源码 commit、供应商版本或制品哈希。生态索引中的候选项目不得自动录入为产品依赖。

## 1. 产品与采集范围

| 字段 | 填写值 |
|---|---|
| 产品/项目名称、型号、SKU | 待填写 |
| 硬件配置/修订版 | 待填写（主控、载板、传感器、驱动器、PLC 等） |
| 软件发布版本/构建号 | 待填写 |
| ROS 2 发行版及补丁版本 | 待填写；不能只填“ROS 2” |
| Ubuntu/其他 OS、内核、架构 | 待填写（含实时内核补丁/配置） |
| 目标部署形态 | 裸机 / deb / 容器 / 混合；待填写 |
| 采集日期、采集人、环境标识 | 待填写 |
| 采集对象序列号/资产编号 | 按组织安全政策记录；避免在公开仓库暴露敏感序列号 |
| 证据归档位置、签名/哈希 | 待填写 |

### 1.1 组件纳入边界

至少分别盘点以下层级，不得只扫描 ROS workspace：

1. ROS 2 核心发行版、RMW/DDS 实现、ROS package、工作空间源码包和 overlay。
2. package.xml 声明的 build/buildtool/export/exec/test 依赖，以及 rosdep 解析出的系统依赖。
3. apt/dpkg、RPM、Python、C/C++ 动态/静态库、运行时插件、语言运行环境。
4. 容器镜像、基础镜像 digest、镜像内软件包、镜像构建来源与 SBOM。
5. CPU/GPU/NPU runtime、CUDA/cuDNN/TensorRT、驱动、BSP、内核模块、设备树和启动固件。
6. MCU/运动控制器/传感器固件、bootloader、FPGA bitstream、校准/配置文件（区分可执行软件与纯配置）。
7. 厂商 SDK、闭源二进制、商业库、授权文件/功能开关及其再分发限制。
8. PLC IDE/runtime、PLC 程序/库、现场总线 master/slave 软件和 ROS 2 协议桥。
9. OTA/更新代理、诊断/安全代理、远程运维组件及供应商预装软件。
10. 构建工具链、交叉编译器、代码生成器和测试工具（与产品运行时依赖分开标识）。

## 2. 采集步骤与建议命令

> 在受控、可复现的目标镜像/设备或与之完全一致的构建环境中执行。命令输出需保存原始日志、时间戳、主机/镜像标识；先确认命令适用性，不要在生产设备上执行可能改变状态的安装/升级操作。

### 2.1 OS、内核与硬件平台

    date -u +%FT%TZ
    uname -a
    cat /etc/os-release
    dpkg --print-architecture 2>/dev/null || true
    lscpu 2>/dev/null || true

记录主板/载板料号和 revision、SoC、GPU/NPU、内存、存储、BIOS/UEFI、BSP、内核配置及供应商支持期限。硬件序列号按权限管理，不要放入公开 SBOM。

### 2.2 ROS 2 workspace 与包依赖

    printenv | grep -E '^(ROS_DISTRO|ROS_VERSION|RMW_IMPLEMENTATION|AMENT_PREFIX_PATH|COLCON_PREFIX_PATH)='
    ros2 doctor --report
    ros2 pkg list
    # 对关键包逐一导出 package.xml / 包版本 / 安装前缀
    ros2 pkg xml <package_name>
    # 从源码工作空间导出精确仓库 revision（需安装 vcstool）
    vcs export --exact src > vcs-export.repos
    # 在 workspace 根目录解析系统依赖；先保存 rosdep 环境与结果
    rosdep check --from-paths src --ignore-src
    rosdep install --from-paths src --ignore-src --simulate

- 归档所有 overlay 的源码清单、.repos 文件、Git remote、tag、完整 commit SHA、dirty 状态和本地补丁。
- package.xml 是依赖声明证据，不是已安装版本证明；需与实际安装包、构建产物和运行镜像交叉核对。
- rosdep key 是跨平台映射键；归档操作系统、发行版、rosdep 数据版本/快照和最终解析到的系统包版本。
- 记录缺失依赖、未解析 key、条件依赖、可选插件和未启用组件，不能静默忽略。

### 2.3 OS 与语言生态包

    dpkg-query -W -f='${binary:Package},${Version},${Architecture}\n' 2>/dev/null | sort > dpkg-packages.csv
    python -m pip freeze --all > python-freeze.txt

若使用其他包管理器，导出对应 lockfile 与已安装清单。同时记录 apt 源、仓库签名密钥/发行版快照、deb 包 SHA-256；Python 虚拟环境、解释器版本、wheel 来源与 hash；C/C++ 动态库清单、静态链接组件、插件目录和系统服务。pip freeze 仅反映当前环境，不等于可复现锁文件。

### 2.4 容器、GPU、BSP 与固件

    docker image inspect <image> --format '{{json .RepoDigests}}'
    docker image ls --digests
    nvidia-smi 2>/dev/null || true

- 容器：记录 registry、repository、tag、不可变 digest、基础镜像 digest、Dockerfile/build args、构建 commit、镜像平台架构；tag 不可替代 digest。
- GPU/NPU：记录硬件型号、驱动、CUDA/cuDNN/TensorRT 或厂商 runtime 版本及兼容矩阵。
- BSP/内核：记录供应商、版本、补丁集、内核模块、设备树、启动链和来源制品哈希。
- 固件：记录设备型号/硬件 revision、固件版本、发布日期、升级包 SHA-256、签名校验结果、回滚方式和供应商来源。
- FPGA/MCU：记录 bitstream/固件构建标识、工具链版本、源码 commit（如可得）、签名与烧录记录。

### 2.5 厂商 SDK、PLC 与专有组件

逐项记录供应商、产品/模块、精确版本、目标架构、下载来源、安装包 hash、授权类型、授权文件位置（仅安全存储引用，不提交密钥）、运行时依赖、支持期限、EOL/PCN、再分发条款和供应商确认记录。PLC 侧还应关联 PLC—ROS 2 ICD：控制器型号、固件、runtime、项目/库版本、协议桥版本、变量映射和安全边界。

## 3. 组件记录表字段

将每个组件写入配套 CSV（[ROS 2 产品级 SBOM 采集表](ROS2-Product-SBOM-Intake.csv)）。最低字段包括：

- component_id：本次清单内稳定唯一标识。
- layer：ros2 / source / os / python / native / container / gpu / bsp / firmware / plc / vendor_sdk / build_tool 等。
- name、version、supplier、package_url（可得时使用 purl）。
- source_url、source_commit、artifact_sha256、image_digest。
- license_declared、license_concluded、license_evidence、notice_obligations。
- relationship、scope（runtime/build/test/optional/dev）、direct_or_transitive。
- device_or_image、architecture、ros_distro、os_release。
- evidence_ref、collected_at_utc、collector、verification_status、notes。

版本未知时填 UNKNOWN 并创建缺口，不得猜测；不适用字段留空。不要将许可证声明字段写成法律结论。

## 4. SBOM 生成与格式

1. **先采集再生成。** Python 环境可使用 CycloneDX Python 工具；ROS/系统/容器/固件/PLC 组件必须由对应采集器、供应商资料和人工证据补齐。
2. CycloneDX 1.7 可作为统一交付格式候选；SPDX 3.0 可用于许可证/来源及供应链数据交换。记录所用规范版本、工具名称/版本、命令、配置和生成时间。
3. 为每个子系统生成子 BOM（例如 ROS workspace、OS 镜像、容器、固件/PLC），再通过明确的依赖/包含关系组合产品 BOM；禁止将多个子 BOM 简单拼接后宣称依赖图完整。
4. SBOM 必须关联产品型号、硬件 revision、软件 release、镜像 digest 和构建流水线；同一产品不同 SKU/地区/选件应分开标识。
5. 保存原始采集清单、机器可读 SBOM、校验报告、签名/哈希、工具日志和人工补充记录。

## 5. 验收清单

- [ ] 产品型号、硬件 revision、软件 release 和部署镜像均已锁定。
- [ ] ROS 2 发行版、RMW/DDS、workspace overlay 和所有源码 commit 已记录。
- [ ] package.xml 声明依赖与实际安装包/构建产物已交叉核对。
- [ ] rosdep keys 已解析到目标 OS 的精确系统包版本；未解析项有责任人和处置结论。
- [ ] OS、Python、C/C++、容器、GPU runtime、驱动、BSP、内核模块已盘点。
- [ ] MCU/传感器/FPGA/PLC 固件和厂商 SDK 已记录版本、哈希及供应商来源。
- [ ] 闭源组件、授权限制、模型/数据/资产许可和 NOTICE 义务已单独审查。
- [ ] 直接/传递、运行时/构建/测试/可选依赖关系已标注。
- [ ] SBOM schema、工具版本、生成参数、校验结果和文件哈希已归档。
- [ ] 漏洞扫描、许可证审查、供应商确认和例外审批有独立记录。
- [ ] 产品变更、固件升级、BSP/SDK 更新、容器重建和安全公告触发重新生成 SBOM。

## 6. 状态与限制

本模板不定义任何具体产品的实际组件版本，不替代目标设备采集、镜像扫描、固件供应商确认、漏洞评估、许可证法律审查或功能安全评估。未采集的组件必须标记为缺失/未知；不得用“未发现”替代“已验证不存在”。

### 6.1 推荐交付目录

    sbom/<product>/<hardware-revision>/<software-release>/
      inventory.csv
      ros-workspace.repos
      rosdep-check.txt
      os-packages.csv
      python-freeze.txt
      container-digests.json
      firmware-register.csv
      vendor-sdk-register.csv
      cyclonedx.cdx.json
      validation-report.md
      evidence/

### 6.2 相关项目文件

- [[开源项目与工具链]]：生态候选项目与版本/许可证线索。
- [[知识生态兼容矩阵]]：ROS 2 发行版、驱动、SDK 和工业互操作静态兼容证据。
- [PLC—ROS 2 ICD 模板](PLC-ROS2-ICD.md)：PLC 接口、协议桥和安全边界。
- [软件供应链与 SBOM 初始基线](../audits/2026-11-04-software-supply-chain-baseline.md)：当前 Python 工具包静态审计。
