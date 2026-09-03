# v262
def send_csv_week(chat_id: int, day_key: str):
    if is_finance_output_suppressed(chat_id):
        return
    return send_export_for_chat_to(int(chat_id), int(chat_id), 'week', day_key, 'csv')

def send_csv_month(chat_id: int, day_key: str):
    if is_finance_output_suppressed(chat_id):
        return
    return send_export_for_chat_to(int(chat_id), int(chat_id), 'month', day_key, 'csv')

def _v177_legacy_0226_send_csv_wedthu(chat_id: int, day_key: str):
    if is_finance_output_suppressed(chat_id):
        return
    return send_export_for_chat_to(int(chat_id), int(chat_id), 'wedthu', day_key, 'csv')
try:
    _v177_legacy_0226_send_csv_wedthu.__name__ = 'send_csv_wedthu'
except Exception:
    pass

def finance_operation_key(chat_id: int, source_msg_id, ledger: str='main') -> str:
    """Stable idempotency key for a finance effect created from a Telegram message."""
    try:
        mid = int(source_msg_id)
    except Exception:
        return ''
    return f"finance:{int(chat_id)}:{str(ledger or 'main')}:{mid}"

def find_record_by_operation_key(chat_id: int, operation_key: str):
    if not operation_key:
        return None
    try:
        store = get_chat_store(int(chat_id))
        for r in store.get('records', []) or []:
            if isinstance(r, dict) and str(r.get('operation_key') or '') == str(operation_key):
                return r
    except Exception:
        pass
    return None

def _finance_add_record_base(chat_id: int, amount: float, note: str, owner: int, source_msg=None, day_key=None, usd_amount=None, usd_note: str='', usd_only: bool=False, source_finance_text: str=''):
    bot_journal('record_add_start', chat_id, f'amount={amount} note={note}')
    if globals().get('constitution_finance_write_blocked_v232') and constitution_finance_write_blocked_v232():
        raise RuntimeError('DATA CONSTITUTION: финансовые изменения заблокированы до восстановления целостности')
    op_id = operation_begin('finance_add', chat_id, target=str(day_key or 'auto'), payload={'amount': amount, 'note': note}, critical=True) if 'operation_begin' in globals() else ''
    if op_id and 'operation_step' in globals():
        operation_step(op_id, 'saved_locally', 'intent recorded', persist=False)
    with locked_chat(chat_id):
        store = get_chat_store(chat_id)
        rid = store.get('next_id', 1)
        if not day_key:
            day_key = day_key_from_message(source_msg)
        source_msg_id = getattr(source_msg, 'message_id', None) if source_msg else None
        source_order_msg_id = getattr(source_msg, 'source_order_msg_id', None) or getattr(source_msg, 'forward_source_msg_id', None) or source_msg_id
        _op_override = str(getattr(source_msg, 'finance_operation_key_override', '') or '') if source_msg is not None else ''
        operation_key = _op_override or finance_operation_key(chat_id, source_msg_id, 'main')
        if operation_key:
            existing_op = find_record_by_operation_key(int(chat_id), operation_key) if 'find_record_by_operation_key' in globals() else None
            if isinstance(existing_op, dict):
                bot_journal('finance_duplicate_operation_blocked_v260', chat_id, f'operation_key={operation_key}')
                if op_id and 'operation_complete' in globals():
                    operation_complete(op_id, 'duplicate blocked by stable operation key; existing record reused')
                return existing_op
        if source_msg_id is not None:
            existing_any = find_record_by_message_id(int(chat_id), int(source_msg_id)) if 'find_record_by_message_id' in globals() else None
            if isinstance(existing_any, dict):
                if '_remember_finance_source_identity_v257' in globals():
                    _remember_finance_source_identity_v257(int(chat_id), existing_any, int(source_msg_id), 'records')
                bot_journal('finance_duplicate_blocked_v257', chat_id, f'source_msg_id={source_msg_id} operation_key={operation_key}; central=1')
                if op_id and 'operation_complete' in globals():
                    operation_complete(op_id, 'duplicate blocked by stable source identity; existing record reused')
                return existing_any
            for existing in store.get('records', []) or []:
                if not isinstance(existing, dict):
                    continue
                if operation_key and str(existing.get('operation_key') or '') == operation_key or int(existing.get('source_msg_id') or 0) == int(source_msg_id):
                    if operation_key and (not existing.get('operation_key')):
                        existing['operation_key'] = operation_key
                    bot_journal('finance_duplicate_blocked', chat_id, f'source_msg_id={source_msg_id} operation_key={operation_key}')
                    if op_id and 'operation_complete' in globals():
                        operation_complete(op_id, 'duplicate blocked; existing record reused')
                    return existing
        rec = {'id': rid, 'short_id': '', 'timestamp': message_timestamp_iso(source_msg), 'amount': amount, 'note': note, 'source_msg_id': source_msg_id, 'source_order_msg_id': source_order_msg_id, 'owner': owner, 'msg_id': source_msg_id, 'origin_msg_id': source_msg_id, 'day_key': day_key, 'operation_key': operation_key}
        if source_msg is not None:
            for _attr, _field in (('forward_source_chat_id','forward_source_chat_id'), ('forward_source_msg_id','forward_source_msg_id'), ('forward_dst_chat_id','forward_dst_chat_id'), ('forward_dst_msg_id','forward_dst_msg_id')):
                try:
                    _v = int(getattr(source_msg, _attr, 0) or 0)
                    if _v: rec[_field] = _v
                except Exception:
                    pass
            if rec.get('forward_source_chat_id') and rec.get('forward_source_msg_id'):
                rec['forwarded_by_bot'] = True
        if usd_amount is not None:
            rec['usd_amount'] = float(usd_amount or 0)
            rec['usd_note'] = str(usd_note or note or '')
            rec['usd_only'] = bool(usd_only)
        if source_finance_text:
            rec['source_finance_text'] = str(source_finance_text)
        # R15 hot path: do not run the historical full-ledger normalizer/dedupe
        # synchronously for every new message.  Exact-once guards above already protect
        # this Telegram effect.  Update the two authoritative in-memory indexes
        # incrementally, commit this chat, and let the debounced finance finalize do the
        # full normalize/reconcile in FINANCE_TASK_POOL.
        records = store.setdefault('records', [])
        _needs_sort = bool(records and record_sort_key(rec) < record_sort_key(records[-1]))
        records.append(rec)
        if _needs_sort:
            try: records.sort(key=record_sort_key)
            except Exception: pass
        daily = store.setdefault('daily_records', {})
        day_rows = daily.setdefault(str(day_key), [])
        _day_needs_sort = bool(day_rows and record_sort_key(rec) < record_sort_key(day_rows[-1]))
        day_rows.append(rec)
        if _day_needs_sort:
            try: day_rows.sort(key=record_sort_key)
            except Exception: pass
        try:
            store['next_id'] = max(int(store.get('next_id', 1) or 1), int(rid) + 1)
        except Exception:
            store['next_id'] = int(rid) + 1
        try:
            store['balance'] = float(store.get('balance', 0) or 0) + float(amount or 0)
        except Exception:
            store['balance'] = sum((float(r.get('amount', 0) or 0) for r in records if isinstance(r, dict)))
        store['_finance_hotpath_pending_normalize_r16'] = True
        store['_finance_fast_generation_r16'] = int(store.get('_finance_fast_generation_r16', 0) or 0) + 1
        store.pop('_finance_day_balance_cache_r16', None)
        if usd_amount is not None and '_usd_balance_cache_r16' in store:
            try: store['_usd_balance_cache_r16'] = float(store.get('_usd_balance_cache_r16', 0) or 0) + float(usd_amount or 0)
            except Exception: store.pop('_usd_balance_cache_r16', None)
        # R7: the durable record itself is committed immediately below.  Month short-id
        # renumbering and global aggregate rebuild are derived data and are rebuilt once
        # by the debounced finance finalize path before any finance window repaint.
        try:
            if 'ensure_finance_record_uid' in globals():
                ensure_finance_record_uid(int(chat_id), rec)
            if 'persist_finance_chat_local_fast' in globals():
                persist_finance_chat_local_fast(int(chat_id))
        except Exception as _v168_local_exc:
            try:
                log_error(f'v168 record local commit {chat_id}: {_v168_local_exc}')
            except Exception:
                pass
        try:
            finance_cache_invalidate(chat_id, 'finance_add')
            finance_integrity_append(chat_id, 'add', rec)
        except Exception as _integrity_exc:
            log_error(f'finance add integrity: {_integrity_exc}')
        try:
            if source_msg_id is not None and '_remember_finance_source_identity_v257' in globals():
                _remember_finance_source_identity_v257(int(chat_id), rec, int(source_msg_id), 'records')
        except Exception as _v257_idx_exc:
            try: log_error(f'v257 finance source identity index: {_v257_idx_exc}')
            except Exception: pass
        if op_id and 'operation_complete' in globals():
            operation_complete(op_id, f"record={rec.get('id')}")
        return rec

def delete_record_in_chat(chat_id: int, rid: int):
    if globals().get('constitution_finance_write_blocked_v232') and constitution_finance_write_blocked_v232():
        raise RuntimeError('DATA CONSTITUTION: удаление заблокировано до восстановления целостности')
    op_id = operation_begin('finance_delete', chat_id, target=str(rid), payload={'rid': rid}, critical=True) if 'operation_begin' in globals() else ''
    with locked_chat(chat_id):
        store = get_chat_store(chat_id)
        deleted_record = next((copy.deepcopy(x) for x in store.get('records', []) if int(x.get('id', -1)) == int(rid)), None)
        store['records'] = [x for x in store['records'] if int(x.get('id', -1)) != int(rid)]
        for day, arr in list(store.get('daily_records', {}).items()):
            arr2 = [x for x in arr if int(x.get('id', -1)) != int(rid)]
            if arr2:
                store['daily_records'][day] = arr2
            else:
                del store['daily_records'][day]
        # R16: record IDs are stable. Do not renumber the whole history on deletion.
        # Adjust only the affected aggregate and leave full normalize/self-check to background.
        try: store['balance'] = float(store.get('balance', 0) or 0) - float((deleted_record or {}).get('amount', 0) or 0)
        except Exception: pass
        store['_finance_hotpath_pending_normalize_r16'] = True
        store['_finance_fast_generation_r16'] = int(store.get('_finance_fast_generation_r16', 0) or 0) + 1
        store.pop('_finance_day_balance_cache_r16', None)
        if isinstance(deleted_record, dict) and '_usd_balance_cache_r16' in store:
            try: store['_usd_balance_cache_r16'] = float(store.get('_usd_balance_cache_r16', 0) or 0) - float(deleted_record.get('usd_amount', 0) or 0)
            except Exception: store.pop('_usd_balance_cache_r16', None)
        try:
            if 'persist_finance_chat_local_fast' in globals():
                persist_finance_chat_local_fast(int(chat_id))
        except Exception as _r7_delete_persist_exc:
            try: log_error(f'R7 delete local persist {chat_id}: {_r7_delete_persist_exc}')
            except Exception: pass
        try:
            finance_cache_invalidate(chat_id, 'finance_delete')
            finance_integrity_append(chat_id, 'delete', deleted_record or {'id': rid})
        except Exception as _integrity_exc:
            log_error(f'finance delete integrity: {_integrity_exc}')
        if op_id and 'operation_complete' in globals():
            operation_complete(op_id, f'record={rid}')

def renumber_chat_records(chat_id: int):
    """Перенумеровывает записи по реальной хронологии поступления сообщений."""
    store = get_chat_store(chat_id)
    normalize_chat_records(chat_id)
    all_recs = list(store.get('records', []) or [])
    all_recs.sort(key=record_sort_key)
    for new_id, r in enumerate(all_recs, 1):
        r['id'] = new_id
    store['records'] = all_recs
    rebuilt_daily = {}
    for r in all_recs:
        rebuilt_daily.setdefault(_record_day_key(r), []).append(r)
    store['daily_records'] = rebuilt_daily
    store['next_id'] = len(all_recs) + 1
    try:
        helper = globals().get('_r7_rebuild_month_short_ids_after_normalize')
        if callable(helper):
            helper(int(chat_id), store)
        else:
            rebuild_month_short_ids(chat_id)
    except Exception:
        rebuild_month_short_ids(chat_id)

def get_or_create_active_windows(chat_id: int) -> dict:
    return data.setdefault('active_messages', {}).setdefault(str(chat_id), {})

def get_primary_main_window(chat_id: int) -> tuple[int | None, str]:
    """Return the single authoritative main window for this chat."""
    chat_id = int(chat_id)
    store = get_chat_store(chat_id)
    mid = 0
    try:
        mid = int(store.get('primary_main_window_id') or 0)
    except Exception:
        mid = 0
    day = str(store.get('primary_main_window_day') or store.get('current_view_day') or today_key())[:10]
    if mid:
        return (mid, day)
    aw = get_or_create_active_windows(chat_id)
    if aw:
        preferred = aw.get(day)
        if preferred:
            try:
                mid = int(preferred)
            except Exception:
                mid = 0
        if not mid:
            try:
                last_day, last_mid = list(aw.items())[-1]
                day = str(last_day)[:10]
                mid = int(last_mid)
            except Exception:
                mid = 0
        if mid:
            store['primary_main_window_id'] = mid
            store['primary_main_window_day'] = day
            store['current_view_day'] = day
            aw.clear()
            aw[day] = mid
    return (mid or None, day)

def canonical_main_day(chat_id: int) -> str:
    _mid, day = get_primary_main_window(int(chat_id))
    return str(day or today_key())[:10]

def is_primary_main_message(chat_id: int, message_id: int) -> bool:
    mid, _day = get_primary_main_window(int(chat_id))
    try:
        return bool(mid and int(mid) == int(message_id))
    except Exception:
        return False

def _v189_delete_stale_main_message(chat_id: int, message_id: int):
    try:
        fn = globals().get('v177_delete_message_async')
        if callable(fn):
            fn(int(chat_id), int(message_id), 'v189_stale_main')
            return
    except Exception:
        pass
    try:
        pool = globals().get('GENERAL_TASK_POOL')
        if pool is not None:
            pool.submit(f'v189-stale-main:{int(chat_id)}:{int(message_id)}', lambda: _tg_call_retry(bot.delete_message, int(chat_id), int(message_id), attempts=1, purpose='v189_stale_main_delete'))
            return
    except Exception:
        pass

def _v186_persist_active_window_state(chat_id: int):
    """Persist UI-only window state outside callback latency path."""
    try:
        _finance_window_state(int(chat_id))['auto_reopen_on_boot'] = True
        _sync_finance_window_state_from_runtime(int(chat_id), schedule_delta=False)
        save_data(data, chat_ids=[int(chat_id)])
        try:
            schedule_config_backup_for_chats(int(chat_id), delay=3.0)
        except Exception:
            pass
    except Exception as exc:
        try:
            log_error(f'v186 active window persist {chat_id}: {exc}')
        except Exception:
            pass

def set_active_window_id(chat_id: int, day_key: str, message_id: int):
    """Promote exactly one Telegram message as the authoritative main window."""
    chat_id = int(chat_id)
    day_key = str(day_key)[:10]
    message_id = int(message_id)
    aw = get_or_create_active_windows(chat_id)
    stale_ids = set()
    for _dk, _mid in list(aw.items()):
        try:
            if int(_mid or 0) and int(_mid) != message_id:
                stale_ids.add(int(_mid))
        except Exception:
            pass
    store = get_chat_store(chat_id)
    try:
        prev_primary = int(store.get('primary_main_window_id') or 0)
        if prev_primary and prev_primary != message_id:
            stale_ids.add(prev_primary)
    except Exception:
        pass
    aw.clear()
    aw[day_key] = message_id
    store['primary_main_window_id'] = message_id
    store['primary_main_window_day'] = day_key
    store['current_view_day'] = day_key
    register_open_window(chat_id, message_id, 'main_day', code='О1', day_key=day_key, params={'parallel_allowed': False, 'primary': True})
    for stale_mid in sorted(stale_ids):
        try:
            unregister_open_window(chat_id, stale_mid)
        except Exception:
            pass
        _v189_delete_stale_main_message(chat_id, stale_mid)
    try:
        DELAYED_SCHEDULER.schedule(f'v186-active-window-persist:{chat_id}', 0.15, _v186_persist_active_window_state, chat_id)
    except Exception:
        pass

def get_active_window_id(chat_id: int, day_key: str):
    mid, active_day = get_primary_main_window(int(chat_id))
    return mid if mid and str(active_day) == str(day_key)[:10] else None

def clear_active_window_id(chat_id: int, day_key: str):
    try:
        chat_id = int(chat_id)
        day_key = str(day_key)[:10]
        aw = get_or_create_active_windows(chat_id)
        old_mid = aw.pop(day_key, None)
        store = get_chat_store(chat_id)
        primary_mid = int(store.get('primary_main_window_id') or 0)
        primary_day = str(store.get('primary_main_window_day') or '')[:10]
        if old_mid:
            unregister_open_window(chat_id, int(old_mid))
        if primary_day == day_key or (old_mid and primary_mid == int(old_mid)):
            store['primary_main_window_id'] = None
            store['primary_main_window_day'] = ''
        try:
            DELAYED_SCHEDULER.schedule(f'v186-active-window-persist:{chat_id}', 0.15, _v186_persist_active_window_state, chat_id)
        except Exception:
            pass
    except Exception as e:
        log_error(f'clear_active_window_id({chat_id},{day_key}): {e}')

def close_previous_main_window_before_back(chat_id: int, day_key: str, current_message_id: int | None=None):
    """При возврате в основное окно удаляет прежнее О1, чтобы не оставалось дубля."""
    try:
        old_mid = get_active_window_id(chat_id, day_key)
        if not old_mid:
            return
        if current_message_id is not None and int(old_mid) == int(current_message_id):
            return
        try:
            bot.delete_message(int(chat_id), int(old_mid))
        except Exception:
            pass
        clear_active_window_id(chat_id, day_key)
    except Exception as e:
        log_error(f'close_previous_main_window_before_back({chat_id},{day_key}): {e}')

def _v177_legacy_0229_update_or_send_day_window(chat_id: int, day_key: str):
    if is_owner_chat(chat_id):
        backup_window_for_owner(chat_id, day_key)
        schedule_balance_panel_refresh(chat_id, 0.5)
        return
    lock = window_locks[chat_id, day_key]
    with lock:
        txt, _ = render_day_window(chat_id, day_key)
        kb = build_main_keyboard(day_key, chat_id)
        old_mid = get_active_window_id(chat_id, day_key)
        if len(txt) > 3900:
            log_error(f'update_or_send_day_window: text too long for {chat_id} {day_key}, len={len(txt)}')
        if old_mid:
            try:
                bot.edit_message_text(txt, chat_id=chat_id, message_id=old_mid, reply_markup=kb, parse_mode='HTML')
                set_active_window_id(chat_id, day_key, old_mid)
                schedule_balance_panel_refresh(chat_id, 0.5)
                return
            except Exception as e:
                err = str(e).lower()
                if 'message is not modified' in err:
                    schedule_balance_panel_refresh(chat_id, 0.5)
                    return
                try:
                    bot.delete_message(chat_id, old_mid)
                except Exception:
                    pass
        sent = bot.send_message(chat_id, txt, reply_markup=kb, parse_mode='HTML')
        set_active_window_id(chat_id, day_key, sent.message_id)
    schedule_balance_panel_refresh(chat_id, 0.5)
try:
    _v177_legacy_0229_update_or_send_day_window.__name__ = 'update_or_send_day_window'
except Exception:
    pass

def is_finance_mode(chat_id):
    store = get_chat_store(chat_id)
    return store.get('finance_mode', False)

def set_finance_mode(chat_id: int, enabled: bool):
    """v108: finance accounting and visible finance windows are separate states.

    A fresh OFF -> ON transition always enables hidden finance and starts with all three
    automatic window modes OFF.  Visible modes are selected independently in F39.
    """
    chat_id = int(chat_id)
    store = get_chat_store(chat_id)
    enabled = bool(enabled)
    was_enabled = bool(store.get('finance_mode', False))
    store['finance_mode'] = enabled
    settings = store.setdefault('settings', {})
    if enabled:
        finance_active_chats.add(chat_id)
        if not was_enabled:
            settings['hidden_finance'] = True
            settings['quick_balance_enabled'] = False
            settings['quick_balance_behavior'] = 'normal'
            settings['quick_balance_user_selected'] = True
            state = store.get('finance_window_state')
            if not isinstance(state, dict):
                state = {}
            state.update({'mode': 'off', 'main_windows': {}, 'balance_panel_id': None, 'balance_panel_mode': 'mini', 'current_view_day': str(store.get('current_view_day') or today_key()), 'auto_reopen_on_boot': False, 'updated_at': now_local().isoformat(timespec='seconds')})
            store['finance_window_state'] = state
            try:
                delete_auto_finance_windows_for_chat(chat_id, persist_now=False)
            except Exception:
                pass
    else:
        finance_active_chats.discard(chat_id)
        settings['hidden_finance'] = False
        settings['quick_balance_enabled'] = False
        settings['quick_balance_behavior'] = 'normal'
        settings['quick_balance_user_selected'] = True
        state = store.get('finance_window_state')
        if not isinstance(state, dict):
            state = {}
        state.update({'mode': 'off', 'main_windows': {}, 'balance_panel_id': None, 'balance_panel_mode': 'mini', 'auto_reopen_on_boot': False, 'updated_at': now_local().isoformat(timespec='seconds')})
        store['finance_window_state'] = state
        try:
            delete_auto_finance_windows_for_chat(chat_id, persist_now=False)
        except Exception:
            pass
    save_data(data, chat_ids=[chat_id])
    try:
        schedule_quick_backup(chat_id, 0.5)
    except Exception:
        pass
    schedule_config_backup_for_chats(chat_id)

def require_finance(chat_id: int) -> bool:
    """
    Проверка: включён ли финансовый режим.
    Если нет — показываем подсказку /поехали.
    """
    if not is_finance_mode(chat_id):
        send_and_auto_delete(chat_id, '⚙️ Финансовый режим выключен.\nАктивируйте командой /ok')
        return False
    return True

def _v177_legacy_0230_refresh_total_message_if_any(chat_id: int):
    """
    Если в чате есть активное сообщение '💰 Общий итог',
    пересчитывает и обновляет его текст.
    """
    store = get_chat_store(chat_id)
    msg_id = store.get('total_msg_id')
    if not msg_id:
        return
    try:
        chat_bal = store.get('balance', 0)
        if not is_owner_chat(chat_id):
            text = wm_common(f'💰 Общий итог по этому чату: {format_chat_amount(chat_id, chat_bal, True)}', 4)
        else:
            lines = []
            info = store.get('info', {})
            title = get_chat_display_name(chat_id)
            lines.append('💰 Общий итог (для владельца)')
            lines.append('')
            lines.append(f'• Этот чат ({title}): {format_chat_amount(chat_id, chat_bal, True)}')
            all_chats = data.get('chats', {})
            allowed_chat_ids = set(tenant_chat_ids(tenant_id_for_chat(chat_id, create=False))) if 'tenant_chat_ids' in globals() else {int(x) for x in all_chats.keys()}
            total_all = 0
            other_lines = []
            for cid, st in all_chats.items():
                try:
                    cid_int = int(cid)
                except Exception:
                    continue
                if cid_int not in allowed_chat_ids:
                    continue
                bal = st.get('balance', 0)
                total_all += bal
                if cid_int == chat_id:
                    continue
                info2 = st.get('info', {})
                title2 = get_chat_display_name(cid_int)
                other_lines.append(f'   • {title2}: {format_chat_amount(chat_id, bal, True)}')
            if other_lines:
                lines.append('')
                lines.append('• Другие чаты:')
                lines.extend(other_lines)
            lines.append('')
            lines.append(f'• Всего по всем чатам: {format_chat_amount(chat_id, total_all, True)}')
            text = '\n'.join(lines)
        bot.edit_message_text(text, chat_id=chat_id, message_id=msg_id, parse_mode='HTML')
        if is_owner_chat(chat_id):
            schedule_owner_total_window_delete(chat_id, msg_id)
    except Exception as e:
        if 'message is not modified' in str(e).lower():
            if is_owner_chat(chat_id):
                schedule_owner_total_window_delete(chat_id, msg_id)
            return
        log_error(f'refresh_total_message_if_any({chat_id}): {e}')
        store['total_msg_id'] = None
        save_data(data)
try:
    _v177_legacy_0230_refresh_total_message_if_any.__name__ = 'refresh_total_message_if_any'
except Exception:
    pass

def refresh_owner_after_chat_change(source_chat_id: int):
    if not OWNER_ID:
        return
    try:
        owner_chat_id = int(OWNER_ID)
    except Exception:
        return
    if int(source_chat_id) == owner_chat_id:
        return
    try:
        owner_store = get_chat_store(owner_chat_id)
        owner_day_key = owner_store.get('current_view_day', today_key())
        backup_window_for_owner(owner_chat_id, owner_day_key, None)
        refresh_balance_panel_now(owner_chat_id)
        refresh_total_message_if_any(owner_chat_id)
    except Exception as e:
        log_error(f'refresh_owner_after_chat_change({source_chat_id}): {e}')

def cancel_pending_window_commands(chat_id: int, delete_prompt: bool=False):
    """Назад в основное окно отменяет режимы ожидания предыдущих окон и их таймеры."""
    try:
        clear_forward_copy_edit_wait(chat_id, delete_prompt=delete_prompt)
    except Exception:
        pass
    try:
        clear_edit_wait_state(chat_id, delete_prompt=delete_prompt)
    except Exception:
        pass
    try:
        clear_finwin_edit_wait_state(chat_id, delete_prompt=delete_prompt)
    except Exception:
        pass
    try:
        clear_category_wait_state(chat_id, 'category_add_wait', delete_prompt=delete_prompt)
    except Exception:
        pass
    try:
        clear_category_wait_state(chat_id, 'category_edit_wait', delete_prompt=delete_prompt)
    except Exception:
        pass
    try:
        _clear_secret_wait(chat_id, delete_prompt=delete_prompt)
    except Exception:
        pass
    try:
        store = get_chat_store(chat_id)
        if store.get('reset_wait'):
            store['reset_wait'] = False
            store['reset_time'] = 0
            save_data(data)
    except Exception:
        pass

def send_info(chat_id: int, text: str):
    send_and_auto_delete(chat_id, text, HELPER_DELETE_DELAY)

@bot.message_handler(commands=['owners', 'additional_owners', 'доп_владельцы'])
def cmd_additional_owners(msg):
    schedule_command_delete(msg)
    if '_tenant_send_dashboard' in globals():
        _tenant_send_dashboard(msg)
        return
    if not is_primary_owner(msg.chat.id):
        return
    bot.send_message(msg.chat.id, wm_owner('👥 Дополнительные владельцы\n\n✅ — доступ владельца включён\n⬜ — доступ выключен', 36), reply_markup=build_additional_owners_keyboard())

@bot.message_handler(commands=['windows', 'okna', 'окна'])
def cmd_windows_in_current_message(msg):
    schedule_command_delete(msg)
    enabled = toggle_chat_buttons_current_window(msg.chat.id)
    send_and_auto_delete(msg.chat.id, f"{('✅' if enabled else '⬜')} Режим открытия в текущем окне: {('ВКЛ' if enabled else 'ВЫКЛ')}", 8)

@bot.message_handler(commands=['ok', 'поехали'])
def cmd_ok(msg):
    try:
        update_chat_info_from_message(msg)
    except Exception:
        pass
    schedule_command_delete(msg)
    chat_id = msg.chat.id
    # R10: /ok (and /поехали) is owner/legacy finance activation only.
    # Contours 1/2 must use their explicit business-mode menu so a command
    # cannot bypass the owner's mode policy.
    try:
        if bool(globals().get('_v215_circle_business_chat', lambda _c: False)(int(chat_id))):
            try:
                send_and_auto_delete(chat_id, '🔒 /ok недоступна в контурах 1/2. Используйте «☰ Меню режимов».', 10)
            except Exception:
                pass
            try:
                globals().get('show_contour_start_modes', lambda *_a, **_k: None)(int(chat_id), int(getattr(getattr(msg, 'from_user', None), 'id', 0) or 0), 0)
            except Exception:
                pass
            return
    except Exception:
        pass
    set_total_secret_mode(chat_id, False)
    if is_finance_output_suppressed(chat_id):
        return
    stop_dozvon_for_target(chat_id)
    store = get_chat_store(chat_id)
    set_finance_mode(chat_id, True)
    view_day = finance_today_key()
    store['current_view_day'] = view_day
    store.setdefault('settings', {})['auto_add'] = True
    save_data(data)
    schedule_finalize(chat_id, view_day)
    send_and_auto_delete(chat_id, '✅ Финансовый режим включён', HELPER_DELETE_DELAY)

@bot.message_handler(commands=['start'])
def cmd_start(msg):
    try:
        update_chat_info_from_message(msg)
    except Exception:
        pass
    schedule_command_delete(msg)
    try:
        if 'tenant_handle_start_payload' in globals() and tenant_handle_start_payload(msg):
            return
    except Exception as e:
        log_error(f'tenant start payload: {e}')
    chat_id = msg.chat.id
    set_total_secret_mode(chat_id, False)
    if is_finance_output_suppressed(chat_id):
        return
    stop_dozvon_for_target(chat_id)
    if guard_non_owner_finance_for_command(msg, {'ok', 'help'}):
        return
    if not require_finance(chat_id):
        return
    day_key = finance_today_key() if is_finance_mode(chat_id) else today_key()
    get_chat_store(chat_id)['current_view_day'] = day_key
    force_new_day_window(chat_id, day_key)

@bot.message_handler(commands=['help'])
def cmd_help(msg):
    try:
        update_chat_info_from_message(msg)
    except Exception:
        pass
    schedule_command_delete(msg)
    chat_id = msg.chat.id
    if is_finance_output_suppressed(chat_id):
        return
    stop_dozvon_for_target(chat_id)
    help_text = build_help_text(chat_id)
    send_and_auto_delete(chat_id, help_text, HELPER_DELETE_DELAY)

@bot.message_handler(commands=['articles', 'статьи'])
def cmd_articles(msg):
    try:
        update_chat_info_from_message(msg)
    except Exception:
        pass
    schedule_command_delete(msg)
    chat_id = msg.chat.id
    if is_finance_output_suppressed(chat_id):
        return
    send_and_auto_delete(chat_id, build_articles_description_text(chat_id), 40)

@bot.message_handler(commands=['restore'])
def cmd_restore(msg):
    """Compatibility registration. Final v182 handler replaces this function in runtime_control."""
    fn = globals().get('v182_cmd_restore')
    if callable(fn) and fn is not cmd_restore:
        return fn(msg)
    global restore_mode
    restore_mode = int(msg.chat.id)
    send_and_auto_delete(msg.chat.id, '📥 Режим восстановления включён. Отправьте GZ / JSON / ISON / CSV.')

@bot.message_handler(commands=['restore_off'])
def cmd_restore_off(msg):
    try:
        schedule_command_delete(msg)
    except Exception:
        pass
    global restore_mode
    restore_mode = None
    data.pop('_restore_mode_chat_v150', None)
    send_and_auto_delete(msg.chat.id, '🔒 Режим восстановления выключен.')

@bot.message_handler(commands=['ping'])
def cmd_ping(msg):
    try:
        update_chat_info_from_message(msg)
    except Exception:
        pass
    schedule_command_delete(msg)
    if guard_non_owner_finance_for_command(msg, {'ok', 'help'}):
        return
    stop_dozvon_for_target(msg.chat.id)
    send_and_auto_delete(msg.chat.id, 'PONG — бот работает 🟢', HELPER_DELETE_DELAY)

@bot.message_handler(commands=['prev'])
def cmd_prev(msg):
    try:
        update_chat_info_from_message(msg)
    except Exception:
        pass
    schedule_command_delete(msg)
    chat_id = msg.chat.id
    if is_finance_output_suppressed(chat_id):
        return
    stop_dozvon_for_target(chat_id)
    if guard_non_owner_finance_for_command(msg, {'ok', 'help'}):
        return
    if not require_finance(chat_id):
        return
    d = datetime.strptime(today_key(), '%Y-%m-%d') - timedelta(days=1)
    day_key = d.strftime('%Y-%m-%d')
    get_chat_store(chat_id)['current_view_day'] = day_key
    update_or_send_day_window(chat_id, day_key)

@bot.message_handler(commands=['next'])
def cmd_next(msg):
    try:
        update_chat_info_from_message(msg)
    except Exception:
        pass
    schedule_command_delete(msg)
    chat_id = msg.chat.id
    if is_finance_output_suppressed(chat_id):
        return
    stop_dozvon_for_target(chat_id)
    if guard_non_owner_finance_for_command(msg, {'ok', 'help'}):
        return
    if not require_finance(chat_id):
        return
    d = datetime.strptime(today_key(), '%Y-%m-%d') + timedelta(days=1)
    day_key = d.strftime('%Y-%m-%d')
    get_chat_store(chat_id)['current_view_day'] = day_key
    update_or_send_day_window(chat_id, day_key)

@bot.message_handler(commands=['balance'])
def cmd_balance(msg):
    try:
        update_chat_info_from_message(msg)
    except Exception:
        pass
    schedule_command_delete(msg)
    chat_id = msg.chat.id
    if is_finance_output_suppressed(chat_id):
        return
    stop_dozvon_for_target(chat_id)
    if guard_non_owner_finance_for_command(msg, {'ok', 'help'}):
        return
    if not require_finance(chat_id):
        return
    store = get_chat_store(chat_id)
    bal = store.get('balance', 0)
    send_info(chat_id, f'💰 Баланс: {fmt_num(bal)}')

@bot.message_handler(commands=['report'])
def cmd_report(msg):
    try:
        update_chat_info_from_message(msg)
    except Exception:
        pass
    schedule_command_delete(msg)
    chat_id = msg.chat.id
    if is_finance_output_suppressed(chat_id):
        return
    stop_dozvon_for_target(chat_id)
    if guard_non_owner_finance_for_command(msg, {'ok', 'help'}):
        return
    if not require_finance(chat_id):
        return
    lines = build_day_report_lines(chat_id)
    report_html = '<pre>' + html.escape('\n'.join(lines)) + '</pre>'
    send_html_and_auto_delete(chat_id, report_html, 20)

def cmd_csv_all(chat_id: int):
    """Canonical CSV for all history of the current ARS/USD view."""
    if is_finance_output_suppressed(chat_id):
        return
    if not require_finance(chat_id):
        return
    return send_export_for_chat_to(int(chat_id), int(chat_id), 'all', today_key(), 'csv')

def cmd_csv_day(chat_id: int, day_key: str):
    """CSV for one day from the same canonical ARS/USD ledger as Excel/Google."""
    if is_finance_output_suppressed(chat_id):
        return
    if not require_finance(chat_id):
        return
    return send_export_for_chat_to(int(chat_id), int(chat_id), 'day', str(day_key)[:10], 'csv')

@bot.message_handler(commands=['runtime_export'])
def cmd_runtime_export(msg):
    try:
        update_chat_info_from_message(msg)
    except Exception:
        pass
    schedule_command_delete(msg)
    chat_id = int(msg.chat.id)
    if 'tenant_require_platform_owner' in globals():
        if not tenant_require_platform_owner(msg):
            return
    elif not is_owner_chat(chat_id):
        send_and_auto_delete(chat_id, 'Эта команда только для владельца платформы.', 8)
        return
    start_dt, end_dt = _runtime_export_parse_range(getattr(msg, 'text', '') or '')
    ok, info = submit_interactive_file_job(chat_id, 'runtime', 'Runtime / Watcher ZIP', send_runtime_export_zip, chat_id, start_dt, end_dt)
    if not ok:
        send_and_auto_delete(chat_id, f'⏳ {info}. Новая копия в очередь не добавлена.', 12)

@bot.message_handler(commands=['tabl_lsx'])
def cmd_tabl_lsx(msg):
    try:
        update_chat_info_from_message(msg)
    except Exception:
        pass
    schedule_command_delete(msg)
    chat_id = msg.chat.id
    if is_finance_output_suppressed(chat_id):
        return
    stop_dozvon_for_target(chat_id)
    if guard_non_owner_finance_for_command(msg, {'ok', 'help', 'tabl_lsx'}):
        return
    if not require_finance(chat_id):
        return
    ok, info = submit_interactive_file_job(chat_id, 'tabl_lsx', 'Excel /tabl_lsx', send_tabl_lsx_for_chat, chat_id, chat_id)
    if not ok:
        send_and_auto_delete(chat_id, f'⏳ {info}. Новая копия в очередь не добавлена.', 12)

@bot.message_handler(commands=['xlsx', 'excel'])
def cmd_xlsx(msg):
    try:
        update_chat_info_from_message(msg)
    except Exception:
        pass
    schedule_command_delete(msg)
    chat_id = msg.chat.id
    if is_finance_output_suppressed(chat_id):
        return
    stop_dozvon_for_target(chat_id)
    if guard_non_owner_finance_for_command(msg, {'ok', 'help'}):
        return
    if not require_finance(chat_id):
        return
    ok, info = submit_interactive_file_job(chat_id, 'xlsx', 'Excel за всё время', send_export_for_chat_to, chat_id, chat_id, 'all', today_key(), 'xlsx')
    if not ok:
        send_and_auto_delete(chat_id, f'⏳ {info}. Новая копия в очередь не добавлена.', 10)

def _send_csv_current_chat_job(chat_id: int):
    """Canonical current-ledger CSV; same source as all Excel/Google tables."""
    try:
        _file_job_progress('собираю канонический CSV', force=True)
        ok = send_export_for_chat_to(int(chat_id), int(chat_id), 'all', today_key(), 'csv')
        try:
            send_backup_to_channel(chat_id)
        except Exception:
            pass
        return bool(ok is not False)
    except Exception as e:
        log_error(f'_send_csv_current_chat_job: {e}')
        return False

@bot.message_handler(commands=['csv'])
def cmd_csv(msg):
    try:
        update_chat_info_from_message(msg)
    except Exception:
        pass
    '\n    Экспортирует CSV текущего чата.\n    '
    schedule_command_delete(msg)
    chat_id = msg.chat.id
    if is_finance_output_suppressed(chat_id):
        return
    stop_dozvon_for_target(chat_id)
    if guard_non_owner_finance_for_command(msg, {'ok', 'help'}):
        return
    if not require_finance(chat_id):
        return
    ok, info = submit_interactive_file_job(chat_id, 'csv', 'CSV этого чата', _send_csv_current_chat_job, chat_id)
    if not ok:
        send_and_auto_delete(chat_id, f'⏳ {info}. Новая копия в очередь не добавлена.', 10)

def _send_json_snapshot_job(chat_id: int):
    started = time.time()
    try:
        bot_journal('json_export_start', chat_id, 'создание атомарного снимка')
        store = snapshot_chat_store(chat_id)
        payload = build_chat_backup_payload(chat_id, store)
        raw = json.dumps(payload, ensure_ascii=False, indent=2).encode('utf-8')
        buf = io.BytesIO(raw)
        buf.name = f"{mega_safe_name(get_chat_display_name(chat_id), 'chat')}_{now_local().strftime('%Y%m%d_%H%M%S')}.json"
        _file_job_progress('отправляю JSON в Telegram', force=True)
        sent = _tg_call_retry(bot.send_document, chat_id, buf, caption='🧾 JSON этого чата — последние операции сверху', timeout=120, purpose='manual_json_export')
        elapsed = time.time() - started
        bot_journal('json_export_sent', chat_id, f"bytes={len(raw)} message_id={getattr(sent, 'message_id', '')} elapsed={elapsed:.3f}s")
        return True
    except Exception as e:
        bot_journal('json_export_error', chat_id, f'elapsed={time.time() - started:.3f}s error={e}', 'ERROR')
        send_and_auto_delete(chat_id, '❌ Не удалось создать JSON. Ошибка записана в журнал.', 15)
        return False

@bot.message_handler(commands=['json'])
def cmd_json(msg):
    try:
        update_chat_info_from_message(msg)
    except Exception:
        pass
    schedule_command_delete(msg)
    chat_id = int(msg.chat.id)
    if is_finance_output_suppressed(chat_id):
        return
    stop_dozvon_for_target(chat_id)
    if guard_non_owner_finance_for_command(msg, {'ok', 'help'}):
        return
    if not require_finance(chat_id):
        return
    bot_journal('json_command', chat_id, f"message_id={getattr(msg, 'message_id', '')}")
    ok, info = submit_interactive_file_job(chat_id, 'json', 'JSON снимок чата', _send_json_snapshot_job, chat_id)
    if not ok:
        send_and_auto_delete(chat_id, f'⏳ {info}. Новая копия в очередь не добавлена.', 10)

@bot.message_handler(commands=['reset'])
def cmd_reset(msg):
    try:
        update_chat_info_from_message(msg)
    except Exception:
        pass
    schedule_command_delete(msg)
    chat_id = msg.chat.id
    if is_finance_output_suppressed(chat_id):
        return
    stop_dozvon_for_target(chat_id)
    if guard_non_owner_finance_for_command(msg, {'ok', 'help'}):
        return
    if not require_finance(chat_id):
        return
    store = get_chat_store(chat_id)
    store['reset_wait'] = True
    store['reset_time'] = time.time()
    save_data(data)
    send_and_auto_delete(chat_id, '⚠️ Вы уверены, что хотите обнулить данные? Напишите ДА в течение 15 секунд.', 15)
    schedule_cancel_wait(chat_id, 15)

@bot.message_handler(commands=['stopforward'])
def cmd_stopforward(msg):
    try:
        update_chat_info_from_message(msg)
    except Exception:
        pass
    schedule_command_delete(msg)
    chat_id = msg.chat.id
    if is_finance_output_suppressed(chat_id):
        return
    stop_dozvon_for_target(chat_id)
    if guard_non_owner_finance_for_command(msg, {'ok', 'help'}):
        return
    if not is_owner_chat(chat_id):
        send_info(chat_id, 'Эта команда только для владельца.')
        schedule_command_delete(msg)
        return
    clear_forward_all()
    send_info(chat_id, 'Пересылка полностью отключена.')

@bot.message_handler(commands=['backup_channel_on'])
def cmd_on_channel(msg):
    try:
        update_chat_info_from_message(msg)
    except Exception:
        pass
    schedule_command_delete(msg)
    chat_id = msg.chat.id
    if is_finance_output_suppressed(chat_id):
        return
    stop_dozvon_for_target(chat_id)
    if guard_non_owner_finance_for_command(msg, {'ok', 'help'}):
        return
    if 'tenant_require_platform_owner' in globals():
        if not tenant_require_platform_owner(msg):
            return
    elif not is_owner_chat(chat_id):
        send_and_auto_delete(chat_id, 'Эта команда только для владельца платформы.', HELPER_DELETE_DELAY)
        return
    backup_flags['channel'] = True
    try:
        set_storage_profile_v237_1('telegram_durable')
    except Exception:
        pass
    save_data(data)
    send_info(chat_id, '📡 Telegram durable включён; MEGA и «Только Render» выключены')

@bot.message_handler(commands=['backup_channel_off'])
def cmd_off_channel(msg):
    try:
        update_chat_info_from_message(msg)
    except Exception:
        pass
    schedule_command_delete(msg)
    chat_id = msg.chat.id
    if is_finance_output_suppressed(chat_id):
        return
    stop_dozvon_for_target(chat_id)
    if guard_non_owner_finance_for_command(msg, {'ok', 'help'}):
        return
    if 'tenant_require_platform_owner' in globals():
        if not tenant_require_platform_owner(msg):
            return
    elif not is_owner_chat(chat_id):
        send_and_auto_delete(chat_id, 'Эта команда только для владельца платформы.', HELPER_DELETE_DELAY)
        return
    backup_flags['channel'] = False
    try:
        if storage_profile_v237_1() == STORAGE_PROFILE_TELEGRAM_V237_1:
            set_storage_profile_v237_1('render')
    except Exception:
        pass
    save_data(data)
    send_info(chat_id, '📡 Telegram durable выключен; выбран «Только Render»')

@bot.message_handler(commands=['dozvon'])
def cmd_dozvon(msg):
    try:
        update_chat_info_from_message(msg)
    except Exception:
        pass
    schedule_command_delete(msg)
    chat_id = msg.chat.id
    if is_finance_output_suppressed(chat_id):
        return
    stop_dozvon_for_target(chat_id)
    if guard_non_owner_finance_for_command(msg, {'ok', 'help'}):
        return
    connected = get_connected_chat_ids(chat_id)
    if not connected:
        send_and_auto_delete(chat_id, '📞 Нет связанных чатов для дозвона.', HELPER_DELETE_DELAY)
        return
    bot.send_message(chat_id, '📞 Выберите чат для дозвона:', reply_markup=build_dozvon_menu(chat_id))

def _v177_legacy_0231_send_and_auto_delete(chat_id: int, text: str, delay: int=HELPER_DELETE_DELAY):
    if is_finance_output_suppressed(chat_id):
        return
    if chat_buttons_current_window_enabled(chat_id):
        send_or_edit_stored_window(chat_id, 'command_window_id', text, delay=delay)
        return
    try:
        msg = bot.send_message(chat_id, text)

        def _delete():
            try:
                bot.delete_message(chat_id, msg.message_id)
            except Exception:
                pass
        DELAYED_SCHEDULER.schedule(f'auto-delete:{chat_id}:{msg.message_id}', delay, _delete)
    except Exception as e:
        log_error(f'send_and_auto_delete: {e}')
try:
    _v177_legacy_0231_send_and_auto_delete.__name__ = 'send_and_auto_delete'
except Exception:
    pass

def _v177_legacy_0233_send_html_and_auto_delete(chat_id: int, html_text: str, delay: int=HELPER_DELETE_DELAY):
    if is_finance_output_suppressed(chat_id):
        return
    if chat_buttons_current_window_enabled(chat_id):
        send_or_edit_stored_window(chat_id, 'command_window_id', html_text, parse_mode='HTML', delay=delay)
        return
    try:
        msg = bot.send_message(chat_id, html_text, parse_mode='HTML')

        def _delete():
            try:
                bot.delete_message(chat_id, msg.message_id)
            except Exception:
                pass
        DELAYED_SCHEDULER.schedule(f'auto-delete-html:{chat_id}:{msg.message_id}', delay, _delete)
    except Exception as e:
        log_error(f'send_html_and_auto_delete: {e}')
try:
    _v177_legacy_0233_send_html_and_auto_delete.__name__ = 'send_html_and_auto_delete'
except Exception:
    pass

def delete_message_later(chat_id: int, message_id: int, delay: int=30):
    """
    Отложенное удаление сообщения пользователя (например, команд).
    """
    try:

        def _job():
            try:
                bot.delete_message(chat_id, message_id)
            except Exception:
                pass
        DELAYED_SCHEDULER.schedule(f'delete-later:{chat_id}:{message_id}', delay, _job)
    except Exception as e:
        log_error(f'delete_message_later: {e}')
_edit_cancel_timers = {}

def clear_edit_wait_state(chat_id: int, expected_prompt_id: int | None=None, delete_prompt: bool=True):
    store = get_chat_store(chat_id)
    edit_wait = store.get('edit_wait') or {}
    prompt_id = edit_wait.get('prompt_msg_id')
    if expected_prompt_id is not None and prompt_id and (int(prompt_id) != int(expected_prompt_id)):
        return False
    key = (int(chat_id), 'edit_wait')
    _edit_cancel_timers.pop(key, None)
    DELAYED_SCHEDULER.cancel(f'edit-wait:{int(chat_id)}')
    store['edit_wait'] = None
    if callable(globals().get('_v262_schedule_transient_chat_persist')):
        _v262_schedule_transient_chat_persist(chat_id)
    if delete_prompt and prompt_id:
        try:
            bot.delete_message(chat_id, int(prompt_id))
        except Exception:
            pass
    return True

def clear_finwin_edit_wait_state(chat_id: int, expected_prompt_id: int | None=None, delete_prompt: bool=True):
    store = get_chat_store(chat_id)
    edit_wait = store.get('finwin_edit_wait') or {}
    prompt_id = edit_wait.get('prompt_msg_id')
    if expected_prompt_id is not None and prompt_id and (int(prompt_id) != int(expected_prompt_id)):
        return False
    key = (int(chat_id), 'finwin_edit_wait')
    _edit_cancel_timers.pop(key, None)
    DELAYED_SCHEDULER.cancel(f'finwin-edit-wait:{int(chat_id)}')
    store['finwin_edit_wait'] = None
    if callable(globals().get('_v262_schedule_transient_chat_persist')):
        _v262_schedule_transient_chat_persist(chat_id)
    if delete_prompt and prompt_id:
        try:
            bot.delete_message(chat_id, int(prompt_id))
        except Exception:
            pass
    return True

def _edit_countdown_text(base_text: str, remaining: int) -> str:
    base = strip_window_mark(str(base_text or '')).rstrip()
    return wm_common(base + f'\n\n⏳ До закрытия: {int(remaining)} сек.', 10)

def schedule_cancel_finwin_edit(chat_id: int, prompt_message_id: int, delay: float | None=None):
    """Единый таймер фин-редактирования; timeout отменяет ввод и возвращает основное окно."""
    key = (int(chat_id), 'finwin_edit_wait')
    scheduler_key = f'finwin-edit-wait:{int(chat_id)}'
    if delay is None:
        delay = internal_timer_seconds('input_wait', 40)

    def _job():
        try:
            store = get_chat_store(chat_id)
            wait = store.get('finwin_edit_wait') or {}
            if not wait or int(wait.get('prompt_msg_id') or 0) != int(prompt_message_id):
                return
            cleared = clear_finwin_edit_wait_state(chat_id, prompt_message_id, delete_prompt=False)
            if cleared:
                day_key = store.get('current_view_day') or today_key()
                return_to_main_window_closing_previous(chat_id, day_key, int(prompt_message_id))
                log_info(f'finwin edit_wait auto-cancelled for chat {chat_id}')
        except Exception as e:
            log_error(f'schedule_cancel_finwin_edit({chat_id},{prompt_message_id}): {e}')
    DELAYED_SCHEDULER.cancel(scheduler_key)
    deadline = DELAYED_SCHEDULER.schedule(scheduler_key, float(delay), _job)
    _edit_cancel_timers[key] = deadline

def schedule_cancel_edit(chat_id: int, prompt_message_id: int, delay: float | None=None):
    """Единый таймер обычного редактирования; timeout отменяет ввод и возвращает основное окно."""
    key = (int(chat_id), 'edit_wait')
    scheduler_key = f'edit-wait:{int(chat_id)}'
    if delay is None:
        delay = internal_timer_seconds('input_wait', 40)

    def _job():
        try:
            store = get_chat_store(chat_id)
            wait = store.get('edit_wait') or {}
            if not wait or int(wait.get('prompt_msg_id') or 0) != int(prompt_message_id):
                return
            cleared = clear_edit_wait_state(chat_id, prompt_message_id, delete_prompt=False)
            if cleared:
                day_key = store.get('current_view_day') or today_key()
                return_to_main_window_closing_previous(chat_id, day_key, int(prompt_message_id))
        except Exception as e:
            log_error(f'schedule_cancel_edit({chat_id},{prompt_message_id}): {e}')
    DELAYED_SCHEDULER.cancel(scheduler_key)
    deadline = DELAYED_SCHEDULER.schedule(scheduler_key, float(delay), _job)
    _edit_cancel_timers[key] = deadline

def schedule_cancel_wait(chat_id: int, delay: float=15.0):
    """Через delay секунд сбрасывает reset_wait через общий планировщик."""
    scheduler_key = f'reset-wait:{int(chat_id)}'

    def _job():
        try:
            store = get_chat_store(chat_id)
            changed = False
            if store.get('reset_wait', False):
                store['reset_wait'] = False
                store['reset_time'] = 0
                changed = True
            if changed:
                save_data(data)
        except Exception as e:
            log_error(f'schedule_cancel_wait job: {e}')
    DELAYED_SCHEDULER.cancel(scheduler_key)
    deadline = DELAYED_SCHEDULER.schedule(scheduler_key, float(delay), _job)
    _edit_cancel_timers[int(chat_id)] = deadline

def _remember_known_chat_user(store: dict, msg) -> bool:
    """Кэширует пользователей, которых бот реально видел в чате.

    Telegram Bot API не выдаёт полный список участников группы, поэтому этот кэш
    дополняет список администраторов в окне «Описание чатов».
    """
    try:
        user = getattr(msg, 'from_user', None)
        if user is None or not getattr(user, 'id', None):
            return False
        uid = str(int(user.id))
        users = store.setdefault('known_users', {})
        old = dict(users.get(uid) or {})
        now_ts = time.time()
        row = {'id': int(user.id), 'first_name': str(getattr(user, 'first_name', '') or ''), 'last_name': str(getattr(user, 'last_name', '') or ''), 'username': str(getattr(user, 'username', '') or '').lstrip('@') or None, 'is_bot': bool(getattr(user, 'is_bot', False)), 'is_premium': bool(getattr(user, 'is_premium', False)), 'language_code': str(getattr(user, 'language_code', '') or '') or None, 'last_seen': old.get('last_seen') or now_local().isoformat(timespec='seconds'), 'last_seen_ts': float(old.get('last_seen_ts') or 0)}
        if now_ts - float(row.get('last_seen_ts') or 0) >= 3600 or not old:
            row['last_seen'] = now_local().isoformat(timespec='seconds')
            row['last_seen_ts'] = now_ts
        changed = old != row
        if changed:
            users[uid] = row
            if len(users) > 500:
                ordered = sorted(users.items(), key=lambda item: float((item[1] or {}).get('last_seen_ts') or 0))
                for old_uid, _ in ordered[:len(users) - 500]:
                    users.pop(old_uid, None)
        return changed
    except Exception:
        return False

def _v177_legacy_0235_update_chat_info_from_message(msg):
    """
    Обновляет информацию о чате в памяти.
    На диск пишем только если реально что-то изменилось.
    """
    chat_id = msg.chat.id
    was_new_chat = str(chat_id) not in (data.get('chats', {}) if isinstance(data, dict) else {})
    try:
        if not getattr(getattr(msg, 'from_user', None), 'is_bot', False):
            stop_dozvon_for_target(chat_id)
    except Exception:
        pass
    store = get_chat_store(chat_id)
    try:
        if store.setdefault('settings', {}).get('bot_removed'):
            store['settings']['bot_removed'] = False
            store['settings'].pop('bot_removed_reason', None)
            store['settings'].pop('bot_removed_at', None)
            save_data(data)
    except Exception:
        pass
    info = store.setdefault('info', {})
    info.setdefault('title', '')
    info.setdefault('username', None)
    info.setdefault('type', getattr(msg.chat, 'type', None))
    changed = False
    try:
        if getattr(getattr(msg, 'from_user', None), 'is_bot', False) and (not getattr(msg.chat, 'title', None)):
            return
    except Exception:
        pass
    new_title = _chat_title_from_message(msg, info.get('title') or '')
    new_username = _chat_username_from_message(msg)
    new_type = msg.chat.type
    if _remember_known_chat_user(store, msg):
        changed = True
    if info.get('title') != new_title:
        info['title'] = new_title
        changed = True
    if info.get('username') != new_username:
        info['username'] = new_username
        changed = True
    if info.get('type') != new_type:
        info['type'] = new_type
        changed = True
    if OWNER_ID and str(chat_id) != str(OWNER_ID):
        owner_store = get_chat_store(int(OWNER_ID))
        kc = owner_store.setdefault('known_chats', {})
        new_known = {'title': info.get('title') or get_chat_display_name(chat_id), 'username': info.get('username'), 'type': info.get('type')}
        new_identity = _chat_identity_key(chat_id, new_known)
        for old_cid, old_info in list(kc.items()):
            try:
                old_id_int = int(old_cid)
            except Exception:
                kc.pop(old_cid, None)
                changed = True
                continue
            if str(old_cid) != str(chat_id) and _chat_identity_key(old_id_int, old_info if isinstance(old_info, dict) else {}) == new_identity:
                kc.pop(old_cid, None)
                changed = True
        if kc.get(str(chat_id)) != new_known:
            kc[str(chat_id)] = new_known
            changed = True
    if changed:
        save_data(data)
        try:
            ids_for_backup = [chat_id]
            if OWNER_ID:
                ids_for_backup.append(int(OWNER_ID))
            schedule_config_backup_for_chats(*ids_for_backup, delay=2.0)
        except Exception as e:
            log_error(f'chat info changed backup schedule {chat_id}: {e}')
    try:
        if was_new_chat and OWNER_ID and (str(chat_id) != str(OWNER_ID)):
            maybe_prompt_owner_for_new_chat_auto_backup(chat_id)
    except Exception as e:
        log_error(f'new chat auto-backup prompt failed for {get_chat_display_name(chat_id)}: {e}')
try:
    _v177_legacy_0235_update_chat_info_from_message.__name__ = 'update_chat_info_from_message'
except Exception:
    pass

def maybe_prompt_owner_for_new_chat_auto_backup(chat_id: int):
    """При первом появлении чата спрашиваем владельца, обновлять ли JSON/CSV бэкапы автоматически."""
    if not OWNER_ID:
        return
    store = get_chat_store(chat_id)
    settings = store.setdefault('settings', {})
    if settings.get('owner_auto_backup_prompted'):
        return
    settings['owner_auto_backup_prompted'] = True
    settings.setdefault('auto_backup_enabled', True)
    save_data(data)
    owner_id = int(OWNER_ID)
    title = get_chat_display_name(chat_id)
    text = f'🆕 Новый чат появился в картотеке\n\n{title}\nАвтоматически обновлять JSON/CSV бэкапы по этому чату?'
    kb = types.InlineKeyboardMarkup(row_width=2)
    kb.row(IB('✅ Да', callback_data=f'ncb:{chat_id}:yes'), IB('❌ Нет', callback_data=f'ncb:{chat_id}:no'))
    msg = bot.send_message(owner_id, text, reply_markup=kb)
    settings['owner_auto_backup_prompt_msg_id'] = msg.message_id
    save_data(data)
    delete_message_later(owner_id, msg.message_id, 10)

def _safe_tmp_json_name(fname: str) -> str:
    base = os.path.basename(str(fname or 'backup.json'))
    base = re.sub('[^0-9A-Za-zА-Яа-я_.\\-]+', '_', base)
    if not base.lower().endswith('.json'):
        base += '.json'
    return base[:80]

def _extract_chat_id_from_json_filename(fname: str):
    """Пытается вытащить chat_id из имени data_<chat_id>.json."""
    try:
        m = re.search('(?:data|chat)_(-?\\d+)\\.(?:json|ison)$', str(fname or '').strip().lower())
        if m:
            return int(m.group(1))
    except Exception:
        pass
    return None

def _describe_json_restore_payload(payload, fname: str=''):
    """Возвращает короткое описание JSON перед подтверждением восстановления."""
    fname_l = str(fname or '').lower()
    if fname_l == 'csv_meta.json':
        return ('метаданные CSV', None)
    if isinstance(payload, dict) and isinstance(payload.get('chats'), dict):
        return (f"глобальный data.json, чатов: {len(payload.get('chats') or {})}", None)
    if isinstance(payload, dict):
        cid = payload.get('chat_id')
        if cid is None:
            cid = _extract_chat_id_from_json_filename(fname)
        if cid is not None:
            try:
                cid = int(cid)
                rec_count = len(payload.get('records') or []) if isinstance(payload.get('records'), list) else 0
                daily = payload.get('daily_records') or {}
                if isinstance(daily, dict):
                    rec_count = rec_count or sum((len(v or []) for v in daily.values()))
                return (f'JSON чата {get_chat_display_name(cid)} / ID {cid}, записей: {rec_count}', cid)
            except Exception:
                pass
    return ('JSON-файл неизвестного формата', None)

def _apply_json_restore_from_owner_prompt(owner_chat_id: int, tmp_path: str, fname: str) -> str:
    """
    Восстановление JSON, когда владелец прислал файл без /restore и нажал ✅ Да.
    Поддерживает:
    • глобальный data.json / JSON с ключом chats;
    • csv_meta.json;
    • per-chat JSON data_<chat_id>.json или JSON с chat_id.
    """
    global data, restore_mode
    fname_l = str(fname or '').lower()
    payload = _load_json(tmp_path, None)
    if not isinstance(payload, dict):
        raise RuntimeError('JSON повреждён или не является объектом')
    if fname_l == 'csv_meta.json':
        os.replace(tmp_path, CSV_META_FILE)
        _save_csv_meta(_load_json(CSV_META_FILE, {}) or {})
        restore_mode = None
        return '🟢 csv_meta.json обновлён'
    if fname_l == 'data.json' or isinstance(payload.get('chats'), dict):
        result = restore_from_json(int(owner_chat_id), tmp_path, actor_user_id=int(OWNER_ID or owner_chat_id))
        export_global_csv(data)
        restore_mode = None
        return f"🟢 Глобальный JSON полностью восстановлен; чатов: {result.get('chats', 0)}"
    target_chat_id = payload.get('chat_id')
    if target_chat_id is None:
        target_chat_id = _extract_chat_id_from_json_filename(fname_l)
    if target_chat_id is None:
        raise RuntimeError('В JSON нет chat_id и его нельзя понять из имени файла')
    target_chat_id = int(target_chat_id)
    result = restore_from_json(target_chat_id, tmp_path, actor_user_id=int(OWNER_ID or owner_chat_id))
    restore_mode = None
    return f"🟢 JSON/ISON чата восстановлен СТРОГО ИЗ ФАЙЛА: {get_chat_display_name(target_chat_id)}; в файле={result.get('backup_records', 0)}, итог={result.get('records_after', 0)}, предыдущее live-состояние заменено={result.get('replaced_live_records', 0)}"

def _cleanup_owner_json_restore_prompt(key: int, remove_prompt: bool=False):
    try:
        with _owner_json_restore_prompt_lock:
            item = _owner_json_restore_prompts.pop(int(key), None)
        if not item:
            return
        if remove_prompt:
            try:
                bot.delete_message(int(OWNER_ID), int(item.get('prompt_msg_id')))
            except Exception:
                pass
        tmp_path = item.get('tmp_path')
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except Exception:
                pass
    except Exception as e:
        log_error(f'_cleanup_owner_json_restore_prompt({key}): {e}')

def _schedule_owner_json_restore_prompt_cleanup(key: int, delay: int=12):

    def _job():
        _cleanup_owner_json_restore_prompt(key, remove_prompt=True)
    try:
        DELAYED_SCHEDULER.schedule(f'owner-json-restore-cleanup:{int(key)}', delay, _job)
    except Exception as e:
        log_error(f'_schedule_owner_json_restore_prompt_cleanup({key}): {e}')

def maybe_prompt_owner_for_json_restore(msg, fname: str) -> bool:
    """
    Если владелец прислал .json в личку без /restore — спрашиваем, обновлять данные или нет.
    Кнопки/окно удаляются через 10 секунд в любом случае.
    """
    try:
        if not is_owner_chat(msg.chat.id):
            return False
        if restore_mode is not None:
            return False
        if not str(fname or '').lower().endswith(('.json', '.ison')):
            return False
        file_info = bot.get_file(msg.document.file_id)
        tmp_name = f'owner_json_restore_{int(msg.chat.id)}_{int(msg.message_id)}_{_safe_tmp_json_name(fname)}'
        stream_fn = globals().get('telegram_download_to_file')
        if callable(stream_fn):
            max_restore = max(1024 * 1024, int(os.getenv('RESTORE_FILE_MAX_BYTES', str(100 * 1024 * 1024)) or str(100 * 1024 * 1024)))
            stream_fn(file_info.file_path, tmp_name, max_bytes=max_restore)
        else:
            raw = bot.download_file(file_info.file_path)
            with open(tmp_name, 'wb') as f:
                f.write(raw)
            raw = None
        payload = _load_json(tmp_name, None)
        if not isinstance(payload, dict):
            try:
                os.remove(tmp_name)
            except Exception:
                pass
            send_and_auto_delete(int(msg.chat.id), f'⚠️ JSON не прочитан или повреждён: {fname}', 10)
            return True
        desc, target_chat_id = _describe_json_restore_payload(payload, fname)
        key = int(msg.message_id)
        text = f'🧾 В чате владельца появился JSON-файл без /restore\n\nФайл: {fname}\nЧто внутри: {desc}\n\nОбновить данные бота из этого JSON?'
        kb = types.InlineKeyboardMarkup(row_width=2)
        kb.row(IB('✅ Да', callback_data=f'ojr:{key}:yes'), IB('❌ Нет', callback_data=f'ojr:{key}:no'))
        sent = bot.send_message(int(msg.chat.id), text, reply_markup=kb)
        with _owner_json_restore_prompt_lock:
            _owner_json_restore_prompts[key] = {'tmp_path': tmp_name, 'fname': fname, 'prompt_msg_id': sent.message_id, 'created_at': time.time(), 'target_chat_id': target_chat_id}
        delete_message_later(int(msg.chat.id), sent.message_id, 10)
        _schedule_owner_json_restore_prompt_cleanup(key, 12)
        return True
    except Exception as e:
        log_error(f'maybe_prompt_owner_for_json_restore({fname}): {e}')
        return False

def run_owner_json_restore_prompt_job(owner_chat_id: int, item: dict):
    tmp_path = item.get('tmp_path')
    fname = item.get('fname') or 'backup.json'
    pre_restore_dir = ''
    restore_epoch = 0
    restore_success = False
    try:
        backup_fn = globals().get('_v153_backup_before_restore')
        if not callable(backup_fn):
            raise RuntimeError('pre_restore backup helper недоступен')
        durable_ready = bool(globals().get('telegram_durable_primary_v234', lambda: False)())
        if not durable_ready and callable(globals().get('mega_is_configured')) and (not mega_is_configured()):
            raise RuntimeError('Внешнее durable-хранилище не настроено — восстановление остановлено')
        pre_restore_dir = backup_fn()
        bot_journal('restore_pre_backup_owner_prompt_v184', int(owner_chat_id), f'file={fname}')
        begin_restore = globals().get('_v241_restore_storage_barrier_begin')
        if callable(begin_restore):
            restore_epoch = int(begin_restore() or 0)
        with data_lock:
            result = _apply_json_restore_from_owner_prompt(owner_chat_id, tmp_path, fname)
        _v240_restore_reanchor_guaranteed(f'owner_json_prompt:{fname}')
        restore_success = True
        send_and_auto_delete(owner_chat_id, result + '\n🏛 DATA CONSTITUTION: состояние закреплено новым generation.', 15)
    except Exception as e:
        send_and_auto_delete(owner_chat_id, f'❌ JSON/ISON не восстановлен: {e}', 15)
    finally:
        if restore_epoch:
            end_restore = globals().get('_v241_restore_storage_barrier_end')
            if callable(end_restore):
                try:
                    end_restore(restore_epoch, restore_success)
                except Exception:
                    pass
        try:
            if pre_restore_dir:
                shutil.rmtree(pre_restore_dir, ignore_errors=True)
        except Exception:
            pass
        try:
            if tmp_path and os.path.exists(tmp_path):
                os.remove(tmp_path)
        except Exception:
            pass
# v262
