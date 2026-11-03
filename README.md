# Robot Knowledge Basement

面向机器人研发、系统集成与运维的结构化知识库，同时提供轻量 Python 知识摄取与检索基础设施。

本仓库包含两部分：

- **Knowledge Vault**：机器人类型、硬件、软件、算法、系统架构、项目实践和从零搭建指南。
- **Python Toolkit**：Markdown 导入、元数据解析、文本切块，以及可扩展的 Embedding / Retrieval 接口。

## Knowledge entry points

- [知识库总目录](knowledge/README.md)
- [知识地图](knowledge/maps/README.md)
- [零基础学习路径](knowledge/getting-started/00-零基础学习路径.md)
- [从零到量产路线](knowledge/getting-started/端到端产品化路线总览.md)
- [知识分类与元数据规范](docs/knowledge-schema.md)
- [系统架构说明](docs/architecture.md)
- [知识库编写规范](docs/编写规范.md)
- [来源链接台账](docs/链接台账.md)
- [全域知识体系建设 TaskPlan](TaskPlan.md)
- [TaskPlan 分册索引](docs/TaskPlan/README.md)
- [Local 分支整理说明](docs/merge-notes.md)

## Main knowledge domains

| Domain | Content |
| --- | --- |
| robots | Robot families and application domains |
| sensors / actuators | Sensors, drive components, encoders and calibration |
| mechanics / power / safety / computing | Chassis, energy, safety devices and compute platforms |
| software / algorithms / navigation | ROS, Nav2, middleware, SLAM, localization, planning and control |
| architecture / parameters | System workflows, system architecture and engineering metrics |
| ecosystem / projects | Industry, vendors, standards and project case studies |
| getting-started / examples | End-to-end robot build guides and code examples |

The knowledge articles retain their Chinese titles and Obsidian WikiLinks so the vault remains easy to navigate in Obsidian. GitHub users can browse the Markdown files directly from the [knowledge index](knowledge/README.md).

## Python toolkit quick start

Requires Python 3.10+.

```bash
git clone https://github.com/rexyll/robot_knowledgebasement.git
cd robot_knowledgebasement

python -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
pytest
```

Inspect and chunk a knowledge article:

```bash
robot-kb inspect knowledge/navigation/differential-drive-odometry.md
robot-kb chunk knowledge/navigation/differential-drive-odometry.md --chunk-size 1000 --overlap 150
```

## Development checks

```bash
ruff check .
ruff format --check .
pytest
```

GitHub Actions runs lint and tests on Python 3.10, 3.11 and 3.12.

## Repository map

```text
configs/                    Runtime configuration
docs/                       Architecture, schema, writing rules and source ledger
knowledge/                  Curated robotics knowledge vault
src/robot_knowledgebase/    Python ingestion and retrieval toolkit
data/                       Local raw/processed/embedding data (ignored by Git)
tests/                      Unit tests
scripts/                    Maintenance and ingestion utilities
```

## Data and contribution rules

Keep one primary topic per article where practical. Record source, date, versions, test conditions and applicable hardware. Clearly label illustrative or unverified procedures. Do not commit credentials, private keys, personal data, confidential customer logs or large binaries.

See [knowledge writing guidelines](docs/编写规范.md) before adding or reorganizing knowledge.
