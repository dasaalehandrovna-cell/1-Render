# v262
def build_forward_root_menu(day_key: str):
    """Корневое меню пересылки: старый режим или новый визуальный режим пары A/B."""
    if forward_menu_new_style_enabled():
        return build_forward_new_menu(day_key)
    return build_forward_source_menu(day_key)

def _v177_legacy_0180_collect_forward_picker_items(include_owner: bool=True, include_removed: bool=False):
    known = collect_forward_menu_chats()
    items = []
    owner_item = None
    for cid, ch in sorted(known.items(), key=lambda x: (x[1].get('title') or '').lower()):
        try:
            int_cid = int(cid)
        except Exception:
            continue
        title = ch.get('title') or f'Чат {cid}'
        if OWNER_ID and str(int_cid) == str(OWNER_ID):
            owner_item = (int_cid, title)
        else:
            if not include_removed and is_chat_bot_removed(int_cid):
                continue
            items.append((int_cid, title))
    if include_owner and OWNER_ID:
        try:
            owner_id = int(OWNER_ID)
            if owner_item is None:
                owner_item = (owner_id, get_chat_display_name(owner_id))
        except Exception:
            owner_item = None
    return (items, owner_item)
try:
    _v177_legacy_0180_collect_forward_picker_items.__name__ = '_collect_forward_picker_items'
except Exception:
    pass

def _chat_description_origin_back(origin: str, day_key: str) -> str:
    return f'd:{day_key}:forward_finmode_menu' if str(origin) == 'finmode' else f'd:{day_key}:forward_menu'

def _v177_legacy_0183_build_chat_description_menu(viewer_chat_id: int, origin: str, day_key: str):
    kb = types.InlineKeyboardMarkup(row_width=2)
    buttons = []
    for cid in collect_all_known_chat_ids(include_owner=True):
        try:
            if is_chat_bot_removed(int(cid)):
                continue
        except Exception:
            pass
        buttons.append(IB(chat_button_title(int(cid)), callback_data=f'chat_desc_open:{origin}:{int(cid)}'))
    add_buttons_in_rows(kb, buttons, 2)
    kb.row(IB('🔙 Назад', callback_data=_chat_description_origin_back(origin, day_key)))
    kb.row(IB('⬅️ Назад осн. окно', callback_data=f'd:{day_key}:back_main'))
    return kb
try:
    _v177_legacy_0183_build_chat_description_menu.__name__ = 'build_chat_description_menu'
except Exception:
    pass

def build_chat_description_menu_text() -> str:
    return 'ℹ️ Описание чатов\n\nВыберите чат. Бот покажет карточку Telegram, количество участников, администраторов и пользователей, которых он реально видел в сообщениях.'

def _chat_user_line(user, prefix: str='') -> str:
    try:
        uid = int(getattr(user, 'id', 0) or 0)
        first = str(getattr(user, 'first_name', '') or '')
        last = str(getattr(user, 'last_name', '') or '')
        name = (first + ' ' + last).strip() or 'Без имени'
        username = str(getattr(user, 'username', '') or '').lstrip('@')
        premium = 'Premium' if bool(getattr(user, 'is_premium', False)) else 'обычный'
        bot_mark = 'бот' if bool(getattr(user, 'is_bot', False)) else premium
        return f'{prefix}{name}' + (f' (@{username})' if username else '') + f' — ID {uid}; {bot_mark}'
    except Exception:
        return f'{prefix}не удалось прочитать пользователя'

def _known_user_line(row: dict, prefix: str='') -> str:
    row = row or {}
    name = (str(row.get('first_name') or '') + ' ' + str(row.get('last_name') or '')).strip() or 'Без имени'
    username = str(row.get('username') or '').lstrip('@')
    kind = 'бот' if row.get('is_bot') else 'Premium' if row.get('is_premium') else 'обычный'
    return f'{prefix}{name}' + (f' (@{username})' if username else '') + f" — ID {row.get('id')}; {kind}; видел: {row.get('last_seen') or 'неизвестно'}"
_CHAT_DESCRIPTION_CACHE_LOCK = threading.RLock()
_CHAT_DESCRIPTION_CACHE = {}
_CHAT_DESCRIPTION_CACHE_SECONDS = 300.0

def _split_chat_description_pages(text: str, limit: int=3300):
    lines = str(text or '').splitlines()
    pages, current, size = ([], [], 0)
    for line in lines:
        chunk = str(line)
        pieces = [chunk[i:i + limit] for i in range(0, len(chunk), limit)] or ['']
        for piece in pieces:
            add = len(piece) + 1
            if current and size + add > limit:
                pages.append('\n'.join(current))
                current, size = ([], 0)
            current.append(piece)
            size += add
    if current or not pages:
        pages.append('\n'.join(current))
    total = len(pages)
    return [f'{page}\n\nСтраница {idx}/{total}' for idx, page in enumerate(pages, 1)]

def get_chat_description_pages(target_chat_id: int, refresh: bool=False):
    key = int(target_chat_id)
    now_ts = time.time()
    if not refresh:
        with _CHAT_DESCRIPTION_CACHE_LOCK:
            cached = _CHAT_DESCRIPTION_CACHE.get(key)
            if cached and now_ts < float(cached.get('expires') or 0):
                return list(cached.get('pages') or [])
    text = build_chat_description_detail(key)
    pages = _split_chat_description_pages(text)
    with _CHAT_DESCRIPTION_CACHE_LOCK:
        _CHAT_DESCRIPTION_CACHE[key] = {'pages': list(pages), 'expires': now_ts + _CHAT_DESCRIPTION_CACHE_SECONDS}
    return pages

def build_chat_description_detail(target_chat_id: int) -> str:
    target_chat_id = int(target_chat_id)
    store = get_chat_store(target_chat_id)
    info = store.get('info') or {}
    chat_obj = None
    errors = []
    try:
        chat_obj = _tg_call_retry(bot.get_chat, target_chat_id, attempts=2, purpose='chat_description_get_chat')
        update_chat_info_from_chat_object(chat_obj)
    except Exception as exc:
        errors.append(f'getChat: {str(exc)[:180]}')

    def attr(name, default=None):
        return getattr(chat_obj, name, default) if chat_obj is not None else info.get(name, default)
    title = str(attr('title', '') or '').strip()
    first = str(attr('first_name', '') or '').strip()
    last = str(attr('last_name', '') or '').strip()
    if not title:
        title = (first + ' ' + last).strip() or get_chat_display_name(target_chat_id)
    username = str(attr('username', '') or '').strip().lstrip('@')
    chat_type = str(attr('type', info.get('type') or 'unknown') or 'unknown')
    member_count = None
    try:
        fn = getattr(bot, 'get_chat_member_count', None) or getattr(bot, 'get_chat_members_count', None)
        if fn:
            member_count = int(_tg_call_retry(fn, target_chat_id, attempts=2, purpose='chat_description_member_count'))
    except Exception as exc:
        errors.append(f'memberCount: {str(exc)[:160]}')
    admins = []
    if chat_type in {'group', 'supergroup', 'channel'}:
        try:
            admins = list(_tg_call_retry(bot.get_chat_administrators, target_chat_id, attempts=2, purpose='chat_description_admins') or [])
        except Exception as exc:
            errors.append(f'administrators: {str(exc)[:160]}')
    lines = ['ℹ️ Полное описание чата', '', f'Название: {title}', f'ID чата: {target_chat_id}', f'Тип: {chat_type}', f'Username: @{username}' if username else 'Username: нет']
    if member_count is not None:
        lines.append(f'Количество участников: {member_count}')
    for label, name in (('Описание', 'description'), ('Bio', 'bio'), ('Ссылка-приглашение', 'invite_link'), ('Связанный чат', 'linked_chat_id'), ('Автоудаление, сек', 'message_auto_delete_time'), ('Медленный режим, сек', 'slow_mode_delay')):
        value = attr(name, None)
        if value not in (None, '', 0, False):
            lines.append(f'{label}: {value}')
    lines.extend([f"Форум: {('да' if bool(attr('is_forum', False)) else 'нет')}", f"Защищённый контент: {('да' if bool(attr('has_protected_content', False)) else 'нет')}", f"Бот удалён/нет доступа: {('да' if is_chat_bot_removed(target_chat_id) else 'нет')}", f"Финансовый режим: {('включён' if is_finance_mode(target_chat_id) else 'выключен')}", f"Скрытые финансы: {('включены' if is_hidden_finance_mode(target_chat_id) else 'выключены')}", ''])
    if chat_type == 'private':
        try:
            member = _tg_call_retry(bot.get_chat_member, target_chat_id, target_chat_id, attempts=1, purpose='chat_description_private_member')
            user = getattr(member, 'user', None)
            if user:
                lines.append('Пользователь:')
                lines.append(_chat_user_line(user, '• '))
        except Exception:
            known = list((store.get('known_users') or {}).values())
            if known:
                lines.append('Пользователь, которого видел бот:')
                lines.append(_known_user_line(known[-1], '• '))
    else:
        lines.append(f'Администраторы: {len(admins)}')
        for member in admins[:100]:
            user = getattr(member, 'user', None)
            status = str(getattr(member, 'status', '') or '')
            custom_title = str(getattr(member, 'custom_title', '') or '')
            suffix = f'; статус {status}' + (f'; должность {custom_title}' if custom_title else '')
            lines.append((_chat_user_line(user, '• ') if user else '• неизвестный администратор') + suffix)
        known_users = list((store.get('known_users') or {}).values())
        known_users.sort(key=lambda row: float((row or {}).get('last_seen_ts') or 0), reverse=True)
        admin_ids = {int(getattr(getattr(m, 'user', None), 'id', 0) or 0) for m in admins}
        known_non_admin = [row for row in known_users if int((row or {}).get('id') or 0) not in admin_ids]
        lines.extend(['', f'Другие пользователи, которых видел бот: {len(known_non_admin)}'])
        for row in known_non_admin[:150]:
            lines.append(_known_user_line(row, '• '))
        lines.extend(['', 'Важно: обычный Telegram Bot API не отдаёт боту полный список всех участников группы. Поэтому здесь показаны точное количество, администраторы и накопленный список пользователей, писавших после включения этого учёта.'])
    if errors:
        lines.extend(['', 'Ограничения/ошибки получения:'] + [f'• {e}' for e in errors])
    return '\n'.join(lines)

def build_chat_description_detail_keyboard(viewer_chat_id: int, origin: str, day_key: str, target_chat_id: int=0, page: int=0, total_pages: int=1):
    kb = types.InlineKeyboardMarkup(row_width=2)
    target_chat_id = int(target_chat_id or 0)
    page = max(0, int(page or 0))
    total_pages = max(1, int(total_pages or 1))
    if total_pages > 1 and target_chat_id:
        nav = []
        if page > 0:
            nav.append(IB('⬅️ Предыдущая', callback_data=f'chat_desc_page:{origin}:{target_chat_id}:{page - 1}'))
        nav.append(IB(f'{page + 1}/{total_pages}', callback_data='none'))
        if page + 1 < total_pages:
            nav.append(IB('Следующая ➡️', callback_data=f'chat_desc_page:{origin}:{target_chat_id}:{page + 1}'))
        kb.row(*nav)
    kb.row(IB('🔄 Обновить данные', callback_data=f'chat_desc_open:{origin}:{target_chat_id}' if target_chat_id else f'chat_desc_menu:{origin}'))
    kb.row(IB('🔙 Назад к чатам', callback_data=f'chat_desc_menu:{origin}'))
    kb.row(IB('🔙 Назад в предыдущее меню', callback_data=_chat_description_origin_back(origin, day_key)))
    kb.row(IB('⬅️ Назад осн. окно', callback_data=f'd:{day_key}:back_main'))
    return kb

def _v177_legacy_0185_build_forward_source_menu(day_key: str | None=None):
    if forward_menu_new_style_enabled():
        return build_forward_new_menu(day_key)
    kb = types.InlineKeyboardMarkup(row_width=3)
    if not OWNER_ID:
        return kb
    items, owner_item = _collect_forward_picker_items(include_owner=True)
    buttons = [IB(chat_button_title(cid, title), callback_data=f'fw_src:{cid}') for cid, title in items]
    add_buttons_in_rows(kb, buttons, 2)
    if owner_item:
        kb.row(IB(chat_button_title(owner_item[0], owner_item[1]), callback_data=f'fw_src:{owner_item[0]}'))
    kb.row(IB('ℹ️ Описание чатов', callback_data='chat_desc_menu:forward'))
    kb.row(IB('📡 Проверить чаты', callback_data='fw_probe_all'), IB('🗑 Удалённые', callback_data='fw_removed_list'))
    if day_key:
        kb.row(IB('🔙 Назад', callback_data=f'd:{day_key}:back_main'))
    else:
        kb.row(IB('🔙 Назад', callback_data='fw_back_root'))
    return kb
try:
    _v177_legacy_0185_build_forward_source_menu.__name__ = 'build_forward_source_menu'
except Exception:
    pass

def _v177_legacy_0186_build_forward_target_menu(src_id: int):
    kb = types.InlineKeyboardMarkup()
    if not OWNER_ID:
        return kb
    items, owner_item = _collect_forward_picker_items(include_owner=True)
    buttons = []
    for int_cid, title in items:
        if int_cid == src_id:
            continue
        buttons.append(IB(chat_button_title(int_cid, title), callback_data=f'fw_tgt:{src_id}:{int_cid}'))
    add_buttons_in_rows(kb, buttons, 2)
    if owner_item and owner_item[0] != src_id:
        kb.row(IB(chat_button_title(owner_item[0], owner_item[1]), callback_data=f'fw_tgt:{src_id}:{owner_item[0]}'))
    kb.row(IB('🔙 Назад', callback_data='fw_back_src'))
    return kb
try:
    _v177_legacy_0186_build_forward_target_menu.__name__ = 'build_forward_target_menu'
except Exception:
    pass

def _forward_pair_key(A: int, B: int) -> str:
    return f'{int(A)}:{int(B)}'

def _forward_pair_undirected_key(A: int, B: int) -> tuple[int, int]:
    A = int(A)
    B = int(B)
    return (A, B) if A <= B else (B, A)

def _v177_legacy_0187_remember_forward_pair(A: int, B: int):
    """Сохраняет порядок создания пар для нового В22. Старую логику пересылки не трогает."""
    try:
        A, B = (int(A), int(B))
        if A == B:
            return
        key = _forward_pair_key(A, B)
        rev = _forward_pair_key(B, A)
        order = data.setdefault('forward_pair_order', [])
        if not isinstance(order, list):
            order = []
            data['forward_pair_order'] = order
        if key not in order and rev not in order:
            order.append(key)
            save_data(data)
    except Exception as e:
        log_error(f'_remember_forward_pair({A},{B}): {e}')
try:
    _v177_legacy_0187_remember_forward_pair.__name__ = '_remember_forward_pair'
except Exception:
    pass

def _v177_legacy_0188_forget_forward_pair_if_empty(A: int, B: int):
    """Убирает пару из порядка, только если уже нет ни пересылки, ни 💰 финучёта в обе стороны."""
    try:
        A, B = (int(A), int(B))
        arrow, fin, ab_on, ba_on, ab_fin, ba_fin = _forward_pair_icons(A, B)
        if ab_on or ba_on or ab_fin or ba_fin:
            return
        key = _forward_pair_key(A, B)
        rev = _forward_pair_key(B, A)
        order = data.setdefault('forward_pair_order', [])
        if isinstance(order, list) and (key in order or rev in order):
            data['forward_pair_order'] = [x for x in order if x not in {key, rev}]
            save_data(data)
    except Exception as e:
        log_error(f'_forget_forward_pair_if_empty({A},{B}): {e}')
try:
    _v177_legacy_0188_forget_forward_pair_if_empty.__name__ = '_forget_forward_pair_if_empty'
except Exception:
    pass

def _forward_pair_sort_key(pair):
    try:
        order = data.get('forward_pair_order', []) or []
        key = _forward_pair_key(pair[0], pair[1])
        rev = _forward_pair_key(pair[1], pair[0])
        if key in order:
            return (0, order.index(key))
        if rev in order:
            return (0, order.index(rev))
        a, b = pair
        return (1, get_chat_display_name(int(a)).lower(), get_chat_display_name(int(b)).lower(), int(a), int(b))
    except Exception:
        return (9, str(pair))

def _sorted_forward_pair(a: int, b: int):
    """Старый helper оставлен для совместимости. Новый В22 порядок выбора не сортирует."""
    a = int(a)
    b = int(b)
    ka = (get_chat_display_name(a).lower(), a)
    kb = (get_chat_display_name(b).lower(), b)
    return (a, b) if ka <= kb else (b, a)

def _v177_legacy_0189_collect_forward_pairs_for_menu() -> list[tuple[int, int]]:
    """Все пары, где есть пересылка или 💰 финучёт пересылки. Порядок пары берём из создания/первого обнаружения."""
    relation_pairs = []
    seen = set()
    fr = data.get('forward_rules', {}) or {}
    ff = data.get('forward_finance', {}) or {}

    def _add_pair(a, b):
        try:
            a = int(a)
            b = int(b)
        except Exception:
            return
        if a == b:
            return
        uk = _forward_pair_undirected_key(a, b)
        if uk in seen:
            return
        seen.add(uk)
        relation_pairs.append((a, b))
    order = data.get('forward_pair_order', []) or []
    if isinstance(order, list):
        for key in order:
            try:
                a_s, b_s = str(key).split(':', 1)
                a, b = (int(a_s), int(b_s))
            except Exception:
                continue
            arrow, fin, ab_on, ba_on, ab_fin, ba_fin = _forward_pair_icons(a, b)
            if ab_on or ba_on or ab_fin or ba_fin:
                _add_pair(a, b)
    for src, dsts in fr.items():
        for dst in (dsts or {}).keys():
            _add_pair(src, dst)
    for src, dsts in ff.items():
        for dst, enabled in (dsts or {}).items():
            if enabled:
                _add_pair(src, dst)
    try:
        order = data.setdefault('forward_pair_order', [])
        if not isinstance(order, list):
            order = []
            data['forward_pair_order'] = order
        changed = False
        for A, B in relation_pairs:
            key = _forward_pair_key(A, B)
            rev = _forward_pair_key(B, A)
            if key not in order and rev not in order:
                order.append(key)
                changed = True
        if changed:
            save_data(data)
    except Exception:
        pass
    return sorted(relation_pairs, key=_forward_pair_sort_key)
try:
    _v177_legacy_0189_collect_forward_pairs_for_menu.__name__ = 'collect_forward_pairs_for_menu'
except Exception:
    pass

def _forward_pair_icons(A: int, B: int):
    fr = data.get('forward_rules', {}) or {}
    ff = data.get('forward_finance', {}) or {}
    ab_on = str(B) in (fr.get(str(A), {}) or {})
    ba_on = str(A) in (fr.get(str(B), {}) or {})
    ab_fin = bool((ff.get(str(A), {}) or {}).get(str(B), False))
    ba_fin = bool((ff.get(str(B), {}) or {}).get(str(A), False))
    return (_forward_arrow_icon(ab_on, ba_on), _forward_fin_icon(ab_fin, ba_fin), ab_on, ba_on, ab_fin, ba_fin)

def _forward_new_pair_buttons(A: int, B: int):
    """Две кнопки пары сверху в новом В22.

    По уточнённому ТЗ:
    • кнопка Чата A сверху остаётся выбором этого чата как нового Чата A;
    • кнопка Чата B сверху открывает настройки именно этой пары и помечается 🛠️ перед именем;
    • ниже разделителя Чаты A из готовых пар не дублируются, чтобы список не захламлялся.
    """
    arrow, fin, *_ = _forward_pair_icons(A, B)
    return (IB(f'{chat_button_title(A)} ({arrow})', callback_data=f'fw_new_src:{A}'), IB(f'({fin}) 🛠️ {chat_button_title(B)}', callback_data=f'fw_new_pair:{A}:{B}'))

def _forward_new_toggle_label(enabled: bool, icon: str) -> str:
    return ('✅' if enabled else '⬜') + icon

def _visible_forward_items_for_new_menu(include_owner: bool=True):
    items, owner_item = _collect_forward_picker_items(include_owner=include_owner)
    all_items = list(items)
    if owner_item:
        all_items.append(owner_item)
    visible = []
    for cid, title in all_items:
        try:
            if is_chat_bot_removed(int(cid)):
                continue
        except Exception:
            pass
        visible.append((int(cid), title))
    return visible

def build_forward_new_text(A: int | None=None, B: int | None=None) -> str:
    """В22 новый режим: пары сверху, выбор A/B и настройка шести кнопок."""
    lines = ['🔁 Пересылка / В22', 'Режим: по-новому', '']
    if A and B:
        arrow, fin, *_ = _forward_pair_icons(A, B)
        lines.append(f'Чат А: {get_chat_display_name(A)} ({arrow})')
        lines.append(f'Чат Б: ({fin}) {get_chat_display_name(B)}')
        lines.append('Ниже выбери направление пересылки и 💰 финучёт.')
    elif A:
        lines.append(f'Чат А выбран: {get_chat_display_name(A)}')
        lines.append('Теперь выбери Чат Б. Остальные чаты остаются ниже по 2 кнопки в ряд.')
    else:
        lines.append('Сверху пары со связями. Ниже — все доступные чаты. Любой чат можно снова выбрать как Чат А.')
    return '\n'.join(lines)

def _v177_legacy_0193_build_forward_new_menu(day_key: str | None=None, A: int | None=None, B: int | None=None):
    """
    Новый В22 по уточнённому ТЗ:
    • старт: пары сверху по 2 кнопки (A слева, B справа), потом пустой разделитель, потом свободные чаты по 2 кнопки;
    • выбран A: кнопка Чат А сверху, остальные чаты остаются ниже по 2 кнопки;
    • выбран B: сверху Чат А / Чат Б, ниже 6 кнопок режимов, ниже кнопка возврата к выбору чатов.
    """
    kb = types.InlineKeyboardMarkup(row_width=2)
    if not OWNER_ID:
        return kb
    visible_items = _visible_forward_items_for_new_menu(include_owner=True)
    pair_rows = collect_forward_pairs_for_menu()
    if A and B:
        A, B = (int(A), int(B))
        arrow, fin, ab_on, ba_on, ab_fin, ba_fin = _forward_pair_icons(A, B)
        kb.row(IB(f'Чат А: {chat_button_title(A)}', callback_data=f'fw_new_pair:{A}:{B}'), IB(f'Чат Б: {chat_button_title(B)}', callback_data=f'fw_new_pair:{A}:{B}'))
        kb.row(IB(_forward_new_toggle_label(ba_on, '⏪️'), callback_data=f'fw_new_mode:{A}:{B}:from'), IB(_forward_new_toggle_label(ab_on, '⏩️'), callback_data=f'fw_new_mode:{A}:{B}:to'), IB(_forward_new_toggle_label(ab_on and ba_on, '🔄'), callback_data=f'fw_new_mode:{A}:{B}:two'), IB(_forward_new_toggle_label(ba_fin, '◀️'), callback_data=f'fw_new_fin:{A}:{B}:ba'), IB(_forward_new_toggle_label(ab_fin, '▶️'), callback_data=f'fw_new_fin:{A}:{B}:ab'), IB('❌', callback_data=f'fw_new_clear:{A}:{B}'))
        kb.row(IB('🔙 Назад в окно выбора чатов', callback_data='fw_new_back_src'))
        return kb
    if A:
        A = int(A)
        kb.row(IB(f'Чат А: {chat_button_title(A)}', callback_data=f'fw_new_src:{A}'))
        buttons = []
        for cid, title in visible_items:
            if int(cid) == int(A):
                continue
            buttons.append(IB(f'Чат Б: {chat_button_title(cid, title)}', callback_data=f'fw_new_tgt:{A}:{int(cid)}'))
        if buttons:
            add_buttons_in_rows(kb, buttons, 2)
        else:
            kb.row(IB('Нет чатов для выбора Чата Б', callback_data='none'))
        kb.row(IB('🔙 Назад в окно выбора чатов', callback_data='fw_new_back_src'))
        return kb
    shown_pairs = 0
    top_pair_a_ids = set()
    for A0, B0 in pair_rows:
        try:
            if is_chat_bot_removed(A0) or is_chat_bot_removed(B0):
                continue
        except Exception:
            pass
        top_pair_a_ids.add(int(A0))
        left_btn, right_btn = _forward_new_pair_buttons(A0, B0)
        kb.row(left_btn, right_btn)
        shown_pairs += 1
    chat_buttons = []
    for cid, title in visible_items:
        if int(cid) in top_pair_a_ids:
            continue
        chat_buttons.append(IB(chat_button_title(cid, title), callback_data=f'fw_new_src:{cid}'))
    if shown_pairs and chat_buttons:
        kb.row(IB('⠀', callback_data='none'))
    if chat_buttons:
        add_buttons_in_rows(kb, chat_buttons, 2)
    elif not shown_pairs:
        kb.row(IB('Нет доступных чатов', callback_data='none'))
    kb.row(IB('ℹ️ Описание чатов', callback_data='chat_desc_menu:forward'))
    kb.row(IB('📡 Проверить чаты', callback_data='fw_probe_all'), IB('🗑 Удалённые', callback_data='fw_removed_list'))
    if day_key:
        kb.row(IB('🔙 Назад', callback_data=f'd:{day_key}:back_main'))
    else:
        kb.row(IB('🔙 Назад', callback_data='fw_back_root'))
    return kb
try:
    _v177_legacy_0193_build_forward_new_menu.__name__ = 'build_forward_new_menu'
except Exception:
    pass

def _v177_legacy_0194_build_forward_menu_text_for_current_mode(title: str | None=None, A: int | None=None, B: int | None=None) -> str:
    if forward_menu_new_style_enabled():
        return build_forward_new_text(A, B)
    return build_forward_status_text(title or 'Пересылка:\nВыберите чат A:')
try:
    _v177_legacy_0194_build_forward_menu_text_for_current_mode.__name__ = 'build_forward_menu_text_for_current_mode'
except Exception:
    pass

def _v177_legacy_0195_build_forward_menu_keyboard_for_current_mode(day_key: str | None=None, A: int | None=None, B: int | None=None):
    if forward_menu_new_style_enabled():
        return build_forward_new_menu(day_key, A, B)
    if A and B:
        return build_forward_mode_menu(A, B)
    if A:
        return build_forward_target_menu(A)
    return build_forward_source_menu(day_key)
try:
    _v177_legacy_0195_build_forward_menu_keyboard_for_current_mode.__name__ = 'build_forward_menu_keyboard_for_current_mode'
except Exception:
    pass
# v262
