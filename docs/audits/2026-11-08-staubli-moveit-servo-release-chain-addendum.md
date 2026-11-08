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
2. override_dh_auto_test目标执行dh_auto_test，但命令以|| true结束；文件中的echo注释明确说明，即使测试失败，也不会取消构建。

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
