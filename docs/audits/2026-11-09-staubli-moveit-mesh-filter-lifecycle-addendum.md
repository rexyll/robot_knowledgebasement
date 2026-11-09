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
