# 00-01｜SO-101 控制板/舵机型号适用边界 P0 定向审查（2026-11-15）

## 1. 审查对象与结论

对象：`knowledge/projects/reference-desktop-manipulator/12-控制板供应商澄清与电气验证计划.md`（main 原始 Blob SHA `cedf45778c667f854d4ebceba07822200468168c`）。

本轮核对 WaveShare 一手产品文档/FAQ/接线说明、Seeed Studio 官方 SO-ARM101 硬件课程 Chapter 2/6、Hugging Face LeRobot SO-101 官方装配页，并回看 FEETECH 通用 STS 寄存器资料和既有 C046 规格书来源记录。

**本轮 P0 发现：原计划对 C046 保护寄存器的使用范围缺少 Leader/Follower 轴位限定，可能使读者把 C046 数据表和寄存器参数误套到 Follower 六轴。** 已在本分支把 C046 的适用范围收窄为 Seeed 公开映射中的 Leader L4–L6，并明确 Follower 六轴需按 Standard/Pro 版本和准确 SKU 分组。没有修改硬件参数、没有执行实机操作或批准电源选型。

## 2. 已核验的产品/版本事实

### 2.1 WaveShare Bus Servo Adapter (A)

WaveShare 官方产品文档当前明确将 SKU 25514 对应到 Bus Servo Adapter (A)，列出 42×33mm、2.5mm 安装孔、USB-C、UART、DC5521、绿色端子、控制模式跳帽和舵机总线接口；输入规格写 9–12.6V，且注明 5–8.4V 也可输入，输入电压需与舵机匹配。见 [官方规格页](https://docs.waveshare.com/Bus_Servo_Adapter_A)。

WaveShare FAQ 明确：
- 板卡最大可承受电流写为 5A；
- 没有板载电压稳压，舵机输出电压与输入相同；
- 没有独立舵机驱动芯片，而是串口转换 IC；
- USB-to-serial 芯片为 CH343；
- 黑色 DC 输入和绿色端子都可供电，但官方指导为二选一连接。

见 [官方 FAQ](https://docs.waveshare.com/Bus_Servo_Adapter_A/FAQ)。

官方接线说明 USB 控制时跳帽置 B、UART 控制置 A，且舵机电压应匹配输入电源；见 [官方接线示例](https://docs.waveshare.com/Bus_Servo_Adapter_A/Product-Wiring-Example)。

**安全边界：** 5A 是 FAQ 中“最大可承受电流”的表述，缺少持续/峰值时长、环境温度、测量点、连接器与 PCB 降额曲线，不能自动解释为 5A 连续额定，也不能直接作为六轴电源选型依据。原计划已有历史原理图记录标注局部 `MAX:6A`，与 FAQ 的 5A 口径不同；在本轮未重新取得/复审原理图完整文件及实物 PCB 修订版前，不以任一数字推导保护阈值或持续额定值。两种供电接口官方说“任选一种连接”，没有证明可将两路独立电源同时接入，也没有证明存在反灌隔离/OR-ing。

该官方资料确认的是**候选板卡 SKU**，不是用户实际 SO-101 套件已经装配该 SKU；没有板卡实物照片、丝印、PCB Revision、采购 BOM 或批次记录，身份仍未确认。

### 2.2 SO-101 Standard / Pro 与逐轴型号映射

Seeed Studio 官方课程 Chapter 2 将 SO-101 区分为 Standard 与 Pro：
- Standard：Follower 六轴 C001 7.4V，供电为两臂 5V；
- Pro：Follower 为 12V ST-3215 系列（例 C018/C047），Leader 为 7.4V 系列，供电是 Leader 5V / Follower 12V。

见 [Seeed Studio Chapter 2](https://wiki.seeedstudio.com/robotics/soarm_physical_ai_course_chapter_2/)（页面标注 2026-10-19 更新）。

Seeed Studio 官方 Chapter 6 进一步给出轴位映射：
- Leader L1：C044，7.4V，1:191；
- Leader L2：C001，7.4V，1:345；
- Leader L3：C044，7.4V，1:191；
- Leader L4–L6：C046，7.4V，1:147；
- Follower F1–F6：C001（7.4V）或 C018/C047（12V），1:345。

见 [Seeed Studio Chapter 6](https://wiki.seeedstudio.com/robotics/soarm_physical_ai_course_chapter_6/)（页面标注 2026-10-19 更新）。

Hugging Face LeRobot 官方 [SO-101 装配页](https://huggingface.co/docs/lerobot/so101)独立说明 Follower 使用 6×STS3215、1:345；Leader L1/L3=1:191、L2=1:345、L4–L6=1:147，并说明 WaveShare 控制板 USB 使用跳帽 B。LeRobot 的齿轮比表没有独立证明 C046 等具体 SKU，也不证明目标实物批次。

**关键纠偏：C046 是公开配置表中的 Leader L4–L6 候选型号，不是 Follower F1–F6 的通用型号。** Follower 必须按 Standard/Pro 版本和实际铭牌识别 C001/C018/C047。不能把 C046 规格书、寄存器默认值或测试结果套到 Follower 六轴。

### 2.3 C046 规格书的来源限制

既有来源台账 #227 记录的 C046 规格书由 Seeed 文件服务器托管，文件内部标注 FEETECH ST-3215-C046、A/0、2025-04-15；原审计发现首页厂商批准栏未见签字，且目标采购批次适用性待确认。因此它是一个有型号标识的**托管规格书副本**，不能仅凭文件名或镜像托管视为目标采购批次的受控厂商规格。必须取得 FEETECH 或授权供应商针对准确 SKU/批次/固件的确认。

## 3. 原资产中的主张边界审查

| 原资产主张/计划 | 核验结果 | 状态与限制 |
| --- | --- | --- |
| WaveShare 25514 是候选控制板 | 官方规格页确认该 SKU 与产品名对应 | 不证明实际套件/批次使用该板；实物身份待确认 |
| 输入 9–12.6V，也可输入 5–8.4V | 官方规格页仍如此表述，并强调需匹配舵机 | 必须区分板卡允许输入描述、舵机额定电压和整机电源设计；不视为所有 Pro/Standard 组合均可混用 |
| 最大承受电流 5A | 官方 FAQ 当前仍写 5A | 缺少测试条件与持续/峰值分类；不当作连续额定 |
| 舵机 V 输出等于输入 | 官方 FAQ 明确无板载稳压、输出等于输入 | 不能把逻辑 5V/3.3V 转换视为舵机电源稳压 |
| 两种输入接口都可供电 | FAQ 说任选一种连接 | 不推断可并联接入两路电源或存在反灌隔离 |
| C046 保护寄存器计划 | C046 对应 Leader L4–L6 候选组 | 原计划需显式限定轴位；不得套用到 Follower C001/C018/C047 |
| STS 通用内存表保护寄存器 | FEETECH Wiki 明确部分初始值随型号变化 | 不等于 C046/C001/C018/C047 固件默认值或实际读回 |
| LeRobot gripper 的保护参数写入 | 原计划此前基于 SO-Follower 代码路径静态审查 | 应明确是 Follower F6 的应用层配置；不是 Leader C046 的保护参数证明，也不证明其他 Follower 型号固件支持相同语义 |

FEETECH 通用 STS 内存表在本轮重新访问时仍注明部分参数初始值、取值范围因型号而异；地址 13/14/15/19/20/28/34/35/36/38/55/65 的通用描述不能替代准确 SKU/固件的厂商数据。见 [FEETECH STS memory table](https://ftservo.github.io/ftservo-wiki/reference/parameter/memory-sts/)。

## 4. 本轮已实施的文档纠偏

更新 `12-控制板供应商澄清与电气验证计划.md`：
- 将 4.4 标题改为 “C046（SO-101 Leader L4–L6）保护寄存器级核验”；
- 新增 Standard/Pro 供电版本和 Leader/Follower 逐轴 SKU/齿轮比矩阵；
- 只允许对经铭牌/BOM/固件确认的 C046 Leader L4–L6 执行对应的只读寄存器基线；
- REG-02 改为只在相同 SKU/固件/批次/适用轴分组内比较；
- REG-03 限定为 C046 Leader L4–L6 的供应商确认；
- REG-07 限定为 Follower F1–F6，并要求 C001/C018/C047 分组记录，不能以 C046 Leader 数据替代；
- 明确所有映射只是供应商/上游公开指南，不是用户设备的采购 BOM、序列号、固件或实物确认。

追加链接台账 #1751–#1756，记录 Seeed Chapter 2/6、Hugging Face SO-101、WaveShare 产品页/FAQ/接线页本轮核验范围。

## 5. 尚未完成的 P0 项

1. **实物身份：** 用户实际 SO-101 控制板 SKU、PCB Rev、批次、跳帽、USB-UART 芯片未确认；不得把网上产品图当作实物证据。
2. **舵机批次：** 两臂分别逐轴建立 F1–F6 / L1–L6 铭牌、SKU、额定电压、齿轮比、序列号和固件版本清单；Standard/Pro 和不同供应批次不能混为一组。
3. **受控资料：** C046 文件是 Seeed 托管副本且厂商审批栏未见签字；所有准确型号应获得制造商/授权供应商适用批次和固件的受控资料。
4. **电源和板卡额定：** 5A FAQ 与历史原理图 6A 标记的测试口径、连接器/PCB 温升与连续/峰值边界未澄清；板卡不对舵机 V 总线稳压。
5. **SDK/原理图/STEP：** WaveShare 资源目录中的 SDK/STEP/原理图原件尚未逐项下载、固定版本、计算哈希及许可证审查。
6. **测试：** PWR/COM/FAULT/REG/SW/MON/SAFE 项仍是测试计划，未执行供电、负载、温升、串口、故障注入、HIL 或实机保护验证。未获供应商批准前不得进行反接、短路、堵转、超压/欠压或保护寄存器写入。

## 6. 状态结论

- **已完成：** 对候选板卡官方资料、SO-101 Standard/Pro 区别、Leader/Follower 轴位 SKU 映射及公开来源的 P0 边界核验；修正了 C046 保护寄存器适用轴位描述；更新来源台账和资产审查记录。
- **未完成：** 真实板卡/舵机 SKU 和采购批次身份；供应商书面确认；受控原始资料归档；电气/通信/保护实测。
- **状态：** 仅为限定范围的来源和适用边界审查，不能将文件标记为整篇通过或硬件验收完成。00-01 继续进行中。

## 7. 证据入口

- [WaveShare 产品规格](https://docs.waveshare.com/Bus_Servo_Adapter_A)
- [WaveShare FAQ](https://docs.waveshare.com/Bus_Servo_Adapter_A/FAQ)
- [WaveShare 接线示例](https://docs.waveshare.com/Bus_Servo_Adapter_A/Product-Wiring-Example)
- [Seeed SO-ARM101 Standard/Pro 说明](https://wiki.seeedstudio.com/robotics/soarm_physical_ai_course_chapter_2/)
- [Seeed SO-ARM101 逐轴电机映射](https://wiki.seeedstudio.com/robotics/soarm_physical_ai_course_chapter_6/)
- [Hugging Face LeRobot SO-101 装配页](https://huggingface.co/docs/lerobot/so101)
- [FEETECH STS 通用内存表](https://ftservo.github.io/ftservo-wiki/reference/parameter/memory-sts/)
- [外部来源台账](../../链接台账.md)（#1751–#1756）

