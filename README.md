# Robot Knowledge Basement

面向机器人系统的知识采集、组织、检索与增强生成（RAG）基础设施。

**Robot Knowledge Basement** 旨在成为机器人研发与运维知识的统一入口：将设备文档、传感器/执行器说明、ROS 资料、导航与操作经验、故障案例等内容沉淀为可追溯、可检索、可持续维护的知识资产。

> 当前版本是一个轻量、可扩展的 Python 项目骨架。核心流程先保持存储与模型无关，后续再按实际需求接入向量数据库、Embedding 服务、LLM 和 ROS。

## Goals

- **Knowledge ingestion**：统一接入 Markdown、纯文本及后续扩展的 PDF、网页和机器人日志。
- **Structured knowledge**：按机器人、传感器、执行器、导航、操作和故障排查组织知识。
- **Retrieval-ready**：提供文档切分、元数据和检索接口的稳定边界。
- **RAG foundation**：为后续检索增强问答、Agent 和工程工具提供基础。
- **Traceability**：保留来源、设备型号、版本、时间和标签等元数据。

## Repository layout

```text
.
├── configs/                 # Runtime configuration examples
├── data/
│   ├── raw/                 # Original imported files (not committed)
│   ├── processed/            # Parsed/chunked artifacts (not committed)
│   └── embeddings/           # Embedding artifacts (not committed)
├── docs/                    # Design notes and developer docs
├── knowledge/
│   ├── robots/
│   ├── sensors/
│   ├── actuators/
│   ├── navigation/
│   ├── manipulation/
│   └── troubleshooting/
├── scripts/                 # Utility scripts
├── src/robot_knowledgebase/
│   ├── ingest/               # Loading and parsing
│   ├── retrieval/            # Retrieval interfaces
│   ├── embeddings/            # Embedding interfaces
│   └── llm/                   # Generation interfaces
└── tests/
```

## Quick start

Requires Python 3.10+.

```bash
git clone https://github.com/rexyll/robot_knowledgebasement.git
cd robot_knowledgebasement

python -m venv .venv
# macOS / Linux
source .venv/bin/activate
# Windows PowerShell
# .venv\\Scripts\\Activate.ps1

python -m pip install -e ".[dev]"
pytest
```

## First example

The initial scaffold exposes small, dependency-light primitives for loading Markdown and splitting text into chunks. See `docs/architecture.md` and `src/robot_knowledgebase/` for details.

## Knowledge document convention

A knowledge Markdown file should include useful provenance in YAML front matter where possible:

```yaml
---
title: Differential drive calibration
category: navigation
robot: my_robot
source: internal_field_notes
version: 1
tags: [odometry, calibration, ros]
updated: 2026-01-01
---
```

Keep original source material in `data/raw/` (excluded from Git) and commit curated, reusable knowledge under `knowledge/`.

## Development

```bash
ruff check .
ruff format --check .
pytest
```

## Roadmap

- [x] Establish repository structure and Python package metadata
- [x] Add configuration example and knowledge templates
- [x] Add Markdown ingestion and deterministic text chunking
- [ ] Add pluggable embedding providers
- [ ] Add local/vector database adapters
- [ ] Add hybrid retrieval and ranking
- [ ] Add RAG API and CLI
- [ ] Add ROS 2 documentation/log ingestion examples

## License

MIT. See [LICENSE](LICENSE).
