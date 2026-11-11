#!/usr/bin/env bash
set -Eeuo pipefail

# apt-get update can exit successfully when one or more mirrors are unreachable.
# Do not proceed until every package required by the next install has a candidate.
max_attempts="${APT_UPDATE_MAX_ATTEMPTS:-5}"
retry_delay_seconds="${APT_UPDATE_RETRY_DELAY_SECONDS:-10}"

if [[ "$#" -lt 1 ]]; then
  echo "Usage: $0 <required-package> [required-package ...]" >&2
  exit 2
fi

for attempt in $(seq 1 "${max_attempts}"); do
  echo "APT_INDEX_REFRESH_ATTEMPT ${attempt}/${max_attempts}"
  apt-get \
    -o Acquire::Retries=3 \
    -o Acquire::http::Timeout=30 \
    -o Acquire::https::Timeout=30 \
    update

  missing=()
  for package in "$@"; do
    candidate="$(apt-cache policy "$package" | awk '/Candidate:/ { print $2; exit }')"
    if [[ -z "${candidate}" || "${candidate}" == "(none)" ]]; then
      missing+=("$package")
    fi
  done

  if [[ "${#missing[@]}" -eq 0 ]]; then
    echo "APT_REQUIRED_PACKAGE_INDEXES_READY: $*"
    exit 0
  fi

  echo "APT_REQUIRED_PACKAGE_INDEXES_INCOMPLETE: ${missing[*]}" >&2
  if [[ "${attempt}" -lt "${max_attempts}" ]]; then
    sleep "${retry_delay_seconds}"
  fi
done

echo "ERROR: apt package indexes remained incomplete after ${max_attempts} attempts; missing candidates: ${missing[*]}" >&2
exit 1
