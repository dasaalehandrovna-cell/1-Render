# v266
"""ОЧНИСЬ 12.35 · physical owner: finance.

Этот файл — единственное физическое место тел функций домена.
Он НЕ запускается отдельно и НЕ импортируется как Python-модуль.
bot.py читает его как каталог исходников и устанавливает нужную стадию в исторической точке runtime.
Последняя версия каждого публичного символа сохраняет обычное имя; старые стадии помечены _legacy_sXXXX_.
"""

# --- finance:0001 · from 01_core_data.py:6102 · public finance_day_start_5am_enabled ---
def finance_day_start_5am_enabled(chat_id: int | None=None) -> bool:
    """Режим финансовых суток хранится отдельно в owner scope."""
    return bool(_owner_setting_value('finance_day_start_5am', False, chat_id))

# --- finance:0002 · from 01_core_data.py:6106 · public toggle_finance_day_start_5am ---
def toggle_finance_day_start_5am(chat_id: int | None=None) -> bool:
    new_value = not finance_day_start_5am_enabled(chat_id)
    _set_owner_setting_value('finance_day_start_5am', new_value, chat_id)
    return new_value

# --- finance:0003 · from 01_core_data.py:6111 · public finance_day_key_from_datetime ---
def finance_day_key_from_datetime(dt: datetime, chat_id: int | None=None) -> str:
    try:
        if finance_day_start_5am_enabled(chat_id):
            dt = dt - timedelta(hours=5)
        else:
            try:
                minute = int(_owner_setting_value('finance_day_start_minute', 5, chat_id) or 5)
            except Exception:
                minute = 5
            dt = dt - timedelta(minutes=max(0, min(59, minute)))
        return dt.strftime('%Y-%m-%d')
    except Exception:
        return today_key()

# --- finance:0004 · from 01_core_data.py:6125 · public finance_day_key_from_message ---
def finance_day_key_from_message(msg=None) -> str:
    try:
        if msg and getattr(msg, 'date', None):
            dt = datetime.fromtimestamp(int(msg.date), tz=get_tz())
        else:
            dt = now_local()
        cid = getattr(getattr(msg, 'chat', None), 'id', None) if msg is not None else current_state_chat_id()
        return finance_day_key_from_datetime(dt, cid)
    except Exception:
        return day_key_from_message(msg)

# --- finance:0005 · from 01_core_data.py:6136 · public finance_today_key ---
def finance_today_key(chat_id: int | None=None) -> str:
    return finance_day_key_from_datetime(now_local(), chat_id if chat_id is not None else current_state_chat_id())

# --- finance:0006 · from 01_core_data.py:6139 · public finance_day_start_label ---
def finance_day_start_label(chat_id: int | None=None) -> str:
    if finance_day_start_5am_enabled(chat_id):
        return '05:00'
    try:
        minute = int(_owner_setting_value('finance_day_start_minute', 5, chat_id) or 5)
    except Exception:
        minute = 5
    return f'00:{max(0, min(59, minute)):02d}'

# --- finance:0007 · from 01_core_data.py:6419 · public format_finance_mode_label ---
def format_finance_mode_label(chat_id: int) -> str:
    return '✅ ВКЛ' if is_finance_mode(chat_id) else '⬜ ВЫКЛ'

# --- finance:0008 · from 01_core_data.py:6422 · public info_finance_toggle_label ---
def info_finance_toggle_label(chat_id: int) -> str:
    return '✅ Фин режим ВКЛ' if is_finance_mode(chat_id) else '⬜ Фин режим ВЫКЛ'

# --- finance:0009 · from 01_core_data.py:6425 · public is_quick_balance_enabled ---
def is_quick_balance_enabled(chat_id: int) -> bool:
    store = get_chat_store(chat_id)
    settings = store.setdefault('settings', {})
    return bool(settings.get('quick_balance_enabled', False))

# --- finance:0010 · from 01_core_data.py:6430 · public get_quick_balance_behavior ---
def get_quick_balance_behavior(chat_id: int) -> str:
    store = get_chat_store(chat_id)
    settings = store.setdefault('settings', {})
    behavior = (settings.get('quick_balance_behavior') or 'normal').strip().lower()
    if behavior in {'normal', 'mini', 'open', 'first'}:
        return behavior
    return 'normal'

# --- finance:0011 · from 01_core_data.py:6438 · public _infer_legacy_finance_window_mode ---
def _infer_legacy_finance_window_mode(chat_id: int) -> str:
    """Migration from v107: hidden-only means no visible auto-window; otherwise preserve old visible mode."""
    try:
        if not is_finance_mode(chat_id):
            return 'off'
        if is_quick_balance_enabled(chat_id):
            behavior = get_quick_balance_behavior(chat_id)
            if behavior in {'open', 'first'}:
                return behavior
        if is_hidden_finance_mode(chat_id):
            return 'off'
        return 'normal'
    except Exception:
        return 'off'

# --- finance:0012 · from 01_core_data.py:6453 · public _finance_window_state ---
def _finance_window_state(chat_id: int) -> dict:
    chat_id = int(chat_id)
    store = get_chat_store(chat_id)
    state = store.get('finance_window_state')
    if not isinstance(state, dict):
        try:
            active = dict((data.get('active_messages', {}) or {}).get(str(chat_id), {}) or {})
        except Exception:
            active = {}
        mode = _infer_legacy_finance_window_mode(chat_id)
        state = {'mode': mode, 'main_windows': {str(k): int(v) for k, v in active.items() if v}, 'balance_panel_id': int(store.get('balance_panel_id')) if store.get('balance_panel_id') else None, 'balance_panel_mode': str(store.get('balance_panel_mode') or 'mini'), 'current_view_day': str(store.get('current_view_day') or today_key()), 'auto_reopen_on_boot': bool(mode != 'off' and (active or store.get('balance_panel_id') or (not is_hidden_finance_mode(chat_id)))), 'updated_at': now_local().isoformat(timespec='seconds')}
        store['finance_window_state'] = state
    state.setdefault('mode', _infer_legacy_finance_window_mode(chat_id))
    if state.get('mode') not in {'off', 'normal', 'open', 'first'}:
        state['mode'] = 'off'
    state.setdefault('main_windows', {})
    state.setdefault('balance_panel_id', None)
    state.setdefault('balance_panel_mode', 'mini')
    state.setdefault('current_view_day', str(store.get('current_view_day') or today_key()))
    state.setdefault('auto_reopen_on_boot', bool(state.get('mode') != 'off'))
    state.setdefault('updated_at', now_local().isoformat(timespec='seconds'))
    return state

# --- finance:0013 · from 01_core_data.py:6476 · public finance_window_mode ---
def finance_window_mode(chat_id: int) -> str:
    if not is_finance_mode(chat_id):
        return 'off'
    try:
        return str(_finance_window_state(chat_id).get('mode') or 'off')
    except Exception:
        return 'off'

# --- finance:0014 · from 01_core_data.py:6484 · public finance_window_mode_enabled ---
def finance_window_mode_enabled(chat_id: int, mode: str | None=None) -> bool:
    current = finance_window_mode(chat_id)
    if mode is None:
        return current in {'normal', 'open', 'first'}
    return current == str(mode)

# --- finance:0015 · from 01_core_data.py:6490 · public _sync_finance_window_state_from_runtime ---
def _sync_finance_window_state_from_runtime(chat_id: int, *, schedule_delta: bool=False):
    """Compact UI state intentionally survives deploy without putting full open_window_registry into delta."""
    try:
        chat_id = int(chat_id)
        store = get_chat_store(chat_id)
        state = _finance_window_state(chat_id)
        try:
            active = dict((data.get('active_messages', {}) or {}).get(str(chat_id), {}) or {})
        except Exception:
            active = {}
        state['main_windows'] = {str(k): int(v) for k, v in active.items() if v}
        state['balance_panel_id'] = int(store.get('balance_panel_id')) if store.get('balance_panel_id') else None
        state['balance_panel_mode'] = str(store.get('balance_panel_mode') or state.get('balance_panel_mode') or 'mini')
        state['current_view_day'] = str(store.get('current_view_day') or state.get('current_view_day') or today_key())
        state['updated_at'] = now_local().isoformat(timespec='seconds')
        store['finance_window_state'] = state
        save_data(data, chat_ids=[chat_id])
        if schedule_delta and mega_is_configured() and (not RESTORE_GUARD_ACTIVE):
            schedule_quick_backup(chat_id, 0.5)
    except Exception as e:
        log_error(f'_sync_finance_window_state_from_runtime({chat_id}): {e}')

# --- finance:0016 · from 01_core_data.py:6512 · public restore_finance_window_runtime_state ---
def restore_finance_window_runtime_state():
    """Rehydrate volatile Telegram message ids from compact chat metadata after MEGA/global+delta restore."""
    try:
        for cid_s, store in (data.get('chats', {}) or {}).items():
            try:
                cid = int(cid_s)
            except Exception:
                continue
            state = store.get('finance_window_state')
            if not isinstance(state, dict):
                _finance_window_state(cid)
                state = store.get('finance_window_state') or {}
            mode = str(state.get('mode') or 'off')
            settings = store.setdefault('settings', {})
            if mode == 'normal':
                settings['quick_balance_enabled'] = False
                settings['quick_balance_behavior'] = 'normal'
                settings['quick_balance_user_selected'] = True
            elif mode in {'open', 'first'}:
                settings['quick_balance_enabled'] = True
                settings['quick_balance_behavior'] = mode
                settings['quick_balance_user_selected'] = True
            else:
                settings['quick_balance_enabled'] = False
                settings['quick_balance_behavior'] = 'normal'
                settings['quick_balance_user_selected'] = True
            main_windows = {str(k): int(v) for k, v in (state.get('main_windows') or {}).items() if v}
            selected_day = str(state.get('current_view_day') or store.get('current_view_day') or today_key())[:10]
            selected_mid = int(main_windows.get(selected_day) or 0)
            if not selected_mid and main_windows:
                try:
                    selected_day, selected_mid = list(main_windows.items())[-1]
                    selected_day = str(selected_day)[:10]
                    selected_mid = int(selected_mid)
                except Exception:
                    selected_mid = 0
            data.setdefault('active_messages', {})[str(cid)] = {selected_day: selected_mid} if selected_mid else {}
            store['primary_main_window_id'] = selected_mid or None
            store['primary_main_window_day'] = selected_day
            store['current_view_day'] = selected_day
            state['main_windows'] = {selected_day: selected_mid} if selected_mid else {}
            state['current_view_day'] = selected_day
            store['balance_panel_id'] = int(state.get('balance_panel_id')) if state.get('balance_panel_id') else None
            store['balance_panel_mode'] = str(state.get('balance_panel_mode') or 'mini')
    except Exception as e:
        log_error(f'restore_finance_window_runtime_state: {e}')

# --- finance:0017 · from 01_core_data.py:6559 · public _persist_finance_window_mode_critical ---
def _persist_finance_window_mode_critical(chat_id: int) -> bool:
    """Persist window choice + callback idempotency marker before a critical callback may be acknowledged."""
    try:
        chat_id = int(chat_id)
        _sync_finance_window_state_from_runtime(chat_id, schedule_delta=False)
        if mega_is_configured() and (not RESTORE_GUARD_ACTIVE):
            ctx = _current_telegram_update_context()
            update_id = ctx.get('update_id')
            if update_id is not None and str(ctx.get('update_type') or '') == 'callback_query':
                mark_durable_update_processed(update_id, chat_id, 'callback_query')
            return bool(persist_critical_delta_now(chat_id))
    except Exception as e:
        log_error(f'_persist_finance_window_mode_critical({chat_id}): {e}')
    return False

# --- finance:0018 · from 01_core_data.py:6574 · public set_finance_window_mode ---
def set_finance_window_mode(chat_id: int, mode: str, *, persist_now: bool=False):
    chat_id = int(chat_id)
    mode = str(mode or 'off').lower().strip()
    if mode not in {'off', 'normal', 'open', 'first'}:
        mode = 'off'
    store = get_chat_store(chat_id)
    settings = store.setdefault('settings', {})
    state = _finance_window_state(chat_id)
    state['mode'] = mode
    state['auto_reopen_on_boot'] = bool(mode != 'off')
    state['updated_at'] = now_local().isoformat(timespec='seconds')
    if mode == 'normal':
        settings['quick_balance_enabled'] = False
        settings['quick_balance_behavior'] = 'normal'
        settings['quick_balance_user_selected'] = True
    elif mode in {'open', 'first'}:
        settings['quick_balance_enabled'] = True
        settings['quick_balance_behavior'] = mode
        settings['quick_balance_user_selected'] = True
    else:
        settings['quick_balance_enabled'] = False
        settings['quick_balance_behavior'] = 'normal'
        settings['quick_balance_user_selected'] = True
    store['finance_window_state'] = state
    save_data(data, chat_ids=[chat_id])
    if persist_now:
        _persist_finance_window_mode_critical(chat_id)
    else:
        schedule_config_backup_for_chats(chat_id)

# --- finance:0019 · from 01_core_data.py:6604 · public _v177_legacy_0025_delete_auto_finance_windows_for_chat ---
def _v177_legacy_0025_delete_auto_finance_windows_for_chat(chat_id: int, *, persist_now: bool=False) -> int:
    """Delete only automatic finance windows controlled by the three F39 modes, not manual reports/F91/category views."""
    chat_id = int(chat_id)
    store = get_chat_store(chat_id)
    ids = set()
    try:
        ids.update((int(v) for v in (get_or_create_active_windows(chat_id) or {}).values() if v))
    except Exception:
        pass
    try:
        if store.get('balance_panel_id'):
            ids.add(int(store.get('balance_panel_id')))
    except Exception:
        pass
    removed = 0
    for mid in sorted(ids):
        try:
            bot.delete_message(chat_id, mid)
            removed += 1
        except Exception:
            pass
        try:
            unregister_open_window(chat_id, mid)
        except Exception:
            pass
    data.setdefault('active_messages', {})[str(chat_id)] = {}
    store['balance_panel_id'] = None
    store['balance_panel_mode'] = 'mini'
    store['main_window_msg_count'] = 0
    store['balance_panel_msg_count'] = 0
    state = _finance_window_state(chat_id)
    state['main_windows'] = {}
    state['balance_panel_id'] = None
    state['balance_panel_mode'] = 'mini'
    state['auto_reopen_on_boot'] = False if finance_window_mode(chat_id) == 'off' else state.get('auto_reopen_on_boot', True)
    state['updated_at'] = now_local().isoformat(timespec='seconds')
    save_data(data, chat_ids=[chat_id])
    if persist_now:
        _persist_finance_window_mode_critical(chat_id)
    else:
        try:
            schedule_quick_backup(chat_id, 0.5)
        except Exception:
            pass
    return removed

# --- finance:0020 · from 01_core_data.py:6654 · public set_quick_balance_behavior ---
def set_quick_balance_behavior(chat_id: int, behavior: str):
    store = get_chat_store(chat_id)
    settings = store.setdefault('settings', {})
    behavior = str(behavior or 'normal').strip().lower()
    if behavior not in {'normal', 'mini', 'open', 'first'}:
        behavior = 'normal'
    settings['quick_balance_behavior'] = behavior
    settings['quick_balance_user_selected'] = True
    save_data(data)
    schedule_config_backup_for_chats(chat_id)
    if behavior == 'first':
        schedule_quick_balance_first_recreate(chat_id)

# --- finance:0021 · from 01_core_data.py:6667 · public set_quick_balance_enabled ---
def set_quick_balance_enabled(chat_id: int, enabled: bool):
    chat_id = int(chat_id)
    store = get_chat_store(chat_id)
    settings = store.setdefault('settings', {})
    enabled = bool(enabled)
    settings['quick_balance_enabled'] = enabled
    if enabled:
        set_finance_mode(chat_id, True)
        if store.get('balance_panel_mode') not in {'mini', 'open'}:
            store['balance_panel_mode'] = 'mini'
        save_data(data)
        schedule_config_backup_for_chats(chat_id)
        schedule_balance_panel_refresh(chat_id, 0.1)
        return
    panel_id = store.get('balance_panel_id')
    if panel_id:
        try:
            bot.delete_message(chat_id, panel_id)
        except Exception:
            pass
    store['balance_panel_id'] = None
    store['balance_panel_mode'] = 'normal'
    settings['quick_balance_behavior'] = 'normal'
    save_data(data)
    schedule_config_backup_for_chats(chat_id)

# --- finance:0022 · from 01_core_data.py:6693 · public is_hidden_finance_mode ---
def is_hidden_finance_mode(chat_id: int) -> bool:
    try:
        store = get_chat_store(chat_id)
        return bool(store.setdefault('settings', {}).get('hidden_finance', False))
    except Exception:
        return False

# --- finance:0023 · from 01_core_data.py:6700 · public is_finance_output_suppressed ---
def is_finance_output_suppressed(chat_id: int) -> bool:
    """Скрытый финрежим: учёт остаётся, но в самом чате ничего финансового не выводим."""
    try:
        return bool(is_hidden_finance_mode(chat_id) and (not is_owner_chat(chat_id)))
    except Exception:
        return False

# --- finance:0024 · from 01_core_data.py:7910 · public set_hidden_finance_mode ---
def set_hidden_finance_mode(chat_id: int, enabled: bool):
    """v108: hidden finance is independent from the three automatic finance-window modes."""
    chat_id = int(chat_id)
    store = get_chat_store(chat_id)
    settings = store.setdefault('settings', {})
    settings['hidden_finance'] = bool(enabled)
    if enabled:
        set_finance_mode(chat_id, True)
    save_data(data, chat_ids=[chat_id])
    schedule_config_backup_for_chats(chat_id)

# --- finance:0025 · from 01_core_data.py:7921 · public force_recreate_balance_panel ---
def force_recreate_balance_panel(chat_id: int):
    """Пересоздаёт быстрый остаток, чтобы он снова стал последним окном в чате."""
    if finance_window_mode(chat_id) not in {'open', 'first'}:
        return
    if not is_finance_mode(chat_id) or not is_quick_balance_enabled(chat_id):
        return
    store = get_chat_store(chat_id)
    panel_id = store.get('balance_panel_id')
    if panel_id:
        try:
            bot.delete_message(chat_id, int(panel_id))
        except Exception:
            pass
    store['balance_panel_id'] = None
    store['balance_panel_mode'] = 'mini'
    store['balance_panel_msg_count'] = 0
    save_data(data)
    send_minimized_balance_panel(chat_id)

# --- finance:0026 · from 01_core_data.py:7940 · public is_normal_finance_window_mode ---
def is_normal_finance_window_mode(chat_id: int) -> bool:
    """Как обычно: отдельный выбранный режим; hidden finance does not disable it."""
    try:
        return bool(is_finance_mode(chat_id) and finance_window_mode(chat_id) == 'normal')
    except Exception:
        return False

# --- finance:0027 · from 01_core_data.py:7972 · public bump_quick_balance_recreate_counter ---
def bump_quick_balance_recreate_counter(chat_id: int, count: int=1):
    """R48: visual counters are RAM-only; never persist the whole chat per message."""
    try:
        if not is_finance_mode(chat_id) or finance_window_mode(chat_id) == 'off':
            return
        if is_normal_finance_window_mode(chat_id):
            store = get_chat_store(chat_id)
            cur = int(store.get('main_window_msg_count', 0) or 0) + int(count or 1)
            store['main_window_msg_count'] = cur
            if cur >= 10:
                schedule_main_window_recreate_after_quiet(chat_id, delay=4.0)
            return
        if not is_quick_balance_enabled(chat_id):
            return
        if get_quick_balance_behavior(chat_id) == 'first':
            schedule_quick_balance_first_recreate(chat_id)
        store = get_chat_store(chat_id)
        cur = int(store.get('balance_panel_msg_count', 0) or 0) + int(count or 1)
        store['balance_panel_msg_count'] = cur
        if cur >= 3:
            schedule_quick_balance_recreate_after_quiet(chat_id, delay=4.0)
    except Exception as e:
        log_error(f'bump_quick_balance_recreate_counter({get_chat_display_name(chat_id)}): {e}')

# --- finance:0028 · from 01_core_data.py:7998 · public schedule_quick_balance_first_recreate ---
def schedule_quick_balance_first_recreate(chat_id: int, delay: float=60.0):
    try: chat_id = int(chat_id)
    except Exception: return
    if finance_window_mode(chat_id) != 'first' or not is_finance_mode(chat_id) or not is_quick_balance_enabled(chat_id) or get_quick_balance_behavior(chat_id) != 'first': return
    def _job():
        try:
            with locked_chat(chat_id):
                allowed = bool(finance_window_mode(chat_id) == 'first' and is_finance_mode(chat_id) and is_quick_balance_enabled(chat_id) and get_quick_balance_behavior(chat_id) == 'first')
            if allowed:
                force_recreate_balance_panel(chat_id)
        except Exception as e:
            log_error(f'schedule_quick_balance_first_recreate({chat_id}): {e}')
    scheduler_key = f'quick-balance-first:{chat_id}'
    with timer_lock:
        DELAYED_SCHEDULER.cancel(scheduler_key)
        deadline = DELAYED_SCHEDULER.schedule(scheduler_key, delay, _job)
        _balance_panel_first_timers[chat_id] = deadline

# --- finance:0029 · from 01_core_data.py:8018 · public schedule_quick_balance_recreate_after_quiet ---
def schedule_quick_balance_recreate_after_quiet(chat_id: int, delay: float=4.0):
    try: chat_id = int(chat_id)
    except Exception: return
    if finance_window_mode(chat_id) not in {'open', 'first'} or not is_finance_mode(chat_id) or not is_quick_balance_enabled(chat_id): return
    def _job():
        try:
            should = False
            with locked_chat(chat_id):
                store = get_chat_store(chat_id)
                if int(store.get('balance_panel_msg_count', 0) or 0) >= 3:
                    store['balance_panel_msg_count'] = 0
                    should = True
            if should:
                force_recreate_balance_panel(chat_id)
        except Exception as e:
            log_error(f'schedule_quick_balance_recreate_after_quiet({get_chat_display_name(chat_id)}): {e}')
    scheduler_key = f'quick-balance-recreate:{chat_id}'
    with timer_lock:
        DELAYED_SCHEDULER.cancel(scheduler_key)
        deadline = DELAYED_SCHEDULER.schedule(scheduler_key, delay, _job)
        _balance_panel_recreate_timers[chat_id] = deadline

# --- finance:0030 · from 01_core_data.py:8716 · public guard_non_owner_finance_for_command ---
def guard_non_owner_finance_for_command(msg, allowed_commands=None) -> bool:
    allowed = {c.lower().lstrip('/') for c in allowed_commands or []}
    chat_id = msg.chat.id
    if is_owner_chat(chat_id):
        return False
    if is_finance_output_suppressed(chat_id):
        return True
    text = (getattr(msg, 'text', None) or '').strip().lower()
    cmd = text.split()[0].split('@')[0].lstrip('/') if text else ''
    if cmd in allowed:
        return False
    if not is_finance_mode(chat_id):
        send_and_auto_delete(chat_id, '⚙️ Для этого включите финансовый режим командой /ok', HELPER_DELETE_DELAY)
        return True
    return False

# --- finance:0031 · from 01_core_data.py:8732 · public guard_non_owner_finance_for_callback ---
def guard_non_owner_finance_for_callback(chat_id: int, data_str: str) -> bool:
    if is_owner_chat(chat_id):
        return False
    if is_finance_output_suppressed(chat_id):
        if finance_window_mode(chat_id) in {'normal', 'open', 'first'}:
            return False
        return True
    if is_finance_mode(chat_id):
        return False
    if data_str in {'info_close', 'main_articles_toggle', 'main_financial_values_toggle'}:
        return False
    if data_str.startswith('d:') and data_str.endswith(':info'):
        return False
    send_and_auto_delete(chat_id, '⚙️ Для этого включите финансовый режим командой /ok', HELPER_DELETE_DELAY)
    return True

# --- finance:0032 · from 01_core_data.py:9291 · public build_balance_panel_keyboard ---
def build_balance_panel_keyboard(chat_id: int):
    kb = types.InlineKeyboardMarkup()
    bal = get_chat_store(chat_id).get('balance', 0)
    kb.row(IB(f'🏦 Остаток: {format_chat_amount(chat_id, bal, True)}', callback_data='bp:open'))
    return kb

# --- finance:0033 · from 01_core_data.py:9305 · public collapse_balance_panel ---
def collapse_balance_panel(chat_id: int):
    store = get_chat_store(chat_id)
    panel_id = store.get('balance_panel_id')
    if not panel_id:
        return
    try:
        bot.edit_message_text('📌 Быстрый остаток', chat_id=chat_id, message_id=panel_id, reply_markup=build_balance_panel_keyboard(chat_id))
        store['balance_panel_mode'] = 'mini'
        save_data(data)
        _sync_finance_window_state_from_runtime(chat_id, schedule_delta=True)
    except Exception as e:
        err = str(e).lower()
        if 'message is not modified' not in err:
            log_error(f'collapse_balance_panel({chat_id}): {e}')

# --- finance:0034 · from 01_core_data.py:9320 · public schedule_balance_panel_collapse ---
def schedule_balance_panel_collapse(chat_id: int, delay: float | None=None):
    if delay is None:
        delay = internal_timer_seconds('balance_collapse', BALANCE_PANEL_COLLAPSE_DELAY)

    def _job():
        try:
            collapse_balance_panel(chat_id)
        except Exception as e:
            log_error(f'schedule_balance_panel_collapse({chat_id}): {e}')
    store = get_chat_store(chat_id)
    key = store.get('balance_panel_id') or chat_id
    scheduler_key = f'balance-panel-collapse:{int(chat_id)}:{int(key)}'
    _cancel_timer(_balance_panel_collapse_timers, key, scheduler_key)
    deadline = DELAYED_SCHEDULER.schedule(scheduler_key, delay, _job)
    _balance_panel_collapse_timers[key] = deadline

# --- finance:0035 · from 01_core_data.py:9336 · public send_minimized_balance_panel ---
def send_minimized_balance_panel(chat_id: int):
    if finance_window_mode(chat_id) not in {'open', 'first'}:
        return
    if not is_finance_mode(chat_id) or not is_quick_balance_enabled(chat_id):
        return
    store = get_chat_store(chat_id)
    panel_id = store.get('balance_panel_id')
    if panel_id:
        try:
            bot.edit_message_text('📌 Быстрый остаток', chat_id=chat_id, message_id=panel_id, reply_markup=build_balance_panel_keyboard(chat_id))
            store['balance_panel_mode'] = 'mini'
            save_data(data)
            _sync_finance_window_state_from_runtime(chat_id, schedule_delta=True)
            return
        except Exception as e:
            err = str(e).lower()
            if 'message is not modified' in err:
                store['balance_panel_mode'] = 'mini'
                save_data(data)
                _sync_finance_window_state_from_runtime(chat_id, schedule_delta=True)
                return
            log_error(f'send_minimized_balance_panel edit({chat_id}): {e}')
            try:
                bot.delete_message(chat_id, panel_id)
            except Exception:
                pass
            store['balance_panel_id'] = None
    try:
        sent = bot.send_message(chat_id, '📌 Быстрый остаток', reply_markup=build_balance_panel_keyboard(chat_id))
        store['balance_panel_id'] = sent.message_id
        store['balance_panel_mode'] = 'mini'
        save_data(data)
        _finance_window_state(chat_id)['auto_reopen_on_boot'] = True
        _sync_finance_window_state_from_runtime(chat_id, schedule_delta=True)
    except Exception as e:
        log_error(f'send_minimized_balance_panel({chat_id}): {e}')

# --- finance:0036 · from 01_core_data.py:9373 · public _v177_legacy_0062_refresh_balance_panel_now ---
def _v177_legacy_0062_refresh_balance_panel_now(chat_id: int):
    if finance_window_mode(chat_id) not in {'open', 'first'}:
        return
    if not is_finance_mode(chat_id) or not is_quick_balance_enabled(chat_id):
        return
    store = get_chat_store(chat_id)
    panel_id = store.get('balance_panel_id')
    if not panel_id:
        send_minimized_balance_panel(chat_id)
        return
    mode = store.get('balance_panel_mode') or 'mini'
    try:
        if mode == 'open':
            day_key = store.get('current_view_day', today_key())
            txt, _ = render_day_window(chat_id, day_key)
            bot.edit_message_text(txt, chat_id=chat_id, message_id=panel_id, reply_markup=build_main_keyboard(day_key, chat_id), parse_mode='HTML')
            _set_panel_open_state(chat_id, panel_id)
        else:
            bot.edit_message_text('📌 Быстрый остаток', chat_id=chat_id, message_id=panel_id, reply_markup=build_balance_panel_keyboard(chat_id))
    except Exception as e:
        err = str(e).lower()
        if 'message is not modified' in err:
            if mode == 'open':
                schedule_balance_panel_collapse(chat_id)
            return
        if 'message to edit not found' in err or 'message_id_invalid' in err:
            try:
                bot_journal('balance_panel_stale_recreate_v238', chat_id, f'old_mid={panel_id}', 'WARN')
            except Exception:
                pass
        else:
            log_error(f'refresh_balance_panel_now({chat_id}): {e}')
        store['balance_panel_id'] = None
        store['balance_panel_mode'] = 'mini'
        save_data(data)
        _sync_finance_window_state_from_runtime(chat_id, schedule_delta=True)
        send_minimized_balance_panel(chat_id)

# --- finance:0037 · from 01_core_data.py:9415 · public schedule_balance_panel_refresh ---
def schedule_balance_panel_refresh(chat_id: int, delay: float | None=None):
    if delay is None:
        delay = internal_timer_seconds('main_window_refresh', BALANCE_PANEL_REFRESH_DELAY)
    if finance_window_mode(chat_id) not in {'open', 'first'}:
        return
    if not is_finance_mode(chat_id) or not is_quick_balance_enabled(chat_id):
        return

    def _job():
        try:
            store = get_chat_store(chat_id)
            if store.get('balance_panel_id'):
                refresh_balance_panel_now(chat_id)
            else:
                send_minimized_balance_panel(chat_id)
        except Exception as e:
            log_error(f'schedule_balance_panel_refresh({chat_id}): {e}')
    scheduler_key = f'balance-panel-refresh:{int(chat_id)}'
    _cancel_timer(_balance_panel_refresh_timers, chat_id, scheduler_key)
    deadline = DELAYED_SCHEDULER.schedule(scheduler_key, delay, _job)
    _balance_panel_refresh_timers[chat_id] = deadline

# --- finance:0038 · from 01_core_data.py:9437 · public open_balance_panel_in_message ---
def open_balance_panel_in_message(chat_id: int, message_id: int, day_key: str | None=None):
    if finance_window_mode(chat_id) not in {'open', 'first'}:
        return
    if not is_finance_mode(chat_id) or not is_quick_balance_enabled(chat_id):
        return
    store = get_chat_store(chat_id)
    day_key = day_key or store.get('current_view_day', today_key())
    store['current_view_day'] = day_key
    try:
        txt, _ = render_day_window(chat_id, day_key)
        bot.edit_message_text(txt, chat_id=chat_id, message_id=message_id, reply_markup=build_main_keyboard(day_key, chat_id), parse_mode='HTML')
        set_active_window_id(chat_id, day_key, message_id)
        _set_panel_open_state(chat_id, message_id)
    except Exception as e:
        err = str(e).lower()
        if 'message is not modified' in err:
            set_active_window_id(chat_id, day_key, message_id)
            _set_panel_open_state(chat_id, message_id)
            return
        log_error(f'open_balance_panel_in_message({chat_id},{message_id}): {e}')

# --- finance:0039 · from 01_core_data.py:11644 · public _durable_direct_finance_effect_complete ---
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

# --- finance:0040 · from 01_core_data.py:11773 · public _v230_constitution_finance_wait ---
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

# --- finance:0041 · from 01_core_data.py:11793 · public _v230_try_repair_direct_finance_after_quarantine ---
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

# --- finance:0042 · from 01_core_data.py:12687 · public _repair_safe_missing_finance_effects ---
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

# --- finance:0043 · from 01_core_data.py:13089 · public calc_opening_balance_for_month ---
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

# --- finance:0044 · from 01_core_data.py:16844 · public _opening_balance_before_exact ---
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

# --- finance:0045 · from 01_core_data.py:18416 · public note_has_income_marker ---
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

# --- finance:0046 · from 01_core_data.py:18434 · public _parse_usd_number_parts ---
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

# --- finance:0047 · from 01_core_data.py:18447 · public extract_usd_transaction ---
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

# --- finance:0048 · from 01_core_data.py:18497 · public _remove_usd_fragment_for_ars ---
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

# --- finance:0049 · from 01_core_data.py:18532 · public parse_usd_edit_value ---
def parse_usd_edit_value(text: str):
    """Редактирование уже найденной USD-записи: число без знака = расход, + = приход."""
    m = num_re.search(str(text or ''))
    if not m:
        raise ValueError('no usd number')
    amount = parse_amount(m.group(0))
    note = (str(text or '')[:m.start()] + ' ' + str(text or '')[m.end():]).strip()
    note = re.sub('\\s+', ' ', note).lower()
    return (float(amount), note)

# --- finance:0050 · from 01_core_data.py:18640 · public get_expense_category_order_slugs ---
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

# --- finance:0051 · from 01_core_data.py:18653 · public get_expense_category_order ---
def get_expense_category_order(store: dict | None=None) -> list[str]:
    by_slug = {}
    for item in list(_base_category_items(store)) + list(_custom_category_list(store)):
        slug = str(item.get('slug') or '')
        if slug:
            by_slug[slug] = item.get('name')
    return [by_slug[slug] for slug in get_expense_category_order_slugs(store) if slug in by_slug]

# --- finance:0052 · from 01_core_data.py:18661 · public move_expense_category_order ---
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

# --- finance:0053 · from 01_core_data.py:18678 · public move_expense_category_to_position ---
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

# --- finance:0054 · from 01_core_data.py:18696 · public get_expense_category_slug ---
def get_expense_category_slug(category: str, store: dict | None=None) -> str | None:
    category = _clean_category_display_name(str(category or '')).upper()
    for item in _base_category_items(store):
        if category in {str(item.get('name') or '').upper(), str(item.get('default_name') or '').upper()}:
            return item.get('slug')
    for item in _custom_category_list(store):
        if item['name'] == category:
            return item['slug']
    return None

# --- finance:0055 · from 01_core_data.py:18732 · public add_custom_expense_category ---
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

# --- finance:0056 · from 01_core_data.py:18755 · public expense_keyword_matches ---
def expense_keyword_matches(note: str, keyword: str) -> bool:
    """Match a configured word/phrase without matching it inside another word."""
    note = re.sub('\\s+', ' ', str(note or '').casefold()).strip()
    keyword = re.sub('\\s+', ' ', str(keyword or '').casefold()).strip()
    if not note or not keyword:
        return False
    pattern = '(?<![\\w])' + re.escape(keyword).replace('\\ ', '\\s+') + '(?![\\w])'
    return bool(re.search(pattern, note, flags=re.UNICODE))

# --- finance:0057 · from 01_core_data.py:18764 · public financial_view_is_usd ---
def financial_view_is_usd(store: dict | None) -> bool:
    """True when the visible finance shell is switched to 💵 USD operations."""
    try:
        return bool((store or {}).setdefault('settings', {}).get('usd_transactions_view', False))
    except Exception:
        return False

# --- finance:0058 · from 01_core_data.py:18806 · public financial_view_total_balance ---
def financial_view_total_balance(store: dict | None) -> float:
    total = 0.0
    for rec in (store or {}).get('records', []) or []:
        if not isinstance(rec, dict) or not financial_view_record_visible(store, rec):
            continue
        total += financial_view_amount(store, rec)
    return float(total)

# --- finance:0059 · from 01_core_data.py:18814 · public financial_view_balance_through_day ---
def financial_view_balance_through_day(store: dict | None, day_key: str) -> float:
    total = 0.0
    for rec in sorted((store or {}).get('records', []) or [], key=record_sort_key):
        dk = _record_day_key(rec)
        if dk > str(day_key):
            break
        if financial_view_record_visible(store, rec):
            total += financial_view_amount(store, rec)
    return float(total)

# --- finance:0060 · from 01_core_data.py:18832 · public resolve_expense_category ---
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

# --- finance:0061 · from 01_core_data.py:18847 · public resolve_expense_category_for_record ---
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

# --- finance:0062 · from 01_core_data.py:18893 · public expense_anchor_records_for_day ---
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

# --- finance:0063 · from 01_core_data.py:18904 · public expense_anchor_button_label ---
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

# --- finance:0064 · from 01_core_data.py:19121 · public _v207_usd_equivalent ---
def _v207_usd_equivalent(value, rate: float) -> str:
    try:
        if float(rate or 0) <= 0:
            return '$—'
        return f'${_v207_report_num(float(value or 0) / float(rate))}'
    except Exception:
        return '$—'

# --- finance:0065 · from 01_core_data.py:19129 · public _v207_usd_range_rows ---
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

# --- finance:0066 · from 01_core_data.py:19530 · public constitution_finance_write_blocked_v232 ---
def constitution_finance_write_blocked_v232() -> bool:
    """Only a real/manual restore guard may freeze finance; Data Constitution quarantine never does."""
    try:
        if not bool(globals().get('RESTORE_GUARD_ACTIVE', False)):
            return False
        reason = str(globals().get('RESTORE_GUARD_REASON', '') or '')
        return not reason.startswith('DATA CONSTITUTION:')
    except Exception:
        return False

# --- finance:0067 · from 02_transport_safety.py:3447 · public finance_currency_context ---
def finance_currency_context(chat_id: int, currency: str | None=None) -> dict:
    """Одна оболочка ARS/USD без смешивания режима ARS+эквивалент с USD-контуром."""
    chat_id = int(chat_id)
    store = get_chat_store(chat_id)
    settings = store.setdefault('settings', {})
    requested = str(currency or '').strip().lower()
    if requested in {'usd', 'dollar', 'доллар'}:
        ledger = 'usd'
    elif requested in {'ars', 'peso', 'песо', 'ars_usd'}:
        ledger = 'ars'
    else:
        mode = str(settings.get('currency_mode') or 'ars').strip().lower()
        ledger = 'usd' if mode == 'usd' else 'ars'
    current = _ensure_currency_ledgers(store)
    prefix = ledger
    records_key = 'records' if current == ledger else f'{prefix}_records'
    daily_key = 'daily_records' if current == ledger else f'{prefix}_daily_records'
    return {'chat_id': chat_id, 'store': store, 'currency': ledger, 'symbol': 'USD' if ledger == 'usd' else 'ARS', 'records_key': records_key, 'daily_key': daily_key, 'balance_key': 'balance' if current == ledger else f'{prefix}_balance', 'next_id_key': 'next_id' if current == ledger else f'{prefix}_next_id'}

# --- finance:0068 · from 02_transport_safety.py:3466 · public finance_currency_records ---
def finance_currency_records(chat_id: int, currency: str | None=None) -> list[dict]:
    ctx = finance_currency_context(chat_id, currency)
    return list(ctx['store'].get(ctx['records_key'], []) or [])

# --- finance:0069 · from 02_transport_safety.py:3470 · public finance_currency_daily ---
def finance_currency_daily(chat_id: int, currency: str | None=None) -> dict:
    ctx = finance_currency_context(chat_id, currency)
    return ctx['store'].get(ctx['daily_key'], {}) or {}

# --- finance:0070 · from 02_transport_safety.py:3600 · public _expense_inbox_root ---
def _expense_inbox_root() -> dict:
    root = _root_settings().setdefault('expense_inbox_v141', {})
    root.setdefault('next_id', 1)
    root.setdefault('items', {})
    root.setdefault('evening_enabled', True)
    root.setdefault('evening_hour', 21)
    root.setdefault('evening_last_date', '')
    root.setdefault('quick_message_buttons_enabled', True)
    root.setdefault('recent_event_migration_v142_at', '')
    return root

# --- finance:0071 · from 02_transport_safety.py:3611 · public expense_quick_buttons_enabled ---
def expense_quick_buttons_enabled() -> bool:
    return bool(_expense_inbox_root().get('quick_message_buttons_enabled', True))

# --- finance:0072 · from 02_transport_safety.py:3614 · public expense_quick_buttons_label ---
def expense_quick_buttons_label() -> str:
    return '📱 Отметка: С КНОПКАМИ' if expense_quick_buttons_enabled() else '📱 Отметка: БЕЗ КНОПОК'

# --- finance:0073 · from 02_transport_safety.py:3617 · public toggle_expense_quick_buttons ---
def toggle_expense_quick_buttons() -> bool:
    root = _expense_inbox_root()
    root['quick_message_buttons_enabled'] = not bool(root.get('quick_message_buttons_enabled', True))
    _root_save('expense_quick_buttons_toggle')
    return bool(root['quick_message_buttons_enabled'])

# --- finance:0074 · from 02_transport_safety.py:3623 · public _expense_event_dt ---
def _expense_event_dt(row: dict):
    try:
        value = str((row or {}).get('created_at') or '')
        dt = datetime.fromisoformat(value)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=now_local().tzinfo)
        return dt
    except Exception:
        try:
            return datetime.fromtimestamp(float((row or {}).get('created_ts') or 0), tz=now_local().tzinfo)
        except Exception:
            return None

# --- finance:0075 · from 02_transport_safety.py:3636 · public _v177_legacy_0112_migrate_recent_expense_shortcut_events ---
def _v177_legacy_0112_migrate_recent_expense_shortcut_events(days: int=2, refresh_messages: bool=False) -> dict:
    """Подхватывает быстрые отметки v140/v141 за последние 48 часов."""
    cfg_fn = globals().get('expense_shortcut_config')
    if not callable(cfg_fn):
        return {'imported': 0, 'updated': 0, 'seen': 0}
    try:
        shortcut = cfg_fn(False) or {}
    except Exception:
        shortcut = {}
    cutoff = now_local() - timedelta(days=max(1, int(days or 2)))
    imported = updated = seen = 0
    duplicate = too_old = missing_message_id = refresh_failed = 0
    total_events = len(list(shortcut.get('events') or []))
    for event in list(shortcut.get('events') or []):
        if not isinstance(event, dict) or not event.get('id'):
            continue
        dt = _expense_event_dt(event)
        if dt is None or dt < cutoff:
            too_old += 1
            continue
        seen += 1
        event_id = str(event.get('id'))
        target = int(event.get('target_chat_id') or shortcut.get('target_chat_id') or OWNER_ID or 0)
        before = None
        with _EXPENSE_INBOX_LOCK:
            for existing in (_expense_inbox_root().get('items') or {}).values():
                if str((existing or {}).get('source_event_id') or '') == event_id:
                    before = existing
                    break
        draft = expense_draft_for_event(event_id, target, dt.isoformat(timespec='seconds'))
        if before is None:
            imported += 1
        else:
            duplicate += 1
        mid = int(event.get('telegram_message_id') or 0)
        if not mid:
            missing_message_id += 1
        if mid and int((draft or {}).get('telegram_message_id') or 0) != mid:
            with _EXPENSE_INBOX_LOCK:
                draft['telegram_message_id'] = mid
        if refresh_messages and mid and target:
            try:
                text_fn = globals().get('expense_compact_message_text')
                text = text_fn(dt.isoformat(timespec='seconds')) if callable(text_fn) else f"💸 iPhone · {dt.strftime('%H:%M')}"
                markup = expense_draft_message_keyboard(int(draft.get('id') or 0), target)
                bot.edit_message_text(text, chat_id=target, message_id=mid, reply_markup=markup)
                updated += 1
            except Exception as exc:
                if 'message is not modified' not in str(exc).lower():
                    try:
                        fast_ui_edit_reply_markup(target, mid, expense_draft_message_keyboard(int(draft.get('id') or 0), target), purpose='expense_draft_markup')
                        updated += 1
                    except Exception:
                        refresh_failed += 1
    root = _expense_inbox_root()
    root['recent_event_migration_v142_at'] = now_local().isoformat(timespec='seconds')
    _root_save('expense_recent_event_migration')
    try:
        bot_journal('expense_recent_events_migrated', OWNER_ID, f'total={total_events} seen_48h={seen} imported={imported} existing={duplicate} updated={updated} too_old_or_bad_date={too_old} missing_message_id={missing_message_id} refresh_failed={refresh_failed}')
    except Exception:
        pass
    return {'imported': imported, 'updated': updated, 'seen': seen, 'existing': duplicate, 'too_old': too_old, 'missing_message_id': missing_message_id, 'refresh_failed': refresh_failed}

# --- finance:0076 · from 02_transport_safety.py:3703 · public expense_draft_create ---
def expense_draft_create(source: str, target_chat_id: int, created_at: str | None=None, source_event_id: str='') -> dict:
    with _EXPENSE_INBOX_LOCK:
        root = _expense_inbox_root()
        rid = int(root.get('next_id') or 1)
        root['next_id'] = rid + 1
        row = {'id': rid, 'status': 'open', 'source': str(source or 'manual'), 'source_event_id': str(source_event_id or ''), 'target_chat_id': int(target_chat_id), 'created_at': str(created_at or now_local().isoformat(timespec='seconds')), 'amount': None, 'category': '', 'note': '', 'telegram_message_id': 0}
        root.setdefault('items', {})[str(rid)] = row
        items = root.get('items') or {}
        if len(items) > _EXPENSE_DRAFT_KEEP:
            closed = sorted((x for x in items.values() if x.get('status') != 'open'), key=lambda x: str(x.get('created_at') or ''))
            for old in closed[:max(0, len(items) - _EXPENSE_DRAFT_KEEP)]:
                items.pop(str(old.get('id')), None)
    _root_save('expense_draft_create')
    return row

# --- finance:0077 · from 02_transport_safety.py:3718 · public expense_draft_for_event ---
def expense_draft_for_event(event_id: str, target_chat_id: int, created_at: str | None=None) -> dict:
    with _EXPENSE_INBOX_LOCK:
        for row in (_expense_inbox_root().get('items') or {}).values():
            if str(row.get('source_event_id') or '') == str(event_id):
                return row
    return expense_draft_create('iphone', target_chat_id, created_at, source_event_id=event_id)

# --- finance:0078 · from 02_transport_safety.py:3725 · public expense_draft_set_message ---
def expense_draft_set_message(draft_id: int, message_id: int):
    with _EXPENSE_INBOX_LOCK:
        row = (_expense_inbox_root().get('items') or {}).get(str(int(draft_id)))
        if row:
            row['telegram_message_id'] = int(message_id)
    _root_save('expense_draft_message')

# --- finance:0079 · from 02_transport_safety.py:3732 · public expense_draft_mark ---
def expense_draft_mark(draft_id: int, status: str, amount=None, category: str='', note: str='') -> bool:
    with _EXPENSE_INBOX_LOCK:
        row = (_expense_inbox_root().get('items') or {}).get(str(int(draft_id)))
        if not isinstance(row, dict):
            return False
        row['status'] = str(status)
        if amount is not None:
            row['amount'] = float(amount)
        if category:
            row['category'] = str(category)
        if note:
            row['note'] = str(note)
        row['updated_at'] = now_local().isoformat(timespec='seconds')
    _root_save('expense_draft_mark')
    return True

# --- finance:0080 · from 02_transport_safety.py:3748 · public expense_open_rows ---
def expense_open_rows(limit: int=100) -> list[dict]:
    with _EXPENSE_INBOX_LOCK:
        rows = [copy.deepcopy(x) for x in (_expense_inbox_root().get('items') or {}).values() if str(x.get('status')) == 'open']
    rows.sort(key=lambda x: str(x.get('created_at') or ''), reverse=True)
    return rows[:max(1, int(limit))]

# --- finance:0081 · from 02_transport_safety.py:3754 · public expense_inbox_text ---
def expense_inbox_text() -> str:
    rows = expense_open_rows(100)
    lines = ['⚠️ НЕРАЗОБРАННЫЕ РАСХОДЫ', '', f'Открытых отметок: {len(rows)}', '']
    if not rows:
        lines.append('Все быстрые отметки разобраны.')
    for row in rows[:30]:
        dt = _reminder_parse_dt(row.get('created_at')) if '_reminder_parse_dt' in globals() else None
        label = dt.strftime('%d.%m %H:%M') if dt else str(row.get('created_at') or '')[:16]
        lines.append(f"{row.get('id')}. {label} · {row.get('source')}")
    return '\n'.join(lines)

# --- finance:0082 · from 02_transport_safety.py:3765 · public _today_finance_total ---
def _today_finance_total() -> float:
    total = 0.0
    day = today_key()
    for _cid, store in (data.get('chats', {}) or {}).items():
        if not isinstance(store, dict):
            continue
        for rec in (store.get('daily_records', {}) or {}).get(day, []) or []:
            try:
                amount = float(rec.get('amount', 0) or 0)
                if amount < 0:
                    total += abs(amount)
            except Exception:
                pass
    return total

# --- finance:0083 · from 02_transport_safety.py:3839 · public finance_cache_invalidate ---
def finance_cache_invalidate(chat_id: int | None=None, reason: str=''):
    with _FINANCE_CACHE_LOCK:
        if chat_id is None:
            _FINANCE_VIEW_CACHE.clear()
        else:
            cid = int(chat_id)
            for key in list(_FINANCE_VIEW_CACHE.keys()):
                if isinstance(key, tuple) and cid in key:
                    _FINANCE_VIEW_CACHE.pop(key, None)
    try:
        if reason:
            bot_journal('finance_cache_invalidated', chat_id, reason)
    except Exception:
        pass

# --- finance:0084 · from 02_transport_safety.py:3854 · public finance_cache_get ---
def finance_cache_get(key, builder, ttl: float=20.0):
    now_m = time.monotonic()
    with _FINANCE_CACHE_LOCK:
        row = _FINANCE_VIEW_CACHE.get(key)
        if row and now_m - float(row.get('created') or 0) <= float(ttl):
            return copy.deepcopy(row.get('value'))
    value = builder()
    with _FINANCE_CACHE_LOCK:
        _FINANCE_VIEW_CACHE[key] = {'created': now_m, 'value': copy.deepcopy(value)}
        if len(_FINANCE_VIEW_CACHE) > 400:
            oldest = sorted(_FINANCE_VIEW_CACHE.items(), key=lambda x: float((x[1] or {}).get('created') or 0))[:100]
            for old_key, _ in oldest:
                _FINANCE_VIEW_CACHE.pop(old_key, None)
    return value

# --- finance:0085 · from 02_transport_safety.py:3917 · public _finance_integrity_upload_anchor ---
def _finance_integrity_upload_anchor(anchor: dict) -> None:
    tmp = None
    try:
        if not globals().get('mega_is_configured') or not mega_is_configured():
            return
        remote = f"{str(globals().get('MEGA_BACKUP_DIR') or '').rstrip('/')}/integrity"
        mega_ensure_remote_path(remote)
        os.makedirs(MEGA_LOCAL_TMP_DIR, exist_ok=True)
        name = f"finance_anchor_{int(anchor.get('seq') or 0):08d}_{str(anchor.get('hash') or '')[:12]}.json"
        tmp = os.path.join(MEGA_LOCAL_TMP_DIR, name)
        _atomic_json_dump(tmp, {'kind': 'finance_integrity_anchor', 'bot_version': VERSION, **anchor})
        _mega_run('mega-put', [tmp, remote], check=True, timeout=MEGA_TIMEOUT)
        bot_journal('finance_integrity_anchor_saved', anchor.get('chat_id'), f"seq={anchor.get('seq')} hash={anchor.get('hash')}")
    except Exception as exc:
        log_error(f'finance integrity anchor: {exc}')
    finally:
        try:
            if tmp and os.path.exists(tmp):
                os.remove(tmp)
        except Exception:
            pass

# --- finance:0086 · from 02_transport_safety.py:3939 · public finance_integrity_append ---
def finance_integrity_append(chat_id: int, action: str, record: dict | None=None, details: dict | None=None) -> str:
    cid = int(chat_id)
    with _FINANCE_INTEGRITY_LOCK:
        root = _integrity_root()
        tips = root.setdefault('tips', {})
        prev = str(tips.get(str(cid)) or '')
        root['event_seq'] = int(root.get('event_seq') or 0) + 1
        seq = int(root['event_seq'])
        payload = {'seq': seq, 'chat_id': cid, 'action': str(action), 'record': _integrity_compact_record(record), 'details': _compact_operation_payload(details), 'at': now_local().isoformat(timespec='microseconds'), 'prev': prev}
        digest = hashlib.sha256((prev + '|' + _integrity_canonical(payload)).encode('utf-8')).hexdigest()
        event = dict(payload)
        event['hash'] = digest
        root.setdefault('events', []).append(event)
        tips[str(cid)] = digest
        if len(root['events']) > _FINANCE_INTEGRITY_KEEP:
            root['events'] = root['events'][-_FINANCE_INTEGRITY_KEEP:]
        anchor = None
        if seq % 50 == 0:
            anchor = {'seq': seq, 'chat_id': cid, 'hash': digest, 'at': payload['at']}
            root['anchor'] = dict(anchor)
    _root_save_coalesced('finance_integrity', 1.0)
    try:
        ledger_fn = globals().get('constitution_ledger_append')
        if callable(ledger_fn):
            ledger_fn(cid, str(action), record, details, digest, seq)
    except Exception as _constitution_ledger_exc:
        try:
            constitution_set_quarantine(f'finance ledger append exception seq={seq}: {_constitution_ledger_exc}')
        except Exception:
            pass
        log_error(f'DATA CONSTITUTION ledger append: {_constitution_ledger_exc}')
    if anchor:
        pool = globals().get('GENERAL_TASK_POOL')
        if pool is not None:
            pool.submit_unique(f'integrity-anchor:{seq}', _finance_integrity_upload_anchor, anchor)
    return digest

# --- finance:0087 · from 02_transport_safety.py:3976 · public finance_integrity_verify ---
def finance_integrity_verify(limit: int=5000) -> dict:
    with _FINANCE_INTEGRITY_LOCK:
        events = copy.deepcopy((_integrity_root().get('events') or [])[-max(1, int(limit)):])
    previous_by_chat = {}
    checked = 0
    for event in events:
        cid = str(event.get('chat_id'))
        prev = str(event.get('prev') or '')
        expected_prev = previous_by_chat.get(cid)
        if expected_prev is not None and prev != expected_prev:
            return {'ok': False, 'checked': checked, 'error': f'разрыв цепочки chat={cid}'}
        payload = {k: copy.deepcopy(v) for k, v in event.items() if k != 'hash'}
        digest = hashlib.sha256((prev + '|' + _integrity_canonical(payload)).encode('utf-8')).hexdigest()
        if digest != str(event.get('hash') or ''):
            return {'ok': False, 'checked': checked, 'error': f'неверный hash chat={cid}'}
        previous_by_chat[cid] = digest
        checked += 1
    return {'ok': True, 'checked': checked, 'error': ''}

# --- finance:0088 · from 02_transport_safety.py:3995 · public finance_integrity_text ---
def finance_integrity_text() -> str:
    report = finance_integrity_verify()
    root = _integrity_root()
    return f"🔗 ЦЕЛОСТНОСТЬ ФИНАНСОВ\n\nСобытий в цепочке: {len(root.get('events') or [])}\nПроверено: {report.get('checked', 0)}\nРезультат: {('✅ цепочка цела' if report.get('ok') else '🔴 обнаружена проблема')}\nПодробности: {report.get('error') or 'нет'}"

# --- finance:0089 · from 02_transport_safety.py:4029 · public expense_draft_insert_value ---
def expense_draft_insert_value(draft_id: int) -> str:
    service = f'(EXPENSEDRAFT|{int(draft_id)}| служебное — можно не трогать)'
    return service + '\n\n0 продукты описание'

# --- finance:0090 · from 02_transport_safety.py:4033 · public expense_draft_message_keyboard ---
def expense_draft_message_keyboard(draft_id: int, viewer_chat_id: int):
    if not expense_quick_buttons_enabled():
        return None
    kb = types.InlineKeyboardMarkup(row_width=1)
    kb.row(make_copy_or_inline_button('✍️ Заполнить расход', expense_draft_insert_value(draft_id), viewer_chat_id=viewer_chat_id))
    kb.row(IB('❌ Это не расход', callback_data=f'expense_draft_dismiss:{int(draft_id)}'))
    return kb

# --- finance:0091 · from 02_transport_safety.py:4041 · public build_expense_inbox_keyboard ---
def build_expense_inbox_keyboard(viewer_chat_id: int):
    kb = types.InlineKeyboardMarkup(row_width=1)
    rows = expense_open_rows(30)
    for row in rows:
        try:
            dt = datetime.fromisoformat(str(row.get('created_at') or ''))
            label = dt.strftime('%d.%m %H:%M')
        except Exception:
            label = str(row.get('created_at') or '')[:16]
        kb.row(IB(f"{row.get('id')}. {label} · заполнить", callback_data=f"expense_draft_open:{row.get('id')}"))
    kb.row(IB(evening_reconciliation_label(), callback_data='expense_evening_toggle'))
    kb.row(IB('🌙 Проверить сейчас', callback_data='expense_evening_now'))
    day = get_chat_store(viewer_chat_id).get('current_view_day') or today_key()
    kb.row(IB('🔙 Назад в Инфо', callback_data=f'd:{day}:info'))
    kb.row(IB('⬅️ Назад осн. окно', callback_data=f'd:{day}:back_main'))
    return kb

# --- finance:0092 · from 02_transport_safety.py:4058 · public build_expense_draft_text ---
def build_expense_draft_text(draft_id: int) -> str:
    row = (_expense_inbox_root().get('items') or {}).get(str(int(draft_id))) or {}
    if not row:
        return '❌ Отметка расхода не найдена.'
    try:
        dt = datetime.fromisoformat(str(row.get('created_at') or ''))
        when = dt.strftime('%d.%m.%Y %H:%M')
    except Exception:
        when = str(row.get('created_at') or '—')
    return f"❓ НЕРАЗОБРАННЫЙ РАСХОД №{draft_id}\n\nВремя: {when}\nЧат: {get_chat_display_name(int(row.get('target_chat_id') or 0))}\nИсточник: {row.get('source') or 'быстрая отметка'}\n\nОткройте исходное сообщение в финансовом чате и нажмите «✍️ Заполнить расход»."

# --- finance:0093 · from 02_transport_safety.py:4069 · public build_expense_draft_detail_keyboard ---
def build_expense_draft_detail_keyboard(draft_id: int, viewer_chat_id: int):
    row = (_expense_inbox_root().get('items') or {}).get(str(int(draft_id))) or {}
    kb = types.InlineKeyboardMarkup(row_width=1)
    target = int(row.get('target_chat_id') or viewer_chat_id)
    if target == int(viewer_chat_id):
        kb.row(make_copy_or_inline_button('✍️ Заполнить здесь', expense_draft_insert_value(draft_id), viewer_chat_id=viewer_chat_id))
    kb.row(IB('✅ Уже внесено', callback_data=f'expense_draft_resolved:{int(draft_id)}'))
    kb.row(IB('❌ Это не расход', callback_data=f'expense_draft_dismiss:{int(draft_id)}'))
    kb.row(IB('⬅️ К неразобранным', callback_data='expense_inbox_open'))
    return kb

# --- finance:0094 · from 02_transport_safety.py:4080 · public _expense_draft_input_predicate ---
def _expense_draft_input_predicate(msg) -> bool:
    try:
        return getattr(msg, 'content_type', None) == 'text' and bool(re.search('\\(EXPENSEDRAFT\\|\\d+\\|', str(getattr(msg, 'text', '') or '')))
    except Exception:
        return False

# --- finance:0095 · from 03_diagnostics_memory.py:1551 · public remove_custom_expense_categories ---
def remove_custom_expense_categories(chat_id: int, slugs: set[str]) -> int:
    store = get_chat_store(chat_id)
    settings = store.setdefault('settings', {})
    custom = settings.setdefault('expense_categories_custom', [])
    before = len(custom) if isinstance(custom, list) else 0
    settings['expense_categories_custom'] = [item for item in (custom if isinstance(custom, list) else []) if not (isinstance(item, dict) and str(item.get('slug')) in slugs)]
    store['category_delete_selection'] = []
    removed = before - len(settings['expense_categories_custom'])
    save_data(data)
    if removed:
        schedule_config_backup_for_chats(chat_id)
    return removed

# --- finance:0096 · from 03_diagnostics_memory.py:1564 · public update_custom_expense_category ---
def update_custom_expense_category(chat_id: int, old_slug: str, name: str, keywords: list[str]) -> dict | None:
    store = get_chat_store(chat_id)
    settings = store.setdefault('settings', {})
    name = str(name or '').strip().upper()
    keywords = sorted(set((str(x).strip().lower() for x in keywords or [] if str(x).strip())))
    if str(old_slug) in CATEGORY_BY_SLUG:
        overrides = settings.setdefault('expense_categories_base_overrides', {})
        if not isinstance(overrides, dict):
            overrides = {}
            settings['expense_categories_base_overrides'] = overrides
        overrides[str(old_slug)] = {'name': name, 'keywords': keywords}
        save_data(data)
        schedule_config_backup_for_chats(chat_id)
        bot_journal('base_category_edited', chat_id, f"{old_slug} -> {name}: {', '.join(keywords)}")
        return {'name': name, 'slug': str(old_slug), 'keywords': keywords, 'base': True}
    custom = settings.setdefault('expense_categories_custom', [])
    if not isinstance(custom, list):
        custom = []
        settings['expense_categories_custom'] = custom
    for item in custom:
        if isinstance(item, dict) and str(item.get('slug')) == str(old_slug):
            item['name'] = name
            item['keywords'] = keywords
            item.setdefault('slug', old_slug)
            save_data(data)
            schedule_config_backup_for_chats(chat_id)
            bot_journal('category_edited', chat_id, f"{old_slug} -> {name}: {', '.join(keywords)}")
            return item
    return None

# --- finance:0097 · from 04_messages_features.py:4002 · public _parse_explicit_usd_operations ---
def _parse_explicit_usd_operations(text: str) -> list[dict]:
    """Извлекает явные суммы вида 300 USD / +1700 USD / USD 500 / US$ 500."""
    raw = str(text or '')
    patterns = [re.compile('(?P<num>[+-]?(?:\\d{1,3}(?:[ .]\\d{3})+|\\d+)(?:[.,]\\d+)?)\\s*(?P<cur>USD|U\\$S|US\\$)', re.I), re.compile('(?P<cur>USD|U\\$S|US\\$)\\s*(?P<num>[+-]?(?:\\d{1,3}(?:[ .]\\d{3})+|\\d+)(?:[.,]\\d+)?)', re.I)]
    found = []
    occupied = []
    for pat in patterns:
        for m in pat.finditer(raw):
            span = m.span()
            if any((not (span[1] <= a or span[0] >= b) for a, b in occupied)):
                continue
            try:
                amount = parse_amount(m.group('num'))
            except Exception:
                continue
            found.append({'amount': float(amount), 'span': span, 'raw': m.group(0)})
            occupied.append(span)
    found.sort(key=lambda x: x['span'][0])
    return found

# --- finance:0098 · from 04_messages_features.py:4069 · public handle_finance_text ---
def handle_finance_text(msg):
    """
    Обработка обычного ввода для финучёта.
    Теперь принимает сумму не только из text, но и из caption
    у фото/видео/документов/аудио и т.п.
    """
    chat_id = msg.chat.id
    if globals().get('constitution_finance_write_blocked_v232') and constitution_finance_write_blocked_v232():
        try:
            if _v198_primary_owner_chat(chat_id):
                send_and_auto_delete(chat_id, '🚨 DATA CONSTITUTION: финансовая запись временно отложена до проверки/восстановления. После снятия карантина Durable Tasks попробует безопасно завершить её. /data_constitution', 20)
            else:
                send_owner_technical_alert('🚨 DATA CONSTITUTION: финансовая запись временно отложена до проверки/восстановления. После снятия карантина Durable Tasks попробует безопасно завершить её. /data_constitution', 20, source_chat_id=chat_id)
                send_plain_and_auto_delete(chat_id, '⏳ Финансовая запись временно отложена до восстановления данных.', 8)
        except Exception:
            pass
        return True
    try:
        uid = int(getattr(getattr(msg, 'from_user', None), 'id', 0) or 0)
        if 'safety_profile_new_enabled' in globals() and safety_profile_new_enabled() and (not security_user_allowed(uid, 'finance_input')):
            send_and_auto_delete(chat_id, '⛔ У вас нет права добавлять финансовые записи.', 8)
            try:
                bot_journal('security_finance_input_blocked', chat_id, f'user={uid}', 'WARN')
            except Exception:
                pass
            return True
    except Exception:
        pass
    try:
        uid = int(getattr(getattr(msg, 'from_user', None), 'id', 0) or 0)
        if 'v152_chat_permission_allowed' in globals() and '_v152_actor_is_platform_owner' in globals():
            capability = 'finance.usd' if 'usd_transactions_view_enabled' in globals() and usd_transactions_view_enabled(chat_id) else 'finance.ars'
            if not _v152_actor_is_platform_owner(uid) and (not v152_chat_permission_allowed(chat_id, 'finance.mode') or not v152_chat_permission_allowed(chat_id, capability)):
                try:
                    send_and_auto_delete(chat_id, '⛔ Добавление финансовых операций запрещено правами этого чата.', 8)
                except Exception:
                    pass
                return True
    except Exception:
        pass
    bot_journal('finance_text_start', chat_id, describe_msg_for_log(msg))
    text = _message_text_for_finance(msg)
    if not text:
        return False
    if not is_finance_mode(chat_id):
        return False
    store = get_chat_store(chat_id)
    settings = store.get('settings', {})
    if not settings.get('auto_add', True):
        return False
    if not looks_like_amount(text):
        if text_has_any_digit(text):
            log_error(f'[FINANCE SKIP] amount not recognized: {describe_msg_for_log(msg)} text={text[:220]!r}')
        return False
    try:
        comp = parse_financial_components(text)
        amount, note = (comp['amount'], comp['note'])
    except Exception as e:
        log_error(f'[FINANCE PARSE ERROR] {describe_msg_for_log(msg)} text={text[:220]!r}: {e}')
        return False
    careful_forward = bool(careful_restore_active(chat_id))
    if careful_forward:
        try:
            fn = globals().get('canonical_main_day')
            entry_day = str(fn(chat_id) if callable(fn) else store.get('current_view_day') or finance_today_key(chat_id))[:10]
        except Exception:
            entry_day = str(store.get('current_view_day') or finance_today_key(chat_id))[:10]
        try:
            bot_journal('careful_restore_route', chat_id, f"msg={getattr(msg, 'message_id', 0)} day={entry_day}", 'INFO')
        except Exception:
            pass
    else:
        entry_day = finance_day_key_from_message(msg)
    try:
        rec = add_record_to_chat(chat_id, amount, note, getattr(getattr(msg, 'from_user', None), 'id', 0), source_msg=msg, day_key=entry_day, usd_amount=comp.get('usd_amount'), usd_note=comp.get('usd_note', ''), usd_only=comp.get('usd_only', False), source_finance_text=comp.get('source_finance_text', text))
        if careful_forward:
            careful_restore_touch_value(chat_id, entry_day, msg=msg, record=rec)
        # R15: repaint from the already committed in-memory/SQLite record immediately.
        # Heavy normalize/Gomonk/global finalize remains detached in FINANCE_TASK_POOL.
        try:
            schedule_financial_window_refresh(chat_id, entry_day, reason='record_commit_fast_r15', delay=0.01)
        except Exception:
            pass
        _r77_reconcile = globals().get('schedule_finance_reconcile_r77')
        if callable(_r77_reconcile):
            _r77_reconcile(chat_id, entry_day, reason='record_add', delay=0.45)
        else:
            schedule_finalize(chat_id, entry_day)
        return True
    except Exception as e:
        log_error(f'[FINANCE ADD ERROR] {describe_msg_for_log(msg)} amount={amount} note={note!r}: {e}')
        return False

# --- finance:0099 · from 04_messages_features.py:4162 · public handle_finance_edit ---
def _legacy_s0099_handle_finance_edit(msg):
    chat_id = msg.chat.id
    try:
        uid = int(getattr(getattr(msg, 'from_user', None), 'id', 0) or 0)
        if 'v152_chat_permission_allowed' in globals() and '_v152_actor_is_platform_owner' in globals():
            if not _v152_actor_is_platform_owner(uid) and (not v152_chat_permission_allowed(chat_id, 'finance.edit')):
                try:
                    send_and_auto_delete(chat_id, '⛔ Редактирование операций запрещено правами этого чата.', 8)
                except Exception:
                    pass
                return False
    except Exception:
        pass
    if globals().get('constitution_finance_write_blocked_v232') and constitution_finance_write_blocked_v232():
        try:
            if _v198_primary_owner_chat(chat_id):
                send_and_auto_delete(chat_id, '🚨 DATA CONSTITUTION: финансовые изменения временно заблокированы. Используйте /data_constitution.', 20)
            else:
                send_owner_technical_alert('🚨 DATA CONSTITUTION: финансовые изменения временно заблокированы. Используйте /data_constitution.', 20, source_chat_id=chat_id)
                send_plain_and_auto_delete(chat_id, '⏳ Финансовая запись временно отложена до восстановления данных.', 8)
        except Exception:
            pass
        return True
    text = (msg.text or msg.caption or '').strip()
    store = get_chat_store(chat_id)
    target = find_record_by_message_id(chat_id, int(msg.message_id)) if 'find_record_by_message_id' in globals() else None
    if target is None:
        for r in store.get('records', []):
            try:
                if any(int(r.get(k) or 0) == int(msg.message_id) for k in ('source_msg_id','origin_msg_id','msg_id','source_order_msg_id')):
                    target = r
                    break
            except Exception:
                continue
    if isinstance(target, dict) and '_remember_finance_source_identity_v257' in globals():
        _remember_finance_source_identity_v257(int(chat_id), target, int(msg.message_id), 'records')
    if not target:
        log_info(f'[EDIT-FIN] record not found for msg_id={msg.message_id}')
        return False
    if text and looks_like_amount(text):
        try:
            comp = parse_financial_components(text)
            amount, note = (comp['amount'], comp['note'])
        except Exception:
            comp = {'usd_amount': 0.0, 'usd_note': '', 'usd_only': False}
            amount, note = (0, 'удалено')
    else:
        comp = {'usd_amount': 0.0, 'usd_note': '', 'usd_only': False}
        amount, note = (0, 'удалено')
    _constitution_before = copy.deepcopy(target)
    _next_source_text = str(comp.get('source_finance_text') or text)
    _next_usd_amount = float(comp.get('usd_amount') or 0) if comp.get('usd_amount') is not None else 0.0
    _next_usd_note = str(comp.get('usd_note') or '') if comp.get('usd_amount') is not None else ''
    _next_usd_only = bool(comp.get('usd_only', False)) if comp.get('usd_amount') is not None else False
    _same_edit = (
        float(target.get('amount') or 0) == float(amount or 0)
        and str(target.get('note') or '') == str(note or '')
        and str(target.get('source_finance_text') or '') == _next_source_text
        and float(target.get('usd_amount') or 0) == _next_usd_amount
        and str(target.get('usd_note') or '') == _next_usd_note
        and bool(target.get('usd_only', False)) == _next_usd_only
    )
    if _same_edit:
        log_info(f"[EDIT-FIN] no-op duplicate R{target.get('id')} ARS={float(amount or 0)} USD={_next_usd_amount} note={note}")
        return True
    target['amount'] = amount
    target['note'] = note
    target['source_finance_text'] = _next_source_text
    if comp.get('usd_amount') is not None:
        target['usd_amount'] = float(comp.get('usd_amount') or 0)
        target['usd_note'] = str(comp.get('usd_note') or '')
        target['usd_only'] = bool(comp.get('usd_only', False))
    elif target.get('usd_amount') is not None:
        target['usd_amount'] = 0.0
        target['usd_note'] = ''
        target['usd_only'] = False
    for day, arr in store.get('daily_records', {}).items():
        for r in arr:
            if r.get('id') == target.get('id'):
                r.update(target)
    store['balance'] = sum((r['amount'] for r in store.get('records', [])))
    _snapshot_active_currency_ledger(store, _ensure_currency_ledgers(store))
    log_info(f"[EDIT-FIN] updated record R{target['id']} ARS={float(amount or 0)} USD={float(target.get('usd_amount') or 0)} usd_only={bool(target.get('usd_only', False))} note={note}")
    save_data(data, chat_ids=[int(chat_id)])
    try:
        finance_integrity_append(int(chat_id), 'edit', target, details={'before': _constitution_before, 'source': 'telegram_edited_message'})
    except Exception as _constitution_edit_exc:
        log_error(f'DATA CONSTITUTION edited finance ledger: {_constitution_edit_exc}')
    return True

# --- finance:0100 · from 04_messages_features.py:5289 · public ensure_finance_record_uid ---
def ensure_finance_record_uid(chat_id: int, rec: dict) -> str:
    if not isinstance(rec, dict):
        return ''
    current = str(rec.get('record_uid') or '').strip().upper()
    if re.fullmatch('[A-F0-9]{12}', current):
        return current
    current = _v168_record_uid_seed(int(chat_id), rec)
    rec['record_uid'] = current
    return current

# --- finance:0101 · from 04_messages_features.py:5299 · public find_finance_record_by_uid ---
def find_finance_record_by_uid(chat_id: int, record_uid: str):
    uid = str(record_uid or '').strip().upper()
    if not re.fullmatch('[A-F0-9]{12}', uid):
        return None
    try:
        for _key, rec in _finance_record_lists(get_chat_store(int(chat_id))):
            if isinstance(rec, dict) and ensure_finance_record_uid(int(chat_id), rec) == uid:
                return rec
    except Exception:
        pass
    return None

# --- finance:0102 · from 04_messages_features.py:5355 · public migrate_finance_record_uids ---
def migrate_finance_record_uids(chat_id: int) -> int:
    changed = 0
    seen = set()
    try:
        for _key, rec in _finance_record_lists(get_chat_store(int(chat_id))):
            if not isinstance(rec, dict) or id(rec) in seen:
                continue
            seen.add(id(rec))
            before = str(rec.get('record_uid') or '')
            after = ensure_finance_record_uid(int(chat_id), rec)
            if after and after != before:
                changed += 1
        if changed:
            persist_finance_chat_local_fast(int(chat_id))
    except Exception as exc:
        try:
            log_error(f'v168 UID migration chat={chat_id}: {exc}')
        except Exception:
            pass
    return changed

# --- finance:0103 · from 04_messages_features.py:5926 · public _finance_record_lists ---
def _finance_record_lists(store: dict):
    """Active + persistent currency ledgers, active first; duplicate objects are skipped."""
    seen = set()
    for key in ('records', 'ars_records', 'usd_records'):
        arr = store.get(key, []) or []
        if not isinstance(arr, list):
            continue
        for rec in arr:
            if not isinstance(rec, dict):
                continue
            oid = id(rec)
            if oid in seen:
                continue
            seen.add(oid)
            yield (key, rec)

# --- finance:0104 · from 04_messages_features.py:5942 · public _finance_source_index_v257 ---
def _finance_source_index_v257(store: dict) -> dict:
    idx = store.setdefault('_finance_source_index_v257', {})
    if not isinstance(idx, dict):
        idx = {}
        store['_finance_source_index_v257'] = idx
    return idx

# --- finance:0105 · from 04_messages_features.py:5967 · public _remember_finance_source_identity_v257 ---
def _remember_finance_source_identity_v257(chat_id: int, rec: dict, msg_id: int | None=None, ledger: str='records') -> bool:
    if not isinstance(rec, dict):
        return False
    try:
        cid = int(chat_id)
        mid = int(msg_id or 0)
    except Exception:
        return False
    if not mid:
        mids = _record_message_ids_v257(rec)
        mid = min(mids) if mids else 0
    if not mid:
        return False
    store = get_chat_store(cid)
    try:
        uid = ensure_finance_record_uid(cid, rec) if 'ensure_finance_record_uid' in globals() else str(rec.get('record_uid') or '')
    except Exception:
        uid = str(rec.get('record_uid') or '')
    row = {'record_uid': str(uid or ''), 'id': int(rec.get('id') or 0), 'ledger': str(ledger or 'records'), 'operation_key': str(rec.get('operation_key') or '')}
    _finance_source_index_v257(store)[str(mid)] = row
    # Heal old restored records: message identity is immutable and must not vanish.
    for key in ('source_msg_id', 'origin_msg_id', 'msg_id'):
        if not rec.get(key): rec[key] = mid
    if not rec.get('source_order_msg_id'): rec['source_order_msg_id'] = mid
    if not rec.get('operation_key') and 'finance_operation_key' in globals():
        try: rec['operation_key'] = finance_operation_key(cid, mid, 'main')
        except Exception: pass
    return True

# --- finance:0106 · from 04_messages_features.py:6029 · public migrate_finance_source_index_v257 ---
def migrate_finance_source_index_v257(chat_id: int) -> int:
    cid=int(chat_id); store=get_chat_store(cid); changed=0
    for key, rec in _finance_record_lists(store):
        mids=_record_message_ids_v257(rec)
        for mid in mids:
            before=dict(_finance_source_index_v257(store).get(str(mid)) or {})
            if _remember_finance_source_identity_v257(cid, rec, mid, key):
                after=_finance_source_index_v257(store).get(str(mid)) or {}
                if before != after: changed += 1
    return changed

# --- finance:0107 · from 04_messages_features.py:6755 · public _message_text_for_finance ---
def _message_text_for_finance(msg) -> str:
    return (getattr(msg, 'text', None) or getattr(msg, 'caption', None) or '').strip()

# --- finance:0108 · from 05_finance_ui.py:34 · public _gomonk_is_usd_view ---
def _gomonk_is_usd_view(chat_id: int) -> bool:
    return _gomonk_currency(chat_id) == 'usd'

# --- finance:0109 · from 05_finance_ui.py:330 · public usd_display_enabled ---
def usd_display_enabled(chat_id: int) -> bool:
    """Совместимость со старым v86: True для ARS-USD и USD."""
    return currency_mode(int(chat_id)) != 'ars'

# --- finance:0110 · from 05_finance_ui.py:334 · public set_usd_display_enabled ---
def set_usd_display_enabled(chat_id: int, enabled: bool):
    set_currency_mode(int(chat_id), 'ars_usd' if enabled else 'ars')

# --- finance:0111 · from 05_finance_ui.py:337 · public toggle_usd_display ---
def toggle_usd_display(chat_id: int) -> bool:
    new_mode = 'ars' if currency_mode(int(chat_id)) != 'ars' else 'ars_usd'
    set_currency_mode(int(chat_id), new_mode)
    return new_mode != 'ars'

# --- finance:0112 · from 05_finance_ui.py:342 · public usd_display_label ---
def usd_display_label(chat_id: int) -> str:
    return currency_mode_label(chat_id)

# --- finance:0113 · from 05_finance_ui.py:360 · public fmt_usd_compact ---
def fmt_usd_compact(amount: float, rate_info: dict | None, signed: bool=True, absolute: bool=False) -> str:
    """Конвертация ARS→USD для режима ARS-USD."""
    if not rate_info or not rate_info.get('rate'):
        return '$—'
    amount = float(amount or 0)
    value = int(round(abs(amount) / float(rate_info['rate'])))
    if absolute or not signed:
        sign = ''
    else:
        sign = '+' if amount >= 0 else '-'
    return f'{sign}${value:,}'.replace(',', ' ')

# --- finance:0114 · from 05_finance_ui.py:372 · public fmt_usd_native ---
def fmt_usd_native(amount: float, signed: bool=True, absolute: bool=False) -> str:
    """Формат суммы, которая уже хранится в отдельном USD-контуре."""
    amount = float(amount or 0)
    value = abs(amount)
    if abs(value - round(value)) < 1e-09:
        body = f'{int(round(value)):,}'.replace(',', ' ')
    else:
        body = f'{value:,.2f}'.replace(',', ' ').rstrip('0').rstrip('.')
    sign = '' if absolute or not signed else '+' if amount >= 0 else '-'
    return f'{sign}${body}'

# --- finance:0115 · from 05_finance_ui.py:513 · public _opening_balance_before_day ---
def _opening_balance_before_day(store: dict, day_key: str, chat_id: int | None=None) -> float:
    """Official opening balance before ``day_key``.

    v195 keeps ONE runtime authority with Excel/Google: when the canonical export
    helper is loaded, the remaining window calls that exact helper too.  The
    fallback below exists only for bootstrap/isolated tests and sums the stored
    accounting ledger losslessly; it never re-parses historical source text.
    """
    canonical = globals().get('_excel_canonical_opening_balance')
    if callable(canonical) and chat_id is not None:
        try:
            return float(canonical(int(chat_id), 'ars', str(day_key or '')[:10], 0, False))
        except Exception:
            pass
    total = 0.0
    target = str(day_key or '')[:10]
    try:
        rows = sorted(store.get('records', []) or [], key=record_sort_key)
    except Exception:
        rows = list(store.get('records', []) or [])
    for rec in rows:
        if not isinstance(rec, dict):
            continue
        try:
            if _record_day_key(rec) >= target:
                break
            total += float(rec.get('amount', 0) or 0)
        except Exception:
            continue
    return float(total)

# --- finance:0116 · from 05_finance_ui.py:725 · public usd_rate_cached ---
def usd_rate_cached(force: bool=False) -> dict | None:
    gs = data.setdefault('_global_settings', {})
    cache = gs.get('usd_rate_cache') if isinstance(gs.get('usd_rate_cache'), dict) else {}
    gate = globals().get('external_access_allowed_v233')
    if callable(gate) and (not gate('currency')):
        try:
            logger_fn = globals().get('external_block_log_v233')
            if callable(logger_fn):
                logger_fn('currency', 'usd_rate')
        except Exception:
            pass
        return cache if cache.get('rate') else None
    age = time.time() - float(cache.get('fetched_ts', 0) or 0)
    if not force and cache.get('rate') and (age < USD_RATE_CACHE_SECONDS):
        return cache
    # R24: FAST/UI window construction never waits for Redis or DolarAPI. A stale
    # local rate is good enough for the first render; refresh happens after it.
    _r24_thread_name = threading.current_thread().name.casefold()
    _r24_ui_thread = _r24_thread_name.startswith(('fast-ui', 'ui-', 'start-ui', 'window-render'))
    if not force and _r24_ui_thread:
        try:
            submit_unique = getattr(GENERAL_TASK_POOL, 'submit_unique', None)
            if callable(submit_unique):
                submit_unique('r24-usd-rate-refresh', usd_rate_cached, True)
            else:
                GENERAL_TASK_POOL.submit('r24-usd-rate-refresh', usd_rate_cached, True)
        except Exception:
            pass
        return cache if cache.get('rate') else None
    if not force:
        kv_get = globals().get('kv_get_json_v248')
        if callable(kv_get):
            try:
                shared_cache = kv_get('cache:usd_rate', None)
                if isinstance(shared_cache, dict) and shared_cache.get('rate'):
                    shared_age = time.time() - float(shared_cache.get('fetched_ts', 0) or 0)
                    if shared_age < USD_RATE_CACHE_SECONDS:
                        gs['usd_rate_cache'] = dict(shared_cache)
                        return dict(shared_cache)
            except Exception:
                pass
    if threading.current_thread().name.startswith('webhook'):
        GENERAL_TASK_POOL.submit('usd-rate-refresh', usd_rate_cached, True)
        return cache if cache.get('rate') else None
    try:
        resp = requests.get(USD_RATE_URL, timeout=8)
        resp.raise_for_status()
        payload = resp.json()
        rate = float(payload.get('venta') or payload.get('promedio') or payload.get('compra') or 0)
        if rate <= 0:
            raise ValueError('курс venta отсутствует')
        cache = {'rate': rate, 'source': str(payload.get('nombre') or payload.get('casa') or 'DolarAPI dólar blue'), 'fetched_at': str(payload.get('fechaActualizacion') or now_local().isoformat(timespec='seconds')), 'fetched_ts': time.time(), 'url': USD_RATE_URL}
        gs['usd_rate_cache'] = cache
        kv_set = globals().get('kv_set_json_v248')
        if callable(kv_set):
            try:
                kv_set('cache:usd_rate', cache, USD_RATE_CACHE_SECONDS)
            except Exception:
                pass
        save_data(data, root_only=True)
        bot_journal('usd_rate_updated', None, f"rate={rate} source={cache['source']} shared_kv={bool(callable(kv_set))}")
        return cache
    except Exception as e:
        bot_journal('usd_rate_error', None, str(e), 'WARN')
        return cache if cache.get('rate') else None

# --- finance:0117 · from 05_finance_ui.py:791 · public _usd_rate_refresh_tick ---
def _usd_rate_refresh_tick():
    try:
        gate = globals().get('external_access_allowed_v233')
        if not (callable(gate) and (not gate('currency'))):
            usd_rate_cached(force=True)
    except Exception:
        pass
    finally:
        try:
            DELAYED_SCHEDULER.schedule('usd-rate-refresh', USD_RATE_CACHE_SECONDS, _usd_rate_refresh_tick)
        except Exception:
            pass

# --- finance:0118 · from 05_finance_ui.py:804 · public _usd_rate_refresh_loop ---
def _usd_rate_refresh_loop():
    return _usd_rate_refresh_tick()

# --- finance:0119 · from 05_finance_ui.py:807 · public fmt_usd_from_ars ---
def fmt_usd_from_ars(amount: float, rate_info: dict | None) -> str:
    """Совместимый короткий USD-формат для старых окон."""
    return fmt_usd_compact(amount, rate_info, signed=False, absolute=True)

# --- finance:0120 · from 05_finance_ui.py:811 · public usd_transactions_view_enabled ---
def usd_transactions_view_enabled(chat_id: int) -> bool:
    try:
        return bool(get_chat_store(int(chat_id)).setdefault('settings', {}).get('usd_transactions_view', False))
    except Exception:
        return False

# --- finance:0121 · from 05_finance_ui.py:817 · public set_usd_transactions_view ---
def _legacy_s0121_set_usd_transactions_view(chat_id: int, enabled: bool):
    store = get_chat_store(int(chat_id))
    store.setdefault('settings', {})['usd_transactions_view'] = bool(enabled)
    save_data(data, chat_ids=[int(chat_id)])
    schedule_config_backup_for_chats(int(chat_id))

# --- finance:0122 · from 05_finance_ui.py:823 · public toggle_usd_transactions_view ---
def toggle_usd_transactions_view(chat_id: int) -> bool:
    new_value = not usd_transactions_view_enabled(int(chat_id))
    set_usd_transactions_view(int(chat_id), new_value)
    return new_value

# --- finance:0123 · from 05_finance_ui.py:828 · public usd_transactions_toggle_label ---
def usd_transactions_toggle_label(chat_id: int) -> str:
    return '🇦🇷 ARS операции' if usd_transactions_view_enabled(int(chat_id)) else '💵 USD операции'

# --- finance:0124 · from 05_finance_ui.py:832 · public ensure_usd_migration_for_chat ---
def ensure_usd_migration_for_chat(chat_id: int) -> int:
    """OCH12.31 safe legacy USD enrichment.

    Historical ARS rows are immutable business facts.  The old v93 heuristic could
    reconstruct a synthetic string from ``record.amount`` merely because the note
    contained ``usd`` and then overwrite amount/note, recalculate the balance and
    renumber R-ids.  That turned legitimate ARS income into USD-only rows.

    12.31 only enriches USD metadata when the *original* source_finance_text already
    contains an explicit numeric USD token and parsing it preserves the stored ARS
    amount.  Existing amount, note, id/short-id and balance are never modified here.
    """
    cid = int(chat_id)
    changed = 0
    skipped_unsafe = 0
    with locked_chat(cid):
        store = get_chat_store(cid)
        settings = store.setdefault('settings', {})
        if settings.get('usd_transactions_migrated_v1231'):
            return 0
        for rec in store.get('records', []) or []:
            if not isinstance(rec, dict) or rec.get('usd_amount') is not None:
                continue
            source = str(rec.get('source_finance_text') or '').strip()
            if not source:
                continue
            # Never infer USD from a free-form note such as "приход от обмена usd".
            # A number must be physically attached to USD/УСД/$ in the preserved
            # original source text.  This deliberately prefers missing old USD
            # metadata over corrupting an already-accounted ARS transaction.
            if not (USD_EXPLICIT_AFTER_RE.search(source) or USD_EXPLICIT_PREFIX_RE.search(source)):
                continue
            try:
                comp = parse_financial_components(source) or {}
                parsed_usd = comp.get('usd_amount')
                if parsed_usd is None:
                    continue
                old_amount = float(rec.get('amount', 0) or 0)
                parsed_ars = float(comp.get('amount', 0) or 0)
                parsed_usd_only = bool(comp.get('usd_only', False))
            except Exception:
                continue
            # Safe cases only: either the parser reproduces the exact ARS amount, or
            # the stored row is already zero-ARS and the source is genuinely USD-only.
            same_ars = abs(parsed_ars - old_amount) <= 0.01
            safe_usd_only = parsed_usd_only and abs(old_amount) <= 0.01
            if not (same_ars or safe_usd_only):
                skipped_unsafe += 1
                continue
            rec['usd_amount'] = float(parsed_usd or 0)
            rec['usd_note'] = str(comp.get('usd_note') or '')
            rec['usd_only'] = bool(parsed_usd_only and abs(old_amount) <= 0.01)
            changed += 1
        # Preserve the old flag for compatibility, but use a new marker so databases
        # restored from pre-v93 snapshots execute this safe migration exactly once.
        settings['usd_transactions_migrated_v93'] = True
        settings['usd_transactions_migrated_v1231'] = True
    # Persistence is intentionally outside the chat lock.  No balance/ID rebuild is
    # needed because ARS business fields are untouched.
    save_data(data, chat_ids=[cid])
    try:
        bot_journal('usd_v1231_safe_migration', cid, f'enriched={changed}; skipped_unsafe={skipped_unsafe}; ars_immutable=1')
    except Exception:
        pass
    return changed

# --- finance:0125 · from 05_finance_ui.py:899 · public usd_records_for_month ---
def usd_records_for_month(chat_id: int, month_key: str) -> list[dict]:
    ensure_usd_migration_for_chat(int(chat_id))
    store = get_chat_store(int(chat_id))
    records = list(store.get('records', []) or [])
    key = ('usd_month', int(chat_id), str(month_key)[:7], len(records), int(store.get('next_id', 0) or 0))

    def _build():
        rows = []
        for rec in records:
            try:
                if not _record_day_key(rec).startswith(str(month_key)[:7]):
                    continue
                usd_amount = float(rec.get('usd_amount', 0) or 0)
                if not usd_amount:
                    continue
                rows.append(rec)
            except Exception:
                continue
        return sorted(rows, key=record_sort_key)
    return finance_cache_get(key, _build, ttl=30.0) if 'finance_cache_get' in globals() else _build()

# --- finance:0126 · from 05_finance_ui.py:920 · public usd_balance_for_chat ---
def usd_balance_for_chat(chat_id: int) -> float:
    ensure_usd_migration_for_chat(int(chat_id))
    store = get_chat_store(int(chat_id))
    if '_usd_balance_cache_r16' in store:
        try: return float(store.get('_usd_balance_cache_r16', 0) or 0)
        except Exception: store.pop('_usd_balance_cache_r16', None)
    total = 0.0
    for rec in store.get('records', []) or []:
        try: total += float(rec.get('usd_amount', 0) or 0)
        except Exception: pass
    store['_usd_balance_cache_r16'] = float(total)
    return float(total)

# --- finance:0127 · from 05_finance_ui.py:933 · public usd_records_for_day ---
def usd_records_for_day(chat_id: int, day_key: str) -> list[dict]:
    ensure_usd_migration_for_chat(int(chat_id))
    store = get_chat_store(int(chat_id))
    records = list(store.get('records', []) or [])
    key = ('usd_day', int(chat_id), str(day_key), len(records), int(store.get('next_id', 0) or 0))

    def _build():
        return [r for r in financial_view_records_for_day_store(store, str(day_key)) if abs(float(r.get('usd_amount', 0) or 0)) > 0]
    return finance_cache_get(key, _build, ttl=20.0) if 'finance_cache_get' in globals() else _build()

# --- finance:0128 · from 05_finance_ui.py:943 · public render_usd_day_window ---
def render_usd_day_window(chat_id: int, day_key: str):
    """Daily USD shell: same navigation/sections as ARS, but every value comes from usd_amount/usd_note."""
    ensure_usd_migration_for_chat(int(chat_id))
    store = get_chat_store(int(chat_id))
    recs = usd_records_for_day(int(chat_id), day_key)
    d = datetime.strptime(day_key, '%Y-%m-%d')
    wd = ['пн', 'вт', 'ср', 'чт', 'пт', 'сб', 'вс'][d.weekday()]
    t = now_local()
    td = t.strftime('%Y-%m-%d')
    yd = (t - timedelta(days=1)).strftime('%Y-%m-%d')
    tm = (t + timedelta(days=1)).strftime('%Y-%m-%d')
    tag = 'сегодня' if day_key == td else 'вчера' if day_key == yd else 'завтра' if day_key == tm else ''
    dk = fmt_date_ddmmyy(day_key)
    label = f'{dk} ({tag}, {wd})' if tag else f'{dk} ({wd})'
    header = ['💵 USD операции', f'📅 {label}', '']
    total_income = 0.0
    total_expense = 0.0
    record_lines = []
    for rec in recs:
        amt = float(rec.get('usd_amount', 0) or 0)
        if amt >= 0:
            total_income += amt
        else:
            total_expense += -amt
        sid = str(rec.get('usd_short_id') or f"U{rec.get('id', '')}")
        note = html.escape(str(rec.get('usd_note') or rec.get('note') or ''))
        sign = '+' if amt >= 0 else '-'
        record_lines.append(f'{sid} {sign}${fmt_num_plain(abs(amt))} {note}'.rstrip())
    day_balance = financial_view_balance_through_day(store, day_key)
    total_balance = financial_view_total_balance(store)
    footer = ['']
    if recs:
        footer.append(f'📉 Расход за день: -${fmt_num_plain(total_expense)}')
        footer.append(f'📈 Приход за день: +${fmt_num_plain(total_income)}')
    footer.append(f"📆 Остаток на конец дня: {('+' if day_balance >= 0 else '-')}${fmt_num_plain(abs(day_balance))}")
    footer.append(f"🏦 Остаток по чату: {('+' if total_balance >= 0 else '-')}${fmt_num_plain(abs(total_balance))}")
    footer.extend(gomonk_summary_lines(chat_id, 'usd'))
    total = total_income - total_expense
    if not record_lines:
        return (wm_common('\n'.join(header + ['Нет USD-записей за этот день.'] + footer), 1, html_mode=True), total)
    if effective_main_financial_value_buttons_enabled(int(chat_id)):
        hint = [f'💳 USD-записей за день: {len(recs)}', 'Нажмите сумму-кнопку ниже, чтобы изменить запись.']
        return (wm_common('\n'.join(header + hint + footer), 1, html_mode=True), total)
    hidden = 0
    visible = list(record_lines)
    if len(visible) > DAY_WINDOW_MAX_RECORDS:
        hidden = len(visible) - DAY_WINDOW_MAX_RECORDS
        visible = visible[-DAY_WINDOW_MAX_RECORDS:]
    while True:
        prefix = [f'… скрыто ранних записей: {hidden}', ''] if hidden > 0 else []
        text = '\n'.join(header + prefix + visible + footer)
        if len(text) <= DAY_WINDOW_MAX_CHARS or len(visible) <= 5:
            return (wm_common(text[:DAY_WINDOW_MAX_CHARS], 1, html_mode=True), total)
        hidden += 1
        visible = visible[1:]

# --- finance:0129 · from 05_finance_ui.py:999 · public _v177_legacy_0163_render_usd_month_window ---
def _v177_legacy_0163_render_usd_month_window(chat_id: int, day_key: str):
    month_key = str(day_key or today_key())[:7]
    try:
        month_dt = datetime.strptime(month_key + '-01', '%Y-%m-%d')
        month_label = month_dt.strftime('%m.%Y')
    except Exception:
        month_label = month_key
    rows = usd_records_for_month(int(chat_id), month_key)
    income = sum((float(r.get('usd_amount', 0) or 0) for r in rows if float(r.get('usd_amount', 0) or 0) > 0))
    expense = sum((abs(float(r.get('usd_amount', 0) or 0)) for r in rows if float(r.get('usd_amount', 0) or 0) < 0))
    lines = [f'💵 USD операции за {month_label}', '']
    if rows:
        for rec in rows:
            amt = float(rec.get('usd_amount', 0) or 0)
            sid = str(rec.get('usd_short_id') or rec.get('short_id') or f"U{rec.get('id', '')}")
            dk = fmt_date_ddmmyy(_record_day_key(rec))
            note = html.escape(str(rec.get('usd_note') or rec.get('note') or ''))
            sign = '+' if amt >= 0 else '-'
            val = fmt_num_plain(abs(amt))
            lines.append(f'{sid} {dk} {sign}${val} {note}'.rstrip())
    else:
        lines.append('Нет USD-транзакций за этот месяц.')
    lines.extend(['', f'📉 Расход за месяц: -${fmt_num_plain(expense)}', f'📈 Приход за месяц: +${fmt_num_plain(income)}', f"💵 Итог месяца: {('+' if income - expense >= 0 else '-')}${fmt_num_plain(abs(income - expense))}", f"🏦 USD остаток по чату: {('+' if usd_balance_for_chat(chat_id) >= 0 else '-')}${fmt_num_plain(abs(usd_balance_for_chat(chat_id)))}"])
    return (wm_common('\n'.join(lines), 1, html_mode=True), income - expense)

# --- finance:0130 · from 05_finance_ui.py:1028 · public _v177_legacy_0164_build_usd_month_keyboard ---
def _v177_legacy_0164_build_usd_month_keyboard(day_key: str):
    try:
        dt = datetime.strptime(str(day_key)[:10], '%Y-%m-%d').replace(day=1)
    except Exception:
        dt = now_local().replace(day=1)
    prev_dt = (dt - timedelta(days=1)).replace(day=1)
    next_dt = (dt.replace(day=28) + timedelta(days=4)).replace(day=1)
    current_month = now_local().strftime('%Y-%m')
    kb = types.InlineKeyboardMarkup(row_width=3)
    nav = [IB('⬅️ Пред. месяц', callback_data=f"d:{prev_dt.strftime('%Y-%m-01')}:usd_month")]
    if dt.strftime('%Y-%m') != current_month:
        nav.append(IB('📅 Этот месяц', callback_data=f'd:{today_key()}:usd_month'))
    nav.append(IB('След. месяц ➡️', callback_data=f"d:{next_dt.strftime('%Y-%m-01')}:usd_month"))
    kb.row(*nav)
    kb.row(IB('⬅️ Назад осн. окно', callback_data=f'd:{str(day_key)[:10]}:back_main'))
    return kb

# --- finance:0131 · from 05_finance_ui.py:1881 · public compose_usd_edit_insert_value ---
def compose_usd_edit_insert_value(target_chat_id: int, rid: int, day_key: str, amount, note: str='') -> str:
    value = compose_edit_input_value(amount, note)
    meta = f'{USD_DIRECT_EDIT_TOKEN}|{int(target_chat_id)}|{int(rid)}|{str(day_key)[:10]}|'
    return f'({meta} служебное — можно не трогать)\n\n{value}'

# --- finance:0132 · from 05_finance_ui.py:2566 · public finance_mode_compact_icon ---
def finance_mode_compact_icon(chat_id: int) -> str:
    """v108: hidden finance and visible auto-window mode are shown independently."""
    try:
        if not is_finance_mode(chat_id):
            return '⬜'
        hidden_prefix = '🙈' if is_hidden_finance_mode(chat_id) else ''
        mode = finance_window_mode(chat_id)
        if mode == 'first':
            return hidden_prefix + '✅🥇'
        if mode == 'open':
            return hidden_prefix + '✅3️⃣'
        if mode == 'normal':
            return hidden_prefix + '✅🔟'
        return hidden_prefix + '✅'
    except Exception:
        return '⬜'

# --- finance:0133 · from 05_finance_ui.py:2583 · public finance_mode_state_lines ---
def finance_mode_state_lines(chat_id: int) -> list[str]:
    """F39/v108: hidden accounting is independent; exactly one of the three visible modes may be active, or none."""
    fin_on = is_finance_mode(chat_id)
    hidden_on = bool(fin_on and is_hidden_finance_mode(chat_id))
    mode = finance_window_mode(chat_id) if fin_on else 'off'
    return [f'Чат: {chat_button_title(chat_id)}', '', f"{('✅' if fin_on else '⬜')} Фин режим", f"{('✅🙈' if hidden_on else '⬜🙈')} Скрытые финансы — независимо", f"{('✅🔟' if fin_on and mode == 'normal' else '⬜')} Как обычно — окно через 10 сообщений", f"{('✅3️⃣' if fin_on and mode == 'open' else '⬜')} Быстрый остаток — открывать окно", f"{('✅🥇' if fin_on and mode == 'first' else '⬜')} Быстрый остаток — всегда первым", '', 'Повторное нажатие активного режима окна выключает только окно; скрытые финансы остаются.']

# --- finance:0134 · from 05_finance_ui.py:2590 · public _v177_legacy_0196_build_finance_toggle_chat_menu ---
def _v177_legacy_0196_build_finance_toggle_chat_menu(day_key: str):
    kb = types.InlineKeyboardMarkup(row_width=2)
    known = collect_forward_menu_chats()
    items = {}
    for cid, ch in known.items():
        try:
            int_cid = int(cid)
        except Exception:
            continue
        items[int_cid] = ch.get('title') or get_chat_display_name(int_cid)
    if OWNER_ID:
        try:
            owner_id = int(OWNER_ID)
            items.setdefault(owner_id, get_chat_display_name(owner_id))
        except Exception:
            pass
    buttons = []
    for int_cid, title in sorted(items.items(), key=lambda x: x[1].lower()):
        if is_chat_bot_removed(int_cid) and (not (OWNER_ID and str(int_cid) == str(OWNER_ID))):
            continue
        icon = finance_mode_compact_icon(int_cid)
        buttons.append(IB(f'{icon} {chat_button_title(int_cid, title)}', callback_data=f'd:{day_key}:fw_finmode_pick_{int_cid}'))
    add_buttons_in_rows(kb, buttons, 2)
    kb.row(IB('ℹ️ Описание чатов', callback_data='chat_desc_menu:finmode'))
    kb.row(IB('🔙 Назад', callback_data=f'd:{day_key}:back_main'))
    return kb

# --- finance:0135 · from 05_finance_ui.py:2621 · public build_quick_balance_chat_menu ---
def build_quick_balance_chat_menu(day_key: str):
    kb = types.InlineKeyboardMarkup(row_width=2)
    known = collect_forward_menu_chats()
    items = {}
    for cid, ch in known.items():
        try:
            int_cid = int(cid)
        except Exception:
            continue
        items[int_cid] = ch.get('title') or get_chat_display_name(int_cid)
    owner_item = None
    if OWNER_ID:
        try:
            owner_id = int(OWNER_ID)
            owner_item = (owner_id, get_chat_display_name(owner_id))
            items.setdefault(owner_id, owner_item[1])
        except Exception:
            owner_item = None
    buttons = []
    for int_cid, title in sorted(items.items(), key=lambda x: x[1].lower()):
        if owner_item and int_cid == owner_item[0]:
            continue
        mode = finance_window_mode(int_cid) if is_finance_mode(int_cid) else 'off'
        icon = '✅🥇' if mode == 'first' else '✅3️⃣' if mode == 'open' else '✅🔟' if mode == 'normal' else '⬜'
        buttons.append(IB(f'{icon} {chat_button_title(int_cid, title)}', callback_data=f'd:{day_key}:qb_cfg_{int_cid}'))
    add_buttons_in_rows(kb, buttons, 2)
    if owner_item:
        mode = finance_window_mode(owner_item[0]) if is_finance_mode(owner_item[0]) else 'off'
        icon = '✅🥇' if mode == 'first' else '✅3️⃣' if mode == 'open' else '✅🔟' if mode == 'normal' else '⬜'
        kb.row(IB(f'{icon} {chat_button_title(owner_item[0], owner_item[1])}', callback_data=f'd:{day_key}:qb_cfg_{owner_item[0]}'))
    kb.row(IB('🔙 Назад', callback_data=f'd:{day_key}:back_main'))
    return kb

# --- finance:0136 · from 05_finance_ui.py:2654 · public _v177_legacy_0198_build_quick_balance_mode_menu ---
def _v177_legacy_0198_build_quick_balance_mode_menu(day_key: str, target_chat_id: int):
    kb = types.InlineKeyboardMarkup(row_width=1)
    fin_on = is_finance_mode(target_chat_id)
    hidden_on = bool(fin_on and is_hidden_finance_mode(target_chat_id))
    mode = finance_window_mode(target_chat_id) if fin_on else 'off'
    fin_icon = '✅' if fin_on else '⬜'
    normal_icon = '✅🔟' if fin_on and mode == 'normal' else '⬜'
    open_icon = '✅3️⃣' if fin_on and mode == 'open' else '⬜'
    first_icon = '✅🥇' if fin_on and mode == 'first' else '⬜'
    hidden_icon = '✅🙈' if hidden_on else '⬜🙈'
    finwin_icon = '🪟✅' if fin_on else '🪟⬜'
    kb.row(IB(f'{fin_icon} Фин режим ВКЛ/ВЫКЛ', callback_data=f'd:{day_key}:fin_mode_toggle_{target_chat_id}'))
    kb.row(IB(f'{normal_icon} Как обычно — фин окно через 10 сообщений', callback_data=f'd:{day_key}:qb_mode_normal_{target_chat_id}'))
    kb.row(IB(f'{open_icon} Фин режим + быстрый остаток: открывать окно', callback_data=f'd:{day_key}:qb_mode_open_{target_chat_id}'))
    kb.row(IB(f'{first_icon} Фин режим + быстрый остаток: всегда первым', callback_data=f'd:{day_key}:qb_mode_first_{target_chat_id}'))
    kb.row(IB(f'{hidden_icon} Скрытые финансы', callback_data=f'd:{day_key}:qb_hidden_toggle_{target_chat_id}'), IB(f'{finwin_icon} Фин окно', callback_data=f'd:{day_key}:qb_finwin_open_{target_chat_id}'))
    kb.row(IB('🔙 Назад к чатам', callback_data=f'd:{day_key}:forward_finmode_menu'))
    return kb

# --- finance:0137 · from 05_finance_ui.py:2677 · public _v177_legacy_0199_build_finance_mode_config_menu ---
def _v177_legacy_0199_build_finance_mode_config_menu(day_key: str, target_chat_id: int):
    """Подменю после: Фин режим → выбор чата. Объединяет финрежим и старый быстрый остаток."""
    return build_quick_balance_mode_menu(day_key, target_chat_id)

# --- finance:0138 · from 05_finance_ui.py:2685 · public build_finance_mode_config_text ---
def build_finance_mode_config_text(target_chat_id: int) -> str:
    return '💰 Фин режим / В24\n' + '\n'.join(finance_mode_state_lines(target_chat_id))

# --- finance:0139 · from 05_finance_ui.py:2688 · public _canon_apply_finance_window_mode_choice__001 ---
def _canon_apply_finance_window_mode_choice__001(chat_id: int, selected_mode: str) -> str:
    """F39/v108: the three visible modes are mutually exclusive; clicking the active one turns only windows off."""
    chat_id = int(chat_id)
    selected_mode = str(selected_mode or 'off')
    if selected_mode not in {'normal', 'open', 'first'}:
        selected_mode = 'off'
    was_finance = is_finance_mode(chat_id)
    if not was_finance:
        set_finance_mode(chat_id, True)
        set_hidden_finance_mode(chat_id, True)
    current = finance_window_mode(chat_id)
    if current == selected_mode:
        set_finance_window_mode(chat_id, 'off', persist_now=False)
        delete_auto_finance_windows_for_chat(chat_id, persist_now=False)
        _persist_finance_window_mode_critical(chat_id)
        return 'off'
    delete_auto_finance_windows_for_chat(chat_id, persist_now=False)
    set_finance_window_mode(chat_id, selected_mode, persist_now=False)
    try:
        store = get_chat_store(chat_id)
        day_key = store.get('current_view_day') or today_key()
        if selected_mode == 'normal':
            store['main_window_msg_count'] = 0
            recreate_main_window_now(chat_id, day_key)
        else:
            store['balance_panel_msg_count'] = 0
            send_minimized_balance_panel(chat_id)
            if selected_mode == 'first':
                schedule_quick_balance_first_recreate(chat_id, 60.0)
    except Exception as e:
        log_error(f'_apply_finance_window_mode_choice({chat_id},{selected_mode}): {e}')
    _finance_window_state(chat_id)['auto_reopen_on_boot'] = True
    _persist_finance_window_mode_critical(chat_id)
    return selected_mode

# --- finance:0140 · from 05_finance_ui.py:2723 · public build_hidden_finance_chat_menu ---
def build_hidden_finance_chat_menu(day_key: str):
    kb = types.InlineKeyboardMarkup(row_width=2)
    known = collect_forward_menu_chats()
    items = {}
    for cid, ch in known.items():
        try:
            int_cid = int(cid)
        except Exception:
            continue
        items[int_cid] = ch.get('title') or get_chat_display_name(int_cid)
    if OWNER_ID:
        try:
            owner_id = int(OWNER_ID)
            items.setdefault(owner_id, get_chat_display_name(owner_id))
        except Exception:
            pass
    buttons = []
    for int_cid, title in sorted(items.items(), key=lambda x: x[1].lower()):
        if is_chat_bot_removed(int_cid) and (not (OWNER_ID and str(int_cid) == str(OWNER_ID))):
            continue
        enabled = is_hidden_finance_mode(int_cid)
        icon = '✅🙈' if enabled else '⬜🙈'
        buttons.append(IB(f'{icon} {chat_button_title(int_cid, title)}', callback_data=f'd:{day_key}:hf_pick_{int_cid}'))
    add_buttons_in_rows(kb, buttons, 2)
    kb.row(IB('🔙 Назад', callback_data=f'd:{day_key}:back_main'))
    return kb

# --- finance:0141 · from 05_finance_ui.py:2776 · public build_usd_edit_records_keyboard ---
def build_usd_edit_records_keyboard(day_key: str, chat_id: int, prefix: str='d', owner_day_key: str | None=None):
    """USD counterpart of build_edit_records_keyboard, including owner-view callbacks."""
    store = get_chat_store(int(chat_id))
    selected = set((int(x) for x in (store.get('usd_edit_delete_selected', {}) or {}).get(str(day_key), [])))
    kb = types.InlineKeyboardMarkup(row_width=3)
    rows = usd_records_for_day(int(chat_id), str(day_key))
    viewer_chat_id = int(OWNER_ID) if prefix == 'fv' and OWNER_ID else int(chat_id)
    for rec in rows:
        rid = int(rec.get('id'))
        amt = float(rec.get('usd_amount', 0) or 0)
        sid = str(rec.get('usd_short_id') or f'U{rid}')
        label = f"{sid} {('+' if amt >= 0 else '-')}${fmt_num_plain(abs(amt))}"
        insert_text = compose_usd_edit_insert_value(chat_id, rid, _record_day_key(rec), amt, rec.get('usd_note') or rec.get('note', ''))
        del_icon = '☑️' if rid in selected else '❌'
        if prefix == 'fv':
            del_cb = f'fv:{chat_id}:{day_key}:del_toggle_{rid}:{owner_day_key or today_key()}'
        else:
            del_cb = f'd:{day_key}:del_toggle_{rid}'
        kb.row(IB(label, callback_data='none'), make_direct_edit_insert_button('✏️', insert_text, viewer_chat_id=viewer_chat_id), IB(del_icon, callback_data=del_cb))
    if selected:
        if prefix == 'fv':
            kb.row(IB('🗑 Удалить выбранное USD', callback_data=f'fv:{chat_id}:{day_key}:del_selected:{owner_day_key or today_key()}'))
        else:
            kb.row(IB('🗑 Удалить выбранное USD', callback_data=f'd:{day_key}:del_selected'))
    if prefix == 'fv':
        kb.row(IB('🔙 Назад', callback_data=f'fv:{chat_id}:{day_key}:clear_delete_back:{owner_day_key or today_key()}'))
    else:
        kb.row(IB('🔙 Назад', callback_data=f'd:{day_key}:back_main'))
    return kb

# --- finance:0142 · from 05_finance_ui.py:2806 · public toggle_usd_edit_delete_selection ---
def _legacy_s0142_toggle_usd_edit_delete_selection(chat_id: int, day_key: str, rid: int):
    store = get_chat_store(int(chat_id))
    all_sel = store.setdefault('usd_edit_delete_selected', {})
    selected = set((int(x) for x in all_sel.get(str(day_key), [])))
    rid = int(rid)
    if rid in selected:
        selected.remove(rid)
    else:
        selected.add(rid)
    if selected:
        all_sel[str(day_key)] = sorted(selected)
    else:
        all_sel.pop(str(day_key), None)
    save_data(data, chat_ids=[int(chat_id)])

# --- finance:0143 · from 05_finance_ui.py:2821 · public clear_usd_edit_delete_selection ---
def _legacy_s0143_clear_usd_edit_delete_selection(chat_id: int, day_key: str | None=None):
    store = get_chat_store(int(chat_id))
    all_sel = store.setdefault('usd_edit_delete_selected', {})
    if day_key is None:
        all_sel.clear()
    else:
        all_sel.pop(str(day_key), None)
    save_data(data, chat_ids=[int(chat_id)])

# --- finance:0144 · from 05_finance_ui.py:2831 · public delete_selected_usd_records ---
def delete_selected_usd_records(chat_id: int, day_key: str) -> int:
    chat_id=int(chat_id)
    with locked_chat(chat_id):
        store=get_chat_store(chat_id); selected={int(x) for x in store.setdefault('usd_edit_delete_selected',{}).get(str(day_key),[]) or []}
        if not selected: return 0
        deleted=0; remove_ids=set(); deleted_usd=0.0
        for rec in store.get('records',[]) or []:
            try: rid=int(rec.get('id',-1))
            except Exception: continue
            if rid not in selected or not float(rec.get('usd_amount',0) or 0): continue
            deleted+=1; deleted_usd+=float(rec.get('usd_amount',0) or 0)
            if abs(float(rec.get('amount',0) or 0))<=0 and bool(rec.get('usd_only',False)): remove_ids.add(rid)
            else: rec['usd_amount']=0.0; rec['usd_note']=''; rec['usd_only']=False
        if remove_ids: store['records']=[r for r in store.get('records',[]) or [] if int(r.get('id',-1)) not in remove_ids]
        for dk,arr in list((store.get('daily_records',{}) or {}).items()):
            new=[]
            for rec in arr or []:
                try: rid=int(rec.get('id',-1))
                except Exception: new.append(rec); continue
                if rid in remove_ids: continue
                if rid in selected and float(rec.get('usd_amount',0) or 0): rec['usd_amount']=0.0; rec['usd_note']=''; rec['usd_only']=False
                new.append(rec)
            if new: store['daily_records'][dk]=new
            else: store['daily_records'].pop(dk,None)
        store.setdefault('usd_edit_delete_selected',{}).pop(str(day_key),None)
        store['_finance_hotpath_pending_normalize_r16']=True; store['_finance_fast_generation_r16']=int(store.get('_finance_fast_generation_r16',0) or 0)+1; store.pop('_finance_day_balance_cache_r16',None)
        if '_usd_balance_cache_r16' in store:
            try: store['_usd_balance_cache_r16']=float(store.get('_usd_balance_cache_r16',0) or 0)-deleted_usd
            except Exception: store.pop('_usd_balance_cache_r16',None)
    persist_finance_chat_local_fast(chat_id)
    if callable(globals().get('_v262_schedule_finance_postcommit')): _v262_schedule_finance_postcommit(chat_id,str(day_key),'delete_selected_usd')
    else: rebuild_global_records(); finance_changed(chat_id,str(day_key),reason='delete_selected_usd',delay=0.1)
    return deleted

# --- finance:0145 · from 05_finance_ui.py:3068 · public _v177_legacy_0201_build_fin_window_usd_month_keyboard ---
def _v177_legacy_0201_build_fin_window_usd_month_keyboard(target_chat_id: int, day_key: str, owner_day_key: str):
    try:
        dt = datetime.strptime(str(day_key)[:10], '%Y-%m-%d').replace(day=1)
    except Exception:
        dt = now_local().replace(day=1)
    prev_dt = (dt - timedelta(days=1)).replace(day=1)
    next_dt = (dt.replace(day=28) + timedelta(days=4)).replace(day=1)
    kb = types.InlineKeyboardMarkup(row_width=3)
    kb.row(IB('⬅️ Пред. месяц', callback_data=f"fv:{target_chat_id}:{prev_dt.strftime('%Y-%m-01')}:usd_month:{owner_day_key}"), IB('📅 Этот месяц', callback_data=f'fv:{target_chat_id}:{today_key()}:usd_month:{owner_day_key}'), IB('След. месяц ➡️', callback_data=f"fv:{target_chat_id}:{next_dt.strftime('%Y-%m-01')}:usd_month:{owner_day_key}"))
    kb.row(IB('🔙 Назад к чату', callback_data=f'fv:{target_chat_id}:{day_key}:open:{owner_day_key}'))
    kb.row(IB('⬅️ Назад осн. окно', callback_data=f'd:{owner_day_key}:back_main'))
    return kb

# --- finance:0146 · from 05_finance_ui.py:5055 · public _expense_shortcut_root ---
def _expense_shortcut_root() -> dict:
    return data.setdefault('_global_settings', {}).setdefault('expense_shortcut', {})

# --- finance:0147 · from 05_finance_ui.py:5058 · public _expense_shortcut_persist ---
def _expense_shortcut_persist():
    try:
        save_data(data, root_only=True)
    except TypeError:
        save_data(data)
    try:
        _mark_global_snapshot_pending()
    except Exception:
        pass
    try:
        if OWNER_ID:
            schedule_config_backup_for_chats(int(OWNER_ID), delay=0.4)
            schedule_quick_backup(int(OWNER_ID), 0.4)
    except Exception:
        pass

# --- finance:0148 · from 05_finance_ui.py:5074 · public expense_shortcut_config ---
def expense_shortcut_config(create: bool=True) -> dict:
    with _EXPENSE_SHORTCUT_LOCK:
        cfg = _expense_shortcut_root()
        changed = False
        if create and (not str(cfg.get('token') or '').strip()):
            cfg['token'] = secrets.token_urlsafe(24)
            changed = True
        if create and (not cfg.get('target_chat_id')) and OWNER_ID:
            cfg['target_chat_id'] = int(OWNER_ID)
            changed = True
        if 'text' not in cfg:
            cfg['text'] = '💸 Был расход'
            changed = True
        if 'events' not in cfg or not isinstance(cfg.get('events'), list):
            cfg['events'] = []
            changed = True
        if changed:
            _expense_shortcut_persist()
        return cfg

# --- finance:0149 · from 05_finance_ui.py:5094 · public expense_shortcut_url ---
def expense_shortcut_url() -> str:
    cfg = expense_shortcut_config(True)
    base = str(WEBHOOK_URL or APP_URL or '').strip().rstrip('/')
    if not base:
        return ''
    return f"{base}/expense-ping/{cfg.get('token')}"

# --- finance:0150 · from 05_finance_ui.py:5101 · public expense_shortcut_set_target ---
def expense_shortcut_set_target(chat_id: int):
    with _EXPENSE_SHORTCUT_LOCK:
        cfg = expense_shortcut_config(True)
        cfg['target_chat_id'] = int(chat_id)
        _expense_shortcut_persist()
    return int(chat_id)

# --- finance:0151 · from 05_finance_ui.py:5108 · public expense_shortcut_regenerate_token ---
def expense_shortcut_regenerate_token() -> str:
    with _EXPENSE_SHORTCUT_LOCK:
        cfg = expense_shortcut_config(True)
        cfg['token'] = secrets.token_urlsafe(24)
        _expense_shortcut_persist()
        return str(cfg['token'])

# --- finance:0152 · from 05_finance_ui.py:5115 · public _expense_shortcut_find_event ---
def _expense_shortcut_find_event(event_id: str):
    cfg = expense_shortcut_config(True)
    for row in cfg.get('events') or []:
        if str((row or {}).get('id')) == str(event_id):
            return row
    return None

# --- finance:0153 · from 05_finance_ui.py:5122 · public _expense_shortcut_cleanup_events_locked ---
def _expense_shortcut_cleanup_events_locked(cfg: dict):
    events = list(cfg.get('events') or [])
    pending = [e for e in events if str((e or {}).get('status')) != 'sent']
    sent = [e for e in events if str((e or {}).get('status')) == 'sent'][-80:]
    cfg['events'] = (pending + sent)[-_EXPENSE_SHORTCUT_EVENT_LIMIT:]

# --- finance:0154 · from 05_finance_ui.py:5128 · public enqueue_expense_ping_event ---
def enqueue_expense_ping_event(source: str='iphone', force: bool=False) -> tuple[str, bool]:
    """Сначала сохраняет событие, затем фоном отправляет Telegram-сообщение."""
    with _EXPENSE_SHORTCUT_LOCK:
        cfg = expense_shortcut_config(True)
        now_ts = time.time()
        if not force:
            for old in reversed(cfg.get('events') or []):
                if now_ts - float((old or {}).get('created_ts') or 0) <= 6.0:
                    if str((old or {}).get('source')) == str(source):
                        return (str(old.get('id')), True)
                else:
                    break
        event_id = f'xp_{int(now_ts * 1000)}_{secrets.token_hex(4)}'
        row = {'id': event_id, 'created_ts': now_ts, 'created_at': now_local().isoformat(timespec='seconds'), 'target_chat_id': int(cfg.get('target_chat_id') or OWNER_ID or 0), 'text': str(cfg.get('text') or '💸 Был расход'), 'source': str(source or 'iphone'), 'status': 'pending', 'attempts': 0, 'last_error': ''}
        cfg.setdefault('events', []).append(row)
        _expense_shortcut_cleanup_events_locked(cfg)
        _expense_shortcut_persist()
    GENERAL_TASK_POOL.submit(f'expense-ping:{event_id}', _deliver_expense_ping_event, event_id)
    return (event_id, False)

# --- finance:0155 · from 05_finance_ui.py:5148 · public expense_compact_message_text ---
def expense_compact_message_text(created_at: str | None=None) -> str:
    """Короткая отметка, чтобы не занимать место в финансовом чате."""
    try:
        dt = datetime.fromisoformat(str(created_at or ''))
    except Exception:
        dt = now_local()
    now_dt = now_local()
    if dt.date() == now_dt.date():
        stamp = dt.strftime('%H:%M')
    else:
        stamp = dt.strftime('%d.%m %H:%M')
    return f'💸 iPhone · {stamp}'

# --- finance:0156 · from 05_finance_ui.py:5161 · public _deliver_expense_ping_event ---
def _deliver_expense_ping_event(event_id: str):
    with _EXPENSE_SHORTCUT_LOCK:
        row = _expense_shortcut_find_event(event_id)
        if not row or str(row.get('status')) == 'sent':
            return True
        row['attempts'] = int(row.get('attempts') or 0) + 1
        target_chat_id = int(row.get('target_chat_id') or 0)
        created_at = str(row.get('created_at') or now_local().isoformat(timespec='seconds'))
    try:
        dt = datetime.fromisoformat(created_at)
    except Exception:
        dt = now_local()
    draft = expense_draft_for_event(event_id, target_chat_id, created_at) if 'expense_draft_for_event' in globals() else {'id': 0}
    draft_id = int((draft or {}).get('id') or 0)
    text = expense_compact_message_text(created_at)
    try:
        markup = expense_draft_message_keyboard(draft_id, target_chat_id) if draft_id and 'expense_draft_message_keyboard' in globals() else None
        sent = _tg_call_retry(bot.send_message, target_chat_id, text, reply_markup=markup, attempts=2, purpose='expense_ping_send')
        if draft_id and 'expense_draft_set_message' in globals():
            expense_draft_set_message(draft_id, int(getattr(sent, 'message_id', 0) or 0))
        with _EXPENSE_SHORTCUT_LOCK:
            row = _expense_shortcut_find_event(event_id)
            if row:
                row['status'] = 'sent'
                row['sent_at'] = now_local().isoformat(timespec='seconds')
                row['telegram_message_id'] = int(getattr(sent, 'message_id', 0) or 0)
                row['last_error'] = ''
                _expense_shortcut_cleanup_events_locked(expense_shortcut_config(True))
                _expense_shortcut_persist()
        try:
            bot_journal('expense_ping_sent', target_chat_id, f"event={event_id} source={(row.get('source') if row else '')}")
        except Exception:
            pass
        return True
    except Exception as exc:
        with _EXPENSE_SHORTCUT_LOCK:
            row = _expense_shortcut_find_event(event_id)
            if row:
                row['status'] = 'pending'
                row['last_error'] = str(exc)[:300]
                _expense_shortcut_persist()
        try:
            bot_journal('expense_ping_retry', target_chat_id, f'event={event_id} error={str(exc)[:240]}', 'WARN')
        except Exception:
            pass
        DELAYED_SCHEDULER.schedule(f'expense-ping-retry:{event_id}', _EXPENSE_SHORTCUT_RETRY_SECONDS, _deliver_expense_ping_event, event_id)
        return False

# --- finance:0157 · from 05_finance_ui.py:5209 · public schedule_expense_ping_recovery ---
def schedule_expense_ping_recovery(delay: float=1.0):

    def _job():
        cfg = expense_shortcut_config(False)
        for row in list((cfg or {}).get('events') or []):
            if str((row or {}).get('status')) != 'sent' and row.get('id'):
                GENERAL_TASK_POOL.submit(f"expense-ping:{row.get('id')}", _deliver_expense_ping_event, str(row.get('id')))
    DELAYED_SCHEDULER.schedule('expense-ping-recovery', max(0.1, float(delay)), _job)

# --- finance:0158 · from 05_finance_ui.py:5218 · public build_expense_shortcut_text ---
def build_expense_shortcut_text(chat_id: int) -> str:
    cfg = expense_shortcut_config(True)
    target = int(cfg.get('target_chat_id') or OWNER_ID or chat_id)
    url = expense_shortcut_url()
    pending = sum((1 for e in cfg.get('events') or [] if str((e or {}).get('status')) != 'sent'))
    url_text = html.escape(url) if url else 'APP_URL/WEBHOOK_URL не определён'
    return f"📱 Быстрый расход с iPhone\n\nЧат назначения: {html.escape(get_chat_display_name(target))}\nID: <code>{target}</code>\nОжидают доставки: {pending}\nКнопки в сообщении: {('✅ ВКЛ' if expense_quick_buttons_enabled() else '⬜ ВЫКЛ')}\nПодхвачены отметки за 2 дня: {html.escape(str(_expense_inbox_root().get('recent_event_migration_v142_at') or 'ещё нет'))}\n\nСкопируйте эту личную ссылку в приложение «Команды»:\n<code>{url_text}</code>\n\nТройное касание задней панели запустит команду, а бот отправит «💸 Был расход». Ссылка секретная: не публикуйте её."

# --- finance:0159 · from 05_finance_ui.py:5226 · public build_expense_shortcut_keyboard ---
def build_expense_shortcut_keyboard(chat_id: int):
    kb = types.InlineKeyboardMarkup(row_width=1)
    kb.row(IB('🎯 Выбрать чат', callback_data='expense_shortcut_pick'))
    kb.row(IB('📋 Прислать ссылку отдельно', callback_data='expense_shortcut_send_url'))
    kb.row(IB('🧪 Проверить сейчас', callback_data='expense_shortcut_test'))
    kb.row(IB(expense_quick_buttons_label(), callback_data='expense_quick_buttons_toggle'))
    kb.row(IB('🔐 Создать новую секретную ссылку', callback_data='expense_shortcut_regenerate'))
    day = get_chat_store(chat_id).get('current_view_day') or today_key()
    kb.row(IB('🔙 Назад в Инфо', callback_data=f'd:{day}:info'))
    kb.row(IB('⬅️ Назад осн. окно', callback_data=f'd:{day}:back_main'))
    return kb

# --- finance:0160 · from 05_finance_ui.py:5238 · public build_expense_shortcut_chat_menu ---
def build_expense_shortcut_chat_menu(chat_id: int):
    kb = types.InlineKeyboardMarkup(row_width=2)
    current = int(expense_shortcut_config(True).get('target_chat_id') or OWNER_ID or chat_id)
    buttons = []
    for cid in collect_all_known_chat_ids(include_owner=True):
        if is_chat_bot_removed(cid):
            continue
        icon = '✅' if int(cid) == current else '▫️'
        buttons.append(IB(f'{icon} {chat_button_title(cid)}', callback_data=f'expense_shortcut_target:{cid}'))
    add_buttons_in_rows(kb, buttons, 2)
    kb.row(IB('🔙 Назад', callback_data='expense_shortcut_info'))
    day = get_chat_store(chat_id).get('current_view_day') or today_key()
    kb.row(IB('⬅️ Назад осн. окно', callback_data=f'd:{day}:back_main'))
    return kb

# --- finance:0161 · from 05_finance_ui.py:5374 · public _expense_anchor_rows ---
def _expense_anchor_rows(kb, store: dict, day_key: str, callback_builder, empty_text: str='Нет расходов в этот день'):
    records = expense_anchor_records_for_day(store, day_key)
    if records:
        for rec in records:
            rid = _record_int_id(rec)
            kb.row(IB(expense_anchor_button_label(rec, store), callback_data=callback_builder(rid)))
    else:
        kb.row(IB(empty_text, callback_data='none'))
    return records

# --- finance:0162 · from 06_commands_callbacks.py:2817 · public finance_operation_key ---
def finance_operation_key(chat_id: int, source_msg_id, ledger: str='main') -> str:
    """Stable idempotency key for a finance effect created from a Telegram message."""
    try:
        mid = int(source_msg_id)
    except Exception:
        return ''
    return f"finance:{int(chat_id)}:{str(ledger or 'main')}:{mid}"

# --- finance:0163 · from 06_commands_callbacks.py:2853 · public _finance_add_record_base ---
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
                    _r49_defer_operation_complete(op_id, 'duplicate blocked by stable operation key; existing record reused')
                return existing_op
        if source_msg_id is not None:
            existing_any = find_record_by_message_id(int(chat_id), int(source_msg_id)) if 'find_record_by_message_id' in globals() else None
            if isinstance(existing_any, dict):
                if '_remember_finance_source_identity_v257' in globals():
                    _remember_finance_source_identity_v257(int(chat_id), existing_any, int(source_msg_id), 'records')
                bot_journal('finance_duplicate_blocked_v257', chat_id, f'source_msg_id={source_msg_id} operation_key={operation_key}; central=1')
                if op_id and 'operation_complete' in globals():
                    _r49_defer_operation_complete(op_id, 'duplicate blocked by stable source identity; existing record reused')
                return existing_any
            for existing in store.get('records', []) or []:
                if not isinstance(existing, dict):
                    continue
                if operation_key and str(existing.get('operation_key') or '') == operation_key or int(existing.get('source_msg_id') or 0) == int(source_msg_id):
                    if operation_key and (not existing.get('operation_key')):
                        existing['operation_key'] = operation_key
                    bot_journal('finance_duplicate_blocked', chat_id, f'source_msg_id={source_msg_id} operation_key={operation_key}')
                    if op_id and 'operation_complete' in globals():
                        _r49_defer_operation_complete(op_id, 'duplicate blocked; existing record reused')
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
        # R48: no SQLite/integrity/root persistence while chat_lock is held.
        try:
            if 'ensure_finance_record_uid' in globals():
                ensure_finance_record_uid(int(chat_id), rec)
        except Exception:
            pass
        result_rec = rec
    # Durable record commit after chat_lock release.
    try:
        if 'persist_finance_chat_local_fast' in globals() and not persist_finance_chat_local_fast(int(chat_id)):
            raise RuntimeError('local SQLite finance persist failed')
    except Exception as _v168_local_exc:
        try: log_error(f'R48 record local commit {chat_id}: {_v168_local_exc}')
        except Exception: pass
    try:
        finance_cache_invalidate(chat_id, 'finance_add')
        finance_integrity_append(chat_id, 'add', result_rec)
    except Exception as _integrity_exc:
        log_error(f'finance add integrity: {_integrity_exc}')
    try:
        if source_msg_id is not None and '_remember_finance_source_identity_v257' in globals():
            _remember_finance_source_identity_v257(int(chat_id), result_rec, int(source_msg_id), 'records')
    except Exception as _v257_idx_exc:
        try: log_error(f'v257 finance source identity index: {_v257_idx_exc}')
        except Exception: pass
    if op_id and 'operation_complete' in globals():
        operation_complete(op_id, f"record={result_rec.get('id')}")
    return result_rec

# --- finance:0164 · from 06_commands_callbacks.py:3193 · public is_finance_mode ---
def is_finance_mode(chat_id):
    store = get_chat_store(chat_id)
    return store.get('finance_mode', False)

# --- finance:0165 · from 06_commands_callbacks.py:3197 · public set_finance_mode ---
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

# --- finance:0166 · from 06_commands_callbacks.py:3247 · public require_finance ---
def require_finance(chat_id: int) -> bool:
    """
    Проверка: включён ли финансовый режим.
    Если нет — показываем подсказку /поехали.
    """
    if not is_finance_mode(chat_id):
        send_and_auto_delete(chat_id, '⚙️ Финансовый режим выключен.\nАктивируйте командой /ok')
        return False
    return True

# --- finance:0167 · from 06_commands_callbacks.py:4376 · public _v258_merge_duplicate_finance_records ---
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

# --- finance:0168 · from 06_commands_callbacks.py:4509 · public recalc_balance ---
def recalc_balance(chat_id: int):
    normalize_chat_records(chat_id)
    store = get_chat_store(chat_id)
    store['balance'] = sum((float(r.get('amount', 0) or 0) for r in store.get('records', [])))

# --- finance:0169 · from 06_commands_callbacks.py:4545 · public calc_day_balance ---
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

# --- finance:0170 · from 06_commands_callbacks.py:4603 · public collect_finance_chat_ids ---
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

# --- finance:0171 · from 06_commands_callbacks.py:4662 · public schedule_all_finance_backups ---
def schedule_all_finance_backups(delay: float=10.0):
    for cid in collect_finance_chat_ids():
        schedule_backup_flush(cid, delay=delay)

# --- finance:0172 · from 06_commands_callbacks.py:4838 · public _v177_legacy_0238_finance_changed ---
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

# --- finance:0173 · from 07_state_web.py:326 · public _finance_changed_now ---
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

# --- finance:0174 · from 07_state_web.py:6421 · public _v150_usd_rate ---
def _v150_usd_rate() -> float:
    try:
        row = usd_rate_cached(force=False) or {}
        return max(0.0, _v150_float(row.get('rate') or row.get('venta') or row.get('sell')))
    except Exception:
        return 0.0

# --- finance:0175 · from 07_state_web.py:6559 · public _v150_ledger_balance ---
def _v150_ledger_balance(store: dict, currency: str) -> float:
    currency = 'usd' if str(currency).lower() == 'usd' else 'ars'
    active = str(store.setdefault('settings', {}).get('_active_currency_ledger') or 'ars').lower()
    if active == currency:
        return _v150_float(store.get('balance'))
    return _v150_float(store.get(f'{currency}_balance'))

# --- finance:0176 · from 07_state_web.py:6578 · public _v150_rebalance_key ---
def _v150_rebalance_key(chat_id: int, currency: str, rec: dict) -> str:
    operation_key = str((rec or {}).get('operation_key') or '').strip()
    if operation_key:
        return f'{chat_id}:{currency}:{operation_key}'
    source = int((rec or {}).get('source_msg_id') or 0)
    if source:
        return f'{chat_id}:{currency}:msg:{source}'
    return f"{chat_id}:{currency}:rid:{int((rec or {}).get('id') or 0)}:{str((rec or {}).get('timestamp') or '')}"

# --- finance:0177 · from 07_state_web.py:6667 · public _v150_repair_pending_rebalances ---
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

# --- finance:0178 · from 07_state_web.py:7309 · public _v177_legacy_0271_v151_usd_records ---
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

# --- finance:0179 · from 07_state_web.py:7427 · public _v151_opening_balance ---
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

# --- finance:0180 · from 07_state_web.py:7450 · public _v151_usd_rate ---
def _v151_usd_rate() -> float:
    try:
        row = usd_rate_cached(force=False) or {}
        return max(0.0, _v151_float(row.get('rate') or row.get('venta') or row.get('sell')))
    except Exception:
        return 0.0

# --- finance:0181 · from 07_state_web.py:7751 · public _v151_rebalance_key ---
def _v151_rebalance_key(chat_id: int, currency: str, rec: dict) -> str:
    operation_key = str((rec or {}).get('operation_key') or '').strip()
    if operation_key:
        return f'{int(chat_id)}:{currency}:{operation_key}'
    source_msg_id = int((rec or {}).get('source_msg_id') or 0)
    if source_msg_id:
        return f'{int(chat_id)}:{currency}:msg:{source_msg_id}'
    return f"{int(chat_id)}:{currency}:rid:{int((rec or {}).get('id') or 0)}:{str((rec or {}).get('timestamp') or '')}"

# --- finance:0182 · from 07_state_web.py:7760 · public _v151_ledger_balance ---
def _v151_ledger_balance(chat_id: int, currency: str) -> float:
    return sum((_v151_float(r.get('_v151_amount')) for r in _v151_all_records(int(chat_id), currency)))

# --- finance:0183 · from 07_state_web.py:7975 · public _v151_repair_pending_rebalances ---
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

# --- finance:0184 · from 07_state_web.py:8120 · public _canon_render_usd_month_window__001 ---
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

# --- finance:0185 · from 07_state_web.py:8147 · public _canon_build_usd_month_keyboard__001 ---
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

# --- finance:0186 · from 07_state_web.py:8160 · public _canon_build_fin_window_usd_month_keyboard__001 ---
def _canon_build_fin_window_usd_month_keyboard__001(target_chat_id: int, day_key: str, owner_day_key: str):
    """В окне владельца также сохраняется исходное расположение кнопок чата."""
    return build_fin_window_view_keyboard(int(target_chat_id), str(day_key)[:10], str(owner_day_key)[:10])

# --- finance:0187 · from 07_state_web.py:10891 · public _v154_day_has_expense ---
def _v154_day_has_expense(chat_id: int | None, day_key: str) -> bool:
    if chat_id is None:
        return False
    try:
        store = get_chat_store(int(chat_id))
        return bool(expense_anchor_records_for_day(store, str(day_key)))
    except Exception:
        return False

# --- finance:0188 · from 07_state_web.py:11047 · public _v177_legacy_0272_v151_usd_records ---
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

# --- finance:0189 · from 07_state_web.py:11181 · public _v154_join_ars_usd ---
def _v154_join_ars_usd(ars_rows: list[list], usd_rows: list[list], chat_id: int) -> list[list]:
    if not excel_usd_table_enabled(int(chat_id)):
        return list(ars_rows or [])
    prefix = list(ars_rows or []) + [[], []]
    shifted_usd = _v193_shift_formula_rows(list(usd_rows or []), len(prefix))
    joined = prefix + shifted_usd
    _v193_validate_currency_formula_domains(joined)
    return joined

# --- finance:0190 · from 07_state_web.py:11249 · public _v154_find_usd_section ---
def _v154_find_usd_section(rows: list[list]) -> int | None:
    for idx, row in enumerate(rows or []):
        try:
            if str((row or [''])[0]).strip().upper() == 'USD':
                return idx
        except Exception:
            pass
    return None

# --- finance:0191 · from 08_reliability_tasks.py:711 · public _v156_clean_embedded_usd_description ---
def _v156_clean_embedded_usd_description(rec: dict) -> str:
    """Extract USD-side description without ever falling back to the ARS note."""
    source = str((rec or {}).get('source_finance_text') or '').strip()
    if source:
        try:
            info = extract_usd_transaction(source)
        except Exception:
            info = None
        if info and info.get('span'):
            try:
                _start, end = info.get('span')
                after = source[int(end):].strip(' \t:;,-–—|/')
                if after:
                    after = _v156_re.sub('(?i)\\b(?:ars|pesos?|peso)\\b', ' ', after)
                    after = _v156_re.sub('\\s+', ' ', after).strip(' :;,-–—|/')
                    if after and (not _v156_re.fullmatch("[\\d\\s.,+'\\-]+", after)):
                        return after.lower()[:220]
            except Exception:
                pass
    usd_note = str((rec or {}).get('usd_note') or '').strip().lower()
    ars_note = str((rec or {}).get('note') or '').strip().lower()
    clean = usd_note
    if clean and ars_note:
        if clean == ars_note:
            clean = ''
        elif ars_note in clean:
            clean = clean.replace(ars_note, ' ', 1)
    clean = _v156_re.sub('(?i)\\b(?:ars|pesos?|peso)\\b', ' ', clean)
    clean = _v156_re.sub("(?<!\\w)[+\\-]?\\d[\\d\\s.,_'’]*(?!\\w)", ' ', clean)
    clean = _v156_re.sub('\\s+', ' ', clean).strip(' :;,-–—|/')
    return (clean or 'USD операция')[:220]

# --- finance:0192 · from 08_reliability_tasks.py:743 · public _canon_v151_usd_records__001 ---
def _canon_v151_usd_records__001(chat_id: int) -> list[dict]:
    """v156 source of truth for XLSX USD rows: USD-only data, no ARS note fallback."""
    store, active, ars_source, usd_source = _v156_store_ledgers(int(chat_id))
    ars_ids = {_v156_record_identity(r) for r in ars_source if isinstance(r, dict)}
    ars_fps = {_v156_record_fingerprint(r) for r in ars_source if isinstance(r, dict)}
    rows = []
    seen = set()
    filtered = 0
    for rec in usd_source:
        if not isinstance(rec, dict):
            continue
        currency = _v156_explicit_currency(rec)
        ident = _v156_record_identity(rec)
        fp = _v156_record_fingerprint(rec)
        if currency == 'ars':
            filtered += 1
            continue
        if currency != 'usd' and (ident in ars_ids or fp in ars_fps):
            filtered += 1
            continue
        if ident in seen:
            continue
        item = dict(rec)
        item['_v151_amount'] = _v151_float(rec.get('amount'))
        item['_v151_note'] = str(rec.get('note') or rec.get('usd_note') or 'USD операция').strip()
        item['_v151_currency'] = 'usd'
        item['_v156_source'] = 'usd_ledger'
        rows.append(item)
        seen.add(ident)
    for rec in ars_source:
        if not isinstance(rec, dict) or rec.get('usd_amount') is None:
            continue
        usd_amount = _v151_float(rec.get('usd_amount'))
        if abs(usd_amount) <= 1e-12:
            continue
        ident = _v156_record_identity(rec)
        if ident in seen:
            continue
        item = dict(rec)
        item['_v151_amount'] = usd_amount
        item['_v151_note'] = _v156_clean_embedded_usd_description(rec)
        item['_v151_currency'] = 'usd'
        item['_v156_source'] = 'explicit_usd_component'
        rows.append(item)
        seen.add(ident)
    try:
        rows = sorted(rows, key=record_sort_key)
    except Exception:
        pass
    if filtered:
        try:
            bot_journal('excel_usd_ars_duplicates_filtered', int(chat_id), f'count={filtered}; active={active}')
        except Exception:
            pass
    return rows

# --- finance:0193 · from 08_reliability_tasks.py:1264 · public _canon_migrate_recent_expense_shortcut_events__001 ---
def _canon_migrate_recent_expense_shortcut_events__001(days: int=2, refresh_messages: bool=False) -> dict:
    cfg_fn = globals().get('expense_shortcut_config')
    if not callable(cfg_fn):
        return {'imported': 0, 'updated': 0, 'seen': 0}
    try:
        shortcut = cfg_fn(False) or {}
    except Exception:
        shortcut = {}
    cutoff = now_local() - timedelta(days=max(1, int(days or 2)))
    imported = updated = seen = 0
    duplicate = too_old = missing_message_id = refresh_failed = stale_message = 0
    total_events = len(list(shortcut.get('events') or []))
    changed_events = False
    for event in list(shortcut.get('events') or []):
        if not isinstance(event, dict) or not event.get('id'):
            continue
        dt = _expense_event_dt(event)
        if dt is None or dt < cutoff:
            too_old += 1
            continue
        seen += 1
        event_id = str(event.get('id'))
        target = int(event.get('target_chat_id') or shortcut.get('target_chat_id') or OWNER_ID or 0)
        before = None
        with _EXPENSE_INBOX_LOCK:
            for existing in (_expense_inbox_root().get('items') or {}).values():
                if str((existing or {}).get('source_event_id') or '') == event_id:
                    before = existing
                    break
        draft = expense_draft_for_event(event_id, target, dt.isoformat(timespec='seconds'))
        if before is None:
            imported += 1
        else:
            duplicate += 1
        mid = int(event.get('telegram_message_id') or 0)
        if not mid:
            missing_message_id += 1
        if mid and int((draft or {}).get('telegram_message_id') or 0) != mid:
            with _EXPENSE_INBOX_LOCK:
                draft['telegram_message_id'] = mid
        if refresh_messages and mid and target:
            try:
                text_fn = globals().get('expense_compact_message_text')
                text = text_fn(dt.isoformat(timespec='seconds')) if callable(text_fn) else f"💸 iPhone · {dt.strftime('%H:%M')}"
                markup = expense_draft_message_keyboard(int(draft.get('id') or 0), target)
                bot.edit_message_text(text, chat_id=target, message_id=mid, reply_markup=markup)
                updated += 1
            except Exception as exc:
                low = str(exc).casefold()
                if 'message is not modified' in low:
                    continue
                if _v157_process_message_missing(exc):
                    stale_message += 1
                    event['telegram_message_id'] = 0
                    changed_events = True
                    try:
                        with _EXPENSE_INBOX_LOCK:
                            draft['telegram_message_id'] = 0
                    except Exception:
                        pass
                    try:
                        unregister_open_window(target, mid)
                    except Exception:
                        pass
                    continue
                try:
                    fast_ui_edit_reply_markup(target, mid, expense_draft_message_keyboard(int(draft.get('id') or 0), target), purpose='expense_draft_markup')
                    updated += 1
                except Exception as exc2:
                    if _v157_process_message_missing(exc2):
                        stale_message += 1
                        event['telegram_message_id'] = 0
                        changed_events = True
                        try:
                            with _EXPENSE_INBOX_LOCK:
                                draft['telegram_message_id'] = 0
                        except Exception:
                            pass
                    else:
                        refresh_failed += 1
    root = _expense_inbox_root()
    root['recent_event_migration_v157_at'] = now_local().isoformat(timespec='seconds')
    _root_save('expense_recent_event_migration_v157')
    if changed_events:
        try:
            save_data(data, root_only=True)
        except Exception:
            pass
    try:
        bot_journal('expense_recent_events_migrated_v157', int(OWNER_ID or 0), f'total={total_events} seen_48h={seen} imported={imported} existing={duplicate} updated={updated} too_old_or_bad_date={too_old} missing_message_id={missing_message_id} stale_message={stale_message} refresh_failed={refresh_failed}')
    except Exception:
        pass
    return {'imported': imported, 'updated': updated, 'seen': seen, 'existing': duplicate, 'too_old': too_old, 'missing_message_id': missing_message_id, 'stale_message': stale_message, 'refresh_failed': refresh_failed}

# --- finance:0194 · from 08_reliability_tasks.py:1559 · public _v158_add_income_annotations_from_description ---
def _v158_add_income_annotations_from_description(rows: list[list], comments: dict) -> dict:
    out = dict(comments or {})
    header_seen = False
    for r_idx, raw in enumerate(rows or [], start=1):
        row = list(raw or [])
        first = str(row[0] if row else '').strip().casefold()
        second = str(row[1] if len(row) > 1 else '').strip()
        second_cf = second.casefold()
        is_header = first in {'дата', 'date'} and second_cf in {'описание', 'description', 'приход/выдача', 'amount'}
        if is_header:
            header_seen = True
            continue
        if first in {'ars', 'usd'} and (not second):
            header_seen = False
            continue
        if not header_seen:
            continue
        note = _v158_real_operation_description(second)
        if not note:
            continue
        income = row[2] if len(row) > 2 else ''
        if _excel_nonempty(income):
            out[r_idx, 3] = note
    return out

# --- finance:0195 · from 08_reliability_tasks.py:2907 · public _canon_delete_auto_finance_windows_for_chat__001 ---
def _canon_delete_auto_finance_windows_for_chat__001(chat_id: int, *, persist_now: bool=False) -> int:
    chat_id = int(chat_id)
    store = get_chat_store(chat_id)
    ids = set()
    try:
        ids.update((int(v) for v in (get_or_create_active_windows(chat_id) or {}).values() if v))
    except Exception:
        pass
    try:
        if store.get('balance_panel_id'):
            ids.add(int(store.get('balance_panel_id')))
    except Exception:
        pass
    data.setdefault('active_messages', {})[str(chat_id)] = {}
    store['balance_panel_id'] = None
    store['balance_panel_mode'] = 'mini'
    store['main_window_msg_count'] = 0
    store['balance_panel_msg_count'] = 0
    state = _finance_window_state(chat_id)
    state['main_windows'] = {}
    state['balance_panel_id'] = None
    state['balance_panel_mode'] = 'mini'
    state['auto_reopen_on_boot'] = False if finance_window_mode(chat_id) == 'off' else state.get('auto_reopen_on_boot', True)
    state['updated_at'] = now_local().isoformat(timespec='seconds')
    for mid in sorted(ids):
        try:
            unregister_open_window(chat_id, mid)
        except Exception:
            pass
    try:
        save_data(data, chat_ids=[chat_id])
    except Exception:
        pass
    if persist_now:
        try:
            _persist_finance_window_mode_critical(chat_id)
        except Exception:
            pass
    else:
        try:
            schedule_quick_backup(chat_id, 0.2)
        except Exception:
            pass

    def _delete_batch():
        removed = 0
        for mid in sorted(ids):
            try:
                bot.delete_message(chat_id, int(mid))
                removed += 1
            except Exception:
                pass
        try:
            bot_journal('finance_windows_deleted_async', chat_id, f'requested={len(ids)} deleted={removed}')
        except Exception:
            pass
    if ids:
        try:
            if not MAINTENANCE_TASK_POOL.submit(f'v160-fin-window-delete:{chat_id}', _delete_batch):
                _v160_schedule(f'v160-fin-delete-fallback:{chat_id}', 0.05, _delete_batch)
        except Exception:
            _v160_schedule(f'v160-fin-delete-fallback:{chat_id}', 0.05, _delete_batch)
    return len(ids)

# --- finance:0196 · from 08_reliability_tasks.py:6852 · public _v177_legacy_0197_build_finance_toggle_chat_menu ---
def _v177_legacy_0197_build_finance_toggle_chat_menu(day_key: str):
    level = _v164_current_window_circle('finmode', 1)
    kb = types.InlineKeyboardMarkup(row_width=2)
    buttons = []
    for cid in _v164_scope_ids(level, current_state_chat_id()):
        try:
            if is_chat_bot_removed(cid):
                continue
        except Exception:
            pass
        icon = finance_mode_compact_icon(cid)
        buttons.append(IB(f'{icon} {chat_button_title(cid, get_chat_display_name(cid))}', callback_data=f'd:{day_key}:fw_finmode_pick_{cid}'))
    add_buttons_in_rows(kb, buttons, 2)
    if not buttons:
        kb.row(IB('Нет чатов этого круга', callback_data='none'))
    kb.row(_v164_circle_switch_button('finmode', level))
    kb.row(IB('ℹ️ Описание чатов', callback_data='chat_desc_menu:finmode'))
    kb.row(IB('🔙 Назад', callback_data=f'd:{day_key}:back_main'))
    return kb

# --- finance:0197 · from 08_reliability_tasks.py:6876 · public _canon_build_quick_balance_mode_menu__001 ---
def _canon_build_quick_balance_mode_menu__001(day_key: str, target_chat_id: int):
    kb = _V164_PREV_BUILD_QUICK_BALANCE_MODE_MENU(day_key, target_chat_id)
    level = _v164_current_window_circle('finmode', circle_level_for_chat(int(target_chat_id)))
    try:
        if kb.keyboard:
            last = kb.keyboard[-1]
            if last and 'Назад' in str(getattr(last[0], 'text', '')):
                kb.keyboard[-1] = [IB('🔙 Назад к чатам', callback_data=f'v164:finback:{level}:{day_key}')]
    except Exception:
        pass
    return kb

# --- finance:0198 · from 08_reliability_tasks.py:6888 · public _canon_build_finance_mode_config_menu__001 ---
def _canon_build_finance_mode_config_menu__001(day_key: str, target_chat_id: int):
    return build_quick_balance_mode_menu(day_key, target_chat_id)

# --- finance:0199 · from 08_reliability_tasks.py:7104 · public _canon_build_finance_toggle_chat_menu__001 ---
def _canon_build_finance_toggle_chat_menu__001(day_key: str):
    """Finance-mode picker: owner + ordinary first circle, or second circle only."""
    level = _v164_current_window_circle('finmode', 1)
    kb = types.InlineKeyboardMarkup(row_width=2)
    buttons = []
    if int(level) == 1 and _v165_is_platform_owner_context():
        owner_item = _v165_owner_item(include_removed=True)
        if owner_item:
            oid, title = owner_item
            icon = finance_mode_compact_icon(oid)
            kb.row(IB(f'{icon} {chat_button_title(oid, title)}', callback_data=f'd:{day_key}:fw_finmode_pick_{oid}'))
    for cid in _v164_scope_ids(level, current_state_chat_id()):
        try:
            cid = int(cid)
        except Exception:
            continue
        if OWNER_ID and str(cid) == str(OWNER_ID):
            continue
        try:
            if is_chat_bot_removed(cid):
                continue
        except Exception:
            pass
        icon = finance_mode_compact_icon(cid)
        buttons.append(IB(f'{icon} {chat_button_title(cid, get_chat_display_name(cid))}', callback_data=f'd:{day_key}:fw_finmode_pick_{cid}'))
    add_buttons_in_rows(kb, buttons, 2)
    if not buttons and (not (int(level) == 1 and _v165_is_platform_owner_context())):
        kb.row(IB('Нет чатов этого круга', callback_data='none'))
    kb.row(_v164_circle_switch_button('finmode', level))
    kb.row(IB('ℹ️ Описание чатов', callback_data='chat_desc_menu:finmode'))
    kb.row(IB('🔙 Назад', callback_data=f'd:{day_key}:back_main'))
    return kb

# --- finance:0200 · from 08_reliability_tasks.py:7222 · public _v166_is_finance_business_callback ---
def _v166_is_finance_business_callback(raw: str) -> bool:
    """Callbacks that can create/delete/edit money stay serialized per chat."""
    low = str(raw or '').casefold()
    if low.startswith(('fw_new_fin:', 'fw_new_mode:', 'fw_new_clear:', 'fw_mode:', 'fw_finpair:', 'fw_clear:')):
        return False
    hard_prefixes = ('fv:', 'fv_', 'edit_', 'del_', 'delete_', 'expense_', 'income_', 'rec_', 'record_', 'usd_edit', 'usd_del', 'cat_move', 'cat_delete')
    if low.startswith(hard_prefixes):
        return True
    dangerous = ('delete_selected', 'apply', 'save', 'confirm', 'finance_off', 'fin_mode_', 'qb_mode_', 'qb_hidden_')
    if any((token in low for token in dangerous)):
        return True
    if low.startswith('d:'):
        try:
            cmd = low.split(':', 2)[2]
        except Exception:
            cmd = low
        safe_tokens = ('info', 'back_main', 'forward_menu', 'forward_finmode_menu', 'calendar', 'articles_toggle', 'financial_values_toggle', 'usd_tx_toggle', 'usd_display_toggle')
        if any((token in cmd for token in safe_tokens)):
            return False
        if any((token in cmd for token in ('delete', 'edit', 'save', 'apply', 'fin_mode_', 'qb_mode_', 'qb_hidden_'))):
            return True
    return False

# --- finance:0201 · from 08_reliability_tasks.py:7625 · public _v166_enable_hidden_finance_memory ---
def _v166_enable_hidden_finance_memory(dst_chat_id: int):
    dst_chat_id = int(dst_chat_id)
    with locked_chat(dst_chat_id):
        store = get_chat_store(dst_chat_id)
        settings = store.setdefault('settings', {})
        was_enabled = bool(store.get('finance_mode', False))
        store['finance_mode'] = True
        try:
            finance_active_chats.add(dst_chat_id)
        except Exception:
            pass
        settings['hidden_finance'] = True
        if not was_enabled:
            settings['quick_balance_enabled'] = False
            settings['quick_balance_behavior'] = 'normal'
            settings['quick_balance_user_selected'] = True
            state = store.get('finance_window_state')
            if not isinstance(state, dict):
                state = {}
            state.update({'mode': 'off', 'main_windows': {}, 'balance_panel_id': None, 'balance_panel_mode': 'mini', 'current_view_day': str(store.get('current_view_day') or today_key()), 'auto_reopen_on_boot': False, 'updated_at': now_local().isoformat(timespec='seconds')})
            store['finance_window_state'] = state
    _v166_schedule_forward_persist(dst_chat_id)

# --- finance:0202 · from 08_reliability_tasks.py:7758 · public _canon_refresh_balance_panel_now__001 ---
def _canon_refresh_balance_panel_now__001(chat_id: int):
    if callable(_V166_PREV_REFRESH_BALANCE):
        _v166_fin_submit(f'balance:{int(chat_id)}', _V166_PREV_REFRESH_BALANCE, int(chat_id))

# --- finance:0203 · from 08_reliability_tasks.py:7892 · public _finance_root_persist_job_v243 ---
def _finance_root_persist_job_v243(chat_id: int) -> None:
    """Persist derived finance root state without nesting data_lock -> SQLite.lock (R36)."""
    try:
        import copy as _r36_copy
        with data_lock:
            data.setdefault('_state_meta', {})['last_saved_at'] = now_local().isoformat(timespec='seconds')
            data['_state_meta']['bot_version'] = VERSION
            root_snapshot = _r36_copy.deepcopy(_sqlite_pack_root(data))
        SQLITE.save_root(root_snapshot)
        try:
            bot_journal('finance_root_persist_v243', int(chat_id), 'background root persisted')
        except Exception:
            pass
    except Exception as exc:
        try:
            log_error(f'finance root persist v243 {chat_id}: {exc}')
        except Exception:
            pass

# --- finance:0204 · from 08_reliability_tasks.py:7911 · public schedule_finance_root_persist_v243 ---
def schedule_finance_root_persist_v243(chat_id: int, delay: float=0.45) -> None:
    cid = int(chat_id)

    def _fire():
        pool = globals().get('BACKGROUND_TASK_POOL')
        if pool is None or not pool.submit(f'finance-root:{cid}', _finance_root_persist_job_v243, cid):
            _finance_root_persist_job_v243(cid)
    try:
        DELAYED_SCHEDULER.cancel(f'finance-root-persist:{cid}')
        DELAYED_SCHEDULER.schedule(f'finance-root-persist:{cid}', max(0.05, float(delay)), _fire)
    except Exception:
        _fire()

# --- finance:0205 · from 08_reliability_tasks.py:7924 · public _finance_postcommit_background_v243 ---
def _finance_postcommit_background_v243(chat_id: int, reason: str='change') -> None:
    cid = int(chat_id)
    try:
        rebuild_global_records()
    except Exception as exc:
        try:
            log_error(f'rebuild_global_records background v243 {cid}: {exc}')
        except Exception:
            pass
    _finance_root_persist_job_v243(cid)
    try:
        schedule_full_backup_only(cid, BACKUP_MIN_DELAY_SECONDS)
    except Exception:
        pass
    try:
        bot_journal('finance_postcommit_background_v243', cid, f'reason={reason}')
    except Exception:
        pass

# --- finance:0206 · from 08_reliability_tasks.py:7943 · public schedule_finance_postcommit_background_v243 ---
def schedule_finance_postcommit_background_v243(chat_id: int, reason: str='change', delay: float=0.25) -> None:
    cid = int(chat_id)

    def _fire():
        pool = globals().get('BACKGROUND_TASK_POOL')
        if pool is None or not pool.submit(f'finance-post:{cid}', _finance_postcommit_background_v243, cid, str(reason)):
            _finance_postcommit_background_v243(cid, str(reason))
    try:
        DELAYED_SCHEDULER.cancel(f'finance-postcommit:{cid}')
        DELAYED_SCHEDULER.schedule(f'finance-postcommit:{cid}', max(0.05, float(delay)), _fire)
    except Exception:
        _fire()

# --- finance:0207 · from 08_reliability_tasks.py:8008 · public finance_changed ---
def finance_changed(chat_id: int, day_key: str | None=None, reason: str='change', delay: float=0.05):
    chat_id = int(chat_id)
    day_key = day_key or get_chat_store(chat_id).get('current_view_day') or today_key()
    try:
        requested = max(0.0, float(delay))
    except Exception:
        requested = 0.05
    effective = min(requested, 0.1)
    bot_journal('finance_changed_scheduled', chat_id, f'day={day_key} reason={reason} delay={effective} v189=single_refresh')

    def _job():
        if not FINANCE_TASK_POOL.submit(chat_id, _finance_changed_now, chat_id, day_key, reason):
            try:
                log_error(f'FINANCE QUEUE FULL, RETRY: {chat_id}')
            except Exception:
                pass
            V166_FINANCE_DEBOUNCE_SCHEDULER.schedule(f'finance-finalize:{chat_id}', 0.25, _fire)

    def _fire():
        with timer_lock:
            _finalize_timers.pop(chat_id, None)
        _job()
    with timer_lock:
        _finalize_timers[chat_id] = _v166_time.time() + effective
    try:
        V166_FINANCE_DEBOUNCE_SCHEDULER.cancel(f'finance-finalize:{chat_id}')
    except Exception:
        pass
    V166_FINANCE_DEBOUNCE_SCHEDULER.schedule(f'finance-finalize:{chat_id}', effective, _fire)

# --- finance:0208 · from 08_reliability_tasks.py:14690 · public contour_visible_finance_enabled ---
def contour_visible_finance_enabled(chat_id: int) -> bool:
    try:
        return bool(is_finance_mode(int(chat_id)) and finance_window_mode(int(chat_id)) in {'normal', 'open', 'first'})
    except Exception:
        return False

# --- finance:0209 · from 08_reliability_tasks.py:14725 · public _v213_clear_finance_active_pointer ---
def _v213_clear_finance_active_pointer(chat_id: int) -> None:
    cid = int(chat_id)
    try:
        store = get_chat_store(cid)
        day = str(store.get('current_view_day') or today_key())[:10]
        try:
            clear_active_window_id(cid, day)
        except Exception:
            pass
        try:
            state = _finance_window_state(cid)
            if finance_window_mode(cid) == 'off':
                state['main_windows'] = {}
                state['balance_panel_id'] = None
                state['auto_reopen_on_boot'] = False
        except Exception:
            pass
    except Exception:
        pass

# --- finance:0210 · from 08_reliability_tasks.py:15020 · public _canon_apply_finance_window_mode_choice__002 ---
def _canon_apply_finance_window_mode_choice__002(chat_id: int, selected_mode: str) -> str:
    result = _V213_PREV_FIN_MODE_CHOICE(int(chat_id), selected_mode)
    try:
        if result == 'off':
            DELAYED_SCHEDULER.schedule(f'contour-home-mode:{int(chat_id)}', 0.1, lambda cid=int(chat_id): open_resolved_contour_home(cid, 0, 0))
    except Exception:
        pass
    return result

# --- finance:0211 · from 10_split_policy_offload.py:54 · public finance_origin_identity_v262 ---
def finance_origin_identity_v262(chat_id: int, rec: dict | None, fallback_msg_id: int=0):
    """Return immutable (source_chat_id, source_message_id, origin_key)."""
    cid = _v262_int(chat_id)
    rec = rec if isinstance(rec, dict) else {}
    src_chat, src_msg = _v262_origin_tuple_from_key(rec.get('finance_origin_key_v262'))
    if not (src_chat and src_msg):
        src_chat = _v262_int(rec.get('forward_source_chat_id'))
        src_msg = _v262_int(rec.get('forward_source_msg_id'))
    if not (src_chat and src_msg):
        src_chat, src_msg = _v262_origin_tuple_from_operation(rec.get('operation_key'))
    if not (src_chat and src_msg):
        try:
            ident = globals().get('_forward_copy_record_identity')
            if callable(ident):
                is_copy, _dst_mid, rchat, rmsg = ident(cid, rec)
                if is_copy and rchat and rmsg:
                    src_chat, src_msg = int(rchat), int(rmsg)
        except Exception:
            pass
    if not src_chat:
        src_chat = cid
    if not src_msg:
        for key in ('source_msg_id', 'origin_msg_id', 'msg_id', 'source_order_msg_id'):
            src_msg = _v262_int(rec.get(key))
            if src_msg:
                break
    if not src_msg:
        src_msg = _v262_int(fallback_msg_id)
    key = f'fin-origin:{int(src_chat)}:{int(src_msg)}' if src_chat and src_msg else ''
    return (int(src_chat or 0), int(src_msg or 0), key)

# --- finance:0212 · from 10_split_policy_offload.py:86 · public _ensure_finance_origin_key_v262 ---
def _ensure_finance_origin_key_v262(chat_id: int, rec: dict | None, fallback_msg_id: int=0) -> str:
    if not isinstance(rec, dict):
        return ''
    src_chat, src_msg, key = finance_origin_identity_v262(int(chat_id), rec, fallback_msg_id)
    if key:
        rec['finance_origin_key_v262'] = key
        rec.setdefault('finance_origin_chat_id_v262', int(src_chat))
        rec.setdefault('finance_origin_msg_id_v262', int(src_msg))
    return key

# --- finance:0213 · from 10_split_policy_offload.py:405 · public apply_linked_finance_edit_v262 ---
def apply_linked_finance_edit_v262(anchor_chat_id: int, anchor_rec: dict, *, update_ars: bool=True, amount=None, note=None, replace_usd: bool=False, usd_amount=None, usd_note=None, usd_only=None, source_text: str | None=None, full_text_replace: bool=False, repaint_copies: bool=True, source_kind: str='edit') -> bool:
    """Atomically mutate all locally known rows for one Telegram-origin operation.

    Local SQLite is committed before returning. Heavy window repaint, Google/MEGA/delta and
    copy rendering are allowed to run on the established background paths.
    """
    if not isinstance(anchor_rec, dict):
        return False
    try:
        if globals().get('constitution_finance_write_blocked_v232') and constitution_finance_write_blocked_v232():
            return False
    except Exception:
        pass
    anchor_chat_id = int(anchor_chat_id)
    origin_chat_id, origin_msg_id, origin_key = finance_origin_identity_v262(anchor_chat_id, anchor_rec)
    if not origin_key:
        return False
    op_id = ''
    try:
        if callable(globals().get('operation_begin')):
            op_id = operation_begin('finance_linked_edit_v262', anchor_chat_id, target=origin_key, payload={'source': source_kind, 'update_ars': bool(update_ars), 'replace_usd': bool(replace_usd)}, critical=True)
    except Exception:
        op_id = ''
    touched_days = {}
    changed_total = 0
    changed_by_chat = {}
    with _V262_FINANCE_LINK_LOCK:
        _ensure_finance_origin_key_v262(anchor_chat_id, anchor_rec)
        try:
            source_store = get_chat_store(int(origin_chat_id)) if origin_chat_id and origin_msg_id else {}
            source_rec = next((r for r in source_store.get('records', []) or [] if isinstance(r, dict) and callable(globals().get('_record_has_message_id')) and _record_has_message_id(r, int(origin_msg_id))), None)
        except Exception:
            source_rec = None
        if not isinstance(source_rec, dict):
            source_rec = _v262_heal_missing_source(origin_chat_id, origin_msg_id, origin_key, anchor_rec, update_ars=update_ars, amount=amount, note=note, replace_usd=replace_usd, usd_amount=usd_amount, usd_note=usd_note, usd_only=usd_only, source_text=source_text)
        locations = _v262_linked_locations(origin_chat_id, origin_msg_id, anchor_chat_id, anchor_rec)
        target_chats = {int(cid) for cid, _mid in locations if cid}
        target_chats.add(anchor_chat_id)
        if origin_chat_id:
            target_chats.add(int(origin_chat_id))
        for cid in sorted(target_chats):
            try:
                with locked_chat(int(cid)):
                    _v262_tag_store_origins(int(cid))
                    rows = _v262_records_for_origin(int(cid), origin_key)
                    if not rows:
                        # Exact message fallback keeps old pre-v260 rows editable.
                        for loc_cid, loc_mid in locations:
                            if int(loc_cid) != int(cid) or not loc_mid:
                                continue
                            rec = find_record_by_message_id(int(cid), int(loc_mid))
                            if isinstance(rec, dict):
                                rec['finance_origin_key_v262'] = origin_key
                                rec['finance_origin_chat_id_v262'] = int(origin_chat_id)
                                rec['finance_origin_msg_id_v262'] = int(origin_msg_id)
                                rows = _v262_records_for_origin(int(cid), origin_key)
                                if rows:
                                    break
                    if not rows:
                        continue
                    before_primary = None
                    changed_here = 0
                    try:
                        _active_before = sum(float(r.get('amount', 0) or 0) for r in get_chat_store(int(cid)).get('records', []) or [] if isinstance(r, dict) and _ensure_finance_origin_key_v262(int(cid), r) == origin_key)
                        _usd_before = sum(float(r.get('usd_amount', 0) or 0) for r in get_chat_store(int(cid)).get('records', []) or [] if isinstance(r, dict) and _ensure_finance_origin_key_v262(int(cid), r) == origin_key)
                    except Exception:
                        _active_before = 0.0; _usd_before = 0.0
                    for _ledger, rec in rows:
                        before = _v262_update_one_record(rec, update_ars=update_ars, amount=amount, note=note, replace_usd=replace_usd, usd_amount=usd_amount, usd_note=usd_note, usd_only=usd_only, source_text=source_text, full_text_replace=full_text_replace)
                        _ensure_finance_origin_key_v262(int(cid), rec)
                        if before != rec:
                            changed_here += 1
                            if before_primary is None:
                                before_primary = before
                    store = get_chat_store(int(cid))
                    # Keep daily mirrors/currency mirrors coherent even if they are separate objects.
                    for daily_key in ('daily_records', 'ars_daily_records', 'usd_daily_records'):
                        for _dk, arr in (store.get(daily_key, {}) or {}).items():
                            for rec in arr or []:
                                if isinstance(rec, dict) and _ensure_finance_origin_key_v262(int(cid), rec) == origin_key:
                                    _v262_update_one_record(rec, update_ars=update_ars, amount=amount, note=note, replace_usd=replace_usd, usd_amount=usd_amount, usd_note=usd_note, usd_only=usd_only, source_text=source_text, full_text_replace=full_text_replace)
                    try:
                        active = _ensure_currency_ledgers(store)
                        _snapshot_active_currency_ledger(store, active)
                    except Exception:
                        pass
                    # R16: edit only the touched operation. Avoid normalize/sort/short-id rebuild
                    # and a full balance sum in the Telegram hot transaction.
                    try:
                        _active_after = sum(float(r.get('amount', 0) or 0) for r in store.get('records', []) or [] if isinstance(r, dict) and _ensure_finance_origin_key_v262(int(cid), r) == origin_key)
                        store['balance'] = float(store.get('balance', 0) or 0) + (_active_after - _active_before)
                    except Exception:
                        pass
                    store['_finance_hotpath_pending_normalize_r16'] = True
                    store['_finance_fast_generation_r16'] = int(store.get('_finance_fast_generation_r16', 0) or 0) + 1
                    store.pop('_finance_day_balance_cache_r16', None)
                    if replace_usd and '_usd_balance_cache_r16' in store:
                        try:
                            _usd_after = sum(float(r.get('usd_amount', 0) or 0) for r in store.get('records', []) or [] if isinstance(r, dict) and _ensure_finance_origin_key_v262(int(cid), r) == origin_key)
                            store['_usd_balance_cache_r16'] = float(store.get('_usd_balance_cache_r16', 0) or 0) + (_usd_after - _usd_before)
                        except Exception: store.pop('_usd_balance_cache_r16', None)
                    current = _v262_records_for_origin(int(cid), origin_key)
                    primary = current[0][1] if current else rows[0][1]
                    touched_days[int(cid)] = str(primary.get('day_key') or store.get('current_view_day') or today_key())
                    _r48_primary = copy.deepcopy(primary) if isinstance(primary, dict) else primary
                    _r48_before_primary = copy.deepcopy(before_primary or {})
                    _r48_changed_here = int(changed_here or 0)
                if not persist_finance_chat_local_fast(int(cid)):
                    raise RuntimeError('local SQLite finance persist failed')
                if _r48_changed_here:
                    changed_total += _r48_changed_here
                    changed_by_chat[int(cid)] = _r48_changed_here
                    try: finance_cache_invalidate(int(cid), 'linked_edit_v262')
                    except Exception: pass
                    try: finance_integrity_append(int(cid), 'edit', _r48_primary, details={'before': _r48_before_primary, 'source': source_kind, 'origin_key': origin_key})
                    except Exception as exc:
                        try: log_error(f'v262 finance integrity {cid}: {exc}')
                        except Exception: pass
            except Exception as exc:
                try:
                    log_error(f'v262 linked edit {origin_key} chat={cid}: {exc}')
                except Exception:
                    pass
                if op_id and callable(globals().get('operation_review')):
                    try: operation_review(op_id, f'chat={cid}: {exc}')
                    except Exception: pass
                return False
    # No-op is success: repeated Telegram delivery must never create a duplicate.
    try:
        bot_journal('finance_linked_edit_v262', anchor_chat_id, f'origin={origin_key}; source={source_kind}; chats={len(touched_days)}; changed={changed_total}; per_chat={changed_by_chat}')
    except Exception:
        pass
    try:
        pool = globals().get('GENERAL_TASK_POOL') or globals().get('FINANCE_TASK_POOL')
        key = f'v262-linked-post:{origin_chat_id}:{origin_msg_id}'
        if pool is not None and hasattr(pool, 'submit'):
            # Ordered per-origin queue: a fast second edit must not lose its final repaint.
            pool.submit(key, _v262_postcommit_linked_edit, int(origin_chat_id), int(origin_msg_id), dict(touched_days), bool(repaint_copies))
        else:
            _v262_postcommit_linked_edit(int(origin_chat_id), int(origin_msg_id), dict(touched_days), bool(repaint_copies))
    except Exception:
        pass
    if op_id and callable(globals().get('operation_complete')):
        try:
            operation_complete(op_id, f'origin={origin_key}; chats={len(touched_days)}; changed={changed_total}')
        except Exception:
            pass
    return True

# --- finance:0214 · from 10_split_policy_offload.py:588 · public handle_finance_edit ---
def handle_finance_edit(msg):
    """Native Telegram long-tap edit uses the same linked-edit transaction."""
    chat_id = int(msg.chat.id)
    try:
        uid = _v262_int(getattr(getattr(msg, 'from_user', None), 'id', 0))
        if 'v152_chat_permission_allowed' in globals() and '_v152_actor_is_platform_owner' in globals():
            if not _v152_actor_is_platform_owner(uid) and (not v152_chat_permission_allowed(chat_id, 'finance.edit')):
                try: send_and_auto_delete(chat_id, '⛔ Редактирование операций запрещено правами этого чата.', 8)
                except Exception: pass
                return False
    except Exception:
        pass
    try:
        if globals().get('constitution_finance_write_blocked_v232') and constitution_finance_write_blocked_v232():
            return True
    except Exception:
        pass
    text = str(getattr(msg, 'text', None) or getattr(msg, 'caption', None) or '').strip()
    anchor_chat_id = chat_id
    target = find_record_by_message_id(chat_id, int(msg.message_id)) if callable(globals().get('find_record_by_message_id')) else None
    if not isinstance(target, dict):
        try:
            store = get_chat_store(chat_id)
            for rec in store.get('records', []) or []:
                if isinstance(rec, dict) and int(msg.message_id) in {_v262_int(rec.get(k)) for k in ('source_msg_id', 'origin_msg_id', 'msg_id', 'source_order_msg_id')}:
                    target = rec
                    break
        except Exception:
            pass
    # OCH12.26: an edited source message may have created finance only in a linked
    # destination chat.  In that case there is correctly no source-chat record.
    # Follow the durable forward map and use the destination record as the linked
    # edit anchor instead of reporting a false "record not found".
    if not isinstance(target, dict):
        try:
            links = list(get_forward_links(int(chat_id), int(msg.message_id)) or []) if callable(globals().get('get_forward_links')) else []
            for dst_chat_id, dst_msg_id in links:
                rec = find_record_by_message_id(int(dst_chat_id), int(dst_msg_id)) if callable(globals().get('find_record_by_message_id')) else None
                if isinstance(rec, dict):
                    target = rec; anchor_chat_id = int(dst_chat_id)
                    try: bot_journal('finance_edit_anchor_from_forward_v1225', int(chat_id), f'source={chat_id}:{msg.message_id}; anchor={anchor_chat_id}:{dst_msg_id}')
                    except Exception: pass
                    break
        except Exception:
            pass
    if not isinstance(target, dict):
        try: log_info(f'[EDIT-FIN v262] record not found msg={msg.message_id}')
        except Exception: pass
        return False
    if text and looks_like_amount(text):
        try:
            comp = parse_financial_components(text)
        except Exception:
            comp = {'amount': 0.0, 'note': 'удалено', 'usd_amount': None, 'usd_note': '', 'usd_only': False, 'source_finance_text': text}
    else:
        comp = {'amount': 0.0, 'note': 'удалено', 'usd_amount': None, 'usd_note': '', 'usd_only': False, 'source_finance_text': text}
    return apply_linked_finance_edit_v262(anchor_chat_id, target, update_ars=True, amount=float(comp.get('amount') or 0), note=str(comp.get('note') or ''), replace_usd=True, usd_amount=comp.get('usd_amount'), usd_note=str(comp.get('usd_note') or ''), usd_only=bool(comp.get('usd_only', False)), source_text=str(comp.get('source_finance_text') or text), full_text_replace=True, repaint_copies=False, source_kind='telegram_native_edit')

# --- finance:0215 · from 10_split_policy_offload.py:647 · public _v262_finance_postcommit_job ---
def _v262_finance_postcommit_job(chat_id: int, day_key: str, reason: str):
    try:
        if callable(globals().get('rebuild_global_records')):
            rebuild_global_records()
    except Exception:
        pass
    try:
        if callable(globals().get('schedule_financial_window_refresh')):
            schedule_financial_window_refresh(int(chat_id), str(day_key or ''), reason=str(reason or 'finance_postcommit_v262'))
    except Exception:
        pass
    try:
        if callable(globals().get('finance_changed')):
            finance_changed(int(chat_id), str(day_key or ''), reason=str(reason or 'finance_postcommit_v262'), delay=0.05)
    except Exception:
        pass

# --- finance:0216 · from 10_split_policy_offload.py:665 · public _v262_schedule_finance_postcommit ---
def _v262_schedule_finance_postcommit(chat_id: int, day_key: str, reason: str='finance_postcommit_v262'):
    cid = int(chat_id); key = f'v262-fin-post:{cid}'
    try:
        pool = globals().get('FINANCE_TASK_POOL') or globals().get('GENERAL_TASK_POOL')
        if pool is not None and hasattr(pool, 'submit') and pool.submit(key, _v262_finance_postcommit_job, cid, str(day_key or ''), str(reason or 'finance_postcommit_v262')):
            return True
    except Exception:
        pass
    try:
        DELAYED_SCHEDULER.schedule(key, 0.05, _v262_finance_postcommit_job, cid, str(day_key or ''), str(reason or 'finance_postcommit_v262'))
        return True
    except Exception:
        return False

# --- finance:0217 · from 10_split_policy_offload.py:707 · public toggle_usd_edit_delete_selection ---
def toggle_usd_edit_delete_selection(chat_id: int, day_key: str, rid: int):
    store = get_chat_store(int(chat_id)); all_sel = store.setdefault('usd_edit_delete_selected', {})
    selected = {int(x) for x in all_sel.get(str(day_key), []) or []}; rid = int(rid)
    selected.discard(rid) if rid in selected else selected.add(rid)
    if selected: all_sel[str(day_key)] = sorted(selected)
    else: all_sel.pop(str(day_key), None)

# --- finance:0218 · from 10_split_policy_offload.py:715 · public clear_usd_edit_delete_selection ---
def clear_usd_edit_delete_selection(chat_id: int, day_key: str | None=None):
    all_sel = get_chat_store(int(chat_id)).setdefault('usd_edit_delete_selected', {})
    all_sel.clear() if day_key is None else all_sel.pop(str(day_key), None)

# --- finance:0219 · from 10_split_policy_offload.py:733 · public set_usd_transactions_view ---
def set_usd_transactions_view(chat_id: int, enabled: bool):
    """Display preference: apply instantly, persist chat asynchronously, never config-checkpoint it."""
    store = get_chat_store(int(chat_id))
    store.setdefault('settings', {})['usd_transactions_view'] = bool(enabled)
    _v262_schedule_transient_chat_persist(int(chat_id))

# --- finance:0220 · from 10_split_policy_offload.py:3396 · public _r7_finance_changed_now ---
def _r7_finance_changed_now(chat_id: int, day_key: str | None=None, reason: str='change'):
    """R7: local finance commit stays synchronous; all derived work is one debounced pass."""
    chat_id = int(chat_id)
    day_key = str(day_key or get_chat_store(chat_id).get('current_view_day') or today_key())[:10]
    try:
        finance_cache_invalidate(chat_id, f'finance_changed:{reason}:r7')
    except Exception:
        pass
    with locked_chat(chat_id):
        store = get_chat_store(chat_id)
        store['current_view_day'] = day_key
        # One normalization only.  Older path normalized inside recalc and again in
        # rebuild_month_short_ids, which was noticeable on chats with long histories.
        normalize_chat_records(chat_id)
        store = get_chat_store(chat_id)
        store.pop('_finance_hotpath_pending_normalize_r15', None)
        store.pop('_finance_hotpath_pending_normalize_r16', None)
        store['balance'] = sum(float(r.get('amount', 0) or 0) for r in store.get('records', []) or [] if isinstance(r, dict))
        _r7_rebuild_month_short_ids_after_normalize(chat_id, store)
        try:
            _snapshot_active_currency_ledger(store, _ensure_currency_ledgers(store))
        except Exception:
            pass
        _r48_need_persist = True
    if callable(globals().get('persist_finance_chat_local_fast')):
        persist_finance_chat_local_fast(chat_id)
    # Nothing below blocks the Telegram handler or holds chat_lock.
    try:
        schedule_quick_backup(chat_id, MEGA_DELTA_PRIORITY_DELAY_SECONDS if mega_backup_priority_enabled() else MEGA_DELTA_DELAY_SECONDS)
    except Exception:
        pass
    try:
        schedule_financial_window_refresh(chat_id, day_key, reason=f'r7:{reason}', delay=0.015)
    except Exception:
        pass
    try:
        schedule_finance_postcommit_background_v243(chat_id, reason=f'r7:{reason}', delay=0.30)
    except Exception:
        pass

# --- finance:0221 · from 10_split_policy_offload.py:3467 · public _r7_v262_finance_postcommit_job ---
def _r7_v262_finance_postcommit_job(chat_id: int, day_key: str, reason: str):
    cid=int(chat_id); dk=str(day_key or '')
    try: finance_cache_invalidate(cid, f'r7:{reason}')
    except Exception: pass
    try: schedule_financial_window_refresh(cid, dk, reason=f'r16-fast:{reason}', delay=0.01)
    except Exception: pass
    try: finance_changed(cid, dk, reason=f'r16-reconcile:{reason}', delay=0.18)
    except Exception: pass

# --- finance:0222 · from 10_split_policy_offload.py:10939 · public _r77_finance_reconcile_job ---
def _r77_finance_reconcile_job(chat_id: int, reason: str='finance_hotpath'):
    cid = int(chat_id)
    started = time.monotonic()
    dirty = False
    try:
        with locked_chat(cid):
            store = get_chat_store(cid)
            dirty = bool(store.get('_finance_hotpath_pending_normalize_r16') or store.get('_finance_hotpath_pending_normalize_r15'))
            if dirty:
                normalize_chat_records(cid)
                store = get_chat_store(cid)
                store.pop('_finance_hotpath_pending_normalize_r15', None)
                store.pop('_finance_hotpath_pending_normalize_r16', None)
                store['balance'] = sum(float(r.get('amount', 0) or 0) for r in store.get('records', []) or [] if isinstance(r, dict))
                try:
                    _r7_rebuild_month_short_ids_after_normalize(cid, store)
                except Exception:
                    pass
                try:
                    _snapshot_active_currency_ledger(store, _ensure_currency_ledgers(store))
                except Exception:
                    pass
        if dirty:
            if callable(globals().get('persist_finance_chat_local_fast')):
                persist_finance_chat_local_fast(cid)
            try:
                schedule_quick_backup(cid, MEGA_DELTA_PRIORITY_DELAY_SECONDS if mega_backup_priority_enabled() else MEGA_DELTA_DELAY_SECONDS)
            except Exception:
                pass
            try:
                schedule_finance_postcommit_background_v243(cid, reason=f'r77:{reason}', delay=0.45)
            except Exception:
                pass
        with _R77_FIN_STATS_LOCK:
            _R77_FIN_STATS['runs'] += 1
            _R77_FIN_STATS['persisted'] += int(bool(dirty))
            _R77_FIN_STATS['skipped_clean'] += int(not dirty)
            _R77_FIN_STATS['last_ms'] = round((time.monotonic()-started)*1000.0, 2)
            _R77_FIN_STATS['last_reason'] = str(reason or '')[:120]
        try:
            bot_journal('r77_finance_reconcile_done', cid, f'reason={reason}; dirty={int(bool(dirty))}; elapsed_ms={(time.monotonic()-started)*1000.0:.1f}')
        except Exception:
            pass
        return True
    except Exception as exc:
        with _R77_FIN_STATS_LOCK:
            _R77_FIN_STATS['errors'] += 1
            _R77_FIN_STATS['last_ms'] = round((time.monotonic()-started)*1000.0, 2)
            _R77_FIN_STATS['last_reason'] = str(reason or '')[:120]
        try:
            log_error(f'R77 finance reconcile {cid}: {exc}')
        except Exception:
            pass
        return False

# --- finance:0223 · from 10_split_policy_offload.py:10995 · public schedule_finance_reconcile_r77 ---
def schedule_finance_reconcile_r77(chat_id: int, day_key: str | None=None, reason: str='finance_hotpath', delay: float=0.45):
    """Coalesce full finance normalization behind the already-durable user commit.

    This path intentionally performs no Telegram repaint.  The caller already scheduled
    the one foreground repaint from the incremental committed state.
    """
    cid = int(chat_id)
    key = f'r77-fin-reconcile:{cid}'
    with _R77_FIN_STATS_LOCK:
        _R77_FIN_STATS['scheduled'] += 1
        _R77_FIN_STATS['last_reason'] = str(reason or '')[:120]
    def _fire():
        pool = globals().get('FINANCE_MAINT_TASK_POOL') or globals().get('FINANCE_TASK_POOL') or globals().get('BACKGROUND_TASK_POOL')
        submitted = False
        try:
            if pool is not None and hasattr(pool, 'submit_unique'):
                submitted = bool(pool.submit_unique(f'finance-maint:{cid}', _r77_finance_reconcile_job, cid, str(reason or 'finance_hotpath')))
            elif pool is not None and hasattr(pool, 'submit'):
                submitted = bool(pool.submit(f'finance-maint:{cid}', _r77_finance_reconcile_job, cid, str(reason or 'finance_hotpath')))
        except Exception:
            submitted = False
        if not submitted:
            # Never inline a full-ledger normalize into the user's callback/message thread.
            try:
                DELAYED_SCHEDULER.schedule(key, 0.35, _fire)
            except Exception:
                pass
    try:
        DELAYED_SCHEDULER.cancel(key)
        DELAYED_SCHEDULER.schedule(key, max(0.25, min(2.0, float(delay or 0.45))), _fire)
        return True
    except Exception:
        _fire()
        return True

# --- finance:0224 · from 10_split_policy_offload.py:12607 · public _och129_finance_record_text ---
def _och129_finance_record_text(rec: dict) -> str:
    try:
        raw = str((rec or {}).get('source_finance_text') or '').strip()
        if raw:
            return raw.replace('\r\n', '\n').replace('\r', '\n')
    except Exception:
        pass
    try:
        fn = globals().get('_v262_record_canonical_text')
        return str(fn(rec) if callable(fn) else '').strip().replace('\r\n', '\n').replace('\r', '\n')
    except Exception:
        return ''

# --- finance:0225 · from 10_split_policy_offload.py:12621 · public handle_finance_message ---
def handle_finance_message(msg):
    """Treat same chat/message identity after deploy as replay/edit, never a new operation."""
    try:
        cid = int(getattr(getattr(msg, 'chat', None), 'id', 0) or 0)
        mid = int(getattr(msg, 'message_id', 0) or 0)
    except Exception:
        cid = mid = 0
    if cid and mid:
        existing = None
        try:
            existing = find_record_by_message_id(cid, mid)
        except Exception:
            existing = None
        if isinstance(existing, dict):
            incoming = str(_message_text_for_finance(msg) or getattr(msg, 'caption', None) or getattr(msg, 'text', None) or '').strip().replace('\r\n', '\n').replace('\r', '\n')
            previous = _och129_finance_record_text(existing)
            if incoming != previous:
                # A Telegram update can be replayed as a normal `message` after a deploy.
                # Use the native linked-edit transaction, then repaint/reconcile old copies.
                try:
                    edited = bool(handle_finance_edit(msg))
                except Exception as exc:
                    edited = False
                    try: log_error(f'[FIN EDIT V263] replay-as-message edit failed {cid}:{mid}: {exc}')
                    except Exception: pass
                if edited:
                    try: schedule_propagate_edited_to_copies(msg)
                    except Exception: pass
                    try: bot_journal('finance_message_reclassified_as_edit_v263', cid, f'msg={mid}; old={previous[:120]!r}; new={incoming[:120]!r}')
                    except Exception: pass
                    return True
            # Identical redelivery: stable source identity is authoritative; no new row.
            try:
                bot_journal('finance_message_replay_blocked_v263', cid, f'msg={mid}; identical={int(incoming == previous)}')
            except Exception:
                pass
            return True
    if callable(_OCH129_PARENT_HANDLE_FINANCE_MESSAGE):
        return _OCH129_PARENT_HANDLE_FINANCE_MESSAGE(msg)
    return False

# v266
