---
title: LiDAR Integration Checklist
category: sensors
robot: project_specific
version: 2
tags: [lidar, tf, ros2, sensor_validation]
status: illustrative
---

# LiDAR Integration Checklist

This is a project checklist, not a product validation report. Fill it with the exact sensor model, documentation, robot configuration and recorded test results. Navigation LiDAR is not automatically a safety-rated scanner.

## Model and documentation
- [ ] Manufacturer, complete model/order code, serial number, hardware and firmware revision.
- [ ] Datasheet, user manual, protocol, driver/SDK version and product label.
- [ ] Intended use: mapping, localization, perception, measurement or other defined task.
- [ ] Operating mode and saved configuration revision.

## Mechanical and electrical
- [ ] Mounting rigidity, measured transform, field of view, occlusion and blind regions.
- [ ] Supply range, current, connector pinout, protective bonding, cable routing and EMC.
- [ ] Vibration, shock, thermal conditions, cleaning method and environmental rating.
- [ ] Optical classification and precautions from the exact product label/manual.

## Software, timing and frames
- [ ] OS, driver, firmware, SDK compatibility and license.
- [ ] Topic/message type, units, range/angle limits, invalid-return encoding and diagnostics.
- [ ] Timestamp meaning, scan timing, synchronization, latency and dropped-message handling.
- [ ] Sensor frame and measured transform in the robot TF tree.
- [ ] Time alignment with IMU/odometry and motion-compensation needs.

## Scenario validation
- [ ] Target size/material/reflectivity, distance, incidence angle and motion.
- [ ] Robot speed, direction, turn, load and final mounting geometry.
- [ ] Intended ambient light, temperature, dust/water and contamination conditions.
- [ ] Accuracy/repeatability measurement against a reference target.
- [ ] Task-relevant detection, missed detection, data loss, reboot and reconnect tests.
- [ ] Record deviations, configuration, test files, acceptance decision and responsible reviewer.

## Release and maintenance
- [ ] Save calibration/configuration against robot serial number and software release.
- [ ] Define cleaning, replacement, recalibration, firmware update and supplier-change triggers.
- [ ] If connected to a safety function, use a separate risk assessment and safety verification process; this checklist alone is not evidence of that function.
