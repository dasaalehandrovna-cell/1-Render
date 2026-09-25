# v266
"""ОЧНИСЬ 12.35 · physical owner: reminders.

Этот файл — единственное физическое место тел функций домена.
Он НЕ запускается отдельно и НЕ импортируется как Python-модуль.
bot.py читает его как каталог исходников и устанавливает нужную стадию в исторической точке runtime.
Последняя версия каждого публичного символа сохраняет обычное имя; старые стадии помечены _legacy_sXXXX_.
"""

# --- reminders:0001 · from 01_core_data.py:12069 · public _durable_reminder_witness_hash ---
def _durable_reminder_witness_hash(witness: dict) -> str:
    payload = {'reminder_id': int((witness or {}).get('reminder_id') or 0), 'kind': str((witness or {}).get('kind') or ''), 'text': str((witness or {}).get('text') or '').strip(), 'interval_minutes': int((witness or {}).get('interval_minutes') or 0)}
    return hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True).encode('utf-8')).hexdigest()[:24]

# --- reminders:0002 · from 01_core_data.py:12073 · public _durable_reminder_receipt_exists ---
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

# --- reminders:0003 · from 01_core_data.py:12086 · public _durable_note_reminder_edit_witness ---
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

# --- reminders:0004 · from 04_messages_features.py:1679 · public _v177_legacy_0117_reminder_ui_mode ---
def _v177_legacy_0117_reminder_ui_mode() -> str:
    mode = str(data.setdefault('_global_settings', {}).get('reminder_ui_mode_v142') or 'new').strip().lower()
    return mode if mode in {'old', 'new'} else 'new'

# --- reminders:0005 · from 04_messages_features.py:1687 · public reminder_ui_new_enabled ---
def reminder_ui_new_enabled() -> bool:
    return reminder_ui_mode() == 'new'

# --- reminders:0006 · from 04_messages_features.py:1690 · public _v177_legacy_0118_set_reminder_ui_mode ---
def _v177_legacy_0118_set_reminder_ui_mode(mode: str) -> str:
    mode = 'new' if str(mode).strip().lower() == 'new' else 'old'
    data.setdefault('_global_settings', {})['reminder_ui_mode_v142'] = mode
    try:
        _reminder_save('reminder_ui_mode')
    except Exception:
        save_data(data, root_only=True)
    return mode

# --- reminders:0007 · from 04_messages_features.py:1703 · public toggle_reminder_ui_mode ---
def toggle_reminder_ui_mode() -> str:
    return set_reminder_ui_mode('old' if reminder_ui_new_enabled() else 'new')

# --- reminders:0008 · from 04_messages_features.py:1706 · public reminder_ui_mode_label ---
def reminder_ui_mode_label() -> str:
    return '⏰ Напоминалка: ПО-НОВОМУ' if reminder_ui_new_enabled() else '⏰ Напоминалка: ПО-СТАРОМУ'

# --- reminders:0009 · from 04_messages_features.py:1709 · public _reminder_owner_id ---
def _reminder_owner_id() -> int | None:
    try:
        return int(OWNER_ID) if OWNER_ID else None
    except Exception:
        return None

# --- reminders:0010 · from 04_messages_features.py:1715 · public _new_reminder_cfg ---
def _new_reminder_cfg() -> dict:
    return {'enabled': False, 'text': '', 'chat_ids': [], 'interval_minutes': 120, 'start_hour': 8, 'end_hour': 22, 'start_date': today_key(), 'end_date': '', 'next_run_at': '', 'last_sent_at': '', 'last_message_ids': {}, 'created_at': now_local().isoformat(timespec='seconds'), 'updated_at': now_local().isoformat(timespec='seconds'), 'completed_at': '', 'completion_reason': '', 'merge_mode_v207': None, 'show_complete_button_v207': None, 'completion_mode_v218': None, 'lifecycle_generation_v245': 1, 'delivery_cycle_v245': '', 'delivery_acked_chats_v245': []}

# --- reminders:0011 · from 04_messages_features.py:1718 · public _normalize_reminder_cfg ---
def _normalize_reminder_cfg(cfg: dict) -> dict:
    if not isinstance(cfg, dict):
        cfg = {}
    cfg.setdefault('enabled', False)
    cfg.setdefault('text', '')
    cfg.setdefault('chat_ids', [])
    cfg.setdefault('interval_minutes', 120)
    cfg.setdefault('start_hour', 8)
    cfg.setdefault('end_hour', 22)
    cfg.setdefault('start_date', today_key())
    cfg.setdefault('end_date', '')
    cfg.setdefault('next_run_at', '')
    cfg.setdefault('last_sent_at', '')
    cfg.setdefault('last_message_ids', {})
    cfg.setdefault('created_at', now_local().isoformat(timespec='seconds'))
    cfg.setdefault('updated_at', now_local().isoformat(timespec='seconds'))
    cfg.setdefault('completed_at', '')
    cfg.setdefault('completion_reason', '')
    cfg.setdefault('merge_mode_v207', None)
    cfg.setdefault('show_complete_button_v207', None)
    cfg.setdefault('completion_mode_v218', None)
    try:
        cfg['lifecycle_generation_v245'] = max(1, int(cfg.get('lifecycle_generation_v245') or 1))
    except Exception:
        cfg['lifecycle_generation_v245'] = 1
    cfg.setdefault('delivery_cycle_v245', '')
    cfg.setdefault('delivery_acked_chats_v245', [])
    return cfg

# --- reminders:0012 · from 04_messages_features.py:1747 · public _reminders_root ---
def _reminders_root() -> dict:
    """v135: несколько независимых напоминалок + миграция одиночной v134 в №1."""
    gs = data.setdefault('_global_settings', {})
    with _REMINDER_CONFIG_LOCK:
        root = gs.get('reminders_v2')
        if not isinstance(root, dict):
            root = {'next_id': 1, 'items': {}, 'migrated_v134': False}
            gs['reminders_v2'] = root
        items = root.setdefault('items', {})
        if not isinstance(items, dict):
            items = {}
            root['items'] = items
        root.setdefault('next_id', 1)
        root.setdefault('migrated_v134', False)
        if not bool(root.get('migrated_v134')):
            legacy = gs.get('reminder')
            if isinstance(legacy, dict) and any([str(legacy.get('text') or '').strip(), legacy.get('chat_ids'), legacy.get('last_message_ids'), legacy.get('enabled')]):
                cfg = _normalize_reminder_cfg(dict(legacy))
                cfg.pop('input_wait', None)
                cfg['updated_at'] = now_local().isoformat(timespec='seconds')
                items.setdefault('1', cfg)
                try:
                    root['next_id'] = max(int(root.get('next_id') or 1), 2)
                except Exception:
                    root['next_id'] = 2
                legacy['enabled'] = False
                legacy['next_run_at'] = ''
                legacy['migrated_to_reminders_v2'] = True
            root['migrated_v134'] = True
        for rid in list(items.keys()):
            if isinstance(items.get(rid), dict):
                items[str(rid)] = _normalize_reminder_cfg(items[rid])
        return root

# --- reminders:0013 · from 04_messages_features.py:1781 · public _v177_legacy_0119_reminder_items ---
def _v177_legacy_0119_reminder_items(include_completed: bool=False) -> list[tuple[int, dict]]:
    root = _reminders_root()
    rows = []
    for rid_raw, cfg in (root.get('items') or {}).items():
        try:
            rid = int(rid_raw)
        except Exception:
            continue
        if not isinstance(cfg, dict):
            continue
        cfg = _normalize_reminder_cfg(cfg)
        if not include_completed and str(cfg.get('completed_at') or '').strip():
            continue
        rows.append((rid, cfg))
    rows.sort(key=lambda x: x[0])
    return rows

# --- reminders:0014 · from 04_messages_features.py:1802 · public _reminder_completed_items ---
def _reminder_completed_items() -> list[tuple[int, dict]]:
    rows = []
    for rid, cfg in _reminder_items(include_completed=True):
        if str(cfg.get('completed_at') or '').strip():
            rows.append((rid, cfg))
    rows.sort(key=lambda x: (str(x[1].get('completed_at') or ''), x[0]), reverse=True)
    return rows

# --- reminders:0015 · from 04_messages_features.py:1810 · public _v177_legacy_0120_reminder_cfg ---
def _v177_legacy_0120_reminder_cfg(reminder_id: int | str | None=None, create: bool=False) -> dict | None:
    if reminder_id is None:
        rows = _reminder_items()
        return rows[0][1] if rows else None
    try:
        rid = int(reminder_id)
    except Exception:
        return None
    root = _reminders_root()
    items = root.setdefault('items', {})
    cfg = items.get(str(rid))
    if cfg is None and create:
        cfg = _new_reminder_cfg()
        items[str(rid)] = cfg
    return _normalize_reminder_cfg(cfg) if isinstance(cfg, dict) else None

# --- reminders:0016 · from 04_messages_features.py:1830 · public _v177_legacy_0121_reminder_create ---
def _v177_legacy_0121_reminder_create() -> tuple[int, dict]:
    with _REMINDER_CONFIG_LOCK:
        root = _reminders_root()
        try:
            rid = max(1, int(root.get('next_id') or 1))
        except Exception:
            rid = 1
        while str(rid) in (root.get('items') or {}):
            rid += 1
        cfg = _new_reminder_cfg()
        root.setdefault('items', {})[str(rid)] = cfg
        root['next_id'] = rid + 1
    _reminder_save('reminder_add')
    return (rid, cfg)

# --- reminders:0017 · from 04_messages_features.py:1849 · public _reminder_position ---
def _reminder_position(reminder_id: int) -> int:
    ids = [rid for rid, _cfg in _reminder_items()]
    try:
        return ids.index(int(reminder_id)) + 1
    except Exception:
        return 0

# --- reminders:0018 · from 04_messages_features.py:1856 · public _reminder_is_completed ---
def _reminder_is_completed(cfg: dict | None) -> bool:
    return bool(str((cfg or {}).get('completed_at') or '').strip())

# --- reminders:0019 · from 04_messages_features.py:1859 · public _reminder_return_callback ---
def _reminder_return_callback(page: int, day_key: str) -> str:
    if str(day_key) == 'completed':
        return f'rem:completed:{max(0, int(page))}'
    return f'rem:list:{max(0, int(page))}:{day_key}'

# --- reminders:0020 · from 04_messages_features.py:1864 · public _v177_legacy_0122_reminder_mark_completed ---
def _v177_legacy_0122_reminder_mark_completed(reminder_id: int, cfg: dict, reason: str='time_finished', delete_messages: bool=True) -> None:
    if _reminder_is_completed(cfg):
        return
    cfg['enabled'] = False
    cfg['next_run_at'] = ''
    cfg['completed_at'] = now_local().isoformat(timespec='seconds')
    cfg['completion_reason'] = str(reason or 'time_finished')
    cfg['delivery_cycle_v245'] = ''
    cfg['delivery_acked_chats_v245'] = []
    _reminder_touch(cfg)
    if delete_messages:
        _reminder_delete_last_messages(cfg)
    try:
        if 'operation_begin' in globals():
            op_id = operation_begin('reminder_complete', OWNER_ID, target=str(reminder_id), payload={'reason': reason}, critical=False)
            operation_complete(op_id, 'reminder moved to completed')
    except Exception:
        pass

# --- reminders:0021 · from 04_messages_features.py:1887 · public _reminder_end_has_passed ---
def _reminder_end_has_passed(cfg: dict, now_dt=None) -> bool:
    now_dt = now_dt or now_local()
    end_date = _reminder_parse_date((cfg or {}).get('end_date'))
    if end_date and now_dt.date() > end_date:
        return True
    return False

# --- reminders:0022 · from 04_messages_features.py:1894 · public build_completed_reminders_text ---
def build_completed_reminders_text(page: int=0, delete_mode: bool=False) -> str:
    rows = _reminder_completed_items()
    pages = max(1, (len(rows) + _REMINDER_COMPLETED_PAGE_SIZE - 1) // _REMINDER_COMPLETED_PAGE_SIZE)
    page = max(0, min(int(page or 0), pages - 1))
    selected = _REMINDER_COMPLETED_DELETE_SELECTION.get(int(OWNER_ID or 0), set())
    return f'✅ ЗАВЕРШЁННЫЕ НАПОМИНАЛКИ\n\nВсего: {len(rows)}\nСтраница: {page + 1}/{pages}\n' + (f'Выбрано для удаления: {len(selected)}\n' if delete_mode else '') + '\nНажмите напоминалку для просмотра и редактирования.'

# --- reminders:0023 · from 04_messages_features.py:1901 · public build_completed_reminders_keyboard ---
def build_completed_reminders_keyboard(page: int=0, delete_mode: bool=False):
    rows = _reminder_completed_items()
    pages = max(1, (len(rows) + _REMINDER_COMPLETED_PAGE_SIZE - 1) // _REMINDER_COMPLETED_PAGE_SIZE)
    page = max(0, min(int(page or 0), pages - 1))
    owner_key = int(OWNER_ID or 0)
    selected = _REMINDER_COMPLETED_DELETE_SELECTION.setdefault(owner_key, set())
    kb = types.InlineKeyboardMarkup(row_width=1)
    start = page * _REMINDER_COMPLETED_PAGE_SIZE
    for idx, (rid, cfg) in enumerate(rows[start:start + _REMINDER_COMPLETED_PAGE_SIZE], start=start + 1):
        label = _reminder_button_label(idx, cfg)
        if delete_mode:
            prefix = '☑️ ' if int(rid) in selected else '▫️ '
            kb.row(IB(prefix + label, callback_data=f'rem:completed_select:{rid}:{page}'))
        else:
            kb.row(IB(label, callback_data=f'rem:completed_open:{rid}:{page}'))
    if pages > 1:
        nav = []
        if page > 0:
            nav.append(IB('⬅️', callback_data=f'rem:completed:{page - 1}:{(1 if delete_mode else 0)}'))
        nav.append(IB(f'{page + 1}/{pages}', callback_data='none'))
        if page + 1 < pages:
            nav.append(IB('➡️', callback_data=f'rem:completed:{page + 1}:{(1 if delete_mode else 0)}'))
        kb.row(*nav)
    if delete_mode:
        kb.row(IB('🗑 Удалить выбранное', callback_data=f'rem:completed_delete_selected:{page}'))
        kb.row(IB('✖️ Отмена выбора', callback_data=f'rem:completed_cancel_select:{page}'))
    else:
        kb.row(IB('☑️ Выбрать для удаления', callback_data=f'rem:completed_select_mode:{page}'))
    kb.row(IB('⬅️ Назад', callback_data=f'rem:list:0:{today_key()}'))
    return kb

# --- reminders:0024 · from 04_messages_features.py:1932 · public _reminder_save ---
def _reminder_save(reason: str='reminder') -> None:
    try:
        save_data(data, root_only=True)
    except Exception as exc:
        log_error(f'reminder save root: {exc}')
    owner = _reminder_owner_id()
    if owner:
        try:
            schedule_delta_backup(owner, delay=0.35, reason=reason)
        except Exception as exc:
            log_error(f'reminder delta schedule: {exc}')

# --- reminders:0025 · from 04_messages_features.py:1944 · public _reminder_generation_v245 ---
def _reminder_generation_v245(cfg: dict | None) -> int:
    try:
        return max(1, int((cfg or {}).get('lifecycle_generation_v245') or 1))
    except Exception:
        return 1

# --- reminders:0026 · from 04_messages_features.py:1950 · public _reminder_touch ---
def _reminder_touch(cfg: dict) -> None:
    cfg['lifecycle_generation_v245'] = _reminder_generation_v245(cfg) + 1
    cfg.pop('delivery_cycle_v245', None)
    cfg.pop('delivery_acked_chats_v245', None)
    cfg['delivery_cycle_v245'] = ''
    cfg['delivery_acked_chats_v245'] = []
    cfg['updated_at'] = now_local().isoformat(timespec='seconds')

# --- reminders:0027 · from 04_messages_features.py:1958 · public _reminder_parse_date ---
def _reminder_parse_date(value: str):
    try:
        return datetime.strptime(str(value or ''), '%Y-%m-%d').date()
    except Exception:
        return None

# --- reminders:0028 · from 04_messages_features.py:1964 · public _reminder_parse_dt ---
def _reminder_parse_dt(value: str):
    try:
        dt = datetime.fromisoformat(str(value or ''))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=now_local().tzinfo)
        return dt
    except Exception:
        return None

# --- reminders:0029 · from 04_messages_features.py:1973 · public _reminder_fmt_date ---
def _reminder_fmt_date(value: str) -> str:
    d = _reminder_parse_date(value)
    return d.strftime('%d.%m.%Y') if d else '—'

# --- reminders:0030 · from 04_messages_features.py:1977 · public _reminder_fmt_dt ---
def _reminder_fmt_dt(value: str) -> str:
    dt = _reminder_parse_dt(value)
    return dt.strftime('%d.%m %H:%M') if dt else '—'

# --- reminders:0031 · from 04_messages_features.py:1981 · public _reminder_interval_label ---
def _reminder_interval_label(minutes: int) -> str:
    try:
        minutes = max(1, int(minutes))
    except Exception:
        minutes = 120
    if minutes % 1440 == 0:
        d = minutes // 1440
        return f'{d} д' if d != 1 else '1 день'
    if minutes % 60 == 0:
        return f'{minutes // 60} ч'
    return f'{minutes} мин'

# --- reminders:0032 · from 04_messages_features.py:1993 · public _reminder_normalize_hours ---
def _reminder_normalize_hours(cfg: dict) -> None:
    try:
        start = max(0, min(23, int(cfg.get('start_hour', 8))))
    except Exception:
        start = 8
    try:
        end = max(0, min(23, int(cfg.get('end_hour', 22))))
    except Exception:
        end = 22
    if start > end:
        end = start
    cfg['start_hour'] = start
    cfg['end_hour'] = end

# --- reminders:0033 · from 04_messages_features.py:2007 · public _reminder_date_allowed ---
def _reminder_date_allowed(now_dt: datetime, cfg: dict) -> bool:
    today = now_dt.date()
    start = _reminder_parse_date(cfg.get('start_date'))
    end = _reminder_parse_date(cfg.get('end_date'))
    if start and today < start:
        return False
    if end and today > end:
        return False
    return True

# --- reminders:0034 · from 04_messages_features.py:2017 · public _reminder_time_allowed ---
def _reminder_time_allowed(now_dt: datetime, cfg: dict) -> bool:
    _reminder_normalize_hours(cfg)
    return int(cfg['start_hour']) <= now_dt.hour <= int(cfg['end_hour'])

# --- reminders:0035 · from 04_messages_features.py:2021 · public _reminder_next_valid_start ---
def _reminder_next_valid_start(now_dt: datetime, cfg: dict):
    _reminder_normalize_hours(cfg)
    start_date = _reminder_parse_date(cfg.get('start_date')) or now_dt.date()
    end_date = _reminder_parse_date(cfg.get('end_date'))
    day = max(now_dt.date(), start_date)
    for _ in range(3700):
        if end_date and day > end_date:
            return None
        candidate = datetime.combine(day, datetime.min.time(), tzinfo=now_dt.tzinfo).replace(hour=int(cfg.get('start_hour', 8)), minute=0, second=0, microsecond=0)
        end_candidate = candidate.replace(hour=int(cfg.get('end_hour', 22)), minute=59, second=59)
        if day == now_dt.date():
            if now_dt <= candidate:
                return candidate
            if now_dt <= end_candidate:
                return now_dt
        elif candidate >= now_dt:
            return candidate
        day += timedelta(days=1)
    return None

# --- reminders:0036 · from 04_messages_features.py:2041 · public _reminder_rearm ---
def _reminder_rearm(cfg: dict, immediate_if_valid: bool=True) -> None:
    now_dt = now_local()
    if not bool(cfg.get('enabled')):
        cfg['next_run_at'] = ''
        return
    if immediate_if_valid and _reminder_date_allowed(now_dt, cfg) and _reminder_time_allowed(now_dt, cfg):
        cfg['next_run_at'] = now_dt.isoformat(timespec='seconds')
        return
    next_dt = _reminder_next_valid_start(now_dt, cfg)
    cfg['next_run_at'] = next_dt.isoformat(timespec='seconds') if next_dt else ''
    if next_dt is None:
        cfg['enabled'] = False

# --- reminders:0037 · from 04_messages_features.py:2054 · public _reminder_advance_after_send ---
def _reminder_advance_after_send(now_dt: datetime, cfg: dict) -> None:
    try:
        minutes = max(1, int(cfg.get('interval_minutes', 120)))
    except Exception:
        minutes = 120
    candidate = now_dt + timedelta(minutes=minutes)
    _reminder_normalize_hours(cfg)
    end_hour = int(cfg.get('end_hour', 22))
    start_hour = int(cfg.get('start_hour', 8))
    if candidate.date() != now_dt.date() or candidate.hour > end_hour:
        day = now_dt.date() + timedelta(days=1)
        candidate = datetime.combine(day, datetime.min.time(), tzinfo=now_dt.tzinfo).replace(hour=start_hour)
    start_date = _reminder_parse_date(cfg.get('start_date'))
    if start_date and candidate.date() < start_date:
        candidate = datetime.combine(start_date, datetime.min.time(), tzinfo=now_dt.tzinfo).replace(hour=start_hour)
    end_date = _reminder_parse_date(cfg.get('end_date'))
    if end_date and candidate.date() > end_date:
        cfg['enabled'] = False
        cfg['next_run_at'] = ''
    else:
        cfg['next_run_at'] = candidate.isoformat(timespec='seconds')

# --- reminders:0038 · from 04_messages_features.py:2076 · public _reminder_rearm_after_interval_v243 ---
def _reminder_rearm_after_interval_v243(cfg: dict, preserve_future: bool=True) -> None:
    """Owner/UI rearm: keep cadence stable instead of firing immediately.

    Boot reconciliation remains responsible for catch-up of overdue reminders. Manual
    enable/edit schedules the next delivery after the configured interval (or the next
    valid window) and never silently turns a completed reminder back on.
    """
    now_dt = now_local()
    if not bool((cfg or {}).get('enabled')):
        cfg['next_run_at'] = ''
        return
    existing = _reminder_parse_dt((cfg or {}).get('next_run_at'))
    if preserve_future and existing is not None and (existing > now_dt):
        try:
            if _reminder_date_allowed(existing, cfg) and _reminder_time_allowed(existing, cfg):
                return
        except Exception:
            pass
    if _reminder_date_allowed(now_dt, cfg) and _reminder_time_allowed(now_dt, cfg):
        tmp = copy.deepcopy(cfg)
        _reminder_advance_after_send(now_dt, tmp)
        cfg['next_run_at'] = str(tmp.get('next_run_at') or '')
        if not cfg['next_run_at']:
            cfg['enabled'] = False
        return
    next_dt = _reminder_next_valid_start(now_dt, cfg)
    cfg['next_run_at'] = next_dt.isoformat(timespec='seconds') if next_dt else ''
    if next_dt is None:
        cfg['enabled'] = False

# --- reminders:0039 · from 04_messages_features.py:2106 · public _reminder_clear_completion_v243 ---
def _reminder_clear_completion_v243(cfg: dict) -> None:
    cfg['completed_at'] = ''
    cfg['completion_reason'] = ''
    for key in ('completed_by_user_id', 'completed_by_label', 'completed_in_chat_id', 'completion_event_id'):
        cfg.pop(key, None)

# --- reminders:0040 · from 04_messages_features.py:2112 · public _reminder_known_chats ---
def _reminder_known_chats() -> list[tuple[int, str]]:
    rows, seen = ([], set())
    try:
        source = _collect_backup_menu_items()
    except Exception:
        source = []
    for cid, title in source:
        try:
            cid = int(cid)
        except Exception:
            continue
        if cid in seen:
            continue
        seen.add(cid)
        rows.append((cid, str(title or get_chat_display_name(cid))))
    owner = _reminder_owner_id()
    if owner and owner not in seen:
        rows.insert(0, (owner, get_chat_display_name(owner)))
    return rows

# --- reminders:0041 · from 04_messages_features.py:2132 · public _reminder_button_label ---
def _reminder_button_label(position: int, cfg: dict) -> str:
    text = re.sub('\\s+', ' ', str(cfg.get('text') or '').strip()) or 'без текста'
    active_mark = '✅ ' if bool(cfg.get('enabled')) and (not _reminder_is_completed(cfg)) else ''
    base = f'{active_mark}{int(position)}. {text}'
    try:
        return pad_button_label_41(base)
    except Exception:
        if len(base) > 41:
            base = base[:40] + '…'
        return base + '⠀' * max(0, 41 - len(base))

# --- reminders:0042 · from 04_messages_features.py:2143 · public _v177_legacy_0123_build_reminder_list_text ---
def _v177_legacy_0123_build_reminder_list_text() -> str:
    rows = _reminder_items()
    completed = _reminder_completed_items()
    enabled = sum((1 for _rid, cfg in rows if bool(cfg.get('enabled'))))
    return f'⏰ НАПОМИНАЛКИ\n\nТекущих: {len(rows)}\nАктивных: {enabled}\nЗавершённых: {len(completed)}\n\nНажмите напоминалку для просмотра и настройки.'

# --- reminders:0043 · from 04_messages_features.py:2153 · public _v177_legacy_0125_build_reminder_list_keyboard ---
def _v177_legacy_0125_build_reminder_list_keyboard(day_key: str | None=None, page: int=0):
    day_key = day_key or today_key()
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
    kb.row(IB('⬅️ Назад', callback_data=f'd:{day_key}:back_main'))
    return kb

# --- reminders:0044 · from 04_messages_features.py:2179 · public _reminder_bind_editor ---
def _reminder_bind_editor(reminder_id: int, chat_id: int, message_id: int, day_key: str, page: int=0) -> None:
    _REMINDER_UI_BINDINGS[int(reminder_id)] = {'chat_id': int(chat_id), 'message_id': int(message_id), 'day_key': str(day_key), 'page': int(page), 'ts': time.time()}

# --- reminders:0045 · from 04_messages_features.py:2182 · public _reminder_unbind ---
def _reminder_unbind(reminder_id: int) -> None:
    _REMINDER_UI_BINDINGS.pop(int(reminder_id), None)

# --- reminders:0046 · from 04_messages_features.py:2185 · public _v177_legacy_0127_build_reminder_menu_text ---
def _v177_legacy_0127_build_reminder_menu_text(reminder_id: int) -> str:
    cfg = _reminder_cfg(reminder_id)
    if not cfg:
        return '⏰ Напоминалка не найдена.'
    _reminder_normalize_hours(cfg)
    preview = re.sub('\\s+', ' ', str(cfg.get('text') or '').strip())
    if len(preview) > 160:
        preview = preview[:157] + '...'
    end_date = _reminder_fmt_date(cfg.get('end_date')) if cfg.get('end_date') else 'без конца'
    if _reminder_is_completed(cfg):
        state = '✅ ЗАВЕРШЕНА'
    else:
        state = '✅ АКТИВНО' if cfg.get('enabled') else '⬜ ВЫКЛЮЧЕНО'
    chats_count = len([x for x in cfg.get('chat_ids') or [] if str(x).strip()])
    pos = _reminder_position(int(reminder_id)) or int(reminder_id)
    return f"⏰ НАПОМИНАЛКА №{pos}\n\nСостояние: {state}\nТекст: {preview or 'не задан'}\nДаты: {_reminder_fmt_date(cfg.get('start_date'))} → {end_date}\nВремя: {int(cfg.get('start_hour', 8)):02d}:00 → {int(cfg.get('end_hour', 22)):02d}:59\nПериод: каждые {_reminder_interval_label(cfg.get('interval_minutes', 120))}\nЧаты: {chats_count}\nСледующая: {_reminder_fmt_dt(cfg.get('next_run_at'))}\nПоследняя: {_reminder_fmt_dt(cfg.get('last_sent_at'))}" + (f"\nЗавершена: {_reminder_fmt_dt(cfg.get('completed_at'))}" if _reminder_is_completed(cfg) else '')

# --- reminders:0047 · from 04_messages_features.py:2206 · public _reminder_insert_query ---
def _reminder_insert_query(token: str, current_text: str='') -> str:
    service = f'({token} служебное — можно не трогать)'
    max_payload = max(0, 252 - len(service) - 2)
    current = str(current_text or '')
    if len(current) > max_payload:
        current = current[:max_payload]
    return service + '\n\n' + current

# --- reminders:0048 · from 04_messages_features.py:2214 · public compose_reminder_text_insert_value ---
def compose_reminder_text_insert_value(reminder_id: int, current_text: str='') -> str:
    return _reminder_insert_query(f'EDITREM|{int(reminder_id)}|', current_text)

# --- reminders:0049 · from 04_messages_features.py:2217 · public compose_reminder_interval_insert_value ---
def compose_reminder_interval_insert_value(reminder_id: int, cfg: dict) -> str:
    return _reminder_insert_query(f'EDITREMINT|{int(reminder_id)}|', _reminder_interval_label(cfg.get('interval_minutes', 120)))

# --- reminders:0050 · from 04_messages_features.py:2220 · public _v177_legacy_0129_build_reminder_menu_keyboard ---
def _v177_legacy_0129_build_reminder_menu_keyboard(reminder_id: int, day_key: str | None=None, page: int=0, viewer_chat_id: int | None=None):
    day_key = day_key or today_key()
    cfg = _reminder_cfg(reminder_id)
    kb = types.InlineKeyboardMarkup(row_width=2)
    if not cfg:
        kb.row(IB('⬅️ К напоминалкам', callback_data=_reminder_return_callback(page, day_key)))
        return kb
    kb.row(make_copy_or_inline_button('✍️ Текст', compose_reminder_text_insert_value(reminder_id, cfg.get('text') or ''), viewer_chat_id=viewer_chat_id), IB(f"💬 Чаты ({len(cfg.get('chat_ids') or [])})", callback_data=f'rem:chats:{reminder_id}:0:{page}:{day_key}'))
    kb.row(IB('📅 Даты', callback_data=f'rem:dates:{reminder_id}:{page}:{day_key}'), IB(f"🔁 {_reminder_interval_label(cfg.get('interval_minutes', 120))}", callback_data=f'rem:interval:{reminder_id}:{page}:{day_key}'))
    kb.row(IB(f"🕗 С {int(cfg.get('start_hour', 8)):02d}:00", callback_data=f'rem:hours:start:{reminder_id}:{page}:{day_key}'), IB(f"🕙 До {int(cfg.get('end_hour', 22)):02d}:59", callback_data=f'rem:hours:end:{reminder_id}:{page}:{day_key}'))
    state_label = '✅ Активно' if cfg.get('enabled') and (not _reminder_is_completed(cfg)) else '⬜ Выключено'
    kb.row(IB(state_label, callback_data=f'rem:toggle:{reminder_id}:{page}:{day_key}'), IB('Изменить📝', callback_data=f'rem:editmenu:{reminder_id}:{page}:{day_key}'))
    kb.row(IB('⬅️ К напоминалкам', callback_data=_reminder_return_callback(page, day_key)))
    return kb

# --- reminders:0051 · from 04_messages_features.py:2239 · public _reminder_edit_menu_keyboard ---
def _reminder_edit_menu_keyboard(reminder_id: int, page: int, day_key: str, viewer_chat_id: int):
    cfg = _reminder_cfg(reminder_id) or {}
    kb = types.InlineKeyboardMarkup(row_width=1)
    kb.row(make_copy_or_inline_button('✍️ Вставить текст', compose_reminder_text_insert_value(reminder_id, cfg.get('text') or ''), viewer_chat_id=viewer_chat_id))
    kb.row(IB('🗑 Удалить', callback_data=f'rem:delete_confirm:{reminder_id}:{page}:{day_key}'))
    kb.row(IB('⬅️ Назад', callback_data=f'rem:open:{reminder_id}:{page}:{day_key}'), IB('✖️ Отмена', callback_data=f'rem:open:{reminder_id}:{page}:{day_key}'))
    return kb

# --- reminders:0052 · from 04_messages_features.py:2247 · public _reminder_dates_text ---
def _reminder_dates_text(reminder_id: int) -> str:
    cfg = _reminder_cfg(reminder_id) or {}
    end = _reminder_fmt_date(cfg.get('end_date')) if cfg.get('end_date') else 'без конца'
    return f"📅 ДАТЫ НАПОМИНАЛКИ\n\nНачало: {_reminder_fmt_date(cfg.get('start_date'))}\nКонец: {end}"

# --- reminders:0053 · from 04_messages_features.py:2252 · public _reminder_dates_keyboard ---
def _reminder_dates_keyboard(reminder_id: int, page: int, day_key: str):
    cfg = _reminder_cfg(reminder_id) or {}
    kb = types.InlineKeyboardMarkup(row_width=2)
    now_ym = now_local().strftime('%Y-%m')
    start_label = '📅 Начало✅' if str(cfg.get('start_date') or '').strip() else '📅 Начало'
    end_label = '🏁 Конец✅' if str(cfg.get('end_date') or '').strip() else '🏁 Конец'
    kb.row(IB(start_label, callback_data=f'rem:calendar:start:{now_ym}:{reminder_id}:{page}:{day_key}'), IB(end_label, callback_data=f'rem:calendar:end:{now_ym}:{reminder_id}:{page}:{day_key}'))
    kb.row(IB('♾ Без конца', callback_data=f'rem:noend:{reminder_id}:{page}:{day_key}'))
    kb.row(IB('⬅️ Назад', callback_data=f'rem:open:{reminder_id}:{page}:{day_key}'))
    return kb

# --- reminders:0054 · from 04_messages_features.py:2263 · public _reminder_calendar_text ---
def _reminder_calendar_text(which: str, year: int, month: int) -> str:
    target = 'начала' if which == 'start' else 'окончания'
    return f'📅 Выберите дату {target}\n\n{_REMINDER_MONTHS_RU[month - 1]} {year}'

# --- reminders:0055 · from 04_messages_features.py:2267 · public _reminder_calendar_keyboard ---
def _reminder_calendar_keyboard(which: str, year: int, month: int, reminder_id: int, page: int, day_key: str):
    kb = types.InlineKeyboardMarkup(row_width=7)
    kb.row(*[IB(x, callback_data='none') for x in ('Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс')])
    cal = calendar.Calendar(firstweekday=0)
    for week in cal.monthdayscalendar(year, month):
        row = []
        for d in week:
            if not d:
                row.append(IB(' ', callback_data='none'))
            else:
                date_key = f'{year:04d}-{month:02d}-{d:02d}'
                row.append(IB(str(d), callback_data=f'rem:date:{which}:{date_key}:{reminder_id}:{page}:{day_key}'))
        kb.row(*row)
    prev_month, prev_year = (month - 1, year)
    if prev_month < 1:
        prev_month, prev_year = (12, prev_year - 1)
    next_month, next_year = (month + 1, year)
    if next_month > 12:
        next_month, next_year = (1, next_year + 1)
    kb.row(IB('⬅️', callback_data=f'rem:calendar:{which}:{prev_year:04d}-{prev_month:02d}:{reminder_id}:{page}:{day_key}'), IB('📅 Даты', callback_data=f'rem:dates:{reminder_id}:{page}:{day_key}'), IB('➡️', callback_data=f'rem:calendar:{which}:{next_year:04d}-{next_month:02d}:{reminder_id}:{page}:{day_key}'))
    return kb

# --- reminders:0056 · from 04_messages_features.py:2289 · public _reminder_interval_keyboard ---
def _reminder_interval_keyboard(reminder_id: int, page: int, day_key: str, viewer_chat_id: int):
    cfg = _reminder_cfg(reminder_id) or {}
    current = int(cfg.get('interval_minutes', 120) or 120)
    kb = types.InlineKeyboardMarkup(row_width=3)
    buttons = []
    for minutes in [30, 60, 120, 180, 240, 360, 720, 1440]:
        mark = '✅ ' if minutes == current else ''
        buttons.append(IB(mark + _reminder_interval_label(minutes), callback_data=f'rem:intset:{minutes}:{reminder_id}:{page}:{day_key}'))
    for i in range(0, len(buttons), 3):
        kb.row(*buttons[i:i + 3])
    kb.row(make_copy_or_inline_button('✍️ Свой интервал', compose_reminder_interval_insert_value(reminder_id, cfg), viewer_chat_id=viewer_chat_id))
    kb.row(IB('⬅️ Назад', callback_data=f'rem:open:{reminder_id}:{page}:{day_key}'))
    return kb

# --- reminders:0057 · from 04_messages_features.py:2303 · public _reminder_hours_keyboard ---
def _reminder_hours_keyboard(which: str, reminder_id: int, page: int, day_key: str):
    cfg = _reminder_cfg(reminder_id) or {}
    current = int(cfg.get('start_hour' if which == 'start' else 'end_hour', 8 if which == 'start' else 22))
    kb = types.InlineKeyboardMarkup(row_width=4)
    buttons = []
    for hour in range(24):
        mark = '✅ ' if hour == current else ''
        buttons.append(IB(f'{mark}{hour:02d}:00', callback_data=f'rem:hourset:{which}:{hour}:{reminder_id}:{page}:{day_key}'))
    for i in range(0, 24, 4):
        kb.row(*buttons[i:i + 4])
    kb.row(IB('⬅️ Назад', callback_data=f'rem:open:{reminder_id}:{page}:{day_key}'))
    return kb

# --- reminders:0058 · from 04_messages_features.py:2316 · public _reminder_chats_keyboard ---
def _reminder_chats_keyboard(reminder_id: int, chat_page: int, list_page: int, day_key: str):
    cfg = _reminder_cfg(reminder_id) or {}
    selected = {int(x) for x in cfg.get('chat_ids') or [] if str(x).lstrip('-').isdigit()}
    rows = _reminder_known_chats()
    per_page = 8
    pages = max(1, (len(rows) + per_page - 1) // per_page)
    chat_page = max(0, min(int(chat_page), pages - 1))
    kb = types.InlineKeyboardMarkup(row_width=1)
    for cid, title in rows[chat_page * per_page:(chat_page + 1) * per_page]:
        mark = '✅' if cid in selected else '⬜'
        name = chat_button_title(cid, title) if 'chat_button_title' in globals() else str(title)
        kb.row(IB(f'{mark} {name}', callback_data=f'rem:chat:{cid}:{reminder_id}:{chat_page}:{list_page}:{day_key}'))
    nav = []
    if chat_page > 0:
        nav.append(IB('⬅️', callback_data=f'rem:chats:{reminder_id}:{chat_page - 1}:{list_page}:{day_key}'))
    nav.append(IB(f'{chat_page + 1}/{pages}', callback_data='none'))
    if chat_page + 1 < pages:
        nav.append(IB('➡️', callback_data=f'rem:chats:{reminder_id}:{chat_page + 1}:{list_page}:{day_key}'))
    kb.row(*nav)
    kb.row(IB('⬅️ Назад', callback_data=f'rem:open:{reminder_id}:{list_page}:{day_key}'))
    return kb

# --- reminders:0059 · from 04_messages_features.py:2338 · public _reminder_parse_custom_interval ---
def _reminder_parse_custom_interval(text: str) -> int | None:
    value = str(text or '').strip().lower().replace(',', '.')
    m = re.fullmatch('\\s*(\\d+(?:\\.\\d+)?)\\s*(мин|м|min|m|ч|час|часа|часов|h|д|дн|день|дня|дней|d)?\\s*', value)
    if not m:
        return None
    num = float(m.group(1))
    unit = m.group(2) or 'мин'
    if unit in {'ч', 'час', 'часа', 'часов', 'h'}:
        minutes = int(round(num * 60))
    elif unit in {'д', 'дн', 'день', 'дня', 'дней', 'd'}:
        minutes = int(round(num * 1440))
    else:
        minutes = int(round(num))
    return minutes if 5 <= minutes <= 43200 else None

# --- reminders:0060 · from 04_messages_features.py:2353 · public _v177_legacy_0131_reminder_delete_message_map ---
def _v177_legacy_0131_reminder_delete_message_map(last_map: dict) -> None:
    for cid_raw, mid_raw in list((last_map or {}).items()):
        try:
            bot.delete_message(int(cid_raw), int(mid_raw))
        except Exception:
            pass

# --- reminders:0061 · from 04_messages_features.py:2364 · public _reminder_delete_last_messages ---
def _reminder_delete_last_messages(cfg: dict) -> None:
    """Очищаем ссылки сразу, а Telegram-удаление выполняем вне UI/config-lock."""
    last_map = dict(cfg.get('last_message_ids') or {})
    cfg['last_message_ids'] = {}
    if not last_map:
        return
    key_seed = '|'.join((f'{k}:{v}' for k, v in sorted(last_map.items())))
    key = 'reminder-cleanup:' + hashlib.sha1(key_seed.encode('utf-8')).hexdigest()[:16]
    pool = globals().get('GENERAL_TASK_POOL') or globals().get('REMINDER_TASK_POOL')
    try:
        if pool is not None and pool.submit_unique(key, _reminder_delete_message_map, last_map):
            return
    except Exception:
        pass
    try:
        _reminder_delete_message_map(last_map)
    except Exception:
        pass

# --- reminders:0062 · from 04_messages_features.py:2383 · public _canon_reminder_send_cycle__001 ---
def _canon_reminder_send_cycle__001(reminder_id: int, cfg: dict) -> bool:
    text = str(cfg.get('text') or '').strip()
    chat_ids = []
    for raw in cfg.get('chat_ids') or []:
        try:
            chat_ids.append(int(raw))
        except Exception:
            pass
    if not text or not chat_ids:
        return False
    message_text = f'НАПОМИНАЛКА🕰️\n\n{text}'
    last_map = cfg.setdefault('last_message_ids', {})
    sent_any = False
    for cid in chat_ids:
        old_mid = last_map.get(str(cid))
        try:
            sent = bot.send_message(cid, message_text)
            last_map[str(cid)] = int(sent.message_id)
            if old_mid and int(old_mid) != int(sent.message_id):
                try:
                    bot.delete_message(cid, int(old_mid))
                except Exception:
                    pass
            sent_any = True
            try:
                bot_journal('reminder_sent', cid, f'reminder_id={int(reminder_id)} message_id={sent.message_id}')
            except Exception:
                pass
        except Exception as exc:
            log_error(f'reminder {reminder_id} send {cid}: {exc}')
            try:
                bot_journal('reminder_send_error', cid, f'reminder_id={int(reminder_id)} {exc}', 'ERROR')
            except Exception:
                pass
    return sent_any

# --- reminders:0063 · from 04_messages_features.py:2419 · public _reminder_tick_one ---
def _reminder_tick_one(reminder_id: int, cfg: dict) -> bool:
    if not bool(cfg.get('enabled')):
        return False
    now_dt = now_local()
    if not str(cfg.get('text') or '').strip() or not (cfg.get('chat_ids') or []):
        return False
    due = _reminder_parse_dt(cfg.get('next_run_at'))
    if due is None:
        _reminder_rearm(cfg, immediate_if_valid=True)
        due = _reminder_parse_dt(cfg.get('next_run_at'))
    if due is None or now_dt < due:
        return False
    if not _reminder_date_allowed(now_dt, cfg) or not _reminder_time_allowed(now_dt, cfg):
        next_dt = _reminder_next_valid_start(now_dt, cfg)
        cfg['next_run_at'] = next_dt.isoformat(timespec='seconds') if next_dt else ''
        if next_dt is None:
            cfg['enabled'] = False
        _reminder_touch(cfg)
        return True
    if _reminder_send_cycle(reminder_id, cfg):
        cfg['last_sent_at'] = now_dt.isoformat(timespec='seconds')
    _reminder_advance_after_send(now_dt, cfg)
    _reminder_touch(cfg)
    return True

# --- reminders:0064 · from 04_messages_features.py:2444 · public _reminder_due_now ---
def _reminder_due_now(cfg: dict, now_dt=None) -> bool:
    if not bool((cfg or {}).get('enabled')):
        return False
    if not str((cfg or {}).get('text') or '').strip() or not ((cfg or {}).get('chat_ids') or []):
        return False
    now_dt = now_dt or now_local()
    due = _reminder_parse_dt((cfg or {}).get('next_run_at'))
    return due is None or now_dt >= due

# --- reminders:0065 · from 04_messages_features.py:2453 · public _reminder_tick_job ---
def _reminder_tick_job(reminder_id: int) -> None:
    """One reminder per keyed worker; completion also removes the last chat message."""
    reminder_id = int(reminder_id)
    snapshot = None
    now_dt = now_local()
    changed_without_send = False
    completed = False
    with _REMINDER_CONFIG_LOCK:
        cfg = _reminder_cfg(reminder_id)
        if not cfg or _reminder_is_completed(cfg):
            return
        if _reminder_end_has_passed(cfg, now_dt):
            _reminder_mark_completed(reminder_id, cfg, 'end_date_finished', delete_messages=True)
            completed = True
        elif not _reminder_due_now(cfg, now_dt):
            return
        else:
            due = _reminder_parse_dt(cfg.get('next_run_at'))
            if due is None:
                _reminder_rearm(cfg, immediate_if_valid=True)
                due = _reminder_parse_dt(cfg.get('next_run_at'))
            if due is None:
                _reminder_mark_completed(reminder_id, cfg, 'no_next_time', delete_messages=True)
                completed = True
            elif now_dt < due:
                return
            elif not _reminder_date_allowed(now_dt, cfg) or not _reminder_time_allowed(now_dt, cfg):
                next_dt = _reminder_next_valid_start(now_dt, cfg)
                cfg['next_run_at'] = next_dt.isoformat(timespec='seconds') if next_dt else ''
                if next_dt is None:
                    _reminder_mark_completed(reminder_id, cfg, 'schedule_finished', delete_messages=True)
                    completed = True
                else:
                    _reminder_touch(cfg)
                    changed_without_send = True
            else:
                snapshot = copy.deepcopy(cfg)
    if completed:
        _reminder_save('reminder_completed')
        return
    if changed_without_send:
        _reminder_save('reminders_tick_window')
        return
    if snapshot is None:
        return
    sent_ok = _reminder_send_cycle(reminder_id, snapshot)
    updated = False
    with _REMINDER_CONFIG_LOCK:
        cfg = _reminder_cfg(reminder_id)
        if cfg and (not _reminder_is_completed(cfg)):
            cfg['last_message_ids'] = dict(snapshot.get('last_message_ids') or {})
            if sent_ok:
                cfg['last_sent_at'] = now_dt.isoformat(timespec='seconds')
            _reminder_advance_after_send(now_dt, cfg)
            if not cfg.get('next_run_at') or _reminder_end_has_passed(cfg, now_local()):
                _reminder_mark_completed(reminder_id, cfg, 'schedule_finished', delete_messages=True)
            else:
                _reminder_touch(cfg)
            updated = True
    if updated:
        _reminder_save('reminders_tick')

# --- reminders:0066 · from 04_messages_features.py:2515 · public _v177_legacy_0132_reminder_tick ---
def _v177_legacy_0132_reminder_tick() -> None:
    now_dt = now_local()
    due_ids = []
    with _REMINDER_CONFIG_LOCK:
        for rid, cfg in _reminder_items():
            try:
                if _reminder_due_now(cfg, now_dt):
                    due_ids.append(int(rid))
            except Exception as exc:
                log_error(f'reminder {rid} due check: {exc}')
    for rid in due_ids:
        if not REMINDER_TASK_POOL.submit_unique(f'reminder:{rid}', _reminder_tick_job, rid):
            try:
                bot_journal('reminder_dispatch_coalesced', None, f'reminder_id={rid}')
            except Exception:
                pass

# --- reminders:0067 · from 04_messages_features.py:2536 · public _reminder_boot_reconcile_v241 ---
def _reminder_boot_reconcile_v241() -> dict:
    """Rebuild runnable reminder timing after deploy/restore.

    Durable reminder settings are authoritative; queued scheduler state is not.  An
    enabled reminder that survived deploy must always have a valid next_run_at.  If
    the stored deadline is overdue, arm it for the next scheduler tick; if the bot is
    outside the configured date/hour window, move it to the next valid window.
    Completed reminders are never resurrected by boot reconciliation.
    """
    now_dt = now_local()
    changed = 0
    active = 0
    overdue = 0
    repaired = 0
    invalid = 0
    completed_fixed = 0
    with _REMINDER_CONFIG_LOCK:
        rows_fn = globals().get('reminder_items_global_for_completion')
        all_rows = rows_fn(include_completed=True) if callable(rows_fn) else _reminder_items(include_completed=True)
        for rid, cfg in all_rows:
            cfg = _normalize_reminder_cfg(cfg)
            if _reminder_is_completed(cfg):
                if cfg.get('enabled') or cfg.get('next_run_at'):
                    cfg['enabled'] = False
                    cfg['next_run_at'] = ''
                    _reminder_touch(cfg)
                    changed += 1
                    completed_fixed += 1
                continue
            if not bool(cfg.get('enabled')):
                continue
            active += 1
            if not str(cfg.get('text') or '').strip() or not (cfg.get('chat_ids') or []):
                if cfg.get('next_run_at'):
                    cfg['next_run_at'] = ''
                    _reminder_touch(cfg)
                    changed += 1
                invalid += 1
                continue
            if _reminder_end_has_passed(cfg, now_dt):
                _reminder_mark_completed(rid, cfg, 'end_date_finished', delete_messages=False)
                changed += 1
                completed_fixed += 1
                continue
            due = _reminder_parse_dt(cfg.get('next_run_at'))
            allowed_now = _reminder_date_allowed(now_dt, cfg) and _reminder_time_allowed(now_dt, cfg)
            new_due = due
            if allowed_now:
                if due is None:
                    last = _reminder_parse_dt(cfg.get('last_sent_at'))
                    try:
                        interval = max(1, int(cfg.get('interval_minutes', 120)))
                    except Exception:
                        interval = 120
                    candidate = last + timedelta(minutes=interval) if last is not None else None
                    if candidate is not None and candidate > now_dt:
                        new_due = candidate
                    else:
                        new_due = now_dt
                        overdue += 1
                elif due <= now_dt:
                    new_due = now_dt
                    overdue += 1
                elif not (_reminder_date_allowed(due, cfg) and _reminder_time_allowed(due, cfg)):
                    new_due = _reminder_next_valid_start(now_dt, cfg)
            elif due is None or due <= now_dt or (not (_reminder_date_allowed(due, cfg) and _reminder_time_allowed(due, cfg))):
                new_due = _reminder_next_valid_start(now_dt, cfg)
            new_text = new_due.isoformat(timespec='seconds') if new_due else ''
            if str(cfg.get('next_run_at') or '') != new_text:
                cfg['next_run_at'] = new_text
                if new_due is None:
                    cfg['enabled'] = False
                _reminder_touch(cfg)
                changed += 1
                repaired += 1
        state_root = data.setdefault('_global_settings', {}).get('reminder_groups_v149')
        if isinstance(state_root, dict):
            for cid, row in list(state_root.items()):
                if not isinstance(row, dict):
                    continue
                next_rows = []
                try:
                    chat_id = int(cid)
                except Exception:
                    chat_id = 0
                active_rows = rows_fn(include_completed=False) if callable(rows_fn) else _reminder_items()
                for _rid, cfg in active_rows:
                    try:
                        ids = {int(x) for x in cfg.get('chat_ids') or []}
                    except Exception:
                        ids = set()
                    if chat_id and chat_id in ids and cfg.get('enabled') and (not _reminder_is_completed(cfg)):
                        dt = _reminder_parse_dt(cfg.get('next_run_at'))
                        if dt is not None:
                            next_rows.append(dt)
                rebuilt = min(next_rows).isoformat(timespec='seconds') if next_rows else ''
                if str(row.get('next_run_at') or '') != rebuilt:
                    row['next_run_at'] = rebuilt
                    changed += 1
    if changed:
        _reminder_save('reminder_boot_reconcile_v241')
    detail = {'active': active, 'repaired': repaired, 'overdue': overdue, 'invalid': invalid, 'completed_fixed': completed_fixed, 'changed': changed}
    try:
        runtime_event('reminder_boot_reconciled_v241', json.dumps(detail, ensure_ascii=False), 'INFO')
    except Exception:
        try:
            bot_journal('reminder_boot_reconciled_v241', int(OWNER_ID or 0) or None, str(detail))
        except Exception:
            pass
    return detail

# --- reminders:0068 · from 04_messages_features.py:2647 · public _reminder_scheduler_tick ---
def _reminder_scheduler_tick() -> None:
    try:
        if runtime_is_ready():
            _reminder_tick()
    except Exception as exc:
        log_error(f'reminder scheduler: {exc}')
    finally:
        try:
            DELAYED_SCHEDULER.schedule('reminder-scheduler', _REMINDER_CHECK_SECONDS, _reminder_scheduler_tick)
        except Exception:
            pass

# --- reminders:0069 · from 04_messages_features.py:2659 · public start_reminder_scheduler ---
def start_reminder_scheduler() -> None:
    global _REMINDER_THREAD_STARTED
    with _REMINDER_THREAD_LOCK:
        if _REMINDER_THREAD_STARTED:
            return
        _REMINDER_THREAD_STARTED = True
        _reminders_root()
        try:
            _reminder_boot_reconcile_v241()
        except Exception as exc:
            log_error(f'reminder boot reconcile v241: {exc}')
            try:
                runtime_event('reminder_boot_reconcile_error_v241', str(exc)[:500], 'WARN')
            except Exception:
                pass
        try:
            save_data(data, root_only=True)
        except Exception as exc:
            log_error(f'reminder migration save: {exc}')
        try:
            DELAYED_SCHEDULER.schedule('reminder-scheduler', 1.0, _reminder_scheduler_tick)
        except Exception:
            pass

# --- reminders:0070 · from 04_messages_features.py:2683 · public _reminder_direct_input_predicate ---
def _reminder_direct_input_predicate(msg) -> bool:
    try:
        actor = int(getattr(getattr(msg, 'from_user', None), 'id', 0) or 0)
        owner_actor = actor == int(OWNER_ID or 0)
        if getattr(msg, 'content_type', None) != 'text' or not (is_owner_chat(int(msg.chat.id)) or owner_actor):
            return False
        text = str(getattr(msg, 'text', '') or '')
        return bool(re.search('\\((?:EDITREM|EDITREMINT)\\|\\d+\\|', text))
    except Exception:
        return False

# --- reminders:0071 · from 04_messages_features.py:2694 · public _reminder_extract_insert ---
def _reminder_extract_insert(text: str, kind: str):
    raw = str(text or '')
    m = re.search(f'\\(({re.escape(kind)}\\|(\\d+)\\|)[^)]*\\)', raw)
    if not m:
        return (None, '')
    try:
        rid = int(m.group(2))
    except Exception:
        return (None, '')
    value = (raw[:m.start()] + ' ' + raw[m.end():]).strip()
    try:
        value = sanitize_telegram_inserted_text(value)
    except Exception:
        value = re.sub('(?m)^\\s*@[A-Za-z0-9_]{3,}\\s+', '', value).strip()
    return (rid, value.strip())

# --- reminders:0072 · from 04_messages_features.py:2710 · public _reminder_refresh_bound_editor ---
def _reminder_refresh_bound_editor(reminder_id: int) -> None:
    binding = _REMINDER_UI_BINDINGS.get(int(reminder_id)) or {}
    try:
        chat_id = int(binding.get('chat_id'))
        message_id = int(binding.get('message_id'))
    except Exception:
        return
    cfg = _reminder_cfg(reminder_id)
    if not cfg:
        return
    day_key = str(binding.get('day_key') or today_key())
    page = int(binding.get('page') or 0)
    try:
        bot.edit_message_text(build_reminder_menu_text(reminder_id), chat_id=chat_id, message_id=message_id, reply_markup=build_reminder_menu_keyboard(reminder_id, day_key, page, viewer_chat_id=chat_id))
    except Exception as exc:
        if 'message is not modified' not in str(exc).lower():
            log_error(f'reminder refresh bound editor {reminder_id}: {exc}')

# --- reminders:0073 · from 04_messages_features.py:2779 · public reminder_callback ---
def reminder_callback(call):
    chat_id = int(call.message.chat.id)
    actor = int(getattr(getattr(call, 'from_user', None), 'id', 0) or 0)
    if not is_owner_chat(chat_id) and actor != int(OWNER_ID or 0):
        try:
            bot.answer_callback_query(call.id, 'Напоминалка доступна только владельцу', show_alert=True)
        except Exception:
            pass
        return
    raw = str(call.data or '')
    parts = raw.split(':')
    action = parts[1] if len(parts) > 1 else 'menu'
    try:
        bot.answer_callback_query(call.id)
    except Exception:
        pass
    if action == 'schedule':
        rid = int(parts[2])
        page = int(parts[3])
        day_key = parts[4]
        safe_edit(bot, call, reminder_schedule_text(rid), reply_markup=reminder_schedule_keyboard(rid, page, day_key))
        return
    if action == 'preview':
        rid = int(parts[2])
        page = int(parts[3])
        day_key = parts[4]
        safe_edit(bot, call, reminder_preview_text(rid), reply_markup=reminder_preview_keyboard(rid, page, day_key, chat_id))
        return
    if action == 'group_open':
        target_chat_id = int(parts[2])
        page = int(parts[3])
        day_key = parts[4]
        safe_edit(bot, call, reminder_group_text(target_chat_id, day_key), reply_markup=reminder_group_keyboard(target_chat_id, page, day_key))
        return
    if action == 'group_set2h':
        target_chat_id = int(parts[2])
        page = int(parts[3])
        day_key = parts[4]
        reminder_group_set_two_hours(target_chat_id, day_key)
        safe_edit(bot, call, reminder_group_text(target_chat_id, day_key), reply_markup=reminder_group_keyboard(target_chat_id, page, day_key))
        return
    if action == 'group_sync':
        target_chat_id = int(parts[2])
        page = int(parts[3])
        day_key = parts[4]
        reminder_group_sync_from_first(target_chat_id, day_key)
        safe_edit(bot, call, reminder_group_text(target_chat_id, day_key), reply_markup=reminder_group_keyboard(target_chat_id, page, day_key))
        return
    if action == 'group_toggle':
        target_chat_id = int(parts[2])
        page = int(parts[3])
        day_key = parts[4]
        reminder_group_toggle_all(target_chat_id, day_key)
        safe_edit(bot, call, reminder_group_text(target_chat_id, day_key), reply_markup=reminder_group_keyboard(target_chat_id, page, day_key))
        return
    if action == 'group_test':
        target_chat_id = int(parts[2])
        page = int(parts[3])
        day_key = parts[4]
        REMINDER_TASK_POOL.submit_unique(f'reminder-group-test:{target_chat_id}', _reminder_group_send_job, target_chat_id, day_key, True)
        try:
            bot.answer_callback_query(call.id, 'Объединённая напоминалка отправляется')
        except Exception:
            pass
        return
    if action == 'completed':
        page = int(parts[2]) if len(parts) > 2 else 0
        delete_mode = bool(int(parts[3])) if len(parts) > 3 and str(parts[3]).isdigit() else False
        safe_edit(bot, call, build_completed_reminders_text(page, delete_mode), reply_markup=build_completed_reminders_keyboard(page, delete_mode))
        return
    if action == 'completed_open':
        rid = int(parts[2])
        page = int(parts[3]) if len(parts) > 3 else 0
        if not _reminder_cfg(rid):
            safe_edit(bot, call, build_completed_reminders_text(page), reply_markup=build_completed_reminders_keyboard(page))
            return
        _reminder_bind_editor(rid, chat_id, call.message.message_id, 'completed', page)
        safe_edit(bot, call, build_reminder_menu_text(rid), reply_markup=build_reminder_menu_keyboard(rid, 'completed', page, viewer_chat_id=chat_id))
        return
    if action == 'completed_select_mode':
        page = int(parts[2]) if len(parts) > 2 else 0
        _REMINDER_COMPLETED_DELETE_SELECTION[int(OWNER_ID or chat_id)].clear()
        safe_edit(bot, call, build_completed_reminders_text(page, True), reply_markup=build_completed_reminders_keyboard(page, True))
        return
    if action == 'completed_select':
        rid = int(parts[2])
        page = int(parts[3]) if len(parts) > 3 else 0
        selected = _REMINDER_COMPLETED_DELETE_SELECTION.setdefault(int(OWNER_ID or chat_id), set())
        if rid in selected:
            selected.remove(rid)
        else:
            selected.add(rid)
        safe_edit(bot, call, build_completed_reminders_text(page, True), reply_markup=build_completed_reminders_keyboard(page, True))
        return
    if action == 'completed_cancel_select':
        page = int(parts[2]) if len(parts) > 2 else 0
        _REMINDER_COMPLETED_DELETE_SELECTION[int(OWNER_ID or chat_id)].clear()
        safe_edit(bot, call, build_completed_reminders_text(page, False), reply_markup=build_completed_reminders_keyboard(page, False))
        return
    if action == 'completed_delete_selected':
        page = int(parts[2]) if len(parts) > 2 else 0
        selected = set(_REMINDER_COMPLETED_DELETE_SELECTION.get(int(OWNER_ID or chat_id), set()))
        root = _reminders_root()
        for rid in selected:
            cfg = _reminder_cfg(rid)
            if cfg:
                _reminder_delete_last_messages(cfg)
            root.setdefault('items', {}).pop(str(rid), None)
            _reminder_unbind(rid)
        _REMINDER_COMPLETED_DELETE_SELECTION[int(OWNER_ID or chat_id)].clear()
        _reminder_save('reminder_completed_bulk_delete')
        rows = _reminder_completed_items()
        pages = max(1, (len(rows) + _REMINDER_COMPLETED_PAGE_SIZE - 1) // _REMINDER_COMPLETED_PAGE_SIZE)
        page = min(page, pages - 1)
        safe_edit(bot, call, build_completed_reminders_text(page, False), reply_markup=build_completed_reminders_keyboard(page, False))
        return
    if action == 'menu':
        day_key = parts[2] if len(parts) > 2 else today_key()
        safe_edit(bot, call, build_reminder_list_text(), reply_markup=build_reminder_list_keyboard(day_key, 0))
        return
    legacy_min_parts = {'dates': 5, 'calendar': 7, 'date': 7, 'noend': 5, 'interval': 5, 'intset': 6, 'hours': 6, 'hourset': 7, 'chats': 6, 'chat': 7, 'toggle': 5, 'delete_confirm': 5, 'delete': 5}
    if action in {'text', 'intcustom', 'cancelinput'} or (action in legacy_min_parts and len(parts) < legacy_min_parts[action]):
        old_day = next((x for x in reversed(parts) if re.fullmatch('\\d{4}-\\d{2}-\\d{2}', str(x or ''))), today_key())
        safe_edit(bot, call, build_reminder_list_text(), reply_markup=build_reminder_list_keyboard(old_day, 0))
        return
    if action == 'list':
        page = int(parts[2]) if len(parts) > 2 else 0
        day_key = parts[3] if len(parts) > 3 else today_key()
        safe_edit(bot, call, build_reminder_list_text(), reply_markup=build_reminder_list_keyboard(day_key, page))
        return
    if action == 'add':
        page = int(parts[2]) if len(parts) > 2 else 0
        day_key = parts[3] if len(parts) > 3 else today_key()
        rid, _cfg = _reminder_create()
        _reminder_bind_editor(rid, chat_id, call.message.message_id, day_key, page)
        safe_edit(bot, call, build_reminder_menu_text(rid), reply_markup=build_reminder_menu_keyboard(rid, day_key, page, viewer_chat_id=chat_id))
        return
    if action == 'open':
        rid = int(parts[2])
        page = int(parts[3]) if len(parts) > 3 else 0
        day_key = parts[4] if len(parts) > 4 else today_key()
        if not _reminder_cfg(rid):
            if str(day_key) == 'completed':
                safe_edit(bot, call, build_completed_reminders_text(page), reply_markup=build_completed_reminders_keyboard(page))
                return
            safe_edit(bot, call, build_reminder_list_text(), reply_markup=build_reminder_list_keyboard(day_key, page))
            return
        _reminder_bind_editor(rid, chat_id, call.message.message_id, day_key, page)
        safe_edit(bot, call, build_reminder_menu_text(rid), reply_markup=build_reminder_menu_keyboard(rid, day_key, page, viewer_chat_id=chat_id))
        return
    if action == 'editmenu':
        rid = int(parts[2])
        page = int(parts[3])
        day_key = parts[4] if len(parts) > 4 else today_key()
        _reminder_bind_editor(rid, chat_id, call.message.message_id, day_key, page)
        safe_edit(bot, call, f'Изменить📝 напоминалку №{_reminder_position(rid) or rid}', reply_markup=_reminder_edit_menu_keyboard(rid, page, day_key, chat_id))
        return
    if action == 'dates':
        rid = int(parts[2])
        page = int(parts[3])
        day_key = parts[4]
        safe_edit(bot, call, _reminder_dates_text(rid), reply_markup=_reminder_dates_keyboard(rid, page, day_key))
        return
    if action == 'calendar':
        which = parts[2] if len(parts) > 2 else 'start'
        ym = parts[3]
        rid = int(parts[4])
        page = int(parts[5])
        day_key = parts[6]
        try:
            year, month = [int(x) for x in ym.split('-', 1)]
        except Exception:
            year, month = (now_local().year, now_local().month)
        safe_edit(bot, call, _reminder_calendar_text(which, year, month), reply_markup=_reminder_calendar_keyboard(which, year, month, rid, page, day_key))
        return
    if action == 'date':
        which, date_key = (parts[2], parts[3])
        rid = int(parts[4])
        page = int(parts[5])
        day_key = parts[6]
        cfg = _reminder_cfg(rid)
        selected = _reminder_parse_date(date_key)
        if not cfg or selected is None:
            return
        if which == 'start':
            cfg['start_date'] = date_key
            end = _reminder_parse_date(cfg.get('end_date'))
            if end and end < selected:
                cfg['end_date'] = date_key
        else:
            start = _reminder_parse_date(cfg.get('start_date')) or selected
            cfg['end_date'] = date_key if selected >= start else start.strftime('%Y-%m-%d')
        if cfg.get('enabled'):
            _reminder_rearm_after_interval_v243(cfg, preserve_future=False)
        _reminder_touch(cfg)
        _reminder_save('reminder_dates')
        safe_edit(bot, call, _reminder_dates_text(rid), reply_markup=_reminder_dates_keyboard(rid, page, day_key))
        return
    if action == 'noend':
        rid = int(parts[2])
        page = int(parts[3])
        day_key = parts[4]
        cfg = _reminder_cfg(rid)
        if not cfg:
            return
        cfg['end_date'] = ''
        if cfg.get('enabled'):
            _reminder_rearm_after_interval_v243(cfg, preserve_future=True)
        _reminder_touch(cfg)
        _reminder_save('reminder_noend')
        safe_edit(bot, call, _reminder_dates_text(rid), reply_markup=_reminder_dates_keyboard(rid, page, day_key))
        return
    if action == 'interval':
        rid = int(parts[2])
        page = int(parts[3])
        day_key = parts[4]
        safe_edit(bot, call, '🔁 ПЕРИОДИЧНОСТЬ\n\nКак часто присылать напоминание?', reply_markup=_reminder_interval_keyboard(rid, page, day_key, chat_id))
        return
    if action == 'intset':
        minutes = int(parts[2])
        rid = int(parts[3])
        page = int(parts[4])
        day_key = parts[5]
        cfg = _reminder_cfg(rid)
        if not cfg:
            return
        cfg['interval_minutes'] = max(5, int(minutes))
        if cfg.get('enabled'):
            _reminder_rearm_after_interval_v243(cfg, preserve_future=False)
        _reminder_touch(cfg)
        _reminder_save('reminder_interval')
        safe_edit(bot, call, build_reminder_menu_text(rid), reply_markup=build_reminder_menu_keyboard(rid, day_key, page, viewer_chat_id=chat_id))
        return
    if action == 'hours':
        which = parts[2]
        rid = int(parts[3])
        page = int(parts[4])
        day_key = parts[5]
        label = 'С КАКОГО ЧАСА' if which == 'start' else 'ДО КАКОГО ЧАСА'
        safe_edit(bot, call, f'🕐 {label}\n\nВыберите час.', reply_markup=_reminder_hours_keyboard(which, rid, page, day_key))
        return
    if action == 'hourset':
        which = parts[2]
        hour = max(0, min(23, int(parts[3])))
        rid = int(parts[4])
        page = int(parts[5])
        day_key = parts[6]
        cfg = _reminder_cfg(rid)
        if not cfg:
            return
        if which == 'start':
            cfg['start_hour'] = hour
            if int(cfg.get('end_hour', 22)) < hour:
                cfg['end_hour'] = hour
        else:
            cfg['end_hour'] = hour
            if int(cfg.get('start_hour', 8)) > hour:
                cfg['start_hour'] = hour
        if cfg.get('enabled'):
            _reminder_rearm_after_interval_v243(cfg, preserve_future=False)
        _reminder_touch(cfg)
        _reminder_save('reminder_hours')
        safe_edit(bot, call, build_reminder_menu_text(rid), reply_markup=build_reminder_menu_keyboard(rid, day_key, page, viewer_chat_id=chat_id))
        return
    if action == 'chats':
        rid = int(parts[2])
        chat_page = int(parts[3])
        list_page = int(parts[4])
        day_key = parts[5]
        safe_edit(bot, call, '💬 ЧАТЫ ДЛЯ НАПОМИНАЛКИ\n\nНажимайте — ✅ выбран / ⬜ не выбран.', reply_markup=_reminder_chats_keyboard(rid, chat_page, list_page, day_key))
        return
    if action == 'chat':
        target = int(parts[2])
        rid = int(parts[3])
        chat_page = int(parts[4])
        list_page = int(parts[5])
        day_key = parts[6]
        cfg = _reminder_cfg(rid)
        if not cfg:
            return
        selected = {int(x) for x in cfg.get('chat_ids') or [] if str(x).lstrip('-').isdigit()}
        if target in selected:
            selected.remove(target)
            old_mid = (cfg.get('last_message_ids') or {}).pop(str(target), None)
            if old_mid:
                try:
                    bot.delete_message(target, int(old_mid))
                except Exception:
                    pass
        else:
            selected.add(target)
        cfg['chat_ids'] = sorted(selected)
        if cfg.get('enabled'):
            _reminder_rearm_after_interval_v243(cfg, preserve_future=True)
        _reminder_touch(cfg)
        _reminder_save('reminder_chats')
        safe_edit(bot, call, '💬 ЧАТЫ ДЛЯ НАПОМИНАЛКИ\n\nНажимайте — ✅ выбран / ⬜ не выбран.', reply_markup=_reminder_chats_keyboard(rid, chat_page, list_page, day_key))
        return
    if action == 'toggle':
        rid = int(parts[2])
        page = int(parts[3])
        day_key = parts[4]
        cfg = _reminder_cfg(rid)
        if not cfg:
            return
        if _reminder_is_completed(cfg):
            send_and_auto_delete(chat_id, '✅ Эта напоминалка завершена. Для повторного запуска используйте «♻️ Возобновить».', 10)
            safe_edit(bot, call, build_reminder_menu_text(rid), reply_markup=build_reminder_menu_keyboard(rid, day_key, page, viewer_chat_id=chat_id))
            return
        if not cfg.get('enabled'):
            if not str(cfg.get('text') or '').strip():
                send_and_auto_delete(chat_id, '❌ Сначала задайте текст напоминания.', 8)
                return
            if not (cfg.get('chat_ids') or []):
                send_and_auto_delete(chat_id, '❌ Сначала выберите хотя бы один чат.', 8)
                return
            if _reminder_parse_date(cfg.get('end_date')) and _reminder_parse_date(cfg.get('end_date')) < now_local().date():
                cfg['end_date'] = ''
            cfg['enabled'] = True
            _reminder_rearm_after_interval_v243(cfg, preserve_future=False)
        else:
            cfg['enabled'] = False
            cfg['next_run_at'] = ''
        _reminder_touch(cfg)
        _reminder_save('reminder_toggle_v243')
        safe_edit(bot, call, build_reminder_menu_text(rid), reply_markup=build_reminder_menu_keyboard(rid, day_key, page, viewer_chat_id=chat_id))
        return
    if action == 'resume_confirm':
        rid = int(parts[2])
        page = int(parts[3])
        day_key = parts[4]
        cfg = _reminder_cfg(rid)
        if not cfg:
            return
        kb = types.InlineKeyboardMarkup(row_width=1)
        kb.row(IB('✅ Да, возобновить', callback_data=f'rem:resume:{rid}:{page}:{day_key}'))
        kb.row(IB('⬅️ Отмена', callback_data=f'rem:open:{rid}:{page}:{day_key}'))
        safe_edit(bot, call, '♻️ Возобновить завершённую напоминалку?\n\nСледующая отправка будет поставлена по её текущему интервалу, а не немедленно.', reply_markup=kb)
        return
    if action == 'resume':
        rid = int(parts[2])
        page = int(parts[3])
        day_key = parts[4]
        cfg = _reminder_cfg(rid)
        if not cfg:
            return
        if not str(cfg.get('text') or '').strip() or not (cfg.get('chat_ids') or []):
            send_and_auto_delete(chat_id, '❌ Для возобновления нужен текст и хотя бы один чат.', 10)
            return
        _reminder_clear_completion_v243(cfg)
        if _reminder_parse_date(cfg.get('end_date')) and _reminder_parse_date(cfg.get('end_date')) < now_local().date():
            cfg['end_date'] = ''
        cfg['enabled'] = True
        _reminder_rearm_after_interval_v243(cfg, preserve_future=False)
        _reminder_touch(cfg)
        _reminder_save('reminder_resume_v243')
        safe_edit(bot, call, build_reminder_menu_text(rid), reply_markup=build_reminder_menu_keyboard(rid, day_key, page, viewer_chat_id=chat_id))
        return
    if action == 'delete_confirm':
        rid = int(parts[2])
        page = int(parts[3])
        day_key = parts[4]
        kb = types.InlineKeyboardMarkup(row_width=2)
        kb.row(IB('🗑 Да, удалить', callback_data=f'rem:delete:{rid}:{page}:{day_key}'), IB('✖️ Отмена', callback_data=f'rem:open:{rid}:{page}:{day_key}'))
        safe_edit(bot, call, '🗑 Удалить напоминалку?\n\nПоследние отправленные сообщения этой напоминалки тоже будут удалены из выбранных чатов.', reply_markup=kb)
        return
    if action == 'delete':
        rid = int(parts[2])
        page = int(parts[3])
        day_key = parts[4]
        root = _reminders_root()
        cfg = _reminder_cfg(rid)
        if cfg:
            _reminder_delete_last_messages(cfg)
        root.setdefault('items', {}).pop(str(rid), None)
        _reminder_unbind(rid)
        _reminder_save('reminder_delete')
        if str(day_key) == 'completed':
            rows = _reminder_completed_items()
            pages = max(1, (len(rows) + _REMINDER_COMPLETED_PAGE_SIZE - 1) // _REMINDER_COMPLETED_PAGE_SIZE)
            page = min(page, pages - 1)
            safe_edit(bot, call, build_completed_reminders_text(page), reply_markup=build_completed_reminders_keyboard(page))
            return
        rows = _reminder_items()
        pages = max(1, (len(rows) + _REMINDER_LIST_PAGE_SIZE - 1) // _REMINDER_LIST_PAGE_SIZE)
        page = min(page, pages - 1)
        safe_edit(bot, call, build_reminder_list_text(), reply_markup=build_reminder_list_keyboard(day_key, page))
        return

# --- reminders:0074 · from 04_messages_features.py:3172 · public _reminder_date_allowed_for_day ---
def _reminder_date_allowed_for_day(cfg: dict, day_key: str) -> bool:
    try:
        d = datetime.strptime(str(day_key), '%Y-%m-%d').date()
    except Exception:
        d = now_local().date()
    start = _reminder_parse_date((cfg or {}).get('start_date'))
    end = _reminder_parse_date((cfg or {}).get('end_date'))
    return not (start and d < start or (end and d > end))

# --- reminders:0075 · from 04_messages_features.py:3181 · public _reminder_single_chat_id ---
def _reminder_single_chat_id(cfg: dict) -> int | None:
    ids = []
    for raw in (cfg or {}).get('chat_ids') or []:
        try:
            ids.append(int(raw))
        except Exception:
            pass
    ids = list(dict.fromkeys(ids))
    return ids[0] if len(ids) == 1 else None

# --- reminders:0076 · from 04_messages_features.py:3191 · public reminder_group_members ---
def reminder_group_members(target_chat_id: int, day_key: str | None=None, enabled_only: bool=False) -> list[tuple[int, dict]]:
    target_chat_id = int(target_chat_id)
    day_key = str(day_key or today_key())
    rows = []
    for rid, cfg in _reminder_items():
        if _reminder_single_chat_id(cfg) != target_chat_id:
            continue
        if enabled_only and (not bool(cfg.get('enabled'))):
            continue
        if not _reminder_date_allowed_for_day(cfg, day_key):
            continue
        rows.append((int(rid), cfg))
    rows.sort(key=lambda row: row[0])
    return rows

# --- reminders:0077 · from 04_messages_features.py:3206 · public _reminder_group_map ---
def _reminder_group_map(day_key: str | None=None, enabled_only: bool=False) -> dict[int, list[tuple[int, dict]]]:
    day_key = str(day_key or today_key())
    grouped = defaultdict(list)
    for rid, cfg in _reminder_items():
        cid = _reminder_single_chat_id(cfg)
        if cid is None:
            continue
        if enabled_only and (not bool(cfg.get('enabled'))):
            continue
        if not _reminder_date_allowed_for_day(cfg, day_key):
            continue
        grouped[int(cid)].append((int(rid), cfg))
    return {cid: sorted(rows, key=lambda row: row[0]) for cid, rows in grouped.items() if len(rows) >= 2}

# --- reminders:0078 · from 04_messages_features.py:3220 · public _reminder_new_list_entries ---
def _reminder_new_list_entries(day_key: str) -> list[tuple[str, int, object]]:
    groups = _reminder_group_map(day_key, enabled_only=False)
    grouped_ids = {rid for rows in groups.values() for rid, _cfg in rows}
    entries = []
    for cid, rows in groups.items():
        entries.append(('group', min((rid for rid, _ in rows)), (cid, rows)))
    for rid, cfg in _reminder_items():
        if rid not in grouped_ids:
            entries.append(('item', int(rid), (int(rid), cfg)))
    entries.sort(key=lambda row: row[1])
    return entries

# --- reminders:0079 · from 04_messages_features.py:3232 · public _v177_legacy_0124_build_reminder_list_text ---
def _v177_legacy_0124_build_reminder_list_text() -> str:
    if not reminder_ui_new_enabled():
        return _BUILD_REMINDER_LIST_TEXT_V141()
    rows = _reminder_items()
    groups = _reminder_group_map(today_key(), enabled_only=False)
    enabled = sum((1 for _rid, cfg in rows if bool(cfg.get('enabled'))))
    return f'⏰ НАПОМИНАЛКИ · ПРОСТОЙ РЕЖИМ\n\nТекущих: {len(rows)} · активных: {enabled}\nОбъединённых чатов: {len(groups)}\nЗавершённых: {len(_reminder_completed_items())}\n\nНастройка идёт по шагам: текст → чаты → период → расписание → проверка.\nЕсли в одном чате несколько напоминалок, бот объединяет их в одно сообщение каждые 2 часа.'

# --- reminders:0080 · from 04_messages_features.py:3244 · public _v177_legacy_0126_build_reminder_list_keyboard ---
def _v177_legacy_0126_build_reminder_list_keyboard(day_key: str | None=None, page: int=0):
    if not reminder_ui_new_enabled():
        return _BUILD_REMINDER_LIST_KEYBOARD_V141(day_key, page)
    day_key = str(day_key or today_key())
    entries = _reminder_new_list_entries(day_key)
    pages = max(1, (len(entries) + _REMINDER_LIST_PAGE_SIZE - 1) // _REMINDER_LIST_PAGE_SIZE)
    page = max(0, min(int(page or 0), pages - 1))
    kb = types.InlineKeyboardMarkup(row_width=1)
    kb.row(IB('+добавить⏰', callback_data=f'rem:add:{page}:{day_key}'))
    start = page * _REMINDER_LIST_PAGE_SIZE
    for kind, _order, payload in entries[start:start + _REMINDER_LIST_PAGE_SIZE]:
        if kind == 'group':
            cid, members = payload
            title = chat_button_title(int(cid)) if 'chat_button_title' in globals() else get_chat_display_name(int(cid))
            active = sum((1 for _rid, cfg in members if bool(cfg.get('enabled'))))
            label = pad_button_label_41(f'👥 {title} · {len(members)} шт · {active} акт')
            kb.row(IB(label, callback_data=f'rem:group_open:{int(cid)}:{page}:{day_key}'))
        else:
            rid, cfg = payload
            pos = _reminder_position(rid) or rid
            kb.row(IB(_reminder_button_label(pos, cfg), callback_data=f'rem:open:{rid}:{page}:{day_key}'))
    if pages > 1:
        nav = []
        if page > 0:
            nav.append(IB('⬅️', callback_data=f'rem:list:{page - 1}:{day_key}'))
        nav.append(IB(f'{page + 1}/{pages}', callback_data='none'))
        if page + 1 < pages:
            nav.append(IB('➡️', callback_data=f'rem:list:{page + 1}:{day_key}'))
        kb.row(*nav)
    kb.row(IB(f'✅ Завершённые ({len(_reminder_completed_items())})', callback_data='rem:completed:0:0'))
    kb.row(IB('⬅️ Назад', callback_data=f'd:{day_key}:back_main'))
    return kb

# --- reminders:0081 · from 04_messages_features.py:3281 · public _reminder_step_state ---
def _reminder_step_state(cfg: dict) -> list[str]:
    return ['✅' if str(cfg.get('text') or '').strip() else '❌', '✅' if cfg.get('chat_ids') or [] else '❌', '✅' if int(cfg.get('interval_minutes', 0) or 0) >= 5 else '❌', '✅' if str(cfg.get('start_date') or '').strip() else '❌']

# --- reminders:0082 · from 04_messages_features.py:3284 · public _v177_legacy_0128_build_reminder_menu_text ---
def _v177_legacy_0128_build_reminder_menu_text(reminder_id: int) -> str:
    if not reminder_ui_new_enabled():
        return _BUILD_REMINDER_MENU_TEXT_V141(reminder_id)
    cfg = _reminder_cfg(reminder_id)
    if not cfg:
        return '⏰ Напоминалка не найдена.'
    steps = _reminder_step_state(cfg)
    preview = re.sub('\\s+', ' ', str(cfg.get('text') or '').strip())
    if len(preview) > 110:
        preview = preview[:107] + '...'
    state = '✅ АКТИВНО' if cfg.get('enabled') and (not _reminder_is_completed(cfg)) else '⬜ ВЫКЛЮЧЕНО'
    if _reminder_is_completed(cfg):
        state = '✅ ЗАВЕРШЕНО'
    return f"⏰ НАПОМИНАЛКА №{_reminder_position(reminder_id) or reminder_id}\n\n{steps[0]} 1. Текст: {preview or 'не задан'}\n{steps[1]} 2. Чаты: {len(cfg.get('chat_ids') or [])}\n{steps[2]} 3. Период: {_reminder_interval_label(cfg.get('interval_minutes', 120))}\n{steps[3]} 4. Расписание: {_reminder_fmt_date(cfg.get('start_date'))} · {int(cfg.get('start_hour', 8)):02d}:00–{int(cfg.get('end_hour', 22)):02d}:59\n\nСостояние: {state}\nСледующая: {_reminder_fmt_dt(cfg.get('next_run_at'))}"

# --- reminders:0083 · from 04_messages_features.py:3303 · public _v177_legacy_0130_build_reminder_menu_keyboard ---
def _v177_legacy_0130_build_reminder_menu_keyboard(reminder_id: int, day_key: str | None=None, page: int=0, viewer_chat_id: int | None=None):
    if not reminder_ui_new_enabled():
        return _BUILD_REMINDER_MENU_KEYBOARD_V141(reminder_id, day_key, page, viewer_chat_id)
    day_key = str(day_key or today_key())
    cfg = _reminder_cfg(reminder_id)
    kb = types.InlineKeyboardMarkup(row_width=2)
    if not cfg:
        kb.row(IB('⬅️ К напоминалкам', callback_data=_reminder_return_callback(page, day_key)))
        return kb
    kb.row(make_copy_or_inline_button('1️⃣ Текст', compose_reminder_text_insert_value(reminder_id, cfg.get('text') or ''), viewer_chat_id=viewer_chat_id), IB(f"2️⃣ Чаты · {len(cfg.get('chat_ids') or [])}", callback_data=f'rem:chats:{reminder_id}:0:{page}:{day_key}'))
    kb.row(IB(f"3️⃣ Период · {_reminder_interval_label(cfg.get('interval_minutes', 120))}", callback_data=f'rem:interval:{reminder_id}:{page}:{day_key}'), IB('4️⃣ Расписание', callback_data=f'rem:schedule:{reminder_id}:{page}:{day_key}'))
    kb.row(IB('5️⃣ Проверить и включить', callback_data=f'rem:preview:{reminder_id}:{page}:{day_key}'))
    try:
        merge_fn = globals().get('_v207_reminder_merge_mode')
        merge_mode = str(merge_fn(cfg, viewer_chat_id) if callable(merge_fn) else 'off')
    except Exception:
        merge_mode = 'off'
    merge_label = {'off': '🚫 Отдельно', 'smart': '🧠 SMART: объединять 2+', 'single': '📌 Всегда 1 сообщение'}.get(merge_mode, '🚫 Отдельно')
    try:
        complete_fn = globals().get('_v207_reminder_complete_button_enabled')
        complete_on = bool(complete_fn(cfg, viewer_chat_id)) if callable(complete_fn) else False
    except Exception:
        complete_on = False
    kb.row(IB(merge_label, callback_data=f'v149:rem:item_merge:{reminder_id}:{page}:{day_key}'))
    kb.row(IB(f"{('✅' if complete_on else '⬜')} Кнопка «Выполнить»: {('ВКЛ' if complete_on else 'ВЫКЛ')}", callback_data=f'v149:rem:item_complete:{reminder_id}:{page}:{day_key}'))
    if _reminder_is_completed(cfg):
        kb.row(IB('♻️ Возобновить', callback_data=f'rem:resume_confirm:{reminder_id}:{page}:{day_key}'), IB('Изменить📝', callback_data=f'rem:editmenu:{reminder_id}:{page}:{day_key}'))
    else:
        state_label = '✅ Активно' if cfg.get('enabled') else '⬜ Выключено'
        kb.row(IB(state_label, callback_data=f'rem:toggle:{reminder_id}:{page}:{day_key}'), IB('Изменить📝', callback_data=f'rem:editmenu:{reminder_id}:{page}:{day_key}'))
    kb.row(IB('⬅️ К напоминалкам', callback_data=_reminder_return_callback(page, day_key)))
    return kb

# --- reminders:0084 · from 04_messages_features.py:3340 · public reminder_schedule_text ---
def reminder_schedule_text(reminder_id: int) -> str:
    cfg = _reminder_cfg(reminder_id) or {}
    end = _reminder_fmt_date(cfg.get('end_date')) if cfg.get('end_date') else 'без конца'
    return f"4️⃣ РАСПИСАНИЕ\n\nДаты: {_reminder_fmt_date(cfg.get('start_date'))} → {end}\nВремя: {int(cfg.get('start_hour', 8)):02d}:00 → {int(cfg.get('end_hour', 22)):02d}:59"

# --- reminders:0085 · from 04_messages_features.py:3345 · public reminder_schedule_keyboard ---
def reminder_schedule_keyboard(reminder_id: int, page: int, day_key: str):
    cfg = _reminder_cfg(reminder_id) or {}
    kb = types.InlineKeyboardMarkup(row_width=2)
    kb.row(IB('📅 Даты', callback_data=f'rem:dates:{reminder_id}:{page}:{day_key}'))
    kb.row(IB(f"🕗 С {int(cfg.get('start_hour', 8)):02d}:00", callback_data=f'rem:hours:start:{reminder_id}:{page}:{day_key}'), IB(f"🕙 До {int(cfg.get('end_hour', 22)):02d}:59", callback_data=f'rem:hours:end:{reminder_id}:{page}:{day_key}'))
    kb.row(IB('⬅️ Назад', callback_data=f'rem:open:{reminder_id}:{page}:{day_key}'))
    return kb

# --- reminders:0086 · from 04_messages_features.py:3353 · public _reminder_preview_times ---
def _reminder_preview_times(cfg: dict, count: int=3) -> list[datetime]:
    tmp = copy.deepcopy(cfg or {})
    now_dt = now_local()
    due = _reminder_parse_dt(tmp.get('next_run_at'))
    if due is None or due < now_dt:
        due = _reminder_next_valid_start(now_dt, tmp)
    out = []
    for _ in range(max(1, int(count))):
        if due is None:
            break
        out.append(due)
        _reminder_advance_after_send(due, tmp)
        due = _reminder_parse_dt(tmp.get('next_run_at'))
    return out

# --- reminders:0087 · from 04_messages_features.py:3368 · public reminder_preview_text ---
def reminder_preview_text(reminder_id: int) -> str:
    cfg = _reminder_cfg(reminder_id) or {}
    errors = []
    if not str(cfg.get('text') or '').strip():
        errors.append('не задан текст')
    if not (cfg.get('chat_ids') or []):
        errors.append('не выбран чат')
    times = _reminder_preview_times(cfg, 3)
    lines = ['5️⃣ ПРОВЕРКА НАПОМИНАЛКИ', '']
    lines.append('Сообщение:')
    lines.append('НАПОМИНАЛКА🕰️')
    lines.append(str(cfg.get('text') or 'не задано')[:900])
    lines += ['', 'Чаты:']
    for raw in (cfg.get('chat_ids') or [])[:12]:
        try:
            lines.append('• ' + get_chat_display_name(int(raw)))
        except Exception:
            pass
    lines += ['', 'Ближайшие отправки:']
    lines.extend(('• ' + dt.strftime('%d.%m %H:%M') for dt in times))
    if errors:
        lines += ['', '❌ Нельзя включить: ' + ', '.join(errors)]
    else:
        lines += ['', '✅ Настройки готовы.']
    return '\n'.join(lines)

# --- reminders:0088 · from 04_messages_features.py:3394 · public reminder_preview_keyboard ---
def reminder_preview_keyboard(reminder_id: int, page: int, day_key: str, viewer_chat_id: int):
    cfg = _reminder_cfg(reminder_id) or {}
    kb = types.InlineKeyboardMarkup(row_width=1)
    valid = bool(str(cfg.get('text') or '').strip() and (cfg.get('chat_ids') or []))
    if valid:
        label = '✅ ВКЛ' if cfg.get('enabled') else '⬜ ВЫКЛ'
        kb.row(IB(label, callback_data=f'rem:toggle:{reminder_id}:{page}:{day_key}'))
    kb.row(IB('⬅️ Назад', callback_data=f'rem:open:{reminder_id}:{page}:{day_key}'))
    return kb

# --- reminders:0089 · from 04_messages_features.py:3404 · public _reminder_group_state_root ---
def _reminder_group_state_root() -> dict:
    return data.setdefault('_global_settings', {}).setdefault('reminder_groups_v142', {})

# --- reminders:0090 · from 04_messages_features.py:3407 · public _reminder_group_key ---
def _reminder_group_key(target_chat_id: int, day_key: str) -> str:
    return f'{str(day_key)}:{int(target_chat_id)}'

# --- reminders:0091 · from 04_messages_features.py:3410 · public reminder_group_text ---
def reminder_group_text(target_chat_id: int, day_key: str) -> str:
    members = reminder_group_members(target_chat_id, day_key, enabled_only=False)
    active = sum((1 for _rid, cfg in members if bool(cfg.get('enabled'))))
    lines = ['👥 ОБЪЕДИНЁННАЯ НАПОМИНАЛКА', '', f'Чат: {get_chat_display_name(int(target_chat_id))}', f'Напоминалок: {len(members)} · активных: {active}', 'Общий ритм при совместной работе: каждые 2 часа.', '']
    for idx, (_rid, cfg) in enumerate(members, 1):
        text = re.sub('\\s+', ' ', str(cfg.get('text') or 'без текста').strip())
        lines.append(f'{idx}. {text[:180]}')
    lines += ['', 'Можно открыть каждую отдельно или применить общие настройки ко всем.']
    return '\n'.join(lines)

# --- reminders:0092 · from 04_messages_features.py:3420 · public reminder_group_keyboard ---
def reminder_group_keyboard(target_chat_id: int, page: int, day_key: str):
    members = reminder_group_members(target_chat_id, day_key, enabled_only=False)
    kb = types.InlineKeyboardMarkup(row_width=1)
    for idx, (rid, cfg) in enumerate(members, 1):
        kb.row(IB(_reminder_button_label(idx, cfg), callback_data=f'rem:open:{rid}:{page}:{day_key}'))
    any_disabled = any((not bool(cfg.get('enabled')) for _rid, cfg in members))
    kb.row(IB('⬜ Все напоминания' if any_disabled else '✅ Все напоминания', callback_data=f'rem:group_toggle:{int(target_chat_id)}:{page}:{day_key}'))
    kb.row(IB('🔁 Всем каждые 2 часа', callback_data=f'rem:group_set2h:{int(target_chat_id)}:{page}:{day_key}'))
    kb.row(IB('🧩 Настройки первой → всем', callback_data=f'rem:group_sync:{int(target_chat_id)}:{page}:{day_key}'))
    kb.row(IB('🧪 Напомнить сейчас', callback_data=f'rem:group_test:{int(target_chat_id)}:{page}:{day_key}'))
    kb.row(IB('⬅️ К напоминалкам', callback_data=f'rem:list:{page}:{day_key}'))
    return kb

# --- reminders:0093 · from 04_messages_features.py:3433 · public reminder_group_set_two_hours ---
def reminder_group_set_two_hours(target_chat_id: int, day_key: str) -> None:
    with _REMINDER_CONFIG_LOCK:
        for _rid, cfg in reminder_group_members(target_chat_id, day_key, enabled_only=False):
            cfg['interval_minutes'] = _REMINDER_GROUP_INTERVAL_MINUTES
            if cfg.get('enabled'):
                _reminder_rearm_after_interval_v243(cfg, preserve_future=False)
            _reminder_touch(cfg)
    _reminder_save('reminder_group_2h')

# --- reminders:0094 · from 04_messages_features.py:3442 · public reminder_group_sync_from_first ---
def reminder_group_sync_from_first(target_chat_id: int, day_key: str) -> None:
    with _REMINDER_CONFIG_LOCK:
        members = reminder_group_members(target_chat_id, day_key, enabled_only=False)
        if not members:
            return
        src = members[0][1]
        shared = {'start_date': src.get('start_date') or today_key(), 'end_date': src.get('end_date') or '', 'start_hour': int(src.get('start_hour', 8)), 'end_hour': int(src.get('end_hour', 22)), 'interval_minutes': _REMINDER_GROUP_INTERVAL_MINUTES}
        for _rid, cfg in members:
            cfg.update(shared)
            if cfg.get('enabled'):
                _reminder_rearm_after_interval_v243(cfg, preserve_future=False)
            _reminder_touch(cfg)
    _reminder_save('reminder_group_sync')

# --- reminders:0095 · from 04_messages_features.py:3456 · public reminder_group_toggle_all ---
def reminder_group_toggle_all(target_chat_id: int, day_key: str) -> None:
    with _REMINDER_CONFIG_LOCK:
        members = reminder_group_members(target_chat_id, day_key, enabled_only=False)
        enable = any((not bool(cfg.get('enabled')) for _rid, cfg in members))
        for _rid, cfg in members:
            if enable and str(cfg.get('text') or '').strip():
                if _reminder_is_completed(cfg):
                    continue
                cfg['enabled'] = True
                cfg['interval_minutes'] = _REMINDER_GROUP_INTERVAL_MINUTES
                _reminder_rearm_after_interval_v243(cfg, preserve_future=False)
            elif not enable:
                cfg['enabled'] = False
                cfg['next_run_at'] = ''
            _reminder_touch(cfg)
    _reminder_save('reminder_group_toggle')

# --- reminders:0096 · from 04_messages_features.py:3473 · public _reminder_group_message_text ---
def _reminder_group_message_text(members: list[tuple[int, dict]]) -> str:
    lines = ['НАПОМИНАЛКА🕰️', '']
    budget = 3850
    for idx, (_rid, cfg) in enumerate(members, 1):
        text = str(cfg.get('text') or '').strip()
        block = f'{idx}. {text}'
        if sum((len(x) + 1 for x in lines)) + len(block) > budget:
            remain = max(0, budget - sum((len(x) + 1 for x in lines)) - 2)
            if remain:
                lines.append(block[:remain] + '…')
            break
        lines.append(block)
    return '\n'.join(lines)

# --- reminders:0097 · from 04_messages_features.py:3487 · public _reminder_group_next_time ---
def _reminder_group_next_time(now_dt: datetime, members: list[tuple[int, dict]]):
    candidate = now_dt + timedelta(minutes=_REMINDER_GROUP_INTERVAL_MINUTES)
    for _ in range(16):
        if any((_reminder_date_allowed(candidate, cfg) and _reminder_time_allowed(candidate, cfg) for _rid, cfg in members)):
            return candidate
        next_day = candidate.date() + timedelta(days=1)
        start_hour = min((int(cfg.get('start_hour', 8)) for _rid, cfg in members))
        candidate = datetime.combine(next_day, datetime.min.time(), tzinfo=now_dt.tzinfo).replace(hour=start_hour)
    return None

# --- reminders:0098 · from 04_messages_features.py:3497 · public _v177_legacy_0134_reminder_group_delete_message ---
def _v177_legacy_0134_reminder_group_delete_message(target_chat_id: int, message_id: int) -> None:
    if not message_id:
        return
    try:
        bot.delete_message(int(target_chat_id), int(message_id))
    except Exception:
        pass

# --- reminders:0099 · from 04_messages_features.py:3509 · public _v177_legacy_0135_reminder_group_send_job ---
def _v177_legacy_0135_reminder_group_send_job(target_chat_id: int, day_key: str, force: bool=False) -> None:
    target_chat_id = int(target_chat_id)
    day_key = str(day_key or today_key())
    now_dt = now_local()
    with _REMINDER_CONFIG_LOCK:
        members = reminder_group_members(target_chat_id, day_key, enabled_only=not force)
        if not force:
            members = [row for row in members if _reminder_date_allowed(now_dt, row[1]) and _reminder_time_allowed(now_dt, row[1]) and _reminder_due_now(row[1], now_dt)]
        if len(members) < 2:
            return
        state = _reminder_group_state_root().setdefault(_reminder_group_key(target_chat_id, day_key), {})
        old_group_mid = int(state.get('last_message_id') or 0)
        old_individual = []
        for _rid, cfg in members:
            old = (cfg.get('last_message_ids') or {}).pop(str(target_chat_id), None)
            if old:
                old_individual.append(int(old))
        snapshot = [(rid, copy.deepcopy(cfg)) for rid, cfg in members]
    try:
        sent = bot.send_message(target_chat_id, _reminder_group_message_text(snapshot))
    except Exception as exc:
        log_error(f'reminder group send {target_chat_id}: {exc}')
        with _REMINDER_GROUP_LOCK:
            state = _reminder_group_state_root().setdefault(_reminder_group_key(target_chat_id, day_key), {})
            state['next_run_at'] = (now_dt + timedelta(minutes=5)).isoformat(timespec='seconds')
            state['last_error'] = str(exc)[:300]
        _reminder_save('reminder_group_retry')
        return
    for mid in set(old_individual + ([old_group_mid] if old_group_mid else [])):
        if mid and int(mid) != int(sent.message_id):
            _reminder_group_delete_message(target_chat_id, mid)
    next_dt = _reminder_group_next_time(now_dt, snapshot)
    with _REMINDER_CONFIG_LOCK:
        state = _reminder_group_state_root().setdefault(_reminder_group_key(target_chat_id, day_key), {})
        state.update({'target_chat_id': target_chat_id, 'day_key': day_key, 'member_ids': [rid for rid, _cfg in snapshot], 'last_message_id': int(sent.message_id), 'last_sent_at': now_dt.isoformat(timespec='seconds'), 'next_run_at': next_dt.isoformat(timespec='seconds') if next_dt else '', 'last_error': ''})
        for rid, _old_cfg in snapshot:
            cfg = _reminder_cfg(rid)
            if not cfg:
                continue
            cfg['last_sent_at'] = now_dt.isoformat(timespec='seconds')
            cfg['next_run_at'] = next_dt.isoformat(timespec='seconds') if next_dt else ''
            cfg['interval_minutes'] = _REMINDER_GROUP_INTERVAL_MINUTES
            _reminder_touch(cfg)
    _reminder_save('reminder_group_sent')
    try:
        bot_journal('reminder_group_sent', target_chat_id, f'members={[rid for rid, _ in snapshot]} message_id={sent.message_id}')
    except Exception:
        pass

# --- reminders:0100 · from 04_messages_features.py:3562 · public _reminder_finance_priority_busy ---
def _reminder_finance_priority_busy() -> bool:
    try:
        for pool in (FINANCE_TASK_POOL, FIN_FORWARD_TASK_POOL):
            st = pool.stats()
            if int(st.get('pending', 0) or 0) > 0 or int(st.get('active', 0) or 0) > 0:
                return True
    except Exception:
        pass
    return False

# --- reminders:0101 · from 04_messages_features.py:3572 · public _reminder_cleanup_stale_groups ---
def _reminder_cleanup_stale_groups(active_keys: set[str]) -> None:
    root = _reminder_group_state_root()
    for key in list(root.keys()):
        if key in active_keys:
            continue
        row = root.pop(key, {}) or {}
        mid = int(row.get('last_message_id') or 0)
        cid = int(row.get('target_chat_id') or 0)
        if mid and cid:
            pool = globals().get('GENERAL_TASK_POOL')
            if pool:
                pool.submit_unique(f'reminder-group-clean:{cid}:{mid}', _reminder_group_delete_message, cid, mid)

# --- reminders:0102 · from 04_messages_features.py:3585 · public _v177_legacy_0133_reminder_tick ---
def _v177_legacy_0133_reminder_tick() -> None:
    """Old mode sends every reminder individually; new mode groups only reminders due now.

    A configured same-day group no longer suppresses a single reminder whose partner is not
    currently due or is outside its active hours. Finance has a bounded 60-second priority
    window so reminders cannot starve forever.
    """
    global _REMINDER_FINANCE_BUSY_SINCE
    now_dt = now_local()
    day_key = now_dt.strftime('%Y-%m-%d')
    finance_busy = _reminder_finance_priority_busy()
    if finance_busy:
        if not _REMINDER_FINANCE_BUSY_SINCE:
            _REMINDER_FINANCE_BUSY_SINCE = time.monotonic()
        busy_for = time.monotonic() - _REMINDER_FINANCE_BUSY_SINCE
        if busy_for < _REMINDER_FINANCE_PRIORITY_GRACE_SECONDS:
            return
        try:
            bot_journal('reminder_finance_priority_expired', None, f'busy_for={busy_for:.1f}s; overdue reminders allowed')
        except Exception:
            pass
    else:
        _REMINDER_FINANCE_BUSY_SINCE = 0.0
    completed_changed = False
    due_rows = []
    with _REMINDER_CONFIG_LOCK:
        for rid, cfg in _reminder_items():
            if _reminder_end_has_passed(cfg, now_dt):
                _reminder_mark_completed(rid, cfg, 'end_date_finished', delete_messages=True)
                completed_changed = True
                continue
            try:
                if _reminder_due_now(cfg, now_dt):
                    due_rows.append((int(rid), cfg))
            except Exception as exc:
                log_error(f'reminder {rid} due check: {exc}')
    if not reminder_ui_new_enabled():
        _reminder_cleanup_stale_groups(set())
        for rid, _cfg in due_rows:
            if not REMINDER_TASK_POOL.submit_unique(f'reminder:{rid}', _reminder_tick_job, rid):
                bot_journal('reminder_dispatch_coalesced', None, f'reminder_id={rid}')
        if completed_changed:
            _reminder_save('reminder_completed_tick')
        return
    configured_groups = _reminder_group_map(day_key, enabled_only=True)
    active_group_keys = {_reminder_group_key(cid, day_key) for cid in configured_groups}
    _reminder_cleanup_stale_groups(active_group_keys)
    due_by_chat = defaultdict(list)
    for rid, cfg in due_rows:
        cid = _reminder_single_chat_id(cfg)
        if cid is None:
            continue
        if _reminder_date_allowed(now_dt, cfg) and _reminder_time_allowed(now_dt, cfg):
            due_by_chat[int(cid)].append((rid, cfg))
    grouped_ids = set()
    grouped_count = 0
    for cid, members in due_by_chat.items():
        if len(members) < 2:
            continue
        grouped_ids.update((rid for rid, _cfg in members))
        grouped_count += 1
        REMINDER_TASK_POOL.submit_unique(f'reminder-group:{cid}:{day_key}', _reminder_group_send_job, cid, day_key, False)
    individual_count = 0
    for rid, _cfg in due_rows:
        if rid in grouped_ids:
            continue
        individual_count += 1
        if not REMINDER_TASK_POOL.submit_unique(f'reminder:{rid}', _reminder_tick_job, rid):
            bot_journal('reminder_dispatch_coalesced', None, f'reminder_id={rid}')
    if due_rows:
        try:
            bot_journal('reminder_tick_dispatch', None, f'mode=new due={len(due_rows)} groups={grouped_count} individual={individual_count} finance_busy={int(finance_busy)}')
        except Exception:
            pass
    if completed_changed:
        _reminder_save('reminder_completed_tick')

# --- reminders:0103 · from 07_state_web.py:662 · public _canon_reminder_delete_message_map__001 ---
def _canon_reminder_delete_message_map__001(last_map: dict) -> None:
    for cid_raw, mid_raw in list((last_map or {}).items()):
        try:
            bot.delete_message(int(cid_raw), int(mid_raw))
            bot_journal('reminder_previous_deleted', int(cid_raw), f'message_id={int(mid_raw)}')
        except Exception as exc:
            bot_journal('reminder_previous_delete_failed', int(cid_raw), f'message_id={mid_raw} error={str(exc)[:300]}', 'WARN')

# --- reminders:0104 · from 07_state_web.py:670 · public _canon_reminder_mark_completed__001 ---
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

# --- reminders:0105 · from 07_state_web.py:681 · public _canon_reminder_group_delete_message__001 ---
def _canon_reminder_group_delete_message__001(chat_id: int, message_id: int):
    try:
        result = _V146_ORIG_REM_GROUP_DELETE(chat_id, message_id) if callable(_V146_ORIG_REM_GROUP_DELETE) else bot.delete_message(int(chat_id), int(message_id))
        bot_journal('reminder_group_previous_deleted', int(chat_id), f'message_id={int(message_id)}')
        return result
    except Exception as exc:
        bot_journal('reminder_group_previous_delete_failed', int(chat_id), f'message_id={message_id} error={str(exc)[:300]}', 'WARN')
        return None

# --- reminders:0106 · from 07_state_web.py:1345 · public _canon_reminder_ui_mode__001 ---
def _canon_reminder_ui_mode__001() -> str:
    mode = str(_tenant_settings_for_context().get('reminder_ui_mode_v142') or 'new').lower()
    return mode if mode in {'old', 'new'} else 'new'

# --- reminders:0107 · from 07_state_web.py:1349 · public _canon_set_reminder_ui_mode__001 ---
def _canon_set_reminder_ui_mode__001(mode: str) -> str:
    mode = 'new' if str(mode).lower() == 'new' else 'old'
    _tenant_settings_for_context()['reminder_ui_mode_v142'] = mode
    save_data(data, root_only=True)
    return mode

# --- reminders:0108 · from 07_state_web.py:1431 · public _reminder_context_filter_active ---
def _reminder_context_filter_active() -> bool:
    return bool(getattr(_TENANT_CONTEXT, 'tenant_id', None) or current_state_chat_id() is not None)

# --- reminders:0109 · from 07_state_web.py:1434 · public _canon_reminder_items__001 ---
def _canon_reminder_items__001(include_completed: bool=False) -> list[tuple[int, dict]]:
    rows = _V148_ORIG_REMINDER_ITEMS(include_completed=include_completed) if callable(_V148_ORIG_REMINDER_ITEMS) else []
    if not _reminder_context_filter_active():
        return rows
    tid = tenant_current_id()
    return [(rid, cfg) for rid, cfg in rows if str((cfg or {}).get('tenant_id') or TENANT_PLATFORM_ID) == tid]

# --- reminders:0110 · from 07_state_web.py:1441 · public _canon_reminder_cfg__001 ---
def _canon_reminder_cfg__001(reminder_id: int | str | None=None, create: bool=False) -> dict | None:
    cfg = _V148_ORIG_REMINDER_CFG(reminder_id, create=create) if callable(_V148_ORIG_REMINDER_CFG) else None
    if not isinstance(cfg, dict):
        return cfg
    if create and (not cfg.get('tenant_id')):
        cfg['tenant_id'] = tenant_current_id()
    if _reminder_context_filter_active() and str(cfg.get('tenant_id') or TENANT_PLATFORM_ID) != tenant_current_id():
        return None
    return cfg

# --- reminders:0111 · from 07_state_web.py:1451 · public _canon_reminder_create__001 ---
def _canon_reminder_create__001() -> tuple[int, dict]:
    rid, cfg = _V148_ORIG_REMINDER_CREATE()
    cfg['tenant_id'] = tenant_current_id()
    _reminder_save('tenant_reminder_add')
    return (rid, cfg)

# --- reminders:0112 · from 07_state_web.py:1457 · public reminder_cfg_global_for_completion ---
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

# --- reminders:0113 · from 07_state_web.py:1477 · public reminder_items_global_for_completion ---
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

# --- reminders:0114 · from 07_state_web.py:2949 · public _v149_reminder_settings ---
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

# --- reminders:0115 · from 07_state_web.py:2960 · public _v149_reminder_chat_settings ---
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

# --- reminders:0116 · from 07_state_web.py:2989 · public _v177_legacy_0261_reminder_merge_mode ---
def _v177_legacy_0261_reminder_merge_mode(tenant_id: str | None=None, chat_id: int | None=None) -> str:
    settings = _v149_reminder_chat_settings(tenant_id, chat_id)
    mode = str(settings.get('merge_mode') or '').strip().lower()
    if mode not in REMINDER_MERGE_MODES_V169:
        mode = 'smart' if bool(settings.get('merge_enabled', False)) else 'off'
    settings['merge_mode'] = mode
    settings['merge_enabled'] = mode != 'off'
    return mode

# --- reminders:0117 · from 07_state_web.py:3002 · public _v177_legacy_0262_reminder_merge_enabled ---
def _v177_legacy_0262_reminder_merge_enabled(tenant_id: str | None=None, chat_id: int | None=None) -> bool:
    return reminder_merge_mode(tenant_id, chat_id) != 'off'

# --- reminders:0118 · from 07_state_web.py:3009 · public _v177_legacy_0263_reminder_merge_mode_label ---
def _v177_legacy_0263_reminder_merge_mode_label(tenant_id: str | None=None, chat_id: int | None=None) -> str:
    return {'off': 'ВЫКЛ', 'smart': 'ВКЛ', 'single': '1 СООБЩЕНИЕ'}.get(reminder_merge_mode(tenant_id, chat_id), 'ВЫКЛ')

# --- reminders:0119 · from 07_state_web.py:3016 · public reminder_show_complete_command ---
def reminder_show_complete_command(tenant_id: str | None=None, chat_id: int | None=None) -> bool:
    return bool(_v149_reminder_chat_settings(tenant_id, chat_id).get('show_complete_command', False))

# --- reminders:0120 · from 07_state_web.py:3019 · public _v207_reminder_setting_chat ---
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

# --- reminders:0121 · from 07_state_web.py:3035 · public _v207_reminder_merge_mode ---
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

# --- reminders:0122 · from 07_state_web.py:3050 · public _canon_v207_reminder_complete_button_enabled__001 ---
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

# --- reminders:0123 · from 07_state_web.py:3062 · public _v207_reminder_merge_label ---
def _v207_reminder_merge_label(cfg: dict | None, chat_id: int | None=None) -> str:
    return {'off': '⬜ Объединять: ВЫКЛ', 'smart': '✅ Объединять: ВКЛ', 'single': '✅ Объединять: 1 СООБЩЕНИЕ'}.get(_v207_reminder_merge_mode(cfg, chat_id), '⬜ Объединять: ВЫКЛ')

# --- reminders:0124 · from 07_state_web.py:3065 · public _canon_v207_reminder_complete_keyboard__001 ---
def _canon_v207_reminder_complete_keyboard__001(reminder_id: int, cfg: dict, chat_id: int):
    if not _v207_reminder_complete_button_enabled(cfg, chat_id):
        return None
    kb = types.InlineKeyboardMarkup(row_width=1)
    kb.row(IB('✅ Выполнить', callback_data=f'v149:rem:done:{int(reminder_id)}:{int(chat_id)}'))
    return kb

# --- reminders:0125 · from 07_state_web.py:3072 · public _canon_v207_reminder_group_keyboard__001 ---
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

# --- reminders:0126 · from 07_state_web.py:3085 · public _v149_reminder_all_rows ---
def _v149_reminder_all_rows(include_completed: bool=False) -> list[tuple[int, dict]]:
    return reminder_items_global_for_completion(include_completed=include_completed)

# --- reminders:0127 · from 07_state_web.py:3088 · public _v149_reminder_chat_ids ---
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

# --- reminders:0128 · from 07_state_web.py:3099 · public _v149_reminder_cfg_tenant ---
def _v149_reminder_cfg_tenant(cfg: dict) -> str:
    return str((cfg or {}).get('tenant_id') or TENANT_PLATFORM_ID)

# --- reminders:0129 · from 07_state_web.py:3102 · public _v177_legacy_0264_v149_reminder_chat_allowed ---
def _v177_legacy_0264_v149_reminder_chat_allowed(cfg: dict, chat_id: int) -> bool:
    tid = _v149_reminder_cfg_tenant(cfg)
    return _v149_chat_belongs_to_tenant(int(chat_id), tid)

# --- reminders:0130 · from 07_state_web.py:3110 · public _v149_reminder_active_now ---
def _v149_reminder_active_now(cfg: dict, now_dt) -> bool:
    return bool(cfg and cfg.get('enabled') and (not _reminder_is_completed(cfg)) and str(cfg.get('text') or '').strip() and _reminder_date_allowed(now_dt, cfg) and _reminder_time_allowed(now_dt, cfg))

# --- reminders:0131 · from 07_state_web.py:3123 · public _canon_v149_reminder_message_text__001 ---
def _canon_v149_reminder_message_text__001(reminder_id: int, cfg: dict, chat_id: int, active_count: int=1) -> str:
    return '\n'.join(['НАПОМИНАЛКА🕰️', '', str(cfg.get('text') or '').strip()])[:4000]

# --- reminders:0132 · from 07_state_web.py:3212 · public _v245_reminder_snapshot_valid ---
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

# --- reminders:0133 · from 07_state_web.py:3255 · public _v149_reminder_batch_job ---
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

# --- reminders:0134 · from 07_state_web.py:3476 · public _canon_reminder_tick__001 ---
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

# --- reminders:0135 · from 07_state_web.py:3492 · public _canon_reminder_group_send_job__001 ---
def _canon_reminder_group_send_job__001(target_chat_id: int, day_key: str | None=None, force: bool=False) -> None:
    _v149_reminder_batch_job(int(target_chat_id))

# --- reminders:0136 · from 07_state_web.py:3495 · public _canon_build_reminder_list_text__001 ---
def _canon_build_reminder_list_text__001() -> str:
    rows = _reminder_items()
    enabled = sum((1 for _rid, cfg in rows if bool(cfg.get('enabled'))))
    return f'⏰ НАПОМИНАЛКИ\n\nТекущих: {len(rows)} · активных: {enabled}\nЗавершённых: {len(_reminder_completed_items())}\n\nНастройки «Объединять» и кнопки «Выполнить» теперь задаются отдельно внутри каждой напоминалки.'

# --- reminders:0137 · from 07_state_web.py:3500 · public _canon_build_reminder_list_keyboard__001 ---
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

# --- reminders:0138 · from 07_state_web.py:3523 · public _canon_v149_reminders_for_completion__001 ---
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

# --- reminders:0139 · from 07_state_web.py:3537 · public _canon_v149_complete_reminder__001 ---
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

# --- reminders:0140 · from 07_state_web.py:6347 · public _v150_reminder_chat_lines ---
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

# --- reminders:0141 · from 07_state_web.py:6365 · public _canon_build_reminder_menu_text__001 ---
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

# --- reminders:0142 · from 07_state_web.py:6388 · public _canon_build_reminder_menu_keyboard__001 ---
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

# --- reminders:0143 · from 08_reliability_tasks.py:11231 · public _v177_legacy_0265_v149_reminder_chat_allowed ---
def _v177_legacy_0265_v149_reminder_chat_allowed(cfg: dict, chat_id: int) -> bool:
    cid = int(chat_id)
    try:
        selected = {int(x) for x in (cfg or {}).get('chat_ids') or []}
    except Exception:
        selected = set()
    if cid not in selected:
        return False
    try:
        tid = str(_v149_reminder_cfg_tenant(cfg) or TENANT_PLATFORM_ID)
    except Exception:
        tid = str(globals().get('TENANT_PLATFORM_ID') or 'platform')
    platform_id = str(globals().get('TENANT_PLATFORM_ID') or 'platform')
    if tid == platform_id:
        try:
            known = {int(x) for x in collect_all_known_chat_ids(include_owner=True)}
            return cid in known
        except Exception:
            return False
    try:
        return bool(_v149_chat_belongs_to_tenant(cid, tid))
    except Exception:
        return bool(_V171_PREV_REMINDER_CHAT_ALLOWED(cfg, cid)) if callable(_V171_PREV_REMINDER_CHAT_ALLOWED) else False

# --- reminders:0144 · from 08_reliability_tasks.py:11260 · public _v171_reminder_global_mode ---
def _v171_reminder_global_mode(migrate: bool=True) -> str:
    gs = data.setdefault('_global_settings', {})
    mode = str(gs.get('reminder_merge_mode_global_v171') or '').strip().lower()
    if mode not in V171_REMINDER_MERGE_MODES and migrate:
        old = 'off'
        try:
            owner = int(OWNER_ID or 0)
            if owner:
                settings = _v149_reminder_chat_settings(None, owner)
                old = str(settings.get('merge_mode') or '').strip().lower()
                if old not in V171_REMINDER_MERGE_MODES:
                    old = 'smart' if bool(settings.get('merge_enabled', False)) else 'off'
        except Exception:
            old = 'off'
        mode = old if old in V171_REMINDER_MERGE_MODES else 'off'
        gs['reminder_merge_mode_global_v171'] = mode
    return mode if mode in V171_REMINDER_MERGE_MODES else 'off'

# --- reminders:0145 · from 08_reliability_tasks.py:11278 · public _canon_reminder_merge_mode__001 ---
def _canon_reminder_merge_mode__001(tenant_id: str | None=None, chat_id: int | None=None) -> str:
    return _v171_reminder_global_mode(True)

# --- reminders:0146 · from 08_reliability_tasks.py:11281 · public _canon_reminder_merge_enabled__001 ---
def _canon_reminder_merge_enabled__001(tenant_id: str | None=None, chat_id: int | None=None) -> bool:
    return reminder_merge_mode(tenant_id, chat_id) != 'off'

# --- reminders:0147 · from 08_reliability_tasks.py:11284 · public _canon_reminder_merge_mode_label__001 ---
def _canon_reminder_merge_mode_label__001(tenant_id: str | None=None, chat_id: int | None=None) -> str:
    return {'off': 'ВЫКЛ', 'smart': 'ВКЛ', 'single': '1 СООБЩЕНИЕ'}.get(reminder_merge_mode(tenant_id, chat_id), 'ВЫКЛ')

# --- reminders:0148 · from 08_reliability_tasks.py:11287 · public _v171_cycle_reminder_merge ---
def _v171_cycle_reminder_merge() -> str:
    current = _v171_reminder_global_mode(True)
    try:
        idx = V171_REMINDER_MERGE_MODES.index(current)
    except ValueError:
        idx = 0
    mode = V171_REMINDER_MERGE_MODES[(idx + 1) % len(V171_REMINDER_MERGE_MODES)]
    data.setdefault('_global_settings', {})['reminder_merge_mode_global_v171'] = mode
    try:
        save_data(data, root_only=True)
    except Exception:
        pass
    return mode

# --- reminders:0149 · from 08_reliability_tasks.py:11300 · public _reminder_extension_callback ---
def _reminder_extension_callback(call, data_str: str) -> bool:
    raw = str(data_str or '')
    if raw.startswith('v149:rem:item_merge:') or raw.startswith('v149:rem:item_complete:'):
        chat_id = int(call.message.chat.id)
        user_id = int(getattr(getattr(call, 'from_user', None), 'id', 0) or 0)
        try:
            tid = str(tenant_id_for_chat(chat_id, create=False) or TENANT_PLATFORM_ID)
            if not tenant_can_manage(user_id, tid):
                bot.answer_callback_query(call.id, 'Недостаточно прав', show_alert=True)
                return True
            parts = raw.split(':')
            action = str(parts[2] or '')
            rid = int(parts[3])
            page = int(parts[4]) if len(parts) > 4 and str(parts[4]).isdigit() else 0
            day_key = parts[5] if len(parts) > 5 else today_key()
            with tenant_context(tid):
                cfg = _reminder_cfg(rid)
                if not isinstance(cfg, dict):
                    bot.answer_callback_query(call.id, 'Напоминалка не найдена', show_alert=True)
                    return True
                if action == 'item_merge':
                    current = _v207_reminder_merge_mode(cfg, chat_id)
                    try:
                        idx = REMINDER_MERGE_MODES_V169.index(current)
                    except ValueError:
                        idx = 0
                    cfg['merge_mode_v207'] = REMINDER_MERGE_MODES_V169[(idx + 1) % len(REMINDER_MERGE_MODES_V169)]
                    toast = _v207_reminder_merge_label(cfg, chat_id).replace('✅ ', '').replace('⬜ ', '')
                else:
                    cfg['show_complete_button_v207'] = not _v207_reminder_complete_button_enabled(cfg, chat_id)
                    toast = f"Кнопка «Выполнить»: {('ВКЛ' if cfg['show_complete_button_v207'] else 'ВЫКЛ')}"
                _reminder_touch(cfg)
                _reminder_save(f'v207_{action}')
                safe_edit(bot, call, build_reminder_menu_text(rid), reply_markup=build_reminder_menu_keyboard(rid, day_key, page, viewer_chat_id=chat_id))
            try:
                REMINDER_TASK_POOL.submit_unique('reminder-v149-batch', _v149_reminder_batch_job, int(chat_id))
            except Exception:
                pass
            try:
                bot.answer_callback_query(call.id, toast[:180])
            except Exception:
                pass
            return True
        except Exception as exc:
            try:
                log_error(f'v207 reminder item setting: {exc}')
            except Exception:
                pass
            try:
                bot.answer_callback_query(call.id, 'Не удалось обновить настройку', show_alert=True)
            except Exception:
                pass
            return True
    if raw.startswith(('v149:rem:merge:', 'v149:rem:command:')):
        chat_id = int(call.message.chat.id)
        user_id = int(getattr(getattr(call, 'from_user', None), 'id', 0) or 0)
        try:
            tid = str(tenant_id_for_chat(chat_id, create=False) or TENANT_PLATFORM_ID)
            if not tenant_can_manage(user_id, tid):
                bot.answer_callback_query(call.id, 'Недостаточно прав', show_alert=True)
                return True
        except Exception:
            pass
        parts = raw.split(':')
        page = int(parts[3]) if len(parts) > 3 and str(parts[3]).isdigit() else 0
        day_key = parts[4] if len(parts) > 4 else today_key()
        try:
            safe_edit(bot, call, build_reminder_list_text(), reply_markup=build_reminder_list_keyboard(day_key, page))
        except Exception as exc:
            try:
                log_error(f'v207 stale reminder global control redirect: {exc}')
            except Exception:
                pass
        try:
            bot.answer_callback_query(call.id, 'Эта настройка теперь находится внутри каждой напоминалки')
        except Exception:
            pass
        return True
    return False

# --- reminders:0150 · from 08_reliability_tasks.py:12950 · public _v173_reminder_selected_chat_ids ---
def _v173_reminder_selected_chat_ids(cfg: dict) -> set[int]:
    out = set()
    for raw in (cfg or {}).get('chat_ids') or []:
        try:
            out.add(int(raw))
        except Exception:
            continue
    return out

# --- reminders:0151 · from 08_reliability_tasks.py:12959 · public _canon_v149_reminder_chat_allowed__001 ---
def _canon_v149_reminder_chat_allowed__001(cfg: dict, chat_id: int) -> bool:
    """Final send-time authority for reminder targets.

    Platform owner reminder:
      explicit selection in cfg.chat_ids is enough; Telegram itself is the final
      reachability check.  Do not re-filter through a tenant-scoped chat picker.

    Non-platform tenant reminder:
      retain strict tenant membership so second-circle spaces cannot notify chats
      belonging to another space merely by injecting an id into stored config.
    """
    try:
        cid = int(chat_id)
    except Exception:
        return False
    if cid not in _v173_reminder_selected_chat_ids(cfg):
        return False
    # R17: one final lifecycle authority for every reminder path.  A confirmed
    # removed/migrated/archived chat is terminal and must never be retried by the
    # scheduler, even if its old id is still present in a stale reminder snapshot.
    try:
        lifecycle_fn = globals().get('_v150_lifecycle')
        status = str((lifecycle_fn(cid) or {}).get('status') or '') if callable(lifecycle_fn) else ''
        if status in {'bot_removed', 'migrated', 'archived'}:
            return False
    except Exception:
        try:
            removed_fn = globals().get('is_chat_bot_removed')
            if callable(removed_fn) and bool(removed_fn(cid)):
                return False
        except Exception:
            pass
    platform_id = str(globals().get('TENANT_PLATFORM_ID') or 'platform')
    try:
        tid = str(_v149_reminder_cfg_tenant(cfg) or platform_id)
    except Exception:
        tid = str((cfg or {}).get('tenant_id') or platform_id)
    if tid == platform_id:
        return True
    try:
        return bool(_v149_chat_belongs_to_tenant(cid, tid))
    except Exception:
        if callable(_V173_PREV_REMINDER_CHAT_ALLOWED):
            try:
                return bool(_V173_PREV_REMINDER_CHAT_ALLOWED(cfg, cid))
            except Exception:
                pass
        return False

# --- reminders:0152 · from 08_reliability_tasks.py:14800 · public _v224_show_reminders_home ---
def _v224_show_reminders_home(chat_id: int, user_id: int=0, current_message_id: int=0) -> int:
    cid = int(chat_id)
    uid = int(user_id or 0)
    mid = int(current_message_id or 0)
    try:
        text = build_v217_chat_reminders_text(cid)
        kb = build_v217_chat_reminders_keyboard(cid, uid)
    except Exception:
        text = window_mark('⏰ НАПОМИНАНИЯ\n\nНапоминания разрешены владельцем для этого чата.', V217_CHAT_REMINDERS_MARKER if 'V217_CHAT_REMINDERS_MARKER' in globals() else 'Ф257')
        kb = types.InlineKeyboardMarkup()
        kb.row(IB('❌ Закрыть', callback_data='aux_close'))
    return _v215_edit_or_send(cid, mid, text, kb, 'directive_reminders_home_v224')

# --- reminders:0153 · from 08_reliability_tasks.py:15882 · public _v215_existing_reminder_target ---
def _v215_existing_reminder_target(chat_id: int) -> bool:
    cid = int(chat_id)
    try:
        root = _reminders_root()
        for cfg in (root.get('items', {}) or {}).values():
            if not isinstance(cfg, dict):
                continue
            for raw in cfg.get('chat_ids') or []:
                try:
                    if int(raw) == cid:
                        return True
                except Exception:
                    continue
    except Exception:
        pass
    return False

# --- reminders:0154 · from 08_reliability_tasks.py:15899 · public contour_reminders_mode_enabled ---
def contour_reminders_mode_enabled(chat_id: int) -> bool:
    cid = int(chat_id)
    settings = _v215_mode_settings(cid)
    if V215_REMINDER_MODE_KEY not in settings:
        return _v215_existing_reminder_target(cid)
    return bool(settings.get(V215_REMINDER_MODE_KEY))

# --- reminders:0155 · from 08_reliability_tasks.py:15931 · public _v215_set_reminders_mode ---
def _v215_set_reminders_mode(chat_id: int, enabled: bool, *, persist: bool=True) -> bool:
    cid = int(chat_id)
    value = bool(enabled)
    _v215_mode_settings(cid)[V215_REMINDER_MODE_KEY] = value
    if persist:
        _v215_persist_mode(cid, 'reminders_mode')
    return value

# --- reminders:0156 · from 08_reliability_tasks.py:16228 · public _canon_reminder_send_cycle__002 ---
def _canon_reminder_send_cycle__002(reminder_id: int, cfg: dict) -> bool:
    if not isinstance(cfg, dict):
        return _V215_PREV_REMINDER_SEND_CYCLE(reminder_id, cfg)
    filtered = []
    for raw in cfg.get('chat_ids') or []:
        try:
            cid = int(raw)
        except Exception:
            continue
        if _v215_circle_business_chat(cid) and (not contour_reminders_mode_enabled(cid)):
            continue
        filtered.append(cid)
    if filtered == list(cfg.get('chat_ids') or []):
        return _V215_PREV_REMINDER_SEND_CYCLE(reminder_id, cfg)
    clone = dict(cfg)
    clone['chat_ids'] = filtered
    return _V215_PREV_REMINDER_SEND_CYCLE(reminder_id, clone)

# --- reminders:0157 · from 08_reliability_tasks.py:16247 · public _canon_reminder_group_send_job__002 ---
def _canon_reminder_group_send_job__002(target_chat_id: int, day_key: str, force: bool=False) -> None:
    cid = int(target_chat_id)
    try:
        lifecycle_fn = globals().get('_v150_lifecycle')
        if callable(lifecycle_fn) and str((lifecycle_fn(cid) or {}).get('status') or '') in {'bot_removed', 'migrated', 'archived'}:
            return
    except Exception:
        pass
    if _v215_circle_business_chat(cid) and (not contour_reminders_mode_enabled(cid)):
        return
    return _V215_PREV_REMINDER_GROUP_SEND(cid, day_key, force)

# --- reminders:0158 · from 08_reliability_tasks.py:16623 · public _canon_v149_reminder_message_text__002 ---
def _canon_v149_reminder_message_text__002(reminder_id: int, cfg: dict, chat_id: int, active_count: int=1) -> str:
    return '\n'.join([f'НАПОМИНАЛКА #{int(reminder_id)}🕰️', '', str((cfg or {}).get('text') or '').strip()])[:4000]

# --- reminders:0159 · from 08_reliability_tasks.py:16637 · public _canon_v207_reminder_complete_keyboard__002 ---
def _canon_v207_reminder_complete_keyboard__002(reminder_id: int, cfg: dict, chat_id: int):
    if not _v207_reminder_complete_button_enabled(cfg, chat_id):
        return None
    kb = types.InlineKeyboardMarkup(row_width=1)
    kb.row(IB('✅ Выполнено', callback_data=f'v149:rem:done:{int(reminder_id)}:{int(chat_id)}'))
    return kb

# --- reminders:0160 · from 08_reliability_tasks.py:16644 · public _canon_v207_reminder_group_keyboard__002 ---
def _canon_v207_reminder_group_keyboard__002(chat_id: int, members: list[tuple[int, dict]]):
    kb = types.InlineKeyboardMarkup(row_width=1)
    count = 0
    for rid, cfg in members:
        if not _v207_reminder_complete_button_enabled(cfg, chat_id):
            continue
        label = str((cfg or {}).get('text') or f'Напоминалка {rid}').strip().replace('\n', ' ')
        if len(label) > 40:
            label = label[:37] + '…'
        kb.row(IB(f'✅ Выполнено · #{int(rid)} {label}', callback_data=f'v149:rem:done:{int(rid)}:{int(chat_id)}'))
        count += 1
    return kb if count else None

# --- reminders:0161 · from 08_reliability_tasks.py:16658 · public _canon_build_reminder_list_keyboard__002 ---
def _canon_build_reminder_list_keyboard__002(day_key: str | None=None, page: int=0):
    kb = _V217_PREV_REMINDER_LIST_KB(day_key, page)
    try:
        cid = int(current_state_chat_id() or 0)
        if _v215_circle_business_chat(cid):
            _v217_insert_before_nav(kb, IB('📋 Напоминалки этого чата', callback_data='v217:remchat:list'))
            _v217_insert_before_nav(kb, IB('☰ Меню', callback_data='v217:contour:menu'))
    except Exception:
        pass
    return kb

# --- reminders:0162 · from 08_reliability_tasks.py:16669 · public _canon_v217_chat_reminder_rows__001 ---
def _canon_v217_chat_reminder_rows__001(chat_id: int) -> list[tuple[int, dict]]:
    cid = int(chat_id)
    tid = str(tenant_id_for_chat(cid, create=False) or '')
    rows = []
    try:
        with tenant_context(tid):
            for rid, cfg in _reminder_items(include_completed=True):
                if int(cid) in [int(x) for x in cfg.get('chat_ids') or [] if str(x).lstrip('-').isdigit()]:
                    rows.append((int(rid), cfg))
    except Exception:
        pass
    rows.sort(key=lambda x: x[0])
    return rows

# --- reminders:0163 · from 08_reliability_tasks.py:16683 · public _v217_reminder_status ---
def _v217_reminder_status(cfg: dict) -> str:
    if _reminder_is_completed(cfg):
        return '✅ выполнена'
    if bool(cfg.get('enabled')):
        return '✅ активна'
    return '⬜ выключена'

# --- reminders:0164 · from 08_reliability_tasks.py:16690 · public build_v217_chat_reminders_text ---
def build_v217_chat_reminders_text(chat_id: int) -> str:
    rows = _v217_chat_reminder_rows(int(chat_id))
    lines = ['📋 НАПОМИНАЛКИ ЭТОГО ЧАТА', '', str(get_chat_display_name(int(chat_id)) or chat_id), f'Всего: {len(rows)}', '']
    if not rows:
        lines.append('Для этого чата напоминалок нет.')
    for rid, cfg in rows[:35]:
        short = _v217_re.sub('\\s+', ' ', str(cfg.get('text') or '').strip())
        if len(short) > 52:
            short = short[:49] + '…'
        next_at = _reminder_fmt_dt(cfg.get('next_run_at')) if cfg.get('next_run_at') else '—'
        try:
            period = _reminder_interval_label(cfg.get('interval_minutes', 120))
        except Exception:
            period = f"{int(cfg.get('interval_minutes', 0) or 0)} мин"
        lines.append(f"#{rid} · {_v217_reminder_status(cfg)}\n{short or 'без текста'}\nПериод: {period} · Следующая: {next_at}")
    return window_mark('\n\n'.join(lines)[:3900], V217_CHAT_REMINDERS_MARKER)

# --- reminders:0165 · from 08_reliability_tasks.py:16707 · public _canon_build_v217_chat_reminders_keyboard__001 ---
def _canon_build_v217_chat_reminders_keyboard__001(chat_id: int, user_id: int):
    cid = int(chat_id)
    uid = int(user_id or 0)
    rows = _v217_chat_reminder_rows(cid)
    kb = types.InlineKeyboardMarkup(row_width=1)
    can_manage = False
    try:
        can_manage = bool(security_user_allowed(uid, 'reminder_manage'))
    except Exception:
        pass
    for rid, cfg in rows[:30]:
        label = _v217_re.sub('\\s+', ' ', str(cfg.get('text') or '').strip())
        if len(label) > 43:
            label = label[:40] + '…'
        cb = f'v217:remchat:open:{rid}' if can_manage else 'none'
        kb.row(IB(f"#{rid} · {_v217_reminder_status(cfg)} · {label or 'без текста'}", callback_data=cb))
    try:
        directive_single = bool(globals().get('directive_chat_enabled_v223', lambda _c: False)(cid)) and resolve_contour_home(cid) == 'reminders'
    except Exception:
        directive_single = False
    if not directive_single:
        kb.row(IB('🔙 К режиму', callback_data='v215:mode:open:reminders'))
        kb.row(IB('☰ Меню', callback_data='v217:contour:menu'))
    else:
        kb.row(IB('❌ Закрыть', callback_data='aux_close'))
    return kb

# --- reminders:0166 · from 08_reliability_tasks.py:16734 · public _canon_v217_find_reply_reminder__001 ---
def _canon_v217_find_reply_reminder__001(chat_id: int, reply_message_id: int) -> tuple[int | None, str]:
    cid = int(chat_id)
    mid = int(reply_message_id or 0)
    candidates = []
    for rid, cfg in _v217_chat_reminder_rows(cid):
        if _reminder_is_completed(cfg) or not cfg.get('enabled'):
            continue
        try:
            if int((cfg.get('last_message_ids') or {}).get(str(cid)) or 0) == mid:
                candidates.append(int(rid))
        except Exception:
            pass
    try:
        state = _v149_group_state_root().get(_v149_group_key(cid), {}) or {}
        if int(state.get('last_message_id') or 0) == mid:
            for raw in state.get('member_ids') or []:
                try:
                    rid = int(raw)
                    if rid not in candidates:
                        cfg = _reminder_cfg(rid)
                        if cfg and (not _reminder_is_completed(cfg)) and cfg.get('enabled'):
                            candidates.append(rid)
                except Exception:
                    pass
    except Exception:
        pass
    if len(candidates) == 1:
        return (candidates[0], 'ok')
    if len(candidates) > 1:
        return (None, 'В этом сообщении несколько напоминалок. Укажите /выполнено #N.')
    return (None, 'Ответьте именно на сообщение нужной напоминалки или укажите /выполнено #N.')

# --- reminders:0167 · from 08_reliability_tasks.py:17003 · public _v218_reminder_complete_button_enabled ---
def _v218_reminder_complete_button_enabled(cfg: dict | None, chat_id: int | None=None) -> bool:
    return _v218_completion_mode(cfg, chat_id) == 'button'

# --- reminders:0168 · from 08_reliability_tasks.py:17007 · public _v218_reminder_message_text ---
def _v218_reminder_message_text(reminder_id: int, cfg: dict, chat_id: int, active_count: int=1) -> str:
    lines = [f'НАПОМИНАЛКА #{int(reminder_id)}🕰️', '', str((cfg or {}).get('text') or '').strip()]
    if _v218_completion_mode(cfg, chat_id) == 'slash':
        lines += ['', f'Выполнить: /done_{int(reminder_id)}']
    return '\n'.join(lines)[:4000]

# --- reminders:0169 · from 08_reliability_tasks.py:17026 · public _v218_reminder_complete_keyboard ---
def _v218_reminder_complete_keyboard(reminder_id: int, cfg: dict, chat_id: int):
    if _v218_completion_mode(cfg, chat_id) != 'button':
        return None
    kb = types.InlineKeyboardMarkup(row_width=1)
    kb.row(IB('✅ Выполнить', callback_data=f'v149:rem:done:{int(reminder_id)}:{int(chat_id)}'))
    return kb

# --- reminders:0170 · from 08_reliability_tasks.py:17033 · public _v218_reminder_group_keyboard ---
def _v218_reminder_group_keyboard(chat_id: int, members: list[tuple[int, dict]]):
    kb = types.InlineKeyboardMarkup(row_width=1)
    count = 0
    for rid, cfg in members:
        if _v218_completion_mode(cfg, chat_id) != 'button':
            continue
        label = str((cfg or {}).get('text') or f'Напоминалка {rid}').strip().replace('\n', ' ')
        if len(label) > 40:
            label = label[:37] + '…'
        kb.row(IB(f'✅ Выполнить · #{int(rid)} {label}', callback_data=f'v149:rem:done:{int(rid)}:{int(chat_id)}'))
        count += 1
    return kb if count else None

# --- reminders:0171 · from 08_reliability_tasks.py:17047 · public _v218_build_reminder_menu_keyboard ---
def _v218_build_reminder_menu_keyboard(reminder_id: int, day_key: str | None=None, page: int=0, viewer_chat_id: int | None=None):
    kb = _V218_PREV_REMINDER_MENU_KB(reminder_id, day_key, page, viewer_chat_id)
    cfg = _reminder_cfg(reminder_id)
    if not isinstance(cfg, dict):
        return kb
    try:
        for row in _v217_rows(kb):
            for btn in row or []:
                if _v217_btn_cb(btn).startswith('v149:rem:item_complete:'):
                    label = _v218_completion_label(cfg, viewer_chat_id)
                    if isinstance(btn, dict):
                        btn['text'] = label
                    else:
                        btn.text = label
    except Exception:
        pass
    return kb

# --- reminders:0172 · from 08_reliability_tasks.py:17066 · public _v218_reminders_for_completion ---
def _v218_reminders_for_completion(chat_id: int) -> list[tuple[int, dict]]:
    rows = _V218_PREV_REMINDERS_FOR_COMPLETION(int(chat_id))
    return [(rid, cfg) for rid, cfg in rows if _v218_completion_mode(cfg, int(chat_id)) == 'slash']

# --- reminders:0173 · from 08_reliability_tasks.py:17680 · public _v220_reminder_list_keyboard ---
def _v220_reminder_list_keyboard(day_key: str | None=None, page: int=0):
    kb = _V220_PREV_REMINDER_LIST_KB(day_key, page)
    try:
        cid = int(current_state_chat_id() or 0)
    except Exception:
        cid = 0
    return _v220_remove_contour_menu_button(kb, cid)

# --- reminders:0174 · from 08_reliability_tasks.py:17689 · public _v220_chat_reminder_keyboard ---
def _v220_chat_reminder_keyboard(chat_id: int, user_id: int):
    return _v220_remove_contour_menu_button(_V220_PREV_CHAT_REMINDER_KB(int(chat_id), int(user_id or 0)), int(chat_id))

# --- reminders:0175 · from 08_reliability_tasks.py:17853 · public _v220_reconcile_completed_reminder_groups ---
def _v220_reconcile_completed_reminder_groups(reminder_id: int, chat_ids: list[int]) -> None:
    for cid in sorted(set((int(x) for x in chat_ids or [] if int(x)))):
        try:
            _v149_reminder_batch_job(int(cid))
        except Exception as exc:
            try:
                log_error(f'v220 reminder group reconcile {int(reminder_id)} chat {cid}: {exc}')
            except Exception:
                pass

# --- reminders:0176 · from 08_reliability_tasks.py:17864 · public _v220_complete_reminder ---
def _v220_complete_reminder(reminder_id: int, chat_id: int, actor_user_id: int, actor_label: str) -> tuple[bool, str]:
    rid = int(reminder_id)
    cid = int(chat_id)
    try:
        cfg_before = _reminder_cfg(rid)
        recipients = list(_v149_reminder_chat_ids(cfg_before)) if isinstance(cfg_before, dict) else []
    except Exception:
        recipients = []
    ok, answer = _V220_PREV_COMPLETE_REMINDER(rid, cid, int(actor_user_id or 0), str(actor_label or ''))
    if ok:
        try:
            REMINDER_TASK_POOL.submit_unique(f'reminder-v220-complete-reconcile:{rid}', _v220_reconcile_completed_reminder_groups, rid, list(recipients))
        except Exception:
            try:
                _v220_reconcile_completed_reminder_groups(rid, list(recipients))
            except Exception:
                pass
        try:
            bot_journal('reminder_global_reconcile_v220', cid, f'reminder_id={rid}; recipients={sorted(set(recipients))}')
        except Exception:
            pass
    return (ok, answer)

# --- reminders:0177 · from 08_reliability_tasks.py:17887 · public _v220_reminder_complete_keyboard ---
def _v220_reminder_complete_keyboard(reminder_id: int, cfg: dict, chat_id: int):
    if _v218_completion_mode(cfg, chat_id) != 'button':
        return None
    kb = types.InlineKeyboardMarkup(row_width=1)
    kb.row(IB('✅ Выполнено', callback_data=f'v149:rem:done:{int(reminder_id)}:{int(chat_id)}'))
    return kb

# --- reminders:0178 · from 08_reliability_tasks.py:17894 · public _v220_reminder_group_keyboard ---
def _v220_reminder_group_keyboard(chat_id: int, members: list[tuple[int, dict]]):
    kb = types.InlineKeyboardMarkup(row_width=1)
    count = 0
    for rid, cfg in members:
        if _v218_completion_mode(cfg, chat_id) != 'button':
            continue
        label = str((cfg or {}).get('text') or f'Напоминалка {rid}').strip().replace('\n', ' ')
        if len(label) > 40:
            label = label[:37] + '…'
        kb.row(IB(f'✅ Выполнено · #{int(rid)} {label}', callback_data=f'v149:rem:done:{int(rid)}:{int(chat_id)}'))
        count += 1
    return kb if count else None

# --- reminders:0179 · from 08_reliability_tasks.py:18705 · public _v221_chat_reminder_rows ---
def _v221_chat_reminder_rows(chat_id: int) -> list[tuple[int, dict]]:
    cid = int(chat_id)
    rows = []
    try:
        source = reminder_items_global_for_completion(include_completed=True)
    except Exception:
        source = []
    for rid, cfg in source:
        try:
            if cid in _v149_reminder_chat_ids(cfg):
                rows.append((int(rid), cfg))
        except Exception:
            pass
    rows.sort(key=lambda x: x[0])
    return rows

# --- reminders:0180 · from 08_reliability_tasks.py:18721 · public _v221_reminders_for_completion ---
def _v221_reminders_for_completion(chat_id: int) -> list[tuple[int, dict]]:
    cid = int(chat_id)
    out = []
    for rid, cfg in reminder_items_global_for_completion(include_completed=False):
        try:
            if cid in _v149_reminder_chat_ids(cfg) and cfg.get('enabled') and (_v218_completion_mode(cfg, cid) == 'slash'):
                out.append((int(rid), cfg))
        except Exception:
            pass
    out.sort(key=lambda x: x[0])
    return out

# --- reminders:0181 · from 08_reliability_tasks.py:18769 · public _v221_complete_reminder ---
def _v221_complete_reminder(reminder_id: int, chat_id: int, actor_user_id: int, actor_label: str) -> tuple[bool, str]:
    rid = int(reminder_id)
    cid = int(chat_id)
    cfg_before = reminder_cfg_global_for_completion(rid)
    recipients = list(_v149_reminder_chat_ids(cfg_before)) if isinstance(cfg_before, dict) else []
    ok, answer = _V221_PREV_COMPLETE_REMINDER(rid, cid, int(actor_user_id or 0), str(actor_label or ''))
    if ok:
        try:
            REMINDER_TASK_POOL.submit_unique(f'reminder-v221-complete-reconcile:{rid}', _v220_reconcile_completed_reminder_groups, rid, list(recipients))
        except Exception:
            try:
                _v220_reconcile_completed_reminder_groups(rid, list(recipients))
            except Exception:
                pass
        try:
            bot_journal('reminder_global_reconcile_v221', cid, f'reminder_id={rid}; recipients={sorted(set(recipients))}')
        except Exception:
            pass
    return (ok, answer)

# --- reminders:0182 · from 08_reliability_tasks.py:18826 · public _v221_find_reply_reminder ---
def _v221_find_reply_reminder(chat_id: int, reply_message_id: int) -> tuple[int | None, str]:
    cid = int(chat_id)
    mid = int(reply_message_id or 0)
    candidates = []
    for rid, cfg in _v221_chat_reminder_rows(cid):
        if _reminder_is_completed(cfg) or not cfg.get('enabled'):
            continue
        try:
            if int((cfg.get('last_message_ids') or {}).get(str(cid)) or 0) == mid:
                candidates.append(int(rid))
        except Exception:
            pass
    try:
        state = _v149_group_state_root().get(_v149_group_key(cid), {}) or {}
        if int(state.get('last_message_id') or 0) == mid:
            for raw in state.get('member_ids') or []:
                try:
                    rid = int(raw)
                    cfg = reminder_cfg_global_for_completion(rid)
                    if rid not in candidates and cfg and (cid in _v149_reminder_chat_ids(cfg)) and (not _reminder_is_completed(cfg)) and cfg.get('enabled'):
                        candidates.append(rid)
                except Exception:
                    pass
    except Exception:
        pass
    if len(candidates) == 1:
        return (candidates[0], 'ok')
    if len(candidates) > 1:
        return (None, 'В этом сообщении несколько напоминалок. Укажите /выполнено #N.')
    return (None, 'Ответьте именно на сообщение нужной напоминалки или укажите /выполнено #N.')

# v266
