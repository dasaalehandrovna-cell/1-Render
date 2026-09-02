# v262
import ctypes as _memory_ctypes
import gc as _memory_gc
import resource as _memory_resource

def _memory_env_float(name: str, default: float, minimum: float, maximum: float) -> float:
    try:
        return max(minimum, min(maximum, float(os.getenv(name, str(default)) or default)))
    except Exception:
        return float(default)

def _memory_env_int(name: str, default: int, minimum: int, maximum: int) -> int:
    try:
        return max(minimum, min(maximum, int(os.getenv(name, str(default)) or default)))
    except Exception:
        return int(default)
MEMORY_GUARD_ENABLED = str(os.getenv('MEMORY_GUARD_ENABLED', '1') or '1').strip().lower() not in {'0', 'false', 'off', 'no'}
MEMORY_GUARD_INTERVAL_SECONDS = _memory_env_float('MEMORY_GUARD_INTERVAL_SECONDS', 30.0, 10.0, 300.0)
MEMORY_SOFT_TRIM_MB = _memory_env_float('MEMORY_SOFT_TRIM_MB', 175.0, 128.0, 1024.0)
MEMORY_WARNING_MB = _memory_env_float('MEMORY_WARNING_MB', 300.0, 128.0, 2048.0)
MEMORY_HIGH_MB = _memory_env_float('MEMORY_HIGH_MB', 350.0, MEMORY_WARNING_MB + 10.0, 3072.0)
MEMORY_CRITICAL_MB = _memory_env_float('MEMORY_CRITICAL_MB', 400.0, MEMORY_HIGH_MB + 10.0, 4096.0)
MEMORY_EMERGENCY_MB = _memory_env_float('MEMORY_EMERGENCY_MB', 440.0, MEMORY_CRITICAL_MB + 10.0, 4096.0)
MEMORY_HEAVY_BLOCK_MB = _memory_env_float('MEMORY_HEAVY_BLOCK_MB', 395.0, MEMORY_HIGH_MB, 4096.0)
MEMORY_TRIM_COOLDOWN_SECONDS = _memory_env_float('MEMORY_TRIM_COOLDOWN_SECONDS', 45.0, 5.0, 600.0)
MEMORY_EVENT_KEEP = _memory_env_int('MEMORY_EVENT_KEEP', 200, 50, 1000)
MEMORY_SAFE_RESTART_ENABLED = str(os.getenv('MEMORY_SAFE_RESTART_ENABLED', '0') or '0').strip().lower() in {'1', 'true', 'on', 'yes'}
MEMORY_SAFE_RESTART_MB = _memory_env_float('MEMORY_SAFE_RESTART_MB', 455.0, MEMORY_EMERGENCY_MB, 4096.0)
MEMORY_SAFE_RESTART_MIN_UPTIME = _memory_env_float('MEMORY_SAFE_RESTART_MIN_UPTIME', 1800.0, 300.0, 86400.0)
_MEMORY_LOCK = threading.RLock()
_MEMORY_EVENTS = deque(maxlen=MEMORY_EVENT_KEEP)
_MEMORY_ACTIVE = {}
_MEMORY_SEQ = 0
_MEMORY_STATE = {'started': False, 'last_level': 'normal', 'last_check_at': '', 'last_trim_at': '', 'last_trim_reason': '', 'trim_count': 0, 'malloc_trim_count': 0, 'blocked_heavy_jobs': 0, 'safe_restart_requested': False, 'peak_container_mb_seen': 0.0, 'peak_python_mb_seen': 0.0, 'last_snapshot': {}}

def _memory_read_number(path: str):
    try:
        raw = Path(path).read_text(errors='ignore').strip()
        if not raw or raw.lower() == 'max':
            return None
        value = int(raw)
        if value < 0 or value >= 1 << 60:
            return None
        return value
    except Exception:
        return None

def _memory_bytes_mb(value):
    try:
        return round(float(value) / 1024.0 / 1024.0, 1)
    except Exception:
        return None

def _memory_cgroup_snapshot() -> dict:
    current = _memory_read_number('/sys/fs/cgroup/memory.current')
    peak = _memory_read_number('/sys/fs/cgroup/memory.peak')
    limit = _memory_read_number('/sys/fs/cgroup/memory.max')
    if current is None:
        current = _memory_read_number('/sys/fs/cgroup/memory/memory.usage_in_bytes')
    if peak is None:
        peak = _memory_read_number('/sys/fs/cgroup/memory/memory.max_usage_in_bytes')
    if limit is None:
        limit = _memory_read_number('/sys/fs/cgroup/memory/memory.limit_in_bytes')
    events = {}
    for candidate in ('/sys/fs/cgroup/memory.events', '/sys/fs/cgroup/memory/memory.failcnt'):
        try:
            if not os.path.exists(candidate):
                continue
            text = Path(candidate).read_text(errors='ignore').strip()
            if candidate.endswith('failcnt'):
                events['failcnt'] = int(text or 0)
            else:
                for line in text.splitlines():
                    parts = line.split()
                    if len(parts) == 2:
                        events[str(parts[0])] = int(parts[1])
            break
        except Exception:
            continue
    out = {'current_mb': _memory_bytes_mb(current), 'peak_mb': _memory_bytes_mb(peak), 'limit_mb': _memory_bytes_mb(limit), 'events': events}
    try:
        if out['current_mb'] is not None and out['limit_mb']:
            out['percent'] = round(100.0 * float(out['current_mb']) / float(out['limit_mb']), 1)
        else:
            out['percent'] = None
    except Exception:
        out['percent'] = None
    return out

def _memory_proc_rollup() -> dict:
    out = {}
    path = '/proc/self/smaps_rollup'
    if not os.path.exists(path):
        return out
    wanted = {'Rss:': 'rss_mb', 'Pss:': 'pss_mb', 'Private_Clean:': 'private_clean_mb', 'Private_Dirty:': 'private_dirty_mb', 'Shared_Clean:': 'shared_clean_mb', 'Shared_Dirty:': 'shared_dirty_mb', 'Anonymous:': 'anonymous_mb', 'Swap:': 'swap_mb'}
    try:
        for line in Path(path).read_text(errors='ignore').splitlines():
            for prefix, key in wanted.items():
                if line.startswith(prefix):
                    out[key] = round(float(line.split()[1]) / 1024.0, 1)
                    break
    except Exception:
        pass
    return out

def _memory_child_processes() -> list[dict]:
    rows = []
    try:
        child_file = f'/proc/{os.getpid()}/task/{os.getpid()}/children'
        raw = Path(child_file).read_text(errors='ignore').strip() if os.path.exists(child_file) else ''
        pids = [int(x) for x in raw.split() if x.isdigit()]
    except Exception:
        pids = []
    for pid in pids[:40]:
        row = {'pid': pid, 'rss_mb': None, 'name': '', 'cmd': ''}
        try:
            status = Path(f'/proc/{pid}/status').read_text(errors='ignore')
            for line in status.splitlines():
                if line.startswith('Name:'):
                    row['name'] = line.split(':', 1)[1].strip()[:80]
                elif line.startswith('VmRSS:'):
                    row['rss_mb'] = round(float(line.split()[1]) / 1024.0, 1)
        except Exception:
            pass
        try:
            cmd = Path(f'/proc/{pid}/cmdline').read_bytes().replace(b'\x00', b' ').decode('utf-8', 'replace').strip()
            row['cmd'] = cmd[:240]
        except Exception:
            pass
        rows.append(row)
    return rows

def telegram_download_to_file(file_path: str, target_path: str, max_bytes: int | None=None, chunk_size: int=1024 * 1024) -> int:
    """Stream a Telegram Bot API file to disk without creating one huge bytes object."""
    file_path = str(file_path or '').lstrip('/')
    if not file_path:
        raise ValueError('empty Telegram file_path')
    token = str(globals().get('BOT_TOKEN') or '').strip()
    if not token:
        raise RuntimeError('BOT_TOKEN is empty')
    os.makedirs(os.path.dirname(os.path.abspath(target_path)) or '.', exist_ok=True)
    url = f'https://api.telegram.org/file/bot{token}/{file_path}'
    total = 0
    with requests.get(url, stream=True, timeout=(15, 180)) as response:
        response.raise_for_status()
        with open(target_path, 'wb') as fh:
            for chunk in response.iter_content(chunk_size=max(65536, int(chunk_size or 0))):
                if not chunk:
                    continue
                total += len(chunk)
                if max_bytes is not None and total > int(max_bytes):
                    raise ValueError(f'Telegram file exceeds limit: {total} > {int(max_bytes)}')
                fh.write(chunk)
    return total

def memory_quick_snapshot() -> dict:
    runtime_fn = globals().get('_runtime_memory_stats')
    process = runtime_fn() if callable(runtime_fn) else {}
    cgroup = _memory_cgroup_snapshot()
    process_rss = process.get('rss_mb')
    container = cgroup.get('current_mb')
    effective = container if container is not None else process_rss
    with _MEMORY_LOCK:
        if container is not None:
            _MEMORY_STATE['peak_container_mb_seen'] = max(float(_MEMORY_STATE.get('peak_container_mb_seen') or 0), float(container))
        if process_rss is not None:
            _MEMORY_STATE['peak_python_mb_seen'] = max(float(_MEMORY_STATE.get('peak_python_mb_seen') or 0), float(process_rss))
    return {'effective_mb': effective, 'python_rss_mb': process_rss, 'python_peak_rss_mb': process.get('peak_rss_mb'), 'container_current_mb': container, 'container_peak_mb': cgroup.get('peak_mb'), 'limit_mb': cgroup.get('limit_mb') or process.get('limit_mb'), 'container_percent': cgroup.get('percent'), 'cgroup_events': cgroup.get('events') or {}}

def _memory_effective_thresholds(snapshot: dict | None=None) -> dict:
    snap = snapshot or {}
    try:
        limit = float(snap.get('limit_mb') or 0.0)
    except Exception:
        limit = 0.0
    return {'warning': max(MEMORY_WARNING_MB, limit * 0.58) if limit else MEMORY_WARNING_MB, 'high': max(MEMORY_HIGH_MB, limit * 0.68) if limit else MEMORY_HIGH_MB, 'critical': max(MEMORY_CRITICAL_MB, limit * 0.78) if limit else MEMORY_CRITICAL_MB, 'emergency': max(MEMORY_EMERGENCY_MB, limit * 0.86) if limit else MEMORY_EMERGENCY_MB, 'heavy_block': max(MEMORY_HEAVY_BLOCK_MB, limit * 0.77) if limit else MEMORY_HEAVY_BLOCK_MB, 'safe_restart': max(MEMORY_SAFE_RESTART_MB, limit * 0.89) if limit else MEMORY_SAFE_RESTART_MB}

def memory_level(snapshot: dict | None=None) -> str:
    snap = snapshot or memory_quick_snapshot()
    thresholds = _memory_effective_thresholds(snap)
    try:
        used = float(snap.get('effective_mb') or 0.0)
    except Exception:
        used = 0.0
    try:
        pct = float(snap.get('container_percent') or 0.0)
    except Exception:
        pct = 0.0
    if used >= thresholds['emergency'] or pct >= 86.0:
        return 'emergency'
    if used >= thresholds['critical'] or pct >= 78.0:
        return 'critical'
    if used >= thresholds['high'] or pct >= 68.0:
        return 'high'
    if used >= thresholds['warning'] or pct >= 58.0:
        return 'warning'
    return 'normal'

def _memory_emit(event: str, detail: dict | None=None, level: str='INFO'):
    global _MEMORY_SEQ
    with _MEMORY_LOCK:
        _MEMORY_SEQ += 1
        row = {'seq': _MEMORY_SEQ, 'ts': now_local().isoformat(timespec='milliseconds') if 'now_local' in globals() else datetime.now(timezone.utc).isoformat(timespec='milliseconds'), 'event': str(event), 'level': str(level).upper(), 'thread': threading.current_thread().name, 'detail': dict(detail or {})}
        _MEMORY_EVENTS.append(row)
    try:
        bot_journal(str(event), None, json.dumps(row['detail'], ensure_ascii=False, separators=(',', ':'), default=str)[:1800], row['level'])
    except Exception:
        pass
    return row

def _v177_legacy_0116_memory_malloc_trim() -> bool:
    try:
        libc = _memory_ctypes.CDLL('libc.so.6')
        result = int(libc.malloc_trim(0))
        with _MEMORY_LOCK:
            _MEMORY_STATE['malloc_trim_count'] = int(_MEMORY_STATE.get('malloc_trim_count') or 0) + 1
        return result == 1
    except Exception:
        return False
try:
    _v177_legacy_0116_memory_malloc_trim.__name__ = 'memory_malloc_trim'
except Exception:
    pass

def _memory_compact_logs(level: str):
    keep = 250 if level == 'warning' else 160 if level == 'high' else 100
    try:
        with bot_journal_lock:
            if len(BOT_ACTION_LOG) > keep:
                tail = list(BOT_ACTION_LOG)[-keep:]
                BOT_ACTION_LOG.clear()
                BOT_ACTION_LOG.extend(tail)
    except Exception:
        pass
    try:
        compact_fn = globals().get('window_diag_compact_for_memory')
        if callable(compact_fn):
            compact_fn(level)
    except Exception:
        pass
    try:
        for scheduler_name in ('DELAYED_SCHEDULER', 'CALLBACK_ACK_SCHEDULER'):
            scheduler = globals().get(scheduler_name)
            if scheduler is not None and hasattr(scheduler, 'compact'):
                scheduler.compact()
    except Exception:
        pass

def memory_trim(reason: str='manual', level: str | None=None, force: bool=False) -> dict:
    now_m = time.monotonic()
    with _MEMORY_LOCK:
        last = float(_MEMORY_STATE.get('last_trim_monotonic') or 0.0)
        if not force and now_m - last < MEMORY_TRIM_COOLDOWN_SECONDS:
            return {'skipped': 'cooldown', 'reason': reason, 'snapshot': memory_quick_snapshot()}
        _MEMORY_STATE['last_trim_monotonic'] = now_m
    before = memory_quick_snapshot()
    current_level = level or memory_level(before)
    try:
        idle_fn = globals().get('_lowram_business_busy')
        busy = bool(idle_fn()) if callable(idle_fn) else True
    except Exception:
        busy = True
    if not busy:
        try:
            flush_fn = globals().get('_lowram_flush_all_hot')
            if callable(flush_fn):
                flush_fn(evict=True)
        except Exception as exc:
            _memory_emit('memory_lowram_flush_error', {'reason': reason, 'error': str(exc)[:300]}, 'WARN')
    _memory_compact_logs(current_level)
    try:
        _memory_gc.collect()
    except Exception:
        pass
    trimmed = memory_malloc_trim()
    after = memory_quick_snapshot()
    with _MEMORY_LOCK:
        _MEMORY_STATE['last_trim_at'] = now_local().isoformat(timespec='seconds') if 'now_local' in globals() else datetime.now(timezone.utc).isoformat(timespec='seconds')
        _MEMORY_STATE['last_trim_reason'] = str(reason)
        _MEMORY_STATE['trim_count'] = int(_MEMORY_STATE.get('trim_count') or 0) + 1
    detail = {'reason': reason, 'level': current_level, 'busy': busy, 'malloc_trim': trimmed, 'before': before, 'after': after}
    _memory_emit('memory_trim', detail, 'WARN' if current_level in {'high', 'critical', 'emergency'} else 'INFO')
    return detail
_MEMORY_SECRET_KEY_RE = re.compile('(?:pass(?:word)?|secret|token|api[_-]?key|credential|auth|login)', re.I)

def _memory_redact_meta(kind: str, value, key: str=''):
    """Redact credentials before they enter active-operation state or diagnostics."""
    if isinstance(value, dict):
        return {str(k): _memory_redact_meta(kind, v, str(k)) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_memory_redact_meta(kind, item, key) for item in value]
    if value is None or isinstance(value, (bool, int, float)):
        return value
    text = str(value)
    protected = {str(globals().get('MEGA_EMAIL') or ''), str(globals().get('MEGA_PASSWORD') or ''), str(os.getenv('BOT_TOKEN') or ''), str(os.getenv('TELEGRAM_BOT_TOKEN') or ''), str(os.getenv('GOOGLE_SERVICE_ACCOUNT_JSON') or ''), str(os.getenv('TENANT_GOOGLE_MASTER_KEY') or ''), str(os.getenv('GOOGLE_TENANT_MASTER_KEY') or '')}
    protected.discard('')
    low_kind = str(kind or '').lower()
    if text in protected or _MEMORY_SECRET_KEY_RE.search(str(key or '')):
        return '<redacted>'
    if any((word in low_kind for word in ('login', 'auth', 'credential'))) and str(key or '').lower() in {'args', 'argv', 'command'}:
        return '<redacted>'
    return text[:500]

@contextmanager
def memory_operation(kind: str, meta: dict | None=None, heavy: bool=False, quiet: bool=False):
    global _MEMORY_SEQ
    kind = str(kind or 'operation')[:120]
    started = time.monotonic()
    before = memory_quick_snapshot()
    safe_meta = _memory_redact_meta(kind, dict(meta or {}))
    with _MEMORY_LOCK:
        _MEMORY_SEQ += 1
        token = f'mem-{_MEMORY_SEQ}'
        _MEMORY_ACTIVE[token] = {'kind': kind, 'started': started, 'thread': threading.current_thread().name, 'meta': safe_meta}
    try:
        yield token
    finally:
        elapsed = max(0.0, time.monotonic() - started)
        after_before_trim = memory_quick_snapshot()
        level = memory_level(after_before_trim)
        if heavy or level in {'high', 'critical', 'emergency'}:
            try:
                _memory_gc.collect()
            except Exception:
                pass
            memory_malloc_trim()
        after = memory_quick_snapshot()
        with _MEMORY_LOCK:
            _MEMORY_ACTIVE.pop(token, None)
        try:
            delta = round(float(after.get('effective_mb') or 0) - float(before.get('effective_mb') or 0), 1)
        except Exception:
            delta = None
        detail = {'kind': kind, 'elapsed': round(elapsed, 3), 'heavy': bool(heavy), 'delta_mb': delta, 'before': before, 'after_before_trim': after_before_trim, 'after': after, 'meta': safe_meta}
        should_emit = heavy or elapsed >= 3.0 or (delta is not None and abs(delta) >= 10.0) or (level != 'normal')
        if quiet:
            should_emit = level != 'normal' or elapsed >= 10.0 or (delta is not None and abs(delta) >= 20.0)
        if should_emit:
            _memory_emit('memory_operation', detail, 'WARN' if level in {'high', 'critical', 'emergency'} else 'INFO')

def memory_heavy_allowed(kind: str) -> tuple[bool, str]:
    snap = memory_quick_snapshot()
    level = memory_level(snap)
    kind_s = str(kind or 'export').lower()
    diagnostic = any((x in kind_s for x in ('journal', 'runtime')))
    used = float(snap.get('effective_mb') or 0.0)
    thresholds = _memory_effective_thresholds(snap)
    heavy_block = float(thresholds.get('heavy_block') or MEMORY_HEAVY_BLOCK_MB)
    if level == 'emergency' and (not diagnostic):
        with _MEMORY_LOCK:
            _MEMORY_STATE['blocked_heavy_jobs'] = int(_MEMORY_STATE.get('blocked_heavy_jobs') or 0) + 1
        return (False, f'Сервер разгружает память ({used:.0f} МБ). Финансы продолжают работать; тяжёлый файл временно не запускается.')
    if used >= heavy_block and (not diagnostic):
        memory_trim('heavy_job_gate', level=level, force=False)
        snap2 = memory_quick_snapshot()
        used2 = float(snap2.get('effective_mb') or 0.0)
        if used2 >= heavy_block:
            with _MEMORY_LOCK:
                _MEMORY_STATE['blocked_heavy_jobs'] = int(_MEMORY_STATE.get('blocked_heavy_jobs') or 0) + 1
            return (False, f'Память занята ({used2:.0f} МБ). Подождите 30–60 секунд и повторите экспорт.')
    return (True, '')

def _memory_worker_environment() -> dict:
    names = ['BOT_THREAD_STACK_KB', 'MALLOC_ARENA_MAX', 'PYTHONMALLOC', 'WEBHOOK_WORKERS', 'UI_WORKERS', 'CALLBACK_ACK_WORKERS', 'RECOVERY_WORKERS', 'REMINDER_WORKERS', 'FINANCE_WORKERS', 'FIN_FORWARD_WORKERS', 'FORWARD_WORKERS', 'BACKUP_WORKERS', 'DELTA_WORKERS', 'EXPORT_WORKERS', 'GENERAL_WORKERS', 'JOURNAL_WORKERS', 'DELAYED_WORKERS']
    return {name: os.getenv(name) for name in names if os.getenv(name) is not None}

def _memory_structure_snapshot(deep: bool=False) -> dict:
    result = {'threads': threading.active_count(), 'open_fds': None, 'worker_stack_kb': globals().get('_BOT_THREAD_STACK_KB'), 'glibc_allocator_v248': dict(globals().get('_GLIBC_ALLOCATOR_V248') or {}), 'soft_trim_mb': MEMORY_SOFT_TRIM_MB, 'worker_env_overrides': _memory_worker_environment()}
    try:
        result['open_fds'] = len(os.listdir('/proc/self/fd'))
    except Exception:
        pass
    try:
        chats = (globals().get('data') or {}).get('chats') or {}
        result['chats'] = len(chats)
        loaded = 0
        loaded_by_key = defaultdict(int)
        cold_keys = set(globals().get('LOWRAM_COLD_KEYS') or [])
        for store in chats.values():
            if isinstance(store, dict):
                for key in cold_keys:
                    if dict.__contains__(store, key):
                        loaded += 1
                        loaded_by_key[str(key)] += 1
        result['cold_fields_loaded'] = loaded
        result['cold_fields_by_key'] = dict(loaded_by_key)
    except Exception:
        pass
    try:
        audit_fn = globals().get('runtime_audit_metrics')
        if callable(audit_fn):
            result['audit_metrics'] = audit_fn()
    except Exception:
        pass
    try:
        wd_fn = globals().get('window_diagnostic_stats')
        if callable(wd_fn):
            result['window_diagnostics'] = wd_fn()
    except Exception:
        pass
    try:
        result['file_jobs'] = len(globals().get('_FILE_JOB_STATE') or {})
        result['journal_action_rows'] = len(globals().get('BOT_ACTION_LOG') or [])
        result['journal_buffer_rows'] = len(globals().get('_JOURNAL_DURABLE_BUFFER') or [])
        result['runtime_events'] = len(globals().get('_RUNTIME_EVENTS') or [])
        result['memory_events'] = len(_MEMORY_EVENTS)
        result['active_memory_operations'] = len(_MEMORY_ACTIVE)
    except Exception:
        pass
    try:
        sched = globals().get('DELAYED_SCHEDULER')
        result['delayed_scheduler'] = sched.stats() if sched is not None else {}
    except Exception:
        pass
    try:
        pools_fn = globals().get('_runtime_pool_stats')
        result['queues'] = pools_fn() if callable(pools_fn) else {}
    except Exception:
        pass
    if deep:
        try:
            result['gc_count'] = list(_memory_gc.get_count())
            result['gc_stats'] = _memory_gc.get_stats()
            result['ru_maxrss_mb'] = round(float(_memory_resource.getrusage(_memory_resource.RUSAGE_SELF).ru_maxrss) / 1024.0, 1)
        except Exception:
            pass
    return result

def memory_runtime_summary() -> dict:
    quick = memory_quick_snapshot()
    with _MEMORY_LOCK:
        state = {'last_level': _MEMORY_STATE.get('last_level'), 'last_check_at': _MEMORY_STATE.get('last_check_at'), 'last_trim_at': _MEMORY_STATE.get('last_trim_at'), 'last_trim_reason': _MEMORY_STATE.get('last_trim_reason'), 'trim_count': _MEMORY_STATE.get('trim_count'), 'malloc_trim_count': _MEMORY_STATE.get('malloc_trim_count'), 'blocked_heavy_jobs': _MEMORY_STATE.get('blocked_heavy_jobs'), 'peak_container_mb_seen': _MEMORY_STATE.get('peak_container_mb_seen'), 'peak_python_mb_seen': _MEMORY_STATE.get('peak_python_mb_seen'), 'active_operations': len(_MEMORY_ACTIVE), 'event_rows': len(_MEMORY_EVENTS)}
    children = _memory_child_processes()
    try:
        wd_fn = globals().get('window_diagnostic_stats')
        wd = wd_fn() if callable(wd_fn) else {}
    except Exception:
        wd = {}
    return {'level': memory_level(quick), 'quick': quick, 'state': state, 'children_rss_mb': round(sum((float(x.get('rss_mb') or 0.0) for x in children)), 1), 'children': children[:8], 'window_diagnostics': wd}

def memory_forensics_snapshot(deep: bool=False) -> dict:
    quick = memory_quick_snapshot()
    with _MEMORY_LOCK:
        state = dict(_MEMORY_STATE)
        active = {k: dict(v) for k, v in _MEMORY_ACTIVE.items()}
        events = list(_MEMORY_EVENTS)[-80:]
    return {'enabled': MEMORY_GUARD_ENABLED, 'level': memory_level(quick), 'thresholds_mb': {'configured': {'warning': MEMORY_WARNING_MB, 'high': MEMORY_HIGH_MB, 'critical': MEMORY_CRITICAL_MB, 'emergency': MEMORY_EMERGENCY_MB, 'heavy_block': MEMORY_HEAVY_BLOCK_MB}, 'effective': _memory_effective_thresholds(quick)}, 'quick': quick, 'process_rollup': _memory_proc_rollup(), 'children': _memory_child_processes(), 'structures': _memory_structure_snapshot(deep=deep), 'state': state, 'active_operations': active, 'events': events}

def _memory_safe_restart_possible() -> bool:
    if not MEMORY_SAFE_RESTART_ENABLED:
        return False
    try:
        uptime = time.monotonic() - float(globals().get('_RUNTIME_STARTED_MONO') or time.monotonic())
        if uptime < MEMORY_SAFE_RESTART_MIN_UPTIME:
            return False
    except Exception:
        return False
    try:
        for pool_name in ('WEBHOOK_TASK_POOL', 'FINANCE_TASK_POOL', 'FIN_FORWARD_TASK_POOL', 'FORWARD_TASK_POOL', 'DELTA_TASK_POOL', 'RECOVERY_TASK_POOL'):
            pool = globals().get(pool_name)
            if pool is None:
                continue
            st = pool.stats() or {}
            if int(st.get('pending', 0) or 0) > 0 or int(st.get('active', 0) or 0) > 0:
                return False
        mt_fn = globals().get('mega_task_registry_stats')
        if callable(mt_fn):
            mt = mt_fn() or {}
            if int(mt.get('processing', 0) or 0) > 0 or int(mt.get('pending', 0) or 0) > 0 or int(mt.get('running', 0) or 0) > 0:
                return False
    except Exception:
        return False
    return True

def _memory_request_safe_restart(snapshot: dict):
    with _MEMORY_LOCK:
        if _MEMORY_STATE.get('safe_restart_requested'):
            return
        _MEMORY_STATE['safe_restart_requested'] = True
    _memory_emit('memory_safe_restart_requested', {'snapshot': snapshot}, 'CRITICAL')
    try:
        shutdown = globals().get('runtime_graceful_shutdown')
        if callable(shutdown):
            shutdown('MEMORY_GUARD')
    finally:
        os._exit(0)

def memory_guard_tick():
    if not MEMORY_GUARD_ENABLED:
        return
    try:
        snap = memory_quick_snapshot()
        level = memory_level(snap)
        with _MEMORY_LOCK:
            previous = str(_MEMORY_STATE.get('last_level') or 'normal')
            _MEMORY_STATE['last_level'] = level
            _MEMORY_STATE['last_check_at'] = now_local().isoformat(timespec='seconds') if 'now_local' in globals() else datetime.now(timezone.utc).isoformat(timespec='seconds')
            _MEMORY_STATE['last_snapshot'] = dict(snap)
        if level != previous:
            _memory_emit('memory_level_changed', {'from': previous, 'to': level, 'snapshot': snap}, 'WARN' if level != 'normal' else 'INFO')
        # v247: trim fragmentation before the adaptive cgroup warning threshold.
        # UI/finance work is never blocked; memory_trim already respects cooldown/busy state.
        python_rss = float(snap.get('python_rss_mb') or snap.get('rss_mb') or 0.0)
        if python_rss >= MEMORY_SOFT_TRIM_MB and level == 'normal':
            memory_trim('guard:soft', level='normal', force=False)
        if level in {'warning', 'high', 'critical', 'emergency'}:
            memory_trim(f'guard:{level}', level=level, force=level == 'emergency')
        if level == 'emergency':
            refreshed = memory_quick_snapshot()
            used = float(refreshed.get('effective_mb') or 0.0)
            if used >= float(_memory_effective_thresholds(refreshed).get('safe_restart') or MEMORY_SAFE_RESTART_MB) and _memory_safe_restart_possible():
                _memory_request_safe_restart(refreshed)
    except Exception as exc:
        _memory_emit('memory_guard_error', {'error': str(exc)[:500]}, 'ERROR')
    finally:
        try:
            DELAYED_SCHEDULER.schedule('memory-guard', MEMORY_GUARD_INTERVAL_SECONDS, memory_guard_tick)
        except Exception:
            pass

def start_memory_runtime_schedulers():
    if not MEMORY_GUARD_ENABLED:
        return False
    with _MEMORY_LOCK:
        if _MEMORY_STATE.get('started'):
            return False
        _MEMORY_STATE['started'] = True
    _memory_emit('memory_guard_started', {'interval': MEMORY_GUARD_INTERVAL_SECONDS, 'thresholds': {'warning': MEMORY_WARNING_MB, 'high': MEMORY_HIGH_MB, 'critical': MEMORY_CRITICAL_MB, 'emergency': MEMORY_EMERGENCY_MB}, 'thread_stack_kb': globals().get('_BOT_THREAD_STACK_KB'), 'env_overrides': _memory_worker_environment()})
    DELAYED_SCHEDULER.schedule('memory-guard', 5.0, memory_guard_tick)
    return True
# v262
