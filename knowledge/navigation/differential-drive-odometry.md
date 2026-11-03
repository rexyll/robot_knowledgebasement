---
title: Differential Drive Odometry Calibration
category: navigation
robot: example_mobile_base
source: project_template
version: 1
tags: [odometry, wheel_radius, wheel_base, ros2]
status: illustrative
---

# Differential Drive Odometry Calibration

> Template note: replace the illustrative values and procedure with measurements validated on your own robot before operational use.

## Purpose

Differential-drive odometry estimates planar motion from the rotation of the left and right drive wheels. Calibration reduces systematic error caused by wheel-radius mismatch and uncertainty in the effective wheel separation.

## Parameters

- **Left wheel radius**: measured or calibrated effective radius of the left wheel.
- **Right wheel radius**: measured or calibrated effective radius of the right wheel.
- **Effective wheel separation**: distance between the effective rolling paths of the two wheels.
- **Encoder scale**: conversion from encoder counts to wheel rotation.

## Suggested validation procedure

1. Verify encoder direction and counts-per-revolution with the robot safely lifted.
2. Measure a straight-line run over a marked distance at a conservative speed.
3. Compare estimated travel with the measured distance; adjust effective wheel radii or encoder scale.
4. Perform an in-place rotation and compare estimated yaw with an external reference.
5. Repeat in both directions and at multiple speeds to identify asymmetry and slip.

## Recordkeeping

Record the robot identifier, wheel/tire revision, payload, floor surface, firmware, ROS distribution, measurement method, raw trials, and final parameter values. Do not copy generic calibration constants into a production robot without testing.
