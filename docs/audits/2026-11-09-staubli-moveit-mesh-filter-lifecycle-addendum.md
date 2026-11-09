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
