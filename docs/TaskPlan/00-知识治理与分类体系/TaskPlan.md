# 00｜知识治理与分类体系 — 章节任务计划

> 本文件是第 00 章的执行清单。**统一继承仓库根目录 `TaskPlan.md` 的全部 Guide、Limit、任务状态和验收制度；本文件不另设、不复制、不覆盖 Guide/Limit。** 章节特殊约束目前无已批准例外。
>
> 目标知识目录：`docs/、knowledge/maps/、根目录 TaskPlan.md`  
> 依赖章节：全章前置；其他章节的分类、元数据和质量规则均依赖本章  
> 现有基础：已有 README、knowledge/README.md、docs/knowledge-schema.md、迁移映射、术语表和来源台账；待统一审计  
> 初始状态：本计划新建；所有节点尚待按根计划标准执行和验收。

## 1. 本章目标与覆盖范围

建立全库稳定的分类树、文档模板、术语和质量流程；维护机器人行业知识的覆盖地图与缺口清单。

**必须覆盖的知识面：** 知识分类、知识地图/MOC、文件命名、元数据、术语、来源台账、双链、版本与变更、数据质量、内容生命周期、知识检索准备。

**明确边界：** 本章制定内容治理方法，不替代各技术章节的专业事实核验；RAG/向量检索工程在 24 章实施。

## 2. 交付物

- 行业知识分类树和章节边界矩阵
- 统一 Markdown/front matter Schema 与模板
- 术语表、缩写表、来源/引用台账规范
- 知识质量检查清单与可自动化检查规则
- 全库现有内容盘点、重复/死链/孤儿/过期项报告

## 3. 任务节点

### 00-01｜全库资产盘点与基线

- **任务范围：** 遍历仓库现有知识、docs、代码、配置和示例，建立文件到章节的映射。
- **必做：** 记录文件路径、主题、语言、来源、更新时间、已有链接、内容成熟度、可信度和是否存在重复；区分正式知识、地图、台账、历史记录和代码。
- **严格禁止：** 不得依据旧 TaskPlan 统计或文件数量推断已完成；不得删除旧文档或把空目录计入知识覆盖。
- **依赖：** 无。
- **交付物与验收：** 提交可复核的资产清单、章节映射表和缺口报告。
- **状态：** 进行中（已完成资产结构基线、P0 高风险边界定向处理，并对 ROS 2 发行版/计算平台、QoS/实时性/组件组合/中间件，以及市场/人形机器人部分主张开展 P1 官方来源定向复核；全库剩余 P1/P2 资产逐项来源审查、事实适用边界与授权核验仍未完成）

### 00-02｜全行业分类树与章节边界

- **任务范围：** 为 01–25 章建立层级分类、交叉关系和唯一主归属。
- **必做：** 覆盖根计划定义的机器人形态、全生命周期、软硬件栈、行业领域和新兴技术；为容易交叉的主题明确主目录与引用关系。
- **严格禁止：** 不得将某一技术路线当作整个行业；不得无限增加一级目录或制造重复主归属。
- **依赖：** 本章盘点节点完成后执行；具体交叉依赖按根计划第 6 章。
- **交付物与验收：** knowledge/README、maps 和迁移映射能定位每个主题，新增目录有理由和边界。
- **状态：** 未开始（已有内容仅作为盘点输入，未验收不算完成）

### 00-03｜文档 Schema 与标准模板

- **任务范围：** 定义技术文章、型号卡片、标准卡片、BOM 条目、测试报告、项目案例和代码示例模板。
- **必做：** 定义标题、摘要、category、tags、source、版本、日期、适用范围、上下游、来源和待确认字段；兼容现有中文字段并提供迁移规则。
- **严格禁止：** 不得强迫不适用章节填入虚构参数；不得将 YAML 子集解析器误称完整 YAML 规范。
- **依赖：** 本章盘点节点完成后执行；具体交叉依赖按根计划第 6 章。
- **交付物与验收：** 发布模板和 Schema 文档，并用至少 3 种不同类型文档试填验证。
- **状态：** 未开始（已有内容仅作为盘点输入，未验收不算完成）

### 00-04｜来源、术语与版本治理

- **任务范围：** 统一来源台账、术语表、标准/型号版本和历史信息维护机制。
- **必做：** 设计来源可信级别、访问状态、发布日期/访问日期、适用版本、术语别名和弃用标记。
- **严格禁止：** 不得将搜索摘要标成已阅读来源；不得静默改写历史结论或抹去过期版本。
- **依赖：** 本章盘点节点完成后执行；具体交叉依赖按根计划第 6 章。
- **交付物与验收：** 来源记录可回溯到具体文档和事实；术语冲突有统一裁决记录。
- **状态：** 未开始（已有内容仅作为盘点输入，未验收不算完成）

### 00-05｜链接与内容质量审计

- **任务范围：** 制定并实现文件路径、内部链接、外链、重复文档、元数据完整性和孤儿知识检测。
- **必做：** 区分 Obsidian WikiLink、Markdown 相对链接、代码围栏和外部 URL；提供误报处理和人工抽查流程。
- **严格禁止：** 不得把登录限制/反爬错误误判为源内容不存在；不得以自动化通过替代专业内容审查。
- **依赖：** 本章盘点节点完成后执行；具体交叉依赖按根计划第 6 章。
- **交付物与验收：** 可运行检查工具、报告样例和误报处理规则齐全。
- **状态：** 未开始（已有内容仅作为盘点输入，未验收不算完成）

### 00-06｜知识更新与贡献流程

- **任务范围：** 建立新增、更新、复核、废弃、归档和版本发布流程。
- **必做：** 设立来源变更、软件 EOL、标准修订、产品停产、价格变化和重大安全通告的更新触发器。
- **严格禁止：** 不得无审查批量改写章节内容；不得允许无来源匿名事实进入高风险知识页。
- **依赖：** 本章盘点节点完成后执行；具体交叉依赖按根计划第 6 章。
- **交付物与验收：** 贡献流程、审阅清单、更新日志和章节维护规则发布并完成试运行。
- **状态：** 未开始（已有内容仅作为盘点输入，未验收不算完成）



## 4. 本章完成条件

1. 分类树与 01–25 章目标目录一致，主归属和交叉链接清晰。
2. 现有知识已完成盘点、重复与缺口分级，保留原始来源和迁移轨迹。
3. 文档、参数、BOM、标准、代码、项目与测试记录均有可用模板。
4. 链接、术语、元数据和变更质量检查可运行且有人工复核流程。

## 5. 缺口与待确认事项

- 盘点后新增的知识缺口追加到本文件末尾的“补充节点”区，使用不重复的新 ID。
- 遇到数据不可得、标准适用性不明确、厂商资料受限或需要真实设备测试时，记录阻塞原因、影响范围和解除条件，不得猜测补齐。
- 若判断本章确实无法遵守根目录 Guide/Limit，暂停相关节点并先向用户说明冲突及例外建议；未经用户确认不得写入新的章节级 Guide/Limit。

## 6. 本章执行记录（只追加）

| 2026-11-05 | 00-01 | 对 `knowledge/actuators/电机与驱动器.md` 完成 P0 功能安全标准范围增量审查：依据 IEC 官方目录核验 IEC 61800-5-2:2016+AMD1:2026 CSV Edition 2.1（2026-10-30，Valid），补充 PDS(SR) 产品范围、应用危险/风险分析与 SIL 初始分配排除项、被驱动设备/制造过程/信号命令有效性边界，以及低需求模式限制；来源台账#896扩充，基线审计第98节、资产清单同步。未审查标准全文、未核验具体驱动器证书或安全子功能、未进行应用风险评估/故障注入/整机安全验证；资产继续未验收。 | IEC 官方合并版目录及公开范围摘要；基线审计§98 |


| 日期 | 节点 | 记录与证据 |
| --- | --- | --- |
| 2026-11-03 | 00-01 | 基线快照：238 个 Git Tree 条目、171 个文件对象、147 个 Markdown；knowledge/ 110 份 Markdown，docs/TaskPlan 27 份 Markdown。完整结构快照见 docs/audits/2026-11-03-baseline-inventory.md。 |
| 2026-11-03 | 00-01 | 更新资产清单：基线为 244 个 Git Tree 条目、175 个文件对象、151 个 Markdown、112 个 knowledge Markdown。112/112 已完成标题、章节结构和开篇检查；72/112 完成较详细正文结构/片段抽样，40/112 仍未完成全文专业审查。清单见 docs/audits/2026-11-03-knowledge-asset-inventory.csv；所有文件仍待 claim-level 来源核验。 |
| 2026-11-03 | 00-01 | 第一批 P0 定向修订六篇：功能安全、电子电气、电池与电源、安全防护器件、充电系统、底盘与运动机构。移除不适用的通用 PL/Cat、保护区、保险/线径/接地、充电倍率和机械性能经验值；详见审计报告第 14 节。 |
| 2026-11-03 | 00-01 | 第二批 P0 定向修订七篇：电机与驱动器、减速器、IMU、编码器与里程计、LiDAR、深度相机、传感器总览。修正通用过载倍数、减速器寿命/回差范围、IMU 指标混淆、PPR/CPR 换算和未经同工况核验的传感器参数；详见第 15 节。 |
| 2026-11-03 | 00-01 | 第三批 P0 定向处理七项：执行器/机械/电源/安全/传感器目录、LiDAR 集成清单、毫米波雷达与超声波专题。详见第 16 节。资产清单 20/20 个 P0 标记 targeted_review=yes；该标记只表示高风险边界定向处理，不是逐条 claim-level 验收。112/112 全库资产仍未完成 claim-level 验收，00-01 保持进行中。 |
| 2026-11-03 | 00-01 | 基于 main 提交 c00ef1088998c2ac2c2c78778e09f787f64397e4 完成 89 份非 README 知识文件全文结构扫描，另抽查 2 份目录 README；刷新 112 条资产清单当前 Blob SHA/大小，修正 23 条过期 SHA。全文结构扫描不代表 claim-level 审查；详情见基线审计第 17 节。 |
| 2026-11-03 | 00-01 | 完成 ROS 2 发行版生命周期及 Jetson/RK3588 计算平台指标的 P1 官方来源定向复核，修订两篇知识页并补充来源台账 #160–#165；未覆盖两篇文章全部主张，也未进行真实板卡/系统验证，详见基线审计第 18 节。 |
| 2026-11-03 | 00-01 | 对产业链/市场、发展趋势、人形机器人和主要厂商四份 P1 资产开展定向主张审查：用 IFR World Robotics 2026 更新工业/专业服务/全尺寸人形机器人市场口径；依据 IFR 人形定义区分销量、工厂下线和客户现场安装；核验 Tesla Q3 2026、AGIBOT、UBTECH、Unitree、Figure 官方公开资料；将未获同口径证据的 BOM 占比、份额、价格和趋势判断删除或降级。来源台账 #175–#185；基线审计第 23 节。所有四项资产仍待完整 claim-level 审查，不因本批修订而通过验收。 |

| 2026-11-03 | 00-08 | 新增 G0–G11 阶段门评审模板，覆盖阶段输入/输出、需求追踪、跨专业评审、阶段专项检查、风险/偏差、行动项和签署；该节点仍在进行中，完整成果物映射矩阵待补。 |

## 7. 补充节点（只追加）

> 新发现的范围在这里追加，不删除或复用已有节点 ID。新增节点仍必须包含任务范围、必做、严格禁止、依赖、交付物与验收、状态。


### 00-07｜零基础学习路径与能力分级

- **任务范围：** 定义非机器人行业读者的学习入口、先修课程、能力等级、术语解释、练习和自测要求。
- **必做：** 设计从 A0 零基础到 A4 产品化/量产能力的课程地图；为数学、物理、编程、计算机、机械制图、材料、电学和工程沟通提供学习目标、可验证练习和下一步路径；抽查不同章节是否对新手友好。
- **严格禁止：** 不得默认读者已有专业背景；不得只堆资源链接；不得将知识阅读替代危险设备操作培训或专业资格。
- **依赖：** 00-01、00-03；与 12、25 章协作。
- **交付物与验收：** 能力分级矩阵、先修课程地图、学习入口决策树和新手可用性抽查报告。
- **状态：** 进行中（已建立 A0–A4 能力入口和零基础学习文档；完整先修课程、练习/测验与可用性抽查待完成）

### 00-08｜全流程阶段门与跨章节成果物追踪

- **任务范围：** 统一需求、设计、样机、EVT、DVT、PVT、量产、交付、售后等阶段的输入输出和验收口径。
- **必做：** 建立阶段门模板、工程成果物目录、责任角色、评审问题、准入/退出标准；将各交付物映射到 01–25 章节并检查是否存在断链。
- **严格禁止：** 不得把能运行的原型机标记为可量产；不得以文件存在代替内容审核和阶段评审。
- **依赖：** 00-01、00-02、02、18、19、20、22、25。
- **交付物与验收：** 全生命周期阶段门矩阵、交付物追踪矩阵和跨章链路审查报告。
- **状态：** 进行中（已创建覆盖 G0–G11 的阶段门评审记录模板初版；跨章节成果物映射、责任角色和阶段准入/退出证据逐项校验仍待完成）


### 00-09｜零基础友好内容标准与教学质量评审

- **任务范围：** 将根计划 G-21 落地为各知识文章可执行的教学质量标准。
- **必做：** 统一“问题/用途—先修—术语—原理—步骤—计算示例—练习—检查—局限/风险—下一步”的内容顺序；区分入门教学、工程参考、流程 SOP、型号/标准卡片和项目案例；定义 M0–M5 内容成熟度并抽样评估各章节文章。
- **严格禁止：** 不得为所有文章强加同一篇幅；不得以大量术语、公式或外链替代解释；不得把专业资格、安全培训或工厂实践包装成自学即可取得。
- **依赖：** 00-01、00-03、00-07。
- **交付物与验收：** 更新后的 docs/编写规范.md、入门知识模板、成熟度评估表和抽样评审记录。
- **状态：** 进行中（编写规范与零基础教学模板已建立；成熟度抽样审查待完成）

### 00-10｜公开仓库发布与项目资料安全审查

- **任务范围：** 审查公开仓库中的项目案例、路径、日志、配置、代码摘录和外部资料是否适合公开。
- **必做：** 检查绝对本地路径、内部主机/网络信息、客户/个人资料、密钥凭证、未授权项目文件和许可证；对不必要的本地路径用中性占位符替换；保留项目分析价值但避免泄露不必要的内部细节。
- **严格禁止：** 不得因审查而擅自删除用户需要的技术事实；不得把未经确认的项目归属、公司关系或商业状态写成事实。
- **依赖：** 00-01；与根计划 Limit、G-08 代码合规要求协同。
- **交付物与验收：** 公开信息审查报告、敏感路径/数据处理记录、许可证与引用待审项清单。
- **状态：** 进行中（项目案例和首页的绝对本地路径已首轮脱敏；代码/许可证和项目事实授权仍待审查）
| 2026-11-03 | 00-01 | 对 knowledge/software/ROS与ROS2.md 开展 P1 QoS、实时性、Composition/进程内通信、Zenoh RMW、Fast DDS、REP 2000 平台支持和 Noetic EOL 定向复核；纠正 QoS 兼容性示例，删除无依据的 3–5 倍吞吐和固定点云带宽值，补充目标拓扑与负载验证边界。来源台账 #186–#194；基线审计第 24 节。文章及资产清单仍保持未完成全文 claim-level 验收状态。 |


| 2026-11-03 | 00-01 | 对 knowledge/algorithms/卡尔曼滤波.md 开展 P1 状态估计基础算法定向复核：纠正 PF/KF 分类、IMU 预积分与偏置修正描述、VIO 尺度可观性条件、Q/R 调参边界、PF 粒子数/ESS 通用常数及 AMCL odom_alpha 与 EKF Q 的混淆；审计报告第25节。只完成局部主张纠错，全文 claim-level 审核、推导/API/版本/许可证核验及真实传感器验证未完成。 |


| 2026-11-03 | 00-01 | 对 knowledge/algorithms/SLAM总览.md 开展 P1 算法选型与指标主张定向复核：删除无条件 FAST-LIO2/黄金组合推荐和脱离测试口径的精度/成功率阈值；纠正 3DGS 与 NeRF/导航地图的关系；区分 Cartographer upstream 与 ROS fork 状态，补充 slam_toolbox 与 ORB-SLAM3/FAST-LIO2/FAST-LIVO2 官方来源；审计报告第26节。未运行算法、未实机测试、全文 claim-level 验收未完成。 |


| 2026-11-03 | 00-01 | SLAM 总览定向复核的二次一致性检查发现正文仍残留固定 KPI 阈值和旧决策树，已补充替换为有测试口径的指标表和条件化算法选型规则；更新文章日期，并刷新资产 CSV 的 Blob SHA/文件大小。仍未完成全文 claim-level 审查与算法/实机验证。 |


| 2026-11-03 | 00-01 | 对 knowledge/algorithms/多传感器融合定位.md 开展 P1 主张定向复核：按 REP-105 纠正 map/odom/base_link 语义，修订 robot_localization 的 TF 发布和双 EKF 适用边界、重复底层信息/协方差关系、navsat_transform_node 数据流、Nav2 AMCL 生命周期及故障退化建议；来源台账 #255–#260，审计报告第27节。未运行 ROS 节点、未使用目标传感器数据、全文 claim-level 验收未完成。 |


| 2026-11-03 | 00-01 | 对 knowledge/algorithms/激光SLAM.md 开展 P1 算法/兼容性/许可证定向复核：区分 LiDAR odometry、LIO、SLAM 和已知地图定位；纠正 LeGO-LOAM 传感器假设、LIO-SAM 双因子图/ROS1与ROS2分支、FAST-LIO2与Point-LIO仓库环境；删除固定时间/外参/体素/地图分辨率阈值；登记 FAST-LIO LICENSE 与 package.xml 冲突及 LIO-SAM package.xml TODO。来源台账 #261–#274，审计报告第28节。未运行代码或实机测试，全文 claim-level 验收未完成。 |


| 2026-11-03 | 00-01 | 对 knowledge/algorithms/视觉SLAM.md 开展 P1 视觉 SLAM/VIO 定向复核：区分单目/双目/RGB-D/VIO 尺度约束及初始化可观性；纠正直接法弱纹理、VINS-Fusion 固定流水线细节、MSCKF/VIO 与完整 SLAM 能力边界、RTAB-Map RGB-only/metric mapping 边界和 stella_vslam IMU 开发状态；核验 ROS 兼容与许可证依赖。来源台账 #275–#288，审计报告第29节。未采集目标设备数据、未构建运行算法，全文 claim-level 验收未完成。 |


| 2026-11-03 | 00-01 | 对 knowledge/algorithms/学习型机器人算法.md 开展 P1 RL/IL/VLA 与工具链主张定向复核：删除通用训练步数/并行环境/数据体量/成功率和行业趋势数字；纠正 Diffusion Policy/ACT/VLA 分类；更新 OpenVLA、π₀/openpi、GR00T N1.7、Figure Helix/Helix 02 架构和许可差异；补充模型部署、数据质量与安全监督边界。来源台账 #289–#305，审计报告第30节。未运行训练/模型或实机系统，全文 claim-level 验收未完成。 |


| 2026-11-03 | 00-01 | 对 knowledge/algorithms/路径规划算法.md 开展 P1 图搜索、采样规划、Nav2 Smac、路径/轨迹与覆盖规划主张定向复核：移除固定速度倍数、Weighted A* 默认权重、覆盖重叠/覆盖率门槛和“99% AMR 默认方案”；补充 A* 理论边界、Hybrid-A*/State Lattice/OMPL 前提和 nav_msgs/Path 接口。来源台账 #306–#310，审计报告第31节。用户于2026-11-03确认相关测试项已执行完成；测试报告/原始数据待归档与证据核对，资产验收仍未完成。 |
| 2026-11-03 | 00-01 | 对 knowledge/algorithms/局部规划与避障.md 开展 P1 Nav2 局部控制器/Costmap/安全制动边界主张定向复核：纠正 MPPI CPU-only 实现、RPP 碰撞检查能力、TEB ROS1 catkin 接口；删除通用频率/时延/行人距离和让行规则，厘清 inflation、costmap filters 与安全保护功能边界。来源台账 #311–#319，审计报告第32节。用户于2026-11-03确认相关测试项已执行完成；测试报告/原始日志待归档与证据核对，资产验收仍未完成。 |


| 2026-11-03 | 00-01 | 对 knowledge/algorithms/多机协同与调度算法.md 开展 P1 任务分配、VRP、MAPF、车队交通与安全资源预约定向复核：拆分 assignment/VRP/MAPF/traffic reservation；纠正 CBBA 收敛假设及 CBS/ECBS/LaCAM/LaCAM* 性质；补充运动学/footprint约束、资源真实释放规则与 Open-RMF Traffic Schedule/Negotiation/Fleet Adapter；删除无依据的车队规模、批处理提效、KPI、SOC 与充电排队数字。来源台账 #320–#334，审计报告第33节。未连接真实车队/设施或运行多机算法，全文 claim-level 验收未完成。 |


| 2026-11-03 | 00-01 | 根据用户明确反馈，将第31节路径规划与第32节局部规划/避障此前列出的测试执行状态更新为“用户确认已完成”；未收到原始测试报告/数值，不补填性能结果；资产验收状态仍保持待主张级证据核对。基线审计报告第34节，CSV scope同步更新。 |
| 2026-11-03 | 00-01 | 对 knowledge/algorithms/视觉感知算法.md 开展 P1 感知任务边界、检测/分割/跟踪/3D 点云/深度/VLM、端侧部署、时序融合、评测与模型许可定向复核：清除未绑定测试条件的 FPS/功耗/近场/同步数字；纠正 CLIP/SAM2/Depth Anything/DROID-SLAM、OpenPCDet/Patchwork++ 职责边界；区分 Ultralytics 授权和 Depth Anything V2 checkpoint 许可。来源台账 #335–#353，审计报告第35节。未采集目标机器人数据或测量部署性能，全文 claim-level 验收未完成。 |

| 2026-11-03 | 00-01 | 对《多机协同与调度算法》完成 P1 MRTA/VRP/MAPF/Open-RMF 定向审计（#320–#334，审计第33节）；对《视觉感知算法》完成 P1 任务分类、部署指标与模型许可定向审计（#335–#353，审计第35节）。两个页面均已同步资产清单，未运行目标车队/传感器或目标部署硬件，验收仍待实机/证据。 |


| 2026-11-03 | 00-01 | 对 knowledge/algorithms/轨迹优化与运动控制.md 开展 P1 路径跟踪、轨迹时间参数化、MPC/求解器、ros2_control 实时接口和足式控制主张定向复核：移除通用环路频率、加速度/预瞄/看门狗数字，澄清 OSQP 凸 QP 与 acados 非线性 OCP/NLP 边界，补充轨迹平滑后的碰撞/可跟踪性复检。来源台账 #354–#362，审计报告第36节。未在目标底盘/机械臂/足式平台运行控制器，实机性能与安全验收未完成。 |


| 2026-11-03 | 00-01 | 对 knowledge/algorithms/README.md 完成 P1 索引结构与导航完整性复核：按感知定位建图、规划轨迹控制、多机器人/学习型算法分组；补充算法地图、导航流程、Nav2、性能指标和功能安全入口；明确索引只负责导航，技术主张以专题正文/证据为准。审计报告第37节，资产 CSV 更新。 |


| 2026-11-03 | 00-01 | 对 knowledge/software/Nav2导航框架.md 开展 P1 官方架构/插件/BT/Costmap/Lifecycle/版本与许可证边界定向复核：拆分实际核心、可选服务器和插件，移除固定“四大服务器”、TEB 原生插件、统一恢复顺序和参数/频率，补充 Lifecycle Manager node_names、Costmap layer/filter 区分、版本锁定与多许可证边界。来源台账 #363–#378，审计报告第38节。未在目标机器人运行 Nav2 bringup/BT/插件，全文 claim-level 验收未完成。 |


| 2026-11-03 | 00-01 | 对 knowledge/software/实时系统与嵌入式.md 开展 P1 实时调度、PREEMPT_RT、Ubuntu Real-time、RTOS/功能安全、总线和 watchdog 主张定向复核：删除通用控制频率/抖动/WCET/急停/心跳数字；纠正 Ubuntu 实时内核包命名、Zephyr Safety 声明边界、FreeRTOS kernel 与 demo 许可证差异；区分 CAN FD、EtherCAT DC 同步与端到端控制延迟；补充 cyclictest/rtla/trace 工具和代表性负载验证。来源台账 #379–#390，审计报告第39节。未在目标硬件开展实时基准/总线负载/故障注入，全文 claim-level 验收未完成。 |


| 2026-11-03 | 00-01 | 对 knowledge/software/advanced-topics/DDS专题.md 开展 P1 ROS 2 通信栈主张定向复核：拆分 DDS/RTPS/RMW/传输，更新 DDS vendor 与 Zenoh RMW/bridge 边界，补齐 Request-vs-Offered QoS 兼容性、SPDP/SEDP/Discovery Server/Cyclone peer 与网卡配置，区分 SHM/Data Sharing/intra-process，清除固定 socket buffer 和跨网段选型口号，并分别记录 middleware/RMW 许可证。来源台账 #391–#407，审计报告第40节。未在目标发行版/硬件/网络拓扑执行互操作或端到端性能测试，全文 claim-level 验收未完成。 |


| 2026-11-03 | 00-01 | 对 knowledge/software/advanced-topics/ROS1与迁移.md 开展 P1 Noetic 生命周期、Ubuntu Focal ESM、ros1_bridge 发行版兼容、自定义接口编译/映射、dynamic_bridge、双栈网络/时间与行动接口迁移定向复核：纠正 Ubuntu 24.04 安装 Noetic bridge 的错误示例，明确三工作区自定义消息构建、编译时类型支持、YAML mapping、Action/QoS 与 ROS1/ROS2 两侧运行依赖；删除无依据迁移工时数字及 Docker 化等同安全说法。来源台账 #408–#413，审计报告第41节。未构建本项目 bridge 或逐接口进行互操作/时延/故障测试，全文 claim-level 验收未完成。 |


| 2026-11-03 | 00-01 | 对 knowledge/ecosystem/标准与法规.md 开展 P1 标准生命周期与地区适用边界定向审计：区分法规/IS/TS/草案/行业建议/认证评估；更新 ISO 3691-4、ISO 10218、TS 15066、ISO 13482 FDIS、ISO 12100/13849/13850、IEC 60204/62619，新增 ISO 21423:2026、VDA 5050 3.0.0、GB/T10827.4-2026、EU Machinery Regulation 与 AI Act 分期日期；纠正 CE、医疗器械路径、MQTT/ISO 20922 和割草机专用标准边界。来源台账 #414–#439，审计报告第42节。未完成具体产品/市场适用性矩阵、正式标准全文条款审查或认证路径确认，全文 claim-level 验收未完成。 |


| 2026-11-03 | 00-01 | 对 knowledge/robots/工业机器人.md 开展 P1 定义/构型/选型指标与市场统计主张定向复核：按 IFR/ISO 8373:2021 补充三轴及以上、可编程、多用途和固定/移动平台定义；将协作机器人与运动学构型分类拆分；删除通用负载/速度/节拍/精度/IP/洁净等级和成本占比数字；补充腕部惯量/重心/负载图、ISO 9283 测试口径、ISO 10218 本体/集成边界，并更新 IFR World Robotics 2026 的 2025 年安装/存量数据。来源台账 #440–#446，审计报告第43节。未开展目标型号性能、payload、节拍、风险评估或整机安全实测，全文 claim-level 验收未完成。 |


| 2026-11-04 | 00-01 | 对 knowledge/robots/协作机器人.md 开展 P1 协作应用安全边界与型号参数定向复核：明确 Cobot 产品/本体不等于现场应用免围栏；梳理 SMS、手引导、SSM、PFL 的机制与组合语境；按完整机器人—工具—工件—人员任务识别风险，删除无依据跨品牌参数快照、6 秒节拍公式、普适 Cat.3/PL d、品牌化力矩传感路线与“零力/碰撞回弹”安全暗示；补充 UR20 单型号规格边界、ISO 10218:2025/ISO/TS 15066 生命周期、ISO 9283 和 ROS 2/MoveIt 软件边界。来源台账 #447–#454，基线审计第44节。未开展目标工位风险评估、SSM/PFL 安全性能测试或现场 SAT，全文 claim-level 验收未完成。 |


| 2026-11-04 | 00-01 | 对 knowledge/robots/移动机器人.md 开展 P1 AGV/AMR/IGV 分类、导航技术、整机选型和工业移动机器人安全主张定向复核：按 IFR/ISO 8373 修订移动机器人定义及术语边界；删除跨车型负载/速度/精度/电池/充电“典型值”与无依据市场趋势；补充车辆/能源/导航/安全/车队/设施架构，区分导航避障与安全相关保护；核验 ISO 3691-4:2023 与 DIS 第三版阶段、ANSI/A3 R15.08-1/-2/-3 的本体/系统/用户边界；明确 VDA 5050/ISO 21423 仅用于接口互操作；修订 LinORobot2/TurtleBot3 的教育/原型用途与版本边界。来源台账 #455–#463，审计报告第45节。未开展目标车辆、载荷、现场路线、制动/人员检测、续航/车队或 SAT 测试，全文 claim-level 验收未完成。 |


| 2026-11-04 | 00-01 | 对 knowledge/robots/仓储物流机器人.md 开展 P1 仓储自动化设备谱系、吞吐量、软件架构和安全边界定向复核：拆分地面 AMR/AGV、货架到人、料箱到人、无人叉车、AS/RS、固定输送/分拣及固定机械臂单元；明确 AutoStore 为网格式 AS/RS，机器人沿 Grid 顶部轨道运行；删除未经证实的市场占比、跨型号参数、单站节拍乘站数、固定人效/车队拥堵阈值和充电桩配比；区分 WMS/WES/WCS/RCS/RMS/PLC/安全控制职责与 VDA 5050 接口边界；补充瓶颈/排队建模、FAT/SAT、EN 528、OSHA 1910.178/1910.147 适用范围。来源台账 #464–#471，审计报告第46节。未获取目标仓库数据、未完成吞吐仿真/设施规模设计、未做现场安全/消防风险评估、设备联调或 FAT/SAT，全文 claim-level 验收未完成。 |


| 2026-11-04 | 00-01 | 对 knowledge/robots/医疗机器人.md 开展 P1 医疗器械预期用途/分类、临床证据、国际监管路径、产品性能口径和专用标准定向复核：区分手术/骨科导航/介入/康复/医院物流/环境消毒，删除“医疗机器人统一三类、注册 3–5 年、临床试验必做”的泛化说法；按 NMPA 第33–36条说明临床评价可基于同品种临床数据或临床试验并存在豁免条件；核验 FDA 510(k)/De Novo/PMA、K242427 示例与 2026 RASD 草案、EU MDR Rule 9/11；删除无条件 DOF/精度/缩放/延迟/消毒率/外骨骼参数；新增 YY 9706.277/278 与 YY/T 1941/1901/1992/1993/1994 实施状态、IEC 80601-2-77、ISO 14971、IEC 62304/62366/81001-5-1；修正 dVRK/CISST 许可证边界。来源台账 #472–#496，审计报告第47节。未开展具体产品分类/注册评估、目标系统测试、非临床/临床试验、风险/可用性/网络安全验证或全部依赖法律审查，全文 claim-level 验收未完成。 |


| 2026-11-04 | 00-01 | 对 knowledge/robots/服务机器人.md 开展 P1 服务机器人定义/分类、IFR 市场统计、应用边界、社交导航、性能口径、安全隐私和部署流程定向复核：依据 ISO 8373:2021/IFR 区分服务/工业/医疗机器人及专业/消费服务机器人；更新 IFR World Robotics 2026 的 2025 年专业服务机器人市场快照；删除无来源的配送类通用参数、社交距离、乘梯协议、现场问题占比、租金与回本周期断言；补充 ODD、现场集成、任务指标和适用标准边界。更新资产 CSV；仅为公开资料定向审查，全文 claim-level 验收、具体产品测试和现场风险评估未完成。 |


| 2026-11-04 | 00-01 | 对 knowledge/robots/清洁机器人.md 开展 P1 家用/商用分类、IFR 市场统计口径、清洁机理、覆盖路径、清洁效果指标、型号规格和安全标准定向复核：纠正消费服务机器人总量与扫地机器人销量混淆；删除无来源的通用电池容量、续航、越障、爬坡、效率、覆盖率、噪声和清洁压力数字；以 Gaussian Scrubber 50/Tennant T16AMR 官方页面作型号级规格示例；核验 IEC 60335-2-67/-2-72 与 ISO/FDIS 13482 状态；删除内部工作区绝对路径。更新资产 CSV；全文 claim-level 验收、实机测试和现场风险评估未完成。 |


| 2026-11-04 | 00-01 | 对 knowledge/robots/特种机器人.md 开展 P1 特种机器人定义/分类、危险环境应用、操控自主等级、防爆与整机认证边界、应急响应能力测试、水下 ROV/AUV 区分和标准适用性定向复核：将“特种机器人”重构为跨平台应用集合；删除无可靠来源的通用耐温、防爆标志、热像/气体检测精度、负载/续航/定位和市场规模数字；区分 ATEX 指令与 IECEx 合格评定体系，补充 ASTM E2521-26/NIST 任务导向测试、ISO/DIS 8373 草案状态及 ISO 10218-2 排除范围。更新资产 CSV；全文 claim-level 审查、具体产品测试和现场危险评估未完成。 |


| 2026-11-04 | 00-01 | 对 knowledge/robots/足式与无人机.md 开展 P1 足式形态/自由度、步态控制与状态估计、学习型控制/Sim2Real、型号参数、UAS 架构、PX4/ArduPilot/Pixhawk 层级与许可证、failsafe、飞行法规和标准状态定向复核：删除通用 DoF、控制频率、MPC 时域、状态漂移、关节扭矩密度、负载/续航/爬坡和无人机 RTK/链路数字；保留 Spot、Go2、Matrice 350 RTK 型号级资料并注明口径，记录 Go2 官方页速度描述冲突；核验 ISO 21384-3:2026、ISO 23665:2026、FAA Remote ID/Part 107 与 EASA Open Category。更新资产 CSV；未进行目标足式设备测试、飞行测试或适用市场法规评审，全文 claim-level 验收未完成。 |


| 2026-11-04 | 00-01 | 对 knowledge/ecosystem/manufacturers/硬件厂商资源汇总.md 开展 P1 厂商资源与型号/版本边界定向审查：核验 SLAMTEC、Livox、Hesai、RealSense、Orbbec、Stereolabs、Bosch、ADI、SICK、OMRON、Oriental Motor、Inovance、Harmonic Drive、Nabtesco、EVE、MiR、Hikrobot、NVIDIA、Rockchip、Raspberry Pi 的官方产品/下载/生命周期入口；修订 SICK TiM571 官方数据表可访问状态，补充 S300 至 2026-11-30 的替代窗口、Jetson Orin 供货周期、CM4/CM5 生命周期及 JetPack 当前版本；删除跨型号聚合参数、未经核验价格和“全部链接已验证”概括。新增链接台账 #497–#520；所有价格/交期、精确 SKU 和供应商资格仍待独立核验。 |


| 2026-11-04 | 00-01 | 对 knowledge/ecosystem/主要厂商.md 开展 P1 厂商产品线、并购/控制权变化与商业化证据定向复核：补充 ABB、FANUC、KUKA、Yaskawa、Universal Robots 工业/协作产品线；Geek+、Quicktron、Hai Robotics、MiR、Hikrobot、ForwardX 的移动/仓储产品线；Gaussian/Tennant 清洁机器人入口；Tesla、Figure、Unitree、AGIBOT、UBTECH 人形机器人状态。将产品目录、厂商自报下线/产能、客户到场/案例和独立部署证据分开；记录 ABB–SoftBank 交易交割未由已检查页面确认、AGIBOT 15,000 台为机器人组合下线数、Figure 02/03 案例归属差异、Tesla 产线启动未披露交付量。来源台账 #521–#540，资产 CSV 更新 Blob SHA/大小；未完成全文逐条 claim-level 验收、所有厂商逐型号资料审查、供应商尽调或采购交付验证。 |


| 2026-11-04 | 00-01 | 新增 knowledge/ecosystem/开源项目与工具链.md，建立代表性机器人软件生态索引：覆盖 ROS 2/Nav2/MoveIt/ros2_control、Gazebo/Isaac、SLAM/轨迹评测、OMPL、PX4/ArduPilot、LeRobot/GR00T；记录版本快照、发行版支持、许可证粒度、维护状态和工程使用边界，并链接至技术章节。更新 ecosystem README、资产 CSV 与链接台账 #541–#562。该索引属于 P1 结构/来源定向审查，尚未形成全依赖 SBOM/完整许可证审计，也未完成目标硬件构建、运行、实时性能/安全测试或全文 claim-level 验收。 |


| 2026-11-04 | 00-01 | 扩展机器人开源资产索引并新增 knowledge/ecosystem/知识生态兼容矩阵.md：补充 Ouster/Livox/RealSense/DepthAI 驱动、robot_localization、launch_testing、rosbag2、ros2_tracing、industrial_ci、micro-ROS、ROS 2 CANopen、open62541；按 Humble/Jazzy/Kilted/Lyrical 与 Gazebo 官方配对、驱动、测试工具及工业通信条目建立静态兼容证据矩阵。修正兼容状态语义，区分 ROS Index 二进制发布、源码构建入口、上游限制/开发中和目标硬件验证；记录 Livox Driver 2 不建议直接量产、CANopen 栈尚未生产就绪、RealSense SDK/固件需跟 wrapper 配套。新增来源台账 #563–#580，更新生态 README 和资产 CSV。尚未完成全依赖 SBOM、逐包许可证法律审查、完整目标硬件构建/长稳/性能/安全测试，00-01 继续进行中。 |

| 2026-11-04 | 00-01 | 继续扩展开源软件生态索引与兼容矩阵：加入 MoveIt Servo 机械臂伺服组件、Velodyne 与 Hesai LiDAR ROS 2 驱动，按证据区分 ROS Index 二进制发行、仓库稳定分支和厂商源码构建入口；对 VDA5050 Connector（Galactic/2022 年旧记录）及 ROS-Industrial industrial_core（ROS 1 历史项目）标注维护风险，避免作为当前 ROS 2 产品基线。同步资产清单和链接台账 #581–#590。仍未完成全依赖 SBOM/许可证法律审查、目标机器人/传感器实机验证、硬实时/安全验收及全文 claim-level 验收；00-01 继续进行中。 |

| 2026-11-04 | 00-01 | 继续扩展工业机器人开源生态与静态兼容矩阵：增加 Basler pylon、Zivid、SICK 工业视觉/LiDAR 驱动及各自 SDK、固件、发行版和维护边界；增加 IgH EtherCAT Master 与 SOEM，区分源代码 GPL 许可、EtherCAT 技术/商标工业产权及 SOEM v2.0.0 商业双许可；补充 Open-RMF fleet adapter 的 ROS Index 多发行版记录与总览 README 差异，并更新 VDA 5050 v3.0.0 协议版本、MQTT/JSON 和安全配置边界。来源链接台账 #591–#607。仍未完成完整 SBOM、逐依赖许可证法律审查、目标相机/雷达/总线/车队实测、实时性能/安全验收及全文 claim-level 审查，00-01 继续进行中。 |

| 2026-11-04 | 00-01 | 继续扩展产业生态软件索引并建立集成关系图：新增 Beremiz PLC IDE/runtime（分组件许可与未加密 ERPC 边界）、ethercat_driver_ros2（Apache-2.0、ros2_control Hardware Interface、Jazzy/Humble 文档冲突）、industrial_calibration 核心与 ROS 2 wrapper（RGB/点云/TF 手眼数据采集）、camera_calibration（单/双目内参）、robot_calibration（相机/关节偏置/移动底盘几何），并将 moveit_calibration 标为 ROS 1 历史项目。新增集成图和阶段门，明确 PLC 协议桥、EtherCAT master 唯一所有者、标定结果独立验证及安全回路责任。来源台账 #608–#621。仍未完成 PLC/驱动实际构建、硬件在环/现场总线、相机标定与手眼精度、目标机器人性能/安全测试、全依赖 SBOM/许可证法律审查及全文 claim-level 验收；00-01 继续进行中。 |
| 2026-11-04 | 00-01 | 扩展机器人产业软件生态的 PLC/ROS 2 协议桥主张审查：新增 ros2_opc_ua（Jazzy+ OPC UA Client 型 ros2_control SystemInterface，但示例能力有限）、ros2_modbus（Modbus TCP I/O topic，未明确发行版矩阵）和 ros2-opcua（实验性 PubSub hybrid node）；建立兼容状态与产品级协议桥专项验收清单，要求 ICD、寄存器/NodeId 映射、读写权限、质量位/时间戳、超时/重连、幂等性及故障注入证据。来源台账 #622–#624。仅静态资料审查，未连接 PLC 或执行互操作测试；00-01 继续进行中。 |
| 2026-11-04 | 00-01 | 扩展工业 PLC 厂商与 ROS 2 连接生态的主张级证据：Beckhoff ADS ROS 2 hardware interface（Jazzy ROS Index 1.0.0）与官方 ADS Linux 客户端库；Siemens SIMATIC/Industrial Edge OPC UA/S7 connectors（区分厂商 Edge 数据采集与 ROS driver，并记录匿名无安全 OPC UA 仅适用于测试）；CODESYS OPC UA Server/Client/PubSub、EtherCAT/Modbus/CANopen 能力（具体依赖 runtime/设备/license）；ros2_medkit_opcua 诊断插件（SOVD/REST，不作实时运动控制）。更新兼容矩阵并新增产品级 PLC 型号/固件/runtime/权限/周期/断线恢复验证边界。来源台账 #625–#631。静态审查，未进行 PLC 实物互操作/安全测试；00-01 继续进行中。 |
| 2026-11-04 | 00-01 | 将 PLC—ROS 2 接口控制文件（ICD）模板纳入治理交付，统一数据点映射、命令语义、协议安全、时序/故障测试和证据签署字段；更新开源生态索引、兼容矩阵及资产清单。模板属于可复用工程骨架，不视为某 PLC 型号接口已经定义或验收；未完成实机互操作、HIL/FAT/SAT、安全验证、完整 SBOM/许可证法律审查及全库 claim-level 验收，00-01 继续进行中。 | ROS 2/Beckhoff/Siemens 官方接口文档；静态设计与仓库结构审查 |
| 2026-11-04 | 00-01 | 建立软件供应链初始审计：核对 Python 工具包项目元数据、声明式 runtime/build/dev 依赖、CI Python 矩阵、GitHub Actions 标签与固定 commit 的外部测试源码；确认当前未记录解析后的完整依赖闭包/锁文件，不能将生态项目索引视为实际安装依赖。新增软件依赖清单 CSV、CycloneDX 1.7 生成策略与风险审计报告；链接台账 #632–#635。静态审查，未执行 pip 安装/构建/测试、未生成或验证 SBOM、未做 CVE/许可证法律审查；产品级 ROS/PLC/硬件依赖仍待确定，00-01 继续进行中。 | 根 pyproject.toml、CI workflow、Ecma ECMA-424、CycloneDX Python 工具、GitHub Actions Secure Use、OMG SPDX 3.0 |

| 2026-11-04 | 00-01 | 新增 ROS 2 机器人产品级 SBOM 采集模板及空白 CSV，覆盖 package.xml/rosdep、ROS workspace overlay、OS/语言依赖、容器 digest、GPU/CUDA、BSP/内核、MCU/传感器/FPGA 固件、厂商 SDK 与 PLC runtime；强调生态候选、声明依赖和产品实际部署组件分层，要求源码 commit/制品 hash/许可证证据可追溯。更新审计 README、开源生态索引、兼容矩阵、链接台账 #636–#638 与资产清单。仅建立模板，未指定目标机器人配置、未从设备/镜像采集、未生成产品 SBOM/漏洞扫描或法律审查；00-01 继续进行中。 | ROS REP-140、ROS 2 build system 与 package development 官方文档；静态模板设计 |

| 2026-11-04 | 00-01 | 更新 CI：新增独立 Python SBOM job，分别在 runtime 与 development venv 中生成并校验 CycloneDX 1.7，隔离 SBOM generator 环境，归档环境 freeze 清单与 SHA256SUMS，上传 30 天 artifact；checkout/setup-python/upload-artifact 均由官方 tag 当前解析到的完整 commit SHA 固定。新增 Python SBOM CI 流水线审计记录，更新依赖清单与基线风险状态，链接台账 #639。配置已静态复核，首次 Actions 执行和 artifact 复核待完成；未完成 CVE/法律审查和产品级 ROS/PLC/硬件 BOM，00-01 继续进行中。 | CycloneDX Python 官方 usage/release、GitHub 官方 Actions refs；CI 配置静态审查 |

| 2026-11-04 | 00-01 | Python SBOM CI 首次真实运行成功：GitHub Actions run #515 的 Python 3.10/3.11/3.12 测试矩阵全部通过；Python 3.12 runtime 与 development 两个隔离环境生成 CycloneDX 1.7 BOM，工具内校验成功并上传 artifact #13295617233。下载后复核 JSON 结构/组件数/依赖 entries，runtime 1/2、development 8/9；5 项 SHA256SUMS 全部通过。SBOM-003 仅对仓库 Python runtime/dev 自动生成范围关闭；未覆盖 ROS/系统包/容器/GPU/BSP/固件/PLC/厂商 SDK，传递依赖未 hash-lock，CVE/许可证法律审查未完成，00-01 继续进行中。 | GitHub Actions run #515 与 artifact 下载；CycloneDX 1.7 JSON 解析和 SHA-256 核验 |

| 2026-11-04 | 00-01 | 对 CI 使用的 rustypot STS3215 源文件增加来源完整性证据：固定上游 commit `7aa85e13143594ea4fd4ed9f29e3e29d39b5de85`，读取 7,434-byte 源文件并计算 SHA-256 `4dbb829228d13492e7dcf80bfbd3d48642a9bbc58c8158e6bdcec1cc35811fa7`；每个 Python 版本 CI 下载后先执行 sha256sum --check --strict，再运行寄存器定义审计。核对相同 commit 根 LICENSE 声明 Apache-2.0、commit signature verification 为 verified；新增来源完整性审计报告、依赖清单更新、链接台账 #640–#641 和资产清单。SBOM-004 的哈希/来源快照部分完成，但许可证适用范围/NOTICE/贡献者及再分发法律审查仍待完成；未完成 Python 依赖锁定、CVE/VEX 或产品级 BOM，00-01 继续进行中。 | 固定 commit raw 源文件、LICENSE、GitHub commit verification；CI 摘要校验配置 |

| 2026-11-04 | 00-01 | 外部源码 SHA-256 校验已在真实 CI 通过：run #534 的 Python 3.10/3.11/3.12 三个测试 job 均成功执行 sha256sum --check --strict，后续 STS3215 寄存器审计与 pytest 通过，SBOM job 也成功。审计记录透明保留 run #528/#533 中 checksum 行格式和临时路径引号导致的失败，以及双引号修正后的通过证据。该结果只验证固定的单一源文件完整性，不等于许可证法律审查或产品 SBOM；00-01 继续进行中。 | GitHub Actions run #534，三个 matrix job 的 checksum step success |

| 2026-11-04 | 00-01 | Python 项目 runtime/dev 依赖锁定已实际落地：uv 0.13.7 在 CI bootstrap run #548 生成根目录 uv.lock（11 个 package 项、Python >=3.10、PyPI artifact SHA-256），锁文件已提交；pyproject.toml 限定 uv required-version。CI run #551 的 Python 3.10/3.11/3.12 均通过 uv sync --locked --extra dev、ruff、rustypot 源码摘要校验和 pytest；SBOM job 使用锁定 runtime/dev 环境生成 CycloneDX 1.7。下载 artifact #13296277606 后，runtime 1 component/2 dependency entries，dev 7/8，JSON 可解析且 5 项 SHA256SUMS 全通过。SBOM-001 对项目 runtime/dev 范围关闭；build-system、generator 工具链、CVE/许可证法律审查及产品级 BOM 仍待处理，00-01 继续进行中。 | GitHub Actions run #548/#551、uv.lock、artifact #13296277606 下载复核 |

| 2026-11-04 | 00-01 | SBOM generator 传递依赖完成独立哈希锁定：新增 requirements-sbom-tools.in/.txt，uv 0.13.7 通过 `uv pip compile --generate-hashes` 生成 34 个工具包的版本与 SHA-256；CI 使用无 pip 初始环境，再由 `uv pip sync --require-hashes` 安装。run #566 三版本测试、runtime/dev locked sync、generator 哈希安装、CycloneDX 1.7 生成校验和 artifact 上传全部通过；下载 artifact #13296392548，runtime 1/2、dev 7/8，5 项 SHA256SUMS 通过。新增工具链锁定审计报告，更新供应链基线、依赖清单、审计 README、链接台账 #644–#645 和资产清单。PEP 517 build isolation setuptools/wheel 仍未锁定，CVE/VEX/法律审查与产品级 BOM 未完成，00-01 继续进行中。 | uv pip compile 官方文档、pip secure installs；GitHub Actions run #566 与 artifact 复核 |

| 2026-11-04 | 00-01 | PEP 517 build isolation 依赖哈希锁定已落地：requirements-build-tools.in/.txt 经 uv 0.13.7 生成，锁定 setuptools 84.2.1、wheel 0.48.0、transitive packaging 26.3，6 个 distribution SHA-256；pyproject.toml 配置 build-constraint-dependencies 与 require-build-hashes=true，uv.lock 已包含哈希约束。CI run #585 在 Python 3.10/3.11/3.12 均通过 `uv build --require-build-hashes`、lint、pytest；SBOM job 成功。Artifact #13298086142 下载后两份 CycloneDX 1.7 JSON 可解析，5 项 SHA256SUMS 全通过。SBOM-008 在当前项目 build-system 范围关闭；uv 功能为实验性，升级时需复验。CVE/VEX、许可证法律审查与产品级 BOM 未完成，00-01 继续进行中。 | uv build constraints 官方文档；GitHub Actions run #585、artifact 下载校验 |

| 2026-11-05 | 00-01 | 对资产清单中此前仅刷新 Git 元数据的 8 份知识域 README 完成全文结构/导航边界抽查（执行器、机械、电源、安全、传感器、厂商资源、机器人分类、软件高级专题）。未发现需立即修正的通用工程阈值或安全保证；P0 README 均保留型号/工况/风险评估边界。该检查不等于链接目标解析或技术文章主张级审查；8 项资产仍保持未验收。详见基线审计第48节。 | README 全文抽查；资产清单同步 |

| 2026-11-05 | 00-01 | 全文审查P0安全防护器件、功能安全体系两篇文章，覆盖安全器件/普通传感器边界、PL/PLr/SIL、急停/STO/能源隔离、停止距离简化模型及验证成果物。未发现需立即修正的明显通用安全保证；标准版本、逐型号证书和目标产品PLr/制动测试仍需独立核验。详见基线审计第49节；不等于合规或产品验证。 | P0安全技术文章全文审查 |

| 2026-11-05 | 00-01 | 完成减速器、电机与驱动器、电池与电源三篇P0文章全文审查；覆盖扭矩/功率近似关系、任务谱、热/惯量/效率、BMS职责、IEC 62619与UN 38.3边界。新增IEC 61800-5-2:2016+AMD1:2026（2026-10-30发布）现行目录证据#896并更新驱动文章。未完成标准全文/国家差异、具体型号证书和产品实测验证；三项资产保持未验收。详见基线审计第50节。 | 文章全文审查；IEC/UNECE官方目录核对 |

| 2026-11-05 | 00-01 | 完成底盘与运动机构、充电桩与自动充电、IMU、激光雷达、编码器与里程计五篇P0文章全文主张边界审查。差速运动学/里程计/充电估算关系均保留适用假设；普通LiDAR与安全扫描仪、SOC调度与充电许可边界清晰。新增ISO 3691-4:2023现行版、ISO/DIS 3691-4第三版草案状态及IEC 60204-1:2016+AMD1:2021官方目录证据#897–#899。标准全文/国家差异、具体产品证书及硬件测试未完成，五项资产仍未验收。详见基线审计第51节。 | 文章全文审查；ISO/IEC官方目录抽查 |
| 2026-11-05 | 00-01 | 对传感器总览、毫米波雷达与超声波、深度相机三篇P0文章完成全文主张边界审查；明确普通感知/安全器件边界、雷达芯片/模组/成品层级，补充D455/D457型号级接口与深度质量口径。新增官方来源台账#900–#904，详见基线审计第52节。未完成所有器件逐型号数据表/认证、射频合规、驱动兼容、环境和目标场景实测，三项资产继续未验收。 | 正文审查；TI/RealSense官方资料核对 |
| 2026-11-05 | 00-01 | 对LiDAR集成检查表与09-03电子电气设计入门页完成全文P0边界复核：补充激光光学等级不等于安全功能认证，以及独立供电支路不自动构成功能安全的限制。依据现有IEC 60204-1官方目录#899核对边界；未进行实物、短路/温升/EMC/安全功能测试。详见基线审计第53节，两项资产继续未验收。 | 正文审查；工程边界核对 |
| 2026-11-05 | 00-01 | 在既有定向复核基础上，对《特种机器人》完成全文主张边界审查：更新ATEX当前合并文本，补充IECEx证书状态/特殊条件/组件证书与整机认证边界；核对ASTM E2521-26现行术语版、NIST任务测试与任务方阈值责任、ISO/DIS 8373草案状态及ISO 10218-2排除范围。新增官方来源#905–#910；无具体产品证书和测试原始数据，文章继续未验收。详见基线审计第54节。 | ISO/ASTM/NIST/EUR-Lex/IECEx官方资料核验；全文审查 |

| 2026-11-05 | 00-01 | 对 `knowledge/software/云平台与IoT通信.md` 完成P1全文主张边界审查并修订：按OASIS MQTT 5.0区分QoS协议交付与业务事务语义，补充AWS IoT Core QoS 0/1服务限制、MQTT 5会话/过期/流控、Retained/LWT边界；修正“DDS不出车”、2字节总开销、1–5Hz通用频率及Mosquitto单机万级/首选等绝对表述；补充端侧安全闭环、设备身份/ACL、App短时凭据、EMQX 5.9.0+ BSL 1.1、Mosquitto/Paho双许可及Paho 2.0 breaking change。新增链接台账#911–#916、基线审计第55节并同步资产清单。正文审查完成但未进行Broker部署/压测、弱网与断电恢复、证书/ACL渗透、端到端命令和OTA实测；资产继续保持未验收状态。 | OASIS/AWS/EMQX/Eclipse官方资料；全文主张边界审查；基线审计第55节 |

| 2026-11-05 | 00-01 | 对 `knowledge/software/仿真平台.md` 完成P1全文主张边界审查并修订：更新Gazebo Jetty/Harmonic/Ionic支持周期与ROS配套、Isaac Sim 6.2/Isaac Lab 3.0 GA兼容、MuJoCo 3.17、CoppeliaSim 4.10、Webots R2025b及Colosseum归档状态；更正Gazebo DART/Bullet/TPE物理引擎边界；补充RTX硬件需求、传感器误差模型、sim time/实时因子、MIL/SIL/PIL/HIL/VIL和Sim2Real校准/域随机化/实机验证要求。新增官方来源台账#917–#929、基线审计第56节并同步资产清单。正文审查完成，但未执行平台安装、模型运行、CI、PIL/HIL、实机标定或Sim2Real验证；资产继续未验收。 | Gazebo/NVIDIA/MuJoCo/Coppelia/Webots官方文档；全文静态主张边界审查；基线审计第56节 |

| 2026-11-05 | 00-01 | 对 `knowledge/software/构建与CI工具链.md` 完成P1全文主张边界审查并修订：更新CMake 4.4.5稳定版/4.5.0-rc2预发布边界、ROS发行版ament/launch_testing版本匹配；补充colcon/rosdep/vcstool职责、交叉编译sysroot/ABI/SDK、QEMU边界、GitHub Actions依赖锁定/最小权限/OIDC/runner隔离、SPDX 3.0/CycloneDX 1.7、SBOM覆盖、SLSA provenance/Artifact Attestations验证，以及固件签名/OTA断电回滚测试。新增官方来源台账#930–#943、基线审计第57节并同步资产清单。旧稿项目测试数字尚待脚本、commit和CI原始日志独立核验；本轮未运行构建/CI、生成SBOM、签名或实机OTA，资产继续未验收。 | CMake/ROS/GitHub/SLSA/SPDX/CycloneDX官方文档；全文静态审查；基线审计第57节 |

| 2026-11-05 | 00-01 | 对 `knowledge/software/视觉软件栈.md` 完成P1全文主张边界审查并修订：重构光学/采集/传输/驱动/消息/算法/推理分层；核对OpenCV 5.0与C++17/API/模块迁移及Apache-2.0主仓库许可、PCL 1.15.1-dev文档边界；补充GenICam/GenTL、USB3/GigE/MIPI、V4L2/libcamera/GStreamer；删除无条件标定精度、PTP亚毫秒同步和Orin FPS指标；补充Kalibr时空标定数据要求、PTP/硬触发/ROS时间戳边界、ONNX Runtime EP、TensorRT 11.4.1 engine portability、OpenVINO 2026.4硬件/驱动矩阵及端到端延迟/ROS 2验收。新增来源台账#944–#958、基线审计第58节并同步资产清单。未执行相机/镜头/光源/SDK实测、标定、推理基准、PTP测量或现场FAT/SAT，资产继续未验收。 | OpenCV/PCL/NVIDIA/Intel/ONNX Runtime/GStreamer/Kalibr/Basler/EMVA官方资料；全文静态审查；基线审计第58节 |

| 2026-11-05 | 00-01 | 对 `knowledge/getting-started/09-10-系统联调与测试.md` 完成P1全文主张边界审查并修订：重构T0–T6测试分层和证据门；核验ROS 2 Jazzy launch_testing active/post-shutdown tests、topic hz订阅端速率口径及Nav2 Lifecycle Manager/行为树边界；删除无项目依据的50m/10cm/15cm/10ms/2h/三轮全绿固定验收值，纠正随机kill -9实机故障注入、2秒速度归零及“轻触不算碰撞”等危险表述；补充故障注入、停止功能区分、配置快照、数据追溯与FAT/SAT门。新增来源台账#959–#963、基线审计第59节并同步资产清单。未连接机器人、未运行仿真/launch测试、未测量制动/急停或执行FAT/SAT，资产继续未验收。 | ROS 2 Jazzy/ROS Index/Nav2官方资料；全文静态审查；基线审计第59节 |

| 2026-11-05 | 00-01 | 对 `knowledge/ecosystem/manufacturers/README.md` 完成P1目录入口全文审查：确认其仅为厂商资源导航，不含可独立核验的产品参数/排名/供货主张；验证综合索引相对链接目标存在；补充非穷尽目录、供应商证据等级、型号/地区/生命周期/许可快照要求和章节边界。基线审计第60节已记录。未审查综合索引正文或逐厂商型号，不改变第21章21-02进行中状态。 |

| 2026-11-05 | 00-01 | 对 `knowledge/projects/README.md` 完成全文审查，补充历史静态梳理与当前可复核事实的边界、仓库/分支/commit/日期绑定和组织/代码血缘证据要求；对 `knowledge/projects/三项目关系总览.md` 及三份项目档案交叉审查，移除未经证实的“同公司/同团队/直接蓝本/血缘/行业领先”等确定性主张，重写为架构相似性对照和证据补齐清单。基线审计第61–62节已记录；三个项目单项档案尚待逐篇核验。 |

| 2026-11-05 | 00-01 | 对 `knowledge/projects/项目-amr.md` 完成全文主张边界审查：将所有包数/接口数/测试数/技术栈/行为声明明确标注为历史静态梳理记录，要求源仓库、固定commit、依赖快照、CI原始日志和行为测试证据；删除弱网/跨机场景不用DDS的行业化外推；补充未复核项及解除条件。基线审计第63节已记录，未进行源码复现或实机验证。 |

| 2026-11-05 | 00-01 | 对 `knowledge/projects/项目-BZ视觉框架.md` 完成全文主张边界审查：将版本/送检/平台、模块/设备/算法/依赖和数据流标注为历史静态记录；补充源码commit、SKU/SDK、算法测试、构建、SBOM/许可证及OTA安全证据要求；将MD5/DES标记为需安全复核的遗留线索；删除未经证实的清洁机器人直接蓝本/血缘及竞品等价断言。基线审计第64节已记录，未执行源码复现、设备测试或OTA安全测试。 |

| 2026-11-05 | 00-01 | 对 `knowledge/projects/项目-清洁机器人.md` 完成全文主张边界审查：将软件栈、重构日期、包/接口/状态机/测试数字和Gazebo仿真描述标为历史档案记录；补充固定源码commit、依赖锁定、可重复统计、CI日志、仿真工况、算法与实机证据要求；指出13项真机阻塞项与9+2+3=14的统计口径冲突；补充HTTP/MQTT/OTA安全边界。基线审计第65节已记录，未复现构建/CI、仿真或实机测试。 |

| 2026-11-05 | 00-01 | 对 `knowledge/robots/README.md` 完成目录入口审查：将单一分类表述改为应用/运动/操作/自治/环境多维交叉分类；补充当前知识卡索引、最低内容要求和未覆盖边界；核对并修正跨章节链接目标。基线审计第66节已记录；未完成10篇类型知识卡的逐篇全文事实核验。 |

| 2026-11-05 | 00-01 | 对 `knowledge/software/advanced-topics/11-扩展知识.md` 与 `advanced-topics/README.md` 完成全文导航审查：明确DDS/ROS1迁移专题定向审查与目标环境验收的区别；修正操作系统/网络通信专题实际路径说明；将PCB/EMC、机械材料、MCU外设缺口归属第05/03/09章；增加主归属、去重和证据维护规则。基线审计第67节已记录；未重新全量审查DDS/ROS1正文或执行目标环境测试。 |

| 2026-11-05 | 00-01 | 对 `knowledge/software/调度系统RMS.md` 完成全文主张边界审查：依据ISO官方页面核对ISO 21423:2026发布与范围；依据VDA官方页面/仓库更新VDA 5050 v3.0.0并区分接口与交通/安全/网络安全边界；修正Topic方向、必选/可选项及QoS，删除无来源固定频率、200–1000台容量和CP-SAT毫秒级性能承诺；补充assignment/VRP/MAPF/资源预约分层和验收边界。来源台账#964–#969，基线审计第68节。未完成正式标准逐条审查、多厂商互操作或现场压力测试。 |

| 2026-11-05 | 00-01 | 对 `knowledge/troubleshooting/系统故障诊断与闭环处理.md` 完成全文主张边界审查：区分FMEA/FMECA与FRACAS/PRACAS；补充IEC 60812:2018通用范围和非安全专用边界；登记MIL-HDBK-2155与NASA PRACAS官方实践；更新ROS 2 diagnostics来源与包职责；核验故障记录模板路径并保留安全升级边界。来源台账#970–#974，基线审计第69节。未执行具体产品故障复现、拆检、测量或现场CAPA验证。 |

| 2026-11-05 | 00-01 | 对 `knowledge/architecture/AMR整体架构.md` 完成全文主张边界审查：删除无来源的固定数据频率与NTP<100ms通用指标；明确逻辑层与物理部署、安全控制和车队/云端边界；补充ROS 2 Topic/Service/Action及QoS兼容性；重写断网降级、故障域和标准适用性；核对ISO 3691-4:2023及ISO/DIS草案状态。来源台账#975–#979，基线审计第70节。未进行目标AMR源码、HIL、实机或现场安全验证，00-01继续进行中。 |

| 2026-11-05 | 00-01 | 对 `knowledge/architecture/README.md` 完成目录入口全文审查：明确AMR架构仅为工业AMR参考视图，梳理建图/导航/多机调度/云端协同与OTA流程导航，厘清算法、软件、安全和系统工程主归属；核对所有目录与专题链接目标。基线审计第71节。未审查四个流程专题正文，也未补齐机械臂、人形及其他机器人类型的架构样例，00-01继续进行中。 |


| 2026-11-05 | 00-01 | 对 `knowledge/architecture/workflows/README.md` 完成流程目录入口审查：新增五类流程专题索引、生命周期阅读顺序、AMR适用边界及算法/软件/安全/系统工程主归属；核对五篇流程专题与流程地图路径；修正流程地图中已失效的 `项目-Bozlin视觉框架` 引用为当前 `项目-BZ视觉框架`。基线审计第72节记录。五篇流程正文尚未逐篇主张核验，00-01继续进行中。 |

| 2026-11-05 | 00-01 | 对 `knowledge/architecture/workflows/建图流程.md` 完成全文静态主张边界审查：移除无依据工时、遥控速度、回环间距、地图分辨率及尺度/残差/重定位/点位/多机固定阈值；拆分几何地图、定位数据、语义图层、部署配置与发布证据；补充场勘、传感器/TF就绪、原始数据、独立控制点、分层验收、版本兼容和回滚流程；修正BZ项目链接。新增来源台账#980–#984、基线审计第73节并同步资产清单。未执行目标算法构建、数据回放、实机建图、定位/导航、多机或现场安全测试，00-01继续进行中。 | slam_toolbox、Nav2 Jazzy、ROS nav_msgs官方文档；全文静态审查；基线审计第73节 |

| 2026-11-05 | 00-01 | 对 `knowledge/architecture/workflows/导航流程.md` 完成全文静态主张边界审查并修订：删除无项目依据的控制频率、速度/距离/精度/成功率/任务耗时等固定阈值；重构任务仲裁、定位、规划、控制、动态障碍、到位交接和异常升级流程；依据REP 105澄清map/odom/base_link与TF时间边界；依据Nav2 Jazzy文档划分Planner/Controller/Behavior/Costmap/Collision Monitor/Lifecycle职责，并明确普通导航软件不构成功能安全。新增来源台账#985–#989、基线审计第74节并同步资产清单。未执行Nav2构建、仿真、实机导航、动态人流、制动距离、HIL或现场验收，00-01继续进行中。 | Nav2 Jazzy官方文档、ROS REP 105；全文静态主张边界审查；基线审计第74节 |

| 2026-11-05 | 00-01 | 对 `knowledge/architecture/workflows/多机调度流程.md` 完成全文静态主张边界审查：分离业务/WMS、RMS任务分配、交通资源协调、车端导航、独立安全控制和设施控制；补充幂等/DAG任务、资源预约与真实占用闭环、死锁/活锁受控恢复、抢占重派、断网与恢复对账、KPI统计和分层验证；删除无项目依据的分配周期、状态频率、预测空闲窗口、拥堵/电量/等待阈值及扩容台数；依据VDA 5050 3.0.0更新zone/path sharing与接口边界，修复BZ旧链接。新增来源台账#990–#993、基线审计第75节并同步资产清单。未执行RMS实现/Schema差异检查、混合厂商互操作、交通仿真、容量压力、故障注入、设施互锁或现场安全验收，00-01继续进行中。 | VDA 5050官方页面、3.0.0规范PDF、官方GitHub与发布公告；全文静态主张边界审查；基线审计第75节 |


| 2026-11-05 | 00-01 | 对 knowledge/architecture/workflows/云端协同与OTA流程.md 完成全文静态主张边界审查：重构设备身份/命令授权/制品manifest/签名与启动链边界；依据NIST SP 800-193、IETF RFC 9019/9124、TUF与Uptane补充固件韧性、回滚/冻结攻击和多组件兼容要求；拆分下载、验证、安装、启动、业务健康与安全功能证据；删除无依据灰度比例、电量、自检时长、回滚阈值和保留期；补充机器人现场升级准入、异常恢复及分层验证清单；修复旧BZ项目档案链接。新增来源台账#994–#998、基线审计第76节并同步资产清单。未执行目标设备密钥/启动链/OTA源码审计、断电恢复、攻击测试、灰度发布、回滚演练或现场安全验收，00-01继续进行中。 | NIST SP 800-193、IETF RFC 9019/9124、TUF、Uptane官方资料；全文静态审查；基线审计第76节 |


| 2026-11-05 | 00-01 | 对 `knowledge/software/advanced-topics/DDS专题.md` 补充P1安全主张级审查：细化DDS-Security身份认证/访问控制/加密边界、ROS 2安全默认未启用与permissive/strict启动策略、enclave/进程安全上下文、ROS 2威胁模型、DoS/凭据泄露/桥接绕行和主机root等未覆盖风险；明确ROS_DOMAIN_ID不是安全控制，DDS-Security不覆盖非DDS链路或功能安全；增加安全配置负向测试、密钥生命周期和安全性能验收清单。正文已提交，基线审计第77节已记录。来源台账#999–#1001写入被平台安全检查阻止，未登记；未执行keystore/RMW安全启动、权限策略测试、密钥轮换、网络攻击、互操作、性能或实机验证，00-01继续进行中。 | ROS 2官方DDS-Security集成、Access Control Policies与Robotic Systems Threat Model设计资料；基线审计第77节 |

| 2026-11-05 | 00-01 | 对 `knowledge/software/advanced-topics/ROS1与迁移.md` 完成第二轮共存边界补充审查：细化Topic/QoS、Service幂等与超时、Action状态机、时间域/REP 105 TF权威、ROS Master与ROS 2发现网络分离、bridge双栈安全边界、单一写入权威、故障恢复及回滚；依据ROS 1归档/EOL、ros1_bridge官方README/映射文档、ROS 2 Jazzy LTS公告、发行版支持计划和REP 105补充官方依据。基线审计第78节；资产清单更新为第二轮定向审查范围。相关URL已写入专题正文，但本轮未更新链接台账；不重试此前被平台安全检查阻止的#999–#1001台账写入。未运行用户项目bridge或执行接口/QoS/时钟/TF/网络/安全负向/故障注入/性能/回滚测试，资产仍未完成完整claim-level验收。 | ROS 1/ROS 2官方资料、ros1_bridge文档、REP 105；第二轮定向静态审查；基线审计第78节 |

| 2026-11-05 | 00-01 | 对 `knowledge/software/ROS与ROS2.md` 完成P1全文主张边界审查并修订：更新ROS 2 Lyrical LTS及平台Tier矩阵；纠正核心客户端库、Lifecycle Node、Service同步/异步、Action取消、参数动态修改等语义；补全QoS多策略兼容性；区分Composition/intra-process/shared-memory；依据rmw_zenoh官方设计补充默认router发现机制；将未经复现的内部项目经验与工具建议降级为待验证线索。基线审计第79节，资产清单同步为全文静态审查。未执行目标平台构建、驱动兼容、RMW/QoS/实时性/性能/网络/安全或实机验证，资产继续未验收。 | ROS 2官方发行版列表、Lyrical发布与平台矩阵、QoS文档、rmw_zenoh设计文档；全文静态主张边界审查；基线审计第79节 |


| 2026-11-05 | 00-01 | 对 `knowledge/software/Nav2导航框架.md` 开展 Lyrical 发行版迁移差异增量复核：依据 Nav2 官方 Kilted→Lyrical migration guide 补充 `nav2_ros_common` 与 `LifecycleNode` 重构影响，加入自定义节点/插件依赖、Lifecycle API、BT/参数/接口迁移及回归检查；依据 ROS Index 记录 Jazzy/Lyrical 包版本索引快照；再次明确 Collision Monitor 是 CPU 软件层监控，不具备硬实时安全认证。基线审计第80节。未在目标工作区执行 Lyrical 构建、插件加载、Lifecycle/BT/规划控制回归、目标硬件实时性或停止距离测试；资产仍未验收，下一项转向《实时系统与嵌入式》P1复核。 | Nav2 Lyrical官方文档、Kilted→Lyrical迁移指南、ROS Index发行版包索引、Collision Monitor上游README；基线审计第80节 |


| 2026-11-05 | 00-01 | 对 `knowledge/safety/安全防护器件.md` 开展 P0 工业机器人应用级防护边界增量审查：依据 ISO 10218-2:2025 明确机器人本体 Part 1 与应用/工作单元 Part 2 的责任层级、工业环境定义和排除用途；补充标准未覆盖危险仍需另行评估；区分 OSHA 一般行业法规与 ANSI/A3 R15.06-2025 国家共识标准，并提示 OSHA 技术手册仍引用旧版标准的版本差异；增加任务/人员/工件/外围设备至检测—逻辑—停止链的防护证据清单。来源沿用链接台账#1014–#1017、#450；基线审计第99节，资产清单已同步更新。未购买/逐条审查标准全文，未进行具体应用风险评估、证书核验、保护区计算、停止时间/距离测试、故障注入或现场验收；资产保持未验收，00-01继续进行中。 |


| 2026-11-05 | 00-01 | 对 `knowledge/getting-started/09-03-电子电气设计.md` 开展 P0 机器电气安全增量审查：依据 IEC 官方目录核验 IEC 60204-1:2016+AMD1:2021 CSV Edition 6.1 当前有效，并区分第七版在研草案；明确机器电气设备范围从电源连接点起、标准与移动机器人车辆安全/功能安全/电池充电要求的协同适用边界；补充PDS、EMC、过电流、SCCR、保护联结、STO/急停、控制回路及技术文件审查清单。来源台账#1088、基线审计第100节及资产清单已同步。未购买/逐条审查标准全文，未检查实际原理图/BOM/线束/充电系统，未开展SCCR、保护联结、绝缘耐压、EMC、温升或保护动作测试；资产保持未验收，00-01继续进行中。 |
| 2026-11-05 | 00-01 | 对 `knowledge/getting-started/09-10-系统联调与测试.md` 增加 ROS 2 Jazzy 集成测试执行隔离与结果留证审查：区分 active/post-shutdown tests，补充独立 ROS domain ID、ReadyToTest/WaitForTopics、测试注册/发现及 `colcon test-result --all --verbose` 失败结果检查；来源台账#1089、基线审计第101节和资产清单已同步。未构建目标工作区、未运行 launch_testing/仿真/硬件测试或 FAT/SAT；资产保持未验收。 | ROS 2 Jazzy 官方集成测试与 CLI 文档；基线审计§101 |
| 2026-11-05 | 00-01 | 对 `knowledge/algorithms/多机协同与调度算法.md` 补充 Open-RMF Fleet Adapter 集成接口与发行版快照审查：核对 Fleet Adapter 的状态/任务/命令桥接、厂商 API 可替换性、Traffic Schedule/Negotiation 与单机导航/独立安全链边界；记录 Jazzy/Kilted/Lyrical 的 ROS Index 包版本快照。来源台账#1090–#1093、基线审计第102节和资产清单已同步。未构建 RMF 工作区、未运行 adapter/traffic schedule/negotiation、未接入真实车队或设施；资产保持未验收。 | ROS Index 与 Open-RMF 官方集成教程；基线审计§102 |
| 2026-11-05 | 00-01 | 对 `knowledge/ecosystem/开源项目与工具链.md` 的 Beremiz PLC IDE/runtime 条目开展 P1 增量主张审查：更新 v1.6.1（2026-10-31）版本快照，区分 IDE/CLI、MatIEC、Python/C++ runtime 的编译与执行职责及组件许可证；补充 eRPC 可选 TLS-PSK、WAMP/Web HMI/服务发现端点的独立安全边界，并标明 Zephyr 支持位于 NDA/双重许可私有分支。来源台账#1094–#1097、基线审计第103节和资产清单已同步。未下载/构建完整源码、未完成依赖法务/SBOM审查、未在目标 MCU/RTOS 构建或测量实时性，也未执行网络/安全测试；资产保持未验收。 | Beremiz 官方 Releases、下载/许可页、运行时架构文档及 MatIEC 仓库元数据；基线审计§103 |
| 2026-11-05 | 00-01 | 对 `knowledge/algorithms/路径规划算法.md` 开展Nav2 Smac增量主张审查：依据Jazzy插件选型与Rolling版Hybrid/Lattice参数文档，补充2D/Hybrid/Lattice的footprint与运动学适用边界、State Lattice离线控制集/地图分辨率绑定、搜索预算、解析扩展和平滑后验证要求。来源台账#1101–#1103、基线审计第105节、资产清单和第14章TaskPlan已同步。用户此前确认的路径规划测试尚未归档原始报告和参数；本轮未运行目标工作区/硬件测试，资产仍未验收。 | Nav2官方Jazzy/Rolling文档；基线审计§105 |
| 2026-11-05 | 00-01 | 对 `knowledge/ecosystem/主要厂商.md` 中OTTO Motors条目开展P1增量主张审查：补齐OTTO 100/600/1200/1500/Lifter型号级规格、Fleet Manager集成能力、VDA 5050合作认证边界及Rockwell SD1791/CVE-2026-75112版本影响与修复门槛；补充Rockwell收购和Milwaukee生产线里程碑并区分产线下线与实际交付。来源台账#1104–#1111、基线审计第106节、资产清单及第21章21-02执行记录已同步。未完成数据表/手册全文审查、接口/证书核验、供应商资格审查或目标工厂性能/安全/网络测试；资产保持未验收。 | OTTO/Rockwell官方产品、软件、互操作、制造及安全公告；全文增量静态审查；基线审计§106 |
| 2026-11-05 | 00-01 | 对 `knowledge/ecosystem/主要厂商.md` 中ABB Robotics交易状态开展P1时效性增量审查：依据2026-11-05 ABB确认的中国监管禁止收购ABB在华机器人业务事项，修正“仅待常规审批”的过时表述；严格区分中国业务禁止、全球其他地区审批/交割及双方仍在沟通三种状态；增加地区合同主体、制造地、IP/软件/数据跨境、保修、备件和售后连续性核验项。新增来源#1112–#1115、基线审计第107节、资产清单和第21章21-02记录已同步。未取得监管决定原件、交易范围修订/其他辖区审批/客户合同或供应链尽调，资产保持未验收。 | ABB、SoftBank官方交易材料、ABB并购登记、Reuters当日对ABB声明的报道；基线审计§107 |

| 2026-11-05 | 00-01 | 对 `knowledge/ecosystem/主要厂商.md` 中KUKA条目开展P1软件/网络安全增量主张审查：区分iiQKA.OS2与KSS/VSS软件分支及控制器配套，梳理iiQWorks/VRC、KSS工程仿真工具、现场总线和安全技术包；记录IEC 62443-4-2 Security Level 2产品认证声明与IEC 62443-4-1开发流程认证的不同范围，并保留KR C5/KR C5-2命名差异待原始证书核验。来源#1116–#1122、基线审计第108节已同步；资产清单本轮未更新，保持既有文件级记录，不触碰此前被拦截的ABB元数据同步。未取得证书原件/完整兼容矩阵，未执行目标控制器仿真、总线、功能安全或网络安全测试；资产保持未验收。 | KUKA官方软件/控制器/网络安全页面及2026-07认证公告；ISA转载KUKA Systems来源稿；基线审计§108 |

| 2026-11-05 | 00-01 | 对 `knowledge/ecosystem/主要厂商.md` 中Yaskawa条目开展P1产品/软件生态主张审查：补充MOTOMAN产品族、GP20/HC10代表型号、YRC1000/YRC1000micro控制器边界、MotoPlus V2.52、MotoSim EG-VRC、MotoLogix及ROS接入证据；明确ROS 2兼容矩阵、受控手册、证书、版本配对和实机验证仍缺。新增来源台账#1123–#1133，基线审计第109节和资产清单已同步。厂商资产继续未验收，00-01与21-02保持进行中。 |

| 2026-11-05 | 00-01 | 对 `knowledge/ecosystem/主要厂商.md` 开展ROKAE珞石P1厂商生态静态主张审查：补充工业/协作/具身智能产品矩阵、HSA/AR/Helios/iNex厂商披露、xCore SDK v3.0.1+与RCI实时控制模式边界，以及ROS 2 Humble/Ubuntu 22.04/x86_64、ros2_control/MoveIt 2/Gazebo支持矩阵和RViz-only双臂URDF限制。新增来源台账#1138–#1143、基线审计第111节、第21章21-02记录及资产清单同步。未构建SDK/ROS包、未运行Gazebo/实机或测量实时性/力控/安全功能；资产保持未验收。 | ROKAE官方产品新闻、开发者文档、ROS 2手册与下载中心；基线审计§111 |

| 2026-11-05 | 00-01 | 对 `knowledge/ecosystem/主要厂商.md` 中埃斯顿ESTUN条目开展P1静态主张审查：区分ER/iER代际切换和持续服务声明，补充Juliet/iER.OS/NGC/ERI及RCS/Editor/API工具链；按ER API手册核验RCS2最低版本、APIServer、API Mode/远程模式与厂商激活授权；审查ESTUN-R-D/codroid_ros2的Humble/Ubuntu 22.04、Codroid专用机型范围、TCP/UDP CRI、ros2_control/MoveIt、mock与skip测试边界。来源台账#1144–#1153、基线审计第112节、第21章21-02记录和资产CSV已同步。未下载受控iER/ERI资料、未构建或运行工作空间、未实测实时性/停止响应/安全链；资产保持未验收，00-01与21-02继续进行中。 | 埃斯顿官方产品/软件/手册及ESTUN-R-D公开GitHub仓库；基线审计§112 |

| 2026-11-05 | 00-01 | 审查埃夫特EFORT与启智Openmind生态：核对本体目录、EC2/EC3手册索引、MoDou IDE V2.2.1与RC版本、虚拟控制器/仿真声明、文档中心当前0篇文档，以及Openmind OS的ROS兼容声明缺少具体发行版矩阵；区分埃夫特与启智主体，并记录旧授权指南和V2.0云账号迁移说明之间的版本差异。来源#1154–#1163、基线审计§113、第21章记录及资产CSV已同步。未下载软件/受控手册，未进行安装、仿真、ROS、总线、实机或安全测试；00-01与21-02继续进行中。 | 埃夫特官方产品/下载/新闻页、启智公司介绍、墨斗IDE版本页 |


| 2026-11-05 | 00-01 | 对knowledge/ecosystem/主要厂商.md中AUBO遨博条目开展P1静态主张边界审查：补充AUBO系列与控制柜配对、CB-M手册版本/通信接口/安全I/O配置条件，区分ARCS/AuboStudio、JSON-RPC 2.0 RPC、RTDE与SCRIPT接口，记录SDK工具链/版本管理、虚拟机和认证范围缺口。新增来源台账#1164–#1171、基线审计第114节和第21章21-02执行记录。未下载构建SDK、未连接控制器/运行仿真、未执行ROS/总线/实机/安全验证，厂商资产保持未验收。 | AUBO官方开发者门户、控制器手册、SDK功能/环境/版本管理文档；基线审计§114 |


| 2026-11-05 | 00-01 | 对 knowledge/ecosystem/主要厂商.md 开展研华Advantech Robotic Suite P1软件平台主张边界审查：核对2.1.0发布日期、NVIDIA/Qualcomm ROS 2 Jazzy适配SKU与JetPack/Ubuntu组合、Intel旧版支持矩阵、ASR-D501 Basic-only边界；区分Basic/Complete安装依赖并记录WISEAgent版本文字疑点；审查SUSI/Modbus/OPC UA ROS节点、Time Sync Viewer的Ubuntu22.04限制、2ms示例参数和公开示例凭据。新增来源#1172–#1180、基线审计第115节和第21章21-02记录。未在目标板安装/运行、未连接PLC/传感器、未测试网络/实时/安全/OTA；资产保持未验收。 | 研华官方Robotic Suite文档与发行说明；基线审计§115 |


| 2026-11-05 | 00-01 | 对 `knowledge/ecosystem/主要厂商.md` 开展RoboDK P1软件生态静态主张审查：区分仿真、API、Post Processor离线代码生成与Robot Driver在线通信；核对API语言/传输、控制器选件依赖、后处理器版本漂移、碰撞模型边界、外部测量系统和许可方式；新增来源台账#1181–#1188、基线审计第116节、第21章21-02记录及资产CSV同步。未安装/构建软件、未接入控制器或测量系统、未执行实机/实时/碰撞/安全验证，资产保持未验收。 | RoboDK官方文档、API、后处理器、Robot Driver、碰撞检测、系统要求、定价与许可FAQ；基线审计§116 |

| 2026-11-05 | 00-01 | 对 knowledge/ecosystem/主要厂商.md 新增 Siemens Tecnomatix Process Simulate / Process Simulate X P1静态主张审查：区分Essentials/Standard/Advanced、VBL令牌池/按controller许可、机器人专用OLP controller、CEE与虚拟PLC三层调试架构；依据Siemens 2606官方更新摘要记录2026年功能快照，并明确PLCSIM Advanced/SIMIT/运动学模型不等于真实硬件HIL或功能安全验收。新增来源台账#1189–#1197、基线审计第117节、第21章21-02记录及资产CSV同步。未安装软件、未取得完整release notes/当前控制器兼容矩阵、未生成并在目标控制器编译程序、未连接PLC/驱动/机器人、未执行HIL/FAT/SAT或现场安全测试；资产保持静态审查未验收。 | Siemens官方产品/SKU/VBL页面、Tecnomatix 2606更新、Academy学习路径、Siemens Industry Online Support应用示例；基线审计§117 |

| 2026-11-05 | 00-01 | 对 knowledge/ecosystem/主要厂商.md 新增ABB RobotStudio / RobotStudio Suite P1软件生态静态主张审查：核对Virtual Controller/RAPID离线编程、RobotWare版本、RobotStudio Cloud、OPC UA/SIMIT PLC虚拟调试和SDK分层；补充2026.2/.NET 10插件与PowerPac兼容断点、企业云浮动/Node-locked许可条件，并审查PROFIsafe/CIP-Safety配置已知问题。新增来源台账#1198–#1206、基线审计第118节、第21章21-02记录及资产CSV同步。未安装软件、未创建目标型号VC、未构建/迁移SDK或PowerPac、未连接目标PLC/控制器、未执行HIL/FAT/SAT/现场安全验证；资产保持静态审查未验收。 | ABB官方Suite/Cloud、RobotStudio 2026.2 Release Notes、2026新许可资料、2025.4操作手册及SDK下载门户；基线审计§118 |

| 2026-11-05 | 00-01 | 对 `knowledge/ecosystem/主要厂商.md` 新增FANUC ROBOGUIDE / Virtual Robot / ROS 2 Driver静态审查：核对V10 64位与应用模块、Virtual Robot和真实控制器版本配对、V10 Revision E + FactoryTalk Logix Echo虚拟调试、ROS 2 Driver的J519/R912/S636选件和Ubuntu/Humble/Jazzy条件；记录v2.4.0与v2.3.0系统要求文档漂移、ROBOGUIDE Revision兼容案例、UDP/loopback/CRX I/O和限定的1 kHz配置。新增来源#1207–#1219、基线审计第119节、第21章记录及资产CSV同步。未安装ROBOGUIDE、未构建目标Virtual Robot/ROS 2工作空间、未连接Logix Echo/真实控制器/PLC、未执行HIL/FAT/SAT或实时/网络/功能安全测试；资产保持静态审查未验收。 | FANUC官方ROBOGUIDE/V10/Logix Echo说明、fanuc_driver官方README/文档/Release/Issue；基线审计§119 |

| 2026-11-05 | 00-01 | 新增Dassault Systèmes DELMIA Robotics 3DEXPERIENCE生态P1静态审查：区分角色化Robot Programmer/RVN/VCA等功能包、机器人模型库Additional Contents与OLP Translator；核对2,000+模型库非默认安装、2026新增71模型/6家厂商、2025多品牌Translator双向/指令差异、MCRS同步能力矩阵历史缺口、RRS II/FANUC VRC、ControlBuild/OPC UA/HIL边界及R2026x GA/FD01/FD02增量。新增来源#1220–#1232、基线审计第120节、第21章执行记录和资产CSV同步。未安装Native Apps/下载模型库、Translator或部署VRC/ControlBuild/真实PLC，未构建/导出目标程序、未执行HIL/FAT/SAT或安全/现场验证；资产保持静态审查未验收。 | Dassault官方DELMIA Robotics产品/社区文章、角色/Library/Translator/VRC/OPC UA/HIL/版本更新；基线审计§120 |

| 2026-11-05 | 00-01 | 对 `knowledge/ecosystem/主要厂商.md` 新增Visual Components 5.1.1制造仿真/机器人OLP/虚拟调试生态静态审查：核对5.1.1（2026-09-28）SKU与KUKA.Sim未包含项、5.1导航/PhysX/Python 3 Navigation API、FactoryLens/Omniverse边界、机器人模型/后处理器/在线连接插件的差异与数量口径、FANUC PC DK/Robot Server/PC Interface前置、ABB RobotWare/Runtime/Mastership条件、OPC UA证书/凭据存储、S7/PLCSIM/SIMIT/WinMOD和离线许可。记录下载页5.1.1与生命周期/系统要求5.0页面同步缺口、5.1.1 PhysX非确定性修复项。新增来源#1233–#1247、基线审计第121节、第21章执行记录和资产清单。未安装VC 5.1.1/FactoryLens、未获取eCatalog/后处理器/机器人插件、未创建校准工作站/导出程序、未接入真实FANUC/ABB/PLC/SIMIT/OPC UA或进行HIL/FAT/SAT/实时/安全测试；资产保持静态审查未验收。 | Visual Components官方Downloads/Release Notes/Help/Licensing/System Requirements/OLP/Connectivity与Academy；基线审计§121 |

| 2026-11-05 | 00-01 | 对KUKA软件生态增加独立P1审查，补充KUKA.Sim 4.x / OfficeLite / KSS与iiQWorks.Sim / iiQKA.OS2 VRC新路线：核对RCS支持KSS 8.5/8.6/8.7、KRL/Config.dat/WorkVisual导出、RoboTeam/变位机/安全距离功能与独立AddOn；核对OfficeLite Hyper-V/KSS虚拟控制器的外围连接限制；审查iiQWorks.Sim Basic/Advanced/RCS/VRC/Connectivity/Modeling/Path/Point/Surface许可矩阵、新旧许可类型、Copilot联网/数据政策和KR C5→KR C5-2迁移服务。新增来源#1248–#1261、基线审计第122节、第21章执行记录和资产清单。未下载软件/虚拟机/RCS/VRC/技术包，未迁移KSS工程或运行真实KRL、PLC/现场总线、HIL/FAT/SAT及安全验证；KUKA保持静态资料审查未验收。 | KUKA官方KUKA.Sim/OfficeLite/iiQKA.OS2/iiQWorks.Sim产品页、my.KUKA许可FAQ与迁移产品资料；基线审计§122 |

| 2026-11-05 | 00-01 | 按根计划队列完成Yaskawa MOTOMAN / MOTOMAN NEXT P1增量静态审查：补充GP/HC/NEX/AR/PL/SG/MPP/MotoMini/MH/PH产品族及型号级控制器映射，厘清传统DX200/YRC1000/YRC1000micro与新YNX1000/ACU两条控制平台；核验MotoSim EG-VRC 2026、INFORM、MotoPlus、YMConnect 1.1.10、MotoROS2 0.2.1、Smart Pendant SDK、MotoLogix以及ACU的RCS/PPLS/MVS/AIS/FCS服务、Linux/C++/gRPC/Docker开发链和YNX Simulator 3.3.0物理边界；记录ROS发行版Release/README口径漂移、Simple Connect/FSU限制、PLC板卡/CIP Safety变量交换差异。新增来源#1262–#1293、基线审计第123节、第21章执行记录和资产清单。未下载/安装/构建软件、未编译/部署控制器或ACU应用、未连接真实PLC/焊机/传感器、未运行HIL/FAT/SAT或安全/实时/节拍测试；资产保持静态审查未验收。 | Yaskawa/Motoman官方产品目录、Developer Portal、MotoSim/YNX Simulator、MotoROS2/YMConnect/GitHub Releases、INFORM/现场总线/控制器手册；基线审计§123 |


| 2026-11-06 | 00-01 | 将 `rexyll/MotionControlAlgorithms` 源码合并登记为根计划 TODO-EXT-001：等待上游最后验证完成后再由用户与助手讨论，验证完成不自动授权合并；当前不复制或导入源码。继续执行当前基线审计，已完成目标仓库算法资产差距分析，报告为 `docs/audits/MotionControlAlgorithms-knowledge-gap-matrix-2026-11-06.md`，覆盖轨迹/运动控制、路径/局部规划、机械臂操作和跨章 HAL/现场总线/验证映射。根节点00-01保持进行中。 |

| 2026-11-06 | 00-01 | 按已建立的 MotionControlAlgorithms 差距矩阵继续完善现有资产：为 `knowledge/algorithms/轨迹优化与运动控制.md` 新增离散 PID 工程化章节，覆盖信号方向/单位、采样时间、测量微分与滤波、积分饱和、输出限幅、前馈/级联、无扰切换、故障语义和分级验收记录。仅完成通用知识补充；未在目标硬件构建/运行 PID、未测量实时性/WCET、未做故障注入/HIL，资产不标记为产品验证通过。根节点00-01继续进行中。 |

| 2026-11-06 | 00-01 | 对照官方 Ruckig Tutorial、MoveIt 2 Time Parameterization 教程及 TOTG API，为《轨迹优化与运动控制》新增 jerk/S曲线、多轴同步、路径时间参数化与在线 OTG 边界、在线重定时状态连续性、输入验证/错误状态和轨迹验证矩阵。来源台账#1307–#1309。未运行目标设备、仿真/HIL或WCET测试，未改变00-01状态。 |

| 2026-11-06 | 00-01 | 为机械臂零基础教材增补 3D 刚体位姿/旋转表示、DH/POE、数值 IK、DLS 与冗余零空间、模型校验流程，并更新 manipulation 索引。来源台账#1310–#1315。未获取目标设备参数或执行软件/实机验证；资产盘点和主张级审计仍进行中。 |


| 2026-11-06 | 00-01 | 按MotionControlAlgorithms差距矩阵继续完善机械臂动力学资产：在既有零基础教材中新增拉格朗日法、刚体惯量、Newton–Euler递归逆动力学、前向动力学、质量矩阵、减速器/电机侧到关节侧力矩映射、摩擦模型和参数辨识验证矩阵。新增来源台账#1316–#1318。未取得具体机器人参数、未执行代码/仿真/实机或实时性验证，00-01保持进行中。 | Modern Robotics官方第8章与8.1/8.3教材资源；知识正文静态增补 |


| 2026-11-06 | 00-01 | 继续补齐机械臂动力学差距：新增参数辨识与负载估计章节，说明回归矩阵、最小/基参数、可辨识性诊断、激励轨迹、数据同步、稳健估计与物理约束、负载质量/重心/惯量估计及在线更新边界。来源台账#1319–#1321。未取得机器人数据、未运行辨识程序或验证负载估计，00-01保持进行中。 | Pinocchio动力学回归API、机器人模型辨识综述、MERL负载估计技术报告 |


| 2026-11-06 | 00-01 | 按机械臂动力学与操作差距继续补齐控制层：新增关节空间位置/速度反馈、计算力矩、笛卡尔/操作空间控制、末端力控制、阻抗/导纳、混合力运动控制，以及接口层级、故障状态机和分级验证矩阵。来源台账#1322–#1325。未构建控制器或运行SIL/HIL/WCET/实机接触测试，00-01保持进行中。 | Modern Robotics第11章官方教学资源；ros2_control Jazzy Admittance Controller文档；静态知识增补 |

| 2026-11-06 | 00-01 | 按运动控制知识差距继续完善机械臂资产：新增零空间冗余解析、加权/阻尼伪逆、严格任务优先级、关节/碰撞约束、QP及动力学一致投影，并记录 MoveIt Servo 的功能与安全边界；来源台账#1326–#1329。仅为静态知识增补，未运行数值程序、仿真、SIL/HIL、WCET或实机验证；00-01继续进行中。 | ETH Zürich课程讲义、TUM/DLR博士论文、MoveIt 2 Rolling官方教程与Concepts；教材§20 |

| 2026-11-06 | 00-01 | 按第14章运动控制差距继续扩充机械臂/移动操作资产：新建《全身控制与接触动力学》，覆盖浮动基座模型、CMM/质心动量定理、单边接触与摩擦锥、WBC层级QP、ZMP/LIPM假设、接触切换、底盘—机械臂协调、软件实时架构和验证矩阵；来源#1330–#1334。仅为静态知识正文，未运行Pinocchio/WBC求解器、仿真/SIL/HIL/WCET或实机验证；00-01继续进行中。 | Kim等WBC论文、Pinocchio API、CMU Atlas WBC论文、MIT CSAIL质心规划论文；新增教材 |


| 2026-11-06 | 00-01 | 按第14章 WBC 知识差距继续增补《全身控制与接触动力学》§14–§15，细化 QP 矩阵组装、层级优先级、摩擦锥近似、接触力分配、CoP/执行器约束、不可行诊断与数值回归用例；来源台账#1335–#1339。已对 TSID、OCS2、Pinocchio 约束 API 与官方四足 MPC 配置示例开展静态资料核对。未构建或运行依赖库/优化器，未执行仿真、SIL/HIL/WCET或实机试验；00-01继续进行中。 |


| 2026-11-06 | 00-01 | 按当前 main Git Tree 对账知识资产清单：确认仓库共 253 个 Blob、205 份 Markdown、142 份 knowledge Markdown、60 份 docs Markdown、26 份章节 TaskPlan；发现旧 CSV 有 17 份 knowledge 文件漏登、24 条已有记录 SHA/大小过期及 1 条空白记录。已补录新增文件、刷新全部旧记录 Blob SHA/字节数，清单扩展元数据对账字段；报告见 `docs/audits/2026-11-06-knowledge-asset-tree-reconciliation.md`。本轮仅为 Git 元数据对账，未重新全文扫描或逐句 claim-level 审查，00-01保持进行中。 |

| 2026-11-06 | 00-01 | 完成审计报告提交后的最终快照复核：当前 main Git Tree 为254个Blob、206份Markdown、142份knowledge Markdown、61份docs Markdown和26份章节TaskPlan；将 `docs/audits/2026-11-06-knowledge-asset-tree-reconciliation.md` 也纳入资产清单，随后在根计划、审计索引和本章记录均提交后再次刷新清单中全部路径的Blob SHA/字节数。最终清单元数据回读作为本轮验收条件；本轮仍未重新全文扫描/逐句claim-level审查，00-01保持进行中。 |

| 2026-11-06 | 00-01（关联 P0 电机/驱动器） | 对 `knowledge/actuators/电机与驱动器.md` §8 开展 IEC 61800-5-2 范围主张定向复核：使用 IEC 官方页面核对 Edition 2.1/2026-10-30/Valid 和修订摘要，使用 ANSI/UL 可见基础版范围预览核对 PDS(SR) 产品/应用集成边界及排除项；补充 IEC 61800-5-1 电气/热/能量安全分工，修正低需求模式绝对化表述，新增来源台账#1340–#1341及专项报告。未取得2026合并版全文，未核验具体驱动器证书/型号，未做应用风险评估、接线/参数审查、故障注入、停止时间/距离、HIL或实机验证；仅§8完成定向复核，整篇资产仍未通过claim-level验收。 |

| 2026-11-06 | 00-01 | P0 IEC 61800-5-2 范围定向复核报告提交后，刷新当前 main 统计：255个Blob、207份Markdown、142份knowledge Markdown、62份docs Markdown和26份章节TaskPlan；专项报告已加入审计索引和资产清单。此后须再刷新资产清单涉及文件的SHA/大小；正文审计仍只覆盖《电机与驱动器》§8，整篇claim-level验收未完成。 |




| 2026-11-06 | 00-01 | 对 P0《功能安全体系》开展 ISO 13849-1:2023 与 IEC 62061:2021+AMD1:2024+AMD2:2026 CSV 公开范围/版次定向审查：新增 §10，厘清两项标准的设计对象、运行模式、PLr/SIL 分配边界、机器级防护/电气危险/网络安全分工和选用流程；新增来源#1342–#1343及基线审计§124。未取得标准全文、未核验具体产品/证书/风险评估或执行HIL/实机验证；整篇资产仍未通过claim-level验收。 | 《功能安全体系》§10；来源#1342–#1343；基线审计§124 |




| 2026-11-06 | 00-01（关联 P0 安全防护器件） | 对《安全防护器件》开展安全激光扫描仪配置主张定向复核：依据 OMRON OS32C 官方规格/手册与 SICK microScan3 Core I/O 官方操作说明，核对完整型号/变体、保护区分辨率/量程、响应时间配置、污染过滤、多重采样、OSSD与非安全输出、EDM及端到端停止链；同步核对 ISO 3691-4:2023 与 ISO/DIS 3691-4 第三版的已发布/草案状态。新增来源#1344–#1349、专项报告和章节20执行记录。未获取目标设备证书/配置备份，未执行保护区计算、响应/停止实测、故障注入或整机验证；整篇资产仍未通过 claim-level 验收，00-01继续进行中。 | |


| 2026-11-06 | 00-01（关联 P0 安全防护器件：急停与安全继电器） | 对《安全防护器件》新增第9–10节，定向复核急停功能/标准生命周期及安全继电器启动与反馈逻辑：ISO 13850:2015仍为已发布版并进入待修订阶段，ISO/WD 13850为工作草案；Siemens 3SK1手册明确急停不得自动/手动启动并规定监控启动及反馈回路，系统响应时间须按相关模块累加；补充OMRON G9SE与Pilz PNOZ X3特定型号公开规格边界。新增来源#1354–#1358及专项报告。未审读标准全文、未取得具体设备证书/接线/参数备份，未执行故障注入、复位逻辑、停止时间实测或整机验证；整篇资产仍未通过claim-level验收，00-01继续进行中。 | [[安全防护器件]] §9–§10；来源#1354–#1358；专项审计报告 |


| 2026-11-06 | 00-01（关联 P0 安全防护器件：安全门联锁） | 对《安全防护器件》新增第11节，依据 ISO 14119:2024 官方摘要核对防护门联锁器件设计/选型、降低可预见规避风险及相邻标准分工；对 Pilz PSENmlock、Schmersal AZM300Z-ST-1P2P-A-T（103011112）、EUCHNER CTP（124987）具体型号资料核对门位置/锁定监控、编码等级、通电解锁/锁定、逃生释放、辅助电源安全切换和不同触发路径响应时间。新增来源#1359–#1362及专项报告。未审读标准全文、未取得目标门体/安装/证书资料，未进行保持力、失电逃生、规避攻击、串联故障注入或整机验证；整篇资产仍未通过claim-level验收，00-01继续进行中。 | [[安全防护器件]] §11；来源#1359–#1362；专项审计报告 |

| 2026-11-06 | 00-01（关联 P0 电池与电源） | 对《电池与电源》开展 IEC/UNECE 标准范围与版次定向复核：核对 IEC 62619:2022 工业锂电池范围、IEC 63056:2020 固定式储能系统补充要求，以及 UNECE《试验和标准手册》Rev.8 Amendment 1（2025）对第38.3节的修订；将正文旧版 Rev.6 Amendment 1 入口更新为当前官方 Rev.8 Amendment 1。新增来源#1350–#1353及专项报告。未审读标准全文、未取得具体电池/证书/运输测试摘要或开展电池包/整机试验；整篇资产仍未通过 claim-level 验收，00-01继续进行中。 | |

| 2026-11-06 | 00-01 | 对 `knowledge/ecosystem/主要厂商.md` 开展Stäubli Robotics P1软件生态静态审查：核对CS9型号映射、VAL 3、uniVAL plc/drive、现场总线与安全功能声明；审查ICube ROS 2 Jazzy/CS9 prototype的position-only、未实现velocity、effort估算、mock局限及开发暂停状态，并区分ROS-Industrial ROS 1历史驱动与ROS 2路线。新增来源#1413–#1421、专项报告、兼容矩阵行和第21章执行记录。未安装软件/构建工作区/连接真实控制器/PLC/安全回路，未执行实时、HIL/FAT/SAT或安全验证；资产保持静态审查未验收，00-01继续进行中。 | Stäubli官方CS9/VAL3/uniVAL页面、ICube ROS 2仓库与文档、ROS-Industrial仓库/ROS Index；基线审计§128 |

| 2026-11-06 | 00-01 | 对《主要厂商》新增Universal Robots §129开展P1主张级静态审查：区分CB3/e-Series/UR Series/g-series与PolyScope 3/5/10；固定UR ROS 2 Driver main HEAD e55b899（2026-11-06）和package.xml 7.2.0；区分PolyScope X内置ROS 2（10.7/Humble、10.15/Jazzy）、外部ros2_control driver、C++ Client Library及URCapX；核验控制模式、运动控制器、effort/force、校准、URSim/mock、SDK/URCapX兼容及安全责任边界。新增来源#1422–#1436、专项报告、兼容矩阵和第21章记录。未安装/构建软件、未连接真实机器人/PLC/安全回路、未执行实时/轨迹/力控/停止距离/HIL/FAT/SAT或安全验证；该厂商资产仅静态审查未验收，00-01继续进行中。 | UR官方ROS 2 Driver/Client Library/PolyScope X SDK/URCapX文档与仓库、UR Safety FAQ及PolyScope 10.15安全手册；基线审计§129 |

| 2026-11-06 | 00-01 | 对UR审计追加主张级版本差异核验：补充PolyScope X URScript ROS API句柄资源生命周期与至少2ms调用延迟/运动blend影响警示；补充CB3 EOL、CB5.6与PolyScope X、PLd Cat.3现行声明及ISO 10218-1:2025计划认证时间边界。新增来源#1437，更新厂商档案、兼容矩阵和基线审计；未对目标版本测量延迟或取得安全证书原件，仍仅静态审查。00-01继续进行中。 | UR官方PolyScope X ROS 2限制文档与Safety FAQ；来源#1436–#1437 |

| 2026-11-06 | 00-01 | 对《主要厂商》新增Doosan Robotics §130开展P1主张与代码静态审查：核对DART-Suite/DRL/DRFL、ROS 2 Humble/Jazzy、DRCF v2/v3、dsr_hardware2 SystemInterface、RT UDP 1ms/12347/rt_host、velocity/effort接口TODO、异步servol_rt语义、模拟器边界、A/E/A-S/M/H/P传感器差异及P系列PLd Cat.3/SIL2安全页面适用范围；发现Humble/Jazzy许可证声明和API文档/DRFL release版本差异。新增来源#1438–#1453、专项报告、兼容矩阵和第21章记录。未安装DART/DRFL、未构建ROS工作区、未连接真实机器人/PLC/安全回路、未执行实时/力控/停止距离/HIL/FAT/SAT，资产仅静态审查未验收，00-01继续进行中。 | Doosan官方ROS 2/API/DRFL/DART/安全文档及GitHub仓库；基线审计§130；来源#1438–#1453 |


| 2026-11-06 | 00-01 | 对《主要厂商》新增Techman Robot §131开展P1软件生态静态审查：区分传统TM与S系列ROS2驱动、固定tmr_ros2/tm2_ros2 Humble/Jazzy分支commit和包版本；核验TMflow/Listen Node控制架构、MoveIt/Gazebo模型与CoG更新、EIH Camera gRPC客户端、S系列安全/网络安全声明及许可证元数据差异。新增来源#1454–#1467、专项报告、兼容矩阵和第21章记录。未安装商业软件/未构建ROS工作区/未运行仿真/未连接真实机器人、相机、PLC或安全回路，未执行实时/轨迹/视觉/HIL/FAT/SAT/安全验证；资产仅静态审查未验收，00-01继续进行中。 | Techman官方产品/ROS/合规/下载页面与GitHub仓库；基线审计§131；来源#1454–#1467 |


| 2026-11-06 | 00-01 | 对既有FANUC软件生态档案§119开展增量主张级复核：核对FANUC Open Platform 1ms/3kg–2300kg宣传与ROS 2 Driver具体控制器、J519/R912/S636选件、URDF模型矩阵；固定main/jazzy与humble分支commit；静态审查Stream Motion UDP序号回退路径及open Issue #67、现有测试缺少乱序/重复/回绕回归用例的可见证据；补充MoveIt动态加速度/jerk约束、position-only命令接口和Lyrical未来API迁移风险。新增来源#1468–#1480、专项审计和兼容矩阵快照。未构建/运行测试、未执行UDP注入、未连接实机或PLC、未测1ms/jitter/轨迹/故障恢复，未进行HIL/FAT/SAT/安全验证；仅静态审查，00-01继续进行中。 | FANUC官方Open Platform、官方GitHub源码/Issues/Release与驱动文档；专项审计§119；来源#1468–#1480 |

| 2026-11-06 | 00-01 | 对Stäubli §128进行增量主张级复核并更正初审结论：确认ICube ROS 2仓库存在0.1.3 prerelease和0.1.4非预发布GitHub Release；0.1.4后至main HEAD仅发现两次CI依赖更新，且2026-11-01 Jazzy build_and_test成功，不能据此证明功能开发恢复或实机验收。补充SRS/VAL Blocks授权/版本前置条件、VAL3 addons部署边界；静态审查UDP would_block丢包仍返回true、sender校验TODO、消息header/payload校验缺口、诊断readiness硬编码、控制器模式/安全状态、4ms控制任务超时/安全/GPIO TODO、position/velocity/effort语义和mock测试覆盖。新增来源#1481–#1493，更新Stäubli专项报告、厂商档案、兼容矩阵、基线审计与审计索引。未构建/运行ICube工作区或测试、未安装SRS/VAL Blocks、未连接CS9/机器人/PLC/安全回路，未执行网络故障注入、实时/WCET、HIL/FAT/SAT或功能安全验证；Stäubli资产保持静态审查未验收，00-01继续进行中。 | Stäubli官方SRS/VAL Blocks页面、ICube GitHub Release/CI/源码/测试、VAL3 README；来源#1481–#1493；Stäubli专项报告§8–§10 |

| 2026-11-06 | 00-01 | 补充Stäubli HardwareInterface轴数/数值边界审查：on_init仅拒绝0轴、不限制≤6；对固定6元素command_reference的NaN检查按num_joints_索引，URDF>6轴存在越界访问静态风险；std::isnan不拒绝Inf。可见测试仅按6轴fixture，未覆盖DoF/Inf边界。新增来源#1494–#1495，并同步专项报告§9.3.1、厂商§128.7、兼容矩阵和基线审计。未运行目标工作区或测试，未复现运行时故障；00-01继续进行中。 | ICube固定main源码/HardwareInterface测试；Stäubli专项报告；来源#1494–#1495 |

| 2026-11-06 | 00-01 | 对Stäubli ICube ROS 2序号流补做静态审查：MAX_FRAME_SEQUENCE_NUMBER为65535，但subscriber的回绕丢包公式在65535→0无丢包时仍多报1；任意下降序号被当成回绕并接受，可能回退序号基准；重复帧标记new_message=false但read_message仍返回true，RobotDriver读取路径不拒绝且接收时间戳刷新。核对VAL3序号生成/延迟计算和现有测试未覆盖回绕、乱序、重复帧。新增来源#1496–#1500并同步专项报告§9.3.2、厂商§128.7、兼容矩阵和基线审计。未进行网络注入或运行测试；00-01继续进行中。 | ICube固定main subscriber/protocol/RobotDriver/测试源码及VAL3序号程序；Stäubli专项报告；来源#1496–#1500 |

| 2026-11-06 | 00-01 | 新增跨语言协议编码核验：initRobotStateMsg声明RobotState payload=124并分配132字节帧；encodeHeader在序号字段后再次写sequence而非payload_size，encodeRobotStateMsg调用该函数，C++ RobotState解析器没有校验此字段；C++自序列化往返测试不能覆盖VAL3→C++互操作。新增来源#1501–#1504，更新专项报告§9.3.3、厂商§128.7、兼容矩阵及基线审计。将其标为高优先级静态缺陷候选，尚未在真实CS9抓包或VAL3编译复核；00-01继续进行中。 | ICube固定main VAL3 encoder/init/call-site/C++ serialization test源码；Stäubli专项报告；来源#1501–#1504及#1486 |

| 2026-11-06 | 00-01 | 补齐VAL3 Header语义的双向源码证据：decodeHeader.pgx将序号之后的2字节解码到nPayloadSize，MessageHeader.dtx定义该字段和8字节Header；与encodeHeader重复写sequence的代码形成闭环证据。新增来源#1505–#1506，专项报告§9.3.3及厂商/矩阵/基线审计引用同步扩展。仍未运行VAL3编译、真实CS9抓包或跨语言fixture测试；00-01继续进行中。 | ICube固定main decodeHeader/MessageHeader类型源码；来源#1505–#1506 |

| 2026-11-06 | 00-01 | 进一步审查C++→VAL3命令帧：C++ RobotCommandMessage固定payload=47、总长55；VAL3 initRobotCommandMsg同设47，但decodeRobotCommandMsg在decodeHeader前用对象中保留的旧nPayloadSize检查长度，随后decodeHeader解析当前Header并可能清除该错误标志，解析后没有再次核对当前nPayloadSize=47；固定字段读取只检查实际55字节偏移。readDataOnce另行拒绝实际长度不匹配的数据报，因此定性为当前Header声明校验缺口而非短包越界。新增来源#1507–#1510，更新专项报告§9.3.4、厂商§128.7、兼容矩阵及基线审计。未执行畸形包注入/VAL3运行；00-01继续进行中。 | ICube固定commit VAL3 command decoder/init/readData、C++命令序列化；来源#1505、#1507–#1510 |
| 2026-11-06 | 00-01 | 对Stäubli ICube DiagnosticData解析器开展增量Header校验审查：deserialize先用对象当前Header校验、后读取输入Header，未在读取后验证payload_size=66；subscriber每个datagram新建消息对象，因此正常接收路径使用构造默认Header而非上一包残留值。read_diagnostic_data调用后检查type/staleness，但不检查payload_size；connect未把诊断接收作为准入，不能认定握手被影响。合法round-trip测试缺少畸形Header负向用例。新增来源#1511–#1515，更新Stäubli专项报告§9.3.5、厂商§128.7、兼容矩阵、基线审计及审计索引。未运行测试/注入或真实CS9验证；00-01继续进行中。 | ICube固定main DiagnosticData parser/subscriber/RobotDriver/FrameHeader/serialization test源码；来源#1511–#1515 |
| 2026-11-07 | 00-01 | 继续检查ICube ROS 2诊断通道端到端实现：发现随附VAL3工程只配置diagnostics UDP endpoint，DTX无siSocketDiagnostics，PJX无DiagnosticData类型/encoder，start.pgx诊断任务TODO，controlTask仅经control socket发布RobotState；C++ mock与test harness自行产生诊断帧，不能代表真实VAL3端实现。RobotDriver::connect将diag readiness硬编码true，未等待诊断首帧。将结论限定为随附公开userapp的实现缺失，不排除集成方自定义任务；未运行VAL3或实机。新增来源#1516–#1524，更新Stäubli专项审计§9.3.6、厂商§128.7、兼容矩阵、基线审计和审计索引。00-01继续进行中。 | ICube固定main VAL3项目清单/DTX/控制任务/启动程序/配置/C++ mock和测试；来源#1516–#1524 |
| 2026-11-07 | 00-01 | 增量检查Stäubli C++ DiagnosticData读取端：RobotDriver::read_diagnostic_data不检查status.new_message；RealTimeSocketSubscriber对同序号帧将该标志置false但仍返回true，且每个成功反序列化的数据报都会刷新reception_timestamp。外部诊断端若持续重复/重放帧，旧诊断内容可能持续被报告成功并刷新staleness。通用subscriber测试覆盖new_message=false时返回true，但没有read_diagnostic_data集成测试。由于固定VAL3 userapp目前没有诊断publisher，该项是发送端接通后的条件性风险。新增来源#1525–#1527，更新Stäubli审计§9.3.7、厂商§128.7、兼容矩阵和基线审计。未运行测试/注入，00-01继续进行中。 | ICube固定main RobotDriver/subscriber/test源码；来源#1525–#1527 |
