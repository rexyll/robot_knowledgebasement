---
tags: [软件, 云平台, IoT, MQTT]
aliases: [云平台, IoT, MQTT, 物联网, 设备接入]
创建日期: 2026-11-01
更新日期: 2026-11-01
---

# 云平台与 IoT 通信

> 机器人车队的大脑后端：设备接入、数据上报、远程控制、OTA、业务系统（工单/报表/看板）。协议三件套：**MQTT（遥测+指令）、HTTP/REST（文件+管理）、WebSocket（实时看板）**。

## 通信协议选型

| 协议 | 模式 | 带宽开销 | 场景 | 备注 |
|---|---|---|---|---|
| **MQTT 3.1.1/5.0** | 发布/订阅 + Broker | 极低（2 字节头起） | 遥测上报、指令下发、车队状态 | 机器人事实标准；QoS0/1/2 三级 |
| HTTP/REST | 请求/响应 | 高 | OTA 文件下载、配置拉取、管理 API | 简单、调试友好 |
| WebSocket | 全双工长连接 | 低 | 实时监控大屏、视频转发 | 浏览器友好 |
| gRPC | RPC 流 | 中 | 内部微服务、车云高性能 | Protobuf 强类型 |
| CoAP/LwM2M | 轻量 UDP | 极低 | MCU 级设备 | 低功耗传感 |

## MQTT 主题树设计（机器人车队模板）

```
genrobot/{site}/{robotId}/...        # 站点+机器人二级命名
├── status          # 心跳/在线状态  保留位 Retain
├── telemetry/odom  # 位置电量 1-5Hz
├── telemetry/health# CPU/温度/错误码
├── event/{type}    # 任务完成/异常/急停 事件流
├── cmd/{type}      # 下行指令（任务/暂停/召回充电）
├── ota/notify      # OTA 通知（版本/进度） → [[云端协同与OTA流程]]
└── log/upload      # 日志切片上传
QoS: 遥测 QoS0、指令与事件 QoS1、 OTA 关键帧 QoS1+幂等去重
安全: TLS1.2+ + 每设备证书/用户名密码 + ACL(只许自己的主题树)
```

## 云平台功能模块

| 模块 | 内容 |
|---|---|
| 设备接入层 | MQTT Broker（EMQX/Mosquitto/阿里云 IoT）、设备注册、证书管理 |
| 数据管道 | 消息总线（Kafka）、时序库（TDengine/InfluxDB/TimescaleDB）存轨迹与遥测 |
| 业务服务 | 任务/工单、地图管理、电子围栏、用户权限、报表 |
| 视频与接管 | WebRTC 远程视频接管（清洁/服务机器人远程干预） |
| 数字孪生 | 地图+实时位置的 2D/3D 看板 → [[仿真平台]] |
| 开放 API | 给第三方 WMS/物业系统 → [[调度系统RMS]] |

## 端侧实现形态

- **ROS2 内独立 IoT 节点**：[[项目-清洁机器人]] 的 `ros_iot`（从 ros_framework 拆出的云通信独立节点）——架构解耦范例
- **App 直连**：Android 端 MQTT 客户端直连 Broker（同主题树、不同 ACL）→ [[项目-清洁机器人]] App/
- **边缘网关**：多机器人共享一个网关出网（工厂内网隔离场景）

## 可靠性与安全清单

1. 断网续传：本地环形缓冲 + 补报（时间戳去重）
2. 时钟同步：NTP/北斗，否则轨迹与事件对不上
3. 指令幂等：msgId + 去重表，防止重发导致重复任务
4. 固件-云端版本协商：能力版本号上报（对应 [[项目-amr]] 的 CONTRACT_VERSIONING 思想）
5. 隐私：视频/地图数据分级加密；欧盟市场 GDPR → [[标准与法规]]

## 上游板块
- [[09-09-网络通讯设计]] —— 车外网通道与安全边界（流程）
- [[DDS专题]] —— 车内 DDS 与车云 MQTT 的边界（软件）

## 下游板块
- [[云端协同与OTA流程]] —— OTA 承载协议（流程）
- [[调度系统RMS]] —— VDA5050 over MQTT（软件）
- [[项目-清洁机器人]] —— ros_iot 节点 + Cloud/（aedes broker）实例（项目）

## 细节加深（V2）
- **Mosquitto 是轻量自建 broker 首选**（台账 #92）：Eclipse 开源（EDL-1.0），单机万级连接；万级以上/集群选 EMQX（商业开源双轨）。[[项目-清洁机器人]] 的 Cloud/ 即 Node.js + aedes（进程内 broker，嵌入式云端形态）。
- **QoS 实战映射**：遥测 QoS0 / 指令与事件 QoS1 / QoS2 不用（开销大且业务可幂等替代）——与本页 V1 结论一致的官方推荐做法。
- **车云协议边界铁律**：DDS 不出车。跨广域网用 MQTT/Zenoh/私有 TCP——[[项目-amr]] 用 ZMQ+protobuf 同理（弱网组播不可靠）。

## 代码实例与开源项目
| 项目 | 语言 | 许可证 | 说明 | 链接 |
|---|---|---|---|---|
| Eclipse Mosquitto | C | EDL-1.0(EPL/EDL 双许可) | 轻量 MQTT broker | https://mosquitto.org |
| paho.mqtt.python | Python | EDL-1.0 | MQTT 客户端（车端/云端通用） | https://github.com/eclipse/paho.mqtt.python |

> 链接验证：[[链接台账]] #92（快照 2026-11-01）。

## 相关链接
- 上位：[[软件地图]] · [[调度系统RMS]]
- 流程：[[云端协同与OTA流程]] · [[多机调度流程]]
- 项目实例：[[项目-清洁机器人]]（Cloud/ = MQTT broker + HTTP API + OTA；ros_iot 节点）
- 协议标准：[[标准与法规]]（VDA5050 也是 MQTT 承载）
