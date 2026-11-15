# 安全防护器件：2026-11-15 官方来源与主张边界增量审计

- 审计日期：2026-11-15
- 资产：knowledge/safety/安全防护器件.md
- 风险等级：P0（机器安全/人员防护）
- 范围：ANSI/A3 R15.06、OSHA、ISO/DIS 3691-4，以及 OMRON OS32C/G9SE、SICK microScan3 Core I/O、Siemens 3SK1、Pilz PSENmlock、Schmersal AZM300、EUCHNER CTP 的公开目录/产品页/官方操作说明
- 结论：完成指定条目的官方来源增量核验并发现若干页面/参数定义边界；**整篇知识页仍未通过完整 claim-level 验收**。

## 1. 关键增量和来源冲突

### 1.1 ANSI/A3 R15.06-2025 Part 3 发布状态

A3 商店出版物页把文件列为 ANSI/A3 R15.06-2025 Parts 1&2 与独立编号 ANSI/A3 R15.06-3-2025 Part 3，明确三部分于 2025-10-29 一并发布；Part 1/2 于 2025-08-21 获批，Part 3 于 2025-10-07 获批。Part 3 名称为 *Use of Industrial Robot Cells*。A3 另一个机器人安全标准概览页仍标为 “Part 3 coming soon”。本审计记录为同一组织公开页面间状态不同步，以具体出版物页面的文件编号和发布记录为引用依据，并保留冲突提醒。

OSHA Robotics Standards 页面（本轮访问）明确称没有专门针对机器人行业的 OSHA 标准，并将 R15.06-2012 作为共识标准例子；该页面说明 National Consensus Standards 不是 OSHA regulations，并列出 29 CFR 1910 适用条款。页面还指出 OSHA-approved State Plans 可能有不同或更严格要求。故不能把 R15.06-2025 称为 OSHA 法规，或把 OSHA 页面保留的 2012 引用当作 2025 版本状态。

## 2. ISO/DIS 3691-4 生命周期页面内部字段不一致

ISO 新版官方页面将 ISO/DIS 3691-4 标为 Draft International Standard / Under development，且称将替代 ISO 3691-4:2023；通用状态字段显示 Stage 40.60（Close of voting），而同页 life-cycle timeline 同时列出 40.99（DIS approved for registration as FDIS）。页面内部不能支持一个无歧义的精确当前 stage。本审计只确认其仍为 DIS 草案、未发布；当前已发布版本仍是 ISO 3691-4:2023。不得把 DIS 当作已生效替代标准，也不擅自将 40.99 的时间线事件推断为已完成 FDIS。

## 3. 器件与参数定义核验

### 3.1 OMRON OS32C

官方规格页（2025-10-01 更新）确认 Type 3、PL d/Category 3、SIL 2、检测分辨率、变体量程、270°和 ON→OFF 80–680 ms 配置范围。普通 OS32C 和 -4M 型号安全区/警告区范围不同。规格页脚注描述 PTM 每扫描增加 6 ms；用户手册 Z296-E1-15 / P/N 99863-0010 Rev.R 的 Table 2-5 对 PTM-RBM active 单独列出响应时间，例如 2 scans 为 94 ms，而 without PTM-RBM 为 80 ms。两种配置名/口径不能被合并成单一固定偏置。实际配置必须通过设备配置导出和状态显示核验。

### 3.2 SICK microScan3 Core I/O

官网操作说明 8016346/1SK3/2025-07-04 复核：4.0 m/5.5 m 量程变体为 30/40 ms 扫描周期；9.0 m 量程变体为 40/50 ms；响应时间下限分别为 ≥70 ms、≥90 ms。响应时间公式为 tR = (tS + tI) × n + tO；OSSD pair 1 的 output processing term 为 10 ms。保护区距离还需包含机器停止、控制器处理、信号传播、控制分辨率和反射测量误差。

### 3.3 Siemens SIRIUS 3SK1

11/2025 Equipment Manual A5E02526190021A/RS-AF/006 确认自动启动和 manual start 均不允许用于急停；急停若以 PL e / SIL 3 为目标必须使用 monitored start。反馈回路监视受控接触器/继电器等执行元件并限制安全输出重新使能。响应时间总和包括受影响输入扩展、基本单元、输出扩展和下游执行器。新增关注点：manual 对 Stop Category 1 的安全输出延时断开提供了限制说明；某些内部故障和掉电状态可能使安全输出立即断开。

### 3.4 OMRON G9SE

官方规格页当前可访问但最后更新日期仍为 2019-06-17；所列 G9SE-201/401/221-T[] 规格把 15 ms 定义为 ON→OFF 主安全接点响应时间（包含 bounce），100 ms 是 OFF→ON operating time（不包括 bounce）；在安全输出电路非定期自诊断执行时，该 operating time 可最大达到 500 ms。该页的“15 ms”和“100 ms”不可统一表述为一个响应时间，页面旧日期要求选型时继续取具体订货号的最新受控说明书。

### 3.5 Pilz PSENmlock、Schmersal AZM300、EUCHNER CTP

Pilz 系列公开页面最高保持力为 7,500 N，且指出 emergency release 不能用于 automatic-reset 版本。此为系列级最大值，不能替代具体订货号的安全保持力或门体设计。Schmersal AZM300Z-ST-1P2P-A-T（103011112）公开页把编码等级列为 ISO 14119 Low，并分别给出 actuator 路径最大 100 ms、安全输入路径最大 1.5 ms、risk duration 最大 200 ms。EUCHNER CTP-L1-AS1B-U-HA-AZ-SJ（124987）公开页明确为 power-to-unlock / spring locking、Unicode actuator teach-in、AS-i 门位置/锁定状态输入位，以及门锁辅助电源必须安全切换；执行器不随本体提供。

## 4. 正文修订

已更新知识页 §7.3、§8.2、§8.4、§10.2、§10.3、§11.4，并新增 §12：

- 明确 ANSI/A3 R15.06-2025 的 Part 1/2 与 ANSI/A3 R15.06-3-2025 Part 3，披露 A3 两张页面的 Part 3 发布状态冲突；
- 披露 ISO/DIS 3691-4 页面 40.60 与 40.99 时间线记录的内部冲突；
- 明确 SICK 量程变体、扫描周期与 response-time formula；
- 明确 G9SE 的响应时间、接通动作时间及非定期自诊断状态下 500 ms 限制；
- 补充 3SK1 Cat. 1 延时关断故障边界和 PSENmlock automatic-reset / emergency-release 组合限制；
- 补充 OS32C 规格页 PTM 6 ms/scan 与手册 PTM-RBM 表值必须区分的配置口径。

## 5. 尚未完成与不予推导

- 未取得/审读 ISO 14119、ISO 13850、ISO 10218、ISO 3691-4、ISO 13849、IEC 62061、ANSI/A3 R15.06 全文。
- 未审查目标国家/地区法规、协调标准和产品分类适用性；OSHA 页面不是各州完整法规清单。
- 未取得目标设备实际订货号、铭牌、固件/配置文件、证书、接线图和安装图；未验证 OSSD、继电器回路、接触器反馈、门锁和控制器组合。
- 未计算真实保护区或停止距离；未做响应时间测量、通道短路/交叉故障/接触器粘连/门锁旁路/失电逃生等故障注入、HIL、现场测试、FAT/SAT 或第三方认证。
- 未根据本轮事实审计修改权利人或许可状态；该资产在逐路径权利登记中的权利人仍为 UNVERIFIED、再分发仍为 UNDETERMINED。

因此，《安全防护器件》仍标记 unaccepted_claim_level_review_pending；本轮仅为公开来源增量审计，不构成器件选型批准、PL/SIL 分配、法规符合性或整机安全验收。
