#!/usr/bin/env bash
set -Eeuo pipefail

# apt-get update can exit successfully when one or more mirrors are unreachable.
# Do not proceed until every package required by the next install has a candidate.
max_attempts="${APT_UPDATE_MAX_ATTEMPTS:-5}"
retry_delay_seconds="${APT_UPDATE_RETRY_DELAY_SECONDS:-10}"

# GitHub-hosted Ubuntu runners execute in Azure. Use Ubuntu's documented Azure archive
# instead of the archive/security endpoints that failed DNS resolution in Run #7/#8.
configure_ubuntu_apt_mirror() {
  local source_file changed=0
  local -a source_files=(
    /etc/apt/sources.list
    /etc/apt/sources.list.d/*.list
    /etc/apt/sources.list.d/*.sources
  )

  for source_file in "${source_files[@]}"; do
    [[ -f "${source_file}" ]] || continue
    if grep -Eq 'https?://([a-z]{2}\.)?(archive|security)\.ubuntu\.com/ubuntu' "${source_file}"; then
      sed -E -i \
        -e 's#https?://([a-z]{2}\.)?archive\.ubuntu\.com/ubuntu/?#http://azure.archive.ubuntu.com/ubuntu/#g' \
        -e 's#https?://([a-z]{2}\.)?security\.ubuntu\.com/ubuntu/?#http://azure.archive.ubuntu.com/ubuntu/#g' \
        "${source_file}"
      changed=1
    fi
  done

  if [[ "${changed}" -eq 1 ]]; then
    echo "APT_UBUNTU_MIRROR_CONFIGURED: azure.archive.ubuntu.com"
  else
    echo "APT_UBUNTU_MIRROR_ALREADY_CONFIGURED_OR_NOT_APPLICABLE"
  fi
}

if [[ "$#" -lt 1 ]]; then
  echo "Usage: $0 <required-package> [required-package ...]" >&2
  exit 2
fi

configure_ubuntu_apt_mirror

for attempt in $(seq 1 "${max_attempts}"); do
  echo "APT_INDEX_REFRESH_ATTEMPT ${attempt}/${max_attempts}"
  if ! apt-get \
    -o Acquire::Retries=3 \
    -o Acquire::http::Timeout=30 \
    -o Acquire::https::Timeout=30 \
    update; then
    echo "APT_UPDATE_COMMAND_FAILED: will inspect required package indexes and retry" >&2
  fi

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
