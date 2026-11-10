# Stäubli SocketV2 cleanup dependency DAG validation、platform-specific native close semantics evidence matrix 与 residual resource reconciliation policy

- **节点：** §9.3.300 / SERVO-883
- **日期：** 2026-11-10
- **固定上游基线：** `ICube-Robotics/staubli_driver_ros2@bd658e2d266e315d2ee35f985fb352ea88306b79`
- **前置节点：** SERVO-880至SERVO-882。
- **性质：** 静态依赖图审查方法、公开平台文档证据矩阵与residual处置策略；未对driver真实运行时资源图作代码级验证。

## 1. 本轮结论与证据边界

1. cleanup不能只用一个线性析构序列表达。资源依赖应建模为有向无环图（DAG），边的含义、所有者、barrier和完成判据必须明确。
2. Linux `close(2)`错误返回不代表fd仍有效。Linux man-pages明确警告失败后重试可能关闭另一个线程已复用的fd；Linux在close早期释放fd，后续步骤仍可能报告错误。
3. POSIX.1-2008对被信号中断的close规定fd状态unspecified；Linux man-pages 6.18记录POSIX.1-2024调整了行为，且Linux没有计划按新规则改变内核行为。因此“POSIX”不是足够精确的平台配置，必须记录目标OS/ABI/版本/标准配置。
4. Windows Winsock `closesocket`的socket值在调用后可能立即复用；微软明确要求不得与另一个Winsock函数对同一socket并发调用。非阻塞socket+非零linger timeout时，`WSAEWOULDBLOCK`表示socket仍有效、disconnect未启动，可按API契约重新调度；这与Linux close的错误重试语义不同。
5. Apple公开历史man page确认close错误集合包括EBADF/EINTR/EIO，但该文档版本较旧且没有明确描述EINTR后descriptor是否仍有效。本报告不从旧页面推断当前macOS/XNU的错误后句柄状态；必须以目标SDK/OS版本和对应XNU实现/实测证据补齐。
6. 本轮没有读取或运行driver代码中的真实socket close路径，因此DAG是需在后续源码盘点中验证的候选模型，不宣称已证明当前实现不存在环。

## 2. Cleanup dependency DAG

### 2.1 节点模型

| Node | 资源/屏障 | owner | 释放/完成判据 |
|---|---|---|---|
| A0 | admission gate | TransportLifecycleOwner | 新connect/send/subscribe拒绝 |
| A1 | callback ingress registry | ROS adapter / callback registry | 不再注册新callback，unregister已提交 |
| A2 | active callback lease | callback lease owner | active计数为0，且无pending dispatch |
| A3 | async send/receive operation | operation owner | 完成、明确取消或记录residual |
| A4 | poller/worker thread | thread owner | wake确认、线程退出、外部join成功 |
| A5 | protocol/session shutdown | session owner | 协议终止确认或明确失败/超时 |
| A6 | native socket/transport handle | unique native handle owner | 平台close adapter给出closed或unknown分类 |
| A7 | I/O buffers / decoder state | transport/Core owner | 无A2/A3/A4引用 |
| A8 | ROS entity / callback target | ROS lifecycle owner | executor不再dispatch且A2为0 |
| A9 | plugin lease/code image | plugin unload coordinator | callback、deleter、vtable、thread entry均不依赖plugin |
| A10 | CoreControlBlock / transaction journal | lifecycle/quarantine owner | 无resource owner、task、residual handle引用 |

### 2.2 必须成立的依赖边

边 `X -> Y`表示X必须先达到其释放判据，Y才允许销毁。候选边：
- A0 -> A1：停止新任务后才能封闭callback ingress。
- A1 -> A2：停止新dispatch后才能等待active lease归零。
- A2 -> A8：callback target/ROS entity不得早于active callback归零销毁。
- A2 -> A7：callback可能引用buffer/decoder，lease drain前不得释放。
- A3 -> A6：native handle仍被in-flight I/O使用时不得close；先完成/取消/隔离操作。
- A3 -> A7：buffer不得早于异步I/O引用消失。
- A4 -> A6：poller/worker退出并join后才允许释放其独占使用的transport handle。
- A4 -> A7：worker退出后才能释放其引用的buffer/decoder。
- A5 -> A6：若协议要求graceful session shutdown，需在transport仍可用时完成；失败则记录，不得假称成功。
- A2 -> A9：所有plugin callback lease归零后才可unload。
- A4 -> A9：线程入口、TLS析构、worker callable或线程栈上的plugin代码引用消失后才可unload。
- A8 -> A9：ROS entity及其callback target销毁且无plugin代码回调后才可unload。
- A6/A7/A8/A9 -> A10：CoreControlBlock最后释放；任何residual handle仍引用它时不得销毁。

注意：A2、A3、A4可能并行drain；图中只表达必要先后约束，不应强行串行化所有节点。实际资源清单可能增加独立节点和边。

### 2.3 DAG验证规则

对每个资源图版本执行：
1. **节点完整性：** 每个native handle、callback target、buffer、thread、ROS entity、plugin lease都必须有唯一owner及稳定ResourceId。
2. **边可解释：** 每条边必须注明引用来源、barrier机制、等待位置、超时后行为和验证证据。
3. **环检测：** 用拓扑排序或DFS检测cycle；cycle意味着设计无法满足全部先后约束。不得通过删边掩盖循环，必须重构owner/lease或拆分阶段。
4. **可达性：** 从A0开始，每个资源销毁节点都必须可由其所有使用者的drain barrier到达；孤立节点视为漏清理风险。
5. **终态覆盖：** 每个节点至少定义CLOSED/RELEASED、RESIDUAL_RETAINED、OUTCOME_UNKNOWN、NOT_APPLICABLE之一；禁止“没有记录即成功”。
6. **deadline闭包：** 超时只改变事务终态/处置策略，不自动解除引用边；仍有活跃使用者时必须保留owner。
7. **版本化：** resource graph revision与transaction plan revision绑定；实现变更需更新图和测试矩阵。

## 3. Platform-specific native close semantics evidence matrix

| Platform/API | 已核实公开语义 | 错误后的句柄策略 | 本项目建议 |
|---|---|---|---|
| Linux `close(2)` | fd在close早期释放，后续I/O/flush步骤仍可能报告错误；失败后重试可能关闭已复用fd | 除EBADF等明确无效情况外，不从整数fd推断仍有效；EINTR及其他错误按Linux适配策略视为fd不可再次操作 | 调用前从可用表原子摘除；一次调用；记录close result/error；不盲目retry |
| POSIX.1-2008 `close()` | caught signal导致EINTR时fd状态unspecified | 标准本身无法决定可否安全重试 | 不能只用“POSIX”配置；需绑定OS实现 |
| POSIX.1-2024 `close()/posix_close()` | close的EINTR语义已调整；posix_close提供flag控制行为；Linux man-pages记载Linux实现与新标准有差异 | 取决于采用的接口、flag、实现及编译目标 | 若未来采用，必须单独实现/测试适配器，不将规范文字直接等同Linux行为 |
| macOS `close(2)` | Apple历史man page记录EBADF/EINTR/EIO；当前目标版本的EINTR后fd状态尚未由本轮权威版本证据确认 | UNKNOWN/待平台验证 | 不得复用Linux假设；补充当前macOS SDK/XNU文档与版本化测试 |
| Windows Winsock `closesocket()` | socket值调用后可能立即复用；不得与同socket上的其他Winsock调用并发；linger影响graceful/abortive及阻塞行为 | WSAEWOULDBLOCK在文档规定的nonblocking+linger场景下表示socket仍有效、disconnect未启动；其他错误需按WSA错误契约逐项分类 | 先阻断并发I/O并drain overlapped operation；调用后立即使应用层handle不可见；按错误码显式映射，不套用POSIX errno |
| Windows CRT `_close()` / HANDLE close | 与Winsock SOCKET不是同一接口/类型 | 本轮未审计 | 禁止把SOCKET传给CRT close或把HANDLE当POSIX fd；另建adapter和证据项 |

### 3.1 Linux具体规则

Linux man-pages指出：fd会在close操作早期释放，因此即使后续步骤报告错误，fd也可能已经被另一个线程重新分配；失败后再次close同一个整数可能误关新资源。EINTR在POSIX.1-2008下曾是状态未指定的特殊情况，而Linux保证fd已关闭；man-pages 6.18说明POSIX.1-2024改变了相关标准行为，但Linux没有计划改变自身行为。

因此Linux adapter契约：
- 先以锁内状态迁移把ResourceHandle从OPEN转为CLOSING并从公开handle表摘除；
- 锁外执行单次`::close(fd)`；
- 无论返回值如何，都禁止把旧整数fd重新发布为OPEN；
- 成功映射CLOSED；错误映射CLOSED_WITH_ERROR或CLOSE_OUTCOME_REPORTED（根据错误分类保留诊断），但不自动重调close；
- EBADF表示调用时fd无效，标记OWNERSHIP_INVARIANT_BROKEN并调查重复close/外部关闭；
- 若需要持久化写入错误语义，应在close前按文件类型/业务需求执行fsync；socket teardown不应把文件fsync语义误套用。

### 3.2 Windows Winsock具体规则

- `closesocket`与socket上的其他Winsock调用不得并发；先停止新I/O并处理所有pending overlapped I/O的完成/取消回调。
- Microsoft文档指出，pending overlapped send/receive会被取消，completion event/routine/port action仍可能发生；所以关闭socket后仍需等待这些回调不再引用plugin/target/buffer。
- `SO_LINGER`影响close行为：默认linger关闭时函数可立即返回而后台完成graceful close；linger开启且timeout为0是abortive close；阻塞socket的非零timeout可能阻塞至发送完成或timeout；非阻塞socket在该配置下可能返回WSAEWOULDBLOCK，此时socket仍有效且disconnect未启动。
- 因此关闭预算必须显式区分API调用阻塞预算、协议graceful deadline与worker drain deadline。不得在ROS executor线程直接调用可能阻塞的closesocket。

### 3.3 Apple/macOS证据缺口

Apple历史man page列出了EINTR但未在该页面说明fd错误后状态；该来源年代较早。当前macOS目标版本、SDK与XNU close实现必须通过后续版本化资料确认。此处不从BSD/旧man page类推当前行为，也不把“Apple Darwin类Unix”当作足够精确的适配目标。

## 4. Residual resource reconciliation policy

### 4.1 状态模型

- **RESIDUAL_RETAINED：** 已知资源仍由本进程持有，owner和native identity均可追踪。
- **CLOSE_OUTCOME_UNKNOWN：** close调用返回结果不足以确定native对象状态；原整数句柄不得重新暴露。
- **ORPHANED_OWNER：** 资源存在但原owner控制块/任务关联异常；必须先恢复唯一owner记录。
- **REMOTE_SESSION_UNKNOWN：** 本地socket关闭不等于远端控制器会话已终止。
- **CALLBACK_RESIDUAL：** active/pending callback仍可能执行，禁止plugin unload和target析构。
- **THREAD_RESIDUAL：** worker仍运行或join失败，保留其访问的全部资源。
- **SEALED_CLEAN：** 所有资源终态确认且无残留引用。
- **SEALED_WITH_RESIDUAL：** 已达到shutdown policy终态，但残留仍被隔离/持有并可审计。

### 4.2 Reconciliation步骤

1. **Freeze identity：** 保存Core ID、generation、transaction ID、ResourceId、平台、API、原始错误码和调用时刻；不将裸fd/socket值作为唯一身份。
2. **Fence access：** 应用层handle立即不可见；所有新操作返回CLOSING/QUARANTINED。
3. **Check references：** 核对in-flight I/O、callback lease、worker、plugin code、buffer引用；任何非零引用阻止最终释放。
4. **Platform probe：** 仅使用平台文档明确安全的probe；禁止用再次close来“探测”原fd，也禁止仅凭EBADF推断目标资源已正确释放（它也可能表示被外部提前关闭）。
5. **Owner decision：** 已确认仍有效则由原owner继续保留或执行唯一允许的close；已确认关闭则将逻辑owner转为CLOSED；无法确认则保持CLOSE_OUTCOME_UNKNOWN并不复用句柄值。
6. **Remote reconciliation：** 对机器人控制器会话，若协议支持，使用独立的新连接/认证会话查询状态；本地close成功不得被解释为远端STOP/SAFE/IDLE确认。
7. **Escalation：** 超过预算后升级为operator-visible residual report；不得自动循环close、强制释放仍被引用对象或卸载plugin。
8. **Process exit：** 仅当残留不会造成进程内UAF/双重关闭/线程访问已析构对象时才可按明确策略退出；否则保留进程或进入经批准的forced-exit路径，并记录安全影响。

### 4.3 报告最小字段

`resource_id, core_id, generation, transaction_id, graph_revision, platform, os_version, api_name, handle_kind, close_attempt_sequence, raw_error_domain, raw_error_code, outcome_state, owner_state, active_reference_counts, retry_disposition, next_reconcile_action`。

报告中不得记录敏感payload；原始句柄值可只在受限诊断环境记录，普通日志使用ResourceId。

## 5. 确定性验证矩阵（全部NOT_RUN）

| ID | 验证 | 断言 | 状态 |
|---|---|---|---|
| DAG-01 | 构建资源依赖图并拓扑排序 | 图无环 | NOT_RUN |
| DAG-02 | 删除任一必要barrier边的mutation test | 测试能检测错误释放顺序 | NOT_RUN |
| DAG-03 | 每资源owner/ResourceId审计 | 无无主资源、无多owner | NOT_RUN |
| DAG-04 | deadline到期且callback仍active | 不释放target/plugin | NOT_RUN |
| DAG-05 | worker residual | buffer/socket owner保留 | NOT_RUN |
| DAG-06 | graph revision与transaction plan不匹配 | 拒绝执行旧plan | NOT_RUN |
| LINUX-01 | Linux close成功 | 应用层handle一次性失效 | NOT_RUN |
| LINUX-02 | Linux close注入EINTR | 不再次close相同fd整数 | NOT_RUN |
| LINUX-03 | close返回EIO/ENOSPC等 | 不将错误误判为fd仍开放 | NOT_RUN |
| LINUX-04 | fd在错误返回后被另线程复用 | 旧事务不关闭新资源 | NOT_RUN |
| POSIX-01 | POSIX.1-2008抽象EINTR | adapter输出UNKNOWN/平台策略而非通用retry | NOT_RUN |
| POSIX-02 | POSIX.1-2024适配配置 | 标准/接口/flag选择被显式记录 | NOT_RUN |
| MAC-01 | 指定macOS版本close EINTR行为 | 证据和适配策略匹配目标版本 | NOT_RUN |
| WIN-01 | closesocket与send/recv并发 | admission fence阻止并发调用 | NOT_RUN |
| WIN-02 | pending overlapped I/O close | completion/cancel回调完成前不卸载target | NOT_RUN |
| WIN-03 | nonblocking+linger WSAEWOULDBLOCK | handle仍有效且不误标closed | NOT_RUN |
| WIN-04 | linger graceful/abortive配置 | deadline和结果分类准确 | NOT_RUN |
| RES-01 | close outcome unknown | handle不可见、不盲目重试 | NOT_RUN |
| RES-02 | 本地close成功但remote session未知 | 不报告remote STOP/IDLE | NOT_RUN |
| RES-03 | residual owner transfer | owner唯一且生命周期覆盖残留 | NOT_RUN |
| RES-04 | reconciliation重复执行 | probe/状态迁移幂等 | NOT_RUN |
| RES-05 | callback/thread residual | 不卸载plugin、不释放引用资源 | NOT_RUN |
| RES-06 | residual report生成失败 | 不改变owner与隔离状态 | NOT_RUN |

## 6. 待决策与实施门禁

待决策：
- Stäubli driver支持的实际操作系统与版本矩阵；若只支持Linux，应在构建/运行配置中显式限制，而不是保留未经验证的泛POSIX假设。
- Linux adapter对EBADF的分类是否作为内部fatal invariant violation。
- macOS是否属于产品目标；若是，必须补当前版本close语义证据。
- Windows是否属于产品目标；若否，Windows矩阵仅作接口设计对照，不纳入发布验收。
- ROS callback/executor shutdown与transport owner的实际引用边。
- 机器人远端session状态查询协议及安全状态确认机制。

实施门禁：
1. 从固定上游源码提取所有socket/fd/worker/callback/buffer/plugin owner和close调用点；
2. 生成实际资源DAG，并为每条边绑定源码位置与测试；
3. 按目标OS版本建立close adapter证据矩阵；
4. 用fake native backend和fd/socket reuse injection测试；
5. Linux上执行fd reuse、EINTR/error injection、double-close和leak测试；
6. 若目标包含Windows/macOS，再分别在对应原生环境执行adapter测试；
7. TSan/ASan/UBSan与ROS component/plugin unload；
8. ROS 2 Control、VAL3/CS9、SIL/HIL、FAT/SAT和实机验收。

## 7. 公开依据

- Linux man-pages `close(2)`：https://man7.org/linux/man-pages/man2/close.2.html
- Linux man-pages 6.18 PDF（2026-02-08）：https://www.kernel.org/pub/linux/docs/man-pages/book/man-pages-6.18.pdf
- POSIX close(3p)参考页面（POSIX.1-2008语义）：https://man.archlinux.org/man/close.3p
- Apple archived Mac OS X `close(2)` manual：https://developer.apple.com/library/archive/documentation/System/Conceptual/ManPages_iPhoneOS/man2/close.2.html
- Microsoft Winsock `closesocket`：https://learn.microsoft.com/en-us/windows/win32/api/winsock/nf-winsock-closesocket
- Microsoft graceful shutdown/linger/socket closure：https://learn.microsoft.com/en-us/windows/win32/WinSock/graceful-shutdown-linger-options-and-socket-closure-2
- Microsoft Winsock `closesocket` behavior summary：https://learn.microsoft.com/en-us/windows/win32/api/winsock2/nf-winsock2-closesocket

## 8. 状态与下一节点

- **已完成：** 候选资源DAG、边语义、DAG验证规则、Linux/POSIX/macOS/Windows close evidence matrix、residual resource状态机与reconciliation流程。
- **未完成：** 尚未从固定上游逐行提取真实资源图；macOS当前版本语义证据不完整；Windows是否为目标平台未决；平台adapter和reconciliation均未实现。
- **验收状态：** DAG-01至04、LINUX-01至04、POSIX-01至02、MAC-01、WIN-01至04、RES-01至06全部NOT_RUN。
- **未执行：** C++17编译、CMake、gtest、native close错误注入、fd/socket reuse、double-close/leak、TSan/ASan/UBSan、macOS/Windows原生测试、ROS component/plugin集成、ROS 2 Control、VAL3/CS9、SIL/HIL、FAT/SAT或实机测试。
- **上游边界：** 未修改固定上游、未创建/应用/合并PR；`TODO-EXT-001`仍未授权。
- **历史同步：** 第21章TaskPlan正文仍存在§9.3.281–§9.3.294逐节点同步缺口；本轮不伪造回填。
- **下一节点：** §9.3.301 / SERVO-884：SocketV2 source-level resource ownership inventory、close-site traceability matrix 与 real implementation dependency DAG extraction。
