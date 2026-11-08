# Stäubli ICube ROS 2专项审查附录｜§9.3.102–§9.3.111

> 本文件是 `docs/audits/2026-11-06-staubli-robotics-ecosystem-review.md` 的追加件，延续其§9.3编号。主报告正文当前结束于§9.3.101；本附录承接根目录 `TaskPlan.md` v8.81–v8.82 的后续记录。这里仅补齐摘要性审计结论和已知边界，不替代每项验收任务所需的原始构建日志、签名元数据、实机记录或完整逐条来源审查。

固定项目基线：ICube `staubli_driver_ros2` commit `bd658e2d266e315d2ee35f985fb352ea88306b79`；目标发行环境声明为ROS 2 Jazzy / Ubuntu 24.04 Noble。MoveIt Servo供应链追溯对象为Jazzy `moveit_servo 2.12.4-1`。

## 9.3.102 CI、容器与可选Servo启动路径覆盖

固定ICube commit中，Servo仅在条件launch路径中启动；`launch_servo`默认false。CI采用`action-ros-ci@0.4.8`执行rosdep/build/test，但workflow没有显式启用Servo启动路径，也没有专门启动`servo_node`的集成测试；Dockerfile依赖manifest安装，未显式安装`moveit_servo`。这证明CI配置没有直接覆盖可选Servo路径，且manifest存在依赖声明缺口；不能进一步断言CI必然缺包或必然失败，因为基础镜像、环境预装和传递依赖可能掩盖缺口。

新增SERVO-673–SERVO-679。未做干净容器复现、rosdep依赖闭包验证、launch_servo双路径测试、servo_node smoke test、启动失败闭锁或CS9/HIL/实机验证。

## 9.3.103 ROS Jazzy发行版包可用性

核对ROS包状态/发行版资料，确认`moveit_servo`存在Jazzy发行记录，版本为`2.12.4-1`；该记录与ROS Index当前main/Rolling显示的2.15.2开发快照属于不同发行版/软件来源口径。不能用当前main分支或Rolling版本覆盖Jazzy生产二进制版本结论。

新增SERVO-680–SERVO-685。包状态页面仅证明发行版记录，不证明目标机器已能从其配置的生产APT源解析候选、下载、安装或运行。未执行目标Ubuntu 24.04/架构上的apt policy、rosdep resolve/install或servo_node启动验证。

## 9.3.104 Noble amd64/arm64构建工件索引

ROS Noble生产仓库及镜像索引可见`ros-jazzy-moveit-servo 2.12.4-1`对应amd64与arm64构建工件；索引快照时间为2026-10-06。不同目录/镜像缓存存在日期不一致，旧目录页不能覆盖较新的索引证据。当前只确认索引与pool中存在对应架构的构建工件，不推断APT候选、签名状态、依赖闭包或安装成功。

新增SERVO-686–SERVO-690。尚未取得完整Packages stanza、deb control元数据和校验值；也未安装、启动或运行Servo。

## 9.3.105 APT生产索引与二进制元数据证据边界

核对ROS Jazzy生产main与ros2-testing仓库路径，确认二者是不同仓库/快照，testing的较新时间戳不能替代生产main。生产pool目录继续提供2.12.4-1工件存在的线索，但本次访问未能读取完整Packages/Packages.gz记录；packages.ros.org端点访问失败，无法取得完整`Depends`、`SHA256`、`Filename`和版本修订字段，也未验证`InRelease`签名。

新增SERVO-691–SERVO-693。SERVO-710相关的生产APT签名、完整Packages stanza、deb SHA256及control元数据仍未完成。

## 9.3.106 MoveIt 2.12.4上游源码与包依赖/节点安装路径

固定MoveIt 2.12.4源码tag，核对`moveit_servo/package.xml`版本与声明运行依赖；同时从`CMakeLists.txt`核实`servo_node`目标已注册并安装到`lib/moveit_servo`。该源码侧证据说明上游tag包含目标节点和对应依赖声明；不等于ICube配置包已正确声明运行依赖，也不证明生产deb实际内容与源码tag逐字节相同。

SERVO-694–SERVO-696完成静态源码核对；新增SERVO-697–SERVO-699，尚未完成生产APT包元数据与目标系统验证。

## 9.3.107 Bloom发布记录与Jazzy release版本链

读取`ros2-gbp/moveit2-release`的release README，确认MoveIt Jazzy `2.12.4-1`发布记录日期为2025-12-05，release package list包含`moveit_servo`；发行记录与上游`moveit_servo`源码包版本2.12.4及ROS Noble生产pool中`2.12.4-1noble.20261006`构建修订形成版本对应线索。ROS Index的当前开发仓库摘要显示2.15.2，不可将其误读为Jazzy生产APT版本。

SERVO-700完成静态记录核对；SERVO-701–SERVO-703未完成。Bloom输入归档、生产APT签名、完整包元数据和构建日志仍待取得。

## 9.3.108 release README当前HEAD与历史发布提交区分

固定`ros2-gbp/moveit2-release`默认分支HEAD `ca9b116837bd3ed6b2de19772aeef8d5c2a82e95`，确认该提交仅新增2026-09-16 Rolling 2.15.2-1记录，不能作为2025-12-05 Jazzy 2.12.4-1发布的提交证据。该区分避免将README当前HEAD错误归因为某个旧发行版本的Bloom发布输入。

新增SERVO-704–SERVO-708。后续历史追溯已完成SERVO-704；SERVO-707/708仍待核验。

## 9.3.109 Jazzy release track与rosdistro合并记录

核对release track配置，确认MoveIt上游仓库、Jazzy分支、`last_version=2.12.4`及release tag模板；定位`ros/rosdistro#48887`，其于2025-12-06合并，merge commit为`91a0881369007a49a1df1cd8702183265bd3ac06`，将Jazzy distribution版本从2.12.3-1更新至2.12.4-1。

SERVO-705、SERVO-706完成静态核对；SERVO-707、SERVO-708及SERVO-711仍未完成。rosdistro合并记录不等同于Build Farm二进制构建成功或APT生产仓库签名验证。

## 9.3.110 release tag、README引入提交与Noble packaging关系

定位README首次引入Jazzy 2.12.4-1条目的提交`458a522d267a5bf75d324030a90ebe85154aa444`及父提交`f1eff8fa0ccc288de2d334b796ffb7dbb3e15b89`；父版本README不存在该条目，目标diff新增发布记录。解析MoveIt与moveit_servo release轻量tag，分别指向`3e353f0257928fe59d133a031395dfeb0fd3bc0d`与`517bafc0d687bd0863fb82ca53fdf792ecd3fc28`。MoveIt Servo的`package.xml`、`CMakeLists.txt`、`servo.cpp`与`servo_parameters.yaml`同上游2.12.4 tag相应文件blob一致。Noble Debian packaging branch的`gbp.conf`将upstream-tag指向moveit_servo release tag，changelog记录`2.12.4-1noble`。

SERVO-704与SERVO-709完成静态追溯；新增SERVO-712–SERVO-714。完整Bloom输入归档SHA、APT签名和deb包校验仍待执行。

## 9.3.111 上游源码树一致性与Build Farm任务追溯

完成release轻量tag commit tree与MoveIt上游2.12.4的`moveit_ros/moveit_servo`目录递归比较：双方均为54个tree条目/43个blob，tree未截断，路径、mode、type与blob SHA逐项一致，差异为0。该结果支持所比较源码子树完全一致，但不覆盖整个MoveIt多仓依赖集合、Bloom source archive、Noble packaging输入、构建环境或最终deb产物。

SERVO-712完成。查阅ROS 2 Build Farm官方job命名规则，并尝试访问Jenkins job/API，但未取得可核验的job索引、构建状态、source revision或console log。按官方模板推导出的`Jbin_uN64__moveit_servo__ubuntu_noble_amd64__binary`仅为Jazzy/Noble/amd64候选查询名，不证明该job真实存在或曾执行；arm64任务名和source job平台短码也未确认。SERVO-713已开始但未完成，SERVO-710及SERVO-714未完成。

ROS 2 Build Farm官方文档区分release source与binary job，并说明binary job由source job触发；命名模板与执行流程可用于定位候选任务，但必须取得实际Jenkins页面/API、job build number、result、source revision及完整console log后才能形成构建证据。

## 9.3.102–§9.3.111统一验收边界

本附录新增/追踪的SERVO任务仍以静态证据和动态验收分层管理。当前可以确认的是Jazzy发行记录、源码tag/commit关系、release README/rosdistro历史以及所比对源码子树一致性；当前不能确认的是：

- ROS生产APT签名有效、完整Packages stanza和deb control/SHA256与上游源码/packaging完全匹配；
- 目标Ubuntu 24.04 amd64/arm64机器解析到正确APT候选并完成安装；
- 干净环境rosdep/colcon构建、launch_servo=true/false、servo_node启动和运行参数有效值；
- ROS 2 Build Farm实际job的成功状态、source revision、构建日志和产物上传；
- VAL3编译、CS9/SRS、现场控制器、HIL/FAT/SAT或真实机器人安全/运动验证。

未修改ICube上游，未批准合并TODO-EXT-001。Stäubli仍未通过工业级验收。

## 9.3.112 ROS Jazzy官方状态页、building/testing/main工件与架构级发布链核验

### 1. ROS官方状态页的当前记录

本轮于2026-11-08读取ROS 2 Build Farm生成的Jazzy package status页面，确认`moveit_servo`发布版本仍为`2.12.4-1`。页面列出的三个仓库顺序为B/T/M；点击页面图例确认其分别指向`building`、`testing`和`main`。

| 目标 | 状态页快照 | building（B） | testing（T） | main（M） |
| --- | --- | --- | --- | --- |
| Ubuntu Noble amd64（N64） | 2026-11-08 03:56:07 -0800 | `2.12.4-1noble.20261105.184638` | `2.12.4-1noble.20261105.184638` | `2.12.4-1noble.20261006.040508` |
| Ubuntu Noble arm64（Nv8） | 2026-11-08 04:03:04 -0800 | `2.12.4-1noble.20261106.111556` | `2.12.4-1noble.20261106.111556` | `2.12.4-1noble.20261006.043301` |

来源：
- <https://repo.ros2.org/status_page/ros_jazzy_default.html>
- <https://repo.ros2.org/status_page/ros_jazzy_unv8.html>
- B/T/M仓库入口可由页面图例链接分别核验：<https://repo.ros2.org/ubuntu/building/>、<https://repo.ros2.org/ubuntu/testing/>、<https://repo.ros2.org/ubuntu/main/>

### 2. building与main目录中的实际deb工件

在官方仓库pool目录中直接读取到如下文件条目：

| 仓库 | 架构 | 文件名 | 大小 | 目录时间 |
| --- | --- | --- | ---: | --- |
| building | amd64 | `ros-jazzy-moveit-servo_2.12.4-1noble.20261105.184638_amd64.deb` | 673,950 bytes | 2026-11-05 18:58 |
| building | arm64 | `ros-jazzy-moveit-servo_2.12.4-1noble.20261106.111556_arm64.deb` | 617,952 bytes | 2026-11-06 11:29 |
| main | amd64 | `ros-jazzy-moveit-servo_2.12.4-1noble.20261006.040508_amd64.deb` | 674,492 bytes | 2026-10-06 04:18 |
| main | arm64 | `ros-jazzy-moveit-servo_2.12.4-1noble.20261006.043301_arm64.deb` | 615,538 bytes | 2026-10-06 04:45 |

来源：
- <https://repo.ros2.org/ubuntu/building/pool/main/r/ros-jazzy-moveit-servo/>
- <https://repo.ros2.org/ubuntu/main/pool/main/r/ros-jazzy-moveit-servo/>

这与状态页逐架构B/T/M版本相互吻合：两种架构的较新deb已进入building目录，状态页显示同版本也已进入testing；main目录仍只有2026-10-06的旧版本文件。浏览器读取器拒绝直接展开deb二进制，当前未读取deb control字段或计算SHA256。

### 3. 对Build Farm执行链的证据解释

ROS `ros_buildfarm`官方release job文档说明：
- source/binary release job负责创建源码包与二进制包；
- source/binary job完成上传后由`import-package`任务导入building仓库；
- 每个架构的所有binary job结束后，系统自动触发`sync-packages-to-testing`；只有满足sync criteria才会把building中的对应架构源码/二进制包同步到testing；
- `sync-packages-to-main`需手动触发。

参考：<https://github.com/ros-infrastructure/ros_buildfarm/blob/master/doc/jobs/release_jobs.rst>

因此，当前状态页及pool目录是比“只根据包版本推测job存在”更强的证据：它们显示amd64、arm64新版本均已进入building，且两种架构对应的同版本均已出现在testing；这支持两架构release binary产物已构建、导入并通过testing同步准入的结论。它仍不等于已取得Jenkins job result/console log，亦不代表功能运行、目标CS9适配或整机安全测试通过。

### 4. 按官方实现推导的架构级Jenkins job标识

`ros_buildfarm/common.py`中的`get_binarydeb_job_name`、`get_release_binary_view_name`和`get_short_arch`定义job命名；`amd64`缩写为`64`，`arm64`缩写为`v8`。对Jazzy/default/Noble目标的候选job标识为：

- amd64：`Jbin_uN64__moveit_servo__ubuntu_noble_amd64__binary`
- arm64：`Jbin_uNv8__moveit_servo__ubuntu_noble_arm64__binary`

参考源码：
- <https://github.com/ros-infrastructure/ros_buildfarm/blob/master/ros_buildfarm/common.py>
- <https://github.com/ros-infrastructure/ros_buildfarm/blob/master/ros_buildfarm/status_page.py>

本轮按上述view/job路径尝试打开build.ros2.org页面及API，仍未能取得Jenkins页面或JSON结果；未获得build number、job result、source revision、console log和各构建步骤详情。故上述两个标识是由官方实现确定的job名称/查询路径，不在本记录中冒充“已读取Jenkins构建详情”。

### 5. APT生产main与密码学验证边界

`repo.ros2.org/ubuntu/main/dists/noble/`目录列表显示`InRelease`（4,679 bytes）、`Release`（3,797 bytes）、`Release.gpg`（833 bytes）均标记为2026-10-06 09:01；`packages.ros.org/ros2/ubuntu/dists/noble/`目录检索结果同样显示2026-10-06 09:01的InRelease/Release/Release.gpg文件。当前可确认这些索引/签名文件名及目录时间，但网页读取器不支持展开这些二进制/签名内容，官方packages.ros.org索引下载也发生超时，因此：
- 未验证InRelease或Release.gpg签名；
- 未取得main生产仓库完整Packages/Packages.gz stanza；
- 未取得两种架构deb的SHA256、Filename、Size与Depends字段的完整APT记录；
- 未读取deb control元数据、未与上游源码/packaging生成关系做端到端哈希核验；
- 未在目标Ubuntu 24.04系统执行apt update、apt policy、apt install、rosdep、launch或servo_node运行。

### 6. SERVO任务状态更新

- **SERVO-713：部分取证取得，任务仍未完成。** 已确认building与testing均存在两架构的2.12.4-1新构建版本，并确定官方实现导出的两个Jenkins候选job名称；Jenkins job元数据、build number、source revision和console log仍缺。
- **SERVO-710：未完成。** 生产APT InRelease/Release签名验证、Packages stanza与deb SHA256/control元数据仍缺。
- **SERVO-714：未完成。** 新构建尚未进入main生产仓库；main仍显示amd64 `20261006.040508`、arm64 `20261006.043301`。最终生产APT包/源码/构建产物哈希对应关系未核验。
- 未修改ICube上游，未进行干净Jazzy安装/构建、VAL3、CS9/SRS、HIL/FAT/SAT或实机验证。Stäubli仍保持静态审查未验收状态。

## 9.3.113 2026-11-08最新ROS Jazzy状态页复核：生产main未晋级

### 1. 最新页面时间戳与逐架构状态

本轮重新读取ROS官方Jazzy status page，避免继续引用上一轮较早的快照：

| 页面 | 页面生成时间（页面本地时区 -0800） | Noble目标 | B（building） | T（testing） | M（main） |
| --- | --- | --- | --- | --- | --- |
| `ros_jazzy_default.html` | 2026-11-08 03:56:07 | amd64（N64） | `2.12.4-1noble.20261105.184638` | `2.12.4-1noble.20261105.184638` | `2.12.4-1noble.20261006.040508` |
| `ros_jazzy_unv8.html` | 2026-11-08 04:23:04 | arm64（Nv8） | `2.12.4-1noble.20261106.111556` | `2.12.4-1noble.20261106.111556` | `2.12.4-1noble.20261006.043301` |

### 2. 与生产main pool目录交叉核对

`repo.ros2.org/ubuntu/main/pool/main/r/ros-jazzy-moveit-servo/`当前目录仍只列出两份2026-10-06生产deb：
- amd64：674,492 bytes，目录时间2026-10-06 04:18；
- arm64：615,538 bytes，目录时间2026-10-06 04:45。

这与两份status page的M列版本相互吻合。没有发现2026-11-05 amd64或2026-11-06 arm64新构建进入生产main的证据。ROS官方状态页当前仍显示新构建处于B/T，不能将其描述为生产APT已发布或用户已可从main安装。

### 3. 当前审计判定

- SERVO-713：building/testing双架构构建证据保持成立；本轮最新状态复核未发现main晋级。Jenkins build number、job result、source revision、console log仍未直接取得，故部分取证、不完成。
- SERVO-714：仍未完成。main生产包继续是10月6日旧工件；未取得完整Packages stanza、deb control、SHA256及源码/二进制端到端对应证据。
- SERVO-710：仍未完成。InRelease/Release.gpg文件存在不等于签名已验证；Packages索引与签名原文仍无法读取。
- 未执行apt update/policy/install、干净Jazzy构建/launch、VAL3编译、SRS、CS9、HIL/FAT/SAT或实机验证；未修改ICube上游，TODO-EXT-001仍未授权合并。

### 4. 原始来源

- <https://repo.ros2.org/status_page/ros_jazzy_default.html>
- <https://repo.ros2.org/status_page/ros_jazzy_unv8.html>
- <https://repo.ros2.org/ubuntu/main/pool/main/r/ros-jazzy-moveit-servo/>
- 上述来源本轮读取时间：2026-11-08。页面可能继续更新，引用的时间戳是页面自身生成时间，不是本地查询时刻。


## 9.3.114 2026-11-08 ROS Jazzy APT索引目录快照复核：testing索引较新，生产main索引仍旧

### 1. 本轮新增的索引目录证据

| 仓库 | 架构/索引 | 目录时间 | 文件大小 |
| --- | --- | --- | ---: |
| ros2-testing | Jazzy Noble amd64 InRelease | 2026-11-06 13:15 | 4,679 bytes |
| ros2-testing | Jazzy Noble amd64 Packages | 2026-11-06 13:15 | 8,406,600 bytes |
| ros2-testing | Jazzy Noble arm64 InRelease | 2026-11-07 11:29 | 4,679 bytes |
| ros2-testing | Jazzy Noble arm64 Packages | 2026-11-07 11:29 | 8,381,795 bytes |
| ros2 production main | Jazzy Noble amd64 Packages | 2026-10-06 08:57 | 约7.9 MB（目录显示） |
| ros2 production main | Jazzy Noble arm64 InRelease/Packages | 2026-10-06 08:59 | InRelease 4,679 bytes；Packages约7.9 MB |

目录来源：
- ros2-testing lists：<https://repo.ros2.org/ubuntu/testing/lists/>
- ros2 production lists：<https://packages.ros.org/ros2/ubuntu/lists/>

testing目录快照日期比production main新约一个月；该证据与§9.3.113状态页B/T/M分离一致。目录时间和文件存在只证明仓库列表中有这些索引文件，不证明索引签名有效、包记录字段正确或deb可安装。

### 2. Packages/InRelease原文访问结果

尝试通过网页读取器打开testing amd64/arm64 Packages、production amd64 Packages及production InRelease原文。读取器对Packages与InRelease返回application/octet-stream不支持，arm64 Packages URL亦不可访问。因此本轮仍未取得可供逐字段复核的moveit_servo完整APT stanza，也没有对InRelease执行密码学验签。

本轮没有取得moveit_servo在amd64/arm64 Packages中的Version、Filename、Size、SHA256、Depends完整记录；没有下载deb并读取DEBIAN/control；没有使用ROS官方keyring执行gpgv/APT验证；没有在Ubuntu 24.04执行apt update、apt-cache policy、安装或servo_node启动。

不能把目录索引时间当作Packages记录的包版本，也不能把InRelease文件存在当作签名通过。

### 3. SERVO任务状态

- SERVO-710：仍未完成。APT签名验证、生产main Packages stanza、deb control/SHA256未取得。
- SERVO-713：仍为部分取证。building/testing双架构工件证据成立；本轮增加testing/production索引目录时间差证据，但Jenkins job/build number/source revision/console log仍未直接取得。
- SERVO-714：仍未完成。生产main索引快照与工件仍是2026-10-06版本，未完成最终deb/源码/构建产物一致性核验。
- 未修改ICube上游，未进行干净Jazzy安装/运行、VAL3编译、SRS、CS9、HIL/FAT/SAT或实机验证；TODO-EXT-001仍未授权合并。

### 4. 本节来源与读取边界

- ROS testing lists目录：<https://repo.ros2.org/ubuntu/testing/lists/>
- ROS production lists目录：<https://packages.ros.org/ros2/ubuntu/lists/>
- ros_buildfarm release job流程：<https://github.com/ros-infrastructure/ros_buildfarm/blob/master/doc/jobs/release_jobs.rst>
- 网页读取器对Packages/InRelease二进制内容的访问错误只说明本次读取通道不支持，不说明源文件损坏、签名无效或服务器拒绝APT客户端。

## 9.3.115 ROS 2 Build Farm release job命名复核与Jazzy状态页再确认（2026-11-08）

### 1. 由ros_buildfarm当前实现重新推导任务标识

本轮直接读取ros-infrastructure/ros_buildfarm的ros_buildfarm/common.py，核对以下实现：
- get_release_source_view_name()：source view前缀由ROS发行版首字母大写加src构成；Ubuntu Noble短码为uN。
- get_sourcedeb_job_name()：source job命名格式为{source_view}__{package}__{os}_{codename}__source。
- get_release_binary_view_prefix()：binary view前缀由发行版首字母大写加bin构成；release build名default映射为空后缀。
- get_release_binary_view_name()：将Ubuntu Noble与amd64/arm64分别缩写为uN64与uNv8。
- get_binarydeb_job_name()：binary job命名格式为{binary_view}__{package}__{os}_{codename}_{arch}__binary。

据此得到以下源码算法推导的候选标识：

| 类型 | 候选job标识 | 证据状态 |
|---|---|---|
| Jazzy source | Jsrc_uN__moveit_servo__ubuntu_noble__source | 由当前ros_buildfarm源码函数推导，尚未从Jenkins目录/API直接确认 |
| Jazzy amd64 binary | Jbin_uN64__moveit_servo__ubuntu_noble_amd64__binary | 同上 |
| Jazzy arm64 binary | Jbin_uNv8__moveit_servo__ubuntu_noble_arm64__binary | 同上 |

源码：https://github.com/ros-infrastructure/ros_buildfarm/blob/master/ros_buildfarm/common.py。ROS 2官方文档给出的release job通用格式及Rolling/Noble/amd64示例也与上述结构一致：https://github.com/ros2/ros2_documentation/blob/rolling/source/The-ROS2-Project/Contributing/Build-Farms.rst。

重要限制：命名算法只证明“如果按当前配置生成该job，其名称应如何构成”，不证明Jenkins上该job实际存在、曾执行或成功。尝试访问三个候选job的Jenkins /api/json端点时，当前读取通道返回不可访问；未取得job配置、build number、result、source revision、artifact fingerprint或console log。不得将候选标识写成已确认job。

### 2. ROS Jazzy官方状态页的最新可读快照

本轮重新打开两份官方状态页，页面自身生成时间仍分别为：

| 页面 | 页面生成时间（-0800） | moveit_servo B | T | M |
|---|---|---|---|---|
| Noble amd64 ros_jazzy_default.html | 2026-11-08 03:56:07 | 2.12.4-1noble.20261105.184638 | 2.12.4-1noble.20261105.184638 | 2.12.4-1noble.20261006.040508 |
| Noble arm64 ros_jazzy_unv8.html | 2026-11-08 04:23:04 | 2.12.4-1noble.20261106.111556 | 2.12.4-1noble.20261106.111556 | 2.12.4-1noble.20261006.043301 |

来源：https://repo.ros2.org/status_page/ros_jazzy_default.html；https://repo.ros2.org/status_page/ros_jazzy_unv8.html。

本轮快照没有显示main晋级：两架构main仍是2026-10-06版本。页面生成时间是页面自身时间戳，不等于本地查询时刻；不得把它描述为2026-11-08晚间的实时刷新。

### 3. 当前证据矩阵与SERVO任务状态

- SERVO-713：部分取证，仍未完成。已确认官方状态页B/T版本与先前building/testing工件证据一致；本轮进一步由ros_buildfarm源码精确推导source及两个架构binary job候选名。仍缺Jenkins直接job页面/API、build number、最终result、source revision和console log。
- SERVO-710：未完成。仍未验证生产main的InRelease/Release签名，未取得moveit_servo完整Packages stanza、SHA256/Depends/Filename/Size，也未读取deb的DEBIAN/control。
- SERVO-714：未完成。main仍是10月6日旧工件；未取得生产main最终deb的哈希及与源码、Bloom输入、Build Farm构建产物的端到端对应关系。
- 未执行Ubuntu 24.04目标环境的apt update/policy/install、rosdep、colcon、launch_servo=true/false或servo_node运行；未执行VAL3编译、CS9/SRS、HIL/FAT/SAT或实机验证。未修改ICube上游，TODO-EXT-001仍未授权合并。

### 4. 本轮读取边界

Jenkins API端点不可访问仅表示本轮读取通道未能取得页面/JSON，不证明job不存在或失败。状态页显示B/T版本一致可支持“该版本已进入building与testing仓库”的结论，但不能替代Jenkins执行日志、APT签名验证、包元数据核验或目标系统安装测试。Stäubli工程验收状态保持未通过。
## 9.3.116 ROS Jazzy状态页刷新与MoveIt Servo二进制池文件名/字节核对（2026-11-08）

### 1. 状态页刷新结果

本轮再次打开ROS官方Jazzy状态页并定位moveit_servo行。amd64页面的生成时间从上一轮03:56:07更新为04:36:03（-0800）；该行版本未变化：B=2.12.4-1noble.20261105.184638，T=2.12.4-1noble.20261105.184638，M=2.12.4-1noble.20261006.040508。arm64页面仍为04:23:04（-0800），版本仍为B/T=2.12.4-1noble.20261106.111556、M=2.12.4-1noble.20261006.043301。

来源：
- amd64状态页：https://repo.ros2.org/status_page/ros_jazzy_default.html（页面生成时间04:36:03；moveit_servo行）
- arm64状态页：https://repo.ros2.org/status_page/ros_jazzy_unv8.html（页面生成时间04:23:04；moveit_servo行）

状态页中B/T/M分别对应building/testing/main仓库。该证据支持两个架构新版本已进入building和testing，而生产main仍是10月6日旧版本；不能据此声称生产APT已晋级，也不能替代Jenkins job日志或APT客户端验证。

### 2. Binary pool文件名和大小交叉核对

本轮直接读取ROS官方building和production main的moveit_servo包目录索引，并点击deb条目以取得完整URL。目录证据如下：

| 仓库 | 完整deb文件名 | 目录修改时间 | 大小（bytes） |
|---|---|---|---:|
| building | ros-jazzy-moveit-servo_2.12.4-1noble.20261105.184638_amd64.deb | 2026-11-05 18:58 | 673,950 |
| building | ros-jazzy-moveit-servo_2.12.4-1noble.20261106.111556_arm64.deb | 2026-11-06 11:29 | 617,952 |
| production main | ros-jazzy-moveit-servo_2.12.4-1noble.20261006.040508_amd64.deb | 2026-10-06 04:18 | 674,492 |
| production main | ros-jazzy-moveit-servo_2.12.4-1noble.20261006.043301_arm64.deb | 2026-10-06 04:45 | 615,538 |

目录来源：
- building：https://repo.ros2.org/ubuntu/building/pool/main/r/ros-jazzy-moveit-servo/
- production main：https://repo.ros2.org/ubuntu/main/pool/main/r/ros-jazzy-moveit-servo/

本轮点击四个deb文件链接后，读取通道均因application/octet-stream不支持而无法展开二进制内容。故本节只确认目录列出的完整文件名、修改时间和字节大小；未读取deb控制信息，未计算或验证SHA256，也未验证包内二进制与Bloom源码/Build Farm source revision一致。testing pool目录请求未取得可读响应；testing仓库状态仍以官方状态页T列为证，不将building目录存在误写成直接读取了testing pool文件。

### 3. SERVO任务状态更新

- SERVO-713：继续为部分取证、未完成。新增证据：amd64状态页04:36刷新后B/T仍一致；两个架构building pool均列出完整deb文件名与大小；状态页T列对应相同版本。仍缺真实Jenkins job/build页面、build number、result、source revision、console log及testing池直接文件读取。
- SERVO-710：未完成。上游tag与Bloom记录已静态追溯，但未取得Bloom执行输入不可变revision/完整源归档SHA；本轮也未读取deb control或APT Packages完整记录，未验证InRelease签名和SHA256。
- SERVO-714：未完成。生产main pool仍仅列2026-10-06两架构旧deb；未取得生产main完整Packages stanza、签名验证结果、最终deb SHA256/control及其与源码/Build Farm产物的端到端关联。
- 未执行apt update/policy/install、rosdep、colcon、Servo launch/smoke test、VAL3编译、CS9/SRS、HIL/FAT/SAT或实机测试。未修改ICube上游，TODO-EXT-001仍未授权合并。

### 4. 证据边界与结论

状态页B/T/M列和pool目录列表属于仓库侧发布状态/文件存在证据；它们不证明客户端索引签名有效、APT候选选择正确、deb完整性或目标运行环境兼容。application/octet-stream读取失败是当前读取通道限制，不是deb损坏或签名失败的证据。当前结论保持：新版本在building/testing可见，production main未晋级，Stäubli工程级验收未通过。
## 9.3.117 ROS Jazzy testing/main APT索引目录时间戳交叉核验（2026-11-08）

### 1. Testing索引目录的双源交叉证据

本轮通过ROS官方testing lists目录检索结果及OSUOSL rsync镜像目录检索结果，重新取得Jazzy Noble APT索引文件的目录元数据。两处目录清单对关键文件名、修改时间及大小给出一致记录：

| 目标 | 索引文件 | 目录修改时间 | 大小 |
|---|---|---|---:|
| testing amd64 | ros-jazzy-noble-amd64_noble_InRelease | 2026-11-06 13:15 | 4,679 bytes |
| testing amd64 | ros-jazzy-noble-amd64_noble_main_amd64_Packages | 2026-11-06 13:15 | 8,406,600 bytes |
| testing arm64 | ros-jazzy-noble-arm64_noble_InRelease | 2026-11-07 11:29 | 4,679 bytes |
| testing arm64 | ros-jazzy-noble-arm64_noble_main_arm64_Packages | 2026-11-07 11:29 | 8,381,795 bytes |
| testing source | ros-jazzy-noble-source_noble_InRelease | 2026-11-07 11:28 | 4,679 bytes |
| testing source | ros-jazzy-noble-source_noble_main_Sources | 2026-11-06 13:09 | 10,217,787 bytes |

来源：
- ROS官方testing lists目录：https://repo.ros2.org/ubuntu/testing/lists/
- OSUOSL镜像目录：https://rsync.osuosl.org/pub/ros2-testing/lists/
- 当前检索返回的两处目录清单中，amd64、arm64、source索引文件名、时间和大小相互吻合。

注意：以上是目录清单元数据的交叉核验，不是Packages/InRelease文件正文下载。此前直接打开Packages/InRelease文件的网页读取器仍无法展示application/octet-stream内容；本轮容器下载尝试亦未成功。因此没有读取moveit_servo完整APT stanza，没有取得Version/Filename/Size/SHA256/Depends，也没有执行gpgv或APT签名验证。

### 2. Production main索引对照

ROS production main lists目录检索结果仍列出Jazzy Noble amd64 Packages于2026-10-06 08:57、arm64 InRelease/Packages于2026-10-06 08:59；amd64 InRelease目录条目时间为2026-10-06 08:57。与testing目录相比，testing amd64索引新约31天，arm64索引新约32天。此差异与§9.3.113–§9.3.116中status page B/T/M列及main pool仍为10月6日旧deb的观察一致。

来源：https://packages.ros.org/ros2/ubuntu/lists/。

索引文件的目录时间较新不等于其中某个包已被正确记录，也不等于签名有效或客户端可安装。testing索引快照不能替代production main索引。

### 3. Status page再次核验

重新打开ROS官方Jazzy状态页并定位moveit_servo行：

| 架构 | 页面生成时间（-0800） | B | T | M |
|---|---|---|---|---|
| amd64 | 2026-11-08 04:36:03 | 2.12.4-1noble.20261105.184638 | 2.12.4-1noble.20261105.184638 | 2.12.4-1noble.20261006.040508 |
| arm64 | 2026-11-08 04:23:04 | 2.12.4-1noble.20261106.111556 | 2.12.4-1noble.20261106.111556 | 2.12.4-1noble.20261006.043301 |

来源：https://repo.ros2.org/status_page/ros_jazzy_default.html；https://repo.ros2.org/status_page/ros_jazzy_unv8.html。

状态页时间戳未比§9.3.116更晚，故本轮将其作为重新确认而非更新快照。B/T/M版本未发生变化。

### 4. SERVO任务状态与证据分级

- SERVO-710：未完成。新增testing与production main索引目录时间/大小双源证据；Packages/InRelease正文、moveit_servo stanza、签名验证、deb control及SHA256仍未取得。
- SERVO-713：部分取证、未完成。testing索引目录元数据进一步证明Jazzy Noble双架构testing索引于11月6/7日更新；status page仍显示B/T新版本一致。Jenkins真实job配置、build number、result、source revision、console log仍未取得。
- SERVO-714：未完成。production main索引仍是10月6日快照，status page M列及main pool旧deb未变化；未取得最终生产包完整APT记录及哈希。
- 未执行目标Ubuntu 24.04 apt update/policy/install、rosdep、colcon、Servo launch/smoke test；未执行VAL3、CS9/SRS、HIL/FAT/SAT或实机安全验证。

### 5. 结论

当前可以确认的是：testing APT索引目录元数据较production main更新约一个月，且双架构testing status page仍显示新构建版本；production main仍未晋级。当前不能确认的是APT索引签名有效、moveit_servo完整包记录字段、deb哈希/内部control、Jenkins构建日志或目标机器安装运行结果。Stäubli工程级验收继续保持未通过。
## 9.3.118 Jazzy状态页时间戳与B/T/M发布阶段语义复核（2026-11-08）

### 1. 规范URL的当前可读快照

本轮直接打开ROS官方规范URL（不带筛选查询参数）并定位moveit_servo行：

| 页面 | 页面生成时间（-0800） | moveit_servo B | T | M |
|---|---|---|---|---|
| Jazzy amd64 default | 2026-11-08 04:36:03 | 2.12.4-1noble.20261105.184638 | 2.12.4-1noble.20261105.184638 | 2.12.4-1noble.20261006.040508 |
| Jazzy arm64 unv8 | 2026-11-08 04:23:04 | 2.12.4-1noble.20261106.111556 | 2.12.4-1noble.20261106.111556 | 2.12.4-1noble.20261006.043301 |

来源：https://repo.ros2.org/status_page/ros_jazzy_default.html；https://repo.ros2.org/status_page/ros_jazzy_unv8.html。

本轮搜索索引还返回带?q=RED筛选参数的arm64页面，标题时间为2026-11-07 18:03:03 -0800。该时间早于本轮规范URL直接读取的2026-11-08 04:23:04 -0800，因此不能将其描述为更新快照；打开该搜索结果时网页读取器又返回了2025年旧缓存，故不将其用于当前包版本判断。规范URL直接读取的2026-11-08快照是本轮状态页证据。

结论：两架构B与T列相同，M仍为10月6日旧版本。未观察到MoveIt Servo从testing晋级production main。

### 2. Build Farm发布流程语义约束

ROS ros_buildfarm官方release job文档说明：source release job由rosdistro distribution文件中的版本变化触发；binary job由对应source job触发；source job获取GBP仓库中包的tag及Ubuntu代号对应的打包信息并构建source package；binary job通过apt source获取source package后构建binary package；包上传导入目标仓库后，在全部job完成并满足sync criteria时，包才会由building同步到testing。

来源：https://github.com/ros-infrastructure/ros_buildfarm/blob/master/doc/jobs/release_jobs.rst。

该流程文档解释了B/T状态的阶段含义，但不能反向证明某个特定moveit_servo Jenkins job的实际result、源码revision、构建日志或sync判定。官方job文档也未提供本次审计所需的具体build number与console log。

### 3. APT原始文件读取边界复测

再次尝试读取ROS testing目录中的amd64 InRelease和Packages原始文件，网页读取器均因application/octet-stream不支持而拒绝展开。并尝试packages.ros.org的dists/noble/InRelease、binary-amd64/Packages.gz、binary-arm64/Packages.gz路径，以及ROS testing pool的moveit_servo目录；当前读取通道均未取得可解析正文。容器侧直连官方源及OSUOSL镜像下载亦失败。

ROS testing lists目录仍可检索到§9.3.117所记录的目录元数据：amd64 11月6日13:15、arm64 11月7日11:29。目录时间和大小是索引文件元数据，不是索引内容或签名校验结果。

production main包目录可读取的索引搜索结果仍列出旧deb：amd64 674,492 bytes、arm64 615,538 bytes，目录时间均为2026-10-06。来源：https://repo.ros2.org/ubuntu/main/pool/main/r/ros-jazzy-moveit-servo/。未取得testing目录中的对应新deb正文/哈希。

### 4. 本轮任务状态

- SERVO-710：未完成。仍缺InRelease正文、签名验证、Packages完整stanza、deb control与SHA256。
- SERVO-713：部分取证、未完成。已确认规范状态页B/T版本与release流程语义；具体Jenkins job API/页面在当前读取通道不可访问，未取得job存在性、build number、result、source revision和console log。候选job名称仍只是按命名规则推导，不作实际job存在证明。
- SERVO-714：未完成。B/T仍为新版本、M仍为旧版本；main pool旧deb目录证据与此一致。
- 未执行目标Ubuntu 24.04 APT签名/安装测试、rosdep、colcon、Servo launch/smoke test；未执行VAL3、CS9/SRS、HIL/FAT/SAT或实机安全验证。

### 5. 结论

本轮修正了状态页时间顺序的表述：带?q=RED的2026-11-07 18:03页面早于规范URL的2026-11-08 04:23快照，不能视为新版本快照。最新可直接读取的规范页面仍显示双架构B/T相同、M为10月6日旧版本。ROS Build Farm文档说明发布流水线阶段，但具体job运行证据仍缺。Stäubli工程级验收继续保持未通过。

## 9.3.119 Jazzy moveit_servo 2.12.4-1 的 rosdistro 与 release-source 对应关系核验（2026-11-08）

### 1. rosdistro 发布声明

读取 `ros/rosdistro` 仓库当前 `master` 上的 `jazzy/distribution.yaml`，定位 `moveit` release stanza：

- release repository：`https://github.com/ros2-gbp/moveit2-release.git`
- release version：`2.12.4-1`
- package list 明确包含 `moveit_servo`
- tag template：`release/jazzy/{package}/{version}`
- source repository：`https://github.com/ros-planning/moveit2.git`，source version 为 `main`
- 本次读取的 distribution.yaml Blob SHA：`9dba523bb0a975f9a36bd96440a406b4f1d14e1b`

按该模板展开，moveit_servo 对应的 release ref 为 `release/jazzy/moveit_servo/2.12.4-1`。GitHub Contents API 能从该 ref 读取 `README.md` 和 `package.xml`，因此该 ref 可解析；这属于release仓库ref与文件可读证据，不等于Build Farm某次构建成功。

### 2. 上游源码版本与release ref的文件级交叉核对

读取 `moveit/moveit2` 仓库 tag `2.12.4` 下的 `moveit_ros/moveit_servo/package.xml`，其内容声明包名 `moveit_servo`、包版本 `2.12.4`。再读取release ref `release/jazzy/moveit_servo/2.12.4-1` 根目录 `package.xml`，其Git Blob SHA与上游tag文件完全相同：

- 上游 `moveit/moveit2@2.12.4:moveit_ros/moveit_servo/package.xml`：`0f00c9ec3b85b0322b96124cd714cf9d280473fb`
- release ref `release/jazzy/moveit_servo/2.12.4-1:package.xml`：`0f00c9ec3b85b0322b96124cd714cf9d280473fb`

这证明两个定位点的package.xml文件字节内容相同；不把单文件相同扩大为整个源码树或Debian packaging完全相同。既有§9.3.111关于release tag与上游包子树的树级比较仍作为独立证据，不在本节重复推导。

### 3. Debian修订号与ROS包版本的区分

上游 `package.xml` 的软件包版本是 `2.12.4`；rosdistro release stanza与Bloom发布记录使用 `2.12.4-1`。后缀 `-1` 属于发行打包修订版本，不应误写成上游package.xml版本。release ref的名称也采用完整发行版本 `2.12.4-1`。

本轮未能从该release ref读取 `debian/changelog` 或 `debian/control`（对应路径返回404），因此没有取得该版本Debian源包修订内容、依赖控制字段或源包哈希。未据此推断其Debian packaging内容。

### 4. 证据分级与未闭环项

| 层级 | 本轮结果 | 证据边界 |
|---|---|---|
| rosdistro声明 | 已确认Jazzy release仓库、版本、包清单和tag模板 | 不证明构建结果 |
| release ref | `release/jazzy/moveit_servo/2.12.4-1`可读取 | 不证明Jenkins job成功 |
| 上游源码 | 上游tag 2.12.4的moveit_servo package.xml已读取 | 单文件比对不替代整个源码树审计 |
| release-source关联 | 两处package.xml Blob SHA完全相同 | 不证明Debian packaging、source package和binary package字节相同 |
| Build Farm | 仍无真实job配置、build number、result、source revision和console log | SERVO-713仅部分取证 |
| APT工件 | 仍未取得testing/main完整Packages stanza、InRelease签名验证、deb control与SHA256 | SERVO-710/714未完成 |

### 5. 任务状态

- SERVO-710：未完成。APT索引正文、签名验证、完整Packages stanza、deb control与SHA256仍缺。
- SERVO-713：部分取证、未完成。rosdistro声明、release ref及package.xml文件级关联已核实；真实Jenkins job/build记录仍缺。
- SERVO-714：未完成。production main是否晋级仍以状态页M列与main pool工件为准；本节未取得新晋级证据。
- 未执行Ubuntu 24.04 apt update/policy/install、rosdep、colcon、Servo运行测试；未执行VAL3、CS9/SRS、HIL/FAT/SAT或实机验证。
- Stäubli工业级验收仍未通过；ICube上游未修改；`TODO-EXT-001`仍未授权合并。

### 6. 来源

- https://github.com/ros/rosdistro/blob/master/jazzy/distribution.yaml
- https://github.com/ros2-gbp/moveit2-release/tree/release/jazzy/moveit_servo/2.12.4-1
- https://github.com/ros2-gbp/moveit2-release/blob/release/jazzy/moveit_servo/2.12.4-1/package.xml
- https://github.com/moveit/moveit2/blob/2.12.4/moveit_ros/moveit_servo/package.xml
- https://github.com/ros2-gbp/moveit2-release/blob/master/README.md


## 9.3.120 Jazzy状态页新快照与production main源包/二进制目录复核（2026-11-08）

### 1. 两架构状态页重新读取

再次直接打开ROS官方Jazzy规范状态页并定位`moveit_servo`行：

- amd64页面生成时间：2026-11-08 04:36:03 -0800；B/T均为`2.12.4-1noble.20261105.184638`，M为`2.12.4-1noble.20261006.040508`。
- arm64页面生成时间：本次读取为2026-11-08 04:43:04 -0800；B/T均为`2.12.4-1noble.20261106.111556`，M为`2.12.4-1noble.20261006.043301`。

与§9.3.118记录相比，arm64页面生成时间从此前记录的04:23:04更新为04:43:04，但moveit_servo的B/T/M版本字符串没有变化。页面更新时间变化不能解释为包版本变化或production晋级。两架构B/T均为新构建版本，M仍指向10月6日旧构建。

### 2. production main pool目录复核

直接打开ROS官方production main目录`https://repo.ros2.org/ubuntu/main/pool/main/r/ros-jazzy-moveit-servo/`，当前目录显示：

| 文件类型 | 目录显示文件名/版本 | 时间 | 大小 |
|---|---|---|---:|
| amd64 binary | `ros-jazzy-moveit-servo_2.12.4-1noble.20261006.040508_amd64.deb` | 2026-10-06 04:18 | 674,492 bytes |
| arm64 binary | `ros-jazzy-moveit-servo_2.12.4-1noble.20261006.043301_arm64.deb` | 2026-10-06 04:45 | 615,538 bytes |
| amd64 dbgsym | 对应20261006.040508构建 | 2026-10-06 04:18 | 30,362,802 bytes |
| arm64 dbgsym | 对应20261006.043301构建 | 2026-10-06 04:45 | 30,002,110 bytes |
| Debian source descriptor | `ros-jazzy-moveit-servo_2.12.4-1noble.dsc` | 2025-12-06 16:22 | 1,564 bytes |
| Debian packaging archive | `ros-jazzy-moveit-servo_2.12.4-1noble.debian.tar.xz` | 2025-12-06 16:22 | 16,152 bytes |
| upstream source archive | `ros-jazzy-moveit-servo_2.12.4.orig.tar.gz` | 2025-12-06 16:22 | 65,707 bytes |

目录中的production binary文件名与状态页M列的构建标识一致，构成状态页与main pool目录元数据的交叉印证。当前目录没有列出11月5/6日的B/T新构建二进制；不能据此推断testing pool不存在这些文件，因为本轮未成功读取testing pool包目录。

### 3. 源包内容读取尝试与边界

本轮尝试通过ROS官方目录和OSUOSL镜像读取`.dsc`、`.debian.tar.xz`及deb文件。网页读取器对官方二进制内容返回unsupported content-type；OSUOSL镜像的`.dsc`返回`text/prs.lines.tag`且未展开；容器下载尝试失败。故本轮只记录目录列出的文件名、时间和大小，不记录未经读取的SHA256、Files字段、Debian control/changelog内容，也不声称签名验证通过。

### 4. 当前结论与状态

- SERVO-710：未完成。仍缺可解析的APT InRelease/Packages正文、签名验证、完整Packages stanza、deb control与SHA256。
- SERVO-713：部分取证、未完成。rosdistro/release ref与package.xml文件级关联已确认；Build Farm真实Jenkins job、build number、result、source revision和console log仍缺。
- SERVO-714：未完成。两架构B/T仍为11月5/6日新构建，M及production main pool仍为10月6日构建；本轮没有观察到production晋级。
- 未执行目标Ubuntu 24.04 apt update/policy/install、rosdep、colcon、Servo launch/smoke test；未执行VAL3、CS9/SRS、HIL/FAT/SAT或实机验证。
- Stäubli工业级验收仍未通过；ICube上游未修改；`TODO-EXT-001`仍未授权合并。

### 5. 来源

- https://repo.ros2.org/status_page/ros_jazzy_default.html
- https://repo.ros2.org/status_page/ros_jazzy_unv8.html
- https://repo.ros2.org/ubuntu/main/pool/main/r/ros-jazzy-moveit-servo/
- https://rsync.osuosl.org/pub/ros2/pool/main/r/ros-jazzy-moveit-servo/


## 9.3.121 Debian源包可读性边界、发布记录与Jazzy状态页再核验（2026-11-08）

### 1. ROS官方状态页复核

重新打开ROS官方规范URL并定位`moveit_servo`：

| 架构 | 页面生成时间（-0800） | B | T | M |
|---|---|---|---|---|
| amd64 | 2026-11-08 04:36:03 | `2.12.4-1noble.20261105.184638` | 同B | `2.12.4-1noble.20261006.040508` |
| arm64 | 2026-11-08 04:43:04 | `2.12.4-1noble.20261106.111556` | 同B | `2.12.4-1noble.20261006.043301` |

与§9.3.120相比，两个页面生成时间及moveit_servo版本均未出现可确认的新变化。B/T仍为11月5/6日构建，M仍为10月6日构建。状态页目录索引所列HTML文件时间（00:16/00:23 UTC）与页面内生成时间显示格式不同，不将目录mtime误作新的包构建或页面内容版本。

### 2. Release仓库发布声明的交叉核验

重新检索`ros2-gbp/moveit2-release`公开仓库README，Jazzy的`moveit 2.12.4-1`发布记录列明`moveit_servo`在本次发布包清单中，并记载Bloom发布命令及版本从2.12.3-1更新至2.12.4-1。该证据与§9.3.119的rosdistro release stanza及release ref相互吻合，能证明发布批次声明和包名纳入关系。

该README不是Noble source/binary job运行日志，也没有给出本轮具体构建的Jenkins build number、source revision、console log、产物哈希或签名验证结果。不能据README推导二进制构建成功或生产仓库已晋级。

### 3. Debian源包文件读取尝试

本轮对以下地址分别尝试直接读取：

- ROS production main的`ros-jazzy-moveit-servo_2.12.4-1noble.dsc`
- OSUOSL镜像中的同名`.dsc`
- ROS testing pool中的同名`.dsc`
- ROS testing pool目录索引

结果：production main的`.dsc`被读取通道以`application/octet-stream`拒绝；OSUOSL镜像与testing地址未能访问；testing pool目录未返回可解析索引。此前main pool目录可见的`.dsc`、`.debian.tar.xz`、`.orig.tar.gz`文件名/时间/大小仍只是目录元数据。

因此本轮仍未取得源包的`Checksums-Sha256`、`Files`、`Format`、`Build-Depends`、签名状态或debian/rules/control/changelog正文。未计算或推测任何源包/二进制包哈希；未将访问失败解释为工件损坏、缺失或签名无效。

### 4. 证据链分层结论

| 证据层 | 当前结论 | 缺口 |
|---|---|---|
| rosdistro/Bloom发布声明 | 已核实moveit 2.12.4-1发布批次包含moveit_servo | 不等于具体构建执行记录 |
| release ref与上游包清单 | §9.3.119已核实package.xml文件级Blob一致 | 不等于Debian源包完整内容一致 |
| Debian source package | main pool目录曾列出dsc/debian.tar.xz/orig.tar.gz | 正文、签名、校验和、打包控制文件未取得 |
| Build Farm binary构建 | 状态页B/T显示双架构新版本 | Jenkins真实job、build number、result、source revision和console log缺失 |
| APT testing/main | 状态页T新、M旧；main pool旧deb与M匹配 | testing pool完整工件、Packages stanza、InRelease验签、deb control/SHA256缺失 |
| 目标环境与Stäubli适配 | 未完成 | Ubuntu 24.04安装/运行、VAL3/CS9/SRS/HIL/实机验证均未执行 |

### 5. 任务状态

- SERVO-710：未完成。APT索引正文、签名验证、完整Packages stanza、deb control与SHA256仍缺。
- SERVO-713：部分取证、未完成。发布声明、rosdistro/release ref和package.xml文件级关联已核实；真实Jenkins job/build记录仍缺。
- SERVO-714：未完成。状态页M与production main pool仍指向10月6日旧构建，未观察到晋级。
- 未执行Ubuntu 24.04 apt/rosdep/colcon/Servo运行测试；未执行VAL3、CS9/SRS、HIL/FAT/SAT或实机验证。
- Stäubli工业级验收仍未通过；ICube上游未修改；`TODO-EXT-001`仍未授权合并。

### 6. 来源

- https://repo.ros2.org/status_page/ros_jazzy_default.html
- https://repo.ros2.org/status_page/ros_jazzy_unv8.html
- https://repo.ros2.org/status_page/
- https://github.com/ros2-gbp/moveit2-release
- https://repo.ros2.org/ubuntu/main/pool/main/r/ros-jazzy-moveit-servo/
- https://repo.ros2.org/ubuntu/testing/pool/main/r/ros-jazzy-moveit-servo/
- https://rsync.osuosl.org/pub/ros2/pool/main/r/ros-jazzy-moveit-servo/


## 9.3.122 Build Farm Jenkins视图、job命名规则与当前发布状态复核（2026-11-08）

### 1. 当前ROS Jazzy状态页

本轮重新直接打开官方规范状态页并定位`moveit_servo`：

| 架构 | 页面生成时间（-0800） | B | T | M |
|---|---|---|---|---|
| amd64 | 2026-11-08 04:36:03 | `2.12.4-1noble.20261105.184638` | 同B | `2.12.4-1noble.20261006.040508` |
| arm64 | 2026-11-08 04:43:04 | `2.12.4-1noble.20261106.111556` | 同B | `2.12.4-1noble.20261006.043301` |

与§9.3.121相比，页面生成时间和`moveit_servo`构建版本未变化。B/T仍为11月5/6日构建，M仍为10月6日旧构建。该状态页给出包版本阶段快照，不提供Jenkins具体build number、source revision或console log。

### 2. Build Farm官方job命名规则复核

重新读取`ros-infrastructure/ros_buildfarm:master/ros_buildfarm/common.py`，核对函数：

- `get_sourcedeb_job_name()`：source job名称由source view、ROS包名、OS、codename组成。
- `get_binarydeb_job_name()`：binary job名称由release build view、ROS包名、OS、codename和架构组成。
- `get_release_source_view_name()` / `get_release_binary_view_name()`：分别决定source与binary view前缀。
- Noble缩写为`N`，Ubuntu缩写为`u`；amd64缩写为`64`，arm64缩写为`v8`；`default` release build name不追加后缀。

按当前官方命名实现推导，候选具体job应为：

| 类型 | 候选job名 | 推导边界 |
|---|---|---|
| Noble source | `Jsrc_uN__moveit_servo__ubuntu_noble__source` | source view不区分amd64/arm64 |
| Noble amd64 binary | `Jbin_uN64__moveit_servo__ubuntu_noble_amd64__binary` | default build view |
| Noble arm64 binary | `Jbin_unv8_uNv8__moveit_servo__ubuntu_noble_arm64__binary` | unv8 build view |

**更正此前简化记录：** arm64 binary候选的view前缀是`Jbin_unv8_uNv8`，不是`Jbin_uNv8`。此前候选名未作为真实job证据；本节给出按当前源码函数展开后的正确候选名。

### 3. Jenkins首页可见证据及其边界

本轮直接打开`https://build.ros2.org/`，Jenkins首页可读，显示以下视图入口：

- `Jsrc_uN`：Jazzy Ubuntu Noble source视图；
- `Jbin_uN64`：Jazzy Ubuntu Noble amd64 binary视图；
- `Jbin_unv8_uNv8`：Jazzy Ubuntu Noble arm64 binary视图。

首页的执行器/队列区也展示其他包在这些平台视图下的job活动，说明这些平台视图正在被Jenkins使用。但首页未显示`moveit_servo`具体job；本轮直接访问上述三个候选job页面、视图页面和API端点时，读取通道超时或拒绝访问。因此：

- **已核实：** Jenkins首页可见三个对应平台视图入口；Build Farm源码可推导候选job命名。
- **未核实：** `moveit_servo`三个具体job是否存在、job配置是否启用、是否曾触发。
- **未取得：** build number、result、timestamp、source revision、console log、上传工件路径和import-package记录。
- **不得推断：** 候选job存在或不存在、成功或失败；Jenkins首页未列出包名不是不存在证据。

### 4. Build Farm发布流程的证据含义

ROS Build Farm官方release job文档说明：source job从GBP release仓库tag取源码及OS-specific packaging信息，生成source package；binary job通过`apt source`获取source package并调用`apt-src build`生成binary package；产物进入building repository；满足sync criteria后自动从building同步到testing；testing到main的sync需人工触发。

因此，状态页B/T同版本只能证明状态页将相同版本显示在building/testing阶段；M仍为旧版本说明本轮未观察到production main晋级。它不替代source/binary job日志，也不等于目标机安装、Servo运行或Stäubli控制器兼容性验证。

### 5. Production main pool目录复核与大小更正

本轮重新直接读取production main pool目录，仍列出：

- amd64 deb：2026-10-06 04:18，674,492 bytes；
- arm64 deb：2026-10-06 04:45，615,538 bytes；
- amd64/arm64 dbgsym：分别30,362,802 / 30,002,110 bytes；
- `.dsc`：2025-12-06，1,564 bytes；
- `.debian.tar.xz`：2025-12-06，16,152 bytes；
- `.orig.tar.gz`：2025-12-06，**65,705 bytes**。

更正§9.3.120/§128.71中记录的`.orig.tar.gz`大小65,707 bytes：本轮直接目录读数为65,705 bytes，后续资产记录采用本轮可见目录值。该更正仅针对目录展示的文件大小，不表示已下载或校验源包内容。

ROS testing pool目录与直接Packages.gz URL本轮仍无法由读取通道访问。production main目录元数据仍与状态页M列10月6日构建对应；未取得testing具体二进制工件正文、APT stanza、InRelease签名验证或deb SHA256。

### 6. 任务状态与下一步

- SERVO-710：未完成。APT Packages/InRelease正文与签名、deb control、SHA256仍缺。
- SERVO-713：部分取证、未完成。发布声明、rosdistro/release ref、package.xml文件级关联、Build Farm命名源码和平台视图入口已核实；具体package job/build证据仍缺。
- SERVO-714：未完成。production main仍为10月6日旧构建，未观察到晋级。
- 未执行Ubuntu 24.04 apt/rosdep/colcon/Servo运行测试；未执行VAL3、CS9/SRS、HIL/FAT/SAT或实机验证。
- Stäubli工业级验收仍未通过；ICube上游未修改；`TODO-EXT-001`仍未授权合并。

### 7. 来源

- https://repo.ros2.org/status_page/ros_jazzy_default.html
- https://repo.ros2.org/status_page/ros_jazzy_unv8.html
- https://build.ros2.org/
- https://github.com/ros-infrastructure/ros_buildfarm/blob/master/ros_buildfarm/common.py
- https://github.com/ros-infrastructure/ros_buildfarm/blob/master/doc/jobs/release_jobs.rst
- https://github.com/ros2/ros2_documentation/blob/rolling/source/The-ROS2-Project/Contributing/Build-Farms.rst
- https://repo.ros2.org/ubuntu/main/pool/main/r/ros-jazzy-moveit-servo/
- https://repo.ros2.org/ubuntu/testing/pool/main/r/ros-jazzy-moveit-servo/


## 9.3.123 ROS Jazzy moveit_servo 双架构状态页刷新（2026-11-08）

### 1. 本轮直接读取的状态页快照

本轮重新打开ROS官方Jazzy规范状态页，并在页面内定位 moveit_servo 行：

| 架构 | 页面生成时间（-0800） | Building（B） | Testing（T） | Main（M） |
|---|---|---|---|---|
| amd64 | 2026-11-08 04:56:18 | 2.12.4-1noble.20261105.184638 | 与B相同 | 2.12.4-1noble.20261006.040508 |
| arm64 | 2026-11-08 04:43:04 | 2.12.4-1noble.20261106.111556 | 与B相同 | 2.12.4-1noble.20261006.043301 |

与§9.3.122相比，amd64页面生成时间从04:36:03刷新至04:56:18（-0800）；arm64仍为04:43:04。两架构的B/T/M版本字段均未变化。该快照继续显示B/T为11月5日和11月6日构建，而M仍指向10月6日旧构建；因此本轮未观察到 moveit_servo 进入production Main的新版本。

### 2. 证据范围与禁止推断

- 已直接核验：amd64与arm64官方状态页页面生成时间，以及 moveit_servo 的B/T/M版本字符串。
- 未核验：具体Jenkins package job配置、build number、result、构建时间、source revision、console log、上传工件指纹与import-package记录；§9.3.122中的job候选名仍只是按 ros_buildfarm/common.py 命名逻辑推导的候选。
- 本轮没有取得APT InRelease/Packages正文、moveit_servo完整Packages stanza、签名验证结果、.deb内DEBIAN/control、SHA256或依赖闭包。因此不得将状态页B/T条目等同于生产Main可安装性，也不得写成APT签名或二进制完整性已通过。
- 未执行Ubuntu 24.04目标环境的APT候选/安装、rosdep依赖解析、colcon构建或servo_node启动测试；未执行VAL3编译/仿真、CS9/SRS/HIL/FAT/SAT或实机测试。

### 3. 任务状态与后续门槛

- SERVO-710：未完成；Bloom执行输入的不可变源码revision/完整归档校验值仍缺。
- SERVO-713：部分取证、未完成；仍需取得moveit_servo实际Jenkins job/build证据和构建工件对应关系。
- SERVO-714：未完成；仍需取得生产Main APT签名、完整包记录、deb control/SHA256及依赖闭包。
- Stäubli工程级验收仍未通过；未修改ICube上游；TODO-EXT-001仍未授权合并。

### 4. 来源

- https://repo.ros2.org/status_page/ros_jazzy_default.html
- https://repo.ros2.org/status_page/ros_jazzy_unv8.html
- §9.3.122（Build Farm视图与候选job命名证据边界）


## 9.3.124 MoveIt Servo Jazzy Noble Debian packaging branch依赖映射与测试失败处理审查（2026-11-08）

### 1. 固定Debian packaging分支证据

通过GitHub REST提交历史读取release repository分支debian/jazzy/noble/moveit_servo，当前分支HEAD为04da341a35a97633b11a95ac1600b1995bcbacc3，提交时间2025-12-05 20:45:20 UTC，提交说明为Generated debian files for noble。GitHub提交验证字段为verified=false / unsigned；本轮不将其描述为已签名提交。

| 文件 | Git Blob SHA | 静态核验内容 |
|---|---|---|
| debian/control | 18376b30cd01762eeb8902dd1f9ec885f332fe62 | Build-Depends与二进制包Depends模板 |
| debian/changelog | 9f8356f7fa8fcc077349b5a65f923c8a5a6d33b6 | 顶部版本2.12.4-1noble，2025-12-04 23:00 UTC，记录class_loader warning修复 |
| debian/rules | f1664b24a5eaabf636fc54e391b022ab8dec99d2 | Debian dh build/test规则及测试容错行为 |
| debian/gbp.conf | 6cb989121b7dffb6295ef3632449059daadeee2d | upstream-tag=release/jazzy/moveit_servo/2.12.4-1；upstream-tree=tag |
| package.xml | 0f00c9ec3b85b0322b96124cd714cf9d280473fb | 上游ROS包的depend与exec_depend声明 |

gbp.conf将Noble Debian包装分支的上游源树指向MoveIt Servo release tag；changelog记录的二进制包装版本为2.12.4-1noble。此处固定的是当前可读取的Git分支与文件Blob，不等于已取得2025-12-05 Build Farm实际checkout的分支快照或上传工件来源证明。

### 2. Debian运行依赖模板与package.xml映射

- 从package.xml提取25项depend/exec_depend，并按ROS Debian包名规则映射为ros-jazzy-*；debian/control的二进制包Depends模板包含全部25项，无缺项。
- Debian Depends模板另包含ros-jazzy-ros-workspace，以及尚待实际构建时展开的${shlibs:Depends}和${misc:Depends}。因此当前核验是源码控制文件之间的静态映射，不是已下载二进制包的最终Depends结果。
- 此结果支持MoveIt Servo自身的Debian packaging运行依赖声明；它不补上Stäubli应用层staubli_moveit_config/package.xml对moveit_servo的显式exec_depend缺口，两者是不同的依赖边。

### 3. Debian测试规则中的非阻断行为

在debian/rules中发现：

1. 当DEB_BUILD_OPTIONS包含nocheck时，BUILD_TESTING_ARG被设置为-DBUILD_TESTING=OFF；同时debian/control中的部分测试Build-Depends使用<!nocheck>标记。
2. override_dh_auto_test目标执行的原始命令为dh_auto_test || true；该shell写法会忽略dh_auto_test的非零退出状态。文件中的echo注释也明确说明，即使测试失败，也不会取消构建。

因此，即使未来取得Build Farm的binary build成功记录，也不能仅凭该成功状态推断MoveIt Servo测试套件全部通过：测试可能因nocheck未启用，也可能执行后返回失败但未阻断Debian包构建。必须另取实际job环境中的DEB_BUILD_OPTIONS、console log和测试结果，才能判断测试是否运行及其结果。当前尚未取得这些job记录，本节不推断任何测试实际失败或实际被跳过。

### 4. 新增任务与证据边界

| 任务 | 验收对象 | 状态 |
|---|---|---|
| SERVO-715 | 固定Noble Debian packaging分支HEAD，核对control/changelog/rules/gbp.conf，并将package.xml 25项depend/exec_depend与Debian Depends模板逐项映射 | 已完成（仅静态Git文件核验；不代表实际deb字段或构建测试已验收） |
| SERVO-716 | 获取amd64/arm64实际Build Farm job环境与console log，确认DEB_BUILD_OPTIONS、测试是否执行、测试结果及失败是否被容错，并与B/T工件关联 | 未执行 |

SERVO-710仍未取得Bloom执行输入不可变revision/源归档SHA；SERVO-713仍未取得具体Jenkins job/build元数据及日志；SERVO-714仍未取得实际APT Packages stanza、InRelease签名、deb内DEBIAN/control与SHA256。未执行Ubuntu 24.04安装运行、VAL3/CS9/SRS/HIL/FAT/SAT或实机验证。Stäubli工程级验收仍未通过；未修改ICube上游；TODO-EXT-001仍未授权合并。

### 5. 来源

- https://github.com/ros2-gbp/moveit2-release/commit/04da341a35a97633b11a95ac1600b1995bcbacc3
- https://github.com/ros2-gbp/moveit2-release/blob/debian/jazzy/noble/moveit_servo/debian/control
- https://github.com/ros2-gbp/moveit2-release/blob/debian/jazzy/noble/moveit_servo/debian/changelog
- https://github.com/ros2-gbp/moveit2-release/blob/debian/jazzy/noble/moveit_servo/debian/rules
- https://github.com/ros2-gbp/moveit2-release/blob/debian/jazzy/noble/moveit_servo/debian/gbp.conf
- https://github.com/ros2-gbp/moveit2-release/blob/debian/jazzy/noble/moveit_servo/package.xml
- §9.3.119、§9.3.123。


## 9.3.125 Debian测试门控的精确行级复核与任务表闭环（2026-11-08）

### 1. 精确行级复核

重新读取固定分支 `debian/jazzy/noble/moveit_servo` 的 `debian/rules`、`debian/control` 和 `package.xml`，Blob SHA与§9.3.124记录一致。关键行号如下：

| 文件 | 行 | 原始规则/字段 | 审计含义 |
|---|---:|---|---|
| debian/rules | 20 | `ifneq ($(filter nocheck,$(DEB_BUILD_OPTIONS)),)` | 只有DEB_BUILD_OPTIONS包含nocheck时进入关闭测试的分支 |
| debian/rules | 21 | `BUILD_TESTING_ARG=-DBUILD_TESTING=OFF` | 通过CMake参数关闭BUILD_TESTING |
| debian/rules | 47 | `override_dh_auto_test:` | 覆盖debhelper默认测试目标 |
| debian/rules | 53 | `dh_auto_test || true` | 测试命令非零退出码被shell OR列表吞掉，不会单独令该recipe失败 |
| debian/control | 5 | Build-Depends中ament-cmake-gtest、moveit-resources-panda-moveit-config、ros-testing标注`<!nocheck>` | nocheck配置下这些测试相关构建依赖可不安装 |

### 2. 证据解释与边界

- `nocheck`关闭路径与`dh_auto_test || true`是两个独立的弱化门控：前者可不运行测试；后者意味着即使执行测试且测试命令返回非零，Debian测试目标也可能仍返回成功。
- 当前源码只证明规则允许上述行为；没有Build Farm实际job环境、完整命令行和console log，不能判断2026-11-05/06的具体amd64/arm64构建是否设置nocheck、是否运行测试、测试数量或结果。
- ROS状态页中的Building/Testing/Main是仓库阶段/包版本状态，不是测试套件通过报告。后续不得将其写成测试通过、覆盖率达标或Servo功能验证通过。
- `debian/control`的25/25运行依赖模板映射结果仍只针对源码模板；`${shlibs:Depends}`与`${misc:Depends}`需在实际deb control中展开后才能验证最终闭包。

### 3. 任务表闭环

21章验收任务表新增：

| 任务 | 验收对象 | 状态 |
|---|---|---|
| SERVO-715 | 固定Noble Debian包装分支，核对control/changelog/rules/gbp.conf并逐项映射package.xml的25项depend/exec_depend | 已完成（静态Git文件核验；不等于实际deb/构建测试验收） |
| SERVO-716 | 取得amd64/arm64真实Build Farm job环境和console log，核验DEB_BUILD_OPTIONS、测试是否执行、测试结果、失败容错及工件关联 | 未执行 |

SERVO-710、SERVO-713、SERVO-714维持原状态；不因本轮行级核验而提前关闭。下一步优先取得具体Jenkins job/build元数据和console log；若Build Farm日志不可读，则应明确记录访问限制，不以状态页替代。

### 4. 来源

- https://github.com/ros2-gbp/moveit2-release/blob/debian/jazzy/noble/moveit_servo/debian/rules
- https://github.com/ros2-gbp/moveit2-release/blob/debian/jazzy/noble/moveit_servo/debian/control
- https://github.com/ros2-gbp/moveit2-release/blob/debian/jazzy/noble/moveit_servo/package.xml
- §9.3.124。


## 9.3.126 ROS 2 Build Farm实际部署配置确认Jazzy release package tests被禁用（2026-11-08）

### 1. 固定实际部署配置分支及Jazzy架构映射

读取 `ros2/ros_buildfarm_config` 仓库README：`ros2` 分支是部署到 `https://build.ros2.org` 的实际配置分支；`master` 是测试farm配置分支。实际部署分支HEAD为 `e8ac988037437c0150a5e7a91cd80395cd1aea91`，提交时间2026-11-02 14:54:31 UTC；因此本轮配置快照早于ROS状态页所列的amd64 2026-11-05及arm64 2026-11-06 moveit_servo构建。

`index.yaml` 的Jazzy `release_builds`映射为：

| Build name | 配置文件 | 目标平台 | Git Blob SHA |
|---|---|---|---|
| `default` | `jazzy/release-build.yaml` | Ubuntu Noble amd64 | `254545a07c675442f55e737cc16a507b0c420bbe` |
| `unv8` | `jazzy/release-ubuntu-arm64-build.yaml` | Ubuntu Noble arm64 | `c81286a7af3205cd57af82d50b17b861f3fe1f14` |

两个文件的 `package_dependency_behavior` 均明确为：

```yaml
package_dependency_behavior:
  include_test_dependencies: false
  run_package_tests: false
```

所以两种架构的Jazzy release build配置均明确要求不引入测试依赖、不执行release package tests。该设置是整个Jazzy release build配置，而非moveit_servo单包的特殊覆盖。

### 2. 将部署配置追到Build Farm实际执行参数

核对 `ros-infrastructure/ros_buildfarm` master HEAD `9a6a04a84804ce1a1fc26c745cdbf604ee956efa`（2026-10-25 04:08:36 UTC）中的源码：

- `ros_buildfarm/release_job.py` 第770行：`'skip_tests': not build_file.run_package_tests`。当实际部署配置的 `run_package_tests: false` 时，生成的binary job参数为 `skip_tests: true`。
- `ros_buildfarm/binarydeb_job.py` 第128–134行：`skip_tests` 为true时，设置 `DEB_BUILD_OPTIONS` 追加 `nocheck`，并将 `DEB_BUILD_PROFILES` 追加 `nocheck`。
- 同文件第144–146行：以 `dpkg-buildpackage -b -us -uc -Pnocheck` 构建binary deb。
- `create_binarydeb_task_generator.py` 也按 `skip_tests` 给测试依赖求解增加 `nocheck` build profile；结合配置中的 `include_test_dependencies: false`，测试依赖不会作为该release build的正常构建依赖引入。

这将“实际部署配置run_package_tests=false”静态连接到“release job skip_tests=true”及“dpkg-buildpackage使用-Pnocheck”的代码路径。该证据比单独从debian/rules推断测试可能被跳过更直接。

### 3. MoveIt Servo 2.12.4测试目标影响

核对 `moveit/moveit2@2.12.4` 的 `moveit_ros/moveit_servo/CMakeLists.txt`（Blob SHA `6ec080d195798ba22e319def3da08c2e36a7d54f`）：第117行以 `if(BUILD_TESTING)` 包围测试配置；该块注册三个ament gtest目标：

1. `moveit_servo_utils_test`，源文件 `tests/test_utils.cpp`；
2. `moveit_servo_cpp_integration_test`，源文件 `tests/test_integration.cpp`；
3. `moveit_servo_ros_integration_test`，源文件 `tests/test_ros_integration.cpp`。

由于release job传入 `nocheck`，且Noble packaging `debian/rules` 第20–21行将 `BUILD_TESTING` 设为OFF，正常配置路径下不会进入这段CMake测试块；上述三个测试目标不会在该release binary build路径中构建/注册。对应测试文件在上游源码树中存在，但这不等于该发布包构建时执行了这些测试。

### 4. 证据边界与解释

- **已确认（静态配置/代码链）：** 实际部署配置分支README将 `ros2` 指定为build.ros2.org部署分支；该分支Jazzy amd64/arm64 release配置均 `run_package_tests:false` 和 `include_test_dependencies:false`；Build Farm源码将其转换为 `skip_tests:true`、`nocheck`环境/构建profile，并以 `-Pnocheck`运行dpkg-buildpackage；MoveIt Servo 2.12.4的三个CMake测试目标受 `BUILD_TESTING` 条件保护。
- **尚未取得：** 2026-11-05/06两个具体moveit_servo Jenkins job的生成XML、历史job配置快照、console log、build number与工件fingerprint。因此本轮不宣称已读取该两次构建日志，也不宣称检查了上游PR/devel/nightly CI是否在其他路径运行同一套测试。
- **结论限定：** ROS Jazzy正式release binary build配置本身明确禁用包测试；Building/Testing状态不能被称为MoveIt Servo单元/集成测试通过。上游其它CI或独立测试结果需要单独取证。
- `debian/rules`中的 `dh_auto_test || true` 是另一层容错规则；在 `nocheck` 和 `BUILD_TESTING=OFF` 的配置路径下，测试目标本身预期不会执行，故不应把该容错写成这两次具体构建中发生过测试失败。

### 5. 验收任务状态更新

| 任务 | 验收对象 | 状态 |
|---|---|---|
| SERVO-715 | Noble Debian包装文件与package.xml 25项depend/exec_depend静态映射 | 已完成（静态文件核验） |
| SERVO-716 | 获取2026-11-05/06 amd64/arm64具体Jenkins job XML、console log与构建工件关联 | 部分取证（实际部署配置已证明release package tests禁用；具体job实例日志/工件fingerprint仍缺） |
| SERVO-717 | 将实际部署的Jazzy default/unv8配置、release_job.py、binarydeb_job.py与MoveIt Servo 2.12.4的BUILD_TESTING测试目标形成可追溯静态证据链 | 已完成（配置文件、Build Farm代码及上游CMake条件均已固定；不替代job实例日志或CI测试结果） |

SERVO-710仍未取得Bloom执行输入源码revision/源归档SHA；SERVO-713仍未取得具体Jenkins job/build元数据和日志；SERVO-714仍未取得APT InRelease签名、完整Packages stanza、实际deb control/SHA256与依赖闭包。未执行Ubuntu 24.04安装/运行、VAL3/CS9/SRS/HIL/FAT/SAT或实机验证。Stäubli工程级验收仍未通过；未修改ICube上游；`TODO-EXT-001`仍未授权合并。

### 6. 来源

- https://github.com/ros2/ros_buildfarm_config/blob/ros2/README.md
- https://github.com/ros2/ros_buildfarm_config/blob/ros2/index.yaml
- https://github.com/ros2/ros_buildfarm_config/blob/ros2/jazzy/release-build.yaml
- https://github.com/ros2/ros_buildfarm_config/blob/ros2/jazzy/release-ubuntu-arm64-build.yaml
- https://github.com/ros2/ros_buildfarm_config/commit/e8ac988037437c0150a5e7a91cd80395cd1aea91
- https://github.com/ros-infrastructure/ros_buildfarm/blob/master/ros_buildfarm/release_job.py
- https://github.com/ros-infrastructure/ros_buildfarm/blob/master/ros_buildfarm/binarydeb_job.py
- https://github.com/moveit/moveit2/blob/2.12.4/moveit_ros/moveit_servo/CMakeLists.txt
- §9.3.124–§9.3.125。


## 9.3.127 MoveIt Servo 2.12.4上游GitHub Actions CI测试路径与实际运行记录（2026-11-08）

### 1. 上游CI工作流定义

固定上游 `moveit/moveit2@2.12.4`（commit `1ade0e9dcf50dbbbc3a984b995c786cf12736235`），其 `.github/workflows/ci.yaml` Blob SHA为 `9261e40b65ea161e801fc21b5f7ecdf97276aa63`。该工作流配置：

- 触发事件包括 `pull_request`、`merge_group`、`workflow_dispatch`，以及向 `jazzy` 分支的 `push`。
- CI job矩阵包括 `jazzy-ci + ccov` 和 `jazzy-ci + ikfast + clang-tidy` 两个配置；两个矩阵项均执行 `uses: ros-industrial/industrial_ci@master`。
- 工作流环境设置 `TARGET_CMAKE_ARGS` 为构建类型、编译警告和链接参数，没有设置 `BUILD_TESTING=OFF`；矩阵环境也没有设置 `NOT_TEST_BUILD=true`。

### 2. Industrial CI测试阶段的执行语义

核对与上游CI运行时间相容的 `ros-industrial/industrial_ci` 源码：其`master`在2025-12-05前最后相关基准提交为 `eb3ea328ff056aa2435d5b3493e7e2929c310f8e`（2025-09-11）。`source_tests.sh`、`env.sh`、`colcon.sh`对应Blob SHA分别为：

- `source_tests.sh`：`0936540e38453c385676e205654d22bc21fc30c9`
- `env.sh`：`81fe7f20396f050f0e56ff77f5438572cda58aec`
- `colcon.sh`：`7ca44096aaa52bd7843a9c3392d6dbc6d500f156`

相关执行逻辑：

1. `env.sh` 将 `NOT_TEST_BUILD` 默认设置为 `false`。
2. `source_tests.sh` 在 `NOT_TEST_BUILD != true` 时调用 `ici_test_workspace`，即默认不跳过target workspace测试。
3. `workspace.sh` 的测试阶段调用 `builder_run_tests`，随后调用 `builder_test_results`。
4. `colcon.sh` 对ROS 2使用 `colcon test`，并调用 `colcon test-result --verbose` 获取测试结果。
5. `ament_cmake_test-extras.cmake` 中 `option(BUILD_TESTING "Build the testing tree." ON)`，而该CI工作流没有覆盖此默认值。

因此，MoveIt 2.12.4上游GitHub Actions的industrial_ci CI路径没有像ROS release binary build那样显式禁用package tests；按工作流配置和runner默认逻辑，target workspace会进入colcon测试阶段。

### 3. MoveIt Servo测试注册关系

在 `moveit_ros/moveit_servo/CMakeLists.txt`（Blob SHA `6ec080d195798ba22e319def3da08c2e36a7d54f`）第117–146行，三个测试可执行目标和ROS测试入口都位于 `if(BUILD_TESTING)` 内：

| 可执行目标 | 对应ROS测试入口 |
|---|---|
| `moveit_servo_utils_test` | `tests/launch/servo_utils.test.py` |
| `moveit_servo_cpp_integration_test` | `tests/launch/servo_cpp_integration.test.py` |
| `moveit_servo_ros_integration_test` | `tests/launch/servo_ros_integration.test.py` |

所以在上述上游CI的默认测试配置中，这三个测试目标会被配置/注册到测试工作区；这与Jazzy release binary build使用 `nocheck` 并关闭 `BUILD_TESTING` 的路径不同。

### 4. 对应2.12.4源码提交的实际GitHub Actions运行

GitHub Actions API返回与上游2.12.4 commit SHA完全相同的运行记录：

- Run ID：`19975338753`；工作流名称 `CI`；事件 `push`；head SHA `1ade0e9dcf50dbbbc3a984b995c786cf12736235`。
- 创建时间：2025-12-05 20:37:49 UTC；结束时间：2025-12-05 21:35:56 UTC；整体结论 `success`。
- `jazzy-ci + ikfast + clang-tidy (delta)` job ID `57290019178`：`success`。
- `jazzy-ci + ccov` job ID `57290019180`：`success`。

该记录证明上游2.12.4源码提交的两项CI矩阵job整体通过。结合工作流和runner配置，CI没有选择跳过target workspace测试；但GitHub API在本轮没有提供逐测试测试报告，且运行未保存可下载的test-results artifact（工作流只在失败条件下上传该类artifact）。因此不将整体workflow成功伪装成三项Servo测试分别有独立的测试报告/逐用例证据，也不把它当作Jazzy Noble正式release deb测试。

### 5. 对§9.3.126结论的限定与任务状态

- §9.3.126的结论仍成立：ROS Build Farm Jazzy正式release binary build配置对Noble amd64/arm64均设置 `run_package_tests:false`，对应release二进制构建不运行MoveIt Servo这三个package tests。
- 本节补充另一条独立测试路径：MoveIt上游2.12.4 GitHub Actions CI通过industrial_ci默认运行target workspace测试；该SHA对应的整体CI矩阵已成功。
- SERVO-718：已完成（静态核对CI workflow、runner默认测试语义、CMake测试注册关系和同SHA运行记录）。
- SERVO-719：部分取证（已取得同SHA CI run与两项job成功记录；逐测试控制台输出/测试XML不可读或未归档，尚未取得三个测试入口各自的独立结果）。
- SERVO-716仍部分取证：release binary job的具体Jenkins XML/console log仍缺；SERVO-710/713/714保持未完成或部分取证。未执行Ubuntu 24.04实际apt安装、VAL3/CS9/SRS/HIL/FAT/SAT或Stäubli实机验证。Stäubli工程级验收仍未通过；未修改ICube上游；`TODO-EXT-001`仍未授权合并。

### 6. 来源

- https://github.com/moveit/moveit2/blob/2.12.4/.github/workflows/ci.yaml
- https://github.com/moveit/moveit2/actions/runs/19975338753
- https://github.com/ros-industrial/industrial_ci/blob/eb3ea328ff056aa2435d5b3493e7e2929c310f8e/industrial_ci/src/tests/source_tests.sh
- https://github.com/ros-industrial/industrial_ci/blob/eb3ea328ff056aa2435d5b3493e7e2929c310f8e/industrial_ci/src/env.sh
- https://github.com/ros-industrial/industrial_ci/blob/eb3ea328ff056aa2435d5b3493e7e2929c310f8e/industrial_ci/src/builders/colcon.sh
- https://github.com/ament/ament_cmake/blob/f91f816a51ad3c048d81b4115eece44c5a063137/ament_cmake_test/ament_cmake_test-extras.cmake
- https://github.com/moveit/moveit2/blob/2.12.4/moveit_ros/moveit_servo/CMakeLists.txt
- §9.3.126。


## 9.3.128 MoveIt Servo 2.12.4同SHA工作流全集与CI日志可用性复核（2026-11-08）

### 1. 同一源码SHA的全部Actions运行

针对上游源码commit `1ade0e9dcf50dbbbc3a984b995c786cf12736235`，通过GitHub Actions `workflow_runs?head_sha=...&per_page=100`检索到5个push运行，不能只看其中一个CI workflow：

| Run ID | 分支 | 工作流/运行结论 | 关键Job/检查 |
|---|---|---|---|
| `19975338753` | `jazzy` | `CI` success | `jazzy-ci + ccov` success；`jazzy-ci + ikfast + clang-tidy (delta)` success |
| `19975338722` | `jazzy` | 含source与release检查的运行，整体failure | `ci (jazzy)` success；`source (jazzy)` success；`release (jazzy)` failure |
| `19975338758` | `jazzy` | tutorial-source success | `tutorial-source (jazzy)` success |
| `19975338729` | `jazzy` | formatting检查 success | `Format` success |
| `19975338846` | `2.12.4` | Dockerfile lint success | ci/release/source/ci-testing四个Dockerfile lint均success |

这些是同一源码SHA的不同workflow/Job，不可把某一失败release job混同为CI矩阵失败，也不可把其他成功的lint/tutorial/source job当作三个Servo测试的逐项报告。提交check-runs共13项；其中与本审查直接相关的两个industrial_ci CI job仍是Run `19975338753`的两个成功矩阵job。`source (jazzy)`的整体job success只记录其job结论，不推断它对Servo三个测试入口的逐用例结果。

### 2. 原始日志与artifact追取结果

对Run `19975338753`的两个industrial_ci job（`57290019178`、`57290019180`）调用GitHub Actions job-log下载接口，均返回HTTP `410`；job-steps接口未返回可用步骤（空数组）。Run artifacts接口返回空列表。

进一步尝试同SHA其他可关联job：`source (jazzy)` job `57290439384`、`tutorial-source (jazzy)` job `57290019177`、`ci (jazzy)` job `57290019108`、`release (jazzy)` job `57290019125`。四个job日志下载接口同样返回HTTP `410`，job-steps接口均未返回可用步骤。

HTTP 410只说明当前GitHub日志下载接口已无法提供这些job日志；不能据此断言当年没有执行测试、测试失败或日志内容是什么。Run artifacts为空也只说明当前API没有列出可下载artifact，不代表历史测试没有产生过内部临时文件。

### 3. 对SERVO-719的结论与边界

- SERVO-718保持已完成：workflow、industrial_ci默认测试路径、ament默认开关、Servo CMake测试注册和同SHA成功CI运行的静态/元数据证据链已建立。
- SERVO-719保持部分取证：已证明同SHA两个CI矩阵job整体成功；已检索同SHA全部5个Actions runs并区分release job失败与CI矩阵成功；但两个关键CI job及其他相关job日志下载均HTTP 410，steps不可读，artifacts列表为空。三个Servo测试入口各自的colcon结果、测试XML和console log仍未取得。
- 不将`source (jazzy)` success等同于Servo测试逐项通过，也不将`release (jazzy)` failure解释成Servo测试失败；二者均缺少可读job日志来确认具体原因。
- §9.3.126正式release binary build关闭package tests的结论不变；§9.3.127上游industrial_ci默认进入colcon测试阶段的配置分析不变。CI运行整体成功不等于生产Noble APT包安装、CS9安全链或Stäubli实机验收。
- SERVO-716仍部分取证；SERVO-710/714未完成、SERVO-713部分取证。未执行Ubuntu 24.04安装运行、VAL3/CS9/SRS/HIL/FAT/SAT或实机验证；未修改ICube上游，`TODO-EXT-001`未授权合并，Stäubli工程级验收仍未通过。

### 4. 来源

- https://api.github.com/repos/moveit/moveit2/actions/runs?head_sha=1ade0e9dcf50dbbbc3a984b995c786cf12736235%26per_page=100
- https://api.github.com/repos/moveit/moveit2/commits/1ade0e9dcf50dbbbc3a984b995c786cf12736235/check-runs
- https://github.com/moveit/moveit2/actions/runs/19975338753
- https://github.com/moveit/moveit2/actions/runs/19975338722
- https://github.com/moveit/moveit2/actions/runs/19975338758
- https://github.com/moveit/moveit2/actions/runs/19975338729
- https://github.com/moveit/moveit2/actions/runs/19975338846
- §9.3.126–§9.3.127。


### 9.3.129 ROS Jazzy双架构状态页刷新与生产pool目录复核（2026-11-08）

#### 1. 官方状态页快照

重新直接打开ROS官方Jazzy Noble amd64与arm64规范状态页，并按`moveit_servo`精确定位行：

| 架构 | 状态页生成时间（UTC−8） | Building | Testing | Main |
|---|---|---|---|---|
| amd64 | 2026-11-08 05:56:04 | `2.12.4-1noble.20261105.184638` | `2.12.4-1noble.20261105.184638` | `2.12.4-1noble.20261006.040508` |
| arm64 | 2026-11-08 05:43:04 | `2.12.4-1noble.20261106.111556` | `2.12.4-1noble.20261106.111556` | `2.12.4-1noble.20261006.043301` |

与§9.3.128记录相比，amd64页面时间从04:56:18刷新至05:56:04，arm64页面时间从04:43:04刷新至05:43:04；两个架构的B/T/M版本字段均未变化。页面刷新只代表状态页生成时间更新，不代表重新构建、重新测试或版本晋级。本轮未观察到moveit_servo进入Main的新版本。

#### 2. 生产main pool目录

直接打开`ros-jazzy-moveit-servo`生产main pool目录，仍只列出与状态页Main列对应的2026-10-06 amd64/arm64二进制文件，目录大小分别为674,492 bytes和615,538 bytes；另列出2025-12-06的`.dsc`、`.debian.tar.xz`和`.orig.tar.gz`，其中`.orig.tar.gz`为65,705 bytes。未见2026-11-05/06新构建进入该生产目录。

该目录列表只能证明读取时目录列出的文件名、时间和字节大小；没有取得APT InRelease/Packages正文、签名校验结果、deb包内`DEBIAN/control`或SHA256，不能据此验收APT索引完整性、包依赖闭包或二进制内容。Building/Testing状态页也不是实际job日志或测试报告。

#### 3. 任务状态与后续取证边界

- SERVO-718保持已完成；SERVO-719保持部分取证：同SHA工作流/job状态已分层，但三个Servo测试入口逐项colcon结果、XML和console log仍未取得。
- SERVO-716保持部分取证、SERVO-713保持部分取证；具体Jenkins job实例、build number、source revision、console log和artifact fingerprint仍缺。
- SERVO-710仍未完成Bloom执行输入源码revision/源归档校验值闭环；SERVO-714仍未完成APT InRelease验签、完整Packages stanza、实际deb control/SHA256及依赖闭包验证。
- 未执行Ubuntu 24.04目标环境APT安装、rosdep解析、MoveIt Servo运行；未执行VAL3编译/SRS仿真、CS9、HIL/FAT/SAT或实机验证。Stäubli工程级验收仍未通过；未修改ICube上游；`TODO-EXT-001`仍未获授权合并。

#### 4. 来源

- ROS Jazzy amd64状态页：https://repo.ros2.org/status_page/ros_jazzy_default.html （页面生成时间05:56:04 -0800，`moveit_servo`第1175行）
- ROS Jazzy arm64状态页：https://repo.ros2.org/status_page/ros_jazzy_unv8.html （页面生成时间05:43:04 -0800，`moveit_servo`第1175行）
- ROS生产main pool目录：https://repo.ros2.org/ubuntu/main/pool/main/r/ros-jazzy-moveit-servo/
- §9.3.128及此前MoveIt Servo发布链追加记录。


### 9.3.130 MoveIt 2.12.4 PlanningSceneMonitor世界几何订阅停止缺陷（2026-11-08）

#### 1. 上游报告与固定版本源码

- 上游问题：`moveit/moveit2#3897`，标题为`stopWorldGeometryMonitor() leaves the PlanningSceneWorld subscription active`，创建于2026-09-29，状态仍为open。报告环境为ROS Jazzy、Ubuntu 24.04、MoveIt binary 2.12.4、FastRTPS。
- issue作者给出的复现步骤：同时启用CollisionObject与PlanningSceneWorld两个topic并分别发布消息；调用一次`stopWorldGeometryMonitor()`后，CollisionObject不再更新，但PlanningSceneWorld仍可替换受监控world；再次调用stop后第二个topic才停止。报告的单次stop路径3/3次复现，double-stop对照3/3次通过。这是上游issue作者报告的结果，本项目没有独立执行该复现。
- 固定MoveIt 2.12.4 tag解析到commit `1ade0e9dcf50dbbbc3a984b995c786cf12736235`。该版本`planning_scene_monitor.cpp`第1291–1316行分别创建两个独立subscriber：`collision_object_subscriber_`与`planning_scene_world_subscriber_`；第1339–1353行的stop实现先检查并reset collision subscriber，使用`else if`才检查/reset planning-scene-world subscriber。两个subscriber同时存在时，一次调用只会执行第一个分支，第二个subscriber保留。该静态源码结构与issue描述一致。
- 同一函数在`startWorldGeometryMonitor()`开始处先调用stop；它随后根据非空topic分别创建两类订阅。默认参数两类topic均非空，因此默认启动路径同时创建两个subscriber。需要注意：这证明默认API调用的订阅组合满足缺陷触发前提，不等于证明Stäubli应用所有运行状态都实际调用该函数、或已发生现场安全事件。

#### 2. 对Stäubli审查的影响

- 该缺陷位于MoveIt PlanningSceneMonitor世界几何监测层，不是Stäubli VAL3驱动或CS9安全功能本身。
- 如果Stäubli部署使用MoveIt 2.12.4、同时启用两个world-geometry输入，并在生命周期切换/关闭场景监测时只调用一次stop，则PlanningSceneWorld仍可能继续更新场景；调用方可能误以为监测已完全停止。对场景重置、感知输入切换、生命周期退出和测试清理均构成状态管理风险。
- 该问题与此前§9.3.99（MoveGroup/Servo Planning Scene同步）及§9.3.98（场景输入来源缺口）相关，但不是同一缺陷。不能据此直接推断碰撞检测必然漏检、机器人必然发生碰撞，亦不能把PlanningSceneMonitor stop语义等同于硬件急停/CS9安全停止。
- issue仍open且没有comments；本轮没有发现可引用的已合并修复或Jazzy 2.12.5二进制发布证据。另有MoveIt issue #3887（“jazzy release 2.12.5+”）仍open，描述Jazzy上次release为2025-12、建议发布后续bugfix；该issue不是#3897缺陷修复PR，也不能据此认定2.12.5已发布。

#### 3. 新增验收任务

- SERVO-720：固定MoveIt 2.12.4源码并核对issue #3897报告与stop/start实现——已完成（上游issue元数据、复现描述及源码分支结构静态对应）。
- SERVO-721：在目标Ubuntu 24.04/Jazzy二进制环境中，对两个订阅均启用时执行单次stop、double-stop、restart/stop重复调用，记录topic graph与回调计数——未执行。
- SERVO-722：核对Stäubli实际启动参数、PlanningSceneMonitor实例及所有start/stop调用点，判定缺陷触发条件是否成立；如条件成立，形成上游修复/版本升级或本地补丁评估——未执行。
- SERVO-723：在固定修复版本或经审查补丁上增加回归测试，覆盖两个订阅分别停止、重复stop、restart、空topic组合及octomap monitor停止语义——未执行。

#### 4. 状态边界

SERVO-720仅完成静态核验。SERVO-721/722/723未执行；未修改ICube上游、未修改MoveIt上游，也未应用本地补丁。MoveIt 2.12.4的风险作为条件性缺陷记录，Stäubli现场适用性仍待目标系统调用链确认。原SERVO-710/713/714/716/719状态不变；未执行VAL3/CS9/SRS/HIL/FAT/SAT或实机验证，Stäubli工程级验收仍未通过，`TODO-EXT-001`仍未授权合并。

#### 5. 来源

- 上游Issue #3897：https://github.com/moveit/moveit2/issues/3897
- 固定MoveIt 2.12.4源码：https://github.com/moveit/moveit2/blob/2.12.4/moveit_ros/planning/planning_scene_monitor/src/planning_scene_monitor.cpp
- 固定tag commit：https://github.com/moveit/moveit2/commit/1ade0e9dcf50dbbbc3a984b995c786cf12736235
- Jazzy后续发布跟踪Issue #3887：https://github.com/moveit/moveit2/issues/3887
- 关联既有审查：§9.3.98、§9.3.99、§9.3.129。


### §9.3.132 MoveIt #3897候选修复PR #3907状态、CI与Jazzy发行链复核（2026-11-08追加）

#### 1. 新发现的候选修复PR

- 本轮检索发现上游PR [#3907](https://github.com/moveit/moveit2/pull/3907)（标题：Preserve planning scene and request diagnostic contracts），PR描述明确列出`Fixes #3897`，涉及`PlanningSceneMonitor::stopWorldGeometryMonitor()`双订阅停止缺陷。
- PR当前状态为open、未合并，目标分支为`main`；head为`Yuhx141:fix/planning-scene-contracts`，head commit `821818f4ffeaa7564459faed2cbddbfb604f9dcb`，PR显示的base SHA为`a9004a43151b7d1fd50d462b8db6d4d280b0cc21`。不得把PR head或其diff当作上游main已包含的代码。
- 与本缺陷直接相关的diff把两个subscriber的reset改为无条件分别执行：先在任一subscriber存在时记录停止日志，随后分别reset `collision_object_subscriber_`和`planning_scene_world_subscriber_`，再沿用既有octomap monitor停止路径。
- PR新增`PlanningSceneMonitor.StopWorldGeometryMonitorStopsAllSubscriptions`测试：同时启动两个独立topic，调用一次stop，再通过`getMonitoredTopics()`验证两个topic均不再列出。已核对该函数会先clear输出vector，再根据当前subscriber成员重建列表，因此断言能反映两个subscriber成员已释放。该测试并未直接计数消息回调，也未覆盖重复stop/restart/空topic/octomap矩阵和Stäubli应用集成。
- PR描述自报在Ubuntu 24.04/ROS Jazzy、基于`a9004a4`执行了四项测试，其中包括新增的StopWorldGeometryMonitor测试。此为PR作者提供的测试记录，不能替代独立复测或上游required CI通过证明。

#### 2. PR审查与CI状态

- GitHub PR元数据仍为`state=open`、`merged=false`，没有已提交的review approval记录。
- PR head SHA的Actions元数据中，`Formatting (pre-commit)`与`CI`两条workflow run均为completed/failure。对应jobs接口返回`total_count=0`，当前无法取得具体失败job、步骤或日志；因此记录为工作流失败、原因未明，不推断是代码缺陷或基础设施故障。
- 同一head SHA的可见commit status只包含CodeRabbit success；它不是仓库维护者的review approval，也不能替代required CI。
- PR目标为main，当前没有证据表明该修复已合并或已进入Jazzy backport。Jazzy发布跟踪issue [#3887](https://github.com/moveit/moveit2/issues/3887)截至本轮仍open，评论显示仍在整理/合并多个可回移变更；不能据此认定#3907已经排入发布或已回移。

#### 3. 上游main与Jazzy正式二进制交叉验证

- 本轮重新读取MoveIt上游main的`planning_scene_monitor.cpp`，blob SHA为`83f67e15cb167957ddf15bde8fc239d053ed727c`。该文件的`stopWorldGeometryMonitor()`仍是`if (collision_object_subscriber_) ... else if (planning_scene_world_subscriber_)`，所以截至该源码快照，候选PR尚未进入main。
- ROS官方Jazzy amd64状态页（2026-11-08 05:56:04 -0800）中，`moveit_servo`的B/T为`2.12.4-1noble.20261105.184638`，M为`2.12.4-1noble.20261006.040508`；arm64状态页（05:43:04 -0800）中，B/T为`2.12.4-1noble.20261106.111556`，M为`2.12.4-1noble.20261006.043301`。
- ROS production main pool目录仍只列出2026-10-06构建的amd64/arm64 `ros-jazzy-moveit-servo` 2.12.4-1 deb（674,492/615,538 bytes）。当前没有2.12.5或能证明包含PR #3907的生产deb文件证据。B/T状态页构建号不能视作M生产发布。
- 因此发布链结论为：#3907是明确关联#3897的候选修复，但当前open/未合并；MoveIt main仍保留旧实现；Jazzy production binary仍为2.12.4-1；修复未被证明进入Jazzy正式包。

#### 4. 任务状态与处置边界

- SERVO-720：已完成（#3897与2.12.4源码静态对应）。
- SERVO-721：未执行（目标Ubuntu/Jazzy实验仍未运行；PR新增topic-list测试不是本项目复测）。
- SERVO-722：未执行/阻塞（ICube现场源码、launch/YAML、PlanningSceneMonitor实例及stop调用链仍缺）。
- SERVO-723：未执行（PR #3907是待合并候选，不是已确认修复版本；目标回归矩阵未运行）。
- SERVO-724：持续进行中（跟踪#3907审查/CI/合并、Jazzy backport、正式deb版本及校验材料）。

本轮仅读取上游PR与官方发行状态，没有向MoveIt/ICube提交代码或补丁，没有把double-stop作为规避措施。未在目标机执行测试；VAL3、CS9、SRS、HIL、FAT/SAT及实机验证均未执行，Stäubli工程级验收仍未通过。

来源：
- https://github.com/moveit/moveit2/issues/3897
- https://github.com/moveit/moveit2/pull/3907
- https://github.com/moveit/moveit2/issues/3887
- https://github.com/moveit/moveit2/blob/main/moveit_ros/planning/planning_scene_monitor/src/planning_scene_monitor.cpp
- https://repo.ros2.org/status_page/ros_jazzy_default.html
- https://repo.ros2.org/status_page/ros_jazzy_unv8.html
- https://repo.ros2.org/ubuntu/main/pool/main/r/ros-jazzy-moveit-servo/


### §9.3.131 MoveItCpp默认启动路径、上游修复追踪与Stäubli调用链证据边界（2026-11-08追加）

#### 1. 上游默认调用路径与当前修复状态

- 固定读取MoveIt上游当前main的`moveit_ros/planning/moveit_cpp/src/moveit_cpp.cpp`。`MoveItCpp::initialize()`在PlanningScene配置成功后依次启动state monitor、发布PlanningScene、启动scene monitor，并调用`planning_scene_monitor_->startWorldGeometryMonitor()`。这是MoveItCpp通用默认初始化路径，不是Stäubli专有集成证据，也不能证明现场实际采用MoveItCpp或未覆写生命周期管理。
- 读取当前main的`planning_scene_monitor.cpp`，`stopWorldGeometryMonitor()`仍按`if (collision_object_subscriber_) reset(); else if (planning_scene_world_subscriber_) reset();`处理两个subscriber。两个subscriber同时存在时，单次调用仍只释放第一个分支对应的subscriber；本轮未观察到当前main已消除该问题。
- GitHub issue search针对`repo:moveit/moveit2 is:pr stopWorldGeometryMonitor`返回0条匹配PR；上游issue #3897仍open。此搜索范围不构成所有历史/草稿/未公开PR的绝对穷尽，不据此断言后续不会修复。

#### 2. Stäubli现场调用链证据边界

- `robot_knowledgebasement`当前main树没有ICube应用源码、Stäubli MoveIt集成包、launch/YAML启动参数、目标PlanningSceneMonitor构造点或stop调用点；现有审计文档也未提供这些部署证据。
- 因缺少目标ICube版本/commit、脱敏启动配置、应用层monitor创建与start/stop代码、启停时topic graph和日志，无法确认实际是否采用MoveItCpp默认路径、两个topic是否同时非空、是否存在额外monitor实例、stop是否只调用一次，以及停止后PlanningSceneWorld是否仍收到消息。
- 因此SERVO-722维持**未执行/阻塞**。本轮完成的是知识库证据范围盘点和上游通用路径核验，不是Stäubli现场调用链验收。证据缺失既不能解释为现场受影响，也不能解释为现场不受影响。

#### 3. SERVO-721最小可复现实验规程（已整理，未执行）

在与目标一致的Ubuntu 24.04、ROS Jazzy、MoveIt 2.12.4环境中，使用隔离节点/namespace和可观测的消息计数：

1. 配置非空CollisionObject与PlanningSceneWorld topic，确认两类消息在stop前均能增加各自回调计数。
2. 调用一次`stopWorldGeometryMonitor()`，持续向两个topic发布新消息；记录两个回调计数、ROS graph和日志。预期修复行为是两个计数均不再增加。
3. 在独立进程重复单次stop实验与double-stop对照，避免前一轮残留订阅污染后一轮结果；double-stop只用于复现对照，不作为修复或现场规避方案。
4. 覆盖restart→stop、仅CollisionObject topic、仅PlanningSceneWorld topic、两个topic均为空，以及octomap monitor启停组合；记录进程退出码、ROS发行版、MoveIt包版本和RMW。
5. 修复验收必须证明单次stop即可释放两个subscriber，并运行相关PlanningSceneMonitor/MoveIt Servo回归测试；不得仅凭节点仍存在或topic graph端点变化作结论。

本轮没有目标Ubuntu/Jazzy执行环境，未运行上述实验；SERVO-721仍未执行。SERVO-723尚无确认修复PR/修复版本，回归测试未执行。

#### 4. 任务状态与边界

- SERVO-720：已完成（固定2.12.4 issue/源码静态对应）。
- SERVO-721：未执行（实验规程已整理）。
- SERVO-722：未执行/阻塞（Stäubli目标源码、部署参数和调用链缺失）。
- SERVO-723：未执行（无确认修复版本/补丁，未运行回归矩阵）。
- SERVO-724：新增持续跟踪项，跟踪#3897修复PR、Jazzy backport和正式发行二进制版本；只有取得明确修复commit、分支合并及发行包证据后才更新修复状态。

未修改ICube或MoveIt上游，未应用本地补丁，未将double-stop作为现场规避措施。VAL3、CS9、SRS、HIL、FAT/SAT及实机验证仍未执行，Stäubli工程级验收仍未通过。

#### 5. 来源

- https://github.com/moveit/moveit2/issues/3897
- https://github.com/moveit/moveit2/pulls
- https://github.com/moveit/moveit2/blob/main/moveit_ros/planning/moveit_cpp/src/moveit_cpp.cpp
- https://github.com/moveit/moveit2/blob/main/moveit_ros/planning/planning_scene_monitor/src/planning_scene_monitor.cpp
- 固定2.12.4源码与issue复现详见§9.3.130。


### §9.3.133 PlanningSceneMonitor停止与重启配置切换的生命周期边界（2026-11-08追加）

#### 1. 固定2.12.4源码调用路径

本轮从MoveIt 2.12.4固定版本的`planning_scene_monitor.cpp`逐一核对三个生命周期函数，文件Blob SHA为`fd07db53761d533f2f6e7f33189063a18000c9a9`：

- `PlanningSceneMonitor::~PlanningSceneMonitor()`在析构体中调用一次`stopWorldGeometryMonitor()`，随后完成executor和场景对象清理；析构体结束后类成员会按C++对象生命周期销毁。因此本缺陷不应描述成“对象析构后仍永久残留订阅”。本轮未发现证据支持该扩大结论。
- `startWorldGeometryMonitor()`开头无条件调用`stopWorldGeometryMonitor()`，之后仅在传入topic字符串非空时创建对应subscriber。
- `stopWorldGeometryMonitor()`仍使用`if (collision_object_subscriber_) ... else if (planning_scene_world_subscriber_)`。当两个subscriber同时存在时，一次调用先释放CollisionObject，PlanningSceneWorld仍保留。

#### 2. 重启配置切换的条件性缺陷

上述调用关系带来一个比单次显式stop更具体的配置切换场景：

1. 初始以非空CollisionObject和PlanningSceneWorld两个topic启动monitor。
2. 再次调用`startWorldGeometryMonitor()`切换配置。函数开头的stop只释放CollisionObject subscriber，旧PlanningSceneWorld subscriber仍在。
3. 若新配置的`planning_scene_world_topic`为空，后续创建阶段不会给`planning_scene_world_subscriber_`赋新值，旧subscriber就可能在重启调用返回后继续留存并接收旧topic消息。
4. 如果新配置的两个topic都非空，旧PlanningSceneWorld subscriber会在后续赋值新subscriber时被替换；这是不同分支，不能与“禁用world topic后旧订阅残留”混为一谈。
5. 若直接调用stop且PlanningSceneMonitor对象继续存活，旧PlanningSceneWorld subscriber会保留；若随后对象析构，剩余成员会随对象结束生命周期销毁。

因此本轮将风险精确限定为：当原配置同时启用两个subscriber，且调用stop或重启为`planning_scene_world_topic=""`的配置时，monitor对象仍存活期间可能保留旧PlanningSceneWorld订阅。是否在Stäubli部署中发生，仍取决于实际topic配置及生命周期调用，当前没有现场证据。

#### 3. SERVO-721/725扩展实验矩阵（均未执行）

在固定Ubuntu 24.04/ROS Jazzy/MoveIt 2.12.4环境中，以隔离namespace和唯一topic名执行：

| 初始配置 | 操作 | 期望保留的topic |
|---|---|---|
| CollisionObject + PlanningSceneWorld | 直接调用stop一次 | 无 |
| CollisionObject + PlanningSceneWorld | restart为仅CollisionObject | 新CollisionObject |
| CollisionObject + PlanningSceneWorld | restart为仅PlanningSceneWorld | 新PlanningSceneWorld |
| CollisionObject + PlanningSceneWorld | restart为两个topic均为空 | 无 |
| CollisionObject + PlanningSceneWorld | restart为两个新topic | 两个新topic，不包含旧topic |
| 仅CollisionObject | stop后保持对象存活 | 无 |
| 仅PlanningSceneWorld | stop后保持对象存活 | 无 |
| 任意上述配置 | 对同一monitor重复stop | 无，且无异常 |

每个场景应在操作后通过`getMonitoredTopics()`比对实际topic集合，同时分别发布带递增标识的旧topic和新topic消息，核对旧topic回调停止、新topic回调只在对应订阅存在时增长。保留ROS graph、回调计数、日志、测试退出码和包版本。PR #3907现有测试只覆盖“双topic启动→单次stop→topic列表双路移除”这一用例；本扩展矩阵尚未由本项目执行。

SERVO-725作为新任务跟踪重启配置切换的显式验证。它是由固定2.12.4源码直接推导的测试需求，不是已经复现的动态故障，也不是Stäubli现场风险确认。

#### 4. 修复审查与边界

PR [#3907](https://github.com/moveit/moveit2/pull/3907)把两个subscriber都改为无条件reset，因此从静态代码结构上覆盖了直接stop和start开头调用stop的双订阅场景。但PR仍open/未合并；其作者自报测试不等于本项目测试。其topic-list测试不能替代上表所有生命周期切换及回调计数矩阵。

未修改MoveIt/ICube上游，未应用补丁；未在目标环境运行实验。SERVO-721、SERVO-723、SERVO-725均未执行；SERVO-722仍因Stäubli现场源码和部署配置缺失而阻塞；SERVO-724继续跟踪PR与Jazzy发布链。VAL3、CS9、SRS、HIL、FAT/SAT和实机验证未执行，Stäubli工程级验收仍未通过。

来源：
- https://github.com/moveit/moveit2/blob/2.12.4/moveit_ros/planning/planning_scene_monitor/src/planning_scene_monitor.cpp
- https://github.com/moveit/moveit2/pull/3907
- https://github.com/moveit/moveit2/issues/3897
- 固定2.12.4源码Blob SHA：`fd07db53761d533f2f6e7f33189063a18000c9a9`。


### §9.3.134 MoveIt PR #3907审查阻塞、Jazzy backport缺口与发布状态复核（2026-11-08追加）

#### 1. PR状态与代码内容

- 重新读取上游PR [#3907](https://github.com/moveit/moveit2/pull/3907)：仍为open、未合并，base为`main`，head为`Yuhx141:fix/planning-scene-contracts`，head SHA `821818f4ffeaa7564459faed2cbddbfb604f9dcb`；PR元数据`updated_at=2026-09-30T18:09:48Z`，`mergeable_state=behind`。即PR分支落后于目标main，需要更新后再评估；这不等同于存在冲突。
- 与#3897直接相关的源码diff把`stopWorldGeometryMonitor()`改为分别无条件reset `collision_object_subscriber_`与`planning_scene_world_subscriber_`，从静态实现上解决双订阅单次stop只释放一个的问题。
- PR新增`PlanningSceneMonitor.StopWorldGeometryMonitorStopsAllSubscriptions`：双topic启动后调用一次stop，再用`getMonitoredTopics()`确认两个topic均被移除。该测试覆盖subscriber/topic列表释放，不直接验证消息回调计数，也未覆盖restart切换到空topic、重复stop和octomap生命周期矩阵。
- PR作者描述自报Ubuntu 24.04/ROS Jazzy下四项测试通过（包含新增测试），测试基线为`a9004a4`。该信息是作者声明，不是本项目独立复测或维护者required CI通过证据。

#### 2. Review与CI证据

- `pulls/3907/reviews`返回空列表，没有提交的review approval。
- 针对head SHA查询Actions workflow runs，`Formatting (pre-commit)`（run `36755746603`）与`CI`（run `36755746261`）均为completed/failure；两者jobs接口当前均返回`total_count=0`，未能取得具体失败job、step或日志，失败原因未知。
- 同一head SHA的check-runs中Mergify Summary与WIP为success、Mergify Merge Queue为neutral；commit status中CodeRabbit为success。这些辅助状态不能覆盖Formatting/CI workflow failure，也不是维护者review approval。
- PR目前仍behind，未发现该PR在目标main上的新head或成功required CI证据；不得把PR作者自报测试视为合并门禁通过。

#### 3. Jazzy回移与正式发行链

- GitHub issue search按`repo:moveit/moveit2 is:pr base:jazzy 3897`及`repo:moveit/moveit2 is:pr base:jazzy stopWorldGeometryMonitor`查询，均为0条匹配。当前未找到#3907的Jazzy backport PR。
- MoveIt Jazzy发布跟踪issue [#3887](https://github.com/moveit/moveit2/issues/3887)仍open。其维护者评论列出若干待回移PR清单，但该清单没有#3907；这只能说明当前可见清单未列出#3907，不能推断以后不会回移。
- ROS官方Jazzy状态页快照：amd64（2026-11-08 05:56:04 -0800）`moveit_servo` B/T为`2.12.4-1noble.20261105.184638`、M为`2.12.4-1noble.20261006.040508`；arm64（05:43:04 -0800）B/T为`2.12.4-1noble.20261106.111556`、M为`2.12.4-1noble.20261006.043301`。production main pool目录仍列出2026-10-06的2.12.4-1 deb文件。故截至该快照，正式Jazzy Main二进制未体现#3907修复。
- 当前MoveIt main的`planning_scene_monitor.cpp` Blob SHA `83f67e15cb167957ddf15bde8fc239d053ed727c`仍保留if/else if stop结构；这与PR未合并状态相符。

#### 4. 任务状态

- SERVO-724持续进行：跟踪#3907更新/CI/review/merge、Jazzy backport及正式deb；当前阻塞点是PR behind、Formatting/CI失败且无可读job明细、无review approval、未发现Jazzy backport。
- SERVO-721与SERVO-723仍未执行；SERVO-725生命周期矩阵仍未执行；SERVO-722现场ICube源码/配置缺失，继续未执行/阻塞。
- 未修改MoveIt或ICube上游，未应用PR补丁。Stäubli工程级验收仍未通过。

来源：
- https://github.com/moveit/moveit2/pull/3907
- https://api.github.com/repos/moveit/moveit2/commits/821818f4ffeaa7564459faed2cbddbfb604f9dcb/check-runs
- https://api.github.com/repos/moveit/moveit2/actions/runs?head_sha=821818f4ffeaa7564459faed2cbddbfb604f9dcb
- https://api.github.com/repos/moveit/moveit2/pulls/3907/reviews
- https://github.com/moveit/moveit2/issues/3887
- https://repo.ros2.org/status_page/ros_jazzy_default.html
- https://repo.ros2.org/status_page/ros_jazzy_unv8.html
- https://repo.ros2.org/ubuntu/main/pool/main/r/ros-jazzy-moveit-servo/


### §9.3.135 PR #3907 Actions workflow失败状态的独立复核（2026-11-08）

#### 1. PR状态与修复范围

- 重新读取 [moveit/moveit2#3907](https://github.com/moveit/moveit2/pull/3907)：PR仍为Open，base为`main`，head为`Yuhx141:fix/planning-scene-contracts`，当前head commit `821818f4ffeaa7564459faed2cbddbfb604f9dcb`。PR声明Fixes #3897，包含双subscriber分别reset的修复和topic-list回归测试。
- PR页面的描述列出Ubuntu 24.04/ROS Jazzy四项测试为作者自报结果；本专项不将其视为本项目独立复测。

#### 2. GitHub Actions直接证据

- 通过GitHub连接器按head SHA读取PR workflow runs，得到两个workflow：Formatting (pre-commit) run `36755746603`、CI run `36755746261`；两者均为`status=completed`、`conclusion=failure`。
- 随后分别查询两个run的jobs，连接器均返回空jobs数组。当前证据因此可以确认workflow级失败，但不能确定失败job、失败step、失败原因或是否属于代码问题；不把空数组解释为“无job运行”或“全部测试失败”。
- 重新查询PR reviews，返回空列表；尚无提交review记录。PR页面仍显示Open。辅助WIP/Mergify/CodeRabbit状态不覆盖这两个workflow失败，也不构成维护者approval。

#### 3. 影响与判定

- PR #3907仍不能作为已合并修复；当前不能将#3897标记为上游已修复。
- SERVO-724维持“正在进行中”：下一步需等待PR更新或补充可读Actions job/step日志、修复Formatting/CI失败、取得维护者review/approval及合并证据；随后继续追踪Jazzy backport和正式二进制。
- SERVO-721、SERVO-723、SERVO-725的目标环境动态测试仍未执行；SERVO-722仍因缺少Stäubli/ICube现场源码、launch/YAML和实际调用链证据而阻塞。
- 未修改MoveIt或ICube上游，未应用PR补丁；未执行Ubuntu 24.04目标安装运行、VAL3/CS9/SRS/HIL/FAT/SAT或实机验证。Stäubli工程级验收仍未通过，TODO-EXT-001仍未授权合并。

来源：
- https://github.com/moveit/moveit2/pull/3907
- https://github.com/moveit/moveit2/issues/3897
- https://api.github.com/repos/moveit/moveit2/actions/runs/36755746603/jobs
- https://api.github.com/repos/moveit/moveit2/actions/runs/36755746261/jobs
- https://api.github.com/repos/moveit/moveit2/pulls/3907/reviews


### §9.3.136 PR #3907 PlanningSceneMonitor回归测试覆盖边界（2026-11-08）

- 对PR #3907的`planning_scene_monitor_test.cpp` diff进行行级复核。新增测试创建PlanningSceneMonitor，启动CollisionObject与PlanningSceneWorld两个topic，先通过`getMonitoredTopics()`确认两个topic均登记，再调用一次`stopWorldGeometryMonitor()`，最后再次读取topic列表并断言两个topic均不存在。
- 该测试直接覆盖“单次stop后两个subscriber均从monitor topic列表移除”的核心回归断言；它不是单纯检查函数返回值，且与PR修复中无条件reset两个subscriber的实现相对应。
- 测试没有发布消息并观察两个订阅回调计数，也没有覆盖stop后的持续消息静默、重复stop、restart配置切换、单topic/空topic组合或octomap monitor停止。故它对#3897的资源登记/移除回归有针对性，但不能替代SERVO-721/725要求的消息行为与完整生命周期矩阵。
- PR页面仍显示Open；本轮Actions workflow已确认Formatting与CI均failure，jobs明细为空，reviews为空。测试源码审查不改变PR门禁状态，也不构成测试通过结论。
- SERVO-724持续进行中；SERVO-721、SERVO-723、SERVO-725动态验证未执行；SERVO-722现场集成证据仍缺。未修改上游/ICube，未应用补丁，未执行目标环境、VAL3/CS9/SRS/HIL或实机验证。

来源：
- https://github.com/moveit/moveit2/pull/3907/files
- https://github.com/moveit/moveit2/pull/3907
- 专项追加件§9.3.136。


### §9.3.137 PR #3907最新讨论、CodeRabbit预合并提示与main分支复核（2026-11-08）

#### 1. PR与Issue最新元数据

- 通过GitHub连接器重新读取PR #3907对应issue：仍为open，`updated_at=2026-09-30T18:09:48Z`，PR描述与测试清单未变；Fixes #3897仍是作者声明，PR未合并。
- #3897仍为open。其复现描述给出Ubuntu 24.04/Jazzy/MoveIt 2.12.4/FastRTPS：双topic均收到消息后单次stop，CollisionObject不再处理而PlanningSceneWorld仍可替换world；单次stop实验3/3失败，double-stop对照3/3通过。这是issue报告者保存的复现证据，不是本项目复测。

#### 2. 新增CodeRabbit评论的证据等级

- PR评论区新增CodeRabbit自动评论，覆盖head `821818f4ffeaa7564459faed2cbddbfb604f9dcb`，报告未生成actionable comments；其预合并提示列出4项通过、1项warning，其中Docstring Coverage为5.56%，阈值80%，涉及18个函数/9个文件（2项跳过）。
- 该提示是CodeRabbit评论中的自动化辅助检查，不是GitHub Actions required check，也不是维护者提交的正式review approval；不能用它覆盖此前确认的Formatting (pre-commit)和CI两个workflow均completed/failure。PR reviews接口仍为空，inline review threads也为空。
- 两个workflow run仍为`36755746603`（Formatting）与`36755746261`（CI），均completed/failure；当前jobs查询无可读job数据，失败job/step/原因未知。

#### 3. Jazzy回移与main源码复核

- #3887（Jazzy 2.12.5+发布跟踪）仍open。维护者可见的backportable PR清单已扩展到#3949等后续PR，但仍未列出#3907；这是当前清单快照，不证明未来不会加入。
- 精确搜索`base:jazzy`且匹配`3897`/`stopWorldGeometryMonitor`的PR仍为0条。
- 再次读取MoveIt main：`planning_scene_monitor.cpp` Blob SHA `83f67e15cb167957ddf15bde8fc239d053ed727c`，stop实现仍为if/else if，只释放一个subscriber；`moveit_cpp.cpp` Blob SHA `abc683745c60e8c12af1955bbd5dbe80f27518fb`，MoveItCpp初始化路径仍调用`startWorldGeometryMonitor()`。上游main仍存在该静态缺陷，不能宣称已修复。

#### 4. 任务状态与结论

- SERVO-724继续进行中：PR未合并，Formatting/CI失败，jobs日志不可读，reviews/threads为空；CodeRabbit提示仅为辅助信息。继续跟踪PR head更新、CI失败明细/修复、正式review/merge、Jazzy backport及APT正式包。
- SERVO-721、SERVO-723、SERVO-725目标环境动态测试未执行；SERVO-722因ICube现场源码/launch/YAML/实际调用链缺失而阻塞。
- 未修改MoveIt或ICube上游、未应用补丁；未执行Ubuntu目标环境测试、VAL3/CS9/SRS/HIL/FAT/SAT或实机验收。Stäubli工程级验收仍未通过，TODO-EXT-001未授权合并。

来源：
- https://github.com/moveit/moveit2/pull/3907
- https://github.com/moveit/moveit2/issues/3897
- https://github.com/moveit/moveit2/issues/3887
- https://github.com/moveit/moveit2/blob/main/moveit_ros/planning/planning_scene_monitor/src/planning_scene_monitor.cpp
- https://github.com/moveit/moveit2/blob/main/moveit_ros/planning/moveit_cpp/src/moveit_cpp.cpp
- 专项追加件§9.3.137。


### §9.3.138 PR #3907失败workflow的artifact可用性检查（2026-11-08）

- 对Formatting run `36755746603`与CI run `36755746261`分别调用GitHub Actions workflow artifacts接口，两个run均返回空artifacts数组。
- 与此前jobs接口空数组结果合并判断：当前连接器可见证据中没有可下载的workflow artifacts，也没有可读job/step记录；因此不能从现有GitHub Actions接口确定失败发生在哪个步骤或原因。不得臆测为编译、测试、格式化或基础设施故障。
- 两个workflow仍为completed/failure。该artifact检查不改变失败状态，不构成重新运行或修复CI。PR #3907仍open、未合并，reviews/inline threads仍为空；CodeRabbit评论仅是辅助自动评论。
- SERVO-724继续进行中，需等待PR作者/维护者更新workflow并提供可读失败信息，或新head触发可检查的CI；随后才可评估修复、review、merge与Jazzy backport。SERVO-721/723/725目标动态验证未执行，SERVO-722现场证据仍缺。
- 未修改上游/ICube、未应用补丁，未执行VAL3/CS9/SRS/HIL/FAT/SAT或实机验证。

来源：
- https://api.github.com/repos/moveit/moveit2/actions/runs/36755746603/artifacts
- https://api.github.com/repos/moveit/moveit2/actions/runs/36755746261/artifacts
- https://github.com/moveit/moveit2/pull/3907
- 专项追加件§9.3.138。


### §9.3.139 PlanningSceneMonitor直接重配置与显式stop/restart边界（2026-11-08）

#### 1. 本轮源码证据

- MoveIt main `planning_scene_monitor.cpp` Blob SHA：`83f67e15cb167957ddf15bde8fc239d053ed727c`。`startWorldGeometryMonitor()`入口先调用`stopWorldGeometryMonitor()`，随后仅在参数topic非空时创建对应subscriber。当前main的stop仍是`if (collision_object_subscriber_) ... else if (planning_scene_world_subscriber_)`，因此单次stop只会reset一个成员。
- `getMonitoredTopics()`根据subscriber成员指针是否非空列出topic名称；它不能单独证明ROS graph中无订阅或回调已经静默。
- PR #3907 head `821818f4ffeaa7564459faed2cbddbfb604f9dcb`的修复源码将两个subscriber分别reset。新增测试`StopWorldGeometryMonitorStopsAllSubscriptions`启动双topic（`load_octomap_monitor=false`），通过`getMonitoredTopics()`确认两个topic登记，调用一次stop后断言两者均不在列表中。该测试是成员登记层面的回归测试，没有发布消息验证回调静默，也未覆盖重配置、重复stop或octomap生命周期。
- PR相对main的比较结果为`diverged`，head领先1个提交、落后3个提交；当前main仍有上述缺陷，PR不能视为已可直接合并。PR仍Open，reviews和inline threads为空；此前记录的Formatting/CI workflow均failure，jobs/artifacts不可读，失败原因未知。

#### 2. 关键生命周期推导（静态分析，不是动态复现）

设旧配置同时订阅CollisionObject=A与PlanningSceneWorld=B。直接再次调用`startWorldGeometryMonitor(A2, "", false)`时，函数内部先stop：只释放A，B仍保留；随后只创建A2，B旧订阅仍留在monitor对象中。类似地，直接重配置为`startWorldGeometryMonitor("", "", false)`会留下B。若重配置为`startWorldGeometryMonitor(A2, B2, false)`，B成员随后被新B2覆盖，旧B不再由成员持有；因此该问题的可观察影响依赖新配置是否为空，不应笼统描述为每次restart都会产生重复订阅。

若调用方先显式stop一次，再调用start，start入口的第二次stop会释放上一次残留的B，随后按新参数建立订阅。因此“显式stop后restart”和“从活动状态直接调用start以切换配置”是两个不同测试路径，必须分别覆盖。对象析构也会销毁成员，不将该问题描述为对象销毁后永久订阅泄漏。

`stopWorldGeometryMonitor()`还会在subscriber处理后调用`octomap_monitor_->stopMonitor()`（若对象存在）；`startWorldGeometryMonitor(..., load_octomap_monitor=false)`不会创建/启动octomap monitor。当前静态代码足以确认stop路径调用stopMonitor，但不能证明OccupancyMapMonitor内部所有线程/订阅的停止时序，需动态检查其API语义和运行日志；本轮不推断额外octomap缺陷。

#### 3. SERVO-725测试矩阵修订

| 场景 | 初始状态与操作 | 预期subscriber成员/topic集合 | 重点观察 |
|---|---|---|---|
| L1 | 空→双topic启动→单次stop | 两topic均移除 | 回归#3897；同时做发布后回调计数 |
| L2 | 双topic活动→直接start为仅CollisionObject新topic | 仅新CollisionObject | 旧PlanningSceneWorld不得残留；当前main静态推导会残留 |
| L3 | 双topic活动→直接start为双空topic | 无world-geometry topic | 当前main静态推导会残留旧PlanningSceneWorld |
| L4 | 双topic活动→直接start为仅PlanningSceneWorld新topic | 仅新PlanningSceneWorld | 旧CollisionObject应移除，新world topic应生效 |
| L5 | 双topic活动→直接start为双新topic | 仅两个新topic | 检查旧topic停止、新topic回调生效 |
| L6 | 双topic活动→显式stop一次→start为仅CollisionObject/双空 | 按新配置建立 | 与L2/L3区分，验证第二次stop清理残留状态 |
| L7 | 单topic（分别两种）→stop、重复stop | 第一次stop后为空，重复stop安全 | 单topic与幂等性 |
| L8 | octomap关闭启动→stop；开启启动→stop→restart关闭 | 按参数启停 | 记录OccupancyMapMonitor状态、日志、topic graph与线程退出证据 |

每个场景需分别采集`getMonitoredTopics()`、ROS graph（如`ros2 topic info -v`）、旧/新topic消息发布与PlanningScene更新回调计数、日志、退出码和精确MoveIt包/commit。测试需在Ubuntu 24.04/ROS Jazzy目标环境执行；目前仅完成源码静态推导和规程修订，未执行动态测试。

#### 4. 状态与限制

- SERVO-724：PR #3907仍Open/未合并，head落后main 3个提交；CI失败原因不可读，reviews为空，继续跟踪新head、CI、review/merge、Jazzy backport和正式deb。
- SERVO-725：本轮完成生命周期状态转换静态分析并修订矩阵；动态测试仍未执行。
- SERVO-721/723：未执行；SERVO-722：缺少Stäubli/ICube现场源码、launch/YAML和实际调用链，仍阻塞。
- 未修改MoveIt/ICube上游，未应用PR补丁；未执行VAL3/CS9/SRS/HIL/FAT/SAT或实机验收。Stäubli工程级验收未通过。

来源：
- https://github.com/moveit/moveit2/blob/main/moveit_ros/planning/planning_scene_monitor/src/planning_scene_monitor.cpp
- https://github.com/moveit/moveit2/pull/3907
- https://github.com/moveit/moveit2/issues/3897
- 专项追加件§9.3.139。


### §9.3.140 OccupancyMapMonitor updater 初始化与停止生命周期审查（2026-11-08）

#### 1. 初始化调用链与上游问题拆分

本轮固定MoveIt main源码：
- occupancy_map_monitor.cpp Blob SHA：7b8bb7a42eed1eea01323458c816993828df3370。
- occupancy_map_monitor.hpp Blob SHA：d30741a6cb7635821e89f480d1142a1c8a8c6bb6。
- occupancy_map_monitor_middleware_handle.cpp Blob SHA：4e870ca9f8f58ecd395beaecbdbff2ccad36eade。
- occupancy_map_updater.hpp Blob SHA：fa29cd1aceca82e3498ccda0d1c1f8c26d4f648b。

main中构造updater的实际顺序为：
setMonitor(this) -> middleware_handle_->initializeOccupancyMapUpdater(updater) -> updater->setParams(sensor_name) -> addUpdater(updater)。
但MiddlewareHandle接口当前返回void；ROS middleware实现调用updater->initialize(node_)，只在false时记录错误，没有把失败状态传回构造器。因此初始化失败的updater仍可能继续执行setParams并被addUpdater登记，之后由startMonitor启动。这与Issue #3902报告一致。Issue #3902仍Open。

PR #3909（Reject occupancy map updaters that fail initialization）针对#3902，将MiddlewareHandle初始化钩子改为bool，失败时返回false，构造器遇到失败便continue，不再配置或登记该updater。PR新增成功/失败两个fake-updater测试；作者自报Ubuntu 24.04/Jazzy构建及4项测试0失败，但这不是本项目独立验证。PR #3909仍Open/未合并，head 3fc0594f708730008da2c4b3709368ade65302f2，base main；与当前main比较diverged，ahead 2 / behind 3。CI run 37457932979和Formatting run 37457933046均completed/failure；jobs与artifacts接口均返回空数组，失败原因未知。Reviews与inline threads为空；CodeRabbit自动评论不是维护者审批。

#### 2. #3901接口契约冲突：不能简单交换调用顺序

occupancy_map_updater.hpp当前注释声称initialize()假定setMonitor()与setParams()已先调用；但main内置插件源码显示：
- PointCloudOctomapUpdater::initialize()设置node_；其setParams()随后通过node_->get_parameter读取配置。
- DepthImageOctomapUpdater::initialize()设置node_并创建image_transport等资源；其setParams()也通过node_->get_parameter读取参数。

因此对于内置插件，先setParams再initialize会在node_尚未初始化时解引用空成员，不能为了满足注释而机械交换顺序。PR #3909作者在Issue #3901评论中也明确指出，内置插件先initialize后setParams；PR #3909因此保留当前运行顺序，只修复初始化失败结果被忽略的问题。Issue #3901仍Open，作为独立API契约问题待上游决策。

结论：当前事实是“接口注释与实现/插件依赖不一致”，不是“已经证明所有updater都必须先setParams”。后续需明确正式契约、同步修正文档/抽象接口和自定义插件迁移策略，并在真实插件与fake插件中覆盖。不能在Stäubli现场自行交换顺序或修改上游。

#### 3. OccupancyMapMonitor停止语义与内置插件观察

main中startMonitor()将active_设为true并逐个调用所有已登记updater的start()；stopMonitor()将active_设为false并逐个调用stop()；析构函数再次调用stopMonitor()。本文件中的active_只见初始化和赋值，没有作为start/stop幂等门闩使用。停止行为实际委托给每个插件，接口stop()为void，没有统一的“所有在途回调已退出”确认/等待接口。

本轮静态查看两个内置插件：
- PointCloud updater的stop删除message filter与subscriber并将指针置空；重复stop从代码表面看可安全处理空指针。
- DepthImage updater的stop调用sub_depth_image_.shutdown()；订阅句柄关闭后是否无在途回调，以及与并发回调的退出顺序，仍需在目标executor/RMW上验证。
- 两者的start路径资源处理方式不同；尤其不能仅凭monitor层active_布尔值认定重复start被统一抑制。

因此stopMonitor()可以确认会逐个调用插件stop，但仅凭这一层不能证明所有插件的后台工作线程、在途回调和资源均已完成退出。需要按启用的插件类型记录旧topic消息、回调计数、订阅graph、线程/日志和stop返回后的静默窗口。对象析构时会再次调用stop，不应假设插件只会收到一次stop。

#### 4. 建议补充的SERVO-726验证矩阵

| 场景 | 操作 | 验收点 |
|---|---|---|
| U1 | updater initialize=true | 调用顺序、setParams成功、登记、start |
| U2 | updater initialize=false | 不调用setParams、不登记、不start；确认失败资源清理 |
| U3 | initialize=true但setParams=false | 不登记、不start；确认initialize已创建的资源被安全回收 |
| U4 | 内置PointCloud updater | initialize先于setParams；缺参/错误类型参数时失败路径安全 |
| U5 | 内置DepthImage updater | initialize先于setParams；ImageTransport和参数错误路径安全 |
| U6 | start→stop→stop | 所有插件停止，重复stop安全，在途回调计数最终稳定 |
| U7 | start→stop→start | 恢复订阅，无重复订阅/重复回调 |
| U8 | start→start→stop | 重复start行为符合明确契约，不产生资源/订阅异常 |
| U9 | monitor析构前已stop | 析构再次stop安全；无use-after-free或残余回调 |
| U10 | 初始化失败插件与成功插件混合 | 失败插件被隔离，成功插件仍可正常启动和停止 |

以上为测试规程，不是已执行结果。Stäubli现场是否启用Octomap monitor、具体sensor plugin、插件参数与executor配置尚未取得；因此这些问题对现场的影响仍为条件性未知，不能宣称现场已触发。

#### 5. 状态与限制

- SERVO-724：继续跟踪PR #3907；仍Open、CI失败原因不可读、无维护者review。
- SERVO-725：PSM双topic与重配置静态矩阵已整理；动态测试未执行。
- SERVO-726：新增updater初始化契约、失败隔离及stop/start生命周期审查；静态源码核对完成，动态验证未执行。
- 上游#3901、#3902仍Open；PR #3909仍Open，目标修复未进入main。PR #3909不解决#3901接口文档契约冲突。
- SERVO-722现场插件配置/源码仍缺，Stäubli适用性未确认。未修改MoveIt/ICube上游、未应用PR补丁；未执行VAL3/CS9/SRS/HIL/FAT/SAT或实机验收。Stäubli工程级验收未通过。

来源：
- https://github.com/moveit/moveit2/issues/3901
- https://github.com/moveit/moveit2/issues/3902
- https://github.com/moveit/moveit2/pull/3909
- https://github.com/moveit/moveit2/blob/main/moveit_ros/occupancy_map_monitor/src/occupancy_map_monitor.cpp
- https://github.com/moveit/moveit2/blob/main/moveit_ros/occupancy_map_monitor/src/occupancy_map_monitor_middleware_handle.cpp
- https://github.com/moveit/moveit2/blob/main/moveit_ros/perception/pointcloud_octomap_updater/src/pointcloud_octomap_updater.cpp
- https://github.com/moveit/moveit2/blob/main/moveit_ros/perception/depth_image_octomap_updater/src/depth_image_octomap_updater.cpp


### §9.3.141 PR #3909 的 MiddlewareHandle 源码兼容性与失败资源回收边界

#### 1. 本轮上游状态复核

- MoveIt PR #3909（`3fc0594f708730008da2c4b3709368ade65302f2`）仍为Open、未合并，目标分支main；与当前main比较为diverged，ahead 2 / behind 3。
- CI run `37457932979` 与 Formatting run `37457933046` 均为completed/failure；jobs与artifacts接口均返回空数组，失败job/step/原因不可见。PR reviews与inline review threads为空。
- CodeRabbit自动评论不是维护者review/approval。该评论指出#3909覆盖#3902但未解决#3901，并提出失败初始化后的清理契约风险；本节分别依据源码和接口定义核验，不将机器人评论当作正式审批。
- PR作者自报Ubuntu 24.04/ROS Jazzy构建及4项测试0失败，仍属于作者报告，不是本项目独立验证。

#### 2. MiddlewareHandle API 的源兼容性影响

PR #3909将公开头文件中 `OccupancyMapMonitor::MiddlewareHandle::initializeOccupancyMapUpdater(OccupancyMapUpdaterPtr)` 从纯虚 `void` 改为纯虚 `bool`，ROS具体实现与测试Mock也同步改签名；PR同时向 `MIGRATION.md` 的ROS Rolling章节增加自定义middleware handle迁移说明。

静态核对确认：
- `OccupancyMapMonitor::MiddlewareHandle` 是公共头文件中的public嵌套类，方法为public纯虚接口。
- `OccupancyMapMonitor(std::unique_ptr<MiddlewareHandle>, ...)` 是public构造函数，允许外部传入自定义handle；因此这不是只能由MoveIt内部访问的私有实现细节。
- 下游若仍以旧的 `void` 返回类型实现该纯虚方法，方法签名不再匹配新接口，派生类无法按新头文件完成编译；自定义handle、测试fake/mock和任何封装此接口的集成都要更新为bool并明确传播初始化成功/失败。
- PR迁移说明位于ROS Rolling章节。当前PR目标是main，不能据此推断该API变更已进入Jazzy稳定分支或Jazzy二进制包。

兼容性判定：源码层面的破坏性变更已确认；二进制ABI是否兼容没有通过ABI工具或旧/新二进制混合加载验证，不能声称兼容。采用该接口的下游应按需要更新实现并以目标分支头文件重编译相关目标；正式回移Jazzy前必须单独评估稳定分支API/ABI影响、版本策略和迁移窗口。

#### 3. initialize失败与setParams失败的资源回收覆盖缺口

PR #3909在middleware返回false后由构造器执行continue，因而跳过setParams与addUpdater；局部updater句柄在本次循环迭代结束时离开作用域。候选实现没有在该分支显式调用updater的stop()，也没有增加统一rollback接口或文档化的“initialize失败必须自行撤销已创建资源”契约。

当前可证明与不可证明的边界：
- 内置PointCloud updater的initialize设置node_并创建TF buffer/listener和shape mask，当前实现最终返回true；其stop()删除message filter/subscriber。不能把该内置路径描述成已经复现initialize(false)泄漏。
- 内置DepthImage updater的initialize设置node_并创建多个ImageTransport对象及TF相关对象，当前实现最终返回true；析构函数明确shutdown深度图像订阅。不能把当前内置实现的true路径外推为所有自定义插件的失败回滚保证。
- 外部updater可以在initialize()中先申请资源再返回false；接口没有统一规定失败后资源必须如何撤销。若只依赖析构，安全性取决于每个插件是否用RAII正确拥有所有资源，以及回调/后台执行是否可能继续引用monitor。
- setParams(false)发生在initialize成功之后，构造器同样continue且不会登记updater；它也可能留下initialize阶段已经分配的资源。PR新增测试没有覆盖此失败路径。
- PR中的fake updater失败测试只记录initialize调用并返回false，没有创建ROS subscription、timer、callback或后台资源，因此不能证明部分初始化失败可安全回收。

结论：这是需要明确契约并测试的资源生命周期缺口，不是已经证实的资源泄漏。禁止仅凭continue或局部对象离开作用域，推断任意第三方插件均能安全清理。

#### 4. 新增SERVO-727验证矩阵

| 场景 | 操作 | 验收点 |
|---|---|---|
| U11 | 使用旧void签名和新bool签名分别编译自定义MiddlewareHandle派生类 | 确认源兼容性变化；盘点所有下游实现、Mock与测试夹具 |
| U12 | 对旧/新头文件和库进行ABI检查，必要时做旧插件/新库混合加载验证 | 得到ABI工具报告；未完成前标记ABI兼容性未知，不承诺二进制兼容 |
| U13 | fake updater在initialize中创建subscription/timer/callback后返回false | 验证continue后的资源释放、ROS graph消退、回调静默、无悬空monitor访问 |
| U14 | initialize成功并创建资源，随后setParams返回false | 验证该失败分支销毁/停止资源，不登记、不启动且无残余回调 |
| U15 | 多插件混合加载，一项初始化失败、一项参数配置失败，其余成功 | 失败插件隔离、成功插件仍可启动停止，资源计数与日志可追溯 |

#### 5. 任务状态与边界

- SERVO-727：源码/API兼容性与失败回收静态审查已完成；U11-U15构建、ABI和动态资源测试未执行。
- SERVO-726：初始化失败传播、#3901调用顺序契约、U1-U10插件生命周期矩阵继续跟踪；动态验证未执行。
- SERVO-724：继续跟踪#3907及#3909的PR head、CI、维护者review/merge和Jazzy回移。#3909目前CI/Formatting失败且失败详情不可读。
- SERVO-722现场Octomap使用情况、sensor plugin、参数与executor仍未确认；不得将上游通用源码结论写成Stäubli现场已触发。
- 未修改MoveIt/ICube上游，未应用PR补丁；未执行目标环境构建、VAL3/CS9/HIL/FAT/SAT或实机验收。Stäubli工程级验收未通过。

来源：
- https://github.com/moveit/moveit2/pull/3909
- https://github.com/moveit/moveit2/issues/3901
- https://github.com/moveit/moveit2/issues/3902
- https://github.com/moveit/moveit2/blob/main/moveit_ros/occupancy_map_monitor/include/moveit/occupancy_map_monitor/occupancy_map_monitor.hpp
- https://github.com/moveit/moveit2/blob/main/moveit_ros/occupancy_map_monitor/src/occupancy_map_monitor.cpp
- https://github.com/moveit/moveit2/blob/main/moveit_ros/perception/pointcloud_octomap_updater/src/pointcloud_octomap_updater.cpp
- https://github.com/moveit/moveit2/blob/main/moveit_ros/perception/depth_image_octomap_updater/src/depth_image_octomap_updater.cpp
- 专项追加件§9.3.140。


### §9.3.142 作者维护的外部复现夹具对 MiddlewareHandle 源码迁移的实证

#### 1. 外部复现仓库及构建依赖

检查仓库：`https://github.com/Yuhx141/ros2-upstream-issue-reproducers`，固定审查commit `9630a900f2d323b3b45c1976df8fe722b809f7a7`。

- 仓库README说明其收录ROS 2上游issue复现器和保存证据，默认launcher source `/opt/ros/jazzy/setup.bash`。
- `PROVENANCE.json`记录MoveIt 2 runtime release为2.12.4，planning-scene source reference为`002f40e58ebf5322c89468f5049867791e5f67fd`，并声明process map verified。
- 两个场景目录`OCC-params-after-initialize`与`OCC-failed-initialize-starts`均有CMake工程；CMake通过`find_package(moveit_ros_occupancy_map_monitor REQUIRED)`链接安装的MoveIt occupancy-map-monitor包，而不是把MoveIt源码直接vendor进该fixture。
- 两个目录的`occupancy_init_probe.cpp`具有相同Blob SHA `4a5dd5b5ffb1cc30da67c55a0c037e5eeea63a60`，是同一实现被两个场景目录复用，不能计作两个独立下游实现。

#### 2. 旧签名直接使用证据

该复现fixture中的`FakeMiddleware`继承`OccupancyMapMonitor::MiddlewareHandle`，实现：

```cpp
void initializeOccupancyMapUpdater(OccupancyMapUpdaterPtr updater) override
{
  updater->initialize(nullptr);
}
```

这段实现满足其所记录MoveIt 2.12.4旧接口，但不能满足PR #3909将该纯虚方法变更为bool后的新接口。若将该复现工程切换到包含PR #3909变更的头文件/库，fixture需要把override签名改为bool，并返回`updater->initialize(...)`的结果或等效状态；否则无法满足新纯虚接口。

这是一项可定位到源码、构建依赖和测试版本的API迁移实证，能够强化SERVO-727的U11设计。证据级别必须保持准确：它是PR作者维护的公开复现工程，不是独立商业产品、不是Stäubli/ICube集成，也不是第三方量产部署；不据此估算受影响下游数量。

#### 3. 与PR #3909兼容性结论的关系

- PR #3909仍把公开纯虚接口由void改为bool，MIGRATION.md说明custom middleware handles需迁移。
- 该外部复现fixture提供了一个具体的旧签名实现，证明迁移要求不仅是理论上的派生类推演。
- 源码兼容性差异确认；未在该仓库复制后应用PR #3909并运行编译，因此“迁移后可成功构建”仍未验证。
- 二进制ABI仍未用ABI checker或混合版本加载实验确认。

#### 4. SERVO-727状态调整

U11从“静态接口差异已确认”细化为“已找到作者维护的MoveIt 2.12.4外部复现fixture旧void override；已确认需源码迁移；fixture升级编译仍未执行”。U12 ABI检查、U13 initialize(false)部分资源回收、U14 setParams(false)资源回收、U15混合插件隔离仍未执行。

来源：
- https://github.com/Yuhx141/ros2-upstream-issue-reproducers/tree/9630a900f2d323b3b45c1976df8fe722b809f7a7/moveit2/OCC-params-after-initialize
- https://github.com/Yuhx141/ros2-upstream-issue-reproducers/blob/9630a900f2d323b3b45c1976df8fe722b809f7a7/moveit2/OCC-params-after-initialize/occupancy_init_probe.cpp
- https://github.com/Yuhx141/ros2-upstream-issue-reproducers/blob/9630a900f2d323b3b45c1976df8fe722b809f7a7/PROVENANCE.json
- https://github.com/moveit/moveit2/pull/3909
- 专项追加件§9.3.141。
