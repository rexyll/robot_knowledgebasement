# Local → Main migration map

This file records the folder-level classification used when integrating the `local` branch into `main`. Original Chinese article filenames and Markdown bodies were retained to preserve Obsidian links and source provenance.

| Local source | Main destination | Classification |
| --- | --- | --- |
| `00-导航/` | `knowledge/maps/` | Navigation maps and MOC pages |
| `00-导航/编写规范.md` | `docs/编写规范.md` | Editorial governance |
| `01-机器人分类/` | `knowledge/robots/` | Existing main category: robots |
| Hardware sensor notes in `02-硬件/` | `knowledge/sensors/` | Existing main category: sensors |
| Motors and reducers in `02-硬件/` | `knowledge/actuators/` | Existing main category: actuators |
| Chassis / motion mechanism | `knowledge/mechanics/` | New category: mechanics |
| Battery / charging / power design | `knowledge/power/` | New category: power |
| Safety devices | `knowledge/safety/` | New category: safety |
| Compute platform | `knowledge/computing/` | New category: computing |
| `03-软件/` | `knowledge/software/` | New category: software |
| `04-算法/` | `knowledge/algorithms/` | New category: algorithms |
| `05-流程与架构/AMR整体架构.md` | `knowledge/architecture/` | New category: architecture |
| Other `05-流程与架构/` notes | `knowledge/architecture/workflows/` | Workflow subcategory |
| `06-核心参数/` | `knowledge/parameters/` | New category: parameters |
| `07-行业与生态/` | `knowledge/ecosystem/` | New category: ecosystem |
| Hardware vendor resource index | `knowledge/ecosystem/manufacturers/` | Ecosystem subcategory |
| `08-项目/` | `knowledge/projects/` | New category: projects |
| `09-从0搭建指南/` | `knowledge/getting-started/` | New category: getting-started |
| `10-代码实例/` | `knowledge/examples/` | New category: examples |
| `11-扩展知识/` | `knowledge/software/advanced-topics/` | Software advanced topics |
| `首页.md` | `knowledge/maps/首页.md` | Knowledge entry page |
| `术语表.md` | `knowledge/术语表.md` | Shared glossary |
| `TaskPlan.md` | `docs/TaskPlan.md` | Project / maintenance history |
| `链接台账.md` | `docs/链接台账.md` | External-source governance |

## Files intentionally not merged

- `.obsidian/workspace.json`: machine/session-specific open panes and workspace state.
- No local knowledge article was intentionally omitted. Obsidian app preferences and core plugin settings were retained.
