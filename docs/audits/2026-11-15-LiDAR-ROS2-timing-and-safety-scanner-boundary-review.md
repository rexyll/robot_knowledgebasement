# 00-01｜LiDAR 型号参数、ROS 2 数据时序与安全扫描仪边界专项复核（2026-11-15）

## 1. 审查范围

对 `knowledge/sensors/激光雷达.md` 进行 P0 定向复核：ROS 2 Jazzy 的 `sensor_msgs/msg/LaserScan` 和 `PointCloud2` 字段语义；Livox Mid-360 官方规格及测试脚注；SICK TiM1xx 普通 2D LiDAR 与 nanoScan3 I/O 安全激光扫描仪用途/安全输出边界；IEC 60825-1:2014、IEC 61496-3:2025 当前版次及适用范围。

本轮是公开资料和接口定义审查，不使用目标机器人原始雷达数据，不构成产品认证或现场安全验收。

## 2. ROS 2 Jazzy 接口语义

### 2.1 LaserScan

ROS 2 Jazzy 的消息定义说明：
- `header.stamp` 是扫描第一束 ray 的 acquisition time；
- 在 `frame_id` 坐标系内，角度绕 +Z 轴测量；Z 向上时逆时针为正，0 rad 沿 +X；
- `time_increment` 是相邻测量时间，供运动状态插值使用；`scan_time` 是相邻两帧扫描的时间间隔；
- `intensities` 使用设备特定单位，无强度数据时应留空；`ranges` 超出 `range_min/max` 的数值按消息定义丢弃。

风险：若驱动将接收时间写入 header.stamp、将 frame 中点/末点写成第一束时刻，或误把 scan_time 填入 time_increment，去畸变和多传感器时间同步都会产生系统偏差。消息字段定义本身不能替代设备驱动实现验证。

### 2.2 PointCloud2

ROS 2 Jazzy 将点云保存为由 `fields` 描述的二进制 blob；有组织点云使用二维 height/width，无组织点云常以 height=1 表示；`point_step`、`row_step`、`is_bigendian` 和 data 长度决定内存布局。

基础消息没有规定统一的逐点时间字段。驱动若添加 `time`、`t` 或 `timestamp`，须结合准确驱动源码/协议确认其单位、参考时钟和相对/绝对时刻。不能仅凭字段名称猜测，也不能在未确认时宣称完成逐点 deskew。

## 3. 代表产品数据边界

### 3.1 Livox Mid-360

官方规格页将量程标注为 100 klx 下 40 m @10% 反射率、70 m @80%；近距离盲区 0.1 m；水平/垂直视场 360°/−7°至+52°；first-return 点率 200,000 points/s、典型 10 Hz、PTPv2/GPS 同步、IP67。

关键脚注：
- 0.1–0.2 m 虽可输出点云，但厂商不保证探测精度；
- 10 m 和 0.2 m 测距随机误差测试条件为 25°C、80% 反射率；
- 0.1–1 m 范围内低反射率/细小目标可能无法保证效果；
- 强烈振动、大雾和高低温会影响性能；−20至0°C自加热峰值功率可达14 W。

因此不能把40/70 m量程写成所有反射率目标保证值，不能把误差数值脱离脚注，也不能凭Class 1宣称机器安全功能。

### 3.2 普通 LiDAR 与安全扫描仪

SICK TiM1xx 官方操作说明把它定义为室内 2D LiDAR，TiM10x/TiM15x 量程分别至 3 m/10 m，配置区域被侵入后可通过数字输出报告，但同一手册明确声明该设备不是机器安全标准下的安全组件。

SICK nanoScan3 I/O（指定 Core I/O / Pro I/O 产品）的 2026-05-26 手册列 Type 3、SIL 2、Category 3、PL d、PFH 8×10⁻⁸ h⁻¹、任务时间 20 年和 OSSD 输出；但手册同时明确区分：
- 安全相关保护字段和 OSSD；
- 以太网测量数据仅供一般监控/AGV导航，不能当作安全相关数据输出；
- 不允许室外、水下、爆炸危险区域使用，且不能用于透明物体检测。

这个例子说明：即使某设备本身是安全扫描仪，也不能把它的普通导航测量通道当成安全输出；必须按具体型号、已验证配置和专用安全接口设计完整安全链。

## 4. 标准版本和适用范围

- IEC 60825-1:2014 第 3 版的 IEC 官方页面仍显示 Valid；其主题是激光产品辐射安全分类和要求。页面将第 4 版显示为 ACD 阶段、预测 2027-02-01 发布，不能当作已经发布的现行标准。
- IEC 61496-3:2025 第 4 版官方页面标记有效，针对使用漫反射响应主动光电保护器件（AOPDDR）的电敏保护设备设计/制造/测试附加要求；未定义具体机器的保护区域布置，也不包含室外应用测试。
- Class 1 激光等级和机器安全扫描器 Type/PL/SIL 是不同分类维度，不能互相替代。

## 5. 本轮结论与遗留项

已完成公开来源、ROS 接口和标准范围定向审查，已修订知识页 §8。仍未完成：
- 目标设备准确 SKU、硬件 revision、固件和驱动 commit/配置；
- LaserScan/PointCloud2 原始消息、时间戳来源、PTP 锁定与时钟偏差；
- 点内时间字段和 IMU/里程计对齐、旋转雷达去畸变实测；
- 玻璃/黑色吸光/细线/低反射率/雨雾/阳光等目标场景检测概率和误检漏检试验；
- 多雷达串扰、振动、温度、污损、保护区域/停止时间、故障注入和安全控制链验证。

因此《激光雷达》继续保持 `unaccepted_claim_level_review_pending`。本轮没有宣称目标雷达的检测距离、精度、安全等级或整机性能已经被验证。

## 6. 来源

- [ROS 2 Jazzy LaserScan.msg](https://github.com/ros2/common_interfaces/blob/jazzy/sensor_msgs/msg/LaserScan.msg)
- [ROS 2 Jazzy PointCloud2.msg](https://github.com/ros2/common_interfaces/blob/jazzy/sensor_msgs/msg/PointCloud2.msg)
- [Livox Mid-360 官方规格](https://www.livoxtech.com/cn/mid-360/specs)
- [SICK TiM1xx 操作说明 8020631](https://www.sick.com/media/docs/5/65/965/operating_instructions_tim1xx_2d_laser_scanner_en_im0070965.pdf)
- [SICK nanoScan3 I/O 操作说明 8024596](https://www.sick.com/media/docs/7/37/137/operating_instructions_nanoscan3_i_o_en_im0087137.pdf)
- [IEC 61496-3:2025](https://webstore.iec.ch/en/publication/84133)
- [IEC 60825-1:2014](https://webstore.iec.ch/en/publication/3587)

**审查日期：** 2026-11-15  
**范围：** 公开资料与接口边界核验；非法律意见、非产品认证、非现场验收。
