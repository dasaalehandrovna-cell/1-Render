# v262
from concurrent.futures import ThreadPoolExecutor, as_completed

def _v240_env_int(name: str, default: int, low: int=1, high: int=64) -> int:
    try:
        return max(low, min(high, int(os.getenv(name, str(default)) or default)))
    except Exception:
        return default

def _v240_env_bool(name: str, default: str='1') -> bool:
    return str(os.getenv(name, default) or default).strip().casefold() in {'1', 'true', 'yes', 'on', 'да', 'вкл'}
MEGA_SHARDED_STORAGE_V240 = _v240_env_bool('MEGA_SHARDED_STORAGE', '1')
MEGA_PARALLEL_MAX_V240 = _v240_env_int('MEGA_PARALLEL_MAX', 2, 1, 16)
MEGA_SHARD_DELTA_WORKERS_V240 = _v240_env_int('MEGA_SHARD_DELTA_WORKERS', 2, 1, 8)
MEGA_SHARD_HEAD_ENABLED_V240 = _v240_env_bool('MEGA_SHARD_HEAD_ENABLED', '1')
MEGA_SHARD_ROOT_V240 = MEGA_BACKUP_DIR.rstrip('/') + '/shards'
MEGA_SHARD_CHATS_ROOT_V240 = MEGA_SHARD_ROOT_V240 + '/chats'

def _v240_mega_business_active() -> bool:
    """True only when MEGA is the selected durable contour, not Telegram-primary."""
    try:
        tg = globals().get('telegram_durable_primary_v234')
        if callable(tg) and bool(tg()):
            return False
    except Exception:
        pass
    try:
        return bool(mega_is_configured())
    except Exception:
        return False
_V240_LANE_LIMITS = {'finance': _v240_env_int('MEGA_LANE_FINANCE', 2, 1, 8), 'forwarding': _v240_env_int('MEGA_LANE_FORWARD', 2, 1, 8), 'reminders': _v240_env_int('MEGA_LANE_REMINDERS', 1, 1, 8), 'tasks': _v240_env_int('MEGA_LANE_TASKS', 2, 1, 8), 'gomonk': _v240_env_int('MEGA_LANE_GOMONK', 1, 1, 8), 'settings': _v240_env_int('MEGA_LANE_SETTINGS', 1, 1, 8), 'snapshot': _v240_env_int('MEGA_LANE_SNAPSHOT', 1, 1, 2), 'restore': _v240_env_int('MEGA_LANE_RESTORE', 2, 1, 8), 'journal': _v240_env_int('MEGA_LANE_JOURNAL', 1, 1, 4), 'cleanup': _v240_env_int('MEGA_LANE_CLEANUP', 1, 1, 2), 'misc': _v240_env_int('MEGA_LANE_MISC', 1, 1, 8)}
_V240_LANE_SEM = {k: threading.BoundedSemaphore(v) for k, v in _V240_LANE_LIMITS.items()}
_V240_PAR_CV = threading.Condition(threading.RLock())
_V240_PAR_WAITING = {0: 0, 1: 0, 2: 0, 3: 0}
_V240_PAR_ACTIVE = 0
_V240_RESOURCE_GUARD = threading.RLock()
_V240_RESOURCE_LOCKS = {}
_V240_PAR_STATS_LOCK = threading.RLock()
_V240_PAR_STATS = {'active': 0, 'peak': 0, 'started': 0, 'completed': 0, 'errors': 0, 'by_lane': defaultdict(lambda: {'started': 0, 'completed': 0, 'errors': 0, 'active': 0, 'peak': 0})}

def mega_shard_chat_dir_v240(chat_id: int) -> str:
    return f'{MEGA_SHARD_CHATS_ROOT_V240}/chat_{int(chat_id)}'

def mega_shard_domain_dir_v240(chat_id: int, domain: str) -> str:
    safe = re.sub('[^a-z0-9_-]+', '_', str(domain or 'state').casefold()).strip('_') or 'state'
    return mega_shard_chat_dir_v240(int(chat_id)).rstrip('/') + '/' + safe

def _v240_chat_id_from_path(text: str):
    m = re.search('/shards/chats/chat_(-?\\d+)(?:/|$)', str(text or '').replace('\\', '/'))
    if m:
        try:
            return int(m.group(1))
        except Exception:
            return None
    return None

def _v240_lane_and_resource(cmd: str, args) -> tuple[str, str, int]:
    parts = [str(x or '').replace('\\', '/') for x in args or []]
    text = ' '.join(parts)
    low = text.casefold()
    chat_id = _v240_chat_id_from_path(text)
    domain = None
    if chat_id is not None:
        m = re.search('/shards/chats/chat_-?\\d+/([^/\\s]+)', low)
        domain = (m.group(1) if m else 'state').strip()
    lane = 'misc'
    pri = 1
    if domain in {'finance', 'forwarding', 'reminders', 'tasks', 'gomonk', 'settings'}:
        lane = domain
        pri = 0 if domain in {'finance', 'tasks'} else 1
    elif '/ledger/finance' in low:
        lane, pri = ('finance', 0)
    elif '/tasks/' in low:
        lane, pri = ('tasks', 0 if '/pending/' in low else 1)
    elif '/database/' in low or 'current_manifest' in low or 'generation_' in low or ('.sqlite' in low):
        lane = 'restore' if str(cmd) in {'mega-get', 'mega-find'} else 'snapshot'
        pri = 1 if lane == 'restore' else 2
    elif '/runtime/journal' in low or 'journal_' in low or '/runtime/' in low:
        lane, pri = ('journal', 3)
    elif str(cmd) == 'mega-rm':
        lane, pri = ('cleanup', 3)
    elif str(cmd) in {'mega-get', 'mega-find'}:
        lane, pri = ('restore', 1)
    canonical_tokens = ('current_manifest.json', 'storage_control.json', 'latest_global.json')
    if any((tok in low for tok in canonical_tokens)):
        resource = 'canonical:pointer'
    elif chat_id is not None:
        resource = f'chat:{chat_id}:{domain or lane}'
    elif lane == 'finance':
        m = re.search('ledger_\\d+_(-?\\d+)_', low)
        resource = f'finance:{m.group(1)}' if m else 'finance:legacy'
    elif lane == 'tasks':
        m = re.search('task_([a-z0-9_-]+)\\.json', low)
        resource = f'task:{m.group(1)}' if m else 'tasks:legacy'
    elif lane == 'snapshot':
        resource = 'snapshot:canonical'
    elif str(cmd) in {'mega-login', 'mega-logout', 'mega-whoami'}:
        resource = 'session'
    else:
        target = parts[-1] if parts else str(cmd or 'misc')
        resource = f'{lane}:{target[:220]}'
    return (lane, resource, pri)

def _v240_resource_lock(key: str):
    with _V240_RESOURCE_GUARD:
        lock = _V240_RESOURCE_LOCKS.get(key)
        if lock is None:
            lock = threading.RLock()
            _V240_RESOURCE_LOCKS[key] = lock
        return lock

def _v240_priority_enter(priority: int):
    global _V240_PAR_ACTIVE
    priority = max(0, min(3, int(priority)))
    with _V240_PAR_CV:
        _V240_PAR_WAITING[priority] += 1
        try:
            while _V240_PAR_ACTIVE >= MEGA_PARALLEL_MAX_V240 or any((_V240_PAR_WAITING[p] > 0 for p in range(priority))):
                _V240_PAR_CV.wait(timeout=0.25)
            _V240_PAR_ACTIVE += 1
        finally:
            _V240_PAR_WAITING[priority] = max(0, _V240_PAR_WAITING[priority] - 1)

def _v240_priority_exit():
    global _V240_PAR_ACTIVE
    with _V240_PAR_CV:
        _V240_PAR_ACTIVE = max(0, _V240_PAR_ACTIVE - 1)
        _V240_PAR_CV.notify_all()

def mega_parallel_execute_v240(exe: str, cmd: str, args, timeout_value):
    """Execute MEGAcmd with bounded parallelism and per-shard serialization."""
    if not MEGA_SHARDED_STORAGE_V240:
        with MEGA_COMMAND_LOCK:
            return subprocess.run([exe] + list(args or []), capture_output=True, text=True, timeout=timeout_value)
    lane, resource, priority = _v240_lane_and_resource(cmd, args)
    lane_sem = _V240_LANE_SEM.get(lane) or _V240_LANE_SEM['misc']
    resource_lock = _v240_resource_lock(resource)
    with resource_lock:
        lane_sem.acquire()
        _v240_priority_enter(priority)
        with _V240_PAR_STATS_LOCK:
            _V240_PAR_STATS['active'] += 1
            _V240_PAR_STATS['started'] += 1
            _V240_PAR_STATS['peak'] = max(_V240_PAR_STATS['peak'], _V240_PAR_STATS['active'])
            row = _V240_PAR_STATS['by_lane'][lane]
            row['active'] += 1
            row['started'] += 1
            row['peak'] = max(row['peak'], row['active'])
        try:
            cp = subprocess.run([exe] + list(args or []), capture_output=True, text=True, timeout=timeout_value)
            with _V240_PAR_STATS_LOCK:
                _V240_PAR_STATS['completed'] += 1
                _V240_PAR_STATS['by_lane'][lane]['completed'] += 1
            return cp
        except Exception:
            with _V240_PAR_STATS_LOCK:
                _V240_PAR_STATS['errors'] += 1
                _V240_PAR_STATS['by_lane'][lane]['errors'] += 1
            raise
        finally:
            with _V240_PAR_STATS_LOCK:
                _V240_PAR_STATS['active'] = max(0, _V240_PAR_STATS['active'] - 1)
                _V240_PAR_STATS['by_lane'][lane]['active'] = max(0, _V240_PAR_STATS['by_lane'][lane]['active'] - 1)
            _v240_priority_exit()
            lane_sem.release()

def mega_parallel_status_v240() -> dict:
    with _V240_PAR_STATS_LOCK:
        return {'enabled': bool(MEGA_SHARDED_STORAGE_V240), 'global_limit': int(MEGA_PARALLEL_MAX_V240), 'active': int(_V240_PAR_STATS['active']), 'peak': int(_V240_PAR_STATS['peak']), 'started': int(_V240_PAR_STATS['started']), 'completed': int(_V240_PAR_STATS['completed']), 'errors': int(_V240_PAR_STATS['errors']), 'lane_limits': dict(_V240_LANE_LIMITS), 'by_lane': {k: dict(v) for k, v in _V240_PAR_STATS['by_lane'].items()}}
_V240_META_LOCK = threading.RLock()
_V240_META_SEEDED = set()

def _v240_chat_meta_payload(chat_id: int) -> dict:
    cid = int(chat_id)
    info = {}
    try:
        info = dict(get_chat_store(cid).get('info') or {})
    except Exception:
        info = {}
    return {'kind': 'telegram_bot_mega_chat_shard', 'schema_version': 1, 'chat_id': cid, 'chat_type': str(info.get('type') or ('private' if cid > 0 else 'unknown')), 'title': str(info.get('title') or get_chat_display_name(cid) or f'Чат {cid}')[:250], 'bot_version': str(globals().get('VERSION') or ''), 'updated_at': now_local().isoformat(timespec='seconds')}

def _v240_seed_chat_meta_sync(chat_id: int):
    cid = int(chat_id)
    with _V240_META_LOCK:
        if cid in _V240_META_SEEDED:
            return True
    folder = mega_shard_chat_dir_v240(cid)
    tmp = ''
    try:
        os.makedirs(MEGA_LOCAL_TMP_DIR, exist_ok=True)
        fd, tmp = tempfile.mkstemp(prefix=f'mega_shard_meta_{cid}_', suffix='.json', dir=MEGA_LOCAL_TMP_DIR)
        os.close(fd)
        _save_json(tmp, _v240_chat_meta_payload(cid))
        ok = bool(mega_put_replace(tmp, folder, 'meta.json', archive_previous=False))
        if ok:
            with _V240_META_LOCK:
                _V240_META_SEEDED.add(cid)
        return ok
    except Exception as exc:
        try:
            log_error(f'mega shard meta {cid}: {exc}')
        except Exception:
            pass
        return False
    finally:
        try:
            if tmp and os.path.exists(tmp):
                os.remove(tmp)
        except Exception:
            pass

def _v240_schedule_chat_meta(chat_id: int):
    cid = int(chat_id)
    with _V240_META_LOCK:
        if cid in _V240_META_SEEDED:
            return
    pool = globals().get('BACKUP_TASK_POOL')
    if pool is not None:
        try:
            if pool.submit_unique(f'mega-shard-meta:{cid}', _v240_seed_chat_meta_sync, cid):
                return
        except Exception:
            pass
    threading.Thread(target=_v240_seed_chat_meta_sync, args=(cid,), daemon=True).start()

def _v240_publish_head_sync(chat_id: int, domain: str, remote_delta: str, payload: dict):
    cid = int(chat_id)
    domain = str(domain or 'state')
    expected_epoch = int((payload or {}).get('_storage_epoch_v241', globals().get('_V241_STORAGE_EPOCH', 0)) or 0)
    if expected_epoch != int(globals().get('_V241_STORAGE_EPOCH', 0) or 0) or globals().get('_V241_RESTORE_ACTIVE', False):
        return False
    tmp = ''
    try:
        folder = mega_shard_domain_dir_v240(cid, domain)
        head = {'kind': 'telegram_bot_mega_shard_head', 'schema_version': 1, 'chat_id': cid, 'domain': domain, 'latest_delta': str(remote_delta or ''), 'latest_delta_id': str((payload or {}).get('delta_id') or ''), 'event_count': int((payload or {}).get('event_count') or 0), 'updated_at': str((payload or {}).get('created_at') or now_local().isoformat(timespec='microseconds')), 'bot_version': str(globals().get('VERSION') or ''), 'storage_lineage_v239': str((payload or {}).get('storage_lineage_v239') or '')}
        fd, tmp = tempfile.mkstemp(prefix=f'mega_head_{cid}_{domain}_', suffix='.json', dir=MEGA_LOCAL_TMP_DIR)
        os.close(fd)
        _save_json(tmp, head)
        return bool(mega_put_replace(tmp, folder, 'HEAD.json', archive_previous=False))
    except Exception as exc:
        try:
            log_error(f'mega shard HEAD {cid}/{domain}: {exc}')
        except Exception:
            pass
        return False
    finally:
        try:
            if tmp and os.path.exists(tmp):
                os.remove(tmp)
        except Exception:
            pass

def _v240_schedule_head(chat_id: int, domain: str, remote_delta: str, payload: dict):
    if not MEGA_SHARD_HEAD_ENABLED_V240:
        return
    if globals().get('_V241_RESTORE_ACTIVE', False):
        return
    _v240_schedule_chat_meta(chat_id)
    payload = _delta_json_clone(payload or {})
    payload['_storage_epoch_v241'] = int(globals().get('_V241_STORAGE_EPOCH', 0) or 0)
    pool = globals().get('BACKUP_TASK_POOL')
    key = f'mega-shard-head:{int(chat_id)}:{domain}'
    if pool is not None:
        try:
            if pool.submit_unique(key, _v240_publish_head_sync, int(chat_id), str(domain), str(remote_delta), payload):
                return
        except Exception:
            pass
    threading.Thread(target=_v240_publish_head_sync, args=(int(chat_id), str(domain), str(remote_delta), payload), daemon=True).start()
_V240_ORIG_RUN_DELTA_BATCH = _canon_run_delta_batch__001
_V240_PENDING_DOMAIN_LOCK = threading.RLock()
_V240_PENDING_DOMAINS = defaultdict(set)
_V240_ORIG_SCHEDULE_DELTA = _canon_schedule_delta_backup__002
_V240_ORIG_CRITICAL_DELTA = _canon_persist_critical_delta_now__002

def _v240_domain_from_reason(reason: str) -> str:
    text = str(reason or 'change').casefold()
    if 'remind' in text or 'напомин' in text:
        return 'reminders'
    if 'forward' in text or 'пересыл' in text:
        return 'forwarding'
    if 'gomonk' in text or 'гомон' in text:
        return 'gomonk'
    if 'task' in text or 'задач' in text:
        return 'tasks'
    if any((x in text for x in ('finance', 'record', 'balance', 'expense', 'income', 'delta_retry', 'quick_upload'))):
        return 'finance'
    if any((x in text for x in ('setting', 'config', 'tenant', 'annotation', 'permission', 'google', 'contour', 'constitution'))):
        return 'settings'
    return 'state'

def _canon_schedule_delta_backup__003(chat_id=None, delay=None, reason='change'):
    if chat_id is not None and MEGA_SHARDED_STORAGE_V240 and _v240_mega_business_active():
        try:
            with _V240_PENDING_DOMAIN_LOCK:
                _V240_PENDING_DOMAINS[int(chat_id)].add(_v240_domain_from_reason(reason))
        except Exception:
            pass
    if callable(_V240_ORIG_SCHEDULE_DELTA):
        return _V240_ORIG_SCHEDULE_DELTA(chat_id, delay=delay, reason=reason)
    return False

def _canon_persist_critical_delta_now__003(chat_id: int) -> bool:
    if MEGA_SHARDED_STORAGE_V240 and _v240_mega_business_active():
        try:
            with _V240_PENDING_DOMAIN_LOCK:
                _V240_PENDING_DOMAINS[int(chat_id)].add('finance')
        except Exception:
            pass
    if callable(_V240_ORIG_CRITICAL_DELTA):
        return bool(_V240_ORIG_CRITICAL_DELTA(int(chat_id)))
    return False

def _v240_pick_pending_domain(chat_id: int) -> str:
    with _V240_PENDING_DOMAIN_LOCK:
        vals = set(_V240_PENDING_DOMAINS.get(int(chat_id)) or set())
    if len(vals) == 1:
        return next(iter(vals))
    if not vals:
        try:
            if is_finance_mode(int(chat_id)):
                return 'finance'
        except Exception:
            pass
        return 'state'
    return 'mixed'

def _v240_shard_delta_day_dir(chat_id: int, domain: str, day_key: str) -> str:
    return mega_shard_domain_dir_v240(int(chat_id), domain).rstrip('/') + '/deltas/' + str(day_key)

def _v240_delta_upload_payload(payload: dict) -> tuple[bool, str]:
    if not payload or not mega_is_configured():
        return (False, '')
    cid = payload.get('_v240_shard_chat_id')
    if not MEGA_SHARDED_STORAGE_V240 or cid is None:
        return _delta_upload_payload_legacy_v240(payload)
    domain = str(payload.get('_v240_shard_domain') or 'state')
    day = str(payload.get('created_at') or today_key())[:10]
    remote_dir = _v240_shard_delta_day_dir(int(cid), domain, day)
    clean = dict(payload)
    clean.pop('_v240_shard_chat_id', None)
    clean.pop('_v240_shard_domain', None)
    clean['storage_layout'] = 'mega_sharded_parallel_v240'
    clean['shard'] = {'chat_id': int(cid), 'domain': domain}
    name = f"delta_{clean.get('delta_id')}.json"
    tmp = ''
    try:
        soft = max(128 * 1024, int(os.getenv('MEGA_DELTA_SOFT_WARN_BYTES', str(512 * 1024)) or 512 * 1024))
        hard = max(soft + 1, int(os.getenv('MEGA_DELTA_HARD_MAX_BYTES', str(1024 * 1024)) or 1024 * 1024))
        encoded = json.dumps(clean, ensure_ascii=False, separators=(',', ':'), default=str).encode('utf-8')
        if len(encoded) > hard:
            try:
                log_error(f'[MEGA SHARD DELTA BLOCKED] chat={cid} domain={domain} bytes={len(encoded)} hard={hard}; full snapshot scheduled')
            except Exception:
                pass
            _mark_global_snapshot_pending()
            return (False, '')
        if len(encoded) > soft:
            try:
                bot_journal('mega_shard_delta_large_v240', int(cid), f'domain={domain}; bytes={len(encoded)}; soft={soft}', 'WARN')
            except Exception:
                pass
        os.makedirs(MEGA_LOCAL_TMP_DIR, exist_ok=True)
        tmp = os.path.join(MEGA_LOCAL_TMP_DIR, name)
        with open(tmp, 'wb') as fh:
            fh.write(encoded)
        mega_ensure_remote_path(remote_dir)
        _mega_run('mega-put', [tmp, remote_dir], check=True, timeout=MEGA_TIMEOUT)
        remote = remote_dir.rstrip('/') + '/' + name
        _v240_schedule_head(int(cid), domain, remote, clean)
        return (True, remote)
    except Exception as exc:
        try:
            log_error(f'[MEGA SHARD DELTA] chat={cid} domain={domain}: {exc}')
        except Exception:
            pass
        return (False, '')
    finally:
        try:
            if tmp and os.path.exists(tmp):
                os.remove(tmp)
        except Exception:
            pass
_delta_upload_payload_legacy_v240 = _canon_delta_upload_payload__001

def _canon_run_delta_batch__002():
    """Build one exact delta per chat and upload independent shards in parallel."""
    global _delta_last_success_at, _delta_last_file, _delta_last_event_count, _delta_last_error, _delta_root_baseline
    batch_epoch = int(globals().get('_V241_STORAGE_EPOCH', 0) or 0)
    if globals().get('_V241_RESTORE_ACTIVE', False):
        return False
    if not MEGA_SHARDED_STORAGE_V240:
        return bool(_V240_ORIG_RUN_DELTA_BATCH()) if callable(_V240_ORIG_RUN_DELTA_BATCH) else False
    with _delta_state_lock:
        chat_ids = sorted(_delta_pending_chats)
        generation_map = {cid: int(_delta_chat_generation.get(cid, 0)) for cid in chat_ids}
    if not chat_ids:
        return True
    built = []
    for cid in chat_ids:
        payload, baseline = _build_delta_payload([cid], {cid: generation_map[cid]})
        if payload is not None:
            payload['_v240_shard_chat_id'] = int(cid)
            payload['_v240_shard_domain'] = _v240_pick_pending_domain(cid)
            payload['_storage_epoch_v241'] = batch_epoch
            try:
                _lineage_fn = globals().get('_v239_storage_lineage')
                if callable(_lineage_fn):
                    payload['storage_lineage_v239'] = str(_lineage_fn(True) or '')
            except Exception:
                pass
        built.append((cid, payload, baseline))
    uploads = {}
    todo = [(cid, payload, baseline) for cid, payload, baseline in built if payload is not None]
    if batch_epoch != int(globals().get('_V241_STORAGE_EPOCH', 0) or 0) or globals().get('_V241_RESTORE_ACTIVE', False):
        try:
            bot_journal('stale_delta_batch_skipped_v241', None, f"job={batch_epoch}; current={globals().get('_V241_STORAGE_EPOCH', 0)}")
        except Exception:
            pass
        return False
    if todo:
        workers = min(MEGA_SHARD_DELTA_WORKERS_V240, len(todo))
        with ThreadPoolExecutor(max_workers=max(1, workers), thread_name_prefix='mega-shard-delta') as ex:
            future_map = {ex.submit(_v240_delta_upload_payload, payload): (cid, payload, baseline) for cid, payload, baseline in todo}
            for fut in as_completed(future_map):
                cid, payload, baseline = future_map[fut]
                try:
                    uploads[cid] = (fut.result(), payload, baseline)
                except Exception as exc:
                    uploads[cid] = ((False, ''), payload, baseline)
                    log_error(f'mega shard delta worker {cid}: {exc}')
    success_any = False
    failed = []
    latest_remote = ''
    total_events = 0
    root_candidate = None
    for cid, payload, baseline in built:
        if payload is None:
            ok, remote = (True, '')
        else:
            (ok, remote), _, _ = uploads.get(cid, ((False, ''), payload, baseline))
        if ok:
            with _delta_state_lock:
                for bid, sigs in (baseline.get('record_sigs') or {}).items():
                    _delta_record_baseline[int(bid)] = dict(sigs or {})
                for bid, sigs in (baseline.get('meta_sigs') or {}).items():
                    _delta_meta_baseline[int(bid)] = dict(sigs or {})
                if int(_delta_chat_generation.get(cid, 0)) == int(generation_map[cid]):
                    _delta_pending_chats.discard(cid)
            with _V240_PENDING_DOMAIN_LOCK:
                _V240_PENDING_DOMAINS.pop(int(cid), None)
            root_candidate = baseline.get('root_sigs') or root_candidate
            if payload is not None:
                success_any = True
                latest_remote = remote or latest_remote
                total_events += int(payload.get('event_count') or 0)
        else:
            failed.append(cid)
    if root_candidate is not None and (success_any or not todo):
        with _delta_state_lock:
            _delta_root_baseline = dict(root_candidate or {})
    with timer_lock:
        for cid in chat_ids:
            if cid not in failed:
                _quick_backup_timers.pop(int(cid), None)
                _quick_backup_dirty_chats.discard(int(cid))
    if success_any:
        _delta_last_success_at = now_local().isoformat(timespec='microseconds')
        _delta_last_file = latest_remote
        _delta_last_event_count = total_events
        _delta_last_error = ''
        _mark_global_snapshot_pending()
        try:
            bot_journal('mega_sharded_delta_batch_v240', None, f'chats={len(chat_ids) - len(failed)}; failed={len(failed)}; events={total_events}; workers={min(MEGA_SHARD_DELTA_WORKERS_V240, max(1, len(todo)))}')
        except Exception:
            pass
    if failed:
        _delta_last_error = 'shard delta upload failed: ' + ','.join((str(x) for x in failed[:8]))
        return False
    with _delta_state_lock:
        more_pending = bool(_delta_pending_chats)
    if more_pending:
        schedule_delta_backup(None, delay=1.0, reason='changes_during_upload')
    return True
try:
    globals()['_V234_MEGA_RUN_DELTA_BATCH'] = _canon_run_delta_batch__002
except Exception:
    pass

def _v240_delta_sort_key(path: str):
    name = os.path.basename(str(path or ''))
    m = re.search('delta_(\\d{8})_(\\d{6})_(\\d{6})_', name)
    if m:
        return ''.join(m.groups())
    return name

def _canon_delta_remote_candidates_after__002(created_at: str, limit: int | None=None) -> list[str]:
    rows = []
    try:
        rows.extend(_mega_find_remote_files(mega_delta_remote_root(), 'delta_*.json'))
    except Exception:
        pass
    if MEGA_SHARDED_STORAGE_V240:
        try:
            rows.extend(_mega_find_remote_files(MEGA_SHARD_CHATS_ROOT_V240, 'delta_*.json'))
        except Exception:
            pass
    base_ts = _parse_iso_timestamp(created_at)
    selected = []
    for path in sorted(set(rows), key=_v240_delta_sort_key):
        name = os.path.basename(path)
        match = re.search('delta_(\\d{8})_(\\d{6})_(\\d{6})_', name)
        if match:
            try:
                dt = datetime.strptime(''.join(match.groups()), '%Y%m%d%H%M%S%f').replace(tzinfo=get_tz())
                if dt.timestamp() <= base_ts:
                    continue
            except Exception:
                pass
        selected.append(path)
    return selected[:int(limit or MEGA_DELTA_RESTORE_LIMIT)]

def _canon_prune_delta_files_after_full_snapshot__002():
    try:
        rows = []
        try:
            rows.extend(_mega_find_remote_files(mega_delta_remote_root(), 'delta_*.json'))
        except Exception:
            pass
        if MEGA_SHARDED_STORAGE_V240:
            try:
                rows.extend(_mega_find_remote_files(MEGA_SHARD_CHATS_ROOT_V240, 'delta_*.json'))
            except Exception:
                pass
        rows = sorted(set(rows), key=_v240_delta_sort_key, reverse=True)
        keep = max(30, int(MEGA_DELTA_KEEP_FILES))
        removed = 0
        for remote_path in rows[keep:]:
            try:
                if _mega_run('mega-rm', [remote_path], check=False, timeout=30).returncode == 0:
                    removed += 1
            except Exception:
                pass
        if removed:
            try:
                bot_journal('mega_delta_pruned_v240', None, f'removed={removed}; keep={keep}; sharded=1')
            except Exception:
                pass
        return removed
    except Exception as exc:
        try:
            log_error(f'delta prune v240: {exc}')
        except Exception:
            pass
        return 0

def _canon_v177_download_remote_json_batch__002(remote_paths: list[str], batch_threshold: int=6) -> tuple[dict, list[str]]:
    paths = [str(x) for x in remote_paths or [] if str(x or '').strip()]
    if not paths:
        return ({}, [])
    grouped = defaultdict(list)
    for remote in paths:
        grouped[remote.rsplit('/', 1)[0] if '/' in remote else remote].append(remote)
    mapping = {}
    cleanup_dirs = []
    guard = threading.RLock()

    def fetch_group(parent, group):
        local_map = {}
        dirs = []
        if len(group) >= int(batch_threshold):
            workdir = tempfile.mkdtemp(prefix='v240_mega_batch_')
            dirs.append(workdir)
            try:
                _mega_run('mega-get', [parent, workdir], check=True, timeout=max(float(MEGA_TIMEOUT), 180.0))
                found = {}
                for base, _dirs, files in os.walk(workdir):
                    for name in files:
                        found.setdefault(name, os.path.join(base, name))
                for remote in group:
                    local = found.get(os.path.basename(remote))
                    if local and os.path.isfile(local):
                        local_map[remote] = local
            except Exception as exc:
                try:
                    log_error(f'[MEGA BATCH RESTORE v240] folder fallback {parent}: {str(exc)[:240]}')
                except Exception:
                    pass
        for remote in group:
            if remote in local_map:
                continue
            local = _mega_download_remote_path(remote)
            if local:
                local_map[remote] = local
                dirs.append(os.path.dirname(local))
        return (local_map, dirs)
    workers = min(_V240_LANE_LIMITS['restore'], len(grouped))
    with ThreadPoolExecutor(max_workers=max(1, workers), thread_name_prefix='mega-restore') as ex:
        futs = [ex.submit(fetch_group, parent, group) for parent, group in grouped.items()]
        for fut in as_completed(futs):
            try:
                lm, ds = fut.result()
                mapping.update(lm)
                cleanup_dirs.extend(ds)
            except Exception as exc:
                try:
                    log_error(f'mega restore parallel batch: {exc}')
                except Exception:
                    pass
    return (mapping, cleanup_dirs)
_V240_ORIG_CHAT_BACKUP_BUNDLE = _canon_mega_upload_chat_backup_bundle__001
_V240_ORIG_CHAT_LATEST_ONLY = _canon_mega_upload_chat_latest_json_only__001

def _canon_mega_upload_chat_backup_bundle__002(chat_id: int, month_key: str | None=None) -> bool:
    """Same public command semantics; files now live under chat/finance shard."""
    if not MEGA_SHARDED_STORAGE_V240 or not _v240_mega_business_active():
        return bool(_V240_ORIG_CHAT_BACKUP_BUNDLE(chat_id, month_key)) if callable(_V240_ORIG_CHAT_BACKUP_BUNDLE) else False
    if not is_backup_to_mega_enabled(chat_id):
        return False
    cid = int(chat_id)
    try:
        save_chat_json(cid)
        finance_root = mega_shard_domain_dir_v240(cid, 'finance')
        checkpoint_dir = finance_root + '/checkpoints'
        ok = bool(mega_put_replace(chat_json_file(cid), checkpoint_dir, 'latest.json', archive_previous=True))
        month_key = month_key or current_month_key()
        month_files = save_chat_monthly_backup_files(cid, month_key)
        json_month_path = month_files.get('json')
        if json_month_path:
            ok = bool(mega_put_replace(json_month_path, finance_root + '/monthly/' + str(month_key), 'current.json', archive_previous=True)) and ok
        _v240_schedule_chat_meta(cid)
        if ok:
            try:
                bot_journal('mega_chat_backup_sharded_v240', cid, f'month={month_key}')
            except Exception:
                pass
        return ok
    except Exception as exc:
        try:
            log_error(f'[MEGA SHARD CHAT BACKUP ERROR] {cid}: {exc}')
        except Exception:
            pass
        return False

def _canon_mega_upload_chat_latest_json_only__002(chat_id: int) -> bool:
    if not MEGA_SHARDED_STORAGE_V240 or not _v240_mega_business_active():
        return bool(_V240_ORIG_CHAT_LATEST_ONLY(chat_id)) if callable(_V240_ORIG_CHAT_LATEST_ONLY) else False
    cid = int(chat_id)
    if not is_backup_to_mega_enabled(cid):
        return False
    try:
        local_path = chat_json_file(cid)
        if not os.path.exists(local_path):
            local_path = save_chat_json_only(cid)
        if not local_path:
            return False
        _v240_schedule_chat_meta(cid)
        return bool(mega_put_replace(local_path, mega_shard_domain_dir_v240(cid, 'finance') + '/checkpoints', 'latest.json', archive_previous=True))
    except Exception as exc:
        try:
            log_error(f'mega_upload_chat_latest_json_only shard v240({cid}): {exc}')
        except Exception:
            pass
        return False
_V240_ORIG_TASK_UPLOAD_PENDING = _canon_mega_task_upload_new_pending__003
_V240_ORIG_TASK_MOVE = _canon_mega_task_move__001
_V240_ORIG_TASK_REFRESH = _canon_mega_task_refresh_registry__002

def _v240_task_dir(chat_id: int, state: str) -> str:
    state = str(state or 'pending').casefold()
    if state not in {'pending', 'running', 'done', 'failed'}:
        state = 'pending'
    return mega_shard_domain_dir_v240(int(chat_id), 'tasks').rstrip('/') + '/' + state

def _canon_mega_task_upload_new_pending__004(update_id, task_payload: dict) -> bool:
    global _mega_task_last_error
    try:
        tg = globals().get('telegram_durable_primary_v234')
        if callable(tg) and bool(tg()):
            return bool(_V240_ORIG_TASK_UPLOAD_PENDING(update_id, task_payload)) if callable(_V240_ORIG_TASK_UPLOAD_PENDING) else False
    except Exception:
        pass
    chat_id = (task_payload or {}).get('chat_id')
    if not MEGA_SHARDED_STORAGE_V240 or chat_id in (None, ''):
        return bool(_V240_ORIG_TASK_UPLOAD_PENDING(update_id, task_payload)) if callable(_V240_ORIG_TASK_UPLOAD_PENDING) else False
    key = _mega_task_id(update_id)
    local_path = ''
    started = time.monotonic()
    if not mega_tasks_active():
        return False
    try:
        known = mega_task_known_state(key)
        if known in {'pending', 'running', 'done'}:
            return True
        remote_dir = _v240_task_dir(int(chat_id), 'pending')
        mega_ensure_remote_path(remote_dir)
        os.makedirs(MEGA_LOCAL_TMP_DIR, exist_ok=True)
        local_path = os.path.join(MEGA_LOCAL_TMP_DIR, mega_task_filename(key))
        with open(local_path, 'w', encoding='utf-8') as fh:
            json.dump(task_payload, fh, ensure_ascii=False, separators=(',', ':'), default=str)
        try:
            _mega_run('mega-put', [local_path, remote_dir], check=True, timeout=MEGA_TIMEOUT)
        except Exception:
            existing = _mega_find_remote_files(remote_dir, mega_task_filename(key), limit=2)
            if not existing:
                raise
        remote_final = remote_dir.rstrip('/') + '/' + mega_task_filename(key)
        _mega_task_update_registry(key, 'pending', remote_final)
        with _MEGA_TASK_LOCK:
            _mega_task_counters['persisted'] += 1
        _v240_schedule_chat_meta(int(chat_id))
        try:
            bot_journal('mega_task_timing', int(chat_id), f'phase=sharded_pending_v240 update={key} elapsed={time.monotonic() - started:.3f}s')
        except Exception:
            pass
        return True
    except Exception as exc:
        _mega_task_last_error = str(exc)[:500]
        with _MEGA_TASK_LOCK:
            _mega_task_counters['persist_errors'] += 1
        try:
            log_error(f'[MEGA SHARD TASK PERSIST] update={key}: {exc}')
        except Exception:
            pass
        return False
    finally:
        try:
            if local_path and os.path.exists(local_path):
                os.remove(local_path)
        except Exception:
            pass

def _canon_mega_task_move__002(update_id, from_state: str, to_state: str) -> bool:
    global _mega_task_last_error
    if not MEGA_SHARDED_STORAGE_V240:
        return bool(_V240_ORIG_TASK_MOVE(update_id, from_state, to_state)) if callable(_V240_ORIG_TASK_MOVE) else False
    key = _mega_task_id(update_id)
    with _MEGA_TASK_LOCK:
        row = dict(_mega_task_registry.get(key) or {})
    src = str(row.get('path') or mega_task_remote_path(key, from_state))
    norm = src.replace('\\', '/')
    if f'/{from_state}/' in norm:
        dst = norm.replace(f'/{from_state}/', f'/{to_state}/', 1)
        dst_dir = dst.rsplit('/', 1)[0]
    else:
        dst_dir = mega_task_remote_dir(to_state)
        dst = dst_dir.rstrip('/') + '/' + mega_task_filename(key)
    try:
        mega_ensure_remote_path(dst_dir)
        res = _mega_run('mega-mv', [src, dst], check=False, timeout=60)
        if res.returncode != 0:
            found = _mega_find_remote_files(dst_dir, mega_task_filename(key), limit=2)
            if not found:
                raise RuntimeError((res.stderr or res.stdout or f'cannot move {src} -> {dst}')[:500])
        _mega_task_update_registry(key, to_state, dst)
        return True
    except Exception as exc:
        _mega_task_last_error = str(exc)[:500]
        try:
            log_error(f'[MEGA SHARD TASK MOVE] update={key} {from_state}->{to_state}: {exc}')
        except Exception:
            pass
        return False

def _canon_mega_task_refresh_registry__003() -> dict:
    global _mega_task_registry_loaded_at, _mega_task_last_error
    if not mega_tasks_active():
        return mega_task_registry_stats()
    try:
        tg = globals().get('telegram_durable_primary_v234')
        if callable(tg) and bool(tg()):
            return _V240_ORIG_TASK_REFRESH() if callable(_V240_ORIG_TASK_REFRESH) else mega_task_registry_stats()
    except Exception:
        pass
    if callable(_V240_ORIG_TASK_REFRESH):
        try:
            _V240_ORIG_TASK_REFRESH()
        except Exception:
            pass
    try:
        rows = _mega_find_remote_files(MEGA_SHARD_CHATS_ROOT_V240, 'task_*.json', limit=None) if MEGA_SHARDED_STORAGE_V240 else []
        rank = {'failed': 1, 'pending': 2, 'running': 3, 'done': 4}
        with _MEGA_TASK_LOCK:
            for path in rows:
                name = os.path.basename(path)
                m = re.fullmatch('task_([A-Za-z0-9_-]+)\\.json', name)
                if not m:
                    continue
                state = next((s for s in ('pending', 'running', 'done', 'failed') if f'/{s}/' in path.replace('\\', '/')), '')
                if not state:
                    continue
                key = m.group(1)
                old = _mega_task_registry.get(key)
                if old is None or rank[state] >= rank.get(str(old.get('state') or ''), 0):
                    _mega_task_registry[key] = {'state': state, 'path': path, 'loaded_at': now_local().isoformat(timespec='seconds')}
            _mega_task_registry_loaded_at = now_local().isoformat(timespec='seconds')
        return mega_task_registry_stats()
    except Exception as exc:
        _mega_task_last_error = str(exc)[:500]
        try:
            log_error(f'mega_task_refresh_registry shard v240: {exc}')
        except Exception:
            pass
        return mega_task_registry_stats()

def _canon_mega_task_prune_done_async__002():

    def worker():
        try:
            rows = []
            try:
                rows.extend(_mega_find_remote_files(mega_task_remote_root(), 'task_*.json'))
            except Exception:
                pass
            if MEGA_SHARDED_STORAGE_V240:
                try:
                    rows.extend(_mega_find_remote_files(MEGA_SHARD_CHATS_ROOT_V240, 'task_*.json'))
                except Exception:
                    pass
            groups = defaultdict(list)
            for p in rows:
                if '/done/' in p.replace('\\', '/'):
                    groups[p.rsplit('/', 1)[0]].append(p)
            for _parent, group in groups.items():
                for remote in sorted(group, reverse=True)[MEGA_TASK_DONE_KEEP:]:
                    try:
                        _mega_run('mega-rm', [remote], check=False, timeout=30)
                    except Exception:
                        pass
        except Exception as exc:
            try:
                log_error(f'_mega_task_prune_done_async v240: {exc}')
            except Exception:
                pass
    threading.Thread(target=worker, daemon=True).start()
try:
    runtime_event('mega_sharded_parallel_v240', f"enabled={int(MEGA_SHARDED_STORAGE_V240)}; global={MEGA_PARALLEL_MAX_V240}; lanes={json.dumps(_V240_LANE_LIMITS, separators=(',', ':'))}", 'INFO')
except Exception:
    pass
# v262
