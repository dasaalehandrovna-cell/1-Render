# v262
"""v172: Telegram-native task / purchase dispatcher.

Loaded last on top of v171.  Task state lives in compact root maps so each task is
persisted as an incremental MEGA root-map delta instead of serializing the whole task
registry inside every chat delta.
"""
import re as _v172_re
import secrets as _v172_secrets
import threading as _v172_threading
import time as _v172_time
from datetime import datetime as _v172_datetime, timedelta as _v172_timedelta
V172_FILE_MARKER = 'v172_task_dispatcher'
V172_TASKS_KEY = '_tasks_v172'
V172_TASK_SETTINGS_KEY = '_task_settings_v172'
V172_TASK_SOURCE_INDEX_KEY = '_task_source_index_v172'
V172_TASK_SCHEMA = 1
V172_TASK_PAGE_SIZE = 7
V172_HISTORY_KEEP = 100
V172_COMMENT_KEEP = 100
try:
    _DELTA_ROOT_MAP_KEYS.update({V172_TASKS_KEY, V172_TASK_SETTINGS_KEY, V172_TASK_SOURCE_INDEX_KEY})
except Exception:
    pass
try:
    data.setdefault(V172_TASKS_KEY, {})
    data.setdefault(V172_TASK_SETTINGS_KEY, {})
    data.setdefault(V172_TASK_SOURCE_INDEX_KEY, {})
except Exception:
    pass
try:
    WINDOW_MARKER_CONSTANTS.update({'v172:task:admin': 'Ф242', 'v172:task:list': 'Ф243', 'v172:task:card': 'Ф244', 'v172:task:history': 'Ф245', 'v172:task:groups': 'Ф246'})
except Exception:
    pass
_TASK_STATUS = {'new': ('🆕', 'Новая'), 'work': ('🔧', 'В работе'), 'wait': ('🟣', 'Ждёт'), 'deferred': ('⏸', 'Отложена'), 'done': ('✅', 'Выполнена')}
_PURCHASE_STATUS = {'need': ('🛒', 'Нужно купить'), 'search': ('🔎', 'Ищем'), 'ordered': ('📦', 'Заказано'), 'bought': ('💰', 'Куплено'), 'received': ('✅', 'Получено')}
_PRIORITY = {'normal': ('🟢', 'Обычная'), 'important': ('🟠', 'Важная'), 'urgent': ('🔴', 'Срочная')}
_V172_INPUT_LOCK = _v172_threading.RLock()
_V172_INPUT_WAIT = {}
_V172_SEARCH_CACHE = {}

def _v172_now():
    try:
        return now_local()
    except Exception:
        return _v172_datetime.now()

def _v172_iso():
    return _v172_now().isoformat(timespec='seconds')

def _v172_mark(text: str, marker: str) -> str:
    try:
        return window_mark(str(text), str(marker))
    except Exception:
        return str(text).rstrip() + f'\n\n{marker}'

def _v172_user_name(user) -> str:
    if user is None:
        return 'неизвестно'
    username = str(getattr(user, 'username', '') or '').strip().lstrip('@')
    if username:
        return '@' + username
    first = str(getattr(user, 'first_name', '') or '').strip()
    last = str(getattr(user, 'last_name', '') or '').strip()
    full = (first + ' ' + last).strip()
    if full:
        return full
    uid = int(getattr(user, 'id', 0) or 0)
    return f'user:{uid}' if uid else 'неизвестно'

def _v172_is_manager(user_id: int, chat_id: int) -> bool:
    try:
        uid = int(user_id or 0)
        if uid and uid == int(OWNER_ID or 0):
            return True
        try:
            if uid in {int(x) for x in get_additional_owner_ids()}:
                return True
        except Exception:
            pass
        fn = globals().get('tenant_can_manage')
        if callable(fn):
            for args, kwargs in (((uid,), {'chat_id': int(chat_id)}), ((uid, int(chat_id)), {})):
                try:
                    if fn(*args, **kwargs):
                        return True
                except Exception:
                    continue
    except Exception:
        pass
    return False

def _v172_tasks_root() -> dict:
    return data.setdefault(V172_TASKS_KEY, {})

def _v172_settings_root() -> dict:
    return data.setdefault(V172_TASK_SETTINGS_KEY, {})

def _v172_source_root() -> dict:
    return data.setdefault(V172_TASK_SOURCE_INDEX_KEY, {})

def _v172_chat_settings(chat_id: int) -> dict:
    root = _v172_settings_root()
    key = str(int(chat_id))
    row = root.setdefault(key, {})
    row.setdefault('enabled', False)
    row.setdefault('next_number', 1)
    return row

def task_dispatcher_enabled(chat_id: int) -> bool:
    try:
        return bool(_v172_chat_settings(int(chat_id)).get('enabled', False))
    except Exception:
        return False

def _v172_persist(chat_id: int, reason: str='task_change') -> None:
    """Persist root state locally immediately and schedule compact MEGA delta."""
    try:
        with data_lock:
            SQLITE.save_root(_sqlite_pack_root(data))
    except Exception as exc:
        try:
            log_error(f'v172 task SQLite root save: {exc}')
        except Exception:
            pass
    try:
        schedule_delta_backup(int(chat_id), delay=0.12, reason=f'v172:{reason}')
    except Exception:
        try:
            _mark_global_snapshot_pending()
        except Exception:
            pass

def _v172_source_key(chat_id: int, message_id: int) -> str:
    return f'{int(chat_id)}:{int(message_id)}'

def _v172_new_uid() -> str:
    root = _v172_tasks_root()
    for _ in range(20):
        uid = _v172_secrets.token_hex(5).upper()
        if uid not in root:
            return uid
    return _v172_secrets.token_hex(8).upper()

def _v172_task_for_uid(uid: str):
    row = _v172_tasks_root().get(str(uid or '').upper())
    return row if isinstance(row, dict) else None

def _v172_tasks_for_chat(chat_id: int, include_deleted: bool=False) -> list[dict]:
    cid = int(chat_id)
    out = []
    for row in _v172_tasks_root().values():
        if not isinstance(row, dict) or int(row.get('chat_id', 0) or 0) != cid:
            continue
        if not include_deleted and bool(row.get('deleted', False)):
            continue
        out.append(row)
    return out

def _v172_status_map(task: dict):
    return _PURCHASE_STATUS if str(task.get('type')) == 'purchase' else _TASK_STATUS

def _v177_legacy_0327_v172_is_complete(task: dict) -> bool:
    return str(task.get('status')) in ({'received'} if str(task.get('type')) == 'purchase' else {'done'})
try:
    _v177_legacy_0327_v172_is_complete.__name__ = '_v172_is_complete'
except Exception:
    pass

def _v172_deadline_dt(task: dict):
    raw = str(task.get('deadline') or '').strip()
    if not raw:
        return None
    try:
        return _v172_datetime.fromisoformat(raw)
    except Exception:
        return None

def _v172_overdue(task: dict) -> bool:
    dt = _v172_deadline_dt(task)
    if not dt or _v172_is_complete(task):
        return False
    try:
        return dt < _v172_now().replace(tzinfo=dt.tzinfo) if dt.tzinfo else dt < _v172_now().replace(tzinfo=None)
    except Exception:
        return False

def _v172_title(text: str) -> str:
    raw = ' '.join(str(text or '').strip().split())
    return raw[:110] if raw else 'Без названия'

def _v172_history(task: dict, action: str, user_id: int=0, user_name: str='', detail: str='') -> None:
    rows = task.setdefault('history', [])
    rows.append({'at': _v172_iso(), 'action': str(action), 'user_id': int(user_id or 0), 'user': str(user_name or ''), 'detail': str(detail or '')[:600]})
    if len(rows) > V172_HISTORY_KEEP:
        del rows[:-V172_HISTORY_KEEP]

def _v172_create_task(chat_id: int, kind: str, text: str, creator, source_msg=None) -> dict:
    cid = int(chat_id)
    kind = 'purchase' if str(kind) == 'purchase' else 'task'
    settings = _v172_chat_settings(cid)
    num = max(1, int(settings.get('next_number', 1) or 1))
    settings['next_number'] = num + 1
    uid = _v172_new_uid()
    source_id = int(getattr(source_msg, 'message_id', 0) or 0) if source_msg is not None else 0
    source_user = getattr(source_msg, 'from_user', None) if source_msg is not None else None
    source_username = ''
    try:
        source_username = str(getattr(getattr(source_msg, 'chat', None), 'username', '') or '').lstrip('@')
    except Exception:
        pass
    creator_id = int(getattr(creator, 'id', 0) or 0)
    creator_name = _v172_user_name(creator)
    row = {'schema': V172_TASK_SCHEMA, 'uid': uid, 'number': num, 'chat_id': cid, 'type': kind, 'title': _v172_title(text), 'description': str(text or '').strip()[:4000], 'object': '', 'creator_user_id': creator_id, 'creator_name': creator_name, 'source_author_id': int(getattr(source_user, 'id', 0) or 0), 'source_author_name': _v172_user_name(source_user) if source_user else '', 'source_message_id': source_id, 'source_chat_username': source_username, 'assignees': [], 'status': 'need' if kind == 'purchase' else 'new', 'priority': 'normal', 'deadline': '', 'cost': '', 'comments': [], 'history': [], 'created_at': _v172_iso(), 'updated_at': _v172_iso(), 'completed_at': '', 'deleted': False}
    _v172_history(row, 'created', creator_id, creator_name, 'Покупка' if kind == 'purchase' else 'Задача')
    _v172_tasks_root()[uid] = row
    if source_id:
        _v172_source_root()[_v172_source_key(cid, source_id)] = uid
    _v172_persist(cid, 'task_create')
    try:
        bot_journal('task_v172_created', cid, f'uid={uid} num={num} type={kind} source={source_id}')
    except Exception:
        pass
    return row

def _v172_touch(task: dict, user=None, action: str='updated', detail: str='') -> None:
    uid = int(getattr(user, 'id', 0) or 0) if user is not None else 0
    name = _v172_user_name(user) if user is not None else 'system'
    task['updated_at'] = _v172_iso()
    task['updated_by'] = uid
    _v172_history(task, action, uid, name, detail)
    if _v172_is_complete(task):
        task['completed_at'] = task.get('completed_at') or _v172_iso()
    else:
        task['completed_at'] = ''
    _v172_persist(int(task.get('chat_id', 0) or 0), action)

def _v172_source_url(task: dict) -> str:
    mid = int(task.get('source_message_id', 0) or 0)
    if not mid:
        return ''
    username = str(task.get('source_chat_username') or '').strip().lstrip('@')
    if username:
        return f'https://t.me/{username}/{mid}'
    cid = str(int(task.get('chat_id', 0) or 0))
    if cid.startswith('-100') and len(cid) > 4:
        return f'https://t.me/c/{cid[4:]}/{mid}'
    return ''

def _v172_assignee_text(task: dict) -> str:
    arr = task.get('assignees') or []
    names = [str(x.get('name') or x.get('user_id') or '') for x in arr if isinstance(x, dict)]
    return ', '.join([x for x in names if x]) or 'не назначен'

def _v172_deadline_text(task: dict) -> str:
    dt = _v172_deadline_dt(task)
    if not dt:
        return 'не указан'
    try:
        value = dt.strftime('%d.%m.%Y %H:%M')
    except Exception:
        value = str(task.get('deadline') or '')
    return ('⏰ ПРОСРОЧЕНО · ' if _v172_overdue(task) else '') + value

def _v172_status_text(task: dict) -> str:
    icon, label = _v172_status_map(task).get(str(task.get('status')), ('❔', str(task.get('status') or '—')))
    return f'{icon} {label}'

def _v172_priority_text(task: dict) -> str:
    icon, label = _PRIORITY.get(str(task.get('priority')), _PRIORITY['normal'])
    return f'{icon} {label}'

def _v172_card_text(task: dict) -> str:
    kind = '🛒 ПОКУПКА' if str(task.get('type')) == 'purchase' else '📋 ЗАДАЧА'
    lines = [f"{kind} №{int(task.get('number', 0) or 0)}", '', f"📝 {str(task.get('description') or task.get('title') or 'Без названия')[:1800]}", '', f"🏠 Объект: {str(task.get('object') or 'не указан')}", f"👤 Поставил: {str(task.get('creator_name') or task.get('creator_user_id') or '—')}", f'👷 Ответственный: {_v172_assignee_text(task)}', f'📅 Срок: {_v172_deadline_text(task)}', f'⚡ Приоритет: {_v172_priority_text(task)}', f'🔧 Статус: {_v172_status_text(task)}']
    if str(task.get('type')) == 'purchase':
        lines.append(f"💵 Стоимость/бюджет: {str(task.get('cost') or '—')}")
    if task.get('source_author_name'):
        lines.append(f"💬 Автор исходного сообщения: {task.get('source_author_name')}")
    if task.get('comments'):
        last = task.get('comments')[-1]
        lines += ['', f"💬 Последний комментарий: {str(last.get('text') or '')[:450]}"]
    lines += ['', f"UID: {task.get('uid')}"]
    return _v172_mark('\n'.join(lines), 'Ф244')

def _v172_standard_nav(kb, chat_id: int, back_cb: str='v172:task:list:active:0'):
    day = today_key()
    try:
        day = str(get_chat_store(int(chat_id)).get('current_view_day') or today_key())
    except Exception:
        pass
    kb.row(IB('🔙 Назад', callback_data=back_cb), IB('⬅️ Назад осн. окно', callback_data=f'd:{day}:back_main'))
    kb.row(IB('ℹ️ Описание', callback_data='v171:desc'), IB('❌ Закрыть', callback_data='info_close'))
    ann_fn = globals().get('annotation_effective_v229')
    show_m = True
    show_t = True
    if callable(ann_fn):
        try:
            show_m = bool(ann_fn('iz_mr', int(chat_id)))
        except Exception:
            pass
        try:
            show_t = bool(ann_fn('tz', int(chat_id)))
        except Exception:
            pass
    ann_buttons = []
    if show_m:
        ann_buttons.append(IB('/iz-mr', callback_data='v160:marker_capture'))
    if show_t:
        ann_buttons.append(IB('/tz', callback_data='v160:tz_capture'))
    if ann_buttons:
        kb.row(*ann_buttons)
    return kb

def _v172_card_keyboard(task: dict, viewer_chat_id: int, viewer_user_id: int):
    uid = str(task.get('uid'))
    kb = types.InlineKeyboardMarkup(row_width=2)
    status_map = _v172_status_map(task)
    buttons = []
    for code, (icon, label) in status_map.items():
        prefix = '✅ ' if str(task.get('status')) == code else ''
        buttons.append(IB(prefix + icon + ' ' + label, callback_data=f'v172:task:st:{uid}:{code}'))
    for i in range(0, len(buttons), 2):
        kb.row(*buttons[i:i + 2])
    kb.row(IB('⚡ Приоритет', callback_data=f'v172:task:prio:{uid}'), IB('📅 Срок', callback_data=f'v172:task:input:{uid}:deadline'))
    kb.row(IB('👤 Взять себе', callback_data=f'v172:task:take:{uid}'), IB('👥 Назначить', callback_data=f'v172:task:input:{uid}:assign'))
    kb.row(IB('🏠 Объект', callback_data=f'v172:task:input:{uid}:object'), IB('✏️ Текст', callback_data=f'v172:task:input:{uid}:text'))
    if str(task.get('type')) == 'purchase':
        kb.row(IB('💰 Стоимость', callback_data=f'v172:task:input:{uid}:cost'))
    kb.row(IB('💬 Комментарий', callback_data=f'v172:task:input:{uid}:comment'), IB('🕘 История', callback_data=f'v172:task:hist:{uid}'))
    url = _v172_source_url(task)
    if url:
        kb.row(IB('💬 Исходное сообщение', url=url))
    elif int(task.get('source_message_id', 0) or 0):
        kb.row(IB('💬 Исходное сообщение', callback_data=f'v172:task:source:{uid}'))
    if _v172_is_manager(viewer_user_id, int(task.get('chat_id', 0) or 0)) or int(viewer_user_id or 0) == int(task.get('creator_user_id', 0) or 0):
        kb.row(IB('🗑 Удалить', callback_data=f'v172:task:del:{uid}'))
    return _v172_standard_nav(kb, viewer_chat_id, 'v172:task:list:active:0')

def _v172_filter_task(task: dict, filt: str, user_id: int=0) -> bool:
    if bool(task.get('deleted', False)):
        return False
    f = str(filt or 'active')
    if f == 'active':
        return not _v172_is_complete(task) and str(task.get('status')) != 'deferred'
    if f == 'all':
        return not _v172_is_complete(task)
    if f == 'work':
        return str(task.get('status')) in {'work', 'search', 'ordered', 'bought'}
    if f == 'wait':
        return str(task.get('status')) == 'wait'
    if f == 'deferred':
        return str(task.get('status')) == 'deferred'
    if f == 'urgent':
        return str(task.get('priority')) == 'urgent' and (not _v172_is_complete(task))
    if f == 'overdue':
        return _v172_overdue(task)
    if f == 'purchase':
        return str(task.get('type')) == 'purchase' and (not _v172_is_complete(task))
    if f == 'done':
        return _v172_is_complete(task)
    if f == 'mine':
        return any((int(x.get('user_id', 0) or 0) == int(user_id or 0) for x in task.get('assignees') or [] if isinstance(x, dict))) and (not _v172_is_complete(task))
    return True

def _v212_legacy__v172_sort_key(task: dict):
    complete = 1 if _v172_is_complete(task) else 0
    overdue = 0 if _v172_overdue(task) else 1
    pri = {'urgent': 0, 'important': 1, 'normal': 2}.get(str(task.get('priority')), 3)
    deadline = str(task.get('deadline') or '9999-99-99')
    return (complete, overdue, pri, deadline, -int(task.get('number', 0) or 0))

def _v172_list_title(filt: str) -> str:
    return {'active': 'Все активные', 'all': 'Невыполненные', 'work': 'В работе', 'wait': 'Ждут', 'deferred': 'Отложенные', 'urgent': 'Срочные', 'overdue': 'Просроченные', 'purchase': 'Покупки', 'done': 'Выполненные', 'mine': 'Мои задачи', 'search': 'Результаты поиска'}.get(str(filt), 'Задачи')

def _v172_list_rows(chat_id: int, filt: str, user_id: int=0):
    if str(filt) == 'search':
        key = (int(chat_id), int(user_id or 0))
        uids = list((_V172_SEARCH_CACHE.get(key) or {}).get('uids') or [])
        rows = [_v172_task_for_uid(uid) for uid in uids]
        return [x for x in rows if isinstance(x, dict) and (not x.get('deleted'))]
    rows = [x for x in _v172_tasks_for_chat(chat_id) if _v172_filter_task(x, filt, user_id)]
    rows.sort(key=_v172_sort_key)
    return rows

def _v172_dashboard_counts(chat_id: int) -> dict:
    rows = _v172_tasks_for_chat(chat_id)
    return {'active': sum((1 for x in rows if not _v172_is_complete(x) and str(x.get('status')) != 'deferred')), 'urgent': sum((1 for x in rows if str(x.get('priority')) == 'urgent' and (not _v172_is_complete(x)))), 'overdue': sum((1 for x in rows if _v172_overdue(x))), 'work': sum((1 for x in rows if str(x.get('status')) in {'work', 'search', 'ordered', 'bought'})), 'wait': sum((1 for x in rows if str(x.get('status')) == 'wait')), 'deferred': sum((1 for x in rows if str(x.get('status')) == 'deferred')), 'purchase': sum((1 for x in rows if str(x.get('type')) == 'purchase' and (not _v172_is_complete(x)))), 'done': sum((1 for x in rows if _v172_is_complete(x)))}

def _v172_list_text(chat_id: int, filt: str, page: int, user_id: int=0):
    rows = _v172_list_rows(chat_id, filt, user_id)
    total_pages = max(1, (len(rows) + V172_TASK_PAGE_SIZE - 1) // V172_TASK_PAGE_SIZE)
    page = max(0, min(int(page or 0), total_pages - 1))
    c = _v172_dashboard_counts(chat_id)
    lines = ['📋 ДИСПЕТЧЕР ЗАДАЧ', f'Чат: {get_chat_display_name(int(chat_id))}', '', f'Раздел: {_v172_list_title(filt)} · {len(rows)}', f"🔴 Срочные {c['urgent']} · ⏰ Просроченные {c['overdue']} · 🔧 В работе {c['work']} · 🛒 Купить {c['purchase']}", '']
    chunk = rows[page * V172_TASK_PAGE_SIZE:(page + 1) * V172_TASK_PAGE_SIZE]
    if not chunk:
        lines.append('Здесь пока нет задач.')
    else:
        for task in chunk:
            icon = '🛒' if str(task.get('type')) == 'purchase' else '📋'
            if _v172_overdue(task):
                icon = '⏰'
            elif str(task.get('priority')) == 'urgent':
                icon = '🔴'
            lines.append(f"{icon} #{task.get('number')} · {_v172_status_text(task)} · {str(task.get('title') or '')[:95]}")
    lines += ['', f'Страница {page + 1}/{total_pages}']
    return (_v172_mark('\n'.join(lines), 'Ф243'), rows, page, total_pages)

def _v172_list_keyboard(chat_id: int, filt: str, page: int, user_id: int=0):
    text, rows, page, total_pages = _v172_list_text(chat_id, filt, page, user_id)
    kb = types.InlineKeyboardMarkup(row_width=2)
    kb.row(IB('➕ Задача', callback_data='v172:task:new:task'), IB('🛒 Покупка', callback_data='v172:task:new:purchase'))
    kb.row(IB('📋 Активные', callback_data='v172:task:list:active:0'), IB('👤 Мои', callback_data='v172:task:list:mine:0'))
    kb.row(IB('🔴 Срочные', callback_data='v172:task:list:urgent:0'), IB('⏰ Просроченные', callback_data='v172:task:list:overdue:0'))
    kb.row(IB('🔧 В работе', callback_data='v172:task:list:work:0'), IB('🟣 Ждут', callback_data='v172:task:list:wait:0'))
    kb.row(IB('⏸ Отложенные', callback_data='v172:task:list:deferred:0'), IB('🛒 Покупки', callback_data='v172:task:list:purchase:0'))
    kb.row(IB('🏠 Объекты', callback_data='v172:task:groups:object:0'), IB('👥 Исполнители', callback_data='v172:task:groups:assignee:0'))
    kb.row(IB('✅ Выполненные', callback_data='v172:task:list:done:0'), IB('🔎 Поиск', callback_data='v172:task:search'))
    chunk = rows[page * V172_TASK_PAGE_SIZE:(page + 1) * V172_TASK_PAGE_SIZE]
    for task in chunk:
        icon = '⏰' if _v172_overdue(task) else '🔴' if str(task.get('priority')) == 'urgent' else '🛒' if str(task.get('type')) == 'purchase' else '📋'
        kb.row(IB(f"{icon} #{task.get('number')} {str(task.get('title') or '')[:38]}", callback_data=f"v172:task:open:{task.get('uid')}"))
    if total_pages > 1:
        prevp = (page - 1) % total_pages
        nextp = (page + 1) % total_pages
        kb.row(IB('◀️', callback_data=f'v172:task:list:{filt}:{prevp}'), IB(f'{page + 1}/{total_pages}', callback_data='none'), IB('▶️', callback_data=f'v172:task:list:{filt}:{nextp}'))
    return (text, _v172_standard_nav(kb, chat_id, f'v172:task:list:{filt}:{page}'))

def _v172_group_values(chat_id: int, kind: str):
    vals = {}
    for task in _v172_tasks_for_chat(chat_id):
        if _v172_is_complete(task):
            continue
        if kind == 'object':
            value = str(task.get('object') or '').strip()
            if value:
                vals[value] = vals.get(value, 0) + 1
        else:
            for a in task.get('assignees') or []:
                if isinstance(a, dict):
                    value = str(a.get('name') or a.get('user_id') or '').strip()
                    if value:
                        vals[value] = vals.get(value, 0) + 1
    return sorted(vals.items(), key=lambda x: (-x[1], x[0].casefold()))

def _v172_value_token(value: str) -> str:
    import hashlib
    return hashlib.sha1(str(value).encode('utf-8')).hexdigest()[:10]

def _v172_groups_text_kb(chat_id: int, kind: str, page: int):
    vals = _v172_group_values(chat_id, kind)
    per = 10
    pages = max(1, (len(vals) + per - 1) // per)
    page = max(0, min(int(page or 0), pages - 1))
    title = '🏠 ОБЪЕКТЫ' if kind == 'object' else '👥 ИСПОЛНИТЕЛИ'
    lines = [title, f'Чат: {get_chat_display_name(chat_id)}', '', 'Выберите раздел:']
    kb = types.InlineKeyboardMarkup()
    for value, count in vals[page * per:(page + 1) * per]:
        token = _v172_value_token(value)
        kb.row(IB(f'{value[:44]} · {count}', callback_data=f'v172:task:groupopen:{kind}:{token}:0'))
    if not vals:
        lines.append('Пока нет заполненных данных.')
    if pages > 1:
        kb.row(IB('◀️', callback_data=f'v172:task:groups:{kind}:{(page - 1) % pages}'), IB(f'{page + 1}/{pages}', callback_data='none'), IB('▶️', callback_data=f'v172:task:groups:{kind}:{(page + 1) % pages}'))
    return (_v172_mark('\n'.join(lines), 'Ф246'), _v172_standard_nav(kb, chat_id, 'v172:task:list:active:0'))

def _v172_group_tasks(chat_id: int, kind: str, token: str):
    value = ''
    for v, _count in _v172_group_values(chat_id, kind):
        if _v172_value_token(v) == token:
            value = v
            break
    if not value:
        return ('', [])
    rows = []
    for task in _v172_tasks_for_chat(chat_id):
        if _v172_is_complete(task):
            continue
        if kind == 'object' and str(task.get('object') or '').strip() == value:
            rows.append(task)
        elif kind == 'assignee' and any((str(a.get('name') or a.get('user_id') or '').strip() == value for a in task.get('assignees') or [] if isinstance(a, dict))):
            rows.append(task)
    rows.sort(key=_v172_sort_key)
    return (value, rows)

def _v172_history_text(task: dict):
    lines = [f"🕘 ИСТОРИЯ ЗАДАЧИ #{task.get('number')}", '']
    rows = list(task.get('history') or [])[-30:]
    for h in rows:
        at = str(h.get('at') or '').replace('T', ' ')[:16]
        user = str(h.get('user') or h.get('user_id') or 'system')
        action = str(h.get('action') or 'изменено')
        detail = str(h.get('detail') or '')
        lines.append(f'• {at} · {user} · {action}' + (f' — {detail}' if detail else ''))
    if not rows:
        lines.append('История пуста.')
    return _v172_mark('\n'.join(lines)[:3900], 'Ф245')

def _v172_admin_text(page: int=0):
    all_ids = []
    try:
        all_ids = list(collect_all_known_chat_ids(include_owner=True))
    except Exception:
        all_ids = [int(OWNER_ID)] if str(OWNER_ID or '').lstrip('-').isdigit() else []
    ids = sorted({int(x) for x in all_ids}, key=lambda c: str(get_chat_display_name(c)).casefold())
    per = 12
    pages = max(1, (len(ids) + per - 1) // per)
    page = max(0, min(int(page or 0), pages - 1))
    enabled = sum((1 for cid in ids if task_dispatcher_enabled(cid)))
    text = _v172_mark(f'📋 ДИСПЕТЧЕР ЗАДАЧ — ЧАТЫ\n\nВключите диспетчер только там, где нужно фиксировать работы и покупки.\nЗадачи каждого чата хранятся отдельно и не смешиваются с другими чатами/контурами.\n\nЧатов: {len(ids)} · включено: {enabled}\nСтраница {page + 1}/{pages}', 'Ф242')
    kb = types.InlineKeyboardMarkup()
    for cid in ids[page * per:(page + 1) * per]:
        flag = '✅' if task_dispatcher_enabled(cid) else '⬜'
        kb.row(IB(f'{flag} {get_chat_display_name(cid)[:42]}', callback_data=f'v172:task:toggle:{cid}:{page}'))
    if pages > 1:
        kb.row(IB('◀️', callback_data=f'v172:task:admin:{(page - 1) % pages}'), IB(f'{page + 1}/{pages}', callback_data='none'), IB('▶️', callback_data=f'v172:task:admin:{(page + 1) % pages}'))
    owner_chat = int(OWNER_ID or 0)
    return (text, _v172_standard_nav(kb, owner_chat, f'd:{today_key()}:back_main'))

def _canon_v172_set_input__001(chat_id: int, user_id: int, action: str, uid: str='', message_id: int=0, prompt_id: int=0):
    with _V172_INPUT_LOCK:
        _V172_INPUT_WAIT[int(chat_id), int(user_id)] = {'action': str(action), 'uid': str(uid or '').upper(), 'message_id': int(message_id or 0), 'prompt_id': int(prompt_id or 0), 'created': _v172_time.time()}

def _canon_v172_get_input__001(chat_id: int, user_id: int):
    key = (int(chat_id), int(user_id))
    with _V172_INPUT_LOCK:
        row = _V172_INPUT_WAIT.get(key)
        if row and _v172_time.time() - float(row.get('created', 0) or 0) > 900:
            _V172_INPUT_WAIT.pop(key, None)
            row = None
        return dict(row) if row else None

def _canon_v172_clear_input__001(chat_id: int, user_id: int):
    with _V172_INPUT_LOCK:
        return _V172_INPUT_WAIT.pop((int(chat_id), int(user_id)), None)

def _v172_parse_deadline(text: str):
    s = str(text or '').strip().lower()
    if s in {'нет', 'убрать', 'очистить', '-', 'без срока'}:
        return ''
    now = _v172_now()
    m = _v172_re.fullmatch('(сегодня|завтра)\\s+(\\d{1,2}):(\\d{2})', s)
    if m:
        base = now if m.group(1) == 'сегодня' else now + _v172_timedelta(days=1)
        return base.replace(hour=int(m.group(2)), minute=int(m.group(3)), second=0, microsecond=0).isoformat(timespec='minutes')
    formats = ('%d.%m.%Y %H:%M', '%d.%m.%y %H:%M', '%d.%m %H:%M', '%Y-%m-%d %H:%M')
    for fmt in formats:
        try:
            dt = _v172_datetime.strptime(s, fmt)
            if fmt == '%d.%m %H:%M':
                dt = dt.replace(year=now.year)
                if dt < now.replace(tzinfo=None) - _v172_timedelta(days=2):
                    dt = dt.replace(year=now.year + 1)
            if getattr(now, 'tzinfo', None) is not None and dt.tzinfo is None:
                dt = dt.replace(tzinfo=now.tzinfo)
            return dt.isoformat(timespec='minutes')
        except Exception:
            continue
    return None

def _canon_v172_prompt__001(chat_id: int, user_id: int, action: str, uid: str='', message_id: int=0):
    prompts = {'new_task': '✍️ Напишите текст новой задачи. Для отмены: отмена', 'new_purchase': '🛒 Напишите, что нужно купить. Для отмены: отмена', 'text': '✏️ Напишите новый текст задачи. Для отмены: отмена', 'object': '🏠 Напишите объект/дом/зону. Например: Дом №2, бассейн, сад. «нет» — очистить.', 'deadline': '📅 Введите срок: 12.08.2026 18:00, 12.08 18:00, сегодня 18:00, завтра 15:00. «нет» — убрать срок.', 'assign': '👥 Напишите ответственных через запятую: Daniel, Juan, @maria. «нет» — снять всех.', 'comment': '💬 Напишите комментарий к задаче. Для отмены: отмена', 'cost': '💰 Напишите стоимость/бюджет свободным текстом, например: 250 000 ARS или 180 USD. «нет» — очистить.', 'search': '🔎 Напишите слово или фразу для поиска по тексту, объекту и исполнителям.'}
    try:
        sent = bot.send_message(int(chat_id), prompts.get(action, 'Введите значение:'))
        _v172_set_input(chat_id, user_id, action, uid, message_id, int(getattr(sent, 'message_id', 0) or 0))
    except Exception:
        _v172_set_input(chat_id, user_id, action, uid, message_id, 0)

def _v172_delete_quiet(chat_id: int, message_id: int):
    if not message_id:
        return
    try:
        bot.delete_message(int(chat_id), int(message_id))
    except Exception:
        pass

def _v172_refresh_card(chat_id: int, message_id: int, task: dict, user_id: int):
    try:
        bot.edit_message_text(_v172_card_text(task), chat_id=int(chat_id), message_id=int(message_id), reply_markup=_v172_card_keyboard(task, chat_id, user_id))
    except Exception:
        pass

def _canon_v172_task_message_input__001(msg) -> bool:
    if getattr(msg, 'content_type', '') != 'text':
        return False
    cid = int(msg.chat.id)
    uid_user = int(getattr(getattr(msg, 'from_user', None), 'id', 0) or 0)
    wait = _v172_get_input(cid, uid_user)
    if not wait:
        return False
    text = str(getattr(msg, 'text', '') or '').strip()
    if text.lower() in {'отмена', 'cancel', 'стоп'}:
        old = _v172_clear_input(cid, uid_user) or wait
        _v172_delete_quiet(cid, int(old.get('prompt_id', 0) or 0))
        _v172_delete_quiet(cid, int(getattr(msg, 'message_id', 0) or 0))
        try:
            send_and_auto_delete(cid, '❎ Действие отменено.', 6)
        except Exception:
            pass
        return True
    action = str(wait.get('action') or '')
    task = _v172_task_for_uid(wait.get('uid')) if wait.get('uid') else None
    if task is not None and int(task.get('chat_id', 0) or 0) != cid:
        _v172_clear_input(cid, uid_user)
        return True
    user = getattr(msg, 'from_user', None)
    ok = True
    notice = '✅ Сохранено.'
    if action in {'new_task', 'new_purchase'}:
        if not task_dispatcher_enabled(cid):
            notice = '❌ Диспетчер задач в этом чате выключен.'
            ok = False
        elif not text:
            notice = '❌ Текст пустой.'
            ok = False
        else:
            task = _v172_create_task(cid, 'purchase' if action == 'new_purchase' else 'task', text, user, source_msg=None)
            notice = f"✅ Создана {('покупка' if action == 'new_purchase' else 'задача')} #{task.get('number')}."
    elif not isinstance(task, dict):
        notice = '❌ Задача не найдена.'
        ok = False
    elif action == 'text':
        if not (_v172_is_manager(uid_user, cid) or uid_user == int(task.get('creator_user_id', 0) or 0)):
            notice = '⛔ Изменять текст может автор или управляющий.'
            ok = False
        else:
            task['description'] = text[:4000]
            task['title'] = _v172_title(text)
            _v172_touch(task, user, 'text_changed', text[:180])
    elif action == 'object':
        value = '' if text.lower() in {'нет', 'убрать', 'очистить', '-'} else text[:180]
        task['object'] = value
        _v172_touch(task, user, 'object_changed', value or 'очищено')
    elif action == 'deadline':
        value = _v172_parse_deadline(text)
        if value is None:
            notice = '❌ Срок не распознан. Пример: 12.08 18:00 или завтра 15:00.'
            ok = False
        else:
            task['deadline'] = value
            _v172_touch(task, user, 'deadline_changed', value or 'срок убран')
    elif action == 'assign':
        if not (_v172_is_manager(uid_user, cid) or uid_user == int(task.get('creator_user_id', 0) or 0)):
            notice = '⛔ Назначать других может автор или управляющий.'
            ok = False
        else:
            if text.lower() in {'нет', 'убрать', 'очистить', '-'}:
                task['assignees'] = []
            else:
                names = [x.strip() for x in text.split(',') if x.strip()][:10]
                task['assignees'] = [{'user_id': 0, 'name': x[:100]} for x in names]
            _v172_touch(task, user, 'assignees_changed', _v172_assignee_text(task))
    elif action == 'comment':
        arr = task.setdefault('comments', [])
        arr.append({'at': _v172_iso(), 'user_id': uid_user, 'user': _v172_user_name(user), 'text': text[:1200]})
        if len(arr) > V172_COMMENT_KEEP:
            del arr[:-V172_COMMENT_KEEP]
        _v172_touch(task, user, 'comment_added', text[:220])
    elif action == 'cost':
        value = '' if text.lower() in {'нет', 'убрать', 'очистить', '-'} else text[:120]
        task['cost'] = value
        _v172_touch(task, user, 'cost_changed', value or 'очищено')
    elif action == 'search':
        q = text.casefold()
        hits = []
        for row in _v172_tasks_for_chat(cid):
            hay = ' '.join([str(row.get('title') or ''), str(row.get('description') or ''), str(row.get('object') or ''), _v172_assignee_text(row)]).casefold()
            if q in hay:
                hits.append(row)
        hits.sort(key=_v172_sort_key)
        _V172_SEARCH_CACHE[cid, uid_user] = {'query': text[:200], 'uids': [x.get('uid') for x in hits], 'at': _v172_time.time()}
        notice = f'🔎 Найдено: {len(hits)}'
    old = _v172_clear_input(cid, uid_user) or wait
    _v172_delete_quiet(cid, int(old.get('prompt_id', 0) or 0))
    _v172_delete_quiet(cid, int(getattr(msg, 'message_id', 0) or 0))
    if not ok:
        try:
            send_and_auto_delete(cid, notice, 10)
        except Exception:
            pass
        if action == 'deadline' and isinstance(task, dict):
            _v172_prompt(cid, uid_user, 'deadline', task.get('uid'), int(wait.get('message_id', 0) or 0))
        return True
    mid = int(wait.get('message_id', 0) or 0)
    if action == 'search':
        text2, kb2 = _v172_list_keyboard(cid, 'search', 0, uid_user)
        if mid:
            try:
                bot.edit_message_text(text2, chat_id=cid, message_id=mid, reply_markup=kb2)
            except Exception:
                bot.send_message(cid, text2, reply_markup=kb2)
        else:
            bot.send_message(cid, text2, reply_markup=kb2)
    elif isinstance(task, dict):
        if mid:
            _v172_refresh_card(cid, mid, task, uid_user)
        elif action in {'new_task', 'new_purchase'}:
            bot.send_message(cid, _v172_card_text(task), reply_markup=_v172_card_keyboard(task, cid, uid_user))
    try:
        send_and_auto_delete(cid, notice, 6)
    except Exception:
        pass
    return True

def _v172_install_message_input_wrapper() -> int:
    for row in list(getattr(bot, 'message_handlers', []) or []):
        if not isinstance(row, dict):
            continue
        fn = row.get('function')
        if not callable(fn) or getattr(fn, '_v172_task_input', False):
            continue
        if getattr(fn, '__name__', '') != 'on_any_message':
            continue

        def _wrapped(msg, _original=fn):
            try:
                if _v172_task_message_input(msg):
                    return
            except Exception as exc:
                try:
                    log_error(f'v172 task input: {exc}')
                except Exception:
                    pass
            return _original(msg)
        _wrapped._v172_task_input = True
        row['function'] = _wrapped
        return 1
    return 0

def _v172_command_text(msg) -> str:
    raw = str(getattr(msg, 'text', '') or '')
    parts = raw.split(None, 1)
    return parts[1].strip() if len(parts) > 1 else ''

def _v172_reply_text(msg) -> str:
    src = getattr(msg, 'reply_to_message', None)
    if src is None:
        return ''
    text = str(getattr(src, 'text', '') or getattr(src, 'caption', '') or '').strip()
    if text:
        return text
    ct = str(getattr(src, 'content_type', '') or 'сообщение')
    return f'{ct}: вложение из исходного сообщения'

def _v172_command_create(msg, kind: str):
    cid = int(msg.chat.id)
    if not task_dispatcher_enabled(cid):
        try:
            bot.reply_to(msg, '📋 Диспетчер задач в этом чате выключен. Владелец может включить его в основном окне.')
        except Exception:
            pass
        return
    text = _v172_command_text(msg)
    src = getattr(msg, 'reply_to_message', None)
    if not text and src is not None:
        text = _v172_reply_text(msg)
    if not text:
        action = 'new_purchase' if kind == 'purchase' else 'new_task'
        _v172_prompt(cid, int(getattr(msg.from_user, 'id', 0) or 0), action)
        return
    if src is not None:
        skey = _v172_source_key(cid, int(getattr(src, 'message_id', 0) or 0))
        existing_uid = _v172_source_root().get(skey)
        existing = _v172_task_for_uid(existing_uid) if existing_uid else None
        if isinstance(existing, dict) and (not existing.get('deleted')):
            try:
                bot.reply_to(msg, f"ℹ️ Это сообщение уже зафиксировано как #{existing.get('number')}.", reply_markup=_v172_card_keyboard(existing, cid, int(getattr(msg.from_user, 'id', 0) or 0)))
            except Exception:
                pass
            return
    task = _v172_create_task(cid, kind, text, msg.from_user, source_msg=src)
    try:
        sent = bot.send_message(cid, _v172_card_text(task), reply_markup=_v172_card_keyboard(task, cid, int(getattr(msg.from_user, 'id', 0) or 0)), reply_to_message_id=int(getattr(src, 'message_id', 0) or 0) or None)
        task['card_message_id'] = int(getattr(sent, 'message_id', 0) or 0)
        _v172_persist(cid, 'task_card_link')
    except Exception:
        try:
            bot.send_message(cid, _v172_card_text(task), reply_markup=_v172_card_keyboard(task, cid, int(getattr(msg.from_user, 'id', 0) or 0)))
        except Exception:
            pass

@bot.message_handler(commands=['tasks', 'задачи'])
def cmd_tasks_v172(msg):
    cid = int(msg.chat.id)
    uid = int(getattr(msg.from_user, 'id', 0) or 0)
    if cid == int(OWNER_ID or 0) and (not task_dispatcher_enabled(cid)):
        text, kb = _v172_admin_text(0)
        bot.send_message(cid, text, reply_markup=kb)
        return
    if not task_dispatcher_enabled(cid):
        bot.reply_to(msg, '📋 Диспетчер задач в этом чате выключен.')
        return
    text, kb = _v172_list_keyboard(cid, 'active', 0, uid)
    bot.send_message(cid, text, reply_markup=kb)

@bot.message_handler(commands=['task', 'задача'])
def cmd_task_v172(msg):
    _v172_command_create(msg, 'task')

@bot.message_handler(commands=['buy', 'покупка'])
def cmd_buy_v172(msg):
    _v172_command_create(msg, 'purchase')

@bot.message_handler(commands=['task_cancel', 'задачи_отмена'])
def cmd_task_cancel_v172(msg):
    row = _v172_clear_input(int(msg.chat.id), int(getattr(msg.from_user, 'id', 0) or 0))
    if row:
        _v172_delete_quiet(int(msg.chat.id), int(row.get('prompt_id', 0) or 0))
    try:
        send_and_auto_delete(int(msg.chat.id), '❎ Ввод задачи отменён.', 6)
    except Exception:
        pass

def _v172_edit_call(call, text, kb):
    try:
        safe_edit(bot, call, text, reply_markup=kb)
    except Exception:
        try:
            fast_ui_edit_message_text(int(call.message.chat.id), int(call.message.message_id), text, reply_markup=kb, purpose='task_callback_fallback_v178')
        except Exception:
            pass

def _v172_callback(call):
    raw = str(getattr(call, 'data', '') or '')
    try:
        resolver = globals().get('resolve_short_callback')
        if callable(resolver):
            raw = str(resolver(raw) or raw)
    except Exception:
        pass
    if not raw.startswith('v172:task:'):
        return False
    viewer_chat = int(call.message.chat.id)
    user = getattr(call, 'from_user', None)
    user_id = int(getattr(user, 'id', 0) or 0)
    parts = raw.split(':')
    action = parts[2] if len(parts) > 2 else ''
    try:
        bot.answer_callback_query(call.id)
    except Exception:
        pass
    if action == 'admin':
        if viewer_chat != int(OWNER_ID or 0) and (not _v172_is_manager(user_id, viewer_chat)):
            return True
        page = int(parts[3]) if len(parts) > 3 and parts[3].lstrip('-').isdigit() else 0
        text, kb = _v172_admin_text(page)
        _v172_edit_call(call, text, kb)
        return True
    if action == 'toggle':
        if viewer_chat != int(OWNER_ID or 0):
            return True
        try:
            target = int(parts[3])
            page = int(parts[4]) if len(parts) > 4 else 0
        except Exception:
            return True
        s = _v172_chat_settings(target)
        s['enabled'] = not bool(s.get('enabled'))
        s['updated_at'] = _v172_iso()
        s['updated_by'] = user_id
        _v172_persist(target, 'dispatcher_toggle')
        try:
            note = '✅ Диспетчер задач включён. Используйте /tasks, /task и /buy.' if s['enabled'] else '⏸ Диспетчер задач выключен владельцем. Существующие задачи сохранены.'
            bot.send_message(target, note)
        except Exception:
            pass
        try:
            schedule_main_window_recreate_after_quiet(target, delay=0.2)
        except Exception:
            pass
        text, kb = _v172_admin_text(page)
        _v172_edit_call(call, text, kb)
        return True
    if not task_dispatcher_enabled(viewer_chat):
        try:
            bot.answer_callback_query(call.id, 'Диспетчер в этом чате выключен.', show_alert=True)
        except Exception:
            pass
        return True
    if action == 'list':
        filt = parts[3] if len(parts) > 3 else 'active'
        try:
            page = int(parts[4]) if len(parts) > 4 else 0
        except Exception:
            page = 0
        text, kb = _v172_list_keyboard(viewer_chat, filt, page, user_id)
        _v172_edit_call(call, text, kb)
        return True
    if action == 'new':
        kind = parts[3] if len(parts) > 3 else 'task'
        _v172_prompt(viewer_chat, user_id, 'new_purchase' if kind == 'purchase' else 'new_task', message_id=int(call.message.message_id))
        return True
    if action == 'search':
        _v172_prompt(viewer_chat, user_id, 'search', message_id=int(call.message.message_id))
        return True
    if action == 'groups':
        kind = parts[3] if len(parts) > 3 else 'object'
        try:
            page = int(parts[4]) if len(parts) > 4 else 0
        except Exception:
            page = 0
        text, kb = _v172_groups_text_kb(viewer_chat, kind, page)
        _v172_edit_call(call, text, kb)
        return True
    if action == 'groupopen':
        if len(parts) < 6:
            return True
        kind, token = (parts[3], parts[4])
        try:
            page = int(parts[5])
        except Exception:
            page = 0
        value, rows = _v172_group_tasks(viewer_chat, kind, token)
        per = V172_TASK_PAGE_SIZE
        pages = max(1, (len(rows) + per - 1) // per)
        page = max(0, min(page, pages - 1))
        title = ('🏠 ' if kind == 'object' else '👤 ') + (value or 'Не найдено')
        text = _v172_mark(f'{title}\n\nЗадач: {len(rows)}\nСтраница {page + 1}/{pages}', 'Ф246')
        kb = types.InlineKeyboardMarkup()
        for task in rows[page * per:(page + 1) * per]:
            kb.row(IB(f"#{task.get('number')} {str(task.get('title') or '')[:42]}", callback_data=f"v172:task:open:{task.get('uid')}"))
        if pages > 1:
            kb.row(IB('◀️', callback_data=f'v172:task:groupopen:{kind}:{token}:{(page - 1) % pages}'), IB(f'{page + 1}/{pages}', callback_data='none'), IB('▶️', callback_data=f'v172:task:groupopen:{kind}:{token}:{(page + 1) % pages}'))
        _v172_standard_nav(kb, viewer_chat, f'v172:task:groups:{kind}:0')
        _v172_edit_call(call, text, kb)
        return True
    uid = parts[3].upper() if len(parts) > 3 else ''
    task = _v172_task_for_uid(uid)
    if not isinstance(task, dict) or int(task.get('chat_id', 0) or 0) != viewer_chat or task.get('deleted'):
        try:
            bot.answer_callback_query(call.id, 'Задача не найдена или уже удалена.', show_alert=True)
        except Exception:
            pass
        return True
    if action == 'open':
        _v172_edit_call(call, _v172_card_text(task), _v172_card_keyboard(task, viewer_chat, user_id))
        return True
    if action == 'st':
        status = parts[4] if len(parts) > 4 else ''
        if status in _v172_status_map(task):
            task['status'] = status
            _v172_touch(task, user, 'status_changed', _v172_status_text(task))
            _v172_edit_call(call, _v172_card_text(task), _v172_card_keyboard(task, viewer_chat, user_id))
        return True
    if action == 'prio':
        order = ['normal', 'important', 'urgent']
        cur = str(task.get('priority') or 'normal')
        task['priority'] = order[(order.index(cur) + 1) % len(order)] if cur in order else 'normal'
        _v172_touch(task, user, 'priority_changed', _v172_priority_text(task))
        _v172_edit_call(call, _v172_card_text(task), _v172_card_keyboard(task, viewer_chat, user_id))
        return True
    if action == 'take':
        arr = [x for x in task.get('assignees') or [] if isinstance(x, dict)]
        existing = next((x for x in arr if int(x.get('user_id', 0) or 0) == user_id and user_id), None)
        if existing:
            arr = [x for x in arr if int(x.get('user_id', 0) or 0) != user_id]
            detail = 'снял себя'
        else:
            arr.append({'user_id': user_id, 'name': _v172_user_name(user)})
            detail = 'взял себе'
            if str(task.get('type')) == 'task' and str(task.get('status')) == 'new':
                task['status'] = 'work'
            if str(task.get('type')) == 'purchase' and str(task.get('status')) == 'need':
                task['status'] = 'search'
        task['assignees'] = arr[:10]
        _v172_touch(task, user, 'assignee_self', detail)
        _v172_edit_call(call, _v172_card_text(task), _v172_card_keyboard(task, viewer_chat, user_id))
        return True
    if action == 'input':
        field = parts[4] if len(parts) > 4 else ''
        if field in {'text', 'assign'} and (not (_v172_is_manager(user_id, viewer_chat) or user_id == int(task.get('creator_user_id', 0) or 0))):
            try:
                bot.answer_callback_query(call.id, 'Это может изменить автор или управляющий.', show_alert=True)
            except Exception:
                pass
            return True
        if field in {'text', 'object', 'deadline', 'assign', 'comment', 'cost'}:
            _v172_prompt(viewer_chat, user_id, field, uid, int(call.message.message_id))
            return True
    if action == 'hist':
        kb = types.InlineKeyboardMarkup()
        _v172_standard_nav(kb, viewer_chat, f'v172:task:open:{uid}')
        _v172_edit_call(call, _v172_history_text(task), kb)
        return True
    if action == 'source':
        try:
            bot.answer_callback_query(call.id, f"Исходное сообщение ID: {task.get('source_message_id')}. Прямая ссылка для этого типа чата недоступна.", show_alert=True)
        except Exception:
            pass
        return True
    if action == 'del':
        if not (_v172_is_manager(user_id, viewer_chat) or user_id == int(task.get('creator_user_id', 0) or 0)):
            try:
                bot.answer_callback_query(call.id, 'Удалить может автор или управляющий.', show_alert=True)
            except Exception:
                pass
            return True
        kb = types.InlineKeyboardMarkup()
        kb.row(IB('✅ Да, удалить', callback_data=f'v172:task:delok:{uid}'), IB('❌ Нет', callback_data=f'v172:task:open:{uid}'))
        _v172_standard_nav(kb, viewer_chat, f'v172:task:open:{uid}')
        _v172_edit_call(call, _v172_mark(f"🗑 Удалить задачу #{task.get('number')}?\n\n{task.get('title')}", 'Ф244'), kb)
        return True
    if action == 'delok':
        if not (_v172_is_manager(user_id, viewer_chat) or user_id == int(task.get('creator_user_id', 0) or 0)):
            return True
        task['deleted'] = True
        _v172_touch(task, user, 'deleted', 'soft delete')
        text, kb = _v172_list_keyboard(viewer_chat, 'active', 0, user_id)
        _v172_edit_call(call, text, kb)
        return True
    return True
_V172_PREV_BUILD_MAIN_KEYBOARD = _v177_legacy_0165_build_main_keyboard

def _v177_legacy_0166_build_main_keyboard(day_key: str, chat_id=None):
    kb = _V172_PREV_BUILD_MAIN_KEYBOARD(day_key, chat_id) if callable(_V172_PREV_BUILD_MAIN_KEYBOARD) else types.InlineKeyboardMarkup()
    try:
        cid = int(chat_id) if chat_id is not None else 0
        rows = list(getattr(kb, 'keyboard', None) or getattr(kb, 'inline_keyboard', None) or [])
        callbacks = {str(getattr(b, 'callback_data', '') or '') for row in rows for b in row or []}
        inserts = []
        if cid and task_dispatcher_enabled(cid) and ('v172:task:list:active:0' not in callbacks):
            inserts.append(IB('📋 Задачи', callback_data='v172:task:list:active:0'))
        if cid and cid == int(OWNER_ID or 0) and ('v172:task:admin:0' not in callbacks):
            inserts.append(IB('📋 Диспетчер задач', callback_data='v172:task:admin:0'))
        if inserts:
            idx = len(rows)
            for i, row in enumerate(rows):
                if any(('закры' in str(getattr(b, 'text', '') or '').casefold() for b in row or [])):
                    idx = i
                    break
            rows.insert(idx, inserts)
            try:
                kb.keyboard = rows
            except Exception:
                try:
                    kb.inline_keyboard = rows
                except Exception:
                    pass
    except Exception as exc:
        try:
            log_error(f'v172 main keyboard: {exc}')
        except Exception:
            pass
    return kb
try:
    _v177_legacy_0166_build_main_keyboard.__name__ = 'build_main_keyboard'
except Exception:
    pass
_V172_PREV_RESTORE_VALIDATOR = _v177_legacy_0288_v153_validate_restore_gz

def _v177_legacy_0289_v153_validate_restore_gz(gz_path: str):
    try:
        return _V172_PREV_RESTORE_VALIDATOR(gz_path) if callable(_V172_PREV_RESTORE_VALIDATOR) else (None, None)
    except Exception as exc:
        if 'unsupported bot version' not in str(exc):
            raise
    import gzip, os, shutil, sqlite3, tempfile, json
    folder = tempfile.mkdtemp(prefix='v172_restore_validate_')
    raw = os.path.join(folder, 'restore.sqlite3')
    try:
        with gzip.open(gz_path, 'rb') as fin, open(raw, 'wb') as fout:
            shutil.copyfileobj(fin, fout, 1024 * 1024)
        conn = sqlite3.connect(raw)
        try:
            integrity = str(conn.execute('PRAGMA integrity_check').fetchone()[0])
            if integrity.lower() != 'ok':
                raise RuntimeError(f'SQLite integrity_check: {integrity}')
            row = conn.execute("SELECT v FROM meta WHERE kind='v153_export' AND k='manifest'").fetchone()
            if not row:
                raise RuntimeError('manifest v153 not found')
            manifest = json.loads(row[0])
        finally:
            conn.close()
        if str(manifest.get('kind')) != 'telegram_bot_full_state_v153':
            raise RuntimeError('unknown export kind')
        if int(manifest.get('schema_version') or 0) != int(V153_EXPORT_SCHEMA):
            raise RuntimeError('unsupported export schema')
        export_version = str(manifest.get('bot_version') or '')
        if not export_version.startswith(tuple((f'bot_v{i}_' for i in range(153, 173)))):
            raise RuntimeError(f"unsupported bot version: {export_version or 'missing'}")
        if _v153_db_logical_checksum(raw) != str(manifest.get('checksum') or ''):
            raise RuntimeError('checksum mismatch')
        return (manifest, raw)
    except Exception:
        shutil.rmtree(folder, ignore_errors=True)
        raise
try:
    _v177_legacy_0289_v153_validate_restore_gz.__name__ = '_v153_validate_restore_gz'
except Exception:
    pass
_V172_PREV_RUNTIME_MARK_READY = _v179_legacy_runtime_mark_ready
if callable(_V172_PREV_RUNTIME_MARK_READY):

    def runtime_mark_ready(detail: str=''):
        result = _V172_PREV_RUNTIME_MARK_READY(detail)
        try:
            data.setdefault(V172_TASKS_KEY, {})
            data.setdefault(V172_TASK_SETTINGS_KEY, {})
            data.setdefault(V172_TASK_SOURCE_INDEX_KEY, {})
            _DELTA_ROOT_MAP_KEYS.update({V172_TASKS_KEY, V172_TASK_SETTINGS_KEY, V172_TASK_SOURCE_INDEX_KEY})
            bot_journal('v172_task_dispatcher_ready', int(OWNER_ID or 0), f"tasks={len(_v172_tasks_root())}; enabled={sum((1 for x in _v172_settings_root().values() if isinstance(x, dict) and x.get('enabled')))}")
        except Exception:
            pass
        return result
_V172_MESSAGE_WRAPPERS = _v172_install_message_input_wrapper()
_V172_CALLBACK_HANDLERS = 0
try:
    _v177_legacy_0007_bot_journal('v172_installed', int(OWNER_ID or 0), f'task_dispatcher=1; callback={_V172_CALLBACK_HANDLERS}; message_wrap={_V172_MESSAGE_WRAPPERS}; root_delta_maps=3')
except Exception:
    pass
'v173: reliable owner cross-chat reminders + unmistakable unique journal filenames.\n\nLoaded after v172.  The platform owner may explicitly select any chat from the reminder\npicker; second-circle tenants remain isolated.  Operational journal downloads get a\nhuman type name plus an export timestamp/sequence so Telegram never has to append (1),\n(2), etc. to two different downloads from the same day.\n'
import os as _v173_os
import re as _v173_re
import threading as _v173_threading
from datetime import datetime as _v173_datetime
V173_FILE_MARKER = 'v173_reminder_crosschat_unique_journals'
_V173_PREV_REMINDER_CHAT_ALLOWED = _v177_legacy_0265_v149_reminder_chat_allowed

def _v173_reminder_selected_chat_ids(cfg: dict) -> set[int]:
    out = set()
    for raw in (cfg or {}).get('chat_ids') or []:
        try:
            out.add(int(raw))
        except Exception:
            continue
    return out

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
_V173_BASE_REMINDER_SEND_INDIVIDUAL = globals().get('_v149_send_individual')
if callable(_V173_BASE_REMINDER_SEND_INDIVIDUAL):

    def _v149_send_individual(chat_id: int, reminder_id: int, cfg: dict, active_count: int):
        try:
            result = _V173_BASE_REMINDER_SEND_INDIVIDUAL(int(chat_id), int(reminder_id), cfg, int(active_count))
            ok = bool(result[0]) if isinstance(result, tuple) and result else bool(result)
            mid = int(result[1] or 0) if isinstance(result, tuple) and len(result) > 1 else 0
            try:
                bot_journal('reminder_delivery_v173', int(chat_id), f'reminder_id={int(reminder_id)} mode=individual ok={ok} message_id={mid}', 'INFO' if ok else 'WARN')
            except Exception:
                pass
            return result
        except Exception as exc:
            try:
                bot_journal('reminder_delivery_v173', int(chat_id), f'reminder_id={int(reminder_id)} mode=individual ok=False error={str(exc)[:300]}', 'ERROR')
            except Exception:
                pass
            raise
_V173_BASE_REMINDER_SEND_GROUP = globals().get('_v149_send_or_edit_group')
if callable(_V173_BASE_REMINDER_SEND_GROUP):

    def _v149_send_or_edit_group(chat_id: int, text: str, old_message_id: int=0, reply_markup=None):
        try:
            result = _V173_BASE_REMINDER_SEND_GROUP(int(chat_id), text, int(old_message_id or 0), reply_markup=reply_markup)
            ok = bool(result[0]) if isinstance(result, tuple) and result else bool(result)
            mid = int(result[1] or 0) if isinstance(result, tuple) and len(result) > 1 else 0
            try:
                bot_journal('reminder_delivery_v173', int(chat_id), f'mode=merged ok={ok} message_id={mid} old_message_id={int(old_message_id or 0)}', 'INFO' if ok else 'WARN')
            except Exception:
                pass
            return result
        except Exception as exc:
            try:
                bot_journal('reminder_delivery_v173', int(chat_id), f'mode=merged ok=False error={str(exc)[:300]}', 'ERROR')
            except Exception:
                pass
            raise
_V173_DOWNLOAD_NAME_LOCK = _v173_threading.RLock()
_V173_DOWNLOAD_NAME_SEQ = 0
_V173_DOWNLOAD_NAME_LAST_SECOND = ''
V173_DOWNLOAD_KIND_NAMES = {'Журнал_текущей_версии': 'События_текущей_версии', 'Журнал_диагностики': 'Диагностика_бота', 'Журнал_FAILED_задач': 'FAILED_задачи', 'Журнал_ошибок': 'Ошибки_бота', 'Журнал_восстановления': 'Восстановление_бота', 'Журнал_пересылки': 'Пересылка_сообщений', 'Журнал_аудита': 'Аудит_целостности', 'Журнал_резервных_копий': 'Резервное_копирование', 'Журнал_финансов': 'Финансовые_операции', 'Журнал_операций': 'Действия_бота', 'Диагностика_Runtime_MEGA': 'Диагностика_Runtime_MEGA', 'ТЗ_окон_текущая_версия': 'ТЗ_окон_текущая_версия', 'ТЗ_окон_архив': 'ТЗ_окон_архив', 'Маркировки_окон': 'Маркировки_окон', 'Исходник_бота': 'Исходник_бота'}

def _v173_export_stamp() -> str:
    global _V173_DOWNLOAD_NAME_SEQ, _V173_DOWNLOAD_NAME_LAST_SECOND
    try:
        now = now_local()
    except Exception:
        now = _v173_datetime.now()
    second = now.strftime('%Y-%m-%d_%H-%M-%S')
    millis = int(getattr(now, 'microsecond', 0) // 1000)
    with _V173_DOWNLOAD_NAME_LOCK:
        if second != _V173_DOWNLOAD_NAME_LAST_SECOND:
            _V173_DOWNLOAD_NAME_LAST_SECOND = second
            _V173_DOWNLOAD_NAME_SEQ = 0
        _V173_DOWNLOAD_NAME_SEQ += 1
        seq = _V173_DOWNLOAD_NAME_SEQ
    return f'{second}-{millis:03d}-{seq:02d}'

def _v173_safe_component(value: str, fallback: str='файл') -> str:
    try:
        fn = globals().get('_v152_filename_component')
        if callable(fn):
            return str(fn(value, fallback))
    except Exception:
        pass
    text = _v173_re.sub('[\\\\/:*?\\"<>|]+', '-', str(value or fallback))
    text = _v173_re.sub('\\s+', '-', text).strip('-._')
    return (text or fallback)[:80]

def _canon_v152_human_download_name__001(recipient_chat_id: int, document, caption: str='', purpose: str='') -> str | None:
    """Readable and collision-free name for each operational download."""
    try:
        kind = _v152_download_kind(document, caption, purpose)
    except Exception:
        kind = None
    if not kind:
        return None
    old_name = str(getattr(document, 'name', '') or getattr(document, 'file_name', '') or '')
    ext = _v173_os.path.splitext(old_name)[1].lower()
    if kind == 'Исходник_бота':
        ext = '.py'
    elif ext not in {'.txt', '.csv', '.zip', '.json', '.xlsx', '.gz', '.sqlite3', '.py'}:
        ext = '.zip' if kind in {'Журнал_FAILED_задач', 'Диагностика_Runtime_MEGA'} else '.txt'
    try:
        scope = _v152_scope_name(int(recipient_chat_id), kind)
    except Exception:
        scope = _v173_safe_component(f'Чат-{recipient_chat_id}', 'Чат')
    try:
        period = _v152_period_suffix(document, caption, purpose)
    except Exception:
        period = ''
    visible_kind = V173_DOWNLOAD_KIND_NAMES.get(str(kind), str(kind))
    pieces = [_v173_safe_component(visible_kind, 'Выгрузка'), _v173_safe_component(scope, 'Чат')]
    if period:
        pieces.append(_v173_safe_component(period, 'период'))
    pieces.append(f'выгрузка-{_v173_export_stamp()}')
    return '_'.join(pieces) + ext
_V173_PREV_RESTORE_VALIDATOR = _v177_legacy_0289_v153_validate_restore_gz

def _v177_legacy_0290_v153_validate_restore_gz(gz_path: str):
    try:
        return _V173_PREV_RESTORE_VALIDATOR(gz_path) if callable(_V173_PREV_RESTORE_VALIDATOR) else (None, None)
    except Exception as exc:
        if 'unsupported bot version' not in str(exc):
            raise
    import gzip, shutil, sqlite3, tempfile, json
    folder = tempfile.mkdtemp(prefix='v173_restore_validate_')
    raw = _v173_os.path.join(folder, 'restore.sqlite3')
    try:
        with gzip.open(gz_path, 'rb') as fin, open(raw, 'wb') as fout:
            shutil.copyfileobj(fin, fout, 1024 * 1024)
        conn = sqlite3.connect(raw)
        try:
            integrity = str(conn.execute('PRAGMA integrity_check').fetchone()[0])
            if integrity.lower() != 'ok':
                raise RuntimeError(f'SQLite integrity_check: {integrity}')
            row = conn.execute("SELECT v FROM meta WHERE kind='v153_export' AND k='manifest'").fetchone()
            if not row:
                raise RuntimeError('manifest v153 not found')
            manifest = json.loads(row[0])
        finally:
            conn.close()
        if str(manifest.get('kind')) != 'telegram_bot_full_state_v153':
            raise RuntimeError('unknown export kind')
        if int(manifest.get('schema_version') or 0) != int(V153_EXPORT_SCHEMA):
            raise RuntimeError('unsupported export schema')
        export_version = str(manifest.get('bot_version') or '')
        if not export_version.startswith(tuple((f'bot_v{i}_' for i in range(153, 174)))):
            raise RuntimeError(f"unsupported bot version: {export_version or 'missing'}")
        if _v153_db_logical_checksum(raw) != str(manifest.get('checksum') or ''):
            raise RuntimeError('checksum mismatch')
        return (manifest, raw)
    except Exception:
        shutil.rmtree(folder, ignore_errors=True)
        raise
try:
    _v177_legacy_0290_v153_validate_restore_gz.__name__ = '_v153_validate_restore_gz'
except Exception:
    pass
try:
    _v177_legacy_0007_bot_journal('v173_installed', int(OWNER_ID or 0), 'platform reminder explicit targets bypass tenant-scoped known-chat recheck; unique typed journal filenames enabled')
except Exception:
    pass
'v174: simplified chat-native task dispatcher with editable keywords and circle inventory.\n\nDesign goals:\n- owner dispatcher inventory comes from v164 circle-1 + circle-2 registries, never tenant_current_id();\n- work chat UI is intentionally compact;\n- normal user messages can create tasks/purchases from editable keywords;\n- status keywords only change a known task by reply or explicit #number, preventing accidental closes;\n- v172 task storage/UID/history/SQLite+MEGA durability are reused without migration.\n'
import re as _v174_re
import threading as _v174_threading
import time as _v174_time
V174_FILE_MARKER = 'v174_simplified_task_dispatcher'
try:
    WINDOW_MARKER_CONSTANTS.update({'v174:td:admin': 'Ф247', 'v174:td:menu': 'Ф248', 'v174:td:card': 'Ф249', 'v174:td:keywords': 'Ф250'})
except Exception:
    pass
_V174_DEFAULT_KEYWORDS = {'task': ['задача', 'нужно сделать', 'надо сделать', 'сделать:', '#задача'], 'purchase': ['купить', 'покупка', 'нужно купить', 'надо купить', 'заказать', '#покупка'], 'done': ['готово', 'сделано', 'выполнено', 'выполнена', '✅'], 'deferred': ['отложить', 'отложено', 'позже', '⏸'], 'cancelled': ['отмена', 'отменить', 'отменено', 'не актуально', 'неактуально', '❌'], 'work': ['в работу', 'делаю', 'начал', 'начинаю', '▶️']}
_V174_KEYWORD_LABELS = {'task': '📋 Задача', 'purchase': '🛒 Покупка', 'done': '✅ Выполнено', 'deferred': '⏸ Отложено', 'cancelled': '❌ Отмена', 'work': '▶️ В работу'}
_V174_INPUT_LOCK = _v174_threading.RLock()
_V174_INPUT_WAIT = {}
try:
    _TASK_STATUS['cancelled'] = ('❌', 'Отменена')
    _PURCHASE_STATUS['deferred'] = ('⏸', 'Отложена')
    _PURCHASE_STATUS['cancelled'] = ('❌', 'Отменена')
except Exception:
    pass
_V174_PREV_IS_COMPLETE = _v177_legacy_0327_v172_is_complete

def _canon_v172_is_complete__001(task: dict) -> bool:
    try:
        status = str((task or {}).get('status') or '')
        if status == 'cancelled':
            return True
        if str((task or {}).get('type')) == 'purchase':
            return status == 'received'
        return status == 'done'
    except Exception:
        return bool(_V174_PREV_IS_COMPLETE(task)) if callable(_V174_PREV_IS_COMPLETE) else False

def _v174_settings(chat_id: int) -> dict:
    row = _v172_chat_settings(int(chat_id))
    row.setdefault('auto_capture', True)
    kw = row.setdefault('keywords_v174', {})
    for kind, defaults in _V174_DEFAULT_KEYWORDS.items():
        current = kw.get(kind)
        if not isinstance(current, list):
            kw[kind] = list(defaults)
        else:
            kw[kind] = [str(x).strip() for x in current if str(x).strip()][:30]
    return row

def _v174_keywords(chat_id: int, kind: str) -> list[str]:
    return list((_v174_settings(int(chat_id)).get('keywords_v174') or {}).get(str(kind), []) or [])

def _v174_set_keywords(chat_id: int, kind: str, values) -> None:
    kind = str(kind)
    if kind not in _V174_DEFAULT_KEYWORDS:
        return
    clean = []
    seen = set()
    for raw in values or []:
        value = ' '.join(str(raw or '').strip().split())[:80]
        low = value.casefold()
        if value and low not in seen:
            seen.add(low)
            clean.append(value)
    if not clean:
        clean = list(_V174_DEFAULT_KEYWORDS[kind])
    _v174_settings(int(chat_id)).setdefault('keywords_v174', {})[kind] = clean[:30]
    _v172_persist(int(chat_id), f'keywords_{kind}')

def _v174_normalize(text: str) -> str:
    return ' '.join(str(text or '').casefold().replace('ё', 'е').split())

def _v174_has_keyword(text: str, keyword: str) -> bool:
    hay = _v174_normalize(text)
    needle = _v174_normalize(keyword)
    if not hay or not needle:
        return False
    if needle.startswith('#') or needle in {'✅', '⏸', '❌', '▶️'}:
        return needle in hay
    try:
        return bool(_v174_re.search('(?<!\\w)' + _v174_re.escape(needle) + '(?!\\w)', hay, flags=_v174_re.UNICODE))
    except Exception:
        return needle in hay

def _v174_match_kind(chat_id: int, text: str, kinds) -> str:
    for kind in kinds:
        words = sorted(_v174_keywords(chat_id, kind), key=lambda x: (-len(_v174_normalize(x)), _v174_normalize(x)))
        for word in words:
            if _v174_has_keyword(text, word):
                return str(kind)
    return ''

def _v174_circle_ids(level: int) -> list[int]:
    level = 2 if int(level) == 2 else 1
    ids = []
    fn = globals().get('_v164_all_circle_ids')
    if callable(fn):
        try:
            ids = [int(x) for x in fn(level)]
        except Exception:
            ids = []
    if not ids:
        known_fn = globals().get('_v164_known_chat_ids')
        info_fn = globals().get('circle_level_for_chat')
        if callable(known_fn) and callable(info_fn):
            try:
                ids = [int(x) for x in known_fn() if int(x) and int(info_fn(int(x))) == level]
            except Exception:
                ids = []
    out = []
    owner = int(OWNER_ID or 0)
    for cid in ids:
        if not cid or cid == owner:
            continue
        try:
            removed_fn = globals().get('is_chat_bot_removed')
            if callable(removed_fn) and removed_fn(int(cid)):
                continue
        except Exception:
            pass
        out.append(int(cid))
    return sorted(set(out), key=lambda c: str(get_chat_display_name(c) or f'Чат {c}').casefold())

def _v212_legacy__v174_admin_text_kb(level: int=1, page: int=0):
    level = 2 if int(level) == 2 else 1
    ids = _v174_circle_ids(level)
    all1, all2 = (_v174_circle_ids(1), _v174_circle_ids(2))
    per = 10
    pages = max(1, (len(ids) + per - 1) // per)
    page = max(0, min(int(page or 0), pages - 1))
    enabled = sum((1 for cid in ids if task_dispatcher_enabled(cid)))
    text = _v172_mark(f"📋 ДИСПЕТЧЕР ЗАДАЧ\n\nВыберите рабочие чаты. После включения бот сможет автоматически фиксировать задачи и покупки по ключевым словам.\n\n1️⃣ Первый круг: {len(all1)}\n2️⃣ Второй круг: {len(all2)}\n\nСейчас: {('1-й' if level == 1 else '2-й')} круг · включено {enabled}/{len(ids)}\nСтраница {page + 1}/{pages}", 'Ф247')
    kb = types.InlineKeyboardMarkup()
    kb.row(IB(('✅ ' if level == 1 else '') + f'1️⃣ Первый круг ({len(all1)})', callback_data='v174:td:admin:1:0'), IB(('✅ ' if level == 2 else '') + f'2️⃣ Второй круг ({len(all2)})', callback_data='v174:td:admin:2:0'))
    for cid in ids[page * per:(page + 1) * per]:
        name = str(get_chat_display_name(cid) or f'Чат {cid}')
        if name.casefold() in {'чат 0', 'chat 0'}:
            continue
        flag = '✅' if task_dispatcher_enabled(cid) else '⬜️'
        kb.row(IB(f'{flag} {name[:46]}', callback_data=f'v174:td:toggle:{cid}:{level}:{page}'))
    if pages > 1:
        kb.row(IB('◀️', callback_data=f'v174:td:admin:{level}:{(page - 1) % pages}'), IB(f'{page + 1}/{pages}', callback_data='none'), IB('▶️', callback_data=f'v174:td:admin:{level}:{(page + 1) % pages}'))
    try:
        _v172_standard_nav(kb, int(OWNER_ID or 0), f'd:{today_key()}:back_main')
    except Exception:
        pass
    return (text, kb)

def _v212_legacy__v174_counts(chat_id: int, user_id: int=0) -> dict:
    rows = _v172_tasks_for_chat(int(chat_id))
    out = {'active': 0, 'mine': 0, 'urgent': 0, 'deferred': 0, 'done': 0, 'cancelled': 0}
    for task in rows:
        status = str(task.get('status') or '')
        cancelled = status == 'cancelled'
        complete = _v172_is_complete(task)
        if cancelled:
            out['cancelled'] += 1
        elif complete:
            out['done'] += 1
        elif status == 'deferred':
            out['deferred'] += 1
        else:
            out['active'] += 1
        if not complete and str(task.get('priority')) == 'urgent':
            out['urgent'] += 1
        if not complete and any((int(a.get('user_id', 0) or 0) == int(user_id or 0) for a in task.get('assignees') or [] if isinstance(a, dict))):
            out['mine'] += 1
    return out

def _v212_legacy__v174_menu_text_kb(chat_id: int, user_id: int=0):
    cid = int(chat_id)
    counts = _v174_counts(cid, user_id)
    auto = bool(_v174_settings(cid).get('auto_capture', True))
    text = _v172_mark(f"📋 ЗАДАЧИ\n\n📌 Активные: {counts['active']}   🔴 Срочные: {counts['urgent']}\n🙋 Мои: {counts['mine']}   ⏸ Отложенные: {counts['deferred']}\n\n🤖 Автоподхват по словам: {('✅ ВКЛ' if auto else '⬜ ВЫКЛ')}\nПример: «нужно купить фильтр» → покупка.\nОтветьте «готово» на исходное сообщение → задача выполнена.", 'Ф248')
    kb = types.InlineKeyboardMarkup()
    kb.row(IB('➕ Задача', callback_data='v174:td:new:task'), IB('🛒 Покупка', callback_data='v174:td:new:purchase'))
    kb.row(IB(f"📌 Активные {counts['active']}", callback_data='v174:td:list:active:0'), IB(f"🙋 Мои {counts['mine']}", callback_data='v174:td:list:mine:0'))
    kb.row(IB(f"🔴 Срочные {counts['urgent']}", callback_data='v174:td:list:urgent:0'), IB(f"⏸ Отложенные {counts['deferred']}", callback_data='v174:td:list:deferred:0'))
    kb.row(IB('✅ Выполненные', callback_data='v174:td:list:done:0'), IB('❌ Отменённые', callback_data='v174:td:list:cancelled:0'))
    kb.row(IB('⚙️ Ключевые слова', callback_data='v174:td:keywords'))
    try:
        _v172_standard_nav(kb, cid, f'd:{today_key()}:back_main')
    except Exception:
        pass
    return (text, kb)

def _v174_task_by_number(chat_id: int, number: int):
    for task in _v172_tasks_for_chat(int(chat_id)):
        if int(task.get('number', 0) or 0) == int(number) and (not task.get('deleted')):
            return task
    return None

def _v228_prev_v174_task_for_reply(chat_id: int, reply_message_id: int):
    cid = int(chat_id)
    mid = int(reply_message_id or 0)
    if not mid:
        return None
    try:
        uid = _v172_source_root().get(_v172_source_key(cid, mid))
        task = _v172_task_for_uid(uid) if uid else None
        if isinstance(task, dict) and (not task.get('deleted')):
            return task
    except Exception:
        pass
    for task in _v172_tasks_for_chat(cid):
        if int(task.get('card_message_id', 0) or 0) == mid and (not task.get('deleted')):
            return task
    return None

def _v174_status_label(task: dict) -> str:
    status = str(task.get('status') or '')
    labels = {'new': '🆕 Новая', 'work': '▶️ В работе', 'wait': '🟣 Ждёт', 'deferred': '⏸ Отложена', 'done': '✅ Выполнена', 'need': '🛒 Купить', 'search': '🔎 Ищем', 'ordered': '📦 Заказано', 'bought': '💰 Куплено', 'received': '✅ Куплено', 'cancelled': '❌ Отменена'}
    return labels.get(status, _v172_status_text(task))

def _v174_compact_text(task: dict) -> str:
    kind = '🛒 ПОКУПКА' if str(task.get('type')) == 'purchase' else '📋 ЗАДАЧА'
    pri = '🔴' if str(task.get('priority')) == 'urgent' else '🟠' if str(task.get('priority')) == 'important' else ''
    lines = [f"{kind} #{int(task.get('number', 0) or 0)} {pri}".rstrip(), str(task.get('description') or task.get('title') or 'Без названия')[:1500], '', f'Статус: {_v174_status_label(task)}']
    deadline = _v172_deadline_text(task)
    if deadline != 'не указан':
        lines.append(f'Срок: {deadline}')
    assignee = _v172_assignee_text(task)
    if assignee != 'не назначен':
        lines.append(f'Ответственный: {assignee}')
    return _v172_mark('\n'.join(lines), 'Ф249')

def _v174_compact_kb(task: dict, chat_id: int, user_id: int):
    uid = str(task.get('uid') or '')
    kb = types.InlineKeyboardMarkup()
    status = str(task.get('status') or '')
    if str(task.get('type')) == 'purchase':
        kb.row(IB(('✅ ' if status == 'ordered' else '') + '📦 Заказано', callback_data=f'v174:td:status:{uid}:ordered'), IB(('✅ ' if status == 'received' else '') + '✅ Куплено', callback_data=f'v174:td:status:{uid}:received'))
    else:
        kb.row(IB(('✅ ' if status == 'work' else '') + '▶️ В работу', callback_data=f'v174:td:status:{uid}:work'), IB(('✅ ' if status == 'done' else '') + '✅ Выполнено', callback_data=f'v174:td:status:{uid}:done'))
    kb.row(IB(('✅ ' if status == 'deferred' else '') + '⏸ Отложить', callback_data=f'v174:td:status:{uid}:deferred'), IB(('✅ ' if status == 'cancelled' else '') + '❌ Отменить', callback_data=f'v174:td:status:{uid}:cancelled'))
    kb.row(IB('✏️ Изменить', callback_data=f'v174:td:edit:{uid}'), IB('🕘 История', callback_data=f'v174:td:history:{uid}'))
    url = _v172_source_url(task)
    if url:
        kb.row(IB('💬 Исходное сообщение', url=url))
    try:
        _v172_standard_nav(kb, int(chat_id), 'v174:td:menu')
    except Exception:
        pass
    return kb

def _v174_edit_text_kb(task: dict, chat_id: int, user_id: int):
    uid = str(task.get('uid') or '')
    text = _v172_mark(f"✏️ ИЗМЕНИТЬ #{task.get('number')}\n\n{str(task.get('description') or task.get('title') or '')[:1200]}\n\n⚡ {_v172_priority_text(task)}\n📅 {_v172_deadline_text(task)}\n👤 {_v172_assignee_text(task)}", 'Ф249')
    kb = types.InlineKeyboardMarkup()
    kb.row(IB('✏️ Текст', callback_data=f'v174:td:input:{uid}:text'), IB('📅 Срок', callback_data=f'v174:td:input:{uid}:deadline'))
    kb.row(IB('⚡ Срочность', callback_data=f'v174:td:priority:{uid}'), IB('👤 Взять / снять себя', callback_data=f'v174:td:take:{uid}'))
    kb.row(IB('🏠 Объект', callback_data=f'v174:td:input:{uid}:object'), IB('💬 Комментарий', callback_data=f'v174:td:input:{uid}:comment'))
    try:
        _v172_standard_nav(kb, int(chat_id), f'v174:td:open:{uid}')
    except Exception:
        pass
    return (text, kb)

def _v212_legacy__v174_filter(task: dict, filt: str, user_id: int) -> bool:
    if task.get('deleted'):
        return False
    status = str(task.get('status') or '')
    complete = _v172_is_complete(task)
    if filt == 'active':
        return not complete and status != 'deferred'
    if filt == 'mine':
        return not complete and any((int(a.get('user_id', 0) or 0) == int(user_id or 0) for a in task.get('assignees') or [] if isinstance(a, dict)))
    if filt == 'urgent':
        return not complete and str(task.get('priority')) == 'urgent'
    if filt == 'deferred':
        return status == 'deferred'
    if filt == 'done':
        return complete and status != 'cancelled'
    if filt == 'cancelled':
        return status == 'cancelled'
    return True

def _v212_legacy__v174_list_text_kb(chat_id: int, filt: str, page: int, user_id: int):
    cid = int(chat_id)
    filt = str(filt or 'active')
    rows = [t for t in _v172_tasks_for_chat(cid) if _v174_filter(t, filt, user_id)]
    rows.sort(key=_v172_sort_key)
    per = 8
    pages = max(1, (len(rows) + per - 1) // per)
    page = max(0, min(int(page or 0), pages - 1))
    title = {'active': '📌 Активные', 'mine': '🙋 Мои', 'urgent': '🔴 Срочные', 'deferred': '⏸ Отложенные', 'done': '✅ Выполненные', 'cancelled': '❌ Отменённые'}.get(filt, '📋 Задачи')
    text = _v172_mark(f'{title}\n\nНайдено: {len(rows)}\nСтраница {page + 1}/{pages}', 'Ф248')
    kb = types.InlineKeyboardMarkup()
    for task in rows[page * per:(page + 1) * per]:
        icon = '🛒' if str(task.get('type')) == 'purchase' else '📋'
        if str(task.get('priority')) == 'urgent' and (not _v172_is_complete(task)):
            icon = '🔴'
        kb.row(IB(f"{icon} #{task.get('number')} {str(task.get('title') or '')[:39]}", callback_data=f"v174:td:open:{task.get('uid')}"))
    if pages > 1:
        kb.row(IB('◀️', callback_data=f'v174:td:list:{filt}:{(page - 1) % pages}'), IB(f'{page + 1}/{pages}', callback_data='none'), IB('▶️', callback_data=f'v174:td:list:{filt}:{(page + 1) % pages}'))
    try:
        _v172_standard_nav(kb, cid, 'v174:td:menu')
    except Exception:
        pass
    return (text, kb)

def _v174_keywords_text_kb(chat_id: int):
    cid = int(chat_id)
    s = _v174_settings(cid)
    auto = bool(s.get('auto_capture', True))
    lines = ['⚙️ КЛЮЧЕВЫЕ СЛОВА', '', f"🤖 Автоподхват: {('✅ ВКЛ' if auto else '⬜ ВЫКЛ')}", '', 'Создание задачи/покупки — если фраза встречается в сообщении.', 'Статус — только ответом на исходное сообщение/карточку или вместе с #номером.', '']
    for kind in ('task', 'purchase', 'done', 'deferred', 'cancelled', 'work'):
        words = ', '.join(_v174_keywords(cid, kind))
        lines.append(f'{_V174_KEYWORD_LABELS[kind]}: {words}')
    text = _v172_mark('\n'.join(lines)[:3900], 'Ф250')
    kb = types.InlineKeyboardMarkup()
    kb.row(IB(f"{('✅' if auto else '⬜')} 🤖 Автоподхват: {('ВКЛ' if auto else 'ВЫКЛ')}", callback_data='v174:td:auto'))
    kb.row(IB('📋 Слова задач', callback_data='v174:td:kw:task'), IB('🛒 Слова покупок', callback_data='v174:td:kw:purchase'))
    kb.row(IB('✅ Выполнено', callback_data='v174:td:kw:done'), IB('▶️ В работу', callback_data='v174:td:kw:work'))
    kb.row(IB('⏸ Отложено', callback_data='v174:td:kw:deferred'), IB('❌ Отмена', callback_data='v174:td:kw:cancelled'))
    kb.row(IB('♻️ Сбросить все слова', callback_data='v174:td:kwreset:all'))
    try:
        _v172_standard_nav(kb, cid, 'v174:td:menu')
    except Exception:
        pass
    return (text, kb)

def _v174_keyword_group_text_kb(chat_id: int, kind: str):
    cid = int(chat_id)
    kind = str(kind)
    words = _v174_keywords(cid, kind)
    text = _v172_mark(f'{_V174_KEYWORD_LABELS.get(kind, kind)} — КЛЮЧЕВЫЕ СЛОВА\n\n' + ('\n'.join((f'• {x}' for x in words)) if words else '—') + '\n\nНажмите «Заменить список» и отправьте слова через запятую.', 'Ф250')
    kb = types.InlineKeyboardMarkup()
    kb.row(IB('✏️ Заменить список', callback_data=f'v174:td:kwedit:{kind}'), IB('♻️ По умолчанию', callback_data=f'v174:td:kwreset:{kind}'))
    try:
        _v172_standard_nav(kb, cid, 'v174:td:keywords')
    except Exception:
        pass
    return (text, kb)

def _canon_v174_set_input__001(chat_id: int, user_id: int, action: str, kind: str='', task_uid: str='', message_id: int=0, prompt_id: int=0):
    with _V174_INPUT_LOCK:
        _V174_INPUT_WAIT[int(chat_id), int(user_id)] = {'action': str(action), 'kind': str(kind), 'task_uid': str(task_uid or '').upper(), 'message_id': int(message_id or 0), 'prompt_id': int(prompt_id or 0), 'created': _v174_time.time()}

def _v212_legacy__v174_prompt_input(chat_id: int, user_id: int, action: str, kind: str='', task_uid: str='', message_id: int=0):
    prompts = {'new_task': '✍️ Напишите задачу одним сообщением. Для отмены: отмена', 'new_purchase': '🛒 Напишите, что нужно купить. Для отмены: отмена', 'text': '✏️ Напишите новый текст. Для отмены: отмена', 'deadline': '📅 Введите срок: 12.08 18:00, сегодня 18:00, завтра 15:00. «нет» — убрать срок.', 'object': '🏠 Напишите объект/дом/зону. «нет» — очистить.', 'comment': '💬 Напишите комментарий. Для отмены: отмена', 'keywords': f'✏️ Отправьте новый список для «{_V174_KEYWORD_LABELS.get(kind, kind)}» через запятую.\nНапример: задача, нужно сделать, поручение\n\nДля отмены: отмена'}
    prompt_id = 0
    try:
        sent = bot.send_message(int(chat_id), prompts.get(action, 'Введите значение:'))
        prompt_id = int(getattr(sent, 'message_id', 0) or 0)
    except Exception:
        pass
    _v174_set_input(chat_id, user_id, action, kind, task_uid, message_id, prompt_id)

def _canon_v174_pop_input__001(chat_id: int, user_id: int):
    with _V174_INPUT_LOCK:
        return _V174_INPUT_WAIT.pop((int(chat_id), int(user_id)), None)

def _canon_v174_get_input__001(chat_id: int, user_id: int):
    with _V174_INPUT_LOCK:
        row = _V174_INPUT_WAIT.get((int(chat_id), int(user_id)))
        if row and _v174_time.time() - float(row.get('created', 0) or 0) > 900:
            _V174_INPUT_WAIT.pop((int(chat_id), int(user_id)), None)
            return None
        return dict(row) if row else None

def _v228_prev_v174_create_from_message(msg, kind: str, text: str=''):
    cid = int(msg.chat.id)
    user_id = int(getattr(getattr(msg, 'from_user', None), 'id', 0) or 0)
    src = getattr(msg, 'reply_to_message', None)
    source = src if src is not None else msg
    body = str(text or '').strip() or _v172_reply_text(msg) or str(getattr(msg, 'text', '') or '').strip()
    if not body:
        return None
    skey = _v172_source_key(cid, int(getattr(source, 'message_id', 0) or 0))
    existing_uid = _v172_source_root().get(skey)
    existing = _v172_task_for_uid(existing_uid) if existing_uid else None
    if isinstance(existing, dict) and (not existing.get('deleted')):
        return existing
    task = _v172_create_task(cid, 'purchase' if kind == 'purchase' else 'task', body, getattr(msg, 'from_user', None), source_msg=source)
    try:
        sent = bot.send_message(cid, _v174_compact_text(task), reply_markup=_v174_compact_kb(task, cid, user_id), reply_to_message_id=int(getattr(source, 'message_id', 0) or 0) or None)
        task['card_message_id'] = int(getattr(sent, 'message_id', 0) or 0)
        _v172_persist(cid, 'v174_compact_card')
    except Exception:
        pass
    return task

def _v174_set_status(task: dict, status: str, user=None, detail: str=''):
    if not isinstance(task, dict):
        return False
    kind = str(task.get('type') or 'task')
    allowed = {'deferred', 'cancelled'}
    allowed |= {'new', 'work', 'done'} if kind != 'purchase' else {'need', 'search', 'ordered', 'received'}
    if status not in allowed:
        return False
    task['status'] = status
    _v172_touch(task, user, 'status_changed', detail or _v174_status_label(task))
    return True

def _v228_prev_v174_refresh_card(task: dict):
    try:
        cid = int(task.get('chat_id', 0) or 0)
        mid = int(task.get('card_message_id', 0) or 0)
        if cid and mid:
            bot.edit_message_text(_v174_compact_text(task), chat_id=cid, message_id=mid, reply_markup=_v174_compact_kb(task, cid, int(task.get('updated_by', 0) or 0)))
    except Exception:
        pass

def _v174_status_target_from_message(msg):
    cid = int(msg.chat.id)
    text = str(getattr(msg, 'text', '') or '')
    m = _v174_re.search('(?:#|№)\\s*(\\d{1,7})', text)
    if m:
        task = _v174_task_by_number(cid, int(m.group(1)))
        if task:
            return task
    reply = getattr(msg, 'reply_to_message', None)
    if reply is not None:
        return _v174_task_for_reply(cid, int(getattr(reply, 'message_id', 0) or 0))
    return None

def _v212_legacy__v174_auto_process(msg) -> None:
    try:
        if str(getattr(msg, 'content_type', '') or '') != 'text':
            return
        cid = int(msg.chat.id)
        if not cid or not task_dispatcher_enabled(cid):
            return
        text = str(getattr(msg, 'text', '') or '').strip()
        if not text or text.startswith('/'):
            return
        sender = getattr(msg, 'from_user', None)
        if sender is not None and bool(getattr(sender, 'is_bot', False)):
            return
        try:
            old_input = globals().get('_v172_get_input')
            if callable(old_input) and old_input(cid, int(getattr(sender, 'id', 0) or 0)):
                return
        except Exception:
            pass
        settings = _v174_settings(cid)
        if not bool(settings.get('auto_capture', True)):
            return
        target = _v174_status_target_from_message(msg)
        if target is not None:
            status_kind = _v174_match_kind(cid, text, ('done', 'deferred', 'cancelled', 'work'))
            if status_kind:
                if status_kind == 'done':
                    status = 'received' if str(target.get('type')) == 'purchase' else 'done'
                elif status_kind == 'work':
                    status = 'search' if str(target.get('type')) == 'purchase' else 'work'
                else:
                    status = status_kind
                if _v174_set_status(target, status, sender, f'по ключевому слову: {status_kind}'):
                    _v174_refresh_card(target)
                    try:
                        bot_journal('v174_task_status_keyword', cid, f"task={target.get('number')}; status={status}; msg={getattr(msg, 'message_id', 0)}")
                    except Exception:
                        pass
                return
        create_kind = _v174_match_kind(cid, text, ('purchase', 'task'))
        if create_kind:
            skey = _v172_source_key(cid, int(getattr(msg, 'message_id', 0) or 0))
            uid = _v172_source_root().get(skey)
            if uid and _v172_task_for_uid(uid):
                return
            task = _v174_create_from_message(msg, 'purchase' if create_kind == 'purchase' else 'task', text)
            if task:
                try:
                    bot_journal('v174_task_autocaptured', cid, f"task={task.get('number')}; type={task.get('type')}; msg={getattr(msg, 'message_id', 0)}")
                except Exception:
                    pass
    except Exception as exc:
        try:
            log_error(f'v174 auto task: {exc}')
        except Exception:
            pass

def _v212_legacy__v174_handle_own_input(msg) -> bool:
    if str(getattr(msg, 'content_type', '') or '') != 'text':
        return False
    cid = int(msg.chat.id)
    uid = int(getattr(getattr(msg, 'from_user', None), 'id', 0) or 0)
    row = _v174_get_input(cid, uid)
    if not row:
        return False
    text = str(getattr(msg, 'text', '') or '').strip()
    _v174_pop_input(cid, uid)
    _v172_delete_quiet(cid, int(row.get('prompt_id', 0) or 0))
    if text.casefold() in {'отмена', 'cancel', 'стоп'}:
        try:
            send_and_auto_delete(cid, '❎ Действие отменено.', 5)
        except Exception:
            pass
        return True
    action = str(row.get('action') or '')
    user = getattr(msg, 'from_user', None)
    if action == 'keywords':
        kind = str(row.get('kind') or '')
        values = [x.strip() for x in _v174_re.split('[,;\\n]+', text) if x.strip()]
        _v174_set_keywords(cid, kind, values)
        try:
            body, kb = _v174_keyword_group_text_kb(cid, kind)
            bot.send_message(cid, body, reply_markup=kb)
        except Exception:
            pass
        _v172_delete_quiet(cid, int(getattr(msg, 'message_id', 0) or 0))
        return True
    if action in {'new_task', 'new_purchase'}:
        if not text:
            return True
        task = _v172_create_task(cid, 'purchase' if action == 'new_purchase' else 'task', text, user, source_msg=None)
        try:
            sent = bot.send_message(cid, _v174_compact_text(task), reply_markup=_v174_compact_kb(task, cid, uid))
            task['card_message_id'] = int(getattr(sent, 'message_id', 0) or 0)
            _v172_persist(cid, 'v174_manual_create')
        except Exception:
            pass
        _v172_delete_quiet(cid, int(getattr(msg, 'message_id', 0) or 0))
        return True
    task = _v172_task_for_uid(row.get('task_uid')) if row.get('task_uid') else None
    if not isinstance(task, dict) or int(task.get('chat_id', 0) or 0) != cid:
        return True
    ok = True
    if action == 'text':
        if not (_v172_is_manager(uid, cid) or uid == int(task.get('creator_user_id', 0) or 0)):
            ok = False
        else:
            task['description'] = text[:4000]
            task['title'] = _v172_title(text)
            _v172_touch(task, user, 'text_changed', text[:180])
    elif action == 'deadline':
        value = _v172_parse_deadline(text)
        if value is None:
            ok = False
            try:
                send_and_auto_delete(cid, '❌ Срок не распознан. Пример: завтра 15:00', 8)
            except Exception:
                pass
        else:
            task['deadline'] = value
            _v172_touch(task, user, 'deadline_changed', value or 'срок убран')
    elif action == 'object':
        value = '' if text.casefold() in {'нет', 'убрать', 'очистить', '-'} else text[:180]
        task['object'] = value
        _v172_touch(task, user, 'object_changed', value or 'очищено')
    elif action == 'comment':
        arr = task.setdefault('comments', [])
        arr.append({'at': _v172_iso(), 'user_id': uid, 'user': _v172_user_name(user), 'text': text[:1200]})
        if len(arr) > V172_COMMENT_KEEP:
            del arr[:-V172_COMMENT_KEEP]
        _v172_touch(task, user, 'comment_added', text[:220])
    _v172_delete_quiet(cid, int(getattr(msg, 'message_id', 0) or 0))
    if ok:
        _v174_refresh_card(task)
        mid = int(row.get('message_id', 0) or 0)
        if mid:
            try:
                bot.edit_message_text(_v174_compact_text(task), chat_id=cid, message_id=mid, reply_markup=_v174_compact_kb(task, cid, uid))
            except Exception:
                pass
    return True

def _v174_install_message_wrapper() -> int:
    for row in list(getattr(bot, 'message_handlers', []) or []):
        if not isinstance(row, dict):
            continue
        fn = row.get('function')
        if not callable(fn) or getattr(fn, '_v174_task_auto', False):
            continue
        if not (getattr(fn, '_v172_task_input', False) or getattr(fn, '__name__', '') == 'on_any_message'):
            continue

        def _wrapped_v174(msg, _original=fn):
            try:
                if _v174_handle_own_input(msg):
                    return
            except Exception as exc:
                try:
                    log_error(f'v174 keyword input: {exc}')
                except Exception:
                    pass
            try:
                _v174_auto_process(msg)
            except Exception as exc:
                try:
                    log_error(f'v174 auto process: {exc}')
                except Exception:
                    pass
            return _original(msg)
        _wrapped_v174._v174_task_auto = True
        _wrapped_v174._v172_task_input = True
        row['function'] = _wrapped_v174
        return 1
    return 0

def _v174_command_tasks(msg):
    cid = int(msg.chat.id)
    uid = int(getattr(getattr(msg, 'from_user', None), 'id', 0) or 0)
    if cid == int(OWNER_ID or 0):
        text, kb = _v174_admin_text_kb(1, 0)
        bot.send_message(cid, text, reply_markup=kb)
        return
    if not task_dispatcher_enabled(cid):
        bot.reply_to(msg, '📋 Диспетчер задач в этом чате выключен.')
        return
    text, kb = _v174_menu_text_kb(cid, uid)
    bot.send_message(cid, text, reply_markup=kb)

def _v174_command_create(msg, kind: str):
    cid = int(msg.chat.id)
    if not task_dispatcher_enabled(cid):
        bot.reply_to(msg, '📋 Диспетчер задач в этом чате выключен.')
        return
    text = _v172_command_text(msg)
    src = getattr(msg, 'reply_to_message', None)
    if src is not None:
        skey = _v172_source_key(cid, int(getattr(src, 'message_id', 0) or 0))
        old_uid = _v172_source_root().get(skey)
        old = _v172_task_for_uid(old_uid) if old_uid else None
        if isinstance(old, dict) and (not old.get('deleted')):
            try:
                bot.reply_to(msg, f"ℹ️ Уже зафиксировано как #{old.get('number')}.", reply_markup=_v174_compact_kb(old, cid, int(getattr(getattr(msg, 'from_user', None), 'id', 0) or 0)))
            except Exception:
                pass
            return
    if not text and src is None:
        _v174_prompt_input(cid, int(getattr(getattr(msg, 'from_user', None), 'id', 0) or 0), 'new_purchase' if kind == 'purchase' else 'new_task')
        return
    _v174_create_from_message(msg, kind, text)

def _v174_replace_command_handlers() -> int:
    count = 0
    for row in list(getattr(bot, 'message_handlers', []) or []):
        if not isinstance(row, dict):
            continue
        fn = row.get('function')
        name = str(getattr(fn, '__name__', ''))
        if name == 'cmd_tasks_v172':
            row['function'] = _v174_command_tasks
            count += 1
        elif name == 'cmd_task_v172':
            row['function'] = lambda msg: _v174_command_create(msg, 'task')
            count += 1
        elif name == 'cmd_buy_v172':
            row['function'] = lambda msg: _v174_command_create(msg, 'purchase')
            count += 1
    return count

def _v228_prev_v174_edit_call(call, text, kb):
    try:
        safe_edit(bot, call, text, reply_markup=kb)
    except Exception:
        try:
            fast_ui_edit_message_text(int(call.message.chat.id), int(call.message.message_id), text, reply_markup=kb, purpose='task_callback_fallback_v178')
        except Exception:
            pass

def _v212_legacy__v174_callback(call):
    raw = str(getattr(call, 'data', '') or '')
    if not raw.startswith('v174:td:'):
        return False
    parts = raw.split(':')
    action = parts[2] if len(parts) > 2 else ''
    cid = int(call.message.chat.id)
    user = getattr(call, 'from_user', None)
    uid_user = int(getattr(user, 'id', 0) or 0)
    try:
        bot.answer_callback_query(call.id)
    except Exception:
        pass
    if action == 'admin':
        if cid != int(OWNER_ID or 0):
            return True
        level = 2 if len(parts) > 3 and str(parts[3]) == '2' else 1
        page = int(parts[4]) if len(parts) > 4 and str(parts[4]).isdigit() else 0
        text, kb = _v174_admin_text_kb(level, page)
        _v174_edit_call(call, text, kb)
        return True
    if action == 'toggle':
        if cid != int(OWNER_ID or 0):
            return True
        try:
            target = int(parts[3])
            level = 2 if int(parts[4]) == 2 else 1
            page = int(parts[5])
        except Exception:
            return True
        if target not in set(_v174_circle_ids(level)):
            try:
                bot.answer_callback_query(call.id, 'Чат больше не входит в этот круг.', show_alert=True)
            except Exception:
                pass
            return True
        s = _v172_chat_settings(target)
        s['enabled'] = not bool(s.get('enabled'))
        s['updated_at'] = _v172_iso()
        s['updated_by'] = uid_user
        _v174_settings(target)
        _v172_persist(target, 'v174_dispatcher_toggle')
        try:
            if s['enabled']:
                bot.send_message(target, '✅ Диспетчер задач включён. Можно просто писать: «нужно сделать …» или «нужно купить …». Статус меняется кнопками или ответом «готово / отложить / отменить».')
        except Exception:
            pass
        try:
            schedule_main_window_recreate_after_quiet(target, delay=0.2)
        except Exception:
            pass
        text, kb = _v174_admin_text_kb(level, page)
        _v174_edit_call(call, text, kb)
        return True
    if not task_dispatcher_enabled(cid):
        try:
            bot.answer_callback_query(call.id, 'Диспетчер в этом чате выключен.', show_alert=True)
        except Exception:
            pass
        return True
    if action == 'menu':
        text, kb = _v174_menu_text_kb(cid, uid_user)
        _v174_edit_call(call, text, kb)
        return True
    if action == 'new':
        kind = parts[3] if len(parts) > 3 else 'task'
        _v174_prompt_input(cid, uid_user, 'new_purchase' if kind == 'purchase' else 'new_task', message_id=int(call.message.message_id))
        return True
    if action == 'list':
        filt = parts[3] if len(parts) > 3 else 'active'
        page = int(parts[4]) if len(parts) > 4 and str(parts[4]).isdigit() else 0
        text, kb = _v174_list_text_kb(cid, filt, page, uid_user)
        _v174_edit_call(call, text, kb)
        return True
    if action == 'keywords':
        text, kb = _v174_keywords_text_kb(cid)
        _v174_edit_call(call, text, kb)
        return True
    if action == 'auto':
        s = _v174_settings(cid)
        s['auto_capture'] = not bool(s.get('auto_capture', True))
        _v172_persist(cid, 'v174_auto_capture')
        text, kb = _v174_keywords_text_kb(cid)
        _v174_edit_call(call, text, kb)
        return True
    if action == 'kw':
        kind = parts[3] if len(parts) > 3 else 'task'
        text, kb = _v174_keyword_group_text_kb(cid, kind)
        _v174_edit_call(call, text, kb)
        return True
    if action == 'kwedit':
        kind = parts[3] if len(parts) > 3 else 'task'
        if not _v172_is_manager(uid_user, cid):
            try:
                bot.answer_callback_query(call.id, 'Ключевые слова меняет управляющий чата.', show_alert=True)
            except Exception:
                pass
            return True
        _v174_prompt_input(cid, uid_user, 'keywords', kind=kind, message_id=int(call.message.message_id))
        return True
    if action == 'kwreset':
        if not _v172_is_manager(uid_user, cid):
            return True
        kind = parts[3] if len(parts) > 3 else 'all'
        if kind == 'all':
            for k, vals in _V174_DEFAULT_KEYWORDS.items():
                _v174_set_keywords(cid, k, vals)
            text, kb = _v174_keywords_text_kb(cid)
        else:
            _v174_set_keywords(cid, kind, _V174_DEFAULT_KEYWORDS.get(kind, []))
            text, kb = _v174_keyword_group_text_kb(cid, kind)
        _v174_edit_call(call, text, kb)
        return True
    task_uid = str(parts[3]).upper() if len(parts) > 3 else ''
    task = _v172_task_for_uid(task_uid)
    if not isinstance(task, dict) or int(task.get('chat_id', 0) or 0) != cid or task.get('deleted'):
        try:
            bot.answer_callback_query(call.id, 'Задача не найдена.', show_alert=True)
        except Exception:
            pass
        return True
    if action == 'open':
        _v174_edit_call(call, _v174_compact_text(task), _v174_compact_kb(task, cid, uid_user))
        return True
    if action == 'status':
        status = parts[4] if len(parts) > 4 else ''
        if _v174_set_status(task, status, user):
            _v174_edit_call(call, _v174_compact_text(task), _v174_compact_kb(task, cid, uid_user))
        return True
    if action == 'edit':
        text, kb = _v174_edit_text_kb(task, cid, uid_user)
        _v174_edit_call(call, text, kb)
        return True
    if action == 'priority':
        order = ['normal', 'important', 'urgent']
        cur = str(task.get('priority') or 'normal')
        task['priority'] = order[(order.index(cur) + 1) % len(order)] if cur in order else 'normal'
        _v172_touch(task, user, 'priority_changed', _v172_priority_text(task))
        text, kb = _v174_edit_text_kb(task, cid, uid_user)
        _v174_edit_call(call, text, kb)
        return True
    if action == 'take':
        arr = [x for x in task.get('assignees') or [] if isinstance(x, dict)]
        mine = any((int(x.get('user_id', 0) or 0) == uid_user and uid_user for x in arr))
        if mine:
            arr = [x for x in arr if int(x.get('user_id', 0) or 0) != uid_user]
            detail = 'снял себя'
        else:
            arr.append({'user_id': uid_user, 'name': _v172_user_name(user)})
            detail = 'взял себе'
            if str(task.get('type')) != 'purchase' and str(task.get('status')) == 'new':
                task['status'] = 'work'
        task['assignees'] = arr[:10]
        _v172_touch(task, user, 'assignee_self', detail)
        text, kb = _v174_edit_text_kb(task, cid, uid_user)
        _v174_edit_call(call, text, kb)
        return True
    if action == 'input':
        field = parts[4] if len(parts) > 4 else ''
        if field in {'text', 'deadline', 'object', 'comment'}:
            _v174_prompt_input(cid, uid_user, field, task_uid=task_uid, message_id=int(call.message.message_id))
            return True
    if action == 'history':
        kb = types.InlineKeyboardMarkup()
        try:
            _v172_standard_nav(kb, cid, f'v174:td:open:{task_uid}')
        except Exception:
            pass
        _v174_edit_call(call, _v172_history_text(task), kb)
        return True
    return True

def _v174_legacy_filter(call):
    raw = str(getattr(call, 'data', '') or '')
    return any((raw.startswith(prefix) for prefix in ('v172:task:admin', 'v172:task:list:', 'v172:task:open:', 'v172:task:hist:', 'v172:task:new:', 'v172:task:search', 'v172:task:groups:')))

def _v174_legacy_callback(call):
    raw = str(getattr(call, 'data', '') or '')
    cid = int(call.message.chat.id)
    user = getattr(call, 'from_user', None)
    uid_user = int(getattr(user, 'id', 0) or 0)
    try:
        bot.answer_callback_query(call.id)
    except Exception:
        pass
    parts = raw.split(':')
    action = parts[2] if len(parts) > 2 else ''
    if action == 'admin':
        if cid == int(OWNER_ID or 0):
            text, kb = _v174_admin_text_kb(1, 0)
            _v174_edit_call(call, text, kb)
        return
    if not task_dispatcher_enabled(cid):
        return
    if action == 'open' and len(parts) > 3:
        task = _v172_task_for_uid(parts[3])
        if isinstance(task, dict) and int(task.get('chat_id', 0) or 0) == cid:
            _v174_edit_call(call, _v174_compact_text(task), _v174_compact_kb(task, cid, uid_user))
        return
    if action == 'hist' and len(parts) > 3:
        task = _v172_task_for_uid(parts[3])
        if isinstance(task, dict) and int(task.get('chat_id', 0) or 0) == cid:
            kb = types.InlineKeyboardMarkup()
            _v172_standard_nav(kb, cid, f"v174:td:open:{task.get('uid')}")
            _v174_edit_call(call, _v172_history_text(task), kb)
        return
    if action == 'new':
        kind = parts[3] if len(parts) > 3 else 'task'
        _v174_prompt_input(cid, uid_user, 'new_purchase' if kind == 'purchase' else 'new_task', message_id=int(call.message.message_id))
        return
    old_filter = parts[3] if action == 'list' and len(parts) > 3 else 'active'
    mapping = {'active': 'active', 'mine': 'mine', 'urgent': 'urgent', 'deferred': 'deferred', 'done': 'done'}
    filt = mapping.get(old_filter, 'active')
    text, kb = _v174_list_text_kb(cid, filt, 0, uid_user)
    _v174_edit_call(call, text, kb)
_V174_PREV_BUILD_MAIN_KEYBOARD = _v177_legacy_0166_build_main_keyboard

def _v212_legacy_build_main_keyboard(day_key: str, chat_id=None):
    kb = _V174_PREV_BUILD_MAIN_KEYBOARD(day_key, chat_id) if callable(_V174_PREV_BUILD_MAIN_KEYBOARD) else types.InlineKeyboardMarkup()
    try:
        cid = int(chat_id) if chat_id is not None else 0
        rows = list(getattr(kb, 'keyboard', None) or getattr(kb, 'inline_keyboard', None) or [])
        cleaned = []
        for row in rows:
            kept = []
            for b in row or []:
                cb = str(getattr(b, 'callback_data', '') or '')
                if cb.startswith('v172:task:') and str(getattr(b, 'text', '') or '') in {'📋 Задачи', '📋 Диспетчер задач'}:
                    continue
                kept.append(b)
            if kept:
                cleaned.append(kept)
        rows = cleaned
        inserts = []
        if cid and cid != int(OWNER_ID or 0) and task_dispatcher_enabled(cid):
            inserts.append(IB('📋 Задачи', callback_data='v174:td:menu'))
        if cid and cid == int(OWNER_ID or 0):
            inserts.append(IB('📋 Диспетчер задач', callback_data='v174:td:admin:1:0'))
        if inserts:
            idx = len(rows)
            for i, row in enumerate(rows):
                if any(('закры' in str(getattr(b, 'text', '') or '').casefold() for b in row)):
                    idx = i
                    break
            rows.insert(idx, inserts)
        try:
            kb.keyboard = rows
        except Exception:
            try:
                kb.inline_keyboard = rows
            except Exception:
                pass
    except Exception as exc:
        try:
            log_error(f'v174 main keyboard: {exc}')
        except Exception:
            pass
    return kb
_V174_PREV_RESTORE_VALIDATOR = _v177_legacy_0290_v153_validate_restore_gz

def _v177_legacy_0291_v153_validate_restore_gz(gz_path: str):
    try:
        return _V174_PREV_RESTORE_VALIDATOR(gz_path) if callable(_V174_PREV_RESTORE_VALIDATOR) else (None, None)
    except Exception as exc:
        if 'unsupported bot version' not in str(exc):
            raise
    import gzip, os, shutil, sqlite3, tempfile, json
    folder = tempfile.mkdtemp(prefix='v174_restore_validate_')
    raw = os.path.join(folder, 'restore.sqlite3')
    try:
        with gzip.open(gz_path, 'rb') as fin, open(raw, 'wb') as fout:
            shutil.copyfileobj(fin, fout, 1024 * 1024)
        conn = sqlite3.connect(raw)
        try:
            integrity = str(conn.execute('PRAGMA integrity_check').fetchone()[0])
            if integrity.lower() != 'ok':
                raise RuntimeError(f'SQLite integrity_check: {integrity}')
            row = conn.execute("SELECT v FROM meta WHERE kind='v153_export' AND k='manifest'").fetchone()
            if not row:
                raise RuntimeError('manifest v153 not found')
            manifest = json.loads(row[0])
        finally:
            conn.close()
        if str(manifest.get('kind')) != 'telegram_bot_full_state_v153':
            raise RuntimeError('unknown export kind')
        if int(manifest.get('schema_version') or 0) != int(V153_EXPORT_SCHEMA):
            raise RuntimeError('unsupported export schema')
        export_version = str(manifest.get('bot_version') or '')
        if not export_version.startswith(tuple((f'bot_v{i}_' for i in range(153, 175)))):
            raise RuntimeError(f"unsupported bot version: {export_version or 'missing'}")
        if _v153_db_logical_checksum(raw) != str(manifest.get('checksum') or ''):
            raise RuntimeError('checksum mismatch')
        return (manifest, raw)
    except Exception:
        shutil.rmtree(folder, ignore_errors=True)
        raise
try:
    _v177_legacy_0291_v153_validate_restore_gz.__name__ = '_v153_validate_restore_gz'
except Exception:
    pass
import hashlib as _v212_hashlib
import secrets as _v212_secrets
V212_TASK_BRANCH_LIMIT = 24

def _v212_task_branches(chat_id: int, include_deleted: bool=False) -> list[dict]:
    rows = _v174_settings(int(chat_id)).setdefault('branches_v212', [])
    out = [x for x in rows if isinstance(x, dict) and (include_deleted or not bool(x.get('deleted')))]
    out.sort(key=lambda x: (int(x.get('display_order') or 9999), str(x.get('created_at') or ''), str(x.get('branch_id') or '')))
    return out

def _v212_branch_by_id(chat_id: int, branch_id: str, include_deleted: bool=False):
    bid = str(branch_id or '')
    return next((x for x in _v212_task_branches(chat_id, include_deleted=True) if str(x.get('branch_id') or '') == bid and (include_deleted or not x.get('deleted'))), None)

def _v212_branch_label(task: dict) -> str:
    bid = str((task or {}).get('branch_id') or '')
    if not bid:
        return ''
    row = _v212_branch_by_id(int((task or {}).get('chat_id') or 0), bid, include_deleted=True)
    return str((row or {}).get('name') or (task or {}).get('branch_name_snapshot') or 'Ветка')

def _v212_match_classification(chat_id: int, text: str):
    cid = int(chat_id)
    candidates = []
    for branch in _v212_task_branches(cid):
        if not bool(branch.get('enabled', True)):
            continue
        for kw in branch.get('keywords') or []:
            if _v174_has_keyword(text, kw):
                candidates.append((len(_v174_normalize(kw)), 0, int(branch.get('display_order') or 9999), 'task', str(branch.get('branch_id') or ''), str(kw)))
    for sys_order, kind in enumerate(('purchase', 'task'), start=1):
        for kw in _v174_keywords(cid, kind):
            if _v174_has_keyword(text, kw):
                candidates.append((len(_v174_normalize(kw)), 1, sys_order, kind, '', str(kw)))
    if not candidates:
        return None
    candidates.sort(key=lambda x: (-x[0], x[1], x[2], 0 if x[3] == 'purchase' else 1, x[5].casefold()))
    length, _, _, kind, branch_id, kw = candidates[0]
    return {'kind': kind, 'branch_id': branch_id, 'keyword': kw, 'specificity': length}

def _v212_source_order_key(original_date, message_id: int) -> str:
    try:
        if hasattr(original_date, 'timestamp'):
            ts = float(original_date.timestamp())
        else:
            ts = float(original_date or 0.0)
    except Exception:
        ts = 0.0
    return f'{int(message_id or 0):012d}:{ts:020.6f}'

def _v212_task_hash(text: str, classification) -> str:
    raw = f"{str(text or '')}\n{(classification or {}).get('kind', '')}\n{(classification or {}).get('branch_id', '')}"
    return _v212_hashlib.sha256(raw.encode('utf-8', 'ignore')).hexdigest()[:24]

def _v212_task_service_text(text: str) -> bool:
    low = _v174_normalize(text)
    return low.startswith(('📋 задачи', '📋 диспетчер задач', '📋 задача №', '🛒 покупка №', '⚙️ ключевые слова', 'ф233', '✅ бот запущен'))

def _v212_send_task_card(task: dict, reply_to_message_id: int=0):
    cid = int(task.get('chat_id') or 0)
    try:
        sent = bot.send_message(cid, _v174_compact_text(task), reply_markup=_v174_compact_kb(task, cid, int(task.get('creator_user_id') or 0)), reply_to_message_id=int(reply_to_message_id or 0) or None, allow_sending_without_reply=True)
        task['card_message_id'] = int(getattr(sent, 'message_id', 0) or 0)
        _v172_persist(cid, 'v212_task_card')
    except Exception:
        pass

def task_reconcile_source_message(chat_id: int, message_id: int, text: str, *, original_date=None, sender_id: int=0, sender_name: str='', sender_is_bot: bool=False, trusted_forwarding_copy: bool=False, origin_chat_id: int=0, origin_message_id: int=0, is_edit: bool=False, previous_message_id: int=0, content_type: str='text'):
    """Single source-message reconcile: CREATE/UPDATE/RECLASSIFY/DEACTIVATE/REACTIVATE/NOOP."""
    cid, mid = (int(chat_id), int(message_id or 0))
    body = str(text or '').strip()
    if not cid or not mid or (not task_dispatcher_enabled(cid)):
        return None
    if not bool(_v174_settings(cid).get('auto_capture', True)):
        return None
    if not body or body.startswith('/'):
        return None
    if sender_is_bot and (not trusted_forwarding_copy):
        # R29: third-party bot messages are valid source data when enabled for this contour.
        try:
            if not bool(globals().get('r29_input_source_enabled', lambda _c, _k: True)(cid, 'other_bots')):
                return None
        except Exception:
            return None
    if _v212_task_service_text(body) and (not trusted_forwarding_copy):
        return None
    classification = _v212_match_classification(cid, body)
    skey = _v172_source_key(cid, mid)
    source_root = _v172_source_root()
    existing_uid = source_root.get(skey)
    if not existing_uid and int(previous_message_id or 0):
        old_key = _v172_source_key(cid, int(previous_message_id))
        existing_uid = source_root.get(old_key)
        if existing_uid:
            source_root.pop(old_key, None)
            source_root[skey] = existing_uid
    task = _v172_task_for_uid(existing_uid) if existing_uid else None
    digest = _v212_task_hash(body, classification)
    if isinstance(task, dict) and (not task.get('deleted')) and (str(task.get('source_reconcile_hash') or '') == digest) and (int(task.get('source_message_id') or 0) == mid):
        return task
    if not isinstance(task, dict) or task.get('deleted'):
        if not classification:
            return None

        class _U:
            pass

        class _C:
            pass

        class _M:
            pass
        u = _U()
        u.id = int(sender_id or 0)
        u.first_name = str(sender_name or '')
        u.last_name = ''
        u.username = ''
        u.is_bot = bool(sender_is_bot)
        c = _C()
        c.id = cid
        c.username = ''
        m = _M()
        m.message_id = mid
        m.from_user = u
        m.chat = c
        m.date = original_date
        task = _v172_create_task(cid, str(classification.get('kind') or 'task'), body, u, source_msg=m)
        first_mid = int(previous_message_id or mid)
        task.update({'source_auto': True, 'source_auto_active': True, 'source_reconcile_hash': digest, 'source_text': body, 'source_order_key': _v212_source_order_key(original_date, first_mid), 'source_original_message_id': first_mid, 'source_original_date': str(original_date or ''), 'origin_chat_id': int(origin_chat_id or 0), 'origin_message_id': int(origin_message_id or 0), 'trusted_forwarding_copy': bool(trusted_forwarding_copy), 'branch_id': str(classification.get('branch_id') or '')})
        if task.get('branch_id'):
            br = _v212_branch_by_id(cid, task['branch_id'], include_deleted=True)
            task['branch_name_snapshot'] = str((br or {}).get('name') or '')
        _v172_history(task, 'source_autocaptured', int(sender_id or 0), str(sender_name or ''), f"keyword={classification.get('keyword')}; branch={task.get('branch_id') or task.get('type')}")
        _v172_persist(cid, 'v212_source_create')
        _v212_send_task_card(task, mid)
        return task
    old_type, old_branch = (str(task.get('type') or 'task'), str(task.get('branch_id') or ''))
    task['source_message_id'] = mid
    source_root[skey] = str(task.get('uid') or existing_uid)
    if not task.get('source_order_key'):
        task['source_order_key'] = _v212_source_order_key(original_date, int(task.get('source_original_message_id') or mid))
    task['source_text'] = body
    task['description'] = body[:4000]
    task['title'] = _v172_title(body)
    task['source_reconcile_hash'] = digest
    task['origin_chat_id'] = int(origin_chat_id or task.get('origin_chat_id') or 0)
    task['origin_message_id'] = int(origin_message_id or task.get('origin_message_id') or 0)
    if classification:
        new_type = str(classification.get('kind') or 'task')
        new_branch = str(classification.get('branch_id') or '')
        was_inactive = not bool(task.get('source_auto_active', True))
        task['source_auto_active'] = True
        task['source_auto'] = True
        task['type'] = new_type
        task['branch_id'] = new_branch
        if new_branch:
            br = _v212_branch_by_id(cid, new_branch, include_deleted=True)
            task['branch_name_snapshot'] = str((br or {}).get('name') or task.get('branch_name_snapshot') or '')
        if was_inactive:
            _v172_history(task, 'source_reactivated', int(sender_id or 0), str(sender_name or ''), 'keyword returned')
        if old_type != new_type or old_branch != new_branch:
            _v172_history(task, 'source_reclassified', int(sender_id or 0), str(sender_name or ''), f"{old_type}/{old_branch or '-'} -> {new_type}/{new_branch or '-'}")
        elif is_edit and (not was_inactive):
            _v172_history(task, 'source_message_edited', int(sender_id or 0), str(sender_name or ''), body[:220])
    elif bool(task.get('source_auto_active', True)):
        task['source_auto_active'] = False
        _v172_history(task, 'source_deactivated', int(sender_id or 0), str(sender_name or ''), 'classification keywords disappeared')
    task['updated_at'] = _v172_iso()
    _v172_persist(cid, 'v212_source_reconcile')
    _v174_refresh_card(task)
    return task

def _canon_v174_auto_process__001(msg) -> None:
    try:
        cid = int(msg.chat.id)
        sender = getattr(msg, 'from_user', None)
        text = str(getattr(msg, 'text', None) or getattr(msg, 'caption', None) or '').strip()
        if not cid or not text:
            return
        if not bool(getattr(sender, 'is_bot', False)):
            target = _v174_status_target_from_message(msg)
            if target is not None:
                status_kind = _v174_match_kind(cid, text, ('done', 'deferred', 'cancelled', 'work'))
                if status_kind:
                    status = ('received' if str(target.get('type')) == 'purchase' else 'done') if status_kind == 'done' else ('search' if str(target.get('type')) == 'purchase' else 'work') if status_kind == 'work' else status_kind
                    if _v174_set_status(target, status, sender, f'по ключевому слову: {status_kind}'):
                        _v174_refresh_card(target)
                    return
        task_reconcile_source_message(cid, int(getattr(msg, 'message_id', 0) or 0), text, original_date=getattr(msg, 'date', None), sender_id=int(getattr(sender, 'id', 0) or 0), sender_name=_v172_user_name(sender) if sender else '', sender_is_bot=bool(getattr(sender, 'is_bot', False)) if sender else False, trusted_forwarding_copy=False, content_type=str(getattr(msg, 'content_type', '') or 'text'))
    except Exception as exc:
        try:
            log_error(f'v212 auto task: {exc}')
        except Exception:
            pass

def _v174_filter(task: dict, filt: str, user_id: int) -> bool:
    if task.get('deleted'):
        return False
    if bool(task.get('source_auto')) and (not bool(task.get('source_auto_active', True))) and (str(filt) not in {'cancelled', 'done'}):
        return False
    f = str(filt or 'active')
    if f.startswith('branch_'):
        return str(task.get('branch_id') or '') == f[len('branch_'):] and (not _v172_is_complete(task)) and (str(task.get('status') or '') != 'cancelled')
    status = str(task.get('status') or '')
    complete = _v172_is_complete(task)
    if f == 'active':
        return not complete and status != 'deferred'
    if f == 'mine':
        return not complete and any((int(a.get('user_id', 0) or 0) == int(user_id or 0) for a in task.get('assignees') or [] if isinstance(a, dict)))
    if f == 'urgent':
        return not complete and str(task.get('priority')) == 'urgent'
    if f == 'deferred':
        return status == 'deferred'
    if f == 'done':
        return complete and status != 'cancelled'
    if f == 'cancelled':
        return status == 'cancelled'
    return True

def _v172_sort_key(task: dict):
    source_key = str(task.get('source_order_key') or '')
    if source_key:
        return (0, source_key, int(task.get('number') or 0))
    return (1, str(task.get('created_at') or ''), int(task.get('number') or 0))

def _v174_list_text_kb(chat_id: int, filt: str, page: int, user_id: int):
    cid = int(chat_id)
    filt = str(filt or 'active')
    rows = [t for t in _v172_tasks_for_chat(cid) if _v174_filter(t, filt, user_id)]
    rows.sort(key=_v172_sort_key)
    per = 8
    pages = max(1, (len(rows) + per - 1) // per)
    page = max(0, min(int(page or 0), pages - 1))
    if filt.startswith('branch_'):
        br = _v212_branch_by_id(cid, filt[len('branch_'):], include_deleted=True)
        title = f"📂 {str((br or {}).get('name') or 'Ветка')}"
    else:
        title = {'active': '📌 Активные', 'mine': '🙋 Мои', 'urgent': '🔴 Срочные', 'deferred': '⏸ Отложенные', 'done': '✅ Выполненные', 'cancelled': '❌ Отменённые'}.get(filt, '📋 Задачи')
    text = _v172_mark(f'{title}\n\nНайдено: {len(rows)}\nСтраница {page + 1}/{pages}', 'Ф248')
    kb = types.InlineKeyboardMarkup()
    for task in rows[page * per:(page + 1) * per]:
        label = _v212_branch_label(task)
        icon = '🛒' if str(task.get('type')) == 'purchase' else '📂' if label else '📋'
        if str(task.get('priority')) == 'urgent' and (not _v172_is_complete(task)):
            icon = '🔴'
        kb.row(IB(f"{icon} #{task.get('number')} {str(task.get('title') or '')[:39]}", callback_data=f"v174:td:open:{task.get('uid')}"))
    if pages > 1:
        kb.row(IB('◀️', callback_data=f'v174:td:list:{filt}:{(page - 1) % pages}'), IB(f'{page + 1}/{pages}', callback_data='none'), IB('▶️', callback_data=f'v174:td:list:{filt}:{(page + 1) % pages}'))
    try:
        _v172_standard_nav(kb, cid, 'v174:td:menu')
    except Exception:
        pass
    return (text, kb)

def _v174_counts(chat_id: int, user_id: int=0) -> dict:
    rows = [t for t in _v172_tasks_for_chat(int(chat_id)) if not (bool(t.get('source_auto')) and (not bool(t.get('source_auto_active', True))))]
    out = {'active': 0, 'mine': 0, 'urgent': 0, 'deferred': 0, 'done': 0, 'cancelled': 0}
    for task in rows:
        status = str(task.get('status') or '')
        cancelled = status == 'cancelled'
        complete = _v172_is_complete(task)
        if cancelled:
            out['cancelled'] += 1
        elif complete:
            out['done'] += 1
        elif status == 'deferred':
            out['deferred'] += 1
        else:
            out['active'] += 1
        if not complete and str(task.get('priority')) == 'urgent':
            out['urgent'] += 1
        if not complete and any((int(a.get('user_id', 0) or 0) == int(user_id or 0) for a in task.get('assignees') or [] if isinstance(a, dict))):
            out['mine'] += 1
    return out

def _canon_v174_menu_text_kb__001(chat_id: int, user_id: int=0):
    cid = int(chat_id)
    counts = _v174_counts(cid, user_id)
    auto = bool(_v174_settings(cid).get('auto_capture', True))
    branches = _v212_task_branches(cid)
    text = _v172_mark('📋 ЗАДАЧИ\n\n' + f"📌 Активные: {counts['active']}   🔴 Срочные: {counts['urgent']}\n🙋 Мои: {counts['mine']}   ⏸ Отложенные: {counts['deferred']}\n\n🤖 Автоподхват по словам: {('✅ ВКЛ' if auto else '⬜ ВЫКЛ')}\nПользовательских веток: {len(branches)}", 'Ф248')
    kb = types.InlineKeyboardMarkup()
    kb.row(IB('➕ Задача', callback_data='v174:td:new:task'), IB('🛒 Покупка', callback_data='v174:td:new:purchase'))
    kb.row(IB(f"📌 Активные {counts['active']}", callback_data='v174:td:list:active:0'), IB(f"🙋 Мои {counts['mine']}", callback_data='v174:td:list:mine:0'))
    kb.row(IB(f"🔴 Срочные {counts['urgent']}", callback_data='v174:td:list:urgent:0'), IB(f"⏸ Отложенные {counts['deferred']}", callback_data='v174:td:list:deferred:0'))
    for br in branches[:V212_TASK_BRANCH_LIMIT]:
        cnt = sum((1 for t in _v172_tasks_for_chat(cid) if _v174_filter(t, 'branch_' + str(br.get('branch_id')), user_id)))
        kb.row(IB(f"📂 {str(br.get('name') or 'Ветка')[:38]} {cnt}", callback_data=f"v174:td:list:branch_{br.get('branch_id')}:0"), IB('⚙️', callback_data=f"v174:td:branch:open:{br.get('branch_id')}"))
    kb.row(IB('➕ Добавить ветку задач', callback_data='v174:td:branch:add'))
    kb.row(IB('✅ Выполненные', callback_data='v174:td:list:done:0'), IB('❌ Отменённые', callback_data='v174:td:list:cancelled:0'))
    kb.row(IB('⚙️ Ключевые слова', callback_data='v174:td:keywords'))
    try:
        _v172_standard_nav(kb, cid, f'd:{today_key()}:back_main')
    except Exception:
        pass
    return (text, kb)

def _v212_branch_detail(chat_id: int, branch_id: str):
    br = _v212_branch_by_id(chat_id, branch_id, include_deleted=True)
    if not br:
        return (_v172_mark('📂 Ветка не найдена', 'Ф248'), types.InlineKeyboardMarkup())
    text = _v172_mark(f"📂 ВЕТКА ЗАДАЧ\n\nНазвание: {br.get('name')}\nСостояние: {('✅ ВКЛ' if br.get('enabled', True) else '⬜ ВЫКЛ')}\nКлючевые слова: {', '.join(br.get('keywords') or []) or '—'}\nПорядок: {br.get('display_order')}", 'Ф248')
    kb = types.InlineKeyboardMarkup()
    bid = str(br.get('branch_id'))
    kb.row(IB('✏️ Переименовать', callback_data=f'v174:td:branch:rename:{bid}'), IB('🔑 Ключевые слова', callback_data=f'v174:td:branch:keywords:{bid}'))
    kb.row(IB('⬜ Выключить' if br.get('enabled', True) else '✅ Включить', callback_data=f'v174:td:branch:toggle:{bid}'))
    kb.row(IB('⬆️', callback_data=f'v174:td:branch:up:{bid}'), IB('⬇️', callback_data=f'v174:td:branch:down:{bid}'))
    kb.row(IB('🗑 Удалить ветку', callback_data=f'v174:td:branch:delete:{bid}'))
    _v172_standard_nav(kb, int(chat_id), 'v174:td:menu')
    return (text, kb)

def _v212_open_task_window(chat_id: int, user_id: int=0):
    cid = int(chat_id)
    text, kb = _v174_menu_text_kb(cid, user_id)
    try:
        reg = globals().get('_open_window_registry')
        rows = list((reg() if callable(reg) else data.get('open_window_registry') or {}).values())
        for item in rows:
            if not isinstance(item, dict) or int(item.get('chat_id') or 0) != cid:
                continue
            if str(item.get('code') or '') == 'Ф248' or str(item.get('window_type') or '') == 'tasks':
                mid = int(item.get('message_id') or 0)
                if mid:
                    try:
                        bot.edit_message_text(text, chat_id=cid, message_id=mid, reply_markup=kb)
                        return mid
                    except Exception:
                        try:
                            unregister_open_window(cid, mid)
                        except Exception:
                            pass
    except Exception:
        pass
    try:
        sent = bot.send_message(cid, text, reply_markup=kb)
        mid = int(getattr(sent, 'message_id', 0) or 0)
        try:
            register_open_window(cid, mid, 'tasks', code='Ф248', params={'task_dispatcher': True})
        except Exception:
            pass
        return mid
    except Exception:
        return 0

def _v174_admin_text_kb(level: int=1, page: int=0):
    level = 2 if int(level) == 2 else 1
    ids = _v174_circle_ids(level)
    all1, all2 = (_v174_circle_ids(1), _v174_circle_ids(2))
    per = 10
    pages = max(1, (len(ids) + per - 1) // per)
    page = max(0, min(int(page or 0), pages - 1))
    owner = int(OWNER_ID or 0)
    text = _v172_mark('📋 ДИСПЕТЧЕР ЗАДАЧ\n\n👤 Владелец имеет отдельный рабочий task-контур.\n1️⃣ Первый круг: %d\n2️⃣ Второй круг: %d\n\nСейчас: %s круг · страница %d/%d' % (len(all1), len(all2), '1-й' if level == 1 else '2-й', page + 1, pages), 'Ф247')
    kb = types.InlineKeyboardMarkup()
    kb.row(IB(('✅' if task_dispatcher_enabled(owner) else '⬜') + ' 👤 Мои задачи / Владелец', callback_data=f'v174:td:toggle:{owner}:0:{page}'))
    kb.row(IB(('✅ ' if level == 1 else '') + f'1️⃣ Первый круг ({len(all1)})', callback_data='v174:td:admin:1:0'), IB(('✅ ' if level == 2 else '') + f'2️⃣ Второй круг ({len(all2)})', callback_data='v174:td:admin:2:0'))
    for cid in ids[page * per:(page + 1) * per]:
        name = str(get_chat_display_name(cid) or f'Чат {cid}')
        kb.row(IB(('✅' if task_dispatcher_enabled(cid) else '⬜') + f' {name[:46]}', callback_data=f'v174:td:toggle:{cid}:{level}:{page}'))
    if pages > 1:
        kb.row(IB('◀️', callback_data=f'v174:td:admin:{level}:{(page - 1) % pages}'), IB(f'{page + 1}/{pages}', callback_data='none'), IB('▶️', callback_data=f'v174:td:admin:{level}:{(page + 1) % pages}'))
    try:
        _v172_standard_nav(kb, owner, f'd:{today_key()}:back_main')
    except Exception:
        pass
    return (text, kb)
_V212_PREV_TASK_INPUT = _v212_legacy__v174_handle_own_input

def _v228_prev_v174_handle_own_input(msg) -> bool:
    try:
        if str(getattr(msg, 'content_type', '') or '') != 'text':
            return _V212_PREV_TASK_INPUT(msg)
        cid = int(msg.chat.id)
        uid = int(getattr(getattr(msg, 'from_user', None), 'id', 0) or 0)
        row = _v174_get_input(cid, uid)
        if not row or not str(row.get('action') or '').startswith('branch_'):
            return _V212_PREV_TASK_INPUT(msg)
        text = str(getattr(msg, 'text', '') or '').strip()
        _v174_pop_input(cid, uid)
        _v172_delete_quiet(cid, int(row.get('prompt_id') or 0))
        if text.casefold() in {'отмена', 'cancel', 'стоп'}:
            send_and_auto_delete(cid, '❎ Действие отменено.', 5)
            return True
        action = str(row.get('action'))
        bid = str(row.get('kind') or '')
        if action == 'branch_name':
            name = ' '.join(text.split())[:80]
            if not name:
                return True
            _v174_prompt_input(cid, uid, 'branch_keywords', kind='NEW|' + name, message_id=int(row.get('message_id') or 0))
            return True
        if action == 'branch_keywords':
            values = [x.strip()[:80] for x in _v174_re.split('[,;\\n]+', text) if x.strip()]
            if bid.startswith('NEW|'):
                name = bid[4:][:80]
                branches = _v174_settings(cid).setdefault('branches_v212', [])
                branch_id = _v212_secrets.token_hex(4)
                order = max([int(x.get('display_order') or 0) for x in branches if isinstance(x, dict)] or [0]) + 1
                branches.append({'branch_id': branch_id, 'name': name, 'keywords': values[:30], 'enabled': True, 'display_order': order, 'created_at': _v172_iso(), 'updated_at': _v172_iso()})
                _v172_persist(cid, 'v212_branch_create')
            else:
                br = _v212_branch_by_id(cid, bid)
                if br:
                    br['keywords'] = values[:30]
                    br['updated_at'] = _v172_iso()
                    _v172_persist(cid, 'v212_branch_keywords')
            try:
                body, kb = _v174_menu_text_kb(cid, uid)
                bot.send_message(cid, body, reply_markup=kb)
            except Exception:
                pass
            return True
        br = _v212_branch_by_id(cid, bid)
        if not br:
            return True
        if action == 'branch_rename':
            br['name'] = ' '.join(text.split())[:80]
            br['updated_at'] = _v172_iso()
            _v172_persist(cid, 'v212_branch_rename')
        return True
    except Exception as exc:
        try:
            log_error(f'v212 branch input: {exc}')
        except Exception:
            pass
        return True
_V212_PREV_TASK_PROMPT = _v212_legacy__v174_prompt_input

def _v228_prev_v174_prompt_input(chat_id: int, user_id: int, action: str, kind: str='', task_uid: str='', message_id: int=0):
    if str(action).startswith('branch_'):
        prompts = {'branch_name': '📂 Введите название новой ветки задач.', 'branch_keywords': '🔑 Введите ключевые слова через запятую.', 'branch_rename': '✏️ Введите новое название ветки.'}
        try:
            sent = bot.send_message(int(chat_id), prompts.get(str(action), 'Введите значение:'))
            pid = int(getattr(sent, 'message_id', 0) or 0)
        except Exception:
            pid = 0
        _v174_set_input(chat_id, user_id, action, kind, task_uid, message_id, pid)
        return
    return _V212_PREV_TASK_PROMPT(chat_id, user_id, action, kind, task_uid, message_id)
_V212_PREV_TD_CALLBACK = _v212_legacy__v174_callback

def _canon_v174_callback__001(call):
    raw = str(getattr(call, 'data', '') or '')
    parts = raw.split(':')
    action = parts[2] if len(parts) > 2 else ''
    cid = int(call.message.chat.id)
    uid = int(getattr(getattr(call, 'from_user', None), 'id', 0) or 0)
    if raw.startswith('v174:td:toggle:'):
        try:
            bot.answer_callback_query(call.id)
        except Exception:
            pass
        if cid != int(OWNER_ID or 0):
            return True
        try:
            target = int(parts[3])
            level = int(parts[4])
            page = int(parts[5])
        except Exception:
            return True
        if target != int(OWNER_ID or 0) and target not in set(_v174_circle_ids(2 if level == 2 else 1)):
            try:
                bot.answer_callback_query(call.id, 'Чат больше не входит в этот круг.', show_alert=True)
            except Exception:
                pass
            return True
        s = _v172_chat_settings(target)
        s['enabled'] = not bool(s.get('enabled'))
        s['updated_at'] = _v172_iso()
        s['updated_by'] = uid
        _v174_settings(target)
        _v172_persist(target, 'v212_dispatcher_toggle')
        if s['enabled']:
            _v212_open_task_window(target, uid if target == int(OWNER_ID or 0) else 0)
        try:
            schedule_main_window_recreate_after_quiet(target, delay=0.2)
        except Exception:
            pass
        text, kb = _v174_admin_text_kb(1 if level not in {1, 2} else level, page)
        _v174_edit_call(call, text, kb)
        return True
    if raw.startswith('v174:td:branch:'):
        try:
            bot.answer_callback_query(call.id)
        except Exception:
            pass
        if not task_dispatcher_enabled(cid):
            return True
        cmd = parts[3] if len(parts) > 3 else ''
        bid = parts[4] if len(parts) > 4 else ''
        if cmd == 'add':
            if not (_v172_is_manager(uid, cid) or uid == int(OWNER_ID or 0)):
                return True
            if len(_v212_task_branches(cid)) >= V212_TASK_BRANCH_LIMIT:
                try:
                    bot.answer_callback_query(call.id, f'Лимит веток: {V212_TASK_BRANCH_LIMIT}', show_alert=True)
                except Exception:
                    pass
                return True
            _v174_prompt_input(cid, uid, 'branch_name', message_id=int(call.message.message_id))
            return True
        br = _v212_branch_by_id(cid, bid, include_deleted=True)
        if cmd == 'open':
            text, kb = _v212_branch_detail(cid, bid)
            _v174_edit_call(call, text, kb)
            return True
        if not br or (not _v172_is_manager(uid, cid) and uid != int(OWNER_ID or 0)):
            return True
        if cmd == 'rename':
            _v174_prompt_input(cid, uid, 'branch_rename', kind=bid, message_id=int(call.message.message_id))
            return True
        if cmd == 'keywords':
            _v174_prompt_input(cid, uid, 'branch_keywords', kind=bid, message_id=int(call.message.message_id))
            return True
        if cmd == 'toggle':
            br['enabled'] = not bool(br.get('enabled', True))
        elif cmd == 'delete':
            br['deleted'] = True
            br['enabled'] = False
        elif cmd in {'up', 'down'}:
            rows = _v212_task_branches(cid)
            idx = next((i for i, x in enumerate(rows) if str(x.get('branch_id')) == bid), -1)
            target = idx - 1 if cmd == 'up' else idx + 1
            if idx >= 0 and 0 <= target < len(rows):
                rows[idx]['display_order'], rows[target]['display_order'] = (rows[target].get('display_order'), rows[idx].get('display_order'))
        br['updated_at'] = _v172_iso()
        _v172_persist(cid, 'v212_branch_' + cmd)
        text, kb = _v174_menu_text_kb(cid, uid)
        _v174_edit_call(call, text, kb)
        return True
    return _V212_PREV_TD_CALLBACK(call)
_V212_PREV_BUILD_MAIN_KEYBOARD = _v212_legacy_build_main_keyboard

def _canon_build_main_keyboard__001(day_key: str, chat_id=None):
    kb = _V212_PREV_BUILD_MAIN_KEYBOARD(day_key, chat_id)
    try:
        cid = int(chat_id) if chat_id is not None else 0
        rows = list(getattr(kb, 'keyboard', None) or getattr(kb, 'inline_keyboard', None) or [])
        cleaned = []
        for row in rows:
            kept = [b for b in row or [] if str(getattr(b, 'text', '') or '') not in {'📋 Мои задачи', '📋 Диспетчер задач'}]
            if kept:
                cleaned.append(kept)
        if cid == int(OWNER_ID or 0):
            insert = []
            if task_dispatcher_enabled(cid):
                insert.append(IB('📋 Мои задачи', callback_data='v174:td:menu'))
            insert.append(IB('📋 Диспетчер задач', callback_data='v174:td:admin:1:0'))
            cleaned.insert(max(0, len(cleaned) - 1), insert)
        try:
            kb.keyboard = cleaned
        except Exception:
            try:
                kb.inline_keyboard = cleaned
            except Exception:
                pass
    except Exception:
        pass
    return kb
_V174_MESSAGE_WRAP = _v174_install_message_wrapper()
_V174_COMMAND_REPLACED = _v174_replace_command_handlers()
_V174_CALLBACK = 0
_V174_LEGACY_CALLBACK = 0
try:
    _v177_legacy_0007_bot_journal('v174_installed', int(OWNER_ID or 0), f'simple_tasks=1; circles1={len(_v174_circle_ids(1))}; circles2={len(_v174_circle_ids(2))}; message_wrap={_V174_MESSAGE_WRAP}; commands={_V174_COMMAND_REPLACED}; callback={_V174_CALLBACK}; legacy={_V174_LEGACY_CALLBACK}')
except Exception:
    pass

def _canon_task_dispatcher_callback_final__001(call) -> bool:
    """v179 single task callback surface; supports both v174 current and v172 legacy buttons."""
    raw = str(getattr(call, 'data', '') or '')
    try:
        resolver = globals().get('resolve_short_callback')
        if callable(resolver):
            raw = str(resolver(raw) or raw)
    except Exception:
        pass
    if raw.startswith('v174:td:'):
        _v174_callback(call)
        return True
    if raw.startswith('v172:task:'):
        if _v174_legacy_filter(call):
            _v174_legacy_callback(call)
            return True
        _v172_callback(call)
        return True
    return False
import secrets as _v213_secrets
import time as _v213_time
V213_INPUT_FLOW_MARKER = 'Ф252'
V213_NEUTRAL_HOME_MARKER = 'Ф253'
V213_INPUT_DEFAULT_SECONDS = 300
V213_INPUT_CHOICES_SECONDS = (60, 180, 300, 600, 900, 1800)
try:
    INTERNAL_TIMER_DEFS.setdefault('interactive_input_idle', {'label': '⏰ Ожидание ввода · автоотмена', 'default': 300, 'min': 60, 'max': 1800})
    WINDOW_MARKER_CONSTANTS.setdefault('v213:input:cancel:*:*', V213_INPUT_FLOW_MARKER)
    WINDOW_MARKER_CONSTANTS.setdefault('v213:itmr_input:*', 'Ф184')
    WINDOW_MARKER_CONSTANTS.setdefault('contour_neutral_home_v213', V213_NEUTRAL_HOME_MARKER)
except Exception:
    pass

def _v213_input_timeout_seconds() -> float:
    try:
        return float(internal_timer_seconds('interactive_input_idle', V213_INPUT_DEFAULT_SECONDS))
    except Exception:
        return float(V213_INPUT_DEFAULT_SECONDS)

def _v213_input_sid() -> str:
    return _v213_secrets.token_hex(6)

def _canon_v213_cancel_markup__001(flow: str, sid: str):
    kb = types.InlineKeyboardMarkup()
    kb.row(IB('Отмена', callback_data=f'v213:input:cancel:{str(flow)[:12]}:{str(sid)[:12]}'))
    return kb

def _v213_prompt_text(text: str) -> str:
    try:
        return window_mark(strip_window_mark(str(text or '')), V213_INPUT_FLOW_MARKER)
    except Exception:
        return str(text or '') + f'\n\n{V213_INPUT_FLOW_MARKER} ⏰'

def contour_visible_finance_enabled(chat_id: int) -> bool:
    try:
        return bool(is_finance_mode(int(chat_id)) and finance_window_mode(int(chat_id)) in {'normal', 'open', 'first'})
    except Exception:
        return False

def resolve_contour_home(chat_id: int) -> str:
    cid = int(chat_id)
    try:
        directive_fn = globals().get('directive_chat_enabled_v223')
        if callable(directive_fn) and directive_fn(cid):
            modes = []
            mode_fn = globals().get('_v215_mode_enabled')
            for mode in ('finance', 'forward', 'reminders', 'tasks'):
                try:
                    if callable(mode_fn) and mode_fn(cid, mode):
                        modes.append(mode)
                except Exception:
                    pass
            if len(modes) == 1:
                return modes[0]
            if len(modes) > 1:
                return 'selector'
            return 'neutral'
    except Exception:
        pass
    if contour_visible_finance_enabled(cid):
        return 'finance'
    try:
        if task_dispatcher_enabled(cid):
            return 'tasks'
    except Exception:
        pass
    return 'neutral'

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

def _v213_show_task_home(chat_id: int, user_id: int=0, current_message_id: int=0) -> int:
    cid = int(chat_id)
    uid = int(user_id or 0)
    mid = int(current_message_id or 0)
    text, kb = _v174_menu_text_kb(cid, uid)
    if mid:
        try:
            result = fast_ui_edit_message_text(cid, mid, text, reply_markup=kb, purpose='contour_home_tasks_v213')
            if result in {'ok', 'scheduled'}:
                try:
                    register_open_window(cid, mid, 'tasks', code='Ф248', params={'task_dispatcher': True, 'contour_home': True})
                except Exception:
                    pass
                _v213_clear_finance_active_pointer(cid)
                return mid
            if result == 'not_found':
                try:
                    unregister_open_window(cid, mid)
                except Exception:
                    pass
        except Exception:
            pass
    out = int(_v212_open_task_window(cid, uid) or 0)
    _v213_clear_finance_active_pointer(cid)
    return out

def _canon_v213_show_neutral_home__001(chat_id: int, current_message_id: int=0) -> int:
    cid = int(chat_id)
    mid = int(current_message_id or 0)
    text = window_mark('ℹ️ В этом контуре сейчас не включено ни одного видимого рабочего режима.', V213_NEUTRAL_HOME_MARKER)
    kb = types.InlineKeyboardMarkup()
    kb.row(IB('❌ Закрыть', callback_data='aux_close'))
    if mid:
        try:
            result = fast_ui_edit_message_text(cid, mid, text, reply_markup=kb, purpose='contour_home_neutral_v213')
            if result in {'ok', 'scheduled'}:
                _v213_clear_finance_active_pointer(cid)
                return mid
        except Exception:
            pass
    try:
        sent = bot.send_message(cid, text, reply_markup=kb)
        _v213_clear_finance_active_pointer(cid)
        return int(getattr(sent, 'message_id', 0) or 0)
    except Exception:
        return 0

def _v224_show_forward_home(chat_id: int, user_id: int=0, current_message_id: int=0) -> int:
    cid = int(chat_id)
    mid = int(current_message_id or 0)
    text = window_mark('📤 ПЕРЕСЫЛКА\n\n✅ Пересылка разрешена владельцем для этого чата.\nПравила работают автоматически; пользовательские настройки режима заблокированы директивной политикой.', V217_FORWARD_SCOPE_MARKER if 'V217_FORWARD_SCOPE_MARKER' in globals() else 'Ф258')
    kb = types.InlineKeyboardMarkup()
    kb.row(IB('❌ Закрыть', callback_data='aux_close'))
    return _v215_edit_or_send(cid, mid, text, kb, 'directive_forward_home_v224')

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

def v224_open_directive_mode_home(chat_id: int, user_id: int, current_message_id: int, mode: str) -> int:
    cid = int(chat_id)
    uid = int(user_id or 0)
    mid = int(current_message_id or 0)
    mode = str(mode or '')
    if mode == 'finance':
        day = str(get_chat_store(cid).get('current_view_day') or today_key())[:10]
        _V213_PREV_RETURN_TO_MAIN(cid, day, current_message_id=mid or None)
        try:
            return int(get_active_window_id(cid, day) or mid or 0)
        except Exception:
            return int(mid or 0)
    if mode == 'tasks':
        return int(_v213_show_task_home(cid, uid, mid) or 0)
    if mode == 'reminders':
        return int(_v224_show_reminders_home(cid, uid, mid) or 0)
    if mode == 'forward':
        return int(_v224_show_forward_home(cid, uid, mid) or 0)
    return int(_v213_show_neutral_home(cid, mid) or 0)

def open_resolved_contour_home(chat_id: int, user_id: int=0, current_message_id: int=0, day_key: str='') -> str:
    cid = int(chat_id)
    uid = int(user_id or 0)
    mid = int(current_message_id or 0)
    home = resolve_contour_home(cid)
    if home == 'selector':
        show_contour_start_modes(cid, uid, mid)
    elif home in {'finance', 'tasks', 'forward', 'reminders'}:
        v224_open_directive_mode_home(cid, uid, mid, home) if bool(globals().get('directive_chat_enabled_v223', lambda _c: False)(cid)) else _V213_PREV_RETURN_TO_MAIN(cid, str(day_key or get_chat_store(cid).get('current_view_day') or today_key())[:10], current_message_id=mid or None) if home == 'finance' else _v213_show_task_home(cid, uid, mid)
    else:
        _v213_show_neutral_home(cid, mid)
    try:
        bot_journal('contour_home_v224' if bool(globals().get('directive_chat_enabled_v223', lambda _c: False)(cid)) else 'contour_home_v213', cid, f'home={home}; msg={mid}')
    except Exception:
        pass
    return home
_V213_PREV_RETURN_TO_MAIN = _canon_return_to_main_window_closing_previous__001

def _canon_return_to_main_window_closing_previous__002(chat_id: int, day_key: str, current_message_id: int | None=None):
    cid = int(chat_id)
    if resolve_contour_home(cid) == 'finance':
        return _V213_PREV_RETURN_TO_MAIN(cid, str(day_key), current_message_id=current_message_id)
    return open_resolved_contour_home(cid, 0, int(current_message_id or 0), str(day_key))
_V213_PREV_CRITICAL_CALLBACK = _canon_v161_critical_callback__001

def _canon_v161_critical_callback__002(call, resolved: str) -> bool:
    raw = str(resolved or '')
    try:
        cid = int(call.message.chat.id)
        uid = int(getattr(getattr(call, 'from_user', None), 'id', 0) or 0)
        mid = int(call.message.message_id)
    except Exception:
        return _V213_PREV_CRITICAL_CALLBACK(call, resolved)
    home = resolve_contour_home(cid)
    if home != 'finance' and (raw == 'nav_prev' or (raw.startswith('d:') and raw.endswith(':back_main'))):
        try:
            _v161_ack(call)
        except Exception:
            pass
        day = get_chat_store(cid).get('current_view_day') or today_key()
        open_resolved_contour_home(cid, uid, mid, str(day))
        return True
    return _V213_PREV_CRITICAL_CALLBACK(call, resolved)

def _canon_contour_callback_guard__001(call, resolved: str) -> bool:
    """Block stale finance callbacks in contours without a visible finance interface."""
    raw = str(resolved or '')
    try:
        cid = int(call.message.chat.id)
    except Exception:
        return False
    if contour_visible_finance_enabled(cid):
        return False
    finance_surface = raw.startswith(('d:', 'c:', 'main_close:', 'remaining_open:'))
    if not finance_surface:
        return False
    if raw.startswith('d:') and any((token in raw for token in ('fin_mode_', 'qb_mode_', 'qb_hidden_', 'qb_finwin_', 'forward_finmode'))):
        return False
    try:
        bot.answer_callback_query(call.id, 'Этот режим в данном контуре выключен', show_alert=False)
    except Exception:
        pass
    try:
        _, day, _ = raw.split(':', 2) if raw.startswith('d:') else ('', today_key(), '')
    except Exception:
        day = today_key()
    uid = int(getattr(getattr(call, 'from_user', None), 'id', 0) or 0)
    open_resolved_contour_home(cid, uid, int(getattr(call.message, 'message_id', 0) or 0), str(day))
    try:
        bot_journal('contour_finance_blocked_v213', cid, f'action={raw}; home={resolve_contour_home(cid)}', 'INFO')
    except Exception:
        pass
    return True
_V213_PREV_START_HANDLER = _v161_cmd_start

def _v213_cmd_start_contour(msg):
    try:
        cid = int(msg.chat.id)
        uid = int(getattr(getattr(msg, 'from_user', None), 'id', 0) or 0)
    except Exception:
        return _V213_PREV_START_HANDLER(msg)
    home = resolve_contour_home(cid)
    if home == 'finance':
        return _V213_PREV_START_HANDLER(msg)
    try:
        update_chat_info_from_message(msg)
    except Exception:
        pass
    try:
        schedule_command_delete(msg)
    except Exception:
        pass
    try:
        if 'tenant_handle_start_payload' in globals() and tenant_handle_start_payload(msg):
            return
    except Exception:
        pass
    if home == 'tasks':
        _v213_show_task_home(cid, uid, 0)
    else:
        _v213_show_neutral_home(cid, 0)
    try:
        bot_journal('start_contour_v213', cid, f'home={home}')
    except Exception:
        pass

def _v213_replace_start_handler() -> int:
    count = 0
    for row in list(getattr(bot, 'message_handlers', []) or []):
        if not isinstance(row, dict):
            continue
        fn = row.get('function')
        if fn is _V213_PREV_START_HANDLER or str(getattr(fn, '__name__', '')) == '_v161_cmd_start':
            row['function'] = _v213_cmd_start_contour
            count += 1
    return count
_V213_PREV_STARTUP_WINDOWS = _canon_schedule_startup_main_windows__001

def _canon_schedule_startup_main_windows__002(delay: float=3.0):

    def _job():
        ids = set()
        try:
            ids.update((int(x) for x in collect_finance_chat_ids()))
        except Exception:
            pass
        try:
            ids.update((int(k) for k, v in (_v172_settings_root() or {}).items() if isinstance(v, dict) and bool(v.get('enabled'))))
        except Exception:
            pass
        try:
            ids.add(int(OWNER_ID or 0))
        except Exception:
            pass
        for cid in sorted((x for x in ids if x)):
            try:
                if is_chat_bot_removed(cid):
                    continue
                home = resolve_contour_home(cid)
                if home == 'finance':
                    store = get_chat_store(cid)
                    state = _finance_window_state(cid)
                    mode = finance_window_mode(cid)
                    if not bool(state.get('auto_reopen_on_boot', False)):
                        continue
                    day = store.get('current_view_day') or today_key()
                    if mode == 'normal':
                        update_or_send_day_window(cid, day)
                    elif mode in {'open', 'first'}:
                        if store.get('balance_panel_id'):
                            refresh_balance_panel_now(cid)
                        else:
                            send_minimized_balance_panel(cid)
                        if mode == 'first':
                            schedule_quick_balance_first_recreate(cid, 60.0)
                elif home == 'tasks':
                    _v213_show_task_home(cid, 0, 0)
                else:
                    _v213_clear_finance_active_pointer(cid)
                _v213_time.sleep(0.05)
            except Exception as exc:
                try:
                    log_error(f'startup_contour_home_v213({cid}): {exc}')
                except Exception:
                    pass
    try:
        DELAYED_SCHEDULER.schedule('startup-main-windows', float(delay), _job)
    except Exception as exc:
        try:
            log_error(f'schedule_startup_contour_home_v213: {exc}')
        except Exception:
            pass
_V213_PREV_FIN_MODE_CHOICE = _canon_apply_finance_window_mode_choice__001

def _canon_apply_finance_window_mode_choice__002(chat_id: int, selected_mode: str) -> str:
    result = _V213_PREV_FIN_MODE_CHOICE(int(chat_id), selected_mode)
    try:
        if result == 'off':
            DELAYED_SCHEDULER.schedule(f'contour-home-mode:{int(chat_id)}', 0.1, lambda cid=int(chat_id): open_resolved_contour_home(cid, 0, 0))
    except Exception:
        pass
    return result

def schedule_contour_home_after_mode_change(chat_id: int, reason: str='mode_change', delay: float=0.15) -> None:
    cid = int(chat_id)

    def _job():
        try:
            open_resolved_contour_home(cid, 0, 0)
        except Exception as exc:
            try:
                log_error(f'contour home after mode {cid}: {exc}')
            except Exception:
                pass
    try:
        DELAYED_SCHEDULER.cancel(f'contour-home-mode:{cid}')
        DELAYED_SCHEDULER.schedule(f'contour-home-mode:{cid}', float(delay), _job)
        bot_journal('contour_home_scheduled_v213', cid, f'reason={reason}')
    except Exception:
        pass

def _v213_task_input_key(chat_id: int, user_id: int, legacy: bool=False) -> str:
    return f"v213-input-{('v172' if legacy else 'v174')}:{int(chat_id)}:{int(user_id)}"

def _canon_v213_task_input_timeout__001(chat_id: int, user_id: int, sid: str, legacy: bool=False):
    lock = _V172_INPUT_LOCK if legacy else _V174_INPUT_LOCK
    root = _V172_INPUT_WAIT if legacy else _V174_INPUT_WAIT
    key = (int(chat_id), int(user_id))
    with lock:
        row = root.get(key)
        if not isinstance(row, dict) or str(row.get('session_id') or '') != str(sid):
            return False
        root.pop(key, None)
    _v172_delete_quiet(int(chat_id), int(row.get('prompt_id') or 0))
    try:
        send_and_auto_delete(int(chat_id), '⌛ Ввод отменён по таймеру.', 7)
    except Exception:
        pass
    try:
        bot_journal('input_timeout_v213', int(chat_id), f"flow={('v172' if legacy else 'v174')}; action={row.get('action')}; user={int(user_id)}")
    except Exception:
        pass
    return True
_V213_PREV_V174_SET_INPUT = _canon_v174_set_input__001

def _v213_v174_set_input(chat_id: int, user_id: int, action: str, kind: str='', task_uid: str='', message_id: int=0, prompt_id: int=0):
    cid, uid = (int(chat_id), int(user_id))
    sid = _v213_input_sid()
    delay = _v213_input_timeout_seconds()
    with _V174_INPUT_LOCK:
        _V174_INPUT_WAIT[cid, uid] = {'action': str(action), 'kind': str(kind), 'task_uid': str(task_uid or '').upper(), 'message_id': int(message_id or 0), 'prompt_id': int(prompt_id or 0), 'created': _v213_time.time(), 'last_activity': _v213_time.time(), 'session_id': sid, 'generation': 1}
    key = _v213_task_input_key(cid, uid, False)
    DELAYED_SCHEDULER.cancel(key)
    DELAYED_SCHEDULER.schedule(key, delay, _v213_task_input_timeout, cid, uid, sid, False)
    return sid
_V213_PREV_V174_POP_INPUT = _canon_v174_pop_input__001

def _v213_v174_pop_input(chat_id: int, user_id: int):
    cid, uid = (int(chat_id), int(user_id))
    try:
        DELAYED_SCHEDULER.cancel(_v213_task_input_key(cid, uid, False))
    except Exception:
        pass
    with _V174_INPUT_LOCK:
        return _V174_INPUT_WAIT.pop((cid, uid), None)

def _v213_v174_get_input(chat_id: int, user_id: int):
    cid, uid = (int(chat_id), int(user_id))
    with _V174_INPUT_LOCK:
        row = _V174_INPUT_WAIT.get((cid, uid))
        return dict(row) if isinstance(row, dict) else None
_V213_TASK_PROMPTS = {'new_task': '✍️ Напишите задачу одним сообщением.', 'new_purchase': '🛒 Напишите, что нужно купить.', 'text': '✏️ Напишите новый текст.', 'deadline': '📅 Введите срок: 12.08 18:00, сегодня 18:00, завтра 15:00. «нет» — убрать срок.', 'object': '🏠 Напишите объект/дом/зону. «нет» — очистить.', 'comment': '💬 Напишите комментарий.', 'keywords': '✏️ Отправьте новый список ключевых слов через запятую.', 'branch_name': '📂 Введите название новой ветки задач.', 'branch_keywords': '🔑 Введите ключевые слова через запятую.', 'branch_rename': '✏️ Введите новое название ветки.'}

def _v213_v174_prompt_input(chat_id: int, user_id: int, action: str, kind: str='', task_uid: str='', message_id: int=0):
    cid, uid = (int(chat_id), int(user_id))
    sid = _v213_input_sid()
    prompt = _V213_TASK_PROMPTS.get(str(action), 'Введите значение:')
    if str(action) == 'keywords':
        prompt = f'✏️ Отправьте новый список для «{_V174_KEYWORD_LABELS.get(kind, kind)}» через запятую.'
    text = _v213_prompt_text(prompt + f'\n\nАвтоотмена: {_format_duration_short(_v213_input_timeout_seconds())}.')
    pid = 0
    try:
        sent = bot.send_message(cid, text, reply_markup=_v213_cancel_markup('task', sid))
        pid = int(getattr(sent, 'message_id', 0) or 0)
    except Exception:
        pass
    _v174_set_input(cid, uid, action, kind, task_uid, message_id, pid)
    with _V174_INPUT_LOCK:
        row = _V174_INPUT_WAIT.get((cid, uid))
        if isinstance(row, dict):
            row['session_id'] = sid
    key = _v213_task_input_key(cid, uid, False)
    DELAYED_SCHEDULER.cancel(key)
    DELAYED_SCHEDULER.schedule(key, _v213_input_timeout_seconds(), _v213_task_input_timeout, cid, uid, sid, False)
    return sid
_V213_PREV_V172_SET_INPUT = _canon_v172_set_input__001

def _v213_v172_set_input(chat_id: int, user_id: int, action: str, uid: str='', message_id: int=0, prompt_id: int=0):
    cid, actor = (int(chat_id), int(user_id))
    sid = _v213_input_sid()
    with _V172_INPUT_LOCK:
        _V172_INPUT_WAIT[cid, actor] = {'action': str(action), 'uid': str(uid or '').upper(), 'message_id': int(message_id or 0), 'prompt_id': int(prompt_id or 0), 'created': _v213_time.time(), 'session_id': sid}
    key = _v213_task_input_key(cid, actor, True)
    DELAYED_SCHEDULER.cancel(key)
    DELAYED_SCHEDULER.schedule(key, _v213_input_timeout_seconds(), _v213_task_input_timeout, cid, actor, sid, True)
    return sid

def _v213_v172_get_input(chat_id: int, user_id: int):
    with _V172_INPUT_LOCK:
        row = _V172_INPUT_WAIT.get((int(chat_id), int(user_id)))
        return dict(row) if isinstance(row, dict) else None

def _v213_v172_clear_input(chat_id: int, user_id: int):
    cid, uid = (int(chat_id), int(user_id))
    try:
        DELAYED_SCHEDULER.cancel(_v213_task_input_key(cid, uid, True))
    except Exception:
        pass
    with _V172_INPUT_LOCK:
        return _V172_INPUT_WAIT.pop((cid, uid), None)
_V213_PREV_V172_PROMPT = _canon_v172_prompt__001

def _v213_v172_prompt(chat_id: int, user_id: int, action: str, uid: str='', message_id: int=0):
    cid, actor = (int(chat_id), int(user_id))
    sid = _v213_input_sid()
    prompts = {'new_task': '✍️ Напишите текст новой задачи.', 'new_purchase': '🛒 Напишите, что нужно купить.', 'text': '✏️ Напишите новый текст задачи.', 'object': '🏠 Напишите объект/дом/зону. «нет» — очистить.', 'deadline': '📅 Введите срок. «нет» — убрать срок.', 'assign': '👥 Напишите ответственных через запятую. «нет» — снять всех.', 'comment': '💬 Напишите комментарий.', 'cost': '💰 Напишите стоимость/бюджет. «нет» — очистить.', 'search': '🔎 Напишите слово или фразу для поиска.'}
    pid = 0
    try:
        sent = bot.send_message(cid, _v213_prompt_text(prompts.get(action, 'Введите значение:') + f'\n\nАвтоотмена: {_format_duration_short(_v213_input_timeout_seconds())}.'), reply_markup=_v213_cancel_markup('tasklegacy', sid))
        pid = int(getattr(sent, 'message_id', 0) or 0)
    except Exception:
        pass
    _v172_set_input(cid, actor, action, uid, message_id, pid)
    with _V172_INPUT_LOCK:
        row = _V172_INPUT_WAIT.get((cid, actor))
        if isinstance(row, dict):
            row['session_id'] = sid
    key = _v213_task_input_key(cid, actor, True)
    DELAYED_SCHEDULER.cancel(key)
    DELAYED_SCHEDULER.schedule(key, _v213_input_timeout_seconds(), _v213_task_input_timeout, cid, actor, sid, True)
_V213_PREV_V160_SET_PENDING = _canon_v160_set_pending__001
_V213_PREV_V160_GET_PENDING = _canon_v160_get_pending__001

def _v213_v160_key(chat_id: int, user_id: int) -> str:
    return f'v213-input-v160:{int(chat_id)}:{int(user_id)}'

def _v213_v160_timeout(chat_id: int, user_id: int, sid: str):
    key = _v160_pending_key(chat_id, user_id)
    with _V160_ANNOTATION_LOCK:
        row = _V160_ANNOTATION_PENDING.get(key)
        if not isinstance(row, dict) or str(row.get('v213_session_id') or '') != str(sid):
            return False
        _V160_ANNOTATION_PENDING.pop(key, None)
    try:
        _v212_tz_cancel_timer(chat_id, user_id)
    except Exception:
        pass
    _v207_delete_capture_prompt(chat_id, row)
    try:
        send_and_auto_delete(chat_id, '⌛ Ввод отменён по таймеру.', 7)
    except Exception:
        pass
    return True

def _canon_v160_set_pending__002(chat_id: int, user_id: int, mode: str, marker: str, source: dict, prompt_message_id: int=0) -> None:
    _V213_PREV_V160_SET_PENDING(chat_id, user_id, mode, marker, source, prompt_message_id)
    sid = _v213_input_sid()
    key = _v160_pending_key(chat_id, user_id)
    with _V160_ANNOTATION_LOCK:
        row = _V160_ANNOTATION_PENDING.get(key)
        if isinstance(row, dict):
            row['v213_session_id'] = sid
            row['v213_last_activity'] = _v213_time.time()
    sk = _v213_v160_key(chat_id, user_id)
    DELAYED_SCHEDULER.cancel(sk)
    DELAYED_SCHEDULER.schedule(sk, _v213_input_timeout_seconds(), _v213_v160_timeout, int(chat_id), int(user_id), sid)

def _canon_v160_get_pending__002(chat_id: int, user_id: int, pop: bool=False):
    row = _V213_PREV_V160_GET_PENDING(chat_id, user_id, pop=pop)
    if pop and row:
        try:
            DELAYED_SCHEDULER.cancel(_v213_v160_key(chat_id, user_id))
        except Exception:
            pass
    return row

def _canon_v160_begin_capture__002(call, mode: str) -> bool:
    chat_id, message_id, marker, source = _v160_call_source(call)
    user_id = int(getattr(getattr(call, 'from_user', None), 'id', 0) or 0)
    if not _v160_can_annotate(user_id):
        try:
            bot.answer_callback_query(call.id, 'Только для владельца платформы', show_alert=True)
        except Exception:
            pass
        return True
    if not marker:
        try:
            bot.answer_callback_query(call.id, 'Не удалось прочитать маркер этого окна', show_alert=True)
        except Exception:
            pass
        return True
    _v160_set_pending(chat_id, user_id, mode, marker, source)
    catalog, _ = _v160_annotation_roots()
    current_name = str((catalog.get(marker) or {}).get('name') or '')
    if mode == 'marker':
        prompt = f'🏷 Название окна для {marker}' + (f'\nСейчас: {current_name}' if current_name else '') + '\n\nНапишите постоянное понятное имя этого окна одним сообщением.'
    else:
        label = f' — {current_name}' if current_name else ''
        prompt = f'📝 ТЗ для окна {marker}{label}\n\nМожно написать свободно или по шаблону:\n\nЧто сейчас происходит:\nЧто должно происходить:\nКакие кнопки / текст / суммы изменить:\nЧто обязательно оставить без изменений:\nПример желаемого результата:\nОбласть: только это окно / всё направление / весь бот\n\nМожно несколькими сообщениями; /готово — завершить, /cancel — отменить.'
    sid = ''
    with _V160_ANNOTATION_LOCK:
        row = _V160_ANNOTATION_PENDING.get(_v160_pending_key(chat_id, user_id))
        sid = str((row or {}).get('v213_session_id') or '')
    try:
        sent = bot.send_message(chat_id, _v213_prompt_text(prompt + f'\n\nАвтоотмена бездействия: {_format_duration_short(_v213_input_timeout_seconds())}.'), reply_to_message_id=message_id, allow_sending_without_reply=True, reply_markup=_v213_cancel_markup('window', sid))
        _v207_capture_prompt_set(chat_id, user_id, int(getattr(sent, 'message_id', 0) or 0))
        bot.answer_callback_query(call.id, 'Контекст окна зафиксирован')
    except Exception:
        pass
    return True
_V213_PREV_TZ_ADD_PART = _canon_v212_tz_add_part__001

def _canon_v212_tz_add_part__002(chat_id: int, user_id: int, message_id: int, text: str) -> bool:
    ok = _V213_PREV_TZ_ADD_PART(chat_id, user_id, message_id, text)
    if ok:
        try:
            row = _V160_ANNOTATION_PENDING.get(_v160_pending_key(chat_id, user_id)) or {}
            sid = str(row.get('v213_session_id') or '')
            if sid:
                sk = _v213_v160_key(chat_id, user_id)
                DELAYED_SCHEDULER.cancel(sk)
                DELAYED_SCHEDULER.schedule(sk, _v213_input_timeout_seconds(), _v213_v160_timeout, int(chat_id), int(user_id), sid)
        except Exception:
            pass
    return ok
_V213_PREV_KEEPALIVE_BEGIN = _canon_keepalive_begin_peer_url_input__001
_V213_PREV_KEEPALIVE_CANCEL = _canon_keepalive_cancel_input__001

def _canon_keepalive_begin_peer_url_input__002(chat_id: int, panel_message_id: int) -> None:
    cid = int(chat_id)
    sid = _v213_input_sid()
    with _KEEPALIVE_INPUT_LOCK:
        _KEEPALIVE_INPUT_WAIT[cid] = {'kind': 'peer_url', 'panel_message_id': int(panel_message_id or 0), 'started_at': _v213_time.time(), 'session_id': sid}
    key = f'v213-input-keepalive:{cid}'
    DELAYED_SCHEDULER.cancel(key)

    def _expire():
        with _KEEPALIVE_INPUT_LOCK:
            row = dict(_KEEPALIVE_INPUT_WAIT.get(cid) or {})
            if str(row.get('session_id') or '') != sid:
                return
            _KEEPALIVE_INPUT_WAIT.pop(cid, None)
        try:
            mid = int(row.get('panel_message_id') or 0)
            fast_ui_edit_message_text(cid, mid, keepalive_peer_status_text() + '\n\n⌛ Ввод адреса отменён по таймеру.', reply_markup=build_keepalive_peer_keyboard(cid), purpose='keepalive_peer_timeout_v213')
        except Exception:
            pass
    DELAYED_SCHEDULER.schedule(key, _v213_input_timeout_seconds(), _expire)

def _canon_keepalive_cancel_input__002(chat_id: int) -> None:
    cid = int(chat_id)
    try:
        DELAYED_SCHEDULER.cancel(f'v213-input-keepalive:{cid}')
    except Exception:
        pass
    return _V213_PREV_KEEPALIVE_CANCEL(cid)
_V213_PREV_GOOGLE_WAIT = _canon_v149_google_wait__001
_V213_PREV_GOOGLE_HANDLE = _canon_tenant_google_handle_message__001

def _canon_v149_google_wait__002(tenant_id: str, kind: str, chat_id: int, user_id: int) -> None:
    tid = _v149_tenant_id(tenant_id)
    cfg = tenant_google_config(tid)
    sid = _v213_input_sid()
    delay = _v213_input_timeout_seconds()
    cfg['input_wait'] = {'kind': str(kind), 'chat_id': int(chat_id), 'user_id': int(user_id), 'expires_at': _v149_time.time() + delay, 'session_id': sid, 'cancel_message_id': 0}
    cfg['updated_at'] = _v149_now_iso()
    tenant_google_persist(tid, 'tenant_google_update')
    try:
        sent = bot.send_message(int(chat_id), _v213_prompt_text(f'⏳ Ожидание данных Google. Автоотмена: {_format_duration_short(delay)}.'), reply_markup=_v213_cancel_markup('google', sid))
        cfg['input_wait']['cancel_message_id'] = int(getattr(sent, 'message_id', 0) or 0)
        tenant_google_persist(tid, 'tenant_google_update')
    except Exception:
        pass
    key = f'v213-input-google:{tid}:{int(chat_id)}:{int(user_id)}'
    DELAYED_SCHEDULER.cancel(key)

    def _expire():
        live = tenant_google_config(tid).get('input_wait') or {}
        if str(live.get('session_id') or '') != sid:
            return
        mid = int(live.get('cancel_message_id') or 0)
        tenant_google_config(tid)['input_wait'] = {}
        tenant_google_persist(tid, 'tenant_google_update')
        _v172_delete_quiet(int(chat_id), mid)
        try:
            send_and_auto_delete(int(chat_id), '⌛ Ввод Google отменён по таймеру.', 7)
        except Exception:
            pass
    DELAYED_SCHEDULER.schedule(key, delay, _expire)

def _canon_tenant_google_handle_message__002(msg) -> bool:
    wait = {}
    tid = ''
    cid = 0
    uid = 0
    try:
        cid = int(msg.chat.id)
        uid = int(getattr(getattr(msg, 'from_user', None), 'id', 0) or 0)
        tid = str(tenant_id_for_chat(cid, create=False) or '')
        wait = dict((tenant_google_config(tid, create=False) or {}).get('input_wait') or {}) if tid else {}
    except Exception:
        pass
    result = _V213_PREV_GOOGLE_HANDLE(msg)
    if result and wait:
        try:
            live = (tenant_google_config(tid, create=False) or {}).get('input_wait') or {}
            if not live:
                DELAYED_SCHEDULER.cancel(f'v213-input-google:{tid}:{cid}:{uid}')
                _v172_delete_quiet(cid, int(wait.get('cancel_message_id') or 0))
        except Exception:
            pass
    return result
_V213_PREV_SECRET_BEGIN = _canon_begin_secret_full_edit__001

def _canon_begin_secret_full_edit__002(viewer_chat_id: int, target_chat_id: int, day_key: str, record_id: int, source_window_msg_id=None) -> bool:
    ok = _V213_PREV_SECRET_BEGIN(viewer_chat_id, target_chat_id, day_key, record_id, source_window_msg_id)
    if not ok:
        return ok
    try:
        wait = get_chat_store(int(viewer_chat_id)).get('secret_full_edit_wait') or {}
        sid = _v213_input_sid()
        wait['v213_session_id'] = sid
        sent = bot.send_message(int(viewer_chat_id), _v213_prompt_text('Редактирование полного SECRET-текста активно.'), reply_markup=_v213_cancel_markup('secret', sid))
        wait.setdefault('helper_message_ids', []).append(int(getattr(sent, 'message_id', 0) or 0))
        save_data(data, chat_ids=[int(viewer_chat_id)])
    except Exception:
        pass
    return ok

def _v213_cancel_authorized(call, expected_user_id: int) -> bool:
    actor = int(getattr(getattr(call, 'from_user', None), 'id', 0) or 0)
    return bool(actor and (actor == int(expected_user_id or 0) or actor == int(OWNER_ID or 0)))

def _v228_prev_pending_input_cancel_callback_final(call) -> bool:
    raw = str(getattr(call, 'data', '') or '')
    if not raw.startswith('v213:input:cancel:'):
        return False
    parts = raw.split(':', 4)
    flow = parts[3] if len(parts) > 3 else ''
    prefix = parts[4] if len(parts) > 4 else ''
    cid = int(call.message.chat.id)
    actor = int(getattr(getattr(call, 'from_user', None), 'id', 0) or 0)
    cancelled = False
    if flow == 'task':
        row = _v174_get_input(cid, actor) or (_v174_get_input(cid, int(OWNER_ID or 0)) if actor == int(OWNER_ID or 0) else None)
        target_user = actor
        if row and str(row.get('session_id') or '').startswith(prefix) and _v213_cancel_authorized(call, target_user):
            old = _v174_pop_input(cid, target_user) or row
            _v172_delete_quiet(cid, int(old.get('prompt_id') or 0))
            cancelled = True
    elif flow == 'tasklegacy':
        row = _v172_get_input(cid, actor)
        target_user = actor
        if row and str(row.get('session_id') or '').startswith(prefix) and _v213_cancel_authorized(call, target_user):
            old = _v172_clear_input(cid, target_user) or row
            _v172_delete_quiet(cid, int(old.get('prompt_id') or 0))
            cancelled = True
    elif flow == 'window':
        row = _v160_get_pending(cid, actor, pop=False)
        if row and str(row.get('v213_session_id') or '').startswith(prefix) and _v213_cancel_authorized(call, actor):
            old = _v160_get_pending(cid, actor, pop=True) or row
            try:
                _v212_tz_cancel_timer(cid, actor)
            except Exception:
                pass
            _v207_delete_capture_prompt(cid, old)
            cancelled = True
    elif flow == 'google':
        tid = str(tenant_id_for_chat(cid, create=False) or '')
        cfg = tenant_google_config(tid, create=False) if tid else {}
        row = (cfg or {}).get('input_wait') or {}
        if row and str(row.get('session_id') or '').startswith(prefix) and _v213_cancel_authorized(call, int(row.get('user_id') or 0)):
            try:
                DELAYED_SCHEDULER.cancel(f"v213-input-google:{tid}:{cid}:{int(row.get('user_id') or 0)}")
            except Exception:
                pass
            mid = int(row.get('cancel_message_id') or 0)
            cfg['input_wait'] = {}
            tenant_google_persist(tid, 'tenant_google_update')
            _v172_delete_quiet(cid, mid)
            cancelled = True
    elif flow == 'secret':
        row = get_chat_store(cid).get('secret_full_edit_wait') or {}
        target = int(row.get('target_chat_id') or 0) if row else 0
        allowed = bool(actor == int(OWNER_ID or 0) or (target and can_manage_secret_target(cid, target)))
        if row and allowed and str(row.get('v213_session_id') or '').startswith(prefix):
            try:
                _secret_full_edit_clear(cid, delete_helpers=True)
                cancelled = True
            except Exception:
                pass
    try:
        bot.answer_callback_query(call.id, 'Ввод отменён' if cancelled else 'Сессия уже завершена', show_alert=False)
    except Exception:
        pass
    if cancelled:
        try:
            send_and_auto_delete(cid, '❎ Ввод отменён.', 5)
        except Exception:
            pass
    return True
_V213_PREV_TIMER_INPUT_KEYBOARD = _canon_build_internal_timer_input_keyboard__001

def _canon_build_internal_timer_input_keyboard__002(chat_id: int):
    kb = _V213_PREV_TIMER_INPUT_KEYBOARD(int(chat_id))
    try:
        session = _timer_input_session(int(chat_id))
        if str(session.get('key') or '') == 'interactive_input_idle':
            rows = list(getattr(kb, 'keyboard', []) or [])
            quick1 = [IB('1 мин', callback_data='v213:itmr_input:60'), IB('3 мин', callback_data='v213:itmr_input:180'), IB('5 мин', callback_data='v213:itmr_input:300')]
            quick2 = [IB('10 мин', callback_data='v213:itmr_input:600'), IB('15 мин', callback_data='v213:itmr_input:900'), IB('30 мин', callback_data='v213:itmr_input:1800')]
            kb.keyboard = [quick1, quick2] + rows
    except Exception:
        pass
    return kb

def _v213_internal_timer_quick_callback(call, raw: str) -> bool:
    if not str(raw or '').startswith('v213:itmr_input:'):
        return False
    cid = int(call.message.chat.id)
    if not is_owner_chat(cid):
        try:
            bot.answer_callback_query(call.id, 'Только для владельца', show_alert=True)
        except Exception:
            pass
        return True
    try:
        value = int(str(raw).rsplit(':', 1)[1])
    except Exception:
        return True
    if value not in V213_INPUT_CHOICES_SECONDS:
        return True
    value = set_internal_timer_seconds('interactive_input_idle', value)
    _reset_timer_input_session(cid, 'interactive_input_idle')
    try:
        bot.answer_callback_query(call.id, f'Ожидание ввода: {_format_duration_short(value)}')
    except Exception:
        pass
    fast_ui_edit_message_text(cid, call.message.message_id, build_internal_timer_input_text(cid), reply_markup=build_internal_timer_input_keyboard(cid), purpose='v213_input_timer_quick')
    try:
        bot_journal('interactive_input_timer_changed_v213', cid, f'seconds={int(value)}')
    except Exception:
        pass
    return True
_V213_PREV_TD_CALLBACK = _canon_v174_callback__001

def _v213_v174_callback(call):
    raw = str(getattr(call, 'data', '') or '')
    parts = raw.split(':')
    cid = int(call.message.chat.id)
    uid = int(getattr(getattr(call, 'from_user', None), 'id', 0) or 0)
    if raw.startswith('v174:td:toggle:'):
        try:
            bot.answer_callback_query(call.id)
        except Exception:
            pass
        if cid != int(OWNER_ID or 0):
            return True
        try:
            target = int(parts[3])
            level = int(parts[4])
            page = int(parts[5])
        except Exception:
            return True
        if target != int(OWNER_ID or 0) and target not in set(_v174_circle_ids(2 if level == 2 else 1)):
            try:
                bot.answer_callback_query(call.id, 'Чат больше не входит в этот круг.', show_alert=True)
            except Exception:
                pass
            return True
        s = _v172_chat_settings(target)
        s['enabled'] = not bool(s.get('enabled'))
        s['updated_at'] = _v172_iso()
        s['updated_by'] = uid
        _v174_settings(target)
        _v172_persist(target, 'v213_dispatcher_toggle')
        if s['enabled']:
            _v212_open_task_window(target, uid if target == int(OWNER_ID or 0) else 0)
        else:
            schedule_contour_home_after_mode_change(target, 'tasks_off', 0.1)
        text, kb = _v174_admin_text_kb(1 if level not in {1, 2} else level, page)
        _v174_edit_call(call, text, kb)
        return True
    return _V213_PREV_TD_CALLBACK(call)

def _v213_task_dispatcher_callback_final(call) -> bool:
    raw = str(getattr(call, 'data', '') or '')
    try:
        resolver = globals().get('resolve_short_callback')
        if callable(resolver):
            raw = str(resolver(raw) or raw)
    except Exception:
        pass
    if raw.startswith('v213:input:cancel:'):
        return pending_input_cancel_callback_final(call)
    if raw.startswith('v213:itmr_input:'):
        return _v213_internal_timer_quick_callback(call, raw)
    if raw.startswith('v174:td:'):
        _v174_callback(call)
        return True
    if raw.startswith('v172:task:'):
        if _v174_legacy_filter(call):
            _v174_legacy_callback(call)
            return True
        _v172_callback(call)
        return True
    return False
_V213_START_REPLACED = _v213_replace_start_handler()
try:
    _v177_legacy_0007_bot_journal('v213_contour_pending_ready', int(OWNER_ID or 0), f'start_replaced={_V213_START_REPLACED}; input_idle={_v213_input_timeout_seconds():.0f}s; contour_home=1; F252=1')
except Exception:
    pass
V214_TASK_CANCEL_LABEL = '❌ Отмена'

def _v214_task_pending_row(chat_id: int, user_id: int, legacy: bool=False):
    root = _V172_INPUT_WAIT if legacy else _V174_INPUT_WAIT
    lock = _V172_INPUT_LOCK if legacy else _V174_INPUT_LOCK
    with lock:
        row = root.get((int(chat_id), int(user_id)))
        return dict(row) if isinstance(row, dict) else None

def _v214_find_task_pending_by_sid(chat_id: int, sid_prefix: str, legacy: bool=False):
    root = _V172_INPUT_WAIT if legacy else _V174_INPUT_WAIT
    lock = _V172_INPUT_LOCK if legacy else _V174_INPUT_LOCK
    cid = int(chat_id)
    prefix = str(sid_prefix or '')
    with lock:
        for (row_chat, row_user), row in list(root.items()):
            if int(row_chat) != cid or not isinstance(row, dict):
                continue
            if str(row.get('session_id') or '').startswith(prefix):
                return (int(row_user), dict(row))
    return (0, None)

def _v214_cancel_task_input_rows(chat_id: int, user_id: int, reason: str='manual', expected_sid: str='', legacy=None):
    """Cancel only Task Dispatcher pending input for chat+user; generation-safe and idempotent."""
    cid, uid = (int(chat_id), int(user_id))
    cancelled = []
    variants = (True,) if legacy is True else (False,) if legacy is False else (False, True)
    for is_legacy in variants:
        root = _V172_INPUT_WAIT if is_legacy else _V174_INPUT_WAIT
        lock = _V172_INPUT_LOCK if is_legacy else _V174_INPUT_LOCK
        key = (cid, uid)
        row = None
        with lock:
            live = root.get(key)
            if not isinstance(live, dict):
                continue
            if expected_sid and str(live.get('session_id') or '') != str(expected_sid):
                continue
            row = root.pop(key, None)
        if not isinstance(row, dict):
            continue
        try:
            DELAYED_SCHEDULER.cancel(_v213_task_input_key(cid, uid, bool(is_legacy)))
        except Exception:
            pass
        try:
            _v172_delete_quiet(cid, int(row.get('prompt_id') or 0))
        except Exception:
            pass
        cancelled.append((bool(is_legacy), row))
    if cancelled:
        try:
            actions = ','.join((str(row.get('action') or '') for _, row in cancelled))
            bot_journal('task_input_cancel_v214', cid, f'user={uid}; reason={reason}; action={actions}')
        except Exception:
            pass
    return cancelled

def cancel_task_input(chat_id: int, user_id: int, reason: str='manual') -> bool:
    """Single public cancellation helper required by v214 task-input navigation contract."""
    return bool(_v214_cancel_task_input_rows(int(chat_id), int(user_id), str(reason or 'manual')))

def _v214_task_input_timeout(chat_id: int, user_id: int, sid: str, legacy: bool=False):
    cancelled = _v214_cancel_task_input_rows(int(chat_id), int(user_id), 'timeout', expected_sid=str(sid), legacy=bool(legacy))
    if not cancelled:
        return False
    try:
        send_and_auto_delete(int(chat_id), '⌛ Ввод отменён по таймеру.', 7)
    except Exception:
        pass
    return True

def _v214_task_back_callback(action: str, kind: str='', task_uid: str='', legacy: bool=False) -> str:
    action = str(action or '')
    kind = str(kind or '')
    task_uid = str(task_uid or '').upper()
    if legacy:
        if task_uid:
            return f'v172:task:open:{task_uid}'
        return 'v172:task:list:active:0'
    if task_uid:
        return f'v174:td:open:{task_uid}'
    if action == 'keywords' and kind:
        return f'v174:td:kw:{kind}'
    if action in {'branch_rename', 'branch_keywords'} and kind and (not kind.startswith('NEW|')):
        return f'v174:td:branch:open:{kind}'
    return 'v174:td:menu'

def _v214_task_prompt_markup(chat_id: int, flow: str, sid: str, action: str='', kind: str='', task_uid: str='', legacy: bool=False):
    kb = types.InlineKeyboardMarkup()
    kb.row(IB(V214_TASK_CANCEL_LABEL, callback_data=f'v213:input:cancel:{str(flow)[:12]}:{str(sid)[:12]}'))
    day = today_key()
    try:
        day = str(get_chat_store(int(chat_id)).get('current_view_day') or today_key())
    except Exception:
        pass
    back_cb = _v214_task_back_callback(action, kind, task_uid, legacy)
    kb.row(IB('🔙 Назад', callback_data=back_cb), IB('⬅️ Назад в основное', callback_data=f'd:{day}:back_main'))
    return kb

def _v214_cancel_markup(flow: str, sid: str):
    kb = types.InlineKeyboardMarkup()
    kb.row(IB(V214_TASK_CANCEL_LABEL, callback_data=f'v213:input:cancel:{str(flow)[:12]}:{str(sid)[:12]}'))
    return kb
_V214_PREV_V174_PROMPT_INPUT = _v213_v174_prompt_input

def _v214_v174_prompt_input(chat_id: int, user_id: int, action: str, kind: str='', task_uid: str='', message_id: int=0):
    cid, uid = (int(chat_id), int(user_id))
    cancel_task_input(cid, uid, 'new_input')
    sid = _v213_input_sid()
    prompt = _V213_TASK_PROMPTS.get(str(action), 'Введите значение:')
    if str(action) == 'keywords':
        prompt = f'⚙️ КЛЮЧЕВЫЕ СЛОВА · РЕЖИМ ВВОДА\n\n✏️ Отправьте новый список для «{_V174_KEYWORD_LABELS.get(kind, kind)}» через запятую.'
    elif str(action).startswith('branch_'):
        prompt = {'branch_name': '📂 Введите название новой ветки задач.', 'branch_keywords': '🔑 Введите ключевые слова через запятую.', 'branch_rename': '✏️ Введите новое название ветки.'}.get(str(action), prompt)
    delay = _v213_input_timeout_seconds()
    text = _v213_prompt_text(prompt + f'\n\n⏳ Автоотмена бездействия: {_format_duration_short(delay)}.')
    pid = 0
    try:
        sent = bot.send_message(cid, text, reply_markup=_v214_task_prompt_markup(cid, 'task', sid, action, kind, task_uid, False))
        pid = int(getattr(sent, 'message_id', 0) or 0)
    except Exception:
        pass
    with _V174_INPUT_LOCK:
        _V174_INPUT_WAIT[cid, uid] = {'action': str(action), 'kind': str(kind), 'task_uid': str(task_uid or '').upper(), 'message_id': int(message_id or 0), 'prompt_id': pid, 'created': _v213_time.time(), 'last_activity': _v213_time.time(), 'session_id': sid, 'generation': 1}
    key = _v213_task_input_key(cid, uid, False)
    try:
        DELAYED_SCHEDULER.cancel(key)
    except Exception:
        pass
    DELAYED_SCHEDULER.schedule(key, delay, _v214_task_input_timeout, cid, uid, sid, False)
    return sid
_V214_PREV_V172_PROMPT = _v213_v172_prompt

def _v214_v172_prompt(chat_id: int, user_id: int, action: str, uid: str='', message_id: int=0):
    cid, actor = (int(chat_id), int(user_id))
    cancel_task_input(cid, actor, 'new_input')
    sid = _v213_input_sid()
    delay = _v213_input_timeout_seconds()
    prompts = {'new_task': '✍️ Напишите текст новой задачи.', 'new_purchase': '🛒 Напишите, что нужно купить.', 'text': '✏️ Напишите новый текст задачи.', 'object': '🏠 Напишите объект/дом/зону. «нет» — очистить.', 'deadline': '📅 Введите срок. «нет» — убрать срок.', 'assign': '👥 Напишите ответственных через запятую. «нет» — снять всех.', 'comment': '💬 Напишите комментарий.', 'cost': '💰 Напишите стоимость/бюджет. «нет» — очистить.', 'search': '🔎 Напишите слово или фразу для поиска.'}
    pid = 0
    try:
        sent = bot.send_message(cid, _v213_prompt_text(prompts.get(str(action), 'Введите значение:') + f'\n\n⏳ Автоотмена бездействия: {_format_duration_short(delay)}.'), reply_markup=_v214_task_prompt_markup(cid, 'tasklegacy', sid, action, '', uid, True))
        pid = int(getattr(sent, 'message_id', 0) or 0)
    except Exception:
        pass
    with _V172_INPUT_LOCK:
        _V172_INPUT_WAIT[cid, actor] = {'action': str(action), 'uid': str(uid or '').upper(), 'message_id': int(message_id or 0), 'prompt_id': pid, 'created': _v213_time.time(), 'session_id': sid}
    key = _v213_task_input_key(cid, actor, True)
    try:
        DELAYED_SCHEDULER.cancel(key)
    except Exception:
        pass
    DELAYED_SCHEDULER.schedule(key, delay, _v214_task_input_timeout, cid, actor, sid, True)
    return sid
_V214_PREV_V174_HANDLE_OWN_INPUT = _v228_prev_v174_handle_own_input

def _v214_v174_handle_own_input(msg) -> bool:
    try:
        if str(getattr(msg, 'content_type', '') or '') == 'text':
            cid = int(msg.chat.id)
            uid = int(getattr(getattr(msg, 'from_user', None), 'id', 0) or 0)
            text = str(getattr(msg, 'text', '') or '').strip().casefold()
            if text in {'отмена', 'cancel', 'стоп'} and _v214_task_pending_row(cid, uid, False):
                cancel_task_input(cid, uid, 'text_cancel')
                _v172_delete_quiet(cid, int(getattr(msg, 'message_id', 0) or 0))
                try:
                    send_and_auto_delete(cid, '❎ Действие отменено.', 5)
                except Exception:
                    pass
                return True
    except Exception:
        pass
    return _V214_PREV_V174_HANDLE_OWN_INPUT(msg)
_V214_PREV_V172_TASK_MESSAGE_INPUT = _canon_v172_task_message_input__001

def _v214_v172_task_message_input(msg) -> bool:
    try:
        if str(getattr(msg, 'content_type', '') or '') == 'text':
            cid = int(msg.chat.id)
            uid = int(getattr(getattr(msg, 'from_user', None), 'id', 0) or 0)
            text = str(getattr(msg, 'text', '') or '').strip().casefold()
            if text in {'отмена', 'cancel', 'стоп'} and _v214_task_pending_row(cid, uid, True):
                cancel_task_input(cid, uid, 'text_cancel')
                _v172_delete_quiet(cid, int(getattr(msg, 'message_id', 0) or 0))
                try:
                    send_and_auto_delete(cid, '❎ Действие отменено.', 5)
                except Exception:
                    pass
                return True
    except Exception:
        pass
    return _V214_PREV_V172_TASK_MESSAGE_INPUT(msg)

def _v214_task_callback_requires_cancel(raw: str) -> bool:
    value = str(raw or '')
    if value.startswith('v213:input:cancel:'):
        return False
    if value in {'nav_prev', 'info_close', 'aux_close'} or value.endswith(':back_main'):
        return True
    return value.startswith(('v174:td:', 'v172:task:'))

def _v214_cancel_pending_before_navigation(call, resolved: str) -> bool:
    try:
        cid = int(call.message.chat.id)
        uid = int(getattr(getattr(call, 'from_user', None), 'id', 0) or 0)
    except Exception:
        return False
    if not uid or not _v214_task_callback_requires_cancel(resolved):
        return False
    return cancel_task_input(cid, uid, 'navigation')
_V214_PREV_PENDING_CANCEL_CALLBACK = _v228_prev_pending_input_cancel_callback_final

def _v214_pending_input_cancel_callback_final(call) -> bool:
    raw = str(getattr(call, 'data', '') or '')
    if not raw.startswith('v213:input:cancel:'):
        return False
    parts = raw.split(':', 4)
    flow = parts[3] if len(parts) > 3 else ''
    prefix = parts[4] if len(parts) > 4 else ''
    if flow not in {'task', 'tasklegacy'}:
        return _V214_PREV_PENDING_CANCEL_CALLBACK(call)
    try:
        cid = int(call.message.chat.id)
        actor = int(getattr(getattr(call, 'from_user', None), 'id', 0) or 0)
    except Exception:
        return True
    legacy = flow == 'tasklegacy'
    target_user, row = _v214_find_task_pending_by_sid(cid, prefix, legacy)
    allowed = bool(row and (actor == target_user or actor == int(OWNER_ID or 0)))
    cancelled = False
    if allowed:
        cancelled = bool(_v214_cancel_task_input_rows(cid, target_user, 'button_cancel', expected_sid=str(row.get('session_id') or ''), legacy=legacy))
    try:
        bot.answer_callback_query(call.id, 'Ввод отменён' if cancelled else 'Сессия уже завершена', show_alert=False)
    except Exception:
        pass
    return True
_V214_PREV_CONTOUR_CALLBACK_GUARD = _canon_contour_callback_guard__001

def _v214_contour_callback_guard(call, resolved: str) -> bool:
    _v214_cancel_pending_before_navigation(call, resolved)
    try:
        actor = int(getattr(getattr(call, 'from_user', None), 'id', 0) or 0)
    except Exception:
        actor = 0
    if actor and actor == int(OWNER_ID or 0):
        return False
    return _V214_PREV_CONTOUR_CALLBACK_GUARD(call, resolved)
_V214_PREV_CRITICAL_CALLBACK = _canon_v161_critical_callback__002

def _v214_critical_callback_final(call, resolved: str) -> bool:
    raw = str(resolved or '')
    try:
        cid = int(call.message.chat.id)
        actor = int(getattr(getattr(call, 'from_user', None), 'id', 0) or 0)
        mid = int(call.message.message_id)
    except Exception:
        return _V214_PREV_CRITICAL_CALLBACK(call, resolved)
    if actor == int(OWNER_ID or 0) and bool(globals().get('directive_chat_enabled_v223', lambda _c: False)(cid)) and (raw == 'nav_prev' or (raw.startswith('d:') and raw.endswith(':back_main'))):
        cancel_task_input(cid, actor, 'directive_owner_navigation')
        try:
            _v161_ack(call)
        except Exception:
            pass
        day = raw.split(':', 2)[1] if raw.startswith('d:') else str(get_chat_store(cid).get('current_view_day') or today_key())
        open_resolved_contour_home(cid, actor, mid, str(day))
        try:
            bot_journal('directive_owner_chat_navigation_v224', cid, f'action={raw}; home={resolve_contour_home(cid)}; admin_bypass=0')
        except Exception:
            pass
        return True
    if actor == int(OWNER_ID or 0) and (raw == 'nav_prev' or (raw.startswith('d:') and raw.endswith(':back_main'))):
        cancel_task_input(cid, actor, 'owner_navigation')
        try:
            _v161_ack(call)
        except Exception:
            pass
        if raw == 'nav_prev':
            try:
                if restore_previous_window(call):
                    return True
            except Exception:
                pass
        try:
            day = raw.split(':', 2)[1] if raw.startswith('d:') else str(get_chat_store(cid).get('current_view_day') or today_key())
            _V213_PREV_RETURN_TO_MAIN(cid, str(day), current_message_id=mid)
            try:
                bot_journal('owner_admin_navigation_v214', cid, f'action={raw}; modes_unchanged=1')
            except Exception:
                pass
        except Exception as exc:
            try:
                log_error(f'owner admin navigation v214 {cid}: {exc}')
            except Exception:
                pass
        return True
    return _V214_PREV_CRITICAL_CALLBACK(call, resolved)
try:
    WINDOW_MARKER_CONSTANTS.setdefault('v214:task:manual_cancel', V213_INPUT_FLOW_MARKER)
    _v177_legacy_0007_bot_journal('v214_task_cancel_owner_nav_ready', int(OWNER_ID or 0), 'manual_cancel=1; back_cancel=1; owner_admin_nav=1')
except Exception:
    pass
V215_CONTOUR_START_MARKER = 'Ф255'
V215_CONTOUR_MODE_MARKER = 'Ф256'
V215_FORWARD_MODE_KEY = 'business_forward_enabled_v215'
V215_REMINDER_MODE_KEY = 'business_reminders_enabled_v215'

def _v215_circle_business_chat(chat_id: int) -> bool:
    try:
        return int(chat_id) != int(OWNER_ID or 0) and int(circle_level_for_chat(int(chat_id))) in {1, 2}
    except Exception:
        return False

def _v215_mode_settings(chat_id: int) -> dict:
    try:
        return get_chat_store(int(chat_id)).setdefault('settings', {})
    except Exception:
        return {}

def _v215_forward_rules_present(chat_id: int) -> bool:
    try:
        src = str(int(chat_id))
        return bool((data.get('forward_rules', {}) or {}).get(src) or {})
    except Exception:
        return False

def contour_forwarding_mode_enabled(chat_id: int) -> bool:
    cid = int(chat_id)
    settings = _v215_mode_settings(cid)
    if V215_FORWARD_MODE_KEY not in settings:
        return _v215_forward_rules_present(cid)
    return bool(settings.get(V215_FORWARD_MODE_KEY))

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

def contour_reminders_mode_enabled(chat_id: int) -> bool:
    cid = int(chat_id)
    settings = _v215_mode_settings(cid)
    if V215_REMINDER_MODE_KEY not in settings:
        return _v215_existing_reminder_target(cid)
    return bool(settings.get(V215_REMINDER_MODE_KEY))

def _v215_persist_mode(chat_id: int, reason: str) -> None:
    cid = int(chat_id)
    try:
        save_data(data, chat_ids=[cid])
    except Exception:
        try:
            save_data(data)
        except Exception:
            pass
    try:
        schedule_delta_backup(cid, delay=0.12, reason=f'v215:{reason}')
    except Exception:
        try:
            schedule_config_backup_for_chats(cid)
        except Exception:
            pass

def _v215_set_forward_mode(chat_id: int, enabled: bool, *, persist: bool=True) -> bool:
    cid = int(chat_id)
    value = bool(enabled)
    _v215_mode_settings(cid)[V215_FORWARD_MODE_KEY] = value
    if persist:
        _v215_persist_mode(cid, 'forward_mode')
    return value

def _v215_set_reminders_mode(chat_id: int, enabled: bool, *, persist: bool=True) -> bool:
    cid = int(chat_id)
    value = bool(enabled)
    _v215_mode_settings(cid)[V215_REMINDER_MODE_KEY] = value
    if persist:
        _v215_persist_mode(cid, 'reminders_mode')
    return value

def _v215_mode_enabled(chat_id: int, mode: str) -> bool:
    cid = int(chat_id)
    mode = str(mode or '')
    if mode == 'finance':
        try:
            return bool(is_finance_mode(cid))
        except Exception:
            return False
    if mode == 'forward':
        return contour_forwarding_mode_enabled(cid)
    if mode == 'reminders':
        return contour_reminders_mode_enabled(cid)
    if mode == 'tasks':
        try:
            return bool(task_dispatcher_enabled(cid))
        except Exception:
            return False
    return False

def _v215_mode_title(mode: str) -> str:
    return {'finance': '💰 Финансы', 'forward': '📤 Пересылка', 'reminders': '⏰ Напоминания', 'tasks': '📋 Задачи'}.get(str(mode or ''), 'Режим')

def _v215_can_toggle_mode(user_id: int, chat_id: int) -> bool:
    try:
        return int(user_id or 0) == int(OWNER_ID or 0) and _v215_circle_business_chat(int(chat_id))
    except Exception:
        return False

def _v216_mode_description(mode: str) -> str:
    return {'finance': 'Расходы, остатки и финансовые отчёты.', 'forward': 'Пересылка сообщений между настроенными чатами.', 'reminders': 'Напоминания, сроки и запланированные события.', 'tasks': 'Задачи, покупки, ответственные и статусы выполнения.'}.get(str(mode or ''), 'Рабочий режим этого чата.')

def _canon_build_contour_start_modes__001(chat_id: int, user_id: int=0):
    cid = int(chat_id)
    level = int(circle_level_for_chat(cid)) if 'circle_level_for_chat' in globals() else 1
    name = str(get_chat_display_name(cid) or f'Чат {cid}')
    text = window_mark(f"🏠 ГЛАВНОЕ МЕНЮ\n\n{name}\nКонтур: {('1️⃣ первый' if level == 1 else '2️⃣ второй')}\n\nВыберите нужный раздел.\n✅ — режим включён    ⬜ — режим выключен\n\nНажмите на режим, чтобы посмотреть его состояние и перейти в рабочее меню.\nНажатие здесь само по себе режим не включает и не выключает.\nКоманда /start из любого места возвращает сюда.", V215_CONTOUR_START_MARKER)
    kb = types.InlineKeyboardMarkup(row_width=1)
    for mode in ('finance', 'forward', 'reminders', 'tasks'):
        icon = '✅' if _v215_mode_enabled(cid, mode) else '⬜'
        kb.row(IB(f'{icon} {_v215_mode_title(mode)}', callback_data=f'v215:mode:open:{mode}'))
    kb.row(IB('ℹ️ Как пользоваться', callback_data='v215:mode:guide'))
    kb.row(IB('❌ Закрыть', callback_data='aux_close'))
    return (text, kb)

def _canon_build_contour_menu_guide__001(chat_id: int):
    cid = int(chat_id)
    level = int(circle_level_for_chat(cid)) if 'circle_level_for_chat' in globals() else 1
    text = window_mark(f"ℹ️ КАК ПОЛЬЗОВАТЬСЯ БОТОМ\n\nКонтур: {('1️⃣ первый' if level == 1 else '2️⃣ второй')}\n\nКарта движения:\n/start\n↓\n🏠 Главное меню\n↓ выберите раздел\n💰 Финансы / 📤 Пересылка / ⏰ Напоминания / 📋 Задачи\n↓\nЭкран режима: состояние + кнопка открытия\n↓\n➡️ Открыть — перейти в штатное рабочее меню\n\n✅ означает, что режим работает.\n⬜ означает, что режим выключен.\nЕсли режим выключен, бизнес-действия недоступны.\nВключение и выключение доступно только тем, кому это разрешено владельцем.\n\nЕсли потерялись в меню — отправьте /start.", V215_CONTOUR_MODE_MARKER)
    kb = types.InlineKeyboardMarkup()
    kb.row(IB('🔙 К режимам', callback_data='v215:mode:back'))
    return (text, kb)

def _canon_build_contour_mode_control__001(chat_id: int, user_id: int, mode: str):
    cid = int(chat_id)
    uid = int(user_id or 0)
    mode = str(mode or '')
    enabled = _v215_mode_enabled(cid, mode)
    state = '✅ Включено' if enabled else '⬜ Выключено'
    extra = ''
    if mode == 'finance' and enabled:
        try:
            if not contour_visible_finance_enabled(cid):
                extra = '\nВидимое финансовое окно: ⬜ (финансы работают скрыто)'
        except Exception:
            pass
    if not enabled and (not _v215_can_toggle_mode(uid, cid)):
        extra += '\n\nДля включения режима обратитесь к владельцу.'
    text = window_mark(f'{_v215_mode_title(mode)}\n\n{_v216_mode_description(mode)}\n\nСостояние: {state}{extra}', V215_CONTOUR_MODE_MARKER)
    kb = types.InlineKeyboardMarkup()
    if _v215_can_toggle_mode(uid, cid):
        kb.row(IB('✅ Режим включён' if enabled else '⬜ Включить режим', callback_data=f'v215:mode:toggle:{mode}'))
    else:
        kb.row(IB(state, callback_data='none'))
    short = {'finance': 'финансы', 'forward': 'пересылку', 'reminders': 'напоминания', 'tasks': 'задачи'}.get(mode, 'меню')
    kb.row(IB(f'➡️ Открыть {short}', callback_data=f'v215:mode:go:{mode}'))
    kb.row(IB('🔙 К режимам', callback_data='v215:mode:back'))
    return (text, kb)

def _v215_edit_or_send(chat_id: int, message_id: int, text: str, kb, purpose: str) -> int:
    cid = int(chat_id)
    mid = int(message_id or 0)
    if mid:
        try:
            result = fast_ui_edit_message_text(cid, mid, text, reply_markup=kb, purpose=purpose)
            if result in {'ok', 'scheduled', 'not_modified'}:
                return mid
        except Exception:
            pass
    try:
        sent = bot.send_message(cid, text, reply_markup=kb)
        return int(getattr(sent, 'message_id', 0) or 0)
    except Exception:
        return 0

def _canon_show_contour_start_modes__001(chat_id: int, user_id: int=0, message_id: int=0) -> int:
    text, kb = build_contour_start_modes(int(chat_id), int(user_id or 0))
    mid = _v215_edit_or_send(int(chat_id), int(message_id or 0), text, kb, 'contour_start_modes_v215')
    if mid:
        try:
            register_open_window(int(chat_id), mid, 'contour_modes', code=V215_CONTOUR_START_MARKER, params={'circle': int(circle_level_for_chat(int(chat_id)))})
        except Exception:
            pass
    return mid

def _v215_toggle_mode(chat_id: int, user_id: int, mode: str) -> bool:
    cid = int(chat_id)
    uid = int(user_id or 0)
    mode = str(mode or '')
    if not _v215_can_toggle_mode(uid, cid):
        raise PermissionError('Недостаточно прав')
    old = _v215_mode_enabled(cid, mode)
    new = not old
    if mode == 'finance':
        set_finance_mode(cid, new)
        if new:
            try:
                set_finance_window_mode(cid, 'normal', persist_now=False)
                st = _finance_window_state(cid)
                st['auto_reopen_on_boot'] = True
                _persist_finance_window_mode_critical(cid)
            except Exception:
                pass
    elif mode == 'forward':
        _v215_set_forward_mode(cid, new)
    elif mode == 'reminders':
        _v215_set_reminders_mode(cid, new)
    elif mode == 'tasks':
        row = _v172_chat_settings(cid)
        row['enabled'] = new
        row['updated_at'] = _v172_iso()
        row['updated_by'] = uid
        _v172_persist(cid, 'v215_start_toggle')
    else:
        raise ValueError('unknown mode')
    try:
        bot_journal('contour_mode_toggle_v215', cid, f'mode={mode}; old={int(old)}; new={int(new)}; by={uid}')
    except Exception:
        pass
    return new

def _canon_v215_go_mode__001(call, mode: str) -> bool:
    cid = int(call.message.chat.id)
    uid = int(getattr(getattr(call, 'from_user', None), 'id', 0) or 0)
    mid = int(call.message.message_id)
    if not _v215_mode_enabled(cid, mode):
        try:
            bot.answer_callback_query(call.id, 'Сначала включите режим.', show_alert=False)
        except Exception:
            pass
        return True
    if mode == 'tasks':
        _v213_show_task_home(cid, uid, mid)
        return True
    if mode == 'finance':
        try:
            if contour_visible_finance_enabled(cid):
                open_resolved_contour_home(cid, uid, mid)
                return True
        except Exception:
            pass
        try:
            bot.answer_callback_query(call.id, 'Финансы включены скрыто. Видимое финансовое окно отключено.', show_alert=True)
        except Exception:
            pass
        return True
    if uid != int(OWNER_ID or 0):
        try:
            bot.answer_callback_query(call.id, 'Меню настройки доступно владельцу.', show_alert=True)
        except Exception:
            pass
        return True
    if mode == 'forward':
        try:
            day = today_key()
            kb = build_forward_menu_keyboard_for_current_mode(day)
            safe_edit(bot, call, build_forward_menu_text_for_current_mode('Пересылка:\nВыберите чат A:'), reply_markup=kb)
        except Exception as exc:
            try:
                log_error(f'v215 forward menu: {exc}')
            except Exception:
                pass
        return True
    if mode == 'reminders':
        try:
            safe_edit(bot, call, build_reminder_list_text(), reply_markup=build_reminder_list_keyboard(today_key(), 0))
        except Exception:
            pass
        return True
    return True

def v215_contour_mode_callback(call, resolved: str) -> bool:
    raw = str(resolved or '')
    if not raw.startswith('v215:mode:'):
        return False
    try:
        cid = int(call.message.chat.id)
        uid = int(getattr(getattr(call, 'from_user', None), 'id', 0) or 0)
        mid = int(call.message.message_id)
    except Exception:
        return True
    if not _v215_circle_business_chat(cid):
        return True
    parts = raw.split(':')
    action = parts[2] if len(parts) > 2 else ''
    mode = parts[3] if len(parts) > 3 else ''
    if action == 'guide':
        try:
            bot.answer_callback_query(call.id)
        except Exception:
            pass
        text, kb = build_contour_menu_guide(cid)
        _v215_edit_or_send(cid, mid, text, kb, 'contour_mode_guide_v216')
        return True
    if action == 'back':
        try:
            bot.answer_callback_query(call.id)
        except Exception:
            pass
        if bool(globals().get('directive_chat_enabled_v223', lambda _c: False)(cid)):
            open_resolved_contour_home(cid, uid, mid)
            return True
        show_contour_start_modes(cid, uid, mid)
        return True
    if action == 'open' and mode in {'finance', 'forward', 'reminders', 'tasks'}:
        try:
            bot.answer_callback_query(call.id)
        except Exception:
            pass
        if bool(globals().get('directive_chat_enabled_v223', lambda _c: False)(cid)):
            if _v215_mode_enabled(cid, mode):
                v224_open_directive_mode_home(cid, uid, mid, mode)
            else:
                open_resolved_contour_home(cid, uid, mid)
            return True
        text, kb = build_contour_mode_control(cid, uid, mode)
        _v215_edit_or_send(cid, mid, text, kb, 'contour_mode_control_v215')
        return True
    if action == 'toggle' and mode in {'finance', 'forward', 'reminders', 'tasks'}:
        try:
            _v215_toggle_mode(cid, uid, mode)
            try:
                bot.answer_callback_query(call.id)
            except Exception:
                pass
            text, kb = build_contour_mode_control(cid, uid, mode)
            _v215_edit_or_send(cid, mid, text, kb, 'contour_mode_toggle_v215')
            try:
                bot.edit_message_reply_markup(chat_id=cid, message_id=mid, reply_markup=kb)
            except Exception:
                pass
        except PermissionError:
            try:
                bot.answer_callback_query(call.id, 'Недостаточно прав для изменения режима.', show_alert=True)
            except Exception:
                pass
        return True
    if action == 'go' and mode in {'finance', 'forward', 'reminders', 'tasks'}:
        if bool(globals().get('directive_chat_enabled_v223', lambda _c: False)(cid)):
            if _v215_mode_enabled(cid, mode):
                v224_open_directive_mode_home(cid, uid, mid, mode)
            return True
        return _v215_go_mode(call, mode)
    return True
_V215_PREV_FORWARD_ANY_MESSAGE = _canon_forward_any_message__001

def _canon_forward_any_message__002(source_chat_id: int, msg):
    cid = int(source_chat_id)
    if _v215_circle_business_chat(cid) and (not contour_forwarding_mode_enabled(cid)):
        try:
            bot_journal('forward_mode_off_skip_v215', cid, f"message_id={int(getattr(msg, 'message_id', 0) or 0)}", 'INFO')
        except Exception:
            pass
        return
    return _V215_PREV_FORWARD_ANY_MESSAGE(cid, msg)
_V215_PREV_ADD_FORWARD_LINK = _canon_add_forward_link__001

def _canon_add_forward_link__002(src_chat_id: int, dst_chat_id: int, mode: str):
    result = _V215_PREV_ADD_FORWARD_LINK(int(src_chat_id), int(dst_chat_id), mode)
    if _v215_circle_business_chat(int(src_chat_id)):
        _v215_set_forward_mode(int(src_chat_id), True, persist=True)
    return result
_V215_PREV_REMOVE_FORWARD_LINK = _canon_remove_forward_link__001

def _canon_remove_forward_link__002(src_chat_id: int, dst_chat_id: int):
    result = _V215_PREV_REMOVE_FORWARD_LINK(int(src_chat_id), int(dst_chat_id))
    cid = int(src_chat_id)
    if _v215_circle_business_chat(cid) and (not _v215_forward_rules_present(cid)):
        _v215_set_forward_mode(cid, False, persist=True)
    return result
_V215_PREV_REMINDER_SEND_CYCLE = _canon_reminder_send_cycle__001

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
_V215_PREV_REMINDER_GROUP_SEND = _canon_reminder_group_send_job__001

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
_V215_PREV_START_HANDLER = _v213_cmd_start_contour

def _v215_cmd_start_modes(msg):
    try:
        cid = int(msg.chat.id)
        uid = int(getattr(getattr(msg, 'from_user', None), 'id', 0) or 0)
    except Exception:
        return _V215_PREV_START_HANDLER(msg)
    if not _v215_circle_business_chat(cid):
        return _V215_PREV_START_HANDLER(msg)
    try:
        update_chat_info_from_message(msg)
    except Exception:
        pass
    try:
        schedule_command_delete(msg)
    except Exception:
        pass
    try:
        if 'tenant_handle_start_payload' in globals() and tenant_handle_start_payload(msg):
            return
    except Exception:
        pass
    show_contour_start_modes(cid, uid, 0)
    try:
        bot_journal('start_mode_selector_v215', cid, f'circle={circle_level_for_chat(cid)}; user={uid}')
    except Exception:
        pass

def _v215_replace_start_handler() -> int:
    count = 0
    for row in list(getattr(bot, 'message_handlers', []) or []):
        if not isinstance(row, dict):
            continue
        fn = row.get('function')
        if fn is _V215_PREV_START_HANDLER or str(getattr(fn, '__name__', '')) == '_v213_cmd_start_contour':
            row['function'] = _v215_cmd_start_modes
            count += 1
    return count
_V215_START_REPLACED = _v215_replace_start_handler()
_V216_PREV_FORCE_START = _canon_v162_force_start__001

def _v216_force_start_contour_modes(msg) -> bool:
    try:
        cid = int(msg.chat.id)
        uid = int(getattr(getattr(msg, 'from_user', None), 'id', 0) or 0)
    except Exception:
        if callable(_V216_PREV_FORCE_START):
            return bool(_V216_PREV_FORCE_START(msg))
        return True
    try:
        payload_fn = globals().get('_v162_start_payload_present')
        if callable(payload_fn) and payload_fn(msg):
            return bool(_V216_PREV_FORCE_START(msg)) if callable(_V216_PREV_FORCE_START) else True
    except Exception:
        pass
    if _v215_circle_business_chat(cid):
        try:
            update_chat_info_from_message(msg)
        except Exception:
            pass
        try:
            set_total_secret_mode(cid, False)
        except Exception:
            pass
        try:
            stop_dozvon_for_target(cid)
        except Exception:
            pass
        try:
            schedule_command_delete(msg)
        except Exception:
            pass
        mid = show_contour_start_modes(cid, uid, 0)
        try:
            bot_journal('start_mode_selector_v216_hard', cid, f'circle={circle_level_for_chat(cid)}; user={uid}; msg={int(mid or 0)}')
        except Exception:
            pass
        return True
    if callable(_V216_PREV_FORCE_START):
        return bool(_V216_PREV_FORCE_START(msg))
    return True
try:
    _v177_legacy_0007_bot_journal('v216_circle_start_hardroute_ready', int(OWNER_ID or 0), 'circle1/2=/start selector; owner=legacy')
except Exception:
    pass
import re as _v217_re
V217_CONTOUR_MENU_VARIANT_KEY = 'contour_start_menu_variant_v217'
V217_CONTOUR_MENU_MARKER = 'Ф255'
V217_CHAT_REMINDERS_MARKER = 'Ф257'
V217_FORWARD_SCOPE_MARKER = 'Ф258'
try:
    WINDOW_MARKER_CONSTANTS.setdefault('v217:contour:menu', V217_CONTOUR_MENU_MARKER)
    WINDOW_MARKER_CONSTANTS.setdefault('v217:remchat:*', V217_CHAT_REMINDERS_MARKER)
    WINDOW_MARKER_CONSTANTS.setdefault('v217:fwdscope:*', V217_FORWARD_SCOPE_MARKER)
    WINDOW_MARKER_CONSTANTS.setdefault('v149:rem:item_complete:*', 'Ф191')
except Exception:
    pass

def _v217_rows(kb):
    return list(getattr(kb, 'keyboard', None) or getattr(kb, 'inline_keyboard', None) or [])

def _v217_set_rows(kb, rows):
    try:
        kb.keyboard = rows
    except Exception:
        try:
            kb.inline_keyboard = rows
        except Exception:
            pass
    return kb

def _v217_btn_cb(btn) -> str:
    if isinstance(btn, dict):
        return str(btn.get('callback_data') or '')
    return str(getattr(btn, 'callback_data', '') or '')

def _v217_btn_text(btn) -> str:
    if isinstance(btn, dict):
        return str(btn.get('text') or '')
    return str(getattr(btn, 'text', '') or '')

def _v217_insert_before_nav(kb, button) -> None:
    rows = _v217_rows(kb)
    if any((_v217_btn_cb(b) == _v217_btn_cb(button) for row in rows for b in row or [])):
        return
    idx = len(rows)
    for i, row in enumerate(rows):
        labels = ' '.join((_v217_btn_text(b) for b in row or [])).casefold()
        callbacks = ' '.join((_v217_btn_cb(b) for b in row or []))
        if 'назад' in labels or 'закры' in labels or 'back_main' in callbacks or ('aux_close' in callbacks):
            idx = i
            break
    rows.insert(idx, [button])
    _v217_set_rows(kb, rows)

def _v217_menu_variant_root() -> dict:
    gs = data.setdefault('_global_settings', {})
    root = gs.get(V217_CONTOUR_MENU_VARIANT_KEY)
    if not isinstance(root, dict):
        root = {'1': 1, '2': 1}
        gs[V217_CONTOUR_MENU_VARIANT_KEY] = root
    for key in ('1', '2'):
        try:
            value = int(root.get(key, 1) or 1)
        except Exception:
            value = 1
        root[key] = value if value in {1, 2, 3} else 1
    return root

def contour_start_menu_variant_v217(chat_id: int) -> int:
    try:
        level = 2 if int(circle_level_for_chat(int(chat_id))) == 2 else 1
    except Exception:
        level = 1
    return int(_v217_menu_variant_root().get(str(level), 1) or 1)

def set_contour_start_menu_variant_v217(level: int, variant: int) -> int:
    level = 2 if int(level) == 2 else 1
    variant = int(variant)
    if variant not in {1, 2, 3}:
        raise ValueError('variant must be 1..3')
    _v217_menu_variant_root()[str(level)] = variant
    try:
        save_data(data, root_only=True)
    except Exception:
        try:
            save_data(data)
        except Exception:
            pass
    try:
        schedule_delta_backup(int(OWNER_ID or 0), delay=0.2, reason=f'v217_contour_menu_variant_{level}')
    except Exception:
        pass
    try:
        bot_journal('contour_menu_variant_v217', int(OWNER_ID or 0), f'circle={level}; variant={variant}')
    except Exception:
        pass
    return variant
_V217_PREV_BUILD_CONTOUR_START_MODES = _canon_build_contour_start_modes__001

def _v217_build_contour_start_modes(chat_id: int, user_id: int=0):
    cid = int(chat_id)
    try:
        level = 2 if int(circle_level_for_chat(cid)) == 2 else 1
    except Exception:
        level = 1
    variant = contour_start_menu_variant_v217(cid)
    name = str(get_chat_display_name(cid) or f'Чат {cid}')
    states = [(mode, bool(_v215_mode_enabled(cid, mode))) for mode in ('finance', 'forward', 'reminders', 'tasks')]
    level_text = '1️⃣ первый' if level == 1 else '2️⃣ второй'
    if variant == 3:
        lines = ['🏠 ГЛАВНОЕ МЕНЮ', '', name, f'Контур: {level_text}', '', 'Состояние режимов:']
        for mode, enabled in states:
            lines.append(f"{('✅' if enabled else '⬜')} {_v215_mode_title(mode)}")
        lines += ['', 'Выберите раздел ниже. Нажатие раздела не меняет его состояние.', 'Команда /start и кнопка ☰ Меню всегда возвращают сюда.']
        text = window_mark('\n'.join(lines), V217_CONTOUR_MENU_MARKER)
        kb = types.InlineKeyboardMarkup(row_width=1)
        for mode, _enabled in states:
            kb.row(IB(_v215_mode_title(mode), callback_data=f'v215:mode:open:{mode}'))
    else:
        text = window_mark(f'🏠 ГЛАВНОЕ МЕНЮ\n\n{name}\nКонтур: {level_text}\n\nВыберите нужный раздел.\n✅ — режим включён    ⬜ — режим выключен\n\nНажатие на раздел открывает его карточку и само по себе ничего не переключает.\nКоманда /start и кнопка ☰ Меню всегда возвращают сюда.', V217_CONTOUR_MENU_MARKER)
        kb = types.InlineKeyboardMarkup(row_width=2 if variant == 2 else 1)
        buttons = [IB(f"{('✅' if enabled else '⬜')} {_v215_mode_title(mode)}", callback_data=f'v215:mode:open:{mode}') for mode, enabled in states]
        if variant == 2:
            kb.row(buttons[0], buttons[1])
            kb.row(buttons[2], buttons[3])
        else:
            for button in buttons:
                kb.row(button)
    kb.row(IB('ℹ️ Как пользоваться', callback_data='v215:mode:guide'))
    kb.row(IB('❌ Закрыть', callback_data='aux_close'))
    return (text, kb)
_V217_PREV_BUILD_MAIN_KEYBOARD = _canon_build_main_keyboard__001

def _v217_build_main_keyboard(day_key: str, chat_id=None):
    kb = _V217_PREV_BUILD_MAIN_KEYBOARD(day_key, chat_id)
    try:
        cid = int(chat_id) if chat_id is not None else int(current_state_chat_id() or 0)
        if _v215_circle_business_chat(cid):
            _v217_insert_before_nav(kb, IB('☰ Меню', callback_data='v217:contour:menu'))
    except Exception:
        pass
    return kb
_V217_PREV_TASK_HOME_KB = _canon_v174_menu_text_kb__001

def _v217_task_home_kb(chat_id: int, user_id: int=0):
    text, kb = _V217_PREV_TASK_HOME_KB(int(chat_id), int(user_id or 0))
    try:
        if _v215_circle_business_chat(int(chat_id)):
            _v217_insert_before_nav(kb, IB('☰ Меню', callback_data='v217:contour:menu'))
    except Exception:
        pass
    return (text, kb)
_V217_PREV_FORWARD_PICKER_ITEMS = _canon_collect_forward_picker_items__001

def _canon_collect_forward_picker_items__002(include_owner: bool=True, include_removed: bool=False):
    rows, extra = _V217_PREV_FORWARD_PICKER_ITEMS(include_owner=include_owner, include_removed=include_removed) if callable(_V217_PREV_FORWARD_PICKER_ITEMS) else ([], None)
    try:
        ctx = int(current_state_chat_id() or 0)
        if not _v215_circle_business_chat(ctx):
            return (rows, extra)
        tid = str(tenant_id_for_chat(ctx, create=False) or '')
        allowed = set((int(x) for x in tenant_chat_ids(tid)))
        clean = [(int(cid), title) for cid, title in rows if int(cid) in allowed]
        return (clean, None)
    except Exception:
        return ([], None)
_V217_PREV_FORWARD_PAIRS = _canon_collect_forward_pairs_for_menu__001

def _canon_collect_forward_pairs_for_menu__002() -> list[tuple[int, int]]:
    rows = _V217_PREV_FORWARD_PAIRS() if callable(_V217_PREV_FORWARD_PAIRS) else []
    try:
        ctx = int(current_state_chat_id() or 0)
        if not _v215_circle_business_chat(ctx):
            return [(int(a), int(b)) for a, b in rows]
        tid = str(tenant_id_for_chat(ctx, create=False) or '')
        allowed = set((int(x) for x in tenant_chat_ids(tid)))
        return [(int(a), int(b)) for a, b in rows if int(a) in allowed and int(b) in allowed]
    except Exception:
        return []

def _v217_forward_scope_guard(src_chat_id: int, dst_chat_id: int) -> None:
    try:
        ctx = int(current_state_chat_id() or 0)
    except Exception:
        ctx = 0
    if not ctx or not _v215_circle_business_chat(ctx):
        return
    tid = str(tenant_id_for_chat(ctx, create=False) or '')
    allowed = set((int(x) for x in tenant_chat_ids(tid)))
    if int(src_chat_id) not in allowed or int(dst_chat_id) not in allowed or (not tenant_same_space(int(src_chat_id), int(dst_chat_id))):
        raise PermissionError('Связь пересылки находится вне текущего пространства')
_V217_PREV_ADD_FORWARD_LINK = _canon_add_forward_link__002

def _v217_add_forward_link(src_chat_id: int, dst_chat_id: int, mode: str):
    _v217_forward_scope_guard(int(src_chat_id), int(dst_chat_id))
    return _V217_PREV_ADD_FORWARD_LINK(int(src_chat_id), int(dst_chat_id), mode)
_V217_PREV_REMOVE_FORWARD_LINK = _canon_remove_forward_link__002

def _v217_remove_forward_link(src_chat_id: int, dst_chat_id: int):
    _v217_forward_scope_guard(int(src_chat_id), int(dst_chat_id))
    return _V217_PREV_REMOVE_FORWARD_LINK(int(src_chat_id), int(dst_chat_id))
_V217_PREV_SET_FORWARD_FINANCE = _canon_set_forward_finance__001

def _canon_set_forward_finance__002(src_chat_id: int, dst_chat_id: int, enabled: bool):
    _v217_forward_scope_guard(int(src_chat_id), int(dst_chat_id))
    return _V217_PREV_SET_FORWARD_FINANCE(int(src_chat_id), int(dst_chat_id), bool(enabled))
_V217_PREV_REMOVE_FORWARD_FINANCE = _canon_remove_forward_finance__001

def _canon_remove_forward_finance__002(src_chat_id: int, dst_chat_id: int):
    _v217_forward_scope_guard(int(src_chat_id), int(dst_chat_id))
    return _V217_PREV_REMOVE_FORWARD_FINANCE(int(src_chat_id), int(dst_chat_id))
_V217_PREV_FORWARD_MENU_KB = _canon_build_forward_menu_keyboard_for_current_mode__001

def _canon_build_forward_menu_keyboard_for_current_mode__002(day_key: str | None=None, A: int | None=None, B: int | None=None):
    kb = _V217_PREV_FORWARD_MENU_KB(day_key, A, B)
    try:
        cid = int(current_state_chat_id() or 0)
        if _v215_circle_business_chat(cid):
            rows = []
            for row in _v217_rows(kb):
                kept = [b for b in row or [] if not _v217_btn_cb(b).startswith('v164:circle:forward:')]
                if kept:
                    rows.append(kept)
            _v217_set_rows(kb, rows)
            _v217_insert_before_nav(kb, IB('☰ Меню', callback_data='v217:contour:menu'))
    except Exception:
        pass
    return kb

def _v217_forward_scope_rows(chat_id: int) -> tuple[list[int], list[tuple[int, int, str, bool]]]:
    cid = int(chat_id)
    tid = str(tenant_id_for_chat(cid, create=False) or '')
    allowed = sorted(set((int(x) for x in tenant_chat_ids(tid))), key=lambda x: str(get_chat_display_name(x) or x).casefold())
    pairs = []
    fr = data.get('forward_rules', {}) or {}
    ff = data.get('forward_finance', {}) or {}
    seen = set()
    for src_raw, dsts in fr.items():
        try:
            src = int(src_raw)
        except Exception:
            continue
        if src not in allowed:
            continue
        for dst_raw, mode in (dsts or {}).items():
            try:
                dst = int(dst_raw)
            except Exception:
                continue
            if dst not in allowed:
                continue
            key = (src, dst)
            if key in seen:
                continue
            seen.add(key)
            pairs.append((src, dst, str(mode or 'copy'), bool((ff.get(str(src)) or {}).get(str(dst), False))))
    return (allowed, pairs)

def build_v217_forward_scope_text(chat_id: int) -> str:
    allowed, pairs = _v217_forward_scope_rows(int(chat_id))
    lines = ['📤 ПЕРЕСЫЛКА ЭТОГО ПРОСТРАНСТВА', '', f'Чатов: {len(allowed)} · связей: {len(pairs)}', '']
    if not pairs:
        lines.append('Связи пересылки для этого пространства пока не настроены.')
    else:
        for src, dst, mode, fin in pairs[:30]:
            lines.append(f'• {get_chat_display_name(src)} → {get_chat_display_name(dst)} · {mode}' + (' · 💰' if fin else ''))
    lines += ['', 'Здесь никогда не показываются связи других контуров.']
    return window_mark('\n'.join(lines)[:3900], V217_FORWARD_SCOPE_MARKER)

def _canon_build_v217_forward_scope_keyboard__001(chat_id: int, user_id: int):
    kb = types.InlineKeyboardMarkup(row_width=1)
    can_manage = False
    try:
        can_manage = bool(security_user_allowed(int(user_id or 0), 'forward_manage'))
    except Exception:
        pass
    if can_manage:
        kb.row(IB('⚙️ Открыть настройки пересылки', callback_data='v217:fwdscope:manage'))
    kb.row(IB('🔙 К режиму', callback_data='v215:mode:open:forward'))
    kb.row(IB('☰ Меню', callback_data='v217:contour:menu'))
    return kb
_V217_PREV_REMINDER_MESSAGE_TEXT = _canon_v149_reminder_message_text__001

def _canon_v149_reminder_message_text__002(reminder_id: int, cfg: dict, chat_id: int, active_count: int=1) -> str:
    return '\n'.join([f'НАПОМИНАЛКА #{int(reminder_id)}🕰️', '', str((cfg or {}).get('text') or '').strip()])[:4000]
_V217_PREV_GROUP_MESSAGE_TEXT = _canon_v149_group_message_text__001

def _canon_v149_group_message_text__002(chat_id: int, members: list[tuple[int, dict]]) -> str:
    lines = ['НАПОМИНАЛКА🕰️', '']
    for rid, cfg in members:
        block = f"#{int(rid)}. {str((cfg or {}).get('text') or '').strip()}"
        if len('\n'.join(lines + [block])) > 3900:
            lines.append('…')
            break
        lines.append(block)
    return '\n'.join(lines)[:4000]

def _canon_v207_reminder_complete_keyboard__002(reminder_id: int, cfg: dict, chat_id: int):
    if not _v207_reminder_complete_button_enabled(cfg, chat_id):
        return None
    kb = types.InlineKeyboardMarkup(row_width=1)
    kb.row(IB('✅ Выполнено', callback_data=f'v149:rem:done:{int(reminder_id)}:{int(chat_id)}'))
    return kb

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
_V217_PREV_REMINDER_LIST_KB = _canon_build_reminder_list_keyboard__001

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

def _v217_reminder_status(cfg: dict) -> str:
    if _reminder_is_completed(cfg):
        return '✅ выполнена'
    if bool(cfg.get('enabled')):
        return '✅ активна'
    return '⬜ выключена'

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

def _v217_complete_command(msg) -> bool:
    text = str(getattr(msg, 'text', '') or '').strip()
    match = _v217_re.match('^/выполнено(?:@[A-Za-z0-9_]+)?(?:\\s+#?(\\d+))?\\s*$', text, _v217_re.I)
    if not match:
        match = _v217_re.match('^/done(?:@[A-Za-z0-9_]+)?\\s+#?(\\d+)\\s*$', text, _v217_re.I)
    if not match:
        return False
    try:
        cid = int(msg.chat.id)
        uid = int(getattr(getattr(msg, 'from_user', None), 'id', 0) or 0)
    except Exception:
        return True
    try:
        schedule_command_delete(msg)
    except Exception:
        pass
    rid = int(match.group(1)) if match.group(1) else None
    if rid is None:
        reply = getattr(msg, 'reply_to_message', None)
        if reply is None:
            send_and_auto_delete(cid, 'Укажите конкретную напоминалку: /выполнено #N или ответьте этой командой на её сообщение.', 12)
            return True
        rid, error = _v217_find_reply_reminder(cid, int(getattr(reply, 'message_id', 0) or 0))
        if rid is None:
            send_and_auto_delete(cid, error, 12)
            return True
    cfg = _reminder_cfg(int(rid))
    if not cfg or cid not in [int(x) for x in cfg.get('chat_ids') or [] if str(x).lstrip('-').isdigit()]:
        send_and_auto_delete(cid, f'Напоминалка #{int(rid)} не относится к этому чату.', 12)
        return True
    ok, answer = _v149_complete_reminder(int(rid), cid, uid, _v149_actor_label(msg))
    send_and_auto_delete(cid, answer, 12)
    return True
_V217_PREV_PROCESS_NEW_UPDATES = getattr(bot, 'process_new_updates', None)

def _v217_process_new_updates(updates):
    remaining = []
    for update in list(updates or []):
        msg = getattr(update, 'message', None)
        if msg is not None:
            try:
                if _v217_complete_command(msg):
                    continue
            except Exception as exc:
                try:
                    log_error(f'v217 reminder complete command: {exc}')
                except Exception:
                    pass
        remaining.append(update)
    if remaining and callable(_V217_PREV_PROCESS_NEW_UPDATES):
        return _V217_PREV_PROCESS_NEW_UPDATES(remaining)
    return None
if callable(_V217_PREV_PROCESS_NEW_UPDATES):
    bot.process_new_updates = _v217_process_new_updates
_V217_PREV_GO_MODE = _canon_v215_go_mode__001

def _v217_go_mode(call, mode: str) -> bool:
    cid = int(call.message.chat.id)
    uid = int(getattr(getattr(call, 'from_user', None), 'id', 0) or 0)
    mode = str(mode or '')
    if not _v215_mode_enabled(cid, mode):
        try:
            bot.answer_callback_query(call.id, 'Сначала включите режим.', show_alert=False)
        except Exception:
            pass
        return True
    if mode == 'forward' and _v215_circle_business_chat(cid):
        tid = str(tenant_id_for_chat(cid, create=False) or '')
        can_manage = False
        try:
            can_manage = bool(security_user_allowed(uid, 'forward_manage'))
        except Exception:
            pass
        if not can_manage:
            safe_edit(bot, call, build_v217_forward_scope_text(cid), reply_markup=build_v217_forward_scope_keyboard(cid, uid))
            return True
        try:
            with tenant_context(tid):
                day = today_key()
                kb = build_forward_menu_keyboard_for_current_mode(day)
                safe_edit(bot, call, build_forward_menu_text_for_current_mode('Пересылка:\nВыберите чат A:'), reply_markup=kb)
        except Exception as exc:
            try:
                log_error(f'v217 scoped forward menu {cid}: {exc}')
            except Exception:
                pass
        return True
    if mode == 'reminders' and _v215_circle_business_chat(cid):
        can_manage = False
        try:
            can_manage = bool(security_user_allowed(uid, 'reminder_manage'))
        except Exception:
            pass
        if not can_manage:
            safe_edit(bot, call, build_v217_chat_reminders_text(cid), reply_markup=build_v217_chat_reminders_keyboard(cid, uid))
            return True
        tid = str(tenant_id_for_chat(cid, create=False) or '')
        with tenant_context(tid):
            safe_edit(bot, call, build_reminder_list_text(), reply_markup=build_reminder_list_keyboard(today_key(), 0))
        return True
    return _V217_PREV_GO_MODE(call, mode)

def _canon_v217_callback_final__001(call, resolved: str) -> bool:
    raw = str(resolved or '')
    try:
        cid = int(call.message.chat.id)
        uid = int(getattr(getattr(call, 'from_user', None), 'id', 0) or 0)
        mid = int(call.message.message_id)
    except Exception:
        return True
    if raw == 'v217:contour:menu':
        if not _v215_circle_business_chat(cid):
            return True
        try:
            bot.answer_callback_query(call.id)
        except Exception:
            pass
        show_contour_start_modes(cid, uid, mid)
        return True
    if raw == 'v217:remchat:list':
        if not _v215_circle_business_chat(cid):
            return True
        try:
            bot.answer_callback_query(call.id)
        except Exception:
            pass
        safe_edit(bot, call, build_v217_chat_reminders_text(cid), reply_markup=build_v217_chat_reminders_keyboard(cid, uid))
        return True
    if raw.startswith('v217:remchat:open:'):
        try:
            rid = int(raw.rsplit(':', 1)[1])
        except Exception:
            return True
        try:
            if not security_user_allowed(uid, 'reminder_manage'):
                bot.answer_callback_query(call.id, 'Недостаточно прав для изменения напоминалки.', show_alert=True)
                return True
        except Exception:
            return True
        cfg = _reminder_cfg(rid)
        if not cfg or cid not in [int(x) for x in cfg.get('chat_ids') or [] if str(x).lstrip('-').isdigit()]:
            try:
                bot.answer_callback_query(call.id, 'Эта напоминалка не относится к текущему чату.', show_alert=True)
            except Exception:
                pass
            return True
        try:
            bot.answer_callback_query(call.id)
        except Exception:
            pass
        try:
            _reminder_bind_editor(rid, cid, mid, today_key(), 0)
        except Exception:
            pass
        safe_edit(bot, call, build_reminder_menu_text(rid), reply_markup=build_reminder_menu_keyboard(rid, today_key(), 0, viewer_chat_id=cid))
        return True
    if raw == 'v217:fwdscope:manage':
        if not _v215_circle_business_chat(cid):
            return True
        try:
            if not security_user_allowed(uid, 'forward_manage'):
                bot.answer_callback_query(call.id, 'Недостаточно прав.', show_alert=True)
                return True
        except Exception:
            return True
        try:
            bot.answer_callback_query(call.id)
        except Exception:
            pass
        tid = str(tenant_id_for_chat(cid, create=False) or '')
        with tenant_context(tid):
            safe_edit(bot, call, build_forward_menu_text_for_current_mode('Пересылка:\nВыберите чат A:'), reply_markup=build_forward_menu_keyboard_for_current_mode(today_key()))
        return True
    if raw.startswith('v149:rem:item_complete:'):
        parts = raw.split(':')
        try:
            rid = int(parts[3])
            page = int(parts[4])
            day_key = str(parts[5])
        except Exception:
            return True
        try:
            if not security_user_allowed(uid, 'reminder_manage'):
                bot.answer_callback_query(call.id, 'Недостаточно прав.', show_alert=True)
                return True
        except Exception:
            return True
        cfg = _reminder_cfg(rid)
        if not cfg:
            return True
        current = bool(_v207_reminder_complete_button_enabled(cfg, cid))
        cfg['show_complete_button_v207'] = not current
        try:
            cfg['updated_at'] = now_local().isoformat(timespec='seconds')
        except Exception:
            pass
        _reminder_save('v217_reminder_complete_button')
        try:
            bot.answer_callback_query(call.id, 'Кнопка «Выполнено»: ' + ('✅ ВКЛ' if not current else '⬜ ВЫКЛ'))
        except Exception:
            pass
        safe_edit(bot, call, build_reminder_menu_text(rid), reply_markup=build_reminder_menu_keyboard(rid, day_key, page, viewer_chat_id=cid))
        return True
    return False
try:
    _v177_legacy_0007_bot_journal('v217_contour_menu_forward_reminder_ready', int(OWNER_ID or 0), 'menu_variants=3; forward_scope=tenant; reminder_done=button+commands+reply')
except Exception:
    pass
import re as _v218_re
V218_REMINDER_COMPLETION_KEY = 'completion_mode_v218'
V218_REMINDER_COMPLETION_MODES = ('button', 'slash', 'none')
V218_DEMO_MARKER = 'Ф260'
try:
    WINDOW_MARKER_CONSTANTS.setdefault('v218:demo:*', V218_DEMO_MARKER)
except Exception:
    pass

def _v218_completion_mode(cfg: dict | None, chat_id: int | None=None) -> str:
    """Read the v218 3-state completion setting without mutating reminder state.

    Migration preserves v217 behaviour: legacy inline ON -> button; legacy inline OFF -> slash,
    because v217 still allowed exact slash completion when its inline button was disabled.
    """
    if not isinstance(cfg, dict):
        return 'none'
    raw = str(cfg.get(V218_REMINDER_COMPLETION_KEY) or '').strip().lower()
    if raw in V218_REMINDER_COMPLETION_MODES:
        return raw
    legacy = cfg.get('show_complete_button_v207', None)
    if legacy is True:
        return 'button'
    if legacy is False:
        return 'slash'
    try:
        previous = globals().get('_V218_PREV_COMPLETE_ENABLED')
        if callable(previous) and previous(cfg, chat_id):
            return 'button'
    except Exception:
        pass
    return 'slash'

def _v218_completion_label(cfg: dict | None, chat_id: int | None=None) -> str:
    mode = _v218_completion_mode(cfg, chat_id)
    return {'button': '✅ Выполнение: КНОПКА', 'slash': '✅ Выполнение: SLASH', 'none': '⬜ Выполнение: НЕТ'}.get(mode, '⬜ Выполнение: НЕТ')

def _v218_cycle_completion_mode(cfg: dict, chat_id: int | None=None) -> str:
    current = _v218_completion_mode(cfg, chat_id)
    nxt = {'button': 'slash', 'slash': 'none', 'none': 'button'}.get(current, 'button')
    cfg[V218_REMINDER_COMPLETION_KEY] = nxt
    cfg['show_complete_button_v207'] = nxt == 'button'
    try:
        cfg['updated_at'] = now_local().isoformat(timespec='seconds')
    except Exception:
        pass
    return nxt
_V218_PREV_COMPLETE_ENABLED = _canon_v207_reminder_complete_button_enabled__001

def _v218_reminder_complete_button_enabled(cfg: dict | None, chat_id: int | None=None) -> bool:
    return _v218_completion_mode(cfg, chat_id) == 'button'
_V218_PREV_REMINDER_MESSAGE_TEXT = _canon_v149_reminder_message_text__002

def _v218_reminder_message_text(reminder_id: int, cfg: dict, chat_id: int, active_count: int=1) -> str:
    lines = [f'НАПОМИНАЛКА #{int(reminder_id)}🕰️', '', str((cfg or {}).get('text') or '').strip()]
    if _v218_completion_mode(cfg, chat_id) == 'slash':
        lines += ['', f'Выполнить: /done_{int(reminder_id)}']
    return '\n'.join(lines)[:4000]
_V218_PREV_GROUP_MESSAGE_TEXT = _canon_v149_group_message_text__002

def _v218_group_message_text(chat_id: int, members: list[tuple[int, dict]]) -> str:
    lines = ['НАПОМИНАЛКА🕰️', '']
    for rid, cfg in members:
        block = f"#{int(rid)}. {str((cfg or {}).get('text') or '').strip()}"
        if _v218_completion_mode(cfg, chat_id) == 'slash':
            block += f'\n   Выполнить: /done_{int(rid)}'
        if len('\n'.join(lines + [block])) > 3900:
            lines.append('…')
            break
        lines.append(block)
    return '\n'.join(lines)[:4000]

def _v218_reminder_complete_keyboard(reminder_id: int, cfg: dict, chat_id: int):
    if _v218_completion_mode(cfg, chat_id) != 'button':
        return None
    kb = types.InlineKeyboardMarkup(row_width=1)
    kb.row(IB('✅ Выполнить', callback_data=f'v149:rem:done:{int(reminder_id)}:{int(chat_id)}'))
    return kb

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
_V218_PREV_REMINDER_MENU_KB = _canon_build_reminder_menu_keyboard__001

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
_V218_PREV_REMINDERS_FOR_COMPLETION = _canon_v149_reminders_for_completion__001

def _v218_reminders_for_completion(chat_id: int) -> list[tuple[int, dict]]:
    rows = _V218_PREV_REMINDERS_FOR_COMPLETION(int(chat_id))
    return [(rid, cfg) for rid, cfg in rows if _v218_completion_mode(cfg, int(chat_id)) == 'slash']

def _v218_completion_command_target(msg) -> tuple[int | None, bool]:
    text = str(getattr(msg, 'text', '') or '').strip()
    patterns = ('^/done_(\\d+)(?:@[A-Za-z0-9_]+)?\\s*$', '^/vyapl_(\\d+)(?:@[A-Za-z0-9_]+)?\\s*$', '^/done(?:@[A-Za-z0-9_]+)?\\s+#?(\\d+)\\s*$', '^/выполнено(?:@[A-Za-z0-9_]+)?\\s+#?(\\d+)\\s*$')
    for pattern in patterns:
        match = _v218_re.match(pattern, text, _v218_re.I)
        if match:
            return (int(match.group(1)), True)
    if _v218_re.match('^/выполнено(?:@[A-Za-z0-9_]+)?\\s*$', text, _v218_re.I):
        return (None, True)
    return (None, False)

def _canon_v218_complete_command__001(msg) -> bool:
    rid, matched = _v218_completion_command_target(msg)
    if not matched:
        return False
    try:
        cid = int(msg.chat.id)
        uid = int(getattr(getattr(msg, 'from_user', None), 'id', 0) or 0)
    except Exception:
        return True
    try:
        schedule_command_delete(msg)
    except Exception:
        pass
    if rid is None:
        reply = getattr(msg, 'reply_to_message', None)
        if reply is None:
            send_and_auto_delete(cid, 'Укажите конкретную напоминалку: /done_N или ответьте /выполнено на её сообщение.', 12)
            return True
        rid, error = _v217_find_reply_reminder(cid, int(getattr(reply, 'message_id', 0) or 0))
        if rid is None:
            send_and_auto_delete(cid, error, 12)
            return True
    cfg = _reminder_cfg(int(rid))
    recipients = [int(x) for x in (cfg or {}).get('chat_ids') or [] if str(x).lstrip('-').isdigit()]
    if not cfg or cid not in recipients:
        send_and_auto_delete(cid, f'Напоминалка #{int(rid)} не относится к этому чату.', 12)
        return True
    try:
        if not _v149_reminder_chat_allowed(cfg, cid):
            send_and_auto_delete(cid, f'Напоминалка #{int(rid)} недоступна в этом пространстве.', 12)
            return True
    except Exception:
        pass
    if _v218_completion_mode(cfg, cid) != 'slash':
        mode = _v218_completion_mode(cfg, cid)
        text = 'Для этой напоминалки выбран способ выполнения «КНОПКА».' if mode == 'button' else 'Для этой напоминалки выполнение отключено.'
        send_and_auto_delete(cid, text, 12)
        return True
    ok, answer = _v149_complete_reminder(int(rid), cid, uid, _v149_actor_label(msg))
    send_and_auto_delete(cid, answer, 12)
    return True
_V218_PREV_PROCESS_NEW_UPDATES = getattr(bot, 'process_new_updates', None)

def _v218_process_new_updates(updates):
    remaining = []
    for update in list(updates or []):
        msg = getattr(update, 'message', None)
        if msg is not None:
            try:
                if _v218_complete_command(msg):
                    continue
            except Exception as exc:
                try:
                    log_error(f'v218 reminder completion command: {exc}')
                except Exception:
                    pass
        remaining.append(update)
    if remaining and callable(_V218_PREV_PROCESS_NEW_UPDATES):
        return _V218_PREV_PROCESS_NEW_UPDATES(remaining)
    return None
if callable(_V218_PREV_PROCESS_NEW_UPDATES):
    bot.process_new_updates = _v218_process_new_updates

def _v218_demo_title(mode: str) -> str:
    return {'finance': '💰 ФИНАНСЫ', 'forward': '🔁 ПЕРЕСЫЛКА', 'reminders': '⏰ НАПОМИНАНИЯ', 'tasks': '📋 ЗАДАЧИ'}.get(str(mode), 'РЕЖИМ')
_V218_DEMO_DESCRIPTIONS = {'finance': {'prev': '⬅️ Предыдущий день — показывает финансовые данные предыдущего дня.', 'next': '➡️ Следующий день — переключает просмотр на следующий день.', 'calendar': '📅 Календарь — позволяет выбрать дату финансового просмотра.', 'report': '📊 Отчёт — открывает отчёты и выбор периода.', 'total': '💰 Общий итог — показывает общий финансовый итог.', 'edit': '📝 Редактировать — открывает список записей для изменения или удаления.', 'csv': '📂 CSV — формирует выгрузку финансов за выбранный период.', 'articles': '📊 Статьи — показывает расходы и доходы по статьям.', 'info': 'ℹ️ Инфо — открывает справочную и служебную информацию.', 'day': 'День — формирует отчёт за выбранный день.', 'week': 'Неделя — формирует отчёт за неделю.', 'month': 'Месяц — формирует отчёт за месяц.', 'year': 'Год — формирует отчёт за год.'}, 'forward': {'links': '🔗 Связи пересылки — показывает настроенные направления внутри этого пространства.', 'add': '➕ Добавить связь — позволяет выбрать источник и получателя пересылки.', 'finance': '💰 Финансовая пересылка — управляет переносом финансового контекста вместе с сообщениями.', 'chats': '📋 Чаты пространства — показывает чаты, доступные для настройки пересылки.', 'settings': '⚙️ Настройки — открывает параметры режима пересылки.'}, 'reminders': {'add': '➕ Напоминалка — создаёт новую напоминалку и позволяет выбрать текст, чаты и расписание.', 'active': '📋 Активные — показывает действующие напоминалки.', 'completed': '✅ Завершённые — показывает выполненные и завершившиеся напоминалки.', 'chat': '📋 Напоминалки этого чата — показывает только напоминалки, где этот чат указан получателем.', 'schedule': '📅 Расписание — показывает даты, время и период повторения.', 'settings': '⚙️ Настройки — открывает параметры напоминаний.'}, 'tasks': {'new': '➕ Задача — создаёт новую задачу.', 'purchase': '🛒 Покупка — создаёт задачу-покупку.', 'active': '📌 Активные задачи — показывает незавершённые задачи этого чата.', 'mine': '🙋 Мои — показывает задачи, назначенные текущему пользователю.', 'urgent': '🔴 Срочные — показывает задачи с высоким приоритетом.', 'deferred': '⏸ Отложенные — показывает отложенные задачи.', 'done': '✅ Выполненные — показывает завершённые задачи.', 'cancelled': '❌ Отменённые — показывает отменённые задачи.', 'keywords': '⚙️ Ключевые слова — настраивает автоматическое распознавание задач.', 'branch': '➕ Добавить ветку задач — создаёт пользовательскую ветку задач и её ключевые слова.'}}

def _v218_demo_text(chat_id: int, mode: str, note: str='') -> str:
    warning = '👁 ОЗНАКОМИТЕЛЬНЫЙ РЕЖИМ\n\nРежим сейчас выключен. Это ознакомительный просмотр.\nЗдесь можно посмотреть назначение кнопок, но бизнес-действия не выполняются.'
    body = {'finance': 'Можно посмотреть назначение финансовых экранов, отчётов, календаря и редактирования.', 'forward': 'Можно посмотреть назначение связей и настроек пересылки этого пространства.', 'reminders': 'Можно посмотреть создание, списки, расписание и завершённые напоминалки.', 'tasks': 'Можно посмотреть создание задач, списки, ветки и ключевые слова.'}.get(mode, 'Можно ознакомиться с интерфейсом режима.')
    suffix = f'\n\nℹ️ {note}' if str(note).strip() else ''
    return window_mark(f'{_v218_demo_title(mode)}\n\n{warning}\n\n{body}{suffix}', V218_DEMO_MARKER)

def _v218_demo_nav(kb, mode: str, sub: bool=False):
    if sub:
        kb.row(IB('🔙 Назад', callback_data=f'v218:demo:{mode}:root'))
    else:
        kb.row(IB('🔙 К режиму', callback_data=f'v215:mode:open:{mode}'))
    kb.row(IB('☰ Меню', callback_data='v217:contour:menu'), IB('❌ Закрыть', callback_data='aux_close'))
    return kb

def _v218_demo_keyboard(mode: str, page: str='root'):
    mode = str(mode)
    kb = types.InlineKeyboardMarkup(row_width=2)
    if mode == 'finance' and page == 'report':
        kb.row(IB('📅 День', callback_data='v218:demo:finance:desc:day'), IB('🗓 Неделя', callback_data='v218:demo:finance:desc:week'))
        kb.row(IB('📆 Месяц', callback_data='v218:demo:finance:desc:month'), IB('🗓 Год', callback_data='v218:demo:finance:desc:year'))
        return _v218_demo_nav(kb, mode, True)
    rows = {'finance': [[('⬅️ Предыдущий день', 'prev'), ('➡️ Следующий день', 'next')], [('📅 Календарь', 'calendar'), ('📊 Отчёт', 'sub_report')], [('💰 Общий итог', 'total'), ('📝 Редактировать', 'edit')], [('📂 CSV', 'csv'), ('📊 Статьи', 'articles')], [('ℹ️ Инфо', 'info')]], 'forward': [[('🔗 Связи пересылки', 'links')], [('➕ Добавить связь', 'add')], [('💰 Финансовая пересылка', 'finance')], [('📋 Чаты пространства', 'chats')], [('⚙️ Настройки', 'settings')]], 'reminders': [[('➕ Напоминалка', 'add')], [('📋 Активные', 'active'), ('✅ Завершённые', 'completed')], [('📋 Напоминалки этого чата', 'chat')], [('📅 Расписание', 'schedule')], [('⚙️ Настройки', 'settings')]], 'tasks': [[('➕ Задача', 'new'), ('🛒 Покупка', 'purchase')], [('📌 Активные', 'active'), ('🙋 Мои', 'mine')], [('🔴 Срочные', 'urgent'), ('⏸ Отложенные', 'deferred')], [('✅ Выполненные', 'done'), ('❌ Отменённые', 'cancelled')], [('⚙️ Ключевые слова', 'keywords')], [('➕ Добавить ветку задач', 'branch')]]}.get(mode, [])
    for row in rows:
        buttons = []
        for label, key in row:
            if key == 'sub_report':
                cb = 'v218:demo:finance:sub:report'
            else:
                cb = f'v218:demo:{mode}:desc:{key}'
            buttons.append(IB(label, callback_data=cb))
        if buttons:
            kb.row(*buttons)
    return _v218_demo_nav(kb, mode, False)

def _v218_show_demo(call, mode: str, page: str='root', note: str='') -> None:
    text = _v218_demo_text(int(call.message.chat.id), mode, note)
    if page == 'report':
        text = window_mark(f'{_v218_demo_title(mode)} · 📊 ОТЧЁТЫ\n\n👁 ОЗНАКОМИТЕЛЬНЫЙ РЕЖИМ\n\nРежим сейчас выключен. Отчёты здесь не формируются.\nВыберите период, чтобы прочитать назначение кнопки.' + (f'\n\nℹ️ {note}' if note else ''), V218_DEMO_MARKER)
    safe_edit(bot, call, text, reply_markup=_v218_demo_keyboard(mode, page))
_V218_PREV_GO_MODE = _v217_go_mode

def _v218_go_mode(call, mode: str) -> bool:
    try:
        cid = int(call.message.chat.id)
    except Exception:
        return _V218_PREV_GO_MODE(call, mode)
    if _v215_circle_business_chat(cid) and (not _v215_mode_enabled(cid, mode)):
        try:
            bot.answer_callback_query(call.id, 'Этот режим сейчас выключен. Возвращаю в меню режимов.')
        except Exception:
            pass
        try:
            show_contour_start_modes(cid, int(getattr(getattr(call, 'from_user', None), 'id', 0) or 0), int(call.message.message_id))
        except Exception:
            pass
        try:
            bot_journal('contour_disabled_mode_redirect_r10', cid, f'mode={mode}; source=go')
        except Exception:
            pass
        return True
    return _V218_PREV_GO_MODE(call, mode)
_V218_PREV_MODE_CONTROL = _canon_build_contour_mode_control__001

def _v218_build_contour_mode_control(chat_id: int, user_id: int, mode: str):
    text, kb = _V218_PREV_MODE_CONTROL(int(chat_id), int(user_id or 0), str(mode))
    try:
        if _v215_circle_business_chat(int(chat_id)) and (not _v215_mode_enabled(int(chat_id), str(mode))):
            marker = V215_CONTOUR_MODE_MARKER
            plain = str(text)
            if 'Можно открыть ознакомительный просмотр' not in plain:
                plain = plain.rsplit('\n\n' + marker, 1)[0] if plain.rstrip().endswith(marker) else plain
                text = window_mark(plain.rstrip() + '\n\n👁 Можно открыть ознакомительный просмотр без включения режима.', marker)
            for row in _v217_rows(kb):
                for btn in row or []:
                    if _v217_btn_cb(btn) == f'v215:mode:go:{mode}':
                        label = '👁 Перейти в ознакомительный режим'
                        if isinstance(btn, dict):
                            btn['text'] = label
                        else:
                            btn.text = label
    except Exception:
        pass
    return (text, kb)

def _canon_v218_callback_final__001(call, resolved: str) -> bool:
    raw = str(resolved or '')
    try:
        cid = int(call.message.chat.id)
        uid = int(getattr(getattr(call, 'from_user', None), 'id', 0) or 0)
    except Exception:
        return True
    if raw.startswith('v149:rem:item_complete:'):
        parts = raw.split(':')
        try:
            rid = int(parts[3])
            page = int(parts[4])
            day_key = str(parts[5])
        except Exception:
            return True
        try:
            if not security_user_allowed(uid, 'reminder_manage'):
                bot.answer_callback_query(call.id, 'Недостаточно прав.', show_alert=True)
                return True
        except Exception:
            return True
        cfg = _reminder_cfg(rid)
        if not cfg:
            try:
                bot.answer_callback_query(call.id, 'Напоминалка не найдена.', show_alert=True)
            except Exception:
                pass
            return True
        new_mode = _v218_cycle_completion_mode(cfg, cid)
        _reminder_save('v218_reminder_completion_mode')
        try:
            REMINDER_TASK_POOL.submit_unique('reminder-v149-batch', _v149_reminder_batch_job, int(cid))
        except Exception:
            pass
        try:
            bot.answer_callback_query(call.id, _v218_completion_label(cfg, cid).replace('✅ ', '').replace('⬜ ', ''))
        except Exception:
            pass
        safe_edit(bot, call, build_reminder_menu_text(rid), reply_markup=build_reminder_menu_keyboard(rid, day_key, page, viewer_chat_id=cid))
        try:
            bot_journal('reminder_completion_mode_v218', cid, f'reminder_id={rid}; mode={new_mode}')
        except Exception:
            pass
        return True
    if raw.startswith('v149:rem:done:'):
        parts = raw.split(':')
        try:
            rid = int(parts[3])
            payload_chat = int(parts[4])
        except Exception:
            return True
        cfg = _reminder_cfg(rid)
        if payload_chat != cid or not cfg or cid not in [int(x) for x in cfg.get('chat_ids') or [] if str(x).lstrip('-').isdigit()]:
            try:
                bot.answer_callback_query(call.id, 'Эта напоминалка не относится к текущему чату.', show_alert=True)
            except Exception:
                pass
            return True
        if _v218_completion_mode(cfg, cid) != 'button':
            try:
                bot.answer_callback_query(call.id, 'Способ выполнения этой напоминалки уже изменён.', show_alert=True)
            except Exception:
                pass
            return True
        ok, answer = _v149_complete_reminder(rid, cid, uid, _v149_actor_label(call))
        try:
            bot.answer_callback_query(call.id, answer[:180], show_alert=not ok)
        except Exception:
            pass
        return True
    if raw.startswith('v218:demo:'):
        if not _v215_circle_business_chat(cid):
            return True
        parts = raw.split(':')
        mode = parts[2] if len(parts) > 2 else ''
        if mode not in {'finance', 'forward', 'reminders', 'tasks'}:
            return True
        if _v215_mode_enabled(cid, mode):
            try:
                bot.answer_callback_query(call.id, 'Режим уже включён. Откройте рабочее меню.', show_alert=False)
            except Exception:
                pass
            text, kb = build_contour_mode_control(cid, uid, mode)
            safe_edit(bot, call, text, reply_markup=kb)
            return True
        action = parts[3] if len(parts) > 3 else 'root'
        if action == 'root':
            try:
                bot.answer_callback_query(call.id)
            except Exception:
                pass
            _v218_show_demo(call, mode, 'root')
            return True
        if action == 'sub' and len(parts) > 4 and (parts[4] == 'report') and (mode == 'finance'):
            try:
                bot.answer_callback_query(call.id)
            except Exception:
                pass
            _v218_show_demo(call, mode, 'report')
            return True
        if action == 'desc':
            key = parts[4] if len(parts) > 4 else ''
            note = _V218_DEMO_DESCRIPTIONS.get(mode, {}).get(key, 'Эта кнопка доступна в рабочем режиме после его включения.')
            try:
                bot.answer_callback_query(call.id)
            except Exception:
                pass
            page = 'report' if mode == 'finance' and key in {'day', 'week', 'month', 'year'} else 'root'
            _v218_show_demo(call, mode, page, note)
            return True
        return True
    return False
try:
    _v177_legacy_0007_bot_journal('v218_reminder_info_demo_ready', int(OWNER_ID or 0), 'reminder_completion=button/slash/none; circle_demo=readonly; demo_callbacks=v218')
except Exception:
    pass
import re as _v219_re
V219_TASK_INLINE_INSERT_MAX = 256
V219_TASK_TEXT_MAX = 4000

def _v219_task_message_text(msg) -> str:
    return str(getattr(msg, 'text', None) or getattr(msg, 'caption', None) or '').strip()

def _v219_task_pending_for_sender(chat_id: int, user_id: int) -> bool:
    if not int(user_id or 0):
        return False
    try:
        if _v174_get_input(int(chat_id), int(user_id)):
            return True
    except Exception:
        pass
    try:
        if _v172_get_input(int(chat_id), int(user_id)):
            return True
    except Exception:
        pass
    return False

def _v219_status_target_from_message(msg, body: str):
    try:
        cid = int(msg.chat.id)
    except Exception:
        return None
    m = _v219_re.search('(?:#|№)\\s*(\\d{1,7})', str(body or ''))
    if m:
        task = _v174_task_by_number(cid, int(m.group(1)))
        if task:
            return task
    reply = getattr(msg, 'reply_to_message', None)
    if reply is not None:
        try:
            return _v174_task_for_reply(cid, int(getattr(reply, 'message_id', 0) or 0))
        except Exception:
            return None
    return None

def _v219_match_status_kind(chat_id: int, text: str) -> str:
    candidates = []
    order = {'done': 0, 'work': 1, 'deferred': 2, 'cancelled': 3}
    for kind in ('done', 'work', 'deferred', 'cancelled'):
        for kw in _v174_keywords(int(chat_id), kind):
            if _v174_has_keyword(text, kw):
                candidates.append((len(_v174_normalize(kw)), order[kind], _v174_normalize(kw), kind))
    if not candidates:
        return ''
    candidates.sort(key=lambda x: (-x[0], x[1], x[2]))
    return str(candidates[0][3])

def _v219_task_ingest_message(msg, *, is_edit: bool=False, source_kind: str='message'):
    try:
        cid = int(msg.chat.id)
        mid = int(getattr(msg, 'message_id', 0) or 0)
    except Exception:
        return None
    body = _v219_task_message_text(msg)
    if not cid or not mid or (not body) or body.startswith('/') or (not task_dispatcher_enabled(cid)):
        return None
    sender = getattr(msg, 'from_user', None)
    sender_id = int(getattr(sender, 'id', 0) or 0) if sender is not None else 0
    sender_is_bot = bool(getattr(sender, 'is_bot', False)) if sender is not None else False
    if not is_edit and _v219_task_pending_for_sender(cid, sender_id):
        return None
    if sender_is_bot:
        # R29: accept delivered third-party bot messages when the local source switch is ON.
        try:
            if not bool(globals().get('r29_input_source_enabled', lambda _c, _k: True)(cid, 'other_bots')):
                return None
        except Exception:
            return None
    if _v212_task_service_text(body):
        return None
    target = _v219_status_target_from_message(msg, body)
    if target is not None:
        status_kind = _v219_match_status_kind(cid, body)
        if status_kind:
            status = ('received' if str(target.get('type')) == 'purchase' else 'done') if status_kind == 'done' else ('search' if str(target.get('type')) == 'purchase' else 'work') if status_kind == 'work' else status_kind
            if _v174_set_status(target, status, sender, f'по ключевому слову: {status_kind}'):
                _v174_refresh_card(target)
                try:
                    bot_journal('task_status_keyword_v219', cid, f"task={target.get('number')}; status={status}; msg={mid}; source={source_kind}")
                except Exception:
                    pass
            return target
    return task_reconcile_source_message(cid, mid, body, original_date=getattr(msg, 'date', None), sender_id=sender_id, sender_name=_v172_user_name(sender) if sender is not None else '', sender_is_bot=sender_is_bot, trusted_forwarding_copy=False, is_edit=bool(is_edit), content_type=str(getattr(msg, 'content_type', '') or 'text'))
_V219_PREV_AUTO_PROCESS = _canon_v174_auto_process__001

def _v219_task_auto_process(msg) -> None:
    try:
        if bool(getattr(msg, '_v219_task_ingested', False)):
            return
        return _v219_task_ingest_message(msg, is_edit=False, source_kind='handler')
    except Exception as exc:
        try:
            log_error(f'v219 task auto process: {exc}')
        except Exception:
            pass
        return None
_V219_PREV_PROCESS_NEW_UPDATES = getattr(bot, 'process_new_updates', None)

def _v219_process_new_updates(updates):
    for update in list(updates or []):
        for attr, edited in (('message', False), ('edited_message', True), ('channel_post', False), ('edited_channel_post', True)):
            msg = getattr(update, attr, None)
            if msg is None:
                continue
            try:
                _v219_task_ingest_message(msg, is_edit=edited, source_kind=attr)
                try:
                    setattr(msg, '_v219_task_ingested', True)
                except Exception:
                    pass
            except Exception as exc:
                try:
                    log_error(f'v219 task ingest {attr}: {exc}')
                except Exception:
                    pass
    if callable(_V219_PREV_PROCESS_NEW_UPDATES):
        return _V219_PREV_PROCESS_NEW_UPDATES(updates)
    return None
if callable(_V219_PREV_PROCESS_NEW_UPDATES):
    bot.process_new_updates = _v219_process_new_updates

def _v219_task_text_prompt_keyboard(chat_id: int, sid: str, task: dict, message_id: int=0):
    kb = _v214_task_prompt_markup(int(chat_id), 'task', sid, 'text', '', str(task.get('uid') or ''), False)
    current = str(task.get('description') or task.get('title') or '')
    try:
        rows = list(getattr(kb, 'keyboard', None) or [])
    except Exception:
        rows = []
    insert_row = []
    if len(current) <= V219_TASK_INLINE_INSERT_MAX:
        try:
            insert_row = [make_copy_or_inline_button('✏️ Вставить текущий текст', current, viewer_chat_id=int(chat_id))]
        except Exception:
            insert_row = [IB('📄 Показать текущий текст', callback_data=f"v219:task:showtext:{str(task.get('uid') or '')}")]
    else:
        insert_row = [IB('📄 Показать полный текст', callback_data=f"v219:task:showtext:{str(task.get('uid') or '')}")]
    try:
        if insert_row:
            kb.keyboard = [insert_row] + rows
    except Exception:
        if insert_row:
            try:
                kb.row(*insert_row)
            except Exception:
                pass
    return kb
_V219_PREV_PROMPT_INPUT = _v214_v174_prompt_input

def _v219_task_prompt_input(chat_id: int, user_id: int, action: str, kind: str='', task_uid: str='', message_id: int=0):
    if str(action) != 'text':
        return _V219_PREV_PROMPT_INPUT(chat_id, user_id, action, kind, task_uid, message_id)
    cid, uid = (int(chat_id), int(user_id))
    task = _v172_task_for_uid(str(task_uid or '').upper())
    if not isinstance(task, dict) or int(task.get('chat_id', 0) or 0) != cid:
        try:
            send_and_auto_delete(cid, '❌ Задача не найдена.', 8)
        except Exception:
            pass
        return None
    cancel_task_input(cid, uid, 'new_input')
    sid = _v213_input_sid()
    delay = _v213_input_timeout_seconds()
    current = str(task.get('description') or task.get('title') or '')
    short_view = current if len(current) <= 1500 else current[:1500] + '\n…\nПолный текст показан отдельным helper-сообщением.'
    prompt = f"✏️ ИЗМЕНИТЬ ТЕКСТ ЗАДАЧИ #{task.get('number')}\n\nТекущий текст:\n{short_view}\n\nОтредактируйте текст и отправьте его одним сообщением.\n⏳ Автоотмена бездействия: {_format_duration_short(delay)}."
    pid = 0
    try:
        sent = bot.send_message(cid, _v213_prompt_text(prompt), reply_markup=_v219_task_text_prompt_keyboard(cid, sid, task, message_id))
        pid = int(getattr(sent, 'message_id', 0) or 0)
    except Exception:
        pass
    if len(current) > V219_TASK_INLINE_INSERT_MAX:
        try:
            send_and_auto_delete(cid, current, max(120, int(delay)))
        except Exception:
            pass
    with _V174_INPUT_LOCK:
        _V174_INPUT_WAIT[cid, uid] = {'action': 'text', 'kind': str(kind), 'task_uid': str(task_uid or '').upper(), 'message_id': int(message_id or 0), 'prompt_id': pid, 'created': _v213_time.time(), 'last_activity': _v213_time.time(), 'session_id': sid, 'generation': 1}
    key = _v213_task_input_key(cid, uid, False)
    try:
        DELAYED_SCHEDULER.cancel(key)
    except Exception:
        pass
    DELAYED_SCHEDULER.schedule(key, delay, _v214_task_input_timeout, cid, uid, sid, False)
    return sid
_V219_PREV_HANDLE_OWN_INPUT = _v214_v174_handle_own_input

def _v219_task_handle_own_input(msg) -> bool:
    try:
        if str(getattr(msg, 'content_type', '') or '') != 'text':
            return _V219_PREV_HANDLE_OWN_INPUT(msg)
        cid = int(msg.chat.id)
        uid = int(getattr(getattr(msg, 'from_user', None), 'id', 0) or 0)
        row = _v214_task_pending_row(cid, uid, False)
        if not row or str(row.get('action') or '') != 'text':
            return _V219_PREV_HANDLE_OWN_INPUT(msg)
        raw = str(getattr(msg, 'text', '') or '').strip()
        if raw.casefold() in {'отмена', 'cancel', 'стоп'}:
            cancel_task_input(cid, uid, 'text_cancel')
            _v172_delete_quiet(cid, int(getattr(msg, 'message_id', 0) or 0))
            try:
                send_and_auto_delete(cid, '❎ Действие отменено.', 5)
            except Exception:
                pass
            return True
        clean = sanitize_telegram_inserted_text(raw)
        if len(clean) > V219_TASK_TEXT_MAX:
            try:
                send_and_auto_delete(cid, f'❌ Текст не сохранён: максимум {V219_TASK_TEXT_MAX} символов. Ничего не обрезано.', 12)
            except Exception:
                pass
            task_uid = str(row.get('task_uid') or '')
            cancel_task_input(cid, uid, 'too_long_retry')
            _v174_prompt_input(cid, uid, 'text', task_uid=task_uid, message_id=int(row.get('message_id', 0) or 0))
            return True
        task = _v172_task_for_uid(str(row.get('task_uid') or ''))
        if not isinstance(task, dict) or int(task.get('chat_id', 0) or 0) != cid:
            cancel_task_input(cid, uid, 'target_missing')
            return True
        if not (_v172_is_manager(uid, cid) or uid == int(task.get('creator_user_id', 0) or 0)):
            cancel_task_input(cid, uid, 'forbidden')
            try:
                send_and_auto_delete(cid, '⛔ Изменять текст может автор или управляющий.', 10)
            except Exception:
                pass
            return True
        cancel_task_input(cid, uid, 'submitted')
        user = getattr(msg, 'from_user', None)
        task['description'] = clean
        task['title'] = _v172_title(clean)
        _v172_touch(task, user, 'text_changed', clean[:180])
        _v172_delete_quiet(cid, int(getattr(msg, 'message_id', 0) or 0))
        _v174_refresh_card(task)
        mid = int(row.get('message_id', 0) or 0)
        if mid:
            try:
                bot.edit_message_text(_v174_compact_text(task), chat_id=cid, message_id=mid, reply_markup=_v174_compact_kb(task, cid, uid))
            except Exception:
                pass
        return True
    except Exception as exc:
        try:
            log_error(f'v219 task text input: {exc}')
        except Exception:
            pass
        return True
_V219_PREV_TASK_CALLBACK_FINAL = _v213_task_dispatcher_callback_final

def _v219_task_dispatcher_callback_final(call) -> bool:
    raw = str(getattr(call, 'data', '') or '')
    try:
        resolver = globals().get('resolve_short_callback')
        if callable(resolver):
            raw = str(resolver(raw) or raw)
    except Exception:
        pass
    if raw.startswith('v219:task:showtext:'):
        try:
            cid = int(call.message.chat.id)
            actor = int(getattr(getattr(call, 'from_user', None), 'id', 0) or 0)
        except Exception:
            return True
        uid = raw.split(':', 3)[3].upper() if len(raw.split(':', 3)) > 3 else ''
        task = _v172_task_for_uid(uid)
        if not isinstance(task, dict) or int(task.get('chat_id', 0) or 0) != cid:
            try:
                bot.answer_callback_query(call.id, 'Задача не найдена.', show_alert=True)
            except Exception:
                pass
            return True
        pending = _v214_task_pending_row(cid, actor, False)
        if not pending or str(pending.get('action') or '') != 'text' or str(pending.get('task_uid') or '').upper() != uid:
            try:
                bot.answer_callback_query(call.id, 'Режим редактирования уже завершён.', show_alert=True)
            except Exception:
                pass
            return True
        try:
            bot.answer_callback_query(call.id, 'Полный текст отправлен ниже')
        except Exception:
            pass
        try:
            send_and_auto_delete(cid, str(task.get('description') or task.get('title') or ''), max(120, int(_v213_input_timeout_seconds())))
        except Exception:
            pass
        return True
    return bool(_V219_PREV_TASK_CALLBACK_FINAL(call))
try:
    WINDOW_MARKER_CONSTANTS.setdefault('v219:task:showtext:*', 'Ф252')
    _v177_legacy_0007_bot_journal('v219_task_reconcile_ready', int(OWNER_ID or 0), 'update_ingest=message/edit/channel/caption; text_insert=exact<=256; long_fallback=helper')
except Exception:
    pass
V220_CONTOUR_MENU_ACCESS_KEY = 'contour_menu_access_v220'
V220_CONTOUR_MENU_UNAVAILABLE = 'Меню режимов для этого чата сейчас недоступно.'

def _v220_contour_menu_access_root() -> dict:
    gs = data.setdefault('_global_settings', {})
    row = gs.setdefault(V220_CONTOUR_MENU_ACCESS_KEY, {})
    if not isinstance(row, dict):
        row = {}
        gs[V220_CONTOUR_MENU_ACCESS_KEY] = row
    row.setdefault('1', True)
    row.setdefault('2', True)
    return row

def contour_menu_access_enabled_v220(chat_id: int | None=None, level: int | None=None) -> bool:
    try:
        lvl = int(level) if level is not None else int(circle_level_for_chat(int(chat_id)))
    except Exception:
        return True
    if lvl not in {1, 2}:
        return True
    return bool(_v220_contour_menu_access_root().get(str(lvl), True))

def set_contour_menu_access_v220(level: int, enabled: bool) -> bool:
    lvl = 2 if int(level) == 2 else 1
    row = _v220_contour_menu_access_root()
    row[str(lvl)] = bool(enabled)
    try:
        save_data(data, root_only=True)
    except Exception:
        pass
    try:
        schedule_delta_backup(int(OWNER_ID or 0), delay=0.12, reason=f'v220_contour_menu_access_{lvl}')
    except Exception:
        pass
    return bool(row[str(lvl)])

def _v220_remove_contour_menu_button(kb, chat_id: int):
    try:
        cid = int(chat_id)
        if not _v215_circle_business_chat(cid) or contour_menu_access_enabled_v220(cid):
            return kb
        rows = []
        for row in _v217_rows(kb):
            kept = [b for b in row or [] if _v217_btn_cb(b) != 'v217:contour:menu']
            if kept:
                rows.append(kept)
        return _v217_set_rows(kb, rows)
    except Exception:
        return kb
_V220_PREV_MAIN_KB = _v217_build_main_keyboard

def _v220_build_main_keyboard(day_key: str, chat_id=None):
    kb = _V220_PREV_MAIN_KB(day_key, chat_id)
    try:
        cid = int(chat_id if chat_id is not None else current_state_chat_id() or 0)
    except Exception:
        cid = 0
    return _v220_remove_contour_menu_button(kb, cid)
_V220_PREV_TASK_MENU = _v217_task_home_kb

def _v220_task_menu_text_kb(chat_id: int, user_id: int=0):
    text, kb = _V220_PREV_TASK_MENU(int(chat_id), int(user_id or 0))
    return (text, _v220_remove_contour_menu_button(kb, int(chat_id)))
_V220_PREV_FORWARD_MENU = _canon_build_forward_menu_keyboard_for_current_mode__002

def _v220_forward_menu_keyboard(day_key: str | None=None, A: int | None=None, B: int | None=None):
    kb = _V220_PREV_FORWARD_MENU(day_key, A, B)
    try:
        cid = int(current_state_chat_id() or 0)
    except Exception:
        cid = 0
    return _v220_remove_contour_menu_button(kb, cid)
_V220_PREV_FORWARD_SCOPE_KB = _canon_build_v217_forward_scope_keyboard__001

def _v220_forward_scope_keyboard(chat_id: int, user_id: int):
    return _v220_remove_contour_menu_button(_V220_PREV_FORWARD_SCOPE_KB(int(chat_id), int(user_id or 0)), int(chat_id))
_V220_PREV_REMINDER_LIST_KB = _canon_build_reminder_list_keyboard__002

def _v220_reminder_list_keyboard(day_key: str | None=None, page: int=0):
    kb = _V220_PREV_REMINDER_LIST_KB(day_key, page)
    try:
        cid = int(current_state_chat_id() or 0)
    except Exception:
        cid = 0
    return _v220_remove_contour_menu_button(kb, cid)
_V220_PREV_CHAT_REMINDER_KB = _canon_build_v217_chat_reminders_keyboard__001

def _v220_chat_reminder_keyboard(chat_id: int, user_id: int):
    return _v220_remove_contour_menu_button(_V220_PREV_CHAT_REMINDER_KB(int(chat_id), int(user_id or 0)), int(chat_id))
_V220_PREV_NEUTRAL_HOME = _canon_v213_show_neutral_home__001

def _v220_show_neutral_home(chat_id: int, current_message_id: int=0) -> int:
    cid = int(chat_id)
    mid = int(current_message_id or 0)
    if not _v215_circle_business_chat(cid) or not contour_menu_access_enabled_v220(cid):
        return _V220_PREV_NEUTRAL_HOME(cid, mid)
    text = window_mark('ℹ️ В этом контуре сейчас не включено ни одного видимого рабочего режима.', V213_NEUTRAL_HOME_MARKER)
    kb = types.InlineKeyboardMarkup(row_width=1)
    kb.row(IB('☰ Меню', callback_data='v217:contour:menu'))
    kb.row(IB('❌ Закрыть', callback_data='aux_close'))
    if mid:
        try:
            result = fast_ui_edit_message_text(cid, mid, text, reply_markup=kb, purpose='contour_home_neutral_v220')
            if result in {'ok', 'scheduled'}:
                _v213_clear_finance_active_pointer(cid)
                return mid
        except Exception:
            pass
    try:
        sent = bot.send_message(cid, text, reply_markup=kb)
        _v213_clear_finance_active_pointer(cid)
        return int(getattr(sent, 'message_id', 0) or 0)
    except Exception:
        return 0
_V220_PREV_SHOW_CONTOUR_START = _canon_show_contour_start_modes__001

def _v220_show_contour_start_modes(chat_id: int, user_id: int=0, message_id: int=0) -> int:
    cid = int(chat_id)
    uid = int(user_id or 0)
    mid = int(message_id or 0)
    if _v215_circle_business_chat(cid) and uid != int(OWNER_ID or 0) and (not contour_menu_access_enabled_v220(cid)):
        try:
            send_and_auto_delete(cid, V220_CONTOUR_MENU_UNAVAILABLE, 10)
        except Exception:
            pass
        try:
            open_resolved_contour_home(cid, uid, mid, today_key())
        except Exception:
            pass
        try:
            bot_journal('contour_menu_access_block_v220', cid, f'source=renderer; user={uid}')
        except Exception:
            pass
        return mid
    return int(_V220_PREV_SHOW_CONTOUR_START(cid, uid, mid) or 0)
_V220_PREV_CONTOUR_GUARD = _v214_contour_callback_guard

def _v220_contour_callback_guard(call, resolved: str) -> bool:
    raw = str(resolved or '')
    try:
        cid = int(call.message.chat.id)
        uid = int(getattr(getattr(call, 'from_user', None), 'id', 0) or 0)
        mid = int(getattr(call.message, 'message_id', 0) or 0)
    except Exception:
        return bool(_V220_PREV_CONTOUR_GUARD(call, raw))
    menu_surface = raw == 'v217:contour:menu' or raw.startswith('v215:mode:') or raw.startswith('v218:demo:')
    if _v215_circle_business_chat(cid) and uid != int(OWNER_ID or 0) and (not contour_menu_access_enabled_v220(cid)) and menu_surface:
        try:
            bot.answer_callback_query(call.id, V220_CONTOUR_MENU_UNAVAILABLE, show_alert=False)
        except Exception:
            pass
        try:
            open_resolved_contour_home(cid, uid, mid, today_key())
        except Exception:
            pass
        try:
            bot_journal('contour_menu_access_block_v220', cid, f'source=callback; action={raw}; user={uid}')
        except Exception:
            pass
        return True
    return bool(_V220_PREV_CONTOUR_GUARD(call, raw))

def _v220_registered_rows_for_circle(level: int) -> list[dict]:
    allowed = set(_v174_circle_ids(2 if int(level) == 2 else 1))
    try:
        reg_fn = globals().get('_open_window_registry')
        rows = list((reg_fn() if callable(reg_fn) else data.get('open_window_registry') or {}).values())
    except Exception:
        rows = []
    out = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        try:
            if int(row.get('chat_id') or 0) in allowed and int(row.get('message_id') or 0):
                out.append(dict(row))
        except Exception:
            pass
    return out

def refresh_circle_menu_access_v220(level: int) -> int:
    """Immediately refresh known main/home windows; stale menu surfaces are converted to home."""
    changed = 0
    for row in _v220_registered_rows_for_circle(level):
        try:
            cid = int(row.get('chat_id') or 0)
            mid = int(row.get('message_id') or 0)
            wtype = str(row.get('window_type') or '')
            code = str(row.get('code') or '')
            if wtype == 'contour_modes' and (not contour_menu_access_enabled_v220(cid)):
                open_resolved_contour_home(cid, 0, mid, str(row.get('day_key') or today_key()))
                changed += 1
                continue
            if wtype == 'main_day':
                day = str(row.get('day_key') or get_chat_store(cid).get('current_view_day') or today_key())
                text, _ = render_day_window(cid, day)
                fast_ui_edit_message_text(cid, mid, text, reply_markup=build_main_keyboard(day, cid), purpose='contour_menu_access_refresh_v220')
                changed += 1
                continue
            if wtype == 'tasks' or code == 'Ф248':
                _v213_show_task_home(cid, 0, mid)
                changed += 1
                continue
            if code == V213_NEUTRAL_HOME_MARKER:
                _v213_show_neutral_home(cid, mid)
                changed += 1
        except Exception:
            continue
    try:
        bot_journal('contour_menu_access_refresh_v220', int(OWNER_ID or 0), f'level={int(level)}; refreshed={changed}')
    except Exception:
        pass
    return changed

def refresh_circle_annotation_windows_v220() -> int:
    """Re-render known live primary windows so /tz and /iz-mr switches apply without restart."""
    changed = 0
    seen = set()
    for level in (1, 2):
        for row in _v220_registered_rows_for_circle(level):
            try:
                cid = int(row.get('chat_id') or 0)
                mid = int(row.get('message_id') or 0)
                key = (cid, mid)
                if key in seen:
                    continue
                seen.add(key)
                wtype = str(row.get('window_type') or '')
                code = str(row.get('code') or '')
                if wtype == 'main_day':
                    day = str(row.get('day_key') or get_chat_store(cid).get('current_view_day') or today_key())
                    text, _ = render_day_window(cid, day)
                    fast_ui_edit_message_text(cid, mid, text, reply_markup=build_main_keyboard(day, cid), purpose='annotation_visibility_refresh_v220')
                    changed += 1
                elif wtype == 'tasks' or code == 'Ф248':
                    _v213_show_task_home(cid, 0, mid)
                    changed += 1
                elif wtype == 'contour_modes':
                    show_contour_start_modes(cid, int(OWNER_ID or 0), mid)
                    changed += 1
                elif code == V213_NEUTRAL_HOME_MARKER:
                    _v213_show_neutral_home(cid, mid)
                    changed += 1
            except Exception:
                continue
    try:
        bot_journal('annotation_visibility_refresh_v220', int(OWNER_ID or 0), f'refreshed={changed}')
    except Exception:
        pass
    return changed

def _v220_reconcile_completed_reminder_groups(reminder_id: int, chat_ids: list[int]) -> None:
    for cid in sorted(set((int(x) for x in chat_ids or [] if int(x)))):
        try:
            _v149_reminder_batch_job(int(cid))
        except Exception as exc:
            try:
                log_error(f'v220 reminder group reconcile {int(reminder_id)} chat {cid}: {exc}')
            except Exception:
                pass
_V220_PREV_COMPLETE_REMINDER = _canon_v149_complete_reminder__001

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

def _v220_reminder_complete_keyboard(reminder_id: int, cfg: dict, chat_id: int):
    if _v218_completion_mode(cfg, chat_id) != 'button':
        return None
    kb = types.InlineKeyboardMarkup(row_width=1)
    kb.row(IB('✅ Выполнено', callback_data=f'v149:rem:done:{int(reminder_id)}:{int(chat_id)}'))
    return kb

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
try:
    WINDOW_MARKER_CONSTANTS.update({'v174:td:admin:*': 'Ф247', 'v174:td:toggle:*': 'Ф247', 'v174:td:list:*': 'Ф248', 'keepalive_peer': 'Ф92', 'keepalive_peer_toggle': 'Ф92', 'keepalive_peer_interval': 'Ф92', 'keepalive_peer_url': 'Ф92', 'keepalive_peer_url_cancel': 'Ф92', 'keepalive_peer_clear': 'Ф92', 'keepalive_peer_now': 'Ф92'})
except Exception:
    pass
try:
    _v177_legacy_0007_bot_journal('v220_runtime_features_ready', int(OWNER_ID or 0), 'reminder_global_completion=all_recipients; contour_menu_access=per_circle; signal_markers=declared')
except Exception:
    pass
import copy as _v221_copy
import re as _v221_re
import threading as _v221_threading
import time as _v221_time
V221_MENU_CLOSED_MARKER = 'Ф261'
V221_OWNER_MESSAGE_INPUT_MARKER = 'Ф262'
V221_OWNER_REQUESTS_MARKER = 'Ф263'
V221_OWNER_REQUEST_CARD_MARKER = 'Ф264'
V221_OWNER_REQUESTS_KEY = 'owner_user_requests_v221'
V221_OWNER_REQUEST_PAGE_SIZE = 15
V221_MENU_CLOSED_TEXT = 'Меню этого чата сейчас закрыто владельцем.\nЕсли вам нужен доступ или помощь — напишите владельцу.'
try:
    WINDOW_MARKER_CONSTANTS.update({'v221:owner_msg:*': V221_OWNER_MESSAGE_INPUT_MARKER, 'v221:req:*': V221_OWNER_REQUESTS_MARKER})
except Exception:
    pass

def contour_menu_access_allowed(chat_id: int, user_id: int=0) -> bool:
    """Single canonical selector-access decision for circle 1/2.

    The persisted switch is chat/circle scoped.  PRIMARY OWNER gets an explicit
    administrative bypass, but that bypass never mutates the switch and is never
    used to render shared work-window buttons for ordinary users.
    """
    try:
        cid = int(chat_id)
        uid = int(user_id or 0)
    except Exception:
        return True
    if not _v215_circle_business_chat(cid):
        return True
    if uid == int(OWNER_ID or 0):
        return True
    return bool(contour_menu_access_enabled_v220(cid))

def _v221_button_cb(button) -> str:
    try:
        if isinstance(button, dict):
            return str(button.get('callback_data') or '')
        return str(getattr(button, 'callback_data', '') or '')
    except Exception:
        return ''

def _v221_markup_rows(kb):
    try:
        return list(getattr(kb, 'keyboard', None) or getattr(kb, 'inline_keyboard', None) or [])
    except Exception:
        return []

def _v221_set_markup_rows(kb, rows):
    try:
        kb.keyboard = rows
        return kb
    except Exception:
        pass
    try:
        kb.inline_keyboard = rows
    except Exception:
        pass
    return kb

def v221_finalize_contour_markup(reply_markup, chat_id: int | None):
    """FINAL policy filter, intended to run after renderer/nav/Constructor/profile layers."""
    if reply_markup is None:
        return None
    try:
        cid = int(chat_id or 0)
    except Exception:
        return reply_markup
    if not cid:
        return reply_markup
    target_fn = globals().get('_v229_annotation_target_chat')
    try:
        contour_target = bool(target_fn(cid)) if callable(target_fn) else bool(_v215_circle_business_chat(cid))
    except Exception:
        contour_target = bool(_v215_circle_business_chat(cid))
    try:
        kb = _v221_copy.deepcopy(reply_markup)
    except Exception:
        kb = reply_markup
    show_tz = True
    show_marker = True
    try:
        show_tz = bool(circle_annotation_button_enabled_v219('tz', cid))
    except Exception:
        pass
    try:
        show_marker = bool(circle_annotation_button_enabled_v219('iz_mr', cid))
    except Exception:
        pass
    menu_on = bool(contour_menu_access_enabled_v220(cid)) if contour_target else True
    cleaned = []
    for row in _v221_markup_rows(kb):
        keep = []
        for button in list(row or []):
            cb = _v221_button_cb(button)
            if cb == 'v160:tz_capture' and (not show_tz):
                continue
            if cb == 'v160:marker_capture' and (not show_marker):
                continue
            if contour_target and cb == 'v217:contour:menu' and (not menu_on):
                continue
            keep.append(button)
        if keep:
            cleaned.append(keep)
    kb = _v221_set_markup_rows(kb, cleaned)
    try:
        directive_fn = globals().get('directive_chat_enabled_v223')
        mode_from_cb = globals().get('_v223_directive_mode_from_callback')
        mutation_cb = globals().get('_v223_is_mode_mutation_callback')
        if contour_target and callable(directive_fn) and directive_fn(cid):
            final_rows = []
            for row in _v221_markup_rows(kb):
                keep = []
                for button in list(row or []):
                    cb = _v221_button_cb(button)
                    if callable(mutation_cb) and mutation_cb(cb):
                        continue
                    mode = mode_from_cb(cb) if callable(mode_from_cb) else ''
                    if mode and (not _v215_mode_enabled(cid, mode)):
                        continue
                    try:
                        enabled_count = sum((1 for m in V223_DIRECTIVE_MODES if _v215_mode_enabled(cid, m)))
                    except Exception:
                        enabled_count = 0
                    if enabled_count <= 1 and (cb == 'v217:contour:menu' or cb in {'v215:mode:back', 'v215:mode:guide'}):
                        continue
                    keep.append(button)
                if keep:
                    final_rows.append(keep)
            kb = _v221_set_markup_rows(kb, final_rows)
    except Exception:
        pass
    return kb
_V221_LIVE_MARKUP_LOCK = _v221_threading.RLock()
_V221_LIVE_MARKUP = {}

def _v221_markup_fingerprint(kb) -> tuple:
    out = []
    for row in _v221_markup_rows(kb):
        rr = []
        for b in row or []:
            try:
                label = str(b.get('text') if isinstance(b, dict) else getattr(b, 'text', ''))
            except Exception:
                label = ''
            rr.append((label, _v221_button_cb(b)))
        out.append(tuple(rr))
    return tuple(out)

def v227_render_effective_contour_markup(source_markup, text: str, chat_id: int):
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

def v221_record_live_markup(chat_id: int, message_id: int, reply_markup, text: str='', source_markup=None) -> None:
    try:
        cid = int(chat_id)
        mid = int(message_id)
    except Exception:
        return
    if not cid or not mid or reply_markup is None:
        return
    try:
        snap = _v221_copy.deepcopy(reply_markup)
    except Exception:
        snap = reply_markup
    with _V221_LIVE_MARKUP_LOCK:
        previous = dict(_V221_LIVE_MARKUP.get((cid, mid)) or {})
        rendered_text = str(text or '')[:4000] or str(previous.get('text') or '')[:4000]
        canonical = source_markup
        if canonical is None:
            canonical = previous.get('source_markup')
        if canonical is None:
            canonical = reply_markup
        try:
            canonical_snap = _v221_copy.deepcopy(canonical)
        except Exception:
            canonical_snap = canonical
        _V221_LIVE_MARKUP[cid, mid] = {'markup': snap, 'source_markup': canonical_snap, 'text': rendered_text, 'at': _v221_time.time()}
        if len(_V221_LIVE_MARKUP) > 1800:
            oldest = sorted(_V221_LIVE_MARKUP.items(), key=lambda x: float((x[1] or {}).get('at') or 0.0))[:300]
            for key, _row in oldest:
                _V221_LIVE_MARKUP.pop(key, None)

def v221_forget_live_markup(chat_id: int, message_id: int) -> None:
    try:
        with _V221_LIVE_MARKUP_LOCK:
            _V221_LIVE_MARKUP.pop((int(chat_id), int(message_id)), None)
    except Exception:
        pass

def v221_refresh_live_contour_policy(level: int | None=None) -> int:
    """Immediately re-apply final UI policy to every live markup observed by v221.

    The persistent window registry is still refreshed through v220 for known canonical
    windows; this live snapshot closes the gap for auxiliary/Constructor/profile windows.
    Stale pre-v221 Telegram buttons remain server-side hard-gated even if Telegram cannot
    be physically re-rendered without a current markup snapshot.
    """
    changed = 0
    with _V221_LIVE_MARKUP_LOCK:
        rows = [(k, dict(v or {})) for k, v in _V221_LIVE_MARKUP.items()]
    for (cid, mid), row in rows:
        try:
            if not _v215_circle_business_chat(int(cid)):
                continue
            if level in {1, 2} and int(circle_level_for_chat(int(cid))) != int(level):
                continue
            before = row.get('markup')
            source = row.get('source_markup') if row.get('source_markup') is not None else before
            after = v227_render_effective_contour_markup(source, str(row.get('text') or ''), int(cid))
            if _v221_markup_fingerprint(before) == _v221_markup_fingerprint(after):
                continue
            bot.edit_message_reply_markup(chat_id=int(cid), message_id=int(mid), reply_markup=after)
            v221_record_live_markup(int(cid), int(mid), after, str(row.get('text') or ''), source_markup=source)
            changed += 1
        except Exception:
            continue
    try:
        if level in {1, 2}:
            refresh_circle_menu_access_v220(int(level))
        else:
            refresh_circle_menu_access_v220(1)
            refresh_circle_menu_access_v220(2)
    except Exception:
        pass
    try:
        refresh_circle_annotation_windows_v220()
    except Exception:
        pass
    try:
        bot_journal('contour_final_policy_refresh_v221', int(OWNER_ID or 0), f'level={level or 0}; live_changed={changed}')
    except Exception:
        pass
    return changed

def _v221_menu_closed_keyboard():
    kb = types.InlineKeyboardMarkup(row_width=1)
    kb.row(IB('✉️ Написать владельцу', callback_data='v221:owner_msg:start'))
    kb.row(IB('❌ Закрыть', callback_data='aux_close'))
    return kb

def show_contour_menu_closed_v221(chat_id: int, user_id: int=0, message_id: int=0) -> int:
    cid = int(chat_id)
    mid = int(message_id or 0)
    kb = _v221_menu_closed_keyboard()
    if mid:
        try:
            result = fast_ui_edit_message_text(cid, mid, V221_MENU_CLOSED_TEXT, reply_markup=kb, purpose='contour_menu_closed_v221')
            if result in {'ok', 'scheduled'}:
                try:
                    register_open_window(cid, mid, 'contour_menu_closed', code=V221_MENU_CLOSED_MARKER, params={'parallel_allowed': True})
                except Exception:
                    pass
                return mid
        except Exception:
            pass
    try:
        sent = bot.send_message(cid, V221_MENU_CLOSED_TEXT, reply_markup=kb)
        mid = int(getattr(sent, 'message_id', 0) or 0)
        if mid:
            try:
                register_open_window(cid, mid, 'contour_menu_closed', code=V221_MENU_CLOSED_MARKER, params={'parallel_allowed': True})
            except Exception:
                pass
        return mid
    except Exception:
        return 0
_V221_PREV_SHOW_CONTOUR_START = _v220_show_contour_start_modes

def _v221_show_contour_start_modes(chat_id: int, user_id: int=0, message_id: int=0) -> int:
    cid = int(chat_id)
    uid = int(user_id or 0)
    mid = int(message_id or 0)
    if _v215_circle_business_chat(cid) and (not contour_menu_access_allowed(cid, uid)):
        try:
            bot_journal('contour_menu_access_block_v221', cid, f'source=renderer; user={uid}; contact_owner=1')
        except Exception:
            pass
        return int(show_contour_menu_closed_v221(cid, uid, mid) or mid)
    return int(_V221_PREV_SHOW_CONTOUR_START(cid, uid, mid) or 0)
_V221_PREV_FORCE_START = _v216_force_start_contour_modes

def _v221_force_start(msg) -> bool:
    try:
        cid = int(msg.chat.id)
        uid = int(getattr(getattr(msg, 'from_user', None), 'id', 0) or 0)
    except Exception:
        return bool(_V221_PREV_FORCE_START(msg)) if callable(_V221_PREV_FORCE_START) else True
    try:
        payload_fn = globals().get('_v162_start_payload_present')
        if callable(payload_fn) and payload_fn(msg):
            return bool(_V221_PREV_FORCE_START(msg)) if callable(_V221_PREV_FORCE_START) else True
    except Exception:
        pass
    if _v215_circle_business_chat(cid) and (not contour_menu_access_allowed(cid, uid)):
        try:
            update_chat_info_from_message(msg)
        except Exception:
            pass
        try:
            schedule_command_delete(msg)
        except Exception:
            pass
        try:
            set_total_secret_mode(cid, False)
        except Exception:
            pass
        try:
            stop_dozvon_for_target(cid)
        except Exception:
            pass
        show_contour_menu_closed_v221(cid, uid, 0)
        try:
            bot_journal('start_menu_closed_v221', cid, f'user={uid}; finance_fallback=0')
        except Exception:
            pass
        return True
    return bool(_V221_PREV_FORCE_START(msg)) if callable(_V221_PREV_FORCE_START) else True
_V221_PREV_CONTOUR_GUARD = _v220_contour_callback_guard

def _v221_contour_callback_guard(call, resolved: str) -> bool:
    raw = str(resolved or '')
    try:
        cid = int(call.message.chat.id)
        uid = int(getattr(getattr(call, 'from_user', None), 'id', 0) or 0)
        mid = int(getattr(call.message, 'message_id', 0) or 0)
    except Exception:
        return bool(_V221_PREV_CONTOUR_GUARD(call, raw))
    if _v215_circle_business_chat(cid):
        if raw == 'v160:tz_capture' and (not circle_annotation_button_enabled_v219('tz', cid)):
            try:
                bot.answer_callback_query(call.id, 'Кнопка /tz скрыта владельцем.', show_alert=True)
            except Exception:
                pass
            return True
        if raw == 'v160:marker_capture' and (not circle_annotation_button_enabled_v219('iz_mr', cid)):
            try:
                bot.answer_callback_query(call.id, 'Кнопка /iz-mr скрыта владельцем.', show_alert=True)
            except Exception:
                pass
            return True
        menu_surface = raw == 'v217:contour:menu' or raw.startswith('v215:mode:') or raw.startswith('v218:demo:')
        if menu_surface and (not contour_menu_access_allowed(cid, uid)):
            try:
                bot.answer_callback_query(call.id, 'Меню этого чата закрыто владельцем.', show_alert=False)
            except Exception:
                pass
            show_contour_menu_closed_v221(cid, uid, mid)
            try:
                bot_journal('contour_menu_access_block_v221', cid, f'source=callback; action={raw}; user={uid}; contact_owner=1')
            except Exception:
                pass
            return True
    return bool(_V221_PREV_CONTOUR_GUARD(call, raw))

def _v221_owner_requests_root() -> dict:
    gs = data.setdefault('_global_settings', {})
    root = gs.setdefault(V221_OWNER_REQUESTS_KEY, {'next_id': 1, 'items': {}})
    if not isinstance(root, dict):
        root = {'next_id': 1, 'items': {}}
        gs[V221_OWNER_REQUESTS_KEY] = root
    if not isinstance(root.get('items'), dict):
        root['items'] = {}
    try:
        root['next_id'] = max(1, int(root.get('next_id') or 1))
    except Exception:
        root['next_id'] = 1
    return root

def _v221_owner_requests_persist(reason: str) -> None:
    try:
        save_data(data, root_only=True)
    except Exception:
        pass
    try:
        schedule_delta_backup(int(OWNER_ID or 0), delay=0.12, reason=f"v221_owner_requests_{str(reason or 'update')[:60]}")
    except Exception:
        pass

def v221_owner_requests_new_count() -> int:
    try:
        return sum((1 for row in (_v221_owner_requests_root().get('items') or {}).values() if isinstance(row, dict) and str(row.get('status') or 'new') == 'new'))
    except Exception:
        return 0

def _v221_user_label(user) -> tuple[str, str]:
    username = str(getattr(user, 'username', '') or '')
    name = ' '.join((x for x in [str(getattr(user, 'first_name', '') or ''), str(getattr(user, 'last_name', '') or '')] if x)).strip()
    return (username[:120], name[:180])

def _v221_create_owner_request(msg, text: str) -> int:
    root = _v221_owner_requests_root()
    items = root.setdefault('items', {})
    rid = int(root.get('next_id') or 1)
    while str(rid) in items:
        rid += 1
    try:
        cid = int(msg.chat.id)
    except Exception:
        cid = 0
    user = getattr(msg, 'from_user', None)
    try:
        uid = int(getattr(user, 'id', 0) or 0)
    except Exception:
        uid = 0
    username, name = _v221_user_label(user)
    try:
        title = str(get_chat_display_name(cid) or getattr(msg.chat, 'title', '') or cid)
    except Exception:
        title = str(cid)
    row = {'message_request_id': rid, 'source_chat_id': cid, 'source_chat_title': title[:220], 'source_user_id': uid, 'username': username, 'name': name, 'text': str(text or ''), 'created_at': now_local().isoformat(timespec='seconds'), 'status': 'new', 'deferred_at': '', 'completed_at': ''}
    items[str(rid)] = row
    root['next_id'] = rid + 1
    _v221_owner_requests_persist('new')
    try:
        bot_journal('owner_user_request_created_v221', cid, f"request={rid}; user={uid}; chars={len(str(text or ''))}")
    except Exception:
        pass
    return rid

def _v221_owner_request_rows(status: str='new') -> list[dict]:
    status = status if status in {'new', 'deferred', 'done'} else 'new'
    rows = [dict(x) for x in (_v221_owner_requests_root().get('items') or {}).values() if isinstance(x, dict) and str(x.get('status') or 'new') == status]
    rows.sort(key=lambda x: (str(x.get('created_at') or ''), int(x.get('message_request_id') or 0)), reverse=True)
    return rows

def _v221_owner_request_get(request_id: int) -> dict | None:
    try:
        row = (_v221_owner_requests_root().get('items') or {}).get(str(int(request_id)))
    except Exception:
        row = None
    return row if isinstance(row, dict) else None

def _v221_owner_request_set_status(request_id: int, status: str) -> bool:
    row = _v221_owner_request_get(int(request_id))
    status = str(status or '')
    if not row or status not in {'new', 'deferred', 'done'}:
        return False
    now_s = now_local().isoformat(timespec='seconds')
    row['status'] = status
    if status == 'deferred':
        row['deferred_at'] = now_s
    if status == 'done':
        row['completed_at'] = now_s
    if status == 'new':
        row['deferred_at'] = ''
        row['completed_at'] = ''
    _v221_owner_requests_persist(f'status_{status}')
    return True

def _v221_request_preview(text: str, n: int=36) -> str:
    value = _v221_re.sub('\\s+', ' ', str(text or '')).strip()
    return value if len(value) <= n else value[:max(1, n - 1)] + '…'

def build_v221_owner_requests_text(status: str='new', page: int=0) -> str:
    status = status if status in {'new', 'deferred', 'done'} else 'new'
    rows = _v221_owner_request_rows(status)
    pages = max(1, (len(rows) + V221_OWNER_REQUEST_PAGE_SIZE - 1) // V221_OWNER_REQUEST_PAGE_SIZE)
    page = max(0, min(int(page or 0), pages - 1))
    title = {'new': '📥 Новые', 'deferred': '⏸ Отложенные', 'done': '✅ Выполненные'}[status]
    return f'📨 СООБЩЕНИЯ ОТ ПОЛЬЗОВАТЕЛЕЙ\n\n{title}: {len(rows)}\nСтраница: {page + 1}/{pages}\n\nНажмите обращение, чтобы открыть полный текст.'

def build_v221_owner_requests_keyboard(status: str='new', page: int=0):
    status = status if status in {'new', 'deferred', 'done'} else 'new'
    rows = _v221_owner_request_rows(status)
    pages = max(1, (len(rows) + V221_OWNER_REQUEST_PAGE_SIZE - 1) // V221_OWNER_REQUEST_PAGE_SIZE)
    page = max(0, min(int(page or 0), pages - 1))
    kb = types.InlineKeyboardMarkup(row_width=1)
    kb.row(IB('📥 Новые', callback_data='v221:req:list:new:0'), IB('⏸ Отложенные', callback_data='v221:req:list:deferred:0'), IB('✅ Выполненные', callback_data='v221:req:list:done:0'))
    start = page * V221_OWNER_REQUEST_PAGE_SIZE
    for row in rows[start:start + V221_OWNER_REQUEST_PAGE_SIZE]:
        rid = int(row.get('message_request_id') or 0)
        when = str(row.get('created_at') or '')
        tm = when[11:16] if len(when) >= 16 else when[:5]
        who = str(row.get('username') or row.get('name') or row.get('source_user_id') or 'пользователь')
        chat = str(row.get('source_chat_title') or row.get('source_chat_id') or 'чат')
        label = f"{tm} · {chat} · {who} · {_v221_request_preview(row.get('text'))}"
        if len(label) > 62:
            label = label[:59] + '…'
        kb.row(IB(label, callback_data=f'v221:req:open:{rid}:{status}:{page}'))
    nav = []
    if page > 0:
        nav.append(IB('⬅️', callback_data=f'v221:req:list:{status}:{page - 1}'))
    nav.append(IB(f'{page + 1}/{pages}', callback_data='none'))
    if page + 1 < pages:
        nav.append(IB('➡️', callback_data=f'v221:req:list:{status}:{page + 1}'))
    kb.row(*nav)
    kb.row(IB('🔙 Назад в Инфо', callback_data='journal_back'), IB('❌ Закрыть', callback_data='info_close'))
    return kb

def build_v221_owner_request_card_text(request_id: int) -> str:
    row = _v221_owner_request_get(int(request_id))
    if not row:
        return '📨 Обращение не найдено.'
    status = {'new': '📥 Новое', 'deferred': '⏸ Отложено', 'done': '✅ Выполнено'}.get(str(row.get('status') or 'new'), str(row.get('status') or ''))
    who = str(row.get('name') or '').strip()
    if row.get('username'):
        who = (who + f" (@{row.get('username')})").strip()
    if not who:
        who = str(row.get('source_user_id') or '—')
    body = str(row.get('text') or '')
    if len(body) > 3200:
        body = body[:3200] + '\n…\nПолный текст показан отдельным временным сообщением.'
    return f"📨 ОБРАЩЕНИЕ #{int(row.get('message_request_id') or request_id)}\n\nОт: {who}\nЧат: {row.get('source_chat_title') or row.get('source_chat_id')}\nДата: {row.get('created_at') or '—'}\nСтатус: {status}\n\nТекст:\n{body}"

def build_v221_owner_request_card_keyboard(request_id: int, return_status: str='new', return_page: int=0):
    rid = int(request_id)
    status = return_status if return_status in {'new', 'deferred', 'done'} else 'new'
    page = max(0, int(return_page or 0))
    kb = types.InlineKeyboardMarkup(row_width=1)
    kb.row(IB('⏸ Отложить', callback_data=f'v221:req:set:{rid}:deferred:{status}:{page}'))
    kb.row(IB('✅ Выполнено', callback_data=f'v221:req:set:{rid}:done:{status}:{page}'))
    kb.row(IB('🔙 Назад', callback_data=f'v221:req:list:{status}:{page}'))
    return kb
_V221_OWNER_MSG_LOCK = _v221_threading.RLock()
_V221_OWNER_MSG_PENDING = {}

def _v221_owner_msg_key(chat_id: int, user_id: int) -> tuple[int, int]:
    return (int(chat_id), int(user_id))

def _v221_owner_msg_timer_key(chat_id: int, user_id: int) -> str:
    return f'v221-owner-msg:{int(chat_id)}:{int(user_id)}'

def _v221_owner_msg_sid() -> str:
    try:
        return str(_v213_input_sid())
    except Exception:
        return f'{int(_v221_time.time() * 1000):x}'

def _v221_owner_msg_pending(chat_id: int, user_id: int) -> dict | None:
    with _V221_OWNER_MSG_LOCK:
        row = _V221_OWNER_MSG_PENDING.get(_v221_owner_msg_key(chat_id, user_id))
        return dict(row) if isinstance(row, dict) else None

def _v221_owner_msg_clear(chat_id: int, user_id: int, sid: str | None=None) -> dict | None:
    key = _v221_owner_msg_key(chat_id, user_id)
    with _V221_OWNER_MSG_LOCK:
        row = _V221_OWNER_MSG_PENDING.get(key)
        if not isinstance(row, dict):
            return None
        if sid and str(row.get('session_id') or '') != str(sid):
            return None
        _V221_OWNER_MSG_PENDING.pop(key, None)
    try:
        DELAYED_SCHEDULER.cancel(_v221_owner_msg_timer_key(chat_id, user_id))
    except Exception:
        pass
    return dict(row)

def _v221_owner_msg_timeout(chat_id: int, user_id: int, sid: str) -> None:
    row = _v221_owner_msg_clear(chat_id, user_id, sid)
    if not row:
        return
    cid = int(chat_id)
    mid = int(row.get('message_id') or 0)
    if mid:
        try:
            show_contour_menu_closed_v221(cid, int(user_id), mid)
        except Exception:
            pass
    try:
        send_and_auto_delete(cid, '⌛ Ввод сообщения владельцу отменён по таймеру.', 8)
    except Exception:
        pass
    try:
        bot_journal('owner_user_request_timeout_v221', cid, f'user={int(user_id)}')
    except Exception:
        pass

def _v221_owner_msg_input_keyboard(sid: str):
    short = str(sid or '')[:12]
    kb = types.InlineKeyboardMarkup(row_width=1)
    kb.row(IB('❌ Отмена', callback_data=f'v221:owner_msg:cancel:{short}'))
    kb.row(IB('🔙 Назад', callback_data=f'v221:owner_msg:back:{short}'))
    return kb

def start_owner_message_input_v221(chat_id: int, user_id: int, message_id: int=0) -> int:
    cid = int(chat_id)
    uid = int(user_id)
    mid = int(message_id or 0)
    sid = _v221_owner_msg_sid()
    delay = float(_v213_input_timeout_seconds())
    _v221_owner_msg_clear(cid, uid)
    text = f'Напишите сообщение владельцу.\n\n⏳ Автоотмена бездействия: {_format_duration_short(delay)}.'
    kb = _v221_owner_msg_input_keyboard(sid)
    if mid:
        try:
            result = fast_ui_edit_message_text(cid, mid, text, reply_markup=kb, purpose='owner_message_input_v221')
            if result != 'ok':
                mid = 0
        except Exception:
            mid = 0
    if not mid:
        try:
            sent = bot.send_message(cid, text, reply_markup=kb)
            mid = int(getattr(sent, 'message_id', 0) or 0)
        except Exception:
            mid = 0
    with _V221_OWNER_MSG_LOCK:
        _V221_OWNER_MSG_PENDING[_v221_owner_msg_key(cid, uid)] = {'session_id': sid, 'message_id': mid, 'created_at': _v221_time.time(), 'last_activity': _v221_time.time()}
    try:
        key = _v221_owner_msg_timer_key(cid, uid)
        DELAYED_SCHEDULER.cancel(key)
        DELAYED_SCHEDULER.schedule(key, delay, _v221_owner_msg_timeout, cid, uid, sid)
    except Exception:
        pass
    try:
        if mid:
            register_open_window(cid, mid, 'owner_message_input', code=V221_OWNER_MESSAGE_INPUT_MARKER, params={'user_id': uid})
    except Exception:
        pass
    return mid

def _v221_owner_msg_touch(chat_id: int, user_id: int) -> None:
    row = _v221_owner_msg_pending(chat_id, user_id)
    if not row:
        return
    sid = str(row.get('session_id') or '')
    delay = float(_v213_input_timeout_seconds())
    with _V221_OWNER_MSG_LOCK:
        live = _V221_OWNER_MSG_PENDING.get(_v221_owner_msg_key(chat_id, user_id))
        if isinstance(live, dict) and str(live.get('session_id') or '') == sid:
            live['last_activity'] = _v221_time.time()
    try:
        key = _v221_owner_msg_timer_key(chat_id, user_id)
        DELAYED_SCHEDULER.cancel(key)
        DELAYED_SCHEDULER.schedule(key, delay, _v221_owner_msg_timeout, int(chat_id), int(user_id), sid)
    except Exception:
        pass

def _v221_capture_owner_message(msg) -> bool:
    try:
        cid = int(msg.chat.id)
        uid = int(getattr(getattr(msg, 'from_user', None), 'id', 0) or 0)
    except Exception:
        return False
    row = _v221_owner_msg_pending(cid, uid)
    if not row:
        return False
    text = str(getattr(msg, 'text', '') or '')
    if not text:
        return False
    if text.lstrip().startswith('/'):
        _v221_owner_msg_touch(cid, uid)
        try:
            send_and_auto_delete(cid, 'Команды здесь не принимаются. Напишите обычное текстовое сообщение владельцу или нажмите «Отмена».', 10)
        except Exception:
            pass
        return True
    sid = str(row.get('session_id') or '')
    live = _v221_owner_msg_clear(cid, uid, sid)
    if not live:
        return True
    rid = _v221_create_owner_request(msg, text)
    try:
        schedule_command_delete(msg)
    except Exception:
        pass
    mid = int(live.get('message_id') or 0)
    if mid:
        try:
            kb = types.InlineKeyboardMarkup(row_width=1)
            kb.row(IB('❌ Закрыть', callback_data='aux_close'))
            fast_ui_edit_message_text(cid, mid, '✅ Сообщение отправлено владельцу.', reply_markup=kb, purpose='owner_message_sent_v221')
        except Exception:
            pass
    else:
        try:
            send_and_auto_delete(cid, '✅ Сообщение отправлено владельцу.', 10)
        except Exception:
            pass
    try:
        bot_journal('owner_user_request_submitted_v221', cid, f'request={rid}; user={uid}')
    except Exception:
        pass
    return True
_V221_PREV_PROCESS_NEW_UPDATES = getattr(bot, 'process_new_updates', None)

def _v221_process_new_updates(updates):
    remaining = []
    for update in list(updates or []):
        msg = getattr(update, 'message', None)
        if msg is not None:
            try:
                if _v221_capture_owner_message(msg):
                    continue
            except Exception as exc:
                try:
                    log_error(f'v221 owner-message capture: {exc}')
                except Exception:
                    pass
        remaining.append(update)
    if remaining and callable(_V221_PREV_PROCESS_NEW_UPDATES):
        return _V221_PREV_PROCESS_NEW_UPDATES(remaining)
    return None
if callable(_V221_PREV_PROCESS_NEW_UPDATES):
    bot.process_new_updates = _v221_process_new_updates

def v221_owner_message_callback_final(call, resolved: str) -> bool:
    raw = str(resolved or '')
    if not raw.startswith('v221:owner_msg:'):
        return False
    try:
        cid = int(call.message.chat.id)
        uid = int(getattr(getattr(call, 'from_user', None), 'id', 0) or 0)
        mid = int(call.message.message_id)
    except Exception:
        return True
    action = raw.split(':')[2] if len(raw.split(':')) > 2 else ''
    if action == 'start':
        if not _v215_circle_business_chat(cid) or contour_menu_access_allowed(cid, uid):
            try:
                show_contour_start_modes(cid, uid, mid)
            except Exception:
                pass
            try:
                bot.answer_callback_query(call.id, 'Меню уже доступно.', show_alert=False)
            except Exception:
                pass
            return True
        start_owner_message_input_v221(cid, uid, mid)
        try:
            bot.answer_callback_query(call.id)
        except Exception:
            pass
        return True
    if action in {'cancel', 'back'}:
        row = _v221_owner_msg_pending(cid, uid)
        if row:
            sid = str(row.get('session_id') or '')
            token = raw.split(':', 3)[3] if raw.count(':') >= 3 else ''
            if token and (not sid.startswith(str(token))):
                try:
                    bot.answer_callback_query(call.id, 'Сессия уже устарела.', show_alert=False)
                except Exception:
                    pass
                return True
            _v221_owner_msg_clear(cid, uid, sid)
        show_contour_menu_closed_v221(cid, uid, mid)
        try:
            bot.answer_callback_query(call.id, 'Ввод отменён' if action == 'cancel' else '')
        except Exception:
            pass
        return True
    return True

def v221_owner_requests_callback_final(call, resolved: str) -> bool:
    raw = str(resolved or '')
    if not raw.startswith('v221:req:'):
        return False
    try:
        cid = int(call.message.chat.id)
        uid = int(getattr(getattr(call, 'from_user', None), 'id', 0) or 0)
    except Exception:
        return True
    if cid != int(OWNER_ID or 0) or uid != int(OWNER_ID or 0):
        try:
            bot.answer_callback_query(call.id, 'Только основной владелец.', show_alert=True)
        except Exception:
            pass
        return True
    parts = raw.split(':')
    action = parts[2] if len(parts) > 2 else ''
    try:
        if action == 'list':
            status = parts[3] if len(parts) > 3 else 'new'
            page = int(parts[4]) if len(parts) > 4 else 0
            safe_edit(bot, call, build_v221_owner_requests_text(status, page), reply_markup=build_v221_owner_requests_keyboard(status, page))
        elif action == 'open':
            rid = int(parts[3])
            status = parts[4] if len(parts) > 4 else 'new'
            page = int(parts[5]) if len(parts) > 5 else 0
            safe_edit(bot, call, build_v221_owner_request_card_text(rid), reply_markup=build_v221_owner_request_card_keyboard(rid, status, page))
            _v221_request_full_text_if_needed(call, rid)
        elif action == 'set':
            rid = int(parts[3])
            value = parts[4]
            return_status = parts[5] if len(parts) > 5 else 'new'
            page = int(parts[6]) if len(parts) > 6 else 0
            _v221_owner_request_set_status(rid, value)
            safe_edit(bot, call, build_v221_owner_requests_text(return_status, page), reply_markup=build_v221_owner_requests_keyboard(return_status, page))
        try:
            bot.answer_callback_query(call.id)
        except Exception:
            pass
    except Exception as exc:
        try:
            bot.answer_callback_query(call.id, str(exc)[:160], show_alert=True)
        except Exception:
            pass
    return True

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

def _v221_complete_command(msg) -> bool:
    rid, matched = _v218_completion_command_target(msg)
    if not matched:
        return False
    try:
        cid = int(msg.chat.id)
        uid = int(getattr(getattr(msg, 'from_user', None), 'id', 0) or 0)
    except Exception:
        return True
    try:
        schedule_command_delete(msg)
    except Exception:
        pass
    if rid is None:
        reply = getattr(msg, 'reply_to_message', None)
        if reply is None:
            send_and_auto_delete(cid, 'Укажите конкретную напоминалку: /done_N или ответьте /выполнено на её сообщение.', 12)
            return True
        rid, error = _v217_find_reply_reminder(cid, int(getattr(reply, 'message_id', 0) or 0))
        if rid is None:
            send_and_auto_delete(cid, error, 12)
            return True
    cfg = reminder_cfg_global_for_completion(int(rid))
    if not cfg or cid not in _v149_reminder_chat_ids(cfg):
        send_and_auto_delete(cid, f'Напоминалка #{int(rid)} не относится к этому чату.', 12)
        return True
    if _v218_completion_mode(cfg, cid) != 'slash':
        mode = _v218_completion_mode(cfg, cid)
        text = 'Для этой напоминалки выбран способ выполнения «КНОПКА».' if mode == 'button' else 'Для этой напоминалки выполнение отключено.'
        send_and_auto_delete(cid, text, 12)
        return True
    ok, answer = _v149_complete_reminder(int(rid), cid, uid, _v149_actor_label(msg))
    send_and_auto_delete(cid, answer, 12)
    return True
_V221_PREV_COMPLETE_REMINDER = _V220_PREV_COMPLETE_REMINDER

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
_V221_PREV_V218_CALLBACK = _canon_v218_callback_final__001

def _v221_v218_callback_final(call, resolved: str) -> bool:
    raw = str(resolved or '')
    if raw.startswith('v149:rem:done:'):
        try:
            parts = raw.split(':')
            rid = int(parts[3])
            payload_chat = int(parts[4])
            cid = int(call.message.chat.id)
            uid = int(getattr(getattr(call, 'from_user', None), 'id', 0) or 0)
        except Exception:
            return True
        cfg = reminder_cfg_global_for_completion(rid)
        if payload_chat != cid or not cfg or cid not in _v149_reminder_chat_ids(cfg):
            try:
                bot.answer_callback_query(call.id, 'Эта напоминалка не относится к текущему чату.', show_alert=True)
            except Exception:
                pass
            return True
        if _v218_completion_mode(cfg, cid) != 'button':
            try:
                bot.answer_callback_query(call.id, 'Способ выполнения этой напоминалки уже изменён.', show_alert=True)
            except Exception:
                pass
            return True
        ok, answer = _v149_complete_reminder(rid, cid, uid, _v149_actor_label(call))
        try:
            bot.answer_callback_query(call.id, answer[:180], show_alert=not ok)
        except Exception:
            pass
        return True
    return bool(_V221_PREV_V218_CALLBACK(call, raw))
try:
    _v177_legacy_0007_bot_journal('v221_contour_reminder_requests_ready', int(OWNER_ID or 0), 'final_markup_filter=1; stale_hard_gate=1; menu_closed_contact_owner=1; reminder_global_lookup=1; owner_requests=persistent')
except Exception:
    pass

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

def _v221_request_full_text_if_needed(call, request_id: int) -> None:
    row = _v221_owner_request_get(int(request_id))
    text = str((row or {}).get('text') or '')
    if len(text) <= 3200:
        return
    try:
        cid = int(call.message.chat.id)
    except Exception:
        return
    chunk_size = 3500
    total = max(1, (len(text) + chunk_size - 1) // chunk_size)
    for idx in range(total):
        chunk = text[idx * chunk_size:(idx + 1) * chunk_size]
        title = f'📄 Полный текст обращения #{int(request_id)}' + (f' · {idx + 1}/{total}' if total > 1 else '')
        try:
            send_and_auto_delete(cid, f'{title}:\n\n{chunk}', 120)
        except Exception:
            pass
V223_DIRECTIVE_POLICY_KEY = 'directive_policy_v223'
V223_DIRECTIVE_MODES = ('finance', 'forward', 'reminders', 'tasks')

def _v223_directive_policy(chat_id: int, create: bool=False) -> dict:
    cid = int(chat_id)
    settings = _v215_mode_settings(cid)
    row = settings.get(V223_DIRECTIVE_POLICY_KEY)
    if not isinstance(row, dict):
        if not create:
            return {'enabled': False, 'annotations': {'tz': True, 'iz_mr': True}}
        row = {'enabled': False, 'annotations': {'tz': True, 'iz_mr': True}}
        settings[V223_DIRECTIVE_POLICY_KEY] = row
    row['enabled'] = bool(row.get('enabled', False))
    annotations = row.get('annotations')
    if not isinstance(annotations, dict):
        annotations = {}
        row['annotations'] = annotations
    annotations.setdefault('tz', True)
    annotations.setdefault('iz_mr', True)
    return row

def directive_chat_enabled_v223(chat_id: int) -> bool:
    try:
        cid = int(chat_id)
        return bool(_v215_circle_business_chat(cid) and _v223_directive_policy(cid, False).get('enabled', False))
    except Exception:
        return False

def directive_annotation_allowed_v223(chat_id: int, kind: str) -> bool:
    """Local directive annotation gate. Global v219 gate is applied separately."""
    try:
        cid = int(chat_id)
        if not directive_chat_enabled_v223(cid):
            return True
        key = 'iz_mr' if str(kind or '').replace('-', '_').casefold() in {'iz_mr', 'izmr', 'marker'} else 'tz'
        return bool((_v223_directive_policy(cid, False).get('annotations') or {}).get(key, True))
    except Exception:
        return True

def v223_effective_chat_capabilities(chat_id: int, user_id: int=0) -> dict:
    """One canonical read model for circle business/menu/annotation policy."""
    cid = int(chat_id)
    uid = int(user_id or 0)
    directive = bool(directive_chat_enabled_v223(cid))
    modes = {mode: bool(_v215_mode_enabled(cid, mode)) for mode in V223_DIRECTIVE_MODES}
    try:
        menu_access = bool(contour_menu_access_enabled_v220(cid))
    except Exception:
        menu_access = True
    try:
        tz_global = bool(circle_annotation_button_enabled_v219('tz', cid))
    except Exception:
        tz_global = True
    try:
        marker_global = bool(circle_annotation_button_enabled_v219('iz_mr', cid))
    except Exception:
        marker_global = True
    return {'chat_id': cid, 'circle': int(circle_level_for_chat(cid)) if _v215_circle_business_chat(cid) else 0, 'directive_mode': directive, 'menu_access': menu_access, 'can_edit_modes': bool(uid == int(OWNER_ID or 0)), 'modes': modes, 'tz': tz_global, 'markers': marker_global}

def _v223_touch_policy(chat_id: int, reason: str) -> None:
    cid = int(chat_id)
    row = _v223_directive_policy(cid, True)
    row['updated_at'] = float(_v221_time.time())
    row['updated_by'] = int(OWNER_ID or 0)
    _v215_persist_mode(cid, f"directive_{str(reason or 'update')[:50]}")

def set_directive_chat_enabled_v223(chat_id: int, enabled: bool) -> bool:
    cid = int(chat_id)
    if not _v215_circle_business_chat(cid):
        raise ValueError('directive policy is available only for circle 1/2 chats')
    row = _v223_directive_policy(cid, True)
    row['enabled'] = bool(enabled)
    _v223_touch_policy(cid, 'enabled')
    try:
        bot_journal('directive_policy_toggle_v223', cid, f'enabled={int(bool(enabled))}; by={int(OWNER_ID or 0)}')
    except Exception:
        pass
    return bool(row['enabled'])

def set_directive_annotation_v223(chat_id: int, kind: str, enabled: bool) -> bool:
    cid = int(chat_id)
    if not _v215_circle_business_chat(cid):
        raise ValueError('directive policy is available only for circle 1/2 chats')
    key = 'iz_mr' if str(kind or '').replace('-', '_').casefold() in {'iz_mr', 'izmr', 'marker'} else 'tz'
    row = _v223_directive_policy(cid, True)
    annotations = row.setdefault('annotations', {})
    annotations[key] = bool(enabled)
    _v223_touch_policy(cid, f'annotation_{key}')
    try:
        bot_journal('directive_annotation_toggle_v223', cid, f'kind={key}; enabled={int(bool(enabled))}')
    except Exception:
        pass
    return bool(annotations[key])

def v223_set_business_mode(chat_id: int, mode: str, enabled: bool) -> bool:
    """Set the EXISTING canonical mode flag; do not create a second mode state."""
    cid = int(chat_id)
    mode = str(mode or '')
    if mode not in V223_DIRECTIVE_MODES or not _v215_circle_business_chat(cid):
        raise ValueError('unknown directive mode/chat')
    desired = bool(enabled)
    current = bool(_v215_mode_enabled(cid, mode))
    if current != desired:
        _v215_toggle_mode(cid, int(OWNER_ID or 0), mode)
    return bool(_v215_mode_enabled(cid, mode))

def _v223_directive_mode_from_callback(raw: str) -> str:
    value = str(raw or '')
    if value.startswith('v215:mode:'):
        parts = value.split(':')
        if len(parts) > 3 and parts[3] in V223_DIRECTIVE_MODES:
            return parts[3]
    if value.startswith('v218:demo:'):
        parts = value.split(':')
        if len(parts) > 2 and parts[2] in V223_DIRECTIVE_MODES:
            return parts[2]
    if value.startswith(('rem:', 'v149:rem:', 'v217:remchat:')):
        return 'reminders'
    if value.startswith(('v172:task:', 'v174:td:', 'v219:task:')):
        return 'tasks'
    if value.startswith(('fw_', 'fv:', 'fwdcopy_', 'v217:fwdscope:')):
        return 'forward'
    if value.startswith('d:'):
        low = value.casefold()
        if low.endswith(':back_main') or low.endswith(':info'):
            return ''
        if 'forward' in low or 'перес' in low:
            return 'forward'
        return 'finance'
    if value.startswith(('c:', 'main_close:', 'remaining_open:')):
        return 'finance'
    return ''

def _v223_is_mode_mutation_callback(raw: str) -> bool:
    value = str(raw or '')
    if value.startswith('v215:mode:toggle:'):
        return True
    if value.startswith('v174:td:toggle:'):
        return True
    if value.startswith('d:') and any((token in value for token in ('fin_mode_toggle_', 'fin_mode_off_', 'qb_mode_normal_', 'qb_mode_open_', 'qb_mode_first_', 'qb_hidden_toggle_', 'qb_finwin_open_'))):
        return True
    return False
_V223_PREV_BUILD_CONTOUR_START_MODES = _v217_build_contour_start_modes

def _v223_build_contour_start_modes(chat_id: int, user_id: int=0):
    cid = int(chat_id)
    if not directive_chat_enabled_v223(cid):
        return _V223_PREV_BUILD_CONTOUR_START_MODES(cid, int(user_id or 0))
    try:
        level = 2 if int(circle_level_for_chat(cid)) == 2 else 1
    except Exception:
        level = 1
    variant = contour_start_menu_variant_v217(cid)
    name = str(get_chat_display_name(cid) or f'Чат {cid}')
    enabled_modes = [mode for mode in V223_DIRECTIVE_MODES if _v215_mode_enabled(cid, mode)]
    lines = ['🏠 ГЛАВНОЕ МЕНЮ', '', name, f"Контур: {('1️⃣ первый' if level == 1 else '2️⃣ второй')}", '🔒 Директивный режим', '']
    if enabled_modes:
        lines.append('Доступные разделы:')
        lines.extend((f'✅ {_v215_mode_title(mode)}' for mode in enabled_modes))
        lines += ['', 'Набор функций этого чата задаёт владелец.']
    else:
        lines += ['Владелец пока не включил для этого чата рабочие разделы.', '', 'Набор функций этого чата задаёт владелец.']
    text = window_mark('\n'.join(lines), V217_CONTOUR_MENU_MARKER)
    kb = types.InlineKeyboardMarkup(row_width=2 if variant == 2 else 1)
    buttons = [IB(_v215_mode_title(mode), callback_data=f'v215:mode:open:{mode}') for mode in enabled_modes]
    if variant == 2:
        for idx in range(0, len(buttons), 2):
            kb.row(*buttons[idx:idx + 2])
    else:
        for button in buttons:
            kb.row(button)
    kb.row(IB('ℹ️ Как пользоваться', callback_data='v215:mode:guide'))
    kb.row(IB('❌ Закрыть', callback_data='aux_close'))
    return (text, kb)
_V224_PREV_SHOW_CONTOUR_START = _v221_show_contour_start_modes

def _v224_show_contour_start_modes(chat_id: int, user_id: int=0, message_id: int=0) -> int:
    cid = int(chat_id)
    uid = int(user_id or 0)
    mid = int(message_id or 0)
    if not directive_chat_enabled_v223(cid):
        return int(_V224_PREV_SHOW_CONTOUR_START(cid, uid, mid) or 0)
    try:
        if not contour_menu_access_enabled_v220(cid):
            return int(show_contour_menu_closed_v221(cid, uid, mid) or mid)
    except Exception:
        pass
    home = resolve_contour_home(cid)
    if home != 'selector':
        if home in {'finance', 'tasks', 'forward', 'reminders'}:
            return int(v224_open_directive_mode_home(cid, uid, mid, home) or mid or 0)
        return int(_v213_show_neutral_home(cid, mid) or mid or 0)
    return int(_V224_PREV_SHOW_CONTOUR_START(cid, uid, mid) or 0)
_V223_PREV_BUILD_GUIDE = _canon_build_contour_menu_guide__001

def _v223_build_contour_menu_guide(chat_id: int):
    cid = int(chat_id)
    if not directive_chat_enabled_v223(cid):
        return _V223_PREV_BUILD_GUIDE(cid)
    text = window_mark('ℹ️ КАК ПОЛЬЗОВАТЬСЯ БОТОМ\n\n🔒 В этом чате действует директивный режим.\nВ главном меню показываются только разделы, разрешённые владельцем.\nПользователь не может самостоятельно включать или выключать режимы.\n\nЕсли нужного раздела нет — обратитесь к владельцу.\nКоманда /start возвращает в актуальное меню.', V215_CONTOUR_MODE_MARKER)
    kb = types.InlineKeyboardMarkup()
    kb.row(IB('🔙 К режимам', callback_data='v215:mode:back'))
    return (text, kb)
_V223_PREV_BUILD_MODE_CONTROL = _v218_build_contour_mode_control

def _v223_build_contour_mode_control(chat_id: int, user_id: int, mode: str):
    cid = int(chat_id)
    mode = str(mode or '')
    if not directive_chat_enabled_v223(cid):
        return _V223_PREV_BUILD_MODE_CONTROL(cid, int(user_id or 0), mode)
    enabled = bool(_v215_mode_enabled(cid, mode))
    text = window_mark(f"{_v215_mode_title(mode)}\n\n{_v216_mode_description(mode)}\n\nСостояние: {('✅ Включено' if enabled else '⬜ Выключено')}\n\n🔒 Набор режимов этого чата задаёт владелец.", V215_CONTOUR_MODE_MARKER)
    kb = types.InlineKeyboardMarkup()
    if enabled:
        short = {'finance': 'финансы', 'forward': 'пересылку', 'reminders': 'напоминания', 'tasks': 'задачи'}.get(mode, 'меню')
        kb.row(IB(f'➡️ Открыть {short}', callback_data=f'v215:mode:go:{mode}'))
    kb.row(IB('🔙 К режимам', callback_data='v215:mode:back'))
    return (text, kb)
_V223_PREV_CONTOUR_GUARD = _v221_contour_callback_guard

def _v223_contour_callback_guard(call, resolved: str) -> bool:
    raw = str(resolved or '')
    try:
        cid = int(call.message.chat.id)
        uid = int(getattr(getattr(call, 'from_user', None), 'id', 0) or 0)
    except Exception:
        return bool(_V223_PREV_CONTOUR_GUARD(call, raw))
    # R10: stale buttons from a business mode must never reopen a mode that the
    # owner has disabled for contour 1/2. Mode-management callbacks themselves
    # remain allowed so an authorized user can enable a mode from the menu.
    try:
        if _v215_circle_business_chat(cid) and (not raw.startswith('v215:mode:')):
            mode_now = _v223_directive_mode_from_callback(raw)
            if mode_now and (not _v215_mode_enabled(cid, mode_now)):
                try:
                    bot.answer_callback_query(call.id, 'Этот режим выключен. Возвращаю в меню режимов.')
                except Exception:
                    pass
                try:
                    show_contour_start_modes(cid, uid, int(call.message.message_id))
                except Exception:
                    pass
                try:
                    bot_journal('contour_disabled_mode_redirect_r10', cid, f'mode={mode_now}; action={raw}; user={uid}')
                except Exception:
                    pass
                return True
    except Exception:
        pass
    if directive_chat_enabled_v223(cid):
        if _v223_is_mode_mutation_callback(raw):
            try:
                bot.answer_callback_query(call.id, '🔒 Настройки этого чата управляются владельцем.', show_alert=True)
            except Exception:
                pass
            try:
                bot_journal('directive_gate_decision_v224', cid, f'decision=BLOCK; reason=mode_mutation; action={raw}; user={uid}; owner_as_chat={int(uid == int(OWNER_ID or 0))}')
            except Exception:
                pass
            return True
        mode = _v223_directive_mode_from_callback(raw)
        if mode and (not _v215_mode_enabled(cid, mode)):
            try:
                bot.answer_callback_query(call.id, '🔒 Эта функция отключена владельцем.', show_alert=True)
            except Exception:
                pass
            try:
                bot_journal('directive_gate_decision_v224', cid, f'decision=BLOCK; reason=mode_disabled; mode={mode}; action={raw}; user={uid}; owner_as_chat={int(uid == int(OWNER_ID or 0))}')
            except Exception:
                pass
            return True
        if mode or raw in {'nav_prev', 'v217:contour:menu', 'v215:mode:back'} or raw.endswith(':back_main'):
            try:
                bot_journal('directive_gate_decision_v224', cid, f"decision=ALLOW; mode={mode or 'navigation'}; action={raw}; user={uid}; owner_as_chat={int(uid == int(OWNER_ID or 0))}")
            except Exception:
                pass
    return bool(_V223_PREV_CONTOUR_GUARD(call, raw))

def v224_refresh_chat_markup_only(chat_id: int) -> int:
    cid = int(chat_id)
    changed = 0
    try:
        with _V221_LIVE_MARKUP_LOCK:
            live = [(k, dict(v or {})) for k, v in _V221_LIVE_MARKUP.items() if int(k[0]) == cid]
        for (_cid, mid), row in live:
            before = row.get('markup')
            source = row.get('source_markup') if row.get('source_markup') is not None else before
            after = v227_render_effective_contour_markup(source, str(row.get('text') or ''), cid)
            if _v221_markup_fingerprint(before) == _v221_markup_fingerprint(after):
                continue
            bot.edit_message_reply_markup(chat_id=cid, message_id=int(mid), reply_markup=after)
            v221_record_live_markup(cid, int(mid), after, str(row.get('text') or ''), source_markup=source)
            changed += 1
    except Exception:
        pass
    try:
        bot_journal('directive_markup_refresh_v224', cid, f'changed={changed}')
    except Exception:
        pass
    return changed

def v223_refresh_chat_policy(chat_id: int) -> int:
    """v224 targeted refresh: only target chat; navigation policy is authoritative."""
    cid = int(chat_id)
    changed = v224_refresh_chat_markup_only(cid)
    try:
        reg_fn = globals().get('_open_window_registry')
        rows = list((reg_fn() if callable(reg_fn) else data.get('open_window_registry') or {}).values())
        target_rows = [row for row in rows if isinstance(row, dict) and int(row.get('chat_id') or 0) == cid and int(row.get('message_id') or 0)]
        target_rows.sort(key=lambda r: str(r.get('updated_at') or ''), reverse=True)
        if target_rows:
            row = target_rows[0]
            mid = int(row.get('message_id') or 0)
            open_resolved_contour_home(cid, 0, mid, str(row.get('day_key') or today_key()))
            changed += 1
        else:
            open_resolved_contour_home(cid, 0, 0, today_key())
            changed += 1
    except Exception:
        pass
    try:
        bot_journal('directive_policy_refresh_v224', cid, f'changed={changed}; targeted=1; home={resolve_contour_home(cid)}')
    except Exception:
        pass
    return changed

def v224_schedule_targeted_policy_refresh(chat_id: int, *, markup_only: bool=False) -> None:
    cid = int(chat_id)

    def _job():
        try:
            (v224_refresh_chat_markup_only if markup_only else v223_refresh_chat_policy)(cid)
        except Exception as exc:
            try:
                bot_journal('directive_refresh_failed_v224', cid, str(exc)[:300], 'WARN')
            except Exception:
                pass
    try:
        pool = globals().get('GENERAL_TASK_POOL')
        if pool is not None and pool.submit_unique(f'v224-directive-refresh:{cid}:{int(markup_only)}', _job):
            return
    except Exception:
        pass
    try:
        DELAYED_SCHEDULER.schedule(f'v224-directive-refresh:{cid}:{int(markup_only)}', 0.05, _job)
    except Exception:
        pass
try:
    WINDOW_MARKER_CONSTANTS.setdefault('v223:directive:*', 'Ф265')
    WINDOW_MARKER_CONSTANTS.setdefault('sp:dashboard:x', 'Ф217')
    WINDOW_MARKER_CONSTANTS.setdefault('v174:td:list:*', 'Ф248')
    _v177_legacy_0007_bot_journal('v223_directive_policy_ready', int(OWNER_ID or 0), 'per_chat_lock=1; canonical_mode_flags=preserved; local_tz_marker_gate=1; stale_callbacks=hard_blocked')
except Exception:
    pass
try:
    WINDOW_MARKER_CONSTANTS.update({'v174:td:open:*': 'Ф249', 'v174:td:status:*': 'Ф249', 'v174:td:edit:*': 'Ф249', 'v174:td:priority:*': 'Ф249', 'v174:td:take:*': 'Ф249', 'v174:td:history:*': 'Ф245', 'v174:td:input:*': 'Ф252', 'v174:td:kw:*': 'Ф250', 'v174:td:kwedit:*': 'Ф252', 'v174:td:kwreset:*': 'Ф250', 'v174:td:auto': 'Ф250'})
except Exception:
    pass
V229_TASK_SINGLE_WINDOW_KEY = 'tasks_single_window_v229'

def tasks_single_window_enabled_v229() -> bool:
    gs = data.setdefault('_global_settings', {})
    if V229_TASK_SINGLE_WINDOW_KEY not in gs:
        gs[V229_TASK_SINGLE_WINDOW_KEY] = True
    return bool(gs.get(V229_TASK_SINGLE_WINDOW_KEY, True))

def set_tasks_single_window_v229(enabled: bool) -> bool:
    gs = data.setdefault('_global_settings', {})
    gs[V229_TASK_SINGLE_WINDOW_KEY] = bool(enabled)
    try:
        save_data(data, root_only=True)
    except Exception:
        pass
    try:
        schedule_delta_backup(int(OWNER_ID or 0), delay=0.2, reason='v229_tasks_single_window')
    except Exception:
        pass
    return bool(gs[V229_TASK_SINGLE_WINDOW_KEY])

def _v229_annotation_target_chat(chat_id: int) -> bool:
    try:
        cid = int(chat_id)
        if cid == int(OWNER_ID or 0):
            return False
        if _v215_circle_business_chat(cid):
            return True
        if task_dispatcher_enabled(cid):
            return True
        fn = globals().get('directive_chat_enabled_v223')
        if callable(fn) and fn(cid):
            return True
    except Exception:
        pass
    return False

def annotation_effective_v229(kind: str, chat_id: int) -> bool:
    """v232 global owner switch applies to every mode/contour/window; directive local OFF may further restrict."""
    try:
        cid = int(chat_id)
        key = 'iz_mr' if str(kind or '').replace('-', '_').casefold() in {'iz_mr', 'izmr', 'marker'} else 'tz'
        settings_fn = globals().get('_v219_annotation_settings')
        base = bool(settings_fn().get(key, True)) if callable(settings_fn) else True
        if not base:
            return False
        directive_fn = globals().get('directive_chat_enabled_v223')
        local_fn = globals().get('directive_annotation_allowed_v223')
        if callable(directive_fn) and directive_fn(cid) and callable(local_fn):
            return bool(local_fn(cid, key))
        return True
    except Exception:
        return True

def _v229_task_window_id(chat_id: int, fallback: int=0) -> int:
    cid = int(chat_id)
    try:
        reg = globals().get('_open_window_registry')
        rows = list((reg() if callable(reg) else data.get('open_window_registry') or {}).values())
        candidates = []
        for row in rows:
            if not isinstance(row, dict) or int(row.get('chat_id') or 0) != cid:
                continue
            if str(row.get('window_type') or '') == 'tasks' or str(row.get('code') or '') in {'Ф248', 'Ф249', 'Ф252'}:
                mid = int(row.get('message_id') or 0)
                if mid:
                    candidates.append(mid)
        if candidates:
            return max(candidates)
    except Exception:
        pass
    return int(fallback or 0)

def _v229_task_set_current(chat_id: int, task_uid: str='') -> None:
    try:
        s = _v174_settings(int(chat_id))
        s['single_window_current_uid_v229'] = str(task_uid or '').upper()
    except Exception:
        pass

def _v229_task_restore(chat_id: int, message_id: int, user_id: int=0, task_uid: str='') -> None:
    cid = int(chat_id)
    mid = int(message_id or 0)
    if not mid:
        return
    try:
        task = _v172_task_for_uid(str(task_uid or '').upper()) if task_uid else None
        if isinstance(task, dict) and int(task.get('chat_id', 0) or 0) == cid and (not task.get('deleted')):
            text, kb = (_v174_compact_text(task), _v174_compact_kb(task, cid, int(user_id or 0)))
            _v229_task_set_current(cid, str(task.get('uid') or ''))
        else:
            text, kb = _v174_menu_text_kb(cid, int(user_id or 0))
            _v229_task_set_current(cid, '')
        bot.edit_message_text(text, chat_id=cid, message_id=mid, reply_markup=kb)
    except Exception:
        pass
_V229_PREV_TASK_EDIT_CALL = _v228_prev_v174_edit_call

def _v174_edit_call(call, text, kb):
    try:
        cid = int(call.message.chat.id)
        current_mid = int(call.message.message_id)
        if tasks_single_window_enabled_v229() and task_dispatcher_enabled(cid):
            mid = _v229_task_window_id(cid, current_mid)
            raw = str(getattr(call, 'data', '') or '')
            parts = raw.split(':')
            if raw.startswith('v174:td:') and len(parts) > 3 and (parts[2] in {'open', 'status', 'edit', 'priority', 'take', 'input', 'history'}):
                _v229_task_set_current(cid, parts[3])
            elif raw.startswith('v174:td:') and parts[2] in {'menu', 'list', 'keywords', 'kw', 'branch'}:
                _v229_task_set_current(cid, '')
            try:
                fast_ui_edit_message_text(cid, mid, text, reply_markup=kb, purpose='tasks_single_window_v229')
                if current_mid != mid:
                    try:
                        bot.delete_message(cid, current_mid)
                    except Exception:
                        pass
                return
            except Exception:
                try:
                    bot.edit_message_text(text, chat_id=cid, message_id=mid, reply_markup=kb)
                    return
                except Exception:
                    pass
    except Exception:
        pass
    return _V229_PREV_TASK_EDIT_CALL(call, text, kb)
_V229_PREV_PROMPT_INPUT = _v228_prev_v174_prompt_input

def _v229_prompt_text(action: str, kind: str='', task_uid: str='') -> str:
    prompt = _V213_TASK_PROMPTS.get(str(action), 'Введите значение:')
    if str(action) == 'keywords':
        prompt = f'✏️ Отправьте новый список для «{_V174_KEYWORD_LABELS.get(kind, kind)}» через запятую.'
    if str(action).startswith('branch_'):
        prompt = {'branch_name': '📂 Введите название новой ветки задач.', 'branch_keywords': '🔑 Введите ключевые слова через запятую.', 'branch_rename': '✏️ Введите новое название ветки.'}.get(str(action), prompt)
    return _v213_prompt_text(prompt + f'\n\n⏳ Автоотмена бездействия: {_format_duration_short(_v213_input_timeout_seconds())}.')

def _canon_v174_prompt_input__001(chat_id: int, user_id: int, action: str, kind: str='', task_uid: str='', message_id: int=0):
    cid, uid = (int(chat_id), int(user_id))
    if not (tasks_single_window_enabled_v229() and task_dispatcher_enabled(cid)):
        return _V229_PREV_PROMPT_INPUT(cid, uid, action, kind, task_uid, message_id)
    cancel_task_input(cid, uid, 'new_input')
    sid = _v213_input_sid()
    delay = _v213_input_timeout_seconds()
    mid = _v229_task_window_id(cid, int(message_id or 0))
    if not mid:
        mid = int(_v212_open_task_window(cid, uid) or 0)
    kb = _v214_task_prompt_markup(cid, 'task', sid, action, kind, task_uid, False)
    if str(action) == 'text':
        task = _v172_task_for_uid(str(task_uid or '').upper())
        if isinstance(task, dict):
            kb = _v219_task_text_prompt_keyboard(cid, sid, task, mid)
    try:
        if mid:
            bot.edit_message_text(_v229_prompt_text(action, kind, task_uid), chat_id=cid, message_id=mid, reply_markup=kb)
    except Exception:
        pass
    with _V174_INPUT_LOCK:
        _V174_INPUT_WAIT[cid, uid] = {'action': str(action), 'kind': str(kind), 'task_uid': str(task_uid or '').upper(), 'message_id': mid, 'prompt_id': 0, 'created': _v213_time.time(), 'last_activity': _v213_time.time(), 'session_id': sid, 'generation': 1, 'single_window_v229': True}
    key = _v213_task_input_key(cid, uid, False)
    try:
        DELAYED_SCHEDULER.cancel(key)
    except Exception:
        pass
    DELAYED_SCHEDULER.schedule(key, delay, _v229_task_input_timeout, cid, uid, sid, False)
    return sid
_V229_PREV_TASK_TIMEOUT = _v214_task_input_timeout

def _v229_task_input_timeout(chat_id: int, user_id: int, sid: str, legacy: bool=False):
    row = _v214_task_pending_row(int(chat_id), int(user_id), bool(legacy))
    result = _V229_PREV_TASK_TIMEOUT(chat_id, user_id, sid, legacy)
    if result and isinstance(row, dict) and row.get('single_window_v229'):
        _v229_task_restore(int(chat_id), int(row.get('message_id') or 0), int(user_id), str(row.get('task_uid') or ''))
    return result
_V229_PREV_PENDING_CANCEL = _v214_pending_input_cancel_callback_final

def _canon_pending_input_cancel_callback_final__001(call) -> bool:
    raw = str(getattr(call, 'data', '') or '')
    row = None
    cid = uid = 0
    try:
        cid = int(call.message.chat.id)
        uid = int(getattr(getattr(call, 'from_user', None), 'id', 0) or 0)
        if raw.startswith('v213:input:cancel:task:'):
            row = _v214_task_pending_row(cid, uid, False)
    except Exception:
        pass
    handled = _V229_PREV_PENDING_CANCEL(call)
    if handled and isinstance(row, dict) and row.get('single_window_v229'):
        _v229_task_restore(cid, int(row.get('message_id') or 0), uid, str(row.get('task_uid') or ''))
    return handled
_V229_PREV_HANDLE_INPUT = _v219_task_handle_own_input

def _canon_v174_handle_own_input__001(msg) -> bool:
    try:
        if str(getattr(msg, 'content_type', '') or '') != 'text':
            return _V229_PREV_HANDLE_INPUT(msg)
        cid = int(msg.chat.id)
        uid = int(getattr(getattr(msg, 'from_user', None), 'id', 0) or 0)
        row = _v214_task_pending_row(cid, uid, False)
        if not (tasks_single_window_enabled_v229() and isinstance(row, dict) and row.get('single_window_v229')):
            return _V229_PREV_HANDLE_INPUT(msg)
        raw = str(getattr(msg, 'text', '') or '').strip()
        action = str(row.get('action') or '')
        kind = str(row.get('kind') or '')
        mid = int(row.get('message_id') or 0)
        if raw.casefold() in {'отмена', 'cancel', 'стоп'}:
            cancel_task_input(cid, uid, 'text_cancel')
            _v172_delete_quiet(cid, int(getattr(msg, 'message_id', 0) or 0))
            _v229_task_restore(cid, mid, uid, str(row.get('task_uid') or ''))
            return True
        user = getattr(msg, 'from_user', None)
        if action in {'new_task', 'new_purchase'}:
            cancel_task_input(cid, uid, 'submitted')
            task = _v172_create_task(cid, 'purchase' if action == 'new_purchase' else 'task', raw, user, source_msg=None)
            _v172_delete_quiet(cid, int(getattr(msg, 'message_id', 0) or 0))
            _v229_task_set_current(cid, str(task.get('uid') or ''))
            if mid:
                bot.edit_message_text(_v174_compact_text(task), chat_id=cid, message_id=mid, reply_markup=_v174_compact_kb(task, cid, uid))
            return True
        if action == 'keywords':
            cancel_task_input(cid, uid, 'submitted')
            values = [x.strip() for x in _v174_re.split('[,;\\n]+', raw) if x.strip()]
            _v174_set_keywords(cid, kind, values)
            _v172_delete_quiet(cid, int(getattr(msg, 'message_id', 0) or 0))
            body, kb = _v174_keyword_group_text_kb(cid, kind)
            bot.edit_message_text(body, chat_id=cid, message_id=mid, reply_markup=kb)
            return True
        if action == 'branch_name':
            name = ' '.join(raw.split())[:80]
            cancel_task_input(cid, uid, 'branch_step')
            _v172_delete_quiet(cid, int(getattr(msg, 'message_id', 0) or 0))
            if name:
                _v174_prompt_input(cid, uid, 'branch_keywords', kind='NEW|' + name, message_id=mid)
            return True
        if action == 'branch_keywords':
            cancel_task_input(cid, uid, 'submitted')
            values = [x.strip()[:80] for x in _v174_re.split('[,;\\n]+', raw) if x.strip()]
            if kind.startswith('NEW|'):
                name = kind[4:][:80]
                branches = _v174_settings(cid).setdefault('branches_v212', [])
                branch_id = _v212_secrets.token_hex(4)
                order = max([int(x.get('display_order') or 0) for x in branches if isinstance(x, dict)] or [0]) + 1
                branches.append({'branch_id': branch_id, 'name': name, 'keywords': values[:30], 'enabled': True, 'display_order': order, 'created_at': _v172_iso(), 'updated_at': _v172_iso()})
                _v172_persist(cid, 'v229_branch_create')
            else:
                br = _v212_branch_by_id(cid, kind)
                if br:
                    br['keywords'] = values[:30]
                    br['updated_at'] = _v172_iso()
                    _v172_persist(cid, 'v229_branch_keywords')
            _v172_delete_quiet(cid, int(getattr(msg, 'message_id', 0) or 0))
            body, kb = _v174_menu_text_kb(cid, uid)
            bot.edit_message_text(body, chat_id=cid, message_id=mid, reply_markup=kb)
            return True
        if action == 'branch_rename':
            cancel_task_input(cid, uid, 'submitted')
            br = _v212_branch_by_id(cid, kind)
            if br:
                br['name'] = ' '.join(raw.split())[:80]
                br['updated_at'] = _v172_iso()
                _v172_persist(cid, 'v229_branch_rename')
            _v172_delete_quiet(cid, int(getattr(msg, 'message_id', 0) or 0))
            body, kb = _v212_branch_detail(cid, kind)
            bot.edit_message_text(body, chat_id=cid, message_id=mid, reply_markup=kb)
            return True
        return _V229_PREV_HANDLE_INPUT(msg)
    except Exception as exc:
        try:
            log_error(f'v229 single-window task input: {exc}')
        except Exception:
            pass
        return True
_V229_PREV_CREATE_FROM_MESSAGE = _v228_prev_v174_create_from_message

def _v174_create_from_message(msg, kind: str, text: str=''):
    try:
        cid = int(msg.chat.id)
        if not (tasks_single_window_enabled_v229() and task_dispatcher_enabled(cid)):
            return _V229_PREV_CREATE_FROM_MESSAGE(msg, kind, text)
        src = getattr(msg, 'reply_to_message', None)
        source = src if src is not None else msg
        body = str(text or '').strip() or _v172_reply_text(msg) or str(getattr(msg, 'text', '') or '').strip()
        if not body:
            return None
        skey = _v172_source_key(cid, int(getattr(source, 'message_id', 0) or 0))
        old_uid = _v172_source_root().get(skey)
        old = _v172_task_for_uid(old_uid) if old_uid else None
        if isinstance(old, dict) and (not old.get('deleted')):
            return old
        task = _v172_create_task(cid, 'purchase' if kind == 'purchase' else 'task', body, getattr(msg, 'from_user', None), source_msg=source)
        mid = _v229_task_window_id(cid, 0)
        if not mid:
            mid = int(_v212_open_task_window(cid, int(getattr(getattr(msg, 'from_user', None), 'id', 0) or 0)) or 0)
        _v229_task_set_current(cid, str(task.get('uid') or ''))
        if mid:
            bot.edit_message_text(_v174_compact_text(task), chat_id=cid, message_id=mid, reply_markup=_v174_compact_kb(task, cid, int(getattr(getattr(msg, 'from_user', None), 'id', 0) or 0)))
        return task
    except Exception:
        return _V229_PREV_CREATE_FROM_MESSAGE(msg, kind, text)
_V229_PREV_REFRESH_CARD = _v228_prev_v174_refresh_card

def _v174_refresh_card(task: dict):
    try:
        cid = int(task.get('chat_id', 0) or 0)
        if tasks_single_window_enabled_v229() and task_dispatcher_enabled(cid):
            current = str(_v174_settings(cid).get('single_window_current_uid_v229') or '').upper()
            if current == str(task.get('uid') or '').upper():
                mid = _v229_task_window_id(cid, 0)
                if mid:
                    bot.edit_message_text(_v174_compact_text(task), chat_id=cid, message_id=mid, reply_markup=_v174_compact_kb(task, cid, int(task.get('updated_by', 0) or 0)))
            return
    except Exception:
        pass
    return _V229_PREV_REFRESH_CARD(task)
_V229_PREV_TASK_FOR_REPLY = _v228_prev_v174_task_for_reply

def _v174_task_for_reply(chat_id: int, reply_message_id: int):
    try:
        cid = int(chat_id)
        mid = int(reply_message_id or 0)
        if tasks_single_window_enabled_v229() and mid and (mid == _v229_task_window_id(cid, 0)):
            uid = str(_v174_settings(cid).get('single_window_current_uid_v229') or '').upper()
            task = _v172_task_for_uid(uid) if uid else None
            if isinstance(task, dict) and (not task.get('deleted')):
                return task
    except Exception:
        pass
    return _V229_PREV_TASK_FOR_REPLY(chat_id, reply_message_id)
_V229_PREV_COMMAND_TASKS = _v174_command_tasks

def _v229_command_tasks(msg):
    try:
        cid = int(msg.chat.id)
        uid = int(getattr(getattr(msg, 'from_user', None), 'id', 0) or 0)
        if tasks_single_window_enabled_v229() and task_dispatcher_enabled(cid):
            _v212_open_task_window(cid, uid)
            try:
                _v172_delete_quiet(cid, int(getattr(msg, 'message_id', 0) or 0))
            except Exception:
                pass
            return
    except Exception:
        pass
    return _V229_PREV_COMMAND_TASKS(msg)
try:
    for _row in list(getattr(bot, 'message_handlers', []) or []):
        if isinstance(_row, dict) and _row.get('function') is _V229_PREV_COMMAND_TASKS:
            _row['function'] = _v229_command_tasks
except Exception:
    pass
try:
    WINDOW_MARKER_CONSTANTS.setdefault('v229:tasks_single_window', 'Ф54')
    _v177_legacy_0007_bot_journal('v229_tasks_single_window_ready', int(OWNER_ID or 0), f'enabled={int(tasks_single_window_enabled_v229())}; annotation_source_gate=1')
except Exception:
    pass

# ---------------------------------------------------------------------------
# R17 terminal chat lifecycle coordinator.
# Confirmed terminal Telegram state is propagated once to every feature that can
# otherwise keep scheduling work for a dead chat.  No network request is added to
# normal button/message hot paths; this runs only on a terminal transition or boot
# reconciliation.
# ---------------------------------------------------------------------------
_R17_TERMINAL_CHAT_STATUSES = {'bot_removed', 'migrated', 'archived'}
_R17_TERMINAL_LOCK = _v172_threading.RLock()

def _r17_terminal_status(chat_id: int) -> str:
    try:
        fn = globals().get('_v150_lifecycle')
        if callable(fn):
            return str((fn(int(chat_id)) or {}).get('status') or '')
    except Exception:
        pass
    try:
        fn = globals().get('is_chat_bot_removed')
        if callable(fn) and bool(fn(int(chat_id))):
            return 'bot_removed'
    except Exception:
        pass
    return ''

def _r17_drop_chat_keyed_runtime(root, chat_id: int) -> int:
    """Remove RAM-only rows keyed by (chat_id, user_id) without touching others."""
    if not isinstance(root, dict):
        return 0
    cid = int(chat_id); removed = 0
    for key, value in list(root.items()):
        hit = False
        try:
            if isinstance(key, tuple) and key and int(key[0]) == cid:
                hit = True
            elif isinstance(value, dict) and int(value.get('chat_id', 0) or 0) == cid:
                hit = True
        except Exception:
            hit = False
        if hit:
            root.pop(key, None); removed += 1
    return removed

def _r17_move_chat_keyed_runtime(root, old_chat_id: int, new_chat_id: int) -> int:
    """Move RAM rows keyed by (chat_id, user_id) during Telegram chat migration."""
    if not isinstance(root, dict):
        return 0
    old = int(old_chat_id); new = int(new_chat_id); moved = 0
    for key, value in list(root.items()):
        new_key = None
        try:
            if isinstance(key, tuple) and key and int(key[0]) == old:
                new_key = (new,) + tuple(key[1:])
            elif isinstance(value, dict) and int(value.get('chat_id', 0) or 0) == old:
                value['chat_id'] = new
                moved += 1
                continue
        except Exception:
            new_key = None
        if new_key is not None:
            row = root.pop(key, None)
            if row is not None:
                root[new_key] = row; moved += 1
    return moved

def r17_suspend_terminal_chat_bindings(chat_id: int, reason: str='', *, source: str='lifecycle', persist: bool=True) -> dict:
    """Stop all active work targeting a confirmed terminal chat, preserving audit.

    Forwarding edges are moved to the existing reversible suspended registry.
    Reminder target ids are removed; a reminder with no remaining recipients is
    disabled.  Active task records are retained but marked cancelled and the chat
    task dispatcher is disabled.  This prevents endless scheduler retries while
    preserving enough state for owner diagnostics.
    """
    cid = int(chat_id)
    status = _r17_terminal_status(cid)
    if status not in _R17_TERMINAL_CHAT_STATUSES:
        return {'changed': False, 'chat_id': cid, 'status': status, 'reason': 'not_terminal'}
    report = {'changed': False, 'chat_id': cid, 'status': status, 'forwarding': 0, 'reminders_pruned': 0, 'reminders_disabled': 0, 'tasks_cancelled': 0, 'tasks_migrated': 0, 'runtime_rows_cleared': 0, 'runtime_rows_migrated': 0}
    why = str(reason or status)[:500]
    migrated_to = 0
    if status == 'migrated':
        try:
            migrated_to = int((_v150_lifecycle(cid) or {}).get('migrated_to') or 0)
        except Exception:
            migrated_to = 0
        if migrated_to == cid:
            migrated_to = 0
    report['migrated_to'] = migrated_to
    with _R17_TERMINAL_LOCK:
        # Forwarding: preserve edges in the v199 suspended registry so an explicit
        # successful probe/re-add can restore them, but remove them from live routing.
        try:
            if status == 'migrated' and migrated_to:
                fn = globals().get('reactivate_forward_target_v199')
                if callable(fn) and bool(fn(cid, migrated_to=migrated_to, persist=False)):
                    report['forwarding'] = 1; report['changed'] = True
            else:
                fn = globals().get('suspend_forward_target_v199')
                if callable(fn) and bool(fn(cid, f'R17 terminal {status}: {why}', persist=False)):
                    report['forwarding'] = 1; report['changed'] = True
        except Exception as exc:
            report['forwarding_error'] = f'{type(exc).__name__}: {str(exc)[:180]}'

        # Reminders: physically prune the dead target so due cycles have no stale
        # recipient left to revisit forever.  Keep a bounded audit on each config.
        try:
            for rid, cfg in list(_v149_reminder_all_rows(include_completed=True)):
                if not isinstance(cfg, dict):
                    continue
                selected = _v149_reminder_chat_ids(cfg)
                if cid not in selected:
                    continue
                if status == 'migrated' and migrated_to:
                    replacement = []
                    for value in selected:
                        value = migrated_to if int(value) == cid else int(value)
                        if value not in replacement:
                            replacement.append(value)
                    cfg['chat_ids'] = replacement
                else:
                    cfg['chat_ids'] = [int(x) for x in selected if int(x) != cid]
                if isinstance(cfg.get('last_message_ids'), dict):
                    cfg['last_message_ids'].pop(str(cid), None)
                acked = []
                for raw in cfg.get('delivery_acked_chats_v245') or []:
                    try:
                        value = int(raw)
                        if value != cid and value not in acked:
                            acked.append(value)
                    except Exception:
                        pass
                cfg['delivery_acked_chats_v245'] = acked
                audit = cfg.setdefault('removed_targets_r17', [])
                if isinstance(audit, list):
                    audit.append({'chat_id': cid, 'status': status, 'migrated_to': migrated_to or None, 'at': _v172_iso(), 'reason': why[:240], 'source': str(source or '')[:80]})
                    del audit[:-40]
                cfg['terminal_target_pruned_at_r17'] = _v172_iso()
                try:
                    _reminder_touch(cfg)
                except Exception:
                    cfg['updated_at'] = _v172_iso()
                report['reminders_pruned'] += 1; report['changed'] = True
                if not _v149_reminder_chat_ids(cfg):
                    cfg['enabled'] = False
                    cfg['next_run_at'] = ''
                    cfg['delivery_cycle_v245'] = ''
                    cfg['delivery_acked_chats_v245'] = []
                    cfg['suspended_terminal_chat_r17'] = True
                    cfg['suspended_terminal_chat_reason_r17'] = why[:300]
                    report['reminders_disabled'] += 1
            try:
                state_root = _v149_group_state_root()
                if isinstance(state_root, dict) and state_root.pop(str(cid), None) is not None:
                    report['changed'] = True
            except Exception:
                pass
        except Exception as exc:
            report['reminders_error'] = f'{type(exc).__name__}: {str(exc)[:180]}'

        # Tasks: removed/archived chats cancel unfinished work.  Telegram migration
        # is different: move the dispatcher/task state to the successor chat so a
        # supergroup upgrade is invisible to users instead of destroying tasks.
        try:
            settings = _v172_chat_settings(cid)
            if status == 'migrated' and migrated_to:
                new_settings = _v172_chat_settings(migrated_to)
                old_enabled = bool(settings.get('enabled', False))
                for key, value in list(settings.items()):
                    if key in {'enabled', 'disabled_terminal_chat_r17', 'disabled_terminal_chat_status_r17', 'disabled_terminal_chat_at_r17', 'disabled_terminal_chat_reason_r17'}:
                        continue
                    if key == 'next_number':
                        try:
                            new_settings[key] = max(int(new_settings.get(key) or 1), int(value or 1))
                        except Exception:
                            pass
                    elif key not in new_settings:
                        new_settings[key] = value
                if old_enabled and not bool(new_settings.get('enabled', False)):
                    new_settings['enabled'] = True
                settings['enabled'] = False
                settings['migrated_to_r17'] = migrated_to
                settings['migrated_at_r17'] = _v172_iso()
                for task in _v172_tasks_for_chat(cid, include_deleted=True):
                    if not isinstance(task, dict):
                        continue
                    task['chat_id'] = migrated_to
                    task['updated_at'] = _v172_iso()
                    _v172_history(task, 'chat_migrated_r17', 0, 'system', f'{cid} -> {migrated_to}: {why[:360]}')
                    report['tasks_migrated'] += 1; report['changed'] = True
                try:
                    src_root = _v172_source_root()
                    for key, value in list(src_root.items()):
                        prefix = f'{cid}:'
                        if str(key).startswith(prefix):
                            src_root[f'{migrated_to}:{str(key)[len(prefix):]}'] = value
                            src_root.pop(key, None)
                            report['changed'] = True
                except Exception:
                    pass
                for name in ('_V172_INPUT_WAIT', '_V174_INPUT_WAIT', '_V172_SEARCH_CACHE'):
                    report['runtime_rows_migrated'] += _r17_move_chat_keyed_runtime(globals().get(name), cid, migrated_to)
                report['changed'] = True
            else:
                if bool(settings.get('enabled', False)):
                    settings['enabled'] = False; report['changed'] = True
                old_marker = (settings.get('disabled_terminal_chat_r17'), settings.get('disabled_terminal_chat_status_r17'))
                settings['disabled_terminal_chat_r17'] = True
                settings['disabled_terminal_chat_status_r17'] = status
                settings['disabled_terminal_chat_at_r17'] = _v172_iso()
                settings['disabled_terminal_chat_reason_r17'] = why[:300]
                if old_marker != (True, status):
                    report['changed'] = True
                for task in _v172_tasks_for_chat(cid, include_deleted=True):
                    if not isinstance(task, dict) or bool(task.get('deleted', False)) or _v172_is_complete(task):
                        continue
                    task['status'] = 'cancelled'
                    task['updated_at'] = _v172_iso()
                    task['completed_at'] = task.get('completed_at') or _v172_iso()
                    task['cancel_reason_r17'] = f'terminal_chat:{status}'
                    _v172_history(task, 'cancelled_chat_removed_r17', 0, 'system', f'{status}: {why[:400]}')
                    report['tasks_cancelled'] += 1; report['changed'] = True
                for name in ('_V172_INPUT_WAIT', '_V174_INPUT_WAIT', '_V172_SEARCH_CACHE'):
                    report['runtime_rows_cleared'] += _r17_drop_chat_keyed_runtime(globals().get(name), cid)
        except Exception as exc:
            report['tasks_error'] = f'{type(exc).__name__}: {str(exc)[:180]}'

        if persist and report['changed']:
            try:
                save_data(data, chat_ids=[cid])
            except Exception as exc:
                report['persist_error'] = f'{type(exc).__name__}: {str(exc)[:180]}'
            try:
                schedule_config_backup_for_chats(cid, int(OWNER_ID or 0), delay=0.25)
            except Exception:
                pass
        try:
            bot_journal('r17_terminal_chat_suspended', cid, f"status={status}; forward={report['forwarding']}; reminders={report['reminders_pruned']}; disabled={report['reminders_disabled']}; tasks_cancelled={report['tasks_cancelled']}; tasks_migrated={report['tasks_migrated']}; source={source}; reason={why[:180]}", 'WARN')
        except Exception:
            pass
    return report

def r17_reconcile_terminal_chats_on_boot() -> dict:
    """Repair stale R16 bindings for chats already terminal before R17 boot."""
    total = {'chats': 0, 'changed': 0, 'reminders': 0, 'tasks': 0, 'forwarding': 0}
    try:
        keys = list(((data or {}).get('chats') or {}).keys())
    except Exception:
        keys = []
    for raw in keys:
        try:
            cid = int(raw)
        except Exception:
            continue
        if _r17_terminal_status(cid) not in _R17_TERMINAL_CHAT_STATUSES:
            continue
        total['chats'] += 1
        rep = r17_suspend_terminal_chat_bindings(cid, reason='R17 boot reconciliation', source='r17_boot', persist=False)
        if rep.get('changed'):
            total['changed'] += 1
        total['reminders'] += int(rep.get('reminders_pruned') or 0)
        total['tasks'] += int(rep.get('tasks_cancelled') or 0)
        total['forwarding'] += int(rep.get('forwarding') or 0)
    if total['changed']:
        try:
            save_data(data, root_only=True)
        except Exception:
            pass
    try:
        bot_journal('r17_terminal_boot_reconcile', int(OWNER_ID or 0), f"terminal={total['chats']}; changed={total['changed']}; reminders={total['reminders']}; tasks={total['tasks']}; forwarding={total['forwarding']}")
    except Exception:
        pass
    return total

try:
    _R17_TERMINAL_BOOT_REPORT = r17_reconcile_terminal_chats_on_boot()
except Exception as _r17_boot_exc:
    _R17_TERMINAL_BOOT_REPORT = {'error': f'{type(_r17_boot_exc).__name__}: {str(_r17_boot_exc)[:180]}'}

# v262
