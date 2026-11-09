# 2026-11-09｜Stäubli MoveIt感知链路审计追加件

> 本追加件承接根 TaskPlan §9.3.155。审查对象是 MoveIt 2 当前 main 的 MeshFilter/OpenGL worker 生命周期实现；它是通用上游源码静态审查，不是 Stäubli/ICube 现场复现。固定文件以本轮读取的 Blob SHA 为准。未修改 MoveIt/ICube 上游，未应用 PR。

## §9.3.156 MeshFilter worker启动异常、FilterJob异常传播与OpenGL上下文回收

### 1. 审查基线

| 文件 | 本轮读取的 Blob SHA |
|---|---|
| `mesh_filter/src/mesh_filter_base.cpp` | `333a7031925cb47fb201af34fe61431a9ccf2a6f` |
| `mesh_filter/include/moveit/mesh_filter/mesh_filter_base.hpp` | `c14aa939580fe69e327629a3f236f1d11fa91d55` |
| `mesh_filter/src/gl_renderer.cpp` | `f74bb8267e32cde20c7acd46ff4b4a985ab81c99` |
| `mesh_filter/include/moveit/mesh_filter/gl_renderer.hpp` | 本轮已读取，类声明含线程ID→context引用计数映射 |
| `mesh_filter/src/gl_mesh.cpp` | `96737abbdd2a3cd93b29ac22cc4e09545aece928` |
| `mesh_filter/include/moveit/mesh_filter/filter_job.hpp` | `8cfe5bdeb8fad6bdf9c8b26cee7ca0a25685069d` |
| `depth_image_octomap_updater/src/depth_image_octomap_updater.cpp` | `3dbb114ab6bfd0654823724b6848c881caa2d8ee` |

### 2. 静态核查结果

1. **worker初始化异常没有线程边界处理。** `MeshFilterBase`构造函数启动`filter_thread_`；worker进入`run()`后首先调用`initialize()`。该调用及后续job执行均没有try/catch或异常结果通道。若初始化中的OpenGL/GLSL操作抛出异常，异常会越过线程入口；按C++线程异常规则将调用`std::terminate`，不是一个可由构造调用方正常捕获并恢复的初始化失败。该结论由代码结构确定，尚未在目标图形驱动/ROS环境复现。

2. **GLRenderer构造失败缺少完整回滚。** `GLRenderer`构造先调用`createGLContext()`再调用`initFrameBuffers()`。后者在framebuffer状态不是`GL_FRAMEBUFFER_COMPLETE`时抛出`runtime_error`；构造函数抛出时对象析构函数不会运行，而此前已创建的纹理、renderbuffer、framebuffer及GL context没有由局部RAII对象统一回滚。实际残留资源取决于失败发生阶段和驱动行为，需故障注入测量，不直接断言每次失败都会泄漏全部对象。

3. **GLEW失败路径存在静态可见的context登记残留。** `createGLContext()`在调用`glutCreateWindow()`和`glewInit()`前先向静态`s_context`插入当前thread id、引用计数1、window id 0；若`glewInit()`返回非`GLEW_OK`，函数抛出异常，但没有删除刚插入的map项，也没有销毁已创建窗口。该路径的回滚缺口由源码顺序确定；是否能在指定平台触发GLEW失败尚未验证。

4. **FilterJob不捕获任务异常，也不保证异常完成通知。** `FilterJob::execute()`在持有job mutex时直接执行`exec_()`，没有捕获异常；只有正常返回后才设置`done_=true`并通知condition variable。若job函数抛出，异常继续逃逸worker线程并导致进程终止；即使未来仅在worker外层捕获，也必须同时把异常存入job并通知等待者，否则`Job::wait()`可能永久等待。当前`Job`接口没有exception_ptr/result状态。

5. **输入mesh法线缺失可进入上述异常链。** `GLMesh`构造在`mesh.vertex_normals`为空时明确抛出`runtime_error`；`MeshFilterBase::addMesh()`将`addMeshHelper()`作为FilterJob执行并同步wait。故传入缺少vertex normals的mesh会在worker执行job时抛异常，当前执行链没有局部异常传递/恢复机制。需要确认DepthImage updater从各种shape类型生成mesh时是否总能提供法线；不能仅凭该接口缺陷断言Stäubli常规模型一定触发。

6. **正常销毁路径的GL线程归属有明确设计依赖。** `GLRenderer`的context表以`std::thread::id`为键，`deleteGLContext()`只查找当前线程的条目；`MeshFilterBase::run()`正常退出时在worker线程调用`deInitialize()`并reset两个renderer，因此正常路径可在创建context的worker线程释放。若初始化中途异常、没有执行`deInitialize()`，该正常配对路径不成立。测试必须记录create/delete的线程ID，并覆盖部分初始化失败和重复构造销毁。

7. **§9.3.155的stop_数据竞争仍成立。** worker在`while (!stop_)`中无锁读取`stop_`，析构线程则在`jobs_mutex_`保护下写入；该mutex并未保护worker的循环条件读取。它是C++数据竞争的静态结论，是否在目标构建中由TSan报告需实测。不能把它直接扩大成必然死锁或必然崩溃。

### 3. 新增验收任务

新增SERVO-739：

- **J1**：在隔离进程中注入GLUT窗口创建失败、GLEW初始化失败、framebuffer incomplete，确认异常边界、窗口销毁、`s_context`引用计数和GL对象回滚。
- **J2**：注入render shader/filter shader编译失败，验证worker线程是否终止进程；改造候选应把初始化结果回传构造方，而不是在线程中无处理抛出。
- **J3**：构造vertex_normals为空的mesh调用addMesh，确认当前异常传播行为及进程结果；随后验证异常可被调用线程观察、job wait必定结束的目标契约。
- **J4**：对FilterJob执行抛异常的exec，验证异常存储、done状态、condition通知及等待方不会永久阻塞。
- **J5**：在每种初始化失败点后重复创建/销毁MeshFilter，检查静态context表、GLUT窗口、GL对象和线程数是否恢复基线。
- **J6**：正常路径与部分初始化失败路径分别记录GL context创建/销毁线程ID，检查跨线程GL调用及context引用计数。
- **J7**：对stop_循环读写运行TSan；对停止时正在执行、已排队、刚提交的Job分别验证取消、执行、通知和join行为。
- **J8**：在DepthImageOctomapUpdater层对stop、in-flight depth callback、mesh_filter析构和GL worker退出做屏障测试；不得把subscription shutdown单独视为callback静默证据。
- **J9**：在Stäubli/ICube目标环境核实图形后端、DISPLAY/EGL/GLX、GPU/软件渲染、GLEW版本、容器权限及实际DepthImage updater启用情况；未取得现场资料前保持未确认。

J1–J9均未执行。没有目标ROS Jazzy构建、TSan/ASan、GL故障注入、CS9/HIL或实机证据。

### 4. 结论与边界

本节确认的是三类静态问题：worker线程入口缺少初始化/job异常边界；GLRenderer构造与GLEW失败路径没有完整回滚；stop_存在无同步读写。另确认正常GL context销毁依赖worker线程执行`deInitialize()`。这些发现需要上游动态复现和修复评估；尚不能据此认定Stäubli部署启用了DepthImage updater、使用特定GPU后端，或现场发生崩溃/资源泄漏。

本轮只完成MoveIt main静态源码审查和SERVO-739测试设计。未运行本项目ROS构建/测试、TSan/ASan、图形后端故障注入、HIL或实机验证；未修改MoveIt/ICube上游、未应用PR #3909；Stäubli工程级验收未通过，TODO-EXT-001未授权合并。

### 来源

- https://github.com/moveit/moveit2/blob/main/moveit_ros/perception/mesh_filter/src/mesh_filter_base.cpp
- https://github.com/moveit/moveit2/blob/main/moveit_ros/perception/mesh_filter/include/moveit/mesh_filter/mesh_filter_base.hpp
- https://github.com/moveit/moveit2/blob/main/moveit_ros/perception/mesh_filter/src/gl_renderer.cpp
- https://github.com/moveit/moveit2/blob/main/moveit_ros/perception/mesh_filter/include/moveit/mesh_filter/gl_renderer.hpp
- https://github.com/moveit/moveit2/blob/main/moveit_ros/perception/mesh_filter/src/gl_mesh.cpp
- https://github.com/moveit/moveit2/blob/main/moveit_ros/perception/mesh_filter/include/moveit/mesh_filter/filter_job.hpp
- https://github.com/moveit/moveit2/blob/main/moveit_ros/perception/depth_image_octomap_updater/src/depth_image_octomap_updater.cpp
- 专项审计§9.3.155；厂商档案§128.106。


## §9.3.157 DepthImage异步输入缓冲区生命周期与条件性悬空指针

### 1. 审查基线与数据路径

本节继续审查MoveIt main的DepthImage回调与MeshFilter异步队列。关键源码：
- `depth_image_octomap_updater/src/depth_image_octomap_updater.cpp`，Blob SHA `3dbb114ab6bfd0654823724b6848c881caa2d8ee`
- `mesh_filter/include/moveit/mesh_filter/mesh_filter_base.hpp`，Blob SHA `c14aa939580fe69e327629a3f236f1d11fa91d55`
- `mesh_filter/src/mesh_filter_base.cpp`，Blob SHA `333a7031925cb47fb201af34fe61431a9ccf2a6f`
- `mesh_filter/include/moveit/mesh_filter/filter_job.hpp`，Blob SHA `8cfe5bdeb8fad6bdf9c8b26cee7ca0a25685069d`

### 2. 静态核查

1. MeshFilter公开接口声明为`filter(const void* sensor_data, GLushort type, bool wait = false) const`，默认异步返回。实现创建FilterJob，其lambda捕获`this`、裸`sensor_data`指针和encoding；worker后续在`doFilter()`中把该指针交给`glTexImage2D(..., sensor_data)`。接口没有携带输入缓冲区所有权，也没有在声明处明确要求调用方必须保持数据存活至任务完成。

2. DepthImage回调把`&depth_msg->data[0]`传入上述默认异步接口。消息数据由回调参数中的`sensor_msgs::msg::Image::ConstSharedPtr`持有；异步job只捕获裸指针，不捕获该SharedPtr。

3. **正常路径具有一个隐式的队列完成屏障。** 相机内参检查通过后，回调随后无条件调用`getFilteredLabels()`。该函数在同一MeshFilter队列追加读取标签的job并同步wait；worker串行处理队列，因此前面的depth filter job先完成，正常路径下depth_msg在回调返回前仍被持有。这一点不能忽略，也不能笼统声称每帧输入都存在UAF。

4. **异常内参路径打破了该隐式屏障。** filter job入队后，回调计算`inv_fx_ = 1.0 / K0_`、`inv_fy_ = 1.0 / K4_`；若`px`、`py`或逆焦距为NaN，代码直接return。该return发生在后续`getFilteredLabels()`同步等待之前。回调结束后，若没有其他SharedPtr持有该消息，depth_msg及其data缓冲区即可释放；而worker队列中的job仍可能稍后读取该裸指针。由此形成**条件性悬空指针/潜在use-after-free路径**。实际是否触发取决于worker调度时序和消息是否另有所有者，尚未动态复现。

5. 当前内参检查使用`isnan`而非`isfinite`；零焦距产生的无穷逆焦距并不会被该NaN分支拦截。这是输入校验健壮性问题，需单独测试，不将其与已识别的提前返回生命周期路径混为一谈。

### 3. 修复方向（供上游评估，不代表已修改）

- 最小化风险的局部修复：把完整CameraInfo数值有效性检查前移到`mesh_filter_->filter()`之前，确保任何拒绝输入的return都发生在提交异步任务之前；并使用`std::isfinite`校验焦距、主点和逆焦距。
- 更可靠的接口修复：让异步job持有输入数据的所有权，例如增加带共享owner/lifetime token的异步接口，或在提交时持有不可变消息/缓冲区共享引用；不能只依赖后续某个读取结果的job偶然形成屏障。
- 若采用同步`wait=true`作为局部补救，应评估它对DepthImage回调延迟和吞吐量的影响，并避免将其作为所有调用方的隐式性能回归。
- 在MeshFilter API文档中明确裸指针异步接口的生命周期契约；最好提供类型安全的拥有型输入接口，避免调用方误用。

### 4. 新增验收任务

新增SERVO-740：

- **K1**：构造可控worker barrier，使filter job入队但在读取输入前暂停；传入含NaN主点或NaN焦距的CameraInfo，触发回调提前return并释放消息；恢复worker，在ASan下验证是否读取已释放缓冲区。
- **K2**：对比有效CameraInfo路径，确认后续`getFilteredLabels()`的队列顺序确实等待前置filter job完成，并记录消息引用生命周期。
- **K3**：覆盖K0/K4为0、NaN、正负Inf，验证`std::isfinite`级输入校验和是否在异步提交前拒绝。
- **K4**：用弱引用/自定义owner计数验证异步job在执行/取消/异常/队列清空时持有并释放输入owner的时点。
- **K5**：在高帧率、慢GPU/软件渲染和executor并发条件下压力测试消息缓冲区生命周期，使用ASan并记录worker开始读取与消息析构的时序。
- **K6**：比较同步等待、共享owner和数据拷贝三种候选修复的回调延迟、吞吐、峰值内存和CPU/GPU开销。
- **K7**：在Stäubli/ICube目标环境核实实际CameraInfo发布端、标定参数校验策略、DepthImage updater启用状态和图形后端；没有现场配置/日志不得判定部署暴露。

K1–K7均未执行。没有ASan动态复现、ROS Jazzy构建、GPU压力测试、CS9/HIL或实机证据。

### 5. 结论与边界

§9.3.157识别的是一个由“默认异步裸指针输入”与“NaN内参提前return”共同构成的条件性生命周期缺口。有效内参路径随后执行同步`getFilteredLabels()`，构成队列屏障，因此不能把问题扩大为所有DepthImage帧必然悬空。该缺口在特定无效CameraInfo和worker调度时序下可能导致worker读取已释放消息缓冲区；需按SERVO-740进行ASan和屏障注入验证。

本轮仅完成MoveIt main静态源码审查和测试设计。未运行ASan、ROS动态测试、GPU/软件渲染压力测试、CS9/HIL或实机验证；未修改MoveIt/ICube上游、未应用PR；Stäubli工程级验收未通过，TODO-EXT-001未授权合并。

### 来源

- https://github.com/moveit/moveit2/blob/main/moveit_ros/perception/depth_image_octomap_updater/src/depth_image_octomap_updater.cpp
- https://github.com/moveit/moveit2/blob/main/moveit_ros/perception/mesh_filter/include/moveit/mesh_filter/mesh_filter_base.hpp
- https://github.com/moveit/moveit2/blob/main/moveit_ros/perception/mesh_filter/src/mesh_filter_base.cpp
- https://github.com/moveit/moveit2/blob/main/moveit_ros/perception/mesh_filter/include/moveit/mesh_filter/filter_job.hpp
- 专项审计§9.3.156；厂商档案§128.107。


### §9.3.158 PointCloudOctomapUpdater点云输入校验、ShapeMask变换状态与停止边界

#### 1. 审查基线

本节基于MoveIt 2主线提交 `6ed6372a72ba9b121ed12ef574ea4ff4d3d92f09` 的以下源码进行静态审查：

- `moveit_ros/perception/pointcloud_octomap_updater/src/pointcloud_octomap_updater.cpp`，Blob SHA `e11a9f41d6dad68de31c83268e6bd686728eee9e`
- `moveit_ros/perception/pointcloud_octomap_updater/include/moveit/pointcloud_octomap_updater/pointcloud_octomap_updater.hpp`，Blob SHA `65c7f090b9417eb3454538b16783191fbfd6b89f`
- `moveit_ros/perception/point_containment_filter/src/shape_mask.cpp`，Blob SHA `7686f0e6b0778daa8991b843100e13a9bb1bd3be`
- `moveit_ros/perception/point_containment_filter/include/moveit/point_containment_filter/shape_mask.hpp`，Blob SHA `d77d8dfe6322d8d46d3f65c1e154f9e07708bd8b`
- `moveit_ros/occupancy_map_monitor/src/occupancy_map_updater.cpp`，Blob SHA `7520e9fccd5d18414e137e3f14c313de50b22cf8`
- `moveit_ros/occupancy_map_monitor/src/occupancy_map_monitor.cpp`，Blob SHA `7b8bb7a42eed1eea01323458c816993828df3370`
- `moveit_ros/occupancy_map_monitor/include/moveit/occupancy_map_monitor/occupancy_map_updater.hpp`，Blob SHA `fa29cd1aceca82e3498ccda0d1c1f8c26d4f648b`

本节是MoveIt通用源码静态审查。提交基线不等于Stäubli/ICube部署版本；未取得现场插件参数、点云发布端和executor配置。

#### 2. 静态核查结论

1. **点云消息本身由SharedPtr持有，回调内同步消费。** `cloudMsgCallback`接收`PointCloud2::ConstSharedPtr`，本函数没有把点云裸指针或引用异步存入后台job；在回调执行期间，消息对象由shared_ptr参数保持存活。因此本节没有发现与§9.3.157相同的“异步job捕获裸消息data指针、回调提前返回”模式。

2. **订阅显式使用MutuallyExclusive callback group，但这不是stop析构屏障。** `start()`创建`CallbackGroupType::MutuallyExclusive`并传给message_filters Subscriber，PointCloud订阅回调属于该组，故该组内同一时刻不会并行执行多个回调。该保证不能扩展到从其他线程调用的`stop()`、`excludeShape()`或`forgetShape()`，也不能单凭callback group证明删除MessageFilter/Subscriber会等待已经开始或已排队的回调退出。

3. **stop()删除订阅对象后没有显式in-flight callback join。** `stop()`依次delete `point_cloud_filter_`和`point_cloud_subscriber_`并置空；注册的lambda捕获裸`this`。源码没有updater级停止标志、活动回调计数、executor屏障或join。OccupancyMapMonitor析构函数调用`stopMonitor()`后才进入成员析构。是否底层rclcpp/message_filters析构会同步等待回调，以及正在执行的lambda是否可能越过updater销毁边界，必须用目标ROS版本和executor做屏障测试；当前只能记为**条件性生命周期风险/缺少显式证明**，不是已复现UAF。

4. **ShapeMask内部形状容器有互斥保护。** `addShape`、`removeShape`、`setTransformCallback`、`maskContainment`及单点查询均使用同一`shapes_lock_`；头文件明确该锁保护`bodies_`和`bspheres_`。因此不能把并发add/remove与mask遍历直接判为无锁容器数据竞争。锁覆盖整个mask计算及transform callback调用，可能造成更新线程等待，但是否形成现场延迟需测量。

5. **transform_cache_的读写路径有局部串行关系。** PointCloud callback先调用基类`updateTransformCache()`清空并填充`transform_cache_`，随后调用`ShapeMask::maskContainment()`，由其transform callback调用`getShapeTransform()`读取该map。两步位于同一个PointCloud回调中；订阅callback group又是MutuallyExclusive。当前源码没有证据表明该updater存在第二个并发写入者，故本节不把它定性为已确认的数据竞争。仍需验证外部自定义transform provider及停止/重启路径没有引入并发访问。

6. **ShapeMask在单个shape变换缺失时仍继续使用shape集合。** `maskContainment()`对每个body请求transform；若callback返回false，只记录错误，不更新该body的pose，也不从后续containment测试中排除该body。随后仍对`bodies_`中的body执行`containsPoint()`。同时`bspheres_`按body总数resize，但只有成功取得transform的body才递增写入索引；失败项可能留下默认或上一次计算的球体数据。由此存在使用旧pose/旧bounding sphere进行自过滤的静态路径，可能造成mask误分类。需要明确缺失transform时应fail-closed、跳过该shape还是拒绝整帧，不能把日志记录视为安全降级策略。

7. **point_subsample参数未验证零值。** 参数以unsigned int读取，`setParams()`只检查参数是否存在，没有检查其数值范围。主循环使用`row += point_subsample_`和`col += point_subsample_`；当配置为0时两个循环的索引不前进，回调会无限循环。该结论直接来自循环结构，尚未运行配置注入测试。至少应在参数校验阶段拒绝0，并覆盖极大值/边界值。

8. **PointCloud2结构校验不足，存在越界和错误解析输入路径。** `ShapeMask::maskContainment()`直接计算`data.size() / point_step`，未先拒绝`point_step == 0`；并按该结果分配mask。PointCloud updater随后按`height * width`的行主序索引`mask_[row * width + col]`，没有先证明点数、data长度、row_step与width/point_step一致。若输入消息结构不一致，可能出现除零、mask索引越界或迭代器越过有效点数据。当前实现也没有显式验证x/y/z字段存在、类型为FLOAT32、count和offset在point_step范围内。应以`point_step > 0`、`row_step >= width * point_step`、`data.size() >= row_step * height`、字段类型/数量/偏移合法及乘法溢出检查建立输入门槛。

9. **行步长与字段布局存在隐含格式假设。** updater以`row * width`计算行起点，ShapeMask和updater都使用线性PointCloud2 iterator，没有显式按`row_step`跳过行尾padding。updater从x iterator读取`pt_iter[0..2]`；sensor_msgs iterator文档仅在x/y/z连续存储时才建议用该方式访问三个坐标。对非紧密行布局或非连续XYZ字段，当前路径可能解析错误。需要明确限定并校验输入格式，或改用独立x/y/z迭代器和按row_step寻址。

10. **点坐标只过滤NaN，没有过滤正负Inf。** 主循环使用`!std::isnan(x/y/z)`，因此Inf会继续进入坐标变换、归一化和`coordToKey()`。应评估`std::isfinite`及OctoMap可表示范围检查；这属于输入健壮性缺口，不代表常规传感器流必然包含Inf。

11. **OctoMap读写锁在已捕获异常路径中有手工释放，但写更新不是事务。** read阶段的try/catch会在异常时unlockRead并return；write阶段catch后也会unlockWrite，因此当前可见的受保护代码异常路径有配对释放。可是write阶段可能已经执行若干`updateNode()`后才抛出；catch仅记录“Internal error”，没有回滚已修改节点，随后仍调用`triggerUpdateCallback()`并可能发布filtered cloud。故失败帧可能留下部分更新的地图并通知下游，不能宣称更新具备原子性。建议使用RAII锁守卫，并定义失败时回滚、标记地图无效或重建的策略；动态故障注入确认异常边界。

12. **当前静态证据不足以把以上问题归因到Stäubli现场。** 尚无现场PointCloud updater是否启用、sensor topic、point_subsample、PointCloud2字段布局、点云发布端、callback group/executor和map更新频率配置。以上是上游通用实现的审查结论，不证明Stäubli/ICube已触发无限循环、mask误分类、越界或地图部分更新。

#### 3. 修复建议（仅供上游评估，未修改上游）

- 参数入口拒绝`point_subsample == 0`，并验证范围与乘法边界。
- 增加PointCloud2结构校验器，校验point_step、row_step、width/height、data长度、字段名称/类型/count/offset、endianness及布局；对不支持的布局明确拒绝而非继续读取。
- 对坐标使用`std::isfinite`并检查OctoMap坐标范围；记录拒绝计数，避免每点高频日志。
- ShapeMask遇到缺失transform时，不应静默沿用旧pose；定义fail-closed/跳过shape/拒绝整帧语义，并保证bounding sphere只合并本帧有效项。
- stop流程增加明确的回调静默/析构协议：停止接收新消息、排空或取消待处理消息、等待in-flight callback退出，再释放updater和被捕获的this。
- OctoMap更新采用RAII读写锁，并定义updateNode中途失败的地图一致性策略；可考虑先构建变更集/副本再提交，或在失败后标记并重建地图。

#### 4. 新增验收任务

新增SERVO-741：

- **L1**：分别配置`point_subsample=0/1/2/UINT_MAX`，验证0在setParams阶段被拒绝，回调不挂死，边界值不会发生无符号回绕。
- **L2**：构造标准XYZ、XYZ字段非连续、字段偏移带padding、row_step大于width*point_step、big-endian点云，确认支持矩阵；不支持输入必须被明确拒绝。
- **L3**：注入point_step=0、data长度短于row_step*height、row_step不足、width*height乘法溢出和data长度非整点等消息，在ASan/UBSan下确认无除零、越界或越迭代器。
- **L4**：覆盖缺失x/y/z、非FLOAT32、count不为1、offset+字段宽度超过point_step等字段定义，确认错误返回而非未捕获异常。
- **L5**：输入NaN、正负Inf、极大有限坐标和零向量，验证finite与OctoMap key范围策略。
- **L6**：让transform callback对部分shape返回false，并在前后帧切换有效/无效transform，检查body pose与bounding sphere是否残留旧值及mask是否误分类。
- **L7**：多线程executor下并发excludeShape/forgetShape与maskContainment，运行TSan并测量shapes_lock_持有时间；验证无死锁和无旧handle误用。
- **L8**：在cloudMsgCallback的TF查询、updateTransformCache、maskContainment、read lock、write lock和publish各阶段设置barrier；并发调用stopMonitor并销毁monitor/updater，验证已排队及in-flight callback全部退出后才释放捕获对象。
- **L9**：分别使用单线程/多线程executor和带/不带TF MessageFilter的配置，验证MutuallyExclusive callback group实际覆盖范围；额外从非executor线程调用stop，确认callback静默协议。
- **L10**：在read阶段及write阶段注入异常，尤其在多次updateNode后抛出；验证锁释放、地图部分修改、update callback触发及filtered cloud发布语义。
- **L11**：并发运行PointCloud更新、OctoMap保存/加载服务和monitor停止/重启，使用TSan及锁超时检测确认tree锁顺序和服务生命周期。
- **L12**：在Stäubli/ICube现场确认PointCloud updater插件启用情况、点云topic/字段布局/row_step、point_subsample、executor和TF配置，并取得目标ROS发行版与日志。

L1–L12均未执行。没有ROS构建、ASan/UBSan/TSan、点云畸形输入测试、OctoMap故障注入、CS9/HIL或实机证据。

#### 5. 结论与边界

§9.3.158确认了若干可从源码直接定位的输入与状态处理缺口：零point_subsample会使循环不前进；PointCloud2结构缺少入口校验；NaN检查没有排除Inf；ShapeMask在transform缺失时仍继续使用body；OctoMap写入异常可能留下部分更新并继续触发通知。另识别stop删除订阅对象但没有显式in-flight callback屏障的生命周期待验证项。PointCloud消息由ConstSharedPtr在同步回调内持有，callback group为MutuallyExclusive；这两点是重要的风险边界，不能遗漏。

本轮仅完成MoveIt源码静态审查与SERVO-741测试设计。未运行ROS构建、ASan/UBSan/TSan、点云压力测试、OctoMap异常注入、CS9/HIL或实机验证；未修改MoveIt/ICube上游，未应用PR。Stäubli工程级验收未通过，TODO-EXT-001未授权合并。

#### 来源

- https://github.com/moveit/moveit2/blob/6ed6372a72ba9b121ed12ef574ea4ff4d3d92f09/moveit_ros/perception/pointcloud_octomap_updater/src/pointcloud_octomap_updater.cpp
- https://github.com/moveit/moveit2/blob/6ed6372a72ba9b121ed12ef574ea4ff4d3d92f09/moveit_ros/perception/pointcloud_octomap_updater/include/moveit/pointcloud_octomap_updater/pointcloud_octomap_updater.hpp
- https://github.com/moveit/moveit2/blob/6ed6372a72ba9b121ed12ef574ea4ff4d3d92f09/moveit_ros/perception/point_containment_filter/src/shape_mask.cpp
- https://github.com/moveit/moveit2/blob/6ed6372a72ba9b121ed12ef574ea4ff4d3d92f09/moveit_ros/perception/point_containment_filter/include/moveit/point_containment_filter/shape_mask.hpp
- https://github.com/moveit/moveit2/blob/6ed6372a72ba9b121ed12ef574ea4ff4d3d92f09/moveit_ros/occupancy_map_monitor/src/occupancy_map_updater.cpp
- https://github.com/moveit/moveit2/blob/6ed6372a72ba9b121ed12ef574ea4ff4d3d92f09/moveit_ros/occupancy_map_monitor/src/occupancy_map_monitor.cpp
- https://github.com/moveit/moveit2/blob/6ed6372a72ba9b121ed12ef574ea4ff4d3d92f09/moveit_ros/occupancy_map_monitor/include/moveit/occupancy_map_monitor/occupancy_map_updater.hpp
- https://github.com/ros2/common_interfaces/blob/rolling/sensor_msgs/include/sensor_msgs/point_cloud2_iterator.hpp


### §9.3.159 OctoMap更新回调、服务生命周期与读写锁边界

#### 1. 审查基线

本节基于MoveIt 2提交`6ed6372a72ba9b121ed12ef574ea4ff4d3d92f09`静态审查：

- `moveit_core/collision_detection/include/moveit/collision_detection/occupancy_map.hpp`，Blob SHA `514cd5a06136eb045abf5c31baad6b7aacd1933c`
- `moveit_ros/occupancy_map_monitor/src/occupancy_map_monitor.cpp`，Blob SHA `7b8bb7a42eed1eea01323458c816993828df3370`
- `moveit_ros/occupancy_map_monitor/include/moveit/occupancy_map_monitor/occupancy_map_monitor.hpp`，Blob SHA `d30741a6cb7635821e89f480d1142a1c8a8c6bb6`
- `moveit_ros/occupancy_map_monitor/src/occupancy_map_monitor_middleware_handle.cpp`，Blob SHA `4e870ca9f8f58ecd395beaecbdbff2ccad36eade`
- `moveit_ros/occupancy_map_monitor/src/occupancy_map_server.cpp`，Blob SHA `4976eb473e76d88ea06651dae11432eb6427fce7`
- `moveit_ros/planning/planning_scene_monitor/src/planning_scene_monitor.cpp`，Blob SHA `83f67e15cb167957ddf15bde8fc239d053ed727c`
- `moveit_ros/perception/pointcloud_octomap_updater/src/pointcloud_octomap_updater.cpp`，Blob SHA `e11a9f41d6dad68de31c83268e6bd686728eee9e`
- `moveit_ros/perception/depth_image_octomap_updater/src/depth_image_octomap_updater.cpp`，沿用§9.3.157已记录的源码基线。
- `moveit_ros/perception/lazy_free_space_updater/src/lazy_free_space_updater.cpp`，Blob SHA `9f092f4181637f369bfbdd0bd31d07214826b6db`

本节只审查MoveIt通用实现，不代表Stäubli/ICube现场使用了这些服务、server节点或多updater组合。

#### 2. 静态核查结论

1. **OctoMap树锁不保护更新回调对象。** `OccMapTree`的`tree_mutex_`只用于树读写；`setUpdateCallback()`直接给`update_callback_`赋值，`triggerUpdateCallback()`直接检查并调用该成员，二者都没有单独的互斥保护。PointCloud/DepthImage/Lazy updater以及load map路径在释放tree写锁后调用`triggerUpdateCallback()`。因此若系统在更新过程中并发替换/清空回调，存在对同一个`std::function`对象并发读写的数据竞争。常见初始化阶段先注册、再启动updater的顺序可避免该条件，但API没有把“只能在启动前设置、运行时不可更改”写成明确契约。

2. **多updater可并发触发同一个回调，未见全局串行化。** PointCloud和DepthImage回调来自各自ROS订阅执行路径，LazyFreeSpaceUpdater还有自己的process线程；各自更新后同步调用同一棵树的`triggerUpdateCallback()`。树写锁会串行化树写入，但回调在解锁后运行，所以两个更新线程可能在不同时间并发进入同一个回调。回调本身必须线程安全，或由OccMapTree统一串行化；当前接口没有明确保证。PlanningSceneMonitor的`octomapUpdateCallback()`使用`scene_update_mutex_`串行化场景更新，但这只是该消费者自己的保护，不是OccMapTree的全局保证。

3. **回调异常会从triggerUpdateCallback向上游传播。** `triggerUpdateCallback()`没有try/catch。PointCloud/Lazy/Depth updater在树写更新try/catch结束、unlock后调用它；若外部回调抛异常，异常会越过updater的地图更新异常处理边界。具体后果取决于回调执行线程和executor；可能导致ROS回调异常退出，Lazy updater线程则可能因未捕获异常终止。需定义回调异常隔离策略，并用故障注入验证。

4. **save/load服务回调捕获裸this，服务资源释放晚于树等核心成员。** OccupancyMapMonitor构造时创建两个lambda，均捕获`[this]`并转发到`saveMapCallback/loadMapCallback`。middleware handle持有ROS service shared_ptr；在类声明中`middleware_handle_`是首个成员，因此按C++逆序析构它最后销毁。析构函数体只调用`stopMonitor()`，并没有显式先禁用/销毁服务、等待in-flight service callback退出。其后`tree_`等成员会先于middleware_handle_销毁，而服务对象在此期间仍由middleware_handle_持有。若executor在监视器析构期间继续调度save/load请求，回调可能访问已销毁或正在析构的成员。该路径是**条件性服务生命周期风险**，需在目标rclcpp版本和多线程executor下做barrier/ASan验证，不能声称已复现UAF。

5. **stopMonitor不停止save/load服务。** `stopMonitor()`只将`active_`设为false并调用每个updater的`stop()`；服务句柄并未取消。因此“监控停止”不等于“地图服务停止”，停止后仍可请求保存/加载地图。这可能是有意设计，但API语义和系统关闭流程必须区分updater停止与monitor/service销毁。

6. **start/stop/isActive的active_没有同步。** `active_`是普通bool；`startMonitor()`、`stopMonitor()`写入，`isActive()`直接读取，源码未见原子或互斥保护。若应用允许多个线程并发启停和查询，构成数据竞争。若生命周期严格由单线程管理，则不触发；应明确线程调用约束或将状态改为受同步保护的状态。

7. **save/load的tree锁覆盖磁盘I/O，正确保护一致性但可能长时间阻塞传感器更新。** `saveMapCallback()`持有共享读锁直到`writeBinary()`完成；`loadMapCallback()`持有独占写锁直到`readBinary()`完成。save期间允许其他读者，但阻塞所有写更新；load期间阻塞读写。大地图、慢存储或网络文件系统可能让点云更新长期等待。当前没有超时、异步快照或耗时指标。应通过大地图/慢盘测试量化最坏阻塞时间；不可仅凭源码断言现场实时性不达标。

8. **手工锁释放目前覆盖了可见catch路径，但缺少RAII统一保证。** save/load回调在catch之后统一unlock；PointCloud/Lazy updater的read/write阶段也有手工catch/unlock。正常捕获异常时锁能释放；但未来新增提前return、抛出点或回调路径容易遗漏。OccMapTree已经提供`reading()/writing()`返回`std::shared_lock/std::unique_lock`，可以优先使用RAII。此前§9.3.158关于写更新非事务性的结论仍成立：锁释放不等于部分写入已回滚。

9. **load成功后在写锁外触发更新回调，顺序合理但消费者可能观察到下一帧更新。** `loadMapCallback()`在`readBinary()`返回成功后释放写锁，再触发回调；回调读取树时不会因同线程仍持有写锁而死锁。但另一updater可能在load释放锁与回调读取之间先取得写锁并更新地图，因此回调读取到的状态可能已经是“加载结果+后续传感器更新”，而不是严格的load完成瞬间快照。若系统要求精确加载快照，需要版本号/快照隔离或暂停updater协议；若只要求最终状态通知，则当前顺序可接受。

10. **occupancy_map_server在二进制序列化失败后仍无条件publish。** `publishOctomap()`在`binaryMapToMsgData()`返回false或抛异常时只记录日志，随后仍执行`octree_binary_pub->publish(map)`。此时map可能只有header而data为空/不完整；下游若把空消息当作有效地图，可能清空或破坏消费者侧地图状态。需要改为成功标志门控发布，并用模拟序列化失败的测试确认不会发送无效消息。当前仅确认服务端源码的无条件发布路径，尚未验证下游对空消息的实际解释。

11. **PlanningSceneMonitor消费者在回调中重新读取树，靠自身scene锁保护场景，但生命周期依赖停止顺序。** `octomapUpdateCallback()`检查`octomap_monitor_`、更新frame transforms、取得`scene_update_mutex_`并对树加读锁，处理Octomap后释放锁再触发场景事件。PlanningSceneMonitor析构顺序会调用`stopWorldGeometryMonitor()`，后者只调用`octomap_monitor_->stopMonitor()`，未在此处reset monitor或显式等待已经进入的OccMapTree update callback退出。该闭包捕获PSM的`this`，因此仍需验证正在执行的树更新回调是否可能越过PSM析构边界。此项与既有SERVO-729/741生命周期矩阵有交叉，新增本节只补充树回调调度路径，不重复宣称已证实故障。

12. **Stäubli现场使用范围仍未确认。** 当前没有现场证据证明启用了OccupancyMapMonitor的save/load服务、独立occupancy_map_server、多个updater并行或PlanningSceneMonitor Octomap回调组合。以上风险不得归因于Stäubli现场已部署或已发生。

#### 3. 修复建议（未修改上游）

- 对`update_callback_`明确线程契约：推荐在初始化阶段设置、启动后不可变；若支持运行时替换，应通过mutex保护复制回调快照，锁外执行，避免持锁调用用户代码。
- 定义回调并发与异常契约：若消费者不保证线程安全，则在树对象内部串行派发；捕获并记录回调异常，避免异常逃逸至后台线程入口。
- 增加显式shutdown：先拒绝新save/load请求并销毁service实体，再等待in-flight服务回调退出，之后停止updater并销毁tree及其他成员。具体次序应避免shutdown等待依赖已停止的executor。
- 明确`stopMonitor()`只停止传感器updater，不代表service shutdown；增加单独的服务停用接口或将服务生命周期纳入monitor关闭协议。
- 将`active_`改为atomic或用同一生命周期mutex保护start/stop/isActive，并规定start/stop不可并发重入。
- save/load采用RAII读写锁；对大地图评估快照/临时文件写入与原子rename，避免磁盘慢操作长时间占用地图锁及失败时破坏已有文件。
- server序列化失败时不要发布无效map；用成功标志门控publish，并提供失败计数/日志节流。
- 若需要严格的load快照通知，加入地图generation/version，或在load期间暂停updater并在恢复后统一通知。

#### 4. 新增验收任务

新增SERVO-742：

- **M1**：多线程持续触发`triggerUpdateCallback()`同时调用`setUpdateCallback()`替换/清空回调，使用TSan确认当前实现是否报数据竞争；比较初始化前注册、运行时替换两种用法。
- **M2**：两个独立updater线程通过barrier同时调用trigger，回调记录并发进入计数，确认是否重叠执行；验证回调的可重入和线程安全契约。
- **M3**：回调内调用`getOcTreePtr()->lockRead()`并读取树，确认trigger发生时写锁已释放且不死锁；同时覆盖回调抛异常。
- **M4**：使用会抛异常的回调分别从PointCloud、DepthImage、LazyFreeSpaceUpdater和load service触发，验证异常是否逃逸ROS callback/后台线程、是否导致线程终止或executor异常。
- **M5**：多线程executor中在save/load服务回调内设置barrier，同时析构OccupancyMapMonitor；使用ASan验证服务先停用、in-flight回调排空与tree成员销毁顺序。覆盖停止后请求服务和析构窗口内请求服务。
- **M6**：验证`stopMonitor()`后save_map/load_map服务仍可访问；明确产品所需语义，并测试显式shutdown后的拒绝行为。
- **M7**：并发startMonitor/stopMonitor/isActive，运行TSan；同时验证单线程串行调用的重启行为、重复start/stop幂等性。
- **M8**：大尺寸地图在慢盘/网络文件系统上save/load，测量读写锁持有时长、点云回调等待时间、更新丢弃率和端到端延迟。
- **M9**：对loadMap输入有效、缺失、截断、损坏文件，分别检查readBinary返回值、异常路径、原树是否保持、成功回调次数和下游地图版本；不预设失败加载是否会部分改写树。
- **M10**：在occupancy_map_server中注入binaryMapToMsgData返回false及异常，确认当前是否仍发布空/不完整消息；验证修复后失败不发布且下游地图不被清空。
- **M11**：PSM Octomap update callback处设置barrier，同时stopWorldGeometryMonitor并析构PSM；使用ASan/TSan验证捕获的this、scene_、octomap_monitor_生命周期和scene_update_mutex_顺序。
- **M12**：在Stäubli/ICube目标部署核实OccupancyMapMonitor插件列表、独立server启用情况、save/load服务暴露情况、PSM是否启用Octomap、executor线程数及回调组配置。

M1–M12全部未执行。没有ROS构建、TSan/ASan、慢盘性能测试、序列化失败注入、load损坏文件测试、CS9/HIL或实机证据。

#### 5. 结论与边界

§9.3.159确认：OccMapTree的树读写锁并不保护update_callback_；回调是同步调用且没有统一串行化/异常隔离；save/load service回调捕获monitor裸this且service资源销毁晚于tree等核心成员，存在条件性析构竞态；stopMonitor并不停止服务；active_没有同步；save/load磁盘I/O处于树锁保护区；occupancy_map_server序列化失败后仍无条件发布消息。多线程触发、回调替换、服务析构竞态和下游空消息效应仍需动态验证。

本轮仅完成静态审查与测试设计。未运行ROS构建、ASan/TSan、慢盘性能测试、load故障注入、序列化失败注入、CS9/HIL或实机验证；未修改MoveIt/ICube上游，未应用PR。Stäubli工程级验收未通过，TODO-EXT-001未授权合并。

#### 来源

- https://github.com/moveit/moveit2/blob/6ed6372a72ba9b121ed12ef574ea4ff4d3d92f09/moveit_core/collision_detection/include/moveit/collision_detection/occupancy_map.hpp
- https://github.com/moveit/moveit2/blob/6ed6372a72ba9b121ed12ef574ea4ff4d3d92f09/moveit_ros/occupancy_map_monitor/src/occupancy_map_monitor.cpp
- https://github.com/moveit/moveit2/blob/6ed6372a72ba9b121ed12ef574ea4ff4d3d92f09/moveit_ros/occupancy_map_monitor/include/moveit/occupancy_map_monitor/occupancy_map_monitor.hpp
- https://github.com/moveit/moveit2/blob/6ed6372a72ba9b121ed12ef574ea4ff4d3d92f09/moveit_ros/occupancy_map_monitor/src/occupancy_map_monitor_middleware_handle.cpp
- https://github.com/moveit/moveit2/blob/6ed6372a72ba9b121ed12ef574ea4ff4d3d92f09/moveit_ros/occupancy_map_monitor/src/occupancy_map_server.cpp
- https://github.com/moveit/moveit2/blob/6ed6372a72ba9b121ed12ef574ea4ff4d3d92f09/moveit_ros/planning/planning_scene_monitor/src/planning_scene_monitor.cpp
- https://github.com/moveit/moveit2/blob/6ed6372a72ba9b121ed12ef574ea4ff4d3d92f09/moveit_ros/perception/lazy_free_space_updater/src/lazy_free_space_updater.cpp


## §9.3.160｜PlanningSceneMonitor OctoMap回调、场景事件通知与锁顺序审查

### 审查基线
MoveIt 2固定提交：`6ed6372a72ba9b121ed12ef574ea4ff4d3d92f09`。检查`planning_scene_monitor.cpp/.hpp`及`planning_scene.cpp`。
- `planning_scene_monitor.cpp` Blob SHA：`83f67e15cb167957ddf15bde8fc239d053ed727c`
- `planning_scene_monitor.hpp` Blob SHA：`8ed8bd8fb8a3b25cfcb3357f2cc5de499a6fbd51`
- `planning_scene.cpp` Blob SHA：`71d4eac188cd7446b2013b61cf25b8b319e073c3`

### 静态核查结论

1. **主要scene/tree锁顺序一致。** `octomapUpdateCallback()`先取得`scene_update_mutex_`写锁，再取得OccMapTree读锁，调用`processOctomapPtr()`，释放树锁和scene锁后才触发`UPDATE_GEOMETRY`。PSM的`lockSceneRead()/lockSceneWrite()`及`clearOctomap()`也遵循scene→tree顺序。在本轮检查路径中未发现ABBA逆序；这不是全仓库无死锁证明。
2. **事件回调不持有scene/tree锁，但持有update_lock_。** `triggerSceneUpdateEvent()`使用`std::recursive_mutex`保护回调vector，并在锁内同步调用外部回调。scene锁释放避免了一类直接scene锁重入死锁，但外部回调仍可能阻塞注册/清理路径。
3. **回调重入可能破坏正在进行的vector遍历。** 同线程回调可重入`addUpdateCallback()`、`clearUpdateCallbacks()`和`triggerSceneUpdateEvent()`。当前实现未复制回调快照；遍历期间push导致vector扩容或clear可能使range-for迭代器失效，属于条件性未定义行为风险；递归触发还可能造成无界递归。若回调等待另一个需要取得update_lock_的线程，也可能形成跨线程等待死锁。
4. **回调异常可能造成场景事件通知遗漏。** 实现先执行所有外部回调，之后才累计`new_scene_update_`并`notify_all()`。任一回调抛异常会中断后续回调和通知；scene数据已经更新，但发布线程/等待者可能未收到该次通知。异常也会向OctoMap updater调用栈传播。
5. **双订阅stop存在明确清理缺口。** `stopWorldGeometryMonitor()`对`collision_object_subscriber_`和`planning_scene_world_subscriber_`使用`if/else if`。两者同时存在时只reset前者，后者保留，可能影响重启、重配置和析构期间的输入静默。
6. **OctoMap monitor stop不等于回调注销或排空。** stop路径调用`octomap_monitor_->stopMonitor()`，但不reset monitor、不清除PSM注册的`[this]`回调，也没有显式等待in-flight callback。PSM析构会停止world monitor并join其private SingleThreadedExecutor线程，但这不能自动证明OccupancyMapMonitor updater线程的回调已排空。结合§9.3.159的updater stop边界，析构竞态仍是待验证风险，未复现UAF。
7. **共享树同步语义。** `PlanningScene::processOctomapPtr()`在world对象已持有相同树指针且位姿未变时复用OcTree共享指针；指针变化时移除并重建shape。PSM的主要读写路径按scene→tree锁顺序访问。绕过PSM锁协议直接访问world/tree的外部代码不在本轮安全保证内。
8. **事件不是逐次更新队列。** scene/tree更新完成后释放锁，再发事件；并发读者可能在通知前看到新scene，这是锁保护下的可见性窗口。发布线程将更新类型按位合并，因此语义更接近“有相应类型更新待发布”，不保证每次树更新对应一个独立事件。
9. **executor边界不能外推。** PSM自身创建的`pnode_`使用SingleThreadedExecutor；这不证明OccupancyMapMonitor updater也运行在同一executor或同一callback group，更不能代表Stäubli现场配置。

### SERVO-743验证矩阵（全部未执行）

- **N1** callback遍历期间调用`addUpdateCallback()`触发vector扩容，ASan/UBSan验证。
- **N2** callback遍历期间调用`clearUpdateCallbacks()`，验证迭代器失效及快照修复。
- **N3** callback递归触发scene update，验证递归限制和事件顺序。
- **N4** callback等待另一线程执行add/clear，验证update_lock_跨线程等待死锁。
- **N5** 第一个callback抛异常，检查后续callback、`new_scene_update_`、条件变量唤醒和planning-scene发布。
- **N6** 同时启用两类world订阅，stop/restart并统计topic接收，验证旧订阅不残留。
- **N7** updater callback入口设置barrier，并发stopWorldGeometryMonitor和析构PSM，ASan/TSan检查this、scene、monitor生命周期。
- **N8** 并发OctoMap更新、clearOctomap、LockedPlanningSceneRO/RW和scene publishing，验证锁顺序。
- **N9** 并发OctoMap更新与PlanningSceneWorld替换/清空，核对OcTree指针、版本及事件类型。
- **N10** 多次stop/start，核对callback注册次数、monitor复用、订阅句柄和重复事件。
- **N11** 慢callback叠加高频OctoMap更新，测量updater阻塞、事件合并和发布延迟。
- **N12** Stäubli/ICube目标部署核实topic、updater线程、PSM executor、外部callback和shutdown顺序。

N1–N12全部未执行；没有动态证据证明迭代器失效、死锁、通知丢失、析构UAF或Stäubli现场受影响。

### 修复与验收建议

- 在`update_lock_`内复制callback快照，释放锁后调用；逐个隔离callback异常，并确保更新类型累计及条件变量通知不会被用户回调异常跳过。
- 明确递归触发策略；stop时分别reset两个world订阅。
- 为OccupancyMapMonitor定义stop的in-flight callback静默契约；析构前拒绝新事件、注销回调、停止updater并join/排空执行上下文，再销毁scene和PSM对象。
- 保持scene mutex→OctoMap tree lock顺序。修复后须在目标ROS/MoveIt/ICube组合执行单测、ASan/TSan和executor barrier测试。

### 证据边界
以上是固定MoveIt源码的静态结论。没有证据证明Stäubli现场启用相同topic/updater/callback组合或发生死锁、UAF、场景不同步。未运行ROS构建、ASan/UBSan/TSan、故障注入、CS9/HIL、FAT/SAT或实机测试；未修改MoveIt/ICube上游，未应用PR。

### 来源
- https://github.com/moveit/moveit2/blob/6ed6372a72ba9b121ed12ef574ea4ff4d3d92f09/moveit_ros/planning/planning_scene_monitor/src/planning_scene_monitor.cpp
- https://github.com/moveit/moveit2/blob/6ed6372a72ba9b121ed12ef574ea4ff4d3d92f09/moveit_ros/planning/planning_scene_monitor/include/moveit/planning_scene_monitor/planning_scene_monitor.hpp
- https://github.com/moveit/moveit2/blob/6ed6372a72ba9b121ed12ef574ea4ff4d3d92f09/moveit_core/planning_scene/src/planning_scene.cpp
- https://moveit.picknik.ai/main/api/html/moveit__ros_2planning_2planning__scene__monitor_2src_2planning__scene__monitor_8cpp_source.html


---

## §9.3.161｜PlanningSceneWorld / CollisionObject / OctoMap 输入替换语义与失败原子性

### 审查基线与文件

固定审查基线：MoveIt 2 commit `6ed6372a72ba9b121ed12ef574ea4ff4d3d92f09`。

- `moveit_ros/planning/planning_scene_monitor/src/planning_scene_monitor.cpp`（Blob SHA `83f67e15cb167957ddf15bde8fc239d053ed727c`）
- `moveit_ros/planning/planning_scene_monitor/include/moveit/planning_scene_monitor/planning_scene_monitor.hpp`（Blob SHA `8ed8bd8fb8a3b25cfcb3357f2cc5de499a6fbd51`）
- `moveit_core/planning_scene/src/planning_scene.cpp`（Blob SHA `71d4eac188cd7446b2013b61cf25b8b319e073c3`）
- `moveit_core/collision_detection/src/world.cpp`（Blob SHA `d4f12ac205b0725ad0ac5613c5a8762b3e701036`）
- `moveit_core/collision_detection/include/moveit/collision_detection/world.hpp`（Blob SHA `a3f41643b37b81264da2a3d691b093473a6e1dba`）

### 发现

1. **CollisionObject ADD 替换不是失败原子操作。** `processCollisionObjectAdd()` 对已有同ID对象先执行 `world_->removeObject(object.id)`，之后才构造并校验新对象形状/位姿。若 `shapesAndPosesFromCollisionObjectMessage()` 因“pose数量多于shape数量”等输入错误返回false，旧对象已被删除，新对象没有成功建立。PSM的 `processCollisionObjectMsg()` 在scene锁内收到false后直接返回，不会调用 `triggerSceneUpdateEvent(UPDATE_GEOMETRY)`。因此可能出现场景内容已改变但对应PSM更新事件未发出的状态。

2. **CollisionObject MOVE 存在部分提交。** `processCollisionObjectMove()` 先调用 `world_->setObjectPose()` 改变对象整体位姿，随后才检查可选shape pose总数是否与现有shape数量一致。数量不一致时返回false，但对象pose已经改变；PSM同样提前返回，不触发geometry update event。该路径的失败返回不能代表场景未发生改变。

3. **PlanningSceneWorld topic回调忽略逐项处理结果。** `newPlanningSceneWorldCallback()` 在scene锁内先 `clearObjects()`，再调用 `processPlanningSceneWorldMsg()`，但不读取/传播其bool结果，最后无条件触发 `UPDATE_SCENE`。后者逐个处理CollisionObject，使用 `result &= processCollisionObjectMsg(...)`，因此某一项失败不会阻止后续项；调用方却无法获知部分对象失败。完整world替换语义下，输入中一个对象失败可能留下“旧world已清空、部分新对象已应用”的部分场景。

4. **无效OctoMap类型可造成scene与monitor tree分裂。** `PlanningScene::processOctomapMsg()` 先移除world中的旧 `OCTOMAP_NS` 对象，再检查数据是否为空及 `id == "OcTree"`。对非空但类型不支持的消息，它移除了场景中的旧OctoMap后报错返回。PSM的world回调仅在OctoMap data为空时清空OccupancyMapMonitor树；非空错误类型不会清空monitor tree。之后若OccupancyMapMonitor触发update callback，`octomapUpdateCallback()`会通过 `processOctomapPtr()` 将monitor tree重新放回PlanningScene；在该回调发生前，scene world与monitor tree则可能暂时表示不同地图。该风险不等于已经证明下游规划必然使用错误地图，需动态验证时序和消费者行为。

5. **完整PlanningScene与diff的OctoMap语义不同。** `setPlanningSceneMsg()` 会清空world后处理world消息；`setPlanningSceneDiffMsg()` 只在OctoMap id非空时替换OctoMap，空字段表示diff未携带OctoMap更新。PSM对完整scene消息还会在OctoMap data为空时清空monitor tree。集成方必须区分“完整快照中的空地图”与“diff中未提供地图”，不能把两种空值语义混为一谈。

6. **CollisionObject REMOVE与输入失败需要分开统计。** 对不存在ID的REMOVE会返回false；PSM因此不触发geometry event。若对象确实不存在，这本身不改变scene；但调用方不应将该false与ADD/MOVE的“已部分改变scene后失败”归为同一类。建议在接口和遥测中区分no-op、validation failure、partial mutation。

7. **world observer与OctoMap mask副作用需要纳入测试。** World对象的remove/add/move操作会同步通知observer；PSM用observer维护普通world object与OccupancyMapMonitor排除shape的对应关系。ADD替换、MOVE部分失败及整world清空/重建都可能先后触发observer副作用。需要验证失败路径下shape handle是否最终与scene中的对象集合一致，不能只断言PlanningScene消息内容。

### 修复建议

- 对ADD：先在临时对象/临时shape集合中完成frame、shape、pose、subframe及类型校验，再以单一提交步骤替换旧对象；失败必须保留旧对象和旧颜色/类型/ACM元数据。
- 对MOVE：先完成全部pose数量、frame和isometry校验，再一次性提交对象pose与shape poses；或在失败时回滚。禁止“先改pose再验证”。
- 对PlanningSceneWorld完整替换：先在临时PlanningSceneWorld/临时scene构建并检查所有对象与OctoMap，再原子替换；若无法原子化，至少返回逐项结果、发出明确失败事件并保证消费者可检测部分更新。
- 对OctoMap：先验证id、payload和解码结果，再替换scene object；失败时保留旧地图。明确scene map与monitor tree的唯一权威源和同步策略，避免错误消息先清scene map而monitor tree仍持有旧地图。
- 对diff/full scene分别建立空OctoMap语义测试；完整快照空地图应明确表示清空，diff未提供地图则不得意外清空。
- 对World observer shape handles建立不变量检查：scene中每个需要排除的world object有且仅有对应有效handle；对象移除后handle全部释放；失败更新不得泄漏或遗留handle。

### SERVO-744｜失败原子性与World/OctoMap跨表示一致性验证矩阵

新增以下验证项，均为待执行：

- **M1 ADD替换失败**：先创建有效对象，再发同ID ADD，构造“shape少于pose”的畸形消息；断言失败后旧对象几何、pose、颜色、类型和ACM保持不变，且事件语义明确。
- **M2 ADD成功替换**：同ID合法ADD，检查只发生一次逻辑替换、shape observer handle无重复/泄漏，geometry event与最终scene一致。
- **M3 MOVE shape pose数量不足/过多**：记录更新前对象pose和shape poses，注入数量不匹配消息；验证失败后所有状态保持原值，不能出现整体pose已改而shape pose未改。
- **M4 MOVE合法路径**：同时改变object pose与shape poses，检查global shape pose、World observer事件和Octree排除shape变换一致。
- **M5 PlanningSceneWorld部分失败**：输入多个对象，其中一项畸形；记录world清空、各项应用、返回/日志和scene event，验证接口能明确报告部分失败或保证原子回滚。
- **M6 无效OctoMap类型**：先建立有效scene OctoMap和monitor tree，再提交非空、错误id的OctoMap；验证旧地图保留策略、monitor tree内容、下一次octomapUpdateCallback结果及scene diff。
- **M7 OctoMap解码异常/截断数据**：对binary与full map payload分别注入损坏数据/异常，检查旧scene地图与monitor tree是否保持一致，不允许先删除旧地图再失败。
- **M8 full scene空OctoMap**：验证完整快照明确清空scene OctoMap和monitor tree，且清理事件/scene publisher diff正确。
- **M9 diff未携带OctoMap**：在现有地图下提交is_diff=true且OctoMap字段未设置的scene diff，确认地图保持；另测显式清空协议。
- **M10 REMOVE不存在对象**：确认返回false/no-op不会改变scene、observer handles或OctoMap masks；与部分提交失败分类分开。
- **M11 World observer与shape handle一致性**：对ADD/APPEND/MOVE/REMOVE/整world替换执行长时间序列压力测试，核对handle数量、对象ID映射和OctoMap排除结果；使用ASan/TSan并记录地图更新延迟。
- **M12 Stäubli/ICube目标部署核实**：确认实际订阅的collision_objects/planning_scene_world/planning_scene topic、消息来源与完整/增量语义、OctoMap monitor插件、QoS/executor配置及上游消息生产者是否可能发出畸形/不完整输入。

M1–M12全部未执行。没有运行ROS构建、单元测试、ASan/UBSan/TSan、OctoMap损坏数据注入、World observer压力测试、CS9/HIL、FAT/SAT或实机验证。

### 结论与证据边界

§9.3.161确认三类需要优先验证的失败一致性风险：ADD/MOVE部分提交后返回false但PSM不发更新事件；PlanningSceneWorld回调忽略逐项处理结果并在部分失败后仍发UPDATE_SCENE；无效OctoMap类型可先移除scene地图而保留monitor tree。它们是固定MoveIt源码基线的静态结论，不证明Stäubli现场已启用相同topic组合，也不证明现场已经发生地图丢失、碰撞漏检或规划安全事件。

本轮仅完成静态审查与测试设计。未运行ROS构建、ASan/UBSan/TSan、故障注入、executor压力测试、CS9/HIL、FAT/SAT或实机验证；未修改MoveIt/ICube上游，未应用PR。Stäubli工程级验收未通过，TODO-EXT-001未授权合并。

### 来源

- https://github.com/moveit/moveit2/blob/6ed6372a72ba9b121ed12ef574ea4ff4d3d92f09/moveit_ros/planning/planning_scene_monitor/src/planning_scene_monitor.cpp
- https://github.com/moveit/moveit2/blob/6ed6372a72ba9b121ed12ef574ea4ff4d3d92f09/moveit_ros/planning/planning_scene_monitor/include/moveit/planning_scene_monitor/planning_scene_monitor.hpp
- https://github.com/moveit/moveit2/blob/6ed6372a72ba9b121ed12ef574ea4ff4d3d92f09/moveit_core/planning_scene/src/planning_scene.cpp
- https://github.com/moveit/moveit2/blob/6ed6372a72ba9b121ed12ef574ea4ff4d3d92f09/moveit_core/collision_detection/src/world.cpp
- https://github.com/moveit/moveit2/blob/6ed6372a72ba9b121ed12ef574ea4ff4d3d92f09/moveit_core/collision_detection/include/moveit/collision_detection/world.hpp


---

## §9.3.162｜PlanningSceneMonitor 发布线程、diff 累积与订阅端同步审查

### 审查基线与文件

固定审查基线：MoveIt 2 commit `6ed6372a72ba9b121ed12ef574ea4ff4d3d92f09`。

- `moveit_ros/planning/planning_scene_monitor/src/planning_scene_monitor.cpp`（Blob SHA `83f67e15cb167957ddf15bde8fc239d053ed727c`）
- `moveit_ros/planning/planning_scene_monitor/include/moveit/planning_scene_monitor/planning_scene_monitor.hpp`（Blob SHA `8ed8bd8fb8a3b25cfcb3357f2cc5de499a6fbd51`）
- `moveit_core/planning_scene/src/planning_scene.cpp`（Blob SHA `71d4eac188cd7446b2013b61cf25b8b319e073c3`）

### 发现

1. **发布线程启动时的第一份全量快照未持有scene mutex。** `scenePublishingThread()`启动后立即调用`scene_->getPlanningSceneMsg(msg)`，仅在有`octomap_monitor_`时取得OctoMap tree读锁；没有取得`scene_update_mutex_`。与之对照，后续增量序列化位于`scene_update_mutex_`写锁内。若启动发布时另一executor回调正在修改RobotState、World或PlanningScene，首份快照可能与写操作并发，形成数据竞争或内部字段不一致。此项由静态锁路径可直接确认，实际触发仍需TSan/并发barrier复现。

2. **更新事件位存在“新事件被发布线程清零覆盖”的竞态。** `triggerSceneUpdateEvent()`在`update_lock_`下执行回调并对原子`new_scene_update_`进行load-OR-store；发布线程在`scene_update_mutex_`下读取待发事件、构建消息后无条件将其赋为`UPDATE_NONE`。两者没有共同互斥协议：若发布线程已读取旧事件，随后新的scene update完成并OR写入新事件，而发布线程之后再执行清零，新事件位会被覆盖。原子变量保证单次读写原子性，但不使“并发OR与无条件清零”成为原子事务。结果可能是场景已经变化而没有对应发布事件；后续其他更新或全量快照可能掩盖，但不能作为可靠保证。

3. **事件通知与condition_variable的谓词锁不一致。** 发布线程在`scene_update_mutex_`保护下检查`new_scene_update_ == UPDATE_NONE`并等待；触发方更新原子事件并notify，但不取得`scene_update_mutex_`。因此存在检查谓词与进入wait之间的通知竞态窗口：通知可能在等待线程真正阻塞前发出，线程随后睡眠，而谓词已经非空。由于没有下一次事件，发布可能一直停滞。应通过同一mutex保护谓词变更/通知，或采用具备可靠序列号/事件队列的等待协议。是否能在目标rclcpp/标准库环境稳定复现需barrier测试。

4. **事件bitmask是“触发门控”，并非逐类过滤已累积diff。** 发布线程判断`publish_update_types_ & new_scene_update_`是否命中；命中后调用`getPlanningSceneDiffMsg()`并`pushDiffs()/clearDiffs()`，取出的是当前diff scene已累积的整体差异，而不是只序列化命中的事件类别。未命中的事件会清掉pending event bits，但不会清除scene diff accumulator；之后一个命中事件到来时，之前未命中的类别可能随同本次diff一起发布。这可能是为避免丢失变化而采用的累积策略，但接口的event mask语义必须明确：它控制发布触发时机，不保证对消息内容做类别过滤。集成方不能把“仅订阅UPDATE_STATE”理解为几何数据绝不会搭载在某次state触发消息中。

5. **事件合并使UPDATE_STATE专用剥离逻辑仅在精确相等时生效。** 代码只在`new_scene_update_ == UPDATE_STATE`时清空diff中的`attached_collision_objects`。若STATE与GEOMETRY事件在一次发布前合并为复合bitmask，该分支不执行，attached collision objects随完整diff保留。若几何事件本来就需要同步attached objects，这是合理行为；但应测试并文档化复合事件行为，不能假设state bit存在就会剥离attached objects。

6. **完整场景与增量发布的恢复语义不同。** 发布器启动时发送一次全量场景；之后只有`UPDATE_SCENE`事件强制发送全量场景，其余命中事件发送diff。发布端没有显示周期性全量校准或订阅端确认/重传机制。若订阅端启动晚于初始全量快照、丢失消息、重启或错过增量，则仅靠后续diff未必能恢复其完整状态，除非应用层另行请求全量PlanningScene。ROS publisher history depth为100并不等于对任意迟加入订阅者保证可获取初始快照；实际QoS durability和late-join行为须在目标配置下验证。

7. **stop/start发布生命周期缺少并发调用契约。** `stopPublishingPlanningScene()`通过swap移动`publish_planning_scene_`并notify/join线程，但发布线程自身在wait predicate和do-while条件中读取同一个unique_ptr；该unique_ptr的读写没有共同锁。若start/stop被多个线程并发调用，存在对unique_ptr并发读写的风险。若API只允许由单一管理线程串行调用，应明确文档约束；若允许并发，则需要状态mutex/atomic stop flag和join生命周期协议。此项不应推断为常规单线程调用必然有问题。

8. **全量/增量消息的序列化与发布不是一个端到端事务。** 线程先在scene锁内构建消息，释放锁后调用ROS publisher。锁释放后scene可继续前进，因此消息代表的是构建时快照而非publish调用时最新状态；这是正常快照语义，但消息缺少本地单调版本号/确认序列时，订阅端难以检测缺口并判断是否需要重新请求全量状态。应考虑在应用层携带generation/sequence并提供全量同步入口。

### 修复建议

- 首次全量快照也必须在`scene_update_mutex_`下序列化；同时按统一锁顺序取得OctoMap tree读锁，避免scene与OctoMap来自不同时间点。
- 将pending event更新、读取和清零纳入同一同步协议。可在同一mutex下交换pending bitmask到局部变量后再构建消息；或使用原子`exchange(UPDATE_NONE)`并确保并发OR不会被覆盖。condition_variable谓词更新也必须与wait使用同一mutex协调。
- 推荐以单调generation计数或有界事件队列记录变更；发布线程消费特定generation，消息构建失败/发布失败时保留待重试状态。
- 明确publish event mask只控制“哪些事件可触发一次diff发送”，还是要求过滤diff内容；如果要求内容过滤，应分类型维护diff accumulator或从不可变快照中按组件构建消息。
- 明确复合事件行为，覆盖STATE、GEOMETRY、TRANSFORMS及UPDATE_SCENE同时/连续到达的情况。
- 对迟加入、重启、消息缺口提供显式全量快照请求/同步握手；必要时加入generation与sequence检查和定期全量校准。
- 将publisher lifecycle限定为单线程串行调用，或为start/stop/join增加专用状态锁和原子停止标志；禁止线程并发访问同一个unique_ptr。
- 订阅端收到diff前必须已建立同一基线快照；检测到sequence gap、model mismatch或diff apply失败时请求完整场景，而不是继续使用不确定的scene。

### SERVO-745｜发布线程与订阅端一致性验证矩阵

新增以下验证项，均为待执行：

- **N1 启动全量快照竞态**：在startPublishingPlanningScene与RobotState/World写入之间设置barrier；TSan检查首份`getPlanningSceneMsg()`是否与写线程并发，校验消息内部RobotState、World和OctoMap快照一致。
- **N2 pending event清零覆盖**：阻断发布线程在读取pending mask与写回NONE之间，注入第二个事件；验证第二个事件必须被发布或保留待发，不得被旧批次清除。
- **N3 condition_variable丢唤醒**：在谓词检查与wait进入之间注入事件，确认线程不会在pending非空时无限睡眠；覆盖多次事件和stop唤醒。
- **N4 并发事件合并**：同时注入STATE、GEOMETRY、TRANSFORMS、SCENE，记录event bitmask、实际PlanningScene消息组件、attached_collision_objects及diff accumulator清理边界。
- **N5 publish_update_types门控语义**：分别只启用STATE/GEOMETRY/TRANSFORMS，先注入未启用事件再注入启用事件；验证未启用类别是否会随累积diff搭载，确保行为与文档一致。
- **N6 STATE与GEOMETRY合并**：验证复合bitmask下attached collision objects、robot_state.is_diff及world object变化都能正确应用，不能把复合事件误当纯STATE。
- **N7 UPDATE_SCENE全量恢复**：构造先diff、后UPDATE_SCENE的序列，确认全量消息可覆盖订阅端旧对象/旧ACM/旧OctoMap等残留状态。
- **N8 late-join与subscriber restart**：分别在publisher启动前后加入订阅者、重启订阅端、丢弃一条diff；验证QoS实际行为、全量请求机制和恢复时间。
- **N9 sequence/generation缺口检测**：在测试harness中为每个逻辑scene update打序号，随机丢弃/重排/重复diff，验证订阅端能识别缺口并请求full scene。
- **N10 start/stop并发与重复调用**：多线程调用start/stop/stop，使用TSan/ASan检查unique_ptr读写、线程join、publisher销毁和重启竞态；另验证串行调用幂等性。
- **N11 publish序列化压力**：大World/OctoMap与高频RobotState并发更新，测量scene lock持有时间、发布延迟、积压bitmask和diff大小；检查是否长期饥饿。
- **N12 Stäubli/ICube目标部署核实**：记录publish_planning_scene、publish_geometry_updates、publish_state_updates、publish_transforms_updates、publish_planning_scene_hz、publisher topic/QoS、late-join策略、订阅端是否请求全量快照，以及真实executor线程/回调组配置。

N1–N12全部未执行。没有运行ROS构建、单元测试、TSan/ASan、barrier并发测试、QoS late-join测试、消息丢弃/重排注入、CS9/HIL、FAT/SAT或实机验证。

### 结论与证据边界

§9.3.162识别PlanningSceneMonitor发布路径的三个优先并发风险：启动全量快照缺少scene mutex；pending event bitmask可能被发布线程清零覆盖；condition_variable谓词更新与等待未共享同一mutex，存在丢唤醒窗口。另确认事件mask是发布触发门控而非逐类过滤累积diff，且发布器没有内建订阅端确认/缺口恢复握手。以上是MoveIt固定提交源码静态结论，不证明Stäubli现场使用相同发布参数/QoS，也不证明现场已发生场景消息丢失或规划安全事件。

本轮仅完成静态审查与测试设计。未运行ROS构建、单元测试、TSan/ASan、barrier并发测试、QoS late-join测试、消息丢弃/重排注入、CS9/HIL、FAT/SAT或实机验证；未修改MoveIt/ICube上游，未应用PR。Stäubli工程级验收未通过，TODO-EXT-001未授权合并。

### 来源

- https://github.com/moveit/moveit2/blob/6ed6372a72ba9b121ed12ef574ea4ff4d3d92f09/moveit_ros/planning/planning_scene_monitor/src/planning_scene_monitor.cpp
- https://github.com/moveit/moveit2/blob/6ed6372a72ba9b121ed12ef574ea4ff4d3d92f09/moveit_ros/planning/planning_scene_monitor/include/moveit/planning_scene_monitor/planning_scene_monitor.hpp
- https://github.com/moveit/moveit2/blob/6ed6372a72ba9b121ed12ef574ea4ff4d3d92f09/moveit_core/planning_scene/src/planning_scene.cpp


## §9.3.163 GetPlanningScene服务与requestPlanningSceneState全量同步链路（2026-11-09）

### 审查范围与固定基线

基于MoveIt 2仓库固定提交`6ed6372a72ba9b121ed12ef574ea4ff4d3d92f09`，静态检查：

- `moveit_ros/planning/planning_scene_monitor/src/planning_scene_monitor.cpp`：`requestPlanningSceneState()`、`getPlanningSceneServiceCallback()`、`newPlanningSceneMessage()`、`startSceneMonitor()`、`updateFrameTransforms()`。
- `moveit_ros/planning/planning_scene_monitor/include/moveit/planning_scene_monitor/planning_scene_monitor.hpp`：服务/订阅API契约及默认服务名。
- `moveit_core/planning_scene/src/planning_scene.cpp`：组件选择序列化、full/diff应用和world处理。
- `moveit_core/planning_scene/include/moveit/planning_scene/planning_scene.hpp`：full/diff API语义。

源码Blob SHA：
- planning_scene_monitor.cpp：`83f67e15cb167957ddf15bde8fc239d053ed727c`
- planning_scene_monitor.hpp：`8ed8bd8fb8a3b25cfcb3357f2cc5de499a6fbd51`
- planning_scene.cpp：`71d4eac188cd7446b2013b61cf25b8b319e073c3`
- planning_scene.hpp：`a141b9f7e5898b486df851204c555a0c20a220c0`

### 静态发现

1. **请求端将服务可达/响应ready等同于场景应用成功，忽略应用返回值。** `requestPlanningSceneState()`等待服务最多5秒，发起异步请求后再等待最多5秒；future ready时调用`newPlanningSceneMessage(response.scene)`，但丢弃其bool结果并直接return true。下游`newPlanningSceneMessage()`的返回值来自`PlanningScene::setPlanningSceneMsg()`或`usePlanningSceneMsg()`，后者可能因world中的CollisionObject处理失败返回false。因此API的true只证明收到响应且进入应用路径，不保证完整场景成功应用。应区分transport success、message apply success和scene validation success。

2. **full scene应用不是事务式提交，失败后无回滚。** 对非diff消息，PSM在`scene_update_mutex_`下调用`parent_scene_->setPlanningSceneMsg(scene)`（有parent时先`scene_->clearDiffs()`），或调用`scene_->usePlanningSceneMsg(scene)`。`setPlanningSceneMsg()`会先更新name、解耦parent、替换transforms/current state/ACM/padding/scale/object colors，清空world objects，再调用`processPlanningSceneWorldMsg()`；后者逐项处理CollisionObject并汇总bool结果，OctoMap随后处理。若后续world对象处理失败，之前已写入的状态不会自动恢复，且PSM仍会在锁外触发`UPDATE_SCENE`并返回false。结合第§9.3.161节的逐对象非原子处理发现，服务响应应用失败可能留下部分新场景，而非保留旧场景。需要构造坏对象/坏OctoMap注入测试确定可观测残留范围。

3. **请求端可能把旧服务快照覆盖到较新的topic更新之上。** 服务请求等待期间，`startSceneMonitor()`订阅回调仍可通过`newPlanningSceneMessage()`更新本地场景。场景锁只保证每次应用串行，不携带服务快照generation、source timestamp或请求开始时的本地版本比较。若较新的topic消息先应用、较早采样的服务响应后返回并应用，后者可能覆盖较新状态。是否发生取决于服务端快照时刻、网络延迟、executor调度和调用方并发；静态代码没有版本冲突检测或“仅在初始化时应用”保护。

4. **服务端响应序列化有场景锁保护，但TF刷新与完整响应不是同一个临界区。** `getPlanningSceneServiceCallback()`在请求包含TRANSFORMS时先调用`updateFrameTransforms()`；该函数自行取得/释放`scene_update_mutex_`并触发TRANSFORMS事件。服务回调随后再次取得该锁并调用`getPlanningSceneMsg()`。所以响应序列化期间scene数据受锁保护，但TF刷新与最终序列化之间允许其他场景更新介入；不能将两段操作视为同一原子快照。应确认产品是否要求机器人状态、World与TF具有同一采样时刻，以及TF时间戳/缓存策略。

5. **组件掩码默认值与全量请求需明确区分。** 服务端请求掩码为0时用`UINT_MAX`请求所有组件；显式掩码只序列化指定组件，且响应`is_diff=false`。客户端`requestPlanningSceneState()`显式请求SCENE_SETTINGS、ROBOT_STATE、ROBOT_STATE_ATTACHED_OBJECTS、WORLD_OBJECT_NAMES、WORLD_OBJECT_GEOMETRY、OCTOMAP、TRANSFORMS、ALLOWED_COLLISION_MATRIX、LINK_PADDING_AND_SCALING和OBJECT_COLORS。由于组件序列化会省略未选字段，而full场景应用会替换/清空多个字段，外部调用者不能把任意部分组件响应直接当作完整快照交给`setPlanningSceneMsg()`；需用契约或专用patch应用方式避免“未请求字段被解释为空”。

6. **WORLD_OBJECT_NAMES与WORLD_OBJECT_GEOMETRY是二选一分支。** `getPlanningSceneMsg()`优先处理WORLD_OBJECT_GEOMETRY；只有未请求geometry而请求names时，才输出仅含ID/type的对象。客户端同时请求二者，因此得到几何数据。第三方客户端只请求names时，响应对象没有完整shape/pose，不能用于碰撞场景重建；且因为`is_diff=false`，必须避免把这种轻量查询响应直接作为full scene替换本地world。

7. **失败恢复路径有限且调用方必须检查返回值。** 服务不可用或等待超时返回false，现有代码不会主动清空本地场景；这是保留旧状态的路径。服务响应ready但应用失败时则存在第1、2点问题：函数仍返回true，且场景可能部分改变。当前实现没有构建临时PlanningScene后原子swap、失败回滚、响应完整性校验或版本冲突重试。服务端序列化本身也没有显式错误状态字段用于表示某组件缺失/读取失败。

8. **同步等待可能与executor调度形成条件性死锁/超时。** API内部同步等待service可用与future完成。如果从同一executor中必须由该executor执行的回调内调用，而executor没有其他可运行线程/执行路径处理client response，则可能等待超时或阻塞；具体是否触发取决于调用线程、callback group、executor类型与线程数，源码审查不能假定部署默认值。禁止将该风险表述为所有调用都会死锁。

9. **topic订阅与service恢复是两条独立同步路径。** `startSceneMonitor()`使用`rclcpp::ServicesQoS()`订阅PlanningScene topic；`requestPlanningSceneState()`走GetPlanningScene service。固定代码未提供服务响应与topic更新之间的统一序列号、时间戳仲裁或去重协议。重启/late join后通常需要调用方显式请求full scene；请求成功与否应在应用层核验。QoS具体兼容性及Stäubli现场配置需单独确认。

### 新增验证任务 SERVO-746 / O1–O12

- O1：构造有效服务响应，验证完整组件均被应用且请求返回true。
- O2：构造world中前项有效、后项无效的full scene，记录`newPlanningSceneMessage()`返回值、外部请求返回值及本地各组件残留；验证部分提交。
- O3：对服务响应注入无效CollisionObject/OctoMap，验证失败后旧world/robot state/ACM/padding/colors是否可恢复。
- O4：在service请求等待期间先注入较新topic full/diff，再释放旧服务响应；验证是否发生旧快照覆盖新更新。
- O5：在服务端响应生成阶段并发更新robot state、world和TF，检查序列化快照内部版本/时间戳一致性。
- O6：逐项测试0掩码、仅TRANSFORMS、仅WORLD_OBJECT_NAMES、仅WORLD_OBJECT_GEOMETRY、OCTOMAP及全部组件的字段完整性与`is_diff`。
- O7：将部分组件响应交给full apply API，确认哪些未请求字段会被清空/重置；形成禁止用法测试。
- O8：服务不存在、等待5秒超时、响应future超时、服务端异常及请求取消时，确认本地场景是否保持旧状态、调用方告警和重试策略。
- O9：分别从普通线程、单线程executor回调、多线程executor回调调用同步请求，记录阻塞、超时和死锁情况。
- O10：service与scene topic同时启用，改变回包延迟/消息顺序，验证更新仲裁、重复应用与最终一致性。
- O11：late join、publisher restart、service server restart后请求full scene，验证World/OctoMap/ACM/attached objects恢复。
- O12：在Stäubli/ICube部署核实真实service名称/命名空间、组件掩码、调用线程、executor/callback group、topic QoS、服务超时、快照频率与上层对bool返回值的处理。

O1–O12全部未执行。未运行ROS构建、单元测试、故障注入、并发调度测试、QoS/服务重启测试、CS9/HIL、FAT/SAT或实机验证。

### 结论与证据边界

§9.3.163确认GetPlanningScene服务端在scene锁内序列化所选组件；零组件掩码表示请求全部组件，客户端默认请求全量组件。主要风险为请求端忽略场景应用bool结果、full scene应用缺少事务回滚、并发topic更新与较旧service快照之间缺少版本仲裁，以及部分组件响应被误用为完整场景时可能造成字段清空。同步等待与executor之间存在条件性阻塞风险，需依据实际调用上下文验证。

以上是MoveIt固定提交源码静态结论，不证明Stäubli/ICube现场采用相同调用顺序、executor/QoS或已发生场景回退、场景部分提交、碰撞漏检或运动安全事件。未运行ROS构建、单测、故障注入、并发/服务超时/QoS测试、CS9/HIL、FAT/SAT或实机验证；未修改MoveIt/ICube上游，未应用PR。Stäubli工程级验收未通过，TODO-EXT-001未授权合并。

### 来源

- https://github.com/moveit/moveit2/blob/6ed6372a72ba9b121ed12ef574ea4ff4d3d92f09/moveit_ros/planning/planning_scene_monitor/src/planning_scene_monitor.cpp
- https://github.com/moveit/moveit2/blob/6ed6372a72ba9b121ed12ef574ea4ff4d3d92f09/moveit_ros/planning/planning_scene_monitor/include/moveit/planning_scene_monitor/planning_scene_monitor.hpp
- https://github.com/moveit/moveit2/blob/6ed6372a72ba9b121ed12ef574ea4ff4d3d92f09/moveit_core/planning_scene/src/planning_scene.cpp
- https://github.com/moveit/moveit2/blob/6ed6372a72ba9b121ed12ef574ea4ff4d3d92f09/moveit_core/planning_scene/include/moveit/planning_scene/planning_scene.hpp


### §9.3.163复核补充：服务响应成功状态与场景应用状态分离

实现层面需将三个结果分别记录：①服务发现/请求是否完成；②响应是否包含预期组件；③本地PlanningScene是否完整应用。当前bool接口将前两者近似为true路径，且忽略第三者的返回值，因此上层不应仅凭`requestPlanningSceneState()==true`作为碰撞场景完整性的唯一证明。建议下游部署在同步后执行独立场景完整性检查（机器人模型名、必需joint state、World对象清单/几何、OctoMap策略、ACM及TF），并记录来源时间戳/版本；在未实现原子替换前，应用失败应视为本地场景可能处于部分更新状态，不应自动继续规划或运动。该建议属于风险控制设计，不代表MoveIt当前已实现这些检查，也不替代CS9/HIL与现场安全验证。


## §9.3.164 requestPlanningSceneState调用方与初始化门禁审查（2026-11-09）

### 审查范围与固定基线

继续基于MoveIt 2固定提交`6ed6372a72ba9b121ed12ef574ea4ff4d3d92f09`，沿调用点检查返回值消费、调用时executor状态、失败后的下游动作及测试覆盖：

- MoveIt Servo：`moveit_ros/moveit_servo/src/utils/common.cpp`、`src/servo_node.cpp`、`config/servo_parameters.yaml`、`config/panda_simulated_config.yaml`及C++ demo。
- RViz：`moveit_ros/visualization/planning_scene_rviz_plugin/src/planning_scene_display.cpp`。
- OMPL工具：`moveit_planners/ompl/ompl_interface/scripts/generate_state_database.cpp`。
- 场景打印工具：`moveit_ros/planning/planning_components_tools/src/print_planning_scene_info.cpp`。
- Python绑定：`moveit_py/src/moveit/moveit_ros/planning_scene_monitor/planning_scene_monitor.cpp`。
- API实现与契约：PlanningSceneMonitor cpp/hpp。

源码Blob SHA：
- Servo common.cpp：`7ce13c1805ba6bce2e58be10828034f35b60471a`
- Servo servo_node.cpp：`eef6cc4073e03863a08eebbf69dc7cefedb15ebc`
- Servo servo_parameters.yaml：`b16fc6bf0c31fea680529b797c9101827ac6024f`
- Servo panda_simulated_config.yaml：`6c8386b98d1086ffa0d372f779f40d8269635477`
- Servo demo_twist.cpp：`c2f4f8d236679e8495d798ce184efc0ec951f17d`
- RViz planning_scene_display.cpp：`56e5c4444fa10ba3c820fcfcc78b8571f7f2b558`
- OMPL generate_state_database.cpp：`fe30f37753d594266de71180bbdad72e600dadf9`
- print_planning_scene_info.cpp：`72a5491fb6dc2c5fab9d744cf471ef13ffe4c3f7`
- Python binding：`53a2730013710e97879a6f53df39912108fdb713`
- PlanningSceneMonitor cpp/hpp：`83f67e15cb167957ddf15bde8fc239d053ed727c` / `8ed8bd8fb8a3b25cfcb3357f2cc5de499a6fbd51`

### 静态发现

1. **Servo次级PSM路径忽略初始场景请求失败，仍继续启动发布。** `createPlanningSceneMonitor()`先启动joint state、scene topic和world geometry monitor；若`is_primary_planning_scene_monitor=true`则提供GetPlanningScene服务，否则调用`requestPlanningSceneState()`，但不检查bool返回值。随后无条件设置发布频率并启动`UPDATE_SCENE`发布器，最后返回PSM。因而次级PSM在服务不可用、超时或同步应用失败时，不会在该函数中阻止初始化，也不会明确报告同步失败；其本地场景是否由后续topic更新补齐取决于外部拓扑。若未补齐，该PSM仍会继续向自己的发布topic发布本地场景。该风险只适用于secondary配置路径；Servo参数默认`is_primary_planning_scene_monitor=true`，示例配置也设为true，不能据此泛化为默认配置必然请求服务。

2. **PSM自带private executor，外部node executor未spin本身不是这些直接调用点的失败原因。** 进一步复核`PlanningSceneMonitor::initialize()`发现：PSM创建独立`pnode_`，将其加入`private_executor_`（SingleThreadedExecutor），并启动`private_executor_thread_`持续spin；`requestPlanningSceneState()`也在该`pnode_`上创建client。因此Servo构造期间、C++ demo主流程、OMPL工具或场景打印工具没有显式spin其外部node executor，并不能据此推断PSM service future必然超时。真正的条件性阻塞场景是：调用`requestPlanningSceneState()`的线程本身正是PSM private executor正在执行回调的线程；同步等待会阻止该单线程executor处理client response。已审查的Servo/RViz/OMPL/print直接调用点分别在构造/普通主线程或RViz background job中，没有静态证据证明它们从PSM private executor回调内部调用；Python调用方上下文需另行验证。

3. **OMPL状态数据库工具检查bool，是调用方中较明确的失败门禁。** `generate_state_database.cpp`在`use_current_scene`时检查`requestPlanningSceneState()`并在false时退出。虽然工具main本身未spin外部node executor，但PSM的private executor会处理其内部client，因此不能将外部executor未spin列为此调用点的静态缺陷。仍需注意§9.3.163中的bool语义缺陷：若服务响应应用失败被底层忽略，OMPL仍可能收到true并继续生成数据库；若服务不可用/超时则会退出。

4. **print_planning_scene_info忽略请求结果，不能证明打印的是远端最新场景。** 工具创建`MultiThreadedExecutor`并`add_node(node)`但未显式spin该外部node；然而PSM有独立private executor负责其`pnode_`上的service client，所以不能据此认定请求必然超时。该工具仍忽略`requestPlanningSceneState()`的bool结果，随后无条件打印本地已知对象；服务不可用/超时或底层apply失败时，输出可能是空/旧/部分场景，且工具没有报告同步失败。

5. **RViz正确采用后台任务并处理bool，但受底层bool语义缺陷污染。** `changedPlanningSceneTopic()`启动scene topic订阅后，将service请求放入background job；bool为true时安排主线程`onNewPlanningSceneState()`，false时设置“Requesting initial scene failed”警告。后台执行避免直接阻塞UI主循环，且显式处理false；但由于§9.3.163发现底层在场景应用返回false时仍可能返回true，RViz仍可能显示成功刷新并触发更新回调，而本地场景实际上部分应用。需将底层应用结果正确向上传递。

6. **Python绑定暴露bool但文档未解释成功语义。** pybind直接绑定C++方法并要求显式传入`service_name`，没有说明返回值含义、超时和PSM private executor同线程重入限制。Python调用者虽可检查bool，但同样继承底层“应用失败返回true”的问题；需要在绑定文档和示例中区分transport/response/apply结果。

7. **调用点的返回值处理不一致。** Servo common与print工具忽略返回值；RViz处理bool；OMPL工具检查bool并在false时退出；Python暴露bool给调用方。PSM private executor负责内部service client的响应处理，但同一private executor回调中同步调用会形成条件性阻塞。故不能将“调用方检查了bool”视为完整保护，必须同时修复API结果语义并明确禁止同executor线程同步重入。

8. **rclcpp异步客户端的executor前提由PSM private executor满足，但存在同线程重入阻塞边界。** rclcpp Client API明确说明async request返回future应由executor处理。PSM为其`pnode_`创建SingleThreadedExecutor并启动专用线程，因而常规外部线程调用同步请求时无需额外spin外部node。若从该private executor自身的回调中同步调用请求，则private executor线程被future wait占用，无法处理响应，可能超时；需要禁止这种调用上下文或改为异步/独立执行。

9. **超时后调用点缺少一致的状态门禁。** OMPL工具退出是相对保守的失败路径，但底层错误bool可能漏报应用失败；Servo secondary路径继续运行；print工具继续打印本地场景；RViz显示警告（但受错误true影响）。建议将“初始场景同步未成功或完整性未知”作为明确状态，不允许Servo在碰撞场景来源/完整性未确认时被误认为ready。此项是下游安全设计建议，不是声称当前MoveIt Servo已发生危险运动。

### 新增验证任务 SERVO-747 / C1–C12

- C1：服务端返回可解析但含无效world对象的消息，确认PSM bool、RViz UI状态、Servo secondary状态一致反映apply failure。
- C2：Servo primary配置true时确认不请求远端service，仅提供本地service；验证默认参数和示例配置。
- C3：Servo secondary配置false，service正常时验证PSM内部private executor完成初始场景同步与world/OctoMap完整性，并确认外部node executor状态不影响该内部client。
- C4：Servo secondary配置false，在外部node executor尚未spin时调用请求，确认PSM private executor仍可处理client response；验证private executor启动/关闭时序。
- C5：service不存在/超时/响应apply失败时，确认Servo secondary不以“场景同步成功”状态启动碰撞依赖路径；评估显式fail-closed门禁。
- C6：RViz后台请求分别注入transport失败、apply失败、完整成功，确认Warn/成功UI反馈无误。
- C7：运行`print_planning_scene_info`，对比PSM private executor正常运行、停止/关闭及请求从private executor回调重入三种模式的服务响应与输出。
- C8：运行OMPL `generate_state_database`，在`use_current_scene=true`下验证PSM private executor正常运行时的返回值、失败门禁、场景完整性和退出码。
- C9：Python binding验证返回值、异常、service_name解析、PSM private executor同线程重入限制与超时文档；补充可运行示例。
- C10：全仓库枚举`requestPlanningSceneState`调用点，要求每处显式记录返回值策略、调用线程是否可能属于PSM private executor、超时行为和scene readiness gate。
- C11：验证请求future超时/取消后client pending request资源生命周期及重复调用的资源增长；区分client局部析构与长期复用client。
- C12：在Stäubli/ICube真实启动拓扑中核对Servo primary/secondary参数、service provider、node executor/callback group、scene topic、碰撞检测开关及初始化门禁。

C1–C12全部未执行。未运行ROS构建、集成测试、executor调度测试、服务超时/失败注入、Servo碰撞场景回归、CS9/HIL、FAT/SAT或实机验证。

### 结论与证据边界

§9.3.164发现调用点存在不同程度的失败处理缺口：Servo secondary路径忽略请求失败并继续启动发布；RViz虽使用后台任务并检查bool，但底层bool可能错误报告apply failure为成功；OMPL工具检查bool并在false时退出；场景打印工具忽略bool；Python绑定暴露bool但没有说明执行契约。PSM创建独立pnode_、SingleThreadedExecutor和专用线程处理内部client，因此这些普通调用点不需要额外spin外部node executor；但从PSM private executor回调内同步重入请求仍有条件性阻塞风险。Servo参数默认primary=true，secondary风险不得泛化到默认配置。

本节为固定MoveIt 2源码静态审查及rclcpp API契约对照，不证明Stäubli/ICube现场使用上述具体工具、Servo secondary配置或同样executor拓扑，也不证明现场已发生碰撞漏检、危险运动或停机事件。所有C1–C12均未执行；未运行ROS构建、集成/并发/故障注入、CS9/HIL、FAT/SAT或实机验证。未修改MoveIt/ICube上游、未应用PR；工程级验收未通过，TODO-EXT-001未授权合并。

### 来源

- https://github.com/moveit/moveit2/blob/6ed6372a72ba9b121ed12ef574ea4ff4d3d92f09/moveit_ros/moveit_servo/src/utils/common.cpp
- https://github.com/moveit/moveit2/blob/6ed6372a72ba9b121ed12ef574ea4ff4d3d92f09/moveit_ros/moveit_servo/src/servo_node.cpp
- https://github.com/moveit/moveit2/blob/6ed6372a72ba9b121ed12ef574ea4ff4d3d92f09/moveit_ros/moveit_servo/config/servo_parameters.yaml
- https://github.com/moveit/moveit2/blob/6ed6372a72ba9b121ed12ef574ea4ff4d3d92f09/moveit_ros/visualization/planning_scene_rviz_plugin/src/planning_scene_display.cpp
- https://github.com/moveit/moveit2/blob/6ed6372a72ba9b121ed12ef574ea4ff4d3d92f09/moveit_planners/ompl/ompl_interface/scripts/generate_state_database.cpp
- https://github.com/moveit/moveit2/blob/6ed6372a72ba9b121ed12ef574ea4ff4d3d92f09/moveit_ros/planning/planning_components_tools/src/print_planning_scene_info.cpp
- https://github.com/moveit/moveit2/blob/6ed6372a72ba9b121ed12ef574ea4ff4d3d92f09/moveit_py/src/moveit/moveit_ros/planning_scene_monitor/planning_scene_monitor.cpp
- https://github.com/ros2/rclcpp/blob/rolling/rclcpp/include/rclcpp/client.hpp
- https://docs.ros.org/en/jazzy/p/rclcpp/generated/classrclcpp_1_1Client.html



## §9.3.165 MoveIt Servo碰撞监测启动门禁、场景新鲜度与命令发布路径（2026-11-09）

### 审查范围与固定基线

继续基于MoveIt 2固定提交 `6ed6372a72ba9b121ed12ef574ea4ff4d3d92f09`，将§9.3.164的GetPlanningScene调用方审查延伸到Servo运行时消费端，检查初始场景同步是否真正成为碰撞监测/运动命令的启动前置条件，以及场景失联、过期和碰撞线程首轮检查的行为。

审查文件及Blob SHA：
- `moveit_ros/moveit_servo/src/utils/common.cpp`：`7ce13c1805ba6bce2e58be10828034f35b60471a`
- `moveit_ros/moveit_servo/src/servo.cpp`：`0334445a7701935a80ba064fbb6f915f6c58dba3`
- `moveit_ros/moveit_servo/src/servo_node.cpp`：`eef6cc4073e03863a08eebbf69dc7cefedb15ebc`
- `moveit_ros/moveit_servo/src/collision_monitor.cpp`：`f1e8c8c9111a65903a62704fa80303cb9d320785`
- `moveit_ros/moveit_servo/include/moveit_servo/collision_monitor.hpp`：`91c1dfdb9a8168c372f5bfdc0aec4fcc135f6de8`
- `moveit_ros/moveit_servo/include/moveit_servo/servo.hpp`：`c4596711e5ea359b48fdfaf40f16dcadcc03150e`
- `moveit_ros/moveit_servo/config/servo_parameters.yaml`：`b16fc6bf0c31fea680529b797c9101827ac6024f`
- `moveit_ros/planning/planning_scene_monitor/src/planning_scene_monitor.cpp`：本轮复核固定提交中的`last_update_time_`写入点及`triggerSceneUpdateEvent()`
- `moveit_ros/planning/planning_scene_monitor/include/moveit/planning_scene_monitor/planning_scene_monitor.hpp`：`getLastUpdateTime()`契约明确为“by any monitor”的最近场景更新时刻。

### 静态发现

1. **Servo启动等待的不是“远端场景已同步”，而是PSM出现任意一次更新。** `ServoNode::servoLoop()`记录启动时间后，循环等待`planning_scene_monitor_->getLastUpdateTime()`不早于启动时间。PSM头文件将该时间定义为“by any monitor”的最后更新时间；源码中CurrentStateMonitor更新会写入`last_update_time_`并触发`UPDATE_STATE`。因此，单纯收到机器人关节状态就可能满足Servo启动等待条件；该门禁不能证明CollisionObject/PlanningSceneWorld/OctoMap已到达，也不能证明§9.3.164中secondary PSM的GetPlanningScene请求成功或完整应用。

2. **secondary PSM同步失败后仍可能进入正常Servo循环。** §9.3.164已确认`createPlanningSceneMonitor()`在secondary配置下调用`requestPlanningSceneState()`但忽略bool结果。随后无条件启动PlanningScene发布器并返回PSM。Servo构造只等待完整机器人状态，之后创建并启动CollisionMonitor；ServoNode再创建命令订阅、输出发布器和servo loop线程。结合第1点，若远端场景服务不可用/超时、而本地joint state持续更新，源码没有要求等待有效world scene，Servo仍可能进入命令处理路径。该结论是静态控制流推导；是否形成现场风险取决于Stäubli/ICube实际primary/secondary配置、场景topic及上层运动使能互锁。

3. **碰撞监测没有场景有效性/新鲜度门禁。** `CollisionMonitor::checkCollisions()`循环获取`LockedPlanningSceneRO`，直接从当前PlanningScene读取robot state、CollisionEnv和AllowedCollisionMatrix并计算环境碰撞/自碰撞距离。该循环没有读取PSM的`getLastUpdateTime()`、场景来源时间戳、world几何更新时间、同步generation或“场景尚未初始化/已过期”标志；没有在场景长时间未更新时将`collision_velocity_scale_`置零或发布独立故障状态。因此场景为空、部分应用、仅有旧world或外部场景发布端停止更新时，碰撞线程仍会对当前可读场景执行计算；它不会仅凭场景陈旧自动进入fail-closed。静态代码不证明现场一定存在陈旧场景，也不意味着静态环境必须周期性发布；需要按场景来源定义新鲜度和失联策略。

4. **碰撞线程首轮检查与首条命令之间没有完成握手。** `Servo::Servo()`在等待完整joint state后创建CollisionMonitor并调用`start()`，该方法只启动独立线程并立即返回。共享的`collision_velocity_scale_`在`servo.hpp`中初始化为`1.0`；CollisionMonitor线程在首次完成碰撞检查前没有将其置为“未知/禁止运动”，也没有ready事件供ServoNode等待。ServoNode启动loop后可处理输入命令；`getNextJointState()`读取该原子缩放值，值为1.0时不产生collision halt/decelerate状态。由此存在“首轮碰撞检查尚未完成，命令路径已可使用初始全速缩放值”的启动竞态窗口。是否能在目标机器上观测到取决于线程调度和首次场景锁/碰撞计算耗时，尚未动态复现。

5. **场景更新停滞时，旧碰撞结果可持续被使用。** CollisionMonitor按`collision_check_rate`周期运行；配置默认10 Hz。循环每次重新读取当前PlanningScene，但没有设置最大场景年龄或连续未更新计数。若外部发布端停止发送world geometry更新而本地保留旧场景，监测线程会继续基于旧几何计算距离；这与“碰撞检查线程仍在运行”不同于“场景数据仍然新鲜”。对静态工作单元，产品可以定义静态场景无需周期刷新，但至少应定义启动完整性、动态障碍源超时、地图版本/时间戳和恢复门禁。

6. **默认OctoMap采集配置与碰撞检测总开关是两个不同参数。** `check_collisions`默认true，控制Servo是否执行碰撞检测；`check_octomap_collisions`默认false，并作为`startWorldGeometryMonitor()`的`load_octomap_monitor`参数。故默认配置仍会进行PlanningScene中的环境碰撞与自碰撞检查，但不会通过该调用默认启用OccupancyMapMonitor的传感器OctoMap更新路径。不能把“默认OctoMap monitor关闭”表述为“默认碰撞检查关闭”，也不能假设现场点云/深度图OctoMap一定参与Servo环境碰撞检查。外部PlanningScene消息是否携带地图及目标配置需现场核实。

7. **暂停/恢复会重启碰撞线程，但不验证场景状态。** `pauseServo()`暂停时调用`setCollisionChecking(false)`，恢复时刷新机器人状态、清空轨迹窗口并调用`setCollisionChecking(true)`。CollisionMonitor的`start()`仅重置stop标志并启动线程；没有在恢复前请求全量场景、验证world更新或等待首轮collision check完成。因而恢复流程修复了机器人状态/平滑器基准，但没有补足场景同步/新鲜度握手。此结论仅描述软件状态机，不等同于pause服务可绕过所有外部安全控制。

8. **碰撞结果只影响速度缩放，不能替代安全认证或安全PLC。** 碰撞距离检查由普通Servo软件线程执行，碰撞结果通过atomic缩放值影响下一个关节命令；源码未将该路径定义为安全额定停止功能。必须与Stäubli控制器安全功能、外部安全扫描器、保护停止和风险评估分开审查，不能把MoveIt Servo collision monitor作为CS9/机器人安全等级的替代证据。

### 新增验证任务 SERVO-748 / D1–D14

- D1：secondary PSM请求GetPlanningScene服务失败，但持续注入joint_states；确认`getLastUpdateTime()`被state update推进且Servo loop是否继续启动。
- D2：secondary PSM收到transport成功但PlanningScene apply失败的响应；跟踪请求bool、场景对象清单、Servo构造和命令发布状态。
- D3：只发布joint_states、不发布CollisionObject/PlanningSceneWorld，验证Servo启动门禁是否错误地将state update视为world scene就绪。
- D4：在CollisionMonitor启动处加入barrier，阻止首次collision check完成，同时输入可导致非零运动的命令；记录初始`collision_velocity_scale_`、status及是否发布首条命令。
- D5：使用已知碰撞场景，测量CollisionMonitor首轮检查完成前后速度缩放和HALT状态的切换时序。
- D6：停止scene/world publisher但持续发送joint_states，记录场景年龄、collision check线程状态、输出命令及是否存在超时/失联状态。
- D7：动态障碍物消息中断、恢复、乱序及旧消息重放，验证场景新鲜度门禁和恢复策略。
- D8：注入部分full scene应用失败，确认CollisionMonitor是否对部分场景继续计算，Servo是否仍可输出命令。
- D9：分别测试`check_collisions=true/false`与`check_octomap_collisions=true/false`四种配置组合，区分自碰撞、普通world geometry和OctoMap输入路径。
- D10：暂停Servo、停止场景源、恢复Servo，验证恢复前是否重新校验场景完整性及等待首轮碰撞检查。
- D11：验证`collision_check_rate`低频/高负载/scene lock竞争时首次检查延迟与命令发布的相对时序。
- D12：定义并验证静态场景、动态障碍场景和OctoMap场景各自的新鲜度/失联策略；对超时采取明确的禁止运动/外部互锁策略。
- D13：核对Servo status topic是否能区分“碰撞安全检查未就绪/场景过期/同步失败”，并验证上层控制器是否消费该状态。
- D14：获取Stäubli/ICube真实Servo primary配置、scene topic、world geometry来源、OctoMap配置、命令输出控制器、pause/unpause调用链和安全PLC互锁证据。

D1–D14全部未执行。未运行ROS构建、动态场景测试、barrier线程测试、ASan/TSan、压力测试、CS9/HIL、FAT/SAT或实机验证。

### 结论与证据边界

§9.3.165将§9.3.164发现的GetPlanningScene同步失败路径追踪到Servo实际运动命令和CollisionMonitor消费端。固定源码显示：Servo loop的初始等待由PSM任意monitor更新满足，关节状态更新即可推进该时间；CollisionMonitor没有场景有效性/新鲜度检查；碰撞线程启动后没有首轮检查ready握手，而共享缩放值初始为1.0；暂停恢复也没有重新验证场景。默认`check_collisions=true`与`check_octomap_collisions=false`必须分开解释。

这些发现表明存在需要验证的fail-open/启动时序风险，不证明Stäubli现场使用secondary配置、已发生碰撞漏检或危险运动。现场配置、场景发布拓扑、控制器互锁及安全PLC证据仍缺。未运行动态测试、CS9/HIL、FAT/SAT或实机验证；未修改MoveIt/ICube上游，未应用PR；Stäubli工程级验收未通过，TODO-EXT-001未授权合并。

### 来源

- https://github.com/moveit/moveit2/blob/6ed6372a72ba9b121ed12ef574ea4ff4d3d92f09/moveit_ros/moveit_servo/src/utils/common.cpp
- https://github.com/moveit/moveit2/blob/6ed6372a72ba9b121ed12ef574ea4ff4d3d92f09/moveit_ros/moveit_servo/src/servo.cpp
- https://github.com/moveit/moveit2/blob/6ed6372a72ba9b121ed12ef574ea4ff4d3d92f09/moveit_ros/moveit_servo/src/servo_node.cpp
- https://github.com/moveit/moveit2/blob/6ed6372a72ba9b121ed12ef574ea4ff4d3d92f09/moveit_ros/moveit_servo/src/collision_monitor.cpp
- https://github.com/moveit/moveit2/blob/6ed6372a72ba9b121ed12ef574ea4ff4d3d92f09/moveit_ros/moveit_servo/include/moveit_servo/servo.hpp
- https://github.com/moveit/moveit2/blob/6ed6372a72ba9b121ed12ef574ea4ff4d3d92f09/moveit_ros/moveit_servo/config/servo_parameters.yaml
- https://github.com/moveit/moveit2/blob/6ed6372a72ba9b121ed12ef574ea4ff4d3d92f09/moveit_ros/planning/planning_scene_monitor/src/planning_scene_monitor.cpp
- https://github.com/moveit/moveit2/blob/6ed6372a72ba9b121ed12ef574ea4ff4d3d92f09/moveit_ros/planning/planning_scene_monitor/include/moveit/planning_scene_monitor/planning_scene_monitor.hpp



## §9.3.166 Servo停止状态、命令发布语义与下游控制器接收边界（2026-11-09）

### 审查范围与固定基线

沿§9.3.165继续追踪Servo从碰撞检测状态码到命令topic发布，再到典型ros2_control JointTrajectoryController接收端的行为。MoveIt固定基线仍为`6ed6372a72ba9b121ed12ef574ea4ff4d3d92f09`。另选取ros-controls/ros2_controllers提交`c8d26930ff87bc819db1452af1d45da5bfa3d50d`作为控制器行为对照样本；该提交不是已确认的Stäubli/ICube部署版本，不能替代现场依赖版本核对。

MoveIt源码Blob SHA：
- `servo_node.cpp`：`eef6cc4073e03863a08eebbf69dc7cefedb15ebc`
- `servo.cpp`：`0334445a7701935a80ba064fbb6f915f6c58dba3`
- `utils/common.cpp`：`7ce13c1805ba6bce2e58be10828034f35b60471a`
- `utils/datatypes.hpp`：`57c0f111b3776c69a838b8ff30190226d54108f2`
- `servo_parameters.yaml`：`b16fc6bf0c31fea680529b797c9101827ac6024f`

对照控制器源码Blob SHA：
- `joint_trajectory_controller.cpp`：`73ab7eec845fdb75c725b95740ae7f9166aca9e4`
- `joint_trajectory_controller.hpp`：`7c8545a1d1f9274c57a8d3b46eacad763e232a4b`

### 静态发现

1. **HALT_FOR_COLLISION抑制本周期命令发布，但不显式发送停止命令。** `Servo::getNextJointState()`在collision_velocity_scale_为0时将状态设为`HALT_FOR_COLLISION`，跳过正常目标位置/速度计算并返回目标状态。随后`ServoNode::servoLoop()`只有在next_joint_state存在且状态既不是INVALID也不是HALT_FOR_COLLISION时才发布JointTrajectory或Float64MultiArray。碰撞HALT分支进入else，只重新读取当前机器人状态、更新本地rolling window并重置smoothing；没有发布零速度消息、hold-position轨迹、cancel请求或控制器停止服务。因此`ServoStatus=HALT_FOR_COLLISION`是Servo内部检测/状态上报，不是下游控制器已执行停止的确认。

2. **Servo status topic与command topic没有事务绑定或执行确认。** Servo每个未暂停循环周期发布状态码和文本，但状态消息不包含对应命令序号、已发布命令序号、控制器接收确认或实际执行反馈关联。publisher的`publish()`调用也没有在本路径中检查控制器是否active、是否匹配订阅、是否接受轨迹或是否已经写入硬件command interface。因而状态消费者不能仅凭收到HALT状态推断控制器已经停止；命令消费者也不能仅凭收到命令推断Servo碰撞状态仍然有效。

3. **Trajectory模式HALT留下最后一条已发布轨迹的下游处理问题。** Servo正常轨迹输出使用`updateSlidingWindow()`生成未来时间窗，并由`composeTrajectoryMessage()`将窗口中除末尾点外的点组成消息；`max_expected_latency`默认配置为0.1秒。HALT时Servo不再发布新轨迹，但没有主动替换或取消控制器中的旧轨迹。下游控制器如何处理旧轨迹、轨迹时间戳和无新消息，取决于实际控制器实现、配置和驱动层，不能由Servo状态码代替验证。

4. **典型JointTrajectoryController对照实现显示，topic无新消息不等于立刻停止当前轨迹。** 在ros-controls/ros2_controllers固定对照提交`c8d26930ff87bc819db1452af1d45da5bfa3d50d`中，`topic_callback()`收到并验证新轨迹后才调用`add_new_trajectory_msg()`替换当前轨迹；周期性`update()`在`has_active_trajectory()`时持续采样当前轨迹并生成下一控制周期命令。没有新topic消息时，当前活动轨迹不会仅因topic沉默而在该回调中自动取消。其`cmd_timeout_`处理发生在轨迹末点之后且依赖参数配置，不是通用的“Servo停止消息丢失即立即停机”机制。该样本只证明此对照版本的行为，不证明Stäubli现场使用同版本或同参数。

5. **Float64MultiArray输出路径同样没有显式停止/接收确认。** Servo在`std_msgs/Float64MultiArray`模式发布由配置的关节位置或速度字段组成的数组。该消息不携带JointTrajectory的header时间戳和轨迹时间窗；接收端的超时、零速、hold、失联检测和驱动使能语义完全依赖具体下游节点/控制器。不能将Trajectory模式的行为假设套用于MultiArray，也不能假设topic停止发布就代表硬件停止。

6. **输入命令超时与碰撞HALT是不同的停止路径。** JointJog/Twist/Pose处理函数在输入命令过期后调用`smoothHalt()`，在平滑停止尚未完成时可返回停止轨迹/状态供正常输出分支发布；而碰撞HALT被servoLoop明确排除在命令发布条件之外。不得将`incoming_command_timeout`默认0.1秒的平滑停止机制误认为碰撞HALT已经发送了相同的停止轨迹。输入命令时间戳新鲜度、碰撞缩放和控制器命令超时是三个独立门禁。

7. **暂停分支绕过本周期status与command发布。** `servoLoop()`检测到`servo_paused_`后重置平滑器、sleep并continue，跳过本周期状态消息发布及命令处理。pause服务返回成功只说明Servo内部暂停状态已切换，不构成控制器/驱动层停止确认；暂停前已被控制器接收的轨迹如何收尾仍依赖下游行为。该问题与§9.3.165的恢复场景校验缺口相关，但本节聚焦命令出口语义。

8. **Servo status中的“emergency stop”文字不能作为安全功能证据。** `HALT_FOR_COLLISION`映射文本为“Collision detected, emergency stop”，但对应实现是普通ROS循环中抑制命令发布并发布状态消息；未见该分支直接调用Stäubli控制器安全停止、保护停止、安全PLC或安全额定停止接口。这里的文案不能解释为已触发安全等级的Emergency Stop。安全停止必须由独立、经风险评估和验证的安全链完成。

### 新增验证任务 SERVO-749 / E1–E15

- E1：在Trajectory输出模式注入碰撞HALT，记录最后一条已发布轨迹的header.stamp、point时间窗、Servo状态、控制器desired state与硬件command interface。
- E2：证明HALT_FOR_COLLISION期间Servo是否发送任何零速、hold-position、空轨迹或cancel消息；预期当前固定源码路径不发布新command，测试记录不得伪造为已执行。
- E3：在碰撞HALT时保持JTC活动轨迹，验证无新Servo轨迹时控制器是否继续采样/执行旧轨迹以及持续时间。
- E4：对实际ICube控制器版本核对topic callback、轨迹替换、活动轨迹结束、cmd_timeout、hold/decelerate和生命周期停用语义。
- E5：分别在Trajectory与Float64MultiArray输出模式执行碰撞HALT，比较接收端停止行为、命令缓存和硬件接口变化。
- E6：断开/暂停Servo publisher或停止Servo进程，验证控制器对topic沉默、DDS断连和publisher销毁的反应；区分命令超时与控制器生命周期停止。
- E7：模拟控制器inactive、订阅端不存在、QoS不兼容、消息丢弃及接收回调延迟，确认Servo是否有可观测的拒收/未送达反馈。
- E8：将ServoStatus与command消息按序号/时间戳关联，验证HALT状态、最后发布命令和控制器接收时刻是否可追溯；评估是否需要单独ack/watchdog接口。
- E9：验证HALT_FOR_COLLISION之后碰撞解除、命令仍持续输入时的恢复行为，确认是否必须经过人工/上层重新使能，而非自动恢复输出。
- E10：pause/unpause期间保持下游旧轨迹活动，验证pause服务是否仅改变Servo内部状态以及下游轨迹何时终止。
- E11：输入命令超时路径与碰撞HALT路径分别测试，验证smoothHalt会发布停止轨迹而碰撞HALT不走同一发布分支。
- E12：检查Servo status消费者、任务调度器和机器人应用是否把HALT_FOR_COLLISION误解释为硬件已停；验证状态丢失/延迟时的安全行为。
- E13：对Trajectory窗口边界、最后一点时间戳、控制器update周期和网络/DDS延迟做故障注入，测量停止响应上界。
- E14：验证Stäubli控制器/安全PLC独立保护停止、驱动使能撤销和安全扫描器触发链；明确Servo topic命令不承担安全功能。
- E15：获取现场ICube/ros2_control版本、控制器类型与参数、command interface映射、QoS、topic remap、驱动失联策略和FAT/SAT证据。

E1–E15全部未执行。对照JTC提交不是现场部署证据；现场控制器类型/版本/配置仍未确认。未运行ROS构建、仿真/动态控制器测试、DDS断链测试、CS9/HIL、FAT/SAT或实机验证。

### 结论与证据边界

§9.3.166确认：MoveIt Servo的碰撞HALT状态不等价于下游控制器收到并执行停止命令。固定Servo源码在HALT_FOR_COLLISION分支抑制正常command publish，发布状态消息，但不显式发布零速/hold/取消轨迹命令；典型JTC对照版本在没有新topic消息时仍持续采样活动轨迹。MultiArray模式的停止语义更依赖未知接收端。pause分支也会跳过状态与命令发布。

这构成“软件内部停止状态”与“执行器停止结果”之间的验证缺口，不足以证明Stäubli现场实际发生危险运动，也不证明现场采用上述JTC对照版本。必须取得ICube部署源码/版本、控制器配置、驱动行为和安全PLC证据，并通过故障注入及HIL/FAT/SAT验证停止响应。不得将Servo status文案中的“emergency stop”解释为安全认证急停。未修改MoveIt/ICube上游，未应用PR；Stäubli工程级验收未通过，TODO-EXT-001未授权合并。

### 来源

- https://github.com/moveit/moveit2/blob/6ed6372a72ba9b121ed12ef574ea4ff4d3d92f09/moveit_ros/moveit_servo/src/servo_node.cpp
- https://github.com/moveit/moveit2/blob/6ed6372a72ba9b121ed12ef574ea4ff4d3d92f09/moveit_ros/moveit_servo/src/servo.cpp
- https://github.com/moveit/moveit2/blob/6ed6372a72ba9b121ed12ef574ea4ff4d3d92f09/moveit_ros/moveit_servo/src/utils/common.cpp
- https://github.com/moveit/moveit2/blob/6ed6372a72ba9b121ed12ef574ea4ff4d3d92f09/moveit_ros/moveit_servo/include/moveit_servo/utils/datatypes.hpp
- https://github.com/moveit/moveit2/blob/6ed6372a72ba9b121ed12ef574ea4ff4d3d92f09/moveit_ros/moveit_servo/config/servo_parameters.yaml
- https://github.com/ros-controls/ros2_controllers/blob/c8d26930ff87bc819db1452af1d45da5bfa3d50d/joint_trajectory_controller/src/joint_trajectory_controller.cpp
- https://github.com/ros-controls/ros2_controllers/blob/c8d26930ff87bc819db1452af1d45da5bfa3d50d/joint_trajectory_controller/include/joint_trajectory_controller/joint_trajectory_controller.hpp


### §9.3.167 Servo topic静默、ros2_control写循环与Stäubli VAL3通信看门狗的跨层关系

#### 1. 审查范围与固定证据

本节沿§9.3.166继续追踪“Servo命令不再发布”之后，JointTrajectoryController（JTC）、controller_manager、硬件接口、UDP传输和CS9侧VAL3控制任务是否仍会产生/接收命令。源码证据分为三组：

- MoveIt 2固定提交：6ed6372a72ba9b121ed12ef574ea4ff4d3d92f09。
- JTC行为对照：ros-controls/ros2_controllers提交c8d26930ff87bc819db1452af1d45da5bfa3d50d。仅作为典型JTC实现，不视为ICube现场软件版本。
- ICube公开参考实现：ICube-Robotics/staubli_driver_ros2提交bd658e2d266e315d2ee35f985fb352ea88306b79。该仓库README称其基于ROS 2 Jazzy、面向CS9、仅支持位置控制，并明确标注为开发中的prototype；开发曾在2025年11月初始POC后暂停。该公开仓库和VAL3源文件不是某台Stäubli现场设备的部署证明。

ICube仓库的VAL3工程文件ros2_server.pjx记录工程目标版本字符串S8.20.2Cs9_BS4270。这只是仓库内工程元数据，不代表现场控制器固件/应用版本。

#### 2. JTC topic沉默后仍可能继续向硬件接口提供命令

在固定JTC对照提交中，topic callback收到并验证新JointTrajectory后才替换当前轨迹；周期update()读取current_trajectory_，在has_active_trajectory()时继续按traj_time_采样，并将command_next_写入position/velocity等command interface。未收到新topic消息本身不会清除current_trajectory_。

轨迹末点处理也不是简单地“没有新topic就停止”。JTC会根据cmd_timeout、goal tolerance和should_decelerate_on_cancel_等配置处理轨迹结束；可能生成hold-position或decelerate-to-hold轨迹。若控制器保持active，即使不再收到Servo新轨迹，控制循环仍可能继续产生保持/末点命令。cmd_timeout为配置项，不能假设所有部署都启用或具有同一值。

因此，Servo HALT_FOR_COLLISION停止发布新轨迹，不等于JTC立即停止update，也不等于其command interface立即清零或释放。是否仍在持续写入以及最终写入何值，取决于当前轨迹、goal/topic路径、JTC参数和控制器生命周期。

#### 3. ros2_control控制循环与硬件写出

对照ros2_control controller_manager源码中，read阶段从硬件读取状态，update阶段调用active controller，write阶段将command interface中的值写入硬件。硬件write返回ERROR时，controller_manager会查找使用该硬件接口的控制器并执行停用流程；read错误也会停用关联控制器。这里的源码对照提交为ros-controls/ros2_control@33c6d025530b53acacdcab8927f359e4f311e260，不作为现场Jazzy安装版本或现场参数证据。

这意味着，只有控制器确实被停用、硬件写循环停止，或硬件驱动主动改变输出/停止发送时，机器人侧才可能观察到报文流变化。单独停止Servo publisher并不必然停止controller_manager的硬件write周期。

#### 4. ICube公开Staubli硬件接口的命令生命周期

在ICube仓库固定提交bd658e2d266e315d2ee35f985fb352ea88306b79中，StaubliHardwareInterface::write()：

- 检查RobotDriver及连接状态；
- 若当前模式不是STOP，检查机器人error_state及INVALID状态；
- 将当前控制模式、controller period和最近有效机器人状态序号写入RobotCommandMessage；
- 对JOINT_POSITION模式，将ros2_control位置命令从弧度转换为Staubli使用的角度制；
- 调用RobotDriver::send_robot_command()发送控制报文；
- 发送失败、NaN命令或机器人错误状态会返回hardware_interface::return_type::ERROR；部分错误分支会先尝试send_stop_all_command()。

该write()并不以“是否刚收到新的Servo topic消息”为发送条件。只要controller_manager仍调用硬件write，驱动就会使用当前command interface值组装并发送命令。JTC保持末点/hold命令时，驱动可能继续向VAL3发送周期性位置报文。

RobotCommandMessage.header.sequence_number使用RobotDriver最近一次有效RobotState序号；controller_period由本次write周期计算。RobotDriver::send_robot_command()返回值来自控制接口send_message()成功与否。当前公开实现没有为每条命令暴露一个与机器人运动执行结果绑定的独立ACK；本地UDP发送成功不能证明VAL3已接收、接受或执行该条命令。VAL3返回的state sequence及sequence_delay可用于观察通信滞后，但不等于逐命令执行确认。

#### 5. VAL3侧命令失联看门狗与STOP路径

同一公开仓库的VAL3 controlTask每个控制循环更新RobotState序号，尝试读取最新RobotCommand，并通过computeSequenceDelay()计算“当前已发送状态序号 - 最近命令携带的状态序号”。在机器人运动时，sequence delay大于5个周期会将命令模式切到STOP；机器人静止时阈值为大于25个周期。仓库troubleshooting文档把运动中大于5周期解释为约20 ms（250 Hz）。

STOP路径会在前一模式为joint-position时调用stopJointPositionControl()；该过程检查movejSync状态并调用movejSyncEnd()，随后controlTask调用stopMove()和resetMotion()。这属于VAL3运动控制程序的普通停止路径，不能据此认定为安全额定急停、保护停止或安全PLC功能。

controlTask还明确留下若干TODO，包括无新命令时的staleness处理和丢包处理；但现有sequence delay阈值仍会在命令序号落后时触发STOP。阈值实际时间受真实任务周期、任务overrun和调度影响，不能只用名义250 Hz推导已验证的停止上界。

#### 6. 本节关键跨层结论

1. **Servo topic静默不必然触发CS9侧命令看门狗。** 若JTC仍active并持续采样活动轨迹/保持末点，controller_manager仍运行硬件write，ICube硬件接口继续发出带有近期RobotState序号的UDP命令，则VAL3看到的可能是连续命令流，而不是失联。此时机器人侧sequence-delay watchdog不会仅因Servo publisher静默而必然触发。
2. **控制器停用与硬件报文停止是不同事件。** controller_manager的read/write错误路径可停用关联控制器，但实际调用顺序、硬件接口模式切换、write阶段是否还执行一次、以及ICube驱动STOP命令是否成功送达，必须按目标ROS发行版和现场配置做集成验证。
3. **ICube驱动有主动STOP尝试，但不是无条件保证。** on_error()在RobotDriver仍is_connected()时尝试send_stop_all_command()；若连接/接口不可用则返回错误。on_shutdown()在状态非STOP时尝试发送STOP再断开。on_cleanup()只断开连接，没有显式先发STOP。析构函数也只调用disconnect。生命周期路径是否能在目标部署中可靠触发及其时序，需动态验证。
4. **状态新鲜度与连接状态不同。** RobotDriver默认state_staleness_timeout为100 ms；read_robot_state()对过期状态返回false，但is_connected()主要检查socket和通信接口ready，不等价于状态新鲜。read()会因状态读取失败返回ERROR。on_error发送STOP时仍需核实底层当前状态、UDP接口和目标端是否可用。
5. **序号滞后是流级健康度，不是逐命令ACK。** sequence_delay可以发现命令流落后，但当前证据没有证明每条位置命令均被机器人接受、执行或达到对应目标。还需检查重复、乱序、序号回绕、缓冲和VAL3任务过载。
6. **STOP不是安全功能证明。** movejSyncEnd()/stopMove()/resetMotion()的停止距离、减速度、延迟、制动器行为及安全等级未由本源码证明；必须独立核对CS9安全配置、安全PLC、E-stop/保护停止及驱动使能撤销链。

#### 7. 新增验证任务 SERVO-750 / F1–F16

- F1：固定目标JTC版本，分别在topic停止前、活动轨迹中、轨迹末点、goal成功/超时后记录active trajectory、desired state及command interface值。
- F2：验证Servo HALT_FOR_COLLISION后JTC是否继续update、何时生成hold/decelerate轨迹、command interface是否持续更新。
- F3：在controller_manager真实控制周期中跟踪read→update→write顺序、控制器停用时序及硬件write最后一次调用。
- F4：将JTC command interface与ICube硬件write输出逐周期关联，记录UDP发送频率、RobotCommand序号、命令模式和参考值。
- F5：分别执行Servo publisher静默、JTC主动停用、controller_manager停止、硬件接口停用，比较VAL3 sequence_delay和机器人停止行为。
- F6：在ICube硬件接口中注入RobotState超过默认100 ms的staleness，确认read() ERROR、controller_manager停用、on_error回调和STOP命令的实际调用顺序。
- F7：注入UDP发送失败、socket断连和接口not-ready，验证write() ERROR、STOP尝试失败及VAL3失联看门狗是否接管。
- F8：分别在RobotDriver仍connected但state stale、control interface not-ready、socket断连三种情况下验证on_error()和send_stop_all_command()结果。
- F9：核实on_cleanup、on_shutdown、硬件deactivate、controller deactivate及进程崩溃路径；测量是否先发送STOP、是否只断开连接及机器人端最终状态。
- F10：在CS9/VAL3上测量运动中sequence delay阈值>5、静止阈值>25的实际周期、任务overrun和触发时间分布。
- F11：对UDP报文进行丢包、重复、乱序、延迟、序号回绕和突发背压注入，确认sequence_delay与命令有效性策略。
- F12：验证movejSyncEnd、stopMove、resetMotion的实际停止距离、减速度、响应时间、制动器/驱动状态及不同机器人负载工况。
- F13：核对position/velocity/effort/acceleration接口组合和控制模式切换；确认该公开驱动只支持position的限制与现场驱动差异。
- F14：取得现场staubli_driver_ros2 commit、ROS发行版、ros2_control/ros2_controllers版本、VAL3应用版本、CS9固件、网络参数和URDF控制器配置。
- F15：验证CS9安全PLC、E-stop、保护停止、门禁/扫描器、制动器和驱动使能撤销链，确认其独立于ROS topic/UDP普通命令。
- F16：在隔离测试单元完成Servo碰撞HALT→JTC→controller_manager→硬件write→UDP→VAL3全链路故障注入及HIL/FAT/SAT记录。

F1–F13、F16均未执行；F14–F15未确认，现场证据缺失。以上均为验证任务，不得记为已测试。

#### 8. 证据边界与验收状态

本节新增了ICube公开原型源码作为比通用JTC更贴近Stäubli的参考实现，但README明确其为prototype且项目开发曾暂停。没有证据证明任何具体Stäubli现场部署了该仓库、该提交、该VAL3工程或该controller_manager/JTC组合。公开源代码的静态行为不能替代现场软件物料清单、CS9工程文件、控制器配置和HIL/FAT/SAT。

本轮未运行ROS构建、JTC动态测试、UDP网络故障注入、VAL3编译/仿真、CS9/HIL、FAT/SAT或实机验证；未证明任何现场故障或危险运动。未修改MoveIt、ros2_control、ros2_controllers或ICube上游，未应用PR。Stäubli工程级验收未通过，TODO-EXT-001未授权合并。

#### 来源与固定Blob

- MoveIt Servo： https://github.com/moveit/moveit2/blob/6ed6372a72ba9b121ed12ef574ea4ff4d3d92f09/moveit_ros/moveit_servo/src/servo_node.cpp
- JTC： https://github.com/ros-controls/ros2_controllers/blob/c8d26930ff87bc819db1452af1d45da5bfa3d50d/joint_trajectory_controller/src/joint_trajectory_controller.cpp （Blob SHA 73ab7eec845fdb75c725b95740ae7f9166aca9e4）
- controller_manager： https://github.com/ros-controls/ros2_control/blob/33c6d025530b53acacdcab8927f359e4f311e260/controller_manager/src/controller_manager.cpp （Blob SHA 7094d01b8a6813ec43ef0ff558fec1bdf8102b1b）
- ICube README： https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/README.md （Blob SHA ce1dd2263e32724b7d3c4e7d66fc0b7ead9762c8）
- ICube hardware interface： https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/src/staubli_hardware_interface.cpp （Blob SHA 4ae2b8c8d91857e5e32558bfcd16e2c391b9c3d0）
- ICube RobotDriver： https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/src/robot_driver.cpp （Blob SHA ede48a314856a455df9d8434f354aaf9fbc47bff）
- ICube RobotDriver header： https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/include/staubli_robot_driver/robot_driver.hpp （Blob SHA 62c87a6741aa082db4599bb2c048aec0fcd7a464）
- VAL3 controlTask： https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/val3/userapp/ros2_server/controlTask.pgx （Blob SHA 00a69c4d13879116fce744ceb1611ecd05d65edf）
- VAL3 stopJointPositionControl： https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/val3/userapp/ros2_server/Control/stopJointPositionControl.pgx （Blob SHA bd4be41dff93258d5c08cbf9411af3d811b5f6c9）
- VAL3 updateJointPositionControl： https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/val3/userapp/ros2_server/Control/updateJointPositionControl.pgx （Blob SHA 28e2f1d6a3482a126b16474c957a608262c32218）
- VAL3 computeSequenceDelay： https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/val3/userapp/ros2_server/Comm/computeSequenceDelay.pgx （Blob SHA e96e5b378bc263255ee4f28720306ee911b8a5c1）
- ICube troubleshooting： https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_driver_ros2/sphinx/demo_applications/troubleshooting.rst （Blob SHA fffd7d2b1fcb9cd95621f6e94191ff6cff49ba91）


### §9.3.168 ICube UDP报文接收新鲜度、序号单调性与发送丢包语义

#### 1. 固定基线与范围

本节固定审查ICube-Robotics/staubli_driver_ros2提交bd658e2d266e315d2ee35f985fb352ea88306b79，重点覆盖RealTimeSocketSubscriber、RobotDriver::read_robot_state()、UDPSocketImpl::send()、UDP接收线程及VAL3 16位序号算法。该仓库README明确其为Jazzy/CS9开发原型，不是现场部署证明。

#### 2. 接收缓冲区与新鲜度判断存在语义错位

RealTimeSocketSubscriber::update_message()每收到一条可反序列化报文，就在接收线程中将本机接收时间写入reception_timestamp，再将消息放入RealtimeThreadSafeBox。该box只提供最新消息快照，不保留可供读取端逐条消费的完整队列。

read_message()读取最新快照并计算time_since_received。如果本次读取的序号与上次相同，会将status.new_message=false；但仍返回true，并保留该报文最近一次到达本机的时间戳。

RobotDriver::read_robot_state()检查接口ready、读取函数返回值、消息类型及时间戳新鲜度，但没有检查status.new_message。因此：
- 同一序号的重复报文只要持续到达，reception_timestamp就会不断刷新；
- read_message()虽识别出重复序号并标记new_message=false，上层仍会把该状态作为有效状态返回；
- 这可能使ros2_control继续使用未推进的关节状态样本，而时间戳年龄仍小于默认100 ms；
- 机器人端VAL3命令序号看门狗可能最终发现命令携带的状态序号未推进，但不能替代ROS侧对状态新鲜度的正确判断。

这不是证明现场一定出现重复报文或危险运动，而是固定源码中“接收时间新鲜”与“状态样本前进”没有绑定的逻辑缺口。

#### 3. 16位序号下降被无条件解释为回绕

FrameHeader.sequence_number为uint16_t，最大值65535。RealTimeSocketSubscriber::read_message()在新序号大于上次序号时计算普通差值；相等时标记重复；只要新序号小于上次序号，就按65535→0回绕公式计算丢包数。

该逻辑没有使用模数序号的半区间判定，也没有拒绝小幅倒退的旧报文。例如上次读到100、随后收到99，会被当作回绕并计算出65535个丢包，随后还会把last_read_sequence_number_更新为99。后续101又会按99为基准计算。因而乱序旧包可能污染序号基准并造成虚假的巨大丢包计数。

真正的65535→0回绕在该算法下可以得到0丢包，但这并不能证明其他下降均为合法回绕。需要用边界测试区分回绕、乱序、重复、重启后序号复位及长时间断连后的重新同步。

#### 4. 状态丢包统计没有形成可观测的故障门禁

read_robot_state()对status.lost_packages的告警代码被注释掉，且当前返回成功条件不要求丢包数为0，也不要求序号连续或单调。读取端仅把最新状态复制给调用方，并更新last_valid_sequence_id_。

该实现倾向于“最新样本优先”，可以容忍中间状态样本丢失；但丢包统计没有转化为可查询的诊断量、阈值策略或控制器降级门禁。需要明确允许丢包的窗口、连续丢包阈值、状态样本最大年龄和重新同步规则，不能仅凭read成功推断反馈链健康。

#### 5. UDP发送would_block时上层仍可能收到成功

固定源码UDPSocketImpl::send()在boost::asio::error::would_block分支记录“Packet dropped”，但该分支没有返回false，而是继续走到函数末尾返回true。源码注释说明这代表内核发送缓冲区满或socket忙，当前报文已被丢弃；并明确留下TODO：增加丢包计数器并在超过阈值时触发错误，或实现异步发送。

RealTimeSocketInterface::send_message()将序列化后的报文交给socket发送；上层RobotDriver::send_robot_command()以该返回值作为发送结果。由此在would_block路径上：
- 报文实际未发送；
- socket层返回true；
- RobotDriver可能把命令视为发送成功；
- 硬件write不一定收到ERROR，也不一定触发controller_manager错误停用；
- 该丢包不会通过现有错误返回值直接进入on_error() STOP尝试。

这与“UDP发送成功不等于机器人执行确认”不同：这里甚至不能保证报文已离开本机内核发送路径。持续丢包是否最终由VAL3序号滞后看门狗触发STOP，取决于机器人侧序号进展、命令周期及任务调度；实际触发时间仍未验证。

#### 6. UDP接收来源校验与协议头验证边界

UDPSocketImpl::handle_data_received()在收到数据后调用上层接收回调；源码TODO明确指出尚需验证sender_endpoint_是否与配置的远端地址匹配，并建议丢弃非预期发送方报文。该提交没有在此回调中执行来源地址检查。部署风险取决于控制网络隔离、路由/防火墙和UDP socket行为，不能据此直接断言外部网络可达或可利用；但来源身份校验确属待验证边界。

FrameHeader::deserialize()读取magic、protocol version、message type、sequence和payload size，但只检查magic number。协议版本在RobotDriver连接建立阶段对当前状态消息进行比较；固定代码没有显示每一条后续状态报文都独立执行同样的版本门禁。RobotStateMessage反序列化中的“Validate header fields”段落没有实际校验逻辑；RobotDriver随后只检查message_type是否为ROBOT_STATE。需继续验证报文长度、payload size、协议版本、消息类型、发送方及控制器重启后重新握手的组合边界。

#### 7. 最新快照缓冲与接收线程错误路径

接收线程在每次反序列化成功后覆盖ThreadSafeBox中的最新消息。如果读取周期低于接收频率，中间样本不会逐条交给read()；序号差可估算中间缺失数量，但不能恢复其状态。对于状态估计/控制用途，这属于采样策略而非天然错误，但必须把采样频率、控制频率和最大允许样本年龄纳入验收。

UDP接收回调在error非空时记录错误后仍继续调用上层callback；随后只要is_receiving()仍为true就重新挂起下一次接收。需验证持续错误时是否形成高频日志/回调循环、线程是否继续存活、is_ready()是否仍仅反映socket connected与receive thread running而无法识别“长时间没有有效报文”。

#### 8. 本节结论

1. 本地接收时间戳不等于机器人状态序号推进；重复报文能刷新本地接收时间，而read_robot_state()忽略new_message=false。
2. 任意序号下降都被当作uint16回绕；小幅乱序旧包会产生虚假大丢包计数并倒退序号基准。
3. 状态丢包计数没有形成可观测告警/阈值门禁；read成功不等于状态流连续健康。
4. UDP would_block实际丢弃报文但仍返回true；上层可能把实际丢弃的命令当作发送成功，且没有丢包计数器。
5. UDP接收回调缺少源码明确标注的发送方地址验证；安全影响需结合现场网络拓扑和过滤规则判断。
6. 接收端只保留最新快照；采样频率不匹配会丢失中间状态样本，虽可估计序号缺口但无法重建样本。
7. 上述均为固定公开原型源码静态审查结论，不证明现场部署该代码或已发生报文丢失、伪造、乱序和危险运动。

#### 9. 新增验证任务 SERVO-751 / G1–G16

- G1：重复发送相同RobotState序号但刷新到达时间，验证read_message的new_message及read_robot_state返回值/状态接口变化。
- G2：序号100后注入99、98、101，验证回绕误判、lost_packages数值和last_read_sequence_number_倒退。
- G3：验证65534→65535→0→1、65535→0以及跨回绕丢包的边界计算。
- G4：验证机器人重启/VAL3任务重启后序号复位时的重新同步、误判及控制器门禁。
- G5：在接收频率高于controller read频率时注入突发状态，验证ThreadSafeBox覆盖样本数、lost_packages统计和控制周期取样。
- G6：为状态重复、序号不前进、乱序和丢包建立明确的状态健康度/最大年龄/降级策略。
- G7：在UDP send触发would_block时验证函数返回值、实际报文到达率、RobotDriver返回值和hardware write结果。
- G8：验证连续would_block时VAL3 sequence_delay增长、STOP触发时间及机器人真实停止响应。
- G9：核对would_block以外的UDP错误是否正确返回false，并验证错误注入到on_error/STOP调用链。
- G10：实现/验证发送丢包计数、阈值报警和控制器降级/停止策略；明确不能将本机send_to成功等同机器人ACK。
- G11：从非预期源地址发送格式正确的状态报文，验证当前部署的UDP来源过滤、网络隔离与状态注入防护。
- G12：验证FrameHeader协议版本、message_type、payload_size、实际长度、magic及消息体字段一致性。
- G13：验证控制器/VAL3版本升级或重启后协议协商、序号重新同步和旧报文隔离。
- G14：注入UDP接收错误、socket关闭、线程仍running但无有效数据、持续错误回调，核实is_ready与有效状态门禁。
- G15：验证diagnostic subscriber的重复/乱序/丢包/过期行为及其是否能及时暴露控制任务故障。
- G16：在隔离测试环境完成重复、乱序、丢包、回绕、would_block、非预期源地址等组合故障注入，并形成HIL/FAT/SAT证据。

G1–G16全部未执行。上述项目不得标记为已测试。

#### 10. 证据边界、状态更正与验收

本节对§9.3.167“发送成功不构成接收/执行确认”的表述作进一步细化：UDP普通发送返回true本来就不等于机器人接收/执行确认；此外，固定实现的would_block分支明确丢弃报文却仍返回true，因此该分支连“本机已成功提交发送”也不能成立。§9.3.167中“发送失败返回ERROR”只适用于send()实际返回false的错误路径，不覆盖would_block丢包路径。

本轮未运行ROS构建、单元测试、网络故障注入、UDP发送缓冲区压力测试、VAL3编译/仿真、CS9/HIL、FAT/SAT或实机验证；未修改ICube/MoveIt/ros2_control上游或应用PR。现场驱动版本、网络隔离、源地址过滤、CS9协议部署和安全链均未确认。Stäubli工程级验收未通过，TODO-EXT-001未授权合并。

#### 固定源码Blob

- ICube README与原型状态：https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/README.md
- RealTimeSocketSubscriber实现：https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/src/real_time_socket_subscriber.cpp （Blob SHA e2cd8fc50b2b13d9e31b2c024e90f9da76107622）
- Subscriber接口/MessageStatus：https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/include/staubli_robot_driver/real_time_socket_subscriber.hpp （Blob SHA 330839cb25e53fe961541f29f634722bec4a47c4）
- RobotDriver读取与staleness：https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/src/robot_driver.cpp （Blob SHA ede48a314856a455df9d8434f354aaf9fbc47bff）
- UDP发送与接收线程：https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/src/communication/udp_socket_impl.hpp （Blob SHA 1309a8f2d59e8295869e178af82a66868bb911ff）
- UDP socket接口：https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/include/staubli_robot_driver/communication/udp_socket.hpp （Blob SHA 31eb5e2e9218e17160fc10dfbd72d77be4b3b0e5）
- FrameHeader与16位序号：https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/include/staubli_robot_driver/communication/protocol.hpp （Blob SHA 773cdeb9c4bf6e2dab3cf9e15426e4e954e35dea）
- FrameHeader反序列化：https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/src/communication/protocol.cpp （Blob SHA d31077aefc1d5515919033aa967c431a01d49a4a）
- 消息反序列化：https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/src/communication/messages.cpp （Blob SHA 86c4d7b6eac0e2455214fc78ebd6864ae5b0b0c6）
- UDP socket测试：https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/test/unit_tests/communication/test_rt_socket_interface.cpp （Blob SHA 9d54374f3b1327f73b5ae276719f27b6a7b62858）
- RobotDriver测试：https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/test/unit_tests/test_robot_driver.cpp （Blob SHA 44da0046ce37fe52649a84ab0833ffee3d9973c5）


### §9.3.169 VAL3同步控制任务overrun、序号回显与命令延迟看门狗耦合

#### 1. 审查范围与固定版本

沿§9.3.168的UDP背压/丢包发现，继续检查ICube公开仓库`ICube-Robotics/staubli_driver_ros2`固定提交`bd658e2d266e315d2ee35f985fb352ea88306b79`中的VAL3任务创建、controlTask执行顺序、序号生成/回显、状态发布和停止调用。重点文件及Blob SHA见本节末尾。该提交的仓库README明确标注Jazzy/CS9开发原型、仅位置控制且不是工业成熟软件；以下结论不得外推为Stäubli现场实际配置。

#### 2. 4 ms同步任务与overrun处理

`start.pgx`将`l_nCtrlPeriod`设为`0.004`，随后执行`taskCreateSync "controlTask", l_nCtrlPeriod, bIsOverrun, controlTask()`。因此该公开原型的名义控制任务周期为4 ms（250 Hz）。启动程序先清空控制socket缓冲区、设置`mMdesc.blend=off`并执行`stopMove()`/`resetMotion()`；supervision/diagnostics task配置仍标记TODO。

`controlTask.pgx`每轮开头检查`bIsOverrun`：若为true，仅记录`Task overrun detected`、将标志清false并执行`nOverruns = nOverruns + 1`。初始化时`nOverruns=0`。全仓库代码搜索仅发现该变量在数据表声明、controlTask初始化和递增位置；未发现累计阈值、STOP/ERROR切换、速度降级或外部消费者。虽然`nOverruns`在`ros2_server.dtx`中声明为public，但RobotState/DiagnosticData消息结构和序列化路径未见该字段，不能把public声明等同于ROS可观测性。

Stäubli CS9同步任务说明（TSS.000.014.04-A）描述：同步任务按创建时周期调度；若一次执行超过指定周期，当前周期正常结束，但下一周期取消，并通过创建任务时指定的布尔变量向VAL3应用报告overrun。由此可知，`bIsOverrun`是调度器提供的周期超限指示，而非本程序主动测量的执行时间。固定原型只消费该标志用于日志/计数，没有将单次或累计overrun直接映射到STOP。

#### 3. sequence_delay不是墙钟超时或overrun计数

`getNextSequenceNumber.pgx`每次调用将`l_nSequenceNumber`加1，并在大于65535时归零；调用点位于controlTask每轮更新状态后。因此该序号只在controlTask实际运行并走到该调用点时推进。

`computeSequenceDelay.pgx`计算`l_nSequenceNumber - robot_command_msg.header.nMsgSequenceNumber`，负值小于-60000时加65536以处理uint16回绕。ROS侧`robot_driver_helpers.hpp::set_sequence_number()`则把最近读到的`RobotStateMessage.header.sequence_number`直接复制到RobotCommand。也就是说命令序号是对最近机器人状态序号的回显，不是独立的主机墙钟/发送周期计数。`sequence_delay`表示该回显在序号空间中的滞后，不能单独当作实际经过毫秒数、控制任务overrun次数或端到端停止时间。

因此，§9.3.167/§9.3.168中把5/25周期阈值直接换算为固定墙钟时间时，必须保留前提：只有在目标CS9任务确实按配置周期稳定推进、ROS控制周期匹配、状态/命令序号持续单调且无调度超限/网络异常时，周期数换算才有意义。overrun后序号推进与真实时间的关系、多个周期取消或长时任务阻塞的行为，必须通过目标硬件动态测量。不能从静态代码给出停止响应上界。

#### 4. 状态遥测存在一轮计算滞后

controlTask当前循环顺序为：`updateState()`→递增并写入RobotState序号→把当前`l_nSequenceDelay`写入`robot_state_msg.robotState.nSequenceDelay`→编码并发送RobotState→调用`readData()`接收命令→`computeSequenceDelay()`重算延迟→执行>5/>25周期门限和命令控制。因此本轮刚收到的命令不会反映在本轮已经发出的状态报文中，ROS侧看到的`nSequenceDelay`至少滞后一轮控制任务。该字段不能用作当前周期的同步反馈或单周期即时确认。

#### 5. STOP路径与overrun路径相互独立

固定controlTask的命令延迟门禁仍是：机器人运动时`l_nSequenceDelay > 5`切换STOP/ERROR；静止时`>25`切换STOP/ERROR；负延迟也进入错误路径。STOP执行前会根据前一控制模式调用`stopJointPositionControl`/`stopJointVelocityControl`，随后调用`stopMove()`和`resetMotion()`。但是`bIsOverrun`检查发生在循环开头，当前实现只记录和计数，不直接设置`l_bError`、不修改`l_nCmdMode`，也不立即调用STOP。只有后续独立的序号延迟/命令有效性/运动控制错误条件触发时，才会走STOP路径。

这形成三个不同的观测维度：调度器overrun标志、VAL3命令序号差、ROS侧RobotState接收年龄。它们分别反映周期调度未按时完成、命令序号回显滞后、状态报文到达新鲜度，不能相互替代。尤其§9.3.168发现的UDP would_block丢包返回true会使主机误以为命令发送成功；该类故障是否能由序号差及时暴露，取决于后续状态序号是否推进及主机命令序号回显，需在组合故障注入中验证。

#### 6. SERVO-752 / H1–H16验证矩阵

| 子项 | 验收对象 | 状态 |
|---|---|---|
| H1 | CS9目标版本中controlTask实际同步周期、task priority/创建顺序及4 ms周期配置 | 未执行 |
| H2 | 单次执行超过4 ms时当前周期、下一周期取消行为与bIsOverrun置位时序 | 未执行 |
| H3 | 连续overrun、任务长时间阻塞及bIsOverrun布尔标志是否合并多个事件 | 未执行 |
| H4 | nOverruns初始化、递增、复位、溢出及是否存在其他读取/阈值消费者 | 未执行 |
| H5 | nOverruns是否经RobotState、DiagnosticData、日志或现场监控接口对外可见 | 未执行 |
| H6 | overrun单独发生时是否仍继续发送状态、接收命令和执行运动更新 | 未执行 |
| H7 | overrun期间VAL3状态序号实际推进次数与墙钟周期/时间戳的关系 | 未执行 |
| H8 | ROS命令序号复制最近机器人状态序号的时序、重复值与主机控制周期错位 | 未执行 |
| H9 | computeSequenceDelay在单次/连续overrun、UDP丢包、延迟和恢复时的数值轨迹 | 未执行 |
| H10 | 运动中>5、静止时>25周期阈值与实际墙钟延迟、停止响应的对应关系 | 未执行 |
| H11 | 状态报文先发送、后接收命令/计算延迟造成的nSequenceDelay一轮滞后 | 未执行 |
| H12 | overrun与UDP would_block、命令重复、状态stale timeout组合故障及STOP路径 | 未执行 |
| H13 | updateState、编码/发送、UDP读取、movejSync更新和stopMove/resetMotion各阶段执行时间分布 | 未执行 |
| H14 | controlTask异常退出、runtime error、任务停止/重启后socket、序号和控制模式恢复 | 未执行 |
| H15 | 通过CS9/VAL3仿真或HIL验证overrun告警、外部可观测性、降级策略与停止上界 | 未执行 |
| H16 | Stäubli现场VAL3应用版本、CS9固件、任务周期、ROS控制周期、诊断映射及安全PLC链核实 | 未确认，现场证据缺失 |

H1–H15全部未执行，H16现场证据缺失。未运行VAL3编译/仿真、CS9任务调度测量、overrun注入、ROS集成、UDP组合故障注入、HIL、FAT/SAT或实机验证。未修改ICube/MoveIt/ros2_control上游或应用PR。Stäubli工程级验收未通过，TODO-EXT-001未授权合并。

#### 7. 固定源码Blob

- `controlTask.pgx`（Blob SHA `00a69c4d13879116fce744ceb1611ecd05d65edf`）：https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/val3/userapp/ros2_server/controlTask.pgx
- `start.pgx`（Blob SHA `2d72315f0da1e18c959a24d3d75622652ee1287b`）：https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/val3/userapp/ros2_server/start.pgx
- `computeSequenceDelay.pgx`（Blob SHA `e96e5b378bc263255ee4f28720306ee911b8a5c1`）：https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/val3/userapp/ros2_server/Comm/computeSequenceDelay.pgx
- `getNextSequenceNumber.pgx`（Blob SHA `8bdda02a8887968b1b86e42be733f553b1e36b19`）：https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/val3/userapp/ros2_server/Comm/getNextSequenceNumber.pgx
- `robot_driver_helpers.hpp`（Blob SHA `88a0cac08d3a299b7330eaa72b1afaaeab2fe41b`）：https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/include/staubli_robot_driver/robot_driver_helpers.hpp
- `robot_driver.cpp`（Blob SHA `ede48a314856a455df9d8434f354aaf9fbc47bff`）：https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/src/robot_driver.cpp
- `updateState.pgx`（Blob SHA `94b2bda039c05bed15c5bbc8a5afd03e9ec3dccf`）：https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/val3/userapp/ros2_server/updateState.pgx
- `ros2_server.dtx`（Blob SHA `558dc2db671da45f5b859a3526148ce816eb6dd4`）：https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/val3/userapp/ros2_server/ros2_server.dtx
- Stäubli CS9同步任务调度参考（TSS.000.014.04-A）：https://bvdp.inetdoc.net/files/iut/staubliiut/doc/Real%20Time%20Val3-Fieldbus%20Synchronization%20TSS00001404A.pdf


### §9.3.170 VAL3 controlTask退出/停止入口、初始化失败与ROS硬件生命周期

#### 1. 审查范围

固定ICube公开提交`bd658e2d266e315d2ee35f985fb352ea88306b79`，沿§9.3.169任务overrun与§9.3.168命令失联问题，读取VAL3 `start.pgx`、`stop.pgx`、`controlTask.pgx`、`readData.pgx`、`resetControlSocket.pgx`、工程`ros2_server.pjx`以及ROS `StaubliHardwareInterface`生命周期回调和`RobotDriver::send_stop_all_command()`。该仓库是公开Jazzy/CS9开发原型，不代表Stäubli现场应用版本。

#### 2. VAL3 stop程序未显式停止controlTask

`stop.pgx`的全部动作只有：记录退出日志、调用`stopMove()`、`resetMotion()`、清空`siSocketControl`缓冲区。未发现其设置`l_bStopControlTask`，也未发现任务停止/删除调用。`controlTask.pgx`把局部变量`l_bStopControlTask`初始化为false，主循环条件为`while !l_bStopControlTask`；全仓库搜索只发现声明和false初始化，没有任何true赋值。因而固定源码无法证明执行`stop.pgx`后周期控制任务会退出。

这不等于已经证明该任务在所有VAL3运行模式下必然继续运行；需验证`stop.pgx`是否被外部应用管理器调用、VAL3任务上下文与停止语义、是否存在未纳入仓库的外部停任务机制。

#### 3. 清空socket不等于使缓存命令失效

`controlTask`将最近解码命令保存在局部`robot_command_msg`。若没有新包但缓存命令`bIsValid`仍为true，代码中的“检查上一条命令staleness”分支仍是TODO；随后继续基于缓存命令计算sequence delay并选择运动模式。`stop.pgx`清空UDP接收缓冲，但没有显式将该缓存命令置为invalid，也没有改变controlTask局部的`l_nCmdMode`或`l_bStopControlTask`。

因此若stop程序与controlTask并发执行，存在stopMove/resetMotion完成后，控制任务在后续周期仍消费旧命令或重新进入位置控制更新的静态风险。实际是否发生、任务调度顺序、movejSync状态约束和延迟看门狗是否先行触发，均须通过VAL3仿真/CS9故障注入确定。不能据此声称现场机器人必然会重启运动。

#### 4. controlTask初始化失败与静默退出可观测性

`controlTask`初始化RobotState消息、RobotCommand消息、控制socket时，任一调用失败都会将局部`l_bError`设为true、写日志并直接`return`。这些早退分支没有统一执行STOP、socket清理、错误状态上报、重试或任务重启。`start.pgx`设置周期后只调用`taskCreateSync`，没有检查任务创建结果或监控任务运行状态；supervision/diagnostics task配置仍为TODO。`ros2_server.pjx`只列出`start`/`stop`/`controlTask`等程序，没有看到独立supervisor程序。

固定代码因此存在启动失败/任务退出后的可观测性和恢复机制缺口。任务退出后机器人端的最后运动状态、VAL3应用调度语义以及控制器内建看门狗行为不能由仓库源码确定，必须在目标CS9环境实测。

#### 5. ROS hardware lifecycle不是统一的停止确认路径

固定`staubli_hardware_interface.cpp`：
- `on_cleanup()`仅调用`robot_driver_->disconnect()`，没有先发送STOP。
- `on_shutdown()`仅在连接存在且`state_msg_.control_state != STOP`时尝试`send_stop_all_command()`，随后断开连接；STOP返回值未检查，回调仍返回SUCCESS。
- `on_error()`在连接存在时尝试`send_stop_all_command()`，同样不检查返回值并返回SUCCESS；未连接则返回ERROR。
- 析构函数只disconnect，不发送STOP。
- `RobotDriver::send_stop_all_command()`在准备命令或发送失败时返回false，但上述两个回调没有消费这个结果。

因此ROS lifecycle回调返回SUCCESS不等于STOP报文已发送，更不等于VAL3已接收或机器人已停止。`on_cleanup`、析构、SIGKILL、进程崩溃或主机掉电不能假设会执行`on_shutdown`/`on_error`。这也不证明现场没有独立安全PLC、控制器任务或外部看门狗；现场安全链必须单独审查。

#### 6. SERVO-753 / I1–I16验证矩阵

| 子项 | 验收对象 | 状态 |
|---|---|---|
| I1 | `stop.pgx`调用后controlTask任务是否仍处于运行状态、是否继续执行周期 | 未执行 |
| I2 | `l_bStopControlTask`所有赋值点、外部引用及实际退出条件 | 未执行 |
| I3 | stop程序调用与controlTask并发时的执行顺序、竞态和socket访问 | 未执行 |
| I4 | stop.pgx清空socket后，缓存的上一条RobotCommand是否仍有效及是否再次下发 | 未执行 |
| I5 | 无新命令时staleness TODO的实际表现、阈值、失效命令清理和停止时延 | 未执行 |
| I6 | RobotState消息初始化失败时controlTask直接return后的任务状态、运动状态及报警 | 未执行 |
| I7 | RobotCommand消息初始化失败时controlTask直接return后的任务状态、运动状态及报警 | 未执行 |
| I8 | resetControlSocket失败时controlTask直接return、socket恢复和任务重启行为 | 未执行 |
| I9 | taskCreateSync创建失败、任务异常终止、runtime error及VAL3应用重启的检测机制 | 未执行 |
| I10 | start.pgx重复执行时是否重复创建controlTask、旧任务/socket残留及状态复位 | 未执行 |
| I11 | stop.pgx、controlTask内部STOP、VAL3应用停止/卸载三种路径的差异 | 未执行 |
| I12 | ROS on_cleanup、on_shutdown、on_error、析构函数各自调用条件与停止/断连顺序 | 未执行 |
| I13 | on_shutdown/on_error忽略send_stop_all_command返回值时的错误传播与生命周期状态 | 未执行 |
| I14 | ROS进程崩溃、SIGKILL、主机掉电、网络断开时是否存在机器人侧独立失联停止机制 | 未执行 |
| I15 | VAL3任务退出/卡死与UDP丢包/命令缓存组合故障下的停止响应时间和安全链 | 未执行 |
| I16 | 目标现场VAL3应用、CS9固件、启动/停止调用方、ROS lifecycle配置及安全PLC链核实 | 未确认，现场证据缺失 |

I1–I15全部未执行，I16现场证据缺失。未运行VAL3编译/仿真、任务停止/重启/初始化故障注入、ROS lifecycle测试、CS9/HIL、FAT/SAT或实机验证。未修改ICube/MoveIt/ros2_control上游或应用PR。Stäubli工程级验收未通过，TODO-EXT-001未授权合并。

#### 7. 固定源码Blob

- `stop.pgx`（Blob SHA `8d88991f087ea2be2e65daacff742da5d58ac73c`）：https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/val3/userapp/ros2_server/stop.pgx
- `start.pgx`（Blob SHA `2d72315f0da1e18c959a24d3d75622652ee1287b`）：https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/val3/userapp/ros2_server/start.pgx
- `controlTask.pgx`（Blob SHA `00a69c4d13879116fce744ceb1611ecd05d65edf`）：https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/val3/userapp/ros2_server/controlTask.pgx
- `ros2_server.pjx`（Blob SHA `b58dbbf1daf778da64e4ff9551d890ee9ec8514b`）：https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/val3/userapp/ros2_server/ros2_server.pjx
- `staubli_hardware_interface.cpp`（Blob SHA `4ae2b8c8d91857e5e32558bfcd16e2c391b9c3d0`）：https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/src/staubli_hardware_interface.cpp
- `robot_driver.cpp`（Blob SHA `ede48a314856a455df9d8434f354aaf9fbc47bff`）：https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/src/robot_driver.cpp
- `readData.pgx`（Blob SHA `bf2e0f3d26e66724b9f656261e29fe573bd5f3b0`）：https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/val3/userapp/ros2_server/Comm/readData.pgx
- `resetControlSocket.pgx`（Blob SHA `25d414065b4567c5634ef8890cc8cafd6f7e9b3e`）：https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/val3/userapp/ros2_server/Comm/resetControlSocket.pgx

### §9.3.171 VAL3安全状态来源、运动许可与ROS接口语义

审查固定公开提交`ICube-Robotics/staubli_driver_ros2@bd658e2d266e315d2ee35f985fb352ea88306b79`中的`updateState.pgx`、`controlTask.pgx`、位置/速度控制程序、状态序列化和ROS hardware interface状态映射。

**状态来源与语义发现：**

1. `updateState.pgx`将`isPowered()`写入`bDrivePowered`和`bBrakeReleased`。在此原型中`brakes_released`并非独立制动器反馈，而是驱动上电状态代理；上电与制动器机械释放/反馈不是可互换概念。
2. `nSafetyStatus=esStatus()`；`bEStopped=(nSafetyStatus != 0)`；`bWaitAck=(nSafetyStatus == 1)`。代码注释将0/1/2/3/4分别解释为无安全停止、等待安全重启、SS1、SS2、等待WMS重启。ROS `estop_pressed`来自`bEStopped`，因此任何非零安全状态均会被映射为true，不能解释成物理急停按钮的直接输入。
3. `bMotionPossible`当前表达式为`bDrivePowered && !bEStopped`。更严格的表达式`bDrivePowered && !bEStopped && (nRobotStatus == 0)`在源码中被注释；`nRobotMode`由`workingMode(nRobotStatus)`另行更新，但没有参与当前motion_possible计算。该差异可能使软件层运动许可状态比文档语义宽，须验证Hold/Manual/Test/模式转换和控制器实际门禁。
4. `bInError`由controlTask本地`l_bError`赋值，不是完整控制器错误码或安全诊断分类。`bMotionPossible`为false时，位置/速度控制程序会调用各自stop控制路径并设置错误；这是VAL3应用软件门禁，不等于安全额定停止功能。
5. ROS hardware interface将这些字段导出为supervision state interfaces。字段序列化/解码成功只证明协议数据传输，不证明其语义与控制器安全硬件输入一致，也不证明数据新鲜度或安全完整性。

**工程边界：**不能把`brakes_released`、`motion_possible`、`estop_pressed`等ROS状态接口当作安全PLC、STO、硬接线急停、制动器安全反馈或安全认证信号。实际安全功能、停止类别、制动器监控、双通道输入、复位条件、响应时间及认证等级必须从目标现场CS9安全配置、机器人型号安全手册、安全PLC图纸和验证记录确认。

新增SERVO-754/J1-J16，J1-J15全部未执行，J16现场证据缺失。未执行VAL3/CS9仿真、安全输入注入、急停/SS1/SS2响应测量、制动器反馈故障测试、HIL、FAT/SAT或实机验证。公开原型静态结论不得归属现场部署；未修改ICube/MoveIt/ros2_control上游。Stäubli工程级验收未通过，TODO-EXT-001未授权合并。

#### 固定源码Blob

- `updateState.pgx`（Blob SHA `94b2bda039c05bed15c5bbc8a5afd03e9ec3dccf`）：https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/val3/userapp/ros2_server/updateState.pgx
- `updateJointPositionControl.pgx`（Blob SHA `28e2f1d6a3482a126b16474c957a608262c32218`）：https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/val3/userapp/ros2_server/Control/updateJointPositionControl.pgx
- `updateJointVelocityControl.pgx`（Blob SHA `72f4eb0215ceeae2c3a528013ea2a79c4dc46344`）：https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/val3/userapp/ros2_server/Control/updateJointVelocityControl.pgx
- `staubli_hardware_interface.cpp`（Blob SHA `4ae2b8c8d91857e5e32558bfcd16e2c391b9c3d0`）：https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/src/staubli_hardware_interface.cpp

### §9.3.172 安全状态采样时序、控制周期竞态与ROS状态快照

审查固定公开提交`ICube-Robotics/staubli_driver_ros2@bd658e2d266e315d2ee35f985fb352ea88306b79`中的`start.pgx`、`controlTask.pgx`、`updateJointPositionControl.pgx`、`updateJointVelocityControl.pgx`、`encodeRobotStateMsg.pgx`及ROS hardware interface。

**VAL3控制循环顺序：**`start.pgx`配置`l_nCtrlPeriod=0.004`并通过`taskCreateSync`启动控制任务。`controlTask.pgx`每周期先调用`updateState()`、生成序号并发送状态，再接收/解码UDP命令、检查命令序号延迟和模式转换，随后执行运动命令。位置控制子程序使用传入的`x_robotState.bMotionPossible`快照做门禁，然后调用`$movejSync()`；两者之间没有再次读取安全状态或重新调用`updateState()`。因此在状态采样之后、命令执行之前发生的安全状态变化，存在应用层继续使用旧快照的时间窗口。4 ms仅是配置周期，不是实测安全响应时间，也不能据此推导最大停止延迟。

**状态有效性与协议编码：**`updateState()`设置`bIsValid`，但`controlTask`在调用后没有显式检查该字段。`encodeRobotStateMsg.pgx`检查消息初始化、消息类型、头部大小和载荷大小等基本条件，再编码状态位及valid-field位；成功编码/发送只表示消息格式处理通过，不表示所有安全状态字段已由独立有效性机制确认，也不证明状态足够新鲜。

**ROS硬件循环：**`read()`从驱动读取RobotState并更新`state_msg_`；`write()`使用缓存状态检查`error_state`和`control_state==INVALID`，未见状态时间戳/年龄门禁，也未在每次非STOP命令发送前检查`motion_possible`、`safety_status`或`brakes_released`。`prepare/perform_command_mode_switch`仅在切换到JOINT_POSITION时检查`error_state`和`motion_possible`；`operation_mode_status!=0`（HOLD）仅记录警告。因而模式切换校验与每周期写命令校验不是同一条状态门禁路径。

**速度控制边界：**公开原型的`updateJointVelocityControl.pgx`将安全限制留为TODO，速度执行调用被注释并直接返回错误；ROS hardware interface也拒绝JOINT_VELOCITY模式切换。因此不能把该原型描述为已具备端到端速度控制执行能力。

新增SERVO-755/K1-K16，K1-K15全部未执行，K16现场证据缺失。未执行状态变化竞态注入、4 ms周期/抖动测量、ROS read/write错周期测试、CS9安全响应测量、VAL3仿真、HIL、FAT/SAT或实机测试。以上为固定公开原型静态代码审查，不代表现场必然复现或现场安全控制器没有独立保护。未修改ICube/MoveIt/ros2_control上游；Stäubli工程级验收未通过，TODO-EXT-001未授权合并。

#### 固定源码Blob

- `start.pgx`（Blob SHA `2d72315f0da1e18c959a24d3d75622652ee1287b`）：https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/val3/userapp/ros2_server/start.pgx
- `controlTask.pgx`（Blob SHA `00a69c4d13879116fce744ceb1611ecd05d65edf`）：https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/val3/userapp/ros2_server/controlTask.pgx
- `updateJointPositionControl.pgx`（Blob SHA `28e2f1d6a3482a126b16474c957a608262c32218`）：https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/val3/userapp/ros2_server/Control/updateJointPositionControl.pgx
- `updateJointVelocityControl.pgx`（Blob SHA `72f4eb0215ceeae2c3a528013ea2a79c4dc46344`）：https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/val3/userapp/ros2_server/Control/updateJointVelocityControl.pgx
- `encodeRobotStateMsg.pgx`（Blob SHA `0dadb0cc7f03de3da165cafa86fa5f943f097ec3`）：https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/val3/userapp/ros2_server/Serialization/encodeRobotStateMsg.pgx
- `staubli_hardware_interface.cpp`（Blob SHA `4ae2b8c8d91857e5e32558bfcd16e2c391b9c3d0`）：https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/src/staubli_hardware_interface.cpp


## §9.3.173｜VAL3停止路径语义、movejSync结束调用与停止完成条件

### 审查范围与固定基线

本节继续使用ICube公开仓库固定提交`ICube-Robotics/staubli_driver_ros2@bd658e2d266e315d2ee35f985fb352ea88306b79`。该项目自述为ROS 2 Jazzy/CS9开发原型，不能认定为任何目标现场部署版本。审查文件及Blob：

- `Control/stopJointPositionControl.pgx`：`bd4be41dff93258d5c08cbf9411af3d811b5f6c9`
- `Control/stopJointVelocityControl.pgx`：`9a41ba293561d0ac216bebcb4da69b7c99458df0`
- `stop.pgx`：`8d88991f087ea2be2e65daacff742da5d58ac73c`
- `Control/updateJointPositionControl.pgx`：`28e2f1d6a3482a126b16474c957a608262c32218`
- `controlTask.pgx`：`00a69c4d13879116fce744ceb1611ecd05d65edf`
- `robot_driver.cpp`：`ede48a314856a455df9d8434f354aaf9fbc47bff`
- `staubli_hardware_interface.cpp`：`4ae2b8c8d91857e5e32558bfcd16e2c391b9c3d0`

### 1. movejSync专用结束路径

`stopJointPositionControl.pgx`执行：若`$movejSyncState()!=-1`，则调用`$movejSyncEnd()`；随后无条件设置`x_bError=false`。同仓库`updateJointPositionControl.pgx`注释描述状态-2为movejSync停止于错误、-1为未启动、0为正常运行、1为命令未及时刷新、2为运动被停止/锁定。按该注释，`!= -1`条件包含-2错误状态；但注释不是API规范，不能推断专用结束API在-2时合法或安全。

静态代码没有检查`$movejSyncEnd()`调用结果、没有在调用后重新读取状态，也没有等待机械臂稳定。函数参数`x_bError`即使在专用结束调用异常或状态未清除时也会被设置为false。VAL3源文件没有展示该调用是否抛错/阻塞；`$movejSyncState`/`$movejSyncEnd`亦未在本次检索到的通用VAL3参考手册中找到足以确认其状态机、返回值、并发约束和停止完成语义的定义。必须取得目标CS9版本受控手册或Stäubli书面说明，并通过目标控制器测试，不作推测。

### 2. stopMove/resetMotion不是停止完成确认

Stäubli VAL3 Reference Manual D.280.935.01-F（2020）对`stopMove()`描述为沿当前轨迹停止并暂停程序运动授权；对`resetMotion()`描述为停止并取消已记录运动命令，且恢复此前由stopMove暂停的程序运动授权。两条API说明均明确警告：调用立即返回，VAL3任务不会等待机械臂停止后才执行下一条指令。较早版本D28062804A亦包含相同说明。

因此：

- API返回仅表示VAL3任务已从该指令继续执行，不能解释为机器人已经静止。
- `stopMove()`与`resetMotion()`是普通程序运动控制API，不是安全额定急停、STO或安全PLC功能。
- `resetMotion()`会取消运动队列并恢复程序运动授权；不能把它简单理解为持续禁止运动的“安全锁定”。后续命令是否能重新运动仍取决于应用逻辑和控制器状态。
- 停止完成必须独立定义可观测条件，例如目标控制器认可的静止/稳定反馈、运动队列状态、停止类别、停止时间和停止距离；这些条件及阈值必须由系统风险评估和现场安全设计确定。

公开参考资料（第三方镜像，需核对目标CS9版本）：
- VAL3 Reference Manual D.280.935.01-F（2020）：https://bvdp.inetdoc.net/files/iut/robotiqueBUT2/Manuel_de_ref_VAL3.PDF
- 较早版D28062804A：https://usermanual.wiki/Document/val3referencemanual.275627616.pdf

### 3. 复合停止路径和跨层语义

- **位置模式STOP/ERROR：** `controlTask.pgx`先调用`stopJointPositionControl`，随后在STOP分支调用`stopMove()`和`resetMotion()`。子程序先前的movejSync结束调用与后续普通运动API形成复合路径，但源码没有停止完成确认、返回码传播或静止等待。
- **独立stop.pgx：** 只调用`stopMove()`、`resetMotion()`、`clearBuffer(siSocketControl)`。清空socket缓冲不等于收到机器人端确认，也不等于清除controlTask局部缓存命令或停止controlTask；该路径与前述controlTask内STOP不是同一生命周期事件。
- **速度模式停止：** `stopJointVelocityControl.pgx`只调用`resetMotion()`并清除错误标志。但同一公开原型的速度更新程序仍将执行调用留为TODO并返回错误，故不能宣称存在已实现且验证过的速度运行/停止链。
- **ROS STOP报文：** `RobotDriver::send_stop_all_command()`准备STOP命令并调用本地`send_message()`，只有准备和本地发送均成功才返回true。没有应用层ACK、VAL3接收确认、STOP状态回读或机械臂静止反馈的等待。硬件生命周期回调忽略该返回值；`write()`周期发送STOP报文也只是软件控制路径。
- **CS9安全停止：** 由现场配置的控制器安全功能、安全输入、安全PLC、STO/制动器链及相应停止类别定义。不得用ROS STOP报文、VAL3普通运动API或movejSync软件API替代安全功能，也不得在没有现场证据时推断其停止类别或性能。

### 4. 工程风险与待验证项

主要缺口不是简单地“有没有调用stop”，而是缺少可审计的停止状态机：触发源、请求送达、控制器接受、运动队列取消、减速/停止过程、静止确认、停止类别和复位许可之间没有端到端事务证据。特别是`x_bError=false`、生命周期回调SUCCESS和本地UDP发送成功均可能被误读为停止成功，必须明确禁止这种等价关系。

新增SERVO-756/L1-L16，L1-L15全部未执行，L16现场证据缺失。需在目标CS9受控版本上确认API语义，并分别执行单API、组合调用、重复调用、并发调用、通信中断、控制任务异常退出、运动中急停/安全停止及ROS lifecycle故障注入；测量请求/接收/减速/静止反馈时间和停止距离。未执行VAL3/CS9仿真、HIL、FAT/SAT或实机测试。现场版本/安全配置未知，本节只代表固定公开原型静态审查。

未修改ICube/MoveIt/ros2_control上游，未应用PR；Stäubli工程级验收未通过，`TODO-EXT-001`未授权合并。


## §9.3.174｜VAL3控制任务错误锁存、模式转换与故障遥测可见性

### 审查范围与固定基线

继续使用固定公开源码 `ICube-Robotics/staubli_driver_ros2@bd658e2d266e315d2ee35f985fb352ea88306b79`。该仓库自述为ROS 2 Jazzy/CS9开发原型，不构成目标现场部署证据。本节聚焦控制任务的错误状态生命周期、模式转换和状态报文时序，不重复§9.3.173的停止API语义结论。

| 文件 | Blob SHA |
|---|---|
| `controlTask.pgx` | `00a69c4d13879116fce744ceb1611ecd05d65edf` |
| `updateJointPositionControl.pgx` | `28e2f1d6a3482a126b16474c957a608262c32218` |
| `stopJointPositionControl.pgx` | `bd4be41dff93258d5c08cbf9411af3d811b5f6c9` |
| `decodeRobotCommandMsg.pgx` | `612f5ce9fff12c0bd6c4e90e5685ea1d4b59bcdd` |
| `readData.pgx` | `bf2e0f3d26e66724b9f656261e29fe573bd5f3b0` |

### 1. 错误状态在本周期内被清除，遥测可能看不到瞬态故障

`controlTask.pgx`每轮循环先调用`updateState()`，然后在接收命令之前设置并发送`robot_state_msg.robotState.bInError = l_bError`及`nControlMode = l_nCmdMode`。随后才执行UDP读取、解码、序号延迟检查、命令类型检查、模式转换和运动控制。

若本轮接收/解码/模式转换/控制更新首次置位`l_bError`，同一轮末尾的错误处理会再次执行停止路径、将命令标记无效、清理通信状态，并把`l_bError=false`；只有socket reset失败等发生在清零之后的错误才会继续保留到下一轮。因此本轮新发生且本轮被清除的错误，不会出现在本轮已经发送的状态帧中，也可能不出现在下一轮`bInError`字段中。状态报文最多反映进入本轮时的旧错误快照，而不是本轮最终决策结果。

这是由控制流顺序直接支持的静态结论；是否有独立VAL3日志、控制器诊断或其他外部通道记录该错误，需要逐故障动态验证。不能据此断言所有故障完全不可观测。

### 2. STOP与ERROR模式的内部编码和恢复语义不一致

代码注释定义模式：0=Invalid/Error，1=STOP/Idle，2=Joint position，3=Joint velocity。错误条件先可能把`l_nCmdMode`设为0；但当上一模式不是STOP且新模式不为STOP时，模式转换保护会把`l_nCmdMode`改成1并置`l_bError=true`。错误处理随后又把`l_nCmdMode=0`，清除错误锁存并将命令标记无效、重置socket。

因此模式0既用于错误路径，又会作为错误处理结束后写入`l_nPreviousCmdMode`的内部状态；模式1则用于强制停止和模式切换保护。下一周期发布的`nControlMode`仍在本周期状态发送之后更新，故外部看到的模式也不是本周期最终执行模式。必须分别跟踪“本周期接收到的命令模式”“控制任务决策模式”“执行的停止动作”“下一周期遥测模式”，不能把单个数值当作同步的状态机确认。

### 3. 命令模式切换会进入错误复位路径，而非单纯完成一次STOP

当上一模式为2或3、收到另一非STOP模式时，代码将新模式强制为1并设置错误标志；随后STOP分支按`l_nPreviousCmdMode`调用对应停止子程序，再调用`stopMove()`和`resetMotion()`。由于`l_bError`仍为true，后面的错误处理块会再次执行`stopMove()`和`resetMotion()`，清除命令有效标志并重置UDP控制socket。也就是说，源码实现不是“自动插入一个STOP周期后无缝切换到新控制模式”，而是进入错误处理/通信重置路径；是否需要重新建立命令流、外部控制器如何恢复，必须由协议与动态测试确认。

对位置模式而言，停止子程序自身无条件将传入错误标志清零，但控制任务的`l_bError`仍保持true，直至错误处理块统一清除；因此不能仅凭子程序参数被清零就认为整个控制任务错误已经恢复。重复停止动作及其时间/运动效果仍需按§9.3.173的停止验收矩阵验证。

### 4. 新鲜命令与错误复位之间存在需要明确的握手契约

错误处理会将`robot_command_msg.robotCommand.bIsValid=false`并调用`resetControlSocket()`，但源码没有在本段实现显式的错误事件编号、故障原因码、错误确认报文或恢复阶段握手。错误清除后，外部控制端如何知道故障发生、何时允许重新发送、是否必须重新执行controller lifecycle或重新激活控制器，不能从该VAL3代码单独得出。

`readData.pgx`最多进行两次读取尝试；本节不把该行为重新归类为UDP传输可靠性结论（该主题已在§9.3.168审查）。本节仅指出：控制任务错误处理主动重置socket与命令有效状态，需测试主机端重连/重发时序、旧报文残留、重复STOP和模式重新激活的协议状态机。

### 5. 新增验收任务

新增SERVO-757：

| 子项 | 验收对象 | 状态 |
|---|---|---|
| M1 | 分别注入命令解码错误、非法模式、序号延迟超限、控制更新失败，记录置错/清错时刻 | 未执行 |
| M2 | 抓取每轮发送的RobotState，确认本轮新错误是否被同轮或下一轮遥测观察到 | 未执行 |
| M3 | 对比VAL3日志、RobotState、ROS GPIO状态和主机日志，建立故障事件可观测性矩阵 | 未执行 |
| M4 | 验证模式2→3、3→2、2/3→0、STOP→2/3的实际状态转换与错误处理 | 未执行 |
| M5 | 验证模式切换时停止子程序、stopMove/resetMotion是否重复执行及其动态效果 | 未执行 |
| M6 | 验证错误处理socket reset成功/失败两条路径的错误锁存、控制模式与下一轮状态帧 | 未执行 |
| M7 | 验证控制端在socket重置后重连、首包、序号重置和控制器重新激活的完整握手 | 未执行 |
| M8 | 验证控制器错误发生时ROS controller_manager、控制器spawner和hardware lifecycle的状态是否同步 | 未执行 |
| M9 | 验证连续错误、错误清除后立即重发、重复STOP和延迟旧命令的竞态 | 未执行 |
| M10 | 目标现场VAL3/CS9版本、错误码/诊断通道、恢复策略及现场通信抓包证据 | 未确认，现场证据缺失 |

M1-M9全部未执行，M10现场证据缺失。未执行VAL3/CS9仿真、UDP故障注入、ROS集成测试、HIL、FAT/SAT或实机验证。

### 6. 结论与边界

固定公开原型的控制任务存在“先发状态、后处理本轮命令和错误”的快照顺序；部分错误可在同一周期停止处理后被清除，因此状态报文不保证呈现该周期最终错误状态。控制模式切换保护会置错并进入通信重置逻辑，不是已证明的无缝STOP后切换。上述发现属于静态控制流与遥测契约缺口，不代表现场已部署该版本、已发生故障或机器人在故障后必然继续运动。

未修改ICube/MoveIt/ros2_control上游，未应用PR；未运行VAL3/CS9仿真、ROS构建/测试、HIL、FAT/SAT或实机验证。Stäubli工程级验收未通过，`TODO-EXT-001`未授权合并。

### 固定源码链接

- https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/val3/userapp/ros2_server/controlTask.pgx
- https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/val3/userapp/ros2_server/Control/updateJointPositionControl.pgx
- https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/val3/userapp/ros2_server/Serialization/decodeRobotCommandMsg.pgx


## §9.3.175｜控制报文序号重启、旧命令残留与通信重置边界

### 审查范围与固定基线

固定审查公开原型 `ICube-Robotics/staubli_driver_ros2@bd658e2d266e315d2ee35f985fb352ea88306b79`。本节只分析VAL3控制socket重置、16位序号重启、ROS接收端序号跟踪、命令陈旧检测和重连边界；不将网络层理论可能性写成已发生的现场故障。

| 文件 | Blob SHA |
|---|---|
| `controlTask.pgx` | `00a69c4d13879116fce744ceb1611ecd05d65edf` |
| `Comm/resetControlSocket.pgx` | `25d414065b4567c5634ef8890cc8cafd6f7e9b3e` |
| `Comm/readDataOnce.pgx` | `652aa04548c814febab3c8c3fc807093261efd97` |
| `Comm/computeSequenceDelay.pgx` | `e96e5b378bc263255ee4f28720306ee911b8a5c1` |
| `Comm/getNextSequenceNumber.pgx` | `8bdda02a8887968b1b86e42be733f553b1e36b19` |
| `src/real_time_socket_subscriber.cpp` | `e2cd8fc50b2b13d9e31b2c024e90f9da76107622` |
| `include/staubli_robot_driver/real_time_socket_subscriber.hpp` | `330839cb25e53fe961541f29f634722bec4a47c4` |
| `include/staubli_robot_driver/robot_driver_helpers.hpp` | `88a0cac08d3a299b7330eaa72b1afaaeab2fe41b` |
| `src/robot_driver.cpp` | `ede48a314856a455df9d8434f354aaf9fbc47bff` |
| `include/staubli_robot_driver/robot_driver.hpp` | `62c87a6741aa082db4599bb2c048aec0fcd7a464` |

### 1. VAL3内部错误复位将状态序号直接归零，但没有会话代次

`controlTask.pgx`启动时把`l_nSequenceNumber=0`；每轮先调用`getNextSequenceNumber()`，序号递增并在大于65535时回绕到0。错误处理块又显式执行`l_nSequenceNumber=0`、`l_nSequenceDelay=1000`、清除命令有效标志和`l_bControlActive`，再调用`resetControlSocket()`。因此错误复位后的下一条RobotState序号会从1重新开始。

协议头只有16位序号、消息类型、magic number、协议版本和payload长度，没有会话ID、启动代次、随机nonce或复位epoch。自然的65535→0回绕与错误处理导致的0→1重启，在报文头上没有可区分标记。该设计不证明一定会误收旧包，但缺少可供接收端可靠区分“正常回绕”和“控制任务重新初始化”的显式会话边界。

### 2. resetControlSocket不检查配置和清缓冲操作的结果

`resetControlSocket.pgx`依次设置socket timeout、设置换行结束符、调用`clearBuffer()`，随后无条件写入`x_bError=false`。程序没有捕获/检查这些socket操作的返回状态，也没有在清理失败时向调用方报告失败。

因此调用方收到的“无错误”仅能说明该VAL3子程序走到了末尾，不能据此证明socket选项已成功应用、缓冲区已完全清空或对端队列已被排空。特别是`clearBuffer()`只作用于本地VAL3 socket缓冲，不构成网络中在途UDP数据包、主机发送队列或ROS端接收线程的端到端清除确认。

### 3. 无新报文时，上一条命令对象仍可能保持有效

`readDataOnce.pgx`在`sioGet()`读到完整长度时才设置`x_bNewData=true`；读到0字节表示本次没有新数据，只有读到部分数据才标记错误。`controlTask.pgx`仅在`l_bNewCmdMessage`为true时调用`decodeRobotCommandMsg()`。没有新报文时，代码保留`robot_command_msg.robotCommand`此前的内容，并在`bIsValid`仍为true时计算序号延迟；“无新报文时检查上一命令陈旧度”的直接分支仍标记为TODO。

现有控制循环并非完全没有陈旧保护：当`l_bControlActive`为true时，会根据状态序号与命令序号差计算`l_nSequenceDelay`，运动中大于5、静止时大于25会触发STOP/ERROR路径。但这属于按周期序号差推算的保护，不是基于命令接收时间戳的独立超时；其边界依赖状态帧持续发送、循环节拍稳定、序号一致且复位/回绕处理正确。不能把TODO误写成“完全没有陈旧保护”，也不能把序号阈值等同于已验证的墙钟超时。

### 4. ROS侧把序号下降统一当作16位自然回绕

`RealTimeSocketSubscriber::read_message()`在收到的序号小于上次读取序号时，按`MAX_FRAME_SEQUENCE_NUMBER`计算wrap-around丢包数；该分支不区分自然回绕和VAL3控制任务错误复位。它仍把新消息交给上层。该订阅器的`last_read_sequence_number_`在接收线程/订阅器生命周期内维护；VAL3端内部resetControlSocket不会重建ROS订阅器。

`RobotDriver::read_robot_state()`会检查消息类型和接收年龄，并更新`last_valid_sequence_id_`；对`status.lost_packages`的警告目前被注释掉，且没有按序号下降触发会话重新同步。因而控制任务复位在ROS侧可能被统计为一次极大的序号回绕丢包，而不是一个需要显式重新握手的会话事件。

### 5. ROS命令序号直接复制最近收到的状态序号

`set_sequence_number()`把`RobotStateMessage.header.sequence_number`复制到命令头；硬件接口周期写命令也使用`get_current_message_sequence()`返回的最近有效状态序号。该设计建立了“命令回显最近状态序号”的关联，但没有独立命令序号、确认序号、复位epoch或挑战应答。

在VAL3端序号归零后，ROS端必须先接收并采纳新的低序号状态，之后写出的命令才会回显新序号。订阅器把低序号按wrap处理而非按会话重置处理；状态读取端没有显式同步阶段。网络延迟、重排、重复包或状态接收线程与控制写线程交错时，究竟何时从旧序号切换到新序号，当前静态实现没有提供端到端握手保证。

### 6. 新增验收任务

新增SERVO-758：

| 子项 | 验收对象 | 状态 |
|---|---|---|
| N1 | 正常16位序号65534→65535→0自然回绕及命令序号对应关系 | 未执行 |
| N2 | 在不同控制模式和不同运动状态下注入VAL3错误复位，记录序号0→1重启和命令接收恢复 | 未执行 |
| N3 | 验证ROS订阅器将复位后低序号识别为wrap时的lost_packages计算和上层处理 | 未执行 |
| N4 | 验证错误复位前在途、重排、重复和延迟UDP命令在复位后到达时的处理 | 未执行 |
| N5 | 验证无新命令期间上一条有效命令的保留时间、序号延迟阈值与真实墙钟超时的关系 | 未执行 |
| N6 | 验证状态流中断、状态重复、状态序号跳变和接收线程延迟时，硬件接口是否错误地继续发送旧序号命令 | 未执行 |
| N7 | 对resetControlSocket各socket选项及clearBuffer操作进行失败注入，验证错误是否能传递给controlTask | 未执行 |
| N8 | 验证错误复位后ROS写线程首次采纳新状态序号的时序、旧命令缓存和控制模式恢复门禁 | 未执行 |
| N9 | 验证自然序号回绕、VAL3任务重启、socket重置、ROS断线重连四类事件的可区分性 | 未执行 |
| N10 | 获取目标现场CS9/VAL3受控协议版本、socket行为说明、控制任务重启记录和双端抓包 | 未确认，现场证据缺失 |

N1-N9全部未执行，N10现场证据缺失。未执行UDP故障注入、VAL3/CS9仿真、ROS集成测试、HIL、FAT/SAT或实机测试。

### 7. 结论与边界

固定公开原型以16位序号关联状态与命令；VAL3错误处理会把序号归零，但协议没有会话代次，ROS订阅器把序号下降统一按自然回绕处理。无新命令时上一命令对象仍可能保持有效，控制任务用序号差阈值进行陈旧保护，但没有独立接收时间戳超时。resetControlSocket不检查socket配置/清缓冲操作结果，不能把其返回无错误等同于缓冲清理和通信重新同步已成功。

这些是代码结构和协议可观测性缺口，不证明某次现场运行已经接受旧命令、发生失控或实际复位失败。网络重排/旧包是否能穿过具体socket与控制器实现，必须由目标环境动态测试确定。

未修改ICube/MoveIt/ros2_control上游，未应用PR；未运行VAL3/CS9仿真、UDP故障注入、ROS构建/测试、HIL、FAT/SAT或实机验证。现场部署版本与协议适用性仍未确认，Stäubli工程级验收未通过，`TODO-EXT-001`未授权合并。

### 固定源码链接

- https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/val3/userapp/ros2_server/controlTask.pgx
- https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/val3/userapp/ros2_server/Comm/resetControlSocket.pgx
- https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/src/real_time_socket_subscriber.cpp
- https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/include/staubli_robot_driver/robot_driver_helpers.hpp
- https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/src/robot_driver.cpp


## §9.3.176｜VAL3应用启动/停止入口、controlTask生命周期与ROS硬件生命周期解耦

### 审查范围与固定基线

固定审查 `ICube-Robotics/staubli_driver_ros2@bd658e2d266e315d2ee35f985fb352ea88306b79`。本节分析VAL3应用的start/stop入口、同步控制任务创建、项目版本元数据，以及ROS 2 SystemInterface生命周期回调与RobotDriver连接生命周期之间的关系。

| 文件 | Blob SHA |
|---|---|
| `val3/userapp/ros2_server/start.pgx` | `2d72315f0da1e18c959a24d3d75622652ee1287b` |
| `val3/userapp/ros2_server/stop.pgx` | `8d88991f087ea2be2e65daacff742da5d58ac73c` |
| `val3/userapp/ros2_server/ros2_server.pjx` | `b58dbbf1daf778da64e4ff9551d890ee9ec8514b` |
| `src/staubli_hardware_interface.cpp` | `4ae2b8c8d91857e5e32558bfcd16e2c391b9c3d0` |
| `include/staubli_robot_driver/staubli_hardware_interface.hpp` | `a84d0c63b15db168ea453a15571ab1494b8f9e99` |
| `src/robot_driver.cpp` | `ede48a314856a455df9d8434f354aaf9fbc47bff` |

### 1. VAL3 start入口的初始化顺序与任务创建

`start.pgx`执行以下步骤：读取VAL3版本、读取boxcar delay、检查monitor speed（低于100%仅记录warning，等待动作被注释）、清理控制socket缓冲、预留未实现的supervision/diagnostics task（TODO）、设置控制周期为0.004秒、关闭blend、调用`stopMove()`和`resetMotion()`、开启`autoConnectMove(true))，最后设置`bIsOverrun=false`并调用`taskCreateSync "controlTask", l_nCtrlPeriod, bIsOverrun, controlTask()`。

可确认该入口尝试以4 ms周期创建同步控制任务，并在创建前进行普通运动状态/缓冲初始化。但静态代码未显示任务创建返回值、任务已运行确认、首帧发送确认或任务存活监视；`bIsOverrun`被初始化后传入任务创建调用，但没有在该入口后续检查。不能将执行到taskCreateSync这一行等同于控制任务已稳定运行。

### 2. VAL3 stop入口没有显式终止controlTask或等待退出

`stop.pgx`记录退出日志，调用`stopMove()`、`resetMotion())并清理控制socket缓冲；没有显式调用任务停止/删除API，没有设置controlTask退出标志，也没有等待控制任务确认退出。另一方面，`controlTask.pgx`本身是周期任务，持续执行读命令、更新控制、发送状态的循环结构。

因此静态证据只能确认stop入口执行了运动停止请求和缓冲清理；不能证明周期任务已终止、已退出临界区或不会继续访问socket。若VAL3运行时在停止应用时自动管理该应用全部任务，仍需目标版本运行时文档/仿真确认，不能仅凭stop.pgx自行推断。

### 3. ROS硬件生命周期只管理UDP客户端连接，没有显式启动/停止VAL3应用

`RobotDriver::connect()`创建UDP控制接口与诊断订阅器，等待有效状态消息并检查协议版本；源码没有显示通过该连接调用VAL3的`start.pgx`或`stop.pgx`。换言之，ROS驱动连接成功与VAL3应用已启动是两个独立条件：驱动只是等待机器人端已经在发送有效状态。

`StaubliHardwareInterface`的`on_configure()`连接RobotDriver；`on_activate()`只把控制模式设置为STOP；`on_cleanup()`断开RobotDriver；`on_shutdown()`在连接且当前状态非STOP时尝试发送STOP，再断开；`on_error()`在连接时尝试发送STOP。类声明覆盖了这些回调，但没有覆盖`on_deactivate()`。因此controller/hardware lifecycle的activate/deactivate并不等价于VAL3 start/stop任务生命周期，deactivate回调也没有在该插件中实现专门的停止握手。

### 4. Cleanup、shutdown和析构的停止保证并不相同

`on_cleanup()`只调用`RobotDriver::disconnect()`，没有先显式发送STOP；`on_shutdown()`只有在`is_connected()`且最后读到的`control_state != STOP`时才发送STOP，随后立即disconnect，不等待机器人端状态回读或机械臂静止；硬件接口析构函数只调用disconnect。RobotDriver的disconnect会释放通信接口、停止本地接收线程、断开UDP socket并重置本地状态，但它不能证明VAL3任务已停止或机器人已进入安全静止状态。

此外`on_shutdown()`未检查`send_stop_all_command()`的返回值后再决定是否断开；其后续disconnect仍会执行。该静态路径需要动态测试确认主机停止流程中的STOP报文是否真正送达、是否被VAL3消费、何时关闭socket以及任务在失去主机通信后如何自行处理。

### 5. 项目版本元数据与运行时兼容性门禁

`ros2_server.pjx`项目参数声明VAL3版本字符串为`s8.20.2Cs9_BS4270`，而`start.pgx`运行时仅读取`getVersion("System"))并取首字符作为major片段，没有执行明确的版本范围拒绝/兼容性分支。该元数据不能证明目标控制器实际加载的应用版本，也不能替代目标CS9控制器固件、VAL3 runtime、应用部署包哈希和现场受控配置记录。

### 6. 新增验收任务

新增SERVO-759：

| 子项 | 验收对象 | 状态 |
|---|---|---|
| P1 | 在目标VAL3/CS9运行时确认start入口的任务创建返回、任务运行状态和首帧发送时序 | 未执行 |
| P2 | 验证重复调用start时已存在controlTask的行为、重复任务防护和错误报告 | 未执行 |
| P3 | 验证stop.pgx执行后controlTask是否继续运行、是否发送状态帧及是否继续访问socket | 未执行 |
| P4 | 通过受控任务退出/应用停止实验确认运行时是否自动终止全部周期任务及其退出时序 | 未执行 |
| P5 | 验证stopMove/resetMotion后任务尚未退出时的socket清理竞态与控制器响应 | 未执行 |
| P6 | 验证ROS on_configure连接前VAL3应用未启动、已启动、启动中、异常退出四种状态的行为 | 未执行 |
| P7 | 验证on_activate/on_deactivate是否应产生STOP、断开或保持连接，以及当前插件实际生命周期调用顺序 | 未执行 |
| P8 | 验证on_cleanup不发STOP直接disconnect后VAL3任务行为与运动状态 | 未执行 |
| P9 | 验证on_shutdown发送STOP后立即disconnect的丢包、确认、停止完成与断链时序 | 未执行 |
| P10 | 核对目标现场VAL3 runtime、CS9固件、应用包版本/哈希、任务调度设置和受控运行时文档 | 未确认，现场证据缺失 |

P1-P9全部未执行，P10现场证据缺失。未执行VAL3/CS9仿真、任务调度故障注入、ROS lifecycle集成测试、HIL、FAT/SAT或实机测试。

### 7. 结论与边界

固定公开原型的VAL3 start入口以4 ms周期创建controlTask；stop入口执行普通运动停止请求和socket缓冲清理，但自身没有显式任务退出/等待逻辑。ROS驱动的connect/disconnect只管理主机侧UDP接口，ROS硬件生命周期也没有显式调用VAL3 start/stop；on_cleanup仅断链，on_shutdown尝试STOP后立即断链，插件没有专门on_deactivate实现。因此“ROS硬件已激活/已清理/已关闭”不能作为“VAL3周期任务已启动/已停止”或“机械臂已安全静止”的等价证明。

上述属于固定公开源码的生命周期边界和待验证契约，不证明VAL3运行时一定遗留任务、不证明stop.pgx在现场不能停止任务，也不证明ROS shutdown一定丢失STOP。VAL3运行时对应用任务的自动管理、stop入口实际调用机制、任务调度和目标控制器安全状态都需在受控CS9环境验证。

未修改ICube/MoveIt/ros2_control上游，未应用PR；未运行VAL3/CS9仿真、ROS构建/测试、HIL、FAT/SAT或实机验证。现场部署版本和运行时行为未确认，Stäubli工程级验收未通过，`TODO-EXT-001`未授权合并。

### 固定源码链接

- https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/val3/userapp/ros2_server/start.pgx
- https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/val3/userapp/ros2_server/stop.pgx
- https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/val3/userapp/ros2_server/ros2_server.pjx
- https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/src/staubli_hardware_interface.cpp
- https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/src/robot_driver.cpp
