# 00-01｜IMU 物理误差模型与代表型号数据表口径专项复核（2026-11-15）

## 1. 审查范围

本轮对 `knowledge/sensors/IMU.md` 的关键量纲和公式进行定向复核，范围包括：

- §2 的 IMU 参数定义、§4 的安装/标定/同步建议；
- §6 的 BMI088、ADIS16470 型号示例；
- §8–§10 的白噪声、偏置随机游走、Allan deviation、连续到离散噪声换算、二维 `Q_d`、Gauss-Markov/OU 与多 OU 近似模型；
- Bosch BMI088、Analog Devices ADIS16470 官方产品页和对应数据手册，以及 NXP AN5087 和 ETH Zürich Kalibr IMU Noise Model。

本轮是公开资料和公式边界审查，不使用实际机器人 IMU 原始数据，不构成器件测试报告或导航性能验收。

## 2. 公式与模型复核

### 2.1 白噪声与 Brownian bias 的参数单位

Kalibr 将角速度/比力测量表示为理想输入、慢变 bias 和快速白噪声之和；其参数表分别给出：

- 陀螺/加速度计白噪声密度：`rad/s/√Hz`、`m/s²/√Hz`；
- 陀螺/加速度计 Brownian bias random walk 驱动：`rad/s²/√Hz`、`m/s³/√Hz`。

这两类参数物理含义不同。厂商的 in-run bias stability 或 bias-instability 指标，不可直接替代 Kalibr 的随机游走驱动强度。

连续白噪声按 Kalibr 的理想低通抽取假设转换为离散测量样本时，`σ_d = σ/√Δt`；bias 的 Brownian 单步增量为 `σ_b√Δt`。Kalibr 明确提醒：只做 subsample、没有对应低通抗混叠时，不能按上述公式缩放噪声密度。现有知识页 §8.5 已写明该前提，本轮确认保留。

### 2.2 Allan deviation 读图边界

NXP AN5087 使用 overlapping Allan variance；常见斜率可用于区分白噪声/ARW、bias instability、rate random walk 等过程。由于窗口重叠，不能把每个重叠簇当作统计独立样本。

Kalibr 的 `τ=1 s` 白噪声读值和 `τ=3 s` Brownian random-walk 拟合读值属于其简化模型的读图约定，并有“相关频带由白噪声主导”等假设；不可作为通用 Allan 参数反演规则。知识页 §8.3 已注明这些限制，本轮保留并在 §11 重申。

### 2.3 离散协方差公式

对知识页 §9.4 的单轴状态 `x=[δθ, δb_g]ᵀ`，模型定义为：

`d(δθ)=δb_g dt + σ_g dW_g`，`d(δb_g)=σ_bg dW_bg`。

由该状态模型得到的 `Q_d` 包含角度白噪声项、bias random walk 驱动项和角度—bias 交叉协方差；现有 §9.4 的矩阵形式与声明模型一致。§9.5 一阶 OU 模型的精确离散状态转移及噪声协方差项也与声明的连续模型一致。

这里的“公式一致”只说明解析模型内部自洽，不证明参数来自某个实物传感器。真实 ESKF 仍需按完整误差状态、坐标系、噪声映射矩阵、采样/滤波链计算 `Q_d`，并用独立数据验证。

## 3. BMI088 官方数据对照

来源：Bosch 当前产品页与数据手册 BST-BMI088-DS000-19 Rev.1.9（2024-01）。

| 参数 | 产品页 | 数据手册 Rev.1.9 | 审计结论 |
| --- | --- | --- | --- |
| 加速度计噪声密度 | 175 μg/√Hz | 160 μg/√Hz（X/Y）、190 μg/√Hz（Z）；3g FS、25°C、标称供电、Normal mode | 两套数据口径并存；不自行平均或选取更优值 |
| 加速度计 ODR | 12.5 Hz–2 kHz | 12.5–1600 Hz | 需要按加速度计专属通道引用 |
| 加速度计带宽 | 5–523 Hz（产品概览） | 5–280 Hz，Z 轴列 245 Hz；3 dB cutoff 与 ODR/OSR 有关 | 不能把概览总带宽直接套用到加速度计 |
| 陀螺噪声密度 | 0.014°/s/√Hz | Table 5 对应 47 Hz BW；输出噪声 0.1°/s RMS，并注明 0.014°/s/√Hz | 分开保存噪声密度、带宽和 RMS 输出噪声 |
| 陀螺 ODR/滤波 | 产品概览 12.5 Hz–2 kHz、5–523 Hz | 数据率 100/200/400/1000/2000 Hz，滤波 BW 12–523 Hz 组合 | 必须绑定准确寄存器配置 |

本轮未确认产品页 175 μg/√Hz 与数据手册 X/Y/Z 分轴值差异的原因；应以采购/设计所用数据手册修订版、具体模式及制造商书面答复为准。

## 4. ADIS16470 官方数据对照

来源：Analog Devices ADIS16470 Rev. C 数据手册和官方产品页。

| 指标 | 陀螺仪 | 加速度计 | 备注 |
| --- | --- | --- | --- |
| 动态范围 | ±2000°/s | ±40 g | 型号规格 |
| In-run bias stability（1σ） | 8°/h | 13 μg | 不是 Brownian bias random-walk 驱动 |
| ARW / VRW（1σ） | 0.34°/√h | 0.037 m/s/√h | 与白噪声相关，但转换依赖 PSD/滤波口径 |
| 噪声密度 | 0.008°/s/√Hz，10–40 Hz | 100 μg/√Hz，10–40 Hz | 加速度计数据表注明 no filtering |
| 3 dB 带宽 | 550 Hz | 600 Hz | 不能当作主机输出率 |

陀螺噪声密度 `0.008°/s/√Hz` 按单位直接换算约 `0.48°/√h`，而数据手册另列 ARW `0.34°/√h`；两者数值相差约 √2。单/双边 PSD 归一化是可能的解释，但手册所引用表格未明确两者的换算关系。本报告不认定原因，也不将两个指标直接互换；需向 ADI 确认定义和试验带宽。

采样配置亦须区分：内部时钟名义 2000 Hz；加速度计每次输出由两个 4000 Hz 样本平均得到；内部时钟模式的输出更新率为 `2000/(DEC_RATE+1)`，并存在外部同步/抽取配置。仅写“2 kHz”不足以定义有效样本率或时间语义。

## 5. 当前结论

1. 已完成 IMU 模型、单位和公式的定向 P0 复核；知识页 §11 新增官方资料口径矩阵。
2. 两个代表型号均发现需要保留的条件/口径差异，已明确标记，不将型号级公开指标泛化为通用 IMU 性能。
3. 《IMU》仍保持 `unaccepted_claim_level_review_pending`。没有目标传感器完整型号、硬件 revision、序列号、驱动寄存器配置、ODR/OSR/filter 设置、FIFO/时间戳日志和原始数据。
4. 未进行 Allan/PSD 实测拟合、温度循环、多次上电、旋转台/振动台、Monte Carlo、目标 ESKF NIS/NEES 或实机测试；不得宣称目标 IMU 噪声参数已辨识或定位性能已验证。
5. 资产内容审计范围已记录，但权利人状态仍 `UNVERIFIED`、再分发仍 `UNDETERMINED`。本轮没有复制标准正文或厂商手册内容，只记录短小参数摘要和指向官方原始链接。

## 6. 来源

- [Bosch BMI088 产品页](https://www.bosch-sensortec.com/en/products/motion-sensors/imus/bmi088)
- [Bosch BMI088 Rev.1.9 数据手册](https://www.bosch-sensortec.com/media/boschsensortec/downloads/datasheets/bst-bmi088-ds001.pdf)，pp. 9–11
- [ADI ADIS16470 产品页](https://www.analog.com/en/products/adis16470.html)
- [ADI ADIS16470 Rev. C 数据手册](https://www.analog.com/media/en/technical-documentation/data-sheets/ADIS16470.pdf)，pp. 3–4、27–28
- [NXP/Freescale AN5087](https://www.nxp.com/assets/documents/data/en/application-notes/AN5087.pdf)，pp. 2–6
- [ETH Zürich ASL Kalibr IMU Noise Model](https://github.com/ethz-asl/kalibr/wiki/IMU-Noise-Model)

**审查日期：** 2026-11-15  
**范围：** 公开资料与数学模型复核；非法律意见、非器件认证、非实机验收。
