# v262
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
# v262
