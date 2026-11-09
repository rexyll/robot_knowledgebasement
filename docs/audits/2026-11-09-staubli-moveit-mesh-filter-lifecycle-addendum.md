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

`ros2_server.pjx`项目参数声明VAL3版本字符串为`s8.20.2Cs9_BS4270`，而`start.pgx`运行时仅读取`getVersion("System")并取首字符作为major片段，没有执行明确的版本范围拒绝/兼容性分支。该元数据不能证明目标控制器实际加载的应用版本，也不能替代目标CS9控制器固件、VAL3 runtime、应用部署包哈希和现场受控配置记录。

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


## §9.3.177｜VAL3工作模式编码、ROS OperationMode枚举与运动许可状态一致性

### 审查范围与固定基线

固定审查 `ICube-Robotics/staubli_driver_ros2@bd658e2d266e315d2ee35f985fb352ea88306b79`，重点追踪VAL3 `workingMode()` 与 `nRobotStatus`、RobotState报文编码、ROS枚举反序列化、hardware_interface模式切换门禁，以及位置控制中的movejSync状态处理。

| 文件 | Blob SHA |
|---|---|
| `val3/userapp/ros2_server/updateState.pgx` | `94b2bda039c05bed15c5bbc8a5afd03e9ec3dccf` |
| `val3/userapp/ros2_server/Serialization/encodeRobotStateMsg.pgx` | `0dadb0cc7f03de3da165cafa86fa5f943f097ec3` |
| `val3/userapp/ros2_server/Control/updateJointPositionControl.pgx` | `28e2f1d6a3482a126b16474c957a608262c32218` |
| `include/staubli_robot_driver/types.hpp` | `8f62807d96a2692e2d9ee653dfdc58888d56d62e` |
| `src/communication/messages.cpp` | `86c4d7b6eac0e2455214fc78ebd6864ae5b0b0c6` |
| `src/staubli_hardware_interface.cpp` | `4ae2b8c8d91857e5e32558bfcd16e2c391b9c3d0` |
| `include/staubli_robot_driver/communication/messages.hpp` | `77f21d8edcb12a39fc6732c2e146586b7fc346fe` |

### 1. VAL3与ROS OperationMode枚举的数值映射不一致

VAL3 `updateState.pgx`将`workingMode(x_state.nRobotStatus)`结果写入`nRobotMode`。该文件注释定义的数值为：

- 0：Invalid / safety transition
- 1：Manual
- 2：Test
- 3：Automatic - Local
- 4：Automatic - Remote

`encodeRobotStateMsg.pgx`将`nRobotMode`原样写入一个字节，没有转换映射表。ROS `types.hpp`中的`OperationMode`却定义为UNKNOWN=0、MANUAL=1、AUTOMATIC=2、REMOTE=3；`messages.cpp`反序列化时直接将收到的字节`static_cast<OperationMode>`。

因此按固定源码的注释/实现逐值对照，至少存在确定的枚举契约不一致：

| VAL3工作模式原值 | VAL3语义 | ROS枚举解释 |
|---:|---|---|
| 0 | Invalid / safety transition | UNKNOWN（表面可对应，但语义未定义） |
| 1 | Manual | MANUAL |
| 2 | Test | AUTOMATIC（不一致） |
| 3 | Automatic - Local | REMOTE（不一致） |
| 4 | Automatic - Remote | 超出已定义OperationMode枚举成员 |

此处是公开原型内VAL3发送端与ROS接收端的静态协议映射缺口。对原始数值4的enum class转换不应被视为得到有效的REMOTE枚举值；当前代码没有显式拒绝未知值或映射为UNKNOWN。必须在协议层统一枚举定义、编码/解码映射和兼容性测试。该发现不能单独证明现场控制器使用了相同VAL3版本/workingMode返回值。

### 2. operation_mode_status被当成通用HOLD标志使用

VAL3注释说明`nRobotStatus`的意义依赖运行模式；对自动模式，0=Move（programmed movement）、1=Move（connection movement）、2=Hold。该值被编码为`operation_mode_status`并由ROS原样接收。

但`perform_command_mode_switch()`中只要`operation_mode_status != 0`便记录“Robot is on HOLD”的warning，不区分自动模式下的connection movement与Hold，也没有依据operation_mode本身解释状态值。由于状态码含义依赖模式，该warning会把自动模式状态1也归为HOLD；对手动/测试模式也不能套用自动模式状态解释。更关键的是，该条件只产生warning，不构成运动模式授权门禁。

### 3. motion_possible并不等同于自动远程运动授权

VAL3 `updateState.pgx`计算：

`bMotionPossible = bDrivePowered AND NOT bEStopped`

而同一函数也读取`workingMode()`和`nRobotStatus`，但它们没有参与该布尔量。源码中还保留一行注释掉的候选表达式，将`nRobotStatus == 0`纳入条件；该注释不能视为实际执行逻辑。

ROS `perform_command_mode_switch()`在切换到JOINT_POSITION时检查`error_state`和`motion_possible`，随后对`operation_mode_status != 0`仅警告；未检查`operation_mode`是否处于AUTOMATIC/REMOTE，也未根据完整安全/工作模式矩阵拒绝模式切换。VAL3位置控制子程序再次只检查`bMotionPossible`、命令有效性和命令类型，然后调用`$movejSync`。因此应用层的显式条件没有形成“处于允许的远程自动模式且状态适合运动”的完整、可追踪授权判定。

这不证明CS9安全控制器会接受任何不允许的运动；控制器/驱动/安全系统可能仍有独立互锁，且movejSync在某些暂停状态可能锁定命令。静态结论仅限于该公开应用层协议字段和ROS门禁未完整表达/执行模式授权契约，必须通过目标控制器手册与受控实验确认。

### 4. movejSync状态2被观察但错误处置被注释

`updateJointPositionControl.pgx`注释定义`$movejSyncState()==2`为movejSync运行中，但因运动被停止（例如eStop、moveHold、stopMove）而锁定命令。当前代码检测到状态2的分支只保留被注释掉的日志和`x_bError=true`赋值，实际不将状态2标记为错误。于是ROS/VAL3上层可能仍看到控制模式为JOINT_POSITION，而底层同步运动命令处于锁定状态；是否为预期的可恢复Hold行为，必须由目标VAL3手册和动态恢复测试定义，不能将该状态当成“运动许可正常”或“命令已执行”。

### 5. 安全状态4与wait_for_ack派生字段

`updateState.pgx`注释列出安全状态4为“Waiting restart from WMS”，但`bWaitAck`只在安全状态等于1（Waiting safety Restart）时置true。ROS硬件接口的`wait_for_ack`也只在`SafetyStatus::WAIT_FOR_RESTART`时置true，不包含`WAIT_FOR_WMS`。原始`safety_status`仍会透传，因此并非状态完全丢失；但下游若只订阅通用名称`wait_for_ack`，将无法从该字段获知WMS重启等待状态。需澄清该接口字段语义是“等待安全重启”还是“等待任意人工/WMS确认”。

### 6. 新增验收任务

新增SERVO-760：

| 子项 | 验收对象 | 状态 |
|---|---|---|
| Q1 | 对照目标VAL3 runtime手册验证workingMode()返回值及0-4全部模式语义 | 未执行 |
| Q2 | 对VAL3发送端、ROS接收端建立单一OperationMode映射表并执行0-4逐值序列化/反序列化测试 | 未执行 |
| Q3 | 对未知/保留OperationMode值（含4及超范围值）验证ROS端拒绝、告警或安全降级行为 | 未执行 |
| Q4 | 验证自动模式status 0/1/2与ROS operation_mode_status解释、warning文本的一致性 | 未执行 |
| Q5 | 验证Manual/Test/Automatic Local/Automatic Remote各模式下prepare/perform switch是否正确拒绝或允许JOINT_POSITION | 未执行 |
| Q6 | 验证drive powered、各SafetyStatus、robot mode/status组合与motion_possible的真值矩阵 | 未执行 |
| Q7 | 在Hold、moveHold、急停、STOP后分别注入位置命令，记录movejSyncState、ROS control_state及恢复条件 | 未执行 |
| Q8 | 验证movejSyncState==2时继续发送更新命令是否缓存、丢弃、恢复执行或需要显式重启 | 未执行 |
| Q9 | 验证SafetyStatus WAIT_FOR_RESTART与WAIT_FOR_WMS时wait_for_ack及原始safety_status下游表现 | 未执行 |
| Q10 | 核对目标现场CS9控制器、安全配置、VAL3版本、operation mode状态定义和远程授权策略 | 未确认，现场证据缺失 |

Q1-Q9全部未执行，Q10现场证据缺失。未执行VAL3/CS9仿真、协议映射测试、ROS集成测试、HIL、FAT/SAT或实机测试。

### 7. 结论与边界

固定公开原型中VAL3的工作模式编码0-4与ROS的OperationMode枚举0-3存在数值语义不一致；VAL3自动模式状态码依赖工作模式，但ROS端将所有非零状态统一提示为HOLD；motion_possible仅基于驱动上电和非急停，ROS模式切换只将非零operation_mode_status作为warning，未显式验证REMOTE/AUTOMATIC运行授权；movejSync状态2的错误处理代码被注释；安全状态4不会置位wait_for_ack派生字段。

这些是静态协议/门禁/遥测语义缺口，不能直接推导为现场运动越权或安全功能失效。安全控制器的独立互锁、VAL3 runtime具体语义、现场程序版本和真实模式切换行为均需受控验证。应将“操作模式映射”“模式授权策略”“底层安全功能”作为三个独立验收层，不能用ROS布尔状态代替CS9安全认证/安全回路。

未修改ICube/MoveIt/ros2_control上游，未应用PR；未执行VAL3/CS9仿真、HIL、FAT/SAT或实机验证。现场部署版本和安全配置未确认，Stäubli工程级验收未通过，`TODO-EXT-001`未授权合并。

### 固定源码链接

- https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/val3/userapp/ros2_server/updateState.pgx
- https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/val3/userapp/ros2_server/Serialization/encodeRobotStateMsg.pgx
- https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/val3/userapp/ros2_server/Control/updateJointPositionControl.pgx
- https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/include/staubli_robot_driver/types.hpp
- https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/src/communication/messages.cpp
- https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/src/staubli_hardware_interface.cpp


## §9.3.178｜VAL3状态快照与命令执行先后、ROS read/write陈旧状态传播及跨周期授权窗口

### 审查范围与固定基线

固定审查 `ICube-Robotics/staubli_driver_ros2@bd658e2d266e315d2ee35f985fb352ea88306b79`。本节把VAL3控制周期中的RobotState发布、UDP命令接收、序号延迟计算、运动命令执行和错误复位，与ROS 2 hardware_interface的read()/write()周期及RobotDriver状态新鲜度门禁合并分析。

| 文件 | Blob SHA |
|---|---|
| `val3/userapp/ros2_server/controlTask.pgx` | `00a69c4d13879116fce744ceb1611ecd05d65edf` |
| `val3/userapp/ros2_server/updateState.pgx` | `94b2bda039c05bed15c5bbc8a5afd03e9ec3dccf` |
| `val3/userapp/ros2_server/Control/updateJointPositionControl.pgx` | `28e2f1d6a3482a126b16474c957a608262c32218` |
| `src/robot_driver.cpp` | `ede48a314856a455df9d8434f354aaf9fbc47bff` |
| `src/staubli_hardware_interface.cpp` | `4ae2b8c8d91857e5e32558bfcd16e2c391b9c3d0` |

### 1. VAL3每轮先发布状态快照，再接收并执行本轮命令

`controlTask.pgx`循环顺序明确为：

1. 调用`updateState(robot_state_msg.robotState)`采集机器人状态；
2. 增加状态序号，并把当前`l_nSequenceDelay`写入状态；
3. 将`l_bError`和`l_nCmdMode`写入`bInError`、`nControlMode`；
4. 编码并发送RobotState；
5. 才调用`readData()`接收本轮RobotCommand；
6. 解码命令、计算序号延迟、检查命令模式转换；
7. 调用位置/速度控制更新或STOP路径；
8. 处理错误、重置状态和socket，最后进入下一轮。

因此RobotState是命令处理前的周期快照，不是本轮命令处理后的执行回执。特别是`nControlMode`和`bInError`反映的是本轮命令接收/执行之前的本地变量状态；`nSequenceDelay`也是上一次循环计算出的值。主机收到某一状态序号，不能据此推断同序号周期中接收的命令已经执行、被拒绝或已停止。

### 2. 序号延迟阈值判断使用本轮之前采样的运动状态

在RobotState发送之后，VAL3才计算`l_nSequenceDelay`并判断阈值：`bInMotion=true`时延迟大于5触发STOP/ERROR；非运动时延迟大于25触发STOP/ERROR。这里的`bInMotion`来自本周期前段的`updateState()`快照；序号延迟是本轮收到命令后计算的，但要到下一轮状态发布才可能出现在`nSequenceDelay`字段。

该顺序意味着诊断状态中运动标志和序号延迟不是同一处理时点的原子快照。静态代码没有提供一个带有命令序号、状态采样时间戳、处理结果和执行结果的统一确认记录。不能仅以ROS读到的`sequence_delay`或`control_state`判断某一命令的确切执行边界。

### 3. 错误发生、STOP执行和错误遥测可能跨越不同周期

若本轮在命令处理/序号检查中置`l_bError=true`，代码会将命令模式置为错误/STOP，执行停止相关子程序与`stopMove()/resetMotion()`，随后在错误处理块清除`l_bError`、将控制模式置为0、清除命令有效标志并重置socket。因为RobotState已经在本轮开始阶段发送，本轮刚出现的错误不会反映在已发送的状态帧中；而错误处理又可能在下一帧发布前清除错误标志。

因此状态遥测可能看不到短暂的本地错误锁存，或者只看到控制模式/序号复位后的状态，具体取决于错误路径、socket reset结果及下一轮采样。此处与§9.3.174的错误遥测可见性结论相关，但本节进一步明确其与命令处理和状态快照的周期先后关系。它不证明现场错误一定丢失，也不证明停止动作没有执行。

### 4. ROS read()拒绝陈旧状态时，硬件接口没有显式使旧state_msg_失效

`RobotDriver::read_robot_state()`会验证消息有效性和`status.time_since_received < state_staleness_timeout_`；若状态陈旧则返回false，并且只在消息有效时才把`current_robot_state_`复制到输出参数。硬件接口`read()`若读失败就返回`hardware_interface::return_type::ERROR`，不会调用`update_state()`清零或标记现有`state_msg_`无效。

因此硬件接口成员`state_msg_`可能保留上一次成功读取的快照。源码中没有在read失败路径写入显式状态失效标志、更新时间戳或自动切换本地控制模式到STOP。ROS控制框架在read返回ERROR后的具体调度行为需按目标ros2_control版本和controller_manager配置验证；不能假定write一定继续，也不能假定read ERROR本身已向机器人发出STOP。

### 5. write()没有基于本次read的新鲜度或安全状态时间戳进行二次门禁

`StaubliHardwareInterface::write()`检查RobotDriver连接状态；当当前控制模式不是STOP时，检查缓存的`state_msg_.error_state`或`control_state==INVALID`，满足条件则尝试发送STOP并返回ERROR。随后构造命令并发送。

该函数没有检查state_msg_对应的接收时间、状态序号是否在本周期更新，也没有在每次位置/速度命令写入前重新检查`motion_possible`、`estop_pressed`、`safety_status`和`operation_mode`。其中`motion_possible`只在`perform_command_mode_switch()`切入JOINT_POSITION时检查，而非每次write调用持续检查。若安全/模式状态在成功read与下一次write之间变化，或read失败后旧快照仍被保留，当前硬件接口自身没有可见的基于状态年龄/序号的二次拒绝逻辑。

此结论描述接口本身缺少的显式检查，不证明controller_manager一定会在read失败后继续调用write，也不证明CS9安全控制器不会独立拒绝命令。ROS调度、网络时序和控制器安全互锁必须分层测试。

### 6. 状态新鲜度与命令周期没有共同的端到端时间基准

RobotDriver的陈旧判断依赖接收端`MessageStatus.time_since_received`和配置的`state_staleness_timeout_`；VAL3序号延迟判断依赖16位状态序号与命令序号差；ROS hardware_interface的write周期参数被写入`controller_period`，但当前审查到的write路径没有将其与最近一次状态接收年龄绑定成命令许可条件。

这三种度量分别代表接收年龄、序号差和控制器周期，不能相互替代。尤其状态序号可能重置/回绕（见§9.3.175），状态接收年龄可能因线程/调度变化而增加，ROS控制周期也可能抖动。固定源码没有构成统一的会话epoch+时间戳+命令ID+执行确认闭环。

### 7. 新增验收任务

新增SERVO-761：

| 子项 | 验收对象 | 状态 |
|---|---|---|
| R1 | 对齐VAL3状态采样、RobotState发送、命令接收、序号检查、运动调用及错误处理的逐周期时间线 | 未执行 |
| R2 | 注入命令模式切换、序号超限、编码/发送失败，核对错误首次产生、STOP调用和状态帧可见时刻 | 未执行 |
| R3 | 验证每一RobotState中的nControlMode、bInError、nSequenceDelay与对应命令序号/处理结果的关联 | 未执行 |
| R4 | 通过网络延迟/乱序/丢包验证bInMotion快照与本轮sequence delay阈值检查的时序边界 | 未执行 |
| R5 | 注入状态帧陈旧、接收线程暂停、重复帧和序号停滞，确认read()返回ERROR后的controller_manager调度行为 | 未执行 |
| R6 | 验证read失败后state_msg_缓存内容是否仍可被write路径读取，以及框架是否会在同周期调用write | 未执行 |
| R7 | 在read与write之间切换急停、SafetyStatus、motion_possible和operation_mode，验证命令是否被持续门禁拒绝 | 未执行 |
| R8 | 验证状态年龄超过阈值时是否存在独立STOP发送、失效标记、控制器停用和重新授权流程 | 未执行 |
| R9 | 记录VAL3状态序号、ROS接收时间、ROS控制周期、命令序号、VAL3处理结果及机器人运动反馈的统一追踪数据 | 未执行 |
| R10 | 核对现场ros2_control/controller_manager版本、调度配置、VAL3控制周期、UDP网络时延与安全系统响应记录 | 未确认，现场证据缺失 |

R1-R9全部未执行，R10现场证据缺失。未执行VAL3/CS9仿真、网络故障注入、ROS控制器集成测试、HIL、FAT/SAT或实机测试。

### 8. 结论与边界

固定公开原型的VAL3控制循环先发布状态快照，再处理本轮命令；序号延迟在状态发布后计算，错误可能在同一循环的后段被复位，因此状态帧不是命令处理回执，短暂错误也不保证被后续状态帧完整呈现。ROS侧RobotDriver拒绝陈旧状态时，hardware_interface::read()返回ERROR但没有显式使旧state_msg_失效；write()没有状态年龄/序号二次门禁，且运动许可条件主要在模式切换时检查，而非每个命令周期重新检查。

这些静态边界构成“状态采样—传输—read—控制器更新—write—VAL3接收—运动执行”链路中的可观测性和时序验收风险；它们不证明read ERROR后write一定继续、不证明现场命令越权，也不证明机器人安全功能失效。必须使用目标ros2_control版本验证调度行为，并在受控CS9环境对状态变化与命令写入竞态进行动态测试。

未修改ICube/MoveIt/ros2_control上游，未应用PR；未执行VAL3/CS9仿真、网络故障注入、ROS集成测试、HIL、FAT/SAT或实机验证。现场部署版本和调度配置未确认，Stäubli工程级验收未通过，`TODO-EXT-001`未授权合并。

### 固定源码链接

- https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/val3/userapp/ros2_server/controlTask.pgx
- https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/val3/userapp/ros2_server/updateState.pgx
- https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/src/robot_driver.cpp
- https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/src/staubli_hardware_interface.cpp


## §9.3.179｜ROS UDP发送成功、VAL3命令接收/执行与状态反馈确认边界

### 审查范围与固定基线

固定审查 `ICube-Robotics/staubli_driver_ros2@bd658e2d266e315d2ee35f985fb352ea88306b79`。本节检查ROS发送接口返回值语义、STOP命令构造、VAL3命令接收与缓存复用、位置同步运动刷新状态，以及速度控制原型完成度。

| 文件 | Blob SHA |
|---|---|
| `src/robot_driver.cpp` | `ede48a314856a455df9d8434f354aaf9fbc47bff` |
| `src/real_time_socket_interface.cpp` | `eda0a830cfe0118e07bc3423ad0f455bd50d610c` |
| `include/staubli_robot_driver/real_time_socket_interface.hpp` | `e4d4650f59d2eb95133f5e948431ebe2073a6667` |
| `include/staubli_robot_driver/robot_driver_helpers.hpp` | `88a0cac08d3a299b7330eaa72b1afaaeab2fe41b` |
| `src/real_time_socket_subscriber.cpp` | `e2cd8fc50b2b13d9e31b2c024e90f9da76107622` |
| `src/staubli_hardware_interface.cpp` | `4ae2b8c8d91857e5e32558bfcd16e2c391b9c3d0` |
| `val3/userapp/ros2_server/controlTask.pgx` | `00a69c4d13879116fce744ceb1611ecd05d65edf` |
| `val3/userapp/ros2_server/Control/updateJointPositionControl.pgx` | `28e2f1d6a3482a126b16474c957a608262c32218` |
| `val3/userapp/ros2_server/Control/updateJointVelocityControl.pgx` | `72f4eb0215ceeae2c3a528013ea2a79c4dc46344` |
| `val3/userapp/ros2_server/Control/stopJointPositionControl.pgx` | `bd4be41dff93258d5c08cbf9411af3d811b5f6c9` |

### 1. send_robot_command成功仅代表本地序列化及socket send成功

ROS `RobotDriver::send_robot_command()`先检查control interface ready，再调用`RealTimeSocketInterface::send_message()`。后者检查socket connected、序列化消息，然后调用`socket_->send(data_out_)`；该调用返回true后整个发送接口即返回true。

代码没有等待VAL3接收线程确认、没有等待controlTask解码确认、没有命令接受/拒绝ACK，也没有等待movejSync或机器人运动反馈来确认本命令已执行。因此`StaubliHardwareInterface::write()`返回OK只表示本地send调用返回成功，不表示机器人端已经接收、接受或执行。UDP不提供应用层可靠交付保证；即使本地send成功，也不能推导数据包到达目标应用。

### 2. STOP命令发送路径也没有完成确认

普通hardware_interface STOP写入通过`send_robot_command()`发送零参考命令。异常路径的`send_stop_all_command()`通过`prepare_robot_command_message()`构造STOP并清零数字/模拟输出；其序号来自`current_robot_state_`，之后调用同一`send_message()`。该辅助路径没有独立STOP ACK、停止完成等待或机器人静止确认。

`prepare_robot_command_message()`复制最近缓存状态的sequence number；`send_stop_all_command()`本身没有先调用`read_robot_state()`检查该状态新鲜度。其序号可能是上次有效状态的序号，而不是在发送STOP瞬间刚确认的新状态。该点与§9.3.175的序号回绕/重启边界和§9.3.178的状态快照滞后问题相互关联。

### 3. VAL3命令接收没有逐命令处理回执，旧命令缓存会被周期重用

`controlTask.pgx`每周期调用`readData()`；收到新报文才调用`decodeRobotCommandMsg()`更新`robot_command_msg`。无新报文且上一条命令仍有效时，源码进入“check staleness of previous message”分支，但该分支仍是TODO。随后只要缓存命令`bIsValid`，就根据当前状态序号与缓存命令序号计算`l_nSequenceDelay`，并在运动时大于5、静止时大于25触发错误/STOP路径。

所以原型并非完全没有陈旧保护：它有基于状态/命令序号差的阈值保护；但没有独立的命令接收墙钟时间戳、逐命令确认和明确的丢失/拒绝原因回报。无新命令时旧命令结构仍被保留，并继续参与当前周期模式解析/控制调用，直到序号阈值路径触发。阈值保护依赖周期节拍和序号同步，不能等同于经过验证的端到端接收超时。

### 4. 位置控制的movejSync状态1被识别但只保留注释告警

`updateJointPositionControl.pgx`注释定义movejSync状态：
- -2：movejSync因无效命令进入错误停止；
- -1：尚未启动；
- 0：运行正常；
- 1：上一条命令未及时刷新；
- 2：运动被停止后命令锁定。

位置控制程序在每次调用时调用`$movejSync(l_jJointPositionCmd)`，然后读取状态。状态-2会停止并置错误；状态1和状态2的日志/错误处理均被注释，实际不置错误。结合controlTask无新UDP命令时仍保留旧命令结构并继续进入控制更新路径，状态1究竟代表短暂刷新迟滞、底层保持旧目标还是触发内部保护，需要按目标VAL3 runtime动态确认。不能仅凭状态1被忽略就断言运动继续，也不能视为已获得命令确认。

### 5. STOP路径请求停止，但遥测不是停止完成确认

VAL3在命令模式为STOP或ERROR时，对上一模式执行相应停止子程序，然后调用`stopMove()`和`resetMotion()`。位置停止子程序在movejSync状态不等于-1时调用`$movejSyncEnd()`，之后返回`x_bError=false`。该返回值只表明程序路径未报告停止子程序错误，不是安全控制器或机械臂静止状态的独立确认。

同一周期随后发布的状态已经在命令接收前发出（§9.3.178），因此主机也不能把紧邻STOP发送前后收到的普通RobotState帧直接当成STOP命令执行确认。现有协议未见独立stop request ID、stop accepted、stop completed、静止判据或确认超时字段。

### 6. 位置与速度命令路径成熟度不对称

ROS硬件接口的`prepare_command_mode_switch()`拒绝JOINT_VELOCITY模式；VAL3的`updateJointVelocityControl.pgx`也明确记录速度命令尚未实现，实际执行处记录“not yet implemented”、置错误并返回。相比之下，位置控制使用`movejSyncBegin/movejSync`，有位置范围检查，但“目标距离当前位姿足够近”的检查仍为TODO。RobotDriver对位置/速度范围校验也保留TODO注释。

因此当前固定原型不应描述为具备已完成的ROS关节速度控制功能；位置控制也不能据此视为已完成所有目标轨迹、刷新超时和安全限位验证。

### 7. 新增验收任务

新增SERVO-762：

| 子项 | 验收对象 | 状态 |
|---|---|---|
| S1 | 在ROS send成功后分别注入UDP丢包、VAL3未运行、VAL3拒绝解码，确认write返回值与机器人端结果的差异 | 未执行 |
| S2 | 为每条命令记录ROS发送时间、序号、VAL3接收/解码时间、接受/拒绝原因及运动反馈 | 未执行 |
| S3 | 验证STOP普通命令与send_stop_all_command异常路径的序号来源、缓存新鲜度和IO清零行为 | 未执行 |
| S4 | 在STOP发送后注入延迟、丢包、乱序和重复包，确认VAL3停止动作及停止完成判据 | 未执行 |
| S5 | 验证无新UDP报文时旧位置命令的复用时长、movejSync状态1、序号阈值与实际运动反馈 | 未执行 |
| S6 | 验证movejSync状态-2/-1/0/1/2的真实语义、停止/恢复行为和遥测关联 | 未执行 |
| S7 | 验证位置控制STOP、movejSyncEnd、stopMove、resetMotion与机器人静止反馈之间的时序 | 未执行 |
| S8 | 验证VAL3 velocity路径在当前版本的不可用状态及ROS模式切换拒绝是否一致 | 未执行 |
| S9 | 验证位置范围、目标距离、命令刷新周期、控制器限速/限加速度约束与异常命令处理 | 未执行 |
| S10 | 核对目标现场应用版本、VAL3 movejSync文档、UDP网络测量、命令日志及安全停止验收记录 | 未确认，现场证据缺失 |

S1-S9全部未执行，S10现场证据缺失。未执行VAL3/CS9仿真、UDP故障注入、命令回执测试、ROS集成测试、HIL、FAT/SAT或实机测试。

### 8. 结论与边界

固定公开原型中ROS发送接口的成功条件止于本地序列化和socket send成功，没有端到端命令接收/接受/执行ACK；STOP路径同样没有停止完成确认，且异常STOP辅助路径使用最近缓存状态序号。VAL3无新命令时保留上一条有效命令结构，staleness分支仍为TODO，但存在基于序号差的阈值保护；位置movejSync状态1（刷新超时）当前仅有被注释的处理，状态-2才触发错误停止。速度控制路径在ROS和VAL3两侧均未实现/被拒绝。

这些发现界定的是公开原型的通信与命令确认能力，不证明现场UDP丢包、不证明STOP必然未送达、不证明机器人忽略停止请求，也不证明movejSync状态1时持续运动。目标CS9的VAL3运行时语义、UDP网络行为、运动停止反馈和现场部署版本仍须受控验证。

未修改ICube/MoveIt/ros2_control上游，未应用PR；未执行VAL3/CS9仿真、UDP故障注入、ROS集成测试、HIL、FAT/SAT或实机验证。现场部署版本和网络测量未确认，Stäubli工程级验收未通过，`TODO-EXT-001`未授权合并。

### 固定源码链接

- https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/src/robot_driver.cpp
- https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/src/real_time_socket_interface.cpp
- https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/include/staubli_robot_driver/robot_driver_helpers.hpp
- https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/src/real_time_socket_subscriber.cpp
- https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/src/staubli_hardware_interface.cpp
- https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/val3/userapp/ros2_server/controlTask.pgx
- https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/val3/userapp/ros2_server/Control/updateJointPositionControl.pgx
- https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/val3/userapp/ros2_server/Control/updateJointVelocityControl.pgx
- https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/val3/userapp/ros2_server/Control/stopJointPositionControl.pgx


## §9.3.180｜关节位置限位一致性、异常数值过滤与命令数组边界

### 审查范围与固定基线

固定审查 `ICube-Robotics/staubli_driver_ros2@bd658e2d266e315d2ee35f985fb352ea88306b79`。本节检查ROS硬件接口命令数值校验、固定六轴协议数组边界、TX2-60L模型限位配置、R2C Xacro接口生成，以及VAL3位置控制的运行时关节范围检查和目标距离检查。

| 文件 | Blob SHA |
|---|---|
| `staubli_hardware_interface.cpp` | `4ae2b8c8d91857e5e32558bfcd16e2c391b9c3d0` |
| `robot_driver.cpp` | `ede48a314856a455df9d8434f354aaf9fbc47bff` |
| `robot_driver_helpers.hpp` | `88a0cac08d3a299b7330eaa72b1afaaeab2fe41b` |
| `communication/messages.hpp` | `77f21d8edcb12a39fc6732c2e146586b7fc346fe` |
| `updateJointPositionControl.pgx` | `28e2f1d6a3482a126b16474c957a608262c32218` |
| `staubli_helpers.xacro` | `3a8431c4b4d4f403984ad8719c0d048de7a97bf6` |
| `r2c/staubli.r2c.xacro` | `0013b6ea5b681e5333799f65867e7de497b54127` |
| `tx2_60l/joint_limits.yaml` | `0f5cb789dac614747bb563867ded5cd1291fec2a` |
| `tx2_60l_med/joint_limits.yaml` | `0f5cb789dac614747bb563867ded5cd1291fec2a` |
| `staubli_moveit_config/config/joint_limits.yaml` | `6a2fb4c585c5caa5299a415c2e1ed1b22b8211e6` |

### 1. ROS write路径只拒绝NaN，没有拒绝全部非有限数值

`StaubliHardwareInterface::write()`把position/velocity command interface中的弧度值乘以rad2deg转换后写入固定六元素`RobotCommandMessage::command_reference`。随后执行的异常数值检查使用`std::isnan()`，只拒绝NaN；源码没有使用`std::isfinite()`，因此正/负Inf不被该检查识别。位置/速度命令也没有在该路径做本地min/max、增量或限速钳制；`RobotDriver::send_robot_command()`仍留有“add checks for position/velocity limits here?” TODO。

该结论是代码检查范围的静态事实：Inf可通过当前NaN专用条件，并不证明VAL3一定接受Inf或现场已发生异常运动。VAL3的`isInRange()`对Inf/NaN的实际处理及序列化/运行时行为仍需目标VAL3版本验证。

### 2. 六轴协议数组与可配置num_joints_之间存在条件性越界风险

`communication/messages.hpp`明确将关节位置、速度、力矩和命令参考定义为固定`std::array<double, 6>`，并注释该协议面向六轴Stäubli机器人。HardwareInterface::write()在复制位置/速度命令时使用`i < num_joints_ && i < 6`，但随后NaN检查循环只使用`i < num_joints_`并直接访问`cmd_msg.command_reference[i]`。on_init()只拒绝零关节，没有在此处强制`num_joints_ == 6`。因此若配置关节数大于6，静态代码路径会越过固定数组边界；若少于6，未写入的协议槽位如何初始化及VAL3对剩余轴的解释也需要确认。

仓库的消息协议和TX2-60L模型均面向六轴，因此这属于配置异常条件下的代码边界风险，不应描述为正常六轴配置必然触发。应在初始化时明确拒绝非六轴配置，或统一按协议容量做安全边界检查。

### 3. 位置限位分布在多层配置，未发现统一一致性门禁

TX2-60L模型配置给出六轴位置范围：J1 ±180°、J2 ±127°、J3 ±150°、J4 ±270°、J5 ±120°、J6 ±270°；并给出模型速度上限J1–J5 300°/s、J6 500°/s，以及加速度上限J1–J5 1000°/s²、J6 3000°/s²。TX2-60L MED配置在本固定提交中与TX2-60L文件内容相同，但这不证明两个实际产品的机械/安全限位可互换。

独立的MoveIt `joint_limits.yaml`仅列出速度1.5 rad/s（J1–J5）、J6 2.0 rad/s及加速度5 rad/s²，未在该文件重复列出位置边界。该值比模型YAML中的名义速度/加速度上限更保守；两份配置的用途、覆盖关系和生效顺序不能混为一谈。当前审查未发现自动比较模型YAML、URDF、MoveIt限值、控制器限幅与CS9实际轴参数的一致性检查。

`staubli_helpers.xacro`将模型配置的min/max position和max velocity写入URDF joint limit；但R2C ros2_control关节宏对position/velocity command interface没有生成对应min/max参数，真实HardwareInterface::write()也没有执行相应数值夹紧。R2C宏从模型限值中取出max_acceleration作为acceleration command interface的max/min参数；该接口被注释为供joint limiter使用，但write()并未把该加速度命令写入RobotCommand。由此不能仅凭URDF/YAML中存在限值，就宣称HardwareInterface发送前已经应用这些限值；实际JointLimiter插件/控制器配置及生效链仍需独立核验。

### 4. VAL3 isInRange检查与目标距离检查的能力边界

`updateJointPositionControl.pgx`将六个`nMotionCmdData`元素复制到`jointRx`目标后调用`isInRange(l_jJointPositionCmd)`；返回false时调用位置停止子程序、置错误并返回。该程序未在仓库内提供`isInRange`实现，因此本轮只能确认调用点存在，不能据此断言其精确边界比较方式、限位来源、单位转换、NaN/Inf行为或与TX2-60L YAML一致。

紧接范围检查之后，源码明确将“Check target is close enough to current position”留为TODO。故即使目标通过当前VAL3范围函数，也不能从源码证明单周期目标跳变量、轨迹连续性、速度/加速度/jerk、路径可达性或制动距离已被独立限制。ROS Driver本身同样没有位置/速度范围检查。

### 5. 本轮静态结论

1. ROS write()的关节命令过滤是NaN专用检查，不是完整有限数检查；Inf可通过该条件。
2. 命令协议固定六元素，而HardwareInterface允许任意非零num_joints_；NaN检查循环没有与六元素数组容量取最小值，配置超过六轴时存在条件性越界访问风险。
3. 模型URDF限位、MoveIt速度/加速度配置、R2C ros2_control接口和VAL3 isInRange分属不同层；当前固定源码没有证明它们由统一来源生成并做一致性校验。
4. VAL3位置控制有运行时isInRange调用，但其实现和限位来源未在仓库中给出；目标距离检查明确为TODO。
5. 本轮未确认目标现场具体机器人型号、实际关节软/硬限位、控制器参数、限幅器插件配置或安全额定限位。软件限位不能替代CS9安全功能或机械硬限位。

### 6. 新增验收任务

新增SERVO-763：

| 子项 | 验收对象 | 状态 |
|---|---|---|
| T1 | 对六轴position/velocity命令分别注入NaN、+Inf、-Inf、极大有限值，验证write门禁、STOP请求和VAL3解码结果 | 未执行 |
| T2 | 初始化0、1、6、7轴及异常joint配置，验证协议固定数组边界、初始化拒绝策略和ASan结果 | 未执行 |
| T3 | 验证ROS write()位置/速度命令与模型min/max/velocity/acceleration限值的实际执行链 | 未执行 |
| T4 | 展开TX2-60L与TX2-60L MED Xacro/URDF，逐轴比对模型YAML、URDF、MoveIt与控制器限值 | 未执行 |
| T5 | 确认R2C ros2_control实际加载的JointLimiter插件、参数来源、接口声明和运行时限幅效果 | 未执行 |
| T6 | 取得目标CS9/VAL3版本对isInRange的正式定义，验证边界相等、越界、NaN/Inf及轴配置差异 | 未执行 |
| T7 | 对位置目标设置大步长、方向反转和近限位跳变，测量movejSync目标变化、速度/加速度/jerk与停止距离 | 未执行 |
| T8 | 验证VAL3位置范围、ROS MoveIt规划限值、控制器参数与真实机器人轴限位的一致性及配置漂移检测 | 未执行 |
| T9 | 对数字/模拟GPIO输出注入NaN/Inf/越界值，验证输出编码、范围检查和故障处理 | 未执行 |
| T10 | 核对现场机器人型号/序列配置、CS9轴参数、VAL3版本、限位/安全参数、JointLimiter配置及FAT/SAT记录 | 未确认，现场证据缺失 |

T1-T9全部未执行，T10现场证据缺失。未执行ROS构建/单测、ASan、Xacro展开、JointLimiter集成测试、VAL3编译/仿真、CS9限位/运动实测、HIL、FAT/SAT或实机验证。

### 7. 结论与边界

固定公开原型的ROS命令入口仅拒绝NaN而非所有非有限数值；固定六元素协议数组与未限制为六轴的num_joints_形成条件性边界风险；模型URDF、MoveIt与硬件接口限值分散在不同配置层；VAL3位置控制调用isInRange但未提供实现，且目标距离检查仍为TODO。该证据支持开展有限数值、配置一致性和目标跳变验证，不证明Inf已进入现场、不证明越限命令被CS9接受，也不证明现场限位失效。

未修改ICube/MoveIt/ros2_control上游，未应用PR；未执行任何动态、HIL、FAT/SAT或实机限位验证。现场机器人型号、软件版本、实际轴参数及安全配置未确认，Stäubli工程级验收未通过，`TODO-EXT-001`未授权合并。

### 固定源码链接

- https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/src/staubli_hardware_interface.cpp
- https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/src/robot_driver.cpp
- https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/include/staubli_robot_driver/communication/messages.hpp
- https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/val3/userapp/ros2_server/Control/updateJointPositionControl.pgx
- https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_description/urdf/include/staubli_helpers.xacro
- https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_description/r2c/staubli.r2c.xacro
- https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_description/config/tx2_60l/joint_limits.yaml
- https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_description/config/tx2_60l_med/joint_limits.yaml
- https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_moveit_config/config/joint_limits.yaml


## §9.3.181｜ROS—VAL3命令报文浮点精度、解码长度校验与错误传播

### 审查范围与固定基线

固定审查 `ICube-Robotics/staubli_driver_ros2@bd658e2d266e315d2ee35f985fb352ea88306b79`。本节沿ROS HardwareInterface → RobotCommandMessage → 二进制序列化 → UDP → VAL3 decodeRobotCommandMsg → controlTask → 位置控制/GPIO的命令路径，检查浮点精度转换、非有限值校验、负载长度和解码错误传播。

| 文件 | Blob SHA |
|---|---|
| `staubli_hardware_interface.cpp` | `4ae2b8c8d91857e5e32558bfcd16e2c391b9c3d0` |
| `robot_driver.cpp` | `ede48a314856a455df9d8434f354aaf9fbc47bff` |
| `communication/messages.cpp` | `86c4d7b6eac0e2455214fc78ebd6864ae5b0b0c6` |
| `communication/serialization.hpp` | `c226d4053693a5466b8bf1aef09049d34a3321d1` |
| `communication/messages.hpp` | `77f21d8edcb12a39fc6732c2e146586b7fc346fe` |
| `test_message_serialization.cpp` | `a7a84bc01456f3a8bb20993ebdc5d487defa5632` |
| `decodeRobotCommandMsg.pgx` | `612f5ce9fff12c0bd6c4e90e5685ea1d4b59bcdd` |
| `decodeHeader.pgx` | `41017a697f0ada9a19bc8bc2296fdab439856356` |
| `initRobotCommandMsg.pgx` | `ab254d2b65caadbacf7fa171c51994ca24f3f450` |
| `controlTask.pgx` | `00a69c4d13879116fce744ceb1611ecd05d65edf` |
| `updateJointPositionControl.pgx` | `28e2f1d6a3482a126b16474c957a608262c32218` |

### 1. C++ double命令在协议层统一收窄为IEEE单精度float32

`serialization.hpp`中的`serialize_type(const double&)`先将double静态转换为float，再按4字节写入；反序列化则先读float再扩展为double。RobotCommand报文的固定长度为55字节：8字节header、4字节controller period、1字节命令类型、6×4字节关节命令、2字节数字输出掩码和4×4字节模拟输出。VAL3解码程序使用`fromBinary(...,"4.0l",...)`读取同样的float32 little-endian字段，字段宽度在当前两端实现中一致。

因此ROS侧double接口值在传输前会发生float32精度收窄；大幅值会有量化误差，超过float32可表示范围的有限double在转换时可能变成Inf。这里是协议精度和数值域边界，不代表常规机器人关节工作范围内的精度必然不足。实际可接受误差预算应按目标机器人、控制周期和运动性能要求验证。

### 2. 当前NaN门禁发生在float32转换之前，且没有覆盖Inf/转换溢出

HardwareInterface::write()在调用send_robot_command()前对joint command_reference做`std::isnan()`检查。该检查不拒绝+Inf/-Inf；有限double在后续`static_cast<float>`时若超出float32范围也可能转成Inf，而门禁发生在此转换之前，因此不会捕获这种转换后产生的非有限值。RobotDriver::send_robot_command()本身仍只有位置/速度限值TODO，没有补充有限值检查。

同一序列化函数也把controller_period和四路analog_outputs从double收窄为float32；本路径未见针对这些字段的统一`std::isfinite()`校验。HardwareInterface::write()对analog_outputs直接复制，没有像joint command_reference那样做NaN检查。VAL3解码程序将四路模拟输出写入命令结构，但controlTask中的数字/模拟输出执行段仍是TODO；所以本轮只能确认解码数据路径缺少明确有限值门禁，不能声称这些模拟值已被输出到现场IO。

### 3. VAL3解码器先检查报文总长度关系，但没有在固定字段读取前验证精确命令payload长度

`initRobotCommandMsg.pgx`设置固定header size和payload size=47，并将序列化数组调整为header+payload。接收解码器先检查`size(nSerializedData) == header.nHeaderSize + header.nPayloadSize`，随后调用`decodeHeader`；header解码检查magic number=43981及protocol version=1。命令解码随后检查message type=2，并按固定偏移依次读取controller period、命令类型、六个float32关节值、数字输出掩码及四个float32模拟输出。

但`decodeRobotCommandMsg.pgx`没有在这些固定偏移读取之前明确断言`header.nHeaderSize == 8`且`header.nPayloadSize == 47`。它只在所有字段读取之后检查最终偏移是否等于数组长度。若输入负载长度与预期不一致，源码没有在固定字段读取前提供独立的精确负载长度门禁；VAL3的`fromBinary`在短缓冲区情况下具体如何报错/保护，仍需目标VAL3 runtime验证，不能仅凭静态源码断言会发生越界访问。多余负载则会在最终offset检查处被标记为解码错误。

### 4. 解码成功后没有对float32字段做isFinite校验，bIsValid会被置真

在完成字段读取且最终offset匹配后，VAL3解码器直接设置`bIsValid=true`并清除`x_bError`；没有对六个`nMotionCmdData`、controller period或四个analog output逐项执行NaN/Inf/有限范围检查。随后controlTask检查命令类型数值范围（小于0或大于4则报错），但这不是浮点命令数据检查。位置控制程序再调用`isInRange()`检查关节位置范围，但其实现和NaN/Inf语义不在该仓库内；速度控制当前未实现。由此只能确认解码成功标记本身不等于浮点数值安全验证完成。

### 5. 解码错误向STOP/ERROR传播的静态路径

`decodeRobotCommandMsg.pgx`在header/message type错误时将命令模式设置为STOP并返回；在最终offset不匹配时还将`bIsValid=false`、命令模式设置为STOP并返回。controlTask在收到新命令后检查解码错误，置`l_bError=true`并设置STOP模式；后续命令模式提取会把错误转为ERROR mode，进入错误处理，调用停止程序、`stopMove()`、`resetMotion()`，将命令类型置为0、清除有效标志并重置control socket。

该错误传播链对明确的解码错误有静态处理分支，但不能由源码静态分析证明停止指令的物理完成时刻、机械臂停止距离或网络异常时的最终安全状态；这些仍需目标CS9/VAL3动态验证。若解码器将包含NaN/Inf的float32报文视为字段格式合法，则其不会因数值非有限而走上述解码错误分支，后续安全效果依赖位置范围函数及控制器运行时行为。

### 6. 现有序列化单测覆盖有限

`test_message_serialization.cpp`中的RobotCommandMessage序列化测试使用普通有限数值（关节值1.1至6.6、周期0.008、模拟输出5.5至8.8），验证往返误差；没有覆盖NaN、+Inf、-Inf、float32最大/最小有限边界、有限double收窄为Inf、次正规数/精度损失、异常payload长度或跨语言VAL3解码一致性。该测试可证明常规样例的序列化往返，不构成异常浮点值或协议模糊输入的验证。

### 7. 本轮静态结论

1. ROS double字段在协议序列化时收窄为float32，VAL3端按float32解码；精度预算和极端值行为需要单独验证。
2. ROS joint NaN检查发生在float32收窄前，只检查NaN，不检查Inf；double转float产生的Inf也不在该门禁覆盖范围内。controller_period与analog_outputs同样缺少统一有限值检查。
3. VAL3命令解码器验证总长度与header/payload长度关系、magic、protocol和message type，并在末尾检查最终offset；但未在固定字段读取前验证精确payload=47及固定header=8。
4. 解码成功后直接将命令标记为valid，没有逐字段NaN/Inf检查；命令类型数值范围检查不替代浮点数据检查。
5. 明确解码错误会在controlTask中转入STOP/ERROR处理并重置socket；不能由此推断物理停止完成或非有限值一定触发解码错误。
6. 现有C++单测仅覆盖正常有限值往返，没有异常浮点、收窄溢出、错误长度或C++/VAL3跨语言协议测试。

### 8. 新增验收任务

新增SERVO-764：

| 子项 | 验收对象 | 状态 |
|---|---|---|
| U1 | 对关节命令注入NaN、±Inf、FLT_MAX附近值及超过FLT_MAX的有限double，记录write门禁、float32编码字节和VAL3解码结果 | 未执行 |
| U2 | 对controller_period及四路analog_outputs注入NaN、±Inf、float32溢出值，验证编码/解码及控制任务处置 | 未执行 |
| U3 | 测量float64→float32→VAL3 num的绝对/相对误差、次正规数和边界舍入，建立型号/工况相关误差预算 | 未执行 |
| U4 | 构造payload长度0、1、46、47、48及header长度异常报文，验证VAL3 fromBinary边界行为、错误标志和任务恢复 | 未执行 |
| U5 | 构造magic、protocol、message type、sequence、payload_size不一致报文，验证解码器错误传播和socket重置 | 未执行 |
| U6 | 为C++序列化新增NaN/Inf/float32溢出/精度边界单测，并增加跨语言黄金报文测试 | 未执行 |
| U7 | 对包含NaN/Inf但字段长度合法的float32报文验证bIsValid、isInRange及位置控制错误路径 | 未执行 |
| U8 | 在VAL3仿真及受控HIL环境中验证解码错误后的停止顺序、错误锁存、socket重连和重新授权 | 未执行 |
| U9 | 确认四路模拟输出在目标现场的执行路径是否启用；若启用，验证范围/有限值门禁与失效安全状态 | 未确认，现场路径证据缺失 |
| U10 | 获取目标机器人型号、CS9/VAL3版本、协议部署版本、现场报文抓包及FAT/SAT数值异常测试记录 | 未确认，现场证据缺失 |

U1-U8全部未执行；U9现场模拟输出执行路径未确认；U10现场证据缺失。未执行ROS构建/单测、VAL3编译/仿真、协议模糊测试、HIL、CS9实机或FAT/SAT验证。

### 9. 结论与边界

本轮固定公开源码静态审查确认：ROS double命令经float32传输；当前NaN门禁无法覆盖Inf及double收窄溢出；VAL3解码器没有对成功解码的浮点字段做有限值检查，也没有在固定字段读取前单独校验精确payload长度；明确解码错误存在STOP/ERROR与socket reset路径。上述内容是代码路径与测试覆盖的静态结论，不证明现场已发送非有限数值、不证明VAL3对异常报文发生越界访问，也不证明物理停止功能失效。

未修改ICube/MoveIt/ros2_control上游，未应用PR；未执行动态、HIL、FAT/SAT或实机验证。现场机器人型号、CS9/VAL3版本、部署协议版本和IO执行路径未确认，Stäubli工程级验收未通过，`TODO-EXT-001`未授权合并。

### 固定源码链接

- https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/include/staubli_robot_driver/communication/serialization.hpp
- https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/src/communication/messages.cpp
- https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/src/staubli_hardware_interface.cpp
- https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/src/robot_driver.cpp
- https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/val3/userapp/ros2_server/Serialization/decodeRobotCommandMsg.pgx
- https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/val3/userapp/ros2_server/Serialization/decodeHeader.pgx
- https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/val3/userapp/ros2_server/Serialization/initRobotCommandMsg.pgx
- https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/val3/userapp/ros2_server/controlTask.pgx
- https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/test/unit_tests/communication/test_message_serialization.cpp


## §9.3.182｜VAL3 UDP接收批处理、旧命令缓存、序号陈旧判定与错误恢复边界

### 审查范围与固定基线

固定审查 `ICube-Robotics/staubli_driver_ros2@bd658e2d266e315d2ee35f985fb352ea88306b79`。本节沿VAL3 `controlTask` → `readData` → `readDataOnce` → `sioGet` → `decodeRobotCommandMsg`，以及 `computeSequenceDelay`、`resetControlSocket` 路径，检查单周期接收次数、报文覆盖、无数据/错误返回、旧命令有效标志和错误恢复行为。

| 文件 | Blob SHA |
|---|---|
| `controlTask.pgx` | `00a69c4d13879116fce744ceb1611ecd05d65edf` |
| `Comm/readData.pgx` | `bf2e0f3d26e66724b9f656261e29fe573bd5f3b0` |
| `Comm/readDataOnce.pgx` | `652aa04548c814febab3c8c3fc807093261efd97` |
| `Comm/resetControlSocket.pgx` | `25d414065b4567c5634ef8890cc8cafd6f7e9b3e` |
| `Comm/computeSequenceDelay.pgx` | `e96e5b378bc263255ee4f28720306ee911b8a5c1` |
| `Comm/getNextSequenceNumber.pgx` | `8bdda02a8887968b1b86e42be733f553b1e36b19` |
| `Serialization/decodeHeader.pgx` | `41017a697f0ada9a19bc8bc2296fdab439856356` |
| `Serialization/decodeRobotCommandMsg.pgx` | `612f5ce9fff12c0bd6c4e90e5685ea1d4b59bcdd` |
| `ros2_server.pjx` | `b58dbbf1daf778da64e4ff9551d890ee9ec8514b` |

项目元数据标记VAL3版本字符串为 `s8.20.2Cs9_BS4270`；它只是该公开工程文件中的版本元数据，不证明目标现场实际运行此版本。

### 1. 每个控制周期最多尝试读取两个UDP报文，两个完整报文时缓冲区保留后一个

`readData()`将最大尝试次数固定为2，并在每次循环中把同一个 `x_nData` 数组传给 `readDataOnce()`。`readDataOnce()`通过 `sioGet()` 将数据写入该数组；返回字节数等于数组长度时标记新数据，返回值大于0但不等于长度时标记通信错误。

如果一次控制周期内两次调用都取得完整报文，第二次读取会覆盖同一数组中的第一次报文；循环结束后只向调用方返回一个 `x_bNewData=true`，后续只解码当前缓冲区中的最后一份报文。若第一次成功、第二次没有新数据，则保留第一次报文并退出。该实现表现为每周期最多排空两个报文、只处理最后读到的一个，不是逐条排队处理所有到达报文。

这意味着突发到达的中间命令可能被跳过，最新报文的序号差会反映被跳过的序号数量。是否会造成控制跟踪误差或触发停止取决于实际到达节奏、周期调度和序号门限，必须通过受控UDP突发测试测量，不能仅凭静态代码推断运动结果。

### 2. 无新报文不会自动清除上一条有效命令，陈旧分支仍为TODO

当 `readDataOnce()`未报告新数据且未报告错误时，`readData()`返回 `x_bNewData=false`。controlTask在该分支仅保留注释“check staleness of previous message”和TODO，没有清除 `robot_command_msg.robotCommand.bIsValid`，也没有更新命令缓存的接收时间戳。

因此无新报文时，旧命令结构继续保持有效；本周期后续控制路径仍会依据缓存命令类型调用相应控制程序。控制任务另有序号延迟检测：每周期本地状态序号递增，`computeSequenceDelay()`计算本地已发送序号与缓存命令序号的差；运动时差值大于5、静止时大于25会置错误并进入STOP/ERROR处理。此保护是序号差门限，不是墙钟时间戳超时，也不等价于在第一个缺包周期立即使命令失效。

### 3. 返回值为0或负数时，readDataOnce没有显式错误分支

`readDataOnce()`仅处理“返回字节数等于数组长度”和“返回值大于0但长度不匹配”两种情况。返回0或负数时，局部 `x_bNewData` 与 `x_bError`保持false，调用方将其视为本次没有新数据，而不是明确通信错误。

源码没有在此处区分“非阻塞套接字暂时无数据”与“底层API返回负数所代表的其他状态”。该返回值的精确含义取决于目标VAL3/SIO API版本；本轮不把负数解释为已证实的系统错误或丢包，只将其标记为需要查阅目标版本接口定义并动态注入验证的边界。

### 4. 短报文触发错误路径，错误处理清除命令有效标志并清空接收缓冲区

当 `sioGet()`返回大于0但小于预期数组长度时，`readDataOnce()`设置错误标志；controlTask收到 `l_bRxError`后置 `l_bError=true`。本周期后续命令模式提取优先将错误转为ERROR模式，执行STOP/停止处理。错误处理段把命令类型设为0、清除 `bIsValid`、清零序号状态并调用 `resetControlSocket()`。

这里需要精确描述“reset”的实际动作：`resetControlSocket()`只设置SIO timeout与endOfString参数并调用 `clearBuffer()`；没有关闭/重新创建UDP socket、重新绑定端口、重新建立对端会话或执行应用层重新授权握手。因此此前审计中“socket reset”应理解为接收缓冲区/套接字参数清理，不应理解为网络连接重建。

### 5. 解码错误不会在同周期继续执行旧运动命令，但恢复握手与错误锁存仍有限

新报文解码失败时，controlTask设置 `l_bError`；随后命令模式提取优先进入ERROR模式，不会按旧缓存命令类型继续走正常位置控制分支。错误处理阶段清除有效标志并清理接收缓冲区。短报文接收错误也进入同类错误处理。

但控制任务在错误处理时清除 `l_bError`，复位序号/接收错误标志和 `l_bControlActive`，然后仅清空SIO缓冲区；代码另留有“重新接受命令前增加延迟”的TODO，没有独立的错误确认、重新授权握手或新会话nonce。下一次完整报文到达后即可再次被当作新命令处理的具体时序及授权安全性，需要目标运行时验证。这里不等于证明旧报文一定会重放：清空缓冲区是否覆盖所有底层队列状态，以及重置后新旧UDP数据报的到达关系，需要动态测试。

### 6. 序号回绕与延迟计算的静态边界

`getNextSequenceNumber()`按16位序号范围0…65535递增回绕；`computeSequenceDelay()`先计算本地序号减接收序号，只有差值小于-60000时才加65536处理回绕，其余负值由controlTask视为异常并置错误。序号差可识别部分跳号、乱序或过期情况，但不能区分相同序号的重放、控制端重启后重新从初始序号开始、跨会话旧报文与合法新会话报文。报文头中没有在本路径被用于认证的会话代号或随机挑战值。

本轮仅确认源码算法与字段路径，不据此声称现场存在重放或会话混淆；控制端重启、序号回绕边界和旧数据报残留必须在隔离环境中验证。

### 7. 本轮静态结论

1. 每周期最多调用两次 `sioGet()`；若两次均取得完整数据，第二份报文覆盖第一份，只解码最后一份。
2. 没有新数据时，旧命令 `bIsValid`不会被readData路径清除；陈旧检查TODO仍存在，实际门禁依赖序号差阈值，而不是墙钟超时。
3. `sioGet()`返回0或负数时，当前代码均不置通信错误；负数语义未由本仓库定义，需查目标VAL3 API并验证。
4. 短报文/读取错误进入STOP/ERROR清理路径，随后清除命令有效标志和SIO接收缓冲区。
5. `resetControlSocket()`不是关闭重建socket或重新授权握手，只修改SIO参数并清空缓冲区；重新接受命令前等待/确认逻辑仍为TODO。
6. 16位序号差门限不能替代会话标识、报文认证或防重放机制；当前静态证据不证明现场存在重放攻击或跨会话命令执行。

### 8. 新增验收任务

新增SERVO-765：

| 子项 | 验收对象 | 状态 |
|---|---|---|
| V1 | 在单周期注入0、1、2、3、10个完整UDP报文，记录sioGet调用次数、最终解码序号及被覆盖报文 | 未执行 |
| V2 | 在第一/第二次读取分别注入完整报文、无数据、短报文，验证readData输出标志及controlTask后续模式 | 未执行 |
| V3 | 对目标VAL3版本的sioGet返回0、负值、短读、完整读和底层socket异常取得正式语义并实测 | 未执行 |
| V4 | 在运动与静止状态逐周期丢包，测量旧命令保持有效周期、序号差增长、STOP触发点和实际停止距离 | 未执行 |
| V5 | 注入乱序、重复、跳号、延迟到达、16位回绕和控制端重启序号复位，验证误判/漏判边界 | 未执行 |
| V6 | 在错误清理前后注入旧数据报与新数据报，验证clearBuffer覆盖范围、接收队列残留和旧命令重放可能性 | 未执行 |
| V7 | 验证错误清理后新命令是否需要显式STOP/授权状态转换，检查是否存在会话nonce/重新授权门禁 | 未执行 |
| V8 | 对短报文、解码错误、socket读取错误连续发生及resetControlSocket失败注入，验证错误锁存、恢复循环和状态遥测 | 未执行 |
| V9 | 在目标VAL3/SIO版本中验证timeout=-1的实际非阻塞语义、sioGet最大数据报长度和clearBuffer行为 | 未执行 |
| V10 | 获取目标现场机器人、CS9/VAL3版本、UDP抓包、控制端重启/网络抖动记录及FAT/SAT通信恢复证据 | 未确认，现场证据缺失 |

V1-V9全部未执行；V10现场证据缺失。未执行VAL3编译/仿真、UDP故障注入、ROS集成、HIL、CS9实机、FAT/SAT或现场抓包验证。

### 9. 结论与边界

固定公开源码显示，VAL3接收逻辑每周期最多读取两个数据报，连续两个完整报文时只保留最后一个；没有新数据时旧命令有效标志继续保留，直到序号延迟阈值触发错误或其他错误路径使其失效。短报文会进入STOP/ERROR清理路径；所谓socket reset实际只是SIO参数设置和clearBuffer，不是重新建立socket或应用层授权握手。sioGet返回0/负值的运行时语义、缓冲区清理覆盖范围和控制器重启后的旧报文处理均需目标VAL3版本验证。

这些是固定公开原型的静态行为，不证明现场发生命令重放、通信中断导致危险运动或停止距离不满足要求。未修改ICube/MoveIt/ros2_control上游，未应用PR；未执行动态、HIL、FAT/SAT或实机验证。现场部署版本、UDP网络拓扑和安全授权配置未确认，Stäubli工程级验收未通过，`TODO-EXT-001`未授权合并。

### 固定源码链接

- https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/val3/userapp/ros2_server/controlTask.pgx
- https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/val3/userapp/ros2_server/Comm/readData.pgx
- https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/val3/userapp/ros2_server/Comm/readDataOnce.pgx
- https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/val3/userapp/ros2_server/Comm/resetControlSocket.pgx
- https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/val3/userapp/ros2_server/Comm/computeSequenceDelay.pgx
- https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/val3/userapp/ros2_server/Comm/getNextSequenceNumber.pgx
- https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/val3/userapp/ros2_server/Serialization/decodeHeader.pgx
- https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/val3/userapp/ros2_server/Serialization/decodeRobotCommandMsg.pgx


## §9.3.183｜ROS/VAL3重启、状态订阅缓存与16位序号会话边界

### 审查范围与固定基线

固定审查 `ICube-Robotics/staubli_driver_ros2@bd658e2d266e315d2ee35f985fb352ea88306b79`。本节追踪ROS RobotDriver connect/disconnect、状态接收线程的latest-message缓存、状态序号差计算、硬件接口命令序号来源，以及VAL3控制任务启动时序号初始化。

| 文件 | Blob SHA |
|---|---|
| `robot_driver.cpp` | `ede48a314856a455df9d8434f354aaf9fbc47bff` |
| `robot_driver.hpp` | `62c87a6741aa082db4599bb2c048aec0fcd7a464` |
| `real_time_socket_subscriber.cpp` | `e2cd8fc50b2b13d9e31b2c024e90f9da76107622` |
| `real_time_socket_subscriber.hpp` | `330839cb25e53fe961541f29f634722bec4a47c4` |
| `udp_socket_impl.hpp` | `1309a8f2d59e8295869e178af82a66868bb911ff` |
| `staubli_hardware_interface.cpp` | `4ae2b8c8d91857e5e32558bfcd16e2c391b9c3d0` |
| `controlTask.pgx` | `00a69c4d13879116fce744ceb1611ecd05d65edf` |
| `getNextSequenceNumber.pgx` | `8bdda02a8887968b1b86e42be733f553b1e36b19` |

### 1. ROS端命令序号并非本地独立计数，而是复制最近有效RobotState序号

`RobotDriver::read_robot_state()`在消息有效且未超出staleness timeout后，将 `state.header.sequence_number`写入 `last_valid_sequence_id_`。硬件接口每次构造RobotCommand时，把该值转换为uint16_t作为命令头序号；STOP辅助命令也使用同一来源。因此ROS端不是自行递增命令序号，而是回显最近有效机器人状态序号。

这使正常运行时ROS命令序号跟随VAL3状态序号；但也意味着命令序号是否更新取决于read路径成功读取状态。read失败时输出状态和last_valid_sequence_id_不会更新，旧序号可能继续被用于后续write，相关缓存门禁问题已在§9.3.178/179记录，本节不重复判定其控制器调度结果。

### 2. RobotDriver断开时会重置状态缓存，但连接成功路径依赖收到第一份有效状态

构造函数调用 `reset_data()`，将last_valid_sequence_id_置0，并把当前状态/诊断消息类型标记INVALID。disconnect()在停止接收线程、释放接口并断开socket后再次调用reset_data()。若connect()发现socket仍连接，会先disconnect()，再建立新接口。

connect()创建新的RealTimeSocketInterface，订阅对象的构造函数将 `last_read_sequence_number_`置0、`first_read_`置true，并启动接收线程；连接建立后等待read_robot_state()取得有效状态。故显式disconnect→connect路径中，ROS侧状态缓存与subscriber序号跟踪均重新初始化。该路径不建立应用层会话ID，也没有与VAL3端进行新的随机挑战或双向序号协商。

若底层socket状态异常变化但未经过RobotDriver::disconnect()，connect()的“是否已连接”分支和旧接口生命周期需要单独覆盖测试；本轮不推断所有异常断链场景均会自动调用reset_data()。

### 3. Subscriber是latest-message单槽缓存，不是可靠队列

接收线程每次成功反序列化后，将消息写入 `RealtimeThreadSafeBox<MessageType>`。read_message()只try_get当前最新消息，不维护逐包队列。高频数据在控制循环消费较慢时可能被中间覆盖；lost_packages仅根据两次被读取消息的序号差估算，不会恢复缺失消息。

read_message()在比较序号前将status.new_message设为true；若序号相同，后续分支才将其设为false。RobotDriver::read_robot_state()没有使用status.new_message来拒绝重复状态，lost_packages的告警也被注释。因此重复读取同一状态时，只要其reception_timestamp仍在staleness timeout内，read_robot_state()仍可返回true并再次把相同序号写入last_valid_sequence_id_。这不是新状态确认，也不代表机器人刚刚产生了新反馈。

### 4. 序号下降被一律按16位回绕计算，不能识别控制器重启与合法回绕的区别

subscriber在新序号大于上次读到的序号时计算普通丢包数；序号变小时按 `MAX_FRAME_SEQUENCE_NUMBER`计算回绕丢包数。它没有根据连接重建、VAL3 task启动、机器人重启或会话代号来区分“合法16位回绕”和“发送端序号复位”。

VAL3 `controlTask`启动时把本地状态序号初始化为0，随后每周期递增；错误复位路径也把本地序号清零。subscriber的first_read逻辑会让新订阅对象收到的第一帧不参与丢包比较。结合ROS命令序号回显最近状态序号，静态代码显示控制器重启后新订阅/新状态可以重新建立序号跟随，但没有会话级身份验证或旧数据报拒绝机制。

这里不能仅凭序号下降断言旧命令会被接受或导致运动：VAL3还会检查序号延迟、命令格式和模式状态；旧UDP报文是否能在socket关闭/重建后残留、到达时序如何、是否被新状态序号门限拒绝，需要网络注入实测。

### 5. UDP socket关闭/重建与VAL3端clearBuffer属于不同层级

ROS的UDPSocketImpl::disconnect()停止接收线程并关闭本地UDP socket；connect()重新open、bind并设置remote endpoint。代码没有显式调用应用层flush，也没有会话握手。底层操作系统对已关闭UDP socket排队数据的处置属于OS网络栈语义，本仓库没有给出跨平台保证，不能把VAL3 clearBuffer与ROS socket close视为同一操作。

VAL3端在controlTask启动和错误恢复路径调用clearBuffer；ROS端断开后关闭socket，重新连接时新建subscriber及其单槽消息缓存。两端各自清理本地资源，但协议没有会话nonce/epoch字段把两个生命周期绑定起来。

### 6. 当前单测覆盖与缺口

`test_robot_driver.cpp`的mock发送线程使用函数内static sequence_number从1开始递增；现有连接、断开、状态读取和staleness恢复测试证明基本连接/数据恢复路径可运行，但没有在同一个RobotDriver对象上完整验证VAL3序号重启、ROS断线重连、序号回绕、重复状态与旧报文交错。测试mock线程的static计数器在测试生命周期内递增，不是每次mock重启都从1重新开始，因此不能覆盖控制器序号复位情形。

`test_rt_socket_interface.cpp`覆盖了消息传输和部分序号场景，但没有构造两个会话之间的延迟旧报文、跨重启重复序号或序号epoch不匹配测试。

### 7. 本轮静态结论

1. ROS命令序号取自最近一次有效RobotState序号，不是ROS独立递增计数器。
2. 显式disconnect会重置RobotDriver状态缓存；新subscriber会把first_read置true，并只在接收线程latest-message单槽中保留最新消息。
3. read_message将重复序号标记为status.new_message=false，但RobotDriver::read_robot_state()忽略该标志；重复且未过期的状态仍可能被作为有效读结果返回，命令序号因此保持旧值。
4. 序号下降被当作16位回绕计算，代码没有识别发送端进程/VAL3任务重启的会话边界。
5. ROS UDP socket关闭/重新绑定和VAL3 clearBuffer分别清理各自本地资源，但协议未提供会话epoch/nonce，也没有跨端重新授权握手。
6. 以上是固定公开原型的静态结论；不能据此断言现场旧报文跨重启残留、被执行或造成危险运动。

### 8. 新增验收任务

新增SERVO-766：

| 子项 | 验收对象 | 状态 |
|---|---|---|
| W1 | 同一RobotDriver对象执行disconnect→connect，验证last_valid_sequence_id_、状态类型、subscriber first_read和缓存均重置 | 未执行 |
| W2 | 保持ROS连接，单独重启VAL3 controlTask，验证状态序号复位、subscriber回绕计数及命令序号重新跟随 | 未执行 |
| W3 | 在状态接收线程注入重复序号且时间戳持续更新/停止更新两种情形，验证read_robot_state返回值及status.new_message | 未执行 |
| W4 | 在latest-message单槽缓存前注入高频突发状态，量化被覆盖帧、lost_packages与实际消费序列 | 未执行 |
| W5 | 注入16位序号65534、65535、0、1以及非回绕下降，验证回绕丢包计算与异常区分能力 | 未执行 |
| W6 | ROS断线/重连与VAL3任务重启交错，注入旧会话延迟数据报，验证是否能被新连接接收及是否影响命令序号 | 未执行 |
| W7 | 对本地UDP socket关闭/重绑、端口复用、接收线程停止/重启进行抓包，确认内核队列和迟到报文处置 | 未执行 |
| W8 | 为subscriber增加重复序号、latest-message覆盖、回绕和会话复位单测，明确new_message与lost_packages契约 | 未执行 |
| W9 | 评估会话epoch/随机nonce/启动代号及双向重同步握手设计，形成兼容性与失效安全评审，不直接修改上游 | 未执行 |
| W10 | 获取现场ROS/CS9/VAL3版本、重启日志、UDP抓包及FAT/SAT重连验收记录 | 未确认，现场证据缺失 |

W1-W9全部未执行；W10现场证据缺失。未执行ROS构建/单测、UDP重启故障注入、VAL3仿真、HIL、CS9实机或FAT/SAT。

### 9. 结论与边界

固定公开源码显示，ROS端命令序号跟随最近有效机器人状态序号；显式disconnect会重置RobotDriver缓存，新subscriber以first_read=true开始并使用latest-message单槽缓存。重复序号会在subscriber状态中被标为非新消息，但RobotDriver读取层没有使用该标志拒绝重复状态。序号下降一律按16位回绕估算丢包，无法区分合法回绕与发送端重启。两端资源清理没有构成协议级会话重同步或重新授权握手。

这构成跨重启会话边界与验证覆盖缺口，不证明旧UDP数据报一定跨重启残留，也不证明旧命令会被执行。未修改ICube/MoveIt/ros2_control上游，未应用PR；未执行动态、HIL、FAT/SAT或实机验证。现场部署版本、网络拓扑及控制器重启行为未确认，Stäubli工程级验收未通过，`TODO-EXT-001`未授权合并。

### 固定源码链接

- https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/src/robot_driver.cpp
- https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/include/staubli_robot_driver/robot_driver.hpp
- https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/src/real_time_socket_subscriber.cpp
- https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/include/staubli_robot_driver/real_time_socket_subscriber.hpp
- https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/src/communication/udp_socket_impl.hpp
- https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/src/staubli_hardware_interface.cpp
- https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/val3/userapp/ros2_server/controlTask.pgx
- https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/val3/userapp/ros2_server/Comm/getNextSequenceNumber.pgx


## §9.3.184｜ROS UDP接收错误、状态反序列化校验与latest-message缓存新鲜度

### 审查范围与固定基线

固定审查 `ICube-Robotics/staubli_driver_ros2@bd658e2d266e315d2ee35f985fb352ea88306b79`。本节沿UDP async receive callback、RobotStateMessage反序列化、RealTimeSocketSubscriber缓存写入/读取、RobotDriver::read_robot_state有效性与staleness门禁追踪异常报文传播。审查对象仍是公开Jazzy/CS9原型，不代表目标现场部署版本。

| 文件 | Blob SHA |
|---|---|
| `udp_socket_impl.hpp` | `1309a8f2d59e8295869e178af82a66868bb911ff` |
| `real_time_socket_subscriber.cpp` | `e2cd8fc50b2b13d9e31b2c024e90f9da76107622` |
| `real_time_socket_subscriber.hpp` | `330839cb25e53fe961541f29f634722bec4a47c4` |
| `messages.cpp` | `86c4d7b6eac0e2455214fc78ebd6864ae5b0b0c6` |
| `protocol.cpp` | `d31077aefc1d5515919033aa967c431a01d49a4a` |
| `protocol.hpp` | `773cdeb9c4bf6e2dab3cf9e15426e4e954e35dea` |
| `robot_driver.cpp` | `ede48a314856a455df9d8434f354aaf9fbc47bff` |
| `robot_driver.hpp` | `62c87a6741aa082db4599bb2c048aec0fcd7a464` |

### 1. UDP接收错误并未阻止回调执行，且来源地址校验仍是注释TODO

`UDPSocketImpl::handle_data_received(error, bytes_transferred)`在error非零时只记录错误日志，没有return或把error传给上层；随后仍无条件调用`reception_callback_(recv_buffer_, bytes_transferred)`，并在`receiving_==true`时重新调用`start_receive()`。因此接收错误事件不会在该函数内自动阻止反序列化尝试，也没有形成明确的接收错误状态传递契约。若错误事件的bytes_transferred为0，RobotState反序列化会因长度不足失败；若错误事件同时携带足够长度数据，回调仍会尝试解析，是否会出现可被接受的非零数据错误组合须按Boost.Asio/目标OS运行时验证，不能由静态代码断言。

同一函数中sender endpoint与remote endpoint比较逻辑完整保留为注释TODO，实际没有丢弃非预期来源地址的门禁。故任何能够向本地UDP端口送达报文的来源，均会进入相同反序列化入口；是否可达取决于网络隔离、防火墙和现场拓扑。静态审查不证明现场已发生伪造或注入。

### 2. 反序列化失败时旧缓存保留，失败报文不会刷新缓存时间戳

`RealTimeSocketSubscriber::update_message()`先构造局部MessageType对象；只有`msg.deserialize(data.data(), bytes_transferred)`返回true时，才写入本地接收时间戳并调用`message_buffer_.set(msg)`。失败分支只记录日志，不清空、不标invalid，也不更新缓存时间戳。因此短包、magic错误等导致deserialize=false的报文不会覆盖上一次成功缓存，也不会刷新那条缓存的reception_timestamp。

`read_message()`随后仍可从RealtimeThreadSafeBox取出旧消息，并按旧reception_timestamp计算time_since_received；在旧消息尚未超过state_staleness_timeout_时，RobotDriver仍可能读取到该旧状态。默认状态staleness timeout为100 ms；超过阈值后read_robot_state()返回false。连续坏包不会把旧消息时间戳续期，但也不会触发此处的即时缓存失效或单独的通信故障锁存。具体控制器write周期在该窗口内的后续影响，仍受ros2_control调度及硬件接口路径影响，不能仅凭本节断言。

### 3. RobotState反序列化的Header校验弱于RobotCommand，固定长度仅作最小长度门禁

`FrameHeader::deserialize()`只检查缓冲区至少8字节、读取字段并验证magic_number；没有检查protocol_version、message_type或payload_size。RobotStateMessage::deserialize()在至少132字节时调用该函数，随后直接按固定偏移读取状态字段。源码中“Validate header fields”部分没有实际校验；最终offset只与固定的get_serialized_size()（132）比较，而不是与实际buffer_size比较。

由此可静态确认：
- RobotState报文长度小于132字节会被拒绝；长度大于132字节时，前132字节解码后offset仍等于132，额外尾随字节不会使其失败。
- 只要magic正确，RobotState解码路径不会自行拒绝protocol_version不匹配或payload_size与固定载荷不一致的Header。
- RobotState解码路径不会校验header.message_type；RobotDriver::is_state_msg_valid()是在消息已经被subscriber写入缓存、read_message取出后才检查message_type是否为ROBOT_STATE。
- RobotState的joint_positions、joint_velocities、joint_torques、ft_sensor及analog_inputs等浮点数组没有逐字段finite/NaN/Inf校验；合法长度但含非有限值的报文仍可能通过deserialize。

对比之下，RobotCommandMessage::deserialize()在header解码后显式校验payload_size与固定载荷长度、message_type为ROBOT_COMMAND；但FrameHeader层仍只校验magic，protocol_version也不在该函数内验证。该差异不应被误写为所有消息类型具有相同严格度。

### 4. 错误message_type与错误protocol_version对缓存和上层读取的影响不同

若一个至少132字节、magic正确但message_type不是ROBOT_STATE的报文进入RobotState subscriber，RobotStateMessage::deserialize()仍可能返回true并刷新reception_timestamp、覆盖latest-message缓存。随后RobotDriver::read_robot_state()的`is_state_msg_valid()`检查会拒绝该缓存消息，但此前的最后一条有效状态已被单槽缓存替换；在下一条有效RobotState到达前，读取层会继续面对该错误类型缓存，而不是自动回退到此前有效状态。

若报文message_type仍为ROBOT_STATE、magic正确，但protocol_version或payload_size不匹配，RobotState解码器不会在运行时拒绝它；RobotDriver读取路径的有效性检查只核对message_type和staleness，不会逐帧复核protocol_version/payload_size。connect()成功路径曾在初始状态后比较一次protocol_version，但这不能替代运行期间逐帧校验。该静态事实意味着异常Header可能进入状态消费路径；不代表现场存在此类报文。

### 5. latest-message缓存、重复读取与staleness是三个独立语义

subscriber仍使用RealtimeThreadSafeBox单槽缓存，read_message只取最新值而不是逐包队列。坏包deserialize失败时缓存保留；同一旧缓存可以被重复读取，`status.new_message`在序号相同分支最终会变为false，但RobotDriver::read_robot_state()不使用该标志拒绝重复状态（重复读取问题已在§9.3.183记录）。因此：
1. 新坏包到达不代表旧状态缓存被刷新；
2. read_message返回true不代表本次接收线程收到了新报文；
3. status.new_message=false不代表RobotDriver拒绝该状态；
4. staleness按缓存中最后一次成功deserialize的本地接收时间计算，而不是按最近一次UDP数据报到达时间计算；
5. 有效长度但Header/浮点语义校验不足的报文，反而可能刷新缓存时间戳并替换最后有效状态。

### 6. 本轮静态结论

1. UDP receive callback在error非零时仍调用上层回调并可能重新挂起下一次接收；error没有传递到subscriber，来源地址校验留在注释TODO。
2. deserialize失败只记录日志，不清空latest-message缓存、不刷新时间戳；旧状态年龄继续增长，100 ms默认staleness阈值之前仍可能被重复读取。
3. RobotStateMessage反序列化仅以132字节作为最小长度，Header只校验magic，未校验protocol_version/message_type/payload_size，且不拒绝尾随字节。
4. 错误message_type的完整长度报文可能先覆盖缓存、刷新时间戳，再被RobotDriver上层拒绝；错误protocol_version/payload_size但message_type正确的状态帧则没有逐帧门禁。
5. RobotState浮点数组没有finite/NaN/Inf检查；不能把“反序列化成功”解释为状态数值可信。
6. 以上为固定公开原型静态事实，不证明现场已接收恶意报文、产生错误运动或出现实际安全事件。

### 7. 新增验收任务

新增SERVO-767：

| 子项 | 验收对象 | 状态 |
|---|---|---|
| X1 | 注入0、7、8、131、132、133字节UDP报文，记录RobotState deserialize返回值、缓存内容及时间戳 | 未执行 |
| X2 | 分别篡改magic、protocol_version、message_type、payload_size，验证RobotState与RobotCommand两种反序列化路径 | 未执行 |
| X3 | 对RobotState六轴位置/速度/力矩、F/T和模拟输入注入NaN、±Inf、float32边界值，验证上层状态接口及日志 | 未执行 |
| X4 | 从预期和非预期源IP/端口发送合法长度状态帧，验证sender endpoint过滤、网络ACL和缓存写入 | 未执行 |
| X5 | 在目标Boost.Asio/OS下制造receive error、0字节及非零bytes_transferred组合，验证callback调用、重新挂起和错误恢复 | 未执行 |
| X6 | 在持续有效状态流中交替注入短包、错误magic、错误Header与随机数据，测量缓存替换/保留、时间戳及错误日志 | 未执行 |
| X7 | 先发送有效状态，再连续发送反序列化失败报文，测量旧缓存在100 ms门限前后的read_robot_state返回值与write调用链 | 未执行 |
| X8 | 构造magic正确、长度≥132但message_type错误的帧，验证错误帧覆盖缓存后是否回退到最后有效状态 | 未执行 |
| X9 | 在已建立连接后动态切换protocol_version/payload_size，验证每帧校验、缓存刷新及恢复策略 | 未执行 |
| X10 | 获取现场ROS/Boost/OS/CS9/VAL3版本、网络ACL/抓包、状态超时参数与FAT/SAT异常报文测试记录 | 未确认，现场证据缺失 |

X1-X9全部未执行，X10现场证据缺失。未执行ROS构建/单测、协议模糊测试、UDP错误注入、VAL3/CS9仿真、HIL、FAT/SAT或实机验证。

### 8. 结论与边界

本轮确认两类不同异常路径：反序列化失败会保留旧缓存且不刷新旧时间戳，旧状态可在超龄前继续被读取；而某些长度合法但Header校验不足的报文可能反而通过RobotState反序列化、刷新时间戳并覆盖缓存，再由上层有限检查拒绝或接受。UDP接收错误回调不具备明确的错误短路，发送源地址校验尚未实现。故必须分别验收数据报传输状态、帧结构/协议校验、字段数值有效性、缓存新鲜度和上层消费行为。

未修改ICube/MoveIt/ros2_control上游，未应用PR；未执行动态、HIL、FAT/SAT或实机验证。目标现场版本、网络拓扑、接收错误语义及安全配置仍未确认。Stäubli工程级验收未通过，`TODO-EXT-001`未授权合并。

### 固定源码链接

- https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/src/communication/udp_socket_impl.hpp
- https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/src/real_time_socket_subscriber.cpp
- https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/include/staubli_robot_driver/real_time_socket_subscriber.hpp
- https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/src/communication/messages.cpp
- https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/src/communication/protocol.cpp
- https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/include/staubli_robot_driver/communication/protocol.hpp
- https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/src/robot_driver.cpp
- https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/include/staubli_robot_driver/robot_driver.hpp


## §9.3.185｜RobotState非有限数值、ros2_control状态接口与位置命令初始化传播边界

### 审查范围与固定基线

固定审查 \`ICube-Robotics/staubli_driver_ros2@bd658e2d266e315d2ee35f985fb352ea88306b79\`。本节从§9.3.184已识别的RobotState解码字段缺少finite校验继续向下追踪，范围限定为 \`StaubliHardwareInterface::read()/update_state()\`、导出的joint/GPIO state interfaces、位置命令模式初始化，以及硬件接口现有单元测试。不重复判断UDP帧解析本身，也不把静态路径推导当作实际机器人已接受命令。

| 文件 | Blob SHA |
|---|---|
| \`staubli_hardware_interface.cpp\` | \`4ae2b8c8d91857e5e32558bfcd16e2c391b9c3d0\` |
| \`staubli_hardware_interface.hpp\` | \`a84d0c63b15db168ea453a15571ab1494b8f9e99\` |
| \`test_staubli_hardware_interface.cpp\` | \`12326353052408a7a040926328dbe7da22625553\` |
| \`test_staubli_hardware_interface.hpp\` | \`f474af023d35b4fd2fc2669092fc9f8bea7cdd19\` |
| \`messages.cpp\` | \`86c4d7b6eac0e2455214fc78ebd6864ae5b0b0c6\` |
| \`robot_driver.cpp\` | \`ede48a314856a455df9d8434f354aaf9fbc47bff\` |

### 1. RobotState关节测量值进入硬件状态缓存前没有有限值门禁

\`StaubliHardwareInterface::read()\`先调用 \`robot_driver_->read_robot_state(state_msg_)\`，成功后调用 \`update_state(state_msg_)\`。后者只根据 \`has_joint_positions\` 与 \`has_joint_velocities\` 标志判断对应字段是否存在，然后逐轴将 \`state_msg_.joint_positions/velocities\` 经 \`deg2rad()\` 写入 \`hw_joint_positions_/hw_joint_velocities_\`；对这些输入没有 \`std::isfinite\`、NaN或Inf拒绝。

关节力矩在 \`has_joint_torques=true\` 时直接复制；标志为false时才将effort缓存清零。状态消息解析路径缺少非有限数值过滤已在§9.3.184识别；本节进一步确认硬件接口没有在写入导出的joint state buffers前补上第二道数值门禁。因此，只要上游给出字段有效标志且反序列化成功的非有限关节测量，静态代码路径允许NaN/Inf进入内部状态缓存。

### 2. 状态接口导出与位置命令模式初始化形成状态到命令的直通路径

\`export_state_interfaces()\`将 \`hw_joint_positions_\`、\`hw_joint_velocities_\` 和 \`hw_joint_efforts_\` 的元素地址直接注册为各关节position/velocity/effort状态接口；没有伴随导出的finite/quality/validity状态。

切入 \`JOINT_POSITION\` 时，\`perform_command_mode_switch()\`在检查 \`error_state\` 与 \`motion_possible\` 后，把 \`hw_joint_positions_\` 整个复制到 \`hw_joint_position_commands_\` 作为安全初始化值。该复制前没有额外finite检查。故非有限位置测量不仅可能呈现在joint state interfaces，也可能被复制成位置命令的初始值。

后续 \`write()\` 将位置命令转换成度并只使用 \`std::isnan()\` 检查命令数组；\`std::isnan(+/-Inf)\`不会命中该门禁。该NaN-only门禁及六元素数组边界已在§9.3.180记录，本节只说明输入测量值到命令初始化之间的传播关系。静态审查不能证明该值已经通过所有序列化/网络环节并被VAL3执行；必须以mock socket、协议抓包和目标控制器测试验证后续行为。

### 3. GPIO输入有效标志为false时保留上一次缓存值

\`update_state()\`仅在 \`has_digital_inputs\` 为true时更新 \`hw_digital_inputs_\`，仅在 \`has_analog_inputs\` 为true时更新 \`hw_analog_inputs_\`。这两个标志为false时没有将缓存清零，也没有记录“当前样本无效”的状态。两个向量在 \`on_init()\` 时初始化为0，但在之后收到过一次有效输入后，如下一帧将valid flag置false，缓存将保持先前样本。

\`export_state_interfaces()\`仍会按配置导出所有digital_input/analog_input接口，没有相应的有效位或样本年龄接口供下游区分“当前值”与“上次有效值”。因此可确认存在旧IO值保留语义；不能仅凭此推断下游业务必然把它当作新值，也不能推断VAL3现场输入字段标志会如何变化。

对照处理：\`has_joint_positions=false\`或 \`has_joint_velocities=false\` 会使 \`update_state()\`返回false；\`has_joint_torques=false\`会将effort置零；digital/analog输入缺失则静默保留旧值。不同字段的missing-data策略并不一致。

### 4. update_state不是整帧原子更新；监督GPIO首次写入前也没有显式初始化

\`update_state()\`按字段顺序原地修改成员缓存。若位置字段有效而速度字段无效，则位置数组已经更新，函数随后因缺少速度数据返回false；\`read()\`因而返回 \`hardware_interface::return_type::ERROR\`，但位置成员并未回滚。控制器管理器在该read错误后的调度/消费行为取决于目标ros2_control版本和配置，本次不据此断言后续write必然发生或必然停止。

此外，头文件中的 \`SupervisionGpio\` 是仅含double成员的结构体，没有成员默认值；硬件接口构造函数和 \`on_init()\` 未显式初始化 \`supervision_gpio_copy_\`。而 \`export_state_interfaces()\` 会导出这些成员的地址，只有 \`update_state()\` 成功执行到末尾时才逐项写入当前状态。故首次成功状态更新之前，这些接口的初值没有由本插件明确设定；是否存在读取窗口及其可观察行为需按目标hardware_interface lifecycle动态确认。

### 5. 当前硬件接口测试未覆盖异常状态字段传播

固定提交的 \`test_staubli_hardware_interface.cpp\` 覆盖构造、初始化、插件加载、接口名称/数量和正常LifecycleTransitions；mock robot只发送有限位置/速度值，随后验证正常read、state interface更新和正常write。现有测试没有注入NaN/Inf、缺失速度字段、扭矩/IO valid flag翻转、非有限位置模式初始化或监督GPIO首次read前的值。

这说明测试覆盖不足，不等于上述路径已在目标控制器或实际机器人上触发。

### 6. 本轮静态结论

1. \`update_state()\`依据has_*标志判断字段存在，但对joint position/velocity/torque及analog input数值没有finite门禁；位置/速度可进入导出状态缓存。
2. \`JOINT_POSITION\`切换会把当前joint position缓存复制到位置命令缓存；该复制前没有finite过滤，形成从RobotState输入到命令初值的静态传播链。
3. \`write()\`的NaN-only检测不能拒绝正负Inf；此检测缺口已在§9.3.180记录。本节不将“write未拒绝Inf”升级为“VAL3已收到/执行Inf命令”。
4. digital/analog输入valid flag为false时，成员缓存保留上次有效值；导出的state interfaces不同时暴露有效标志或数据年龄。
5. \`update_state()\`可能在位置数据写入后因速度字段缺失返回false，形成非事务式部分更新；监督GPIO成员在首次成功更新之前没有由插件显式初始化。
6. 上述均为固定公开原型静态事实；未证明现场状态数据含非有限值、IO字段曾失效、控制器读取了旧值或异常位置命令到达机器人。

### 7. 新增验收任务

新增SERVO-768：

| 子项 | 验收对象 | 状态 |
|---|---|---|
| Y1 | 通过RobotState协议分别注入joint position的NaN、+Inf、-Inf，记录deserialize、read、update_state和导出state interface值 | 未执行 |
| Y2 | 对joint velocity注入NaN/±Inf，检查状态缓存、read返回值和下游状态接口 | 未执行 |
| Y3 | 在has_joint_torques=true时注入NaN/±Inf，并对比has_joint_torques=false时effort清零行为 | 未执行 |
| Y4 | 先发送有效digital/analog输入，再将valid flags置false，验证缓存是否保留旧值及下游接口可见值 | 未执行 |
| Y5 | 位置有效、速度无效及相反组合分别注入，记录update_state成员写入顺序、read错误返回和缓存回滚行为 | 未执行 |
| Y6 | 在收到非有限位置状态后切换JOINT_POSITION，检查position command是否复制该值及模式切换门禁 | 未执行 |
| Y7 | 通过mock socket验证write对NaN/+Inf/-Inf的处理、序列化结果和send调用；只做隔离测试，不接真实机械臂 | 未执行 |
| Y8 | 在首次成功read前后读取全部supervision state interfaces，验证初始化值、首次更新与生命周期顺序 | 未执行 |
| Y9 | 将valid flag翻转、连续状态丢失和恢复组合成矩阵，验证关节/GPIO/监督状态的清空、保留、部分更新及恢复语义 | 未执行 |
| Y10 | 获取现场ROS 2/ros2_control/ICube版本、状态数据抓包、IO valid flag定义、控制器日志及FAT/SAT异常状态验收记录 | 未确认，现场证据缺失 |

Y1-Y9全部未执行，Y10现场证据缺失。未执行ROS构建/单测、mock socket异常注入、ASan/UBSan、VAL3/CS9仿真、HIL、FAT/SAT或实机验证。

### 8. 结论与边界

本节确认RobotState字段有效标志与数值质量是两种不同契约：has_*只说明发送端声明该字段存在，不能替代数值finite检查；状态接口导出也没有附带质量/年龄信息。位置状态可能被直接用作位置命令模式的初始化值；IO字段缺失时旧缓存保持不变；部分状态缺失时更新过程不是整帧事务。需要在独立mock环境先验证输入值、缓存值、状态接口和write报文，再决定是否开展目标CS9/HIL测试。

未修改ICube/MoveIt/ros2_control上游，未应用PR；未执行动态、HIL、FAT/SAT或实机验证。目标现场版本、控制器调度行为、IO配置及安全配置仍未确认。Stäubli工程级验收未通过，\`TODO-EXT-001\`未授权合并。

### 固定源码链接

- https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/src/staubli_hardware_interface.cpp
- https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/include/staubli_robot_driver/staubli_hardware_interface.hpp
- https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/test/unit_tests/test_staubli_hardware_interface.cpp
- https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/test/unit_tests/test_staubli_hardware_interface.hpp
- https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/src/communication/messages.cpp
- https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/src/robot_driver.cpp


## §9.3.186｜ros2_control命令模式切换、混合接口解析与GPIO输出缓存跨STOP/lifecycle持久化

### 审查范围与固定基线

固定审查 ICube-Robotics/staubli_driver_ros2@bd658e2d266e315d2ee35f985fb352ea88306b79。沿§9.3.185已确认的状态/命令缓存继续检查命令接口导出、prepare/perform_command_mode_switch、write()报文构造、GPIO输出命令缓存，以及硬件插件STOP和cleanup/reconfigure生命周期边界。

| 文件 | Blob SHA |
|---|---|
| staubli_hardware_interface.cpp | 4ae2b8c8d91857e5e32558bfcd16e2c391b9c3d0 |
| staubli_hardware_interface.hpp | a84d0c63b15db168ea453a15571ab1494b8f9e99 |
| test_staubli_hardware_interface.cpp | 12326353052408a7a040926328dbe7da22625553 |
| test_staubli_hardware_interface.hpp | f474af023d35b4fd2fc2669092fc9f8bea7cdd19 |
| messages.cpp | 86c4d7b6eac0e2455214fc78ebd6864ae5b0b0c6 |
| robot_driver.cpp | ede48a314856a455df9d8434f354aaf9fbc47bff |
| VAL3 controlTask.pgx | 00a69c4d13879116fce744ceb1611ecd05d65edf |

### 1. 模式解析只取start_interfaces中的第一个匹配项，混合接口没有整体拒绝

resolve_mode()按start_interfaces顺序扫描字符串，遇到position、velocity、effort或acceleration关键词后立即返回对应CommandType。prepare_command_mode_switch()明确留有TODO，尚未验证所有接口是否成组启动/停止；stop_interfaces参数没有参与模式判断，outgoing_mode解析仍被注释。

因此，若一次启动请求同时包含position和velocity接口，position项先出现时resolve_mode()返回JOINT_POSITION并被接受；velocity项先出现时则返回JOINT_VELOCITY并因当前不支持速度控制而被拒绝。混合接口的结果对输入列表顺序敏感，而不是基于完整请求集合做一致性校验。effort混入请求也由首个匹配项决定最终路径。该结论是函数控制流可直接推导的，不代表controller_manager一定会生成某种特定混合请求。

### 2. acceleration-only启动的实现行为与头文件注释矛盾

头文件对hw_joint_acceleration_commands_的说明称加速度接口只用于joint limiter，切换到acceleration mode将总是被拒绝。但当前实现中，acceleration-only请求使resolve_mode()返回INVALID；prepare_command_mode_switch()将其识别为only_stop_or_accel_starting，允许通过，并把pending_mode_设为STOP。即该请求不会激活机器人加速度控制模式，而是被接受并折算为STOP/no active joint command mode。需要统一接口文档与实际返回契约，不能把当前实现描述为拒绝该请求。

### 3. STOP常规write仍携带缓存的GPIO输出命令

on_init()将digital/analog output command向量初始化为0。export_command_interfaces()将这些向量元素地址导出为命令接口。write()即使在current_control_mode_为STOP时，也只将关节command_reference清零；随后仍无条件从hw_digital_output_commands_和hw_analog_output_commands_复制输出值到RobotCommandMessage，再发送整条报文。

perform_command_mode_switch()会重置关节position/velocity/acceleration命令缓存，但没有清空digital/analog output command缓存。on_activate()只把current_control_mode_设置为STOP；on_cleanup()只断开RobotDriver连接；二者都没有重置GPIO输出命令。因此，同一StaubliHardwareInterface实例在输出命令曾被写入后经历STOP或cleanup→configure→activate时，后续write()仍可能把旧GPIO输出值带入常规STOP报文。缓存值是ROS插件进程内的命令状态，不等于控制器已接受或物理IO已切换。

对照RobotCommandMessage构造函数：独立构造的消息默认digital_outputs为false、analog_outputs为0.0；RobotDriver::send_stop_all_command()使用新构造的STOP消息，因而与hardware_interface::write()中复用GPIO命令缓存的STOP报文行为不同。前者的默认输出值不能证明后续常规write也会清空缓存。

### 4. 物理IO执行边界仍未闭合

固定VAL3 controlTask.pgx在Execute GPIO commands段仍将digital outputs与analog outputs的执行实现标为TODO。因此本节确认的是ROS侧命令接口、报文填充和缓存生命周期语义；不能据此声称目标CS9现场已按这些字段驱动真实IO，也不能声称STOP报文中的旧输出值已造成物理输出保持。需在目标VAL3应用/IO映射与现场版本确认后开展隔离仿真和HIL验证。

### 5. 现有测试覆盖不足

test_staubli_hardware_interface.cpp覆盖构造、初始化、接口名称/数量、mock robot正常连接及一次正常read/write。当前文件没有调用prepare_command_mode_switch()/perform_command_mode_switch()来覆盖position/velocity混合接口顺序、stop_interfaces组合、acceleration-only启动、模式切换失败后的状态，也没有设置GPIO输出后验证STOP write报文或cleanup/reconfigure后的输出缓存是否保留。未执行该测试套件构建或运行。

### 6. 本轮静态结论

1. resolve_mode()采用首个匹配项策略；prepare_command_mode_switch()没有对start_interfaces整体进行互斥/完整性校验，stop_interfaces未参与当前模式决策，混合接口请求可能呈现顺序敏感结果。
2. acceleration-only启动在当前实现中被接受并映射为STOP，与头文件“总是拒绝加速度模式切换”的注释不一致；它不是实际加速度控制。
3. 常规write()在STOP模式仍把GPIO输出缓存复制到RobotCommandMessage；perform_command_mode_switch()、on_activate()和on_cleanup()没有清空这些缓存，cleanup/reconfigure复用同一插件对象时存在旧输出命令再次进入报文的静态路径。
4. send_stop_all_command()使用新构造的RobotCommandMessage，其GPIO输出默认false/0；这与硬件接口write()构造STOP报文时携带缓存输出的路径不同。
5. 固定VAL3原型尚未实现controlTask中的digital/analog output执行段；本节不证明物理IO动作，也不证明该公开原型等同现场部署。
6. 以上是静态代码路径和测试覆盖缺口；没有执行mock报文断言、ROS构建/单测、生命周期故障注入、VAL3/CS9仿真、HIL、FAT/SAT或实机测试。

### 7. 新增验收任务

新增SERVO-769：

| 子项 | 验收对象 | 状态 |
|---|---|---|
| Z1 | 对position+velocity、velocity+position、position+effort等start_interfaces排列进行表驱动测试，记录prepare返回值和pending mode | 未执行 |
| Z2 | 对不同stop_interfaces组合及start_interfaces为空的切换请求测试，确认当前模式决策是否忽略停止集合 | 未执行 |
| Z3 | 分别测试acceleration-only、position+acceleration、acceleration+position请求，并核对头文件注释与实际返回契约 | 未执行 |
| Z4 | 通过硬件接口测试设置digital/analog输出命令后切换STOP，捕获write报文并断言GPIO字段是否保留缓存值 | 未执行 |
| Z5 | 设置非默认GPIO输出后执行cleanup→configure→activate，在mock连接下验证同一插件实例的命令缓存是否重置 | 未执行 |
| Z6 | 比较RobotDriver::send_stop_all_command()与StaubliHardwareInterface::write(STOP)两条路径的数字/模拟输出字段 | 未执行 |
| Z7 | 对position模式切换成功、状态门禁失败、STOP切换及连续切换组合验证关节命令缓存与GPIO缓存的独立重置行为 | 未执行 |
| Z8 | 在目标VAL3程序中确认GPIO TODO的实际实现状态、输出映射和STOP/模式切换期间的物理输出策略 | 未执行 |
| Z9 | 在隔离mock/仿真环境验证混合接口请求和GPIO缓存跨lifecycle持久化，不连接真实机械臂 | 未执行 |
| Z10 | 获取现场ROS 2/ros2_control/ICube/VAL3版本、控制器接口声明、GPIO映射、lifecycle日志及FAT/SAT输出状态记录 | 未确认，现场证据缺失 |

Z1-Z9全部未执行，Z10现场证据缺失。未执行ROS构建/单测、mock报文断言、生命周期故障注入、VAL3/CS9仿真、HIL、FAT/SAT或实机验证。

### 8. 结论与边界

本节识别的是命令模式切换请求解释不完整，以及GPIO命令缓存与运动STOP/lifecycle状态相互独立的契约缺口。建议后续实现/测试明确拒绝混合运动接口、统一acceleration-only行为文档，并明确STOP、deactivate、cleanup、reconfigure时GPIO输出的安全默认值和保持策略；任何上游改动仍需用户授权。本节不提出或应用上游补丁。

未修改ICube/MoveIt/ros2_control上游，未应用PR；未执行动态、HIL、FAT/SAT或实机验证。目标现场版本、GPIO实际执行路径和安全输出策略仍未确认。Stäubli工程级验收未通过，TODO-EXT-001未授权合并。

### 固定源码链接

- https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/src/staubli_hardware_interface.cpp
- https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/include/staubli_robot_driver/staubli_hardware_interface.hpp
- https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/test/unit_tests/test_staubli_hardware_interface.cpp
- https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/test/unit_tests/test_staubli_hardware_interface.hpp
- https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/src/communication/messages.cpp
- https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/src/robot_driver.cpp
- https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/val3/userapp/ros2_server/controlTask.pgx


## §9.3.187｜VAL3命令序号延迟门禁、STOP/ERROR模式覆盖与通信复位语义审查

### 审查范围与固定基线

固定审查 `ICube-Robotics/staubli_driver_ros2@bd658e2d266e315d2ee35f985fb352ea88306b79`。沿§9.3.179、§9.3.182和§9.3.186继续追踪VAL3 `controlTask.pgx`中的命令序号延迟计算、延迟阈值处理、命令模式提取、STOP/ERROR执行分支和错误恢复。

| 文件 | Blob SHA |
|---|---|
| controlTask.pgx | 00a69c4d13879116fce744ceb1611ecd05d65edf |
| Comm/computeSequenceDelay.pgx | e96e5b378bc263255ee4f28720306ee911b8a5c1 |
| Comm/getNextSequenceNumber.pgx | 8bdda02a8887968b1b86e42be733f553b1e36b19 |
| Comm/readData.pgx | bf2e0f3d26e66724b9f656261e29fe573bd5f3b0 |
| Comm/readDataOnce.pgx | 652aa04548c814febab3c8c3fc807093261efd97 |

### 1. 延迟阈值分支先写STOP，随后被统一模式提取覆盖为ERROR

`controlTask.pgx`在检测到运动中序号延迟大于5、静止时大于25或负延迟时，先记录“going to STOP mode”，置 `l_bError=true` 并将 `l_nCmdMode=1`。但紧接着的统一命令模式提取分支检查 `l_bError`：只要错误标志为true，就将 `l_nCmdMode`重新赋值为0（ERROR），而不是保留1（STOP）。

因此这些延迟异常路径的实际内部模式不是日志所述的STOP，而是进入后续 `l_nCmdMode<=1` 的STOP/ERROR共用执行分支，并继续触发统一错误处理。错误处理再次调用 `stopMove()`、`resetMotion()`，把命令类型置0、清除错误标志、将命令有效位清false并重置控制socket。该路径会导致通信会话重置/重新建立，而不只是停留在普通STOP等待新命令。不能据日志文本把其描述成“仅切到STOP”；也不能把软件错误处理或API调用当作停止完成确认。

### 2. STOP与ERROR共享运动停止调用，但错误分支额外清理通信状态

执行段对 `l_nCmdMode<=1`统一执行停止逻辑；随后 `if(l_bError)` 才执行额外的错误处理，包括再次停止/复位运动、重置序号计数和延迟、清除控制活动状态、使旧命令无效及调用 `resetControlSocket()`。因此模式数值0与1在执行入口共享部分停止动作，但其后续通信生命周期不同。延迟异常因为前述覆盖进入ERROR路径，不能等同于一个普通STOP命令。

### 3. 序号延迟算法采用有阈值的16位回绕解释

`computeSequenceDelay.pgx`计算 `last_sent-last_received`；仅当差值小于-60000时加65536作为uint16回绕修正。小于0但未达到回绕阈值的差值保持负数，随后由controlTask判为异常并触发错误复位。该实现把“合法回绕”和“负延迟/异常序号”按固定数值阈值区分；没有会话epoch或发送端重启标识。此处是算法边界说明，与§9.3.183已登记的重启/回绕歧义相关，不重复将其作为新的独立根因。

### 4. 接收批处理结果与命令模式决策的关系

`readData.pgx`每周期最多调用两次 `readDataOnce`；当已经读到一条消息、后续一次读取没有新数据时返回，若两次均读到数据则保留后一次写入的缓冲内容。该行为与§9.3.182的双次读取审查一致。本节不重复登记批处理本身，而是确认延迟判定和模式提取发生在当前缓冲命令解码之后，延迟门禁触发的 `l_bError` 会被后续统一模式提取读取并覆盖模式值。

### 5. 静态结论

1. 延迟超限和负延迟分支设置 `l_bError=true`，虽暂时写入STOP模式1，但统一模式提取随后将其覆盖为ERROR模式0。
2. 上述路径进入STOP/ERROR共用停止入口，并继续执行错误处理：运动API调用、命令失效、序号/延迟复位、控制活动标志清除和控制socket重置。
3. 因此“日志写going to STOP”不代表最终模式仍为STOP，也不代表只等待下一条命令；本地通信状态会被重置。重连握手与实际控制恢复仍需动态确认。
4. `computeSequenceDelay`仅对差值小于-60000应用16位回绕修正；其余负值触发错误路径。该阈值与会话epoch缺失的交互需要组合测试。
5. 以上为固定公开VAL3源码控制流静态结论；不证明现场部署该版本、不证明现场出现序号延迟，也不证明stopMove/resetMotion已使机械臂静止。

### 6. 新增验收任务

新增SERVO-770：

| 子项 | 验收对象 | 状态 |
|---|---|---|
| AA1 | 分别注入运动中delay=5/6及静止delay=25/26，记录日志、最终l_nCmdMode、l_bError和执行分支 | 未执行 |
| AA2 | 注入负delay（-1、-59999、-60000、-60001），验证回绕修正边界及最终模式 | 未执行 |
| AA3 | 对超限分支追踪统一模式提取前后l_nCmdMode，确认STOP赋值被ERROR覆盖 | 未执行 |
| AA4 | 断言延迟超限后是否执行错误处理、清除bIsValid、重置序号并调用resetControlSocket | 未执行 |
| AA5 | 对普通STOP与延迟异常ERROR比较运动停止调用、socket状态、控制活动标志和下一条命令接受条件 | 未执行 |
| AA6 | 在mock VAL3/协议模型中注入旧命令、重复命令、跨回绕命令及短时乱序，验证错误分类 | 未执行 |
| AA7 | 验证resetControlSocket失败时错误标志重新置位后的任务行为及恢复路径 | 未执行 |
| AA8 | 将序号延迟阈值、命令接收批处理、任务overrun与状态先发送后接收组合成时序矩阵 | 未执行 |
| AA9 | 在目标CS9/VAL3版本核对任务周期、序号类型、SIO行为、socket复位及控制恢复要求 | 未确认，现场证据缺失 |
| AA10 | 获取现场控制器日志、UDP抓包、断连重连记录、STOP/ERROR状态轨迹及FAT/SAT验证记录 | 未确认，现场证据缺失 |

AA1-AA8全部未执行，AA9-AA10现场证据缺失。未执行VAL3编译/仿真、ROS集成测试、UDP故障注入、CS9/HIL、FAT/SAT或实机测试。

### 7. 结论与边界

本节新增问题是延迟保护分支的“STOP日志/赋值”与统一模式提取后的最终ERROR状态不一致，以及该ERROR路径额外重置通信会话。建议后续将STOP请求、故障锁存和通信复位拆成显式状态转移，并为每条转移建立可观测状态/回执；任何上游修复仍需用户授权。本节不提出或应用补丁。

未修改ICube/MoveIt/ros2_control上游，未应用PR；未执行动态、HIL、FAT/SAT或实机验证。目标现场版本、序号延迟测量、socket恢复策略和独立安全链仍未确认。Stäubli工程级验收未通过，`TODO-EXT-001`未授权合并。

### 固定源码链接

- https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/val3/userapp/ros2_server/controlTask.pgx
- https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/val3/userapp/ros2_server/Comm/computeSequenceDelay.pgx
- https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/val3/userapp/ros2_server/Comm/getNextSequenceNumber.pgx
- https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/val3/userapp/ros2_server/Comm/readData.pgx
- https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/val3/userapp/ros2_server/Comm/readDataOnce.pgx

## §9.3.188｜VAL3通信复位后的重新接入门禁与旧报文可达性审查

### 审查范围与固定基线

固定审查 `ICube-Robotics/staubli_driver_ros2@bd658e2d266e315d2ee35f985fb352ea88306b79`。本节承接§9.3.175、§9.3.182、§9.3.183和§9.3.187，但不重复登记16位序号回绕、双次UDP读取、旧命令缓存或socket复位本身；重点检查错误复位之后，VAL3如何重新接受第一条命令，以及ROS侧重连是否形成协议级新会话。

| 文件 | Blob SHA |
|---|---|
| Comm/resetControlSocket.pgx | 25d414065b4567c5634ef8890cc8cafd6f7e9b3e |
| controlTask.pgx | 00a69c4d13879116fce744ceb1611ecd05d65edf |
| Comm/readData.pgx | bf2e0f3d26e66724b9f656261e29fe573bd5f3b0 |
| Comm/readDataOnce.pgx | 652aa04548c814febab3c8c3fc807093261efd97 |
| Serialization/decodeRobotCommandMsg.pgx | 612f5ce9fff12c0bd6c4e90e5685ea1d4b59bcdd |
| Serialization/initRobotCommandMsg.pgx | ab254d2b65caadbacf7fa171c51994ca24f3f450 |
| start.pgx | 2d72315f0da1e18c959a24d3d75622652ee1287b |
| robot_driver.cpp | ede48a314856a455df9d8434f354aaf9fbc47bff |
| real_time_socket_subscriber.cpp | e2cd8fc50b2b13d9e31b2c024e90f9da76107622 |
| real_time_socket_interface.cpp | eda0a830cfe0118e07bc3423ad0f455bd50d610c |
| communication/udp_socket_impl.hpp | 1309a8f2d59e8295869e178af82a66868bb911ff |

### 1. VAL3复位是本地缓冲清理，不是socket重建或会话握手

`resetControlSocket.pgx`对传入SIO句柄设置timeout=-1、endOfString=10，调用`clearBuffer()`，随后将传入错误标志设为false。该函数没有关闭/重建socket、重新绑定端口、交换会话标识或等待ROS端确认。VAL3 `start.pgx`也在创建controlTask前调用一次`clearBuffer(siSocketControl)`，随后按4 ms周期创建任务。

因此，源码中的“reset”应准确理解为对既有SIO socket的参数设置和当前缓冲清理，不能称为UDP连接重新建立，也不能称为应用层重新授权握手。并且clearBuffer没有单独的结果返回值；仅从此函数无法证明控制器底层接收队列、网络中的在途数据报或远端发送队列均已清空。

### 2. controlTask重新接入的门槛仅是第一条可解码报文

§9.3.187所审查的错误处理路径会把`l_nSequenceNumber`重置为0、`l_nSequenceDelay`设为1000、`l_bControlActive`清false，并将`robot_command_msg.robotCommand.bIsValid`清false，随后调用resetControlSocket。复位成功后没有独立的WAIT_FOR_RECONNECT状态、静默等待计时器、挑战/应答、会话epoch或新连接确认；源码中的“before accepting new commands”延时仍明确标为TODO。

主循环下一轮继续调用readData。只要收到完整报文，`decodeRobotCommandMsg`通过Header解码及message type=2检查、完成固定字段解码后就会将`bIsValid`设为true；同一轮`l_bNewCmdMessage`为true且`l_bControlActive`为false时，控制任务直接把控制活动标志设true并记录“connection to controller established”。没有第二阶段握手或独立的重新授权判定。命令模式提取随后直接读取该报文的`nMotionCmdType`，满足其他现有门禁时即可进入运动控制分支。

这证明公开原型的重新接入条件是“收到并解码一条完整RobotCommand报文”，不是“确认来自一个新的ROS会话”。但是否会造成具体旧命令执行，仍取决于报文到达时序、序号差、机器人运动快照和目标VAL3运行时行为，需由隔离仿真/故障注入验证。

### 3. clearBuffer之后的在途旧报文与序号回绕存在待验证交叉窗口

`clearBuffer()`只能作为本地接收缓冲清理证据；固定源码没有应用层session ID/nonce或发送端代际标识。若旧UDP数据报在清理动作之后才到达，它在报文结构上仍可能满足同一RobotCommand类型和长度检查。重新接入时，VAL3本地状态序号已从0重新开始，而ROS端命令序号由最近收到的RobotState序号回显；该组合可能将旧会话报文与新会话序号空间混淆。

例如，在仅用于设计测试的边界模型中，若复位后VAL3最新状态序号为1，而延迟到达的旧命令序号为65530，`computeSequenceDelay`按16位回绕解释可得到7；静止状态门槛为大于25才触发错误，因此该数值在静止快照下不会仅因延迟阈值而被拒绝。该算例不是现场观测，也不证明该包会实际进入SIO或被执行；它说明不能把clearBuffer和序号回绕算法视为会话隔离机制。运动快照下阈值更严格（>5），但仍不能替代epoch/握手验证。

### 4. ROS侧connect/disconnect也未建立协议级会话代际

`RobotDriver::connect()`创建新的RealTimeSocketInterface/Subscriber，等待至少一条有效RobotState，并检查协议版本；`disconnect()`销毁接口、停止接收线程、断开UDP socket并调用reset_data()。新subscriber构造时`first_read_`初始化为true，RobotDriver::reset_data()将last_valid_sequence_id_清零并使当前状态Header类型无效。这是ROS进程本地对象/缓存重置。

但ROS侧命令发送仍只是`send_robot_command()`调用control_interface_->send_message()；硬件接口命令序号从最近有效RobotState序号取得。没有向VAL3发送独立session nonce、握手挑战或重新授权消息。UDP接收端的sender_endpoint来源地址验证仍为TODO注释；本节不据此推断现场存在外部攻击，只记录固定原型尚无该过滤门禁。

### 5. 静态结论与风险边界

1. resetControlSocket执行本地SIO参数设置和clearBuffer，不执行socket关闭/重建或协议级会话握手。
2. VAL3错误复位后清除了本地命令有效位和控制活动标志，但下一条完整且可解码的命令即可重新置位控制活动标志；显式重连授权、静默等待和新会话标识均未见实现。
3. ROS disconnect/connect重建本地UDP接收对象并等待RobotState，但没有与VAL3进行会话代际同步；命令序号继续回显最新状态序号。
4. 清理动作之后到达的旧数据报是否能进入新会话，受UDP在途包、SIO缓冲、任务周期和序号窗口影响。固定源码支持“缺少协议级排除门禁”的判断，不足以证明某个旧包必然被执行。
5. `readDataOnce`对完整长度报文才置newData；部分报文错误路径及零/负返回值边界已在§9.3.182登记，本节不重复作为新发现。
6. 以上仅是固定公开原型静态控制流和跨层接口审查，不证明现场部署该版本，不证明现场发生旧命令重放，也不证明机械臂停止或安全链状态。

### 6. 新增验收任务

新增SERVO-771：

| 子项 | 验收对象 | 状态 |
|---|---|---|
| AB1 | 在mock VAL3中于clearBuffer前、执行期间、执行后分别注入旧RobotCommand，记录接收/解码/执行路径 | 未执行 |
| AB2 | 验证复位后无报文、STOP报文、位置命令、速度命令及错误类型报文的首包行为 | 未执行 |
| AB3 | 对复位后状态序号1/2/25/26及旧命令序号65530/65535/0/1组合测试回绕和延迟门禁 | 未执行 |
| AB4 | 在静止与运动快照下分别注入延迟旧命令，记录最终模式、bIsValid、l_bControlActive及运动更新调用 | 未执行 |
| AB5 | 在clearBuffer调用前后安排UDP在途包/延迟包，验证VAL3 SIO接收缓冲与任务周期竞态 | 未执行 |
| AB6 | 验证resetControlSocket失败、clearBuffer运行时异常或socket不可用时错误标志与控制任务行为 | 未执行 |
| AB7 | ROS disconnect→connect后验证新subscriber首帧、状态序号重置、命令序号回显与旧数据隔离 | 未执行 |
| AB8 | 设计并验证协议级session epoch/nonce或等价重同步门禁；未实现前以测试证明旧会话报文被拒绝 | 未执行 |
| AB9 | 核对目标CS9/VAL3版本的SIO clearBuffer语义、UDP接收队列语义、任务调度和应用部署配置 | 未确认，现场证据缺失 |
| AB10 | 获取现场抓包、VAL3日志、ROS reconnect日志、序号轨迹、故障恢复记录及FAT/SAT验收证据 | 未确认，现场证据缺失 |

AB1-AB8全部未执行，AB9-AB10现场证据缺失。未执行VAL3编译/仿真、ROS构建/集成、UDP延迟/乱序/重放注入、CS9/HIL、FAT/SAT或实机测试。

### 7. 结论与边界

本节新增的交叉风险是：两端本地socket/缓存重置与应用层新会话建立之间缺少可见的协议级握手/代际门禁。建议后续在隔离环境验证旧包可达性，并由具备目标控制器经验的工程团队评估增加session epoch/nonce、首包STOP/显式授权、序号基线同步及复位后的稳定等待策略；不能把固定延时当作安全功能，也不能未经验证直接修改现场控制程序。本节不提出或应用上游补丁。

未修改ICube/MoveIt/ros2_control上游，未应用PR；未执行动态、HIL、FAT/SAT或实机验证。目标现场版本、网络拓扑、CS9 SIO行为和独立安全链仍未确认。Stäubli工程级验收未通过，`TODO-EXT-001`未授权合并。

### 固定源码链接

- https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/val3/userapp/ros2_server/Comm/resetControlSocket.pgx
- https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/val3/userapp/ros2_server/controlTask.pgx
- https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/val3/userapp/ros2_server/Comm/readData.pgx
- https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/val3/userapp/ros2_server/Comm/readDataOnce.pgx
- https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/val3/userapp/ros2_server/Serialization/decodeRobotCommandMsg.pgx
- https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/val3/userapp/ros2_server/Serialization/initRobotCommandMsg.pgx
- https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/val3/userapp/ros2_server/start.pgx
- https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/src/robot_driver.cpp
- https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/src/real_time_socket_subscriber.cpp
- https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/src/real_time_socket_interface.cpp
- https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/src/communication/udp_socket_impl.hpp

## §9.3.189｜VAL3通信复位错误传播、控制任务存活与恢复状态一致性

### 审查范围与固定基线

固定审查 `ICube-Robotics/staubli_driver_ros2@bd658e2d266e315d2ee35f985fb352ea88306b79`。本节承接§9.3.187–188，但不重复讨论序号延迟阈值和协议握手缺失；聚焦resetControlSocket的错误输出契约、controlTask调用方分支、初始化失败退出与运行期错误复位的控制流。

| 文件 | Blob SHA |
|---|---|
| Comm/resetControlSocket.pgx | 25d414065b4567c5634ef8890cc8cafd6f7e9b3e |
| controlTask.pgx | 00a69c4d13879116fce744ceb1611ecd05d65edf |
| start.pgx | 2d72315f0da1e18c959a24d3d75622652ee1287b |
| ros2_server.dtx | 558dc2db671da45f5b859a3526148ce816eb6dd4 |
| configs/sio.cfx | 76ad0c9f4b1902f26f21ea08eed0ef5f16e63d9e |
| stop.pgx | 8d88991f087ea2be2e65daacff742da5d58ac73c |

### 1. resetControlSocket的错误输出在正常返回路径上被无条件清零

`resetControlSocket.pgx`的顺序是：对传入SIO句柄执行`sioCtrl(timeout,-1)`、`sioCtrl(endOfString,10)`、`clearBuffer()`，然后无条件执行`x_bError=false`并返回。该程序没有检查上述操作的返回值，也没有局部错误捕获/错误码映射路径。

调用方`controlTask.pgx`在初始化阶段调用该程序后检查`l_bErrorTmp`，运行期错误复位后也检查同一个输出标志；但只要resetControlSocket正常走到末尾，输出就必然为false。因此，这两个调用方分支不能从该函数获得“sioCtrl或clearBuffer失败”的普通错误返回证据。这里确认的是VAL3程序层面的输出契约缺口；不能据此断言内建SIO操作在所有目标固件上的失败行为，也不能排除运行时异常会中止/终止任务。

### 2. 初始化失败与运行期复位失败的处理路径不对称

controlTask启动时先初始化状态消息和命令消息；若对应初始化程序通过输出标志报告失败，controlTask设置`l_bError=true`、记录错误并直接`return`。socket初始化也有相同形式的检查，但由于resetControlSocket无条件清零输出标志，普通返回路径下该检查无法识别其内部SIO设置/清缓冲失败。

运行期错误处理则先执行停止/复位动作，将命令模式置为ERROR，随后清除`l_bError`、重置序号和延迟、清除控制活动和命令有效标志，再调用resetControlSocket。只有当该函数返回true错误标志时才重新置`l_bError=true`。按当前函数实现，该分支同样无法捕获其内部操作失败的普通返回状态。之后controlTask没有显式重建socket、重新创建自身任务或进入独立的FAULT_LATCHED状态；而是继续完成本周期并进入下一轮循环。

### 3. 错误恢复没有独立的任务级监督/重启机制

`start.pgx`设置4 ms周期，调用`taskCreateSync "controlTask"...`启动控制任务；同一文件中的“supervision/diagnostics task”仍标记TODO。仓库可见的启动路径没有展示独立看门狗对controlTask退出、卡死或持续复位失败进行检测并重启的实现。不能从单一调用点推断VAL3任务调度器的全部生命周期语义；本节仅记录应用层可见代码未提供监督任务/重启状态机。

`ros2_server.dtx`将`siSocketControl`链接到`UdpSocket\control`；`sio.cfx`配置control UDP socket的远端地址、端口、timeout和quietTime。当前审查未获得目标CS9的SIO运行时错误语义或现场部署配置，故不能把配置文件中的静态参数当作实际运行时socket健康证明。

### 4. 停止入口与运行期错误复位的差异

`stop.pgx`执行`stopMove()`、`resetMotion()`和`clearBuffer(siSocketControl)`后结束；它不调用resetControlSocket，不更新controlTask内部错误标志/命令有效标志/序号，也不展示等待controlTask退出或确认任务停止的逻辑。因此stop入口的缓冲清理与controlTask内部错误复位不是同一套状态转换。是否存在外层调用顺序保证、任务停止同步或并发访问保护，需要结合完整VAL3应用入口及目标控制器任务语义继续核验。

### 5. 静态结论与风险边界

1. resetControlSocket在正常返回路径上无条件将错误输出置false，调用方无法通过该输出区分内部SIO参数设置/clearBuffer是否失败。
2. controlTask初始化阶段对状态/命令消息初始化失败会直接return；socket复位错误检查在当前helper实现下不具备有效的普通失败传播。
3. 运行期错误复位先清除本地错误锁存和命令/活动状态，再尝试resetControlSocket；若helper正常返回，任务继续进入下一周期，而源码没有独立FAULT_LATCHED、socket重建或任务重启流程。
4. start.pgx的supervision/diagnostics task仍为TODO；应用层可见代码没有展示controlTask watchdog或自动重启监督器。VAL3调度器自身行为不在本节可证明范围。
5. stop.pgx仅停止运动并clearBuffer，与controlTask错误复位的内部状态清理不同；其与控制任务的并发/生命周期关系需受控验证。
6. 上述是固定公开原型静态控制流结论，不证明现场SIO调用失败、controlTask已经退出/卡死、机器人仍在运动或安全链失效。

### 6. 新增验收任务

新增SERVO-772：

| 子项 | 验收对象 | 状态 |
|---|---|---|
| AC1 | 对sioCtrl(timeout)、sioCtrl(endOfString)、clearBuffer分别注入成功/失败/运行时异常，确认VAL3输出错误标志和任务行为 | 未执行 |
| AC2 | 验证resetControlSocket是否应先将x_bError置true，并仅在所有复位步骤成功后清false；对每一步失败检查错误传播 | 未执行 |
| AC3 | 验证controlTask启动时状态消息、命令消息和socket初始化失败的return、任务状态及start调用方可观测性 | 未执行 |
| AC4 | 运行期注入复位失败，验证l_bError、l_bControlActive、bIsValid、序号、命令模式及下一周期状态报文 | 未执行 |
| AC5 | 连续复位失败/间歇成功时验证是否出现无限重试、日志风暴、任务周期超限或错误状态闪断 | 未执行 |
| AC6 | 验证controlTask退出、异常终止或不再按期运行时是否存在独立监督器检测、报警和受控重启 | 未执行 |
| AC7 | 验证stop.pgx与controlTask并发执行时的stopMove/resetMotion/clearBuffer顺序、任务退出同步和socket访问竞争 | 未执行 |
| AC8 | 核对目标CS9/VAL3版本中sioCtrl、clearBuffer错误语义、任务异常处理与taskCreateSync生命周期定义 | 未确认，现场证据缺失 |
| AC9 | 获取现场任务状态、VAL3日志、SIO错误记录、控制器版本及复位故障恢复证据 | 未确认，现场证据缺失 |
| AC10 | 在隔离仿真/HIL中完成复位故障注入、恢复/退出路径和安全状态回归验收 | 未执行，需受控环境 |

AC1-AC7、AC10未执行；AC8-AC9现场证据缺失。未执行VAL3编译/仿真、ROS集成、CS9/HIL、FAT/SAT或实机测试。

### 7. 结论与边界

本节新增问题是“复位函数错误输出契约与调用方失败处理不闭合”，以及“应用层未见独立控制任务监督/重启状态机”。建议先在目标VAL3版本确认内建SIO操作的失败语义，再设计可观测、可锁存的复位失败状态和外部监督策略；不得在未经风险分析与受控验证的情况下直接修改现场运动控制程序。未提出或应用上游补丁。

未修改ICube/MoveIt/ros2_control上游，未应用PR；未执行动态、HIL、FAT/SAT或实机验证。目标现场版本、SIO失败语义、任务调度语义、网络拓扑及独立安全链仍未确认。Stäubli工程级验收未通过，`TODO-EXT-001`未授权合并。

### 固定源码链接

- https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/val3/userapp/ros2_server/Comm/resetControlSocket.pgx
- https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/val3/userapp/ros2_server/controlTask.pgx
- https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/val3/userapp/ros2_server/start.pgx
- https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/val3/userapp/ros2_server/stop.pgx
- https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/val3/userapp/ros2_server/ros2_server.dtx
- https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/val3/configs/sio.cfx


## §9.3.190｜VAL3启动前置条件检查、monitor speed与控制周期性能门禁

### 审查范围与固定基线

固定审查 `ICube-Robotics/staubli_driver_ros2@bd658e2d266e315d2ee35f985fb352ea88306b79`。本节不重复§9.3.176已登记的任务创建/停止同步、ROS lifecycle解耦和版本元数据问题，也不重复§9.3.169的overrun计数；本节只检查start入口在创建4 ms控制任务前读取的运行条件，是否形成真正的启动准入门禁，以及相关性能参数是否有范围/异常处理。

| 文件 | Blob SHA |
|---|---|
| `start.pgx` | `2d72315f0da1e18c959a24d3d75622652ee1287b` |
| `ros2_server.pjx` | `b58dbbf1daf778da64e4ff9551d890ee9ec8514b` |
| `ros2_server.dtx` | `558dc2db671da45f5b859a3526148ce816eb6dd4` |
| `configs/sio.cfx` | `76ad0c9f4b1902f26f21ea08eed0ef5f16e63d9e` |

### 1. monitor speed低于100%时仅告警，不阻止启动

`start.pgx`调用`getMonitorSpeed()`；若返回值小于100，只写入一条Warning日志。原本用于弹窗提示和等待monitor speed恢复100%的`popUpMsg`与`wait(getMonitorSpeed() == 100)`均被注释。该条件分支结束后程序继续清理socket、执行运动初始化、开启`autoConnectMove(true)`并调用`taskCreateSync`创建控制任务。固定源码没有将monitor speed不足转换为启动失败返回，也没有将该条件锁存为运行期运动许可状态。

所以静态代码证明的是“低于100%时会告警但仍继续启动流程”，不是“目标控制器实际以低速运行”或“运动控制必然失稳”。注释中关于控制算法可能无法正确工作的文字是源码作者的风险提示；其量化影响、适用控制器模式和实际性能阈值仍需目标CS9版本文档及测量确认。

### 2. boxcar delay仅采样并记录，没有阈值或闭环调整

入口读取`$getBoxcarDelay()`并记录数值；相邻的`$setBoxcarFreq(60.0)`调用被注释。代码没有对delay设置允许范围、最大值、异常值处理或启动拒绝条件，也没有根据读取结果调整4 ms控制周期。该读取结果只用于日志，不能视为完成滤波器配置校验或补偿。

### 3. 4 ms周期配置与启动前置条件未建立可验证关联

在上述读取/告警后，入口固定设置`l_nCtrlPeriod=0.004`并调用`taskCreateSync`。当前可见逻辑没有计算boxcar delay相对4 ms周期的比例、没有根据monitor speed/滤波延迟调整周期，也没有在创建任务前进行周期预算或启动性能验收。工程配置中的控制UDP socket timeout为`-0.001`、quietTime为`30`，这些静态配置不构成任务周期抖动或通信时延测量证据。

本节只确认VAL3入口没有实现上述前置条件到周期配置的显式门禁/关联；不推断boxcar delay的单位、内部滤波器精确响应或CS9调度器最坏执行时间。相关API语义须由适用版本手册确认。

### 4. 静态结论与边界

1. monitor speed低于100时，固定原型仅记录Warning；等待/阻塞动作被注释，后续启动流程仍继续。
2. boxcar delay只读取并写日志；滤波器频率设置调用被注释，没有阈值、合法范围或异常分支。
3. 控制周期固定为4 ms，入口没有把monitor speed或boxcar delay与周期预算关联，也没有启动前性能验收结果门禁。
4. 这些是启动入口静态控制流结论，不证明现场monitor speed低于100、boxcar滤波器配置异常、控制周期超限或机器人控制失稳。
5. 需要在目标CS9/VAL3版本确认API返回单位/范围、monitor speed实际语义、boxcar delay测量方式、任务周期抖动和运动控制影响；未取得证据前不得把4 ms配置值写成实测控制周期或安全响应时间。

### 5. 新增验收任务

新增SERVO-773：

| 子项 | 验收对象 | 状态 |
|---|---|---|
| AD1 | 在隔离仿真中分别设置monitor speed为100、低于100及运行中变化，确认start日志、等待行为和任务创建是否一致 | 未执行 |
| AD2 | 证明monitor speed低于100时start是否仍执行clearBuffer、stopMove、resetMotion、autoConnectMove和taskCreateSync完整后续路径 | 未执行 |
| AD3 | 核对目标CS9/VAL3版本getMonitorSpeed返回值范围、更新时序、异常/不可用返回语义 | 未确认，现场版本证据缺失 |
| AD4 | 对boxcar delay设置多个合法/边界/异常配置，记录$getBoxcarDelay单位、数值稳定性和日志格式 | 未执行 |
| AD5 | 核对$getBoxcarDelay与$setBoxcarFreq的目标版本API契约，并确认当前未调用setBoxcarFreq是否符合现场配置要求 | 未确认，现场版本证据缺失 |
| AD6 | 测量boxcar delay与4 ms任务周期、端到端状态/命令时延之间的关系，建立有单位和采样条件的预算 | 未执行 |
| AD7 | 在monitor speed变化和滤波延迟变化组合下测量taskCreateSync周期抖动、overrun计数及状态报文间隔 | 未执行 |
| AD8 | 验证前置条件不满足时是否应阻止创建控制任务，并定义可观测、可恢复的启动失败状态 | 未执行，需工程安全评审 |
| AD9 | 核对现场控制器型号、CS9/VAL3版本、monitor speed设置、boxcar配置、任务周期和运行日志 | 未确认，现场证据缺失 |
| AD10 | 在隔离仿真/HIL中完成启动前置条件边界、性能回归及安全状态验证 | 未执行，需受控环境 |

AD1-AD2、AD4、AD6-AD8、AD10未执行；AD3、AD5、AD9现场版本/配置证据缺失。未执行VAL3编译/仿真、ROS集成、CS9/HIL、FAT/SAT或实机验证。

### 6. 结论与工程建议

建议将启动前置条件拆分为“可观测诊断值”和“必须满足的准入条件”，明确monitor speed与boxcar delay的目标版本语义、单位、范围和失效策略；只有在工程风险评审确定阈值后，才定义阻止启动或降级运行的行为。对4 ms控制周期应提供目标控制器上的周期分布、overrun、通信时延和滤波延迟证据，不应仅凭静态配置认定实时性能达标。本节没有提出未经验证即可直接部署的VAL3程序改动。

未修改ICube/MoveIt/ros2_control上游，未应用PR；未执行动态、HIL、FAT/SAT或实机验证。现场控制器型号、CS9/VAL3版本、monitor speed语义、boxcar delay单位/范围、滤波配置和独立安全链仍未确认。Stäubli工程级验收未通过，`TODO-EXT-001`未授权合并。

### 固定源码链接

- `https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/val3/userapp/ros2_server/start.pgx`
- `https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/val3/userapp/ros2_server/ros2_server.pjx`
- `https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/val3/userapp/ros2_server/ros2_server.dtx`
- `https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/val3/configs/sio.cfx`


## §9.3.191｜VAL3控制任务停止标志可达性、重复启动与启停残留状态

### 审查范围与固定基线

固定审查 `ICube-Robotics/staubli_driver_ros2@bd658e2d266e315d2ee35f985fb352ea88306b79`。本节承接§9.3.176、§9.3.189及§9.3.190：不重复ROS lifecycle与VAL3入口解耦、socket复位错误传播或启动性能前置条件；本节聚焦控制任务退出条件是否可由stop入口触发、重复start是否有应用层防重入门禁，以及stop→start之间的任务/通信状态边界。

| 文件 | Blob SHA |
|---|---|
| `start.pgx` | `2d72315f0da1e18c959a24d3d75622652ee1287b` |
| `stop.pgx` | `8d88991f087ea2be2e65daacff742da5d58ac73c` |
| `controlTask.pgx` | `00a69c4d13879116fce744ceb1611ecd05d65edf` |
| `ros2_server.pjx` | `b58dbbf1daf778da64e4ff9551d890ee9ec8514b` |

### 1. controlTask退出条件是局部变量，公开程序内没有停止写入点

`controlTask.pgx`将`l_bStopControlTask`声明为该Program的Local bool，并在入口处设置为`false`。主循环条件为`while !l_bStopControlTask`；退出循环后的清理代码才执行日志、`stopMove()`和`resetMotion()`。

对固定仓库执行精确源码搜索，`l_bStopControlTask`仅命中该局部声明和入口初始化，没有命中后续赋值。对`taskStatus`、`taskKill`和`taskStop`的源码搜索没有找到调用点。由于该停止标志是Program局部变量，独立的`stop.pgx`不能仅凭同名程序上下文直接写入该局部状态；固定源码也没有展示参数、共享数据或任务API将stop入口连接到该退出条件。

因此，在公开应用层可见控制流中，stop入口没有触发controlTask正常离开while循环的显式机制。此结论不排除VAL3运行时、示教器操作或部署工程存在仓库未收录的外部任务管理行为。

### 2. stop.pgx执行运动/缓冲操作，但没有控制任务退出同步

`stop.pgx`按顺序执行`stopMove()`、`resetMotion()`和`clearBuffer(siSocketControl)`后结束。没有看到它设置controlTask的停止标志、调用任务状态/终止API、等待任务退出、等待退出清理完成或确认任务已停止。

与此同时，controlTask主循环在每周期完成状态发布、命令接收/解码、模式判断及运动/GPIO处理后继续下一轮；退出清理仅位于while循环之后。故不能把stop.pgx返回等同于controlTask已退出，也不能把缓冲区清理等同于控制任务停止接收后续报文。

### 3. start.pgx没有应用层重复启动防护

`start.pgx`每次进入都会执行socket缓冲清理、`stopMove()`、`resetMotion()`、`autoConnectMove(true)`，将`bIsOverrun=false`，再调用`taskCreateSync "controlTask", l_nCtrlPeriod, bIsOverrun, controlTask()`。固定程序中没有在该调用前检查同名任务是否已经存在/运行，也没有应用层启动互斥锁或“已启动”状态门禁。

因此，静态源码只能确认每次start入口都会到达taskCreateSync调用点；同名任务已存在时VAL3运行时究竟拒绝、替换、并行创建、报错还是采用其他行为，必须由目标版本API契约和控制器实测确认。不能据此直接断言重复start会产生两个并行controlTask。

### 4. stop→start之间的状态清理存在跨任务时序问题待验证

controlTask每次实际进入程序时会重新初始化局部错误标志、控制活动标志、序号、延迟和命令模式，并调用resetControlSocket；start入口则在taskCreateSync之前清理socket缓冲并复位运动。若前一次controlTask仍在运行而再次调用start，两个入口可能在同一socket、共享overrun标志和运动控制资源上发生交错；具体是否发生取决于taskCreateSync对同名任务的语义、任务调度时序及VAL3资源访问规则。

stop入口清理缓冲之后，若controlTask仍在运行，它仍处于主循环中；之后抵达的新报文是否会被该任务读取并执行，需要隔离环境验证。当前静态源码不足以证明该竞态在现场发生，也不足以证明start/stop调用顺序已由外部流程严格串行化。

### 5. 静态结论与边界

1. `l_bStopControlTask`是controlTask局部变量；固定程序中只见入口置false和while条件读取，没有后续置true的源码写入点。
2. stop.pgx只调用stopMove、resetMotion和clearBuffer，没有显式终止/等待controlTask，也没有确认任务退出后的清理完成。
3. start.pgx每次调用都会到达taskCreateSync；未见应用层同名任务存在性检查、启动互斥或已启动状态门禁。
4. 固定仓库搜索未发现taskStatus、taskKill、taskStop调用；这只代表公开仓库代码未展示这些API，不代表VAL3运行时或现场工程不存在其他任务管理方式。
5. ros2_server.pjx将start.pgx、stop.pgx和controlTask.pgx列为同一VAL3项目程序；未从项目清单获得外部启动/停止调用者及现场操作流程。
6. 本节不推断taskCreateSync同名任务冲突语义、不推断stopMove/resetMotion使任务退出、不推断stop后机器人必然继续运动，也不证明现场重复start/stop竞态已经发生。

### 6. 新增验收任务

新增SERVO-774：

| 子项 | 验收对象 | 状态 |
|---|---|---|
| AE1 | 在目标CS9/VAL3版本中分别于任务不存在、正在运行、已退出时调用start，记录taskCreateSync返回/异常/任务表变化 | 未执行 |
| AE2 | 对同名controlTask重复调用taskCreateSync，确认运行时是拒绝、替换、并行创建还是其他行为，并记录错误码 | 未确认，目标版本API证据缺失 |
| AE3 | 在隔离工程中验证Program Local变量作用域，确认stop入口不能直接改变controlTask的l_bStopControlTask，并追踪所有可写路径 | 未执行 |
| AE4 | controlTask运行期间调用stop，记录任务是否继续循环、是否继续收发UDP、是否执行退出清理段 | 未执行 |
| AE5 | 连续执行start→start、start→stop→start、start→stop→stop，记录任务实例数量、任务状态、socket访问和运动API调用顺序 | 未执行 |
| AE6 | 核对目标VAL3版本任务状态查询/停止/删除API的准确名称、作用域、同步语义和异常处理契约 | 未确认，目标版本文档缺失 |
| AE7 | 在消息初始化失败、socket初始化失败、运行时异常及正常退出条件下，验证controlTask return/loop exit与start调用方可观测性 | 未执行 |
| AE8 | 对stop清缓冲前后注入旧报文和新报文，验证仍存活controlTask的接收、解码、命令模式与运动更新路径 | 未执行 |
| AE9 | 获取现场VAL3项目启动映射、示教器/远程调用记录、任务表快照、控制器型号及版本，确认实际启停编排 | 未确认，现场证据缺失 |
| AE10 | 在隔离仿真/HIL中完成重复启停、并发时序、任务退出确认及独立安全状态回归验收 | 未执行，需受控环境 |

AE1、AE3-AE5、AE7-AE8、AE10未执行；AE2、AE6目标版本API证据缺失；AE9现场证据缺失。以上均为验收设计，不代表测试已通过。

### 7. 结论与工程建议

在目标VAL3版本明确taskCreateSync的同名任务语义前，不应假设重复start是幂等操作。建议先定义唯一的任务生命周期状态机，并由经版本确认的任务管理接口实现“启动前检查—启动结果确认—停止请求—退出确认—资源清理—允许重启”的闭环；停止标志应通过经验证的共享/参数接口提供受控写入，不应尝试从外部直接访问Program Local变量。任何改动均须先做风险评审、仿真与受控安全验证，本节没有提出可直接部署的程序补丁。

未修改ICube/MoveIt/ros2_control上游，未应用PR；未执行VAL3编译/仿真、ROS集成、CS9/HIL、FAT/SAT或实机验证。目标控制器型号、CS9/VAL3版本、taskCreateSync重复任务语义、现场启动映射和独立安全链仍未确认。Stäubli工程级验收未通过，`TODO-EXT-001`未授权合并。

### 固定源码链接

- `https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/val3/userapp/ros2_server/start.pgx`
- `https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/val3/userapp/ros2_server/stop.pgx`
- `https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/val3/userapp/ros2_server/controlTask.pgx`
- `https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/val3/userapp/ros2_server/ros2_server.pjx`


## §9.3.192｜VAL3启动初始化、overrun计数器与诊断字段可观测性

### 审查范围与固定基线

固定上游提交：`ICube-Robotics/staubli_driver_ros2@bd658e2d266e315d2ee35f985fb352ea88306b79`。本节承接§9.3.189–191，重点检查启动入口与控制任务主体之间的初始化时序、全局诊断字段的写入/清零位置，以及这些字段是否进入ROS状态协议。避免重复审查controlTask退出条件和taskCreateSync同名任务语义。

| 文件 | Blob SHA |
|---|---|
| `start.pgx` | `2d72315f0da1e18c959a24d3d75622652ee1287b` |
| `controlTask.pgx` | `00a69c4d13879116fce744ceb1611ecd05d65edf` |
| `ros2_server.dtx` | `558dc2db671da45f5b859a3526148ce816eb6dd4` |
| `ros2_server.pjx` | `b58dbbf1daf778da64e4ff9551d890ee9ec8514b` |
| `Serialization/initRobotCommandMsg.pgx` | `ab254d2b65caadbacf7fa171c51994ca24f3f450` |
| `Serialization/initRobotStateMsg.pgx` | `211f052f6df8c4dd73f68aed6979a0163992f25b` |
| `Serialization/encodeRobotStateMsg.pgx` | `0dadb0cc7f03de3da165cafa86fa5f943f097ec3` |
| `Serialization/decodeRobotCommandMsg.pgx` | `612f5ce9fff12c0bd6c4e90e5685ea1d4b59bcdd` |
| `Types/RobotStateMsg/RobotStateMsg.dtx` | `ef79e0f3ae502940a338d8f12ffcda5bad836d99` |

项目清单`ros2_server.pjx`声明VAL3参数版本字符串为`s8.20.2Cs9_BS4270`。这是仓库项目元数据，不等同于现场控制器已安装/运行该版本。

### 1. start入口与controlTask主体的初始化时序

`start.pgx`在调用`taskCreateSync`之前先执行`bIsOverrun=false`，随后以`l_nCtrlPeriod=0.004`创建`controlTask`。入口本身没有对`nOverruns`、`nErrorCode`或`nInError`赋值。

`controlTask.pgx`主体开始后依次将局部错误状态、控制活动标志、序号和延迟初始化，并将全局`nOverruns=0`。因此，overrun计数器的清零发生在任务实际进入主体之后，而不是start入口调用taskCreateSync之前。若任务创建/启动失败或主体未运行，不能从start入口代码推定nOverruns已完成本轮清零；taskCreateSync失败如何返回/报告仍需目标VAL3版本API契约确认。

### 2. overrun标志与计数器的实际数据流

`ros2_server.dtx`声明公共全局`bIsOverrun`，默认值为true；start入口将其设为false后创建周期任务。controlTask每轮检查该标志，若为true则写入Warning日志、将标志清false并对`nOverruns`加一。

这形成“调度器/任务周期机制提供overrun标志—controlTask消费并清零—累计计数”的应用层数据流。公开程序没有看到nOverruns的周期性复位或限幅，也没有看到其被写入RobotState消息。若overrun发生在任务主体开始前、任务不再运行或任务停止消费标志，计数器和标志的行为需要目标运行时验证；静态代码不能证明每个超周期都会被准确计数一次。

### 3. 公开诊断字段没有形成已实现的应用层故障接口

`ros2_server.dtx`还声明公共全局`nErrorCode`和`nInError`，但对固定提交全仓精确检索未找到这两个字段在程序中的读写调用点。它们也没有出现在本节检查的RobotState序列化字段中。

`nOverruns`虽被controlTask清零和递增，但同样未见被编码进RobotState报文。状态编码器发送的是状态延迟、控制/安全/机器人模式、状态标志、有效字段标志、关节数据和预留传感器/IO字段；没有nOverruns、nErrorCode或nInError字段。故不能把这些公共VAL3数据声明视为ROS驱动可直接消费的诊断遥测。

此结论限定于固定仓库中的VAL3应用程序和公开ROS状态协议。控制器示教器、外部诊断工具或未纳入仓库的工程程序可能读取公共变量，不能据此断言现场完全无法观察这些数据。

### 4. 消息初始化与控制任务局部状态的边界

`initRobotCommandMsg.pgx`初始化Header、消息类型和payload长度，分配序列化缓冲区，将远程控制周期设为-1、运动命令类型设为STOP、六轴运动数据清零，并将命令有效标志设为false。数字输出/模拟输出数组在数据类型中声明，但初始化程序没有逐元素赋初值；解码程序会填充模拟输出值，数字输出mask转数组的代码仍为注释，controlTask中的GPIO输出执行也仍为TODO。不能据此认定这些字段已经驱动现场IO；数组初值和后续使用必须单独验证。

`initRobotStateMsg.pgx`初始化Header、状态消息类型及payload长度，并将RobotState有效标志设为false；实际状态字段随后由每周期`updateState`填充。该初始化程序没有把nOverruns/nErrorCode/nInError映射到状态消息。

controlTask中的`l_bError`、`l_bControlActive`、序号及命令状态均为局部变量，每次任务主体开始会重新初始化；全局诊断数据则具有不同生命周期。重启后局部状态重置、全局计数器清零发生在任务主体入口，而start先清overrun flag再请求创建任务，二者存在可观察时序差异。

### 5. 静态结论与边界

1. start.pgx在taskCreateSync前将bIsOverrun置false，但没有清零nOverruns/nErrorCode/nInError。
2. controlTask主体进入后将nOverruns置0；每轮检测bIsOverrun为true时清false并递增nOverruns。
3. ros2_server.dtx将nErrorCode/nInError声明为public，但固定提交的应用程序没有找到读写点；其运行时初值不能仅凭未显式配置推定。
4. nOverruns没有被本节检查的RobotState编码器序列化，也没有在公开状态报文中对应字段。
5. 项目清单记录VAL3参数版本字符串s8.20.2Cs9_BS4270；现场实际部署版本仍未知。
6. 本节不推断taskCreateSync创建失败的具体返回语义、不推断计数器在现场的实际值，也不推断控制器不存在其他外部诊断通道。

### 6. 新增验收任务

新增SERVO-775：

| 子项 | 验收对象 | 状态 |
|---|---|---|
| AF1 | 对固定版本完整检索bIsOverrun、nOverruns、nErrorCode、nInError的全部读写点，并与实际VAL3项目打包内容核对 | 静态审查完成；现场包核对未执行 |
| AF2 | 在目标CS9/VAL3版本中分别验证taskCreateSync成功、拒绝、异常返回时，start调用方可观察结果及全局标志变化 | 未确认，目标版本API证据缺失 |
| AF3 | 任务主体进入前后读取nOverruns，验证清零发生点、重复start/任务重建后的保留与复位行为 | 未执行 |
| AF4 | 注入单次、连续和相邻周期overrun，验证bIsOverrun清除时序、nOverruns增量准确性及计数器溢出/饱和行为 | 未执行 |
| AF5 | 验证nOverruns能否通过示教器、VAL3诊断接口或外部工具读取，并记录读取权限、刷新周期和时间戳 | 未确认，现场工具/权限证据缺失 |
| AF6 | 验证nErrorCode/nInError在冷启动、正常启动、初始化失败和运行故障后的实际初值及更新路径 | 未执行 |
| AF7 | 对照RobotState协议定义、编码器和ROS反序列化端，验证overrun/error诊断字段是否被明确排除或另有独立遥测通道 | 未执行 |
| AF8 | 验证消息初始化失败或controlTask未进入主体时，start入口、任务状态、nOverruns及日志之间的可观测关联 | 未执行 |
| AF9 | 获取现场控制器型号、CS9/VAL3实际版本、项目部署包SHA、任务日志及诊断变量快照 | 未确认，现场证据缺失 |
| AF10 | 在隔离仿真/HIL中完成任务创建失败、周期超限、计数器恢复及诊断遥测回归验证 | 未执行，需受控环境 |

AF1固定仓库静态检索已完成；AF1现场部署包核对、AF3-AF4、AF6-AF8、AF10未执行；AF2目标版本API证据缺失；AF5诊断工具/权限证据缺失；AF9现场证据缺失。上述状态不代表动态测试通过。

### 7. 工程建议与验收边界

建议把诊断数据明确分层：任务调度事件计数、应用错误码、当前故障状态、状态报文遥测及现场日志应分别定义数据所有者、复位策略、有效性、时间戳和读取接口。若nOverruns需要被ROS侧监控，应通过经评审的协议扩展或独立诊断接口提供，不能把VAL3 public变量声明等同于ROS遥测。对nErrorCode/nInError应明确是未实现预留字段还是由外部工程维护，避免形成虚假的诊断能力预期。

任何实现变更均须先做协议兼容性评审、仿真和受控安全验证；本节没有修改代码，也没有提出可直接部署的补丁。

未修改ICube/MoveIt/ros2_control上游，未应用PR；未执行VAL3编译/仿真、ROS集成、CS9/HIL、FAT/SAT或实机验证。现场控制器型号、CS9/VAL3版本、部署包、诊断工具权限、任务创建API语义和独立安全链仍未确认。Stäubli工程级验收未通过，`TODO-EXT-001`未授权合并。

### 固定源码链接

- `https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/val3/userapp/ros2_server/start.pgx`
- `https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/val3/userapp/ros2_server/controlTask.pgx`
- `https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/val3/userapp/ros2_server/ros2_server.dtx`
- `https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/val3/userapp/ros2_server/ros2_server.pjx`
- `https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/val3/userapp/ros2_server/Serialization/encodeRobotStateMsg.pgx`
- `https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/val3/userapp/ros2_server/Serialization/initRobotCommandMsg.pgx`
- `https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/val3/userapp/ros2_server/Serialization/initRobotStateMsg.pgx`
- `https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/val3/userapp/ros2_server/Serialization/decodeRobotCommandMsg.pgx`


## §9.3.193｜VAL3超周期标志计数语义与ROS控制周期匹配

### 固定源码基线与证据

固定上游：`ICube-Robotics/staubli_driver_ros2@bd658e2d266e315d2ee35f985fb352ea88306b79`。

| 文件 | Blob SHA | 本节用途 |
|---|---|---|
| `staubli_robot_driver/val3/userapp/ros2_server/start.pgx` | `2d72315f0da1e18c959a24d3d75622652ee1287b` | VAL3控制任务周期设为0.004秒，并把bIsOverrun传入taskCreateSync |
| `staubli_robot_driver/val3/userapp/ros2_server/controlTask.pgx` | `00a69c4d13879116fce744ceb1611ecd05d65edf` | 主循环开头检查、清除布尔超周期标志并递增nOverruns |
| `staubli_robot_driver/val3/userapp/ros2_server/ros2_server.dtx` | `558dc2db671da45f5b859a3526148ce816eb6dd4` | bIsOverrun、nOverruns全局变量声明 |
| `staubli_bringup/config/controllers.yaml` | `a0e81e0a69f98215e6d5ac69c1f4ebd0c3634884` | ROS controller_manager默认update_rate=250 Hz |
| `staubli_driver_ros2/sphinx/quickstart/available_models.rst` | `a6d6d74050899704b18b9000ad7e665bfae9458c` | 型号采样周期差异及VAL3/ROS周期同步配置说明 |
| `staubli_driver_ros2/sphinx/demo_applications/troubleshooting.rst` | `fffd7d2b1fcb9cd95621f6e94191ff6cff49ba91` | 5个连续控制周期丢包约20ms的诊断说明 |
| `staubli_robot_driver/src/staubli_hardware_interface.cpp` | `4ae2b8c8d91857e5e32558bfcd16e2c391b9c3d0` | write使用ros2_control传入的period填充命令周期字段 |

### 1. 超周期标志的消费方式与计数器语义

`start.pgx`将`l_nCtrlPeriod=0.004`，并调用`taskCreateSync "controlTask", l_nCtrlPeriod, bIsOverrun, controlTask()`。因此当前仓库默认VAL3任务请求周期为4ms（250Hz），并将公共布尔量`bIsOverrun`作为taskCreateSync的超周期标志参数。

`controlTask.pgx`在每次主循环开始处执行：
- 若bIsOverrun为true，写入一条“Task overrun detected”日志；
- 将bIsOverrun清为false；
- 将nOverruns递增1。

计数器的实现语义是“控制任务每次观察到true标志时加一”，不是对调度器原生超周期事件数进行独立读取或累计。程序没有保存每次超周期的时间戳、最长执行时长、连续超周期长度、窗口超周期率或超周期间隔分布。

由于bIsOverrun是单个布尔量，如果运行时在controlTask消费并清零之前允许多次超周期事件重复置位，那么多个事件在布尔状态上不可区分，应用计数器可能只增加一次。反之，如果VAL3调度器保证每个周期以可观察方式重新置位，实际计数结果可能不同。固定仓库没有提供taskCreateSync该参数在目标控制器上的完整事件语义，故这里只确认应用侧布尔消费逻辑，不断言现场一定发生计数丢失。

此外，超周期检查位于每轮循环的开头；一次迭代内的状态更新、消息编码/发送、命令接收/解码、序号延迟检查、模式转换、运动控制调用和错误复位均发生在该检查之后。应用没有在循环末尾再做一次标志采样，也没有把单轮执行时间与4ms预算直接比较。因此，仅凭nOverruns无法还原超周期发生的精确时刻、持续时间或根因。

### 2. 默认VAL3与ROS控制周期的匹配

当前固定配置有明确的默认匹配关系：
- VAL3 start.pgx：0.004秒，即250Hz；
- ROS controller_manager配置：update_rate=250Hz；
- 文档将VAL3应用描述为默认按250Hz设计。

`available_models.rst`同时指出机器人型号采样时间可能不同：TX2-60L为4ms/250Hz，TX2-60L MR为1ms/1kHz。文档说明，如需更高频率，应调整VAL3 start.pgx中的控制周期、重新部署应用，并同步更新ROS 2 control参数；对TX2-60L MR，文档给出的已成功测试参考为500Hz/2ms。

因此，硬件控制器采样时间、VAL3控制任务周期和ROS controller_manager update_rate是三个相关但不应混为一谈的配置维度。型号硬件采样时间为1ms，并不意味着当前仓库的VAL3应用和ROS配置已经自动运行在1kHz；反过来，若仅将VAL3任务改为500Hz而ROS controller_manager仍保持250Hz，也不满足文档要求的周期匹配原则。实际部署必须核对具体型号、VAL3任务周期、ROS update_rate及hardware_interface write传入的period。

### 3. 周期失配与序号延迟保护不是同一个指标

troubleshooting文档将“连续5个或更多控制周期未收到ROS命令”解释为在250Hz下约20ms，并建议检查专用以太网链路、ROS主机负载及实时内核。controlTask也根据命令序号延迟阈值在运动/静止状态下转入STOP或ERROR处理。

该命令序号延迟反映的是通信报文到达/序列进度，不等同于VAL3任务自身的调度超周期。两者可能相关，但不能互相替代：
- nOverruns反映应用观察到的VAL3超周期标志；
- nSequenceDelay反映命令报文序号间隔；
- ROS controller_manager update_rate是ROS侧调度配置；
- controller硬件采样周期是控制器型号/配置属性。

目前公开RobotState协议未传输nOverruns（见§9.3.192），也没有在状态协议中报告VAL3实际周期、ROS实测周期或每周期执行耗时。上层不能仅凭当前RobotState状态判断实时周期健康度。

### 4. 静态结论

1. 固定VAL3应用请求4ms/250Hz控制任务，ROS controller_manager默认update_rate同为250Hz。
2. 官方仓库文档说明TX2-60L MR硬件采样周期为1ms，并记录500Hz/2ms的VAL3任务周期成功测试参考；更改VAL3周期后必须同步更新ROS 2 control参数。
3. nOverruns每次只在主循环开头观察到bIsOverrun=true时加一；该变量是布尔量，应用侧没有保存事件时间戳、执行耗时或超周期持续时间。
4. 如果目标运行时允许在应用清零前多次置位，布尔标志无法表达多个事件；是否合并以及调度器置位时序必须通过目标VAL3版本动态确认。
5. ROS命令序号延迟、VAL3超周期标志和ROS update_rate属于不同测量维度，不能将其作为同一个周期健康指标。
6. 以上均为固定提交静态配置与代码结论，不代表现场运行频率、真实超周期率或实时性能达标。

### 5. 新增验收任务

新增SERVO-776：

| 子项 | 验收对象 | 状态 |
|---|---|---|
| AG1 | 获取目标VAL3版本taskCreateSync文档，确认超周期参数的置位、保持、清零和重复事件语义 | 未确认，目标版本API证据缺失 |
| AG2 | 在隔离环境分别注入单次、连续及同一消费窗口内多次超周期，比较调度器事件数、bIsOverrun和nOverruns | 未执行 |
| AG3 | 在每周期开始、循环末尾及下一周期入口记录时间戳，测量controlTask实际执行时间、调度抖动和超周期持续时间 | 未执行 |
| AG4 | 对照TX2-60L、TX2-60L MR实际型号，核对控制器采样周期、VAL3任务周期、ROS update_rate三者配置 | 未确认，现场型号/配置证据缺失 |
| AG5 | 在250Hz配置下测量ROS controller_manager实际周期、hardware_interface read/write周期及VAL3报文到达周期 | 未执行 |
| AG6 | 在受控条件验证TX2-60L MR文档参考500Hz/2ms配置，确认VAL3任务和ROS update_rate同步修改后的稳定性 | 未执行，需对应型号受控环境 |
| AG7 | 分别制造ROS命令延迟与VAL3任务超周期，验证nSequenceDelay与nOverruns是否可区分且诊断日志不混淆 | 未执行 |
| AG8 | 评估nOverruns及周期耗时是否需要独立诊断遥测，定义采样窗口、时间戳、复位策略和上层告警阈值 | 未执行 |
| AG9 | 获取现场控制器型号、VAL3版本、部署包SHA、ROS参数快照及带时间基准的运行日志 | 未确认，现场证据缺失 |
| AG10 | 在隔离仿真/HIL中执行周期配置切换、超周期注入、ROS负载/网络扰动及恢复回归 | 未执行，需受控环境 |

AG1、AG4、AG9缺少目标版本/现场证据；AG2-AG3、AG5-AG8、AG10均未执行。公开文档中“500Hz成功测试”仅作为上游文档陈述记录，不作为本项目独立复测通过的证据。

### 6. 工程建议与边界

建议把周期配置作为同一部署配置组管理：记录机器人型号及硬件采样时间、VAL3 taskCreateSync周期、ROS controller_manager update_rate、hardware_interface实际write周期，并在启动时输出可追溯的配置摘要。对周期健康度至少区分实际周期、抖动、单轮执行时间、超周期事件数、命令序号延迟和通信丢包，避免只用一个布尔标志/累计计数器代表实时性能。

在明确目标VAL3调度器语义前，不建议仅通过调整nOverruns代码或放宽阈值宣称解决超周期问题。任何周期提升都必须在对应机器人型号和隔离环境完成稳定性、停止响应及独立安全链验证。

未修改ICube/MoveIt/ros2_control上游，未应用PR；未执行VAL3编译/仿真、ROS集成、CS9/HIL、FAT/SAT或实机验证。Stäubli工程级验收未通过，`TODO-EXT-001`未授权合并。

### 固定源码链接

- `https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/val3/userapp/ros2_server/start.pgx`
- `https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/val3/userapp/ros2_server/controlTask.pgx`
- `https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_bringup/config/controllers.yaml`
- `https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_driver_ros2/sphinx/quickstart/available_models.rst`
- `https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_driver_ros2/sphinx/demo_applications/troubleshooting.rst`
- `https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/src/staubli_hardware_interface.cpp`


## §9.3.194｜VAL3控制循环周期预算组成与运动模式分支路径（2026-11-09）

### 1. 审查范围与固定证据

本节沿固定上游提交 `bd658e2d266e315d2ee35f985fb352ea88306b79` 重新检查VAL3控制循环的直接调用路径，重点区分每轮固定工作、位置控制分支、速度控制分支、STOP/ERROR分支，以及UDP子程序调用。该审查不重复§9.3.193的周期配置与overrun布尔计数语义；本节回答的是：配置为4ms的单轮控制任务究竟串行执行哪些工作，是否有源码层的分支耗时/最坏执行时间证据。

| 源文件 | 固定提交Blob SHA | 本节用途 |
|---|---|---|
| `staubli_robot_driver/val3/userapp/ros2_server/controlTask.pgx` | `00a69c4d13879116fce744ceb1611ecd05d65edf` | 控制循环/运动/通信调用链 |
| `staubli_robot_driver/val3/userapp/ros2_server/start.pgx` | `2d72315f0da1e18c959a24d3d75622652ee1287b` | 控制循环/运动/通信调用链 |
| `staubli_robot_driver/val3/userapp/ros2_server/ros2_server.dtx` | `558dc2db671da45f5b859a3526148ce816eb6dd4` | 控制循环/运动/通信调用链 |
| `staubli_robot_driver/val3/userapp/ros2_server/Control/updateJointPositionControl.pgx` | `28e2f1d6a3482a126b16474c957a608262c32218` | 控制循环/运动/通信调用链 |
| `staubli_robot_driver/val3/userapp/ros2_server/Control/updateJointVelocityControl.pgx` | `72f4eb0215ceeae2c3a528013ea2a79c4dc46344` | 控制循环/运动/通信调用链 |
| `staubli_robot_driver/val3/userapp/ros2_server/Control/stopJointPositionControl.pgx` | `bd4be41dff93258d5c08cbf9411af3d811b5f6c9` | 控制循环/运动/通信调用链 |
| `staubli_robot_driver/val3/userapp/ros2_server/Control/stopJointVelocityControl.pgx` | `9a41ba293561d0ac216bebcb4da69b7c99458df0` | 控制循环/运动/通信调用链 |
| `staubli_robot_driver/val3/userapp/ros2_server/Comm/sendData.pgx` | `9df5d2b3240e780e1342ea248b97bb0262c9b58d` | 控制循环/运动/通信调用链 |
| `staubli_robot_driver/val3/userapp/ros2_server/Comm/readData.pgx` | `bf2e0f3d26e66724b9f656261e29fe573bd5f3b0` | 控制循环/运动/通信调用链 |
| `staubli_robot_driver/val3/userapp/ros2_server/Comm/readDataOnce.pgx` | `652aa04548c814febab3c8c3fc807093261efd97` | 控制循环/运动/通信调用链 |

### 2. 每轮主循环的串行调用顺序

`start.pgx`将`l_nCtrlPeriod`设为0.004秒，并以该周期创建`controlTask`。在`controlTask.pgx`的每轮主循环中，源码顺序为：

1. 在循环开头消费`bIsOverrun`标志并更新`nOverruns`；
2. 调用`updateState`更新RobotState；
3. 生成序号并填入上一轮记录的命令序号延迟；
4. 调用`encodeRobotStateMsg`，成功后调用`sendData`；
5. 调用`readData`接收命令，若有新数据则调用`decodeRobotCommandMsg`；
6. 计算命令序号延迟，执行延迟阈值、命令类型和模式转换检查；
7. 根据最终命令模式进入STOP/ERROR、位置控制或速度控制分支；
8. 执行GPIO输出位置的TODO占位；
9. 若`l_bError`置位，执行停止、运动复位、命令/通信状态清理及`resetControlSocket`；
10. 更新上一轮模式/接收错误状态，调用`delay(0)`后进入下一轮。

因此状态发布和命令处理不是并行流水线，而是在同一控制任务迭代中按源码顺序串行调用。状态报文在本轮命令接收和运动更新之前发送；本轮命令执行结果要到后续状态更新周期才可能反映在RobotState中。该先后关系仅说明程序调用顺序，不据此推定VAL3调度器、SIO或运动API的实际阻塞时长。

### 3. 位置控制分支的调用组成

`updateJointPositionControl.pgx`在每次调用开始时先查询`$movejSyncState()`，随后检查motion possible、命令有效性和命令类型。首次进入位置模式时还会执行`resetMotion()`，并在状态为未启动时调用`$movejSyncBegin(mMdesc)`。之后将六个关节命令写入`jointRx`，执行`isInRange`限位判断，通过后调用`$movejSync(l_jJointPositionCmd)`，并再次调用`$movejSyncState()`检查状态。

这意味着位置控制的稳态路径至少包含一次运动状态查询、一次运动命令更新和一次运动状态复查；首次进入路径还包含运动复位与movejSync启动。无效命令、motion impossible、命令类型不匹配、限位失败或movejSync错误等分支可能再进入`stopJointPositionControl`，后者查询`$movejSyncState()`，在状态非-1时调用`$movejSyncEnd()`。

源码没有在这些调用前后记录时间戳，也没有将`movejSync`、`movejSyncState`、`movejSyncBegin`或`movejSyncEnd`的执行时间与4ms预算比较。不得仅凭API名称中的Sync推断这些调用必然阻塞整个任务，也不得推断它们一定是常数时间或非阻塞；其调度/阻塞/缓冲契约必须由目标CS9/VAL3版本文档及运行测量确认。

### 4. 速度控制与STOP/ERROR分支的路径差异

`updateJointVelocityControl.pgx`在运动许可、命令有效性和命令类型检查后，首次调用可执行`resetMotion()`，但当前固定原型中的速度命令执行仍是TODO：日志提示尚未实现，随后将错误标志置true并立即返回。因而在该固定提交中，速度模式不是与位置模式等价的已实现控制路径；它会转入主循环统一的错误处理路径。该事实是本节路径差异背景，不把已在既有审查登记的“速度控制未实现”重复登记为新问题。

STOP/ERROR路径则可能先按上一模式调用`stopJointPositionControl`或`stopJointVelocityControl`，随后调用`stopMove()`和`resetMotion()`。错误处理分支在`l_nCmdMode==2`时还可能再次调用位置停止子程序，然后再次执行`stopMove()`、`resetMotion()`、清除命令有效位/控制活动状态，并调用`resetControlSocket`。因此异常/转换路径的调用数量和顺序可能显著不同于位置控制稳态路径。源码没有为该最长分支定义独立预算，也没有证明所有错误分支都能在一个4ms周期内完成。

### 5. UDP收发路径与观测缺口

`sendData.pgx`通过`sioSet`发送整个序列化数组，并检查返回字节数是否等于缓冲区长度；`readData.pgx`每轮最多调用两次`readDataOnce`，而`readDataOnce.pgx`通过`sioGet`读取数据并区分完整长度、正数短报文及其他返回值。上述调用在`controlTask`主循环内同步调用；本节固定源码没有显示独立通信任务将收发从控制循环剥离。

但SIO调用的具体阻塞上限、超时语义、UDP接收队列行为及其与VAL3任务调度的交互，不能仅由这些调用点推断。也没有每次`sioSet/sioGet`的耗时、排队深度、重试耗时或单轮收发总耗时遥测。两次读取的静态上限只是源码循环次数上限，不是可直接换算的毫秒上限。

### 6. 静态结论与边界

1. 4ms是`start.pgx`的任务周期配置；固定程序没有测量单轮执行时间或各分支最坏执行时间。
2. 每轮串行包含状态更新、状态编码/发送、命令读取/解码、延迟/模式检查及运动分支；这些工作共享同一控制任务执行路径。
3. 位置控制稳态每轮会调用`$movejSyncState()`、`$movejSync()`及再次查询状态；首次进入与异常退出路径还有额外运动API调用。
4. 速度控制当前固定原型仍会在TODO执行点返回错误，主循环随即进入错误复位路径；它与位置控制的执行成本不可视为相同。
5. STOP/ERROR/模式转换路径会额外调用停止、运动复位和socket复位函数，源码未给出这些路径的WCET或周期内完成证据。
6. SIO收发在控制循环内调用，但其阻塞时间和目标运行时调度语义未由固定源码确定。
7. 本节没有证明现场发生周期超限、运动API阻塞或UDP调用卡顿；也没有完成实时性能测试或安全响应验证。

### 7. 新增验收任务

新增SERVO-777：

| 子项 | 验收对象 | 状态 |
|---|---|---|
| AH1 | 静态梳理controlTask每轮调用顺序，并对位置、速度、STOP、ERROR及模式转换路径建立调用清单 | 固定提交静态审查完成 |
| AH2 | 获取目标CS9/VAL3版本对movejSyncBegin/movejSync/movejSyncState/movejSyncEnd、stopMove/resetMotion及delay(0)的执行/阻塞/调度契约 | 未确认，目标版本API证据缺失 |
| AH3 | 在隔离仿真中对位置控制首次进入、稳态更新、正常停止和异常停止分别采集调用前后时间戳 | 未执行 |
| AH4 | 分别测量状态更新、RobotState编码、sioSet发送、sioGet接收、命令解码的单项耗时及尾延迟 | 未执行 |
| AH5 | 对位置/速度/STOP/ERROR/模式切换分支测量单轮执行时间分布、最大值、抖动和4ms预算余量 | 未执行 |
| AH6 | 对SIO超时、无数据、连续数据、短报文和通信错误注入，测量readData最多两次读取及sendData失败路径的耗时 | 未执行 |
| AH7 | 在受控环境测量运动API调用与UDP收发同时存在时的任务调度、周期抖动和overrun关联，不将命令序号延迟当作调度超周期 | 未执行 |
| AH8 | 评估是否需要为各关键阶段增加低开销时间戳/直方图/最大耗时遥测，并定义时间基准、采样窗口和日志扰动控制 | 未执行 |
| AH9 | 获取现场控制器型号、CS9/VAL3版本、部署包SHA、实际控制模式占比及带时间基准的周期日志 | 未确认，现场证据缺失 |
| AH10 | 在隔离仿真/HIL中完成不同分支、通信扰动、运动停止/恢复和周期预算回归，独立验证安全停止链 | 未执行，需受控环境 |

AH1仅完成固定提交静态审查；AH2缺少目标版本API契约；AH3-AH8及AH10未执行；AH9缺少现场证据。任何动态测试必须在隔离且具备独立安全措施的环境进行。

### 8. 工程建议与限制

建议将控制循环拆分为可审计的阶段预算：状态采集、状态编码/发送、命令接收/解码、命令校验、运动API、错误/停止处理及循环调度。至少记录每阶段耗时分布、最大值、超预算次数和时间戳，同时评估遥测自身对4ms循环的扰动。对于运动API和SIO调用，先取得目标版本契约并进行受控测量，再讨论是否需要异步化、限时策略或任务拆分；不得仅依据函数名称或静态代码作实时性结论。

未修改ICube/MoveIt/ros2_control上游，未应用PR，`TODO-EXT-001`未授权合并。未执行VAL3编译/仿真、ROS集成、CS9/HIL、FAT/SAT或实机验证；Stäubli工程级验收未通过。

### 固定源码链接

- https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/val3/userapp/ros2_server/controlTask.pgx
- https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/val3/userapp/ros2_server/start.pgx
- https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/val3/userapp/ros2_server/ros2_server.dtx
- https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/val3/userapp/ros2_server/Control/updateJointPositionControl.pgx
- https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/val3/userapp/ros2_server/Control/updateJointVelocityControl.pgx
- https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/val3/userapp/ros2_server/Control/stopJointPositionControl.pgx
- https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/val3/userapp/ros2_server/Control/stopJointVelocityControl.pgx
- https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/val3/userapp/ros2_server/Comm/sendData.pgx
- https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/val3/userapp/ros2_server/Comm/readData.pgx
- https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/val3/userapp/ros2_server/Comm/readDataOnce.pgx


## §9.3.195｜CS9同步VAL3任务调度、delay(0)让出语义与SIO超时边界（2026-11-09）

### 1. 审查范围与固定证据

本节沿固定ICube公开提交 `bd658e2d266e315d2ee35f985fb352ea88306b79`，核对VAL3同步任务创建、控制循环末尾的`delay(0)`、SIO收发调用及socket timeout配置，并与Stäubli公开CS9/VAL3文档交叉对照。目标是区分“周期配置”“调度让出”“网络读取是否等待”和“实际执行时间”，不重复§9.3.194的运动分支调用清单。

| 源文件 | 固定提交Blob SHA | 本节用途 |
|---|---|---|
| `staubli_robot_driver/val3/userapp/ros2_server/start.pgx` | `2d72315f0da1e18c959a24d3d75622652ee1287b` | taskCreateSync周期配置 |
| `staubli_robot_driver/val3/userapp/ros2_server/controlTask.pgx` | `00a69c4d13879116fce744ceb1611ecd05d65edf` | delay(0)、SIO收发调用顺序 |
| `staubli_robot_driver/val3/userapp/ros2_server/Comm/resetControlSocket.pgx` | 本节固定提交文件 | 运行期timeout设置 |
| `staubli_robot_driver/val3/userapp/ros2_server/Comm/readData.pgx` | `bf2e0f3d26e66724b9f656261e29fe573bd5f3b0` | 两次读取控制流 |
| `staubli_robot_driver/val3/userapp/ros2_server/Comm/readDataOnce.pgx` | `652aa04548c814febab3c8c3fc807093261efd97` | sioGet返回值处理 |
| `staubli_robot_driver/val3/userapp/ros2_server/Comm/sendData.pgx` | `9df5d2b3240e780e1342ea248b97bb0262c9b58d` | sioSet发送及长度检查 |
| `staubli_robot_driver/val3/configs/sio.cfx` | 固定提交配置文件 | socket初始timeOut配置 |

### 2. CS9同步任务调度契约

Stäubli《CS9 Real Time Val3/Fieldbus configuration》TSS.000.014.04-A（2021-07-06）第3章描述CS9 CPU周期中的任务顺序：系统同步任务先执行，随后用户IO刷新任务，再执行VAL3同步任务和异步任务。系统同步任务负责机器人轨迹及系统IO；IO刷新任务负责用户IO板卡。该文档明确指出同步VAL3任务会消耗较多CPU资源，必须结合控制器周期及IO刷新/jitter配置理解。

该文档第4.2节说明同步VAL3任务按创建时指定周期调度；每次序列最多执行3000条VAL3指令；`delay(0)`可用于强制切换到下一任务；同步任务若执行时间超过指定周期，当前周期正常结束但下一周期取消，并通过taskCreateSync创建时指定的布尔变量报告overrun。由此，4ms是同步任务调度周期，不代表controlTask可独占完整4ms，也不代表单轮代码已在4ms内完成。实际可用预算还受到系统同步任务、用户IO刷新、其他同步任务及CPU负载影响。

VAL3 Reference Manual D.280.935.01-F（2020）第5章及taskCreateSync/delay条目补充：`delay(0)`在非正延时下立即调度下一VAL3任务；taskCreateSync周期受系统时钟周期约束；同步任务使用全局overrun布尔变量。该手册对同步任务周期数值和控制器时钟的具体适用性仍需目标现场版本核对。

### 3. 固定源码中的delay(0)不是周期等待

固定`start.pgx`设置`l_nCtrlPeriod=0.004`并调用`taskCreateSync "controlTask", l_nCtrlPeriod, bIsOverrun, controlTask()`。固定`controlTask.pgx`在每轮末尾调用`delay(0)`，源码注释写作“Sleep until next period”。但依据上述VAL3手册，delay(0)语义是立即让出/切换到下一VAL3任务，不是等待4ms周期计时器，也不单独建立下一次周期触发。

因此应将控制任务调度拆分为两个概念：taskCreateSync提供周期性调度框架；delay(0)在本次任务序列中主动让出执行权。周期是否准时、下一周期是否被取消以及实际抖动，仍由CS9调度器与CPU周期共同决定，不能由源码注释推导。

### 4. SIO timeout配置与sioGet接收路径

固定`sio.cfx`中control UDP socket的初始`timeOut`为-0.001。固定`controlTask.pgx`启动后先调用`resetControlSocket`；该子程序通过`sioCtrl(x_UdpSocket,"timeout",-1)`将运行期timeout改为-1，再设置endOfString并clearBuffer。故不能将sio.cfx的初始值直接视为controlTask初始化后的最终运行值。

VAL3 Reference Manual D.280.935.01-F第3.7.3节说明：`sioGet`在timeout=-1时读取当前输入缓冲区，缓冲区为空则返回0；timeout=0时若无数据可能无限等待；正timeout会等待到数据到达或超时。固定`readDataOnce.pgx`调用sioGet并仅在返回长度等于完整缓冲区时置new-data；正数短报文置错误，0或负值没有显式错误分支。结合初始化设置，controlTask运行期接收路径采用非阻塞读配置，空缓冲区不会按手册描述无限等待。

但这不等于已证明sioGet在目标CS9版本的执行时间严格为零，也不证明所有SIO调用都不会触发调度切换。VAL3手册的任务调度章节将SIO读写列为可能触发下一任务序列的指令；实际是否发生等待/让出还受socket状态、缓冲区、运行时版本及调用路径影响，需在目标环境测量。

### 5. sioSet发送路径与尚未闭环的超时契约

固定`sendData.pgx`通过sioSet发送整个状态报文，并检查返回字节数是否等于数组长度；不匹配进入发送错误路径。VAL3 Reference Manual说明sioSet在通信错误时可能返回-1或少于请求长度的字节数，但当前已检索条目没有充分给出目标CS9/VAL3版本中timeout=-1的最大执行时间、排队和调度契约。因此本节只确认代码调用点、返回值检查和运行期timeout配置，不宣称发送调用具有硬实时上界。

通信错误可能置位l_bError并进入统一停止/复位流程；这描述的是软件控制流，不等于机器人已完成物理停止，也不构成安全额定停止功能。

### 6. 版本适用性与边界

TSS.000.014.04-A封面/版本信息标注日期2021-07-06，文档列出的测试环境为SRC s8.10.4、Safety 1.003/SafePMT 3.0.0.28。ICube仓库VAL3项目文件中的字符串s8.20.2Cs9_BS4270只是项目元数据，不能证明现场部署版本，也不能证明TSS文档测试环境与现场一致。VAL3 Reference Manual D.280.935.01-F为2020年版本，需结合现场控制器随附手册、readme/errata和Stäubli书面确认。

本节仅形成固定公开源码与公开文档的静态契约对照。没有证据证明现场发生同步任务超周期、SIO阻塞、CPU负载不足或安全停止失效；也没有测得controlTask的WCET、4ms预算余量或实际jitter。

### 7. 新增验收任务

新增SERVO-778：

| 子项 | 验收对象 | 状态 |
|---|---|---|
| AI1 | 静态核对start.pgx 4ms taskCreateSync、controlTask delay(0)、resetControlSocket timeout=-1及sio.cfx初始timeout配置 | 固定提交静态审查完成 |
| AI2 | 获取目标现场CS9/VAL3版本、受控手册/errata，确认taskCreateSync、delay(0)、sioGet/sioSet调度与超时契约 | 未确认，目标版本/文档适用性证据缺失 |
| AI3 | 记录现场CPU周期、系统同步任务、IO refresh cyclicRatio、jitter mode及并行同步任务配置 | 未执行，需现场配置取证 |
| AI4 | 在隔离仿真中测量controlTask启动、delay(0)前后及相邻周期时间戳/抖动 | 未执行 |
| AI5 | 对timeout=-1的sioGet注入空缓冲区、单包、双包、短包和通信错误，测量返回路径与调度切换 | 未执行 |
| AI6 | 对sioSet注入对端不可达、发送错误及部分发送条件，测量最大执行时间、返回字节数和overrun关联 | 未执行 |
| AI7 | 在隔离环境制造同步任务负载/超周期，核对周期取消、bOverrun置位、controlTask消费及nOverruns计数时序 | 未执行 |
| AI8 | 核对同步任务3000条指令序列上限、同周期任务创建顺序及系统任务/IO刷新对周期预算的影响 | 未执行，需目标版本确认与测量 |
| AI9 | 获取现场控制器型号、CS9/VAL3版本、部署包SHA、IO刷新/jitter配置、socket参数及运行日志 | 未确认，现场证据缺失 |
| AI10 | 在隔离仿真/HIL中完成SIO超时/故障、周期负载、超周期恢复与独立安全停止链回归 | 未执行，需受控环境 |

### 8. 工程建议与限制

建议将同步任务周期、CPU周期、IO刷新周期比、jitter mode及其他同步任务纳入同一受控配置基线；分别记录调度周期、任务实际执行时间、让出点、SIO等待/返回时间、overrun标志与应用计数器。对sioGet与sioSet分开测量，不能因接收路径timeout=-1就推断发送路径具有同样的非阻塞上界。动态测量必须在隔离环境进行，且不得以调高周期/改变IO刷新配置替代安全验证。

未修改ICube/MoveIt/ros2_control上游，未应用PR，`TODO-EXT-001`未授权合并。未执行VAL3编译/仿真、周期/抖动测量、SIO故障注入、ROS集成、CS9/HIL、FAT/SAT或实机测试；Stäubli工程级验收未通过。

### 固定源码链接

- https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/val3/userapp/ros2_server/start.pgx
- https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/val3/userapp/ros2_server/controlTask.pgx
- https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/val3/userapp/ros2_server/Comm/resetControlSocket.pgx
- https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/val3/userapp/ros2_server/Comm/readData.pgx
- https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/val3/userapp/ros2_server/Comm/readDataOnce.pgx
- https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/val3/userapp/ros2_server/Comm/sendData.pgx
- https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/val3/configs/sio.cfx

### 参考资料

- Stäubli, *CS9 Real Time Val3/Fieldbus configuration*, TSS.000.014.04-A, 2021-07-06: https://bvdp.inetdoc.net/files/iut/staubliiut/doc/Real%20Time%20Val3-Fieldbus%20Synchronization%20TSS00001404A.pdf
- Stäubli, *VAL3 Reference Manual*, D.280.935.01-F, 2020-09-21: https://bvdp.inetdoc.net/files/iut/PHL/Manuel%20de%20ref%20VAL3.PDF


## §9.3.196｜ROS—UDP—VAL3双向报文名义流量、包率与MTU边界（2026-11-09）

### 1. 审查范围与已知输入

本节只建立固定公开原型的协议负载/包率算术基线，承接§9.3.194–§9.3.195，不重复控制循环WCET或SIO超时语义。固定上游为 `bd658e2d266e315d2ee35f985fb352ea88306b79`。

| 输入 | 数值 | 证据边界 |
|---|---:|---|
| RobotState固定帧长 | 132 B | 8 B Header + 124 B payload；沿用§9.3.3/§9.3.8静态协议布局，VAL3 Header编码缺陷仍未修复/验证 |
| RobotCommand固定帧长 | 55 B | 8 B Header + 47 B payload；沿用§9.3.4/§9.3.8静态协议布局 |
| VAL3控制任务周期 | 4 ms / 250 Hz | start.pgx配置值，不是实测持续发送频率 |
| ROS controller_manager默认频率 | 250 Hz | 配置默认值；目标部署参数快照未取得 |
| UDP/IP/链路参数 | 未知 | 现场MTU、IPv4/IPv6、VLAN、交换机队列和socket缓冲区均未取证 |

### 2. 名义应用层负载计算

在“每个4 ms周期发送一帧RobotState、ROS侧每周期发送一帧RobotCommand”的理想化假设下：

- RobotState：132 B × 250/s = 33,000 B/s（33.0 kB/s）。
- RobotCommand：55 B × 250/s = 13,750 B/s（13.75 kB/s）。
- 双向应用层数据合计：46,750 B/s，约374 kbit/s。
- 双向UDP数据报总包率：250 + 250 = 500 datagrams/s。

以上是名义负载模型，不是实际抓包统计。VAL3 overrun可能取消周期；ROS更新可能受控制器管理器调度、硬件读写耗时及控制器激活状态影响；因此实际发送频率、突发性和包率必须以时间戳抓包测量。

### 3. 以太网线速占用估算与MTU

仅为提供量级参考，假设IPv4、UDP、Ethernet II，无VLAN标签，并把以太网帧头14 B、FCS 4 B、前导码/SFD 8 B及IFG 12 B计入线速占用：

- RobotState单包估算：132 + IPv4 20 + UDP 8 + Ethernet 14 + FCS 4 + preamble/SFD 8 + IFG 12 = 198 B；250包/s约49,500 B/s。
- RobotCommand单包估算：55 + 20 + 8 + 14 + 4 + 8 + 12 = 121 B；250包/s约30,250 B/s。
- 单个控制会话合计约79,750 B/s，即约638 kbit/s线速占用估算。

若采用802.1Q VLAN，每帧还增加4 B；若采用IPv6，网络层头部通常比上述IPv4假设多20 B。实际链路占用还受交换机封装、其他流量和统计口径影响。按IPv4假设，IP数据报长度分别为160 B与83 B，均远小于常见1500 B Ethernet MTU，正常固定长度帧不需要IP分片；这只是长度比较，不证明现场MTU配置、路径MTU或实际抓包没有分片/封装问题。

### 4. 不能由低带宽推导的工程结论

1. 约638 kbit/s的单会话估算不证明控制链路低延迟、低抖动、零丢包或具备实时性；包率、队列积压、调度延迟和尾延迟比平均吞吐更关键。
2. UDP不提供传输层重传/有序交付保证；应用层序号、超时、重复/乱序处理及STOP确认边界仍以既有专项审查为准，不因负载较低而消失。
3. 132 B/55 B小于常见MTU不代表VAL3 SIO接收数组、Boost.Asio接收缓冲、socket队列或操作系统接收路径不存在截断、溢出、背压和丢包。
4. 本估算只计一条control通道，不含诊断通道、FTP部署/日志下载、DDS/ROS其他流量、ARP/邻居发现、管理网络及其他设备流量；多机器人场景应按每个端点/流分别计数，不能把单会话结果当作网络总负载。
5. 名义250 Hz不等于实测250 Hz。VAL3同步任务超周期、状态先发后收、ROS周期错相以及网络突发均可能改变端到端采样/反馈间隔。

### 5. 结论与验证边界

固定协议长度与名义周期可支持一个可复算的流量模型：单会话在双向各250 Hz假设下约500 datagrams/s、46.75 kB/s应用负载；在明确的IPv4/Ethernet开销假设下约638 kbit/s线速占用。该结果仅是理论容量基线，不是网络性能或安全验收结果。当前没有现场pcap、MTU/路由/交换机配置、socket buffer快照、收发时间戳或丢包计数，因此不能判断真实网络是否满足4 ms控制周期。

### 6. 新增验收任务

新增SERVO-779：

| 子项 | 验收对象 | 状态 |
|---|---|---|
| AJ1 | 以固定协议定义复核RobotState 132 B、RobotCommand 55 B帧长及实际序列化长度 | 固定源码/文档静态算术基线完成；跨语言线上帧未验证 |
| AJ2 | 在目标配置确认VAL3任务周期、ROS update_rate及真实状态/命令发布频率 | 未确认，目标配置/运行日志缺失 |
| AJ3 | 在隔离网络抓取双向UDP流，统计pps、平均/峰值bps、突发间隔和方向 | 未执行 |
| AJ4 | 核对目标主机/CS9/交换机MTU、IPv4/IPv6、VLAN、路由和路径MTU | 未确认，现场网络证据缺失 |
| AJ5 | 获取ROS与VAL3 socket接收/发送缓冲区、队列上限及相关OS网络参数 | 未确认，目标版本/现场配置证据缺失 |
| AJ6 | 注入接收端慢处理、CPU负载和突发流量，测量队列积压、丢包、延迟分布及恢复行为 | 未执行 |
| AJ7 | 将状态包接收时间、命令发送时间、VAL3读取/执行时间和状态回传时间统一到可比时间基准 | 未执行 |
| AJ8 | 在单机器人及多端点场景测量control/diagnostic/DDS/管理流量叠加后的链路占用与隔离效果 | 未执行 |
| AJ9 | 获取目标现场pcap、网卡统计、交换机端口计数、丢包/错误计数及配置快照 | 未确认，现场证据缺失 |
| AJ10 | 在隔离仿真/HIL中完成网络负载、MTU边界、背压/丢包和独立安全停止链回归 | 未执行，需受控环境 |

AJ1仅完成固定协议布局与算术模型；AJ2、AJ4–AJ5、AJ9缺少目标配置/现场证据；AJ3、AJ6–AJ8、AJ10未执行。未执行ROS构建、VAL3仿真、CS9/HIL、FAT/SAT或实机验证；未修改ICube/MoveIt/ros2_control上游，未应用PR，`TODO-EXT-001`未授权合并。

### 固定源码链接

- https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/val3/userapp/ros2_server/start.pgx
- https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/val3/userapp/ros2_server/Comm/sendData.pgx
- https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/val3/userapp/ros2_server/Comm/readData.pgx
- https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/val3/userapp/ros2_server/Comm/readDataOnce.pgx



## §9.3.197｜ROS 2 C++ API默认UDP端口与VAL3部署端口配置一致性（2026-11-09）

### 1. 审查范围与固定证据

本节检查固定ICube公开原型中C++通信API默认端口、ros2_control硬件参数注入、Xacro启动配置与VAL3 SIO配置是否一致。固定上游提交：`bd658e2d266e315d2ee35f985fb352ea88306b79`。仅做源码/配置静态审查，不推断现场控制器当前配置。

| 文件 | 固定Blob SHA | 关键证据 |
|---|---|---|
| `protocol.hpp` | `773cdeb9c4bf6e2dab3cf9e15426e4e954e35dea` | `DEFAULT_CONTROL_PORT=8080`、`DEFAULT_DIAGNOSTICS_PORT=8081` |
| `robot_driver.hpp` | `62c87a6741aa082db4599bb2c048aec0fcd7a464` | `NetworkConfig`四个端口成员默认继承上述常量 |
| `robot_driver.cpp` | `ede48a314856a455df9d8434f354aaf9fbc47bff` | `connect(robot_ip, timeout_ms)`创建默认`NetworkConfig`，仅赋值robot_ip后转调配置重载 |
| `staubli.r2c.xacro` | `0013b6ea5b681e5333799f65867e7de497b54127` | 控制/诊断远端与本地端口显式设为11000/11001 |
| `staubli_hardware_interface.cpp` | `4ae2b8c8d91857e5e32558bfcd16e2c391b9c3d0` | `on_configure`读取四个硬件参数并写入`NetworkConfig` |
| `sio.cfx` | `76ad0c9f4b1902f26f21ea08eed0ef5f16e63d9e` | VAL3 control/diagnostics socket端口分别为11000/11001 |
| `val3/README.md` | `560e9c7e281b19bc79c22e0fe286427a9cf0b9f7` | 手动配置表同样列出11000/11001 |
| `overview.rst` | `ce3e3dcba07864ac0f3e2b48595283f24d73620c` | 文档将四个端口参数默认值均描述为11000/11001 |

### 2. 配置路径对照

| 调用/部署路径 | ROS侧本地端口 | 控制器远端端口 | 静态结论 |
|---|---:|---:|---|
| `RobotDriver::NetworkConfig{}`默认构造 | 8080 / 8081 | 8080 / 8081 | 与仓库VAL3配置不一致 |
| `RobotDriver::connect(robot_ip, timeout_ms)` | 8080 / 8081 | 8080 / 8081 | 通过默认配置重载，继承不一致值 |
| 仓库默认Xacro硬件接口路径 | 11000 / 11001 | 11000 / 11001 | 与仓库VAL3 SIO配置一致 |
| 手动部署VAL3并按README配置 | 由ROS参数提供 | 11000 / 11001 | 文档部署基线一致 |

### 3. 影响分析与边界

1. `RobotDriver::connect(robot_ip, timeout_ms)`仅设置robot_ip，端口仍取`NetworkConfig`默认值8080/8081；而仓库VAL3 `sio.cfx`的control/diagnostics端口为11000/11001。若调用方直接使用该便捷重载并部署仓库默认VAL3配置，静态配置存在端口错配风险。
2. `NetworkConfig`默认构造后再调用`connect(config)`而不显式赋端口，也具有相同风险。
3. 仓库标准ros2_control路径由Xacro显式传入11000/11001；`StaubliHardwareInterface::on_configure`再将参数写入`NetworkConfig`，因此不能把C++结构体默认值差异直接扩大为“标准bringup必然连不上”。
4. `overview.rst`、VAL3 README与`sio.cfx`均描述/配置11000/11001；C++ API常量8080/8081与此形成文档/API默认值不一致。使用者若只阅读参数文档而绕开Xacro，可能误判直接API默认行为。
5. UDP socket的`connect`实现会绑定本地端口并设置远端endpoint；端口错配会影响本地接收绑定及发送目的端口。实际是否表现为连接超时、仅单向无数据或其他症状，取决于控制器配置、路由和应用握手，当前没有现场抓包或连接复现，不能写成已发生故障。
6. 本节不判断控制器现场端口、其他版本发行包或用户自定义launch是否沿用上述值；只对固定提交中的默认值和仓库配套配置作静态比较。

### 4. 建议的工程闭环

- 为端口配置建立单一权威来源：让C++默认常量、Xacro参数默认值、VAL3 SIO配置与文档表格从同一版本化配置生成，或在构建/测试阶段做一致性断言。
- 明确区分“C++库API默认值”“ros2_control/Xacro参数默认值”“VAL3控制器端监听/配置端口”，不要只用一个“默认端口”标签。
- 对`RobotDriver::connect(robot_ip)`增加回归测试，验证其默认端口与仓库默认VAL3部署一致；对显式`NetworkConfig`保留覆盖端口测试。
- 在mock与集成测试中分别覆盖默认配置和Xacro等价配置，避免测试只使用自定义回环端口而遗漏部署默认值。
- 在现场部署前采集ROS参数转储、VAL3 SIO配置文件SHA、控制器端口配置及双向pcap；以同一部署版本归档。

### 5. 新增验收任务 SERVO-780 / AK1–AK10

| 子项 | 验收对象 | 状态 |
|---|---|---|
| AK1 | 核对协议常量8080/8081 | 固定源码静态核对完成 |
| AK2 | 核对`NetworkConfig`默认成员继承关系 | 固定源码静态核对完成 |
| AK3 | 核对便捷重载是否仅赋值robot_ip并继承默认端口 | 固定源码静态核对完成 |
| AK4 | 核对Xacro是否显式覆盖为11000/11001 | 固定源码静态核对完成 |
| AK5 | 核对HardwareInterface参数注入路径 | 固定源码静态核对完成 |
| AK6 | 核对VAL3 SIO配置及部署README端口 | 固定源码/文档静态核对完成 |
| AK7 | 核对overview参数默认值与C++ API默认值差异 | 固定文档/源码静态核对完成 |
| AK8 | 构建并运行默认API端口回归测试及mock双向握手测试 | 未执行 |
| AK9 | 验证Xacro/launch端口覆盖与目标控制器配置一致 | 未执行，目标部署环境缺失 |
| AK10 | 获取现场ROS参数、VAL3配置SHA、控制器端口配置和双向pcap | 未确认，现场证据缺失 |

AK1–AK7仅完成固定提交的静态核对；AK8未执行；AK9–AK10缺目标部署/现场证据。未执行ROS构建、mock集成、VAL3仿真、CS9/HIL、FAT/SAT或实机验证。未修改ICube/MoveIt/ros2_control上游，未应用PR；Stäubli工程级验收未通过，`TODO-EXT-001`未授权合并。

### 固定源码与部署资料

- https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/include/staubli_robot_driver/communication/protocol.hpp
- https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/include/staubli_robot_driver/robot_driver.hpp
- https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/src/robot_driver.cpp
- https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_description/r2c/staubli.r2c.xacro
- https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/val3/configs/sio.cfx
- https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/val3/README.md
- https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_driver_ros2/sphinx/quickstart/overview.rst


## §9.3.198 RobotDriver连接等待循环、首次状态就绪与超时边界

### 1. 固定审查基线

本节固定审查ICube公开仓库提交 bd658e2d266e315d2ee35f985fb352ea88306b79，仅对公开原型源码作静态判断，不代表Stäubli/ICube现场部署版本。

| 文件 | Blob SHA |
|---|---|
| staubli_robot_driver/src/robot_driver.cpp | ede48a314856a455df9d8434f354aaf9fbc47bff |
| staubli_robot_driver/include/staubli_robot_driver/robot_driver.hpp | 62c87a6741aa082db4599bb2c048aec0fcd7a464 |
| staubli_robot_driver/src/real_time_socket_subscriber.cpp | e2cd8fc50b2b13d9e31b2c024e90f9da76107622 |
| staubli_robot_driver/include/staubli_robot_driver/real_time_socket_subscriber.hpp | 330839cb25e53fe961541f29f634722bec4a47c4 |
| staubli_robot_driver/src/real_time_socket_interface.cpp | eda0a830cfe0118e07bc3423ad0f455bd50d610c |
| staubli_robot_driver/include/staubli_robot_driver/real_time_socket_interface.hpp | e4d4650f59d2eb95133f5e948431ebe2073a6667 |
| staubli_robot_driver/src/communication/udp_socket_impl.hpp | 1309a8f2d59e8295869e178af82a66868bb911ff |
| staubli_robot_driver/test/unit_tests/test_robot_driver.cpp | 44da0046ce37fe52649a84ab0833ffee3d9973c5 |

### 2. 就绪层级与调用链

1. **UDP socket connect不是机器人应用握手。** RobotDriver::connect先分别连接控制与诊断socket，再创建实时subscriber/interface。RealTimeSocketSubscriber::is_ready定义仅为socket存在、is_connected为true且is_receiving为true，不证明已收到任何数据报。
2. **首次状态帧门槛在更高一层。** connect在socket/subscriber初始化后调用read_robot_state等待状态。该方法要求control interface ready、缓存中曾收到消息、message_type为ROBOT_STATE且消息年龄小于state_staleness_timeout。因此“socket已连接/接收线程已运行”与“收到有效且新鲜的RobotState”是不同状态；本节不把前者单独视为机器人控制链ready。
3. **状态新鲜度默认阈值为100ms。** RobotDriver构造时调用无参set_state_staleness_timeout，头文件默认参数为100ms。subscriber接收回调在反序列化成功后写入reception_timestamp；读取时按该时间戳计算age。若没有新包但缓存曾收到过消息，read_message仍返回缓存帧并由上层进行staleness检查。
4. **连接等待循环以500ms间隔采样。** connect循环每次先调用read_robot_state，再执行rclcpp::sleep_for(500ms)；timeout由连接开始时刻与循环条件比较。轮询间隔大于默认100ms staleness阈值，但接收线程持续异步更新latest-message缓存，因此稳定250Hz状态流下通常可读到较新帧；不能仅凭500ms轮询就推断稳定流必然被判stale。
5. **首次成功后没有提前退出。** 即使某次read_robot_state已成功，代码仍继续sleep并循环，直到timeout条件不再成立；最终interfaces_ready只由最后一次迭代写入的cmd_interface_ready和诊断布尔值决定，而不是记录“曾经成功”或首次成功时刻。因此连接调用仍会占用调用线程直至整个timeout窗口结束；若最后一次采样时状态已stale/失效，连接会失败，即使窗口早些时候曾出现过有效状态。稳定持续状态流下该失败条件不必然触发。
6. **timeout边界受轮询粒度影响。** 每次循环在重新检查deadline前先sleep 500ms，故超时退出可能相对请求timeout延后最多约一个轮询周期，另加线程调度延迟。
7. **现有mock测试没有测量连接耗时。** test_robot_driver.cpp的mock robot每4ms发送RobotState和DiagnosticData，ConnectionTest调用connect(...,1000)并只断言返回成功/connected；没有断言成功后立即返回、最大连接耗时或首次有效状态时间。因此该测试不能发现“已经ready仍持续等待”的时延问题，也没有覆盖只短暂出现状态后停止的窗口末端情形。
8. **范围排除。** 诊断通道readiness占位、diagnostic数据实际读取缺失等问题已在既有连接握手审查节点登记；本节不重复计为新发现。本节只聚焦控制状态首次有效后连接循环的等待/采样语义。

### 3. 工程影响与建议

- 连接调用延迟由配置timeout主导，而不是首次有效RobotState到达时间；HardwareInterface的on_configure固定传入5000ms，因此标准硬件配置路径在状态很早到达时仍可能等待接近完整5秒。此为静态控制流推导，尚未实测具体耗时。
- 若有效状态在连接窗口中途出现但在最后一次采样前停止或变旧，最终采样值会覆盖先前成功结果，可能导致连接失败。该路径需要受控报文注入验证，不能说现场必然发生。
- 建议把循环改为“满足所有必需握手条件即记录成功并break”；若要求连续稳定性，应另设明确的连续有效帧数量/稳定时间门槛，而不是无说明地等待完整timeout并仅看最后一帧。
- 将deadline检查与sleep策略设计成剩余时间受限的等待，避免500ms固定sleep造成timeout超调；同时分开记录socket建立、接收线程启动、首个可解码帧、首个有效新鲜RobotState及上层控制/安全许可状态。
- 连接成功后仍应持续由read/watchdog检查状态新鲜度；首次握手成功不能替代运行期断流监控，也不能代替CS9安全状态、操作模式或命令接受确认。

### 4. 新增验收任务 SERVO-781 / AL1–AL10

| 子项 | 验收对象 | 状态 |
|---|---|---|
| AL1 | 核对UDP socket连接与receive thread启动顺序 | 固定提交静态核对完成 |
| AL2 | 核对subscriber is_ready仅表示socket connected/receiving | 固定提交静态核对完成 |
| AL3 | 核对首次RobotState是否经过反序列化、message_type和staleness检查 | 固定提交静态核对完成 |
| AL4 | 核对state staleness默认100ms及reception_timestamp更新点 | 固定提交静态核对完成 |
| AL5 | 核对connect等待循环500ms采样间隔 | 固定提交静态核对完成 |
| AL6 | 核对首次成功后循环是否break、最终结果是否只取末次采样 | 固定提交静态核对完成 |
| AL7 | 核对timeout sleep超调边界及5s on_configure调用参数 | 固定提交静态核对完成 |
| AL8 | 检查现有mock ConnectionTest是否断言连接耗时/首帧时刻 | 固定测试源码审查完成：无此类断言 |
| AL9 | 在mock中测量首次有效状态后connect返回时间，并注入状态中断/过期 | 未执行 |
| AL10 | 在目标CS9/VAL3及ROS部署中记录连接阶段时间戳、状态流中断和控制许可 | 未确认，目标部署/现场证据缺失 |

AL1–AL8完成固定提交静态源码/测试审查；AL9未执行；AL10缺目标部署及现场证据。未运行ROS构建/单测、mock时序注入、VAL3仿真、CS9/HIL、FAT/SAT或实机验证。未修改ICube/MoveIt/ros2_control上游，未应用PR；Stäubli工程级验收未通过，TODO-EXT-001未授权合并。

### 固定源码链接

- https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/src/robot_driver.cpp
- https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/include/staubli_robot_driver/robot_driver.hpp
- https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/src/real_time_socket_subscriber.cpp
- https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/include/staubli_robot_driver/real_time_socket_subscriber.hpp
- https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/src/communication/udp_socket_impl.hpp
- https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/test/unit_tests/test_robot_driver.cpp


## §9.3.199｜状态新鲜度、控制模式准入与诊断通道就绪语义（2026-11-09）

### 审查范围与固定基线

本节继续审查固定ICube提交 bd658e2d266e315d2ee35f985fb352ea88306b79，聚焦RobotDriver连接状态在生命周期运行阶段的语义、硬件接口控制模式切换是否使用新鲜状态，以及诊断通道是否真正完成首帧校验。源码静态审查，不代表现场行为或安全验证。

### 发现

1. **is_connected不代表状态仍新鲜。** robot_driver.hpp注释明确说明该函数不检查message staleness；实现仅检查control/diagnostics socket connected及两个接口is_ready。接收线程仍运行但RobotState停止更新时，该函数仍可能返回true。
2. **状态新鲜度只在显式读取时检查。** read_robot_state要求控制接口ready、至少曾收到可读消息、message_type为ROBOT_STATE，且time_since_received小于state_staleness_timeout_（默认100ms）；失败时不把新状态写入输出参数，也不清除上一次缓存状态。
3. **激活回调没有二次就绪门禁。** StaubliHardwareInterface::on_activate仅将current_control_mode_设为STOP并返回SUCCESS；不重新检查RobotDriver连接、首帧有效性、状态新鲜度、错误状态或motion_possible。连接成功与激活时状态有效之间没有在该回调中建立新的保证。
4. **读周期会把状态过期传播为硬件读错误。** read先检查is_connected，再调用read_robot_state；后者因状态过期返回false时，硬件read返回ERROR。因此连接socket仍在线不等于控制周期可持续读取。
5. **命令模式切换读取缓存状态而非独立验证新鲜度。** perform_command_mode_switch在切换到JOINT_POSITION时检查缓存的state_msg_.error_state和state_msg_.motion_possible，但该函数本身没有时间戳/新鲜度门禁。若上一次成功read后状态流中断，缓存字段不会因后续read_robot_state失败而自动清空；命令模式准入是否发生在失败read之后取决于controller_manager调用时序，须动态验证。
6. **write与生命周期错误处理的检查粒度不同。** write检查socket/interface连接；非STOP模式还检查缓存的error_state及control_state INVALID，并在异常时尝试发送STOP。该函数自身没有读取新RobotState或计算状态年龄。on_error/on_shutdown也以is_connected作为入口条件；is_connected不检查状态新鲜度。不能据此断言STOP必然发送失败或实际机器人未停止，需验证命令接收和VAL3执行链。
7. **诊断通道的ready不是诊断数据已就绪。** connect创建diagnostics subscriber并检查其socket connected/receiving，但等待循环将diag_interface_ready = true硬编码，read_diagnostic_data调用仍被TODO注释。之后打印current_diagnostic_data_.robot_firmware_version，但本次connect流程没有先读取并验证诊断帧；reset_data仅将诊断message_type置为INVALID。因此该日志不能作为本次连接已验证固件版本的证据，诊断首帧缺失也不会阻止connect成功。
8. **控制与诊断两条通道的就绪等级应分开记录。** 当前connect的有效RobotState检查只覆盖控制通道；诊断socket/接收线程检查仅证明传输层已启动。控制器类型校验代码被注释，VAL3版本检查仍为TODO。不能将connect成功解释为固件/控制器兼容性已经验证。

### 影响边界与结论

本节识别的是静态接口语义缺口：is_connected是传输/接收线程状态，不是新鲜状态或运动许可；激活、命令模式切换和写入路径使用的部分状态来自最近一次成功read；诊断通道没有在connect时验证首个诊断数据帧。实际是否出现过期状态下的模式切换、错误恢复时STOP是否被控制器接受、诊断报文是否在其他路径被消费，均需运行时证据。安全功能必须由控制器安全链和独立验证承担，不能以本驱动的ROS状态门禁替代。

### SERVO-782｜AM1–AM10

| 子项 | 核查内容 | 状态 |
|---|---|---|
| AM1 | 核对is_connected声明注释及实现是否包含状态新鲜度 | 固定提交静态核对完成 |
| AM2 | 核对read_robot_state过期/无新消息时的返回与缓存更新行为 | 固定提交静态核对完成 |
| AM3 | 核对on_activate是否重新验证连接、首帧和状态许可 | 固定提交静态核对完成 |
| AM4 | 核对read/write及on_error/on_shutdown的连接/状态检查边界 | 固定提交静态核对完成 |
| AM5 | 核对perform_command_mode_switch的位置模式准入是否检查状态新鲜度 | 固定提交静态核对完成 |
| AM6 | 核对connect诊断通道首帧读取与diag_interface_ready赋值 | 固定提交静态核对完成 |
| AM7 | 核对固件版本日志、控制器类型校验及VAL3版本检查是否有有效诊断数据支撑 | 固定提交静态核对完成 |
| AM8 | 动态注入状态流中断、read失败与并发命令模式切换，记录缓存状态及模式结果 | 未执行 |
| AM9 | 在目标ROS/CS9/VAL3部署中核对controller_manager周期、lifecycle调用顺序、诊断发送配置与日志 | 未确认，目标部署配置证据缺失 |
| AM10 | 在隔离HIL/现场验证诊断帧缺失、状态过期、STOP命令接收/执行及独立安全链 | 未执行，现场证据缺失 |

AM1–AM7完成固定提交静态源码核对；AM8未执行；AM9缺目标部署配置；AM10缺现场/HIL证据。未运行ROS构建/单测、动态并发注入、VAL3仿真、CS9/HIL、FAT/SAT或实机验证。未修改ICube/MoveIt/ros2_control上游，未应用PR；Stäubli工程级验收未通过，TODO-EXT-001未授权合并。

### 固定源码链接

- https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/src/robot_driver.cpp
- https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/include/staubli_robot_driver/robot_driver.hpp
- https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/src/staubli_hardware_interface.cpp
- https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/src/real_time_socket_subscriber.cpp


## §9.3.200｜RobotDriver状态新鲜度阈值API的取值边界与并发更新契约

### 审查基线与静态发现

固定ICube公开提交 `bd658e2d266e315d2ee35f985fb352ea88306b79`，检查`RobotDriver::set_state_staleness_timeout()`、`set_diagnostic_staleness_timeout()`及对应读取路径。

1. **默认阈值为100ms，但公开setter不校验输入范围。** 构造函数调用两个setter默认参数`rclcpp::Duration(0, 1e8)`；头文件也将默认值描述为100ms。实现只记录传入duration并直接赋值，没有拒绝零值、负值或不合理的大值。
2. **零值和负值会使所有消息被判定为stale。** `read_robot_state()`及`read_diagnostic_data()`均使用`status.time_since_received >= *_staleness_timeout_`作为过期条件。接收年龄为非负值；阈值为0或负数时，即使刚收到消息，比较也成立，读取持续失败。此为比较逻辑的静态推导，尚未通过测试验证。
3. **过大的正阈值会放宽旧状态可被接受的窗口。** setter允许任意duration，未将状态阈值与控制周期、通信周期或安全策略关联。将阈值设得很大可能使长时间未更新的缓存状态仍被read接受；不代表用户当前这样配置，仓库默认仍为100ms。
4. **setter与读取字段没有显式同步。** 两个duration成员由setter直接写入，read路径直接读取；该字段没有atomic或mutex保护。若外部调用方在实时read线程并发修改阈值，按C++对象并发访问规则存在数据竞争风险。仓库内可见调用主要为构造阶段默认设置及测试中的配置调用，未发现运行期并发更新证据，因此这是条件性API线程安全缺口，不是已复现数据竞争。
5. **头文件注释与函数签名不一致。** 两个setter的Doxygen注释均写有`@return True if timeout was set successfully`，实际返回类型为`void`；调用方无法通过返回值判断配置是否被接受，而实现也没有拒绝路径。
6. **诊断阈值的运行时意义当前更弱。** `read_diagnostic_data()`具备同样的staleness比较，但connect流程将diagnostic ready硬编码为true且未读取诊断首帧（详见§9.3.199）；因此不能把diagnostic timeout setter存在解释为诊断通道已在启动流程受其保护。

### 建议与验收要求

- 将setter改为有明确成功/失败结果的配置接口，拒绝`<= 0`阈值，并设置可解释的上限或明确由应用层负责的策略边界。
- 若允许运行期调整，应使用互斥/原子化快照或生命周期约束，保证read线程不会与duration写入并发冲突；否则在API文档明确只允许连接前、单线程设置。
- 将状态阈值与实际RobotState发送周期、ROS控制周期和目标故障检测时间预算关联；不得为了消除偶发read ERROR而无依据地放宽阈值。
- 增加0、负值、极小正值、默认100ms、阈值边界前后和超大值测试；增加setter与read并发的TSan测试；诊断通道单独验证首帧、陈旧和断流处理。

### SERVO-783 / AN1–AN10

| ID | 验收项 | 状态 |
|---|---|---|
| AN1 | 核对两个staleness setter默认值及实现 | 固定提交静态核对完成 |
| AN2 | 核对read路径的age与threshold比较方向 | 固定提交静态核对完成 |
| AN3 | 推导零值/负值阈值下的读取结果 | 静态逻辑核对完成，动态测试未执行 |
| AN4 | 核对超大阈值与控制周期/安全策略之间是否有关联 | 静态核对完成：未见范围门禁 |
| AN5 | 核对setter与read访问是否有mutex/atomic同步 | 静态核对完成：未见同步 |
| AN6 | 核对仓库内setter调用位置及是否存在运行期并发更新 | 固定仓库静态检索完成；现场外部调用未知 |
| AN7 | 修正并验证Doxygen @return与void签名一致性 | 未执行，属于上游修复建议 |
| AN8 | 对0、负值、极小/默认/边界/超大阈值执行单元测试 | 未执行 |
| AN9 | 对运行期并发修改与read执行开展TSan/线程屏障测试 | 未执行 |
| AN10 | 在目标部署确认实际阈值、RobotState周期、外部setter调用和诊断数据路径 | 未确认，目标部署/现场证据缺失 |

AN1–AN6完成固定提交静态源码/调用点核对；AN7–AN9未执行；AN10缺目标部署及现场证据。未运行ROS构建/单测、TSan、Mock/SIL、VAL3仿真、CS9/HIL、FAT/SAT或实机测试。未修改ICube/MoveIt/ros2_control上游，未应用PR；Stäubli工程级验收未通过，`TODO-EXT-001`未授权合并。

### 固定源码链接

- https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/include/staubli_robot_driver/robot_driver.hpp
- https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/src/robot_driver.cpp
- https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/test/unit_tests/test_robot_driver.cpp


## §9.3.201｜RobotDriver接收序号回绕、乱序帧与重连会话恢复边界（2026-11-09）

### 审查基线与范围

固定ICube公开提交 bd658e2d266e315d2ee35f985fb352ea88306b79，审查 RealTimeSocketSubscriber 的接收缓存、16位序号统计、RobotDriver状态序号更新、disconnect/reconnect对象生命周期及现有通信单测。此处聚焦序号连续性和会话恢复；不重复§9.3.198–§9.3.200对ready/staleness/timeout的结论。

### 静态发现

1. **16位序号回绕的丢包公式存在+1偏差。** 协议头的 sequence_number 为 uint16_t，最大值定义为65535。subscriber在新序号小于上次序号时按 (65535 - last) + current + 1 计算丢包数。按连续模65536序列，65534→0应为0个丢包，但当前公式给出2；65534→1应为2个丢包，当前公式给出3。该公式在回绕分支系统性多计1，需以边界单测确认并修正。
2. **所有小于上次序号的帧都被解释为回绕，未区分乱序/迟到帧。** 例如last=100、current=99会进入wrap分支并报告65535个丢包，而非识别为迟到/乱序。subscriber仍将该帧写入调用方消息并把last_read_sequence_number_回退为99；RobotDriver后续可能把其作为新鲜状态更新current_robot_state_及last_valid_sequence_id_。接收时间戳新并不证明控制器序列更新。
3. **邮箱按最后到达覆盖，而非按序号新旧筛选。** update_message对成功反序列化的帧直接更新RealtimeThreadSafeBox；没有在入箱前比较序号或丢弃过期序号。因此乱序旧帧若晚于新帧抵达，可覆盖缓存中的新帧。这里的结论针对乱序帧的序号语义，不代表UDP一定会在现场产生乱序。
4. **相同序号只被视为重复读取，不是独立的重复报文告警。** read_message在当前序号等于last_read_sequence_number_时将new_message置false、lost_packages置0，但仍返回true并保留该消息供上层检查staleness。该逻辑能识别同一缓存再次读取；没有独立统计重复数据报、重复帧率或拒绝策略。
5. **断开/重连会重建subscriber序号跟踪状态，但协议没有会话epoch。** disconnect先reset控制接口和诊断subscriber，再停止/断开socket并reset_data；后续connect新建subscriber，其构造函数将last_read_sequence_number_置0、first_read_置true，RobotDriver的last_valid_sequence_id_也重置为0。因此本地计数器在重连后重新起算。但8字节协议头没有session ID/boot ID/epoch，单凭首个报文无法判断它属于当前控制器会话还是旧会话延迟到达；是否存在可达的旧数据报窗口需要目标网络/重连动态实验，不可直接断言现场会误接收。
6. **现有单测覆盖不完整。** test_rt_socket_interface.cpp覆盖普通递增、跳号及无新帧重复读取；未覆盖65534/65535/0回绕边界、真实重复数据报、乱序抵达后缓存回退、重连首帧旧epoch以及重连时接收线程/缓存的竞态。
7. **RobotDriver只告警丢包且不把序号异常作为状态拒绝条件。** read_robot_state对lost_packages仅保留注释掉的WARN，不校验序号是否单调前进；验证消息类型和新鲜度后就更新last_valid_sequence_id_。因此subscriber层的序号误判或回退不会被RobotDriver作为独立准入失败处理。

### 建议与验收要求

- 使用明确的模65536序号差值和半区间规则区分正常递增、回绕、重复及乱序；对迟到帧不应覆盖已接受的新状态。协议若需要跨重启区分会话，应增加session/boot标识或建立经过验证的重同步握手。
- 增加序号边界测试：65534→65535→0→1；65534→0（无丢包）；65534→1（丢2）；重复帧；乱序帧；跨越半区间的歧义；从任意序号开始的first_read；disconnect/reconnect后首帧；旧会话延迟帧。
- 在mock/SIL中注入乱序、重复、丢失、延迟及重连竞态，记录缓存序号、接收时间、丢包统计、RobotDriver输出状态和控制命令门禁；再在隔离HIL验证控制器重启与网络队列清理策略。
- 不把UDP序号统计当作安全功能；过期/乱序状态的拒绝、停止动作和独立安全链仍需端到端验证。

### SERVO-784 / AO1–AO10

| ID | 验收项 | 状态 |
|---|---|---|
| AO1 | 核对协议序号宽度、最大值及序列起始语义 | 固定提交静态核对完成 |
| AO2 | 核对正常递增/丢包计数公式 | 固定提交静态核对完成 |
| AO3 | 推导65534/65535/0回绕边界并识别公式偏差 | 固定源码逻辑核对完成，动态未执行 |
| AO4 | 核对重复序号与重复数据报处理 | 固定提交静态核对完成 |
| AO5 | 核对乱序帧是否被识别/丢弃及是否覆盖缓存 | 固定提交静态核对完成 |
| AO6 | 核对disconnect/reconnect的subscriber及RobotDriver序号重置 | 固定提交静态核对完成 |
| AO7 | 核对现有单测的回绕/重复/乱序/重连覆盖 | 固定提交静态核对完成 |
| AO8 | 增加边界与乱序/重复/旧会话帧单元测试并运行 | 未执行 |
| AO9 | Mock/SIL/HIL注入重连、旧帧延迟与接收线程竞态 | 未执行 |
| AO10 | 核对目标VAL3序号重启策略、网络队列及现场重连行为 | 未确认，目标部署/现场证据缺失 |

AO1–AO7完成固定提交静态源码/测试覆盖核对；AO8–AO9未执行；AO10缺目标部署及现场证据。未运行ROS构建/单测、Mock/SIL、TSan、VAL3仿真、CS9/HIL、FAT/SAT或实机验证。未修改ICube上游，未应用PR；Stäubli工程级验收未通过，TODO-EXT-001未授权合并。

### 固定源码链接

- https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/src/real_time_socket_subscriber.cpp
- https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/include/staubli_robot_driver/real_time_socket_subscriber.hpp
- https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/include/staubli_robot_driver/communication/protocol.hpp
- https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/src/robot_driver.cpp
- https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/test/unit_tests/communication/test_rt_socket_interface.cpp


## §9.3.202｜MessageStatus输出初始化与read_message线程安全契约（2026-11-09）

### 审查基线与范围

固定ICube公开提交 `bd658e2d266e315d2ee35f985fb352ea88306b79`，检查`MessageStatus`定义、`RealTimeSocketSubscriber::read_message()`实现、调用方与通信单测。聚焦无消息返回时的输出确定性，以及文档声明的线程安全是否覆盖序号跟踪状态。本节为固定源码静态审查，不代表已复现未定义行为或并发数据竞争。

### 静态发现

1. **MessageStatus有两个字段没有默认初始化。** `new_message`与`lost_packages`均为普通标量成员且没有类内初始值；只有`time_since_received`设置了默认duration。调用方常见写法是`MessageStatus status;`，这不会将前两个成员自动初始化为确定值。
2. **从未收到过消息时，read_message提前返回但没有写入lost_packages。** 当邮箱`try_get()`为空时，函数先设置`status.new_message=false`；若传入消息的`reception_timestamp`仍为0，则立即返回false。该分支没有给`status.lost_packages`赋值，也没有重置`status.time_since_received`。对默认构造的status，lost_packages保持未初始化；对复用的status，time_since_received可能保留上一次调用的旧值。
3. **接口文档要求调用方“无论如何检查status”，但失败输出没有完整定义。** 头文件read_message注释提示调用方在任何情况下都应检查status；然而无首帧分支只保证new_message被写为false，其他字段不一定反映本次调用。若调用方在false返回后读取lost_packages，可能读取未初始化值；若复用status，time_since_received则可能被误认为本次测量值。
4. **read_message的线程安全说明没有覆盖全部可变状态。** 头文件称该方法thread-safe，message_buffer_使用RealtimeThreadSafeBox保护邮箱读写；但`first_read_`和`last_read_sequence_number_`由read_message直接读取/写入，未见mutex/atomic保护。两个线程同时调用同一subscriber的read_message时，可能并发访问并更新这两个成员，形成条件性数据竞争及序号状态交错。
5. **现有调用点未证明当前部署必然有多读者。** 固定仓库的RobotDriver状态读取、mock server命令读取及单测均表现为各自接口的单一逻辑消费路径；本次检索未建立同一subscriber被多个线程并发read的事实。因此多读者风险应表述为公开API线程安全契约不完整，而非已发生的现场竞态。
6. **现有测试没有覆盖失败输出完整初始化和并发读者。** 通信单测覆盖收到首帧、重复读取、普通跳号和丢包统计；没有测试“从未收到首帧时status所有字段均确定”、status对象跨调用复用，也没有双读者并发/TSan测试。

### 建议与验收要求

- 为`MessageStatus`所有字段提供确定的默认值，并在`read_message`每次调用入口统一初始化全部输出字段；明确false返回时各字段的语义，避免调用方读到旧值或未初始化值。
- 若类设计只支持单一消费者，应将`read_message`文档改为明确的single-consumer约束，并说明RealtimeThreadSafeBox只保护生产者/消费者邮箱，不使整个subscriber API自动具备多读者线程安全。
- 若确需多读者支持，应对`first_read_`与`last_read_sequence_number_`的序号状态转移实施一致性同步；仅将字段分别改成atomic不足以自动保证复合序号处理的线性化语义。
- 增加无首帧、status复用、首帧后断流及每个返回分支的输出断言；在明确支持多读者的设计下增加并发读/TSan测试，否则增加API约束测试和调用图审查。

### SERVO-785 / AP1–AP10

| ID | 验收项 | 状态 |
|---|---|---|
| AP1 | 核对MessageStatus所有成员的默认初始化 | 固定提交静态源码核对完成 |
| AP2 | 核对邮箱为空且调用方消息尚无时间戳时的提前返回路径 | 固定提交静态源码核对完成 |
| AP3 | 核对失败返回时lost_packages/time_since_received是否被本次调用确定赋值 | 固定提交静态源码核对完成 |
| AP4 | 核对read_message头文件线程安全声明与RealtimeThreadSafeBox保护范围 | 固定提交静态源码核对完成 |
| AP5 | 核对first_read_与last_read_sequence_number_的并发访问同步 | 固定提交静态源码核对完成 |
| AP6 | 检索固定仓库调用点，区分已证实单消费者路径与潜在多读者API风险 | 固定提交静态检索完成 |
| AP7 | 增加无首帧/复用status/失败返回字段初始化单测并运行 | 未执行 |
| AP8 | 对同一subscriber多读者并发read执行TSan或屏障测试，或验证单消费者API约束 | 未执行 |
| AP9 | 核对目标部署对read_message的外部调用、线程模型及编译配置 | 未确认，目标部署证据缺失 |
| AP10 | 在目标ROS/CS9隔离环境验证无首帧、断流恢复和并发调用边界 | 未确认，现场/HIL证据缺失 |

AP1–AP6完成固定提交静态源码/调用点核对；AP7–AP8未执行；AP9缺目标部署线程模型证据；AP10缺现场/HIL证据。未运行ROS构建/单测、TSan、Mock/SIL、VAL3仿真、CS9/HIL、FAT/SAT或实机测试。未修改ICube/MoveIt/ros2_control上游，未应用PR；Stäubli工程级验收未通过，`TODO-EXT-001`未授权合并。

### 固定源码链接

- https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/include/staubli_robot_driver/real_time_socket_subscriber.hpp
- https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/src/real_time_socket_subscriber.cpp
- https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/test/unit_tests/communication/test_rt_socket_interface.cpp
- https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/src/robot_driver.cpp
- https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/src/mock_robot_server.cpp


## §9.3.203｜UDP接收线程停止、重启与异步接收生命周期（2026-11-09）

### 审查基线与范围

固定ICube公开提交 `bd658e2d266e315d2ee35f985fb352ea88306b79`，审查`UDPSocketImpl`的`start_receive_thread()`、`stop_receive_thread()`、`start_receive()`、`handle_data_received()`及`test_sockets.cpp`。重点核对停止事件循环是否取消底层异步接收、同一socket停止后重启的操作生命周期，以及接收错误是否仍被传递给业务回调。本节为固定提交静态审查，不代表已动态复现数据丢失、缓冲区竞争或控制故障。

### 静态发现

1. **停止接收线程只停止io_service，没有显式取消socket上的异步接收操作。** `stop_receive_thread()`在`receiving_==true`时调用`io_service_.stop()`，随后join线程并将receiving_置false；该路径没有调用`socket_.cancel()`，也没有关闭socket。停止事件循环与取消底层I/O是不同操作，不能把线程退出等同于异步接收操作已取消/完成。
2. **停止后重启可能留下旧接收操作并叠加新操作。** `start_receive_thread()`每次启动都会`io_service_.reset()`并调用`start_receive()`，后者提交新的`async_receive_from()`，而停止路径没有显式取消旧操作。按Asio事件循环语义，stop使run退出并不等价于撤销挂起操作；reset允许事件循环再次运行。因而在同一socket停止后重启时，旧的挂起接收操作可能仍待完成，同时又新增接收操作。两者都引用同一个`recv_buffer_`和`sender_endpoint_`，可能导致接收归属、回调顺序和缓冲区内容的非预期交错。此为静态生命周期风险，实际可达性及表现仍需动态测试确认。
3. **接收错误路径仍调用用户回调。** `handle_data_received()`在`error`非空时记录错误，但随后无条件调用`reception_callback_(recv_buffer_, bytes_transferred)`。例如取消、关闭或其他接收错误可能以非成功完成路径到达回调；业务层不应默认此时的缓冲区内容构成有效数据报。应明确错误码处理策略，成功接收前不调用正常数据回调，或将错误状态显式纳入回调契约。
4. **错误后是否继续投递下一次接收没有按错误类型区分。** 回调执行后只要`is_receiving()`仍为true便再次调用`start_receive()`。因此非致命错误、持续错误或socket关闭等情况可能触发重复错误回调/重投递行为；应定义可恢复错误与终止错误的分类和退避/退出策略。当前没有证据证明目标现场发生错误风暴。
5. **线程启动/停止状态由atomic布尔量表示，但操作本身没有串行化。** `receiving_`只保护状态标志的读写；未见围绕socket、io_service、receive_thread_及回调对象的启动/停止互斥。若外部并发调用start/stop/disconnect，检查状态与执行操作之间可能发生竞态。当前审查没有证明部署调用点存在这些并发调用，故登记为接口并发契约风险。
6. **现有测试没有覆盖同一连接socket的stop→start生命周期。** `test_sockets.cpp`包含持续接收、批量接收、断开后重连、receive_once、DoubleStartReceiveThread（第二次start被拒绝、stop两次）等测试；未见在socket保持连接时停止接收线程后再次启动，并验证只存在一个有效接收操作、回调次数/数据完整性稳定。也未见取消操作完成、关闭时错误回调、错误后重投递策略的定向测试。
7. **receive_once依赖start/stop线程路径，继承相同的挂起操作边界。** `receive_once()`通过启动接收线程等待future，超时后调用`stop_receive_thread()`；若超时路径只停止事件循环而未取消底层接收，之后在同一socket上再次receive_once或启动连续接收时，也可能叠加尚未完成的异步操作。需要将连续超时与下一次接收作为专项回归场景。

### 建议与验收要求

- 停止流程应明确取消/关闭当前异步接收操作，并等待其完成处理后再宣布接收生命周期结束；对`operation_aborted`等预期取消错误应有明确分支。
- 启动流程应保证同一socket最多只有一个有效接收操作；建议将socket生命周期状态、io_service和线程句柄操作串行化，并防止并发start/stop/disconnect。
- `handle_data_received()`应先分类处理error，再决定是否调用数据回调及是否重新提交接收；错误信息应可观测，避免将无效缓冲区当作正常数据包。
- 为停止/重启、超时后重试、disconnect时取消、错误回调、并发start/stop增加单元测试；在可控loopback环境中统计每个发送数据报的唯一交付次数、回调字节数、错误码和接收操作数。
- 在目标ROS/CS9隔离环境执行压力测试与TSan/ASan（适用时），并确认实际Boost.Asio版本及部署编译配置；静态检查不能代替这些证据。

### SERVO-786 / AQ1–AQ10

| ID | 验收项 | 状态 |
|---|---|---|
| AQ1 | 核对stop_receive_thread是否显式取消/关闭挂起异步接收 | 固定提交静态源码核对完成 |
| AQ2 | 核对io_service.stop/reset与挂起操作的生命周期关系 | 固定提交静态语义核对完成，动态未执行 |
| AQ3 | 核对停止后重启是否再次提交async_receive_from及共享缓冲区 | 固定提交静态源码核对完成 |
| AQ4 | 核对接收error时是否仍调用正常数据回调 | 固定提交静态源码核对完成 |
| AQ5 | 核对错误后是否无条件重投递下一次接收 | 固定提交静态源码核对完成 |
| AQ6 | 核对receiving_状态标志与socket/thread操作是否串行化 | 固定提交静态源码核对完成 |
| AQ7 | 核对现有测试对连接保持时stop→start、超时重试及取消错误的覆盖 | 固定提交静态测试覆盖核对完成 |
| AQ8 | 增加stop→start、连续receive_once超时/重试和唯一交付次数测试并运行 | 未执行 |
| AQ9 | 增加取消/关闭错误路径、并发start/stop压力测试及适用的TSan/ASan | 未执行 |
| AQ10 | 核对目标部署Boost.Asio版本、线程调用模型并在隔离CS9/HIL验证 | 未确认，目标部署/现场证据缺失 |

AQ1–AQ7完成固定提交静态源码/测试覆盖核对；AQ8–AQ9未执行；AQ10缺目标部署及现场证据。未运行ROS构建/单测、TSan/ASan、Mock/SIL、VAL3仿真、CS9/HIL、FAT/SAT或实机测试。未修改ICube/MoveIt/ros2_control上游，未应用PR；Stäubli工程级验收未通过，`TODO-EXT-001`未授权合并。

### 固定源码链接

- https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/src/communication/udp_socket_impl.hpp
- https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/test/unit_tests/communication/test_sockets.cpp
- https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/src/communication/udp_socket.cpp
- https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/src/real_time_socket_subscriber.cpp
- https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/include/staubli_robot_driver/communication/udp_socket.hpp


## §9.3.204｜UDP数据报来源验证、报文长度与协议边界安全审查（2026-11-09）

### 审查基线与范围

固定ICube公开提交 `bd658e2d266e315d2ee35f985fb352ea88306b79`。审查UDP接收端点、发送方识别、接收字节数到消息反序列化的边界传递、三类消息头字段校验及现有单测覆盖。固定源码链接均指向该提交。本节为静态源码与测试代码审查，不代表已动态构造恶意报文、完成网络渗透测试或观察到现场状态注入。

### 静态发现

1. **UDP接收端未验证数据报来源。** `UDPSocketImpl::start_receive()`使用`async_receive_from(..., sender_endpoint_, ...)`接收任意来源的数据报；`handle_data_received()`没有比较`sender_endpoint_`与配置的`remote_endpoint_`，也没有检查来源端口。源码中还保留了明确的TODO，说明应丢弃unexpected sender以避免状态数据注入及序号跟踪干扰。当前`remote_endpoint_`用于`send_to()`，不能据此认为接收端已绑定或过滤远端。该路径允许非预期来源的数据进入业务回调；网络可达性、路由隔离和现场攻击可达性未验证。
2. **仅做IP/端口白名单仍不等同于发送方身份认证。** 即使补充endpoint比较，也只能形成网络层来源筛选；在存在地址欺骗、同网段主机失陷或路由配置错误时，不能替代认证/完整性保护。应结合隔离网络、ACL/VLAN及经威胁建模选定的消息认证机制，且不得破坏控制周期预算。
3. **UDP回调没有统一执行精确数据报长度门禁。** 接收回调将`bytes_transferred`原样传给消息反序列化；未见在进入消息类型解析前验证数据报长度必须与该类型完整帧长一致。三类消息固定长度分别为RobotState 132 B、RobotCommand 55 B、DiagnosticData 74 B。当前反序列化入口普遍只拒绝`buffer_size < expected_size`，长度大于期望值时仍可能继续解析并忽略尾随字节；因此“至少足长”不等于“帧长精确匹配”。
4. **RobotState反序列化未验证消息头的类型、协议版本和payload_size。** `RobotStateMessage::deserialize()`调用`header.deserialize()`后直接解析状态字段，没有像RobotCommand那样检查`header.message_type`及`header.payload_size`；`FrameHeader::deserialize()`自身只检查magic number，不检查protocol_version。只要magic正确且数据报达到最小长度，其他类型/版本/声明长度不匹配的帧仍可能被解释为RobotState并进入状态缓存。该结论是静态可达性，不代表已发生现场注入。
5. **RobotCommand校验比RobotState完整，但仍不完整。** `RobotCommandMessage::deserialize()`在解析头后检查message_type与payload_size，但没有检查protocol_version；其入口同样只拒绝短于期望长度的缓冲区，未拒绝超长数据报。因此协议版本不匹配和尾随字节仍可能被接受。
6. **DiagnosticData的头字段校验顺序存在缺陷。** `DiagnosticDataMessage::deserialize()`在调用`header.deserialize(buffer, buffer_size)`之前，就读取对象当前`header.payload_size`和`header.message_type`进行校验。对正常新建对象，这些字段来自构造函数的默认值，而非待解析网络帧；随后解析网络头后没有再次验证payload_size/message_type。故该前置校验不能证明收到的诊断帧类型及payload长度正确。其入口也未验证协议版本和精确数据报长度。
7. **失败反序列化与缓存更新之间存在一道保护，但不能弥补头字段漏检。** `RealTimeSocketSubscriber::update_message()`仅在`msg.deserialize(...)`返回true时设置`message_buffer_`；返回false时只记录错误，不更新邮箱。因此显式返回false的短帧/部分解析失败不会直接提交该局部对象。但RobotState漏检的头字段、DiagnosticData无效的前置校验等情况可能令畸形帧返回true，仍可覆盖有效缓存。解析函数在失败前对局部对象字段的部分写入不会自动污染邮箱，但调用者若复用对象则需另行验证；当前subscriber每次回调创建局部MessageType。
8. **FrameHeader的协议版本字段目前只是被反序列化，没有统一兼容性判定。** `FrameHeader::deserialize()`检查magic number后即返回成功；未对`protocol_version`进行支持版本校验。各消息类型应共享一致的header校验器，避免每种消息各自遗漏。
9. **现有测试主要验证合法loopback报文，不足以证明边界拒绝行为。** `test_rt_socket_interface.cpp`覆盖正常RobotState接收、序号丢包统计和双向消息；`test_sockets.cpp`覆盖普通UDP接收、批量报文、重连及线程行为。未见针对非预期源IP/端口、错误magic、错误protocol_version、错误message_type、payload_size不匹配、短帧、超长帧、尾随字节、截断/超大UDP数据报或三类消息交叉类型的拒绝测试。
10. **来源白名单与协议校验尚无部署配置证据。** 固定仓库未证明目标部署是否在外部网络设备上实施ACL、独立控制网或其他来源约束，也未取得现场端口映射、对端IP/端口、Boost.Asio版本、CS9/VAL3版本及抓包证据。不能将源码TODO直接等同于现场可被任意互联网主机访问。

### 建议与验收要求

- 在UDP接收边界记录并校验`sender_endpoint_`的地址与端口；允许多控制器/冗余链路时使用显式配置的来源集合，不要将任意来源自动加入白名单。将IP/端口筛选视为纵深防御，而非密码学身份认证。
- 在消息解析前根据通道/预期消息类型执行精确长度检查；对短帧、超长帧、截断帧和带尾随字节帧统一拒绝，并记录计数/错误原因。注意UDP最大数据报、接收缓冲区大小与Asio错误码的处理应一并测试。
- 统一校验magic number、protocol_version、message_type、payload_size及实际数据报长度；先解析头，再对解析后的头字段做校验。RobotState和DiagnosticData必须补齐与RobotCommand一致且正确排序的校验逻辑。
- 对拒绝路径保证不更新状态/诊断邮箱，不推进序号跟踪，不刷新接收时间戳；在连续有效帧后注入畸形帧，验证上层仍只读到最后一条有效状态，并按策略标记数据新鲜度。
- 增加来源端口/IP矩阵、消息类型交叉注入、所有头字段边界、精确长度±1/尾随字节、随机畸形帧和UDP截断场景测试；使用loopback/隔离网段，不在生产控制网做未授权注入。
- 在目标环境核实控制网络ACL/VLAN、实际远端地址/端口、协议版本协商、部署二进制SHA和日志；如引入认证，评估密钥生命周期、重放保护、序号/会话epoch和实时开销。

### SERVO-787 / AR1–AR10

| ID | 验收项 | 状态 |
|---|---|---|
| AR1 | 核对async_receive_from写入sender_endpoint_后是否执行来源地址过滤 | 固定提交静态源码核对完成：未见过滤，源码含TODO |
| AR2 | 核对接收来源端口是否与配置远端端口匹配 | 固定提交静态源码核对完成：未见端口校验 |
| AR3 | 核对UDP接收回调到消息解析入口是否执行精确数据报长度检查 | 固定提交静态源码核对完成：未见统一精确长度门禁 |
| AR4 | 核对RobotState头部message_type、protocol_version、payload_size校验 | 固定提交静态源码核对完成：未见完整头字段校验 |
| AR5 | 核对RobotCommand头部字段与超长报文处理 | 固定提交静态源码核对完成：检查类型/声明长度，未检查版本及精确长度 |
| AR6 | 核对DiagnosticData头字段校验是否发生在网络头反序列化之后 | 固定提交静态源码核对完成：当前校验顺序在头解析之前 |
| AR7 | 核对FrameHeader协议版本校验及三类消息的一致性 | 固定提交静态源码核对完成：FrameHeader只校验magic |
| AR8 | 核对deserialize失败是否更新subscriber邮箱/时间戳 | 固定提交静态源码核对完成：false不更新邮箱；漏检后返回true仍可能更新 |
| AR9 | 核对现有单测对来源、短/超长帧、畸形头及交叉消息类型的覆盖 | 固定提交静态测试覆盖核对完成：未见上述定向用例 |
| AR10 | 核对目标部署网络ACL、对端端点、协议/软件版本，并在隔离CS9/HIL验证 | 未确认，缺目标部署/现场及受控测试证据 |

AR1–AR9完成固定提交静态源码/测试覆盖核对；AR10缺目标部署、现场网络配置及隔离验证证据。未运行构建/单测、模糊测试、网络注入、Mock/SIL、VAL3仿真、CS9/HIL、FAT/SAT或实机测试。未修改ICube/MoveIt/ros2_control上游，未应用PR；Stäubli工程级验收未通过，`TODO-EXT-001`未授权合并。

### 固定源码链接

- https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/src/communication/udp_socket_impl.hpp
- https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/src/real_time_socket_subscriber.cpp
- https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/src/communication/messages.cpp
- https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/src/communication/protocol.cpp
- https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/include/staubli_robot_driver/communication/protocol.hpp
- https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/test/unit_tests/communication/test_rt_socket_interface.cpp
- https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/test/unit_tests/communication/test_sockets.cpp
