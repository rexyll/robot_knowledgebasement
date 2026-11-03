---
tags: [软件, 工具链, CI]
aliases: [工具链, colcon, CMake, CI]
创建日期: 2026-11-01
更新日期: 2026-11-01
---

# 构建与 CI 工具链

> 机器人软件的工程纪律：多语言多包构建 → 单元/集成测试 → 冒烟 → 打包发布。两个内部项目都建立了完整台账式 CI 流程（本页记录其模式作为行业参考实践）。

## 构建系统链

| 层 | 工具 | 说明 |
|---|---|---|
| C++ 底层 | **CMake**（≥3.16） | ament_cmake（ROS2 C++ 标准）、纯 CMake（如 [[项目-Bozlin视觉框架]]） |
| ROS2 构建 | **colcon** | `colcon build --base-paths src --parallel-workers N`；`--symlink-install` 开发热替 |
| Python 包 | setuptools/ament_python | setup.py/package.xml 双声明 |
| Android | Gradle | [[项目-清洁机器人]] App 端 `build.gradle.kts` |
| 依赖固化 | rosdep、vcstool、Docker 镜像 | `rosdep install --from-paths src` |

## 包组织规范（多包工作区）

```
src/
├── interfaces/        # 消息/服务/Action 定义包（独立小包,版本化）
├── drivers/           # 传感器/底盘驱动
├── algorithms/        # 算法库（纯库,不依赖运行时）
├── capabilities/      # 业务能力包（见 [[项目-amr]] 插件架构）
├── bringup/           # 启动配置、参数文件、launch
└── 3rdparty/          # 第三方（固定版本）
```

- 接口先行：`.msg/.srv/.idl` 变更必须独立提交 + 版本号 + SHA256 契约（[[项目-amr]] 的 CONTRACT_IDL.sha256 实践）→ [[ROS与ROS2]]

## 测试金字塔（机器人版）

```
        集成/系统测试: launch_testing 多节点 + rosbag2 回放回归
      组件测试: 单节点注入假驱动(话题桩) + 行为断言
    单元测试: gtest(ros2 接口 mock) / pytest(rclpy)
  静态: clang-tidy/lint + 编译警告=错误
```

- ROS2 单测：`ament_add_gtest`、`launch_testing`；Python：`launch_pytest`
- 仿真冒烟：headless Gazebo/自研轻量仿真跑固定场景脚本（到位时间/碰撞次数断言）→ [[仿真平台]]

## 内部项目的 CI 模式（实际观察到的好实践）

| 项目 | CI 形态 |
|---|---|
| [[项目-amr]] | `scripts/ci_capability.sh`（构建+16 包 106 用例）+ `capability_smoke_stability.sh 3 150`（3 轮×150s 稳定性冒烟，输出 RESULT PASS）+ 文档链接检查（43 个 md/225 链接全绿） |
| [[项目-清洁机器人]] | 三层测试网：**契约测试**（接口形状）→ **冒烟**（单机流程）→ **行为测试**（业务场景 FSM 断言）；`build_all.sh/package_all.sh/deploy_all.sh` 全链脚本 |
| [[项目-Bozlin视觉框架]] | GTest 单元测试目录 + 白盒测试模块（white_box_testing/） |

> 通用经验：**台账化**（TaskPlan/REPOS.md 单一事实源）+ **稳定性冒烟固定轮次**（发现内存泄漏/句柄泄漏）+ **文档链接 CI**（防架构文档腐烂）。

## 发布打包

- ROS2：colcon 打包 → deb/tar；整机发布含固件+ROS2+配置 → 差分 OTA 包 → [[云端协同与OTA流程]]
- 版本策略：语义化版本（SemVer）+ 契约版本表 + ReleaseNotes（[[项目-Bozlin视觉框架]] 的 ReleaseNotes.txt 模式）
- 灰度：云端按机器人分组灰度推送 → [[云平台与IoT通信]]

## 上游板块
- [[ROS与ROS2]] —— colcon/ament 生态（软件）
- [[09-06-操作系统选型与内核裁剪]] —— 镜像构建纳入 CI（软件）

## 下游板块
- [[09-10-系统联调与测试]] —— 三层测试网实操（流程）
- [[云端协同与OTA流程]] —— CI 产物→灰度发布（流程）
- [[项目-amr]]（ci_capability 六步门禁） · [[项目-清洁机器人]]（三层测试网） —— 台账实践源（项目）

## 细节加深（V2）
- **colcon 官方文档**（台账 #94）：`--packages-select`/`--packages-up-to`（增量构建）、`--event-handlers console_direct+`（实时日志）是日常三件套。
- **launch_testing 是集成测试标准件**（台账 #46，v3.4.13）：`generate_test_description()` + ReadyToTest + 进程退出码断言——把"起得来、数据活着、死得干净"写成代码。
- **契约 lint 思路**（源自 [[项目-amr]]）：消息/服务定义变更必须独立提交+SHA256 指纹+兼容表更新——CI 里跑 `git diff --exit-code interfaces/ || 校验契约版本`。

## 代码实例与开源项目
| 项目 | 语言 | 许可证 | 说明 | 链接 |
|---|---|---|---|---|
| colcon 文档 | Python | Apache-2.0/BSD | 官方构建编排 | https://colcon.readthedocs.io |
| launch_testing | Python | Apache-2.0 | ROS2 集成测试框架（v3.4.13） | https://docs.ros.org/en/jazzy/p/launch_testing/ |
| rosbag2 | C++/Python | Apache-2.0 | 录包回归基础设施 | https://docs.ros.org/en/rolling/p/rosbag2/ |

> 链接验证：[[链接台账]] #46/#83/#94（快照 2026-11-01）。

## 相关链接
- 上位：[[软件地图]] · [[ROS与ROS2]] · [[仿真平台]]
- 项目实例：[[项目-amr]] · [[项目-清洁机器人]] · [[项目-Bozlin视觉框架]]
