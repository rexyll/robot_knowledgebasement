#!/usr/bin/env bash
# Build/install the pinned upstream ROS 2 workspace in both BUILD_TESTING modes.
# This script does not modify the upstream checkout.
set -Eeuo pipefail

: "${SOURCE_DIR:?Set SOURCE_DIR to the pinned staubli_driver_ros2 checkout}"
: "${OUTPUT_DIR:?Set OUTPUT_DIR for snapshots, logs and reports}"

EXPECTED_UPSTREAM_COMMIT="${EXPECTED_UPSTREAM_COMMIT:-bd658e2d266e315d2ee35f985fb352ea88306b79}"
ROS_DISTRO="${ROS_DISTRO:-jazzy}"
ROS_SETUP="${ROS_SETUP:-/opt/ros/jazzy/setup.bash}"
BUILD_ROOT="${BUILD_ROOT:-${OUTPUT_DIR}/build}"
INSTALL_ROOT="${INSTALL_ROOT:-${OUTPUT_DIR}/install}"
LOG_ROOT="${LOG_ROOT:-${OUTPUT_DIR}/logs}"
EVIDENCE_DIR="${EVIDENCE_DIR:-${OUTPUT_DIR}/evidence}"
CONSUMER_ROOT="${CONSUMER_ROOT:-${OUTPUT_DIR}/consumer}"

SOURCE_DIR="$(cd "${SOURCE_DIR}" && pwd)"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
mkdir -p "${OUTPUT_DIR}" "${BUILD_ROOT}" "${INSTALL_ROOT}" "${LOG_ROOT}"

fail() {
  printf 'SERVO-906 ERROR: %s\n' "$*" >&2
  exit 2
}

[[ "${ROS_DISTRO}" == "jazzy" ]] || fail "ROS_DISTRO must be jazzy, got ${ROS_DISTRO}"
[[ -f "${ROS_SETUP}" ]] || fail "ROS setup file not found: ${ROS_SETUP}"
[[ -f "${SOURCE_DIR}/staubli_robot_driver/CMakeLists.txt" ]] || fail "SOURCE_DIR must be the upstream workspace root"
[[ -f "${SOURCE_DIR}/staubli_robot_driver/package.xml" ]] || fail "staubli_robot_driver/package.xml is missing"
command -v git >/dev/null || fail "git is required"
command -v colcon >/dev/null || fail "colcon is required"
command -v rosdep >/dev/null || fail "rosdep is required"
command -v python3 >/dev/null || fail "python3 is required"

actual_commit="$(git -C "${SOURCE_DIR}" rev-parse HEAD)"
[[ "${actual_commit}" == "${EXPECTED_UPSTREAM_COMMIT}" ]] || fail "upstream commit mismatch: expected ${EXPECTED_UPSTREAM_COMMIT}, got ${actual_commit}"
[[ -z "$(git -C "${SOURCE_DIR}" status --porcelain)" ]] || fail "upstream checkout must be clean"

# package.xml omits these CMake-level dependencies; check them explicitly.
source "${ROS_SETUP}"
[[ "${ROS_DISTRO:-}" == "jazzy" ]] || fail "sourced ROS environment is not Jazzy"
ros2 pkg prefix backward_ros >/dev/null 2>&1 || fail "backward_ros is not discoverable in the sourced ROS environment"
dpkg-query -W -f='${db:Status-Status}' libboost-system-dev 2>/dev/null | grep -qx installed || fail "libboost-system-dev is not installed"
dpkg-query -W -f='${db:Status-Status}' libasio-dev 2>/dev/null | grep -qx installed || fail "libasio-dev is not installed"
[[ -f /usr/include/asio.hpp ]] || fail "standalone Asio header /usr/include/asio.hpp is missing"
rosdep check --from-paths "${SOURCE_DIR}" --ignore-src --rosdistro jazzy

command_log="${LOG_ROOT}/servo-906-build-install.log"
: > "${command_log}"
run_logged() {
  printf '\n$' >> "${command_log}"
  printf ' %q' "$@" >> "${command_log}"
  printf '\n' >> "${command_log}"
  "$@" 2>&1 | tee -a "${command_log}"
}

for mode in OFF ON; do
  lower="$(printf '%s' "${mode}" | tr '[:upper:]' '[:lower:]')"
  build_base="${BUILD_ROOT}/build-testing-${lower}"
  install_base="${INSTALL_ROOT}/build-testing-${lower}"
  log_base="${LOG_ROOT}/colcon-${lower}"
  package_build="${build_base}/staubli_robot_driver"

  mkdir -p "${package_build}/.cmake/api/v1/query"
  : > "${package_build}/.cmake/api/v1/query/codemodel-v2"

  run_logged colcon build \
    --base-paths "${SOURCE_DIR}" \
    --build-base "${build_base}" \
    --install-base "${install_base}" \
    --log-base "${log_base}" \
    --event-handlers console_direct+ \
    --cmake-args "-DBUILD_TESTING=${mode}" -DCMAKE_BUILD_TYPE=RelWithDebInfo

  [[ -s "${package_build}/install_manifest.txt" ]] || fail "install_manifest.txt missing/empty for BUILD_TESTING=${mode}"
  grep -Fxq "BUILD_TESTING:BOOL=${mode}" "${package_build}/CMakeCache.txt" || fail "CMakeCache BUILD_TESTING does not match ${mode}"
  [[ -f "${install_base}/setup.bash" ]] || fail "colcon install setup missing for BUILD_TESTING=${mode}"

  run_logged python3 "${SCRIPT_DIR}/collect_staubli_cmake_file_api.py" \
    --build-dir "${package_build}" \
    --build-testing "${mode}" \
    --export-root "${install_base}" \
    --output "${OUTPUT_DIR}/build-testing-${lower}.json"

  consumer_src="${CONSUMER_ROOT}/src/staubli_install_consumer"
  mkdir -p "${consumer_src}"
  cat > "${consumer_src}/package.xml" <<'PACKAGE_XML'
<?xml version="1.0"?>
<package format="3">
  <name>staubli_install_consumer</name>
  <version>0.0.1</version>
  <description>Install-space consumer smoke test</description>
  <maintainer email="ci@example.invalid">CI</maintainer>
  <license>Apache-2.0</license>
  <buildtool_depend>ament_cmake</buildtool_depend>
  <depend>staubli_robot_driver</depend>
  <export><build_type>ament_cmake</build_type></export>
</package>
PACKAGE_XML
  cat > "${consumer_src}/CMakeLists.txt" <<'CMAKE'
cmake_minimum_required(VERSION 3.8)
project(staubli_install_consumer)
find_package(ament_cmake REQUIRED)
find_package(staubli_robot_driver REQUIRED)
add_executable(staubli_install_consumer main.cpp)
target_link_libraries(staubli_install_consumer PRIVATE staubli_robot_driver::staubli_robot_driver)
install(TARGETS staubli_install_consumer DESTINATION lib/${PROJECT_NAME})
ament_package()
CMAKE
  cat > "${consumer_src}/main.cpp" <<'CPP'
#include "staubli_robot_driver/communication/protocol.hpp"
int main() { return 0; }
CPP

  # Run each consumer in a clean ROS environment. Sourcing a second overlay
  # into the parent shell would retain the first mode in AMENT/CMAKE prefixes
  # and could let OFF/ON consumer checks resolve against the wrong install tree.
  (
    unset AMENT_PREFIX_PATH CMAKE_PREFIX_PATH COLCON_PREFIX_PATH
    unset PYTHONPATH LD_LIBRARY_PATH ROS_PACKAGE_PATH
    source "${ROS_SETUP}"
    source "${install_base}/setup.bash"
    run_logged colcon build \
      --base-paths "${consumer_src}" \
      --build-base "${CONSUMER_ROOT}/build-${lower}" \
      --install-base "${CONSUMER_ROOT}/install-${lower}" \
      --log-base "${CONSUMER_ROOT}/logs-${lower}" \
      --event-handlers console_direct+
    printf 'INSTALL_SPACE_CONSUMER_PASS BUILD_TESTING=%s\n' "${mode}" | tee -a "${command_log}"
  )
done

run_logged colcon test \
  --base-paths "${SOURCE_DIR}" \
  --build-base "${BUILD_ROOT}/build-testing-on" \
  --install-base "${INSTALL_ROOT}/build-testing-on" \
  --log-base "${LOG_ROOT}/colcon-on" \
  --packages-select staubli_robot_driver \
  --event-handlers console_direct+
run_logged colcon test-result --test-result-base "${BUILD_ROOT}/build-testing-on" --verbose

run_logged python3 "${SCRIPT_DIR}/validate_staubli_upstream_target_graph.py" \
  --build-off "${OUTPUT_DIR}/build-testing-off.json" \
  --build-on "${OUTPUT_DIR}/build-testing-on.json" \
  --report "${OUTPUT_DIR}/servo-906-validation-report.json"

run_logged python3 "${SCRIPT_DIR}/package_staubli_build_evidence.py" package \
  --output-dir "${EVIDENCE_DIR}" \
  --build-off "${OUTPUT_DIR}/build-testing-off.json" \
  --build-on "${OUTPUT_DIR}/build-testing-on.json" \
  --validator-report "${OUTPUT_DIR}/servo-906-validation-report.json" \
  --source-dir "${SOURCE_DIR}" \
  --command-log "${command_log}"
run_logged python3 "${SCRIPT_DIR}/package_staubli_build_evidence.py" verify \
  --manifest "${EVIDENCE_DIR}/evidence_manifest.json"

printf '\nSERVO-906_BUILD_INSTALL_EVIDENCE_PASS\n'
