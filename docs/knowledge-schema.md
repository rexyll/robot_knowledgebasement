# Knowledge schema

Use Markdown with a small, consistent front matter block. Keep one primary topic per file where practical. Chinese article titles are preserved; directory names use stable English domain names. The directory table distinguishes current folders from planned destinations; a planned path is not evidence that content already exists.

## Front matter

    ---
    title: Differential drive odometry calibration
    category: navigation
    document_type: technical_reference
    robot: example_mobile_base
    source:
      - title: Manufacturer manual
        url: https://example.invalid/manual
        accessed: 2026-11-03
    version: 1
    tags: [odometry, wheel_radius, wheel_base, ros2]
    updated: 2026-11-03
    prerequisites: [basic_geometry, linux_cli]
    learning_objectives: [derive_wheel_odometry, calibrate_wheel_radius]
    maturity: M1
    status: draft
    ---

Legacy Obsidian notes may contain additional fields such as aliases, 创建日期, and 更新日期. Preserve source metadata when migrating. The Python core parser handles common flat key/value fields and inline lists; it is not a full YAML implementation. The example above describes the desired conceptual schema; do not assume the current parser supports nested objects unless tests confirm it.

## Metadata semantics

| Field | Meaning |
| --- | --- |
| document_type | beginner_lesson, technical_reference, engineering_process, artifact_template, product_profile, standard_card, project_case, troubleshooting_case, map/index |
| prerequisites | Knowledge or skills required before following the page |
| learning_objectives | Observable abilities after reading/doing the page |
| maturity | M0 placeholder, M1 overview, M2 learnable, M3 engineering reference, M4 stage-review ready, M5 project-verified |
| status | draft, review, verified, deprecated, historical |
| source | Source(s) supporting facts, values, tables or procedures; link each important claim to a specific source where feasible |

## Current knowledge domains

| Domain | Directory | Typical content | State |
| --- | --- | --- | --- |
| robots | knowledge/robots/ | Robot families, applications and platform profiles | Existing |
| sensors | knowledge/sensors/ | LiDAR, cameras, IMU, radar, encoders and calibration | Existing |
| actuators | knowledge/actuators/ | Motors, drives, reducers and end effectors | Existing |
| navigation | knowledge/navigation/ | Localization, navigation and odometry practice | Existing |
| manipulation | knowledge/manipulation/ | Kinematics, grasping, motion planning and end effectors | Placeholder only |
| troubleshooting | knowledge/troubleshooting/ | Symptoms, diagnosis, mitigations and recovery | Placeholder only |
| mechanics | knowledge/mechanics/ | Chassis, locomotion mechanisms, mechanical design and materials | Existing |
| power | knowledge/power/ | Batteries, power distribution, charging and energy | Existing |
| safety | knowledge/safety/ | Safety devices, risk assessment and functional safety | Existing; needs expansion |
| computing | knowledge/computing/ | Compute platforms, SoCs, MCUs and industrial PCs | Existing |
| software | knowledge/software/ | ROS, middleware, Nav2, simulation, embedded software and cloud | Existing; mixed scope |
| algorithms | knowledge/algorithms/ | SLAM, localization, planning, perception, control and learning | Existing |
| architecture | knowledge/architecture/ | System architecture and operational workflows | Existing |
| parameters | knowledge/parameters/ | Engineering parameters, comparisons and performance metrics | Existing |
| ecosystem | knowledge/ecosystem/ | Vendors, industry, standards and market context | Existing; source audit needed |
| projects | knowledge/projects/ | Project-specific architecture and engineering notes | Existing; public disclosure audit needed |
| getting-started | knowledge/getting-started/ | Beginner learning, sample builds and end-to-end productization | Existing |
| examples | knowledge/examples/ | Code examples, source repositories and license notes | Existing; license review required |
| maps | knowledge/maps/ | Knowledge maps and navigation entry points | Existing |
| system-engineering | knowledge/system-engineering/ | Product definition, requirements, systems architecture and traceability | Planned; not yet established |
| electronics | knowledge/electronics/ | Circuits, PCB, wiring, EMC/ESD, power distribution and electrical design | Planned; currently scattered across getting-started/power |
| embedded | knowledge/embedded/ | Bootloaders, BSP, HAL, firmware, peripheral and device drivers | Planned; currently partial notes in software |
| networking | knowledge/networking/ | Wired/wireless networks, industrial buses, timing and middleware protocols | Planned; currently scattered across software/guides |
| applications | knowledge/applications/ | HMI, user workflows, industry integrations and human-robot interaction | Planned; mostly represented by project examples |
| cloud | knowledge/cloud/ | Device identity, telemetry, OTA, remote operations and cloud-edge management | Planned; introductory page currently in software |
| fleet-management | knowledge/fleet-management/ | RMS/FMS, task assignment, traffic control, charging and fleet operations | Planned; introductory pages currently in algorithms/software |
| bom | knowledge/bom/ | EBOM/MBOM/SBOM, sourcing, alternatives, costing and lifecycle risk | Planned; sample BOM only in getting-started |
| validation | knowledge/validation/ | DVP&R, SIL/HIL, reliability, production test and acceptance | Planned; sample bring-up test only in getting-started |
| standards | knowledge/standards/ | Standards, regulations, certification pathways and compliance evidence | Planned; existing overview requires source/version audit |
| data-ai | knowledge/data-ai/ | Data collection, labeling, ML/AI lifecycle and embodied intelligence | Planned; partial learning-algorithm overview exists |
| operations | knowledge/operations/ | NPI, manufacturing, production quality, delivery, service and retirement | Planned; project workflows need expansion |

## Provenance, safety and publication

Record affected hardware and software versions, source, test conditions, and date for operational procedures. Important numeric or safety-critical claims should point to the exact source supporting the claim, not merely a vendor home page. Clearly label unverified or illustrative notes. External links should be tracked in docs/链接台账.md.

Do not put credentials, private keys, personal data, sensitive customer logs, internal network details or unnecessary local absolute paths in the public repository. Project case studies must be approved for public disclosure and distinguish documented facts from inference.

## Migration rules

- Keep existing main-branch files unless a documented consolidation is necessary.
- Move notes into the closest existing domain first; create a new domain only for a durable topic that spans multiple notes or has its own navigation needs.
- Keep filenames and aliases where practical to avoid breaking Obsidian WikiLinks.
- Keep vault maps, glossaries and editorial governance outside technical domain directories.
- A directory marked planned is a gap, not an implemented knowledge domain. Create it when an initial substantive article and navigation plan are ready.
