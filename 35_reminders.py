# v262
_REMINDER_THREAD_STARTED = False
_REMINDER_THREAD_LOCK = threading.RLock()
_REMINDER_CONFIG_LOCK = threading.RLock()
_REMINDER_CHECK_SECONDS = 15.0
_REMINDER_LIST_PAGE_SIZE = 8
_REMINDER_UI_BINDINGS = {}
_REMINDER_COMPLETED_DELETE_SELECTION = defaultdict(set)
_REMINDER_COMPLETED_PAGE_SIZE = 10
_REMINDER_MONTHS_RU = ['Январь', 'Февраль', 'Март', 'Апрель', 'Май', 'Июнь', 'Июль', 'Август', 'Сентябрь', 'Октябрь', 'Ноябрь', 'Декабрь']
_REMINDER_GROUP_INTERVAL_MINUTES = 120
_REMINDER_GROUP_LOCK = threading.RLock()
_REMINDER_FINANCE_BUSY_SINCE = 0.0
_REMINDER_FINANCE_PRIORITY_GRACE_SECONDS = 60.0

def _v177_legacy_0117_reminder_ui_mode() -> str:
    mode = str(data.setdefault('_global_settings', {}).get('reminder_ui_mode_v142') or 'new').strip().lower()
    return mode if mode in {'old', 'new'} else 'new'
try:
    _v177_legacy_0117_reminder_ui_mode.__name__ = 'reminder_ui_mode'
except Exception:
    pass

def reminder_ui_new_enabled() -> bool:
    return reminder_ui_mode() == 'new'

def _v177_legacy_0118_set_reminder_ui_mode(mode: str) -> str:
    mode = 'new' if str(mode).strip().lower() == 'new' else 'old'
    data.setdefault('_global_settings', {})['reminder_ui_mode_v142'] = mode
    try:
        _reminder_save('reminder_ui_mode')
    except Exception:
        save_data(data, root_only=True)
    return mode
try:
    _v177_legacy_0118_set_reminder_ui_mode.__name__ = 'set_reminder_ui_mode'
except Exception:
    pass

def toggle_reminder_ui_mode() -> str:
    return set_reminder_ui_mode('old' if reminder_ui_new_enabled() else 'new')

def reminder_ui_mode_label() -> str:
    return '⏰ Напоминалка: ПО-НОВОМУ' if reminder_ui_new_enabled() else '⏰ Напоминалка: ПО-СТАРОМУ'

def _reminder_owner_id() -> int | None:
    try:
        return int(OWNER_ID) if OWNER_ID else None
    except Exception:
        return None

def _new_reminder_cfg() -> dict:
    return {'enabled': False, 'text': '', 'chat_ids': [], 'interval_minutes': 120, 'start_hour': 8, 'end_hour': 22, 'start_date': today_key(), 'end_date': '', 'next_run_at': '', 'last_sent_at': '', 'last_message_ids': {}, 'created_at': now_local().isoformat(timespec='seconds'), 'updated_at': now_local().isoformat(timespec='seconds'), 'completed_at': '', 'completion_reason': '', 'merge_mode_v207': None, 'show_complete_button_v207': None, 'completion_mode_v218': None, 'lifecycle_generation_v245': 1, 'delivery_cycle_v245': '', 'delivery_acked_chats_v245': []}

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
try:
    _v177_legacy_0119_reminder_items.__name__ = '_reminder_items'
except Exception:
    pass

def _reminder_completed_items() -> list[tuple[int, dict]]:
    rows = []
    for rid, cfg in _reminder_items(include_completed=True):
        if str(cfg.get('completed_at') or '').strip():
            rows.append((rid, cfg))
    rows.sort(key=lambda x: (str(x[1].get('completed_at') or ''), x[0]), reverse=True)
    return rows

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
try:
    _v177_legacy_0120_reminder_cfg.__name__ = '_reminder_cfg'
except Exception:
    pass

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
try:
    _v177_legacy_0121_reminder_create.__name__ = '_reminder_create'
except Exception:
    pass

def _reminder_position(reminder_id: int) -> int:
    ids = [rid for rid, _cfg in _reminder_items()]
    try:
        return ids.index(int(reminder_id)) + 1
    except Exception:
        return 0

def _reminder_is_completed(cfg: dict | None) -> bool:
    return bool(str((cfg or {}).get('completed_at') or '').strip())

def _reminder_return_callback(page: int, day_key: str) -> str:
    if str(day_key) == 'completed':
        return f'rem:completed:{max(0, int(page))}'
    return f'rem:list:{max(0, int(page))}:{day_key}'

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
try:
    _v177_legacy_0122_reminder_mark_completed.__name__ = '_reminder_mark_completed'
except Exception:
    pass

def _reminder_end_has_passed(cfg: dict, now_dt=None) -> bool:
    now_dt = now_dt or now_local()
    end_date = _reminder_parse_date((cfg or {}).get('end_date'))
    if end_date and now_dt.date() > end_date:
        return True
    return False

def build_completed_reminders_text(page: int=0, delete_mode: bool=False) -> str:
    rows = _reminder_completed_items()
    pages = max(1, (len(rows) + _REMINDER_COMPLETED_PAGE_SIZE - 1) // _REMINDER_COMPLETED_PAGE_SIZE)
    page = max(0, min(int(page or 0), pages - 1))
    selected = _REMINDER_COMPLETED_DELETE_SELECTION.get(int(OWNER_ID or 0), set())
    return f'✅ ЗАВЕРШЁННЫЕ НАПОМИНАЛКИ\n\nВсего: {len(rows)}\nСтраница: {page + 1}/{pages}\n' + (f'Выбрано для удаления: {len(selected)}\n' if delete_mode else '') + '\nНажмите напоминалку для просмотра и редактирования.'

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

def _reminder_generation_v245(cfg: dict | None) -> int:
    try:
        return max(1, int((cfg or {}).get('lifecycle_generation_v245') or 1))
    except Exception:
        return 1

def _reminder_touch(cfg: dict) -> None:
    cfg['lifecycle_generation_v245'] = _reminder_generation_v245(cfg) + 1
    cfg.pop('delivery_cycle_v245', None)
    cfg.pop('delivery_acked_chats_v245', None)
    cfg['delivery_cycle_v245'] = ''
    cfg['delivery_acked_chats_v245'] = []
    cfg['updated_at'] = now_local().isoformat(timespec='seconds')

def _reminder_parse_date(value: str):
    try:
        return datetime.strptime(str(value or ''), '%Y-%m-%d').date()
    except Exception:
        return None

def _reminder_parse_dt(value: str):
    try:
        dt = datetime.fromisoformat(str(value or ''))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=now_local().tzinfo)
        return dt
    except Exception:
        return None

def _reminder_fmt_date(value: str) -> str:
    d = _reminder_parse_date(value)
    return d.strftime('%d.%m.%Y') if d else '—'

def _reminder_fmt_dt(value: str) -> str:
    dt = _reminder_parse_dt(value)
    return dt.strftime('%d.%m %H:%M') if dt else '—'

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

def _reminder_date_allowed(now_dt: datetime, cfg: dict) -> bool:
    today = now_dt.date()
    start = _reminder_parse_date(cfg.get('start_date'))
    end = _reminder_parse_date(cfg.get('end_date'))
    if start and today < start:
        return False
    if end and today > end:
        return False
    return True

def _reminder_time_allowed(now_dt: datetime, cfg: dict) -> bool:
    _reminder_normalize_hours(cfg)
    return int(cfg['start_hour']) <= now_dt.hour <= int(cfg['end_hour'])

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

def _reminder_clear_completion_v243(cfg: dict) -> None:
    cfg['completed_at'] = ''
    cfg['completion_reason'] = ''
    for key in ('completed_by_user_id', 'completed_by_label', 'completed_in_chat_id', 'completion_event_id'):
        cfg.pop(key, None)

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

def _v177_legacy_0123_build_reminder_list_text() -> str:
    rows = _reminder_items()
    completed = _reminder_completed_items()
    enabled = sum((1 for _rid, cfg in rows if bool(cfg.get('enabled'))))
    return f'⏰ НАПОМИНАЛКИ\n\nТекущих: {len(rows)}\nАктивных: {enabled}\nЗавершённых: {len(completed)}\n\nНажмите напоминалку для просмотра и настройки.'
try:
    _v177_legacy_0123_build_reminder_list_text.__name__ = 'build_reminder_list_text'
except Exception:
    pass

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
try:
    _v177_legacy_0125_build_reminder_list_keyboard.__name__ = 'build_reminder_list_keyboard'
except Exception:
    pass

def _reminder_bind_editor(reminder_id: int, chat_id: int, message_id: int, day_key: str, page: int=0) -> None:
    _REMINDER_UI_BINDINGS[int(reminder_id)] = {'chat_id': int(chat_id), 'message_id': int(message_id), 'day_key': str(day_key), 'page': int(page), 'ts': time.time()}

def _reminder_unbind(reminder_id: int) -> None:
    _REMINDER_UI_BINDINGS.pop(int(reminder_id), None)

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
try:
    _v177_legacy_0127_build_reminder_menu_text.__name__ = 'build_reminder_menu_text'
except Exception:
    pass

def _reminder_insert_query(token: str, current_text: str='') -> str:
    service = f'({token} служебное — можно не трогать)'
    max_payload = max(0, 252 - len(service) - 2)
    current = str(current_text or '')
    if len(current) > max_payload:
        current = current[:max_payload]
    return service + '\n\n' + current

def compose_reminder_text_insert_value(reminder_id: int, current_text: str='') -> str:
    return _reminder_insert_query(f'EDITREM|{int(reminder_id)}|', current_text)

def compose_reminder_interval_insert_value(reminder_id: int, cfg: dict) -> str:
    return _reminder_insert_query(f'EDITREMINT|{int(reminder_id)}|', _reminder_interval_label(cfg.get('interval_minutes', 120)))

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
try:
    _v177_legacy_0129_build_reminder_menu_keyboard.__name__ = 'build_reminder_menu_keyboard'
except Exception:
    pass

def _reminder_edit_menu_keyboard(reminder_id: int, page: int, day_key: str, viewer_chat_id: int):
    cfg = _reminder_cfg(reminder_id) or {}
    kb = types.InlineKeyboardMarkup(row_width=1)
    kb.row(make_copy_or_inline_button('✍️ Вставить текст', compose_reminder_text_insert_value(reminder_id, cfg.get('text') or ''), viewer_chat_id=viewer_chat_id))
    kb.row(IB('🗑 Удалить', callback_data=f'rem:delete_confirm:{reminder_id}:{page}:{day_key}'))
    kb.row(IB('⬅️ Назад', callback_data=f'rem:open:{reminder_id}:{page}:{day_key}'), IB('✖️ Отмена', callback_data=f'rem:open:{reminder_id}:{page}:{day_key}'))
    return kb

def _reminder_dates_text(reminder_id: int) -> str:
    cfg = _reminder_cfg(reminder_id) or {}
    end = _reminder_fmt_date(cfg.get('end_date')) if cfg.get('end_date') else 'без конца'
    return f"📅 ДАТЫ НАПОМИНАЛКИ\n\nНачало: {_reminder_fmt_date(cfg.get('start_date'))}\nКонец: {end}"

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

def _reminder_calendar_text(which: str, year: int, month: int) -> str:
    target = 'начала' if which == 'start' else 'окончания'
    return f'📅 Выберите дату {target}\n\n{_REMINDER_MONTHS_RU[month - 1]} {year}'

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

def _v177_legacy_0131_reminder_delete_message_map(last_map: dict) -> None:
    for cid_raw, mid_raw in list((last_map or {}).items()):
        try:
            bot.delete_message(int(cid_raw), int(mid_raw))
        except Exception:
            pass
try:
    _v177_legacy_0131_reminder_delete_message_map.__name__ = '_reminder_delete_message_map'
except Exception:
    pass

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

def _reminder_due_now(cfg: dict, now_dt=None) -> bool:
    if not bool((cfg or {}).get('enabled')):
        return False
    if not str((cfg or {}).get('text') or '').strip() or not ((cfg or {}).get('chat_ids') or []):
        return False
    now_dt = now_dt or now_local()
    due = _reminder_parse_dt((cfg or {}).get('next_run_at'))
    return due is None or now_dt >= due

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
try:
    _v177_legacy_0132_reminder_tick.__name__ = '_reminder_tick'
except Exception:
    pass

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

@bot.message_handler(func=_reminder_direct_input_predicate, content_types=['text'])
def reminder_direct_input_message(msg):
    chat_id = int(msg.chat.id)
    text = str(msg.text or '')
    if 'EDITREMINT|' in text:
        rid, value = _reminder_extract_insert(text, 'EDITREMINT')
        cfg = _reminder_cfg(rid) if rid is not None else None
        if not cfg:
            send_and_auto_delete(chat_id, '❌ Напоминалка не найдена.', 8)
            return
        minutes = _reminder_parse_custom_interval(value)
        if minutes is None:
            send_and_auto_delete(chat_id, '❌ Пример: 90 мин, 2 ч, 1 день. Минимум 5 минут.', 10)
            return
        _durable_note_source_consumed('reminder_interval_insert')
        cfg['interval_minutes'] = int(minutes)
        _durable_note_reminder_edit_witness({'reminder_id': int(rid), 'kind': 'interval', 'interval_minutes': int(minutes)})
        if cfg.get('enabled'):
            _reminder_rearm_after_interval_v243(cfg, preserve_future=False)
        _reminder_touch(cfg)
        _reminder_save('reminder_interval_insert')
        try:
            bot.delete_message(chat_id, msg.message_id)
        except Exception:
            pass
        _reminder_refresh_bound_editor(rid)
        return
    rid, value = _reminder_extract_insert(text, 'EDITREM')
    cfg = _reminder_cfg(rid) if rid is not None else None
    if not cfg:
        send_and_auto_delete(chat_id, '❌ Напоминалка не найдена.', 8)
        return
    if not value:
        send_and_auto_delete(chat_id, '❌ Текст пустой.', 8)
        return
    if len(value) > 4000:
        send_and_auto_delete(chat_id, '❌ Текст слишком длинный. Максимум 4000 символов.', 10)
        return
    _durable_note_source_consumed('reminder_text_insert')
    cfg['text'] = value
    _durable_note_reminder_edit_witness({'reminder_id': int(rid), 'kind': 'text', 'text': str(value)})
    if cfg.get('enabled'):
        _reminder_rearm_after_interval_v243(cfg, preserve_future=True)
    _reminder_touch(cfg)
    _reminder_save('reminder_text_insert')
    try:
        bot.delete_message(chat_id, msg.message_id)
    except Exception:
        pass
    _reminder_refresh_bound_editor(rid)

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
_BUILD_REMINDER_LIST_TEXT_V141 = _v177_legacy_0123_build_reminder_list_text
_BUILD_REMINDER_LIST_KEYBOARD_V141 = _v177_legacy_0125_build_reminder_list_keyboard
_BUILD_REMINDER_MENU_TEXT_V141 = _v177_legacy_0127_build_reminder_menu_text
_BUILD_REMINDER_MENU_KEYBOARD_V141 = _v177_legacy_0129_build_reminder_menu_keyboard

def _reminder_date_allowed_for_day(cfg: dict, day_key: str) -> bool:
    try:
        d = datetime.strptime(str(day_key), '%Y-%m-%d').date()
    except Exception:
        d = now_local().date()
    start = _reminder_parse_date((cfg or {}).get('start_date'))
    end = _reminder_parse_date((cfg or {}).get('end_date'))
    return not (start and d < start or (end and d > end))

def _reminder_single_chat_id(cfg: dict) -> int | None:
    ids = []
    for raw in (cfg or {}).get('chat_ids') or []:
        try:
            ids.append(int(raw))
        except Exception:
            pass
    ids = list(dict.fromkeys(ids))
    return ids[0] if len(ids) == 1 else None

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

def _v177_legacy_0124_build_reminder_list_text() -> str:
    if not reminder_ui_new_enabled():
        return _BUILD_REMINDER_LIST_TEXT_V141()
    rows = _reminder_items()
    groups = _reminder_group_map(today_key(), enabled_only=False)
    enabled = sum((1 for _rid, cfg in rows if bool(cfg.get('enabled'))))
    return f'⏰ НАПОМИНАЛКИ · ПРОСТОЙ РЕЖИМ\n\nТекущих: {len(rows)} · активных: {enabled}\nОбъединённых чатов: {len(groups)}\nЗавершённых: {len(_reminder_completed_items())}\n\nНастройка идёт по шагам: текст → чаты → период → расписание → проверка.\nЕсли в одном чате несколько напоминалок, бот объединяет их в одно сообщение каждые 2 часа.'
try:
    _v177_legacy_0124_build_reminder_list_text.__name__ = 'build_reminder_list_text'
except Exception:
    pass

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
try:
    _v177_legacy_0126_build_reminder_list_keyboard.__name__ = 'build_reminder_list_keyboard'
except Exception:
    pass

def _reminder_step_state(cfg: dict) -> list[str]:
    return ['✅' if str(cfg.get('text') or '').strip() else '❌', '✅' if cfg.get('chat_ids') or [] else '❌', '✅' if int(cfg.get('interval_minutes', 0) or 0) >= 5 else '❌', '✅' if str(cfg.get('start_date') or '').strip() else '❌']

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
try:
    _v177_legacy_0128_build_reminder_menu_text.__name__ = 'build_reminder_menu_text'
except Exception:
    pass

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
try:
    _v177_legacy_0130_build_reminder_menu_keyboard.__name__ = 'build_reminder_menu_keyboard'
except Exception:
    pass

def reminder_schedule_text(reminder_id: int) -> str:
    cfg = _reminder_cfg(reminder_id) or {}
    end = _reminder_fmt_date(cfg.get('end_date')) if cfg.get('end_date') else 'без конца'
    return f"4️⃣ РАСПИСАНИЕ\n\nДаты: {_reminder_fmt_date(cfg.get('start_date'))} → {end}\nВремя: {int(cfg.get('start_hour', 8)):02d}:00 → {int(cfg.get('end_hour', 22)):02d}:59"

def reminder_schedule_keyboard(reminder_id: int, page: int, day_key: str):
    cfg = _reminder_cfg(reminder_id) or {}
    kb = types.InlineKeyboardMarkup(row_width=2)
    kb.row(IB('📅 Даты', callback_data=f'rem:dates:{reminder_id}:{page}:{day_key}'))
    kb.row(IB(f"🕗 С {int(cfg.get('start_hour', 8)):02d}:00", callback_data=f'rem:hours:start:{reminder_id}:{page}:{day_key}'), IB(f"🕙 До {int(cfg.get('end_hour', 22)):02d}:59", callback_data=f'rem:hours:end:{reminder_id}:{page}:{day_key}'))
    kb.row(IB('⬅️ Назад', callback_data=f'rem:open:{reminder_id}:{page}:{day_key}'))
    return kb

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

def reminder_preview_keyboard(reminder_id: int, page: int, day_key: str, viewer_chat_id: int):
    cfg = _reminder_cfg(reminder_id) or {}
    kb = types.InlineKeyboardMarkup(row_width=1)
    valid = bool(str(cfg.get('text') or '').strip() and (cfg.get('chat_ids') or []))
    if valid:
        label = '✅ ВКЛ' if cfg.get('enabled') else '⬜ ВЫКЛ'
        kb.row(IB(label, callback_data=f'rem:toggle:{reminder_id}:{page}:{day_key}'))
    kb.row(IB('⬅️ Назад', callback_data=f'rem:open:{reminder_id}:{page}:{day_key}'))
    return kb

def _reminder_group_state_root() -> dict:
    return data.setdefault('_global_settings', {}).setdefault('reminder_groups_v142', {})

def _reminder_group_key(target_chat_id: int, day_key: str) -> str:
    return f'{str(day_key)}:{int(target_chat_id)}'

def reminder_group_text(target_chat_id: int, day_key: str) -> str:
    members = reminder_group_members(target_chat_id, day_key, enabled_only=False)
    active = sum((1 for _rid, cfg in members if bool(cfg.get('enabled'))))
    lines = ['👥 ОБЪЕДИНЁННАЯ НАПОМИНАЛКА', '', f'Чат: {get_chat_display_name(int(target_chat_id))}', f'Напоминалок: {len(members)} · активных: {active}', 'Общий ритм при совместной работе: каждые 2 часа.', '']
    for idx, (_rid, cfg) in enumerate(members, 1):
        text = re.sub('\\s+', ' ', str(cfg.get('text') or 'без текста').strip())
        lines.append(f'{idx}. {text[:180]}')
    lines += ['', 'Можно открыть каждую отдельно или применить общие настройки ко всем.']
    return '\n'.join(lines)

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

def reminder_group_set_two_hours(target_chat_id: int, day_key: str) -> None:
    with _REMINDER_CONFIG_LOCK:
        for _rid, cfg in reminder_group_members(target_chat_id, day_key, enabled_only=False):
            cfg['interval_minutes'] = _REMINDER_GROUP_INTERVAL_MINUTES
            if cfg.get('enabled'):
                _reminder_rearm_after_interval_v243(cfg, preserve_future=False)
            _reminder_touch(cfg)
    _reminder_save('reminder_group_2h')

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

def _reminder_group_next_time(now_dt: datetime, members: list[tuple[int, dict]]):
    candidate = now_dt + timedelta(minutes=_REMINDER_GROUP_INTERVAL_MINUTES)
    for _ in range(16):
        if any((_reminder_date_allowed(candidate, cfg) and _reminder_time_allowed(candidate, cfg) for _rid, cfg in members)):
            return candidate
        next_day = candidate.date() + timedelta(days=1)
        start_hour = min((int(cfg.get('start_hour', 8)) for _rid, cfg in members))
        candidate = datetime.combine(next_day, datetime.min.time(), tzinfo=now_dt.tzinfo).replace(hour=start_hour)
    return None

def _v177_legacy_0134_reminder_group_delete_message(target_chat_id: int, message_id: int) -> None:
    if not message_id:
        return
    try:
        bot.delete_message(int(target_chat_id), int(message_id))
    except Exception:
        pass
try:
    _v177_legacy_0134_reminder_group_delete_message.__name__ = '_reminder_group_delete_message'
except Exception:
    pass

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
try:
    _v177_legacy_0135_reminder_group_send_job.__name__ = '_reminder_group_send_job'
except Exception:
    pass

def _reminder_finance_priority_busy() -> bool:
    try:
        for pool in (FINANCE_TASK_POOL, FIN_FORWARD_TASK_POOL):
            st = pool.stats()
            if int(st.get('pending', 0) or 0) > 0 or int(st.get('active', 0) or 0) > 0:
                return True
    except Exception:
        pass
    return False

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
try:
    _v177_legacy_0133_reminder_tick.__name__ = '_reminder_tick'
except Exception:
    pass
# v262
