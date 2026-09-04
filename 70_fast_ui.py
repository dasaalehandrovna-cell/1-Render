# v262
UI_EDIT_MIN_INTERVAL_SECONDS = float(os.getenv('UI_EDIT_MIN_INTERVAL_SECONDS', '0.03') or '0.03')
_ui_edit_lock = threading.RLock()
_ui_edit_last_ts = {}
_ui_edit_pending = {}
_ui_edit_timers = {}

def _ui_edit_key(chat_id: int, message_id: int):
    return (int(chat_id), int(message_id))

def _perform_fast_ui_edit(payload: dict) -> str:
    chat_id = int(payload.get('chat_id'))
    message_id = int(payload.get('message_id'))
    text = payload.get('text') or ''
    reply_markup = payload.get('reply_markup')
    parse_mode = payload.get('parse_mode')
    purpose = payload.get('purpose') or 'fast_ui_edit'

    def _call_with_window_context(method, *args, **kwargs):
        diag_context = globals().get('window_diag_context')
        values = {'purpose': purpose, 'request_id': payload.get('_window_diag_request_id'), 'expected_seq': payload.get('_window_diag_expected_seq'), 'window_force': True}
        if callable(diag_context):
            with diag_context(**values):
                return _tg_call_retry(method, *args, **kwargs)
        return _tg_call_retry(method, *args, **kwargs)
    try:
        _call_with_window_context(bot.edit_message_text, text, chat_id=chat_id, message_id=message_id, reply_markup=reply_markup, parse_mode=parse_mode, attempts=1, purpose=purpose + '_text')
        return 'ok'
    except Exception as e1:
        low = str(e1).lower()
        if 'message is not modified' in low:
            return 'ok'
        if is_telegram_429(e1):
            try:
                bot_journal('ui_edit_rate_limited', chat_id, f'{purpose}: {str(e1)[:220]}', 'WARN')
            except Exception:
                pass
            return 'rate_limited'
        if 'message to edit not found' in low or "message can't be edited" in low:
            return 'not_found'
        try:
            _call_with_window_context(bot.edit_message_caption, chat_id=chat_id, message_id=message_id, caption=text, reply_markup=reply_markup, parse_mode=parse_mode, attempts=1, purpose=purpose + '_caption')
            return 'ok'
        except Exception as e2:
            low2 = str(e2).lower()
            if 'message is not modified' in low2:
                return 'ok'
            if is_telegram_429(e2):
                try:
                    bot_journal('ui_edit_rate_limited', chat_id, f'{purpose}: {str(e2)[:220]}', 'WARN')
                except Exception:
                    pass
                return 'rate_limited'
            if 'message to edit not found' in low2 or "message can't be edited" in low2:
                return 'not_found'
            try:
                bot_journal('ui_edit_failed', chat_id, f'{purpose}: {str(e1)[:180]} / {str(e2)[:180]}', 'WARN')
            except Exception:
                pass
            return 'failed'

def _v177_legacy_0210_run_pending_ui_edit(key):
    with _ui_edit_lock:
        payload = _ui_edit_pending.pop(key, None)
        _ui_edit_timers.pop(key, None)
        if not payload:
            return
        _ui_edit_last_ts[key] = time.time()
    try:
        diag_apply = globals().get('window_diag_fast_ui_apply')
        if callable(diag_apply):
            diag_apply(payload, delayed=True)
    except Exception:
        pass
    _perform_fast_ui_edit(payload)
try:
    _v177_legacy_0210_run_pending_ui_edit.__name__ = '_run_pending_ui_edit'
except Exception:
    pass

def _v177_legacy_0211_fast_ui_edit_message_text(chat_id: int, message_id: int, text: str, reply_markup=None, parse_mode=None, purpose: str='fast_ui') -> str:
    try:
        if 'secret' not in str(purpose or '').lower():
            reply_markup = ensure_previous_back_nav_keyboard(reply_markup, int(chat_id), int(message_id))
            reply_markup = ensure_main_back_nav_keyboard(reply_markup, int(chat_id))
    except Exception:
        pass
    try:
        text = _ensure_window_marker_for_render(text, reply_markup, int(chat_id), int(message_id), purpose)
    except Exception:
        pass
    key = _ui_edit_key(chat_id, message_id)
    payload = {'chat_id': int(chat_id), 'message_id': int(message_id), 'text': text, 'reply_markup': reply_markup, 'parse_mode': parse_mode, 'purpose': purpose}
    try:
        diag_prepare = globals().get('window_diag_prepare_fast_ui_payload')
        if callable(diag_prepare):
            payload = diag_prepare(payload) or payload
    except Exception:
        pass
    force_immediate = str(purpose or '') == 'back_main_instant'
    if force_immediate:
        cancel_fast_ui_edit(chat_id, message_id)
    now_ts = time.time()
    with _ui_edit_lock:
        last_ts = float(_ui_edit_last_ts.get(key, 0) or 0)
        wait = 0.0 if force_immediate else max(0.0, effective_ui_edit_interval() - (now_ts - last_ts))
        if wait > 0:
            replaced_payload = _ui_edit_pending.get(key)
            _ui_edit_pending[key] = payload
            scheduler_key = f'ui-edit:{int(chat_id)}:{int(message_id)}'
            DELAYED_SCHEDULER.cancel(scheduler_key)
            deadline = DELAYED_SCHEDULER.schedule(scheduler_key, wait + 0.05, _run_pending_ui_edit, key)
            _ui_edit_timers[key] = deadline
            try:
                diag_scheduled = globals().get('window_diag_fast_ui_scheduled')
                if callable(diag_scheduled):
                    diag_scheduled(payload, wait + 0.05, replaced_payload=replaced_payload)
            except Exception:
                pass
            return 'scheduled'
        _ui_edit_last_ts[key] = now_ts
    try:
        diag_apply = globals().get('window_diag_fast_ui_apply')
        if callable(diag_apply):
            diag_apply(payload, delayed=False)
    except Exception:
        pass
    return _perform_fast_ui_edit(payload)
try:
    _v177_legacy_0211_fast_ui_edit_message_text.__name__ = 'fast_ui_edit_message_text'
except Exception:
    pass

def v178_edit_reply_markup_async(chat_id: int, message_id: int, reply_markup=None, purpose: str='ui_markup') -> bool:
    """Non-blocking keyboard-only update for callback handlers in every contour."""
    cid = int(chat_id)
    mid = int(message_id)

    def _job():
        started = time.monotonic()
        try:
            _tg_call_retry(bot.edit_message_reply_markup, cid, mid, reply_markup=reply_markup, attempts=1, purpose=str(purpose or 'ui_markup') + '_async')
        except Exception:
            pass
        finally:
            try:
                stage = globals().get('v177_perf_stage')
                if callable(stage):
                    stage('telegram_reply_markup_async', time.monotonic() - started)
            except Exception:
                pass
    try:
        return bool(UI_TASK_POOL.submit_unique(f'v178-markup:{cid}:{mid}', _job))
    except Exception:
        return False

def v177_delete_message_async(chat_id: int, message_id: int, purpose: str='ui_close') -> bool:
    """Delete an obsolete UI message without making the callback wait for Telegram."""
    cid = int(chat_id)
    mid = int(message_id)

    def _job():
        started = time.monotonic()
        try:
            _tg_call_retry(bot.delete_message, cid, mid, attempts=1, purpose=str(purpose or 'ui_close') + '_async')
        except Exception:
            pass
        finally:
            try:
                stage = globals().get('v177_perf_stage')
                if callable(stage):
                    stage('telegram_delete_async', time.monotonic() - started)
            except Exception:
                pass
    try:
        pool = globals().get('GENERAL_TASK_POOL')
        if pool is not None:
            return bool(pool.submit_unique(f'v177-ui-delete:{cid}:{mid}', _job))
    except Exception:
        pass
    return False

def cancel_fast_ui_edit(chat_id: int, message_id: int):
    key = _ui_edit_key(chat_id, message_id)
    with _ui_edit_lock:
        _ui_edit_pending.pop(key, None)
        _ui_edit_timers.pop(key, None)
    DELAYED_SCHEDULER.cancel(f'ui-edit:{int(chat_id)}:{int(message_id)}')
_WINDOW_NAV_HISTORY_LOCK = threading.RLock()
_WINDOW_NAV_HISTORY = defaultdict(list)
_WINDOW_NAV_HISTORY_LIMIT = 12
_WINDOW_MARKER_MISSING_THROTTLE = {}

def _serialize_inline_keyboard(reply_markup):
    if reply_markup is None:
        return None
    rows_out = []
    try:
        for row in list(getattr(reply_markup, 'keyboard', None) or []):
            row_out = []
            for btn in row or []:
                try:
                    if hasattr(btn, 'to_dict'):
                        row_out.append(btn.to_dict())
                    else:
                        row_out.append({'text': getattr(btn, 'text', ''), 'callback_data': getattr(btn, 'callback_data', None), 'url': getattr(btn, 'url', None), 'switch_inline_query': getattr(btn, 'switch_inline_query', None), 'switch_inline_query_current_chat': getattr(btn, 'switch_inline_query_current_chat', None)})
                except Exception:
                    continue
            if row_out:
                rows_out.append(row_out)
    except Exception:
        return None
    return rows_out

def _deserialize_inline_keyboard(rows_data):
    if not rows_data:
        return None
    kb = types.InlineKeyboardMarkup()
    for row in rows_data:
        buttons = []
        for raw in row or []:
            try:
                if hasattr(types.InlineKeyboardButton, 'de_json'):
                    btn = types.InlineKeyboardButton.de_json(raw)
                else:
                    allowed = {k: v for k, v in dict(raw or {}).items() if k in {'url', 'callback_data', 'switch_inline_query', 'switch_inline_query_current_chat', 'callback_game', 'pay', 'login_url', 'web_app', 'copy_text'} and v is not None}
                    btn = types.InlineKeyboardButton(str((raw or {}).get('text') or ''), **allowed)
                buttons.append(btn)
            except Exception:
                continue
        if buttons:
            kb.row(*buttons)
    return kb

def _window_nav_key(chat_id: int, message_id: int):
    return (int(chat_id), int(message_id))

def _nav_history_push_v248(key, snap: dict) -> bool:
    # If this key already fell back locally during a KV outage, keep one coherent stack.
    with _WINDOW_NAV_HISTORY_LOCK:
        stack = _WINDOW_NAV_HISTORY.get(key)
        if stack:
            if stack[-1].get('text') == snap.get('text') and stack[-1].get('markup') == snap.get('markup'):
                return True
            stack.append(snap)
            if len(stack) > _WINDOW_NAV_HISTORY_LIMIT:
                del stack[:-_WINDOW_NAV_HISTORY_LIMIT]
            return True
    push = globals().get('kv_nav_push_v248')
    if callable(push):
        try:
            if push(int(key[0]), int(key[1]), snap, _WINDOW_NAV_HISTORY_LIMIT):
                return True
        except Exception:
            pass
    with _WINDOW_NAV_HISTORY_LOCK:
        stack = _WINDOW_NAV_HISTORY[key]
        if stack and stack[-1].get('text') == snap.get('text') and stack[-1].get('markup') == snap.get('markup'):
            return True
        stack.append(snap)
        if len(stack) > _WINDOW_NAV_HISTORY_LIMIT:
            del stack[:-_WINDOW_NAV_HISTORY_LIMIT]
    return True

def _nav_history_peek_v248(key):
    with _WINDOW_NAV_HISTORY_LOCK:
        stack = _WINDOW_NAV_HISTORY.get(key) or []
        if stack:
            return dict(stack[-1])
    fn = globals().get('kv_nav_peek_v248')
    if callable(fn):
        try:
            value = fn(int(key[0]), int(key[1]))
            return dict(value) if isinstance(value, dict) else None
        except Exception:
            pass
    return None

def _nav_history_pop_v248(key) -> bool:
    with _WINDOW_NAV_HISTORY_LOCK:
        stack = _WINDOW_NAV_HISTORY.get(key) or []
        if stack:
            stack.pop()
            if not stack:
                _WINDOW_NAV_HISTORY.pop(key, None)
            return True
    fn = globals().get('kv_nav_pop_v248')
    if callable(fn):
        try:
            return bool(fn(int(key[0]), int(key[1])))
        except Exception:
            pass
    return False

def _nav_history_clear_v248(chat_id: int, message_id: int) -> None:
    key = _window_nav_key(chat_id, message_id)
    with _WINDOW_NAV_HISTORY_LOCK:
        _WINDOW_NAV_HISTORY.pop(key, None)
    fn = globals().get('kv_nav_clear_v248')
    if callable(fn):
        try:
            fn(int(chat_id), int(message_id))
        except Exception:
            pass

def remember_previous_window(call):
    try:
        msg = call.message
        key = _window_nav_key(msg.chat.id, msg.message_id)
        text = getattr(msg, 'text', None) or getattr(msg, 'caption', None) or ''
        markup = _serialize_inline_keyboard(getattr(msg, 'reply_markup', None))
        if not text and (not markup):
            return False
        snap = {'text': str(text), 'markup': markup, 'parse_mode': None, 'saved_at': time.time()}
        return _nav_history_push_v248(key, snap)
    except Exception:
        return False

def window_has_previous(chat_id: int, message_id: int) -> bool:
    key = _window_nav_key(chat_id, message_id)
    with _WINDOW_NAV_HISTORY_LOCK:
        if bool(_WINDOW_NAV_HISTORY.get(key)):
            return True
    fn = globals().get('kv_nav_has_v248')
    if callable(fn):
        try:
            return bool(fn(int(chat_id), int(message_id)))
        except Exception:
            pass
    return False

def ensure_previous_back_nav_keyboard(reply_markup, chat_id: int, message_id: int):
    if reply_markup is None:
        reply_markup = types.InlineKeyboardMarkup()
    try:
        callbacks, labels = ([], [])
        for row in list(getattr(reply_markup, 'keyboard', None) or []):
            for btn in row or []:
                callbacks.append(str(getattr(btn, 'callback_data', '') or ''))
                labels.append(str(getattr(btn, 'text', '') or ''))
        has_own_back = any(('back' in cb.casefold() and 'back_main' not in cb.casefold() or cb.startswith('nav_prev') for cb in callbacks)) or any(('назад' in t.casefold() and 'осн' not in t.casefold() for t in labels))
        if not has_own_back and window_has_previous(chat_id, message_id):
            reply_markup.row(IB('🔙 Назад', callback_data='nav_prev'))
    except Exception:
        pass
    return reply_markup

def _v177_legacy_0212_restore_previous_window(call) -> bool:
    chat_id = int(call.message.chat.id)
    message_id = int(call.message.message_id)
    key = _window_nav_key(chat_id, message_id)
    snap = _nav_history_peek_v248(key)
    if not snap:
        try:
            bot.answer_callback_query(call.id, 'История окна очищена после перезапуска. Используйте «Назад осн. окно».')
        except Exception:
            pass
        return False
    markup = _deserialize_inline_keyboard(snap.get('markup'))
    try:
        markup = ensure_previous_back_nav_keyboard(markup, chat_id, message_id)
        markup = ensure_main_back_nav_keyboard(markup, chat_id)
    except Exception:
        pass
    result = fast_ui_edit_message_text(chat_id, message_id, str(snap.get('text') or ''), reply_markup=markup, parse_mode=snap.get('parse_mode'), purpose='nav_prev_restore')
    if result in {'ok', 'scheduled', 'rate_limited'}:
        _nav_history_pop_v248(key)
        return True
    return False
try:
    _v177_legacy_0212_restore_previous_window.__name__ = 'restore_previous_window'
except Exception:
    pass

def _suggest_window_marker(group: str) -> str:
    try:
        nums = []
        for value in WINDOW_MARKER_CONSTANTS.values():
            value = str(value or '')
            if value.startswith(group) and value[len(group):].isdigit():
                nums.append(int(value[len(group):]))
        return f'{group}{(max(nums) + 1 if nums else 1)}'
    except Exception:
        return f'{group}?'

def journal_missing_window_marker(raw_action: str, chat_id=None, message_id=None, text: str='', reply_markup=None, purpose: str=''):
    raw = str(raw_action or '')
    normalized = _normalize_window_action(raw)
    group = _window_group_for_action(normalized)
    first_line_rows = strip_window_mark(str(text or '')).strip().splitlines()[:1]
    first_line = (first_line_rows[0] if first_line_rows else '')[:140]
    try:
        marker_key = _window_key_from_markup(reply_markup) if reply_markup is not None else ''
    except Exception:
        marker_key = ''
    throttle_key = (normalized, int(chat_id or 0), int(message_id or 0), str(purpose or ''))
    now_ts = time.time()
    if now_ts - float(_WINDOW_MARKER_MISSING_THROTTLE.get(throttle_key, 0) or 0) < 30:
        return
    _WINDOW_MARKER_MISSING_THROTTLE[throttle_key] = now_ts
    detail = f'raw={raw[:220]}; normalized={normalized}; chat={chat_id}; msg={message_id}; purpose={purpose}; first_line={first_line!r}; markup_key={marker_key}; suggested={_suggest_window_marker(group)}'
    try:
        bot_journal('window_marker_missing', chat_id, detail, 'ERROR')
    except Exception:
        log_error('WINDOW_MARKER_MISSING_DETAIL: ' + detail)

def _ensure_window_marker_for_render(text: str, reply_markup, chat_id: int, message_id: int, purpose: str='') -> str:
    body = str(text or '')
    if has_window_mark(body) or reply_markup is None:
        return body
    key = _window_key_from_markup(reply_markup)
    code = _window_marker_code(key)
    if not window_marker_is_declared(key):
        journal_missing_window_marker(key, chat_id, message_id, body, reply_markup, purpose)
    return window_mark(body, code)

def _v177_legacy_0214_safe_edit(bot, call, text, reply_markup=None, parse_mode=None):
    """Быстрое обновление окна с маркером, историей и безопасным fallback."""
    chat_id = call.message.chat.id
    msg_id = call.message.message_id
    raw_action = str(getattr(call, 'data', '') or '')
    if raw_action != 'nav_prev':
        remember_previous_window(call)
    try:
        code = window_code_for_callback(raw_action, owner_chat=is_owner_chat(chat_id))
        if not window_marker_is_declared(raw_action):
            journal_missing_window_marker(raw_action, chat_id, msg_id, text, reply_markup, 'safe_edit')
        text = window_mark(text, code, html_mode=str(parse_mode or '').upper() == 'HTML')
    except Exception:
        pass
    if reply_markup is None:
        try:
            reply_markup = default_window_nav_keyboard(chat_id)
        except Exception:
            pass
    try:
        reply_markup = ensure_previous_back_nav_keyboard(reply_markup, chat_id, msg_id)
        reply_markup = ensure_main_back_nav_keyboard(reply_markup, chat_id)
    except Exception:
        pass
    result = fast_ui_edit_message_text(chat_id, msg_id, text, reply_markup=reply_markup, parse_mode=parse_mode, purpose='safe_edit_fast')
    if result in {'ok', 'scheduled', 'rate_limited'}:
        if result == 'rate_limited':
            try:
                bot.answer_callback_query(call.id, 'Обновление отложено: Telegram ограничил частые клики.', show_alert=False)
            except Exception:
                pass
        try:
            _touch_v98_auto_close_for_callback(chat_id, msg_id, raw_action)
        except Exception:
            pass
        return
    try:
        if chat_buttons_current_window_enabled(chat_id):
            try:
                bot.answer_callback_query(call.id, 'Текущее окно недоступно, новое не создаю.', show_alert=False)
            except Exception:
                pass
            return
    except Exception:
        pass
    try:
        try:
            diag_note = globals().get('window_diag_note_recreate')
            if callable(diag_note):
                diag_note(chat_id, msg_id, result, 'safe_edit_send_fallback')
        except Exception:
            pass
        diag_context = globals().get('window_diag_context')
        if callable(diag_context):
            with diag_context(purpose='safe_edit_send_fallback', recreate_from=msg_id, recreate_reason=result, window_force=True):
                sent = _tg_call_retry(bot.send_message, chat_id, text, reply_markup=reply_markup, parse_mode=parse_mode, attempts=1, purpose='safe_edit_send_fallback')
        else:
            sent = _tg_call_retry(bot.send_message, chat_id, text, reply_markup=reply_markup, parse_mode=parse_mode, attempts=1, purpose='safe_edit_send_fallback')
        try:
            _touch_v98_auto_close_for_callback(chat_id, sent.message_id, raw_action)
        except Exception:
            pass
    except Exception as e:
        if not is_telegram_429(e):
            log_error(f'safe_edit fallback send {chat_id}: {e}')
try:
    _v177_legacy_0214_safe_edit.__name__ = 'safe_edit'
except Exception:
    pass

def _v177_legacy_0215_safe_edit_current_only(bot, call, text, reply_markup=None, parse_mode=None):
    """Редактирует только текущее окно, без создания нового."""
    chat_id = call.message.chat.id
    msg_id = call.message.message_id
    raw_action = str(getattr(call, 'data', '') or '')
    if raw_action != 'nav_prev':
        remember_previous_window(call)
    try:
        code = window_code_for_callback(raw_action, owner_chat=is_owner_chat(chat_id))
        if not window_marker_is_declared(raw_action):
            journal_missing_window_marker(raw_action, chat_id, msg_id, text, reply_markup, 'safe_edit_current_only')
        text = window_mark(text, code, html_mode=str(parse_mode or '').upper() == 'HTML')
    except Exception:
        pass
    if reply_markup is None:
        try:
            reply_markup = default_window_nav_keyboard(chat_id)
        except Exception:
            pass
    try:
        reply_markup = ensure_previous_back_nav_keyboard(reply_markup, chat_id, msg_id)
        reply_markup = ensure_main_back_nav_keyboard(reply_markup, chat_id)
    except Exception:
        pass
    result = fast_ui_edit_message_text(chat_id, msg_id, text, reply_markup=reply_markup, parse_mode=parse_mode, purpose='safe_edit_current_only_fast')
    if result == 'rate_limited':
        try:
            bot.answer_callback_query(call.id, 'Обновление отложено: слишком много кликов.', show_alert=False)
        except Exception:
            pass
    try:
        _touch_v98_auto_close_for_callback(chat_id, msg_id, raw_action)
    except Exception:
        pass
    return result in {'ok', 'scheduled', 'rate_limited'}
try:
    _v177_legacy_0215_safe_edit_current_only.__name__ = 'safe_edit_current_only'
except Exception:
    pass
CATEGORY_PAGE_SAFE_CHARS = 3300

def _split_category_pages(text: str, limit: int=CATEGORY_PAGE_SAFE_CHARS) -> list[str]:
    text = str(text or '').strip()
    if not text:
        return ['']
    pages = []
    current = ''
    for raw_line in text.splitlines():
        line = raw_line
        chunks = []
        while len(line) > limit:
            cut = line.rfind(' ', 0, limit)
            if cut < max(200, limit // 3):
                cut = limit
            chunks.append(line[:cut].rstrip())
            line = line[cut:].lstrip()
        chunks.append(line)
        for chunk in chunks:
            candidate = chunk if not current else current + '\n' + chunk
            if len(candidate) > limit and current:
                pages.append(current.rstrip())
                current = chunk
            else:
                current = candidate
    if current or not pages:
        pages.append(current.rstrip())
    return pages

def _serialize_category_markup(markup) -> list[list[dict]]:
    rows = []
    for row in getattr(markup, 'keyboard', []) or []:
        out = []
        for btn in row or []:
            item = {'text': str(getattr(btn, 'text', '') or '')}
            cb = getattr(btn, 'callback_data', None)
            if cb is not None:
                full = None
                try:
                    full = resolve_short_callback(str(cb))
                except Exception:
                    full = None
                item['callback_data'] = str(full or cb)
            url = getattr(btn, 'url', None)
            if url:
                item['url'] = str(url)
            out.append(item)
        if out:
            rows.append(out)
    return rows

def _deserialize_category_markup(rows) -> object:
    kb = types.InlineKeyboardMarkup()
    for row in rows or []:
        buttons = []
        for item in row or []:
            text = str((item or {}).get('text') or '')
            cb = (item or {}).get('callback_data')
            url = (item or {}).get('url')
            if cb is not None:
                cb = str(cb)
                if cb.startswith('fvcat_'):
                    cb = fvcat_callback(cb)
                elif cb.startswith('cat_'):
                    cb = cat_callback(cb)
                else:
                    cb = make_short_callback(cb)
                buttons.append(IB(text, callback_data=cb))
            elif url:
                buttons.append(types.InlineKeyboardButton(text=text, url=str(url)))
            else:
                buttons.append(IB(text, callback_data='none'))
        if buttons:
            kb.row(*buttons)
    return kb

def _category_paged_keyboard(state: dict, page_index: int):
    kb = _deserialize_category_markup((state or {}).get('base_markup') or [])
    total = max(1, len((state or {}).get('pages') or []))
    page_index = max(0, min(int(page_index), total - 1))
    row = []
    if page_index > 0:
        row.append(IB('⬅️ Предыдущая', callback_data='cat_page:prev'))
    row.append(IB(f'{page_index + 1}/{total}', callback_data='none'))
    if page_index < total - 1:
        row.append(IB('Следующая ➡️', callback_data='cat_page:next'))
    kb.row(*row)
    return kb

def _category_page_text(state: dict, page_index: int) -> str:
    pages = (state or {}).get('pages') or ['']
    total = len(pages)
    page_index = max(0, min(int(page_index), total - 1))
    body = str(pages[page_index] or '').rstrip() + f'\n\n{page_index + 1}/{total}'
    return window_mark(body, str((state or {}).get('marker_code') or ''), html_mode=str((state or {}).get('parse_mode') or '').upper() == 'HTML')

def _show_category_page(chat_id: int, message_id: int, requested) -> bool:
    store = get_chat_store(int(chat_id))
    state = store.get('categories_pagination') or {}
    pages = state.get('pages') or []
    if not pages:
        return False
    current = int(state.get('page', 0) or 0)
    if requested == 'next':
        idx = current + 1
    elif requested == 'prev':
        idx = current - 1
    else:
        try:
            idx = int(requested)
        except Exception:
            idx = current
    idx = max(0, min(idx, len(pages) - 1))
    state['page'] = idx
    store['categories_pagination'] = state
    text = _category_page_text(state, idx)
    kb = _category_paged_keyboard(state, idx)
    try:
        result = fast_ui_edit_message_text(int(chat_id), int(message_id), text, reply_markup=kb, parse_mode=state.get('parse_mode') or None, purpose='category_page_v178')
        if str(result or '') not in {'ok', 'scheduled'}:
            return False
    except Exception as exc:
        log_error(f'category page edit failed {chat_id}:{message_id}: {exc}')
        return False
    store['categories_msg_id'] = int(message_id)
    save_data(data, chat_ids=[int(chat_id)])
    return True

def send_or_edit_categories_window(chat_id, text, reply_markup=None, parse_mode=None, preferred_message_id=None, marker_action: str | None=None):
    """One categories window. Long article text is split into Telegram-safe pages instead of truncation."""
    store = get_chat_store(chat_id)
    base_reply_markup = reply_markup
    try:
        marker_key = marker_action or _window_key_from_markup(base_reply_markup)
        marker_code = _window_marker_code(marker_key, 'Ф')
        body = strip_window_mark(str(text or ''))
        pages = _split_category_pages(body)
        if len(pages) > 1:
            state = {'pages': pages, 'page': 0, 'marker_code': marker_code, 'parse_mode': str(parse_mode or ''), 'base_markup': _serialize_category_markup(base_reply_markup), 'marker_action': str(marker_action or '')}
            store['categories_pagination'] = state
            text = _category_page_text(state, 0)
            reply_markup = _category_paged_keyboard(state, 0)
            try:
                bot_journal('categories_window_paginated', chat_id, f'pages={len(pages)} chars={len(body)} marker={marker_code}')
            except Exception:
                pass
        else:
            store.pop('categories_pagination', None)
            text = window_mark(body, marker_code, html_mode=str(parse_mode or '').upper() == 'HTML')
    except Exception:
        pass
    store['categories_refresh_state'] = {'marker_action': marker_action or '', 'callbacks': _markup_callback_values(base_reply_markup)}
    mid = store.get('categories_msg_id')
    candidates = []
    if preferred_message_id is not None:
        try:
            candidates.append(int(preferred_message_id))
        except Exception:
            pass
    if mid:
        try:
            mid_int = int(mid)
            if mid_int not in candidates:
                candidates.append(mid_int)
        except Exception:
            pass
    for target_id in candidates:
        try:
            result = fast_ui_edit_message_text(chat_id, target_id, text, reply_markup=reply_markup, parse_mode=parse_mode, purpose='categories_window_v178')
            if str(result or '') in {'ok', 'scheduled'}:
                store['categories_msg_id'] = target_id
                register_open_window(chat_id, target_id, 'categories', code=marker_action or '')
                save_data(data, chat_ids=[int(chat_id)])
                return target_id
            if str(result or '') != 'not_found':
                continue
            if store.get('categories_msg_id') == target_id:
                unregister_open_window(chat_id, target_id)
                store['categories_msg_id'] = None
                save_data(data, chat_ids=[int(chat_id)])
        except Exception as e:
            log_error(f'send_or_edit_categories_window edit failed {chat_id}:{target_id}: {e}')
    sent = bot.send_message(chat_id, text, reply_markup=reply_markup, parse_mode=parse_mode)
    store['categories_msg_id'] = sent.message_id
    register_open_window(chat_id, sent.message_id, 'categories', code=marker_action or '')
    save_data(data, chat_ids=[int(chat_id)])
    return sent.message_id

def open_report_window(chat_id: int, month_key: str=None, message_id: int=None):
    """
    Открывает или обновляет отдельное окно отчёта без размножения сообщений.
    """
    text, month_key = build_month_report_text(chat_id, month_key)
    kb = build_report_keyboard(month_key)
    store = get_chat_store(chat_id)
    if message_id and (not store.get('report_window_id')):
        store['report_window_id'] = message_id
    final_id = send_or_edit_stored_window(chat_id, 'report_window_id', text, reply_markup=kb, parse_mode='HTML', delay=None)
    store['report_window_id'] = final_id
    store['report_month'] = month_key
    save_data(data)

def build_owner_instruction_text() -> str:
    return '📘 Инструкция по кнопкам\n\n🏠 Основное финансовое окно\n⬅️ День / День ➡️ — перейти на соседний день. 📅 Сегодня — вернуться к текущей дате.\n📅 Дата — открыть календарь; в календаре можно менять месяц и год.\n📊 Отчёт — месячный отчёт. 🧮 Итог — общий итог. 🏦 с ост — остаток после каждого расхода.\n✏️ Изменить / 🗑 Удалить — работа с финансовыми записями. 📦 Статьи — расходы по категориям.\n📄 CSV — окно Ф47: пять периодов; в каждой строке Период / CSV / Excel / Excel статьи. Точный период открывается отдельной кнопкой ниже.\n\n💱 Валюта\nARS — отдельный учёт в песо. ARS-USD — тот же ARS с эквивалентом по курсу. USD — отдельный долларовый учёт со всеми финансовыми функциями.\n/ost — включает или выключает подпись «ост:» в окне остатка.\n\n💰Перес\nОбычно — бот-копия без кнопки и без /izm_R. Кнопка — под копией появляется ✏️ Изменить. Слеш — в текст копии добавляется /izm_R. При переключении обновляются существующие копии от открытой даты до сегодня.\n\n🔐 Секрет\nСекрет у выбранного чата — включает тотальный секрет именно для этого чата. В секрет участвуют и созданные ботом копии. 🪷 Маска — показывает нейтральное сообщение вместо удалённого секретного сообщения.\n\n📦 Статьи\nФ110 — точный диапазон операций; 💵 USD включает долларовое отображение статей. ↕️ Расположение открывает Ф152: сначала выберите статью, затем номер новой позиции.\n📚 Описание статей — ключевые слова категорий. ➕/✏️/🗑 — добавить, изменить или удалить пользовательскую статью.\n\nℹ️ INFO\n📓 Журнал / 🗂 Журналы чатов — журналы действий. Кнопки в текущем окне — режим обновления интерфейса. Финансы — настройка финансового режима.\n💵 Доллар — выбор ARS / ARS-USD / USD. 💰Перес — оформление бот-копий. Финансы-кнопки — записи как inline-кнопки.\n☁️ MEGA — приоритет резервного копирования. ⏱ Внутренние таймеры — единые таймеры обычных режимов. 🚦 Очереди — очереди и диспетчер-свидетель.\n\n📤 Пересылка\nМеню пересылки задаёт связанные чаты и финансовую обработку копий. Режим «как у владельца» создаёт отдельный owner scope: настройки такого владельца сохраняются независимо.\n\n💾 Сохранение\nПосле финансового изменения данные сначала сохраняются, затем ставится быстрый backup, после чего обновляются связанные открытые окна и планируется полный backup. В v106 содержательные message/edited_message, включая части Telegram-альбомов, сначала фиксируются маленьким task-файлом в MEGA. Задача пересылки не получает done, пока для исходного сообщения не подтверждены все требуемые направления и, при включённом финучёте, финансовая запись назначения. При deploy pending/running поднимаются из MEGA; потерянный RAM-коллектор альбома ремонтируется по сохранённому update. Callback-кнопки навигации остаются быстрыми.'

def build_owner_instruction_keyboard(chat_id: int):
    kb = types.InlineKeyboardMarkup()
    kb.row(IB('🚦 Очереди', callback_data='info_queues'))
    kb.row(IB('🔙 Назад в Инфо', callback_data=f"d:{get_chat_store(chat_id).get('current_view_day', today_key())}:info"))
    kb.row(IB('❌ Закрыть', callback_data='info_close'))
    return kb

def all_task_pool_stats() -> list[dict]:
    return [WEBHOOK_TASK_POOL.stats(), FAST_UI_TASK_POOL.stats(), UI_TASK_POOL.stats(), CALLBACK_ACK_TASK_POOL.stats(), RECOVERY_TASK_POOL.stats(), REMINDER_TASK_POOL.stats(), FINANCE_TASK_POOL.stats(), FIN_FORWARD_TASK_POOL.stats(), FORWARD_TASK_POOL.stats(), DELTA_TASK_POOL.stats(), BACKUP_TASK_POOL.stats(), EXPORT_TASK_POOL.stats(), GENERAL_TASK_POOL.stats(), MAINTENANCE_TASK_POOL.stats(), JOURNAL_TASK_POOL.stats(), DELAYED_TASK_POOL.stats(), DOZVON_TASK_POOL.stats()]

def build_queue_status_text() -> str:
    lines = ['🚦 Очереди и нагрузка', '']
    for st in all_task_pool_stats():
        lines.append(f"{st['name']}: {st['active']}/{st['workers']} работают, ожидают {st['pending']}, ключей {st['keys']}, отказов {st['rejected']}, ошибок {st['failed']}, max ожидание {st['max_wait']}с")
    with timer_lock:
        lines.append('')
        lines.append(f'Таймеров полного бэкапа: {len(_backup_timers)}')
        lines.append(f'Таймеров delta: {len(_quick_backup_timers)}')
        lines.append(f'Dirty чатов: {len(_backup_dirty_chats)}')
    with _delta_state_lock:
        lines.append(f'Delta pending chats: {len(_delta_pending_chats)}')
        lines.append(f"Global full pending: {('да' if _global_snapshot_pending else 'нет')}")
    ds = DELAYED_SCHEDULER.stats()
    lines.append(f"Планировщик: задач {ds['scheduled']}, отменено {ds['cancelled']}, выполнено {ds['executed']}")
    uds = UPDATE_DISPATCHER.stats()
    lines.append(f"Диспетчер-свидетель: pending {uds['pending']}, oldest {uds['oldest']}с, готово {uds['completed']}, повторы {uds['duplicates']}, timeout {uds['timeouts']}, retry {uds['retries']}, ACK ждёт до {uds['ack_wait']}с")
    mts = mega_task_registry_stats() if 'mega_task_registry_stats' in globals() else {}
    lines.append(f"☁️ MEGA-задачи: pending {mts.get('pending', 0)}, running {mts.get('running', 0)}, failed {mts.get('failed', 0)}, done {mts.get('done', 0)}, сейчас {mts.get('processing', 0)}")
    lines.append(f"MEGA task: сохранено {mts.get('persisted', 0)}, восстановлено {mts.get('recovered', 0)}, уже выполнено {mts.get('skipped_done', 0)}, ошибки записи {mts.get('persist_errors', 0)}, ошибки финализации {mts.get('finalize_errors', 0)}")
    if mts.get('last_error'):
        lines.append(f"Последняя ошибка MEGA task: {str(mts.get('last_error'))[:180]}")
    lines.append(f'Excel-бэкап всех чатов: {backup_excel_all_label()}')
    lines.append(f'Telegram общий интервал: {TELEGRAM_GLOBAL_MIN_GAP:.3f}с')
    return '\n'.join(lines)
CHAT_JOURNAL_PAGE_SIZE = 20

def _journal_chat_items():
    try:
        return _collect_known_chat_items()
    except Exception:
        items = []
        for cid in (data.get('chats', {}) or {}).keys():
            try:
                items.append((int(cid), get_chat_display_name(int(cid))))
            except Exception:
                pass
        return sorted(items, key=lambda x: str(x[1]).lower())

def build_chat_journal_menu_text(page: int=0) -> str:
    items = _journal_chat_items()
    pages = max(1, (len(items) + CHAT_JOURNAL_PAGE_SIZE - 1) // CHAT_JOURNAL_PAGE_SIZE)
    page = max(0, min(int(page), pages - 1))
    enabled = sum((1 for cid, _ in items if is_chat_journal_enabled(cid)))
    return wm_owner(f'📓 Журналы по чатам\n\nОбщий журнал по умолчанию выключен. Здесь можно включать запись только для нужных чатов.\n\nВключено: {enabled} из {len(items)}\nСтраница: {page + 1}/{pages}', 9)

def build_chat_journal_menu_keyboard(page: int=0):
    items = _journal_chat_items()
    pages = max(1, (len(items) + CHAT_JOURNAL_PAGE_SIZE - 1) // CHAT_JOURNAL_PAGE_SIZE)
    page = max(0, min(int(page), pages - 1))
    start = page * CHAT_JOURNAL_PAGE_SIZE
    chunk = items[start:start + CHAT_JOURNAL_PAGE_SIZE]
    kb = types.InlineKeyboardMarkup(row_width=1)
    for cid, title in chunk:
        icon = '✅' if is_chat_journal_enabled(cid) else '⬜'
        kb.row(IB(f'{icon} 📓 {chat_button_title(cid, title)}', callback_data=f'journal_chat_toggle:{cid}:{page}'))
    if pages > 1:
        row = []
        if page > 0:
            row.append(IB('⬅️', callback_data=f'journal_chats_open:{page - 1}'))
        row.append(IB(f'{page + 1}/{pages}', callback_data='none'))
        if page + 1 < pages:
            row.append(IB('➡️', callback_data=f'journal_chats_open:{page + 1}'))
        kb.row(*row)
    kb.row(IB('🔙 Назад в Инфо', callback_data='journal_chats_back'))
    return kb

def current_bot_sender_name() -> str:
    """Имя Telegram-бота, который прислал меню. Кэшируем, чтобы не дергать API на каждую кнопку."""
    try:
        global _BOT_DISPLAY_NAME_CACHE
    except Exception:
        pass
    try:
        cached = globals().get('_BOT_DISPLAY_NAME_CACHE')
        if cached:
            return str(cached)
        me = bot.get_me()
        first = str(getattr(me, 'first_name', '') or '').strip()
        username = str(getattr(me, 'username', '') or '').strip().lstrip('@')
        value = first or (f'@{username}' if username else 'Telegram bot')
        if username and first:
            value = f'{first} (@{username})'
        globals()['_BOT_DISPLAY_NAME_CACHE'] = value
        return value
    except Exception:
        username = get_bot_username_cached() if 'get_bot_username_cached' in globals() else ''
        return f'@{username}' if username else 'Telegram bot'

def bot_file_identity_lines() -> list[str]:
    return [f'🤖 Бот: {current_bot_sender_name()}', f'📄 Файл: {BOT_FILE_NAME}', f'🏷 Версия: {VERSION}']

def _keepalive_fmt(seconds: int) -> str:
    try:
        sec = max(0, int(seconds or 0))
    except Exception:
        sec = 0
    if sec and sec % 60 == 0:
        return f'{sec // 60} мин'
    return f'{sec} сек'

def _keepalive_countdown(seconds: float) -> str:
    try:
        sec = max(0, int(round(float(seconds or 0))))
    except Exception:
        sec = 0
    m, s = divmod(sec, 60)
    return f'{m} мин {s:02d} сек' if m else f'{s} сек'

def _toggle_state(enabled: bool) -> str:
    return '✅ ВКЛ' if bool(enabled) else '⬜ ВЫКЛ'

def keep_alive_status_text() -> str:
    """Combined owner diagnostic retained for compatibility and journal links."""
    state = globals().get('KEEP_ALIVE_STATE') or {}
    self_on = bool(globals().get('keepalive_self_enabled', lambda: KEEP_ALIVE_ENABLED)())
    self_sec = int(globals().get('keepalive_self_interval_seconds', lambda: KEEP_ALIVE_INTERVAL_SECONDS)())
    auto_on = bool(globals().get('keepalive_auto_enabled', lambda: True)())
    auto_idle = int(globals().get('keepalive_auto_idle_seconds', lambda: 720)())
    auto_state = globals().get('keepalive_auto_runtime_state', lambda: {})() or {}
    peer_on = bool(globals().get('keepalive_peer_enabled', lambda: False)())
    peer_sec = int(globals().get('keepalive_peer_interval_seconds', lambda: 600)())
    peer_url = str(globals().get('keepalive_peer_target_url', lambda: '')() or '')
    mode = str(auto_state.get('mode') or '')
    if mode == 'standby_manual':
        auto_now = '⬜ резерв не нужен — ручной self-ping активен'
    elif mode == 'standby_peer':
        auto_now = '⬜ ожидание — второй Render присылает ping'
    elif mode == 'standby_external':
        auto_now = '⬜ ожидание — есть внешний входящий трафик'
    elif mode == 'due':
        auto_now = '✅ порог достигнут — резервный self-ping сейчас сработает'
    else:
        auto_now = '⬜ авторежим выключен'
    lines = ['💓 ЗАЩИТА ОТ СНА / ПЕЛЕНГ', '', f'Ручной самопеленг: {_toggle_state(self_on)} · {_keepalive_fmt(self_sec)}', f'Авторежим-резерв: {_toggle_state(auto_on)} · порог {_keepalive_fmt(auto_idle)}', f'Авторежим сейчас: {auto_now}', f'Основной → второй Render: {_toggle_state(peer_on)} · {_keepalive_fmt(peer_sec)}', f"Второй сервис: {peer_url or 'адрес не задан'}", '', f"Последний self-ping: {state.get('last_ok_at') or 'ещё не было'}", f"Последний основной → второй: {state.get('peer_last_ok_at') or 'ещё не было'}", f"Последний второй → основной: {state.get('peer_received_at') or 'НЕ ОБНАРУЖЕН'}", f"Последний внешний запрос: {state.get('last_inbound_activity_at') or 'ещё не было'} · {state.get('last_inbound_activity_kind') or '—'}", f"Последний авто-self-ping: {state.get('auto_last_trigger_at') or 'ещё не было'}", f"Self ошибки: {state.get('fail_count', 0)}; peer ошибки: {state.get('peer_fail_count', 0)}", '', 'Авторежим — страховка: пока второй Render/Telegram/внешние запросы приходят, он молчит. Если трафик пропал, self-ping срабатывает до 15-минутного порога сна Render.', '', mega_traffic_stats_text(compact=True) if 'mega_traffic_stats_text' in globals() else 'MEGA traffic counter unavailable']
    return wm_owner('\n'.join(lines), 9)

def keepalive_self_status_text() -> str:
    state = globals().get('KEEP_ALIVE_STATE') or {}
    enabled = bool(globals().get('keepalive_self_enabled', lambda: KEEP_ALIVE_ENABLED)())
    seconds = int(globals().get('keepalive_self_interval_seconds', lambda: KEEP_ALIVE_INTERVAL_SECONDS)())
    auto_enabled = bool(globals().get('keepalive_auto_enabled', lambda: True)())
    auto_idle = int(globals().get('keepalive_auto_idle_seconds', lambda: 720)())
    auto_state = globals().get('keepalive_auto_runtime_state', lambda: {})() or {}
    mode = str(auto_state.get('mode') or '')
    if mode == 'standby_manual':
        auto_runtime = '⬜ ОЖИДАНИЕ — ручной самопеленг уже работает'
    elif mode == 'standby_peer':
        auto_runtime = '⬜ ОЖИДАНИЕ — ping второго Render приходит'
    elif mode == 'standby_external':
        auto_runtime = '⬜ ОЖИДАНИЕ — есть входящие запросы'
    elif mode == 'due':
        auto_runtime = '✅ СРАБАТЫВАЕТ — внешних запросов давно нет'
    else:
        auto_runtime = '⬜ ВЫКЛ'
    due = _keepalive_countdown(auto_state.get('due_in_seconds', 0))
    return wm_owner(f"💓 САМОПЕЛЕНГ RENDER\n\nРучной режим: {_toggle_state(enabled)}\nИнтервал ручного режима: {_keepalive_fmt(seconds)}\nАдрес: {APP_URL or 'не задан'}\n\nАвторежим-резерв: {_toggle_state(auto_enabled)}\nПорог без входящего трафика: {_keepalive_fmt(auto_idle)}\nСостояние авторежима: {auto_runtime}\nДо резервного self-ping: {(due if auto_enabled and (not enabled) else '—')}\nПоследний внешний запрос: {state.get('last_inbound_activity_at') or 'ещё не было'}\nИсточник: {state.get('last_inbound_activity_kind') or '—'}\nПоследний auto self-ping: {state.get('auto_last_trigger_at') or 'ещё не было'}\n\nПоследний self успех: {state.get('last_ok_at') or 'ещё не было'}\nПоследний HTTP: {state.get('last_status_code') or '—'}\nОшибок: {state.get('fail_count', 0)}\nПоследняя ошибка: {state.get('last_error') or 'нет'}\n\nРучной режим работает как раньше. Авторежим — независимая страховка: если ручной режим выключен и второй Render/Telegram/другие входящие запросы перестали приходить, бот сам делает один маленький HEAD /keepalive до засыпания Render. Когда входящий ping возвращается, авторежим автоматически снова ждёт и лишних self-запросов не делает.", 9)

def build_keepalive_self_keyboard(chat_id: int):
    enabled = bool(globals().get('keepalive_self_enabled', lambda: KEEP_ALIVE_ENABLED)())
    auto_enabled = bool(globals().get('keepalive_auto_enabled', lambda: True)())
    seconds = int(globals().get('keepalive_self_interval_seconds', lambda: KEEP_ALIVE_INTERVAL_SECONDS)())
    auto_idle = int(globals().get('keepalive_auto_idle_seconds', lambda: 720)())
    kb = types.InlineKeyboardMarkup(row_width=1)
    kb.row(IB(f"{('✅' if enabled else '⬜')} Ручной самопеленг", callback_data='keepalive_self_toggle'))
    kb.row(IB(f"{('✅' if auto_enabled else '⬜')} Авторежим-резерв", callback_data='keepalive_auto_toggle'))
    kb.row(IB(f'⏱ Ручной интервал: {_keepalive_fmt(seconds)}', callback_data='keepalive_self_interval'))
    kb.row(IB(f'🛡 Порог авторежима: {_keepalive_fmt(auto_idle)}', callback_data='keepalive_auto_interval'))
    kb.row(IB('🧪 Пеленговать себя сейчас', callback_data='keepalive_self_now'))
    kb.row(IB('🛰 Взаимный пеленг', callback_data='keepalive_peer'))
    kb.row(IB('🔙 Назад в Инфо', callback_data='journal_back'))
    return kb

def build_keepalive_interval_keyboard(kind: str, chat_id: int):
    kind = str(kind or 'self')
    if kind == 'peer':
        current = int(globals().get('keepalive_peer_interval_seconds', lambda: 600)())
        choices = tuple(globals().get('KEEPALIVE_SAFE_INTERVALS') or (300, 480, 600, 720, 840))
        prefix = 'keepalive_peer_set'
        back = 'keepalive_peer'
    elif kind == 'auto':
        current = int(globals().get('keepalive_auto_idle_seconds', lambda: 720)())
        choices = tuple(globals().get('KEEPALIVE_AUTO_SAFE_IDLE_SECONDS') or (600, 660, 720, 780, 840))
        prefix = 'keepalive_auto_set'
        back = 'keepalive_status'
    else:
        current = int(globals().get('keepalive_self_interval_seconds', lambda: 600)())
        choices = tuple(globals().get('KEEPALIVE_SAFE_INTERVALS') or (300, 480, 600, 720, 840))
        prefix = 'keepalive_self_set'
        back = 'keepalive_status'
    kb = types.InlineKeyboardMarkup(row_width=2)
    buttons = []
    for sec in choices:
        sec = int(sec)
        label = ('✅ ' if sec == current else '⬜ ') + _keepalive_fmt(sec)
        buttons.append(IB(label, callback_data=f'{prefix}:{sec}'))
    for i in range(0, len(buttons), 2):
        kb.row(*buttons[i:i + 2])
    kb.row(IB('🔙 Назад', callback_data=back))
    return kb

def keepalive_peer_status_text() -> str:
    state = globals().get('KEEP_ALIVE_STATE') or {}
    enabled = bool(globals().get('keepalive_peer_enabled', lambda: False)())
    seconds = int(globals().get('keepalive_peer_interval_seconds', lambda: 600)())
    peer_url = str(globals().get('keepalive_peer_target_url', lambda: '')() or '')
    incoming = state.get('peer_received_at') or 'НЕ ОБНАРУЖЕН'
    return wm_owner(f"🛰 ВЗАИМНЫЙ ПЕЛЕНГ / ВТОРОЙ RENDER\n\nОсновной бот → второй Render: {_toggle_state(enabled)}\nИнтервал исходящего пинга: {_keepalive_fmt(seconds)}\nАдрес второго Render: {peer_url or 'НЕ ЗАДАН'}\nПоследний успех основной → второй: {state.get('peer_last_ok_at') or 'ещё не было'}\n\nВторой Render → основной бот: {('✅ ПИНГ ПРИХОДИТ' if state.get('peer_received_at') else '⬜ ПИНГ ЕЩЁ НЕ ОБНАРУЖЕН')}\nПоследний входящий ping второго: {incoming}\nПоследняя исходящая ошибка: {state.get('peer_last_error') or 'нет'}\n\nЭто два независимых направления. Переключатель ниже управляет только Основной → второй. Направление Второй → основной задаётся TARGET_URL/PING_INTERVAL_SECONDS в peer_watchdog на втором Render. Входящий ping второго автоматически подавляет резервный auto-self-ping, пока приходит вовремя.", 9)

def build_keepalive_peer_keyboard(chat_id: int):
    enabled = bool(globals().get('keepalive_peer_enabled', lambda: False)())
    seconds = int(globals().get('keepalive_peer_interval_seconds', lambda: 600)())
    peer_url = str(globals().get('keepalive_peer_target_url', lambda: '')() or '')
    kb = types.InlineKeyboardMarkup(row_width=1)
    kb.row(IB(f"{('✅' if enabled else '⬜')} Основной → второй Render", callback_data='keepalive_peer_toggle'))
    kb.row(IB(f'⏱ Интервал: {_keepalive_fmt(seconds)}', callback_data='keepalive_peer_interval'))
    kb.row(IB('🔗 Изменить адрес второго сервиса' if peer_url else '🔗 Задать адрес второго сервиса', callback_data='keepalive_peer_url'))
    if peer_url:
        kb.row(IB('🧹 Очистить адрес', callback_data='keepalive_peer_clear'))
    kb.row(IB('🧪 Пеленговать второй сейчас', callback_data='keepalive_peer_now'))
    kb.row(IB('💓 Самопеленг / авторежим', callback_data='keepalive_status'))
    kb.row(IB('🔙 Назад в Инфо', callback_data='journal_back'))
    return kb
_EXPENSE_SHORTCUT_LOCK = threading.RLock()
_EXPENSE_SHORTCUT_EVENT_LIMIT = 200
_EXPENSE_SHORTCUT_RETRY_SECONDS = 30.0

def _expense_shortcut_root() -> dict:
    return data.setdefault('_global_settings', {}).setdefault('expense_shortcut', {})

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

def expense_shortcut_url() -> str:
    cfg = expense_shortcut_config(True)
    base = str(WEBHOOK_URL or APP_URL or '').strip().rstrip('/')
    if not base:
        return ''
    return f"{base}/expense-ping/{cfg.get('token')}"

def expense_shortcut_set_target(chat_id: int):
    with _EXPENSE_SHORTCUT_LOCK:
        cfg = expense_shortcut_config(True)
        cfg['target_chat_id'] = int(chat_id)
        _expense_shortcut_persist()
    return int(chat_id)

def expense_shortcut_regenerate_token() -> str:
    with _EXPENSE_SHORTCUT_LOCK:
        cfg = expense_shortcut_config(True)
        cfg['token'] = secrets.token_urlsafe(24)
        _expense_shortcut_persist()
        return str(cfg['token'])

def _expense_shortcut_find_event(event_id: str):
    cfg = expense_shortcut_config(True)
    for row in cfg.get('events') or []:
        if str((row or {}).get('id')) == str(event_id):
            return row
    return None

def _expense_shortcut_cleanup_events_locked(cfg: dict):
    events = list(cfg.get('events') or [])
    pending = [e for e in events if str((e or {}).get('status')) != 'sent']
    sent = [e for e in events if str((e or {}).get('status')) == 'sent'][-80:]
    cfg['events'] = (pending + sent)[-_EXPENSE_SHORTCUT_EVENT_LIMIT:]

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

def schedule_expense_ping_recovery(delay: float=1.0):

    def _job():
        cfg = expense_shortcut_config(False)
        for row in list((cfg or {}).get('events') or []):
            if str((row or {}).get('status')) != 'sent' and row.get('id'):
                GENERAL_TASK_POOL.submit(f"expense-ping:{row.get('id')}", _deliver_expense_ping_event, str(row.get('id')))
    DELAYED_SCHEDULER.schedule('expense-ping-recovery', max(0.1, float(delay)), _job)

def build_expense_shortcut_text(chat_id: int) -> str:
    cfg = expense_shortcut_config(True)
    target = int(cfg.get('target_chat_id') or OWNER_ID or chat_id)
    url = expense_shortcut_url()
    pending = sum((1 for e in cfg.get('events') or [] if str((e or {}).get('status')) != 'sent'))
    url_text = html.escape(url) if url else 'APP_URL/WEBHOOK_URL не определён'
    return f"📱 Быстрый расход с iPhone\n\nЧат назначения: {html.escape(get_chat_display_name(target))}\nID: <code>{target}</code>\nОжидают доставки: {pending}\nКнопки в сообщении: {('✅ ВКЛ' if expense_quick_buttons_enabled() else '⬜ ВЫКЛ')}\nПодхвачены отметки за 2 дня: {html.escape(str(_expense_inbox_root().get('recent_event_migration_v142_at') or 'ещё нет'))}\n\nСкопируйте эту личную ссылку в приложение «Команды»:\n<code>{url_text}</code>\n\nТройное касание задней панели запустит команду, а бот отправит «💸 Был расход». Ссылка секретная: не публикуйте её."

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

def build_journal_v208_menu_text() -> str:
    """Compact Telegram-safe menu; the full journal remains available as a file.

    v208 appended a ~3900-char tail to the status block, which deterministically
    crossed Telegram's 4096-char edit limit and made 📓 Журнал look unresponsive.
    """
    try:
        status = journal_v208_status_text()
    except Exception:
        status = '📓 Диагностический журнал'
    try:
        tail = format_journal_text(24)
    except Exception:
        tail = ''
    max_total = 3400
    tail_budget = 2100
    if len(tail) > tail_budget:
        tail = '…\n' + tail[-(tail_budget - 2):]
    header = '\n\n──────── Последние действия (компактно) ────────\n'
    text = status + (header + tail if tail else '')
    if len(text) > max_total:
        base = status + (header if tail else '')
        room = max(0, max_total - len(base))
        text = base + ('…\n' + tail[-max(0, room - 2):] if room and tail else '')
    return text[:max_total]

def build_journal_v208_menu_keyboard(chat_id: int):
    kb = types.InlineKeyboardMarkup(row_width=2)
    kb.row(IB(journal_toggle_label(), callback_data='journal_toggle_open'), IB('✅ MEGA gzip' if journal_compact_remote_effective_enabled() else '⬜ MEGA gzip', callback_data='journal_compact_toggle'))
    kb.row(IB(f'⏱ Batch: {journal_compact_interval_seconds() // 60} мин', callback_data='journal_compact_interval_menu'), IB('✅ Telegram API verbose' if verbose_telegram_journal_enabled() else '⬜ Telegram API verbose', callback_data='journal_verbose_toggle'))
    kb.row(IB('📄 Полный диагностический журнал', callback_data='journal_file'))
    kb.row(IB('📓 Журнал текущей версии', callback_data='journal_current_file'))
    _jfull = journal_download_base_name_for('full')
    _jf = _jfull if len(_jfull) <= 24 else _jfull[:21] + '…'
    _jcur = journal_download_base_name_for('current')
    _jc = _jcur if len(_jcur) <= 24 else _jcur[:21] + '…'
    kb.row(IB(f'✏️ Общий журнал: {_jf}', callback_data='journal_name_edit:full'))
    kb.row(IB(f'✏️ Текущий журнал: {_jc}', callback_data='journal_name_edit:current'))
    kb.row(IB('🤖 Скачать бот текущего деплоя', callback_data='journal_bot_source'))
    day = get_chat_store(int(chat_id)).get('current_view_day') or today_key()
    kb.row(IB('🔙 Назад', callback_data='journal_back'), IB('⬅️ Основное', callback_data=f'd:{day}:back_main'), IB('❌ Закрыть', callback_data='info_close'))
    return kb

def _v177_legacy_0216_build_info_keyboard(chat_id: int):
    kb = types.InlineKeyboardMarkup()
    layout = version_mode_layout()
    if is_owner_chat(chat_id):
        kb.row(IB('📓 Журнал', callback_data='journal_open'), IB(journal_toggle_label(), callback_data='journal_toggle'))
        if version_mode_feature('per_chat_journal'):
            kb.row(IB('🗂 Журналы чатов', callback_data='journal_chats_open'), IB(chat_journal_toggle_label(chat_id), callback_data=f'journal_chat_toggle:{chat_id}:0'))
        kb.row(IB(buttons_current_window_label(chat_id), callback_data='buttons_current_toggle'), IB(info_finance_toggle_label(chat_id), callback_data='info_finance_off'))
        if version_mode_feature('forward_copy_edit'):
            kb.row(IB(forward_copy_edit_mode_label(chat_id), callback_data='forward_copy_edit_mode_toggle'))
        kb.row(IB(forward_menu_style_label(chat_id), callback_data='forward_menu_style_toggle'), IB(icon_button_mode_label(chat_id), callback_data='icon_buttons_toggle'))
        kb.row(IB('🛡 Guard: ВКЛ — нажать отключить' if RESTORE_GUARD_ACTIVE else '🛡 Guard: ВЫКЛ — автобэкапы разрешены', callback_data='restore_guard_toggle'))
        kb.row(IB('☁️ Обновить JSON из MEGA', callback_data='mega_manual_restore'))
        kb.row(IB(total_secret_mask_label(chat_id), callback_data='total_secret_mask_toggle'), IB(f'🕔 {finance_day_start_label(chat_id)}', callback_data='finance_day5_toggle'))
        if version_mode_feature('mega_priority') and layout in {'v82', 'v83'}:
            kb.row(IB(mega_backup_priority_label(chat_id), callback_data='mega_priority_toggle'))
        elif version_mode_feature('mega_priority') and layout in {'v84', 'v85', 'v86', 'v87'}:
            kb.row(IB(mega_backup_priority_label(chat_id), callback_data='mega_priority_toggle'), IB(main_financial_value_buttons_label(chat_id), callback_data='main_financial_values_toggle'))
        if layout in {'v85', 'v86', 'v87'}:
            if layout == 'v87':
                kb.row(IB(gomonk_info_label(chat_id), callback_data=f'gomonk_open:{_gomonk_currency(chat_id)}'), IB(currency_mode_label(chat_id), callback_data='currency_menu'))
            elif layout == 'v86':
                kb.row(IB(gomonk_info_label(chat_id), callback_data=f'gomonk_open:{_gomonk_currency(chat_id)}'), IB(usd_display_label(chat_id), callback_data='usd_display_toggle'))
            else:
                kb.row(IB(gomonk_info_label(chat_id), callback_data=f'gomonk_open:{_gomonk_currency(chat_id)}'))
        if layout == 'v83':
            kb.row(IB(main_article_buttons_label(chat_id), callback_data='main_articles_toggle'))
        if version_mode_feature('keepalive_menu'):
            kb.row(IB('💓 Самопеленг', callback_data='keepalive_status'), IB('🛰 Второй сервер', callback_data='keepalive_peer'))
        kb.row(IB('⏱ Внутренние таймеры', callback_data='internal_timers'))
        kb.row(IB('☁️ Google Чт–Ср', callback_data=f'v169:gmenu:{int(chat_id)}'))
        kb.row(IB('📱 Быстрый расход iPhone', callback_data='expense_shortcut_info'))
        kb.row(IB(expense_quick_buttons_label(), callback_data='expense_quick_buttons_toggle'), IB(reminder_ui_mode_label(), callback_data='reminder_ui_mode_toggle'))
        kb.row(IB('⚠️ Неразобранные расходы', callback_data='expense_inbox_open'), IB('⚙️ Процессы', callback_data='process_center'))
        kb.row(IB(safety_profile_label(), callback_data='safety_profile_toggle'), IB('🧯 Проблемные задачи', callback_data='problem_tasks'))
        kb.row(IB('🔗 Целостность финансов', callback_data='integrity_status'))
        kb.row(IB(excel_table_style_label(chat_id), callback_data='excel_style_menu'))
        kb.row(IB('📘 Инструкция', callback_data='info_instruction'), IB('🚦 Очереди', callback_data='info_queues'))
        kb.row(IB('🖥 Render / Сервер', callback_data='runtime_watcher'))
        if active_bot_behavior_profile() in {'v93_current', 'v92_current', 'v91_current', 'v90_current'}:
            kb.row(IB('🧩 Delta / snapshots', callback_data='info_delta_status'))
        if is_primary_owner(chat_id):
            kb.row(IB('👥 /owners', callback_data='additional_owners'))
    else:
        kb.row(IB(info_finance_toggle_label(chat_id), callback_data='info_finance_off'))
        if version_mode_feature('forward_copy_edit'):
            kb.row(IB(forward_copy_edit_mode_label(chat_id), callback_data='forward_copy_edit_mode_toggle'))
        if layout in {'v84', 'v85', 'v86', 'v87'}:
            kb.row(IB(main_financial_value_buttons_label(chat_id), callback_data='main_financial_values_toggle'))
        if layout in {'v85', 'v86', 'v87'}:
            if layout == 'v87':
                kb.row(IB(gomonk_info_label(chat_id), callback_data=f'gomonk_open:{_gomonk_currency(chat_id)}'), IB(currency_mode_label(chat_id), callback_data='currency_menu'))
            elif layout == 'v86':
                kb.row(IB(gomonk_info_label(chat_id), callback_data=f'gomonk_open:{_gomonk_currency(chat_id)}'), IB(usd_display_label(chat_id), callback_data='usd_display_toggle'))
            else:
                kb.row(IB(gomonk_info_label(chat_id), callback_data=f'gomonk_open:{_gomonk_currency(chat_id)}'))
        elif layout == 'v83':
            kb.row(IB(main_article_buttons_label(chat_id), callback_data='main_articles_toggle'))
        kb.row(IB('⚙️ Процессы', callback_data='process_center'))
    kb.row(IB('⬅️ Назад осн. окно', callback_data=f"d:{get_chat_store(chat_id).get('current_view_day', today_key())}:back_main"), IB('❌ Закрыть', callback_data='info_close'))
    return kb
try:
    _v177_legacy_0216_build_info_keyboard.__name__ = 'build_info_keyboard'
except Exception:
    pass

def open_info_window(chat_id: int):
    info_text = wm_common(build_info_text(chat_id), 9)
    send_or_edit_stored_window(chat_id, 'info_msg_id', info_text, reply_markup=build_info_keyboard(chat_id), parse_mode=None, delay=None)

def _expense_anchor_rows(kb, store: dict, day_key: str, callback_builder, empty_text: str='Нет расходов в этот день'):
    records = expense_anchor_records_for_day(store, day_key)
    if records:
        for rec in records:
            rid = _record_int_id(rec)
            kb.row(IB(expense_anchor_button_label(rec, store), callback_data=callback_builder(rid)))
    else:
        kb.row(IB(empty_text, callback_data='none'))
    return records

def _send_category_pick_start_record(chat_id: int, message_id: int, start_key: str):
    store = get_chat_store(chat_id)
    kb = types.InlineKeyboardMarkup(row_width=1)
    _expense_anchor_rows(kb, store, start_key, lambda rid: cat_callback(f'cat_pick_start_record:{start_key}:{rid}'))
    kb.row(IB('➡️ Продолжить с начала дня', callback_data=cat_callback(f'cat_pick_start_record:{start_key}:0')))
    dt = datetime.strptime(start_key, '%Y-%m-%d')
    kb.row(IB('🔙 Назад к календарю', callback_data=cat_callback(f'cat_pick_start:{dt.year}:{dt.month}')))
    text = f'🎯 Точное начало периода\n📅 День: {fmt_date_ddmmyy(start_key)}\n\nВыберите расход, с которого начинать расчёт, или продолжите с начала дня.'
    send_or_edit_categories_window(chat_id, text, reply_markup=kb, preferred_message_id=message_id, marker_action='cat_pick_start_record:*')

def _category_end_day_buttons_precise(start_key: str, start_rid: int, view_year: int, view_month: int):
    kb = types.InlineKeyboardMarkup(row_width=7)
    last_day = calendar.monthrange(int(view_year), int(view_month))[1]
    buttons = []
    for dnum in range(1, last_day + 1):
        day_key = _date_key_from_ymd(view_year, view_month, dnum)
        if day_key < start_key:
            buttons.append(IB('·', callback_data='none'))
        else:
            buttons.append(IB(str(dnum), callback_data=cat_callback(f'cat_pick_set_end3:{start_key}:{int(start_rid)}:{view_year}:{view_month}:{dnum}')))
    for idx in range(0, len(buttons), 7):
        kb.row(*buttons[idx:idx + 7])
    return kb

def _send_category_pick_end_precise(chat_id: int, message_id: int, start_key: str, start_rid: int, view_year: int, view_month: int):
    store = get_chat_store(chat_id)
    kb = _category_end_day_buttons_precise(start_key, start_rid, view_year, view_month)
    prev_y, prev_m = _shift_month(view_year, view_month, -1)
    next_y, next_m = _shift_month(view_year, view_month, 1)
    start_month_key = start_key[:7]
    nav = []
    if f'{prev_y:04d}-{prev_m:02d}' >= start_month_key:
        nav.append(IB('⬅️ Месяц', callback_data=cat_callback(f'cat_pick_end3:{start_key}:{int(start_rid)}:{prev_y}:{prev_m}')))
    else:
        nav.append(IB(' ', callback_data='none'))
    nav.append(IB(f'{russian_month_name(view_month)} {view_year}', callback_data='none'))
    nav.append(IB('Месяц ➡️', callback_data=cat_callback(f'cat_pick_end3:{start_key}:{int(start_rid)}:{next_y}:{next_m}')))
    kb.row(*nav)
    kb.row(IB(f'⏹ По сегодняшний день · {fmt_date_ddmmyy(today_key())}', callback_data=cat_callback(f'cat_pick_today_end:{start_key}:{int(start_rid)}')))
    start_dt = datetime.strptime(start_key, '%Y-%m-%d')
    kb.row(IB('🔙 Изменить начало', callback_data=cat_callback(f'cat_pick_set_start:{start_dt.year}:{start_dt.month}:{start_dt.day}')))
    text = f'🎯 Точный период расходов\n▶️ Начало: {exact_boundary_text(store, start_key, start_rid, True)}\n\nВыберите конечный день: {russian_month_name(view_month)} {view_year}'
    send_or_edit_categories_window(chat_id, text, reply_markup=kb, preferred_message_id=message_id, marker_action='cat_pick_end3:*')

def _send_category_pick_end_record(chat_id: int, message_id: int, start_key: str, start_rid: int, end_key: str):
    store = get_chat_store(chat_id)
    kb = types.InlineKeyboardMarkup(row_width=1)
    records = expense_anchor_records_for_day(store, end_key)
    displayed = 0
    all_recs = sorted_records_for_day(store, end_key)
    pos = {_record_int_id(r): i for i, r in enumerate(all_recs)}
    for rec in records:
        rid = _record_int_id(rec)
        if end_key == start_key and start_rid:
            if pos.get(rid, -1) < pos.get(int(start_rid), 0):
                continue
        displayed += 1
        kb.row(IB(expense_anchor_button_label(rec, store), callback_data=cat_callback(f'cat_pick_end_record:{start_key}:{int(start_rid)}:{end_key}:{rid}')))
    if not displayed:
        kb.row(IB('Нет подходящих расходов в этот день', callback_data='none'))
    kb.row(IB('✅ Продолжить до конца дня', callback_data=cat_callback(f'cat_pick_end_record:{start_key}:{int(start_rid)}:{end_key}:0')))
    end_dt = datetime.strptime(end_key, '%Y-%m-%d')
    kb.row(IB('🔙 Назад к календарю', callback_data=cat_callback(f'cat_pick_end3:{start_key}:{int(start_rid)}:{end_dt.year}:{end_dt.month}')))
    text = f'🎯 Точный конец периода\n▶️ Начало: {exact_boundary_text(store, start_key, start_rid, True)}\n📅 Конечный день: {fmt_date_ddmmyy(end_key)}\n\nВыберите последний расход, который включить в расчёт, или продолжите до конца дня.'
    send_or_edit_categories_window(chat_id, text, reply_markup=kb, preferred_message_id=message_id, marker_action='cat_pick_end_record:*')

def build_categories_record_summary_keyboard(start_key: str, start_rid: int, end_key: str, end_rid: int, store: dict):
    kb = types.InlineKeyboardMarkup(row_width=3)
    cats = calc_categories_for_record_range(store, start_key, start_rid, end_key, end_rid)
    buttons = []
    for category in get_ordered_category_names(cats=cats, store=store):
        slug = get_expense_category_slug(category, store)
        if slug:
            buttons.append(IB(_clean_category_display_name(category), callback_data=cat_callback(f'cat_show_records:{start_key}:{int(start_rid)}:{end_key}:{int(end_rid)}:{slug}')))
    add_buttons_in_rows(kb, buttons, 3)
    if _v85_enabled('usd_categories') and (not financial_view_is_usd(store)):
        usd_on = bool(store.setdefault('settings', {}).get('category_usd_enabled', False))
        kb.row(IB('✅ 💵 USD: ВКЛ' if usd_on else '⬜ 💵 USD: ВЫКЛ', callback_data=cat_callback(f'cat_usd_toggle_records:{start_key}:{int(start_rid)}:{end_key}:{int(end_rid)}')))
    kb.row(IB('↕️ Расположение', callback_data=cat_callback(f'cat_order_open_exact:{start_key}:{int(start_rid)}:{end_key}:{int(end_rid)}')))
    start_dt = datetime.strptime(start_key, '%Y-%m-%d')
    end_dt = datetime.strptime(end_key, '%Y-%m-%d')
    kb.row(IB('⬅️ Назад', callback_data=cat_callback(f'cat_pick_set_end3:{start_key}:{int(start_rid)}:{end_dt.year}:{end_dt.month}:{end_dt.day}')), IB('🎯 Выбрать заново', callback_data=cat_callback(f'cat_pick_start:{start_dt.year}:{start_dt.month}')))
    kb.row(IB('⬅️ Назад осн. окно', callback_data=f'd:{today_key()}:back_main'), IB('❌ Закрыть', callback_data=cat_callback('cat_close')))
    return kb

def build_category_record_detail_text(store: dict, start_key: str, start_rid: int, end_key: str, end_rid: int, category: str):
    items = collect_items_for_category_record_range(store, start_key, start_rid, end_key, end_rid, category)
    view_usd = financial_view_is_usd(store)
    mode = currency_mode_from_store(store)
    category_mixed = bool(not view_usd and store.setdefault('settings', {}).get('category_usd_enabled', False) and _v85_enabled('usd_categories'))
    show_rate = not view_usd and (mode != 'ars' or category_mixed)
    rate_info = usd_rate_cached() if show_rate else None
    total = sum((amount for _, amount, _ in items))
    clean_category = _clean_category_display_name(category).upper()
    lines = [f'📦 {clean_category}', f'▶️ {exact_boundary_text(store, start_key, start_rid, True)}', f'⏹ {exact_boundary_text(store, end_key, end_rid, False)}', '', f'Итого: {format_category_view_amount(store, total, category_mixed)}']
    if show_rate and rate_info:
        lines.append(f"Курс: 1 USD = {fmt_num(rate_info['rate']).lstrip('+')} ARS ({_clean_category_display_name(rate_info.get('source') or 'DolarAPI')})")
    lines.append('')
    if not items:
        lines.append('Нет операций по этой статье.')
    else:
        for day_key, amount, note in items:
            clean_note = _clean_category_display_name(str(note or '').strip())
            lines.append(f'• {fmt_date_ddmmyy(day_key)}: {format_category_view_amount(store, amount, category_mixed)} {clean_note}'.rstrip())
    return wm_common('\n'.join(lines), 8)
_category_other_sort_state = {}

def _other_sort_key(chat_id: int, start_key: str, start_rid: int, end_key: str, end_rid: int):
    return (int(chat_id), str(start_key), int(start_rid), str(end_key), int(end_rid))

def other_sort_records(store: dict, start_key: str, start_rid: int, end_key: str, end_rid: int) -> list[dict]:
    out = []
    for _day, rec in exact_record_range(store, start_key, start_rid, end_key, end_rid):
        try:
            if financial_view_amount(store, rec) >= 0:
                continue
        except Exception:
            continue
        category = resolve_expense_category_for_record(rec, store)
        if get_expense_category_slug(category, store) == 'other':
            out.append(rec)
    return out

def build_other_sort_text(store: dict, start_key: str, start_rid: int, end_key: str, end_rid: int) -> str:
    count = len(other_sort_records(store, start_key, start_rid, end_key, end_rid))
    return wm_common(f'🔀 Сортировка статьи ПРОЧЕЕ\n\nВыберите финансовые значения, которые нужно перенести в другую статью. После выбора нажмите «Выбрать их».\n\nДоступно записей: {count}', 8)

def build_other_sort_keyboard(chat_id: int, store: dict, start_key: str, start_rid: int, end_key: str, end_rid: int):
    kb = types.InlineKeyboardMarkup(row_width=1)
    key = _other_sort_key(chat_id, start_key, start_rid, end_key, end_rid)
    selected = _category_other_sort_state.setdefault(key, set())
    valid_ids = set()
    for rec in other_sort_records(store, start_key, start_rid, end_key, end_rid):
        rid = _record_int_id(rec)
        valid_ids.add(rid)
        mark = '✅' if rid in selected else '▫️'
        label = f'{mark} {financial_record_button_label(rec, chat_id)}'
        kb.row(IB(label, callback_data=cat_callback(f'cat_other_sort_toggle:{rid}:{start_key}:{int(start_rid)}:{end_key}:{int(end_rid)}')))
    selected.intersection_update(valid_ids)
    if selected:
        kb.row(IB(f'✅ Выбрать их ({len(selected)})', callback_data=cat_callback(f'cat_other_sort_choose:{start_key}:{int(start_rid)}:{end_key}:{int(end_rid)}')))
    else:
        kb.row(IB('Выберите значения выше', callback_data='none'))
    kb.row(IB('⬅️ Назад', callback_data=cat_callback(f'cat_show_records:{start_key}:{int(start_rid)}:{end_key}:{int(end_rid)}:other')))
    kb.row(IB('⬅️ Назад осн. окно', callback_data=f'd:{today_key()}:back_main'), IB('❌ Закрыть', callback_data=cat_callback('cat_close')))
    return kb

def build_other_sort_target_text(chat_id: int, start_key: str, start_rid: int, end_key: str, end_rid: int) -> str:
    key = _other_sort_key(chat_id, start_key, start_rid, end_key, end_rid)
    selected = _category_other_sort_state.get(key, set())
    return wm_common(f'📦 Куда перенести выбранные записи?\n\nВыбрано: {len(selected)}', 8)

def build_other_sort_target_keyboard(chat_id: int, store: dict, start_key: str, start_rid: int, end_key: str, end_rid: int):
    kb = types.InlineKeyboardMarkup(row_width=2)
    buttons = []
    for slug in get_expense_category_order_slugs(store):
        if slug == 'other':
            continue
        name = _clean_category_display_name(get_category_by_slug(slug, store) or slug)
        buttons.append(IB(name, callback_data=cat_callback(f'cat_other_sort_target:{slug}:{start_key}:{int(start_rid)}:{end_key}:{int(end_rid)}')))
    add_buttons_in_rows(kb, buttons, 2)
    kb.row(IB('⬅️ Назад к выбору', callback_data=cat_callback(f'cat_other_sort:{start_key}:{int(start_rid)}:{end_key}:{int(end_rid)}')))
    kb.row(IB('⬅️ Назад осн. окно', callback_data=f'd:{today_key()}:back_main'), IB('❌ Закрыть', callback_data=cat_callback('cat_close')))
    return kb

def apply_other_sort_target(store: dict, selected_ids: set[int], target_slug: str) -> int:
    changed = 0
    ids = {int(x) for x in selected_ids}
    for rec in store.get('records', []) or []:
        if _record_int_id(rec) in ids:
            rec['category_override_slug'] = str(target_slug)
            changed += 1
    for arr in (store.get('daily_records', {}) or {}).values():
        for rec in arr or []:
            if _record_int_id(rec) in ids:
                rec['category_override_slug'] = str(target_slug)
    return changed

def build_category_record_detail_keyboard(start_key: str, start_rid: int, end_key: str, end_rid: int, category: str | None=None, store: dict | None=None):
    kb = types.InlineKeyboardMarkup()
    if category and get_expense_category_slug(category, store) == 'other':
        kb.row(IB('🔀 Сортировка', callback_data=cat_callback(f'cat_other_sort:{start_key}:{int(start_rid)}:{end_key}:{int(end_rid)}')))
    kb.row(IB('⬅️ Назад', callback_data=cat_callback(f'cat_back_records:{start_key}:{int(start_rid)}:{end_key}:{int(end_rid)}')))
    kb.row(IB('⬅️ Назад осн. окно', callback_data=f'd:{today_key()}:back_main'), IB('❌ Закрыть', callback_data=cat_callback('cat_close')))
    return kb

def _category_picker_day_buttons(year: int, month: int, stage: str, start_day: int | None=None, selected_day: int | None=None):
    kb = types.InlineKeyboardMarkup(row_width=7)
    last_day = calendar.monthrange(int(year), int(month))[1]
    buttons = []
    for dnum in range(1, last_day + 1):
        label = f'✅{dnum}' if selected_day == dnum else str(dnum)
        if stage == 'start':
            cb = cat_callback(f'cat_pick_set_start:{year}:{month}:{dnum}')
        else:
            cb = cat_callback(f'cat_pick_set_end:{year}:{month}:{int(start_day or 1)}:{dnum}')
        buttons.append(IB(label, callback_data=cb))
    for i in range(0, len(buttons), 7):
        kb.row(*buttons[i:i + 7])
    return kb

def _send_category_pick_start(chat_id: int, message_id: int, year: int, month: int, selected: int | None=None):
    kb = _category_picker_day_buttons(year, month, 'start', selected_day=selected)
    if selected:
        kb.row(IB('✅ Выбрать это', callback_data=cat_callback(f'cat_pick_end:{year}:{month}:{selected}')))
    kb.row(IB('🔙 Назад', callback_data=cat_callback(f'cat_m:{year}:{month}')))
    text = f'📅 Выберите начальную дату: {month:02d}.{year}'
    if selected:
        text += f'\n✅ Начало: {selected:02d}.{month:02d}.{year}'
    send_or_edit_categories_window(chat_id, wm_common(text, 13), reply_markup=kb, preferred_message_id=message_id, marker_action='cat_pick_start:*')

def _shift_month(year: int, month: int, delta: int=0) -> tuple[int, int]:
    base = datetime(int(year), int(month), 1)
    m0 = base.year * 12 + base.month - 1 + int(delta or 0)
    y = m0 // 12
    m = m0 % 12 + 1
    return (y, m)

def _date_key_from_ymd(year: int, month: int, day: int) -> str:
    last_day = calendar.monthrange(int(year), int(month))[1]
    d = max(1, min(int(day), last_day))
    return f'{int(year):04d}-{int(month):02d}-{d:02d}'

def _category_picker_day_buttons_end_any_month(start_key: str, view_year: int, view_month: int, selected_key: str | None=None):
    kb = types.InlineKeyboardMarkup(row_width=7)
    last_day = calendar.monthrange(int(view_year), int(view_month))[1]
    buttons = []
    for dnum in range(1, last_day + 1):
        dk = _date_key_from_ymd(view_year, view_month, dnum)
        label = f'✅{dnum}' if selected_key == dk else str(dnum)
        buttons.append(IB(label, callback_data=cat_callback(f'cat_pick_set_end2:{start_key}:{int(view_year)}:{int(view_month)}:{dnum}')))
    for i in range(0, len(buttons), 7):
        kb.row(*buttons[i:i + 7])
    return kb

def _send_category_pick_end_any_month(chat_id: int, message_id: int, start_key: str, view_year: int, view_month: int, selected_end_key: str | None=None):
    start_dt = datetime.strptime(str(start_key)[:10], '%Y-%m-%d')
    kb = _category_picker_day_buttons_end_any_month(start_key, view_year, view_month, selected_key=selected_end_key)
    prev_y, prev_m = _shift_month(view_year, view_month, -1)
    next_y, next_m = _shift_month(view_year, view_month, 1)
    kb.row(IB('⬅️ Месяц', callback_data=cat_callback(f'cat_pick_end2:{start_key}:{prev_y}:{prev_m}')), IB(f'{int(view_month):02d}.{int(view_year)}', callback_data='none'), IB('Месяц ➡️', callback_data=cat_callback(f'cat_pick_end2:{start_key}:{next_y}:{next_m}')))
    if selected_end_key:
        kb.row(IB('✅ Выбрать конечное', callback_data=cat_callback(f'cat_range_custom2:{start_key}:{selected_end_key}')))
    kb.row(IB('🔙 Назад к началу', callback_data=cat_callback(f'cat_pick_set_start:{start_dt.year}:{start_dt.month}:{start_dt.day}')))
    text = f'📅 Начало: {fmt_date_ddmmyy(start_key)}\nВыберите конечную дату: {int(view_month):02d}.{int(view_year)}'
    if selected_end_key:
        text += f'\n✅ Конец: {fmt_date_ddmmyy(selected_end_key)}'
    send_or_edit_categories_window(chat_id, wm_common(text, 13), reply_markup=kb, preferred_message_id=message_id)

def _send_category_pick_end(chat_id: int, message_id: int, year: int, month: int, start_day: int, selected_end: int | None=None):
    start_key = _date_key_from_ymd(year, month, start_day)
    selected_end_key = _date_key_from_ymd(year, month, selected_end) if selected_end else None
    _send_category_pick_end_any_month(chat_id, message_id, start_key, int(year), int(month), selected_end_key)

def handle_categories_callback(call, data_str: str) -> bool:
    """UI окна расходов по статьям."""
    chat_id = call.message.chat.id
    store = get_chat_store(chat_id)
    if data_str.startswith('cat_page:'):
        requested = data_str.split(':', 1)[1] if ':' in data_str else '0'
        _show_category_page(chat_id, call.message.message_id, requested)
        try:
            bot.answer_callback_query(call.id)
        except Exception:
            pass
        return True
    if data_str == 'cat_prompt_back':
        was_edit = bool(store.get('category_edit_wait'))
        clear_category_wait_state(chat_id, 'category_add_wait', call.message.message_id, delete_prompt=False)
        clear_category_wait_state(chat_id, 'category_edit_wait', call.message.message_id, delete_prompt=False)
        if was_edit:
            send_or_edit_categories_window(chat_id, wm_common('✏️ Изменить статью\n\nВыберите статью. Б = базовая, С = своя.', 14), reply_markup=build_category_edit_keyboard(chat_id), preferred_message_id=call.message.message_id)
        else:
            return handle_categories_callback(call, 'cat_today')
        return True
    if data_str == 'cat_add_cancel':
        clear_category_wait_state(chat_id, 'category_add_wait', call.message.message_id, delete_prompt=True)
        clear_category_wait_state(chat_id, 'category_edit_wait', call.message.message_id, delete_prompt=True)
        try:
            bot.answer_callback_query(call.id, 'Команда отменена')
        except Exception:
            pass
        return True
    if data_str.startswith('cat_main_edit:'):
        try:
            parts = data_str.split(':', 2)
            slug = parts[1]
        except Exception:
            return True
        start_category_edit_wait(chat_id, chat_id, slug)
        try:
            bot.answer_callback_query(call.id, 'Редактирование статьи', show_alert=False)
        except Exception:
            pass
        return True
    if data_str == 'cat_edit_menu':
        send_or_edit_categories_window(chat_id, wm_common('✏️ Изменить статью\n\nВыберите статью. Б = базовая, С = своя. Можно менять название и ключевые слова.', 14), reply_markup=build_category_edit_keyboard(chat_id), preferred_message_id=call.message.message_id)
        return True
    if data_str.startswith('cat_edit_pick:'):
        slug = data_str.split(':', 1)[1]
        start_category_edit_wait(chat_id, chat_id, slug)
        try:
            bot.answer_callback_query(call.id, 'Напиши новую статью и ключи', show_alert=False)
        except Exception:
            pass
        return True
    if data_str == 'cat_del_menu':
        clear_category_wait_state(chat_id, 'category_add_wait', delete_prompt=False)
        clear_category_wait_state(chat_id, 'category_edit_wait', delete_prompt=False)
        store['category_delete_selection'] = []
        save_data(data)
        send_or_edit_categories_window(chat_id, wm_common('🗑 Удалить статью\n\nВыберите пользовательские статьи галочками и нажмите «Удалить выбранное». Стандартные статьи не удаляем, чтобы не ломать базовую логику.', 15), reply_markup=build_category_delete_keyboard(chat_id), preferred_message_id=call.message.message_id)
        return True
    if data_str.startswith('cat_del_toggle:'):
        slug = data_str.split(':', 1)[1]
        selected = set(store.get('category_delete_selection') or [])
        if slug in selected:
            selected.remove(slug)
        else:
            selected.add(slug)
        store['category_delete_selection'] = sorted(selected)
        save_data(data)
        send_or_edit_categories_window(chat_id, wm_common('🗑 Удалить статью\n\nВыберите пользовательские статьи галочками и нажмите «Удалить выбранное».', 15), reply_markup=build_category_delete_keyboard(chat_id), preferred_message_id=call.message.message_id)
        return True
    if data_str == 'cat_del_selected':
        selected = set(store.get('category_delete_selection') or [])
        if not selected:
            try:
                bot.answer_callback_query(call.id, 'Ничего не выбрано', show_alert=False)
            except Exception:
                pass
            return True
        count = remove_custom_expense_categories(chat_id, selected)
        try:
            bot.answer_callback_query(call.id, f'Удалено статей: {count}', show_alert=False)
        except Exception:
            pass
        return handle_categories_callback(call, 'cat_today')
    if data_str == 'cat_close':
        mid = store.get('categories_msg_id')
        if mid:
            try:
                bot.delete_message(chat_id, mid)
            except Exception:
                pass
        if mid:
            unregister_open_window(chat_id, int(mid))
        store['categories_msg_id'] = None
        store['categories_refresh_state'] = None
        store.pop('categories_pagination', None)
        save_data(data, chat_ids=[int(chat_id)])
        return True
    if data_str == 'cat_today':
        return handle_categories_callback(call, f'cat_wthu:{today_key()}')
    if data_str == 'cat_add':
        start_category_add_wait(chat_id, chat_id)
        try:
            bot.answer_callback_query(call.id, 'Напиши название и ключи статьи', show_alert=False)
        except Exception:
            pass
        return True
    if data_str == 'cat_desc':
        kb = types.InlineKeyboardMarkup()
        kb.row(IB('🔙 Назад к статьям', callback_data=cat_callback(f'cat_wthu:{today_key()}')))
        kb.row(IB('⬅️ Назад осн. окно', callback_data=f'd:{today_key()}:back_main'), IB('❌ Закрыть статьи', callback_data=cat_callback('cat_close')))
        send_or_edit_categories_window(chat_id, build_articles_description_text(chat_id), reply_markup=kb, preferred_message_id=call.message.message_id)
        return True
    if data_str.startswith('cat_wthu:'):
        ref = data_str.split(':', 1)[1] or today_key()
        start_key = week_start_thursday(ref)
        start, end = week_bounds_thu_wed(start_key)
        label = f'{fmt_date_ddmmyy(start)} — {fmt_date_ddmmyy(end)} (Чт–Ср)'
        text, _ = summarize_categories(store, start, end, label)
        kb = build_categories_summary_keyboard('wthu', start, end, store=store)
        send_or_edit_categories_window(chat_id, text, reply_markup=kb, preferred_message_id=call.message.message_id)
        return True
    if data_str.startswith('cat_wk:'):
        start_key = data_str.split(':', 1)[1].strip() or week_start_monday(today_key())
        start, end = week_bounds_from_start(start_key)
        label = f'{fmt_date_ddmmyy(start)} — {fmt_date_ddmmyy(end)} (Пн–Вс)'
        text, _ = summarize_categories(store, start, end, label)
        kb = build_categories_summary_keyboard('wk', start, end, store=store)
        send_or_edit_categories_window(chat_id, text, reply_markup=kb, preferred_message_id=call.message.message_id)
        return True
    if data_str == 'cat_months' or data_str.startswith('cat_months_y:'):
        try:
            year = int(data_str.split(':', 1)[1]) if data_str.startswith('cat_months_y:') else now_local().year
        except Exception:
            year = now_local().year
        kb = types.InlineKeyboardMarkup(row_width=2)
        month_buttons = []
        current_ym = now_local().strftime('%Y-%m')
        for m in range(1, 13):
            ym = f'{year:04d}-{m:02d}'
            label = f'📍 {russian_month_name(m)} ({m}) — текущий' if ym == current_ym else f'{russian_month_name(m)} ({m})'
            month_buttons.append(IB(label, callback_data=cat_callback(f'cat_m:{year}:{m}')))
        for i in range(0, len(month_buttons), 2):
            kb.row(*month_buttons[i:i + 2])
        kb.row(IB('⬅️ Год', callback_data=cat_callback(f'cat_months_y:{year - 1}')), IB(str(year), callback_data='none'), IB('Год ➡️', callback_data=cat_callback(f'cat_months_y:{year + 1}')))
        kb.row(IB('📅 Сегодня', callback_data=cat_callback('cat_today')), IB('⬅️ Назад осн. окно', callback_data=f'd:{today_key()}:back_main'), IB('❌ Закрыть статьи', callback_data=cat_callback('cat_close')))
        send_or_edit_categories_window(chat_id, wm_common(f'📦 Выберите месяц, год {year}:', 12), reply_markup=kb, marker_action='markup:plain')
        return True
    if data_str.startswith('cat_m:'):
        try:
            parts = data_str.split(':')
            if len(parts) >= 3:
                year, month = (int(parts[1]), int(parts[2]))
            else:
                year, month = (now_local().year, int(parts[1]))
        except Exception:
            return True
        last_day = calendar.monthrange(year, month)[1]
        kb = types.InlineKeyboardMarkup(row_width=7)
        weeks = [(1, 7), (8, 14), (15, 21), (22, last_day)]
        kb.row(*[IB(f'{a:02d}–{b:02d}', callback_data=cat_callback(f'cat_rng:{year}:{month}:{a}:{b}')) for a, b in weeks])
        kb.row(IB('📅 Произвольный период', callback_data=cat_callback(f'cat_pick_start:{year}:{month}')))
        row = []
        if month != now_local().month or year != now_local().year:
            row.append(IB('📅 Сегодня', callback_data=cat_callback('cat_today')))
        row.append(IB('🔙 Назад', callback_data=cat_callback('cat_months')))
        kb.row(*row)
        send_or_edit_categories_window(chat_id, wm_common(f'📆 Выберите неделю: {russian_month_name(month)} ({month}) {year}', 13), reply_markup=kb, marker_action='cat_m:*')
        return True
    if data_str.startswith('cat_pick_start:'):
        try:
            _, y, m = data_str.split(':')
            _send_category_pick_start(chat_id, call.message.message_id, int(y), int(m))
        except Exception as e:
            log_error(f'cat_pick_start: {e}')
        return True
    if data_str.startswith('cat_pick_set_start:'):
        try:
            _, y, m, d = data_str.split(':')
            start_key = _date_key_from_ymd(int(y), int(m), int(d))
            _send_category_pick_start_record(chat_id, call.message.message_id, start_key)
        except Exception as e:
            log_error(f'cat_pick_set_start: {e}')
        return True
    if data_str.startswith('cat_pick_start_record:'):
        try:
            _, start_key, start_rid = data_str.split(':')
            start_dt = datetime.strptime(start_key, '%Y-%m-%d')
            _send_category_pick_end_precise(chat_id, call.message.message_id, start_key, int(start_rid), start_dt.year, start_dt.month)
        except Exception as e:
            log_error(f'cat_pick_start_record: {e}')
        return True
    if data_str.startswith('cat_pick_today_end:'):
        try:
            _, start_key, start_rid = data_str.split(':')
            end_key = today_key()
            if end_key < start_key:
                end_key = start_key
            _send_category_pick_end_record(chat_id, call.message.message_id, start_key, int(start_rid), end_key)
        except Exception as e:
            log_error(f'cat_pick_today_end: {e}')
        return True
    if data_str == 'cat_pick_today_start':
        try:
            start_key = today_key()
            now_dt = now_local()
            _send_category_pick_end_precise(chat_id, call.message.message_id, start_key, 0, now_dt.year, now_dt.month)
        except Exception as e:
            log_error(f'cat_pick_today_start: {e}')
        return True
    if data_str.startswith('cat_usd_toggle_period:'):
        try:
            _, mode, start, end = data_str.split(':', 3)
            settings = store.setdefault('settings', {})
            settings['category_usd_enabled'] = not bool(settings.get('category_usd_enabled', False))
            save_data(data, chat_ids=[chat_id])
            schedule_config_backup_for_chats(chat_id)
            if settings['category_usd_enabled']:
                usd_rate_cached(force=False)
            label = f'{fmt_date_ddmmyy(start)} — {fmt_date_ddmmyy(end)}'
            text, _ = summarize_categories(store, start, end, label)
            kb = build_categories_summary_keyboard(mode, start, end, store=store)
            marker = 'cat_wthu:*' if mode == 'wthu' else 'cat_wk:*' if mode == 'wk' else 'cat_range_custom2:*'
            send_or_edit_categories_window(chat_id, text, reply_markup=kb, preferred_message_id=call.message.message_id, marker_action=marker)
        except Exception as e:
            log_error(f'cat_usd_toggle_period: {e}')
        return True

    def _refresh_layout_same_message(context: str, params: tuple, marker_action: str):
        text = build_category_layout_text(store, context)
        kb = build_category_layout_keyboard(store, context, params, chat_id=chat_id)
        final_text = window_mark(strip_window_mark(text), _window_marker_code(marker_action, 'Ф'))
        result = fast_ui_edit_message_text(chat_id, call.message.message_id, final_text, reply_markup=kb, purpose='category_layout_v178')
        if str(result or '') not in {'ok', 'scheduled'}:
            raise RuntimeError(f'category layout edit failed: {result}')
        store['categories_msg_id'] = int(call.message.message_id)
        register_open_window(chat_id, int(call.message.message_id), 'categories', code=marker_action)
        save_data(data, chat_ids=[int(chat_id)])
        return int(call.message.message_id)
    if data_str.startswith('cat_order_open_sum:'):
        try:
            _, mode, start, end = data_str.split(':', 3)
            _refresh_layout_same_message('sum', (mode, start, end), 'cat_order_open_sum:*')
        except Exception as e:
            log_error(f'cat_order_open_sum: {e}')
        return True
    if data_str.startswith('cat_order_select_sum:'):
        try:
            _, slug, mode, start, end = data_str.split(':', 4)
            params = ('sum', mode, start, end)
            key = _category_order_selection_key(chat_id, params)
            _category_order_selection[key] = slug
            _refresh_layout_same_message('sum', (mode, start, end), 'cat_order_open_sum:*')
        except Exception as e:
            log_error(f'cat_order_select_sum: {e}')
        return True
    if data_str.startswith('cat_order_position_sum:'):
        try:
            _, position, mode, start, end = data_str.split(':', 4)
            params = ('sum', mode, start, end)
            key = _category_order_selection_key(chat_id, params)
            slug = _category_order_selection.get(key)
            if not slug:
                try:
                    bot.answer_callback_query(call.id, 'Сначала выберите статью')
                except Exception:
                    pass
                return True
            moved = move_expense_category_to_position(store, slug, int(position))
            _category_order_selection.pop(key, None)
            if moved:
                save_data(data, chat_ids=[chat_id])
                schedule_quick_backup(chat_id, MEGA_DELTA_PRIORITY_DELAY_SECONDS if mega_backup_priority_enabled() else MEGA_DELTA_DELAY_SECONDS)
                schedule_config_backup_for_chats(chat_id, delay=0.4)
            _refresh_layout_same_message('sum', (mode, start, end), 'cat_order_open_sum:*')
        except Exception as e:
            log_error(f'cat_order_position_sum: {e}')
        return True
    if data_str.startswith('cat_order_move_sum:'):
        try:
            _, slug, direction, mode, start, end = data_str.split(':', 5)
            if move_expense_category_order(store, slug, direction):
                save_data(data, chat_ids=[chat_id])
                schedule_config_backup_for_chats(chat_id)
            _refresh_layout_same_message('sum', (mode, start, end), 'cat_order_open_sum:*')
        except Exception as e:
            log_error(f'cat_order_move_sum: {e}')
        return True
    if data_str.startswith('cat_order_open_exact:'):
        try:
            _, start_key, start_rid, end_key, end_rid = data_str.split(':')
            _refresh_layout_same_message('exact', (start_key, int(start_rid), end_key, int(end_rid)), 'cat_order_open_exact:*')
        except Exception as e:
            log_error(f'cat_order_open_exact: {e}')
        return True
    if data_str.startswith('cat_order_select_exact:'):
        try:
            _, slug, start_key, start_rid, end_key, end_rid = data_str.split(':', 5)
            params = (start_key, int(start_rid), end_key, int(end_rid))
            key = _category_order_selection_key(chat_id, params)
            _category_order_selection[key] = slug
            _refresh_layout_same_message('exact', params, 'cat_order_open_exact:*')
        except Exception as e:
            log_error(f'cat_order_select_exact: {e}')
        return True
    if data_str.startswith('cat_order_position_exact:'):
        try:
            _, position, start_key, start_rid, end_key, end_rid = data_str.split(':', 5)
            params = (start_key, int(start_rid), end_key, int(end_rid))
            key = _category_order_selection_key(chat_id, params)
            slug = _category_order_selection.get(key)
            if not slug:
                try:
                    bot.answer_callback_query(call.id, 'Сначала выберите статью')
                except Exception:
                    pass
                return True
            moved = move_expense_category_to_position(store, slug, int(position))
            _category_order_selection.pop(key, None)
            if moved:
                save_data(data, chat_ids=[chat_id])
                schedule_quick_backup(chat_id, MEGA_DELTA_PRIORITY_DELAY_SECONDS if mega_backup_priority_enabled() else MEGA_DELTA_DELAY_SECONDS)
                schedule_config_backup_for_chats(chat_id, delay=0.4)
            _refresh_layout_same_message('exact', params, 'cat_order_open_exact:*')
        except Exception as e:
            log_error(f'cat_order_position_exact: {e}')
        return True
    if data_str.startswith('cat_order_move_exact:'):
        try:
            _, slug, direction, start_key, start_rid, end_key, end_rid = data_str.split(':', 6)
            if move_expense_category_order(store, slug, direction):
                save_data(data, chat_ids=[chat_id])
                schedule_config_backup_for_chats(chat_id)
            _refresh_layout_same_message('exact', (start_key, int(start_rid), end_key, int(end_rid)), 'cat_order_open_exact:*')
        except Exception as e:
            log_error(f'cat_order_move_exact: {e}')
        return True
    if data_str.startswith('cat_pick_end3:'):
        try:
            _, start_key, start_rid, y, m = data_str.split(':')
            _send_category_pick_end_precise(chat_id, call.message.message_id, start_key, int(start_rid), int(y), int(m))
        except Exception as e:
            log_error(f'cat_pick_end3: {e}')
        return True
    if data_str.startswith('cat_pick_set_end3:'):
        try:
            _, start_key, start_rid, y, m, d = data_str.split(':')
            end_key = _date_key_from_ymd(int(y), int(m), int(d))
            _send_category_pick_end_record(chat_id, call.message.message_id, start_key, int(start_rid), end_key)
        except Exception as e:
            log_error(f'cat_pick_set_end3: {e}')
        return True
    if data_str.startswith('cat_pick_end_record:'):
        try:
            _, start_key, start_rid, end_key, end_rid = data_str.split(':')
            text, _ = summarize_categories_record_range(store, start_key, int(start_rid), end_key, int(end_rid))
            kb = build_categories_record_summary_keyboard(start_key, int(start_rid), end_key, int(end_rid), store)
            send_or_edit_categories_window(chat_id, text, reply_markup=kb, preferred_message_id=call.message.message_id, marker_action='cat_range_records:*')
        except Exception as e:
            log_error(f'cat_pick_end_record: {e}')
        return True
    if data_str.startswith('cat_usd_toggle_records:'):
        try:
            _, start_key, start_rid, end_key, end_rid = data_str.split(':')
            settings = store.setdefault('settings', {})
            settings['category_usd_enabled'] = not bool(settings.get('category_usd_enabled', False))
            save_data(data, chat_ids=[chat_id])
            if settings['category_usd_enabled']:
                usd_rate_cached(force=False)
            text, _ = summarize_categories_record_range(store, start_key, int(start_rid), end_key, int(end_rid))
            kb = build_categories_record_summary_keyboard(start_key, int(start_rid), end_key, int(end_rid), store)
            send_or_edit_categories_window(chat_id, text, reply_markup=kb, preferred_message_id=call.message.message_id, marker_action='cat_range_records:*')
        except Exception as e:
            log_error(f'cat_usd_toggle_records: {e}')
        return True
    if data_str.startswith('cat_range_records:'):
        try:
            _, start_key, start_rid, end_key, end_rid = data_str.split(':')
            text, _ = summarize_categories_record_range(store, start_key, int(start_rid), end_key, int(end_rid))
            kb = build_categories_record_summary_keyboard(start_key, int(start_rid), end_key, int(end_rid), store)
            send_or_edit_categories_window(chat_id, text, reply_markup=kb, preferred_message_id=call.message.message_id, marker_action='cat_range_records:*')
        except Exception as e:
            log_error(f'cat_range_records: {e}')
        return True
    if data_str.startswith('cat_back_records:'):
        try:
            _, start_key, start_rid, end_key, end_rid = data_str.split(':')
            text, _ = summarize_categories_record_range(store, start_key, int(start_rid), end_key, int(end_rid))
            kb = build_categories_record_summary_keyboard(start_key, int(start_rid), end_key, int(end_rid), store)
            send_or_edit_categories_window(chat_id, text, reply_markup=kb, preferred_message_id=call.message.message_id, marker_action='cat_range_records:*')
        except Exception as e:
            log_error(f'cat_back_records: {e}')
        return True
    if data_str.startswith('cat_other_sort:'):
        try:
            _, start_key, start_rid, end_key, end_rid = data_str.split(':')
            send_or_edit_categories_window(chat_id, build_other_sort_text(store, start_key, int(start_rid), end_key, int(end_rid)), reply_markup=build_other_sort_keyboard(chat_id, store, start_key, int(start_rid), end_key, int(end_rid)), preferred_message_id=call.message.message_id, marker_action='cat_other_sort:*')
        except Exception as e:
            log_error(f'cat_other_sort: {e}')
        return True
    if data_str.startswith('cat_other_sort_toggle:'):
        try:
            _, rid, start_key, start_rid, end_key, end_rid = data_str.split(':')
            key = _other_sort_key(chat_id, start_key, int(start_rid), end_key, int(end_rid))
            selected = _category_other_sort_state.setdefault(key, set())
            rid_i = int(rid)
            if rid_i in selected:
                selected.remove(rid_i)
            else:
                selected.add(rid_i)
            send_or_edit_categories_window(chat_id, build_other_sort_text(store, start_key, int(start_rid), end_key, int(end_rid)), reply_markup=build_other_sort_keyboard(chat_id, store, start_key, int(start_rid), end_key, int(end_rid)), preferred_message_id=call.message.message_id, marker_action='cat_other_sort_toggle:*')
        except Exception as e:
            log_error(f'cat_other_sort_toggle: {e}')
        return True
    if data_str.startswith('cat_other_sort_choose:'):
        try:
            _, start_key, start_rid, end_key, end_rid = data_str.split(':')
            key = _other_sort_key(chat_id, start_key, int(start_rid), end_key, int(end_rid))
            if not _category_other_sort_state.get(key):
                bot.answer_callback_query(call.id, 'Сначала выберите записи', show_alert=False)
                return True
            send_or_edit_categories_window(chat_id, build_other_sort_target_text(chat_id, start_key, int(start_rid), end_key, int(end_rid)), reply_markup=build_other_sort_target_keyboard(chat_id, store, start_key, int(start_rid), end_key, int(end_rid)), preferred_message_id=call.message.message_id, marker_action='cat_other_sort_choose:*')
        except Exception as e:
            log_error(f'cat_other_sort_choose: {e}')
        return True
    if data_str.startswith('cat_other_sort_target:'):
        try:
            _, target_slug, start_key, start_rid, end_key, end_rid = data_str.split(':', 5)
            key = _other_sort_key(chat_id, start_key, int(start_rid), end_key, int(end_rid))
            selected = set(_category_other_sort_state.get(key, set()))
            changed = apply_other_sort_target(store, selected, target_slug)
            _category_other_sort_state.pop(key, None)
            if changed:
                save_data(data, chat_ids=[chat_id])
                finance_changed(chat_id, store.get('current_view_day') or today_key(), reason='category_manual_sort', delay=0.05)
                schedule_config_backup_for_chats(chat_id)
            text, _ = summarize_categories_record_range(store, start_key, int(start_rid), end_key, int(end_rid))
            kb = build_categories_record_summary_keyboard(start_key, int(start_rid), end_key, int(end_rid), store)
            send_or_edit_categories_window(chat_id, text, reply_markup=kb, preferred_message_id=call.message.message_id, marker_action='cat_range_records:*')
            try:
                bot.answer_callback_query(call.id, f'Перенесено записей: {changed}', show_alert=False)
            except Exception:
                pass
        except Exception as e:
            log_error(f'cat_other_sort_target: {e}')
        return True
    if data_str.startswith('cat_show_records:'):
        try:
            _, start_key, start_rid, end_key, end_rid, slug = data_str.split(':', 5)
            category = get_category_by_slug(slug, store)
            if not category:
                try:
                    bot.answer_callback_query(call.id, 'Статья не найдена', show_alert=False)
                except Exception:
                    pass
                return True
            text = build_category_record_detail_text(store, start_key, int(start_rid), end_key, int(end_rid), category)
            kb = build_category_record_detail_keyboard(start_key, int(start_rid), end_key, int(end_rid), category=category, store=store)
            send_or_edit_categories_window(chat_id, text, reply_markup=kb, preferred_message_id=call.message.message_id, marker_action='cat_show_records:*')
        except Exception as e:
            log_error(f'cat_show_records: {e}')
        return True
    if data_str.startswith('cat_pick_end:'):
        try:
            _, y, m, start_d = data_str.split(':')
            _send_category_pick_end(chat_id, call.message.message_id, int(y), int(m), int(start_d))
        except Exception as e:
            log_error(f'cat_pick_end: {e}')
        return True
    if data_str.startswith('cat_pick_set_end:'):
        try:
            _, y, m, start_d, end_d = data_str.split(':')
            _send_category_pick_end(chat_id, call.message.message_id, int(y), int(m), int(start_d), int(end_d))
        except Exception as e:
            log_error(f'cat_pick_set_end: {e}')
        return True
    if data_str.startswith('cat_pick_end2:'):
        try:
            _, start_key, y, m = data_str.split(':')
            _send_category_pick_end_any_month(chat_id, call.message.message_id, start_key, int(y), int(m))
        except Exception as e:
            log_error(f'cat_pick_end2: {e}')
        return True
    if data_str.startswith('cat_pick_set_end2:'):
        try:
            _, start_key, y, m, d = data_str.split(':')
            end_key = _date_key_from_ymd(int(y), int(m), int(d))
            _send_category_pick_end_any_month(chat_id, call.message.message_id, start_key, int(y), int(m), end_key)
        except Exception as e:
            log_error(f'cat_pick_set_end2: {e}')
        return True
    if data_str.startswith('cat_range_custom2:'):
        try:
            _, start, end = data_str.split(':', 2)
            if end < start:
                start, end = (end, start)
            label = f'{fmt_date_ddmmyy(start)} — {fmt_date_ddmmyy(end)}'
            text, _ = summarize_categories(store, start, end, label)
            kb = build_categories_summary_keyboard('rng', start, end, store=store)
            send_or_edit_categories_window(chat_id, text, reply_markup=kb, preferred_message_id=call.message.message_id)
        except Exception as e:
            log_error(f'cat_range_custom2: {e}')
        return True
    if data_str.startswith('cat_range_custom:'):
        try:
            _, y, m, a, b = data_str.split(':')
            y, m, a, b = map(int, (y, m, a, b))
            last_day = calendar.monthrange(y, m)[1]
            a = max(1, min(a, last_day))
            b = max(1, min(b, last_day))
            if b < a:
                a, b = (b, a)
            start = f'{y}-{m:02d}-{a:02d}'
            end = f'{y}-{m:02d}-{b:02d}'
            label = f'{fmt_date_ddmmyy(start)} — {fmt_date_ddmmyy(end)}'
            text, _ = summarize_categories(store, start, end, label)
            kb = build_categories_summary_keyboard('rng', start, end, store=store)
            send_or_edit_categories_window(chat_id, text, reply_markup=kb, preferred_message_id=call.message.message_id)
        except Exception as e:
            log_error(f'cat_range_custom: {e}')
        return True
    if data_str.startswith('cat_rng:'):
        try:
            _, y, m, a, b = data_str.split(':')
            y, m, a, b = map(int, (y, m, a, b))
        except Exception:
            return True
        if m == 12:
            last_day = (datetime(y + 1, 1, 1) - timedelta(days=1)).day
        else:
            last_day = (datetime(y, m + 1, 1) - timedelta(days=1)).day
        a = max(1, min(a, last_day))
        b = max(1, min(b, last_day))
        if b < a:
            b = a
        start = f'{y}-{m:02d}-{a:02d}'
        end = f'{y}-{m:02d}-{b:02d}'
        label = f'{fmt_date_ddmmyy(start)} — {fmt_date_ddmmyy(end)}'
        text, _ = summarize_categories(store, start, end, label)
        kb = build_categories_summary_keyboard('rng', start, end, store=store)
        send_or_edit_categories_window(chat_id, text, reply_markup=kb, preferred_message_id=call.message.message_id)
        return True
    if data_str.startswith('cat_show_wthu:'):
        _, ref, slug = data_str.split(':', 2)
        category = get_category_by_slug(slug, store)
        if not category:
            return True
        start_key = week_start_thursday(ref or today_key())
        start, end = week_bounds_thu_wed(start_key)
        label = f'{fmt_date_ddmmyy(start)} — {fmt_date_ddmmyy(end)} (Чт–Ср)'
        text = build_category_detail_text(store, start, end, category, label)
        kb = build_category_detail_keyboard(start, end, f'cat_wthu:{start}', mode='wthu', slug=slug, store=store)
        send_or_edit_categories_window(chat_id, text, reply_markup=kb, preferred_message_id=call.message.message_id)
        return True
    if data_str.startswith('cat_show_wk:'):
        _, ref, slug = data_str.split(':', 2)
        category = get_category_by_slug(slug, store)
        if not category:
            return True
        start_key = week_start_monday(ref or today_key())
        start, end = week_bounds_from_start(start_key)
        label = f'{fmt_date_ddmmyy(start)} — {fmt_date_ddmmyy(end)} (Пн–Вс)'
        text = build_category_detail_text(store, start, end, category, label)
        kb = build_category_detail_keyboard(start, end, f'cat_wk:{start}', mode='wk', slug=slug, store=store)
        send_or_edit_categories_window(chat_id, text, reply_markup=kb, preferred_message_id=call.message.message_id)
        return True
    if data_str.startswith('cat_show:'):
        _, start, end, slug = data_str.split(':', 3)
        category = get_category_by_slug(slug, store)
        if not category:
            return True
        start_dt = datetime.strptime(start, '%Y-%m-%d')
        end_dt = datetime.strptime(end, '%Y-%m-%d')
        label = f'{fmt_date_ddmmyy(start)} — {fmt_date_ddmmyy(end)}'
        if (end_dt - start_dt).days == 6 and start == week_start_thursday(start):
            back_callback = f'cat_wthu:{start}'
            label += ' (Чт–Ср)'
        elif (end_dt - start_dt).days == 6 and start == week_start_monday(start):
            back_callback = f'cat_wk:{start}'
            label += ' (Пн–Вс)'
        elif start_dt.year != end_dt.year or start_dt.month != end_dt.month:
            back_callback = f'cat_range_custom2:{start}:{end}'
        else:
            y, m = (start_dt.year, start_dt.month)
            back_callback = f'cat_rng:{y}:{m}:{start_dt.day}:{end_dt.day}'
        mode = None
        if (end_dt - start_dt).days == 6 and start == week_start_thursday(start):
            mode = 'wthu'
        elif (end_dt - start_dt).days == 6 and start == week_start_monday(start):
            mode = 'wk'
        text = build_category_detail_text(store, start, end, category, label)
        kb = build_category_detail_keyboard(start, end, back_callback, mode=mode, slug=slug, store=store)
        send_or_edit_categories_window(chat_id, text, reply_markup=kb, preferred_message_id=call.message.message_id)
        return True
    return False
_callback_debounce_state = {}

def _v177_legacy_0223_callback_should_debounce(call, data_str: str, min_interval: float=0.12) -> bool:
    """Защита от частых кликов: Telegram уже получил answer_callback_query, поэтому «Загрузка» не висит."""
    try:
        chat_id = int(call.message.chat.id)
        msg_id = int(call.message.message_id)
        data_str = str(data_str or '')
        if data_str == 'none':
            return True
        hot = False
        if data_str.startswith('d:'):
            parts = data_str.split(':', 2)
            action = parts[2] if len(parts) > 2 else ''
            hot = action in {'prev', 'next', 'today', 'open', 'back_main', 'calendar', 'csv_all'}
        elif data_str.startswith('fv:') or data_str.startswith('c:') or data_str.startswith('fc:'):
            hot = True
        elif data_str.startswith(('secday:', 'secview:', 'secchatcal:', 'secmon:', 'secmonthlist:')):
            hot = True
        if not hot:
            return False
        key = (chat_id, msg_id, data_str.split(':', 1)[0], data_str.split(':')[-1])
        now_ts = time.time()
        prev_ts = _callback_debounce_state.get(key, 0)
        _callback_debounce_state[key] = now_ts
        skipped = now_ts - prev_ts < float(min_interval)
        if skipped:
            try:
                bot_journal('button_debounced', chat_id, data_str)
            except Exception:
                pass
        return skipped
    except Exception:
        return False
try:
    _v177_legacy_0223_callback_should_debounce.__name__ = '_callback_should_debounce'
except Exception:
    pass
_secret_edit_refresh_lock = threading.RLock()
_secret_edit_refresh_timers = {}

def schedule_secret_edit_refresh_window(viewer_chat_id: int, message_id: int, target_chat_id: int, day_key: str, self_only: bool=False, delay: float=0.7):
    key = (int(viewer_chat_id), int(message_id))
    generation = time.time_ns()
    scheduler_key = f'secret-edit-refresh:{key[0]}:{key[1]}'

    def _job():
        try:
            with _secret_edit_refresh_lock:
                if _secret_edit_refresh_timers.get(key) != generation:
                    return
            text = build_secret_edit_text(int(target_chat_id), day_key)
            kb = build_secret_edit_keyboard(int(viewer_chat_id), int(target_chat_id), day_key, self_only=bool(self_only))
            try:
                fast_ui_edit_message_text(int(viewer_chat_id), int(message_id), text, reply_markup=kb, purpose='secret_edit_debounce')
            except Exception as e:
                if not is_telegram_429(e) and 'message is not modified' not in str(e).lower():
                    log_error(f'secret edit debounce refresh {viewer_chat_id}:{message_id}: {e}')
            register_secret_window(int(viewer_chat_id), int(message_id), int(target_chat_id), 'edit', day_key=day_key, self_only=bool(self_only))
            schedule_secret_calendar_close(int(viewer_chat_id), int(message_id))
        finally:
            with _secret_edit_refresh_lock:
                if _secret_edit_refresh_timers.get(key) == generation:
                    _secret_edit_refresh_timers.pop(key, None)
    with _secret_edit_refresh_lock:
        DELAYED_SCHEDULER.cancel(scheduler_key)
        _secret_edit_refresh_timers[key] = generation
        DELAYED_SCHEDULER.schedule(scheduler_key, float(delay), _job)
_CALLBACK_ACK_LOCK = threading.RLock()
_CALLBACK_ACK_STATE = {}
_CALLBACK_ACK_TTL_SECONDS = 180.0
try:
    CALLBACK_RECEIPT_ACK_DELAY_SECONDS = max(0.03, min(0.10, float(os.getenv('CALLBACK_RECEIPT_ACK_DELAY_SECONDS', '0.06') or '0.06')))
except Exception:
    CALLBACK_RECEIPT_ACK_DELAY_SECONDS = 0.06
_ORIGINAL_BOT_ANSWER_CALLBACK_QUERY = bot.answer_callback_query

def _callback_ack_prune_locked(now_ts=None):
    now_ts = float(now_ts or time.time())
    for key, row in list(_CALLBACK_ACK_STATE.items()):
        if now_ts - float((row or {}).get('ts', now_ts)) > _CALLBACK_ACK_TTL_SECONDS:
            _CALLBACK_ACK_STATE.pop(key, None)

def _late_callback_notice(chat_id, text):
    try:
        if chat_id is not None and str(text or '').strip():
            send_and_auto_delete(int(chat_id), f'ℹ️ {str(text).strip()}', 8)
    except Exception:
        pass

def _tracked_answer_callback_query(callback_query_id, *args, **kwargs):
    callback_id = str(callback_query_id or '')
    text = kwargs.get('text')
    if text is None and args:
        text = args[0]
    with _CALLBACK_ACK_LOCK:
        _callback_ack_prune_locked()
        row = _CALLBACK_ACK_STATE.setdefault(callback_id, {'ts': time.time()})
        row['ts'] = time.time()
        # R18: an empty ACK must stay empty.  R17 converted every silent receipt ACK
        # into the visible Telegram toast "⏳ Выполняю…", which made navigation feel
        # delayed even when the actual window render was fast.  Long jobs must request
        # an explicit progress text themselves.
        if row.get('answered'):
            # R18: the receipt ACK wins immediately.  A later ordinary toast from a
            # handler must not create a new Telegram message (R17 could turn every
            # navigation click into extra chat noise).  Preserve only explicit alert
            # semantics, which are normally permission/error messages.
            chat_id = row.get('chat_id')
            if bool(kwargs.get('show_alert')) and str(text or '').strip() and (not row.get('late_notice_sent')):
                row['late_notice_sent'] = True
                # Keep the dedicated ACK pool pure: late permission/error feedback is
                # ordinary background Telegram work and must never queue ahead of ACKs.
                _late_pool = globals().get('GENERAL_TASK_POOL')
                if _late_pool is not None:
                    _late_pool.submit_unique(f'callback-late-alert:{callback_id}', _late_callback_notice, chat_id, text)
                else:
                    threading.Thread(target=_late_callback_notice, args=(chat_id, text), name=f'r18-late-alert-{callback_id}', daemon=True).start()
            return True
        if row.get('inflight'):
            return True
        row['inflight'] = True
    try:
        result = _ORIGINAL_BOT_ANSWER_CALLBACK_QUERY(callback_query_id, *args, **kwargs)
        with _CALLBACK_ACK_LOCK:
            row = _CALLBACK_ACK_STATE.setdefault(callback_id, {})
            row.update({'answered': True, 'inflight': False, 'ts': time.time()})
        try:
            CALLBACK_ACK_SCHEDULER.cancel(f'callback-receipt-ack:{callback_id}')
        except Exception:
            pass
        return result
    except Exception:
        with _CALLBACK_ACK_LOCK:
            row = _CALLBACK_ACK_STATE.setdefault(callback_id, {})
            row['inflight'] = False
            row['ts'] = time.time()
        raise
bot.answer_callback_query = _tracked_answer_callback_query

def _answer_callback_query_quiet(callback_id: str, chat_id=None):
    try:
        bot.answer_callback_query(callback_id, show_alert=False)
    except Exception:
        pass

def answer_callback_query_background(callback_id: str):
    """Immediate ACK from a callback handler, isolated from GENERAL/MEGA work."""
    key = f'callback-ack:{callback_id}'
    if not CALLBACK_ACK_TASK_POOL.submit_unique(key, _answer_callback_query_quiet, callback_id, None):
        try:
            bot_journal('callback_ack_coalesced', None, str(callback_id))
        except Exception:
            pass

def _v177_legacy_0224_schedule_callback_receipt_ack(callback_id: str, chat_id=None, delay: float | None=None):
    """Fallback ACK scheduled as soon as Flask receives callback_query."""
    callback_id = str(callback_id or '')
    if not callback_id:
        return
    with _CALLBACK_ACK_LOCK:
        _callback_ack_prune_locked()
        row = _CALLBACK_ACK_STATE.setdefault(callback_id, {})
        row['chat_id'] = int(chat_id) if chat_id is not None else row.get('chat_id')
        row['ts'] = time.time()
        if row.get('answered'):
            return
    CALLBACK_ACK_SCHEDULER.schedule(f'callback-receipt-ack:{callback_id}', CALLBACK_RECEIPT_ACK_DELAY_SECONDS if delay is None else max(0.05, float(delay)), _answer_callback_query_quiet, callback_id, chat_id)
try:
    _v177_legacy_0224_schedule_callback_receipt_ack.__name__ = 'schedule_callback_receipt_ack'
except Exception:
    pass

def build_process_center_keyboard(chat_id: int):
    kb = types.InlineKeyboardMarkup(row_width=2)
    kb.row(IB('🔄 Обновить', callback_data='process_center'))
    if is_owner_chat(chat_id):
        kb.row(IB('🧯 Проблемные задачи', callback_data='problem_tasks'))
    day = get_chat_store(chat_id).get('current_view_day') or today_key()
    kb.row(IB('🔙 Назад в Инфо', callback_data=f'd:{day}:info'), IB('❌ Закрыть', callback_data='info_close'))
    return kb

def build_problem_tasks_keyboard(chat_id: int):
    kb = types.InlineKeyboardMarkup(row_width=1)
    kb.row(IB('🔄 Обновить', callback_data='problem_tasks'))
    day = get_chat_store(chat_id).get('current_view_day') or today_key()
    kb.row(IB('🔙 Назад в Инфо', callback_data=f'd:{day}:info'))
    kb.row(IB('❌ Закрыть', callback_data='info_close'))
    return kb

def _v177_legacy_0225_build_safety_profile_keyboard(chat_id: int):
    kb = types.InlineKeyboardMarkup(row_width=1)
    kb.row(IB(safety_profile_label(), callback_data='safety_profile_toggle'))
    kb.row(IB('👥 Права пользователей', callback_data='security_roles:0'))
    day = get_chat_store(chat_id).get('current_view_day') or today_key()
    kb.row(IB('🔙 Назад в Инфо', callback_data=f'd:{day}:info'))
    return kb
try:
    _v177_legacy_0225_build_safety_profile_keyboard.__name__ = 'build_safety_profile_keyboard'
except Exception:
    pass

def build_security_roles_text(page: int=0) -> str:
    rows = security_known_users()
    page_size = 10
    pages = max(1, (len(rows) + page_size - 1) // page_size)
    page = max(0, min(int(page or 0), pages - 1))
    return f'👥 ПРАВА ПОЛЬЗОВАТЕЛЕЙ\n\nРаботают только когда профиль защиты включён «ПО-НОВОМУ».\nОбычный — прежние разрешения. Ограниченные роли запрещают лишние действия.\n\nПользователей: {len(rows)}\nСтраница: {page + 1}/{pages}'

def build_security_roles_keyboard(page: int=0):
    rows = security_known_users()
    page_size = 10
    pages = max(1, (len(rows) + page_size - 1) // page_size)
    page = max(0, min(int(page or 0), pages - 1))
    kb = types.InlineKeyboardMarkup(row_width=1)
    start = page * page_size
    for row in rows[start:start + page_size]:
        uid = int(row.get('id') or 0)
        name = security_user_display(uid)
        if len(name) > 22:
            name = name[:21] + '…'
        kb.row(IB(f'{name} · {security_role_label(security_role_for_user(uid))}', callback_data=f'security_role_user:{uid}:{page}'))
    if pages > 1:
        nav = []
        if page > 0:
            nav.append(IB('⬅️', callback_data=f'security_roles:{page - 1}'))
        nav.append(IB(f'{page + 1}/{pages}', callback_data='none'))
        if page + 1 < pages:
            nav.append(IB('➡️', callback_data=f'security_roles:{page + 1}'))
        kb.row(*nav)
    kb.row(IB('⬅️ Назад', callback_data='safety_profile_open'))
    return kb

def build_security_role_user_text(user_id: int) -> str:
    uid = int(user_id)
    role = security_role_for_user(uid)
    return f'👤 ПРАВА ПОЛЬЗОВАТЕЛЯ\n\nИмя: {security_user_display(uid)}\nID: {uid}\nРоль: {security_role_label(role)}\n\nВыберите один понятный профиль. Владелец всегда имеет полный доступ.'

def build_security_role_user_keyboard(user_id: int, page: int=0):
    uid = int(user_id)
    kb = types.InlineKeyboardMarkup(row_width=1)
    for role in ('standard', 'view_only', 'expense_input', 'finance_admin', 'forward_manager', 'secret_manager', 'reminder_manager'):
        mark = '✅ ' if security_role_for_user(uid) == role else '▫️ '
        kb.row(IB(mark + security_role_label(role), callback_data=f'security_role_set:{uid}:{role}:{int(page)}'))
    kb.row(IB('⬅️ К пользователям', callback_data=f'security_roles:{int(page)}'))
    return kb

def build_integrity_keyboard(chat_id: int):
    kb = types.InlineKeyboardMarkup(row_width=1)
    kb.row(IB('🔍 Проверить заново', callback_data='integrity_status'))
    day = get_chat_store(chat_id).get('current_view_day') or today_key()
    kb.row(IB('🔙 Назад в Инфо', callback_data=f'd:{day}:info'))
    return kb
# v262
