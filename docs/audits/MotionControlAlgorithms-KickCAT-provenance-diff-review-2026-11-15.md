# MotionControlAlgorithms：KickCAT vendored 快照逐文件差异与来源审计

- 审查日期：2026-11-15
- 父仓库：rexyll/MotionControlAlgorithms
- 父仓库基线：c11091bd2bb3ce001eb09f2664c1ff5076f8a73b
- KickCAT 上游：leducp/KickCAT
- KickCAT 固定上游 commit：cb2e1a192ac11ffaa58f08945053b8129abf94cb（2026-10-05）
- 本地 vendored 子树 SHA：930c75e31f5b8f3c77c9de01ff754e7339359053
- 方法：Git tree/blob SHA 对照、逐文件文本差异、父仓库提交历史和 DS402 补丁脚本静态审查；未修改上游代码，未执行构建或法律评估。

## 1. 复算结果

| 指标 | 数量 / 结果 |
|---|---:|
| 父仓库 KickCAT 子树 blob | 482 |
| argparse gitlink | 1（固定提交 7d093f8e1201db2dded2eee94de77665698ee9dc） |
| 上游固定 commit blob | 489 |
| 路径与 blob SHA 完全一致 | 471 |
| 同路径但 blob SHA 不同 | 10 |
| 父仓库本地新增路径 | 1 |
| 上游有、当前 vendored 子树没有的路径 | 8 |

10 个 blob 差异中，examples/slave/xmc4800/wdc_foot/nuttx/foot.xml 只是换行格式差异：上游文件含 1,119 处 CRLF，本地副本为 LF；将换行统一后文本相同。其余 9 个路径存在内容差异。另有本地新增 simulation/slave_configs/ecat402-drive-fault.json。

因此应准确表述为：**471/482 个本地 blob 与固定上游版本完全相同；10 个现有路径 blob 不同（其中 1 个仅换行格式），另有 1 个本地新增文件；上游另有 8 个路径未纳入当前快照。** 不应将本地快照称为 pristine 上游副本，也不应把 CRLF→LF 单独描述为功能修改。

## 2. 逐文件差异及来源

| 路径 | 差异类别 | 观察到的变更 | 可见来源 / 状态 |
|---|---|---|---|
| examples/slave/xmc4800/wdc_foot/nuttx/foot.xml | 格式 | CRLF 转 LF，规范化后文本相同 | 初次导入 f91e16919b5a；无语义差异 |
| lib/simulation/include/kickcat/simulation/devices/Ds402Motor.h | DS402 SIL 故障注入 | 新增 fault_after_cycles / fault_reaction_cycles；计数受 Operation Enabled 与 controlword enable 条件约束；实现 Fault Reaction Active 计时、Fault latch 和 bit-7 上升沿复位 | 初次导入 f91e16919b5a 已包含。父仓库脚本 apply_kickcat_ds402_fault_patch.py 固定检查同一 KickCAT commit，并提供两文件补丁重放入口；本轮未重新执行脚本并对生成文件做 blob 等同性证明 |
| lib/simulation/src/DeviceApp.cc | DS402 SIL 故障注入 | 从 JSON 配置读取 fault_after_cycles 与 fault_reaction_cycles | 初次导入 f91e16919b5a；由上述脚本覆盖 |
| simulation/slave_configs/ecat402-drive-fault.json | 本地新增 fixture | 指定 ecat402-drive.xml、ds402_motor=true、fault_after_cycles=250、fault_reaction_cycles=3 | 本地新增，父仓库历史仅能追溯至初次导入 f91e16919b5a；导入前作者/变更记录未由本轮证据还原 |
| lib/include/kickcat/SimulatorControl.h | LRW 故障注入控制接口 | 新增 SetLrwDrop 命令、payload、ack 结构与 setLrwDrop 控制接口 | c046fd2c65f6（Add simulator control command for datagram-level LRW suppression） |
| lib/slave/include/kickcat/EmulatedNetwork.h | LRW 故障注入 | 新增 test-only setLrwDatagramDrop 开关和成员状态 | ef62090d7d01 |
| lib/slave/src/EmulatedNetwork.cc | LRW 故障注入行为 | 只跳过 LRW process-data datagram；保留同一 Ethernet frame 中其余 BRD/FPRD 等 datagram 的处理 | d88951054350 |
| lib/simulation/src/SimulatorControlServer.cc | LRW 控制通道 | 接收 SetLrwDrop，调用 EmulatedNetwork 开关并返回 ACK | 9d34386ede0f |
| unit/src/EmulatedNetwork-t.cc | LRW 回归测试 | 新增同帧 LRW + BRD 场景，检查丢弃 LRW 时 BRD 仍被处理；后续修正测试 helper/include | 72feca346e40、e085a697f1cc、7d3f2744c45c、6640a6ebe9cb |
| simulation/network_simulator.cc | 仿真链路故障与控制通道 | 增加 socket 写错误码日志；在注入链路断开后，仅当有界重试确认 sysfs carrier/operstate 已 down 时，才把 ENOBUFS 归类为预期 SIL frame loss；carrier 仍 up 或其他写失败仍为 fatal；并将 control.drain() 移至 idle continue 前，避免 EtherCAT wire 空闲时控制请求/ACK 停滞 | 6938d3c100a5、5d101326a23e、fbaa7af3c88b、a44c92716578、359e8cecab15、936a4c72ad85 |
| simulation/slave_configs/ecat402-drive.xml | ESI 配置 | 移除 EoE / FoE 项，CoE SdoInfo 从 true 改为 false | f3f08c65231f（Make KickCAT servo ESI CoE-only without SDO Information）；设备/协议依据与目标硬件适配性仍需验证 |

### 2.1 DS402 补丁可重放性边界

父仓库脚本 scripts/ethercat_sil/apply_kickcat_ds402_fault_patch.py：
- 将基线硬性固定为 cb2e1a192ac11ffaa58f08945053b8129abf94cb；
- 只修改 Ds402Motor.h 与 DeviceApp.cc；
- 检查精确插入锚点，检测部分补丁，支持已应用状态及 Operation Enabled cycle 计数语义升级；
- 父仓库 CI workflow 通过固定上游 checkout 后调用该脚本，并检查 fault_after_cycles、fault_reaction_cycles 和关键状态机条件。

这为 DS402 两文件提供了可复现路径，但仍应在专项验证中从干净 pinned checkout 重放，并将生成的两文件与 vendored blob 做 SHA 比对，形成机器可核验的 patch manifest。新增 JSON fixture 也应纳入同一测试数据清单。

### 2.2 LRW 与网络链路仿真改动的边界

LRW 改动针对 SIL/仿真网络故障注入：将过程数据 LRW datagram 的处理故障与 Ethernet frame 本身区分，目标是模拟 PDO/process-data 不可用，同时保留拓扑/AL-state 等其它 datagram 的可观测性。控制命令通过仿真器带外控制通道传递，不应被描述为 EtherCAT 线上新增协议。

network_simulator.cc 改动则针对 Linux socket/veth 注入链路断开的错误分类与仿真器控制通道活性。只有“ENOBUFS + 有界等待后明确观察到 carrier/operstate down”才被视为预期丢帧；接口仍 up 时仍按仿真器错误退出。该逻辑依赖 Linux sysfs 与特定 SIL 网络拓扑，不能自动外推为所有网络设备的通用错误处理策略。

### 2.3 上游未纳入路径

本轮 tree 对照发现以下 **8 个上游文件路径** 未纳入当前 vendored 子树：

- .github/actions/apt-install/action.yml
- .github/actions/setup-conan-action/action.yml
- .github/actions/setup-simulation/action.yml
- .github/workflows/ci.yml
- .github/workflows/quality.yml
- test/install/cmake/CMakeLists.txt
- test/install/main.cc
- test/install/pkgconfig/Makefile

这些路径主要是上游 CI/actions 和安装导出测试资源。当前快照包含本地 CMakeLists.txt 与 .gitignore；它们不属于本轮 upstream-only 清单。
## 3. ROS 2 / Gazebo 包许可证元数据

以下四个 package.xml 均明确写入 MIT：

| 包路径 | Blob SHA |
|---|---|
| gazebo/mca_gazebo_adapter/package.xml | 3626efc66bab22a3d0445ba52b14144d9c0b901e |
| ros2/mca_gz_ros2_control_adapter/package.xml | ba4f625751da40bad3fbddd9c47aff5c764d67cc |
| ros2/mca_ros2_adapter/package.xml | 8839730a7109bdffa18db16dbf8a07bc21acb05c |
| ros2/mca_ros2_control_adapter/package.xml | d72eea2da0033f86ca290d9fa50e14971ea16b24 |

它们与父仓库根 Apache-2.0 声明不一致。package.xml 的 license 字段是当前元数据证据，不足以单独认定包源码真实许可；不得自动将 MIT 改成 Apache-2.0。须由项目权利人确认包级许可意图、代码来源和是否含独立第三方贡献，再同步 package.xml、许可证文本及 NOTICE。

## 4. 许可证与分发判断边界

- KickCAT 根目录自带 CeCILL-C v1.0；父仓库根 Apache-2.0 不会自动覆盖该目录。
- KickCAT vendor 子组件 imgui_stdlib 为 MIT，portable-file-dialogs 为 WTFPL-2.0。
- argparse 是独立 Git submodule，固定 commit 7d093f8e1201db2dded2eee94de77665698ee9dc，已核验其上游许可证为 MIT。
- CeCILL-C 对修改软件、集成贡献、衍生组合和通知/源码提供有具体条款；这些修改在特定分发方式下如何归类，需要由权利人/法律顾问根据实际组合与交付形态判断。本报告不构成法律意见，也不认定当前仓库已违反许可。
- 不能仅凭当前 CI 编译/测试成功推断许可证义务已满足。

## 5. 下一步整改顺序

1. **DS402 patch manifest：** 在干净 pinned checkout 重放两文件补丁，对照 vendored blob SHA；把本地 JSON fixture 的来源、用途、维护者和测试关联补全。
2. **LRW patch series：** 将 SimulatorControl / EmulatedNetwork / SimulatorControlServer / unit test 的提交整理为可重放补丁系列，附文件 blob SHA、目的、测试用例和测试执行记录。
3. **network simulator patch series：** 把 raw socket errno、ENOBUFS + carrier-down 分类、sysfs carrier/operstate、control channel drain 分为逻辑清晰的补丁单元；验证 idle、link-up ENOBUFS、link-down ENOBUFS 和 redundancy 端口场景。
4. **ESI 依据：** 为 CoE-only / SdoInfo=false 配置补充设备厂商 ESI、协议要求、目标模拟器需求和测试证据；未确认前不要把该 XML 当作目标设备的官方 ESI。
5. **包级许可：** 由权利人确认四个 ROS/Gazebo 包的 MIT 声明是否有意独立于根 Apache-2.0；确认前不自动更改。
6. **供应链与 SBOM：** 分别为 Linux core、KickCAT simulation、unit tests/benchmarks、SocketCAN、IgH、ROS 2 Jazzy、Gazebo Harmonic、Windows/Npcap 等实际可选 profile 建立解析后依赖闭包；生成 CycloneDX 或 SPDX，执行 schema 校验、许可证策略扫描和漏洞扫描，并归档构建参数、工具版本与制品 provenance。

## 6. 验证边界

本轮只完成 Git tree/blob 与代码/元数据静态审查。未运行 DS402 patch replay、KickCAT unit tests、Linux link-fault SIL、ROS 2/Gazebo build、全 profile dependency resolution、SBOM generation/validation、CVE scan、HIL 或物理 EtherCAT 测试；未修改 MotionControlAlgorithms 上游任何源码、LICENSE、NOTICE、package.xml、CI 或依赖声明。
