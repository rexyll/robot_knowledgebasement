# 2026-11-08｜Stäubli专项审计记录同步性核查

> 本记录属于第00章 00-01「全库资产盘点与基线」的审计治理工作。核查对象为 `rexyll/robot_knowledgebasement` 的 `main` 分支；本记录只登记文件间的可核验差异，不把摘要性 TaskPlan 记录当作专项报告正文，也不提前提升任何节点验收状态。

## 1. 核查结论

截至本次读取，Stäubli/ICube ROS 2专项审查在根目录 `TaskPlan.md` 中已记录到 §9.3.111，但其配套审计报告、厂商知识页、审计索引和第00章执行日志没有同步到同一进度。该差异是仓库的文档追踪/可审计性缺口，不代表此前的静态审查结论必然错误，也不能据此推断缺失文件中的内容不存在。

| 记录载体 | main 分支读取结果 | 最新可见进度 | Blob SHA |
| --- | --- | --- | --- |
| 根目录 `TaskPlan.md` | v8.81；版本日志末条为2026-11-08 | §9.3.111 | `3881faf2d11530a935fc1569aaa57c116f3a972e` |
| `docs/audits/2026-11-06-staubli-robotics-ecosystem-review.md` | 6,744行；末尾为§9.3.101及SERVO-666–SERVO-672验收任务 | §9.3.101 | `aae87e1dce6734232c40b371a10154bdc9d539a9` |
| `knowledge/ecosystem/主要厂商.md` | 2,322行；最后一个Stäubli增量节为128.61，引用专项审计§9.3.87、SERVO-513–SERVO-522 | §9.3.87 | `d3405aa5a2c242ddf6722edaef9c36ec520f26e6` |
| `docs/audits/README.md` | 111行；最后一个Stäubli索引条目停留在§9.3.56、SERVO-188–SERVO-202 | §9.3.56 | `71403a62c7f2126da2a28bfe19d7ffdf84d845e8` |
| `docs/TaskPlan/00-知识治理与分类体系/TaskPlan.md` | 506行；最后一条00-01专项记录为§9.3.38、SERVO-01–SERVO-14 | §9.3.38 | `5cf0844d3511d04988d3d7040a628d22f282a7d3` |

因此，不能仅凭根计划摘要就认为§9.3.88–§9.3.111已在各交付载体完成归档。特别是根计划记录的§9.3.102–§9.3.111尚未进入专项报告正文；厂商档案、README和00章执行日志落后得更多。

## 2. 可确认的最新增量工作边界

根计划v8.81对§9.3.102–§9.3.111的记录显示，工作主题已从Servo launch依赖继续进入MoveIt Servo Jazzy 2.12.4-1发布供应链追溯，包含：

- §9.3.102：检查CI与Docker对可选Servo启动路径的覆盖；发现manifest/测试覆盖缺口，但未据此断言CI必然缺包。
- §9.3.103–§9.3.106：定向核对Jazzy包可用性、Noble amd64/arm64构建工件索引、MoveIt 2.12.4源码清单、Servo节点安装路径及ROS发行记录。
- §9.3.107–§9.3.110：追溯Bloom发布记录、rosdistro合并提交、release README首次引入记录、轻量release tag及Noble Debian packaging branch。
- §9.3.111：已完成release tag commit tree与MoveIt上游2.12.4的`moveit_ros/moveit_servo`目录递归比对，双方均为54个tree条目/43个blob，路径、mode、type与blob SHA逐项一致；SERVO-712完成。SERVO-713只推进到查阅Build Farm job命名规范并尝试访问Jenkins/API，尚未取得可核验job索引、构建状态、source revision或console log。

以上为根计划现存的摘要记录；在补齐专项报告章节与逐项来源链接之前，不应将其提升为“完整可复核报告已归档”。

## 3. Build Farm证据边界

ROS 2官方Build Farm文档说明，release job分为source与binary类型；source job由rosdistro distribution文件中的版本变化触发，binary job由对应source job触发。文档给出命名模板，并举例Rolling/Noble/amd64的binary job名称为`Rbin_uN64__rclcpp__ubuntu_noble_amd64__binary`。据此，对Jazzy/Noble/amd64的`moveit_servo` binary job只能推导出候选名称：

`Jbin_uN64__moveit_servo__ubuntu_noble_amd64__binary`

该字符串只是按公开命名模板推导的查询候选，不构成Jenkins job存在、曾执行、构建成功、上传生产仓库或产物可安装的证据。当前未确认arm64任务名，也未确认source job的具体platform短码。

本轮尝试访问候选Jenkins job/API时，网页读取端返回不可访问；运行环境访问`build.ros2.org`时DNS解析失败；搜索也没有返回可验证的精确job页面。因此，本轮不报告job URL、build number、result、source revision或console log，不把访问失败解释为job不存在或构建失败。

参考：
- ROS 2 Build Farms官方文档：<https://github.com/ros2/ros2_documentation/blob/rolling/source/The-ROS2-Project/Contributing/Build-Farms.rst>
- ROS Build Farm release job实现说明：<https://github.com/ros-infrastructure/ros_buildfarm/blob/master/doc/jobs/release_jobs.rst>

## 4. 必须补齐的同步工作

1. 将根计划已记录的§9.3.102–§9.3.111逐节补入专项审计报告，保留每节的输入源码版本、官方来源、事实结论、推断边界、验收任务ID与状态。
2. 将§9.3.88–§9.3.111的经核对摘要同步到`knowledge/ecosystem/主要厂商.md`；未从专项报告恢复的来源编号不得猜测或复用。
3. 更新`docs/audits/README.md`中的专项审计索引，明确正文最新节、未执行的SERVO任务及静态审查边界。
4. 更新第00章00-01执行日志，使其反映真实交付载体进度，而不是只记录早期§9.3.38。
5. 同步完成后再核对各文件引用的来源编号、任务ID、上游commit、发行版/二进制版本和验收状态；有冲突时保留差异说明，不静默覆盖历史判断。

## 5. 状态与限制

- 第00章00-01：**进行中**。本次仅确认审计记录不同步并建立纠偏任务，不代表全库资产盘点或claim-level审计完成。
- 第21章21-02/Stäubli：**进行中**。仍是固定公开源码与文档的静态审查，未完成Jazzy干净环境安装/构建/launch、VAL3编译、CS9/SRS、HIL、FAT、SAT或实机验证。
- SERVO-710：生产APT签名、Packages stanza、deb SHA256和control元数据仍未取得。
- SERVO-713：Build Farm job/build证据仍未取得；候选任务名不得标成已确认job。
- SERVO-714：发布构建与APT产物的最终一致性核验仍未完成。
- 未修改ICube上游；未授权合并TODO-EXT-001；不以普通STOP/软件状态推断CS9安全停止或物理静止。

## 6. 本轮同步处理结果（2026-11-08追加）

根计划已在v8.82中记录原始不同步问题；本轮进一步完成以下补齐：

| 载体 | 本轮处理 | 最新结果 |
| --- | --- | --- |
| 专项报告正文 | 保留旧主报告，新增§9.3.102–§9.3.111发布供应链追加件，避免覆盖历史段落 | 主报告§9.3.101 + 追加件§9.3.111 |
| 厂商档案 | 在`knowledge/ecosystem/主要厂商.md`新增§128.62，链接主报告与追加件，摘要发行证据及未完成验证边界 | §128.62引用§9.3.102–§9.3.111 |
| 审计索引 | 在`docs/audits/README.md`增加追加件索引 | 已链接追加件与差异报告 |
| 第00章执行日志 | 已记录原始载体不同步问题；本轮追加本次报告/厂商页/索引同步结果 | 00-01仍为进行中 |
| 根TaskPlan | v8.82已记录原始核查；后续v8.83记录本轮同步补齐及残余阻塞 | 00-01/21-02仍进行中 |

本轮新增追加件路径：`docs/audits/2026-11-08-staubli-moveit-servo-release-chain-addendum.md`。追加件对§9.3.102–§9.3.111给出逐节摘要和任务边界；主报告旧文件未被重写。厂商档案和README现有旧条目仍保留，新增的末尾入口明确指向最新追加件。

**尚未解决：** 没有取得Build Farm真实job页面/API、build number/result/source revision/console log；没有取得生产APT签名、完整Packages stanza、deb control和SHA256；未执行干净ROS Jazzy环境安装、构建与Servo启动。静态审查材料同步完成不等于专项工程验收完成。

## 7. 新增Build Farm二进制仓库证据（2026-11-08追加）

本轮在ROS官方Jazzy status page、Build Farm `building`与生产`main` pool目录中取得了比此前候选job名更强的证据：

- amd64：状态页B/T均为`2.12.4-1noble.20261105.184638`，M为`2.12.4-1noble.20261006.040508`；building目录列出对应新deb（673,950 bytes），main目录列出旧deb（674,492 bytes）。
- arm64：状态页B/T均为`2.12.4-1noble.20261106.111556`，M为`2.12.4-1noble.20261006.043301`；building目录列出对应新deb（617,952 bytes），main目录列出旧deb（615,538 bytes）。
- ROS ros_buildfarm官方说明明确：release job产物导入building；每架构binary jobs结束后满足sync criteria会自动同步到testing；testing到main需手动触发。因此本轮可确认两种架构的较新产物已在building，并在status page中与testing版本一致；生产main仍为10月6日旧版本。
- 按官方ros_buildfarm实现推导出amd64与arm64的binary job标识，但build.ros2.org页面/API仍不可读取；未取得build number、result、source revision或console log。

本次追加件及厂商档案已同步到§9.3.112 / §128.63。上述证据将SERVO-713推进为“部分取证取得”，但仍不标记完成；SERVO-710（APT签名、Packages stanza、deb control/SHA256）和SERVO-714（生产main产物最终一致性）仍未完成。直接下载deb和访问Packages/InRelease签名内容本轮失败，不作密码学/包元数据通过结论。详细记录见`docs/audits/2026-11-08-staubli-moveit-servo-release-chain-addendum.md`。

## 8. 资产清单Git元数据刷新（2026-11-08追加）

本轮新增厂商档案§128.62–§128.63后，回查`docs/audits/2026-11-03-knowledge-asset-inventory.csv`发现《主要厂商.md》仍保存旧Blob SHA和文件大小。现已将该资产行更新为：
- 当前Blob SHA：`47cec733256e1a226d3e548cda520a93969d23a0`
- UTF-8文件大小：501,796 bytes（按当前文件文本UTF-8编码长度计算）
- metadata_reconciled_date：2026-11-08
- metadata_reconciliation_scope：仅刷新该文件的Blob SHA与UTF-8大小，明确不做claim-level审查。

README中的清单说明已补充此单行刷新范围。该操作只维护Git Tree元数据一致性，不改变该资产的`unaccepted_claim_level_review_pending`状态，也不代表142份资产的所有Blob SHA/大小均已在本日重新刷新。其他资产仍须按全库盘点流程逐项对账。

## 9. ROS Jazzy状态页最新快照同步（2026-11-08追加）

本轮重新读取ROS官方状态页并确认：
- Noble amd64页面生成时间2026-11-08 03:56:07 -0800，building/testing仍为`2.12.4-1noble.20261105.184638`，main仍为`2.12.4-1noble.20261006.040508`。
- Noble arm64页面生成时间2026-11-08 04:23:04 -0800，building/testing仍为`2.12.4-1noble.20261106.111556`，main仍为`2.12.4-1noble.20261006.043301`。
- main pool目录仍列出两份10月6日旧deb，没有发现新版本进入main的证据。InRelease/Release.gpg仍未进行密码学验签，Packages stanza、deb control和SHA256未取得。

本轮同步载体：
- 专项追加件新增§9.3.113；
- 厂商档案新增§128.64；
- 本README更新追加件索引；
- 第00章00-01执行日志追加本轮快照复核；
- 根TaskPlan更新至v8.86；
- 资产清单中《主要厂商.md》一行刷新Blob SHA/UTF-8大小。

**任务状态不变：** SERVO-713仍为部分取证；SERVO-710/714仍未完成；00-01及21-02继续进行中。此轮仅刷新发行状态证据与文档追踪，不构成APT安全、功能、VAL3/CS9、HIL或实机验收。

## 10. 厂商资产元数据再次对账（2026-11-08追加）

因§128.64再次修改`knowledge/ecosystem/主要厂商.md`，已再次刷新资产清单中该文件唯一对应行：
- 当前Git Blob SHA：`74a7c8851d2d9a4ff0c89f4428bbecc3eb5d7c16`
- UTF-8大小：503,010 bytes
- metadata_reconciled_date：2026-11-08
- 本次仅刷新该文件Blob SHA/大小和元数据说明；不做claim-level内容验收，不表示其余141项已在本轮重算。

README已同步说明：2026-11-08对同一资产行随§128.62–§128.64两轮内容更新刷新元数据。该资产仍处于静态厂商审查进行中状态。


## 11. ROS Jazzy APT lists目录快照复核（2026-11-08追加）

本轮继续核对MoveIt Servo发布供应链，直接检查ROS官方APT lists目录：ros2-testing Noble amd64 InRelease/Packages目录时间为2026-11-06 13:15，Packages 8,406,600 bytes；arm64 InRelease/Packages目录时间为2026-11-07 11:29，Packages 8,381,795 bytes。ros2生产main amd64 Packages目录时间为2026-10-06 08:57；arm64 InRelease/Packages目录时间为2026-10-06 08:59。因此testing索引快照比生产main更新，不能把testing的较新索引视为生产main已同步。

尝试读取Packages/InRelease原文时，网页读取器返回不支持application/octet-stream，故未取得moveit_servo完整Packages stanza、SHA256/Depends，也未验证InRelease签名；没有读取deb control或执行Ubuntu 24.04 APT安装。读取通道错误不等于源文件损坏或签名失败。

本轮新增专项追加件§9.3.114、厂商档案§128.65，并更新审计README。厂商档案修改后资产清单需再次刷新该文件单行Blob SHA/UTF-8大小；这仍只是元数据维护，不是claim-level验收。SERVO-710/714未完成，SERVO-713仍部分取证；00-01/21-02继续进行中。


## 12. 厂商资产元数据最终刷新与载体同步（2026-11-08追加）

在§128.65写入后，已将knowledge/ecosystem/主要厂商.md对应资产行再次刷新为Git Blob SHA 03ff74bcb3fd064529137fbd2407e7eeac85ceb8、UTF-8大小505,182 bytes、metadata_reconciled_date=2026-11-08。该动作只更新此单一资产的Git元数据，不代表142项资产的全库元数据重算，也不改变该文档P1 claim-level review未完成状态。

本轮文档同步状态：根TaskPlan v8.87记录§9.3.114/§128.65；专项追加件新增§9.3.114；厂商档案新增§128.65；审计README、00-01与21-02章节日志已同步；资产清单对应行已刷新。SERVO-710/714仍未完成，SERVO-713仍部分取证；没有取得Jenkins直接构建日志、APT签名/完整Packages stanza/deb control/SHA256，也没有执行APT安装、ROS运行、VAL3/CS9/HIL/实机验收。

## 13. Build Farm命名与状态页复核后的载体同步（2026-11-08追加）

本轮新增专项审计追加件§9.3.115，直接核对ros_buildfarm/common.py中的source/binary job命名函数，并推导Jazzy/Noble的source、amd64 binary、arm64 binary三个候选job名。候选名称仍未由Jenkins页面/API直接确认；三个/api/json端点均未能由本轮读取通道访问，未取得build number、result、source revision或console log。

ROS官方Jazzy状态页仍显示：amd64页面生成时间2026-11-08 03:56:07 -0800，moveit_servo B/T为2.12.4-1noble.20261105.184638、M为2.12.4-1noble.20261006.040508；arm64页面生成时间04:23:04 -0800，B/T为2.12.4-1noble.20261106.111556、M为2.12.4-1noble.20261006.043301。未发现main晋级。

同步载体：专项追加件§9.3.115；厂商档案§128.66；审计README；根TaskPlan后续更新。厂商档案更新后，资产清单对应行已刷新为Blob SHA f5b00f49ec86b448a6cbf653b25ad13af938c61c、UTF-8大小506,424 bytes、metadata_reconciled_date=2026-11-08。该动作只刷新单一文件Git元数据，不代表claim-level验收或全库元数据重算。

SERVO-713仍部分取证、未完成；SERVO-710/714仍未完成。APT签名、Packages完整记录、deb control/SHA256、Jazzy目标环境安装运行、VAL3/CS9/SRS/HIL/实机验证仍未完成。00-01/21-02保持进行中，Stäubli未通过工程验收，TODO-EXT-001仍未授权合并。