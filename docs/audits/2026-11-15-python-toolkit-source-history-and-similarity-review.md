# 00-01｜Python Toolkit 13 项实际发布文件的 Git 来源与代码相似性审查（2026-11-15）

## 1. 审查范围

本报告跟进 wheel/sdist 实测清单，对实际进入 Python Toolkit 分发物的 11 个 Python 模块和 2 个测试文件逐路径核查 Git 历史、提交身份、文件内容和公开代码相似性线索。

- 固定仓库基线：main@aac8e081ca733265f34b08000647473d02e23e72
- 本轮审查所依据的 PR head：8e95dbca3ae459b22300ed007bdb6db9da494770
- 分发物清单：2026-11-15-python-distribution-file-manifest.json
- wheel：11 个包模块；sdist：上述 11 个包模块 + tests/test_chunker.py、tests/test_markdown.py。
- GitHub REST per-path commits、完整 commit metadata 与当前文件正文均已读取；代码相似性检索仅覆盖若干高信号字符串，不是全网穷尽式抄袭检测。

## 2. 逐文件 Git 历史

| 发布文件 | 路径历史记录数 | 首次加入提交 | 后续修改提交 |
|---|---:|---|---|
| src/robot_knowledgebase/__init__.py | 1 | ccc9393dc9c18a9e098b2bf0d9b049f0ec169cc2 | 无 |
| src/robot_knowledgebase/cli.py | 1 | 744f70f8df0355af7bf74d5817b23d30e49bf037 | 无 |
| src/robot_knowledgebase/embeddings/__init__.py | 1 | 17d9f8ee1847428462d5fa2abc98631bc15758b4 | 无 |
| src/robot_knowledgebase/embeddings/base.py | 2 | 8aadd2f928f576d9c474b8c8a979dc30c7f962d9 | 83f08d91306547485d8618dc6e772783357fd17e |
| src/robot_knowledgebase/ingest/__init__.py | 1 | 28f307dacf2799edea17fc00889fcd06ef6de9a0 | 无 |
| src/robot_knowledgebase/ingest/chunker.py | 1 | 2ed203a1c671dd4c13c9b390beceda9a97e0c35e | 无 |
| src/robot_knowledgebase/ingest/markdown.py | 3 | 55007dcf088962fd7aa97144e2f5927c7420038b | 1cab4fcb66c5320ec0d7b87d2a2dc4974f05f5d3、caa0b596b270df870aef080a0d784492ef02132c |
| src/robot_knowledgebase/llm/__init__.py | 1 | 3a6a90bd3e00c410aa422fe342d1b64dfb628637 | 无 |
| src/robot_knowledgebase/models.py | 1 | cbd596fba455dda754eac06d827a2dc51a629290 | 无 |
| src/robot_knowledgebase/retrieval/__init__.py | 1 | ccfdb0edb99887655cb3998dddd58d4c00f787a0 | 无 |
| src/robot_knowledgebase/retrieval/base.py | 2 | 7ba4ffa29ed134c8851cbe931ae494f8b3f17273 | 5b79b6c63c71d271c9a950a3c0146bc352a291c8 |
| tests/test_chunker.py | 1 | 983d90f077e67f10981beb6677ce619f3cd64128 | 无 |
| tests/test_markdown.py | 1 | 6ed4ef7a316c20ba9a1c3cbea1b4bdaee71af491 | 无 |

**历史汇总：** 13 个文件均有路径历史；共 17 条路径历史 commit 记录（13 次新增、4 次后续修改）。记录中的 GitHub author/committer 均为仓库账号 rexyll。逐一读取这 17 个 commit 的 GitHub verification 字段，均为 verified=false、reason=unsigned。也就是说，Git 历史一致显示该账号为提交署名主体，但没有签名验证证据；GitHub 账号、提交邮箱或未签名的 commit 都不能单独证明自然人身份、雇佣/委托关系、版权归属或再分发授权。

### 2.1 文件内容静态检查

13 个文件的当前正文和首次加入 patch 已抽查。内容主要是 CLI 参数解析、dataclass 数据对象、分块与 Markdown front matter 的简化解析、EmbeddingProvider/Retriever Protocol 以及对应测试。文件中未发现明确的版权声明、第三方来源注释、vendor 标记或生成器来源标记。

这只表示当前文件和这些提交 patch 未提供明确来源标注；不能据此推断没有参考、改写、AI 辅助生成或复制第三方实现。尤其是简短通用接口、数据类和常见算法，单看仓库内部历史无法建立完整的创作来源链。

## 3. chunker.py 的公开相似性线索

GitHub code search 对说明文字 “Split text into overlapping chunks, preferring whitespace boundaries.” 返回两个较早的公开项目命中。对命中的文件和历史进一步比较如下。

### 3.1 Camila20197/cattle-raising-assistant

- 原始文件在 2026-08-08T19:38:56Z 的提交 934f93998a2c5dc0cd5472f756d97fd499c4d8ba 中可见，路径为 src/ingetion/chunker.py；2026-08-09 的 00db33d24852aba0ab32ff4c21d35ea7988da505 将该路径更正/重命名为 src/ingestion/chunker.py。
- 原始文件实现 split_text，默认 chunk_size=1000、overlap=200；使用 start/end 窗口、空格边界截断、重叠回退，并使用 start = max(end - overlap, start + 1) 保证前进。
- 本仓库 chunk_text 的默认值为 chunk_size=1000、overlap=150，同样使用 start/end 窗口、空格边界截断和重叠回退；表达式为 start = max(start + 1, end - overlap)。本仓库还将文本先 strip，并仅在窗口后半段搜索边界，因此并非逐行相同，但整体控制流程和重叠分块思路相近。
- 对方仓库 API license 字段为 null；根目录 LICENSE 路径请求返回 404。当前没有找到可据以确认再利用许可的仓库级许可信息。
- 文件链接：[原始提交中的 chunker.py](https://github.com/Camila20197/cattle-raising-assistant/blob/934f93998a2c5dc0cd5472f756d97fd499c4d8ba/src/ingetion/chunker.py)。

### 3.2 vvadr/Multi-Agent-AI-Analyst

- 公开文件版本对应提交 6839cfb56bef7f9284363c55dd3e85ea9e346270，提交日期为 2026-08-19。
- 文件也使用相同的通用说明文字；其实现将空白归一化为单空格，并额外处理重叠窗口落在单词中间的情况，与本仓库代码并不相同。
- 对方仓库 API license 字段为 null；根目录 LICENSE 路径请求返回 404。
- 文件链接：[chunking.py](https://github.com/vvadr/Multi-Agent-AI-Analyst/blob/6839cfb56bef7f9284363c55dd3e85ea9e346270/backend/app/ingestion/chunking.py)。

### 3.3 判定边界

上述时间均早于本仓库对应 chunker.py 的首次加入提交（2026-11-03T05:32:19Z）。这构成需要向实际作者确认的来源相似性线索，但不是代码抄袭或衍生关系的证明：重叠文本分块属于常见算法模式，通用 docstring 也可能来自相似提示词或独立实现。当前没有证据确认本仓库使用了任一外部仓库的代码，也没有证据排除这种可能。

对于 markdown.py 的特有 docstring，本轮精确字符串搜索未发现相同结果；但代码搜索索引不完整，不能作为全量相似性 clearance。对 EmbeddingProvider 等通用接口名称的搜索命中也不构成代码复制证据。

## 4. 对权利与分发状态的影响

- 13/13 个文件的 Git 历史追溯已完成到可见提交记录；这不是法律意义上的作者/权利人证明。
- 13/13 仍保持 rights_holder_status=UNVERIFIED、redistribution_status=UNDETERMINED；没有任何文件获准再分发。
- chunker.py 单独标记为潜在外部相似性待确认；两个候选源的 GitHub 仓库许可证元数据均为空，已核查的根 LICENSE 路径也未找到。没有从这些线索中获得许可授权。
- 不修改根 LICENSE，不添加覆盖性 MIT SPDX 声明，不把 pyproject.toml 改为 SPDX MIT，也不将此结论外推到 Knowledge Vault。
- 不从这两个外部项目复制或导入任何文件；本次只读取公开代码做相似性比对。

## 5. 解除阻塞所需证据

1. 由实际作者/权利人确认 13 个文件的创作来源：独立编写、AI 辅助生成、基于教程/公共领域材料，或参考/改写了具体项目；如有共同作者、雇主、客户或委托方权利，须明确其权利范围。
2. 对 chunker.py 的相似性线索作出来源说明。若确有借用或衍生，取得可验证的许可/授权并落实署名、NOTICE、许可证文本及其他义务；若没有借用，应保留独立来源说明和设计/开发证据。
3. 将来源与权利证据回填到逐路径登记表。只有证据足以覆盖实际 wheel/sdist 文件及再分发范围时，才讨论 MIT/SPDX metadata 迁移。
4. sdist 独立解包、安装和两项 Toolkit 测试 smoke test 已完成：Run #43711114308 首次通过，并在当前 PR HEAD 的 Run #43711328493 再次通过；Python 3.12.16 上从临时解包目录安装，两个测试文件共 10 passed，模块导入路径确认位于独立 venv，CLI 输出 robot-kb 0.1.0；当前 HEAD 证据 artifact ID 14160676005。后续包成员/构建后端变更时必须复跑。

**结论：** 本轮完成了 13 个实际发布源码/测试文件的 Git 路径历史与静态来源线索审查，发现 chunker.py 存在待确认的公开相似性线索；独立 sdist 解包、安装和测试已由 CI Run #43711114308 首次通过，并由当前 PR HEAD 的 Run #43711328493 复验通过。权利人身份和再分发授权依然未证实，13/13 文件仍不得标为可再分发，00-01 继续进行中。本报告是技术来源审计记录，不替代法律意见。
