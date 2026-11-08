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

同步载体：专项追加件§9.3.115；厂商档案§128.66；审计README；根TaskPlan v8.88；00-01与21-02章节TaskPlan执行日志。厂商档案更新后，资产清单对应行已刷新为Blob SHA f5b00f49ec86b448a6cbf653b25ad13af938c61c、UTF-8大小506,424 bytes、metadata_reconciled_date=2026-11-08。该动作只刷新单一文件Git元数据，不代表claim-level验收或全库元数据重算。

SERVO-713仍部分取证、未完成；SERVO-710/714仍未完成。APT签名、Packages完整记录、deb control/SHA256、Jazzy目标环境安装运行、VAL3/CS9/SRS/HIL/实机验证仍未完成。00-01/21-02保持进行中，Stäubli未通过工程验收，TODO-EXT-001仍未授权合并。
## 14. ROS Jazzy状态页刷新与Servo binary pool精确文件核对（2026-11-08追加）

新增专项追加件§9.3.116与厂商档案§128.67。amd64官方状态页本轮生成时间更新为2026-11-08 04:36:03 -0800，moveit_servo B/T仍为2.12.4-1noble.20261105.184638、M仍为2.12.4-1noble.20261006.040508；arm64页面仍为04:23:04 -0800，B/T为2.12.4-1noble.20261106.111556、M为2.12.4-1noble.20261006.043301。

building pool直接列出amd64新deb（完整文件名ros-jazzy-moveit-servo_2.12.4-1noble.20261105.184638_amd64.deb，673,950 bytes，目录时间11-05 18:58）和arm64新deb（ros-jazzy-moveit-servo_2.12.4-1noble.20261106.111556_arm64.deb，617,952 bytes，目录时间11-06 11:29）；production main pool仍仅列10-06旧deb（amd64 674,492 bytes、arm64 615,538 bytes）。点击deb链接后读取通道不支持application/octet-stream，未取得包内control/哈希；testing pool目录也未直接取得可读响应，testing版本仍以状态页T列为证。

厂商档案更新后，资产清单中该文件单行已刷新为Blob SHA 7a58b297e73046ca65956547c2098dea54b6540c、UTF-8大小507502 bytes。仅为单一资产元数据刷新，不代表claim-level验收或全库重算。

SERVO-713仍部分取证、未完成；SERVO-710/714未完成。APT签名/Packages完整记录、deb control/SHA256、真实Jenkins build日志、目标Jazzy安装运行、VAL3/CS9/SRS/HIL/实机验证仍缺。
## 15. Testing/main APT索引目录双源交叉核验（2026-11-08追加）

新增专项追加件§9.3.117与厂商档案§128.68。ROS官方testing lists目录及OSUOSL rsync镜像目录均列出Jazzy Noble amd64 InRelease/Packages时间为2026-11-06 13:15（4,679/8,406,600 bytes），arm64为2026-11-07 11:29（4,679/8,381,795 bytes）；source InRelease为11月7日11:28，Sources为11月6日13:09（10,217,787 bytes）。Production main lists目录仍列amd64 10月6日08:57、arm64 10月6日08:59的旧索引。Testing索引目录时间比main新约31–32天。

本轮再次打开Jazzy amd64/arm64状态页，页面时间戳仍为04:36:03/04:23:04 -0800，moveit_servo B/T/M版本未变化。索引目录元数据双源一致，但Packages/InRelease正文仍未成功下载或展开；未取得包stanza、签名验证、deb control/SHA256。不得将索引时间新误读为production晋级或APT签名通过。

厂商档案更新后，资产清单对应行刷新为Blob SHA 33181a6ddebfbf4cda3c18b6b6d6ef470466075a、UTF-8 508670 bytes；仅元数据刷新，不代表claim-level审查或全库重算。

SERVO-710/714仍未完成；SERVO-713部分取证、未完成。目标Jazzy apt安装运行、VAL3、CS9/SRS、HIL/FAT/SAT与实机验证未执行。
## 16. 状态页时间顺序与Build Farm阶段语义复核（2026-11-08追加）

新增专项追加件§9.3.118、厂商档案§128.69。ROS Jazzy规范URL直接读取的页面生成时间为amd64 2026-11-08 04:36:03、arm64 2026-11-08 04:23:04（-0800）；moveit_servo amd64 B/T均为2.12.4-1noble.20261105.184638、M为2.12.4-1noble.20261006.040508；arm64 B/T均为2.12.4-1noble.20261106.111556、M为2.12.4-1noble.20261006.043301。搜索索引中带?q=RED的2026-11-07 18:03:03页面早于11月8日规范快照，且打开后返回2025年旧缓存，不得将其误称为更新快照。

ROS ros_buildfarm release job官方文档确认source job、binary job和building到testing的sync criteria流程；但不证明具体moveit_servo Jenkins job的实际执行结果。具体job API/页面在当前读取通道不可访问。再次尝试读取InRelease/Packages、压缩Packages和testing包目录未成功；未获得签名、包stanza、deb control或SHA256。Production main pool仍列10月6日旧deb。

资产清单厂商档案行刷新为Blob SHA 996235b93781acb4ab77737ef1274ebd22eadc6d、UTF-8 510090 bytes，CSV保持14列且正确闭合引号。仅元数据刷新，不代表claim-level复审。

SERVO-710/714未完成；SERVO-713部分取证但未完成。目标APT安装运行、VAL3、CS9/SRS、HIL/FAT/SAT和实机验证未执行。

## 17. MoveIt Servo rosdistro release ref与上游package.xml文件级核对（2026-11-08追加）

新增专项追加件§9.3.119、厂商档案§128.70。读取ros/rosdistro当前master的jazzy/distribution.yaml，moveit release stanza声明release仓库ros2-gbp/moveit2-release、版本2.12.4-1、包清单含moveit_servo、tag模板release/jazzy/{package}/{version}；source仓库为moveit/moveit2、source version main。按模板展开的release ref release/jazzy/moveit_servo/2.12.4-1可读取。上游moveit/moveit2 tag 2.12.4中的moveit_ros/moveit_servo/package.xml与release ref根package.xml Blob SHA均为0f00c9ec3b85b0322b96124cd714cf9d280473fb，文件完全相同，包版本字段为2.12.4；发行修订号-1属于release版本号。release ref下debian/changelog和debian/control读取返回404，未取得Debian packaging内容。该文件级匹配不等于完整source package或binary package一致，也不证明Build Farm具体job成功。

SERVO-713新增rosdistro/release ref/package.xml关联证据，但仍部分取证、未完成；Jenkins job/build number/result/source revision/console log仍缺。SERVO-710/714未完成；APT索引正文、签名、完整Packages stanza、deb control/SHA256仍缺。未执行Ubuntu 24.04安装运行、VAL3、CS9/SRS、HIL/FAT/SAT或实机验证。Stäubli工业级验收仍未通过。


## 18. Jazzy状态页生成时间与production main pool目录复核（2026-11-08追加）

新增专项追加件§9.3.120、厂商档案§128.71。ROS Jazzy amd64状态页生成时间04:36:03 -0800，arm64本轮页面生成时间04:43:04 -0800；moveit_servo B/T分别保持11月5日与11月6日构建，M仍分别为10月6日旧构建。arm64页面生成时间变化不代表包版本变化。ROS production main pool目录直接列出的amd64/arm64 deb分别为674,492/615,538 bytes，构建标识与状态页M列相符；目录还列出2025-12-06的dsc、debian.tar.xz和orig.tar.gz源包文件及其大小。官方deb/dsc与OSUOSL dsc均未能展开，容器下载失败，因此没有取得SHA256、Debian control/changelog或签名验证。testing pool本轮未成功读取，不能据main目录缺项推断testing文件不存在。

SERVO-710/714未完成；SERVO-713部分取证、未完成。目标Ubuntu 24.04安装运行、VAL3、CS9/SRS、HIL/FAT/SAT和实机验证均未执行。Stäubli工业级验收仍未通过。


## 19. MoveIt Servo Debian源包发布证据边界与载体同步（2026-11-08追加）

本轮新增专项追加件§9.3.121、厂商档案§128.72。重新读取ROS Jazzy规范状态页，amd64 04:36:03、arm64 04:43:04（-0800），moveit_servo B/T仍分别为11月5/6日构建、M仍为10月6日构建；未观察到新构建版本或production晋级。状态页目录索引中的HTML文件mtime与页面内生成时间格式不同，未混作版本变化。

`ros2-gbp/moveit2-release` README的Jazzy `moveit 2.12.4-1`发布记录列出`moveit_servo`，与rosdistro release stanza和release ref关联一致。该记录只证明发布批次声明，不是具体Jenkins job/build成功证据。再次尝试读取ROS main、OSUOSL镜像及ROS testing的`.dsc`和testing pool目录，读取通道拒绝或无法访问；未取得源包校验和、debian/control/changelog/rules正文、签名状态、APT完整Packages stanza、deb control/SHA256或真实Jenkins build日志。

载体同步：
- 专项追加件新增§9.3.121；
- `knowledge/ecosystem/主要厂商.md`新增§128.72；
- `docs/audits/README.md`更新追加件索引；
- 第00章与第21章TaskPlan追加本轮执行记录；
- 厂商档案资产清单对应行刷新为Blob SHA `52fbf4732b5af143a541cf2f8c493780adda2002`、UTF-8大小514,147 bytes。该刷新仅为Git元数据维护，不构成claim-level验收或全库重算。

SERVO-710/714未完成，SERVO-713部分取证未完成；00-01/21-02保持进行中。未执行Ubuntu 24.04 apt/rosdep/colcon/Servo运行、VAL3、CS9/SRS、HIL/FAT/SAT或实机验证。Stäubli工业级验收仍未通过；未修改ICube上游；`TODO-EXT-001`仍未授权合并。


## 20. Build Farm Jenkins平台视图与候选job证据边界同步（2026-11-08追加）

本轮新增专项追加件§9.3.122、厂商档案§128.73。重新读取ROS Jazzy amd64/arm64规范状态页，页面生成时间04:36:03/04:43:04（-0800），moveit_servo版本仍为B/T 11月5/6日构建、M 10月6日旧构建。Build Farm当前`common.py`命名函数已重新核对；按源码推导Noble source候选`Jsrc_uN__moveit_servo__ubuntu_noble__source`、amd64 binary候选`Jbin_uN64__moveit_servo__ubuntu_noble_amd64__binary`、arm64 binary候选`Jbin_unv8_uNv8__moveit_servo__ubuntu_noble_arm64__binary`。本轮纠正此前arm64候选前缀遗漏`unv8`的简写。

Jenkins首页可见`Jsrc_uN`、`Jbin_uN64`、`Jbin_unv8_uNv8`平台视图入口；但moveit_servo具体job未出现在首页执行器/队列片段中，候选job页面、视图页面及API访问超时或拒绝。视图入口存在不证明包级job存在；候选名不证明job成功或失败。仍缺具体job配置、build number/result/timestamp/source revision/console log及import-package记录。

Build Farm release文档说明source job、binary job、building→testing sync criteria和testing→main人工sync流程；仅为流程语义证据。production main pool仍列10月6日amd64/arm64 deb（674,492/615,538 bytes）；本轮直接目录显示`.orig.tar.gz`大小65,705 bytes，纠正§9.3.120/§128.71此前记录65,707 bytes。未下载或校验源包内容。testing pool和Packages.gz本轮仍无法读取。

同步载体：
- 专项追加件新增§9.3.122；
- 厂商档案新增§128.73；
- 审计README更新索引；
- 第00章、第21章TaskPlan追加执行记录；
- 厂商档案资产清单行刷新为Blob SHA `a524a65e286b8127b6375407fc31d4d9a669957a`、UTF-8大小515,845 bytes，仅元数据维护，不代表claim-level验收。

SERVO-710/714未完成，SERVO-713部分取证未完成；00-01/21-02保持进行中。未执行Ubuntu 24.04 apt/rosdep/colcon/Servo运行、VAL3、CS9/SRS、HIL/FAT/SAT或实机验证。Stäubli工业级验收仍未通过；未修改ICube上游；`TODO-EXT-001`仍未授权合并。


## 21. 2026-11-08 ROS Jazzy双架构状态页刷新（§9.3.123）

本轮再次直接读取ROS官方Jazzy规范状态页并定位moveit_servo行：amd64页面生成时间刷新至2026-11-08 04:56:18 -0800，B/T仍为2.12.4-1noble.20261105.184638、M仍为2.12.4-1noble.20261006.040508；arm64页面仍为04:43:04 -0800，B/T仍为2.12.4-1noble.20261106.111556、M仍为2.12.4-1noble.20261006.043301。因此本轮只有amd64页面生成时间更新，没有观察到B/T/M版本变化或Main晋级。

专项追加件新增§9.3.123，厂商档案新增§128.74，审计README同步索引。Jenkins具体package job/build number/result/source revision/console log仍缺；APT InRelease/Packages正文及签名、deb control/SHA256/依赖闭包仍未取得。未执行目标Ubuntu 24.04安装运行、VAL3、CS9/SRS/HIL/FAT/SAT或实机验证；SERVO-710/714未完成，SERVO-713部分取证未完成，Stäubli工程级验收仍未通过，TODO-EXT-001仍未授权合并。

来源：
- https://repo.ros2.org/status_page/ros_jazzy_default.html
- https://repo.ros2.org/status_page/ros_jazzy_unv8.html
- 专项追加件§9.3.123。


## 21.1 厂商档案资产清单单行元数据刷新

因§128.74更新厂商档案后，已将资产清单中 knowledge/ecosystem/主要厂商.md 对应行刷新为Blob SHA 403007ce8e50dab4b3a2af3ddceebd7e63e5364a、UTF-8大小516,870 bytes。该操作仅刷新单一资产的Git元数据，不代表claim-level复核完成，也不代表其余资产行已重新计算。


## 22. 2026-11-08 MoveIt Servo Debian包装依赖映射与测试门控（§9.3.124）

新增静态核验：release repository的debian/jazzy/noble/moveit_servo分支HEAD为04da341a35a97633b11a95ac1600b1995bcbacc3（2025-12-05 20:45:20 UTC，unsigned）。debian/control的binary Depends模板与package.xml的25项depend/exec_depend逐项映射无缺项，另含ros-jazzy-ros-workspace和未展开的shlibs/misc占位符。debian/rules可在DEB_BUILD_OPTIONS=nocheck时关闭测试，且dh_auto_test || true会容忍测试失败继续打包；故状态页Binary Build/Testing不能作为测试通过证据。新增SERVO-715（静态映射已完成）和SERVO-716（真实job环境与日志未取得）。

该结果不等于实际deb内DEBIAN/control、签名/SHA256已验证，也不证明某次构建设置了nocheck或测试失败。Jenkins具体job/build number/result/source revision/console log仍缺；SERVO-710/713/714仍未完成或部分取证。未执行Ubuntu 24.04安装运行及VAL3/CS9/HIL/实机验证；Stäubli工程级验收仍未通过。

来源：
- https://github.com/ros2-gbp/moveit2-release/commit/04da341a35a97633b11a95ac1600b1995bcbacc3
- Debian control/rules/changelog/gbp.conf与package.xml：专项追加件§9.3.124。


## 22.1 厂商档案资产清单单行元数据刷新

因新增§128.75，资产清单中 knowledge/ecosystem/主要厂商.md 对应行刷新为Blob SHA 06c8d61a50aeaf9ca4e378e0207cc871224d1bec、UTF-8大小518,450 bytes。该操作仅刷新单一资产Git元数据，不代表claim-level复核完成，也不代表其余资产行已重新计算。


## 23. 2026-11-08 Debian测试门控精确行级复核（§9.3.125）

复核debian/rules与control的精确行号：rules第20–21行在DEB_BUILD_OPTIONS含nocheck时设置BUILD_TESTING=OFF；第47行定义override_dh_auto_test，第53行执行dh_auto_test || true；control第5行将ament-cmake-gtest、moveit-resources-panda-moveit-config、ros-testing等构建依赖标注<!nocheck>。这证明包装规则允许跳过测试或忽略测试命令失败，但不证明具体Build Farm构建实际走了哪条路径。SERVO-715已完成静态核验，SERVO-716仍需具体job环境与console log。

来源：moveit2-release debian/jazzy/noble/moveit_servo/debian/rules、debian/control；专项追加件§9.3.125。
