# 减速器制造商目录参数、寿命模型与蜗轮蜗杆自锁边界增量审计

- 审查日期：2026-11-15
- 资产：knowledge/actuators/减速器.md
- 风险类别：P0 运动执行器 / 机械传动 / 重力负载保持边界
- 审查类型：对 2026-11-05 全文静态边界审查后的制造商目录术语、负载谱算法和自锁边界增量核验
- 结论：完成公开产品资料增量审查；整篇资产仍未完成 claim-level 验收。

## 1. Harmonic Drive CSG-GH/CSF-GH 产品目录

官方 CSG-GH/CSF-GH 目录分别定义：Rated torque 为指定输入转速下允许的连续负载扭矩；Limit for Repeated Peak Torque 与加速/减速阶段由输出惯量产生的重复峰值相关；Limit for Average Torque 是变负载/变输入速度下必须计算并满足的平均扭矩限制；Limit for Momentary Torque 用于碰撞或急停的瞬时事件，发生幅值和频率应尽可能小，且不应出现在正常工作周期。

目录说明齿轮寿命由波发生器轴承寿命决定，并给出 CSG-GH/CSF-GH 系列 L10/L50 参考指标和对应寿命关系。平均负载扭矩在目录选型流程中使用立方加权形式，并另外校核平均/最大输入速度、重复峰值扭矩、瞬时扭矩和冲击次数。该公式只属于该目录定义，不得套用于其他厂商/系列。

目录还说明效率会随减速比、输入速度、负载扭矩、温度和润滑条件变化；输出端交叉滚子轴承的最大力矩、寿命与静态安全系数需要校核；特定垂直安装与持续单向恒载条件需关注润滑问题。

来源：
- Harmonic Drive CSG-GH/CSF-GH official catalog：https://www.harmonicdrive.net/_hd/content/documents/csg-gh-catalog.pdf

## 2. Nabtesco RV-Original 产品指南

Nabtesco 官方 RV 产品指南在 RV-Original 目录中独立列出 Rated torque、Allowable acceleration/deceleration torque、Momentary max. allowable torque、Rated output speed、Duty ratio 100% 下参考允许输出速度、Rated service life、Backlash/Lost motion 和 Torsional rigidity。

指南中的 RV 型号表同时显示不同型号在额定扭矩、加减速扭矩、瞬时最大允许扭矩、允许输出速度和额定寿命上具有不同规格。表格不支持把某一 RV 型号的比例或额定寿命推广至所有型号，更不能跨厂商比较峰值/额定倍数。

来源：
- Nabtesco RV Product Guide：https://precision.nabtesco.com/img/area/leaflet_pdf/en/en_cat_product-guide.pdf

## 3. 蜗轮蜗杆自锁和效率

Norelem 官方蜗轮蜗杆技术资料指出，自锁取决于导程角、齿面状态、滑动速度、润滑和发热，并区分静态与动态自锁；冲击和振动可能妨碍自锁，润滑与负载等因素还会改变滑动行为，因此资料不保证自锁性能。该资料也指出目录运行效率并不直接等于启动效率，因为启动时润滑膜尚未形成。

U.S. Army Corps of Engineers 2025 工程手册独立提示，并非所有蜗轮蜗杆都自锁，并且机电驱动系统中的蜗轮蜗杆自锁特性不能代替制动器。该证据用于说明安全保持边界，不用于具体机器人产品定点选型。

来源：
- Norelem Technical Information for Worm Gears：https://norelem.co.uk/medias/Technischer-Hinweis-Schneckenradsaetze-EN.pdf
- USACE EM 1110-2-2610 (2025)：https://www.publications.usace.army.mil/Portals/76/Publications/EngineerManuals/EM%201110-2-2610_FINAL_18Mar2025.pdf

## 4. 知识页修改

在 knowledge/actuators/减速器.md 新增 §7：
1. 并列区分连续额定、重复峰值、平均负载、瞬时冲击与加减速允许扭矩的制造商定义。
2. 明确 Harmonic Drive 立方加权平均负载公式及寿命模型仅适用于对应系列/目录计算规则，不是通用齿轮箱算法。
3. 明确 Nabtesco RV-Original 目录的额定/加减速/瞬时扭矩与寿命数据绑定型号及目录条件。
4. 增加蜗轮蜗杆动态/静态自锁、润滑/温度/振动影响，以及不得替代机械制动器的安全边界。
5. 补充启动效率、输出交叉滚子轴承外部力矩、静态安全系数和安装方向润滑检查点。

## 5. 未完成与限制

- 没有本项目具体减速器订货号、配置版本、最新受控样本或供应商书面答复；
- 没有本项目完整任务负载谱（连续/加速/减速/保持/碰撞/急停）以及温度、润滑、安装方向和外部径向/轴向/倾覆载荷；
- 没有执行具体减速器平均负载、寿命与输出轴承安全校核，也未验证供应商计算工具；
- 没有进行效率/启动效率、温升、回差、传动误差、刚度、振动、润滑、急停冲击或耐久试验；
- 没有批准任何具体品牌或型号。整篇资产仍为 unaccepted_claim_level_review_pending，权利人仍为 UNVERIFIED、再分发仍为 UNDETERMINED。

**判断：** 本轮补充了制造商参数词典、负载谱计算和蜗轮蜗杆自锁边界，可以帮助防止跨产品/跨厂商错误换算；它不等于完成目标减速器选型、实际寿命验证或整机安全论证。
