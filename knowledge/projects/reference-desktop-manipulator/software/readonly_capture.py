"""Offline-safe, read-only STS3215 snapshot collector.

This module deliberately does not create, connect, configure, or disconnect a bus.
The caller must inject an already-approved bus object. It only invokes read().
The returned values are decoded register integers/booleans, not wire bytes.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter_ns
from typing import Any, Mapping, Protocol


class ReadOnlyBus(Protocol):
    """Minimal capability surface required by this collector."""

    def read(
        self,
        data_name: str,
        motor: str,
        *,
        normalize: bool = False,
        num_retry: int = 0,
    ) -> int | float:
        ...


def load_register_whitelist(path: str | Path | None = None) -> dict[str, Any]:
    """Load and minimally validate the versioned STS3215 field whitelist."""
    source_path = Path(path) if path is not None else Path(__file__).with_name(
        "sts3215_readonly_fields.json"
    )
    payload = json.loads(source_path.read_text(encoding="utf-8"))
    if payload.get("model") != "sts3215" or payload.get("read_operation_only") is not True:
        raise ValueError("Unsupported or unsafe register whitelist")
    registers = payload.get("registers")
    if not isinstance(registers, list) or not registers:
        raise ValueError("Whitelist must contain a non-empty registers list")
    names = [item.get("name") for item in registers]
    if any(not isinstance(name, str) or not name for name in names):
        raise ValueError("Every whitelist register must have a non-empty name")
    if len(names) != len(set(names)):
        raise ValueError("Duplicate register names in whitelist")
    return payload


def capture_snapshot(
    bus: ReadOnlyBus,
    motors: Mapping[str, int],
    *,
    whitelist_path: str | Path | None = None,
) -> dict[str, Any]:
    """Read each whitelisted field separately and preserve per-field failures.

    The function performs no connection lifecycle management and never writes.
    It intentionally uses individual read() calls rather than sync_read(), so
    each motor/field has an independently timestamped result and failure record.
    """
    if not motors:
        raise ValueError("motors mapping must not be empty")

    whitelist = load_register_whitelist(whitelist_path)
    records: list[dict[str, Any]] = []

    for motor_name, motor_id in motors.items():
        if not isinstance(motor_name, str) or not motor_name:
            raise ValueError("motor names must be non-empty strings")
        if not isinstance(motor_id, int) or isinstance(motor_id, bool):
            raise ValueError(f"motor ID for {motor_name!r} must be an integer")

        for register in whitelist["registers"]:
            started_ns = perf_counter_ns()
            captured_at = datetime.now(timezone.utc).isoformat()
            record: dict[str, Any] = {
                "captured_at_utc": captured_at,
                "elapsed_ns": None,
                "motor_name": motor_name,
                "motor_id": motor_id,
                "field": register["name"],
                "address": register["address"],
                "width_bytes": register["width_bytes"],
                "access": register["access"],
                "result": None,
            }
            try:
                value = bus.read(
                    register["name"],
                    motor_name,
                    normalize=False,
                    num_retry=0,
                )
            except Exception as exc:  # preserve a failed field; never substitute zero
                record["result"] = "error"
                record["exception_type"] = type(exc).__name__
                record["exception_message"] = str(exc)
            else:
                record["result"] = "ok"
                record["register_value_decoded"] = value
            finally:
                record["elapsed_ns"] = perf_counter_ns() - started_ns
            records.append(record)

    return {
        "schema_version": "1.0",
        "captured_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_audit_baseline": whitelist["source"],
        "robot": "SO-101",
        "motor_map": [{"name": name, "id": motor_id} for name, motor_id in motors.items()],
        "value_semantics": "decoded register values; not raw wire bytes",
        "records": records,
    }
