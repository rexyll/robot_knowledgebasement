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
