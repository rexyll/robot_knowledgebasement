# Stäubli ROS 2 upstream install-export remediation proposal

## Status

- Scope: review proposal only; this file is part of `robot_knowledgebasement`.
- Upstream repository: `ICube-Robotics/staubli_driver_ros2`.
- Pinned upstream revision: `bd658e2d266e315d2ee35f985fb352ea88306b79`.
- No upstream source, branch, tag, or pull request has been changed or created.
- Reason: Run `43133529247` proved two install-space consumer failures on both `BUILD_TESTING=OFF` and `ON`.

## Evidence

1. The pinned `staubli_robot_driver/CMakeLists.txt` calls `find_package(Boost REQUIRED COMPONENTS system)`, adds `Boost::system` to the main shared library's link interface, and adds `${asio_SOURCE_DIR}/asio/include` to its PUBLIC include directories.
2. The same CMake file does not declare Boost in `ament_export_dependencies()`; `staubli_robot_driver/package.xml` also has no Boost dependency.
3. The installed export contains `/asio/include` in `INTERFACE_INCLUDE_DIRECTORIES` and `Boost::system` in `INTERFACE_LINK_LIBRARIES`.
4. The downstream consumer intentionally does not call `find_package(Boost)` before `find_package(staubli_robot_driver)`. CMake therefore reports both the nonexistent `/asio/include` path and missing `Boost::system` imported target.
5. The pinned implementation header `staubli_robot_driver/src/communication/udp_socket_impl.hpp` includes `<boost/asio.hpp>`. Repository search finds Boost usage in the CMake file and this private implementation header, not in the installed public include tree.

Run #9 evidence:
- Run: https://github.com/rexyll/robot_knowledgebasement/actions/runs/43133529247
- Artifact ID: `13906750810`
- Artifact SHA-256: `763b18cca96e95153341f3992b7080143849a38133f7bfc4cef80aae26a0df32`
- OFF/ON builds and installs completed; all seven gtest XML reports passed (46 test cases total).
- OFF/ON installed consumers both failed at CMake configure; target graph validator reported 47/49 checks passed and two ASIO include export failures.

## Proposed minimal upstream change

The following is a review proposal, not an applied patch.

### 1. Remove the undefined standalone-Asio source include

In `staubli_robot_driver/CMakeLists.txt`, remove this PUBLIC include entry from the main library:

```cmake
${asio_SOURCE_DIR}/asio/include
```

The implementation uses Boost.Asio (`<boost/asio.hpp>`), and the source already finds Boost. No standalone Asio source directory is defined by this CMake project. The exported include interface should retain the build-tree and install-tree project include paths only.

### 2. Keep Boost::system private unless a public API requires it

The observed Boost.Asio include is in `src/communication/udp_socket_impl.hpp`, which is not part of the installed public header tree. If upstream maintainers confirm no public header or public inline implementation exposes Boost types, prefer:

```cmake
target_link_libraries(${PROJECT_NAME}
  PRIVATE Boost::system
)
```

This prevents a private implementation dependency from leaking as `Boost::system` in the installed target's `INTERFACE_LINK_LIBRARIES`. If upstream chooses to expose Boost in the public API instead, it must export the corresponding Boost CMake dependency before loading the exported targets.

### 3. Declare Boost in the package manifest

Add the appropriate rosdep dependency key for Boost to `staubli_robot_driver/package.xml` (normally `<depend>boost</depend>`) so clean ROS workspaces install the dependency without relying on this repository's explicit apt bootstrap. Confirm the key against the upstream target ROS distributions before merging.

## Required upstream acceptance tests

A proposed upstream change is acceptable only when all of the following pass on the same pinned candidate commit:

- Clean ROS Jazzy dependency resolution from package manifests.
- `BUILD_TESTING=OFF`: configure, build, install, and standalone install-space consumer configure/build.
- `BUILD_TESTING=ON`: configure, build, install, all seven gtest suites, and standalone install-space consumer configure/build.
- Installed exported target has no nonexistent `/asio/include` or unresolved `${asio_SOURCE_DIR}` path.
- Installed exported target has no undeclared `Boost::system` dependency. If Boost remains public, the package config must create that imported target before loading exported targets.
- No consumer-side preemptive `find_package(Boost)`, fake include directories, or post-install export rewriting.
- Preserve the fixed source commit and complete evidence manifest/hash checks for each candidate run.

## Authorization and implementation status

The user explicitly authorized implementation on their fork. The minimal patch has been committed to:

- Repository: https://github.com/rexyll/staubli_driver_ros2
- Branch: `fix/install-export-boost-asio`
- Base: `bd658e2d266e315d2ee35f985fb352ea88306b79`
- Commits:
  - `679cc4dd939484eeb9c72fb12c163a2b53b407b2` — remove invalid PUBLIC ASIO include and make Boost::system PRIVATE.
  - `6bbddecaaf9567bd463eacb7a04f6c2295b10bee` — declare the Boost package dependency.
- The fork branch was re-read after the writes; both file changes are present. The branch is two commits ahead of, and zero commits behind, the pinned base.

An attempt to create a pull request from `rexyll:fix/install-export-boost-asio` to `ICube-Robotics/staubli_driver_ros2:main` was rejected with HTTP 403 `Resource not accessible by integration`. The connection has verified fork read/write access but cannot create a PR in the upstream repository. No substitute PR against the fork itself was created.

Next action: the user can open the PR in GitHub from the fork branch to upstream main. Once it exists, validate the PR CI and run the complete ROS Jazzy matrix: OFF/ON clean build/install, independent install-space consumer configure/build, and all gtest suites. The fork commits are a proposed fix, not yet validated or accepted upstream. Until the complete matrix passes, SERVO-906 and SERVO-907 remain BLOCKED.
