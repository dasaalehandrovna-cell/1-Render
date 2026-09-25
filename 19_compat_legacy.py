# v266
"""ОЧНИСЬ 12.35 · legacy compatibility stage catalog.

Ранние версии переопределяемых инфраструктурных функций вынесены сюда, чтобы в 01–10
оставалась ровно одна финальная def каждого имени. Этот файл не запускается отдельно.
"""

# --- compat_legacy:0001 · from 01_core_data.py:244 · public traffic_audit_text ---
def _legacy_compat_s0001_traffic_audit_text(scope: str='month') -> str:
    b = _traffic_scope_bucket(scope)
    labels = {'month': 'этот месяц', 'today': 'сегодня', 'process': 'этот процесс', 'all': 'вся сохранённая история'}
    label = labels.get(str(scope).lower(), str(scope))
    lines = [f'📶 МАКСИМАЛЬНЫЙ АУДИТ ТРАФИКА — {label}', f"Исходящий (главный ориентир): {_traffic_fmt_bytes(b.get('outbound_bytes', 0))}", f"Входящий: {_traffic_fmt_bytes(b.get('inbound_bytes', 0))}", f"Сетевых вызовов: {b.get('calls', 0)} · ошибок: {b.get('errors', 0)}", '', 'По системам:']
    rows = sorted((b.get('categories') or {}).items(), key=lambda kv: int((kv[1] or {}).get('outbound_bytes', 0) or 0), reverse=True)
    names = {'telegram': 'Telegram API', 'mega_put': 'MEGA upload', 'mega_get': 'MEGA download', 'mega_control': 'MEGA служебное', 'google': 'Google API', 'currency': 'Курс USD', 'self_http': 'Self/Render HTTP', 'peer_http': 'Второй Render HTTP', 'other_http': 'Прочий HTTP', 'web_http': 'HTTP responses/webhook'}
    for cat, row in rows:
        lines.append(f"• {names.get(cat, cat)}: ↑ {_traffic_fmt_bytes(row.get('outbound_bytes', 0))} · ↓ {_traffic_fmt_bytes(row.get('inbound_bytes', 0))} · {row.get('calls', 0)} выз. · err {row.get('errors', 0)}")
    ops = sorted((b.get('operations') or {}).items(), key=lambda kv: int((kv[1] or {}).get('outbound_bytes', 0) or 0), reverse=True)
    if ops:
        lines += ['', 'ТОП конкретных операций:']
        for op, row in ops[:10]:
            lines.append(f"• {op}: ↑ {_traffic_fmt_bytes(row.get('outbound_bytes', 0))} · {row.get('calls', 0)} выз.")
    hours = sorted((b.get('hours') or {}).items(), key=lambda kv: str(kv[0]), reverse=True)
    if hours:
        lines += ['', 'Последние часы (↑ исходящий):']
        for hour, row in hours[:8]:
            top = sorted((row.get('categories') or {}).items(), key=lambda kv: int((kv[1] or {}).get('outbound_bytes', 0) or 0), reverse=True)
            culprit = top[0][0] + ' ' + _traffic_fmt_bytes((top[0][1] or {}).get('outbound_bytes', 0)) if top else '—'
            lines.append(f"• {str(hour)[5:].replace('T', ' ')}: {_traffic_fmt_bytes(row.get('outbound_bytes', 0))} · {culprit}")
    lines += ['', '🧾 Сводка также пишется в обычные Render Logs при каждом checkpoint — без отдельного сетевого запроса.', 'ℹ️ Бот считает прикладные байты. Панель Render может быть выше из-за TLS/TCP/HTTP overhead и платформенного учёта.']
    return '\n'.join(lines)[:3900]

# --- compat_legacy:0002 · from 01_core_data.py:349 · public _traffic_classify_http ---
def _legacy_compat_s0002_traffic_classify_http(url: str, method: str) -> tuple[str, str]:
    try:
        u = urllib.parse.urlsplit(str(url or ''))
        host = (u.hostname or '').casefold()
        path = u.path or '/'
        last = path.rstrip('/').split('/')[-1] or '/'
    except Exception:
        host = ''
        last = '/'
    if host.endswith('api.telegram.org'):
        return ('telegram', f'telegram:{last}')
    if 'googleapis.com' in host or host.endswith('google.com'):
        return ('google', f'google:{method.upper()}:{host}:{last}')
    render_host = str(os.getenv('RENDER_EXTERNAL_HOSTNAME', '') or '').casefold()
    if render_host and host == render_host:
        return ('self_http', f'self:{method.upper()}:{last}')
    peer_url = str(os.getenv('PEER_KEEPALIVE_URL', '') or '')
    try:
        peer_fn = globals().get('keepalive_peer_target_url')
        if callable(peer_fn):
            peer_url = str(peer_fn() or peer_url)
    except Exception:
        pass
    try:
        peer_host = (urllib.parse.urlsplit(peer_url).hostname or '').casefold() if peer_url else ''
    except Exception:
        peer_host = ''
    if peer_host and host == peer_host:
        return ('peer_http', f'peer:{method.upper()}:{last}')
    rate_url = str(globals().get('USD_RATE_URL') or '')
    if 'dolarapi.com' in host or (rate_url and str(url or '') == rate_url):
        return ('currency', f'currency:{method.upper()}:{host}')
    return ('other_http', f"http:{method.upper()}:{host or 'unknown'}:{last}")

# --- compat_legacy:0003 · from 01_core_data.py:7923 · public _tg_call_retry ---
def _legacy_compat_s0003_tg_call_retry(func, *args, attempts: int=7, purpose: str='telegram', **kwargs):
    """
    Telegram API wrapper: если Telegram вернул 429, ждём retry_after и повторяем.
    Это нужно, чтобы пересылка не терялась, а доставлялась позже.
    """
    last_err = None
    _r52_tg_call_started=time.monotonic()
    try: r52_diag('TG_CALL_ENTER', purpose=purpose, func=getattr(func,'__name__',str(func))[:120], attempts=attempts, chat=_tg_first_chat_id(args,kwargs))
    except Exception: pass
    for attempt in range(1, int(attempts) + 1):
        try:
            chat_id = _tg_first_chat_id(args, kwargs)
            try: r52_diag('TG_CALL_ATTEMPT', purpose=purpose, func=getattr(func,'__name__',str(func))[:120], attempt=attempt, attempts=attempts, chat=chat_id)
            except Exception: pass
            _telegram_rate_limit_global()
            if chat_id is not None:
                ui_gap = effective_fast_telegram_gap() if _is_fast_ui_purpose(purpose) else 0.35
                _telegram_rate_limit_chat(chat_id, min_gap=ui_gap)
            try:
                if verbose_telegram_journal_enabled() and (not _is_fast_ui_purpose(purpose)):
                    bot_journal('telegram_api_call', chat_id, f"{purpose}: {getattr(func, '__name__', str(func))} attempt={attempt}/{attempts}")
            except Exception:
                pass
            try:
                for _obj in list(args) + list(kwargs.values()):
                    if hasattr(_obj, 'seek'):
                        try:
                            _obj.seek(0)
                        except Exception:
                            pass
            except Exception:
                pass
            try:
                _telegram_guard_local.in_retry = True
                _res = func(*args, **kwargs)
            finally:
                _telegram_guard_local.in_retry = False
            # R48: success is a pure transport hot path. Incoming updates and explicit
            # probes refresh lifecycle; every send/edit must not acquire data_lock.
            try: r52_diag('TG_CALL_OK', purpose=purpose, func=getattr(func,'__name__',str(func))[:120], attempt=attempt, chat=chat_id, elapsed=time.monotonic()-_r52_tg_call_started)
            except Exception: pass
            return _res
        except TypeError:
            raise
        except Exception as e:
            last_err = e
            try: r52_diag('TG_CALL_ERROR', purpose=purpose, func=getattr(func,'__name__',str(func))[:120], attempt=attempt, chat=locals().get('chat_id'), elapsed=time.monotonic()-_r52_tg_call_started, error=f'{type(e).__name__}:{str(e)[:1000]}')
            except Exception: pass
            retry_after = _telegram_retry_after_seconds(e)
            if retry_after is None:
                try:
                    chat_id_for_mark = _tg_first_chat_id(args, kwargs)
                    if chat_id_for_mark is not None and _is_bot_removed_error(e):
                        set_chat_bot_removed(int(chat_id_for_mark), True, str(e)[:240])
                except Exception:
                    pass
                raise
            wait = _telegram_register_429_cooldown(e, extra=0.35)
            log_info(f'[TG 429 RETRY] {purpose}: attempt={attempt}/{attempts}, wait={wait:.2f}s, error={str(e)[:220]}')
            try:
                bot_journal('telegram_429_retry', chat_id if 'chat_id' in locals() else None, f'{purpose}: attempt={attempt}/{attempts}, wait={wait}s, error={str(e)[:220]}', 'WARN')
            except Exception:
                pass
            if _is_fast_ui_purpose(purpose):
                raise e
            if attempt >= int(attempts):
                break
            time.sleep(wait)
    raise last_err

# --- compat_legacy:0004 · from 01_core_data.py:12389 · public runtime_graceful_shutdown ---
def _legacy_compat_s0004_runtime_graceful_shutdown(signal_name: str='SIGTERM'):
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
            DELAYED_SCHEDULER.cancel('r68-local-runtime-tick')
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
            _r68_write_local_runtime_state('shutdown')
            _r68_write_local_sqlite_snapshot('shutdown', True)
        except Exception as e:
            runtime_event('r68_local_shutdown_snapshot_error', str(e), 'WARN')
        try:
            journal_flush_to_mega(True)
        except Exception:
            pass
        runtime_upload_snapshot('shutdown', True)
    finally:
        _RUNTIME_SHUTDOWN_LOCK.release()

# --- compat_legacy:0005 · from 01_core_data.py:13177 · public save_data ---
def _legacy_compat_s0005_save_data(d, chat_ids=None, full: bool=False, root_only: bool=False):
    """R48 persistence: snapshot under short RAM locks; SQLite only after unlock."""
    ids = set()
    with data_lock:
        d.setdefault('_state_meta', {})['last_saved_at'] = now_local().isoformat(timespec='seconds')
        d['_state_meta']['bot_version'] = VERSION
        d['finance_active_chats'] = {str(cid): True for cid in list(finance_active_chats)}
        d['backup_flags'] = {'drive': bool(backup_flags.get('drive', True)), 'channel': bool(backup_flags.get('channel', True))}
        try:
            _persist_forward_index_in_data(d)
        except Exception as e:
            log_error(f'save_data forward_index: {e}')
        root_payload = copy.deepcopy(_sqlite_pack_root(d))
        if chat_ids is not None:
            source_ids = chat_ids if isinstance(chat_ids, (list, tuple, set)) else [chat_ids]
            for cid in source_ids:
                try: ids.add(int(cid))
                except Exception: pass
        elif not full:
            cid = current_state_chat_id()
            if cid is not None:
                try: ids.add(int(cid))
                except Exception: pass
        all_chat_ids = []
        if full or not ids:
            for cid_s in list((d.get('chats', {}) or {}).keys()):
                try: all_chat_ids.append(int(cid_s))
                except Exception: pass
    SQLITE.save_root(root_payload)
    if root_only:
        return
    target_ids = sorted(ids if (ids and not full) else set(all_chat_ids))
    bundles=[]
    for cid in target_ids:
        try:
            with locked_chat(cid):
                store = ((d.get('chats', {}) or {}).get(str(cid)))
                if not isinstance(store, dict):
                    continue
                if LOWRAM_ENABLED:
                    meta, cold = _lowram_flush_chat(cid, store, evict=False)
                else:
                    meta, cold = copy.deepcopy(dict(store)), {}
                bundles.append((cid, meta, cold))
        except Exception as exc:
            log_error(f'save_data snapshot chat={cid}: {exc}')
            if ids and not full:
                raise
    total=0
    for cid, meta, cold in bundles:
        total += int(SQLITE.save_chat_bundle(cid, meta, cold) or 0)
    if total:
        with _LOWRAM_LOCK:
            _LOWRAM_STATS['cold_saves'] += total
    try:
        fn = globals().get('config_guard_note_after_save_v234')
        if callable(fn):
            fn('save_data')
    except Exception as exc:
        try: log_error(f'config guard save hook v234: {exc}')
        except Exception: pass

# --- compat_legacy:0006 · from 01_core_data.py:16717 · public _v234_config_projection_from_payload ---
def _legacy_compat_s0006_v234_config_projection_from_payload(payload: dict) -> dict:
    payload = payload if isinstance(payload, dict) else {}
    root = {}
    for key in _V234_ROOT_CONFIG_KEYS:
        value = payload.get(key)
        if isinstance(value, (dict, list)) or value is not None:
            root[key] = _v234_json_clone(value if value is not None else {})
    gs = payload.get('_global_settings') or {}
    if isinstance(gs, dict):
        root['_global_settings'] = {str(k): _v234_json_clone(_v239_config_guard_sanitize_transient(v, str(k))) for k, v in gs.items() if str(k) not in _V234_GLOBAL_SETTINGS_EXCLUDE}
    chats_out = {}
    for cid, store in (payload.get('chats') or {}).items():
        if not isinstance(store, dict):
            continue
        settings = store.get('settings') or {}
        if not isinstance(settings, dict):
            settings = {}
        cfg = {str(k): _v234_json_clone(_v239_config_guard_sanitize_transient(v, str(k))) for k, v in settings.items() if str(k) not in _V234_CHAT_SETTINGS_EXCLUDE}
        row = {'settings': cfg}
        if isinstance(store.get('info'), dict):
            row['info'] = _v234_json_clone(store.get('info'))
        if isinstance(store.get('known_chats'), dict):
            row['known_chats'] = _v234_json_clone(store.get('known_chats'))
        if isinstance(store.get('chat_lifecycle_v150'), dict):
            life = dict(store.get('chat_lifecycle_v150') or {})
            life.pop('history', None)
            row['chat_lifecycle_v150'] = _v234_json_clone(life)
        chats_out[str(cid)] = row
    return {'root': root, 'chats': chats_out}

# --- compat_legacy:0007 · from 02_transport_safety.py:2272 · public external_access_allowed_v233 ---
def _legacy_compat_s0007_external_access_allowed_v233(category: str='other_http') -> bool:
    """v246 Render-only means storage-only isolation, not an offline bot.

    Normal Telegram bot traffic, Google, FX and other user features stay available.
    Only the two remote backup contours (MEGA and Telegram backup-channel) are blocked.
    The tiny MEGA storage-control beacon is a control-plane exception so the next deploy
    can know which mode was selected before it restarted.
    """
    cat = str(category or 'other_http').strip().casefold()
    if cat in {'telegram', 'local', 'sqlite', 'memory', 'render_inbound', 'mega_control'}:
        return True
    if bool(globals().get('_V240_RECOVERY_AUTHORITY_ACTIVE', False)) and cat in {'mega', 'mega_put', 'mega_get', 'mega_critical', 'mega_backup', 'telegram_backup', 'telegram_durable'}:
        return True
    if not external_local_only_v233_enabled():
        return True
    return cat not in {'mega', 'mega_put', 'mega_get', 'mega_critical', 'mega_backup', 'telegram_backup', 'telegram_durable', 'backup_channel'}

# --- compat_legacy:0008 · from 05_finance_ui.py:1969 · public toggle_edit_delete_selection ---
def _legacy_compat_s0008_toggle_edit_delete_selection(chat_id: int, day_key: str, rid: int):
    store = get_chat_store(chat_id)
    all_sel = store.setdefault('edit_delete_selected', {})
    selected = set((int(x) for x in all_sel.get(day_key, [])))
    rid = int(rid)
    if rid in selected:
        selected.remove(rid)
    else:
        selected.add(rid)
    if selected:
        all_sel[day_key] = sorted(selected)
    else:
        all_sel.pop(day_key, None)
    save_data(data)

# --- compat_legacy:0009 · from 05_finance_ui.py:1984 · public clear_edit_delete_selection ---
def _legacy_compat_s0009_clear_edit_delete_selection(chat_id: int, day_key: str | None=None):
    store = get_chat_store(chat_id)
    all_sel = store.setdefault('edit_delete_selected', {})
    if day_key is None:
        all_sel.clear()
    else:
        all_sel.pop(day_key, None)
    save_data(data)

# --- compat_legacy:0010 · from 05_finance_ui.py:1993 · public update_record_in_chat ---
def _legacy_compat_s0010_update_record_in_chat(chat_id: int, rid: int, amount: float, note: str, source_finance_text: str | None=None, source_msg_id: int | None=None) -> bool:
    """Edit one finance row and persist the matching ARS/USD ledger mirror immediately.

    Normal edits target the active ledger by R-id.  💰Перес can additionally pass the bot-copy
    message id, which lets an old pre-deploy row be edited even when it currently lives in a
    non-active currency ledger with a colliding R-id.
    """
    bot_journal('record_update_start', chat_id, f"rid={rid} amount={amount} note={note} msg={source_msg_id or ''}")
    if globals().get('constitution_finance_write_blocked_v232') and constitution_finance_write_blocked_v232():
        return False
    chat_id = int(chat_id)
    rid = int(rid)
    op_id = operation_begin('finance_edit', chat_id, target=str(rid), payload={'amount': amount, 'note': note, 'source_msg_id': source_msg_id}, critical=True) if 'operation_begin' in globals() else ''
    store = get_chat_store(chat_id)
    active = _ensure_currency_ledgers(store)

    def _match(rec):
        if not isinstance(rec, dict):
            return False
        try:
            if int(rec.get('id', -1)) != rid:
                return False
        except Exception:
            return False
        return source_msg_id is None or _record_has_message_id(rec, int(source_msg_id))
    record_keys = ['records'] if source_msg_id is None else ['records', 'ars_records', 'usd_records']
    targets = []
    touched_ledgers = set()
    seen = set()
    for key in record_keys:
        for rec in store.get(key, []) or []:
            if not _match(rec):
                continue
            oid = id(rec)
            if oid in seen:
                continue
            seen.add(oid)
            targets.append((key, rec))
            if key == 'ars_records':
                touched_ledgers.add('ars')
            elif key == 'usd_records':
                touched_ledgers.add('usd')
            elif key == 'records':
                touched_ledgers.add(active)
    if not targets:
        if op_id and 'operation_review' in globals():
            operation_review(op_id, 'record not found')
        return False
    before_snapshot = copy.deepcopy(targets[0][1]) if targets else {}
    for _key, target in targets:
        target['amount'] = amount
        target['note'] = note
        if source_finance_text is not None:
            target['source_finance_text'] = str(source_finance_text or '').strip()
    daily_keys = ['daily_records'] if source_msg_id is None else ['daily_records', 'ars_daily_records', 'usd_daily_records']
    for dkey in daily_keys:
        for _dk, arr in (store.get(dkey, {}) or {}).items():
            for rec in arr or []:
                if not _match(rec):
                    continue
                rec['amount'] = amount
                rec['note'] = note
                if source_finance_text is not None:
                    rec['source_finance_text'] = str(source_finance_text or '').strip()
    store['balance'] = sum((float(r.get('amount', 0) or 0) for r in store.get('records', []) or []))
    for ledger in touched_ledgers:
        if ledger == active:
            continue
        store[f'{ledger}_balance'] = sum((float(r.get('amount', 0) or 0) for r in store.get(f'{ledger}_records', []) or []))
    _snapshot_active_currency_ledger(store, active)
    # R7: amount/note edit does not reorder records. Avoid full monthly/global
    # rebuild in the Telegram request path; derived aggregates run once later.
    try:
        for _key, _target in targets:
            ensure_finance_record_uid(chat_id, _target)
    except Exception:
        pass
    if 'persist_finance_chat_local_fast' in globals():
        persist_finance_chat_local_fast(chat_id)
    else:
        save_data(data, chat_ids=[chat_id])
    try:
        _dk = str((targets[0][1] if targets else {}).get('day_key') or store.get('current_view_day') or '')
        schedule_financial_window_refresh(chat_id, _dk, reason='record_edit_fast_v168')
    except Exception:
        pass
    try:
        schedule_finance_postcommit_background_v243(chat_id, reason='record_edit_r7', delay=0.25)
    except Exception:
        pass
    try:
        finance_cache_invalidate(chat_id, 'finance_edit')
        finance_integrity_append(chat_id, 'edit', targets[0][1] if targets else {'id': rid}, details={'before': before_snapshot})
    except Exception as _integrity_exc:
        log_error(f'finance edit integrity: {_integrity_exc}')
    if op_id and 'operation_complete' in globals():
        operation_complete(op_id, f'record={rid}')
    return True

# --- compat_legacy:0011 · from 05_finance_ui.py:3090 · public _nav_history_push_v248 ---
def _legacy_compat_s0011_nav_history_push_v248(key, snap: dict) -> bool:
    """R22 hot path: RAM first, KV durability later.

    Navigation history is UI continuity, so Redis/Key Value RTT must never be in
    front of a button.  The in-memory stack is authoritative for the live process;
    the remote copy is mirrored on the cleanup lane.
    """
    with _WINDOW_NAV_HISTORY_LOCK:
        stack = _WINDOW_NAV_HISTORY[key]
        if stack and stack[-1].get('text') == snap.get('text') and stack[-1].get('markup') == snap.get('markup'):
            return True
        stack.append(snap)
        if len(stack) > _WINDOW_NAV_HISTORY_LIMIT:
            del stack[:-_WINDOW_NAV_HISTORY_LIMIT]
    try:
        _R22_NAV_REMOTE_HAS[key] = True
    except Exception:
        pass

    def _mirror():
        push = globals().get('kv_nav_push_v248')
        if callable(push):
            try:
                push(int(key[0]), int(key[1]), dict(snap), _WINDOW_NAV_HISTORY_LIMIT)
            except Exception:
                pass
    try:
        pool = globals().get('UI_CLEANUP_TASK_POOL') or globals().get('BACKGROUND_TASK_POOL')
        if pool is not None:
            pool.submit(f'r22-nav-mirror:{int(key[0])}:{int(key[1])}', _mirror)
    except Exception:
        pass
    return True

# --- compat_legacy:0012 · from 05_finance_ui.py:3169 · public _nav_history_pop_v248 ---
def _legacy_compat_s0012_nav_history_pop_v248(key) -> bool:
    popped = False
    with _WINDOW_NAV_HISTORY_LOCK:
        stack = _WINDOW_NAV_HISTORY.get(key) or []
        if stack:
            stack.pop()
            popped = True
            if not stack:
                _WINDOW_NAV_HISTORY.pop(key, None)
    if not popped:
        return False

    # Mirror the pop after the UI commit; never wait for KV on a Back click.
    def _mirror_pop():
        fn = globals().get('kv_nav_pop_v248')
        if callable(fn):
            try:
                fn(int(key[0]), int(key[1]))
            except Exception:
                pass
    try:
        pool = globals().get('UI_CLEANUP_TASK_POOL') or globals().get('BACKGROUND_TASK_POOL')
        if pool is not None:
            pool.submit_unique(f'r72-nav-pop:{int(key[0])}:{int(key[1])}', _mirror_pop)
    except Exception:
        pass
    return True

# --- compat_legacy:0013 · from 05_finance_ui.py:3197 · public _nav_history_clear_v248 ---
def _legacy_compat_s0013_nav_history_clear_v248(chat_id: int, message_id: int) -> None:
    key = _window_nav_key(chat_id, message_id)
    with _WINDOW_NAV_HISTORY_LOCK:
        _WINDOW_NAV_HISTORY.pop(key, None)
    _R22_NAV_REMOTE_HAS.pop(key, None)
    fn = globals().get('kv_nav_clear_v248')
    if callable(fn):
        try:
            fn(int(chat_id), int(message_id))
        except Exception:
            pass

# --- compat_legacy:0014 · from 05_finance_ui.py:3209 · public r27_callback_is_back_navigation ---
def _legacy_compat_s0014_r27_callback_is_back_navigation(call, data_str: str) -> bool:
    """True for a user-visible Back button (not backup operations).

    We inspect both callback token and the text of the clicked button. This lets old
    windows keep their historical callback names while R27 gives all Back buttons the
    same navigation semantics: previous window first, legacy fallback second.
    """
    raw = str(data_str or '').strip()
    low = raw.casefold()
    if 'backup' in low:
        return False
    if low == 'nav_prev' or low.endswith(':back_main'):
        return True
    normalized = low.replace(':', '_').replace('-', '_')
    parts = [x for x in normalized.split('_') if x]
    if 'back' in parts or low.startswith('back_') or low.endswith('_back'):
        return True
    try:
        markup = getattr(getattr(call, 'message', None), 'reply_markup', None)
        for row in list(getattr(markup, 'keyboard', None) or []):
            for btn in row or []:
                if str(getattr(btn, 'callback_data', '') or '') != raw:
                    continue
                label = str(getattr(btn, 'text', '') or '').casefold()
                if 'назад' in label:
                    return True
    except Exception:
        pass
    return False

# --- compat_legacy:0015 · from 05_finance_ui.py:3276 · public window_has_previous ---
def _legacy_compat_s0015_window_has_previous(chat_id: int, message_id: int) -> bool:
    """Non-blocking R22 check. Never contacts Redis on the render hot path."""
    key = _window_nav_key(chat_id, message_id)
    with _WINDOW_NAV_HISTORY_LOCK:
        if bool(_WINDOW_NAV_HISTORY.get(key)):
            return True
    if bool(_R22_NAV_REMOTE_HAS.get(key, False)):
        return True
    # One background prefetch is allowed for post-restart continuity. Its result
    # can affect the next render, never the current button latency.
    if key not in _R22_NAV_REMOTE_PREFETCH:
        _R22_NAV_REMOTE_PREFETCH.add(key)
        def _prefetch():
            try:
                fn = globals().get('kv_nav_has_v248')
                if callable(fn):
                    _R22_NAV_REMOTE_HAS[key] = bool(fn(int(key[0]), int(key[1])))
            except Exception:
                pass
            finally:
                _R22_NAV_REMOTE_PREFETCH.discard(key)
        try:
            pool = globals().get('UI_CLEANUP_TASK_POOL') or globals().get('BACKGROUND_TASK_POOL')
            if pool is not None:
                pool.submit_unique(f'r22-nav-has:{int(key[0])}:{int(key[1])}', _prefetch)
        except Exception:
            _R22_NAV_REMOTE_PREFETCH.discard(key)
    return False

# --- compat_legacy:0016 · from 06_commands_callbacks.py:4156 · public _v258_record_strong_keys ---
def _legacy_compat_s0016_v258_record_strong_keys(rec: dict, chat_id: int) -> list[str]:
    """Stable keys that prove two finance rows are the same Telegram effect.

    Deliberately excludes source_order_msg_id: forwarded copies may legitimately
    share an upstream order id while being different messages in this chat.
    """
    out = []
    try:
        op = str((rec or {}).get('operation_key') or '').strip()
        if op and op.startswith(f'finance:{int(chat_id)}:'):
            out.append('op:' + op)
    except Exception:
        pass
    for key in ('source_msg_id', 'origin_msg_id', 'msg_id'):
        try:
            mid = int((rec or {}).get(key) or 0)
            if mid:
                out.append(f'msg:{mid}')
        except Exception:
            pass
    return list(dict.fromkeys(out))

# --- compat_legacy:0017 · from 06_commands_callbacks.py:4181 · public normalize_chat_records ---
def _legacy_compat_s0017_normalize_chat_records(chat_id: int) -> None:
    """
    v258: records — основной источник, daily_records строится из него.
    Сортировка стабильная: Telegram date + исходный message_id. Исторические
    дубли одной Telegram-записи после deploy/edit схлопываются по сильной
    идентичности, но независимые одинаковые суммы/описания не объединяются.
    """
    store = get_chat_store(chat_id)
    records = store.get('records')
    daily = store.get('daily_records') or {}
    if not isinstance(records, list) or not records:
        rebuilt = []
        for dk in sorted(daily.keys()):
            for rec in daily.get(dk, []) or []:
                if isinstance(rec, dict):
                    rec.setdefault('day_key', dk)
                    rebuilt.append(rec)
        records = rebuilt
    try:
        records, _v258_removed = _v258_merge_duplicate_finance_records(int(chat_id), list(records or []))
    except Exception as _v258_dedupe_exc:
        _v258_removed = 0
        try: log_error(f'v258 finance duplicate migration {chat_id}: {_v258_dedupe_exc}')
        except Exception: pass
    clean = []
    for rec in records or []:
        if not isinstance(rec, dict):
            continue
        rec.setdefault('timestamp', now_local().isoformat(timespec='seconds'))
        rec.setdefault('amount', 0)
        rec.setdefault('note', '')
        rec.setdefault('owner', '')
        rec.setdefault('source_order_msg_id', rec.get('source_msg_id') or rec.get('origin_msg_id') or rec.get('msg_id') or rec.get('id') or 0)
        _record_day_key(rec)
        try:
            if 'ensure_finance_record_uid' in globals():
                ensure_finance_record_uid(int(chat_id), rec)
        except Exception:
            pass
        clean.append(rec)
    clean.sort(key=record_sort_key)
    store['records'] = clean
    rebuilt_daily = {}
    for rec in clean:
        rebuilt_daily.setdefault(_record_day_key(rec), []).append(rec)
    store['daily_records'] = rebuilt_daily
    if _v258_removed:
        try:
            store['balance'] = sum((float(r.get('amount', 0) or 0) for r in clean))
            store['next_id'] = max([int(r.get('id', 0) or 0) for r in clean] + [0]) + 1
            store['_finance_dedupe_v258_removed'] = int(store.get('_finance_dedupe_v258_removed') or 0) + int(_v258_removed)
            if 'migrate_finance_source_index_v257' in globals():
                migrate_finance_source_index_v257(int(chat_id))
            bot_journal('finance_duplicate_collapsed_v258', int(chat_id), f'removed={int(_v258_removed)}')
        except Exception as _v258_post_exc:
            try: log_error(f'v258 finance duplicate post-normalize {chat_id}: {_v258_post_exc}')
            except Exception: pass

# --- compat_legacy:0018 · from 06_commands_callbacks.py:4457 · public schedule_full_backup_only ---
def _legacy_compat_s0018_schedule_full_backup_only(chat_id: int, delay: float=3.0):
    """Тяжёлый JSON/канал/MEGA-файл чата — отдельно от быстрого delta."""
    chat_id = int(chat_id)
    if RESTORE_GUARD_ACTIVE:
        log_error(f'FULL BACKUP SCHEDULE BLOCKED {chat_id}: {RESTORE_GUARD_REASON}')
        return
    try:
        delay = max(float(delay or 0), BACKUP_MIN_DELAY_SECONDS)
    except Exception:
        delay = BACKUP_MIN_DELAY_SECONDS
    due = time.time() + delay
    expected_epoch = int(globals().get('_V241_STORAGE_EPOCH', 0) or 0)
    with timer_lock:
        _backup_dirty_chats.add(chat_id)
        _backup_timers[chat_id] = due

    def _fire():
        with timer_lock:
            _backup_timers.pop(chat_id, None)
        if expected_epoch != int(globals().get('_V241_STORAGE_EPOCH', 0) or 0) or globals().get('_V241_RESTORE_ACTIVE', False):
            with timer_lock:
                _backup_dirty_chats.discard(chat_id)
            return
        if not BACKUP_TASK_POOL.submit(f'full:{chat_id}', _run_full_chat_backup, chat_id, expected_epoch):
            log_error(f'FULL BACKUP QUEUE FULL, RETRY: {chat_id}')
            schedule_full_backup_only(chat_id, BACKUP_BUSY_RETRY_SECONDS)
    DELAYED_SCHEDULER.cancel(f'full-backup:{chat_id}')
    DELAYED_SCHEDULER.schedule(f'full-backup:{chat_id}', delay, _fire)

# --- compat_legacy:0019 · from 07_state_web.py:6509 · public add_record_to_chat ---
def _legacy_compat_s0019_add_record_to_chat(chat_id: int, amount: float, note: str, owner: int, source_msg=None, day_key=None, usd_amount=None, usd_note: str='', usd_only: bool=False, source_finance_text: str=''):
    rec = _V151_BASE_ADD_RECORD(chat_id, amount, note, owner, source_msg=source_msg, day_key=day_key, usd_amount=usd_amount, usd_note=usd_note, usd_only=usd_only, source_finance_text=source_finance_text)
    if isinstance(rec, dict):
        try:
            ensure_finance_record_uid(int(chat_id), rec)
        except Exception:
            pass
        currencies = ['ars']
        if usd_amount is not None:
            currencies.append('usd')
        _v151_schedule_postcommit_cover(int(chat_id), rec, currencies)
    return rec

# --- compat_legacy:0020 · from 08_reliability_tasks.py:13737 · public v227_render_effective_contour_markup ---
def _legacy_compat_s0020_v227_render_effective_contour_markup(source_markup, text: str, chat_id: int):
    """Build the exact Telegram markup from the canonical source, then apply final visibility.

    v226 could remember a pre-augmentation keyboard while Telegram actually received a later
    augmented keyboard.  Keeping source+delivered separately makes OFF removal and ON restore
    symmetric and prevents the live refresh from comparing against the wrong snapshot.
    """
    cid = int(chat_id or 0)
    try:
        kb = _v221_copy.deepcopy(source_markup)
    except Exception:
        kb = source_markup
    try:
        augment = globals().get('_v160_augment_markup')
        if callable(augment):
            kb = augment(kb, str(text or ''), cid)
    except Exception:
        pass
    try:
        return v221_finalize_contour_markup(kb, cid)
    except Exception:
        return kb

# --- compat_legacy:0021 · from 09_final_transport.py:1910 · public circle_annotation_button_enabled_v219 ---
def _legacy_compat_s0021_circle_annotation_button_enabled_v219(kind: str, chat_id: int | None=None) -> bool:
    key = 'iz_mr' if str(kind or '').replace('-', '_').casefold() in {'iz_mr', 'izmr', 'marker'} else 'tz'
    base = bool(_v219_annotation_settings().get(key, True))
    if chat_id is None or not base:
        return base
    fn = globals().get('annotation_effective_v229')
    if callable(fn):
        try:
            return bool(fn(key, int(chat_id)))
        except Exception:
            pass
    try:
        cid = int(chat_id)
        if not _v215_circle_business_chat(cid):
            return base
        directive_fn = globals().get('directive_chat_enabled_v223')
        local_fn = globals().get('directive_annotation_allowed_v223')
        if callable(directive_fn) and directive_fn(cid) and callable(local_fn):
            return bool(base and local_fn(cid, key))
    except Exception:
        pass
    return base

# --- compat_legacy:0022 · from 09_final_transport.py:2135 · public circle_annotation_global_enabled_v219 ---
def _legacy_compat_s0022_circle_annotation_global_enabled_v219(kind: str, chat_id: int | None=None) -> bool:
    key = 'iz_mr' if str(kind or '').replace('-', '_').casefold() in {'iz_mr', 'izmr', 'marker'} else 'tz'
    if chat_id is not None:
        try:
            if not _v215_circle_business_chat(int(chat_id)):
                return True
        except Exception:
            return True
    return bool(_v219_annotation_settings().get(key, True))

# --- compat_legacy:0023 · from 09_final_transport.py:2347 · public annotation_visibility_state_v226 ---
def _legacy_compat_s0023_annotation_visibility_state_v226(kind: str, chat_id: int) -> dict:
    cid = int(chat_id)
    key = 'iz_mr' if str(kind or '').replace('-', '_').casefold() in {'iz_mr', 'izmr', 'marker'} else 'tz'
    try:
        global_on = bool(circle_annotation_global_enabled_v219(key, cid))
    except Exception:
        global_on = bool(_v219_annotation_settings().get(key, True))
    try:
        directive = bool(directive_chat_enabled_v223(cid))
    except Exception:
        directive = False
    local_on = True
    if directive:
        try:
            local_on = bool(directive_annotation_allowed_v223(cid, key))
        except Exception:
            local_on = True
    try:
        circle = bool(_v215_circle_business_chat(cid))
    except Exception:
        circle = False
    return {'kind': key, 'circle': circle, 'global': global_on, 'directive': directive, 'local': local_on, 'effective': bool(global_on and local_on)}

# --- compat_legacy:0024 · from 09_final_transport.py:5817 · public _final_filter_markup ---
def _legacy_compat_s0024_final_filter_markup(chat_id, reply_markup, stage='final_filter', message_id=None):
    prepared = reply_markup
    try:
        fn = globals().get('v221_final_reply_markup')
        if callable(fn):
            prepared = fn(int(chat_id), prepared)
    except Exception:
        pass
    # R75 HARD FENCE: this is deliberately below every legacy/profile/restore/
    # markup-only path.  No Telegram mutation can bypass the four OFF switches.
    try:
        fence = globals().get('_r75_transport_feature_fence')
        if callable(fence):
            prepared = fence(prepared, int(chat_id), stage=str(stage or 'final_filter'), message_id=message_id)
    except Exception:
        pass
    return prepared

# --- compat_legacy:0025 · from 09_final_transport.py:5836 · public _final_prepare_markup ---
def _legacy_compat_s0025_final_prepare_markup(chat_id, reply_markup, text='', stage='prepare', message_id=None):
    prepared = reply_markup
    try:
        fn = globals().get('v227_render_effective_contour_markup')
        if callable(fn):
            prepared = fn(int(chat_id), prepared, text=str(text or ''))
        else:
            fn = globals().get('_v160_augment_markup')
            if callable(fn):
                prepared = fn(prepared, str(text or ''), int(chat_id))
    except Exception:
        prepared = reply_markup
    return _final_filter_markup(chat_id, prepared, stage=stage, message_id=message_id)

# --- compat_legacy:0026 · from 10_split_policy_offload.py:792 · public _split_send_delta_v267 ---
def _legacy_compat_s0026_split_send_delta_v267(reason='change'):
    base, secret = _split_peer_base(), _split_secret()
    if not base or not secret:
        return False, 'worker URL/secret not configured', False
    payload,current,workdir,fallback = _split_build_delta_v267(reason)
    if payload is None:
        if workdir:
            _split_shutil.rmtree(workdir, ignore_errors=True)
        return False, fallback or 'delta unavailable', True
    try:
        wire=payload.pop('_wire_gzip', None)
        if wire is None:
            wire=_split_gzip.compress(_split_json.dumps(payload,separators=(',',':')).encode('utf-8'),compresslevel=9)
        r=requests.post(base+'/internal/delta',data=wire,headers={**_split_headers('vys-262-front-delta-r12'),'Content-Type':'application/json','Content-Encoding':'gzip'},timeout=15)
        if 200 <= r.status_code < 300:
            body={}
            try: body=r.json() if r.content else {}
            except Exception: body={}
            status=str(body.get('status') or 'applied')
            if status in {'applied','up_to_date','noop'}:
                _split_promote_delta_baseline_v267(current)
                _SPLIT_STATE['delta_last_ok']=_split_time.time()
                _SPLIT_STATE['delta_last_error']=''
                _SPLIT_STATE['delta_last_bytes']=len(wire)
                _SPLIT_STATE['delta_last_pages']=len(payload.get('pages') or [])
                _SPLIT_STATE['delta_total_bytes']=int(_SPLIT_STATE.get('delta_total_bytes') or 0)+len(wire)
                _SPLIT_STATE['delta_total_pages']=int(_SPLIT_STATE.get('delta_total_pages') or 0)+len(payload.get('pages') or [])
                _split_ack_mirrored_events_v268(payload.get('event_ids') or [])
                return True,status,False
        if r.status_code in {409, 412, 422}:
            return False, f'worker requests full: HTTP {r.status_code} {r.text[:180]}', True
        return False,f'HTTP {r.status_code}: {r.text[:180]}',False
    except Exception as exc:
        return False,f'{type(exc).__name__}: {str(exc)[:180]}',False
    finally:
        if workdir:
            _split_shutil.rmtree(workdir, ignore_errors=True)

# --- compat_legacy:0027 · from 10_split_policy_offload.py:923 · public split_witness_event_v268 ---
def _legacy_compat_s0027_split_witness_event_v268(update_id, payload, chat_id=None, update_type='other'):
    """R57: keep Redis completely out of the Telegram hot path.

    FAST sends the small raw-update witness only to HEAVY. HEAVY owns any optional
    Redis mirroring/cache work in background. This means turning Redis ON from the
    Info menu cannot add Redis network latency to a button or message callback.
    """
    row=_split_event_row_v268(update_id,payload,chat_id,update_type)
    base,secret=_split_peer_base(),_split_secret(); detail='worker not configured'
    if base and secret:
        try:
            raw=_split_json.dumps(row,ensure_ascii=False,separators=(',',':'),default=str).encode('utf-8')
            wire=_split_gzip.compress(raw,compresslevel=1)
            r=requests.post(base+'/internal/event/receipt',data=wire,headers={**_split_headers('vys-262-front-event-r57'),'Content-Type':'application/json','Content-Encoding':'gzip'},timeout=max(0.35,min(2.5,float(_split_os.getenv('SPLIT_EVENT_RECEIPT_TIMEOUT_SEC','1.2') or '1.2'))))
            if 200 <= r.status_code < 300:
                _SPLIT_STATE['event_last_receipt_ok']=_split_time.time(); _SPLIT_STATE['event_last_error']=''
                _SPLIT_STATE['event_received']=int(_SPLIT_STATE.get('event_received') or 0)+1
                return True
            detail=f'worker HTTP {r.status_code}: {r.text[:160]}'
        except Exception as exc:
            detail=f'worker {type(exc).__name__}: {str(exc)[:160]}'
    _SPLIT_STATE['event_last_error']=detail[:260]
    return False

# --- compat_legacy:0028 · from 10_split_policy_offload.py:947 · public _split_event_status_send_v268 ---
def _legacy_compat_s0028_split_event_status_send_v268(update_id, chat_id=None, update_type='other', success=True, error=''):
    """R57: commit witness also goes through HEAVY; FAST never blocks on Redis."""
    event_id=_split_event_id_v268(update_id)
    row={'schema':1,'event_id':event_id,'update_id':str(update_id),'chat_id':chat_id,'update_type':str(update_type or 'other')[:40],
         'state':'committed' if success else 'failed_retry','committed_at':_split_time.time() if success else 0.0,
         'state_token':_split_current_state_token_v265(),'last_error':str(error or '')[:300]}
    base,secret=_split_peer_base(),_split_secret(); detail='worker not configured'
    if base and secret:
        try:
            r=requests.post(base+'/internal/event/commit',json=row,headers=_split_headers('vys-262-front-event-commit-r57'),timeout=4)
            if 200 <= r.status_code < 300:
                if success:
                    _SPLIT_STATE['event_last_commit_ok']=_split_time.time(); _SPLIT_STATE['event_committed']=int(_SPLIT_STATE.get('event_committed') or 0)+1
                _SPLIT_STATE['event_last_error']=''
                return True
            detail=f'worker HTTP {r.status_code}: {r.text[:160]}'
        except Exception as exc:
            detail=f'worker {type(exc).__name__}: {str(exc)[:160]}'
    _SPLIT_STATE['event_last_error']=detail[:260]
    return False

# --- compat_legacy:0029 · from 10_split_policy_offload.py:1542 · public _split_request_worker_full_sync_r18 ---
def _legacy_compat_s0029_split_request_worker_full_sync_r18(reason='need_full'):
    """Queue a full rebase on HEAVY; FAST never waits for snapshot/MEGA work."""
    base, secret = _split_peer_base(), _split_secret()
    if not base or not secret:
        return False, 'worker URL/secret not configured'
    try:
        body = {'type':'sync_state', 'reason':str(reason or 'need_full')[:160], 'state_token':_split_current_state_token_v265()}
        r = requests.post(base + '/internal/job', json=body, headers=_split_headers('vys-262-front-r18-rebase'), timeout=2.5)
        if 200 <= r.status_code < 300:
            return True, f'worker full rebase queued HTTP {r.status_code}'
        return False, f'worker full rebase HTTP {r.status_code}: {r.text[:160]}'
    except Exception as exc:
        return False, f'{type(exc).__name__}: {str(exc)[:160]}'

# --- compat_legacy:0030 · from 10_split_policy_offload.py:1607 · public split_schedule_worker_sync_v262 ---
def _legacy_compat_s0030_split_schedule_worker_sync_v262(reason='change', delay=None):
    """Coalesced state handoff; Telegram never waits for MEGA or snapshot transfer."""
    global _SPLIT_SYNC_TIMER, _SPLIT_SYNC_DUE_AT, _SPLIT_SYNC_FIRST_DIRTY_AT
    if not _split_env_bool('SPLIT_WORKER_SYNC_ENABLED', True):
        return False
    # One Telegram update may call save_data/config/finance hooks many times. R4
    # could arm the worker while the handler was still executing, then arm it again
    # at the post-update continuity checkpoint. Defer all those requests and emit
    # exactly one notification after the update completes.
    if _split_inside_telegram_update_v265():
        _SPLIT_STATE['sync_pending'] = True
        _SPLIT_STATE['sync_reason'] = str(reason or 'change')[:160]
        return True
    try:
        wait = float(delay if delay is not None else _split_os.getenv('SPLIT_STATE_SYNC_DELAY_SEC', '8') or '8')
    except Exception:
        wait = 1.5
    try:
        min_interval = float(_split_os.getenv('SPLIT_STATE_SYNC_MIN_INTERVAL_SEC', '30') or '30')
    except Exception:
        min_interval = 12.0
    wait = max(0.08, min(30.0, wait))
    min_interval = max(0.2, min(120.0, min_interval))
    # R15: RAW events are already remotely witnessed.  State mirroring may therefore
    # debounce short finance bursts instead of snapshotting/gzipping on every message.
    _reason_l = str(reason or '').lower()
    if 'finance' in _reason_l or 'critical' in _reason_l or 'event_commit' in _reason_l:
        wait = max(wait, 0.8)
        min_interval = max(min_interval, 1.5)
    now = _split_time.time()
    last = float(_SPLIT_STATE.get('sync_last_attempt') or 0.0)
    with _SPLIT_SYNC_LOCK:
        if _SPLIT_SYNC_FIRST_DIRTY_AT <= 0.0:
            _SPLIT_SYNC_FIRST_DIRTY_AT = now
        first_dirty = _SPLIT_SYNC_FIRST_DIRTY_AT
    try:
        max_latency = max(1.0, min(12.0, float(_split_os.getenv('SPLIT_SYNC_MAX_LATENCY_SEC','60') or '60')))
    except Exception:
        max_latency = 3.0
    due = max(now + wait, last + min_interval if last else now + wait)
    due = min(due, first_dirty + max_latency)
    due = max(now + 0.05, due)
    _SPLIT_STATE['sync_pending'] = True
    _SPLIT_STATE['sync_reason'] = str(reason or 'change')[:160]
    with _SPLIT_SYNC_LOCK:
        # R15 trailing-edge debounce: a burst of ten messages produces one mirror
        # attempt after the burst, not ten competing SQLite backups.
        if _SPLIT_SYNC_TIMER is not None:
            try:
                _SPLIT_SYNC_TIMER.cancel()
            except Exception:
                pass
        _SPLIT_SYNC_DUE_AT = due
        _SPLIT_SYNC_TIMER = _split_threading.Timer(max(0.05, due - now), _split_sync_timer_fire)
        _SPLIT_SYNC_TIMER.daemon = True
        _SPLIT_SYNC_TIMER.start()
    return True

# --- compat_legacy:0031 · from 10_split_policy_offload.py:2349 · public _r20_capsule_push_now ---
def _legacy_compat_s0031_r20_capsule_push_now(reason='state_change'):
    global _R20_CAPSULE_LAST_GEN_SENT, _R20_CAPSULE_LAST_SEQ_SENT
    _SPLIT_STATE['capsule_last_attempt'] = _split_time.time()
    try:
        payload = _r20_capsule_build(reason)
        raw = _split_json.dumps(payload, ensure_ascii=False, separators=(',',':'), default=str).encode('utf-8')
        packed = _split_gzip.compress(raw, compresslevel=3)
        max_bytes = 8 * 1024 * 1024
        if len(packed) > max_bytes:
            raise RuntimeError(f'capsule too large: {len(packed)}')
        seq = int(payload.get('user_state_seq') or 0); gen = int(payload.get('config_generation') or 0)
        worker_ok=False; worker_detail='HEAVY peer not configured'
        base, secret = _split_peer_base(), _split_secret()
        if base and secret:
            try:
                r=requests.post(base + '/internal/capsule', data=packed,
                    headers={**_split_headers('och12-front-capsule'), 'Content-Type':'application/json', 'Content-Encoding':'gzip'}, timeout=3.0)
                worker_ok = 200 <= r.status_code < 300
                worker_detail = f'HTTP {r.status_code}' if worker_ok else f'HTTP {r.status_code}: {r.text[:120]}'
            except Exception as exc:
                worker_detail=f'{type(exc).__name__}: {str(exc)[:140]}'
        redis_ok, redis_detail = _r20_capsule_store_redis(payload, packed)
        _SPLIT_STATE['capsule_redis_cache_ok']=bool(redis_ok)
        _SPLIT_STATE['capsule_redis_cache_detail']=str(redis_detail)[:180]
        if worker_ok:
            _R20_CAPSULE_LAST_GEN_SENT=max(_R20_CAPSULE_LAST_GEN_SENT,gen); _R20_CAPSULE_LAST_SEQ_SENT=max(_R20_CAPSULE_LAST_SEQ_SENT,seq)
            _SPLIT_STATE['capsule_last_ok']=_split_time.time(); _SPLIT_STATE['capsule_last_error']=''
            _SPLIT_STATE['capsule_last_seq']=seq; _SPLIT_STATE['capsule_last_generation']=gen
            return True
        _SPLIT_STATE['capsule_last_error']=f'heavy={worker_detail}; redis-cache={redis_detail}'[:240]
    except Exception as exc:
        _SPLIT_STATE['capsule_last_error']=f'{type(exc).__name__}: {str(exc)[:220]}'
        try: log_error('OCH12 capsule: '+_SPLIT_STATE['capsule_last_error'])
        except Exception: pass
    return False

# --- compat_legacy:0032 · from 10_split_policy_offload.py:2616 · public _split_schedule_idle_full_reconcile_v270 ---
def _legacy_compat_s0032_split_schedule_idle_full_reconcile_v270(reason='need_full', delay=None):
    global _SPLIT_FULL_TIMER
    wait = float(delay if delay is not None else _split_os.getenv('R28_FULL_SNAPSHOT_USER_QUIET_SEC','30') or '20')
    with _SPLIT_FULL_LOCK:
        if _SPLIT_FULL_TIMER is not None:
            try: _SPLIT_FULL_TIMER.cancel()
            except Exception: pass
        _SPLIT_FULL_TIMER = _split_threading.Timer(max(5.0, wait), _split_idle_full_reconcile_fire_v270, args=(str(reason or 'need_full'),))
        _SPLIT_FULL_TIMER.daemon = True
        _SPLIT_FULL_TIMER.start()
    _SPLIT_STATE['full_reconcile_pending'] = True
    return True

# --- compat_legacy:0033 · from 10_split_policy_offload.py:3319 · public _r70_routes_text ---
def _legacy_compat_s0033_r70_routes_text():
    h=dict(_SPLIT_STATE.get('worker_health') or {});st=dict(h.get('state') or {})
    worker_ok=bool(h.get('ok')) and int(_SPLIT_STATE.get('peer_status') or 0) in range(200,300)
    try:
        wa_stats = dict(WINDOW_ACTOR_REGISTRY.stats() or {})
    except Exception:
        wa_stats = {}
    lines=[
        f'🧭 <b>{BOT_DISPLAY_NAME} · ВЛАДЕЛЬЦЫ ПРОЦЕССОВ R1/R2</b>','',
        '🔒 Telegram webhook / callback ACK — <b>R1 FAST</b>',
        '🔒 Telegram окна / кнопки — <b>R1 FAST</b>',
        '🔒 Реальная доставка пересылки — <b>R1 FAST</b>',
        '🔒 Canonical business mutation — <b>R1 FAST</b>',
        '🛰 Google / тяжёлые таблицы — <b>R2 HEAVY</b>',
        '🛰 File export / тяжёлая генерация — <b>R2 HEAVY</b>',
        '🛰 MEGA runtime heavy jobs — <b>R2 HEAVY</b>',
        '🔁 State events / delta — <b>R1 → R2</b>',
        '🧪 Диагностика — <b>R1 инициирует, R2 исполняет</b>','',
        f'R2 сейчас: {"✅ доступен" if worker_ok else "⛔ недоступен"} · очередь {int(h.get("queue_size") or 0)} · Google {int(h.get("google_queue_size") or 0)}',
        f'События R2: received {int(st.get("event_received") or 0)} · commit {int(st.get("event_committed") or 0)} · pending {int(st.get("event_pending") or 0)}',
        f'Window Actor: окон {int(wa_stats.get("windows") or 0)} · markup-only {int(wa_stats.get("markup_only") or 0)} · no-op {int(wa_stats.get("noops") or 0)} · stale render {int(wa_stats.get("stale_renders") or 0)} · stale callback {int(wa_stats.get("stale_callbacks") or 0)}','',
        f'{BOT_DISPLAY_NAME} намеренно не разрешает переключать Telegram UI/forward delivery на R2: у этих путей должен быть ровно один владелец, иначе снова возможны дубли окон/сообщений.',
        'Для сравнения R1↔R2 используйте 🧪 Тест #1 ↔ #2 и E2E.'
    ]
    return window_mark('\n'.join(lines),'Ф4072')

# --- compat_legacy:0034 · from 10_split_policy_offload.py:3345 · public _r70_routes_keyboard ---
def _legacy_compat_s0034_r70_routes_keyboard():
    kb=types.InlineKeyboardMarkup(row_width=2)
    kb.row(IB('🧪 Тест #1 ↔ #2',callback_data='r44:test:open'),IB('🔄 Render #2',callback_data='r10:worker:refresh'))
    kb.row(IB('🔙 Render #2',callback_data='r10:worker:status'),IB('❌ Закрыть',callback_data='info_close'))
    return kb

# --- compat_legacy:0035 · from 10_split_policy_offload.py:4604 · public _r49_info_inject_redis_toggle ---
def _legacy_compat_s0035_r49_info_inject_redis_toggle(kb, chat_id: int):
    if int(chat_id) != int(OWNER_ID or 0):
        return kb
    try:
        rows_fn = globals().get('_v177_info_rows')
        set_fn = globals().get('_v177_info_set_rows')
        rows = list(rows_fn(kb) or []) if callable(rows_fn) else list(getattr(kb, 'keyboard', None) or [])
        remove_callbacks={'r49:redis:toggle','r60:redis:menu','r60:redis:inspect:0','r59:vars:render:0','r59:vars:code:0'}
        rows = [list(row or []) for row in rows if not any(_r29_button_callback(b) in remove_callbacks for b in (row or []))]
        insert_at = len(rows)
        for i, row in enumerate(rows):
            if any((_r29_button_callback(b) in {'info_close', 'aux_close', 'nav_prev'} or 'назад' in _r29_button_text(b).casefold()) for b in (row or [])):
                insert_at = i
                break
        rows.insert(insert_at, [IB('🌐 Render ENV', callback_data='r59:vars:render:0'), IB('🧩 Код/runtime', callback_data='r59:vars:code:0')])
        rows.insert(insert_at + 1, [_r49_redis_button(),IB('🧠 Redis: содержимое',callback_data='r60:redis:inspect:0')])
        if callable(set_fn):
            return set_fn(kb, rows)
        setattr(kb, 'keyboard', rows)
    except Exception:
        try:
            kb.row(IB('🌐 Render ENV', callback_data='r59:vars:render:0'), IB('🧩 Код/runtime', callback_data='r59:vars:code:0'))
            kb.row(_r49_redis_button(),IB('🧠 Redis: содержимое',callback_data='r60:redis:inspect:0'))
        except Exception: pass
    return kb

# --- compat_legacy:0036 · from 10_split_policy_offload.py:5628 · public _r34_post_events ---
def _legacy_compat_s0036_r34_post_events(events,wire,large=False):
    """12.27 durability: canonical MEGA normally required; uncertain empty boot is local-safe mode."""
    if not _r71_route_is_fast('durability'):
        return _R80_HEAVY_POST_EVENTS(events,wire,large=large)
    # OCH12.31: there is no permanent empty-boot MEGA write fence.  Redis remains
    # a cache, while canonical MEGA durability resumes as soon as MEGA is reachable.
    redis_ok=False; redis_detail='cache disabled'
    try: redis_ok,redis_detail=_r43_store_events_redis(events)
    except Exception as exc: redis_detail=f'{type(exc).__name__}: {str(exc)[:160]}'
    max_rev=max([int((x or {}).get('revision') or 0) for x in (events or [])] or [0])
    with _R80_MEGA_LOCK:
        for ev in (events or []):
            if _r80_compact_event_valid(ev):
                eid=str(ev.get('event_id') or '')
                if eid: _R80_MEGA_TAIL_EVENTS[eid]=ev
        _R80_MEGA_STATE['tail_dirty']=True
        covered=int(_R80_MEGA_STATE.get('tail_max_revision') or 0)
    if covered<max_rev:
        ok,detail=_r80_flush_compact_tail('durability-ack')
        if not ok: raise RuntimeError('MEGA canonical tail pending: '+str(detail)[:180])
        with _R80_MEGA_LOCK: covered=int(_R80_MEGA_STATE.get('tail_max_revision') or 0)
    if covered<max_rev: raise RuntimeError(f'MEGA canonical tail incomplete covered={covered} required={max_rev}')
    _R32_EVENT_STATE['last_revision_acked']=max(int(_R32_EVENT_STATE.get('last_revision_acked') or 0),max_rev)
    _R32_EVENT_STATE['last_revision_applied_peer']=max(int(_R32_EVENT_STATE.get('last_revision_applied_peer') or 0),max_rev)
    _R32_EVENT_STATE['sent']=int(_R32_EVENT_STATE.get('sent') or 0)+len(events or [])
    _R32_EVENT_STATE['batches']=int(_R32_EVENT_STATE.get('batches') or 0)+1
    _R32_EVENT_STATE['last_ok']=_r32_time.time(); _R32_EVENT_STATE['last_error']=''
    _R32_EVENT_STATE['redis_cache_ok']=bool(redis_ok); _R32_EVENT_STATE['redis_cache_detail']=str(redis_detail)[:180]
    st=globals().get('_SPLIT_STATE')
    if isinstance(st,dict):
        st['r34_event_last_revision_acked']=max_rev; st['r35_event_last_revision_applied_peer']=max_rev
        st['r80_failover_durability']='MEGA_CANONICAL_V126'; st['redis_event_cache_ok']=bool(redis_ok)
    return True

# --- compat_legacy:0037 · from 10_split_policy_offload.py:5792 · public _split_push_snapshot_now_v263 ---
def _legacy_compat_s0037_split_push_snapshot_now_v263(reason='shutdown',sync_mega=False):
    if not _OCH1226_MEGA_DURABILITY_ENABLED: return True
    if not (_r71_route_is_fast('checkpoints') or _r71_route_is_fast('mega')):
        return _R80_HEAVY_PUSH_SNAPSHOT(reason,sync_mega=sync_mega)
    if not _r80_mega_master_enabled(): return False
    if bool(sync_mega):
        ok,_detail=_r80_snapshot_full_compact('sync-'+str(reason or 'snapshot')[:80]); return bool(ok)
    return bool(_r80_queue_compact_full('snapshot-'+str(reason or '')[:80]))

# --- compat_legacy:0038 · from 10_split_policy_offload.py:5952 · public _r33_remote_file_adapter ---
def _legacy_compat_s0038_r33_remote_file_adapter(kind,label,func_name,args,kwargs):
    # R34: never wait for global state synchronization on FAST.  The job carries a
    # revision fence and HEAVY waits for only the state it actually needs.
    body=_r33_export_body(str(kind),str(label),str(func_name),args,kwargs)
    try: _file_job_progress('передаю задание Render #2', force=True)
    except Exception: pass
    submit=globals().get('_r7_worker_file_submit')
    if not callable(submit): raise RuntimeError('R38 HEAVY export bridge unavailable')
    jid=submit(body)
    try: bot_journal('r35_heavy_file_accepted_legacy_guard',int(body.get('recipient_chat_id') or 0),f"kind={kind}; op={body.get('operation')}; job={jid}; required_revision={body.get('required_revision') or 0}")
    except Exception: pass
    # R35 intentionally does NOT mark accepted/queued as delivered here. The final
    # adapter defined below waits for the real FAST delivery callback.
    return True

# --- compat_legacy:0039 · from 10_split_policy_offload.py:6195 · public _r33_remote_file_adapter ---
def _legacy_compat_s0039_r33_remote_file_adapter(kind,label,func_name,args,kwargs):
    body=_r33_export_body(str(kind),str(label),str(func_name),args,kwargs)
    body['front_release']='Пер-R43'
    try: _file_job_progress('передаю задание Render #2',force=True)
    except Exception: pass
    submit=globals().get('_r7_worker_file_submit')
    if not callable(submit): raise RuntimeError('R38 HEAVY export bridge unavailable')
    jid=submit(body)
    existing=_r35_delivery_get(jid)
    if str(existing.get('state') or '') not in {'running','done','done_error'}:
        _r35_delivery_set(jid,'accepted',{'job_id':jid,'operation':body.get('operation'),'recipient_chat_id':body.get('recipient_chat_id')})
    try: bot_journal('r36_heavy_file_accepted',int(body.get('recipient_chat_id') or 0),f"kind={kind}; op={body.get('operation')}; job={jid}; required_revision={body.get('required_revision') or 0}")
    except Exception: pass
    _r35_wait_remote_delivery(jid,body)
    # This call runs inside the original FAST file-job context, so only now may the
    # canonical runner close the status window and release its single-flight lock.
    delivery=str(body.get('delivery') or 'chat').lower()
    delivered_kind='Telegram через Render #2' if delivery=='chat' else ('Google Sheets' if delivery=='google' else 'Google Drive')
    if not file_job_mark_external_delivery(delivered_kind,jid):
        raise RuntimeError('R36 delivery was confirmed but FAST file-job context was lost')
    return True

# --- compat_legacy:0040 · from 10_split_policy_offload.py:7013 · public submit_interactive_file_job ---
def _legacy_compat_s0040_submit_interactive_file_job(chat_id:int,kind:str,label:str,func,*args,**kwargs):
    kind_s=str(kind or 'file'); heavy=(kind_s in _R33_HEAVY_FILE_KINDS or kind_s.startswith('window_'))
    if heavy: return _r40_submit_heavy_file(chat_id,kind_s,label,func,*args,**kwargs)
    return _LOCAL_SUBMIT_FILE_JOB(chat_id,kind,label,func,*args,**kwargs) if callable(_LOCAL_SUBMIT_FILE_JOB) else (False,'Экспорт недоступен')

# --- compat_legacy:0041 · from 10_split_policy_offload.py:7206 · public _r44_redact ---
def _legacy_compat_s0041_r44_redact(value):
    s=str(value if value is not None else '')
    try:
        sec=str(_r44_os.getenv('PEER_SHARED_SECRET','') or '')
        if sec and len(sec)>=6: s=s.replace(sec,'<peer-secret>')
    except Exception: pass
    for key in ('BOT_TOKEN','TELEGRAM_BOT_TOKEN','REDIS_URL','MEGA_PASSWORD','MEGA_SESSION','GOOGLE_SERVICE_ACCOUNT_JSON'):
        try:
            v=str(_r44_os.getenv(key,'') or '')
            if v and len(v)>=8: s=s.replace(v,f'<{key.lower()}>')
        except Exception: pass
    return s[:2400]

# --- compat_legacy:0042 · from 10_split_policy_offload.py:7219 · public _r44_diag ---
def _legacy_compat_s0042_r44_diag(event, **fields):
    try:
        row={'ts':round(_r44_time.time(),3),'event':str(event or '')[:120],'thread':_r44_threading.current_thread().name[:80]}
        for k,v in fields.items(): row[str(k)[:80]]=_r44_redact(v)
        raw=_r44_json.dumps(row,ensure_ascii=False,separators=(',',':'),default=str)+'\n'
        with _R44_DIAG_LOCK:
            _R44_DIAG_PATH.parent.mkdir(parents=True,exist_ok=True)
            try:
                if _R44_DIAG_PATH.exists() and _R44_DIAG_PATH.stat().st_size>_R44_DIAG_MAX:
                    old=_R44_DIAG_PATH.with_suffix(_R44_DIAG_PATH.suffix+'.1')
                    try: old.unlink(missing_ok=True)
                    except Exception: pass
                    try: _R44_DIAG_PATH.replace(old)
                    except Exception: pass
            except Exception: pass
            with open(_R44_DIAG_PATH,'a',encoding='utf-8') as fh: fh.write(raw)
    except Exception:
        pass

# --- compat_legacy:0043 · from 10_split_policy_offload.py:7238 · public _r44_diag_tail ---
def _legacy_compat_s0043_r44_diag_tail(limit=30):
    try:
        if not _R44_DIAG_PATH.exists(): return []
        with open(_R44_DIAG_PATH,'r',encoding='utf-8',errors='replace') as fh:
            rows=fh.readlines()[-max(1,min(100,int(limit or 30))):]
        out=[]
        for line in rows:
            try: out.append(_r44_json.loads(line))
            except Exception: continue
        return out
    except Exception: return []

# --- compat_legacy:0044 · from 10_split_policy_offload.py:7882 · public _r71_apply_runtime_side_effects ---
def _legacy_compat_s0044_r71_apply_runtime_side_effects():
    """12.26: keep legacy MEGA runtime OFF; canonical control-plane durability uses its own lease."""
    try:
        if 'MEGA_ENABLED' in globals(): globals()['MEGA_ENABLED']=False
        _split_os.environ['MEGA_ENABLED']='0'
        _split_os.environ['FAST_RUNTIME_MEGA_DISABLED']='1'
        _split_os.environ['OCH1226_MEGA_CANONICAL']='1' if _OCH1226_MEGA_DURABILITY_ENABLED else '0'
    except Exception: pass

# --- compat_legacy:0045 · from 10_split_policy_offload.py:7891 · public _r71_save_routes ---
def _legacy_compat_s0045_r71_save_routes(routes, reason='switch'):
    global _R71_ROUTE_CACHE
    clean = {k: _r71_normalize_owner((routes or {}).get(k, _R71_ROUTE_DEFAULTS[k])) for k in _R71_ROUTE_KEYS}
    if _OCH1224_SINGLE_RENDER:
        clean = {k: 'fast' for k in _R71_ROUTE_KEYS}
        reason = 'och12.24-single-render-forced'
    with _R71_ROUTE_LOCK:
        _R71_ROUTE_CACHE = dict(clean)
        try:
            db = globals().get('SQLITE')
            if db is not None and hasattr(db, 'set_meta'):
                db.set_meta(_R71_ROUTE_META_NS, _R71_ROUTE_META_KEY, dict(clean))
        except Exception as exc:
            try: log_error(f'R71 route persist: {exc}')
            except Exception: pass
    _r71_apply_runtime_side_effects()
    try:
        bot_journal('r71_route_change', int(OWNER_ID or 0), f'reason={reason}; routes={clean}')
    except Exception:
        pass
    return dict(clean)

# --- compat_legacy:0046 · from 10_split_policy_offload.py:7940 · public _r70_routes_text ---
def _legacy_compat_s0046_r70_routes_text():
    h = dict(_SPLIT_STATE.get('worker_health') or {}); st = dict(h.get('state') or {})
    worker_ok = bool(h.get('ok')) and int(_SPLIT_STATE.get('peer_status') or 0) in range(200, 300)
    try: wa_stats = dict(WINDOW_ACTOR_REGISTRY.stats() or {})
    except Exception: wa_stats = {}
    warn = []
    if _r71_route_is_fast('google') and not _r71_fast_google_ready():
        warn.append('⚠️ Google выбран на R1, но локальный service account сейчас не найден.')
    if _r71_route_is_fast('mega') and not _r71_fast_mega_ready():
        warn.append('⚠️ MEGA выбран на R1, но FAST не видит credentials/MEGAcmd.')
    lines = [
        f'🧭 <b>{BOT_DISPLAY_NAME} · ПЕРЕКЛЮЧАТЕЛИ R1/R2</b>', '',
        'Фиксированные владельцы:',
        '🔒 Telegram webhook / callback ACK — <b>R1 FAST</b>',
        '🔒 Telegram окна / кнопки — <b>R1 FAST</b>',
        '🔒 Реальная доставка пересылки — <b>R1 FAST</b>',
        '🔒 Canonical business mutation — <b>R1 FAST</b>', '',
        'Переключаемые режимы:',
        f'📊 Google / тяжёлые таблицы — {_r71_owner_html("google")}',
        f'📦 File export / Excel / CSV / JSON / SQLite — {_r71_owner_html("files")}',
        f'🧪 Runtime / журналы / ТЗ окон — {_r71_owner_html("diagnostics")}',
        f'🗄 MEGA backup / recovery / runtime — {_r71_owner_html("mega")}', '',
        'Синхронизация состояния R1 → R2 остаётся включённой независимо от выбора: это зеркало/страховка, а не владелец пользовательской операции.',
        f'R2 сейчас: {"✅ доступен" if worker_ok else "⛔ недоступен"} · очередь {int(h.get("queue_size") or 0)} · Google {int(h.get("google_queue_size") or 0)}',
        f'События R2: received {int(st.get("event_received") or 0)} · commit {int(st.get("event_committed") or 0)} · pending {int(st.get("event_pending") or 0)}',
        f'Window Actor R1: окон {int(wa_stats.get("windows") or 0)} · markup-only {int(wa_stats.get("markup_only") or 0)} · no-op {int(wa_stats.get("noops") or 0)}',
    ]
    if warn:
        lines += ['', *warn]
    lines += ['', 'Нажатие переключателя меняет <b>реального исполнителя</b>, а не только подпись. По умолчанию после обновления всё тяжёлое остаётся на R2.']
    return window_mark('\n'.join(lines), 'Ф4072')

# --- compat_legacy:0047 · from 10_split_policy_offload.py:7973 · public _r71_route_button ---
def _legacy_compat_s0047_r71_route_button(key):
    owner = _r71_route_owner(key)
    prefix = '🟢 #1' if owner == 'fast' else '🛰 #2'
    short = {'google':'Google','files':'Файлы','diagnostics':'Диагн.','mega':'MEGA'}[key]
    return IB(f'{prefix} · {short}', callback_data=f'r71:route:{key}')

# --- compat_legacy:0048 · from 10_split_policy_offload.py:7980 · public _r70_routes_keyboard ---
def _legacy_compat_s0048_r70_routes_keyboard():
    kb = types.InlineKeyboardMarkup(row_width=2)
    kb.row(_r71_route_button('google'), _r71_route_button('files'))
    kb.row(_r71_route_button('diagnostics'), _r71_route_button('mega'))
    kb.row(IB('🟢 ВСЁ тяжёлое → #1', callback_data='r71:all:fast'), IB('🛰 ВСЁ тяжёлое → #2', callback_data='r71:all:heavy'))
    kb.row(IB('🧪 Тест #1 ↔ #2', callback_data='r44:test:open'), IB('🔄 Render #2', callback_data='r10:worker:refresh'))
    kb.row(IB('🔙 Render #2', callback_data='r10:worker:status'), IB('❌ Закрыть', callback_data='info_close'))
    return kb

# --- compat_legacy:0049 · from 10_split_policy_offload.py:8066 · public submit_interactive_file_job ---
def _legacy_compat_s0049_submit_interactive_file_job(chat_id:int, kind:str, label:str, func, *args, **kwargs):
    group = _r71_job_group(kind, label, args, kwargs)
    if _r71_route_is_fast(group):
        return _r71_submit_local_file_job(chat_id, kind, label, func, *args, **kwargs)
    return _R71_REMOTE_FILE_SUBMIT(chat_id, kind, label, func, *args, **kwargs)

# --- compat_legacy:0050 · from 10_split_policy_offload.py:8095 · public schedule_delta_backup ---
def _legacy_compat_s0050_schedule_delta_backup(chat_id=None, delay=None, reason='change'):
    if _r71_route_is_fast('mega'):
        fn = globals().get('_canon_schedule_delta_backup__003') or globals().get('_canon_schedule_delta_backup__002')
        if callable(fn): return fn(chat_id, delay=delay, reason=reason)
    return _R71_REMOTE_SCHEDULE_DELTA(chat_id, delay=delay, reason=reason)

# --- compat_legacy:0051 · from 10_split_policy_offload.py:8102 · public persist_critical_delta_now ---
def _legacy_compat_s0051_persist_critical_delta_now(chat_id):
    if _r71_route_is_fast('mega'):
        fn = globals().get('_canon_persist_critical_delta_now__003') or globals().get('_canon_persist_critical_delta_now__002')
        if callable(fn): return fn(int(chat_id))
    return _R71_REMOTE_CRITICAL_DELTA(int(chat_id))

# --- compat_legacy:0052 · from 10_split_policy_offload.py:8109 · public schedule_full_backup_only ---
def _legacy_compat_s0052_schedule_full_backup_only(chat_id, delay=3.0):
    if _r71_route_is_fast('mega'):
        fn = globals().get('_V176_ORIG_FULL_BACKUP')
        if callable(fn): return fn(int(chat_id), delay)
    return _R71_REMOTE_FULL_BACKUP(int(chat_id), delay)

# --- compat_legacy:0053 · from 10_split_policy_offload.py:8120 · public schedule_config_backup_for_chats ---
def _legacy_compat_s0053_schedule_config_backup_for_chats(*chat_ids, delay=3.0):
    if _r71_route_is_fast('mega'):
        fn = globals().get('_canon_schedule_config_backup_for_chats__002') or globals().get('_canon_schedule_config_backup_for_chats__001')
        if callable(fn): return fn(*chat_ids, delay=delay)
    return _R71_REMOTE_CONFIG_BACKUP(*chat_ids, delay=delay)

# --- compat_legacy:0054 · from 10_split_policy_offload.py:8574 · public _r73_schedule_live_refresh ---
def _legacy_compat_s0054_r73_schedule_live_refresh(reason='settings'):
    def _job():
        try:
            lock = globals().get('_V221_LIVE_MARKUP_LOCK')
            reg = globals().get('_V221_LIVE_MARKUP')
            if lock is None or not isinstance(reg, dict):
                return
            with lock:
                items = [(k, dict(v or {})) for k, v in reg.items()]
        except Exception:
            return
        changed = 0
        for (cid, mid), row in items:
            try:
                source = row.get('source_markup') if row.get('source_markup') is not None else row.get('markup')
                after = v227_render_effective_contour_markup(source, str(row.get('text') or ''), int(cid))
                fp = globals().get('_v221_markup_fingerprint')
                if callable(fp) and fp(row.get('markup')) == fp(after):
                    continue
                fast_ui_edit_reply_markup(int(cid), int(mid), after, purpose='r73_factory_refresh')
                rec = globals().get('v221_record_live_markup')
                if callable(rec):
                    rec(int(cid), int(mid), after, str(row.get('text') or ''), source_markup=source)
                changed += 1
            except Exception:
                continue
        try:
            bot_journal('r73_factory_live_refresh', int(OWNER_ID or 0), f'reason={reason}; changed={changed}')
        except Exception:
            pass
    try:
        pool = globals().get('GENERAL_TASK_POOL')
        submit_unique = getattr(pool, 'submit_unique', None) if pool is not None else None
        if callable(submit_unique):
            submit_unique('r73-factory-refresh', _job)
            return
    except Exception:
        pass
    try:
        threading.Thread(target=_job, daemon=True, name='r73-factory-refresh').start()
    except Exception:
        pass

# --- compat_legacy:0055 · from 10_split_policy_offload.py:8877 · public _r75_transport_feature_fence ---
def _legacy_compat_s0055_r75_transport_feature_fence(reply_markup, chat_id, stage='final_transport', message_id=None):
    """Last-chance visibility policy.  Must run immediately before Telegram API."""
    if reply_markup is None:
        return None
    try:
        cid = int(chat_id or 0)
    except Exception:
        return reply_markup
    if not cid:
        return reply_markup
    try:
        import copy as _r75_copy
        kb = _r75_copy.deepcopy(reply_markup)
    except Exception:
        kb = reply_markup
    rows_fn = globals().get('_v221_markup_rows')
    set_fn = globals().get('_v221_set_markup_rows')
    try:
        rows = list(rows_fn(kb) or []) if callable(rows_fn) else list(getattr(kb, 'keyboard', None) or getattr(kb, 'inline_keyboard', None) or [])
    except Exception:
        rows = []
    clean = []
    removed = []
    for row in rows:
        keep = []
        for button in list(row or []):
            raw = _r73_cb(button)
            base = _r75_base_callback(raw)
            feature = _r75_feature_for_callback(base)
            if feature and not _r73_feature_enabled(feature, cid):
                removed.append({'feature': feature, 'callback': base[:120], 'raw': str(raw)[:120]})
                continue
            keep.append(button)
        if keep:
            clean.append(keep)
    if callable(set_fn):
        kb = set_fn(kb, clean)
    else:
        try:
            kb.keyboard = clean
        except Exception:
            try:
                kb.inline_keyboard = clean
            except Exception:
                pass
    stage_name = str(stage or 'final_transport')[:80]
    with _R75_FEATURE_FENCE_LOCK:
        _R75_FEATURE_FENCE_STATS['checked'] = int(_R75_FEATURE_FENCE_STATS.get('checked') or 0) + 1
        if removed:
            _R75_FEATURE_FENCE_STATS['drops'] = int(_R75_FEATURE_FENCE_STATS.get('drops') or 0) + len(removed)
            by_stage = _R75_FEATURE_FENCE_STATS.setdefault('by_stage', {})
            by_stage[stage_name] = int(by_stage.get(stage_name) or 0) + len(removed)
            by_feature = _R75_FEATURE_FENCE_STATS.setdefault('by_feature', {})
            for item in removed:
                f = str(item.get('feature') or '')
                by_feature[f] = int(by_feature.get(f) or 0) + 1
            recent = _R75_FEATURE_FENCE_STATS.setdefault('recent', [])
            recent.append({'at': time.time(), 'chat_id': cid, 'message_id': int(message_id or 0), 'scope': _r73_scope_key_for_chat(cid), 'stage': stage_name, 'removed': removed[:12]})
            del recent[:-60]
    if removed:
        detail = {
            'scope': _r73_scope_key_for_chat(cid),
            'stage': stage_name,
            'removed': removed[:12],
            'settings': {f: int(_r73_feature_enabled(f, cid)) for f in _R73_FEATURES},
        }
        try:
            caller_fn = globals().get('_window_diag_caller')
            if callable(caller_fn):
                detail['producer'] = str(caller_fn() or '')[:180]
        except Exception:
            pass
        try:
            emit = globals().get('_window_diag_emit')
            if callable(emit):
                emit('r75_feature_leak_blocked', cid, int(message_id or 0) or None, detail, 'WARN')
        except Exception:
            pass
        try:
            bot_journal('r75_feature_leak_blocked', cid, __import__('json').dumps(detail, ensure_ascii=False, separators=(',', ':'), default=str)[:1800], 'WARN')
        except Exception:
            pass
    return kb

# --- compat_legacy:0056 · from 10_split_policy_offload.py:8971 · public _r75_beetle_text ---
def _legacy_compat_s0056_r75_beetle_text():
    snap = r75_feature_fence_snapshot()
    by_feature = snap.get('by_feature') or {}
    by_stage = snap.get('by_stage') or {}
    lines = [
        f'🪲 ЖУК-НАРЫВНИК R75 · {BOT_DISPLAY_NAME}', '',
        'Ловит попытки вернуть выключенные Конструкторы, Описания, ТЗ и Маркеры.',
        'Проверка стоит прямо перед Telegram API и отдельно перед semantic-router.', '',
        f"Проверок финального фильтра: {int(snap.get('checked') or 0)}",
        f"Заблокировано кнопок: {int(snap.get('drops') or 0)}",
        f"Конструкторы: {int(by_feature.get('constructors') or 0)} · Описания: {int(by_feature.get('descriptions') or 0)}",
        f"ТЗ: {int(by_feature.get('tz') or 0)} · Маркеры: {int(by_feature.get('markers') or 0)}",
    ]
    if by_stage:
        lines += ['', 'Откуда пытались пройти:']
        for stage, count in sorted(by_stage.items(), key=lambda kv: int(kv[1] or 0), reverse=True)[:8]:
            lines.append(f'• {stage}: {int(count or 0)}')
    recent = list(snap.get('recent') or [])[-8:]
    if recent:
        lines += ['', 'Последние блокировки:']
        for row in reversed(recent):
            rem = row.get('removed') or []
            features = ','.join(sorted({str(x.get('feature') or '') for x in rem if x.get('feature')})) or '—'
            cbs = ', '.join(str(x.get('callback') or '')[:38] for x in rem[:3]) or '—'
            lines.append(f"• {row.get('stage','?')} · {row.get('scope','?')} · {features} · {cbs}")
    lines += ['', 'В полном журнале события `r75_feature_leak_blocked` содержат producer, stage, scope, callback и фактическое состояние всех четырёх переключателей.']
    return window_mark('\n'.join(lines)[:3800], 'Ф89')

# --- compat_legacy:0057 · from 10_split_policy_offload.py:9667 · public _r75_beetle_text ---
def _legacy_compat_s0057_r75_beetle_text():
    base=str(_R76_BEETLE_CORE() if callable(_R76_BEETLE_CORE) else '')
    snap=r76_ui_profile_snapshot()
    lines=['', '⚡ R76 ПРОФИЛЬ ОТРИСОВКИ',
           f"Semantic-дубли удалены: {int(snap.get('semantic_drops') or 0)} в {int(snap.get('semantic_windows') or 0)} окнах",
           f"Factory refresh: запусков {int(snap.get('refresh_runs') or 0)} · просмотрено {int(snap.get('refresh_scanned') or 0)} · изменено {int(snap.get('refresh_changed') or 0)} · исключено текущее {int(snap.get('refresh_excluded') or 0)}",
           f"Средний локальный final-filter: {snap.get('filter_avg_ms',0)} ms"]
    cb=list(snap.get('callback_recent') or [])[-5:]
    if cb:
        lines.append('Последние callback total:')
        for x in reversed(cb): lines.append(f"• {x.get('action') or '—'} · {x.get('ms')} ms")
    tr=list(snap.get('transport_recent') or [])[-5:]
    if tr:
        lines.append('Последние Telegram transport:')
        for x in reversed(tr): lines.append(f"• {x.get('purpose') or x.get('func')} · {x.get('ms')} ms · {'OK' if x.get('ok') else 'ERR'}")
    # Keep Telegram text under its hard limit while retaining the newest profiler data.
    joined=(base.rstrip()+"\n"+'\n'.join(lines)).strip()
    return window_mark(joined[-3850:], 'Ф89')

# --- compat_legacy:0058 · from 10_split_policy_offload.py:10857 · public _r70_routes_text ---
def _legacy_compat_s0058_r70_routes_text():
    h=dict(_SPLIT_STATE.get('worker_health') or {}); st=dict(h.get('state') or {})
    worker_ok=bool(h.get('ok')) and int(_SPLIT_STATE.get('peer_status') or 0) in range(200,300)
    with _R80_MEGA_LOCK: ms=dict(_R80_MEGA_STATE)
    master=_r80_mega_master_enabled()
    lines=[
        f'🧭 <b>{BOT_DISPLAY_NAME} · R1/R2 ПРОЦЕССЫ</b>','',
        'Всегда на R1 FAST:',
        '🔒 Telegram webhook / ACK / окна / кнопки',
        '🔒 Canonical business mutation / SQLite commit',
        '🔒 Реальная доставка пересылок','',
        'Переключаемые тяжёлые контуры:',
        f'📊 Google / таблицы — {_r71_owner_html("google")}',
        f'📦 Файлы / Excel / CSV / JSON / SQLite — {_r71_owner_html("files")}',
        f'🧪 Диагностика / журналы / архивы — {_r71_owner_html("diagnostics")}',
        f'🗄 MEGA browser / recovery — {_r71_owner_html("mega")}',
        f'🧱 State events / capsule durability — {_r71_owner_html("durability")}',
        f'📸 FULL / compact tail checkpoints — {_r71_owner_html("checkpoints")}','',
        f'R2: {"✅ доступен" if worker_ok else "⛔ недоступен"} · HTTP {int(_SPLIT_STATE.get("peer_status") or 0)} · очередь {int(h.get("queue_size") or 0)}',
        f'MEGA master Render #1: {"✅ MEGA_ENABLED=1" if master else "⛔ MEGA_ENABLED=0"}',
        f'R1 compact MEGA: FULL {(_r10_age_text(ms.get("last_full_at")) if ms.get("last_full_at") else "—")} · tail {int(ms.get("last_tail_count") or 0)} · maxrev {int(ms.get("tail_max_revision") or 0)}',
        f'R1 compact error: {str(ms.get("last_error") or "нет")[:180]}','',
        '🚨 Если R2 умер: нажмите «ВСЁ → R1». State-events перестанут ждать R2; Redis остаётся быстрым TAIL, MEGA пишется пакетно в фоне.',
        'MEGA compact хранит только fixed latest + один aggregated tail + head.json. Никаких per-event/generation тысяч файлов.',
        'Ни один MEGA/Redis/Google heavy-вызов не ставится между нажатием пользователя и отрисовкой окна.',
    ]
    return window_mark('\n'.join(lines),'Ф4072')

# --- compat_legacy:0059 · from 10_split_policy_offload.py:10890 · public _r70_routes_keyboard ---
def _legacy_compat_s0059_r70_routes_keyboard():
    kb=types.InlineKeyboardMarkup(row_width=2)
    kb.row(_r71_route_button('google'),_r71_route_button('files'))
    kb.row(_r71_route_button('diagnostics'),_r71_route_button('mega'))
    kb.row(_r71_route_button('durability'),_r71_route_button('checkpoints'))
    kb.row(IB('🚨 R2 НЕТ → ВСЁ #1',callback_data='r71:all:fast'),IB('⛔ Render #2 выключен',callback_data='r71:all:heavy'))
    if _OCH1224_SINGLE_RENDER:
        kb.row(IB('📸 MEGA FULL сейчас',callback_data='r80:mega:full'),IB('⛔ Render #2 отключён',callback_data='r71:all:heavy'))
        kb.row(IB('❌ Закрыть',callback_data='info_close'))
    else:
        kb.row(IB('📸 MEGA FULL сейчас',callback_data='r80:mega:full'),IB('🧪 Тест #1 ↔ #2',callback_data='r44:test:open'))
        kb.row(IB('🔄 Render #2',callback_data='r10:worker:refresh'),IB('❌ Закрыть',callback_data='info_close'))
    return kb

# --- compat_legacy:0060 · from 10_split_policy_offload.py:11246 · public _r70_routes_text ---
def _legacy_compat_s0060_r70_routes_text():
    routes = _r71_load_routes()
    all_fast = all(str(routes.get(k) or '') == 'fast' for k in _R71_ROUTE_KEYS)
    master = _r80_mega_master_enabled()
    with _R80_MEGA_LOCK:
        ms = dict(_R80_MEGA_STATE)
    generation=str(ms.get('last_full_generation') or '—')
    lines = [
        f'🧭 <b>{BOT_DISPLAY_NAME} · R1 ПРОЦЕССЫ</b>', '',
        '✅ <b>Render #2 отключён · рабочий runtime только R1</b>', '',
        'Хранилище 12.31:',
        '☁️ MEGA — единственный источник восстановления',
        '⚡ Redis — только cache / locks / ускорение; restore из Redis запрещён',
        '💾 SQLite — рабочая локальная база', '',
        f'MEGA permission: {"✅ credentials" if master else "⛔ disabled"}',
        f'Canonical durability: {"✅ ON" if _OCH1226_MEGA_DURABILITY_ENABLED else "⛔ OFF"}',
        f'Generation: <code>{generation[:72]}</code>',
        f'Последний FULL: {(_r10_age_text(ms.get("last_full_at")) if ms.get("last_full_at") else "—")}',
        f'Current tail: {int(ms.get("last_tail_count") or 0)} events · maxrev {int(ms.get("tail_max_revision") or 0)}',
        f'Ошибка MEGA: {str(ms.get("last_error") or "нет")[:180]}', '',
        'Путь restore: database/current_manifest.json → immutable generation → database/deltas/current_tail.json.gz',
        'Старые current_manifest/tail не удаляются: они перемещаются в history/.',
        'compact_v80 больше не является каноническим restore.',
    ]
    return window_mark('\n'.join(lines), 'Ф4072')

# --- compat_legacy:0061 · from 10_split_policy_offload.py:11272 · public _r70_routes_keyboard ---
def _legacy_compat_s0061_r70_routes_keyboard():
    kb=types.InlineKeyboardMarkup(row_width=2)
    kb.row(_r71_route_button('google'),_r71_route_button('files'))
    kb.row(_r71_route_button('diagnostics'),_r71_route_button('mega'))
    kb.row(_r71_route_button('durability'),_r71_route_button('checkpoints'))
    kb.row(IB('✅ R2 НЕТ · ВСЁ #1',callback_data='r71:all:fast'),IB('⛔ Render #2 выключен',callback_data='r71:all:heavy'))
    if _OCH1224_SINGLE_RENDER:
        kb.row(IB('📸 MEGA FULL сейчас',callback_data='r80:mega:full'),IB('⛔ Render #2 отключён',callback_data='r71:all:heavy'))
        kb.row(IB('❌ Закрыть',callback_data='info_close'))
    else:
        kb.row(IB('📸 MEGA FULL сейчас',callback_data='r80:mega:full'),IB('🧪 Тест #1 ↔ #2',callback_data='r44:test:open'))
        kb.row(IB('🔄 Render #2',callback_data='r10:worker:refresh'),IB('❌ Закрыть',callback_data='info_close'))
    return kb

# v266
