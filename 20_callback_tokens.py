# v262
_short_callback_lock = threading.RLock()
_short_callback_store = {}
_short_callback_counter = 0
SHORT_CALLBACK_TTL_SECONDS = 6 * 60 * 60
SHORT_CALLBACK_LOCAL_HOT_MAX_V248 = max(512, min(20000, int(os.getenv('SHORT_CALLBACK_LOCAL_HOT_MAX', '4096') or '4096')))


# R24: keyboard construction is RAM-only. Redis is optional restart continuity and
# is mirrored as a background batch. No callback waits for Redis and no Redis result
# changes the live button semantics.
_SHORT_CALLBACK_MIRROR_LOCK_R24 = threading.RLock()
_SHORT_CALLBACK_MIRROR_PENDING_R24 = {}
_SHORT_CALLBACK_MIRROR_SCHEDULED_R24 = False
_SHORT_CALLBACK_MIRROR_BATCH_R24 = 160
_SHORT_CALLBACK_MIRROR_MAX_PENDING_R24 = 8000

def _flush_short_callback_mirrors_r24():
    global _SHORT_CALLBACK_MIRROR_SCHEDULED_R24
    while True:
        with _SHORT_CALLBACK_MIRROR_LOCK_R24:
            if not _SHORT_CALLBACK_MIRROR_PENDING_R24:
                _SHORT_CALLBACK_MIRROR_SCHEDULED_R24 = False
                return
            keys = list(_SHORT_CALLBACK_MIRROR_PENDING_R24.keys())[:_SHORT_CALLBACK_MIRROR_BATCH_R24]
            batch = [(k, _SHORT_CALLBACK_MIRROR_PENDING_R24.pop(k)) for k in keys]
        try:
            if not bool(globals().get('key_value_configured_v248', lambda: False)()):
                with _SHORT_CALLBACK_MIRROR_LOCK_R24:
                    _SHORT_CALLBACK_MIRROR_SCHEDULED_R24 = False
                return
            client = globals().get('KEY_VALUE_CLIENT_V248')
            key_fn = globals().get('_kv_key_v248')
            if client is None or not callable(key_fn):
                raise RuntimeError('KV client unavailable')
            commands = [('SET', key_fn(f'cb:{token}'), str(value), 'EX', int(SHORT_CALLBACK_TTL_SECONDS)) for token, value in batch]
            client.pipeline(commands)
        except Exception:
            # RAM remains authoritative. Retry later, never in the callback thread.
            with _SHORT_CALLBACK_MIRROR_LOCK_R24:
                for token, value in batch:
                    if len(_SHORT_CALLBACK_MIRROR_PENDING_R24) < _SHORT_CALLBACK_MIRROR_MAX_PENDING_R24:
                        _SHORT_CALLBACK_MIRROR_PENDING_R24[token] = value
                _SHORT_CALLBACK_MIRROR_SCHEDULED_R24 = False
            try:
                sched = globals().get('DELAYED_SCHEDULER')
                if sched is not None:
                    sched.schedule('r24-short-callback-mirror-retry', 2.0, _schedule_short_callback_mirror_flush_r24)
            except Exception:
                pass
            return

def _schedule_short_callback_mirror_flush_r24():
    global _SHORT_CALLBACK_MIRROR_SCHEDULED_R24
    with _SHORT_CALLBACK_MIRROR_LOCK_R24:
        if _SHORT_CALLBACK_MIRROR_SCHEDULED_R24 or not _SHORT_CALLBACK_MIRROR_PENDING_R24:
            return True
        _SHORT_CALLBACK_MIRROR_SCHEDULED_R24 = True
    try:
        pool = globals().get('GENERAL_TASK_POOL') or globals().get('UI_CLEANUP_TASK_POOL')
        if pool is not None and hasattr(pool, 'submit_unique'):
            if pool.submit_unique('r24-short-callback-mirror', _flush_short_callback_mirrors_r24):
                return True
    except Exception:
        pass
    with _SHORT_CALLBACK_MIRROR_LOCK_R24:
        _SHORT_CALLBACK_MIRROR_SCHEDULED_R24 = False
    return False

def _queue_short_callback_mirror_r24(token: str, data_str: str) -> bool:
    with _SHORT_CALLBACK_MIRROR_LOCK_R24:
        if len(_SHORT_CALLBACK_MIRROR_PENDING_R24) >= _SHORT_CALLBACK_MIRROR_MAX_PENDING_R24:
            try: _SHORT_CALLBACK_MIRROR_PENDING_R24.pop(next(iter(_SHORT_CALLBACK_MIRROR_PENDING_R24)), None)
            except Exception: pass
        _SHORT_CALLBACK_MIRROR_PENDING_R24[str(token)] = str(data_str)
    return _schedule_short_callback_mirror_flush_r24()

def base36(num: int) -> str:
    try:
        num = int(num)
    except Exception:
        num = 0
    alphabet = '0123456789abcdefghijklmnopqrstuvwxyz'
    if num == 0:
        return '0'
    neg = num < 0
    num = abs(num)
    out = ''
    while num:
        num, rem = divmod(num, 36)
        out = alphabet[rem] + out
    return ('-' if neg else '') + out

def make_short_callback(data_str: str, prefix: str | None=None) -> str:
    global _short_callback_counter
    data_str = str(data_str or '')
    try:
        if len(data_str.encode('utf-8')) <= 54:
            return data_str
    except Exception:
        pass
    if not prefix:
        if data_str.startswith('fvcat_'):
            prefix = 'fvcatx'
        elif data_str.startswith('cat_'):
            prefix = 'catx'
        else:
            prefix = 'cbx'
    with _short_callback_lock:
        _short_callback_counter += 1
        token = base36(_short_callback_counter) + base36(int(time.time() * 1000) % 46656)
        _short_callback_store[token] = {'data': data_str, 'ts': time.time()}
    _queue_short_callback_mirror_r24(token, data_str)
    with _short_callback_lock:
        max_local = SHORT_CALLBACK_LOCAL_HOT_MAX_V248
        if len(_short_callback_store) > max_local:
            cutoff = time.time() - SHORT_CALLBACK_TTL_SECONDS
            for k in list(_short_callback_store.keys()):
                if len(_short_callback_store) <= max_local:
                    break
                row = _short_callback_store.get(k) or {}
                if float(row.get('ts', 0) or 0) < cutoff or len(_short_callback_store) > max_local:
                    _short_callback_store.pop(k, None)
    return f'{prefix}:{token}'

def resolve_short_callback(data_str: str) -> str | None:
    data_str = str(data_str or '')
    if not (data_str.startswith('catx:') or data_str.startswith('fvcatx:') or data_str.startswith('cbx:')):
        return data_str
    token = data_str.split(':', 1)[1]
    with _short_callback_lock:
        item = _short_callback_store.get(token)
    if item:
        return str(item.get('data') or '')
    resolver = globals().get('kv_callback_resolve_v248')
    if callable(resolver):
        try:
            restored = resolver(token)
            if restored:
                with _short_callback_lock:
                    _short_callback_store[token] = {'data': str(restored), 'ts': time.time()}
                    while len(_short_callback_store) > SHORT_CALLBACK_LOCAL_HOT_MAX_V248:
                        _short_callback_store.pop(next(iter(_short_callback_store)), None)
                return str(restored)
        except Exception:
            pass
    return None

def cat_callback(data_str: str) -> str:
    return make_short_callback(data_str, 'catx')

def fvcat_callback(data_str: str) -> str:
    return make_short_callback(data_str, 'fvcatx')

def export_callback(data_str: str) -> str:
    return make_short_callback(data_str, 'cbx')

def build_categories_buttons(start: str, end: str, store: dict | None=None):
    kb = types.InlineKeyboardMarkup(row_width=3)
    buttons = []
    for cat in get_ordered_category_names(include_all=True, store=store):
        slug = get_expense_category_slug(cat, store)
        if not slug:
            continue
        buttons.append(IB(_clean_category_display_name(cat), callback_data=cat_callback(f'cat_show:{start}:{end}:{slug}')))
    for i in range(0, len(buttons), 3):
        kb.row(*buttons[i:i + 3])
    return kb

def build_categories_summary_keyboard(mode: str, start: str, end: str, store: dict | None=None):
    kb = build_categories_buttons(start, end, store=store)
    if mode == 'wthu':
        prev_key = (datetime.strptime(start, '%Y-%m-%d') - timedelta(days=7)).strftime('%Y-%m-%d')
        next_key = (datetime.strptime(start, '%Y-%m-%d') + timedelta(days=7)).strftime('%Y-%m-%d')
        row = [IB('⬅️ Чт–Ср', callback_data=cat_callback(f'cat_wthu:{prev_key}'))]
        if start != week_start_thursday(today_key()):
            row.append(IB('📅 Сегодня', callback_data=cat_callback('cat_today')))
        row.append(IB('Чт–Ср ➡️', callback_data=cat_callback(f'cat_wthu:{next_key}')))
        kb.row(*row)
        kb.row(IB('⬜ Пн–Вс', callback_data=cat_callback(f'cat_wk:{week_start_monday(start)}')), IB('📆 Выбор недели', callback_data=cat_callback('cat_months')))
    elif mode == 'wk':
        prev_key = (datetime.strptime(start, '%Y-%m-%d') - timedelta(days=7)).strftime('%Y-%m-%d')
        next_key = (datetime.strptime(start, '%Y-%m-%d') + timedelta(days=7)).strftime('%Y-%m-%d')
        row = [IB('⬅️ Пн–Вс', callback_data=cat_callback(f'cat_wk:{prev_key}'))]
        if start != week_start_monday(today_key()):
            row.append(IB('📅 Сегодня', callback_data=cat_callback('cat_today')))
        row.append(IB('Пн–Вс ➡️', callback_data=cat_callback(f'cat_wk:{next_key}')))
        kb.row(*row)
        thu_ref = (datetime.strptime(start, '%Y-%m-%d') + timedelta(days=3)).strftime('%Y-%m-%d')
        kb.row(IB('🟦 Чт–Ср', callback_data=cat_callback(f'cat_wthu:{thu_ref}')), IB('📆 Выбор недели', callback_data=cat_callback('cat_months')))
    else:
        kb.row(IB('📅 Сегодня', callback_data=cat_callback('cat_today')), IB('📆 Выбор недели', callback_data=cat_callback('cat_months')))
    if _v85_enabled('usd_categories') and (not financial_view_is_usd(store or {})) and (currency_mode_from_store(store or {}) == 'ars'):
        usd_on = bool((store or {}).setdefault('settings', {}).get('category_usd_enabled', False))
        kb.row(IB('✅ 💵 USD ВКЛ' if usd_on else '⬜ 💵 USD ВЫКЛ', callback_data=cat_callback(f'cat_usd_toggle_period:{mode}:{start}:{end}')))
    if mode == 'wthu':
        kb.row(IB('↕️ Расположение', callback_data=cat_callback(f'cat_order_open_sum:{mode}:{start}:{end}')))
    kb.row(IB('📚 Описание статей', callback_data=cat_callback('cat_desc')))
    kb.row(IB('➕ Добавить', callback_data=cat_callback('cat_add')), IB('✏️ Изменить', callback_data=cat_callback('cat_edit_menu')), IB('🗑 Удалить', callback_data=cat_callback('cat_del_menu')))
    kb.row(IB('⬅️ Назад осн. окно', callback_data=f'd:{today_key()}:back_main'), IB('❌ Закрыть', callback_data=cat_callback('cat_close')))
    return kb

def build_category_layout_text(store: dict, context: str='exact') -> str:
    if context == 'exact':
        lines = ['↕️ Расположение статей', '', 'Слева выберите статью — возле неё появится ✅. Затем справа нажмите номер новой позиции.', 'Статья будет вставлена в выбранное место, остальные автоматически сдвинутся.', '']
    else:
        lines = ['↕️ Расположение статей', '', 'Слева выберите статью — возле неё появится ✅. Затем справа нажмите номер новой позиции.', 'Статья будет вставлена в выбранное место, остальные автоматически сдвинутся.', '']
    for idx, name in enumerate(get_expense_category_order(store), 1):
        lines.append(f'{idx}. {_clean_category_display_name(name)}')
    return wm_common('\n'.join(lines), 7)

def build_category_layout_keyboard(store: dict, context: str, params: tuple, chat_id: int | None=None) -> object:
    slugs = get_expense_category_order_slugs(store)
    if context == 'exact':
        kb = types.InlineKeyboardMarkup(row_width=2)
        start_key, start_rid, end_key, end_rid = params
        selection_key = _category_order_selection_key(int(chat_id or 0), params)
        selected = _category_order_selection.get(selection_key)
        for idx, slug in enumerate(slugs, 1):
            name = _clean_category_display_name(get_category_by_slug(slug, store) or slug)
            left = f'✅ {name}' if slug == selected else name
            select_cb = cat_callback(f'cat_order_select_exact:{slug}:{start_key}:{int(start_rid)}:{end_key}:{int(end_rid)}')
            pos_cb = cat_callback(f'cat_order_position_exact:{idx}:{start_key}:{int(start_rid)}:{end_key}:{int(end_rid)}')
            kb.row(IB(left[:36], callback_data=select_cb), IB(str(idx), callback_data=pos_cb))
        back_cb = cat_callback(f'cat_range_records:{start_key}:{int(start_rid)}:{end_key}:{int(end_rid)}')
        kb.row(IB('⬅️ Назад', callback_data=back_cb), IB('❌ Закрыть', callback_data=cat_callback('cat_close')))
        return kb
    kb = types.InlineKeyboardMarkup(row_width=2)
    mode, start, end = params
    selection_key = _category_order_selection_key(int(chat_id or 0), ('sum', mode, start, end))
    selected = _category_order_selection.get(selection_key)
    for idx, slug in enumerate(slugs, 1):
        name = _clean_category_display_name(get_category_by_slug(slug, store) or slug)
        left = f'✅ {name}' if slug == selected else name
        select_cb = cat_callback(f'cat_order_select_sum:{slug}:{mode}:{start}:{end}')
        pos_cb = cat_callback(f'cat_order_position_sum:{idx}:{mode}:{start}:{end}')
        kb.row(IB(left[:36], callback_data=select_cb), IB(str(idx), callback_data=pos_cb))
    if mode == 'wthu':
        back_cb = cat_callback(f'cat_wthu:{start}')
    elif mode == 'wk':
        back_cb = cat_callback(f'cat_wk:{start}')
    else:
        back_cb = cat_callback(f'cat_range_custom2:{start}:{end}')
    kb.row(IB('⬅️ Назад', callback_data=back_cb), IB('❌ Закрыть', callback_data=cat_callback('cat_close')))
    return kb

def build_category_detail_text(store: dict, start: str, end: str, category: str, label: str):
    """Детализация статьи в режимах ARS / ARS-USD / USD."""
    items = collect_items_for_category(store, start, end, category)
    view_usd = financial_view_is_usd(store)
    mode = currency_mode_from_store(store)
    category_mixed = bool(not view_usd and mode == 'ars' and store.setdefault('settings', {}).get('category_usd_enabled', False) and _v85_enabled('usd_categories'))
    show_rate = not view_usd and (mode != 'ars' or category_mixed)
    rate_info = usd_rate_cached(force=False) if show_rate else None
    clean_category = _clean_category_display_name(category).upper()
    lines = [f'📦 {clean_category}', f'🗓 {label}', '']
    total = sum((amt for _, amt, _ in items))
    lines.append(f'Итого: {format_category_view_amount(store, total, category_mixed)}')
    if show_rate and rate_info and rate_info.get('rate'):
        lines.append(f"Курс: 1 USD = {fmt_num(rate_info['rate']).lstrip('+')} ARS ({_clean_category_display_name(rate_info.get('source') or 'DolarAPI')})")
    lines.append('')
    if not items:
        lines.append('Нет операций по этой статье.')
    else:
        for day_i, amt_i, note_i in items:
            clean_note = _clean_category_display_name((note_i or '').strip())
            amount_text = format_category_view_amount(store, amt_i, category_mixed)
            lines.append(f'• {fmt_date_ddmmyy(day_i)}: {amount_text} {clean_note}'.rstrip())
    return wm_common('\n'.join(lines), 8)

def build_category_detail_keyboard(start: str, end: str, back_callback: str, mode: str | None=None, slug: str | None=None, store: dict | None=None):
    kb = build_categories_buttons(start, end, store=store)
    if mode == 'wthu' and slug:
        prev_key = (datetime.strptime(start, '%Y-%m-%d') - timedelta(days=7)).strftime('%Y-%m-%d')
        next_key = (datetime.strptime(start, '%Y-%m-%d') + timedelta(days=7)).strftime('%Y-%m-%d')
        row = [IB('⬅️ Чт–Ср', callback_data=cat_callback(f'cat_show_wthu:{prev_key}:{slug}'))]
        if start != week_start_thursday(today_key()):
            row.append(IB('📅 Сегодня', callback_data=cat_callback(f'cat_show_wthu:{today_key()}:{slug}')))
        row.append(IB('Чт–Ср ➡️', callback_data=cat_callback(f'cat_show_wthu:{next_key}:{slug}')))
        kb.row(*row)
    elif mode == 'wk' and slug:
        prev_key = (datetime.strptime(start, '%Y-%m-%d') - timedelta(days=7)).strftime('%Y-%m-%d')
        next_key = (datetime.strptime(start, '%Y-%m-%d') + timedelta(days=7)).strftime('%Y-%m-%d')
        row = [IB('⬅️ Пн–Вс', callback_data=cat_callback(f'cat_show_wk:{prev_key}:{slug}'))]
        if start != week_start_monday(today_key()):
            row.append(IB('📅 Сегодня', callback_data=cat_callback(f'cat_show_wk:{today_key()}:{slug}')))
        row.append(IB('Пн–Вс ➡️', callback_data=cat_callback(f'cat_show_wk:{next_key}:{slug}')))
        kb.row(*row)
    kb.row(IB('🔙 Назад', callback_data=cat_callback(back_callback) if str(back_callback).startswith('cat') else back_callback))
    kb.row(IB('⬅️ Назад осн. окно', callback_data=f'd:{today_key()}:back_main'), IB('❌ Закрыть статьи', callback_data=cat_callback('cat_close')))
    return kb

def looks_like_amount(text):
    try:
        amount, note = split_amount_and_note(text)
        return True
    except:
        return False

def text_has_any_digit(text: str) -> bool:
    return bool(re.search('\\d', str(text or '')))

def describe_msg_for_log(msg) -> str:
    try:
        return f"chat={getattr(getattr(msg, 'chat', None), 'id', '?')} msg={getattr(msg, 'message_id', '?')} type={getattr(msg, 'content_type', '?')}"
    except Exception:
        return 'msg=?'

def _category_add_prompt_text(target_chat_id: int) -> str:
    return wm_common(f'➕ Добавление статьи расходов для: {get_chat_display_name(target_chat_id)}\n\nОтправь одним сообщением в формате:\nНазвание статьи: ключ1, ключ2, ключ3\n\nПример:\nРЕМОНТ: гипсокартон, шпаклевка, краска, инструмент\n\nБот будет относить расход к статье, если в описании расхода найден любой ключ.\nДля отмены напиши: отмена', 11)

def start_category_add_wait(owner_chat_id: int, target_chat_id: int, owner_day_key: str | None=None):
    store = get_chat_store(owner_chat_id)
    prev = store.get('category_add_wait') or {}
    store['category_add_wait'] = {'type': 'expense_category_add', 'target_chat_id': int(target_chat_id), 'owner_day_key': owner_day_key or today_key(), 'started_at': now_local().isoformat(timespec='seconds')}
    save_data(data)
    kb = _category_prompt_keyboard(owner_chat_id, owner_day_key=owner_day_key)
    prev_id = prev.get('prompt_msg_id') if isinstance(prev, dict) else None
    text = _category_add_prompt_text(target_chat_id)
    if prev_id:
        try:
            _tg_call_retry(bot.edit_message_text, text, chat_id=owner_chat_id, message_id=int(prev_id), reply_markup=kb, purpose='category_add_prompt_edit')
            prompt_id = int(prev_id)
        except Exception:
            sent = _tg_call_retry(bot.send_message, owner_chat_id, text, reply_markup=kb, purpose='category_add_prompt')
            prompt_id = sent.message_id
    else:
        sent = _tg_call_retry(bot.send_message, owner_chat_id, text, reply_markup=kb, purpose='category_add_prompt')
        prompt_id = sent.message_id
    store['category_add_wait']['prompt_msg_id'] = prompt_id
    store['category_add_wait']['countdown_base_text'] = text
    save_data(data)
    schedule_cancel_category_wait(owner_chat_id, 'category_add_wait', prompt_id, None)
    bot_journal('category_add_wait_start', owner_chat_id, f'target={get_chat_display_name(target_chat_id)}')

def handle_category_add_message(msg) -> bool:
    if getattr(msg, 'content_type', None) != 'text':
        return False
    chat_id = int(msg.chat.id)
    store = get_chat_store(chat_id)
    wait = store.get('category_add_wait')
    if not wait or wait.get('type') != 'expense_category_add':
        return False
    _durable_note_source_consumed('category_add_wait')
    text = (msg.text or '').strip()
    target_chat_id = int(wait.get('target_chat_id') or chat_id)
    try:
        name, keywords = parse_category_definition(text)
        if name is None:
            clear_category_wait_state(chat_id, 'category_add_wait', delete_prompt=True)
            send_and_auto_delete(chat_id, '❎ Добавление статьи отменено.', 10)
            return True
        item = add_custom_expense_category(target_chat_id, name, keywords)
        clear_category_wait_state(chat_id, 'category_add_wait', delete_prompt=True)
        send_and_auto_delete(chat_id, f"✅ Статья добавлена: {item.get('name')}\nКлючи: {', '.join(item.get('keywords', []))}", 20)
        try:
            bot.delete_message(chat_id, msg.message_id)
        except Exception:
            pass
        return True
    except Exception:
        send_and_auto_delete(chat_id, '❌ Не понял формат. Пример:\nРЕМОНТ: гипсокартон, шпаклевка, краска\n\nДля отмены напиши: отмена', 20)
        return True
_category_wait_timers = {}

def _category_wait_key(chat_id: int, field: str):
    return (int(chat_id), str(field))

def clear_category_wait_state(chat_id: int, field: str, expected_prompt_id: int | None=None, delete_prompt: bool=True) -> bool:
    store = get_chat_store(chat_id)
    wait = store.get(field) or {}
    prompt_id = wait.get('prompt_msg_id') if isinstance(wait, dict) else None
    if expected_prompt_id is not None and prompt_id and (int(prompt_id) != int(expected_prompt_id)):
        return False
    key = _category_wait_key(chat_id, field)
    _category_wait_timers.pop(key, None)
    DELAYED_SCHEDULER.cancel(f'category-wait:{int(chat_id)}:{str(field)}')
    store[field] = None
    save_data(data)
    if delete_prompt and prompt_id:
        try:
            bot.delete_message(chat_id, int(prompt_id))
        except Exception:
            pass
    return True

def _category_countdown_text(base_text: str, remaining: int) -> str:
    base = strip_window_mark(str(base_text or '')).rstrip()
    return wm_common(base + f'\n\n⏳ До закрытия: {int(remaining)} сек.', 11)

def schedule_cancel_category_wait(chat_id: int, field: str, prompt_message_id: int, delay: float | None=None):
    """Единый таймер ожидания статьи; по timeout операция отменяется и окно возвращается в основное."""
    key = _category_wait_key(chat_id, field)
    if delay is None:
        delay = internal_timer_seconds('input_wait', 40)

    def _job():
        try:
            store = get_chat_store(chat_id)
            wait = store.get(field) or {}
            if not wait or int(wait.get('prompt_msg_id') or 0) != int(prompt_message_id):
                return
            cleared = clear_category_wait_state(chat_id, field, prompt_message_id, delete_prompt=False)
            if cleared:
                day_key = store.get('current_view_day') or today_key()
                return_to_main_window_closing_previous(chat_id, day_key, int(prompt_message_id))
        except Exception as e:
            log_error(f'schedule_cancel_category_wait({chat_id},{field},{prompt_message_id}): {e}')
    scheduler_key = f'category-wait:{int(chat_id)}:{str(field)}'
    DELAYED_SCHEDULER.cancel(scheduler_key)
    deadline = DELAYED_SCHEDULER.schedule(scheduler_key, float(delay), _job)
    _category_wait_timers[key] = deadline

def _category_prompt_keyboard(chat_id: int, owner_day_key: str | None=None, back_callback: str | None=None, insert_text: str | None=None):
    kb = types.InlineKeyboardMarkup()
    day = owner_day_key or get_chat_store(chat_id).get('current_view_day') or today_key()
    owner_store = get_chat_store(chat_id)
    wait = owner_store.get('category_add_wait') or owner_store.get('category_edit_wait') or {}
    target_chat_id = int(wait.get('target_chat_id') or chat_id)
    if target_chat_id != int(chat_id):
        delete_callback = fvcat_callback(f'fvcat_del_menu:{target_chat_id}:{day}:{day}')
    else:
        delete_callback = cat_callback('cat_del_menu')
    if insert_text:
        kb.row(make_copy_or_inline_button('✏️ Изменить значение', str(insert_text), viewer_chat_id=chat_id))
    kb.row(IB('🗑 Удалить статью', callback_data=delete_callback))
    kb.row(IB('⬅️ Назад', callback_data=cat_callback('cat_prompt_back')), IB('❌ Закрыть', callback_data=cat_callback('cat_add_cancel')), IB('⬅️ Осн. окно', callback_data=back_callback or f'd:{day}:back_main'))
    return kb

def category_custom_items_for_chat(chat_id: int) -> list[dict]:
    return list(_custom_category_list(get_chat_store(chat_id)))

def category_edit_items_for_chat(chat_id: int) -> list[dict]:
    store = get_chat_store(chat_id)
    return list(_base_category_items(store)) + list(_custom_category_list(store))

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

def build_category_delete_keyboard(chat_id: int):
    store = get_chat_store(chat_id)
    selected = set(store.get('category_delete_selection') or [])
    kb = types.InlineKeyboardMarkup(row_width=2)
    items = category_custom_items_for_chat(chat_id)
    if not items:
        kb.row(IB('Нет пользовательских статей', callback_data='none'))
    for item in items:
        slug = item.get('slug')
        icon = '☑️' if slug in selected else '⬛'
        kb.row(IB(f"{icon} {item.get('name')}", callback_data=cat_callback(f'cat_del_toggle:{slug}')))
    kb.row(IB('🗑 Удалить выбранное', callback_data=cat_callback('cat_del_selected')))
    kb.row(IB('⏪ Назад к статьям', callback_data=cat_callback('cat_today')), IB('⬅️ Назад осн. окно', callback_data=f"d:{get_chat_store(chat_id).get('current_view_day', today_key())}:back_main"))
    return kb

def build_category_edit_keyboard(chat_id: int):
    kb = types.InlineKeyboardMarkup(row_width=2)
    items = category_edit_items_for_chat(chat_id)
    if not items:
        kb.row(IB('Нет статей', callback_data='none'))
    for item in items:
        mark = 'Б' if item.get('base') else 'С'
        kb.row(IB(f"✏️ {item.get('name')} ({mark})", callback_data=cat_callback(f"cat_edit_pick:{item.get('slug')}")))
    kb.row(IB('⏪ Назад к статьям', callback_data=cat_callback('cat_today')), IB('⬅️ Назад осн. окно', callback_data=f"d:{get_chat_store(chat_id).get('current_view_day', today_key())}:back_main"))
    return kb

def start_category_edit_wait(chat_id: int, target_chat_id: int, slug: str):
    store = get_chat_store(chat_id)
    target_store = get_chat_store(target_chat_id)
    item = _base_category_item_by_slug(target_store, slug) or next((x for x in _custom_category_list(target_store) if x.get('slug') == slug), None)
    if not item:
        send_and_auto_delete(chat_id, '❌ Статья не найдена.', 10)
        return
    text = wm_common(f"✏️ Изменение статьи: {item.get('name')}\n\nОтправь новое название и ключевые слова одним сообщением:\nНазвание статьи: ключ1, ключ2, ключ3\n\nСейчас: {item.get('name')}: {', '.join(item.get('keywords', []))}\n\nЕсли нужно изменить только ключи — оставь то же название.\nЧерез 1 минуту режим автоматически закроется.", 11)
    current_edit_text = f"{item.get('name')}: {', '.join(item.get('keywords', []))}"
    kb = _category_prompt_keyboard(chat_id, insert_text=current_edit_text)
    prev = store.get('category_edit_wait') or {}
    prev_id = prev.get('prompt_msg_id') if isinstance(prev, dict) else None
    if prev_id:
        try:
            _tg_call_retry(bot.edit_message_text, text, chat_id=chat_id, message_id=int(prev_id), reply_markup=kb, purpose='category_edit_prompt_edit')
            prompt_id = int(prev_id)
        except Exception:
            sent = _tg_call_retry(bot.send_message, chat_id, text, reply_markup=kb, purpose='category_edit_prompt_send')
            prompt_id = sent.message_id
    else:
        sent = _tg_call_retry(bot.send_message, chat_id, text, reply_markup=kb, purpose='category_edit_prompt_send')
        prompt_id = sent.message_id
    store['category_edit_wait'] = {'type': 'expense_category_edit', 'target_chat_id': int(target_chat_id), 'slug': str(slug), 'prompt_msg_id': prompt_id, 'countdown_base_text': text, 'owner_day_key': owner_day_key if 'owner_day_key' in locals() else today_key(), 'started_at': now_local().isoformat(timespec='seconds')}
    save_data(data)
    schedule_cancel_category_wait(chat_id, 'category_edit_wait', prompt_id, None)

def handle_category_edit_message(msg) -> bool:
    if getattr(msg, 'content_type', None) != 'text':
        return False
    chat_id = int(msg.chat.id)
    store = get_chat_store(chat_id)
    wait = store.get('category_edit_wait')
    if not wait or wait.get('type') != 'expense_category_edit':
        return False
    _durable_note_source_consumed('category_edit_wait')
    text = (msg.text or '').strip()
    if text.lower() in {'отмена', 'cancel', '/cancel'}:
        clear_category_wait_state(chat_id, 'category_edit_wait', delete_prompt=True)
        send_and_auto_delete(chat_id, '❎ Изменение статьи отменено.', 10)
        return True
    try:
        name, keywords = parse_category_definition(text)
        if not name:
            raise ValueError('format')
        item = update_custom_expense_category(int(wait.get('target_chat_id') or chat_id), str(wait.get('slug')), name, keywords)
        clear_category_wait_state(chat_id, 'category_edit_wait', delete_prompt=True)
        if item:
            send_and_auto_delete(chat_id, f"✅ Статья изменена: {item.get('name')}\nКлючи: {', '.join(item.get('keywords', []))}", 20)
        else:
            send_and_auto_delete(chat_id, '❌ Статья не найдена.', 10)
        try:
            bot.delete_message(chat_id, msg.message_id)
        except Exception:
            pass
        return True
    except Exception:
        send_and_auto_delete(chat_id, '❌ Не понял формат. Пример:\nРЕМОНТ: гипсокартон, шпаклевка, краска', 20)
        return True
# v262
