# v262
def mega_is_configured(control_plane: bool=False) -> bool:
    recovery = bool(globals().get('_V240_RECOVERY_AUTHORITY_ACTIVE', False)) or bool(control_plane)
    if not recovery:
        contour_fn = globals().get('mega_contour_enabled_v234')
        if callable(contour_fn):
            try:
                if not contour_fn():
                    return False
            except Exception:
                return False
        else:
            raw = str(os.getenv('MEGA_CONTOUR_ENABLED', '0') or '0').strip().casefold()
            if raw not in {'1', 'true', 'yes', 'on', 'вкл'}:
                return False
    gate = globals().get('external_access_allowed_v233')
    gate_category = 'mega_control' if control_plane else 'mega'
    if callable(gate) and (not gate(gate_category)):
        return False
    return bool(MEGA_ENABLED and MEGA_EMAIL and MEGA_PASSWORD)

def mega_remote_file_path(filename: str=None) -> str:
    filename = filename or MEGA_LATEST_GLOBAL_NAME
    return MEGA_BACKUP_DIR.rstrip('/') + '/' + filename

def _mega_required_commands():
    return ['mega-login', 'mega-whoami', 'mega-mkdir', 'mega-put', 'mega-get', 'mega-rm', 'mega-mv', 'mega-find']

def mega_missing_commands():
    return [cmd for cmd in _mega_required_commands() if shutil.which(cmd) is None]

def _mega_memory_safe_args(cmd: str, args) -> list[str]:
    """Return diagnostic-only MEGAcmd arguments with credentials removed."""
    values = list(args or [])[:3]
    if str(cmd or '').lower() == 'mega-login':
        return ['<redacted-email>', '<redacted-secret>'][:len(values)]
    protected = {str(globals().get('MEGA_EMAIL') or ''), str(globals().get('MEGA_PASSWORD') or ''), str(os.getenv('BOT_TOKEN') or ''), str(os.getenv('TELEGRAM_BOT_TOKEN') or '')}
    protected.discard('')
    out = []
    for index, value in enumerate(values):
        text = str(value)
        if text in protected:
            out.append('<redacted>')
        elif index == 0:
            out.append(os.path.basename(text)[:120])
        else:
            out.append(text[:80])
    return out
_V178_MEGA_PRIORITY_CV = threading.Condition(threading.RLock())
_V178_MEGA_PRIORITY_WAITING = {0: 0, 1: 0, 2: 0, 3: 0}
_V178_MEGA_PRIORITY_ACTIVE = False
_MEGA_TRAFFIC_LOCK = threading.RLock()
_MEGA_TRAFFIC_STARTED_AT = time.time()
_MEGA_TRAFFIC_STATS = {'put_bytes': 0, 'put_count': 0, 'by_category': {}}

def _mega_traffic_category(remote: str, local: str='') -> str:
    text = (str(remote or '') + ' ' + str(local or '')).casefold()
    if '/tasks/' in text:
        return 'critical_tasks'
    if '/deltas/' in text or 'delta_' in text:
        return 'deltas'
    if '/ledger/' in text:
        return 'constitution_ledger'
    if '/database/generations' in text or ('generation_' in text and '.sqlite' in text):
        return 'sqlite_generation'
    if '/database/' in text or 'bot_state' in text or '.sqlite' in text:
        return 'sqlite_database'
    if '/runtime/' in text or 'runtime_' in text:
        return 'runtime_diagnostics'
    if 'journal_' in text or '/journal' in text:
        return 'journal'
    if '/monthly/' in text:
        return 'chat_monthly'
    if '/chats/' in text or 'latest_chat_' in text:
        return 'chat_backup'
    if 'botsource' in text or 'bot_source' in text or str(local or '').endswith('.py'):
        return 'source_archive'
    return 'other'

def _mega_traffic_record_put(local_path: str, remote: str) -> None:
    try:
        size = int(os.path.getsize(local_path)) if local_path and os.path.isfile(local_path) else 0
    except Exception:
        size = 0
    category = _mega_traffic_category(remote, local_path)
    with _MEGA_TRAFFIC_LOCK:
        _MEGA_TRAFFIC_STATS['put_bytes'] = int(_MEGA_TRAFFIC_STATS.get('put_bytes', 0) or 0) + size
        _MEGA_TRAFFIC_STATS['put_count'] = int(_MEGA_TRAFFIC_STATS.get('put_count', 0) or 0) + 1
        by = _MEGA_TRAFFIC_STATS.setdefault('by_category', {})
        row = by.setdefault(category, {'bytes': 0, 'count': 0})
        row['bytes'] = int(row.get('bytes', 0) or 0) + size
        row['count'] = int(row.get('count', 0) or 0) + 1
    try:
        traffic_audit_record('mega_put', f'mega-put:{category}', size + 256, 0, False)
    except Exception:
        pass

def _mega_traffic_download_size(args) -> int:
    try:
        if len(args or []) < 2:
            return 0
        remote = str(args[0] or '')
        target = str(args[-1] or '')
        if os.path.isfile(target):
            return int(os.path.getsize(target))
        if os.path.isdir(target):
            candidate = os.path.join(target, os.path.basename(remote.rstrip('/')))
            if os.path.isfile(candidate):
                return int(os.path.getsize(candidate))
    except Exception:
        pass
    return 0

def mega_traffic_stats() -> dict:
    with _MEGA_TRAFFIC_LOCK:
        out = {'started_at': _MEGA_TRAFFIC_STARTED_AT, 'put_bytes': int(_MEGA_TRAFFIC_STATS.get('put_bytes', 0) or 0), 'put_count': int(_MEGA_TRAFFIC_STATS.get('put_count', 0) or 0), 'by_category': {k: dict(v) for k, v in (_MEGA_TRAFFIC_STATS.get('by_category') or {}).items()}}
    return out

def mega_traffic_stats_text(compact: bool=False) -> str:
    s = mega_traffic_stats()
    total = float(s.get('put_bytes', 0) or 0) / (1024.0 * 1024.0)
    rows = sorted((s.get('by_category') or {}).items(), key=lambda kv: int((kv[1] or {}).get('bytes', 0) or 0), reverse=True)
    if compact:
        top = ', '.join((f"{k}={float(v.get('bytes', 0) or 0) / (1024 * 1024):.2f}MB" for k, v in rows[:5])) or 'пока 0'
        return f"MEGA upload этого процесса: {total:.2f} MB / {s.get('put_count', 0)} put; {top}"
    lines = [f"☁️ MEGA upload этого процесса: {total:.2f} MB / {s.get('put_count', 0)} put"]
    for k, v in rows:
        lines.append(f"• {k}: {float(v.get('bytes', 0) or 0) / (1024 * 1024):.2f} MB / {v.get('count', 0)}")
    return '\n'.join(lines)

def _v178_mega_priority(cmd: str, args) -> int:
    text = ' '.join((str(x or '') for x in args or [])).casefold()
    if any((x in text for x in ('/tasks/pending', '/ledger/finance'))):
        return 0
    if any((x in text for x in ('/tasks/running', '/tasks/done', '/tasks/failed', '/deltas/'))):
        return 1
    if any((x in text for x in ('/database/', 'generation_', 'current_manifest', 'sqlite', '/chats/', '/global', 'backup'))):
        return 2
    if any((x in text for x in ('/runtime/journal', '/runtime', 'journal_', 'runtime_slot_'))):
        return 3
    if str(cmd or '') in {'mega-find', 'mega-whoami', 'mega-mkdir'}:
        return 2
    return 1

def _v178_mega_gate_enter(priority: int) -> None:
    global _V178_MEGA_PRIORITY_ACTIVE
    priority = max(0, min(3, int(priority)))
    with _V178_MEGA_PRIORITY_CV:
        _V178_MEGA_PRIORITY_WAITING[priority] += 1
        try:
            while _V178_MEGA_PRIORITY_ACTIVE or any((_V178_MEGA_PRIORITY_WAITING[p] > 0 for p in range(priority))):
                _V178_MEGA_PRIORITY_CV.wait(timeout=0.5)
            _V178_MEGA_PRIORITY_ACTIVE = True
        finally:
            _V178_MEGA_PRIORITY_WAITING[priority] = max(0, _V178_MEGA_PRIORITY_WAITING[priority] - 1)

def _v178_mega_gate_exit() -> None:
    global _V178_MEGA_PRIORITY_ACTIVE
    with _V178_MEGA_PRIORITY_CV:
        _V178_MEGA_PRIORITY_ACTIVE = False
        _V178_MEGA_PRIORITY_CV.notify_all()

def _v177_legacy_0063_mega_run(cmd: str, args=None, timeout: int | None=None, check: bool=True, control_plane: bool=False):
    """One MEGAcmd command at a time; v178 gives durable business writes priority over diagnostics."""
    gate = globals().get('external_access_allowed_v233')
    gate_category = 'mega_control' if bool(control_plane) else 'mega'
    if callable(gate) and (not gate(gate_category)):
        try:
            logger_fn = globals().get('external_block_log_v233')
            if callable(logger_fn):
                logger_fn(gate_category, str(cmd or ''))
        except Exception:
            pass
        raise RuntimeError(f"external_local_only_v233:{gate_category}:{str(cmd or '')}")
    args = list(args or [])
    exe = shutil.which(cmd)
    if not exe:
        raise RuntimeError(f'MEGAcmd command not found: {cmd}')

    def _execute_once():
        mem_ctx = globals().get('memory_operation')

        def _run_command():
            parallel_exec = globals().get('mega_parallel_execute_v240')
            if callable(parallel_exec):
                try:
                    return parallel_exec(exe, cmd, args, timeout or MEGA_TIMEOUT)
                except subprocess.TimeoutExpired:
                    raise RuntimeError(f'{cmd} timeout after {timeout or MEGA_TIMEOUT}s')
            priority = _v178_mega_priority(cmd, args)
            _v178_mega_gate_enter(priority)
            try:
                with MEGA_COMMAND_LOCK:
                    try:
                        return subprocess.run([exe] + args, capture_output=True, text=True, timeout=timeout or MEGA_TIMEOUT)
                    except subprocess.TimeoutExpired:
                        raise RuntimeError(f'{cmd} timeout after {timeout or MEGA_TIMEOUT}s')
            finally:
                _v178_mega_gate_exit()
        if callable(mem_ctx):
            safe_args = _mega_memory_safe_args(cmd, args)
            with mem_ctx(f'mega:{cmd}', {'args': safe_args}, heavy=cmd in {'mega-find', 'mega-get', 'mega-put'}, quiet=True):
                res = _run_command()
        else:
            res = _run_command()
        if res.returncode != 0 and str(cmd or '') == 'mega-put' and (len(args) >= 2):
            text = ((res.stderr or '') + '\n' + (res.stdout or '')).casefold()
            if "couldn't find destination folder" in text or 'could not find destination folder' in text or ('destination folder' in text and 'find' in text):
                healer = globals().get('_v190_recreate_remote_path_uncached')
                if callable(healer):
                    try:
                        if healer(str(args[-1] or '')):
                            res = _run_command()
                    except Exception as heal_exc:
                        try:
                            log_error(f'[MEGA ROOT SELF-HEAL] {heal_exc}')
                        except Exception:
                            pass
        if check and res.returncode != 0:
            out = (res.stdout or '').strip()
            err = (res.stderr or '').strip()
            msg = (err or out or f'returncode={res.returncode}')[:800]
            raise RuntimeError(f'{cmd} failed: {msg}')
        _audit_error = bool(res.returncode != 0)
        if _audit_error and str(cmd or '') == 'mega-mkdir':
            try:
                _mkdir_text = ((res.stderr or '') + '\n' + (res.stdout or '')).casefold()
                if 'already exists' in _mkdir_text or 'exists' in _mkdir_text:
                    _audit_error = False
            except Exception:
                pass
        if res.returncode == 0 and str(cmd or '') == 'mega-put' and (len(args) >= 2):
            try:
                _mega_traffic_record_put(str(args[0] or ''), str(args[-1] or ''))
            except Exception:
                pass
        elif str(cmd or '') == 'mega-get':
            try:
                inbound = _mega_traffic_download_size(args) if res.returncode == 0 else 0
                _remote = str(args[0] or '') if args else ''
                _local = str(args[-1] or '') if args else ''
                _cat = _mega_traffic_category(_remote, _local)
                traffic_audit_record('mega_get', f'mega-get:{_cat}', 256 + sum((len(str(x or '')) for x in args)), inbound, _audit_error)
            except Exception:
                pass
        else:
            try:
                inbound = len(((res.stdout or '') + (res.stderr or '')).encode('utf-8', errors='ignore'))
                _probe = ' '.join((str(x or '') for x in args))
                _cat = _mega_traffic_category(_probe, '')
                traffic_audit_record('mega_control', f'mega:{cmd}:{_cat}', 192 + sum((len(str(x or '')) for x in args)), inbound, _audit_error)
            except Exception:
                pass
        return res
    guard = globals().get('guarded_external_call')
    if callable(guard):
        return guard(f'mega:{cmd}', _execute_once, attempts=2, base_delay=0.6)
    return _execute_once()
try:
    _v177_legacy_0063_mega_run.__name__ = '_mega_run'
except Exception:
    pass
TRAFFIC_AUDIT_REMOTE_DIR = MEGA_BACKUP_DIR.rstrip('/') + '/runtime/traffic_audit'
TRAFFIC_AUDIT_REMOTE_NAME = 'latest_traffic_audit.json.gz'

def traffic_audit_checkpoint_to_mega(reason: str='periodic') -> bool:
    if not TRAFFIC_AUDIT_ENABLED or not mega_is_configured():
        return True
    tmp = ''
    try:
        snap = traffic_audit_snapshot()
        snap['kind'] = 'telegram_bot_traffic_audit'
        snap['bot_version'] = str(globals().get('VERSION') or '')
        snap['reason'] = str(reason or 'periodic')[:80]
        try:
            with _RUNTIME_LOCK:
                rs = dict(_RUNTIME_STATE)
            snap['runtime_summary'] = {'phase': rs.get('phase'), 'ready': bool(rs.get('ready')), 'last_event': rs.get('last_event'), 'last_error': rs.get('last_error'), 'started_at': rs.get('started_at'), 'last_webhook_at': rs.get('last_webhook_at')}
            snap['runtime_summary']['recent_events'] = [dict(x) for x in list(globals().get('_RUNTIME_EVENTS') or [])[-12:]]
            mem = _runtime_memory_stats() if '_runtime_memory_stats' in globals() else {}
            snap['runtime_summary']['memory'] = {k: mem.get(k) for k in ('rss_mb', 'peak_rss_mb', 'container_current_mb', 'container_peak_mb', 'limit_mb', 'cgroup_events')}
        except Exception:
            pass
        os.makedirs(MEGA_LOCAL_TMP_DIR, exist_ok=True)
        tmp = os.path.join(MEGA_LOCAL_TMP_DIR, 'traffic_audit_checkpoint.json.gz')
        raw = json.dumps(snap, ensure_ascii=False, separators=(',', ':'), default=str).encode('utf-8')
        with gzip.open(tmp, 'wb', compresslevel=6) as fh:
            fh.write(raw)
        ok = bool(mega_put_replace(tmp, TRAFFIC_AUDIT_REMOTE_DIR, TRAFFIC_AUDIT_REMOTE_NAME, archive_previous=False))
        try:
            fn = globals().get('traffic_audit_render_log_summary')
            if callable(fn):
                fn(str(reason or 'periodic'))
        except Exception:
            pass
        return ok
    except Exception as exc:
        try:
            log_error(f'traffic audit checkpoint: {exc}')
        except Exception:
            pass
        return False
    finally:
        try:
            if tmp and os.path.exists(tmp):
                os.remove(tmp)
        except Exception:
            pass

def traffic_audit_restore_from_mega() -> bool:
    if not TRAFFIC_AUDIT_ENABLED or not mega_is_configured():
        return False
    folder = ''
    try:
        rows = _mega_find_remote_files(TRAFFIC_AUDIT_REMOTE_DIR, TRAFFIC_AUDIT_REMOTE_NAME, 5)
        if not rows:
            rows = _mega_find_remote_files(TRAFFIC_AUDIT_REMOTE_DIR, 'latest_traffic_audit.json', 5)
        if not rows:
            return False
        remote = rows[0]
        folder = tempfile.mkdtemp(prefix='traffic_audit_restore_')
        res = _mega_run('mega-get', [remote, folder], check=False, timeout=60)
        if res.returncode != 0:
            return False
        local = os.path.join(folder, os.path.basename(remote))
        if not os.path.isfile(local):
            cand = list(Path(folder).glob('*.json*'))
            local = str(cand[0]) if cand else ''
        if not local or not os.path.isfile(local):
            return False
        if str(local).endswith('.gz'):
            with gzip.open(local, 'rt', encoding='utf-8') as fh:
                payload = json.load(fh)
        else:
            payload = json.loads(Path(local).read_text(encoding='utf-8'))
        ok = bool(traffic_audit_load_baseline(payload))
        if ok:
            try:
                fn = globals().get('traffic_audit_render_log_summary')
                if callable(fn):
                    fn('restored_baseline')
            except Exception:
                pass
        return ok
    except Exception as exc:
        try:
            log_error(f'traffic audit restore: {exc}')
        except Exception:
            pass
        return False
    finally:
        try:
            if folder:
                shutil.rmtree(folder, ignore_errors=True)
        except Exception:
            pass
_V178_MEGA_CACHE_LOCK = threading.RLock()
_V178_MEGA_SESSION_OK_UNTIL = 0.0
_V178_MEGA_SESSION_TTL_SECONDS = max(60.0, min(1800.0, float(os.getenv('MEGA_SESSION_CACHE_SECONDS', '300') or '300')))
_V178_MEGA_KNOWN_DIRS = set()

def _v190_invalidate_mega_path_cache(remote_dir: str | None=None) -> None:
    """Forget a remote path and its descendants after an external rename/delete."""
    target = str(remote_dir or '').rstrip('/')
    with _V178_MEGA_CACHE_LOCK:
        if not target:
            _V178_MEGA_KNOWN_DIRS.clear()
        else:
            for item in list(_V178_MEGA_KNOWN_DIRS):
                if item == target or item.startswith(target + '/') or target.startswith(item + '/'):
                    _V178_MEGA_KNOWN_DIRS.discard(item)
    try:
        globals()['_mega_task_dirs_ready'] = False
    except Exception:
        pass

def _v190_schedule_root_reseed() -> None:
    """After an externally deleted/renamed canonical root, seed a new full DB snapshot ASAP.

    The user action that discovered the loss is never made to wait for this snapshot.
    ``_submit_global_snapshot_v90`` itself defers while UI/content/finance lanes are busy.
    """

    def _fire():
        fn = globals().get('_submit_global_snapshot_v90')
        if callable(fn):
            fn('mega_root_self_heal')
            return
        snap = globals().get('mega_upload_latest_database_backup')
        pool = globals().get('BACKUP_TASK_POOL')
        if callable(snap) and pool is not None:
            try:
                pool.submit_unique('mega-root-reseed-v190', snap, True)
            except Exception:
                pass
    try:
        sched = globals().get('DELAYED_SCHEDULER')
        if sched is not None:
            sched.cancel('mega-root-reseed-v190')
            sched.schedule('mega-root-reseed-v190', 2.0, _fire)
        else:
            _fire()
    except Exception:
        pass

def _v190_recreate_remote_path_uncached(remote_dir: str) -> bool:
    """Recreate a MEGA directory tree without trusting the process-lifetime cache."""
    remote_dir = str(remote_dir or MEGA_BACKUP_DIR).strip() or MEGA_BACKUP_DIR
    _v190_invalidate_mega_path_cache(remote_dir)
    exe = shutil.which('mega-mkdir')
    if not exe:
        return False
    parts = [p for p in remote_dir.strip('/').split('/') if p]
    current = ''
    canonical_root = '/' + str(MEGA_BACKUP_DIR or '').strip('/')
    canonical_root_created = False
    for part in parts:
        current += '/' + part
        priority = 0 if current.startswith(str(MEGA_BACKUP_DIR).rstrip('/')) else 2
        _v178_mega_gate_enter(priority)
        try:
            with MEGA_COMMAND_LOCK:
                res = subprocess.run([exe, current], capture_output=True, text=True, timeout=30)
        finally:
            _v178_mega_gate_exit()
        text = ((res.stderr or '') + '\n' + (res.stdout or '')).casefold()
        ok = res.returncode == 0 or 'already exists' in text or 'exists' in text
        if not ok:
            return False
        if current == canonical_root and res.returncode == 0:
            canonical_root_created = True
        with _V178_MEGA_CACHE_LOCK:
            _V178_MEGA_KNOWN_DIRS.add(current)
    try:
        bot_journal('mega_root_self_healed_v190', None, f'path={remote_dir}; root_created={int(canonical_root_created)}')
    except Exception:
        pass
    if canonical_root_created:
        _v190_schedule_root_reseed()
    return True

def mega_login_if_needed(control_plane: bool=False) -> bool:
    """Check the MEGA session at most once per TTL instead of before every command chain."""
    global _V178_MEGA_SESSION_OK_UNTIL
    if not mega_is_configured(control_plane=control_plane):
        return False
    now_m = time.monotonic()
    with _V178_MEGA_CACHE_LOCK:
        if now_m < float(_V178_MEGA_SESSION_OK_UNTIL or 0.0):
            return True
    missing = mega_missing_commands()
    if missing:
        raise RuntimeError('MEGAcmd не установлен или команды не в PATH: ' + ', '.join(missing))
    try:
        # v250: on a fresh Render container there is usually no MEGAcmd session yet.
        # Do not spend up to 30s proving that before the real login.  This shorter
        # probe is used only by the control plane; normal MEGA operations keep their
        # original reliability timeouts.
        if control_plane:
            try:
                whoami_timeout = max(3, min(12, int(os.getenv('MEGA_CONTROL_WHOAMI_TIMEOUT', '6') or '6')))
            except Exception:
                whoami_timeout = 6
        else:
            whoami_timeout = 30
        res = _mega_run('mega-whoami', [], check=False, timeout=whoami_timeout, control_plane=control_plane)
        text = ((res.stdout or '') + '\n' + (res.stderr or '')).lower()
        if res.returncode == 0 and (MEGA_EMAIL.lower() in text or 'account e-mail' in text or 'email' in text):
            with _V178_MEGA_CACHE_LOCK:
                _V178_MEGA_SESSION_OK_UNTIL = time.monotonic() + _V178_MEGA_SESSION_TTL_SECONDS
            return True
    except Exception:
        pass
    res = _mega_run('mega-login', [MEGA_EMAIL, MEGA_PASSWORD], check=False, timeout=MEGA_TIMEOUT, control_plane=control_plane)
    if res.returncode != 0:
        msg = ((res.stderr or '') or (res.stdout or '') or 'login failed')[:500]
        raise RuntimeError(f'mega-login failed: {msg}')
    with _V178_MEGA_CACHE_LOCK:
        _V178_MEGA_SESSION_OK_UNTIL = time.monotonic() + _V178_MEGA_SESSION_TTL_SECONDS
    return True

def _v178_mega_ensure_cached_path(remote_dir: str, force: bool=False) -> bool:
    if not mega_login_if_needed():
        return False
    remote_dir = (remote_dir or MEGA_BACKUP_DIR).strip() or MEGA_BACKUP_DIR
    if force:
        return _v190_recreate_remote_path_uncached(remote_dir)
    parts = [p for p in remote_dir.strip('/').split('/') if p]
    current = ''
    for part in parts:
        current += '/' + part
        with _V178_MEGA_CACHE_LOCK:
            if current in _V178_MEGA_KNOWN_DIRS:
                continue
        res = _mega_run('mega-mkdir', [current], check=False, timeout=30)
        text = ((res.stderr or '') + '\n' + (res.stdout or '')).casefold()
        if res.returncode != 0 and 'already exists' not in text and ('exists' not in text):
            return False
        with _V178_MEGA_CACHE_LOCK:
            _V178_MEGA_KNOWN_DIRS.add(current)
    return True

def mega_ensure_remote_dir(force: bool=False) -> bool:
    return _v178_mega_ensure_cached_path(MEGA_BACKUP_DIR, force=force)

def mega_ensure_remote_path(remote_dir: str, force: bool=False) -> bool:
    """Create a path cheaply; force=True ignores stale runtime cache."""
    return _v178_mega_ensure_cached_path(remote_dir, force=force)

def mega_safe_name(value, fallback: str='chat') -> str:
    """Безопасное имя файла/папки для MEGA: имя чата + без мусора."""
    try:
        value = str(value or '').strip()
    except Exception:
        value = ''
    if not value:
        value = fallback
    value = value.replace(' ', '_')
    value = re.sub('[^0-9A-Za-zА-Яа-я_@.\\-]+', '', value)
    value = value.strip('._-')
    return (value or fallback)[:80]

def mega_chat_slug(chat_id: int) -> str:
    try:
        name = get_chat_display_name(chat_id)
    except Exception:
        name = f'chat_{chat_id}'
    safe = mega_safe_name(name, f'chat_{chat_id}')
    return f'{safe}_{chat_id}'

def mega_remote_chat_dir(chat_id: int) -> str:
    return f"{MEGA_BACKUP_DIR.rstrip('/')}/{MEGA_CHAT_BACKUP_DIR}/{mega_chat_slug(chat_id)}"

def mega_remote_month_dir(month_key: str) -> str:
    return f"{MEGA_BACKUP_DIR.rstrip('/')}/{MEGA_MONTHLY_BACKUP_DIR}/{month_key}"

def _copy_file_for_mega(src_path: str, dst_name: str) -> str | None:
    """Потоковая копия во временный файл для MEGA без чтения всего файла в RAM."""
    try:
        if not src_path or not os.path.exists(src_path):
            return None
        os.makedirs(MEGA_LOCAL_TMP_DIR, exist_ok=True)
        dst_path = os.path.join(MEGA_LOCAL_TMP_DIR, dst_name)
        with open(src_path, 'rb') as src, open(dst_path, 'wb') as dst:
            shutil.copyfileobj(src, dst, length=1024 * 1024)
        return dst_path
    except Exception as e:
        log_error(f'_copy_file_for_mega({src_path},{dst_name}): {e}')
        return None

def _mega_remote_missing_error(raw: str) -> bool:
    txt = str(raw or '').casefold()
    return any((x in txt for x in ("couldn't find", 'not found', 'no such file', 'does not exist')))

def _mega_find_remote_files(remote_dir: str, pattern: str, limit: int | None=None) -> list[str]:
    """Список удалённых файлов MEGA. Имена v90 содержат sortable timestamp."""
    if not mega_is_configured() or shutil.which('mega-find') is None:
        return []
    try:
        res = _mega_run('mega-find', [str(remote_dir), f'--pattern={pattern}', '--type=f'], check=False, timeout=60)
        rows = sorted({x.strip() for x in (res.stdout or '').splitlines() if x.strip()}, reverse=True)
        return rows[:int(limit)] if limit else rows
    except Exception as e:
        log_error(f'_mega_find_remote_files({remote_dir},{pattern}): {e}')
        return []

def _mega_prune_remote_history(remote_dir: str, pattern: str, keep: int) -> int:
    """Удаляет только лишние СТАРЫЕ исторические копии. Активный файл не затрагивается."""
    rows = _mega_find_remote_files(remote_dir, pattern)
    removed = 0
    for remote_path in rows[max(1, int(keep)):]:
        try:
            res = _mega_run('mega-rm', [remote_path], check=False, timeout=30)
            if res.returncode == 0:
                removed += 1
        except Exception:
            pass
    return removed

def _mega_prune_remote_history_bounded(remote_dir: str, pattern: str, keep: int, max_remove: int=50) -> int:
    """Incrementally reduce remote node count without a large maintenance burst."""
    rows = _mega_find_remote_files(remote_dir, pattern)
    removed = 0
    for remote_path in rows[max(1, int(keep)):max(1, int(keep)) + max(1, int(max_remove))]:
        try:
            res = _mega_run('mega-rm', [remote_path], check=False, timeout=30)
            if res.returncode == 0:
                removed += 1
        except Exception:
            pass
    return removed

def mega_diagnostic_node_housekeeping(max_remove: int=50) -> dict:
    """Keep diagnostics useful while preventing thousands of tiny MEGA nodes.

    MEGAcmd builds a local cache of the account tree on a fresh filesystem.  Old
    per-chunk journal nodes make that first account sync progressively slower even
    though their payload is tiny.  Cleanup runs only after READY and is bounded.
    """
    result = {'journal_removed': 0, 'critical_removed': 0}
    if not mega_is_configured():
        return result
    try:
        result['journal_removed'] = _mega_prune_remote_history_bounded(_journal_durable_remote_dir(), 'journal_*.json.gz', int(BOT_JOURNAL_DURABLE_REMOTE_KEEP), max_remove)
    except Exception as exc:
        result['journal_error'] = str(exc)[:240]
    try:
        critical_dir = _journal_durable_remote_dir()
        result['critical_removed'] = _mega_prune_remote_history_bounded(critical_dir, 'journal_critical_*.json.gz', 240, max_remove)
    except Exception as exc:
        result['critical_error'] = str(exc)[:240]
    try:
        if result.get('journal_removed') or result.get('critical_removed'):
            bot_journal('mega_node_housekeeping_v211', None, json.dumps(result, ensure_ascii=False, separators=(',', ':')))
    except Exception:
        pass
    return result

def _mega_promote_remote_candidate(remote_candidate: str, remote_final: str, *, history_dir: str | None=None, archive_name: str | None=None) -> bool:
    """Safely promote a candidate using only MEGAcmd operations it handles reliably.

    MEGAcmd `mv` can rename when destination does not exist and can move into an
    existing folder.  Some installed builds reject a single move that both crosses
    folders and renames (the v113 `must be a valid folder` spam).  Therefore we:
      1) rename old final inside its current folder;
      2) rename candidate -> final inside that same folder;
      3) only then move the archived old file into the existing history folder.

    If candidate promotion fails, best-effort rollback restores the old final.
    """
    final_parent = remote_final.rsplit('/', 1)[0] or '/'
    final_name = remote_final.rsplit('/', 1)[-1]
    candidate_parent = remote_candidate.rsplit('/', 1)[0] or '/'
    if candidate_parent.rstrip('/') != final_parent.rstrip('/'):
        raise RuntimeError('candidate and final must be in the same MEGA folder')
    mega_ensure_remote_path(final_parent)
    stamp = now_local().strftime('%Y%m%d_%H%M%S_%f')
    if archive_name:
        safe_archive_name = os.path.basename(str(archive_name))
    else:
        stem, ext = os.path.splitext(final_name)
        safe_archive_name = f"{mega_safe_name(stem, 'file')}__{stamp}{ext or '.json'}"
    remote_old_temp = final_parent.rstrip('/') + '/' + safe_archive_name
    old_moved = False
    mv_old = _mega_run('mega-mv', [remote_final, remote_old_temp], check=False, timeout=60)
    if mv_old.returncode == 0:
        old_moved = True
    else:
        err = (mv_old.stderr or mv_old.stdout or '')[:500]
        if not _mega_remote_missing_error(err):
            log_error(f'[MEGA PROMOTE] cannot stage previous {remote_final}: {err}')
            return False
    mv_new = None
    err = ''
    for _attempt in range(3):
        mv_new = _mega_run('mega-mv', [remote_candidate, remote_final], check=False, timeout=60)
        if mv_new.returncode == 0:
            break
        err = (mv_new.stderr or mv_new.stdout or '')[:500]
        if _attempt < 2 and _mega_remote_missing_error(err):
            time.sleep(0.25 * (_attempt + 1))
            continue
        break
    if mv_new is None or mv_new.returncode != 0:
        if old_moved:
            _mega_run('mega-mv', [remote_old_temp, remote_final], check=False, timeout=60)
        log_error(f'[MEGA PROMOTE] candidate activation failed {remote_candidate} -> {remote_final}: {err}')
        return False
    if old_moved:
        if history_dir:
            try:
                mega_ensure_remote_path(history_dir)
                moved = _mega_run('mega-mv', [remote_old_temp, history_dir], check=False, timeout=60)
                if moved.returncode != 0:
                    err = (moved.stderr or moved.stdout or '')[:500]
                    log_error(f'[MEGA PROMOTE] history move deferred for {remote_old_temp}: {err}')
            except Exception as e:
                log_error(f'[MEGA PROMOTE] history move deferred for {remote_old_temp}: {e}')
        else:
            _mega_run('mega-rm', [remote_old_temp], check=False, timeout=30)
    return True

def mega_put_replace(local_path: str, remote_dir: str, remote_name: str | None=None, *, archive_previous: bool=True) -> bool:
    """Safely update a MEGA file without rm->put and without cross-folder rename.

    Heartbeat callers may set archive_previous=False: runtime_latest then keeps no
    30-second history copies because immutable runtime events already have /events.
    """
    if not mega_is_configured() or not local_path or (not os.path.exists(local_path)):
        return False
    candidate_local = None
    _txn_lock = None
    try:
        _resolver = globals().get('_v240_lane_and_resource')
        _locker = globals().get('_v240_resource_lock')
        if callable(_resolver) and callable(_locker):
            try:
                _final_hint = remote_dir.rstrip('/') + '/' + str(remote_name or os.path.basename(local_path))
                _lane, _resource, _pri = _resolver('mega-put', [local_path, _final_hint])
                _txn_lock = _locker(_resource)
                _txn_lock.acquire()
            except Exception:
                _txn_lock = None
        mega_ensure_remote_path(remote_dir)
        final_name = str(remote_name or os.path.basename(local_path))
        stem, ext = os.path.splitext(final_name)
        stamp = now_local().strftime('%Y%m%d_%H%M%S_%f')
        candidate_name = f"candidate_{mega_safe_name(stem, 'file')}_{stamp}{ext or '.json'}"
        candidate_local = _copy_file_for_mega(local_path, candidate_name)
        if not candidate_local:
            return False
        _mega_run('mega-put', [candidate_local, remote_dir], check=True, timeout=MEGA_TIMEOUT)
        remote_candidate = remote_dir.rstrip('/') + '/' + candidate_name
        remote_file = remote_dir.rstrip('/') + '/' + final_name
        history_dir = None
        archive_name = None
        if archive_previous:
            history_dir = remote_dir.rstrip('/') + '/history'
            mega_ensure_remote_path(history_dir)
            archive_name = f"{mega_safe_name(stem, 'file')}__{stamp}{ext or '.json'}"
        ok = _mega_promote_remote_candidate(remote_candidate, remote_file, history_dir=history_dir, archive_name=archive_name)
        if not ok:
            return False
        if archive_previous and history_dir:
            try:
                _mega_prune_remote_history(history_dir, f"{mega_safe_name(stem, 'file')}__*{ext or '.json'}", MEGA_FILE_HISTORY_KEEP)
            except Exception:
                pass
        return True
    except Exception as e:
        log_error(f'[MEGA SAFE REPLACE ERROR] {local_path} -> {remote_dir}: {e}')
        return False
    finally:
        try:
            if candidate_local and os.path.exists(candidate_local):
                os.remove(candidate_local)
        except Exception:
            pass
        try:
            if _txn_lock is not None:
                _txn_lock.release()
        except Exception:
            pass
_MEGA_TASK_LOCK = threading.RLock()
_mega_task_registry = {}
_mega_task_processing = set()
_mega_task_counters = {'persisted': 0, 'recovered': 0, 'completed': 0, 'failed': 0, 'skipped_done': 0, 'persist_errors': 0, 'finalize_errors': 0}
_mega_task_last_error = ''
_mega_task_registry_loaded_at = ''
_mega_task_dirs_ready = False

def _canon_mega_tasks_active__001() -> bool:
    return bool(MEGA_TASKS_ENABLED and mega_is_configured() and (not RESTORE_GUARD_ACTIVE))

def mega_task_remote_root() -> str:
    return f"{MEGA_BACKUP_DIR.rstrip('/')}/{MEGA_TASK_BACKUP_DIR}"

def ensure_mega_task_dirs(force: bool=False) -> bool:
    global _mega_task_dirs_ready
    if not mega_tasks_active():
        return False
    with _MEGA_TASK_LOCK:
        if _mega_task_dirs_ready and (not force):
            return True
    try:
        mega_ensure_remote_path(mega_task_remote_root())
        for state in ('pending', 'running', 'done', 'failed'):
            mega_ensure_remote_path(mega_task_remote_dir(state))
        with _MEGA_TASK_LOCK:
            _mega_task_dirs_ready = True
        return True
    except Exception as e:
        log_error(f'ensure_mega_task_dirs: {e}')
        return False

def mega_task_remote_dir(state: str) -> str:
    state = str(state or 'pending').strip().lower()
    if state not in {'pending', 'running', 'done', 'failed'}:
        state = 'pending'
    return f"{mega_task_remote_root().rstrip('/')}/{state}"

def _mega_task_id(update_id) -> str:
    try:
        return str(int(update_id))
    except Exception:
        raw = str(update_id or '')
        return hashlib.sha256(raw.encode('utf-8', errors='ignore')).hexdigest()[:24]

def mega_task_filename(update_id) -> str:
    return f'task_{_mega_task_id(update_id)}.json'

def mega_task_remote_path(update_id, state: str) -> str:
    return f"{mega_task_remote_dir(state).rstrip('/')}/{mega_task_filename(update_id)}"

def _mega_task_update_registry(update_id, state: str, path: str | None=None):
    key = _mega_task_id(update_id)
    with _MEGA_TASK_LOCK:
        _mega_task_registry[key] = {'state': str(state), 'path': path or mega_task_remote_path(key, state), 'loaded_at': now_local().isoformat(timespec='seconds')}

def _canon_mega_task_known_state__001(update_id) -> str:
    key = _mega_task_id(update_id)
    with _MEGA_TASK_LOCK:
        return str((_mega_task_registry.get(key) or {}).get('state') or '')

def _v177_legacy_0064_mega_task_registry_stats() -> dict:
    with _MEGA_TASK_LOCK:
        states = defaultdict(int)
        for row in _mega_task_registry.values():
            states[str((row or {}).get('state') or 'unknown')] += 1
        processing = len(_mega_task_processing)
        counters = dict(_mega_task_counters)
        loaded_at = _mega_task_registry_loaded_at
        last_error = _mega_task_last_error
    return {'pending': int(states.get('pending', 0)), 'running': int(states.get('running', 0)), 'done': int(states.get('done', 0)), 'failed': int(states.get('failed', 0)), 'processing': processing, 'loaded_at': loaded_at, 'last_error': last_error, **counters}
try:
    _v177_legacy_0064_mega_task_registry_stats.__name__ = 'mega_task_registry_stats'
except Exception:
    pass

def durable_update_processed(update_id) -> bool:
    key = _mega_task_id(update_id)
    try:
        with data_lock:
            return key in ((data or {}).get('_durable_processed_updates', {}) or {})
    except Exception:
        return False

def mark_durable_update_processed(update_id, chat_id=None, update_type: str='other'):
    """Put the idempotency marker into the same global/delta state as bot data."""
    key = _mega_task_id(update_id)
    with data_lock:
        ledger = data.setdefault('_durable_processed_updates', {})
        if not isinstance(ledger, dict):
            ledger = {}
            data['_durable_processed_updates'] = ledger
        ledger[key] = {'at': now_local().isoformat(timespec='microseconds'), 'chat_id': chat_id, 'type': str(update_type or 'other')}
        while len(ledger) > MEGA_TASK_PROCESSED_KEEP:
            try:
                ledger.pop(next(iter(ledger)))
            except Exception:
                break
    save_data(data, root_only=True)

def _durable_raw_content_type(raw: dict | None) -> str:
    """Best-effort Telegram content classifier for durable forwarding diagnostics.

    Raw Bot API updates do not carry a `content_type` field.  We only use this label
    for task metadata/logging; delivery itself is always attempted by source message_id.
    """
    if not isinstance(raw, dict):
        return 'unknown'
    for key in ('text', 'photo', 'video', 'animation', 'audio', 'voice', 'video_note', 'document', 'sticker', 'location', 'venue', 'contact', 'dice', 'poll', 'game', 'story', 'paid_media', 'invoice', 'web_app_data'):
        if key in raw and raw.get(key) is not None:
            return key
    ignored = {'message_id', 'message_thread_id', 'direct_messages_topic', 'from', 'sender_chat', 'sender_boost_count', 'sender_business_bot', 'date', 'business_connection_id', 'chat', 'forward_origin', 'is_topic_message', 'is_automatic_forward', 'reply_to_message', 'external_reply', 'quote', 'reply_to_story', 'reply_to_checklist_task_id', 'via_bot', 'edit_date', 'has_protected_content', 'is_from_offline', 'media_group_id', 'author_signature', 'paid_star_count', 'effect_id', 'show_caption_above_media', 'has_media_spoiler', 'reply_markup'}
    for key in raw.keys():
        if key not in ignored:
            return str(key)
    return 'unknown'

def _durable_payload_message(payload: dict):
    """Return (raw_message_dict, source_chat_id, source_msg_id, media_group_id)."""
    if not isinstance(payload, dict):
        return (None, None, None, None)
    for name in ('message', 'edited_message', 'channel_post', 'edited_channel_post'):
        msg = payload.get(name)
        if not isinstance(msg, dict):
            continue
        try:
            chat_id = int((msg.get('chat') or {}).get('id'))
        except Exception:
            chat_id = None
        try:
            msg_id = int(msg.get('message_id') or 0) or None
        except Exception:
            msg_id = None
        group_id = str(msg.get('media_group_id') or '').strip() or None
        return (msg, chat_id, msg_id, group_id)
    return (None, None, None, None)

def _durable_forward_targets(source_chat_id: int | None) -> list[tuple]:
    if source_chat_id is None:
        return []
    try:
        return list(resolve_forward_targets(int(source_chat_id)) or [])
    except Exception as e:
        log_error(f'DURABLE resolve targets {source_chat_id}: {e}')
        return []

def _durable_record_edit_witness(chat_id: int, rid: int, amount=None, note=None, source_finance_text=None, usd_amount=None, usd_note=None, kind: str='finance') -> dict:
    witness = {'chat_id': int(chat_id), 'rid': int(rid), 'kind': str(kind or 'finance')}
    if amount is not None:
        witness['amount'] = float(amount)
    if note is not None:
        witness['note'] = str(note or '')
    if source_finance_text is not None:
        witness['source_finance_text'] = str(source_finance_text or '').strip()
    if usd_amount is not None:
        witness['usd_amount'] = float(usd_amount)
    if usd_note is not None:
        witness['usd_note'] = str(usd_note or '')
    return witness

def _durable_secret_edit_witness(chat_id: int, record_id: int, text: str) -> dict:
    return {'chat_id': int(chat_id), 'record_id': int(record_id), 'text': str(text or '').strip()}

def _durable_sanitize_inserted_text_no_network(text: str) -> str:
    """Receipt-time sanitizer: never calls Telegram before the durable task is persisted."""
    value = str(text or '').strip()
    value = re.sub('(?m)^\\s*@[A-Za-z0-9_]{3,}\\s+(?=(?:\\(|[+\\-–]?\\s*\\d))', '', value)
    return re.sub('[ \\t]+', ' ', value).strip()

def _durable_direct_insert_value(clean: str, token_match) -> str:
    """Remove an inline bot prefix before deleting a service token.

    Telegram can send ``@botname (EDITREM|...) text``.  The live handler knows the
    username, while the receipt-time verifier must not call Telegram.  Stripping a prefix
    only when it is the entire segment before the token keeps ordinary @mentions intact.
    """
    prefix = str(clean or '')[:token_match.start()]
    suffix = str(clean or '')[token_match.end():]
    if re.fullmatch('\\s*@[A-Za-z0-9_]{3,}\\s*', prefix or ''):
        prefix = ''
    return _durable_sanitize_inserted_text_no_network((prefix + ' ' + suffix).strip())

def _durable_extract_edit_expectations(payload: dict, source_chat_id: int, source_msg_id: int, text: str) -> dict:
    """Recognize deterministic edit/input routes before ordinary finance classification.

    This is verification metadata only.  It never performs a business mutation.  The same
    payload can therefore be checked safely after a Render restart without replaying money.
    """
    result = {'consumes_source': False, 'record_edits': [], 'secret_edits': [], 'secret_copy_edits': [], 'reminder_edits': []}
    clean = str(text or '').strip()
    if not clean:
        try:
            store = get_chat_store(int(source_chat_id))
            secret_full_wait = store.get('secret_full_edit_wait') or {}
            if secret_full_wait.get('type') == 'secret_full_edit':
                result['consumes_source'] = True
        except Exception:
            pass
        return result
    is_edited_update = bool((payload or {}).get('edited_message') or (payload or {}).get('edited_channel_post'))
    try:
        token_kind = None if is_edited_update else 'EDITUSD' if 'EDITUSD|' in clean else 'EDITREC' if 'EDITREC|' in clean else None
        if token_kind:
            result['consumes_source'] = True
            m = re.search('\\((%s\\|[^)]*)\\)' % re.escape(token_kind), clean)
            if m:
                parts = m.group(1).split('|', 4)
                target_chat_id = int(parts[1])
                rid = int(parts[2])
                value_text = _durable_direct_insert_value(clean, m)
            else:
                tail = clean[clean.find(token_kind + '|'):]
                parts = tail.split('|', 4)
                if len(parts) < 5:
                    return result
                target_chat_id = int(parts[1])
                rid = int(parts[2])
                value_text = _durable_sanitize_inserted_text_no_network(parts[4])
            if value_text:
                if token_kind == 'EDITUSD':
                    usd_amount, usd_note = parse_usd_edit_value(value_text)
                    result['record_edits'].append(_durable_record_edit_witness(target_chat_id, rid, source_finance_text=None, usd_amount=usd_amount, usd_note=usd_note, kind='usd_direct'))
                else:
                    amount, note = split_amount_and_note(value_text)
                    result['record_edits'].append(_durable_record_edit_witness(target_chat_id, rid, amount=amount, note=note, source_finance_text=value_text, kind='direct_edit'))
            return result
    except Exception:
        if 'EDITREC|' in clean or 'EDITUSD|' in clean:
            result['consumes_source'] = True
            return result
    try:
        if 'EDITSECRET|' in clean:
            result['consumes_source'] = True
            m = re.search('\\((EDITSECRET\\|[^)]*)\\)', clean)
            if m:
                parts = m.group(1).split('|', 3)
                target_chat_id = int(parts[1])
                record_id = int(parts[2])
                new_text = _durable_direct_insert_value(clean, m)
                if new_text:
                    result['secret_edits'].append(_durable_secret_edit_witness(target_chat_id, record_id, new_text))
            return result
    except Exception:
        result['consumes_source'] = True
        return result
    try:
        reminder_kind = 'EDITREMINT' if 'EDITREMINT|' in clean else 'EDITREM' if 'EDITREM|' in clean else None
        if reminder_kind:
            result['consumes_source'] = True
            m = re.search('\\((%s\\|(\\d+)\\|)[^)]*\\)' % re.escape(reminder_kind), clean)
            if not m:
                return result
            reminder_id = int(m.group(2))
            value_text = _durable_direct_insert_value(clean, m)
            if reminder_kind == 'EDITREMINT':
                try:
                    minutes = _reminder_parse_custom_interval(value_text) if '_reminder_parse_custom_interval' in globals() else None
                except Exception:
                    minutes = None
                if minutes is not None:
                    result['reminder_edits'].append({'reminder_id': reminder_id, 'kind': 'interval', 'interval_minutes': int(minutes)})
            elif value_text:
                result['reminder_edits'].append({'reminder_id': reminder_id, 'kind': 'text', 'text': str(value_text)})
            return result
    except Exception:
        if 'EDITREM|' in clean or 'EDITREMINT|' in clean:
            result['consumes_source'] = True
            return result
    if 'GOMONKI' in clean.upper():
        result['consumes_source'] = True
        return result
    if clean.startswith('/'):
        return result
    try:
        store = get_chat_store(int(source_chat_id))
        fwd_wait = store.get('forward_copy_edit_wait') or {}
        if fwd_wait.get('type') == 'forward_copy_edit':
            result['consumes_source'] = True
            value_text = _durable_sanitize_inserted_text_no_network(clean)
            comp = parse_financial_components(value_text)
            result['record_edits'].append(_durable_record_edit_witness(int(source_chat_id), int(fwd_wait.get('rid')), amount=comp.get('amount'), note=comp.get('note'), source_finance_text=comp.get('source_finance_text') or value_text, usd_amount=comp.get('usd_amount'), usd_note=comp.get('usd_note') if comp.get('usd_amount') is not None else None, kind='forward_copy_edit'))
            return result
        finwin_wait = store.get('finwin_edit_wait') or {}
        if finwin_wait.get('type') == 'finwin_edit':
            result['consumes_source'] = True
            value_text = _durable_sanitize_inserted_text_no_network(clean)
            amount, note = split_amount_and_note(value_text)
            result['record_edits'].append(_durable_record_edit_witness(int(finwin_wait.get('target_chat_id')), int(finwin_wait.get('rid')), amount=amount, note=note, source_finance_text=value_text, kind='finwin_edit'))
            return result
        secret_full_wait = store.get('secret_full_edit_wait') or {}
        if secret_full_wait.get('type') == 'secret_full_edit':
            result['consumes_source'] = True
            value_text = str(clean or '').strip()
            if value_text:
                result['secret_edits'].append(_durable_secret_edit_witness(int(secret_full_wait.get('target_chat_id')), int(secret_full_wait.get('record_id')), value_text))
            return result
        edit_wait = store.get('edit_wait') or {}
        if edit_wait.get('type') == 'edit':
            result['consumes_source'] = True
            value_text = _durable_sanitize_inserted_text_no_network(clean)
            amount, note = split_amount_and_note(value_text)
            result['record_edits'].append(_durable_record_edit_witness(int(source_chat_id), int(edit_wait.get('rid')), amount=amount, note=note, source_finance_text=value_text, kind='edit_wait'))
            return result
        if bool(store.get('category_add_wait')) or bool(store.get('category_edit_wait')):
            result['consumes_source'] = True
            return result
        text_up = clean.strip().upper()
        if bool(store.get('reset_wait')) and text_up == 'ДА':
            result['consumes_source'] = True
            return result
        if bool(store.get('finwin_reset_wait')) and text_up in {'ДА', 'НЕТ', 'ОТМЕНА', 'CANCEL'}:
            result['consumes_source'] = True
            return result
        if bool(store.get('finance_toggle_wait')) and text_up in {'ДА', 'НЕТ', 'ОТМЕНА', 'CANCEL'}:
            result['consumes_source'] = True
            return result
    except Exception:
        pass
    try:
        is_edited = isinstance(payload.get('edited_message'), dict) or isinstance(payload.get('edited_channel_post'), dict)
        if is_edited:
            rec = find_record_by_message_id(int(source_chat_id), int(source_msg_id))
            if isinstance(rec, dict):
                if clean and looks_like_amount(clean):
                    comp = parse_financial_components(clean)
                    result['record_edits'].append(_durable_record_edit_witness(int(source_chat_id), int(rec.get('id')), amount=comp.get('amount'), note=comp.get('note'), source_finance_text=comp.get('source_finance_text') or clean, usd_amount=comp.get('usd_amount'), usd_note=comp.get('usd_note') if comp.get('usd_amount') is not None else None, kind='native_source_edit'))
                else:
                    result['record_edits'].append(_durable_record_edit_witness(int(source_chat_id), int(rec.get('id')), amount=0.0, note='удалено', source_finance_text=clean, kind='native_source_edit_removed'))
            for dst_chat_id, dst_msg_id in get_forward_links(int(source_chat_id), int(source_msg_id)):
                if not get_forward_finance(int(source_chat_id), int(dst_chat_id)):
                    continue
                dst_rec = find_record_by_message_id(int(dst_chat_id), int(dst_msg_id))
                if not isinstance(dst_rec, dict):
                    continue
                if clean and looks_like_amount(clean):
                    comp = parse_financial_components(clean)
                    result['record_edits'].append(_durable_record_edit_witness(int(dst_chat_id), int(dst_rec.get('id')), amount=comp.get('amount'), note=comp.get('note'), source_finance_text=comp.get('source_finance_text') or clean, usd_amount=comp.get('usd_amount'), usd_note=comp.get('usd_note') if comp.get('usd_amount') is not None else None, kind='propagated_copy_edit'))
                else:
                    result['record_edits'].append(_durable_record_edit_witness(int(dst_chat_id), int(dst_rec.get('id')), amount=0.0, note='удалено', source_finance_text=clean, kind='propagated_copy_edit_removed'))
            for dst_chat_id, dst_msg_id in get_forward_links(int(source_chat_id), int(source_msg_id)):
                try:
                    if not is_total_secret_mode(int(dst_chat_id)):
                        continue
                    result['secret_copy_edits'].append({'chat_id': int(dst_chat_id), 'copied_message_id': int(dst_msg_id), 'source_chat_id': int(source_chat_id), 'source_msg_id': int(source_msg_id), 'text': str(clean)})
                    dst_secret_rec = next((r for r in _secret_records(int(dst_chat_id)) if isinstance(r, dict) and bool(r.get('is_bot_copy')) and (int(r.get('source_msg_id') or 0) == int(dst_msg_id) or (int(r.get('forward_source_chat_id') or 0) == int(source_chat_id) and int(r.get('forward_source_msg_id') or 0) == int(source_msg_id)))), None)
                    if isinstance(dst_secret_rec, dict):
                        result['secret_edits'].append(_durable_secret_edit_witness(int(dst_chat_id), int(dst_secret_rec.get('id')), clean))
                except Exception:
                    pass
            secret_rec = next((r for r in _secret_records(int(source_chat_id)) if int(r.get('source_msg_id') or 0) == int(source_msg_id)), None)
            if isinstance(secret_rec, dict) and clean:
                marked, cleaned_secret = _extract_secret_codeword(clean)
                expected_secret_text = cleaned_secret if marked else clean
                result['secret_edits'].append(_durable_secret_edit_witness(int(source_chat_id), int(secret_rec.get('id')), expected_secret_text))
    except Exception:
        pass
    return result

def _v177_legacy_0066_durable_expected_effects(payload: dict) -> dict:
    """Snapshot the effects that this Telegram update is actually expected to create.

    v109 rule: the witness must never infer a financial effect merely because a message
    contains a digit.  We use the real finance parser predicate (`looks_like_amount`) and
    the destination's finance mode at task-creation time.  This prevents false `running`
    tasks from being replayed and creating duplicate money records.
    """
    out = {'source_finance': False, 'source_secret': False, 'forward_targets': [], 'record_edits': [], 'secret_edits': [], 'secret_copy_edits': [], 'reminder_edits': []}
    raw, source_chat_id, source_msg_id, _group_id = _durable_payload_message(payload)
    if not isinstance(raw, dict) or source_chat_id is None or source_msg_id is None:
        return out
    text = str(raw.get('text') or raw.get('caption') or '').strip()
    edit_expect = _durable_extract_edit_expectations(payload, int(source_chat_id), int(source_msg_id), text)
    out['record_edits'] = list(edit_expect.get('record_edits') or [])
    out['secret_edits'] = list(edit_expect.get('secret_edits') or [])
    out['secret_copy_edits'] = list(edit_expect.get('secret_copy_edits') or [])
    out['reminder_edits'] = list(edit_expect.get('reminder_edits') or [])
    edit_consumes_source = bool(edit_expect.get('consumes_source'))
    if text.startswith('/') and (not text.lower().startswith('/izm_')) and (not edit_consumes_source):
        return out
    is_edited_update = bool((payload or {}).get('edited_message') or (payload or {}).get('edited_channel_post'))
    waiting = bool(edit_consumes_source)
    try:
        store = get_chat_store(int(source_chat_id))
        secret_wait = (store or {}).get('secret_wait') or {}
        if isinstance(secret_wait, dict) and secret_wait.get('type') == 'secret_note_add':
            waiting = True
    except Exception:
        pass
    try:
        marked, _cleaned = _extract_secret_codeword(text)
    except Exception:
        marked = False
    try:
        if is_edited_update:
            existing_secret = any((isinstance(r, dict) and int(r.get('source_msg_id') or 0) == int(source_msg_id) for r in _secret_records(int(source_chat_id))))
            out['source_secret'] = bool(existing_secret or marked)
        else:
            out['source_secret'] = bool(is_total_secret_mode(int(source_chat_id)) or marked)
    except Exception:
        out['source_secret'] = bool(marked)
    try:
        content_type = _durable_raw_content_type(raw)
        finance_handler_types = {'text', 'photo', 'video', 'animation', 'audio', 'voice', 'video_note', 'document', 'sticker', 'location', 'venue', 'contact', 'dice', 'poll', 'game', 'story', 'paid_media', 'invoice'}
        existing_finance_record = True
        if is_edited_update:
            existing_finance_record = find_record_by_message_id(int(source_chat_id), int(source_msg_id)) is not None
        out['source_finance'] = bool(existing_finance_record and content_type in finance_handler_types and (not waiting) and (not edit_consumes_source) and (not out['source_secret']) and is_finance_mode(int(source_chat_id)) and text and looks_like_amount(text))
    except Exception:
        out['source_finance'] = False
    if edit_consumes_source:
        out['source_secret'] = False
        out['forward_targets'] = []
        out['source_consumed_by_edit_route'] = True
        return out
    for dst_chat_id, mode, finance_enabled in _durable_forward_targets(source_chat_id):
        dst = int(dst_chat_id)
        dst_finance = False
        if finance_enabled and text:
            try:
                dst_finance = bool(is_finance_mode(dst) and looks_like_amount(text))
            except Exception:
                dst_finance = False
        dst_secret = False
        try:
            dst_secret = bool(is_total_secret_mode(dst))
        except Exception:
            pass
        out['forward_targets'].append({'dst_chat_id': dst, 'mode': str(mode), 'finance_expected': dst_finance, 'secret_expected': dst_secret})
    return out
try:
    _v177_legacy_0066_durable_expected_effects.__name__ = '_durable_expected_effects'
except Exception:
    pass

def _v177_legacy_0067_durable_normalize_expected_for_route(payload: dict, expected: dict | None) -> dict:
    """Remove impossible witnesses implied by an older durable task schema.

    Older v115/v116 tasks could persist both source_secret=True and source_finance=True
    for a marked secret such as ``5🙊``. The real handler consumes the source message in
    the secret route before ordinary source finance. This only removes that impossible
    source-finance expectation; it never adds money records or sends Telegram content.
    """
    adjusted = _delta_json_clone(expected or {}) if isinstance(expected, dict) else {}
    raw, _source_chat_id, _source_msg_id, _group_id = _durable_payload_message(payload or {})
    text = str((raw or {}).get('text') or (raw or {}).get('caption') or '').strip() if isinstance(raw, dict) else ''
    marked = False
    if text:
        try:
            marked, _cleaned = _extract_secret_codeword(text)
        except Exception:
            marked = False
    secret_route = bool(adjusted.get('source_secret')) or bool(marked)
    if secret_route and bool(adjusted.get('source_finance')):
        adjusted['source_finance'] = False
        adjusted['source_finance_suppressed_by_secret_route'] = True
    try:
        _raw2, _src2, _mid2, _grp2 = _durable_payload_message(payload or {})
        if isinstance(_raw2, dict) and _src2 is not None and (_mid2 is not None):
            edit_meta = _durable_extract_edit_expectations(payload or {}, int(_src2), int(_mid2), str(_raw2.get('text') or _raw2.get('caption') or '').strip())
            if edit_meta.get('consumes_source'):
                adjusted['source_finance'] = False
                adjusted['source_secret'] = False
                adjusted['forward_targets'] = []
                adjusted['source_consumed_by_edit_route'] = True
            witness_keys = {'record_edits': ('chat_id', 'rid', 'kind'), 'secret_edits': ('chat_id', 'record_id'), 'secret_copy_edits': ('chat_id', 'copied_message_id', 'source_chat_id', 'source_msg_id'), 'reminder_edits': ('reminder_id', 'kind')}
            for field, key_fields in witness_keys.items():
                rows = list(adjusted.get(field, []) or [])
                for row in edit_meta.get(field, []) or []:
                    row_key = tuple((str((row or {}).get(key)) for key in key_fields))
                    rows = [old_row for old_row in rows if tuple((str((old_row or {}).get(key)) for key in key_fields)) != row_key]
                    rows.append(_delta_json_clone(row))
                adjusted[field] = rows
    except Exception:
        pass
    if isinstance(raw, dict):
        sender_skip_reason = _forward_sender_skip_reason_raw(raw)
        edited_source = bool(raw.get('edit_date'))
        if sender_skip_reason or edited_source:
            adjusted['forward_targets'] = []
            adjusted['forward_suppressed_by_worker_skip'] = sender_skip_reason or 'edited_source'
    return adjusted
try:
    _v177_legacy_0067_durable_normalize_expected_for_route.__name__ = '_durable_normalize_expected_for_route'
except Exception:
    pass

def _durable_expected_from_task_or_payload(task: dict | None, payload: dict) -> dict:
    try:
        expected = (task or {}).get('expected_effects')
        if isinstance(expected, dict):
            adjusted = _durable_adjust_expected_for_captured_wait(task, payload, _delta_json_clone(expected))
            return _durable_normalize_expected_for_route(payload, adjusted)
    except Exception:
        pass
    return _durable_normalize_expected_for_route(payload, _durable_expected_effects(payload))

def _durable_live_forward_outcome(payload: dict) -> dict:
    raw, source_chat_id, source_msg_id, _group_id = _durable_payload_message(payload or {})
    if not isinstance(raw, dict) or source_chat_id is None or source_msg_id is None:
        return {}
    return _forward_outcome_snapshot(int(source_chat_id), int(source_msg_id))

def _durable_apply_live_forward_outcome(payload: dict, expected: dict | None) -> dict:
    """Use only concrete live worker evidence; never guesses a Telegram delivery.

    skip:* means the worker deliberately did not send. delivered carries the Telegram
    destination message id and can safely rebuild a missing local forward index. Failed or
    pending targets remain expected and therefore cannot be silently lost.
    """
    adjusted = _delta_json_clone(expected or {}) if isinstance(expected, dict) else {}
    raw, source_chat_id, source_msg_id, _group_id = _durable_payload_message(payload or {})
    if not isinstance(raw, dict) or source_chat_id is None or source_msg_id is None:
        return adjusted
    outcome = _forward_outcome_snapshot(int(source_chat_id), int(source_msg_id))
    state = str(outcome.get('state') or '')
    if state.startswith('skip:') or state == 'no_targets':
        adjusted['forward_targets'] = []
        adjusted['forward_suppressed_by_live_outcome'] = state
        return adjusted
    targets = outcome.get('targets') or {}
    terminal = set()
    for dst_raw, info in list(targets.items()):
        try:
            dst = int(dst_raw)
            info = info or {}
            target_state = str(info.get('state') or '')
            if target_state in {'suspended', 'migrated', 'unavailable_terminal'}:
                terminal.add(dst)
                continue
            if target_state != 'delivered':
                continue
            dst_msg_id = int(info.get('dst_msg_id') or 0)
            if not dst_msg_id:
                continue
            current = {int(d): int(m) for d, m in get_forward_links(int(source_chat_id), int(source_msg_id))}
            if int(current.get(dst) or 0) != dst_msg_id:
                _store_forward_link(int(source_chat_id), int(source_msg_id), dst, dst_msg_id)
                try:
                    _persist_forward_index_in_data(data)
                    save_data(data, root_only=True)
                except Exception as e:
                    log_error(f'[FORWARD OUTCOME LINK REPAIR] {source_chat_id}:{source_msg_id}->{dst}:{dst_msg_id}: {e}')
        except Exception as e:
            log_error(f'durable live forward outcome repair: {e}')
    if terminal:
        adjusted['forward_targets'] = [row for row in adjusted.get('forward_targets') or [] if int((row or {}).get('dst_chat_id') or 0) not in terminal]
        adjusted['forward_terminal_targets_v199'] = sorted(terminal)
    return adjusted

def _durable_forward_work_still_pending(payload: dict) -> bool:
    """True only when this live process has positive evidence that forwarding is not finished yet."""
    try:
        raw, source_chat_id, source_msg_id, group_id = _durable_payload_message(payload or {})
        if not isinstance(raw, dict) or source_chat_id is None or source_msg_id is None:
            return False
        if group_id and _durable_media_group_in_memory(payload):
            return True
        outcome = _forward_outcome_snapshot(int(source_chat_id), int(source_msg_id))
        state = str(outcome.get('state') or '')
        if state in {'scheduled', 'dispatching', 'media_group_pending'}:
            return True
        for info in (outcome.get('targets') or {}).values():
            if str((info or {}).get('state') or '') in {'pending', 'attempted'}:
                return True
    except Exception:
        return False
    return False

def _durable_record_matches_witness(rec: dict | None, witness: dict) -> bool:
    if not isinstance(rec, dict):
        return False
    try:
        if 'amount' in witness and abs(float(rec.get('amount', 0) or 0) - float(witness.get('amount', 0) or 0)) > 1e-06:
            return False
        if 'note' in witness and str(rec.get('note') or '').strip() != str(witness.get('note') or '').strip():
            return False
        if 'source_finance_text' in witness and str(rec.get('source_finance_text') or '').strip() != str(witness.get('source_finance_text') or '').strip():
            return False
        if 'usd_amount' in witness and abs(float(rec.get('usd_amount', 0) or 0) - float(witness.get('usd_amount', 0) or 0)) > 1e-06:
            return False
        if 'usd_note' in witness and str(rec.get('usd_note') or '').strip() != str(witness.get('usd_note') or '').strip():
            return False
        return True
    except Exception:
        return False

def _durable_find_record_for_witness(chat_id: int, rid: int, witness: dict):
    """Find an edited row across active + ARS + USD mirrors and require exact new value.

    v123 verified only the currently loaded `records` list.  After currency switching or a
    deploy an already-edited row can live in ars_records/usd_records while the active list is
    another ledger, which caused a false `record_edit ... missing` and a failed durable task.
    """
    store = get_chat_store(int(chat_id))
    candidates = []
    seen = set()
    for key in ('records', 'ars_records', 'usd_records'):
        for rec in list(store.get(key, []) or []):
            if not isinstance(rec, dict):
                continue
            try:
                if int(rec.get('id', -1)) != int(rid):
                    continue
            except Exception:
                continue
            oid = id(rec)
            if oid in seen:
                continue
            seen.add(oid)
            candidates.append(rec)
    for rec in candidates:
        if _durable_record_matches_witness(rec, witness):
            return rec
    return None

def _v177_legacy_0068_durable_effect_report(payload: dict, expected: dict | None=None) -> dict:
    """Return explicit effect status. No repairs, no replay, no side effects."""
    expected = _durable_normalize_expected_for_route(payload, expected if isinstance(expected, dict) else _durable_expected_effects(payload))
    expected = _durable_apply_live_forward_outcome(payload, expected)
    raw, source_chat_id, source_msg_id, _group_id = _durable_payload_message(payload)
    report = {'complete': True, 'missing': [], 'ambiguous': []}
    if not isinstance(raw, dict) or source_chat_id is None or source_msg_id is None:
        return report
    links = {}
    try:
        links = {int(dst): int(mid) for dst, mid in get_forward_links(source_chat_id, source_msg_id)}
    except Exception:
        links = {}
    for target in expected.get('forward_targets', []) or []:
        try:
            dst = int(target.get('dst_chat_id'))
        except Exception:
            continue
        dst_msg_id = links.get(dst)
        if not dst_msg_id:
            report['complete'] = False
            report['ambiguous'].append(f'forward:{source_chat_id}:{source_msg_id}->{dst}')
            continue
        if bool(target.get('finance_expected')):
            try:
                rec = find_record_by_message_id(dst, dst_msg_id)
            except Exception:
                rec = None
            if not isinstance(rec, dict):
                report['complete'] = False
                report['missing'].append(f'forward_finance:{dst}:{dst_msg_id}')
        if bool(target.get('secret_expected')):
            try:
                ok = any((isinstance(r, dict) and int(r.get('source_msg_id') or 0) == int(dst_msg_id) and (int(r.get('forward_source_msg_id') or source_msg_id) == int(source_msg_id)) for r in _secret_records(dst)))
            except Exception:
                ok = False
            if not ok:
                report['complete'] = False
                report['missing'].append(f'forward_secret:{dst}:{dst_msg_id}')
    if bool(expected.get('source_finance')):
        try:
            ok = find_record_by_message_id(int(source_chat_id), int(source_msg_id)) is not None
        except Exception:
            ok = False
        if not ok:
            report['complete'] = False
            report['missing'].append(f'source_finance:{source_chat_id}:{source_msg_id}')
    if bool(expected.get('source_secret')):
        try:
            ok = any((int(r.get('source_msg_id') or 0) == int(source_msg_id) for r in _secret_records(source_chat_id) if isinstance(r, dict)))
        except Exception:
            ok = False
        if not ok:
            report['complete'] = False
            report['missing'].append(f'source_secret:{source_chat_id}:{source_msg_id}')
    for witness in expected.get('record_edits', []) or []:
        try:
            w_chat = int(witness.get('chat_id'))
            w_rid = int(witness.get('rid'))
            rec = _durable_find_record_for_witness(w_chat, w_rid, witness)
            if not isinstance(rec, dict):
                report['complete'] = False
                report['missing'].append(f"record_edit:{w_chat}:R{w_rid}:{witness.get('kind', 'edit')}")
        except Exception:
            report['complete'] = False
            report['missing'].append(f'record_edit:invalid:{witness}')
    for witness in expected.get('secret_edits', []) or []:
        try:
            w_chat = int(witness.get('chat_id'))
            record_id = int(witness.get('record_id'))
            rec = next((r for r in _secret_records(w_chat) if int(r.get('id') or 0) == record_id), None)
            ok = isinstance(rec, dict) and str(rec.get('text') or '').strip() == str(witness.get('text') or '').strip()
            if not ok:
                report['complete'] = False
                report['missing'].append(f'secret_edit:{w_chat}:{record_id}')
        except Exception:
            report['complete'] = False
            report['missing'].append(f'secret_edit:invalid:{witness}')
    for witness in expected.get('secret_copy_edits', []) or []:
        try:
            w_chat = int(witness.get('chat_id'))
            copied_mid = int(witness.get('copied_message_id'))
            src_chat = int(witness.get('source_chat_id'))
            src_mid = int(witness.get('source_msg_id'))
            expected_text = str(witness.get('text') or '').strip()
            rec = next((r for r in _secret_records(w_chat) if isinstance(r, dict) and bool(r.get('is_bot_copy')) and (int(r.get('source_msg_id') or 0) == copied_mid or (int(r.get('forward_source_chat_id') or 0) == src_chat and int(r.get('forward_source_msg_id') or 0) == src_mid))), None)
            ok = isinstance(rec, dict) and str(rec.get('text') or '').strip() == expected_text
            if not ok:
                report['complete'] = False
                report['missing'].append(f'secret_copy_edit:{w_chat}:{copied_mid}')
        except Exception:
            report['complete'] = False
            report['missing'].append(f'secret_copy_edit:invalid:{witness}')
    for witness in expected.get('reminder_edits', []) or []:
        try:
            reminder_id = int(witness.get('reminder_id'))
            cfg = _reminder_cfg(reminder_id) if '_reminder_cfg' in globals() else None
            ok = isinstance(cfg, dict)
            if ok and str(witness.get('kind') or '') == 'text':
                ok = str(cfg.get('text') or '').strip() == str(witness.get('text') or '').strip()
            elif ok and str(witness.get('kind') or '') == 'interval':
                ok = int(cfg.get('interval_minutes') or 0) == int(witness.get('interval_minutes') or 0)
            if not ok:
                ok = _durable_reminder_receipt_exists(payload, witness)
            if not ok:
                report['complete'] = False
                report['missing'].append(f"reminder_edit:{reminder_id}:{witness.get('kind', 'value')}")
        except Exception:
            report['complete'] = False
            report['missing'].append(f'reminder_edit:invalid:{witness}')
    return report
try:
    _v177_legacy_0068_durable_effect_report.__name__ = '_durable_effect_report'
except Exception:
    pass

def _durable_forward_effect_complete(payload: dict, expected: dict | None=None) -> bool:
    """Verify only forwarding effects explicitly expected for this task."""
    expected = expected if isinstance(expected, dict) else _durable_expected_effects(payload)
    report = _durable_effect_report(payload, expected)
    for item in (report.get('missing') or []) + (report.get('ambiguous') or []):
        if str(item).startswith('forward'):
            return False
    return True

def _durable_secret_effect_complete(payload: dict) -> bool:
    raw, source_chat_id, source_msg_id, _group_id = _durable_payload_message(payload)
    if not isinstance(raw, dict) or source_chat_id is None or source_msg_id is None:
        return True
    text = str(raw.get('text') or raw.get('caption') or '')
    secret_expected = False
    try:
        secret_expected = bool(is_total_secret_mode(source_chat_id))
    except Exception:
        pass
    if not secret_expected:
        try:
            marked, _cleaned = _extract_secret_codeword(text)
            secret_expected = bool(marked)
        except Exception:
            secret_expected = False
    if not secret_expected:
        return True
    try:
        return any((int(r.get('source_msg_id') or 0) == int(source_msg_id) for r in _secret_records(source_chat_id) if isinstance(r, dict)))
    except Exception:
        return False

def _durable_direct_finance_effect_complete(payload: dict, expected: dict | None=None) -> bool:
    expected = expected if isinstance(expected, dict) else _durable_expected_effects(payload)
    if not bool(expected.get('source_finance')):
        return True
    _raw, source_chat_id, source_msg_id, _group_id = _durable_payload_message(payload)
    if source_chat_id is None or source_msg_id is None:
        return True
    try:
        return find_record_by_message_id(source_chat_id, source_msg_id) is not None
    except Exception:
        return False

def _durable_media_group_in_memory(payload: dict) -> bool:
    _raw, source_chat_id, _source_msg_id, group_id = _durable_payload_message(payload)
    if source_chat_id is None or not group_id:
        return False
    key = (int(source_chat_id), str(group_id))
    try:
        if key in _media_group_cache or key in _media_group_timers:
            return True
    except Exception:
        pass
    return False

def _durable_payload_to_message(payload: dict):
    """Recreate the Telegram Message object from the persisted raw update."""
    try:
        update = telebot.types.Update.de_json(payload)
        for attr in ('message', 'edited_message', 'channel_post', 'edited_channel_post'):
            msg = getattr(update, attr, None)
            if msg is not None:
                return msg
    except Exception as e:
        log_error(f'DURABLE payload->message: {e}')
    return None

def _repair_missing_durable_forward(payload: dict) -> bool:
    """Best-effort repair of missing forwarding directions without duplicating delivered ones.

    Albums are normally sent together by the 0.8s collector. If that collector vanished because
    Render deployed, each persisted album part can be resent individually to only the missing
    destinations. The important invariant is no lost message; already-linked destinations are skipped.
    """
    raw, source_chat_id, source_msg_id, group_id = _durable_payload_message(payload)
    if not isinstance(raw, dict) or source_chat_id is None or source_msg_id is None:
        return True
    targets = _durable_forward_targets(source_chat_id)
    if not targets:
        return True
    if group_id and _durable_media_group_in_memory(payload):
        return False
    links = {}
    try:
        links = {int(dst): int(mid) for dst, mid in get_forward_links(source_chat_id, source_msg_id)}
    except Exception:
        links = {}
    missing = [(int(dst), mode, bool(fin)) for dst, mode, fin in targets if int(dst) not in links]
    if not missing:
        return True
    msg = _durable_payload_to_message(payload)
    if msg is None:
        return False
    all_ok = True
    for dst_chat_id, _mode, finance_enabled in missing:
        try:
            result = _forward_single_to_target(source_chat_id, msg, dst_chat_id, finance_enabled)
            if not result:
                all_ok = False
        except Exception as e:
            all_ok = False
            log_error(f'DURABLE FORWARD REPAIR {source_chat_id}:{source_msg_id}->{dst_chat_id}: {e}')
    return bool(all_ok and _durable_forward_effect_complete(payload))

def _v177_legacy_0069_wait_durable_subtasks(chat_id, timeout: float=20.0, wait_forward: bool=True, payload: dict | None=None, expected: dict | None=None, update_id=None) -> bool:
    """Wait for this exact source message, never for an entire chat queue.

    Consecutive finance messages may share the same source chat key. Waiting for key-idle
    incorrectly included later messages and produced false 20-second failures. v143 polls the
    source_chat_id:source_message_id outcome and concrete delivery witnesses only.
    """
    if chat_id is None or not wait_forward:
        return True
    if not isinstance(payload, dict):
        return True
    raw, source_chat_id, source_msg_id, group_id = _durable_payload_message(payload)
    if not isinstance(raw, dict) or source_chat_id is None or source_msg_id is None:
        return True
    deadline = time.monotonic() + max(0.5, float(timeout))
    started = time.monotonic()
    last_state = ''
    last_targets = {}
    try:
        bot_journal('durable_forward_wait_start', chat_id, f"update={update_id} source={source_chat_id}:{source_msg_id} group={group_id or '-'} timeout={timeout}")
    except Exception:
        pass
    while True:
        outcome = _forward_outcome_snapshot(int(source_chat_id), int(source_msg_id))
        last_state = str(outcome.get('state') or '')
        last_targets = outcome.get('targets') or {}
        try:
            report = _durable_effect_report(payload, expected if isinstance(expected, dict) else None)
            if bool(report.get('complete')):
                try:
                    bot_journal('durable_forward_wait_done', chat_id, f"update={update_id} source={source_chat_id}:{source_msg_id} state={last_state or '-'} elapsed={time.monotonic() - started:.3f}s complete=1")
                except Exception:
                    pass
                return True
        except Exception:
            report = {'complete': False}
        pending = _durable_forward_work_still_pending(payload)
        final_state = last_state.startswith('skip:') or last_state in {'completed', 'failed', 'no_targets'}
        if final_state and (not pending):
            try:
                bot_journal('durable_forward_wait_done', chat_id, f'update={update_id} source={source_chat_id}:{source_msg_id} state={last_state} elapsed={time.monotonic() - started:.3f}s complete=0 verify_next=1')
            except Exception:
                pass
            return True
        if time.monotonic() >= deadline:
            qf = FIN_FORWARD_TASK_POOL.stats()
            qn = FORWARD_TASK_POOL.stats()
            target_state = {str(k): str((v or {}).get('state') or '') for k, v in list(last_targets.items())[:20]}
            log_error(f"DURABLE EXACT FORWARD TIMEOUT update={update_id} source={source_chat_id}:{source_msg_id} state={last_state or '-'} targets={target_state} finQ={qf.get('pending')}/{qf.get('active')} fwdQ={qn.get('pending')}/{qn.get('active')}")
            return False
        time.sleep(0.05)
try:
    _v177_legacy_0069_wait_durable_subtasks.__name__ = 'wait_durable_subtasks'
except Exception:
    pass

def _v230_constitution_finance_wait(payload: dict | None, expected_effects: dict | None=None) -> bool:
    """True only when a direct expected finance effect is intentionally blocked by constitution quarantine."""
    if not isinstance(payload, dict):
        return False
    try:
        if not (globals().get('constitution_finance_write_blocked_v232') and constitution_finance_write_blocked_v232()):
            return False
    except Exception:
        return False
    expected = _durable_normalize_expected_for_route(payload, expected_effects if isinstance(expected_effects, dict) else _durable_expected_effects(payload))
    if not bool(expected.get('source_finance')):
        return False
    try:
        report = _durable_effect_report(payload, expected)
        missing = [str(x) for x in report.get('missing') or []]
        ambiguous = [str(x) for x in report.get('ambiguous') or []]
        return not ambiguous and any((x.startswith('source_finance:') for x in missing))
    except Exception:
        return False

def _v230_try_repair_direct_finance_after_quarantine(payload: dict | None, expected_effects: dict | None=None) -> bool:
    """Replay only idempotent finance witness after quarantine is cleared; never sends Telegram copies."""
    if not isinstance(payload, dict):
        return False
    try:
        if globals().get('constitution_finance_write_blocked_v232') and constitution_finance_write_blocked_v232():
            return False
    except Exception:
        return False
    expected = _durable_normalize_expected_for_route(payload, expected_effects if isinstance(expected_effects, dict) else _durable_expected_effects(payload))
    if not bool(expected.get('source_finance')):
        return False
    try:
        report = _durable_effect_report(payload, expected)
        missing = [str(x) for x in report.get('missing') or []]
        ambiguous = [str(x) for x in report.get('ambiguous') or []]
        if ambiguous or not any((x.startswith('source_finance:') for x in missing)):
            return False
        return bool(_repair_safe_missing_finance_effects(payload, expected))
    except Exception as exc:
        try:
            log_error(f'v230 direct finance recovery: {exc}')
        except Exception:
            pass
        return False

def finalize_durable_task_after_business(update_id, chat_id, update_type: str='other', payload: dict | None=None, expected_effects: dict | None=None) -> bool:
    """Commit a task only after its explicitly-declared effects are visible.

    v109 is verification-only here. It never replays the business handler and never sends
    a missing Telegram copy from the finalizer. Missing/ambiguous effects stay recoverable
    without producing duplicate finance records or duplicate forwarded messages.
    """
    key = _mega_task_id(update_id)
    callback_target = _durable_callback_target_chat(payload) if isinstance(payload, dict) else None
    expected = _durable_normalize_expected_for_route(payload or {}, expected_effects if isinstance(expected_effects, dict) else _durable_expected_effects(payload) if isinstance(payload, dict) else {})
    ledger_tokens = expected.get('_constitution_ledger_tokens_v190') or []
    if ledger_tokens:
        ready_fn = globals().get('constitution_ledger_tokens_ready')
        if callable(ready_fn):
            ready, detail = ready_fn(ledger_tokens)
            if not ready:
                try:
                    bot_journal('durable_wait_constitution_ledger_v190', chat_id, f'update={key}; {detail}')
                except Exception:
                    pass
                return False
    wait_forward = bool(expected.get('forward_targets')) or any((str((row or {}).get('kind') or '').startswith('propagated_copy_edit') for row in expected.get('record_edits') or []))
    if isinstance(payload, dict) and callback_target is None:
        wait_forward = bool(wait_forward or _durable_forward_work_still_pending(payload))
    if not wait_durable_subtasks(chat_id, timeout=20.0, wait_forward=wait_forward, payload=payload, expected=expected, update_id=key):
        return False
    if isinstance(payload, dict) and callback_target is None:
        expected = _durable_apply_live_forward_outcome(payload, expected)
        if _durable_forward_work_still_pending(payload):
            bot_journal('durable_forward_pending', chat_id, f'update_id={key}; live asynchronous forward still active')
            return False
        try:
            _repair_safe_missing_forward_secret_effects(payload, expected)
        except Exception as _sec_repair_exc:
            log_error(f'DURABLE SECRET REPAIR CHECK update={key}: {_sec_repair_exc}')
        report = _durable_effect_report(payload, expected)
        if not bool(report.get('complete')):
            if _v230_try_repair_direct_finance_after_quarantine(payload, expected):
                report = _durable_effect_report(payload, expected)
            if not bool(report.get('complete')):
                bot_journal('durable_effects_pending', chat_id, f"update_id={key} missing={report.get('missing')} ambiguous={report.get('ambiguous')}")
                return False
    try:
        mark_durable_update_processed(key, chat_id, update_type)
    except Exception as e:
        log_error(f'DURABLE MARKER FAILED update={key}: {e}')
        return False
    try:
        critical_chats = set()
        if chat_id is None:
            if OWNER_ID:
                critical_chats.add(int(OWNER_ID))
        else:
            critical_chats.add(int(chat_id))
        if callback_target is not None:
            critical_chats.add(int(callback_target))
        for target in expected.get('forward_targets', []) or []:
            try:
                critical_chats.add(int(target.get('dst_chat_id')))
            except Exception:
                pass
        if not critical_chats:
            log_error(f'DURABLE CRITICAL DELTA FAILED update={key}: no chat scope')
            return False
        for cid in sorted(critical_chats):
            if not persist_critical_delta_now(cid):
                log_error(f'DURABLE CRITICAL DELTA FAILED update={key} chat={cid}')
                return False
    except Exception as e:
        log_error(f'DURABLE CRITICAL DELTA ERROR update={key}: {e}')
        return False
    return mega_task_finish(key, True)

def schedule_durable_task_finalize_retry(update_id, chat_id, update_type: str='other', delay: float=5.0, payload: dict | None=None, expected_effects: dict | None=None):
    """Short verification-only retry. Never repeats business effects."""
    key = _mega_task_id(update_id)
    payload_copy = _delta_json_clone(payload or {}) if isinstance(payload, dict) else None
    expected_copy = _delta_json_clone(expected_effects or {}) if isinstance(expected_effects, dict) else None
    attempts = {'n': 0, 'started': time.monotonic()}

    def _job():
        if mega_task_known_state(key) == 'done':
            return
        if payload_copy and _v230_constitution_finance_wait(payload_copy, expected_copy):
            try:
                bot_journal('durable_finance_wait_constitution_v230', chat_id, f'update={key}; recoverable=1', 'WARN')
            except Exception:
                pass
            DELAYED_SCHEDULER.schedule(f'mega-task-finalize:{key}', 15.0, _job)
            return
        live_pending = bool(payload_copy and _durable_forward_work_still_pending(payload_copy))
        pending_age = time.monotonic() - attempts['started']
        if not live_pending or pending_age >= 30.0:
            attempts['n'] += 1
        if finalize_durable_task_after_business(key, chat_id, update_type, payload=payload_copy, expected_effects=expected_copy):
            return
        if live_pending and pending_age < 30.0:
            DELAYED_SCHEDULER.schedule(f'mega-task-finalize:{key}', 1.0, _job)
            return
        if attempts['n'] >= 6:
            report = _durable_effect_report(payload_copy or {}, expected_copy or {}) if payload_copy else {}
            reason = f"needs_review: durable effects not proven; missing={report.get('missing', [])}; ambiguous={report.get('ambiguous', [])}"
            mega_task_finish(key, False, reason)
            try:
                bot_journal('durable_needs_review_silent', chat_id, f'update={key}; {reason[:700]}', 'WARN')
            except Exception:
                pass
            return
        DELAYED_SCHEDULER.schedule(f'mega-task-finalize:{key}', 3.0 if payload_copy else 5.0, _job)
    DELAYED_SCHEDULER.cancel(f'mega-task-finalize:{key}')
    DELAYED_SCHEDULER.schedule(f'mega-task-finalize:{key}', max(0.5, float(delay)), _job)

def enqueue_durable_finalize_background(update_id, chat_id, update_type: str, payload: dict, expected_effects: dict) -> bool:
    """Move slow durable witness verification out of the content/UI worker.

    Business effects have already run exactly once and the MEGA task is in ``running``.
    This job only waits for finance/forward/delta witnesses, marks the update processed,
    and moves the task to done. It never replays Telegram sends or finance mutations.
    """
    key = _mega_task_id(update_id)
    payload_copy = _delta_json_clone(payload or {})
    expected_copy = _delta_json_clone(expected_effects or {})

    def _job():
        started = time.monotonic()
        try:
            finalized = finalize_durable_task_after_business(key, chat_id, update_type, payload=payload_copy, expected_effects=expected_copy)
            if not finalized:
                schedule_durable_task_finalize_retry(key, chat_id, update_type, 1.0, payload=payload_copy, expected_effects=expected_copy)
                bot_journal('durable_finalize_background_pending', chat_id, f'update_id={key} elapsed={time.monotonic() - started:.3f}s')
            else:
                bot_journal('durable_finalize_background_done', chat_id, f'update_id={key} elapsed={time.monotonic() - started:.3f}s')
        except Exception as exc:
            log_error(f'DURABLE BACKGROUND FINALIZE update={key}: {exc}')
            schedule_durable_task_finalize_retry(key, chat_id, update_type, 1.0, payload=payload_copy, expected_effects=expected_copy)
        finally:
            try:
                DELAYED_SCHEDULER.schedule(f'lowram-after-durable:{key}', 15.0, _lowram_release_chat, chat_id)
            except Exception:
                pass
    return RECOVERY_TASK_POOL.submit(f'durable-finalize:{key}', _job)
_TELEGRAM_UPDATE_CONTEXT = threading.local()

def _current_telegram_update_context() -> dict:
    try:
        return dict(getattr(_TELEGRAM_UPDATE_CONTEXT, 'value', {}) or {})
    except Exception:
        return {}

def _durable_target_specs_for_source(source_chat_id: int) -> list[dict]:
    """Resolve the concrete forwarding targets at the moment the handler decides to forward."""
    specs = []
    for dst_chat_id, mode, finance_enabled in _durable_forward_targets(source_chat_id):
        dst = int(dst_chat_id)
        dst_secret = False
        try:
            dst_secret = bool(is_total_secret_mode(dst))
        except Exception:
            pass
        specs.append({'dst_chat_id': dst, 'mode': str(mode), 'finance_enabled': bool(finance_enabled), 'secret_expected': dst_secret})
    return specs

def _durable_note_forward_decision(source_chat_id: int, direct: bool=False):
    """Record the ACTUAL handler decision, not the potential configuration.

    This stays in the current update thread only.  The finalizer uses it after the handler
    returns, so a text consumed by SECRET/edit/category/wait state is not falsely marked
    as three missing forwards merely because forwarding is configured for the chat.
    """
    try:
        ctx = getattr(_TELEGRAM_UPDATE_CONTEXT, 'value', None)
        if not isinstance(ctx, dict):
            return
        if ctx.get('chat_id') is not None and int(ctx.get('chat_id')) != int(source_chat_id):
            return
        ctx['forward_decision_reached'] = True
        ctx['forward_direct'] = bool(direct)
        ctx['actual_forward_targets'] = _durable_target_specs_for_source(int(source_chat_id))
    except Exception as e:
        try:
            log_error(f'durable forward decision note {source_chat_id}: {e}')
        except Exception:
            pass

def _durable_note_forward_target_migration(source_chat_id: int, old_chat_id: int, new_chat_id: int):
    """Keep the live durable witness aligned with Telegram basic-group -> supergroup migration.

    The forwarding worker may discover the new destination only after the handler has already
    captured its original target list. Without this rewrite the finalizer keeps waiting for the
    obsolete chat_id and can move a successfully delivered task to MEGA/failed.
    """
    try:
        ctx = getattr(_TELEGRAM_UPDATE_CONTEXT, 'value', None)
        if not isinstance(ctx, dict):
            return False
        if ctx.get('chat_id') is not None and int(ctx.get('chat_id')) != int(source_chat_id):
            return False
        changed = False
        specs = ctx.get('actual_forward_targets') or []
        for spec in specs:
            if not isinstance(spec, dict):
                continue
            try:
                if int(spec.get('dst_chat_id')) != int(old_chat_id):
                    continue
            except Exception:
                continue
            spec['dst_chat_id'] = int(new_chat_id)
            try:
                spec['secret_expected'] = bool(is_total_secret_mode(int(new_chat_id)))
            except Exception:
                pass
            changed = True
        if changed:
            try:
                bot_journal('durable_forward_target_migrated', int(source_chat_id), f'{int(old_chat_id)}->{int(new_chat_id)}')
            except Exception:
                pass
        return changed
    except Exception as e:
        try:
            log_error(f'durable forward target migration {old_chat_id}->{new_chat_id}: {e}')
        except Exception:
            pass
        return False

def _durable_note_record_edit_witness(witness: dict):
    try:
        ctx = getattr(_TELEGRAM_UPDATE_CONTEXT, 'value', None)
        if not isinstance(ctx, dict) or not isinstance(witness, dict):
            return
        rows = ctx.setdefault('record_edits', [])
        key = (int(witness.get('chat_id')), int(witness.get('rid')), str(witness.get('kind') or 'edit'))
        rows[:] = [r for r in rows if (int(r.get('chat_id')), int(r.get('rid')), str(r.get('kind') or 'edit')) != key]
        rows.append(_delta_json_clone(witness))
    except Exception:
        pass

def _durable_note_secret_edit_witness(witness: dict):
    try:
        ctx = getattr(_TELEGRAM_UPDATE_CONTEXT, 'value', None)
        if not isinstance(ctx, dict) or not isinstance(witness, dict):
            return
        rows = ctx.setdefault('secret_edits', [])
        key = (int(witness.get('chat_id')), int(witness.get('record_id')))
        rows[:] = [r for r in rows if (int(r.get('chat_id')), int(r.get('record_id'))) != key]
        rows.append(_delta_json_clone(witness))
    except Exception:
        pass

def _durable_reminder_witness_hash(witness: dict) -> str:
    payload = {'reminder_id': int((witness or {}).get('reminder_id') or 0), 'kind': str((witness or {}).get('kind') or ''), 'text': str((witness or {}).get('text') or '').strip(), 'interval_minutes': int((witness or {}).get('interval_minutes') or 0)}
    return hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True).encode('utf-8')).hexdigest()[:24]

def _durable_reminder_receipt_exists(payload: dict, witness: dict) -> bool:
    try:
        update_id = str((payload or {}).get('update_id'))
        reminder_id = int((witness or {}).get('reminder_id'))
        kind = str((witness or {}).get('kind') or '')
        witness_hash = _durable_reminder_witness_hash(witness)
        for row in list((data or {}).get('_durable_reminder_edit_receipts', []) or []):
            if str((row or {}).get('update_id')) == update_id and int((row or {}).get('reminder_id') or 0) == reminder_id and (str((row or {}).get('kind') or '') == kind) and (str((row or {}).get('witness_hash') or '') == witness_hash):
                return True
    except Exception:
        pass
    return False

def _durable_note_reminder_edit_witness(witness: dict):
    try:
        ctx = getattr(_TELEGRAM_UPDATE_CONTEXT, 'value', None)
        if not isinstance(ctx, dict) or not isinstance(witness, dict):
            return
        rows = ctx.setdefault('reminder_edits', [])
        key = (int(witness.get('reminder_id')), str(witness.get('kind') or ''))
        rows[:] = [r for r in rows if (int(r.get('reminder_id')), str(r.get('kind') or '')) != key]
        exact = _delta_json_clone(witness)
        rows.append(exact)
        update_id = ctx.get('update_id')
        if update_id is not None:
            receipts = data.setdefault('_durable_reminder_edit_receipts', [])
            receipt = {'update_id': str(update_id), 'reminder_id': int(witness.get('reminder_id')), 'kind': str(witness.get('kind') or ''), 'witness_hash': _durable_reminder_witness_hash(witness), 'at': now_local().isoformat(timespec='seconds')}
            receipts[:] = [row for row in receipts if not (str((row or {}).get('update_id')) == receipt['update_id'] and int((row or {}).get('reminder_id') or 0) == receipt['reminder_id'] and (str((row or {}).get('kind') or '') == receipt['kind']))]
            receipts.append(receipt)
            if len(receipts) > 300:
                del receipts[:-300]
    except Exception:
        pass

def _durable_note_source_consumed(reason: str):
    """Tell the durable finalizer that the handler consumed this source before finance/forward routes."""
    try:
        ctx = getattr(_TELEGRAM_UPDATE_CONTEXT, 'value', None)
        if not isinstance(ctx, dict):
            return
        ctx['source_consumed_reason'] = str(reason or 'handler_consumed')
    except Exception:
        pass

def _durable_execution_context_snapshot() -> dict:
    try:
        ctx = getattr(_TELEGRAM_UPDATE_CONTEXT, 'value', None)
        if not isinstance(ctx, dict):
            return {}
        return {'forward_decision_reached': bool(ctx.get('forward_decision_reached')), 'forward_direct': bool(ctx.get('forward_direct')), 'actual_forward_targets': _delta_json_clone(ctx.get('actual_forward_targets') or []), 'source_consumed_reason': str(ctx.get('source_consumed_reason') or ''), 'record_edits': _delta_json_clone(ctx.get('record_edits') or []), 'secret_edits': _delta_json_clone(ctx.get('secret_edits') or []), 'reminder_edits': _delta_json_clone(ctx.get('reminder_edits') or []), 'constitution_ledger_tokens': _delta_json_clone(ctx.get('constitution_ledger_tokens') or [])}
    except Exception:
        return {}

def _durable_expected_after_execution(base_expected: dict | None, execution_ctx: dict | None, payload: dict | None=None) -> dict:
    """Turn potential receipt-time effects into the effects the completed handler actually chose.

    Finance/secret expectations remain as declared.  Forwarding is special: configuration
    only means a message *could* be forwarded.  A handler may legally consume it first.
    After a successful handler return, lack of a forward decision means no forward was intended.
    """
    expected = _delta_json_clone(base_expected or {}) if isinstance(base_expected, dict) else {}
    execution_ctx = execution_ctx if isinstance(execution_ctx, dict) else {}
    actual_specs = execution_ctx.get('actual_forward_targets') if execution_ctx.get('forward_decision_reached') else []
    ledger_tokens = [str(x) for x in execution_ctx.get('constitution_ledger_tokens') or [] if str(x or '').strip()]
    if ledger_tokens:
        expected['_constitution_ledger_tokens_v190'] = ledger_tokens
    rebuilt = []
    text = ''
    try:
        raw, _src, _mid, _group = _durable_payload_message(payload or {})
        text = str((raw or {}).get('text') or (raw or {}).get('caption') or '').strip()
    except Exception:
        text = ''
    for spec in actual_specs or []:
        try:
            dst = int(spec.get('dst_chat_id'))
        except Exception:
            continue
        fin_expected = False
        if bool(spec.get('finance_enabled')) and text:
            try:
                fin_expected = bool(is_finance_mode(dst) and looks_like_amount(text))
            except Exception:
                fin_expected = False
        rebuilt.append({'dst_chat_id': dst, 'mode': str(spec.get('mode') or ''), 'finance_expected': fin_expected, 'secret_expected': bool(spec.get('secret_expected'))})
    expected['forward_targets'] = rebuilt
    expected['forward_decision_actual'] = bool(execution_ctx.get('forward_decision_reached'))
    for field, key_fields in (('record_edits', ('chat_id', 'rid', 'kind')), ('secret_edits', ('chat_id', 'record_id')), ('reminder_edits', ('reminder_id', 'kind'))):
        merged = list(expected.get(field, []) or [])
        for row in execution_ctx.get(field, []) or []:
            try:
                row_key = tuple((str(row.get(k)) for k in key_fields))
                merged = [old for old in merged if tuple((str(old.get(k)) for k in key_fields)) != row_key]
                merged.append(_delta_json_clone(row))
            except Exception:
                pass
        expected[field] = merged
    consumed_reason = str(execution_ctx.get('source_consumed_reason') or '').strip()
    if consumed_reason:
        expected['source_finance'] = False
        expected['source_secret'] = False
        expected['forward_targets'] = []
        expected['source_consumed_reason'] = consumed_reason
    return _durable_normalize_expected_for_route(payload or {}, expected)

def _durable_adjust_expected_for_captured_wait(task: dict | None, payload: dict, expected: dict) -> dict:
    """Reduce false restart-time ambiguity for waits that deterministically consume text.

    This uses the wait-state snapshot already stored in the durable task.  It never adds
    effects; it only suppresses forwarding where the captured handler state proves the text
    belonged to a dedicated input flow.
    """
    if not isinstance(task, dict) or not isinstance(expected, dict):
        return expected
    try:
        raw, _src, _mid, _group = _durable_payload_message(payload)
        if not isinstance(raw, dict) or not raw.get('text') is not None:
            return expected
        waits = (task.get('context') or {}).get('wait_states') or {}
        if not isinstance(waits, dict) or not waits:
            return expected
        deterministic = {'secret_wait', 'category_add_wait', 'category_edit_wait', 'edit_wait', 'finwin_edit_wait', 'forward_copy_edit_wait', 'secret_full_edit_wait'}
        if any((k in waits and waits.get(k) for k in deterministic)):
            adjusted = _delta_json_clone(expected)
            adjusted['forward_targets'] = []
            adjusted['source_finance'] = False
            adjusted['source_finance_suppressed_by_captured_wait'] = True
            adjusted['forward_suppressed_by_captured_wait'] = True
            try:
                _raw2, _src2, _mid2, _grp2 = _durable_payload_message(payload or {})
                value_text = _durable_sanitize_inserted_text_no_network(str((_raw2 or {}).get('text') or '').strip())
                witness = None
                fw = waits.get('forward_copy_edit_wait') or {}
                if isinstance(fw, dict) and fw.get('type') == 'forward_copy_edit' and value_text:
                    comp = parse_financial_components(value_text)
                    witness = _durable_record_edit_witness(int(_src2), int(fw.get('rid')), amount=comp.get('amount'), note=comp.get('note'), source_finance_text=comp.get('source_finance_text') or value_text, usd_amount=comp.get('usd_amount'), usd_note=comp.get('usd_note') if comp.get('usd_amount') is not None else None, kind='forward_copy_edit')
                fin = waits.get('finwin_edit_wait') or {}
                if witness is None and isinstance(fin, dict) and (fin.get('type') == 'finwin_edit') and value_text:
                    amount, note = split_amount_and_note(value_text)
                    witness = _durable_record_edit_witness(int(fin.get('target_chat_id')), int(fin.get('rid')), amount=amount, note=note, source_finance_text=value_text, kind='finwin_edit')
                ew = waits.get('edit_wait') or {}
                if witness is None and isinstance(ew, dict) and (ew.get('type') == 'edit') and value_text:
                    amount, note = split_amount_and_note(value_text)
                    witness = _durable_record_edit_witness(int(_src2), int(ew.get('rid')), amount=amount, note=note, source_finance_text=value_text, kind='edit_wait')
                if witness is not None:
                    rows = list(adjusted.get('record_edits', []) or [])
                    if witness not in rows:
                        rows.append(witness)
                    adjusted['record_edits'] = rows
            except Exception:
                pass
            return adjusted
        text_up = str(raw.get('text') or '').strip().upper()
        if waits.get('finwin_reset_wait') and text_up in {'ДА', 'НЕТ', 'ОТМЕНА', 'CANCEL'}:
            adjusted = _delta_json_clone(expected)
            adjusted['forward_targets'] = []
            return adjusted
        if waits.get('finance_toggle_wait') and text_up in {'ДА', 'НЕТ', 'ОТМЕНА', 'CANCEL'}:
            adjusted = _delta_json_clone(expected)
            adjusted['forward_targets'] = []
            return adjusted
        if waits.get('reset_wait') and text_up == 'ДА':
            adjusted = _delta_json_clone(expected)
            adjusted['forward_targets'] = []
            return adjusted
    except Exception:
        pass
    return expected

def _durable_callback_target_chat(payload: dict) -> int | None:
    """Only rare state-changing finance-window callbacks get cloud-task latency.

    Navigation callbacks stay fast. These toggles are protected because replaying a toggle twice
    after deploy could otherwise reverse the user's choice.
    """
    try:
        cb = payload.get('callback_query') if isinstance(payload, dict) else None
        if not isinstance(cb, dict):
            return None
        data_str = str(cb.get('data') or '')
        msg = cb.get('message') or {}
        chat_id = int((msg.get('chat') or {}).get('id'))
        if data_str == 'info_finance_off' or data_str.startswith('main_close:'):
            return chat_id
        if not data_str.startswith('d:'):
            return None
        parts = data_str.split(':', 2)
        if len(parts) < 3:
            return None
        cmd = parts[2]
        prefixes = ('qb_mode_normal_', 'qb_mode_open_', 'qb_mode_first_', 'qb_hidden_toggle_', 'fin_mode_toggle_', 'fin_mode_off_')
        if not cmd.startswith(prefixes):
            return None
        return int(cmd.rsplit('_', 1)[1])
    except Exception:
        return None

def _v177_legacy_0070_durable_task_required(payload: dict) -> tuple[bool, str]:
    """Hybrid persistence policy.

    Only state-changing/content-bearing message updates are persisted: finance, forwarding,
    article/edit input, secret input, edited messages and explicit mutation commands.
    Navigation/read-only commands and callback buttons stay on the existing Telegram retry path.
    """
    if not isinstance(payload, dict):
        return (False, 'invalid')
    if not mega_tasks_active():
        return (False, 'mega_tasks_inactive')
    for key in ('message', 'edited_message', 'channel_post', 'edited_channel_post'):
        msg = payload.get(key)
        if not isinstance(msg, dict):
            continue
        media_group_id = str(msg.get('media_group_id') or '').strip()
        text = str(msg.get('text') or msg.get('caption') or '').strip()
        first = text.split(maxsplit=1)[0].lower() if text else ''
        read_only_commands = {'/start', '/help', '/info', '/queues', '/queue_status', '/mega_status', '/delta_status', '/health', '/ping', '/prev', '/next', '/balance', '/report', '/tabl_lsx', '/xlsx', '/excel', '/csv', '/json', '/mega_restore_now', '/mega_backup_now', '/diag', '/diagnostics', '/errors', '/bot_errors', '/journal', '/runtime_export', '/log', '/logs', '/sqlite', '/db', '/windows', '/okna', '/окна', '/owners', '/additional_owners', '/доп_владельцы', '/dozvon'}
        if first in read_only_commands:
            return (False, f'{key}:readonly')
        mutation_commands = {'/reset', '/stopforward', '/backup_channel_on', '/backup_channel_off', '/buttons', '/restore_guard_off', '/restore_guard_on', '/off_on_backup_excel'}
        if first in mutation_commands or first.startswith('/izm_'):
            return (True, f'{key}:mutation_command')
        if first.startswith('/'):
            return (False, f'{key}:command_noncritical')
        try:
            chat_id = int((msg.get('chat') or {}).get('id'))
        except Exception:
            chat_id = None
        if key in {'edited_message', 'edited_channel_post'}:
            return (True, key)
        if chat_id is not None:
            try:
                store = get_chat_store(chat_id)
                waiting = any((str(k).endswith('_wait') and bool(v) for k, v in (store or {}).items()))
                if waiting:
                    return (True, f'{key}:input_wait' + (':media_group' if media_group_id else ''))
            except Exception:
                pass
            try:
                if is_finance_mode(chat_id):
                    return (True, f'{key}:finance' + (':media_group' if media_group_id else ''))
            except Exception:
                pass
            try:
                if resolve_forward_targets(chat_id):
                    ctype = _durable_raw_content_type(msg)
                    return (True, f'{key}:forward_all:{ctype}' + (':media_group' if media_group_id else ''))
            except Exception:
                pass
            try:
                if is_total_secret_mode(chat_id):
                    return (True, f'{key}:secret' + (':media_group' if media_group_id else ''))
            except Exception:
                pass
        return (False, f'{key}:noncritical_content')
    if isinstance(payload.get('callback_query'), dict):
        target_chat = _durable_callback_target_chat(payload)
        if target_chat is not None:
            return (True, f'callback:critical_finance_window:{target_chat}')
        return (False, 'callback:webhook_retry_only')
    return (False, 'noncritical_update')
try:
    _v177_legacy_0070_durable_task_required.__name__ = 'durable_task_required'
except Exception:
    pass

def _build_mega_task_payload(update_id, payload: dict, chat_id=None, update_type: str='other', reason: str='') -> dict:
    key = _mega_task_id(update_id)
    context = {}
    if chat_id is not None:
        try:
            store = get_chat_store(int(chat_id))
            waits = {str(k): _delta_json_clone(v) for k, v in (store or {}).items() if str(k).endswith('_wait') and bool(v)}
            if waits:
                context['wait_states'] = waits
            if (store or {}).get('current_view_day'):
                context['current_view_day'] = str(store.get('current_view_day'))
        except Exception as e:
            log_error(f'MEGA TASK context capture update={key}: {e}')
    callback_target = _durable_callback_target_chat(payload) if isinstance(payload, dict) else None
    if callback_target is not None:
        context['callback_target_chat_id'] = int(callback_target)
    return {'kind': 'telegram_bot_durable_task', 'schema_version': 5, 'bot_version': VERSION, 'task_id': key, 'update_id': int(update_id) if str(update_id).lstrip('-').isdigit() else str(update_id), 'created_at': now_local().isoformat(timespec='microseconds'), 'chat_id': chat_id, 'update_type': str(update_type or 'other'), 'reason': str(reason or 'critical_update'), 'source_message_id': _durable_payload_message(payload)[2] if isinstance(payload, dict) else None, 'media_group_id': _durable_payload_message(payload)[3] if isinstance(payload, dict) else None, 'content_type': _durable_raw_content_type(_durable_payload_message(payload)[0] if isinstance(payload, dict) else None), 'forward_targets': [{'dst_chat_id': int(dst), 'mode': str(mode), 'finance_enabled': bool(fin)} for dst, mode, fin in _durable_forward_targets(_durable_payload_message(payload)[1] if isinstance(payload, dict) else None)], 'expected_effects': _durable_expected_effects(payload if isinstance(payload, dict) else {}), 'context': context, 'payload': _delta_json_clone(payload or {})}

def restore_mega_task_context(task: dict):
    """Restore transient input/wait context captured at receipt before replay after deploy.

    This is what keeps an article/finance edit answer meaningful even if Render wiped the
    local SQLite after the prompt was opened but before the answer was processed.
    """
    if not isinstance(task, dict):
        return
    chat_id = task.get('chat_id')
    if chat_id is None:
        return
    context = task.get('context') or {}
    waits = context.get('wait_states') or {}
    changed = False
    try:
        store = get_chat_store(int(chat_id))
        for key, value in waits.items():
            if str(key).endswith('_wait') and value and (not store.get(str(key))):
                store[str(key)] = _delta_json_clone(value)
                changed = True
        if context.get('current_view_day') and (not store.get('current_view_day')):
            store['current_view_day'] = str(context.get('current_view_day'))
            changed = True
        if changed:
            save_data(data, chat_ids=[int(chat_id)])
            bot_journal('mega_task_context_restored', int(chat_id), f"task={task.get('task_id')} waits={list(waits.keys())}")
    except Exception as e:
        log_error(f"restore_mega_task_context task={task.get('task_id')}: {e}")

def _canon_mega_task_upload_new_pending__001(update_id, task_payload: dict) -> bool:
    """v190 write-before-execute witness: one MEGA put, no candidate+rename round-trip.

    task_<update_id>.json is unique.  If a retry races with an already uploaded copy,
    the existing file is accepted.  This keeps strict external durability while removing
    two foreground MEGA operations from every finance message.
    """
    global _mega_task_last_error
    _timing_started = time.monotonic()
    if not mega_tasks_active():
        return False
    key = _mega_task_id(update_id)
    try:
        if 'operation_begin_durable' in globals():
            operation_begin_durable(key, task_payload)
            operation_step(operation_for_update(key), 'saved_locally', 'durable payload prepared', persist=False)
    except Exception as _op_exc:
        log_error(f'operation ledger begin update={key}: {_op_exc}')
    known = mega_task_known_state(key)
    if known in {'pending', 'running', 'done'}:
        return True
    local_path = None
    try:
        remote_dir = mega_task_remote_dir('pending')
        if not ensure_mega_task_dirs():
            raise RuntimeError('MEGA task directories unavailable')
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
        remote_final = mega_task_remote_path(key, 'pending')
        _mega_task_update_registry(key, 'pending', remote_final)
        try:
            if 'operation_step' in globals():
                operation_step(operation_for_update(key), 'saved_to_mega', remote_final, persist=False)
        except Exception:
            pass
        with _MEGA_TASK_LOCK:
            _mega_task_counters['persisted'] += 1
        bot_journal('mega_task_timing', None, f'phase=persist_v190_one_put update={key} elapsed={time.monotonic() - _timing_started:.3f}s')
        return True
    except Exception as e:
        _mega_task_last_error = str(e)[:500]
        with _MEGA_TASK_LOCK:
            _mega_task_counters['persist_errors'] += 1
        log_error(f'[MEGA TASK PERSIST] update={key}: {e}')
        return False
    finally:
        try:
            if local_path and os.path.exists(local_path):
                os.remove(local_path)
        except Exception:
            pass

def _canon_mega_task_move__001(update_id, from_state: str, to_state: str) -> bool:
    global _mega_task_last_error
    _timing_started = time.monotonic()
    if not mega_tasks_active():
        return False
    key = _mega_task_id(update_id)
    try:
        src = mega_task_remote_path(key, from_state)
        dst_dir = mega_task_remote_dir(to_state)
        dst = mega_task_remote_path(key, to_state)
        if not ensure_mega_task_dirs():
            raise RuntimeError('MEGA task directories unavailable')
        res = _mega_run('mega-mv', [src, dst], check=False, timeout=60)
        if res.returncode != 0:
            err = (res.stderr or res.stdout or '')[:500]
            if _mega_remote_missing_error(err):
                try:
                    mega_ensure_remote_path(dst_dir, force=True)
                    res = _mega_run('mega-mv', [src, dst], check=False, timeout=60)
                    err = (res.stderr or res.stdout or '')[:500]
                except Exception:
                    pass
            found = _mega_find_remote_files(dst_dir, mega_task_filename(key), limit=2)
            if res.returncode != 0 and (not found):
                raise RuntimeError(err or f'cannot move {src} -> {dst}')
        _mega_task_update_registry(key, to_state, dst)
        bot_journal('mega_task_timing', None, f'phase=move update={key} {from_state}->{to_state} elapsed={time.monotonic() - _timing_started:.3f}s')
        return True
    except Exception as e:
        _mega_task_last_error = str(e)[:500]
        log_error(f'[MEGA TASK MOVE] update={key} {from_state}->{to_state}: {e}')
        return False

def _canon_mega_task_begin__001(update_id, allow_existing_running: bool=False) -> bool:
    """Claim a persisted task locally without a foreground MEGA move.

    The remote file intentionally stays in ``pending`` until background verification moves
    it directly to done/failed.  If Render dies during execution, startup sees ``pending``
    and safely replays/repairs the idempotent update.
    """
    key = _mega_task_id(update_id)
    success = False
    with _MEGA_TASK_LOCK:
        if key in _mega_task_processing:
            return False
        state = mega_task_known_state(key)
        if state == 'done':
            return False
        if state == 'running' and (not allow_existing_running):
            return False
        if state not in {'pending', 'failed', 'running'}:
            return False
        _mega_task_processing.add(key)
    try:
        state = mega_task_known_state(key)
        if state == 'failed':
            if not _mega_task_move(key, 'failed', 'pending'):
                return False
        elif state == 'running' and (not allow_existing_running):
            return False
        try:
            if 'operation_step' in globals():
                operation_step(operation_for_update(key), 'effect_running', f'state=pending_remote/local_running', persist=False)
        except Exception:
            pass
        success = True
        return True
    finally:
        if not success:
            with _MEGA_TASK_LOCK:
                _mega_task_processing.discard(key)

def _canon_mega_task_prune_done_async__001():

    def _job():
        try:
            rows = _mega_find_remote_files(mega_task_remote_dir('done'), 'task_*.json')
            for remote_path in rows[MEGA_TASK_DONE_KEEP:]:
                _mega_run('mega-rm', [remote_path], check=False, timeout=30)
                key = os.path.basename(remote_path).removeprefix('task_').removesuffix('.json')
                with _MEGA_TASK_LOCK:
                    if mega_task_known_state(key) == 'done':
                        _mega_task_registry.pop(key, None)
        except Exception as e:
            log_error(f'_mega_task_prune_done_async: {e}')
    BACKUP_TASK_POOL.submit('mega-task-prune', _job)

def _v177_legacy_0071_mega_task_finish(update_id, success: bool, error: str='') -> bool:
    global _mega_task_last_error
    _timing_started = time.monotonic()
    key = _mega_task_id(update_id)
    target = 'done' if success else 'failed'
    ok = False
    for attempt in range(MEGA_TASK_FINALIZE_RETRIES):
        state = mega_task_known_state(key) or 'running'
        if state == target:
            ok = True
            break
        if state == 'done' and success:
            ok = True
            break
        if _mega_task_move(key, state if state in {'pending', 'running', 'failed'} else 'running', target):
            ok = True
            break
        if attempt + 1 < MEGA_TASK_FINALIZE_RETRIES:
            time.sleep(min(1.0, 0.2 * (attempt + 1)))
    with _MEGA_TASK_LOCK:
        _mega_task_processing.discard(key)
        if success:
            if ok:
                _mega_task_counters['completed'] += 1
            else:
                _mega_task_counters['finalize_errors'] += 1
        else:
            _mega_task_counters['failed'] += 1
    if success and ok:
        _mega_task_prune_done_async()
    if not ok:
        _mega_task_last_error = f'finalize {target} failed for {key}: {error}'[:500]
    try:
        if success and ok and ('operation_complete' in globals()):
            operation_complete(operation_for_update(key), 'durable task completed')
        elif not success and str(error or '').startswith('needs_review') and ('operation_review' in globals()):
            operation_review(operation_for_update(key), error)
        elif not success and 'operation_fail' in globals():
            operation_fail(operation_for_update(key), error or 'durable task failed')
    except Exception as _op_exc:
        log_error(f'operation ledger finish update={key}: {_op_exc}')
    bot_journal('mega_task_timing', None, f'phase=finish update={key} target={target} ok={ok} elapsed={time.monotonic() - _timing_started:.3f}s')
    return ok
try:
    _v177_legacy_0071_mega_task_finish.__name__ = 'mega_task_finish'
except Exception:
    pass

def _canon_mega_task_refresh_registry__001() -> dict:
    """Load task states from MEGA in one recursive find. Safe to call at startup or manually."""
    global _mega_task_registry_loaded_at, _mega_task_last_error
    if not mega_tasks_active():
        return mega_task_registry_stats()
    try:
        root = mega_task_remote_root()
        if not ensure_mega_task_dirs(force=True):
            raise RuntimeError('MEGA task directories unavailable')
        for candidate in _mega_find_remote_files(root, 'candidate_task_*.json', limit=None):
            name = os.path.basename(candidate)
            match = re.fullmatch('candidate_task_([A-Za-z0-9_-]+)_\\d{8}_\\d{6}_\\d{6}\\.json', name)
            if not match:
                continue
            key = match.group(1)
            final = mega_task_remote_path(key, 'pending')
            existing = _mega_find_remote_files(mega_task_remote_dir('pending'), mega_task_filename(key), limit=1)
            if existing:
                _mega_run('mega-rm', [candidate], check=False, timeout=30)
            else:
                _mega_run('mega-mv', [candidate, final], check=False, timeout=60)
        rows = _mega_find_remote_files(root, 'task_*.json', limit=None)
        new_registry = {}
        for path in rows:
            name = os.path.basename(path)
            match = re.fullmatch('task_([A-Za-z0-9_-]+)\\.json', name)
            if not match:
                continue
            state = ''
            for candidate in ('pending', 'running', 'done', 'failed'):
                if f'/{candidate}/' in path.replace('\\', '/'):
                    state = candidate
                    break
            if not state:
                continue
            key = match.group(1)
            rank = {'failed': 1, 'pending': 2, 'running': 3, 'done': 4}
            old = new_registry.get(key)
            if old is None or rank[state] >= rank.get(old.get('state'), 0):
                new_registry[key] = {'state': state, 'path': path, 'loaded_at': now_local().isoformat(timespec='seconds')}
        with _MEGA_TASK_LOCK:
            for key, row in _mega_task_registry.items():
                if key in _mega_task_processing and key not in new_registry:
                    new_registry[key] = dict(row)
            _mega_task_registry.clear()
            _mega_task_registry.update(new_registry)
            _mega_task_registry_loaded_at = now_local().isoformat(timespec='seconds')
        return mega_task_registry_stats()
    except Exception as e:
        _mega_task_last_error = str(e)[:500]
        log_error(f'mega_task_refresh_registry: {e}')
        return mega_task_registry_stats()

def _mega_task_effect_exists(payload: dict, expected_effects: dict | None=None) -> bool:
    """True only if every explicitly expected effect is already proven."""
    try:
        report = _durable_effect_report(payload, expected_effects if isinstance(expected_effects, dict) else None)
        return bool(report.get('complete'))
    except Exception:
        return False

def _repair_safe_missing_forward_secret_effects(payload: dict, expected_effects: dict | None=None) -> bool:
    """Repair only SECRET metadata for an already-confirmed Telegram copy.

    No copy_message/forward_message call is made here, so this cannot create a duplicate.
    """
    expected = expected_effects if isinstance(expected_effects, dict) else _durable_expected_effects(payload)
    raw, source_chat_id, source_msg_id, _group_id = _durable_payload_message(payload)
    if not isinstance(raw, dict) or source_chat_id is None or source_msg_id is None:
        return True
    try:
        links = {int(dst): int(mid) for dst, mid in get_forward_links(source_chat_id, source_msg_id)}
    except Exception:
        links = {}
    msg = None
    for target in expected.get('forward_targets', []) or []:
        if not bool(target.get('secret_expected')):
            continue
        try:
            dst = int(target.get('dst_chat_id'))
            dst_msg_id = int(links.get(dst) or 0)
        except Exception:
            continue
        if not dst_msg_id:
            continue
        try:
            exists = any((isinstance(r, dict) and int(r.get('source_msg_id') or 0) == dst_msg_id and (int(r.get('forward_source_msg_id') or source_msg_id) == int(source_msg_id)) for r in _secret_records(dst)))
        except Exception:
            exists = False
        if exists:
            continue
        if msg is None:
            msg = _durable_payload_to_message(payload)
        if msg is None:
            return False
        try:
            save_secret_bot_copy(dst, dst_msg_id, msg)
            try:
                bot.delete_message(dst, dst_msg_id)
            except Exception:
                pass
            bot_journal('durable_forward_secret_repaired', dst, f'src={source_chat_id}:{source_msg_id} dst_msg={dst_msg_id}')
        except Exception as e:
            log_error(f'DURABLE SAFE SECRET REPAIR {source_chat_id}:{source_msg_id}->{dst}:{dst_msg_id}: {e}')
            return False
    return True

def _repair_safe_missing_finance_effects(payload: dict, expected_effects: dict | None=None) -> bool:
    """Repair only finance effects that are intrinsically idempotent in v109.

    Never sends Telegram messages. A forwarded-finance repair is allowed only when the
    destination Telegram link already exists. Direct finance uses source message_id as its
    unique operation key, so add_record_to_chat returns the existing record on replay.
    """
    expected = _durable_normalize_expected_for_route(payload, expected_effects if isinstance(expected_effects, dict) else _durable_expected_effects(payload))
    raw, source_chat_id, source_msg_id, _group_id = _durable_payload_message(payload)
    if not isinstance(raw, dict) or source_chat_id is None or source_msg_id is None:
        return False
    msg = _durable_payload_to_message(payload)
    if msg is None:
        return False
    if bool(expected.get('source_finance')):
        try:
            if find_record_by_message_id(source_chat_id, source_msg_id) is None:
                handle_finance_text(msg)
        except Exception as e:
            log_error(f'DURABLE SAFE DIRECT FINANCE REPAIR {source_chat_id}:{source_msg_id}: {e}')
    links = {}
    try:
        links = {int(dst): int(mid) for dst, mid in get_forward_links(source_chat_id, source_msg_id)}
    except Exception:
        links = {}
    text = _message_text_for_finance(msg)
    for target in expected.get('forward_targets', []) or []:
        if not bool(target.get('finance_expected')):
            continue
        try:
            dst = int(target.get('dst_chat_id'))
        except Exception:
            continue
        dst_msg_id = links.get(dst)
        if not dst_msg_id:
            continue
        try:
            if find_record_by_message_id(dst, dst_msg_id) is None:
                owner_id = msg.from_user.id if getattr(msg, 'from_user', None) else 0
                sync_forwarded_finance_message(dst, dst_msg_id, text, owner_id, source_msg=msg)
        except Exception as e:
            log_error(f'DURABLE SAFE FORWARD FINANCE REPAIR {source_chat_id}:{source_msg_id}->{dst}:{dst_msg_id}: {e}')
    return bool(_durable_effect_report(payload, expected).get('complete'))

def _v177_legacy_0072_execute_telegram_payload(payload: dict, update_id=None, update_chat_id=None, update_type: str='other'):
    """Single execution path used by live webhook and MEGA startup recovery."""
    update = telebot.types.Update.de_json(payload)
    if update_chat_id is None:
        update_chat_id = _extract_update_chat_id(payload) if isinstance(payload, dict) else None
    previous_ctx = getattr(_TELEGRAM_UPDATE_CONTEXT, 'value', None)
    critical_callback_target = _durable_callback_target_chat(payload) if isinstance(payload, dict) else None
    callback_data = ''
    source_message_id = None
    source_user_id = None
    try:
        if isinstance(payload, dict):
            callback = payload.get('callback_query') or {}
            if isinstance(callback, dict):
                callback_data = str(callback.get('data') or '')
                source_user_id = (callback.get('from') or {}).get('id') if isinstance(callback.get('from'), dict) else None
                callback_message = callback.get('message') or {}
                if isinstance(callback_message, dict):
                    source_message_id = callback_message.get('message_id')
            if source_message_id is None:
                message_payload = payload.get('message') or payload.get('edited_message') or payload.get('channel_post') or payload.get('edited_channel_post') or {}
                if isinstance(message_payload, dict):
                    source_message_id = message_payload.get('message_id')
                    source_user_id = source_user_id or ((message_payload.get('from') or {}).get('id') if isinstance(message_payload.get('from'), dict) else None)
    except Exception:
        callback_data = ''
    _TELEGRAM_UPDATE_CONTEXT.value = {'update_id': update_id, 'chat_id': update_chat_id, 'update_type': str(update_type or 'other'), 'callback_data': callback_data, 'message_id': source_message_id, 'user_id': source_user_id, 'critical_callback': critical_callback_target is not None, 'critical_callback_target': critical_callback_target, 'deferred_quick_chats': set()}
    execution_ctx = {}
    try:
        with state_chat_context(update_chat_id):
            if update_chat_id is None:
                bot.process_new_updates([update])
            else:
                with locked_chat(update_chat_id):
                    bot.process_new_updates([update])
        execution_ctx = _durable_execution_context_snapshot()
    finally:
        if not execution_ctx:
            execution_ctx = _durable_execution_context_snapshot()
        if previous_ctx is None:
            try:
                delattr(_TELEGRAM_UPDATE_CONTEXT, 'value')
            except Exception:
                pass
        else:
            _TELEGRAM_UPDATE_CONTEXT.value = previous_ctx
    return execution_ctx
try:
    _v177_legacy_0072_execute_telegram_payload.__name__ = '_execute_telegram_payload'
except Exception:
    pass

def _mega_task_recover_one(update_id, state: str, remote_path: str):
    """Recover without replaying uncertain `running` business operations.

    pending = business never started -> may execute once.
    running = business may have partially/fully executed -> inspect and repair only safe
    idempotent finance effects; never resend Telegram copies and never rerun callbacks/handlers.
    """
    key = _mega_task_id(update_id)
    if mega_task_known_state(key) == 'done':
        return
    if not mega_task_begin(key, allow_existing_running=state == 'running'):
        return
    try:
        path = remote_path
        if state == 'pending':
            with _MEGA_TASK_LOCK:
                path = str((_mega_task_registry.get(key) or {}).get('path') or mega_task_remote_path(key, 'running'))
        local = _mega_download_remote_path(path)
        task = _load_json(local, {}) if local else {}
        payload = (task or {}).get('payload') or {}
        if not isinstance(payload, dict) or not payload:
            raise RuntimeError('task payload is empty')
        restore_mega_task_context(task)
        chat_id = (task or {}).get('chat_id')
        update_type = str((task or {}).get('update_type') or 'recovered')
        expected = _durable_expected_from_task_or_payload(task, payload)
        if durable_update_processed(key):
            mega_task_finish(key, True, 'processed_marker_present')
            with _MEGA_TASK_LOCK:
                _mega_task_counters['skipped_done'] += 1
            return
        if state == 'running':
            if _v230_constitution_finance_wait(payload, expected):
                schedule_durable_task_finalize_retry(key, chat_id, update_type, 15.0, payload=payload, expected_effects=expected)
                try:
                    bot_journal('mega_task_finance_wait_constitution_v230', chat_id, f'update_id={key}; state=running', 'WARN')
                except Exception:
                    pass
                return
            if not _mega_task_effect_exists(payload, expected):
                _repair_safe_missing_finance_effects(payload, expected)
                _repair_safe_missing_forward_secret_effects(payload, expected)
            if _mega_task_effect_exists(payload, expected):
                if finalize_durable_task_after_business(key, chat_id, update_type, payload=payload, expected_effects=expected):
                    with _MEGA_TASK_LOCK:
                        _mega_task_counters['skipped_done'] += 1
                return
            report = _durable_effect_report(payload, expected)
            reason = f"needs_review_running: business not replayed; missing={report.get('missing', [])}; ambiguous={report.get('ambiguous', [])}"
            mega_task_finish(key, False, reason)
            bot_journal('mega_task_needs_review', chat_id, f'update_id={key} {reason}')
            try:
                if OWNER_ID and (not ('safety_profile_new_enabled' in globals() and safety_profile_new_enabled())):
                    bot.send_message(int(OWNER_ID), f'⚠️ Задача {key} после перезапуска НЕ повторена, чтобы не создать дубль.\n{reason[:850]}')
            except Exception:
                pass
            return
        execution_ctx = _execute_telegram_payload(payload, key, chat_id, update_type)
        expected_after = _durable_expected_after_execution(expected, execution_ctx, payload)
        finalized = finalize_durable_task_after_business(key, chat_id, update_type, payload=payload, expected_effects=expected_after)
        if not finalized:
            schedule_durable_task_finalize_retry(key, chat_id, update_type, 1.0, payload=payload, expected_effects=expected_after)
        with _MEGA_TASK_LOCK:
            _mega_task_counters['recovered'] += 1
        bot_journal('mega_task_recovered', chat_id, f'update_id={key} state={state} finalized={finalized}')
    except Exception as e:
        mega_task_finish(key, False, str(e))
        log_error(f'MEGA TASK RECOVERY FAILED update={key}: {e}')
        try:
            if OWNER_ID:
                bot.send_message(int(OWNER_ID), f'⚠️ MEGA-задача {key} не восстановлена автоматически:\n{str(e)[:700]}')
        except Exception:
            pass

def _canon_schedule_mega_task_recovery__001(delay: float | None=None):
    """After data restore, replay pending/uncertain tasks independently of normal bot queues."""
    if not mega_tasks_active():
        return
    delay = MEGA_TASK_RECOVERY_DELAY_SECONDS if delay is None else max(0.1, float(delay))

    def _scan_and_submit():
        stats = mega_task_refresh_registry()
        rows = []
        with _MEGA_TASK_LOCK:
            for key, row in _mega_task_registry.items():
                if row.get('state') in {'pending', 'running'}:
                    rows.append((key, str(row.get('state')), str(row.get('path') or '')))
        rows = sorted(rows, key=lambda x: int(x[0]) if str(x[0]).isdigit() else str(x[0]))[:MEGA_TASK_RECOVERY_LIMIT]
        for key, state, path in rows:

            def _job(k=key, st=state, rp=path):
                _mega_task_recover_one(k, st, rp)
            if not RECOVERY_TASK_POOL.submit('mega-recover-global', _job):
                log_error(f'MEGA TASK RECOVERY QUEUE FULL update={key}')
        log_info(f"[MEGA TASKS] registry pending={stats.get('pending')} running={stats.get('running')} failed={stats.get('failed')} recovery_submitted={len(rows)}")
    DELAYED_SCHEDULER.cancel('mega-task-startup-recovery')
    DELAYED_SCHEDULER.schedule('mega-task-startup-recovery', delay, _scan_and_submit)

def _canon_schedule_safe_failed_task_repairs__001(delay: float=6.0, limit: int=20):
    """Repair FAILED tasks only when completion can be proven without replaying business work.

    Besides the existing metadata-only repairs, v122 recognizes an old false-positive trio
    11 -> 22 -> 33 from the hidden secret-sequence handler.  The trio is repaired only when
    all three failed tasks belong to the same chat + same Telegram user, arrived in order
    within the handler's 10-second window, and each failure is only a source_finance witness.
    No finance record is created/deleted and no Telegram message is replayed.
    """
    if not mega_tasks_active():
        return

    def _scan():
        loaded = []
        try:
            mega_task_refresh_registry()
            with _MEGA_TASK_LOCK:
                rows = [(k, str(row.get('path') or '')) for k, row in _mega_task_registry.items() if row.get('state') == 'failed'][:max(1, int(limit))]
            for key, remote_path in rows:
                local = None
                try:
                    local = _mega_download_remote_path(remote_path or mega_task_remote_path(key, 'failed'))
                    task = _load_json(local, {}) if local else {}
                    payload = (task or {}).get('payload') or {}
                    if not isinstance(payload, dict) or not payload:
                        continue
                    expected = _durable_expected_from_task_or_payload(task, payload)
                    report = _durable_effect_report(payload, expected)
                    loaded.append({'key': key, 'task': task, 'payload': payload, 'expected': expected, 'report': report})
                except Exception as e:
                    log_error(f'SAFE FAILED TASK LOAD update={key}: {e}')
                finally:
                    try:
                        if local:
                            shutil.rmtree(os.path.dirname(local), ignore_errors=True)
                    except Exception:
                        pass
            repaired = 0
            repaired_keys = set()
            for item in loaded:
                key = item['key']
                task = item['task']
                payload = item['payload']
                expected = item['expected']
                report = item['report']
                missing = [str(x) for x in report.get('missing') or []]
                ambiguous = [str(x) for x in report.get('ambiguous') or []]
                finance_only = not ambiguous and bool(missing) and all((x.startswith('source_finance:') for x in missing)) and bool(expected.get('source_finance'))
                if finance_only:
                    try:
                        if globals().get('constitution_finance_write_blocked_v232') and constitution_finance_write_blocked_v232():
                            continue
                    except Exception:
                        continue
                    _repair_safe_missing_finance_effects(payload, expected)
                    report = _durable_effect_report(payload, expected)
                    missing = [str(x) for x in report.get('missing') or []]
                    ambiguous = [str(x) for x in report.get('ambiguous') or []]
                eligible = bool(report.get('complete')) or (not ambiguous and bool(missing) and all((x.startswith('forward_secret:') for x in missing)))
                if not eligible:
                    continue
                try:
                    if finalize_durable_task_after_business(key, (task or {}).get('chat_id'), str((task or {}).get('update_type') or 'recovered'), payload=payload, expected_effects=expected):
                        repaired += 1
                        repaired_keys.add(str(key))
                        reason = 'reclassified_complete' if bool(report.get('complete')) else f'missing={missing}'
                        bot_journal('mega_task_failed_safe_repaired', (task or {}).get('chat_id'), f'update_id={key} {reason}')
                except Exception as e:
                    log_error(f'SAFE FAILED TASK REPAIR update={key}: {e}')
            seq_candidates = []
            for item in loaded:
                if str(item['key']) in repaired_keys:
                    continue
                report = item['report']
                missing = [str(x) for x in report.get('missing') or []]
                ambiguous = [str(x) for x in report.get('ambiguous') or []]
                if ambiguous or len(missing) != 1 or (not missing[0].startswith('source_finance:')):
                    continue
                try:
                    raw, src_chat_id, msg_id, _group = _durable_payload_message(item['payload'])
                    text = str((raw or {}).get('text') or '').strip()
                    if text not in {'11', '22', '33'}:
                        continue
                    user_id = int(((raw or {}).get('from') or {}).get('id') or 0)
                    src_chat_id = int(src_chat_id)
                    msg_id = int(msg_id)
                    if not user_id or not src_chat_id or (not msg_id):
                        continue
                    created = str((item['task'] or {}).get('created_at') or '')
                    dt = datetime.fromisoformat(created) if created else None
                    ts = float(dt.timestamp()) if dt else 0.0
                    if not ts:
                        continue
                    seq_candidates.append({**item, 'text': text, 'src_chat_id': src_chat_id, 'user_id': user_id, 'msg_id': msg_id, 'ts': ts})
                except Exception:
                    continue
            by_owner = {}
            for item in seq_candidates:
                by_owner.setdefault((item['src_chat_id'], item['user_id']), []).append(item)
            for group in by_owner.values():
                group.sort(key=lambda x: (x['ts'], x['msg_id']))
                for idx in range(max(0, len(group) - 2)):
                    trio = group[idx:idx + 3]
                    if [x['text'] for x in trio] != ['11', '22', '33']:
                        continue
                    if not trio[0]['msg_id'] < trio[1]['msg_id'] < trio[2]['msg_id']:
                        continue
                    if trio[2]['ts'] - trio[0]['ts'] > 10.0:
                        continue
                    for item in trio:
                        key = item['key']
                        if str(key) in repaired_keys:
                            continue
                        expected = _delta_json_clone(item['expected'] or {})
                        expected['source_finance'] = False
                        expected['source_secret'] = False
                        expected['forward_targets'] = []
                        expected['source_consumed_reason'] = 'legacy_secret_sequence_trio'
                        try:
                            if finalize_durable_task_after_business(key, (item['task'] or {}).get('chat_id'), str((item['task'] or {}).get('update_type') or 'recovered'), payload=item['payload'], expected_effects=expected):
                                repaired += 1
                                repaired_keys.add(str(key))
                                bot_journal('mega_task_failed_safe_repaired', (item['task'] or {}).get('chat_id'), f'update_id={key} legacy_secret_sequence_trio')
                        except Exception as e:
                            log_error(f'SAFE SECRET-SEQUENCE FAILED REPAIR update={key}: {e}')
                    break
            if repaired:
                log_info(f'[MEGA TASKS] safe failed repairs={repaired}')
        except Exception as e:
            log_error(f'schedule_safe_failed_task_repairs: {e}')
    DELAYED_SCHEDULER.cancel('mega-task-safe-failed-repair')
    DELAYED_SCHEDULER.schedule('mega-task-safe-failed-repair', max(1.0, float(delay)), _scan)

def mega_task_requeue_failed(limit: int=20) -> int:
    """Manual owner action only: move a bounded number of failed tasks back to pending."""
    moved = 0
    mega_task_refresh_registry()
    with _MEGA_TASK_LOCK:
        keys = [k for k, row in _mega_task_registry.items() if row.get('state') == 'failed'][:max(1, int(limit))]
    for key in keys:
        if _mega_task_move(key, 'failed', 'pending'):
            moved += 1
    if moved:
        schedule_mega_task_recovery(0.3)
    return moved

def schedule_restored_secret_media_recovery(delay: float=60.0):
    """Resume only missing SECRET media when runtime is idle and memory is safe."""

    def _defer(seconds: float, reason: str):
        try:
            bot_journal('secret_media_recovery_deferred_v210', None, reason)
        except Exception:
            pass
        DELAYED_SCHEDULER.cancel('secret-media-startup-recovery')
        DELAYED_SCHEDULER.schedule('secret-media-startup-recovery', max(30.0, float(seconds)), _job)

    def _interactive_busy() -> bool:
        for name in ('FAST_UI_TASK_POOL', 'UI_TASK_POOL', 'FINANCE_TASK_POOL', 'FORWARD_TASK_POOL', 'CONTENT_TASK_POOL'):
            pool = globals().get(name)
            if pool is None or not hasattr(pool, 'stats'):
                continue
            try:
                st = pool.stats() or {}
                if int(st.get('active', 0) or 0) > 0 or int(st.get('pending', 0) or 0) > 0:
                    return True
            except Exception:
                continue
        return False

    def _job():
        try:
            pressure_fn = globals().get('_runtime_memory_pressure')
            pressure = pressure_fn() if callable(pressure_fn) else {}
            level = str((pressure or {}).get('level') or 'normal')
            if level in {'high', 'critical', 'emergency'}:
                _defer(120.0, f'memory={level}')
                return
            if _interactive_busy():
                _defer(45.0, 'interactive queues busy')
                return
            for cid in secret_chats():
                try:
                    pending_media = any((isinstance(r, dict) and r.get('file_id') and (not r.get('mega_media_path')) for r in _secret_records(cid)))
                    if pending_media:
                        if not BACKUP_TASK_POOL.submit(f'secret-media-recover:{cid}', upload_chat_secrets_to_mega, cid):
                            schedule_secret_mega_upload(cid, BACKUP_BUSY_RETRY_SECONDS)
                except Exception as e:
                    log_error(f'SECRET MEDIA RECOVERY chat={cid}: {e}')
        except Exception as e:
            log_error(f'schedule_restored_secret_media_recovery: {e}')
    DELAYED_SCHEDULER.cancel('secret-media-startup-recovery')
    DELAYED_SCHEDULER.schedule('secret-media-startup-recovery', max(30.0, float(delay)), _job)

def current_month_key() -> str:
    return now_local().strftime('%Y-%m')

def _v177_legacy_0075_record_day_key(rec: dict) -> str:
    dk = str((rec or {}).get('day_key') or '').strip()
    if dk:
        return dk[:10]
    ts = str((rec or {}).get('timestamp') or '')
    return ts[:10] if len(ts) >= 10 else today_key()
try:
    _v177_legacy_0075_record_day_key.__name__ = '_record_day_key'
except Exception:
    pass

def calc_opening_balance_for_month(store: dict, month_key: str, chat_id: int | None=None, currency: str='ars') -> float:
    """Canonical opening balance before YYYY-MM-01 for the requested currency."""
    start = f'{month_key}-01'
    helper = globals().get('_excel_canonical_opening_balance')
    if callable(helper) and chat_id is not None:
        return float(helper(int(chat_id), currency, start, 0, False))
    total = 0.0
    for r in store.get('records', []) or []:
        try:
            if _record_day_key(r) < start:
                total += float(r.get('amount', 0) or 0)
        except Exception:
            pass
    return float(total)

def month_records_for_chat(store: dict, month_key: str) -> list[dict]:
    out = []
    prefix = month_key + '-'
    for r in store.get('records', []) or []:
        try:
            if _record_day_key(r).startswith(prefix):
                out.append(r)
        except Exception:
            pass
    return sorted(out, key=lambda r: (_record_day_key(r), str(r.get('timestamp', ''))))

def build_chat_settings_backup_payload(chat_id: int, store: dict | None=None) -> dict:
    """Полная настройка чата для JSON-бэкапа: финрежим, скрытый режим, пересылки, быстрый остаток."""
    store = store or get_chat_store(chat_id)
    cid = str(chat_id)
    with data_lock:
        fr = json.loads(json.dumps(data.get('forward_rules', {}) or {}, ensure_ascii=False, default=str))
        ff = json.loads(json.dumps(data.get('forward_finance', {}) or {}, ensure_ascii=False, default=str))
        fac = json.loads(json.dumps(data.get('finance_active_chats', {}) or {}, ensure_ascii=False, default=str))
        flags = json.loads(json.dumps(data.get('backup_flags', {}) or {}, ensure_ascii=False, default=str))
    incoming_rules = {src: (dsts or {}).get(cid) for src, dsts in fr.items() if cid in (dsts or {})}
    outgoing_rules = fr.get(cid, {}) or {}
    incoming_finance = {src: (dsts or {}).get(cid) for src, dsts in ff.items() if cid in (dsts or {})}
    outgoing_finance = ff.get(cid, {}) or {}
    return {'chat_id': int(chat_id), 'chat_name': get_chat_display_name(chat_id), 'finance_mode': bool(store.get('finance_mode') or is_finance_mode(chat_id)), 'settings': store.get('settings', {}) or {}, 'balance_panel_id': store.get('balance_panel_id'), 'balance_panel_mode': store.get('balance_panel_mode'), 'current_view_day': store.get('current_view_day'), 'auto_backup_enabled': is_auto_backup_enabled(chat_id), 'hidden_finance': is_hidden_finance_mode(chat_id), 'quick_balance_enabled': is_quick_balance_enabled(chat_id), 'quick_balance_behavior': get_quick_balance_behavior(chat_id), 'forward_rules_outgoing': outgoing_rules, 'forward_rules_incoming': incoming_rules, 'forward_finance_outgoing': outgoing_finance, 'forward_finance_incoming': incoming_finance, 'global_forward_rules': fr, 'global_forward_finance': ff, 'finance_active_chats': fac, 'backup_flags': flags}

def build_chat_monthly_backup_payload(chat_id: int, month_key: str | None=None) -> dict:
    month_key = month_key or current_month_key()
    store = get_chat_store(chat_id)
    opening = calc_opening_balance_for_month(store, month_key)
    recs = sorted(month_records_for_chat(store, month_key), key=record_sort_key)
    total_income = 0.0
    total_expense = 0.0
    clean_recs = []
    for r in recs:
        rr = backup_record_copy(r)
        amt = float(r.get('amount', 0) or 0)
        if amt >= 0:
            total_income += amt
        else:
            total_expense += -amt
        rr['day_key'] = _record_day_key(r)
        rr['date'] = fmt_date_backup(rr['day_key'])
        clean_recs.append(rr)
    closing = opening + total_income - total_expense
    return {'kind': 'chat_monthly_backup', 'version': VERSION, 'created_at': now_local().isoformat(timespec='seconds'), 'date_format': 'DD:MM:YY', 'month': month_key, 'chat_id': int(chat_id), 'chat_name': get_chat_display_name(chat_id), 'opening_balance': opening, 'total_income': total_income, 'total_expense': total_expense, 'closing_balance': closing, 'record_count': len(clean_recs), 'settings_backup': build_chat_settings_backup_payload(chat_id, store), 'records': clean_recs}

def save_chat_monthly_backup_files(chat_id: int, month_key: str | None=None) -> dict:
    """Создаёт месячные JSON/CSV/XLSX с остатком на начало месяца и закрытием месяца."""
    month_key = month_key or current_month_key()
    slug = mega_chat_slug(chat_id)
    base = f'{month_key}_{slug}'
    os.makedirs(MEGA_LOCAL_TMP_DIR, exist_ok=True)
    json_path = os.path.join(MEGA_LOCAL_TMP_DIR, base + '.json')
    csv_path = os.path.join(MEGA_LOCAL_TMP_DIR, base + '.csv')
    xlsx_path = os.path.join(MEGA_LOCAL_TMP_DIR, base + '.xlsx')
    payload = build_chat_monthly_backup_payload(chat_id, month_key)
    table_records = list(payload.get('records', []) or [])
    table_canonical_records = []
    table_opening = float(payload.get('opening_balance') or 0.0)
    _start = f'{month_key}-01'
    _end = _start
    range_builder = globals().get('_excel_canonical_records_for_range')
    opening_builder = globals().get('_excel_canonical_opening_balance')
    try:
        import calendar as _v194_calendar
        _yy, _mm = [int(x) for x in str(month_key).split('-', 1)]
        _start = f'{_yy:04d}-{_mm:02d}-01'
        _end = f'{_yy:04d}-{_mm:02d}-{_v194_calendar.monthrange(_yy, _mm)[1]:02d}'
        if callable(range_builder):
            _canon = list(range_builder(int(chat_id), 'ars', _start, _end) or [])
            table_canonical_records = list(_canon)
            table_records = []
            for _rec in _canon or []:
                _rr = backup_record_copy(_rec)
                _rr['amount'] = float(_rec.get('_v151_amount', _rec.get('amount', 0)) or 0)
                _rr['note'] = str(_rec.get('_v151_note', _rec.get('note') or '') or '')
                _rr['day_key'] = str(globals().get('_v151_day_key', _record_day_key)(_rec))[:10]
                _rr['date'] = fmt_date_backup(_rr['day_key'])
                table_records.append(_rr)
        if callable(opening_builder):
            table_opening = float(opening_builder(int(chat_id), 'ars', _start, 0, False))
    except Exception as _v194_month_table_exc:
        try:
            log_error(f'monthly table canonical projection({chat_id},{month_key}): {_v194_month_table_exc}')
        except Exception:
            pass
    table_income = sum((max(0.0, float(r.get('amount', 0) or 0)) for r in table_records))
    table_expense = sum((max(0.0, -float(r.get('amount', 0) or 0)) for r in table_records))
    table_closing = float(table_opening + table_income - table_expense)
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    with open(csv_path, 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f)
        w.writerow(['month', month_key])
        w.writerow(['chat', payload.get('chat_name')])
        w.writerow(['opening_balance', table_opening])
        w.writerow(['total_income', table_income])
        w.writerow(['total_expense', table_expense])
        w.writerow(['closing_balance', table_closing])
        w.writerow([])
        w.writerow(['date', 'amount', 'note', 'id', 'short_id', 'timestamp', 'owner'])
        prev_day = None
        for r in table_records:
            day_key = str(r.get('day_key') or '')[:10]
            if prev_day is not None and day_key and (day_key != prev_day):
                w.writerow([])
            w.writerow([fmt_date_table(day_key), r.get('amount'), r.get('note', ''), r.get('id', ''), r.get('short_id', ''), r.get('timestamp', ''), r.get('owner', '')])
            if day_key:
                prev_day = day_key
    rows = [['Месяц', month_key, 'ARS'], ['Чат', payload.get('chat_name')], ['Остаток с прошлого раза', '', table_opening, ''], [], ['Дата', 'Описание', 'Приход', 'Расход', 'ID', 'Номер', 'Время', 'Автор']]
    data_start_row = 6
    prev_day = None
    for r in table_records:
        day_key = str(r.get('day_key') or '')[:10]
        if prev_day is not None and day_key and (day_key != prev_day):
            rows.append([])
        base_row = _xlsx_record_row(fmt_date_table(day_key), r.get('amount'), r.get('note', ''))
        rows.append(base_row + [r.get('id', ''), r.get('short_id', ''), r.get('timestamp', ''), r.get('owner', '')])
        if day_key:
            prev_day = day_key
    data_end_row = max(data_start_row, len(rows))
    rows.append([])
    income_row = len(rows) + 1
    rows.append(['', 'Приход за период', {'formula': f'SUM(C{data_start_row}:C{data_end_row})', 'value': table_income}, ''])
    expense_row = len(rows) + 1
    rows.append(['', 'Расход за период', '', {'formula': f'SUM(D{data_start_row}:D{data_end_row})', 'value': table_expense}])
    _v150_month_closing = float(table_closing)
    rows.append(['', 'Остаток на руках', {'formula': f'C3+C{income_row}-D{expense_row}', 'value': _v150_month_closing}, ''])
    _v150_month_reserve = float(_v150_export_reserve(chat_id)) if '_v150_export_reserve' in globals() else 0.0
    rows.append(['', 'Гомонковые', _v150_month_reserve, ''])
    rows.append(['', 'Остаток в обороте', _v150_month_closing - _v150_month_reserve, ''])
    rows.append([])
    _v150_month_products = 0.0
    _v150_month_food = 0.0
    try:
        if callable(globals().get('_v151_food_metric')) and table_canonical_records:
            _v150_month_products, _v150_month_food, _v194_days, _v194_rate = _v151_food_metric(int(chat_id), table_canonical_records, _start, _end)
        elif callable(globals().get('_v150_product_total_from_records')):
            _v150_month_products = _v150_product_total_from_records(chat_id, table_records)
            _v150_month_food = _v150_food_per_person(_v150_month_products) if '_v150_food_per_person' in globals() else 0.0
    except Exception:
        _v150_month_products = 0.0
        _v150_month_food = 0.0
    rows.append(['', 'Расход еды на человека в сутки', _v150_month_food, ''])
    try:
        usd_builder = globals().get('_v151_simple_table')
        usd_enabled = globals().get('excel_usd_table_enabled')
        ctx_local = globals().get('_V151_EXPORT_LOCAL')
        if callable(usd_builder) and (not callable(usd_enabled) or bool(usd_enabled(int(chat_id)))) and (ctx_local is not None):
            prev_ctx = getattr(ctx_local, 'value', None)
            year_v, month_v = [int(x) for x in str(month_key).split('-', 1)]
            import calendar as _v192_calendar
            last_v = _v192_calendar.monthrange(year_v, month_v)[1]
            start_v = f'{year_v:04d}-{month_v:02d}-01'
            end_v = f'{year_v:04d}-{month_v:02d}-{last_v:02d}'
            try:
                ctx_local.value = {'kind': 'exact', 'target_chat_id': int(chat_id), 'start_key': start_v, 'start_rid': 0, 'end_key': end_v, 'end_rid': 0, 'file_type': 'xlsx'}
                usd_rows, _usd_annotations = usd_builder(int(chat_id), 'usd', compact=False)
            finally:
                ctx_local.value = prev_ctx
            if usd_rows:
                prefix_offset = len(rows) + 2
                rows.extend([[], []])
                shifter = globals().get('_v193_shift_formula_rows')
                shifted_usd = shifter(usd_rows, prefix_offset) if callable(shifter) else usd_rows
                rows.extend(shifted_usd)
                validator = globals().get('_v193_validate_currency_formula_domains')
                if callable(validator):
                    validator(rows)
    except Exception as _v192_usd_exc:
        try:
            log_error(f'monthly XLSX USD append({chat_id},{month_key}): {_v192_usd_exc}')
        except Exception:
            pass
    _write_excel_by_selected_style(xlsx_path, rows, chat_id, sheet_name='Месяц', category_layout=False)
    return {'json': json_path, 'csv': csv_path, 'xlsx': xlsx_path}

def _canon_mega_upload_chat_backup_bundle__001(chat_id: int, month_key: str | None=None) -> bool:
    """MEGA-бэкап одного чата: только JSON (latest + месячный JSON)."""
    if not mega_is_configured():
        return False
    if not is_backup_to_mega_enabled(chat_id):
        return False
    try:
        save_chat_json(chat_id)
        slug = mega_chat_slug(chat_id)
        remote_chat_dir = mega_remote_chat_dir(chat_id)
        ok = True
        ok = mega_put_replace(chat_json_file(chat_id), remote_chat_dir, f'latest_{slug}.json') and ok
        month_key = month_key or current_month_key()
        month_files = save_chat_monthly_backup_files(chat_id, month_key)
        remote_month_dir = mega_remote_month_dir(month_key)
        json_month_path = month_files.get('json')
        if json_month_path:
            ok = mega_put_replace(json_month_path, remote_month_dir, os.path.basename(json_month_path)) and ok
        if ok:
            log_info(f'[MEGA] JSON-only chat backup uploaded: {get_chat_display_name(chat_id)} / {month_key}')
        return ok
    except Exception as e:
        log_error(f'[MEGA CHAT BACKUP ERROR] {chat_id}: {e}')
        return False

def _canon_mega_upload_chat_latest_json_only__001(chat_id: int) -> bool:
    """Быстрый MEGA JSON без Excel/CSV и месячного пакета."""
    if not is_backup_to_mega_enabled(chat_id) or not mega_is_configured():
        return False
    try:
        local_path = chat_json_file(chat_id)
        if not os.path.exists(local_path):
            local_path = save_chat_json_only(chat_id)
        if not local_path:
            return False
        slug = mega_chat_slug(chat_id)
        remote_chat_dir = mega_remote_chat_dir(chat_id)
        return bool(mega_put_replace(local_path, remote_chat_dir, f'latest_{slug}.json'))
    except Exception as e:
        log_error(f'mega_upload_chat_latest_json_only({chat_id}): {e}')
        return False

def _canon_schedule_config_backup_for_chats__001(*chat_ids, delay: float=3.0):
    """После изменения настроек/пересылки обновляем JSON/канал/MEGA с мягким debounce.

    Не ставим мгновенный бэкап после каждого клика/секрета: это разгружает Telegram API
    и не влияет на сохранность, потому что операции всё равно уже записаны в SQLite/data.
    """
    try:
        delay = max(float(delay or 0), BACKUP_MIN_DELAY_SECONDS)
    except Exception:
        delay = BACKUP_MIN_DELAY_SECONDS
    ids = set()
    for cid in chat_ids:
        try:
            if cid is not None:
                ids.add(int(cid))
        except Exception:
            pass
    if not ids:
        try:
            ids.update(collect_finance_chat_ids())
        except Exception:
            pass
    for cid in ids:
        try:
            schedule_backup_flush(cid, delay=delay)
        except Exception:
            pass
_delta_state_lock = threading.RLock()
_delta_record_baseline: dict[int, dict[str, str]] = {}
_delta_meta_baseline: dict[int, dict[str, str]] = {}
_delta_root_baseline: dict[str, str] = {}
_delta_pending_chats: set[int] = set()
_delta_chat_generation: dict[int, int] = defaultdict(int)
_delta_generation = 0
_delta_batch_timer = None
_delta_last_success_at = ''
_delta_last_file = ''
_delta_last_event_count = 0
_delta_last_error = ''
_global_snapshot_pending = False
_global_snapshot_last_success_monotonic = time.monotonic()
_global_snapshot_last_success_at = ''
_global_snapshot_last_change_monotonic = 0.0
_global_snapshot_capture_generation = 0
_DELTA_VOLATILE_CHAT_KEYS = {'active_windows', 'edit_wait', 'edit_target', 'categories_msg_id', 'report_window_id', 'info_msg_id', 'command_window_id', 'total_msg_id', 'balance_panel_id', 'secret_wait', 'main_window_msg_count', 'balance_panel_msg_count', 'current_view_day', 'finance_window_state', 'primary_main_window_id', 'primary_main_window_day'}
_DELTA_DERIVED_CHAT_KEYS = {'records', 'daily_records', 'daily_records_by_date', 'ars_records', 'ars_daily_records', 'ars_daily_records_by_date', 'usd_records', 'usd_daily_records', 'usd_daily_records_by_date'}
_DELTA_VOLATILE_ROOT_KEYS = {'chats', 'records', 'active_messages', 'bot_errors', '_state_meta', 'open_window_registry'}
_DELTA_ROOT_MAP_KEYS = {'forward_index', 'forward_rules', 'forward_finance', 'finance_active_chats', '_global_settings', 'csv_meta', 'chat_backup_meta', 'backup_flags', '_durable_processed_updates', 'durable_command_receipts_v150', 'gomonk_rebalance_intents_v150', 'gomonk_rebalance_receipts_v151', '_durable_reminder_edit_receipts', '_secret_notes'}
_DELTA_GLOBAL_SETTINGS_EXCLUDE = {'version_mode_snapshots', '_window_tz_v160', '_window_marker_catalog_v160', 'finance_integrity_v141', 'operation_ledger_v141'}
_DELTA_CHAT_SETTINGS_EXCLUDE = {'gomonk_rebalance_history_v150', 'gomonk_rebalance_history_v151'}

def mega_delta_remote_root() -> str:
    return f"{MEGA_BACKUP_DIR.rstrip('/')}/{MEGA_DELTA_BACKUP_DIR}"

def mega_delta_remote_day_dir(day_key: str | None=None) -> str:
    return mega_delta_remote_root().rstrip('/') + '/' + str(day_key or today_key())

def _delta_json_clone(value):
    return json.loads(json.dumps(value, ensure_ascii=False, default=str))

def _delta_hash(value) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), default=str)
    return hashlib.sha256(raw.encode('utf-8')).hexdigest()

def _delta_record_key(rec: dict) -> str:
    if not isinstance(rec, dict):
        return 'invalid:' + _delta_hash(rec)[:16]
    uid = str(rec.get('record_uid') or '').strip().upper()
    if re.fullmatch('[A-F0-9]{12}', uid):
        return f'uid:{uid}'
    for key in ('id', 'record_id'):
        value = rec.get(key)
        if value not in (None, ''):
            return f'id:{value}'
    return 'src:%s:%s:%s' % (rec.get('source_chat_id') or rec.get('chat_id') or '', rec.get('source_msg_id') or rec.get('origin_msg_id') or rec.get('msg_id') or '', rec.get('timestamp') or rec.get('day_key') or '')

def _delta_chat_meta(store: dict) -> dict:
    """Only compact chat metadata; finance arrays are carried by record upserts/deletes."""
    out = {}
    for k, v in (store or {}).items():
        if k in _DELTA_VOLATILE_CHAT_KEYS or k in _DELTA_DERIVED_CHAT_KEYS:
            continue
        if str(k) == 'settings' and isinstance(v, dict):
            v = {str(sk): sv for sk, sv in v.items() if str(sk) not in _DELTA_CHAT_SETTINGS_EXCLUDE}
        if str(k) == 'chat_lifecycle_v150' and isinstance(v, dict):
            v = {str(lk): lv for lk, lv in v.items() if str(lk) != 'history'}
        out[str(k)] = _delta_json_clone(v)
    return out

def _delta_root_patch(payload: dict) -> dict:
    """Компактный root для delta без UI-реестра и архивов профилей версий."""
    out = {str(k): _delta_json_clone(v) for k, v in (payload or {}).items() if k not in _DELTA_VOLATILE_ROOT_KEYS and k not in {'_universal_backup', '_backup_meta', '_runtime_snapshot', '_delta_restore_meta'}}
    gs = out.get('_global_settings')
    source_gs = (payload or {}).get('_global_settings') or {}
    if isinstance(gs, dict):
        out['_global_settings'] = {str(k): v for k, v in gs.items() if str(k) not in _DELTA_GLOBAL_SETTINGS_EXCLUDE}
    try:
        integ = source_gs.get('finance_integrity_v141') if isinstance(source_gs, dict) else None
        if isinstance(integ, dict):
            out['_finance_integrity_head_v189'] = {'event_seq': int(integ.get('event_seq') or 0), 'tips': _delta_json_clone(integ.get('tips') or {}), 'anchor': _delta_json_clone(integ.get('anchor') or {})}
    except Exception:
        pass
    return out

def _delta_root_signature_state(root: dict) -> dict:
    out = {}
    for key, value in (root or {}).items():
        if key in _DELTA_ROOT_MAP_KEYS and isinstance(value, dict):
            out[str(key)] = {'kind': 'map', 'entries': {str(entry): _delta_hash(entry_value) for entry, entry_value in value.items()}}
        else:
            out[str(key)] = {'kind': 'value', 'hash': _delta_hash(value)}
    return out

def _delta_baseline_from_payload(payload: dict) -> tuple[dict[int, dict[str, str]], dict[int, dict[str, str]], dict[str, str]]:
    rec_baseline: dict[int, dict[str, str]] = {}
    meta_baseline: dict[int, dict[str, str]] = {}
    for cid_s, store in ((payload or {}).get('chats', {}) or {}).items():
        try:
            cid = int(cid_s)
        except Exception:
            continue
        if not isinstance(store, dict):
            continue
        if LOWRAM_ENABLED and isinstance(store, ColdChatStore) and (not dict.__contains__(store, 'records')):
            records = SQLITE.get_cold(cid, 'records', []) or []
        else:
            records = store.get('records', []) or []
        rec_baseline[cid] = {_delta_record_key(rec): _delta_hash(rec) for rec in records if isinstance(rec, dict)}
        records = None
        meta = _delta_chat_meta(_lowram_store_meta_payload(store) if LOWRAM_ENABLED else store)
        meta_baseline[cid] = {str(key): _delta_hash(value) for key, value in meta.items()}
    root = _delta_root_patch(payload or {})
    root_baseline = _delta_root_signature_state(root)
    return (rec_baseline, meta_baseline, root_baseline)

def initialize_delta_baseline(payload: dict | None=None):
    """Начальная точка delta. Ничего не загружает и не создаёт бэкап."""
    global _delta_record_baseline, _delta_meta_baseline, _delta_root_baseline
    snapshot = payload
    if snapshot is None:
        with data_lock:
            _persist_forward_index_in_data(data)
            snapshot = data or {}
    recs, metas, root_sig = _delta_baseline_from_payload(snapshot or {})
    with _delta_state_lock:
        _delta_record_baseline = recs
        _delta_meta_baseline = metas
        _delta_root_baseline = dict(root_sig or {})

def _build_delta_payload(chat_ids: list[int], generation_map: dict[int, int]) -> tuple[dict | None, dict]:
    """Строит только изменившиеся записи и поля настроек относительно подтверждённого delta/full."""
    requested_ids = sorted({int(x) for x in chat_ids})
    with data_lock:
        _persist_forward_index_in_data(data)
        state = {str(key): _delta_json_clone(value) for key, value in (data or {}).items() if key != 'chats'}
        all_chats = (data or {}).get('chats', {}) or {}
        if LOWRAM_ENABLED:
            state['chats'] = {str(cid): _delta_json_clone(_lowram_materialize_chat_snapshot(cid, all_chats.get(str(cid), {}) or {})) for cid in requested_ids}
        else:
            state['chats'] = {str(cid): _delta_json_clone(all_chats.get(str(cid), {}) or {}) for cid in requested_ids}
    with _delta_state_lock:
        old_records = {int(cid): dict(sigs or {}) for cid, sigs in _delta_record_baseline.items()}
        old_meta = {int(cid): dict(sigs or {}) for cid, sigs in _delta_meta_baseline.items()}
        old_root = dict(_delta_root_baseline or {})
    chat_changes = {}
    next_record_sigs = {}
    next_meta_sigs = {}
    event_count = 0
    chats = state.get('chats', {}) or {}
    for cid in requested_ids:
        store = chats.get(str(cid)) or {}
        if not isinstance(store, dict):
            continue
        current_records = {_delta_record_key(rec): rec for rec in store.get('records', []) or [] if isinstance(rec, dict)}
        current_sigs = {key: _delta_hash(rec) for key, rec in current_records.items()}
        previous_sigs = old_records.get(cid, {}) or {}
        upsert_keys = [key for key, sig in current_sigs.items() if previous_sigs.get(key) != sig]
        delete_keys = [key for key in previous_sigs if key not in current_sigs]
        meta = _delta_chat_meta(store)
        current_meta_sigs = {str(key): _delta_hash(value) for key, value in meta.items()}
        previous_meta_sigs = old_meta.get(cid, {}) or {}
        changed_meta_keys = [key for key, sig in current_meta_sigs.items() if previous_meta_sigs.get(key) != sig]
        deleted_meta_keys = [key for key in previous_meta_sigs if key not in current_meta_sigs]
        if upsert_keys or delete_keys or changed_meta_keys or deleted_meta_keys:
            row = {'chat_id': cid, 'upserts': [{'key': key, 'record': current_records[key]} for key in upsert_keys], 'deletes': delete_keys, 'chat_meta_patch': {key: meta[key] for key in changed_meta_keys}, 'chat_meta_deletes': deleted_meta_keys}
            chat_changes[str(cid)] = row
            event_count += len(upsert_keys) + len(delete_keys) + len(changed_meta_keys) + len(deleted_meta_keys)
        next_record_sigs[cid] = current_sigs
        next_meta_sigs[cid] = current_meta_sigs
    root = _delta_root_patch(state)
    current_root_sigs = _delta_root_signature_state(root)
    root_patch = {}
    root_deletes = []
    root_map_patches = {}
    root_map_deletes = {}
    for key, sig_state in current_root_sigs.items():
        old_state = old_root.get(key) or {}
        if sig_state.get('kind') == 'map':
            current_entries = sig_state.get('entries') or {}
            old_entries = old_state.get('entries') or {} if old_state.get('kind') == 'map' else {}
            changed_entries = [entry for entry, sig in current_entries.items() if old_entries.get(entry) != sig]
            deleted_entries = [entry for entry in old_entries if entry not in current_entries]
            if changed_entries:
                root_map_patches[key] = {entry: root[key][entry] for entry in changed_entries}
            if deleted_entries:
                root_map_deletes[key] = deleted_entries
            event_count += len(changed_entries) + len(deleted_entries)
        elif old_state != sig_state:
            root_patch[key] = root[key]
            event_count += 1
    for key in old_root:
        if key not in current_root_sigs:
            root_deletes.append(key)
            event_count += 1
    baseline = {'record_sigs': next_record_sigs, 'meta_sigs': next_meta_sigs, 'root_sigs': current_root_sigs, 'generation_map': generation_map}
    if event_count <= 0:
        return (None, baseline)
    created_at = now_local().isoformat(timespec='microseconds')
    seq = time.time_ns()
    payload = {'kind': 'telegram_finance_bot_delta', 'schema_version': 1, 'bot_version': VERSION, 'created_at': created_at, 'delta_id': f"{now_local().strftime('%Y%m%d_%H%M%S_%f')}_{seq}", 'chat_changes': chat_changes, 'root_patch': root_patch, 'root_deletes': root_deletes, 'root_map_patches': root_map_patches, 'root_map_deletes': root_map_deletes, 'event_count': event_count, 'chat_count': len(chat_changes), 'storage_lineage_v239': globals().get('_v239_storage_lineage', lambda create=True: '')(True) if callable(globals().get('_v239_storage_lineage')) else ''}
    return (payload, baseline)

def _commit_delta_baseline(baseline: dict):
    global _delta_root_baseline
    with _delta_state_lock:
        for cid, sigs in (baseline.get('record_sigs') or {}).items():
            _delta_record_baseline[int(cid)] = dict(sigs or {})
        for cid, sigs in (baseline.get('meta_sigs') or {}).items():
            _delta_meta_baseline[int(cid)] = dict(sigs or {})
        if 'root_sigs' in baseline:
            _delta_root_baseline = dict(baseline.get('root_sigs') or {})

def _canon_delta_upload_payload__001(payload: dict) -> tuple[bool, str]:
    """Canonical compact-delta uploader. Soft warn 512 KiB; hard stop 1 MiB."""
    if not payload or not mega_is_configured():
        return (False, '')
    _gate = globals().get('v239_external_durable_write_allowed')
    if callable(_gate):
        _ok, _why = _gate()
        if not _ok:
            try:
                runtime_event('mega_delta_write_blocked_v239', str(_why)[:500], 'WARN')
            except Exception:
                pass
            return (False, '')
    try:
        soft = max(128 * 1024, int(os.getenv('MEGA_DELTA_SOFT_WARN_BYTES', str(512 * 1024)) or 512 * 1024))
        hard = max(soft + 1, int(os.getenv('MEGA_DELTA_HARD_MAX_BYTES', str(1024 * 1024)) or 1024 * 1024))
        encoded_size = len(json.dumps(payload, ensure_ascii=False, separators=(',', ':'), default=str).encode('utf-8'))
        if encoded_size > hard:

            def _sz(value):
                try:
                    return len(json.dumps(value, ensure_ascii=False, separators=(',', ':'), default=str).encode('utf-8'))
                except Exception:
                    return -1
            pieces = [f'{k}={_sz((payload or {}).get(k))}' for k in ('chat_changes', 'root_patch', 'root_map_patches', 'root_deletes', 'root_map_deletes')]
            try:
                chats = payload.get('chat_changes') or {}
                top = sorted(((str(k), _sz(v)) for k, v in chats.items()), key=lambda x: x[1], reverse=True)[:3]
                if top:
                    pieces.append('top_chats=' + ','.join((f'{k}:{v}' for k, v in top)))
            except Exception:
                pass
            log_error(f"[MEGA DELTA BLOCKED] oversized compact delta: {encoded_size} bytes > hard {hard}; {' '.join(pieces)}; full snapshot scheduled")
            _mark_global_snapshot_pending()
            return (False, '')
        if encoded_size > soft:
            try:
                now_m = time.monotonic()
                last = float(globals().get('_V189_DELTA_LAST_WARN', 0.0) or 0.0)
                if now_m - last >= 60.0:
                    globals()['_V189_DELTA_LAST_WARN'] = now_m
                    bot_journal('mega_delta_large_allowed_v189', None, f'bytes={encoded_size}; soft={soft}; hard={hard}', 'WARN')
            except Exception:
                pass
    except Exception as e:
        log_error(f'[MEGA DELTA SIZE CHECK] {e}')
    day_dir = mega_delta_remote_day_dir(str(payload.get('created_at') or today_key())[:10])
    os.makedirs(MEGA_LOCAL_TMP_DIR, exist_ok=True)
    name = f"delta_{payload.get('delta_id')}.json"
    local_path = os.path.join(MEGA_LOCAL_TMP_DIR, name)
    try:
        with open(local_path, 'w', encoding='utf-8') as fh:
            json.dump(payload, fh, ensure_ascii=False, separators=(',', ':'), default=str)
        mega_ensure_remote_path(day_dir)
        _mega_run('mega-put', [local_path, day_dir], check=True, timeout=MEGA_TIMEOUT)
        return (True, day_dir.rstrip('/') + '/' + name)
    except Exception as e:
        log_error(f'[MEGA DELTA ERROR] {e}')
        return (False, '')
    finally:
        try:
            if os.path.exists(local_path):
                os.remove(local_path)
        except Exception:
            pass
SYSTEM_SNAPSHOT_HOUR_CHOICES_V242 = (6, 12)
SYSTEM_SNAPSHOT_SETTING_KEY_V242 = 'mega_system_snapshot_hours_v242'

def system_snapshot_hours_v242() -> int:
    """Persisted owner choice for the rare full SQLite system generation."""
    try:
        env = str(os.getenv('MEGA_SYSTEM_SNAPSHOT_HOURS', '') or '').strip()
        if env:
            raw = int(float(env))
            return min(SYSTEM_SNAPSHOT_HOUR_CHOICES_V242, key=lambda x: abs(x - raw))
    except Exception:
        pass
    try:
        gs = (data or {}).setdefault('_global_settings', {})
        raw = int(gs.get(SYSTEM_SNAPSHOT_SETTING_KEY_V242, 6) or 6)
    except Exception:
        raw = 6
    return min(SYSTEM_SNAPSHOT_HOUR_CHOICES_V242, key=lambda x: abs(x - raw))

def system_snapshot_interval_seconds_v242() -> float:
    return float(system_snapshot_hours_v242() * 3600)

def _system_snapshot_elapsed_v242(now_mono: float | None=None) -> float:
    """Age of the active canonical generation, including generation restored on this deploy."""
    now_mono = time.monotonic() if now_mono is None else float(now_mono)
    elapsed = max(0.0, now_mono - float(_global_snapshot_last_success_monotonic or now_mono))
    created = str(_global_snapshot_last_success_at or '')
    if not created:
        try:
            meta = SQLITE.get_meta('db_snapshot', 'main', {}) or {}
            created = str(meta.get('created_at') or '')
        except Exception:
            created = ''
    if created:
        try:
            wall_age = max(0.0, time.time() - float(_parse_iso_timestamp(created) or 0.0))
            if wall_age < 365 * 86400:
                elapsed = max(elapsed, wall_age)
        except Exception:
            pass
    return float(elapsed)

def set_system_snapshot_hours_v242(hours: int) -> int:
    """Set 6/12h interval, persist it, and reschedule a pending system generation."""
    try:
        raw = int(hours)
    except Exception:
        raw = 6
    value = min(SYSTEM_SNAPSHOT_HOUR_CHOICES_V242, key=lambda x: abs(x - raw))
    try:
        gs = data.setdefault('_global_settings', {})
        gs[SYSTEM_SNAPSHOT_SETTING_KEY_V242] = int(value)
        gs['mega_system_snapshot_changed_at_v242'] = now_local().isoformat(timespec='seconds')
        try:
            save_data(data, root_only=True)
        except TypeError:
            save_data(data)
    except Exception as exc:
        try:
            log_error(f'system snapshot interval persist v242: {exc}')
        except Exception:
            pass
    try:
        fn = globals().get('schedule_delta_backup')
        if callable(fn):
            fn(int(globals().get('OWNER_ID') or 0) or None, delay=0.8, reason='settings:system_snapshot_interval_v242')
    except Exception:
        pass
    try:
        DELAYED_SCHEDULER.cancel('mega-global-quiet-v90')
        DELAYED_SCHEDULER.cancel('mega-global-max-v90')
        if bool(globals().get('_global_snapshot_pending', False)):
            _mark_global_snapshot_pending()
    except Exception:
        pass
    try:
        bot_journal('mega_system_snapshot_interval_v242', int(globals().get('OWNER_ID') or 0) or None, f'hours={value}')
    except Exception:
        pass
    return int(value)

def toggle_system_snapshot_hours_v242() -> int:
    return set_system_snapshot_hours_v242(12 if system_snapshot_hours_v242() == 6 else 6)

def _mark_global_snapshot_pending():
    """v242: mark the canonical SQLite generation dirty and schedule only the 6/12h system checkpoint.

    The old 10-minute quiet snapshot is intentionally removed.  Small per-chat/business
    shard deltas are the durability layer between system generations.
    """
    global _global_snapshot_pending, _global_snapshot_last_change_monotonic
    if RESTORE_GUARD_ACTIVE or not mega_is_configured():
        return
    try:
        switch = globals().get('v176_process_enabled')
        if callable(switch) and (not switch('full_global')):
            with _delta_state_lock:
                _global_snapshot_pending = True
                _global_snapshot_last_change_monotonic = time.monotonic()
            return
    except Exception:
        pass
    now_mono = time.monotonic()
    interval = max(300.0, float(system_snapshot_interval_seconds_v242()))
    with _delta_state_lock:
        _global_snapshot_pending = True
        _global_snapshot_last_change_monotonic = now_mono
        elapsed = _system_snapshot_elapsed_v242(now_mono)
        wait = max(1.0, interval - elapsed)

    def _system_fire():
        with _delta_state_lock:
            pending = _global_snapshot_pending
        if pending:
            _submit_global_snapshot_v90('system_interval_v242')
    DELAYED_SCHEDULER.cancel('mega-global-quiet-v90')
    DELAYED_SCHEDULER.cancel('mega-global-max-v90')
    DELAYED_SCHEDULER.schedule('mega-global-max-v90', wait, _system_fire)

def _submit_global_snapshot_v90(reason: str):
    if RESTORE_GUARD_ACTIVE:
        return
    try:
        busy = any((int((pool.stats() or {}).get('active', 0) or 0) + int((pool.stats() or {}).get('pending', 0) or 0) > 0 for pool in (WEBHOOK_TASK_POOL, FAST_UI_TASK_POOL, UI_TASK_POOL, FINANCE_TASK_POOL)))
    except Exception:
        busy = False
    if busy:
        DELAYED_SCHEDULER.schedule('mega-global-user-idle-v190', 5.0, _submit_global_snapshot_v90, reason)
        return

    def _job():
        ok = mega_upload_latest_global_backup()
        if not ok:
            DELAYED_SCHEDULER.schedule('mega-global-retry-v90', BACKUP_BUSY_RETRY_SECONDS, _submit_global_snapshot_v90, 'retry')
    if not BACKUP_TASK_POOL.submit('mega-global-v90', _job):
        log_error(f'GLOBAL v90 QUEUE FULL ({reason}), RETRY')
        DELAYED_SCHEDULER.schedule('mega-global-retry-v90', BACKUP_BUSY_RETRY_SECONDS, _submit_global_snapshot_v90, 'queue_retry')

def _canon_run_delta_batch__001():
    global _delta_last_success_at, _delta_last_file, _delta_last_event_count, _delta_last_error
    with _delta_state_lock:
        chat_ids = sorted(_delta_pending_chats)
        generation_map = {cid: int(_delta_chat_generation.get(cid, 0)) for cid in chat_ids}
    if not chat_ids:
        return True
    payload, baseline = _build_delta_payload(chat_ids, generation_map)
    if payload is not None:
        ok, remote_path = _delta_upload_payload(payload)
        if not ok:
            _delta_last_error = 'delta upload failed'
            return False
        _delta_last_success_at = str(payload.get('created_at') or '')
        _delta_last_file = remote_path
        _delta_last_event_count = int(payload.get('event_count', 0) or 0)
        _delta_last_error = ''
        log_info(f"[MEGA DELTA] uploaded {remote_path}; events={_delta_last_event_count}; chats={payload.get('chat_count')}")
        _mark_global_snapshot_pending()
    _commit_delta_baseline(baseline)
    with _delta_state_lock:
        for cid, gen in generation_map.items():
            if int(_delta_chat_generation.get(cid, 0)) == int(gen):
                _delta_pending_chats.discard(cid)
        more_pending = bool(_delta_pending_chats)
    with timer_lock:
        for cid in generation_map:
            _quick_backup_timers.pop(int(cid), None)
            _quick_backup_dirty_chats.discard(int(cid))
    if more_pending:
        schedule_delta_backup(None, delay=1.0, reason='changes_during_upload')
    return True

def _canon_schedule_delta_backup__001(chat_id: int | None, delay: float | None=None, reason: str='change'):
    """Общий debounce разных чатов: несколько изменений попадают в один маленький delta."""
    global _delta_generation, _delta_batch_timer
    if RESTORE_GUARD_ACTIVE or not mega_is_configured():
        return False
    _gate = globals().get('v239_external_durable_write_allowed')
    if callable(_gate):
        _ok, _why = _gate()
        if not _ok:
            try:
                runtime_event('mega_delta_schedule_blocked_v239', str(_why)[:500], 'WARN')
            except Exception:
                pass
            return False
    with _delta_state_lock:
        _delta_generation += 1
        if chat_id is not None:
            cid = int(chat_id)
            _delta_pending_chats.add(cid)
            _delta_chat_generation[cid] = _delta_generation
        elif not _delta_pending_chats:
            return False
    if delay is None:
        delay = MEGA_DELTA_PRIORITY_DELAY_SECONDS if mega_backup_priority_enabled() else MEGA_DELTA_DELAY_SECONDS
    delay = max(0.5, float(delay))

    def _fire():

        def _job():
            if not _run_delta_batch():
                schedule_delta_backup(None, delay=BACKUP_BUSY_RETRY_SECONDS, reason='upload_retry')
        if not DELTA_TASK_POOL.submit('mega-delta-v90', _job):
            log_error('DELTA QUEUE FULL, RETRY')
            schedule_delta_backup(None, delay=BACKUP_BUSY_RETRY_SECONDS, reason='queue_retry')
    DELAYED_SCHEDULER.cancel('mega-delta-batch-v90')
    _delta_batch_timer = DELAYED_SCHEDULER.schedule('mega-delta-batch-v90', delay, _fire)
    return True

def _canon_persist_critical_delta_now__001(chat_id: int) -> bool:
    """Синхронно грузит маленький delta для критической операции.

    Используется после финансовой бот-пересылки: сообщение уже отправлено в Telegram,
    поэтому перед возвратом из обработчика состояние должно оказаться не только в
    локальной SQLite, но и в MEGA. Это защищает даже от deploy через секунду.
    """
    global _delta_generation
    if RESTORE_GUARD_ACTIVE or not mega_is_configured():
        return False
    cid = int(chat_id)
    with CRITICAL_DELTA_LOCK:
        with _delta_state_lock:
            _delta_generation += 1
            _delta_pending_chats.add(cid)
            _delta_chat_generation[cid] = _delta_generation
        try:
            DELAYED_SCHEDULER.cancel('mega-delta-batch-v90')
        except Exception:
            pass
        ok = bool(_run_delta_batch())
        if not ok:
            log_error(f'[CRITICAL DELTA] immediate MEGA persistence failed for chat={cid}')
        return ok

def _apply_delta_payload_to_state(state: dict, delta: dict) -> dict:
    if not isinstance(state, dict) or not isinstance(delta, dict):
        return state
    root_patch = delta.get('root_patch') or {}
    for key in delta.get('root_deletes') or []:
        if key not in _DELTA_VOLATILE_ROOT_KEYS:
            state.pop(str(key), None)
    for key, value in root_patch.items():
        if key not in _DELTA_VOLATILE_ROOT_KEYS:
            state[key] = _delta_json_clone(value)
    for key, entries in (delta.get('root_map_patches') or {}).items():
        target = state.setdefault(str(key), {})
        if not isinstance(target, dict):
            target = {}
            state[str(key)] = target
        for entry, value in (entries or {}).items():
            target[str(entry)] = _delta_json_clone(value)
    for key, entries in (delta.get('root_map_deletes') or {}).items():
        target = state.get(str(key))
        if isinstance(target, dict):
            for entry in entries or []:
                target.pop(str(entry), None)
    chats = state.setdefault('chats', {})
    for cid_s, change in (delta.get('chat_changes') or {}).items():
        if not isinstance(change, dict):
            continue
        store = chats.setdefault(str(cid_s), {})
        meta = change.get('chat_meta')
        if isinstance(meta, dict):
            for key, value in meta.items():
                store[key] = _delta_json_clone(value)
        for key in change.get('chat_meta_deletes') or []:
            store.pop(str(key), None)
        for key, value in (change.get('chat_meta_patch') or {}).items():
            store[str(key)] = _delta_json_clone(value)
        current = {_delta_record_key(rec): rec for rec in store.get('records', []) or [] if isinstance(rec, dict)}
        for key in change.get('deletes') or []:
            current.pop(str(key), None)
        for item in change.get('upserts') or []:
            if not isinstance(item, dict) or not isinstance(item.get('record'), dict):
                continue
            current[str(item.get('key') or _delta_record_key(item['record']))] = _delta_json_clone(item['record'])
        records = sorted(current.values(), key=record_sort_key)
        daily = defaultdict(list)
        for rec in records:
            dk = _record_day_key(rec)
            rec['day_key'] = dk
            daily[dk].append(rec)
        store['records'] = records
        store['daily_records'] = {dk: sorted(rows, key=record_sort_key) for dk, rows in sorted(daily.items())}
        store['balance'] = sum((float(rec.get('amount', 0) or 0) for rec in records))
    state['overall_balance'] = sum((float((s or {}).get('balance', 0) or 0) for s in chats.values() if isinstance(s, dict)))
    state['records'] = []
    state['_delta_restore_meta'] = {'last_delta_id': delta.get('delta_id'), 'last_delta_created_at': delta.get('created_at'), 'last_delta_event_count': delta.get('event_count')}
    return state

def _canon_delta_remote_candidates_after__001(created_at: str, limit: int | None=None) -> list[str]:
    rows = _mega_find_remote_files(mega_delta_remote_root(), 'delta_*.json')
    base_ts = _parse_iso_timestamp(created_at)
    selected = []
    for path in sorted(rows):
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

def merge_global_snapshot_with_mega_deltas(local_global_path: str) -> tuple[str, int]:
    """Скачивает и применяет immutable delta, созданные после full snapshot."""
    base = _load_json(local_global_path, {}) or {}
    if not _global_payload_is_structurally_valid(base):
        return (local_global_path, 0)
    created_at = str((base.get('_universal_backup') or {}).get('created_at') or (base.get('_backup_meta') or {}).get('created_at') or '')
    remote_rows = _delta_remote_candidates_after(created_at)
    applied = 0
    local_map = {}
    cleanup_dirs = []
    try:
        local_map, cleanup_dirs = _v177_download_remote_json_batch(remote_rows)
        for remote_path in remote_rows:
            local_delta = local_map.get(remote_path)
            if not local_delta:
                continue
            delta = _load_json(local_delta, {}) or {}
            if delta.get('kind') != 'telegram_finance_bot_delta':
                continue
            if _parse_iso_timestamp(delta.get('created_at')) <= _parse_iso_timestamp(created_at):
                continue
            _apply_delta_payload_to_state(base, delta)
            applied += 1
    finally:
        for folder in sorted(set(cleanup_dirs), key=len, reverse=True):
            try:
                shutil.rmtree(folder, ignore_errors=True)
            except Exception:
                pass
    if not applied:
        return (local_global_path, 0)
    merged = os.path.join(MEGA_LOCAL_TMP_DIR, f'merged_global_with_{applied}_deltas.json')
    _save_json(merged, base)
    log_info(f'[MEGA RESTORE] merged full snapshot + {applied} delta files')
    return (merged, applied)

def _canon_prune_delta_files_after_full_snapshot__001():
    """v190 bounded delta retention.

    The verified active SQLite generation already contains all state up to its capture.
    Keep only the newest MEGA_DELTA_KEEP_FILES deltas as an independent short rollback
    trail instead of letting thousands of tiny files grow forever.
    """
    try:
        rows = _mega_find_remote_files(mega_delta_remote_root(), 'delta_*.json')
        keep = max(30, int(MEGA_DELTA_KEEP_FILES))
        removed = 0
        for remote_path in rows[keep:]:
            try:
                res = _mega_run('mega-rm', [remote_path], check=False, timeout=30)
                if res.returncode == 0:
                    removed += 1
            except Exception:
                pass
        if removed:
            try:
                bot_journal('mega_delta_pruned_v190', None, f'removed={removed}; keep={keep}')
            except Exception:
                pass
        return removed
    except Exception as exc:
        try:
            log_error(f'delta prune v190: {exc}')
        except Exception:
            pass
        return 0

def delta_status_text() -> str:
    with _delta_state_lock:
        pending = len(_delta_pending_chats)
        global_pending = _global_snapshot_pending
        since_full = max(0, int(time.monotonic() - _global_snapshot_last_success_monotonic))
    return f"🧩 Delta / snapshots v91\nОжидают чаты: {pending}\nПоследний delta: {_delta_last_success_at or '-'}\nСобытий в нём: {_delta_last_event_count}\nФайл: {_delta_last_file or '-'}\nОшибка: {_delta_last_error or '-'}\nSQLite snapshot ожидается: {('да' if global_pending else 'нет')}\nПосле последнего full: {since_full} сек.\nSYSTEM generation: каждые {system_snapshot_hours_v242()} ч. при наличии изменений; short-idle snapshot отключён.\n" + (mega_traffic_stats_text(compact=True) if 'mega_traffic_stats_text' in globals() else '')

def _snapshot_runtime_state_for_backup(payload: dict) -> dict:
    """Минимальный стабильный runtime-слой, необходимый для восстановления между версиями."""
    return {'backup_flags': json.loads(json.dumps(payload.get('backup_flags', {}) or {}, ensure_ascii=False, default=str)), 'finance_active_chats': json.loads(json.dumps(payload.get('finance_active_chats', {}) or {}, ensure_ascii=False, default=str)), 'forward_index': json.loads(json.dumps(payload.get('forward_index', {}) or {}, ensure_ascii=False, default=str)), 'global_settings': json.loads(json.dumps(payload.get('_global_settings', {}) or {}, ensure_ascii=False, default=str)), 'csv_meta': json.loads(json.dumps(payload.get('csv_meta', {}) or {}, ensure_ascii=False, default=str)), 'chat_backup_meta': json.loads(json.dumps(payload.get('chat_backup_meta', {}) or {}, ensure_ascii=False, default=str))}

def _v177_legacy_0077_make_global_backup_payload() -> dict:
    """Универсальный полный JSON: данные, настройки и индекс старых пересланных сообщений."""
    with data_lock:
        _persist_forward_index_in_data(data)
        payload = json.loads(json.dumps(data or {}, ensure_ascii=False, default=str))
    payload.setdefault('chats', {})
    payload.setdefault('forward_rules', data.get('forward_rules', {}) if isinstance(data, dict) else {})
    payload.setdefault('forward_finance', data.get('forward_finance', {}) if isinstance(data, dict) else {})
    try:
        for _cid, _store in (payload.get('chats', {}) or {}).items():
            if isinstance(_store, dict):
                _store['records'] = backup_records_list(_store.get('records', []))
                _store['daily_records_by_date'] = {fmt_date_backup(k): backup_records_list(v) for k, v in (_store.get('daily_records', {}) or {}).items()}
    except Exception as e:
        log_error(f'make_global_backup_payload date annotate: {e}')
    created_at = now_local().isoformat(timespec='seconds')
    payload['_universal_backup'] = {'kind': UNIVERSAL_BACKUP_KIND, 'schema_version': UNIVERSAL_BACKUP_SCHEMA_VERSION, 'bot_version': VERSION, 'created_at': created_at, 'restore_mode': 'replace_full_state', 'contains': ['all_chats', 'records', 'settings', 'global_settings', 'forward_rules', 'forward_finance', 'forward_index', 'secret_messages', 'backup_metadata']}
    payload['_runtime_snapshot'] = _snapshot_runtime_state_for_backup(payload)
    payload['_backup_meta'] = {'kind': 'mega_latest_global', 'version': VERSION, 'schema_version': UNIVERSAL_BACKUP_SCHEMA_VERSION, 'created_at': created_at, 'chat_count': len(payload.get('chats', {}) or {}), 'finance_active_chats': payload.get('finance_active_chats', {}), 'forward_rules_count': sum((len(v or {}) for v in (payload.get('forward_rules', {}) or {}).values())), 'forward_finance_count': sum((len(v or {}) for v in (payload.get('forward_finance', {}) or {}).values())), 'forward_index_count': len(payload.get('forward_index', {}) or {}), 'note': 'Универсальный полный JSON: все чаты, записи, настройки, секреты, пересылка и индекс сообщений.'}
    return payload
try:
    _v177_legacy_0077_make_global_backup_payload.__name__ = 'make_global_backup_payload'
except Exception:
    pass

def save_global_backup_snapshot(path: str) -> str:
    """Атомарно создаёт локальный universal snapshot."""
    payload = make_global_backup_payload()
    tmp = path + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
        f.flush()
        try:
            os.fsync(f.fileno())
        except Exception:
            pass
    os.replace(tmp, path)
    return path

def _global_payload_stats(payload: dict, path: str | None=None) -> dict:
    chats = payload.get('chats', {}) if isinstance(payload, dict) else {}
    if not isinstance(chats, dict):
        chats = {}
    record_count = 0
    nonempty_chats = 0
    for store in chats.values():
        if not isinstance(store, dict):
            continue
        recs = store.get('records') or []
        if isinstance(recs, list):
            record_count += len(recs)
            if recs:
                nonempty_chats += 1
    try:
        size_bytes = os.path.getsize(path) if path and os.path.exists(path) else len(json.dumps(payload, ensure_ascii=False))
    except Exception:
        size_bytes = 0
    universal = payload.get('_universal_backup') or {}
    return {'size_bytes': int(size_bytes), 'chat_count': len(chats), 'nonempty_chats': nonempty_chats, 'record_count': int(record_count), 'schema_version': int(universal.get('schema_version') or 0), 'created_at': str(universal.get('created_at') or (payload.get('_backup_meta') or {}).get('created_at') or ''), 'is_universal': universal.get('kind') == UNIVERSAL_BACKUP_KIND}

def _global_payload_is_structurally_valid(payload: dict) -> bool:
    if not isinstance(payload, dict):
        return False
    if not isinstance(payload.get('chats'), dict):
        return False
    universal = payload.get('_universal_backup') or {}
    return universal.get('kind') == UNIVERSAL_BACKUP_KIND or '_backup_meta' in payload

def _global_candidate_rejection(candidate: dict, current: dict | None=None) -> str:
    """Возвращает причину отказа, если кандидат похож на обнулённую/обрезанную базу."""
    if not candidate.get('is_universal'):
        return 'candidate is not universal'
    if candidate.get('size_bytes', 0) < MEGA_GLOBAL_MIN_SAFE_BYTES and candidate.get('record_count', 0) == 0:
        return f"candidate too small/empty: {candidate.get('size_bytes')} bytes"
    if current:
        old_records = int(current.get('record_count', 0) or 0)
        new_records = int(candidate.get('record_count', 0) or 0)
        old_size = int(current.get('size_bytes', 0) or 0)
        new_size = int(candidate.get('size_bytes', 0) or 0)
        old_chats = int(current.get('chat_count', 0) or 0)
        new_chats = int(candidate.get('chat_count', 0) or 0)
        if old_records >= 10 and new_records < old_records * (1.0 - MEGA_GLOBAL_MAX_RECORD_DROP):
            return f'record drop blocked: {old_records} -> {new_records}'
        if old_size >= 100000 and new_size < old_size * 0.5:
            return f'size drop blocked: {old_size} -> {new_size}'
        if old_chats >= 2 and new_chats < max(1, int(old_chats * 0.5)):
            return f'chat drop blocked: {old_chats} -> {new_chats}'
    return ''

def restore_guard_manual_override_enabled() -> bool:
    """Постоянный owner override: разрешить работу/автобэкапы даже без restore snapshot."""
    try:
        return bool(SQLITE.get_meta('safety', 'restore_guard_manual_override', True))
    except Exception:
        return False

def set_restore_guard_manual_override(enabled: bool):
    try:
        SQLITE.set_meta('safety', 'restore_guard_manual_override', bool(enabled))
    except Exception as e:
        log_error(f'set_restore_guard_manual_override: {e}')

def restore_guard_status_text() -> str:
    return f"🛡 Restore guard: {('✅ ВКЛ' if RESTORE_GUARD_ACTIVE else '⬜ ВЫКЛ')}\nРучное отключение: {('✅ ВКЛ' if restore_guard_manual_override_enabled() else '⬜ ВЫКЛ')}\nПричина: {RESTORE_GUARD_REASON or '-'}\nАвтобэкапы: {('заблокированы' if RESTORE_GUARD_ACTIVE else 'разрешены')}\nMEGA настроена: {('ДА' if mega_is_configured() else 'НЕТ')}"

def disable_restore_guard_and_enable_mega_backups() -> int:
    """Явное решение владельца: снять аварийный guard и включить MEGA auto-backup во всех известных чатах."""
    set_restore_guard_manual_override(True)
    _clear_restore_guard()
    count = 0
    for cid in collect_all_known_chat_ids(include_owner=True):
        try:
            settings = _ensure_backup_settings(int(cid))
            settings['auto_backup_to_mega_enabled'] = True
            settings['auto_backup_enabled'] = True
            count += 1
        except Exception:
            pass
    try:
        save_data(data, full=True)
    except Exception as e:
        log_error(f'disable_restore_guard_and_enable_mega_backups save: {e}')
    for cid in collect_all_known_chat_ids(include_owner=True):
        try:
            schedule_backup_flush(int(cid), delay=BACKUP_MIN_DELAY_SECONDS)
        except Exception:
            pass
    return count

def _set_restore_guard(reason: str):
    global RESTORE_GUARD_ACTIVE, RESTORE_GUARD_REASON
    if restore_guard_manual_override_enabled():
        RESTORE_GUARD_ACTIVE = False
        RESTORE_GUARD_REASON = ''
        log_info(f"[RESTORE GUARD BYPASSED BY OWNER] {str(reason or '')[:500]}")
        return
    RESTORE_GUARD_ACTIVE = True
    RESTORE_GUARD_REASON = str(reason or 'restore not confirmed')[:1000]
    log_error(f'[RESTORE GUARD ON] {RESTORE_GUARD_REASON}')

def _clear_restore_guard():
    global RESTORE_GUARD_ACTIVE, RESTORE_GUARD_REASON
    RESTORE_GUARD_ACTIVE = False
    RESTORE_GUARD_REASON = ''

def mega_history_remote_dir() -> str:
    return f"{MEGA_BACKUP_DIR.rstrip('/')}/{MEGA_HISTORY_BACKUP_DIR}"

def mega_download_global_named(remote_name: str) -> str | None:
    if not mega_is_configured():
        return None
    try:
        mega_login_if_needed()
        restore_dir = tempfile.mkdtemp(prefix='mega_restore_')
        remote_file = mega_remote_file_path(remote_name)
        _mega_run('mega-get', [remote_file, restore_dir], check=True, timeout=MEGA_TIMEOUT)
        local_path = os.path.join(restore_dir, os.path.basename(remote_name))
        if not os.path.exists(local_path):
            for name in os.listdir(restore_dir):
                if name.lower().endswith('.json'):
                    local_path = os.path.join(restore_dir, name)
                    break
        return local_path if os.path.exists(local_path) else None
    except Exception as e:
        log_error(f'[MEGA RESTORE DOWNLOAD ERROR] {remote_name}: {e}')
        return None

def mega_download_latest_global_backup() -> str | None:
    return mega_download_global_named(MEGA_LATEST_GLOBAL_NAME)

def _mega_history_candidates(limit: int=20) -> list[str]:
    """Возвращает последние immutable global snapshots из MEGA history."""
    exe = shutil.which('mega-find')
    if not exe or not mega_is_configured():
        return []
    try:
        mega_ensure_remote_path(mega_history_remote_dir())
        res = _mega_run('mega-find', [mega_history_remote_dir(), '--pattern=global_*.json', '--type=f'], check=False, timeout=60)
        rows = [x.strip() for x in (res.stdout or '').splitlines() if x.strip().lower().endswith('.json')]
        return sorted(set(rows), reverse=True)[:max(1, int(limit))]
    except Exception as e:
        log_error(f'_mega_history_candidates: {e}')
        return []

def _mega_download_remote_path(remote_path: str) -> str | None:
    try:
        restore_dir = tempfile.mkdtemp(prefix='mega_history_restore_')
        _mega_run('mega-get', [remote_path, restore_dir], check=True, timeout=MEGA_TIMEOUT)
        base = os.path.basename(remote_path.rstrip('/'))
        local = os.path.join(restore_dir, base)
        if os.path.exists(local):
            return local
        for name in os.listdir(restore_dir):
            if name.lower().endswith('.json'):
                return os.path.join(restore_dir, name)
    except Exception as e:
        log_error(f'_mega_download_remote_path({remote_path}): {e}')
    return None
try:
    GRACEFUL_SHUTDOWN_SECONDS = max(5.0, min(240.0, float(os.getenv('GRACEFUL_SHUTDOWN_SECONDS', '25') or '25')))
except Exception:
    GRACEFUL_SHUTDOWN_SECONDS = 25.0
try:
    BOOT_SYNC_RECOVERY_SECONDS = max(5.0, min(180.0, float(os.getenv('BOOT_SYNC_RECOVERY_SECONDS', '45') or '45')))
except Exception:
    BOOT_SYNC_RECOVERY_SECONDS = 45.0
try:
    BOOT_RECOVERY_RETRY_SECONDS = max(1.0, min(60.0, float(os.getenv('BOOT_RECOVERY_RETRY_SECONDS', '5') or '5')))
except Exception:
    BOOT_RECOVERY_RETRY_SECONDS = 5.0
try:
    RUNTIME_WATCHER_HISTORY_KEEP = max(20, min(500, int(os.getenv('RUNTIME_WATCHER_HISTORY_KEEP', '100') or '100')))
except Exception:
    RUNTIME_WATCHER_HISTORY_KEEP = 100
try:
    RUNTIME_WATCHER_HEARTBEAT_SECONDS = max(120.0, min(3600.0, float(os.getenv('RUNTIME_WATCHER_HEARTBEAT_SECONDS', '900') or '900')))
except Exception:
    RUNTIME_WATCHER_HEARTBEAT_SECONDS = 900.0
try:
    RUNTIME_WATCHER_SLOT_COUNT = max(2, min(5, int(os.getenv('RUNTIME_WATCHER_SLOT_COUNT', '3') or '3')))
except Exception:
    RUNTIME_WATCHER_SLOT_COUNT = 3
_RUNTIME_LOCK = threading.RLock()
_RUNTIME_SHUTDOWN_LOCK = threading.Lock()
_RUNTIME_UPLOAD_LOCK = threading.Lock()
_RUNTIME_EVENTS = deque(maxlen=40)
_RUNTIME_PREVIOUS = {}
_RUNTIME_HEARTBEAT_OK_SEQ = 0
_RUNTIME_REMOTE_DIR_NAME = 'runtime'
_RUNTIME_LATEST_NAME = 'runtime_latest.json'
_RUNTIME_STARTED_MONO = time.monotonic()
_RUNTIME_STARTED_AT = now_local().isoformat(timespec='seconds')
_RUNTIME_STATE = {'phase': 'module_loaded', 'ready': False, 'shutting_down': False, 'started_at': _RUNTIME_STARTED_AT, 'ready_at': '', 'boot_completed_at': '', 'boot_duration_seconds': None, 'restore_attempted': False, 'restore_ok': None, 'restore_detail': '', 'task_recovery_started_at': '', 'task_recovery_finished_at': '', 'task_recovery_remaining': 0, 'task_recovery_recovered': 0, 'last_webhook_at': '', 'last_webhook_update_id': '', 'last_webhook_type': '', 'last_webhook_chat_id': None, 'webhook_received': 0, 'webhook_blocked_boot': 0, 'webhook_blocked_shutdown': 0, 'shutdown_started_at': '', 'shutdown_finished_at': '', 'shutdown_signal': '', 'shutdown_drain_ok': None, 'shutdown_delta_ok': None, 'last_error': '', 'previous_reason': 'first_seen', 'previous_snapshot_source': '', 'last_runtime_snapshot_ok_at': '', 'last_runtime_snapshot_error': '', 'last_runtime_slot': '', 'last_runtime_slot_at': '', 'runtime_slot_failures': 0, 'fatal_main_exception': '', 'fatal_thread_exception': ''}

def _runtime_render_env() -> dict:
    keys = ('RENDER_INSTANCE_ID', 'RENDER_GIT_COMMIT', 'RENDER_SERVICE_ID', 'RENDER_SERVICE_NAME', 'RENDER_SERVICE_TYPE', 'RENDER_REGION', 'RENDER_EXTERNAL_HOSTNAME')
    return {k: str(os.getenv(k, '') or '') for k in keys}

def runtime_event(name: str, detail: str='', level: str='INFO'):
    row = {'ts': now_local().isoformat(timespec='milliseconds'), 'event': str(name or 'event'), 'detail': str(detail or '')[:1000], 'level': str(level or 'INFO')[:16]}
    with _RUNTIME_LOCK:
        _RUNTIME_EVENTS.append(row)
        _RUNTIME_STATE['last_event_at'] = row['ts']
        _RUNTIME_STATE['last_event'] = row['event']
        if level.upper() in {'ERROR', 'CRITICAL'}:
            _RUNTIME_STATE['last_error'] = row['detail']
    try:
        bot_journal('runtime_' + row['event'], None, row['detail'], level)
    except Exception:
        pass

def runtime_set_phase(phase: str, detail: str=''):
    with _RUNTIME_LOCK:
        _RUNTIME_STATE['phase'] = str(phase)
    runtime_event('phase', f'{phase}: {detail}' if detail else str(phase))

def runtime_is_ready() -> bool:
    with _RUNTIME_LOCK:
        return bool(_RUNTIME_STATE.get('ready')) and (not bool(_RUNTIME_STATE.get('shutting_down')))

def runtime_is_shutting_down() -> bool:
    with _RUNTIME_LOCK:
        return bool(_RUNTIME_STATE.get('shutting_down'))

def _runtime_memory_stats() -> dict:
    out = {'rss_mb': None, 'peak_rss_mb': None, 'limit_mb': None, 'rss_percent_limit': None, 'container_current_mb': None, 'container_peak_mb': None, 'container_percent_limit': None, 'effective_mb': None, 'cgroup_events': {}}
    try:
        status = Path('/proc/self/status').read_text(errors='ignore') if os.path.exists('/proc/self/status') else ''
        for line in status.splitlines():
            if line.startswith('VmRSS:'):
                out['rss_mb'] = round(float(line.split()[1]) / 1024.0, 1)
            elif line.startswith('VmHWM:'):
                out['peak_rss_mb'] = round(float(line.split()[1]) / 1024.0, 1)
    except Exception:
        pass

    def _read_cgroup_number(paths):
        for candidate in paths:
            try:
                if not os.path.exists(candidate):
                    continue
                raw = Path(candidate).read_text(errors='ignore').strip()
                if not raw or raw.lower() == 'max':
                    continue
                value = int(raw)
                if 0 < value < 1 << 60:
                    return value
            except Exception:
                continue
        return None
    try:
        limit = _read_cgroup_number(('/sys/fs/cgroup/memory.max', '/sys/fs/cgroup/memory/memory.limit_in_bytes'))
        current = _read_cgroup_number(('/sys/fs/cgroup/memory.current', '/sys/fs/cgroup/memory/memory.usage_in_bytes'))
        peak = _read_cgroup_number(('/sys/fs/cgroup/memory.peak', '/sys/fs/cgroup/memory/memory.max_usage_in_bytes'))
        if limit is not None:
            out['limit_mb'] = round(limit / 1024.0 / 1024.0, 1)
        if current is not None:
            out['container_current_mb'] = round(current / 1024.0 / 1024.0, 1)
        if peak is not None:
            out['container_peak_mb'] = round(peak / 1024.0 / 1024.0, 1)
        if out.get('limit_mb'):
            if out.get('rss_mb') is not None:
                out['rss_percent_limit'] = round(100.0 * float(out['rss_mb']) / float(out['limit_mb']), 1)
            if out.get('container_current_mb') is not None:
                out['container_percent_limit'] = round(100.0 * float(out['container_current_mb']) / float(out['limit_mb']), 1)
        out['effective_mb'] = out.get('container_current_mb') if out.get('container_current_mb') is not None else out.get('rss_mb')
        events_path = '/sys/fs/cgroup/memory.events'
        if os.path.exists(events_path):
            events = {}
            for line in Path(events_path).read_text(errors='ignore').splitlines():
                parts = line.split()
                if len(parts) == 2:
                    try:
                        events[str(parts[0])] = int(parts[1])
                    except Exception:
                        pass
            out['cgroup_events'] = events
        else:
            fail_path = '/sys/fs/cgroup/memory/memory.failcnt'
            if os.path.exists(fail_path):
                out['cgroup_events'] = {'failcnt': int(Path(fail_path).read_text(errors='ignore').strip() or 0)}
    except Exception:
        pass
    return out

def _runtime_memory_pressure() -> dict:
    mem = _runtime_memory_stats()
    effective = mem.get('effective_mb') if mem.get('effective_mb') is not None else mem.get('rss_mb')
    pct = mem.get('container_percent_limit') if mem.get('container_percent_limit') is not None else mem.get('rss_percent_limit')
    level_fn = globals().get('memory_level')
    if callable(level_fn):
        try:
            level = level_fn({'effective_mb': effective, 'container_percent': pct, 'python_rss_mb': mem.get('rss_mb'), 'container_current_mb': mem.get('container_current_mb')})
        except Exception:
            level = 'normal'
    else:
        level = 'normal'
        try:
            used = float(effective or 0.0)
            p = float(pct or 0.0)
            if used >= 440.0 or p >= 86.0:
                level = 'emergency'
            elif used >= 400.0 or p >= 78.0:
                level = 'critical'
            elif used >= 350.0 or p >= 68.0:
                level = 'high'
            elif used >= 300.0 or p >= 58.0:
                level = 'warning'
        except Exception:
            pass
    return {'level': level, 'rss_mb': mem.get('rss_mb'), 'container_mb': mem.get('container_current_mb'), 'effective_mb': effective, 'limit_mb': mem.get('limit_mb'), 'percent': pct, 'container_peak_mb': mem.get('container_peak_mb'), 'cgroup_events': mem.get('cgroup_events') or {}}

def _runtime_previous_summary(prev: dict) -> dict:
    """Flatten previous watcher state. Never keep recursive previous_runtime chains in RAM."""
    if not isinstance(prev, dict) or not prev:
        return {}
    st = prev.get('state') or {}
    ren = prev.get('render') or {}
    proc = prev.get('process') or {}
    return {'kind': 'telegram_bot_runtime_previous_summary', 'captured_at': prev.get('captured_at') or '', 'bot_version': prev.get('bot_version') or '', 'state': {'phase': st.get('phase') or '', 'ready': bool(st.get('ready')), 'started_at': st.get('started_at') or '', 'ready_at': st.get('ready_at') or '', 'last_webhook_at': st.get('last_webhook_at') or '', 'last_webhook_update_id': st.get('last_webhook_update_id') or '', 'shutdown_started_at': st.get('shutdown_started_at') or '', 'shutdown_finished_at': st.get('shutdown_finished_at') or '', 'shutdown_signal': st.get('shutdown_signal') or '', 'fatal_main_exception': st.get('fatal_main_exception') or '', 'fatal_thread_exception': st.get('fatal_thread_exception') or '', 'last_runtime_snapshot_ok_at': st.get('last_runtime_snapshot_ok_at') or ''}, 'render': {'RENDER_INSTANCE_ID': ren.get('RENDER_INSTANCE_ID') or '', 'RENDER_GIT_COMMIT': ren.get('RENDER_GIT_COMMIT') or '', 'RENDER_SERVICE_ID': ren.get('RENDER_SERVICE_ID') or ''}, 'process': {'rss_mb': proc.get('rss_mb'), 'peak_rss_mb': proc.get('peak_rss_mb'), 'container_current_mb': proc.get('container_current_mb'), 'container_peak_mb': proc.get('container_peak_mb'), 'limit_mb': proc.get('limit_mb'), 'rss_percent_limit': proc.get('rss_percent_limit'), 'container_percent_limit': proc.get('container_percent_limit'), 'cgroup_events': dict(proc.get('cgroup_events') or {}), 'uptime_seconds': proc.get('uptime_seconds')}}

def _runtime_emergency_trim(reason: str='memory_pressure') -> dict:
    """Best-effort RAM cleanup. Never discards finance/forward state or unsaved journal rows."""
    trim_fn = globals().get('memory_trim')
    if callable(trim_fn):
        try:
            return trim_fn(reason, force=True)
        except Exception as exc:
            runtime_event('memory_trim_delegate_error', str(exc), 'WARN')
    before = _runtime_memory_pressure()
    try:
        with bot_journal_lock:
            if len(BOT_ACTION_LOG) > 160:
                tail = list(BOT_ACTION_LOG)[-160:]
                BOT_ACTION_LOG.clear()
                BOT_ACTION_LOG.extend(tail)
    except Exception:
        pass
    try:
        import gc
        gc.collect()
    except Exception:
        pass
    try:
        import ctypes
        ctypes.CDLL('libc.so.6').malloc_trim(0)
    except Exception:
        pass
    after = _runtime_memory_pressure()
    return {'reason': reason, 'before': before, 'after': after}

def runtime_heartbeat_snapshot(event: str='heartbeat') -> dict:
    """Tiny durable liveness marker: deliberately excludes history, full queues and events."""
    with _RUNTIME_LOCK:
        st = dict(_RUNTIME_STATE)
    mem = _runtime_memory_stats()
    return {'kind': 'telegram_bot_runtime_heartbeat', 'schema_version': 2, 'bot_version': VERSION, 'captured_at': now_local().isoformat(timespec='milliseconds'), 'event': str(event or 'heartbeat'), 'state': {'phase': st.get('phase') or '', 'ready': bool(st.get('ready')), 'shutting_down': bool(st.get('shutting_down')), 'started_at': st.get('started_at') or '', 'ready_at': st.get('ready_at') or '', 'last_webhook_at': st.get('last_webhook_at') or '', 'last_webhook_update_id': st.get('last_webhook_update_id') or '', 'shutdown_started_at': st.get('shutdown_started_at') or '', 'shutdown_finished_at': st.get('shutdown_finished_at') or '', 'shutdown_signal': st.get('shutdown_signal') or '', 'fatal_main_exception': st.get('fatal_main_exception') or '', 'fatal_thread_exception': st.get('fatal_thread_exception') or '', 'last_runtime_snapshot_ok_at': st.get('last_runtime_snapshot_ok_at') or ''}, 'render': _runtime_render_env(), 'process': {'pid': os.getpid(), 'rss_mb': mem.get('rss_mb'), 'peak_rss_mb': mem.get('peak_rss_mb'), 'container_current_mb': mem.get('container_current_mb'), 'container_peak_mb': mem.get('container_peak_mb'), 'limit_mb': mem.get('limit_mb'), 'rss_percent_limit': mem.get('rss_percent_limit'), 'container_percent_limit': mem.get('container_percent_limit'), 'cgroup_events': mem.get('cgroup_events') or {}, 'threads': threading.active_count(), 'uptime_seconds': round(max(0.0, time.monotonic() - _RUNTIME_STARTED_MONO), 3)}, 'queues': {'content': WEBHOOK_TASK_POOL.stats().get('pending', 0), 'fast_ui': FAST_UI_TASK_POOL.stats().get('pending', 0), 'ui': UI_TASK_POOL.stats().get('pending', 0), 'callback_ack': CALLBACK_ACK_TASK_POOL.stats().get('pending', 0), 'recovery': RECOVERY_TASK_POOL.stats().get('pending', 0), 'reminder': REMINDER_TASK_POOL.stats().get('pending', 0), 'finance': FINANCE_TASK_POOL.stats().get('pending', 0), 'fin_forward': FIN_FORWARD_TASK_POOL.stats().get('pending', 0), 'forward': FORWARD_TASK_POOL.stats().get('pending', 0), 'delta': DELTA_TASK_POOL.stats().get('pending', 0), 'backup': BACKUP_TASK_POOL.stats().get('pending', 0), 'maintenance': MAINTENANCE_TASK_POOL.stats().get('pending', 0)}}

def _runtime_disk_stats() -> dict:
    try:
        usage = shutil.disk_usage(os.getcwd())
        return {'total_mb': round(usage.total / 1024 / 1024, 1), 'used_mb': round(usage.used / 1024 / 1024, 1), 'free_mb': round(usage.free / 1024 / 1024, 1)}
    except Exception:
        return {'total_mb': None, 'used_mb': None, 'free_mb': None}

def _runtime_pool_stats() -> dict:
    pools = (WEBHOOK_TASK_POOL, FAST_UI_TASK_POOL, UI_TASK_POOL, CALLBACK_ACK_TASK_POOL, RECOVERY_TASK_POOL, REMINDER_TASK_POOL, FINANCE_TASK_POOL, FIN_FORWARD_TASK_POOL, FORWARD_TASK_POOL, DELTA_TASK_POOL, BACKUP_TASK_POOL, EXPORT_TASK_POOL, GENERAL_TASK_POOL, MAINTENANCE_TASK_POOL, JOURNAL_TASK_POOL, DELAYED_TASK_POOL, DOZVON_TASK_POOL)
    return {p.name: p.stats() for p in pools}

def runtime_snapshot(extra: dict | None=None) -> dict:
    with _RUNTIME_LOCK:
        state = dict(_RUNTIME_STATE)
        events = list(_RUNTIME_EVENTS)[-20:]
        previous = _runtime_previous_summary(_RUNTIME_PREVIOUS) if isinstance(_RUNTIME_PREVIOUS, dict) else {}
    snap = {'kind': 'telegram_bot_runtime_watcher', 'schema_version': 1, 'bot_version': VERSION, 'captured_at': now_local().isoformat(timespec='milliseconds'), 'state': state, 'render': _runtime_render_env(), 'process': {'pid': os.getpid(), 'hostname': socket.gethostname(), 'python': sys.version.split()[0], 'platform': platform.platform(), 'threads': threading.active_count(), 'uptime_seconds': round(max(0.0, time.monotonic() - _RUNTIME_STARTED_MONO), 3), **_runtime_memory_stats()}, 'disk': _runtime_disk_stats(), 'queues': _runtime_pool_stats(), 'delayed': DELAYED_SCHEDULER.stats(), 'callback_ack_delayed': CALLBACK_ACK_SCHEDULER.stats(), 'mega_tasks': mega_task_registry_stats() if 'mega_task_registry_stats' in globals() else {}, 'delta': {'pending_chats': len(_delta_pending_chats) if '_delta_pending_chats' in globals() else 0, 'last_success_at': globals().get('_delta_last_success_at', ''), 'last_file': globals().get('_delta_last_file', ''), 'last_event_count': globals().get('_delta_last_event_count', 0), 'last_error': globals().get('_delta_last_error', '')}, 'keep_alive': dict(KEEP_ALIVE_STATE) if 'KEEP_ALIVE_STATE' in globals() else {}, 'memory_guard': _runtime_memory_pressure(), 'memory_runtime': memory_runtime_summary() if 'memory_runtime_summary' in globals() else {}, 'audit_metrics': runtime_audit_metrics() if 'runtime_audit_metrics' in globals() else {}, 'config_guard_v234': {'boot_verified': bool(globals().get('CONFIG_GUARD_BOOT_VERIFIED_V234', False)), 'report': _delta_json_clone(globals().get('CONFIG_GUARD_LAST_REPORT_V234', {}) or {}), 'latest': config_guard_latest_local_v234() if callable(globals().get('config_guard_latest_local_v234')) else {}}, 'previous_runtime': previous, 'events': events}
    if extra:
        snap['extra'] = _delta_json_clone(extra)
    return snap

def runtime_remote_dir() -> str:
    return f"{MEGA_BACKUP_DIR.rstrip('/')}/{_RUNTIME_REMOTE_DIR_NAME}"

def runtime_latest_remote_path() -> str:
    """Legacy v108-v117 path. v118 no longer writes this file."""
    return f"{runtime_remote_dir().rstrip('/')}/{_RUNTIME_LATEST_NAME}"

def _runtime_slot_name(index: int) -> str:
    idx = int(index) % max(2, int(RUNTIME_WATCHER_SLOT_COUNT))
    return f'runtime_slot_{idx}.json'

def _runtime_slot_remote_path(index: int) -> str:
    return f"{runtime_remote_dir().rstrip('/')}/{_runtime_slot_name(index)}"

def _runtime_snapshot_sort_ts(snap: dict) -> float:
    """Sortable timestamp for choosing the newest durable runtime breadcrumb."""
    if not isinstance(snap, dict):
        return 0.0
    candidates = [snap.get('captured_at'), (snap.get('state') or {}).get('last_runtime_snapshot_ok_at') if isinstance(snap.get('state'), dict) else None, (snap.get('state') or {}).get('last_event_at') if isinstance(snap.get('state'), dict) else None, (snap.get('state') or {}).get('started_at') if isinstance(snap.get('state'), dict) else None]
    for value in candidates:
        try:
            dt = datetime.fromisoformat(str(value or '').replace('Z', '+00:00'))
            return float(dt.timestamp())
        except Exception:
            continue
    return 0.0

def _runtime_load_remote_snapshot(remote_path: str) -> dict:
    """Read runtime diagnostics quietly; corrupt historical breadcrumbs must not slow/noise boot."""
    local = None
    try:
        local = _mega_download_remote_path(remote_path)
        if not local:
            return {}
        try:
            with open(local, 'r', encoding='utf-8') as fh:
                snap = json.load(fh)
        except Exception:
            return {}
        return snap if isinstance(snap, dict) else {}
    except Exception:
        return {}
    finally:
        try:
            if local:
                shutil.rmtree(os.path.dirname(local), ignore_errors=True)
        except Exception:
            pass

def _runtime_write_redundant_slot(local_snapshot: str, event: str='snapshot') -> tuple[bool, str]:
    """Write one of 2-5 alternating runtime slots without MEGA rename/promote.

    v113-v117 showed that `mega-mv old_file new_filename` is not reliable on the
    installed MEGAcmd build ("must be a valid folder").  v118 therefore keeps
    multiple fixed slots.  Updating one slot is rm+put; the other slots remain
    untouched, so a hard kill between the two commands still leaves a recent
    durable breadcrumb for the next process.
    """
    interval = max(20.0, float(RUNTIME_WATCHER_HEARTBEAT_SECONDS))
    slot_index = int(time.time() // interval) % max(2, int(RUNTIME_WATCHER_SLOT_COUNT))
    slot_name = _runtime_slot_name(slot_index)
    remote_slot = _runtime_slot_remote_path(slot_index)
    alias_local = os.path.join(MEGA_LOCAL_TMP_DIR, slot_name)
    try:
        if os.path.abspath(alias_local) != os.path.abspath(local_snapshot):
            shutil.copy2(local_snapshot, alias_local)
        rm = _mega_run('mega-rm', [remote_slot], check=False, timeout=30)
        if rm.returncode != 0:
            err = (rm.stderr or rm.stdout or '')[:500]
            if not _mega_remote_missing_error(err):
                with _RUNTIME_LOCK:
                    _RUNTIME_STATE['runtime_slot_failures'] = int(_RUNTIME_STATE.get('runtime_slot_failures', 0) or 0) + 1
                log_error(f'[RUNTIME SLOT] cannot remove {remote_slot}: {err}')
                return (False, slot_name)
        _mega_run('mega-put', [alias_local, runtime_remote_dir()], check=True, timeout=MEGA_TIMEOUT)
        now_ts = now_local().isoformat(timespec='milliseconds')
        with _RUNTIME_LOCK:
            _RUNTIME_STATE['last_runtime_slot'] = slot_name
            _RUNTIME_STATE['last_runtime_slot_at'] = now_ts
        return (True, slot_name)
    except Exception as e:
        with _RUNTIME_LOCK:
            _RUNTIME_STATE['runtime_slot_failures'] = int(_RUNTIME_STATE.get('runtime_slot_failures', 0) or 0) + 1
        log_error(f'[RUNTIME SLOT] write failed {slot_name}: {e}')
        return (False, slot_name)
    finally:
        try:
            if alias_local != local_snapshot and os.path.exists(alias_local):
                os.remove(alias_local)
        except Exception:
            pass

def runtime_load_previous_snapshot() -> dict:
    """Load the newest trustworthy previous runtime snapshot.

    Priority is not based on filenames: v118 reads all current rotating slots and
    a few immutable runtime events, then chooses the newest `captured_at`.  The
    stale legacy `runtime_latest.json` is used only as a last-resort fallback.
    """
    global _RUNTIME_PREVIOUS
    if not mega_is_configured():
        return {}
    try:
        mega_ensure_remote_path(runtime_remote_dir())
        remote_candidates: list[tuple[str, str]] = []
        try:
            for remote in _mega_find_remote_files(runtime_remote_dir(), 'runtime_slot_*.json', limit=10):
                remote_candidates.append(('slot', remote))
        except Exception:
            pass
        events_dir = runtime_remote_dir().rstrip('/') + '/events'
        try:
            for remote in _mega_find_remote_files(events_dir, 'runtime_*.json', limit=3):
                remote_candidates.append(('event', remote))
        except Exception:
            pass
        try:
            for remote in _mega_find_remote_files(runtime_remote_dir(), 'candidate_runtime_latest_*.json', limit=2):
                remote_candidates.append(('legacy_candidate', remote))
            for remote in _mega_find_remote_files(runtime_remote_dir(), 'runtime_latest__*.json', limit=1):
                remote_candidates.append(('legacy_staged', remote))
        except Exception:
            pass
        best_snap = {}
        best_source = ''
        best_ts = 0.0
        seen = set()
        for source_kind, remote in remote_candidates:
            if remote in seen:
                continue
            seen.add(remote)
            snap = _runtime_load_remote_snapshot(remote)
            ts = _runtime_snapshot_sort_ts(snap)
            if snap and ts >= best_ts:
                best_snap = snap
                best_ts = ts
                best_source = f'{source_kind}:{os.path.basename(remote)}'
        if not best_snap:
            legacy_paths = [runtime_latest_remote_path()]
            for remote in legacy_paths:
                snap = _runtime_load_remote_snapshot(remote)
                ts = _runtime_snapshot_sort_ts(snap)
                if snap and ts >= best_ts:
                    best_snap = snap
                    best_ts = ts
                    best_source = f'legacy:{os.path.basename(remote)}'
        prev = _runtime_previous_summary(best_snap) if isinstance(best_snap, dict) else {}
        with _RUNTIME_LOCK:
            _RUNTIME_PREVIOUS = prev
            _RUNTIME_STATE['previous_snapshot_source'] = best_source
        if prev:
            runtime_event('previous_snapshot_loaded', f"source={best_source or 'unknown'} captured_at={prev.get('captured_at', '')} bot={prev.get('bot_version', '')}")
        return prev
    except Exception as e:
        runtime_event('previous_snapshot_error', str(e), 'WARN')
        return {}

def _runtime_parse_ts(value):
    try:
        text = str(value or '').strip()
        if not text:
            return None
        return datetime.fromisoformat(text.replace('Z', '+00:00'))
    except Exception:
        return None

def _runtime_seconds_between(a, b):
    da, db = (_runtime_parse_ts(a), _runtime_parse_ts(b))
    if not da or not db:
        return None
    try:
        if (da.tzinfo is None) != (db.tzinfo is None):
            da = da.replace(tzinfo=None)
            db = db.replace(tzinfo=None)
        return (db - da).total_seconds()
    except Exception:
        return None

def _v177_legacy_0078_runtime_classify_previous(prev: dict) -> str:
    """Best-effort diagnosis. It deliberately says *probable* when Render provides no exact reason."""
    if not isinstance(prev, dict) or not prev:
        return 'first_seen'
    prev_state = prev.get('state') or {}
    prev_render = prev.get('render') or {}
    cur_render = _runtime_render_env()
    prev_commit = str(prev_render.get('RENDER_GIT_COMMIT') or '')
    cur_commit = str(cur_render.get('RENDER_GIT_COMMIT') or '')
    prev_instance = str(prev_render.get('RENDER_INSTANCE_ID') or '')
    cur_instance = str(cur_render.get('RENDER_INSTANCE_ID') or '')
    graceful = bool(prev_state.get('shutdown_finished_at')) or str(prev_state.get('phase') or '') in {'stopped', 'shutdown_complete'}
    signal_name = str(prev_state.get('shutdown_signal') or '')
    if prev_commit and cur_commit and (prev_commit != cur_commit):
        return 'deploy_new_commit_graceful' if graceful else 'deploy_new_commit_ungraceful'
    last_webhook = prev_state.get('last_webhook_at')
    shutdown_at = prev_state.get('shutdown_started_at') or prev.get('captured_at')
    idle_before_shutdown = _runtime_seconds_between(last_webhook, shutdown_at)
    idle_to_new_start = _runtime_seconds_between(last_webhook, _RUNTIME_STARTED_AT)
    probable_idle = bool(idle_before_shutdown is not None and idle_before_shutdown >= 13.5 * 60 or (not graceful and idle_to_new_start is not None and (idle_to_new_start >= 13.5 * 60)))
    if not graceful:
        try:
            prev_proc = prev.get('process') or {}
            events = prev_proc.get('cgroup_events') or {}
            oom_kill = int(events.get('oom_kill', 0) or 0) + int(events.get('oom_group_kill', 0) or 0)
            peak = float(prev_proc.get('container_peak_mb') or prev_proc.get('peak_rss_mb') or 0.0)
            limit = float(prev_proc.get('limit_mb') or 0.0)
            if oom_kill > 0 or (limit > 0 and peak / limit >= 0.9):
                return 'probable_memory_oom_or_hard_kill'
        except Exception:
            pass
    if graceful:
        if probable_idle and signal_name in {'SIGTERM', ''}:
            return 'probable_render_idle_spin_down_graceful'
        if signal_name == 'SIGINT':
            return 'manual_or_local_stop_same_commit'
        return 'planned_restart_same_commit'
    if prev_instance and cur_instance and (prev_instance != cur_instance):
        if probable_idle:
            return 'probable_render_idle_spin_down_or_idle_restart'
        return 'new_instance_same_commit_crash_restart_or_maintenance'
    return 'process_restart_or_unknown'
try:
    _v177_legacy_0078_runtime_classify_previous.__name__ = 'runtime_classify_previous'
except Exception:
    pass
_RUNTIME_EXPORT_FILE_RE = re.compile('(?:candidate_runtime_latest_|runtime_latest__|runtime_)(\\d{8})_(\\d{6})')

def _runtime_export_filename_dt(remote_path: str):
    """Timestamp embedded in v111-v118 runtime filenames; used only for export filtering."""
    m = _RUNTIME_EXPORT_FILE_RE.search(os.path.basename(str(remote_path or '')))
    if not m:
        return None
    try:
        return datetime.strptime(m.group(1) + m.group(2), '%Y%m%d%H%M%S')
    except Exception:
        return None

def _runtime_export_parse_range(text: str):
    """Parse /runtime_export [YYYY-MM-DD HH:MM [HH:MM]]; returns naive local datetimes or (None,None)."""
    raw = str(text or '').strip()
    parts = raw.split()
    if parts and parts[0].lower().startswith('/runtime_export'):
        parts = parts[1:]
    if not parts or parts[0].lower() in {'all', 'все'}:
        return (None, None)
    try:
        day = datetime.strptime(parts[0], '%Y-%m-%d')
    except Exception:
        return (None, None)
    start = day
    end = day + timedelta(days=1)
    if len(parts) >= 2:
        try:
            hh, mm = [int(x) for x in parts[1].split(':', 1)]
            start = day.replace(hour=hh, minute=mm, second=0)
        except Exception:
            pass
    if len(parts) >= 3:
        try:
            hh, mm = [int(x) for x in parts[2].split(':', 1)]
            end = day.replace(hour=hh, minute=mm, second=59)
            if end < start:
                end += timedelta(days=1)
        except Exception:
            pass
    return (start, end)

def _v177_legacy_0079_runtime_export_select_paths(start_dt=None, end_dt=None, max_downloads: int=360):
    """Return complete index + bounded actual-download set. Never deletes or mutates MEGA."""
    root = runtime_remote_dir()
    events_dir = root.rstrip('/') + '/events'
    indexed = []
    groups = (('candidate', root, 'candidate_runtime_latest_*.json'), ('staged', root, 'runtime_latest__*.json'), ('slot', root, 'runtime_slot_*.json'), ('event', events_dir, 'runtime_*.json'))
    for kind, remote_dir, pattern in groups:
        try:
            for remote in _mega_find_remote_files(remote_dir, pattern):
                dt = _runtime_export_filename_dt(remote)
                if start_dt is not None and dt is not None and (dt < start_dt):
                    continue
                if end_dt is not None and dt is not None and (dt > end_dt):
                    continue
                indexed.append((kind, remote, dt))
        except Exception as e:
            log_error(f'runtime_export list {kind}: {e}')
    try:
        for remote in _mega_find_remote_files(root, 'runtime_latest.json', limit=1):
            indexed.append(('legacy', remote, None))
    except Exception:
        pass
    uniq = {}
    for kind, remote, dt in indexed:
        uniq[str(remote)] = (kind, str(remote), dt)
    indexed = sorted(uniq.values(), key=lambda x: (x[2] or datetime.min, x[1]), reverse=True)
    fixed = [x for x in indexed if x[0] in {'slot', 'event', 'legacy'}]
    variable = [x for x in indexed if x[0] not in {'slot', 'event', 'legacy'}]
    budget = max(20, int(max_downloads))
    selected = fixed[:min(len(fixed), 120)]
    remaining = max(0, budget - len(selected))
    if len(variable) <= remaining:
        selected.extend(variable)
    elif remaining > 0:
        if remaining == 1:
            selected.append(variable[0])
        else:
            chosen = set()
            for i in range(remaining):
                idx = round(i * (len(variable) - 1) / (remaining - 1))
                chosen.add(int(idx))
            selected.extend((variable[i] for i in sorted(chosen)))
    return (indexed, selected[:budget])
try:
    _v177_legacy_0079_runtime_export_select_paths.__name__ = '_runtime_export_select_paths'
except Exception:
    pass

def _runtime_export_arcname(kind: str, remote_path: str) -> str:
    folder = {'candidate': 'candidates', 'staged': 'staged', 'slot': 'slots', 'event': 'events', 'legacy': 'legacy'}.get(str(kind), 'other')
    return f'{folder}/{os.path.basename(str(remote_path))}'

def _v177_legacy_0080_send_runtime_export_zip(recipient_chat_id: int, start_dt=None, end_dt=None):
    """Background owner export of runtime breadcrumbs. Complete MEGA index + sampled actual JSONs in one ZIP."""
    recipient_chat_id = int(recipient_chat_id)
    workdir = tempfile.mkdtemp(prefix='runtime_export_')
    zip_path = None
    downloaded_dirs = []
    try:
        bot_journal('runtime_export_start', recipient_chat_id, f'start={start_dt} end={end_dt}')
        _file_job_progress('индексирую Runtime в MEGA', force=True)
        indexed, selected = _runtime_export_select_paths(start_dt, end_dt, max_downloads=360 if start_dt else 240)
        _file_job_progress('скачиваю JSON из MEGA', 0, len(selected), force=True)
        stamp = now_local().strftime('%Y%m%d_%H%M%S')
        zip_path = os.path.join(MEGA_LOCAL_TMP_DIR, f'runtime_export_{stamp}.zip')
        os.makedirs(MEGA_LOCAL_TMP_DIR, exist_ok=True)
        manifest_lines = [f'version={VERSION}', f"created={now_local().isoformat(timespec='seconds')}", f"filter_start={start_dt or ''}", f"filter_end={end_dt or ''}", f'indexed_remote_files={len(indexed)}', f'selected_for_download={len(selected)}', '', 'ALL REMOTE FILES (complete index; * means selected for JSON download):']
        selected_set = {x[1] for x in selected}
        for kind, remote, dt in indexed:
            manifest_lines.append(f"{('*' if remote in selected_set else ' ')} | {kind:9s} | {dt or ''} | {remote}")
        ok_count = 0
        fail_count = 0
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as z:
            z.writestr('manifest.txt', '\n'.join(manifest_lines))
            try:
                z.writestr('current_runtime_snapshot.json', json.dumps(runtime_snapshot({'source': 'runtime_export'}), ensure_ascii=False, indent=2, default=str))
            except Exception:
                pass
            for kind, remote, _dt in selected:
                local = _mega_download_remote_path(remote)
                if not local and str(kind) == 'slot':
                    time.sleep(0.35)
                    local = _mega_download_remote_path(remote)
                if not local:
                    fail_count += 1
                    _file_job_progress('скачиваю JSON из MEGA', ok_count + fail_count, len(selected))
                    continue
                downloaded_dirs.append(os.path.dirname(local))
                try:
                    z.write(local, _runtime_export_arcname(kind, remote))
                    ok_count += 1
                except Exception:
                    fail_count += 1
                _file_job_progress('скачиваю JSON из MEGA', ok_count + fail_count, len(selected))
        _file_job_progress('ZIP собран, готовлю отправку', force=True)
        fobj = file_bytesio_named(zip_path, os.path.basename(zip_path))
        if not fobj:
            raise RuntimeError('runtime ZIP was not created')
        caption = f"📦 Runtime MEGA ZIP\nИндекс: {len(indexed)} файлов; JSON внутри: {ok_count}; ошибок скачивания: {fail_count}.\n{('Период: ' + str(start_dt) + ' — ' + str(end_dt) if start_dt else 'Период: последние доступные + полный индекс.')}"
        _file_job_progress('отправляю ZIP в Telegram', force=True)
        _tg_call_retry(bot.send_document, recipient_chat_id, fobj, caption=caption, timeout=120, purpose='runtime_export_send')
        bot_journal('runtime_export_done', recipient_chat_id, f'indexed={len(indexed)} downloaded={ok_count} failed={fail_count}')
        return True
    except Exception as e:
        log_error(f'send_runtime_export_zip: {e}')
        try:
            send_and_auto_delete(recipient_chat_id, f'❌ Runtime ZIP: {str(e)[:220]}', 20)
        except Exception:
            pass
        return False
    finally:
        for folder in set(downloaded_dirs):
            try:
                shutil.rmtree(folder, ignore_errors=True)
            except Exception:
                pass
        try:
            shutil.rmtree(workdir, ignore_errors=True)
        except Exception:
            pass
        if zip_path:
            try:
                os.remove(zip_path)
            except Exception:
                pass
try:
    _v177_legacy_0080_send_runtime_export_zip.__name__ = 'send_runtime_export_zip'
except Exception:
    pass

def _v177_legacy_0081_runtime_upload_snapshot(event: str='snapshot', immutable_event: bool=True) -> bool:
    if not mega_is_configured():
        return False
    heartbeat = str(event) == 'heartbeat'
    acquired = _RUNTIME_UPLOAD_LOCK.acquire(timeout=0.05 if heartbeat else 5.0)
    if not acquired:
        if not heartbeat:
            runtime_event('watcher_upload_busy', f'event={event}; another runtime upload is active', 'WARN')
        return False
    tmp = None
    started = time.monotonic()
    try:
        pressure = _runtime_memory_pressure()
        if heartbeat:
            if str(pressure.get('level')) in {'high', 'critical'}:
                _runtime_emergency_trim('heartbeat_memory_pressure')
            snap = runtime_heartbeat_snapshot(event)
        else:
            snap = runtime_snapshot({'event': event})
        os.makedirs(MEGA_LOCAL_TMP_DIR, exist_ok=True)
        stamp = now_local().strftime('%Y%m%d_%H%M%S_%f')
        safe_event = mega_safe_name(event, 'event')
        tmp = os.path.join(MEGA_LOCAL_TMP_DIR, f'runtime_{stamp}_{safe_event}.json')
        _atomic_json_dump(tmp, snap)
        mega_ensure_remote_path(runtime_remote_dir())
        event_ok = True
        if immutable_event:
            events_dir = runtime_remote_dir().rstrip('/') + '/events'
            mega_ensure_remote_path(events_dir)
            try:
                _mega_run('mega-put', [tmp, events_dir], check=True, timeout=MEGA_TIMEOUT)
                try:
                    _mega_prune_remote_history(events_dir, 'runtime_*.json', RUNTIME_WATCHER_HISTORY_KEEP)
                except Exception:
                    pass
            except Exception as e:
                event_ok = False
                log_error(f'[RUNTIME EVENT] upload failed event={event}: {e}')
        slot_ok, slot_name = _runtime_write_redundant_slot(tmp, event)
        elapsed = round(time.monotonic() - started, 3)
        durable_ok = bool(slot_ok and event_ok)
        with _RUNTIME_LOCK:
            if durable_ok:
                _RUNTIME_STATE['last_runtime_snapshot_ok_at'] = now_local().isoformat(timespec='milliseconds')
                _RUNTIME_STATE['last_runtime_snapshot_error'] = ''
            else:
                _RUNTIME_STATE['last_runtime_snapshot_error'] = f'slot_ok={slot_ok}; event_ok={event_ok}; slot={slot_name}'[:500]
        if not durable_ok:
            runtime_event('watcher_mega_error', f'event={event}; elapsed={elapsed}s; slot={slot_name}; slot_ok={slot_ok}; event_ok={event_ok}', 'WARN')
            return False
        if heartbeat:
            global _RUNTIME_HEARTBEAT_OK_SEQ
            try:
                _RUNTIME_HEARTBEAT_OK_SEQ += 1
            except Exception:
                _RUNTIME_HEARTBEAT_OK_SEQ = 1
            if _RUNTIME_HEARTBEAT_OK_SEQ % 10 == 0 or elapsed >= 3.0 or str(pressure.get('level')) != 'normal':
                runtime_event('watcher_mega_ok', f'event={event}; elapsed={elapsed}s; slot={slot_name}; immutable={bool(immutable_event)}')
        else:
            runtime_event('watcher_mega_ok', f'event={event}; elapsed={elapsed}s; slot={slot_name}; immutable={bool(immutable_event)}')
        return True
    except Exception as e:
        elapsed = round(time.monotonic() - started, 3)
        with _RUNTIME_LOCK:
            _RUNTIME_STATE['last_runtime_snapshot_error'] = str(e)[:500]
        runtime_event('watcher_mega_error', f'event={event}; elapsed={elapsed}s; {e}', 'WARN')
        return False
    finally:
        try:
            if tmp and os.path.exists(tmp):
                os.remove(tmp)
        except Exception:
            pass
        try:
            _RUNTIME_UPLOAD_LOCK.release()
        except Exception:
            pass
try:
    _v177_legacy_0081_runtime_upload_snapshot.__name__ = 'runtime_upload_snapshot'
except Exception:
    pass

def runtime_mark_webhook(payload: dict | None=None, blocked: str=''):
    with _RUNTIME_LOCK:
        _RUNTIME_STATE['webhook_received'] = int(_RUNTIME_STATE.get('webhook_received', 0) or 0) + 1
        _RUNTIME_STATE['last_webhook_at'] = now_local().isoformat(timespec='milliseconds')
        if blocked == 'boot':
            _RUNTIME_STATE['webhook_blocked_boot'] = int(_RUNTIME_STATE.get('webhook_blocked_boot', 0) or 0) + 1
        elif blocked == 'shutdown':
            _RUNTIME_STATE['webhook_blocked_shutdown'] = int(_RUNTIME_STATE.get('webhook_blocked_shutdown', 0) or 0) + 1
        if isinstance(payload, dict):
            _RUNTIME_STATE['last_webhook_update_id'] = payload.get('update_id', '')
            if 'edited_message' in payload:
                typ = 'edited_message'
            elif 'message' in payload:
                typ = 'message'
            elif 'callback_query' in payload:
                typ = 'callback_query'
            elif 'channel_post' in payload:
                typ = 'channel_post'
            elif 'edited_channel_post' in payload:
                typ = 'edited_channel_post'
            else:
                typ = 'other'
            _RUNTIME_STATE['last_webhook_type'] = typ
            try:
                _RUNTIME_STATE['last_webhook_chat_id'] = _extract_update_chat_id(payload)
            except Exception:
                pass

def _runtime_watcher_should_yield_to_critical_mega() -> bool:
    """Watcher is diagnostic and must never intentionally compete with business persistence."""
    try:
        for pool in (DELTA_TASK_POOL, BACKUP_TASK_POOL):
            st = pool.stats() or {}
            if int(st.get('pending', 0) or 0) > 0 or int(st.get('active', 0) or 0) > 0:
                return True
        mt = mega_task_registry_stats() or {}
        if int(mt.get('processing', 0) or 0) > 0:
            return True
    except Exception:
        return False
    return False

def _lowram_business_busy() -> bool:
    try:
        for pool_name in ('WEBHOOK_TASK_POOL', 'UI_TASK_POOL', 'RECOVERY_TASK_POOL', 'REMINDER_TASK_POOL', 'FINANCE_TASK_POOL', 'FIN_FORWARD_TASK_POOL', 'FORWARD_TASK_POOL', 'DELTA_TASK_POOL', 'BACKUP_TASK_POOL'):
            pool = globals().get(pool_name)
            if pool is None:
                continue
            st = pool.stats() or {}
            if int(st.get('pending', 0) or 0) > 0 or int(st.get('active', 0) or 0) > 0:
                return True
        mt = mega_task_registry_stats() or {}
        return int(mt.get('processing', 0) or 0) > 0
    except Exception:
        return True

def _lowram_idle_sweep_job():
    """Return forgotten cold chat histories to SQLite only while the bot is idle."""
    try:
        if runtime_is_shutting_down():
            return
        if LOWRAM_ENABLED and (not _lowram_business_busy()):

            def _loaded_fields_count():
                total = 0
                try:
                    for store in ((data or {}).get('chats', {}) or {}).values():
                        if isinstance(store, dict):
                            total += sum((1 for k in LOWRAM_COLD_KEYS if dict.__contains__(store, k)))
                except Exception:
                    pass
                return total
            loaded_before = _loaded_fields_count()
            if loaded_before > 0:
                _lowram_flush_all_hot(evict=True)
                try:
                    import gc
                    gc.collect()
                    trim_fn = globals().get('memory_malloc_trim')
                    if callable(trim_fn):
                        trim_fn()
                except Exception:
                    pass
                loaded_after = _loaded_fields_count()
                mem = _runtime_memory_stats()
                runtime_event('lowram_idle_evict', f"loaded_fields={loaded_before}->{loaded_after} rss={mem.get('rss_mb', '?')}MB")
    except Exception as e:
        runtime_event('lowram_idle_evict_error', str(e), 'WARN')
    finally:
        try:
            DELAYED_SCHEDULER.schedule('lowram-idle-sweep', 45.0, _lowram_idle_sweep_job)
        except Exception:
            pass

def _v179_base_runtime_heartbeat_job():
    if runtime_is_shutting_down():
        return
    next_delay = RUNTIME_WATCHER_HEARTBEAT_SECONDS
    try:
        if _runtime_watcher_should_yield_to_critical_mega():
            runtime_event('watcher_heartbeat_deferred', 'critical MEGA work has priority')
            next_delay = min(60.0, RUNTIME_WATCHER_HEARTBEAT_SECONDS)
        else:
            GENERAL_TASK_POOL.submit('runtime-heartbeat-upload', runtime_upload_snapshot, 'heartbeat', False)
    finally:
        try:
            DELAYED_SCHEDULER.schedule('runtime-heartbeat', next_delay, _runtime_heartbeat_job)
        except Exception:
            pass

def _v177_legacy_0082_runtime_mark_ready(detail: str=''):
    with _RUNTIME_LOCK:
        if _RUNTIME_STATE.get('ready'):
            return
        _RUNTIME_STATE['ready'] = True
        _RUNTIME_STATE['phase'] = 'ready'
        _RUNTIME_STATE['ready_at'] = now_local().isoformat(timespec='seconds')
        _RUNTIME_STATE['boot_completed_at'] = _RUNTIME_STATE['ready_at']
        _RUNTIME_STATE['boot_duration_seconds'] = round(max(0.0, time.monotonic() - _RUNTIME_STARTED_MONO), 3)
    runtime_event('ready', detail or 'BOOT completed')
    GENERAL_TASK_POOL.submit('runtime-ready-snapshot', runtime_upload_snapshot, 'boot_ready', True)
    try:
        DELAYED_SCHEDULER.schedule('runtime-heartbeat', RUNTIME_WATCHER_HEARTBEAT_SECONDS, _runtime_heartbeat_job)
    except Exception:
        pass
    if not RESTORE_GUARD_ACTIVE:
        try:
            schedule_startup_main_windows(delay=1.0)
        except Exception as e:
            runtime_event('startup_windows_error', str(e), 'WARN')
    try:
        schedule_restored_secret_media_recovery(60.0)
    except Exception as e:
        runtime_event('secret_media_resume_error', str(e), 'WARN')
    try:
        DELAYED_SCHEDULER.schedule('journal-warm-tail', 12.0, _journal_warm_tail_job)
    except Exception:
        pass
    try:
        DELAYED_SCHEDULER.schedule('lowram-idle-sweep', 45.0, _lowram_idle_sweep_job)
    except Exception:
        pass
try:
    _v177_legacy_0082_runtime_mark_ready.__name__ = 'runtime_mark_ready'
except Exception:
    pass

def _runtime_pending_recovery_rows() -> list[tuple[str, str, str]]:
    rows = []
    with _MEGA_TASK_LOCK:
        for key, row in _mega_task_registry.items():
            if str((row or {}).get('state')) in {'pending', 'running'}:
                rows.append((key, str(row.get('state')), str(row.get('path') or '')))
    return sorted(rows, key=lambda x: (0, int(x[0])) if str(x[0]).isdigit() else (1, str(x[0])))

def runtime_recover_tasks_blocking(max_seconds: float | None=None) -> dict:
    if not mega_tasks_active():
        return mega_task_registry_stats()
    max_seconds = BOOT_SYNC_RECOVERY_SECONDS if max_seconds is None else max(0.0, float(max_seconds))
    deadline = time.monotonic() + max_seconds
    with _RUNTIME_LOCK:
        _RUNTIME_STATE['task_recovery_started_at'] = now_local().isoformat(timespec='seconds')
    runtime_set_phase('task_recovery', 'восстанавливаю pending/running из MEGA')
    while time.monotonic() < deadline:
        stats = mega_task_refresh_registry()
        rows = _runtime_pending_recovery_rows()
        with _RUNTIME_LOCK:
            _RUNTIME_STATE['task_recovery_remaining'] = len(rows)
        if not rows:
            with _RUNTIME_LOCK:
                _RUNTIME_STATE['task_recovery_finished_at'] = now_local().isoformat(timespec='seconds')
            return stats
        progressed = False
        for key, state, path in rows[:MEGA_TASK_RECOVERY_LIMIT]:
            if time.monotonic() >= deadline:
                break
            before = mega_task_known_state(key)
            _mega_task_recover_one(key, state, path)
            after = mega_task_known_state(key)
            progressed = progressed or after != before
        if not progressed:
            time.sleep(0.25)
    mega_task_refresh_registry()
    rows = _runtime_pending_recovery_rows()
    with _RUNTIME_LOCK:
        _RUNTIME_STATE['task_recovery_remaining'] = len(rows)
    return mega_task_registry_stats()

def runtime_continue_boot_recovery_background():
    """Keep webhook gated until old durable tasks are resolved; health endpoint stays alive."""
    while not runtime_is_shutting_down():
        try:
            runtime_recover_tasks_blocking(max_seconds=max(5.0, BOOT_SYNC_RECOVERY_SECONDS))
            rows = _runtime_pending_recovery_rows() if mega_tasks_active() else []
            if not rows:
                runtime_mark_ready('старые MEGA-задачи проверены/восстановлены')
                return
            runtime_event('boot_recovery_wait', f'осталось задач: {len(rows)}', 'WARN')
        except Exception as e:
            runtime_event('boot_recovery_error', str(e), 'ERROR')
        time.sleep(BOOT_RECOVERY_RETRY_SECONDS)

def runtime_queue_drain_status() -> dict:
    critical = (WEBHOOK_TASK_POOL, FINANCE_TASK_POOL, FIN_FORWARD_TASK_POOL, FORWARD_TASK_POOL, DELTA_TASK_POOL)
    stats = {p.name: p.stats() for p in critical}
    stats['critical_pending'] = sum((int(v.get('pending', 0) or 0) for v in stats.values() if isinstance(v, dict)))
    stats['critical_active'] = sum((int(v.get('active', 0) or 0) for v in stats.values() if isinstance(v, dict)))
    return stats

def _runtime_force_delta_flush() -> bool:
    """Capture all changed compact chat/root metadata once before a graceful exit."""
    global _delta_generation
    if RESTORE_GUARD_ACTIVE or not mega_is_configured():
        return False
    try:
        with _delta_state_lock:
            for cid in (data.get('chats', {}) or {}).keys():
                try:
                    int_cid = int(cid)
                except Exception:
                    continue
                _delta_generation += 1
                _delta_pending_chats.add(int_cid)
                _delta_chat_generation[int_cid] = _delta_generation
        if not _delta_pending_chats:
            return True
        return bool(_run_delta_batch())
    except Exception as e:
        runtime_event('shutdown_delta_error', str(e), 'ERROR')
        return False

def runtime_graceful_shutdown(signal_name: str='SIGTERM'):
    with _RUNTIME_LOCK:
        if _RUNTIME_STATE.get('shutdown_finished_at'):
            return
    if not _RUNTIME_SHUTDOWN_LOCK.acquire(blocking=False):
        return
    try:
        with _RUNTIME_LOCK:
            _RUNTIME_STATE['shutting_down'] = True
            _RUNTIME_STATE['ready'] = False
            _RUNTIME_STATE['phase'] = 'shutting_down'
            _RUNTIME_STATE['shutdown_started_at'] = now_local().isoformat(timespec='seconds')
            _RUNTIME_STATE['shutdown_signal'] = str(signal_name)
        runtime_event('shutdown_start', f'signal={signal_name}')
        try:
            DELAYED_SCHEDULER.cancel('runtime-heartbeat')
            DELAYED_SCHEDULER.cancel('journal-warm-tail')
            DELAYED_SCHEDULER.cancel('lowram-idle-sweep')
        except Exception:
            pass
        deadline = time.monotonic() + GRACEFUL_SHUTDOWN_SECONDS
        drain_ok = False
        while time.monotonic() < deadline:
            drain = runtime_queue_drain_status()
            if int(drain.get('critical_pending', 0) or 0) <= 0:
                drain_ok = True
                break
            time.sleep(0.05)
        with _RUNTIME_LOCK:
            _RUNTIME_STATE['shutdown_drain_ok'] = bool(drain_ok)
        runtime_event('shutdown_drain', f'ok={drain_ok}; {runtime_queue_drain_status()}')
        try:
            save_data(data, full=True)
        except Exception as e:
            runtime_event('shutdown_local_save_error', str(e), 'ERROR')
        delta_ok = _runtime_force_delta_flush()
        with _RUNTIME_LOCK:
            _RUNTIME_STATE['shutdown_delta_ok'] = bool(delta_ok)
            _RUNTIME_STATE['phase'] = 'shutdown_complete'
            _RUNTIME_STATE['shutdown_finished_at'] = now_local().isoformat(timespec='seconds')
        runtime_event('shutdown_complete', f'delta_ok={delta_ok}; drain_ok={drain_ok}')
        try:
            journal_flush_to_mega(True)
        except Exception:
            pass
        runtime_upload_snapshot('shutdown', True)
    finally:
        _RUNTIME_SHUTDOWN_LOCK.release()

def _runtime_signal_handler(signum, frame):
    try:
        name = signal.Signals(signum).name
    except Exception:
        name = str(signum)
    try:
        runtime_graceful_shutdown(name)
    finally:
        raise SystemExit(0)

def _runtime_main_excepthook(exc_type, exc_value, exc_traceback):
    try:
        detail = f"{getattr(exc_type, '__name__', exc_type)}: {exc_value}"
        with _RUNTIME_LOCK:
            _RUNTIME_STATE['fatal_main_exception'] = detail[:1000]
        runtime_event('fatal_main_exception', detail, 'CRITICAL')
        try:
            journal_flush_to_mega(True)
        except Exception:
            pass
        try:
            runtime_upload_snapshot('fatal_main_exception', True)
        except Exception:
            pass
    finally:
        try:
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
        except Exception:
            pass

def _runtime_thread_excepthook(args):
    try:
        thread_name = getattr(getattr(args, 'thread', None), 'name', 'unknown')
        detail = f"thread={thread_name}; {getattr(args.exc_type, '__name__', args.exc_type)}: {args.exc_value}"
        with _RUNTIME_LOCK:
            _RUNTIME_STATE['fatal_thread_exception'] = detail[:1000]
        runtime_event('thread_unhandled_exception', detail, 'ERROR')
        try:
            GENERAL_TASK_POOL.submit('runtime-thread-error-snapshot', runtime_upload_snapshot, 'thread_exception', True)
        except Exception:
            pass
    except Exception:
        pass
    try:
        old = getattr(threading, '__excepthook__', None)
        if old:
            old(args)
    except Exception:
        pass

def runtime_install_signal_handlers():
    try:
        signal.signal(signal.SIGTERM, _runtime_signal_handler)
        signal.signal(signal.SIGINT, _runtime_signal_handler)
        sys.excepthook = _runtime_main_excepthook
        if hasattr(threading, 'excepthook'):
            threading.excepthook = _runtime_thread_excepthook
        runtime_event('signal_handlers', 'SIGTERM/SIGINT + Python/thread exception hooks installed')
    except Exception as e:
        runtime_event('signal_handler_error', str(e), 'WARN')

def _fmt_runtime_age(seconds) -> str:
    try:
        sec = max(0, int(float(seconds)))
    except Exception:
        return '—'
    d, sec = divmod(sec, 86400)
    h, sec = divmod(sec, 3600)
    m, sec = divmod(sec, 60)
    if d:
        return f'{d}д {h:02d}:{m:02d}:{sec:02d}'
    return f'{h:02d}:{m:02d}:{sec:02d}'

def build_runtime_watcher_text() -> str:
    snap = runtime_snapshot()
    st = snap.get('state') or {}
    ren = snap.get('render') or {}
    proc = snap.get('process') or {}
    disk = snap.get('disk') or {}
    mega = snap.get('mega_tasks') or {}
    audit = snap.get('audit_metrics') or {}
    memrt = snap.get('memory_runtime') or {}
    memquick = memrt.get('quick') or {}
    memstate = memrt.get('state') or {}
    prev = snap.get('previous_runtime') or {}
    prev_state = prev.get('state') or {}
    prev_render = prev.get('render') or {}
    queues = snap.get('queues') or {}
    status = '🟢 READY' if runtime_is_ready() else '🟠 SHUTDOWN' if runtime_is_shutting_down() else '🟡 BOOT / RECOVERY'
    commit = str(ren.get('RENDER_GIT_COMMIT') or '—')
    instance = str(ren.get('RENDER_INSTANCE_ID') or '—')
    lines = ['🖥 Render / Сервер — Watcher', f'Состояние: {status}', f"Фаза: {st.get('phase') or '—'}", f'Версия: {VERSION}', f"Uptime: {_fmt_runtime_age(proc.get('uptime_seconds'))}", f"Старт: {st.get('started_at') or '—'}", f"READY: {st.get('ready_at') or '—'}", f"BOOT: {(st.get('boot_duration_seconds') if st.get('boot_duration_seconds') is not None else '—')} сек", '', 'Render:', f"Instance: {(instance[-28:] if instance != '—' else instance)}", f"Commit: {(commit[:12] if commit != '—' else commit)}", f"Service: {ren.get('RENDER_SERVICE_NAME') or ren.get('RENDER_SERVICE_ID') or '—'}", f"Region/type: {ren.get('RENDER_REGION') or '—'} / {ren.get('RENDER_SERVICE_TYPE') or '—'}", f"PID/host: {proc.get('pid')} / {proc.get('hostname')}", '', 'Ресурсы:', f"Python RAM: {(proc.get('rss_mb') if proc.get('rss_mb') is not None else '—')} MB; пик: {(proc.get('peak_rss_mb') if proc.get('peak_rss_mb') is not None else '—')} MB", f"Контейнер RAM: {(proc.get('container_current_mb') if proc.get('container_current_mb') is not None else '—')} MB; пик: {(proc.get('container_peak_mb') if proc.get('container_peak_mb') is not None else '—')} MB", f"RAM лимит cgroup: {(proc.get('limit_mb') if proc.get('limit_mb') is not None else '—')} MB; контейнер: {(proc.get('container_percent_limit') if proc.get('container_percent_limit') is not None else '—')}%", f"Memory guard: {memrt.get('level') or '—'} | trim {memstate.get('trim_count', '—')} | malloc_trim {memstate.get('malloc_trim_count', '—')} | blocked exports {memstate.get('blocked_heavy_jobs', '—')}", f"Дочерние процессы: {len(memrt.get('children') or [])}; RAM детей {memrt.get('children_rss_mb', '—')} MB", f"Диск: занято {(disk.get('used_mb') if disk.get('used_mb') is not None else '—')} MB; свободно {(disk.get('free_mb') if disk.get('free_mb') is not None else '—')} MB", f"Потоков Python: {proc.get('threads')}", f"Runtime объекты: операции {audit.get('operation_items', '—')} | integrity {audit.get('integrity_events', '—')} | forward outcomes {audit.get('forward_outcomes', '—')} | fin batches {audit.get('finance_forward_batches', '—')}", f"Кэши/буферы: finance {audit.get('finance_cache_entries', '—')} | expense {audit.get('expense_drafts', '—')} | journal {audit.get('journal_buffer_rows', '—')} | reminder mode {audit.get('reminder_mode', '—')}", '', 'BOOT / Telegram gate:', f"Restore: attempted={st.get('restore_attempted')} ok={st.get('restore_ok')} | {str(st.get('restore_detail') or '—')[:220]}", f"Recovery: start {st.get('task_recovery_started_at') or '—'} | finish {st.get('task_recovery_finished_at') or '—'} | осталось {st.get('task_recovery_remaining', 0)}", f"Webhook получено: {st.get('webhook_received', 0)}", f"Последний: {st.get('last_webhook_at') or '—'} | {st.get('last_webhook_type') or '—'} | update {st.get('last_webhook_update_id') or '—'} | chat {st.get('last_webhook_chat_id') or '—'}", f"Отклонено BOOT: {st.get('webhook_blocked_boot', 0)} | SHUTDOWN: {st.get('webhook_blocked_shutdown', 0)}", '', 'Очереди P/A | done err rej | max wait:']
    for name in ('content', 'ui', 'callback-ack', 'recovery', 'reminder', 'finance', 'fin-forward', 'forward', 'delta', 'backup', 'export', 'general', 'maintenance', 'journal', 'delayed', 'dozvon'):
        q = queues.get(name) or {}
        lines.append(f"{name}: {q.get('pending', 0)}/{q.get('active', 0)} | {q.get('completed', 0)} {q.get('failed', 0)} {q.get('rejected', 0)} | {q.get('max_wait', 0)}с")
    ack_delayed = snap.get('callback_ack_delayed') or {}
    lines.append(f"callback ACK timers: active {ack_delayed.get('scheduled', 0)} | done {ack_delayed.get('executed', 0)} | cancelled {ack_delayed.get('cancelled', 0)} | dispatch err {ack_delayed.get('dispatch_failed', 0)}")
    delta = snap.get('delta') or {}
    keep = snap.get('keep_alive') or {}
    lines.extend(['', 'MEGA durable tasks / delta:', f"tasks: pending {mega.get('pending', 0)} | running {mega.get('running', 0)} | failed {mega.get('failed', 0)} | done {mega.get('done', 0)} | processing {mega.get('processing', 0)}", f"task counters: saved {mega.get('persisted', 0)} | recovered {mega.get('recovered', 0)} | done {mega.get('completed', 0)} | skip {mega.get('skipped_done', 0)} | save err {mega.get('persist_errors', 0)} | final err {mega.get('finalize_errors', 0)}", f"task last error: {str(mega.get('last_error') or 'нет')[:220]}", f"delta: pending chats {delta.get('pending_chats', 0)} | last {delta.get('last_success_at') or '—'} | events {delta.get('last_event_count', 0)}", f"delta file: {os.path.basename(str(delta.get('last_file') or '—'))}", f"delta error: {str(delta.get('last_error') or 'нет')[:220]}", f"keep-alive: last ok {keep.get('last_ok_at') or keep.get('last_success_at') or '—'} | last error {str(keep.get('last_error') or 'нет')[:160]}", '', 'SHUTDOWN:', f"start {st.get('shutdown_started_at') or '—'} | finish {st.get('shutdown_finished_at') or '—'} | signal {st.get('shutdown_signal') or '—'}", f"drain={st.get('shutdown_drain_ok')} | final delta={st.get('shutdown_delta_ok')}", '', 'Предыдущий запуск:', f"Классификация: {st.get('previous_reason') or '—'}", f"Предыдущий state: {prev_state.get('phase') or '—'}", f"Предыдущий snapshot: {prev.get('captured_at') or '—'}", f"Предыдущий старт: {prev_state.get('started_at') or '—'}", f"Предыдущий shutdown: {prev_state.get('shutdown_finished_at') or 'не зафиксирован'}", f"Предыдущий signal: {prev_state.get('shutdown_signal') or '—'}", f"Предыдущий instance: {str(prev_render.get('RENDER_INSTANCE_ID') or '—')[-28:]}", f"Предыдущий commit: {str(prev_render.get('RENDER_GIT_COMMIT') or '—')[:12]}", '', f"Последняя ошибка Watcher: {str(st.get('last_error') or 'нет')[:300]}", '', lowram_status_text() if 'lowram_status_text' in globals() else 'LOW-RAM: —'])
    return wm_owner('\n'.join(lines), 12)

def build_runtime_events_text(limit: int=14) -> str:
    with _RUNTIME_LOCK:
        rows = list(_RUNTIME_EVENTS)[-max(1, int(limit)):]
    lines = ['📜 Runtime события (последние)']
    if not rows:
        lines.append('Событий пока нет.')
    for row in rows:
        lines.append(f"{row.get('ts', '')} [{row.get('level', '')}] {row.get('event', '')} — {row.get('detail', '')[:180]}")
    return wm_owner('\n'.join(lines), 13)

def lowram_database_remote_dir() -> str:
    return MEGA_BACKUP_DIR.rstrip('/') + '/' + LOWRAM_DB_REMOTE_DIR_NAME

def lowram_database_remote_latest() -> str:
    return lowram_database_remote_dir().rstrip('/') + '/' + LOWRAM_DB_LATEST_NAME

def _lowram_gzip_file(src: str, dst: str):
    with open(src, 'rb') as fin, gzip.open(dst, 'wb', compresslevel=5) as fout:
        shutil.copyfileobj(fin, fout, length=1024 * 1024)
    return dst

def _lowram_gunzip_file(src: str, dst: str):
    with gzip.open(src, 'rb') as fin, open(dst, 'wb') as fout:
        shutil.copyfileobj(fin, fout, length=1024 * 1024)
    return dst
_CONSTITUTION_BLOCK_LOG_LAST = 0.0

def _constitution_snapshot_block_notice(reason: str) -> None:
    """One warning per 30 min; the original quarantine event is the actionable ERROR."""
    global _CONSTITUTION_BLOCK_LOG_LAST
    now_m = time.monotonic()
    if now_m - float(_CONSTITUTION_BLOCK_LOG_LAST or 0.0) < 1800.0:
        return
    _CONSTITUTION_BLOCK_LOG_LAST = now_m
    try:
        runtime_event('data_constitution_snapshot_still_blocked', str(reason or 'quarantine')[:700], 'WARN')
    except Exception:
        pass
    log_info(f"[DATA CONSTITUTION] snapshot still blocked: {str(reason or 'quarantine')[:500]}")

def _canon_mega_upload_latest_database_backup__001(force: bool=False) -> bool:
    """v185 DATA CONSTITUTION snapshot: immutable generation + semantic manifest.

    Canonical source of truth is current_manifest.json -> immutable generation_*.sqlite3.gz.
    v203 does not duplicate the large gzip into a legacy mirror unless explicitly enabled.
    """
    if not mega_is_configured():
        return False
    if not force:
        _gate = globals().get('v239_external_durable_write_allowed')
        if callable(_gate):
            _ok, _why = _gate()
            if not _ok:
                _constitution_snapshot_block_notice(str(_why))
                return False
        own_quarantine = bool(globals().get('DATA_CONSTITUTION_QUARANTINE', False))
        if own_quarantine:
            recover_fn = globals().get('constitution_try_auto_clear_quarantine')
            recovered = bool(recover_fn()) if callable(recover_fn) else False
            if not recovered:
                _constitution_snapshot_block_notice(globals().get('DATA_CONSTITUTION_REASON', '') or RESTORE_GUARD_REASON or 'quarantine')
                return False
        if RESTORE_GUARD_ACTIVE:
            _constitution_snapshot_block_notice(RESTORE_GUARD_REASON)
            return False
        if globals().get('constitution_quarantine_active') and constitution_quarantine_active():
            _constitution_snapshot_block_notice(globals().get('DATA_CONSTITUTION_REASON', '') or 'quarantine')
            return False
    with MEGA_GLOBAL_BACKUP_LOCK:
        workdir = tempfile.mkdtemp(prefix='lowram_db_snapshot_')
        try:
            with _delta_state_lock:
                capture_generation = int(_delta_generation)
            raw = os.path.join(workdir, 'bot_state.sqlite3')
            gz = os.path.join(workdir, f"candidate_bot_state_{now_local().strftime('%Y%m%d_%H%M%S_%f')}.sqlite3.gz")
            with data_lock:
                _lowram_flush_all_hot(evict=False)
                created_at = now_local().isoformat(timespec='seconds')
                legacy_mirror_enabled = bool(_env_bool('MEGA_LEGACY_DB_MIRROR_ENABLED', '0'))
                SQLITE.set_meta('db_snapshot', 'main', {'created_at': created_at, 'bot_version': VERSION, 'schema': 3, 'data_constitution': 2, 'fast_boot_mirror': int(legacy_mirror_enabled)})
                try:
                    semantic_fn = globals().get('constitution_semantic_manifest_from_live')
                    if callable(semantic_fn):
                        embedded = semantic_fn() or {}
                        embedded['snapshot_created_at'] = created_at
                        SQLITE.set_meta('data_constitution_snapshot', 'main', embedded)
                except Exception as _embed_exc:
                    log_error(f'[DATA CONSTITUTION EMBED] {_embed_exc}')
                SQLITE.backup_to(raw)
            _lowram_gzip_file(raw, gz)
            preflight = globals().get('config_guard_snapshot_preflight_v234')
            if callable(preflight):
                cfg_ok, cfg_detail = preflight(raw)
                if not cfg_ok:
                    raise RuntimeError('transient config snapshot mismatch: ' + str(cfg_detail))
            publish = globals().get('constitution_publish_sqlite_generation')
            if not callable(publish):
                raise RuntimeError('DATA CONSTITUTION publisher unavailable')
            manifest = publish(raw, gz, created_at)
            initialize_delta_baseline(data)
            global _global_snapshot_pending, _global_snapshot_last_success_monotonic, _global_snapshot_last_success_at
            with _delta_state_lock:
                newer = int(_delta_generation) > int(capture_generation)
                _global_snapshot_pending = bool(newer)
                _global_snapshot_last_success_monotonic = time.monotonic()
                _global_snapshot_last_success_at = created_at
            DELAYED_SCHEDULER.cancel('mega-global-max-v90')
            DELAYED_SCHEDULER.cancel('mega-global-quiet-v90')
            if newer:
                _mark_global_snapshot_pending()
            try:
                history = lowram_database_remote_dir().rstrip('/') + '/history'
                _mega_prune_remote_history(history, 'bot_state_*.sqlite3.gz', max(12, int(LOWRAM_DB_HISTORY_KEEP)))
            except Exception:
                pass
            try:
                _prune_delta_files_after_full_snapshot()
            except Exception:
                pass
            with _LOWRAM_LOCK:
                _LOWRAM_STATS['db_snapshots'] += 1
                _LOWRAM_STATS['last_snapshot_at'] = created_at
            log_info(f"[DATA CONSTITUTION SNAPSHOT] active={manifest.get('generation')} records={manifest.get('total_records')} bytes={os.path.getsize(gz)}")
            return True
        except Exception as e:
            with _LOWRAM_LOCK:
                _LOWRAM_STATS['db_snapshot_errors'] += 1
                _LOWRAM_STATS['last_error'] = str(e)[:300]
            if str(e).startswith('transient snapshot mismatch:'):
                try:
                    runtime_event('data_constitution_snapshot_retry', str(e)[:700], 'WARN')
                except Exception:
                    pass
                log_info(f'[DATA CONSTITUTION SNAPSHOT RETRY] {e}')
            else:
                log_error(f'[MEGA DB SNAPSHOT ERROR] {e}')
            return False
        finally:
            shutil.rmtree(workdir, ignore_errors=True)
            try:
                import gc
                gc.collect()
            except Exception:
                pass

def _v177_legacy_0085_mega_restore_sqlite_snapshot_from_cloud(force: bool=False) -> tuple[bool, str]:
    """Restore canonical generation first; fallback to legacy latest mirror.

    v241: ``force=True`` is reserved for an explicit owner recovery command.  It
    bypasses only the same-instance "local is newer" shortcut; checksum, SQLite
    integrity and Data Constitution validation remain mandatory.
    """
    global _LOWRAM_DB_RESTORED_THIS_BOOT, _LOWRAM_DB_RESTORE_DETAIL
    if not (LOWRAM_ENABLED and mega_is_configured()):
        return (False, 'LOWRAM/MEGA unavailable')
    workdir = tempfile.mkdtemp(prefix='lowram_db_restore_')
    try:
        mega_login_if_needed()
        try:
            mega_ensure_remote_dir()
        except Exception:
            pass
        gz = None
        active_manifest = None
        source = ''
        resolver = globals().get('constitution_download_best_boot_generation_v235') or globals().get('constitution_download_active_generation')
        if callable(resolver):
            try:
                gz, active_manifest, source = resolver(workdir)
            except Exception as exc:
                log_error(f'[DATA CONSTITUTION RESTORE] generation resolver: {exc}')
        if not gz:
            remote = lowram_database_remote_latest()
            res = _mega_run('mega-get', [remote, workdir], check=False, timeout=MEGA_TIMEOUT)
            if res.returncode == 0:
                candidates = list(Path(workdir).rglob(LOWRAM_DB_LATEST_NAME))
                if candidates:
                    gz = str(candidates[0])
                    source = 'legacy protected latest mirror'
        if not gz:
            return (False, 'MEGA SQLite snapshot/generation not found yet')
        raw = os.path.join(workdir, 'restored.sqlite3')
        _lowram_gunzip_file(gz, raw)
        test = sqlite3.connect(raw)
        remote_created = ''
        try:
            row = test.execute('PRAGMA quick_check').fetchone()
            if not row or str(row[0]).lower() != 'ok':
                raise RuntimeError(f'SQLite quick_check failed: {row}')
            try:
                mrow = test.execute("SELECT v FROM meta WHERE kind='db_snapshot' AND k='main'").fetchone()
                if mrow:
                    remote_created = str((json.loads(mrow[0]) or {}).get('created_at') or '')
            except Exception:
                remote_created = ''
            embedded_manifest = {}
            try:
                erow = test.execute("SELECT v FROM meta WHERE kind='data_constitution_snapshot' AND k='main'").fetchone()
                embedded_manifest = json.loads(erow[0]) if erow and erow[0] else {}
                if not isinstance(embedded_manifest, dict):
                    embedded_manifest = {}
            except Exception:
                embedded_manifest = {}
        finally:
            test.close()
        if active_manifest and str(active_manifest.get('sqlite_sha256') or ''):
            with open(raw, 'rb') as _fh:
                _actual_sha = hashlib.sha256(_fh.read()).hexdigest()
            if _actual_sha != str(active_manifest.get('sqlite_sha256') or ''):
                raise RuntimeError(f"active generation checksum mismatch: {_actual_sha[:12]} != {str(active_manifest.get('sqlite_sha256') or '')[:12]}")
        semantic_fn = globals().get('constitution_semantic_manifest_from_sqlite')
        if callable(semantic_fn):
            semantic = semantic_fn(raw)
            if embedded_manifest:
                if int(semantic.get('total_records') or 0) != int(embedded_manifest.get('total_records') or 0):
                    raise RuntimeError(f"embedded semantic mismatch: records {semantic.get('total_records')} != {embedded_manifest.get('total_records')}")
                for _cid, _old in (embedded_manifest.get('chats') or {}).items():
                    _new = (semantic.get('chats') or {}).get(str(_cid)) or {}
                    if int((_new or {}).get('record_count') or 0) != int((_old or {}).get('record_count') or 0):
                        raise RuntimeError(f"embedded semantic mismatch chat {_cid}: {(_new or {}).get('record_count')} != {(_old or {}).get('record_count')}")
                if int(semantic.get('integrity_seq') or 0) != int(embedded_manifest.get('integrity_seq') or 0):
                    raise RuntimeError(f"embedded integrity mismatch: {semantic.get('integrity_seq')} != {embedded_manifest.get('integrity_seq')}")
            if active_manifest:
                if int(semantic.get('total_records') or 0) != int(active_manifest.get('total_records') or 0):
                    raise RuntimeError(f"active generation semantic mismatch: records {semantic.get('total_records')} != manifest {active_manifest.get('total_records')}")
                for cid, old in (active_manifest.get('chats') or {}).items():
                    got = (semantic.get('chats') or {}).get(str(cid)) or {}
                    if int(got.get('record_count') or 0) != int((old or {}).get('record_count') or 0):
                        raise RuntimeError(f"active generation semantic mismatch chat={cid}: {got.get('record_count')} != {(old or {}).get('record_count')}")
        local_root = SQLITE.load_root() or {}
        local_saved = str((local_root.get('_state_meta') or {}).get('last_saved_at') or '') if isinstance(local_root, dict) else ''
        local_has_state = bool(SQLITE.load_chats()) or SQLITE.cold_count() > 0
        if not force and local_has_state and (_parse_iso_timestamp(local_saved) > _parse_iso_timestamp(remote_created) + 1):
            _LOWRAM_DB_RESTORED_THIS_BOOT = True
            _LOWRAM_DB_RESTORE_DETAIL = f"kept fresher local ({local_saved}) over cloud ({remote_created or 'unknown'})"
            with _LOWRAM_LOCK:
                _LOWRAM_STATS['last_restore_at'] = now_local().isoformat(timespec='seconds')
            log_info(f'[MEGA DB RESTORE] {_LOWRAM_DB_RESTORE_DETAIL}')
            return (True, _LOWRAM_DB_RESTORE_DETAIL)
        SQLITE.replace_database(raw)
        if active_manifest:
            try:
                SQLITE.set_meta('boot_restore_binding_v240', 'selected', {'generation': str(active_manifest.get('generation') or ''), 'storage_lineage_v239': str(active_manifest.get('storage_lineage_v239') or ''), 'config_generation_v240': int(active_manifest.get('config_generation_v240') or 0), 'config_hash_v240': str(active_manifest.get('config_hash_v240') or ''), 'config_lineage_v240': str(active_manifest.get('config_lineage_v240') or active_manifest.get('storage_lineage_v239') or '')})
            except Exception:
                pass
        meta = SQLITE.get_meta('db_snapshot', 'main', {}) or {}
        _LOWRAM_DB_RESTORED_THIS_BOOT = True
        _LOWRAM_DB_RESTORE_DETAIL = str(meta.get('created_at') or remote_created or 'unknown')
        with _LOWRAM_LOCK:
            _LOWRAM_STATS['db_restores'] += 1
            _LOWRAM_STATS['last_restore_at'] = now_local().isoformat(timespec='seconds')
        log_info(f'[DATA CONSTITUTION RESTORE] restored {source}; created_at={_LOWRAM_DB_RESTORE_DETAIL}')
        return (True, f'{source}: SQLite snapshot {_LOWRAM_DB_RESTORE_DETAIL}')
    except Exception as e:
        with _LOWRAM_LOCK:
            _LOWRAM_STATS['last_error'] = str(e)[:300]
        try:
            if 'constitution_set_quarantine' in globals():
                constitution_set_quarantine(f'restore failed: {e}')
        except Exception:
            pass
        log_error(f'[MEGA DB RESTORE ERROR] {e}')
        return (False, str(e)[:300])
    finally:
        shutil.rmtree(workdir, ignore_errors=True)
try:
    _v177_legacy_0085_mega_restore_sqlite_snapshot_from_cloud.__name__ = 'mega_restore_sqlite_snapshot_from_cloud'
except Exception:
    pass

def _lowram_apply_delta_to_live_state(delta: dict):
    """Apply one compact delta to metadata + SQLite cold finance history without global materialization."""
    if not isinstance(delta, dict):
        return
    for key in delta.get('root_deletes') or []:
        if key not in _DELTA_VOLATILE_ROOT_KEYS:
            data.pop(str(key), None)
    for key, value in (delta.get('root_patch') or {}).items():
        if key not in _DELTA_VOLATILE_ROOT_KEYS:
            data[str(key)] = _delta_json_clone(value)
    for key, entries in (delta.get('root_map_patches') or {}).items():
        target = data.setdefault(str(key), {})
        if not isinstance(target, dict):
            target = {}
            data[str(key)] = target
        for entry, value in (entries or {}).items():
            target[str(entry)] = _delta_json_clone(value)
    for key, entries in (delta.get('root_map_deletes') or {}).items():
        target = data.get(str(key))
        if isinstance(target, dict):
            for entry in entries or []:
                target.pop(str(entry), None)
    chats = data.setdefault('chats', {})
    changed = []
    for cid_s, change in (delta.get('chat_changes') or {}).items():
        if not isinstance(change, dict):
            continue
        try:
            cid = int(cid_s)
        except Exception:
            continue
        store = chats.get(str(cid))
        if not isinstance(store, ColdChatStore):
            store = _lowram_wrap_store(cid, store if isinstance(store, dict) else {})
            chats[str(cid)] = store
        for key in change.get('chat_meta_deletes') or []:
            dict.pop(store, str(key), None)
        meta = change.get('chat_meta')
        if isinstance(meta, dict):
            for key, value in meta.items():
                dict.__setitem__(store, str(key), _delta_json_clone(value))
        for key, value in (change.get('chat_meta_patch') or {}).items():
            if str(key) not in LOWRAM_COLD_KEYS:
                dict.__setitem__(store, str(key), _delta_json_clone(value))
        records = SQLITE.get_cold(cid, 'records', []) or []
        current = {_delta_record_key(rec): rec for rec in records if isinstance(rec, dict)}
        for key in change.get('deletes') or []:
            current.pop(str(key), None)
        for item in change.get('upserts') or []:
            if isinstance(item, dict) and isinstance(item.get('record'), dict):
                current[str(item.get('key') or _delta_record_key(item['record']))] = _delta_json_clone(item['record'])
        records = sorted(current.values(), key=record_sort_key)
        SQLITE.set_cold(cid, 'records', records)
        SQLITE.set_cold(cid, 'daily_records', _lowram_rebuild_daily(records))
        dict.__setitem__(store, 'balance', sum((float(r.get('amount', 0) or 0) for r in records if isinstance(r, dict))))
        SQLITE.save_chat(cid, _lowram_store_meta_payload(store))
        changed.append(cid)
        records = current = None
    SQLITE.save_root(_sqlite_pack_root(data))

def _canon_v177_download_remote_json_batch__001(remote_paths: list[str], batch_threshold: int=6) -> tuple[dict, list[str]]:
    """Download many MEGA files by parent directory instead of one mega-get per delta.

    Returns {remote_path: local_path} plus temporary directories to remove.  Small groups
    and failed folder downloads fall back to the old exact-file path.
    """
    paths = [str(x) for x in remote_paths or [] if str(x or '').strip()]
    mapping = {}
    cleanup_dirs = []
    grouped = defaultdict(list)
    for remote in paths:
        parent = remote.rsplit('/', 1)[0] if '/' in remote else remote
        grouped[parent].append(remote)
    for parent, group in grouped.items():
        if len(group) >= int(batch_threshold):
            workdir = tempfile.mkdtemp(prefix='v177_mega_batch_')
            cleanup_dirs.append(workdir)
            try:
                _mega_run('mega-get', [parent, workdir], check=True, timeout=max(float(MEGA_TIMEOUT), 180.0))
                found = {}
                for base, _dirs, files in os.walk(workdir):
                    for name in files:
                        found.setdefault(name, os.path.join(base, name))
                for remote in group:
                    local = found.get(os.path.basename(remote))
                    if local and os.path.isfile(local):
                        mapping[remote] = local
            except Exception as exc:
                try:
                    log_error(f'[MEGA BATCH RESTORE] folder fallback {parent}: {str(exc)[:240]}')
                except Exception:
                    pass
        for remote in group:
            if remote in mapping:
                continue
            local = _mega_download_remote_path(remote)
            if local:
                mapping[remote] = local
                cleanup_dirs.append(os.path.dirname(local))
    return (mapping, cleanup_dirs)
_LOWRAM_BOOT_APPLIED_DELTA_PATHS = set()

def _canon_lowram_apply_deltas_after_db_snapshot__001() -> int:
    if not _LOWRAM_DB_RESTORED_THIS_BOOT:
        return 0
    meta = SQLITE.get_meta('db_snapshot', 'main', {}) or {}
    created_at = str(meta.get('created_at') or '')
    if not created_at:
        return 0
    remote_rows = [p for p in _delta_remote_candidates_after(created_at) if p not in _LOWRAM_BOOT_APPLIED_DELTA_PATHS]
    snapshot_lineage = ''
    try:
        _lineage_fn = globals().get('_v239_storage_lineage')
        if callable(_lineage_fn):
            snapshot_lineage = str(_lineage_fn(False) or '')
    except Exception:
        snapshot_lineage = ''
    applied = 0
    local_map = {}
    cleanup_dirs = []
    started = time.monotonic()
    try:
        local_map, cleanup_dirs = _v177_download_remote_json_batch(remote_rows)
        for remote_path in remote_rows:
            local = local_map.get(remote_path)
            if not local:
                continue
            delta = _load_json(local, {}) or {}
            if delta.get('kind') != 'telegram_finance_bot_delta':
                continue
            if _parse_iso_timestamp(delta.get('created_at')) <= _parse_iso_timestamp(created_at):
                continue
            delta_lineage = str(delta.get('storage_lineage_v239') or '')
            if snapshot_lineage and delta_lineage != snapshot_lineage:
                try:
                    runtime_event('delta_lineage_skipped_v239', f"snapshot={snapshot_lineage}; delta={delta_lineage or 'legacy'}; file={os.path.basename(remote_path)}", 'WARN')
                except Exception:
                    pass
                _LOWRAM_BOOT_APPLIED_DELTA_PATHS.add(remote_path)
                continue
            _lowram_apply_delta_to_live_state(delta)
            applied += 1
            _LOWRAM_BOOT_APPLIED_DELTA_PATHS.add(remote_path)
    finally:
        for folder in sorted(set(cleanup_dirs), key=len, reverse=True):
            try:
                shutil.rmtree(folder, ignore_errors=True)
            except Exception:
                pass
    if applied:
        _load_forward_index_from_data(data)
        log_info(f'[MEGA DB RESTORE] applied {applied} compact deltas after SQLite snapshot in {time.monotonic() - started:.1f}s')
    return applied

def mega_upload_latest_global_backup(force: bool=False) -> bool:
    """v114: automatic full snapshot is the SQLite working DB; legacy global JSON is optional."""
    if LOWRAM_ENABLED and (not LOWRAM_LEGACY_GLOBAL_JSON):
        return mega_upload_latest_database_backup(force=force)
    if not mega_is_configured():
        return False
    if RESTORE_GUARD_ACTIVE and (not force):
        log_error(f'[MEGA BACKUP BLOCKED BY RESTORE GUARD] {RESTORE_GUARD_REASON}')
        return False
    with MEGA_GLOBAL_BACKUP_LOCK:
        candidate_path = None
        try:
            with _delta_state_lock:
                snapshot_capture_generation = int(_delta_generation)
            os.makedirs(MEGA_LOCAL_TMP_DIR, exist_ok=True)
            stamp = now_local().strftime('%Y%m%d_%H%M%S_%f')
            candidate_name = f'candidate_global_{stamp}.json'
            candidate_path = os.path.join(MEGA_LOCAL_TMP_DIR, candidate_name)
            save_global_backup_snapshot(candidate_path)
            candidate_payload = _load_json(candidate_path, {}) or {}
            candidate_stats = _global_payload_stats(candidate_payload, candidate_path)
            current_path = mega_download_latest_global_backup()
            current_payload = _load_json(current_path, {}) if current_path else {}
            current_stats = _global_payload_stats(current_payload, current_path) if _global_payload_is_structurally_valid(current_payload) else None
            rejection = '' if force else _global_candidate_rejection(candidate_stats, current_stats)
            if rejection:
                _set_restore_guard('dangerous MEGA overwrite prevented: ' + rejection)
                log_error(f'[MEGA GLOBAL REJECTED] candidate={candidate_stats} current={current_stats}')
                return False
            mega_ensure_remote_path(MEGA_BACKUP_DIR)
            mega_ensure_remote_path(mega_history_remote_dir())
            _mega_run('mega-put', [candidate_path, MEGA_BACKUP_DIR], check=True, timeout=MEGA_TIMEOUT)
            remote_candidate = MEGA_BACKUP_DIR.rstrip('/') + '/' + candidate_name
            remote_latest = mega_remote_file_path(MEGA_LATEST_GLOBAL_NAME)
            archive_name = None
            if current_path and current_stats:
                old_stamp = re.sub('[^0-9]', '', current_stats.get('created_at', ''))[:14] or stamp
                archive_name = f"global_{old_stamp}_{current_stats.get('record_count', 0)}r_{stamp}.json"
            if not _mega_promote_remote_candidate(remote_candidate, remote_latest, history_dir=mega_history_remote_dir() if archive_name else None, archive_name=archive_name):
                raise RuntimeError('cannot activate latest_global.json in MEGA')
            initialize_delta_baseline(candidate_payload)
            global _global_snapshot_pending, _global_snapshot_last_success_monotonic, _global_snapshot_last_success_at
            with _delta_state_lock:
                newer_changes_exist = int(_delta_generation) > int(snapshot_capture_generation)
                _global_snapshot_pending = bool(newer_changes_exist)
                _global_snapshot_last_success_monotonic = time.monotonic()
                _global_snapshot_last_success_at = now_local().isoformat(timespec='seconds')
            DELAYED_SCHEDULER.cancel('mega-global-max-v90')
            DELAYED_SCHEDULER.cancel('mega-global-quiet-v90')
            if newer_changes_exist:
                _mark_global_snapshot_pending()
            try:
                _mega_prune_remote_history(mega_history_remote_dir(), 'global_*.json', MEGA_GLOBAL_HISTORY_KEEP)
                _prune_delta_files_after_full_snapshot()
            except Exception:
                pass
            log_info(f'[MEGA] guarded latest uploaded: {remote_latest}; stats={candidate_stats}')
            return True
        except Exception as e:
            log_error(f'[MEGA BACKUP ERROR] {e}')
            return False
        finally:
            try:
                import gc
                gc.collect()
            except Exception:
                pass

def is_data_effectively_empty_for_restore(d: dict) -> bool:
    """True, если база похожа на пустую после нового deploy/restart Render."""
    if not isinstance(d, dict):
        return True
    if d.get('forward_rules') or d.get('forward_finance'):
        return False
    chats = d.get('chats', {}) or {}
    if not chats:
        return True
    for _, store in chats.items():
        if not isinstance(store, dict):
            continue
        if LOWRAM_ENABLED:
            try:
                cid_i = int(_)
            except Exception:
                cid_i = None
            if cid_i is not None:
                if SQLITE.get_cold(cid_i, 'records', []) or SQLITE.get_cold(cid_i, 'secret_messages', []):
                    return False
        else:
            if store.get('records'):
                return False
            daily = store.get('daily_records') or {}
            if any((daily.get(day) or [] for day in daily)):
                return False
            if store.get('secret_messages'):
                return False
    return True

def _parse_iso_timestamp(value: str | None) -> float:
    try:
        return datetime.fromisoformat(str(value or '').replace('Z', '+00:00')).timestamp()
    except Exception:
        return 0.0

def _local_restore_stats(d: dict) -> dict:
    """Статистика локальной базы без удержания всей истории в RAM."""
    chats = (d or {}).get('chats', {}) if isinstance(d, dict) else {}
    if not isinstance(chats, dict):
        chats = {}
    records = 0
    nonempty = 0
    secrets = 0
    for cid_s, store in chats.items():
        if not isinstance(store, dict):
            continue
        try:
            cid = int(cid_s)
        except Exception:
            continue
        if LOWRAM_ENABLED:
            recs = SQLITE.get_cold(cid, 'records', []) or []
            sec = SQLITE.get_cold(cid, 'secret_messages', []) or []
        else:
            recs = store.get('records') or []
            sec = store.get('secret_messages') or []
        records += len(recs) if isinstance(recs, list) else 0
        if recs:
            nonempty += 1
        secrets += len(sec) if isinstance(sec, list) else 0
        recs = sec = None
    return {'chat_count': len(chats), 'nonempty_chats': nonempty, 'record_count': records, 'secret_count': secrets, 'forward_rules_count': sum((len(v or {}) for v in ((d or {}).get('forward_rules', {}) or {}).values())), 'forward_index_count': len((d or {}).get('forward_index', {}) or {}), 'last_saved_at': str(((d or {}).get('_state_meta') or {}).get('last_saved_at') or '')}

def _mega_discover_global_candidates(limit: int=60) -> list[str]:
    """Ищет полноценные global JSON во всём каталоге MEGA, а не только exact latest/history.

    Это восстанавливает ситуацию, когда latest_global.json был временно перемещён в history,
    остался candidate_global_*.json после прерванной ротации или файл лежит глубже в каталоге.
    """
    if not mega_is_configured() or shutil.which('mega-find') is None:
        return []
    rows = []
    try:
        mega_login_if_needed()
        for pattern in (MEGA_LATEST_GLOBAL_NAME, 'global_*.json', 'candidate_global_*.json', '*global*.json'):
            res = _mega_run('mega-find', [MEGA_BACKUP_DIR, f'--pattern={pattern}', '--type=f'], check=False, timeout=90)
            rows.extend((x.strip() for x in (res.stdout or '').splitlines() if x.strip().lower().endswith('.json')))
    except Exception as e:
        log_error(f'_mega_discover_global_candidates: {e}')
    latest_path = mega_remote_file_path(MEGA_LATEST_GLOBAL_NAME)
    uniq = []
    seen = set()
    for path in [latest_path] + sorted(set(rows), reverse=True):
        if path and path not in seen:
            seen.add(path)
            uniq.append(path)
    return uniq[:max(1, int(limit))]

def _mega_select_best_global_candidate(limit: int=60) -> tuple[str | None, dict, str]:
    """Скачивает доступные global snapshots и выбирает лучший валидный полный снимок."""
    best_path = None
    best_stats = {}
    best_label = ''
    candidates = _mega_discover_global_candidates(limit=limit)
    direct_latest = mega_download_latest_global_backup()
    local_candidates = []
    if direct_latest:
        local_candidates.append(('latest', direct_latest))
    for remote_path in candidates:
        if remote_path == mega_remote_file_path(MEGA_LATEST_GLOBAL_NAME) and direct_latest:
            continue
        local_candidates.append((remote_path, None))
    for label, local_path in local_candidates:
        try:
            if local_path is None:
                local_path = _mega_download_remote_path(label)
            if not local_path:
                continue
            payload = _load_json(local_path, {}) or {}
            if not _global_payload_is_structurally_valid(payload):
                log_error(f'[MEGA RESTORE] invalid global candidate: {label}')
                continue
            stats = _global_payload_stats(payload, local_path)
            if stats.get('record_count', 0) == 0 and (not ALLOW_EMPTY_MEGA_RESTORE):
                continue
            score = (_parse_iso_timestamp(stats.get('created_at')), int(stats.get('record_count', 0) or 0), int(stats.get('chat_count', 0) or 0), int(stats.get('size_bytes', 0) or 0))
            best_score = (_parse_iso_timestamp(best_stats.get('created_at')), int(best_stats.get('record_count', 0) or 0), int(best_stats.get('chat_count', 0) or 0), int(best_stats.get('size_bytes', 0) or 0)) if best_stats else (-1, -1, -1, -1)
            if score > best_score:
                best_path, best_stats, best_label = (local_path, stats, label)
        except Exception as e:
            log_error(f'[MEGA RESTORE] candidate scan error {label}: {e}')
    return (best_path, best_stats, best_label)

def _mega_select_best_global_candidate_with_retry(limit: int=80) -> tuple[str | None, dict, str]:
    """Повторяет поиск full snapshot после холодного deploy, прежде чем включать guard."""
    last = (None, {}, '')
    for attempt in range(1, int(MEGA_RESTORE_DISCOVERY_RETRIES) + 1):
        try:
            last = _mega_select_best_global_candidate(limit=limit)
            if last[0]:
                if attempt > 1:
                    log_info(f'[MEGA RESTORE] global snapshot found on retry {attempt}: {last[2]}')
                return last
        except Exception as e:
            log_error(f'[MEGA RESTORE] discovery attempt {attempt}/{MEGA_RESTORE_DISCOVERY_RETRIES}: {e}')
        if attempt < int(MEGA_RESTORE_DISCOVERY_RETRIES):
            delay = float(MEGA_RESTORE_DISCOVERY_RETRY_SECONDS) * attempt
            log_info(f'[MEGA RESTORE] snapshot not available yet; retry in {delay:g}s ({attempt}/{MEGA_RESTORE_DISCOVERY_RETRIES})')
            time.sleep(delay)
    return last

def _v177_legacy_0086_mega_restore_full_from_cloud(force: bool=False) -> tuple[bool, str]:
    """Полное восстановление из лучшего global snapshot + всех последующих delta.

    Восстанавливает весь state целиком: chats, records, settings, owners, forwarding,
    forward_index, secret_messages и прочие поля универсального backup.
    """
    global data
    if not mega_is_configured():
        return (False, 'MEGA не настроена')
    local_empty = is_data_effectively_empty_for_restore(data)
    local_stats = _local_restore_stats(data)
    base_path, base_stats, label = _mega_select_best_global_candidate_with_retry(limit=80)
    if not base_path:
        if local_empty:
            _set_restore_guard('local database is empty; no valid full global snapshot found in MEGA')
        return (False, 'В MEGA не найден валидный полный global JSON')
    try:
        merged_path, applied_delta_count = merge_global_snapshot_with_mega_deltas(base_path)
        remote_payload = _load_json(merged_path, {}) or {}
        if not _global_payload_is_structurally_valid(remote_payload):
            return (False, 'Найденный global JSON повреждён после объединения delta')
        remote_stats = _global_payload_stats(remote_payload, merged_path)
        remote_stats['applied_deltas'] = applied_delta_count
        remote_created = str(remote_stats.get('created_at') or '')
        local_saved = str(local_stats.get('last_saved_at') or '')
        remote_newer = _parse_iso_timestamp(remote_created) > _parse_iso_timestamp(local_saved) + 1
        materially_richer = int(remote_stats.get('record_count', 0) or 0) > int(local_stats.get('record_count', 0) or 0) or int(remote_stats.get('chat_count', 0) or 0) > int(local_stats.get('chat_count', 0) or 0)
        local_suspicious = local_empty or (int(local_stats.get('record_count', 0) or 0) == 0 and int(remote_stats.get('record_count', 0) or 0) > 0) or (int(local_stats.get('chat_count', 0) or 0) <= 1 and int(remote_stats.get('chat_count', 0) or 0) > 1)
        if not force and (not (local_suspicious or remote_newer or materially_richer)):
            _clear_restore_guard()
            return (False, f'Локальная база не хуже MEGA; восстановление не требуется. local={local_stats}, mega={remote_stats}')
        restore_chat_id = int(OWNER_ID) if OWNER_ID else 0
        restore_from_json(restore_chat_id, merged_path)
        _restore_runtime_state_from_data(data)
        initialize_delta_baseline(data)
        _clear_restore_guard()
        msg = f"Полное восстановление OK из {label or 'MEGA'}: чатов={remote_stats.get('chat_count', 0)}, записей={remote_stats.get('record_count', 0)}, delta={applied_delta_count}"
        log_info('[MEGA RESTORE FULL] ' + msg)
        return (True, msg)
    except Exception as e:
        log_error(f'[MEGA RESTORE FULL ERROR] {e}')
        if local_empty:
            _set_restore_guard('MEGA full restore failed: ' + str(e)[:500])
        return (False, 'Ошибка полного восстановления: ' + str(e)[:500])
try:
    _v177_legacy_0086_mega_restore_full_from_cloud.__name__ = 'mega_restore_full_from_cloud'
except Exception:
    pass

def mega_autorestore_if_needed() -> bool:
    """Надёжное авто-восстановление: всегда проверяет MEGA и умеет восстановить частичную/старую SQLite."""
    global data
    if not MEGA_AUTORESTORE or not mega_is_configured():
        if is_data_effectively_empty_for_restore(data):
            _set_restore_guard('local database is empty and MEGA autorestore is unavailable')
        return False
    ok, detail = mega_restore_full_from_cloud(force=False)
    log_info(f'[MEGA AUTORESTORE] ok={ok}; {detail}')
    return bool(ok)

def mega_status_text() -> str:
    lines = ['☁️ MEGA.nz / MEGAcmd']
    lines.append(f"MEGA_ENABLED: {('✅ ВКЛ' if MEGA_ENABLED else '⬜ ВЫКЛ')}")
    lines.append(f"MEGA_AUTORESTORE: {('✅ ВКЛ' if MEGA_AUTORESTORE else '⬜ ВЫКЛ')}")
    lines.append(f"RESTORE_GUARD: {('✅ ВКЛ — ' + RESTORE_GUARD_REASON if RESTORE_GUARD_ACTIVE else '⬜ ВЫКЛ')}")
    lines.append(f'MEGA_HISTORY_DIR: {mega_history_remote_dir()}')
    lines.append(f'MEGA_DELTA_DIR: {mega_delta_remote_root()}')
    lines.append(f'Delta delay: {(MEGA_DELTA_PRIORITY_DELAY_SECONDS if mega_backup_priority_enabled() else MEGA_DELTA_DELAY_SECONDS):g} сек')
    lines.append(f'SQLite SYSTEM generation: каждые {system_snapshot_hours_v242()} ч. при изменениях; /restore и ручной backup — сразу.')
    lines.append(f"MEGA_EMAIL: {('есть' if MEGA_EMAIL else 'нет')}")
    lines.append(f'MEGA_BACKUP_DIR: {MEGA_BACKUP_DIR}')
    lines.append(f'MEGA_CHAT_BACKUP_DIR: {MEGA_CHAT_BACKUP_DIR}')
    lines.append(f'MEGA_MONTHLY_BACKUP_DIR: {MEGA_MONTHLY_BACKUP_DIR}')
    missing = mega_missing_commands()
    lines.append(f"MEGAcmd: {('OK' if not missing else 'нет команд: ' + ', '.join(missing))}")
    if mega_is_configured() and (not missing):
        try:
            mega_login_if_needed()
            res = _mega_run('mega-whoami', [], check=False, timeout=30)
            txt = ((res.stdout or '') + (res.stderr or '')).strip()
            if txt:
                lines.append('whoami: ' + txt[:300])
            else:
                lines.append('whoami: OK')
        except Exception as e:
            lines.append('whoami/login: ERROR — ' + str(e)[:300])
    return '\n'.join(lines)

def _load_csv_meta():
    try:
        meta_from_data = (data or {}).get('csv_meta')
        if isinstance(meta_from_data, dict) and meta_from_data:
            return meta_from_data
    except Exception:
        pass
    meta = SQLITE.get_meta('csv_meta', 'main', None)
    if isinstance(meta, dict) and meta:
        try:
            data['csv_meta'] = meta
        except Exception:
            pass
        return meta
    legacy = _load_json(CSV_META_FILE, {})
    if isinstance(legacy, dict) and legacy:
        SQLITE.set_meta('csv_meta', 'main', legacy)
        try:
            data['csv_meta'] = legacy
        except Exception:
            pass
    return legacy if isinstance(legacy, dict) else {}

def _save_csv_meta(meta: dict):
    try:
        meta = meta or {}
        SQLITE.set_meta('csv_meta', 'main', meta)
        try:
            data['csv_meta'] = meta
            save_data(data)
        except Exception:
            pass
        _save_json(CSV_META_FILE, meta)
        log_info('csv_meta updated in sqlite/data')
    except Exception as e:
        log_error(f'_save_csv_meta: {e}')
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CHAT_BACKUP_META_FILE = os.path.join(BASE_DIR, 'chat_backup_meta.json')

def _load_chat_backup_meta() -> dict:
    """Загрузка meta-файла бэкапов для всех чатов."""
    try:
        meta_from_data = (data or {}).get('chat_backup_meta')
        if isinstance(meta_from_data, dict) and meta_from_data:
            return meta_from_data
        meta = SQLITE.get_meta('chat_backup_meta', 'main', None)
        if isinstance(meta, dict) and meta:
            try:
                data['chat_backup_meta'] = meta
            except Exception:
                pass
            return meta
        if not os.path.exists(CHAT_BACKUP_META_FILE):
            return {}
        legacy = _load_json(CHAT_BACKUP_META_FILE, {})
        if isinstance(legacy, dict) and legacy:
            SQLITE.set_meta('chat_backup_meta', 'main', legacy)
            try:
                data['chat_backup_meta'] = legacy
            except Exception:
                pass
        return legacy if isinstance(legacy, dict) else {}
    except Exception as e:
        log_error(f'_load_chat_backup_meta: {e}')
        return {}

def _save_chat_backup_meta(meta: dict) -> None:
    """Сохранение meta-файла, sqlite-копии и data-копии для MEGA autorestore."""
    try:
        meta = meta or {}
        SQLITE.set_meta('chat_backup_meta', 'main', meta)
        try:
            data['chat_backup_meta'] = meta
            save_data(data)
        except Exception:
            pass
        log_info(f'SAVING META TO: {os.path.abspath(CHAT_BACKUP_META_FILE)}')
        _save_json(CHAT_BACKUP_META_FILE, meta)
        log_info('chat_backup_meta updated in sqlite/data')
    except Exception as e:
        log_error(f'_save_chat_backup_meta: {e}')

def send_backup_to_chat(chat_id: int, ensure_files: bool=True) -> None:
    if not can_receive_direct_json_backup(chat_id):
        return
    if is_finance_output_suppressed(chat_id) or not is_backup_to_chat_enabled(chat_id):
        return
    '\n    Авто-бэкап JSON прямо в чат.\n    Работает только для владельца и служебного backup-канала.\n    Логика:\n    • гарантируем актуальный data_<chat_id>.json\n    • читаем meta-файл chat_backup_meta.json\n    • если есть msg_id → edit_message_media()\n    • если нет / не найдено → отправляем новое сообщение\n    • обновляем meta-файл в рабочей директории (Render-friendly)\n    • старое сообщение обновляется всегда; новое создаётся только если старое удалено/недоступно\n    '
    try:
        if not chat_id:
            return
        if ensure_files:
            try:
                save_chat_json(chat_id)
            except Exception as e:
                log_error(f'send_backup_to_chat save_chat_json({chat_id}): {e}')
        json_path = chat_json_file(chat_id)
        if not os.path.exists(json_path):
            log_error(f'send_backup_to_chat: {json_path} NOT FOUND')
            return
        meta = _load_chat_backup_meta()
        msg_key = f'msg_chat_{chat_id}'
        ts_key = f'timestamp_chat_{chat_id}'
        chat_title = _get_chat_title_for_backup(chat_id)
        caption = f"🧾 Авто-бэкап JSON чата: {chat_title}\n⏱ {now_local().strftime('%Y-%m-%d %H:%M:%S')}"
        msg_id = meta.get(msg_key)

        def _open_file() -> io.BytesIO | None:
            """Чтение JSON в BytesIO с правильным именем файла."""
            try:
                with open(json_path, 'rb') as f:
                    data_bytes = f.read()
            except Exception as e:
                log_error(f'send_backup_to_chat open({json_path}): {e}')
                return None
            if not data_bytes:
                return None
            base = os.path.basename(json_path)
            name_no_ext, dot, ext = base.partition('.')
            suffix = get_chat_name_for_filename(chat_id)
            file_name = suffix if suffix else name_no_ext
            if dot:
                file_name += f'.{ext}'
            buf = io.BytesIO(data_bytes)
            buf.name = file_name
            return buf
        if msg_id:
            fobj = _open_file()
            if not fobj:
                return
            try:
                _tg_call_retry(bot.edit_message_media, chat_id=chat_id, message_id=msg_id, media=types.InputMediaDocument(media=fobj, caption=caption), purpose='backup_edit_message_media')
                log_info(f'Chat backup UPDATED in chat {chat_id}')
                meta[ts_key] = now_local().isoformat(timespec='seconds')
                _save_chat_backup_meta(meta)
                return
            except Exception as e:
                log_error(f'send_backup_to_chat edit FAILED in {chat_id}: {e}')
                msg_id = None
        fobj = _open_file()
        if not fobj:
            return
        sent = _tg_call_retry(bot.send_document, chat_id, fobj, caption=caption, purpose='backup_send_document')
        meta[msg_key] = sent.message_id
        meta[ts_key] = now_local().isoformat(timespec='seconds')
        _save_chat_backup_meta(meta)
        log_info(f'Chat backup CREATED in chat {chat_id}')
    except Exception as e:
        log_error(f'send_backup_to_chat({chat_id}): {e}')

def default_data():
    return {'overall_balance': 0, 'records': [], 'chats': {}, 'active_messages': {}, 'next_id': 1, 'backup_flags': {'drive': True, 'channel': True}, 'finance_active_chats': {}, 'forward_rules': {}, 'forward_finance': {}, 'forward_index': {}, 'bot_errors': [], 'csv_meta': {}, 'chat_backup_meta': {}, '_global_settings': {'bot_journal_enabled': True, 'bot_journal_verbose_telegram': False, 'buttons_current_window': True, 'forward_menu_new_style': True, 'icon_button_mode': False, 'total_secret_mask_enabled': False, 'finance_day_start_5am': False, 'finance_day_start_minute': 5, 'backup_excel_all_enabled': True, 'mega_backup_priority': True, 'bot_behavior_profile': 'v97_current', 'journal_default_off_v83_applied': True}}
_ORIGINAL_INLINE_KEYBOARD_BUTTON = types.InlineKeyboardButton

def _compact_button_label(text) -> str:
    label = str(text or '')
    if not icon_button_mode_enabled():
        return label
    exact = {'⬅️ Назад осн. окно': '⬅️', '🔙 Назад': '↩️', '🔙 Назад в Инфо': '↩️ ℹ️', '⏪ Назад к статьям': '↩️ 📊', '❌ Закрыть': '✖️', '❌ Закрыть статьи': '✖️ 📊', '🗑 Удалить статью': '🗑', '🗑 Удалить выбранное': '🗑 ✅', '🗑 Удалить секреты': '🗑🔐', '🗑 День': '🗑 Д', '🗑 Неделя': '🗑 Н', '🗑 Месяц': '🗑 М', '🗑 Всё': '🗑 Всё', '➕ Добавить': '➕', '➕ Добавить статью': '➕', '✏️ Изменить': '✏️', '📅 Сегодня': '📅', '📅 Календарь': '📆', '📆 Выбор недели': '📆', '📚 Описание статей': '📚', '📓 Журнал': '📓', '📄 Скачать TXT': '📄', '📡 Проверить все': '📡', '⬅️ День': '⬅️', 'День ➡️': '➡️', '⬅️ Месяц': '⬅️', 'Месяц ➡️': '➡️', '⬅️ Чт–Ср': '⬅️ Чт', 'Чт–Ср ➡️': 'Чт ➡️', '⬅️ Пн–Вс': '⬅️ Пн', 'Пн–Вс ➡️': 'Пн ➡️', '⬜ Пн–Вс': '⬜ Пн', '🟦 Чт–Ср': '🟦 Чт', '👥 /owners': '👥 /own', 'Нет доступных чатов': 'Нет чатов', 'Нет данных для изменения': 'Нет данных', 'Нет пользовательских статей': 'Нет статей', 'Удалённых нет': 'Нет'}
    if label in exact:
        return exact[label]
    close_match = re.fullmatch('❌ Закрыть (\\d{2}:\\d{2})', label)
    if close_match:
        return f'✖️ {close_match.group(1)}'
    if re.fullmatch('[✅⬜❌] Фин режим (?:ВКЛ|ВЫКЛ)', label):
        return ('✅' if label.startswith('✅') else '⬜') + ' Фин'
    if re.fullmatch('[✅⬜❌] (?:Общий )?журнал(?: чата)? (?:ВКЛ|ВЫКЛ)', label, flags=re.IGNORECASE):
        return ('✅' if label.startswith('✅') else '⬜') + ' 📓'
    if re.fullmatch('[✅⬜❌] Статьи-кнопки (?:ВКЛ|ВЫКЛ)', label):
        return ('✅' if label.startswith('✅') else '⬜') + ' 📚'
    if label.startswith('✅ В текущем окне'):
        return '✅ 🪟'
    if label.startswith(('⬜ В текущем окне', '❌ В текущем окне')):
        return '⬜ 🪟'
    if label.startswith('🧩 Пересылка:') or label.startswith('🔁 Пересылка:'):
        return '🔁/🧩'
    if label.startswith('🔣 Кнопки:') or label.startswith('🔤 Кнопки:'):
        return '🔣/🔤'
    if label.startswith('🪷 Маска:'):
        return '🪷' + ('✅' if 'ВКЛ' in label else '⬜')
    if label in {'☁️ Сразу в MEGA', '🕓 MEGA как обычно'}:
        return '☁️⚡' if 'Сразу' in label else '☁️🕓'
    if re.fullmatch('[✅⬜❌] Секрет', label):
        return ('✅' if label.startswith('✅') else '⬜') + '🔐'
    if label.startswith('🏦 Остаток:'):
        return label.replace('🏦 Остаток:', '🏦', 1)
    if label.startswith('✏️ ') and len(label) > 18:
        return '✏️ ' + label[3:24].strip()
    if label.startswith('☑️ ') or label.startswith('⬛ '):
        return label[:2] + ' ' + label[3:24].strip()
    return label

def IB(text, *args, **kwargs):
    return _ORIGINAL_INLINE_KEYBOARD_BUTTON(_compact_button_label(text), *args, **kwargs)

_USER_STATE_META_KIND_V265_EARLY = 'user_state_shadow_v265'
_USER_STATE_META_KEY_V265_EARLY = 'latest'
_USER_STATE_ROOT_EXCLUDE_V265_EARLY = {'overall_balance', 'records', 'bot_errors', '_state_meta'}
_USER_STATE_CHAT_EXCLUDE_V265_EARLY = set(globals().get('LOWRAM_COLD_KEYS') or set()) | {'balance', 'next_id'}

def _apply_user_state_shadow_early_v266(d):
    """Overlay persisted non-financial user state before any boot defaults/migrations.

    This function intentionally lives in the base storage module: 99_web_runtime calls
    load_data() before 98_split_front is executed, so a late split-only restore hook is
    too late to protect tenant/chat settings from factory defaults.
    """
    if not isinstance(d, dict):
        return d
    try:
        payload = SQLITE.get_meta(_USER_STATE_META_KIND_V265_EARLY, _USER_STATE_META_KEY_V265_EARLY, {}) or {}
    except Exception:
        payload = {}
    if not isinstance(payload, dict) or not payload:
        return d
    # R19 process-level anti-downgrade fence. If any earlier authoritative load in
    # this process observed a newer shadow sequence, a later stale SQLite/legacy
    # restore is not allowed to overlay an older shadow on top of it.
    try:
        incoming_seq = int(payload.get('seq') or 0)
        applied_seq = int(globals().get('_USER_STATE_APPLIED_SEQ_R19', 0) or 0)
        if applied_seq and incoming_seq and incoming_seq < applied_seq:
            log_error(f'USER_STATE R19 stale early shadow rejected seq={incoming_seq} < applied={applied_seq}')
            return d
        globals()['_USER_STATE_APPLIED_SEQ_R19'] = max(applied_seq, incoming_seq)
    except Exception:
        pass
    root_shadow = payload.get('root') or {}
    if isinstance(root_shadow, dict):
        for key, value in root_shadow.items():
            if str(key) not in _USER_STATE_ROOT_EXCLUDE_V265_EARLY:
                d[str(key)] = value
    chats_dst = d.setdefault('chats', {})
    chat_shadow = payload.get('chats') or {}
    if isinstance(chat_shadow, dict):
        for cid, meta in chat_shadow.items():
            if not isinstance(meta, dict):
                continue
            cur = chats_dst.get(str(cid))
            if not isinstance(cur, dict):
                cur = {}
                chats_dst[str(cid)] = cur
            for key, value in meta.items():
                if str(key) not in _USER_STATE_CHAT_EXCLUDE_V265_EARLY:
                    cur[str(key)] = value
    try:
        log_info(f"USER_STATE R6 early restore seq={payload.get('seq')} chats={len(chat_shadow) if isinstance(chat_shadow, dict) else 0}")
    except Exception:
        pass
    return d

def _v177_legacy_0087_load_data():
    _import_legacy_global_json_to_db(DATA_FILE, force=False)
    root = SQLITE.load_root()
    chats = SQLITE.load_chats()
    if root is None and (not chats):
        d = default_data()
    else:
        d = _sqlite_unpack_data(root or {}, chats or {})
    # R6: restore user settings/tenant/UI shadow *before* defaults are filled.
    d = _apply_user_state_shadow_early_v266(d)
    base = default_data()
    for k, v in base.items():
        if k not in d:
            d[k] = v
    flags = d.get('backup_flags') or {}
    backup_flags['drive'] = bool(flags.get('drive', True))
    backup_flags['channel'] = bool(flags.get('channel', True))
    fac = d.get('finance_active_chats') or {}
    finance_active_chats.clear()
    for cid, enabled in fac.items():
        if enabled:
            try:
                finance_active_chats.add(int(cid))
            except Exception:
                pass
    if OWNER_ID:
        try:
            finance_active_chats.add(int(OWNER_ID))
        except Exception:
            pass
    _lowram_prepare_loaded_data(d, migrate_existing=True)
    try:
        _load_forward_index_from_data(d)
        if not (d.get('forward_index') or {}):
            _rebuild_forward_index_from_finance_records(d)
    except Exception as e:
        log_error(f'load_data forward_index: {e}')
    return d
try:
    _v177_legacy_0087_load_data.__name__ = 'load_data'
except Exception:
    pass

def save_data(d, chat_ids=None, full: bool=False, root_only: bool=False):
    """Потокобезопасное сохранение.

    В обработчике конкретного чата SQLite обновляет только этот чат. Полный
    проход по всем чатам выполняется при старте, восстановлении и глобальном
    бэкапе. Это убирает квадратичную нагрузку при 100 активных чатах.
    """
    with data_lock:
        d.setdefault('_state_meta', {})['last_saved_at'] = now_local().isoformat(timespec='seconds')
        d['_state_meta']['bot_version'] = VERSION
        fac = {str(cid): True for cid in list(finance_active_chats)}
        d['finance_active_chats'] = fac
        d['backup_flags'] = {'drive': bool(backup_flags.get('drive', True)), 'channel': bool(backup_flags.get('channel', True))}
        try:
            _persist_forward_index_in_data(d)
        except Exception as e:
            log_error(f'save_data forward_index: {e}')
        SQLITE.save_root(_sqlite_pack_root(d))
        if root_only:
            return
        ids = set()
        if chat_ids is not None:
            if isinstance(chat_ids, (list, tuple, set)):
                source_ids = chat_ids
            else:
                source_ids = [chat_ids]
            for cid in source_ids:
                try:
                    ids.add(int(cid))
                except Exception:
                    pass
        elif not full:
            cid = current_state_chat_id()
            if cid is not None:
                try:
                    ids.add(int(cid))
                except Exception:
                    pass
        chats = d.get('chats', {}) or {}
        if ids and (not full):
            for cid in ids:
                payload = chats.get(str(cid))
                if isinstance(payload, dict):
                    if LOWRAM_ENABLED:
                        _lowram_flush_chat(cid, payload, evict=False)
                        SQLITE.save_chat(cid, _lowram_store_meta_payload(payload))
                    else:
                        SQLITE.save_chat(cid, payload)
        elif LOWRAM_ENABLED:
            meta_chats = {}
            for cid_s, payload in list(chats.items()):
                try:
                    cid = int(cid_s)
                except Exception:
                    continue
                if isinstance(payload, dict):
                    _lowram_flush_chat(cid, payload, evict=False)
                    meta_chats[str(cid)] = _lowram_store_meta_payload(payload)
            SQLITE.save_chats(meta_chats)
        else:
            SQLITE.save_chats(chats)
    try:
        fn = globals().get('config_guard_note_after_save_v234')
        if callable(fn):
            fn('save_data')
    except Exception as exc:
        try:
            log_error(f'config guard save hook v234: {exc}')
        except Exception:
            pass

def chat_json_file(chat_id: int) -> str:
    return f'data_{chat_id}.json'

def chat_csv_file(chat_id: int) -> str:
    return f'data_{chat_id}.csv'

def chat_xlsx_file(chat_id: int) -> str:
    return f'data_{chat_id}.xlsx'

def chat_meta_file(chat_id: int) -> str:
    return f'csv_meta_{chat_id}.json'

def get_chat_store(chat_id: int) -> dict:
    """
    Хранилище данных одного чата.
    Добавлено поле "known_chats" для отображения названий/username в меню пересылки.
    """
    with data_lock:
        chats = data.setdefault('chats', {})
        store = chats.setdefault(str(chat_id), {'info': {}, 'known_chats': {}, 'balance': 0, 'next_id': 1, 'active_windows': {}, 'edit_wait': None, 'edit_target': None, 'current_view_day': today_key(), 'finance_mode': False, 'settings': {'auto_add': True, 'quick_balance_enabled': False, 'quick_balance_behavior': 'normal', 'quick_balance_user_selected': False, 'hidden_finance': False, 'auto_backup_enabled': True, 'auto_backup_to_chat_enabled': True, 'auto_backup_to_channel_enabled': True, 'auto_backup_to_mega_enabled': True, 'journal_enabled': True, 'buttons_current_window': True, 'forward_copy_edit_mode': 'slash', 'main_article_buttons_enabled': False, 'main_financial_value_buttons_enabled': False, 'gomonk_enabled': False, 'gomonk_entries': [], 'remaining_with_gomonk': True, 'usd_gomonk_enabled': False, 'usd_gomonk_entries': [], 'usd_remaining_with_gomonk': True, 'usd_display_enabled': False, 'currency_mode': 'ars', 'remaining_show_ost_label': True}})
        if LOWRAM_ENABLED and (not isinstance(store, ColdChatStore)):
            store = _lowram_wrap_store(int(chat_id), store)
            chats[str(chat_id)] = store
        store.setdefault('settings', {}).setdefault('auto_add', True)
        store.setdefault('settings', {}).setdefault('quick_balance_enabled', False)
        store.setdefault('settings', {}).setdefault('quick_balance_behavior', 'normal')
        store.setdefault('settings', {}).setdefault('quick_balance_user_selected', False)
        store.setdefault('settings', {}).setdefault('hidden_finance', False)
        store.setdefault('settings', {}).setdefault('auto_backup_enabled', True)
        legacy_backup_enabled = bool(store.setdefault('settings', {}).get('auto_backup_enabled', True))
        store.setdefault('settings', {}).setdefault('auto_backup_to_chat_enabled', legacy_backup_enabled)
        store.setdefault('settings', {}).setdefault('auto_backup_to_channel_enabled', legacy_backup_enabled)
        store.setdefault('settings', {}).setdefault('auto_backup_to_mega_enabled', legacy_backup_enabled)
        store.setdefault('settings', {}).setdefault('journal_enabled', True)
        store.setdefault('settings', {}).setdefault('main_article_buttons_enabled', False)
        store.setdefault('settings', {}).setdefault('main_financial_value_buttons_enabled', False)
        store.setdefault('settings', {}).setdefault('gomonk_enabled', False)
        store.setdefault('settings', {}).setdefault('gomonk_entries', [])
        store.setdefault('settings', {}).setdefault('remaining_with_gomonk', True)
        store.setdefault('settings', {}).setdefault('usd_gomonk_enabled', False)
        store.setdefault('settings', {}).setdefault('usd_gomonk_entries', [])
        store.setdefault('settings', {}).setdefault('usd_remaining_with_gomonk', True)
        store.setdefault('settings', {}).setdefault('usd_display_enabled', False)
        store.setdefault('settings', {}).setdefault('currency_mode', 'ars_usd' if store.setdefault('settings', {}).get('usd_display_enabled', False) else 'ars')
        store.setdefault('settings', {}).setdefault('remaining_show_ost_label', True)
        store.setdefault('settings', {}).setdefault('category_usd_enabled', False)
        store.setdefault('settings', {}).setdefault('buttons_current_window', True)
        store.setdefault('settings', {}).setdefault('forward_copy_edit_mode', 'slash')
        store.setdefault('finance_mode', False)
        if is_owner_chat(chat_id):
            store['settings']['auto_add'] = True
        if 'known_chats' not in store:
            store['known_chats'] = {}
        return store

def _chat_identity_key(cid: int, info: dict | None=None) -> str:
    """Безопасный ключ дубля: username можно считать одним чатом, а одинаковый title — только подозрение, не удаление."""
    info = info or {}
    username = str(info.get('username') or '').strip().lower().lstrip('@')
    if username:
        return 'u:' + username
    return 'id:' + str(int(cid))

def _chat_title_suspect_key(cid: int, info: dict | None=None) -> str:
    info = info or {}
    title = re.sub('\\s+', ' ', str(info.get('title') or get_chat_display_name(cid) or '').strip().casefold())
    typ = str(info.get('type') or '')
    return f't:{typ}:{title}' if title else f'id:{cid}'

def normalize_known_chats_for_owner() -> int:
    """
    Убирает только безопасные дубли карточек чатов у владельца:
    • одинаковый chat_id невозможен в dict, но битые ключи чистим;
    • одинаковый username считаем дублем;
    • одинаковые названия НЕ удаляем, а складываем в suspected_duplicate_titles.
    """
    if not OWNER_ID:
        return 0
    try:
        owner_store = get_chat_store(int(OWNER_ID))
        known = owner_store.setdefault('known_chats', {})
        if not isinstance(known, dict):
            owner_store['known_chats'] = {}
            return 0
        keep = {}
        removed = 0
        rows = []
        for cid_s, info in known.items():
            try:
                cid = int(cid_s)
            except Exception:
                removed += 1
                continue
            rows.append((cid, info if isinstance(info, dict) else {}, str(cid_s) in (data.get('chats', {}) or {})))
        rows.sort(key=lambda x: (not x[2], str(x[0])))
        seen_identity = set()
        title_map = defaultdict(list)
        for cid, info, exists in rows:
            key = _chat_identity_key(cid, info)
            if key in seen_identity:
                removed += 1
                continue
            seen_identity.add(key)
            keep[str(cid)] = info
            title_map[_chat_title_suspect_key(cid, info)].append(str(cid))
        suspects = {k: v for k, v in title_map.items() if len(v) > 1 and k and (not k.startswith('id:'))}
        if keep != known or owner_store.get('suspected_duplicate_titles') != suspects:
            owner_store['known_chats'] = keep
            owner_store['suspected_duplicate_titles'] = suspects
            save_data(data)
        return removed
    except Exception as e:
        log_error(f'normalize_known_chats_for_owner: {e}')
        return 0

def _v177_legacy_0088_collect_forward_menu_chats() -> dict:
    """
    Собирает список чатов для меню пересылки:
    1) из known_chats владельца
    2) из data["chats"] как резерв
    """
    result = {}
    if OWNER_ID:
        try:
            owner_store = get_chat_store(int(OWNER_ID))
            known = owner_store.get('known_chats', {}) or {}
            for cid, info in known.items():
                result[str(cid)] = {'title': info.get('title') or f'Чат {cid}', 'username': info.get('username'), 'type': info.get('type')}
        except Exception as e:
            log_error(f'collect_forward_menu_chats known_chats: {e}')
    try:
        for cid, store in (data.get('chats', {}) or {}).items():
            if OWNER_ID and str(cid) == str(OWNER_ID):
                continue
            info = store.get('info', {}) or {}
            prev = result.get(str(cid), {})
            result[str(cid)] = {'title': info.get('title') or prev.get('title') or f'Чат {cid}', 'username': info.get('username') or prev.get('username'), 'type': info.get('type') or prev.get('type')}
    except Exception as e:
        log_error(f'collect_forward_menu_chats data.chats: {e}')
    deduped = {}
    seen = set()
    for cid, info in sorted(result.items(), key=lambda kv: (str((kv[1] or {}).get('title') or '').lower(), str(kv[0]))):
        try:
            key = _chat_identity_key(int(cid), info if isinstance(info, dict) else {})
        except Exception:
            key = 'id:' + str(cid)
        if key in seen:
            continue
        seen.add(key)
        deduped[str(cid)] = info
    return deduped
try:
    _v177_legacy_0088_collect_forward_menu_chats.__name__ = 'collect_forward_menu_chats'
except Exception:
    pass

def _xlsx_col_name(n: int) -> str:
    """1 -> A, 27 -> AA."""
    out = ''
    n = int(n)
    while n > 0:
        n, rem = divmod(n - 1, 26)
        out = chr(65 + rem) + out
    return out or 'A'

def _xlsx_xml_escape(value) -> str:
    text = '' if value is None else str(value)
    return text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('"', '&quot;').replace("'", '&apos;')

def _xlsx_cell_xml(row_idx: int, col_idx: int, value, style: int | None=None) -> str:
    ref = f'{_xlsx_col_name(col_idx)}{row_idx}'
    s_attr = f' s="{int(style)}"' if style is not None else ''
    if isinstance(value, dict) and value.get('formula'):
        formula = _xlsx_xml_escape(str(value.get('formula') or '').lstrip('='))
        cached = value.get('value', 0)
        try:
            cached = float(cached)
            if cached.is_integer():
                cached = int(cached)
        except Exception:
            cached = 0
        return f'<c r="{ref}"{s_attr}><f>{formula}</f><v>{cached}</v></c>'
    if isinstance(value, (int, float)) and (not isinstance(value, bool)):
        return f'<c r="{ref}"{s_attr}><v>{value}</v></c>'
    return f'<c r="{ref}" t="inlineStr"{s_attr}><is><t>{_xlsx_xml_escape(value)}</t></is></c>'

def _v177_legacy_0089_write_simple_xlsx(path: str, rows: list[list], sheet_name: str='Данные') -> None:
    """Минимальный XLSX; sheet XML пишется потоково во временный файл."""
    rows = rows or [['date', 'amount', 'note']]
    workbook_xml = f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">\n<sheets><sheet name="{_xlsx_xml_escape(sheet_name)[:31]}" sheetId="1" r:id="rId1"/></sheets>\n<calcPr calcId="191029" fullCalcOnLoad="1" forceFullCalc="1"/>\n</workbook>'
    rels_xml = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">\n<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>\n</Relationships>'
    workbook_rels_xml = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">\n<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>\n<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>\n</Relationships>'
    content_types_xml = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">\n<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>\n<Default Extension="xml" ContentType="application/xml"/>\n<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>\n<Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>\n<Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>\n</Types>'
    styles_xml = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">\n<fonts count="2"><font><sz val="11"/><name val="Calibri"/></font><font><b/><sz val="11"/><name val="Calibri"/></font></fonts>\n<fills count="1"><fill><patternFill patternType="none"/></fill></fills>\n<borders count="1"><border><left/><right/><top/><bottom/><diagonal/></border></borders>\n<cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>\n<cellXfs count="2"><xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/><xf numFmtId="0" fontId="1" fillId="0" borderId="0" xfId="0" applyFont="1"/></cellXfs>\n<cellStyles count="1"><cellStyle name="Normal" xfId="0" builtinId="0"/></cellStyles>\n</styleSheet>'
    sheet_tmp = None
    try:
        fd, sheet_tmp = tempfile.mkstemp(prefix='xlsx_sheet_', suffix='.xml', dir=MEGA_LOCAL_TMP_DIR if os.path.isdir(MEGA_LOCAL_TMP_DIR) else None)
        os.close(fd)
        with open(sheet_tmp, 'w', encoding='utf-8', newline='') as sheet:
            sheet.write('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n')
            sheet.write('<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">\n')
            sheet.write('<sheetViews><sheetView workbookViewId="0"><pane ySplit="1" topLeftCell="A2" activePane="bottomLeft" state="frozen"/></sheetView></sheetViews>\n')
            sheet.write('<cols><col min="1" max="1" width="13" customWidth="1"/><col min="2" max="2" width="42" customWidth="1"/><col min="3" max="3" width="14" customWidth="1"/><col min="4" max="4" width="14" customWidth="1"/><col min="5" max="10" width="18" customWidth="1"/></cols>\n<sheetData>')
            for r_idx, row in enumerate(rows, start=1):
                sheet.write(f'<row r="{r_idx}">')
                for c_idx, value in enumerate(row, start=1):
                    sheet.write(_xlsx_cell_xml(r_idx, c_idx, value, style=1 if r_idx == 1 else None))
                sheet.write('</row>')
            sheet.write('</sheetData>\n</worksheet>')
        with zipfile.ZipFile(path, 'w', zipfile.ZIP_DEFLATED) as z:
            z.writestr('[Content_Types].xml', content_types_xml)
            z.writestr('_rels/.rels', rels_xml)
            z.writestr('xl/workbook.xml', workbook_xml)
            z.writestr('xl/_rels/workbook.xml.rels', workbook_rels_xml)
            z.write(sheet_tmp, 'xl/worksheets/sheet1.xml')
            z.writestr('xl/styles.xml', styles_xml)
    finally:
        try:
            if sheet_tmp and os.path.exists(sheet_tmp):
                os.remove(sheet_tmp)
        except Exception:
            pass
try:
    _v177_legacy_0089_write_simple_xlsx.__name__ = '_write_simple_xlsx'
except Exception:
    pass

def _xlsx_income_expense_values(amount):
    """Возвращает (приход, расход) для Excel: сумма разбита по двум колонкам."""
    try:
        v = float(amount or 0)
    except Exception:
        v = 0.0
    if v >= 0:
        income = int(v) if float(v).is_integer() else v
        return (income, '')
    expense = abs(v)
    expense = int(expense) if float(expense).is_integer() else expense
    return ('', expense)

def _xlsx_record_row(date_value, amount, note):
    income, expense = _xlsx_income_expense_values(amount)
    return [date_value, note or '', income, expense]

def _opening_balance_before_exact(store: dict, start_day: str, start_rid: int | None=0) -> float:
    """One opening-balance bridge for every legacy Excel/table caller.

    After 73_state_export_runtime is loaded this resolves the canonical ARS/USD
    projection; before that it keeps the old lossless bootstrap behaviour.
    """
    cid_resolver = globals().get('_excel_chat_id_for_store')
    canonical = globals().get('_excel_canonical_opening_balance')
    if callable(cid_resolver) and callable(canonical):
        try:
            cid = cid_resolver(store)
            if cid is not None:
                try:
                    currency = 'usd' if financial_view_is_usd(store) else 'ars'
                except Exception:
                    currency = 'ars'
                return float(canonical(int(cid), currency, str(start_day or '')[:10], int(start_rid or 0), bool(start_rid)))
        except Exception:
            pass
    start_day = str(start_day or '')[:10]
    try:
        start_rid = int(start_rid or 0)
    except Exception:
        start_rid = 0
    total = 0.0
    records = sorted((store or {}).get('records', []) or [], key=record_sort_key)
    for rec in records:
        if not financial_view_record_visible(store, rec):
            continue
        day_key = _record_day_key(rec)
        if day_key < start_day:
            total += financial_view_amount(store, rec)
            continue
        if day_key > start_day:
            break
        if not start_rid:
            break
        if _record_int_id(rec) == start_rid:
            break
        total += financial_view_amount(store, rec)
    return float(total)

def _v177_legacy_0090_xlsx_simple_rows_with_balances(rows: list[list], opening_balance: float, target_chat_id: int | None=None) -> list[list]:
    """Add opening balance, period totals and real closing cash balance to 4-column XLSX."""
    src = [list(r or []) for r in rows or []]
    if not src:
        src = [['Дата', 'Описание', 'Приход', 'Расход']]
    header = src[0]
    body = src[1:]
    opening = float(opening_balance or 0.0)
    income_total = 0.0
    expense_total = 0.0
    for row in body:
        try:
            val = row[2] if len(row) > 2 else ''
            if _excel_nonempty(val) and (not isinstance(val, dict)):
                income_total += float(val)
        except Exception:
            pass
        try:
            val = row[3] if len(row) > 3 else ''
            if _excel_nonempty(val) and (not isinstance(val, dict)):
                expense_total += float(val)
        except Exception:
            pass
    out = [header, ['', 'Остаток с прошлого раза', opening, ''], []]
    data_start_row = 4
    out.extend(body)
    data_end_row = max(data_start_row, len(out))
    out.append([])
    income_row = len(out) + 1
    out.append(['', 'Приход за период', {'formula': f'SUM(C{data_start_row}:C{data_end_row})', 'value': income_total}, ''])
    expense_row = len(out) + 1
    out.append(['', 'Расход за период', '', {'formula': f'SUM(D{data_start_row}:D{data_end_row})', 'value': expense_total}])
    closing = opening + income_total - expense_total
    out.append(['', 'Остаток на руках', {'formula': f'C2+C{income_row}-D{expense_row}', 'value': closing}, ''])
    return out
try:
    _v177_legacy_0090_xlsx_simple_rows_with_balances.__name__ = '_xlsx_simple_rows_with_balances'
except Exception:
    pass

def _v177_legacy_0093_compact_simple_excel_rows_and_annotations(raw_rows: list[tuple], opening_balance: float, target_chat_id: int | None=None) -> tuple[list[list], dict[tuple[int, int], str]]:
    """3-column Excel: Date / Income / Expense; description lives only in Comment/Note."""
    opening = float(opening_balance or 0.0)
    rows = [['Дата', 'Приход', 'Расход'], ['Остаток с прошлого раза', opening, ''], []]
    annotations: dict[tuple[int, int], str] = {}
    income_total = 0.0
    expense_total = 0.0
    prev_day = None
    for date_value, amount_value, note_value in raw_rows or []:
        if prev_day is not None and str(date_value) != str(prev_day):
            rows.append([])
        prev_day = date_value
        try:
            amount = parse_csv_amount(amount_value)
        except Exception:
            try:
                amount = float(amount_value or 0)
            except Exception:
                amount = 0.0
        income, expense = _xlsx_income_expense_values(amount)
        rows.append([date_value, income, expense])
        row_idx = len(rows)
        note = str(note_value or '').strip()
        if note:
            annotations[row_idx, 2 if _excel_nonempty(income) else 3] = note
        if amount >= 0:
            income_total += amount
        else:
            expense_total += abs(amount)
    data_start_row = 4
    data_end_row = max(data_start_row, len(rows))
    rows.append([])
    income_row = len(rows) + 1
    rows.append(['Приход за период', {'formula': f'SUM(B{data_start_row}:B{data_end_row})', 'value': income_total}, ''])
    expense_row = len(rows) + 1
    rows.append(['Расход за период', '', {'formula': f'SUM(C{data_start_row}:C{data_end_row})', 'value': expense_total}])
    closing = opening + income_total - expense_total
    rows.append(['Остаток на руках', {'formula': f'B2+B{income_row}-C{expense_row}', 'value': closing}, ''])
    return (rows, annotations)
try:
    _v177_legacy_0093_compact_simple_excel_rows_and_annotations.__name__ = '_compact_simple_excel_rows_and_annotations'
except Exception:
    pass

def _v177_legacy_0097_period_export_bounds(store: dict, mode: str, day_key: str) -> tuple[str, str]:
    mode = str(mode or 'all').replace('csv_', '').replace('xlsx_', '')
    if mode == 'all_real':
        mode = 'all'
    base = datetime.strptime(str(day_key)[:10], '%Y-%m-%d')
    if mode == 'day':
        return (day_key, day_key)
    if mode == 'week':
        return ((base - timedelta(days=6)).strftime('%Y-%m-%d'), day_key)
    if mode == 'month':
        return (base.replace(day=1).strftime('%Y-%m-%d'), day_key)
    if mode == 'wedthu':
        start = base
        while start.weekday() != 2:
            start -= timedelta(days=1)
        return (start.strftime('%Y-%m-%d'), (start + timedelta(days=1)).strftime('%Y-%m-%d'))
    keys = sorted(((store or {}).get('daily_records', {}) or {}).keys())
    if keys:
        return (keys[0], keys[-1])
    return (day_key, day_key)
try:
    _v177_legacy_0097_period_export_bounds.__name__ = '_period_export_bounds'
except Exception:
    pass
TABL_LSX_CATEGORIES = ['Продукты', 'Хоз общ', 'Авто и (бус)', 'прочие', 'орг. техника', 'Еда доп и ШБ', 'Связь', 'переводы', 'Проживание', 'Хоз за ашр', 'аптечка']

def _tabl_lsx_category(note: str) -> str:
    text = str(note or '').casefold()
    checks = [('Еда доп и ШБ', ('шб', 'шамп', 'мыло', 'зуб', 'паста', 'гигиен')), ('Продукты', ('продукт', 'еда', 'хлеб', 'мол', 'фрукт', 'овощ', 'банан', 'лук', 'масло', 'йогурт', 'кофе', 'чай', 'курица', 'мясо')), ('Хоз общ', ('хоз', 'салф', 'порош', 'клей', 'краск', 'саморез', 'инструмент', 'батарей', 'розет', 'шнур', 'пульт', 'ключ')), ('Авто и (бус)', ('авто', 'бенз', 'соляр', 'заправ', 'машин', 'шина', 'масло авто', 'пикап', 'бус')), ('орг. техника', ('орг', 'двд', 'dvd', 'переходник', 'блок питание', 'провод', 'кабель', 'монитор', 'паяль', 'заряд', 'науш', 'мыш', 'принтер')), ('Связь', ('тел', 'связ', 'пополнение', 'сим', 'интернет')), ('переводы', ('перевод', 'вестерн', 'western', 'банковский', 'mercado', 'меркадо')), ('Проживание', ('прож', 'аренд', 'квар', 'отель', 'дом')), ('Хоз за ашр', ('ашр', 'ашрам')), ('аптечка', ('аптеч', 'аптек', 'лекар', 'ибуп', 'витамин', 'стоматолог'))]
    for name, words in checks:
        if any((w in text for w in words)):
            return name
    return 'прочие'

def _tabl_lsx_weeks(reference_day: str | None=None, count: int=4) -> list[tuple[str, str]]:
    ref = reference_day or today_key()
    start_key = week_start_thursday(ref)
    start = datetime.strptime(start_key, '%Y-%m-%d').date()
    weeks = []
    first = start - timedelta(days=7 * (int(count) - 1))
    for i in range(int(count)):
        s = first + timedelta(days=7 * i)
        e = s + timedelta(days=6)
        weeks.append((s.strftime('%Y-%m-%d'), e.strftime('%Y-%m-%d')))
    return weeks

def _tabl_lsx_opening_balance(store: dict, start_key: str, chat_id: int | None=None) -> float:
    helper = globals().get('_excel_canonical_opening_balance')
    if callable(helper) and chat_id is not None:
        return float(helper(int(chat_id), 'ars', str(start_key)[:10], 0, False))
    total = 0.0
    for r in store.get('records', []) or []:
        try:
            if _record_day_key(r) < start_key:
                total += float(r.get('amount', 0) or 0)
        except Exception:
            pass
    return float(total)

def _xlsx_cell_xml2(row_idx: int, col_idx: int, value, style: int=0) -> str:
    if value is None:
        value = ''
    ref = f'{_xlsx_col_name(col_idx)}{row_idx}'
    s_attr = f' s="{int(style)}"' if int(style or 0) else ''
    if isinstance(value, dict) and value.get('formula'):
        formula = _xlsx_xml_escape(str(value.get('formula') or '').lstrip('='))
        cached = value.get('value', 0)
        try:
            cached = float(cached)
            cached = int(cached) if cached.is_integer() else cached
        except Exception:
            cached = 0
        return f'<c r="{ref}"{s_attr}><f>{formula}</f><v>{cached}</v></c>'
    if isinstance(value, (int, float)) and (not isinstance(value, bool)):
        return f'<c r="{ref}"{s_attr}><v>{float(value):.2f}</v></c>'
    text = str(value)
    return f'<c r="{ref}" t="inlineStr"{s_attr}><is><t>{_xlsx_xml_escape(text)}</t></is></c>'

def _v177_legacy_0098_write_tabl_lsx_xlsx(path: str, rows: list[list], styles: list[list], sheet_name: str='4 недели', comments: dict | None=None, freeze_rows: int=3, widths: list[float] | None=None, annotation_mode: str | None='notes') -> None:
    """Minimal XLSX writer with two genuinely different annotation types.

    annotation_mode="notes"    -> classic Excel Notes (legacy comments XML + VML ObjectType=Note)
    annotation_mode="comments" -> modern threaded Excel Comments (threadedComments + person)
    annotation_mode=None        -> no annotations
    """
    comments = comments or {}
    annotation_mode = str(annotation_mode or '').strip().lower() or None
    if annotation_mode not in {None, 'notes', 'comments'}:
        annotation_mode = 'notes'
    if not comments:
        annotation_mode = None
    max_cols = max((len(r) for r in rows), default=1)
    widths = list(widths or [13, 16, 28] + [20] * max(0, max_cols - 3))
    if len(widths) < max_cols:
        widths.extend([18] * (max_cols - len(widths)))
    freeze_rows = max(0, int(freeze_rows or 0))
    cols_xml = ''.join((f'<col min="{i}" max="{i}" width="{min(widths[i - 1] if i - 1 < len(widths) else 18, 34)}" customWidth="1"/>' for i in range(1, max_cols + 1)))
    legacy_drawing = '<legacyDrawing r:id="rId2"/>' if annotation_mode == 'notes' else ''
    workbook_xml = f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">\n<sheets><sheet name="{_xlsx_xml_escape(sheet_name)[:31]}" sheetId="1" r:id="rId1"/></sheets>\n<calcPr calcId="191029" fullCalcOnLoad="1" forceFullCalc="1"/>\n</workbook>'
    rels_xml = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">\n<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>\n</Relationships>'
    person_rel = ''
    if annotation_mode == 'comments':
        person_rel = '\n<Relationship Id="rId3" Type="http://schemas.microsoft.com/office/2017/10/relationships/person" Target="persons/person.xml"/>'
    workbook_rels_xml = f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">\n<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>\n<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>{person_rel}\n</Relationships>'
    category_colors = ['FFC6EFCE', 'FFDDEBF7', 'FFFCE4D6', 'FFE4DFEC', 'FFFFF2CC', 'FFD9EAD3', 'FFCFE2F3', 'FFF4CCCC', 'FFD0E0E3', 'FFEAD1DC', 'FFD9D2E9']
    extra_fills = ''.join((f'<fill><patternFill patternType="solid"><fgColor rgb="{rgb}"/></patternFill></fill>' for rgb in category_colors))
    header_xfs = ''.join((f'<xf numFmtId="0" fontId="1" fillId="{7 + i}" borderId="1" xfId="0" applyFill="1" applyFont="1"/>' for i in range(len(category_colors))))
    data_xfs = ''.join((f'<xf numFmtId="0" fontId="0" fillId="{7 + i}" borderId="1" xfId="0" applyFill="1"/>' for i in range(len(category_colors))))
    styles_xml = f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">\n<fonts count="3"><font><sz val="10"/><name val="Calibri"/></font><font><b/><sz val="10"/><name val="Calibri"/></font><font><b/><sz val="14"/><name val="Calibri"/></font></fonts>\n<fills count="18"><fill><patternFill patternType="none"/></fill><fill><patternFill patternType="gray125"/></fill><fill><patternFill patternType="solid"><fgColor rgb="FF00E000"/></patternFill></fill><fill><patternFill patternType="solid"><fgColor rgb="FFFFC000"/></patternFill></fill><fill><patternFill patternType="solid"><fgColor rgb="FFFF9999"/></patternFill></fill><fill><patternFill patternType="solid"><fgColor rgb="FFE2F0D9"/></patternFill></fill><fill><patternFill patternType="solid"><fgColor rgb="FFD9EAD3"/></patternFill></fill>{extra_fills}</fills>\n<borders count="2"><border><left/><right/><top/><bottom/><diagonal/></border><border><left style="thin"/><right style="thin"/><top style="thin"/><bottom style="thin"/><diagonal/></border></borders>\n<cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>\n<cellXfs count="30"><xf numFmtId="0" fontId="0" fillId="0" borderId="1" xfId="0"/><xf numFmtId="0" fontId="2" fillId="0" borderId="0" xfId="0"/><xf numFmtId="0" fontId="1" fillId="2" borderId="1" xfId="0" applyFill="1" applyFont="1"/><xf numFmtId="0" fontId="1" fillId="3" borderId="1" xfId="0" applyFill="1" applyFont="1"/><xf numFmtId="0" fontId="0" fillId="0" borderId="1" xfId="0"/><xf numFmtId="0" fontId="1" fillId="4" borderId="1" xfId="0" applyFill="1" applyFont="1"/><xf numFmtId="0" fontId="1" fillId="5" borderId="1" xfId="0" applyFill="1" applyFont="1"/><xf numFmtId="0" fontId="1" fillId="6" borderId="1" xfId="0" applyFill="1" applyFont="1"/>{header_xfs}{data_xfs}</cellXfs>\n<cellStyles count="1"><cellStyle name="Normal" xfId="0" builtinId="0"/></cellStyles>\n</styleSheet>'
    content_types_extra = ''
    sheet_rels_xml = None
    notes_xml = None
    vml_xml = None
    threaded_xml = None
    persons_xml = None
    if annotation_mode == 'notes':
        content_types_extra = '<Default Extension="vml" ContentType="application/vnd.openxmlformats-officedocument.vmlDrawing"/>\n<Override PartName="/xl/comments1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.comments+xml"/>'
        comment_nodes = []
        shapes = []
        for idx, ((row_idx, col_idx), text) in enumerate(sorted(comments.items()), start=1):
            ref = f'{_xlsx_col_name(int(col_idx))}{int(row_idx)}'
            safe_text = _xlsx_xml_escape(str(text or ''))
            comment_nodes.append(f'<comment ref="{ref}" authorId="0"><text><t xml:space="preserve">{safe_text}</t></text></comment>')
            shapes.append(f'<v:shape id="_x0000_s{1024 + idx}" type="#_x0000_t202" style="position:absolute;margin-left:59.25pt;margin-top:1.5pt;width:144pt;height:79.5pt;z-index:{idx};visibility:hidden" fillcolor="#ffffe1" o:insetmode="auto">\n<v:fill color2="#ffffe1"/><v:shadow on="t" color="black" obscured="t"/><v:path o:connecttype="none"/><v:textbox style="mso-direction-alt:auto"><div style="text-align:left"/></v:textbox>\n<x:ClientData ObjectType="Note"><x:MoveWithCells/><x:SizeWithCells/><x:Anchor>{max(0, int(col_idx) - 1)}, 15, {max(0, int(row_idx) - 1)}, 2, {int(col_idx) + 2}, 15, {int(row_idx) + 4}, 4</x:Anchor><x:AutoFill>False</x:AutoFill><x:Row>{max(0, int(row_idx) - 1)}</x:Row><x:Column>{max(0, int(col_idx) - 1)}</x:Column></x:ClientData></v:shape>')
        notes_xml = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n<comments xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><authors><author></author></authors><commentList>{''.join(comment_nodes)}</commentList></comments>"""
        vml_xml = f"""<?xml version="1.0" encoding="UTF-8"?>\n<xml xmlns:v="urn:schemas-microsoft-com:vml" xmlns:o="urn:schemas-microsoft-com:office:office" xmlns:x="urn:schemas-microsoft-com:office:excel">\n<o:shapelayout v:ext="edit"><o:idmap v:ext="edit" data="1"/></o:shapelayout><v:shapetype id="_x0000_t202" coordsize="21600,21600" o:spt="202" path="m,l,21600r21600,l21600,xe"><v:stroke joinstyle="miter"/><v:path gradientshapeok="t" o:connecttype="rect"/></v:shapetype>{''.join(shapes)}</xml>"""
        sheet_rels_xml = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">\n<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/comments" Target="../comments1.xml"/>\n<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/vmlDrawing" Target="../drawings/vmlDrawing1.vml"/>\n</Relationships>'
    elif annotation_mode == 'comments':
        content_types_extra = '<Override PartName="/xl/threadedComments/threadedComment1.xml" ContentType="application/vnd.ms-excel.threadedcomments+xml"/>\n<Override PartName="/xl/persons/person.xml" ContentType="application/vnd.ms-excel.person+xml"/>'
        person_id = '{7C441D5B-9D3A-4B84-95C4-5BCE02D746A1}'
        comment_nodes = []
        comment_time = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')
        for row_idx, col_idx in sorted(comments.keys()):
            ref = f'{_xlsx_col_name(int(col_idx))}{int(row_idx)}'
            safe_text = _xlsx_xml_escape(str(comments[row_idx, col_idx] or ''))
            comment_nodes.append(f'<threadedComment ref="{ref}" dT="{comment_time}" personId="{person_id}"><text>{safe_text}</text></threadedComment>')
        threaded_xml = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n<ThreadedComments xmlns="http://schemas.microsoft.com/office/spreadsheetml/2018/threadedcomments">{''.join(comment_nodes)}</ThreadedComments>"""
        persons_xml = f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n<personList xmlns="http://schemas.microsoft.com/office/spreadsheetml/2018/person"><person displayName="Telegram Finance Bot" id="{person_id}" userId="telegram-finance-bot" providerId="None"/></personList>'
        sheet_rels_xml = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">\n<Relationship Id="rId1" Type="http://schemas.microsoft.com/office/2017/10/relationships/threadedComment" Target="../threadedComments/threadedComment1.xml"/>\n</Relationships>'
    content_types_xml = f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">\n<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>\n<Default Extension="xml" ContentType="application/xml"/>{content_types_extra}\n<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>\n<Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>\n<Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>\n</Types>'
    sheet_tmp = None
    try:
        temp_dir = MEGA_LOCAL_TMP_DIR if os.path.isdir(MEGA_LOCAL_TMP_DIR) else None
        fd, sheet_tmp = tempfile.mkstemp(prefix='xlsx_sheet_', suffix='.xml', dir=temp_dir)
        os.close(fd)
        with open(sheet_tmp, 'w', encoding='utf-8', newline='') as sheet:
            sheet.write('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n')
            sheet.write('<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">\n')
            pane = f'<pane ySplit="{freeze_rows}" topLeftCell="A{freeze_rows + 1}" activePane="bottomLeft" state="frozen"/>' if freeze_rows else ''
            sheet.write(f'<sheetViews><sheetView workbookViewId="0">{pane}</sheetView></sheetViews>\n')
            sheet.write(f'<cols>{cols_xml}</cols>\n<sheetData>')
            for r_idx, row in enumerate(rows, start=1):
                st_row = styles[r_idx - 1] if r_idx - 1 < len(styles) else []
                height = ' ht="22" customHeight="1"' if r_idx <= max(1, freeze_rows) else ''
                sheet.write(f'<row r="{r_idx}"{height}>')
                for c_idx in range(1, max_cols + 1):
                    value = row[c_idx - 1] if c_idx - 1 < len(row) else ''
                    style = st_row[c_idx - 1] if c_idx - 1 < len(st_row) else 0
                    sheet.write(_xlsx_cell_xml2(r_idx, c_idx, value, style=style))
                sheet.write('</row>')
            sheet.write(f'</sheetData>{legacy_drawing}\n</worksheet>')
        with zipfile.ZipFile(path, 'w', zipfile.ZIP_DEFLATED) as z:
            z.writestr('[Content_Types].xml', content_types_xml)
            z.writestr('_rels/.rels', rels_xml)
            z.writestr('xl/workbook.xml', workbook_xml)
            z.writestr('xl/_rels/workbook.xml.rels', workbook_rels_xml)
            z.write(sheet_tmp, 'xl/worksheets/sheet1.xml')
            z.writestr('xl/styles.xml', styles_xml)
            if sheet_rels_xml:
                z.writestr('xl/worksheets/_rels/sheet1.xml.rels', sheet_rels_xml)
            if annotation_mode == 'notes':
                z.writestr('xl/comments1.xml', notes_xml)
                z.writestr('xl/drawings/vmlDrawing1.vml', vml_xml)
            elif annotation_mode == 'comments':
                z.writestr('xl/threadedComments/threadedComment1.xml', threaded_xml)
                z.writestr('xl/persons/person.xml', persons_xml)
    finally:
        try:
            if sheet_tmp and os.path.exists(sheet_tmp):
                os.remove(sheet_tmp)
        except Exception:
            pass
try:
    _v177_legacy_0098_write_tabl_lsx_xlsx.__name__ = '_write_tabl_lsx_xlsx'
except Exception:
    pass

def _validate_xlsx_annotation_package(path: str, annotation_mode: str | None) -> None:
    """Fail closed if Notes and Comments OOXML parts ever get mixed.

    Excel Notes are the legacy comments1.xml + VML note shapes. Modern Excel
    Comments are threadedComments + persons. In notes mode the threaded parts
    must be completely absent.
    """
    mode = str(annotation_mode or '').strip().lower() or None
    if mode not in {None, 'notes', 'comments'}:
        return
    with zipfile.ZipFile(path, 'r') as z:
        names = set(z.namelist())
        legacy_xml = z.read('xl/comments1.xml').decode('utf-8', 'replace') if 'xl/comments1.xml' in names else ''
        vml_text = z.read('xl/drawings/vmlDrawing1.vml').decode('utf-8', 'replace') if 'xl/drawings/vmlDrawing1.vml' in names else ''
    has_legacy_notes = 'xl/comments1.xml' in names and 'xl/drawings/vmlDrawing1.vml' in names
    has_threaded_comments = 'xl/threadedComments/threadedComment1.xml' in names or 'xl/persons/person.xml' in names
    if mode == 'notes':
        if has_threaded_comments:
            raise RuntimeError('XLSX notes mode contains threaded Comments parts')
        if has_legacy_notes:
            if 'ObjectType="Note"' not in vml_text:
                raise RuntimeError('XLSX notes VML does not declare ObjectType=Note')
            if 'Telegram Finance Bot' in legacy_xml:
                raise RuntimeError('XLSX notes mode must not carry a comment author')
            if '<comment ' in legacy_xml and (not re.search('<comment\\b[^>]*>.*?<t(?:\\s[^>]*)?>(?!\\s*</t>).*?</t>', legacy_xml, flags=re.S)):
                raise RuntimeError('XLSX notes mode contains empty note bodies')
    if mode == 'comments' and has_legacy_notes:
        raise RuntimeError('XLSX comments mode contains legacy Notes parts')

def _excel_nonempty(value) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    return True

def _excel_category_color_index(note: str) -> int:
    try:
        category = _tabl_lsx_category(note)
        return TABL_LSX_CATEGORIES.index(category) if category in TABL_LSX_CATEGORIES else TABL_LSX_CATEGORIES.index('прочие')
    except Exception:
        return 0

def _v177_legacy_0099_modern_simple_excel_styles_comments(rows: list[list]) -> tuple[list[list], dict, int, list[float]]:
    """Modern 4-column/backup Excel: colored amounts + annotations on expenses."""
    max_cols = max((len(r) for r in rows), default=4)
    styles = []
    comments = {}
    header_row = 1
    data_started = False
    for r_idx, row in enumerate(rows, start=1):
        row = list(row or [])
        normalized0 = str(row[0] if row else '').strip().casefold()
        normalized1 = str(row[1] if len(row) > 1 else '').strip().casefold()
        is_header = normalized0 in {'дата', 'date'} and normalized1 in {'описание', 'description', 'amount'}
        if is_header:
            header_row = r_idx
            data_started = True
            styles.append([2] * max_cols)
            continue
        st = [4] * max_cols if any((_excel_nonempty(v) for v in row)) else [0] * max_cols
        if not data_started:
            if r_idx == 1 and any((_excel_nonempty(v) for v in row)):
                st = [1] + [4] * max(0, max_cols - 1)
            styles.append(st)
            continue
        note = str(row[1] if len(row) > 1 else '').strip()
        note_key = note.casefold()
        if note_key in {'остаток с прошлого раза', 'остаток на руках'}:
            styles.append([6] * max_cols)
            continue
        if note_key in {'приход за период', 'расход за период'}:
            styles.append([5] * max_cols)
            continue
        income = row[2] if len(row) > 2 else ''
        expense = row[3] if len(row) > 3 else ''
        if _excel_nonempty(income) and len(st) > 2:
            st[2] = 7
        if _excel_nonempty(expense) and len(st) > 3:
            cat_idx = _excel_category_color_index(note)
            st[3] = 19 + cat_idx
            if note:
                comments[r_idx, 4] = note
        styles.append(st)
    widths = [13, 38, 15, 15] + [14] * max(0, max_cols - 4)
    return (styles, comments, header_row, widths)
try:
    _v177_legacy_0099_modern_simple_excel_styles_comments.__name__ = '_modern_simple_excel_styles_comments'
except Exception:
    pass

def _v177_legacy_0100_modern_compact_excel_styles_comments(rows: list[list], annotations: dict[tuple[int, int], str]) -> tuple[list[list], dict, int, list[float]]:
    """Modern 3-column Excel without Description column; annotations are on amount cells."""
    max_cols = max((len(r) for r in rows), default=3)
    styles = []
    for r_idx, row in enumerate(rows or [], start=1):
        row = list(row or [])
        first = str(row[0] if row else '').strip().casefold()
        is_header = first in {'дата', 'date'}
        if is_header:
            styles.append([2] * max_cols)
            continue
        if not any((_excel_nonempty(v) for v in row)):
            styles.append([0] * max_cols)
            continue
        if first in {'остаток с прошлого раза', 'остаток на руках'}:
            styles.append([6] * max_cols)
            continue
        if first in {'приход за период', 'расход за период'}:
            styles.append([5] * max_cols)
            continue
        st = [4] * max_cols
        if len(row) > 1 and _excel_nonempty(row[1]):
            st[1] = 7
        if len(row) > 2 and _excel_nonempty(row[2]):
            note = str((annotations or {}).get((r_idx, 3)) or '')
            st[2] = 19 + _excel_category_color_index(note)
        styles.append(st)
    return (styles, dict(annotations or {}), 1, [22, 16, 16])
try:
    _v177_legacy_0100_modern_compact_excel_styles_comments.__name__ = '_modern_compact_excel_styles_comments'
except Exception:
    pass

def _v177_legacy_0101_modern_category_excel_styles_comments(rows: list[list]) -> tuple[list[list], dict, int, list[float]]:
    """Modern category/stat Excel: each expense column gets its own fill and annotation."""
    max_cols = max((len(r) for r in rows), default=4)
    styles = []
    comments = {}
    header_row = 1
    header_found = False
    for r_idx, row in enumerate(rows, start=1):
        row = list(row or [])
        first = str(row[0] if row else '').strip().casefold()
        second = str(row[1] if len(row) > 1 else '').strip().casefold()
        is_header = first in {'дата', 'date'} and second in {'описание', 'description', 'приход/выдача'}
        if is_header:
            header_row = r_idx
            header_found = True
            st = [2] * min(3, max_cols) + [8 + (c - 3) % len(TABL_LSX_CATEGORIES) for c in range(3, max_cols)]
            styles.append(st)
            continue
        if not any((_excel_nonempty(v) for v in row)):
            styles.append([0] * max_cols)
            continue
        label = second
        if label in {'сумма по статьям', 'расход'}:
            styles.append([5] * max_cols)
            continue
        if label in {'приход', 'остаток с прошлого раза', 'остаток на руках', 'на руках:'}:
            styles.append([6] * max_cols)
            continue
        st = [4] * max_cols
        note = str(row[1] if len(row) > 1 else '').strip()
        if header_found:
            if len(row) > 2 and _excel_nonempty(row[2]):
                st[2] = 7
            for c in range(3, max_cols):
                if c < len(row) and _excel_nonempty(row[c]):
                    st[c] = 19 + (c - 3) % len(TABL_LSX_CATEGORIES)
                    if note:
                        comments[r_idx, c + 1] = note
        styles.append(st)
    widths = [13, 36, 15] + [18] * max(0, max_cols - 3)
    return (styles, comments, header_row, widths)
try:
    _v177_legacy_0101_modern_category_excel_styles_comments.__name__ = '_modern_category_excel_styles_comments'
except Exception:
    pass

def _v177_legacy_0103_modern_category_no_description_styles_comments(rows: list[list], annotations: dict[tuple[int, int], str]) -> tuple[list[list], dict, int, list[float]]:
    """Category report without Description column: Date / Income / article columns."""
    max_cols = max((len(r) for r in rows), default=3)
    styles = []
    for r_idx, row in enumerate(rows or [], start=1):
        row = list(row or [])
        first = str(row[0] if row else '').strip().casefold()
        is_header = first in {'дата', 'date'}
        if is_header:
            styles.append([2] * min(2, max_cols) + [8 + (c - 2) % len(TABL_LSX_CATEGORIES) for c in range(2, max_cols)])
            continue
        if not any((_excel_nonempty(v) for v in row)):
            styles.append([3] * max_cols)
            continue
        if first in {'сумма по статьям', 'расход', 'приход', 'остаток с прошлого раза', 'остаток на руках', 'на руках:'}:
            styles.append([5 if first in {'сумма по статьям', 'расход'} else 6] * max_cols)
            continue
        st = [4] * max_cols
        if len(row) > 1 and _excel_nonempty(row[1]):
            st[1] = 7
        for c in range(2, max_cols):
            if c < len(row) and _excel_nonempty(row[c]):
                st[c] = 19 + (c - 2) % len(TABL_LSX_CATEGORIES)
        styles.append(st)
    return (styles, dict(annotations or {}), 1, [22, 15] + [18] * max(0, max_cols - 2))
try:
    _v177_legacy_0103_modern_category_no_description_styles_comments.__name__ = '_modern_category_no_description_styles_comments'
except Exception:
    pass

def _v177_legacy_0104_category_excel_expected_annotations(rows: list[list]) -> dict[tuple[int, int], str]:
    """Return the exact expense cells that must carry an annotation in category Excel.

    This mirrors _modern_category_excel_styles_comments(). Summary / balance rows
    intentionally do not receive expense notes, even if they contain category totals.
    """
    expected: dict[tuple[int, int], str] = {}
    header_found = False
    skip_labels = {'сумма по статьям', 'расход', 'приход', 'остаток с прошлого раза', 'остаток на руках', 'на руках:'}
    for r_idx, row in enumerate(rows or [], start=1):
        row = list(row or [])
        first = str(row[0] if row else '').strip().casefold()
        second = str(row[1] if len(row) > 1 else '').strip().casefold()
        is_header = first in {'дата', 'date'} and second in {'описание', 'description', 'приход/выдача'}
        if is_header:
            header_found = True
            continue
        if not header_found or not any((_excel_nonempty(v) for v in row)):
            continue
        if second in skip_labels:
            continue
        note_text = str(row[1] if len(row) > 1 else '').strip()
        if not note_text:
            continue
        for c in range(3, len(row)):
            if _excel_nonempty(row[c]):
                expected[r_idx, c + 1] = note_text
    return expected
try:
    _v177_legacy_0104_category_excel_expected_annotations.__name__ = '_category_excel_expected_annotations'
except Exception:
    pass

def _validate_xlsx_expected_notes(path: str, expected: dict[tuple[int, int], str]) -> None:
    """Verify that every intended Excel Note cell contains the exact description text.

    This checks the generated XLSX package itself, not only the in-memory mapping.
    """
    if not expected:
        return
    import xml.etree.ElementTree as ET
    with zipfile.ZipFile(path, 'r') as z:
        names = set(z.namelist())
        if 'xl/comments1.xml' not in names:
            raise RuntimeError('Excel статьи: файл не содержит xl/comments1.xml для Примечаний')
        raw = z.read('xl/comments1.xml')
    root = ET.fromstring(raw)
    ns = {'m': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
    actual: dict[str, str] = {}
    for node in root.findall('.//m:comment', ns):
        ref = str(node.attrib.get('ref') or '')
        text = ''.join(node.itertext()).strip()
        if ref:
            actual[ref] = text
    missing = []
    wrong = []
    for (row_idx, col_idx), text in expected.items():
        ref = f'{_xlsx_col_name(int(col_idx))}{int(row_idx)}'
        if ref not in actual:
            missing.append(ref)
        elif actual.get(ref, '') != str(text).strip():
            wrong.append(ref)
    if missing or wrong:
        raise RuntimeError(f'Excel статьи: повреждены примечания missing={missing[:8]} wrong={wrong[:8]} expected={len(expected)} actual={len(actual)}')

def _write_excel_by_selected_style(path: str, rows: list[list], chat_id: int, sheet_name: str='Данные', category_layout: bool=False, mode_override: str | None=None, compact_annotations: dict[tuple[int, int], str] | None=None) -> None:
    """XLSX writer with per-export style override: OLD / Comments / Notes."""
    mode = str(mode_override or excel_table_style(int(chat_id)) or 'old').strip().lower()
    if mode not in {'old', 'new_plain', 'new_comments', 'new_notes', 'google_notes'}:
        mode = 'old'
    local_mode = 'new_notes' if mode == 'google_notes' else mode
    # R16: ALL XLSX files are colored.  'old' now means old layout/annotation
    # behaviour only; it no longer bypasses the canonical vys-262 palette.
    if category_layout == 'category_compact':
        styles, annotations, freeze_rows, widths = _modern_category_no_description_styles_comments(rows, compact_annotations or {})
    elif category_layout:
        styles, annotations, freeze_rows, widths = _modern_category_excel_styles_comments(rows)
    elif compact_annotations is not None:
        styles, annotations, freeze_rows, widths = _modern_compact_excel_styles_comments(rows, compact_annotations)
    else:
        styles, annotations, freeze_rows, widths = _modern_simple_excel_styles_comments(rows)
    annotation_mode = None if local_mode in {'old', 'new_plain'} else 'comments' if local_mode == 'new_comments' else 'notes'
    if annotation_mode is None:
        annotations = {}
    expected_annotations: dict[tuple[int, int], str] = {}
    if annotation_mode == 'notes':
        if category_layout == 'category_compact':
            expected_annotations = {k: str(v).strip() for k, v in (compact_annotations or {}).items() if str(v or '').strip()}
        elif category_layout:
            expected_annotations = _category_excel_expected_annotations(rows)
        elif compact_annotations is not None:
            expected_annotations = {k: str(v).strip() for k, v in compact_annotations.items() if str(v or '').strip()}
        if expected_annotations:
            annotations = dict(expected_annotations)
    _write_tabl_lsx_xlsx(path, rows, styles, sheet_name=sheet_name, comments=annotations, freeze_rows=freeze_rows, widths=widths, annotation_mode=annotation_mode)
    _validate_xlsx_annotation_package(path, annotation_mode)
    if expected_annotations:
        _validate_xlsx_expected_notes(path, expected_annotations)

def create_tabl_lsx_file(chat_id: int, reference_day: str | None=None) -> str:
    chat_id = int(chat_id)
    store = get_chat_store(chat_id)
    modern_excel = excel_table_style(chat_id) != 'old'
    weeks = _tabl_lsx_weeks(reference_day or today_key(), 4)
    cols = ['Дата', 'Приход/выдача', 'Откуда/кому'] + TABL_LSX_CATEGORIES
    rows, styles = ([], [])
    comments = {}
    title = f'сегодня {fmt_date_ddmmyy(today_key())} — {get_chat_display_name(chat_id)}'
    rows.append([title])
    styles.append([1] + [0] * (len(cols) - 1))
    rows.append(['Таблица за последние 4 недели: четверг–среда'])
    styles.append([1] + [0] * (len(cols) - 1))
    rows.append([])
    styles.append([])
    daily = {}
    range_builder = globals().get('_excel_canonical_records_for_range')
    if callable(range_builder) and weeks:
        canonical_rows = range_builder(chat_id, 'ars', weeks[0][0], weeks[-1][1])
        for _rec in canonical_rows or []:
            _dk = str(globals().get('_v151_day_key', _record_day_key)(_rec))[:10]
            daily.setdefault(_dk, []).append(_rec)
    else:
        daily = store.get('daily_records', {}) or {}
    for start_key, end_key in weeks:
        rows.append(['Неделя', f'{fmt_date_ddmmyy(start_key)} — {fmt_date_ddmmyy(end_key)}'])
        styles.append([3, 3] + [3] * (len(cols) - 2))
        rows.append(cols)
        styles.append([2, 2, 2] + [8 + i for i in range(len(TABL_LSX_CATEGORIES))] if modern_excel else [2] * len(cols))
        opening = _tabl_lsx_opening_balance(store, start_key, chat_id=chat_id)
        rows.append([fmt_date_ddmmyy(start_key), int(round(opening)), 'Остаток с прошлого раза'] + [''] * len(TABL_LSX_CATEGORIES))
        styles.append([7, 7, 7] + [4] * len(TABL_LSX_CATEGORIES))
        income_total = 0.0
        expense_total = 0.0
        cat_totals = {cat: 0.0 for cat in TABL_LSX_CATEGORIES}
        week_canonical_records = []
        start_dt = datetime.strptime(start_key, '%Y-%m-%d').date()
        for offset in range(7):
            dk = (start_dt + timedelta(days=offset)).strftime('%Y-%m-%d')
            recs = sorted(daily.get(dk, []) or [], key=record_sort_key)
            if not recs:
                rows.append([fmt_date_ddmmyy(dk)] + [''] * (len(cols) - 1))
                styles.append([3] + [4] * (len(cols) - 1))
                continue
            first_for_day = True
            for rec in recs:
                week_canonical_records.append(rec)
                try:
                    amount = float(rec.get('_v151_amount', rec.get('amount', 0)) or 0)
                except Exception:
                    amount = 0.0
                note = str(rec.get('_v151_note', rec.get('note') or '') or '').strip()
                row = [fmt_date_ddmmyy(dk) if first_for_day else '', '', ''] + [''] * len(TABL_LSX_CATEGORIES)
                row_styles = [3 if row[0] else 4, 4, 4] + [4] * len(TABL_LSX_CATEGORIES)
                first_for_day = False
                if amount >= 0:
                    income_total += amount
                    row[1] = int(round(amount))
                    row[2] = note
                else:
                    value = abs(amount)
                    expense_total += value
                    cat = None
                    try:
                        resolved = resolve_expense_category_for_record(rec, store)
                        resolved_cf = str(resolved or '').strip().casefold()
                        for _cat_name in TABL_LSX_CATEGORIES:
                            if str(_cat_name).strip().casefold() == resolved_cf:
                                cat = _cat_name
                                break
                    except Exception:
                        cat = None
                    if not cat:
                        cat = _tabl_lsx_category(note)
                    cat_idx = TABL_LSX_CATEGORIES.index(cat)
                    cat_totals[cat] = cat_totals.get(cat, 0.0) + value
                    col_idx = 3 + cat_idx
                    if modern_excel:
                        row[col_idx] = int(value) if float(value).is_integer() else value
                        row_styles[col_idx] = 19 + cat_idx
                        if note:
                            comments[len(rows) + 1, col_idx + 1] = note
                    else:
                        shown = fmt_num_plain(value)
                        row[col_idx] = (shown + (' ' + note if note else '')).strip()
                rows.append(row)
                styles.append(row_styles)
        total_row = ['Итог:', int(round(income_total)), ''] + [int(round(cat_totals.get(cat, 0))) if cat_totals.get(cat, 0) else '' for cat in TABL_LSX_CATEGORIES]
        rows.append(total_row)
        styles.append([5] * len(cols))
        rows.append(['расход:', int(round(expense_total))] + [''] * (len(cols) - 2))
        styles.append([5] * len(cols))
        _v150_week_closing = float(opening + income_total - expense_total)
        rows.append(['Остаток на руках', int(round(_v150_week_closing))] + [''] * (len(cols) - 2))
        styles.append([6] * len(cols))
        _v150_week_reserve = float(_v150_export_reserve(chat_id)) if '_v150_export_reserve' in globals() else 0.0
        rows.append(['Гомонковые', int(round(_v150_week_reserve)) if float(_v150_week_reserve).is_integer() else _v150_week_reserve] + [''] * (len(cols) - 2))
        styles.append([6] * len(cols))
        _v150_week_turnover = _v150_week_closing - _v150_week_reserve
        rows.append(['Остаток в обороте', int(round(_v150_week_turnover)) if float(_v150_week_turnover).is_integer() else _v150_week_turnover] + [''] * (len(cols) - 2))
        styles.append([6] * len(cols))
        rows.append([])
        styles.append([])
        _v150_products_total = float(cat_totals.get('Продукты', 0.0) or 0.0)
        _v150_food_metric_value = 0.0
        try:
            if callable(globals().get('_v151_food_metric')):
                _v150_products_total, _v150_food_metric_value, _v194_days, _v194_rate = _v151_food_metric(int(chat_id), week_canonical_records, start_key, end_key)
            elif '_v150_food_per_person' in globals():
                _v150_food_metric_value = _v150_food_per_person(_v150_products_total)
        except Exception:
            _v150_food_metric_value = 0.0
        rows.append(['Расход еды на человека в сутки', _v150_food_metric_value] + [''] * (len(cols) - 2))
        styles.append([5] * len(cols))
        rows.append([])
        styles.append([])
    os.makedirs(MEGA_LOCAL_TMP_DIR, exist_ok=True)
    start_all, end_all = (weeks[0][0], weeks[-1][1])
    mode_tag = excel_table_style(chat_id)
    fname = f"tabl_lsx_{mode_tag}_{mega_safe_name(get_chat_display_name(chat_id), 'chat')}_{start_all}_{end_all}.xlsx"
    path = os.path.join(MEGA_LOCAL_TMP_DIR, fname)
    annotation_mode = excel_annotation_mode(chat_id)
    try:
        usd_builder = globals().get('_v151_simple_table')
        usd_enabled = globals().get('excel_usd_table_enabled')
        ctx_local = globals().get('_V151_EXPORT_LOCAL')
        if callable(usd_builder) and (not callable(usd_enabled) or bool(usd_enabled(int(chat_id)))) and (ctx_local is not None):
            prev_ctx = getattr(ctx_local, 'value', None)
            try:
                ctx_local.value = {'kind': 'exact', 'target_chat_id': int(chat_id), 'start_key': str(start_all), 'start_rid': 0, 'end_key': str(end_all), 'end_rid': 0, 'file_type': 'xlsx'}
                usd_rows, _usd_notes = usd_builder(int(chat_id), 'usd', compact=False)
            finally:
                ctx_local.value = prev_ctx
            if usd_rows:
                offset = len(rows) + 2
                rows.extend([[], []])
                styles.extend([[], []])
                shifter = globals().get('_v193_shift_formula_rows')
                shifted_usd = shifter(usd_rows, offset) if callable(shifter) else usd_rows
                if modern_excel and callable(globals().get('_modern_simple_excel_styles_comments')):
                    usd_styles, usd_comments, _freeze, _widths = _modern_simple_excel_styles_comments(shifted_usd)
                    styles.extend(usd_styles)
                    for (rr, cc), text in (usd_comments or {}).items():
                        comments[int(rr) + offset, int(cc)] = text
                else:
                    styles.extend([[4] * len(r or []) for r in shifted_usd])
                rows.extend(shifted_usd)
                validator = globals().get('_v193_validate_currency_formula_domains')
                if callable(validator):
                    validator(rows)
    except Exception as _v192_usd_exc:
        try:
            log_error(f'tabl_lsx USD append({chat_id}): {_v192_usd_exc}')
        except Exception:
            pass
    _write_tabl_lsx_xlsx(path, rows, styles, sheet_name='4 недели', comments=comments if modern_excel else None, annotation_mode=annotation_mode)
    if modern_excel:
        _validate_xlsx_annotation_package(path, annotation_mode)
    return path

def send_tabl_lsx_for_chat(recipient_chat_id: int, target_chat_id: int):
    path = None
    try:
        _file_job_progress('собираю Excel', force=True)
        path = create_tabl_lsx_file(target_chat_id, today_key())
        _file_job_progress('отправляю Excel в Telegram', force=True)
        display = os.path.basename(path)
        fobj = file_bytesio_named(path, display)
        if not fobj:
            raise RuntimeError('Excel создан, но не удалось открыть файл для отправки в Telegram')
        _tg_call_retry(bot.send_document, recipient_chat_id, fobj, caption=f'📊 Таблица LSX ({excel_table_style_caption(target_chat_id)}) за последние 4 недели Чт–Ср: {get_chat_display_name(target_chat_id)}', timeout=120, purpose='tabl_lsx_send_document')
        return True
    except Exception as e:
        log_error(f'send_tabl_lsx_for_chat({target_chat_id}): {e}')
        send_and_auto_delete(recipient_chat_id, '❌ Не удалось создать /tabl_lsx.', 15)
        return False
    finally:
        if path:
            try:
                os.remove(path)
            except Exception:
                pass

def save_chat_xlsx(chat_id: int, path: str | None=None, store: dict | None=None) -> str | None:
    """Создаёт Excel .xlsx для чата; date в формате DD:MM:YY."""
    try:
        store = store or data.get('chats', {}).get(str(chat_id)) or get_chat_store(chat_id)
        path = path or chat_xlsx_file(chat_id)
        rows = [['Дата', 'Описание', 'Приход', 'Расход']]
        daily = store.get('daily_records', {}) or {}
        for dk in sorted(daily.keys()):
            recs_sorted = sorted(daily.get(dk, []) or [], key=record_sort_key)
            for r in recs_sorted:
                rows.append(_xlsx_record_row(fmt_date_table(dk), r.get('amount', 0), r.get('note', '')))
        rows = insert_blank_rows_between_days(rows, header_rows=1)
        first_key = sorted(daily.keys())[0] if daily else today_key()
        opening = _opening_balance_before_exact(store, first_key, 0)
        rows = _xlsx_simple_rows_with_balances(rows, opening, chat_id)
        _write_excel_by_selected_style(path, rows, chat_id, sheet_name='Данные', category_layout=False)
        return path
    except Exception as e:
        log_error(f'save_chat_xlsx({get_chat_display_name(chat_id)}): {e}')
        return None

def snapshot_chat_store(chat_id: int) -> dict:
    """Стабильный снимок одного чата для файлового бэкапа."""
    with locked_chat(int(chat_id)):
        normalize_chat_records(int(chat_id))
        store = data.get('chats', {}).get(str(chat_id)) or get_chat_store(chat_id)
        return json.loads(json.dumps(store, ensure_ascii=False, default=str))

def build_chat_backup_payload(chat_id: int, store: dict | None=None) -> dict:
    """JSON для чтения: последние операции и даты находятся сверху."""
    store = store or snapshot_chat_store(chat_id)
    records_desc = sorted(store.get('records', []) or [], key=record_sort_key, reverse=True)
    daily_src = store.get('daily_records', {}) or {}
    daily_desc = {}
    daily_by_date_desc = {}
    for day_key in sorted(daily_src.keys(), reverse=True):
        day_records = sorted(daily_src.get(day_key, []) or [], key=record_sort_key, reverse=True)
        daily_desc[str(day_key)] = backup_records_list(day_records)
        daily_by_date_desc[fmt_date_backup(day_key)] = backup_records_list(day_records)
    return {'kind': 'chat_full_backup', 'version': VERSION, 'created_at': now_local().isoformat(timespec='seconds'), 'date_format': 'DD:MM:YY', 'sort_order': 'newest_first', 'chat_id': chat_id, 'chat_name': get_chat_display_name(chat_id), 'balance': store.get('balance', 0), 'records': backup_records_list(records_desc), 'daily_records': daily_desc, 'daily_records_by_date': daily_by_date_desc, 'next_id': store.get('next_id', 1), 'info': store.get('info', {}), 'known_chats': store.get('known_chats', {}), 'settings_backup': build_chat_settings_backup_payload(chat_id, store), 'chat_state': {str(k): _v184_copy(v) if '_v184_copy' in globals() else json.loads(json.dumps(v, ensure_ascii=False, default=str)) for k, v in (store or {}).items() if str(k) not in {'records', 'daily_records', 'daily_records_by_date', 'balance', 'next_id', 'info', 'known_chats', 'settings'}}, 'restore_contract': {'schema': 1, 'scope': 'chat', 'policy': 'strict_replace_from_file_no_live_merge', 'records_source': 'records', 'derived_fields': ['balance', 'daily_records', 'daily_records_by_date', 'overall_balance']}}

def save_chat_json_only(chat_id: int) -> str | None:
    """Быстрый лёгкий JSON без CSV/Excel."""
    try:
        store = snapshot_chat_store(chat_id)
        payload = build_chat_backup_payload(chat_id, store)
        path = chat_json_file(chat_id)
        _save_json(path, payload)
        return path
    except Exception as e:
        log_error(f'save_chat_json_only({get_chat_display_name(chat_id)}): {e}')
        return None

def save_chat_json(chat_id: int):
    """Полный локальный пакет чата: JSON + CSV + опциональный Excel + META."""
    try:
        store = snapshot_chat_store(chat_id)
        payload = build_chat_backup_payload(chat_id, store)
        chat_path_json = chat_json_file(chat_id)
        _save_json(chat_path_json, payload)
        chat_path_csv = chat_csv_file(chat_id)
        chat_path_xlsx = chat_xlsx_file(chat_id)
        chat_path_meta = chat_meta_file(chat_id)
        with open(chat_path_csv, 'w', newline='', encoding='utf-8') as f:
            w = csv.writer(f)
            w.writerow(['date', 'amount', 'note'])
            daily = store.get('daily_records', {}) or {}
            rows = []
            for dk in sorted(daily.keys()):
                for r in sorted(daily.get(dk, []) or [], key=record_sort_key):
                    rows.append((fmt_date_table(dk), fmt_csv_amount(r.get('amount')), r.get('note', '')))
            write_csv_rows_with_day_gaps(w, rows, 3)
        if backup_excel_all_enabled(chat_id):
            save_chat_xlsx(chat_id, chat_path_xlsx, store)
        meta = {'last_saved': now_local().isoformat(timespec='seconds'), 'date_format': 'DD.MM.YY', 'record_count': sum((len(v) for v in store.get('daily_records', {}).values())), 'excel_enabled': backup_excel_all_enabled(chat_id)}
        _save_json(chat_path_meta, meta)
        log_info(f'Per-chat files saved for chat {get_chat_display_name(chat_id)}')
        return chat_path_json
    except Exception as e:
        log_error(f'save_chat_json({get_chat_display_name(chat_id)}): {e}')
        return None

def _extract_universal_state(payload: dict) -> dict:
    """Поддерживает текущий плоский формат и будущий envelope со state/bot_state."""
    if not isinstance(payload, dict):
        return {}
    for key in ('state', 'bot_state', 'data'):
        candidate = payload.get(key)
        if isinstance(candidate, dict) and isinstance(candidate.get('chats'), dict):
            state = json.loads(json.dumps(candidate, ensure_ascii=False, default=str))
            runtime = payload.get('runtime') or payload.get('_runtime_snapshot') or {}
            if isinstance(runtime, dict):
                state.setdefault('forward_index', runtime.get('forward_index', {}))
                state.setdefault('finance_active_chats', runtime.get('finance_active_chats', {}))
                state.setdefault('backup_flags', runtime.get('backup_flags', {}))
                state.setdefault('_global_settings', runtime.get('global_settings', {}))
            return state
    return json.loads(json.dumps(payload, ensure_ascii=False, default=str))

def _migrate_full_state(restored: dict) -> dict:
    """Мягкая миграция старых JSON: неизвестные поля сохраняются, отсутствующие добавляются."""
    base = default_data()
    for key, value in base.items():
        if key not in restored:
            restored[key] = json.loads(json.dumps(value, ensure_ascii=False, default=str))
    restored.setdefault('chats', {})
    restored.setdefault('forward_rules', {})
    restored.setdefault('forward_finance', {})
    restored.setdefault('forward_index', {})
    default_globals = default_data().get('_global_settings', {})
    globals_state = restored.setdefault('_global_settings', {})
    if not isinstance(globals_state, dict):
        globals_state = {}
        restored['_global_settings'] = globals_state
    for key, value in default_globals.items():
        globals_state.setdefault(key, value)
    runtime = restored.get('_runtime_snapshot') or {}
    if isinstance(runtime, dict):
        if not restored.get('forward_index') and isinstance(runtime.get('forward_index'), dict):
            restored['forward_index'] = runtime.get('forward_index') or {}
        if not restored.get('finance_active_chats') and runtime.get('finance_active_chats'):
            restored['finance_active_chats'] = runtime.get('finance_active_chats')
        if not restored.get('backup_flags') and runtime.get('backup_flags'):
            restored['backup_flags'] = runtime.get('backup_flags')
        for key, value in (runtime.get('global_settings') or {}).items():
            globals_state.setdefault(key, value)
    return restored

def _restore_runtime_state_from_data(restored: dict):
    """Загружает логическое состояние в оперативные структуры ДО первого save_data()."""
    finance_active_chats.clear()
    fac = restored.get('finance_active_chats') or {}
    if isinstance(fac, dict):
        items = fac.items()
    elif isinstance(fac, (list, tuple, set)):
        items = ((x, True) for x in fac)
    else:
        items = ()
    for cid, enabled in items:
        if enabled:
            try:
                finance_active_chats.add(int(cid))
            except Exception:
                pass
    if OWNER_ID:
        try:
            finance_active_chats.add(int(OWNER_ID))
        except Exception:
            pass
    flags = restored.get('backup_flags') or {}
    backup_flags['drive'] = bool(flags.get('drive', True))
    backup_flags['channel'] = bool(flags.get('channel', True))
    _load_forward_index_from_data(restored)
    _rebuild_forward_index_from_finance_records(restored)

def _v184_copy(value):
    try:
        return json.loads(json.dumps(value, ensure_ascii=False, default=str))
    except Exception:
        return copy.deepcopy(value)

def _v184_record_identity(chat_id: int, rec: dict) -> str:
    """Stable identity used only for safe restore de-duplication."""
    if not isinstance(rec, dict):
        return ''
    op = str(rec.get('operation_key') or '').strip()
    if op:
        return 'op:' + op
    for key in ('finance_record_uid', 'record_uid'):
        val = str(rec.get(key) or '').strip()
        if val:
            return key + ':' + val
    src = rec.get('source_msg_id') or rec.get('origin_msg_id') or rec.get('msg_id')
    if src not in (None, '', 0, '0'):
        return f'msg:{int(chat_id)}:{src}'
    rid = rec.get('id')
    ts = str(rec.get('timestamp') or '')
    amt = rec.get('amount')
    note = str(rec.get('note') or '')
    return f'legacy:{rid}:{ts}:{amt}:{note}'

def _v184_settings_scope_ok(chat_id: int, candidate: dict, platform_owner: bool=False) -> bool:
    """Allow exact scope metadata for platform owner; tenant managers cannot rebind a chat to another tenant."""
    if platform_owner:
        return True
    try:
        saved_tid = str((candidate or {}).get('tenant_id') or '')
        current_tid = str(tenant_id_for_chat(int(chat_id), create=False) or '') if 'tenant_id_for_chat' in globals() else ''
        if saved_tid and current_tid and (saved_tid != current_tid):
            return False
    except Exception:
        return False
    return True

def restore_forward_edges_exact(root_key: str, chat_id: int, outgoing: dict, incoming: dict) -> dict:
    """STRICT restore of forwarding edges belonging to one chat, without merge or per-edge side effects."""
    if root_key not in {'forward_rules', 'forward_finance'}:
        raise ValueError(f'Unsupported forwarding root: {root_key}')
    cid = str(int(chat_id))
    outgoing = outgoing if isinstance(outgoing, dict) else {}
    incoming = incoming if isinstance(incoming, dict) else {}
    lock = globals().get('_V166_FORWARD_STATE_LOCK')

    def _apply():
        root = data.setdefault(root_key, {})
        if not isinstance(root, dict):
            root = {}
            data[root_key] = root
        root.pop(cid, None)
        for src in list(root.keys()):
            row = root.get(src)
            if not isinstance(row, dict):
                continue
            row.pop(cid, None)
            if not row:
                root.pop(src, None)
        if outgoing:
            root[cid] = _v184_copy(outgoing)
        for src, value in incoming.items():
            ss = str(src)
            if ss == cid:
                if cid not in root and outgoing:
                    root[cid] = _v184_copy(outgoing)
                continue
            root.setdefault(ss, {})[cid] = _v184_copy(value)
    if lock is not None:
        with data_lock, lock:
            _apply()
    else:
        with data_lock:
            _apply()
    try:
        order = data.get('forward_pair_order')
        if isinstance(order, list):
            kept = []
            for key in order:
                try:
                    a, b = str(key).split(':', 1)
                except Exception:
                    kept.append(key)
                    continue
                if a == cid or b == cid:
                    continue
                kept.append(key)
            data['forward_pair_order'] = kept
    except Exception:
        pass
    return {'root': root_key, 'chat_id': int(chat_id), 'outgoing': len(outgoing), 'incoming': len(incoming)}

def _v184_apply_chat_settings_backup(chat_id: int, settings_backup: dict, *, platform_owner: bool=False) -> dict:
    """Strict file restore for chat settings. Current live settings/forward edges never fill gaps."""
    if not isinstance(settings_backup, dict):
        settings_backup = {}
    cid = str(int(chat_id))
    store = get_chat_store(int(chat_id))
    saved_settings = settings_backup.get('settings')
    restored_settings = 0
    if isinstance(saved_settings, dict):
        candidate = _v184_copy(saved_settings)
        if not _v184_settings_scope_ok(chat_id, candidate, platform_owner):
            current = dict(store.get('settings') or {})
            for k in ('tenant_id', 'owner_scope_id', 'owner_scope_settings', 'parent_first_chat_id', 'circle_level'):
                if k in current:
                    candidate[k] = _v184_copy(current[k])
                else:
                    candidate.pop(k, None)
        store['settings'] = candidate
        restored_settings = len(candidate)
        get_chat_store(int(chat_id))
    direct = {'finance_mode': 'finance_mode', 'balance_panel_id': 'balance_panel_id', 'balance_panel_mode': 'balance_panel_mode', 'current_view_day': 'current_view_day'}
    for src, dst in direct.items():
        if src in settings_backup:
            store[dst] = _v184_copy(settings_backup.get(src))
    compat = {'auto_backup_enabled': 'auto_backup_enabled', 'hidden_finance': 'hidden_finance', 'quick_balance_enabled': 'quick_balance_enabled', 'quick_balance_behavior': 'quick_balance_behavior'}
    st = store.setdefault('settings', {})
    for src, dst in compat.items():
        if src in settings_backup:
            st[dst] = _v184_copy(settings_backup.get(src))
    fr_out = settings_backup.get('forward_rules_outgoing')
    fr_in = settings_backup.get('forward_rules_incoming')
    ff_out = settings_backup.get('forward_finance_outgoing')
    ff_in = settings_backup.get('forward_finance_incoming')
    if fr_out is None or fr_in is None:
        g = settings_backup.get('global_forward_rules') or {}
        if fr_out is None and isinstance(g, dict):
            fr_out = g.get(cid) or {}
        if fr_in is None and isinstance(g, dict):
            fr_in = {src: (dsts or {}).get(cid) for src, dsts in g.items() if isinstance(dsts, dict) and cid in dsts}
    if ff_out is None or ff_in is None:
        g = settings_backup.get('global_forward_finance') or {}
        if ff_out is None and isinstance(g, dict):
            ff_out = g.get(cid) or {}
        if ff_in is None and isinstance(g, dict):
            ff_in = {src: (dsts or {}).get(cid) for src, dsts in g.items() if isinstance(dsts, dict) and cid in dsts}
    restore_forward_edges_exact('forward_rules', int(chat_id), fr_out or {}, fr_in or {})
    restore_forward_edges_exact('forward_finance', int(chat_id), ff_out or {}, ff_in or {})
    fac = settings_backup.get('finance_active_chats')
    enabled = bool(settings_backup.get('finance_mode', store.get('finance_mode', False)))
    if isinstance(fac, dict) and cid in fac:
        enabled = bool(fac.get(cid))
    if enabled:
        finance_active_chats.add(int(chat_id))
    else:
        finance_active_chats.discard(int(chat_id))
    data['finance_active_chats'] = {str(x): True for x in sorted(finance_active_chats)}
    global_flags = False
    if platform_owner and isinstance(settings_backup.get('backup_flags'), dict):
        flags = settings_backup.get('backup_flags') or {}
        backup_flags['drive'] = bool(flags.get('drive', True))
        backup_flags['channel'] = bool(flags.get('channel', True))
        data['backup_flags'] = {'drive': backup_flags['drive'], 'channel': backup_flags['channel']}
        global_flags = True
    return {'settings_keys': restored_settings, 'forward_edges': len(fr_out or {}) + len(fr_in or {}) + len(ff_out or {}) + len(ff_in or {}), 'global_flags': global_flags}

def _v186_restore_day_key_without_mutation(rec: dict, daily_hint: dict | None=None) -> str:
    """Derive the runtime day index without changing the backup record itself."""
    if isinstance(rec, dict):
        dk = str(rec.get('day_key') or '')[:10]
        if re.fullmatch('\\d{4}-\\d{2}-\\d{2}', dk):
            return dk
        ts = str(rec.get('timestamp') or '')[:10]
        if re.fullmatch('\\d{4}-\\d{2}-\\d{2}', ts):
            return ts
        dmy = str(rec.get('date') or '')[:8]
        m = re.fullmatch('(\\d{2})[:./-](\\d{2})[:./-](\\d{2})', dmy)
        if m:
            return f'20{m.group(3)}-{m.group(2)}-{m.group(1)}'
    if isinstance(daily_hint, dict) and isinstance(rec, dict):
        rid = rec.get('id')
        op = rec.get('operation_key')
        sm = rec.get('source_msg_id')
        for dk, rows in daily_hint.items():
            for old in rows or []:
                if not isinstance(old, dict):
                    continue
                if rid is not None and old.get('id') == rid or (op and old.get('operation_key') == op) or (sm and old.get('source_msg_id') == sm):
                    return str(dk)[:10]
    return today_key()

def _v186_rebuild_restore_derived(chat_id: int, daily_hint: dict | None=None) -> dict:
    """Rebuild only derived runtime indexes/balance; preserve every field/order of file records exactly."""
    store = get_chat_store(int(chat_id))
    records = store.get('records') if isinstance(store.get('records'), list) else []
    daily = {}
    total = 0.0
    valid = 0
    for rec in records:
        if not isinstance(rec, dict):
            continue
        dk = _v186_restore_day_key_without_mutation(rec, daily_hint)
        daily.setdefault(dk, []).append(rec)
        try:
            total += float(rec.get('amount', 0) or 0)
        except Exception:
            pass
        valid += 1
    store['daily_records'] = daily
    store['balance'] = total
    return {'records': valid, 'days': len(daily), 'balance': total}

def _v184_post_restore_rehydrate(restored: dict | None=None, chat_ids=None) -> dict:
    """One post-restore path. Per-chat restore stays targeted; global GZ/JSON may rebuild globally."""
    state = restored if isinstance(restored, dict) else data
    result = {'normalized_chats': 0, 'errors': [], 'targeted': chat_ids is not None}
    try:
        _restore_runtime_state_from_data(state)
    except Exception as exc:
        result['errors'].append('runtime:' + str(exc)[:160])
    ids = []
    if chat_ids is None:
        for cid_s in state.get('chats', {}) or {}:
            try:
                ids.append(int(cid_s))
            except Exception:
                pass
        try:
            tenant_v148_bootstrap()
            tenant_v148_enforce_forward_isolation()
        except Exception as exc:
            result['errors'].append('tenant:' + str(exc)[:160])
    else:
        for cid in chat_ids:
            try:
                ids.append(int(cid))
            except Exception:
                pass
        for cid in ids:
            try:
                st = get_chat_store(cid).get('settings') or {}
                tid = str(st.get('tenant_id') or '')
                if tid and 'tenant_get' in globals():
                    trow = tenant_get(tid)
                    if trow:
                        root = _tenants_root()
                        root.setdefault('chat_to_tenant', {})[str(cid)] = tid
                        chats = trow.setdefault('chat_ids', [])
                        if int(cid) not in [int(x) for x in chats]:
                            chats.append(int(cid))
            except Exception as exc:
                result['errors'].append(f'tenant:{cid}:' + str(exc)[:120])
    for cid in ids:
        try:
            _v186_rebuild_restore_derived(cid)
            result['normalized_chats'] += 1
        except Exception as exc:
            result['errors'].append(f'chat:{cid}:' + str(exc)[:120])
    try:
        rebuild_global_records()
    except Exception as exc:
        result['errors'].append('global:' + str(exc)[:160])
    try:
        state['forward_index'] = {}
        _load_forward_index_from_data(state)
        _rebuild_forward_index_from_finance_records(state)
    except Exception as exc:
        result['errors'].append('forward_rebuild:' + str(exc)[:160])
    if chat_ids is None:
        try:
            if 'restore_finance_window_runtime_state' in globals():
                restore_finance_window_runtime_state()
        except Exception as exc:
            result['errors'].append('windows:' + str(exc)[:160])
    return result

def _v186_clear_chat_scope_before_restore(chat_id: int) -> None:
    """Remove current working state for exactly one chat before file restore. Audit/constitution history stays immutable."""
    cid = int(chat_id)
    cs = str(cid)
    try:
        data.setdefault('chats', {}).pop(cs, None)
    except Exception:
        pass
    try:
        with SQLITE.lock:
            SQLITE.conn.execute('DELETE FROM cold_fields WHERE chat_id=?', (cs,))
            SQLITE.conn.execute('DELETE FROM chats WHERE chat_id=?', (cs,))
            SQLITE.conn.commit()
    except Exception as exc:
        raise RuntimeError(f'Не удалось очистить SQLite scope чата {cid}: {exc}')
    try:
        data.setdefault('active_messages', {}).pop(cs, None)
    except Exception:
        pass
    try:
        reg = data.setdefault('open_window_registry', {})
        for key, row in list(reg.items()):
            try:
                if int((row or {}).get('chat_id') or 0) == cid:
                    reg.pop(key, None)
            except Exception:
                continue
    except Exception:
        pass
    try:
        restore_forward_edges_exact('forward_rules', cid, {}, {})
        restore_forward_edges_exact('forward_finance', cid, {}, {})
    except Exception:
        pass
    try:
        finance_active_chats.discard(cid)
        data['finance_active_chats'] = {str(x): True for x in sorted(finance_active_chats)}
    except Exception:
        pass
    try:
        data['forward_index'] = {}
    except Exception:
        pass
    try:
        hist = globals().get('_WINDOW_NAV_HISTORY')
        lock = globals().get('_WINDOW_NAV_HISTORY_LOCK')
        if isinstance(hist, dict):
            if lock is not None:
                with lock:
                    for key in list(hist):
                        if isinstance(key, tuple) and key and (int(key[0]) == cid):
                            hist.pop(key, None)
            else:
                for key in list(hist):
                    if isinstance(key, tuple) and key and (int(key[0]) == cid):
                        hist.pop(key, None)
        clear_kv = globals().get('kv_nav_clear_chat_v248')
        if callable(clear_kv):
            clear_kv(cid)
    except Exception:
        pass

def _v184_restore_per_chat_payload(chat_id: int, payload: dict, *, platform_owner: bool=False) -> dict:
    """STRICT REPLACE FROM FILE: no current records/settings are merged into the restored chat."""
    kind = str(payload.get('kind') or 'legacy_chat_backup')
    backup_records = payload.get('records') if isinstance(payload.get('records'), list) else []
    if not backup_records and isinstance(payload.get('daily_records'), dict):
        for dk in sorted(payload.get('daily_records') or {}):
            for rec in (payload.get('daily_records') or {}).get(dk) or []:
                if isinstance(rec, dict):
                    rr = _v184_copy(rec)
                    rr.setdefault('day_key', str(dk))
                    backup_records.append(rr)
    seen_ids = set()
    for rec in backup_records:
        if not isinstance(rec, dict):
            continue
        try:
            rid = int(rec.get('id') or 0)
        except Exception:
            rid = 0
        if rid > 0:
            if rid in seen_ids:
                raise RuntimeError(f'Backup inconsistent: duplicate record id={rid}')
            seen_ids.add(rid)
    backup_balance = None
    if 'balance' in payload:
        try:
            backup_balance = float(payload.get('balance') or 0)
        except Exception:
            backup_balance = None
    backup_rows_balance = sum((float((r or {}).get('amount', 0) or 0) for r in backup_records if isinstance(r, dict)))
    if backup_balance is not None and abs(backup_balance - backup_rows_balance) > 0.011:
        raise RuntimeError(f'Backup inconsistent: balance={backup_balance} but records={backup_rows_balance}')
    old_store = data.get('chats', {}).get(str(int(chat_id)))
    old_count = 0
    try:
        old_count = len((old_store or {}).get('records') or [])
    except Exception:
        pass
    _v186_clear_chat_scope_before_restore(int(chat_id))
    store = get_chat_store(int(chat_id))
    chat_state = payload.get('chat_state')
    restored_chat_state_keys = 0
    if isinstance(chat_state, dict):
        for key, value in chat_state.items():
            if str(key) in {'records', 'daily_records', 'daily_records_by_date', 'balance', 'next_id', 'info', 'known_chats', 'settings'}:
                continue
            store[str(key)] = _v184_copy(value)
            restored_chat_state_keys += 1
    store['records'] = [_v184_copy(r) for r in backup_records if isinstance(r, dict)]
    store['daily_records'] = {}
    store['info'] = _v184_copy(payload.get('info') or {}) if isinstance(payload.get('info'), dict) else {}
    store['known_chats'] = _v184_copy(payload.get('known_chats') or {}) if isinstance(payload.get('known_chats'), dict) else {}
    settings_result = _v184_apply_chat_settings_backup(int(chat_id), payload.get('settings_backup') if isinstance(payload.get('settings_backup'), dict) else {}, platform_owner=platform_owner)
    _v186_rebuild_restore_derived(int(chat_id), payload.get('daily_records') if isinstance(payload.get('daily_records'), dict) else None)
    if 'next_id' in payload:
        try:
            store['next_id'] = int(payload.get('next_id'))
        except Exception:
            store['next_id'] = payload.get('next_id')
    else:
        numeric_ids = []
        for rec in store.get('records') or []:
            try:
                numeric_ids.append(int(rec.get('id') or 0))
            except Exception:
                pass
        store['next_id'] = max([1] + [x + 1 for x in numeric_ids if x >= 0])
    post = _v184_post_restore_rehydrate(data, [int(chat_id)])
    save_data(data, chat_ids=[int(chat_id)], root_only=False)
    return {'kind': kind, 'backup_records': len(backup_records), 'records_after': len(store.get('records') or []), 'replaced_live_records': int(old_count), 'preserved_live_records': 0, 'settings': settings_result, 'chat_state_keys': restored_chat_state_keys, 'restore_policy': 'strict_replace_from_file', 'post': post}

def restore_from_json(chat_id: int, path: str, *, actor_user_id: int | None=None):
    """Full restore contract for universal JSON/ISON and per-chat backups."""
    global data
    raw_payload = _load_json(path, None)
    if not isinstance(raw_payload, dict):
        raise RuntimeError('JSON/ISON повреждён или пустой')
    platform_owner = False
    try:
        uid = int(actor_user_id or 0)
        platform_owner = bool(uid and (uid == int(OWNER_ID or 0) or ('_v153_platform_owner' in globals() and _v153_platform_owner(uid))))
    except Exception:
        platform_owner = False
    payload = _extract_universal_state(raw_payload)
    if 'chats' in payload and isinstance(payload.get('chats'), dict):
        if actor_user_id is not None and (not platform_owner):
            raise RuntimeError('Полный глобальный JSON может восстановить только владелец платформы')
        restored_state = _migrate_full_state(payload)
        try:
            with SQLITE.lock:
                SQLITE.conn.execute('DELETE FROM cold_fields')
                SQLITE.conn.execute('DELETE FROM chats')
                SQLITE.conn.commit()
        except Exception as exc:
            raise RuntimeError(f'Не удалось очистить SQLite перед global JSON restore: {exc}')
        data = restored_state
        post = _v184_post_restore_rehydrate(data)
        save_data(data, full=True)
        if not is_data_effectively_empty_for_restore(data):
            _clear_restore_guard()
        log_info(f"restore_from_json v184: universal global state restored schema={(raw_payload.get('_universal_backup') or {}).get('schema_version', 'legacy')} chats={len(data.get('chats', {}) or {})}")
        return {'scope': 'global', 'chats': len(data.get('chats', {}) or {}), 'post': post}
    if 'records' in payload or 'daily_records' in payload:
        result = _v184_restore_per_chat_payload(int(chat_id), payload, platform_owner=platform_owner)
        if get_chat_store(int(chat_id)).get('records') or any(get_chat_store(int(chat_id)).get('daily_records', {}).values()):
            _clear_restore_guard()
        log_info(f'restore_from_json v186: chat {chat_id} strict file state restored; result={result}')
        return result
    raise RuntimeError("Неизвестный формат JSON/ISON (нет 'chats' и нет 'records/daily_records').")

def restore_from_csv(chat_id: int, path: str):
    """
    Восстановление из CSV (пер-чат).
    Ожидает колонки как у тебя в CSV:
    chat_id,ID,short_id,timestamp,amount,note,owner,day_key
    """
    store = get_chat_store(chat_id)
    daily = {}
    records = []
    with open(path, 'r', encoding='utf-8', newline='') as f:
        r = csv.DictReader(f)
        for row in r:
            try:
                dk = (row.get('day_key') or today_key()).strip()
                amt = parse_csv_amount(row.get('amount') or 0)
                note = (row.get('note') or '').strip()
                owner = row.get('owner') or ''
                ts = (row.get('timestamp') or now_local().isoformat(timespec='seconds')).strip()
                rec = {'id': int(row.get('ID') or 0) or 0, 'short_id': row.get('short_id') or '', 'timestamp': ts, 'amount': amt, 'note': note, 'owner': owner}
                daily.setdefault(dk, []).append(rec)
                records.append(rec)
            except Exception as e:
                log_error(f'restore_from_csv row skip: {e}')
    store['daily_records'] = daily
    store['records'] = records
    renumber_chat_records(chat_id)
    recalc_balance(chat_id)
    rebuild_global_records()
    save_data(data)
    finance_changed(chat_id, get_chat_store(chat_id).get('current_view_day', today_key()), reason='restore_csv_core', delay=0.1)
    log_info(f'restore_from_csv: chat {chat_id} restored from CSV')

def fmt_num(x):
    """
    Европейский формат вывода с обязательным знаком.
    В фин-окнах округляем до целого, чтобы не появлялись хвосты float вроде
    +2.683.012,399999999907.
    Примеры:
        +1234.56 → +1.235
        -800     → -800
        0        → +0
    """
    try:
        x = float(x or 0)
    except Exception:
        try:
            x = float(str(x).replace(' ', '').replace('.', '').replace(',', '.'))
        except Exception:
            x = 0.0
    sign = '+' if x >= 0 else '-'
    whole = int(round(abs(x)))
    s = f'{whole:,}'.replace(',', '.')
    return f'{sign}{s}'
num_re = re.compile("[+\\-–]?\\s*\\d[\\d\\s.,_'’]*")

def fmt_num_plain(x):
    """
    Формат числа БЕЗ знака (+/-).
    Использовать только для отчётов по статьям расходов.
    """
    try:
        return fmt_num(x).lstrip('+-')
    except Exception:
        return str(x)

def parse_amount(raw: str) -> float:
    """
    Универсальный парсер:
    - понимает любые разделители
    - смешанные форматы (1.234,56 / 1,234.56)
    - определяет десятичную часть по самому правому разделителю
    - число без знака = расход
    """
    s = raw.strip()
    is_negative = s.startswith('-') or s.startswith('–')
    is_positive = s.startswith('+')
    s_clean = s.lstrip('+-–').strip()
    s_clean = s_clean.replace(' ', '').replace('_', '').replace('’', '').replace("'", '')
    if ',' not in s_clean and '.' not in s_clean:
        value = float(s_clean)
        if not is_positive and (not is_negative):
            is_negative = True
        return -value if is_negative else value
    if '.' in s_clean and ',' in s_clean:
        if s_clean.rfind(',') > s_clean.rfind('.'):
            s_clean = s_clean.replace('.', '')
            s_clean = s_clean.replace(',', '.')
        else:
            s_clean = s_clean.replace(',', '')
    elif ',' in s_clean:
        pos = s_clean.rfind(',')
        if len(s_clean) - pos - 1 in (1, 2):
            s_clean = s_clean.replace('.', '')
            s_clean = s_clean.replace(',', '.')
        else:
            s_clean = s_clean.replace(',', '')
    elif '.' in s_clean:
        pos = s_clean.rfind('.')
        if len(s_clean) - pos - 1 in (1, 2):
            s_clean = s_clean.replace(',', '')
        else:
            s_clean = s_clean.replace('.', '')
    value = float(s_clean)
    if not is_positive and (not is_negative):
        is_negative = True
    return -value if is_negative else value

def note_has_income_marker(note: str) -> bool:
    """True, если текст явно говорит о приходе денег.
    Учитывает «приход» в любом регистре, но не срабатывает на «не приход», «без прихода», «нет прихода».
    """
    t = re.sub('\\s+', ' ', str(note or '').casefold()).strip()
    if not t:
        return False
    negative_patterns = ('(?:^|\\s)не\\s+приход', '(?:^|\\s)без\\s+приход', '(?:^|\\s)нет\\s+приход', '(?:^|\\s)ne\\s+prihod', '(?:^|\\s)bez\\s+prihod', '(?:^|\\s)net\\s+prihod')
    if any((re.search(pat, t, re.I) for pat in negative_patterns)):
        return False
    income_patterns = ('приход', 'prihod', 'prixod', 'обмен', 'возврат', 'сдача')
    return any((re.search(pat, t, re.I) for pat in income_patterns))
USD_EXPLICIT_AFTER_RE = re.compile("(?P<sign>[+\\-–]?)\\s*(?P<num>\\d[\\d\\s.,_'’]*?)(?P<mult>[kк])?\\s*(?P<cur>usd|usд|усд|\\$)", re.I)
USD_EXPLICIT_PREFIX_RE = re.compile("\\$\\s*(?P<sign>[+\\-–]?)\\s*(?P<num>\\d[\\d\\s.,_'’]*?)(?P<mult>[kк])?(?=\\s|$)", re.I)
USD_COMPACT_K_RE = re.compile('(?P<sign>[+\\-–]?)\\s*(?P<num>\\d+(?:[.,]\\d+)?)\\s*(?P<plus_after>\\+)?\\s*[kк]\\b', re.I)
USD_EXCHANGE_RE = re.compile('обмен|exchange|change', re.I)
USD_PESO_RE = re.compile('песс?о|peso|ars|арс', re.I)

def _parse_usd_number_parts(sign: str, num: str, mult: str='') -> float:
    raw = str(num or '').strip()
    if not raw:
        raise ValueError('empty usd amount')
    value = abs(float(parse_amount('+' + raw)))
    if str(mult or '').strip().casefold() in {'k', 'к'}:
        value *= 1000.0
    if str(sign or '').strip() in {'-', '–'}:
        return -value
    if str(sign or '').strip() == '+':
        return value
    return -value

def extract_usd_transaction(text: str) -> dict | None:
    """Извлекает отдельное движение USD из пользовательской строки.

    Правила v93:
    - явные USD/УСД/$: плюс = приход, минус/без знака = расход;
    - «обмен ... песо/ARS» с компактным 1к/2к = расход USD;
    - «+1к от ...» = приход USD;
    - «И 5+к» = приход 5000 USD.
    Возвращает span USD-фрагмента, чтобы ARS-часть можно было разобрать отдельно.
    """
    raw = str(text or '')
    if not raw.strip():
        return None
    candidates = []
    for rx in (USD_EXPLICIT_AFTER_RE, USD_EXPLICIT_PREFIX_RE):
        for m in rx.finditer(raw):
            try:
                amount = _parse_usd_number_parts(m.group('sign'), m.group('num'), m.group('mult'))
            except Exception:
                continue
            if not str(m.group('sign') or '').strip():
                low = raw.casefold()
                if ('приход' in low or 'prihod' in low) and (not USD_EXCHANGE_RE.search(low)):
                    amount = abs(amount)
            candidates.append({'amount': float(amount), 'span': m.span(), 'explicit': True, 'token': m.group(0)})
    if candidates:
        candidates.sort(key=lambda x: x['span'][0])
        info = candidates[0]
        info['note'] = re.sub('\\s+', ' ', raw).strip().lower()
        return info
    low = raw.casefold()
    k_matches = list(USD_COMPACT_K_RE.finditer(raw))
    if not k_matches:
        return None
    for m in k_matches:
        before = low[max(0, m.start() - 6):m.start()]
        if m.group('plus_after') and re.search('(?:^|\\s)и\\s*$', before):
            value = abs(_parse_usd_number_parts('+', m.group('num'), 'к'))
            return {'amount': value, 'span': m.span(), 'explicit': False, 'token': m.group(0), 'note': re.sub('\\s+', ' ', raw).strip().lower()}
    if USD_EXCHANGE_RE.search(low) and (USD_PESO_RE.search(low) or len(num_re.findall(raw)) >= 2):
        exchange_pos = USD_EXCHANGE_RE.search(low).start()
        m = min(k_matches, key=lambda x: abs(x.start() - exchange_pos))
        value = abs(_parse_usd_number_parts('+', m.group('num'), 'к'))
        return {'amount': -value, 'span': m.span(), 'explicit': False, 'token': m.group(0), 'note': re.sub('\\s+', ' ', raw).strip().lower()}
    for m in k_matches:
        if str(m.group('sign') or '').strip() == '+' and (re.search('\\bот\\b', low) or 'приход' in low):
            value = abs(_parse_usd_number_parts('+', m.group('num'), 'к'))
            return {'amount': value, 'span': m.span(), 'explicit': False, 'token': m.group(0), 'note': re.sub('\\s+', ' ', raw).strip().lower()}
    return None

def _remove_usd_fragment_for_ars(text: str, usd_info: dict | None) -> str:
    raw = str(text or '')
    if not usd_info or not usd_info.get('span'):
        return raw
    try:
        start, end = usd_info['span']
        rest = (raw[:int(start)] + ' ' + raw[int(end):]).strip()
    except Exception:
        rest = raw
    rest = re.sub("(?i)\\bпо\\s*[+\\-–]?\\s*\\d[\\d\\s.,_'’]*", ' ', rest)
    return re.sub('\\s+', ' ', rest).strip()

def parse_financial_components(text: str) -> dict:
    """Разбирает одну строку одновременно на ARS и отдельное движение USD."""
    raw = str(text or '').strip()
    usd = extract_usd_transaction(raw)
    if usd is None:
        amount, note = split_amount_and_note(raw)
        return {'amount': float(amount), 'note': note, 'usd_amount': None, 'usd_note': '', 'usd_only': False, 'source_finance_text': raw}
    ars_text = _remove_usd_fragment_for_ars(raw, usd)
    ars_amount = None
    ars_note = ''
    if num_re.search(ars_text or ''):
        try:
            ars_amount, ars_note = split_amount_and_note(ars_text)
        except Exception:
            ars_amount, ars_note = (None, '')
    usd_only = ars_amount is None
    try:
        _us, _ue = usd.get('span') or (0, 0)
        usd_note = re.sub('\\s+', ' ', raw[:int(_us)] + ' ' + raw[int(_ue):]).strip().lower()
    except Exception:
        usd_note = ''
    return {'amount': float(ars_amount or 0.0), 'note': ars_note if ars_amount is not None else re.sub('\\s+', ' ', raw).strip().lower(), 'usd_amount': float(usd.get('amount', 0.0) or 0.0), 'usd_note': usd_note, 'usd_only': bool(usd_only), 'source_finance_text': raw}

def parse_usd_edit_value(text: str):
    """Редактирование уже найденной USD-записи: число без знака = расход, + = приход."""
    m = num_re.search(str(text or ''))
    if not m:
        raise ValueError('no usd number')
    amount = parse_amount(m.group(0))
    note = (str(text or '')[:m.start()] + ' ' + str(text or '')[m.end():]).strip()
    note = re.sub('\\s+', ' ', note).lower()
    return (float(amount), note)

def split_amount_and_note(text: str):
    """
    Возвращает:
        amount (float)
        note (str)
    """
    m = num_re.search(text)
    if not m:
        raise ValueError('no number found')
    raw_number = m.group(0)
    amount = parse_amount(raw_number)
    note = text.replace(raw_number, ' ').strip()
    note = re.sub('\\s+', ' ', note).lower()
    if amount < 0 and note_has_income_marker(note):
        amount = abs(amount)
    return (amount, note)
EXPENSE_CATEGORIES = {'ПРОДУКТЫ': ['продукты', 'шб', 'еда'], 'ОРГТЕХНИКА': ['оргтех', 'оргтехника'], 'СВЯЗЬ': ['тел', 'tel', 'пополнение'], 'АВТО': ['авто', 'бензин', 'билет'], 'ПЕРЕВОДЫ': ['переводы', 'перевод', 'переводчик'], 'ПРОЧЕЕ': []}
EXPENSE_CATEGORY_SLUGS = {'ПРОДУКТЫ': 'food', 'ОРГТЕХНИКА': 'org', 'СВЯЗЬ': 'link', 'АВТО': 'auto', 'ПЕРЕВОДЫ': 'transfers', 'ПРОЧЕЕ': 'other'}
CATEGORY_BY_SLUG = {v: k for k, v in EXPENSE_CATEGORY_SLUGS.items()}
EXPENSE_CATEGORY_ORDER = ['ПРОДУКТЫ', 'ОРГТЕХНИКА', 'СВЯЗЬ', 'АВТО', 'ПЕРЕВОДЫ', 'ПРОЧЕЕ']

def _custom_category_list(store: dict | None) -> list:
    if not isinstance(store, dict):
        return []
    settings = store.setdefault('settings', {})
    raw = settings.setdefault('expense_categories_custom', [])
    if isinstance(raw, dict):
        raw = list(raw.values())
        settings['expense_categories_custom'] = raw
    if not isinstance(raw, list):
        settings['expense_categories_custom'] = []
        return []
    out = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        raw_name = str(item.get('name') or '').strip()
        name = _clean_category_display_name(raw_name).upper()
        if name and raw_name != name:
            item['name'] = name
        keywords = [str(x).strip().lower() for x in item.get('keywords') or [] if str(x).strip()]
        slug = str(item.get('slug') or '').strip()
        if not name or not keywords:
            continue
        if not slug:
            slug = make_custom_category_slug(name, raw)
            item['slug'] = slug
        out.append({'name': name, 'slug': slug, 'keywords': keywords})
    return out

def _base_category_overrides(store: dict | None) -> dict:
    if not isinstance(store, dict):
        return {}
    settings = store.setdefault('settings', {})
    raw = settings.setdefault('expense_categories_base_overrides', {})
    if not isinstance(raw, dict):
        raw = {}
        settings['expense_categories_base_overrides'] = raw
    return raw

def _base_category_items(store: dict | None=None) -> list[dict]:
    overrides = _base_category_overrides(store)
    items = []
    for default_name in EXPENSE_CATEGORY_ORDER:
        slug = EXPENSE_CATEGORY_SLUGS.get(default_name)
        ov = overrides.get(slug) if isinstance(overrides, dict) else None
        if not isinstance(ov, dict):
            ov = {}
        raw_name = str(ov.get('name') or default_name).strip()
        name = _clean_category_display_name(raw_name).upper()
        if ov and name and (raw_name != name):
            ov['name'] = name
        keywords = ov.get('keywords') if isinstance(ov.get('keywords'), list) else EXPENSE_CATEGORIES.get(default_name, [])
        keywords = [str(x).strip().lower() for x in keywords or [] if str(x).strip()]
        items.append({'name': name, 'slug': slug, 'keywords': keywords, 'base': True, 'default_name': default_name})
    return items

def _base_category_item_by_slug(store: dict | None, slug: str) -> dict | None:
    slug = str(slug or '')
    for item in _base_category_items(store):
        if item.get('slug') == slug:
            return item
    return None

def make_custom_category_slug(name: str, existing=None) -> str:
    base = re.sub('[^0-9a-zA-Zа-яА-Я]+', '_', str(name or '').lower()).strip('_')[:32] or 'cat'
    slug = 'custom_' + base
    used = set(EXPENSE_CATEGORY_SLUGS.values())
    for item in existing or []:
        if isinstance(item, dict) and item.get('slug'):
            used.add(str(item.get('slug')))
    if slug not in used:
        return slug
    i = 2
    while f'{slug}_{i}' in used:
        i += 1
    return f'{slug}_{i}'

def get_expense_category_order_slugs(store: dict | None=None) -> list[str]:
    """Стабильный порядок статей сверху вниз; пользователь может менять его в v91."""
    items = list(_base_category_items(store)) + list(_custom_category_list(store))
    available = [str(item.get('slug') or '') for item in items if str(item.get('slug') or '')]
    try:
        settings = (store or {}).setdefault('settings', {})
        saved = [str(x) for x in settings.get('expense_category_order_slugs') or [] if str(x)]
    except Exception:
        saved = []
    result = [slug for slug in saved if slug in available]
    result.extend((slug for slug in available if slug not in result))
    return result

def get_expense_category_order(store: dict | None=None) -> list[str]:
    by_slug = {}
    for item in list(_base_category_items(store)) + list(_custom_category_list(store)):
        slug = str(item.get('slug') or '')
        if slug:
            by_slug[slug] = item.get('name')
    return [by_slug[slug] for slug in get_expense_category_order_slugs(store) if slug in by_slug]

def move_expense_category_order(store: dict, slug: str, direction: str) -> bool:
    order = get_expense_category_order_slugs(store)
    slug = str(slug or '')
    if slug not in order:
        return False
    idx = order.index(slug)
    new_idx = idx - 1 if str(direction).lower() == 'up' else idx + 1
    if new_idx < 0 or new_idx >= len(order):
        return False
    order[idx], order[new_idx] = (order[new_idx], order[idx])
    store.setdefault('settings', {})['expense_category_order_slugs'] = order
    return True
_category_order_selection = {}

def _category_order_selection_key(chat_id: int, params: tuple) -> tuple:
    return (int(chat_id),) + tuple((str(x) for x in params))

def move_expense_category_to_position(store: dict, slug: str, position: int) -> bool:
    """Вставка статьи в новую позицию со сдвигом промежуточных статей."""
    order = get_expense_category_order_slugs(store)
    slug = str(slug or '')
    if slug not in order or not order:
        return False
    try:
        target_idx = max(0, min(len(order) - 1, int(position) - 1))
    except Exception:
        return False
    old_idx = order.index(slug)
    if old_idx == target_idx:
        return True
    order.pop(old_idx)
    order.insert(target_idx, slug)
    store.setdefault('settings', {})['expense_category_order_slugs'] = order
    return True

def get_expense_category_slug(category: str, store: dict | None=None) -> str | None:
    category = _clean_category_display_name(str(category or '')).upper()
    for item in _base_category_items(store):
        if category in {str(item.get('name') or '').upper(), str(item.get('default_name') or '').upper()}:
            return item.get('slug')
    for item in _custom_category_list(store):
        if item['name'] == category:
            return item['slug']
    return None

def get_category_by_slug(slug: str, store: dict | None=None) -> str | None:
    slug = str(slug or '').strip()
    base = _base_category_item_by_slug(store, slug)
    if base:
        return base.get('name')
    for item in _custom_category_list(store):
        if item['slug'] == slug:
            return item['name']
    return None

def parse_category_definition(text: str):
    raw = _clean_category_display_name(str(text or '').strip())
    if not raw:
        raise ValueError('empty')
    if raw.lower() in {'отмена', 'cancel', '/cancel'}:
        return (None, None)
    sep = ':' if ':' in raw else '|' if '|' in raw else '-' if ' - ' in raw else None
    if not sep:
        raise ValueError('format')
    name, keys = raw.split(sep, 1)
    name = re.sub('\\s+', ' ', name.strip()).upper()
    keywords = [re.sub('\\s+', ' ', x.strip().lower()) for x in re.split('[,;]', keys) if x.strip()]
    if not name or not keywords:
        raise ValueError('format')
    return (name, keywords)

def add_custom_expense_category(chat_id: int, name: str, keywords: list[str]) -> dict:
    store = get_chat_store(chat_id)
    settings = store.setdefault('settings', {})
    custom = settings.setdefault('expense_categories_custom', [])
    if not isinstance(custom, list):
        custom = []
        settings['expense_categories_custom'] = custom
    name = str(name or '').strip().upper()
    keywords = [str(x).strip().lower() for x in keywords or [] if str(x).strip()]
    for item in custom:
        if isinstance(item, dict) and str(item.get('name', '')).strip().upper() == name:
            item['keywords'] = sorted(set((item.get('keywords') or []) + keywords))
            save_data(data)
            schedule_config_backup_for_chats(chat_id)
            bot_journal('category_updated', chat_id, f"{name}: {', '.join(item['keywords'])}")
            return item
    item = {'name': name, 'slug': make_custom_category_slug(name, custom), 'keywords': sorted(set(keywords))}
    custom.append(item)
    save_data(data)
    schedule_config_backup_for_chats(chat_id)
    bot_journal('category_added', chat_id, f"{name}: {', '.join(item['keywords'])}")
    return item

def expense_keyword_matches(note: str, keyword: str) -> bool:
    """Match a configured word/phrase without matching it inside another word."""
    note = re.sub('\\s+', ' ', str(note or '').casefold()).strip()
    keyword = re.sub('\\s+', ' ', str(keyword or '').casefold()).strip()
    if not note or not keyword:
        return False
    pattern = '(?<![\\w])' + re.escape(keyword).replace('\\ ', '\\s+') + '(?![\\w])'
    return bool(re.search(pattern, note, flags=re.UNICODE))

def financial_view_is_usd(store: dict | None) -> bool:
    """True when the visible finance shell is switched to 💵 USD operations."""
    try:
        return bool((store or {}).setdefault('settings', {}).get('usd_transactions_view', False))
    except Exception:
        return False

def financial_view_amount(store: dict | None, rec: dict | None) -> float:
    try:
        key = 'usd_amount' if financial_view_is_usd(store) else 'amount'
        return float((rec or {}).get(key, 0) or 0)
    except Exception:
        return 0.0

def financial_view_note(store: dict | None, rec: dict | None) -> str:
    rec = rec or {}
    if financial_view_is_usd(store):
        return str(rec.get('usd_note') or rec.get('note') or '')
    return str(rec.get('note') or '')

def financial_view_short_id(store: dict | None, rec: dict | None) -> str:
    rec = rec or {}
    if financial_view_is_usd(store):
        return str(rec.get('usd_short_id') or f"U{rec.get('id', '')}")
    return str(rec.get('short_id') or f"R{rec.get('id', '')}")

def financial_view_record_visible(store: dict | None, rec: dict | None) -> bool:
    rec = rec or {}
    if financial_view_is_usd(store):
        try:
            return abs(float(rec.get('usd_amount', 0) or 0)) > 0
        except Exception:
            return False
    return not bool(rec.get('usd_only', False))

def financial_view_records_for_day_store(store: dict | None, day_key: str) -> list[dict]:
    try:
        rows = ((store or {}).get('daily_records', {}) or {}).get(str(day_key), []) or []
        return sorted([r for r in rows if isinstance(r, dict) and financial_view_record_visible(store, r)], key=record_sort_key)
    except Exception:
        return []

def financial_view_total_balance(store: dict | None) -> float:
    total = 0.0
    for rec in (store or {}).get('records', []) or []:
        if not isinstance(rec, dict) or not financial_view_record_visible(store, rec):
            continue
        total += financial_view_amount(store, rec)
    return float(total)

def financial_view_balance_through_day(store: dict | None, day_key: str) -> float:
    total = 0.0
    for rec in sorted((store or {}).get('records', []) or [], key=record_sort_key):
        dk = _record_day_key(rec)
        if dk > str(day_key):
            break
        if financial_view_record_visible(store, rec):
            total += financial_view_amount(store, rec)
    return float(total)

def format_category_view_amount(store: dict | None, amount: float, category_mixed: bool=False) -> str:
    if financial_view_is_usd(store):
        try:
            return f'${fmt_num_plain(abs(float(amount or 0)))}'
        except Exception:
            return '$0'
    return format_category_amount(store or {}, amount, category_mixed)

def resolve_expense_category(note: str, store: dict | None=None):
    """Определяет статью расхода; всё без совпавших ключей попадает в ПРОЧЕЕ."""
    for item in _custom_category_list(store):
        for kw in item.get('keywords', []):
            if expense_keyword_matches(note, kw):
                return item.get('name')
    for item in _base_category_items(store):
        if item.get('slug') == 'other':
            continue
        for kw in item.get('keywords', []):
            if expense_keyword_matches(note, kw):
                return item.get('name')
    other = _base_category_item_by_slug(store, 'other')
    return (other or {}).get('name') or 'ПРОЧЕЕ'

def resolve_expense_category_for_record(rec: dict, store: dict | None=None):
    """Учитывает ручной перенос записи из ПРОЧЕЕ в выбранную статью."""
    try:
        override_slug = str((rec or {}).get('category_override_slug') or '').strip()
        if override_slug:
            category = get_category_by_slug(override_slug, store)
            if category:
                return category
    except Exception:
        pass
    return resolve_expense_category((rec or {}).get('note', ''), store)

def calc_categories_for_period(store: dict, start: str, end: str) -> dict:
    """Считает суммы расходов по статьям (только отрицательные amount) в диапазоне дат включительно."""
    out = {}
    daily = store.get('daily_records', {}) or {}
    for day, records in daily.items():
        if not start <= day <= end:
            continue
        for r in records or []:
            if not financial_view_record_visible(store, r):
                continue
            amt = financial_view_amount(store, r)
            if amt >= 0:
                continue
            cat = resolve_expense_category(financial_view_note(store, r), store)
            try:
                override_slug = str((r or {}).get('category_override_slug') or '').strip()
                if override_slug:
                    cat = get_category_by_slug(override_slug, store) or cat
            except Exception:
                pass
            if not cat:
                continue
            out[cat] = out.get(cat, 0) + -amt
    return out

def _record_int_id(rec: dict) -> int:
    try:
        return int((rec or {}).get('id', 0) or 0)
    except Exception:
        return 0

def sorted_records_for_day(store: dict, day_key: str) -> list:
    return financial_view_records_for_day_store(store, day_key)

def expense_anchor_records_for_day(store: dict, day_key: str) -> list:
    """Расходные записи дня, которые можно выбрать как точную границу периода."""
    out = []
    for rec in sorted_records_for_day(store, day_key):
        try:
            if financial_view_amount(store, rec) < 0:
                out.append(rec)
        except Exception:
            continue
    return out

def expense_anchor_button_label(rec: dict, store: dict | None=None) -> str:
    """Короткая, но понятная подпись кнопки точного расхода."""
    try:
        raw_amount = financial_view_amount(store, rec)
        amount = f"{('+' if raw_amount >= 0 else '-')}${fmt_num_plain(abs(raw_amount))}" if financial_view_is_usd(store) else format_store_amount(store or {}, raw_amount, mixed_space=False, ars_plain=False)
    except Exception:
        amount = str(financial_view_amount(store, rec))
    note = _clean_category_display_name(re.sub('\\s+', ' ', financial_view_note(store, rec)).strip())
    category = _clean_category_display_name(resolve_expense_category(note, store) or '')
    try:
        override_slug = str((rec or {}).get('category_override_slug') or '').strip()
        if override_slug:
            category = _clean_category_display_name(get_category_by_slug(override_slug, store) or category)
    except Exception:
        pass
    rec_code = financial_view_short_id(store, rec)
    parts = [rec_code, amount]
    if note:
        parts.append(note[:30])
    if category and category.casefold() not in note.casefold():
        parts.append(f'[{category[:16]}]')
    return ' • '.join(parts)[:62]

def exact_record_range(store: dict, start_day: str, start_rid: int | None, end_day: str, end_rid: int | None):
    """Записи между двумя точными границами включительно.

    start_rid=0/None означает начало стартового дня.
    end_rid=0/None означает конец конечного дня.
    Граница выбирается по расходу, но в экспорт попадают все записи между
    выбранными позициями: и расходы, и приходы.
    """
    start_day = str(start_day)[:10]
    end_day = str(end_day)[:10]
    try:
        start_rid = int(start_rid or 0)
    except Exception:
        start_rid = 0
    try:
        end_rid = int(end_rid or 0)
    except Exception:
        end_rid = 0
    if end_day < start_day:
        start_day, end_day = (end_day, start_day)
        start_rid, end_rid = (end_rid, start_rid)
    rows = []
    daily = store.get('daily_records', {}) or {}
    for day_key in sorted(daily.keys()):
        if not start_day <= day_key <= end_day:
            continue
        recs = sorted_records_for_day(store, day_key)
        if not recs:
            continue
        lo = 0
        hi = len(recs) - 1
        if day_key == start_day and start_rid:
            found = next((idx for idx, rec in enumerate(recs) if _record_int_id(rec) == start_rid), None)
            if found is not None:
                lo = found
        if day_key == end_day and end_rid:
            found = next((idx for idx, rec in enumerate(recs) if _record_int_id(rec) == end_rid), None)
            if found is not None:
                hi = found
        if lo > hi:
            continue
        for rec in recs[lo:hi + 1]:
            rows.append((day_key, rec))
    return rows

def exact_boundary_text(store: dict, day_key: str, rid: int | None, is_start: bool) -> str:
    rid = int(rid or 0)
    if not rid:
        return f"{fmt_date_ddmmyy(day_key)} — {('с начала дня' if is_start else 'до конца дня')}"
    rec = next((_r for _r in sorted_records_for_day(store, day_key) if _record_int_id(_r) == rid), None)
    if not rec:
        return f"{fmt_date_ddmmyy(day_key)} — {('с начала дня' if is_start else 'до конца дня')}"
    return f'{fmt_date_ddmmyy(day_key)} — {expense_anchor_button_label(rec, store)}'

def calc_categories_for_record_range(store: dict, start_day: str, start_rid: int, end_day: str, end_rid: int) -> dict:
    out = {}
    for _day, rec in exact_record_range(store, start_day, start_rid, end_day, end_rid):
        try:
            amt = financial_view_amount(store, rec)
        except Exception:
            continue
        if amt >= 0:
            continue
        category = resolve_expense_category(financial_view_note(store, rec), store)
        try:
            override_slug = str((rec or {}).get('category_override_slug') or '').strip()
            if override_slug:
                category = get_category_by_slug(override_slug, store) or category
        except Exception:
            pass
        if not category:
            continue
        out[category] = out.get(category, 0) + -amt
    return out

def collect_items_for_category_record_range(store: dict, start_day: str, start_rid: int, end_day: str, end_rid: int, category: str):
    items = []
    for day_key, rec in exact_record_range(store, start_day, start_rid, end_day, end_rid):
        try:
            amt = financial_view_amount(store, rec)
        except Exception:
            continue
        if amt >= 0:
            continue
        note = financial_view_note(store, rec)
        resolved = resolve_expense_category(note, store)
        try:
            override_slug = str((rec or {}).get('category_override_slug') or '').strip()
            if override_slug:
                resolved = get_category_by_slug(override_slug, store) or resolved
        except Exception:
            pass
        if resolved == category:
            items.append((day_key, -amt, note))
    return items

def _v207_exact_ars_rows(store: dict, start_day: str, start_rid: int, end_day: str, end_rid: int):
    """Canonical ARS rows inside the exact user-selected boundaries.

    The exact anchors belong to the ARS ledger.  This helper deliberately ignores the
    temporary USD presentation flag so an F110 category report can never switch ledgers
    merely because another USD window was opened before it.
    """
    start_day = str(start_day or '')[:10]
    end_day = str(end_day or start_day)[:10]
    try:
        start_rid = int(start_rid or 0)
    except Exception:
        start_rid = 0
    try:
        end_rid = int(end_rid or 0)
    except Exception:
        end_rid = 0
    if end_day < start_day:
        start_day, end_day = (end_day, start_day)
        start_rid, end_rid = (end_rid, start_rid)
    out = []
    daily = (store or {}).get('daily_records', {}) or {}
    for day_key in sorted(daily.keys()):
        if not start_day <= str(day_key) <= end_day:
            continue
        rows = [r for r in daily.get(day_key) or [] if isinstance(r, dict) and (not bool(r.get('usd_only', False)))]
        try:
            rows = sorted(rows, key=record_sort_key)
        except Exception:
            pass
        if not rows:
            continue
        lo, hi = (0, len(rows) - 1)
        if str(day_key) == start_day and start_rid:
            found = next((i for i, r in enumerate(rows) if _record_int_id(r) == start_rid), None)
            if found is not None:
                lo = int(found)
        if str(day_key) == end_day and end_rid:
            found = next((i for i, r in enumerate(rows) if _record_int_id(r) == end_rid), None)
            if found is not None:
                hi = int(found)
        if lo <= hi:
            out.extend(((str(day_key), r) for r in rows[lo:hi + 1]))
    return out

def _v207_ars_opening_fallback(store: dict, start_day: str, start_rid: int) -> float:
    total = 0.0
    target_key = None
    daily = (store or {}).get('daily_records', {}) or {}
    try:
        rows = [r for r in daily.get(str(start_day)[:10]) or [] if isinstance(r, dict) and (not bool(r.get('usd_only', False)))]
        rows = sorted(rows, key=record_sort_key)
        target = next((r for r in rows if _record_int_id(r) == int(start_rid or 0)), None)
        if target is not None:
            target_key = record_sort_key(target)
    except Exception:
        target_key = None
    for day_key in sorted(daily.keys()):
        if str(day_key) > str(start_day)[:10]:
            break
        rows = [r for r in daily.get(day_key) or [] if isinstance(r, dict) and (not bool(r.get('usd_only', False)))]
        try:
            rows = sorted(rows, key=record_sort_key)
        except Exception:
            pass
        for rec in rows:
            if str(day_key) < str(start_day)[:10]:
                try:
                    total += float(rec.get('amount', 0) or 0)
                except Exception:
                    pass
                continue
            if not int(start_rid or 0):
                return float(total)
            try:
                if target_key is not None and record_sort_key(rec) >= target_key:
                    return float(total)
                if target_key is None and _record_int_id(rec) >= int(start_rid):
                    return float(total)
                total += float(rec.get('amount', 0) or 0)
            except Exception:
                pass
        if str(day_key) == str(start_day)[:10]:
            break
    return float(total)

def _v207_report_date(value: str) -> str:
    try:
        return datetime.strptime(str(value)[:10], '%Y-%m-%d').strftime('%d.%m.%y')
    except Exception:
        return str(value or '')[:10]

def _v207_report_num(value) -> str:
    try:
        return fmt_num_plain(float(value or 0))
    except Exception:
        return '0'

def _v207_usd_equivalent(value, rate: float) -> str:
    try:
        if float(rate or 0) <= 0:
            return '$—'
        return f'${_v207_report_num(float(value or 0) / float(rate))}'
    except Exception:
        return '$—'

def _v207_usd_range_rows(chat_id: int | None, store: dict, start_day: str, end_day: str):
    if chat_id:
        fn = globals().get('_excel_canonical_records_for_range')
        if callable(fn):
            try:
                return list(fn(int(chat_id), 'usd', str(start_day)[:10], str(end_day)[:10]) or [])
            except Exception:
                pass
        fn = globals().get('_v151_all_records')
        day_fn = globals().get('_v151_day_key')
        if callable(fn) and callable(day_fn):
            try:
                return [r for r in fn(int(chat_id), 'usd') or [] if str(start_day)[:10] <= str(day_fn(r) or '') <= str(end_day)[:10]]
            except Exception:
                pass
    out = []
    for day_key, rows in ((store or {}).get('daily_records', {}) or {}).items():
        if not str(start_day)[:10] <= str(day_key) <= str(end_day)[:10]:
            continue
        for rec in rows or []:
            if not isinstance(rec, dict):
                continue
            try:
                amount = float(rec.get('usd_amount', 0) or 0)
            except Exception:
                amount = 0.0
            if abs(amount) <= 1e-12:
                continue
            out.append({**rec, '_v151_amount': amount, '_v151_note': str(rec.get('usd_note') or rec.get('note') or '')})
    try:
        return sorted(out, key=record_sort_key)
    except Exception:
        return out

def summarize_categories_record_range(store: dict, start_day: str, start_rid: int, end_day: str, end_rid: int):
    """F110 exact-period report: opening → income → ARS/USD expenses → closing balances."""
    ars_rows = _v207_exact_ars_rows(store, start_day, start_rid, end_day, end_rid)
    cats = {}
    ars_income = 0.0
    ars_delta = 0.0
    for _day_key, rec in ars_rows:
        try:
            amount = float((rec or {}).get('amount', 0) or 0)
        except Exception:
            amount = 0.0
        ars_delta += amount
        if amount > 0:
            ars_income += amount
            continue
        if amount >= 0:
            continue
        note = str((rec or {}).get('note') or '')
        category = resolve_expense_category(note, store)
        try:
            override_slug = str((rec or {}).get('category_override_slug') or '').strip()
            if override_slug:
                category = get_category_by_slug(override_slug, store) or category
        except Exception:
            pass
        if category:
            cats[category] = cats.get(category, 0.0) + abs(amount)
    chat_id = None
    resolver = globals().get('_excel_chat_id_for_store')
    if callable(resolver):
        try:
            chat_id = int(resolver(store) or 0) or None
        except Exception:
            chat_id = None
    opening_fn = globals().get('_excel_canonical_opening_balance')
    try:
        ars_opening = float(opening_fn(int(chat_id), 'ars', str(start_day)[:10], int(start_rid or 0), bool(start_rid)) if chat_id and callable(opening_fn) else _v207_ars_opening_fallback(store, start_day, start_rid))
    except Exception:
        ars_opening = _v207_ars_opening_fallback(store, start_day, start_rid)
    try:
        usd_opening = float(opening_fn(int(chat_id), 'usd', str(start_day)[:10], 0, False) if chat_id and callable(opening_fn) else 0.0)
    except Exception:
        usd_opening = 0.0
    usd_rows = _v207_usd_range_rows(chat_id, store, start_day, end_day)
    usd_income = 0.0
    usd_delta = 0.0
    usd_expenses = []
    for rec in usd_rows:
        try:
            amount = float((rec or {}).get('_v151_amount', (rec or {}).get('usd_amount', 0)) or 0)
        except Exception:
            amount = 0.0
        note = str((rec or {}).get('_v151_note') or (rec or {}).get('usd_note') or (rec or {}).get('note') or '').strip()
        usd_delta += amount
        if amount > 0:
            usd_income += amount
        elif amount < 0:
            usd_expenses.append((abs(amount), note))
    ars_closing = ars_opening + ars_delta
    usd_closing = usd_opening + usd_delta
    try:
        gomonk = float(gomonk_total(int(chat_id), 'usd')) if chat_id and 'gomonk_total' in globals() else 0.0
    except Exception:
        gomonk = 0.0
    usd_turnover = usd_closing - gomonk
    rate_info = None
    try:
        rate_info = usd_rate_cached()
    except Exception:
        rate_info = None
    try:
        rate = float((rate_info or {}).get('rate') or 0)
    except Exception:
        rate = 0.0
    lines = ['📦 Расходы по статьям — точный период', f'▶️ {exact_boundary_text(store, start_day, start_rid, True)}', f'⏹ {exact_boundary_text(store, end_day, end_rid, False)}', '']
    if rate_info and rate > 0:
        lines.append(f"💵 Курс: 1 USD = {fmt_num(rate).lstrip('+')} ARS ({_clean_category_display_name(rate_info.get('source') or 'DolarAPI')})")
    else:
        lines.append('💵 Курс USD временно недоступен')
    lines += ['', f'Отчёт бр с {_v207_report_date(start_day)}-{_v207_report_date(end_day)}', f'Ост: {_v207_report_num(ars_opening)}ars({_v207_usd_equivalent(ars_opening, rate)}) и {_v207_report_num(usd_opening)}usd', f'Приход: {_v207_report_num(ars_income)}ars (от ст и(или) от обмена) и {_v207_report_num(usd_income)}usd', '', 'Расход ARS:']
    if cats:
        category_mixed = bool((store or {}).setdefault('settings', {}).get('category_usd_enabled', False) and _v85_enabled('usd_categories'))
        for category in get_ordered_category_names(cats=cats, store=store):
            clean_name = _clean_category_display_name(category).upper()
            amount = float(cats.get(category, 0) or 0)
            lines.append(f'{clean_name}: {format_category_amount(store or {}, amount, category_mixed)}')
    else:
        lines.append('- нет')
    lines += ['', 'Расход USD:']
    if usd_expenses:
        for amount, note in usd_expenses:
            suffix = f' · {note}' if note else ''
            lines.append(f'- ${_v207_report_num(amount)}{suffix}'[:3900])
    else:
        lines.append('- нет')
    lines += ['', 'Остаток:', f"{_v207_report_num(ars_closing)}ars({(_v207_report_num(ars_closing / rate) + 'usd' if rate > 0 else '—usd')})", f'И {_v207_report_num(usd_closing)} usd ({_v207_report_num(gomonk)}гомонковые и в обороте {_v207_report_num(usd_turnover)} USD)']
    return (wm_common('\n'.join(lines), 7), cats)

def collect_items_for_category(store: dict, start: str, end: str, category: str):
    """Возвращает список (day, amount, note) для указанной статьи и периода."""
    items = []
    daily = store.get('daily_records', {}) or {}
    for day, records in daily.items():
        if not start <= day <= end:
            continue
        for r in records or []:
            if not financial_view_record_visible(store, r):
                continue
            amt = financial_view_amount(store, r)
            if amt >= 0:
                continue
            note = financial_view_note(store, r)
            resolved = resolve_expense_category(note, store)
            try:
                override_slug = str((r or {}).get('category_override_slug') or '').strip()
                if override_slug:
                    resolved = get_category_by_slug(override_slug, store) or resolved
            except Exception:
                pass
            if resolved == category:
                items.append((day, -amt, note))
    return items

def get_ordered_category_names(include_all: bool=False, cats: dict | None=None, store: dict | None=None):
    names = []
    seen = set()
    order = get_expense_category_order(store)
    if include_all:
        for cat in order:
            if cat not in seen:
                names.append(cat)
                seen.add(cat)
    elif cats:
        for cat in order:
            if cat in cats and cat not in seen:
                names.append(cat)
                seen.add(cat)
        for cat in sorted(cats.keys()):
            if cat not in seen:
                names.append(cat)
                seen.add(cat)
    return names

def build_articles_description_text(chat_id: int | None=None) -> str:
    """Описание статей: статья = ключевые слова. Для владельца показывает стандартные + пользовательские по выбранному чату."""
    try:
        store = get_chat_store(chat_id) if chat_id is not None else None
    except Exception:
        store = None
    lines = ['📚 Описание статей расходов', '']
    for item in _base_category_items(store):
        keys = item.get('keywords', []) or []
        clean_name = _clean_category_display_name(item.get('name') or '')
        lines.append(f"{clean_name}: {(', '.join(keys) if keys else '—')}")
    custom = _custom_category_list(store)
    if custom:
        lines.append('')
        lines.append('Пользовательские статьи:')
        for item in custom:
            clean_name = _clean_category_display_name(item.get('name') or '')
            lines.append(f"{clean_name}: {', '.join(item.get('keywords') or [])}")
    lines.append('')
    lines.append('Добавить новую статью можно в окне 📊 Статьи → ➕ Добавить статью.')
    return wm_common('\n'.join(lines), 7)

def summarize_categories(store: dict, start: str, end: str, label: str):
    """Сводка статей с тем же режимом валюты, что и основное финансовое окно."""
    cats = calc_categories_for_period(store, start, end)
    view_usd = financial_view_is_usd(store)
    mode = currency_mode_from_store(store)
    category_mixed = bool(not view_usd and mode == 'ars' and store.setdefault('settings', {}).get('category_usd_enabled', False) and _v85_enabled('usd_categories'))
    show_rate = not view_usd and (mode != 'ars' or category_mixed)
    rate_info = usd_rate_cached(force=False) if show_rate else None
    lines = ['📦 Расходы по статьям', f'🗓 {label}', '']
    if show_rate:
        if rate_info and rate_info.get('rate'):
            lines.append(f"💵 Курс: 1 USD = {fmt_num(rate_info['rate']).lstrip('+')} ARS ({_clean_category_display_name(rate_info.get('source') or 'DolarAPI')})")
        else:
            lines.append('💵 Курс USD временно недоступен')
        lines.append('')
    if not cats:
        lines.append('Нет данных по статьям за этот период.')
    else:
        for cat in get_ordered_category_names(cats=cats, store=store):
            clean_name = _clean_category_display_name(cat).upper()
            lines.append(f'{clean_name}: {format_category_view_amount(store, cats.get(cat, 0), category_mixed)}')
    lines.extend(['', '✏️ Изменить: название статьи и/или её ключевые слова.'])
    return (wm_common('\n'.join(lines), 7), cats)
# v262
