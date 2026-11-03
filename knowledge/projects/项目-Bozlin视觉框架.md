---
tags: [项目, 视觉框架, 建筑机器人]
aliases: [项目-Bozlin视觉框架, Bozlin, boz framework, VisionServer]
路径: E:\boz\framework
创建日期: 2026-11-01
更新日期: 2026-11-01
---

# 项目：Bozlin Vision Framework V2（跨平台机器人视觉框架）

> **定位**：面向**建筑/装修机器人**（铺地砖、抹墙、刮腻子、打磨、贴墙纸、举升、测量）的**跨平台机器视觉框架**（Windows/Linux，送检版本运行于 Jetson TX2）。Poco 为核心库、GTest 单测、V2.0.0 于 2019-2020 送检测中心。
> **路径**：`E:\boz\framework`

## 1. 项目构成（5 个模块）

| 模块 | 内容 |
|---|---|
| **Bozlin/**（核心源码） | Core（SDK/Server 共享类型）/ Server（HTTP、TCP 服务）/ **Devices**（相机设备抽象）/ **Algorithms**（算法插件）/ Activities（业务逻辑）/ App（各机器人主入口）/ SDK / Python |
| **VisionGuard/** | 视觉守护进程（config.json 定义云升级接口集） |
| **Guardian/** | 守护模块（CMakeLists + src） |
| **Daemon/** | BozlinDaemon：启动请求处理工厂、启动服务（框架自启动载体） |
| **update / white_box_testing** | 自更新 + 白盒测试 |

## 2. 设备抽象层（Devices/——多相机接入实证）

| 设备 | 说明 |
|---|---|
| BZLCamera | 自研相机抽象基类族 |
| HikvisionCamera | 海康 MVS SDK |
| BaslerCamera | Basler Pylon SDK |
| FaroLaserScanner | 法如激光扫描仪（大场景 3D 扫描→测量/建模） |
| PhoXi3DScanner | Photoneo 结构光 3D 相机（高精度点云） |
| RealSenseCamera | Intel RealSense（→ [[深度相机]]） |
| FakeCamera | 测试用虚拟设备（→ [[构建与CI工具链]] 里的"假驱动"模式） |
| CANET | CAN 转以太网（与机器人本体通信 → [[实时系统与嵌入式]]） |

## 3. 算法插件层（Algorithms/——建筑机器人工艺全景）

| 工艺 | 算法模块 |
|---|---|
| 地砖铺贴 | CatchFloorTile（抓取地砖）、SmoothFloorTile（地砖找平） |
| 墙面处理 | Wallplaster2 / wallplasterOpencv（抹灰/刮腻子）、wallpolishOpencv（打磨）、wallpaperOpencv（贴墙纸） |
| 砌墙 | wallbrickalgorithm |
| 举升 | jackup（举升视觉定位） |
| 测量 | fakemeasure、show3d（三维显示）、onshow |
| 通用 | simple（模板示例）、Joint（接缝）、exception |

> 每个 App 子目录（VisionServer / JackupVisionServer / MeasureVisionServer）= 一种机器人形态的视觉服务入口——**一个框架服务多机型**。

## 4. 技术栈（3rdparty/ 全清单即技术选型）

| 用途 | 库 |
|---|---|
| 框架底座 | **Poco**（HTTP/TCP/Util/进程） |
| 通信 | **zmq**、**gRPC**、**mosquitto（MQTT）** |
| 安全 | openssl、des（加密） |
| 图像 | libpng / libJpeg / zlib、OpenCV（算法内） |
| 数据 | **libpqxx（PostgreSQL 客户端）**、unqlite（嵌入式 KV）、SQLite 类 |
| 串口 | serial / CSerial（设备层 → [[实时系统与嵌入式]]） |
| 测试 | googletest（GTest 单测目录 + white_box_testing） |
| 专属 | pinkAgentSDK（机器人代理 SDK） |
| 文档生成 | libharu（PDF 生成——测量报告输出） |

## 5. 云升级机制（VisionGuard/config.json 实证）

```
cloudServer: https://bzlcloud.xyz
升级链路: upgradefilecheck → beginupgrade → 版本信息/下载/MD5 校验
  → installPath /VisionServer + backupFolder /visionServer_bak(备份回滚!)
  → 算法包/设备包/框架包 分通道上传下载 (upgradeAlg/upgradeDev/downloadFrame)
运维: 心跳上报(heartpag)、日志上传(单文件/压缩包)、注册(在线/离线)、任务队列拉取
服务形态: systemd 类服务名 visionServer
```
→ 与 [[云端协同与OTA流程]] 的"备份分区+回滚"完全同构；与 [[项目-清洁机器人]] 的 ros_ota 同期实现。

## 6. 数据流（框架主循环）

```
相机采集(Devices 多相机) → 环形缓冲/线程池
  → 算法插件(Algorithms 注册表: SimpleAlgorithm/SprayAlgorithm + 工艺算法)
  → 结果路由(结构化结果: 定位偏差/平整度/完成度)
  → Server(HTTP/TCP API 暴露) + 云上报(MQTT/心跳)
  → 本体执行(CANET→机器人 PLC/控制器) + PDF 报告(libharu)
守护链: Daemon(启动) + Guardian/VisionGuard(守护+自更新)
```

## 7. 架构评价与行业映射

- **插件化思想成熟**：Core/Server/Devices/Algorithms 四分法 = 设备-算法-服务-类型解耦，是 [[项目-清洁机器人]] `modules/` 目录结构的直接蓝本（→ [[三项目关系总览]] 血缘证据）
- **跨平台工程**：Windows/Linux 双端 + CMake 统一构建（`cmake/` 目录工具链）
- 行业对标：Cognex VisionPro / Halcon HDevelop+应用壳 / 海康 Vision Master 的"自研版"
- 建筑机器人赛道：对标大界机器人（建筑机器人视觉与工艺系统）、研砼/筑智建等

## 8. 知识库映射

| 项目实现 | 通用知识页 |
|---|---|
| 多相机设备抽象 | [[深度相机]] · [[视觉软件栈]] |
| Faro/PhoXi 3D 扫描 | [[激光雷达]]（3D 扫描同源技术） |
| Poco HTTP/TCP 框架 | [[视觉软件栈]]（工业视觉框架形态） |
| 算法插件注册 | [[视觉感知算法]]（工艺检测类） |
| VisionGuard 云升级 | [[云端协同与OTA流程]] |
| GTest + 白盒测试 | [[构建与CI工具链]] |

## 相关链接
- 同族：[[项目-amr]] · [[项目-清洁机器人]] · [[三项目关系总览]]
- 领域：[[视觉软件栈]] · [[特种机器人]]（建筑机器人归此域）
