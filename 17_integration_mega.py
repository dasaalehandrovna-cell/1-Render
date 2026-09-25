# v266
"""ОЧНИСЬ 12.35 · physical owner: mega.

Этот файл — единственное физическое место тел функций домена.
Он НЕ запускается отдельно и НЕ импортируется как Python-модуль.
bot.py читает его как каталог исходников и устанавливает нужную стадию в исторической точке runtime.
Последняя версия каждого публичного символа сохраняет обычное имя; старые стадии помечены _legacy_sXXXX_.
"""

# --- mega:0001 · from 01_core_data.py:4301 · public journal_flush_to_mega ---
def journal_flush_to_mega(force: bool=False) -> bool:
    """v208: durable full diagnostic journal as batched gzip chunks; never one network call per row."""
    if restore_quiet_active_v222():
        return True
    global _JOURNAL_DURABLE_SEQ
    if not BOT_JOURNAL_DURABLE_ENABLED:
        return False
    if not journal_compact_remote_enabled():
        fn = globals().get('journal_flush_critical_to_mega')
        return bool(fn(force)) if callable(fn) else True
    if not globals().get('mega_is_configured') or not mega_is_configured():
        return False
    with _JOURNAL_DURABLE_LOCK:
        if not _JOURNAL_DURABLE_BUFFER:
            return True
        if not force and len(_JOURNAL_DURABLE_BUFFER) < BOT_JOURNAL_DURABLE_FLUSH_ROWS:
            return False
        rows = list(_JOURNAL_DURABLE_BUFFER)
        _JOURNAL_DURABLE_BUFFER.clear()
        _JOURNAL_DURABLE_SEQ += 1
        seq = _JOURNAL_DURABLE_SEQ
    tmp = None
    try:
        remote_dir = _journal_durable_remote_dir()
        mega_ensure_remote_path(remote_dir)
        os.makedirs(MEGA_LOCAL_TMP_DIR, exist_ok=True)
        stamp = now_local().strftime('%Y%m%d_%H%M%S_%f') if 'now_local' in globals() else datetime.now().strftime('%Y%m%d_%H%M%S_%f')
        inst = mega_safe_name(str(os.getenv('RENDER_INSTANCE_ID', 'local') or 'local')[-18:], 'instance')
        name = f'journal_{stamp}_{inst}_{seq:06d}.json.gz'
        tmp = os.path.join(MEGA_LOCAL_TMP_DIR, name)
        payload = {'kind': 'telegram_bot_journal_chunk', 'schema_version': 3, 'compression': 'gzip', 'bot_version': globals().get('VERSION', ''), 'created_at': _journal_ts(), 'render_instance_id': str(os.getenv('RENDER_INSTANCE_ID', '') or ''), 'render_git_commit': str(os.getenv('RENDER_GIT_COMMIT', '') or ''), 'row_count': len(rows), 'rows': rows}
        raw_bytes, packed_bytes = _journal_write_gzip_payload(tmp, payload)
        _mega_run('mega-put', [tmp, remote_dir], check=True, timeout=MEGA_TIMEOUT)
        _JOURNAL_DURABLE_STATS['uploaded_chunks'] += 1
        _JOURNAL_DURABLE_STATS['uploaded_rows'] += len(rows)
        _JOURNAL_DURABLE_STATS['uploaded_payload_bytes'] += int(packed_bytes)
        _JOURNAL_DURABLE_STATS['raw_estimated_bytes'] += int(raw_bytes)
        _JOURNAL_DURABLE_STATS['last_upload_at'] = _journal_ts()
        _JOURNAL_DURABLE_STATS['last_upload_file'] = name
        _JOURNAL_DURABLE_STATS['last_error'] = ''
        if _JOURNAL_DURABLE_STATS['uploaded_chunks'] % 50 == 0:
            try:
                _mega_prune_remote_history(remote_dir, 'journal_*.json.gz', BOT_JOURNAL_DURABLE_REMOTE_KEEP)
            except Exception:
                pass
        return True
    except Exception as e:
        _JOURNAL_DURABLE_STATS['upload_errors'] += 1
        _JOURNAL_DURABLE_STATS['last_error'] = str(e)[:500]
        with _JOURNAL_DURABLE_LOCK:
            _JOURNAL_DURABLE_BUFFER[0:0] = rows
            if len(_JOURNAL_DURABLE_BUFFER) > 5000:
                del _JOURNAL_DURABLE_BUFFER[:-5000]
        return False
    finally:
        try:
            if tmp and os.path.exists(tmp):
                os.remove(tmp)
        except Exception:
            pass

# --- mega:0002 · from 01_core_data.py:4362 · public journal_flush_critical_to_mega ---
def journal_flush_critical_to_mega(force: bool=False) -> bool:
    """Persist only ERROR/CRITICAL/lifecycle rows when routine MEGA journal is disabled."""
    if restore_quiet_active_v222():
        return True
    if not BOT_CRITICAL_JOURNAL_DURABLE_ENABLED or not mega_is_configured():
        return True
    rows = []
    try:
        with _JOURNAL_DURABLE_LOCK:
            rows = [dict(r) for r in _JOURNAL_DURABLE_BUFFER if bool((r or {}).get('critical_remote'))]
        if not rows:
            return True
        remote_dir = _journal_durable_remote_dir()
        mega_ensure_remote_path(remote_dir)
        global _JOURNAL_DURABLE_SEQ
        with _JOURNAL_DURABLE_LOCK:
            _JOURNAL_DURABLE_SEQ += 1
            seq = _JOURNAL_DURABLE_SEQ
        stamp = now_local().strftime('%Y%m%d_%H%M%S_%f')
        inst = mega_safe_name(_runtime_instance_id() if '_runtime_instance_id' in globals() else str(os.getpid()), 'instance')
        name = f'journal_critical_{stamp}_{inst}_{seq:06d}.json.gz'
        tmp = os.path.join(MEGA_LOCAL_TMP_DIR, name)
        critical_rows = rows[-100:]
        try:
            with bot_journal_lock:
                recent_context = [dict(r) for r in list(BOT_ACTION_LOG)[-60:]]
        except Exception:
            recent_context = []
        try:
            with globals().get('_RUNTIME_LOCK', threading.RLock()):
                runtime_context = [dict(r) for r in list(globals().get('_RUNTIME_EVENTS') or [])[-30:]]
                runtime_state = dict(globals().get('_RUNTIME_STATE') or {})
        except Exception:
            runtime_context = []
            runtime_state = {}
        payload = {'kind': 'telegram_bot_critical_journal_chunk', 'schema_version': 2, 'bot_version': globals().get('VERSION', ''), 'created_at': _journal_ts(), 'render_instance_id': str(os.getenv('RENDER_INSTANCE_ID', '') or ''), 'render_git_commit': str(os.getenv('RENDER_GIT_COMMIT', '') or ''), 'rows': critical_rows, 'recent_journal_context': recent_context, 'runtime_events': runtime_context, 'runtime_state': {k: runtime_state.get(k) for k in ('phase', 'ready', 'last_event', 'last_event_at', 'last_error', 'started_at', 'last_webhook_at', 'shutdown_started_at', 'shutdown_finished_at', 'shutdown_signal', 'fatal_main_exception', 'fatal_thread_exception')}}
        _raw_bytes, _packed_bytes = _journal_write_gzip_payload(tmp, payload)
        _mega_run('mega-put', [tmp, remote_dir], check=True, timeout=MEGA_TIMEOUT)
        keys = {_journal_row_key(r) for r in rows}
        with _JOURNAL_DURABLE_LOCK:
            _JOURNAL_DURABLE_BUFFER[:] = [r for r in _JOURNAL_DURABLE_BUFFER if _journal_row_key(r) not in keys]
        _JOURNAL_DURABLE_STATS['uploaded_chunks'] += 1
        _JOURNAL_DURABLE_STATS['uploaded_rows'] += len(critical_rows)
        _JOURNAL_DURABLE_STATS['uploaded_payload_bytes'] += int(_packed_bytes)
        _JOURNAL_DURABLE_STATS['raw_estimated_bytes'] += int(_raw_bytes)
        _JOURNAL_DURABLE_STATS['last_upload_at'] = _journal_ts()
        _JOURNAL_DURABLE_STATS['last_upload_file'] = name
        if _JOURNAL_DURABLE_STATS['uploaded_chunks'] % 25 == 0:
            try:
                _mega_prune_remote_history(remote_dir, 'journal_critical_*.json.gz', 400)
            except Exception:
                pass
        return True
    except Exception as exc:
        _JOURNAL_DURABLE_STATS['upload_errors'] += 1
        _JOURNAL_DURABLE_STATS['last_error'] = str(exc)[:700]
        return False
    finally:
        try:
            if 'tmp' in locals() and os.path.exists(tmp):
                os.remove(tmp)
        except Exception:
            pass

# --- mega:0003 · from 01_core_data.py:4450 · public _journal_read_mega_rows ---
def _journal_read_mega_rows(limit: int=20000) -> list[dict]:
    """Читает последние durable journal chunks из MEGA, newest-first files -> chronological rows."""
    if not BOT_JOURNAL_DURABLE_ENABLED or not globals().get('mega_is_configured') or (not mega_is_configured()):
        return []
    remote_dir = _journal_durable_remote_dir()
    try:
        estimated_files = max(3, int(max(1, int(limit)) / max(1, BOT_JOURNAL_DURABLE_FLUSH_ROWS)) + 3)
        files = _mega_find_remote_files(remote_dir, 'journal_*', min(BOT_JOURNAL_DURABLE_RESTORE_FILES, estimated_files))
    except Exception:
        return []
    chunks = []
    total = 0
    for remote in files:
        local = None
        try:
            local = _mega_download_remote_path(remote)
            rows = _journal_load_chunk_rows(local) if local else []
            if rows:
                chunks.append(rows)
                total += len(rows)
                if total >= int(limit):
                    break
        except Exception:
            continue
        finally:
            try:
                if local:
                    shutil.rmtree(os.path.dirname(local), ignore_errors=True)
            except Exception:
                pass
    merged = []
    for rows in reversed(chunks):
        merged.extend(rows)
    return _journal_merge_rows(merged, limit=limit)

# --- mega:0004 · from 01_core_data.py:4485 · public journal_restore_from_mega ---
def journal_restore_from_mega(limit: int=200) -> dict:
    """BOOT: restores only a small recent tail. Full history stays in MEGA and is streamed on export."""
    remote_rows = _journal_read_mega_rows(limit)
    local_rows = _journal_read_file_rows(limit)
    merged = _journal_merge_rows(remote_rows, local_rows, limit=limit)
    if remote_rows:
        try:
            with bot_journal_lock:
                BOT_ACTION_LOG.clear()
                BOT_ACTION_LOG.extend(merged[-BOT_JOURNAL_MAX:])
            with open(BOT_JOURNAL_FILE, 'w', encoding='utf-8') as f:
                for row in merged:
                    f.write(json.dumps(row, ensure_ascii=False) + '\n')
        except Exception as e:
            _JOURNAL_DURABLE_STATS['last_error'] = str(e)[:500]
    _JOURNAL_DURABLE_STATS['restored_rows'] = len(remote_rows)
    _JOURNAL_DURABLE_STATS['restored_chunks'] = 0 if not remote_rows else 1
    return {'remote_rows': len(remote_rows), 'merged_rows': len(merged)}

# --- mega:0005 · from 01_core_data.py:4608 · public _journal_stream_mega_rows_to_file ---
def _journal_stream_mega_rows_to_file(fh, limit: int=3000, bot_version_filter: str | None=None, since_ts: str | None=None) -> int:
    """Stream durable journal chunks without loading the whole history into RAM.

    bot_version_filter is exact for v124+ rows. since_ts is a compatibility fallback for
    older rows that did not yet carry bot_version. Existing full-journal callers use no filter.
    """
    if not BOT_JOURNAL_DURABLE_ENABLED or not mega_is_configured():
        return 0
    remote_dir = _journal_durable_remote_dir()
    max_files = min(BOT_JOURNAL_DURABLE_RESTORE_FILES, max(8, int(max(1, limit) / max(1, BOT_JOURNAL_DURABLE_FLUSH_ROWS)) + 16))
    try:
        files = _mega_find_remote_files(remote_dir, 'journal_*', max_files)
    except Exception:
        return 0
    count = 0
    seen = set()
    wanted_version = str(bot_version_filter or '').strip()
    since_ts = str(since_ts or '').strip()
    for remote in reversed(files):
        local = None
        try:
            local = _mega_download_remote_path(remote)
            rows = _journal_load_chunk_rows(local) if local else []
            if not rows:
                continue
            for r in rows:
                if not isinstance(r, dict):
                    continue
                if wanted_version:
                    row_version = str(r.get('bot_version') or '').strip()
                    if row_version:
                        if row_version != wanted_version:
                            continue
                    elif since_ts and str(r.get('ts') or '') < since_ts:
                        continue
                key = _journal_row_key(r)
                if key in seen:
                    continue
                seen.add(key)
                _journal_write_export_row(fh, r)
                count += 1
                if count >= int(limit):
                    return count
        except Exception as e:
            fh.write(f'[journal chunk read error] {remote}: {e}\n')
        finally:
            try:
                if local:
                    shutil.rmtree(os.path.dirname(local), ignore_errors=True)
            except Exception:
                pass
    return count

# --- mega:0006 · from 01_core_data.py:5143 · public archive_current_bot_source_to_mega ---
def archive_current_bot_source_to_mega() -> bool:
    """One immutable name per VERSION+commit, so the running source survives later deploys."""
    if not mega_is_configured():
        return False
    path = _current_source_path()
    if not os.path.exists(path):
        return False
    commit = re.sub('[^0-9A-Za-z]+', '', str(os.getenv('RENDER_GIT_COMMIT', '') or ''))[:16] or 'no_commit'
    safe_ver = re.sub('[^0-9A-Za-z_\\-]+', '_', str(VERSION))[:90]
    remote_name = f'{safe_ver}__{commit}.py'
    ok = mega_put_replace(path, BOT_SOURCE_ARCHIVE_DIR, remote_name, archive_previous=False)
    try:
        bot_journal('bot_source_archive', None, f'ok={ok} file={remote_name}')
    except Exception:
        pass
    return bool(ok)

# --- mega:0007 · from 01_core_data.py:6707 · public mega_backup_priority_enabled ---
def mega_backup_priority_enabled(chat_id: int | None=None) -> bool:
    """Приоритет MEGA — настройка owner scope; без контекста сохраняется legacy fallback."""
    return bool(_owner_setting_value('mega_backup_priority', False, chat_id))

# --- mega:0008 · from 01_core_data.py:6711 · public set_mega_backup_priority_enabled ---
def set_mega_backup_priority_enabled(enabled: bool, chat_id: int | None=None):
    _set_owner_setting_value('mega_backup_priority', bool(enabled), chat_id)
    if mega_is_configured():
        _schedule_global_mega_snapshot(1.0)

# --- mega:0009 · from 01_core_data.py:6716 · public toggle_mega_backup_priority ---
def toggle_mega_backup_priority(chat_id: int | None=None) -> bool:
    new_value = not mega_backup_priority_enabled(chat_id)
    set_mega_backup_priority_enabled(new_value, chat_id)
    return new_value

# --- mega:0010 · from 01_core_data.py:6721 · public mega_backup_priority_label ---
def mega_backup_priority_label(chat_id: int | None=None) -> str:
    return '☁️ Сразу в MEGA' if mega_backup_priority_enabled(chat_id) else '🕓 MEGA как обычно'

# --- mega:0011 · from 01_core_data.py:6997 · public is_backup_to_mega_enabled ---
def is_backup_to_mega_enabled(chat_id: int) -> bool:
    return is_backup_target_enabled(chat_id, 'mega')

# --- mega:0012 · from 01_core_data.py:10108 · public mega_is_configured ---
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
    # OCH12.22: MEGA_ENABLED controls normal/background runtime only.
    # Explicit control-plane recovery is allowed whenever credentials/root exist.
    enabled_for_call = True if control_plane else bool(MEGA_ENABLED)
    return bool(enabled_for_call and MEGA_EMAIL and MEGA_PASSWORD and str(MEGA_BACKUP_DIR or '').strip('/'))

# --- mega:0013 · from 01_core_data.py:10131 · public mega_remote_file_path ---
def mega_remote_file_path(filename: str=None) -> str:
    filename = filename or MEGA_LATEST_GLOBAL_NAME
    return MEGA_BACKUP_DIR.rstrip('/') + '/' + filename

# --- mega:0014 · from 01_core_data.py:10135 · public _mega_required_commands ---
def _mega_required_commands():
    return ['mega-login', 'mega-whoami', 'mega-mkdir', 'mega-put', 'mega-get', 'mega-rm', 'mega-mv', 'mega-find']

# --- mega:0015 · from 01_core_data.py:10138 · public mega_missing_commands ---
def mega_missing_commands():
    return [cmd for cmd in _mega_required_commands() if shutil.which(cmd) is None]

# --- mega:0016 · from 01_core_data.py:10141 · public _mega_memory_safe_args ---
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

# --- mega:0017 · from 01_core_data.py:10165 · public _mega_traffic_category ---
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

# --- mega:0018 · from 01_core_data.py:10189 · public _mega_traffic_record_put ---
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

# --- mega:0019 · from 01_core_data.py:10207 · public _mega_traffic_download_size ---
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

# --- mega:0020 · from 01_core_data.py:10223 · public mega_traffic_stats ---
def mega_traffic_stats() -> dict:
    with _MEGA_TRAFFIC_LOCK:
        out = {'started_at': _MEGA_TRAFFIC_STARTED_AT, 'put_bytes': int(_MEGA_TRAFFIC_STATS.get('put_bytes', 0) or 0), 'put_count': int(_MEGA_TRAFFIC_STATS.get('put_count', 0) or 0), 'by_category': {k: dict(v) for k, v in (_MEGA_TRAFFIC_STATS.get('by_category') or {}).items()}}
    return out

# --- mega:0021 · from 01_core_data.py:10228 · public mega_traffic_stats_text ---
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

# --- mega:0022 · from 01_core_data.py:10240 · public _v178_mega_priority ---
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

# --- mega:0023 · from 01_core_data.py:10254 · public _v178_mega_gate_enter ---
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

# --- mega:0024 · from 01_core_data.py:10266 · public _v178_mega_gate_exit ---
def _v178_mega_gate_exit() -> None:
    global _V178_MEGA_PRIORITY_ACTIVE
    with _V178_MEGA_PRIORITY_CV:
        _V178_MEGA_PRIORITY_ACTIVE = False
        _V178_MEGA_PRIORITY_CV.notify_all()

# --- mega:0025 · from 01_core_data.py:10272 · public _mega_exec_raw ---
def _mega_exec_raw(cmd: str, args=None, timeout: int | None=None, check: bool=True, control_plane: bool=False):
    """One MEGAcmd command at a time; canonical 12.26 durability uses control-plane access.

    MEGA_ENABLED remains OFF for legacy/background writers.  The one canonical
    generation/tail transaction temporarily raises _V240_RECOVERY_AUTHORITY_ACTIVE,
    which is treated exactly like an explicit control-plane call here.
    """
    control_plane = bool(control_plane or globals().get('_V240_RECOVERY_AUTHORITY_ACTIVE', False))
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

# --- mega:0026 · from 01_core_data.py:10378 · public traffic_audit_checkpoint_to_mega ---
def traffic_audit_checkpoint_to_mega(reason: str='periodic') -> bool:
    if restore_quiet_active_v222():
        return True
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

# --- mega:0027 · from 01_core_data.py:10424 · public traffic_audit_restore_from_mega ---
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

# --- mega:0028 · from 01_core_data.py:10476 · public _v190_invalidate_mega_path_cache ---
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

# --- mega:0029 · from 01_core_data.py:10556 · public mega_login_if_needed ---
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

# --- mega:0030 · from 01_core_data.py:10596 · public _v178_mega_ensure_cached_path ---
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

# --- mega:0031 · from 01_core_data.py:10617 · public mega_ensure_remote_dir ---
def mega_ensure_remote_dir(force: bool=False) -> bool:
    return _v178_mega_ensure_cached_path(MEGA_BACKUP_DIR, force=force)

# --- mega:0032 · from 01_core_data.py:10620 · public mega_ensure_remote_path ---
def mega_ensure_remote_path(remote_dir: str, force: bool=False) -> bool:
    """Create a path cheaply; force=True ignores stale runtime cache."""
    return _v178_mega_ensure_cached_path(remote_dir, force=force)

# --- mega:0033 · from 01_core_data.py:10624 · public mega_safe_name ---
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

# --- mega:0034 · from 01_core_data.py:10637 · public mega_chat_slug ---
def mega_chat_slug(chat_id: int) -> str:
    try:
        name = get_chat_display_name(chat_id)
    except Exception:
        name = f'chat_{chat_id}'
    safe = mega_safe_name(name, f'chat_{chat_id}')
    return f'{safe}_{chat_id}'

# --- mega:0035 · from 01_core_data.py:10645 · public mega_remote_chat_dir ---
def mega_remote_chat_dir(chat_id: int) -> str:
    return f"{MEGA_BACKUP_DIR.rstrip('/')}/{MEGA_CHAT_BACKUP_DIR}/{mega_chat_slug(chat_id)}"

# --- mega:0036 · from 01_core_data.py:10648 · public mega_remote_month_dir ---
def mega_remote_month_dir(month_key: str) -> str:
    return f"{MEGA_BACKUP_DIR.rstrip('/')}/{MEGA_MONTHLY_BACKUP_DIR}/{month_key}"

# --- mega:0037 · from 01_core_data.py:10651 · public _copy_file_for_mega ---
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

# --- mega:0038 · from 01_core_data.py:10665 · public _mega_remote_missing_error ---
def _mega_remote_missing_error(raw: str) -> bool:
    txt = str(raw or '').casefold()
    return any((x in txt for x in ("couldn't find", 'not found', 'no such file', 'does not exist')))

# --- mega:0039 · from 01_core_data.py:10669 · public _mega_find_remote_files ---
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

# --- mega:0040 · from 01_core_data.py:10681 · public _mega_prune_remote_history ---
def _mega_prune_remote_history(remote_dir: str, pattern: str, keep: int) -> int:
    """12.26: database backup history is append-only; legacy non-database paths may prune."""
    if str(os.getenv('OCH1226_MEGA_NO_DELETE', '1') or '1').strip().lower() in {'1','true','yes','on'} and '/database/' in ('/' + str(remote_dir or '').strip('/') + '/'):
        return 0
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

# --- mega:0041 · from 01_core_data.py:10696 · public _mega_prune_remote_history_bounded ---
def _mega_prune_remote_history_bounded(remote_dir: str, pattern: str, keep: int, max_remove: int=50) -> int:
    """12.26: never delete canonical database history; legacy diagnostic paths stay bounded."""
    if str(os.getenv('OCH1226_MEGA_NO_DELETE', '1') or '1').strip().lower() in {'1','true','yes','on'} and '/database/' in ('/' + str(remote_dir or '').strip('/') + '/'):
        return 0
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

# --- mega:0042 · from 01_core_data.py:10711 · public mega_diagnostic_node_housekeeping ---
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

# --- mega:0043 · from 01_core_data.py:10737 · public _mega_promote_remote_candidate ---
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
            _no_delete = str(os.getenv('OCH1226_MEGA_NO_DELETE', '1') or '1').strip().lower() in {'1','true','yes','on'}
            _canonical_db = '/database/' in ('/' + str(remote_final or '').strip('/') + '/')
            if _no_delete and _canonical_db:
                try:
                    _history = final_parent.rstrip('/') + '/history'
                    mega_ensure_remote_path(_history)
                    moved = _mega_run('mega-mv', [remote_old_temp, _history], check=False, timeout=60)
                    if moved.returncode != 0:
                        log_error(f'[MEGA PROMOTE] 12.26 history move deferred for {remote_old_temp}')
                except Exception as e:
                    log_error(f'[MEGA PROMOTE] 12.26 history move deferred: {e}')
            else:
                _mega_run('mega-rm', [remote_old_temp], check=False, timeout=30)
    return True

# --- mega:0044 · from 01_core_data.py:10813 · public mega_put_replace ---
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
            try:
                if str(os.getenv('OCH1226_MEGA_NO_DELETE', '1') or '1').strip().lower() in {'1','true','yes','on'} and '/database/' in ('/' + str(remote_file).strip('/') + '/'):
                    failed_dir = remote_dir.rstrip('/') + '/failed'
                    mega_ensure_remote_path(failed_dir)
                    _mega_run('mega-mv', [remote_candidate, failed_dir], check=False, timeout=60)
            except Exception:
                pass
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

# --- mega:0045 · from 01_core_data.py:10889 · public _canon_mega_tasks_active__001 ---
def _canon_mega_tasks_active__001() -> bool:
    return bool(MEGA_TASKS_ENABLED and mega_is_configured() and (not RESTORE_GUARD_ACTIVE))

# --- mega:0046 · from 01_core_data.py:10892 · public mega_task_remote_root ---
def mega_task_remote_root() -> str:
    return f"{MEGA_BACKUP_DIR.rstrip('/')}/{MEGA_TASK_BACKUP_DIR}"

# --- mega:0047 · from 01_core_data.py:10895 · public ensure_mega_task_dirs ---
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

# --- mega:0048 · from 01_core_data.py:10913 · public mega_task_remote_dir ---
def mega_task_remote_dir(state: str) -> str:
    state = str(state or 'pending').strip().lower()
    if state not in {'pending', 'running', 'done', 'failed'}:
        state = 'pending'
    return f"{mega_task_remote_root().rstrip('/')}/{state}"

# --- mega:0049 · from 01_core_data.py:10919 · public _mega_task_id ---
def _mega_task_id(update_id) -> str:
    try:
        return str(int(update_id))
    except Exception:
        raw = str(update_id or '')
        return hashlib.sha256(raw.encode('utf-8', errors='ignore')).hexdigest()[:24]

# --- mega:0050 · from 01_core_data.py:10926 · public mega_task_filename ---
def mega_task_filename(update_id) -> str:
    return f'task_{_mega_task_id(update_id)}.json'

# --- mega:0051 · from 01_core_data.py:10929 · public mega_task_remote_path ---
def mega_task_remote_path(update_id, state: str) -> str:
    return f"{mega_task_remote_dir(state).rstrip('/')}/{mega_task_filename(update_id)}"

# --- mega:0052 · from 01_core_data.py:10932 · public _mega_task_update_registry ---
def _mega_task_update_registry(update_id, state: str, path: str | None=None):
    key = _mega_task_id(update_id)
    with _MEGA_TASK_LOCK:
        _mega_task_registry[key] = {'state': str(state), 'path': path or mega_task_remote_path(key, state), 'loaded_at': now_local().isoformat(timespec='seconds')}

# --- mega:0053 · from 01_core_data.py:10937 · public _canon_mega_task_known_state__001 ---
def _canon_mega_task_known_state__001(update_id) -> str:
    key = _mega_task_id(update_id)
    with _MEGA_TASK_LOCK:
        return str((_mega_task_registry.get(key) or {}).get('state') or '')

# --- mega:0054 · from 01_core_data.py:10942 · public _v177_legacy_0064_mega_task_registry_stats ---
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

# --- mega:0055 · from 01_core_data.py:12338 · public _build_mega_task_payload ---
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

# --- mega:0056 · from 01_core_data.py:12356 · public restore_mega_task_context ---
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

# --- mega:0057 · from 01_core_data.py:12385 · public _canon_mega_task_upload_new_pending__001 ---
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

# --- mega:0058 · from 01_core_data.py:12445 · public _canon_mega_task_move__001 ---
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

# --- mega:0059 · from 01_core_data.py:12478 · public _canon_mega_task_begin__001 ---
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

# --- mega:0060 · from 01_core_data.py:12517 · public _canon_mega_task_prune_done_async__001 ---
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

# --- mega:0061 · from 01_core_data.py:12532 · public _v177_legacy_0071_mega_task_finish ---
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

# --- mega:0062 · from 01_core_data.py:12580 · public _canon_mega_task_refresh_registry__001 ---
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

# --- mega:0063 · from 01_core_data.py:12633 · public _mega_task_effect_exists ---
def _mega_task_effect_exists(payload: dict, expected_effects: dict | None=None) -> bool:
    """True only if every explicitly expected effect is already proven."""
    try:
        report = _durable_effect_report(payload, expected_effects if isinstance(expected_effects, dict) else None)
        return bool(report.get('complete'))
    except Exception:
        return False

# --- mega:0064 · from 01_core_data.py:12783 · public _mega_task_recover_one ---
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

# --- mega:0065 · from 01_core_data.py:12857 · public _canon_schedule_mega_task_recovery__001 ---
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

# --- mega:0066 · from 01_core_data.py:13014 · public mega_task_requeue_failed ---
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

# --- mega:0067 · from 01_core_data.py:13282 · public _canon_mega_upload_chat_backup_bundle__001 ---
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

# --- mega:0068 · from 01_core_data.py:13307 · public _canon_mega_upload_chat_latest_json_only__001 ---
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

# --- mega:0069 · from 01_core_data.py:13375 · public mega_delta_remote_root ---
def mega_delta_remote_root() -> str:
    return f"{MEGA_BACKUP_DIR.rstrip('/')}/{MEGA_DELTA_BACKUP_DIR}"

# --- mega:0070 · from 01_core_data.py:13378 · public mega_delta_remote_day_dir ---
def mega_delta_remote_day_dir(day_key: str | None=None) -> str:
    return mega_delta_remote_root().rstrip('/') + '/' + str(day_key or today_key())

# --- mega:0071 · from 01_core_data.py:13929 · public merge_global_snapshot_with_mega_deltas ---
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

# --- mega:0072 · from 01_core_data.py:14112 · public disable_restore_guard_and_enable_mega_backups ---
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

# --- mega:0073 · from 01_core_data.py:14152 · public mega_history_remote_dir ---
def mega_history_remote_dir() -> str:
    return f"{MEGA_BACKUP_DIR.rstrip('/')}/{MEGA_HISTORY_BACKUP_DIR}"

# --- mega:0074 · from 01_core_data.py:14155 · public mega_download_global_named ---
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

# --- mega:0075 · from 01_core_data.py:14174 · public mega_download_latest_global_backup ---
def mega_download_latest_global_backup() -> str | None:
    return mega_download_global_named(MEGA_LATEST_GLOBAL_NAME)

# --- mega:0076 · from 01_core_data.py:14177 · public _mega_history_candidates ---
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

# --- mega:0077 · from 01_core_data.py:14191 · public _mega_download_remote_path ---
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

# --- mega:0078 · from 01_core_data.py:15081 · public _runtime_watcher_should_yield_to_critical_mega ---
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

# --- mega:0079 · from 01_core_data.py:15551 · public _canon_mega_upload_latest_database_backup__001 ---
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
            # R48: flush/snapshot own their locks; never hold data_lock through SQLite backup.
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

# --- mega:0080 · from 01_core_data.py:15656 · public _v177_legacy_0085_mega_restore_sqlite_snapshot_from_cloud ---
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

# --- mega:0081 · from 01_core_data.py:15935 · public mega_upload_latest_global_backup ---
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

# --- mega:0082 · from 01_core_data.py:16067 · public _mega_discover_global_candidates ---
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

# --- mega:0083 · from 01_core_data.py:16092 · public _mega_select_best_global_candidate ---
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

# --- mega:0084 · from 01_core_data.py:16127 · public _mega_select_best_global_candidate_with_retry ---
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

# --- mega:0085 · from 01_core_data.py:16145 · public _v177_legacy_0086_mega_restore_full_from_cloud ---
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

# --- mega:0086 · from 01_core_data.py:16194 · public mega_autorestore_if_needed ---
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

# --- mega:0087 · from 01_core_data.py:16205 · public mega_status_text ---
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

# --- mega:0088 · from 01_core_data.py:21812 · public mega_publish_current_sqlite_v1226 ---
def mega_publish_current_sqlite_v1226(reason: str='scheduled_generation') -> dict:
    """Low-RAM canonical MEGA generation publisher for the single FAST Render.

    The live SQLite is the persistence authority.  We flush only already-loaded chat
    objects, use SQLite's backup API, embed/verify the generation manifest, then publish
    an immutable generation and atomically advance current_manifest.  Crucially this
    does NOT perform a global full-state serialization, so backup creation never clones every chat
    and cold ledger into Python RAM.
    """
    global _V240_RECOVERY_AUTHORITY_ACTIVE
    prev = bool(globals().get('_V240_RECOVERY_AUTHORITY_ACTIVE', False))
    globals()['_V240_RECOVERY_AUTHORITY_ACTIVE'] = True
    workdir = tempfile.mkdtemp(prefix='och1226_generation_')
    try:
        if not mega_is_configured(control_plane=True):
            raise RuntimeError('MEGA canonical control plane unavailable')
        with MEGA_GLOBAL_BACKUP_LOCK:
            # Persist the global/root configuration without touching every cold chat.
            # This captures owner settings, routes, reminders/config indexes and other
            # root state while keeping finance ledgers on their existing SQLite rows.
            save_data(data, root_only=True)
            flushed = _och1226_flush_loaded_chat_stores_only()
            created_at = now_local().isoformat(timespec='microseconds')
            raw = os.path.join(workdir, 'bot_state.sqlite3')
            gz = raw + '.gz'
            SQLITE.backup_to(raw)
            embedded = _v242_embed_manifest_from_sqlite(raw, created_at, reason)
            _lowram_gzip_file(raw, gz)
            manifest = constitution_publish_sqlite_generation(raw, gz, created_at, allow_destructive=False)
            manifest = dict(manifest or {})
            _v242_verify_published_generation(manifest)
            manifest['och1226_loaded_chat_flush_rows'] = int(flushed)
            manifest['och1226_layout'] = 'current_manifest + immutable generation + database/deltas/current_tail'
            try:
                SQLITE.set_meta('mega_storage_v1226', 'last_publish', {
                    'at': created_at,
                    'reason': str(reason),
                    'generation': str(manifest.get('generation') or ''),
                    'records': int(manifest.get('total_records') or 0),
                    'flushed_loaded_rows': int(flushed),
                })
            except Exception:
                pass
            try:
                runtime_event('mega_generation_publish_v1226', f"reason={reason}; generation={manifest.get('generation')}; records={manifest.get('total_records')}; hot_flush={flushed}")
            except Exception:
                pass
            return manifest
    finally:
        globals()['_V240_RECOVERY_AUTHORITY_ACTIVE'] = bool(prev)
        shutil.rmtree(workdir, ignore_errors=True)

# --- mega:0089 · from 01_core_data.py:21865 · public mega_publish_current_sqlite_v242 ---
def mega_publish_current_sqlite_v242(reason: str='snapshot', *, manual_restore: bool=False, allow_destructive: bool=False) -> dict:
    """The single canonical full-SQLite WRITE path for v242 and future compatible code.

    Normal scheduled backups and confirmed /restore use the same capture/publish format.
    Manual restore rotates lineage and reanchors config first; ordinary snapshots do not.
    """
    if not mega_is_configured():
        raise RuntimeError('MEGA unavailable')
    previous_recovery = bool(globals().get('_V240_RECOVERY_AUTHORITY_ACTIVE', False))
    if manual_restore:
        globals()['_V240_RECOVERY_AUTHORITY_ACTIVE'] = True
    try:
        if manual_restore:
            _v239_rotate_storage_lineage('v242:' + str(reason or 'manual_restore'))
            cfg_fn = globals().get('config_guard_reanchor_after_manual_restore_v241')
            if callable(cfg_fn):
                cfg_fn('v242:' + str(reason or 'manual_restore'))
        else:
            _v239_storage_lineage(create=True)
        workdir = tempfile.mkdtemp(prefix='v242_mega_publish_')
        try:
            with MEGA_GLOBAL_BACKUP_LOCK:
                created_at = now_local().isoformat(timespec='microseconds')
                raw = os.path.join(workdir, 'bot_state.sqlite3')
                gz = raw + '.gz'
                # R48: each persistence stage owns its lock; no data_lock across disk I/O.
                flush_fn = globals().get('_lowram_flush_all_hot')
                if callable(flush_fn):
                    flush_fn(evict=False)
                save_data(data, full=True)
                SQLITE.backup_to(raw)
                embedded = _v242_embed_manifest_from_sqlite(raw, created_at, reason)
                try:
                    SQLITE.set_meta('data_constitution_snapshot', 'main', dict(embedded, snapshot_created_at=created_at, snapshot_reason_v242=str(reason)))
                    SQLITE.set_meta('db_snapshot', 'main', {'created_at': created_at, 'bot_version': VERSION, 'schema': 3, 'data_constitution': 2, 'storage_contract': 'v242_simple'})
                except Exception:
                    pass
                _lowram_gzip_file(raw, gz)
                preflight = globals().get('config_guard_snapshot_preflight_v234')
                if callable(preflight):
                    cfg_ok, cfg_detail = preflight(raw)
                    if not cfg_ok:
                        raise RuntimeError('config snapshot mismatch: ' + str(cfg_detail))
                manifest = constitution_publish_sqlite_generation(raw, gz, created_at, allow_destructive=bool(allow_destructive or manual_restore))
                active = _v242_verify_published_generation(manifest)
                try:
                    SQLITE.set_meta('mega_storage_v242', 'last_publish', {'at': created_at, 'reason': str(reason), 'generation': str(active.get('generation') or ''), 'records': int(active.get('total_records') or 0)})
                except Exception:
                    pass
                if manual_restore:
                    init_delta = globals().get('initialize_delta_baseline')
                    if callable(init_delta):
                        init_delta(data)
                    try:
                        lock = globals().get('_delta_state_lock')
                        pending = globals().get('_delta_pending_chats')
                        gens = globals().get('_delta_chat_generation')
                        if lock is not None:
                            with lock:
                                if hasattr(pending, 'clear'):
                                    pending.clear()
                                if hasattr(gens, 'clear'):
                                    gens.clear()
                        else:
                            if hasattr(pending, 'clear'):
                                pending.clear()
                            if hasattr(gens, 'clear'):
                                gens.clear()
                    except Exception:
                        pass
                try:
                    runtime_event('mega_canonical_publish_v242', f"reason={reason}; generation={active.get('generation')}; records={active.get('total_records')}")
                except Exception:
                    pass
                return active
        finally:
            shutil.rmtree(workdir, ignore_errors=True)
    finally:
        globals()['_V240_RECOVERY_AUTHORITY_ACTIVE'] = bool(previous_recovery or globals().get('_V241_RESTORE_ACTIVE', False))

# --- mega:0090 · from 01_core_data.py:21945 · public _canon_mega_upload_latest_database_backup__002 ---
def _canon_mega_upload_latest_database_backup__002(force: bool=False) -> bool:
    """v242 unified scheduled/manual full DB uploader. Deltas remain parallel and separate."""
    if not mega_is_configured():
        return False
    if not force:
        gate = globals().get('v239_external_durable_write_allowed')
        if callable(gate):
            ok, why = gate()
            if not ok:
                try:
                    _constitution_snapshot_block_notice(str(why))
                except Exception:
                    pass
                return False
        if bool(globals().get('RESTORE_GUARD_ACTIVE', False)):
            return False
        if globals().get('constitution_quarantine_active') and constitution_quarantine_active():
            return False
    try:
        mega_publish_current_sqlite_v242('forced_backup' if force else 'scheduled_backup', manual_restore=False, allow_destructive=False)
        return True
    except Exception as exc:
        try:
            runtime_event('mega_canonical_publish_failed_v242', str(exc)[:700], 'ERROR')
        except Exception:
            pass
        try:
            log_error(f'[MEGA DB SNAPSHOT ERROR v242] {exc}')
        except Exception:
            pass
        return False

# --- mega:0091 · from 02_transport_safety.py:76 · public mega_storage_control_read_v246 ---
def mega_storage_control_read_v246() -> dict | None:
    """Read the tiny mode beacon even while normal MEGA storage is disabled."""
    if not bool(MEGA_ENABLED and MEGA_EMAIL and MEGA_PASSWORD):
        return None
    work = tempfile.mkdtemp(prefix='storage_control_v246_')
    try:
        if not mega_login_if_needed(control_plane=True):
            return None
        remote = _storage_control_remote_v246()
        res = _mega_run('mega-get', [remote, work], check=False, timeout=min(60, int(MEGA_TIMEOUT)), control_plane=True)
        if int(getattr(res, 'returncode', 1)) != 0:
            return None
        candidates = list(Path(work).rglob(STORAGE_CONTROL_FILENAME_V246))
        if not candidates:
            return None
        obj = json.loads(candidates[0].read_text(encoding='utf-8'))
        if not isinstance(obj, dict) or str(obj.get('kind') or '') != STORAGE_CONTROL_KIND_V246:
            return None
        raw_mode = str(obj.get('mode') or '').strip()
        if not raw_mode:
            return None
        mode = _storage_profile_normalize_v237_1(raw_mode)
        if mode not in {STORAGE_PROFILE_LOCAL_V237_1, STORAGE_PROFILE_TELEGRAM_V237_1, STORAGE_PROFILE_MEGA_V237_1}:
            return None
        obj['mode'] = mode
        return obj
    except Exception as exc:
        try:
            bot_journal('storage_control_read_v246', int(OWNER_ID or 0) or None, str(exc)[:240], 'WARN')
        except Exception:
            pass
        return None
    finally:
        shutil.rmtree(work, ignore_errors=True)

# --- mega:0092 · from 02_transport_safety.py:111 · public mega_storage_control_write_v246 ---
def mega_storage_control_write_v246(mode: str, reason: str='switch', epoch: int | None=None) -> bool:
    """Publish one canonical MEGA mode beacon using candidate -> replace."""
    mode = _storage_profile_normalize_v237_1(mode)
    if not bool(MEGA_ENABLED and MEGA_EMAIL and MEGA_PASSWORD):
        return False
    with _STORAGE_CONTROL_REMOTE_LOCK_V246:
        if epoch is not None and int(epoch) != int(globals().get('_V241_STORAGE_EPOCH', 0) or 0):
            return False
        work = tempfile.mkdtemp(prefix='storage_control_publish_v246_')
        candidate_remote = ''
        try:
            if not mega_login_if_needed(control_plane=True):
                return False
            root = str(globals().get('MEGA_BACKUP_DIR') or '').rstrip('/')
            payload = {
                'kind': STORAGE_CONTROL_KIND_V246,
                'schema_version': STORAGE_CONTROL_SCHEMA_V246,
                'mode': mode,
                'updated_at': now_local().isoformat(timespec='microseconds'),
                'bot_version': str(globals().get('VERSION') or 'выс-264'),
                'epoch': int(globals().get('_V241_STORAGE_EPOCH', 0) or 0),
                'reason': str(reason or 'switch')[:120],
            }
            stamp = now_local().strftime('%Y%m%d_%H%M%S_%f')
            candidate_name = f'storage_control_candidate_{stamp}.json'
            local = Path(work) / candidate_name
            local.write_text(json.dumps(payload, ensure_ascii=False, separators=(',', ':')) + '\n', encoding='utf-8')
            _mega_run('mega-mkdir', [root], check=False, timeout=30, control_plane=True)
            put = _mega_run('mega-put', [str(local), root], check=False, timeout=min(60, int(MEGA_TIMEOUT)), control_plane=True)
            if int(getattr(put, 'returncode', 1)) != 0:
                return False
            candidate_remote = root + '/' + candidate_name
            final_remote = root + '/' + STORAGE_CONTROL_FILENAME_V246
            _mega_run('mega-rm', [final_remote], check=False, timeout=30, control_plane=True)
            mv = _mega_run('mega-mv', [candidate_remote, final_remote], check=False, timeout=30, control_plane=True)
            if int(getattr(mv, 'returncode', 1)) != 0:
                return False
            verify = mega_storage_control_read_v246() or {}
            return str(verify.get('mode') or '') == mode and int(verify.get('epoch') or 0) == int(payload['epoch'])
        except Exception as exc:
            try:
                bot_journal('storage_control_write_v246', int(OWNER_ID or 0) or None, str(exc)[:240], 'WARN')
            except Exception:
                pass
            return False
        finally:
            if candidate_remote:
                try:
                    _mega_run('mega-rm', [candidate_remote], check=False, timeout=20, control_plane=True)
                except Exception:
                    pass
            shutil.rmtree(work, ignore_errors=True)

# --- mega:0093 · from 02_transport_safety.py:182 · public _v246_mega_restore_evidence ---
def _v246_mega_restore_evidence() -> dict:
    """Describe the effective MEGA truth: full DB generation plus newest recoverable delta."""
    out = {'backend': 'mega', 'available': False, 'full': False, 'fresh_at': '', 'fresh_epoch': 0.0, 'richness': 2, 'detail': ''}
    if not bool(MEGA_ENABLED and MEGA_EMAIL and MEGA_PASSWORD):
        return out
    work = tempfile.mkdtemp(prefix='mega_evidence_v246_')
    try:
        if not mega_login_if_needed(control_plane=True):
            return out
        remote = (constitution_current_manifest_remote() if callable(globals().get('constitution_current_manifest_remote')) else str(globals().get('MEGA_BACKUP_DIR') or '').rstrip('/') + '/database/current_manifest.json')
        res = _mega_run('mega-get', [remote, work], check=False, timeout=min(60, int(MEGA_TIMEOUT)), control_plane=True)
        if int(getattr(res, 'returncode', 1)) != 0:
            return out
        candidates = list(Path(work).rglob('current_manifest.json'))
        if not candidates:
            candidates = list(Path(work).rglob('*.json'))
        if not candidates:
            return out
        manifest = json.loads(candidates[0].read_text(encoding='utf-8'))
        if not isinstance(manifest, dict):
            return out
        created = str(manifest.get('created_at') or manifest.get('snapshot_created_at') or '')
        full = bool(manifest.get('remote_generation') and (manifest.get('sqlite_sha256') or manifest.get('semantic_hash')))

        latest_delta_path = ''
        latest_delta_epoch = 0.0
        latest_delta_at = ''
        roots = []
        try:
            roots.append(str(mega_delta_remote_root()))
        except Exception:
            pass
        try:
            shard_root = str(globals().get('MEGA_SHARD_CHATS_ROOT_V240') or '').strip()
            if shard_root:
                roots.append(shard_root)
        except Exception:
            pass
        for root in dict.fromkeys(x for x in roots if x):
            try:
                found = _mega_run('mega-find', [root, '--pattern=delta_*.json', '--type=f'], check=False, timeout=60, control_plane=True)
                if int(getattr(found, 'returncode', 1)) != 0:
                    continue
                for row in (getattr(found, 'stdout', '') or '').splitlines():
                    path = str(row or '').strip()
                    name = os.path.basename(path)
                    m = re.search(r'delta_(\d{8})_(\d{6})_(\d{6})_', name)
                    if not m:
                        continue
                    try:
                        dt = datetime.strptime(''.join(m.groups()), '%Y%m%d%H%M%S%f').replace(tzinfo=get_tz())
                        epoch = float(dt.timestamp())
                    except Exception:
                        continue
                    if epoch > latest_delta_epoch:
                        latest_delta_epoch = epoch
                        latest_delta_path = path
                        latest_delta_at = dt.isoformat(timespec='microseconds')
            except Exception:
                pass

        snapshot_epoch = _v246_iso_epoch(created)
        if latest_delta_epoch > snapshot_epoch:
            fresh_at, fresh_epoch = latest_delta_at, latest_delta_epoch
        else:
            fresh_at, fresh_epoch = created, snapshot_epoch
        out.update({
            'available': True,
            'full': full,
            'fresh_at': fresh_at,
            'fresh_epoch': fresh_epoch,
            'detail': (
                f"generation={manifest.get('generation') or '—'}; "
                f"records={manifest.get('total_records', '—')}; "
                f"ledger={manifest.get('ledger_highwater_seq', '—')}; "
                f"latest_delta={os.path.basename(latest_delta_path) if latest_delta_path else '—'}"
            ),
        })
    except Exception as exc:
        out['detail'] = str(exc)[:240]
    finally:
        shutil.rmtree(work, ignore_errors=True)
    return out

# --- mega:0094 · from 02_transport_safety.py:357 · public mega_contour_enabled_v234 ---
def _legacy_s0094_mega_contour_enabled_v234() -> bool:
    return storage_profile_v237_1() == STORAGE_PROFILE_MEGA_V237_1

# --- mega:0095 · from 02_transport_safety.py:675 · public _storage_cancel_mega_jobs_v237_1 ---
def _storage_cancel_mega_jobs_v237_1() -> None:
    sched = globals().get('DELAYED_SCHEDULER')
    if sched is None:
        return
    for key in ('mega-delta-batch-v90', 'mega-task-startup-recovery', 'mega-task-safe-failed-repair', 'mega-global-quiet-v90', 'mega-global-max-v90', 'mega-global-retry-v90', 'mega-global-user-idle-v190', 'mega-node-housekeeping-v211', 'mega-root-reseed-v190'):
        try:
            sched.cancel(key)
        except Exception:
            pass

# --- mega:0096 · from 02_transport_safety.py:763 · public set_mega_contour_enabled_v234 ---
def set_mega_contour_enabled_v234(enabled: bool) -> bool:
    if bool(enabled):
        return set_storage_profile_v237_1(STORAGE_PROFILE_MEGA_V237_1) == STORAGE_PROFILE_MEGA_V237_1
    if storage_profile_v237_1() == STORAGE_PROFILE_MEGA_V237_1:
        set_storage_profile_v237_1(STORAGE_PROFILE_TELEGRAM_V237_1)
    return False

# --- mega:0097 · from 02_transport_safety.py:1393 · public _canon_mega_tasks_active__002 ---
def _canon_mega_tasks_active__002() -> bool:
    if telegram_durable_primary_v234():
        return not RESTORE_GUARD_ACTIVE
    return bool(_V234_MEGA_TASKS_ACTIVE()) if callable(_V234_MEGA_TASKS_ACTIVE) else False

# --- mega:0098 · from 02_transport_safety.py:1404 · public _canon_mega_task_known_state__002 ---
def _canon_mega_task_known_state__002(update_id) -> str:
    if telegram_durable_primary_v234():
        row = _tg_task_row_v234(update_id)
        return str((row or {}).get('state') or '')
    return str(_V234_MEGA_TASK_KNOWN_STATE(update_id) or '') if callable(_V234_MEGA_TASK_KNOWN_STATE) else ''

# --- mega:0099 · from 02_transport_safety.py:1419 · public _canon_mega_task_upload_new_pending__002 ---
def _canon_mega_task_upload_new_pending__002(update_id, task_payload: dict) -> bool:
    if not telegram_durable_primary_v234():
        return bool(_V234_MEGA_TASK_UPLOAD_PENDING(update_id, task_payload)) if callable(_V234_MEGA_TASK_UPLOAD_PENDING) else False
    key = _mega_task_id(update_id)
    with _TG_DURABLE_LOCK_V234:
        head = telegram_durable_bootstrap_v234(False)
        tasks = head.setdefault('tasks', {})
        existing = tasks.get(key)
        if isinstance(existing, dict) and str(existing.get('state') or '') in {'pending', 'running', 'done', 'failed'}:
            return True
        row = _delta_json_clone(task_payload or {})
        row['state'] = 'pending'
        row['created_at'] = row.get('created_at') or now_local().isoformat(timespec='microseconds')
        row['updated_at'] = now_local().isoformat(timespec='microseconds')
        row['backend'] = 'telegram'
        tasks[key] = row
        _tg_task_prune_done_v234(tasks)
        if not _tg_durable_persist_head_v234(f'task_pending:{key}'):
            tasks.pop(key, None)
            return False
    with _MEGA_TASK_LOCK:
        _mega_task_registry[key] = {'state': 'pending', 'path': f'telegram-head:{key}', 'loaded_at': now_local().isoformat(timespec='seconds')}
        _mega_task_counters['persisted'] += 1
    _TG_DURABLE_STATS_V234['task_writes'] += 1
    return True

# --- mega:0100 · from 02_transport_safety.py:1445 · public _canon_mega_task_begin__002 ---
def _canon_mega_task_begin__002(update_id, allow_existing_running: bool=False) -> bool:
    if not telegram_durable_primary_v234():
        return bool(_V234_MEGA_TASK_BEGIN(update_id, allow_existing_running=allow_existing_running)) if callable(_V234_MEGA_TASK_BEGIN) else False
    key = _mega_task_id(update_id)
    with _TG_DURABLE_LOCK_V234:
        head = telegram_durable_bootstrap_v234(False)
        tasks = head.setdefault('tasks', {})
        row = tasks.get(key)
        if not isinstance(row, dict):
            return False
        state = str(row.get('state') or '')
        if state == 'running' and allow_existing_running:
            return True
        if state != 'pending':
            return False
        row['state'] = 'running'
        row['started_at'] = now_local().isoformat(timespec='microseconds')
        row['updated_at'] = row['started_at']
        if not _tg_durable_persist_head_v234(f'task_running:{key}'):
            row['state'] = 'pending'
            return False
    with _MEGA_TASK_LOCK:
        _mega_task_registry[key] = {'state': 'running', 'path': f'telegram-head:{key}', 'loaded_at': now_local().isoformat(timespec='seconds')}
        _mega_task_processing.add(key)
    return True

# --- mega:0101 · from 02_transport_safety.py:1471 · public _canon_mega_task_finish__001 ---
def _canon_mega_task_finish__001(update_id, success: bool, error: str='') -> bool:
    if not telegram_durable_primary_v234():
        return bool(_V234_MEGA_TASK_FINISH(update_id, success, error)) if callable(_V234_MEGA_TASK_FINISH) else False
    key = _mega_task_id(update_id)
    target = 'done' if success else 'failed'
    with _TG_DURABLE_LOCK_V234:
        head = telegram_durable_bootstrap_v234(False)
        tasks = head.setdefault('tasks', {})
        row = tasks.get(key)
        if not isinstance(row, dict):
            row = {'update_id': key, 'backend': 'telegram'}
            tasks[key] = row
        row['state'] = target
        row['updated_at'] = now_local().isoformat(timespec='microseconds')
        row['error'] = str(error or '')[:1200]
        _tg_task_prune_done_v234(tasks)
        if not _tg_durable_persist_head_v234(f'task_{target}:{key}'):
            return False
    with _MEGA_TASK_LOCK:
        _mega_task_processing.discard(key)
        _mega_task_registry[key] = {'state': target, 'path': f'telegram-head:{key}', 'loaded_at': now_local().isoformat(timespec='seconds')}
        if success:
            _mega_task_counters['completed'] += 1
        else:
            _mega_task_counters['failed'] += 1
    return True

# --- mega:0102 · from 02_transport_safety.py:1498 · public _canon_mega_task_refresh_registry__002 ---
def _canon_mega_task_refresh_registry__002() -> dict:
    global _mega_task_registry_loaded_at, _mega_task_last_error
    if not telegram_durable_primary_v234():
        return _V234_MEGA_TASK_REFRESH() if callable(_V234_MEGA_TASK_REFRESH) else mega_task_registry_stats()
    try:
        head = telegram_durable_bootstrap_v234(True)
        tasks = head.get('tasks') or {}
        with _MEGA_TASK_LOCK:
            _mega_task_registry.clear()
            for key, row in tasks.items():
                if not isinstance(row, dict):
                    continue
                _mega_task_registry[str(key)] = {'state': str(row.get('state') or ''), 'path': f'telegram-head:{key}', 'loaded_at': now_local().isoformat(timespec='seconds')}
            _mega_task_registry_loaded_at = now_local().isoformat(timespec='seconds')
            _mega_task_last_error = ''
        return mega_task_registry_stats()
    except Exception as exc:
        _mega_task_last_error = str(exc)[:500]
        return mega_task_registry_stats()

# --- mega:0103 · from 02_transport_safety.py:1518 · public _canon_mega_task_registry_stats__001 ---
def _canon_mega_task_registry_stats__001() -> dict:
    if not telegram_durable_primary_v234() and callable(_V234_MEGA_TASK_STATS):
        return _V234_MEGA_TASK_STATS()
    with _MEGA_TASK_LOCK:
        states = defaultdict(int)
        for row in _mega_task_registry.values():
            states[str((row or {}).get('state') or 'unknown')] += 1
        counters = dict(_mega_task_counters)
    st = telegram_durable_status_v234() if telegram_durable_configured_v234() else {}
    return {'backend': 'telegram', 'pending': int(states.get('pending', 0)), 'running': int(states.get('running', 0)), 'done': int(states.get('done', 0)), 'failed': int(states.get('failed', 0)), 'processing': len(_mega_task_processing), 'loaded_at': globals().get('_mega_task_registry_loaded_at', ''), 'last_error': str(st.get('last_error') or globals().get('_mega_task_last_error', '')), **counters}

# --- mega:0104 · from 02_transport_safety.py:1575 · public _canon_schedule_mega_task_recovery__002 ---
def _canon_schedule_mega_task_recovery__002(delay: float | None=None):
    if not telegram_durable_primary_v234():
        return _V234_MEGA_TASK_RECOVERY(delay) if callable(_V234_MEGA_TASK_RECOVERY) else None
    if not mega_tasks_active():
        return None
    delay = max(0.1, float(delay if delay is not None else 1.0))

    def _scan():
        head = telegram_durable_bootstrap_v234(True)
        rows = [(str(k), dict(v)) for k, v in (head.get('tasks') or {}).items() if isinstance(v, dict) and str(v.get('state') or '') in {'pending', 'running'}]
        rows.sort(key=lambda kv: int(kv[0]) if kv[0].isdigit() else kv[0])
        for key, row in rows[:MEGA_TASK_RECOVERY_LIMIT]:
            pool = globals().get('RECOVERY_TASK_POOL')
            if pool is None or not pool.submit('telegram-recover-global', _tg_task_recover_one_v234, key, row):
                _tg_task_recover_one_v234(key, row)
    DELAYED_SCHEDULER.cancel('telegram-task-startup-recovery-v234')
    return DELAYED_SCHEDULER.schedule('telegram-task-startup-recovery-v234', delay, _scan)

# --- mega:0105 · from 02_transport_safety.py:1681 · public _canon_mega_task_upload_new_pending__003 ---
def _canon_mega_task_upload_new_pending__003(update_id, task_payload: dict) -> bool:
    p = storage_profile_v237_1()
    if p == STORAGE_PROFILE_TELEGRAM_V237_1 and (not storage_mode_feature_enabled_v240('telegram_durable', 'tasks')):
        return False
    if p == STORAGE_PROFILE_MEGA_V237_1 and (not storage_mode_feature_enabled_v240('mega', 'tasks')):
        return False
    return bool(_V240_TASK_UPLOAD_PENDING_ORIG(update_id, task_payload))

# --- mega:0106 · from 02_transport_safety.py:1689 · public _canon_schedule_mega_task_recovery__003 ---
def _canon_schedule_mega_task_recovery__003(delay: float | None=None):
    p = storage_profile_v237_1()
    if p == STORAGE_PROFILE_TELEGRAM_V237_1 and (not storage_mode_feature_enabled_v240('telegram_durable', 'tasks')):
        return None
    if p == STORAGE_PROFILE_MEGA_V237_1 and (not storage_mode_feature_enabled_v240('mega', 'tasks')):
        return None
    return _V240_TASK_RECOVERY_ORIG(delay)

# --- mega:0107 · from 02_transport_safety.py:2061 · public _v240_mega_business_active ---
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

# --- mega:0108 · from 02_transport_safety.py:2083 · public mega_shard_chat_dir_v240 ---
def mega_shard_chat_dir_v240(chat_id: int) -> str:
    return f'{MEGA_SHARD_CHATS_ROOT_V240}/chat_{int(chat_id)}'

# --- mega:0109 · from 02_transport_safety.py:2086 · public mega_shard_domain_dir_v240 ---
def mega_shard_domain_dir_v240(chat_id: int, domain: str) -> str:
    safe = re.sub('[^a-z0-9_-]+', '_', str(domain or 'state').casefold()).strip('_') or 'state'
    return mega_shard_chat_dir_v240(int(chat_id)).rstrip('/') + '/' + safe

# --- mega:0110 · from 02_transport_safety.py:2172 · public mega_parallel_execute_v240 ---
def mega_parallel_execute_v240(exe: str, cmd: str, args, timeout_value):
    """OCH12.26: one MEGAcmd command at a time on the 512 MB FAST instance.

    v240 used per-shard parallel subprocesses.  MEGAcmd itself owns one account/session
    daemon, so login/put/rm from different lanes can race even when the remote paths are
    unrelated.  Keep the shard metadata/layout, but serialize the actual CLI command.
    """
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
            # OCH12.26 transaction fence: MEGAcmd has a single session state.
            # Never allow LOGIN/PUT/RM/MV/GET to overlap across lanes.
            with MEGA_COMMAND_LOCK:
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

# --- mega:0111 · from 02_transport_safety.py:2214 · public mega_parallel_status_v240 ---
def mega_parallel_status_v240() -> dict:
    with _V240_PAR_STATS_LOCK:
        return {'enabled': bool(MEGA_SHARDED_STORAGE_V240), 'global_limit': int(MEGA_PARALLEL_MAX_V240), 'active': int(_V240_PAR_STATS['active']), 'peak': int(_V240_PAR_STATS['peak']), 'started': int(_V240_PAR_STATS['started']), 'completed': int(_V240_PAR_STATS['completed']), 'errors': int(_V240_PAR_STATS['errors']), 'lane_limits': dict(_V240_LANE_LIMITS), 'by_lane': {k: dict(v) for k, v in _V240_PAR_STATS['by_lane'].items()}}

# --- mega:0112 · from 02_transport_safety.py:2661 · public _canon_mega_upload_chat_backup_bundle__002 ---
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

# --- mega:0113 · from 02_transport_safety.py:2692 · public _canon_mega_upload_chat_latest_json_only__002 ---
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

# --- mega:0114 · from 02_transport_safety.py:2722 · public _canon_mega_task_upload_new_pending__004 ---
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

# --- mega:0115 · from 02_transport_safety.py:2780 · public _canon_mega_task_move__002 ---
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

# --- mega:0116 · from 02_transport_safety.py:2812 · public _canon_mega_task_refresh_registry__003 ---
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

# --- mega:0117 · from 02_transport_safety.py:2853 · public _canon_mega_task_prune_done_async__002 ---
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

# --- mega:0118 · from 06_commands_callbacks.py:4666 · public _schedule_global_mega_snapshot ---
def _schedule_global_mega_snapshot(delay: float=30.0):
    """Совместимость старых вызовов: v90 лишь отмечает pending full snapshot.

    Полный global больше не создаётся через 20–30 секунд после каждого чата.
    Его запускает общий quiet/max scheduler.
    """
    _mark_global_snapshot_pending()

# --- mega:0119 · from 06_commands_callbacks.py:5906 · public run_manual_mega_restore ---
def run_manual_mega_restore(chat_id: int):
    """OCH12.31 manual MEGA restore shares the browser's exact-file restore path.

    If the canonical current_manifest names a generation, restore that immutable file
    without current_tail.  If the manifest is missing/invalid, do not guess which of
    several generations is authoritative: open the same MEGA browser the owner already
    uses successfully and let the owner choose the exact point-in-time file.
    """
    chat_id = int(chat_id)
    work = ''
    try:
        send_and_auto_delete(chat_id, '☁️ 12.31: читаю canonical current_manifest и восстанавливаю точную generation без current_tail…', 30)
        token_fn = globals().get('_v265_mdb_token')
        restore_fn = globals().get('_v242_restore_selected_mega_database')
        paths_fn = globals().get('_r80_compact_paths')
        get_exact = globals().get('_r81_mega_get_exact')
        if not callable(token_fn) or not callable(restore_fn) or not callable(paths_fn) or not callable(get_exact):
            raise RuntimeError('единый MEGA browser/restore pipeline недоступен')
        paths = paths_fn() or {}
        manifest_remote = str(paths.get('latest') or '')
        remote = ''
        manifest_detail = ''
        work = tempfile.mkdtemp(prefix='och1231_manual_manifest_')
        if manifest_remote:
            local_manifest, manifest_detail = get_exact(manifest_remote, work, max(120, int(float(globals().get('MEGA_TIMEOUT') or 120))))
            if local_manifest and os.path.isfile(local_manifest):
                try:
                    with open(local_manifest, 'r', encoding='utf-8') as fh:
                        manifest = json.load(fh) or {}
                    remote = str(manifest.get('remote_generation') or '').strip()
                    if not remote:
                        generation = str(manifest.get('generation') or manifest.get('base_generation') or '').strip()
                        root = str(globals().get('MEGA_BACKUP_DIR') or '').rstrip('/')
                        if generation and root:
                            remote = root + '/database/generations/' + os.path.basename(generation)
                except Exception as exc:
                    manifest_detail = f'manifest decode {type(exc).__name__}: {str(exc)[:180]}'
                    remote = ''
        if not remote:
            # Missing/broken manifest is exactly the case where "newest" can be unsafe
            # (for example an EMPTY_INIT generation may be newer than the wanted DB).
            # Open the canonical browser rather than silently choosing the wrong file.
            refresh = globals().get('_v265_refresh_mega_browser')
            text_fn = globals().get('mega_database_browser_text_v242')
            kb_fn = globals().get('mega_database_browser_keyboard_v242')
            generations_dir_fn = globals().get('constitution_generations_dir')
            if callable(refresh) and callable(text_fn) and callable(kb_fn) and callable(generations_dir_fn):
                refresh(str(generations_dir_fn()), 0)
                bot.send_message(chat_id, window_mark(text_fn(0), 'Ф233'), reply_markup=kb_fn(0))
                send_and_auto_delete(chat_id, '⚠️ current_manifest не дал точную generation. Я не выбираю файл наугад: открыт список database/generations для ручного выбора.', 60)
                try:
                    bot_journal('mega_manual_restore_v1231_browser_fallback', chat_id, f'manifest={manifest_remote}; detail={manifest_detail[:240]}', 'WARN')
                except Exception:
                    pass
                return False
            raise RuntimeError('current_manifest не дал точную generation: ' + str(manifest_detail)[:300])
        token = str(token_fn(remote, 'file'))
        rep = restore_fn(token, chat_id) or {}
        if not bool(rep.get('ok')):
            raise RuntimeError('единый MEGA restore не подтвердил успех')
        try:
            refresh_registered_financial_windows(chat_id)
        except Exception:
            pass
        try:
            schedule_startup_main_windows(delay=0.5)
        except Exception:
            pass
        checkpoint_note = '✅' if rep.get('checkpoint_ok') else ('—' if rep.get('checkpoint_required') is False else '⛔')
        name = os.path.basename(remote)
        send_and_auto_delete(
            chat_id,
            f"✅ MEGA → бот восстановлен из {name}. Без current_tail. records={rep.get('source_records')} · новая canonical generation={rep.get('generation') or 'LOCAL-PENDING'} · checkpoint={checkpoint_note}",
            180,
        )
        try:
            bot_journal('mega_manual_restore_v1231', chat_id, f"source={remote}; exact_generation=1; tail=0; checkpoint_ok={int(bool(rep.get('checkpoint_ok')))}")
        except Exception:
            pass
        return True
    except Exception as exc:
        log_error(f'run_manual_mega_restore: {exc}')
        send_and_auto_delete(chat_id, '❌ Ошибка ручного восстановления из MEGA: ' + str(exc)[:500], 180)
        return False
    finally:
        if work:
            try:
                shutil.rmtree(work, ignore_errors=True)
            except Exception:
                pass

# --- mega:0120 · from 06_commands_callbacks.py:6026 · public _v243_manual_chat_mega_backup ---
def _v243_manual_chat_mega_backup(chat_id: int) -> bool:
    cid = int(chat_id)
    try:
        with state_chat_context(cid):
            save_data(data, chat_ids=[cid])
            return bool(mega_upload_chat_backup_bundle(cid, current_month_key()))
    except Exception as exc:
        try:
            log_error(f'manual chat MEGA backup v243 {cid}: {exc}')
        except Exception:
            pass
        return False

# --- mega:0121 · from 06_commands_callbacks.py:6039 · public run_manual_mega_backup_v243 ---
def run_manual_mega_backup_v243(chat_id: int):
    chat_id = int(chat_id)
    previous = bool(globals().get('_V240_RECOVERY_AUTHORITY_ACTIVE', False))
    globals()['_V240_RECOVERY_AUTHORITY_ACTIVE'] = True
    try:
        send_and_auto_delete(chat_id, '☁️ MEGA backup: фиксирую текущую SQLite как новую generation…', 30)
        publish = globals().get('mega_publish_current_sqlite_v242')
        if not callable(publish):
            raise RuntimeError('canonical MEGA publisher unavailable')
        active = publish('mega_backup_now_v243', manual_restore=False, allow_destructive=False) or {}
        generation = str(active.get('generation') or '')
        records = int(active.get('total_records') or 0)
        if not generation:
            raise RuntimeError('generation was not confirmed after upload')
        heal = globals().get('_v243_mark_runtime_restore_healthy')
        if callable(heal):
            heal('mega_backup_now_v243', remote_confirmed=True, generation=generation)
        queued = 0
        rejected = 0
        pool = globals().get('BACKUP_TASK_POOL') or globals().get('BACKGROUND_TASK_POOL')
        for cid in collect_finance_chat_ids():
            try:
                ok = bool(pool and pool.submit(f'manual-mega-chat:{int(cid)}', _v243_manual_chat_mega_backup, int(cid)))
                if ok:
                    queued += 1
                else:
                    rejected += 1
            except Exception:
                rejected += 1
        send_and_auto_delete(chat_id, f'✅ MEGA backup готов. generation={generation}; записей={records}. Чат-бэкапы параллельно: очередь={queued}, не поставлено={rejected}. Эта generation пригодна для восстановления после следующего deploy.', 120)
        try:
            bot_journal('mega_backup_now_v243', chat_id, f'generation={generation}; records={records}; queued={queued}; rejected={rejected}')
        except Exception:
            pass
    except Exception as exc:
        log_error(f'run_manual_mega_backup_v243: {exc}')
        send_and_auto_delete(chat_id, '❌ MEGA backup не создан: ' + str(exc)[:500], 120)
    finally:
        globals()['_V240_RECOVERY_AUTHORITY_ACTIVE'] = previous

# --- mega:0122 · from 07_state_web.py:538 · public _canon_mega_task_finish__002 ---
def _canon_mega_task_finish__002(update_id, success: bool, error: str='') -> bool:
    result = _V146_ORIG_MEGA_TASK_FINISH(update_id, success, error) if callable(_V146_ORIG_MEGA_TASK_FINISH) else False
    if not success:
        key = _mega_task_id(update_id)
        _V146_FAILED_TASK_RUNTIME_ERRORS[key] = {'error': str(error or '')[:500], 'at': _v146_iso_now()}
        try:
            GENERAL_TASK_POOL.submit_unique('v146-failed-task-details', refresh_failed_task_diagnostics, True)
        except Exception:
            pass
    return result

# --- mega:0123 · from 07_state_web.py:608 · public _v177_legacy_0065_mega_task_registry_stats ---
def _v177_legacy_0065_mega_task_registry_stats() -> dict:
    base = _V146_ORIG_MEGA_TASK_STATS() if callable(_V146_ORIG_MEGA_TASK_STATS) else {}
    try:
        with _MEGA_TASK_LOCK:
            current_failed = [str(key) for key, row in _mega_task_registry.items() if str((row or {}).get('state') or '') == 'failed'][:_V146_FAILED_DIAG_LIMIT]
    except Exception:
        current_failed = []
    current_set = set(current_failed)
    details = [row for row in list(_V146_FAILED_TASK_DETAILS) if str((row or {}).get('task_id') or '') in current_set]
    detail_set = {str((row or {}).get('task_id') or '') for row in details}
    mismatch = detail_set != current_set
    if mismatch:
        try:
            GENERAL_TASK_POOL.submit_unique('v147-failed-task-details', refresh_failed_task_diagnostics, True)
        except Exception:
            pass
    base['failed_details'] = details
    base['failed_task_ids'] = sorted(current_set)
    base['failed_details_at'] = _V146_FAILED_TASK_DETAILS_AT
    base['failed_details_pending'] = bool(current_set and mismatch)
    base['failed_details_summary'] = {'failed': len(current_set), 'loaded': len(details), 'pending': bool(current_set and mismatch)}
    return base

# --- mega:0124 · from 07_state_web.py:9096 · public _mega_run ---
def _mega_run(cmd: str, args=None, timeout=None, check: bool=True, control_plane: bool=False):
    if not callable(_mega_exec_raw):
        raise RuntimeError('MEGA runner unavailable')
    safe_args = list(args or [])
    temp_dir = ''
    try:
        if str(cmd or '').lower() == 'mega-put' and safe_args:
            source = str(safe_args[0] or '')
            if _v153_os.path.isfile(source):
                safe = v153_prepare_safe_file(source, 'mega upload task snapshot failed backup audit runtime')
                if safe != source:
                    safe_args[0] = safe
                    temp_dir = _v153_os.path.dirname(safe)
        return _mega_exec_raw(cmd, safe_args, timeout=timeout, check=check, control_plane=control_plane)
    except Exception as exc:
        raise RuntimeError(v153_redact_text(exc)) from None
    finally:
        if temp_dir:
            _v153_shutil.rmtree(temp_dir, ignore_errors=True)
            _V153_SANITIZED_TEMP.discard(temp_dir)

# --- mega:0125 · from 07_state_web.py:9257 · public _canon_mega_task_registry_stats__002 ---
def _canon_mega_task_registry_stats__002() -> dict:
    base = _V153_ORIG_MEGA_STATS() if callable(_V153_ORIG_MEGA_STATS) else {}
    try:
        with _MEGA_TASK_LOCK:
            failed_ids = [str(k) for k, row in _mega_task_registry.items() if str((row or {}).get('state') or '') == 'failed']
        details = [x for x in list(base.get('failed_details') or []) if str((x or {}).get('task_id') or '') in set(failed_ids)]
        base['failed'] = len(failed_ids)
        base['failed_details'] = details
        base['failed_details_pending'] = len(details) != min(len(failed_ids), int(globals().get('_V146_FAILED_DIAG_LIMIT') or 10))
    except Exception:
        pass
    return v153_sanitize(base)

# --- mega:0126 · from 07_state_web.py:9356 · public _v153_select_boot_mega_root ---
def _v153_select_boot_mega_root() -> str:
    root = str(globals().get('MEGA_CANONICAL_BACKUP_DIR_V238') or globals().get('MEGA_BACKUP_DIR') or '').rstrip('/')
    _v153_apply_mega_root(root)
    return root

# --- mega:0127 · from 07_state_web.py:9361 · public _canon_mega_restore_sqlite_snapshot_from_cloud__001 ---
def _canon_mega_restore_sqlite_snapshot_from_cloud__001(force: bool=False) -> tuple[bool, str]:
    """v241: preserve explicit owner force=True through the compatibility wrapper."""
    _v153_select_boot_mega_root()
    if callable(_V153_ORIG_RESTORE_SQLITE):
        try:
            return _V153_ORIG_RESTORE_SQLITE(force=bool(force))
        except TypeError:
            return _V153_ORIG_RESTORE_SQLITE()
    return (False, 'SQLite restore unavailable')

# --- mega:0128 · from 07_state_web.py:9371 · public _canon_mega_restore_full_from_cloud__001 ---
def _canon_mega_restore_full_from_cloud__001(force: bool=False) -> tuple[bool, str]:
    _v153_select_boot_mega_root()
    if callable(_V153_ORIG_RESTORE_FULL):
        return _V153_ORIG_RESTORE_FULL(force=force)
    return (False, 'Full restore unavailable')

# --- mega:0129 · from 07_state_web.py:9466 · public _v153_apply_mega_root ---
def _v153_apply_mega_root(root: str) -> None:
    canonical = str(globals().get('MEGA_CANONICAL_BACKUP_DIR_V238') or globals().get('MEGA_BACKUP_DIR') or '').rstrip('/')
    globals()['MEGA_BACKUP_DIR'] = canonical
    globals()['MEGA_LEGACY_BACKUP_DIR'] = canonical
    globals()['MEGA_TARGET_BACKUP_DIR'] = canonical
    globals()['BOT_SOURCE_ARCHIVE_DIR'] = f'{canonical}/runtime/bot_versions'
    try:
        globals()['DURABLE_JOURNAL_REMOTE_DIR'] = f'{canonical}/runtime/journal'
    except Exception:
        pass

# --- mega:0130 · from 07_state_web.py:9489 · public purge_legacy_mega_root_state_v238 ---
def purge_legacy_mega_root_state_v238(persist: bool=True) -> bool:
    """Remove retired root-migration payload even if an old delta/checkpoint reintroduced it."""
    changed = False
    try:
        gs = data.setdefault('_global_settings', {})
        changed = gs.pop('mega_root_migration_v153', None) is not None
        if changed and persist:
            SQLITE.save_root(_sqlite_pack_root(data))
            try:
                bot_journal('mega_root_legacy_state_purged_v238', int(OWNER_ID or 0) or None, 'mega_root_migration_v153 removed', 'INFO')
            except Exception:
                pass
    except Exception:
        return False
    return changed

# --- mega:0131 · from 07_state_web.py:9517 · public _v153_mega_copy_verify ---
def _v153_mega_copy_verify(old_remote: str, new_remote: str) -> tuple[bool, str]:
    local_old = local_new = None
    try:
        local_old = _mega_download_remote_path(old_remote)
        if not local_old:
            return (False, 'download old failed')
        old_hash = _v153_sha256_file(local_old)
        new_dir, new_name = new_remote.rsplit('/', 1)
        if not mega_put_replace(local_old, new_dir, new_name, archive_previous=False):
            return (False, 'upload new failed')
        local_new = _mega_download_remote_path(new_remote)
        if not local_new:
            return (False, 'verify download failed')
        new_hash = _v153_sha256_file(local_new)
        return (old_hash == new_hash, old_hash if old_hash == new_hash else 'checksum mismatch')
    finally:
        for local in (local_old, local_new):
            try:
                if local:
                    _v153_shutil.rmtree(_v153_os.path.dirname(local), ignore_errors=True)
            except Exception:
                pass

# --- mega:0132 · from 07_state_web.py:9540 · public v153_migrate_mega_root ---
def v153_migrate_mega_root() -> dict:
    """v179 compatibility status: root migration is permanently retired."""
    root = str(globals().get('MEGA_BACKUP_DIR') or '').rstrip('/')
    return {'status': 'disabled_v179', 'active_root': root, 'canonical_root': str(globals().get('MEGA_BACKUP_DIR') or ''), 'remaining_files': 0, 'last_error': ''}

# --- mega:0133 · from 07_state_web.py:10585 · public v153_cmd_mega_migration_status ---
def v153_cmd_mega_migration_status(msg):
    uid = _v153_actor_id(msg)
    if not _v153_platform_owner(uid):
        return
    bot.reply_to(msg, f"☁️ Хранилище MEGA\n✅ v238: один канонический корень\nАктивная папка: {globals().get('MEGA_BACKUP_DIR')}\nПодкорневые release-каталоги и legacy migration state не используются.")

# --- mega:0134 · from 07_state_web.py:11431 · public _v242_mega_database_catalog ---
def _v242_mega_database_catalog(limit: int=14) -> list[dict]:
    """List actual recoverable SQLite files in the canonical MEGA database tree."""
    if not mega_is_configured():
        return []
    rows = []
    seen = set()
    finder = globals().get('_mega_find_remote_files')
    if not callable(finder):
        return rows
    active = {}
    try:
        active = constitution_load_active_manifest_remote(force=True) or {}
    except Exception:
        active = {}
    active_remote = str(active.get('remote_generation') or '')

    def add(remote, kind):
        remote = str(remote or '').strip()
        if not remote or remote in seen:
            return
        seen.add(remote)
        name = os.path.basename(remote)
        token = hashlib.sha256(remote.encode('utf-8')).hexdigest()[:12]
        row = {'token': token, 'remote': remote, 'name': name, 'kind': kind, 'active': bool(active_remote and remote == active_remote)}
        _V242_MEGA_DB_CATALOG_CACHE[token] = row
        rows.append(row)
    try:
        for remote in finder(constitution_generations_dir(), 'generation_*.sqlite3.gz', limit=max(8, int(limit))):
            add(remote, 'generation')
    except Exception:
        pass
    try:
        for remote in finder(constitution_database_dir(), LOWRAM_DB_LATEST_NAME, limit=2):
            add(remote, 'legacy_latest')
    except Exception:
        pass
    try:
        for remote in finder(constitution_database_dir() + '/history', 'bot_state_*.sqlite3.gz', limit=6):
            add(remote, 'legacy_history')
    except Exception:
        pass
    try:
        for remote in finder(constitution_database_dir() + '/pre_restore', 'pre_restore_*.sqlite3.gz', limit=6):
            add(remote, 'pre_restore')
    except Exception:
        pass
    return rows[:max(1, int(limit))]

# --- mega:0135 · from 07_state_web.py:11479 · public _v242_mega_catalog_entry ---
def _v242_mega_catalog_entry(token: str) -> dict:
    token = str(token or '')
    row = _V242_MEGA_DB_CATALOG_CACHE.get(token)
    if row:
        return dict(row)
    _v242_mega_database_catalog(24)
    return dict(_V242_MEGA_DB_CATALOG_CACHE.get(token) or {})

# --- mega:0136 · from 07_state_web.py:11487 · public _v242_restore_selected_mega_database ---
def _v242_restore_selected_mega_database(token: str, chat_id: int) -> dict:
    """R65 exact point-in-time restore selected in the all-MEGA browser.

    FAST never logs into MEGA when MEGA_ENABLED=0.  The selected file is streamed from
    authenticated HEAVY, validated locally, then FAST seals the accepted SQLite into Redis.
    """
    browser_entry = globals().get('_v265_mdb_entry')
    row = dict(browser_entry(token) or {}) if callable(browser_entry) else {}
    if not row:
        row = _v242_mega_catalog_entry(token)
    if not row:
        raise RuntimeError('Выбранный файл больше не найден в каталоге MEGA')
    if str(row.get('kind') or '') == 'dir':
        raise RuntimeError('Для восстановления нужно выбрать файл, а не папку')
    remote = str(row.get('path') or row.get('remote') or '')
    if not remote:
        raise RuntimeError('У выбранного файла отсутствует MEGA path')
    previous = bool(globals().get('_V240_RECOVERY_AUTHORITY_ACTIVE', False))
    globals()['_V240_RECOVERY_AUTHORITY_ACTIVE'] = True
    epoch = 0
    backup_dir = ''
    success = False
    try:
        begin = globals().get('_v241_restore_storage_barrier_begin')
        if callable(begin):
            epoch = int(begin() or 0)
        backup_dir = _v153_backup_before_restore()
        work = _v153_tempfile.mkdtemp(prefix='v242_mega_selected_')
        try:
            downloaded = ''
            fetch = globals().get('_v265_heavy_download_mega_file')
            if callable(fetch):
                downloaded = str(fetch(remote, work) or '')
            elif mega_is_configured():
                res = _mega_run('mega-get', [remote, work], check=False, timeout=max(float(MEGA_TIMEOUT), 240.0))
                if res.returncode != 0:
                    raise RuntimeError('Не удалось скачать выбранную базу MEGA')
                found = [str(x) for x in Path(work).rglob('*') if x.is_file()]
                downloaded = found[0] if found else ''
            else:
                raise RuntimeError('Render #2 недоступен, а прямой MEGA на FAST отключён')
            if not downloaded or not os.path.isfile(downloaded):
                raise RuntimeError('Скачанный файл базы не найден')
            raw = os.path.join(work, 'selected.sqlite3')
            with open(downloaded, 'rb') as _r65_in:
                magic = _r65_in.read(2)
            if magic == b'\x1f\x8b':
                _lowram_gunzip_file(downloaded, raw)
            else:
                _v153_shutil.copy2(downloaded, raw)
            semantic = constitution_semantic_manifest_from_sqlite(raw) or {}
            conn = sqlite3.connect(raw)
            try:
                qc = conn.execute('PRAGMA quick_check').fetchone()
                if not qc or str(qc[0]).lower() != 'ok':
                    raise RuntimeError(f'SQLite quick_check failed: {qc}')
            finally:
                conn.close()
            SQLITE.replace_database(raw)
            restored = load_data()
            data.clear()
            data.update(restored)
            try:
                tenant_v148_bootstrap()
            except Exception:
                pass
            try:
                tenant_v148_enforce_forward_isolation()
            except Exception:
                pass
            try:
                fn = globals().get('_v184_post_restore_rehydrate')
                if callable(fn):
                    fn(data)
            except Exception:
                pass
            # OCH12.31 low-RAM restore seal: persist only root settings and chat
            # stores that are already resident after rehydrate.  Never materialize
            # every cold ledger just to seal a manually restored SQLite.
            save_data(data, root_only=True)
            flush_loaded = globals().get('_och1226_flush_loaded_chat_stores_only')
            if callable(flush_loaded):
                flush_loaded()
            # OCH12.31: the owner-selected generation is now the live authority.
            # Update in-session restore diagnostics immediately; the background
            # canonical reanchor will make the next deploy use this state too.
            try:
                _raw_trace=str(os.getenv('R68_RESTORE_TRACE_JSON','') or '{}')
                _trace=json.loads(_raw_trace) if _raw_trace else {}
                if not isinstance(_trace,dict): _trace={}
                _trace.update({'base_source':'MANUAL_MEGA_RESTORE','manual_restore_source':remote,
                               'manual_restore_at':now_local().isoformat(timespec='seconds'),
                               'empty_init_reason':'','empty_boot_mega_write_guard':False})
                os.environ['R68_RESTORE_TRACE_JSON']=json.dumps(_trace,ensure_ascii=False,separators=(',',':'))
                os.environ['OCH1227_EMPTY_BOOT']='0'
                os.environ['OCH1227_EMPTY_BOOT_REASON']=''
                os.environ['OCH1227_EMPTY_BOOT_MEGA_WRITE_GUARD']='0'
                os.environ['OCH1230_EMPTY_BOOT_NEEDS_SEED']='0'
            except Exception:
                pass
            checkpoint_row = {'required': False, 'ok': False, 'detail': 'helper unavailable'}
            try:
                seal = globals().get('r64_publish_restore_snapshot_v271')
                if callable(seal):
                    checkpoint_row = dict(seal('owner_selected_mega_database_r65') or checkpoint_row)
            except Exception as _r65_seal_exc:
                checkpoint_row = {'required': True, 'ok': False, 'detail': f'{type(_r65_seal_exc).__name__}: {str(_r65_seal_exc)[:220]}'}
            reanchor = _v240_restore_reanchor_guaranteed('owner_selected_mega_database_r65') or {}
            try:
                rec = globals().get('_reminder_boot_reconcile_v241')
                if callable(rec):
                    rec()
            except Exception:
                pass
            success = True
            active = reanchor.get('active') or {}
            return {
                'ok': True, 'source': remote,
                'source_records': int(semantic.get('total_records') or 0),
                'generation': str(active.get('generation') or ''),
                'remote_confirmed': bool(reanchor.get('remote_confirmed_v242', False)),
                'checkpoint_required': bool(checkpoint_row.get('required')),
                'checkpoint_ok': bool(checkpoint_row.get('ok')),
                'checkpoint_detail': str(checkpoint_row.get('detail') or '')[:300],
            }
        finally:
            _v153_shutil.rmtree(work, ignore_errors=True)
    finally:
        if backup_dir:
            try:
                _v153_shutil.rmtree(backup_dir, ignore_errors=True)
            except Exception:
                pass
        end = globals().get('_v241_restore_storage_barrier_end')
        if epoch and callable(end):
            try:
                end(epoch, success)
            except Exception:
                pass
        # OCH12.31: once a user-confirmed MEGA restore succeeded, the restored
        # SQLite becomes the new canonical MEGA lineage automatically.  This also
        # clears any EMPTY_INIT write fence left by the preceding deploy.
        if success:
            try:
                os.environ['OCH1227_EMPTY_BOOT_MEGA_WRITE_GUARD']='0'
                os.environ['OCH1230_EMPTY_BOOT_NEEDS_SEED']='0'
                schedule=globals().get('_och1230_schedule_manual_mega_reanchor')
                if callable(schedule):
                    schedule('owner_selected_mega_database_r65',2.0,0)
            except Exception:
                pass
        globals()['_V240_RECOVERY_AUTHORITY_ACTIVE'] = bool(previous)

# --- mega:0137 · from 09_final_transport.py:1636 · public _v211_mega_node_housekeeping_job ---
def _v211_mega_node_housekeeping_job():
    """Incremental post-READY cleanup; never blocks boot or critical persistence."""
    delay = 21600.0
    try:
        if runtime_is_shutting_down() or not runtime_is_ready():
            return
        if _runtime_watcher_should_yield_to_critical_mega():
            delay = 900.0
            return
        fn = globals().get('mega_diagnostic_node_housekeeping')
        if callable(fn):
            report = fn(50) or {}
            removed = int(report.get('journal_removed', 0) or 0) + int(report.get('critical_removed', 0) or 0)
            delay = 120.0 if removed else 21600.0
            if removed:
                runtime_event('mega_node_housekeeping_v211', f'removed={removed}; next={int(delay)}s')
    except Exception as exc:
        delay = 1800.0
        try:
            runtime_event('mega_node_housekeeping_error_v211', str(exc), 'WARN')
        except Exception:
            pass
    finally:
        try:
            DELAYED_SCHEDULER.schedule('mega-node-housekeeping-v211', delay, _v211_mega_node_housekeeping_job)
        except Exception:
            pass

# --- mega:0138 · from 09_final_transport.py:2645 · public mega_contour_status_text_v234 ---
def mega_contour_status_text_v234() -> str:
    return storage_profiles_status_text_v237_1()

# --- mega:0139 · from 09_final_transport.py:2648 · public mega_contour_keyboard_v234 ---
def mega_contour_keyboard_v234():
    return storage_profiles_keyboard_v237_1()

# --- mega:0140 · from 09_final_transport.py:2815 · public _v265_peer_mega_request ---
def _legacy_s0140_v265_peer_mega_request(path: str) -> dict:
    base_fn = globals().get('_split_peer_base')
    headers_fn = globals().get('_split_headers')
    base = str(base_fn() if callable(base_fn) else '').rstrip('/')
    if not base or not callable(headers_fn):
        raise RuntimeError('Render #2 / PEER_SERVICE_URL недоступен')
    response = requests.get(
        base + '/internal/r65/mega/list',
        params={'path': str(path or '/')},
        headers=headers_fn('vys-262-r65-mega-recovery-browser'),
        timeout=(5, 90),
    )
    try:
        body = response.json() if response.content else {}
    except Exception:
        body = {'error': (response.text or '')[:700]}
    if not (200 <= response.status_code < 300) or not bool((body or {}).get('ok')):
        raise RuntimeError(str((body or {}).get('error') or f'HEAVY HTTP {response.status_code}')[:700])
    return dict(body or {})

# --- mega:0141 · from 09_final_transport.py:2836 · public _v265_refresh_mega_browser ---
def _v265_refresh_mega_browser(path: str='/', page: int=0) -> dict:
    path = str(path or '/').strip() or '/'
    with _V265_MEGA_BROWSER_LOCK:
        _V265_MEGA_BROWSER_STATE['loading'] = True
        _V265_MEGA_BROWSER_STATE['error'] = ''
    try:
        body = _v265_peer_mega_request(path)
        entries = []
        for raw in list(body.get('entries') or []):
            if not isinstance(raw, dict):
                continue
            ep = str(raw.get('path') or '').strip()
            kind = 'dir' if str(raw.get('type') or '') == 'dir' else 'file'
            if not ep:
                continue
            row = {'path': ep, 'kind': kind, 'name': str(raw.get('name') or ep.rsplit('/', 1)[-1] or '/')}
            row['token'] = _v265_mdb_token(ep, kind)
            entries.append(row)
        with _V265_MEGA_BROWSER_LOCK:
            _V265_MEGA_BROWSER_STATE.update({
                'path': str(body.get('path') or path),
                'parent': str(body.get('parent') or '/'),
                'entries': entries,
                'page': max(0, int(page or 0)),
                'error': '',
                'loaded_at': time.time(),
                'loading': False,
                'configured_root': str(body.get('configured_root') or ''),
                'elapsed_mega': float(body.get('elapsed_mega') or 0.0),
            })
        return dict(_V265_MEGA_BROWSER_STATE)
    except Exception as exc:
        with _V265_MEGA_BROWSER_LOCK:
            _V265_MEGA_BROWSER_STATE['loading'] = False
            _V265_MEGA_BROWSER_STATE['error'] = f'{type(exc).__name__}: {str(exc)[:700]}'
        raise

# --- mega:0142 · from 09_final_transport.py:2883 · public mega_database_browser_text_v242 ---
def mega_database_browser_text_v242(page: int | None=None) -> str:
    st = _v265_mdb_state(page)
    entries = list(st.get('entries') or [])
    per = 10
    pages = max(1, (len(entries) + per - 1) // per)
    cur = min(max(0, int(st.get('page') or 0)), pages - 1)
    err = str(st.get('error') or '')
    status = '⏳ загрузка…' if st.get('loading') else (('⛔ ' + err[:700]) if err else f'✅ {len(entries)} элементов')
    return (
        '🗄 БАЗЫ MEGA / ВОССТАНОВЛЕНИЕ · R1\n\n'
        f"Путь: {st.get('path') or '/'}\n"
        f"Статус: {status}\n"
        f"Страница: {cur + 1}/{pages}\n"
        f"Рабочий root R1: {st.get('configured_root') or '—'}\n\n"
        'Ручной recovery-browser может просматривать ВСЕ папки аккаунта MEGA. '
        'Автоматический backup при этом остаётся строго внутри MEGA_BACKUP_DIR.\n\n'
        'Файл при восстановлении принимается только после SQLite quick_check; текущая база сначала получает pre_restore.'
    )[:3900]

# --- mega:0143 · from 09_final_transport.py:2903 · public mega_database_browser_keyboard_v242 ---
def mega_database_browser_keyboard_v242(page: int | None=None):
    kb = types.InlineKeyboardMarkup(row_width=1)
    st = _v265_mdb_state(page)
    entries = list(st.get('entries') or [])
    per = 10
    pages = max(1, (len(entries) + per - 1) // per)
    cur = min(max(0, int(st.get('page') or 0)), pages - 1)
    for row in entries[cur * per:(cur + 1) * per]:
        name = str(row.get('name') or '')
        short = name if len(name) <= 48 else name[:45] + '…'
        if row.get('kind') == 'dir':
            kb.row(IB('📁 ' + short, callback_data=f"v242:mdb:dir:{row.get('token')}"))
        else:
            kb.row(IB('📄 ' + short, callback_data=f"v242:mdb:pick:{row.get('token')}"))
    nav = []
    if cur > 0:
        nav.append(IB('◀️', callback_data=f'v242:mdb:page:{cur - 1}'))
    if cur + 1 < pages:
        nav.append(IB('▶️', callback_data=f'v242:mdb:page:{cur + 1}'))
    if nav:
        kb.row(*nav)
    parent = str(st.get('parent') or '/')
    path = str(st.get('path') or '/')
    if path != '/':
        kb.row(IB('⬆️ Вверх', callback_data=f"v242:mdb:dir:{_v265_mdb_token(parent, 'dir')}"))
    kb.row(IB('🏠 Корень MEGA', callback_data='v242:mdb:root'), IB('🔄 Обновить', callback_data='v242:mdb:refresh'))
    kb.row(IB('🔙 Настройки после деплоя', callback_data='v234:config:open'))
    kb.row(IB('❌ Закрыть', callback_data='info_close'))
    return kb

# --- mega:0144 · from 09_final_transport.py:2934 · public mega_database_confirm_text_v242 ---
def mega_database_confirm_text_v242(token: str) -> str:
    row = _v265_mdb_entry(token)
    return (
        '⚠️ ВОССТАНОВЛЕНИЕ БАЗЫ ИЗ MEGA · R1\n\n'
        f"Файл: {row.get('name') or str(row.get('path') or '').rsplit('/',1)[-1] or 'не найден'}\n"
        f"Путь: {row.get('path') or '—'}\n\n"
        'FAST скачает файл из MEGA прямо на R1, проверит gzip/raw SQLite и PRAGMA quick_check. '
        'Только валидная SQLite полностью заменит рабочую базу без merge. Перед заменой создаётся pre_restore. '
        'После успеха FAST сразу закрепит FULL snapshot в Redis и поставит compact MEGA checkpoint на R1.'
    )[:3900]

# --- mega:0145 · from 09_final_transport.py:2946 · public mega_database_confirm_keyboard_v242 ---
def mega_database_confirm_keyboard_v242(token: str):
    kb = types.InlineKeyboardMarkup()
    kb.row(IB('✅ ПОДТВЕРДИТЬ восстановление', callback_data=f'v242:mdb:confirm:{token}'))
    kb.row(IB('⬅️ Назад к папке', callback_data='v242:mdb:back'))
    kb.row(IB('❌ Закрыть', callback_data='info_close'))
    return kb

# --- mega:0146 · from 09_final_transport.py:2954 · public _v265_heavy_download_mega_file ---
def _legacy_s0146_v265_heavy_download_mega_file(remote: str, workdir: str) -> str:
    base_fn = globals().get('_split_peer_base')
    headers_fn = globals().get('_split_headers')
    base = str(base_fn() if callable(base_fn) else '').rstrip('/')
    if not base or not callable(headers_fn):
        raise RuntimeError('Render #2 / PEER_SERVICE_URL недоступен')
    response = requests.get(
        base + '/internal/r65/mega/file',
        params={'path': str(remote or '')},
        headers=headers_fn('vys-262-r65-mega-recovery-file'),
        timeout=(8, 360),
        stream=True,
    )
    if not (200 <= response.status_code < 300):
        try:
            body = response.json() if response.content else {}
            detail = str((body or {}).get('error') or '')
        except Exception:
            detail = (response.text or '')[:700]
        raise RuntimeError(f'HEAVY MEGA file HTTP {response.status_code}: {detail[:700]}')
    name = str(remote or '').rstrip('/').rsplit('/', 1)[-1] or 'mega_restore.bin'
    safe = re.sub(r'[^A-Za-z0-9_.-]+', '_', name)[-120:] or 'mega_restore.bin'
    target = os.path.join(str(workdir), safe)
    size = 0
    max_bytes = 256 * 1024 * 1024
    with open(target, 'wb') as fh:
        for chunk in response.iter_content(1024 * 1024):
            if not chunk:
                continue
            size += len(chunk)
            if size > max_bytes:
                raise RuntimeError('Файл MEGA больше recovery-лимита 256 МБ')
            fh.write(chunk)
    if size <= 0:
        raise RuntimeError('HEAVY передал пустой файл')
    return target

# --- mega:0147 · from 10_split_policy_offload.py:1691 · public _r222_schedule_post_restore_mega ---
def _r222_schedule_post_restore_mega(reason='restore', delay=150.0, retry=0):
    sched = globals().get('DELAYED_SCHEDULER')
    if sched is None:
        return False
    try:
        sched.cancel('r222-post-restore-mega')
    except Exception:
        pass
    try:
        return bool(sched.schedule('r222-post-restore-mega', max(30.0, float(delay)), _r222_post_restore_mega_checkpoint, str(reason or 'restore'), int(retry or 0)))
    except Exception:
        return False

# --- mega:0148 · from 10_split_policy_offload.py:1705 · public _r222_post_restore_mega_checkpoint ---
def _r222_post_restore_mega_checkpoint(reason='restore', retry=0):
    """One deferred MEGA FULL, never concurrent with restore or high RAM."""
    quiet_fn = globals().get('restore_quiet_active_v222')
    try:
        if callable(quiet_fn) and quiet_fn():
            return _r222_schedule_post_restore_mega(reason, 45.0, int(retry or 0) + 1)
    except Exception:
        pass
    # Only normal runtime MEGA ownership gets an automatic post-restore publish.
    try:
        if not (_r80_mega_master_enabled() and _r71_route_is_fast('mega')):
            return False
    except Exception:
        return False
    allow = globals().get('memory_heavy_allowed')
    if callable(allow):
        try:
            ok, _detail = allow('post-restore-mega-checkpoint')
            if not ok:
                return _r222_schedule_post_restore_mega(reason, 60.0, int(retry or 0) + 1)
        except Exception:
            pass
    try:
        ok, detail = _r80_snapshot_full_compact('post-restore-' + str(reason or 'restore')[:72])
        try:
            bot_journal('r222_post_restore_mega_checkpoint', int(OWNER_ID or 0), f'ok={int(bool(ok))}; retry={int(retry or 0)}; {str(detail)[:260]}', 'INFO' if ok else 'WARN')
        except Exception:
            pass
        if not ok and int(retry or 0) < 6:
            _r222_schedule_post_restore_mega(reason, min(600.0, 60.0 * (2 ** min(3, int(retry or 0)))), int(retry or 0) + 1)
        return bool(ok)
    finally:
        try:
            DELAYED_SCHEDULER.schedule('r222-release-mega-after-restore', 3.0, _r222_release_mega_after_restore, 0)
        except Exception:
            pass

# --- mega:0149 · from 10_split_policy_offload.py:1743 · public _r222_release_mega_after_restore ---
def _r222_release_mega_after_restore(retry=0):
    """Release MEGAcmd immediately after restore work instead of waiting 75s."""
    try:
        if _och1210_mega_busy():
            if int(retry or 0) < 6:
                DELAYED_SCHEDULER.schedule('r222-release-mega-after-restore', 10.0, _r222_release_mega_after_restore, int(retry or 0) + 1)
            return False
        import shutil as _r222_shutil, subprocess as _r222_subprocess
        exe = _r222_shutil.which('mega-quit')
        if not exe:
            return False
        _r222_subprocess.run([exe], stdout=_r222_subprocess.DEVNULL, stderr=_r222_subprocess.DEVNULL, timeout=6, check=False)
        gc_fn = globals().get('_memory_gc')
        if gc_fn is not None and hasattr(gc_fn, 'collect'):
            gc_fn.collect()
        trim_fn = globals().get('memory_malloc_trim')
        if callable(trim_fn):
            trim_fn()
        try: bot_journal('r222_mega_released_after_restore', int(OWNER_ID or 0), f'retry={int(retry or 0)}')
        except Exception: pass
        return True
    except Exception:
        return False

# --- mega:0150 · from 10_split_policy_offload.py:1768 · public _och1230_manual_restore_mega_reanchor ---
def _och1230_manual_restore_mega_reanchor(reason='manual-restore', retry=0):
    """Publish the manually restored SQLite as the new canonical MEGA state.

    Runs only after the local restore barrier has ended.  It deliberately bypasses the
    old 150-second restore cooldown/retry fence, but still respects the memory heavy-job
    gate.  Failure is retried; local SQLite remains authoritative meanwhile.
    """
    _split_os.environ['OCH1227_EMPTY_BOOT_MEGA_WRITE_GUARD']='0'
    _split_os.environ['OCH1230_EMPTY_BOOT_NEEDS_SEED']='0'
    if not (_r80_mega_master_enabled() and _r71_route_is_fast('mega')):
        return False
    try:
        if bool(globals().get('_V241_RESTORE_ACTIVE',False)):
            return _och1230_schedule_manual_mega_reanchor(reason, 2.0, retry)
    except Exception:
        pass
    allow=globals().get('memory_heavy_allowed')
    if callable(allow):
        try:
            ok,_detail=allow('manual-restore-mega-reanchor')
            if not ok:
                return _och1230_schedule_manual_mega_reanchor(reason, min(60.0,10.0*(int(retry or 0)+1)), retry)
        except Exception:
            pass
    ok,detail=_r80_snapshot_full_compact('manual-restore-reanchor:'+str(reason or '')[:64])
    if ok:
        _split_os.environ['OCH1230_MANUAL_REANCHOR_DONE']='1'
        _split_os.environ['OCH1230_MANUAL_REANCHOR_DETAIL']=str(detail or '')[:420]
        try:
            SQLITE.set_meta('restore_control_v240','remote_reanchor_pending',{})
        except Exception:
            pass
        try:
            bot_journal('och1230_manual_restore_mega_reanchor',int(OWNER_ID or 0),f'ok=1; {str(detail)[:300]}')
        except Exception:
            pass
        try:
            root=str(globals().get('MEGA_BACKUP_DIR') or _split_os.getenv('MEGA_BACKUP_DIR','') or '').rstrip('/')
            generation=str(_R80_MEGA_STATE.get('last_full_generation') or '—')
            bot.send_message(int(OWNER_ID or 0),
                f'✅ {globals().get("BOT_DISPLAY_NAME") or "очнись_12.35"}: ручное восстановление закреплено в MEGA.\n'
                f'Generation: {generation}\nManifest: {root}/database/current_manifest.json\nTail: создан заново.')
        except Exception:
            pass
        return True
    _split_os.environ['OCH1230_MANUAL_REANCHOR_DETAIL']=str(detail or '')[:420]
    try:
        bot_journal('och1230_manual_restore_mega_reanchor',int(OWNER_ID or 0),f'ok=0 retry={int(retry or 0)}; {str(detail)[:300]}','WARN')
    except Exception:
        pass
    if int(retry or 0)<6:
        return _och1230_schedule_manual_mega_reanchor(reason,min(180.0,15.0*(2**min(3,int(retry or 0)))),int(retry or 0)+1)
    return False

# --- mega:0151 · from 10_split_policy_offload.py:1823 · public _och1230_schedule_manual_mega_reanchor ---
def _och1230_schedule_manual_mega_reanchor(reason='manual-restore', delay=2.0, retry=0):
    sched=globals().get('DELAYED_SCHEDULER')
    if sched is None:
        try:
            _split_threading.Thread(target=_och1230_manual_restore_mega_reanchor,args=(reason,retry),daemon=True,name='och1230-manual-mega-reanchor').start()
            return True
        except Exception:
            return False
    try:
        sched.cancel('och1230-manual-mega-reanchor')
    except Exception:
        pass
    try:
        return bool(sched.schedule('och1230-manual-mega-reanchor',max(1.0,float(delay)),_och1230_manual_restore_mega_reanchor,str(reason or 'manual-restore'),int(retry or 0)))
    except Exception:
        return False

# --- mega:0152 · from 10_split_policy_offload.py:2106 · public _v262_split_mega_upload_latest_database_backup ---
def _v262_split_mega_upload_latest_database_backup(force=False):
    split_schedule_worker_sync_v262(reason='manual_db_snapshot' if force else 'db_snapshot', delay=0.08 if force else 0.5)
    return True

# --- mega:0153 · from 10_split_policy_offload.py:8393 · public _r44_mega_screen ---
def _r44_mega_screen(chat_id,path,page=0):
    r,meta=_r44_request(chat_id,'GET','/internal/r44/test/mega/list',params={'path':str(path)},timeout=45)
    p=meta.get('payload') if isinstance(meta.get('payload'),dict) else {}
    if not meta.get('ok') or not p.get('ok'):
        text=window_mark('📁 <b>MEGA #2</b>\n\n⛔ '+_r44_html.escape(str(p.get('error') or meta.get('error') or f'HTTP {meta.get("status")}')[:1200]),'Ф4045')
        kb=types.InlineKeyboardMarkup();kb.row(IB('🔙 В тест',callback_data='r44:test:open'));return text,kb
    entries=list(p.get('entries') or []); page=max(0,int(page or 0)); per=9; pages=max(1,(len(entries)+per-1)//per); page=min(page,pages-1)
    text=window_mark(f'📁 <b>MEGA #2</b>\n\nПуть: <code>{_r44_html.escape(str(p.get("path") or path)[:500])}</code>\nПапок/файлов: {len(entries)} · страница {page+1}/{pages}\nПолучено за {meta.get("elapsed",0)}с','Ф4045')
    kb=types.InlineKeyboardMarkup(row_width=1)
    for ent in entries[page*per:(page+1)*per]:
        ep=str(ent.get('path') or ''); kind=str(ent.get('type') or 'file'); name=str(ent.get('name') or ep.rsplit('/',1)[-1] or '/')
        tok=_r44_token(ep,kind); label=('📁 ' if kind=='dir' else '📄 ')+name[:46]
        kb.row(IB(label,callback_data=f'r44:test:mega:{"d" if kind=="dir" else "f"}:{tok}'))
    nav=[]
    ptok=_r44_token(str(p.get('path') or path),'dir')
    if page>0: nav.append(IB('◀️',callback_data=f'r44:test:mega:p:{ptok}:{page-1}'))
    if page+1<pages: nav.append(IB('▶️',callback_data=f'r44:test:mega:p:{ptok}:{page+1}'))
    if nav: kb.row(*nav)
    parent=str(p.get('parent') or '')
    if parent and parent!=str(p.get('path') or ''):
        kb.row(IB('⬆️ Вверх',callback_data=f'r44:test:mega:d:{_r44_token(parent,"dir")}'))
    kb.row(IB('🔄 Обновить',callback_data=f'r44:test:mega:d:{ptok}'),IB('🔙 В тест',callback_data='r44:test:open'))
    return text,kb

# --- mega:0154 · from 10_split_policy_offload.py:8417 · public _r44_send_mega_file ---
def _r44_send_mega_file(chat_id,path):
    cid=int(chat_id); r,meta=_r44_request(cid,'GET','/internal/r44/test/mega/file',params={'path':str(path)},timeout=120,stream=True)
    if r is None or not meta.get('ok'):
        return False,str(meta.get('error') or f'HTTP {meta.get("status")}')[:700]
    tmp=None
    try:
        name=str(path).rstrip('/').rsplit('/',1)[-1] or 'mega_file.bin'
        fd,tmp=_r44_tempfile.mkstemp(prefix='r44_mega_',suffix='_'+_r44_re.sub(r'[^A-Za-z0-9_.-]+','_',name)[-70:]);_r44_os.close(fd)
        size=0
        with open(tmp,'wb') as fh:
            for chunk in r.iter_content(1024*512):
                if not chunk: continue
                size+=len(chunk)
                if size>50*1024*1024: raise RuntimeError('Файл больше диагностического лимита 50 МБ')
                fh.write(chunk)
        with open(tmp,'rb') as fh: bot.send_document(cid,fh,caption=f'🧪 R44 · HEAVY передал из MEGA\n{name}')
        _r44_diag('mega_file_delivered',chat=cid,path=path,bytes=size,elapsed=meta.get('elapsed'))
        return True,f'{name} · {size} байт'
    except Exception as exc:
        _r44_diag('mega_file_error',chat=cid,path=path,error=exc);return False,f'{type(exc).__name__}: {str(exc)[:500]}'
    finally:
        try:
            if tmp:_r44_os.unlink(tmp)
        except Exception:pass

# --- mega:0155 · from 10_split_policy_offload.py:9009 · public _r71_fast_mega_ready ---
def _legacy_s0155_r71_fast_mega_ready():
    try:
        import shutil as _r71_shutil
        creds = bool((str(globals().get('MEGA_EMAIL') or _split_os.getenv('MEGA_EMAIL', '') or '').strip() and str(globals().get('MEGA_PASSWORD') or _split_os.getenv('MEGA_PASSWORD', '') or '').strip()) or str(_split_os.getenv('MEGA_SESSION', '') or '').strip())
        return creds and _r71_shutil.which('mega-ls') is not None and _r71_shutil.which('mega-get') is not None
    except Exception:
        return False

# --- mega:0156 · from 10_split_policy_offload.py:9226 · public mega_upload_latest_database_backup ---
def _legacy_s0156_mega_upload_latest_database_backup(force=False):
    if _r71_route_is_fast('mega'):
        fn = globals().get('_canon_mega_upload_latest_database_backup__002') or globals().get('_canon_mega_upload_latest_database_backup__001')
        if callable(fn): return fn(bool(force))
    return _R71_REMOTE_MEGA_UPLOAD_DB(bool(force))

# --- mega:0157 · from 10_split_policy_offload.py:9240 · public _r71_mega_parent ---
def _r71_mega_parent(path):
    p = str(path or '/').strip() or '/'
    if p == '/': return '/'
    q = p.rstrip('/')
    parent = q.rsplit('/', 1)[0] if '/' in q else ''
    return parent or '/'

# --- mega:0158 · from 10_split_policy_offload.py:9248 · public _r71_mega_child ---
def _r71_mega_child(path, name):
    p = str(path or '/').strip() or '/'
    n = str(name or '').strip().strip('/')
    if p == '/': return '/' + n
    return p.rstrip('/') + '/' + n

# --- mega:0159 · from 10_split_policy_offload.py:9255 · public _r71_local_mega_list ---
def _r71_local_mega_list(path):
    """List immediate MEGA children on R1 using MEGAcmd's own type flag.

    OCH12.12: the old R1 browser combined plain ``mega-ls`` with ``mega-ls -l``
    by row number.  ``mega-ls -l`` may contain a FLAGS header/service rows, so the
    two outputs drifted and real directories could be rendered as files.  A
    single authoritative long listing is now parsed exactly like the proven R2
    browser: FLAGS VERS SIZE DATE TIME NAME, with NAME allowed to contain spaces.
    """
    if not _r71_fast_mega_ready():
        raise RuntimeError('R1 MEGA: credentials или MEGAcmd недоступны')
    login = globals().get('mega_login_if_needed')
    if callable(login): login(control_plane=True)
    runner = globals().get('_mega_run')
    if not callable(runner):
        raise RuntimeError('R1 MEGA runner unavailable')
    path = str(path or '/').strip() or '/'
    longr = runner('mega-ls', ['-l', path], timeout=90, check=False, control_plane=True)
    if int(getattr(longr, 'returncode', 1) or 0) != 0:
        raise RuntimeError(str(getattr(longr, 'stderr', '') or getattr(longr, 'stdout', '') or 'mega-ls -l failed')[:700])

    entries = []
    for raw in str(getattr(longr, 'stdout', '') or '').splitlines():
        line = str(raw or '').strip()
        if not line or line.upper().startswith('FLAGS ') or line.startswith('Versions of '):
            continue
        # MEGAcmd -l: FLAGS VERS SIZE DATE TIME NAME; NAME may contain spaces.
        parts = line.split(None, 5)
        if len(parts) < 6:
            continue
        flags, name = parts[0], parts[5].strip()
        if not name or name in {'.', '..'}:
            continue
        kind = 'dir' if str(flags).lower().startswith('d') else 'file'
        entries.append({'path': _r71_mega_child(path, name), 'name': name, 'type': kind})

    # Keep one canonical row per object and show folders before files.
    dedup = {}
    for row in entries:
        dedup[(str(row.get('type') or ''), str(row.get('path') or ''))] = row
    entries = list(dedup.values())
    entries.sort(key=lambda row: (0 if row.get('type') == 'dir' else 1, str(row.get('name') or '').casefold()))
    return {
        'ok': True,
        'path': path,
        'parent': _r71_mega_parent(path),
        'entries': entries,
        'configured_root': str(globals().get('MEGA_BACKUP_DIR') or ''),
        'owner': 'R1_FAST',
        'parser': 'mega-ls-long-flags-v84',
    }

# --- mega:0160 · from 10_split_policy_offload.py:9308 · public _v265_peer_mega_request ---
def _v265_peer_mega_request(path):
    if _r71_route_is_fast('mega'):
        return _r71_local_mega_list(path)
    if callable(_R71_REMOTE_MEGA_BROWSER_REQUEST):
        return _R71_REMOTE_MEGA_BROWSER_REQUEST(path)
    raise RuntimeError('Render #2 MEGA browser unavailable')

# --- mega:0161 · from 10_split_policy_offload.py:9316 · public _v265_heavy_download_mega_file ---
def _v265_heavy_download_mega_file(remote, workdir):
    if not _r71_route_is_fast('mega'):
        if callable(_R71_REMOTE_MEGA_DOWNLOAD): return _R71_REMOTE_MEGA_DOWNLOAD(remote, workdir)
        raise RuntimeError('Render #2 MEGA download unavailable')
    if not _r71_fast_mega_ready(): raise RuntimeError('R1 MEGA unavailable')
    login = globals().get('mega_login_if_needed')
    if callable(login): login(control_plane=True)
    runner = globals().get('_mega_run')
    if not callable(runner): raise RuntimeError('R1 MEGA runner unavailable')
    _split_os.makedirs(str(workdir), exist_ok=True)
    res = runner('mega-get', [str(remote), str(workdir)], timeout=360, check=False, control_plane=True)
    if int(getattr(res, 'returncode', 1) or 0) != 0:
        raise RuntimeError(str(getattr(res, 'stderr', '') or getattr(res, 'stdout', '') or 'mega-get failed')[:700])
    name = str(remote or '').rstrip('/').rsplit('/', 1)[-1] or 'mega_restore.bin'
    target = _split_os.path.join(str(workdir), name)
    if _split_os.path.isfile(target): return target
    files = [x for x in _split_os.listdir(str(workdir)) if _split_os.path.isfile(_split_os.path.join(str(workdir), x))]
    if len(files) == 1: return _split_os.path.join(str(workdir), files[0])
    raise RuntimeError('R1 MEGA скачал файл, но локальный путь не найден')

# --- mega:0162 · from 10_split_policy_offload.py:9472 · public mega_contour_enabled_v234 ---
def mega_contour_enabled_v234():
    if _r71_route_is_fast('mega'):
        return True
    return bool(_R71_MEGA_CONTOUR_CORE()) if callable(_R71_MEGA_CONTOUR_CORE) else False

# --- mega:0163 · from 10_split_policy_offload.py:11381 · public _r80_mega_master_enabled ---
def _r80_mega_master_enabled():
    try:
        import runtime_config as _r80_rc
        fn=getattr(_r80_rc,'mega_render_enabled',None)
        if callable(fn): return bool(fn())
        return bool(getattr(_r80_rc,'_MEGA_RENDER_ENABLED',False))
    except Exception:
        return False

# --- mega:0164 · from 10_split_policy_offload.py:11407 · public _r80_mega_runtime_ready ---
def _r80_mega_runtime_ready():
    # OCH12.31: EMPTY_INIT is still a normal writable runtime.  A previous failed
    # restore must not leave MEGA durability permanently disabled.
    return bool(_OCH1226_MEGA_DURABILITY_ENABLED and _r80_mega_master_enabled() and _r71_route_is_fast('mega') and _r71_fast_mega_ready() and _r80_compact_root())

# --- mega:0165 · from 10_split_policy_offload.py:11435 · public _r80_mega_put_fixed ---
def _r80_mega_put_fixed(local_path,remote_path):
    """Publish one canonical database object, archiving the previous object instead of deleting it."""
    paths=_r80_compact_paths(); root=paths.get('root')
    if not root: return False,'MEGA canonical database root unavailable'
    prev=bool(globals().get('_V240_RECOVERY_AUTHORITY_ACTIVE',False))
    globals()['_V240_RECOVERY_AUTHORITY_ACTIVE']=True
    try:
        remote_dir=remote_path.rsplit('/',1)[0] or root
        mega_ensure_remote_path(remote_dir)
        ok=bool(mega_put_replace(str(local_path),remote_dir,remote_path.rsplit('/',1)[-1],archive_previous=True))
        return ok,('ok' if ok else 'mega_put_replace returned false')
    except Exception as exc:
        return False,f'{type(exc).__name__}: {str(exc)[:220]}'
    finally:
        globals()['_V240_RECOVERY_AUTHORITY_ACTIVE']=prev

# --- mega:0166 · from 10_split_policy_offload.py:11770 · public _r81_mega_get_exact ---
def _r81_mega_get_exact(remote_path,workdir,timeout_sec=90):
    folder=_split_os.path.join(str(workdir),str(abs(hash(str(remote_path))))[-10:])
    _split_os.makedirs(folder,exist_ok=True)
    res=_mega_run('mega-get',[str(remote_path),folder],check=False,timeout=float(timeout_sec))
    if int(getattr(res,'returncode',1) or 0)!=0:
        return None,str(getattr(res,'stderr','') or getattr(res,'stdout','') or 'mega-get failed')[:240]
    base=_split_os.path.basename(str(remote_path).rstrip('/')); direct=_split_os.path.join(folder,base)
    if _split_os.path.isfile(direct): return direct,'ok'
    for root,_dirs,files in _split_os.walk(folder):
        if base in files: return _split_os.path.join(root,base),'ok'
    return None,'downloaded exact object missing locally'

# --- mega:0167 · from 10_split_policy_offload.py:11782 · public _r221_manual_mega_ready ---
def _r221_manual_mega_ready():
    """Manual recovery bypasses MEGA_ENABLED but still requires real credentials + CLI."""
    try:
        creds = bool((str(globals().get('MEGA_EMAIL') or _split_os.getenv('MEGA_EMAIL','') or '').strip() and
                      str(globals().get('MEGA_PASSWORD') or _split_os.getenv('MEGA_PASSWORD','') or '').strip()) or
                     str(_split_os.getenv('MEGA_SESSION','') or '').strip())
        return bool(creds and _split_shutil.which('mega-ls') and _split_shutil.which('mega-get'))
    except Exception:
        return False

# --- mega:0168 · from 10_split_policy_offload.py:11792 · public r81_manual_compact_mega_restore ---
def r81_manual_compact_mega_restore():
    """12.26 manual restore: exact current_manifest -> immutable generation -> matching MEGA tail. Never Redis."""
    work=None; prev=bool(globals().get('_V240_RECOVERY_AUTHORITY_ACTIVE',False))
    globals()['_V240_RECOVERY_AUTHORITY_ACTIVE']=True
    try:
        if not _r221_manual_mega_ready(): return False,'MEGA credentials/CLI unavailable for manual recovery',0
        login=globals().get('mega_login_if_needed')
        if callable(login): login(control_plane=True)
        work=_split_tempfile.mkdtemp(prefix='och1226_manual_generation_restore_')
        dl=globals().get('constitution_download_active_generation')
        if not callable(dl): return False,'constitution_download_active_generation unavailable',0
        gz_path,manifest,detail=dl(work)
        if not gz_path or not isinstance(manifest,dict): return False,'canonical generation: '+str(detail),0
        generation=str(manifest.get('generation') or '')
        candidate=_split_os.path.join(work,'candidate.sqlite3')
        try:
            with _split_gzip.open(gz_path,'rb') as src,open(candidate,'wb') as dst:
                _split_shutil.copyfileobj(src,dst,length=1024*1024)
        except Exception as exc:
            return False,f'generation decompress {type(exc).__name__}: {str(exc)[:180]}',0
        if not _r81_compact_db_valid(candidate): return False,'canonical generation SQLite quick_check failed',0
        paths=_r80_compact_paths(); tail_path,tail_detail=_r81_mega_get_exact(paths['tail'],work,90)
        applied=0
        if tail_path:
            try: tail=_split_json.loads(_split_gzip.decompress(open(tail_path,'rb').read()).decode('utf-8')) or {}
            except Exception as exc: return False,f'canonical tail decode {type(exc).__name__}: {str(exc)[:180]}',0
            if int(tail.get('schema') or 0)!=126: return False,'canonical tail schema != 126',0
            if str(tail.get('base_generation') or '')==generation:
                events=list(tail.get('events') or [])
                if any(not _r81_compact_event_valid(ev) for ev in events): return False,'canonical tail contains invalid R32 event',0
                applied,_stale=_r81_apply_compact_events(candidate,events)
                claimed=int(tail.get('max_revision') or 0); final_max=_r81_compact_max_revision(candidate)
                if claimed and final_max<claimed: return False,f'canonical tail incomplete {final_max} < {claimed}',applied
        if not _r81_compact_db_valid(candidate): return False,'canonical candidate invalid after tail',applied
        SQLITE.replace_database(candidate)
        # Adopt the restored canonical baseline in the live durability manager.
        _tail_events=list((tail or {}).get('events') or []) if isinstance(locals().get('tail'),dict) else []
        with _R80_MEGA_LOCK:
            _R80_MEGA_TAIL_EVENTS.clear()
            for _ev in _tail_events:
                if _r81_compact_event_valid(_ev):
                    _R80_MEGA_TAIL_EVENTS[str(_ev.get('event_id'))]=_ev
            _R80_MEGA_STATE.update({
                'last_full_generation':generation,'last_full_at':_split_time.time(),
                'full_event_cutoff_score':float((tail or {}).get('full_event_cutoff_score') or 0.0) if isinstance(locals().get('tail'),dict) else 0.0,
                'full_event_revision':int((tail or {}).get('full_event_revision') or 0) if isinstance(locals().get('tail'),dict) else 0,
                'full_db_revision':float((tail or {}).get('full_db_revision') or 0.0) if isinstance(locals().get('tail'),dict) else 0.0,
                'last_tail_at':_split_time.time(),'last_tail_count':len(_tail_events),
                'tail_max_revision':int((tail or {}).get('max_revision') or _r81_compact_max_revision(candidate)) if isinstance(locals().get('tail'),dict) else _r81_compact_max_revision(candidate),
                'tail_dirty':False,'last_error':'','next_retry':0.0,
            })
        return True,f'MEGA canonical generation restore OK generation={generation}; applied={applied}; Redis not used',applied
    except Exception as exc:
        return False,f'{type(exc).__name__}: {str(exc)[:260]}',0
    finally:
        globals()['_V240_RECOVERY_AUTHORITY_ACTIVE']=prev
        if work: _split_shutil.rmtree(work,ignore_errors=True)

# --- mega:0169 · from 10_split_policy_offload.py:11944 · public _r71_fast_mega_ready ---
def _r71_fast_mega_ready():
    if not _r80_mega_master_enabled(): return False
    try:
        import shutil as _r80_shutil
        creds=bool((str(globals().get('MEGA_EMAIL') or _split_os.getenv('MEGA_EMAIL','') or '').strip() and str(globals().get('MEGA_PASSWORD') or _split_os.getenv('MEGA_PASSWORD','') or '').strip()) or str(_split_os.getenv('MEGA_SESSION','') or '').strip())
        return creds and _r80_shutil.which('mega-ls') is not None and _r80_shutil.which('mega-get') is not None
    except Exception: return False

# --- mega:0170 · from 10_split_policy_offload.py:12084 · public mega_upload_latest_database_backup ---
def mega_upload_latest_database_backup(force=False):
    if _r71_route_is_fast('checkpoints') or _r71_route_is_fast('mega'):
        return _r80_queue_compact_full('manual-force' if force else 'scheduled-full')
    return _R80_REMOTE_MEGA_UPLOAD_DB(bool(force))

# --- mega:0171 · from 10_split_policy_offload.py:12891 · public _och1224_hard_release_mega_runtime ---
def _och1224_hard_release_mega_runtime() -> dict:
    """OCH12.26 release MEGAcmd only when the transaction manager is idle."""
    global _V178_MEGA_SESSION_OK_UNTIL
    out = {'quit': False, 'term': 0, 'kill': 0, 'survivors': 0}
    try:
        with _OCH1225_MEGA_CMD_LOCK:
            if int(_OCH1225_MEGA_CMD_ACTIVE or 0) > 0:
                return {'skipped': 'command_active', 'active': int(_OCH1225_MEGA_CMD_ACTIVE or 0)}
    except Exception:
        return {'skipped': 'manager_state_unavailable'}
    try:
        import shutil as _msh, subprocess as _msp, signal as _msig
        exe = _msh.which('mega-quit')
        if exe:
            try:
                _msp.run([exe], stdout=_msp.DEVNULL, stderr=_msp.DEVNULL, timeout=5, check=False)
                out['quit'] = True
            except Exception:
                pass
        me = int(_split_os.getpid())
        victims = []
        for ent in _split_os.listdir('/proc'):
            if not str(ent).isdigit():
                continue
            pid = int(ent)
            if pid in {0, 1, me}:
                continue
            try:
                comm = open(f'/proc/{pid}/comm', 'r', encoding='utf-8', errors='ignore').read().strip()
            except Exception:
                continue
            if comm in {'mega-cmd-server', 'mega-exec'}:
                victims.append(pid)
        for pid in victims:
            try:
                _split_os.kill(pid, _msig.SIGTERM); out['term'] += 1
            except Exception:
                pass
        if victims:
            _split_time.sleep(0.15)
        def _alive_non_zombie(pid):
            try:
                stat = open(f'/proc/{pid}/stat', 'r', encoding='utf-8', errors='ignore').read().split()
                return bool(len(stat) > 2 and stat[2] != 'Z')
            except Exception:
                return False
        survivors = [pid for pid in victims if _alive_non_zombie(pid)]
        for pid in survivors:
            try:
                _split_os.kill(pid, _msig.SIGKILL); out['kill'] += 1
            except Exception:
                pass
        if survivors:
            _split_time.sleep(0.05)
        out['survivors'] = sum(1 for pid in survivors if _alive_non_zombie(pid))
    except Exception as exc:
        out['error'] = f'{type(exc).__name__}: {str(exc)[:160]}'
    try:
        gc_fn = globals().get('_memory_gc')
        if gc_fn is not None and hasattr(gc_fn, 'collect'):
            gc_fn.collect()
        trim_fn = globals().get('memory_malloc_trim')
        if callable(trim_fn):
            trim_fn()
    except Exception:
        pass
    try:
        # A killed/restarted MEGAcmd daemon must never inherit a process-local
        # "session OK" TTL or directory cache.
        _V178_MEGA_SESSION_OK_UNTIL = 0.0
        cache = globals().get('_V178_MEGA_KNOWN_DIRS')
        if hasattr(cache, 'clear'): cache.clear()
    except Exception:
        pass
    if out.get('term') or out.get('kill') or out.get('survivors') or out.get('error'):
        try:
            bot_journal('och1225_mega_idle_release', int(OWNER_ID or 0), str(out))
        except Exception:
            pass
    return out

# --- mega:0172 · from 10_split_policy_offload.py:12973 · public _och1224_release_mega_if_quiet ---
def _och1224_release_mega_if_quiet():
    if not _OCH1224_MEGA_ZERO_RESIDENT:
        return False
    if _och1210_mega_busy():
        # Do not create a cleanup watchdog loop.  The command that finishes last
        # schedules the next latest-wins release.
        return False
    try:
        with _OCH1225_MEGA_CMD_LOCK:
            idle_for = _split_time.time() - float(_OCH1225_MEGA_LAST_CMD_FINISHED or 0.0)
        if _OCH1225_MEGA_LAST_CMD_FINISHED and idle_for < _OCH1224_MEGA_ZERO_DELAY * 0.8:
            return False
    except Exception:
        pass
    out = _och1224_hard_release_mega_runtime()
    return not bool((out or {}).get('skipped'))

# --- mega:0173 · from 10_split_policy_offload.py:12991 · public _och1224_schedule_mega_release ---
def _och1224_schedule_mega_release():
    if not _OCH1224_MEGA_ZERO_RESIDENT:
        return
    try:
        # latest-wins key: a multi-command MEGA sequence continuously pushes the
        # cleanup deadline forward, then one cleanup runs after the sequence is quiet.
        DELAYED_SCHEDULER.schedule(_OCH1224_MEGA_CLEANUP_KEY, _OCH1224_MEGA_ZERO_DELAY, _och1224_release_mega_if_quiet)
    except Exception:
        pass

# --- mega:0174 · from 10_split_policy_offload.py:13002 · public _och1210_mega_run ---
def _och1210_mega_run(cmd: str, args=None, timeout=None, check: bool=True, control_plane: bool=False):
    global _OCH1210_MEGA_LAST_ACTIVITY, _OCH1225_MEGA_CMD_ACTIVE, _OCH1225_MEGA_LAST_CMD_FINISHED
    _OCH1210_MEGA_LAST_ACTIVITY = _split_time.time()
    if not callable(_OCH1210_PARENT_MEGA_RUN):
        raise RuntimeError('MEGA runner unavailable')
    # The underlying executor is also serialized, but this counter lets cleanup and
    # Memory Guard know that a CLI command is alive without reading subprocess state.
    with _OCH1225_MEGA_CMD_LOCK:
        _OCH1225_MEGA_CMD_ACTIVE += 1
    try:
        return _OCH1210_PARENT_MEGA_RUN(cmd, args=args, timeout=timeout, check=check, control_plane=control_plane)
    finally:
        _OCH1210_MEGA_LAST_ACTIVITY = _split_time.time()
        with _OCH1225_MEGA_CMD_LOCK:
            _OCH1225_MEGA_CMD_ACTIVE = max(0, int(_OCH1225_MEGA_CMD_ACTIVE) - 1)
            _OCH1225_MEGA_LAST_CMD_FINISHED = _split_time.time()
        _och1224_schedule_mega_release()

# --- mega:0175 · from 10_split_policy_offload.py:13024 · public _och1210_mega_busy ---
def _och1210_mega_busy() -> bool:
    # OCH12.31: the zero-resident cleanup must never kill MEGAcmd while a restore,
    # canonical publish/re-anchor or other recovery authority owns MEGA.
    try:
        if bool(globals().get('_V241_RESTORE_ACTIVE', False)) or bool(globals().get('_V240_RECOVERY_AUTHORITY_ACTIVE', False)):
            return True
    except Exception:
        return True
    try:
        with _OCH1225_MEGA_CMD_LOCK:
            if int(_OCH1225_MEGA_CMD_ACTIVE or 0) > 0:
                return True
    except Exception:
        return True
    try:
        with _R80_MEGA_LOCK:
            if bool(_R80_MEGA_STATE.get('running')):
                return True
    except Exception:
        return True
    try:
        with _V240_PAR_STATS_LOCK:
            if int((_V240_PAR_STATS or {}).get('active') or 0) > 0:
                return True
    except Exception:
        pass
    try:
        active = globals().get('_MEMORY_ACTIVE') or {}
        if any(str((row or {}).get('kind') or '').startswith('mega:') for row in active.values()):
            return True
    except Exception:
        pass
    return False

# --- mega:0176 · from 10_split_policy_offload.py:13059 · public _och1210_quit_mega_server_if_idle ---
def _och1210_quit_mega_server_if_idle() -> bool:
    global _OCH1210_MEGA_LAST_ACTIVITY
    if _split_time.time() - float(_OCH1210_MEGA_LAST_ACTIVITY or 0.0) < _OCH1210_MEGA_IDLE_SEC:
        return False
    if _och1210_mega_busy() or _och111_hot_ui_busy():
        return False
    try:
        import shutil as _r83_shutil, subprocess as _r83_subprocess
        exe = _r83_shutil.which('mega-quit')
        if not exe:
            return False
        _r83_subprocess.run([exe], stdout=_r83_subprocess.DEVNULL, stderr=_r83_subprocess.DEVNULL, timeout=8, check=False)
        _OCH1210_MEGA_LAST_ACTIVITY = _split_time.time()
        try:
            gc_fn = globals().get('_memory_gc')
            if gc_fn is not None and hasattr(gc_fn, 'collect'): gc_fn.collect()
            trim_fn = globals().get('memory_malloc_trim')
            if callable(trim_fn): trim_fn()
        except Exception:
            pass
        try: bot_journal('r83_mega_idle_server_released', int(OWNER_ID or 0), f'idle_sec={int(_OCH1210_MEGA_IDLE_SEC)}')
        except Exception: pass
        return True
    except Exception:
        return False

# --- mega:0177 · from 10_split_policy_offload.py:13086 · public _och1210_mega_idle_reaper_loop ---
def _och1210_mega_idle_reaper_loop():
    _split_time.sleep(30.0)
    while True:
        try: _och1210_quit_mega_server_if_idle()
        except Exception: pass
        _split_time.sleep(30.0)

# --- mega:0178 · from 10_split_policy_offload.py:13094 · public _och1210_start_mega_idle_reaper ---
def _och1210_start_mega_idle_reaper():
    global _OCH1210_MEGA_REAPER_STARTED
    if _OCH1224_MEGA_ZERO_RESIDENT:
        return
    with _OCH1210_MEGA_REAPER_LOCK:
        if _OCH1210_MEGA_REAPER_STARTED:
            return
        _OCH1210_MEGA_REAPER_STARTED = True
    _split_threading.Thread(target=_och1210_mega_idle_reaper_loop, daemon=True, name='r83-mega-idle').start()

# v266
