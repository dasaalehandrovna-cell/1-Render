"""vys-262 R14 internal runtime configuration.

All non-secret operational tunables that used to be Render environment variables
live here.  Render ENV is intentionally reserved for credentials, remote
addresses and external account/resource identifiers.

Values in this file are authoritative: install_internal_runtime_config() uses
assignment (not setdefault), so stale numeric/tuning variables left in Render do
not override the packaged configuration.
"""
from __future__ import annotations

import os
from typing import Dict

CONFIG_VERSION = "vys-262-r14-internal-config"

# Render #1 / FAST.  These values were the R13 recommended deployment values.
FRONT_INTERNAL_ENV: Dict[str, str] = {
    # Process / role
    "PORT": "5000",
    "BOT_SPLIT_ROLE": "front",
    "RENDER_TELEGRAM_ONLY": "1",
    "MALLOC_ARENA_MAX": "2",

    # Small user-facing runtime constants
    "QUICK_EXPENSE_REMINDER_MINUTES": "60",

    # Shared Redis layout (names/limits are implementation details, not secrets)
    "WORKER_REDIS_SNAPSHOT_KEY": "vys262:bot_state:latest_gz",
    "WORKER_REDIS_SNAPSHOT_MAX_MB": "16",
    "WORKER_REDIS_EVENT_PREFIX": "vys262:tg_events:v1",
    "WORKER_EVENT_RETENTION_SEC": "604800",

    # Peer / event-journal transport
    "PEER_PING_ENABLED": "1",
    "PEER_PING_INTERVAL_SEC": "120",
    "SPLIT_WORKER_SYNC_ENABLED": "1",
    "SPLIT_STATE_SYNC_DELAY_SEC": "0.35",
    "SPLIT_STATE_SYNC_MIN_INTERVAL_SEC": "0.5",
    "SPLIT_DELTA_MAX_PAGES": "256",
    "SPLIT_DELTA_MAX_BYTES": "524288",
    "SPLIT_EVENT_RECEIPT_TIMEOUT_SEC": "6",

    # Boot / rolling deploy recovery
    "SPLIT_BOOT_ALWAYS_RESTORE": "1",
    "SPLIT_BOOT_HANDOFF_GRACE_SEC": "10",
    "SPLIT_BOOT_WORKER_ATTEMPTS": "3",
    "SPLIT_BOOT_WORKER_TIMEOUT": "12",
    "SPLIT_RESTORE_RETRY_SEC": "20",
    "SPLIT_FORCE_BOOT_RESTORE": "0",
    "SPLIT_ALLOW_EMPTY_BOOT": "0",
    "SPLIT_EMERGENCY_MEGA": "1",

    # Heavy services are remote on Front.  MEGA credentials may still exist only
    # for emergency boot restore, but normal MEGA runtime stays disabled here.
    "MEGA_ENABLED": "0",
    "MEGA_AUTORESTORE": "0",
    "TG_DURABLE_ENABLED": "0",
    "MEGA_TIMEOUT": "120",
    "MEGA_LOGIN_TIMEOUT": "120",
    "SPLIT_GOOGLE_REMOTE_ENABLED": "1",
}

# Render #2 / HEAVY.
WORKER_INTERNAL_ENV: Dict[str, str] = {
    "PORT": "10000",
    "PEER_PING_ENABLED": "1",
    "PEER_PING_INTERVAL_SEC": "120",

    # Redis keys / retention
    "WORKER_REDIS_SNAPSHOT_KEY": "vys262:bot_state:latest_gz",
    "WORKER_REDIS_SNAPSHOT_MAX_MB": "16",
    "WORKER_REDIS_DELTA_KEY": "vys262:bot_state:latest_gz:deltas_v1",
    "WORKER_REDIS_DELTA_MAX_ITEMS": "2000",
    "WORKER_REDIS_EVENT_PREFIX": "vys262:tg_events:v1",
    "WORKER_EVENT_RETENTION_SEC": "604800",
    "WORKER_EVENT_MAX_WIRE_KB": "512",

    # Worker local cache / transport limits
    "WORKER_CACHE_DIR": "/tmp/vys262_worker",
    "WORKER_RESTORE_CACHE_MAX_AGE_SEC": "120",
    "WORKER_SNAPSHOT_UPLOAD_MAX_MB": "64",
    "WORKER_DELTA_MAX_WIRE_KB": "2048",
    "WORKER_DELTA_MAX_JSON_MB": "16",
    "WORKER_DELTA_MAX_PAGES": "4096",
    "WORKER_DELTA_MAX_DB_MB": "128",
    "WORKER_FRONT_FETCH_TIMEOUT": "30",

    # Local full checkpoint / reconcile cadence
    "WORKER_FULL_CHECKPOINT_SEC": "21600",
    "WORKER_FULL_CHECKPOINT_MAX_DELTAS": "1000",
    "WORKER_FULL_CHECKPOINT_MAX_DELTA_MB": "16",
    "WORKER_MEGA_CHECKPOINT_SEC": "86400",
    "WORKER_RECONCILE_SEC": "21600",

    # MEGA command timeouts
    "MEGA_TIMEOUT": "180",
    "MEGA_LOGIN_TIMEOUT": "120",
}


def install_internal_runtime_config(role: str) -> Dict[str, str]:
    """Install packaged tunables before the rest of the service reads os.environ."""
    role = str(role or "").strip().lower()
    values = FRONT_INTERNAL_ENV if role == "front" else WORKER_INTERNAL_ENV if role == "worker" else {}
    for key, value in values.items():
        os.environ[str(key)] = str(value)
    os.environ["VYS262_INTERNAL_CONFIG_VERSION"] = CONFIG_VERSION
    return dict(values)


def internal_runtime_config(role: str) -> Dict[str, str]:
    role = str(role or "").strip().lower()
    return dict(FRONT_INTERNAL_ENV if role == "front" else WORKER_INTERNAL_ENV if role == "worker" else {})
