# v262
def _canon_record_day_key__001(rec: dict) -> str:
    """Безопасно возвращает day_key для записи."""
    dk = rec.get('day_key')
    if dk:
        return str(dk)[:10]
    ts = rec.get('timestamp') or ''
    if isinstance(ts, str) and len(ts) >= 10 and re.match('\\d{4}-\\d{2}-\\d{2}', ts[:10]):
        rec['day_key'] = ts[:10]
        return ts[:10]
    rec['day_key'] = today_key()
    return rec['day_key']

def _v258_record_strong_keys(rec: dict, chat_id: int) -> list[str]:
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

def _v258_merge_duplicate_finance_records(chat_id: int, records: list[dict]) -> tuple[list[dict], int]:
    """Collapse historical deploy/edit duplicates without merging real operations.

    Same Telegram message must produce one finance record.  The oldest record id
    is kept for button/reference stability, while editable finance fields are
    taken from the newest duplicate (the usual post-deploy edited copy).
    """
    cid = int(chat_id)
    out = []
    key_to_idx = {}
    removed = 0
    editable = ('amount','note','usd_amount','usd_note','usd_only','source_finance_text',
                'timestamp','day_key','owner','category_override_slug','currency')
    identity_fill = ('source_msg_id','origin_msg_id','msg_id','source_order_msg_id','operation_key')
    for raw in records or []:
        if not isinstance(raw, dict):
            continue
        rec = raw
        keys = _v258_record_strong_keys(rec, cid)
        matches = sorted({key_to_idx[k] for k in keys if k in key_to_idx})
        if not matches:
            idx = len(out)
            out.append(rec)
            for k in keys:
                key_to_idx[k] = idx
            continue
        idx = matches[0]
        base = out[idx]
        # If older corrupted state already created more than one canonical bucket
        # that this row bridges, fold those buckets too.
        for other_idx in reversed(matches[1:]):
            if other_idx == idx or other_idx >= len(out):
                continue
            other = out[other_idx]
            try:
                base_id = int(base.get('id') or 0)
                other_id = int(other.get('id') or 0)
            except Exception:
                base_id = other_id = 0
            newer = other if other_id >= base_id else base
            for fld in editable:
                if fld in newer:
                    base[fld] = newer.get(fld)
            for fld in identity_fill:
                if not base.get(fld) and other.get(fld):
                    base[fld] = other.get(fld)
            out.pop(other_idx)
            removed += 1
            # Rebuild map after structural fold; duplicate migrations are tiny and
            # correctness is more important than micro-optimizing this path.
            key_to_idx = {}
            for oi, rr in enumerate(out):
                for kk in _v258_record_strong_keys(rr, cid):
                    key_to_idx[kk] = oi
            idx = min(idx, len(out)-1)
            base = out[idx]
        try:
            base_id = int(base.get('id') or 0)
            rec_id = int(rec.get('id') or 0)
        except Exception:
            base_id = rec_id = 0
        newer = rec if rec_id >= base_id else base
        # Keep the canonical (usually oldest) record id/record_uid, but apply the
        # newest financial edit so an old dragon/emoji/text variant disappears.
        for fld in editable:
            if fld in newer:
                base[fld] = newer.get(fld)
        for fld in identity_fill:
            if not base.get(fld) and rec.get(fld):
                base[fld] = rec.get(fld)
        for k in set(keys + _v258_record_strong_keys(base, cid)):
            key_to_idx[k] = idx
        removed += 1
    return out, removed

def normalize_chat_records(chat_id: int) -> None:
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

def recalc_balance(chat_id: int):
    normalize_chat_records(chat_id)
    store = get_chat_store(chat_id)
    store['balance'] = sum((float(r.get('amount', 0) or 0) for r in store.get('records', [])))

def rebuild_month_short_ids(chat_id: int):
    """Пересчитывает short_id как месячную нумерацию по стабильной хронологии."""
    normalize_chat_records(chat_id)
    store = get_chat_store(chat_id)
    daily = store.get('daily_records', {}) or {}
    month_counters = {}
    usd_month_counters = {}
    for dk in sorted(daily.keys()):
        month_key = dk[:7]
        month_counters.setdefault(month_key, 1)
        usd_month_counters.setdefault(month_key, 1)
        recs = sorted(daily.get(dk, []) or [], key=record_sort_key)
        daily[dk] = recs
        for r in recs:
            try:
                if 'ensure_finance_record_uid' in globals():
                    ensure_finance_record_uid(int(chat_id), r)
            except Exception:
                pass
            has_usd = bool(float(r.get('usd_amount', 0) or 0))
            usd_only = bool(r.get('usd_only', False))
            if not usd_only:
                r['short_id'] = f'R{month_counters[month_key]}'
                month_counters[month_key] += 1
            elif has_usd:
                r['short_id'] = f'U{usd_month_counters[month_key]}'
            if has_usd:
                r['usd_short_id'] = f'U{usd_month_counters[month_key]}'
                usd_month_counters[month_key] += 1
    store['records'] = [r for dk in sorted(daily.keys()) for r in daily.get(dk, [])]

def calc_day_balance(store: dict, day_key: str) -> float:
    """R16 fast closing balance: O(1) for the latest day, cached for history."""
    day_key = str(day_key or '')[:10]
    daily = store.get('daily_records', {}) or {}
    if not daily:
        return 0.0
    try:
        latest = max(str(k)[:10] for k in daily.keys())
        if day_key >= latest:
            return float(store.get('balance', 0) or 0)
    except Exception:
        pass
    gen = int(store.get('_finance_fast_generation_r16', 0) or 0)
    cache = store.setdefault('_finance_day_balance_cache_r16', {})
    cached = cache.get(day_key) if isinstance(cache, dict) else None
    if isinstance(cached, dict) and int(cached.get('generation', -1)) == gen:
        try: return float(cached.get('value', 0) or 0)
        except Exception: pass
    total = 0.0
    for dk in sorted(daily.keys()):
        if str(dk)[:10] > day_key:
            break
        for r in daily.get(dk, []) or []:
            total += float(r.get('amount', 0) or 0)
    try:
        cache[day_key] = {'generation': gen, 'value': float(total)}
        if len(cache) > 64:
            for key in list(cache)[:-64]: cache.pop(key, None)
    except Exception:
        pass
    return float(total)

def rebuild_global_records():
    """Быстрый общий итог без копирования всех записей всех чатов при каждом сообщении."""
    with data_lock:
        total = 0.0
        for _cid, store in (data.get('chats', {}) or {}).items():
            try:
                if 'balance' in store:
                    total += float(store.get('balance', 0) or 0)
                else:
                    total += sum((float(r.get('amount', 0) or 0) for r in store.get('records', []) or []))
            except Exception:
                pass
        data['records'] = []
        data['overall_balance'] = total
_finalize_timers = {}
_backup_timers = {}
_quick_backup_timers = {}
_balance_panel_refresh_timers = {}
_balance_panel_collapse_timers = {}
_balance_panel_first_timers = {}
_balance_panel_recreate_timers = {}
_total_message_timers = {}
_backup_dirty_chats = set()
_quick_backup_dirty_chats = set()
_global_mega_timer = None

def collect_finance_chat_ids():
    ids = set()
    try:
        for cid, enabled in (data.get('finance_active_chats', {}) or {}).items():
            if enabled:
                ids.add(int(cid))
    except Exception:
        pass
    try:
        for cid in list(finance_active_chats):
            ids.add(int(cid))
    except Exception:
        pass
    try:
        for cid, store in (data.get('chats', {}) or {}).items():
            try:
                int_cid = int(cid)
            except Exception:
                continue
            if store.get('finance_mode') or (OWNER_ID and str(int_cid) == str(OWNER_ID)):
                ids.add(int_cid)
    except Exception:
        pass
    return sorted(ids)

def _canon_schedule_startup_main_windows__001(delay: float=3.0):
    """v108: restore only automatic finance windows that were actually open before deploy."""

    def _job():
        try:
            for cid in collect_finance_chat_ids():
                try:
                    if is_chat_bot_removed(cid):
                        continue
                    store = get_chat_store(cid)
                    state = _finance_window_state(cid)
                    mode = finance_window_mode(cid)
                    if mode == 'off' or not bool(state.get('auto_reopen_on_boot', False)):
                        continue
                    day_key = store.get('current_view_day') or today_key()
                    if mode == 'normal':
                        update_or_send_day_window(cid, day_key)
                    elif mode in {'open', 'first'}:
                        if store.get('balance_panel_id'):
                            refresh_balance_panel_now(cid)
                        else:
                            send_minimized_balance_panel(cid)
                        if mode == 'first':
                            schedule_quick_balance_first_recreate(cid, 60.0)
                    time.sleep(0.2)
                except Exception as e:
                    log_error(f'startup_finance_window({get_chat_display_name(cid)}): {e}')
        except Exception as e:
            log_error(f'schedule_startup_main_windows job: {e}')
    try:
        DELAYED_SCHEDULER.schedule('startup-main-windows', delay, _job)
    except Exception as e:
        log_error(f'schedule_startup_main_windows: {e}')

def schedule_all_finance_backups(delay: float=10.0):
    for cid in collect_finance_chat_ids():
        schedule_backup_flush(cid, delay=delay)

def _schedule_global_mega_snapshot(delay: float=30.0):
    """Совместимость старых вызовов: v90 лишь отмечает pending full snapshot.

    Полный global больше не создаётся через 20–30 секунд после каждого чата.
    Его запускает общий quiet/max scheduler.
    """
    _mark_global_snapshot_pending()

def _run_quick_chat_backup(chat_id: int):
    """v90 quick backup = маленький immutable delta, а не полная копия чата/global."""
    chat_id = int(chat_id)
    if RESTORE_GUARD_ACTIVE:
        log_error(f'QUICK DELTA BLOCKED {chat_id}: {RESTORE_GUARD_REASON}')
        return
    with state_chat_context(chat_id):
        try:
            save_data(data, chat_ids=[chat_id])
            with _delta_state_lock:
                _delta_pending_chats.add(chat_id)
                if not _delta_chat_generation.get(chat_id):
                    _delta_chat_generation[chat_id] = int(time.time_ns())
            if not durable_run_pending_delta_now_v234():
                schedule_delta_backup(chat_id, BACKUP_BUSY_RETRY_SECONDS, reason='delta_retry')
        finally:
            with timer_lock:
                _quick_backup_dirty_chats.discard(chat_id)

def _run_full_chat_backup(chat_id: int, expected_epoch: int | None=None):
    chat_id = int(chat_id)
    if expected_epoch is not None and int(expected_epoch) != int(globals().get('_V241_STORAGE_EPOCH', 0) or 0):
        try:
            bot_journal('stale_full_backup_skipped_v241', chat_id, f"job={expected_epoch}; current={globals().get('_V241_STORAGE_EPOCH', 0)}")
        except Exception:
            pass
        return
    if globals().get('_V241_RESTORE_ACTIVE', False):
        return
    if RESTORE_GUARD_ACTIVE:
        log_error(f'FULL BACKUP BLOCKED {chat_id}: {RESTORE_GUARD_REASON}')
        return
    with state_chat_context(chat_id):
        try:
            if not is_finance_mode(chat_id):
                return
            if not is_auto_backup_enabled(chat_id):
                return
            save_data(data, chat_ids=[chat_id])
            save_chat_json(chat_id)
            if expected_epoch is not None and int(expected_epoch) != int(globals().get('_V241_STORAGE_EPOCH', 0) or 0):
                try:
                    bot_journal('stale_full_backup_midflight_skipped_v241', chat_id, f"job={expected_epoch}; current={globals().get('_V241_STORAGE_EPOCH', 0)}")
                except Exception:
                    pass
                return
            if globals().get('_V241_RESTORE_ACTIVE', False):
                return
            if is_backup_to_chat_enabled(chat_id) and can_receive_direct_json_backup(chat_id) and (not is_finance_output_suppressed(chat_id)):
                send_backup_to_chat(chat_id, ensure_files=False)
            if is_backup_to_channel_enabled(chat_id):
                send_backup_to_channel(chat_id, ensure_files=False)
            if is_backup_to_mega_enabled(chat_id):
                mega_upload_chat_backup_bundle(chat_id, current_month_key())
                _mark_global_snapshot_pending()
        except Exception as exc:
            log_error(f'_run_full_chat_backup({chat_id}): {exc}')
        finally:
            with timer_lock:
                _backup_dirty_chats.discard(chat_id)
                _backup_timers.pop(chat_id, None)
            try:
                _lowram_release_chat(chat_id)
            except Exception as _lr_exc:
                log_error(f'LOWRAM full-backup release {chat_id}: {_lr_exc}')

def schedule_quick_backup(chat_id: int, delay: float | None=None):
    """Debounce delta for one chat. Critical toggle callbacks defer async delta until their sync commit.

    Without this tiny guard, an async delta could persist the toggled state a fraction of a second
    before its idempotency marker. A deploy in that microscopic gap could replay the toggle twice.
    """
    chat_id = int(chat_id)
    try:
        ctx = getattr(_TELEGRAM_UPDATE_CONTEXT, 'value', None)
        if isinstance(ctx, dict) and ctx.get('critical_callback'):
            ctx.setdefault('deferred_quick_chats', set()).add(chat_id)
            return
    except Exception:
        pass
    if RESTORE_GUARD_ACTIVE:
        return
    if delay is None:
        delay = MEGA_DELTA_PRIORITY_DELAY_SECONDS if mega_backup_priority_enabled() else MEGA_DELTA_DELAY_SECONDS
    due = time.time() + max(0.5, float(delay))
    expected_epoch = int(globals().get('_V241_STORAGE_EPOCH', 0) or 0)
    with timer_lock:
        _quick_backup_dirty_chats.add(chat_id)
        _quick_backup_timers[chat_id] = due
    with _delta_state_lock:
        global _delta_generation
        _delta_generation += 1
        _delta_pending_chats.add(chat_id)
        _delta_chat_generation[chat_id] = _delta_generation

    def _fire():
        if expected_epoch != int(globals().get('_V241_STORAGE_EPOCH', 0) or 0) or globals().get('_V241_RESTORE_ACTIVE', False):
            with timer_lock:
                _quick_backup_dirty_chats.discard(chat_id)
            return

        def _job():
            if expected_epoch != int(globals().get('_V241_STORAGE_EPOCH', 0) or 0) or globals().get('_V241_RESTORE_ACTIVE', False):
                return
            if not durable_run_pending_delta_now_v234():
                schedule_delta_backup(None, delay=BACKUP_BUSY_RETRY_SECONDS, reason='quick_upload_retry')
        if not DELTA_TASK_POOL.submit('mega-delta-v90', _job):
            log_error(f'QUICK DELTA QUEUE FULL, RETRY: {chat_id}')
            schedule_quick_backup(chat_id, BACKUP_BUSY_RETRY_SECONDS)
    DELAYED_SCHEDULER.cancel('mega-delta-batch-v90')
    DELAYED_SCHEDULER.schedule('mega-delta-batch-v90', max(0.5, float(delay)), _fire)

def schedule_full_backup_only(chat_id: int, delay: float=3.0):
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

def schedule_backup_flush(chat_id: int, delay: float=3.0):
    """SQLite уже сохранена; delta быстро; тяжёлый файл чата — после экономичного idle debounce."""
    chat_id = int(chat_id)
    if RESTORE_GUARD_ACTIVE:
        log_error(f'BACKUP SCHEDULE BLOCKED {chat_id}: {RESTORE_GUARD_REASON}')
        return
    quick_delay = MEGA_DELTA_PRIORITY_DELAY_SECONDS if mega_backup_priority_enabled() else MEGA_DELTA_DELAY_SECONDS
    schedule_quick_backup(chat_id, quick_delay)
    schedule_full_backup_only(chat_id, delay)

def _safe_stabilize(action_name, func):
    try:
        return func()
    except Exception as e:
        log_error(f'[STABILIZE ERROR] {action_name}: {e}')
        try:
            bot_journal('stabilize_error', None, f'{action_name}: {e}', 'ERROR')
        except Exception:
            pass
        return None

def _v177_legacy_0237_finance_changed_now(chat_id: int, day_key: str | None=None, reason: str='change'):
    """
    Единая точка после фин-изменения.
    Важно: Telegram-отправки/редактирования окон и бэкапы не держат chat_lock,
    чтобы кнопки в этом же чате не висели «Загрузка».
    """
    chat_id = int(chat_id)
    day_key = day_key or get_chat_store(chat_id).get('current_view_day') or today_key()
    try:
        finance_cache_invalidate(chat_id, f'finance_changed:{reason}')
    except Exception:
        pass
    try:
        with locked_chat(chat_id):
            store = get_chat_store(chat_id)
            store['current_view_day'] = day_key
            _safe_stabilize('normalize_chat_records', lambda: normalize_chat_records(chat_id))
            _safe_stabilize('recalc_balance', lambda: recalc_balance(chat_id))
            _safe_stabilize('rebuild_month_short_ids', lambda: rebuild_month_short_ids(chat_id))
            _safe_stabilize('currency_ledger_snapshot', lambda: _snapshot_active_currency_ledger(store, _ensure_currency_ledgers(store)))
            _safe_stabilize('persist_finance_local_fast_v243', lambda: persist_finance_chat_local_fast(chat_id))
            hidden = is_finance_output_suppressed(chat_id)
            visible_window_mode = finance_window_mode(chat_id)
        _safe_stabilize('delta_queue_early', lambda: schedule_quick_backup(chat_id, MEGA_DELTA_PRIORITY_DELAY_SECONDS if mega_backup_priority_enabled() else MEGA_DELTA_DELAY_SECONDS))
        _safe_stabilize('finance_ui_fast_dispatch_v243', lambda: schedule_financial_window_refresh(chat_id, day_key, reason=f'finalize:{reason}', delay=0.01))
        _safe_stabilize('finance_postcommit_schedule_v243', lambda: schedule_finance_postcommit_background_v243(chat_id, reason=reason, delay=0.2))
    except Exception as e:
        raise

def _v177_legacy_0238_finance_changed(chat_id: int, day_key: str | None=None, reason: str='change', delay: float=0.35):
    """Debounced универсальный финальный пересчёт для одного чата."""
    chat_id = int(chat_id)
    bot_journal('finance_changed_scheduled', chat_id, f'day={day_key} reason={reason} delay={delay}')
    day_key = day_key or get_chat_store(chat_id).get('current_view_day') or today_key()

    def _job():
        if not FINANCE_TASK_POOL.submit(chat_id, _finance_changed_now, chat_id, day_key, reason):
            log_error(f'FINANCE QUEUE FULL, RETRY: {chat_id}')
            with timer_lock:
                _finalize_timers[chat_id] = time.time() + 1.0
            DELAYED_SCHEDULER.schedule(f'finance-finalize:{chat_id}', 1.0, _fire_finance)
    with timer_lock:
        _finalize_timers[chat_id] = time.time() + max(0.0, float(delay))

    def _fire_finance():
        with timer_lock:
            _finalize_timers.pop(chat_id, None)
        _job()
    DELAYED_SCHEDULER.schedule(f'finance-finalize:{chat_id}', delay, _fire_finance)

def _v177_legacy_0239_schedule_finalize(chat_id: int, day_key: str, delay: float=0.35):
    """Совместимость со старым кодом: теперь всё идёт через finance_changed()."""
    return finance_changed(chat_id, day_key, reason='schedule_finalize', delay=delay)

def _v177_legacy_0240_backup_window_for_owner(chat_id: int, day_key: str, message_id_override: int | None=None):
    """
    Окно дня для владельца без document-caption.
    JSON-бэкапы отправляются отдельно через schedule_backup_flush().
    """
    lock = window_locks[chat_id, day_key]
    with lock:
        txt, _ = render_day_window(chat_id, day_key)
        kb = build_main_keyboard(day_key, chat_id)
        if len(txt) > 3900:
            log_error(f'backup_window_for_owner: text too long for {chat_id} {day_key}, len={len(txt)}')
        mid = message_id_override or get_active_window_id(chat_id, day_key)
        if message_id_override:
            try:
                set_active_window_id(chat_id, day_key, message_id_override)
            except Exception:
                pass
        if mid:
            try:
                result = fast_ui_edit_message_text(chat_id, mid, txt, reply_markup=kb, parse_mode='HTML', purpose='main_day_background_v178')
            except Exception:
                result = 'failed'
            if str(result or '') in {'ok', 'scheduled'}:
                set_active_window_id(chat_id, day_key, mid)
                return result
            if str(result or '') == 'not_found':
                try:
                    aw = get_or_create_active_windows(chat_id)
                    if aw.get(day_key) == mid:
                        aw.pop(day_key, None)
                        save_data(data)
                except Exception:
                    pass
                try:
                    delete_async = globals().get('v177_delete_message_async')
                    if callable(delete_async):
                        delete_async(chat_id, mid, 'main_day_replace_v178')
                except Exception:
                    pass
            elif str(result or '') not in {'rate_limited', 'failed'}:
                return result
        sent = bot.send_message(chat_id, txt, reply_markup=kb, parse_mode='HTML')
        set_active_window_id(chat_id, day_key, sent.message_id)
try:
    _v177_legacy_0240_backup_window_for_owner.__name__ = 'backup_window_for_owner'
except Exception:
    pass

def cancel_auto_delete_for_message(chat_id: int, message_id: int):
    """Если окно с автоудалением превращается кнопкой «Назад» в основное — его старый таймер больше не должен удалить О1."""
    chat_id = int(chat_id)
    message_id = int(message_id)
    try:
        _cancel_v98_auto_close(chat_id, message_id)
    except Exception:
        pass
    for key in (f'auto-delete:{chat_id}:{message_id}', f'auto-delete-html:{chat_id}:{message_id}', f'delete-later:{chat_id}:{message_id}'):
        try:
            DELAYED_SCHEDULER.cancel(key)
        except Exception:
            pass
    try:
        store = get_chat_store(chat_id)
        was_total_window = int(store.get('total_msg_id') or 0) == message_id
        for timer_key in list(_aux_window_timers.keys()):
            try:
                timer_chat_id, store_key = timer_key
                if int(timer_chat_id) != chat_id:
                    continue
                if int(store.get(str(store_key)) or 0) != message_id:
                    continue
            except Exception:
                continue
            DELAYED_SCHEDULER.cancel(f'stored-window-delete:{chat_id}:{store_key}')
            _aux_window_timers.pop(timer_key, None)
            store[str(store_key)] = None
        if was_total_window:
            DELAYED_SCHEDULER.cancel(f'owner-total-delete:{chat_id}')
            _total_message_timers.pop(chat_id, None)
            store['total_msg_id'] = None
    except Exception as e:
        log_error(f'cancel_auto_delete_for_message({chat_id},{message_id}): {e}')

def recreate_main_window_now(chat_id: int, day_key: str):
    """Удаляет старое о1, если возможно, и создаёт новое основное окно."""
    try:
        old_mid = get_active_window_id(chat_id, day_key)
        if old_mid:
            try:
                bot.delete_message(chat_id, int(old_mid))
            except Exception:
                pass
            try:
                clear_active_window_id(chat_id, day_key)
            except Exception:
                pass
    except Exception:
        pass
    force_new_day_window(chat_id, day_key)

def _v177_legacy_0241_force_new_day_window(chat_id: int, day_key: str):
    txt, _ = render_day_window(chat_id, day_key)
    kb = build_main_keyboard(day_key, chat_id)
    sent = bot.send_message(chat_id, txt, reply_markup=kb, parse_mode='HTML')
    set_active_window_id(chat_id, day_key, sent.message_id)
    schedule_balance_panel_refresh(chat_id, 0.5)
try:
    _v177_legacy_0241_force_new_day_window.__name__ = 'force_new_day_window'
except Exception:
    pass

def _v177_legacy_0242_return_to_main_window_closing_previous(chat_id: int, day_key: str, current_message_id: int | None=None):
    """Return to О1 without promoting a missing/stale Telegram message to active."""
    chat_id = int(chat_id)
    try:
        current_message_id = int(current_message_id) if current_message_id is not None else None
    except Exception:
        current_message_id = None
    try:
        if current_message_id is not None:
            cancel_auto_delete_for_message(chat_id, current_message_id)
            cancel_fast_ui_edit(chat_id, current_message_id)
    except Exception:
        pass
    try:
        old_mid = get_active_window_id(chat_id, day_key)
        old_mid = int(old_mid) if old_mid else None
    except Exception:
        old_mid = None
    txt, _ = render_day_window(chat_id, day_key)
    kb = build_main_keyboard(day_key, chat_id)
    if current_message_id is not None:
        result = fast_ui_edit_message_text(chat_id, current_message_id, txt, reply_markup=kb, parse_mode='HTML', purpose='back_main_instant')
        bot_journal('back_main_fast', chat_id, f'day={day_key} result={result} old={old_mid} current={current_message_id}')
        if result == 'ok':
            set_active_window_id(chat_id, day_key, current_message_id)
            if old_mid and old_mid != current_message_id:

                def _delete_old():
                    try:
                        _tg_call_retry(bot.delete_message, chat_id, int(old_mid), attempts=1, purpose='back_main_delete_old')
                    except Exception:
                        pass
                    finally:
                        try:
                            unregister_open_window(chat_id, int(old_mid))
                        except Exception:
                            pass
                GENERAL_TASK_POOL.submit(f'back-delete:{chat_id}:{old_mid}', _delete_old)
            schedule_balance_panel_refresh(chat_id, 0.05)
            return
        if result == 'not_found':
            try:
                unregister_open_window(chat_id, current_message_id)
            except Exception:
                pass
            try:
                if get_active_window_id(chat_id, day_key) == current_message_id:
                    clear_active_window_id(chat_id, day_key)
                    old_mid = None
            except Exception:
                pass
        if old_mid and old_mid != current_message_id:

            def _refresh_existing():
                try:
                    backup_window_for_owner(chat_id, day_key, message_id_override=old_mid)
                except Exception as exc:
                    log_error(f'back_main preserve old({chat_id},{day_key},{old_mid}): {exc}')
            GENERAL_TASK_POOL.submit(f'back-preserve:{chat_id}:{old_mid}', _refresh_existing)
            return

    def _send_fallback():
        try:
            update_or_send_day_window(chat_id, day_key)
        except Exception as e:
            log_error(f'return_to_main fallback({chat_id},{day_key}): {e}')
    if not GENERAL_TASK_POOL.submit(f'back-send:{chat_id}', _send_fallback):
        _send_fallback()
try:
    _v177_legacy_0242_return_to_main_window_closing_previous.__name__ = 'return_to_main_window_closing_previous'
except Exception:
    pass

def reset_chat_data(chat_id: int):
    """v27: обнуление данных чата без ручного дублирования окон/бэкапов."""
    try:
        with locked_chat(chat_id):
            store = get_chat_store(chat_id)
            cleanup_forward_links(chat_id)
            store['balance'] = 0
            store['records'] = []
            store['daily_records'] = {}
            store['next_id'] = 1
            store['active_windows'] = {}
            clear_edit_wait_state(chat_id, delete_prompt=True)
            store['edit_target'] = None
            store['reset_wait'] = False
            store['reset_time'] = 0
            day_key = store.get('current_view_day', today_key())
            save_data(data)
        finance_changed(chat_id, day_key, reason='reset', delay=0.1)
    except Exception as e:
        log_error(f'reset_chat_data({chat_id}): {e}')

def handle_document(msg):
    global restore_mode, data
    chat_id = msg.chat.id
    update_chat_info_from_message(msg)
    if handle_secret_input_message(msg):
        return
    try:
        if not getattr(getattr(msg, 'from_user', None), 'is_bot', False):
            bump_quick_balance_recreate_counter(chat_id)
            stop_dozvon_for_target(chat_id)
    except Exception:
        pass
    file = msg.document
    fname = (file.file_name or '').lower()
    log_info(f'[DOC] recv chat={chat_id} restore={restore_mode} fname={fname}')
    if restore_mode is None and is_owner_chat(chat_id) and fname.endswith(('.json', '.ison')):
        if maybe_prompt_owner_for_json_restore(msg, fname):
            return
    if restore_mode is not None and restore_mode == chat_id:
        if not (fname.endswith('.json') or fname.endswith('.ison') or fname.endswith('.csv') or fname.endswith('.gz')):
            send_and_auto_delete(chat_id, '⚠️ В режиме восстановления принимаются GZ / JSON / ISON / CSV.')
            return
        if fname.endswith('.gz'):
            try:
                prep = globals().get('v182_prepare_gz_restore_document')
                if not callable(prep):
                    raise RuntimeError('GZ restore helper не загружен')
                prep(msg, file)
            except Exception as e:
                send_and_auto_delete(chat_id, f'❌ GZ не подготовлен: {e}', 15)
            return
        tmp_path = f'restore_{chat_id}_{fname}'
        try:
            file_info = bot.get_file(file.file_id)
            stream_fn = globals().get('telegram_download_to_file')
            if callable(stream_fn):
                max_restore = max(1024 * 1024, int(os.getenv('RESTORE_FILE_MAX_BYTES', str(100 * 1024 * 1024)) or str(100 * 1024 * 1024)))
                stream_fn(file_info.file_path, tmp_path, max_bytes=max_restore)
            else:
                raw = bot.download_file(file_info.file_path)
                with open(tmp_path, 'wb') as f:
                    f.write(raw)
                raw = None
        except Exception as e:
            try:
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)
            except Exception:
                pass
            send_and_auto_delete(chat_id, f'❌ Ошибка скачивания: {e}')
            return
        backup_dir = ''
        restore_epoch = 0
        restore_success = False
        try:
            begin_restore = globals().get('_v241_restore_storage_barrier_begin')
            if callable(begin_restore):
                restore_epoch = int(begin_restore() or 0)
            try:
                backup_fn = globals().get('_v153_backup_before_restore')
                if callable(backup_fn):
                    backup_dir = str(backup_fn() or '')
                    bot_journal('restore_pre_backup_ok_v240', chat_id, f'file={fname}')
                else:
                    bot_journal('restore_pre_backup_unavailable_v240', chat_id, f'file={fname}', 'WARN')
            except Exception as pre_exc:
                log_error(f'pre_restore best-effort before file restore: {pre_exc}')
                try:
                    bot_journal('restore_pre_backup_failed_v240', chat_id, str(pre_exc)[:400], 'WARN')
                except Exception:
                    pass
            if fname == 'csv_meta.json':
                os.replace(tmp_path, CSV_META_FILE)
                _save_csv_meta(_load_json(CSV_META_FILE, {}) or {})
                restore_mode = None
                data.pop('_restore_mode_chat_v150', None)
                save_data(data, chat_ids=[chat_id])
                _v240_restore_reanchor_guaranteed('csv_meta_restore_exact')
                restore_success = True
                send_and_auto_delete(chat_id, '🟢 csv_meta.json импортирован и точно закреплён в durable-хранилище')
                return
            if fname.endswith(('.json', '.ison')):
                payload = _load_json(tmp_path, None)
                if not isinstance(payload, dict):
                    raise RuntimeError('JSON/ISON не является объектом')
                uid = int(getattr(getattr(msg, 'from_user', None), 'id', 0) or 0)
                platform_owner = bool(uid and (uid == int(OWNER_ID or 0) or ('_v153_platform_owner' in globals() and _v153_platform_owner(uid))))
                if isinstance(payload.get('chats'), dict) or fname in {'data.json', 'data.ison'}:
                    result = restore_from_json(chat_id, tmp_path, actor_user_id=uid)
                    restore_mode = None
                    data.pop('_restore_mode_chat_v150', None)
                    _v240_restore_reanchor_guaranteed('global_json_restore_exact')
                    restore_success = True
                    send_and_auto_delete(chat_id, f"🟢 Полный JSON/ISON всего бота восстановлен и закреплён. Чатов: {result.get('chats', 0)}", 18)
                    return
                inner_chat_id = payload.get('chat_id')
                if inner_chat_id is None:
                    inner_chat_id = _extract_chat_id_from_json_filename(fname) if '_extract_chat_id_from_json_filename' in globals() else None
                if inner_chat_id is None:
                    raise RuntimeError('В JSON/ISON нет chat_id')
                target_chat_id = int(inner_chat_id)
                if target_chat_id != int(chat_id) and (not platform_owner):
                    allowed = False
                    try:
                        allowed = bool(_v153_can_manage_tenant(uid, _v153_tenant_for_chat(target_chat_id)) and _v153_tenant_for_chat(target_chat_id) == _v153_tenant_for_chat(chat_id))
                    except Exception:
                        allowed = False
                    if not allowed:
                        raise RuntimeError(f'Файл относится к чату {target_chat_id}; нет прав восстановить его из текущего контура')
                result = restore_from_json(target_chat_id, tmp_path, actor_user_id=uid)
                restore_mode = None
                data.pop('_restore_mode_chat_v150', None)
                _v240_restore_reanchor_guaranteed(f'chat_json_restore_exact:{target_chat_id}')
                restore_success = True
                settings_count = int((result.get('settings') or {}).get('settings_keys') or 0)
                send_and_auto_delete(chat_id, f"🟢 JSON/ISON восстановлен СТРОГО ИЗ ФАЙЛА: {get_chat_display_name(target_chat_id)}\nЗаписей в файле: {result.get('backup_records', 0)}\nЗаписей после restore: {result.get('records_after', 0)}\nПредыдущее live-состояние заменено: {result.get('replaced_live_records', 0)} записей\nВосстановлено настроек: {settings_count}\nНичего из текущего состояния не подмешивалось.", 22)
                return
            if fname.startswith('data_') and fname.endswith('.csv'):
                restore_from_csv(chat_id, tmp_path)
                day_key = get_chat_store(chat_id).get('current_view_day', today_key())
                finance_changed(chat_id, day_key, reason='restore_csv', delay=0.1)
                restore_mode = None
                data.pop('_restore_mode_chat_v150', None)
                save_data(data, chat_ids=[chat_id])
                _v240_restore_reanchor_guaranteed(f'chat_csv_restore_exact:{chat_id}')
                restore_success = True
                send_and_auto_delete(chat_id, f'🟢 CSV чата восстановлен и точно закреплён ({fname})')
                return
            send_and_auto_delete(chat_id, f'⚠️ Неизвестный файл: {fname}')
        except Exception as e:
            send_and_auto_delete(chat_id, f'❌ Ошибка восстановления: {e}')
        finally:
            if restore_epoch:
                end_restore = globals().get('_v241_restore_storage_barrier_end')
                if callable(end_restore):
                    try:
                        end_restore(restore_epoch, restore_success)
                    except Exception:
                        pass
            try:
                os.remove(tmp_path)
            except Exception:
                pass
            try:
                if backup_dir:
                    shutil.rmtree(backup_dir, ignore_errors=True)
            except Exception:
                pass
        return
    try:
        schedule_forward_any_message(chat_id, msg)
    except Exception as e:
        log_error(f'handle_document forward failed: {e}')

def cleanup_forward_links(chat_id: int):
    """
    Удаляет все связи пересылки для чата из памяти и из сохранённого индекса.
    """
    _cleanup_forward_storage_for_chat(chat_id)
KEEP_ALIVE_SEND_TO_OWNER = False
KEEPALIVE_CONFIG_KEY = 'keepalive_v205'
KEEPALIVE_SAFE_INTERVALS = (300, 480, 600, 720, 840)
KEEPALIVE_AUTO_SAFE_IDLE_SECONDS = (600, 660, 720, 780, 840)
KEEPALIVE_AUTO_DEFAULT_IDLE_SECONDS = 720
KEEPALIVE_MIN_SECONDS = 60
KEEPALIVE_MAX_SECONDS = 3600
KEEP_ALIVE_STATE = {'started_at': None, 'last_attempt_at': None, 'last_ok_at': None, 'last_error': '', 'last_status_code': None, 'ok_count': 0, 'fail_count': 0, 'self_ping_at': None, 'external_ping_at': None, 'external_monitor_at': None, 'peer_received_at': None, 'last_keepalive_user_agent': '', 'last_inbound_activity_at': None, 'last_inbound_activity_kind': '', 'auto_last_trigger_at': None, 'auto_last_reason': '', 'auto_trigger_count': 0, 'peer_started_at': None, 'peer_last_attempt_at': None, 'peer_last_ok_at': None, 'peer_last_error': '', 'peer_last_status_code': None, 'peer_ok_count': 0, 'peer_fail_count': 0}
_keep_alive_thread = None
_peer_keep_alive_thread = None
_keep_alive_thread_lock = threading.RLock()
_keep_alive_wakeup = threading.Event()
_peer_keep_alive_wakeup = threading.Event()
_KEEPALIVE_INPUT_LOCK = threading.RLock()
_KEEPALIVE_INPUT_WAIT = {}
_KEEPALIVE_RUNTIME_STARTED_MONO = time.monotonic()
_KEEPALIVE_LAST_EXTERNAL_MONO = _KEEPALIVE_RUNTIME_STARTED_MONO
_KEEPALIVE_AUTO_LAST_PING_MONO = 0.0
_KEEPALIVE_ACTIVITY_LOCK = threading.RLock()
_PEER_FAIL_LOG_LOCK_V238 = threading.RLock()
_PEER_FAIL_LAST_KEY_V238 = ''
_PEER_FAIL_LAST_LOG_MONO_V238 = 0.0
_PEER_FAIL_LOG_COOLDOWN_V238 = 1800.0

def _keepalive_env_bool(name: str, default: bool=False) -> bool:
    raw = str(os.getenv(name, '1' if default else '0') or '').strip().lower()
    return raw in {'1', 'true', 'yes', 'y', 'on', 'да'}

def _keepalive_clamp_interval(value, default: int=600) -> int:
    try:
        return max(KEEPALIVE_MIN_SECONDS, min(KEEPALIVE_MAX_SECONDS, int(value)))
    except Exception:
        return int(default)

def _keepalive_root(create: bool=True) -> dict:
    try:
        gs = data.setdefault('_global_settings', {}) if create else data.get('_global_settings') or {}
    except Exception:
        return {}
    root = gs.get(KEEPALIVE_CONFIG_KEY)
    if not isinstance(root, dict):
        if not create:
            return {}
        root = {}
        gs[KEEPALIVE_CONFIG_KEY] = root
    root['schema'] = 2
    root.setdefault('self_enabled', bool(KEEP_ALIVE_ENABLED))
    root.setdefault('self_interval_seconds', int(KEEP_ALIVE_INTERVAL_SECONDS))
    root.setdefault('auto_enabled', _keepalive_env_bool('KEEP_ALIVE_AUTO_ENABLED', True))
    root.setdefault('auto_idle_seconds', _keepalive_clamp_interval(os.getenv('KEEP_ALIVE_AUTO_IDLE_SECONDS', str(KEEPALIVE_AUTO_DEFAULT_IDLE_SECONDS)), KEEPALIVE_AUTO_DEFAULT_IDLE_SECONDS))
    root.setdefault('peer_enabled', _keepalive_env_bool('PEER_KEEPALIVE_ENABLED', False))
    root.setdefault('peer_interval_seconds', _keepalive_clamp_interval(os.getenv('PEER_KEEPALIVE_INTERVAL_SECONDS', '600'), 600))
    root.setdefault('peer_url', str(os.getenv('PEER_KEEPALIVE_URL', '') or '').strip())
    root.setdefault('updated_at', '')
    return root

def _keepalive_persist(reason: str='settings') -> None:
    root = _keepalive_root(True)
    try:
        root['updated_at'] = now_local().isoformat(timespec='seconds')
    except Exception:
        root['updated_at'] = _journal_ts()
    try:
        save_data(data, root_only=True)
    except TypeError:
        save_data(data)
    except Exception as exc:
        try:
            log_error(f'keepalive save: {exc}')
        except Exception:
            pass
    try:
        fn = globals().get('schedule_delta_backup')
        if callable(fn):
            fn(None, delay=0.8, reason=f'keepalive:{str(reason)[:80]}')
    except Exception:
        pass
    try:
        bot_journal('keepalive_setting', int(OWNER_ID or 0) or None, str(reason)[:300])
    except Exception:
        pass

def keepalive_self_enabled() -> bool:
    gate = globals().get('external_access_allowed_v233')
    if callable(gate) and (not gate('self_http')):
        return False
    return bool(_keepalive_root(True).get('self_enabled', bool(KEEP_ALIVE_ENABLED)))

def keepalive_self_interval_seconds() -> int:
    root = _keepalive_root(True)
    value = _keepalive_clamp_interval(root.get('self_interval_seconds', KEEP_ALIVE_INTERVAL_SECONDS), int(KEEP_ALIVE_INTERVAL_SECONDS))
    root['self_interval_seconds'] = value
    return value

def set_keepalive_self_enabled(enabled: bool, persist: bool=True) -> bool:
    enabled = bool(enabled)
    _keepalive_root(True)['self_enabled'] = enabled
    globals()['KEEP_ALIVE_ENABLED'] = enabled
    _keep_alive_wakeup.set()
    if persist:
        _keepalive_persist(f'self_enabled={int(enabled)}')
    return enabled

def set_keepalive_self_interval(seconds: int, persist: bool=True) -> int:
    value = _keepalive_clamp_interval(seconds, 600)
    _keepalive_root(True)['self_interval_seconds'] = value
    globals()['KEEP_ALIVE_INTERVAL_SECONDS'] = value
    _keep_alive_wakeup.set()
    if persist:
        _keepalive_persist(f'self_interval={value}')
    return value

def keepalive_auto_enabled() -> bool:
    gate = globals().get('external_access_allowed_v233')
    if callable(gate) and (not gate('self_http')):
        return False
    return bool(_keepalive_root(True).get('auto_enabled', True))

def keepalive_auto_idle_seconds() -> int:
    root = _keepalive_root(True)
    value = _keepalive_clamp_interval(root.get('auto_idle_seconds', KEEPALIVE_AUTO_DEFAULT_IDLE_SECONDS), KEEPALIVE_AUTO_DEFAULT_IDLE_SECONDS)
    value = max(300, min(840, int(value)))
    root['auto_idle_seconds'] = value
    return value

def set_keepalive_auto_enabled(enabled: bool, persist: bool=True) -> bool:
    enabled = bool(enabled)
    _keepalive_root(True)['auto_enabled'] = enabled
    _keep_alive_wakeup.set()
    if persist:
        _keepalive_persist(f'auto_enabled={int(enabled)}')
    return enabled

def set_keepalive_auto_idle_seconds(seconds: int, persist: bool=True) -> int:
    value = max(300, min(840, _keepalive_clamp_interval(seconds, KEEPALIVE_AUTO_DEFAULT_IDLE_SECONDS)))
    _keepalive_root(True)['auto_idle_seconds'] = value
    _keep_alive_wakeup.set()
    if persist:
        _keepalive_persist(f'auto_idle={value}')
    return value

def keepalive_note_inbound_activity(kind: str='external') -> None:
    """Record real inbound traffic that can keep Render awake.

    Self-ping is deliberately NOT recorded here. Telegram/web/user/peer traffic
    postpones the automatic fallback. Render local health checks are not routed here.
    """
    global _KEEPALIVE_LAST_EXTERNAL_MONO
    now_m = time.monotonic()
    with _KEEPALIVE_ACTIVITY_LOCK:
        _KEEPALIVE_LAST_EXTERNAL_MONO = now_m
        KEEP_ALIVE_STATE['last_inbound_activity_at'] = _journal_ts()
        KEEP_ALIVE_STATE['last_inbound_activity_kind'] = str(kind or 'external')[:80]
    _keep_alive_wakeup.set()

def keepalive_auto_runtime_state(now_m: float | None=None) -> dict:
    now_m = float(time.monotonic() if now_m is None else now_m)
    threshold = keepalive_auto_idle_seconds()
    with _KEEPALIVE_ACTIVITY_LOCK:
        external_m = float(_KEEPALIVE_LAST_EXTERNAL_MONO or _KEEPALIVE_RUNTIME_STARTED_MONO)
        auto_m = float(_KEEPALIVE_AUTO_LAST_PING_MONO or 0.0)
    basis = max(float(_KEEPALIVE_RUNTIME_STARTED_MONO), external_m, auto_m)
    idle = max(0.0, now_m - basis)
    due_in = max(0.0, float(threshold) - idle)
    manual = keepalive_self_enabled()
    auto = keepalive_auto_enabled()
    if not auto:
        mode = 'disabled'
    elif manual:
        mode = 'standby_manual'
    elif due_in <= 0.0:
        mode = 'due'
    else:
        kind = str(KEEP_ALIVE_STATE.get('last_inbound_activity_kind') or '')
        mode = 'standby_peer' if kind == 'peer_watchdog' else 'standby_external'
    return {'enabled': auto, 'manual': manual, 'threshold': threshold, 'idle_seconds': idle, 'due_in_seconds': due_in, 'mode': mode}

def keepalive_peer_enabled() -> bool:
    gate = globals().get('external_access_allowed_v233')
    if callable(gate) and (not gate('peer_http')):
        return False
    return bool(_keepalive_root(True).get('peer_enabled', False))

def keepalive_peer_interval_seconds() -> int:
    root = _keepalive_root(True)
    value = _keepalive_clamp_interval(root.get('peer_interval_seconds', 600), 600)
    root['peer_interval_seconds'] = value
    return value

def keepalive_peer_target_url() -> str:
    raw = str(_keepalive_root(True).get('peer_url') or os.getenv('PEER_KEEPALIVE_URL', '') or '').strip()
    if not raw:
        return ''
    if not raw.lower().startswith(('http://', 'https://')):
        raw = 'https://' + raw
    try:
        parsed = urllib.parse.urlsplit(raw)
        if not parsed.hostname:
            return ''
        return urllib.parse.urlunsplit((parsed.scheme or 'https', parsed.netloc, parsed.path.rstrip('/'), '', '')).rstrip('/')
    except Exception:
        return ''

def set_keepalive_peer_enabled(enabled: bool, persist: bool=True) -> bool:
    enabled = bool(enabled)
    _keepalive_root(True)['peer_enabled'] = enabled
    _peer_keep_alive_wakeup.set()
    if persist:
        _keepalive_persist(f'peer_enabled={int(enabled)}')
    return enabled

def set_keepalive_peer_interval(seconds: int, persist: bool=True) -> int:
    value = _keepalive_clamp_interval(seconds, 600)
    _keepalive_root(True)['peer_interval_seconds'] = value
    _peer_keep_alive_wakeup.set()
    if persist:
        _keepalive_persist(f'peer_interval={value}')
    return value

def set_keepalive_peer_url(raw_url: str, persist: bool=True) -> str:
    raw = str(raw_url or '').strip()
    if raw.casefold() in {'-', 'нет', 'off', 'clear', 'очистить'}:
        raw = ''
    if raw and (not raw.lower().startswith(('http://', 'https://'))):
        raw = 'https://' + raw
    if raw:
        parsed = urllib.parse.urlsplit(raw)
        if (parsed.scheme or '').lower() not in {'http', 'https'} or not parsed.hostname:
            raise ValueError('Нужен адрес вида https://имя-сервиса.onrender.com')
        raw = urllib.parse.urlunsplit((parsed.scheme.lower(), parsed.netloc, parsed.path.rstrip('/'), '', '')).rstrip('/')
    _keepalive_root(True)['peer_url'] = raw
    _peer_keep_alive_wakeup.set()
    if persist:
        _keepalive_persist('peer_url_changed' if raw else 'peer_url_cleared')
    return raw

def _keep_alive_base_candidates() -> list[str]:
    result = []
    extra = os.getenv('KEEP_ALIVE_URLS', '')
    values = [APP_URL, WEBHOOK_URL, os.getenv('RENDER_EXTERNAL_URL', '').strip(), _RENDER_HOST_URL]
    if extra:
        values.extend((x.strip() for x in extra.split(',')))
    for raw in values:
        if not raw:
            continue
        base = str(raw).strip().rstrip('/')
        if base and base not in result:
            result.append(base)
    return result

def _keepalive_wire_user_agent_v250(kind: str='keepalive') -> str:
    """Return an ASCII-only User-Agent for requests/urllib3/http.client.

    Python's HTTP stack encodes header values as latin-1. VERSION is intentionally
    user-facing Cyrillic (for example ``выс-260``), so it must never be placed
    directly into an outgoing HTTP header.
    """
    try:
        number = int(globals().get('RELEASE_NUMBER') or 249)
    except Exception:
        number = 249
    safe_kind = re.sub(r'[^A-Za-z0-9._-]+', '-', str(kind or 'keepalive')).strip('-') or 'keepalive'
    return f'vys-{number}-{safe_kind}'[:180]

def _keepalive_ping_url(session, base_url: str, user_agent: str) -> tuple[bool, int | None, str]:
    """One very small HEAD probe; GET only as a compatibility fallback."""
    base = str(base_url or '').strip().rstrip('/')
    if not base:
        return (False, None, 'URL не задан')
    try:
        parsed = urllib.parse.urlsplit(base)
        path = parsed.path.rstrip('/')
        if path.endswith('/keepalive') or path.endswith('/healthz'):
            url = base
        else:
            url = base + '/keepalive'
    except Exception:
        url = base + '/keepalive'
    try:
        wire_user_agent = str(user_agent or '').encode('ascii', 'strict').decode('ascii')[:180]
    except Exception:
        wire_user_agent = _keepalive_wire_user_agent_v250('keepalive')
    headers = {'Cache-Control': 'no-cache', 'User-Agent': wire_user_agent}
    try:
        resp = session.head(url, timeout=12, headers=headers, allow_redirects=True)
        code = int(resp.status_code)
        if 200 <= code < 500:
            return (True, code, '')
        resp = session.get(url, timeout=12, headers=headers, allow_redirects=True)
        code = int(resp.status_code)
        if 200 <= code < 500:
            return (True, code, '')
        return (False, code, f'HTTP {code} {url}')
    except Exception as exc:
        return (False, None, f'{url}: {exc}')

def keepalive_ping_self_once() -> tuple[bool, str]:
    KEEP_ALIVE_STATE['last_attempt_at'] = _journal_ts()
    bases = _keep_alive_base_candidates()
    if not bases:
        KEEP_ALIVE_STATE['last_error'] = 'APP_URL / WEBHOOK_URL / RENDER URL не заданы'
        KEEP_ALIVE_STATE['fail_count'] = int(KEEP_ALIVE_STATE.get('fail_count', 0)) + 1
        return (False, KEEP_ALIVE_STATE['last_error'])
    session = requests.Session()
    last_error = ''
    last_code = None
    for base in bases:
        ok, code, err = _keepalive_ping_url(session, base, _keepalive_wire_user_agent_v250('keepalive'))
        last_code = code
        if ok:
            KEEP_ALIVE_STATE['last_status_code'] = code
            KEEP_ALIVE_STATE['last_ok_at'] = _journal_ts()
            KEEP_ALIVE_STATE['self_ping_at'] = KEEP_ALIVE_STATE['last_ok_at']
            KEEP_ALIVE_STATE['last_error'] = ''
            KEEP_ALIVE_STATE['ok_count'] = int(KEEP_ALIVE_STATE.get('ok_count', 0)) + 1
            return (True, f'HTTP {code}')
        last_error = err
    KEEP_ALIVE_STATE['last_status_code'] = last_code
    KEEP_ALIVE_STATE['last_error'] = last_error or 'self-ping failed'
    KEEP_ALIVE_STATE['fail_count'] = int(KEEP_ALIVE_STATE.get('fail_count', 0)) + 1
    return (False, KEEP_ALIVE_STATE['last_error'])

def keepalive_ping_peer_once() -> tuple[bool, str]:
    target = keepalive_peer_target_url()
    KEEP_ALIVE_STATE['peer_last_attempt_at'] = _journal_ts()
    if not target:
        KEEP_ALIVE_STATE['peer_last_error'] = 'Адрес второго сервиса не задан'
        KEEP_ALIVE_STATE['peer_fail_count'] = int(KEEP_ALIVE_STATE.get('peer_fail_count', 0)) + 1
        return (False, KEEP_ALIVE_STATE['peer_last_error'])
    ok, code, err = _keepalive_ping_url(requests.Session(), target, _keepalive_wire_user_agent_v250('peer-keepalive'))
    KEEP_ALIVE_STATE['peer_last_status_code'] = code
    if ok:
        KEEP_ALIVE_STATE['peer_last_ok_at'] = _journal_ts()
        KEEP_ALIVE_STATE['peer_last_error'] = ''
        KEEP_ALIVE_STATE['peer_ok_count'] = int(KEEP_ALIVE_STATE.get('peer_ok_count', 0)) + 1
        return (True, f'HTTP {code}')
    KEEP_ALIVE_STATE['peer_last_error'] = err or 'peer ping failed'
    KEEP_ALIVE_STATE['peer_fail_count'] = int(KEEP_ALIVE_STATE.get('peer_fail_count', 0)) + 1
    return (False, KEEP_ALIVE_STATE['peer_last_error'])

def keep_alive_task():
    """Manual self-ping plus automatic fail-safe before Render's idle spin-down.

    Manual mode remains exactly user-controlled. Auto mode is a dormant safety net:
    if real inbound traffic (especially peer watchdog) is arriving, it sends nothing.
    If inbound traffic disappears, one small self HEAD is sent before the 15-minute
    Render idle boundary and repeated only while the outage/inactivity continues.
    """
    global _KEEPALIVE_AUTO_LAST_PING_MONO
    cycle = 0
    KEEP_ALIVE_STATE['started_at'] = _journal_ts()
    manual_next_m = time.monotonic()
    while True:
        timeout = 30.0
        try:
            now_m = time.monotonic()
            manual_on = keepalive_self_enabled()
            auto_on = keepalive_auto_enabled()
            if manual_on:
                if now_m >= manual_next_m:
                    ok, detail = keepalive_ping_self_once()
                    cycle += 1
                    if not ok:
                        log_error(f'Keep-alive failed: {detail}')
                    elif cycle == 1 or cycle % 12 == 0:
                        log_info(f'Keep-alive OK: {detail}; interval={keepalive_self_interval_seconds()}s')
                    manual_next_m = time.monotonic() + float(keepalive_self_interval_seconds())
                timeout = max(5.0, min(30.0, manual_next_m - time.monotonic()))
            elif auto_on:
                auto_state = keepalive_auto_runtime_state(now_m)
                due_in = float(auto_state.get('due_in_seconds') or 0.0)
                if due_in <= 0.0:
                    kind = str(KEEP_ALIVE_STATE.get('last_inbound_activity_kind') or 'нет')
                    idle_sec = int(round(float(auto_state.get('idle_seconds') or 0.0)))
                    ok, detail = keepalive_ping_self_once()
                    if ok:
                        _KEEPALIVE_AUTO_LAST_PING_MONO = time.monotonic()
                        KEEP_ALIVE_STATE['auto_last_trigger_at'] = _journal_ts()
                        KEEP_ALIVE_STATE['auto_last_reason'] = f'нет внешнего запроса {idle_sec} сек; последний источник={kind}'[:300]
                        KEEP_ALIVE_STATE['auto_trigger_count'] = int(KEEP_ALIVE_STATE.get('auto_trigger_count', 0)) + 1
                        log_info(f'Auto keep-alive fallback OK: {detail}; idle={idle_sec}s; source={kind}')
                    else:
                        log_error(f'Auto keep-alive fallback failed: {detail}')
                    timeout = 30.0
                else:
                    timeout = max(5.0, min(30.0, due_in))
            else:
                timeout = 30.0
        except Exception as exc:
            KEEP_ALIVE_STATE['last_error'] = str(exc)[:500]
            KEEP_ALIVE_STATE['fail_count'] = int(KEEP_ALIVE_STATE.get('fail_count', 0)) + 1
            try:
                log_error(f'Keep-alive loop error: {exc}')
            except Exception:
                pass
            timeout = 30.0
        _keep_alive_wakeup.wait(max(5.0, float(timeout)))
        _keep_alive_wakeup.clear()

def peer_keep_alive_task():
    global _PEER_FAIL_LAST_KEY_V238, _PEER_FAIL_LAST_LOG_MONO_V238
    KEEP_ALIVE_STATE['peer_started_at'] = _journal_ts()
    while True:
        try:
            if keepalive_peer_enabled():
                ok, detail = keepalive_ping_peer_once()
                if not ok:
                    now_m = time.monotonic()
                    key = str(detail or 'peer unavailable')[:300]
                    with _PEER_FAIL_LOG_LOCK_V238:
                        should_log = key != _PEER_FAIL_LAST_KEY_V238 or now_m - _PEER_FAIL_LAST_LOG_MONO_V238 >= _PEER_FAIL_LOG_COOLDOWN_V238
                        if should_log:
                            _PEER_FAIL_LAST_KEY_V238 = key
                            _PEER_FAIL_LAST_LOG_MONO_V238 = now_m
                    if should_log:
                        try:
                            bot_journal('peer_keepalive_unavailable_v238', None, key, 'WARN')
                        except Exception:
                            pass
                else:
                    with _PEER_FAIL_LOG_LOCK_V238:
                        _PEER_FAIL_LAST_KEY_V238 = ''
                        _PEER_FAIL_LAST_LOG_MONO_V238 = 0.0
                timeout = keepalive_peer_interval_seconds()
            else:
                timeout = 30
        except Exception as exc:
            KEEP_ALIVE_STATE['peer_last_error'] = str(exc)[:500]
            KEEP_ALIVE_STATE['peer_fail_count'] = int(KEEP_ALIVE_STATE.get('peer_fail_count', 0)) + 1
            try:
                bot_journal('peer_keepalive_loop_error_v238', None, str(exc)[:300], 'WARN')
            except Exception:
                pass
            timeout = 30
        _peer_keep_alive_wakeup.wait(max(5.0, float(timeout)))
        _peer_keep_alive_wakeup.clear()

def _canon_keepalive_begin_peer_url_input__001(chat_id: int, panel_message_id: int) -> None:
    with _KEEPALIVE_INPUT_LOCK:
        _KEEPALIVE_INPUT_WAIT[int(chat_id)] = {'kind': 'peer_url', 'panel_message_id': int(panel_message_id or 0), 'started_at': time.time()}

def _canon_keepalive_cancel_input__001(chat_id: int) -> None:
    with _KEEPALIVE_INPUT_LOCK:
        _KEEPALIVE_INPUT_WAIT.pop(int(chat_id), None)

def keepalive_handle_message(msg) -> bool:
    """Consume owner-only peer-URL input before finance/forward parsing."""
    try:
        if str(getattr(msg, 'content_type', '') or '') != 'text':
            return False
        cid = int(msg.chat.id)
        uid = int(getattr(getattr(msg, 'from_user', None), 'id', 0) or 0)
        if not int(OWNER_ID or 0) or cid != int(OWNER_ID) or uid != int(OWNER_ID):
            return False
        with _KEEPALIVE_INPUT_LOCK:
            wait = dict(_KEEPALIVE_INPUT_WAIT.get(cid) or {})
        if not wait or wait.get('kind') != 'peer_url':
            return False
        if time.time() - float(wait.get('started_at') or 0) > 900:
            keepalive_cancel_input(cid)
            return False
        text = str(getattr(msg, 'text', '') or '').strip()
        try:
            set_keepalive_peer_url(text, persist=True)
            keepalive_cancel_input(cid)
            panel = int(wait.get('panel_message_id') or 0)
            if panel:
                fn_text = globals().get('keepalive_peer_status_text')
                fn_kb = globals().get('build_keepalive_peer_keyboard')
                if callable(fn_text) and callable(fn_kb):
                    fast_ui_edit_message_text(cid, panel, fn_text(), reply_markup=fn_kb(cid), purpose='keepalive_peer_url_saved')
            try:
                bot.delete_message(cid, int(msg.message_id))
            except Exception:
                pass
        except Exception as exc:
            send_and_auto_delete(cid, f'❌ Адрес не сохранён: {exc}', 15)
        return True
    except Exception as exc:
        try:
            log_error(f'keepalive input: {exc}')
        except Exception:
            pass
        return True

@bot.channel_post_handler(content_types=['text', 'photo', 'video', 'animation', 'audio', 'voice', 'video_note', 'document', 'sticker', 'location', 'venue', 'contact', 'dice', 'poll', 'game', 'story', 'paid_media', 'invoice'])
def on_any_channel_post(msg):
    try:
        update_chat_info_from_message(msg)
    except Exception as e:
        log_error(f'channel_post update_chat_info failed: {e}')
    if handle_secret_sequence(msg):
        return
    if handle_secret_input_message(msg):
        return
    try:
        bump_quick_balance_recreate_counter(msg.chat.id)
    except Exception:
        pass
    try:
        stop_dozvon_for_target(msg.chat.id)
    except Exception:
        pass
    try:
        if is_finance_mode(msg.chat.id):
            handle_finance_text(msg)
    except Exception as e:
        log_error(f'channel_post finance failed: {e}')
    try:
        _task_reconcile = globals().get('task_reconcile_source_message')
        if callable(_task_reconcile):
            _sender = getattr(msg, 'from_user', None)
            _task_reconcile(int(msg.chat.id), int(getattr(msg, 'message_id', 0) or 0), str(getattr(msg, 'text', None) or getattr(msg, 'caption', None) or ''), original_date=getattr(msg, 'date', None), sender_id=int(getattr(_sender, 'id', 0) or 0), sender_name=str(getattr(_sender, 'first_name', '') or getattr(_sender, 'username', '') or ''), sender_is_bot=bool(getattr(_sender, 'is_bot', False)) if _sender else False, trusted_forwarding_copy=False, is_edit=False, content_type=str(getattr(msg, 'content_type', '') or 'text'))
    except Exception as _task_exc:
        try:
            log_error(f'v212 task source reconcile handler: {_task_exc}')
        except Exception:
            pass
    try:
        schedule_forward_any_message(msg.chat.id, msg)
    except Exception as e:
        log_error(f'channel_post forward schedule failed: {e}')

@bot.edited_channel_post_handler(content_types=['text', 'photo', 'video', 'animation', 'audio', 'voice', 'video_note', 'document', 'sticker', 'location', 'venue', 'contact', 'dice', 'poll'])
def on_edited_channel_post(msg):
    try:
        update_chat_info_from_message(msg)
    except Exception as e:
        log_error(f'edited_channel_post update_chat_info failed: {e}')
    if handle_secret_edited_message(msg):
        return
    try:
        if is_finance_mode(msg.chat.id):
            handle_finance_edit(msg)
    except Exception as e:
        log_error(f'edited_channel_post finance edit failed: {e}')
    try:
        _task_reconcile = globals().get('task_reconcile_source_message')
        if callable(_task_reconcile):
            _sender = getattr(msg, 'from_user', None)
            _task_reconcile(int(msg.chat.id), int(getattr(msg, 'message_id', 0) or 0), str(getattr(msg, 'text', None) or getattr(msg, 'caption', None) or ''), original_date=getattr(msg, 'date', None), sender_id=int(getattr(_sender, 'id', 0) or 0), sender_name=str(getattr(_sender, 'first_name', '') or getattr(_sender, 'username', '') or ''), sender_is_bot=bool(getattr(_sender, 'is_bot', False)) if _sender else False, trusted_forwarding_copy=False, is_edit=True, content_type=str(getattr(msg, 'content_type', '') or 'text'))
    except Exception as _task_exc:
        try:
            log_error(f'v212 task source reconcile handler: {_task_exc}')
        except Exception:
            pass
    try:
        schedule_propagate_edited_to_copies(msg)
    except Exception as e:
        log_error(f'edited_channel_post propagate schedule failed: {e}')

def propagate_edited_to_copies(msg):
    source_chat_id = msg.chat.id
    text = _message_text_for_finance(msg)
    links = get_forward_links(source_chat_id, msg.message_id)
    if not links:
        return
    links = sorted(list(links), key=lambda pair: 0 if get_forward_finance(source_chat_id, int(pair[0])) else 1)
    for dst_chat_id, dst_msg_id in links:
        try:
            finance_enabled = get_forward_finance(source_chat_id, dst_chat_id)
            sync_edited_copy_to_target(source_chat_id, msg, dst_chat_id, dst_msg_id, finance_enabled)
        except Exception as e:
            log_error(f'propagate_edited_to_copies failed {dst_chat_id}:{dst_msg_id}: {e}')

@bot.edited_message_handler(content_types=['text', 'photo', 'video', 'animation', 'document', 'audio', 'voice'])
def on_edited_message(msg):
    chat_id = msg.chat.id
    try:
        bot_journal('edited_message_received', chat_id, f"msg={getattr(msg, 'message_id', 0)}")
    except Exception:
        pass
    try:
        update_chat_info_from_message(msg)
    except Exception:
        pass
    if handle_secret_edited_message(msg):
        return
    edit_text = _message_text_for_finance(msg)
    if is_forward_delete_command(edit_text):
        try:
            schedule_delete_forward_copies_for_source(chat_id, msg.message_id)
        except Exception as e:
            log_error(f'[EDIT-DEL] schedule failed: {e}')
    try:
        edited = handle_finance_edit(msg)
        if edited:
            store = get_chat_store(chat_id)
            day_key = store.get('current_view_day') or today_key()
            log_info(f'[EDIT-FIN] finalize day_key={day_key}')
            schedule_finalize(chat_id, day_key)
    except Exception as e:
        log_error(f'[EDIT-FIN] failed: {e}')
    try:
        _task_reconcile = globals().get('task_reconcile_source_message')
        if callable(_task_reconcile):
            _sender = getattr(msg, 'from_user', None)
            _task_reconcile(int(msg.chat.id), int(getattr(msg, 'message_id', 0) or 0), str(getattr(msg, 'text', None) or getattr(msg, 'caption', None) or ''), original_date=getattr(msg, 'date', None), sender_id=int(getattr(_sender, 'id', 0) or 0), sender_name=str(getattr(_sender, 'first_name', '') or getattr(_sender, 'username', '') or ''), sender_is_bot=bool(getattr(_sender, 'is_bot', False)) if _sender else False, trusted_forwarding_copy=False, is_edit=True, content_type=str(getattr(msg, 'content_type', '') or 'text'))
    except Exception as _task_exc:
        try:
            log_error(f'v212 task source reconcile handler: {_task_exc}')
        except Exception:
            pass
    try:
        if not is_forward_delete_command(edit_text):
            schedule_propagate_edited_to_copies(msg)
    except Exception as e:
        log_error(f'[EDIT-FWD] schedule failed: {e}')

@bot.message_handler(commands=['buttons'])
def cmd_buttons(msg):
    try:
        update_chat_info_from_message(msg)
    except Exception:
        pass
    schedule_command_delete(msg)
    chat_id = msg.chat.id
    if not is_owner_chat(chat_id):
        return
    new_state = toggle_icon_button_mode(chat_id)
    send_and_auto_delete(chat_id, f"✅ Кнопки переключены: {('значки' if new_state else 'текст')}", 30)
    try:
        refresh_registered_financial_windows(chat_id)
    except Exception:
        pass

@bot.message_handler(commands=['restore_guard'])
def cmd_restore_guard(msg):
    try:
        update_chat_info_from_message(msg)
    except Exception:
        pass
    schedule_command_delete(msg)
    chat_id = msg.chat.id
    if 'tenant_require_platform_owner' in globals():
        if not tenant_require_platform_owner(msg):
            return
    elif not is_owner_chat(chat_id if 'chat_id' in locals() else msg.chat.id):
        return
    send_and_auto_delete(chat_id, restore_guard_status_text(), 120)

@bot.message_handler(commands=['restore_guard_off'])
def cmd_restore_guard_off(msg):
    try:
        update_chat_info_from_message(msg)
    except Exception:
        pass
    schedule_command_delete(msg)
    chat_id = msg.chat.id
    if 'tenant_require_platform_owner' in globals():
        if not tenant_require_platform_owner(msg):
            return
    elif not is_owner_chat(chat_id if 'chat_id' in locals() else msg.chat.id):
        return
    count = disable_restore_guard_and_enable_mega_backups()
    send_and_auto_delete(chat_id, restore_guard_status_text() + f'\n\n✅ Guard отключён владельцем. MEGA autobackup включён для {count} чатов.', 120)

@bot.message_handler(commands=['restore_guard_on'])
def cmd_restore_guard_on(msg):
    try:
        update_chat_info_from_message(msg)
    except Exception:
        pass
    schedule_command_delete(msg)
    chat_id = msg.chat.id
    if 'tenant_require_platform_owner' in globals():
        if not tenant_require_platform_owner(msg):
            return
    elif not is_owner_chat(chat_id if 'chat_id' in locals() else msg.chat.id):
        return
    set_restore_guard_manual_override(False)
    send_and_auto_delete(chat_id, '🛡 Ручное отключение Restore guard снято. При следующей аварийной проверке guard снова сможет включиться.', 90)

@bot.message_handler(commands=['delta_status'])
def cmd_delta_status(msg):
    try:
        update_chat_info_from_message(msg)
    except Exception:
        pass
    schedule_command_delete(msg)
    if 'tenant_require_platform_owner' in globals():
        if not tenant_require_platform_owner(msg):
            return
    elif not is_owner_chat(chat_id if 'chat_id' in locals() else msg.chat.id):
        return
    send_and_auto_delete(msg.chat.id, delta_status_text(), 120)

@bot.message_handler(commands=['mega_status'])
def cmd_mega_status(msg):
    try:
        update_chat_info_from_message(msg)
    except Exception:
        pass
    schedule_command_delete(msg)
    chat_id = msg.chat.id
    if 'tenant_require_platform_owner' in globals():
        if not tenant_require_platform_owner(msg):
            return
    elif not is_owner_chat(chat_id if 'chat_id' in locals() else msg.chat.id):
        send_and_auto_delete(chat_id, 'Эта команда только для владельца.', HELPER_DELETE_DELAY)
        return
    send_and_auto_delete(chat_id, mega_status_text(), 90)

def run_manual_mega_restore(chat_id: int):
    """Owner recovery using the same canonical SQLite+delta engine as deploy.

    v241: legacy full-global JSON is compatibility fallback only.  A successful
    recovery is immediately re-anchored as a new exact durable generation so the
    next deploy reproduces the same state instead of depending on an old JSON.
    """
    global data
    chat_id = int(chat_id)
    backup_dir = ''
    restore_epoch = 0
    success = False
    try:
        send_and_auto_delete(chat_id, '☁️ Ручное восстановление: читаю canonical SQLite + delta из MEGA…', 30)
        begin = globals().get('_v241_restore_storage_barrier_begin')
        if callable(begin):
            restore_epoch = int(begin() or 0)
        backup_fn = globals().get('_v153_backup_before_restore')
        if callable(backup_fn):
            backup_dir = str(backup_fn() or '')
        else:
            raise RuntimeError('pre_restore backup helper недоступен')
        canonical_fn = globals().get('mega_restore_sqlite_snapshot_from_cloud')
        ok = False
        detail = 'canonical restore helper unavailable'
        if callable(canonical_fn):
            try:
                ok, detail = canonical_fn(force=True)
            except TypeError:
                ok, detail = canonical_fn()
        applied_deltas = 0
        source = 'canonical SQLite'
        if ok:
            restored = load_data()
            data.clear()
            data.update(restored)
            try:
                seen = globals().get('_LOWRAM_BOOT_APPLIED_DELTA_PATHS')
                if hasattr(seen, 'clear'):
                    seen.clear()
            except Exception:
                pass
            delta_fn = globals().get('lowram_apply_deltas_after_db_snapshot')
            if callable(delta_fn):
                applied_deltas = int(delta_fn() or 0)
        else:
            legacy = globals().get('mega_restore_full_from_cloud')
            if not callable(legacy):
                raise RuntimeError(detail)
            ok, detail = legacy(force=True)
            source = 'legacy global JSON'
            if not ok:
                raise RuntimeError(detail)
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
        except Exception as exc:
            log_error(f'manual MEGA rehydrate v241: {exc}')
        try:
            bind = globals().get('config_guard_bind_recovered_state_v242')
            if callable(bind):
                bind()
        except Exception as exc:
            raise RuntimeError('config binding after MEGA restore failed: ' + str(exc)[:300])
        verify = globals().get('constitution_boot_verify_after_restore')
        if callable(verify):
            rep = verify() or {}
            if not bool(rep.get('ok')):
                raise RuntimeError('semantic verify after MEGA restore failed: ' + str(rep.get('reason') or 'unknown')[:350])
        save_data(data, full=True)
        reanchor = globals().get('_v240_restore_reanchor_guaranteed')
        if not callable(reanchor):
            raise RuntimeError('Guaranteed restore reanchor helper недоступен')
        constitution_result = reanchor('mega_restore_now_v242') or {}
        active = constitution_result.get('active') or {}
        generation = active.get('generation') or '—'
        cfg_report = constitution_result.get('config_checkpoint') or {}
        lineage = str(constitution_result.get('lineage') or active.get('storage_lineage_v239') or '')
        remote_confirmed = bool(constitution_result.get('remote_confirmed_v240', False))
        warning = str(constitution_result.get('warning') or '')
        initialize_delta_baseline(data)
        try:
            heal = globals().get('_v243_mark_runtime_restore_healthy')
            if callable(heal):
                heal('mega_restore_now_v243', remote_confirmed=remote_confirmed, generation=str(generation))
        except Exception:
            pass
        _clear_restore_guard()
        success = True
        try:
            reconcile = globals().get('_reminder_boot_reconcile_v241')
            if callable(reconcile):
                reconcile()
        except Exception as exc:
            log_error(f'manual MEGA reminder reconcile v241: {exc}')
        try:
            refresh_registered_financial_windows(chat_id)
        except Exception:
            pass
        try:
            schedule_startup_main_windows(delay=0.5)
        except Exception:
            pass
        if remote_confirmed:
            restore_note = 'Состояние закреплено новым canonical checkpoint для следующего deploy.'
        else:
            restore_note = 'Состояние уже принято локально; remote canonical re-anchor поставлен на автоматический повтор.'
        send_and_auto_delete(chat_id, f"✅ MEGA → бот восстановлен. Источник: {source}; delta={applied_deltas}; generation={generation}; config={cfg_report.get('generation', '—')}; lineage={lineage or '—'}. " + restore_note + (f' Причина pending: {warning[:180]}' if warning else ''), 180)
        try:
            bot_journal('mega_manual_restore_guaranteed_v242', chat_id, f"source={source}; delta={applied_deltas}; generation={generation}; config={cfg_report.get('generation', '')}; lineage={lineage}; remote_confirmed={int(remote_confirmed)}; epoch={restore_epoch}")
        except Exception:
            pass
    except Exception as e:
        log_error(f'run_manual_mega_restore: {e}')
        send_and_auto_delete(chat_id, '❌ Ошибка ручного восстановления из MEGA: ' + str(e)[:500], 180)
    finally:
        if backup_dir:
            try:
                shutil.rmtree(backup_dir, ignore_errors=True)
            except Exception:
                pass
        end = globals().get('_v241_restore_storage_barrier_end')
        if restore_epoch and callable(end):
            try:
                end(restore_epoch, success)
            except Exception:
                pass

@bot.message_handler(commands=['mega_restore_now'])
def cmd_mega_restore_now(msg):
    try:
        update_chat_info_from_message(msg)
    except Exception:
        pass
    schedule_command_delete(msg)
    chat_id = msg.chat.id
    if 'tenant_require_platform_owner' in globals():
        if not tenant_require_platform_owner(msg):
            return
    elif not is_owner_chat(chat_id if 'chat_id' in locals() else msg.chat.id):
        send_and_auto_delete(chat_id, 'Эта команда только для владельца.', HELPER_DELETE_DELAY)
        return
    _restore_pool = globals().get('RECOVERY_TASK_POOL') or globals().get('GENERAL_TASK_POOL')
    if _restore_pool is None or not _restore_pool.submit(f'manual-mega-restore:{chat_id}', run_manual_mega_restore, chat_id):
        send_and_auto_delete(chat_id, '⛔ Очередь восстановления переполнена. Попробуйте позже.', 20)

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

@bot.message_handler(commands=['mega_backup_now'])
def cmd_mega_backup_now(msg):
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
        send_and_auto_delete(chat_id, 'Эта команда только для владельца.', HELPER_DELETE_DELAY)
        return
    pool = globals().get('RECOVERY_TASK_POOL') or globals().get('BACKGROUND_TASK_POOL')
    if pool is None or not pool.submit(f'manual-mega-backup:{chat_id}', run_manual_mega_backup_v243, chat_id):
        send_and_auto_delete(chat_id, '⛔ Очередь MEGA backup занята. Попробуйте позже.', 20)

def build_diag_text() -> str:
    chats = data.get('chats', {}) or {}
    finance_ids = collect_finance_chat_ids()
    hidden = []
    quick_on = []
    try:
        for cid in finance_ids:
            if is_hidden_finance_mode(cid):
                hidden.append(cid)
            if is_quick_balance_enabled(cid):
                quick_on.append(cid)
    except Exception:
        pass
    fr = data.get('forward_rules', {}) or {}
    forward_pairs = sum((len(v or {}) for v in fr.values()))
    active_windows_count = 0
    try:
        active_windows_count = sum((len(v or {}) for v in (data.get('active_messages', {}) or {}).values()))
    except Exception:
        active_windows_count = 0
    dirty_count = 0
    try:
        with timer_lock:
            dirty_count = len(_backup_dirty_chats)
    except Exception:
        pass
    errors = get_recent_errors(5)
    lines = ['🧪 Диагностика бота', f'Версия: {VERSION}', f'SQLite: {DB_FILE}', f'Чатов в базе: {len(chats)}', f'Фин-чатов: {len(finance_ids)}', f'Скрытых фин-чатов: {len(hidden)}', f'Быстрый остаток включён: {len(quick_on)}', f'Связей пересылки: {forward_pairs}', f'Активных окон: {active_windows_count}', f'Dirty-бэкапов в очереди: {dirty_count}', f"Очередь content: {WEBHOOK_TASK_POOL.stats()['pending']}", f"Очередь UI: {UI_TASK_POOL.stats()['pending']}", f"Очередь callback ACK: {CALLBACK_ACK_TASK_POOL.stats()['pending']}", f"Очередь recovery: {RECOVERY_TASK_POOL.stats()['pending']}", f"Очередь напоминалок: {REMINDER_TASK_POOL.stats()['pending']}", f"Очередь пересылки: {FORWARD_TASK_POOL.stats()['pending']}", f"Очередь финансов: {FINANCE_TASK_POOL.stats()['pending']}", f"Очередь delta: {DELTA_TASK_POOL.stats()['pending']}", f"Очередь backup: {BACKUP_TASK_POOL.stats()['pending']}", f"Очередь maintenance: {MAINTENANCE_TASK_POOL.stats()['pending']}", f"BACKUP_CHAT_ID: {('есть' if BACKUP_CHAT_ID else 'нет')}", f"Бэкап в канал: {('✅ ВКЛ' if backup_flags.get('channel', True) else '⬜ ВЫКЛ')}", f"MEGA: {('✅ ВКЛ' if MEGA_ENABLED else '⬜ ВЫКЛ')} / {('настроено' if mega_is_configured() else 'не настроено')}", f'MEGA dir: {MEGA_BACKUP_DIR}', f'MEGA delta dir: {mega_delta_remote_root()}', f'Delta pending: {len(_delta_pending_chats)} / last events: {_delta_last_event_count}', f"Global full pending: {('да' if _global_snapshot_pending else 'нет')}", f'Ошибок в журнале: {len(get_recent_errors(80))}']
    if errors:
        lines.append('')
        lines.append('Последние ошибки:')
        for e in errors:
            lines.append(f"• {e.get('ts', '')} — {format_error_for_owner(e.get('msg', ''))[:160]}")
    return '\n'.join(lines)

@bot.message_handler(commands=['off_on_backup_excel'])
def cmd_off_on_backup_excel(msg):
    update_chat_info_from_message(msg)
    schedule_command_delete(msg)
    chat_id = msg.chat.id
    if 'tenant_can_manage' in globals():
        actor = int(getattr(getattr(msg, 'from_user', None), 'id', 0) or 0)
        if not tenant_can_manage(actor, chat_id=chat_id):
            send_and_auto_delete(chat_id, 'Эта команда только для владельца пространства.', HELPER_DELETE_DELAY)
            return
    elif not is_owner_chat(chat_id):
        send_and_auto_delete(chat_id, 'Эта команда только для владельца.', HELPER_DELETE_DELAY)
        return
    enabled = toggle_backup_excel_all_enabled()
    if enabled:
        target_ids = tenant_chat_ids(tenant_id_for_chat(chat_id, create=False)) if 'tenant_chat_ids' in globals() else collect_finance_chat_ids()
        for cid in target_ids:
            if is_finance_mode(int(cid)):
                schedule_backup_flush(int(cid), BACKUP_MIN_DELAY_SECONDS)
    send_and_auto_delete(chat_id, f"📊 Excel-бэкап чатов пространства: {('✅ ВКЛ' if enabled else '⬜ ВЫКЛ')}", 20)

@bot.message_handler(commands=['queues', 'queue_status'])
def cmd_queues(msg):
    update_chat_info_from_message(msg)
    schedule_command_delete(msg)
    chat_id = msg.chat.id
    if 'tenant_require_platform_owner' in globals():
        if not tenant_require_platform_owner(msg):
            return
    elif not is_owner_chat(chat_id if 'chat_id' in locals() else msg.chat.id):
        send_and_auto_delete(chat_id, 'Эта команда только для владельца.', HELPER_DELETE_DELAY)
        return
    send_and_auto_delete(chat_id, build_queue_status_text(), 90)

@bot.message_handler(commands=['diag', 'diagnostics'])
def cmd_diag(msg):
    try:
        update_chat_info_from_message(msg)
    except Exception:
        pass
    schedule_command_delete(msg)
    chat_id = msg.chat.id
    if 'tenant_require_platform_owner' in globals():
        if not tenant_require_platform_owner(msg):
            return
    elif not is_owner_chat(chat_id if 'chat_id' in locals() else msg.chat.id):
        send_and_auto_delete(chat_id, 'Эта команда только для владельца.', HELPER_DELETE_DELAY)
        return
    send_and_auto_delete(chat_id, build_diag_text(), 60)

@bot.message_handler(commands=['errors', 'bot_errors'])
def cmd_errors(msg):
    try:
        update_chat_info_from_message(msg)
    except Exception:
        pass
    schedule_command_delete(msg)
    chat_id = msg.chat.id
    if 'tenant_require_platform_owner' in globals():
        if not tenant_require_platform_owner(msg):
            return
    elif not is_owner_chat(chat_id if 'chat_id' in locals() else msg.chat.id):
        send_and_auto_delete(chat_id, 'Эта команда только для владельца.', HELPER_DELETE_DELAY)
        return
    errors = get_recent_errors(30)
    if not errors:
        send_and_auto_delete(chat_id, '🧯 Ошибок в журнале нет.', 30)
        return
    unique = []
    seen = set()
    for e in reversed(errors):
        msg_text = format_error_for_owner(e.get('msg', ''))
        fingerprint = re.sub('\\s+', ' ', msg_text).strip()[:1200]
        if fingerprint in seen:
            continue
        seen.add(fingerprint)
        unique.append((e, msg_text))
        if len(unique) >= 12:
            break
    unique.reverse()
    blocks = ['🧯 Последние ошибки бота:']
    for e, msg_text in unique:
        blocks.append(f"• {e.get('ts', '')}\n{msg_text[:650]}")
    chunks = []
    current = ''
    for block in blocks:
        candidate = block if not current else current + '\n\n' + block
        if len(candidate) > 3400 and current:
            chunks.append(current)
            current = block
        else:
            current = candidate
    if current:
        chunks.append(current)
    for idx, chunk in enumerate(chunks, start=1):
        prefix = f'🧯 Ф40 {idx}/{len(chunks)}\n' if len(chunks) > 1 else ''
        send_and_auto_delete(chat_id, prefix + chunk, 90)

@bot.message_handler(commands=['journal', 'log', 'logs'])
def cmd_journal(msg):
    try:
        update_chat_info_from_message(msg)
    except Exception:
        pass
    schedule_command_delete(msg)
    chat_id = msg.chat.id
    bot_journal('command_journal', chat_id, getattr(msg, 'text', ''))
    if 'tenant_require_platform_owner' in globals():
        if not tenant_require_platform_owner(msg):
            return
    elif not is_owner_chat(chat_id if 'chat_id' in locals() else msg.chat.id):
        send_and_auto_delete(chat_id, 'Эта команда только для владельца.', HELPER_DELETE_DELAY)
        return
    send_journal_file_to_owner(chat_id, 3000)

def _send_sqlite_dump_job(chat_id: int):
    """Send the working SQLite snapshot through the same no-duplicate file lane."""
    try:
        _file_job_progress('отправляю SQLite в Telegram', force=True)
        with open(DB_FILE, 'rb') as f:
            _tg_call_retry(bot.send_document, chat_id, f, caption=f'🗄 SQLite база: {os.path.basename(DB_FILE)}', timeout=120, purpose='manual_sqlite_export')
        return True
    except Exception as e:
        log_error(f'_send_sqlite_dump_job: {e}')
        send_and_auto_delete(chat_id, f'❌ Не удалось отправить SQLite: {e}', HELPER_DELETE_DELAY)
        return False

@bot.message_handler(commands=['sqlite', 'db'])
def cmd_sqlite_dump(msg):
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
    elif not is_owner_chat(chat_id if 'chat_id' in locals() else msg.chat.id):
        send_and_auto_delete(chat_id, 'Эта команда только для владельца.', HELPER_DELETE_DELAY)
        return
    ok, info = submit_interactive_file_job(chat_id, 'sqlite', 'SQLite база', _send_sqlite_dump_job, chat_id)
    if not ok:
        send_and_auto_delete(chat_id, f'⏳ {info}. Новая копия в очередь не добавлена.', 10)

def start_keep_alive_thread():
    global _keep_alive_thread, _peer_keep_alive_thread
    with _keep_alive_thread_lock:
        if _keep_alive_thread is None or not _keep_alive_thread.is_alive():
            _keep_alive_thread = threading.Thread(target=keep_alive_task, name='keep-alive-watchdog', daemon=True)
            _keep_alive_thread.start()
        if _peer_keep_alive_thread is None or not _peer_keep_alive_thread.is_alive():
            _peer_keep_alive_thread = threading.Thread(target=peer_keep_alive_task, name='peer-keep-alive-watchdog', daemon=True)
            _peer_keep_alive_thread.start()
        return _keep_alive_thread
# v262
