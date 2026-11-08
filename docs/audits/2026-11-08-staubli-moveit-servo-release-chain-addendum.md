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
