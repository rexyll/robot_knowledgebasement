# Knowledge schema

Use Markdown with a small, consistent front matter block. Keep one primary topic per file where practical.

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

## Suggested categories

| Category | Typical content |
| --- | --- |
| robots | Robot platform profiles, specifications, frames, capabilities |
| sensors | Cameras, LiDAR, IMU, force/torque, calibration |
| actuators | Motors, drives, grippers, controllers |
| navigation | Localization, mapping, planning, odometry |
| manipulation | Kinematics, grasping, motion planning, end effectors |
| troubleshooting | Fault symptoms, diagnosis, mitigations, recovery |

## Safety and provenance

Record the affected hardware and software versions, source, test conditions, and date for operational procedures. Clearly label unverified community notes. Do not put credentials, private keys, personal data, or sensitive customer logs in the repository.
