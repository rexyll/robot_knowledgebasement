---
tags: [软件, DDS, 中间件]
aliases: [DDS专题, DDS]
创建日期: 2026-11-01
更新日期: 2026-11-01
---

# DDS 专题（Data Distribution Service）

> ROS2 的通信地基。理解 DDS = 理解 ROS2 的 QoS、发现机制、多机组网的全部怪癖。[[ROS与ROS2]] 讲「怎么用」，本页讲「底下是什么、坏了怎么查」。

## 1. DDS 是什么（30 秒版）

- OMG 标准（DDS v1.4 + DDS-RPC），**以数据为中心**的发布订阅中间件：无 Broker、无中心节点，参与者（DomainParticipant）通过**组播发现**彼此后 P2P 直连。
- 传输层默认 UDP 组播+单播；支持 shared memory（进程内零拷贝）与 TCP。
- ROS2 的 `rmw`（ROS Middleware）层抽象 DDS 实现——**同一份代码可换 RMW**。

## 2. 三大实现对比（2026 现状）

| 实现 | 许可证 | 语言 | ROS2 地位 | 强项 | 链接（台账验证） |
|---|---|---|---|---|---|
| **Fast DDS**（eProsima） | Apache-2.0 | C++ | Jazzy 默认 | 文档全、Discovery Server 先进 | #19 |
| **Cyclone DDS**（Eclipse） | EPL-2.0/EDL-1.0 | C | Tier-1 可选 | WiFi/多网卡更稳、C 实现内存占用低 | #20 |
| Connext（RTI） | 商业 | C++ | Tier-1 商业支持 | 车规/航天级支持合同 | 官网 rticommunity.com（未列入本轮） |
| **Zenoh**（Eclipse，非 DDS） | EPL-2.0/Apache-2.0 | Rust | 桥接/替代 | 跨网段/弱网/大规模；broker 模式可选 | #21/#22 |

## 3. QoS 速查（ROS2 第一坑的完整地图）

| QoS | 取值 | 效果 | 典型组合 |
|---|---|---|---|
| Reliability | RELIABLE / BEST_EFFORT | 重传 / 尽力 | 传感器 BEST_EFFORT，指令 RELIABLE |
| Durability | VOLATILE / TRANSIENT_LOCAL | 迟加入者能否收到历史 | 地图/参数 TRANSIENT_LOCAL |
| History | KEEP_LAST(N) / KEEP_ALL | 队列深度 | 传感器 KEEP_LAST(1-5) |
| Deadline / Lifespan | 时长 | 超时检测 / 消息有效期 | 心跳 Deadline 0.5s |
| **兼容规则** | 发布较"强"订阅较"弱"才通 | RELIABLE pub + BEST_EFFORT sub ✅；反向 ❌ | 收不到先查这里 |

```bash
ros2 topic info /scan --verbose   # 看发布/订阅双方实际 QoS —— 排障第一步
```

## 4. 发现机制与多机排障

```
简单发现(默认): 组播 SPDP 找参与者 → 单播 SEDP 交换端点
  → WiFi 组播被 AP 抑制/跨 VLAN 就瞎 → 三板斧(→ [[09-09-网络通讯设计]])
Discovery Server(Fast DDS): 中心化发现表, 单播全网, 跨网段方案
Zenoh 桥: zenoh-bridge-ros2dds 跑在网段边界, ROS2 图跨桥扩展(#22)
```

排障命令链：`ros2 doctor` → `ROS_DOMAIN_ID` 一致性 → `ros2 multicast receive/send` 测组播 → 抓包 `tcpdump port 7400`。

## 5. 性能调优（关键旋钮）

- **大消息（点云/图像）**：shared memory（Fast DDS SHM / Cyclone iceoryx）或 intra-process composition（→ [[ROS与ROS2]]）
- **UDP 缓冲**：`net.core.rmem_max=8388608` 等 sysctl——点云丢帧先查这里
- **Cyclone 配置**：`CYCLONEDDS_URI` 锁网卡、关组播、调碎片（fragmentation）
- **基准工具**：`performance_test`（Fast DDS 自带）对比 RMW 吞吐

## 6. 上游板块
- [[ROS与ROS2]] —— rmw 抽象与生态（软件）
- [[09-06-操作系统选型与内核裁剪]] —— 内核 UDP 缓冲/sysctl（软件）

## 7. 下游板块
- [[09-09-网络通讯设计]] —— 组网方案选型（流程）
- [[云平台与IoT通信]] —— 车云边界用 MQTT/Zenoh 而非裸 DDS（软件）
- [[09-07-软件栈搭建]] —— RMW 切换实操（流程）

## 8. 细节加深（V2）
- **DDS-RPC**：DDS 标准的 request/reply 扩展，ROS2 Service/Action 底层逐步向其靠拢——跨厂商互操作的前提。
- **选型经验法则**（社区共识+本库项目佐证）：单机默认；多机有线可默认；**WiFi/VPN/跨网段直接上 Zenoh 桥**（[[项目-amr]] 用 ZMQ+protobuf 做跨机总线同理——弱网场景大家都在绕开裸 DDS）。
- **调试神器**：Fast DDS 的 `DDS Shaper`/`shapesdemo` 可独立于 ROS 演示 QoS 行为——教学演示 QoS 兼容矩阵最快的方式。

## 9. 代码实例与开源项目
| 项目 | 语言 | 许可证 | 说明 | 链接 |
|---|---|---|---|---|
| Fast DDS 文档 | C++ | Apache-2.0 | 官方文档（含 Discovery Server 教程） | https://fast-dds.docs.eprosima.com/en/latest/ |
| Cyclone DDS | C | EPL-2.0/EDL-1.0 | GitHub 主仓 | https://github.com/eclipse-cyclonedds/cyclonedds |
| zenoh-bridge-ros2dds | Rust | EPL-2.0/Apache-2.0 | ROS2 图跨网段扩展 | https://github.com/eclipse-zenoh/zenoh-plugin-ros2dds |

> 链接验证：[[链接台账]] #19-#22（快照 2026-11-01）。

## 相关链接
- [[ROS与ROS2]] · [[09-09-网络通讯设计]] · [[术语表]]
