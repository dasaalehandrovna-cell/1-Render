# v267
"""ОЧНИСЬ 12.35 · physical owner: tasks.

Этот файл — единственное физическое место тел функций домена.
Он НЕ запускается отдельно и НЕ импортируется как Python-модуль.
bot.py читает его как каталог исходников и устанавливает нужную стадию в исторической точке runtime.
Последняя версия каждого публичного символа сохраняет обычное имя; старые стадии помечены _legacy_sXXXX_.
"""

# --- tasks:0001 · from 04_messages_features.py:6102 · public _v212_task_reconcile_forward_copy ---
def _v212_task_reconcile_forward_copy(dst_chat_id: int, dst_msg_id: int, source_chat_id: int, source_msg, *, is_edit: bool=False, previous_message_id: int=0):
    fn = globals().get('task_reconcile_source_message')
    if not callable(fn):
        return None
    try:
        body = str(_message_text_for_finance(source_msg) or getattr(source_msg, 'caption', None) or getattr(source_msg, 'text', None) or '')
        sender = getattr(source_msg, 'from_user', None)
        return fn(int(dst_chat_id), int(dst_msg_id), body, original_date=(globals().get('_v172_now')() if callable(globals().get('_v172_now')) else now_local()) if not is_edit else getattr(source_msg, 'date', None), sender_id=int(getattr(sender, 'id', 0) or 0), sender_name=getattr(sender, 'first_name', '') or getattr(sender, 'username', '') or '', sender_is_bot=True, trusted_forwarding_copy=True, origin_chat_id=int(source_chat_id), origin_message_id=int(getattr(source_msg, 'message_id', 0) or 0), is_edit=bool(is_edit), previous_message_id=int(previous_message_id or 0), content_type=str(getattr(source_msg, 'content_type', '') or 'text'))
    except Exception as exc:
        try:
            log_error(f'v212 forwarding task reconcile {dst_chat_id}:{dst_msg_id}: {exc}')
        except Exception:
            pass
        return None

# --- tasks:0002 · from 08_reliability_tasks.py:11944 · public _v172_tasks_root ---
def _v172_tasks_root() -> dict:
    return data.setdefault(V172_TASKS_KEY, {})

# --- tasks:0003 · from 08_reliability_tasks.py:11961 · public task_dispatcher_enabled ---
def task_dispatcher_enabled(chat_id: int) -> bool:
    try:
        return bool(_v172_chat_settings(int(chat_id)).get('enabled', False))
    except Exception:
        return False

# --- tasks:0004 · from 08_reliability_tasks.py:11998 · public _v172_task_for_uid ---
def _v172_task_for_uid(uid: str):
    row = _v172_tasks_root().get(str(uid or '').upper())
    return row if isinstance(row, dict) else None

# --- tasks:0005 · from 08_reliability_tasks.py:12002 · public _v172_tasks_for_chat ---
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

# --- tasks:0006 · from 08_reliability_tasks.py:12051 · public _v172_create_task ---
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

# --- tasks:0007 · from 08_reliability_tasks.py:12193 · public _v172_filter_task ---
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

# --- tasks:0008 · from 08_reliability_tasks.py:12321 · public _v172_group_tasks ---
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

# --- tasks:0009 · from 08_reliability_tasks.py:12437 · public _canon_v172_task_message_input__001 ---
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

# --- tasks:0010 · from 08_reliability_tasks.py:13332 · public _v174_task_by_number ---
def _v174_task_by_number(chat_id: int, number: int):
    for task in _v172_tasks_for_chat(int(chat_id)):
        if int(task.get('number', 0) or 0) == int(number) and (not task.get('deleted')):
            return task
    return None

# --- tasks:0011 · from 08_reliability_tasks.py:13338 · public _v228_prev_v174_task_for_reply ---
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

# --- tasks:0012 · from 08_reliability_tasks.py:13707 · public _v174_command_tasks ---
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

# --- tasks:0013 · from 08_reliability_tasks.py:14073 · public _v212_task_branches ---
def _v212_task_branches(chat_id: int, include_deleted: bool=False) -> list[dict]:
    rows = _v174_settings(int(chat_id)).setdefault('branches_v212', [])
    out = [x for x in rows if isinstance(x, dict) and (include_deleted or not bool(x.get('deleted')))]
    out.sort(key=lambda x: (int(x.get('display_order') or 9999), str(x.get('created_at') or ''), str(x.get('branch_id') or '')))
    return out

# --- tasks:0014 · from 08_reliability_tasks.py:14119 · public _v212_task_hash ---
def _v212_task_hash(text: str, classification) -> str:
    raw = f"{str(text or '')}\n{(classification or {}).get('kind', '')}\n{(classification or {}).get('branch_id', '')}"
    return _v212_hashlib.sha256(raw.encode('utf-8', 'ignore')).hexdigest()[:24]

# --- tasks:0015 · from 08_reliability_tasks.py:14123 · public _v212_task_service_text ---
def _v212_task_service_text(text: str) -> bool:
    low = _v174_normalize(text)
    return low.startswith(('📋 задачи', '📋 диспетчер задач', '📋 задача №', '🛒 покупка №', '⚙️ ключевые слова', 'ф233', '✅ бот запущен'))

# --- tasks:0016 · from 08_reliability_tasks.py:14127 · public _v212_send_task_card ---
def _v212_send_task_card(task: dict, reply_to_message_id: int=0):
    cid = int(task.get('chat_id') or 0)
    try:
        sent = bot.send_message(cid, _v174_compact_text(task), reply_markup=_v174_compact_kb(task, cid, int(task.get('creator_user_id') or 0)), reply_to_message_id=int(reply_to_message_id or 0) or None, allow_sending_without_reply=True)
        task['card_message_id'] = int(getattr(sent, 'message_id', 0) or 0)
        _v172_persist(cid, 'v212_task_card')
    except Exception:
        pass

# --- tasks:0017 · from 08_reliability_tasks.py:14136 · public task_reconcile_source_message ---
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

# --- tasks:0018 · from 08_reliability_tasks.py:14380 · public _v212_open_task_window ---
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

# --- tasks:0019 · from 08_reliability_tasks.py:14637 · public _canon_task_dispatcher_callback_final__001 ---
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

# --- tasks:0020 · from 08_reliability_tasks.py:14745 · public _v213_show_task_home ---
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

# --- tasks:0021 · from 08_reliability_tasks.py:15047 · public _v213_task_input_key ---
def _v213_task_input_key(chat_id: int, user_id: int, legacy: bool=False) -> str:
    return f"v213-input-{('v172' if legacy else 'v174')}:{int(chat_id)}:{int(user_id)}"

# --- tasks:0022 · from 08_reliability_tasks.py:15050 · public _canon_v213_task_input_timeout__001 ---
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

# --- tasks:0023 · from 08_reliability_tasks.py:15521 · public _v213_task_dispatcher_callback_final ---
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

# --- tasks:0024 · from 08_reliability_tasks.py:15550 · public _v214_task_pending_row ---
def _v214_task_pending_row(chat_id: int, user_id: int, legacy: bool=False):
    root = _V172_INPUT_WAIT if legacy else _V174_INPUT_WAIT
    lock = _V172_INPUT_LOCK if legacy else _V174_INPUT_LOCK
    with lock:
        row = root.get((int(chat_id), int(user_id)))
        return dict(row) if isinstance(row, dict) else None

# --- tasks:0025 · from 08_reliability_tasks.py:15557 · public _v214_find_task_pending_by_sid ---
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

# --- tasks:0026 · from 08_reliability_tasks.py:15570 · public _v214_cancel_task_input_rows ---
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

# --- tasks:0027 · from 08_reliability_tasks.py:15606 · public cancel_task_input ---
def cancel_task_input(chat_id: int, user_id: int, reason: str='manual') -> bool:
    """Single public cancellation helper required by v214 task-input navigation contract."""
    return bool(_v214_cancel_task_input_rows(int(chat_id), int(user_id), str(reason or 'manual')))

# --- tasks:0028 · from 08_reliability_tasks.py:15610 · public _v214_task_input_timeout ---
def _v214_task_input_timeout(chat_id: int, user_id: int, sid: str, legacy: bool=False):
    cancelled = _v214_cancel_task_input_rows(int(chat_id), int(user_id), 'timeout', expected_sid=str(sid), legacy=bool(legacy))
    if not cancelled:
        return False
    try:
        send_and_auto_delete(int(chat_id), '⌛ Ввод отменён по таймеру.', 7)
    except Exception:
        pass
    return True

# --- tasks:0029 · from 08_reliability_tasks.py:15620 · public _v214_task_back_callback ---
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

# --- tasks:0030 · from 08_reliability_tasks.py:15636 · public _v214_task_prompt_markup ---
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

# --- tasks:0031 · from 08_reliability_tasks.py:15724 · public _v214_v172_task_message_input ---
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

# --- tasks:0032 · from 08_reliability_tasks.py:15742 · public _v214_task_callback_requires_cancel ---
def _v214_task_callback_requires_cancel(raw: str) -> bool:
    value = str(raw or '')
    if value.startswith('v213:input:cancel:'):
        return False
    if value in {'nav_prev', 'info_close', 'aux_close'} or value.endswith(':back_main'):
        return True
    return value.startswith(('v174:td:', 'v172:task:'))

# --- tasks:0033 · from 08_reliability_tasks.py:16484 · public _v217_task_home_kb ---
def _v217_task_home_kb(chat_id: int, user_id: int=0):
    text, kb = _V217_PREV_TASK_HOME_KB(int(chat_id), int(user_id or 0))
    try:
        if _v215_circle_business_chat(int(chat_id)):
            _v217_insert_before_nav(kb, IB('☰ Меню', callback_data='v217:contour:menu'))
    except Exception:
        pass
    return (text, kb)

# --- tasks:0034 · from 08_reliability_tasks.py:17332 · public _v219_task_message_text ---
def _v219_task_message_text(msg) -> str:
    return str(getattr(msg, 'text', None) or getattr(msg, 'caption', None) or '').strip()

# --- tasks:0035 · from 08_reliability_tasks.py:17335 · public _v219_task_pending_for_sender ---
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

# --- tasks:0036 · from 08_reliability_tasks.py:17380 · public _v219_task_ingest_message ---
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

# --- tasks:0037 · from 08_reliability_tasks.py:17418 · public _v219_task_auto_process ---
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

# --- tasks:0038 · from 08_reliability_tasks.py:17431 · public _v219_task_text_prompt_keyboard ---
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

# --- tasks:0039 · from 08_reliability_tasks.py:17458 · public _v219_task_prompt_input ---
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

# --- tasks:0040 · from 08_reliability_tasks.py:17497 · public _v219_task_handle_own_input ---
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

# --- tasks:0041 · from 08_reliability_tasks.py:17558 · public _v219_task_dispatcher_callback_final ---
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

# --- tasks:0042 · from 08_reliability_tasks.py:17662 · public _v220_task_menu_text_kb ---
def _v220_task_menu_text_kb(chat_id: int, user_id: int=0):
    text, kb = _V220_PREV_TASK_MENU(int(chat_id), int(user_id or 0))
    return (text, _v220_remove_contour_menu_button(kb, int(chat_id)))

# --- tasks:0043 · from 08_reliability_tasks.py:19235 · public tasks_single_window_enabled_v229 ---
def tasks_single_window_enabled_v229() -> bool:
    gs = data.setdefault('_global_settings', {})
    if V229_TASK_SINGLE_WINDOW_KEY not in gs:
        gs[V229_TASK_SINGLE_WINDOW_KEY] = True
    return bool(gs.get(V229_TASK_SINGLE_WINDOW_KEY, True))

# --- tasks:0044 · from 08_reliability_tasks.py:19241 · public set_tasks_single_window_v229 ---
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

# --- tasks:0045 · from 08_reliability_tasks.py:19287 · public _v229_task_window_id ---
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

# --- tasks:0046 · from 08_reliability_tasks.py:19306 · public _v229_task_set_current ---
def _v229_task_set_current(chat_id: int, task_uid: str='') -> None:
    try:
        s = _v174_settings(int(chat_id))
        s['single_window_current_uid_v229'] = str(task_uid or '').upper()
    except Exception:
        pass

# --- tasks:0047 · from 08_reliability_tasks.py:19313 · public _v229_task_restore ---
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

# --- tasks:0048 · from 08_reliability_tasks.py:19401 · public _v229_task_input_timeout ---
def _v229_task_input_timeout(chat_id: int, user_id: int, sid: str, legacy: bool=False):
    row = _v214_task_pending_row(int(chat_id), int(user_id), bool(legacy))
    result = _V229_PREV_TASK_TIMEOUT(chat_id, user_id, sid, legacy)
    if result and isinstance(row, dict) and row.get('single_window_v229'):
        _v229_task_restore(int(chat_id), int(row.get('message_id') or 0), int(user_id), str(row.get('task_uid') or ''))
    return result

# --- tasks:0049 · from 08_reliability_tasks.py:19550 · public _v174_task_for_reply ---
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

# --- tasks:0050 · from 08_reliability_tasks.py:19564 · public _v229_command_tasks ---
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

# v267
