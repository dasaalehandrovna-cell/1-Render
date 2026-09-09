# v262

# --- ИСТОЧНИК: 16_window_diagnostics.py ---
import inspect as _window_diag_inspect
WINDOW_DIAGNOSTICS_ENABLED = str(os.getenv('WINDOW_DIAGNOSTICS_ENABLED', '1') or '1').strip().lower() not in {'0', 'false', 'off', 'no'}
WINDOW_DIAGNOSTICS_TAIL_LIMIT = max(100, min(5000, int(os.getenv('WINDOW_DIAGNOSTICS_TAIL_LIMIT', '1000') or '1000')))
WINDOW_DIAGNOSTICS_STATE_LIMIT = max(200, min(10000, int(os.getenv('WINDOW_DIAGNOSTICS_STATE_LIMIT', '1500') or '1500')))
_WINDOW_DIAG_LOCK = threading.RLock()
_WINDOW_DIAG_EVENTS = deque(maxlen=WINDOW_DIAGNOSTICS_TAIL_LIMIT)
_WINDOW_DIAG_STATE = {}
_WINDOW_DIAG_COUNTERS = defaultdict(int)
_WINDOW_DIAG_SEQ = 0
_WINDOW_DIAG_CONTEXT = threading.local()
_WINDOW_DIAG_INSTALLED = False
_WINDOW_DIAG_ORIGINAL_METHODS = {}

def _window_diag_next_seq() -> int:
    global _WINDOW_DIAG_SEQ
    with _WINDOW_DIAG_LOCK:
        _WINDOW_DIAG_SEQ += 1
        return int(_WINDOW_DIAG_SEQ)

def _window_diag_key(chat_id, message_id):
    try:
        return (int(chat_id), int(message_id))
    except Exception:
        return None

def _window_diag_hash(value) -> str:
    try:
        if isinstance(value, bytes):
            raw = value
        else:
            raw = str(value or '').encode('utf-8', errors='replace')
        return hashlib.sha256(raw).hexdigest()[:16]
    except Exception:
        return ''

def _window_diag_marker(text: str) -> str:
    try:
        match = re.search('(?:^|\\s)([СФПОВсов]\\d{1,6})(?:-\\(W[A-Z0-9]{6,12}\\))?(?:\\s*[⏳⏰])?\\s*$', str(text or ''), flags=re.IGNORECASE)
        return str(match.group(1) if match else '').upper()
    except Exception:
        return ''

def _window_diag_keyboard(reply_markup) -> dict:
    callbacks = []
    labels = []
    button_count = 0
    try:
        for row in list(getattr(reply_markup, 'keyboard', None) or []):
            for button in row or []:
                button_count += 1
                label = str(getattr(button, 'text', '') or '').strip()
                callback = str(getattr(button, 'callback_data', '') or '').strip()
                if label:
                    labels.append(label[:50])
                if callback:
                    try:
                        callback = _normalize_window_action(callback)
                    except Exception:
                        callback = callback[:80]
                    callbacks.append(callback[:100])
    except Exception:
        pass
    canonical = json.dumps({'callbacks': callbacks, 'labels': labels}, ensure_ascii=False, sort_keys=True)
    return {'buttons': int(button_count), 'hash': _window_diag_hash(canonical), 'callbacks': callbacks[:10]}

def _window_diag_first_line(text: str, marker: str='', purpose: str='') -> str:
    secret = str(marker or '').upper().startswith('С') or 'secret' in str(purpose or '').lower()
    if secret:
        return '<секретный текст скрыт>'
    try:
        rows = [x.strip() for x in str(text or '').splitlines() if x.strip()]
        value = rows[0] if rows else ''
        value = re.sub('https?://\\S+', '<url>', value, flags=re.IGNORECASE)
        value = re.sub('(?:token|key|secret|password)\\s*[=:]\\s*\\S+', '\\1=<hidden>', value, flags=re.IGNORECASE)
        return value[:140]
    except Exception:
        return ''

def _window_diag_snapshot_payload(text, reply_markup, purpose: str='') -> dict:
    body = str(text or '')
    marker = _window_diag_marker(body)
    kb = _window_diag_keyboard(reply_markup)
    return {'marker': marker, 'text_hash': _window_diag_hash(body), 'text_len': len(body), 'first_line': _window_diag_first_line(body, marker, purpose), 'keyboard_hash': kb.get('hash') or '', 'buttons': int(kb.get('buttons') or 0), 'callbacks': list(kb.get('callbacks') or [])}

def _window_diag_update_context() -> dict:
    try:
        fn = globals().get('_current_telegram_update_context')
        return dict(fn() or {}) if callable(fn) else {}
    except Exception:
        return {}

def _window_diag_caller() -> str:
    try:
        frame = _window_diag_inspect.currentframe()
        frame = frame.f_back if frame else None
        fallback = ''
        for _ in range(18):
            if frame is None:
                break
            filename = os.path.basename(str(frame.f_code.co_filename or ''))
            func = str(frame.f_code.co_name or '')
            line = int(frame.f_lineno or 0)
            if filename and filename != '16_window_diagnostics.py':
                candidate = f'{filename}:{func}:{line}'
                if not fallback:
                    fallback = candidate
                if re.match('\\d{2}_.+\\.py$', filename) and func not in {'_tg_call_retry', 'wrapper', '_wrapped'}:
                    return candidate
            frame = frame.f_back
        return fallback
    except Exception:
        return ''

def _window_diag_context_value() -> dict:
    try:
        return dict(getattr(_WINDOW_DIAG_CONTEXT, 'value', {}) or {})
    except Exception:
        return {}

@contextmanager
def window_diag_context(**values):
    previous = getattr(_WINDOW_DIAG_CONTEXT, 'value', None)
    merged = dict(previous or {})
    merged.update({k: v for k, v in values.items() if v is not None})
    _WINDOW_DIAG_CONTEXT.value = merged
    try:
        yield merged
    finally:
        if previous is None:
            try:
                delattr(_WINDOW_DIAG_CONTEXT, 'value')
            except Exception:
                pass
        else:
            _WINDOW_DIAG_CONTEXT.value = previous

def _window_diag_emit(action: str, chat_id=None, message_id=None, detail: dict | None=None, level: str='INFO') -> dict:
    if not WINDOW_DIAGNOSTICS_ENABLED:
        return {}
    seq = _window_diag_next_seq()
    update_ctx = _window_diag_update_context()
    row = {'seq': seq, 'ts': now_local().isoformat(timespec='milliseconds') if 'now_local' in globals() else datetime.now(timezone.utc).isoformat(timespec='milliseconds'), 'action': str(action or 'window_event'), 'level': str(level or 'INFO').upper(), 'chat_id': int(chat_id) if chat_id is not None else None, 'message_id': int(message_id) if message_id is not None else None, 'thread': threading.current_thread().name, 'caller': _window_diag_caller(), 'update_id': update_ctx.get('update_id'), 'update_type': update_ctx.get('update_type'), 'callback_data': str(update_ctx.get('callback_data') or '')[:240], 'source_message_id': update_ctx.get('message_id'), 'detail': dict(detail or {})}
    with _WINDOW_DIAG_LOCK:
        _WINDOW_DIAG_EVENTS.append(row)
        _WINDOW_DIAG_COUNTERS[row['action']] += 1
    try:
        compact = {'seq': seq, 'msg': row.get('message_id'), 'update': row.get('update_id'), 'callback': row.get('callback_data'), 'caller': row.get('caller')}
        compact.update(dict(detail or {}))
        text = json.dumps(compact, ensure_ascii=False, separators=(',', ':'), default=str)
        bot_journal(row['action'], chat_id, text[:1800], row['level'])
    except Exception:
        pass
    return row

def _window_diag_state_get(chat_id, message_id) -> dict:
    key = _window_diag_key(chat_id, message_id)
    if key is None:
        return {}
    with _WINDOW_DIAG_LOCK:
        return dict(_WINDOW_DIAG_STATE.get(key) or {})

def _window_diag_state_set(chat_id, message_id, snapshot: dict, source: str, purpose: str='', deleted: bool=False) -> dict:
    key = _window_diag_key(chat_id, message_id)
    if key is None:
        return {}
    row = dict(snapshot or {})
    row.update({'seq': _window_diag_next_seq(), 'chat_id': key[0], 'message_id': key[1], 'source': str(source or ''), 'purpose': str(purpose or '')[:160], 'deleted': bool(deleted), 'updated_at': now_local().isoformat(timespec='milliseconds') if 'now_local' in globals() else datetime.now(timezone.utc).isoformat(timespec='milliseconds')})
    with _WINDOW_DIAG_LOCK:
        _WINDOW_DIAG_STATE[key] = row
        if len(_WINDOW_DIAG_STATE) > WINDOW_DIAGNOSTICS_STATE_LIMIT:
            oldest = sorted(_WINDOW_DIAG_STATE.items(), key=lambda kv: int((kv[1] or {}).get('seq') or 0))
            for stale_key, _ in oldest[:max(1, len(_WINDOW_DIAG_STATE) - WINDOW_DIAGNOSTICS_STATE_LIMIT)]:
                _WINDOW_DIAG_STATE.pop(stale_key, None)
    return dict(row)

def _window_diag_is_candidate(chat_id, message_id, text=None, reply_markup=None) -> bool:
    if not WINDOW_DIAGNOSTICS_ENABLED:
        return False
    if reply_markup is not None or _window_diag_marker(str(text or '')):
        return True
    if _window_diag_state_get(chat_id, message_id):
        return True
    try:
        getter = globals().get('get_registered_open_window')
        return bool(getter(int(chat_id), int(message_id))) if callable(getter) else False
    except Exception:
        return False

def _v177_legacy_0113_window_diag_duplicate_marker(chat_id: int, message_id: int, marker: str) -> dict:
    if not marker:
        return {}
    with _WINDOW_DIAG_LOCK:
        rows = [dict(v) for (cid, mid), v in _WINDOW_DIAG_STATE.items() if cid == int(chat_id) and mid != int(message_id) and (not bool((v or {}).get('deleted'))) and (str((v or {}).get('marker') or '') == str(marker))]
    if not rows:
        return {}
    rows.sort(key=lambda x: int(x.get('seq') or 0), reverse=True)
    return rows[0]
try:
    _v177_legacy_0113_window_diag_duplicate_marker.__name__ = '_window_diag_duplicate_marker'
except Exception:
    pass

def _v177_legacy_0114_window_diag_prepare_fast_ui_payload(payload: dict) -> dict:
    if not WINDOW_DIAGNOSTICS_ENABLED or not isinstance(payload, dict):
        return payload
    chat_id = int(payload.get('chat_id'))
    message_id = int(payload.get('message_id'))
    current = _window_diag_state_get(chat_id, message_id)
    snap = _window_diag_snapshot_payload(payload.get('text'), payload.get('reply_markup'), str(payload.get('purpose') or ''))
    payload['_window_diag_request_id'] = f'w{_window_diag_next_seq()}'
    payload['_window_diag_expected_seq'] = int(current.get('seq') or 0)
    payload['_window_diag_snapshot'] = snap
    return payload
try:
    _v177_legacy_0114_window_diag_prepare_fast_ui_payload.__name__ = 'window_diag_prepare_fast_ui_payload'
except Exception:
    pass

def window_diag_fast_ui_scheduled(payload: dict, wait_seconds: float, replaced_payload: dict | None=None):
    if not WINDOW_DIAGNOSTICS_ENABLED or not isinstance(payload, dict):
        return
    detail = {'request_id': payload.get('_window_diag_request_id'), 'expected_seq': payload.get('_window_diag_expected_seq'), 'wait': round(float(wait_seconds or 0), 3), 'purpose': str(payload.get('purpose') or '')[:160], 'to_marker': (payload.get('_window_diag_snapshot') or {}).get('marker'), 'to_hash': (payload.get('_window_diag_snapshot') or {}).get('text_hash')}
    action = 'window_ui_edit_scheduled'
    if isinstance(replaced_payload, dict):
        action = 'window_ui_edit_coalesced'
        detail.update({'replaced_request_id': replaced_payload.get('_window_diag_request_id'), 'replaced_marker': (replaced_payload.get('_window_diag_snapshot') or {}).get('marker'), 'replaced_hash': (replaced_payload.get('_window_diag_snapshot') or {}).get('text_hash')})
    _window_diag_emit(action, payload.get('chat_id'), payload.get('message_id'), detail, 'INFO')

def _v177_legacy_0115_window_diag_fast_ui_apply(payload: dict, delayed: bool=False):
    if not WINDOW_DIAGNOSTICS_ENABLED or not isinstance(payload, dict):
        return
    chat_id = int(payload.get('chat_id'))
    message_id = int(payload.get('message_id'))
    current = _window_diag_state_get(chat_id, message_id)
    expected_seq = int(payload.get('_window_diag_expected_seq') or 0)
    current_seq = int(current.get('seq') or 0)
    detail = {'request_id': payload.get('_window_diag_request_id'), 'delayed': bool(delayed), 'expected_seq': expected_seq, 'current_seq': current_seq, 'current_marker': current.get('marker'), 'to_marker': (payload.get('_window_diag_snapshot') or {}).get('marker'), 'purpose': str(payload.get('purpose') or '')[:160]}
    if delayed and expected_seq != current_seq:
        detail['reason'] = 'another_window_mutation_happened_after_schedule'
        _window_diag_emit('window_stale_edit_apply', chat_id, message_id, detail, 'ERROR')
    else:
        _window_diag_emit('window_ui_edit_apply', chat_id, message_id, detail, 'INFO')
try:
    _v177_legacy_0115_window_diag_fast_ui_apply.__name__ = 'window_diag_fast_ui_apply'
except Exception:
    pass

def window_diag_note_recreate(chat_id: int, message_id: int, reason: str, purpose: str=''):
    _window_diag_emit('window_recreate_requested', chat_id, message_id, {'reason': str(reason or '')[:220], 'purpose': str(purpose or '')[:160]}, 'WARN')

def _window_diag_edit_wrapper(method_name: str, original):

    def _wrapped(*args, **kwargs):
        text_key = 'caption' if method_name == 'edit_message_caption' else 'text'
        text = kwargs.get(text_key)
        if text is None and args:
            text = args[0]
        chat_id = kwargs.get('chat_id')
        message_id = kwargs.get('message_id')
        reply_markup = kwargs.get('reply_markup')
        ctx = _window_diag_context_value()
        purpose = str(ctx.get('purpose') or method_name)
        candidate = _window_diag_is_candidate(chat_id, message_id, text, reply_markup)
        before = _window_diag_state_get(chat_id, message_id) if candidate else {}
        requested = _window_diag_snapshot_payload(text, reply_markup, purpose) if candidate else {}
        if candidate and reply_markup is None and before:
            requested['keyboard_hash'] = before.get('keyboard_hash') or ''
            requested['buttons'] = int(before.get('buttons') or 0)
            requested['callbacks'] = list(before.get('callbacks') or [])
        expected_seq = int(ctx.get('expected_seq') or 0)
        if candidate and expected_seq and (int(before.get('seq') or 0) != expected_seq):
            _window_diag_emit('window_transport_stale_request', chat_id, message_id, {'method': method_name, 'purpose': purpose, 'expected_seq': expected_seq, 'current_seq': int(before.get('seq') or 0), 'from_marker': before.get('marker'), 'to_marker': requested.get('marker'), 'request_id': ctx.get('request_id')}, 'ERROR')
        try:
            result = original(*args, **kwargs)
        except Exception as exc:
            if candidate:
                low = str(exc or '').lower()
                if 'message is not modified' in low:
                    action, level = ('window_edit_not_modified', 'INFO')
                    _window_diag_state_set(chat_id, message_id, requested, method_name, purpose)
                elif 'message to edit not found' in low or "message can't be edited" in low:
                    action, level = ('window_edit_target_missing', 'WARN')
                    _window_diag_state_set(chat_id, message_id, before or requested, method_name, purpose, deleted=True)
                    try:
                        unregister = globals().get('unregister_open_window')
                        if callable(unregister):
                            unregister(int(chat_id), int(message_id))
                    except Exception:
                        pass
                else:
                    action, level = ('window_edit_failed', 'ERROR')
                _window_diag_emit(action, chat_id, message_id, {'method': method_name, 'purpose': purpose, 'error': str(exc)[:360], 'from_marker': before.get('marker'), 'to_marker': requested.get('marker'), 'from_hash': before.get('text_hash'), 'to_hash': requested.get('text_hash'), 'request_id': ctx.get('request_id')}, level)
            raise
        if candidate:
            changed = any((str(before.get(k) or '') != str(requested.get(k) or '') for k in ('marker', 'text_hash', 'keyboard_hash')))
            state = _window_diag_state_set(chat_id, message_id, requested, method_name, purpose)
            _window_diag_emit('window_edit_applied' if changed else 'window_edit_repeated', chat_id, message_id, {'method': method_name, 'purpose': purpose, 'from_seq': before.get('seq'), 'to_seq': state.get('seq'), 'from_marker': before.get('marker'), 'to_marker': requested.get('marker'), 'from_hash': before.get('text_hash'), 'to_hash': requested.get('text_hash'), 'from_keyboard': before.get('keyboard_hash'), 'to_keyboard': requested.get('keyboard_hash'), 'first_line': requested.get('first_line'), 'buttons': requested.get('buttons'), 'request_id': ctx.get('request_id')}, 'INFO')
        return result
    return _wrapped

def _window_diag_send_wrapper(original):

    def _wrapped(*args, **kwargs):
        chat_id = kwargs.get('chat_id') if kwargs.get('chat_id') is not None else args[0] if args else None
        text = kwargs.get('text') if kwargs.get('text') is not None else args[1] if len(args) > 1 else ''
        reply_markup = kwargs.get('reply_markup')
        ctx = _window_diag_context_value()
        purpose = str(ctx.get('purpose') or 'send_message')
        candidate = bool(reply_markup is not None or _window_diag_marker(str(text or '')) or ctx.get('window_force'))
        snap = _window_diag_snapshot_payload(text, reply_markup, purpose) if candidate else {}
        try:
            result = original(*args, **kwargs)
        except Exception as exc:
            if candidate:
                _window_diag_emit('window_send_failed', chat_id, None, {'purpose': purpose, 'error': str(exc)[:360], 'marker': snap.get('marker'), 'hash': snap.get('text_hash'), 'recreate_from': ctx.get('recreate_from')}, 'ERROR')
            raise
        if candidate:
            message_id = int(getattr(result, 'message_id', 0) or 0)
            state = _window_diag_state_set(chat_id, message_id, snap, 'send_message', purpose)
            _window_diag_emit('window_created', chat_id, message_id, {'purpose': purpose, 'marker': snap.get('marker'), 'hash': snap.get('text_hash'), 'keyboard': snap.get('keyboard_hash'), 'first_line': snap.get('first_line'), 'buttons': snap.get('buttons'), 'to_seq': state.get('seq'), 'recreate_from': ctx.get('recreate_from'), 'recreate_reason': ctx.get('recreate_reason')}, 'INFO')
            if ctx.get('recreate_from'):
                _window_diag_emit('window_recreated', chat_id, message_id, {'old_message_id': int(ctx.get('recreate_from') or 0), 'reason': str(ctx.get('recreate_reason') or '')[:220], 'marker': snap.get('marker'), 'purpose': purpose}, 'WARN')
            duplicate = _window_diag_duplicate_marker(int(chat_id), message_id, str(snap.get('marker') or ''))
            if duplicate:
                _window_diag_emit('window_duplicate_marker_candidate', chat_id, message_id, {'marker': snap.get('marker'), 'previous_message_id': duplicate.get('message_id'), 'previous_seq': duplicate.get('seq'), 'purpose': purpose}, 'WARN')
        return result
    return _wrapped

def _window_diag_delete_wrapper(original):

    def _wrapped(*args, **kwargs):
        chat_id = kwargs.get('chat_id') if kwargs.get('chat_id') is not None else args[0] if args else None
        message_id = kwargs.get('message_id') if kwargs.get('message_id') is not None else args[1] if len(args) > 1 else None
        before = _window_diag_state_get(chat_id, message_id)
        candidate = bool(before)
        try:
            if not candidate:
                getter = globals().get('get_registered_open_window')
                candidate = bool(getter(int(chat_id), int(message_id))) if callable(getter) else False
        except Exception:
            pass
        try:
            result = original(*args, **kwargs)
        except Exception as exc:
            if candidate:
                low = str(exc or '').lower()
                already_gone = any((token in low for token in ('message to delete not found', 'message_id_invalid', 'message not found')))
                unavailable = "can't be deleted for everyone" in low or "message can't be deleted" in low
                if already_gone or unavailable:
                    deleted = _window_diag_state_set(chat_id, message_id, before, 'delete_message', '', deleted=True)
                    _window_diag_emit('window_delete_already_gone' if already_gone else 'window_delete_unavailable', chat_id, message_id, {'marker': before.get('marker'), 'error': str(exc)[:360], 'to_seq': deleted.get('seq')}, 'INFO')
                    try:
                        unregister = globals().get('unregister_open_window')
                        if callable(unregister):
                            unregister(int(chat_id), int(message_id))
                    except Exception:
                        pass
                else:
                    _window_diag_emit('window_delete_failed', chat_id, message_id, {'marker': before.get('marker'), 'error': str(exc)[:360]}, 'WARN')
            raise
        if candidate:
            deleted = _window_diag_state_set(chat_id, message_id, before, 'delete_message', '', deleted=True)
            _window_diag_emit('window_deleted', chat_id, message_id, {'marker': before.get('marker'), 'hash': before.get('text_hash'), 'to_seq': deleted.get('seq')}, 'INFO')
            try:
                unregister = globals().get('unregister_open_window')
                if callable(unregister):
                    unregister(int(chat_id), int(message_id))
            except Exception:
                pass
        return result
    return _wrapped

def _window_diag_reply_markup_wrapper(original):

    def _wrapped(*args, **kwargs):
        chat_id = kwargs.get('chat_id') if kwargs.get('chat_id') is not None else args[0] if args else None
        message_id = kwargs.get('message_id') if kwargs.get('message_id') is not None else args[1] if len(args) > 1 else None
        reply_markup = kwargs.get('reply_markup')
        before = _window_diag_state_get(chat_id, message_id)
        candidate = bool(before or reply_markup is not None)
        kb = _window_diag_keyboard(reply_markup) if candidate else {}
        try:
            result = original(*args, **kwargs)
        except Exception as exc:
            if candidate:
                _window_diag_emit('window_keyboard_edit_failed', chat_id, message_id, {'marker': before.get('marker'), 'from_keyboard': before.get('keyboard_hash'), 'to_keyboard': kb.get('hash'), 'error': str(exc)[:360]}, 'WARN')
            raise
        if candidate:
            snap = dict(before)
            snap.update({'keyboard_hash': kb.get('hash') or '', 'buttons': kb.get('buttons') or 0, 'callbacks': kb.get('callbacks') or []})
            state = _window_diag_state_set(chat_id, message_id, snap, 'edit_message_reply_markup', '')
            _window_diag_emit('window_keyboard_edited', chat_id, message_id, {'marker': before.get('marker'), 'from_keyboard': before.get('keyboard_hash'), 'to_keyboard': kb.get('hash'), 'buttons': kb.get('buttons'), 'to_seq': state.get('seq')}, 'INFO')
        return result
    return _wrapped

def _install_window_transport_diagnostics():
    global _WINDOW_DIAG_INSTALLED
    if _WINDOW_DIAG_INSTALLED or not WINDOW_DIAGNOSTICS_ENABLED:
        return
    methods = {'edit_message_text': _window_diag_edit_wrapper, 'edit_message_caption': _window_diag_edit_wrapper, 'send_message': lambda _name, original: _window_diag_send_wrapper(original), 'delete_message': lambda _name, original: _window_diag_delete_wrapper(original), 'edit_message_reply_markup': lambda _name, original: _window_diag_reply_markup_wrapper(original)}
    for name, factory in methods.items():
        original = getattr(bot, name, None)
        if not callable(original):
            continue
        _WINDOW_DIAG_ORIGINAL_METHODS[name] = original
        setattr(bot, name, factory(name, original))
    _WINDOW_DIAG_INSTALLED = True
    _window_diag_emit('window_diagnostics_installed', None, None, {'methods': sorted(_WINDOW_DIAG_ORIGINAL_METHODS), 'tail_limit': WINDOW_DIAGNOSTICS_TAIL_LIMIT, 'state_limit': WINDOW_DIAGNOSTICS_STATE_LIMIT}, 'INFO')
_ORIGINAL_WINDOW_REGISTER = _v177_legacy_0041_register_open_window
if callable(_ORIGINAL_WINDOW_REGISTER):

    def register_open_window(chat_id: int, message_id: int, window_type: str, code: str='', day_key: str | None=None, params: dict | None=None):
        before = None
        try:
            before = get_registered_open_window(int(chat_id), int(message_id))
        except Exception:
            before = None
        result = _ORIGINAL_WINDOW_REGISTER(chat_id, message_id, window_type, code=code, day_key=day_key, params=params)
        after = None
        try:
            after = get_registered_open_window(int(chat_id), int(message_id))
        except Exception:
            after = None
        before_sig = _window_diag_hash(json.dumps(before or {}, ensure_ascii=False, sort_keys=True, default=str))
        after_sig = _window_diag_hash(json.dumps(after or {}, ensure_ascii=False, sort_keys=True, default=str))
        if before_sig != after_sig:
            marker = ''
            try:
                marker = _window_marker_code(code or window_type)
            except Exception:
                pass
            _window_diag_emit('window_registry_registered' if not before else 'window_registry_changed', chat_id, message_id, {'window_type_before': (before or {}).get('window_type'), 'window_type_after': str(window_type or ''), 'code_before': (before or {}).get('code'), 'code_after': str(code or ''), 'marker': marker, 'day_before': (before or {}).get('day_key'), 'day_after': day_key, 'params_hash_before': _window_diag_hash(json.dumps((before or {}).get('params') or {}, ensure_ascii=False, sort_keys=True, default=str)), 'params_hash_after': _window_diag_hash(json.dumps(params or {}, ensure_ascii=False, sort_keys=True, default=str))}, 'WARN' if before and ((before or {}).get('window_type') != str(window_type or '') or (before or {}).get('code') != str(code or '')) else 'INFO')
        return result
_ORIGINAL_WINDOW_UNREGISTER = _v177_legacy_0042_unregister_open_window
if callable(_ORIGINAL_WINDOW_UNREGISTER):

    def unregister_open_window(chat_id: int, message_id: int):
        before = None
        try:
            before = get_registered_open_window(int(chat_id), int(message_id))
        except Exception:
            before = None
        result = _ORIGINAL_WINDOW_UNREGISTER(chat_id, message_id)
        if before:
            _window_diag_emit('window_registry_unregistered', chat_id, message_id, {'window_type': before.get('window_type'), 'code': before.get('code'), 'day': before.get('day_key')}, 'INFO')
        return result

def window_diagnostic_snapshot() -> dict:
    with _WINDOW_DIAG_LOCK:
        states = [dict(v) for v in _WINDOW_DIAG_STATE.values()]
        counters = dict(_WINDOW_DIAG_COUNTERS)
        events_count = len(_WINDOW_DIAG_EVENTS)
    active = [x for x in states if not bool(x.get('deleted'))]
    suspicious_names = {'window_stale_edit_apply', 'window_transport_stale_request', 'window_recreated', 'window_duplicate_marker_candidate', 'window_edit_target_missing', 'window_edit_failed', 'window_send_failed', 'window_delete_failed', 'window_registry_changed'}
    return {'enabled': bool(WINDOW_DIAGNOSTICS_ENABLED), 'installed': bool(_WINDOW_DIAG_INSTALLED), 'events_in_memory': events_count, 'tracked_windows': len(states), 'active_windows': len(active), 'deleted_windows_retained': len(states) - len(active), 'last_sequence': int(_WINDOW_DIAG_SEQ), 'counters': counters, 'suspicious_total': sum((int(counters.get(name, 0) or 0) for name in suspicious_names)), 'active_by_marker': dict(sorted({m: sum((1 for x in active if str(x.get('marker') or '') == m)) for m in {str(x.get('marker') or '') for x in active if x.get('marker')}}.items()))}

def window_diagnostic_tail(limit: int=500) -> list[dict]:
    try:
        limit = max(1, min(WINDOW_DIAGNOSTICS_TAIL_LIMIT, int(limit or 500)))
    except Exception:
        limit = 500
    with _WINDOW_DIAG_LOCK:
        return [copy.deepcopy(x) for x in list(_WINDOW_DIAG_EVENTS)[-limit:]]

def window_diag_compact_for_memory(level: str='warning') -> dict:
    """Shrink only in-RAM window trace. Durable journal rows remain in MEGA."""
    level = str(level or 'warning').lower()
    event_keep = {'warning': 600, 'high': 350, 'critical': 220, 'emergency': 120}.get(level, 600)
    state_keep = {'warning': 1000, 'high': 650, 'critical': 400, 'emergency': 250}.get(level, 1000)
    with _WINDOW_DIAG_LOCK:
        before_events = len(_WINDOW_DIAG_EVENTS)
        before_states = len(_WINDOW_DIAG_STATE)
        if before_events > event_keep:
            tail = list(_WINDOW_DIAG_EVENTS)[-event_keep:]
            _WINDOW_DIAG_EVENTS.clear()
            _WINDOW_DIAG_EVENTS.extend(tail)
        if before_states > state_keep:
            ordered = sorted(_WINDOW_DIAG_STATE.items(), key=lambda kv: int((kv[1] or {}).get('seq') or 0), reverse=True)
            keep_keys = {k for k, _ in ordered[:state_keep]}
            for key in list(_WINDOW_DIAG_STATE):
                if key not in keep_keys:
                    _WINDOW_DIAG_STATE.pop(key, None)
        return {'level': level, 'events': [before_events, len(_WINDOW_DIAG_EVENTS)], 'states': [before_states, len(_WINDOW_DIAG_STATE)]}

def window_diagnostic_stats() -> dict:
    return window_diagnostic_snapshot()
_install_window_transport_diagnostics()

# --- ИСТОЧНИК: 17_memory_runtime.py ---
import ctypes as _memory_ctypes
import gc as _memory_gc
import resource as _memory_resource

def _memory_env_float(name: str, default: float, minimum: float, maximum: float) -> float:
    try:
        return max(minimum, min(maximum, float(os.getenv(name, str(default)) or default)))
    except Exception:
        return float(default)

def _memory_env_int(name: str, default: int, minimum: int, maximum: int) -> int:
    try:
        return max(minimum, min(maximum, int(os.getenv(name, str(default)) or default)))
    except Exception:
        return int(default)
MEMORY_GUARD_ENABLED = str(os.getenv('MEMORY_GUARD_ENABLED', '1') or '1').strip().lower() not in {'0', 'false', 'off', 'no'}
MEMORY_GUARD_INTERVAL_SECONDS = _memory_env_float('MEMORY_GUARD_INTERVAL_SECONDS', 30.0, 10.0, 300.0)
MEMORY_SOFT_TRIM_MB = _memory_env_float('MEMORY_SOFT_TRIM_MB', 175.0, 128.0, 1024.0)
MEMORY_WARNING_MB = _memory_env_float('MEMORY_WARNING_MB', 300.0, 128.0, 2048.0)
MEMORY_HIGH_MB = _memory_env_float('MEMORY_HIGH_MB', 350.0, MEMORY_WARNING_MB + 10.0, 3072.0)
MEMORY_CRITICAL_MB = _memory_env_float('MEMORY_CRITICAL_MB', 400.0, MEMORY_HIGH_MB + 10.0, 4096.0)
MEMORY_EMERGENCY_MB = _memory_env_float('MEMORY_EMERGENCY_MB', 440.0, MEMORY_CRITICAL_MB + 10.0, 4096.0)
MEMORY_HEAVY_BLOCK_MB = _memory_env_float('MEMORY_HEAVY_BLOCK_MB', 395.0, MEMORY_HIGH_MB, 4096.0)
MEMORY_TRIM_COOLDOWN_SECONDS = _memory_env_float('MEMORY_TRIM_COOLDOWN_SECONDS', 45.0, 5.0, 600.0)
MEMORY_EVENT_KEEP = _memory_env_int('MEMORY_EVENT_KEEP', 200, 50, 1000)
MEMORY_SAFE_RESTART_ENABLED = str(os.getenv('MEMORY_SAFE_RESTART_ENABLED', '0') or '0').strip().lower() in {'1', 'true', 'on', 'yes'}
MEMORY_SAFE_RESTART_MB = _memory_env_float('MEMORY_SAFE_RESTART_MB', 455.0, MEMORY_EMERGENCY_MB, 4096.0)
MEMORY_SAFE_RESTART_MIN_UPTIME = _memory_env_float('MEMORY_SAFE_RESTART_MIN_UPTIME', 1800.0, 300.0, 86400.0)
_MEMORY_LOCK = threading.RLock()
_MEMORY_EVENTS = deque(maxlen=MEMORY_EVENT_KEEP)
_MEMORY_ACTIVE = {}
_MEMORY_SEQ = 0
_MEMORY_STATE = {'started': False, 'last_level': 'normal', 'last_check_at': '', 'last_trim_at': '', 'last_trim_reason': '', 'trim_count': 0, 'malloc_trim_count': 0, 'blocked_heavy_jobs': 0, 'safe_restart_requested': False, 'peak_container_mb_seen': 0.0, 'peak_python_mb_seen': 0.0, 'last_snapshot': {}}

def _memory_read_number(path: str):
    try:
        raw = Path(path).read_text(errors='ignore').strip()
        if not raw or raw.lower() == 'max':
            return None
        value = int(raw)
        if value < 0 or value >= 1 << 60:
            return None
        return value
    except Exception:
        return None

def _memory_bytes_mb(value):
    try:
        return round(float(value) / 1024.0 / 1024.0, 1)
    except Exception:
        return None

def _memory_cgroup_snapshot() -> dict:
    current = _memory_read_number('/sys/fs/cgroup/memory.current')
    peak = _memory_read_number('/sys/fs/cgroup/memory.peak')
    limit = _memory_read_number('/sys/fs/cgroup/memory.max')
    if current is None:
        current = _memory_read_number('/sys/fs/cgroup/memory/memory.usage_in_bytes')
    if peak is None:
        peak = _memory_read_number('/sys/fs/cgroup/memory/memory.max_usage_in_bytes')
    if limit is None:
        limit = _memory_read_number('/sys/fs/cgroup/memory/memory.limit_in_bytes')
    events = {}
    for candidate in ('/sys/fs/cgroup/memory.events', '/sys/fs/cgroup/memory/memory.failcnt'):
        try:
            if not os.path.exists(candidate):
                continue
            text = Path(candidate).read_text(errors='ignore').strip()
            if candidate.endswith('failcnt'):
                events['failcnt'] = int(text or 0)
            else:
                for line in text.splitlines():
                    parts = line.split()
                    if len(parts) == 2:
                        events[str(parts[0])] = int(parts[1])
            break
        except Exception:
            continue
    out = {'current_mb': _memory_bytes_mb(current), 'peak_mb': _memory_bytes_mb(peak), 'limit_mb': _memory_bytes_mb(limit), 'events': events}
    try:
        if out['current_mb'] is not None and out['limit_mb']:
            out['percent'] = round(100.0 * float(out['current_mb']) / float(out['limit_mb']), 1)
        else:
            out['percent'] = None
    except Exception:
        out['percent'] = None
    return out

def _memory_proc_rollup() -> dict:
    out = {}
    path = '/proc/self/smaps_rollup'
    if not os.path.exists(path):
        return out
    wanted = {'Rss:': 'rss_mb', 'Pss:': 'pss_mb', 'Private_Clean:': 'private_clean_mb', 'Private_Dirty:': 'private_dirty_mb', 'Shared_Clean:': 'shared_clean_mb', 'Shared_Dirty:': 'shared_dirty_mb', 'Anonymous:': 'anonymous_mb', 'Swap:': 'swap_mb'}
    try:
        for line in Path(path).read_text(errors='ignore').splitlines():
            for prefix, key in wanted.items():
                if line.startswith(prefix):
                    out[key] = round(float(line.split()[1]) / 1024.0, 1)
                    break
    except Exception:
        pass
    return out

def _memory_child_processes() -> list[dict]:
    rows = []
    try:
        child_file = f'/proc/{os.getpid()}/task/{os.getpid()}/children'
        raw = Path(child_file).read_text(errors='ignore').strip() if os.path.exists(child_file) else ''
        pids = [int(x) for x in raw.split() if x.isdigit()]
    except Exception:
        pids = []
    for pid in pids[:40]:
        row = {'pid': pid, 'rss_mb': None, 'name': '', 'cmd': ''}
        try:
            status = Path(f'/proc/{pid}/status').read_text(errors='ignore')
            for line in status.splitlines():
                if line.startswith('Name:'):
                    row['name'] = line.split(':', 1)[1].strip()[:80]
                elif line.startswith('VmRSS:'):
                    row['rss_mb'] = round(float(line.split()[1]) / 1024.0, 1)
        except Exception:
            pass
        try:
            cmd = Path(f'/proc/{pid}/cmdline').read_bytes().replace(b'\x00', b' ').decode('utf-8', 'replace').strip()
            row['cmd'] = cmd[:240]
        except Exception:
            pass
        rows.append(row)
    return rows

def telegram_download_to_file(file_path: str, target_path: str, max_bytes: int | None=None, chunk_size: int=1024 * 1024) -> int:
    """Stream a Telegram Bot API file to disk without creating one huge bytes object."""
    file_path = str(file_path or '').lstrip('/')
    if not file_path:
        raise ValueError('empty Telegram file_path')
    token = str(globals().get('BOT_TOKEN') or '').strip()
    if not token:
        raise RuntimeError('BOT_TOKEN is empty')
    os.makedirs(os.path.dirname(os.path.abspath(target_path)) or '.', exist_ok=True)
    url = f'https://api.telegram.org/file/bot{token}/{file_path}'
    total = 0
    with requests.get(url, stream=True, timeout=(15, 180)) as response:
        response.raise_for_status()
        with open(target_path, 'wb') as fh:
            for chunk in response.iter_content(chunk_size=max(65536, int(chunk_size or 0))):
                if not chunk:
                    continue
                total += len(chunk)
                if max_bytes is not None and total > int(max_bytes):
                    raise ValueError(f'Telegram file exceeds limit: {total} > {int(max_bytes)}')
                fh.write(chunk)
    return total

def memory_quick_snapshot() -> dict:
    runtime_fn = globals().get('_runtime_memory_stats')
    process = runtime_fn() if callable(runtime_fn) else {}
    cgroup = _memory_cgroup_snapshot()
    process_rss = process.get('rss_mb')
    container = cgroup.get('current_mb')
    effective = container if container is not None else process_rss
    with _MEMORY_LOCK:
        if container is not None:
            _MEMORY_STATE['peak_container_mb_seen'] = max(float(_MEMORY_STATE.get('peak_container_mb_seen') or 0), float(container))
        if process_rss is not None:
            _MEMORY_STATE['peak_python_mb_seen'] = max(float(_MEMORY_STATE.get('peak_python_mb_seen') or 0), float(process_rss))
    return {'effective_mb': effective, 'python_rss_mb': process_rss, 'python_peak_rss_mb': process.get('peak_rss_mb'), 'container_current_mb': container, 'container_peak_mb': cgroup.get('peak_mb'), 'limit_mb': cgroup.get('limit_mb') or process.get('limit_mb'), 'container_percent': cgroup.get('percent'), 'cgroup_events': cgroup.get('events') or {}}

def _memory_effective_thresholds(snapshot: dict | None=None) -> dict:
    snap = snapshot or {}
    try:
        limit = float(snap.get('limit_mb') or 0.0)
    except Exception:
        limit = 0.0
    return {'warning': max(MEMORY_WARNING_MB, limit * 0.58) if limit else MEMORY_WARNING_MB, 'high': max(MEMORY_HIGH_MB, limit * 0.68) if limit else MEMORY_HIGH_MB, 'critical': max(MEMORY_CRITICAL_MB, limit * 0.78) if limit else MEMORY_CRITICAL_MB, 'emergency': max(MEMORY_EMERGENCY_MB, limit * 0.86) if limit else MEMORY_EMERGENCY_MB, 'heavy_block': max(MEMORY_HEAVY_BLOCK_MB, limit * 0.77) if limit else MEMORY_HEAVY_BLOCK_MB, 'safe_restart': max(MEMORY_SAFE_RESTART_MB, limit * 0.89) if limit else MEMORY_SAFE_RESTART_MB}

def memory_level(snapshot: dict | None=None) -> str:
    snap = snapshot or memory_quick_snapshot()
    thresholds = _memory_effective_thresholds(snap)
    try:
        used = float(snap.get('effective_mb') or 0.0)
    except Exception:
        used = 0.0
    try:
        pct = float(snap.get('container_percent') or 0.0)
    except Exception:
        pct = 0.0
    if used >= thresholds['emergency'] or pct >= 86.0:
        return 'emergency'
    if used >= thresholds['critical'] or pct >= 78.0:
        return 'critical'
    if used >= thresholds['high'] or pct >= 68.0:
        return 'high'
    if used >= thresholds['warning'] or pct >= 58.0:
        return 'warning'
    return 'normal'

def _memory_emit(event: str, detail: dict | None=None, level: str='INFO'):
    global _MEMORY_SEQ
    with _MEMORY_LOCK:
        _MEMORY_SEQ += 1
        row = {'seq': _MEMORY_SEQ, 'ts': now_local().isoformat(timespec='milliseconds') if 'now_local' in globals() else datetime.now(timezone.utc).isoformat(timespec='milliseconds'), 'event': str(event), 'level': str(level).upper(), 'thread': threading.current_thread().name, 'detail': dict(detail or {})}
        _MEMORY_EVENTS.append(row)
    try:
        bot_journal(str(event), None, json.dumps(row['detail'], ensure_ascii=False, separators=(',', ':'), default=str)[:1800], row['level'])
    except Exception:
        pass
    return row

def _v177_legacy_0116_memory_malloc_trim() -> bool:
    try:
        libc = _memory_ctypes.CDLL('libc.so.6')
        result = int(libc.malloc_trim(0))
        with _MEMORY_LOCK:
            _MEMORY_STATE['malloc_trim_count'] = int(_MEMORY_STATE.get('malloc_trim_count') or 0) + 1
        return result == 1
    except Exception:
        return False
try:
    _v177_legacy_0116_memory_malloc_trim.__name__ = 'memory_malloc_trim'
except Exception:
    pass

def _memory_compact_logs(level: str):
    keep = 250 if level == 'warning' else 160 if level == 'high' else 100
    try:
        with bot_journal_lock:
            if len(BOT_ACTION_LOG) > keep:
                tail = list(BOT_ACTION_LOG)[-keep:]
                BOT_ACTION_LOG.clear()
                BOT_ACTION_LOG.extend(tail)
    except Exception:
        pass
    try:
        compact_fn = globals().get('window_diag_compact_for_memory')
        if callable(compact_fn):
            compact_fn(level)
    except Exception:
        pass
    try:
        for scheduler_name in ('DELAYED_SCHEDULER', 'CALLBACK_ACK_SCHEDULER'):
            scheduler = globals().get(scheduler_name)
            if scheduler is not None and hasattr(scheduler, 'compact'):
                scheduler.compact()
    except Exception:
        pass

def memory_trim(reason: str='manual', level: str | None=None, force: bool=False) -> dict:
    now_m = time.monotonic()
    with _MEMORY_LOCK:
        last = float(_MEMORY_STATE.get('last_trim_monotonic') or 0.0)
        if not force and now_m - last < MEMORY_TRIM_COOLDOWN_SECONDS:
            return {'skipped': 'cooldown', 'reason': reason, 'snapshot': memory_quick_snapshot()}
        _MEMORY_STATE['last_trim_monotonic'] = now_m
    before = memory_quick_snapshot()
    current_level = level or memory_level(before)
    try:
        idle_fn = globals().get('_lowram_business_busy')
        busy = bool(idle_fn()) if callable(idle_fn) else True
    except Exception:
        busy = True
    if not busy:
        try:
            flush_fn = globals().get('_lowram_flush_all_hot')
            if callable(flush_fn):
                flush_fn(evict=True)
        except Exception as exc:
            _memory_emit('memory_lowram_flush_error', {'reason': reason, 'error': str(exc)[:300]}, 'WARN')
    _memory_compact_logs(current_level)
    try:
        _memory_gc.collect()
    except Exception:
        pass
    trimmed = memory_malloc_trim()
    after = memory_quick_snapshot()
    with _MEMORY_LOCK:
        _MEMORY_STATE['last_trim_at'] = now_local().isoformat(timespec='seconds') if 'now_local' in globals() else datetime.now(timezone.utc).isoformat(timespec='seconds')
        _MEMORY_STATE['last_trim_reason'] = str(reason)
        _MEMORY_STATE['trim_count'] = int(_MEMORY_STATE.get('trim_count') or 0) + 1
    detail = {'reason': reason, 'level': current_level, 'busy': busy, 'malloc_trim': trimmed, 'before': before, 'after': after}
    _memory_emit('memory_trim', detail, 'WARN' if current_level in {'high', 'critical', 'emergency'} else 'INFO')
    return detail
_MEMORY_SECRET_KEY_RE = re.compile('(?:pass(?:word)?|secret|token|api[_-]?key|credential|auth|login)', re.I)

def _memory_redact_meta(kind: str, value, key: str=''):
    """Redact credentials before they enter active-operation state or diagnostics."""
    if isinstance(value, dict):
        return {str(k): _memory_redact_meta(kind, v, str(k)) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_memory_redact_meta(kind, item, key) for item in value]
    if value is None or isinstance(value, (bool, int, float)):
        return value
    text = str(value)
    protected = {str(globals().get('MEGA_EMAIL') or ''), str(globals().get('MEGA_PASSWORD') or ''), str(os.getenv('BOT_TOKEN') or ''), str(os.getenv('TELEGRAM_BOT_TOKEN') or ''), str(os.getenv('GOOGLE_SERVICE_ACCOUNT_JSON') or ''), str(os.getenv('TENANT_GOOGLE_MASTER_KEY') or ''), str(os.getenv('GOOGLE_TENANT_MASTER_KEY') or '')}
    protected.discard('')
    low_kind = str(kind or '').lower()
    if text in protected or _MEMORY_SECRET_KEY_RE.search(str(key or '')):
        return '<redacted>'
    if any((word in low_kind for word in ('login', 'auth', 'credential'))) and str(key or '').lower() in {'args', 'argv', 'command'}:
        return '<redacted>'
    return text[:500]

@contextmanager
def memory_operation(kind: str, meta: dict | None=None, heavy: bool=False, quiet: bool=False):
    global _MEMORY_SEQ
    kind = str(kind or 'operation')[:120]
    started = time.monotonic()
    before = memory_quick_snapshot()
    safe_meta = _memory_redact_meta(kind, dict(meta or {}))
    with _MEMORY_LOCK:
        _MEMORY_SEQ += 1
        token = f'mem-{_MEMORY_SEQ}'
        _MEMORY_ACTIVE[token] = {'kind': kind, 'started': started, 'thread': threading.current_thread().name, 'meta': safe_meta}
    try:
        yield token
    finally:
        elapsed = max(0.0, time.monotonic() - started)
        after_before_trim = memory_quick_snapshot()
        level = memory_level(after_before_trim)
        if heavy or level in {'high', 'critical', 'emergency'}:
            try:
                _memory_gc.collect()
            except Exception:
                pass
            memory_malloc_trim()
        after = memory_quick_snapshot()
        with _MEMORY_LOCK:
            _MEMORY_ACTIVE.pop(token, None)
        try:
            delta = round(float(after.get('effective_mb') or 0) - float(before.get('effective_mb') or 0), 1)
        except Exception:
            delta = None
        detail = {'kind': kind, 'elapsed': round(elapsed, 3), 'heavy': bool(heavy), 'delta_mb': delta, 'before': before, 'after_before_trim': after_before_trim, 'after': after, 'meta': safe_meta}
        should_emit = heavy or elapsed >= 3.0 or (delta is not None and abs(delta) >= 10.0) or (level != 'normal')
        if quiet:
            should_emit = level != 'normal' or elapsed >= 10.0 or (delta is not None and abs(delta) >= 20.0)
        if should_emit:
            _memory_emit('memory_operation', detail, 'WARN' if level in {'high', 'critical', 'emergency'} else 'INFO')

def memory_heavy_allowed(kind: str) -> tuple[bool, str]:
    snap = memory_quick_snapshot()
    level = memory_level(snap)
    kind_s = str(kind or 'export').lower()
    diagnostic = any((x in kind_s for x in ('journal', 'runtime')))
    used = float(snap.get('effective_mb') or 0.0)
    thresholds = _memory_effective_thresholds(snap)
    heavy_block = float(thresholds.get('heavy_block') or MEMORY_HEAVY_BLOCK_MB)
    if level == 'emergency' and (not diagnostic):
        with _MEMORY_LOCK:
            _MEMORY_STATE['blocked_heavy_jobs'] = int(_MEMORY_STATE.get('blocked_heavy_jobs') or 0) + 1
        return (False, f'Сервер разгружает память ({used:.0f} МБ). Финансы продолжают работать; тяжёлый файл временно не запускается.')
    if used >= heavy_block and (not diagnostic):
        memory_trim('heavy_job_gate', level=level, force=False)
        snap2 = memory_quick_snapshot()
        used2 = float(snap2.get('effective_mb') or 0.0)
        if used2 >= heavy_block:
            with _MEMORY_LOCK:
                _MEMORY_STATE['blocked_heavy_jobs'] = int(_MEMORY_STATE.get('blocked_heavy_jobs') or 0) + 1
            return (False, f'Память занята ({used2:.0f} МБ). Подождите 30–60 секунд и повторите экспорт.')
    return (True, '')

def _memory_worker_environment() -> dict:
    names = ['BOT_THREAD_STACK_KB', 'MALLOC_ARENA_MAX', 'PYTHONMALLOC', 'WEBHOOK_WORKERS', 'UI_WORKERS', 'CALLBACK_ACK_WORKERS', 'RECOVERY_WORKERS', 'REMINDER_WORKERS', 'FINANCE_WORKERS', 'FIN_FORWARD_WORKERS', 'FORWARD_WORKERS', 'BACKUP_WORKERS', 'DELTA_WORKERS', 'EXPORT_WORKERS', 'GENERAL_WORKERS', 'JOURNAL_WORKERS', 'DELAYED_WORKERS']
    return {name: os.getenv(name) for name in names if os.getenv(name) is not None}

def _memory_structure_snapshot(deep: bool=False) -> dict:
    result = {'threads': threading.active_count(), 'open_fds': None, 'worker_stack_kb': globals().get('_BOT_THREAD_STACK_KB'), 'glibc_allocator_v248': dict(globals().get('_GLIBC_ALLOCATOR_V248') or {}), 'soft_trim_mb': MEMORY_SOFT_TRIM_MB, 'worker_env_overrides': _memory_worker_environment()}
    try:
        result['open_fds'] = len(os.listdir('/proc/self/fd'))
    except Exception:
        pass
    try:
        chats = (globals().get('data') or {}).get('chats') or {}
        result['chats'] = len(chats)
        loaded = 0
        loaded_by_key = defaultdict(int)
        cold_keys = set(globals().get('LOWRAM_COLD_KEYS') or [])
        for store in chats.values():
            if isinstance(store, dict):
                for key in cold_keys:
                    if dict.__contains__(store, key):
                        loaded += 1
                        loaded_by_key[str(key)] += 1
        result['cold_fields_loaded'] = loaded
        result['cold_fields_by_key'] = dict(loaded_by_key)
    except Exception:
        pass
    try:
        audit_fn = globals().get('runtime_audit_metrics')
        if callable(audit_fn):
            result['audit_metrics'] = audit_fn()
    except Exception:
        pass
    try:
        wd_fn = globals().get('window_diagnostic_stats')
        if callable(wd_fn):
            result['window_diagnostics'] = wd_fn()
    except Exception:
        pass
    try:
        result['file_jobs'] = len(globals().get('_FILE_JOB_STATE') or {})
        result['journal_action_rows'] = len(globals().get('BOT_ACTION_LOG') or [])
        result['journal_buffer_rows'] = len(globals().get('_JOURNAL_DURABLE_BUFFER') or [])
        result['runtime_events'] = len(globals().get('_RUNTIME_EVENTS') or [])
        result['memory_events'] = len(_MEMORY_EVENTS)
        result['active_memory_operations'] = len(_MEMORY_ACTIVE)
    except Exception:
        pass
    try:
        sched = globals().get('DELAYED_SCHEDULER')
        result['delayed_scheduler'] = sched.stats() if sched is not None else {}
    except Exception:
        pass
    try:
        pools_fn = globals().get('_runtime_pool_stats')
        result['queues'] = pools_fn() if callable(pools_fn) else {}
    except Exception:
        pass
    if deep:
        try:
            result['gc_count'] = list(_memory_gc.get_count())
            result['gc_stats'] = _memory_gc.get_stats()
            result['ru_maxrss_mb'] = round(float(_memory_resource.getrusage(_memory_resource.RUSAGE_SELF).ru_maxrss) / 1024.0, 1)
        except Exception:
            pass
    return result

def memory_runtime_summary() -> dict:
    quick = memory_quick_snapshot()
    with _MEMORY_LOCK:
        state = {'last_level': _MEMORY_STATE.get('last_level'), 'last_check_at': _MEMORY_STATE.get('last_check_at'), 'last_trim_at': _MEMORY_STATE.get('last_trim_at'), 'last_trim_reason': _MEMORY_STATE.get('last_trim_reason'), 'trim_count': _MEMORY_STATE.get('trim_count'), 'malloc_trim_count': _MEMORY_STATE.get('malloc_trim_count'), 'blocked_heavy_jobs': _MEMORY_STATE.get('blocked_heavy_jobs'), 'peak_container_mb_seen': _MEMORY_STATE.get('peak_container_mb_seen'), 'peak_python_mb_seen': _MEMORY_STATE.get('peak_python_mb_seen'), 'active_operations': len(_MEMORY_ACTIVE), 'event_rows': len(_MEMORY_EVENTS)}
    children = _memory_child_processes()
    try:
        wd_fn = globals().get('window_diagnostic_stats')
        wd = wd_fn() if callable(wd_fn) else {}
    except Exception:
        wd = {}
    return {'level': memory_level(quick), 'quick': quick, 'state': state, 'children_rss_mb': round(sum((float(x.get('rss_mb') or 0.0) for x in children)), 1), 'children': children[:8], 'window_diagnostics': wd}

def memory_forensics_snapshot(deep: bool=False) -> dict:
    quick = memory_quick_snapshot()
    with _MEMORY_LOCK:
        state = dict(_MEMORY_STATE)
        active = {k: dict(v) for k, v in _MEMORY_ACTIVE.items()}
        events = list(_MEMORY_EVENTS)[-80:]
    return {'enabled': MEMORY_GUARD_ENABLED, 'level': memory_level(quick), 'thresholds_mb': {'configured': {'warning': MEMORY_WARNING_MB, 'high': MEMORY_HIGH_MB, 'critical': MEMORY_CRITICAL_MB, 'emergency': MEMORY_EMERGENCY_MB, 'heavy_block': MEMORY_HEAVY_BLOCK_MB}, 'effective': _memory_effective_thresholds(quick)}, 'quick': quick, 'process_rollup': _memory_proc_rollup(), 'children': _memory_child_processes(), 'structures': _memory_structure_snapshot(deep=deep), 'state': state, 'active_operations': active, 'events': events}

def _memory_safe_restart_possible() -> bool:
    if not MEMORY_SAFE_RESTART_ENABLED:
        return False
    try:
        uptime = time.monotonic() - float(globals().get('_RUNTIME_STARTED_MONO') or time.monotonic())
        if uptime < MEMORY_SAFE_RESTART_MIN_UPTIME:
            return False
    except Exception:
        return False
    try:
        for pool_name in ('WEBHOOK_TASK_POOL', 'FINANCE_TASK_POOL', 'FIN_FORWARD_TASK_POOL', 'FORWARD_TASK_POOL', 'DELTA_TASK_POOL', 'RECOVERY_TASK_POOL'):
            pool = globals().get(pool_name)
            if pool is None:
                continue
            st = pool.stats() or {}
            if int(st.get('pending', 0) or 0) > 0 or int(st.get('active', 0) or 0) > 0:
                return False
        mt_fn = globals().get('mega_task_registry_stats')
        if callable(mt_fn):
            mt = mt_fn() or {}
            if int(mt.get('processing', 0) or 0) > 0 or int(mt.get('pending', 0) or 0) > 0 or int(mt.get('running', 0) or 0) > 0:
                return False
    except Exception:
        return False
    return True

def _memory_request_safe_restart(snapshot: dict):
    with _MEMORY_LOCK:
        if _MEMORY_STATE.get('safe_restart_requested'):
            return
        _MEMORY_STATE['safe_restart_requested'] = True
    _memory_emit('memory_safe_restart_requested', {'snapshot': snapshot}, 'CRITICAL')
    try:
        shutdown = globals().get('runtime_graceful_shutdown')
        if callable(shutdown):
            shutdown('MEMORY_GUARD')
    finally:
        os._exit(0)

def memory_guard_tick():
    if not MEMORY_GUARD_ENABLED:
        return
    try:
        snap = memory_quick_snapshot()
        level = memory_level(snap)
        with _MEMORY_LOCK:
            previous = str(_MEMORY_STATE.get('last_level') or 'normal')
            _MEMORY_STATE['last_level'] = level
            _MEMORY_STATE['last_check_at'] = now_local().isoformat(timespec='seconds') if 'now_local' in globals() else datetime.now(timezone.utc).isoformat(timespec='seconds')
            _MEMORY_STATE['last_snapshot'] = dict(snap)
        if level != previous:
            _memory_emit('memory_level_changed', {'from': previous, 'to': level, 'snapshot': snap}, 'WARN' if level != 'normal' else 'INFO')
        # v247: trim fragmentation before the adaptive cgroup warning threshold.
        # UI/finance work is never blocked; memory_trim already respects cooldown/busy state.
        python_rss = float(snap.get('python_rss_mb') or snap.get('rss_mb') or 0.0)
        if python_rss >= MEMORY_SOFT_TRIM_MB and level == 'normal':
            memory_trim('guard:soft', level='normal', force=False)
        if level in {'warning', 'high', 'critical', 'emergency'}:
            memory_trim(f'guard:{level}', level=level, force=level == 'emergency')
        if level == 'emergency':
            refreshed = memory_quick_snapshot()
            used = float(refreshed.get('effective_mb') or 0.0)
            if used >= float(_memory_effective_thresholds(refreshed).get('safe_restart') or MEMORY_SAFE_RESTART_MB) and _memory_safe_restart_possible():
                _memory_request_safe_restart(refreshed)
    except Exception as exc:
        _memory_emit('memory_guard_error', {'error': str(exc)[:500]}, 'ERROR')
    finally:
        try:
            DELAYED_SCHEDULER.schedule('memory-guard', MEMORY_GUARD_INTERVAL_SECONDS, memory_guard_tick)
        except Exception:
            pass

def start_memory_runtime_schedulers():
    if not MEMORY_GUARD_ENABLED:
        return False
    with _MEMORY_LOCK:
        if _MEMORY_STATE.get('started'):
            return False
        _MEMORY_STATE['started'] = True
    _memory_emit('memory_guard_started', {'interval': MEMORY_GUARD_INTERVAL_SECONDS, 'thresholds': {'warning': MEMORY_WARNING_MB, 'high': MEMORY_HIGH_MB, 'critical': MEMORY_CRITICAL_MB, 'emergency': MEMORY_EMERGENCY_MB}, 'thread_stack_kb': globals().get('_BOT_THREAD_STACK_KB'), 'env_overrides': _memory_worker_environment()})
    DELAYED_SCHEDULER.schedule('memory-guard', 5.0, memory_guard_tick)
    return True

# --- ИСТОЧНИК: 20_callback_tokens.py ---
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
