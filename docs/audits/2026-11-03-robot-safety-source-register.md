# 机器人硬件与安全专项来源补充台账（2026-11-03）

> 本文件作为既有《链接台账》#159 之后的专项补充记录。条目用于定位制造商/标准组织原始资料，不代表任何产品已完成认证或适合特定项目。正式设计和采购前须按完整型号、版次和目标市场复核。

| ID | 发布方 | 来源 | 支持内容 | 核验状态/边界 |
| --- | --- | --- | --- | --- |
| 160 | ISO | [ISO 13849-1:2023](https://www.iso.org/standard/73481.html) | 安全相关控制系统设计/集成方法；标准本身不指定特定应用的安全功能或 PLr | 官方页面已核对 |
| 161 | ISO | [ISO 13850:2015](https://www.iso.org/standard/59970.html) | 机器急停功能设计原则；当前发布版页面显示 2020 年复审确认 | 官方页面已核对 |
| 162 | ISO | [ISO/WD 13850 第四版](https://www.iso.org/standard/95370.html) | 第四版仍处于 Working Draft；草案不能作为正式发布版引用 | 官方页面已核对，状态快照日期 2026-11-03 |
| 163 | IEC | [IEC 60204-1:2016+A1:2021](https://webstore.iec.ch/en/publication/71256) | 机器电气设备通用要求；覆盖保护联结、过流/短路保护、EMC、STO、急停和控制回路 | 官方页面已核对 |
| 164 | IEC | [IEC 62619:2022](https://webstore.iec.ch/en/publication/64073) | 工业应用二次锂电芯/电池安全要求与试验；官方范围例示 AGV/叉车 | 官方页面已核对 |
| 165 | UNECE | [UN Manual of Tests and Criteria Rev.6 Amendment 1](https://unece.org/DAM/trans/danger/publi/manual/Rev.6/ST-SG-AC10-11-Rev6-Amend1e.pdf) | 38.3.5 测试摘要内容入口；UN 38.3 属运输试验资料，不是整机安全认证 | 官方入口/索引摘要已找到；正式运输前需人工核对当前版次及目标运输规则 |
| 166 | NVIDIA | [Jetson FAQ](https://developer.nvidia.com/embedded/faq) | Jetson Developer Kit 用于开发/测试，不用于生产部署；量产应评估生产模块与载板 | 官方 FAQ 已核对 |
| 167 | Bosch Sensortec | [BMI088 产品页](https://www.bosch-sensortec.com/en/products/motion-sensors/imus/bmi088) · [数据表](https://www.bosch-sensortec.com/media/boschsensortec/downloads/datasheets/bst-bmi088-ds001.pdf) | 仅支持该具体 IMU 型号的接口、量程、带宽和数据率等规格；不同配置下数值不可泛化 | 官方页面与数据表入口已核对 |
| 168 | Analog Devices | [ADIS16470 产品页](https://www.analog.com/en/products/adis16470.html) · [数据表 Rev. C](https://www.analog.com/media/en/technical-documentation/data-sheets/adis16470.pdf) | 仅支持 ADIS16470 具体型号的量程、偏置稳定性、接口与环境规格 | 官方产品页和数据表入口已核对 |

## 使用规则

1. 具体数值进入设计文件前，要记录完整型号、订货号、数据表版次、配置模式、测试条件、访问日期和责任人。
2. 标准网页摘要只帮助判断标准标题、版次、范围和状态，不替代正式标准全文及适用性评估。
3. UN 38.3 的运输测试摘要、工业电池安全试验和机器人整机安全评估属于不同层次，不能相互替代。
4. 厂商宣传页、产品页和数据表之间若存在不一致，应以适用型号的正式数据表、技术说明和供应商书面澄清为准，并保留差异记录。
5. 本补充台账不自动把任何知识页标记为 claim-level review accepted。
