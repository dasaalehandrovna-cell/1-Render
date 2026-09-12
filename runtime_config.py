"""vys-262 R47 FINALIZED internal runtime configuration.

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

CONFIG_VERSION = "vys-262-r68-forwarding-ingress-preflight"

# Render #1 / FAST.  These values were the R13 recommended deployment values.
FRONT_INTERNAL_ENV: Dict[str, str] = {
    "R43_FAST_AUTHORITY": "0",
    # Process / role
    "PORT": "5000",
    "BOT_SPLIT_ROLE": "front",
    "RENDER_TELEGRAM_ONLY": "1",
    "MALLOC_ARENA_MAX": "2",
    "BOT_THREAD_STACK_KB": "512",
    "SCHEDULER_WORKERS": "2",
    "R21_HEAVY_DISPATCH_WORKERS": "2",
    "BOT_JOURNAL_MAX": "600",
    "MEMORY_EVENT_KEEP": "100",
    "FINANCE_INTEGRITY_KEEP": "800",
    "R45_DIAG_RING_ROWS": "750",
    "R45_DIAG_QUEUE_ROWS": "1500",

    # R26: FAST isolation + forensic trace + bounded full rebase cadence.
    "UI_WORKERS": "2",
        "FAST_UI_WORKERS": "2",
        "FAST_UI_MAX_PENDING": "300",
        "WINDOW_RENDER_WORKERS": "2",
        "WINDOW_RENDER_MAX_PENDING_KEYS": "256",
    "UI_MAX_PENDING": "300",
    "CALLBACK_ACK_WORKERS": "2",
    "UI_CLEANUP_WORKERS": "1",
    "UI_DELETE_WORKERS": "1",
    "UI_DELETE_MAX_PENDING": "400",
    "R26_TRACE_RING_ROWS": "1200",
    "R26_TRACE_EXPORT_ROWS": "1500",
    "R27_FAST_USER_PRIORITY_SEC": "2.0",
    "R27_SNAPSHOT_USER_QUIET_SEC": "30",
    "R27_STATE_MIRROR_DELAY_SEC": "30",
    "R27_FULL_SNAPSHOT_MIN_INTERVAL_SEC": "300",
    "R28_CONTINUITY_USER_QUIET_SEC": "12",
    "R28_FULL_SNAPSHOT_USER_QUIET_SEC": "30",
    "R28_STATE_MIRROR_DELAY_SEC": "30",
    "R28_FULL_SNAPSHOT_MIN_INTERVAL_SEC": "300",
    "R32_EVENT_STREAM_ENABLED": "1",
    "R32_EVENT_QUEUE_MAX": "5000",
    "R40_EVENT_DB_BUSY_MS": "120",
    "R32_EVENT_BATCH_DELAY_SEC": "0.65",
    "R32_EVENT_BATCH_MAX": "192",
    "R34_EVENT_TARGET_WIRE_KB": "768",
    "R34_EVENT_LARGE_WIRE_KB": "32768",
    "R32_EVENT_POST_TIMEOUT_SEC": "90",
    "R32_SHUTDOWN_EVENT_FLUSH_SEC": "8",
    "R36_FILE_SUBMIT_ATTEMPTS": "4",
    "R36_FILE_SUBMIT_TIMEOUT_SEC": "45",
    "R36_FAST_JOB_WAIT_SEC": "1800",
    # R38 durable FAST->HEAVY outbox / edge-restart tolerance
    "R38_PEER_MIN_GAP_SEC": "0.25",
    "R38_PEER_POST_TIMEOUT_SEC": "18",
    "R38_PEER_JOB_MAX_AGE_SEC": "21600",
    "R38_MEGA_EVENT_MIN_GAP_SEC": "1.0",
    "R38_FAST_JOB_WAIT_SEC": "3600",
    # R35 aliases remain only for rollback compatibility.
    "R24_LOWRAM_EVICT_RSS_MB": "300",
    "UI_CLEANUP_MAX_PENDING": "400",
    "WEBHOOK_WORKERS": "2",
    "WEBHOOK_MAX_CONNECTIONS": "8",
    "WAITRESS_THREADS": "6",
    "WEBHOOK_INBOX_WRITE_QUEUE_MAX": "1000",
    "WEBHOOK_STUCK_WARN_SECONDS": "5",
    "R25_TRACE_SLOW_LOCK_SEC": "0.020",
    "DELTA_WORKERS": "1",
    "BACKGROUND_WORKERS": "1",

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
    "SPLIT_STATE_SYNC_DELAY_SEC": "8",
    "SPLIT_STATE_SYNC_MIN_INTERVAL_SEC": "30",
    "SPLIT_FINANCE_SYNC_DELAY_SEC": "8",
    "SPLIT_CONTINUITY_FINANCE_DELAY_SEC": "8.0",
    "SPLIT_CONTINUITY_OTHER_DELAY_SEC": "12.0",
    "SPLIT_CONTINUITY_MAX_LATENCY_SEC": "30.0",
    "SPLIT_SYNC_MAX_LATENCY_SEC": "60",
    "SPLIT_CAPSULE_DELAY_SEC": "2.0",
    "SPLIT_CAPSULE_MAX_LATENCY_SEC": "6.0",
    "WORKER_REDIS_CAPSULE_KEY": "vys262:durable_capsule:r20",
    "SPLIT_FULL_RECONCILE_QUIET_SEC": "30",
    "SPLIT_DELTA_MAX_PAGES": "256",
    "SPLIT_DELTA_MAX_BYTES": "524288",
    "SPLIT_EVENT_RECEIPT_TIMEOUT_SEC": "1.2",
    "SPLIT_REDIS_FALLBACK_CONNECT_TIMEOUT_SEC": "0.35",
    "SPLIT_REDIS_FALLBACK_SOCKET_TIMEOUT_SEC": "0.65",

    # Boot / rolling deploy recovery
    "SPLIT_BOOT_ALWAYS_RESTORE": "0",
    "SPLIT_BOOT_HANDOFF_GRACE_SEC": "16",
    "SPLIT_PREBOOT_CAPTURE_WAIT_SEC": "4.0",
    "SPLIT_BOOT_WORKER_ATTEMPTS": "3",
    "SPLIT_BOOT_WORKER_TIMEOUT": "12",
    "SPLIT_RESTORE_RETRY_SEC": "5",
    "SPLIT_RESTORE_BOOT_ATTEMPTS": "3",
    "SPLIT_FORCE_BOOT_RESTORE": "0",
    "SPLIT_ALLOW_EMPTY_BOOT": "0",
    "SPLIT_EMERGENCY_MEGA": "1",

    # Heavy services are remote on Front.  MEGA credentials may still exist only
    # for emergency boot restore, but normal MEGA runtime stays disabled here.
    "MEGA_ENABLED": "0",
    "MEGA_AUTORESTORE": "0",
    "TG_DURABLE_ENABLED": "0",
    "TELEGRAM_DURABLE_ENABLED": "0",
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
    "WORKER_EVENT_REDIS_QUEUE_MAX": "2048",
    "WORKER_EVENT_REDIS_RETRY_MS": "250",
    "WORKER_EVENT_REDIS_RECONCILE_SEC": "5",
    "WORKER_R32_EVENT_RETENTION_SEC": "2592000",
    "WORKER_R32_EVENT_MAX_WIRE_KB": "8192",
    "WORKER_R32_MEGA_SEGMENT_EVENTS": "128",
    "WORKER_R32_MEGA_FLUSH_SEC": "30",

    # Worker local cache / transport limits
    "WORKER_CACHE_DIR": "/tmp/vys262_worker",
    "WORKER_RESTORE_CACHE_MAX_AGE_SEC": "120",
    "WORKER_SNAPSHOT_UPLOAD_MAX_MB": "64",
    "WORKER_DELTA_MAX_WIRE_KB": "2048",
    "WORKER_DELTA_MAX_JSON_MB": "16",
    "WORKER_DELTA_MAX_PAGES": "4096",
    "WORKER_DELTA_MAX_DB_MB": "128",
    "WORKER_FRONT_FETCH_TIMEOUT": "30",
    "WORKER_FULL_REBASE_MIN_INTERVAL_SEC": "45",

    # Local full checkpoint / reconcile cadence
    "WORKER_FULL_CHECKPOINT_SEC": "21600",
    "WORKER_FULL_CHECKPOINT_MAX_DELTAS": "1000",
    "WORKER_FULL_CHECKPOINT_MAX_DELTA_MB": "16",
    "WORKER_MEGA_CHECKPOINT_SEC": "86400",
    "WORKER_RECONCILE_SEC": "21600",

    # R38 Google/Drive resilience and durable Google recovery
    "R38_GOOGLE_RETRY_WINDOW_SEC": "600",
    "R38_GOOGLE_CALLBACK_WINDOW_SEC": "60",
    "R38_GOOGLE_MEGA_SCAN_SEC": "45",
    "R38_GOOGLE_MEGA_TIMEOUT": "180",

    # MEGA command timeouts
    "MEGA_TIMEOUT": "180",
    "MEGA_LOGIN_TIMEOUT": "120",
}



# R57: Render master switches are captured before packaged tuning is installed.
# MEGA_ENABLED=0 disables every MEGA path; REDIS_ENABLED=0 disables every Redis path.
# TELEGRAM_BACKUP_ENABLED=0 disables the Telegram backup/durable channel on FAST.
# R59: preserve the exact process environment as it arrived from Render before
# packaged runtime_config mutates/overwrites operational values.  This is used
# only for owner diagnostics; secret values are masked by the UI layer.
_RENDER_ENV_AT_IMPORT: Dict[str, str] = {str(k): str(v) for k, v in os.environ.items()}

def render_env_snapshot() -> Dict[str, str]:
    return dict(_RENDER_ENV_AT_IMPORT)

def _render_flag(name: str, default: bool) -> bool:
    raw = str(os.environ.get(name, "1" if default else "0") or "").strip().lower()
    return raw in {"1", "true", "yes", "on", "да"}

_MEGA_RENDER_ENABLED = _render_flag("MEGA_ENABLED", True)
_REDIS_RENDER_ENABLED = _render_flag("REDIS_ENABLED", False)
_REDIS_START_ENABLED = _render_flag("REDIS_START_ENABLED", False)
_TELEGRAM_BACKUP_RENDER_ENABLED = _render_flag("TELEGRAM_BACKUP_ENABLED", True)

# R61: Redis configuration belongs to Render only. The code never rewrites
# REDIS_ENABLED, REDIS_START_ENABLED or REDIS_URL. Menu switches change only
# an in-memory runtime flag until the next process restart.
_REDIS_EXTERNAL_URL = str(
    os.environ.get("REDIS_URL")
    or os.environ.get("RENDER_KEY_VALUE_URL")
    or os.environ.get("KEY_VALUE_URL")
    or os.environ.get("VALKEY_URL")
    or ""
).strip()
_REDIS_RUNTIME_ENABLED = False
_REDIS_RUNTIME_INITIALIZED = False

def redis_render_url() -> str:
    """Exact Redis/Valkey URL supplied by Render. Never mutated by runtime code."""
    return str(_REDIS_EXTERNAL_URL or "").strip()

def redis_effective_url() -> str:
    """Operational Redis URL only when the runtime switch is currently ON."""
    if not (_REDIS_RENDER_ENABLED and _REDIS_RUNTIME_ENABLED and _REDIS_EXTERNAL_URL):
        return ""
    return str(_REDIS_EXTERNAL_URL).strip()

def _apply_redis_runtime_state(enabled: bool) -> None:
    global _REDIS_RUNTIME_ENABLED
    _REDIS_RUNTIME_ENABLED = bool(enabled and _REDIS_RENDER_ENABLED and _REDIS_EXTERNAL_URL)

def redis_runtime_state() -> Dict[str, object]:
    enabled = bool(redis_effective_url())
    if not _REDIS_RENDER_ENABLED:
        mode = "locked_off"
    elif enabled:
        mode = "cache_on"
    else:
        mode = "runtime_off"
    return {
        "configured": bool(_REDIS_EXTERNAL_URL),
        "master_enabled": bool(_REDIS_RENDER_ENABLED),
        "start_enabled": bool(_REDIS_START_ENABLED),
        "enabled": enabled,
        "default_enabled": bool(_REDIS_RENDER_ENABLED and _REDIS_START_ENABLED),
        "restart_enabled": bool(_REDIS_RENDER_ENABLED and _REDIS_START_ENABLED),
        "mode": mode,
        "role": "background-cache-outbox",
        "source_of_truth": "sqlite",
        "url_source_present": bool(_REDIS_EXTERNAL_URL),
        "render_env_owned": True,
    }

def set_redis_runtime_enabled(enabled: bool) -> Dict[str, object]:
    _apply_redis_runtime_state(bool(enabled))
    state = redis_runtime_state()
    if bool(enabled) and not state["master_enabled"]:
        state["error"] = "REDIS_ENABLED=0 in Render"
    elif bool(enabled) and not state["configured"]:
        state["error"] = "REDIS_URL is not configured in Render"
    return state

def _init_redis_runtime_default() -> None:
    global _REDIS_RUNTIME_INITIALIZED
    if not _REDIS_RUNTIME_INITIALIZED:
        # Render owns restart behavior: master permission + explicit startup switch.
        _apply_redis_runtime_state(_REDIS_RENDER_ENABLED and _REDIS_START_ENABLED)
        _REDIS_RUNTIME_INITIALIZED = True

def install_internal_runtime_config(role: str) -> Dict[str, str]:
    """Install packaged tunables before the rest of the service reads os.environ."""
    role = str(role or "").strip().lower()
    values = FRONT_INTERNAL_ENV if role == "front" else WORKER_INTERNAL_ENV if role == "worker" else {}
    for key, value in values.items():
        # External master switches must never be overwritten by packaged defaults.
        if str(key) in {"MEGA_ENABLED", "REDIS_ENABLED", "TELEGRAM_BACKUP_ENABLED", "REDIS_START_ENABLED", "REDIS_URL"}:
            continue
        os.environ[str(key)] = str(value)
    fast_runtime_mega_disabled = role == "front" and str(os.environ.get("FAST_RUNTIME_MEGA_DISABLED", "0") or "0").strip().lower() in {"1", "true", "yes", "on"}
    os.environ["MEGA_ENABLED"] = "1" if (_MEGA_RENDER_ENABLED and not fast_runtime_mega_disabled) else "0"
    os.environ["TELEGRAM_BACKUP_ENABLED"] = "1" if _TELEGRAM_BACKUP_RENDER_ENABLED else "0"
    os.environ["MEGA_STRICT_ROOT"] = "1"
    os.environ["MEGA_LEGACY_BACKUP_DIRS"] = ""
    if role == "front" and not _TELEGRAM_BACKUP_RENDER_ENABLED:
        # Master OFF: preserve the Render value outside the process, but make every
        # in-process Telegram durable/backup-channel path see it as unavailable.
        os.environ["BACKUP_CHAT_ID"] = ""
        os.environ["TELEGRAM_DURABLE_ENABLED"] = "0"
        os.environ["TG_DURABLE_ENABLED"] = "0"
    if not _MEGA_RENDER_ENABLED:
        os.environ["MEGA_AUTORESTORE"] = "0"
        os.environ["SPLIT_EMERGENCY_MEGA"] = "0"
        os.environ["WORKER_CAPSULE_MEGA_ENABLED"] = "0"
    _init_redis_runtime_default()
    os.environ["VYS262_INTERNAL_CONFIG_VERSION"] = CONFIG_VERSION
    return dict(values)


def internal_runtime_config(role: str) -> Dict[str, str]:
    role = str(role or "").strip().lower()
    return dict(FRONT_INTERNAL_ENV if role == "front" else WORKER_INTERNAL_ENV if role == "worker" else {})
