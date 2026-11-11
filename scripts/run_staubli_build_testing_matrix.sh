#!/usr/bin/env bash
set -euo pipefail
: "\${SOURCE_DIR:?Set SOURCE_DIR to the upstream source checkout}"
: "\${OUTPUT_DIR:?Set OUTPUT_DIR for normalized snapshots}"
BUILD_ROOT="\${BUILD_ROOT:-\${OUTPUT_DIR}/build}"
mkdir -p "\${BUILD_ROOT}" "\${OUTPUT_DIR}"
for mode in OFF ON; do
  lower="$(printf '%s' "$mode" | tr '[:upper:]' '[:lower:]')"
  build_dir="\${BUILD_ROOT}/build-testing-\${lower}"
  mkdir -p "\${build_dir}/.cmake/api/v1/query"
  : > "\${build_dir}/.cmake/api/v1/query/codemodel-v2"
  cmake -S "\${SOURCE_DIR}" -B "\${build_dir}" -DBUILD_TESTING="$mode"
  python3 "$(dirname "$0")/collect_staubli_cmake_file_api.py" --build-dir "\${build_dir}" --build-testing "$mode" --output "\${OUTPUT_DIR}/build-testing-\${lower}.json"
done
python3 "$(dirname "$0")/validate_staubli_fake_harness_target_graph.py" --build-off "\${OUTPUT_DIR}/build-testing-off.json" --build-on "\${OUTPUT_DIR}/build-testing-on.json" --report "\${OUTPUT_DIR}/servo-901-validation-report.json"
