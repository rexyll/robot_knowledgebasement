# Knowledge schema

Use Markdown with a small, consistent front matter block. Keep one primary topic per file where practical. Chinese article titles are preserved; directory names use stable English domain names.

## Front matter

```yaml
---
title: Differential drive odometry calibration
category: navigation
robot: example_mobile_base
source: field_notes
version: 1
tags: [odometry, wheel_radius, wheel_base, ros2]
updated: 2026-01-01
---
```

Legacy Obsidian notes may contain additional fields such as `aliases`, `创建日期`, and `更新日期`. Preserve source metadata when migrating. The Python core parser handles common flat key/value fields and inline lists; it is not a full YAML implementation.

## Knowledge domains

| Category | Directory | Typical content |
| --- | --- | --- |
| robots | `knowledge/robots/` | Robot families, applications and platform profiles |
| sensors | `knowledge/sensors/` | LiDAR, cameras, IMU, radar, encoders and calibration |
| actuators | `knowledge/actuators/` | Motors, drives, reducers and end effectors |
| navigation | `knowledge/navigation/` | Localization, navigation and odometry practice |
| manipulation | `knowledge/manipulation/` | Kinematics, grasping, motion planning and end effectors |
| troubleshooting | `knowledge/troubleshooting/` | Symptoms, diagnosis, mitigations and recovery |
| mechanics | `knowledge/mechanics/` | Chassis, locomotion mechanisms, mechanical design and materials |
| power | `knowledge/power/` | Batteries, power distribution, charging and energy |
| safety | `knowledge/safety/` | Safety devices, risk assessment and functional safety |
| computing | `knowledge/computing/` | Compute platforms, SoCs, MCUs and industrial PCs |
| software | `knowledge/software/` | ROS, middleware, Nav2, simulation, embedded software and cloud |
| algorithms | `knowledge/algorithms/` | SLAM, localization, planning, perception, control and learning |
| architecture | `knowledge/architecture/` | System architecture and operational workflows |
| parameters | `knowledge/parameters/` | Engineering parameters, comparisons and performance metrics |
| ecosystem | `knowledge/ecosystem/` | Vendors, industry, standards and market context |
| projects | `knowledge/projects/` | Project-specific architecture and engineering notes |
| getting-started | `knowledge/getting-started/` | End-to-end robot design and bring-up guides |
| examples | `knowledge/examples/` | Code examples, source repositories and license notes |
| maps | `knowledge/maps/` | Knowledge maps and navigation entry points |

## Provenance and safety

Record affected hardware and software versions, source, test conditions, and date for operational procedures. Clearly label unverified or illustrative notes. External links should be tracked in `docs/链接台账.md`. Do not put credentials, private keys, personal data, or sensitive customer logs in the repository.

## Migration rules

- Keep existing main-branch files unless a documented consolidation is necessary.
- Move notes into the closest existing domain first; create a new domain only for a durable topic that spans multiple notes or has its own navigation needs.
- Keep filenames and aliases where practical to avoid breaking Obsidian WikiLinks.
- Keep vault maps, glossaries and editorial governance outside technical domain directories.
