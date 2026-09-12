# v262

# --- ИСТОЧНИК: 72_multitenant_runtime.py ---
_V146_WINDOW_LOCK = threading.RLock()
_V146_WINDOW_DIRTY_TYPES = {'main_day', 'remaining', 'categories', 'fin_view', 'local_fin_view', 'fin_categories_view', 'stored', 'static_view'}
_V146_WINDOW_REGISTRY_KEEP_DAYS = max(1, min(90, int(os.getenv('WINDOW_REGISTRY_KEEP_DAYS', '7') or '7')))
_V146_DURABLE_FORWARD_TIMEOUT = max(20.0, min(180.0, float(os.getenv('DURABLE_FORWARD_TIMEOUT_SECONDS', '45') or '45')))
_V146_FAILED_DIAG_LIMIT = max(1, min(20, int(os.getenv('FAILED_TASK_DIAG_LIMIT', '10') or '10')))
_V146_FAILED_CACHE_TTL = max(30.0, min(1800.0, float(os.getenv('FAILED_TASK_DIAG_TTL_SECONDS', '300') or '300')))
_V146_FAILED_TASK_DETAILS = []
_V146_FAILED_TASK_DETAILS_AT = 0.0
_V146_FAILED_TASK_RUNTIME_ERRORS = {}
_V146_FAILED_TASK_LOAD_LOCK = threading.Lock()
_V146_LAST_MALLOC_TRIM_MONO = 0.0
_V146_MALLOC_TRIM_COOLDOWN = max(30.0, min(600.0, float(os.getenv('MALLOC_TRIM_COOLDOWN_SECONDS', '180') or '180')))
_V146_MALLOC_TRIM_MIN_MB = max(128.0, min(2048.0, float(os.getenv('MALLOC_TRIM_MIN_MB', '220') or '220')))
try:
    BACKUP_MIN_DELAY_SECONDS = max(300.0, float(os.getenv('BACKUP_MIN_DELAY_SECONDS', '300') or '300'))
except Exception:
    BACKUP_MIN_DELAY_SECONDS = 300.0

def _v146_iso_now() -> str:
    try:
        return now_local().isoformat(timespec='milliseconds')
    except Exception:
        return datetime.now(timezone.utc).isoformat(timespec='milliseconds')

def _v146_registry_key(chat_id: int, message_id: int) -> str:
    return f'{owner_scope_id(int(chat_id))}:{int(chat_id)}:{int(message_id)}'

def _v146_window_identity(row: dict | None) -> str:
    row = row or {}
    payload = {'window_type': str(row.get('window_type') or ''), 'code': str(row.get('code') or ''), 'day_key': str(row.get('day_key') or ''), 'params': row.get('params') or {}}
    try:
        return hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str).encode('utf-8')).hexdigest()[:20]
    except Exception:
        return str(payload)

def _v146_registry_rows_for_message(chat_id: int, message_id: int) -> list[tuple[str, dict]]:
    out = []
    for key, item in list((_open_window_registry() or {}).items()):
        try:
            if int((item or {}).get('chat_id') or 0) == int(chat_id) and int((item or {}).get('message_id') or 0) == int(message_id):
                out.append((str(key), item or {}))
        except Exception:
            continue
    return out

def _v179_base_get_registered_open_window(chat_id: int, message_id: int) -> dict | None:
    rows = _v146_registry_rows_for_message(int(chat_id), int(message_id))
    if not rows:
        return None
    rows.sort(key=lambda pair: (int((pair[1] or {}).get('epoch') or 0), str((pair[1] or {}).get('updated_at') or '')), reverse=True)
    return dict(rows[0][1])

def window_registry_epoch(chat_id: int, message_id: int) -> int:
    try:
        return int((get_registered_open_window(int(chat_id), int(message_id)) or {}).get('epoch') or 0)
    except Exception:
        return 0

def _v168_schedule_window_registry_persist():
    """Window registry is diagnostic/UI state; never block a callback on a full root SQLite save."""

    def _job():
        try:
            save_data(data, root_only=True)
        except Exception as exc:
            try:
                log_error(f'v168 window registry persist: {exc}')
            except Exception:
                pass
    try:
        scheduler = globals().get('V166_CONFIG_IO_SCHEDULER')
        if scheduler is not None:
            scheduler.cancel('window-registry-root-v168')
            scheduler.schedule('window-registry-root-v168', 0.2, _job)
            return
    except Exception:
        pass
    try:
        pool = globals().get('V166_CONFIG_IO_TASK_POOL')
        if pool is not None and pool.submit('window-registry-root-v168', _job):
            return
    except Exception:
        pass
    try:
        DELAYED_SCHEDULER.schedule('window-registry-root-v168', 0.2, _job)
    except Exception:
        pass

def _v179_base_register_open_window(chat_id: int, message_id: int, window_type: str, code: str='', day_key: str | None=None, params: dict | None=None):
    chat_id = int(chat_id)
    message_id = int(message_id)
    params = dict(params or {})
    now_s = _v146_iso_now()
    with _V146_WINDOW_LOCK:
        reg = _open_window_registry()
        rows = _v146_registry_rows_for_message(chat_id, message_id)
        previous = None
        if rows:
            rows.sort(key=lambda pair: (int((pair[1] or {}).get('epoch') or 0), str((pair[1] or {}).get('updated_at') or '')), reverse=True)
            previous = dict(rows[0][1])
            for old_key, _old in rows:
                reg.pop(old_key, None)
        currency_chat_id = chat_id
        try:
            if params.get('target_chat_id') is not None:
                currency_chat_id = int(params.get('target_chat_id'))
        except Exception:
            currency_chat_id = chat_id
        new_row = {'owner_id': owner_scope_id(chat_id), 'chat_id': chat_id, 'message_id': message_id, 'window_type': str(window_type or ''), 'code': str(code or ''), 'currency_mode': currency_mode(currency_chat_id) if 'currency_mode' in globals() else 'ars', 'day_key': day_key, 'params': params}
        changed_identity = _v146_window_identity(previous) != _v146_window_identity(new_row)
        prev_epoch = int((previous or {}).get('epoch') or 0)
        epoch = max(1, prev_epoch + 1 if changed_identity else prev_epoch)
        new_row.update({'epoch': epoch, 'dirty': False, 'dirty_reason': '', 'dirty_at': '', 'registered_at': str((previous or {}).get('registered_at') or now_s), 'updated_at': now_s, 'last_interaction_at': now_s})
        reg[_v146_registry_key(chat_id, message_id)] = new_row
    _v168_schedule_window_registry_persist()
    try:
        _window_diag_emit('window_registry_epoch_changed' if changed_identity and previous else 'window_registry_registered', chat_id, message_id, {'epoch_before': int((previous or {}).get('epoch') or 0), 'epoch_after': epoch, 'type_before': str((previous or {}).get('window_type') or ''), 'type_after': str(window_type or ''), 'code_before': str((previous or {}).get('code') or ''), 'code_after': str(code or ''), 'day_before': (previous or {}).get('day_key'), 'day_after': day_key, 'duplicates_removed': max(0, len(rows) - 1)}, 'WARN' if max(0, len(rows) - 1) else 'INFO')
    except Exception:
        pass
    return dict(new_row)

def _canon_unregister_open_window__001(chat_id: int, message_id: int):
    chat_id = int(chat_id)
    message_id = int(message_id)
    removed = []
    with _V146_WINDOW_LOCK:
        reg = _open_window_registry()
        for key, item in _v146_registry_rows_for_message(chat_id, message_id):
            removed.append(dict(item or {}))
            reg.pop(key, None)
        if removed:
            pass
    if removed:
        _v168_schedule_window_registry_persist()
    try:
        cancel_fast_ui_edit(chat_id, message_id)
    except Exception:
        pass
    if removed:
        try:
            _window_diag_emit('window_registry_unregistered', chat_id, message_id, {'count': len(removed), 'epoch': max((int((x or {}).get('epoch') or 0) for x in removed))}, 'INFO')
        except Exception:
            pass

def _v146_mark_window_dirty(item: dict, reason: str) -> bool:
    if not isinstance(item, dict):
        return False
    if bool(item.get('dirty')) and str(item.get('dirty_reason') or '') == str(reason or ''):
        return False
    item['dirty'] = True
    item['dirty_reason'] = str(reason or 'finance_changed')[:180]
    item['dirty_at'] = _v146_iso_now()
    return True

def mark_registered_financial_windows_dirty(changed_chat_id: int, keep_message_ids: set[int] | None=None, reason: str='finance_changed') -> int:
    changed_chat_id = int(changed_chat_id)
    keep = {int(x) for x in keep_message_ids or set()}
    changed = 0
    with _V146_WINDOW_LOCK:
        for item in (_open_window_registry() or {}).values():
            if not isinstance(item, dict):
                continue
            try:
                mid = int(item.get('message_id') or 0)
                if mid in keep and int(item.get('chat_id') or 0) == changed_chat_id:
                    continue
                params = item.get('params') or {}
                target = int(params.get('target_chat_id') if params.get('target_chat_id') is not None else item.get('chat_id'))
                depends = target == changed_chat_id or bool(params.get('depends_on_all'))
                if not depends:
                    continue
                if str(item.get('window_type') or '') not in _V146_WINDOW_DIRTY_TYPES:
                    continue
                if _v146_mark_window_dirty(item, reason):
                    changed += 1
            except Exception:
                continue
        if changed:
            save_data(data, root_only=True)
    try:
        bot_journal('window_lazy_dirty_marked', changed_chat_id, f'count={changed} keep={sorted(keep)} reason={reason}')
    except Exception:
        pass
    return changed

def _v177_legacy_0245_cleanup_open_window_registry(reason: str='manual') -> dict:
    now_dt = now_local()
    cutoff = now_dt - timedelta(days=_V146_WINDOW_REGISTRY_KEEP_DAYS)
    removed = 0
    duplicates = 0
    f91_removed = 0
    normalized = 0
    with _V146_WINDOW_LOCK:
        reg = _open_window_registry()
        grouped = defaultdict(list)
        for key, item in list(reg.items()):
            try:
                grouped[int(item.get('chat_id') or 0), int(item.get('message_id') or 0)].append((key, item))
            except Exception:
                reg.pop(key, None)
                removed += 1
        new_reg = {}
        for (chat_id, message_id), rows in grouped.items():
            rows.sort(key=lambda pair: (int((pair[1] or {}).get('epoch') or 0), str((pair[1] or {}).get('updated_at') or '')), reverse=True)
            key, item = rows[0]
            duplicates += max(0, len(rows) - 1)
            keep = True
            store = get_chat_store(chat_id)
            wtype = str((item or {}).get('window_type') or '')
            code = str((item or {}).get('code') or '')
            try:
                updated = datetime.fromisoformat(str((item or {}).get('updated_at') or ''))
                if updated.tzinfo is None:
                    updated = updated.replace(tzinfo=now_dt.tzinfo)
            except Exception:
                updated = now_dt
            if wtype == 'remaining' or code.upper() == 'Ф91':
                if int(store.get('remaining_msg_id') or 0) != message_id:
                    keep = False
                    f91_removed += 1
            elif wtype == 'main_day':
                day = str((item or {}).get('day_key') or '')
                if int((get_or_create_active_windows(chat_id) or {}).get(day) or 0) != message_id:
                    keep = False
            elif wtype == 'stored' and code:
                if int(store.get(code) or 0) != message_id:
                    keep = False
            elif updated < cutoff and wtype in {'static_view', 'fin_view', 'local_fin_view', 'fin_categories_view', 'categories'}:
                keep = False
            if keep:
                canonical = _v146_registry_key(chat_id, message_id)
                item['epoch'] = max(1, int(item.get('epoch') or 1))
                new_reg[canonical] = item
                if canonical != key:
                    normalized += 1
            else:
                removed += 1
                try:
                    cancel_fast_ui_edit(chat_id, message_id)
                except Exception:
                    pass
        if duplicates or removed or normalized or (len(reg) != len(new_reg)):
            reg.clear()
            reg.update(new_reg)
            save_data(data, root_only=True)
    result = {'reason': reason, 'kept': len(_open_window_registry() or {}), 'removed': removed, 'duplicates_removed': duplicates, 'f91_removed': f91_removed, 'keys_normalized': normalized}
    try:
        bot_journal('window_registry_cleanup', None, json.dumps(result, ensure_ascii=False))
    except Exception:
        pass
    return result
try:
    _v177_legacy_0245_cleanup_open_window_registry.__name__ = 'cleanup_open_window_registry'
except Exception:
    pass

def _v146_refresh_primary_windows(chat_id: int, day_key: str, reason: str='finance_changed') -> dict:
    chat_id = int(chat_id)
    day_key = str(day_key or today_key())[:10]
    store = get_chat_store(chat_id)
    refreshed = []
    missing = []
    keep = set()
    mid = get_active_window_id(chat_id, day_key)
    if mid:
        keep.add(int(mid))
        actual = get_registered_open_window(chat_id, int(mid))
        if not actual or str(actual.get('window_type') or '') in {'', 'main_day'}:
            try:
                text, _ = render_day_window(chat_id, day_key)
                result = fast_ui_edit_message_text(chat_id, int(mid), text, reply_markup=build_main_keyboard(day_key, chat_id), purpose='finance_primary_window_refresh')
                refreshed.append({'message_id': int(mid), 'kind': 'main_day', 'result': result})
            except Exception as exc:
                if _message_missing_error(exc):
                    clear_active_window_id(chat_id, day_key)
                    unregister_open_window(chat_id, int(mid))
                    missing.append(int(mid))
                else:
                    log_error(f'v146 primary window refresh {chat_id}:{mid}: {exc}')
    rem_mid = int(store.get('remaining_msg_id') or 0)
    if rem_mid:
        keep.add(rem_mid)
        actual = get_registered_open_window(chat_id, rem_mid)
        if not actual or str(actual.get('window_type') or '') in {'', 'remaining'}:
            try:
                result = fast_ui_edit_message_text(chat_id, rem_mid, build_remaining_text(chat_id, day_key), reply_markup=build_remaining_keyboard(chat_id, day_key), parse_mode='HTML', purpose='finance_remaining_window_refresh')
                refreshed.append({'message_id': rem_mid, 'kind': 'remaining', 'result': result})
            except Exception as exc:
                if _message_missing_error(exc):
                    store['remaining_msg_id'] = None
                    unregister_open_window(chat_id, rem_mid)
                    missing.append(rem_mid)
                else:
                    log_error(f'v146 remaining window refresh {chat_id}:{rem_mid}: {exc}')
    dirty = mark_registered_financial_windows_dirty(chat_id, keep, reason)
    result = {'chat_id': chat_id, 'day': day_key, 'refreshed': refreshed, 'dirty': dirty, 'missing': missing}
    try:
        bot_journal('finance_window_refresh_detached_done', chat_id, json.dumps(result, ensure_ascii=False, default=str)[:1600])
    except Exception:
        pass
    return result

def _v177_legacy_0246_schedule_financial_window_refresh(chat_id: int, day_key: str | None=None, reason: str='finance_changed', delay: float=0.15):
    chat_id = int(chat_id)
    day_key = str(day_key or get_chat_store(chat_id).get('current_view_day') or today_key())[:10]
    scheduler_key = f'v146-fin-window:{chat_id}'

    def _dispatch():
        if not UI_TASK_POOL.submit(scheduler_key, _v146_refresh_primary_windows, chat_id, day_key, reason):
            log_error(f'V146 WINDOW REFRESH QUEUE FULL: {chat_id}')
    DELAYED_SCHEDULER.cancel(scheduler_key)
    DELAYED_SCHEDULER.schedule(scheduler_key, max(0.05, float(delay)), _dispatch)
    try:
        bot_journal('finance_window_refresh_detached', chat_id, f'day={day_key} reason={reason} delay={delay}')
    except Exception:
        pass

def _v177_legacy_0045_refresh_registered_financial_windows(chat_id: int):
    """v146 compatibility: no mass Telegram edits; schedule only primary windows and mark the rest dirty."""
    schedule_financial_window_refresh(int(chat_id), reason='registry_refresh')
    return True

def _finance_changed_now(chat_id: int, day_key: str | None=None, reason: str='change'):
    """v243 finance fast path: per-chat durability first, derived/global work detached."""
    chat_id = int(chat_id)
    day_key = str(day_key or get_chat_store(chat_id).get('current_view_day') or today_key())[:10]
    finance_cache_invalidate(chat_id, f'finance_changed:{reason}')
    with locked_chat(chat_id):
        store = get_chat_store(chat_id)
        _safe_stabilize('normalize_chat_records', lambda: normalize_chat_records(chat_id))
        _safe_stabilize('recalc_balance', lambda: recalc_balance(chat_id))
        _safe_stabilize('rebuild_month_short_ids', lambda: rebuild_month_short_ids(chat_id))
        _safe_stabilize('currency_ledger_snapshot', lambda: _snapshot_active_currency_ledger(store, _ensure_currency_ledgers(store)))
        _r48_need_persist = True
    _safe_stabilize('delta_queue_early', lambda: schedule_quick_backup(chat_id, MEGA_DELTA_PRIORITY_DELAY_SECONDS if mega_backup_priority_enabled() else MEGA_DELTA_DELAY_SECONDS))
    _safe_stabilize('finance_ui_fast_dispatch_v243', lambda: schedule_financial_window_refresh(chat_id, day_key, reason=f'finalize:{reason}', delay=0.01))
    fn = globals().get('schedule_finance_postcommit_background_v243')
    if callable(fn):
        _safe_stabilize('finance_postcommit_schedule_v243', lambda: fn(chat_id, reason=reason, delay=0.2))
    else:
        _safe_stabilize('full_backup_queue', lambda: schedule_full_backup_only(chat_id, BACKUP_MIN_DELAY_SECONDS))
    if callable(globals().get('persist_finance_chat_local_fast')):
        persist_finance_chat_local_fast(chat_id)

    try:
        bot_journal('finance_business_complete_v243', chat_id, f'day={day_key} reason={reason}; chat_durable=1; derived_background=1')
    except Exception:
        pass
    return True
_V146_ORIG_WINDOW_DIAG_PREPARE = _v177_legacy_0114_window_diag_prepare_fast_ui_payload
_V146_ORIG_WINDOW_DIAG_APPLY = _v177_legacy_0115_window_diag_fast_ui_apply

def _canon_window_diag_prepare_fast_ui_payload__001(payload: dict) -> dict:
    if callable(_V146_ORIG_WINDOW_DIAG_PREPARE):
        payload = _V146_ORIG_WINDOW_DIAG_PREPARE(payload) or payload
    try:
        payload['_window_registry_epoch'] = window_registry_epoch(int(payload.get('chat_id')), int(payload.get('message_id')))
    except Exception:
        payload['_window_registry_epoch'] = 0
    return payload

def _v146_fast_ui_payload_current(payload: dict) -> tuple[bool, dict]:
    chat_id = int(payload.get('chat_id'))
    message_id = int(payload.get('message_id'))
    expected = int(payload.get('_window_registry_epoch') or 0)
    current = window_registry_epoch(chat_id, message_id)
    ok = expected == 0 or current == expected
    return (ok, {'expected_epoch': expected, 'current_epoch': current, 'purpose': str(payload.get('purpose') or '')[:160]})

def _canon_window_diag_fast_ui_apply__001(payload: dict, delayed: bool=False):
    if callable(_V146_ORIG_WINDOW_DIAG_APPLY):
        try:
            _V146_ORIG_WINDOW_DIAG_APPLY(payload, delayed=delayed)
        except Exception:
            pass
    ok, detail = _v146_fast_ui_payload_current(payload)
    if delayed and (not ok):
        try:
            _window_diag_emit('window_stale_update_rejected', payload.get('chat_id'), payload.get('message_id'), detail, 'WARN')
        except Exception:
            pass
    return bool(ok or not delayed)

def _canon_run_pending_ui_edit__001(key):
    with _ui_edit_lock:
        payload = _ui_edit_pending.pop(key, None)
        _ui_edit_timers.pop(key, None)
        if not payload:
            return
        _ui_edit_last_ts[key] = time.time()
    allowed = True
    try:
        allowed = bool(window_diag_fast_ui_apply(payload, delayed=True))
    except Exception:
        allowed = True
    if not allowed:
        try:
            bot_journal('window_stale_update_rejected', payload.get('chat_id'), f"message_id={payload.get('message_id')} purpose={payload.get('purpose')}", 'WARN')
        except Exception:
            pass
        return
    _perform_fast_ui_edit(payload)
_V146_ORIG_PERSIST_FORWARD_FINANCE = _v177_legacy_0155_persist_forward_finance_delivery_now

def _canon_persist_forward_finance_delivery_now__001(src_chat_id: int, src_msg_id: int, dst_chat_id: int, dst_msg_id: int, rec: dict | None=None):
    batch_id = _fin_forward_batch_id(int(src_chat_id), int(src_msg_id)) if '_fin_forward_batch_id' in globals() else ''
    with _FIN_FORWARD_BATCH_LOCK:
        in_batch = batch_id in _FIN_FORWARD_BATCHES
    if not in_batch or not callable(_V146_ORIG_PERSIST_FORWARD_FINANCE):
        return _V146_ORIG_PERSIST_FORWARD_FINANCE(src_chat_id, src_msg_id, dst_chat_id, dst_msg_id, rec) if callable(_V146_ORIG_PERSIST_FORWARD_FINANCE) else False
    try:
        if isinstance(rec, dict):
            tags = {'forwarded_by_bot': True, 'forward_source_chat_id': int(src_chat_id), 'forward_source_msg_id': int(src_msg_id), 'forward_dst_chat_id': int(dst_chat_id), 'forward_dst_msg_id': int(dst_msg_id)}
            rec.update(tags)
            store = get_chat_store(int(dst_chat_id))
            rid = rec.get('id')
            for arr in (store.get('daily_records', {}) or {}).values():
                for rr in arr or []:
                    if isinstance(rr, dict) and rr.get('id') == rid:
                        rr.update(tags)
        _persist_forward_index_in_data(data)
        save_data(data, chat_ids=[int(dst_chat_id)])
        schedule_quick_backup(int(dst_chat_id), 0.5)
        with _FIN_FORWARD_BATCH_LOCK:
            row = _FIN_FORWARD_BATCHES.get(batch_id)
            if isinstance(row, dict):
                row.setdefault('durable_chats', set()).add(int(dst_chat_id))
        bot_journal('forward_finance_local_committed', int(dst_chat_id), f'batch={batch_id} src={src_chat_id}:{src_msg_id} dst_msg={dst_msg_id}; combined_delta=1')
        return True
    except Exception as exc:
        log_error(f'[V146 FWD FINANCE LOCAL ERROR] {src_chat_id}:{src_msg_id}->{dst_chat_id}:{dst_msg_id}: {exc}')
        return False

def _v146_finish_forward_follow(follow: dict, durable_ok: bool, durable_error: str=''):
    source_chat_id = int(follow.get('source_chat_id'))
    source_msg_id = int(follow.get('source_msg_id'))
    normal_targets = list(follow.get('normal_targets') or [])
    if durable_ok:
        if normal_targets:
            if not FORWARD_TASK_POOL.submit(source_chat_id, _forward_normal_stage, source_chat_id, follow.get('msg'), normal_targets):
                _forward_normal_stage(source_chat_id, follow.get('msg'), normal_targets)
        elif source_msg_id:
            _forward_outcome_update(source_chat_id, source_msg_id, state='completed')
    else:
        _forward_outcome_update(source_chat_id, source_msg_id, state='durable_pending', error=str(durable_error or 'delta upload failed')[:300])

        def _retry():
            ok = False
            try:
                ok = bool(durable_run_pending_delta_now_v234())
            except Exception as exc:
                log_error(f'V146 FIN BATCH DELTA RETRY {source_chat_id}:{source_msg_id}: {exc}')
            if ok:
                _v146_finish_forward_follow(follow, True)
            else:
                DELAYED_SCHEDULER.schedule(f'v146-fin-batch-delta:{source_chat_id}:{source_msg_id}', 5.0, _retry)
        DELAYED_SCHEDULER.schedule(f'v146-fin-batch-delta:{source_chat_id}:{source_msg_id}', 5.0, _retry)

def _canon_fin_forward_batch_finish_target__001(batch_id: str, dst_chat_id: int, ok: bool, elapsed: float, error: str='') -> None:
    follow = None
    with _FIN_FORWARD_BATCH_LOCK:
        row = _FIN_FORWARD_BATCHES.get(str(batch_id))
        if not isinstance(row, dict):
            return
        row.setdefault('targets', {})[str(int(dst_chat_id))] = {'ok': bool(ok), 'elapsed': round(float(elapsed), 3), 'error': str(error or '')[:300]}
        row['remaining'] = max(0, int(row.get('remaining', 0)) - 1)
        if row['remaining'] == 0:
            follow = dict(row)
            if isinstance(row.get('durable_chats'), set):
                follow['durable_chats'] = sorted(row.get('durable_chats'))
            _FIN_FORWARD_BATCHES.pop(str(batch_id), None)
    try:
        bot_journal('finance_forward_target_done', (follow or {}).get('source_chat_id'), f"batch={batch_id} dst={int(dst_chat_id)} ok={bool(ok)} elapsed={elapsed:.3f}s error={str(error or '')[:180]}", 'INFO' if ok else 'ERROR')
    except Exception:
        pass
    if not follow:
        return
    started = float(follow.get('started_mono') or time.monotonic())
    durable_started = time.monotonic()
    durable_ok = False
    durable_error = ''
    try:
        durable_ok = bool(durable_run_pending_delta_now_v234())
        if not durable_ok:
            durable_error = 'combined delta returned false'
    except Exception as exc:
        durable_error = str(exc)
        log_error(f'V146 FIN BATCH COMBINED DELTA {batch_id}: {exc}')
    _v146_finish_forward_follow(follow, durable_ok, durable_error)
    try:
        target_rows = follow.get('targets') or {}
        failed = sum((1 for x in target_rows.values() if not bool((x or {}).get('ok'))))
        bot_journal('finance_forward_batch_done', int(follow.get('source_chat_id')), f'batch={batch_id} targets={len(target_rows)} failed={failed} durable={int(durable_ok)} delta_elapsed={time.monotonic() - durable_started:.3f}s total_elapsed={time.monotonic() - started:.3f}s')
    except Exception:
        pass

def _canon_wait_durable_subtasks__001(chat_id, timeout: float=20.0, wait_forward: bool=True, payload: dict | None=None, expected: dict | None=None, update_id=None) -> bool:
    if chat_id is None or not wait_forward or (not isinstance(payload, dict)):
        return True
    raw, source_chat_id, source_msg_id, group_id = _durable_payload_message(payload)
    if not isinstance(raw, dict) or source_chat_id is None or source_msg_id is None:
        return True
    effective_timeout = max(float(timeout or 0), _V146_DURABLE_FORWARD_TIMEOUT)
    deadline = time.monotonic() + effective_timeout
    started = time.monotonic()
    last_state = ''
    last_targets = {}
    bot_journal('durable_forward_wait_start', chat_id, f"update={update_id} source={source_chat_id}:{source_msg_id} group={group_id or '-'} timeout={effective_timeout:g}")
    while True:
        outcome = _forward_outcome_snapshot(int(source_chat_id), int(source_msg_id))
        last_state = str(outcome.get('state') or '')
        last_targets = outcome.get('targets') or {}
        try:
            report = _durable_effect_report(payload, expected if isinstance(expected, dict) else None)
        except Exception as _report_exc:
            report = {'complete': False, 'missing': [f'report_error:{str(_report_exc)[:120]}'], 'ambiguous': []}
        if bool(report.get('complete')):
            bot_journal('durable_forward_wait_done', chat_id, f"update={update_id} source={source_chat_id}:{source_msg_id} state={last_state or '-'} elapsed={time.monotonic() - started:.3f}s complete=1")
            return True
        pending = _durable_forward_work_still_pending(payload)
        final_state = last_state.startswith('skip:') or last_state in {'completed', 'failed', 'no_targets'}
        if final_state and (not pending):
            bot_journal('durable_forward_wait_done', chat_id, f'update={update_id} source={source_chat_id}:{source_msg_id} state={last_state} elapsed={time.monotonic() - started:.3f}s complete=0 verify_next=1')
            return True
        if time.monotonic() >= deadline:
            qf = FIN_FORWARD_TASK_POOL.stats()
            qn = FORWARD_TASK_POOL.stats()
            target_state = {str(k): str((v or {}).get('state') or '') for k, v in list(last_targets.items())[:20]}
            log_error(f"DURABLE EXACT FORWARD TIMEOUT update={update_id} source={source_chat_id}:{source_msg_id} timeout={effective_timeout:g} state={last_state or '-'} targets={target_state} missing={report.get('missing')} ambiguous={report.get('ambiguous')} finQ={qf.get('pending')}/{qf.get('active')} fwdQ={qn.get('pending')}/{qn.get('active')}")
            return False
        time.sleep(0.05)
_V146_ORIG_MEGA_TASK_FINISH = _canon_mega_task_finish__001
_V146_ORIG_MEGA_TASK_STATS = _canon_mega_task_registry_stats__001

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

def _v146_load_failed_task_detail(key: str, row: dict) -> dict:
    local = None
    try:
        if telegram_durable_primary_v234() and str((row or {}).get('path') or '').startswith('telegram-head:'):
            task = _tg_task_row_v234(key) or dict(row or {})
            remote = str((row or {}).get('path') or f'telegram-head:{key}')
        else:
            remote = str((row or {}).get('path') or mega_task_remote_path(key, 'failed'))
            local = _mega_download_remote_path(remote)
            if not local:
                raise RuntimeError('failed task file download returned empty')
            with open(local, 'r', encoding='utf-8') as fh:
                task = json.load(fh)
        payload = task.get('payload') or {}
        expected = _durable_expected_from_task_or_payload(task, payload)
        report = _durable_effect_report(payload, expected)
        raw, source_chat_id, source_msg_id, group_id = _durable_payload_message(payload)
        runtime_error = _V146_FAILED_TASK_RUNTIME_ERRORS.get(str(key)) or {}
        return {'task_id': str(key), 'update_id': task.get('update_id'), 'created_at': task.get('created_at'), 'chat_id': task.get('chat_id'), 'update_type': task.get('update_type'), 'reason': task.get('reason'), 'source_chat_id': source_chat_id, 'source_message_id': source_msg_id, 'media_group_id': group_id, 'content_type': task.get('content_type'), 'forward_targets': task.get('forward_targets') or [], 'missing': report.get('missing') or [], 'ambiguous': report.get('ambiguous') or [], 'complete_now': bool(report.get('complete')), 'runtime_error': runtime_error.get('error') or '', 'safe_replay': False, 'remote_path': remote}
    except Exception as exc:
        return {'task_id': str(key), 'load_error': str(exc)[:500], 'remote_path': str((row or {}).get('path') or '')}
    finally:
        try:
            if local:
                shutil.rmtree(os.path.dirname(local), ignore_errors=True)
        except Exception:
            pass

def refresh_failed_task_diagnostics(force: bool=False) -> list[dict]:
    global _V146_FAILED_TASK_DETAILS, _V146_FAILED_TASK_DETAILS_AT
    if not force and time.monotonic() - _V146_FAILED_TASK_DETAILS_AT < _V146_FAILED_CACHE_TTL:
        return list(_V146_FAILED_TASK_DETAILS)
    if not _V146_FAILED_TASK_LOAD_LOCK.acquire(blocking=False):
        return list(_V146_FAILED_TASK_DETAILS)
    try:
        with _MEGA_TASK_LOCK:
            rows = [(str(k), dict(v or {})) for k, v in _mega_task_registry.items() if str((v or {}).get('state') or '') == 'failed'][:_V146_FAILED_DIAG_LIMIT]
        details = []
        reconciled = []
        for key, row in rows:
            detail = _v146_load_failed_task_detail(key, row)
            if bool((detail or {}).get('complete_now')) and callable(_V146_ORIG_MEGA_TASK_FINISH):
                try:
                    if _V146_ORIG_MEGA_TASK_FINISH(key, True, 'v147 verified existing effects'):
                        reconciled.append(str(key))
                        continue
                except Exception:
                    pass
            details.append(detail)
        _V146_FAILED_TASK_DETAILS = details
        _V146_FAILED_TASK_DETAILS_AT = time.monotonic()
        try:
            bot_journal('failed_task_diagnostics_refreshed', None, json.dumps({'count': len(details), 'reconciled': reconciled, 'tasks': details}, ensure_ascii=False, default=str)[:1800], 'WARN' if details else 'INFO')
        except Exception:
            pass
        return list(details)
    finally:
        _V146_FAILED_TASK_LOAD_LOCK.release()

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
try:
    _v177_legacy_0065_mega_task_registry_stats.__name__ = 'mega_task_registry_stats'
except Exception:
    pass

def _canon_memory_malloc_trim__001() -> bool:
    global _V146_LAST_MALLOC_TRIM_MONO
    now_m = time.monotonic()
    if now_m - _V146_LAST_MALLOC_TRIM_MONO < _V146_MALLOC_TRIM_COOLDOWN:
        return False
    try:
        snap = memory_quick_snapshot()
        used = float(snap.get('effective_mb') or 0.0)
        if used < _V146_MALLOC_TRIM_MIN_MB and memory_level(snap) == 'normal':
            return False
    except Exception:
        used = 0.0
    try:
        libc = _memory_ctypes.CDLL('libc.so.6')
        result = int(libc.malloc_trim(0))
        _V146_LAST_MALLOC_TRIM_MONO = now_m
        with _MEMORY_LOCK:
            _MEMORY_STATE['malloc_trim_count'] = int(_MEMORY_STATE.get('malloc_trim_count') or 0) + 1
            _MEMORY_STATE['last_malloc_trim_at'] = _v146_iso_now()
            _MEMORY_STATE['last_malloc_trim_used_mb'] = used
        return result == 1
    except Exception:
        return False
_V146_ORIG_REM_DELETE_MAP = _v177_legacy_0131_reminder_delete_message_map
_V146_ORIG_REM_COMPLETE = _v177_legacy_0122_reminder_mark_completed
_V146_ORIG_REM_GROUP_DELETE = _v177_legacy_0134_reminder_group_delete_message

def _canon_reminder_delete_message_map__001(last_map: dict) -> None:
    for cid_raw, mid_raw in list((last_map or {}).items()):
        try:
            bot.delete_message(int(cid_raw), int(mid_raw))
            bot_journal('reminder_previous_deleted', int(cid_raw), f'message_id={int(mid_raw)}')
        except Exception as exc:
            bot_journal('reminder_previous_delete_failed', int(cid_raw), f'message_id={mid_raw} error={str(exc)[:300]}', 'WARN')

def _canon_reminder_mark_completed__001(reminder_id: int, cfg: dict, reason: str='time_finished', delete_messages: bool=True) -> None:
    was_completed = _reminder_is_completed(cfg)
    if callable(_V146_ORIG_REM_COMPLETE):
        _V146_ORIG_REM_COMPLETE(reminder_id, cfg, reason, delete_messages)
    if not was_completed and _reminder_is_completed(cfg):
        try:
            bot_journal('reminder_completed', None, f'reminder_id={int(reminder_id)} reason={reason} delete_messages={int(bool(delete_messages))}')
            bot_journal('reminder_archived', None, f"reminder_id={int(reminder_id)} completed_at={cfg.get('completed_at')}")
        except Exception:
            pass

def _canon_reminder_group_delete_message__001(chat_id: int, message_id: int):
    try:
        result = _V146_ORIG_REM_GROUP_DELETE(chat_id, message_id) if callable(_V146_ORIG_REM_GROUP_DELETE) else bot.delete_message(int(chat_id), int(message_id))
        bot_journal('reminder_group_previous_deleted', int(chat_id), f'message_id={int(message_id)}')
        return result
    except Exception as exc:
        bot_journal('reminder_group_previous_delete_failed', int(chat_id), f'message_id={message_id} error={str(exc)[:300]}', 'WARN')
        return None
_V146_ORIG_RUNTIME_MARK_READY = _v177_legacy_0082_runtime_mark_ready

def _v177_legacy_0083_runtime_mark_ready(detail: str=''):
    result = _V146_ORIG_RUNTIME_MARK_READY(detail) if callable(_V146_ORIG_RUNTIME_MARK_READY) else None
    try:
        DELAYED_SCHEDULER.schedule('v146-window-registry-cleanup', 2.0, cleanup_open_window_registry, 'startup')
    except Exception:
        pass
    try:

        def _v178_start_failed_diagnostics_if_enabled():
            enabled_fn = globals().get('v176_process_enabled')
            if callable(enabled_fn) and (not bool(enabled_fn('failed_diag'))):
                return []
            fn = globals().get('refresh_failed_task_diagnostics')
            return fn(True) if callable(fn) else []
        DELAYED_SCHEDULER.schedule('v146-failed-task-diagnostics', 8.0, _v178_start_failed_diagnostics_if_enabled)
    except Exception:
        pass
    return result
try:
    _v177_legacy_0083_runtime_mark_ready.__name__ = 'runtime_mark_ready'
except Exception:
    pass
try:
    WINDOW_MARKER_CONSTANTS.setdefault('exp_style_period', 'Ф179')
    WINDOW_MARKER_CONSTANTS.setdefault('exp_new_period_send', 'Ф180')
except Exception:
    pass
TENANT_SCHEMA_VERSION = 1
TENANT_PLATFORM_ID = 'platform'
TENANT_ROLE_ORDER = ('tenant_owner', 'tenant_admin', 'operator', 'viewer')
TENANT_ROLE_LABELS = {'platform_owner': 'Владелец платформы', 'tenant_owner': 'Владелец пространства', 'tenant_admin': 'Администратор', 'operator': 'Оператор', 'viewer': 'Только просмотр', 'standard': 'Участник чата'}
_TENANT_LOCK = threading.RLock()
_TENANT_CONTEXT = threading.local()
_TENANT_BOT_USERNAME = ''

def _tenant_now() -> str:
    return now_local().isoformat(timespec='seconds')

def _tenant_platform_owner_user_id() -> int:
    try:
        return int(OWNER_ID or 0)
    except Exception:
        return 0

def tenant_current_actor_user_id() -> int:
    try:
        ctx = _current_telegram_update_context()
        return int(ctx.get('user_id') or 0)
    except Exception:
        return 0

def tenant_is_platform_owner_user(user_id: int | None) -> bool:
    try:
        return bool(int(user_id or 0) and int(user_id or 0) == _tenant_platform_owner_user_id())
    except Exception:
        return False

def tenant_is_platform_owner_context(chat_id: int | None=None) -> bool:
    uid = tenant_current_actor_user_id()
    if uid:
        return tenant_is_platform_owner_user(uid)
    try:
        cid = int(chat_id if chat_id is not None else current_state_chat_id() or 0)
    except Exception:
        cid = 0
    return bool(cid and cid == _tenant_platform_owner_user_id())

@contextmanager
def tenant_context(tenant_id: str | None):
    prev = getattr(_TENANT_CONTEXT, 'tenant_id', None)
    try:
        _TENANT_CONTEXT.tenant_id = str(tenant_id or '') or None
        yield
    finally:
        _TENANT_CONTEXT.tenant_id = prev

def _tenants_root() -> dict:
    gs = data.setdefault('_global_settings', {})
    with _TENANT_LOCK:
        root = gs.get('tenants_v148')
        if not isinstance(root, dict):
            root = {}
            gs['tenants_v148'] = root
        root.setdefault('schema_version', TENANT_SCHEMA_VERSION)
        root.setdefault('tenants', {})
        root.setdefault('chat_to_tenant', {})
        root.setdefault('invite_tokens', {})
        root.setdefault('legacy_migrated', False)
        root.setdefault('created_at', _tenant_now())
        return root

def _tenant_default_name(chat_id: int | None=None) -> str:
    if chat_id:
        try:
            return str(get_chat_display_name(int(chat_id)) or f'Чат {int(chat_id)}')[:80]
        except Exception:
            pass
    return 'Новое пространство'

def _tenant_normalize(tenant_id: str, row: dict | None=None) -> dict:
    row = row if isinstance(row, dict) else {}
    row['id'] = str(tenant_id)
    row.setdefault('name', 'Пространство')
    row.setdefault('owner_user_id', 0)
    row.setdefault('root_chat_id', 0)
    row.setdefault('chat_ids', [])
    row.setdefault('users', {})
    row.setdefault('settings', {})
    row.setdefault('status', 'active')
    row.setdefault('created_at', _tenant_now())
    row.setdefault('updated_at', _tenant_now())
    clean_chats = []
    for raw in row.get('chat_ids') or []:
        try:
            cid = int(raw)
        except Exception:
            continue
        if cid not in clean_chats:
            clean_chats.append(cid)
    row['chat_ids'] = clean_chats
    users = row.get('users') if isinstance(row.get('users'), dict) else {}
    owner_uid = int(row.get('owner_user_id') or 0)
    if owner_uid:
        users.setdefault(str(owner_uid), {})['role'] = 'tenant_owner'
    for uid, item in list(users.items()):
        try:
            int(uid)
        except Exception:
            users.pop(uid, None)
            continue
        if not isinstance(item, dict):
            item = {'role': 'viewer'}
            users[str(uid)] = item
        role = str(item.get('role') or 'viewer')
        if role not in TENANT_ROLE_ORDER:
            role = 'viewer'
        item['role'] = role
        item.setdefault('joined_at', _tenant_now())
        item.setdefault('updated_at', _tenant_now())
    row['users'] = users
    return row

def tenant_get(tenant_id: str | None) -> dict | None:
    if not tenant_id:
        return None
    root = _tenants_root()
    row = (root.get('tenants') or {}).get(str(tenant_id))
    if not isinstance(row, dict):
        return None
    row = _tenant_normalize(str(tenant_id), row)
    root['tenants'][str(tenant_id)] = row
    return row

def tenant_all() -> list[dict]:
    root = _tenants_root()
    rows = []
    for tid, row in list((root.get('tenants') or {}).items()):
        if isinstance(row, dict):
            rows.append(_tenant_normalize(str(tid), row))
    rows.sort(key=lambda r: (0 if str(r.get('id')) == TENANT_PLATFORM_ID else 1, str(r.get('name') or '').casefold()))
    return rows

def _v177_legacy_0248_tenant_id_for_chat(chat_id: int | None, create: bool=False, actor_user_id: int | None=None) -> str:
    explicit = getattr(_TENANT_CONTEXT, 'tenant_id', None)
    if explicit:
        return str(explicit)
    try:
        cid = int(chat_id or 0)
    except Exception:
        cid = 0
    root = _tenants_root()
    if cid:
        tid = str((root.get('chat_to_tenant') or {}).get(str(cid)) or '')
        if tid and tenant_get(tid):
            return tid
    if not create:
        return TENANT_PLATFORM_ID
    uid = int(actor_user_id or tenant_current_actor_user_id() or 0)
    if tenant_is_platform_owner_user(uid):
        tenant_bind_chat(cid, TENANT_PLATFORM_ID, changed_by=uid, force=True)
        return TENANT_PLATFORM_ID
    owner_uid = uid if tenant_user_is_chat_admin(cid, uid) else 0
    tid = tenant_create(_tenant_default_name(cid), owner_uid, cid, created_by=uid, deterministic_chat_id=cid)
    return tid
try:
    _v177_legacy_0248_tenant_id_for_chat.__name__ = 'tenant_id_for_chat'
except Exception:
    pass

def tenant_current_id(chat_id: int | None=None) -> str:
    explicit = getattr(_TENANT_CONTEXT, 'tenant_id', None)
    if explicit:
        return str(explicit)
    if chat_id is None:
        chat_id = current_state_chat_id()
    return tenant_id_for_chat(chat_id, create=False)

def tenant_create(name: str, owner_user_id: int, root_chat_id: int, created_by: int=0, deterministic_chat_id: int | None=None) -> str:
    root = _tenants_root()
    with _TENANT_LOCK:
        if deterministic_chat_id is not None:
            seed = hashlib.sha256(f'chat:{int(deterministic_chat_id)}'.encode('utf-8')).hexdigest()[:12]
            tid = f'chat_{seed}'
        else:
            tid = f't_{secrets.token_hex(6)}'
        while tid in root['tenants']:
            if deterministic_chat_id is not None:
                break
            tid = f't_{secrets.token_hex(6)}'
        row = _tenant_normalize(tid, {'name': str(name or _tenant_default_name(root_chat_id))[:80], 'owner_user_id': int(owner_user_id or 0), 'root_chat_id': int(root_chat_id or 0), 'chat_ids': [int(root_chat_id)] if root_chat_id else [], 'users': {}, 'settings': {}, 'created_by': int(created_by or 0), 'created_at': _tenant_now(), 'updated_at': _tenant_now()})
        root['tenants'][tid] = row
        if root_chat_id:
            tenant_bind_chat(int(root_chat_id), tid, changed_by=int(created_by or owner_user_id or 0), force=True)
        if owner_user_id:
            tenant_set_user_role(tid, int(owner_user_id), 'tenant_owner', changed_by=created_by, save=False)
        return tid

def tenant_bind_chat(chat_id: int, tenant_id: str, changed_by: int=0, force: bool=False) -> bool:
    cid = int(chat_id)
    row = tenant_get(tenant_id)
    if not row:
        return False
    root = _tenants_root()
    old_tid = str((root.get('chat_to_tenant') or {}).get(str(cid)) or '')
    if old_tid == str(tenant_id) and cid in [int(x) for x in row.get('chat_ids') or []]:
        try:
            st = get_chat_store(cid).setdefault('settings', {})
            expected_scope = int(row.get('root_chat_id') or cid)
            if str(st.get('tenant_id') or '') == str(tenant_id) and int(st.get('owner_scope_id') or expected_scope) == expected_scope:
                return True
        except Exception:
            pass
    if old_tid and old_tid != str(tenant_id) and (not force):
        return False
    if old_tid and old_tid != str(tenant_id):
        old = tenant_get(old_tid)
        if old:
            old['chat_ids'] = [int(x) for x in old.get('chat_ids') or [] if int(x) != cid]
            old['updated_at'] = _tenant_now()
    root['chat_to_tenant'][str(cid)] = str(tenant_id)
    if cid not in row['chat_ids']:
        row['chat_ids'].append(cid)
    row['updated_at'] = _tenant_now()
    try:
        store = get_chat_store(cid)
        store.setdefault('settings', {})['tenant_id'] = str(tenant_id)
        store['settings']['owner_scope_id'] = int(row.get('root_chat_id') or cid)
    except Exception:
        pass
    try:
        bot_journal('tenant_chat_bound', cid, f"tenant={tenant_id} old={old_tid or '-'} by={int(changed_by or 0)}")
    except Exception:
        pass
    if old_tid and old_tid != str(tenant_id):
        try:
            enforce = globals().get('tenant_v148_enforce_forward_isolation')
            if callable(enforce):
                enforce()
        except Exception as exc:
            log_error(f'tenant rebind forward cleanup {cid}: {exc}')
    return True

def tenant_unbind_chat(chat_id: int, changed_by: int=0) -> bool:
    cid = int(chat_id)
    root = _tenants_root()
    tid = str((root.get('chat_to_tenant') or {}).get(str(cid)) or '')
    row = tenant_get(tid)
    if not row or int(row.get('root_chat_id') or 0) == cid:
        return False
    root['chat_to_tenant'].pop(str(cid), None)
    row['chat_ids'] = [int(x) for x in row.get('chat_ids') or [] if int(x) != cid]
    row['updated_at'] = _tenant_now()
    new_tid = tenant_create(_tenant_default_name(cid), 0, cid, created_by=changed_by, deterministic_chat_id=cid)
    try:
        bot_journal('tenant_chat_unbound', cid, f'old={tid} new={new_tid} by={changed_by}')
    except Exception:
        pass
    return True

def tenant_role_for_user(user_id: int | None, tenant_id: str | None=None, chat_id: int | None=None) -> str:
    try:
        uid = int(user_id or 0)
    except Exception:
        uid = 0
    if tenant_is_platform_owner_user(uid):
        return 'platform_owner'
    tid = str(tenant_id or tenant_current_id(chat_id))
    row = tenant_get(tid)
    if not row or not uid:
        return 'standard'
    item = (row.get('users') or {}).get(str(uid)) or {}
    role = str(item.get('role') or 'standard')
    return role if role in TENANT_ROLE_ORDER else 'standard'

def tenant_user_spaces(user_id: int) -> list[dict]:
    uid = int(user_id)
    if tenant_is_platform_owner_user(uid):
        return tenant_all()
    out = []
    for row in tenant_all():
        if str(uid) in (row.get('users') or {}):
            out.append(row)
    return out

def tenant_set_user_role(tenant_id: str, user_id: int, role: str, changed_by: int=0, save: bool=True) -> bool:
    row = tenant_get(tenant_id)
    if not row:
        return False
    uid = int(user_id)
    role = str(role or 'viewer')
    if role not in TENANT_ROLE_ORDER:
        return False
    if role == 'tenant_owner':
        if str(tenant_id) == TENANT_PLATFORM_ID and uid != _tenant_platform_owner_user_id():
            return False
        old_owner = int(row.get('owner_user_id') or 0)
        if old_owner and old_owner != uid:
            row.setdefault('users', {}).setdefault(str(old_owner), {})['role'] = 'tenant_admin'
        row['owner_user_id'] = uid
    item = row.setdefault('users', {}).setdefault(str(uid), {})
    item['role'] = role
    item.setdefault('joined_at', _tenant_now())
    item['updated_at'] = _tenant_now()
    item['changed_by'] = int(changed_by or 0)
    row['updated_at'] = _tenant_now()
    if save:
        save_data(data, full=True)
        try:
            schedule_delta_backup(int(row.get('root_chat_id') or OWNER_ID or 0), delay=0.5, reason='tenant_user_role')
        except Exception:
            pass
    return True

def _v177_legacy_0249_tenant_can_manage(user_id: int | None, tenant_id: str | None=None, chat_id: int | None=None, owner_only: bool=False) -> bool:
    role = tenant_role_for_user(user_id, tenant_id, chat_id)
    if role == 'platform_owner':
        return True
    if owner_only:
        return role == 'tenant_owner'
    return role in {'tenant_owner', 'tenant_admin'}
try:
    _v177_legacy_0249_tenant_can_manage.__name__ = 'tenant_can_manage'
except Exception:
    pass

def tenant_user_is_chat_admin(chat_id: int, user_id: int) -> bool:
    try:
        cid = int(chat_id)
        uid = int(user_id)
    except Exception:
        return False
    if not cid or not uid:
        return False
    if tenant_is_platform_owner_user(uid):
        return True
    try:
        store = get_chat_store(cid)
        typ = str((store.get('info') or {}).get('type') or '')
        if typ == 'private' or cid > 0:
            return cid == uid
    except Exception:
        if cid > 0:
            return cid == uid
    try:
        member = bot.get_chat_member(cid, uid)
        return str(getattr(member, 'status', '') or '') in {'creator', 'administrator'}
    except Exception:
        return False

def tenant_chat_ids(tenant_id: str | None=None) -> list[int]:
    row = tenant_get(tenant_id or tenant_current_id())
    if not row:
        return []
    return sorted({int(x) for x in row.get('chat_ids') or []}, key=lambda x: get_chat_display_name(x).casefold())

def _v177_legacy_0250_tenant_same_space(chat_a: int, chat_b: int) -> bool:
    """True only for two explicitly bound chats in the same space.

    Unknown chat IDs must never inherit the platform tenant implicitly: an old/stale
    forwarding rule to an unseen chat is blocked until that chat is registered.
    """
    try:
        a = int(chat_a)
        b = int(chat_b)
    except Exception:
        return False
    if a == b:
        return True
    mapping = _tenants_root().get('chat_to_tenant') or {}
    ta = str(mapping.get(str(a)) or '')
    tb = str(mapping.get(str(b)) or '')
    return bool(ta and tb and (ta == tb) and tenant_get(ta))
try:
    _v177_legacy_0250_tenant_same_space.__name__ = 'tenant_same_space'
except Exception:
    pass

def _v177_legacy_0251_tenant_note_chat_seen(msg) -> None:
    try:
        chat_id = int(msg.chat.id)
        user_id = int(getattr(getattr(msg, 'from_user', None), 'id', 0) or 0)
    except Exception:
        return
    tid = tenant_id_for_chat(chat_id, create=True, actor_user_id=user_id)
    row = tenant_get(tid)
    if not row:
        return
    if not int(row.get('owner_user_id') or 0) and user_id and tenant_user_is_chat_admin(chat_id, user_id):
        tenant_set_user_role(tid, user_id, 'tenant_owner', changed_by=user_id, save=False)
    try:
        store = get_chat_store(chat_id)
        store.setdefault('settings', {})['tenant_id'] = tid
        store['settings']['owner_scope_id'] = int(row.get('root_chat_id') or chat_id)
    except Exception:
        pass
try:
    _v177_legacy_0251_tenant_note_chat_seen.__name__ = 'tenant_note_chat_seen'
except Exception:
    pass
_V148_ORIG_UPDATE_CHAT_INFO = _v177_legacy_0235_update_chat_info_from_message

def _v177_legacy_0236_update_chat_info_from_message(msg):
    result = None
    if callable(_V148_ORIG_UPDATE_CHAT_INFO):
        result = _V148_ORIG_UPDATE_CHAT_INFO(msg)
    try:
        tenant_note_chat_seen(msg)
    except Exception as exc:
        log_error(f'tenant_note_chat_seen: {exc}')
    return result
try:
    _v177_legacy_0236_update_chat_info_from_message.__name__ = 'update_chat_info_from_message'
except Exception:
    pass

def _v168_owner_access_ids() -> set[int]:
    gs = data.setdefault('_global_settings', {})
    raw = gs.get('owner_access_chat_ids_v168')
    if not isinstance(raw, list):
        raw = []
        gs['owner_access_chat_ids_v168'] = raw
    out = set()
    for value in raw or []:
        try:
            out.add(int(value))
        except Exception:
            pass
    return out

def _canon_get_additional_owner_ids__001() -> set[int]:
    return _v168_owner_access_ids()

def _canon_set_additional_owner__001(chat_id: int, enabled: bool):
    cid = int(chat_id)
    owners = _v168_owner_access_ids()
    if enabled:
        owners.add(cid)
    else:
        owners.discard(cid)
    gs = data.setdefault('_global_settings', {})
    gs['owner_access_chat_ids_v168'] = sorted(owners)

    def _persist_owner_access():
        try:
            save_data(data, root_only=True)
        except Exception as exc:
            try:
                log_error(f'v168 owner access persist {cid}: {exc}')
            except Exception:
                pass
    try:
        scheduler = globals().get('V166_CONFIG_IO_SCHEDULER')
        if scheduler is not None:
            scheduler.cancel('owner-access-root-v168')
            scheduler.schedule('owner-access-root-v168', 0.1, _persist_owner_access)
        else:
            _persist_owner_access()
    except Exception:
        _persist_owner_access()
    try:
        schedule_config_backup_for_chats(cid, delay=0.25)
    except Exception:
        pass

def _canon_is_primary_owner__001(chat_id: int) -> bool:
    try:
        cid = int(chat_id)
    except Exception:
        return False
    owner_uid = _tenant_platform_owner_user_id()
    if cid == owner_uid:
        return True
    actor = tenant_current_actor_user_id()
    return bool(actor == owner_uid and cid in _v168_owner_access_ids())

def _canon_is_owner_chat__001(chat_id: int) -> bool:
    try:
        cid = int(chat_id)
    except Exception:
        return False
    owner_uid = _tenant_platform_owner_user_id()
    actor = tenant_current_actor_user_id()
    if cid == owner_uid:
        return True
    if actor == owner_uid:
        return cid in _v168_owner_access_ids()
    if actor:
        return tenant_can_manage(actor, chat_id=cid)
    row = tenant_get(tenant_id_for_chat(cid, create=False))
    return bool(row and int(row.get('root_chat_id') or 0) == cid)

def _canon_owner_scope_id__001(chat_id: int | None=None) -> int:
    try:
        cid = int(chat_id if chat_id is not None else current_state_chat_id() or OWNER_ID or 0)
    except Exception:
        cid = _tenant_platform_owner_user_id()
    row = tenant_get(tenant_id_for_chat(cid, create=False))
    return int((row or {}).get('root_chat_id') or cid or _tenant_platform_owner_user_id())

def _canon_owner_scoped_settings__001(chat_id: int | None=None) -> dict:
    tid = tenant_current_id(chat_id)
    row = tenant_get(tid)
    if not row:
        return data.setdefault('_global_settings', {})
    return row.setdefault('settings', {})

def _canon_bind_chat_to_owner_scope__001(chat_id: int, scope_id: int):
    tid = tenant_id_for_chat(int(scope_id), create=True, actor_user_id=tenant_current_actor_user_id())
    ok = tenant_bind_chat(int(chat_id), tid, changed_by=tenant_current_actor_user_id(), force=True)
    if ok:
        save_data(data, chat_ids=[int(chat_id), int(scope_id)], root_only=False)
    return ok

def _canon_collect_forward_menu_chats__001() -> dict:
    tid = tenant_current_id()
    result = {}
    resolver = globals().get('resolve_canonical_chat_id_v199')
    suspended = globals().get('is_forward_target_suspended_v199')
    for raw_cid in tenant_chat_ids(tid):
        try:
            cid = int(resolver(int(raw_cid))) if callable(resolver) else int(raw_cid)
            if callable(suspended) and suspended(cid):
                continue
            store = get_chat_store(cid)
            info = store.get('info') or {}
            result[str(cid)] = {'title': info.get('title') or get_chat_display_name(cid) or f'Чат {cid}', 'username': info.get('username'), 'type': info.get('type')}
        except Exception:
            continue
    return result

def _canon_collect_all_known_chat_ids__001(include_owner: bool=True) -> list[int]:
    resolver = globals().get('resolve_canonical_chat_id_v199')
    ids = []
    for raw in tenant_chat_ids(tenant_current_id()):
        try:
            cid = int(resolver(int(raw))) if callable(resolver) else int(raw)
        except Exception:
            continue
        if cid not in ids:
            ids.append(cid)
    if not include_owner:
        root_id = owner_scope_id(current_state_chat_id())
        ids = [cid for cid in ids if int(cid) != int(root_id)]
    return sorted(set(ids), key=lambda cid: get_chat_display_name(cid).casefold())
_V148_ORIG_RESOLVE_FORWARD_TARGETS = _v177_legacy_0140_resolve_forward_targets

def _canon_resolve_forward_targets__001(source_chat_id: int):
    resolver = globals().get('resolve_canonical_chat_id_v199')
    suspended = globals().get('is_forward_target_suspended_v199')
    src = int(resolver(int(source_chat_id))) if callable(resolver) else int(source_chat_id)
    rows = _V148_ORIG_RESOLVE_FORWARD_TARGETS(src) if callable(_V148_ORIG_RESOLVE_FORWARD_TARGETS) else []
    out = []
    seen = set()
    for dst, mode, fin in rows or []:
        dst = int(resolver(int(dst))) if callable(resolver) else int(dst)
        if dst in seen or (callable(suspended) and suspended(dst)):
            continue
        if tenant_same_space(src, dst):
            out.append((dst, mode, bool(fin)))
            seen.add(dst)
        else:
            try:
                bot_journal('tenant_cross_forward_blocked', src, f'dst={dst}')
            except Exception:
                pass
    return out
_V148_ORIG_ADD_FORWARD_LINK = _v177_legacy_0141_add_forward_link

def _v177_legacy_0142_add_forward_link(src_chat_id: int, dst_chat_id: int, mode: str):
    if not tenant_same_space(int(src_chat_id), int(dst_chat_id)):
        raise PermissionError('Нельзя связать пересылкой чаты из разных пространств')
    return _V148_ORIG_ADD_FORWARD_LINK(int(src_chat_id), int(dst_chat_id), mode)
try:
    _v177_legacy_0142_add_forward_link.__name__ = 'add_forward_link'
except Exception:
    pass

def _canon_clear_forward_all__001():
    """v148: очищает связи только текущего пространства, а не чужие контуры."""
    allowed = {str(x) for x in tenant_chat_ids(tenant_current_id())}
    fr = data.setdefault('forward_rules', {})
    ff = data.setdefault('forward_finance', {})
    for src in list(fr.keys()):
        if str(src) in allowed:
            fr.pop(src, None)
            ff.pop(src, None)
            continue
        for dst in list((fr.get(src) or {}).keys()):
            if str(dst) in allowed:
                (fr.get(src) or {}).pop(dst, None)
                (ff.get(src) or {}).pop(dst, None)
    data['forward_pair_order'] = [key for key in data.get('forward_pair_order') or [] if not any((part in allowed for part in str(key).split(':', 1)))]
    persist_forward_rules_to_owner()
    save_data(data, full=True)
_V148_ORIG_COLLECT_FORWARD_PAIRS = _v177_legacy_0189_collect_forward_pairs_for_menu

def _v177_legacy_0190_collect_forward_pairs_for_menu() -> list[tuple[int, int]]:
    rows = _V148_ORIG_COLLECT_FORWARD_PAIRS() if callable(_V148_ORIG_COLLECT_FORWARD_PAIRS) else []
    tid = tenant_current_id()
    allowed = set(tenant_chat_ids(tid))
    return [(int(a), int(b)) for a, b in rows if int(a) in allowed and int(b) in allowed]
try:
    _v177_legacy_0190_collect_forward_pairs_for_menu.__name__ = 'collect_forward_pairs_for_menu'
except Exception:
    pass
_V148_ORIG_GET_CONNECTED = _v177_legacy_0059_get_connected_chat_ids

def _canon_get_connected_chat_ids__001(chat_id: int):
    rows = _V148_ORIG_GET_CONNECTED(int(chat_id)) if callable(_V148_ORIG_GET_CONNECTED) else []
    return [int(cid) for cid in rows if tenant_same_space(int(chat_id), int(cid))]

def _tenant_settings_for_context(chat_id: int | None=None) -> dict:
    return owner_scoped_settings(chat_id)

def _v177_legacy_0147_forward_copy_edit_mode(chat_id: int | None=None) -> str:
    mode = str(_tenant_settings_for_context(chat_id).get('forward_copy_edit_mode') or 'normal').lower()
    return mode if mode in FORWARD_COPY_EDIT_MODES and version_mode_feature('forward_copy_edit') else 'normal'
try:
    _v177_legacy_0147_forward_copy_edit_mode.__name__ = 'forward_copy_edit_mode'
except Exception:
    pass

def _v177_legacy_0149_set_forward_copy_edit_mode(chat_id: int, mode: str):
    mode = str(mode or 'normal').lower()
    if mode not in FORWARD_COPY_EDIT_MODES:
        mode = 'normal'
    _tenant_settings_for_context(chat_id)['forward_copy_edit_mode'] = mode
    save_data(data, root_only=True)
    return mode
try:
    _v177_legacy_0149_set_forward_copy_edit_mode.__name__ = 'set_forward_copy_edit_mode'
except Exception:
    pass

def _canon_reminder_ui_mode__001() -> str:
    mode = str(_tenant_settings_for_context().get('reminder_ui_mode_v142') or 'new').lower()
    return mode if mode in {'old', 'new'} else 'new'

def _canon_set_reminder_ui_mode__001(mode: str) -> str:
    mode = 'new' if str(mode).lower() == 'new' else 'old'
    _tenant_settings_for_context()['reminder_ui_mode_v142'] = mode
    save_data(data, root_only=True)
    return mode

def _canon_internal_timer_seconds__001(key: str, fallback=None) -> float:
    spec = INTERNAL_TIMER_DEFS.get(str(key), {})
    default = spec.get('default', fallback if fallback is not None else 0)
    try:
        value = _tenant_settings_for_context().setdefault('internal_timers', {}).get(str(key), default)
        return float(value)
    except Exception:
        return float(default or 0)

def _canon_set_internal_timer_seconds__001(key: str, seconds: int | float) -> float:
    spec = INTERNAL_TIMER_DEFS.get(str(key))
    if not spec:
        raise KeyError(key)
    value = max(float(spec.get('min', 0)), min(float(spec.get('max', 10 ** 9)), float(seconds)))
    _tenant_settings_for_context().setdefault('internal_timers', {})[str(key)] = value
    save_data(data, root_only=True)
    return value

def _canon_backup_excel_all_enabled__001(chat_id: int | None=None) -> bool:
    return bool(_tenant_settings_for_context(chat_id).get('backup_excel_all_enabled', True))

def _canon_set_backup_excel_all_enabled__001(enabled: bool, chat_id: int | None=None):
    _tenant_settings_for_context(chat_id)['backup_excel_all_enabled'] = bool(enabled)
    save_data(data, root_only=True)

def _canon_excel_interface_mode__001(chat_id: int | None=None) -> str:
    mode = str(_tenant_settings_for_context(chat_id).get('excel_interface_mode') or 'new').lower()
    return mode if mode in {'old', 'new'} else 'new'

def _canon_set_excel_interface_mode__001(mode: str) -> str:
    mode = 'old' if str(mode).lower() == 'old' else 'new'
    _tenant_settings_for_context()['excel_interface_mode'] = mode
    save_data(data, root_only=True)
    return mode

def _canon_excel_new_export_options__001() -> dict:
    settings = _tenant_settings_for_context()
    options = settings.get('excel_new_export_options')
    if not isinstance(options, dict):
        options = {'old_table': False, 'comments': False, 'notes': True, 'description_column': False}
        settings['excel_new_export_options'] = options
    return normalize_excel_export_options(options)

def _canon_toggle_excel_new_export_option__001(option: str) -> dict:
    opts = excel_new_export_options()
    option = str(option or '')
    if option in opts:
        opts[option] = not bool(opts.get(option))
    if option == 'old_table' and opts.get('old_table'):
        opts['comments'] = opts['notes'] = opts['description_column'] = False
    elif option in {'comments', 'notes', 'description_column'} and opts.get(option):
        opts['old_table'] = False
        if option in {'comments', 'notes'}:
            for other in {'comments', 'notes'} - {option}:
                opts[other] = False
    _tenant_settings_for_context()['excel_new_export_options'] = dict(opts)
    save_data(data, root_only=True)
    return opts

def _canon_excel_table_style__001(chat_id: int) -> str:
    mode = _normalize_excel_table_style(_tenant_settings_for_context(chat_id).get('excel_table_style'))
    return mode or 'new_notes'

def _canon_set_excel_table_style__001(chat_id: int, mode: str) -> str:
    mode = _normalize_excel_table_style(mode) or 'new_notes'
    _tenant_settings_for_context(chat_id)['excel_table_style'] = mode
    try:
        get_chat_store(int(chat_id)).setdefault('settings', {})['excel_table_style'] = mode
    except Exception:
        pass
    save_data(data, chat_ids=[int(chat_id)])
    return mode
_V148_ORIG_REMINDER_ITEMS = _v177_legacy_0119_reminder_items
_V148_ORIG_REMINDER_CFG = _v177_legacy_0120_reminder_cfg
_V148_ORIG_REMINDER_CREATE = _v177_legacy_0121_reminder_create

def _reminder_context_filter_active() -> bool:
    return bool(getattr(_TENANT_CONTEXT, 'tenant_id', None) or current_state_chat_id() is not None)

def _canon_reminder_items__001(include_completed: bool=False) -> list[tuple[int, dict]]:
    rows = _V148_ORIG_REMINDER_ITEMS(include_completed=include_completed) if callable(_V148_ORIG_REMINDER_ITEMS) else []
    if not _reminder_context_filter_active():
        return rows
    tid = tenant_current_id()
    return [(rid, cfg) for rid, cfg in rows if str((cfg or {}).get('tenant_id') or TENANT_PLATFORM_ID) == tid]

def _canon_reminder_cfg__001(reminder_id: int | str | None=None, create: bool=False) -> dict | None:
    cfg = _V148_ORIG_REMINDER_CFG(reminder_id, create=create) if callable(_V148_ORIG_REMINDER_CFG) else None
    if not isinstance(cfg, dict):
        return cfg
    if create and (not cfg.get('tenant_id')):
        cfg['tenant_id'] = tenant_current_id()
    if _reminder_context_filter_active() and str(cfg.get('tenant_id') or TENANT_PLATFORM_ID) != tenant_current_id():
        return None
    return cfg

def _canon_reminder_create__001() -> tuple[int, dict]:
    rid, cfg = _V148_ORIG_REMINDER_CREATE()
    cfg['tenant_id'] = tenant_current_id()
    _reminder_save('tenant_reminder_add')
    return (rid, cfg)

def reminder_cfg_global_for_completion(reminder_id: int | str | None) -> dict | None:
    """Canonical delivered-completion lookup.

    Reminder IDs are global.  UI tenant context must never hide a reminder that was
    actually delivered to the current recipient chat.  This helper deliberately
    bypasses the v148 UI-context filter but does not grant any action by itself;
    callers must still validate the real recipient chat and selected completion mode.
    """
    if reminder_id is None:
        return None
    try:
        rid = int(reminder_id)
    except Exception:
        return None
    try:
        cfg = _V148_ORIG_REMINDER_CFG(rid, create=False) if callable(_V148_ORIG_REMINDER_CFG) else None
    except Exception:
        cfg = None
    return cfg if isinstance(cfg, dict) else None

def reminder_items_global_for_completion(include_completed: bool=False) -> list[tuple[int, dict]]:
    """Return the canonical global reminder registry for recipient-side actions.

    Unlike _reminder_items/_v149_reminder_all_rows this helper never consults the
    current Telegram tenant context.  It is intentionally narrow: callers still
    authorize every action by exact recipient chat membership.
    """
    try:
        rows = _V148_ORIG_REMINDER_ITEMS(include_completed=bool(include_completed)) if callable(_V148_ORIG_REMINDER_ITEMS) else []
    except Exception:
        rows = []
    return [(int(rid), cfg) for rid, cfg in list(rows or []) if isinstance(cfg, dict)]

def _canon_security_role_for_user__001(user_id: int | None) -> str:
    return tenant_role_for_user(user_id, chat_id=current_state_chat_id())

def _canon_security_set_role__001(user_id: int, role: str) -> str:
    tid = tenant_current_id()
    role_map = {'finance_admin': 'tenant_admin', 'forward_manager': 'operator', 'secret_manager': 'operator', 'reminder_manager': 'operator', 'expense_input': 'operator', 'view_only': 'viewer', 'standard': 'operator'}
    tenant_role = role if role in TENANT_ROLE_ORDER else role_map.get(str(role), 'viewer')
    if not tenant_can_manage(tenant_current_actor_user_id(), tid):
        raise PermissionError('Недостаточно прав')
    tenant_set_user_role(tid, int(user_id), tenant_role, changed_by=tenant_current_actor_user_id())
    return tenant_role

def _canon_security_known_users__001() -> list[dict]:
    tid = tenant_current_id()
    row = tenant_get(tid) or {}
    allowed = {str(uid) for uid in (row.get('users') or {}).keys()}
    merged = {}
    for cid in tenant_chat_ids(tid):
        try:
            store = get_chat_store(cid)
            for item in (store.get('known_users') or {}).values():
                if not isinstance(item, dict):
                    continue
                uid = str(int(item.get('id') or 0))
                if uid == '0' or (allowed and uid not in allowed):
                    continue
                merged[uid] = dict(item)
        except Exception:
            pass
    for uid, membership in (row.get('users') or {}).items():
        merged.setdefault(str(uid), {'id': int(uid), 'first_name': '', 'username': '', 'last_seen_ts': 0})
        merged[str(uid)]['tenant_role'] = str((membership or {}).get('role') or 'viewer')
    return sorted(merged.values(), key=lambda x: (float(x.get('last_seen_ts') or 0), int(x.get('id') or 0)), reverse=True)

def _v177_legacy_0109_security_user_allowed(user_id: int | None, capability: str) -> bool:
    role = tenant_role_for_user(user_id, chat_id=current_state_chat_id())
    if role in {'platform_owner', 'tenant_owner', 'tenant_admin'}:
        return True
    if role == 'operator':
        return str(capability or 'view') in {'view', 'finance_input', 'finance_manage', 'export', 'forward_manage', 'reminder_manage'}
    if role == 'viewer':
        return str(capability or 'view') == 'view'
    return str(capability or 'view') in {'view', 'finance_input'}
try:
    _v177_legacy_0109_security_user_allowed.__name__ = 'security_user_allowed'
except Exception:
    pass

def _tenant_action_target_chat_ids(action: str) -> set[int]:
    raw = str(action or '')
    ids = set()
    for token in re.findall('(?<!\\d)-?\\d{5,16}(?!\\d)', raw):
        try:
            ids.add(int(token))
        except Exception:
            pass
    return ids

def _v177_legacy_0111_safety_permission_allowed(user_id: int | None, chat_id: int | None, action: str) -> bool:
    try:
        uid = int(user_id or 0)
        cid = int(chat_id or 0)
    except Exception:
        return False
    if tenant_is_platform_owner_user(uid):
        return True
    tid = tenant_id_for_chat(cid, create=False)
    for target in _tenant_action_target_chat_ids(action):
        if str(target) in (_tenants_root().get('chat_to_tenant') or {}) and tenant_id_for_chat(target, create=False) != tid:
            return False
    role = tenant_role_for_user(uid, tid)
    normalized = str(action or '').lower()
    if normalized.startswith(('mega_', 'restore_', 'journal_', 'runtime_', 'problem_tasks', 'safety_profile', 'additional_owners', 'addown:', 'keepalive_', 'info_queues', 'info_delta_status', 'process_center', 'integrity_status', 'expense_')):
        return False
    if normalized.startswith(('sp:', 'tenant:')):
        write_actions = ('sp:chatlink', 'sp:userlink', 'sp:role', 'sp:transfer', 'sp:rename', 'sp:unlink')
        if normalized.startswith(write_actions):
            return role in {'tenant_owner', 'tenant_admin'}
        return role in {'tenant_owner', 'tenant_admin', 'operator', 'viewer'}
    if any((x in normalized for x in ('reset', 'delete', 'del_selected', 'fw_new_clear', 'security_role'))):
        return role in {'tenant_owner', 'tenant_admin'}
    if not safety_profile_new_enabled():
        return True
    return security_user_allowed(uid, _security_callback_capability(normalized))
try:
    _v177_legacy_0111_safety_permission_allowed.__name__ = 'safety_permission_allowed'
except Exception:
    pass

def _tenant_bot_username() -> str:
    global _TENANT_BOT_USERNAME
    if _TENANT_BOT_USERNAME:
        return _TENANT_BOT_USERNAME
    try:
        _TENANT_BOT_USERNAME = str(getattr(bot.get_me(), 'username', '') or '').lstrip('@')
    except Exception:
        _TENANT_BOT_USERNAME = ''
    return _TENANT_BOT_USERNAME

def _tenant_token_hash(raw: str) -> str:
    return hashlib.sha256(str(raw).encode('utf-8')).hexdigest()

def _tenant_prune_invites() -> None:
    root = _tenants_root()
    now_ts = time.time()
    tokens = root.setdefault('invite_tokens', {})
    for key, row in list(tokens.items()):
        if not isinstance(row, dict):
            tokens.pop(key, None)
            continue
        if bool(row.get('revoked')) or float(row.get('expires_ts') or 0) < now_ts or int(row.get('uses') or 0) >= int(row.get('max_uses') or 1):
            if now_ts - float(row.get('created_ts') or now_ts) > 86400:
                tokens.pop(key, None)
    if len(tokens) > 500:
        ordered = sorted(tokens.items(), key=lambda kv: float((kv[1] or {}).get('created_ts') or 0))
        for key, _ in ordered[:-500]:
            tokens.pop(key, None)

def _v177_legacy_0252_tenant_create_invite(tenant_id: str, kind: str, role: str, created_by: int, max_uses: int=1, ttl_hours: int=72) -> str:
    row = tenant_get(tenant_id)
    if not row:
        raise ValueError('Пространство не найдено')
    kind = 'chat' if str(kind) == 'chat' else 'user'
    role = str(role or 'operator')
    if role not in TENANT_ROLE_ORDER or role == 'tenant_owner':
        role = 'operator'
    raw = secrets.token_urlsafe(12).replace('-', '').replace('_', '')[:18]
    prefix = 'sc' if kind == 'chat' else 'su'
    payload = f'{prefix}_{raw}'
    now_ts = time.time()
    _tenant_prune_invites()
    _tenants_root().setdefault('invite_tokens', {})[_tenant_token_hash(payload)] = {'tenant_id': str(tenant_id), 'kind': kind, 'role': role, 'created_by': int(created_by or 0), 'created_at': _tenant_now(), 'created_ts': now_ts, 'expires_ts': now_ts + max(1, int(ttl_hours)) * 3600, 'max_uses': max(1, int(max_uses)), 'uses': 0, 'revoked': False}
    save_data(data, root_only=True)
    return payload
try:
    _v177_legacy_0252_tenant_create_invite.__name__ = 'tenant_create_invite'
except Exception:
    pass

def _v177_legacy_0253_tenant_consume_invite(payload: str, user_id: int, chat_id: int, chat_type: str='') -> tuple[bool, str, str]:
    key = _tenant_token_hash(str(payload or '').strip())
    row = (_tenants_root().get('invite_tokens') or {}).get(key)
    if not isinstance(row, dict):
        return (False, 'Ссылка недействительна или уже использована.', '')
    if row.get('revoked') or float(row.get('expires_ts') or 0) < time.time() or int(row.get('uses') or 0) >= int(row.get('max_uses') or 1):
        return (False, 'Срок действия ссылки закончился.', '')
    tid = str(row.get('tenant_id') or '')
    tenant = tenant_get(tid)
    if not tenant:
        return (False, 'Пространство не найдено.', '')
    kind = str(row.get('kind') or 'user')
    if kind == 'chat':
        if str(chat_type or '') == 'private' or int(chat_id) > 0:
            return (False, 'Эту ссылку нужно использовать при добавлении бота в группу/канал.', tid)
        if not tenant_user_is_chat_admin(int(chat_id), int(user_id)):
            return (False, 'Привязать чат может только его администратор.', tid)
        old_tid = str((_tenants_root().get('chat_to_tenant') or {}).get(str(int(chat_id))) or '')
        if old_tid and old_tid != tid:
            old = tenant_get(old_tid)
            if old and int(old.get('owner_user_id') or 0):
                return (False, 'Этот чат уже принадлежит другому пространству.', tid)
        tenant_bind_chat(int(chat_id), tid, changed_by=int(user_id), force=True)
        message = f"✅ Чат подключён к пространству «{tenant.get('name')}»."
    else:
        tenant_set_user_role(tid, int(user_id), str(row.get('role') or 'operator'), changed_by=int(row.get('created_by') or 0), save=False)
        message = f"✅ Вы подключены к пространству «{tenant.get('name')}» как {TENANT_ROLE_LABELS.get(str(row.get('role')), str(row.get('role')))}."
    row['uses'] = int(row.get('uses') or 0) + 1
    row['last_used_at'] = _tenant_now()
    row['last_used_by'] = int(user_id or 0)
    save_data(data, full=True)
    return (True, message, tid)
try:
    _v177_legacy_0253_tenant_consume_invite.__name__ = 'tenant_consume_invite'
except Exception:
    pass

def tenant_invite_link(payload: str) -> str:
    username = _tenant_bot_username()
    if not username:
        return payload
    if str(payload).startswith('sc_'):
        return f'https://t.me/{username}?startgroup={payload}'
    return f'https://t.me/{username}?start={payload}'

def tenant_handle_start_payload(msg) -> bool:
    text = str(getattr(msg, 'text', '') or '').strip()
    parts = text.split(maxsplit=1)
    if len(parts) < 2:
        return False
    payload = parts[1].strip()
    if not payload.startswith(('su_', 'sc_')):
        return False
    try:
        uid = int(getattr(getattr(msg, 'from_user', None), 'id', 0) or 0)
        cid = int(msg.chat.id)
        typ = str(getattr(msg.chat, 'type', '') or '')
        ok, message, _tid = tenant_consume_invite(payload, uid, cid, typ)
        bot.send_message(cid, message)
        try:
            bot_journal('tenant_invite_consumed' if ok else 'tenant_invite_rejected', cid, f'user={uid} payload={payload[:5]}***')
        except Exception:
            pass
    except Exception as exc:
        bot.send_message(msg.chat.id, f'❌ Не удалось применить ссылку: {str(exc)[:300]}')
    return True

def _v177_legacy_0254_tenant_visible_spaces(user_id: int) -> list[dict]:
    return tenant_all() if tenant_is_platform_owner_user(user_id) else tenant_user_spaces(user_id)
try:
    _v177_legacy_0254_tenant_visible_spaces.__name__ = 'tenant_visible_spaces'
except Exception:
    pass

def _v177_legacy_0255_tenant_dashboard_text(chat_id: int, user_id: int) -> str:
    current_tid = tenant_id_for_chat(chat_id, create=True, actor_user_id=user_id)
    current = tenant_get(current_tid) or {}
    spaces = tenant_visible_spaces(user_id)
    role = tenant_role_for_user(user_id, current_tid)
    return f"🏢 ПРОСТРАНСТВА · ИЗОЛИРОВАННЫЙ РЕЖИМ\n\nТекущий чат: {get_chat_display_name(chat_id)}\nПространство: {current.get('name') or current_tid}\nРоль: {TENANT_ROLE_LABELS.get(role, role)}\nЧатов в пространстве: {len(current.get('chat_ids') or [])}\nПодключённых пользователей: {len(current.get('users') or {})}\n\nДоступно пространств: {len(spaces)}\nЧужие чаты, настройки, финансы, напоминания и пересылки здесь не отображаются."
try:
    _v177_legacy_0255_tenant_dashboard_text.__name__ = 'tenant_dashboard_text'
except Exception:
    pass

def _v177_legacy_0256_tenant_dashboard_keyboard(chat_id: int, user_id: int):
    kb = types.InlineKeyboardMarkup(row_width=1)
    current_tid = tenant_id_for_chat(chat_id, create=True, actor_user_id=user_id)
    for row in tenant_visible_spaces(user_id)[:25]:
        tid = str(row.get('id'))
        mark = '✅' if tid == current_tid else '▫️'
        kb.row(IB(f"{mark} {row.get('name')} · {len(row.get('chat_ids') or [])} ч.", callback_data=f'sp:open:{tid}'))
    if tenant_can_manage(user_id, current_tid):
        kb.row(IB('💬 Чаты пространства', callback_data=f'sp:chats:{current_tid}'))
        kb.row(IB('👥 Пользователи', callback_data=f'sp:users:{current_tid}'))
        kb.row(IB('🔗 Ссылка для подключения чата', callback_data=f'sp:chatlink:{current_tid}'))
        kb.row(IB('👤 Ссылка для пользователя', callback_data=f'sp:userlink:{current_tid}:operator'))
    kb.row(IB('❌ Закрыть', callback_data='info_close'))
    return kb
try:
    _v177_legacy_0256_tenant_dashboard_keyboard.__name__ = 'tenant_dashboard_keyboard'
except Exception:
    pass

def _v177_legacy_0257_tenant_detail_text(tenant_id: str, viewer_user_id: int) -> str:
    row = tenant_get(tenant_id)
    visible_ids = {str(item.get('id')) for item in tenant_visible_spaces(viewer_user_id)}
    if not row or str(tenant_id) not in visible_ids:
        return '❌ Пространство недоступно.'
    owner = int(row.get('owner_user_id') or 0)
    lines = [f"🏢 {row.get('name')}", '', f"ID: {row.get('id')}", f"Владелец: {(security_user_display(owner) if owner else 'не назначен')}", f"Корневой чат: {get_chat_display_name(int(row.get('root_chat_id') or 0))}", f"Чатов: {len(row.get('chat_ids') or [])}", f"Пользователей: {len(row.get('users') or {})}", '', 'Чаты:']
    for cid in row.get('chat_ids') or []:
        lines.append(f'• {get_chat_display_name(int(cid))} · {int(cid)}')
    return '\n'.join(lines)[:3900]
try:
    _v177_legacy_0257_tenant_detail_text.__name__ = 'tenant_detail_text'
except Exception:
    pass

def tenant_users_text(tenant_id: str) -> str:
    row = tenant_get(tenant_id) or {}
    lines = [f"👥 ПОЛЬЗОВАТЕЛИ · {row.get('name')}", '']
    for uid, item in sorted((row.get('users') or {}).items(), key=lambda kv: (TENANT_ROLE_ORDER.index(str((kv[1] or {}).get('role') or 'viewer')), int(kv[0]))):
        role = str((item or {}).get('role') or 'viewer')
        lines.append(f'• {security_user_display(int(uid))} · {TENANT_ROLE_LABELS.get(role, role)} · {uid}')
    if len(lines) == 2:
        lines.append('Нет подключённых пользователей.')
    return '\n'.join(lines)[:3900]

def _v177_legacy_0258_tenant_chats_text(tenant_id: str) -> str:
    row = tenant_get(tenant_id) or {}
    lines = [f"💬 ЧАТЫ · {row.get('name')}", '']
    for cid in row.get('chat_ids') or []:
        marker = '🏠' if int(cid) == int(row.get('root_chat_id') or 0) else '•'
        lines.append(f'{marker} {get_chat_display_name(int(cid))} · {int(cid)}')
    return '\n'.join(lines)[:3900]
try:
    _v177_legacy_0258_tenant_chats_text.__name__ = 'tenant_chats_text'
except Exception:
    pass

def _v177_legacy_0260_tenant_handle_callback(call, data_str: str) -> bool:
    raw = str(data_str or '')
    if not raw.startswith('sp:'):
        return False
    chat_id = int(call.message.chat.id)
    user_id = int(getattr(call.from_user, 'id', 0) or 0)
    parts = raw.split(':')
    action = parts[1] if len(parts) > 1 else ''
    tid = parts[2] if len(parts) > 2 else tenant_id_for_chat(chat_id, create=True, actor_user_id=user_id)
    if action == 'dashboard':
        safe_edit(bot, call, tenant_dashboard_text(chat_id, user_id), reply_markup=tenant_dashboard_keyboard(chat_id, user_id))
        return True
    if not tenant_is_platform_owner_user(user_id) and (not any((str(r.get('id')) == tid for r in tenant_visible_spaces(user_id)))):
        bot.answer_callback_query(call.id, 'Пространство недоступно.', show_alert=True)
        return True
    if action == 'open':
        kb = types.InlineKeyboardMarkup(row_width=1)
        if tenant_can_manage(user_id, tid):
            kb.row(IB('💬 Чаты', callback_data=f'sp:chats:{tid}'), IB('👥 Пользователи', callback_data=f'sp:users:{tid}'))
            kb.row(IB('🔗 Подключить чат', callback_data=f'sp:chatlink:{tid}'))
            kb.row(IB('👤 Пригласить оператора', callback_data=f'sp:userlink:{tid}:operator'))
            kb.row(IB('👁 Пригласить зрителя', callback_data=f'sp:userlink:{tid}:viewer'))
        kb.row(IB('🔙 К пространствам', callback_data='sp:list:x'))
        safe_edit(bot, call, tenant_detail_text(tid, user_id), reply_markup=kb)
        return True
    if action == 'list':
        safe_edit(bot, call, tenant_dashboard_text(chat_id, user_id), reply_markup=tenant_dashboard_keyboard(chat_id, user_id))
        return True
    if action in {'chatlink', 'userlink'} and (not tenant_can_manage(user_id, tid)):
        bot.answer_callback_query(call.id, 'Недостаточно прав.', show_alert=True)
        return True
    if action == 'chats':
        kb = types.InlineKeyboardMarkup()
        kb.row(IB('🔙 Назад', callback_data=f'sp:open:{tid}'))
        safe_edit(bot, call, tenant_chats_text(tid), reply_markup=kb)
        return True
    if action == 'users':
        kb = types.InlineKeyboardMarkup()
        kb.row(IB('🔙 Назад', callback_data=f'sp:open:{tid}'))
        safe_edit(bot, call, tenant_users_text(tid), reply_markup=kb)
        return True
    if action == 'chatlink':
        payload = tenant_create_invite(tid, 'chat', 'tenant_admin', user_id, max_uses=1, ttl_hours=72)
        text = '🔗 ССЫЛКА ДЛЯ ПОДКЛЮЧЕНИЯ ЧАТА\n\n' + tenant_invite_link(payload) + f'\n\nКод: {payload}' + f'\nВ уже существующем чате можно выполнить: /space_join {payload}' + '\n\nОдноразовая, действует 72 часа. Привязку должен подтвердить администратор целевого чата.'
        kb = types.InlineKeyboardMarkup()
        kb.row(IB('🔙 Назад', callback_data=f'sp:open:{tid}'))
        safe_edit(bot, call, text, reply_markup=kb)
        return True
    if action == 'userlink':
        role = parts[3] if len(parts) > 3 else 'operator'
        payload = tenant_create_invite(tid, 'user', role, user_id, max_uses=20, ttl_hours=72)
        text = f'👤 ССЫЛКА ДЛЯ ПОЛЬЗОВАТЕЛЯ\n\n{tenant_invite_link(payload)}\n\nРоль: {TENANT_ROLE_LABELS.get(role, role)}. До 20 использований, 72 часа.'
        kb = types.InlineKeyboardMarkup()
        kb.row(IB('🔙 Назад', callback_data=f'sp:open:{tid}'))
        safe_edit(bot, call, text, reply_markup=kb)
        return True
    return True
try:
    _v177_legacy_0260_tenant_handle_callback.__name__ = 'tenant_handle_callback'
except Exception:
    pass

def _tenant_command_parts(msg) -> list[str]:
    return str(getattr(msg, 'text', '') or '').strip().split()

def _tenant_send_dashboard(msg):
    uid = int(getattr(getattr(msg, 'from_user', None), 'id', 0) or 0)
    cid = int(msg.chat.id)
    tenant_note_chat_seen(msg)
    bot.send_message(cid, tenant_dashboard_text(cid, uid), reply_markup=tenant_dashboard_keyboard(cid, uid))

@bot.message_handler(commands=['space', 'spaces', 'tenant', 'пространство', 'пространства'])
def cmd_tenant_space(msg):
    schedule_command_delete(msg)
    _tenant_send_dashboard(msg)

@bot.message_handler(commands=['space_create', 'tenant_create'])
def cmd_tenant_create(msg):
    schedule_command_delete(msg)
    uid = int(getattr(getattr(msg, 'from_user', None), 'id', 0) or 0)
    cid = int(msg.chat.id)
    if not tenant_user_is_chat_admin(cid, uid):
        send_and_auto_delete(cid, '❌ Создать пространство может владелец личного чата или администратор группы.', 12)
        return
    mapped_tid = str((_tenants_root().get('chat_to_tenant') or {}).get(str(cid)) or '')
    current_tid = mapped_tid or ''
    current = tenant_get(current_tid) if current_tid else None
    if current and (int(current.get('owner_user_id') or 0) or current_tid == TENANT_PLATFORM_ID):
        send_and_auto_delete(cid, '❌ Этот чат уже принадлежит пространству. Используйте /space.', 12)
        return
    parts = _tenant_command_parts(msg)
    name = ' '.join(parts[1:]).strip() or _tenant_default_name(cid)
    if current:
        current['name'] = name[:80]
        tenant_set_user_role(current_tid, uid, 'tenant_owner', changed_by=uid, save=False)
        tid = current_tid
    else:
        tid = tenant_create(name, uid, cid, created_by=uid, deterministic_chat_id=cid)
    save_data(data, full=True)
    bot.send_message(cid, f"✅ Создано пространство «{tenant_get(tid).get('name')}».\nОткройте /space для управления.")

@bot.message_handler(commands=['space_claim', 'tenant_claim'])
def cmd_tenant_claim(msg):
    schedule_command_delete(msg)
    uid = int(getattr(getattr(msg, 'from_user', None), 'id', 0) or 0)
    cid = int(msg.chat.id)
    if not tenant_user_is_chat_admin(cid, uid):
        send_and_auto_delete(cid, '❌ Подтвердить владение может только администратор этого чата.', 12)
        return
    tid = tenant_id_for_chat(cid, create=True, actor_user_id=uid)
    row = tenant_get(tid)
    if int(row.get('owner_user_id') or 0) and (not tenant_is_platform_owner_user(uid)):
        send_and_auto_delete(cid, '❌ У пространства уже есть владелец.', 12)
        return
    parts = _tenant_command_parts(msg)
    if len(parts) > 1:
        row['name'] = ' '.join(parts[1:])[:80]
    tenant_set_user_role(tid, uid, 'tenant_owner', changed_by=uid)
    bot.send_message(cid, f"✅ Вы стали владельцем пространства «{row.get('name')}».")

@bot.message_handler(commands=['space_join', 'tenant_join'])
def cmd_tenant_join(msg):
    schedule_command_delete(msg)
    parts = _tenant_command_parts(msg)
    if len(parts) < 2:
        send_and_auto_delete(msg.chat.id, 'Использование: /space_join КОД_ССЫЛКИ', 12)
        return
    payload = parts[1].strip()
    uid = int(getattr(getattr(msg, 'from_user', None), 'id', 0) or 0)
    cid = int(msg.chat.id)
    ok, text, _ = tenant_consume_invite(payload, uid, cid, str(getattr(msg.chat, 'type', '') or ''))
    bot.send_message(cid, text)

@bot.message_handler(commands=['space_chat_link', 'tenant_chat_link'])
def cmd_tenant_chat_link(msg):
    schedule_command_delete(msg)
    uid = int(getattr(getattr(msg, 'from_user', None), 'id', 0) or 0)
    cid = int(msg.chat.id)
    tid = tenant_id_for_chat(cid, create=True, actor_user_id=uid)
    if not tenant_can_manage(uid, tid):
        send_and_auto_delete(cid, '❌ Недостаточно прав.', 12)
        return
    payload = tenant_create_invite(tid, 'chat', 'tenant_admin', uid, max_uses=1, ttl_hours=72)
    bot.send_message(cid, '🔗 Ссылка для подключения одного чата (72 часа):\n' + tenant_invite_link(payload) + f'\n\nКод: {payload}\nВ уже существующем чате: /space_join {payload}')

@bot.message_handler(commands=['space_user_link', 'tenant_user_link'])
def cmd_tenant_user_link(msg):
    schedule_command_delete(msg)
    uid = int(getattr(getattr(msg, 'from_user', None), 'id', 0) or 0)
    cid = int(msg.chat.id)
    tid = tenant_id_for_chat(cid, create=True, actor_user_id=uid)
    if not tenant_can_manage(uid, tid):
        send_and_auto_delete(cid, '❌ Недостаточно прав.', 12)
        return
    parts = _tenant_command_parts(msg)
    role = parts[1].lower() if len(parts) > 1 else 'operator'
    if role not in {'tenant_admin', 'operator', 'viewer'}:
        role = 'operator'
    payload = tenant_create_invite(tid, 'user', role, uid, max_uses=20, ttl_hours=72)
    bot.send_message(cid, f'👤 Ссылка для пользователей ({TENANT_ROLE_LABELS.get(role)}):\n{tenant_invite_link(payload)}')

@bot.message_handler(commands=['space_users', 'tenant_users'])
def cmd_tenant_users(msg):
    schedule_command_delete(msg)
    uid = int(getattr(getattr(msg, 'from_user', None), 'id', 0) or 0)
    cid = int(msg.chat.id)
    tid = tenant_id_for_chat(cid, create=True, actor_user_id=uid)
    if not tenant_can_manage(uid, tid):
        send_and_auto_delete(cid, '❌ Недостаточно прав.', 12)
        return
    bot.send_message(cid, tenant_users_text(tid))

@bot.message_handler(commands=['space_chats', 'tenant_chats'])
def cmd_tenant_chats(msg):
    schedule_command_delete(msg)
    uid = int(getattr(getattr(msg, 'from_user', None), 'id', 0) or 0)
    cid = int(msg.chat.id)
    tid = tenant_id_for_chat(cid, create=True, actor_user_id=uid)
    if not tenant_can_manage(uid, tid):
        send_and_auto_delete(cid, '❌ Недостаточно прав.', 12)
        return
    bot.send_message(cid, tenant_chats_text(tid))

@bot.message_handler(commands=['space_role', 'tenant_role'])
def cmd_tenant_role(msg):
    schedule_command_delete(msg)
    actor = int(getattr(getattr(msg, 'from_user', None), 'id', 0) or 0)
    cid = int(msg.chat.id)
    tid = tenant_id_for_chat(cid, create=True, actor_user_id=actor)
    if not tenant_can_manage(actor, tid):
        send_and_auto_delete(cid, '❌ Недостаточно прав.', 12)
        return
    parts = _tenant_command_parts(msg)
    if len(parts) < 3:
        send_and_auto_delete(cid, 'Использование: /space_role USER_ID tenant_admin|operator|viewer', 15)
        return
    try:
        uid = int(parts[1])
        role = parts[2].lower()
    except Exception:
        send_and_auto_delete(cid, '❌ Неверный USER_ID.', 12)
        return
    if role not in {'tenant_admin', 'operator', 'viewer'}:
        send_and_auto_delete(cid, '❌ Допустимые роли: tenant_admin, operator, viewer.', 12)
        return
    tenant_set_user_role(tid, uid, role, changed_by=actor)
    bot.send_message(cid, f'✅ Пользователь {uid}: {TENANT_ROLE_LABELS.get(role)}.')

@bot.message_handler(commands=['space_transfer', 'tenant_transfer'])
def cmd_tenant_transfer(msg):
    schedule_command_delete(msg)
    actor = int(getattr(getattr(msg, 'from_user', None), 'id', 0) or 0)
    cid = int(msg.chat.id)
    tid = tenant_id_for_chat(cid, create=True, actor_user_id=actor)
    if not tenant_can_manage(actor, tid, owner_only=True):
        send_and_auto_delete(cid, '❌ Передать владение может только владелец пространства.', 12)
        return
    if tid == TENANT_PLATFORM_ID:
        send_and_auto_delete(cid, '❌ Владение всей платформой закреплено за основным владельцем и не передаётся этой командой.', 15)
        return
    parts = _tenant_command_parts(msg)
    if len(parts) < 2:
        send_and_auto_delete(cid, 'Использование: /space_transfer USER_ID', 12)
        return
    uid = int(parts[1])
    tenant_set_user_role(tid, uid, 'tenant_owner', changed_by=actor)
    bot.send_message(cid, f'✅ Владение пространством передано пользователю {uid}.')

@bot.message_handler(commands=['space_rename', 'tenant_rename'])
def cmd_tenant_rename(msg):
    schedule_command_delete(msg)
    actor = int(getattr(getattr(msg, 'from_user', None), 'id', 0) or 0)
    cid = int(msg.chat.id)
    tid = tenant_id_for_chat(cid, create=True, actor_user_id=actor)
    if not tenant_can_manage(actor, tid):
        send_and_auto_delete(cid, '❌ Недостаточно прав.', 12)
        return
    parts = _tenant_command_parts(msg)
    name = ' '.join(parts[1:]).strip()
    if not name:
        send_and_auto_delete(cid, 'Использование: /space_rename Новое название', 12)
        return
    tenant_get(tid)['name'] = name[:80]
    tenant_get(tid)['updated_at'] = _tenant_now()
    save_data(data, root_only=True)
    bot.send_message(cid, f'✅ Пространство переименовано: {name[:80]}')

@bot.message_handler(commands=['space_unlink', 'tenant_unlink'])
def cmd_tenant_unlink(msg):
    schedule_command_delete(msg)
    actor = int(getattr(getattr(msg, 'from_user', None), 'id', 0) or 0)
    cid = int(msg.chat.id)
    tid = tenant_id_for_chat(cid, create=True, actor_user_id=actor)
    if not tenant_can_manage(actor, tid):
        send_and_auto_delete(cid, '❌ Недостаточно прав.', 12)
        return
    row = tenant_get(tid)
    if int(row.get('root_chat_id') or 0) == cid:
        send_and_auto_delete(cid, '❌ Корневой чат нельзя отсоединить. Можно передать владение или подключить другие чаты.', 15)
        return
    tenant_unbind_chat(cid, changed_by=actor)
    save_data(data, full=True)
    bot.send_message(cid, '✅ Чат отсоединён и получил собственное изолированное пространство.')

def tenant_require_platform_owner(msg, notify: bool=True) -> bool:
    uid = int(getattr(getattr(msg, 'from_user', None), 'id', 0) or 0)
    ok = tenant_is_platform_owner_user(uid)
    if not ok and notify:
        try:
            send_and_auto_delete(int(msg.chat.id), 'Эта команда доступна только владельцу всей платформы.', 10)
        except Exception:
            pass
    return ok

def _canon_build_fin_windows_chat_menu__001(day_key: str):
    kb = types.InlineKeyboardMarkup(row_width=2)
    buttons = []
    for cid in tenant_chat_ids(tenant_current_id()):
        if not is_finance_mode(int(cid)):
            continue
        if is_chat_bot_removed(int(cid)) and (not (OWNER_ID and str(int(cid)) == str(OWNER_ID))):
            continue
        buttons.append(IB(chat_button_title(int(cid), get_chat_display_name(int(cid))), callback_data=f'd:{day_key}:finwin_open_{int(cid)}'))
    if buttons:
        add_buttons_in_rows(kb, sorted(buttons, key=lambda b: str(getattr(b, 'text', '')).casefold()), 2)
    else:
        kb.row(IB('Нет чатов с финрежимом', callback_data='none'))
    kb.row(IB('🔙 Назад', callback_data=f'd:{day_key}:back_main'))
    return kb

def _v177_legacy_0061_build_forward_status_lines() -> list[str]:
    lines = []
    fr = data.get('forward_rules', {}) or {}
    ff = data.get('forward_finance', {}) or {}
    allowed = set(tenant_chat_ids(tenant_current_id()))
    pairs = set()
    for src, dsts in fr.items():
        try:
            a = int(src)
        except Exception:
            continue
        if a not in allowed:
            continue
        for dst in (dsts or {}).keys():
            try:
                b = int(dst)
            except Exception:
                continue
            if b not in allowed:
                continue
            pairs.add(tuple(sorted((a, b))))
    for a, b in sorted(pairs, key=lambda p: (get_chat_display_name(p[0]).casefold(), get_chat_display_name(p[1]).casefold())):
        ab = str(b) in (fr.get(str(a), {}) or {})
        ba = str(a) in (fr.get(str(b), {}) or {})
        if not (ab or ba):
            continue
        ab_fin = bool((ff.get(str(a), {}) or {}).get(str(b), False))
        ba_fin = bool((ff.get(str(b), {}) or {}).get(str(a), False))
        lines.append(f'• {chat_button_title(a)} -({_forward_arrow_icon(ab, ba)})-({_forward_fin_icon(ab_fin, ba_fin)})-{chat_button_title(b)}')
    return lines or ['• Связи пересылки не настроены']
try:
    _v177_legacy_0061_build_forward_status_lines.__name__ = 'build_forward_status_lines'
except Exception:
    pass
_V148_ORIG_BUILD_INFO_KEYBOARD = _v177_legacy_0216_build_info_keyboard

def _v177_legacy_0217_build_info_keyboard(chat_id: int):
    kb = _V148_ORIG_BUILD_INFO_KEYBOARD(int(chat_id))
    platform = tenant_is_platform_owner_context(int(chat_id))
    if not platform:
        blocked_prefixes = ('journal_', 'restore_guard', 'mega_manual_restore', 'mega_priority', 'keepalive_', 'process_center', 'safety_profile', 'problem_tasks', 'integrity_status', 'info_queues', 'runtime_watcher', 'info_delta_status', 'additional_owners', 'addown:', 'expense_')
        clean_rows = []
        for row in list(getattr(kb, 'keyboard', []) or []):
            kept = []
            for button in row:
                cb = str(getattr(button, 'callback_data', '') or '')
                if cb.startswith(blocked_prefixes):
                    continue
                kept.append(button)
            if kept:
                clean_rows.append(kept)
        kb.keyboard = clean_rows
    actor = tenant_current_actor_user_id()
    role = tenant_role_for_user(actor, chat_id=int(chat_id)) if actor else 'tenant_owner' if is_owner_chat(int(chat_id)) else 'standard'
    if role in {'platform_owner', 'tenant_owner', 'tenant_admin', 'operator', 'viewer'}:
        if not any((str(getattr(button, 'callback_data', '') or '') == 'sp:dashboard' for row in getattr(kb, 'keyboard', []) for button in row)):
            kb.row(IB('🏢 Пространство', callback_data='sp:dashboard'))
    return kb
try:
    _v177_legacy_0217_build_info_keyboard.__name__ = 'build_info_keyboard'
except Exception:
    pass
_V148_ORIG_BUILD_INFO_TEXT = _v177_legacy_0054_build_info_text

def _v177_legacy_0055_build_info_text(chat_id: int) -> str:
    text = _V148_ORIG_BUILD_INFO_TEXT(int(chat_id))
    if not tenant_is_platform_owner_context(int(chat_id)):
        forbidden = ('/errors', '/runtime_export', '/mega_', '/queues', '/journal', '/sqlite', '/db', '/restore_guard', 'MEGA:')
        text = '\n'.join((line for line in str(text).splitlines() if not any((token in line for token in forbidden))))
    tid = tenant_id_for_chat(int(chat_id), create=False)
    row = tenant_get(tid) or {}
    suffix = f"\n\n🏢 Пространство: {row.get('name') or tid}\n/space — чаты, пользователи и ссылки подключения"
    return (str(text).rstrip() + suffix)[:3900]
try:
    _v177_legacy_0055_build_info_text.__name__ = 'build_info_text'
except Exception:
    pass
_V148_ORIG_BUILD_HELP_TEXT = _v177_legacy_0053_build_help_text

def _canon_build_help_text__001(chat_id: int) -> str:
    text = _V148_ORIG_BUILD_HELP_TEXT(int(chat_id))
    actor = tenant_current_actor_user_id()
    tid = tenant_id_for_chat(int(chat_id), create=False)
    role = tenant_role_for_user(actor, tid) if actor else 'standard'
    lines = [str(text).rstrip(), '', '🏢 Изолированное пространство:', '/space — открыть пространство']
    if role in {'platform_owner', 'tenant_owner', 'tenant_admin'}:
        lines.extend(['/space_chat_link — подключить свой дополнительный чат', '/space_user_link operator — пригласить пользователя', '/space_users — пользователи и роли', '/space_chats — чаты пространства'])
    return '\n'.join(lines)[:3900]

def tenant_v148_enforce_forward_isolation() -> int:
    removed = 0
    fr = data.setdefault('forward_rules', {})
    ff = data.setdefault('forward_finance', {})
    for src, dsts in list(fr.items()):
        try:
            src_id = int(src)
        except Exception:
            fr.pop(src, None)
            ff.pop(str(src), None)
            continue
        if not isinstance(dsts, dict):
            fr.pop(src, None)
            ff.pop(str(src_id), None)
            continue
        for dst in list(dsts.keys()):
            try:
                dst_id = int(dst)
            except Exception:
                dsts.pop(dst, None)
                (ff.get(str(src_id)) or {}).pop(str(dst), None)
                removed += 1
                continue
            if not tenant_same_space(src_id, dst_id):
                dsts.pop(dst, None)
                (ff.get(str(src_id)) or {}).pop(str(dst_id), None)
                removed += 1
        if not dsts:
            fr.pop(str(src), None)
            ff.pop(str(src_id), None)
    if removed:
        persist_forward_rules_to_owner()
        try:
            bot_journal('tenant_cross_links_removed', OWNER_ID, f'count={removed}', 'WARN')
        except Exception:
            pass
    return removed

def tenant_v148_bootstrap() -> dict:
    root = _tenants_root()
    report = {'created': 0, 'bound': 0, 'legacy_owners': 0, 'reminders_tagged': 0, 'cross_links_removed': 0}
    with _TENANT_LOCK:
        if TENANT_PLATFORM_ID not in root['tenants']:
            root['tenants'][TENANT_PLATFORM_ID] = _tenant_normalize(TENANT_PLATFORM_ID, {'name': 'Основное пространство владельца', 'owner_user_id': _tenant_platform_owner_user_id(), 'root_chat_id': _tenant_platform_owner_user_id(), 'chat_ids': [], 'users': {}, 'settings': {}, 'created_by': _tenant_platform_owner_user_id()})
            report['created'] += 1
        platform_row = tenant_get(TENANT_PLATFORM_ID)
        legacy_ids = []
        try:
            legacy_ids = [int(x) for x in data.setdefault('_global_settings', {}).get('additional_owner_ids', [])]
        except Exception:
            legacy_ids = []
        owner_tenants = {}
        for uid in legacy_ids:
            tid = f'owner_{uid}'
            if tid not in root['tenants']:
                root['tenants'][tid] = _tenant_normalize(tid, {'name': f'Пространство {get_chat_display_name(uid)}', 'owner_user_id': uid, 'root_chat_id': uid, 'chat_ids': [uid], 'users': {}, 'settings': {}, 'created_by': _tenant_platform_owner_user_id()})
                report['created'] += 1
            owner_tenants[uid] = tid
            report['legacy_owners'] += 1
        if legacy_ids:
            data['_global_settings']['legacy_additional_owner_ids_v148'] = legacy_ids
            data['_global_settings']['additional_owner_ids'] = []
        for cid_raw, store in list((data.get('chats') or {}).items()):
            try:
                cid = int(cid_raw)
            except Exception:
                continue
            target_tid = TENANT_PLATFORM_ID
            try:
                old_scope = int(((store or {}).get('settings') or {}).get('owner_scope_id') or 0)
                if old_scope in owner_tenants:
                    target_tid = owner_tenants[old_scope]
            except Exception:
                pass
            if not (root.get('chat_to_tenant') or {}).get(str(cid)):
                tenant_bind_chat(cid, target_tid, changed_by=_tenant_platform_owner_user_id(), force=True)
                report['bound'] += 1
        for row in tenant_all():
            rid = int(row.get('root_chat_id') or 0)
            if rid and rid not in row['chat_ids']:
                row['chat_ids'].append(rid)
            if rid:
                root['chat_to_tenant'][str(rid)] = str(row.get('id'))
        try:
            rem_root = data.setdefault('_global_settings', {}).get('reminders_v2') or {}
            for cfg in (rem_root.get('items') or {}).values():
                if isinstance(cfg, dict) and (not cfg.get('tenant_id')):
                    cfg['tenant_id'] = TENANT_PLATFORM_ID
                    report['reminders_tagged'] += 1
        except Exception:
            pass
        if not platform_row.get('settings_migrated_v148'):
            gs = data.setdefault('_global_settings', {})
            for key in ('buttons_current_window', 'forward_menu_new_style', 'icon_button_mode', 'total_secret_mask_enabled', 'finance_day_start_5am', 'finance_day_start_minute', 'mega_backup_priority', 'internal_timers', 'backup_excel_all_enabled', 'excel_interface_mode', 'excel_new_export_options', 'excel_table_style_global', 'forward_copy_edit_mode_global', 'reminder_ui_mode_v142', 'expense_shortcut'):
                if key in gs:
                    mapped = key.replace('_global', '') if key in {'excel_table_style_global', 'forward_copy_edit_mode_global'} else key
                    platform_row.setdefault('settings', {})[mapped] = copy.deepcopy(gs.get(key))
            platform_row['settings_migrated_v148'] = True
        root['legacy_migrated'] = True
        root['schema_version'] = TENANT_SCHEMA_VERSION
    report['cross_links_removed'] += tenant_v148_enforce_forward_isolation()
    save_data(data, full=True)
    try:
        bot_journal('tenant_v148_bootstrap', OWNER_ID, json.dumps(report, ensure_ascii=False))
    except Exception:
        pass
    return report

def tenant_v148_snapshot() -> dict:
    root = _tenants_root()
    return {'schema_version': root.get('schema_version'), 'tenants': len(root.get('tenants') or {}), 'bound_chats': len(root.get('chat_to_tenant') or {}), 'active_invites': sum((1 for row in (root.get('invite_tokens') or {}).values() if isinstance(row, dict) and (not row.get('revoked')) and (float(row.get('expires_ts') or 0) >= time.time()) and (int(row.get('uses') or 0) < int(row.get('max_uses') or 1))))}
import base64 as _v149_base64
import hashlib as _v149_hashlib
import hmac as _v149_hmac
import json as _v149_json
import mimetypes as _v149_mimetypes
import os as _v149_os
import re as _v149_re
import secrets as _v149_secrets
import threading as _v149_threading
import time as _v149_time
from collections import defaultdict as _v149_defaultdict
from contextlib import contextmanager as _v149_contextmanager
from copy import deepcopy as _v149_deepcopy
from pathlib import Path as _v149_Path
V149_GOOGLE_SCHEMA_VERSION = 1
V149_REMINDER_SCHEMA_VERSION = 1
_V149_GOOGLE_CONTEXT = _v149_threading.local()
_V149_GOOGLE_TOKEN_LOCK = _v149_threading.RLock()
_V149_GOOGLE_TOKEN_CACHE = {}
_V149_REMINDER_BATCH_LOCK = _v149_threading.RLock()
_V149_COMPLETION_LOCK = _v149_threading.RLock()
_V149_PLATFORM_GOOGLE_JSON = str(globals().get('GOOGLE_SERVICE_ACCOUNT_JSON') or '')
_V149_PLATFORM_GOOGLE_SHEET = str(globals().get('GOOGLE_SHEETS_SPREADSHEET_ID') or '')
_V149_PLATFORM_GOOGLE_SHARE = str(globals().get('GOOGLE_SHEETS_SHARE_EMAIL') or '')
_V149_BASE_GOOGLE_SHEETS_CREATE = _v177_legacy_0208_google_sheets_create_category_report
_V149_BASE_REMINDER_LIST_TEXT = _v177_legacy_0124_build_reminder_list_text
_V149_BASE_REMINDER_MENU_TEXT = _v177_legacy_0128_build_reminder_menu_text

def _v149_now_iso() -> str:
    return now_local().isoformat(timespec='seconds')

def _v149_actor_id(obj) -> int:
    try:
        return int(getattr(getattr(obj, 'from_user', None), 'id', 0) or 0)
    except Exception:
        return 0

def _v149_actor_label(obj) -> str:
    user = getattr(obj, 'from_user', None)
    if user is None:
        return ''
    full = ' '.join((x for x in [str(getattr(user, 'first_name', '') or '').strip(), str(getattr(user, 'last_name', '') or '').strip()] if x)).strip()
    username = str(getattr(user, 'username', '') or '').strip()
    if username:
        return f'{full or username} (@{username})'[:120]
    return (full or str(getattr(user, 'id', '') or ''))[:120]

def _v149_tenant_id(tenant_id: str | None=None, target_chat_id: int | None=None) -> str:
    if tenant_id:
        return str(tenant_id)
    ctx = str(getattr(_V149_GOOGLE_CONTEXT, 'tenant_id', '') or '')
    if ctx:
        return ctx
    if target_chat_id is not None:
        try:
            resolved = tenant_id_for_chat(int(target_chat_id), create=False)
            if resolved:
                return str(resolved)
        except Exception:
            pass
    try:
        return str(tenant_current_id(target_chat_id) or TENANT_PLATFORM_ID)
    except Exception:
        return str(TENANT_PLATFORM_ID)

def _v149_chat_belongs_to_tenant(chat_id: int, tenant_id: str) -> bool:
    """Require an explicit v148 binding; fallback-to-platform is not enough for isolation."""
    try:
        return int(chat_id) in {int(x) for x in tenant_chat_ids(str(tenant_id))}
    except Exception:
        return False

@_v149_contextmanager
def tenant_google_context(tenant_id: str | None=None, target_chat_id: int | None=None):
    previous = getattr(_V149_GOOGLE_CONTEXT, 'tenant_id', None)
    _V149_GOOGLE_CONTEXT.tenant_id = _v149_tenant_id(tenant_id, target_chat_id)
    try:
        yield _V149_GOOGLE_CONTEXT.tenant_id
    finally:
        _V149_GOOGLE_CONTEXT.tenant_id = previous

def tenant_google_config(tenant_id: str | None=None, create: bool=True) -> dict:
    tid = _v149_tenant_id(tenant_id)
    row = tenant_get(tid)
    if not isinstance(row, dict):
        if not create:
            return {}
        raise RuntimeError('Пространство Google не найдено')
    cfg = row.get('google_v149')
    if not isinstance(cfg, dict):
        if not create:
            return {}
        cfg = {}
        row['google_v149'] = cfg
    cfg.setdefault('schema_version', V149_GOOGLE_SCHEMA_VERSION)
    cfg.setdefault('credentials_sealed', '')
    cfg.setdefault('credential_fingerprint', '')
    cfg.setdefault('service_account_email', '')
    cfg.setdefault('owner_google_email', '')
    cfg.setdefault('spreadsheet_id', '')
    cfg.setdefault('spreadsheet_title', '')
    cfg.setdefault('drive_folder_id', '')
    cfg.setdefault('drive_folder_name', '')
    cfg.setdefault('export_settings', {'sheet_enabled': True, 'drive_enabled': True, 'sheet_mode': 'new_tab', 'history_limit': 100, 'error_limit': 50})
    cfg.setdefault('history', [])
    cfg.setdefault('errors', [])
    cfg.setdefault('input_wait', {})
    cfg.setdefault('connected_at', '')
    cfg.setdefault('connected_by', 0)
    cfg.setdefault('updated_at', _v149_now_iso())
    return cfg

def _v149_google_master_key() -> bytes:
    raw = str(_v149_os.getenv('TENANT_GOOGLE_MASTER_KEY') or _v149_os.getenv('GOOGLE_TENANT_MASTER_KEY') or '').strip()
    if len(raw) < 24:
        raise RuntimeError('Для подключения Google пространств задайте в Render секрет TENANT_GOOGLE_MASTER_KEY длиной не менее 24 символов')
    return _v149_hashlib.sha256(raw.encode('utf-8')).digest()

def _v149_stream_xor(payload: bytes, key: bytes, nonce: bytes) -> bytes:
    out = bytearray(len(payload))
    offset = 0
    counter = 0
    while offset < len(payload):
        block = _v149_hmac.new(key, nonce + counter.to_bytes(8, 'big'), _v149_hashlib.sha256).digest()
        take = min(len(block), len(payload) - offset)
        for idx in range(take):
            out[offset + idx] = payload[offset + idx] ^ block[idx]
        offset += take
        counter += 1
    return bytes(out)

def _v149_seal_secret(raw: str) -> str:
    master = _v149_google_master_key()
    nonce = _v149_secrets.token_bytes(16)
    enc_key = _v149_hmac.new(master, b'enc:' + nonce, _v149_hashlib.sha256).digest()
    mac_key = _v149_hmac.new(master, b'mac:' + nonce, _v149_hashlib.sha256).digest()
    cipher = _v149_stream_xor(str(raw).encode('utf-8'), enc_key, nonce)
    tag = _v149_hmac.new(mac_key, b'v1:' + nonce + cipher, _v149_hashlib.sha256).digest()
    return 'v1.' + _v149_base64.urlsafe_b64encode(nonce + tag + cipher).decode('ascii')

def _v149_open_secret(sealed: str) -> str:
    if not str(sealed or '').startswith('v1.'):
        raise RuntimeError('Формат зашифрованного Google-ключа не поддерживается')
    try:
        blob = _v149_base64.urlsafe_b64decode(str(sealed).split('.', 1)[1].encode('ascii'))
        nonce, tag, cipher = (blob[:16], blob[16:48], blob[48:])
    except Exception as exc:
        raise RuntimeError(f'Google-ключ повреждён: {exc}')
    master = _v149_google_master_key()
    enc_key = _v149_hmac.new(master, b'enc:' + nonce, _v149_hashlib.sha256).digest()
    mac_key = _v149_hmac.new(master, b'mac:' + nonce, _v149_hashlib.sha256).digest()
    expected = _v149_hmac.new(mac_key, b'v1:' + nonce + cipher, _v149_hashlib.sha256).digest()
    if not _v149_hmac.compare_digest(tag, expected):
        raise RuntimeError('Google-ключ не прошёл проверку целостности')
    try:
        return _v149_stream_xor(cipher, enc_key, nonce).decode('utf-8')
    except Exception as exc:
        raise RuntimeError(f'Google-ключ не расшифрован: {exc}')

def _v149_parse_google_service_json(raw: str) -> dict:
    try:
        info = _v149_json.loads(str(raw))
    except Exception as exc:
        raise RuntimeError(f'JSON Google повреждён: {exc}')
    if not isinstance(info, dict):
        raise RuntimeError('JSON Google должен быть объектом')
    if str(info.get('type') or '') != 'service_account':
        raise RuntimeError('Нужен JSON ключ типа service_account')
    for key in ('client_email', 'private_key', 'token_uri'):
        if not str(info.get(key) or '').strip():
            raise RuntimeError(f'В Google JSON отсутствует {key}')
    return info

def tenant_google_set_credentials(tenant_id: str, raw: str, actor_user_id: int) -> dict:
    tid = _v149_tenant_id(tenant_id)
    info = _v149_parse_google_service_json(raw)
    cfg = tenant_google_config(tenant_id)
    cfg['credentials_sealed'] = _v149_seal_secret(_v149_json.dumps(info, ensure_ascii=False, separators=(',', ':')))
    cfg['credential_fingerprint'] = _v149_hashlib.sha256(str(info.get('client_email') or '').encode('utf-8') + str(info.get('private_key_id') or '').encode('utf-8')).hexdigest()[:20]
    cfg['service_account_email'] = str(info.get('client_email') or '')[:250]
    cfg['connected_at'] = _v149_now_iso()
    cfg['connected_by'] = int(actor_user_id or 0)
    cfg['updated_at'] = _v149_now_iso()
    cfg['input_wait'] = {}
    with _V149_GOOGLE_TOKEN_LOCK:
        for key in list(_V149_GOOGLE_TOKEN_CACHE):
            if str(key).startswith(str(tenant_id) + ':'):
                _V149_GOOGLE_TOKEN_CACHE.pop(key, None)
    tenant_google_history(tenant_id, 'account_connected', 'Google service account подключён', ok=True)
    tenant_google_persist(tid, 'tenant_google_update')
    return info

def tenant_google_persist(tenant_id: str, reason: str='tenant_google') -> None:
    tid = _v149_tenant_id(tenant_id)
    save_data(data, root_only=True)
    try:
        row = tenant_get(tid) or {}
        scope_chat = int(row.get('root_chat_id') or OWNER_ID or 0)
        if scope_chat:
            schedule_delta_backup(scope_chat, delay=0.35, reason=str(reason or 'tenant_google'))
    except Exception as exc:
        try:
            log_error(f'tenant google delta schedule: {exc}')
        except Exception:
            pass

def tenant_google_history(tenant_id: str, action: str, detail: str='', ok: bool=True, **meta) -> None:
    cfg = tenant_google_config(tenant_id)
    row = {'at': _v149_now_iso(), 'action': str(action)[:80], 'ok': bool(ok), 'detail': str(detail or '')[:500]}
    if meta:
        row['meta'] = {str(k)[:50]: str(v)[:250] for k, v in meta.items() if k not in {'credentials', 'private_key', 'token'}}
    rows = cfg.setdefault('history', [])
    rows.append(row)
    limit = max(10, min(500, int((cfg.get('export_settings') or {}).get('history_limit', 100) or 100)))
    del rows[:-limit]
    cfg['updated_at'] = _v149_now_iso()

def tenant_google_error(tenant_id: str, action: str, exc) -> None:
    tid = _v149_tenant_id(tenant_id)
    cfg = tenant_google_config(tenant_id)
    message = str(exc or 'Ошибка')
    message = _v149_re.sub('-----BEGIN [^-]+-----.*?-----END [^-]+-----', '[REDACTED KEY]', message, flags=_v149_re.S)
    message = _v149_re.sub('(?i)(access_token|refresh_token|private_key|client_secret)\\s*[:=]\\s*[^,\\s]+', '\\1=[REDACTED]', message)
    rows = cfg.setdefault('errors', [])
    rows.append({'at': _v149_now_iso(), 'action': str(action)[:80], 'error': message[:1000]})
    limit = max(10, min(200, int((cfg.get('export_settings') or {}).get('error_limit', 50) or 50)))
    del rows[:-limit]
    cfg['updated_at'] = _v149_now_iso()
    try:
        tenant_google_persist(tid, 'tenant_google_update')
    except Exception:
        pass

def _canon_google_service_account_info__001(tenant_id: str | None=None) -> dict:
    tid = _v149_tenant_id(tenant_id)
    cfg = tenant_google_config(tid, create=False)
    sealed = str(cfg.get('credentials_sealed') or '') if cfg else ''
    if sealed:
        return _v149_parse_google_service_json(_v149_open_secret(sealed))
    if tid == str(TENANT_PLATFORM_ID) and _V149_PLATFORM_GOOGLE_JSON:
        raw = _V149_PLATFORM_GOOGLE_JSON
        try:
            if raw.lstrip().startswith('{'):
                return _v149_parse_google_service_json(raw)
            return _v149_parse_google_service_json(_v149_base64.b64decode(raw).decode('utf-8'))
        except Exception as exc:
            raise RuntimeError(f'GOOGLE_SERVICE_ACCOUNT_JSON владельца платформы повреждён: {exc}')
    raise RuntimeError('Google-аккаунт этого пространства не подключён. Откройте /google')

def _v149_google_id(value: str, kind: str) -> str:
    raw = str(value or '').strip()
    if kind == 'sheet':
        match = _v149_re.search('/spreadsheets/d/([A-Za-z0-9_-]+)', raw)
    else:
        match = _v149_re.search('/folders/([A-Za-z0-9_-]+)', raw)
    if match:
        raw = match.group(1)
    raw = raw.split('?')[0].split('#')[0].strip().strip('/')
    if not _v149_re.fullmatch('[A-Za-z0-9_-]{10,}', raw):
        raise RuntimeError('Неверная ссылка или ID Google ' + ('таблицы' if kind == 'sheet' else 'папки'))
    return raw

def _canon_google_spreadsheet_id__001(value: str | None=None, tenant_id: str | None=None) -> str:
    if value is not None and str(value).strip():
        return _v149_google_id(str(value), 'sheet')
    tid = _v149_tenant_id(tenant_id)
    cfg = tenant_google_config(tid, create=False)
    raw = str((cfg or {}).get('spreadsheet_id') or '')
    if not raw and tid == str(TENANT_PLATFORM_ID):
        raw = _V149_PLATFORM_GOOGLE_SHEET
    if not raw:
        raise RuntimeError('Для этого пространства не выбрана Google Таблица. Откройте /google')
    return _v149_google_id(raw, 'sheet')

def tenant_google_drive_folder_id(tenant_id: str | None=None) -> str:
    tid = _v149_tenant_id(tenant_id)
    raw = str(tenant_google_config(tid, create=False).get('drive_folder_id') or '')
    if not raw:
        raise RuntimeError('Для этого пространства не выбрана папка Google Drive. Откройте /google')
    return _v149_google_id(raw, 'folder')

def _canon_google_access_token__001(tenant_id: str | None=None) -> str:
    tid = _v149_tenant_id(tenant_id)
    info = _google_service_account_info(tid)
    fingerprint = _v149_hashlib.sha256((str(info.get('client_email')) + str(info.get('private_key_id'))).encode('utf-8')).hexdigest()[:20]
    cache_key = f'{tid}:{fingerprint}'
    with _V149_GOOGLE_TOKEN_LOCK:
        now = _v149_time.time()
        cached = _V149_GOOGLE_TOKEN_CACHE.get(cache_key) or {}
        if cached.get('token') and now < float(cached.get('expires_at', 0)) - 120:
            return str(cached['token'])
        header = {'alg': 'RS256', 'typ': 'JWT'}
        claims = {'iss': info['client_email'], 'scope': 'https://www.googleapis.com/auth/spreadsheets https://www.googleapis.com/auth/drive', 'aud': info.get('token_uri') or 'https://oauth2.googleapis.com/token', 'iat': int(now), 'exp': int(now) + 3600}
        signing_input = (_b64url(_v149_json.dumps(header, separators=(',', ':')).encode('utf-8')) + '.' + _b64url(_v149_json.dumps(claims, separators=(',', ':')).encode('utf-8'))).encode('ascii')
        signature = _google_sign_rs256(signing_input, info['private_key'])
        assertion = signing_input.decode('ascii') + '.' + _b64url(signature)
        response = _google_request_guarded('oauth', requests.post, info.get('token_uri') or 'https://oauth2.googleapis.com/token', data={'grant_type': 'urn:ietf:params:oauth:grant-type:jwt-bearer', 'assertion': assertion}, timeout=30, attempts=2)
        if response.status_code >= 300:
            raise RuntimeError(f'Google OAuth {response.status_code}: {response.text[:500]}')
        payload = response.json()
        token = str(payload.get('access_token') or '')
        if not token:
            raise RuntimeError('Google OAuth не вернул access_token')
        _V149_GOOGLE_TOKEN_CACHE[cache_key] = {'token': token, 'expires_at': now + int(payload.get('expires_in', 3600) or 3600)}
        return token

def _canon_google_sheets_create_category_report__001(title: str, rows: list[list], layout: str='category', annotations_override: dict | None=None, include_annotations: bool=True, tenant_id: str | None=None, target_chat_id: int | None=None) -> str:
    if not callable(_V149_BASE_GOOGLE_SHEETS_CREATE):
        raise RuntimeError('Модуль Google Sheets не загружен')
    tid = _v149_tenant_id(tenant_id, target_chat_id)
    if target_chat_id is not None and (not _v149_chat_belongs_to_tenant(int(target_chat_id), tid)):
        raise RuntimeError('Google export blocked: target chat is not connected to this space')
    cfg = tenant_google_config(tid)
    if not bool((cfg.get('export_settings') or {}).get('sheet_enabled', True)):
        raise RuntimeError('Выгрузка в Google Sheets выключена для этого пространства')
    try:
        with tenant_google_context(tid):
            url = _V149_BASE_GOOGLE_SHEETS_CREATE(title, rows, layout=layout, annotations_override=annotations_override, include_annotations=include_annotations)
        tenant_google_history(tid, 'sheets_export', title, ok=True, chat_id=target_chat_id or 0, url=url)
        tenant_google_persist(tid, 'tenant_google_update')
        return url
    except Exception as exc:
        tenant_google_error(tid, 'sheets_export', exc)
        raise

def tenant_google_upload_export(local_path: str, display_name: str, target_chat_id: int, mime_type: str | None=None) -> str:
    tid = _v149_tenant_id(target_chat_id=target_chat_id)
    if not _v149_chat_belongs_to_tenant(int(target_chat_id), tid):
        raise RuntimeError('Google Drive export blocked: target chat is not connected to this space')
    cfg = tenant_google_config(tid)
    if not bool((cfg.get('export_settings') or {}).get('drive_enabled', True)):
        raise RuntimeError('Выгрузка в Google Drive выключена для этого пространства')
    folder_id = tenant_google_drive_folder_id(tid)
    token = _google_access_token(tid)
    mime_type = str(mime_type or _v149_mimetypes.guess_type(display_name)[0] or 'application/octet-stream')
    headers = {'Authorization': f'Bearer {token}'}
    metadata = {'name': str(display_name or _v149_Path(local_path).name)[:240], 'parents': [folder_id], 'appProperties': {'tenant_id': tid, 'source_chat_id': str(int(target_chat_id))}}
    try:
        with open(local_path, 'rb') as fh:
            response = _google_request_guarded('drive_upload', requests.post, 'https://www.googleapis.com/upload/drive/v3/files', headers=headers, params={'uploadType': 'multipart', 'fields': 'id,name,webViewLink,parents'}, files={'metadata': (None, _v149_json.dumps(metadata, ensure_ascii=False), 'application/json; charset=UTF-8'), 'file': (metadata['name'], fh, mime_type)}, timeout=120, attempts=1)
        if response.status_code >= 300:
            raise RuntimeError(f'Google Drive upload {response.status_code}: {response.text[:700]}')
        payload = response.json()
        file_id = str(payload.get('id') or '')
        url = str(payload.get('webViewLink') or (f'https://drive.google.com/file/d/{file_id}/view' if file_id else ''))
        tenant_google_history(tid, 'drive_export', metadata['name'], ok=True, chat_id=target_chat_id, file_id=file_id)
        tenant_google_persist(tid, 'tenant_google_update')
        return url
    except Exception as exc:
        tenant_google_error(tid, 'drive_export', exc)
        raise

def tenant_google_create_spreadsheet(tenant_id: str, title: str='Финансы бота') -> str:
    """v244: create a usable spreadsheet even when no Drive folder was configured.

    If a folder exists we place the file there. Otherwise Google creates it in the
    service account Drive root. When an owner/share email is known, grant writer
    access immediately so the owner can open the newly created file.
    """
    tid = _v149_tenant_id(tenant_id)
    token = _google_access_token(tid)
    cfg = tenant_google_config(tid)
    folder_raw = str(cfg.get('drive_folder_id') or '').strip()
    folder_id = _v149_google_id(folder_raw, 'folder') if folder_raw else ''
    headers = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}
    metadata = {'name': str(title or 'Финансы бота')[:200], 'mimeType': 'application/vnd.google-apps.spreadsheet', 'appProperties': {'tenant_id': tid, 'created_by_bot_version': VERSION}}
    if folder_id:
        metadata['parents'] = [folder_id]
    response = _google_request_guarded('drive_create_sheet_v244', requests.post, 'https://www.googleapis.com/drive/v3/files', headers=headers, params={'fields': 'id,name,webViewLink,parents'}, json=metadata, timeout=60, attempts=1)
    if response.status_code >= 300 and (not folder_id):
        sheet_create = _google_request_guarded('sheets_create_spreadsheet_v244', requests.post, 'https://sheets.googleapis.com/v4/spreadsheets', headers=headers, json={'properties': {'title': str(title or 'Финансы бота')[:200]}}, timeout=60, attempts=1)
        if sheet_create.status_code < 300:
            sp = sheet_create.json()
            sid = str(sp.get('spreadsheetId') or '')
            response = type('_V244GoogleCreateResponse', (), {'status_code': 200, 'json': lambda self, _sid=sid, _title=str((sp.get('properties') or {}).get('title') or title): {'id': _sid, 'name': _title, 'webViewLink': f'https://docs.google.com/spreadsheets/d/{_sid}/edit'}, 'text': ''})()
    if response.status_code >= 300:
        exc = RuntimeError(f'Google create spreadsheet {response.status_code}: {response.text[:700]}')
        tenant_google_error(tid, 'create_spreadsheet', exc)
        raise exc
    payload = response.json()
    spreadsheet_id = _v149_google_id(str(payload.get('id') or ''), 'sheet')
    cfg['spreadsheet_id'] = spreadsheet_id
    cfg['spreadsheet_title'] = str(payload.get('name') or title)[:200]
    cfg['updated_at'] = _v149_now_iso()
    share_email = str(cfg.get('owner_google_email') or '').strip()
    if not share_email and tid == str(TENANT_PLATFORM_ID):
        share_email = str(_V149_PLATFORM_GOOGLE_SHARE or '').strip()
    share_note = ''
    if share_email:
        try:
            perm = _google_request_guarded('drive_share_sheet_v244', requests.post, f'https://www.googleapis.com/drive/v3/files/{spreadsheet_id}/permissions', headers=headers, params={'sendNotificationEmail': 'false', 'fields': 'id'}, json={'type': 'user', 'role': 'writer', 'emailAddress': share_email}, timeout=45, attempts=1)
            if perm.status_code < 300:
                share_note = f'; shared={share_email}'
            else:
                share_note = f'; share_warning={perm.status_code}'
                tenant_google_error(tid, 'share_created_spreadsheet', RuntimeError(perm.text[:500]))
        except Exception as exc:
            share_note = '; share_warning=exception'
            try:
                tenant_google_error(tid, 'share_created_spreadsheet', exc)
            except Exception:
                pass
    tenant_google_history(tid, 'create_spreadsheet_v244', cfg['spreadsheet_title'] + share_note, ok=True, spreadsheet_id=spreadsheet_id, folder_id=folder_id or 'root')
    tenant_google_persist(tid, 'tenant_google_update')
    return str(payload.get('webViewLink') or f'https://docs.google.com/spreadsheets/d/{spreadsheet_id}/edit')

def tenant_google_test(tenant_id: str) -> tuple[bool, str]:
    tid = _v149_tenant_id(tenant_id)
    try:
        token = _google_access_token(tid)
        headers = {'Authorization': f'Bearer {token}'}
        parts = []
        folder_id = str(tenant_google_config(tid).get('drive_folder_id') or '')
        if folder_id:
            response = _google_request_guarded('drive_folder_test', requests.get, f"https://www.googleapis.com/drive/v3/files/{_v149_google_id(folder_id, 'folder')}", headers=headers, params={'fields': 'id,name,mimeType,trashed'}, timeout=30, attempts=2)
            if response.status_code >= 300:
                raise RuntimeError(f'Drive folder {response.status_code}: {response.text[:500]}')
            payload = response.json()
            tenant_google_config(tid)['drive_folder_name'] = str(payload.get('name') or '')[:200]
            parts.append('Drive: доступ есть')
        sheet_raw = str(tenant_google_config(tid).get('spreadsheet_id') or '')
        if not sheet_raw and tid == str(TENANT_PLATFORM_ID):
            sheet_raw = _V149_PLATFORM_GOOGLE_SHEET
        if sheet_raw:
            sid = _v149_google_id(sheet_raw, 'sheet')
            response = _google_request_guarded('sheet_test', requests.get, f'https://sheets.googleapis.com/v4/spreadsheets/{sid}', headers=headers, params={'fields': 'spreadsheetId,properties.title'}, timeout=30, attempts=2)
            if response.status_code >= 300:
                raise RuntimeError(f'Sheets {response.status_code}: {response.text[:500]}')
            payload = response.json()
            tenant_google_config(tid)['spreadsheet_title'] = str((payload.get('properties') or {}).get('title') or '')[:200]
            parts.append('Sheets: доступ есть')
        if not parts:
            parts.append('Аккаунт подключён; задайте таблицу и папку')
        tenant_google_history(tid, 'connection_test', '; '.join(parts), ok=True)
        tenant_google_persist(tid, 'tenant_google_update')
        return (True, '✅ ' + '; '.join(parts))
    except Exception as exc:
        tenant_google_error(tid, 'connection_test', exc)
        return (False, '❌ ' + str(exc)[:700])

def _v149_mask_id(value: str) -> str:
    raw = str(value or '')
    if len(raw) <= 10:
        return raw or 'не задан'
    return raw[:6] + '…' + raw[-4:]

def tenant_google_status_text(tenant_id: str) -> str:
    tid = _v149_tenant_id(tenant_id)
    row = tenant_get(tid) or {}
    cfg = tenant_google_config(tid)
    env_fallback = tid == str(TENANT_PLATFORM_ID) and (not cfg.get('credentials_sealed')) and bool(_V149_PLATFORM_GOOGLE_JSON)
    account = str(cfg.get('service_account_email') or ('Render Environment' if env_fallback else 'не подключён'))
    sheet = str(cfg.get('spreadsheet_title') or '')
    folder = str(cfg.get('drive_folder_name') or '')
    return f"☁️ GOOGLE · {row.get('name') or tid}\n\nАккаунт: {account}\nGoogle владельца: {cfg.get('owner_google_email') or 'не указан'}\nТаблица: {sheet or _v149_mask_id(cfg.get('spreadsheet_id') or (_V149_PLATFORM_GOOGLE_SHEET if env_fallback else ''))}\nПапка Drive: {folder or _v149_mask_id(cfg.get('drive_folder_id'))}\nВыгрузка Sheets: {('включена' if bool((cfg.get('export_settings') or {}).get('sheet_enabled', True)) else 'выключена')}\nВыгрузка Drive: {('включена' if bool((cfg.get('export_settings') or {}).get('drive_enabled', True)) else 'выключена')}\nИстория: {len(cfg.get('history') or [])}\nОшибки: {len(cfg.get('errors') or [])}\n\nДанные, токены, таблица, папка, история и ошибки принадлежат только этому пространству.\nДля подключения нужен JSON ключ service_account и общий мастер-ключ TENANT_GOOGLE_MASTER_KEY в Render."

def tenant_google_keyboard(tenant_id: str):
    tid = str(tenant_id)
    cfg = tenant_google_config(tid)
    kb = types.InlineKeyboardMarkup(row_width=1)
    kb.row(IB('🔑 Подключить / заменить аккаунт', callback_data='v149:google:connect'))
    kb.row(IB('📊 Указать Google Таблицу', callback_data='v149:google:sheet'))
    kb.row(IB('📁 Указать папку Google Drive', callback_data='v149:google:folder'))
    kb.row(IB('👤 Указать email Google владельца', callback_data='v149:google:owner_email'))
    settings = cfg.get('export_settings') or {}
    kb.row(IB(f"{('✅' if settings.get('sheet_enabled', True) else '⬜')} 📊 Выгрузка Sheets: {('ВКЛ' if settings.get('sheet_enabled', True) else 'ВЫКЛ')}", callback_data='v149:google:toggle_sheet'))
    kb.row(IB(f"{('✅' if settings.get('drive_enabled', True) else '⬜')} 📁 Выгрузка Drive: {('ВКЛ' if settings.get('drive_enabled', True) else 'ВЫКЛ')}", callback_data='v149:google:toggle_drive'))
    kb.row(IB('➕ Создать таблицу в папке', callback_data='v149:google:create_sheet'))
    kb.row(IB('🧪 Проверить подключение', callback_data='v149:google:test'))
    kb.row(IB(f"📜 История ({len(cfg.get('history') or [])})", callback_data='v149:google:history'), IB(f"⚠️ Ошибки ({len(cfg.get('errors') or [])})", callback_data='v149:google:errors'))
    kb.row(IB('🧹 Отключить Google', callback_data='v149:google:disconnect_confirm'))
    return kb

def _canon_v149_google_wait__001(tenant_id: str, kind: str, chat_id: int, user_id: int) -> None:
    tid = _v149_tenant_id(tenant_id)
    cfg = tenant_google_config(tid)
    cfg['input_wait'] = {'kind': str(kind), 'chat_id': int(chat_id), 'user_id': int(user_id), 'expires_at': _v149_time.time() + 900}
    cfg['updated_at'] = _v149_now_iso()
    tenant_google_persist(tid, 'tenant_google_update')

def _v149_google_can_manage(chat_id: int, user_id: int, owner_only: bool=True) -> tuple[bool, str]:
    tid = str(tenant_id_for_chat(int(chat_id), create=True, actor_user_id=int(user_id)) or TENANT_PLATFORM_ID)
    return (bool(tenant_can_manage(int(user_id), tid, owner_only=owner_only)), tid)

def _canon_tenant_google_handle_message__001(msg) -> bool:
    """Called near the top of the common non-command message router."""
    try:
        chat_id = int(msg.chat.id)
        user_id = _v149_actor_id(msg)
        tid = str(tenant_id_for_chat(chat_id, create=False) or '')
        if not tid:
            return False
        cfg = tenant_google_config(tid, create=False)
        wait = (cfg or {}).get('input_wait') or {}
        if not wait:
            return False
        if not tenant_can_manage(user_id, tid, owner_only=True):
            return False
        if not wait or int(wait.get('chat_id') or 0) != chat_id or int(wait.get('user_id') or 0) != user_id:
            return False
        if _v149_time.time() > float(wait.get('expires_at') or 0):
            cfg['input_wait'] = {}
            tenant_google_persist(tid, 'tenant_google_update')
            return False
        kind = str(wait.get('kind') or '')
        if kind == 'credentials':
            if str(getattr(msg, 'content_type', '')) != 'document':
                send_and_auto_delete(chat_id, 'Пришлите JSON-файл service_account как документ.', 12)
                return True
            document = getattr(msg, 'document', None)
            if not document or int(getattr(document, 'file_size', 0) or 0) > 250000:
                send_and_auto_delete(chat_id, 'JSON-файл отсутствует или слишком большой.', 12)
                return True
            filename = str(getattr(document, 'file_name', '') or '').lower()
            if filename and (not filename.endswith('.json')):
                send_and_auto_delete(chat_id, 'Нужен файл с расширением .json.', 12)
                return True
            file_info = bot.get_file(document.file_id)
            raw_bytes = bot.download_file(file_info.file_path)
            raw = bytes(raw_bytes).decode('utf-8')
            info = tenant_google_set_credentials(tid, raw, user_id)
            try:
                bot.delete_message(chat_id, msg.message_id)
            except Exception:
                pass
            bot.send_message(chat_id, f"✅ Google-аккаунт подключён: {info.get('client_email')}\n\nТеперь укажите свою таблицу и папку Drive через /google.")
            return True
        if str(getattr(msg, 'content_type', '')) != 'text':
            send_and_auto_delete(chat_id, 'Пришлите ссылку или ID текстом.', 10)
            return True
        value = str(getattr(msg, 'text', '') or '').strip()
        if kind == 'sheet':
            cfg['spreadsheet_id'] = _v149_google_id(value, 'sheet')
            cfg['spreadsheet_title'] = ''
            action = 'sheet_configured'
            text = '✅ Google Таблица сохранена.'
        elif kind == 'folder':
            cfg['drive_folder_id'] = _v149_google_id(value, 'folder')
            cfg['drive_folder_name'] = ''
            action = 'drive_folder_configured'
            text = '✅ Папка Google Drive сохранена.'
        elif kind == 'owner_email':
            if not _v149_re.fullmatch('[^@\\s]+@[^@\\s]+\\.[^@\\s]+', value):
                raise RuntimeError('Неверный email')
            cfg['owner_google_email'] = value[:250]
            action = 'owner_email_configured'
            text = '✅ Email владельца Google сохранён.'
        else:
            return False
        cfg['input_wait'] = {}
        cfg['updated_at'] = _v149_now_iso()
        tenant_google_history(tid, action, text, ok=True)
        tenant_google_persist(tid, 'tenant_google_update')
        try:
            bot.delete_message(chat_id, msg.message_id)
        except Exception:
            pass
        bot.send_message(chat_id, text, reply_markup=tenant_google_keyboard(tid))
        return True
    except Exception as exc:
        try:
            tid = str(tenant_id_for_chat(int(msg.chat.id), create=False) or TENANT_PLATFORM_ID)
            tenant_google_error(tid, 'input', exc)
            send_and_auto_delete(int(msg.chat.id), '❌ ' + str(exc)[:700], 20)
        except Exception:
            pass
        return True

def _v149_google_history_text(tenant_id: str, errors: bool=False) -> str:
    cfg = tenant_google_config(tenant_id)
    rows = list(cfg.get('errors' if errors else 'history') or [])[-20:]
    title = '⚠️ ОШИБКИ GOOGLE' if errors else '📜 ИСТОРИЯ GOOGLE'
    if not rows:
        return title + '\n\nПока пусто.'
    lines = [title, '']
    for row in reversed(rows):
        if errors:
            lines.append(f"{row.get('at')} · {row.get('action')}\n{row.get('error')}")
        else:
            mark = '✅' if row.get('ok') else '❌'
            lines.append(f"{mark} {row.get('at')} · {row.get('action')}\n{row.get('detail')}")
    return '\n\n'.join(lines)[:3900]

@bot.message_handler(commands=['google', 'google_space', 'google_tenant'])
def cmd_v149_google(msg):
    try:
        schedule_command_delete(msg)
    except Exception:
        pass
    chat_id = int(msg.chat.id)
    user_id = _v149_actor_id(msg)
    ok, tid = _v149_google_can_manage(chat_id, user_id, owner_only=True)
    if not ok:
        send_and_auto_delete(chat_id, '❌ Google пространства может настраивать только его владелец.', 12)
        return
    bot.send_message(chat_id, tenant_google_status_text(tid), reply_markup=tenant_google_keyboard(tid), disable_web_page_preview=True)

@bot.message_handler(commands=['google_connect'])
def cmd_v149_google_connect(msg):
    try:
        schedule_command_delete(msg)
    except Exception:
        pass
    chat_id = int(msg.chat.id)
    user_id = _v149_actor_id(msg)
    ok, tid = _v149_google_can_manage(chat_id, user_id, owner_only=True)
    if not ok:
        send_and_auto_delete(chat_id, '❌ Недостаточно прав.', 10)
        return
    bot.send_message(chat_id, '🔐 Service account теперь настраивается только в Environment второго Render.\n\nВ Telegram ключ загружать не нужно. Откройте /google → «📊 Куда выгружать Excel» и пришлите ссылку или ID таблицы.')

@bot.message_handler(commands=['google_sheet'])
def cmd_v149_google_sheet(msg):
    try:
        schedule_command_delete(msg)
    except Exception:
        pass
    chat_id = int(msg.chat.id)
    user_id = _v149_actor_id(msg)
    ok, tid = _v149_google_can_manage(chat_id, user_id, owner_only=True)
    if not ok:
        send_and_auto_delete(chat_id, '❌ Недостаточно прав.', 10)
        return
    parts = str(getattr(msg, 'text', '') or '').split(maxsplit=1)
    if len(parts) > 1:
        cfg = tenant_google_config(tid)
        cfg['spreadsheet_id'] = _v149_google_id(parts[1], 'sheet')
        cfg['spreadsheet_title'] = ''
        cfg['updated_at'] = _v149_now_iso()
        tenant_google_history(tid, 'sheet_configured', 'Google Таблица сохранена', ok=True)
        tenant_google_persist(tid, 'tenant_google_update')
        bot.send_message(chat_id, '✅ Google Таблица сохранена.', reply_markup=tenant_google_keyboard(tid))
        return
    _v149_google_wait(tid, 'sheet', chat_id, user_id)
    bot.send_message(chat_id, '📊 Пришлите ссылку или ID Google Таблицы. Таблица должна быть открыта вашему service_account как редактору.')

@bot.message_handler(commands=['google_drive'])
def cmd_v149_google_drive(msg):
    try:
        schedule_command_delete(msg)
    except Exception:
        pass
    chat_id = int(msg.chat.id)
    user_id = _v149_actor_id(msg)
    ok, tid = _v149_google_can_manage(chat_id, user_id, owner_only=True)
    if not ok:
        send_and_auto_delete(chat_id, '❌ Недостаточно прав.', 10)
        return
    parts = str(getattr(msg, 'text', '') or '').split(maxsplit=1)
    if len(parts) > 1:
        cfg = tenant_google_config(tid)
        cfg['drive_folder_id'] = _v149_google_id(parts[1], 'folder')
        cfg['drive_folder_name'] = ''
        cfg['updated_at'] = _v149_now_iso()
        tenant_google_history(tid, 'drive_folder_configured', 'Папка Drive сохранена', ok=True)
        tenant_google_persist(tid, 'tenant_google_update')
        bot.send_message(chat_id, '✅ Папка Google Drive сохранена.', reply_markup=tenant_google_keyboard(tid))
        return
    _v149_google_wait(tid, 'folder', chat_id, user_id)
    bot.send_message(chat_id, '📁 Пришлите ссылку или ID папки Google Drive. Папка должна быть открыта вашему service_account как редактору.')

@bot.message_handler(commands=['google_email'])
def cmd_v149_google_email(msg):
    try:
        schedule_command_delete(msg)
    except Exception:
        pass
    chat_id = int(msg.chat.id)
    user_id = _v149_actor_id(msg)
    ok, tid = _v149_google_can_manage(chat_id, user_id, owner_only=True)
    if not ok:
        send_and_auto_delete(chat_id, '❌ Недостаточно прав.', 10)
        return
    parts = str(getattr(msg, 'text', '') or '').split(maxsplit=1)
    if len(parts) > 1:
        value = parts[1].strip()
        if not _v149_re.fullmatch('[^@\\s]+@[^@\\s]+\\.[^@\\s]+', value):
            send_and_auto_delete(chat_id, '❌ Неверный email.', 10)
            return
        cfg = tenant_google_config(tid)
        cfg['owner_google_email'] = value[:250]
        cfg['updated_at'] = _v149_now_iso()
        tenant_google_history(tid, 'owner_email_configured', 'Email Google владельца сохранён', ok=True)
        tenant_google_persist(tid, 'tenant_google_update')
        bot.send_message(chat_id, '✅ Email Google владельца сохранён.', reply_markup=tenant_google_keyboard(tid))
        return
    _v149_google_wait(tid, 'owner_email', chat_id, user_id)
    bot.send_message(chat_id, '👤 Пришлите email Google-аккаунта владельца пространства.')

def _v149_reminder_settings(tenant_id: str | None=None) -> dict:
    """Tenant-level reminder metadata (history and per-chat setting map)."""
    tid = _v149_tenant_id(tenant_id)
    row = tenant_get(tid)
    if not isinstance(row, dict):
        return {}
    settings = row.setdefault('settings', {})
    settings.setdefault('reminder_completion_history_v149', [])
    settings.setdefault('reminder_chat_settings_v149', {})
    return settings

def _v149_reminder_chat_settings(tenant_id: str | None=None, chat_id: int | None=None) -> dict:
    tid = _v149_tenant_id(tenant_id, chat_id)
    row = tenant_get(tid) or {}
    if chat_id is None:
        try:
            chat_id = int(current_state_chat_id() or row.get('root_chat_id') or 0)
        except Exception:
            chat_id = int(row.get('root_chat_id') or 0)
    try:
        cid = int(chat_id or 0)
    except Exception:
        cid = 0
    settings = _v149_reminder_settings(tid)
    mapping = settings.setdefault('reminder_chat_settings_v149', {})
    key = str(cid)
    item = mapping.get(key)
    if not isinstance(item, dict):
        item = {'merge_enabled': bool(settings.get('reminder_merge_enabled_v149', False)), 'merge_mode': 'smart' if bool(settings.get('reminder_merge_enabled_v149', False)) else 'off', 'show_complete_command': bool(settings.get('reminder_show_complete_command_v149', False))}
        mapping[key] = item
    item.setdefault('merge_enabled', False)
    if str(item.get('merge_mode') or '') not in {'off', 'smart', 'single'}:
        item['merge_mode'] = 'smart' if bool(item.get('merge_enabled', False)) else 'off'
    item['merge_enabled'] = str(item.get('merge_mode') or 'off') != 'off'
    item.setdefault('show_complete_command', False)
    item['chat_id'] = cid
    item['tenant_id'] = tid
    return item
REMINDER_MERGE_MODES_V169 = ('off', 'smart', 'single')

def _v177_legacy_0261_reminder_merge_mode(tenant_id: str | None=None, chat_id: int | None=None) -> str:
    settings = _v149_reminder_chat_settings(tenant_id, chat_id)
    mode = str(settings.get('merge_mode') or '').strip().lower()
    if mode not in REMINDER_MERGE_MODES_V169:
        mode = 'smart' if bool(settings.get('merge_enabled', False)) else 'off'
    settings['merge_mode'] = mode
    settings['merge_enabled'] = mode != 'off'
    return mode
try:
    _v177_legacy_0261_reminder_merge_mode.__name__ = 'reminder_merge_mode'
except Exception:
    pass

def _v177_legacy_0262_reminder_merge_enabled(tenant_id: str | None=None, chat_id: int | None=None) -> bool:
    return reminder_merge_mode(tenant_id, chat_id) != 'off'
try:
    _v177_legacy_0262_reminder_merge_enabled.__name__ = 'reminder_merge_enabled'
except Exception:
    pass

def _v177_legacy_0263_reminder_merge_mode_label(tenant_id: str | None=None, chat_id: int | None=None) -> str:
    return {'off': 'ВЫКЛ', 'smart': 'ВКЛ', 'single': '1 СООБЩЕНИЕ'}.get(reminder_merge_mode(tenant_id, chat_id), 'ВЫКЛ')
try:
    _v177_legacy_0263_reminder_merge_mode_label.__name__ = 'reminder_merge_mode_label'
except Exception:
    pass

def reminder_show_complete_command(tenant_id: str | None=None, chat_id: int | None=None) -> bool:
    return bool(_v149_reminder_chat_settings(tenant_id, chat_id).get('show_complete_command', False))

def _v207_reminder_setting_chat(cfg: dict | None, chat_id: int | None=None) -> int:
    try:
        if chat_id is not None and int(chat_id):
            return int(chat_id)
    except Exception:
        pass
    for raw in (cfg or {}).get('chat_ids') or []:
        try:
            return int(raw)
        except Exception:
            continue
    try:
        return int(current_state_chat_id() or 0)
    except Exception:
        return 0

def _v207_reminder_merge_mode(cfg: dict | None, chat_id: int | None=None) -> str:
    if not isinstance(cfg, dict):
        return 'off'
    mode = str(cfg.get('merge_mode_v207') or '').strip().lower()
    if mode in REMINDER_MERGE_MODES_V169:
        return mode
    cid = _v207_reminder_setting_chat(cfg, chat_id)
    try:
        mode = str(reminder_merge_mode(chat_id=cid) or 'off').strip().lower()
    except Exception:
        mode = 'off'
    if mode not in REMINDER_MERGE_MODES_V169:
        mode = 'off'
    return mode

def _canon_v207_reminder_complete_button_enabled__001(cfg: dict | None, chat_id: int | None=None) -> bool:
    if not isinstance(cfg, dict):
        return False
    value = cfg.get('show_complete_button_v207', None)
    if value is not None:
        return bool(value)
    cid = _v207_reminder_setting_chat(cfg, chat_id)
    try:
        return bool(reminder_show_complete_command(chat_id=cid))
    except Exception:
        return False

def _v207_reminder_merge_label(cfg: dict | None, chat_id: int | None=None) -> str:
    return {'off': '⬜ Объединять: ВЫКЛ', 'smart': '✅ Объединять: ВКЛ', 'single': '✅ Объединять: 1 СООБЩЕНИЕ'}.get(_v207_reminder_merge_mode(cfg, chat_id), '⬜ Объединять: ВЫКЛ')

def _canon_v207_reminder_complete_keyboard__001(reminder_id: int, cfg: dict, chat_id: int):
    if not _v207_reminder_complete_button_enabled(cfg, chat_id):
        return None
    kb = types.InlineKeyboardMarkup(row_width=1)
    kb.row(IB('✅ Выполнить', callback_data=f'v149:rem:done:{int(reminder_id)}:{int(chat_id)}'))
    return kb

def _canon_v207_reminder_group_keyboard__001(chat_id: int, members: list[tuple[int, dict]]):
    kb = types.InlineKeyboardMarkup(row_width=1)
    count = 0
    for rid, cfg in members:
        if not _v207_reminder_complete_button_enabled(cfg, chat_id):
            continue
        label = str((cfg or {}).get('text') or f'Напоминалка {rid}').strip().replace('\n', ' ')
        if len(label) > 44:
            label = label[:41] + '…'
        kb.row(IB(f'✅ Выполнить · {label}', callback_data=f'v149:rem:done:{int(rid)}:{int(chat_id)}'))
        count += 1
    return kb if count else None

def _v149_reminder_all_rows(include_completed: bool=False) -> list[tuple[int, dict]]:
    return reminder_items_global_for_completion(include_completed=include_completed)

def _v149_reminder_chat_ids(cfg: dict) -> list[int]:
    result = []
    for raw in (cfg or {}).get('chat_ids') or []:
        try:
            cid = int(raw)
        except Exception:
            continue
        if cid not in result:
            result.append(cid)
    return result

def _v149_reminder_cfg_tenant(cfg: dict) -> str:
    return str((cfg or {}).get('tenant_id') or TENANT_PLATFORM_ID)

def _v177_legacy_0264_v149_reminder_chat_allowed(cfg: dict, chat_id: int) -> bool:
    tid = _v149_reminder_cfg_tenant(cfg)
    return _v149_chat_belongs_to_tenant(int(chat_id), tid)
try:
    _v177_legacy_0264_v149_reminder_chat_allowed.__name__ = '_v149_reminder_chat_allowed'
except Exception:
    pass

def _v149_reminder_active_now(cfg: dict, now_dt) -> bool:
    return bool(cfg and cfg.get('enabled') and (not _reminder_is_completed(cfg)) and str(cfg.get('text') or '').strip() and _reminder_date_allowed(now_dt, cfg) and _reminder_time_allowed(now_dt, cfg))

def _v149_group_state_root() -> dict:
    root = data.setdefault('_global_settings', {}).setdefault('reminder_groups_v149', {})
    return root if isinstance(root, dict) else {}

def _v149_group_key(chat_id: int) -> str:
    return str(int(chat_id))

def _v149_completion_history(tenant_id: str) -> list:
    return _v149_reminder_settings(tenant_id).setdefault('reminder_completion_history_v149', [])

def _canon_v149_reminder_message_text__001(reminder_id: int, cfg: dict, chat_id: int, active_count: int=1) -> str:
    return '\n'.join(['НАПОМИНАЛКА🕰️', '', str(cfg.get('text') or '').strip()])[:4000]

def _canon_v149_group_message_text__001(chat_id: int, members: list[tuple[int, dict]]) -> str:
    lines = ['НАПОМИНАЛКА🕰️', '']
    budget = 3900
    for idx, (_rid, cfg) in enumerate(members, 1):
        text = str(cfg.get('text') or '').strip()
        block = f'{idx}. {text}'
        if len('\n'.join(lines + [block])) > budget:
            lines.append('…')
            break
        lines.append(block)
    return '\n'.join(lines)[:4000]

def _v149_delete_message(chat_id: int, message_id: int) -> None:
    if not message_id:
        return
    try:
        bot.delete_message(int(chat_id), int(message_id))
    except Exception:
        pass

def _v149_send_or_edit_group(chat_id: int, text: str, old_message_id: int=0, reply_markup=None) -> tuple[bool, int]:
    if old_message_id:
        try:
            bot.edit_message_text(text, chat_id=int(chat_id), message_id=int(old_message_id), reply_markup=reply_markup)
            return (True, int(old_message_id))
        except Exception as exc:
            if 'message is not modified' in str(exc).lower():
                return (True, int(old_message_id))
    try:
        sent = bot.send_message(int(chat_id), text, reply_markup=reply_markup)
        new_id = int(sent.message_id)
        if old_message_id and old_message_id != new_id:
            _v149_delete_message(chat_id, old_message_id)
        return (True, new_id)
    except Exception as exc:
        log_error(f'v149 reminder group send {chat_id}: {exc}')
        # R53: Telegram 400 chat-not-found is terminal.  Persist lifecycle once so
        # the existing reminder target filter stops retrying this dead chat forever.
        try:
            if _v150_error_class(exc)[0] == 'bot_removed':
                set_chat_status_v150(int(chat_id), 'bot_removed', str(exc), source='reminder_group_send', persist=True, schedule_backup=True)
                log_error(f'R53 reminder target suspended chat={int(chat_id)} reason=telegram_chat_not_found')
        except Exception as lifecycle_exc:
            log_error(f'R53 reminder lifecycle update failed chat={chat_id}: {lifecycle_exc}')
        return (False, int(old_message_id or 0))

def _v149_send_individual(chat_id: int, reminder_id: int, cfg: dict, active_count: int) -> tuple[bool, int]:
    old_mid = int((cfg.get('last_message_ids') or {}).get(str(chat_id)) or 0)
    try:
        sent = bot.send_message(int(chat_id), _v149_reminder_message_text(reminder_id, cfg, chat_id, active_count), reply_markup=_v207_reminder_complete_keyboard(reminder_id, cfg, chat_id))
        new_mid = int(sent.message_id)
        if old_mid and old_mid != new_mid:
            _v149_delete_message(chat_id, old_mid)
        return (True, new_mid)
    except Exception as exc:
        log_error(f'v149 reminder {reminder_id} send {chat_id}: {exc}')
        # R53: do not let an unreachable historic target generate a send every
        # scheduler tick.  The canonical lifecycle filter will exclude it next tick.
        try:
            if _v150_error_class(exc)[0] == 'bot_removed':
                set_chat_status_v150(int(chat_id), 'bot_removed', str(exc), source='reminder_individual_send', persist=True, schedule_backup=True)
                log_error(f'R53 reminder target suspended chat={int(chat_id)} reminder={int(reminder_id)} reason=telegram_chat_not_found')
        except Exception as lifecycle_exc:
            log_error(f'R53 reminder lifecycle update failed chat={chat_id}: {lifecycle_exc}')
        return (False, old_mid)

def _v149_cleanup_legacy_group_state_once() -> bool:
    """Remove v142 fixed-2h group messages/state without changing reminder intervals again."""
    gs = data.setdefault('_global_settings', {})
    if bool(gs.get('reminder_groups_v149_migrated')):
        return False
    old = gs.pop('reminder_groups_v142', {})
    if isinstance(old, dict):
        for key, row in list(old.items()):
            if not isinstance(row, dict):
                continue
            try:
                cid = int(row.get('target_chat_id') or str(key).rsplit(':', 1)[-1])
                mid = int(row.get('last_message_id') or 0)
            except Exception:
                cid = mid = 0
            if cid and mid:
                _v149_delete_message(cid, mid)
    gs['reminder_groups_v149_migrated'] = True
    return True

def _v245_reminder_snapshot_valid(reminder_id: int, snapshot: dict, chat_id: int | None=None) -> bool:
    """Reject stale queued reminder work after OFF/done/edit/chat changes."""
    try:
        with _REMINDER_CONFIG_LOCK:
            current = _reminder_cfg(int(reminder_id))
            if not current or not bool(current.get('enabled')) or _reminder_is_completed(current):
                return False
            if _reminder_generation_v245(current) != _reminder_generation_v245(snapshot):
                return False
            if chat_id is not None:
                cid = int(chat_id)
                if cid not in _v149_reminder_chat_ids(current):
                    return False
                if not _v149_reminder_chat_allowed(current, cid):
                    return False
            return True
    except Exception:
        return False

def _v245_delivery_cycle_prepare(cfg: dict, due_token: str) -> set[int]:
    """Return already-acked chats for this exact due cycle; reset stale acks."""
    token = str(due_token or '')
    if str(cfg.get('delivery_cycle_v245') or '') != token:
        cfg['delivery_cycle_v245'] = token
        cfg['delivery_acked_chats_v245'] = []
    acked = set()
    for raw in cfg.get('delivery_acked_chats_v245') or []:
        try:
            acked.add(int(raw))
        except Exception:
            pass
    return acked

def _v245_expected_delivery_chats(cfg: dict) -> set[int]:
    out = set()
    for cid in _v149_reminder_chat_ids(cfg):
        try:
            if _v149_reminder_chat_allowed(cfg, int(cid)):
                out.add(int(cid))
        except Exception:
            pass
    return out

def _v149_reminder_batch_job(force_chat_id: int | None=None) -> None:
    """One atomic reminder cycle for all chats.

    Every reminder retains its own interval. A merged chat refreshes whenever any member is due,
    so the visible common message follows the smallest currently active interval. Membership
    changes (completed/outside hours) refresh the same message even when no reminder is due.
    """
    if not _V149_REMINDER_BATCH_LOCK.acquire(blocking=False):
        return
    try:
        legacy_migrated = _v149_cleanup_legacy_group_state_once()
        now_dt = now_local()
        due_ids = set()
        due_chats_by_rid = {}
        cycle_token_by_rid = {}
        snapshots = {}
        active_by_chat = _v149_defaultdict(list)
        ended_changed = False
        delivery_runtime_changed = False
        with _REMINDER_CONFIG_LOCK:
            for rid, cfg in _v149_reminder_all_rows(include_completed=False):
                rid = int(rid)
                if _reminder_end_has_passed(cfg, now_dt):
                    _reminder_mark_completed(rid, cfg, 'end_date_finished', delete_messages=True)
                    ended_changed = True
                    continue
                if _reminder_due_now(cfg, now_dt):
                    if _reminder_date_allowed(now_dt, cfg) and _reminder_time_allowed(now_dt, cfg):
                        due_token = str(cfg.get('next_run_at') or '')
                        acked = _v245_delivery_cycle_prepare(cfg, due_token)
                        expected = _v245_expected_delivery_chats(cfg)
                        pending = expected - acked
                        if force_chat_id is not None:
                            pending = {int(force_chat_id)} if int(force_chat_id) in pending else set()
                        cycle_token_by_rid[rid] = due_token
                        due_chats_by_rid[rid] = set(pending)
                        if pending:
                            due_ids.add(rid)
                        elif expected:
                            due_ids.add(rid)
                        delivery_runtime_changed = True
                    else:
                        next_dt = _reminder_next_valid_start(now_dt, cfg)
                        cfg['next_run_at'] = next_dt.isoformat(timespec='seconds') if next_dt else ''
                        if next_dt is None:
                            _reminder_mark_completed(rid, cfg, 'schedule_finished', delete_messages=True)
                        else:
                            _reminder_touch(cfg)
                        ended_changed = True
                if _v149_reminder_active_now(cfg, now_dt):
                    snap = _v149_deepcopy(cfg)
                    snapshots[rid] = snap
                    for cid in _v149_reminder_chat_ids(snap):
                        if force_chat_id is not None and int(cid) != int(force_chat_id):
                            continue
                        if _v149_reminder_chat_allowed(snap, cid):
                            active_by_chat[int(cid)].append((rid, snap))
                        else:
                            try:
                                bot_journal('tenant_reminder_cross_chat_blocked', int(cid), f'reminder_id={rid} tenant={_v149_reminder_cfg_tenant(snap)}', 'WARN')
                            except Exception:
                                pass
            state_snapshot = _v149_deepcopy(_v149_group_state_root())
        individual_updates = {}
        group_updates = {}
        group_remove_individual = _v149_defaultdict(list)
        acked_updates = _v149_defaultdict(set)
        chats_to_consider = set(active_by_chat)
        if force_chat_id is None:
            chats_to_consider.update((int(k) for k in state_snapshot.keys() if str(k).lstrip('-').isdigit()))
        else:
            chats_to_consider.add(int(force_chat_id))
        for cid in sorted(chats_to_consider):
            members = [row for row in active_by_chat.get(cid, []) if _v245_reminder_snapshot_valid(row[0], row[1], cid)]
            members = sorted(members, key=lambda row: row[0])
            state = state_snapshot.get(_v149_group_key(cid), {}) or {}
            old_group_mid = int(state.get('last_message_id') or 0)
            old_member_ids = [int(x) for x in state.get('member_ids') or [] if str(x).isdigit()]
            merge_members = []
            individual_members = []
            force_individual_ids = set()
            for rid, cfg in members:
                mode = _v207_reminder_merge_mode(cfg, cid)
                if mode == 'off':
                    individual_members.append((rid, cfg))
                else:
                    merge_members.append((rid, cfg))
            current_group_ids = [rid for rid, _cfg in merge_members]
            due_group = [rid for rid, _cfg in merge_members if rid in due_ids and int(cid) in due_chats_by_rid.get(rid, set())]
            keep_group = bool(len(merge_members) >= 2 or any((_v207_reminder_merge_mode(cfg, cid) == 'single' for _rid, cfg in merge_members)))
            membership_changed = current_group_ids != old_member_ids
            if keep_group:
                if due_group or membership_changed or force_chat_id is not None or (not old_group_mid):
                    ok, message_id = _v149_send_or_edit_group(cid, _v149_group_message_text(cid, merge_members), old_group_mid, reply_markup=_v207_reminder_group_keyboard(cid, merge_members))
                    if ok:
                        for rid, cfg in merge_members:
                            if rid in due_group and _v245_reminder_snapshot_valid(rid, cfg, cid):
                                acked_updates[rid].add(int(cid))
                            old_individual = int((cfg.get('last_message_ids') or {}).get(str(cid)) or 0)
                            if old_individual:
                                group_remove_individual[rid].append((cid, old_individual))
                        group_updates[cid] = {'last_message_id': message_id, 'member_ids': current_group_ids, 'last_sent_at': _v149_now_iso(), 'tenant_id': _v149_tenant_id(target_chat_id=cid)}
                force_individual_ids.update(set(old_member_ids) - set(current_group_ids))
            else:
                if old_group_mid:
                    _v149_delete_message(cid, old_group_mid)
                    group_updates[cid] = None
                    force_individual_ids.update(old_member_ids)
                individual_members.extend(merge_members)
            active_count = len(individual_members)
            for rid, cfg in individual_members:
                is_due_here = rid in due_ids and int(cid) in due_chats_by_rid.get(rid, set())
                if not is_due_here and rid not in force_individual_ids and (force_chat_id is None):
                    continue
                if not _v245_reminder_snapshot_valid(rid, cfg, cid):
                    continue
                ok, message_id = _v149_send_individual(cid, rid, cfg, active_count)
                if ok:
                    if not _v245_reminder_snapshot_valid(rid, cfg, cid):
                        try:
                            _v149_delete_message(cid, message_id)
                        except Exception:
                            pass
                        continue
                    if is_due_here:
                        acked_updates[rid].add(int(cid))
                    individual_updates[rid, cid] = message_id
        for rid, pairs in group_remove_individual.items():
            for cid, mid in pairs:
                _v149_delete_message(cid, mid)
        changed = bool(ended_changed or legacy_migrated or delivery_runtime_changed)
        with _REMINDER_CONFIG_LOCK:
            state_root = _v149_group_state_root()
            for cid, update in group_updates.items():
                key = _v149_group_key(cid)
                if update is None:
                    state_root.pop(key, None)
                else:
                    state_root[key] = update
                changed = True
            for (rid, cid), mid in individual_updates.items():
                cfg = _reminder_cfg(rid)
                if cfg:
                    cfg.setdefault('last_message_ids', {})[str(cid)] = int(mid)
                    changed = True
            for rid, pairs in group_remove_individual.items():
                cfg = _reminder_cfg(rid)
                if cfg:
                    for cid, _mid in pairs:
                        cfg.setdefault('last_message_ids', {}).pop(str(cid), None)
                    changed = True
            for rid in sorted(due_ids):
                cfg = _reminder_cfg(rid)
                snap = snapshots.get(rid)
                if not cfg or not snap or _reminder_is_completed(cfg) or (not cfg.get('enabled')):
                    continue
                if _reminder_generation_v245(cfg) != _reminder_generation_v245(snap):
                    continue
                token = str(cycle_token_by_rid.get(rid) or cfg.get('next_run_at') or '')
                if str(cfg.get('delivery_cycle_v245') or '') != token:
                    cfg['delivery_cycle_v245'] = token
                    cfg['delivery_acked_chats_v245'] = []
                acked = set()
                for raw in cfg.get('delivery_acked_chats_v245') or []:
                    try:
                        acked.add(int(raw))
                    except Exception:
                        pass
                acked.update((int(x) for x in acked_updates.get(rid, set())))
                cfg['delivery_acked_chats_v245'] = sorted(acked)
                expected = _v245_expected_delivery_chats(cfg)
                if expected and expected.issubset(acked):
                    cfg['last_sent_at'] = now_dt.isoformat(timespec='seconds')
                    cfg['delivery_cycle_v245'] = ''
                    cfg['delivery_acked_chats_v245'] = []
                    _reminder_advance_after_send(now_dt, cfg)
                    if not cfg.get('next_run_at') or _reminder_end_has_passed(cfg, now_local()):
                        _reminder_mark_completed(rid, cfg, 'schedule_finished', delete_messages=True)
                    else:
                        _reminder_touch(cfg)
                    try:
                        bot_journal('reminder_cycle_delivered_v245', None, f'reminder_id={rid} chats={len(expected)}')
                    except Exception:
                        pass
                else:
                    missing = sorted(expected - acked)
                    try:
                        bot_journal('reminder_cycle_retry_v245', None, f'reminder_id={rid} missing={missing}', 'WARN')
                    except Exception:
                        pass
                changed = True
            for cid, row in list(state_root.items()):
                try:
                    chat_id = int(cid)
                except Exception:
                    continue
                next_rows = []
                member_ids = []
                for rid, cfg in _v149_reminder_all_rows(include_completed=False):
                    if not _v149_reminder_active_now(cfg, now_local()) or chat_id not in _v149_reminder_chat_ids(cfg):
                        continue
                    if not _v149_reminder_chat_allowed(cfg, chat_id):
                        continue
                    if _v207_reminder_merge_mode(cfg, chat_id) == 'off':
                        continue
                    member_ids.append(int(rid))
                    dt = _reminder_parse_dt(cfg.get('next_run_at'))
                    if dt is not None:
                        next_rows.append(dt)
                row['member_ids'] = sorted(member_ids)
                row['next_run_at'] = min(next_rows).isoformat(timespec='seconds') if next_rows else ''
        if changed:
            _reminder_save('v149_dynamic_merged_tick')
        if due_ids or group_updates:
            try:
                bot_journal('reminder_v149_batch', None, f'due={len(due_ids)} chats={len(chats_to_consider)} groups={sum((1 for v in group_updates.values() if v))}')
            except Exception:
                pass
    finally:
        _V149_REMINDER_BATCH_LOCK.release()

def _canon_reminder_tick__001() -> None:
    global _REMINDER_FINANCE_BUSY_SINCE
    finance_busy = _reminder_finance_priority_busy()
    if finance_busy:
        if not _REMINDER_FINANCE_BUSY_SINCE:
            _REMINDER_FINANCE_BUSY_SINCE = _v149_time.monotonic()
        if _v149_time.monotonic() - _REMINDER_FINANCE_BUSY_SINCE < _REMINDER_FINANCE_PRIORITY_GRACE_SECONDS:
            return
    else:
        _REMINDER_FINANCE_BUSY_SINCE = 0.0
    if not REMINDER_TASK_POOL.submit_unique('reminder-v149-batch', _v149_reminder_batch_job, None):
        try:
            bot_journal('reminder_dispatch_coalesced', None, 'v149 batch')
        except Exception:
            pass

def _canon_reminder_group_send_job__001(target_chat_id: int, day_key: str | None=None, force: bool=False) -> None:
    _v149_reminder_batch_job(int(target_chat_id))

def _canon_build_reminder_list_text__001() -> str:
    rows = _reminder_items()
    enabled = sum((1 for _rid, cfg in rows if bool(cfg.get('enabled'))))
    return f'⏰ НАПОМИНАЛКИ\n\nТекущих: {len(rows)} · активных: {enabled}\nЗавершённых: {len(_reminder_completed_items())}\n\nНастройки «Объединять» и кнопки «Выполнить» теперь задаются отдельно внутри каждой напоминалки.'

def _canon_build_reminder_list_keyboard__001(day_key: str | None=None, page: int=0):
    day_key = str(day_key or today_key())
    rows = _reminder_items()
    pages = max(1, (len(rows) + _REMINDER_LIST_PAGE_SIZE - 1) // _REMINDER_LIST_PAGE_SIZE)
    page = max(0, min(int(page or 0), pages - 1))
    kb = types.InlineKeyboardMarkup(row_width=1)
    kb.row(IB('+добавить⏰', callback_data=f'rem:add:{page}:{day_key}'))
    start = page * _REMINDER_LIST_PAGE_SIZE
    for idx, (rid, cfg) in enumerate(rows[start:start + _REMINDER_LIST_PAGE_SIZE], start=start + 1):
        kb.row(IB(_reminder_button_label(idx, cfg), callback_data=f'rem:open:{rid}:{page}:{day_key}'))
    if pages > 1:
        nav = []
        if page > 0:
            nav.append(IB('⬅️', callback_data=f'rem:list:{page - 1}:{day_key}'))
        nav.append(IB(f'{page + 1}/{pages}', callback_data='none'))
        if page + 1 < pages:
            nav.append(IB('➡️', callback_data=f'rem:list:{page + 1}:{day_key}'))
        kb.row(*nav)
    kb.row(IB(f'✅ Завершённые ({len(_reminder_completed_items())})', callback_data='rem:completed:0:0'))
    kb.row(IB('📜 История выполнений', callback_data='v149:rem:history'))
    kb.row(IB('⬅️ Назад', callback_data=f'd:{day_key}:back_main'))
    return kb

def _canon_v149_reminders_for_completion__001(chat_id: int) -> list[tuple[int, dict]]:
    rows = []
    current = now_local()
    for rid, cfg in _reminder_items(include_completed=False):
        if not _v149_reminder_active_now(cfg, current):
            continue
        if int(chat_id) not in _v149_reminder_chat_ids(cfg):
            continue
        if not _v149_reminder_chat_allowed(cfg, chat_id):
            continue
        rows.append((int(rid), cfg))
    rows.sort(key=lambda row: row[0])
    return rows

def _canon_v149_complete_reminder__001(reminder_id: int, chat_id: int, actor_user_id: int, actor_label: str) -> tuple[bool, str]:
    with _V149_COMPLETION_LOCK, _REMINDER_CONFIG_LOCK:
        cfg = reminder_cfg_global_for_completion(int(reminder_id))
        if not cfg or int(chat_id) not in _v149_reminder_chat_ids(cfg):
            return (False, 'Напоминалка не найдена в этом чате.')
        if _reminder_is_completed(cfg) or not cfg.get('enabled'):
            return (False, 'Эта напоминалка уже выполнена или выключена. Повторное выполнение не записано.')
        tenant_id = _v149_reminder_cfg_tenant(cfg)
        event_id = _v149_hashlib.sha256(f"{tenant_id}:{int(reminder_id)}:{cfg.get('created_at')}:{cfg.get('updated_at')}".encode('utf-8')).hexdigest()[:24]
        history = _v149_completion_history(tenant_id)
        if any((str(row.get('event_id')) == event_id for row in history if isinstance(row, dict))):
            return (False, 'Это выполнение уже учтено.')
        text = str(cfg.get('text') or '').strip()
        _reminder_mark_completed(int(reminder_id), cfg, 'manual_vyapl', delete_messages=True)
        cfg['completed_by_user_id'] = int(actor_user_id or 0)
        cfg['completed_by_label'] = str(actor_label or '')[:120]
        cfg['completed_in_chat_id'] = int(chat_id)
        cfg['completion_event_id'] = event_id
        event = {'event_id': event_id, 'at': str(cfg.get('completed_at') or _v149_now_iso()), 'tenant_id': tenant_id, 'reminder_id': int(reminder_id), 'reminder_text': text[:500], 'chat_id': int(chat_id), 'chat_title': str(get_chat_display_name(int(chat_id)) or '')[:150], 'user_id': int(actor_user_id or 0), 'user': str(actor_label or '')[:120]}
        history.append(event)
        del history[:-500]
        _reminder_save('reminder_manual_vyapl')
    try:
        submitted = REMINDER_TASK_POOL.submit_unique('reminder-v149-batch', _v149_reminder_batch_job, None)
        if not submitted:
            try:
                DELAYED_SCHEDULER.schedule(f'reminder-v245-complete:{int(reminder_id)}', 0.5, lambda: REMINDER_TASK_POOL.submit_unique('reminder-v149-batch', _v149_reminder_batch_job, None))
            except Exception:
                pass
    except Exception:
        pass
    try:
        bot_journal('reminder_manual_completed', int(chat_id), f'reminder_id={int(reminder_id)} user={int(actor_user_id or 0)} event={event_id}')
    except Exception:
        pass
    return (True, f'✅ Выполнено: {text[:300]}')

def _v149_completion_keyboard(chat_id: int, rows: list[tuple[int, dict]]):
    kb = types.InlineKeyboardMarkup(row_width=1)
    for rid, cfg in rows[:30]:
        label = str(cfg.get('text') or f'Напоминалка {rid}').strip().replace('\n', ' ')
        if len(label) > 48:
            label = label[:45] + '…'
        kb.row(IB(f'✅ {label}', callback_data=f'v149:rem:done:{int(rid)}:{int(chat_id)}'))
    return kb

def _v149_completion_history_text(tenant_id: str) -> str:
    rows = list(_v149_completion_history(tenant_id))[-30:]
    if not rows:
        return '📜 ИСТОРИЯ ВЫПОЛНЕНИЙ\n\nПока пусто.'
    lines = ['📜 ИСТОРИЯ ВЫПОЛНЕНИЙ', '']
    for row in reversed(rows):
        lines.append(f"✅ {row.get('at')} · №{row.get('reminder_id')}\n{row.get('reminder_text')}\nКто: {row.get('user') or row.get('user_id')}\nЧат: {row.get('chat_title') or row.get('chat_id')}")
    return '\n\n'.join(lines)[:3900]

@bot.message_handler(func=lambda m: bool(_v149_re.match('^/vyapl(?:_\\d+)?(?:@[A-Za-z0-9_]+)?(?:\\s|$)', str(getattr(m, 'text', '') or ''), _v149_re.I)), content_types=['text'])
def cmd_v149_vyapl(msg):
    try:
        schedule_command_delete(msg)
    except Exception:
        pass
    chat_id = int(msg.chat.id)
    user_id = _v149_actor_id(msg)
    label = _v149_actor_label(msg)
    match = _v149_re.match('^/vyapl(?:_(\\d+))?(?:@[A-Za-z0-9_]+)?', str(msg.text or ''), _v149_re.I)
    rid = int(match.group(1)) if match and match.group(1) else None
    rows = _v149_reminders_for_completion(chat_id)
    if rid is not None:
        ok, text = _v149_complete_reminder(rid, chat_id, user_id, label)
        bot.send_message(chat_id, text)
        return
    if not rows:
        send_and_auto_delete(chat_id, 'Нет активных напоминалок для выполнения.', 10)
        return
    if len(rows) == 1:
        ok, text = _v149_complete_reminder(rows[0][0], chat_id, user_id, label)
        bot.send_message(chat_id, text)
        return
    bot.send_message(chat_id, 'Какую напоминалку отметить выполненной?', reply_markup=_v149_completion_keyboard(chat_id, rows))

@bot.message_handler(commands=['vyapl_history'])
def cmd_v149_vyapl_history(msg):
    try:
        schedule_command_delete(msg)
    except Exception:
        pass
    chat_id = int(msg.chat.id)
    user_id = _v149_actor_id(msg)
    tid = str(tenant_id_for_chat(chat_id, create=False) or TENANT_PLATFORM_ID)
    if not tenant_can_manage(user_id, tid):
        send_and_auto_delete(chat_id, '❌ История доступна владельцу и администраторам пространства.', 10)
        return
    bot.send_message(chat_id, _v149_completion_history_text(tid))

def _v177_legacy_0266_v149_extension_callback(call, data_str: str) -> bool:
    data_str = str(data_str or '')
    if not data_str.startswith('v149:'):
        return False
    chat_id = int(call.message.chat.id)
    user_id = _v149_actor_id(call)
    try:
        if data_str.startswith('v149:google:'):
            ok, tid = _v149_google_can_manage(chat_id, user_id, owner_only=True)
            if not ok:
                bot.answer_callback_query(call.id, 'Только владелец пространства', show_alert=True)
                return True
            action = data_str.split(':', 2)[2]
            if action == 'connect':
                bot.send_message(chat_id, '🔐 Service account хранится только на Render #2. Здесь ключ не загружается.\n\nИспользуйте «📊 Куда выгружать Excel» и укажите таблицу.')
            elif action == 'sheet':
                _v149_google_wait(tid, 'sheet', chat_id, user_id)
                bot.send_message(chat_id, '📊 Пришлите ссылку или ID своей Google Таблицы.')
            elif action == 'folder':
                _v149_google_wait(tid, 'folder', chat_id, user_id)
                bot.send_message(chat_id, '📁 Пришлите ссылку или ID своей папки Google Drive.')
            elif action == 'owner_email':
                _v149_google_wait(tid, 'owner_email', chat_id, user_id)
                bot.send_message(chat_id, '👤 Пришлите email Google-аккаунта владельца пространства.')
            elif action in {'toggle_sheet', 'toggle_drive'}:
                cfg = tenant_google_config(tid)
                settings = cfg.setdefault('export_settings', {})
                key = 'sheet_enabled' if action == 'toggle_sheet' else 'drive_enabled'
                settings[key] = not bool(settings.get(key, True))
                cfg['updated_at'] = _v149_now_iso()
                tenant_google_history(tid, action, f'{key}={settings[key]}', ok=True)
                tenant_google_persist(tid, 'tenant_google_settings')
                bot.send_message(chat_id, tenant_google_status_text(tid), reply_markup=tenant_google_keyboard(tid))
            elif action == 'create_sheet':
                url = tenant_google_create_spreadsheet(tid, f"Финансы · {(tenant_get(tid) or {}).get('name') or tid}")
                bot.send_message(chat_id, f'✅ Таблица создана и закреплена за пространством:\n{url}', disable_web_page_preview=True)
            elif action == 'test':
                _ok, text = tenant_google_test(tid)
                bot.send_message(chat_id, text)
            elif action == 'history':
                bot.send_message(chat_id, _v149_google_history_text(tid, False))
            elif action == 'errors':
                bot.send_message(chat_id, _v149_google_history_text(tid, True))
            elif action == 'disconnect_confirm':
                kb = types.InlineKeyboardMarkup(row_width=2)
                kb.row(IB('🧹 Да, отключить', callback_data='v149:google:disconnect'), IB('Отмена', callback_data='v149:google:status'))
                bot.send_message(chat_id, 'Отключить Google только у этого пространства? Таблицы и файлы в Google удалены не будут.', reply_markup=kb)
            elif action == 'disconnect':
                cfg = tenant_google_config(tid)
                keep_history = list(cfg.get('history') or [])
                keep_errors = list(cfg.get('errors') or [])
                (tenant_get(tid) or {}).pop('google_v149', None)
                fresh = tenant_google_config(tid)
                fresh['history'] = keep_history
                fresh['errors'] = keep_errors
                tenant_google_history(tid, 'account_disconnected', 'Google отключён', ok=True)
                tenant_google_persist(tid, 'tenant_google_disconnect')
                bot.send_message(chat_id, '✅ Google этого пространства отключён.')
            elif action == 'status':
                bot.send_message(chat_id, tenant_google_status_text(tid), reply_markup=tenant_google_keyboard(tid))
            try:
                bot.answer_callback_query(call.id)
            except Exception:
                pass
            return True
        if data_str.startswith('v149:rem:'):
            parts = data_str.split(':')
            action = parts[2] if len(parts) > 2 else ''
            tid = str(tenant_id_for_chat(chat_id, create=False) or TENANT_PLATFORM_ID)
            if action in {'merge', 'command'}:
                if not tenant_can_manage(user_id, tid):
                    bot.answer_callback_query(call.id, 'Недостаточно прав', show_alert=True)
                    return True
                settings = _v149_reminder_chat_settings(tid, chat_id)
                if action == 'merge':
                    current_mode = reminder_merge_mode(tid, chat_id)
                    try:
                        idx = REMINDER_MERGE_MODES_V169.index(current_mode)
                    except ValueError:
                        idx = 0
                    next_mode = REMINDER_MERGE_MODES_V169[(idx + 1) % len(REMINDER_MERGE_MODES_V169)]
                    settings['merge_mode'] = next_mode
                    settings['merge_enabled'] = next_mode != 'off'
                else:
                    key = 'show_complete_command'
                    settings[key] = not bool(settings.get(key, False))
                settings['updated_at'] = _v149_now_iso()
                tenant_google_persist(tid, 'reminder_chat_settings_v149')
                page = int(parts[3]) if len(parts) > 3 and str(parts[3]).isdigit() else 0
                day_key = parts[4] if len(parts) > 4 else today_key()
                with tenant_context(tid):
                    reminder_text = build_reminder_list_text()
                    reminder_keyboard = build_reminder_list_keyboard(day_key, page)
                safe_edit(bot, call, reminder_text, reply_markup=reminder_keyboard)
                if action == 'merge':
                    REMINDER_TASK_POOL.submit_unique('reminder-v149-batch', _v149_reminder_batch_job, None)
                try:
                    bot.answer_callback_query(call.id, 'Настройка обновлена')
                except Exception:
                    pass
                return True
            if action == 'done':
                rid = int(parts[3])
                target_chat_id = int(parts[4])
                if target_chat_id != chat_id:
                    bot.answer_callback_query(call.id, 'Кнопка относится к другому чату', show_alert=True)
                    return True
                try:
                    clicked_mid = int(call.message.message_id)
                    group_mid = int((_v149_group_state_root().get(_v149_group_key(chat_id), {}) or {}).get('last_message_id') or 0)
                except Exception:
                    clicked_mid = group_mid = 0
                ok, text = _v149_complete_reminder(rid, chat_id, user_id, _v149_actor_label(call))
                try:
                    bot.answer_callback_query(call.id, text[:180], show_alert=not ok)
                except Exception:
                    pass
                if ok:
                    if clicked_mid and clicked_mid != group_mid:
                        _v149_delete_message(chat_id, clicked_mid)
                    try:
                        REMINDER_TASK_POOL.submit_unique('reminder-v149-batch', _v149_reminder_batch_job, int(chat_id))
                    except Exception:
                        pass
                return True
            if action == 'history':
                if not tenant_can_manage(user_id, tid):
                    bot.answer_callback_query(call.id, 'Недостаточно прав', show_alert=True)
                    return True
                bot.send_message(chat_id, _v149_completion_history_text(tid))
                try:
                    bot.answer_callback_query(call.id)
                except Exception:
                    pass
                return True
    except Exception as exc:
        try:
            if data_str.startswith('v149:google:'):
                tid = str(tenant_id_for_chat(chat_id, create=False) or TENANT_PLATFORM_ID)
                tenant_google_error(tid, 'callback', exc)
            bot.answer_callback_query(call.id, str(exc)[:180], show_alert=True)
        except Exception:
            pass
        return True
    return True
try:
    _v177_legacy_0266_v149_extension_callback.__name__ = 'v149_extension_callback'
except Exception:
    pass

# --- ИСТОЧНИК: 99_web_runtime.py ---
def _v205_http_audit_operation() -> str:
    try:
        path = str(request.path or '/')
        if path.startswith('/tg/'):
            path = '/tg/<webhook>'
        elif path.startswith('/expense-ping/'):
            path = '/expense-ping/<token>'
        return f'http-server:{request.method}:{path[:80]}'
    except Exception:
        return 'http-server'

@app.after_request
def _v205_traffic_after_request(response):
    try:
        inbound = int(request.content_length or 0)
        body_len = response.calculate_content_length()
        if body_len is None:
            body_len = len(response.get_data() or b'')
        hdr = sum((len(str(k)) + len(str(v)) + 4 for k, v in response.headers.items()))
        traffic_audit_record('web_http', _v205_http_audit_operation(), int(body_len or 0) + hdr, inbound, int(getattr(response, 'status_code', 200) or 200) >= 500)
    except Exception:
        pass
    return response

@app.route('/', methods=['GET'])
def index():
    return ('OK', 200) if runtime_is_ready() else ('BOOTING', 503)

@app.route('/healthz', methods=['GET'])
def healthz():
    return ({'ok': True, 'version': VERSION, 'phase': _RUNTIME_STATE.get('phase'), 'ready': runtime_is_ready(), 'shutting_down': runtime_is_shutting_down()}, 200)

@app.route('/readyz', methods=['GET'])
def readyz():
    code = 200 if runtime_is_ready() else 503
    return ({'ok': runtime_is_ready(), 'version': VERSION, 'phase': _RUNTIME_STATE.get('phase'), 'task_recovery_remaining': _RUNTIME_STATE.get('task_recovery_remaining', 0)}, code)

@app.route('/keepalive', methods=['GET', 'HEAD'])
def keepalive_endpoint():
    ping_at = _journal_ts()
    user_agent = str(request.headers.get('User-Agent', '') or '')[:240]
    KEEP_ALIVE_STATE['external_ping_at'] = ping_at
    KEEP_ALIVE_STATE['last_keepalive_user_agent'] = user_agent
    if user_agent == _keepalive_wire_user_agent_v250('keepalive'):
        KEEP_ALIVE_STATE['self_ping_at'] = ping_at
    else:
        KEEP_ALIVE_STATE['external_monitor_at'] = ping_at
        is_peer = 'peer-keepalive' in user_agent.casefold() or 'peer-watchdog' in user_agent.casefold()
        if is_peer:
            KEEP_ALIVE_STATE['peer_received_at'] = ping_at
        try:
            keepalive_note_inbound_activity('peer_watchdog' if is_peer else 'external_keepalive')
        except Exception:
            pass
    if request.method == 'HEAD':
        return ('', 200)
    return ({'ok': True, 'version': VERSION, 'time': ping_at, 'profile': active_bot_behavior_profile(), 'keep_alive': bool(globals().get('keepalive_self_enabled', lambda: KEEP_ALIVE_ENABLED)()), 'self_interval_seconds': int(globals().get('keepalive_self_interval_seconds', lambda: KEEP_ALIVE_INTERVAL_SECONDS)()), 'auto_keep_alive': bool(globals().get('keepalive_auto_enabled', lambda: True)()), 'auto_idle_seconds': int(globals().get('keepalive_auto_idle_seconds', lambda: 720)()), 'peer_keep_alive': bool(globals().get('keepalive_peer_enabled', lambda: False)()), 'ready': runtime_is_ready(), 'phase': _RUNTIME_STATE.get('phase'), 'uptime_seconds': round(max(0.0, time.monotonic() - _RUNTIME_STARTED_MONO), 1), 'external_monitor_seen': bool(KEEP_ALIVE_STATE.get('external_monitor_at'))}, 200)

@app.route('/expense-ping/<token>', methods=['GET', 'POST'])
def expense_ping_endpoint(token: str):
    """Защищённый endpoint для iPhone Shortcuts/Back Tap.

    Событие сначала сохраняется в постоянную очередь бота, поэтому временная ошибка
    Telegram не стирает отметку расхода: доставка будет повторена.
    """
    try:
        keepalive_note_inbound_activity('expense_ping')
    except Exception:
        pass
    if not runtime_is_ready() or runtime_is_shutting_down():
        return ({'ok': False, 'status': 'booting'}, 503)
    cfg = expense_shortcut_config(False) or {}
    expected = str(cfg.get('token') or '')
    if not expected or not secrets.compare_digest(str(token or ''), expected):
        return ({'ok': False}, 404)
    if 'safety_profile_new_enabled' in globals() and safety_profile_new_enabled():
        try:
            rate_key = f"{request.remote_addr or 'unknown'}:{str(token)[-8:]}"
            now_ts = time.time()
            bucket = _IPHONE_ENDPOINT_RUNTIME[rate_key]
            while bucket and now_ts - float(bucket[0]) > 60.0:
                bucket.popleft()
            if len(bucket) >= 10:
                try:
                    bot_journal('expense_ping_rate_limited', None, f'key={rate_key}', 'WARN')
                except Exception:
                    pass
                return ({'ok': False, 'error': 'rate_limited'}, 429)
            bucket.append(now_ts)
        except Exception:
            pass
    try:
        event_id, duplicate = enqueue_expense_ping_event('iphone_back_tap', force=False)
        target_chat_id = int(expense_shortcut_config(True).get('target_chat_id') or 0)
        return ({'ok': True, 'queued': True, 'duplicate_suppressed': bool(duplicate), 'event': event_id, 'target_chat_id': target_chat_id, 'time': now_local().isoformat(timespec='seconds')}, 202 if not duplicate else 200)
    except Exception as exc:
        log_error(f'expense ping endpoint: {exc}')
        return ({'ok': False, 'error': 'queue_failed'}, 503)

def _refresh_callback_window_timers(chat_id: int, message_id: int, raw_callback: str):
    """v135: любой клик в связанном окне начинает ВСЕ его авто-таймеры заново."""
    chat_id = int(chat_id)
    message_id = int(message_id)
    raw = str(raw_callback or '')
    resolved = resolve_short_callback(raw) or raw
    try:
        _touch_v98_auto_close_for_callback(chat_id, message_id, resolved)
    except Exception:
        pass
    store = get_chat_store(chat_id)
    try:
        for timer_chat_id, store_key in list(_aux_window_timers.keys()):
            if int(timer_chat_id) == chat_id and int(store.get(str(store_key)) or 0) == message_id:
                schedule_stored_window_delete(chat_id, str(store_key), None)
    except Exception:
        pass
    try:
        wait = store.get('edit_wait') or {}
        if int(wait.get('prompt_msg_id') or 0) == message_id:
            schedule_cancel_edit(chat_id, message_id, delay=None)
    except Exception:
        pass
    try:
        wait = store.get('finwin_edit_wait') or {}
        if int(wait.get('prompt_msg_id') or 0) == message_id:
            schedule_cancel_finwin_edit(chat_id, message_id, delay=None)
    except Exception:
        pass
    for field in ('category_add_wait', 'category_edit_wait'):
        try:
            wait = store.get(field) or {}
            if int(wait.get('prompt_msg_id') or 0) == message_id:
                schedule_cancel_category_wait(chat_id, field, message_id, delay=None)
        except Exception:
            pass
    try:
        wait = store.get('forward_copy_edit_wait') or {}
        if int(wait.get('prompt_msg_id') or 0) == message_id:
            schedule_forward_copy_edit_wait_cancel(chat_id, message_id, delay=None)
    except Exception:
        pass
    try:
        active = store.get('secret_active_window') or {}
        if int(active.get('message_id') or 0) == message_id:
            schedule_secret_calendar_close(chat_id, message_id)
    except Exception:
        pass
    try:
        if (chat_id, message_id) in _secret_media_timer_generation:
            schedule_secret_media_close(chat_id, message_id)
    except Exception:
        pass
    try:
        secret_wait = store.get('secret_wait') or {}
        if int(secret_wait.get('prompt_msg_id') or 0) == message_id:
            schedule_o9_secret_wait_timeout(chat_id, message_id, O9_SECRET_WAIT_SECONDS)
    except Exception:
        pass

def _protect_pending_ui_timers_on_receipt(payload: dict):
    """Продлевает связанные авто-close/auto-cancel/auto-return уже в момент receipt webhook."""
    try:
        if not isinstance(payload, dict):
            return
        msg = payload.get('message') or payload.get('edited_message')
        if isinstance(msg, dict):
            chat = msg.get('chat') or {}
            chat_id = int(chat.get('id'))
            store = get_chat_store(chat_id)
            wait = store.get('edit_wait') or {}
            if isinstance(wait, dict) and wait.get('prompt_msg_id'):
                schedule_cancel_edit(chat_id, int(wait['prompt_msg_id']), delay=None)
            wait = store.get('finwin_edit_wait') or {}
            if isinstance(wait, dict) and wait.get('prompt_msg_id'):
                schedule_cancel_finwin_edit(chat_id, int(wait['prompt_msg_id']), delay=None)
            for field in ('category_add_wait', 'category_edit_wait'):
                wait = store.get(field) or {}
                if isinstance(wait, dict) and wait.get('prompt_msg_id'):
                    schedule_cancel_category_wait(chat_id, field, int(wait['prompt_msg_id']), delay=None)
            wait = store.get('forward_copy_edit_wait') or {}
            if isinstance(wait, dict) and wait.get('prompt_msg_id'):
                schedule_forward_copy_edit_wait_cancel(chat_id, int(wait['prompt_msg_id']), delay=None)
            try:
                secret_wait = store.get('secret_wait') or {}
                if isinstance(secret_wait, dict) and secret_wait.get('prompt_msg_id'):
                    schedule_o9_secret_wait_timeout(chat_id, int(secret_wait['prompt_msg_id']), O9_SECRET_WAIT_SECONDS)
            except Exception:
                pass
            return
        cq = payload.get('callback_query')
        if isinstance(cq, dict):
            cmsg = cq.get('message') or {}
            chat = cmsg.get('chat') or {}
            chat_id = int(chat.get('id'))
            message_id = int(cmsg.get('message_id') or 0)
            if message_id:
                _refresh_callback_window_timers(chat_id, message_id, str(cq.get('data') or ''))
    except Exception as e:
        try:
            log_error(f'receipt timer protection: {e}')
        except Exception:
            pass
import hashlib as _v163_webhook_hashlib
_v163_webhook_seed = os.getenv('WEBHOOK_SECRET', '').strip() or _v163_webhook_hashlib.sha256(('telegram-webhook-v163|' + str(BOT_TOKEN) + '|' + str(os.getenv('RENDER_SERVICE_ID', '') or WEBHOOK_URL)).encode('utf-8')).hexdigest()[:40]
WEBHOOK_SECRET_PATH = _v163_webhook_seed
WEBHOOK_ROUTE_PATH = f'/tg/{WEBHOOK_SECRET_PATH}'
WEBHOOK_HEADER_SECRET = _v163_webhook_hashlib.sha256(('header|' + WEBHOOK_SECRET_PATH + '|' + str(BOT_TOKEN)).encode('utf-8')).hexdigest()[:48]
WEBHOOK_HEADER_SECRET_ENABLED = False

_V260_WEBHOOK_INBOX_KIND = 'webhook_inbox_v260'
_V260_WEBHOOK_MAX_ATTEMPTS = 5

# R49: Telegram admission/replay uses one persistent SQLite store.  Schema/WAL are
# configured exactly once; a single bounded writer serializes durable mutations and
# a separate query-only connection serves reads.  Post-business `done` marks can be
# queued asynchronously so bookkeeping never extends the user-visible handler.
_V260_INBOX_DB = Path(os.getenv('WEBHOOK_INBOX_DB_FILE', str(DB_FILE) + '.webhook_inbox.sqlite3') or (str(DB_FILE) + '.webhook_inbox.sqlite3')).resolve()

class _V260WebhookInboxStore:
    def __init__(self, path: Path):
        import queue as _queue
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.read_lock = threading.RLock()
        self.write_q = _queue.PriorityQueue(maxsize=max(128, min(5000, int(os.getenv('WEBHOOK_INBOX_WRITE_QUEUE_MAX', '1000') or '1000'))))
        self.seq = 0
        self.seq_lock = threading.RLock()
        self.stats = {'submitted':0, 'done':0, 'failed':0, 'dropped':0, 'max_pending':0}
        self.write_conn = sqlite3.connect(str(self.path), timeout=2.0, check_same_thread=False)
        self.write_conn.row_factory = sqlite3.Row
        self._configure(self.write_conn, writer=True)
        self.read_conn = sqlite3.connect(str(self.path), timeout=1.0, check_same_thread=False)
        self.read_conn.row_factory = sqlite3.Row
        self._configure(self.read_conn, writer=False)
        self.thread = threading.Thread(target=self._writer_loop, name='webhook-inbox-writer-1', daemon=True)
        self.thread.start()

    def _configure(self, conn, writer: bool):
        conn.execute('PRAGMA busy_timeout=1500')
        if writer:
            conn.execute('PRAGMA journal_mode=WAL')
            conn.execute('PRAGMA synchronous=FULL')
            conn.execute('CREATE TABLE IF NOT EXISTS inbox(update_id TEXT PRIMARY KEY, v TEXT NOT NULL, updated_ts REAL NOT NULL DEFAULT 0)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_inbox_updated ON inbox(updated_ts)')
            conn.commit()
        else:
            try: conn.execute('PRAGMA query_only=ON')
            except Exception: pass

    def _next_seq(self):
        with self.seq_lock:
            self.seq += 1
            return self.seq

    def _writer_loop(self):
        while True:
            priority, seq, fn, ev, box = self.write_q.get()
            try:
                box['result'] = fn(self.write_conn)
                self.write_conn.commit()
                box['ok'] = True
                self.stats['done'] += 1
            except Exception as exc:
                try: self.write_conn.rollback()
                except Exception: pass
                box['error'] = exc
                self.stats['failed'] += 1
            finally:
                if ev is not None: ev.set()
                self.write_q.task_done()

    def submit(self, fn, *, priority=1, wait=True, timeout=3.0):
        ev = threading.Event() if wait else None
        box = {'ok':False, 'result':None, 'error':None}
        item = (max(0, min(9, int(priority))), self._next_seq(), fn, ev, box)
        try:
            self.write_q.put(item, block=bool(wait), timeout=max(0.05, float(timeout)) if wait else 0)
            self.stats['submitted'] += 1
            self.stats['max_pending'] = max(int(self.stats.get('max_pending') or 0), self.write_q.qsize())
        except Exception:
            self.stats['dropped'] += 1
            if wait: raise
            return False
        if not wait:
            return True
        if not ev.wait(max(0.5, float(timeout))):
            raise TimeoutError('webhook inbox writer timeout')
        if box.get('error') is not None:
            raise box['error']
        return box.get('result')

    @staticmethod
    def _dump(row):
        return json.dumps(row, ensure_ascii=False, separators=(',', ':'), default=str)

    def write_row(self, row: dict, *, wait=True, priority=1):
        if not isinstance(row, dict) or not row.get('update_id'):
            return False
        payload = self._dump(row)
        uid = str(row.get('update_id'))
        ts = float(row.get('updated_ts') or time.time())
        def _op(conn):
            conn.execute('INSERT INTO inbox(update_id,v,updated_ts) VALUES(?,?,?) ON CONFLICT(update_id) DO UPDATE SET v=excluded.v,updated_ts=excluded.updated_ts', (uid, payload, ts))
            return True
        return self.submit(_op, priority=priority, wait=wait)

    def read_row(self, update_id):
        with self.read_lock:
            row = self.read_conn.execute('SELECT v FROM inbox WHERE update_id=?', (str(update_id),)).fetchone()
        if not row: return {}
        try:
            obj = json.loads(row[0])
            return obj if isinstance(obj, dict) else {}
        except Exception:
            return {}

    def mark(self, update_id, state: str, error: str='', *, wait=True, priority=1):
        uid = str(update_id); new_state = str(state or ''); err = str(error or '')[:500]
        def _op(conn):
            raw = conn.execute('SELECT v FROM inbox WHERE update_id=?', (uid,)).fetchone()
            try: row = json.loads(raw[0]) if raw else {}
            except Exception: row = {}
            if not isinstance(row, dict): row = {}
            row.setdefault('update_id', uid); row.setdefault('payload', {}); row.setdefault('type', 'other')
            attempts = max(0, int(row.get('attempts') or 0))
            if new_state in {'running','external_running'} and str(row.get('state') or '') not in {'running','external_running'}:
                attempts += 1
            row.update({'state':new_state,'attempts':attempts,'error':err,'updated_at':now_local().isoformat(timespec='milliseconds'),'updated_ts':time.time()})
            payload = self._dump(row)
            conn.execute('INSERT INTO inbox(update_id,v,updated_ts) VALUES(?,?,?) ON CONFLICT(update_id) DO UPDATE SET v=excluded.v,updated_ts=excluded.updated_ts', (uid, payload, float(row['updated_ts'])))
            return row
        return self.submit(_op, priority=priority, wait=wait)

    def scan(self):
        with self.read_lock:
            raw = self.read_conn.execute('SELECT update_id,v,updated_ts FROM inbox').fetchall()
        out=[]
        for r in raw:
            try:
                obj=json.loads(r[1]) if isinstance(r[1],str) else {}
                if isinstance(obj,dict): out.append(obj)
            except Exception: pass
        return out

    def delete_keys(self, keys):
        vals=[(str(k),) for k in keys if str(k)]
        if not vals: return 0
        return self.submit(lambda conn: (conn.executemany('DELETE FROM inbox WHERE update_id=?', vals), len(vals))[1], priority=5, wait=True)

    def status(self):
        return dict(self.stats, pending=self.write_q.qsize(), alive=bool(self.thread.is_alive()))

_V260_INBOX_STORE = _V260WebhookInboxStore(_V260_INBOX_DB)
_V260_INBOX_READY = True

# Compatibility names below are canonical thin APIs over the single R49 store; they
# do not create connections or PRAGMAs per event.
def _v260_inbox_write(row: dict) -> bool:
    return bool(_V260_INBOX_STORE.write_row(row, wait=True, priority=1))

def _v260_webhook_inbox_row(update_id) -> dict:
    try: return _V260_INBOX_STORE.read_row(update_id)
    except Exception: return {}

def _v260_webhook_inbox_put(update_id, payload, chat_id=None, update_type='other') -> bool:
    """Durably register admission before HTTP 200; only this admission write waits."""
    try:
        old = _v260_webhook_inbox_row(update_id) or {}
        state = str(old.get('state') or '')
        row = {
            'update_id': str(update_id), 'chat_id': chat_id, 'type': str(update_type or 'other'), 'payload': payload,
            'state': state if state in {'queued','running','done','failed','external_pending','external_running','external_failed_review','needs_review'} else 'queued',
            'attempts': max(0, int(old.get('attempts') or 0)), 'error': str(old.get('error') or '')[:500],
            'updated_at': now_local().isoformat(timespec='milliseconds'), 'updated_ts': time.time()
        }
        return bool(_V260_INBOX_STORE.write_row(row, wait=True, priority=0))
    except Exception as exc:
        log_error(f'WEBHOOK INBOX R49 put update={update_id}: {exc}')
        return False

def _v260_webhook_inbox_mark(update_id, state: str, error: str=''):
    try: return _V260_INBOX_STORE.mark(update_id, state, error, wait=True, priority=1) or {}
    except Exception as exc:
        log_error(f'WEBHOOK INBOX R49 mark update={update_id}: {exc}')
        return {}

def _v260_webhook_inbox_mark_async(update_id, state: str='done', error: str='') -> bool:
    try: return bool(_V260_INBOX_STORE.mark(update_id, state, error, wait=False, priority=2))
    except Exception as exc:
        log_error(f'WEBHOOK INBOX R49 async mark update={update_id}: {exc}')
        return False

def _v260_webhook_inbox_state(update_id) -> str:
    return str((_v260_webhook_inbox_row(update_id) or {}).get('state') or '')

def _v260_inbox_scan_rows() -> list[dict]:
    try: return _V260_INBOX_STORE.scan()
    except Exception: return []

def _v260_inbox_delete_keys(keys) -> None:
    try: _V260_INBOX_STORE.delete_keys(keys)
    except Exception: pass

def _v260_inbox_migrate_legacy_once() -> int:
    """Best-effort one-time read of R35 rows without taking SQLITE.lock."""
    marker = _V260_INBOX_DB.with_suffix(_V260_INBOX_DB.suffix + '.migrated_r36')
    if marker.exists(): return 0
    moved=0
    try:
        conn=sqlite3.connect(str(DB_FILE),timeout=.5,check_same_thread=False)
        try:
            rows=conn.execute('SELECT k,v FROM meta WHERE kind=?', (_V260_WEBHOOK_INBOX_KIND,)).fetchall()
        finally: conn.close()
        for _k, raw in rows:
            try:
                obj=json.loads(raw) if isinstance(raw,str) else {}
                if isinstance(obj,dict) and obj.get('update_id') and _v260_inbox_write(obj): moved+=1
            except Exception: pass
    except Exception:
        pass
    try: marker.write_text(str(time.time()),encoding='utf-8')
    except Exception: pass
    return moved

def _v260_submit_webhook_inbox_row(row: dict) -> bool:
    """Replay on the same keyed lane, but never race a just-active human."""
    if not isinstance(row, dict):
        return False
    try:
        quiet = float(globals().get('r27_user_quiet_for', lambda: 10**9)())
        if quiet < 5.0:
            scheduler = globals().get('DELAYED_SCHEDULER')
            update_id = row.get('update_id')
            if scheduler is not None:
                scheduler.schedule(f'r48-recovery-yield:{update_id}', max(0.5, 5.0-quiet), lambda: _v260_submit_webhook_inbox_row(_v260_webhook_inbox_row(update_id) or row))
            return True
    except Exception:
        pass
    update_id = row.get('update_id')
    payload = row.get('payload') or {}
    chat_id = row.get('chat_id')
    update_type = str(row.get('type') or 'other')
    update_key = chat_id if chat_id is not None else update_id
    selector = globals().get('v163_webhook_select_lane')
    try:
        if callable(selector):
            selected_pool, selected_key = selector(payload, update_type, update_key)
        else:
            selected_pool = UI_TASK_POOL if update_type == 'callback_query' else WEBHOOK_TASK_POOL
            selected_key = f'ui:{update_key}' if update_type == 'callback_query' else update_key
        return bool(selected_pool.submit(selected_key, _v260_replay_webhook_inbox_row, row))
    except Exception as exc:
        log_error(f'WEBHOOK INBOX V260 submit update={update_id}: {exc}')
        return False


def _v260_schedule_webhook_inbox_retry(row_or_update_id, delay: float | None=None) -> bool:
    try:
        row = row_or_update_id if isinstance(row_or_update_id, dict) else _v260_webhook_inbox_row(row_or_update_id)
        if not isinstance(row, dict) or not row:
            return False
        update_id = row.get('update_id')
        attempts = max(0, int(row.get('attempts') or 0))
        if attempts >= _V260_WEBHOOK_MAX_ATTEMPTS:
            _v260_webhook_inbox_mark(update_id, 'needs_review', str(row.get('error') or 'local retry exhausted'))
            return False
        delays = (1.0, 3.0, 8.0, 20.0, 45.0)
        wait = float(delay if delay is not None else delays[min(attempts, len(delays)-1)])
        scheduler = globals().get('DELAYED_SCHEDULER')
        if scheduler is None:
            return False
        scheduler.schedule(f'webhook-inbox-v260:{update_id}', wait, lambda: _v260_submit_webhook_inbox_row(_v260_webhook_inbox_row(update_id)))
        return True
    except Exception as exc:
        log_error(f'WEBHOOK INBOX V260 retry schedule: {exc}')
        return False


def _v260_replay_webhook_inbox_row(row: dict):
    update_id = row.get('update_id'); payload = row.get('payload') or {}
    chat_id = row.get('chat_id'); update_type = str(row.get('type') or 'other')
    current = _v260_webhook_inbox_row(update_id) or row
    if str(current.get('state') or '') == 'done':
        return True
    if int(current.get('attempts') or 0) >= _V260_WEBHOOK_MAX_ATTEMPTS:
        _v260_webhook_inbox_mark(update_id, 'needs_review', str(current.get('error') or 'local retry exhausted'))
        return False
    try:
        _v260_webhook_inbox_mark(update_id, 'running')
        _execute_telegram_payload(payload, update_id, chat_id, update_type)
        _v260_webhook_inbox_mark(update_id, 'done')
        _r13_commit_fn = globals().get('split_event_committed_v268')
        if callable(_r13_commit_fn): _r13_commit_fn(update_id, chat_id, update_type, True, '')
        bot_journal('webhook_inbox_recovered_v260', chat_id, f'update_id={update_id}; type={update_type}')
        return True
    except Exception as exc:
        failed_row = _v260_webhook_inbox_mark(update_id, 'failed', str(exc))
        _r13_commit_fn = globals().get('split_event_committed_v268')
        if callable(_r13_commit_fn): _r13_commit_fn(update_id, chat_id, update_type, False, str(exc))
        log_error(f'WEBHOOK INBOX V260 recovery failed update={update_id}: {exc}')
        _v260_schedule_webhook_inbox_retry(failed_row or update_id)
        return False


def recover_webhook_inbox_v260(limit: int=100) -> int:
    rows=[]
    try:
        _v260_inbox_migrate_legacy_once()
        raw=_v260_inbox_scan_rows()
        stale_done=[]
        now_ts=time.time()
        for row in raw:
            if not isinstance(row,dict): continue
            key=str(row.get('update_id') or '')
            state = str(row.get('state') or '')
            if state == 'done' and now_ts-float(row.get('updated_ts') or now_ts) > 172800:
                stale_done.append(str(key)); continue
            # Cloud/external work has its own MEGA task registry and must never be
            # replayed by the local-only inbox after a restart.
            if state.startswith('external_') or state == 'done':
                continue
            if state not in {'queued','running','failed'}:
                continue
            if int(row.get('attempts') or 0) >= _V260_WEBHOOK_MAX_ATTEMPTS:
                _v260_webhook_inbox_mark(row.get('update_id'), 'needs_review', str(row.get('error') or 'local retry exhausted'))
                continue
            rows.append(row)
        if stale_done:
            _v260_inbox_delete_keys(stale_done)
    except Exception as exc:
        log_error(f'WEBHOOK INBOX V260 scan: {exc}'); return 0
    submitted=0
    for row in rows[:max(1,int(limit))]:
        if _v260_submit_webhook_inbox_row(row):
            submitted+=1
    return submitted

def _r19_update_journal_start(update_id, update_chat_id, update_type, wait, durable_cloud):
    try:
        bot_journal('update_process_start', update_chat_id, f'update_id={update_id} type={update_type} queue_wait={wait:.3f}s durable={durable_cloud}')
    except Exception:
        pass


def _r19_post_update_cleanup(update_id, update_chat_id, update_type, wait, started, success, durable_cloud):
    # Never hold the user-facing callback worker while flushing cold chat state or
    # writing diagnostic rows. These actions are important, but not interactive.
    try:
        bot_journal('update_process_done', update_chat_id, f'update_id={update_id} type={update_type} queue_wait={wait:.3f}s process={time.time() - started:.3f}s total={time.time() - (started - wait):.3f}s success={success} durable={durable_cloud}')
    except Exception:
        pass
    # R24: do not throw an active chat out of RAM after every button. Memory-pressure
    # eviction is handled centrally by the idle sweep / durable cleanup only.


def _r19_schedule_post_update_cleanup(update_id, update_chat_id, update_type, wait, started, success, durable_cloud):
    pool = globals().get('UI_CLEANUP_TASK_POOL') or globals().get('BACKGROUND_TASK_POOL')
    if pool is not None:
        try:
            if pool.submit(f'cleanup:{update_id}', _r19_post_update_cleanup, update_id, update_chat_id, update_type, wait, started, success, durable_cloud):
                return True
        except Exception:
            pass
    return False



def _r22_callback_inbox_mark_background(update_id, state: str, error: str='') -> None:
    """SQLite inbox bookkeeping outside the callback worker."""
    try:
        _v260_webhook_inbox_mark(update_id, state, error)
    except Exception:
        pass


def _r22_callback_commit_background(update_id, chat_id, success: bool, error: str='') -> None:
    try:
        fn = globals().get('split_event_committed_v268')
        if callable(fn):
            fn(update_id, chat_id, 'callback_query', bool(success), str(error or ''))
    except Exception:
        pass


def _r22_callback_sidejobs(payload: dict, update_id, update_chat_id) -> None:
    """Remote witness/timer/journal work that must never precede FAST dispatch."""
    try:
        fn = globals().get('split_witness_event_v268')
        if callable(fn):
            if not fn(update_id, payload, update_chat_id, 'callback_query'):
                log_error(f'R22 CALLBACK REMOTE WITNESS FAILED update={update_id}')
    except Exception as exc:
        try: log_error(f'R22 CALLBACK REMOTE WITNESS ERROR update={update_id}: {exc}')
        except Exception: pass
    try:
        _protect_pending_ui_timers_on_receipt(payload)
    except Exception:
        pass


def _r25_callback_durable_admission(payload: dict, update_id, update_chat_id) -> None:
    """Persist/mirror a callback after FAST admission; never delays HTTP 200 or UI."""
    try:
        if not _v260_webhook_inbox_put(update_id, payload, update_chat_id, 'callback_query'):
            log_error(f'R26 CALLBACK LOCAL INBOX BACKGROUND FAILED update={update_id}')
    except Exception as exc:
        try: log_error(f'R26 CALLBACK LOCAL INBOX ERROR update={update_id}: {exc}')
        except Exception: pass
    try:
        _r22_callback_sidejobs(payload, update_id, update_chat_id)
    except Exception:
        pass


_R48_NAV_COALESCE_LOCK = threading.RLock()
_R48_NAV_INFLIGHT = set()

# R65: priority navigation epoch.  Back/Info/Main may bypass an ordinary window
# callback, so any older render that finishes later must not repaint over it.
_R65_NAV_EPOCH_LOCK = threading.RLock()
_R65_WINDOW_NAV_EPOCH = {}
_R65_UPDATE_NAV_EPOCH = {}

def _r65_is_priority_navigation(raw: str) -> bool:
    low = str(raw or '').casefold()
    if not low:
        return False
    business = globals().get('_v166_is_finance_business_callback')
    try:
        if callable(business) and business(raw):
            return False
    except Exception:
        pass
    safe = globals().get('_v166_is_safe_window_callback')
    try:
        if callable(safe):
            return bool(safe(raw))
    except Exception:
        pass
    if low in {'nav_prev', 'info_close', 'journal_back', 'fw_back_src'}:
        return True
    if low.startswith('d:'):
        try:
            cmd = low.split(':', 2)[2]
        except Exception:
            cmd = low
        return any(x in cmd for x in ('info', 'back_main', 'forward_menu', 'calendar', 'prev', 'next', 'today'))
    return ('back' in low) or low.endswith('_close')

def _r65_note_callback_epoch(payload: dict, update_id) -> None:
    try:
        cq = (payload or {}).get('callback_query') or {}
        msg = cq.get('message') or {}
        chat = int((msg.get('chat') or {}).get('id'))
        mid = int(msg.get('message_id'))
        raw = str(cq.get('data') or '')
    except Exception:
        return
    key = (chat, mid)
    now = time.time()
    with _R65_NAV_EPOCH_LOCK:
        epoch = int(_R65_WINDOW_NAV_EPOCH.get(key, 0) or 0)
        is_nav = bool(_r65_is_priority_navigation(raw))
        if is_nav:
            epoch += 1
            _R65_WINDOW_NAV_EPOCH[key] = epoch
        _R65_UPDATE_NAV_EPOCH[str(update_id or '')] = {'chat': chat, 'message_id': mid, 'epoch': epoch, 'is_nav': is_nav, 'ts': now}
        if len(_R65_UPDATE_NAV_EPOCH) > 3000:
            cutoff = now - 1800.0
            for uid, row in list(_R65_UPDATE_NAV_EPOCH.items()):
                if float((row or {}).get('ts') or 0.0) < cutoff:
                    _R65_UPDATE_NAV_EPOCH.pop(uid, None)

def _r65_render_epoch_for_update(update_id, chat_id: int, message_id: int) -> dict:
    try:
        key = (int(chat_id), int(message_id))
    except Exception:
        return {}
    with _R65_NAV_EPOCH_LOCK:
        row = dict(_R65_UPDATE_NAV_EPOCH.get(str(update_id or ''), {}) or {})
        current = int(_R65_WINDOW_NAV_EPOCH.get(key, 0) or 0)
    return {'_r65_nav_epoch': int(row.get('epoch', current) or 0), '_r65_nav_is_priority': bool(row.get('is_nav', False))}

def _r65_render_is_stale_after_navigation(payload: dict) -> bool:
    try:
        key = (int(payload.get('chat_id')), int(payload.get('message_id')))
        render_epoch = int(payload.get('_r65_nav_epoch') or 0)
    except Exception:
        return False
    with _R65_NAV_EPOCH_LOCK:
        current = int(_R65_WINDOW_NAV_EPOCH.get(key, 0) or 0)
    return render_epoch < current

def _r48_nav_coalesce_key(payload: dict):
    """Only idempotent navigation clicks are coalesced. Money/edit/delete/apply are never dropped."""
    try:
        cq=(payload or {}).get('callback_query') or {}; raw=str(cq.get('data') or '')
        msg=cq.get('message') or {}; chat=(msg.get('chat') or {}).get('id'); mid=msg.get('message_id')
        if not raw or chat is None or mid is None: return None
        business=globals().get('_v166_is_finance_business_callback')
        if callable(business) and business(raw): return None
        low=raw.casefold()
        safe=False
        if low in {'nav_prev','back','forward_menu_style_toggle','buttons_current_toggle','icon_buttons_toggle','journal_back','keepalive_status','info_queues','info_delta_status'}: safe=True
        if low.startswith('d:'):
            try: cmd=low.split(':',2)[2]
            except Exception: cmd=low
            safe=any(x in cmd for x in ('calendar','info','back_main','prev','next','today','forward_menu','forward_finmode_menu')) and not any(x in cmd for x in ('delete','edit','save','apply','confirm','toggle_'))
        if not safe and (low.startswith(('fw_back','fw_new_back','rem:list','rem:open')) or low.endswith('_close')): safe=True
        return f'{int(chat)}:{int(mid)}:{raw}' if safe else None
    except Exception:
        return None

def _r48_mark_coalesced_callback_durable(payload: dict, update_id, update_chat_id):
    try: _v260_webhook_inbox_put(update_id,payload,update_chat_id,'callback_query')
    except Exception: pass
    try: _v260_webhook_inbox_mark_async(update_id,'done','coalesced_safe_navigation_r49')
    except Exception: pass
    try: _r22_callback_commit_background(update_id,update_chat_id,True,'coalesced_safe_navigation_r48')
    except Exception: pass


def _r22_accept_callback_fast(payload: dict, update_id, update_chat_id, update_key):
    """R22 callback admission.

    Ordering guarantee: claim + FAST enqueue happen before any SQLite/Redis/network
    durability work.  HTTP 200 is still withheld until the local SQLite inbox is
    durable, so deploy/crash safety is retained while the visible UI can already run.
    """
    claim_state, ticket = UPDATE_DISPATCHER.claim(update_id, update_chat_id, 'callback_query')
    try:
        _cq0=(payload or {}).get('callback_query') or {}; _m0=_cq0.get('message') or {}
        r52_note_callback_activity(); r52_diag('CALLBACK_CLAIM', update=update_id, chat=update_chat_id, msg=_m0.get('message_id'), user=((_cq0.get('from') or {}).get('id') if isinstance(_cq0.get('from'),dict) else None), action=str(_cq0.get('data') or '')[:240], claim=claim_state, dispatcher=UPDATE_DISPATCHER.stats(), pools=r52_hot_pool_snapshot())
    except Exception: pass
    if claim_state == 'new':
        try:
            _r65_note_callback_epoch(payload, update_id)
        except Exception:
            pass
    _r48_coalesce_key = _r48_nav_coalesce_key(payload) if claim_state == 'new' else None
    if claim_state == 'new' and _r48_coalesce_key:
        with _R48_NAV_COALESCE_LOCK:
            if _r48_coalesce_key in _R48_NAV_INFLIGHT:
                UPDATE_DISPATCHER.finish(update_id, True, 'coalesced_safe_navigation_r48')
                try: UI_CLEANUP_TASK_POOL.submit(f'r48-coalesced:{update_id}', _r48_mark_coalesced_callback_durable, payload, update_id, update_chat_id)
                except Exception: pass
                try: log_info(f'R48 NAV COALESCE update={update_id} chat={update_chat_id} key={_r48_coalesce_key}')
                except Exception: pass
                return ('OK', 200)
            _R48_NAV_INFLIGHT.add(_r48_coalesce_key)
    if claim_state == 'new':
        update_enqueued_at = time.time()

        def _process_callback():
            started = time.time()
            wait = started - update_enqueued_at
            UPDATE_DISPATCHER.mark_started(update_id)
            try: r52_diag('CALLBACK_WORKER_ENTER', update=update_id, chat=update_chat_id, wait=wait, action=str(((payload or {}).get('callback_query') or {}).get('data') or '')[:240], dispatcher=UPDATE_DISPATCHER.stats(), pools=r52_hot_pool_snapshot())
            except Exception: pass
            try:
                _cq = payload.get('callback_query') or {}
                r25_trace_begin(update_id, update_chat_id, 'callback_query', str(_cq.get('data') or ''))
                r25_trace_stage('HANDLER_ENTER')
            except Exception:
                pass
            try:
                UI_CLEANUP_TASK_POOL.submit(f'r22-inbox-running:{update_id}', _r22_callback_inbox_mark_background, update_id, 'running', '')
                UI_CLEANUP_TASK_POOL.submit(f'r22-journal-start:{update_id}', _r19_update_journal_start, update_id, update_chat_id, 'callback_query', wait, False)
            except Exception:
                pass
            success = False
            error_text = ''
            try:
                try: r25_trace_stage('EXECUTE_TELEGRAM_PAYLOAD_START')
                except Exception: pass
                try: r52_diag('EXECUTE_PAYLOAD_START', update=update_id, chat=update_chat_id, action=str(((payload or {}).get('callback_query') or {}).get('data') or '')[:240], pools=r52_hot_pool_snapshot())
                except Exception: pass
                _execute_telegram_payload(payload, update_id, update_chat_id, 'callback_query')
                try: r52_diag('EXECUTE_PAYLOAD_DONE', update=update_id, chat=update_chat_id, elapsed=time.time()-started, pools=r52_hot_pool_snapshot())
                except Exception: pass
                try: r25_trace_stage('EXECUTE_TELEGRAM_PAYLOAD_DONE')
                except Exception: pass
                success = True
                try:
                    UI_CLEANUP_TASK_POOL.submit(f'r22-inbox-done:{update_id}', _r22_callback_inbox_mark_background, update_id, 'done', '')
                    UI_CLEANUP_TASK_POOL.submit(f'r22-event-commit:{update_id}', _r22_callback_commit_background, update_id, update_chat_id, True, '')
                except Exception:
                    pass
            except Exception as exc:
                error_text = str(exc)
                try:
                    UI_CLEANUP_TASK_POOL.submit(f'r22-inbox-failed:{update_id}', _r22_callback_inbox_mark_background, update_id, 'failed', error_text)
                    UI_CLEANUP_TASK_POOL.submit(f'r22-event-failed:{update_id}', _r22_callback_commit_background, update_id, update_chat_id, False, error_text)
                except Exception:
                    pass
                try:
                    _v260_schedule_webhook_inbox_retry(update_id)
                except Exception:
                    pass
                try:
                    log_error(f'R22 CALLBACK PROCESS FAILED update={update_id} chat={update_chat_id}: {exc}')
                    r52_diag('CALLBACK_WORKER_ERROR', update=update_id, chat=update_chat_id, action=str(((payload or {}).get('callback_query') or {}).get('data') or '')[:240], elapsed=time.time()-started, error=f'{type(exc).__name__}:{str(exc)[:1200]}', traceback=''.join(traceback.format_exc())[-6000:], pools=r52_hot_pool_snapshot())
                except Exception:
                    pass
                raise
            finally:
                try:
                    r25_trace_stage('HANDLER_DONE', time.time()-started, str(error_text or '')[:160])
                    log_info(f'FASTBTN handler update={update_id} chat={update_chat_id} wait={wait:.3f}s process={time.time()-started:.3f}s success={int(bool(success))} error={str(error_text or "")[:120]}')
                    r52_diag('CALLBACK_WORKER_EXIT', update=update_id, chat=update_chat_id, wait=wait, elapsed=time.time()-started, success=int(bool(success)), error=str(error_text or '')[:800], dispatcher=UPDATE_DISPATCHER.stats(), pools=r52_hot_pool_snapshot())
                except Exception:
                    pass
                UPDATE_DISPATCHER.finish(update_id, success, error_text)
                if _r48_coalesce_key:
                    try:
                        with _R48_NAV_COALESCE_LOCK: _R48_NAV_INFLIGHT.discard(_r48_coalesce_key)
                    except Exception: pass
                try: r25_trace_end()
                except Exception: pass
                _r19_schedule_post_update_cleanup(update_id, update_chat_id, 'callback_query', wait, started, success, False)

        selector = globals().get('v163_webhook_select_lane')
        if callable(selector):
            selected_pool, selected_key = selector(payload, 'callback_query', update_key)
        else:
            selected_pool, selected_key = (FAST_UI_TASK_POOL, f'fast-callback:{update_key}')
        try: r52_diag('CALLBACK_LANE_SELECTED', update=update_id, chat=update_chat_id, action=str(((payload or {}).get('callback_query') or {}).get('data') or '')[:240], pool=getattr(selected_pool,'name','?'), key=selected_key, pool_stats=selected_pool.stats() if hasattr(selected_pool,'stats') else {})
        except Exception: pass
        _r52_enqueued = selected_pool.submit(selected_key, _process_callback)
        try: r52_diag('CALLBACK_ENQUEUE_RESULT', update=update_id, chat=update_chat_id, pool=getattr(selected_pool,'name','?'), key=selected_key, queued=int(bool(_r52_enqueued)), pool_stats=selected_pool.stats() if hasattr(selected_pool,'stats') else {}, dispatcher=UPDATE_DISPATCHER.stats())
        except Exception: pass
        if not _r52_enqueued:
            if _r48_coalesce_key:
                try:
                    with _R48_NAV_COALESCE_LOCK: _R48_NAV_INFLIGHT.discard(_r48_coalesce_key)
                except Exception: pass
            UPDATE_DISPATCHER.release_failed_enqueue(update_id, f'{selected_pool.name}_queue_full')
            return ('BUSY', 503)
        UPDATE_DISPATCHER.mark_enqueued(update_id, selected_pool.name, selected_key)
    elif claim_state == 'done':
        # Keep the local durable row healthy if Telegram redelivered after a network race.
        try:
            if not _v260_webhook_inbox_put(update_id, payload, update_chat_id, 'callback_query'):
                return ('LOCAL DURABLE INBOX FAILED', 503)
        except Exception:
            return ('LOCAL DURABLE INBOX FAILED', 503)
        return ('OK', 200)

    # R26: FAST enqueue is the webhook admission point. SQLite inbox + remote witness
    # happen after admission on a background lane. This removes the 4-5 second POST /tg
    # tail seen when the shared SQLite connection was busy, while exact business ordering
    # remains inside the keyed callback actor.
    try:
        pool = globals().get('UI_CLEANUP_TASK_POOL') or globals().get('BACKGROUND_TASK_POOL')
        queued = bool(pool and pool.submit_unique(f'r25-callback-durable:{update_id}', _r25_callback_durable_admission, payload, update_id, update_chat_id))
        if not queued:
            try: log_error(f'R48 callback durable lane busy update={update_id}; bounded retry scheduled')
            except Exception: pass
            scheduler=globals().get('DELAYED_SCHEDULER')
            if scheduler is not None:
                scheduler.schedule(f'r48-callback-durable-retry:{update_id}',0.5,lambda: _r25_callback_durable_admission(payload,update_id,update_chat_id))
    except Exception:
        pass
    try:
        UPDATE_DISPATCHER.mark_http_acked(update_id)
        _cq = payload.get('callback_query') or {}
        log_info(f'BTNTRACE update={update_id} chat={update_chat_id} action={str(_cq.get("data") or "")[:180]} stage=FAST_ENQUEUED_HTTP200')
        r52_diag('CALLBACK_HTTP200', update=update_id, chat=update_chat_id, action=str(_cq.get('data') or '')[:240], dispatcher=UPDATE_DISPATCHER.stats(), pools=r52_hot_pool_snapshot())
    except Exception:
        pass
    return ('OK', 200)

@app.route(WEBHOOK_ROUTE_PATH, methods=['POST'])
def telegram_webhook():
    if WEBHOOK_HEADER_SECRET_ENABLED:
        supplied = str(request.headers.get('X-Telegram-Bot-Api-Secret-Token', '') or '')
        if supplied != WEBHOOK_HEADER_SECRET:
            # R53: a secret mismatch used to be completely silent and therefore
            # looked exactly like a dead callback dispatcher.  Never print either
            # secret; log only request metadata and whether a header was present.
            try:
                log_error(
                    'R53 WEBHOOK FORBIDDEN: secret header mismatch; '
                    f'present={int(bool(supplied))} content_length={request.content_length or 0} '
                    f'remote={str(request.headers.get("X-Forwarded-For") or request.remote_addr or "")[:120]}'
                )
                r52_diag('WEBHOOK_FORBIDDEN', header_present=int(bool(supplied)), content_length=request.content_length or 0, remote=str(request.headers.get('X-Forwarded-For') or request.remote_addr or '')[:120])
            except Exception:
                pass
            return ('FORBIDDEN', 403)
    try:
        keepalive_note_inbound_activity('telegram_webhook')
    except Exception:
        pass
    try:
        payload = request.get_json(force=True, silent=False)
        try:
            _r27_note = globals().get('r27_note_user_activity')
            if callable(_r27_note) and isinstance(payload, dict) and any(k in payload for k in ('callback_query','message','edited_message')):
                _r27_note('telegram')
        except Exception:
            pass
    except Exception as e:
        log_error(f'WEBHOOK: get_json failed: {e}')
        return ('BAD REQUEST', 400)
    if runtime_is_shutting_down():
        runtime_mark_webhook(payload if isinstance(payload, dict) else None, blocked='shutdown')
        return ('SHUTTING DOWN', 503)
    if not runtime_is_ready():
        runtime_mark_webhook(payload if isinstance(payload, dict) else None, blocked='boot')
        try:
            _boot_cq = (payload.get('callback_query') or {}) if isinstance(payload, dict) else {}
            log_info(
                f'R54 WEBHOOK DURING BOOT update={(payload or {}).get("update_id") if isinstance(payload, dict) else "?"} '
                f'type={"callback_query" if _boot_cq else "message" if isinstance(payload, dict) and "message" in payload else "other"} '
                f'phase={str((_RUNTIME_STATE or {}).get("phase") or "")}'
            )
            r52_diag('WEBHOOK_DURING_BOOT', update=(payload or {}).get('update_id') if isinstance(payload, dict) else None, action=str(_boot_cq.get('data') or '')[:240], phase=str((_RUNTIME_STATE or {}).get('phase') or ''))
        except Exception:
            pass
        return ('BOOTING', 503)
    runtime_mark_webhook(payload if isinstance(payload, dict) else None)
    # R26 forensic receipt marker (normal Render log only; no DB/network dependency).
    if isinstance(payload, dict) and 'callback_query' in payload:
        try:
            _r25_cq = payload.get('callback_query') or {}
            _r25_msg = _r25_cq.get('message') or {}; _r25_chat = _r25_msg.get('chat') or {}
            log_info(f'BTNTRACE update={payload.get("update_id")} chat={_r25_chat.get("id")} action={str(_r25_cq.get("data") or "")[:180]} stage=RECEIVE')
            r52_note_callback_activity(); r52_diag('WEBHOOK_RECEIVE', update=payload.get('update_id'), callback_id=str(_r25_cq.get('id') or ''), chat=_r25_chat.get('id'), msg=_r25_msg.get('message_id'), user=((_r25_cq.get('from') or {}).get('id') if isinstance(_r25_cq.get('from'),dict) else None), action=str(_r25_cq.get('data') or '')[:240], content_length=request.content_length or 0, remote=str(request.headers.get('X-Forwarded-For') or request.remote_addr or '')[:120], dispatcher=UPDATE_DISPATCHER.stats(), pools=r52_hot_pool_snapshot())
        except Exception:
            pass
    # R18 absolute UI hot path: start Telegram callback ACK immediately after the
    # READY/shutdown gate, before logging, Update.de_json, SQLite inbox, Redis/Worker
    # witness, locks or routing.  The ACK uses a dedicated pool, so Telegram network
    # RTT runs in parallel with local window rendering.
    if isinstance(payload, dict) and 'callback_query' in payload:
        try:
            _r18_cq = payload.get('callback_query') or {}
            _r18_msg = _r18_cq.get('message') or {}
            _r18_chat = _r18_msg.get('chat') or {}
            _r18_cid = _r18_chat.get('id')
            try:
                _r25_reg = globals().get('r25_register_callback_update')
                if callable(_r25_reg): _r25_reg(str(_r18_cq.get('id') or ''), payload.get('update_id'), _r18_cid, str(_r18_cq.get('data') or ''))
            except Exception:
                pass
            _r52_ack_scheduled=schedule_callback_receipt_ack(str(_r18_cq.get('id') or ''), _r18_cid, delay=0.0)
            try: r52_diag('ACK_SCHEDULE_RESULT', update=payload.get('update_id'), callback_id=str(_r18_cq.get('id') or ''), chat=_r18_cid, action=str(_r18_cq.get('data') or '')[:240], scheduled=int(bool(_r52_ack_scheduled)), ack_pool=CALLBACK_ACK_TASK_POOL.stats())
            except Exception: pass
        except Exception as ack_exc:
            log_error(f'CALLBACK IMMEDIATE ACK: {ack_exc}')
            try: r52_diag('ACK_SCHEDULE_ERROR', update=(payload or {}).get('update_id'), error=f'{type(ack_exc).__name__}:{str(ack_exc)[:800]}', pools=r52_hot_pool_snapshot())
            except Exception: pass
    try:
        if isinstance(payload, dict):
            if 'edited_message' in payload:
                log_info('WEBHOOK: получен update с edited_message ✅')
            elif 'message' in payload:
                log_info('WEBHOOK: получен update с message')
            elif 'callback_query' in payload:
                log_info('WEBHOOK: получен update с callback_query')
            try:
                upd_type = 'edited_message' if 'edited_message' in payload else 'message' if 'message' in payload else 'callback_query' if 'callback_query' in payload else 'other'
                if upd_type == 'callback_query':
                    cid_j = _extract_update_chat_id(payload)
                    UI_CLEANUP_TASK_POOL.submit(f'r22-webhook-journal:{payload.get("update_id", time.time_ns())}', bot_journal, 'webhook_update', cid_j, upd_type)
                else:
                    bot_journal('webhook_update', _extract_update_chat_id(payload), upd_type)
            except Exception:
                pass
        update = telebot.types.Update.de_json(payload)
        update_chat_id = _extract_update_chat_id(payload) if isinstance(payload, dict) else None
        update_id = getattr(update, 'update_id', None)
        if update_id is None:
            update_id = time.time_ns()
        update_key = update_chat_id if update_chat_id is not None else update_id
        update_type = 'edited_message' if isinstance(payload, dict) and 'edited_message' in payload else 'callback_query' if isinstance(payload, dict) and 'callback_query' in payload else 'message' if isinstance(payload, dict) and 'message' in payload else 'other'
        if update_type == 'callback_query':
            # Rare finance toggles keep the pre-execution cloud witness because replaying
            # a toggle twice can reverse state. All normal/navigation callbacks take R22.
            _r22_cloud_critical, _r22_cloud_reason = durable_task_required(payload)
            if not _r22_cloud_critical:
                return _r22_accept_callback_fast(payload, update_id, update_chat_id, update_key)
        _r25_adm_action = ''
        try:
            if update_type == 'callback_query': _r25_adm_action = str((payload.get('callback_query') or {}).get('data') or '')[:180]
            elif update_type in {'message','edited_message'}: _r25_adm_action = str(((payload.get(update_type) or payload.get('message') or {}).get('text') or update_type))[:180]
            log_info(f'BTNTRACE update={update_id} chat={update_chat_id} action={_r25_adm_action} stage=ADMISSION_SQLITE_START')
        except Exception: pass
        _r25_adm_started = time.monotonic()
        _inbox_state_v260 = _v260_webhook_inbox_state(update_id)
        if _inbox_state_v260 == 'done':
            return ('OK', 200)
        if not _v260_webhook_inbox_put(update_id, payload, update_chat_id, update_type):
            return ('LOCAL DURABLE INBOX FAILED', 503)
        try: log_info(f'BTNTRACE update={update_id} chat={update_chat_id} action={_r25_adm_action} stage=ADMISSION_SQLITE_DONE elapsed={time.monotonic()-_r25_adm_started:.3f}s')
        except Exception: pass
        # R13: before Telegram gets HTTP 200 and before business execution starts,
        # make the raw update durable on Worker/Redis.  If both remote witnesses are
        # unavailable, return 503 so Telegram retries instead of risking a deploy gap.
        _r13_witness_fn = globals().get('split_witness_event_v268')
        if callable(_r13_witness_fn):
            if update_type == 'callback_query':
                # UI callbacks are already in the local durable inbox.  Mirror the raw
                # event remotely on DELTA lane, but never put Redis/Worker RTT in front
                # of a user's button.  Message/finance traffic keeps the strict witness.
                def _r18_callback_witness():
                    try:
                        if not _r13_witness_fn(update_id, payload, update_chat_id, update_type):
                            log_error(f'R18 CALLBACK REMOTE WITNESS FAILED update={update_id}')
                    except Exception as _r18w_exc:
                        log_error(f'R18 CALLBACK REMOTE WITNESS ERROR update={update_id}: {_r18w_exc}')
                if not DELTA_TASK_POOL.submit_unique(f'callback-witness:{update_id}', _r18_callback_witness):
                    try:
                        DELAYED_SCHEDULER.schedule(f'callback-witness:{update_id}', 0.20, _r18_callback_witness)
                    except Exception:
                        log_error(f'R48 callback witness deferred queue unavailable update={update_id}')
            else:
                _r25_witness_started = time.monotonic()
                try: log_info(f'BTNTRACE update={update_id} chat={update_chat_id} action={_r25_adm_action} stage=REMOTE_WITNESS_START')
                except Exception: pass
                _r25_witness_ok = _r13_witness_fn(update_id, payload, update_chat_id, update_type)
                try: log_info(f'BTNTRACE update={update_id} chat={update_chat_id} action={_r25_adm_action} stage=REMOTE_WITNESS_DONE elapsed={time.monotonic()-_r25_witness_started:.3f}s detail={int(bool(_r25_witness_ok))}')
                except Exception: pass
                if not _r25_witness_ok:
                    log_error(f'R13 REMOTE EVENT WITNESS FAILED update={update_id}')
                    return ('REMOTE DURABLE WITNESS FAILED', 503)
        _protect_pending_ui_timers_on_receipt(payload)
        if durable_update_processed(update_id):
            _v260_webhook_inbox_mark(update_id, 'done')
            with _MEGA_TASK_LOCK:
                _mega_task_counters['skipped_done'] += 1
            return ('OK', 200)
        durable_cloud, durable_reason = durable_task_required(payload)
        durable_expected = _durable_expected_effects(payload) if durable_cloud else {}
        if durable_cloud:
            _v260_webhook_inbox_mark(update_id, 'external_pending')
            cloud_state = mega_task_known_state(update_id)
            if cloud_state == 'done':
                _v260_webhook_inbox_mark(update_id, 'done')
                with _MEGA_TASK_LOCK:
                    _mega_task_counters['skipped_done'] += 1
                return ('OK', 200)
            if cloud_state == 'running':
                schedule_mega_task_recovery(0.2)
                return ('TASK RUNNING', 503)
            if cloud_state == 'failed':
                _v260_webhook_inbox_mark(update_id, 'external_failed_review')
                return ('TASK NEEDS REVIEW', 200)
            if cloud_state != 'pending':
                task_payload = _build_mega_task_payload(update_id, payload, update_chat_id, update_type, durable_reason)
                durable_expected = _durable_expected_from_task_or_payload(task_payload, payload)
                if not _mega_task_upload_new_pending(update_id, task_payload):
                    return ('TASK BACKUP UNAVAILABLE', 503)
        claim_state, ticket = UPDATE_DISPATCHER.claim(update_id, update_chat_id, update_type)
        if claim_state == 'done':
            return ('OK', 200)
        update_enqueued_at = time.time()
        if claim_state == 'new':

            def _process_update():
                started = time.time()
                wait = started - update_enqueued_at
                UPDATE_DISPATCHER.mark_started(update_id)
                try:
                    _r25_worker_action = ''
                    if update_type == 'callback_query': _r25_worker_action = str((payload.get('callback_query') or {}).get('data') or '')
                    elif update_type in {'message','edited_message'}: _r25_worker_action = str(((payload.get(update_type) or payload.get('message') or {}).get('text') or update_type))
                    r25_trace_begin(update_id, update_chat_id, update_type, _r25_worker_action)
                    r25_trace_stage('GENERAL_HANDLER_ENTER')
                except Exception: pass
                _v260_webhook_inbox_mark(update_id, 'external_running' if durable_cloud else 'running')
                if update_type == 'callback_query':
                    try:
                        UI_CLEANUP_TASK_POOL.submit(f'journal-start:{update_id}', _r19_update_journal_start, update_id, update_chat_id, update_type, wait, durable_cloud)
                    except Exception:
                        pass
                else:
                    _r19_update_journal_start(update_id, update_chat_id, update_type, wait, durable_cloud)
                success = False
                error_text = ''
                durable_started = False
                try:
                    if durable_cloud:
                        durable_started = mega_task_begin(update_id, allow_existing_running=False)
                        if not durable_started:
                            raise RuntimeError('MEGA durable task could not enter running state')
                    try: r25_trace_stage('EXECUTE_TELEGRAM_PAYLOAD_START')
                    except Exception: pass
                    execution_ctx = _execute_telegram_payload(payload, update_id, update_chat_id, update_type)
                    try: r25_trace_stage('EXECUTE_TELEGRAM_PAYLOAD_DONE')
                    except Exception: pass
                    success = True
                    _v260_webhook_inbox_mark_async(update_id, 'done')
                    _r13_commit_fn = globals().get('split_event_committed_v268')
                    if callable(_r13_commit_fn): _r13_commit_fn(update_id, update_chat_id, update_type, True, '')
                    if durable_cloud:
                        durable_expected_after = _durable_expected_after_execution(durable_expected, execution_ctx, payload)
                        queued_finalize = enqueue_durable_finalize_background(update_id, update_chat_id, update_type, payload, durable_expected_after)
                        if not queued_finalize:
                            finalized = finalize_durable_task_after_business(update_id, update_chat_id, update_type, payload=payload, expected_effects=durable_expected_after)
                            if not finalized:
                                schedule_durable_task_finalize_retry(update_id, update_chat_id, update_type, 1.0, payload=payload, expected_effects=durable_expected_after)
                                log_error(f'MEGA TASK FINALIZE DEFERRED update={update_id}; durable effects still pending')
                except Exception as exc:
                    error_text = str(exc)
                    _failed_inbox_v260 = _v260_webhook_inbox_mark(update_id, 'external_failed_review' if durable_cloud else 'failed', error_text)
                    _r13_commit_fn = globals().get('split_event_committed_v268')
                    if callable(_r13_commit_fn): _r13_commit_fn(update_id, update_chat_id, update_type, False, error_text)
                    if not durable_cloud:
                        _v260_schedule_webhook_inbox_retry(_failed_inbox_v260 or update_id)
                    if durable_cloud and durable_started:
                        mega_task_finish(update_id, False, error_text)
                    log_error(f'WEBHOOK PROCESS FAILED update={update_id} chat={update_chat_id}: {exc}')
                    raise
                finally:
                    try: r25_trace_stage('HANDLER_DONE', time.time()-started, str(error_text or '')[:160])
                    except Exception: pass
                    UPDATE_DISPATCHER.finish(update_id, success, error_text)
                    try: r25_trace_end()
                    except Exception: pass
                    # R19: release the callback/content worker immediately. Cleanup is
                    # serialized on a separate pool and can never keep a UI key active.
                    _r19_schedule_post_update_cleanup(update_id, update_chat_id, update_type, wait, started, success, durable_cloud)
            selector = globals().get('v163_webhook_select_lane')
            if callable(selector):
                selected_pool, selected_key = selector(payload, update_type, update_key)
            else:
                selected_pool = UI_TASK_POOL if update_type == 'callback_query' else WEBHOOK_TASK_POOL
                selected_key = f'ui:{update_key}' if update_type == 'callback_query' else update_key
            if not selected_pool.submit(selected_key, _process_update):
                log_error(f'{selected_pool.name.upper()} QUEUE FULL: chat={update_chat_id}')
                UPDATE_DISPATCHER.release_failed_enqueue(update_id, f'{selected_pool.name}_queue_full')
                return ('BUSY', 503)
            UPDATE_DISPATCHER.mark_enqueued(update_id, selected_pool.name, selected_key)
            # v260: every non-cloud update is first committed to the local SQLite inbox.
            # Once accepted into its keyed worker queue Telegram can be acknowledged at once:
            # a restart will replay the local inbox, while source/forward operation keys make
            # that replay exact-once.  Cloud-durable updates retain their external witness path.
            if not durable_cloud:
                UPDATE_DISPATCHER.mark_http_acked(update_id)
                return ('OK', 200)
        if claim_state == 'pending' and _v260_webhook_inbox_state(update_id) in {'queued','running','done'} and not durable_cloud:
            UPDATE_DISPATCHER.mark_http_acked(update_id)
            return ('OK', 200)
        state, dispatch_error = UPDATE_DISPATCHER.wait_result(ticket, WEBHOOK_ACK_WAIT_SECONDS)
        if state == 'done':
            UPDATE_DISPATCHER.mark_http_acked(update_id)
            return ('OK', 200)
        if state == 'failed':
            return ('RETRY', 503)
        return ('PENDING', 503)
    except Exception as e:
        log_error(f'WEBHOOK: enqueue/update dispatcher error: {e}')
        return ('ERROR', 500)

import urllib.parse as _r53_urlparse
_R53_WEBHOOK_WATCHDOG_STARTED = False
_R53_WEBHOOK_WATCHDOG_LOCK = threading.RLock()
_R53_WEBHOOK_WATCHDOG_LAST = ''


def _r53_expected_webhook_url() -> str:
    return str(WEBHOOK_URL or '').rstrip('/') + str(WEBHOOK_ROUTE_PATH or '')


def _r53_normalize_url(url: str) -> str:
    return str(url or '').strip().rstrip('/')


def _r53_safe_webhook_url(url: str) -> str:
    """Log a webhook endpoint without leaking its secret path."""
    try:
        u = _r53_urlparse.urlsplit(str(url or ''))
        if not u.scheme or not u.netloc:
            return '<empty>' if not url else '<invalid-url>'
        return f'{u.scheme}://{u.netloc}/tg/<redacted>'
    except Exception:
        return '<invalid-url>'


def _r53_webhook_info_snapshot() -> dict:
    info = bot.get_webhook_info()
    actual = str(getattr(info, 'url', '') or '')
    return {
        'url': actual,
        'safe_url': _r53_safe_webhook_url(actual),
        'pending': int(getattr(info, 'pending_update_count', 0) or 0),
        'ip': str(getattr(info, 'ip_address', '') or '')[:80],
        'last_error_date': int(getattr(info, 'last_error_date', 0) or 0),
        'last_error_message': str(getattr(info, 'last_error_message', '') or '')[:500],
        'last_sync_error_date': int(getattr(info, 'last_synchronization_error_date', 0) or 0),
        'max_connections': int(getattr(info, 'max_connections', 0) or 0),
        'allowed_updates': list(getattr(info, 'allowed_updates', None) or []),
    }


def _r53_log_webhook_info(reason: str, snap: dict, expected: str) -> None:
    try:
        log_info(
            'R53 WEBHOOK INFO '
            f'reason={reason} expected={_r53_safe_webhook_url(expected)} actual={snap.get("safe_url")} '
            f'match={int(_r53_normalize_url(snap.get("url")) == _r53_normalize_url(expected))} '
            f'pending={snap.get("pending", 0)} ip={snap.get("ip") or "-"} '
            f'max_conn={snap.get("max_connections", 0)} last_error_date={snap.get("last_error_date", 0)} '
            f'last_error={str(snap.get("last_error_message") or "-")[:300]}'
        )
        r52_diag(
            'WEBHOOK_INFO', reason=reason,
            expected=_r53_safe_webhook_url(expected), actual=snap.get('safe_url'),
            match=int(_r53_normalize_url(snap.get('url')) == _r53_normalize_url(expected)),
            pending=snap.get('pending', 0), ip=snap.get('ip'), max_connections=snap.get('max_connections', 0),
            last_error_date=snap.get('last_error_date', 0), last_error_message=snap.get('last_error_message', ''),
            allowed_updates=snap.get('allowed_updates', [])
        )
    except Exception:
        pass


def _r53_install_webhook_transport(reason: str='startup'):
    """Install and verify the one Telegram webhook owned by this FAST service."""
    global WEBHOOK_HEADER_SECRET_ENABLED
    expected = _r53_expected_webhook_url()
    if not WEBHOOK_URL or not expected:
        raise RuntimeError('WEBHOOK_URL / Render public hostname is not available')
    try:
        webhook_connections = max(1, min(20, int(os.getenv('WEBHOOK_MAX_CONNECTIONS', '8') or '8')))
    except Exception:
        webhook_connections = 8
    kwargs = dict(
        url=expected,
        max_connections=webhook_connections,
        allowed_updates=['message', 'edited_message', 'callback_query', 'channel_post', 'edited_channel_post', 'deleted_business_messages'],
    )

    def _set_once():
        global WEBHOOK_HEADER_SECRET_ENABLED
        try:
            result = bot.set_webhook(secret_token=WEBHOOK_HEADER_SECRET, **kwargs)
            WEBHOOK_HEADER_SECRET_ENABLED = True
            return result
        except TypeError:
            result = bot.set_webhook(**kwargs)
            WEBHOOK_HEADER_SECRET_ENABLED = False
            return result

    force_reset = str(os.getenv('WEBHOOK_FORCE_RESET', '0') or '0').strip().casefold() in {'1', 'true', 'yes', 'on'}
    if force_reset:
        bot.remove_webhook()
        time.sleep(0.35)
    _set_once()
    time.sleep(0.15)
    snap = _r53_webhook_info_snapshot()
    _r53_log_webhook_info(reason + ':verify1', snap, expected)
    if _r53_normalize_url(snap.get('url')) != _r53_normalize_url(expected):
        log_error(
            'R53 WEBHOOK URL MISMATCH: Telegram points elsewhere; repairing. '
            f'expected={_r53_safe_webhook_url(expected)} actual={snap.get("safe_url")}'
        )
        bot.remove_webhook()
        time.sleep(0.35)
        _set_once()
        time.sleep(0.2)
        snap = _r53_webhook_info_snapshot()
        _r53_log_webhook_info(reason + ':verify2', snap, expected)
        if _r53_normalize_url(snap.get('url')) != _r53_normalize_url(expected):
            raise RuntimeError(
                'Telegram webhook verification failed: expected current FAST Render URL, Telegram reports another URL'
            )
    log_info(
        f'Webhook установлен и проверен: {_r53_safe_webhook_url(expected)} '
        f'(max_connections={webhook_connections}; force_reset={force_reset}; secret_header={WEBHOOK_HEADER_SECRET_ENABLED})'
    )
    return True


def _v177_legacy_0269_set_webhook():
    return _r53_install_webhook_transport('startup')


def _r53_webhook_watchdog_loop():
    global _R53_WEBHOOK_WATCHDOG_LAST
    interval = max(30.0, min(300.0, float(os.getenv('WEBHOOK_WATCHDOG_SEC', '60') or '60')))
    while not runtime_is_shutting_down():
        time.sleep(interval)
        if not runtime_is_ready():
            continue
        expected = _r53_expected_webhook_url()
        try:
            snap = _r53_webhook_info_snapshot()
            mismatch = _r53_normalize_url(snap.get('url')) != _r53_normalize_url(expected)
            fingerprint = '|'.join([
                str(snap.get('safe_url') or ''), str(snap.get('pending') or 0),
                str(snap.get('last_error_date') or 0), str(snap.get('last_error_message') or '')[:180]
            ])
            if mismatch:
                log_error(
                    'R53 WEBHOOK WATCHDOG mismatch detected; self-healing. '
                    f'expected={_r53_safe_webhook_url(expected)} actual={snap.get("safe_url")}'
                )
                _r53_log_webhook_info('watchdog:mismatch', snap, expected)
                _r53_install_webhook_transport('watchdog-repair')
                _R53_WEBHOOK_WATCHDOG_LAST = ''
            elif fingerprint != _R53_WEBHOOK_WATCHDOG_LAST and (
                int(snap.get('pending') or 0) > 0 or int(snap.get('last_error_date') or 0) > 0
            ):
                _r53_log_webhook_info('watchdog:notice', snap, expected)
                _R53_WEBHOOK_WATCHDOG_LAST = fingerprint
        except Exception as exc:
            try:
                log_error(f'R53 WEBHOOK WATCHDOG error: {type(exc).__name__}: {str(exc)[:500]}')
                r52_diag('WEBHOOK_WATCHDOG_ERROR', error=f'{type(exc).__name__}:{str(exc)[:800]}')
            except Exception:
                pass


def _r53_start_webhook_watchdog_once() -> bool:
    global _R53_WEBHOOK_WATCHDOG_STARTED
    with _R53_WEBHOOK_WATCHDOG_LOCK:
        if _R53_WEBHOOK_WATCHDOG_STARTED:
            return True
        _R53_WEBHOOK_WATCHDOG_STARTED = True
        threading.Thread(target=_r53_webhook_watchdog_loop, name='r53-webhook-watchdog', daemon=True).start()
    return True


def _r54_replay_preboot_webhooks() -> dict:
    """Replay Telegram updates captured by start_front while MEGA restore/import ran.

    The preboot gateway deliberately returned HTTP 503 even after fsyncing the raw
    update, so Telegram may redeliver it as well.  The canonical webhook inbox and
    UPDATE_DISPATCHER dedupe by update_id, making local replay + Telegram retry safe.
    """
    raw_path = str(os.getenv('PREBOOT_WEBHOOK_SPOOL_FILE', '') or '').strip()
    if not raw_path:
        return {'ok': True, 'found': 0, 'replayed': 0, 'remaining': 0}
    path = Path(raw_path)
    if not path.exists():
        return {'ok': True, 'found': 0, 'replayed': 0, 'remaining': 0}
    try:
        lines = path.read_text(encoding='utf-8').splitlines()
    except Exception as exc:
        log_error(f'R54 PREBOOT REPLAY read failed: {type(exc).__name__}: {str(exc)[:300]}')
        return {'ok': False, 'found': 0, 'replayed': 0, 'remaining': -1}
    replayed = 0
    duplicates = 0
    remaining = []
    bad = 0
    for line in lines:
        try:
            row = json.loads(line)
            payload = row.get('payload') if isinstance(row, dict) else None
            if not isinstance(payload, dict) or payload.get('update_id') is None:
                bad += 1
                continue
            update_id = int(payload.get('update_id'))
            # If Telegram already redelivered and completed this update while replay
            # was waiting in the queue, discard the spool copy without executing it.
            try:
                if durable_update_processed(update_id) or _v260_webhook_inbox_state(update_id) == 'done':
                    duplicates += 1
                    continue
            except Exception:
                pass
            headers = {}
            if WEBHOOK_HEADER_SECRET_ENABLED:
                headers['X-Telegram-Bot-Api-Secret-Token'] = WEBHOOK_HEADER_SECRET
            with app.test_request_context(WEBHOOK_ROUTE_PATH, method='POST', json=payload, headers=headers):
                result = telegram_webhook()
            status = 200
            if isinstance(result, tuple) and len(result) >= 2:
                try: status = int(result[1])
                except Exception: status = 500
            elif hasattr(result, 'status_code'):
                try: status = int(result.status_code)
                except Exception: status = 500
            if 200 <= status < 300:
                replayed += 1
                log_info(f'R54 PREBOOT REPLAY update={update_id} status={status} accepted=1')
            else:
                remaining.append(line)
                log_error(f'R54 PREBOOT REPLAY update={update_id} status={status} accepted=0')
        except Exception as exc:
            remaining.append(line)
            log_error(f'R54 PREBOOT REPLAY row failed: {type(exc).__name__}: {str(exc)[:300]}')
    tmp = path.with_suffix(path.suffix + '.tmp')
    try:
        if remaining:
            tmp.write_text('\n'.join(remaining) + '\n', encoding='utf-8')
            os.replace(tmp, path)
        else:
            path.unlink(missing_ok=True)
            tmp.unlink(missing_ok=True)
    except Exception as exc:
        log_error(f'R54 PREBOOT REPLAY persist failed: {type(exc).__name__}: {str(exc)[:300]}')
    report = {'ok': not remaining, 'found': len(lines), 'replayed': replayed, 'duplicates': duplicates, 'bad': bad, 'remaining': len(remaining)}
    log_info('R54 PREBOOT REPLAY DONE ' + json.dumps(report, ensure_ascii=False, separators=(',', ':')))
    try: r52_diag('PREBOOT_REPLAY_DONE', **report)
    except Exception: pass
    if remaining and not runtime_is_shutting_down():
        try:
            DELAYED_SCHEDULER.schedule('r54-preboot-replay-retry', 2.0, lambda: GENERAL_TASK_POOL.submit_unique('r54-preboot-replay', _r54_replay_preboot_webhooks))
        except Exception:
            pass
    return report


def _r54_schedule_preboot_replay() -> bool:
    raw_path = str(os.getenv('PREBOOT_WEBHOOK_SPOOL_FILE', '') or '').strip()
    if not raw_path or not Path(raw_path).exists():
        return False
    try:
        return bool(GENERAL_TASK_POOL.submit_unique('r54-preboot-replay', _r54_replay_preboot_webhooks))
    except Exception as exc:
        log_error(f'R54 PREBOOT REPLAY schedule failed: {exc}')
        return False

try:
    _v177_legacy_0269_set_webhook.__name__ = 'set_webhook'
except Exception:
    pass

def _start_web_server_bounded_r49():
    """Production HTTP server with a bounded worker pool; never thread-per-request."""
    try:
        threads = max(2, min(16, int(os.getenv('WAITRESS_THREADS', '6') or '6')))
    except Exception:
        threads = 6
    def _serve():
        from waitress import serve
        serve(app, host='0.0.0.0', port=int(PORT), threads=threads, channel_timeout=30, cleanup_interval=10)
    thread = threading.Thread(target=_serve, name='web-server-1', daemon=True)
    thread.start()
    try: runtime_event('bounded_http_server_r49', f'waitress_threads={threads}')
    except Exception: pass
    return thread
_V211_WEB_BIND_LOCK = threading.RLock()
_V211_WEB_THREAD = None
try:
    V211_BOOT_BIND_FAILSAFE_SECONDS = max(15.0, min(60.0, float(os.getenv('BOOT_BIND_FAILSAFE_SECONDS', '30') or '30')))
except Exception:
    V211_BOOT_BIND_FAILSAFE_SECONDS = 30.0
try:
    V211_DEPLOY_HANDOFF_GRACE_SECONDS = max(2.0, min(12.0, float(os.getenv('DEPLOY_HANDOFF_GRACE_SECONDS', '5') or '5')))
except Exception:
    V211_DEPLOY_HANDOFF_GRACE_SECONDS = 5.0

def _v211_ensure_web_server_started(reason: str='ready-handoff'):
    global _V211_WEB_THREAD
    with _V211_WEB_BIND_LOCK:
        if _V211_WEB_THREAD is not None and _V211_WEB_THREAD.is_alive():
            return _V211_WEB_THREAD
        _V211_WEB_THREAD = _start_web_server_bounded_r49()
    try:
        runtime_event('web_server_bound_v211', f'reason={reason}; ready={int(runtime_is_ready())}')
    except Exception:
        pass
    return _V211_WEB_THREAD

def _v211_boot_bind_failsafe():
    time.sleep(float(V211_BOOT_BIND_FAILSAFE_SECONDS))
    if runtime_is_shutting_down():
        return
    with _V211_WEB_BIND_LOCK:
        alive = bool(_V211_WEB_THREAD is not None and _V211_WEB_THREAD.is_alive())
    if not alive:
        try:
            runtime_event('web_bind_failsafe_v211', f'after={V211_BOOT_BIND_FAILSAFE_SECONDS:g}s', 'WARN')
        except Exception:
            pass
        _v211_ensure_web_server_started('failsafe')
_V211_POST_READY_STARTED = False
_V211_POST_READY_LOCK = threading.RLock()
STARTUP_RELEASE_SUMMARY = (
    '• R57: MEGA, Redis и Telegram backup-channel имеют независимые Render master-switches.\n'
    '• Redis не участвует в Telegram hot-path; включение из меню выполняется фоном.\n'
    '• После READY владелец получает только короткое сообщение; подробности открываются кнопкой.\n'
    '• /restore принимает полный .bin как raw SQLite или gzip snapshot.\n'
    '• SQLite остаётся основным локальным источником состояния FAST.'
)


def _v211_start_post_ready_runtime():
    """Start user-visible/background business schedulers only after true READY."""
    global _V211_POST_READY_STARTED
    if not runtime_is_ready() or runtime_is_shutting_down():
        return False
    with _V211_POST_READY_LOCK:
        if _V211_POST_READY_STARTED:
            return True
        _V211_POST_READY_STARTED = True
    try:
        schedule_expense_ping_recovery(1.5)
    except Exception as e:
        log_error(f'expense ping recovery schedule: {e}')
    try:
        start_keep_alive_thread()
    except Exception as e:
        log_error(f'keepalive start: {e}')
    try:
        _r53_start_webhook_watchdog_once()
    except Exception as e:
        log_error(f'R53 webhook watchdog start: {e}')
    try:
        start_reminder_scheduler()
    except Exception as e:
        log_error(f'reminder scheduler start: {e}')
    try:
        start_safety_schedulers()
    except Exception as e:
        log_error(f'safety schedulers start: {e}')
    try:
        pending = SQLITE.get_meta('restore_control_v240', 'remote_reanchor_pending', {}) or {}
        retry_fn = globals().get('_v240_schedule_pending_restore_reanchor_retry')
        if pending and callable(retry_fn):
            retry_fn(10.0)
    except Exception as e:
        log_error(f'v240 pending restore re-anchor schedule: {e}')
    try:
        st_fn = globals().get('telegram_durable_status_v234')
        sched_fn = globals().get('telegram_schedule_full_snapshot_v234')
        if callable(st_fn) and callable(sched_fn):
            _tgst = st_fn()
            if _tgst.get('configured') and int(_tgst.get('snapshot_parts') or 0) <= 0:
                sched_fn('first_generation', delay=15.0)
    except Exception as e:
        log_error(f'telegram durable initial snapshot schedule: {e}')
    try:
        try:
            _inbox_recovered_v260 = recover_webhook_inbox_v260(100)
            _remote_recover_fn = globals().get('split_recover_remote_events_v268')
            _remote_recovered_v268 = _remote_recover_fn(100) if callable(_remote_recover_fn) else 0
            _fin_recovered_v260 = recover_partial_finance_forwards_v260(200) if callable(globals().get('recover_partial_finance_forwards_v260')) else 0
            runtime_event('v260_local_recovery_started', f'webhook={_inbox_recovered_v260}; remote_event={_remote_recovered_v268}; finance_forward={_fin_recovered_v260}')
        except Exception as _v260_recovery_exc:
            log_error(f'v260 local recovery start: {_v260_recovery_exc}')
        runtime_event('post_ready_runtime_started_v211', 'expense/keepalive/reminder/safety/telegram-durable/v260-local-inbox')
    except Exception:
        pass
    return True

def _r57_restore_source_info() -> tuple[str, dict]:
    trace = {}
    try:
        import json as _r57_json
        raw = str(os.getenv('R49_RESTORE_TRACE_JSON', '') or '').strip()
        if raw:
            parsed = _r57_json.loads(raw)
            if isinstance(parsed, dict):
                trace = parsed
    except Exception:
        trace = {}
    source = str(trace.get('base_source') or '').strip().upper()
    labels = {
        'MEGA': 'MEGA',
        'LOCAL_SQLITE': 'локальная SQLite',
        'LOCAL_SQLITE_NEWER_OR_MEGA_UNAVAILABLE': 'локальная SQLite',
        'EMPTY_INIT_MEGA_DISABLED': 'новая SQLite · MEGA отключена',
        'EMPTY_INIT': 'новая SQLite',
        'MEGA_RESTORE_FAILED': 'MEGA не восстановлена',
    }
    label = labels.get(source) or str(_RUNTIME_STATE.get('restore_detail') or 'локальное состояние')
    return label[:180], trace

def _r57_startup_keyboard(details: bool = False):
    kb = types.InlineKeyboardMarkup()
    if details:
        kb.row(IB('↩️ Коротко', callback_data='r57:startup:compact'))
    else:
        kb.row(IB('ℹ️ Подробнее', callback_data='r57:startup:details'))
    return kb

def _r57_startup_compact_text() -> str:
    source, _trace = _r57_restore_source_info()
    return f"✅ Бот запущен · R65 · {VERSION}\nВосстановление: {source}"

def _r57_startup_details_text() -> str:
    source, trace = _r57_restore_source_info()
    try:
        redis_state = globals().get('redis_runtime_state', lambda: {})() or {}
    except Exception:
        redis_state = {}
    mega_enabled = str(os.getenv('MEGA_ENABLED', '1') or '1').strip().casefold() not in {'0','false','no','off'}
    tg_backup_enabled = str(os.getenv('TELEGRAM_BACKUP_ENABLED', '1') or '1').strip().casefold() not in {'0','false','no','off'}
    try:
        task_stats = mega_task_registry_stats() or {}
    except Exception:
        task_stats = {}
    details = [
        f"🤖 R65 · {VERSION}",
        f"Восстановление: {source}",
        f"Правки: {STARTUP_RELEASE_SUMMARY}",
        f"Старт: {_RUNTIME_STATE.get('started_at') or '—'}",
        f"READY: {_RUNTIME_STATE.get('ready_at') or '—'}",
        f"Boot: {_RUNTIME_STATE.get('boot_duration_seconds') or '—'} с",
        f"MEGA: {'ВКЛ' if mega_enabled else 'ВЫКЛ'}",
        f"Redis: {'ВКЛ' if redis_state.get('enabled') else 'ВЫКЛ'} (Render master: {'ВКЛ' if redis_state.get('master_enabled') else 'ВЫКЛ'})",
        f"Telegram backup: {'ВКЛ' if tg_backup_enabled and bool(str(os.getenv('BACKUP_CHAT_ID','') or '').strip()) else 'ВЫКЛ'}",
        f"Render: {str(os.getenv('RENDER_EXTERNAL_HOSTNAME', '') or os.getenv('RENDER_INSTANCE_ID', '') or '—')[-48:]}",
        f"Commit: {str(os.getenv('RENDER_GIT_COMMIT', '') or '—')[:12]}",
        f"Durable jobs: pending {task_stats.get('pending', 0)}, running {task_stats.get('running', 0)}, failed {task_stats.get('failed', 0)}",
        f"Журнал: {'ВКЛ' if is_journal_registration_enabled() else 'ВЫКЛ'}",
        f"Keep-alive: {'ВКЛ' if globals().get('keepalive_self_enabled', lambda: KEEP_ALIVE_ENABLED)() else 'ВЫКЛ'}",
    ]
    if trace:
        details.append(f"Restore base: {trace.get('base_source') or '—'}")
        if trace.get('final_revision') not in (None, ''):
            details.append(f"Revision: {trace.get('final_revision')}")
        if trace.get('error'):
            details.append(f"Restore error: {str(trace.get('error'))[:240]}")
    if _RUNTIME_STATE.get('restore_detail'):
        details.append(f"Детали: {str(_RUNTIME_STATE.get('restore_detail'))[:420]}")
    return '\n'.join(details)

def _v211_notify_owner_ready_once():
    try:
        if not runtime_is_ready() or not OWNER_ID:
            return False
        with _RUNTIME_LOCK:
            if _RUNTIME_STATE.get('owner_ready_notice_sent'):
                return True
            _RUNTIME_STATE['owner_ready_notice_sent'] = True
        owner_id = int(OWNER_ID)
        bot.send_message(owner_id, _r57_startup_compact_text(), reply_markup=_r57_startup_keyboard(False))
        return True
    except Exception as exc:
        try:
            log_error(f'notify owner READY r57: {exc}')
        except Exception:
            pass
        return False

def _v211_deploy_handoff_catchup(db_restored: bool) -> int:
    """Late cut-over gate: bind near the end of boot, settle briefly, then re-read remote durability.

    During normal deploy the previous healthy instance can continue serving while this new
    process restores MEGA.  The second delta/task pass picks up remote changes that appeared
    during that overlap before this process declares READY.  It deliberately does not assume
    an exact Render SIGTERM/cut-over ordering; business durability remains protected by the
    existing write-before-execute tasks + delta/Data Constitution contracts.
    """
    if str(os.getenv('SPLIT_PREBOOT_AUTHORITATIVE_R20', '') or '').strip().casefold() in {'1','true','yes','on'}:
        # start_front already settled Worker/Redis handoff. Never re-apply legacy
        # Telegram/MEGA deltas over the authoritative split database.
        runtime_event('boot_handoff_r20_split_authority', 'legacy remote delta catch-up skipped')
        return 0
    runtime_set_phase('boot_deploy_handoff', 'порт готов; финальная сверка remote delta/tasks перед READY')
    _v211_ensure_web_server_started('deploy-handoff')
    time.sleep(float(V211_DEPLOY_HANDOFF_GRACE_SECONDS))
    caught = 0
    if db_restored:
        try:
            caught = int(lowram_apply_deltas_after_db_snapshot() or 0)
            runtime_event('boot_handoff_delta_catchup_v211', f'applied={caught}')
        except Exception as exc:
            runtime_event('boot_handoff_delta_catchup_error_v211', str(exc), 'WARN')
    try:
        if mega_tasks_active():
            mega_task_refresh_registry()
            runtime_recover_tasks_blocking(min(10.0, float(BOOT_SYNC_RECOVERY_SECONDS)))
    except Exception as exc:
        runtime_event('boot_handoff_task_refresh_error_v211', str(exc), 'WARN')
    return caught

def main():
    global data
    runtime_install_signal_handlers()
    # v250: Render must see an open port before any remote storage/login/restore.
    # /healthz is available immediately; / and /readyz remain BOOTING/503 until
    # the durability restore and verification have actually completed.
    _v211_ensure_web_server_started('boot-immediate-v250')
    runtime_set_phase('boot_port_bound_v250', 'порт Render открыт; начинаю выбор storage и восстановление')
    threading.Thread(target=_v211_boot_bind_failsafe, name='v211-web-bind-failsafe', daemon=True).start()
    try:
        _boot_profile = storage_profile_bootstrap_v237_1()
    except Exception:
        _boot_profile = storage_profile_v237_1()
    try:
        runtime_event('boot_storage_authority_v238', f"profile={_boot_profile}; source={globals().get('_STORAGE_PROFILE_BOOT_SOURCE_V238', 'unknown')}; mega_root={globals().get('MEGA_BACKUP_DIR', '')}")
    except Exception:
        pass
    _restore_backend = str(globals().get('_STORAGE_PROFILE_RESTORE_BACKEND_V246') or '').strip().casefold()
    if _restore_backend not in {'telegram', 'mega', 'local'}:
        _restore_backend = 'telegram' if _boot_profile == STORAGE_PROFILE_TELEGRAM_V237_1 else 'mega' if _boot_profile == STORAGE_PROFILE_MEGA_V237_1 else 'local'
    _tg_primary = bool(_restore_backend == 'telegram' and telegram_durable_available_v237_1())
    _mega_primary = bool(_restore_backend == 'mega' and MEGA_ENABLED and MEGA_EMAIL and MEGA_PASSWORD)
    _local_primary = not (_tg_primary or _mega_primary)
    _render_selected = bool(_boot_profile == STORAGE_PROFILE_LOCAL_V237_1)
    _backend_name = 'Telegram durable' if _tg_primary else 'MEGA' if _mega_primary else 'Render local'
    _split_preboot_authoritative_r19 = str(os.getenv('SPLIT_PREBOOT_AUTHORITATIVE_R20', '') or '').strip().casefold() in {'1','true','yes','on'}
    _split_preboot_revision_r19 = str(os.getenv('SPLIT_PREBOOT_REVISION_R20', '') or '').strip()
    if _split_preboot_authoritative_r19:
        # R19: start_front has already chosen the freshest Worker/Redis/local SQLite.
        # Disable every legacy boot source for this process so there is exactly one
        # restore authority and no fresh->old rollback during bot.main().
        _tg_primary = False
        _mega_primary = False
        _local_primary = True
        _restore_backend = 'split'
        _backend_name = 'Split Worker/Redis authoritative'
    try:
        runtime_event('boot_restore_backend_v246', f"selected_profile={_boot_profile}; restore_backend={_restore_backend}; evidence={json.dumps(globals().get('_STORAGE_PROFILE_REMOTE_EVIDENCE_V246', {}), ensure_ascii=False, default=str)[:1200]}")
    except Exception:
        pass
    _v246_prev_recovery_authority = bool(globals().get('_V240_RECOVERY_AUTHORITY_ACTIVE', False))
    if _render_selected and (_tg_primary or _mega_primary):
        globals()['_V240_RECOVERY_AUTHORITY_ACTIVE'] = True
    runtime_set_phase('boot_local_load', f'восстанавливаю рабочую SQLite из {_backend_name} / локального диска')
    restored = bool(_split_preboot_authoritative_r19)
    db_restored = bool(_split_preboot_authoritative_r19)
    db_detail = (f'Пер-R43 split authoritative revision={_split_preboot_revision_r19 or "unknown"}' if _split_preboot_authoritative_r19 else '')
    if LOWRAM_ENABLED and (not _split_preboot_authoritative_r19):
        try:
            if _tg_primary:
                if storage_mode_feature_enabled_v240('telegram_durable', 'boot_restore', recovery=_render_selected):
                    db_restored, db_detail = telegram_restore_sqlite_snapshot_v234()
                else:
                    db_restored, db_detail = (False, 'Telegram boot restore disabled by mode feature')
            elif _mega_primary:
                if storage_mode_feature_enabled_v240('mega', 'boot_restore', recovery=_render_selected):
                    db_restored, db_detail = mega_restore_sqlite_snapshot_from_cloud()
                else:
                    db_restored, db_detail = (False, 'MEGA boot restore disabled by mode feature')
            else:
                db_restored, db_detail = (False, 'No remote restore backend selected')

            # v246 Render-only recovery: evidence chooses the best source first, but
            # a remote snapshot can disappear or fail verification between probe and
            # download. If that happens, try the other *complete* remote source before
            # falling back to local state. The running profile still remains Render-only.
            if _render_selected and not db_restored and (_tg_primary or _mega_primary):
                evidence = globals().get('_STORAGE_PROFILE_REMOTE_EVIDENCE_V246', {}) or {}
                alt_backend = 'mega' if _tg_primary else 'telegram'
                alt = evidence.get(alt_backend) if isinstance(evidence, dict) else None
                alt_ok = bool(isinstance(alt, dict) and alt.get('available') and alt.get('full'))
                if alt_backend == 'telegram':
                    alt_ok = bool(alt_ok and telegram_durable_available_v237_1())
                else:
                    alt_ok = bool(alt_ok and MEGA_ENABLED and MEGA_EMAIL and MEGA_PASSWORD)
                if alt_ok:
                    try:
                        if alt_backend == 'telegram' and storage_mode_feature_enabled_v240('telegram_durable', 'boot_restore', recovery=True):
                            alt_restored, alt_detail = telegram_restore_sqlite_snapshot_v234()
                        elif alt_backend == 'mega' and storage_mode_feature_enabled_v240('mega', 'boot_restore', recovery=True):
                            alt_restored, alt_detail = mega_restore_sqlite_snapshot_from_cloud()
                        else:
                            alt_restored, alt_detail = (False, 'alternate recovery feature disabled')
                        runtime_event('boot_restore_fallback_v246', f'from={_restore_backend}; to={alt_backend}; ok={alt_restored}; {alt_detail}')
                        if alt_restored:
                            db_restored, db_detail = True, f'fallback {alt_backend}: {alt_detail}'
                            _restore_backend = alt_backend
                            _tg_primary = alt_backend == 'telegram'
                            _mega_primary = alt_backend == 'mega'
                            _local_primary = False
                            _backend_name = 'Telegram durable' if _tg_primary else 'MEGA'
                    except Exception as alt_exc:
                        runtime_event('boot_restore_fallback_error_v246', f'to={alt_backend}; {alt_exc}', 'WARN')
            runtime_event('boot_sqlite_snapshot', f'backend={_backend_name}; ok={db_restored} {db_detail}')
        except Exception as e:
            runtime_event('boot_sqlite_snapshot_error', f'backend={_backend_name}; {e}', 'WARN')
    data = load_data()
    try:
        storage_profile_apply_boot_hint_v237_1()
    except Exception as exc:
        try:
            runtime_event('storage_profile_apply_v246', str(exc), 'WARN')
        except Exception:
            pass
    if _tg_primary:
        try:
            telegram_durable_bootstrap_v234(True)
            delta_count = telegram_apply_remote_deltas_v234()
            restored = bool(db_restored or delta_count)
            runtime_event('boot_telegram_deltas', f'applied={delta_count}')
        except Exception as e:
            runtime_event('boot_telegram_deltas_error', str(e), 'ERROR')
    elif db_restored and _mega_primary:
        try:
            delta_count = lowram_apply_deltas_after_db_snapshot()
            restored = True
            runtime_event('boot_sqlite_deltas', f'applied={delta_count}')
            try:
                config_guard_bind_recovered_state_v242()
            except Exception as _cfg_bind_exc:
                runtime_event('boot_config_binding_finalize_error_v242', str(_cfg_bind_exc), 'ERROR')
                raise
        except Exception as e:
            restored = False
            runtime_event('boot_sqlite_deltas_error', str(e), 'ERROR')
    runtime_set_phase('boot_remote_restore', f'проверяю snapshot / fallback / delta в {_backend_name}')
    with _RUNTIME_LOCK:
        _RUNTIME_STATE['restore_attempted'] = True
    try:
        if _tg_primary:
            if not db_restored and (not restored):
                _lowram_prepare_loaded_data(data, migrate_existing=True)
                _lowram_flush_all_hot(evict=True)
            with _RUNTIME_LOCK:
                _RUNTIME_STATE['restore_ok'] = bool(not RESTORE_GUARD_ACTIVE)
                suffix = '; running profile remains Render-only' if _render_selected else ''
                _RUNTIME_STATE['restore_detail'] = (f'Telegram SQLite snapshot + deltas ({db_detail})' if db_restored else 'Telegram deltas applied' if restored else 'restore guard active' if RESTORE_GUARD_ACTIVE else 'local state retained; Telegram snapshot not yet available') + suffix
        elif _mega_primary:
            if not db_restored:
                restored = mega_autorestore_if_needed()
                _lowram_prepare_loaded_data(data, migrate_existing=True)
                _lowram_flush_all_hot(evict=True)
            if not (db_restored or restored):
                try:
                    _set_restore_guard('MEGA boot restore did not find a valid canonical snapshot/generation')
                except Exception:
                    pass
            with _RUNTIME_LOCK:
                _RUNTIME_STATE['restore_ok'] = bool(db_restored or restored)
                suffix = '; running profile remains Render-only' if _render_selected else ''
                _RUNTIME_STATE['restore_detail'] = ('MEGA SQLite generation + verified deltas' if db_restored else 'MEGA legacy-global fallback applied' if restored else 'MEGA restore failed: no valid snapshot/generation') + suffix
        else:
            _lowram_prepare_loaded_data(data, migrate_existing=True)
            _lowram_flush_all_hot(evict=True)
            with _RUNTIME_LOCK:
                _RUNTIME_STATE['restore_ok'] = bool(not RESTORE_GUARD_ACTIVE)
                _RUNTIME_STATE['restore_detail'] = (db_detail if _split_preboot_authoritative_r19 else 'Local Render state retained; no remote recovery source available')
    except Exception as e:
        log_error(f'main durable restore: {e}')
        restored = False
        with _RUNTIME_LOCK:
            _RUNTIME_STATE['restore_ok'] = False
            _RUNTIME_STATE['restore_detail'] = str(e)[:500]
        runtime_event('boot_restore_error', str(e), 'ERROR')
    finally:
        globals()['_V240_RECOVERY_AUTHORITY_ACTIVE'] = _v246_prev_recovery_authority
    # R49: start_front is the single restore authority; expose its exact source map
    # to Watcher instead of replacing it with a generic split-authoritative label.
    try:
        _trace_raw = str(os.getenv('R49_RESTORE_TRACE_JSON', '') or '').strip()
        _trace = json.loads(_trace_raw) if _trace_raw else {}
        if isinstance(_trace, dict) and _trace:
            with _RUNTIME_LOCK:
                _RUNTIME_STATE['restore_trace'] = _trace
                _RUNTIME_STATE['restore_attempted'] = True
                if _RUNTIME_STATE.get('restore_ok') is not False:
                    _RUNTIME_STATE['restore_ok'] = bool(_trace.get('final_revision') or _trace.get('base_source') == 'EMPTY_INIT')
                _RUNTIME_STATE['restore_detail'] = (
                    f"R49 base={_trace.get('base_source') or '—'} rev={_trace.get('base_revision') or 0}; "
                    f"events={_trace.get('redis_events_detail') or '—'}; capsule={_trace.get('redis_capsule_detail') or '—'}; "
                    f"HEAVY={int(bool(_trace.get('heavy_contacted')))} MEGA={int(bool(_trace.get('mega_contacted')))}; "
                    f"final={_trace.get('final_revision') or 0}"
                )[:500]
    except Exception as _trace_exc:
        runtime_event('r49_restore_trace_parse_error', str(_trace_exc), 'WARN')
    try:
        purge = globals().get('purge_legacy_mega_root_state_v238')
        if callable(purge):
            purge(True)
    except Exception as exc:
        runtime_event('mega_root_legacy_state_purge_warn_v238', str(exc), 'WARN')
    try:
        cfg_report = config_guard_boot_verify_v234()
        runtime_event('boot_config_guard_v234', json.dumps(cfg_report, ensure_ascii=False, default=str)[:1200], 'INFO' if cfg_report.get('ok') else 'ERROR')
        if not bool(cfg_report.get('ok')):
            with _RUNTIME_LOCK:
                _RUNTIME_STATE['restore_ok'] = False
                _RUNTIME_STATE['restore_detail'] = 'CONFIG GUARD: ' + str(cfg_report.get('reason') or 'configuration verification failed')[:420]
    except Exception as exc:
        with _RUNTIME_LOCK:
            _RUNTIME_STATE['restore_ok'] = False
            _RUNTIME_STATE['restore_detail'] = 'CONFIG GUARD ERROR: ' + str(exc)[:420]
        runtime_event('boot_config_guard_error_v234', str(exc), 'ERROR')
    try:
        protected_ok, protected_detail = constitution_verify_protected_symbols()
        if not protected_ok:
            raise RuntimeError('storage-core redefined: ' + str(protected_detail))
        constitution_report = constitution_boot_verify_after_restore()
        if not bool(constitution_report.get('ok')):
            with _RUNTIME_LOCK:
                _RUNTIME_STATE['restore_ok'] = False
                _RUNTIME_STATE['restore_detail'] = 'DATA CONSTITUTION GUARD: ' + str(constitution_report.get('reason') or 'semantic verification failed')[:420]
        runtime_event('boot_data_constitution', json.dumps({'ok': bool(constitution_report.get('ok')), 'mode': constitution_report.get('mode'), 'reason': constitution_report.get('reason'), 'records': (constitution_report.get('live') or {}).get('total_records')}, ensure_ascii=False), 'INFO' if bool(constitution_report.get('ok')) else 'ERROR')
    except Exception as exc:
        try:
            constitution_set_quarantine(f'BOOT constitution exception: {exc}')
        except Exception:
            pass
        with _RUNTIME_LOCK:
            _RUNTIME_STATE['restore_ok'] = False
            _RUNTIME_STATE['restore_detail'] = 'DATA CONSTITUTION ERROR: ' + str(exc)[:420]
        runtime_event('boot_data_constitution_error', str(exc), 'ERROR')
    runtime_set_phase('boot_watcher_previous', 'читаю предыдущий runtime snapshot')
    try:
        prev_runtime = runtime_load_previous_snapshot()
        prev_reason = runtime_classify_previous(prev_runtime)
        with _RUNTIME_LOCK:
            _RUNTIME_STATE['previous_reason'] = prev_reason
        runtime_event('previous_runtime', prev_reason)
    except Exception as e:
        runtime_event('previous_runtime_error', str(e), 'WARN')
    runtime_set_phase('boot_journal_deferred', 'диагностический журнал прогревается после READY; бизнес-durability уже проверена')
    if not RESTORE_GUARD_ACTIVE:
        migrate_legacy_owner_secrets()
    try:
        gs = data.setdefault('_global_settings', {})
        if not bool(gs.get('journal_default_off_v83_applied', False)):
            gs['bot_journal_enabled'] = False
            for _cid, _store in (data.get('chats', {}) or {}).items():
                if isinstance(_store, dict):
                    _store.setdefault('settings', {})['journal_enabled'] = False
            gs['journal_default_off_v83_applied'] = True
        gs.setdefault('bot_behavior_profile', DEFAULT_BOT_BEHAVIOR_PROFILE)
        if not bool(gs.get('version_mode_v88_migrated', False)):
            if str(gs.get('bot_behavior_profile') or '') == 'v87_current':
                gs['bot_behavior_profile'] = 'v88_current'
            gs['version_mode_v88_migrated'] = True
        if not bool(gs.get('version_mode_v90_migrated', False)):
            if str(gs.get('bot_behavior_profile') or '') == 'v88_current':
                gs['bot_behavior_profile'] = 'v90_current'
            gs['version_mode_v90_migrated'] = True
        if not bool(gs.get('version_mode_v91_migrated', False)):
            if str(gs.get('bot_behavior_profile') or '') == 'v90_current':
                gs['bot_behavior_profile'] = 'v91_current'
            gs['version_mode_v91_migrated'] = True
        if not bool(gs.get('version_mode_v92_migrated', False)):
            if str(gs.get('bot_behavior_profile') or '') == 'v91_current':
                gs['bot_behavior_profile'] = 'v92_current'
            gs['version_mode_v92_migrated'] = True
        if not bool(gs.get('category_names_clean_v88_applied', False)):
            for _cid, _store in (data.get('chats', {}) or {}).items():
                if not isinstance(_store, dict):
                    continue
                _custom_category_list(_store)
                _base_category_items(_store)
            gs['category_names_clean_v88_applied'] = True
    except Exception as e:
        log_error(f'v88 defaults migration: {e}')
    try:
        migrated_v208 = bool(journal_v208_apply_defaults())
        try:
            _v176_apply_runtime_flags()
        except Exception:
            pass
        runtime_event('journal_v208_boot_policy', f'migrated={int(migrated_v208)} full={int(is_journal_registration_enabled())} compact={int(journal_compact_remote_effective_enabled())} interval={journal_compact_interval_seconds()}s')
    except Exception as e:
        runtime_event('journal_v208_boot_policy_error', str(e), 'ERROR')
    journal_start_durable_loop()
    try:
        if 'tenant_v148_bootstrap' in globals():
            tenant_report = tenant_v148_bootstrap()
            runtime_event('tenant_v148_bootstrap', json.dumps(tenant_report, ensure_ascii=False))
    except Exception as e:
        log_error(f'tenant_v148_bootstrap: {e}')
        runtime_event('tenant_v148_bootstrap_error', str(e), 'ERROR')
    try:
        marker_report = audit_window_marker_registry()
        log_info(f'Маркеры окон проверены: {marker_report}')
    except Exception as e:
        log_error(f'audit_window_marker_registry: {e}')
    try:
        DELAYED_SCHEDULER.schedule('usd-rate-refresh', 2.0, _usd_rate_refresh_tick)
    except Exception as e:
        log_error(f'usd rate refresh start: {e}')
    for cid in list((data.get('chats', {}) or {}).keys()):
        try:
            store = get_chat_store(int(cid))
            settings = store.setdefault('settings', {})
            settings.setdefault('quick_balance_enabled', False)
            settings.setdefault('quick_balance_behavior', 'normal')
            settings.setdefault('quick_balance_user_selected', False)
            settings.setdefault('hidden_finance', False)
            settings.setdefault('auto_backup_enabled', True)
            settings.setdefault('auto_backup_to_mega_enabled', False)
            settings.setdefault('journal_enabled', True)
            settings.setdefault('main_article_buttons_enabled', False)
            settings.setdefault('main_financial_value_buttons_enabled', False)
            settings.setdefault('currency_mode', 'ars_usd' if settings.get('usd_display_enabled', False) else 'ars')
            settings.setdefault('remaining_show_ost_label', True)
            settings.setdefault('total_secret_mode', False)
        except Exception:
            pass
    runtime_set_phase('boot_runtime_state', 'восстанавливаю индексы и окна')
    _restore_runtime_state_from_data(data)
    restore_finance_window_runtime_state()
    if not RESTORE_GUARD_ACTIVE:
        save_data(data)
        data['forward_rules'] = load_forward_rules()
        try:
            if 'tenant_v148_enforce_forward_isolation' in globals():
                removed = tenant_v148_enforce_forward_isolation()
                if removed:
                    runtime_event('tenant_cross_links_removed_after_load', f'count={removed}', 'WARN')
        except Exception as e:
            log_error(f'tenant forward isolation after load: {e}')
    else:
        data.setdefault('forward_rules', {})
        log_error('v91 emergency mode: local writes and all automatic backups remain blocked')
    try:
        initialize_delta_baseline(data)
    except Exception as e:
        log_error(f'initialize_delta_baseline: {e}')
    runtime_set_phase('boot_task_registry', 'читаю durable tasks pending/running')
    boot_recovery_remaining = 0
    if mega_tasks_active():
        try:
            task_stats = mega_task_refresh_registry()
            log_info(f"[DURABLE TASKS STARTUP:{task_stats.get('backend', 'mega')}] pending={task_stats.get('pending', 0)} running={task_stats.get('running', 0)} failed={task_stats.get('failed', 0)} done={task_stats.get('done', 0)}")
            runtime_recover_tasks_blocking(BOOT_SYNC_RECOVERY_SECONDS)
            boot_recovery_remaining = len(_runtime_pending_recovery_rows())
        except Exception as e:
            log_error(f'mega_task_refresh/recovery startup: {e}')
            runtime_event('boot_task_recovery_error', str(e), 'ERROR')
            try:
                boot_recovery_remaining = len(_runtime_pending_recovery_rows())
            except Exception:
                boot_recovery_remaining = 1
    with _RUNTIME_LOCK:
        _RUNTIME_STATE['task_recovery_remaining'] = int(boot_recovery_remaining)
    if OWNER_ID:
        try:
            finance_active_chats.add(int(OWNER_ID))
        except Exception:
            pass
    log_info(f'Данные загружены из SQLite ({DB_FILE}). Версия бота: {VERSION}')
    runtime_set_phase('boot_webhook', 'устанавливаю Telegram webhook')
    set_webhook()
    try:
        start_memory_runtime_schedulers()
    except Exception as e:
        log_error(f'memory guard start: {e}')
    if boot_recovery_remaining > 0:
        _v211_ensure_web_server_started('boot-recovery-pending')
        runtime_set_phase('boot_recovery_background', f'осталось {boot_recovery_remaining}; webhook временно 503')
        try:
            RECOVERY_TASK_POOL.submit_unique('boot-task-recovery', runtime_continue_boot_recovery_background)
        except Exception:
            runtime_continue_boot_recovery_background()
    else:
        _v211_deploy_handoff_catchup(bool(db_restored))
        _remaining_after_handoff = len(_runtime_pending_recovery_rows()) if mega_tasks_active() else 0
        with _RUNTIME_LOCK:
            _RUNTIME_STATE['task_recovery_remaining'] = int(_remaining_after_handoff)
        if _remaining_after_handoff:
            runtime_set_phase('boot_recovery_background', f'после handoff осталось {_remaining_after_handoff}; webhook временно 503')
            try:
                RECOVERY_TASK_POOL.submit_unique('boot-task-recovery', runtime_continue_boot_recovery_background)
            except Exception:
                runtime_continue_boot_recovery_background()
        else:
            runtime_mark_ready('SQLite/config + final deploy delta catch-up; настройки и durable tasks проверены')
            try:
                journal_flush_to_mega(True)
            except Exception:
                pass
    try:
        if bool(globals().get('mega_contour_enabled_v234', lambda: False)()):
            if not MAINTENANCE_TASK_POOL.submit('archive-current-bot-source', archive_current_bot_source_to_mega):
                log_error('bot source archive maintenance queue full')
    except Exception as exc:
        log_error(f'bot source archive schedule: {exc}')
    if LOWRAM_ENABLED and (not db_restored) and (not RESTORE_GUARD_ACTIVE) and bool(globals().get('CONFIG_GUARD_BOOT_VERIFIED_V234', False)):

        def _seed_primary_db_snapshot():
            try:
                time.sleep(2.0)
                if bool(globals().get('telegram_durable_primary_v234', lambda: False)()):
                    telegram_upload_sqlite_snapshot_v234(force=True)
                elif bool(globals().get('mega_contour_enabled_v234', lambda: False)()):
                    mega_upload_latest_database_backup(force=True)
            except Exception as exc:
                log_error(f'LOWRAM initial DB snapshot: {exc}')
        try:
            MAINTENANCE_TASK_POOL.submit_unique('lowram-db-seed', _seed_primary_db_snapshot)
        except Exception:
            pass
    try:
        schedule_safe_failed_task_repairs(8.0, 20)
    except Exception as exc:
        log_error(f'safe failed task repair schedule: {exc}')
    if runtime_is_ready():
        _v211_notify_owner_ready_once()
    try:
        _v211_web_thread = _v211_ensure_web_server_started('main-loop')
        while _v211_web_thread.is_alive():
            _v211_web_thread.join(timeout=3600.0)
    finally:
        try:
            runtime_graceful_shutdown('APP_EXIT')
        except Exception as e:
            log_error(f'final graceful shutdown: {e}')

# --- ИСТОЧНИК: 73_state_export_runtime.py ---
import json as _v150_json
import math as _v150_math
import re as _v150_re
import threading as _v150_threading
_SEND_DOCUMENT_TRANSFORM_LOCAL = _v150_threading.local()
import time as _v150_time
from datetime import datetime as _v150_datetime
V150_CHAT_STATUSES = {'active', 'unreachable', 'bot_removed', 'migrated', 'archived'}
V150_CHAT_STATUS_LABELS = {'active': '🟢 active', 'unreachable': '🟠 unreachable', 'bot_removed': '⛔ bot_removed', 'migrated': '➡️ migrated', 'archived': '📦 archived'}
_V150_LOCK = _v150_threading.RLock()
_V150_LAST_ACTIVE_PERSIST = {}
_V150_BASE_REMINDER_MENU_TEXT = _v177_legacy_0128_build_reminder_menu_text
_V150_BASE_REMINDER_MENU_KEYBOARD = _v177_legacy_0130_build_reminder_menu_keyboard
_V150_BASE_CATEGORY_ROWS = _v177_legacy_0174_build_exact_category_stats_xlsx_rows
_V150_BASE_SIMPLE_ROWS = _v177_legacy_0090_xlsx_simple_rows_with_balances
_V150_BASE_COMPACT_ROWS = _v177_legacy_0093_compact_simple_excel_rows_and_annotations
_V150_BASE_ADD_RECORD = globals().get('_finance_add_record_base')
_V150_BASE_ADD_CURRENCY_RECORD = globals().get('_base_add_currency_record')
_V150_BASE_DURABLE_REQUIRED = _v177_legacy_0070_durable_task_required
_V150_BASE_DURABLE_EXPECTED = _v177_legacy_0066_durable_expected_effects
_V150_BASE_DURABLE_REPORT = _v177_legacy_0068_durable_effect_report
_V150_BASE_EXECUTE_PAYLOAD = _v177_legacy_0072_execute_telegram_payload
_V150_BASE_SET_WEBHOOK = _v177_legacy_0269_set_webhook
_V150_BASE_UPDATE_CHAT_MESSAGE = _v177_legacy_0236_update_chat_info_from_message
_V150_BASE_UPDATE_CHAT_OBJECT = _v177_legacy_0039_update_chat_info_from_chat_object
_V150_BASE_MIGRATE_CHAT = _v177_legacy_0156_migrate_chat_id_everywhere
_V150_BASE_TENANT_CHATS_TEXT = _v177_legacy_0258_tenant_chats_text

def _v150_now() -> str:
    try:
        return now_local().isoformat(timespec='seconds')
    except Exception:
        return _v150_datetime.now().astimezone().isoformat(timespec='seconds')

def _v150_float(value, default=0.0) -> float:
    try:
        number = float(value or 0)
        return number if _v150_math.isfinite(number) else float(default)
    except Exception:
        return float(default)

def _v150_command_from_payload(payload: dict) -> tuple[str, int | None, int | None, int | None]:
    if not isinstance(payload, dict):
        return ('', None, None, None)
    raw = payload.get('message') or payload.get('edited_message') or payload.get('channel_post') or payload.get('edited_channel_post')
    if not isinstance(raw, dict):
        return ('', None, None, None)
    text = str(raw.get('text') or raw.get('caption') or '').strip()
    first = text.split(maxsplit=1)[0].lower() if text.startswith('/') else ''
    if '@' in first:
        first = first.split('@', 1)[0]
    try:
        chat_id = int((raw.get('chat') or {}).get('id'))
    except Exception:
        chat_id = None
    try:
        msg_id = int(raw.get('message_id'))
    except Exception:
        msg_id = None
    try:
        user_id = int((raw.get('from') or {}).get('id'))
    except Exception:
        user_id = None
    return (first, chat_id, msg_id, user_id)

def _v150_reminder_chat_lines(cfg: dict) -> list[str]:
    chat_ids = []
    for raw in (cfg or {}).get('chat_ids') or []:
        try:
            cid = int(raw)
        except Exception:
            continue
        if cid not in chat_ids:
            chat_ids.append(cid)
    if not chat_ids:
        return ['💬 Чат: не выбран']
    if len(chat_ids) == 1:
        return [f'💬 Чат: {get_chat_display_name(chat_ids[0])}']
    lines = ['💬 Чаты:']
    for cid in chat_ids:
        lines.append(f'• {get_chat_display_name(cid)}')
    return lines

def _canon_build_reminder_menu_text__001(reminder_id: int) -> str:
    cfg = _reminder_cfg(reminder_id)
    base = _V150_BASE_REMINDER_MENU_TEXT(reminder_id) if callable(_V150_BASE_REMINDER_MENU_TEXT) else ''
    if not isinstance(cfg, dict):
        return base
    lines = str(base or '').splitlines()
    out = []
    inserted = False
    for line in lines:
        if _v150_re.match('^\\s*[✅⬜❌]\\s*2\\.\\s*Чаты\\s*:', str(line), flags=_v150_re.I):
            out.extend(_v150_reminder_chat_lines(cfg))
            inserted = True
            continue
        out.append(line)
    if not inserted:
        insert_at = 2 if len(out) >= 2 else len(out)
        for idx, line in enumerate(out):
            if 'Период:' in line or 'Расписание:' in line or 'Состояние:' in line:
                insert_at = idx
                break
        out[insert_at:insert_at] = _v150_reminder_chat_lines(cfg) + ['']
    return '\n'.join(out)[:3900]

def _canon_build_reminder_menu_keyboard__001(reminder_id: int, day_key: str | None=None, page: int=0, viewer_chat_id: int | None=None):
    kb = _V150_BASE_REMINDER_MENU_KEYBOARD(reminder_id, day_key, page, viewer_chat_id) if callable(_V150_BASE_REMINDER_MENU_KEYBOARD) else types.InlineKeyboardMarkup()
    try:
        filtered = []
        for row in list(getattr(kb, 'keyboard', None) or []):
            clean = []
            for button in row:
                text = str(getattr(button, 'text', '') or '').strip()
                if 'К напоминалкам' not in text and _v150_re.search('(^|\\s)(⬅️|🔙)?\\s*Назад\\s*$', text, flags=_v150_re.I):
                    continue
                clean.append(button)
            if clean:
                filtered.append(clean)
        kb.keyboard = filtered
    except Exception as exc:
        try:
            log_error(f'v150 f191 keyboard cleanup: {exc}')
        except Exception:
            pass
    return kb

def _v150_export_currency(chat_id: int) -> str:
    try:
        return 'usd' if financial_view_is_usd(get_chat_store(int(chat_id))) else 'ars'
    except Exception:
        return 'ars'

def _v150_export_reserve(chat_id: int) -> float:
    try:
        return float(gomonk_total(int(chat_id), _v150_export_currency(chat_id)) or 0)
    except Exception:
        return 0.0

def _v150_usd_rate() -> float:
    try:
        row = usd_rate_cached(force=False) or {}
        return max(0.0, _v150_float(row.get('rate') or row.get('venta') or row.get('sell')))
    except Exception:
        return 0.0

def _v150_food_per_person(products_total: float) -> float:
    rate = _v150_usd_rate()
    return max(0.0, _v150_float(products_total)) / 5.0 / rate if rate > 0 else 0.0

def _v150_is_products_category(name: str) -> bool:
    clean = _v150_re.sub('\\s+', ' ', str(name or '').strip().casefold())
    return clean in {'продукты', 'еда', 'продукт', 'food', 'products'}

def _v150_product_total_from_records(chat_id: int, records) -> float:
    store = get_chat_store(int(chat_id))
    total = 0.0
    for item in records or []:
        rec = item[1] if isinstance(item, tuple) and len(item) >= 2 else item
        if not isinstance(rec, dict):
            continue
        amount = financial_view_amount(store, rec)
        if amount >= 0:
            continue
        note = financial_view_note(store, rec)
        try:
            category = resolve_expense_category(note, store)
        except Exception:
            category = ''
        if _v150_is_products_category(category):
            total += abs(float(amount))
    return total

def _v150_append_summary_rows(rows: list[list], chat_id: int | None, closing: float, products_total: float, layout: str) -> list[list]:
    out = [list(x or []) for x in rows or []]
    if chat_id is None:
        return out
    reserve = _v150_export_reserve(int(chat_id))
    turnover = float(closing) - min(reserve, max(0.0, float(closing)))
    metric = _v150_food_per_person(products_total)
    if layout == 'compact':
        out.append(['Гомонковые', reserve, ''])
        out.append(['Остаток в обороте', turnover, ''])
        out.append([])
        out.append(['Расход еды на человека в сутки', metric, ''])
    else:
        width = max([len(r) for r in out if r] + [4])
        row_res = ['', 'Гомонковые', reserve] + [''] * max(0, width - 3)
        row_turn = ['', 'Остаток в обороте', turnover] + [''] * max(0, width - 3)
        row_food = ['', 'Расход еды на человека в сутки', metric] + [''] * max(0, width - 3)
        out.extend([row_res[:width], row_turn[:width], [], row_food[:width]])
    return out

def _v150_cell_value(value) -> float:
    if isinstance(value, dict):
        return _v150_float(value.get('value'))
    return _v150_float(value)

def _v177_legacy_0175_build_exact_category_stats_xlsx_rows(target_chat_id: int, start_key: str, start_rid: int, end_key: str, end_rid: int) -> list[list]:
    rows = _V150_BASE_CATEGORY_ROWS(target_chat_id, start_key, start_rid, end_key, end_rid)
    closing = 0.0
    for row in reversed(rows or []):
        if len(row) > 2 and str(row[1] if len(row) > 1 else '').strip().casefold() == 'остаток на руках':
            closing = _v150_cell_value(row[2])
            break
    try:
        records = exact_record_range(get_chat_store(int(target_chat_id)), start_key, start_rid, end_key, end_rid)
        products_total = _v150_product_total_from_records(int(target_chat_id), records)
    except Exception:
        products_total = 0.0
    return _v150_append_summary_rows(rows, int(target_chat_id), closing, products_total, 'wide')
try:
    _v177_legacy_0175_build_exact_category_stats_xlsx_rows.__name__ = 'build_exact_category_stats_xlsx_rows'
except Exception:
    pass

def _v177_legacy_0091_xlsx_simple_rows_with_balances(rows: list[list], opening_balance: float, target_chat_id: int | None=None) -> list[list]:
    base = _V150_BASE_SIMPLE_ROWS(rows, opening_balance, target_chat_id) if _V150_BASE_SIMPLE_ROWS.__code__.co_argcount >= 3 else _V150_BASE_SIMPLE_ROWS(rows, opening_balance)
    closing = 0.0
    for row in reversed(base or []):
        if len(row) > 2 and str(row[1] if len(row) > 1 else '').strip().casefold() == 'остаток на руках':
            closing = _v150_cell_value(row[2])
            break
    products_total = 0.0
    if target_chat_id is not None:
        store = get_chat_store(int(target_chat_id))
        for row in (rows or [])[1:]:
            if len(row) < 4:
                continue
            note = str(row[1] or '')
            expense = _v150_float(row[3])
            if expense <= 0:
                continue
            try:
                category = resolve_expense_category(note, store)
            except Exception:
                category = ''
            if _v150_is_products_category(category):
                products_total += expense
    return _v150_append_summary_rows(base, target_chat_id, closing, products_total, 'wide')
try:
    _v177_legacy_0091_xlsx_simple_rows_with_balances.__name__ = '_xlsx_simple_rows_with_balances'
except Exception:
    pass

def _v177_legacy_0094_compact_simple_excel_rows_and_annotations(raw_rows: list[tuple], opening_balance: float, target_chat_id: int | None=None) -> tuple[list[list], dict[tuple[int, int], str]]:
    if _V150_BASE_COMPACT_ROWS.__code__.co_argcount >= 3:
        base, notes = _V150_BASE_COMPACT_ROWS(raw_rows, opening_balance, target_chat_id)
    else:
        base, notes = _V150_BASE_COMPACT_ROWS(raw_rows, opening_balance)
    closing = 0.0
    for row in reversed(base or []):
        if row and str(row[0] or '').strip().casefold() == 'остаток на руках':
            closing = _v150_cell_value(row[1] if len(row) > 1 else 0)
            break
    products_total = 0.0
    if target_chat_id is not None:
        store = get_chat_store(int(target_chat_id))
        for _date, amount_raw, note in raw_rows or []:
            try:
                amount = parse_csv_amount(amount_raw)
            except Exception:
                amount = _v150_float(amount_raw)
            if amount >= 0:
                continue
            try:
                category = resolve_expense_category(str(note or ''), store)
            except Exception:
                category = ''
            if _v150_is_products_category(category):
                products_total += abs(amount)
    return (_v150_append_summary_rows(base, target_chat_id, closing, products_total, 'compact'), notes)
try:
    _v177_legacy_0094_compact_simple_excel_rows_and_annotations.__name__ = '_compact_simple_excel_rows_and_annotations'
except Exception:
    pass

def _v150_ledger_balance(store: dict, currency: str) -> float:
    currency = 'usd' if str(currency).lower() == 'usd' else 'ars'
    active = str(store.setdefault('settings', {}).get('_active_currency_ledger') or 'ars').lower()
    if active == currency:
        return _v150_float(store.get('balance'))
    return _v150_float(store.get(f'{currency}_balance'))

def _v150_reduce_reserve_entries(chat_id: int, currency: str, consume: float) -> list[dict]:
    entries = [dict(x) for x in gomonk_entries(int(chat_id), currency) or []]
    left = max(0.0, _v150_float(consume))
    for idx in range(len(entries) - 1, -1, -1):
        if left <= 1e-09:
            break
        amount = max(0.0, _v150_float(entries[idx].get('amount')))
        used = min(amount, left)
        entries[idx]['amount'] = amount - used
        left -= used
    return [x for x in entries if _v150_float(x.get('amount')) > 1e-09]

def _v150_rebalance_key(chat_id: int, currency: str, rec: dict) -> str:
    operation_key = str((rec or {}).get('operation_key') or '').strip()
    if operation_key:
        return f'{chat_id}:{currency}:{operation_key}'
    source = int((rec or {}).get('source_msg_id') or 0)
    if source:
        return f'{chat_id}:{currency}:msg:{source}'
    return f"{chat_id}:{currency}:rid:{int((rec or {}).get('id') or 0)}:{str((rec or {}).get('timestamp') or '')}"

def _v150_apply_reserve_cover(chat_id: int, currency: str, rec: dict | None, reason: str='new_finance_operation') -> dict:
    if not isinstance(rec, dict):
        return {}
    currency = 'usd' if str(currency).lower() == 'usd' else 'ars'
    marker_root = rec.setdefault('gomonk_rebalance_v150', {})
    if marker_root.get(currency):
        return marker_root[currency]
    key = _v150_rebalance_key(int(chat_id), currency, rec)
    store = get_chat_store(int(chat_id))
    settings = store.setdefault('settings', {})
    enabled_key = 'usd_gomonk_enabled' if currency == 'usd' else 'gomonk_enabled'
    balance = _v150_ledger_balance(store, currency)
    target = float(gomonk_total(int(chat_id), currency) or 0)
    effective = min(target, max(0.0, balance)) if bool(settings.get(enabled_key, False)) else 0.0
    virtual_used = max(0.0, target - effective) if bool(settings.get(enabled_key, False)) else 0.0
    turnover_after = balance - effective
    result = {'key': key, 'currency': currency, 'at': _v150_now(), 'reason': reason, 'balance': balance, 'reserve_before': target, 'consumed': virtual_used, 'reserve_after': effective, 'turnover_after': turnover_after, 'constant_target_v209': target, 'entries_mutated': False}
    marker_root[currency] = result
    history = settings.setdefault('gomonk_rebalance_history_v150', [])
    history.append({**result, 'record_id': rec.get('id'), 'source_msg_id': rec.get('source_msg_id')})
    del history[:-300]
    intents = data.setdefault('gomonk_rebalance_intents_v150', {})
    if key in intents:
        intents[key].update({'status': 'done', 'done_at': _v150_now(), 'result': result})
    save_data(data, chat_ids=[int(chat_id)])
    try:
        schedule_config_backup_for_chats(int(chat_id), delay=0.5)
    except Exception:
        pass
    try:
        bot_journal('gomonk_constant_cover_v209', int(chat_id), _v150_json.dumps(result, ensure_ascii=False))
    except Exception:
        pass
    return result

def _v150_prepare_intent(chat_id: int, currency: str, source_msg, amount: float, note: str) -> str:
    try:
        source_msg_id = int(getattr(source_msg, 'message_id', 0) or 0)
    except Exception:
        source_msg_id = 0
    if not source_msg_id:
        return ''
    key = f'{int(chat_id)}:{currency}:msg:{source_msg_id}'
    intents = data.setdefault('gomonk_rebalance_intents_v150', {})
    if key not in intents:
        intents[key] = {'status': 'pending', 'chat_id': int(chat_id), 'currency': currency, 'source_msg_id': source_msg_id, 'amount': _v150_float(amount), 'note': str(note or '')[:180], 'created_at': _v150_now()}
        save_data(data, chat_ids=[int(chat_id)])
    return key

def _v150_add_record_compat(chat_id: int, amount: float, note: str, owner: int, source_msg=None, day_key=None, usd_amount=None, usd_note: str='', usd_only: bool=False, source_finance_text: str=''):
    _v150_prepare_intent(int(chat_id), 'ars', source_msg, amount, note)
    if usd_amount is not None:
        _v150_prepare_intent(int(chat_id), 'usd', source_msg, usd_amount, usd_note or note)
    rec = _V150_BASE_ADD_RECORD(chat_id, amount, note, owner, source_msg=source_msg, day_key=day_key, usd_amount=usd_amount, usd_note=usd_note, usd_only=usd_only, source_finance_text=source_finance_text)
    if isinstance(rec, dict):
        _v150_apply_reserve_cover(int(chat_id), 'ars', rec)
        if usd_amount is not None:
            _v150_apply_reserve_cover(int(chat_id), 'usd', rec)
    return rec

def _v150_add_currency_record_compat(chat_id: int, ledger: str, amount: float, note: str, owner: int, source_msg=None, day_key: str | None=None):
    ledger = 'usd' if str(ledger).lower() == 'usd' else 'ars'
    _v150_prepare_intent(int(chat_id), ledger, source_msg, amount, note)
    store = get_chat_store(int(chat_id))
    source_msg_id = int(getattr(source_msg, 'message_id', 0) or 0) if source_msg is not None else 0
    records_key = 'records' if str(store.setdefault('settings', {}).get('_active_currency_ledger') or 'ars') == ledger else f'{ledger}_records'
    if source_msg_id:
        existing = next((r for r in store.get(records_key, []) or [] if isinstance(r, dict) and int(r.get('source_msg_id') or 0) == source_msg_id), None)
        if isinstance(existing, dict):
            _v150_apply_reserve_cover(int(chat_id), ledger, existing, 'duplicate_retry_repair')
            return existing
    before_ids = {id(r) for r in store.get(records_key, []) or [] if isinstance(r, dict)}
    result = _V150_BASE_ADD_CURRENCY_RECORD(chat_id, ledger, amount, note, owner, source_msg=source_msg, day_key=day_key)
    store = get_chat_store(int(chat_id))
    candidates = [r for r in store.get(records_key, []) or [] if isinstance(r, dict) and id(r) not in before_ids]
    rec = candidates[-1] if candidates else result if isinstance(result, dict) else None
    if isinstance(rec, dict):
        _v150_apply_reserve_cover(int(chat_id), ledger, rec)
    return rec

def _v150_repair_pending_rebalances() -> int:
    repaired = 0
    intents = data.setdefault('gomonk_rebalance_intents_v150', {})
    for key, intent in list(intents.items()):
        if not isinstance(intent, dict) or intent.get('status') != 'pending':
            continue
        try:
            chat_id = int(intent.get('chat_id'))
            currency = str(intent.get('currency') or 'ars')
            source_msg_id = int(intent.get('source_msg_id') or 0)
            store = get_chat_store(chat_id)
            active = str(store.setdefault('settings', {}).get('_active_currency_ledger') or 'ars')
            records = store.get('records', []) if active == currency else store.get(f'{currency}_records', [])
            rec = next((r for r in records or [] if isinstance(r, dict) and int(r.get('source_msg_id') or 0) == source_msg_id), None)
            if isinstance(rec, dict):
                _v150_apply_reserve_cover(chat_id, currency, rec, 'startup_pending_repair')
                repaired += 1
        except Exception as exc:
            try:
                log_error(f'v150 rebalance repair {key}: {exc}')
            except Exception:
                pass
    return repaired

def _v150_error_class(err) -> tuple[str, str]:
    text = str(err or '').strip()
    low = text.casefold()
    definitive = ('bot was kicked', 'bot was blocked by the user', 'bot is not a member', 'kicked from the', 'bot was blocked', 'bot removed')
    if any((x in low for x in definitive)):
        return ('bot_removed', 'telegram_confirmed_bot_removed')
    if 'migrate_to_chat_id' in low or 'group chat was upgraded' in low:
        return ('migrated', 'telegram_migration')
    # For a chat already known to the bot, Telegram's explicit
    # `400 Bad Request: chat not found` during a membership/probe request means
    # the bot can no longer access that chat.  The original monolith treated
    # this as removal; keep that behaviour so the chat immediately moves to
    # the "Removed" menu instead of staying orange forever.
    if 'chat not found' in low:
        return ('bot_removed', 'telegram_chat_not_found_confirmed')
    if 'not enough rights' in low or 'have no rights' in low or 'not enough permissions' in low:
        return ('unreachable', 'telegram_missing_rights')
    if 'forbidden' in low:
        return ('unreachable', 'telegram_forbidden_unconfirmed')
    if 'timeout' in low or 'timed out' in low or 'connection' in low or ('temporar' in low) or ('429' in low) or ('too many requests' in low):
        return ('unreachable', 'telegram_temporary_error')
    return ('unreachable', 'telegram_unknown_error')

def _canon_is_bot_removed_error__001(err) -> bool:
    return _v150_error_class(err)[0] == 'bot_removed'

def _v150_lifecycle(chat_id: int) -> dict:
    store = get_chat_store(int(chat_id))
    row = store.get('chat_lifecycle_v150')
    if not isinstance(row, dict):
        settings = store.setdefault('settings', {})
        old_removed = bool(settings.get('bot_removed', False))
        old_reason = str(settings.get('bot_removed_reason') or '')
        status = 'active'
        if old_removed:
            status, _reason_code = _v150_error_class(old_reason)
        _created_at = _v150_now()
        row = {'status': status, 'status_since': _created_at, 'last_seen_at': '', 'last_success_at': '', 'last_error': old_reason, 'consecutive_failures': 0, 'migrated_to': None, 'history': [{'at': _created_at, 'from': 'unknown', 'to': status, 'reason': old_reason[:200] if old_reason else 'chat card discovered during v150 migration', 'source': 'v150_migration', 'migrated_to': None}]}
        store['chat_lifecycle_v150'] = row
    row.setdefault('status', 'active')
    row.setdefault('status_since', _v150_now())
    row.setdefault('last_seen_at', '')
    row.setdefault('last_success_at', '')
    row.setdefault('last_error', '')
    row.setdefault('consecutive_failures', 0)
    row.setdefault('migrated_to', None)
    row.setdefault('history', [])
    return row

def set_chat_status_v150(chat_id: int, status: str, reason: str, *, source: str='runtime', migrated_to: int | None=None, force_history: bool=False, persist: bool=True, schedule_backup: bool=True) -> dict:
    chat_id = int(chat_id)
    status = str(status or 'unreachable').strip().lower()
    if status not in V150_CHAT_STATUSES:
        status = 'unreachable'
    with _V150_LOCK:
        row = _v150_lifecycle(chat_id)
        previous = str(row.get('status') or 'active')
        now = _v150_now()
        if previous == 'archived' and status == 'active' and (str(source or '') != 'command'):
            row['last_seen_at'] = now
            row['last_success_at'] = now
            return row
        changed = previous != status
        if status == 'active' and previous == 'active' and (not force_history):
            # v262: active heartbeat is runtime state, not a Configuration Constitution change.
            # Never put the user's callback/message behind a full save every five minutes.
            row['last_seen_at'] = now
            row['last_success_at'] = now
            row['last_error'] = ''
            row['consecutive_failures'] = 0
            try:
                settings = get_chat_store(chat_id).setdefault('settings', {})
                settings['bot_removed'] = False
                settings.pop('bot_removed_reason', None)
                settings.pop('bot_removed_at', None)
            except Exception:
                pass
            if persist:
                try:
                    fn = globals().get('_v262_schedule_transient_chat_persist')
                    if callable(fn):
                        fn(chat_id)
                except Exception:
                    pass
            return row
        if changed:
            row['status'] = status
            row['status_since'] = now
        if status == 'active':
            row['last_seen_at'] = now
            row['last_success_at'] = now
            row['last_error'] = ''
            row['consecutive_failures'] = 0
        elif status == 'migrated':
            row['migrated_to'] = int(migrated_to) if migrated_to is not None else row.get('migrated_to')
            row['last_error'] = str(reason or '')[:500]
        else:
            row['last_error'] = str(reason or '')[:500]
            row['consecutive_failures'] = int(row.get('consecutive_failures') or 0) + 1
        settings = get_chat_store(chat_id).setdefault('settings', {})
        settings['bot_removed'] = status == 'bot_removed'
        if status == 'bot_removed':
            settings['bot_removed_reason'] = str(reason or '')[:300]
            settings['bot_removed_at'] = now
        else:
            settings.pop('bot_removed_reason', None)
            settings.pop('bot_removed_at', None)
        signature = (previous, status, str(reason or '')[:200], str(source or ''))
        last = (row.get('history') or [])[-1] if row.get('history') else {}
        last_signature = (last.get('from'), last.get('to'), last.get('reason'), last.get('source')) if isinstance(last, dict) else None
        if changed or force_history or signature != last_signature:
            row['history'].append({'at': now, 'from': previous, 'to': status, 'reason': str(reason or '')[:200], 'source': str(source or '')[:80], 'migrated_to': int(migrated_to) if migrated_to is not None else None})
            del row['history'][:-200]
        # R17 terminal-chat fan-out.  The helper is defined by 76_tasks_runtime
        # later in module load, so this remains dependency-safe during boot.
        # It mutates only local canonical state here; the single save below writes
        # chat lifecycle + root task/reminder/forward state atomically to SQLite.
        if status in {'bot_removed', 'migrated', 'archived'}:
            try:
                cleanup_fn = globals().get('r17_suspend_terminal_chat_bindings')
                if callable(cleanup_fn):
                    cleanup_fn(chat_id, reason=str(reason or status), source=str(source or 'lifecycle'), persist=False)
            except Exception as cleanup_exc:
                try:
                    bot_journal('r17_terminal_cleanup_error', chat_id, f'{type(cleanup_exc).__name__}: {str(cleanup_exc)[:240]}', 'ERROR')
                except Exception:
                    pass
        if persist:
            save_data(data, chat_ids=[chat_id])
            if status == 'active':
                _V150_LAST_ACTIVE_PERSIST[chat_id] = _v150_time.monotonic()
        if schedule_backup:
            try:
                schedule_config_backup_for_chats(chat_id, delay=1.0)
            except Exception:
                pass
        try:
            bot_journal('chat_lifecycle', chat_id, f'{previous}->{status}; source={source}; reason={str(reason)[:240]}', 'WARN' if status != 'active' else 'INFO')
        except Exception:
            pass
        return row

def _canon_set_chat_bot_removed__001(chat_id: int, removed: bool=True, reason: str='', *, persist: bool=True, schedule_backup: bool=True) -> bool:
    """Canonical lifecycle bridge used by the deep probe.

    Keep the v197 keyword contract even though the v150 lifecycle layer owns the
    final runtime implementation.  Return a real changed/not-changed boolean so
    callers do not treat the lifecycle dict itself as an unconditional change.
    """
    chat_id = int(chat_id)
    before = str(_v150_lifecycle(chat_id).get('status') or 'active')
    if not removed:
        set_chat_status_v150(chat_id, 'active', reason or 'telegram api success', source='legacy_bridge', persist=persist, schedule_backup=schedule_backup)
    else:
        status, code = _v150_error_class(reason)
        set_chat_status_v150(chat_id, status, reason or code, source=code, persist=persist, schedule_backup=schedule_backup)
    after = str(_v150_lifecycle(chat_id).get('status') or 'active')
    return before != after

def _canon_is_chat_bot_removed__001(chat_id: int) -> bool:
    try:
        return str(_v150_lifecycle(int(chat_id)).get('status')) in {'bot_removed', 'migrated', 'archived'}
    except Exception:
        return False

def _canon_chat_button_title__001(chat_id: int, title: str | None=None) -> str:
    title = str(title or get_chat_display_name(int(chat_id)))
    try:
        status = str(_v150_lifecycle(int(chat_id)).get('status') or 'active')
    except Exception:
        status = 'active'
    icon = {'active': '', 'unreachable': '🟠 ', 'bot_removed': '⛔ ', 'migrated': '➡️ ', 'archived': '📦 '}.get(status, '')
    return icon + title

def _canon_update_chat_info_from_message__001(msg):
    result = _V150_BASE_UPDATE_CHAT_MESSAGE(msg) if callable(_V150_BASE_UPDATE_CHAT_MESSAGE) else None
    try:
        chat_id = int(msg.chat.id)
        set_chat_status_v150(chat_id, 'active', 'message received', source='telegram_update')
    except Exception:
        pass
    return result

def _canon_update_chat_info_from_chat_object__001(chat_obj, *, persist: bool=True, schedule_backup: bool=True) -> bool:
    result = False
    if callable(_V150_BASE_UPDATE_CHAT_OBJECT):
        try:
            result = bool(_V150_BASE_UPDATE_CHAT_OBJECT(chat_obj, persist=persist, schedule_backup=schedule_backup))
        except TypeError:
            result = bool(_V150_BASE_UPDATE_CHAT_OBJECT(chat_obj))
    try:
        set_chat_status_v150(int(chat_obj.id), 'active', 'getChat success', source='telegram_get_chat', persist=persist, schedule_backup=schedule_backup)
    except Exception:
        pass
    return result

def _v150_probe_bot_in_chat_legacy(chat_id: int) -> bool:
    """Legacy lifecycle-only probe kept private.

    v197 introduced the canonical extended probe in 00_core.py with keyword controls
    (deep/persist/schedule_backup).  Do NOT rebind the public probe_bot_in_chat here:
    doing so used to erase that signature and broke the full chat sync.
    """
    chat_id = int(chat_id)
    try:
        obj = _tg_call_retry(bot.get_chat, chat_id, attempts=2, purpose='probe_get_chat')
        update_chat_info_from_chat_object(obj)
        return True
    except Exception as exc:
        status, code = _v150_error_class(exc)
        set_chat_status_v150(chat_id, status, str(exc)[:500], source=code)
        return False

def _canon_migrate_chat_id_everywhere__001(old_chat_id: int, new_chat_id: int, reason: str='telegram supergroup migration') -> bool:
    ok = bool(_V150_BASE_MIGRATE_CHAT(old_chat_id, new_chat_id, reason)) if callable(_V150_BASE_MIGRATE_CHAT) else False
    if ok:
        set_chat_status_v150(int(old_chat_id), 'migrated', reason, source='telegram_migration', migrated_to=int(new_chat_id), force_history=True)
        set_chat_status_v150(int(new_chat_id), 'active', f'migrated from {int(old_chat_id)}', source='telegram_migration', force_history=True)
    return ok

def _v150_status_line(chat_id: int) -> str:
    row = _v150_lifecycle(int(chat_id))
    status = str(row.get('status') or 'active')
    reason = str(row.get('last_error') or '').strip()
    label = V150_CHAT_STATUS_LABELS.get(status, status)
    return f'{label}' + (f' · {reason[:90]}' if reason else '')

def _v177_legacy_0259_tenant_chats_text(tenant_id: str) -> str:
    row = tenant_get(tenant_id) or {}
    lines = [f"💬 ЧАТЫ · {row.get('name')}", '']
    for cid in row.get('chat_ids') or []:
        cid = int(cid)
        marker = '🏠' if cid == int(row.get('root_chat_id') or 0) else '•'
        lines.append(f'{marker} {get_chat_display_name(cid)} · {cid}')
        lines.append(f'   {_v150_status_line(cid)}')
    if len(lines) == 2:
        lines.append('Нет подключённых чатов.')
    return '\n'.join(lines)[:3900]
try:
    _v177_legacy_0259_tenant_chats_text.__name__ = 'tenant_chats_text'
except Exception:
    pass

def _v150_chat_access(user_id: int, chat_id: int) -> bool:
    try:
        tid = tenant_id_for_chat(int(chat_id), create=False)
        if not tid:
            return tenant_is_platform_owner_user(int(user_id))
        return tenant_can_manage(int(user_id), str(tid)) or tenant_is_platform_owner_user(int(user_id))
    except Exception:
        return False

def _v150_status_text(chat_id: int) -> str:
    row = _v150_lifecycle(int(chat_id))
    lines = [f'💬 {get_chat_display_name(int(chat_id))}', f'ID: {int(chat_id)}', f"Статус: {V150_CHAT_STATUS_LABELS.get(str(row.get('status')), str(row.get('status')))}", f"С этого времени: {row.get('status_since') or '—'}", f"Последний успешный контакт: {row.get('last_success_at') or '—'}", f"Последняя ошибка: {row.get('last_error') or '—'}", f"Ошибок подряд: {int(row.get('consecutive_failures') or 0)}"]
    if row.get('migrated_to'):
        lines.append(f"Перенесён в: {row.get('migrated_to')}")
    return '\n'.join(lines)[:3900]

def _v150_history_text(chat_id: int) -> str:
    row = _v150_lifecycle(int(chat_id))
    lines = [f'🧾 ИСТОРИЯ ЧАТА · {get_chat_display_name(int(chat_id))}', '']
    for item in reversed((row.get('history') or [])[-30:]):
        if not isinstance(item, dict):
            continue
        lines.append(f"{item.get('at')} · {item.get('from')} → {item.get('to')}")
        lines.append(f"Причина: {item.get('reason') or '—'} · источник: {item.get('source') or '—'}")
    if len(lines) == 2:
        lines.append('История пока пуста.')
    return '\n'.join(lines)[:3900]

def _v150_target_chat_from_command(msg) -> int:
    parts = str(getattr(msg, 'text', '') or '').split(maxsplit=1)
    if len(parts) > 1:
        try:
            return int(parts[1].strip())
        except Exception:
            pass
    return int(msg.chat.id)

@bot.message_handler(commands=['chat_status'])
def v150_cmd_chat_status(msg):
    target = _v150_target_chat_from_command(msg)
    uid = int(getattr(getattr(msg, 'from_user', None), 'id', 0) or 0)
    if not _v150_chat_access(uid, target):
        bot.reply_to(msg, '⛔ Недостаточно прав для этого чата.')
        return
    bot.reply_to(msg, _v150_status_text(target))

@bot.message_handler(commands=['chat_history'])
def v150_cmd_chat_history(msg):
    target = _v150_target_chat_from_command(msg)
    uid = int(getattr(getattr(msg, 'from_user', None), 'id', 0) or 0)
    if not _v150_chat_access(uid, target):
        bot.reply_to(msg, '⛔ Недостаточно прав для этого чата.')
        return
    bot.reply_to(msg, _v150_history_text(target))

@bot.message_handler(commands=['chat_archive'])
def v150_cmd_chat_archive(msg):
    target = _v150_target_chat_from_command(msg)
    uid = int(getattr(getattr(msg, 'from_user', None), 'id', 0) or 0)
    if not _v150_chat_access(uid, target):
        bot.reply_to(msg, '⛔ Недостаточно прав для этого чата.')
        return
    set_chat_status_v150(target, 'archived', f'manual archive by {uid}', source='command', force_history=True)
    bot.reply_to(msg, '📦 Чат переведён в статус archived. Данные и история сохранены.')

@bot.message_handler(commands=['chat_restore'])
def v150_cmd_chat_restore(msg):
    target = _v150_target_chat_from_command(msg)
    uid = int(getattr(getattr(msg, 'from_user', None), 'id', 0) or 0)
    if not _v150_chat_access(uid, target):
        bot.reply_to(msg, '⛔ Недостаточно прав для этого чата.')
        return
    set_chat_status_v150(target, 'active', f'manual restore by {uid}', source='command', force_history=True)
    try:
        GENERAL_TASK_POOL.submit_unique(f'probe-chat-{target}', probe_bot_in_chat, target)
    except Exception:
        pass
    bot.reply_to(msg, '✅ Карточка чата восстановлена и поставлена на проверку Telegram.')

@bot.message_handler(commands=['command_audit'])
def v150_cmd_command_audit(msg):
    uid = int(getattr(getattr(msg, 'from_user', None), 'id', 0) or 0)
    if not tenant_is_platform_owner_user(uid):
        bot.reply_to(msg, '⛔ Команда доступна только владельцу платформы.')
        return
    bot.reply_to(msg, '✅ Slash-команды v150\n\n• command-декораторов и алиасов: 91; конфликтов между ними: 0;\n• в меню Telegram зарегистрировано 96 допустимых латинских команд и алиасов;\n• обычный catch-all исключает сообщения, начинающиеся с /;\n• изменяющие состояние команды защищены durable receipt;\n• /vyapl_ID обрабатывается отдельным цифровым маршрутом и не конфликтует с /vyapl_history.\n\nПолный аудит находится в COMMAND_AUDIT_v150.txt внутри ZIP.')
_V150_MUTATION_COMMANDS = {'/reset', '/stopforward', '/backup_channel_on', '/backup_channel_off', '/buttons', '/secret_bot', '/mega_backup_now', '/knopki', '/кнопки', '/mask', '/maska', '/маска', '/day5', '/fin_day5', '/sutki', '/ost', '/остаток', '/старт', '/restore_guard_off', '/restore_guard_on', '/off_on_backup_excel', '/space_create', '/tenant_create', '/space_claim', '/tenant_claim', '/space_join', '/tenant_join', '/space_chat_link', '/tenant_chat_link', '/space_user_link', '/tenant_user_link', '/space_role', '/tenant_role', '/space_transfer', '/tenant_transfer', '/space_rename', '/tenant_rename', '/space_unlink', '/tenant_unlink', '/google_connect', '/google_sheet', '/google_drive', '/google_email', '/chat_archive', '/chat_restore'}

def _v150_is_mutation_command(command: str) -> bool:
    cmd = str(command or '').lower()
    if cmd in _V150_MUTATION_COMMANDS or bool(_v150_re.fullmatch('/vyapl(?:_\\d+)?', cmd)):
        return True
    return bool(_v150_re.fullmatch('/(?:владелец|vladelec)(?:1904|-1904|_1904)', cmd, flags=_v150_re.I))

def _v150_is_known_slash_command(text: str) -> bool:
    token = str(text or '').strip().split(maxsplit=1)[0].split('@', 1)[0].casefold()
    if not token.startswith('/'):
        return False
    name = token[1:]
    known = {str(cmd).casefold() for cmd, _desc in _V150_TELEGRAM_COMMANDS} if '_V150_TELEGRAM_COMMANDS' in globals() else set()
    known.update({'старт', 'кнопки', 'маска', 'остаток', 'секрет', 'sekret', 'cekret'})
    return name in known or bool(_v150_re.fullmatch('(?:vyapl_\\d+|izm_[ru]\\d+(?:_u[a-f0-9]{12})?|\\d+)', name, flags=_v150_re.I))

def _canon_durable_task_required__001(payload: dict) -> tuple[bool, str]:
    try:
        _raw_restore = (payload or {}).get('message') or (payload or {}).get('channel_post')
        if isinstance(_raw_restore, dict) and isinstance(_raw_restore.get('document'), dict):
            _restore_cid = int((_raw_restore.get('chat') or {}).get('id'))
            _restore_name = str((_raw_restore.get('document') or {}).get('file_name') or '').lower()
            _restore_active = globals().get('restore_mode')
            if _restore_active is not None and int(_restore_active) == _restore_cid and _restore_name.endswith(('.json', '.ison', '.csv', '.gz')):
                return (False, 'v186:restore_document_control')
            if _restore_name.endswith(('.json', '.ison')):
                try:
                    if is_owner_chat(_restore_cid):
                        return (False, 'v186:owner_backup_document_control')
                except Exception:
                    pass
    except Exception:
        pass
    command, _chat_id, _msg_id, _uid = _v150_command_from_payload(payload)
    if str(command or '').lower() in {'/restore', '/restore_off', '/mega_restore_now'}:
        return (False, 'v239:restore_control_plane')
    if str(command or '').lower().startswith('/izm_'):
        return (False, 'v168:record_edit_open')
    if _v150_is_mutation_command(command):
        try:
            if not mega_tasks_active():
                return (False, 'mega_tasks_inactive')
        except Exception:
            pass
        return (True, 'v150:mutation_command')
    if command and _chat_id is not None:
        try:
            if is_total_secret_mode(int(_chat_id)) and (not _v150_is_known_slash_command(command)):
                return (True, 'v150:total_secret_slash_content')
        except Exception:
            pass
    return _V150_BASE_DURABLE_REQUIRED(payload)

def _v150_receipt_key(payload: dict) -> str:
    command, chat_id, msg_id, user_id = _v150_command_from_payload(payload)
    update_id = (payload or {}).get('update_id')
    return f'{update_id}:{chat_id}:{msg_id}:{user_id}:{command}'

def _canon_durable_expected_effects__001(payload: dict) -> dict:
    out = _V150_BASE_DURABLE_EXPECTED(payload)
    command, chat_id, msg_id, user_id = _v150_command_from_payload(payload)
    if _v150_is_mutation_command(command):
        out['command_receipt_v150'] = {'key': _v150_receipt_key(payload), 'command': command, 'chat_id': chat_id, 'message_id': msg_id, 'user_id': user_id}
    elif command and chat_id is not None:
        try:
            if is_total_secret_mode(int(chat_id)) and (not _v150_is_known_slash_command(command)):
                out['source_secret'] = True
        except Exception:
            pass
    return out

def _v150_has_receipt(key: str) -> bool:
    return any((isinstance(x, dict) and str(x.get('key')) == str(key) for x in data.get('durable_command_receipts_v150') or []))

def _v150_store_receipt(payload: dict):
    command, chat_id, msg_id, user_id = _v150_command_from_payload(payload)
    if not _v150_is_mutation_command(command):
        return
    key = _v150_receipt_key(payload)
    if _v150_has_receipt(key):
        return
    rows = data.setdefault('durable_command_receipts_v150', [])
    rows.append({'key': key, 'command': command, 'chat_id': chat_id, 'message_id': msg_id, 'user_id': user_id, 'update_id': payload.get('update_id'), 'completed_at': _v150_now()})
    del rows[:-800]
    save_data(data, chat_ids=[chat_id] if chat_id is not None else None)

def _v177_legacy_0073_execute_telegram_payload(payload: dict, update_id=None, update_chat_id=None, update_type: str='other'):
    result = _V150_BASE_EXECUTE_PAYLOAD(payload, update_id=update_id, update_chat_id=update_chat_id, update_type=update_type)
    _v150_store_receipt(payload)
    return result
try:
    _v177_legacy_0073_execute_telegram_payload.__name__ = '_execute_telegram_payload'
except Exception:
    pass

def _canon_durable_effect_report__001(payload: dict, expected: dict | None=None) -> dict:
    report = _V150_BASE_DURABLE_REPORT(payload, expected)
    exp = expected if isinstance(expected, dict) else _durable_expected_effects(payload)
    receipt = exp.get('command_receipt_v150') if isinstance(exp, dict) else None
    if isinstance(receipt, dict) and (not _v150_has_receipt(str(receipt.get('key') or ''))):
        report['complete'] = False
        missing = report.setdefault('missing', [])
        tag = f"command_receipt:{receipt.get('command')}:{receipt.get('message_id')}"
        if tag not in missing:
            missing.append(tag)
    return report
_V150_TELEGRAM_COMMANDS = [('additional_owners', 'Команда /additional_owners'), ('articles', 'Статьи расходов'), ('backup_channel_off', 'Команда /backup_channel_off'), ('backup_channel_on', 'Команда /backup_channel_on'), ('balance', 'Текущий баланс'), ('bot_errors', 'Команда /bot_errors'), ('buttons', 'Команда /buttons'), ('chat_archive', 'Архивировать чат'), ('chat_history', 'История статусов чата'), ('chat_restore', 'Восстановить карточку чата'), ('chat_status', 'Статус чата'), ('command_audit', 'Аудит slash-команд'), ('csv', 'Скачать CSV'), ('db', 'Команда /db'), ('delta_status', 'Команда /delta_status'), ('diag', 'Команда /diag'), ('diagnostics', 'Команда /diagnostics'), ('dozvon', 'Команда /dozvon'), ('errors', 'Команда /errors'), ('excel', 'Настройки Excel'), ('google', 'Google пространства'), ('google_connect', 'Команда /google_connect'), ('google_drive', 'Команда /google_drive'), ('google_email', 'Команда /google_email'), ('google_sheet', 'Команда /google_sheet'), ('google_space', 'Команда /google_space'), ('google_tenant', 'Команда /google_tenant'), ('help', 'Справка по командам'), ('journal', 'Команда /journal'), ('json', 'Скачать JSON'), ('log', 'Команда /log'), ('logs', 'Команда /logs'), ('mega_backup_now', 'Команда /mega_backup_now'), ('mega_restore_now', 'Команда /mega_restore_now'), ('mega_status', 'Команда /mega_status'), ('next', 'Команда /next'), ('off_on_backup_excel', 'Команда /off_on_backup_excel'), ('ok', 'Команда /ok'), ('okna', 'Команда /okna'), ('owners', 'Команда /owners'), ('ping', 'Проверка ответа бота'), ('prev', 'Команда /prev'), ('queue_status', 'Команда /queue_status'), ('queues', 'Команда /queues'), ('report', 'Финансовый отчёт'), ('reset', 'Команда /reset'), ('restore', 'Команда /restore'), ('restore_guard', 'Команда /restore_guard'), ('restore_guard_off', 'Команда /restore_guard_off'), ('restore_guard_on', 'Команда /restore_guard_on'), ('restore_off', 'Команда /restore_off'), ('runtime_export', 'Команда /runtime_export'), ('secret_bot', 'Команда /secret_bot'), ('space', 'Текущее пространство'), ('space_chat_link', 'Команда /space_chat_link'), ('space_chats', 'Команда /space_chats'), ('space_claim', 'Команда /space_claim'), ('space_create', 'Команда /space_create'), ('space_join', 'Команда /space_join'), ('space_rename', 'Команда /space_rename'), ('space_role', 'Команда /space_role'), ('space_transfer', 'Команда /space_transfer'), ('space_unlink', 'Команда /space_unlink'), ('space_user_link', 'Команда /space_user_link'), ('space_users', 'Команда /space_users'), ('spaces', 'Список пространств'), ('sqlite', 'Команда /sqlite'), ('start', 'Открыть главное меню'), ('stopforward', 'Команда /stopforward'), ('tabl_lsx', 'Excel за четыре недели'), ('tenant', 'Команда /tenant'), ('tenant_chat_link', 'Команда /tenant_chat_link'), ('tenant_chats', 'Команда /tenant_chats'), ('tenant_claim', 'Команда /tenant_claim'), ('tenant_create', 'Команда /tenant_create'), ('tenant_join', 'Команда /tenant_join'), ('tenant_rename', 'Команда /tenant_rename'), ('tenant_role', 'Команда /tenant_role'), ('tenant_transfer', 'Команда /tenant_transfer'), ('tenant_unlink', 'Команда /tenant_unlink'), ('tenant_user_link', 'Команда /tenant_user_link'), ('tenant_users', 'Команда /tenant_users'), ('vyapl', 'Выполнить напоминание'), ('vyapl_history', 'История выполнения напоминаний'), ('windows', 'Команда /windows'), ('xlsx', 'Скачать Excel'), ('knopki', 'Переключить вид кнопок'), ('mask', 'Маскировка секретного режима'), ('maska', 'Маскировка секретного режима'), ('day5', 'Финансовые сутки с 05:00'), ('fin_day5', 'Финансовые сутки с 05:00'), ('sutki', 'Финансовые сутки с 05:00'), ('ost', 'Переключить подпись остатка'), ('secret', 'Открыть секретные записи'), ('sekret', 'Открыть секретные записи'), ('cekret', 'Открыть секретные записи')]

def _v150_register_commands():
    try:
        commands = [types.BotCommand(name, description[:256]) for name, description in _V150_TELEGRAM_COMMANDS]
        bot.set_my_commands(commands)
        try:
            bot_journal('slash_commands_registered', int(OWNER_ID or 0), f'count={len(commands)}')
        except Exception:
            pass
        return True
    except Exception as exc:
        try:
            log_error(f'v150 set_my_commands: {exc}')
        except Exception:
            pass
        return False

def _v150_migrate_chat_lifecycle() -> int:
    count = 0
    for cid, store in list((data.get('chats') or {}).items()):
        if not isinstance(store, dict):
            continue
        try:
            chat_id = int(cid)
            before = store.get('chat_lifecycle_v150')
            _v150_lifecycle(chat_id)
            if not isinstance(before, dict):
                count += 1
        except Exception:
            continue
    if count:
        save_data(data)
    return count

def _v177_legacy_0270_set_webhook():
    global restore_mode
    try:
        _saved_restore_chat = data.get('_restore_mode_chat_v150')
        restore_mode = int(_saved_restore_chat) if _saved_restore_chat is not None else None
        migrated = _v150_migrate_chat_lifecycle()
        repaired = _v150_repair_pending_rebalances()
        try:
            bot_journal('v150_startup_migration', int(OWNER_ID or 0), f'chat_lifecycle={migrated}; rebalance_repaired={repaired}')
        except Exception:
            pass
    except Exception as exc:
        try:
            log_error(f'v150 startup migration: {exc}')
        except Exception:
            pass
    result = _V150_BASE_SET_WEBHOOK()
    _v150_register_commands()
    return result
try:
    _v177_legacy_0270_set_webhook.__name__ = 'set_webhook'
except Exception:
    pass
import math as _v151_math
import re as _v151_re
import threading as _v151_threading
from datetime import datetime as _v151_datetime, timedelta as _v151_timedelta
_V151_EXPORT_LOCAL = _v151_threading.local()
_V151_MONTH_LOCAL = _v151_threading.local()
_V151_REBALANCE_LOCK = _v151_threading.RLock()
_V151_BASE_SEND_EXPORT = _v177_legacy_0209_send_export_for_chat_to
_V151_BASE_SEND_EXACT_EXPORT = _v177_legacy_0179_send_exact_range_export
_V151_BASE_PERIOD_ROWS = _v177_legacy_0203_period_export_rows
_V151_BASE_EXACT_ROWS = _v177_legacy_0173_exact_export_rows
_V151_BASE_SET_WEBHOOK = _v177_legacy_0270_set_webhook
_V151_BASE_ADD_RECORD = globals().get('_finance_add_record_base')
_V151_BASE_ADD_LEDGER_RECORD = globals().get('_base_add_currency_record')

def _v151_float(value, default=0.0) -> float:
    try:
        number = float(value or 0)
        return number if _v151_math.isfinite(number) else float(default)
    except Exception:
        return float(default)

def _v151_num(value):
    number = _v151_float(value)
    return int(number) if float(number).is_integer() else number

def _v151_now() -> str:
    try:
        return now_local().isoformat(timespec='seconds')
    except Exception:
        return _v151_datetime.now().astimezone().isoformat(timespec='seconds')

def _v151_day_key(rec: dict) -> str:
    try:
        return str(_record_day_key(rec))[:10]
    except Exception:
        return str((rec or {}).get('day_key') or '')[:10]

def _v151_parse_day(value: str):
    raw = str(value or '')[:10]
    for fmt in ('%Y-%m-%d', '%d.%m.%Y', '%d.%m.%y'):
        try:
            return _v151_datetime.strptime(raw, fmt)
        except Exception:
            continue
    return None

def _v151_sync_currency_snapshots(store: dict) -> str:
    try:
        active = _ensure_currency_ledgers(store)
        _snapshot_active_currency_ledger(store, active)
        return active
    except Exception:
        return str(store.setdefault('settings', {}).get('_active_currency_ledger') or 'ars').lower()

def _v151_ars_records(chat_id: int) -> list[dict]:
    """Authoritative ARS ledger for every report/export/UI balance calculation.

    v253 currency-isolation contract:
    * a pure USD operation is never projected into the ARS table;
    * a genuinely mixed operation (non-zero ARS + USD component) remains in both
      independent currency sections;
    * historical ARS amounts are never re-parsed from source text.

    Pure USD is detected only from explicit accounting metadata, never from note
    text: ``usd_only``, explicit ``currency=USD``, or the safe legacy shape
    ``amount == 0`` with a non-zero ``usd_amount``.  The last shape has no ARS
    monetary effect, so excluding it cannot change a real peso balance.
    """
    # R15: immediately after an incremental finance commit the store is already
    # consistent for rendering (records + daily_records + balance).  The debounced
    # FINANCE_TASK_POOL finalizer performs the historical full normalize/dedupe.
    # Skipping it here keeps the first visual repaint cheap on long histories.
    store = get_chat_store(int(chat_id))
    if not bool(store.get('_finance_hotpath_pending_normalize_r15')):
        try:
            normalize_chat_records(int(chat_id))
        except Exception as _v258_norm_exc:
            try: log_error(f'v258 report normalize ARS {chat_id}: {_v258_norm_exc}')
            except Exception: pass
        store = get_chat_store(int(chat_id))
    active = _v151_sync_currency_snapshots(store)
    source = store.get('records', []) if active == 'ars' else store.get('ars_records', [])
    rows = []
    filtered_pure_usd = 0
    for rec in source or []:
        if not isinstance(rec, dict):
            continue
        ars_amount = _v151_float(rec.get('amount'))
        usd_amount = _v151_float(rec.get('usd_amount'))
        explicit_currency = str(rec.get('currency') or '').strip().casefold()
        pure_usd = bool(rec.get('usd_only', False))
        pure_usd = pure_usd or explicit_currency in {'usd', '$', 'us$', 'u$s'}
        pure_usd = pure_usd or (abs(ars_amount) <= 1e-12 and abs(usd_amount) > 1e-12)
        if pure_usd:
            filtered_pure_usd += 1
            continue
        item = dict(rec)
        item['_v151_amount'] = ars_amount
        item['_v151_note'] = str(rec.get('note') or '')
        item['_v151_currency'] = 'ars'
        item['_v195_authoritative'] = True
        rows.append(item)
    if filtered_pure_usd:
        try:
            bot_journal('google_excel_pure_usd_removed_from_ars_v253', int(chat_id), f'count={filtered_pure_usd}; active={active}')
        except Exception:
            pass
    try:
        return sorted(rows, key=record_sort_key)
    except Exception:
        return rows

def _v177_legacy_0271_v151_usd_records(chat_id: int) -> list[dict]:
    """Собирает отдельный USD-контур и старые usd_amount без дублей."""
    store = get_chat_store(int(chat_id))
    active = _v151_sync_currency_snapshots(store)
    independent = store.get('records', []) if active == 'usd' else store.get('usd_records', [])
    ars_source = store.get('records', []) if active == 'ars' else store.get('ars_records', [])
    rows = []
    seen = set()

    def _key(rec: dict, prefix: str=''):
        operation_key = str(rec.get('operation_key') or '').strip()
        source_msg_id = int(rec.get('source_msg_id') or 0)
        if operation_key:
            return ('op', operation_key)
        if source_msg_id:
            return ('msg', source_msg_id)
        return (prefix, int(rec.get('id') or 0), str(rec.get('timestamp') or ''), _v151_day_key(rec))
    for rec in independent or []:
        if not isinstance(rec, dict):
            continue
        item = dict(rec)
        item['_v151_amount'] = _v151_float(rec.get('amount'))
        item['_v151_note'] = str(rec.get('note') or rec.get('usd_note') or '')
        item['_v151_currency'] = 'usd'
        key = _key(item, 'usd')
        seen.add(key)
        rows.append(item)
    for rec in ars_source or []:
        if not isinstance(rec, dict):
            continue
        if rec.get('usd_amount') is None or abs(_v151_float(rec.get('usd_amount'))) <= 1e-12:
            continue
        key = _key(rec, 'embedded')
        if key in seen:
            continue
        item = dict(rec)
        item['_v151_amount'] = _v151_float(rec.get('usd_amount'))
        item['_v151_note'] = str(rec.get('usd_note') or rec.get('note') or '')
        item['_v151_currency'] = 'usd'
        item['_v151_embedded'] = True
        seen.add(key)
        rows.append(item)
    try:
        return sorted(rows, key=record_sort_key)
    except Exception:
        return rows
try:
    _v177_legacy_0271_v151_usd_records.__name__ = '_v151_usd_records'
except Exception:
    pass

def _v151_all_records(chat_id: int, currency: str) -> list[dict]:
    return _v151_usd_records(chat_id) if str(currency).lower() == 'usd' else _v151_ars_records(chat_id)

def _v151_context() -> dict:
    return dict(getattr(_V151_EXPORT_LOCAL, 'value', None) or {})

def _v177_legacy_0273_v151_context_bounds(chat_id: int, ctx: dict | None=None) -> tuple[str, str]:
    ctx = dict(ctx or _v151_context())
    day_key = str(ctx.get('day_key') or today_key())[:10]
    kind = str(ctx.get('kind') or 'period')
    if kind == 'exact':
        start = str(ctx.get('start_key') or day_key)[:10]
        end = str(ctx.get('end_key') or day_key)[:10]
        return (end, start) if end < start else (start, end)
    mode = str(ctx.get('mode') or 'all').replace('csv_', '').replace('xlsx_', '')
    base = _v151_parse_day(day_key) or now_local().replace(hour=0, minute=0, second=0, microsecond=0)
    if mode == 'day':
        return (day_key, day_key)
    if mode == 'week':
        return ((base - _v151_timedelta(days=6)).strftime('%Y-%m-%d'), day_key)
    if mode == 'month':
        return (base.replace(day=1).strftime('%Y-%m-%d'), day_key)
    if mode == 'wedthu':
        start = base
        while start.weekday() != 2:
            start -= _v151_timedelta(days=1)
        return (start.strftime('%Y-%m-%d'), (start + _v151_timedelta(days=1)).strftime('%Y-%m-%d'))
    days = [_v151_day_key(r) for r in _v151_ars_records(chat_id) + _v151_usd_records(chat_id)]
    days = sorted((x for x in days if _v151_parse_day(x)))
    return (days[0], days[-1]) if days else (day_key, day_key)
try:
    _v177_legacy_0273_v151_context_bounds.__name__ = '_v151_context_bounds'
except Exception:
    pass

def _v151_period_days(start_key: str, end_key: str) -> int:
    start = _v151_parse_day(start_key)
    end = _v151_parse_day(end_key)
    if not start or not end:
        return 1
    if end < start:
        start, end = (end, start)
    return max(1, (end.date() - start.date()).days + 1)

def _v151_records_in_context(chat_id: int, currency: str, ctx: dict | None=None) -> list[dict]:
    ctx = dict(ctx or _v151_context())
    start_key, end_key = _v151_context_bounds(chat_id, ctx)
    start_rid = int(ctx.get('start_rid') or 0)
    end_rid = int(ctx.get('end_rid') or 0)
    exact = str(ctx.get('kind') or '') == 'exact'
    out = []
    for rec in _v151_all_records(chat_id, currency):
        day = _v151_day_key(rec)
        if not day or day < start_key or day > end_key:
            continue
        if exact and str(currency).lower() == 'ars':
            rid = int(rec.get('id') or 0)
            if day == start_key and start_rid and (rid < start_rid):
                continue
            if day == end_key and end_rid and (rid > end_rid):
                continue
        out.append(rec)
    try:
        return sorted(out, key=record_sort_key)
    except Exception:
        return out

def _v151_opening_balance(chat_id: int, currency: str, ctx: dict | None=None) -> float:
    ctx = dict(ctx or _v151_context())
    start_key, _end_key = _v151_context_bounds(chat_id, ctx)
    start_rid = int(ctx.get('start_rid') or 0)
    exact = str(ctx.get('kind') or '') == 'exact'
    canonical = globals().get('_excel_canonical_opening_balance')
    if callable(canonical):
        return float(canonical(int(chat_id), currency, start_key, start_rid, exact))
    total = 0.0
    for rec in _v151_all_records(chat_id, currency):
        day = _v151_day_key(rec)
        if day < start_key:
            total += _v151_float(rec.get('_v151_amount'))
            continue
        if day > start_key:
            break
        if exact and str(currency).lower() == 'ars' and start_rid:
            if int(rec.get('id') or 0) < start_rid:
                total += _v151_float(rec.get('_v151_amount'))
                continue
        break
    return total

def _v151_usd_rate() -> float:
    try:
        row = usd_rate_cached(force=False) or {}
        return max(0.0, _v151_float(row.get('rate') or row.get('venta') or row.get('sell')))
    except Exception:
        return 0.0

def _v151_product_total(chat_id: int, records: list[dict]) -> float:
    store = get_chat_store(int(chat_id))
    total = 0.0
    for rec in records or []:
        amount = _v151_float(rec.get('_v151_amount'))
        if amount >= 0:
            continue
        note = str(rec.get('_v151_note') or '')
        try:
            category = resolve_expense_category(note, store)
            override_slug = str((rec or {}).get('category_override_slug') or '').strip()
            if override_slug:
                category = get_category_by_slug(override_slug, store) or category
            category = str(category or '').strip().casefold()
        except Exception:
            category = ''
        if category in {'продукты', 'продукт', 'еда', 'food', 'products'}:
            total += abs(amount)
    return total

def _v151_food_metric(chat_id: int, records: list[dict], start_key: str, end_key: str) -> tuple[float, float, int, float]:
    products = _v151_product_total(chat_id, records)
    days = _v151_period_days(start_key, end_key)
    rate = _v151_usd_rate()
    metric = products / 5.0 / rate / days if rate > 0 and days > 0 else 0.0
    return (products, metric, days, rate)

def _v151_reserve(chat_id: int, currency: str) -> float:
    try:
        return max(0.0, _v151_float(gomonk_total(int(chat_id), currency)))
    except Exception:
        return 0.0

def _v151_table_totals(records: list[dict], opening: float) -> tuple[float, float, float]:
    income = sum((max(0.0, _v151_float(r.get('_v151_amount'))) for r in records or []))
    expense = sum((max(0.0, -_v151_float(r.get('_v151_amount'))) for r in records or []))
    return (income, expense, opening + income - expense)

def _v177_legacy_0274_v151_simple_table(chat_id: int, currency: str, compact: bool=False) -> tuple[list[list], dict[tuple[int, int], str]]:
    """Build the canonical simple table.

    v257 Google/full-table contract: A=Date, B=Description, C=Amount. Income is
    positive and expense is negative in the same C column. Period Income and
    Period Expense totals are also both displayed in C (expense total positive).
    The compact legacy export keeps its historical three-column split because it
    is a separate downloadable layout and is not the Thu-Wed Google grid.
    """
    ctx = _v151_context()
    start_key, end_key = _v151_context_bounds(chat_id, ctx)
    records = _v151_records_in_context(chat_id, currency, ctx)
    opening = _v151_opening_balance(chat_id, currency, ctx)
    income, expense, closing = _v151_table_totals(records, opening)
    reserve = _v151_reserve(chat_id, currency)
    turnover = closing - min(reserve, max(0.0, closing))
    rows = []
    annotations: dict[tuple[int, int], str] = {}
    title = str(currency).upper()
    if compact:
        rows.extend([[title, '', ''], ['Дата', 'Приход', 'Расход'], ['Остаток с прошлого раза', _v151_num(opening), ''], []])
        prev_day = None
        for rec in records:
            day = _v151_day_key(rec)
            if prev_day is not None and day != prev_day:
                rows.append([])
            prev_day = day
            amount = _v151_float(rec.get('_v151_amount'))
            income_cell, expense_cell = _xlsx_income_expense_values(amount)
            rows.append([fmt_date_table(day), income_cell, expense_cell])
            note = str(rec.get('_v151_note') or '').strip()
            if note:
                annotations[len(rows), 2 if income_cell != '' else 3] = note
        rows.extend([[], ['Приход за период', _v151_num(income), ''], ['Расход за период', '', _v151_num(expense)], ['Остаток на руках', _v151_num(closing), ''], ['Гомонковые', _v151_num(reserve), ''], ['Остаток в обороте', _v151_num(turnover), '']])
        if currency == 'ars':
            products, metric, days, rate = _v151_food_metric(chat_id, records, start_key, end_key)
            rows.extend([[], ['Продукты', _v151_num(products), ''], [], ['Расход еды на человека в сутки', metric, ''], ['Расчёт', f'{days} дн. · 5 чел. · курс {rate:g}' if rate > 0 else f'{days} дн. · 5 чел. · курс не найден', '']])
        return (rows, annotations)

    rows.extend([[title, '', ''], ['Дата', 'Описание', 'Приход'], ['', 'Остаток с прошлого раза', _v151_num(opening)], []])
    prev_day = None
    for rec in records:
        day = _v151_day_key(rec)
        if prev_day is not None and day != prev_day:
            rows.append([])
        prev_day = day
        amount = _v151_float(rec.get('_v151_amount'))
        rows.append([fmt_date_table(day), str(rec.get('_v151_note') or ''), _v151_num(amount)])
    rows.extend([[], ['', 'Приход за период', _v151_num(income)], ['', 'Расход за период', _v151_num(expense)], ['', 'Остаток на руках', _v151_num(closing)], ['', 'Гомонковые', _v151_num(reserve)], ['', 'Остаток в обороте', _v151_num(turnover)]])
    if currency == 'ars':
        products, metric, days, rate = _v151_food_metric(chat_id, records, start_key, end_key)
        rows.extend([[], ['', 'Продукты', _v151_num(products)], [], ['', 'Расход еды на человека в сутки', metric], ['', 'Расчёт', f'{days} дн. · 5 чел. · курс {rate:g}' if rate > 0 else f'{days} дн. · 5 чел. · курс не найден']])
    return (rows, annotations)

try:
    _v177_legacy_0274_v151_simple_table.__name__ = '_v151_simple_table'
except Exception:
    pass

def _v177_legacy_0275_v151_categories(chat_id: int, records: list[dict]) -> list[str]:
    store = get_chat_store(int(chat_id))
    totals = {}
    for rec in records:
        amount = _v151_float(rec.get('_v151_amount'))
        if amount >= 0:
            continue
        note = str(rec.get('_v151_note') or '')
        try:
            category = resolve_expense_category(note, store)
            override_slug = str(rec.get('category_override_slug') or '').strip()
            if override_slug:
                category = get_category_by_slug(override_slug, store) or category
        except Exception:
            category = 'прочие'
        totals[str(category or 'прочие')] = totals.get(str(category or 'прочие'), 0.0) + abs(amount)
    try:
        categories = list(get_ordered_category_names(cats=totals, store=store) or [])
    except Exception:
        categories = list(totals)
    return categories or ['прочие']
try:
    _v177_legacy_0275_v151_categories.__name__ = '_v151_categories'
except Exception:
    pass

def _v177_legacy_0276_v151_category_table(chat_id: int, currency: str) -> list[list]:
    ctx = _v151_context()
    start_key, end_key = _v151_context_bounds(chat_id, ctx)
    records = _v151_records_in_context(chat_id, currency, ctx)
    opening = _v151_opening_balance(chat_id, currency, ctx)
    categories = _v151_categories(chat_id, records)
    clean_categories = [_clean_category_display_name(x) for x in categories]
    rows = [[str(currency).upper()] + [''] * (2 + len(categories))]
    rows.append(['Дата', 'Описание', 'Приход'] + clean_categories)
    rows.append(['', 'Остаток с прошлого раза', _v151_num(opening)] + [''] * len(categories))
    rows.append([])
    store = get_chat_store(int(chat_id))
    cat_totals = {cat: 0.0 for cat in categories}
    income = 0.0
    expense = 0.0
    prev_day = None
    for rec in records:
        day = _v151_day_key(rec)
        if prev_day is not None and day != prev_day:
            rows.append([])
        prev_day = day
        note = str(rec.get('_v151_note') or '')
        amount = _v151_float(rec.get('_v151_amount'))
        row = [fmt_date_table(day), note, ''] + [''] * len(categories)
        if amount >= 0:
            income += amount
            row[2] = _v151_num(amount)
        else:
            value = abs(amount)
            expense += value
            try:
                category = resolve_expense_category(note, store)
                override_slug = str(rec.get('category_override_slug') or '').strip()
                if override_slug:
                    category = get_category_by_slug(override_slug, store) or category
            except Exception:
                category = 'прочие'
            if category not in cat_totals:
                category = categories[-1]
            idx = categories.index(category)
            cat_totals[category] += value
            row[3 + idx] = _v151_num(value)
        rows.append(row)
    closing = opening + income - expense
    reserve = _v151_reserve(chat_id, currency)
    turnover = closing - min(reserve, max(0.0, closing))
    rows.extend([[], ['', 'Сумма по статьям', _v151_num(income)] + [_v151_num(cat_totals.get(cat, 0.0)) for cat in categories], [], ['', 'Расход', _v151_num(expense)] + [''] * len(categories), ['', 'Приход', _v151_num(income)] + [''] * len(categories), ['', 'Остаток на руках', _v151_num(closing)] + [''] * len(categories), ['', 'Гомонковые', _v151_num(reserve)] + [''] * len(categories), ['', 'Остаток в обороте', _v151_num(turnover)] + [''] * len(categories)])
    if currency == 'ars':
        products, metric, days, rate = _v151_food_metric(chat_id, records, start_key, end_key)
        rows.extend([[], ['', 'Продукты', _v151_num(products)] + [''] * len(categories), [], ['', 'Расход еды на человека в сутки', metric] + [''] * len(categories), ['', 'Расчёт', f'{days} дн. · 5 чел. · курс {rate:g}' if rate > 0 else f'{days} дн. · 5 чел. · курс не найден'] + [''] * len(categories)])
    return rows

try:
    _v177_legacy_0276_v151_category_table.__name__ = '_v151_category_table'
except Exception:
    pass

def _v177_legacy_0176_build_exact_category_stats_xlsx_rows(target_chat_id: int, start_key: str, start_rid: int, end_key: str, end_rid: int) -> list[list]:
    previous = getattr(_V151_EXPORT_LOCAL, 'value', None)
    if not previous:
        _V151_EXPORT_LOCAL.value = {'kind': 'exact', 'target_chat_id': int(target_chat_id), 'start_key': str(start_key)[:10], 'start_rid': int(start_rid or 0), 'end_key': str(end_key)[:10], 'end_rid': int(end_rid or 0), 'file_type': 'xlsxstat'}
    try:
        ars_rows = _v151_category_table(int(target_chat_id), 'ars')
        usd_rows = _v151_category_table(int(target_chat_id), 'usd')
        return ars_rows + [[], []] + usd_rows
    finally:
        if not previous:
            _V151_EXPORT_LOCAL.value = None
try:
    _v177_legacy_0176_build_exact_category_stats_xlsx_rows.__name__ = 'build_exact_category_stats_xlsx_rows'
except Exception:
    pass

def _v177_legacy_0092_xlsx_simple_rows_with_balances(rows: list[list], opening_balance: float, target_chat_id: int | None=None) -> list[list]:
    if target_chat_id is None:
        return globals().get('_V150_BASE_SIMPLE_ROWS', lambda r, o, *_: r)(rows, opening_balance, target_chat_id)
    ars_rows, _ = _v151_simple_table(int(target_chat_id), 'ars', compact=False)
    usd_rows, _ = _v151_simple_table(int(target_chat_id), 'usd', compact=False)
    return ars_rows + [[], []] + usd_rows
try:
    _v177_legacy_0092_xlsx_simple_rows_with_balances.__name__ = '_xlsx_simple_rows_with_balances'
except Exception:
    pass

def _v177_legacy_0095_compact_simple_excel_rows_and_annotations(raw_rows: list[tuple], opening_balance: float, target_chat_id: int | None=None) -> tuple[list[list], dict[tuple[int, int], str]]:
    if target_chat_id is None:
        base = globals().get('_V150_BASE_COMPACT_ROWS')
        return base(raw_rows, opening_balance, target_chat_id) if callable(base) else ([], {})
    ars_rows, ars_notes = _v151_simple_table(int(target_chat_id), 'ars', compact=True)
    offset = len(ars_rows) + 2
    usd_rows, usd_notes = _v151_simple_table(int(target_chat_id), 'usd', compact=True)
    notes = dict(ars_notes)
    for (row_idx, col_idx), text in usd_notes.items():
        notes[int(row_idx) + offset, int(col_idx)] = text
    return (ars_rows + [[], []] + usd_rows, notes)
try:
    _v177_legacy_0095_compact_simple_excel_rows_and_annotations.__name__ = '_compact_simple_excel_rows_and_annotations'
except Exception:
    pass

def _v151_excel_options_for_style(style: str | None, options: dict | None) -> dict | None:
    if isinstance(options, dict):
        return options
    mode = str(style or '').strip().lower()
    if not mode:
        try:
            return normalize_excel_export_options()
        except Exception:
            return {'old_table': True, 'comments': False, 'notes': False, 'description_column': True}
    mapping = {'old': {'old_table': True, 'comments': False, 'notes': False, 'description_column': True}, 'new_plain': {'old_table': False, 'comments': False, 'notes': False, 'description_column': True}, 'new_comments': {'old_table': False, 'comments': True, 'notes': False, 'description_column': True}, 'new_notes': {'old_table': False, 'comments': False, 'notes': True, 'description_column': True}, 'google_notes': {'old_table': False, 'comments': False, 'notes': True, 'description_column': True}}
    return mapping.get(mode) or normalize_excel_export_options()

def _canon_send_export_for_chat_to__001(recipient_chat_id: int, target_chat_id: int, mode: str, day_key: str, file_type: str='csv', excel_style_override: str | None=None, excel_options_override: dict | None=None, delivery: str='chat'):
    previous = getattr(_V151_EXPORT_LOCAL, 'value', None)
    _V151_EXPORT_LOCAL.value = {'kind': 'period', 'target_chat_id': int(target_chat_id), 'mode': str(mode or 'all'), 'day_key': str(day_key or today_key())[:10], 'file_type': str(file_type or 'csv').lower()}
    try:
        options = excel_options_override
        if str(file_type or '').lower().lstrip('.') in {'xlsx', 'xlsxstat'}:
            effective_style = excel_style_override or excel_table_style(int(target_chat_id))
            options = _v151_excel_options_for_style(effective_style, excel_options_override)
        return _V151_BASE_SEND_EXPORT(recipient_chat_id, target_chat_id, mode, day_key, file_type, excel_style_override=excel_style_override, excel_options_override=options, delivery=delivery)
    finally:
        _V151_EXPORT_LOCAL.value = previous

def _canon_send_exact_range_export__001(recipient_chat_id: int, target_chat_id: int, start_key: str, start_rid: int, end_key: str, end_rid: int, file_type: str, excel_style_override: str | None=None, excel_options_override: dict | None=None, delivery: str='chat'):
    previous = getattr(_V151_EXPORT_LOCAL, 'value', None)
    _V151_EXPORT_LOCAL.value = {'kind': 'exact', 'target_chat_id': int(target_chat_id), 'start_key': str(start_key)[:10], 'start_rid': int(start_rid or 0), 'end_key': str(end_key)[:10], 'end_rid': int(end_rid or 0), 'file_type': str(file_type or 'csv').lower()}
    try:
        options = excel_options_override
        if str(file_type or '').lower().lstrip('.') in {'xlsx', 'xlsxstat'}:
            effective_style = excel_style_override or excel_table_style(int(target_chat_id))
            options = _v151_excel_options_for_style(effective_style, excel_options_override)
        return _V151_BASE_SEND_EXACT_EXPORT(recipient_chat_id, target_chat_id, start_key, start_rid, end_key, end_rid, file_type, excel_style_override=excel_style_override, excel_options_override=options, delivery=delivery)
    finally:
        _V151_EXPORT_LOCAL.value = previous

def _v177_legacy_0204_period_export_rows(chat_id: int, mode: str, day_key: str):
    """Canonical rows for every CSV/XLSX period export.

    CSV follows the selected ARS/USD operation view. XLSX builders later build
    both isolated ledgers, so ARS rows here are only the presence/caption source.
    """
    ctx = _v151_context()
    file_type = str(ctx.get('file_type') or 'csv').lower()
    store = get_chat_store(int(chat_id))
    currency = 'ars' if file_type in {'xlsx', 'xlsxstat'} else 'usd' if financial_view_is_usd(store) else 'ars'
    records = _v151_records_in_context(int(chat_id), currency, ctx)
    if file_type in {'xlsx', 'xlsxstat'} and (not records):
        records = _v151_records_in_context(int(chat_id), 'usd', ctx)
    rows = [(fmt_date_table(_v151_day_key(r)), fmt_csv_amount(r.get('_v151_amount')), r.get('_v151_note', '')) for r in records]
    labels = {'day': 'за день', 'week': 'за неделю', 'month': 'за месяц', 'wedthu': 'Чт–Ср', 'all': 'за всё время'}
    normalized = str(mode or 'all').replace('csv_', '').replace('xlsx_', '')
    label = labels.get(normalized, 'за всё время')
    if currency == 'usd' and file_type not in {'xlsx', 'xlsxstat'}:
        label = 'USD ' + label
    return (rows, label)
try:
    _v177_legacy_0204_period_export_rows.__name__ = '_period_export_rows'
except Exception:
    pass

def _canon_exact_export_rows__001(chat_id: int, start_key: str, start_rid: int, end_key: str, end_rid: int):
    ctx = _v151_context()
    file_type = str(ctx.get('file_type') or 'csv').lower()
    store = get_chat_store(int(chat_id))
    currency = 'ars' if file_type in {'xlsx', 'xlsxstat'} else 'usd' if financial_view_is_usd(store) else 'ars'
    records = _v151_records_in_context(int(chat_id), currency, ctx)
    if file_type in {'xlsx', 'xlsxstat'} and (not records):
        records = _v151_records_in_context(int(chat_id), 'usd', ctx)
    return [(fmt_date_table(_v151_day_key(r)), fmt_csv_amount(r.get('_v151_amount')), r.get('_v151_note', '')) for r in records]

def _v151_rebalance_key(chat_id: int, currency: str, rec: dict) -> str:
    operation_key = str((rec or {}).get('operation_key') or '').strip()
    if operation_key:
        return f'{int(chat_id)}:{currency}:{operation_key}'
    source_msg_id = int((rec or {}).get('source_msg_id') or 0)
    if source_msg_id:
        return f'{int(chat_id)}:{currency}:msg:{source_msg_id}'
    return f"{int(chat_id)}:{currency}:rid:{int((rec or {}).get('id') or 0)}:{str((rec or {}).get('timestamp') or '')}"

def _v151_ledger_balance(chat_id: int, currency: str) -> float:
    return sum((_v151_float(r.get('_v151_amount')) for r in _v151_all_records(int(chat_id), currency)))

def _v151_reduce_reserve(chat_id: int, currency: str, amount: float) -> list[dict]:
    entries = [dict(x) for x in gomonk_entries(int(chat_id), currency) or []]
    left = max(0.0, _v151_float(amount))
    for idx in range(len(entries) - 1, -1, -1):
        if left <= 1e-09:
            break
        current = max(0.0, _v151_float(entries[idx].get('amount')))
        used = min(current, left)
        entries[idx]['amount'] = current - used
        left -= used
    return [x for x in entries if _v151_float(x.get('amount')) > 1e-09]

def _v151_apply_reserve_cover(chat_id: int, currency: str, rec: dict | None, reason: str='new_finance_operation') -> dict:
    if not isinstance(rec, dict):
        return {}
    currency = 'usd' if str(currency).lower() == 'usd' else 'ars'
    marker_root = rec.setdefault('gomonk_rebalance_v151', {})
    if marker_root.get(currency):
        return marker_root[currency]
    key = _v151_rebalance_key(int(chat_id), currency, rec)
    receipts = data.setdefault('gomonk_rebalance_receipts_v151', {})
    with _V151_REBALANCE_LOCK:
        existing = receipts.get(key)
        if isinstance(existing, dict) and existing.get('status') == 'done':
            marker_root[currency] = dict(existing.get('result') or existing)
            return marker_root[currency]
        settings = get_chat_store(int(chat_id)).setdefault('settings', {})
        enabled_key = 'usd_gomonk_enabled' if currency == 'usd' else 'gomonk_enabled'
        balance = _v151_ledger_balance(int(chat_id), currency)
        target = _v151_reserve(int(chat_id), currency)
        effective = min(target, max(0.0, balance)) if bool(settings.get(enabled_key, False)) else 0.0
        virtual_used = max(0.0, target - effective) if bool(settings.get(enabled_key, False)) else 0.0
        turnover_before = balance - target
        turnover_after = balance - effective
        receipts[key] = {'status': 'pending', 'chat_id': int(chat_id), 'currency': currency, 'record_id': rec.get('id'), 'source_msg_id': rec.get('source_msg_id'), 'created_at': _v151_now(), 'reason': reason}
        result = {'key': key, 'currency': currency, 'at': _v151_now(), 'reason': reason, 'balance': balance, 'reserve_before': target, 'turnover_before': turnover_before, 'consumed': virtual_used, 'reserve_after': effective, 'turnover_after': turnover_after, 'constant_target_v209': target, 'entries_mutated': False}
        marker_root[currency] = result
        receipts[key] = {'status': 'done', 'done_at': _v151_now(), 'result': result}
        history = settings.setdefault('gomonk_rebalance_history_v151', [])
        history.append({**result, 'record_id': rec.get('id'), 'source_msg_id': rec.get('source_msg_id')})
        del history[:-500]
        try:
            persist_finance_chat_local_fast(int(chat_id))
        except Exception:
            pass
        try:
            fn = globals().get('schedule_finance_root_persist_v243')
            if callable(fn):
                fn(int(chat_id), 0.45)
        except Exception:
            pass
        try:
            schedule_config_backup_for_chats(int(chat_id), delay=0.8)
        except Exception:
            pass
        try:
            bot_journal('gomonk_constant_cover_v209', int(chat_id), f'currency={currency}; key={key}; target={target}; active={effective}; turnover={turnover_after}')
        except Exception:
            pass
        return result

# R11: the authoritative finance row is already committed by _finance_add_record_base.
# Gomonk/reserve-cover is derived state and must never keep the Telegram content lane
# busy after that commit. Queue it on the per-chat FINANCE lane and coalesce bursts.
_V151_POSTCOMMIT_LOCK = _v151_threading.RLock()
_V151_POSTCOMMIT_PENDING = {}
_V151_POSTCOMMIT_RUNNING = set()

def _v151_postcommit_identity(chat_id: int, rec: dict) -> dict:
    return {
        'uid': str((rec or {}).get('record_uid') or ''),
        'source_msg_id': int((rec or {}).get('source_msg_id') or 0),
        'record_id': int((rec or {}).get('id') or 0),
        'day_key': str((rec or {}).get('day_key') or ''),
    }

def _v151_resolve_postcommit_record(chat_id: int, ident: dict):
    uid = str((ident or {}).get('uid') or '')
    if uid and callable(globals().get('find_finance_record_by_uid')):
        try:
            rec = find_finance_record_by_uid(int(chat_id), uid)
            if isinstance(rec, dict):
                return rec
        except Exception:
            pass
    source_msg_id = int((ident or {}).get('source_msg_id') or 0)
    if source_msg_id and callable(globals().get('find_record_by_message_id')):
        try:
            rec = find_record_by_message_id(int(chat_id), source_msg_id)
            if isinstance(rec, dict):
                return rec
        except Exception:
            pass
    rid = int((ident or {}).get('record_id') or 0)
    try:
        for _key, rec in _finance_record_lists(get_chat_store(int(chat_id))):
            if isinstance(rec, dict) and rid and int(rec.get('id') or 0) == rid:
                return rec
    except Exception:
        pass
    return None

def _v151_postcommit_cover_job(chat_id: int):
    cid = int(chat_id)
    try:
        while True:
            with _V151_POSTCOMMIT_LOCK:
                batch = list((_V151_POSTCOMMIT_PENDING.get(cid) or {}).values())
                _V151_POSTCOMMIT_PENDING[cid] = {}
            if not batch:
                break
            last_day = ''
            for item in batch:
                ident = dict(item.get('ident') or {})
                rec = _v151_resolve_postcommit_record(cid, ident)
                if not isinstance(rec, dict):
                    continue
                last_day = str(ident.get('day_key') or rec.get('day_key') or last_day)
                for currency in tuple(item.get('currencies') or ('ars',)):
                    try:
                        _v151_apply_reserve_cover(cid, str(currency), rec, 'postcommit_async_r11')
                    except Exception as exc:
                        try: log_error(f'R11 async reserve cover chat={cid} currency={currency}: {exc}')
                        except Exception: pass
            # finance_changed/schedule_finalize is normally queued by the caller after
            # add_record_to_chat returns. A tiny safety repaint is only needed when this
            # helper was invoked from a path that did not schedule one.
            try:
                if last_day and callable(globals().get('schedule_financial_window_refresh')):
                    schedule_financial_window_refresh(cid, last_day, reason='reserve_cover_r11', delay=0.02)
            except Exception:
                pass
    finally:
        rerun = False
        with _V151_POSTCOMMIT_LOCK:
            _V151_POSTCOMMIT_RUNNING.discard(cid)
            rerun = bool(_V151_POSTCOMMIT_PENDING.get(cid))
        if rerun:
            _v151_schedule_postcommit_cover(cid, None, ())

def _v151_schedule_postcommit_cover(chat_id: int, rec: dict | None, currencies) -> bool:
    cid = int(chat_id)
    with _V151_POSTCOMMIT_LOCK:
        if isinstance(rec, dict):
            ident = _v151_postcommit_identity(cid, rec)
            key = str(ident.get('uid') or ident.get('source_msg_id') or ident.get('record_id') or id(rec))
            row = (_V151_POSTCOMMIT_PENDING.setdefault(cid, {})).setdefault(key, {'ident': ident, 'currencies': set()})
            row['currencies'].update(str(x) for x in (currencies or ()) if x)
        if cid in _V151_POSTCOMMIT_RUNNING:
            return True
        if not _V151_POSTCOMMIT_PENDING.get(cid):
            return True
        _V151_POSTCOMMIT_RUNNING.add(cid)
    pool = globals().get('FINANCE_TASK_POOL')
    try:
        if pool is not None and hasattr(pool, 'submit') and pool.submit(cid, _v151_postcommit_cover_job, cid):
            return True
    except Exception:
        pass
    # Never fall back to synchronous work in the Telegram/content thread.
    try:
        t = _v151_threading.Thread(target=_v151_postcommit_cover_job, args=(cid,), name=f'fin-cover-r11-{cid}', daemon=True)
        t.start()
        return True
    except Exception:
        with _V151_POSTCOMMIT_LOCK:
            _V151_POSTCOMMIT_RUNNING.discard(cid)
        return False

def add_record_to_chat(chat_id: int, amount: float, note: str, owner: int, source_msg=None, day_key=None, usd_amount=None, usd_note: str='', usd_only: bool=False, source_finance_text: str=''):
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

def _add_record_to_currency_ledger(chat_id: int, ledger: str, amount: float, note: str, owner: int, source_msg=None, day_key: str | None=None):
    ledger = 'usd' if str(ledger).lower() == 'usd' else 'ars'
    store_before = get_chat_store(int(chat_id))
    active = str(store_before.setdefault('settings', {}).get('_active_currency_ledger') or 'ars')
    records_before = store_before.get('records', []) if active == ledger else store_before.get(f'{ledger}_records', [])
    existing_keys = {_v151_rebalance_key(int(chat_id), ledger, r) for r in records_before or [] if isinstance(r, dict)}
    result = _V151_BASE_ADD_LEDGER_RECORD(chat_id, ledger, amount, note, owner, source_msg=source_msg, day_key=day_key)
    store_after = get_chat_store(int(chat_id))
    active_after = str(store_after.setdefault('settings', {}).get('_active_currency_ledger') or 'ars')
    records_after = store_after.get('records', []) if active_after == ledger else store_after.get(f'{ledger}_records', [])
    rec = None
    source_msg_id = int(getattr(source_msg, 'message_id', 0) or 0) if source_msg is not None else 0
    if source_msg_id:
        rec = next((r for r in records_after or [] if isinstance(r, dict) and int(r.get('source_msg_id') or 0) == source_msg_id), None)
    if rec is None:
        rec = next((r for r in reversed(records_after or []) if isinstance(r, dict) and _v151_rebalance_key(int(chat_id), ledger, r) not in existing_keys), None)
    if rec is None and isinstance(result, dict):
        rec = result
    if isinstance(rec, dict):
        try:
            ensure_finance_record_uid(int(chat_id), rec)
        except Exception:
            pass
        _v151_schedule_postcommit_cover(int(chat_id), rec, [ledger])
        try:
            schedule_financial_window_refresh(int(chat_id), str(rec.get('day_key') or day_key or ''), reason='currency_record_add_fast_r11')
        except Exception:
            pass
    return result if result is not None else rec

def _v151_repair_pending_rebalances() -> int:
    repaired = 0
    receipts = data.setdefault('gomonk_rebalance_receipts_v151', {})
    for key, receipt in list(receipts.items()):
        if not isinstance(receipt, dict) or receipt.get('status') != 'pending':
            continue
        try:
            chat_id = int(receipt.get('chat_id'))
            currency = str(receipt.get('currency') or 'ars')
            source_msg_id = int(receipt.get('source_msg_id') or 0)
            record_id = int(receipt.get('record_id') or 0)
            rec = next((r for r in _v151_all_records(chat_id, currency) if source_msg_id and int(r.get('source_msg_id') or 0) == source_msg_id or (record_id and int(r.get('id') or 0) == record_id)), None)
            if isinstance(rec, dict):
                _v151_apply_reserve_cover(chat_id, currency, rec, 'startup_pending_repair')
                repaired += 1
            else:
                receipt.update({'status': 'cancelled_no_record', 'closed_at': _v151_now()})
        except Exception as exc:
            try:
                log_error(f'v151 reserve receipt repair {key}: {exc}')
            except Exception:
                pass
    if repaired:
        save_data(data)
    return repaired
_V151_EXAMPLE_RE = _v151_re.compile('^\\(?\\s*(?:пример\\s*:\\s*)?имя\\s*1\\s+1?[ .]?000\\s*:\\s*имя\\s*2\\s+5?[ .]?777\\s*\\)?$', flags=_v151_re.I)

def _v151_gomonk_payload(text: str) -> tuple[str, str | None]:
    raw = str(text or '').replace('\r\n', '\n').replace('\r', '\n')
    token = _v151_re.search('\\(\\s*GOMONKI\\s*\\|\\s*(ARS|USD)\\s*\\)', raw, flags=_v151_re.I)
    currency = token.group(1).lower() if token else None
    kept = []
    for line in raw.split('\n'):
        stripped = line.strip()
        folded = _v151_re.sub('\\s+', ' ', stripped).casefold()
        if not stripped:
            continue
        if _v151_re.search('\\(\\s*gomonki\\s*\\|\\s*(?:ars|usd)\\s*\\)', folded, flags=_v151_re.I):
            continue
        if _V151_EXAMPLE_RE.match(folded):
            continue
        kept.append(stripped)
    return ('\n'.join(kept).strip(), currency)

def _canon_parse_gomonk_entries__001(text: str) -> list[dict]:
    payload, _currency = _v151_gomonk_payload(sanitize_telegram_inserted_text(str(text or '')))
    if not payload:
        return []
    parts = [p.strip() for p in _v151_re.split('\\s*:\\s*|\\n+', payload) if p.strip()]
    result = []
    number_pattern = '(?<![A-Za-zА-Яа-яЁё0-9_])[-+]?(?:\\d{1,3}(?:[ .]\\d{3})+(?:,\\d+)?|\\d+(?:[.,]\\d+)?)'
    for idx, part in enumerate(parts, start=1):
        folded = _v151_re.sub('\\s+', ' ', part).casefold().strip('() ')
        if folded.startswith('пример:') or _v151_re.fullmatch('имя\\s*[12]\\s+(?:1?[ .]?000|5?[ .]?777)', folded, flags=_v151_re.I):
            continue
        matches = list(_v151_re.finditer(number_pattern, part))
        if not matches:
            continue
        match = matches[-1]
        number = match.group(0).replace(' ', '').replace('.', '').replace(',', '.')
        try:
            amount = abs(float(number))
        except Exception:
            continue
        name = (part[:match.start()] + ' ' + part[match.end():]).strip(' -–—,.;') or f'Сумма {idx}'
        if amount > 0:
            result.append({'name': name[:80], 'amount': amount})
    return result[:30]

def _v151_gomonk_template(chat_id: int, currency: str, include_values: bool) -> str:
    username = get_bot_username_cached() or 'Good_server_bot'
    lines = [f'@{username} (GOMONKI|{currency.upper()})', '(Пример: Имя1 1000 : Имя2 5777)', '']
    if include_values:
        values = []
        for item in gomonk_entries(int(chat_id), currency):
            amount = _v151_num(item.get('amount'))
            values.append(f"{str(item.get('name') or 'Сумма').strip()} {amount}")
        lines.append(' : '.join(values))
    return '\n'.join(lines)

def _canon_build_gomonk_menu_keyboard__001(chat_id: int, currency: str | None=None):
    currency = _gomonk_currency(chat_id, currency)
    kb = types.InlineKeyboardMarkup(row_width=1)
    kb.row(IB(gomonk_toggle_label(chat_id, currency), callback_data=f'gomonk_toggle:{currency}'))
    can_edit = bool(gomonk_enabled(chat_id, currency) and gomonk_entries(chat_id, currency))
    label = '✏️ Изменить гомонковые' if can_edit else '💰 Ввести гомонковые'
    kb.row(make_copy_or_inline_button(label, _v151_gomonk_template(chat_id, currency, can_edit), viewer_chat_id=chat_id))
    kb.row(IB('🔙 Назад в Инфо', callback_data=f'gomonk_back:{currency}'))
    return kb

def _canon_build_gomonk_menu_text__001(chat_id: int, currency: str | None=None) -> str:
    currency = _gomonk_currency(chat_id, currency)
    entries = gomonk_entries(chat_id, currency)
    fmt = (lambda value: fmt_usd_native(value)) if currency == 'usd' else fmt_num
    lines = [f'🧳 Гомонковые • {currency.upper()}', '', 'ARS и USD хранятся отдельно.', 'Строка с примером является только подсказкой и никогда не сохраняется.', '', f"Режим: {('✅ ВКЛ' if gomonk_enabled(chat_id, currency) else '⬜ ВЫКЛ')}"]
    if entries:
        lines.append('Сохранено:')
        for item in entries:
            lines.append(f"• {item['name']}: {fmt(item['amount'])}")
        lines.append(f'Итого: {fmt(gomonk_total(chat_id, currency))}')
    else:
        lines.append('Сохранённых сумм пока нет.')
    return wm_common('\n'.join(lines), 9)

def _v177_legacy_0162_handle_gomonk_insert_message(msg) -> bool:
    if getattr(msg, 'content_type', None) != 'text' or not _v85_enabled('gomonk_wallets'):
        return False
    raw = str(getattr(msg, 'text', '') or '')
    if not _v151_re.search('\\(\\s*GOMONKI\\s*\\|\\s*(?:ARS|USD)\\s*\\)', raw, flags=_v151_re.I):
        return False
    _durable_note_source_consumed('gomonk_insert_v151')
    chat_id = int(msg.chat.id)
    payload, token_currency = _v151_gomonk_payload(raw)
    currency = token_currency or _gomonk_currency(chat_id)
    entries = parse_gomonk_entries(payload)
    try:
        bot.delete_message(chat_id, msg.message_id)
    except Exception:
        pass
    if not entries:
        send_and_auto_delete(chat_id, 'ℹ️ Шаблон получен без реальных значений. Гомонковые не изменены.', 12)
        return True
    set_gomonk_entries(chat_id, entries, currency)
    settings = _gomonk_settings(chat_id, currency)
    enabled_key, _entries_key, _remaining_key = _gomonk_keys(chat_id, currency)
    settings[enabled_key] = True
    save_data(data, chat_ids=[chat_id])
    total = gomonk_total(chat_id, currency)
    shown = fmt_usd_native(total) if currency == 'usd' else fmt_num(total)
    try:
        bot_journal('gomonk_values_saved_v151', chat_id, f'currency={currency}; count={len(entries)}; total={total}')
    except Exception:
        pass
    send_and_auto_delete(chat_id, f'✅ Гомонковые {currency.upper()} сохранены: {len(entries)}, сумма {shown}', 10)
    try:
        open_gomonk_window(chat_id, currency=currency)
        finance_changed(chat_id, get_chat_store(chat_id).get('current_view_day') or today_key(), reason='gomonk_update', delay=0.05)
    except Exception:
        pass
    return True
try:
    _v177_legacy_0162_handle_gomonk_insert_message.__name__ = 'handle_gomonk_insert_message'
except Exception:
    pass

def _canon_render_usd_month_window__001(chat_id: int, day_key: str):
    month_key = str(day_key or today_key())[:7]
    try:
        month_dt = _v151_datetime.strptime(month_key + '-01', '%Y-%m-%d')
        month_label = month_dt.strftime('%m.%Y')
    except Exception:
        month_label = month_key
    rows = [r for r in usd_records_for_month(int(chat_id), month_key) if _v151_float(r.get('usd_amount')) < 0]
    total_expense = sum((abs(_v151_float(r.get('usd_amount'))) for r in rows))
    lines = [f'💵 USD расходы за {month_label}', '']
    if rows:
        for rec in rows:
            amount = abs(_v151_float(rec.get('usd_amount')))
            sid = str(rec.get('usd_short_id') or rec.get('short_id') or f"U{rec.get('id', '')}")
            date_label = fmt_date_ddmmyy(_v151_day_key(rec))
            note = html.escape(str(rec.get('usd_note') or rec.get('note') or ''))
            lines.append(f'{sid} {date_label} -${fmt_num_plain(amount)} {note}'.rstrip())
    else:
        lines.append('Нет USD-расходов за этот месяц.')
    balance = usd_balance_for_chat(int(chat_id))
    lines.extend(['', f'📉 Расход за месяц: -${fmt_num_plain(total_expense)}', f"🏦 USD остаток по чату: {('+' if balance >= 0 else '-')}${fmt_num_plain(abs(balance))}"])
    try:
        _V151_MONTH_LOCAL.chat_id = int(chat_id)
    except Exception:
        pass
    return (wm_common('\n'.join(lines), 1, html_mode=True), -total_expense)

def _canon_build_usd_month_keyboard__001(day_key: str):
    """Возвращает ту же клавиатуру, что уже была в USD-окне."""
    chat_id = getattr(_V151_MONTH_LOCAL, 'chat_id', None)
    if chat_id is not None:
        try:
            return build_main_keyboard(str(day_key)[:10], int(chat_id))
        except Exception:
            pass
    try:
        return build_main_keyboard(str(day_key)[:10], None)
    except Exception:
        return types.InlineKeyboardMarkup()

def _canon_build_fin_window_usd_month_keyboard__001(target_chat_id: int, day_key: str, owner_day_key: str):
    """В окне владельца также сохраняется исходное расположение кнопок чата."""
    return build_fin_window_view_keyboard(int(target_chat_id), str(day_key)[:10], str(owner_day_key)[:10])

def _canon_set_webhook__001():
    try:
        repaired = _v151_repair_pending_rebalances()
        if repaired:
            try:
                bot_journal('v151_startup_repair', int(OWNER_ID or 0), f'reserve_receipts={repaired}')
            except Exception:
                pass
    except Exception as exc:
        try:
            log_error(f'v151 startup repair: {exc}')
        except Exception:
            pass
    return _V151_BASE_SET_WEBHOOK()
import functools as _v152_functools
import os as _v152_os
import re as _v152_re
from datetime import datetime as _v152_datetime
V152_CHAT_RIGHTS_SCHEMA = 1
V152_PERMISSION_GROUPS = (('finance', '💰 Финансы', (('finance.mode', 'Финансовый режим'), ('finance.ars', 'ARS'), ('finance.usd', 'USD'), ('finance.gomonk', 'Гомонковые'), ('finance.edit', 'Редактирование операций'), ('finance.delete', 'Удаление операций'), ('finance.view_totals', 'Просмотр итогов'), ('finance.view_month', 'Просмотр месяца'))), ('exports', '📤 Выгрузки', (('exports.excel_chat', 'Excel в чат'), ('exports.google_sheets', 'Google Sheets'), ('exports.google_drive', 'Google Drive'), ('exports.journals', 'Скачивание журналов'), ('exports.reports', 'Отчёты'))), ('reminders', '⏰ Напоминалки', (('reminders.use', 'Использование напоминалок'), ('reminders.create', 'Создание'), ('reminders.edit', 'Изменение'), ('reminders.delete', 'Удаление'), ('reminders.complete', 'Выполнение через /vyapl'))), ('forward', '🔁 Пересылка и чаты', (('forward.messages', 'Пересылка сообщений'), ('forward.media_groups', 'Пересылка медиагрупп'), ('chats.connect_children', 'Подключение дочерних чатов'), ('chats.manage_users', 'Управление пользователями'), ('chats.manage_roles', 'Управление ролями'))), ('settings', '⚙️ Настройки', (('settings.change', 'Изменение настроек'), ('settings.windows', 'Управление окнами'), ('settings.iphone', 'Быстрые отметки с iPhone'), ('settings.info', 'Просмотр INFO'), ('settings.diagnostics', 'Диагностика'), ('settings.backup_recovery', 'Backup и recovery'), ('settings.audit', 'Аудит'))))
V152_PERMISSION_ITEMS = tuple((item for _group, _label, items in V152_PERMISSION_GROUPS for item in items))
V152_PERMISSION_KEYS = tuple((key for key, _label in V152_PERMISSION_ITEMS))
V152_PERMISSION_LABELS = dict(V152_PERMISSION_ITEMS)
V152_PERMISSION_INDEX = {key: idx for idx, key in enumerate(V152_PERMISSION_KEYS)}

def _v152_permissions_root() -> dict:
    root = data.setdefault('_global_settings', {}).setdefault('chat_permissions_v152', {})
    if not isinstance(root, dict):
        root = {}
        data.setdefault('_global_settings', {})['chat_permissions_v152'] = root
    root.setdefault('schema_version', V152_CHAT_RIGHTS_SCHEMA)
    root.setdefault('global', {})
    root.setdefault('history', [])
    return root

def _v152_tenant_id_for_chat(chat_id: int) -> str:
    try:
        return str(tenant_id_for_chat(int(chat_id), create=False) or TENANT_PLATFORM_ID)
    except Exception:
        return str(TENANT_PLATFORM_ID)

def _v152_tenant_row(tenant_id: str) -> dict:
    try:
        return tenant_get(str(tenant_id)) or {}
    except Exception:
        return {}

def _v152_tenant_permissions(tenant_id: str) -> dict:
    row = _v152_tenant_row(tenant_id)
    settings = row.setdefault('settings', {})
    permissions = settings.setdefault('chat_permissions_v152_defaults', {})
    return permissions if isinstance(permissions, dict) else {}

def _v152_chat_policy(chat_id: int) -> dict:
    store = get_chat_store(int(chat_id))
    settings = store.setdefault('settings', {})
    policy = settings.setdefault('chat_permissions_v152', {})
    if not isinstance(policy, dict):
        policy = {}
        settings['chat_permissions_v152'] = policy
    policy.setdefault('inherit_tenant', True)
    policy.setdefault('overrides', {})
    policy.setdefault('updated_at', '')
    policy.setdefault('updated_by', 0)
    return policy

def v152_global_permission_allowed(capability: str) -> bool:
    if capability not in V152_PERMISSION_LABELS:
        return True
    return bool((_v152_permissions_root().get('global') or {}).get(capability, True))

def v152_tenant_permission_allowed(tenant_id: str, capability: str) -> bool:
    if not v152_global_permission_allowed(capability):
        return False
    return bool(_v152_tenant_permissions(str(tenant_id)).get(capability, True))

def v152_chat_permission_allowed(chat_id: int, capability: str) -> bool:
    capability = str(capability or '')
    if capability not in V152_PERMISSION_LABELS:
        return True
    tid = _v152_tenant_id_for_chat(int(chat_id))
    if not v152_global_permission_allowed(capability):
        return False
    policy = _v152_chat_policy(int(chat_id))
    if bool(policy.get('inherit_tenant', True)):
        return v152_tenant_permission_allowed(tid, capability)
    overrides = policy.get('overrides') if isinstance(policy.get('overrides'), dict) else {}
    return bool(overrides.get(capability, v152_tenant_permission_allowed(tid, capability)))

def _v152_actor_id(obj=None) -> int:
    try:
        return int(getattr(getattr(obj, 'from_user', None), 'id', 0) or tenant_current_actor_user_id() or 0)
    except Exception:
        return 0

def _v152_actor_is_platform_owner(user_id: int) -> bool:
    try:
        return bool(tenant_is_platform_owner_user(int(user_id)))
    except Exception:
        return bool(int(user_id or 0) == int(OWNER_ID or 0))

def _v152_actor_can_manage_tenant(user_id: int, tenant_id: str) -> bool:
    if _v152_actor_is_platform_owner(user_id):
        return True
    try:
        return bool(tenant_can_manage(int(user_id), str(tenant_id)))
    except Exception:
        return False

def _v152_actor_can_manage_chat(user_id: int, chat_id: int) -> bool:
    return _v152_actor_can_manage_tenant(int(user_id), _v152_tenant_id_for_chat(int(chat_id)))

def _v152_persist(reason: str, chat_id: int | None=None, tenant_id: str | None=None, actor_id: int=0) -> None:
    now = now_local().isoformat(timespec='seconds') if 'now_local' in globals() else _v152_datetime.now().isoformat(timespec='seconds')
    row = {'at': now, 'reason': str(reason), 'chat_id': int(chat_id or 0), 'tenant_id': str(tenant_id or ''), 'actor_id': int(actor_id or 0)}
    history = _v152_permissions_root().setdefault('history', [])
    history.append(row)
    del history[:-500]
    try:
        save_data(data, root_only=True)
    except TypeError:
        save_data(data)
    try:
        root_chat = int(_v152_tenant_row(tenant_id or _v152_tenant_id_for_chat(int(chat_id or 0))).get('root_chat_id') or OWNER_ID or chat_id or 0)
        if root_chat:
            schedule_delta_backup(root_chat, delay=0.35, reason=f'chat_permissions_v152:{reason}')
    except Exception:
        pass
    try:
        bot_journal('chat_permissions_v152_changed', int(chat_id or OWNER_ID or 0), f"reason={reason}; tenant={tenant_id or ''}; actor={int(actor_id or 0)}")
    except Exception:
        pass

def _v152_set_global(capability: str, enabled: bool, actor_id: int) -> bool:
    if not _v152_actor_is_platform_owner(actor_id) or capability not in V152_PERMISSION_LABELS:
        return False
    _v152_permissions_root().setdefault('global', {})[capability] = bool(enabled)
    _v152_persist(f'global:{capability}={int(bool(enabled))}', tenant_id=TENANT_PLATFORM_ID, actor_id=actor_id)
    return True

def _v152_set_tenant(tenant_id: str, capability: str, enabled: bool, actor_id: int) -> bool:
    if not _v152_actor_can_manage_tenant(actor_id, tenant_id) or capability not in V152_PERMISSION_LABELS:
        return False
    if enabled and (not v152_global_permission_allowed(capability)):
        return False
    _v152_tenant_permissions(tenant_id)[capability] = bool(enabled)
    _v152_persist(f'tenant:{capability}={int(bool(enabled))}', tenant_id=tenant_id, actor_id=actor_id)
    return True

def _v152_set_chat(chat_id: int, capability: str, enabled: bool, actor_id: int) -> bool:
    if not _v152_actor_can_manage_chat(actor_id, chat_id) or capability not in V152_PERMISSION_LABELS:
        return False
    if enabled and (not v152_global_permission_allowed(capability)):
        return False
    policy = _v152_chat_policy(chat_id)
    if bool(policy.get('inherit_tenant', True)):
        return False
    policy.setdefault('overrides', {})[capability] = bool(enabled)
    policy['updated_at'] = now_local().isoformat(timespec='seconds')
    policy['updated_by'] = int(actor_id)
    _v152_persist(f'chat:{capability}={int(bool(enabled))}', chat_id=chat_id, tenant_id=_v152_tenant_id_for_chat(chat_id), actor_id=actor_id)
    return True
V152_PRESETS = {'all': set(V152_PERMISSION_KEYS), 'none': set(), 'finance': {key for key in V152_PERMISSION_KEYS if key.startswith('finance.')} | {'exports.excel_chat', 'exports.reports', 'settings.info'}, 'view': {'finance.view_totals', 'finance.view_month', 'exports.journals', 'exports.reports', 'reminders.use', 'settings.info'}, 'standard': {'finance.mode', 'finance.ars', 'finance.usd', 'finance.gomonk', 'finance.view_totals', 'finance.view_month', 'exports.excel_chat', 'exports.reports', 'reminders.use', 'reminders.complete', 'forward.messages', 'forward.media_groups', 'settings.info'}, 'locked': {'finance.view_totals', 'finance.view_month', 'exports.journals', 'exports.reports', 'reminders.use', 'settings.info', 'settings.diagnostics'}}
V152_PRESET_LABELS = {'all': '✅ Включить всё', 'none': '⬜ Выключить всё', 'finance': '💰 Только финансы', 'view': '👁 Только просмотр', 'standard': '🧑\u200d💼 Стандартный чат', 'locked': '🔒 Заблокировать изменения'}

def _v152_apply_preset(scope: str, target: str | int, preset: str, actor_id: int) -> bool:
    enabled = V152_PRESETS.get(str(preset))
    if enabled is None:
        return False
    values = {key: bool(key in enabled and v152_global_permission_allowed(key)) for key in V152_PERMISSION_KEYS}
    if scope == 'global':
        if not _v152_actor_is_platform_owner(actor_id):
            return False
        _v152_permissions_root()['global'] = {key: key in enabled for key in V152_PERMISSION_KEYS}
        _v152_persist(f'global_preset:{preset}', tenant_id=TENANT_PLATFORM_ID, actor_id=actor_id)
        return True
    if scope == 'tenant':
        tenant_id = str(target)
        if not _v152_actor_can_manage_tenant(actor_id, tenant_id):
            return False
        _v152_tenant_row(tenant_id).setdefault('settings', {})['chat_permissions_v152_defaults'] = dict(values)
        _v152_persist(f'tenant_preset:{preset}', tenant_id=tenant_id, actor_id=actor_id)
        return True
    chat_id = int(target)
    if not _v152_actor_can_manage_chat(actor_id, chat_id):
        return False
    policy = _v152_chat_policy(chat_id)
    policy['inherit_tenant'] = False
    policy['overrides'] = dict(values)
    policy['updated_at'] = now_local().isoformat(timespec='seconds')
    policy['updated_by'] = int(actor_id)
    _v152_persist(f'chat_preset:{preset}', chat_id=chat_id, tenant_id=_v152_tenant_id_for_chat(chat_id), actor_id=actor_id)
    return True

def _v152_toggle_chat_inheritance(chat_id: int, actor_id: int) -> bool:
    if not _v152_actor_can_manage_chat(actor_id, chat_id):
        return False
    policy = _v152_chat_policy(chat_id)
    old = bool(policy.get('inherit_tenant', True))
    if old:
        tid = _v152_tenant_id_for_chat(chat_id)
        policy['overrides'] = {key: v152_tenant_permission_allowed(tid, key) for key in V152_PERMISSION_KEYS}
        policy['inherit_tenant'] = False
    else:
        policy['inherit_tenant'] = True
    policy['updated_at'] = now_local().isoformat(timespec='seconds')
    policy['updated_by'] = int(actor_id)
    _v152_persist(f'chat_inherit={int(not old)}', chat_id=chat_id, tenant_id=_v152_tenant_id_for_chat(chat_id), actor_id=actor_id)
    return True

def _v152_accessible_chats(user_id: int, context_chat_id: int) -> list[int]:
    if _v152_actor_is_platform_owner(user_id):
        out = []
        try:
            for tenant in tenant_all():
                for cid in tenant.get('chat_ids') or []:
                    if int(cid) not in out:
                        out.append(int(cid))
        except Exception:
            pass
        return sorted(out, key=lambda cid: str(get_chat_display_name(cid) or cid).casefold())
    tid = _v152_tenant_id_for_chat(context_chat_id)
    if not _v152_actor_can_manage_tenant(user_id, tid):
        return []
    try:
        return list(tenant_chat_ids(tid))
    except Exception:
        return []

def _v152_short(text: str, limit: int=38) -> str:
    text = ' '.join(str(text or '').split())
    return text if len(text) <= limit else text[:limit - 1] + '…'

def build_v152_chat_rights_list_text(user_id: int, context_chat_id: int, page: int=0) -> str:
    chats = _v152_accessible_chats(user_id, context_chat_id)
    pages = max(1, (len(chats) + 9) // 10)
    page = max(0, min(int(page), pages - 1))
    return f'🛡 ПРАВА ЧАТОВ · Ф206\n\nПрава применяются внутри обработчиков команд и callback, а не только скрывают кнопки.\nГлобальный запрет владельца платформы имеет приоритет над пространством и чатом.\n\nДоступных чатов: {len(chats)}\nСтраница: {page + 1}/{pages}'

def build_v152_chat_rights_list_keyboard(user_id: int, context_chat_id: int, page: int=0):
    chats = _v152_accessible_chats(user_id, context_chat_id)
    pages = max(1, (len(chats) + 9) // 10)
    page = max(0, min(int(page), pages - 1))
    kb = types.InlineKeyboardMarkup(row_width=1)
    if _v152_actor_is_platform_owner(user_id):
        kb.row(IB('🌐 Ограничения платформы', callback_data='v152:r:g:0'))
    tid = _v152_tenant_id_for_chat(context_chat_id)
    if _v152_actor_can_manage_tenant(user_id, tid):
        kb.row(IB('🏢 Права пространства', callback_data=f'v152:r:t:{tid}:0'))
    for cid in chats[page * 10:page * 10 + 10]:
        tenant = _v152_tenant_row(_v152_tenant_id_for_chat(cid))
        root = '⭐ ' if int((tenant or {}).get('root_chat_id') or 0) == int(cid) else ''
        kb.row(IB(root + _v152_short(get_chat_display_name(cid) or f'Чат {cid}'), callback_data=f'v152:r:c:{int(cid)}:0'))
    if pages > 1:
        nav = []
        if page > 0:
            nav.append(IB('⬅️', callback_data=f'v152:r:l:{page - 1}'))
        nav.append(IB(f'{page + 1}/{pages}', callback_data='none'))
        if page + 1 < pages:
            nav.append(IB('➡️', callback_data=f'v152:r:l:{page + 1}'))
        kb.row(*nav)
    kb.row(IB('⬅️ К защите', callback_data='safety_profile_open'))
    return kb

def _v152_scope_value(scope: str, target: str | int, capability: str) -> bool:
    if scope == 'global':
        return v152_global_permission_allowed(capability)
    if scope == 'tenant':
        return v152_tenant_permission_allowed(str(target), capability)
    return v152_chat_permission_allowed(int(target), capability)

def _v152_scope_title(scope: str, target: str | int) -> str:
    if scope == 'global':
        return '🌐 ОГРАНИЧЕНИЯ ПЛАТФОРМЫ'
    if scope == 'tenant':
        row = _v152_tenant_row(str(target))
        return f"🏢 ПРАВА ПРОСТРАНСТВА\n{row.get('name') or target}"
    chat_id = int(target)
    return f'💬 ПРАВА ЧАТА\n{get_chat_display_name(chat_id) or chat_id}'

def build_v152_permission_text(scope: str, target: str | int) -> str:
    allowed = sum((1 for key in V152_PERMISSION_KEYS if _v152_scope_value(scope, target, key)))
    lines = [_v152_scope_title(scope, target), '', f'Разрешено: {allowed}/{len(V152_PERMISSION_KEYS)}']
    if scope == 'chat':
        policy = _v152_chat_policy(int(target))
        lines.append(f"Наследовать настройки пространства: {('✅ включено' if policy.get('inherit_tenant', True) else '⬜ выключено')}")
        if policy.get('inherit_tenant', True):
            lines.append('Чтобы менять отдельные функции этого чата, сначала выключите наследование.')
    if scope != 'global':
        locked = [V152_PERMISSION_LABELS[key] for key in V152_PERMISSION_KEYS if not v152_global_permission_allowed(key)]
        if locked:
            lines.append(f'Глобально заблокировано: {len(locked)}')
    return '\n'.join(lines)

def build_v152_permission_keyboard(scope: str, target: str | int, page: int=0):
    kb = types.InlineKeyboardMarkup(row_width=1)
    if scope == 'chat':
        policy = _v152_chat_policy(int(target))
        kb.row(IB(f"Наследовать настройки пространства: {('✅ ВКЛ' if policy.get('inherit_tenant', True) else '⬜ ВЫКЛ')}", callback_data=f'v152:r:i:{int(target)}:{int(page)}'))
    for preset in ('all', 'none', 'finance', 'view', 'standard', 'locked'):
        kb.row(IB(V152_PRESET_LABELS[preset], callback_data=f'v152:r:p:{scope[0]}:{target}:{preset}:{int(page)}'))
    inherited = scope == 'chat' and bool(_v152_chat_policy(int(target)).get('inherit_tenant', True))
    for _group, group_label, items in V152_PERMISSION_GROUPS:
        kb.row(IB(group_label, callback_data='none'))
        for capability, label in items:
            enabled = _v152_scope_value(scope, target, capability)
            locked = scope != 'global' and (not v152_global_permission_allowed(capability))
            prefix = '🔒' if locked else '✅' if enabled else '⬜'
            suffix = ' · наследуется' if inherited else ''
            idx = V152_PERMISSION_INDEX[capability]
            kb.row(IB(f'{prefix} {label}{suffix}', callback_data=f'v152:r:x:{scope[0]}:{target}:{idx}:{int(page)}'))
    kb.row(IB('⬅️ К списку чатов', callback_data=f'v152:r:l:{int(page)}'))
    return kb
_V152_ORIG_BUILD_INFO_KEYBOARD = _v177_legacy_0217_build_info_keyboard

def _v177_legacy_0218_build_info_keyboard(chat_id: int):
    kb = _V152_ORIG_BUILD_INFO_KEYBOARD(int(chat_id))
    try:
        for row in getattr(kb, 'keyboard', None) or getattr(kb, 'inline_keyboard', None) or []:
            for button in row:
                if isinstance(button, dict):
                    if button.get('callback_data') == 'safety_profile_toggle':
                        button['callback_data'] = 'safety_profile_open'
                elif getattr(button, 'callback_data', None) == 'safety_profile_toggle':
                    button.callback_data = 'safety_profile_open'
    except Exception:
        pass
    return kb
try:
    _v177_legacy_0218_build_info_keyboard.__name__ = 'build_info_keyboard'
except Exception:
    pass
_V152_ORIG_BUILD_SAFETY_KEYBOARD = _v177_legacy_0225_build_safety_profile_keyboard

def _canon_build_safety_profile_keyboard__001(chat_id: int):
    kb = types.InlineKeyboardMarkup(row_width=1)
    kb.row(IB(f"🔄 По-старому/по-новому · сейчас {('ПО-НОВОМУ' if safety_profile_new_enabled() else 'ПО-СТАРОМУ')}", callback_data='safety_profile_toggle'))
    kb.row(IB('🛡 Права чатов', callback_data='v152:r:l:0'))
    kb.row(IB('👥 Права пользователей', callback_data='security_roles:0'))
    day = get_chat_store(int(chat_id)).get('current_view_day') or today_key()
    kb.row(IB('🔙 Назад в Инфо', callback_data=f'd:{day}:info'))
    return kb

def v152_callback_capability(action: str) -> str | None:
    raw = str(action or '')
    value = raw.split(':', 2)[2] if raw.startswith('d:') and raw.count(':') >= 2 else raw
    low = value.casefold()
    if low.startswith('v152:r:'):
        return None
    if any((x in low for x in ('journal', 'log_file', 'errors_file', 'failed', 'problem_tasks'))):
        return 'exports.journals'
    if 'google' in low:
        if any((x in low for x in ('drive', 'folder', 'upload_drive'))):
            return 'exports.google_drive'
        return 'exports.google_sheets'
    if any((x in low for x in ('excel', 'xlsx', 'csv', 'tabl_lsx', 'download'))):
        return 'exports.excel_chat'
    if any((x in low for x in ('report', 'summary', 'itog'))):
        return 'exports.reports'
    if low.startswith(('rem:add', 'reminder_add')):
        return 'reminders.create'
    if low.startswith(('rem:delete', 'rem:del', 'reminder_delete')):
        return 'reminders.delete'
    if low.startswith(('rem:edit', 'rem:save', 'reminder_edit')):
        return 'reminders.edit'
    if any((x in low for x in ('v149:rem:done', 'vyapl'))):
        return 'reminders.complete'
    if low.startswith(('rem:', 'reminder', 'v149:rem:')):
        return 'reminders.use'
    if any((x in low for x in ('media_group', 'mediagroup', 'album'))) and low.startswith(('fw', 'fwd', 'forward')):
        return 'forward.media_groups'
    if low.startswith(('fw', 'fwd', 'forward', 'stopforward')):
        return 'forward.messages'
    if low.startswith(('sp:chatlink', 'tenant_chat_link', 'space_chat_link', 'sp:unlink')):
        return 'chats.connect_children'
    if low.startswith(('sp:userlink', 'tenant_user', 'space_user')):
        return 'chats.manage_users'
    if low.startswith(('sp:role', 'sp:transfer', 'tenant_role', 'space_role')):
        return 'chats.manage_roles'
    if 'gomonk' in low:
        return 'finance.gomonk'
    if any((x in low for x in ('usd_month', 'month_usd', 'usd:month', 'month_view'))):
        return 'finance.view_month'
    if any((x in low for x in ('usd', 'currency_usd'))):
        return 'finance.usd'
    if any((x in low for x in ('delete', 'del_selected', 'remove_record'))):
        return 'finance.delete'
    if any((x in low for x in ('edit', 'izm', 'record_change'))):
        return 'finance.edit'
    if any((x in low for x in ('balance', 'totals', 'ostatok'))):
        return 'finance.view_totals'
    if any((x in low for x in ('finance_mode', 'info_finance', 'finmode'))):
        return 'finance.mode'
    if 'expense_shortcut' in low or 'iphone' in low:
        return 'settings.iphone'
    if any((x in low for x in ('runtime', 'diagnostic', 'diag', 'queues', 'delta_status'))):
        return 'settings.diagnostics'
    if any((x in low for x in ('mega_', 'restore', 'backup', 'sqlite', 'db'))):
        return 'settings.backup_recovery'
    if any((x in low for x in ('audit', 'integrity'))):
        return 'settings.audit'
    if any((x in low for x in ('window', 'okna', 'buttons_current'))):
        return 'settings.windows'
    if low in {'info', 'info_open'} or low.endswith(':info'):
        return 'settings.info'
    if any((x in low for x in ('toggle', 'setting', 'style', 'mode'))):
        return 'settings.change'
    return None
_V152_ORIG_SAFETY_PERMISSION_ALLOWED = _v177_legacy_0111_safety_permission_allowed

def _canon_safety_permission_allowed__001(user_id: int | None, chat_id: int | None, action: str) -> bool:
    try:
        uid, cid = (int(user_id or 0), int(chat_id or 0))
    except Exception:
        return False
    if _v152_actor_is_platform_owner(uid):
        return True
    capability = v152_callback_capability(action)
    if capability:
        tid = _v152_tenant_id_for_chat(cid)
        role = tenant_role_for_user(uid, tid)
        if role not in {'tenant_owner', 'tenant_admin', 'operator', 'viewer', 'standard'}:
            return False
        mutating = capability not in {'finance.view_totals', 'finance.view_month', 'exports.journals', 'exports.reports', 'reminders.use', 'settings.info', 'settings.diagnostics', 'settings.audit'}
        if mutating and role in {'viewer', 'standard'}:
            return False
        return v152_chat_permission_allowed(cid, capability)
    if callable(_V152_ORIG_SAFETY_PERMISSION_ALLOWED):
        return bool(_V152_ORIG_SAFETY_PERMISSION_ALLOWED(uid, cid, action))
    return True
_V152_ORIG_SECURITY_USER_ALLOWED = _v177_legacy_0109_security_user_allowed

def _canon_security_user_allowed__001(user_id: int | None, capability: str) -> bool:
    if callable(_V152_ORIG_SECURITY_USER_ALLOWED) and (not _V152_ORIG_SECURITY_USER_ALLOWED(user_id, capability)):
        return False
    try:
        cid = int(current_state_chat_id() or 0)
    except Exception:
        cid = 0
    if not cid or _v152_actor_is_platform_owner(int(user_id or 0)):
        return True
    fine = {'finance_input': 'finance.usd' if usd_transactions_view_enabled(cid) else 'finance.ars', 'finance_manage': 'finance.edit', 'export': 'exports.excel_chat', 'forward_manage': 'forward.messages', 'reminder_manage': 'reminders.use', 'view': 'settings.info'}.get(str(capability or ''))
    return v152_chat_permission_allowed(cid, fine) if fine else True

def v152_command_capability(command: str) -> str | None:
    cmd = str(command or '').strip().casefold().lstrip('/').split('@', 1)[0]
    if _v152_re.fullmatch('vyapl(?:_\\d+)?', cmd):
        return 'reminders.complete'
    maps = {'finance.mode': {'buttons'}, 'finance.view_totals': {'balance', 'ok', 'поехали'}, 'finance.view_month': {'prev', 'next'}, 'exports.excel_chat': {'csv', 'xlsx', 'excel', 'tabl_lsx', 'json'}, 'exports.journals': {'journal', 'log', 'logs', 'errors', 'bot_errors'}, 'exports.reports': {'report'}, 'exports.google_sheets': {'google', 'google_space', 'google_tenant', 'google_connect', 'google_sheet', 'google_email'}, 'exports.google_drive': {'google_drive'}, 'reminders.complete': {'vyapl_history'}, 'forward.messages': {'stopforward'}, 'chats.connect_children': {'space_chat_link', 'tenant_chat_link', 'space_join', 'tenant_join', 'space_unlink', 'tenant_unlink', 'space_claim', 'tenant_claim'}, 'chats.manage_users': {'space_user_link', 'tenant_user_link', 'space_users', 'tenant_users'}, 'chats.manage_roles': {'space_role', 'tenant_role', 'space_transfer', 'tenant_transfer'}, 'settings.change': {'space_rename', 'tenant_rename', 'space_create', 'tenant_create', 'off_on_backup_excel'}, 'settings.windows': {'windows', 'okna', 'окна'}, 'settings.info': {'space', 'spaces', 'tenant', 'пространство', 'пространства', 'space_chats', 'tenant_chats', 'help', 'start'}, 'settings.diagnostics': {'diag', 'diagnostics', 'queues', 'queue_status', 'delta_status', 'runtime_export', 'mega_status', 'chat_status', 'chat_history'}, 'settings.backup_recovery': {'backup_channel_on', 'backup_channel_off', 'mega_backup_now', 'mega_restore_now', 'restore', 'restore_off', 'restore_guard', 'restore_guard_on', 'restore_guard_off', 'sqlite', 'db', 'chat_archive', 'chat_restore'}, 'settings.audit': {'command_audit', 'articles', 'статьи'}}
    for capability, commands in maps.items():
        if cmd in commands:
            return capability
    return None

def _v152_command_allowed(msg, capability: str) -> bool:
    uid = _v152_actor_id(msg)
    if _v152_actor_is_platform_owner(uid):
        return True
    try:
        cid = int(msg.chat.id)
    except Exception:
        return False
    role = tenant_role_for_user(uid, _v152_tenant_id_for_chat(cid))
    mutating = capability not in {'finance.view_totals', 'finance.view_month', 'exports.journals', 'exports.reports', 'reminders.use', 'settings.info', 'settings.diagnostics', 'settings.audit'}
    if mutating and role in {'viewer', 'standard'}:
        return False
    return v152_chat_permission_allowed(cid, capability)

def _v152_install_command_wrappers() -> int:
    wrapped = 0
    handlers = getattr(bot, 'message_handlers', None)
    if not isinstance(handlers, list):
        return 0
    for handler in handlers:
        if not isinstance(handler, dict):
            continue
        original = handler.get('function')
        if not callable(original) or getattr(original, '_v152_permission_wrapped', False):
            continue
        if getattr(original, '__name__', '') == 'on_any_message':
            continue

        @_v152_functools.wraps(original)
        def guarded(message, *args, __original=original, **kwargs):
            text = str(getattr(message, 'text', '') or '').strip()
            if text.startswith('/'):
                command = text.split(None, 1)[0]
                capability = v152_command_capability(command)
                if capability and (not _v152_command_allowed(message, capability)):
                    try:
                        send_and_auto_delete(int(message.chat.id), f'⛔ Для этого чата запрещено: {V152_PERMISSION_LABELS.get(capability, capability)}.', 10)
                        bot_journal('chat_permission_command_denied', int(message.chat.id), f'user={_v152_actor_id(message)} command={command} capability={capability}', 'WARN')
                    except Exception:
                        pass
                    return None
            return __original(message, *args, **kwargs)
        guarded._v152_permission_wrapped = True
        handler['function'] = guarded
        wrapped += 1
    return wrapped
_V152_ORIG_HANDLE_GOMONK_INSERT = _v177_legacy_0162_handle_gomonk_insert_message

def _canon_handle_gomonk_insert_message__001(msg):
    cid = int(msg.chat.id)
    uid = _v152_actor_id(msg)
    if not _v152_actor_is_platform_owner(uid) and (not v152_chat_permission_allowed(cid, 'finance.gomonk')):
        try:
            send_and_auto_delete(cid, '⛔ Изменение гомонковых запрещено правами этого чата.', 8)
        except Exception:
            pass
        return False
    return _V152_ORIG_HANDLE_GOMONK_INSERT(msg) if callable(_V152_ORIG_HANDLE_GOMONK_INSERT) else False
_V152_ORIG_SCHEDULE_FORWARD = _v177_legacy_0001_schedule_forward_any_message

def _canon_schedule_forward_any_message__001(chat_id: int, msg):
    cid = int(chat_id)
    uid = _v152_actor_id(msg)
    capability = 'forward.media_groups' if getattr(msg, 'media_group_id', None) else 'forward.messages'
    if not _v152_actor_is_platform_owner(uid) and (not v152_chat_permission_allowed(cid, capability)):
        try:
            bot_journal('chat_permission_forward_blocked', cid, f'user={uid}; capability={capability}', 'WARN')
        except Exception:
            pass
        return None
    return _V152_ORIG_SCHEDULE_FORWARD(cid, msg) if callable(_V152_ORIG_SCHEDULE_FORWARD) else None

class _V152NamedFileProxy:

    def __init__(self, wrapped, name: str):
        self._wrapped = wrapped
        self.name = str(name)

    def __getattr__(self, item):
        return getattr(self._wrapped, item)

    def read(self, *args, **kwargs):
        return self._wrapped.read(*args, **kwargs)

    def seek(self, *args, **kwargs):
        return self._wrapped.seek(*args, **kwargs)

    def tell(self, *args, **kwargs):
        return self._wrapped.tell(*args, **kwargs)

    def __iter__(self):
        return iter(self._wrapped)

def _v152_file_text(document, caption: str='', purpose: str='') -> tuple[str, str]:
    name = ''
    try:
        name = str(getattr(document, 'name', '') or getattr(document, 'file_name', '') or '')
    except Exception:
        pass
    return (name, f"{name} {caption or ''} {purpose or ''}".casefold())

def _v152_without_version_noise(text: str) -> str:
    """Remove version/build tokens before semantic filename classification.

    v169 contained the word ``forward`` in VERSION itself.  The old classifier searched
    the whole filename/caption and therefore renamed unrelated downloads (TZ export,
    current-version journal and even the bot source) to ``Журнал_пересылки``.
    Classification must be based on the actual export purpose, not on words inside the
    release name.
    """
    low = str(text or '').casefold()
    try:
        ver = str(globals().get('VERSION') or '').casefold().strip()
        if ver:
            low = low.replace(ver, ' ')
    except Exception:
        pass
    low = _v152_re.sub('\\bbot_v\\d+[0-9a-z_\\-]*\\b', ' ', low)
    low = _v152_re.sub('\\bv\\d+_[0-9a-z_\\-]+\\b', ' ', low)
    low = _v152_re.sub('\\s+', ' ', low).strip()
    return low

def _v152_download_kind(document, caption: str='', purpose: str='') -> str | None:
    """Return a unique human category for operational downloads.

    The order is intentional: explicit export types win before generic journal keywords.
    Financial XLSX/CSV exports are *not* journals and keep their own existing filenames.
    """
    name, raw_low = _v152_file_text(document, caption, purpose)
    low = _v152_without_version_noise(raw_low)
    base = _v152_os.path.basename(str(name or '')).casefold()
    ext = _v152_os.path.splitext(base)[1].lower()
    if ext == '.py' or 'исходник текущего деплоя' in low or 'исходник бота' in low:
        return 'Исходник_бота'
    if 'архив тз' in low or 'архив_тз_окон' in low:
        return 'ТЗ_окон_архив'
    if 'тз по окнам' in low or 'тз_окон_текущ' in low or 'тз_окон' in base:
        return 'ТЗ_окон_текущая_версия'
    if 'маркировки окон' in low or 'маркировки_окон' in base:
        return 'Маркировки_окон'
    if 'runtime mega zip' in low or base.startswith('runtime_export_'):
        return 'Диагностика_Runtime_MEGA'
    if 'журнал текущей версии' in low or 'журнал текущей версии бота' in low:
        return 'Журнал_текущей_версии'
    if any((x in low for x in ('максимальный диагностический журнал', 'диагностический журнал', 'diagnostic', 'diagnostics'))):
        return 'Журнал_диагностики'
    if any((x in low for x in ('failed', 'problem_tasks', 'проблемные задачи', 'проблемных задач'))):
        return 'Журнал_FAILED_задач'
    if any((x in low for x in ('журнал ошибок', 'error journal', 'errors journal', 'журнал_ошибок'))):
        return 'Журнал_ошибок'
    if any((x in low for x in ('журнал восстановления', 'recovery journal', 'restore journal', 'журнал_восстановления'))):
        return 'Журнал_восстановления'
    if any((x in low for x in ('журнал пересылки', 'forward journal', 'forwarding journal', 'журнал_пересылки'))):
        return 'Журнал_пересылки'
    if any((x in low for x in ('журнал аудита', 'audit journal', 'integrity journal', 'журнал_аудита'))):
        return 'Журнал_аудита'
    if any((x in low for x in ('журнал backup', 'журнал бэкап', 'backup journal', 'журнал резерв', 'журнал_backup'))):
        return 'Журнал_резервных_копий'
    if any((x in low for x in ('журнал финансов', 'финансовый журнал', 'finance journal', 'журнал_финансов'))):
        return 'Журнал_финансов'
    if any((x in low for x in ('журнал операций', 'журнал действий', 'action journal', 'operations journal', 'журнал_операций'))):
        return 'Журнал_операций'
    if base.startswith('journal_') or ' журнал ' in f' {low} ':
        return 'Журнал_операций'
    return None

def _v152_journal_kind(document, caption: str='', purpose: str='') -> str | None:
    """Compatibility alias retained for older modules."""
    return _v152_download_kind(document, caption, purpose)

def _v152_filename_component(value: str, fallback: str='Чат') -> str:
    text = str(value or fallback).strip()
    text = _v152_re.sub('[\\\\/:*?\\"<>|]+', '-', text)
    text = _v152_re.sub('\\s+', '-', text)
    text = _v152_re.sub('-+', '-', text).strip('-._')
    if not _v152_re.search('[0-9A-Za-zА-Яа-яЁё]', text):
        text = str(fallback or 'Чат')
    return (text or fallback)[:80]

def _v152_scope_name(recipient_chat_id: int, kind: str) -> str:
    try:
        tid = _v152_tenant_id_for_chat(int(recipient_chat_id))
        tenant = _v152_tenant_row(tid)
        system_scope_kinds = {'Журнал_FAILED_задач', 'Журнал_диагностики', 'Журнал_аудита', 'Диагностика_Runtime_MEGA', 'Журнал_текущей_версии', 'ТЗ_окон_текущая_версия', 'ТЗ_окон_архив', 'Маркировки_окон'}
        if kind in system_scope_kinds and tenant:
            return _v152_filename_component(tenant.get('name') or tid, 'Пространство')
    except Exception:
        pass
    try:
        return _v152_filename_component(get_chat_display_name(int(recipient_chat_id)) or f'Чат-{recipient_chat_id}', f'Чат-{recipient_chat_id}')
    except Exception:
        return _v152_filename_component(f'Чат-{recipient_chat_id}')

def _v152_period_suffix(document, caption: str='', purpose: str='') -> str:
    name, _low = _v152_file_text(document, caption, purpose)
    source = f"{name} {caption or ''} {purpose or ''}"
    dates = []
    for y, m, d in _v152_re.findall('(?<!\\d)(20\\d{2})[-_]?([01]\\d)[-_]?([0-3]\\d)(?!\\d)', source):
        value = f'{y}-{m}-{d}'
        if value not in dates:
            dates.append(value)
    if len(dates) >= 2:
        return f'{dates[0]}_{dates[-1]}'
    if len(dates) == 1:
        return dates[0]
    try:
        return now_local().strftime('%Y-%m-%d')
    except Exception:
        return _v152_datetime.now().strftime('%Y-%m-%d')

def _v177_legacy_0277_v152_human_download_name(recipient_chat_id: int, document, caption: str='', purpose: str='') -> str | None:
    kind = _v152_download_kind(document, caption, purpose)
    if not kind:
        return None
    old_name = str(getattr(document, 'name', '') or getattr(document, 'file_name', '') or '')
    ext = _v152_os.path.splitext(old_name)[1].lower()
    if kind == 'Исходник_бота':
        safe_ver = _v152_filename_component(str(globals().get('VERSION') or 'текущая-версия'), 'текущая-версия')
        return f'Исходник_бота_{safe_ver}_{_v152_period_suffix(document, caption, purpose)}.py'
    if ext not in {'.txt', '.csv', '.zip', '.json', '.xlsx', '.gz', '.sqlite3', '.py'}:
        ext = '.zip' if kind in {'Журнал_FAILED_задач', 'Диагностика_Runtime_MEGA'} else '.txt'
    scope = _v152_scope_name(int(recipient_chat_id), kind)
    period = _v152_period_suffix(document, caption, purpose)
    return f'{kind}_{scope}_{period}{ext}'
try:
    _v177_legacy_0277_v152_human_download_name.__name__ = 'v152_human_download_name'
except Exception:
    pass
# FINALIZED: v152 download naming is applied by the single final send_document transport.

def _v152_answer(call, text: str='', alert: bool=False):
    try:
        bot.answer_callback_query(call.id, text or None, show_alert=bool(alert))
    except Exception:
        pass

def _v152_edit_rights(call, scope: str, target: str | int, page: int=0):
    safe_edit(bot, call, build_v152_permission_text(scope, target), reply_markup=build_v152_permission_keyboard(scope, target, page))

def _v152_handle_rights_callback(call, data_str: str) -> bool:
    if not str(data_str).startswith('v152:r:'):
        return False
    chat_id = int(call.message.chat.id)
    user_id = _v152_actor_id(call)
    parts = str(data_str).split(':')
    try:
        action = parts[2]
        if action == 'l':
            page = int(parts[3]) if len(parts) > 3 else 0
            if not (_v152_actor_is_platform_owner(user_id) or _v152_actor_can_manage_tenant(user_id, _v152_tenant_id_for_chat(chat_id))):
                _v152_answer(call, 'Недостаточно прав', True)
                return True
            safe_edit(bot, call, build_v152_chat_rights_list_text(user_id, chat_id, page), reply_markup=build_v152_chat_rights_list_keyboard(user_id, chat_id, page))
            return True
        if action == 'g':
            if not _v152_actor_is_platform_owner(user_id):
                _v152_answer(call, 'Только владелец платформы', True)
                return True
            _v152_edit_rights(call, 'global', 'platform', int(parts[3]) if len(parts) > 3 else 0)
            return True
        if action == 't':
            tenant_id = parts[3]
            page = int(parts[4]) if len(parts) > 4 else 0
            if not _v152_actor_can_manage_tenant(user_id, tenant_id):
                _v152_answer(call, 'Чужое пространство', True)
                return True
            _v152_edit_rights(call, 'tenant', tenant_id, page)
            return True
        if action == 'c':
            target_chat = int(parts[3])
            page = int(parts[4]) if len(parts) > 4 else 0
            if not _v152_actor_can_manage_chat(user_id, target_chat):
                _v152_answer(call, 'Чужой чат', True)
                return True
            _v152_edit_rights(call, 'chat', target_chat, page)
            return True
        if action == 'i':
            target_chat = int(parts[3])
            page = int(parts[4]) if len(parts) > 4 else 0
            if not _v152_toggle_chat_inheritance(target_chat, user_id):
                _v152_answer(call, 'Не удалось изменить наследование', True)
                return True
            _v152_answer(call, 'Наследование изменено')
            _v152_edit_rights(call, 'chat', target_chat, page)
            return True
        if action == 'p':
            scope_code, target, preset = (parts[3], parts[4], parts[5])
            page = int(parts[6]) if len(parts) > 6 else 0
            scope = {'g': 'global', 't': 'tenant', 'c': 'chat'}.get(scope_code)
            real_target = int(target) if scope == 'chat' else target
            if not scope or not _v152_apply_preset(scope, real_target, preset, user_id):
                _v152_answer(call, 'Пресет недоступен', True)
                return True
            _v152_answer(call, 'Права применены')
            _v152_edit_rights(call, scope, real_target, page)
            return True
        if action == 'x':
            scope_code, target, idx_raw = (parts[3], parts[4], parts[5])
            page = int(parts[6]) if len(parts) > 6 else 0
            idx = int(idx_raw)
            if idx < 0 or idx >= len(V152_PERMISSION_KEYS):
                _v152_answer(call, 'Неизвестное право', True)
                return True
            capability = V152_PERMISSION_KEYS[idx]
            scope = {'g': 'global', 't': 'tenant', 'c': 'chat'}.get(scope_code)
            real_target = int(target) if scope == 'chat' else target
            if scope != 'global' and (not v152_global_permission_allowed(capability)):
                _v152_answer(call, 'Функция запрещена владельцем платформы', True)
                return True
            if scope == 'chat' and _v152_chat_policy(int(real_target)).get('inherit_tenant', True):
                _v152_answer(call, 'Сначала выключите наследование пространства', True)
                return True
            current = _v152_scope_value(scope, real_target, capability)
            ok = _v152_set_global(capability, not current, user_id) if scope == 'global' else _v152_set_tenant(str(real_target), capability, not current, user_id) if scope == 'tenant' else _v152_set_chat(int(real_target), capability, not current, user_id)
            if not ok:
                _v152_answer(call, 'Недостаточно прав', True)
                return True
            _v152_answer(call, 'Право изменено')
            _v152_edit_rights(call, scope, real_target, page)
            return True
    except Exception as exc:
        try:
            log_error(f'v152 rights callback {data_str}: {exc}')
        except Exception:
            pass
        _v152_answer(call, 'Ошибка изменения прав', True)
        return True
    return True

# R47 FINALIZATION: rights callbacks are dispatched directly by the sole extension router.
_V152_WRAPPED_COMMAND_HANDLERS = _v152_install_command_wrappers()
try:
    _v177_legacy_0006_bot_journal('v152_permissions_installed', int(OWNER_ID or 0), f'command_handlers={_V152_WRAPPED_COMMAND_HANDLERS}; capabilities={len(V152_PERMISSION_KEYS)}')
except Exception:
    pass
'v153: remaining fixes 11-16.\n\n- deep command/button/runtime audit;\n- interactive export wait notices with a reusable Download button;\n- global secret redaction and preflight scanning;\n- runtime cleanup, exact failed counters and chat lifecycle history;\n- /json_full and validated /restore for global or tenant state;\n- v238 one canonical MEGA root only; release child roots are removed and never restore sources.\n'
import copy as _v153_copy
import gzip as _v153_gzip
import hashlib as _v153_hashlib
import json as _v153_json
import os as _v153_os
import re as _v153_re
import shutil as _v153_shutil
import sqlite3 as _v153_sqlite3
import tempfile as _v153_tempfile
import threading as _v153_threading
import time as _v153_time
import zipfile as _v153_zipfile
from datetime import datetime as _v153_datetime
from pathlib import Path as _V153Path
V153_EXPORT_SCHEMA = 1
V153_OLD_MEGA_ROOT = str(globals().get('MEGA_BACKUP_DIR') or '')
V153_NEW_MEGA_ROOT = str(globals().get('MEGA_BACKUP_DIR') or '')
V153_MIGRATION_BATCH = max(3, min(100, int(_v153_os.getenv('V153_MEGA_MIGRATION_BATCH', '20') or '20')))
V153_RESTORE_PENDING_TTL = 24 * 3600
_V153_LOCK = _v153_threading.RLock()
_V153_WAITING_EXPORTS = {}
_V153_READY_EXPORTS = {}
_V153_RESTORE_PENDING = {}
_V153_CALLBACK_RECEIPTS = {}
_V153_CALLBACK_SIGNATURES = {}
_V153_SANITIZED_TEMP = set()

def _v153_now() -> str:
    try:
        return now_local().isoformat(timespec='seconds')
    except Exception:
        return _v153_datetime.now().astimezone().isoformat(timespec='seconds')

def _v153_actor_id(obj) -> int:
    try:
        return int(getattr(getattr(obj, 'from_user', None), 'id', 0) or 0)
    except Exception:
        return 0

def _v153_platform_owner(uid: int) -> bool:
    try:
        return bool(tenant_is_platform_owner_user(int(uid)))
    except Exception:
        try:
            return int(uid) == int(OWNER_ID or 0)
        except Exception:
            return False

def _v153_tenant_for_chat(chat_id: int) -> str:
    try:
        return str(tenant_id_for_chat(int(chat_id), create=False) or TENANT_PLATFORM_ID)
    except Exception:
        return str(globals().get('TENANT_PLATFORM_ID') or 'platform')

def _v153_can_manage_tenant(uid: int, tenant_id: str) -> bool:
    if _v153_platform_owner(uid):
        return True
    try:
        return bool(tenant_can_manage(int(uid), str(tenant_id), owner_only=True))
    except TypeError:
        try:
            return bool(tenant_can_manage(int(uid), str(tenant_id)))
        except Exception:
            return False
    except Exception:
        return False
_V153_SECRET_KEY_RE = _v153_re.compile('^(?:password|passwd|pass|mega_password|telegram_token|bot_token|access[_-]?token|refresh[_-]?token|oauth[_-]?token|google[_-]?oauth[_-]?token|api[_-]?key|private[_-]?key|credential(?:s)?|authorization|cookie|webhook[_-]?secret|client[_-]?secret)$', _v153_re.I)
_V153_ENV_SECRET_RE = _v153_re.compile('(?:PASS|PASSWORD|SECRET|TOKEN|API_KEY|PRIVATE_KEY|CREDENTIAL|AUTH|COOKIE|OAUTH|WEBHOOK)', _v153_re.I)

def _v153_secret_values() -> list[str]:
    values = set()
    for key, value in _v153_os.environ.items():
        if _V153_ENV_SECRET_RE.search(str(key)) and value and (len(str(value)) >= 6):
            values.add(str(value))
    for name in ('MEGA_EMAIL', 'MEGA_PASSWORD', 'BOT_TOKEN', 'B_T', 'GOOGLE_SERVICE_ACCOUNT_JSON', 'TENANT_GOOGLE_MASTER_KEY', 'GOOGLE_TENANT_MASTER_KEY', 'WEBHOOK_SECRET'):
        value = str(globals().get(name) or _v153_os.getenv(name) or '')
        if value and len(value) >= 6:
            values.add(value)
    return sorted(values, key=len, reverse=True)

def v153_redact_text(value) -> str:
    text = str(value or '')
    for secret in _v153_secret_values():
        if secret in text:
            text = text.replace(secret, '***')
    text = _v153_re.sub('(?i)(Authorization\\s*[:=]\\s*)(?:Bearer\\s+)?[^\\s,;]+', '\\1***', text)
    text = _v153_re.sub('(?i)(Cookie\\s*[:=]\\s*)[^\\r\\n]+', '\\1***', text)
    text = _v153_re.sub('(?i)("?(?:password|passwd|secret|token|api[_-]?key|private[_-]?key|authorization|cookie|client[_-]?secret|webhook[_-]?secret)"?\\s*[:=]\\s*)("[^"\\r\\n]*"|[^,;\\r\\n ]+)', lambda m: m.group(1) + '"***"', text)
    text = _v153_re.sub('(?i)(Bearer\\s+)[A-Za-z0-9._~+/=-]+', '\\1***', text)
    return text

def v153_sanitize(value, key: str=''):
    if _V153_SECRET_KEY_RE.search(str(key or '')):
        return '***'
    if isinstance(value, dict):
        return {str(k): v153_sanitize(v, str(k)) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [v153_sanitize(x, key) for x in value]
    if isinstance(value, str):
        return v153_redact_text(value)
    return value
_V153_ORIG_LOG_ERROR = _v177_legacy_0003_log_error
_V153_ORIG_LOG_INFO = _v177_legacy_0002_log_info
_V153_ORIG_BOT_JOURNAL = _v177_legacy_0006_bot_journal
_V153_ORIG_ATOMIC_JSON_DUMP = _v177_legacy_0008_atomic_json_dump
_V153_ORIG_MAKE_GLOBAL_BACKUP = _v177_legacy_0077_make_global_backup_payload

def _canon_log_error__001(message):
    if callable(_V153_ORIG_LOG_ERROR):
        return _V153_ORIG_LOG_ERROR(v153_redact_text(message))

def _canon_log_info__001(message):
    safe = v153_redact_text(message)
    try:
        text = str(safe or '')
        if text.startswith(('BTNTRACE ', 'LOCKTRACE ', 'SPLITTRACE ', 'R26 SQLITE ONLINE BACKUP')):
            fn = globals().get('r26_diag_trace_line')
            if callable(fn): fn(text)
    except Exception:
        pass
    if callable(_V153_ORIG_LOG_INFO):
        return _V153_ORIG_LOG_INFO(safe)

def _v177_legacy_0007_bot_journal(action, chat_id=None, detail='', level='INFO'):
    if callable(_V153_ORIG_BOT_JOURNAL):
        return _V153_ORIG_BOT_JOURNAL(str(action), chat_id, v153_sanitize(detail), str(level))
try:
    _v177_legacy_0007_bot_journal.__name__ = 'bot_journal'
except Exception:
    pass

def _canon_atomic_json_dump__001(path: str, payload) -> None:
    safe = v153_sanitize(payload)
    if callable(_V153_ORIG_ATOMIC_JSON_DUMP):
        return _V153_ORIG_ATOMIC_JSON_DUMP(path, safe)
    with open(path, 'w', encoding='utf-8') as fh:
        _v153_json.dump(safe, fh, ensure_ascii=False)

def _canon_make_global_backup_payload__001():
    payload = _V153_ORIG_MAKE_GLOBAL_BACKUP() if callable(_V153_ORIG_MAKE_GLOBAL_BACKUP) else {}
    return v153_sanitize(payload)

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

def _v153_text_extension(path: str) -> bool:
    return _v153_os.path.splitext(str(path or ''))[1].lower() in {'.txt', '.json', '.csv', '.log', '.md', '.xml', '.yaml', '.yml'}

def _v153_sanitize_zip(src: str, dst: str) -> None:
    with _v153_zipfile.ZipFile(src, 'r') as zin, _v153_zipfile.ZipFile(dst, 'w', _v153_zipfile.ZIP_DEFLATED) as zout:
        for item in zin.infolist():
            raw = zin.read(item.filename)
            ext = _v153_os.path.splitext(item.filename)[1].lower()
            if ext in {'.txt', '.json', '.csv', '.log', '.md', '.xml', '.yaml', '.yml'}:
                try:
                    raw = v153_redact_text(raw.decode('utf-8')).encode('utf-8')
                except Exception:
                    pass
            zout.writestr(item, raw)

def v153_prepare_safe_file(path: str, hint: str='') -> str:
    """Return original or a sanitized temporary copy. Binary state DBs are not rewritten."""
    src = str(path or '')
    if not src or not _v153_os.path.isfile(src):
        return src
    low = f'{src} {hint}'.casefold()
    sensitive_export = any((x in low for x in ('journal', 'log', 'runtime', 'diagn', 'failed', 'audit', 'error', 'snapshot', 'export')))
    if not sensitive_export and (not _v153_text_extension(src)):
        return src
    folder = _v153_tempfile.mkdtemp(prefix='v153_safe_')
    dst = _v153_os.path.join(folder, _v153_os.path.basename(src))
    try:
        if src.lower().endswith('.zip'):
            _v153_sanitize_zip(src, dst)
        elif _v153_text_extension(src):
            raw = _V153Path(src).read_text(encoding='utf-8', errors='replace')
            _V153Path(dst).write_text(v153_redact_text(raw), encoding='utf-8')
        else:
            return src
        _V153_SANITIZED_TEMP.add(folder)
        return dst
    except Exception:
        _v153_shutil.rmtree(folder, ignore_errors=True)
        return src
# FINALIZED: v153 sanitization is applied by the single final send_document transport.
_V153_ORIG_FILE_RUNNER = _v177_legacy_0012_interactive_file_job_runner
_V153_ORIG_FILE_SUBMIT = _v177_legacy_0016_submit_interactive_file_job

def _v153_wait_token(chat_id: int, kind: str) -> str:
    raw = f'{chat_id}:{kind}:{_v153_time.time_ns()}'.encode()
    return _v153_hashlib.sha256(raw).hexdigest()[:16]

def _v153_wait_keyboard(token: str):
    kb = types.InlineKeyboardMarkup()
    kb.add(IB('📥 Скачать сейчас', callback_data=f'v153:file:{token}'))
    return kb

def _v153_register_wait(chat_id: int, kind: str, label: str, func, args, kwargs, active: dict) -> None:
    chat_id = int(chat_id)
    token = _v153_wait_token(chat_id, kind)
    text = f"⏳ Сейчас нельзя скачать «{label}».\n\nУже формируется:\n«{active.get('label') or 'другой файл'}»."
    with _V153_LOCK:
        old = _V153_WAITING_EXPORTS.get(chat_id) or {}
    msg_id = int(old.get('message_id') or 0)
    try:
        if msg_id:
            bot.edit_message_text(text, chat_id=chat_id, message_id=msg_id)
        else:
            sent = bot.send_message(chat_id, text)
            msg_id = int(getattr(sent, 'message_id', 0) or 0)
    except Exception:
        pass
    request = {'token': token, 'chat_id': chat_id, 'kind': str(kind), 'label': str(label), 'func': func, 'args': tuple(args), 'kwargs': dict(kwargs), 'message_id': msg_id, 'created_at': _v153_now()}
    with _V153_LOCK:
        _V153_WAITING_EXPORTS[chat_id] = request

def _v153_release_waiters(ok: bool, error_text: str='') -> None:
    with _V153_LOCK:
        rows = list(_V153_WAITING_EXPORTS.values())
        _V153_WAITING_EXPORTS.clear()
    for row in rows:
        token = str(row['token'])
        with _V153_LOCK:
            _V153_READY_EXPORTS[token] = row
        if ok:
            text = f"✅ Теперь можно скачать «{row['label']}»."
        else:
            text = '⚠️ Предыдущая выгрузка завершилась ошибкой.\n\nТеперь можно попробовать снова.'
        try:
            if row.get('message_id'):
                bot.edit_message_text(text, chat_id=int(row['chat_id']), message_id=int(row['message_id']), reply_markup=_v153_wait_keyboard(token))
            else:
                sent = bot.send_message(int(row['chat_id']), text, reply_markup=_v153_wait_keyboard(token))
                row['message_id'] = int(getattr(sent, 'message_id', 0) or 0)
        except Exception:
            pass

def _v177_legacy_0013_interactive_file_job_runner(job_meta: dict, func, args, kwargs):
    state = {'ok': False, 'error': ''}

    def _target(*a, **k):
        try:
            result = func(*a, **k)
            state['ok'] = result is not False
            if not state['ok']:
                state['error'] = 'операция завершилась без подтверждения'
            return result
        except Exception as exc:
            state['error'] = v153_redact_text(exc)[:300]
            raise
    if callable(_V153_ORIG_FILE_RUNNER):
        result = _V153_ORIG_FILE_RUNNER(job_meta, _target, args, kwargs)
    else:
        result = _target(*args, **kwargs)
    _v153_release_waiters(bool(state['ok']), state['error'])
    return result
try:
    _v177_legacy_0013_interactive_file_job_runner.__name__ = '_interactive_file_job_runner'
except Exception:
    pass

def _v177_legacy_0017_submit_interactive_file_job(chat_id: int, kind: str, label: str, func, *args, **kwargs):
    busy = _file_job_busy_info() if '_file_job_busy_info' in globals() else {}
    if busy:
        _v153_register_wait(int(chat_id), str(kind), str(label), func, args, kwargs, busy)
        return (False, f"Уже формируется: {busy.get('label') or 'файл'}")
    if callable(_V153_ORIG_FILE_SUBMIT):
        return _V153_ORIG_FILE_SUBMIT(chat_id, kind, label, func, *args, **kwargs)
    return (False, 'Экспорт недоступен')
try:
    _v177_legacy_0017_submit_interactive_file_job.__name__ = 'submit_interactive_file_job'
except Exception:
    pass
_V153_ORIG_RUNTIME_SELECT = _v177_legacy_0079_runtime_export_select_paths
_V153_ORIG_RUNTIME_SEND = _v177_legacy_0080_send_runtime_export_zip
_V153_ORIG_MEGA_STATS = _v177_legacy_0065_mega_task_registry_stats
_V153_ORIG_RUNTIME_MARK_READY = _v177_legacy_0083_runtime_mark_ready
_V153_ORIG_RUNTIME_UPLOAD = _v177_legacy_0081_runtime_upload_snapshot
_V153_ORIG_NORMALIZE_EXPECTED = _v177_legacy_0067_durable_normalize_expected_for_route
_V153_ORIG_RESTORE_SQLITE = _v177_legacy_0085_mega_restore_sqlite_snapshot_from_cloud
_V153_ORIG_RESTORE_FULL = _v177_legacy_0086_mega_restore_full_from_cloud
_V153_ORIG_CLASSIFY_PREVIOUS = _v177_legacy_0078_runtime_classify_previous
_V153_INSTANCE_SUPERSEDED = False
_V153_INSTANCE_LEASE_LAST = 0.0

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

def _canon_runtime_export_select_paths__001(start_dt=None, end_dt=None, max_downloads: int=360):
    indexed, _legacy_selected = _V153_ORIG_RUNTIME_SELECT(start_dt, end_dt, max_downloads=max_downloads) if callable(_V153_ORIG_RUNTIME_SELECT) else ([], [])
    stable = [x for x in indexed if x[0] in {'slot', 'event'}]
    stable = stable[:max(20, min(int(max_downloads), 180))]
    selected = list(stable)
    newest_stable = max((x[2] for x in stable if x[2] is not None), default=None)
    candidates = [x for x in indexed if x[0] in {'candidate', 'staged'} and x[2] is not None]
    if candidates:
        newest = max(candidates, key=lambda x: x[2])
        if newest_stable is None or newest[2] > newest_stable:
            selected.append(newest)
    return (indexed, selected[:max_downloads])

def _v153_chat_lifecycle_snapshot() -> dict:
    out = {'created_at': _v153_now(), 'chats': {}}
    try:
        for cid_s, store in list(((data or {}).get('chats') or {}).items()):
            if not isinstance(store, dict):
                continue
            life = (store.get('settings') or {}).get('chat_lifecycle_v150') or {}
            if life:
                out['chats'][str(cid_s)] = v153_sanitize(life)
    except Exception:
        pass
    return out

def _canon_send_runtime_export_zip__001(recipient_chat_id: int, start_dt=None, end_dt=None):
    if not callable(_V153_ORIG_RUNTIME_SEND):
        return False
    previous_hook = getattr(_SEND_DOCUMENT_TRANSFORM_LOCAL, 'hook', None)

    def _runtime_zip_transform(chat_id, document, args, kwargs):
        try:
            name = str(getattr(document, 'name', '') or '')
            if name and _v153_os.path.isfile(name) and name.lower().endswith('.zip'):
                temp_dir = _v153_tempfile.mkdtemp(prefix='v153_runtime_')
                temp = _v153_os.path.join(temp_dir, _v153_os.path.basename(name))
                _v153_shutil.copy2(name, temp)
                with _v153_zipfile.ZipFile(temp, 'a', _v153_zipfile.ZIP_DEFLATED) as z:
                    z.writestr('chat_lifecycle_history.json', _v153_json.dumps(_v153_chat_lifecycle_snapshot(), ensure_ascii=False, indent=2))
                    z.writestr('v153_runtime_fixes.txt', _v153_runtime_audit_text())
                safe_document = open(temp, 'rb')
                def _cleanup():
                    try: safe_document.close()
                    except Exception: pass
                    _v153_shutil.rmtree(temp_dir, ignore_errors=True)
                return safe_document, _cleanup
        except Exception as exc:
            log_error(f'runtime lifecycle append: {exc}')
        return document, None

    _SEND_DOCUMENT_TRANSFORM_LOCAL.hook = _runtime_zip_transform
    try:
        return _V153_ORIG_RUNTIME_SEND(recipient_chat_id, start_dt, end_dt)
    finally:
        if previous_hook is None:
            try: delattr(_SEND_DOCUMENT_TRANSFORM_LOCAL, 'hook')
            except Exception: pass
        else:
            _SEND_DOCUMENT_TRANSFORM_LOCAL.hook = previous_hook

def _canon_durable_normalize_expected_for_route__001(payload: dict, expected: dict | None) -> dict:
    adjusted = _V153_ORIG_NORMALIZE_EXPECTED(payload, expected) if callable(_V153_ORIG_NORMALIZE_EXPECTED) else dict(expected or {})
    raw, _cid, _mid, _grp = _durable_payload_message(payload or {}) if '_durable_payload_message' in globals() else ({}, None, None, None)
    text = str((raw or {}).get('text') or (raw or {}).get('caption') or '') if isinstance(raw, dict) else ''
    if 'EDITREM|' not in text and 'EDITREMINT|' not in text:
        adjusted['reminder_edits'] = []
    return adjusted

def _v153_runtime_cleanup_remote() -> dict:
    result = {'candidates_removed': 0, 'staged_removed': 0}
    try:
        root = runtime_remote_dir()
        result['candidates_removed'] = _mega_prune_remote_history(root, 'candidate_runtime_latest_*.json', 2)
        result['staged_removed'] = _mega_prune_remote_history(root, 'runtime_latest__*.json', 2)
    except Exception as exc:
        result['error'] = v153_redact_text(exc)
    return result

def _v153_remote_marker_exists(root: str) -> bool:
    try:
        rows = _mega_find_remote_files(str(root).rstrip('/'), 'migration_v153_complete.json', limit=3)
        return any((str(x).rstrip('/').endswith('/migration_v153_complete.json') for x in rows))
    except Exception:
        return False

def _v153_select_boot_mega_root() -> str:
    root = str(globals().get('MEGA_CANONICAL_BACKUP_DIR_V238') or globals().get('MEGA_BACKUP_DIR') or '').rstrip('/')
    _v153_apply_mega_root(root)
    return root

def _canon_mega_restore_sqlite_snapshot_from_cloud__001(force: bool=False) -> tuple[bool, str]:
    """v241: preserve explicit owner force=True through the compatibility wrapper."""
    _v153_select_boot_mega_root()
    if callable(_V153_ORIG_RESTORE_SQLITE):
        try:
            return _V153_ORIG_RESTORE_SQLITE(force=bool(force))
        except TypeError:
            return _V153_ORIG_RESTORE_SQLITE()
    return (False, 'SQLite restore unavailable')

def _canon_mega_restore_full_from_cloud__001(force: bool=False) -> tuple[bool, str]:
    _v153_select_boot_mega_root()
    if callable(_V153_ORIG_RESTORE_FULL):
        return _V153_ORIG_RESTORE_FULL(force=force)
    return (False, 'Full restore unavailable')

def _v153_instance_lease_payload() -> dict:
    return {'kind': 'telegram_bot_active_instance_v153', 'instance_id': str(_v153_os.getenv('RENDER_INSTANCE_ID') or _v153_os.uname().nodename), 'commit': str(_v153_os.getenv('RENDER_GIT_COMMIT') or ''), 'started_at': str(globals().get('_RUNTIME_STARTED_AT') or _v153_now()), 'heartbeat_at': _v153_now(), 'version': VERSION}

def _v179_base_instance_lease_check() -> dict:
    global _V153_INSTANCE_SUPERSEDED, _V153_INSTANCE_LEASE_LAST
    result = {'active': True, 'superseded': False}
    if not mega_is_configured():
        return result
    now_m = _v153_time.monotonic()
    if now_m - _V153_INSTANCE_LEASE_LAST < 20.0:
        result['superseded'] = bool(_V153_INSTANCE_SUPERSEDED)
        result['active'] = not bool(_V153_INSTANCE_SUPERSEDED)
        return result
    _V153_INSTANCE_LEASE_LAST = now_m
    remote_dir = runtime_remote_dir()
    remote = remote_dir.rstrip('/') + '/active_instance_v153.json'
    ours = _v153_instance_lease_payload()
    current = None
    local = None
    try:
        local = _mega_download_remote_path(remote)
        if local and _v153_os.path.isfile(local):
            current = _v153_json.loads(_V153Path(local).read_text(encoding='utf-8'))
    except Exception:
        current = None
    finally:
        if local:
            _v153_shutil.rmtree(_v153_os.path.dirname(local), ignore_errors=True)
    other_id = str((current or {}).get('instance_id') or '')
    our_id = str(ours['instance_id'])
    current_started = str((current or {}).get('started_at') or '')
    ours_started = str(ours['started_at'])
    if other_id and other_id != our_id and (current_started > ours_started):
        _V153_INSTANCE_SUPERSEDED = True
        result.update({'active': False, 'superseded': True, 'newer_instance': other_id})
        try:
            _RUNTIME_STATE['phase'] = 'superseded'
            _RUNTIME_STATE['ready'] = False
            _RUNTIME_STATE['last_event'] = 'newer_render_instance_active'
            _RUNTIME_STATE['last_event_at'] = _v153_now()
        except Exception:
            pass
        bot_journal('runtime_instance_superseded', None, f'newer_instance={other_id}; newer_started={current_started}', 'WARN')
        return result
    temp_dir = _v153_tempfile.mkdtemp(prefix='v153_lease_')
    try:
        path = _v153_os.path.join(temp_dir, 'active_instance_v153.json')
        _V153Path(path).write_text(_v153_json.dumps(v153_sanitize(ours), ensure_ascii=False, indent=2), encoding='utf-8')
        if mega_put_replace(path, remote_dir, 'active_instance_v153.json', archive_previous=False):
            _V153_INSTANCE_SUPERSEDED = False
            result['active_instance'] = our_id
    finally:
        _v153_shutil.rmtree(temp_dir, ignore_errors=True)
    return result

def _canon_runtime_classify_previous__001(prev: dict) -> str:
    base = _V153_ORIG_CLASSIFY_PREVIOUS(prev) if callable(_V153_ORIG_CLASSIFY_PREVIOUS) else 'process_restart_or_unknown'
    try:
        prev_state = (prev or {}).get('state') or {}
        prev_render = (prev or {}).get('render') or {}
        prev_id = str(prev_render.get('RENDER_INSTANCE_ID') or '')
        cur_id = str(_v153_os.getenv('RENDER_INSTANCE_ID') or '')
        prev_capture = str((prev or {}).get('captured_at') or '')
        cur_start = str(globals().get('_RUNTIME_STARTED_AT') or '')
        if prev_id and cur_id and (prev_id != cur_id) and prev_capture and cur_start and (prev_capture >= cur_start):
            return 'overlapping_render_instances_detected'
        if bool(prev_state.get('shutdown_finished_at')):
            return base
        if str(prev_state.get('phase') or '') == 'superseded':
            return 'older_instance_superseded_by_newer_instance'
    except Exception:
        pass
    return base

def _canon_runtime_upload_snapshot__001(event: str='snapshot', immutable_event: bool=True) -> bool:
    lease = _v153_instance_lease_check()
    if lease.get('superseded'):
        return False
    ok = _V153_ORIG_RUNTIME_UPLOAD(event, immutable_event) if callable(_V153_ORIG_RUNTIME_UPLOAD) else False
    try:
        if event in {'boot_ready', 'manual', 'shutdown'}:
            GENERAL_TASK_POOL.submit_unique('v153-runtime-prune', _v153_runtime_cleanup_remote)
    except Exception:
        pass
    return ok

def _v153_migration_store(root=None) -> dict:
    return {'status': 'removed_v238', 'copied_files': 0, 'total_files': 0, 'remaining_files': 0, 'last_error': '', 'active_root': str(globals().get('MEGA_CANONICAL_BACKUP_DIR_V238') or globals().get('MEGA_BACKUP_DIR') or '')}

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
_V153_ORIG_LOAD_DATA = _v177_legacy_0087_load_data

def _canon_load_data__001():
    loaded = _V153_ORIG_LOAD_DATA() if callable(_V153_ORIG_LOAD_DATA) else {}
    try:
        gs = loaded.get('_global_settings') if isinstance(loaded, dict) else None
        if isinstance(gs, dict):
            gs.pop('mega_root_migration_v153', None)
        _v153_apply_mega_root(str(globals().get('MEGA_CANONICAL_BACKUP_DIR_V238') or globals().get('MEGA_BACKUP_DIR') or ''))
    except Exception:
        pass
    return loaded

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

def _v153_remote_relative(path: str, root: str) -> str:
    raw = str(path or '')
    prefix = str(root).rstrip('/') + '/'
    return raw[len(prefix):] if raw.startswith(prefix) else _v153_os.path.basename(raw)

def _v153_sha256_file(path: str) -> str:
    h = _v153_hashlib.sha256()
    with open(path, 'rb') as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()

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

def v153_migrate_mega_root() -> dict:
    """v179 compatibility status: root migration is permanently retired."""
    root = str(globals().get('MEGA_BACKUP_DIR') or '').rstrip('/')
    return {'status': 'disabled_v179', 'active_root': root, 'canonical_root': str(globals().get('MEGA_BACKUP_DIR') or ''), 'remaining_files': 0, 'last_error': ''}

def _v179_base_schedule_migration():
    return False

def _v153_sql_rows(conn, table: str, where: str='', params=()):
    sql = f'SELECT * FROM {table}' + (f' WHERE {where}' if where else '')
    return conn.execute(sql, tuple(params)).fetchall()

def _v153_db_logical_checksum(path: str) -> str:
    conn = _v153_sqlite3.connect(path)
    try:
        h = _v153_hashlib.sha256()
        for table in ('kv', 'chats', 'meta', 'cold_fields'):
            cols = [x[1] for x in conn.execute(f'PRAGMA table_info({table})').fetchall()]
            if not cols:
                continue
            order = ','.join(cols[:2])
            for row in conn.execute(f'SELECT * FROM {table} ORDER BY {order}').fetchall():
                if table == 'meta' and len(row) >= 2 and (str(row[0]) == 'v153_export') and (str(row[1]) == 'manifest'):
                    continue
                h.update(table.encode())
                h.update(b'\x00')
                for value in row:
                    h.update(str(value).encode('utf-8', 'replace'))
                    h.update(b'\x00')
        return h.hexdigest()
    finally:
        conn.close()

def _v153_scope_chat_ids_from_item(item) -> set[int]:
    result = set()
    if not isinstance(item, dict):
        return result
    for key in ('chat_id', 'source_chat_id', 'target_chat_id', 'src_chat_id', 'dst_chat_id', 'root_chat_id'):
        raw = item.get(key)
        if str(raw or '').lstrip('-').isdigit():
            result.add(int(raw))
    for key in ('chat_ids', 'target_chat_ids', 'forward_targets'):
        value = item.get(key) or []
        if isinstance(value, dict):
            value = list(value.keys())
        for raw in value if isinstance(value, (list, tuple, set)) else []:
            if isinstance(raw, dict):
                raw = raw.get('dst_chat_id') or raw.get('chat_id')
            if str(raw or '').lstrip('-').isdigit():
                result.add(int(raw))
    return result

def _v153_item_in_tenant_scope(item, tenant_id: str, chat_ids: set[int], key: str='') -> bool:
    if isinstance(item, dict):
        tid = str(item.get('tenant_id') or '')
        if tid and tid == str(tenant_id):
            return True
        if _v153_scope_chat_ids_from_item(item) & set(chat_ids):
            return True
    key_s = str(key or '')
    for cid in chat_ids:
        if key_s == str(cid) or key_s.startswith(f'{cid}:') or key_s.startswith(f'{cid}|'):
            return True
    return False

def _v153_filter_global_settings_for_tenant(gs: dict, tenant_id: str, chat_ids: set[int]) -> dict:
    tenants = ((gs or {}).get('tenants_v148') or {}).get('tenants') or {}
    tenant_row = _v153_copy.deepcopy(tenants.get(str(tenant_id)) or {})
    safe = {'tenants_v148': {'schema_version': 1, 'tenants': {str(tenant_id): v153_sanitize(tenant_row)}, 'chat_to_tenant': {str(cid): str(tenant_id) for cid in sorted(chat_ids)}, 'invite_tokens': {}, 'legacy_migrated': True, 'created_at': _v153_now()}}
    rem = _v153_copy.deepcopy((gs or {}).get('reminders_v2') or {})
    items = {}
    for rid, cfg in (rem.get('items') or {}).items() if isinstance(rem, dict) else []:
        if _v153_item_in_tenant_scope(cfg, tenant_id, chat_ids):
            items[str(rid)] = v153_sanitize(cfg)
    if items:
        safe['reminders_v2'] = {'next_id': max([int(x) for x in items if str(x).isdigit()] + [0]) + 1, 'items': items, 'migrated_v134': True}
    op = _v153_copy.deepcopy((gs or {}).get('operation_ledger_v141') or {})
    if isinstance(op, dict):
        op_items = {str(k): v153_sanitize(v) for k, v in (op.get('items') or {}).items() if _v153_item_in_tenant_scope(v, tenant_id, chat_ids, str(k))}
        if op_items:
            order = [str(x) for x in op.get('order') or [] if str(x) in op_items]
            safe['operation_ledger_v141'] = {'items': op_items, 'order': order, 'next_seq': int(op.get('next_seq') or 1)}
    integ = _v153_copy.deepcopy((gs or {}).get('finance_integrity_v141') or {})
    if isinstance(integ, dict):
        events = [v153_sanitize(x) for x in integ.get('events') or [] if _v153_item_in_tenant_scope(x, tenant_id, chat_ids)]
        tips = {str(k): v for k, v in (integ.get('tips') or {}).items() if str(k).lstrip('-').isdigit() and int(k) in chat_ids}
        if events or tips:
            safe['finance_integrity_v141'] = {'events': events, 'tips': tips, 'anchor': {}, 'event_seq': int(integ.get('event_seq') or 0)}
    return safe

def _v153_filter_root_for_tenant(root: dict, tenant_id: str, chat_ids: set[int]) -> dict:
    out = {}
    for key, value in (root or {}).items():
        if key == '_global_settings':
            out[key] = _v153_filter_global_settings_for_tenant(value if isinstance(value, dict) else {}, str(tenant_id), chat_ids)
            continue
        if key in {'chats', '_restore_mode_chat_v150'}:
            continue
        if isinstance(value, list):
            rows = [v153_sanitize(_v153_copy.deepcopy(item)) for item in value if _v153_item_in_tenant_scope(item, tenant_id, chat_ids)]
            if rows:
                out[key] = rows
            continue
        if isinstance(value, dict):
            filtered = {}
            for item_key, item in value.items():
                if _v153_item_in_tenant_scope(item, tenant_id, chat_ids, str(item_key)):
                    filtered[str(item_key)] = v153_sanitize(_v153_copy.deepcopy(item))
            if filtered:
                out[key] = filtered
            continue
    return out

def _v153_collect_failed_tasks(tenant_id: str | None, chat_ids: set[int]) -> list[dict]:
    rows = []
    try:
        mega_task_refresh_registry()
        with _MEGA_TASK_LOCK:
            failed = [(str(k), str((v or {}).get('path') or '')) for k, v in _mega_task_registry.items() if str((v or {}).get('state') or '') == 'failed']
        for key, remote in failed[:500]:
            local = _mega_download_remote_path(remote)
            if not local:
                continue
            try:
                task = _v153_json.loads(_V153Path(local).read_text(encoding='utf-8'))
                cid = int(task.get('chat_id') or 0)
                if tenant_id is None or cid in chat_ids:
                    rows.append(v153_sanitize(task))
            finally:
                _v153_shutil.rmtree(_v153_os.path.dirname(local), ignore_errors=True)
    except Exception as exc:
        rows.append({'load_error': v153_redact_text(exc)})
    return rows

def _v153_build_export(scope: str, tenant_id: str | None=None) -> str:
    _lowram_flush_all_hot(evict=False)
    save_data(data, full=True)
    folder = _v153_tempfile.mkdtemp(prefix='v153_full_export_')
    raw = _v153_os.path.join(folder, 'state.sqlite3')
    SQLITE.backup_to(raw)
    conn = _v153_sqlite3.connect(raw)
    try:
        chat_ids = set()
        if scope == 'tenant':
            chat_ids = set((int(x) for x in tenant_chat_ids(str(tenant_id))))
            marks = ','.join(('?' for _ in chat_ids)) or 'NULL'
            if chat_ids:
                conn.execute(f'DELETE FROM chats WHERE CAST(chat_id AS INTEGER) NOT IN ({marks})', tuple(chat_ids))
                conn.execute(f'DELETE FROM cold_fields WHERE CAST(chat_id AS INTEGER) NOT IN ({marks})', tuple(chat_ids))
            else:
                conn.execute('DELETE FROM chats')
                conn.execute('DELETE FROM cold_fields')
            row = conn.execute("SELECT v FROM kv WHERE k='root'").fetchone()
            root = _v153_json.loads(row[0]) if row else {}
            filtered = _v153_filter_root_for_tenant(root, str(tenant_id), chat_ids)
            conn.execute("INSERT INTO kv(k,v) VALUES('root',?) ON CONFLICT(k) DO UPDATE SET v=excluded.v", (_v153_json.dumps(filtered, ensure_ascii=False, separators=(',', ':')),))
        else:
            for table, key_cols, json_col in (('kv', ('k',), 'v'), ('chats', ('chat_id',), 'v'), ('meta', ('kind', 'k'), 'v'), ('cold_fields', ('chat_id', 'k'), 'v')):
                cols = ','.join(key_cols + (json_col,))
                for row in conn.execute(f'SELECT {cols} FROM {table}').fetchall():
                    keys, raw_json = (row[:-1], row[-1])
                    try:
                        payload = v153_sanitize(_v153_json.loads(raw_json))
                    except Exception:
                        payload = v153_redact_text(raw_json)
                    where = ' AND '.join((f'{c}=?' for c in key_cols))
                    conn.execute(f'UPDATE {table} SET {json_col}=? WHERE {where}', (_v153_json.dumps(payload, ensure_ascii=False, separators=(',', ':')), *keys))
            chat_ids = {int(x[0]) for x in conn.execute('SELECT chat_id FROM chats').fetchall() if str(x[0]).lstrip('-').isdigit()}
        failed = _v153_collect_failed_tasks(tenant_id if scope == 'tenant' else None, chat_ids)
        conn.execute("INSERT INTO meta(kind,k,v) VALUES('v153_export','failed_tasks',?) ON CONFLICT(kind,k) DO UPDATE SET v=excluded.v", (_v153_json.dumps(failed, ensure_ascii=False, separators=(',', ':')),))
        manifest = {'kind': 'telegram_bot_full_state_v153', 'schema_version': V153_EXPORT_SCHEMA, 'bot_version': VERSION, 'created_at': _v153_now(), 'scope': scope, 'tenant_id': str(tenant_id or ''), 'chat_ids': sorted(chat_ids), 'chat_count': len(chat_ids), 'failed_tasks': len(failed), 'checksum': ''}
        conn.execute("INSERT INTO meta(kind,k,v) VALUES('v153_export','manifest',?) ON CONFLICT(kind,k) DO UPDATE SET v=excluded.v", (_v153_json.dumps(manifest, ensure_ascii=False, separators=(',', ':')),))
        conn.commit()
    finally:
        conn.close()
    checksum = _v153_db_logical_checksum(raw)
    conn = _v153_sqlite3.connect(raw)
    try:
        manifest = _v153_json.loads(conn.execute("SELECT v FROM meta WHERE kind='v153_export' AND k='manifest'").fetchone()[0])
        manifest['checksum'] = checksum
        conn.execute("UPDATE meta SET v=? WHERE kind='v153_export' AND k='manifest'", (_v153_json.dumps(manifest, ensure_ascii=False, separators=(',', ':')),))
        conn.commit()
    finally:
        conn.close()
    gz = _v153_os.path.join(folder, 'latest_bot_state.sqlite3.gz')
    with open(raw, 'rb') as fin, _v153_gzip.open(gz, 'wb', compresslevel=6) as fout:
        _v153_shutil.copyfileobj(fin, fout, 1024 * 1024)
    return gz

def _v153_send_full_export(chat_id: int, scope: str, tenant_id: str | None):
    path = _v153_build_export(scope, tenant_id)
    try:
        with open(path, 'rb') as fh:
            caption = '🗄 Полное состояние всего бота' if scope == 'global' else f"🗄 Состояние пространства: {(tenant_get(tenant_id) or {}).get('name') or tenant_id}"
            _tg_call_retry(bot.send_document, int(chat_id), fh, caption=caption, timeout=180, purpose='json_full_v153')
        return True
    finally:
        _v153_shutil.rmtree(_v153_os.path.dirname(path), ignore_errors=True)

def _v177_legacy_0278_v153_validate_restore_gz(gz_path: str) -> tuple[dict, str]:
    folder = _v153_tempfile.mkdtemp(prefix='v153_restore_validate_')
    raw = _v153_os.path.join(folder, 'restore.sqlite3')
    try:
        with _v153_gzip.open(gz_path, 'rb') as fin, open(raw, 'wb') as fout:
            _v153_shutil.copyfileobj(fin, fout, 1024 * 1024)
        conn = _v153_sqlite3.connect(raw)
        try:
            integrity = str(conn.execute('PRAGMA integrity_check').fetchone()[0])
            if integrity.lower() != 'ok':
                raise RuntimeError(f'SQLite integrity_check: {integrity}')
            row = conn.execute("SELECT v FROM meta WHERE kind='v153_export' AND k='manifest'").fetchone()
            if not row:
                raise RuntimeError('manifest v153 not found')
            manifest = _v153_json.loads(row[0])
        finally:
            conn.close()
        if str(manifest.get('kind')) != 'telegram_bot_full_state_v153':
            raise RuntimeError('unknown export kind')
        if int(manifest.get('schema_version') or 0) != V153_EXPORT_SCHEMA:
            raise RuntimeError('unsupported export schema')
        export_version = str(manifest.get('bot_version') or '')
        if not export_version.startswith('bot_v153_'):
            raise RuntimeError(f"unsupported bot version: {export_version or 'missing'}")
        checksum = _v153_db_logical_checksum(raw)
        if checksum != str(manifest.get('checksum') or ''):
            raise RuntimeError('checksum mismatch')
        return (manifest, raw)
    except Exception:
        _v153_shutil.rmtree(folder, ignore_errors=True)
        raise
try:
    _v177_legacy_0278_v153_validate_restore_gz.__name__ = '_v153_validate_restore_gz'
except Exception:
    pass

def _v153_restore_keyboard(token: str, scope: str):
    kb = types.InlineKeyboardMarkup()
    if scope == 'tenant':
        kb.add(IB('♻️ Восстановить строго из файла', callback_data=f'v153:restore:{token}:replace'))
    else:
        kb.add(IB('♻️ Восстановить весь бот', callback_data=f'v153:restore:{token}:replace'))
    kb.add(IB('❌ Отмена', callback_data=f'v153:restore:{token}:cancel'))
    return kb

def _v153_download_replied_document(msg) -> str:
    reply = getattr(msg, 'reply_to_message', None)
    document = getattr(reply, 'document', None)
    if not document:
        raise RuntimeError('Ответьте командой /restore на файл latest_bot_state.sqlite3.gz')
    name = str(getattr(document, 'file_name', '') or '')
    if not name.lower().endswith('.sqlite3.gz'):
        raise RuntimeError('Нужен файл .sqlite3.gz')
    info = bot.get_file(document.file_id)
    raw = bot.download_file(info.file_path)
    folder = _v153_tempfile.mkdtemp(prefix='v153_restore_upload_')
    path = _v153_os.path.join(folder, 'latest_bot_state.sqlite3.gz')
    with open(path, 'wb') as fh:
        fh.write(raw)
    return path

def v153_cmd_json_full(msg):
    uid = _v153_actor_id(msg)
    chat_id = int(msg.chat.id)
    tenant_id = _v153_tenant_for_chat(chat_id)
    if _v153_platform_owner(uid):
        parts = str(getattr(msg, 'text', '') or '').split(maxsplit=1)
        if len(parts) <= 1:
            kb = types.InlineKeyboardMarkup()
            kb.row(IB('🌐 Весь бот', callback_data='v153:json:global'))
            for tenant in tenant_all() or []:
                tid = str((tenant or {}).get('id') or '')
                if tid:
                    kb.row(IB(f"🏠 {(tenant or {}).get('name') or tid}", callback_data=f'v153:json:tenant:{tid}'))
            bot.reply_to(msg, '🗄 Что выгрузить?', reply_markup=kb)
            return
        if parts[1].strip().lower() not in {'all', 'все', 'global'}:
            tenant_id = parts[1].strip()
            if not tenant_get(tenant_id):
                bot.reply_to(msg, '⛔ Пространство не найдено.')
                return
            scope = 'tenant'
        else:
            scope = 'global'
    elif _v153_can_manage_tenant(uid, tenant_id):
        scope = 'tenant'
    else:
        bot.reply_to(msg, '⛔ Недостаточно прав для полного экспорта.')
        return
    submit_interactive_file_job(chat_id, 'json_full', 'Полное состояние бота' if scope == 'global' else 'Состояние пространства', _v153_send_full_export, chat_id, scope, tenant_id if scope == 'tenant' else None)

def v153_cmd_restore(msg):
    uid = _v153_actor_id(msg)
    chat_id = int(msg.chat.id)
    try:
        gz = _v153_download_replied_document(msg)
        manifest, raw = _v153_validate_restore_gz(gz)
        scope = str(manifest.get('scope') or '')
        tenant_id = str(manifest.get('tenant_id') or _v153_tenant_for_chat(chat_id))
        if scope == 'global' and (not _v153_platform_owner(uid)):
            raise RuntimeError('Глобальное восстановление доступно только владельцу платформы')
        if scope == 'tenant' and (not _v153_can_manage_tenant(uid, tenant_id)):
            current = _v153_tenant_for_chat(chat_id)
            if not _v153_can_manage_tenant(uid, current):
                raise RuntimeError('Нельзя восстановить чужое пространство')
            tenant_id = current
        token = _v153_hashlib.sha256(f'{uid}:{chat_id}:{_v153_time.time_ns()}'.encode()).hexdigest()[:16]
        with _V153_LOCK:
            _V153_RESTORE_PENDING[token] = {'uid': uid, 'chat_id': chat_id, 'gz': gz, 'raw': raw, 'manifest': manifest, 'tenant_id': tenant_id, 'created': _v153_time.time()}
        text = f"🧪 Файл проверен.\n\nВерсия: {manifest.get('bot_version')}\nОбласть: {('весь бот' if scope == 'global' else 'пространство')}\nЧатов: {manifest.get('chat_count')}\nFailed-задач: {manifest.get('failed_tasks')}\nСоздан: {manifest.get('created_at')}\n\nПеред применением будет создана резервная копия текущего состояния."
        bot.reply_to(msg, text, reply_markup=_v153_restore_keyboard(token, scope))
    except Exception as exc:
        bot.reply_to(msg, f'❌ Восстановление не подготовлено:\n{v153_redact_text(exc)[:500]}')

def _v241_restore_storage_barrier_begin() -> int:
    """Invalidate queued pre-restore backup work before replacing canonical state."""
    epoch = int(globals().get('_V241_STORAGE_EPOCH', 0) or 0) + 1
    globals()['_V241_STORAGE_EPOCH'] = epoch
    globals()['_V241_RESTORE_ACTIVE'] = True
    globals()['_V240_RECOVERY_AUTHORITY_ACTIVE'] = True
    sched = globals().get('DELAYED_SCHEDULER')
    if sched is not None:
        for key in ('mega-delta-batch-v90', 'mega-global-quiet-v90', 'mega-global-max-v90', 'mega-global-retry-v90', 'mega-global-user-idle-v190', 'telegram-delta-batch-v234', 'telegram-full-quiet-v234', 'telegram-full-max-v234', 'config-checkpoint-sync-v234'):
            try:
                sched.cancel(key)
            except Exception:
                pass
        try:
            ids = set((globals().get('_backup_timers') or {}).keys()) | set((globals().get('_quick_backup_timers') or {}).keys())
            for cid in ids:
                try:
                    sched.cancel(f'full-backup:{int(cid)}')
                except Exception:
                    pass
        except Exception:
            pass
    lock = globals().get('timer_lock')
    try:
        if lock is not None:
            with lock:
                for name in ('_backup_timers', '_quick_backup_timers'):
                    obj = globals().get(name)
                    if hasattr(obj, 'clear'):
                        obj.clear()
                for name in ('_backup_dirty_chats', '_quick_backup_dirty_chats'):
                    obj = globals().get(name)
                    if hasattr(obj, 'clear'):
                        obj.clear()
    except Exception:
        pass
    try:
        dlock = globals().get('_V240_PENDING_DOMAIN_LOCK')
        pending = globals().get('_V240_PENDING_DOMAINS')
        if dlock is not None and hasattr(pending, 'clear'):
            with dlock:
                pending.clear()
    except Exception:
        pass
    try:
        bot_journal('restore_storage_barrier_v241', int(OWNER_ID or 0) or None, f'begin epoch={epoch}')
    except Exception:
        pass
    return epoch

def _v241_restore_storage_barrier_end(epoch: int, success: bool) -> None:
    globals()['_V241_RESTORE_ACTIVE'] = False
    globals()['_V240_RECOVERY_AUTHORITY_ACTIVE'] = False
    try:
        bot_journal('restore_storage_barrier_v241', int(OWNER_ID or 0) or None, f'end epoch={int(epoch)}; success={int(bool(success))}')
    except Exception:
        pass

def _v153_backup_before_restore() -> str:
    """Always create a local safety copy; try durable witnesses without blocking restore.

    v240 Recovery Authority is intentionally independent of the normal storage mode.
    """
    _recovery_was_active = bool(globals().get('_V240_RECOVERY_AUTHORITY_ACTIVE', False))
    globals()['_V240_RECOVERY_AUTHORITY_ACTIVE'] = True
    folder = _v153_tempfile.mkdtemp(prefix='v240_pre_restore_')
    raw = _v153_os.path.join(folder, 'pre_restore.sqlite3')
    SQLITE.backup_to(raw)
    gz = raw + '.gz'
    with open(raw, 'rb') as fin, _v153_gzip.open(gz, 'wb', compresslevel=5) as fout:
        _v153_shutil.copyfileobj(fin, fout, 1024 * 1024)
    errors = []
    durable = False
    try:
        if mega_is_configured():
            durable = bool(mega_put_replace(gz, f"{MEGA_BACKUP_DIR.rstrip('/')}/database/pre_restore", f"pre_restore_{now_local().strftime('%Y%m%d_%H%M%S')}.sqlite3.gz", archive_previous=False))
            if not durable:
                errors.append('MEGA pre_restore returned false')
    except Exception as exc:
        errors.append('MEGA: ' + str(exc)[:220])
    if not durable:
        try:
            if bool(globals().get('telegram_durable_available_v237_1', lambda: False)()):
                snap_fn = globals().get('telegram_upload_sqlite_snapshot_v234')
                durable = bool(callable(snap_fn) and snap_fn(force=True))
                if not durable:
                    errors.append('Telegram pre_restore returned false')
        except Exception as exc:
            errors.append('Telegram: ' + str(exc)[:220])
    SQLITE.set_meta('restore_control_v240', 'last_pre_restore', {'at': now_local().isoformat(timespec='microseconds'), 'durable': bool(durable), 'errors': errors[-4:], 'local_path': raw})
    try:
        bot_journal('pre_restore_v240', int(OWNER_ID or 0) or None, f"durable={int(durable)}; errors={' | '.join(errors)[:500]}", 'INFO' if durable else 'WARN')
    except Exception:
        pass
    globals()['_V240_RECOVERY_AUTHORITY_ACTIVE'] = bool(_recovery_was_active or globals().get('_V241_RESTORE_ACTIVE', False))
    return folder

def _v153_apply_global_restore(raw: str) -> None:
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
        if '_v184_post_restore_rehydrate' in globals():
            _v184_post_restore_rehydrate(data)
    except Exception as exc:
        log_error(f'v184 global GZ post-restore rehydrate: {exc}')
    save_data(data, full=True)

def _v153_retarget_tenant_value(value, source_tenant: str, target_tenant: str):
    if isinstance(value, dict):
        return {str(k): _v153_retarget_tenant_value(v, source_tenant, target_tenant) for k, v in value.items()}
    if isinstance(value, list):
        return [_v153_retarget_tenant_value(v, source_tenant, target_tenant) for v in value]
    if isinstance(value, str) and value == str(source_tenant):
        return str(target_tenant)
    return _v153_copy.deepcopy(value)

def _v153_remove_scope_from_root_value(value, target_tenant: str, target_chat_ids: set[int]):
    if isinstance(value, list):
        return [x for x in value if not _v153_item_in_tenant_scope(x, target_tenant, target_chat_ids)]
    if isinstance(value, dict):
        return {str(k): v for k, v in value.items() if not _v153_item_in_tenant_scope(v, target_tenant, target_chat_ids, str(k))}
    return value

def _v153_restore_tenant_root(source_root: dict, manifest: dict, target_tenant: str, target_chat_ids: set[int], mode: str) -> dict[int, int]:
    source_tenant = str(manifest.get('tenant_id') or target_tenant)
    source_chat_ids = {int(x) for x in manifest.get('chat_ids') or []}
    live_gs = data.setdefault('_global_settings', {})
    live_tenants = _tenants_root()
    current_row = tenant_get(target_tenant) or {}
    source_gs = (source_root or {}).get('_global_settings') or {}
    source_row = ((source_gs.get('tenants_v148') or {}).get('tenants') or {}).get(source_tenant) or {}
    imported_row = _v153_retarget_tenant_value(v153_sanitize(source_row), source_tenant, target_tenant)
    imported_row['id'] = str(target_tenant)
    imported_row['owner_user_id'] = int(current_row.get('owner_user_id') or imported_row.get('owner_user_id') or 0)
    imported_row['chat_ids'] = sorted(source_chat_ids)
    imported_row['root_chat_id'] = int(imported_row.get('root_chat_id') or next(iter(sorted(source_chat_ids)), 0))
    live_tenants.setdefault('tenants', {})[str(target_tenant)] = imported_row
    for cid in source_chat_ids:
        live_tenants.setdefault('chat_to_tenant', {})[str(cid)] = str(target_tenant)
    remap = {}
    source_rem = (source_gs.get('reminders_v2') or {}).get('items') or {}
    live_rem = live_gs.setdefault('reminders_v2', {'next_id': 1, 'items': {}, 'migrated_v134': True})
    live_items = live_rem.setdefault('items', {})
    if mode == 'replace':
        for rid, cfg in list(live_items.items()):
            if _v153_item_in_tenant_scope(cfg, target_tenant, target_chat_ids):
                live_items.pop(str(rid), None)
    next_id = max([int(x) for x in live_items if str(x).isdigit()] + [int(live_rem.get('next_id') or 1), 1])
    for rid_s, cfg in source_rem.items():
        old_id = int(rid_s) if str(rid_s).isdigit() else 0
        new_id = old_id
        if str(new_id) in live_items and (not _v153_item_in_tenant_scope(live_items.get(str(new_id)), target_tenant, target_chat_ids)):
            next_id += 1
            new_id = next_id
        row = _v153_retarget_tenant_value(cfg, source_tenant, target_tenant)
        row['tenant_id'] = str(target_tenant)
        live_items[str(new_id)] = row
        remap[old_id] = new_id
    live_rem['next_id'] = max([int(x) for x in live_items if str(x).isdigit()] + [1]) + 1
    live_rem['migrated_v134'] = True
    for gs_key in ('operation_ledger_v141', 'finance_integrity_v141'):
        src_value = source_gs.get(gs_key)
        if src_value is None:
            continue
        if mode == 'replace' and gs_key in live_gs:
            if gs_key == 'operation_ledger_v141':
                old_live = live_gs.get(gs_key) or {}
                kept_items = {str(k): v for k, v in (old_live.get('items') or {}).items() if not _v153_item_in_tenant_scope(v, target_tenant, target_chat_ids, str(k))}
                live_gs[gs_key] = {'items': kept_items, 'order': [str(x) for x in old_live.get('order') or [] if str(x) in kept_items], 'next_seq': int(old_live.get('next_seq') or 1)}
            elif gs_key == 'finance_integrity_v141':
                old_live = live_gs.get(gs_key) or {}
                live_gs[gs_key] = {'events': [x for x in old_live.get('events') or [] if not _v153_item_in_tenant_scope(x, target_tenant, target_chat_ids)], 'tips': {str(k): v for k, v in (old_live.get('tips') or {}).items() if not (str(k).lstrip('-').isdigit() and int(k) in target_chat_ids)}, 'anchor': {}, 'event_seq': int(old_live.get('event_seq') or 0)}
        if gs_key == 'operation_ledger_v141':
            live = live_gs.setdefault(gs_key, {'items': {}, 'order': [], 'next_seq': 1})
            for op_id, row in ((src_value or {}).get('items') or {}).items():
                target_id = str(op_id)
                while target_id in (live.get('items') or {}):
                    target_id = target_id + '_r'
                live.setdefault('items', {})[target_id] = _v153_retarget_tenant_value(row, source_tenant, target_tenant)
                live.setdefault('order', []).append(target_id)
            live['next_seq'] = max(int(live.get('next_seq') or 1), int((src_value or {}).get('next_seq') or 1))
        elif gs_key == 'finance_integrity_v141':
            live = live_gs.setdefault(gs_key, {'events': [], 'tips': {}, 'anchor': {}, 'event_seq': 0})
            live.setdefault('events', []).extend(_v153_retarget_tenant_value((src_value or {}).get('events') or [], source_tenant, target_tenant))
            live.setdefault('tips', {}).update((src_value or {}).get('tips') or {})
            live['event_seq'] = max(int(live.get('event_seq') or 0), int((src_value or {}).get('event_seq') or 0))
    for key, src_value in (source_root or {}).items():
        if key == '_global_settings':
            continue
        src_value = _v153_retarget_tenant_value(src_value, source_tenant, target_tenant)
        if mode == 'replace' and key in data:
            data[key] = _v153_remove_scope_from_root_value(data.get(key), target_tenant, target_chat_ids)
        if isinstance(src_value, list):
            live = data.setdefault(key, [])
            seen = {_v153_json.dumps(x, sort_keys=True, ensure_ascii=False, default=str) for x in live if isinstance(live, list)}
            for item in src_value:
                sig = _v153_json.dumps(item, sort_keys=True, ensure_ascii=False, default=str)
                if sig not in seen:
                    live.append(item)
                    seen.add(sig)
        elif isinstance(src_value, dict):
            data.setdefault(key, {}).update(src_value)
    return remap

def _v153_apply_tenant_restore(raw: str, target_tenant: str, mode: str='replace') -> None:
    mode = 'replace'
    src = _v153_sqlite3.connect(raw)
    src.row_factory = _v153_sqlite3.Row
    try:
        manifest = _v153_json.loads(src.execute("SELECT v FROM meta WHERE kind='v153_export' AND k='manifest'").fetchone()[0])
        source_chat_ids = {int(x) for x in manifest.get('chat_ids') or []}
        root_row = src.execute("SELECT v FROM kv WHERE k='root'").fetchone()
        source_root = _v153_json.loads(root_row[0]) if root_row else {}
        target_row = tenant_get(target_tenant) or {}
        target_chat_ids = set((int(x) for x in target_row.get('chat_ids') or []))
        for cid in source_chat_ids:
            current_tenant = str(tenant_id_for_chat(cid, create=False) or '')
            if current_tenant and current_tenant != str(target_tenant) and (cid not in target_chat_ids):
                raise RuntimeError(f'Чат {cid} сейчас принадлежит другому пространству')
        if mode == 'replace':
            for cid in list(target_chat_ids - source_chat_ids):
                data.get('chats', {}).pop(str(cid), None)
                SQLITE.delete_chat(cid)
                for key in list(LOWRAM_COLD_KEYS):
                    SQLITE.delete_cold(cid, key)
            try:
                root = _tenants_root()
                row = (root.get('tenants') or {}).get(str(target_tenant)) or target_row
                row['chat_ids'] = sorted(source_chat_ids)
                if int(row.get('root_chat_id') or 0) not in source_chat_ids:
                    row['root_chat_id'] = next(iter(sorted(source_chat_ids)), 0)
                mapping = root.setdefault('chat_to_tenant', {})
                for cid in target_chat_ids - source_chat_ids:
                    if str(mapping.get(str(cid)) or '') == str(target_tenant):
                        mapping.pop(str(cid), None)
            except Exception:
                pass
        for row in src.execute('SELECT chat_id,v FROM chats').fetchall():
            cid = int(row[0])
            payload = _v153_json.loads(row[1])
            data.setdefault('chats', {})[str(cid)] = _lowram_wrap_store(cid, payload)
            SQLITE.save_chat(cid, _lowram_store_meta_payload(payload))
        for row in src.execute('SELECT chat_id,k,v FROM cold_fields').fetchall():
            cid = int(row[0])
            key = str(row[1])
            value = _v153_json.loads(row[2])
            SQLITE.set_cold(cid, key, value)
        _v153_restore_tenant_root(source_root, manifest, target_tenant, target_chat_ids, mode)
        for cid in source_chat_ids:
            tenant_bind_chat(cid, target_tenant, changed_by=0, force=True)
        try:
            tenant_v148_enforce_forward_isolation()
        except Exception:
            pass
        try:
            if '_v184_post_restore_rehydrate' in globals():
                _v184_post_restore_rehydrate(data, source_chat_ids)
        except Exception as exc:
            log_error(f'v184 tenant GZ post-restore rehydrate: {exc}')
        save_data(data, full=True)
    finally:
        src.close()

def _v153_restore_failed_tasks_from_db(raw: str, allowed_chat_ids: set[int] | None=None) -> int:
    """Restore exported failed-task files through HEAVY; FAST has no runtime MEGA credentials."""
    conn = _v153_sqlite3.connect(raw)
    try:
        row = conn.execute("SELECT v FROM meta WHERE kind='v153_export' AND k='failed_tasks'").fetchone()
        tasks = _v153_json.loads(row[0]) if row else []
    finally:
        conn.close()
    selected = []
    for task in tasks or []:
        if not isinstance(task, dict) or task.get('load_error'):
            continue
        cid = int(task.get('chat_id') or 0)
        if allowed_chat_ids is not None and cid not in allowed_chat_ids:
            continue
        key = str(task.get('task_id') or task.get('update_id') or task.get('job_id') or '').strip()
        if not key:
            continue
        clean = v153_sanitize(task)
        clean['_restore_key_v153'] = key
        selected.append(clean)
    if not selected:
        return 0
    base = globals().get('_split_peer_base', lambda: '')()
    headers_fn = globals().get('_split_headers')
    if not base or not callable(headers_fn):
        raise RuntimeError('HEAVY peer unavailable for failed-task restore')
    restored = 0
    # Keep the request bounded; HEAVY owns all MEGA I/O and verifies every batch.
    for pos in range(0, len(selected), 50):
        chunk = selected[pos:pos + 50]
        response = requests.post(
            str(base).rstrip('/') + '/internal/restore/failed-tasks',
            json={'tasks': chunk},
            headers=headers_fn('vys-262-r49-restore-failed-tasks'),
            timeout=180,
        )
        if not (200 <= response.status_code < 300):
            raise RuntimeError(f'HEAVY failed-task restore HTTP {response.status_code}: {response.text[:220]}')
        body = response.json() if response.content else {}
        if not bool(body.get('ok')) or int(body.get('restored') or 0) != len(chunk):
            raise RuntimeError('HEAVY failed-task restore incomplete: ' + str(body)[:260])
        restored += int(body.get('restored') or 0)
    return restored


def _v240_retry_pending_restore_reanchor() -> bool:
    """Retry manual-restore publication through HEAVY; FAST never touches MEGA at runtime."""
    pending = SQLITE.get_meta('restore_control_v240', 'remote_reanchor_pending', {}) or {}
    if not isinstance(pending, dict) or not pending:
        return True
    if bool(globals().get('_V241_RESTORE_ACTIVE', False)):
        _v240_schedule_pending_restore_reanchor_retry(30.0)
        return False
    try:
        push = globals().get('_split_push_snapshot_now_v263')
        if not callable(push) or not bool(push('restore_retry:' + str(pending.get('reason') or 'restore'), sync_mega=True)):
            raise RuntimeError('HEAVY did not confirm MEGA publication')
        SQLITE.set_meta('restore_control_v240', 'remote_reanchor_pending', {})
        SQLITE.set_meta('restore_control_v240', 'config_remote_pending', {})
        try: runtime_event('restore_remote_reanchor_completed_v240', 'backend=HEAVY->MEGA', 'INFO')
        except Exception: pass
        return True
    except Exception as exc:
        pending['last_retry_at'] = now_local().isoformat(timespec='microseconds')
        pending['last_retry_error'] = str(exc)[:500]
        pending['retry_count'] = int(pending.get('retry_count') or 0) + 1
        SQLITE.set_meta('restore_control_v240', 'remote_reanchor_pending', pending)
        delay = min(600.0, 30.0 * 2 ** min(4, int(pending.get('retry_count') or 1) - 1))
        _v240_schedule_pending_restore_reanchor_retry(delay)
        try: runtime_event('restore_remote_reanchor_retry_failed_v240', str(exc)[:500], 'WARN')
        except Exception: pass
        return False

def _v240_schedule_pending_restore_reanchor_retry(delay: float=20.0):
    sched = globals().get('DELAYED_SCHEDULER')
    if sched is None:
        return None
    try:
        sched.cancel('restore-remote-reanchor-v240')
    except Exception:
        pass
    return sched.schedule('restore-remote-reanchor-v240', max(5.0, float(delay)), _v240_retry_pending_restore_reanchor)

def _canon_v240_restore_reanchor_guaranteed__001(reason: str) -> dict:
    """Never revert a user-confirmed restore because remote re-anchor is unavailable.

    Normal path remains exact durable. On failure, the restored SQLite becomes the local
    canonical state immediately and a remote re-anchor is marked pending for retry.
    """
    try:
        result = constitution_reanchor_after_manual_restore(str(reason))
        result['remote_confirmed_v240'] = True
        SQLITE.set_meta('restore_control_v240', 'remote_reanchor_pending', {})
        return result
    except Exception as exc:
        err = str(exc)[:600]
        try:
            lineage_fn = globals().get('_v239_storage_lineage')
            lineage = str(lineage_fn(True) if callable(lineage_fn) else '')
        except Exception:
            lineage = ''
        try:
            cp = config_guard_accept_current_v234('restore_local_fallback_v240:' + str(reason))
        except Exception:
            cp = {}
        try:
            # R48: save/snapshot functions own their short locks; no global lock across SQLite.
            save_data(data, full=True)
            embedded = constitution_semantic_manifest_from_live()
            embedded['snapshot_created_at'] = now_local().isoformat(timespec='microseconds')
            embedded['restore_reason_v240'] = str(reason)
            embedded['storage_lineage_v239'] = lineage
            SQLITE.set_meta('data_constitution_snapshot', 'main', embedded)
        except Exception:
            pass
        pending = {'at': now_local().isoformat(timespec='microseconds'), 'reason': str(reason), 'error': err, 'lineage': lineage, 'config_generation': int((cp or {}).get('generation') or 0)}
        SQLITE.set_meta('restore_control_v240', 'remote_reanchor_pending', pending)
        try:
            _v240_schedule_pending_restore_reanchor_retry(20.0)
        except Exception:
            pass
        try:
            init_delta = globals().get('initialize_delta_baseline')
            if callable(init_delta):
                init_delta(data)
        except Exception:
            pass
        try:
            constitution_clear_quarantine('manual restore accepted locally; remote re-anchor pending v240')
        except Exception:
            pass
        try:
            runtime_event('restore_remote_reanchor_pending_v240', err, 'WARN')
        except Exception:
            pass
        return {'checkpoint': {}, 'config_checkpoint': cp, 'active': {'backend': 'local', 'generation': 'LOCAL-PENDING'}, 'lineage': lineage, 'remote_confirmed_v240': False, 'warning': err}

def _v153_execute_restore(token: str, mode: str, call) -> bool:
    mode = 'replace'
    with _V153_LOCK:
        row = _V153_RESTORE_PENDING.pop(str(token), None)
    if not row:
        try:
            bot.answer_callback_query(call.id, 'Файл восстановления устарел', show_alert=True)
        except Exception:
            pass
        return True
    uid = _v153_actor_id(call)
    if uid != int(row.get('uid') or 0) and (not _v153_platform_owner(uid)):
        try:
            bot.answer_callback_query(call.id, 'Это подтверждение другого пользователя', show_alert=True)
        except Exception:
            pass
        return True
    backup_dir = ''
    restore_epoch = 0
    restore_success = False
    try:
        restore_epoch = _v241_restore_storage_barrier_begin()
        backup_dir = _v153_backup_before_restore()
        scope = str((row.get('manifest') or {}).get('scope') or '')
        if scope == 'global':
            _v153_apply_global_restore(str(row['raw']))
            restored_failed = _v153_restore_failed_tasks_from_db(str(row['raw']), None)
        else:
            _v153_apply_tenant_restore(str(row['raw']), str(row['tenant_id']), str(mode))
            restored_failed = _v153_restore_failed_tasks_from_db(str(row['raw']), set((int(x) for x in (row.get('manifest') or {}).get('chat_ids') or [])))
        constitution_result = _v240_restore_reanchor_guaranteed(f'gz_restore:{scope}:{mode}')
        remote_ok = bool(constitution_result.get('remote_confirmed_v240', True))
        redis_fn = globals().get('r64_publish_restore_snapshot_v271')
        redis_result = redis_fn(f'gz_restore:{scope}:{mode}') if callable(redis_fn) else {'required': False, 'ok': False, 'detail': 'R64 Redis seal helper unavailable'}
        redis_required = bool((redis_result or {}).get('required'))
        redis_ok = bool((redis_result or {}).get('ok'))
        suffix = '' if remote_ok else '\n⚠️ Remote re-anchor временно pending; восстановленное состояние уже принято локально.'
        if redis_required and redis_ok:
            suffix += f"\n🧠 Redis: full SQLite snapshot проверен ({int((redis_result or {}).get('size') or 0)} B)."
            headline = '✅ Восстановление завершено и закреплено в Redis.'
        elif redis_required:
            suffix += '\n⛔ Redis snapshot НЕ закреплён: ' + str((redis_result or {}).get('detail') or 'unknown')[:320]
            headline = '⚠️ База восстановлена локально, но Redis recovery НЕ закреплён.'
        else:
            suffix += '\nℹ️ Redis recovery не настроен в Render.'
            headline = '✅ Восстановление завершено.'
        safe_edit(bot, call, f"{headline}\nGeneration: {(constitution_result.get('active') or {}).get('generation', '—')}\nFailed-задач восстановлено: {restored_failed}." + suffix)
        restore_success = True
        bot_journal('v240_restore_applied', int(row['chat_id']), f"scope={scope}; mode={mode}; tenant={row.get('tenant_id')}; by={uid}; constitution=1; remote_confirmed={int(remote_ok)}; redis_required={int(redis_required)}; redis_ok={int(redis_ok)}; epoch={restore_epoch}")
    except Exception as exc:
        safe_edit(bot, call, f'❌ Восстановление остановлено:\n{v153_redact_text(exc)[:800]}')
        bot_journal('v153_restore_failed', int(row['chat_id']), v153_redact_text(exc), 'ERROR')
    finally:
        for path in {row.get('gz'), row.get('raw')}:
            try:
                if path:
                    _v153_shutil.rmtree(_v153_os.path.dirname(str(path)), ignore_errors=True)
            except Exception:
                pass
        if backup_dir:
            _v153_shutil.rmtree(backup_dir, ignore_errors=True)
        if restore_epoch:
            _v241_restore_storage_barrier_end(restore_epoch, restore_success)
    return True
_V153_UI_CACHE = {}

def _v153_ui_sig(kind: str, chat_id, message_id, payload, markup=None) -> str:
    try:
        markup_value = markup.to_json() if hasattr(markup, 'to_json') else repr(markup)
    except Exception:
        markup_value = repr(markup)
    raw = _v153_json.dumps([kind, int(chat_id), int(message_id), str(payload or ''), markup_value], ensure_ascii=False, default=str)
    return _v153_hashlib.sha256(raw.encode('utf-8')).hexdigest()

def _v153_ui_cached(sig: str):
    with _V153_LOCK:
        row = _V153_UI_CACHE.get(sig)
        if row and _v153_time.monotonic() - float(row[0]) <= 120.0:
            return row[1]
        for key, item in list(_V153_UI_CACHE.items()):
            if _v153_time.monotonic() - float(item[0]) > 180.0:
                _V153_UI_CACHE.pop(key, None)
    return None

def _v153_ui_remember(sig: str, result):
    with _V153_LOCK:
        _V153_UI_CACHE[sig] = (_v153_time.monotonic(), result)
    return result
# FINALIZED: edit/delete idempotence is executed in the single Telegram transport.

def _v179_base_reconcile_windows() -> dict:
    result = cleanup_open_window_registry('v153_periodic') if 'cleanup_open_window_registry' in globals() else {}
    try:
        bot_journal('v153_window_reconcile', None, result)
    except Exception:
        pass
    return result

def _v153_handler_audit() -> dict:
    commands = {}
    duplicates = []
    handlers_without_filters = 0
    for handler in list(getattr(bot, 'message_handlers', []) or []):
        filters = handler.get('filters', {}) if isinstance(handler, dict) else {}
        fn = handler.get('function') if isinstance(handler, dict) else None
        rows = filters.get('commands') or []
        if not filters:
            handlers_without_filters += 1
        for command in rows:
            key = str(command).lower()
            if key in commands and commands[key] is not fn:
                duplicates.append(key)
            commands[key] = fn
    callback_count = len(list(getattr(bot, 'callback_query_handlers', []) or []))
    return {'commands': len(commands), 'duplicate_commands': sorted(set(duplicates)), 'message_handlers': len(list(getattr(bot, 'message_handlers', []) or [])), 'callback_handlers': callback_count, 'handlers_without_filters': handlers_without_filters, 'known_commands': sorted(commands)}

def _v153_runtime_audit_text() -> str:
    a = _v153_handler_audit()
    stats = mega_task_registry_stats()
    migration = _v153_migration_store()
    lines = ['ГЛУБОКИЙ АУДИТ v153', f'Создан: {_v153_now()}', '', f"Slash-команд: {a['commands']}; дублей: {', '.join(a['duplicate_commands']) or 'нет'}.", f"Message handlers: {a['message_handlers']}; callback handlers: {a['callback_handlers']}.", 'Команды /json_full, /restore и /full_audit имеют отдельные обработчики и проверку прав.', 'Callback подтверждения защищены одноразовыми token и actor check.', 'Повторная выгрузка не создаёт очередь: одно INFO-сообщение становится кнопкой скачивания.', 'Telegram message is not modified считается идемпотентным результатом, а не ошибкой бизнеса.', 'Явный chat not found для известного чата означает bot_removed; timeout/429/сетевая ошибка остаются unreachable; lifecycle active/unreachable/bot_removed/migrated/archived сохраняется в runtime ZIP.', 'Runtime ZIP скачивает slots/events; устаревшие candidate/staged остаются только в индексе и очищаются до 2 файлов.', f"Durable failed: {stats.get('failed', 0)}; details: {len(stats.get('failed_details') or [])}; pending_detail_refresh={bool(stats.get('failed_details_pending'))}.", 'Reminder witnesses принимаются только при явном EDITREM/EDITREMINT, поэтому финансовая задача не требует reminder_edit.', 'Секреты очищаются перед журналом, snapshot, ZIP/TXT/JSON export и отправкой документа.', f"MEGA root v238: один canonical {globals().get('MEGA_BACKUP_DIR')}; legacy migration state удалён."]
    return '\n'.join(lines)

def v153_cmd_full_audit(msg):
    uid = _v153_actor_id(msg)
    if not _v153_platform_owner(uid):
        bot.reply_to(msg, '⛔ Аудит доступен только владельцу платформы.')
        return
    bot.reply_to(msg, _v153_runtime_audit_text()[:3900])

def v153_cmd_mega_migration_status(msg):
    uid = _v153_actor_id(msg)
    if not _v153_platform_owner(uid):
        return
    bot.reply_to(msg, f"☁️ Хранилище MEGA\n✅ v238: один канонический корень\nАктивная папка: {globals().get('MEGA_BACKUP_DIR')}\nПодкорневые release-каталоги и legacy migration state не используются.")

def _v153_callback_once(call, key: str) -> bool:
    now = _v153_time.time()
    actor = _v153_actor_id(call)
    receipt = f"{actor}:{getattr(call, 'id', '')}:{key}"
    with _V153_LOCK:
        for old, ts in list(_V153_CALLBACK_RECEIPTS.items()):
            if now - ts > 600:
                _V153_CALLBACK_RECEIPTS.pop(old, None)
        if receipt in _V153_CALLBACK_RECEIPTS:
            return False
        _V153_CALLBACK_RECEIPTS[receipt] = now
    return True
def _v153_extension_callback(call, data_str: str) -> bool:
    data_str = str(data_str or '')
    if data_str in {'r57:startup:details', 'r57:startup:compact'}:
        uid = _v153_actor_id(call)
        if not _v153_platform_owner(uid):
            return True
        try:
            bot.answer_callback_query(call.id)
        except Exception:
            pass
        if data_str.endswith(':details'):
            safe_edit(bot, call, _r57_startup_details_text(), reply_markup=_r57_startup_keyboard(True))
        else:
            safe_edit(bot, call, _r57_startup_compact_text(), reply_markup=_r57_startup_keyboard(False))
        return True
    if data_str == 'runtime_watcher':
        uid = _v153_actor_id(call)
        chat_id = int(call.message.chat.id)
        if not _v153_platform_owner(uid):
            return False
        kbw = types.InlineKeyboardMarkup()
        kbw.row(IB('🔄 Обновить', callback_data='runtime_watcher'), IB('📜 События', callback_data='runtime_events'))
        kbw.row(IB('☁️ Снимок Watcher в MEGA', callback_data='runtime_snapshot_now'))
        kbw.row(IB('📦 Runtime ZIP', callback_data='runtime_export'), IB('🗄 /json_full', callback_data='v153:json:menu'))
        kbw.row(IB('🚦 Очереди', callback_data='info_queues'), IB('🧩 Delta', callback_data='info_delta_status'))
        day = get_chat_store(chat_id).get('current_view_day') or today_key()
        kbw.row(IB('🔙 Назад в Инфо', callback_data=f'd:{day}:info'), IB('❌ Закрыть', callback_data='info_close'))
        safe_edit(bot, call, build_runtime_watcher_text(), reply_markup=kbw)
        return True
    if data_str == 'v153:json:menu':
        uid = _v153_actor_id(call)
        chat_id = int(call.message.chat.id)
        if not _v153_platform_owner(uid):
            tenant_id = _v153_tenant_for_chat(chat_id)
            if _v153_can_manage_tenant(uid, tenant_id):
                submit_interactive_file_job(chat_id, 'json_full', 'Состояние пространства', _v153_send_full_export, chat_id, 'tenant', tenant_id)
            return True
        kb = types.InlineKeyboardMarkup()
        kb.row(IB('🌐 Весь бот', callback_data='v153:json:global'))
        for tenant in tenant_all() or []:
            tid = str((tenant or {}).get('id') or '')
            if tid:
                kb.row(IB(f"🏠 {(tenant or {}).get('name') or tid}", callback_data=f'v153:json:tenant:{tid}'))
        safe_edit(bot, call, '🗄 Что выгрузить?', reply_markup=kb)
        return True
    if data_str == 'v153:json:global':
        uid = _v153_actor_id(call)
        chat_id = int(call.message.chat.id)
        if not _v153_platform_owner(uid):
            try:
                bot.answer_callback_query(call.id, 'Только для владельца платформы', show_alert=True)
            except Exception:
                pass
            return True
        submit_interactive_file_job(chat_id, 'json_full', 'Полное состояние бота', _v153_send_full_export, chat_id, 'global', None)
        return True
    if data_str.startswith('v153:json:tenant:'):
        uid = _v153_actor_id(call)
        chat_id = int(call.message.chat.id)
        tenant_id = data_str.split(':', 3)[3]
        if not (_v153_platform_owner(uid) or _v153_can_manage_tenant(uid, tenant_id)):
            try:
                bot.answer_callback_query(call.id, 'Недостаточно прав', show_alert=True)
            except Exception:
                pass
            return True
        submit_interactive_file_job(chat_id, 'json_full', 'Состояние пространства', _v153_send_full_export, chat_id, 'tenant', tenant_id)
        return True
    if data_str.startswith('v153:file:'):
        token = data_str.split(':', 2)[2]
        with _V153_LOCK:
            row = _V153_READY_EXPORTS.pop(token, None)
        if not row:
            try:
                bot.answer_callback_query(call.id, 'Запрос уже использован или устарел', show_alert=True)
            except Exception:
                pass
            return True
        if int(row.get('chat_id') or 0) != int(call.message.chat.id):
            try:
                bot.answer_callback_query(call.id, 'Это кнопка другого чата', show_alert=True)
            except Exception:
                pass
            return True
        if not _v153_callback_once(call, data_str):
            return True
        try:
            safe_edit(bot, call, f"⏳ Запускаю «{row['label']}»…")
        except Exception:
            pass
        submit_interactive_file_job(int(row['chat_id']), row['kind'], row['label'], row['func'], *row['args'], **row['kwargs'])
        return True
    if data_str.startswith('v153:restore:'):
        parts = data_str.split(':')
        if len(parts) >= 4:
            token, action = (parts[2], parts[3])
            if action == 'cancel':
                with _V153_LOCK:
                    current = _V153_RESTORE_PENDING.get(token)
                    if current and current.get('_restore_queued'):
                        row = None
                        already_started = True
                    else:
                        row = _V153_RESTORE_PENDING.pop(token, None)
                        already_started = False
                if already_started:
                    try: bot.answer_callback_query(call.id, 'Восстановление уже запущено и не может быть отменено.', show_alert=True)
                    except Exception: pass
                    return True
                if row:
                    for path in (row.get('gz'), row.get('raw')):
                        try:
                            _v153_shutil.rmtree(_v153_os.path.dirname(str(path)), ignore_errors=True)
                        except Exception:
                            pass
                safe_edit(bot, call, '❌ Восстановление отменено.')
                return True
            if action == 'merge':
                try:
                    bot.answer_callback_query(call.id, 'Объединение через /restore отключено. Запустите /restore заново.', show_alert=True)
                except Exception:
                    pass
                return True
            if action == 'replace':
                uid = _v153_actor_id(call)
                with _V153_LOCK:
                    row = _V153_RESTORE_PENDING.get(token)
                    if not row:
                        already = False
                        allowed = False
                    else:
                        allowed = bool(uid == int(row.get('uid') or 0) or _v153_platform_owner(uid))
                        already = bool(row.get('_restore_queued'))
                        if allowed and not already:
                            row['_restore_queued'] = True
                if not row:
                    try: bot.answer_callback_query(call.id, 'Файл восстановления устарел', show_alert=True)
                    except Exception: pass
                    return True
                if not allowed:
                    try: bot.answer_callback_query(call.id, 'Это подтверждение другого пользователя', show_alert=True)
                    except Exception: pass
                    return True
                if already:
                    try: bot.answer_callback_query(call.id, 'Восстановление уже выполняется.')
                    except Exception: pass
                    return True
                safe_edit(bot, call, '⏳ Восстановление принято. Выполняю в отдельном recovery-потоке…')
                queued = bool(RECOVERY_TASK_POOL.submit_unique(f'v153-restore:{token}', _v153_execute_restore, token, 'replace', call))
                if not queued:
                    with _V153_LOCK:
                        current = _V153_RESTORE_PENDING.get(token)
                        if current:
                            current['_restore_queued'] = False
                    safe_edit(bot, call, '⚠️ Очередь восстановления занята. Нажмите «Восстановить» ещё раз.')
                return True
    return False

def _v153_prune_restore_pending() -> None:
    now = _v153_time.time()
    expired = []
    with _V153_LOCK:
        for token, row in list(_V153_RESTORE_PENDING.items()):
            if now - float((row or {}).get('created') or 0.0) > V153_RESTORE_PENDING_TTL:
                expired.append(_V153_RESTORE_PENDING.pop(token, None))
    for row in expired:
        for path in ((row or {}).get('gz'), (row or {}).get('raw')):
            try:
                if path:
                    _v153_shutil.rmtree(_v153_os.path.dirname(str(path)), ignore_errors=True)
            except Exception:
                pass

def _v153_add_command(commands, function):
    try:
        decorator = bot.message_handler(commands=list(commands))
        decorator(function)
    except Exception:
        pass

def _v153_replace_restore_handler():
    replaced = 0
    for handler in list(getattr(bot, 'message_handlers', []) or []):
        if not isinstance(handler, dict):
            continue
        filters = handler.get('filters') or {}
        commands = [str(x).lower() for x in filters.get('commands') or []]
        if 'restore' in commands:
            handler['function'] = v153_cmd_restore
            replaced += 1
    if not replaced:
        _v153_add_command(['restore'], v153_cmd_restore)
    return replaced
_v153_add_command(['json_full'], v153_cmd_json_full)
_v153_add_command(['full_audit', 'audit_full'], v153_cmd_full_audit)
_v153_add_command(['mega_migration_status'], v153_cmd_mega_migration_status)
_V153_RESTORE_HANDLERS = _v153_replace_restore_handler()
_V153_CALLBACK_DEDUPE_HANDLERS = 0

def _v177_legacy_0084_runtime_mark_ready(detail: str=''):
    result = _V153_ORIG_RUNTIME_MARK_READY(detail) if callable(_V153_ORIG_RUNTIME_MARK_READY) else None
    try:
        DELAYED_SCHEDULER.schedule('v153-instance-lease', 1.0, lambda: GENERAL_TASK_POOL.submit_unique('v153-instance-lease', _v153_instance_lease_check))
        None
        DELAYED_SCHEDULER.schedule('v153-window-reconcile', 8.0, lambda: GENERAL_TASK_POOL.submit_unique('v153-window-reconcile', _v153_reconcile_windows))
        DELAYED_SCHEDULER.schedule('v153-runtime-cleanup', 12.0, lambda: GENERAL_TASK_POOL.submit_unique('v153-runtime-prune', _v153_runtime_cleanup_remote))
        DELAYED_SCHEDULER.schedule('v153-restore-pending-cleanup', 60.0, _v153_prune_restore_pending)

        def _lease_loop():
            _v153_instance_lease_check()
            try:
                None
            except Exception:
                pass

        def _window_loop():
            _v153_reconcile_windows()
            try:
                None
            except Exception:
                pass
        None
        None
    except Exception:
        pass
    return result
try:
    _v177_legacy_0084_runtime_mark_ready.__name__ = 'runtime_mark_ready'
except Exception:
    pass
try:
    _v177_legacy_0007_bot_journal('v153_remaining_fixes_installed', int(OWNER_ID or 0), f'restore_handlers={_V153_RESTORE_HANDLERS}; callback_dedupe={_V153_CALLBACK_DEDUPE_HANDLERS}; new_mega_root={V153_NEW_MEGA_ROOT}')
except Exception:
    pass
'v154: expense marks in F111/F114 and strict ARS/USD Excel isolation.'
import calendar as _v154_calendar
import copy as _v154_copy
import os as _v154_os
import shutil as _v154_shutil
import sqlite3 as _v154_sqlite3
import gzip as _v154_gzip
import json as _v154_json
_V154_BASE_PERIOD_EXCEL_KEYBOARD = _v177_legacy_0172_period_excel_style_keyboard
_V154_BASE_CATEGORY_COMPACT = _v177_legacy_0177_category_rows_without_description
_V154_BASE_MODERN_COMPACT = _v177_legacy_0100_modern_compact_excel_styles_comments
_V154_BASE_MODERN_SIMPLE = _v177_legacy_0099_modern_simple_excel_styles_comments
_V154_BASE_MODERN_CATEGORY = _v177_legacy_0101_modern_category_excel_styles_comments
_V154_BASE_MODERN_CATEGORY_COMPACT = _v177_legacy_0103_modern_category_no_description_styles_comments

def excel_usd_table_enabled(chat_id: int) -> bool:
    """Whether a separate USD operation table is appended to Excel/Google exports."""
    try:
        settings = get_chat_store(int(chat_id)).setdefault('settings', {})
        return bool(settings.get('excel_include_usd_table', True))
    except Exception:
        return True

def set_excel_usd_table_enabled(chat_id: int, enabled: bool) -> bool:
    chat_id = int(chat_id)
    settings = get_chat_store(chat_id).setdefault('settings', {})
    settings['excel_include_usd_table'] = bool(enabled)
    save_data(data, chat_ids=[chat_id])
    try:
        schedule_config_backup_for_chats(chat_id, delay=0.5)
    except Exception:
        pass
    try:
        bot_journal('excel_usd_table_toggle', chat_id, f'enabled={bool(enabled)}')
    except Exception:
        pass
    return bool(enabled)

def toggle_excel_usd_table_enabled(chat_id: int) -> bool:
    return set_excel_usd_table_enabled(int(chat_id), not excel_usd_table_enabled(int(chat_id)))

def _canon_period_excel_style_keyboard__001(scope: str, target_chat_id: int, mode: str, file_type: str, day_key: str, owner_day_key: str):
    """F179: original controls + an explicit independent USD-table switch."""
    kb = _V154_BASE_PERIOD_EXCEL_KEYBOARD(scope, target_chat_id, mode, file_type, day_key, owner_day_key)
    enabled = excel_usd_table_enabled(int(target_chat_id))
    label = f"{('✅' if enabled else '⬜')} 💵 USD расходы в таблице: {('ВКЛ' if enabled else 'ВЫКЛ')}"
    row = [IB(label, callback_data=export_callback(f'exp_excel_dollar_toggle:{scope}:{int(target_chat_id)}:{mode}:{file_type}:{day_key}:{owner_day_key}'))]
    try:
        insert_at = max(0, len(kb.keyboard) - 2)
        kb.keyboard.insert(insert_at, row)
    except Exception:
        kb.row(*row)
    return kb

def _v154_day_has_expense(chat_id: int | None, day_key: str) -> bool:
    if chat_id is None:
        return False
    try:
        store = get_chat_store(int(chat_id))
        return bool(expense_anchor_records_for_day(store, str(day_key)))
    except Exception:
        return False

def _v177_legacy_0169_export_calendar_start_keyboard(view_year: int, view_month: int, return_day_key: str, chat_id: int | None=None):
    """F111. Mark a date with 📝 only when that day actually has an expense."""
    kb = types.InlineKeyboardMarkup(row_width=7)
    last_day = _v154_calendar.monthrange(int(view_year), int(view_month))[1]
    buttons = []
    for day_num in range(1, last_day + 1):
        day_key = _date_key_from_ymd(view_year, view_month, day_num)
        label = f'📝{day_num}' if _v154_day_has_expense(chat_id, day_key) else str(day_num)
        buttons.append(IB(label, callback_data=export_callback(f'exp_pick_set_start:{view_year}:{view_month}:{day_num}:{return_day_key}')))
    for idx in range(0, len(buttons), 7):
        kb.row(*buttons[idx:idx + 7])
    prev_y, prev_m = _shift_month(view_year, view_month, -1)
    next_y, next_m = _shift_month(view_year, view_month, 1)
    kb.row(IB('⬅️ Месяц', callback_data=export_callback(f'exp_pick_start:{prev_y}:{prev_m}:{return_day_key}')), IB(f'{russian_month_name(view_month)} {view_year}', callback_data='none'), IB('Месяц ➡️', callback_data=export_callback(f'exp_pick_start:{next_y}:{next_m}:{return_day_key}')))
    kb.row(IB('◀️ Год', callback_data=export_callback(f'exp_pick_start:{view_year - 1}:{view_month}:{return_day_key}')), IB(str(view_year), callback_data='none'), IB('Год ▶️', callback_data=export_callback(f'exp_pick_start:{view_year + 1}:{view_month}:{return_day_key}')))
    kb.row(IB('🔙 Назад в CSV / Excel', callback_data=f'd:{return_day_key}:csv_all'))
    return kb
try:
    _v177_legacy_0169_export_calendar_start_keyboard.__name__ = '_export_calendar_start_keyboard'
except Exception:
    pass

def _v177_legacy_0171_export_end_calendar_keyboard(start_key: str, start_rid: int, view_year: int, view_month: int, return_day_key: str, chat_id: int | None=None):
    """F114. Mark selectable dates that contain expenses, without changing range rules."""
    kb = types.InlineKeyboardMarkup(row_width=7)
    last_day = _v154_calendar.monthrange(int(view_year), int(view_month))[1]
    buttons = []
    for day_num in range(1, last_day + 1):
        day_key = _date_key_from_ymd(view_year, view_month, day_num)
        if day_key < start_key:
            buttons.append(IB('·', callback_data='none'))
        else:
            label = f'📝{day_num}' if _v154_day_has_expense(chat_id, day_key) else str(day_num)
            buttons.append(IB(label, callback_data=export_callback(f'exp_pick_set_end:{start_key}:{int(start_rid)}:{view_year}:{view_month}:{day_num}:{return_day_key}')))
    for idx in range(0, len(buttons), 7):
        kb.row(*buttons[idx:idx + 7])
    prev_y, prev_m = _shift_month(view_year, view_month, -1)
    next_y, next_m = _shift_month(view_year, view_month, 1)
    nav = []
    if f'{prev_y:04d}-{prev_m:02d}' >= start_key[:7]:
        nav.append(IB('⬅️ Месяц', callback_data=export_callback(f'exp_pick_end:{start_key}:{int(start_rid)}:{prev_y}:{prev_m}:{return_day_key}')))
    else:
        nav.append(IB(' ', callback_data='none'))
    nav.append(IB(f'{russian_month_name(view_month)} {view_year}', callback_data='none'))
    nav.append(IB('Месяц ➡️', callback_data=export_callback(f'exp_pick_end:{start_key}:{int(start_rid)}:{next_y}:{next_m}:{return_day_key}')))
    kb.row(*nav)
    kb.row(IB('◀️ Год', callback_data=export_callback(f'exp_pick_end:{start_key}:{int(start_rid)}:{view_year - 1}:{view_month}:{return_day_key}')), IB(str(view_year), callback_data='none'), IB('Год ▶️', callback_data=export_callback(f'exp_pick_end:{start_key}:{int(start_rid)}:{view_year + 1}:{view_month}:{return_day_key}')))
    start_dt = datetime.strptime(start_key, '%Y-%m-%d')
    kb.row(IB('🔙 Изменить начало', callback_data=export_callback(f'exp_pick_set_start:{start_dt.year}:{start_dt.month}:{start_dt.day}:{return_day_key}')))
    return kb
try:
    _v177_legacy_0171_export_end_calendar_keyboard.__name__ = '_export_end_calendar_keyboard'
except Exception:
    pass

def _excel_canonical_opening_balance(chat_id: int, currency: str, start_day: str, start_rid: int | None=0, exact: bool=False) -> float:
    cid = int(chat_id)
    cur = 'usd' if str(currency or 'ars').strip().lower() == 'usd' else 'ars'
    start = str(start_day or '')[:10]
    try:
        start_rid = int(start_rid or 0)
    except Exception:
        start_rid = 0
    total = 0.0
    rows = list(_v151_all_records(cid, cur) or [])
    try:
        rows = sorted(rows, key=record_sort_key)
    except Exception:
        pass
    target_sort_key = None
    if bool(exact) and start_rid and (cur == 'ars'):
        try:
            target = next((r for r in rows if _v151_day_key(r) == start and int(r.get('id') or 0) == start_rid), None)
            if target is not None:
                target_sort_key = record_sort_key(target)
        except Exception:
            target_sort_key = None
    for rec in rows:
        day = _v151_day_key(rec)
        if not day:
            continue
        amount = _v151_float(rec.get('_v151_amount'))
        if day < start:
            total += amount
            continue
        if day > start:
            break
        if not bool(exact) or not start_rid or cur != 'ars':
            break
        if target_sort_key is not None:
            try:
                if record_sort_key(rec) < target_sort_key:
                    total += amount
                    continue
            except Exception:
                pass
            break
        try:
            if int(rec.get('id') or 0) < start_rid:
                total += amount
                continue
        except Exception:
            pass
        break
    return float(total)

def _excel_canonical_records_for_range(chat_id: int, currency: str, start_day: str, end_day: str) -> list[dict]:
    cid = int(chat_id)
    cur = 'usd' if str(currency or 'ars').strip().lower() == 'usd' else 'ars'
    start = str(start_day or '')[:10]
    end = str(end_day or start)[:10]
    if end < start:
        start, end = (end, start)
    out = []
    for rec in _v151_all_records(cid, cur) or []:
        day = _v151_day_key(rec)
        if day and start <= day <= end:
            out.append(rec)
    try:
        return sorted(out, key=record_sort_key)
    except Exception:
        return out

def _excel_chat_id_for_store(store: dict | None) -> int | None:
    if not isinstance(store, dict):
        return None
    try:
        ctx = _v151_context()
        cid = int(ctx.get('target_chat_id') or 0)
        if cid:
            return cid
    except Exception:
        pass
    try:
        for raw_cid, row in (data.get('chats', {}) or {}).items():
            if row is store:
                return int(raw_cid)
    except Exception:
        pass
    try:
        owner_scope = int((store.get('settings', {}) or {}).get('owner_scope_id') or 0)
        if owner_scope:
            return owner_scope
    except Exception:
        pass
    return None

def _v177_legacy_0272_v151_usd_records(chat_id: int) -> list[dict]:
    store = get_chat_store(int(chat_id))
    active = _v151_sync_currency_snapshots(store)
    ars_source = store.get('records', []) if active == 'ars' else store.get('ars_records', [])
    usd_source = store.get('records', []) if active == 'usd' else store.get('usd_records', [])
    ars_by_msg = {}
    ars_by_op = {}
    for rec in ars_source or []:
        if not isinstance(rec, dict):
            continue
        msg = int(rec.get('source_msg_id') or 0)
        op = str(rec.get('operation_key') or '').strip()
        if msg:
            ars_by_msg[msg] = rec
        if op:
            ars_by_op[op] = rec

    def _same_business_row(left: dict, right: dict) -> bool:
        try:
            return abs(_v151_float(left.get('amount')) - _v151_float(right.get('amount'))) <= 1e-09 and str(left.get('note') or '').strip() == str(right.get('note') or '').strip() and (_v151_day_key(left) == _v151_day_key(right))
        except Exception:
            return False
    rows = []
    represented_sources = set()
    seen_independent = set()
    for rec in usd_source or []:
        if not isinstance(rec, dict):
            continue
        operation_key = str(rec.get('operation_key') or '').strip()
        source_msg_id = int(rec.get('source_msg_id') or 0)
        peer = ars_by_msg.get(source_msg_id) if source_msg_id else None
        if peer is None and operation_key:
            peer = ars_by_op.get(operation_key)
        explicit_usd = str(rec.get('currency') or '').strip().upper() == 'USD'
        if peer is not None and _same_business_row(rec, peer) and (not explicit_usd):
            continue
        key = ('op', operation_key) if operation_key else ('msg', source_msg_id) if source_msg_id else (int(rec.get('id') or 0), str(rec.get('timestamp') or ''), _v151_day_key(rec), _v151_float(rec.get('amount')))
        if key in seen_independent:
            continue
        seen_independent.add(key)
        item = dict(rec)
        item['_v151_amount'] = _v151_float(rec.get('amount'))
        item['_v151_note'] = str(rec.get('note') or rec.get('usd_note') or '')
        item['_v151_currency'] = 'usd'
        rows.append(item)
        if source_msg_id:
            represented_sources.add(('msg', source_msg_id))
        if operation_key:
            represented_sources.add(('op', operation_key))
    for rec in ars_source or []:
        if not isinstance(rec, dict):
            continue
        usd_amount = _v151_float(rec.get('usd_amount'))
        if abs(usd_amount) <= 1e-12:
            continue
        operation_key = str(rec.get('operation_key') or '').strip()
        source_msg_id = int(rec.get('source_msg_id') or 0)
        source_keys = set()
        if source_msg_id:
            source_keys.add(('msg', source_msg_id))
        if operation_key:
            source_keys.add(('op', operation_key))
        if source_keys and any((k in represented_sources for k in source_keys)):
            continue
        item = dict(rec)
        item['_v151_amount'] = usd_amount
        item['_v151_note'] = str(rec.get('usd_note') or rec.get('note') or '')
        item['_v151_currency'] = 'usd'
        item['_v151_embedded'] = True
        rows.append(item)
        represented_sources.update(source_keys)
    try:
        return sorted(rows, key=record_sort_key)
    except Exception:
        return rows
try:
    _v177_legacy_0272_v151_usd_records.__name__ = '_v151_usd_records'
except Exception:
    pass
_V193_A1_REF_RE = _v151_re.compile('(?<![A-Z0-9_])(\\$?[A-Z]{1,3}\\$?)(\\d+)')

def _v193_shift_formula_a1(formula: str, row_offset: int) -> str:
    """Shift only A1-style row references when a prebuilt table is appended lower in a sheet."""
    text = str(formula or '')
    offset = int(row_offset or 0)
    if not text or not offset:
        return text

    def _repl(match):
        return f'{match.group(1)}{int(match.group(2)) + offset}'
    return _V193_A1_REF_RE.sub(_repl, text)

def _v193_shift_formula_rows(rows: list[list], row_offset: int) -> list[list]:
    """Deep-copy row payloads and move formula references with the appended section."""
    out = _v154_copy.deepcopy(list(rows or []))
    offset = int(row_offset or 0)
    if not offset:
        return out
    for row in out:
        if not isinstance(row, list):
            continue
        for idx, cell in enumerate(row):
            if isinstance(cell, dict) and cell.get('formula'):
                item = dict(cell)
                item['formula'] = _v193_shift_formula_a1(item.get('formula'), offset)
                row[idx] = item
    return out

def _v193_validate_currency_formula_domains(rows: list[list]) -> bool:
    """USD formulas must never point back into the ARS section after sections are joined."""
    usd_row = None
    for idx, row in enumerate(rows or [], start=1):
        try:
            if str((row or [''])[0]).strip().upper() == 'USD':
                usd_row = idx
                break
        except Exception:
            pass
    if not usd_row:
        return True
    bad = []
    for rr, row in enumerate(rows or [], start=1):
        if rr < usd_row or not isinstance(row, list):
            continue
        for cc, cell in enumerate(row, start=1):
            if not isinstance(cell, dict) or not cell.get('formula'):
                continue
            refs = [int(m.group(2)) for m in _V193_A1_REF_RE.finditer(str(cell.get('formula') or ''))]
            if refs and min(refs) < usd_row:
                bad.append((rr, cc, str(cell.get('formula'))))
    if bad:
        raise RuntimeError(f'Excel USD formula escaped into ARS section: {bad[:8]}')
    return True

def _v154_join_ars_usd(ars_rows: list[list], usd_rows: list[list], chat_id: int) -> list[list]:
    if not excel_usd_table_enabled(int(chat_id)):
        return list(ars_rows or [])
    prefix = list(ars_rows or []) + [[], []]
    shifted_usd = _v193_shift_formula_rows(list(usd_rows or []), len(prefix))
    joined = prefix + shifted_usd
    _v193_validate_currency_formula_domains(joined)
    return joined

def _canon_build_exact_category_stats_xlsx_rows__001(target_chat_id: int, start_key: str, start_rid: int, end_key: str, end_rid: int) -> list[list]:
    """ARS keeps category layout; USD is always a clean four-column operation table."""
    previous = getattr(_V151_EXPORT_LOCAL, 'value', None)
    if not previous:
        _V151_EXPORT_LOCAL.value = {'kind': 'exact', 'target_chat_id': int(target_chat_id), 'start_key': str(start_key)[:10], 'start_rid': int(start_rid or 0), 'end_key': str(end_key)[:10], 'end_rid': int(end_rid or 0), 'file_type': 'xlsxstat'}
    try:
        ars_rows = _v151_category_table(int(target_chat_id), 'ars')
        usd_rows, _ = _v151_simple_table(int(target_chat_id), 'usd', compact=False)
        return _v154_join_ars_usd(ars_rows, usd_rows, int(target_chat_id))
    finally:
        if not previous:
            _V151_EXPORT_LOCAL.value = None

def _canon_xlsx_simple_rows_with_balances__001(rows: list[list], opening_balance: float, target_chat_id: int | None=None) -> list[list]:
    if target_chat_id is None:
        return globals().get('_V150_BASE_SIMPLE_ROWS', lambda r, o, *_: r)(rows, opening_balance, target_chat_id)
    ars_rows, _ = _v151_simple_table(int(target_chat_id), 'ars', compact=False)
    usd_rows, _ = _v151_simple_table(int(target_chat_id), 'usd', compact=False)
    return _v154_join_ars_usd(ars_rows, usd_rows, int(target_chat_id))

def _v177_legacy_0096_compact_simple_excel_rows_and_annotations(raw_rows: list[tuple], opening_balance: float, target_chat_id: int | None=None) -> tuple[list[list], dict[tuple[int, int], str]]:
    if target_chat_id is None:
        base = globals().get('_V150_BASE_COMPACT_ROWS')
        return base(raw_rows, opening_balance, target_chat_id) if callable(base) else ([], {})
    ars_rows, ars_notes = _v151_simple_table(int(target_chat_id), 'ars', compact=True)
    if not excel_usd_table_enabled(int(target_chat_id)):
        return (ars_rows, dict(ars_notes))
    usd_rows, _ = _v151_simple_table(int(target_chat_id), 'usd', compact=False)
    prefix = list(ars_rows or []) + [[], []]
    shifted_usd = _v193_shift_formula_rows(usd_rows, len(prefix))
    joined = prefix + shifted_usd
    _v193_validate_currency_formula_domains(joined)
    return (joined, dict(ars_notes))
try:
    _v177_legacy_0096_compact_simple_excel_rows_and_annotations.__name__ = '_compact_simple_excel_rows_and_annotations'
except Exception:
    pass

def _v177_legacy_0178_category_rows_without_description(rows: list[list]) -> tuple[list[list], dict[tuple[int, int], str]]:
    """Compact only the ARS category section; never remove Description from the USD section."""
    usd_index = None
    for idx, row in enumerate(rows or []):
        try:
            if str((row or [''])[0]).strip().upper() == 'USD':
                usd_index = idx
                break
        except Exception:
            pass
    if usd_index is None or not callable(_V154_BASE_CATEGORY_COMPACT):
        return _V154_BASE_CATEGORY_COMPACT(rows) if callable(_V154_BASE_CATEGORY_COMPACT) else (rows, {})
    ars_part = list(rows[:usd_index])
    usd_part = list(rows[usd_index:])
    compact_ars, annotations = _V154_BASE_CATEGORY_COMPACT(ars_part)
    return (compact_ars + usd_part, annotations)
try:
    _v177_legacy_0178_category_rows_without_description.__name__ = '_category_rows_without_description'
except Exception:
    pass

def _v154_find_usd_section(rows: list[list]) -> int | None:
    for idx, row in enumerate(rows or []):
        try:
            if str((row or [''])[0]).strip().upper() == 'USD':
                return idx
        except Exception:
            pass
    return None

def _v154_merge_styles(prefix_rows, suffix_rows, prefix_result, suffix_result, keep_suffix_comments=True):
    p_styles, p_comments, p_freeze, p_widths = prefix_result
    s_styles, s_comments, _s_freeze, s_widths = suffix_result
    offset = len(prefix_rows)
    comments = dict(p_comments or {})
    if keep_suffix_comments:
        for (r, c), text in (s_comments or {}).items():
            comments[int(r) + offset, int(c)] = text
    max_len = max(len(p_widths or []), len(s_widths or []))
    widths = []
    for i in range(max_len):
        widths.append(max((p_widths or [0])[i] if i < len(p_widths or []) else 0, (s_widths or [0])[i] if i < len(s_widths or []) else 0))
    return (list(p_styles or []) + list(s_styles or []), comments, p_freeze, widths)

def _canon_modern_compact_excel_styles_comments__001(rows: list[list], annotations: dict[tuple[int, int], str]):
    """Compact ARS may stay 3-column, while appended USD keeps its four-column simple layout."""
    idx = _v154_find_usd_section(rows)
    if idx is None or not callable(_V154_BASE_MODERN_COMPACT) or (not callable(_V154_BASE_MODERN_SIMPLE)):
        return _V154_BASE_MODERN_COMPACT(rows, annotations)
    prefix, suffix = (list(rows[:idx]), list(rows[idx:]))
    p = _V154_BASE_MODERN_COMPACT(prefix, annotations)
    s = _V154_BASE_MODERN_SIMPLE(suffix)
    return _v154_merge_styles(prefix, suffix, p, s, keep_suffix_comments=False)

def _v177_legacy_0102_modern_category_excel_styles_comments(rows: list[list]):
    idx = _v154_find_usd_section(rows)
    if idx is None or not callable(_V154_BASE_MODERN_CATEGORY) or (not callable(_V154_BASE_MODERN_SIMPLE)):
        return _V154_BASE_MODERN_CATEGORY(rows)
    prefix, suffix = (list(rows[:idx]), list(rows[idx:]))
    return _v154_merge_styles(prefix, suffix, _V154_BASE_MODERN_CATEGORY(prefix), _V154_BASE_MODERN_SIMPLE(suffix), keep_suffix_comments=True)
try:
    _v177_legacy_0102_modern_category_excel_styles_comments.__name__ = '_modern_category_excel_styles_comments'
except Exception:
    pass

def _canon_modern_category_no_description_styles_comments__001(rows: list[list], annotations: dict[tuple[int, int], str]):
    idx = _v154_find_usd_section(rows)
    if idx is None or not callable(_V154_BASE_MODERN_CATEGORY_COMPACT) or (not callable(_V154_BASE_MODERN_SIMPLE)):
        return _V154_BASE_MODERN_CATEGORY_COMPACT(rows, annotations)
    prefix, suffix = (list(rows[:idx]), list(rows[idx:]))
    p = _V154_BASE_MODERN_CATEGORY_COMPACT(prefix, annotations)
    s = _V154_BASE_MODERN_SIMPLE(suffix)
    return _v154_merge_styles(prefix, suffix, p, s, keep_suffix_comments=False)

def _v177_legacy_0279_v153_validate_restore_gz(gz_path: str) -> tuple[dict, str]:
    folder = _v153_tempfile.mkdtemp(prefix='v154_restore_validate_')
    raw = _v154_os.path.join(folder, 'restore.sqlite3')
    try:
        with _v154_gzip.open(gz_path, 'rb') as fin, open(raw, 'wb') as fout:
            _v154_shutil.copyfileobj(fin, fout, 1024 * 1024)
        conn = _v154_sqlite3.connect(raw)
        try:
            integrity = str(conn.execute('PRAGMA integrity_check').fetchone()[0])
            if integrity.lower() != 'ok':
                raise RuntimeError(f'SQLite integrity_check: {integrity}')
            row = conn.execute("SELECT v FROM meta WHERE kind='v153_export' AND k='manifest'").fetchone()
            if not row:
                raise RuntimeError('manifest v153 not found')
            manifest = _v154_json.loads(row[0])
        finally:
            conn.close()
        if str(manifest.get('kind')) != 'telegram_bot_full_state_v153':
            raise RuntimeError('unknown export kind')
        if int(manifest.get('schema_version') or 0) != V153_EXPORT_SCHEMA:
            raise RuntimeError('unsupported export schema')
        export_version = str(manifest.get('bot_version') or '')
        if not (export_version.startswith('bot_v153_') or export_version.startswith('bot_v154_')):
            raise RuntimeError(f"unsupported bot version: {export_version or 'missing'}")
        checksum = _v153_db_logical_checksum(raw)
        if checksum != str(manifest.get('checksum') or ''):
            raise RuntimeError('checksum mismatch')
        return (manifest, raw)
    except Exception:
        _v154_shutil.rmtree(folder, ignore_errors=True)
        raise
try:
    _v177_legacy_0279_v153_validate_restore_gz.__name__ = '_v153_validate_restore_gz'
except Exception:
    pass
try:
    WINDOW_MARKER_CONSTANTS['exp_excel_dollar_toggle:*'] = 'Ф179'
except Exception:
    pass
try:
    _v177_legacy_0007_bot_journal('v154_excel_usd_isolation_installed', int(OWNER_ID or 0), 'strict_usd_ledger=1; f111_f114_marks=1; f179_usd_toggle=1')
except Exception:
    pass

def _v243_mark_runtime_restore_healthy(reason: str, *, remote_confirmed: bool=False, generation: str='') -> dict:
    detail = str(reason or 'manual recovery accepted')
    if generation:
        detail += f'; generation={generation}'
    detail += '; MEGA canonical confirmed' if remote_confirmed else '; MEGA canonical pending/retry allowed'
    try:
        lock = globals().get('_RUNTIME_LOCK')
        state = globals().get('_RUNTIME_STATE')
        if isinstance(state, dict):
            if lock is not None:
                with lock:
                    state['restore_attempted'] = True
                    state['restore_ok'] = True
                    state['restore_detail'] = detail[:500]
                    state['last_error'] = ''
            else:
                state['restore_attempted'] = True
                state['restore_ok'] = True
                state['restore_detail'] = detail[:500]
                state['last_error'] = ''
    except Exception:
        pass
    try:
        _clear_restore_guard()
    except Exception:
        pass
    try:
        clearq = globals().get('constitution_clear_quarantine')
        if callable(clearq):
            clearq('v243 confirmed local recovery')
    except Exception:
        pass
    try:
        runtime_event('runtime_restore_healed_v243', detail[:700], 'INFO')
    except Exception:
        pass
    try:
        resume = globals().get('_v244_google_resume_after_recovery')
        sched = globals().get('DELAYED_SCHEDULER')
        if callable(resume):
            if sched is not None:
                sched.schedule('google-resume-after-recovery-v244', 1.0, resume, str(reason or 'recovery'))
            else:
                resume(str(reason or 'recovery'))
    except Exception:
        pass
    return {'ok': True, 'detail': detail, 'remote_confirmed': bool(remote_confirmed), 'generation': str(generation or '')}

def _canon_v240_restore_reanchor_guaranteed__002(reason: str) -> dict:
    """Publish an accepted manual restore through HEAVY -> MEGA, never MEGA from FAST."""
    previous = bool(globals().get('_V240_RECOVERY_AUTHORITY_ACTIVE', False))
    globals()['_V240_RECOVERY_AUTHORITY_ACTIVE'] = True
    try:
        push = globals().get('_split_push_snapshot_now_v263')
        if not callable(push):
            raise RuntimeError('HEAVY snapshot handoff is unavailable')
        if not bool(push('manual_restore:' + str(reason or 'restore'), sync_mega=True)):
            raise RuntimeError('HEAVY did not confirm MEGA publication')
        try:
            cp = config_guard_accept_current_v234('restore_heavy_mega:' + str(reason)) or {}
        except Exception:
            cp = {}
        total = int((constitution_semantic_manifest_from_live() or {}).get('total_records') or 0)
        active = {'backend': 'heavy-mega', 'generation': 'HEAVY-MEGA-CONFIRMED', 'total_records': total}
        SQLITE.set_meta('restore_control_v240', 'remote_reanchor_pending', {})
        try: runtime_event('restore_remote_reanchor_confirmed_v242', 'backend=HEAVY->MEGA', 'INFO')
        except Exception: pass
        try: _v243_mark_runtime_restore_healthy(str(reason), remote_confirmed=True, generation='HEAVY-MEGA-CONFIRMED')
        except Exception: pass
        return {'active': active, 'lineage': '', 'config_checkpoint': cp, 'remote_confirmed_v240': True, 'remote_confirmed_v242': True}
    except Exception as exc:
        err = str(exc)[:700]
        try:
            cp = config_guard_accept_current_v234('restore_local_pending_heavy:' + str(reason))
        except Exception:
            cp = {}
        pending = {'at': now_local().isoformat(timespec='microseconds'), 'reason': str(reason), 'error': err,
                   'config_generation': int((cp or {}).get('generation') or 0)}
        try: SQLITE.set_meta('restore_control_v240', 'remote_reanchor_pending', pending)
        except Exception: pass
        try: _v240_schedule_pending_restore_reanchor_retry(20.0)
        except Exception: pass
        try: runtime_event('restore_remote_reanchor_pending_v242', err, 'WARN')
        except Exception: pass
        try: _v243_mark_runtime_restore_healthy(str(reason), remote_confirmed=False, generation='LOCAL-PENDING')
        except Exception: pass
        return {'active': {'backend': 'local', 'generation': 'LOCAL-PENDING', 'total_records': int((constitution_semantic_manifest_from_live() or {}).get('total_records') or 0)},
                'lineage': '', 'config_checkpoint': cp, 'remote_confirmed_v240': False, 'remote_confirmed_v242': False, 'warning': err}
    finally:
        globals()['_V240_RECOVERY_AUTHORITY_ACTIVE'] = bool(previous or globals().get('_V241_RESTORE_ACTIVE', False))

_V242_MEGA_DB_CATALOG_CACHE = {}

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

def _v242_mega_catalog_entry(token: str) -> dict:
    token = str(token or '')
    row = _V242_MEGA_DB_CATALOG_CACHE.get(token)
    if row:
        return dict(row)
    _v242_mega_database_catalog(24)
    return dict(_V242_MEGA_DB_CATALOG_CACHE.get(token) or {})

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
            save_data(data, full=True)
            redis_row = {'required': False, 'ok': False, 'detail': 'helper unavailable'}
            try:
                seal = globals().get('r64_publish_restore_snapshot_v271')
                if callable(seal):
                    redis_row = dict(seal('owner_selected_mega_database_r65') or redis_row)
            except Exception as _r65_redis_exc:
                redis_row = {'required': True, 'ok': False, 'detail': f'{type(_r65_redis_exc).__name__}: {str(_r65_redis_exc)[:220]}'}
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
                'redis_required': bool(redis_row.get('required')),
                'redis_ok': bool(redis_row.get('ok')),
                'redis_detail': str(redis_row.get('detail') or '')[:300],
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
        globals()['_V240_RECOVERY_AUTHORITY_ACTIVE'] = bool(previous)

# v262
