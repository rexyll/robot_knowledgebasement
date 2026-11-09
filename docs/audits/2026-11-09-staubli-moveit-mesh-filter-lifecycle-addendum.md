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
