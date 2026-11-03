---
title: LiDAR Integration Checklist
category: sensors
robot: example_mobile_base
source: project_template
version: 1
tags: [lidar, tf, ros2, sensor_validation]
status: illustrative
---

# LiDAR Integration Checklist

> Template checklist only. Confirm the sensor manufacturer's specifications and the robot's safety requirements before deployment.

## Mechanical and electrical

- [ ] Confirm mounting rigidity and field of view.
- [ ] Verify supply voltage, current budget, connector pinout, and grounding.
- [ ] Check cable strain relief and environmental rating.

## Software and coordinate frames

- [ ] Confirm the driver version and supported firmware.
- [ ] Verify timestamp behavior and expected scan frequency.
- [ ] Confirm the published topic and message type.
- [ ] Verify the sensor frame exists in the TF tree and its transform is measured.
- [ ] Check range limits, angle limits, and invalid-return encoding.

## Validation

- [ ] Inspect data while stationary and while moving.
- [ ] Compare scan geometry against known physical dimensions.
- [ ] Check for dropped messages and timestamp discontinuities.
- [ ] Record hardware serial/model, firmware, driver version, ROS distribution, and test environment.
