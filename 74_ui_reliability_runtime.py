# v262
"""v155: full button/navigation audit hardening and live callback outcome diagnostics."""
import copy as _v155_copy
import gzip as _v155_gzip
import json as _v155_json
import os as _v155_os
import shutil as _v155_shutil
import sqlite3 as _v155_sqlite3
import tempfile as _v155_tempfile
import re as _v155_re
import threading as _v155_threading
import time as _v155_time
from collections import deque as _v155_deque
V155_BUTTON_AUDIT_ENABLED = str(_v155_os.getenv('BUTTON_OUTCOME_AUDIT', '1') or '1').strip().lower() not in {'0', 'false', 'off', 'no'}
_V155_BUTTON_AUDIT_LOCK = _v155_threading.RLock()
_V155_BUTTON_AUDIT_RECENT = _v155_deque(maxlen=500)
_V155_BUTTON_AUDIT_INSTALLED = 0

def _v155_source_marker(call) -> str:
    try:
        msg = getattr(call, 'message', None)
        text = getattr(msg, 'text', None) or getattr(msg, 'caption', None) or ''
        fn = globals().get('_window_diag_marker')
        if callable(fn):
            return str(fn(text) or '')
        m = _v155_re.search('(?:^|\\s)([СФПОВсов]\\d{1,6})(?:\\s*[⏳⏰])?\\s*$', str(text or ''), flags=_v155_re.IGNORECASE)
        return str(m.group(1) if m else '').upper()
    except Exception:
        return ''

def _v155_button_label(call, raw_data: str, resolved_data: str) -> str:
    try:
        markup = getattr(getattr(call, 'message', None), 'reply_markup', None)
        for row in list(getattr(markup, 'keyboard', None) or []):
            for button in row or []:
                cb = str(getattr(button, 'callback_data', '') or '')
                resolved = cb
                try:
                    resolver = globals().get('resolve_short_callback')
                    if callable(resolver):
                        resolved = resolver(cb) or cb
                except Exception:
                    pass
                if cb == raw_data or str(resolved) == str(resolved_data):
                    return str(getattr(button, 'text', '') or '')[:120]
    except Exception:
        pass
    return ''

def _v177_legacy_0293_v155_expected_marker(action: str, chat_id: int) -> str:
    try:
        fn = globals().get('window_code_for_callback')
        owner_fn = globals().get('is_owner_chat')
        if callable(fn):
            return str(fn(action, owner_chat=bool(owner_fn(chat_id) if callable(owner_fn) else False)) or '')
    except Exception:
        pass
    return ''
try:
    _v177_legacy_0293_v155_expected_marker.__name__ = '_v155_expected_marker'
except Exception:
    pass

def _v155_window_events_since(seq: int, chat_id: int, message_id: int) -> list[dict]:
    try:
        tail_fn = globals().get('window_diagnostic_tail')
        if not callable(tail_fn):
            return []
        rows = []
        for row in tail_fn(120):
            try:
                if int(row.get('seq') or 0) <= int(seq or 0):
                    continue
                row_chat = row.get('chat_id')
                row_msg = row.get('message_id')
                if row_chat is not None and int(row_chat) != int(chat_id):
                    continue
                if row_msg is not None and int(row_msg) != int(message_id):
                    pass
                rows.append(row)
            except Exception:
                continue
        return rows[-30:]
    except Exception:
        return []

def _v155_summarize_effect(events: list[dict], source_message_id: int) -> tuple[str, str, str]:
    if not events:
        return ('handled_no_window_change', '', '')
    names = [str((row or {}).get('action') or '') for row in events]
    failure_order = ('window_edit_target_missing', 'window_edit_failed', 'window_keyboard_edit_failed', 'window_delete_failed', 'window_send_failed', 'window_transport_stale_request', 'window_stale_edit_apply')
    for name in failure_order:
        if name in names:
            row = next((x for x in reversed(events) if str((x or {}).get('action') or '') == name), {})
            return (name, str(((row or {}).get('detail') or {}).get('to_marker') or ''), ','.join(names[-8:]))
    if 'window_edit_applied' in names:
        row = next((x for x in reversed(events) if str((x or {}).get('action') or '') == 'window_edit_applied'), {})
        detail = (row or {}).get('detail') or {}
        return ('edited', str(detail.get('to_marker') or detail.get('marker') or ''), ','.join(names[-8:]))
    if 'window_edit_not_modified' in names:
        row = next((x for x in reversed(events) if str((x or {}).get('action') or '') == 'window_edit_not_modified'), {})
        detail = (row or {}).get('detail') or {}
        return ('already_current', str(detail.get('to_marker') or ''), ','.join(names[-8:]))
    if 'window_deleted' in names:
        return ('deleted', '', ','.join(names[-8:]))
    if 'window_created' in names:
        row = next((x for x in reversed(events) if str((x or {}).get('action') or '') == 'window_created'), {})
        detail = (row or {}).get('detail') or {}
        return ('created', str(detail.get('marker') or detail.get('to_marker') or ''), ','.join(names[-8:]))
    return ('handled', '', ','.join(names[-8:]))

def _v155_record_button_outcome(call, raw_data: str, resolved_data: str, started: float, seq_before: int, error: str='') -> None:
    if not V155_BUTTON_AUDIT_ENABLED:
        return
    try:
        msg = getattr(call, 'message', None)
        chat_id = int(getattr(getattr(msg, 'chat', None), 'id', 0) or 0)
        message_id = int(getattr(msg, 'message_id', 0) or 0)
        events = _v155_window_events_since(seq_before, chat_id, message_id)
        result, actual_marker, event_names = _v155_summarize_effect(events, message_id)
        if error:
            result = 'exception'
        close_action = str(resolved_data or raw_data or '') in {'aux_close', 'info_close'}
        if close_action and result in {'window_edit_target_missing', 'window_delete_failed', 'handled_no_window_change'}:
            result = 'already_closed'
        row = {'ts': now_local().isoformat(timespec='milliseconds') if 'now_local' in globals() else '', 'chat_id': chat_id, 'message_id': message_id, 'user_id': int(getattr(getattr(call, 'from_user', None), 'id', 0) or 0), 'button': _v155_button_label(call, raw_data, resolved_data), 'callback': str(resolved_data or raw_data)[:220], 'source_marker': _v155_source_marker(call), 'expected_marker': _v155_expected_marker(str(resolved_data or raw_data), chat_id), 'actual_marker': str(actual_marker or ''), 'result': result, 'elapsed_ms': int(max(0.0, _v155_time.monotonic() - started) * 1000), 'events': event_names[:500], 'error': str(error or '')[:300]}
        with _V155_BUTTON_AUDIT_LOCK:
            _V155_BUTTON_AUDIT_RECENT.append(row)
        if str(resolved_data or '') != 'none':
            bot_journal('button_outcome', chat_id, _v155_json.dumps(row, ensure_ascii=False, separators=(',', ':'), default=str)[:1750], 'ERROR' if result in {'exception', 'window_edit_failed', 'window_keyboard_edit_failed', 'window_delete_failed', 'window_send_failed', 'window_edit_target_missing'} else 'INFO')
    except Exception:
        pass

def v155_button_audit_recent(limit: int=100) -> list[dict]:
    try:
        limit = max(1, min(500, int(limit or 100)))
    except Exception:
        limit = 100
    with _V155_BUTTON_AUDIT_LOCK:
        return [_v155_copy.deepcopy(x) for x in list(_V155_BUTTON_AUDIT_RECENT)[-limit:]]
_V155_ORIG_O9_SECRET_TRIPLE_CLICK = _v177_legacy_0020_handle_o9_secret_triple_click

def _canon_handle_o9_secret_triple_click__001(call, data_str: str) -> bool:
    return False

def _v155_cancel_o9_click_state(chat_id: int, message_id: int) -> None:
    try:
        lock = globals().get('_o9_secret_click_lock')
        clicks = globals().get('_o9_secret_clicks')
        timers = globals().get('_o9_secret_action_timers')
        cancel = globals().get('_cancel_o9_secret_timer')
        if lock is None or not isinstance(clicks, dict):
            return
        with lock:
            keys = [k for k in list(clicks) if isinstance(k, tuple) and len(k) >= 2 and (int(k[0]) == int(chat_id)) and (int(k[1]) == int(message_id))]
        for key in keys:
            try:
                if callable(cancel):
                    cancel(key)
            except Exception:
                pass
            try:
                with lock:
                    clicks.pop(key, None)
                    if isinstance(timers, dict):
                        timers.pop(key, None)
            except Exception:
                pass
    except Exception:
        pass

def _v155_clear_nav_history(chat_id: int, message_id: int) -> None:
    try:
        clear_fn = globals().get('_nav_history_clear_v248')
        if callable(clear_fn):
            clear_fn(int(chat_id), int(message_id))
            return
        lock = globals().get('_WINDOW_NAV_HISTORY_LOCK')
        history = globals().get('_WINDOW_NAV_HISTORY')
        key_fn = globals().get('_window_nav_key')
        if lock is not None and isinstance(history, dict):
            key = key_fn(chat_id, message_id) if callable(key_fn) else (int(chat_id), int(message_id))
            with lock:
                history.pop(key, None)
    except Exception:
        pass

def _v155_clear_window_local_waits(chat_id: int, message_id: int) -> None:
    """Clear only waits attached to the message being turned into the main window."""
    try:
        store = get_chat_store(int(chat_id))
    except Exception:
        return
    try:
        wait = store.get('secret_wait') or {}
        wait_mid = int(wait.get('prompt_msg_id') or wait.get('window_msg_id') or 0)
        if wait_mid == int(message_id):
            fn = globals().get('_clear_secret_wait')
            if callable(fn):
                fn(int(chat_id), delete_prompt=False)
    except Exception:
        pass
    try:
        wait = store.get('forward_copy_edit_wait') or {}
        wait_mid = int(wait.get('prompt_msg_id') or 0)
        if wait_mid == int(message_id):
            fn = globals().get('clear_forward_copy_edit_wait')
            if callable(fn):
                fn(int(chat_id), delete_prompt=False)
    except Exception:
        pass
_V155_ORIG_RETURN_TO_MAIN = _v177_legacy_0242_return_to_main_window_closing_previous
if callable(_V155_ORIG_RETURN_TO_MAIN):

    def return_to_main_window_closing_previous(chat_id: int, day_key: str, current_message_id: int | None=None):
        try:
            if current_message_id is not None:
                _v155_cancel_o9_click_state(int(chat_id), int(current_message_id))
                _v155_clear_nav_history(int(chat_id), int(current_message_id))
                _v155_clear_window_local_waits(int(chat_id), int(current_message_id))
        except Exception:
            pass
        result = _V155_ORIG_RETURN_TO_MAIN(chat_id, day_key, current_message_id)
        try:
            bot_journal('back_main_clean', int(chat_id), f'day={str(day_key)[:10]}; msg={int(current_message_id or 0)}; secret_gesture=disabled; nav_history=cleared')
        except Exception:
            pass
        return result
_V155_ORIG_BUILD_EXPENSE_INBOX_KEYBOARD = globals().get('build_expense_inbox_keyboard')
if callable(_V155_ORIG_BUILD_EXPENSE_INBOX_KEYBOARD):

    def build_expense_inbox_keyboard(chat_id: int):
        kb = _V155_ORIG_BUILD_EXPENSE_INBOX_KEYBOARD(chat_id)
        try:
            for row in list(getattr(kb, 'keyboard', None) or []):
                for button in row or []:
                    if str(getattr(button, 'callback_data', '') or '') == 'expense_shortcut_test' and 'забы' in str(getattr(button, 'text', '') or '').casefold():
                        button.text = '🧪 Тест быстрой отметки'
        except Exception:
            pass
        return kb

def _v177_legacy_0280_v153_validate_restore_gz(gz_path: str) -> tuple[dict, str]:
    folder = _v155_tempfile.mkdtemp(prefix='v155_restore_validate_')
    raw = _v155_os.path.join(folder, 'restore.sqlite3')
    try:
        with _v155_gzip.open(gz_path, 'rb') as fin, open(raw, 'wb') as fout:
            _v155_shutil.copyfileobj(fin, fout, 1024 * 1024)
        conn = _v155_sqlite3.connect(raw)
        try:
            integrity = str(conn.execute('PRAGMA integrity_check').fetchone()[0])
            if integrity.lower() != 'ok':
                raise RuntimeError(f'SQLite integrity_check: {integrity}')
            row = conn.execute("SELECT v FROM meta WHERE kind='v153_export' AND k='manifest'").fetchone()
            if not row:
                raise RuntimeError('manifest v153 not found')
            manifest = _v155_json.loads(row[0])
        finally:
            conn.close()
        if str(manifest.get('kind')) != 'telegram_bot_full_state_v153':
            raise RuntimeError('unknown export kind')
        if int(manifest.get('schema_version') or 0) != int(V153_EXPORT_SCHEMA):
            raise RuntimeError('unsupported export schema')
        export_version = str(manifest.get('bot_version') or '')
        if not export_version.startswith(('bot_v153_', 'bot_v154_', 'bot_v155_')):
            raise RuntimeError(f"unsupported bot version: {export_version or 'missing'}")
        checksum = _v153_db_logical_checksum(raw)
        if checksum != str(manifest.get('checksum') or ''):
            raise RuntimeError('checksum mismatch')
        return (manifest, raw)
    except Exception:
        _v155_shutil.rmtree(folder, ignore_errors=True)
        raise
try:
    _v177_legacy_0280_v153_validate_restore_gz.__name__ = '_v153_validate_restore_gz'
except Exception:
    pass

def _v155_button_audit_summary_text() -> str:
    rows = v155_button_audit_recent(120)
    counts = {}
    suspicious = []
    for row in rows:
        result = str((row or {}).get('result') or 'unknown')
        counts[result] = int(counts.get(result, 0)) + 1
        expected = str((row or {}).get('expected_marker') or '')
        actual = str((row or {}).get('actual_marker') or '')
        if result in {'exception', 'window_edit_failed', 'window_keyboard_edit_failed', 'window_delete_failed', 'window_send_failed', 'window_edit_target_missing'}:
            suspicious.append(row)
        elif expected and actual and (expected not in {'Ф9998', 'С9998', 'П9998'}) and (expected != actual):
            suspicious.append(row)
    lines = ['🧭 АУДИТ КНОПОК v155', '', f"Live-аудит: {('✅ ВКЛ' if V155_BUTTON_AUDIT_ENABLED else '⬜ ВЫКЛ')}", f'Callback-обработчиков под наблюдением: {_V155_BUTTON_AUDIT_INSTALLED}', f'Последних кликов в памяти: {len(rows)}', f'Подозрительных результатов: {len(suspicious)}', '', 'Результаты: ' + (', '.join((f'{k}={v}' for k, v in sorted(counts.items()))) if counts else 'пока нет кликов после запуска'), '', 'Обычная кнопка «Назад осн. окно» больше не связана с секретным жестом О9.', 'Секретный доступ остаётся через существующие slash-команды /secret*/секрет*.']
    if suspicious:
        lines += ['', 'Последние подозрительные:']
        for row in suspicious[-8:]:
            lines.append(f"• {row.get('button') or row.get('callback')} → {row.get('result')} ({row.get('source_marker') or '-'}→{row.get('actual_marker') or row.get('expected_marker') or '-'})")
    return '\n'.join(lines)[:3900]

def v155_cmd_button_audit(msg):
    try:
        uid = int(getattr(getattr(msg, 'from_user', None), 'id', 0) or 0)
        chat_id = int(getattr(getattr(msg, 'chat', None), 'id', 0) or 0)
        owner = bool(uid and (uid == int(OWNER_ID or 0) or uid in {int(x) for x in get_additional_owner_ids()}))
        if not owner:
            bot.reply_to(msg, 'Команда доступна владельцу.')
            return
        bot.reply_to(msg, _v155_button_audit_summary_text())
    except Exception as exc:
        try:
            bot.reply_to(msg, f'Не удалось собрать аудит кнопок: {exc}')
        except Exception:
            pass
try:
    bot.message_handler(commands=['button_audit'])(v155_cmd_button_audit)
except Exception:
    pass
try:
    _v177_legacy_0007_bot_journal('v155_button_navigation_audit_installed', int(OWNER_ID or 0), f'callback_handlers={_V155_BUTTON_AUDIT_INSTALLED}; o9_button_gesture=disabled; back_main_clean=1; outcome_audit={int(V155_BUTTON_AUDIT_ENABLED)}')
except Exception:
    pass
'v156: persistent visual process status + strict USD-only Excel data/description isolation.'
import copy as _v156_copy
import gzip as _v156_gzip
import json as _v156_json
import os as _v156_os
import re as _v156_re
import shutil as _v156_shutil
import sqlite3 as _v156_sqlite3
import tempfile as _v156_tempfile
import threading as _v156_threading
import time as _v156_time
_V156_PROCESS_UI_LOCK = _v156_threading.RLock()
_V156_PROCESS_UI = {}
_V156_PROCESS_STATUS_DELAY = 0.8
_V156_PROCESS_STATUS_INTERVAL = 2.0
_V156_PROCESS_STATUS_KEY_PREFIX = 'v156-process-status:'

def _v177_legacy_0296_process_visual_status_enabled(chat_id: int) -> bool:
    try:
        settings = get_chat_store(int(chat_id)).setdefault('settings', {})
        return bool(settings.get('process_visual_status_enabled', True))
    except Exception:
        return True
try:
    _v177_legacy_0296_process_visual_status_enabled.__name__ = 'process_visual_status_enabled'
except Exception:
    pass

def set_process_visual_status_enabled(chat_id: int, enabled: bool) -> bool:
    chat_id = int(chat_id)
    settings = get_chat_store(chat_id).setdefault('settings', {})
    settings['process_visual_status_enabled'] = bool(enabled)
    try:
        save_data(data, chat_ids=[chat_id])
        schedule_config_backup_for_chats(chat_id, delay=0.5)
    except Exception:
        pass
    if not enabled:
        _v156_process_status_clear(chat_id, delete=True)
    try:
        bot_journal('process_visual_status_toggle', chat_id, f'enabled={int(bool(enabled))}')
    except Exception:
        pass
    return bool(enabled)

def toggle_process_visual_status(chat_id: int) -> bool:
    return set_process_visual_status_enabled(int(chat_id), not process_visual_status_enabled(int(chat_id)))

def process_visual_status_label(chat_id: int) -> str:
    return f"👁 Окно процессов: {('✅ ВКЛ' if process_visual_status_enabled(int(chat_id)) else '⬜ ВЫКЛ')}"

def _v156_process_status_clear(chat_id: int, delete: bool=False) -> None:
    chat_id = int(chat_id)
    try:
        DELAYED_SCHEDULER.cancel(f'{_V156_PROCESS_STATUS_KEY_PREFIX}{chat_id}')
    except Exception:
        pass
    with _V156_PROCESS_UI_LOCK:
        state = _V156_PROCESS_UI.pop(chat_id, None) or {}
    msg_id = int(state.get('message_id') or 0)
    if delete and msg_id:
        try:
            bot.delete_message(chat_id, msg_id)
        except Exception:
            pass

def _v156_active_process_rows(chat_id: int) -> list[dict]:
    """Only real registered operations for this chat; no unrelated global pools."""
    rows = []
    try:
        lock = globals().get('_PROCESS_CENTER_LOCK')
        runtime = globals().get('_PROCESS_RUNTIME') or {}
        if lock is not None:
            with lock:
                active = list((runtime.get('active') or {}).values())
        else:
            active = list((runtime.get('active') or {}).values())
        for row in active:
            try:
                if int((row or {}).get('chat_id') or 0) != int(chat_id):
                    continue
            except Exception:
                continue
            rows.append(_v156_copy.deepcopy(row))
    except Exception:
        pass
    rows.sort(key=lambda r: float((r or {}).get('started_mono') or 0.0))
    return rows

def _v156_process_status_text(chat_id: int, rows: list[dict], hint: str='') -> str:
    now_m = _v156_time.monotonic()
    lines = ['⏳ Операция выполняется']
    if hint:
        lines.append(f'Действие: {str(hint)[:100]}')
    lines.append('')
    for row in rows[:6]:
        started = float((row or {}).get('started_mono') or now_m)
        elapsed = max(0, int(now_m - started))
        label = str((row or {}).get('label') or (row or {}).get('id') or 'Операция')
        phase = str((row or {}).get('phase') or 'выполняется')
        lines.append(f'• {label}: {phase} · {elapsed}с')
    if len(rows) > 6:
        lines.append(f'…ещё {len(rows) - 6}')
    lines.extend(['', 'Окно закроется после завершения процесса.'])
    return '\n'.join(lines)[:3900]

def _v177_legacy_0301_v156_process_status_schedule(chat_id: int, delay: float) -> None:
    try:
        key = f'{_V156_PROCESS_STATUS_KEY_PREFIX}{int(chat_id)}'
        DELAYED_SCHEDULER.cancel(key)
        DELAYED_SCHEDULER.schedule(key, max(0.05, float(delay)), _v156_process_status_tick, int(chat_id))
    except Exception:
        pass
try:
    _v177_legacy_0301_v156_process_status_schedule.__name__ = '_v156_process_status_schedule'
except Exception:
    pass

def _v177_legacy_0305_v156_process_status_arm(chat_id: int | None, hint: str='') -> None:
    try:
        chat_id = int(chat_id or 0)
    except Exception:
        return
    if not chat_id or not process_visual_status_enabled(chat_id):
        return
    with _V156_PROCESS_UI_LOCK:
        state = _V156_PROCESS_UI.setdefault(chat_id, {'message_id': 0, 'hint': '', 'armed_at': _v156_time.monotonic()})
        if hint:
            state['hint'] = str(hint)[:120]
        state['armed_at'] = min(float(state.get('armed_at') or _v156_time.monotonic()), _v156_time.monotonic())
    _v156_process_status_schedule(chat_id, _V156_PROCESS_STATUS_DELAY)
try:
    _v177_legacy_0305_v156_process_status_arm.__name__ = '_v156_process_status_arm'
except Exception:
    pass

def _v177_legacy_0309_v156_process_status_tick(chat_id: int) -> None:
    chat_id = int(chat_id)
    if not process_visual_status_enabled(chat_id):
        _v156_process_status_clear(chat_id, delete=True)
        return
    rows = _v156_active_process_rows(chat_id)
    with _V156_PROCESS_UI_LOCK:
        state = _V156_PROCESS_UI.get(chat_id) or {}
        msg_id = int(state.get('message_id') or 0)
        hint = str(state.get('hint') or '')
    if not rows:
        if msg_id:
            try:
                bot.edit_message_text(f"✅ {hint or 'Операция'}\nВыполнено.", chat_id=chat_id, message_id=msg_id)
                delete_message_later(chat_id, msg_id, 4)
            except Exception:
                pass
        _v156_process_status_clear(chat_id, delete=False)
        return
    text = _v156_process_status_text(chat_id, rows, hint)
    if msg_id:
        try:
            bot.edit_message_text(text, chat_id=chat_id, message_id=msg_id)
        except Exception as exc:
            low = str(exc).casefold()
            if 'message is not modified' not in low:
                try:
                    bot_journal('process_visual_status_edit_error', chat_id, str(exc)[:300], 'WARN')
                except Exception:
                    pass
    else:
        try:
            sent = bot.send_message(chat_id, text)
            new_id = int(getattr(sent, 'message_id', 0) or 0)
            if new_id:
                with _V156_PROCESS_UI_LOCK:
                    if chat_id in _V156_PROCESS_UI:
                        _V156_PROCESS_UI[chat_id]['message_id'] = new_id
        except Exception:
            pass
    _v156_process_status_schedule(chat_id, _V156_PROCESS_STATUS_INTERVAL)
try:
    _v177_legacy_0309_v156_process_status_tick.__name__ = '_v156_process_status_tick'
except Exception:
    pass
_V156_ORIG_PROCESS_REGISTER = globals().get('process_register')
if callable(_V156_ORIG_PROCESS_REGISTER):

    def process_register(process_id: str, label: str, chat_id=None, phase: str='ожидает', cancellable: bool=False, meta: dict | None=None):
        result = _V156_ORIG_PROCESS_REGISTER(process_id, label, chat_id, phase=phase, cancellable=cancellable, meta=meta)
        _v156_process_status_arm(chat_id, str(label or 'Операция'))
        return result
_V156_ORIG_PROCESS_UPDATE = globals().get('process_update')
if callable(_V156_ORIG_PROCESS_UPDATE):

    def process_update(process_id: str, phase: str | None=None, details: str=''):
        result = _V156_ORIG_PROCESS_UPDATE(process_id, phase=phase, details=details)
        try:
            lock = globals().get('_PROCESS_CENTER_LOCK')
            runtime = globals().get('_PROCESS_RUNTIME') or {}
            if lock is not None:
                with lock:
                    row = _v156_copy.deepcopy((runtime.get('active') or {}).get(str(process_id)) or {})
            else:
                row = _v156_copy.deepcopy((runtime.get('active') or {}).get(str(process_id)) or {})
            if row:
                _v156_process_status_arm(row.get('chat_id'), row.get('label') or 'Операция')
        except Exception:
            pass
        return result
_V156_ORIG_PROCESS_FINISH = globals().get('process_finish')
if callable(_V156_ORIG_PROCESS_FINISH):

    def process_finish(process_id: str, ok: bool | None=True, details: str=''):
        chat_id = 0
        label = 'Операция'
        try:
            lock = globals().get('_PROCESS_CENTER_LOCK')
            runtime = globals().get('_PROCESS_RUNTIME') or {}
            if lock is not None:
                with lock:
                    row = _v156_copy.deepcopy((runtime.get('active') or {}).get(str(process_id)) or {})
            else:
                row = _v156_copy.deepcopy((runtime.get('active') or {}).get(str(process_id)) or {})
            chat_id = int(row.get('chat_id') or 0)
            label = str(row.get('label') or label)
        except Exception:
            pass
        result = _V156_ORIG_PROCESS_FINISH(process_id, ok=ok, details=details)
        if chat_id:
            _v156_process_status_arm(chat_id, label)
            _v156_process_status_schedule(chat_id, 0.08)
        return result

def _v177_legacy_0018_submit_interactive_file_job(chat_id: int, kind: str, label: str, func, *args, **kwargs) -> tuple[bool, str]:
    chat_id = int(chat_id)
    gate = globals().get('memory_heavy_allowed')
    if callable(gate):
        try:
            allowed, reason = gate(str(kind or 'export'))
        except Exception:
            allowed, reason = (True, '')
        if not allowed:
            try:
                send_and_auto_delete(chat_id, f'🧠 {reason}', 15)
            except Exception:
                pass
            return (False, reason or 'сервер временно разгружает память')
    key = _INTERACTIVE_FILE_JOB_KEY
    with _FILE_JOB_LOCK:
        existing = _FILE_JOB_STATE.get(key)
        if isinstance(existing, dict):
            return (False, build_all_processes_toast(chat_id))
        meta = {'key': key, 'chat_id': chat_id, 'kind': str(kind), 'label': str(label), 'queued_monotonic': _v156_time.monotonic(), 'started_monotonic': 0.0, 'phase': 'в очереди', 'status_msg_id': None, 'last_ui_monotonic': 0.0}
        _FILE_JOB_STATE[key] = meta
    if process_visual_status_enabled(chat_id):
        try:
            status = bot.send_message(chat_id, f'⏳ {label}\nВремя: 0:00\nЭтап: в очереди\nОкно останется до завершения операции.')
            with _FILE_JOB_LOCK:
                if isinstance(_FILE_JOB_STATE.get(key), dict):
                    _FILE_JOB_STATE[key]['status_msg_id'] = int(getattr(status, 'message_id', 0) or 0) or None
        except Exception:
            pass
    ok = EXPORT_TASK_POOL.submit_unique(key, _interactive_file_job_runner, dict(meta), func, args, kwargs)
    if not ok:
        with _FILE_JOB_LOCK:
            _FILE_JOB_STATE.pop(key, None)
        release_fn = globals().get('kv_distributed_lock_release_v248')
        if kv_lock_token and callable(release_fn):
            try:
                release_fn('interactive_file_job', kv_lock_token)
            except Exception:
                pass
        return (False, build_all_processes_toast(chat_id))
    try:
        DELAYED_SCHEDULER.cancel(f'file-job-tick:{key}')
        DELAYED_SCHEDULER.schedule(f'file-job-tick:{key}', internal_timer_seconds('process_status_refresh', 10.0), _file_job_tick, key)
    except Exception:
        pass
    try:
        bot_journal('file_job_queued', chat_id, f'kind={kind} label={label}; visual={int(process_visual_status_enabled(chat_id))}')
    except Exception:
        pass
    return (True, 'Запущено')
try:
    _v177_legacy_0018_submit_interactive_file_job.__name__ = 'submit_interactive_file_job'
except Exception:
    pass
_V156_ORIG_BUILD_INFO_KEYBOARD = _v177_legacy_0218_build_info_keyboard
if callable(_V156_ORIG_BUILD_INFO_KEYBOARD):

    def build_info_keyboard(chat_id: int):
        kb = _V156_ORIG_BUILD_INFO_KEYBOARD(int(chat_id))
        try:
            button = IB(process_visual_status_label(int(chat_id)), callback_data='v156:process_visual_toggle')
            rows = list(getattr(kb, 'keyboard', []) or [])
            insert_at = None
            for idx, row in enumerate(rows):
                if any((str(getattr(x, 'callback_data', '') or '') == 'process_center' for x in row or [])):
                    insert_at = idx + 1
                    break
            if insert_at is None:
                insert_at = max(0, len(rows) - 1)
            rows.insert(insert_at, [button])
            kb.keyboard = rows
        except Exception:
            try:
                kb.row(IB(process_visual_status_label(int(chat_id)), callback_data='v156:process_visual_toggle'))
            except Exception:
                pass
        return kb
_V156_ORIG_BUILD_INFO_TEXT = _v177_legacy_0055_build_info_text
if callable(_V156_ORIG_BUILD_INFO_TEXT):

    def build_info_text(chat_id: int) -> str:
        text = str(_V156_ORIG_BUILD_INFO_TEXT(int(chat_id)) or '')
        line = f"Окно процессов: {('✅ ВКЛ' if process_visual_status_enabled(int(chat_id)) else '⬜ ВЫКЛ')}"
        rows = text.splitlines()
        try:
            idx = rows.index('Слеш-команды:')
            rows[idx:idx] = [line, '']
        except Exception:
            rows.extend(['', line])
        return '\n'.join(rows)[:3900]

def _v156_handle_process_toggle(call) -> bool:
    raw = str(getattr(call, 'data', '') or '')
    resolved = raw
    try:
        resolver = globals().get('resolve_short_callback')
        if callable(resolver):
            resolved = str(resolver(raw) or raw)
    except Exception:
        pass
    if resolved != 'v156:process_visual_toggle':
        return False
    try:
        chat_id = int(call.message.chat.id)
        enabled = toggle_process_visual_status(chat_id)
        safe_edit(bot, call, build_info_text(chat_id), reply_markup=build_info_keyboard(chat_id))
        try:
            bot.answer_callback_query(call.id, f"Окно процессов: {('✅ ВКЛ' if enabled else '⬜ ВЫКЛ')}")
        except Exception:
            pass
        return True
    except Exception as exc:
        try:
            log_error(f'v156 process visual toggle: {exc}')
        except Exception:
            pass
        return True
try:
    WINDOW_MARKER_CONSTANTS['v156:process_visual_toggle'] = 'Ф9'
except Exception:
    pass

def _v156_store_ledgers(chat_id: int) -> tuple[dict, str, list[dict], list[dict]]:
    store = get_chat_store(int(chat_id))
    settings = store.setdefault('settings', {})
    active = str(settings.get('_active_currency_ledger') or '').strip().lower()
    if active not in {'ars', 'usd'}:
        try:
            active = str(_ensure_currency_ledgers(store) or 'ars').lower()
        except Exception:
            active = 'ars'
    ars = list((store.get('records') if active == 'ars' else store.get('ars_records')) or [])
    usd = list((store.get('records') if active == 'usd' else store.get('usd_records')) or [])
    return (store, active, ars, usd)

def _v156_record_identity(rec: dict) -> tuple:
    op = str((rec or {}).get('operation_key') or '').strip()
    if op:
        return ('op', op)
    try:
        mid = int((rec or {}).get('source_msg_id') or 0)
    except Exception:
        mid = 0
    if mid:
        return ('msg', mid)
    return ('fp', str((rec or {}).get('day_key') or _v151_day_key(rec))[:10], str((rec or {}).get('timestamp') or '')[:32], int((rec or {}).get('id') or 0))

def _v156_record_fingerprint(rec: dict) -> tuple:
    return (str((rec or {}).get('day_key') or _v151_day_key(rec))[:10], round(float((rec or {}).get('amount') or 0.0), 8), str((rec or {}).get('note') or '').strip().casefold(), int((rec or {}).get('source_msg_id') or 0), int((rec or {}).get('source_order_msg_id') or 0))

def _v156_explicit_currency(rec: dict) -> str:
    raw = str((rec or {}).get('currency') or '').strip().casefold()
    if raw in {'usd', '$', 'us$', 'u$s'}:
        return 'usd'
    if raw in {'ars', 'peso', 'pesos'}:
        return 'ars'
    return ''

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
_V156_ORIG_SNAPSHOT_LEDGER = globals().get('_snapshot_active_currency_ledger')
if callable(_V156_ORIG_SNAPSHOT_LEDGER):

    def _snapshot_active_currency_ledger(store: dict, ledger: str | None=None) -> None:
        ledger = str(ledger or (store.setdefault('settings', {}).get('_active_currency_ledger') or 'ars')).lower()
        ledger = 'usd' if ledger == 'usd' else 'ars'
        try:
            for rec in store.get('records', []) or []:
                if isinstance(rec, dict):
                    rec['currency'] = ledger.upper()
        except Exception:
            pass
        return _V156_ORIG_SNAPSHOT_LEDGER(store, ledger)
_V156_ORIG_LOAD_LEDGER = globals().get('_load_currency_ledger')
if callable(_V156_ORIG_LOAD_LEDGER):

    def _load_currency_ledger(store: dict, ledger: str) -> None:
        ledger = 'usd' if str(ledger).lower() == 'usd' else 'ars'
        result = _V156_ORIG_LOAD_LEDGER(store, ledger)
        try:
            for rec in store.get('records', []) or []:
                if isinstance(rec, dict):
                    rec['currency'] = ledger.upper()
        except Exception:
            pass
        return result

def _v177_legacy_0281_v153_validate_restore_gz(gz_path: str) -> tuple[dict, str]:
    folder = _v156_tempfile.mkdtemp(prefix='v156_restore_validate_')
    raw = _v156_os.path.join(folder, 'restore.sqlite3')
    try:
        with _v156_gzip.open(gz_path, 'rb') as fin, open(raw, 'wb') as fout:
            _v156_shutil.copyfileobj(fin, fout, 1024 * 1024)
        conn = _v156_sqlite3.connect(raw)
        try:
            integrity = str(conn.execute('PRAGMA integrity_check').fetchone()[0])
            if integrity.lower() != 'ok':
                raise RuntimeError(f'SQLite integrity_check: {integrity}')
            row = conn.execute("SELECT v FROM meta WHERE kind='v153_export' AND k='manifest'").fetchone()
            if not row:
                raise RuntimeError('manifest v153 not found')
            manifest = _v156_json.loads(row[0])
        finally:
            conn.close()
        if str(manifest.get('kind')) != 'telegram_bot_full_state_v153':
            raise RuntimeError('unknown export kind')
        if int(manifest.get('schema_version') or 0) != int(V153_EXPORT_SCHEMA):
            raise RuntimeError('unsupported export schema')
        export_version = str(manifest.get('bot_version') or '')
        if not export_version.startswith(('bot_v153_', 'bot_v154_', 'bot_v155_', 'bot_v156_')):
            raise RuntimeError(f"unsupported bot version: {export_version or 'missing'}")
        checksum = _v153_db_logical_checksum(raw)
        if checksum != str(manifest.get('checksum') or ''):
            raise RuntimeError('checksum mismatch')
        return (manifest, raw)
    except Exception:
        _v156_shutil.rmtree(folder, ignore_errors=True)
        raise
try:
    _v177_legacy_0281_v153_validate_restore_gz.__name__ = '_v153_validate_restore_gz'
except Exception:
    pass
_V156_CALLBACK_INTERCEPTS = 0
try:
    _v177_legacy_0007_bot_journal('v156_process_status_usd_excel_installed', int(OWNER_ID or 0), f'process_ui=1; callback_intercepts={_V156_CALLBACK_INTERCEPTS}; strict_usd_excel=1; ars_note_fallback=0')
except Exception:
    pass
'v157: process-window submenu, robust Back navigation, vertical INFO layout and button-log repairs.'
import gzip as _v157_gzip
import json as _v157_json
import os as _v157_os
import shutil as _v157_shutil
import sqlite3 as _v157_sqlite3
import tempfile as _v157_tempfile
import threading as _v157_threading
_V157_LEGACY_PROCESS_ENABLED = _v177_legacy_0296_process_visual_status_enabled
_V157_PROCESS_SETTINGS_KEY = 'process_visual_status_v157'

def _v157_is_primary_owner_chat(chat_id: int) -> bool:
    try:
        fn = globals().get('is_primary_owner')
        if callable(fn):
            return bool(fn(int(chat_id)))
    except Exception:
        pass
    try:
        return int(chat_id) == int(OWNER_ID or 0)
    except Exception:
        return False

def _v157_process_settings() -> dict:
    gs = data.setdefault('_global_settings', {})
    root = gs.get(_V157_PROCESS_SETTINGS_KEY)
    if not isinstance(root, dict):
        root = {}
        gs[_V157_PROCESS_SETTINGS_KEY] = root
    if 'owner_enabled' not in root:
        default = True
        try:
            if callable(_V157_LEGACY_PROCESS_ENABLED) and OWNER_ID:
                default = bool(_V157_LEGACY_PROCESS_ENABLED(int(OWNER_ID)))
        except Exception:
            default = True
        root['owner_enabled'] = default
    if 'others_enabled' not in root:
        root['others_enabled'] = True
    return root

def _v177_legacy_0297_process_visual_status_enabled(chat_id: int) -> bool:
    try:
        cfg = _v157_process_settings()
        return bool(cfg.get('owner_enabled', True) if _v157_is_primary_owner_chat(int(chat_id)) else cfg.get('others_enabled', True))
    except Exception:
        return True
try:
    _v177_legacy_0297_process_visual_status_enabled.__name__ = 'process_visual_status_enabled'
except Exception:
    pass

def _v157_save_process_settings() -> None:
    try:
        save_data(data, root_only=True)
    except Exception:
        pass
    try:
        if OWNER_ID:
            schedule_config_backup_for_chats(int(OWNER_ID), delay=0.5)
    except Exception:
        pass

def _v157_clear_process_scope(scope: str) -> None:
    try:
        with _V156_PROCESS_UI_LOCK:
            chat_ids = list((_V156_PROCESS_UI or {}).keys())
    except Exception:
        chat_ids = []
    for cid in chat_ids:
        try:
            is_owner = _v157_is_primary_owner_chat(int(cid))
            if scope == 'owner' and is_owner or (scope == 'others' and (not is_owner)):
                _v156_process_status_clear(int(cid), delete=True)
        except Exception:
            pass
    try:
        with _FILE_JOB_LOCK:
            jobs = [dict(x) for x in (_FILE_JOB_STATE or {}).values() if isinstance(x, dict)]
        for row in jobs:
            cid = int(row.get('chat_id') or 0)
            is_owner = _v157_is_primary_owner_chat(cid)
            if not (scope == 'owner' and is_owner or (scope == 'others' and (not is_owner))):
                continue
            mid = int(row.get('status_msg_id') or 0)
            if mid:
                try:
                    bot.delete_message(cid, mid)
                except Exception:
                    pass
                try:
                    with _FILE_JOB_LOCK:
                        for state in (_FILE_JOB_STATE or {}).values():
                            if isinstance(state, dict) and int(state.get('chat_id') or 0) == cid and (int(state.get('status_msg_id') or 0) == mid):
                                state['status_msg_id'] = None
                except Exception:
                    pass
    except Exception:
        pass

def _v157_set_process_scope(scope: str, enabled: bool) -> bool:
    cfg = _v157_process_settings()
    key = 'owner_enabled' if scope == 'owner' else 'others_enabled'
    cfg[key] = bool(enabled)
    _v157_save_process_settings()
    if not enabled:
        _v157_clear_process_scope(scope)
    try:
        bot_journal('process_visual_scope_toggle', int(OWNER_ID or 0), f'scope={scope}; enabled={int(bool(enabled))}')
    except Exception:
        pass
    return bool(enabled)

def _v157_process_menu_text() -> str:
    cfg = _v157_process_settings()
    return f"👁️ ОКНО ПРОЦЕССОВ\n\nПоказывает одно служебное сообщение, пока операция действительно выполняется. После завершения сообщение показывает результат и закрывается.\n\n👤 Для владельца: {('✅ ВКЛ' if cfg.get('owner_enabled', True) else '⬜ ВЫКЛ')}\n👥 Для других чатов и пользователей: {('✅ ВКЛ' if cfg.get('others_enabled', True) else '⬜ ВЫКЛ')}\n\nПереключатели ниже независимы друг от друга."

def _v157_process_menu_keyboard(chat_id: int):
    cfg = _v157_process_settings()
    kb = types.InlineKeyboardMarkup(row_width=1)
    kb.row(IB(f"{('✅' if cfg.get('owner_enabled', True) else '⬜')} 👤 Для владельца: {('ВКЛ' if cfg.get('owner_enabled', True) else 'ВЫКЛ')}", callback_data='v157:process_owner_toggle'))
    kb.row(IB(f"{('✅' if cfg.get('others_enabled', True) else '⬜')} 👥 Для других чатов и пользователей: {('ВКЛ' if cfg.get('others_enabled', True) else 'ВЫКЛ')}", callback_data='v157:process_others_toggle'))
    day = get_chat_store(int(chat_id)).get('current_view_day') or today_key()
    kb.row(IB('🔙 Назад в Инфо', callback_data=f'd:{day}:info'))
    kb.row(IB('⬅️ Назад в основное окно', callback_data=f'd:{day}:back_main'))
    return kb
_V157_ORIG_BUILD_INFO_TEXT = _v177_legacy_0055_build_info_text

def _v177_legacy_0056_build_info_text(chat_id: int, *args, **kwargs) -> str:
    text = ''
    try:
        if callable(_V157_ORIG_BUILD_INFO_TEXT):
            text = str(_V157_ORIG_BUILD_INFO_TEXT(int(chat_id)) or '')
    except TypeError:
        try:
            text = str(_V157_ORIG_BUILD_INFO_TEXT(int(chat_id), *args, **kwargs) or '')
        except Exception:
            text = ''
    cfg = _v157_process_settings()
    summary = f"Окно процессов: владелец {('✅ ВКЛ' if cfg.get('owner_enabled', True) else '⬜ ВЫКЛ')} · остальные {('✅ ВКЛ' if cfg.get('others_enabled', True) else '⬜ ВЫКЛ')}"
    rows = text.splitlines()
    replaced = False
    for idx, row in enumerate(rows):
        if str(row).strip().startswith('Окно процессов:'):
            rows[idx] = summary
            replaced = True
            break
    if not replaced:
        try:
            idx = rows.index('Слеш-команды:')
            rows[idx:idx] = [summary, '']
        except Exception:
            rows.extend(['', summary])
    return '\n'.join(rows)[:3900]
try:
    _v177_legacy_0056_build_info_text.__name__ = 'build_info_text'
except Exception:
    pass
_V157_ORIG_BUILD_INFO_KEYBOARD = _v177_legacy_0218_build_info_keyboard

def _v157_kb_rows(kb):
    return list(getattr(kb, 'keyboard', None) or getattr(kb, 'inline_keyboard', None) or [])

def _v157_btn_text(btn) -> str:
    if isinstance(btn, dict):
        return str(btn.get('text') or '')
    return str(getattr(btn, 'text', '') or '')

def _v157_btn_cb(btn) -> str:
    if isinstance(btn, dict):
        return str(btn.get('callback_data') or '')
    return str(getattr(btn, 'callback_data', '') or '')

def _v177_legacy_0219_build_info_keyboard(chat_id: int):
    kb = _V157_ORIG_BUILD_INFO_KEYBOARD(int(chat_id)) if callable(_V157_ORIG_BUILD_INFO_KEYBOARD) else types.InlineKeyboardMarkup()
    rows = _v157_kb_rows(kb)
    found_process = False
    for ridx, row in enumerate(rows):
        for bidx, btn in enumerate(list(row or [])):
            if _v157_btn_cb(btn) == 'v156:process_visual_toggle' or _v157_btn_text(btn).strip().startswith('👁 Окно процессов') or _v157_btn_text(btn).strip().startswith('👁️ Окно процессов'):
                rows[ridx][bidx] = IB('👁️ Окно процессов', callback_data='v157:process_menu')
                found_process = True
    if not found_process and is_owner_chat(int(chat_id)):
        insert_at = max(0, len(rows) - 1)
        rows.insert(insert_at, [IB('👁️ Окно процессов', callback_data='v157:process_menu')])
    start = None
    for idx, row in enumerate(rows):
        if any(('перес:' in _v157_btn_text(btn).casefold() for btn in row or [])):
            start = idx
            break
    if start is not None:
        head = rows[:start]
        tail = []
        for row in rows[start:]:
            for btn in row or []:
                tail.append([btn])
        rows = head + tail
    try:
        kb.keyboard = rows
    except Exception:
        try:
            kb.inline_keyboard = rows
        except Exception:
            pass
    return kb
try:
    _v177_legacy_0219_build_info_keyboard.__name__ = 'build_info_keyboard'
except Exception:
    pass

def _v157_process_message_missing(exc) -> bool:
    low = str(exc or '').casefold()
    return any((x in low for x in ('message_id_invalid', 'message id invalid', 'message to edit not found', 'message not found', 'message to delete not found')))

def _v177_legacy_0310_v156_process_status_tick(chat_id: int) -> None:
    chat_id = int(chat_id)
    if not process_visual_status_enabled(chat_id):
        _v156_process_status_clear(chat_id, delete=True)
        return
    rows = _v156_active_process_rows(chat_id)
    with _V156_PROCESS_UI_LOCK:
        state = _V156_PROCESS_UI.get(chat_id) or {}
        msg_id = int(state.get('message_id') or 0)
        hint = str(state.get('hint') or '')
    if not rows:
        if msg_id:
            try:
                bot.edit_message_text(f"✅ {hint or 'Операция'}\nВыполнено.", chat_id=chat_id, message_id=msg_id)
                delete_message_later(chat_id, msg_id, 4)
            except Exception as exc:
                if not _v157_process_message_missing(exc):
                    try:
                        bot_journal('process_visual_status_finish_error', chat_id, str(exc)[:300], 'WARN')
                    except Exception:
                        pass
        _v156_process_status_clear(chat_id, delete=False)
        return
    text = _v156_process_status_text(chat_id, rows, hint)
    if msg_id:
        try:
            bot.edit_message_text(text, chat_id=chat_id, message_id=msg_id)
        except Exception as exc:
            low = str(exc).casefold()
            if 'message is not modified' in low:
                pass
            elif _v157_process_message_missing(exc):
                with _V156_PROCESS_UI_LOCK:
                    if chat_id in _V156_PROCESS_UI:
                        _V156_PROCESS_UI[chat_id]['message_id'] = 0
                msg_id = 0
            else:
                try:
                    bot_journal('process_visual_status_edit_error', chat_id, str(exc)[:300], 'WARN')
                except Exception:
                    pass
    if not msg_id:
        try:
            sent = bot.send_message(chat_id, text, disable_notification=True)
            new_id = int(getattr(sent, 'message_id', 0) or 0)
            if new_id:
                with _V156_PROCESS_UI_LOCK:
                    if chat_id in _V156_PROCESS_UI:
                        _V156_PROCESS_UI[chat_id]['message_id'] = new_id
        except Exception:
            pass
    _v156_process_status_schedule(chat_id, _V156_PROCESS_STATUS_INTERVAL)
try:
    _v177_legacy_0310_v156_process_status_tick.__name__ = '_v156_process_status_tick'
except Exception:
    pass
try:
    WINDOW_MARKER_CONSTANTS['d:*:back_main'] = 'Ф91'
    if isinstance(globals().get('WINDOW_MARKER_CLOCK_CODES'), set):
        WINDOW_MARKER_CLOCK_CODES.add('Ф91')
except Exception:
    pass
try:
    WINDOW_MARKER_CONSTANTS.update({'sp:dashboard': 'Ф217', 'sp:list:*': 'Ф217', 'sp:open:*': 'Ф218', 'sp:users:*': 'Ф219', 'sp:chats:*': 'Ф220', 'sp:chatlink:*': 'Ф221', 'sp:userlink:*': 'Ф222', 'v152:r:l:*': 'Ф223', 'v152:r:c:*': 'Ф224', 'v152:r:t:*': 'Ф225', 'v152:r:g:*': 'Ф226', 'v152:r:i:*': 'Ф227', 'v152:r:p:*': 'Ф228', 'v152:r:x:*': 'Ф229', 'expense_quick_buttons_toggle': 'Ф230', 'v157:process_menu': 'Ф231', 'v157:process_owner_toggle': 'Ф231', 'v157:process_others_toggle': 'Ф231', 'v156:process_visual_toggle': 'Ф231'})
except Exception:
    pass
_V157_ORIG_V155_EXPECTED_MARKER = _v177_legacy_0293_v155_expected_marker

def _v177_legacy_0294_v155_expected_marker(action: str, chat_id: int) -> str:
    raw = str(action or '')
    if raw == 'nav_prev':
        return ''
    if raw.endswith(':back_main'):
        return 'Ф91'
    if raw == 'expense_quick_buttons_toggle':
        return ''
    if callable(_V157_ORIG_V155_EXPECTED_MARKER):
        try:
            return str(_V157_ORIG_V155_EXPECTED_MARKER(raw, int(chat_id)) or '')
        except Exception:
            pass
    return ''
try:
    _v177_legacy_0294_v155_expected_marker.__name__ = '_v155_expected_marker'
except Exception:
    pass
_V157_ORIG_RESTORE_PREVIOUS_WINDOW = _v177_legacy_0212_restore_previous_window

def _v177_legacy_0213_restore_previous_window(call) -> bool:
    try:
        chat_id = int(call.message.chat.id)
        message_id = int(call.message.message_id)
    except Exception:
        return False
    try:
        if callable(globals().get('window_has_previous')) and (not window_has_previous(chat_id, message_id)):
            day = get_chat_store(chat_id).get('current_view_day') or today_key()
            return_to_main_window_closing_previous(chat_id, day, current_message_id=message_id)
            try:
                bot_journal('nav_prev_fallback_main', chat_id, f'msg={message_id}; reason=no_history')
            except Exception:
                pass
            return True
    except Exception:
        pass
    ok = False
    try:
        ok = bool(_V157_ORIG_RESTORE_PREVIOUS_WINDOW(call)) if callable(_V157_ORIG_RESTORE_PREVIOUS_WINDOW) else False
    except Exception as exc:
        try:
            bot_journal('nav_prev_restore_error', chat_id, str(exc)[:300], 'WARN')
        except Exception:
            pass
        ok = False
    if ok:
        return True
    day = get_chat_store(chat_id).get('current_view_day') or today_key()
    return_to_main_window_closing_previous(chat_id, day, current_message_id=message_id)
    try:
        bot_journal('nav_prev_fallback_main', chat_id, f'msg={message_id}; reason=restore_failed')
    except Exception:
        pass
    return True
try:
    _v177_legacy_0213_restore_previous_window.__name__ = 'restore_previous_window'
except Exception:
    pass
_V157_ORIG_FORCE_NEW_DAY_WINDOW = _v177_legacy_0241_force_new_day_window

def _canon_force_new_day_window__001(chat_id: int, day_key: str):
    chat_id = int(chat_id)
    day_key = str(day_key)[:10]
    try:
        old_mid = get_active_window_id(chat_id, day_key)
        old_mid = int(old_mid) if old_mid else 0
    except Exception:
        old_mid = 0
    if old_mid:
        try:
            backup_window_for_owner(chat_id, day_key, message_id_override=old_mid)
            schedule_balance_panel_refresh(chat_id, 0.2)
            bot_journal('start_window_reused', chat_id, f'day={day_key}; previous={old_mid}; active={get_active_window_id(chat_id, day_key)}')
            return
        except Exception as exc:
            try:
                bot_journal('start_window_reuse_failed', chat_id, f'day={day_key}; msg={old_mid}; {str(exc)[:220]}', 'WARN')
            except Exception:
                pass
    if callable(_V157_ORIG_FORCE_NEW_DAY_WINDOW):
        return _V157_ORIG_FORCE_NEW_DAY_WINDOW(chat_id, day_key)
    return None
_V157_ORIG_RETURN_TO_MAIN = _v177_legacy_0242_return_to_main_window_closing_previous

def _v177_legacy_0243_return_to_main_window_closing_previous(chat_id: int, day_key: str, current_message_id: int | None=None):
    chat_id = int(chat_id)
    day_key = str(day_key)[:10]
    try:
        current_mid = int(current_message_id or 0)
    except Exception:
        current_mid = 0
    try:
        active_mid = int(get_active_window_id(chat_id, day_key) or 0)
    except Exception:
        active_mid = 0
    if current_mid and active_mid and (current_mid != active_mid):
        try:
            reg_fn = globals().get('get_registered_open_window')
            registered = reg_fn(chat_id, current_mid) if callable(reg_fn) else None
            if not registered and _v157_threading.current_thread().name.startswith(('delayed', 'general')):
                try:
                    backup_window_for_owner(chat_id, day_key, message_id_override=active_mid)
                    bot_journal('back_main_stale_timer_skipped', chat_id, f'stale={current_mid}; active={active_mid}; day={day_key}')
                    return
                except Exception:
                    pass
        except Exception:
            pass
    if callable(_V157_ORIG_RETURN_TO_MAIN):
        return _V157_ORIG_RETURN_TO_MAIN(chat_id, day_key, current_message_id=current_message_id)
    return None
try:
    _v177_legacy_0243_return_to_main_window_closing_previous.__name__ = 'return_to_main_window_closing_previous'
except Exception:
    pass

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
                    bot.edit_message_reply_markup(chat_id=target, message_id=mid, reply_markup=expense_draft_message_keyboard(int(draft.get('id') or 0), target))
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

def _v157_primary_actor(call) -> bool:
    try:
        return int(getattr(getattr(call, 'from_user', None), 'id', 0) or 0) == int(OWNER_ID or 0)
    except Exception:
        return False

def _v177_legacy_0314_v157_handle_callback(call) -> bool:
    raw = str(getattr(call, 'data', '') or '')
    resolved = raw
    try:
        resolver = globals().get('resolve_short_callback')
        if callable(resolver):
            resolved = str(resolver(raw) or raw)
    except Exception:
        pass
    if resolved not in {'v157:process_menu', 'v157:process_owner_toggle', 'v157:process_others_toggle', 'v156:process_visual_toggle'}:
        return False
    chat_id = int(call.message.chat.id)
    if resolved in {'v157:process_menu', 'v156:process_visual_toggle'}:
        safe_edit(bot, call, _v157_process_menu_text(), reply_markup=_v157_process_menu_keyboard(chat_id))
        return True
    if not _v157_primary_actor(call):
        try:
            bot.answer_callback_query(call.id, 'Эти переключатели доступны только основному владельцу.', show_alert=True)
        except Exception:
            pass
        return True
    scope = 'owner' if resolved == 'v157:process_owner_toggle' else 'others'
    cfg = _v157_process_settings()
    key = 'owner_enabled' if scope == 'owner' else 'others_enabled'
    enabled = _v157_set_process_scope(scope, not bool(cfg.get(key, True)))
    safe_edit(bot, call, _v157_process_menu_text(), reply_markup=_v157_process_menu_keyboard(chat_id))
    try:
        bot.answer_callback_query(call.id, f"{('Включено' if enabled else 'Выключено')}: {('владелец' if scope == 'owner' else 'другие чаты и пользователи')}")
    except Exception:
        pass
    return True
try:
    _v177_legacy_0314_v157_handle_callback.__name__ = '_v157_handle_callback'
except Exception:
    pass

def _v177_legacy_0282_v153_validate_restore_gz(gz_path: str) -> tuple[dict, str]:
    folder = _v157_tempfile.mkdtemp(prefix='v157_restore_validate_')
    raw = _v157_os.path.join(folder, 'restore.sqlite3')
    try:
        with _v157_gzip.open(gz_path, 'rb') as fin, open(raw, 'wb') as fout:
            _v157_shutil.copyfileobj(fin, fout, 1024 * 1024)
        conn = _v157_sqlite3.connect(raw)
        try:
            integrity = str(conn.execute('PRAGMA integrity_check').fetchone()[0])
            if integrity.lower() != 'ok':
                raise RuntimeError(f'SQLite integrity_check: {integrity}')
            row = conn.execute("SELECT v FROM meta WHERE kind='v153_export' AND k='manifest'").fetchone()
            if not row:
                raise RuntimeError('manifest v153 not found')
            manifest = _v157_json.loads(row[0])
        finally:
            conn.close()
        if str(manifest.get('kind')) != 'telegram_bot_full_state_v153':
            raise RuntimeError('unknown export kind')
        if int(manifest.get('schema_version') or 0) != int(V153_EXPORT_SCHEMA):
            raise RuntimeError('unsupported export schema')
        export_version = str(manifest.get('bot_version') or '')
        if not export_version.startswith(('bot_v153_', 'bot_v154_', 'bot_v155_', 'bot_v156_', 'bot_v157_')):
            raise RuntimeError(f"unsupported bot version: {export_version or 'missing'}")
        checksum = _v153_db_logical_checksum(raw)
        if checksum != str(manifest.get('checksum') or ''):
            raise RuntimeError('checksum mismatch')
        return (manifest, raw)
    except Exception:
        _v157_shutil.rmtree(folder, ignore_errors=True)
        raise
try:
    _v177_legacy_0282_v153_validate_restore_gz.__name__ = '_v153_validate_restore_gz'
except Exception:
    pass
_V157_CALLBACK_INTERCEPTS = 0
try:
    _v177_legacy_0007_bot_journal('v157_process_menu_navigation_repair_installed', int(OWNER_ID or 0), f'callback_intercepts={_V157_CALLBACK_INTERCEPTS}; process_scopes=2; info_vertical_from_peres=1; back_main_marker=Ф91; nav_prev_fallback=1; start_window_reuse=1; stale_quick_buttons=1')
except Exception:
    pass
'v158: remove auxiliary process messages and add income annotations to every annotated Excel layout.'

def _v177_legacy_0298_process_visual_status_enabled(chat_id: int) -> bool:
    return False
try:
    _v177_legacy_0298_process_visual_status_enabled.__name__ = 'process_visual_status_enabled'
except Exception:
    pass



def _v177_legacy_0311_v156_process_status_tick(chat_id: int) -> None:
    try:
        _v156_process_status_clear(int(chat_id), delete=True)
    except Exception:
        pass
try:
    _v177_legacy_0311_v156_process_status_tick.__name__ = '_v156_process_status_tick'
except Exception:
    pass
try:
    with _V156_PROCESS_UI_LOCK:
        _v158_existing_process_chats = list((_V156_PROCESS_UI or {}).keys())
except Exception:
    _v158_existing_process_chats = []
for _v158_cid in _v158_existing_process_chats:
    try:
        _v156_process_status_clear(int(_v158_cid), delete=True)
    except Exception:
        pass
_V158_PREV_BUILD_INFO_TEXT = _v177_legacy_0056_build_info_text
_V158_PREV_BUILD_INFO_KEYBOARD = _v177_legacy_0219_build_info_keyboard

def _v177_legacy_0057_build_info_text(chat_id: int, *args, **kwargs) -> str:
    text = ''
    if callable(_V158_PREV_BUILD_INFO_TEXT):
        try:
            text = str(_V158_PREV_BUILD_INFO_TEXT(int(chat_id), *args, **kwargs) or '')
        except TypeError:
            text = str(_V158_PREV_BUILD_INFO_TEXT(int(chat_id)) or '')
    rows = [row for row in text.splitlines() if not str(row).strip().casefold().startswith('окно процессов:')]
    cleaned = []
    for row in rows:
        if not str(row).strip() and cleaned and (not str(cleaned[-1]).strip()):
            continue
        cleaned.append(row)
    return '\n'.join(cleaned)[:3900]
try:
    _v177_legacy_0057_build_info_text.__name__ = 'build_info_text'
except Exception:
    pass

def _v158_button_cb(btn) -> str:
    if isinstance(btn, dict):
        return str(btn.get('callback_data') or '')
    return str(getattr(btn, 'callback_data', '') or '')

def _v158_button_text(btn) -> str:
    if isinstance(btn, dict):
        return str(btn.get('text') or '')
    return str(getattr(btn, 'text', '') or '')

def _v177_legacy_0220_build_info_keyboard(chat_id: int):
    kb = _V158_PREV_BUILD_INFO_KEYBOARD(int(chat_id)) if callable(_V158_PREV_BUILD_INFO_KEYBOARD) else types.InlineKeyboardMarkup()
    rows = list(getattr(kb, 'keyboard', None) or getattr(kb, 'inline_keyboard', None) or [])
    blocked = {'v156:process_visual_toggle', 'v157:process_menu', 'v157:process_owner_toggle', 'v157:process_others_toggle'}
    new_rows = []
    for row in rows:
        kept = []
        for btn in list(row or []):
            cb = _v158_button_cb(btn)
            txt = _v158_button_text(btn).strip().casefold()
            if cb in blocked or txt.startswith('👁 окно процессов') or txt.startswith('👁️ окно процессов'):
                continue
            kept.append(btn)
        if kept:
            new_rows.append(kept)
    try:
        kb.keyboard = new_rows
    except Exception:
        try:
            kb.inline_keyboard = new_rows
        except Exception:
            pass
    return kb
try:
    _v177_legacy_0220_build_info_keyboard.__name__ = 'build_info_keyboard'
except Exception:
    pass

def _canon_v157_handle_callback__001(call) -> bool:
    raw = str(getattr(call, 'data', '') or '')
    resolved = raw
    try:
        resolver = globals().get('resolve_short_callback')
        if callable(resolver):
            resolved = str(resolver(raw) or raw)
    except Exception:
        pass
    if resolved not in {'v156:process_visual_toggle', 'v157:process_menu', 'v157:process_owner_toggle', 'v157:process_others_toggle'}:
        return False
    try:
        bot.answer_callback_query(call.id, 'Окно процессов отключено: служебные сообщения больше не создаются.')
    except Exception:
        pass
    return True
_V158_PREV_MODERN_SIMPLE = _v177_legacy_0099_modern_simple_excel_styles_comments
_V158_PREV_MODERN_CATEGORY = _v177_legacy_0102_modern_category_excel_styles_comments
_V158_PREV_CATEGORY_EXPECTED = _v177_legacy_0104_category_excel_expected_annotations
_V158_PREV_CATEGORY_COMPACT_ROWS = _v177_legacy_0178_category_rows_without_description
_V158_PREV_COMPACT_ROWS = _v177_legacy_0096_compact_simple_excel_rows_and_annotations
_V158_SUMMARY_LABELS = {'остаток с прошлого раза', 'сумма по статьям', 'расход', 'приход', 'приход за период', 'расход за период', 'остаток на руках', 'на руках:', 'гомонковые', 'остаток в обороте', 'продукты', 'расход еды на человека в сутки', 'расчёт'}

def _v158_real_operation_description(value) -> str:
    note = str(value or '').strip()
    if not note or note.casefold() in _V158_SUMMARY_LABELS:
        return ''
    return note

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

def _canon_modern_simple_excel_styles_comments__001(rows: list[list]):
    if callable(_V158_PREV_MODERN_SIMPLE):
        styles, comments, header_row, widths = _V158_PREV_MODERN_SIMPLE(rows)
    else:
        max_cols = max((len(r) for r in rows or []), default=4)
        styles, comments, header_row, widths = ([[0] * max_cols for _ in rows or []], {}, 1, [13, 38, 15, 15])
    comments = _v158_add_income_annotations_from_description(rows, comments)
    return (styles, comments, header_row, widths)

def _canon_modern_category_excel_styles_comments__001(rows: list[list]):
    if callable(_V158_PREV_MODERN_CATEGORY):
        styles, comments, header_row, widths = _V158_PREV_MODERN_CATEGORY(rows)
    else:
        max_cols = max((len(r) for r in rows or []), default=4)
        styles, comments, header_row, widths = ([[0] * max_cols for _ in rows or []], {}, 1, [13, 36, 15, 18])
    comments = _v158_add_income_annotations_from_description(rows, comments)
    return (styles, comments, header_row, widths)

def _canon_category_excel_expected_annotations__001(rows: list[list]) -> dict[tuple[int, int], str]:
    expected = {}
    if callable(_V158_PREV_CATEGORY_EXPECTED):
        try:
            expected.update(_V158_PREV_CATEGORY_EXPECTED(rows) or {})
        except Exception:
            pass
    return _v158_add_income_annotations_from_description(rows, expected)

def _canon_category_rows_without_description__001(rows: list[list]) -> tuple[list[list], dict[tuple[int, int], str]]:
    if callable(_V158_PREV_CATEGORY_COMPACT_ROWS):
        out_rows, annotations = _V158_PREV_CATEGORY_COMPACT_ROWS(rows)
    else:
        out_rows, annotations = (list(rows or []), {})
    annotations = dict(annotations or {})
    in_usd = False
    for r_idx, raw in enumerate(rows or [], start=1):
        row = list(raw or [])
        first_raw = str(row[0] if row else '').strip()
        if first_raw.upper() == 'USD':
            in_usd = True
            continue
        if len(row) < 3:
            continue
        first = first_raw.casefold()
        desc = str(row[1] or '').strip()
        is_header = first in {'дата', 'date'} and desc.casefold() in {'описание', 'description'}
        if is_header:
            continue
        note = _v158_real_operation_description(desc)
        if not note or not _excel_nonempty(row[2]):
            continue
        annotations[r_idx, 3 if in_usd else 2] = note
    return (out_rows, annotations)

def _canon_compact_simple_excel_rows_and_annotations__001(raw_rows: list[tuple], opening_balance: float, target_chat_id: int | None=None):
    if callable(_V158_PREV_COMPACT_ROWS):
        rows, annotations = _V158_PREV_COMPACT_ROWS(raw_rows, opening_balance, target_chat_id)
    else:
        rows, annotations = ([], {})
    annotations = dict(annotations or {})
    in_usd = False
    header_seen = False
    for r_idx, raw in enumerate(rows or [], start=1):
        row = list(raw or [])
        first_raw = str(row[0] if row else '').strip()
        if first_raw.upper() == 'USD':
            in_usd = True
            header_seen = False
            continue
        if not in_usd:
            continue
        first = first_raw.casefold()
        desc = str(row[1] if len(row) > 1 else '').strip()
        if first in {'дата', 'date'} and desc.casefold() in {'описание', 'description'}:
            header_seen = True
            continue
        if not header_seen or len(row) < 3:
            continue
        note = _v158_real_operation_description(desc)
        if note and _excel_nonempty(row[2]):
            annotations[r_idx, 3] = note
    return (rows, annotations)
_V158_PREV_RESTORE_VALIDATE = _v177_legacy_0282_v153_validate_restore_gz
try:
    import gzip as _v158_gzip
    import json as _v158_json
    import os as _v158_os
    import shutil as _v158_shutil
    import sqlite3 as _v158_sqlite3
    import tempfile as _v158_tempfile
except Exception:
    pass

def _v177_legacy_0283_v153_validate_restore_gz(gz_path: str) -> tuple[dict, str]:
    folder = _v158_tempfile.mkdtemp(prefix='v158_restore_validate_')
    raw = _v158_os.path.join(folder, 'restore.sqlite3')
    try:
        with _v158_gzip.open(gz_path, 'rb') as fin, open(raw, 'wb') as fout:
            _v158_shutil.copyfileobj(fin, fout, 1024 * 1024)
        conn = _v158_sqlite3.connect(raw)
        try:
            integrity = str(conn.execute('PRAGMA integrity_check').fetchone()[0])
            if integrity.lower() != 'ok':
                raise RuntimeError(f'SQLite integrity_check: {integrity}')
            row = conn.execute("SELECT v FROM meta WHERE kind='v153_export' AND k='manifest'").fetchone()
            if not row:
                raise RuntimeError('manifest v153 not found')
            manifest = _v158_json.loads(row[0])
        finally:
            conn.close()
        if str(manifest.get('kind')) != 'telegram_bot_full_state_v153':
            raise RuntimeError('unknown export kind')
        if int(manifest.get('schema_version') or 0) != int(V153_EXPORT_SCHEMA):
            raise RuntimeError('unsupported export schema')
        export_version = str(manifest.get('bot_version') or '')
        if not export_version.startswith(('bot_v153_', 'bot_v154_', 'bot_v155_', 'bot_v156_', 'bot_v157_', 'bot_v158_')):
            raise RuntimeError(f"unsupported bot version: {export_version or 'missing'}")
        checksum = _v153_db_logical_checksum(raw)
        if checksum != str(manifest.get('checksum') or ''):
            raise RuntimeError('checksum mismatch')
        return (manifest, raw)
    except Exception:
        _v158_shutil.rmtree(folder, ignore_errors=True)
        raise
try:
    _v177_legacy_0283_v153_validate_restore_gz.__name__ = '_v153_validate_restore_gz'
except Exception:
    pass
try:
    _v177_legacy_0007_bot_journal('v158_no_process_messages_income_notes_installed', int(OWNER_ID or 0), 'process_chat_messages=0; process_internal_journal=1; income_excel_annotations=1; info_process_menu=removed')
except Exception:
    pass
'v159: correct timer markers, make helper-window lifetime configurable, restore visible file progress.'
import gzip as _v159_gzip
import json as _v159_json
import os as _v159_os
import re as _v159_re
import shutil as _v159_shutil
import sqlite3 as _v159_sqlite3
import tempfile as _v159_tempfile
import time as _v159_time
try:
    if 'main_window_refresh' in INTERNAL_TIMER_DEFS:
        INTERNAL_TIMER_DEFS['main_window_refresh']['label'] = '⏰ Обновление главного окна Ф91'
    if 'process_status_refresh' in INTERNAL_TIMER_DEFS:
        INTERNAL_TIMER_DEFS['process_status_refresh']['label'] = '⚙️ Обновление времени / этапа процессов'
    INTERNAL_TIMER_DEFS.setdefault('helper_process_close', {'label': '⏳ Закрытие окна операции после завершения', 'default': 4, 'min': 1, 'max': 3600})
    INTERNAL_TIMER_DEFS.setdefault('file_status_close', {'label': '📥📤 Закрытие окна скачивания / загрузки', 'default': 15, 'min': 1, 'max': 3600})
    INTERNAL_TIMER_DEFS.setdefault('helper_message_close', {'label': '💬 Закрытие малых служебных сообщений', 'default': 25, 'min': 1, 'max': 3600})
except Exception:
    pass
try:
    if isinstance(WINDOW_MARKER_CLOCK_CODES, set):
        WINDOW_MARKER_CLOCK_CODES.discard('Ф40')
        WINDOW_MARKER_CLOCK_CODES.add('Ф91')
        WINDOW_MARKER_CLOCK_CODES.update({'Ф232', 'Ф233'})
except Exception:
    pass
try:
    WINDOW_MARKER_CONSTANTS['itmr_back_info'] = 'Ф54'
except Exception:
    pass

def _v159_force_marker(text: str, code: str, glyph: str | None=None) -> str:
    body = strip_window_mark(str(text or ''))
    body = _v159_re.sub('(?mi)^\\s*(?:[СФП]\\d{1,6}|[ов]\\d{1,3})(?:\\s*[⏳⏰])?\\s*$', '', body)
    body = _v159_re.sub('\\n{3,}', '\n\n', body).strip()
    if glyph:
        return f'{body}\n\n{code} {glyph}'
    return window_mark(body, code)
_V159_PREV_BUILD_TIMERS_TEXT = _v177_legacy_0023_build_internal_timers_text
_V159_PREV_BUILD_TIMER_INPUT_TEXT = _v177_legacy_0024_build_internal_timer_input_text

def _canon_build_internal_timers_text__001() -> str:
    lines = ['⏱ Внутренние таймеры', '', 'Настройки общие для обычных служебных окон и процессов.', 'Окно процесса остаётся открытым пока операция реально выполняется; выбранное время определяет, сколько оно ещё видно после завершения.', 'Окна скачивания/загрузки показывают прошедшее время, этап и прогресс до окончания файла.', 'Главное окно — Ф91.', '']
    for key, cfg in INTERNAL_TIMER_DEFS.items():
        lines.append(f"{cfg['label']}: {_format_duration_short(internal_timer_seconds(key))}")
    lines.extend(['', 'Выберите таймер для изменения.'])
    return _v159_force_marker('\n'.join(lines), 'Ф183')

def _canon_build_internal_timer_input_text__001(chat_id: int) -> str:
    if callable(_V159_PREV_BUILD_TIMER_INPUT_TEXT):
        try:
            text = _V159_PREV_BUILD_TIMER_INPUT_TEXT(int(chat_id))
        except Exception:
            text = '⏱ Настройка таймера'
    else:
        text = '⏱ Настройка таймера'
    return _v159_force_marker(text, 'Ф184')
_V159_PREV_FAST_UI_EDIT = _v177_legacy_0211_fast_ui_edit_message_text
_V159_TIMER_PURPOSE_MARKERS = {'internal_timers': 'Ф183', 'internal_timer_pick': 'Ф184', 'internal_timer_digit': 'Ф185', 'internal_timer_unit': 'Ф186', 'internal_timer_backspace': 'Ф187', 'internal_timer_clear': 'Ф188', 'internal_timer_apply': 'Ф189', 'internal_timer_back_info': 'Ф54'}
if callable(_V159_PREV_FAST_UI_EDIT):

    def fast_ui_edit_message_text(chat_id: int, message_id: int, text: str, reply_markup=None, parse_mode=None, purpose: str='fast_ui') -> str:
        code = _V159_TIMER_PURPOSE_MARKERS.get(str(purpose or ''))
        if code:
            text = _v159_force_marker(text, code)
        return _V159_PREV_FAST_UI_EDIT(int(chat_id), int(message_id), text, reply_markup=reply_markup, parse_mode=parse_mode, purpose=purpose)

def _v177_legacy_0299_process_visual_status_enabled(chat_id: int) -> bool:
    return True
try:
    _v177_legacy_0299_process_visual_status_enabled.__name__ = 'process_visual_status_enabled'
except Exception:
    pass

def _v177_legacy_0303_v156_process_status_schedule(chat_id: int, delay: float) -> None:
    try:
        key = f'{_V156_PROCESS_STATUS_KEY_PREFIX}{int(chat_id)}'
        DELAYED_SCHEDULER.cancel(key)
        DELAYED_SCHEDULER.schedule(key, max(0.05, float(delay)), _v156_process_status_tick, int(chat_id))
    except Exception:
        pass
try:
    _v177_legacy_0303_v156_process_status_schedule.__name__ = '_v156_process_status_schedule'
except Exception:
    pass

def _v177_legacy_0307_v156_process_status_arm(chat_id: int | None, hint: str='') -> None:
    try:
        chat_id = int(chat_id or 0)
    except Exception:
        return
    if not chat_id:
        return
    with _V156_PROCESS_UI_LOCK:
        state = _V156_PROCESS_UI.setdefault(chat_id, {'message_id': 0, 'hint': '', 'armed_at': _v159_time.monotonic()})
        if hint:
            state['hint'] = str(hint)[:120]
        state['armed_at'] = min(float(state.get('armed_at') or _v159_time.monotonic()), _v159_time.monotonic())
    _v156_process_status_schedule(chat_id, 0.8)
try:
    _v177_legacy_0307_v156_process_status_arm.__name__ = '_v156_process_status_arm'
except Exception:
    pass

def _v159_process_status_text(chat_id: int, rows: list[dict], hint: str='') -> str:
    now_m = _v159_time.monotonic()
    lines = ['⏳ Операция выполняется']
    if hint:
        lines.append(f'Действие: {str(hint)[:100]}')
    lines.append('')
    for row in rows[:6]:
        started = float((row or {}).get('started_mono') or now_m)
        elapsed = max(0, int(now_m - started))
        label = str((row or {}).get('label') or (row or {}).get('id') or 'Операция')
        phase = str((row or {}).get('phase') or 'выполняется')
        lines.append(f'• {label}: {phase} · {elapsed}с')
    if len(rows) > 6:
        lines.append(f'…ещё {len(rows) - 6}')
    close_s = internal_timer_seconds('helper_process_close', 4)
    lines.extend(['', f'После завершения окно закроется через {_format_duration_short(close_s)}.'])
    return _v159_force_marker('\n'.join(lines)[:3800], 'Ф232', '⏰')

def _v177_legacy_0312_v156_process_status_tick(chat_id: int) -> None:
    chat_id = int(chat_id)
    rows = _v156_active_process_rows(chat_id)
    with _V156_PROCESS_UI_LOCK:
        state = _V156_PROCESS_UI.get(chat_id) or {}
        msg_id = int(state.get('message_id') or 0)
        hint = str(state.get('hint') or '')
    if not rows:
        if msg_id:
            try:
                close_s = internal_timer_seconds('helper_process_close', 4)
                final = _v159_force_marker(f"✅ {hint or 'Операция'}\nВыполнено.\nОкно закроется через {_format_duration_short(close_s)}.", 'Ф232', '⏳')
                bot.edit_message_text(final, chat_id=chat_id, message_id=msg_id)
                delete_message_later(chat_id, msg_id, close_s)
            except Exception:
                pass
        _v156_process_status_clear(chat_id, delete=False)
        return
    text = _v159_process_status_text(chat_id, rows, hint)
    if msg_id:
        try:
            bot.edit_message_text(text, chat_id=chat_id, message_id=msg_id)
        except Exception as exc:
            low = str(exc).casefold()
            if 'message is not modified' not in low:
                try:
                    bot_journal('process_visual_status_edit_error', chat_id, str(exc)[:300], 'WARN')
                except Exception:
                    pass
            if 'message_id_invalid' in low or 'message to edit not found' in low or "message can't be edited" in low:
                try:
                    sent = bot.send_message(chat_id, text)
                    new_id = int(getattr(sent, 'message_id', 0) or 0)
                    if new_id:
                        with _V156_PROCESS_UI_LOCK:
                            if chat_id in _V156_PROCESS_UI:
                                _V156_PROCESS_UI[chat_id]['message_id'] = new_id
                except Exception:
                    pass
    else:
        try:
            sent = bot.send_message(chat_id, text)
            new_id = int(getattr(sent, 'message_id', 0) or 0)
            if new_id:
                with _V156_PROCESS_UI_LOCK:
                    if chat_id in _V156_PROCESS_UI:
                        _V156_PROCESS_UI[chat_id]['message_id'] = new_id
        except Exception:
            pass
    _v156_process_status_schedule(chat_id, internal_timer_seconds('process_status_refresh', 10.0))
try:
    _v177_legacy_0312_v156_process_status_tick.__name__ = '_v156_process_status_tick'
except Exception:
    pass

def _v159_file_phase_prefix(phase: str) -> str:
    low = str(phase or '').casefold()
    if any((x in low for x in ('скачив', 'читаю', 'получаю'))):
        return '📥 Скачивание'
    if any((x in low for x in ('загруж', 'отправля', 'выгруж', 'mega', 'drive'))):
        return '📤 Загрузка'
    if any((x in low for x in ('zip', 'excel', 'собир', 'формир', 'экспорт'))):
        return '⚙️ Подготовка'
    return '⏳ Выполнение'

def _v159_file_status_text(label: str, elapsed: str, phase: str, cur=None, tot=None) -> str:
    progress = f'\nПрогресс: {cur}/{tot}' if cur is not None and tot is not None else ''
    close_s = internal_timer_seconds('file_status_close', 15)
    text = f'{_v159_file_phase_prefix(phase)} · {label}\nВремя: {elapsed}\nЭтап: {phase}{progress}\nПосле завершения закроется через {_format_duration_short(close_s)}.'
    return _v159_force_marker(text, 'Ф233', '⏰')

def _canon_file_job_progress__001(phase: str, current=None, total=None, force: bool=False):
    ctx = _file_job_current()
    if not ctx:
        return
    key = str(ctx.get('key') or _INTERACTIVE_FILE_JOB_KEY)
    now_m = _v159_time.monotonic()
    with _FILE_JOB_LOCK:
        st = _FILE_JOB_STATE.get(key)
        if not isinstance(st, dict):
            return
        st['phase'] = str(phase or 'работаю')
        if current is not None:
            st['current'] = current
        if total is not None:
            st['total'] = total
        last = float(st.get('last_ui_monotonic') or 0.0)
        refresh = internal_timer_seconds('process_status_refresh', 10.0)
        if not force and now_m - last < refresh:
            return
        st['last_ui_monotonic'] = now_m
        chat_id = int(st.get('chat_id'))
        msg_id = st.get('status_msg_id')
        label = str(st.get('label') or 'Файл')
        started = float(st.get('started_monotonic') or st.get('queued_monotonic') or now_m)
        elapsed = _file_job_elapsed_text(now_m - started)
        cur = st.get('current')
        tot = st.get('total')
    if not msg_id:
        return
    try:
        with _FILE_JOB_LOCK:
            st2 = _FILE_JOB_STATE.get(key)
            rendered = _v199_render_active_file_state(st2) if isinstance(st2, dict) else _v159_file_status_text(label, elapsed, str(phase or 'работаю'), cur, tot)
        bot.edit_message_text(rendered, chat_id=chat_id, message_id=int(msg_id))
    except Exception:
        pass

def _v177_legacy_0011_file_job_tick(key: str):
    key = str(key)
    with _FILE_JOB_LOCK:
        st = _FILE_JOB_STATE.get(key)
        if not isinstance(st, dict):
            return
        chat_id = int(st.get('chat_id'))
        msg_id = st.get('status_msg_id')
        label = str(st.get('label') or 'Файл')
        phase = str(st.get('phase') or 'работаю')
        started = float(st.get('started_monotonic') or st.get('queued_monotonic') or _v159_time.monotonic())
        elapsed = _file_job_elapsed_text(_v159_time.monotonic() - started)
        cur = st.get('current')
        tot = st.get('total')
    try:
        if msg_id:
            with _FILE_JOB_LOCK:
                st2 = _FILE_JOB_STATE.get(key)
                rendered = _v199_render_active_file_state(st2) if isinstance(st2, dict) else _v159_file_status_text(label, elapsed, phase, cur, tot)
            bot.edit_message_text(rendered, chat_id=chat_id, message_id=int(msg_id))
    except Exception:
        pass
    with _FILE_JOB_LOCK:
        alive = isinstance(_FILE_JOB_STATE.get(key), dict)
    if alive:
        DELAYED_SCHEDULER.schedule(f'file-job-tick:{key}', internal_timer_seconds('process_status_refresh', 10.0), _file_job_tick, key)
try:
    _v177_legacy_0011_file_job_tick.__name__ = '_file_job_tick'
except Exception:
    pass

def _v177_legacy_0014_interactive_file_job_runner(job_meta: dict, func, args, kwargs):
    key = str(job_meta.get('key') or _INTERACTIVE_FILE_JOB_KEY)
    previous = getattr(_FILE_JOB_CONTEXT, 'value', None)
    _FILE_JOB_CONTEXT.value = {'key': key}
    ok = False
    error_text = ''
    try:
        with _FILE_JOB_LOCK:
            st = _FILE_JOB_STATE.get(key)
            if isinstance(st, dict):
                st['started_monotonic'] = _v159_time.monotonic()
                st['phase'] = 'запуск'
        _file_job_progress('запуск', force=True)
        mem_ctx = globals().get('memory_operation')
        if callable(mem_ctx):
            with mem_ctx(f"file:{job_meta.get('kind') or 'export'}", {'chat_id': job_meta.get('chat_id'), 'label': job_meta.get('label')}, heavy=True):
                result = func(*args, **kwargs)
        else:
            result = func(*args, **kwargs)
        ok = result is not False
        if not ok:
            error_text = 'операция завершилась без подтверждения'
    except Exception as exc:
        error_text = str(exc)[:300]
        try:
            log_error(f"INTERACTIVE FILE JOB {job_meta.get('kind')}: {exc}")
        except Exception:
            pass
    finally:
        now_m = _v159_time.monotonic()
        with _FILE_JOB_LOCK:
            st = _FILE_JOB_STATE.get(key)
            if isinstance(st, dict):
                chat_id = int(st.get('chat_id'))
                msg_id = st.get('status_msg_id')
                label = str(st.get('label') or 'Файл')
                started = float(st.get('started_monotonic') or st.get('queued_monotonic') or now_m)
                elapsed = _file_job_elapsed_text(now_m - started)
            else:
                chat_id = int(job_meta.get('chat_id') or 0)
                msg_id = None
                label = str(job_meta.get('label') or 'Файл')
                elapsed = '0:00'
        try:
            if msg_id:
                close_s = internal_timer_seconds('file_status_close', 15)
                if ok:
                    final = f'✅ {label}\nГотово за {elapsed}.\nОкно закроется через {_format_duration_short(close_s)}.'
                else:
                    final = f"⚠️ {label}\nЗавершено за {elapsed}.\n{error_text or 'Telegram не подтвердил отправку.'}\nОкно закроется через {_format_duration_short(close_s)}."
                final = _v159_force_marker(final, 'Ф233', '⏳')
                bot.edit_message_text(final, chat_id=chat_id, message_id=int(msg_id))
                delete_message_later(chat_id, int(msg_id), close_s)
        except Exception:
            pass
        try:
            bot_journal('file_job_done' if ok else 'file_job_uncertain', chat_id, f"kind={job_meta.get('kind')} elapsed={elapsed} error={error_text}")
        except Exception:
            pass
        try:
            DELAYED_SCHEDULER.cancel(f'file-job-tick:{key}')
        except Exception:
            pass
        with _FILE_JOB_LOCK:
            _FILE_JOB_STATE.pop(key, None)
        try:
            release_fn = globals().get('kv_distributed_lock_release_v248')
            kv_token = job_meta.get('kv_lock_token_v248') if isinstance(job_meta, dict) else None
            if kv_token and callable(release_fn):
                release_fn('interactive_file_job', kv_token)
        except Exception:
            pass
        if previous is None:
            try:
                delattr(_FILE_JOB_CONTEXT, 'value')
            except Exception:
                pass
        else:
            _FILE_JOB_CONTEXT.value = previous
try:
    _v177_legacy_0014_interactive_file_job_runner.__name__ = '_interactive_file_job_runner'
except Exception:
    pass

def _v177_legacy_0019_submit_interactive_file_job(chat_id: int, kind: str, label: str, func, *args, **kwargs) -> tuple[bool, str]:
    chat_id = int(chat_id)
    gate = globals().get('memory_heavy_allowed')
    if callable(gate):
        try:
            allowed, reason = gate(str(kind or 'export'))
        except Exception:
            allowed, reason = (True, '')
        if not allowed:
            try:
                send_and_auto_delete(chat_id, f'🧠 {reason}', internal_timer_seconds('helper_message_close', 25))
            except Exception:
                pass
            return (False, reason or 'сервер временно разгружает память')
    key = _INTERACTIVE_FILE_JOB_KEY
    with _FILE_JOB_LOCK:
        existing = _FILE_JOB_STATE.get(key)
        if isinstance(existing, dict):
            return (False, build_all_processes_toast(chat_id))
        meta = {'key': key, 'chat_id': chat_id, 'kind': str(kind), 'label': str(label), 'queued_monotonic': _v159_time.monotonic(), 'started_monotonic': 0.0, 'phase': 'в очереди', 'status_msg_id': None, 'last_ui_monotonic': 0.0}
        _FILE_JOB_STATE[key] = meta
    try:
        text = _v159_file_status_text(str(label), '0:00', 'в очереди')
        status = bot.send_message(chat_id, text)
        with _FILE_JOB_LOCK:
            if isinstance(_FILE_JOB_STATE.get(key), dict):
                _FILE_JOB_STATE[key]['status_msg_id'] = int(getattr(status, 'message_id', 0) or 0) or None
    except Exception:
        pass
    ok = EXPORT_TASK_POOL.submit_unique(key, _interactive_file_job_runner, dict(meta), func, args, kwargs)
    if not ok:
        with _FILE_JOB_LOCK:
            _FILE_JOB_STATE.pop(key, None)
        release_fn = globals().get('kv_distributed_lock_release_v248')
        if kv_lock_token and callable(release_fn):
            try:
                release_fn('interactive_file_job', kv_lock_token)
            except Exception:
                pass
        return (False, build_all_processes_toast(chat_id))
    try:
        DELAYED_SCHEDULER.cancel(f'file-job-tick:{key}')
        DELAYED_SCHEDULER.schedule(f'file-job-tick:{key}', internal_timer_seconds('process_status_refresh', 10.0), _file_job_tick, key)
    except Exception:
        pass
    try:
        bot_journal('file_job_queued', chat_id, f'kind={kind} label={label}; visual=1; marker=Ф233')
    except Exception:
        pass
    return (True, 'Запущено')
try:
    _v177_legacy_0019_submit_interactive_file_job.__name__ = 'submit_interactive_file_job'
except Exception:
    pass
_V159_OLD_HELPER_DELAY = float(globals().get('HELPER_DELETE_DELAY') or 25)

def _v159_helper_delay(delay) -> float:
    try:
        value = float(delay)
    except Exception:
        value = _V159_OLD_HELPER_DELAY
    if abs(value - _V159_OLD_HELPER_DELAY) < 0.001:
        return internal_timer_seconds('helper_message_close', _V159_OLD_HELPER_DELAY)
    return max(0.1, value)

def _v159_helper_mark(text: str) -> str:
    return _v159_force_marker(str(text or ''), 'Ф233', '⏳')
_V224_INLINE_HELPER_LOCK = _v155_threading.RLock()
_V224_INLINE_HELPER_STATE = {}
_V224_INLINE_HELPER_RE = _v159_re.compile('(?m)^\\s*ℹ️\\s*Ф233\\s*·[^\\n]*(?:\\n(?: {2,}|\\t)[^\\n]*)*\\n?', flags=_v159_re.IGNORECASE)

def _v224_inline_helper_candidate(chat_id: int):
    """Return the exact callback source window when possible, otherwise newest live normal window."""
    cid = int(chat_id)
    live = globals().get('_V221_LIVE_MARKUP')
    lock = globals().get('_V221_LIVE_MARKUP_LOCK')
    if not isinstance(live, dict):
        return None
    try:
        ctx = _current_telegram_update_context() if '_current_telegram_update_context' in globals() else {}
    except Exception:
        ctx = {}
    cb = str((ctx or {}).get('callback_data') or '')
    source_mid = int((ctx or {}).get('message_id') or 0)

    def _copy_rows():
        if lock is not None:
            with lock:
                return [((int(k[0]), int(k[1])), dict(v or {})) for k, v in live.items()]
        return [((int(k[0]), int(k[1])), dict(v or {})) for k, v in live.items()]
    try:
        rows = _copy_rows()
    except Exception:
        return None
    candidates = []
    for (rcid, mid), row in rows:
        if rcid != cid:
            continue
        base = str(row.get('text') or '')
        if not base:
            continue
        try:
            marker = str(_v160_marker_from_text(base) or '')
        except Exception:
            marker = ''
        if marker in {'Ф232', 'Ф233'}:
            continue
        candidates.append((mid, row))
    if cb:
        for mid, row in candidates:
            if mid == source_mid:
                return (mid, row)
        return None
    if not candidates:
        return None
    candidates.sort(key=lambda item: float((item[1] or {}).get('at') or 0.0), reverse=True)
    return candidates[0]

def _v224_inline_helper_text(base_text: str, helper_text: str) -> str:
    base = _V224_INLINE_HELPER_RE.sub('', str(base_text or '')).strip()
    helper = _v159_re.sub('\\s+', ' ', strip_window_mark(str(helper_text or ''))).strip()
    if len(helper) > 650:
        helper = helper[:647] + '…'
    lines = base.splitlines()
    insert_at = 1 if lines else 0
    lines.insert(insert_at, f'ℹ️ Ф233 · {helper}')
    return '\n'.join(lines)

def _v224_try_inline_helper(chat_id: int, text: str, delay: int) -> bool:
    raw = str(text or '')
    if not raw or len(raw) > 900:
        return False
    candidate = _v224_inline_helper_candidate(int(chat_id))
    try:
        ctx = _current_telegram_update_context() if '_current_telegram_update_context' in globals() else {}
    except Exception:
        ctx = {}
    cb = str((ctx or {}).get('callback_data') or '')
    if cb in {'aux_close', 'info_close'} and candidate is None:
        try:
            bot_journal('stale_close_noop_v224', int(chat_id), f'action={cb}; helper_suppressed=1')
        except Exception:
            pass
        return True
    if candidate is None:
        return False
    mid, row = candidate
    base = _V224_INLINE_HELPER_RE.sub('', str(row.get('text') or '')).strip()
    markup = row.get('markup')
    inline = _v224_inline_helper_text(base, raw)
    if len(inline) > 3900:
        return False
    result = fast_ui_edit_message_text(int(chat_id), int(mid), inline, reply_markup=markup, purpose='inline_service_v224')
    if str(result or '') not in {'ok', 'not_modified'}:
        return False
    with _V224_INLINE_HELPER_LOCK:
        gen = int((_V224_INLINE_HELPER_STATE.get((int(chat_id), int(mid))) or {}).get('gen') or 0) + 1
        _V224_INLINE_HELPER_STATE[int(chat_id), int(mid)] = {'gen': gen, 'inline': inline, 'base': base, 'markup': markup}

    def _clear(cid=int(chat_id), message_id=int(mid), expected=gen):
        with _V224_INLINE_HELPER_LOCK:
            st = dict(_V224_INLINE_HELPER_STATE.get((cid, message_id)) or {})
        if int(st.get('gen') or 0) != int(expected):
            return
        live = globals().get('_V221_LIVE_MARKUP') or {}
        try:
            current = dict(live.get((cid, message_id)) or {})
        except Exception:
            current = {}
        if str(current.get('text') or '') != str(st.get('inline') or ''):
            return
        current_markup = current.get('markup') if current.get('markup') is not None else st.get('markup')
        res = fast_ui_edit_message_text(cid, message_id, str(st.get('base') or ''), reply_markup=current_markup, purpose='inline_service_clear_v224')
        if str(res or '') in {'ok', 'not_modified', 'not_found'}:
            with _V224_INLINE_HELPER_LOCK:
                if int((_V224_INLINE_HELPER_STATE.get((cid, message_id)) or {}).get('gen') or 0) == expected:
                    _V224_INLINE_HELPER_STATE.pop((cid, message_id), None)
    try:
        DELAYED_SCHEDULER.cancel(f'inline-helper-v224:{int(chat_id)}:{int(mid)}')
        DELAYED_SCHEDULER.schedule(f'inline-helper-v224:{int(chat_id)}:{int(mid)}', float(delay), _clear)
    except Exception:
        pass
    try:
        bot_journal('inline_service_status_v224', int(chat_id), f"msg={int(mid)}; delay={int(delay)}; source={cb or 'message'}")
    except Exception:
        pass
    return True

def _v177_legacy_0232_send_and_auto_delete(chat_id: int, text: str, delay: int=25):
    if is_finance_output_suppressed(chat_id):
        return
    delay = _v159_helper_delay(delay)
    try:
        if _v224_try_inline_helper(int(chat_id), str(text or ''), int(delay)):
            return
    except Exception:
        pass
    marked = _v159_helper_mark(text)
    if chat_buttons_current_window_enabled(chat_id):
        send_or_edit_stored_window(chat_id, 'command_window_id', marked, delay=delay)
        return
    try:
        msg = bot.send_message(chat_id, marked)
        DELAYED_SCHEDULER.schedule(f'auto-delete:{chat_id}:{msg.message_id}', delay, lambda: _v159_delete_quiet(chat_id, msg.message_id))
    except Exception as e:
        log_error(f'send_and_auto_delete: {e}')
try:
    _v177_legacy_0232_send_and_auto_delete.__name__ = 'send_and_auto_delete'
except Exception:
    pass

def _v177_legacy_0234_send_html_and_auto_delete(chat_id: int, html_text: str, delay: int=25):
    if is_finance_output_suppressed(chat_id):
        return
    delay = _v159_helper_delay(delay)
    marked = _v159_helper_mark(html_text)
    if chat_buttons_current_window_enabled(chat_id):
        send_or_edit_stored_window(chat_id, 'command_window_id', marked, parse_mode='HTML', delay=delay)
        return
    try:
        msg = bot.send_message(chat_id, marked, parse_mode='HTML')
        DELAYED_SCHEDULER.schedule(f'auto-delete-html:{chat_id}:{msg.message_id}', delay, lambda: _v159_delete_quiet(chat_id, msg.message_id))
    except Exception as e:
        log_error(f'send_html_and_auto_delete: {e}')
try:
    _v177_legacy_0234_send_html_and_auto_delete.__name__ = 'send_html_and_auto_delete'
except Exception:
    pass

def _v159_delete_quiet(chat_id: int, message_id: int) -> None:
    try:
        bot.delete_message(int(chat_id), int(message_id))
    except Exception:
        pass
try:
    WINDOW_MARKER_CONSTANTS.update({'v159:process_status': 'Ф232', 'v159:file_status': 'Ф233', 'v159:helper_message': 'Ф233'})
except Exception:
    pass

def _v177_legacy_0284_v153_validate_restore_gz(gz_path: str) -> tuple[dict, str]:
    folder = _v159_tempfile.mkdtemp(prefix='v159_restore_validate_')
    raw = _v159_os.path.join(folder, 'restore.sqlite3')
    try:
        with _v159_gzip.open(gz_path, 'rb') as fin, open(raw, 'wb') as fout:
            _v159_shutil.copyfileobj(fin, fout, 1024 * 1024)
        conn = _v159_sqlite3.connect(raw)
        try:
            integrity = str(conn.execute('PRAGMA integrity_check').fetchone()[0])
            if integrity.lower() != 'ok':
                raise RuntimeError(f'SQLite integrity_check: {integrity}')
            row = conn.execute("SELECT v FROM meta WHERE kind='v153_export' AND k='manifest'").fetchone()
            if not row:
                raise RuntimeError('manifest v153 not found')
            manifest = _v159_json.loads(row[0])
        finally:
            conn.close()
        if str(manifest.get('kind')) != 'telegram_bot_full_state_v153':
            raise RuntimeError('unknown export kind')
        if int(manifest.get('schema_version') or 0) != int(V153_EXPORT_SCHEMA):
            raise RuntimeError('unsupported export schema')
        export_version = str(manifest.get('bot_version') or '')
        if not export_version.startswith(('bot_v153_', 'bot_v154_', 'bot_v155_', 'bot_v156_', 'bot_v157_', 'bot_v158_', 'bot_v159_')):
            raise RuntimeError(f"unsupported bot version: {export_version or 'missing'}")
        checksum = _v153_db_logical_checksum(raw)
        if checksum != str(manifest.get('checksum') or ''):
            raise RuntimeError('checksum mismatch')
        return (manifest, raw)
    except Exception:
        _v159_shutil.rmtree(folder, ignore_errors=True)
        raise
try:
    _v177_legacy_0284_v153_validate_restore_gz.__name__ = '_v153_validate_restore_gz'
except Exception:
    pass
try:
    _v177_legacy_0007_bot_journal('v159_internal_timers_helper_windows_installed', int(OWNER_ID or 0), 'timer_markers=corrected; process_helper=restored; file_progress=restored; helper_close_timers=3; service_marker=Ф233 unified')
except Exception:
    pass
'v160: UI stabilization, parallel-window support, reliable helper timers and exact window/TZ annotations.'
import copy as _v160_copy
import gzip as _v160_gzip
import json as _v160_json
import os as _v160_os
import re as _v160_re
import shutil as _v160_shutil
import sqlite3 as _v160_sqlite3
import tempfile as _v160_tempfile
import threading as _v160_threading
import time as _v160_time
from datetime import timedelta as _v160_timedelta
try:
    INTERNAL_TIMER_DEFS.pop('helper_process_close', None)
    if 'process_status_refresh' in INTERNAL_TIMER_DEFS:
        INTERNAL_TIMER_DEFS['process_status_refresh']['label'] = '📥📤 Обновление времени / этапа файлов Ф233'
    if 'file_status_close' in INTERNAL_TIMER_DEFS:
        INTERNAL_TIMER_DEFS['file_status_close']['label'] = '📥📤 Закрытие окна файла Ф233 после завершения'
    if 'helper_message_close' in INTERNAL_TIMER_DEFS:
        INTERNAL_TIMER_DEFS['helper_message_close']['label'] = '💬 Закрытие единого служебного окна Ф233'
except Exception:
    pass
try:
    if isinstance(WINDOW_MARKER_CLOCK_CODES, set):
        WINDOW_MARKER_CLOCK_CODES.discard('Ф232')
        WINDOW_MARKER_CLOCK_CODES.add('Ф233')
except Exception:
    pass

def _v177_legacy_0300_process_visual_status_enabled(chat_id: int) -> bool:
    return False
try:
    _v177_legacy_0300_process_visual_status_enabled.__name__ = 'process_visual_status_enabled'
except Exception:
    pass

def _v177_legacy_0304_v156_process_status_schedule(chat_id: int, delay: float) -> None:
    try:
        DELAYED_SCHEDULER.cancel(f'{_V156_PROCESS_STATUS_KEY_PREFIX}{int(chat_id)}')
    except Exception:
        pass
try:
    _v177_legacy_0304_v156_process_status_schedule.__name__ = '_v156_process_status_schedule'
except Exception:
    pass


def _v177_legacy_0313_v156_process_status_tick(chat_id: int) -> None:
    try:
        chat_id = int(chat_id)
    except Exception:
        return
    msg_id = 0
    try:
        with _V156_PROCESS_UI_LOCK:
            row = _V156_PROCESS_UI.pop(chat_id, None) or {}
            msg_id = int(row.get('message_id') or 0)
    except Exception:
        pass
    if msg_id:
        try:
            bot.delete_message(chat_id, msg_id)
        except Exception:
            pass
try:
    _v177_legacy_0313_v156_process_status_tick.__name__ = '_v156_process_status_tick'
except Exception:
    pass
_V160_TIMER_LOCK = _v160_threading.RLock()
_V160_TIMERS = {}

def _v160_cancel_timer(key: str) -> None:
    key = str(key)
    timer = None
    with _V160_TIMER_LOCK:
        timer = _V160_TIMERS.pop(key, None)
    if timer is not None:
        try:
            timer.cancel()
        except Exception:
            pass

def _v160_schedule(key: str, delay: float, func, *args, **kwargs):
    key = str(key)
    _v160_cancel_timer(key)
    try:
        wait = max(0.05, float(delay))
    except Exception:
        wait = 0.05

    def _run():
        try:
            func(*args, **kwargs)
        finally:
            with _V160_TIMER_LOCK:
                current = _V160_TIMERS.get(key)
                if current is timer:
                    _V160_TIMERS.pop(key, None)
    timer = _v160_threading.Timer(wait, _run)
    timer.daemon = True
    with _V160_TIMER_LOCK:
        _V160_TIMERS[key] = timer
    timer.start()
    return timer

def _v177_legacy_0315_v160_delete_quiet(chat_id: int, message_id: int) -> None:
    chat_id = int(chat_id)
    message_id = int(message_id)
    try:
        bot.delete_message(chat_id, message_id)
    except Exception:
        pass
    try:
        unregister_open_window(chat_id, message_id)
    except Exception:
        pass
    try:
        store = get_chat_store(chat_id)
        changed = False
        for key in ('_v160_file_status_msg_id', 'command_window_id'):
            try:
                if int(store.get(key) or 0) == message_id:
                    store[key] = None
                    changed = True
            except Exception:
                pass
        if changed:
            save_data(data, chat_ids=[chat_id])
            try:
                schedule_quick_backup(chat_id, 0.5)
            except Exception:
                pass
    except Exception:
        pass
try:
    _v177_legacy_0315_v160_delete_quiet.__name__ = '_v160_delete_quiet'
except Exception:
    pass

def _v177_legacy_0316_v160_schedule_delete(chat_id: int, message_id: int, delay: float, prefix: str='delete') -> None:
    _v160_schedule(f'v160:{prefix}:{int(chat_id)}:{int(message_id)}', delay, _v160_delete_quiet, int(chat_id), int(message_id))
try:
    _v177_legacy_0316_v160_schedule_delete.__name__ = '_v160_schedule_delete'
except Exception:
    pass

def _canon_file_job_tick__001(key: str):
    key = str(key)
    with _FILE_JOB_LOCK:
        st = _FILE_JOB_STATE.get(key)
        if not isinstance(st, dict):
            return
        chat_id = int(st.get('chat_id'))
        msg_id = st.get('status_msg_id')
        label = str(st.get('label') or 'Файл')
        phase = str(st.get('phase') or 'работаю')
        started = float(st.get('started_monotonic') or st.get('queued_monotonic') or _v160_time.monotonic())
        elapsed = _file_job_elapsed_text(_v160_time.monotonic() - started)
        cur = st.get('current')
        tot = st.get('total')
    try:
        if msg_id:
            bot.edit_message_text(_v159_file_status_text(label, elapsed, phase, cur, tot), chat_id=chat_id, message_id=int(msg_id))
    except Exception:
        pass
    with _FILE_JOB_LOCK:
        alive = isinstance(_FILE_JOB_STATE.get(key), dict)
    if alive:
        _v160_schedule(f'v160:file-tick:{key}', internal_timer_seconds('process_status_refresh', 10.0), _file_job_tick, key)

def _v177_legacy_0015_interactive_file_job_runner(job_meta: dict, func, args, kwargs):
    key = str(job_meta.get('key') or _INTERACTIVE_FILE_JOB_KEY)
    previous = getattr(_FILE_JOB_CONTEXT, 'value', None)
    _FILE_JOB_CONTEXT.value = {'key': key}
    ok = False
    error_text = ''
    try:
        with _FILE_JOB_LOCK:
            st = _FILE_JOB_STATE.get(key)
            if isinstance(st, dict):
                st['started_monotonic'] = _v160_time.monotonic()
                st['phase'] = 'запуск'
        _file_job_progress('запуск', force=True)
        mem_ctx = globals().get('memory_operation')
        if callable(mem_ctx):
            with mem_ctx(f"file:{job_meta.get('kind') or 'export'}", {'chat_id': job_meta.get('chat_id'), 'label': job_meta.get('label')}, heavy=True):
                result = func(*args, **kwargs)
        else:
            result = func(*args, **kwargs)
        ok = result is not False
        if not ok:
            error_text = 'операция завершилась без подтверждения'
    except Exception as exc:
        error_text = str(exc)[:300]
        try:
            log_error(f"INTERACTIVE FILE JOB {job_meta.get('kind')}: {exc}")
        except Exception:
            pass
    finally:
        now_m = _v160_time.monotonic()
        with _FILE_JOB_LOCK:
            st = _FILE_JOB_STATE.get(key)
            if isinstance(st, dict):
                chat_id = int(st.get('chat_id'))
                msg_id = st.get('status_msg_id')
                label = str(st.get('label') or 'Файл')
                started = float(st.get('started_monotonic') or st.get('queued_monotonic') or now_m)
                elapsed = _file_job_elapsed_text(now_m - started)
            else:
                chat_id = int(job_meta.get('chat_id') or 0)
                msg_id = None
                label = str(job_meta.get('label') or 'Файл')
                elapsed = '0:00'
        try:
            if msg_id:
                close_s = internal_timer_seconds('file_status_close', 15)
                if ok:
                    final = f'✅ {label}\nГотово за {elapsed}.\nОкно закроется через {_format_duration_short(close_s)}.'
                else:
                    final = f"⚠️ {label}\nЗавершено за {elapsed}.\n{error_text or 'Telegram не подтвердил отправку.'}\nОкно закроется через {_format_duration_short(close_s)}."
                final = _v159_force_marker(final, 'Ф233', '⏳')
                bot.edit_message_text(final, chat_id=chat_id, message_id=int(msg_id))
                _v160_schedule_delete(chat_id, int(msg_id), close_s, 'file-close')
        except Exception:
            pass
        try:
            bot_journal('file_job_done' if ok else 'file_job_uncertain', chat_id, f"kind={job_meta.get('kind')} elapsed={elapsed} error={error_text}")
        except Exception:
            pass
        _v160_cancel_timer(f'v160:file-tick:{key}')
        try:
            DELAYED_SCHEDULER.cancel(f'file-job-tick:{key}')
        except Exception:
            pass
        # v259: release the distributed Key Value single-flight lock on every
        # terminal path (success, false result, exception, Telegram failure).
        # Without this, CSV/Excel and journal buttons share a stale lock and only
        # the first file action after deploy can run.
        try:
            kv_token = job_meta.get('kv_lock_token_v248') if isinstance(job_meta, dict) else None
            kv_name = str((job_meta or {}).get('kv_lock_name_v259') or f'interactive_file_job:v{int(globals().get("RELEASE_NUMBER") or 259)}')
            release_fn = globals().get('kv_distributed_lock_release_v248')
            if kv_token and callable(release_fn):
                released = bool(release_fn(kv_name, kv_token))
                try:
                    bot_journal('file_job_kv_lock_release_v259', chat_id, f'kind={job_meta.get("kind")}; released={int(released)}; lock={kv_name}')
                except Exception:
                    pass
        except Exception as kv_release_exc:
            try:
                log_error(f'file job Key Value release v259: {kv_release_exc}')
            except Exception:
                pass
        with _FILE_JOB_LOCK:
            _FILE_JOB_STATE.pop(key, None)
        if previous is None:
            try:
                delattr(_FILE_JOB_CONTEXT, 'value')
            except Exception:
                pass
        else:
            _FILE_JOB_CONTEXT.value = previous
try:
    _v177_legacy_0015_interactive_file_job_runner.__name__ = '_interactive_file_job_runner'
except Exception:
    pass

def _canon_submit_interactive_file_job__001(chat_id: int, kind: str, label: str, func, *args, **kwargs) -> tuple[bool, str]:
    chat_id = int(chat_id)
    gate = globals().get('memory_heavy_allowed')
    if callable(gate):
        try:
            allowed, reason = gate(str(kind or 'export'))
        except Exception:
            allowed, reason = (True, '')
        if not allowed:
            try:
                send_and_auto_delete(chat_id, f'🧠 {reason}', internal_timer_seconds('helper_message_close', 25))
            except Exception:
                pass
            return (False, reason or 'сервер временно разгружает память')
    key = _INTERACTIVE_FILE_JOB_KEY
    # v259: the previous runner cleared only the local single-flight state but
    # forgot to release the Render Key Value lock.  After the first CSV/XLSX/
    # journal job every later file button could therefore look dead until the
    # one-hour Redis TTL expired.  Scope the distributed lock by release so an
    # orphaned v258 lock cannot poison the new deploy, and always release it in
    # the runner finally block below.
    try:
        kv_lock_name = f'interactive_file_job:v{int(globals().get("RELEASE_NUMBER") or 259)}'
    except Exception:
        kv_lock_name = 'interactive_file_job:v259'
    kv_lock_token = None
    kv_lock_backend = 'local'
    kv_lock_fn = globals().get('kv_distributed_lock_try_v248')
    if callable(kv_lock_fn):
        try:
            allowed_kv, kv_lock_token, kv_lock_backend = kv_lock_fn(kv_lock_name, 900)
        except Exception:
            allowed_kv, kv_lock_token, kv_lock_backend = (True, None, 'local_fallback')
        if not allowed_kv:
            return (False, build_all_processes_toast(chat_id))
    with _FILE_JOB_LOCK:
        existing = _FILE_JOB_STATE.get(key)
        if isinstance(existing, dict):
            release_fn = globals().get('kv_distributed_lock_release_v248')
            if kv_lock_token and callable(release_fn):
                try:
                    release_fn(kv_lock_name, kv_lock_token)
                except Exception:
                    pass
            return (False, build_all_processes_toast(chat_id))
        meta = {'key': key, 'chat_id': chat_id, 'kind': str(kind), 'label': str(label), 'queued_monotonic': _v160_time.monotonic(), 'started_monotonic': 0.0, 'phase': 'в очереди', 'status_msg_id': None, 'last_ui_monotonic': 0.0, 'kv_lock_token_v248': kv_lock_token, 'kv_lock_backend_v248': kv_lock_backend, 'kv_lock_name_v259': kv_lock_name}
        _FILE_JOB_STATE[key] = meta
    try:
        _v160_cancel_timer(f'v199:service-delete:{chat_id}')
        status_mid = _v199_upsert_service_window(chat_id, _v159_file_status_text(str(label), '0:00', 'в очереди')) or None
        with _FILE_JOB_LOCK:
            if isinstance(_FILE_JOB_STATE.get(key), dict):
                _FILE_JOB_STATE[key]['status_msg_id'] = status_mid
        if status_mid:
            try:
                store = get_chat_store(chat_id)
                store['_v160_file_status_msg_id'] = int(status_mid)
                store['_v160_file_status_created_at'] = now_local().isoformat(timespec='seconds')
                save_data(data, chat_ids=[chat_id])
                schedule_quick_backup(chat_id, 0.2)
            except Exception:
                pass
    except Exception:
        pass
    ok = EXPORT_TASK_POOL.submit_unique(key, _interactive_file_job_runner, dict(meta), func, args, kwargs)
    if not ok:
        with _FILE_JOB_LOCK:
            _FILE_JOB_STATE.pop(key, None)
        release_fn = globals().get('kv_distributed_lock_release_v248')
        if kv_lock_token and callable(release_fn):
            try:
                release_fn(kv_lock_name, kv_lock_token)
            except Exception:
                pass
        return (False, build_all_processes_toast(chat_id))
    _v160_schedule(f'v160:file-tick:{key}', internal_timer_seconds('process_status_refresh', 10.0), _file_job_tick, key)
    try:
        bot_journal('file_job_queued', chat_id, f'kind={kind} label={label}; visual=1; marker=Ф233; timer=dedicated')
    except Exception:
        pass
    return (True, 'Запущено')

def _v198_primary_owner_chat(chat_id: int) -> bool:
    try:
        return bool(OWNER_ID) and int(chat_id) == int(OWNER_ID)
    except Exception:
        return False

def _v198_owner_only_technical_text(text: str) -> bool:
    value = str(text or '')
    low = value.lower()
    return '🚨' in value or 'смотрите журнал' in low or 'смотри /errors' in low or ('data constitution:' in low)

def _v198_route_helper_message(chat_id: int, text: str):
    """Return (target_chat_id, text) or (None, text) when a technical alert has nowhere safe to go."""
    try:
        source = int(chat_id)
    except Exception:
        source = 0
    value = str(text or '')
    if _v198_owner_only_technical_text(value) and (not _v198_primary_owner_chat(source)):
        try:
            owner = int(OWNER_ID or 0)
        except Exception:
            owner = 0
        if not owner:
            return (None, value)
        try:
            source_name = get_chat_display_name(source) if source else 'неизвестный чат'
        except Exception:
            source_name = str(source or 'неизвестный чат')
        value = f'{value}\n\nИсточник: {source_name} · {source}'
        return (owner, value)
    return (source, value)

def _v199_service_text(text: str) -> str:
    return _v159_force_marker(str(text or ''), 'Ф233', '⏳')
_V211_SERVICE_RUNTIME_ID = str(os.getenv('RENDER_INSTANCE_ID', '') or f'local-{os.getpid()}-{int(time.time())}')

def _v199_service_message_id(chat_id: int) -> int:
    """Return only a service message created by this running process.

    Ф233 is transient UI. Persisting its Telegram message_id is useful for same-process
    refreshes, but after deploy the old id can already be deleted.  Never probe/edit a
    previous-runtime id: clear it locally and create a fresh Ф233 instead.
    """
    try:
        store = get_chat_store(int(chat_id))
        mid = int(store.get('_v199_service_status_msg_id') or 0)
        owner = str(store.get('_v199_service_status_runtime_id') or '')
        if mid and owner != _V211_SERVICE_RUNTIME_ID:
            store.pop('_v199_service_status_msg_id', None)
            store.pop('_v199_service_status_runtime_id', None)
            if int(store.get('_v160_file_status_msg_id') or 0) == mid:
                store.pop('_v160_file_status_msg_id', None)
                store.pop('_v160_file_status_created_at', None)
            return 0
        return mid
    except Exception:
        return 0

def _v199_clear_service_message(chat_id: int, message_id: int) -> None:
    try:
        store = get_chat_store(int(chat_id))
        if int(store.get('_v199_service_status_msg_id') or 0) == int(message_id):
            store.pop('_v199_service_status_msg_id', None)
            store.pop('_v199_service_status_runtime_id', None)
        if int(store.get('_v160_file_status_msg_id') or 0) == int(message_id):
            store.pop('_v160_file_status_msg_id', None)
            store.pop('_v160_file_status_created_at', None)
    except Exception:
        pass

def _v199_delete_service_message(chat_id: int, message_id: int) -> None:
    try:
        bot.delete_message(int(chat_id), int(message_id))
    except Exception:
        pass
    _v199_clear_service_message(chat_id, message_id)

def _v199_upsert_service_window(chat_id: int, text: str, *, parse_mode=None) -> int:
    chat_id = int(chat_id)
    marked = _v199_service_text(text)
    mid = _v199_service_message_id(chat_id)
    if mid:
        try:
            kwargs = {'chat_id': chat_id, 'message_id': mid}
            if parse_mode:
                kwargs['parse_mode'] = parse_mode
            bot.edit_message_text(marked, **kwargs)
            return mid
        except Exception:
            _v199_clear_service_message(chat_id, mid)
    kwargs = {}
    if parse_mode:
        kwargs['parse_mode'] = parse_mode
    msg = bot.send_message(chat_id, marked, **kwargs)
    mid = int(getattr(msg, 'message_id', 0) or 0)
    if mid:
        try:
            _store = get_chat_store(chat_id)
            _store['_v199_service_status_msg_id'] = mid
            _store['_v199_service_status_runtime_id'] = _V211_SERVICE_RUNTIME_ID
            save_data(data, chat_ids=[chat_id])
        except Exception:
            pass
    return mid

def _v199_active_file_state_for_chat(chat_id: int):
    with _FILE_JOB_LOCK:
        for st in _FILE_JOB_STATE.values():
            if isinstance(st, dict) and int(st.get('chat_id') or 0) == int(chat_id):
                return st
    return None

def _v199_render_active_file_state(st: dict) -> str:
    now_m = _v160_time.monotonic()
    label = str(st.get('label') or 'Файл')
    phase = str(st.get('phase') or 'работаю')
    started = float(st.get('started_monotonic') or st.get('queued_monotonic') or now_m)
    base = _v159_file_status_text(label, _file_job_elapsed_text(now_m - started), phase, st.get('current'), st.get('total'))
    helper = str(st.get('helper_text_v199') or '').strip()
    deadline = float(st.get('helper_deadline_v199') or 0.0)
    if helper and deadline > now_m:
        base = re.sub('\\\\n\\\\nФ233[^\\\\n]*$', '', str(base).rstrip())
        return _v199_service_text(base + '\\n\\n' + helper)
    return _v199_service_text(base)

def _v199_service_helper_expire(chat_id: int, expected_deadline: float):
    st = _v199_active_file_state_for_chat(chat_id)
    if not isinstance(st, dict):
        return
    with _FILE_JOB_LOCK:
        if abs(float(st.get('helper_deadline_v199') or 0.0) - float(expected_deadline)) > 0.001:
            return
        if float(expected_deadline) > _v160_time.monotonic():
            return
        st.pop('helper_text_v199', None)
        st.pop('helper_deadline_v199', None)
        mid = int(st.get('status_msg_id') or 0)
        text = _v199_render_active_file_state(st)
    if mid:
        try:
            bot.edit_message_text(text, chat_id=int(chat_id), message_id=mid)
        except Exception:
            pass

def _canon_send_and_auto_delete__001(chat_id: int, text: str, delay: int=25):
    target_chat_id, routed_text = _v198_route_helper_message(chat_id, text)
    if not target_chat_id or is_finance_output_suppressed(target_chat_id):
        return
    delay = _v159_helper_delay(delay)
    try:
        st = _v199_active_file_state_for_chat(int(target_chat_id))
        if isinstance(st, dict):
            deadline = _v160_time.monotonic() + float(delay)
            with _FILE_JOB_LOCK:
                st['helper_text_v199'] = str(routed_text or '')
                st['helper_deadline_v199'] = deadline
                mid = int(st.get('status_msg_id') or 0)
                rendered = _v199_render_active_file_state(st)
            if mid:
                bot.edit_message_text(rendered, chat_id=int(target_chat_id), message_id=mid)
            _v160_schedule(f'v199:service-helper-expire:{int(target_chat_id)}', delay, _v199_service_helper_expire, int(target_chat_id), deadline)
            return
        mid = _v199_upsert_service_window(int(target_chat_id), str(routed_text or ''))
        if mid:
            _v160_cancel_timer(f'v199:service-delete:{int(target_chat_id)}')
            _v160_schedule(f'v199:service-delete:{int(target_chat_id)}', delay, _v199_delete_service_message, int(target_chat_id), int(mid))
    except Exception as exc:
        try:
            log_error(f'send_and_auto_delete v199: {exc}')
        except Exception:
            pass

def _v199_send_html_and_auto_delete_service(chat_id: int, html_text: str, delay: int=25):
    target_chat_id, routed_text = _v198_route_helper_message(chat_id, html_text)
    if not target_chat_id or is_finance_output_suppressed(target_chat_id):
        return
    delay = _v159_helper_delay(delay)
    try:
        mid = _v199_upsert_service_window(int(target_chat_id), str(routed_text or ''), parse_mode='HTML')
        if mid:
            _v160_cancel_timer(f'v199:service-delete:{int(target_chat_id)}')
            _v160_schedule(f'v199:service-delete:{int(target_chat_id)}', delay, _v199_delete_service_message, int(target_chat_id), int(mid))
    except Exception as exc:
        try:
            log_error(f'send_html_and_auto_delete v199: {exc}')
        except Exception:
            pass

def send_owner_technical_alert(text: str, delay: int=25, source_chat_id: int | None=None):
    """Explicit technical-notification API. It never emits into non-owner contours."""
    try:
        owner = int(OWNER_ID or 0)
    except Exception:
        owner = 0
    if not owner:
        return False
    value = str(text or '')
    if source_chat_id is not None:
        try:
            source = int(source_chat_id)
            if source != owner:
                try:
                    source_name = get_chat_display_name(source)
                except Exception:
                    source_name = str(source)
                value += f'\n\nИсточник: {source_name} · {source}'
        except Exception:
            pass
    send_and_auto_delete(owner, value, delay)
    return True

def send_plain_and_auto_delete(chat_id: int, text: str, delay: int=8):
    """Short business feedback for non-owner contours, without W/Ф diagnostic markers."""
    try:
        target = int(chat_id)
    except Exception:
        return
    if is_finance_output_suppressed(target):
        return
    try:
        msg = bot.send_message(target, str(text or ''))
        _v160_schedule_delete(target, int(msg.message_id), max(0.1, float(delay)), 'plain-helper')
    except Exception as exc:
        try:
            log_error(f'send_plain_and_auto_delete v198: {exc}')
        except Exception:
            pass

def _canon_send_html_and_auto_delete__001(chat_id: int, html_text: str, delay: int=25):
    return _v199_send_html_and_auto_delete_service(chat_id, html_text, delay)

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
_V160_FAST_EDIT_LOCKS = defaultdict(_v160_threading.RLock)
_V160_FAST_EDIT_LAST = {}
_V160_FAST_EDIT_MIN_GAP = max(0.03, min(0.2, float(_v160_os.getenv('V160_UI_MIN_GAP_SECONDS', '0.08') or '0.08')))

def _canon_callback_should_debounce__001(call, data_str: str, min_interval: float=0.12) -> bool:
    return str(data_str or '') == 'none'

def _canon_fast_ui_edit_message_text__001(chat_id: int, message_id: int, text: str, reply_markup=None, parse_mode=None, purpose: str='fast_ui') -> str:
    chat_id = int(chat_id)
    message_id = int(message_id)
    try:
        code = (_V159_TIMER_PURPOSE_MARKERS or {}).get(str(purpose or ''))
        if code:
            text = _v159_force_marker(text, code)
    except Exception:
        pass
    try:
        if 'secret' not in str(purpose or '').lower():
            reply_markup = ensure_previous_back_nav_keyboard(reply_markup, chat_id, message_id)
            reply_markup = ensure_main_back_nav_keyboard(reply_markup, chat_id)
    except Exception:
        pass
    try:
        text = _ensure_window_marker_for_render(text, reply_markup, chat_id, message_id, purpose)
    except Exception:
        pass
    try:
        augment = globals().get('_v160_augment_markup')
        if callable(augment):
            reply_markup = augment(reply_markup, text, chat_id)
    except Exception:
        pass
    payload = {'chat_id': chat_id, 'message_id': message_id, 'text': text, 'reply_markup': reply_markup, 'parse_mode': parse_mode, 'purpose': purpose}
    try:
        prepare = globals().get('window_diag_prepare_fast_ui_payload')
        if callable(prepare):
            payload = prepare(payload) or payload
    except Exception:
        pass
    try:
        cancel_fast_ui_edit(chat_id, message_id)
    except Exception:
        pass
    key = (chat_id, message_id)
    with _V160_FAST_EDIT_LOCKS[key]:
        now_m = _v160_time.monotonic()
        last = float(_V160_FAST_EDIT_LAST.get(key, 0.0) or 0.0)
        remain = _V160_FAST_EDIT_MIN_GAP - (now_m - last)
        if remain > 0:
            _v160_time.sleep(remain)
        _V160_FAST_EDIT_LAST[key] = _v160_time.monotonic()
        try:
            apply_fn = globals().get('window_diag_fast_ui_apply')
            if callable(apply_fn):
                apply_fn(payload, delayed=False)
        except Exception:
            pass
        return _perform_fast_ui_edit(payload)
_V160_CALLBACK_LOCK = _v160_threading.RLock()
_V160_CALLBACK_IDS = {}

def _v160_exact_callback_duplicate(call) -> bool:
    call_id = str(getattr(call, 'id', '') or '')
    if not call_id:
        return False
    now_m = _v160_time.monotonic()
    with _V160_CALLBACK_LOCK:
        for old, ts in list(_V160_CALLBACK_IDS.items()):
            if now_m - float(ts) > 600:
                _V160_CALLBACK_IDS.pop(old, None)
        if call_id in _V160_CALLBACK_IDS:
            return True
        _V160_CALLBACK_IDS[call_id] = now_m
    return False

def _v160_clear_legacy_same_button_suppression(call) -> None:
    try:
        store = globals().get('_V153_CALLBACK_SIGNATURES')
        lock = globals().get('_V153_LOCK')
        if not isinstance(store, dict):
            return
        actor_fn = globals().get('_v153_actor_id')
        actor = int(actor_fn(call)) if callable(actor_fn) else int(getattr(getattr(call, 'from_user', None), 'id', 0) or 0)
        message = getattr(call, 'message', None)
        signature = (actor, int(getattr(getattr(message, 'chat', None), 'id', 0) or 0), int(getattr(message, 'message_id', 0) or 0), str(getattr(call, 'data', '') or ''))
        if lock is not None:
            with lock:
                store.pop(signature, None)
        else:
            store.pop(signature, None)
    except Exception:
        pass

def _canon_window_diag_duplicate_marker__001(chat_id: int, message_id: int, marker: str) -> dict:
    return {}

def _canon_cleanup_open_window_registry__001(reason: str='manual') -> dict:
    now_dt = now_local()
    keep_days = max(7, min(90, int(_v160_os.getenv('V160_PARALLEL_WINDOW_KEEP_DAYS', '30') or '30')))
    cutoff = now_dt - _v160_timedelta(days=keep_days)
    removed = duplicates = normalized = 0
    with _V146_WINDOW_LOCK:
        reg = _open_window_registry()
        grouped = defaultdict(list)
        for key, item in list(reg.items()):
            try:
                cid = int((item or {}).get('chat_id') or 0)
                mid = int((item or {}).get('message_id') or 0)
                if not cid or not mid:
                    reg.pop(key, None)
                    removed += 1
                    continue
                grouped[cid, mid].append((key, item or {}))
            except Exception:
                reg.pop(key, None)
                removed += 1
        new_reg = {}
        for (chat_id, message_id), rows in grouped.items():
            rows.sort(key=lambda pair: (int((pair[1] or {}).get('epoch') or 0), str((pair[1] or {}).get('updated_at') or '')), reverse=True)
            key, item = rows[0]
            duplicates += max(0, len(rows) - 1)
            try:
                updated = datetime.fromisoformat(str((item or {}).get('updated_at') or ''))
                if updated.tzinfo is None:
                    updated = updated.replace(tzinfo=now_dt.tzinfo)
            except Exception:
                updated = now_dt
            if updated < cutoff:
                removed += 1
                continue
            canonical = _v146_registry_key(chat_id, message_id)
            item = dict(item or {})
            item['epoch'] = max(1, int(item.get('epoch') or 1))
            item['parallel_allowed'] = True
            new_reg[canonical] = item
            if canonical != key:
                normalized += 1
        if duplicates or removed or normalized or (len(reg) != len(new_reg)):
            reg.clear()
            reg.update(new_reg)
            save_data(data, root_only=True)
    result = {'reason': reason, 'kept': len(_open_window_registry() or {}), 'removed': removed, 'duplicates_removed': duplicates, 'parallel_preserved': True, 'keys_normalized': normalized}
    try:
        bot_journal('window_registry_cleanup', None, _v160_json.dumps(result, ensure_ascii=False))
    except Exception:
        pass
    return result
_V160_PREV_RETURN_TO_MAIN = _v177_legacy_0243_return_to_main_window_closing_previous

def _v177_legacy_0244_return_to_main_window_closing_previous(chat_id: int, day_key: str, current_message_id: int | None=None):
    chat_id = int(chat_id)
    day_key = str(day_key)[:10]
    try:
        current_mid = int(current_message_id or 0)
    except Exception:
        current_mid = 0
    try:
        old_mid = int(get_active_window_id(chat_id, day_key) or 0)
    except Exception:
        old_mid = 0
    if current_mid:
        try:
            cancel_auto_delete_for_message(chat_id, current_mid)
        except Exception:
            pass
        try:
            cancel_fast_ui_edit(chat_id, current_mid)
        except Exception:
            pass
        txt, _ = render_day_window(chat_id, day_key)
        kb = build_main_keyboard(day_key, chat_id)
        result = fast_ui_edit_message_text(chat_id, current_mid, txt, reply_markup=kb, parse_mode='HTML', purpose='back_main_instant')
        try:
            bot_journal('back_main_fast', chat_id, f'day={day_key} result={result} old={old_mid or None} current={current_mid}; parallel=1')
        except Exception:
            pass
        if result == 'ok':
            set_active_window_id(chat_id, day_key, current_mid)
            if old_mid and old_mid != current_mid:
                try:
                    row = get_registered_open_window(chat_id, old_mid) or {}
                    if row:
                        row['parallel_allowed'] = True
                    bot_journal('parallel_main_preserved', chat_id, f'day={day_key}; primary={current_mid}; preserved={old_mid}')
                except Exception:
                    pass
            schedule_balance_panel_refresh(chat_id, 0.05)
            return
        if result == 'not_found':
            try:
                unregister_open_window(chat_id, current_mid)
            except Exception:
                pass
            if old_mid and old_mid != current_mid:
                try:
                    backup_window_for_owner(chat_id, day_key, message_id_override=old_mid)
                    return
                except Exception:
                    pass
    if callable(_V160_PREV_RETURN_TO_MAIN):
        return _V160_PREV_RETURN_TO_MAIN(chat_id, day_key, current_message_id=None)
    return None
try:
    _v177_legacy_0244_return_to_main_window_closing_previous.__name__ = 'return_to_main_window_closing_previous'
except Exception:
    pass
try:
    WINDOW_MARKER_CONSTANTS.update({'v149:rem:merge:*': 'Ф191', 'v149:rem:command:*': 'Ф191', 'v149:rem:item_merge:*': 'Ф191', 'v149:rem:item_complete:*': 'Ф191', 'v149:rem:done:*': 'Ф191', 'v149:rem:history': 'Ф191', 'v160:marker_capture': 'Ф235', 'v160:tz_capture': 'Ф236', 'v160:export_markers': 'Ф237', 'v160:export_tz': 'Ф238'})
except Exception:
    pass
_V160_PREV_EXPECTED_MARKER = _v177_legacy_0294_v155_expected_marker

def _v177_legacy_0295_v155_expected_marker(action: str, chat_id: int) -> str:
    raw = str(action or '')
    if raw.startswith('v149:rem:merge:') or raw.startswith('v149:rem:command:') or raw.startswith('v149:rem:item_merge:') or raw.startswith('v149:rem:item_complete:') or raw.startswith('v149:rem:done:') or (raw == 'v149:rem:history'):
        return 'Ф191'
    if raw.startswith('v160:'):
        return ''
    if callable(_V160_PREV_EXPECTED_MARKER):
        try:
            return str(_V160_PREV_EXPECTED_MARKER(raw, int(chat_id)) or '')
        except Exception:
            pass
    return ''
try:
    _v177_legacy_0295_v155_expected_marker.__name__ = '_v155_expected_marker'
except Exception:
    pass
_V160_ANNOTATION_LOCK = _v160_threading.RLock()
_V160_ANNOTATION_PENDING = {}
_V160_LAST_WINDOW_META = {}
_V160_PENDING_TTL = 900.0
_V160_MARKER_ROOT_KEY = '_window_marker_catalog_v160'
_V160_TZ_ROOT_KEY = '_window_tz_v160'

def _v160_marker_from_text(text: str) -> str:
    try:
        fn = globals().get('_window_diag_marker')
        marker = str(fn(str(text or '')) or '') if callable(fn) else ''
        if marker:
            return marker.upper()
    except Exception:
        pass
    try:
        match = _v160_re.search('(?:^|\\n)\\s*([СФПОВсов]\\d{1,6})(?:-\\(W[A-Z0-9]{6,12}\\))?(?:\\s*[⏳⏰])?\\s*$', str(text or ''), flags=_v160_re.IGNORECASE)
        return str(match.group(1) if match else '').upper()
    except Exception:
        return ''

def _v160_markup_callbacks(reply_markup) -> set[str]:
    out = set()
    try:
        for row in list(getattr(reply_markup, 'keyboard', None) or []):
            for button in row or []:
                cb = str(getattr(button, 'callback_data', '') or '')
                if cb:
                    out.add(cb)
    except Exception:
        pass
    return out

def _v177_legacy_0317_v160_augment_markup(reply_markup, text: str, chat_id=None):
    marker = _v160_marker_from_text(text)
    if not marker:
        return reply_markup
    try:
        if isinstance(reply_markup, types.InlineKeyboardMarkup):
            kb = _v160_copy.deepcopy(reply_markup)
        else:
            kb = types.InlineKeyboardMarkup()
    except Exception:
        kb = reply_markup if reply_markup is not None else types.InlineKeyboardMarkup()
    try:
        cid = int(chat_id) if chat_id is not None else 0
    except Exception:
        cid = 0
    show_marker = True
    show_tz = True
    try:
        vis_fn = globals().get('circle_annotation_button_enabled_v219')
        if cid and callable(vis_fn):
            show_marker = bool(vis_fn('iz_mr', cid))
            show_tz = bool(vis_fn('tz', cid))
    except Exception:
        show_marker = True
        show_tz = True
    try:
        rows = list(getattr(kb, 'keyboard', None) or [])
        cleaned = []
        for row in rows:
            keep = []
            for button in list(row or []):
                cb = str(getattr(button, 'callback_data', '') or '')
                if cb == 'v160:marker_capture' and (not show_marker):
                    continue
                if cb == 'v160:tz_capture' and (not show_tz):
                    continue
                keep.append(button)
            if keep:
                cleaned.append(keep)
        try:
            kb.keyboard = cleaned
        except Exception:
            pass
        callbacks = _v160_markup_callbacks(kb)
        add = []
        if show_marker and 'v160:marker_capture' not in callbacks:
            add.append(IB('/iz-mr', callback_data='v160:marker_capture'))
        if show_tz and 'v160:tz_capture' not in callbacks:
            add.append(IB('/tz', callback_data='v160:tz_capture'))
        if add:
            kb.row(*add)
        if marker == 'Ф89':
            callbacks = _v160_markup_callbacks(kb)
            if 'v160:export_markers' not in callbacks:
                kb.row(IB('🏷 Скачать маркировки окон', callback_data='v160:export_markers'))
            if 'v160:export_tz' not in callbacks:
                kb.row(IB('📝 Скачать ТЗ окон', callback_data='v160:export_tz'))
    except Exception:
        return reply_markup
    return kb
try:
    _v177_legacy_0317_v160_augment_markup.__name__ = '_v160_augment_markup'
except Exception:
    pass

def _v160_is_switch_callback(raw: str) -> bool:
    low = str(raw or '').casefold()
    switch_tokens = ('toggle', '_on', '_off', ':on', ':off', 'enable', 'disable', 'itmr_digit:', 'itmr_unit:', 'itmr_backspace', 'itmr_clear', 'itmr_apply')
    return any((token in low for token in switch_tokens))

def _v160_recent_diag_for_message(chat_id: int, message_id: int) -> dict:
    try:
        rows = list(window_diagnostic_tail(160)) if callable(globals().get('window_diagnostic_tail')) else []
    except Exception:
        rows = []
    for row in reversed(rows):
        try:
            if int(row.get('chat_id') or 0) != int(chat_id) or int(row.get('message_id') or 0) != int(message_id):
                continue
            cb = str(row.get('callback_data') or '')
            if cb.startswith('v160:') or _v160_is_switch_callback(cb):
                continue
            if row.get('action') in {'window_edit_applied', 'window_created', 'window_ui_edit_apply', 'window_registry_registered', 'window_registry_epoch_changed'}:
                return {'action': row.get('action'), 'callback': cb, 'caller': row.get('caller'), 'update_id': row.get('update_id'), 'detail': dict(row.get('detail') or {}), 'ts': row.get('ts')}
        except Exception:
            continue
    return {}

def _v207_detach_f233_service_role_if_converted(chat_id: int, message_id: int, marker: str) -> None:
    """A former F233 message becomes an ordinary window as soon as another marker is rendered into it.

    v205 could leave the old service-message id and its delete/file timers attached to the
    Telegram message.  Later F233 progress/helper activity could then overwrite or delete a
    window that the user had already turned into main/back/another normal window.
    """
    try:
        cid = int(chat_id)
        mid = int(message_id)
        mark = str(marker or '').upper()
    except Exception:
        return
    if not cid or not mid or (not mark) or (mark == 'Ф233'):
        return
    try:
        if int(_v199_service_message_id(cid) or 0) != mid:
            return
    except Exception:
        return
    try:
        _v160_cancel_timer(f'v199:service-delete:{cid}')
    except Exception:
        pass
    try:
        _v160_cancel_timer(f'v199:service-helper-expire:{cid}')
    except Exception:
        pass
    try:
        _v160_cancel_timer(f'v160:file-close:{cid}:{mid}')
    except Exception:
        pass
    try:
        cancel_auto_delete_for_message(cid, mid)
    except Exception:
        pass
    try:
        _v199_clear_service_message(cid, mid)
    except Exception:
        pass
    try:
        store = get_chat_store(cid)
        if int(store.get('_v160_file_status_msg_id') or 0) == mid:
            store.pop('_v160_file_status_msg_id', None)
        save_data(data, chat_ids=[cid])
    except Exception:
        pass
    try:
        with _FILE_JOB_LOCK:
            for st in _FILE_JOB_STATE.values():
                if isinstance(st, dict) and int(st.get('chat_id') or 0) == cid and (int(st.get('status_msg_id') or 0) == mid):
                    st['status_msg_id'] = None
                    st.pop('helper_text_v199', None)
                    st.pop('helper_deadline_v199', None)
    except Exception:
        pass
    try:
        bot_journal('f233_converted_to_normal_window_v207', cid, f'msg={mid}; marker={mark}')
    except Exception:
        pass

def _v160_note_window_meta(chat_id: int, message_id: int, text: str, purpose: str='') -> None:
    marker = _v160_marker_from_text(text)
    if not marker:
        return
    try:
        _v207_detach_f233_service_role_if_converted(int(chat_id), int(message_id), marker)
    except Exception:
        pass
    ctx = {}
    try:
        ctx = _current_telegram_update_context()
    except Exception:
        pass
    raw_callback = str((ctx or {}).get('callback_data') or '')
    with _V160_ANNOTATION_LOCK:
        previous_meta = dict(_V160_LAST_WINDOW_META.get((int(chat_id), int(message_id))) or {})
    if _v160_is_switch_callback(raw_callback) and previous_meta:
        previous_meta['seen_at'] = now_local().isoformat(timespec='milliseconds')
        previous_meta['last_switch_callback'] = raw_callback[:240]
        with _V160_ANNOTATION_LOCK:
            _V160_LAST_WINDOW_META[int(chat_id), int(message_id)] = previous_meta
        return
    rows = [x.strip() for x in str(text or '').splitlines() if x.strip()]
    first_line = rows[0][:220] if rows else ''
    meta = {'version': VERSION, 'marker': marker, 'chat_id': int(chat_id), 'message_id': int(message_id), 'first_line': first_line, 'purpose': str(purpose or '')[:180], 'callback': raw_callback[:240], 'update_id': (ctx or {}).get('update_id'), 'seen_at': now_local().isoformat(timespec='milliseconds')}
    if not raw_callback:
        meta.update({k: v for k, v in _v160_recent_diag_for_message(chat_id, message_id).items() if v not in (None, '', {})})
    with _V160_ANNOTATION_LOCK:
        _V160_LAST_WINDOW_META[int(chat_id), int(message_id)] = meta
        if len(_V160_LAST_WINDOW_META) > 1200:
            for stale in list(_V160_LAST_WINDOW_META)[:200]:
                _V160_LAST_WINDOW_META.pop(stale, None)
_V160_ORIG_SEND_MESSAGE = getattr(bot, 'send_message', None)
_V160_ORIG_EDIT_MESSAGE_TEXT = getattr(bot, 'edit_message_text', None)
_V160_ORIG_EDIT_MESSAGE_CAPTION = getattr(bot, 'edit_message_caption', None)
if callable(_V160_ORIG_SEND_MESSAGE):

    def _v160_send_message(chat_id, text, *args, **kwargs):
        try:
            kwargs['reply_markup'] = _v160_augment_markup(kwargs.get('reply_markup'), str(text or ''), chat_id)
        except Exception:
            pass
        result = _V160_ORIG_SEND_MESSAGE(chat_id, text, *args, **kwargs)
        try:
            _v160_note_window_meta(int(chat_id), int(getattr(result, 'message_id', 0) or 0), str(text or ''), 'send_message')
        except Exception:
            pass
        return result
    bot.send_message = _v160_send_message
if callable(_V160_ORIG_EDIT_MESSAGE_TEXT):

    def _v160_edit_message_text(text, *args, **kwargs):
        chat_id = kwargs.get('chat_id') if kwargs.get('chat_id') is not None else args[0] if len(args) > 0 else None
        message_id = kwargs.get('message_id') if kwargs.get('message_id') is not None else args[1] if len(args) > 1 else None
        try:
            kwargs['reply_markup'] = _v160_augment_markup(kwargs.get('reply_markup'), str(text or ''), chat_id)
        except Exception:
            pass
        result = _V160_ORIG_EDIT_MESSAGE_TEXT(text, *args, **kwargs)
        try:
            _v160_note_window_meta(int(chat_id), int(message_id), str(text or ''), 'edit_message_text')
        except Exception:
            pass
        return result
    bot.edit_message_text = _v160_edit_message_text
if callable(_V160_ORIG_EDIT_MESSAGE_CAPTION):

    def _v160_edit_message_caption(*args, **kwargs):
        caption = kwargs.get('caption')
        if caption is None and args:
            caption = args[0]
        chat_id = kwargs.get('chat_id') if kwargs.get('chat_id') is not None else args[1] if len(args) > 1 else None
        try:
            kwargs['reply_markup'] = _v160_augment_markup(kwargs.get('reply_markup'), str(caption or ''), chat_id)
        except Exception:
            pass
        result = _V160_ORIG_EDIT_MESSAGE_CAPTION(*args, **kwargs)
        try:
            _v160_note_window_meta(int(kwargs.get('chat_id')), int(kwargs.get('message_id')), str(caption or ''), 'edit_message_caption')
        except Exception:
            pass
        return result
    bot.edit_message_caption = _v160_edit_message_caption

def _v160_annotation_roots():
    gs = data.setdefault('_global_settings', {})
    catalog = gs.setdefault(_V160_MARKER_ROOT_KEY, {})
    tz_rows = gs.setdefault(_V160_TZ_ROOT_KEY, [])
    if not isinstance(catalog, dict):
        catalog = {}
        gs[_V160_MARKER_ROOT_KEY] = catalog
    if not isinstance(tz_rows, list):
        tz_rows = []
        gs[_V160_TZ_ROOT_KEY] = tz_rows
    return (catalog, tz_rows)

def _v160_persist_annotations(chat_id: int) -> None:
    try:
        save_data(data, root_only=True)
    except Exception:
        pass
    try:
        schedule_delta_backup(int(OWNER_ID or chat_id), delay=0.2, reason='v160_window_annotations')
    except Exception:
        try:
            schedule_quick_backup(int(OWNER_ID or chat_id), 0.5)
        except Exception:
            pass

def _v177_legacy_0319_v160_source_meta(chat_id: int, message_id: int, marker: str, text: str='') -> dict:
    with _V160_ANNOTATION_LOCK:
        meta = dict(_V160_LAST_WINDOW_META.get((int(chat_id), int(message_id))) or {})
    if not meta:
        meta = _v160_recent_diag_for_message(chat_id, message_id)
    rows = [x.strip() for x in str(text or '').splitlines() if x.strip()]
    meta.update({'version': VERSION, 'marker': str(marker), 'chat_id': int(chat_id), 'message_id': int(message_id), 'first_line': str(meta.get('first_line') or (rows[0] if rows else ''))[:220], 'captured_at': now_local().isoformat(timespec='milliseconds')})
    return meta
try:
    _v177_legacy_0319_v160_source_meta.__name__ = '_v160_source_meta'
except Exception:
    pass

def _v160_save_marker_name(chat_id: int, user_id: int, marker: str, name: str, source: dict) -> dict:
    marker = str(marker or '').upper().strip()
    name = ' '.join(str(name or '').strip().split())[:180]
    if not marker or not name:
        raise ValueError('marker/name missing')
    catalog, _ = _v160_annotation_roots()
    now_s = now_local().isoformat(timespec='milliseconds')
    with _V160_ANNOTATION_LOCK:
        row = dict(catalog.get(marker) or {})
        history = list(row.get('name_history') or [])
        previous = str(row.get('name') or '')
        if previous and previous != name:
            history.append({'at': now_s, 'name': previous, 'changed_by': int(user_id)})
        row.update({'marker': marker, 'name': name, 'name_history': history[-30:], 'first_named_at': str(row.get('first_named_at') or now_s), 'last_named_at': now_s, 'named_by': int(user_id), 'source': _v160_copy.deepcopy(source)})
        catalog[marker] = row
    _v160_persist_annotations(chat_id)
    try:
        bot_journal('window_marker_named', chat_id, f"marker={marker}; name={name[:100]}; source_msg={source.get('message_id')}")
    except Exception:
        pass
    return row

def _v177_legacy_0320_v160_save_tz(chat_id: int, user_id: int, marker: str, body: str, source: dict) -> dict:
    marker = str(marker or '').upper().strip()
    body = str(body or '')
    if len(body) > 200000:
        raise ValueError('ТЗ слишком большое: максимум 200000 символов')
    if not marker or not body.strip():
        raise ValueError('marker/tz missing')
    catalog, rows = _v160_annotation_roots()
    now_s = now_local().isoformat(timespec='milliseconds')
    row = {'id': f'tz-{int(_v160_time.time() * 1000)}-{int(user_id)}', 'at': now_s, 'marker': marker, 'window_name': str((catalog.get(marker) or {}).get('name') or ''), 'text': body, 'user_id': int(user_id), 'source': _v160_copy.deepcopy(source)}
    with _V160_ANNOTATION_LOCK:
        rows.append(row)
        if len(rows) > 2000:
            del rows[:-2000]
    _v160_persist_annotations(chat_id)
    try:
        bot_journal('window_tz_saved', chat_id, f"marker={marker}; chars={len(body)}; source_msg={source.get('message_id')}")
    except Exception:
        pass
    return row
try:
    _v177_legacy_0320_v160_save_tz.__name__ = '_v160_save_tz'
except Exception:
    pass

def _v160_pending_key(chat_id: int, user_id: int):
    return (int(chat_id), int(user_id))

def _v212_legacy_v160_set_pending(chat_id: int, user_id: int, mode: str, marker: str, source: dict, prompt_message_id: int=0) -> None:
    now_m = _v160_time.monotonic()
    with _V160_ANNOTATION_LOCK:
        for key, row in list(_V160_ANNOTATION_PENDING.items()):
            if now_m - float((row or {}).get('created_mono') or 0.0) > _V160_PENDING_TTL:
                _V160_ANNOTATION_PENDING.pop(key, None)
        _V160_ANNOTATION_PENDING[_v160_pending_key(chat_id, user_id)] = {'mode': str(mode), 'marker': str(marker), 'source': _v160_copy.deepcopy(source), 'created_mono': now_m, 'prompt_message_id': int(prompt_message_id or 0)}

def _v207_capture_prompt_set(chat_id: int, user_id: int, prompt_message_id: int) -> None:
    if not int(prompt_message_id or 0):
        return
    with _V160_ANNOTATION_LOCK:
        row = _V160_ANNOTATION_PENDING.get(_v160_pending_key(chat_id, user_id))
        if isinstance(row, dict):
            row['prompt_message_id'] = int(prompt_message_id)

def _v207_delete_capture_prompt(chat_id: int, pending: dict | None) -> None:
    try:
        mid = int((pending or {}).get('prompt_message_id') or 0)
    except Exception:
        mid = 0
    if not mid:
        return
    try:
        bot.delete_message(int(chat_id), mid)
    except Exception:
        pass

def _canon_v160_get_pending__001(chat_id: int, user_id: int, pop: bool=False):
    key = _v160_pending_key(chat_id, user_id)
    with _V160_ANNOTATION_LOCK:
        row = _V160_ANNOTATION_PENDING.get(key)
        if row and _v160_time.monotonic() - float(row.get('created_mono') or 0.0) > _V160_PENDING_TTL:
            _V160_ANNOTATION_PENDING.pop(key, None)
            return None
        if pop and row:
            return _V160_ANNOTATION_PENDING.pop(key, None)
        return dict(row or {}) if row else None

def _v160_can_annotate(user_id: int) -> bool:
    try:
        fn = globals().get('_v153_platform_owner')
        if callable(fn):
            return bool(fn(int(user_id)))
    except Exception:
        pass
    try:
        return int(user_id) == int(OWNER_ID or 0)
    except Exception:
        return False

def _v160_call_source(call):
    message = getattr(call, 'message', None)
    chat_id = int(getattr(getattr(message, 'chat', None), 'id', 0) or 0)
    message_id = int(getattr(message, 'message_id', 0) or 0)
    text = str(getattr(message, 'text', None) or getattr(message, 'caption', None) or '')
    marker = _v160_marker_from_text(text)
    source = _v160_source_meta(chat_id, message_id, marker, text)
    return (chat_id, message_id, marker, source)

def _canon_v160_begin_capture__001(call, mode: str) -> bool:
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
        title = f'🏷 Название окна для {marker}'
        detail = f'\nСейчас: {current_name}' if current_name else ''
        prompt = f'{title}{detail}\n\nНапишите постоянное понятное имя этого окна одним сообщением.'
        placeholder = 'Например: Меню напоминалок'
    else:
        label = f' — {current_name}' if current_name else ''
        prompt = f'📝 ТЗ для окна {marker}{label}\n\nМожно написать свободно или скопировать шаблон ниже и заполнить только нужные строки:\n\nЧто сейчас происходит:\nЧто должно происходить:\nКакие кнопки / текст / суммы изменить:\nЧто обязательно оставить без изменений:\nПример желаемого результата:\nОбласть: только это окно / всё направление / весь бот\n\nЕсли область не указана, ТЗ считается общим для всего бота, как и раньше.'
        placeholder = 'Заполните ТЗ или напишите свободно'
    try:
        sent_prompt = bot.send_message(chat_id, prompt, reply_to_message_id=message_id, allow_sending_without_reply=True, reply_markup=types.ForceReply(selective=True, input_field_placeholder=placeholder))
        try:
            _v207_capture_prompt_set(chat_id, user_id, int(getattr(sent_prompt, 'message_id', 0) or 0))
        except Exception:
            pass
        bot.answer_callback_query(call.id, 'Контекст окна зафиксирован')
    except Exception:
        pass
    return True

def _v177_legacy_0322_v160_export_text(kind: str) -> tuple[str, str]:
    catalog, tz_rows = _v160_annotation_roots()
    now_s = now_local().strftime('%Y-%m-%d %H:%M:%S')
    if kind == 'markers':
        lines = ['МАРКИРОВКИ ОКОН', f'Версия: {VERSION}', f'Создано: {now_s}', '']
        actions_by_marker = defaultdict(list)
        try:
            for action, marker in (WINDOW_MARKER_CONSTANTS or {}).items():
                marker = str(marker or '').upper().strip()
                if marker and str(action) not in actions_by_marker[marker]:
                    actions_by_marker[marker].append(str(action))
        except Exception:
            pass
        markers = set(actions_by_marker) | {str(x).upper() for x in catalog}

        def _sort_marker(m):
            m = str(m)
            found = _v160_re.search('(\\d+)$', m)
            return (m[:1], int(found.group(1)) if found else 999999, m)
        for marker in sorted(markers, key=_sort_marker):
            row = dict(catalog.get(marker) or {})
            src = dict(row.get('source') or {})
            actions = actions_by_marker.get(marker) or []
            action_text = ', '.join(actions[:20]) + (f' … ещё {len(actions) - 20}' if len(actions) > 20 else '')
            lines.extend([f"{marker} = {row.get('name') or 'без пользовательского имени'}", f"  constant_actions: {action_text or '—'}", f"  first_line: {src.get('first_line') or '—'}", f"  callback_when_named: {src.get('callback') or '—'}", f"  purpose/action: {src.get('purpose') or src.get('action') or '—'}", f"  caller: {src.get('caller') or '—'}", f"  chat_id: {src.get('chat_id') or '—'}; message_id: {src.get('message_id') or '—'}", f"  named_at: {row.get('last_named_at') or '—'}", ''])
        return ('Маркировки_окон', '\n'.join(lines).rstrip() + '\n')
    lines = ['ТЗ ПО ОКНАМ', f'Версия: {VERSION}', f'Создано: {now_s}', '']
    for row in list(tz_rows):
        src = dict((row or {}).get('source') or {})
        lines.extend([f"[{row.get('at')}] {row.get('marker')} — {row.get('window_name') or (catalog.get(str(row.get('marker'))) or {}).get('name') or 'без имени'}", f"Источник: chat={src.get('chat_id') or '—'} msg={src.get('message_id') or '—'} callback={src.get('callback') or '—'}", str(row.get('text') or ''), '', '---', ''])
    return ('ТЗ_окон', '\n'.join(lines).rstrip() + '\n')
try:
    _v177_legacy_0322_v160_export_text.__name__ = '_v160_export_text'
except Exception:
    pass

def _v160_send_annotation_export(chat_id: int, kind: str):
    _file_job_progress('формирую файл', force=True)
    base, content = _v160_export_text(kind)
    folder = _v160_tempfile.mkdtemp(prefix='v160_annotations_')
    path = _v160_os.path.join(folder, f"{base}_{now_local().strftime('%Y_%m_%d_%H%M%S')}.txt")
    try:
        with open(path, 'w', encoding='utf-8') as fh:
            fh.write(content)
        _file_job_progress('отправляю файл в Telegram', force=True)
        with open(path, 'rb') as fh:
            bot.send_document(int(chat_id), fh, caption=f"{('🏷 Маркировки окон' if kind == 'markers' else '📝 ТЗ по окнам')} · {VERSION}")
        return True
    finally:
        _v160_shutil.rmtree(folder, ignore_errors=True)

def _v177_legacy_0323_v160_handle_special_callback(call, resolved: str) -> bool:
    if resolved == 'v160:marker_capture':
        return _v160_begin_capture(call, 'marker')
    if resolved == 'v160:tz_capture':
        return _v160_begin_capture(call, 'tz')
    if resolved in {'v160:export_markers', 'v160:export_tz'}:
        user_id = int(getattr(getattr(call, 'from_user', None), 'id', 0) or 0)
        if not _v160_can_annotate(user_id):
            try:
                bot.answer_callback_query(call.id, 'Только для владельца платформы', show_alert=True)
            except Exception:
                pass
            return True
        chat_id = int(call.message.chat.id)
        kind = 'markers' if resolved.endswith('markers') else 'tz'
        label = 'Маркировки окон' if kind == 'markers' else 'ТЗ по окнам'
        ok, reason = submit_interactive_file_job(chat_id, f'window_{kind}', label, _v160_send_annotation_export, chat_id, kind)
        if not ok:
            send_and_auto_delete(chat_id, f"⏳ {reason or 'Сейчас уже формируется другой файл.'}", 10)
        try:
            bot.answer_callback_query(call.id, 'Формирую файл' if ok else 'Файл уже формируется')
        except Exception:
            pass
        return True
    return False
try:
    _v177_legacy_0323_v160_handle_special_callback.__name__ = '_v160_handle_special_callback'
except Exception:
    pass

def _v160_capture_filter(msg) -> bool:
    try:
        text = str(getattr(msg, 'text', '') or '').strip()
        chat_id = int(msg.chat.id)
        user_id = int(getattr(getattr(msg, 'from_user', None), 'id', 0) or 0)
        if _v160_get_pending(chat_id, user_id):
            return True
        low = text.casefold()
        return low.startswith('/iz-mr') or low.startswith('/iz_mr') or low.startswith('/tz')
    except Exception:
        return False

def _v160_reply_source(msg):
    reply = getattr(msg, 'reply_to_message', None)
    if reply is None:
        return (0, '', {})
    mid = int(getattr(reply, 'message_id', 0) or 0)
    text = str(getattr(reply, 'text', None) or getattr(reply, 'caption', None) or '')
    marker = _v160_marker_from_text(text)
    source = _v160_source_meta(int(msg.chat.id), mid, marker, text) if marker else {}
    return (mid, marker, source)

def _v160_capture_message(msg):
    chat_id = int(msg.chat.id)
    user_id = int(getattr(getattr(msg, 'from_user', None), 'id', 0) or 0)
    if not _v160_can_annotate(user_id):
        return
    text = str(getattr(msg, 'text', '') or '').strip()
    low = text.casefold()
    pending = _v160_get_pending(chat_id, user_id, pop=False)
    command_mode = None
    rest = ''
    if low.startswith('/iz-mr'):
        command_mode = 'marker'
        rest = text[len('/iz-mr'):].strip()
    elif low.startswith('/iz_mr'):
        command_mode = 'marker'
        rest = text[len('/iz_mr'):].strip()
    elif low.startswith('/tz'):
        command_mode = 'tz'
        rest = text[len('/tz'):].strip()
    if command_mode is not None:
        match = _v160_re.match('^([СФПОВсов]\\d{1,6})\\s+(.+)$', rest, flags=_v160_re.IGNORECASE | _v160_re.DOTALL)
        if match:
            marker = str(match.group(1)).upper()
            body = str(match.group(2)).strip()
            _, reply_marker, source = _v160_reply_source(msg)
            if not source or reply_marker != marker:
                source = _v160_source_meta(chat_id, int(getattr(msg, 'message_id', 0) or 0), marker, '')
            if command_mode == 'marker':
                row = _v160_save_marker_name(chat_id, user_id, marker, body, source)
                send_and_auto_delete(chat_id, f"✅ {marker} = {row.get('name')}", 8)
            else:
                _v160_save_tz(chat_id, user_id, marker, body, source)
                send_and_auto_delete(chat_id, f'✅ ТЗ для {marker} сохранено.', 8)
            return
        if not pending:
            _, marker, source = _v160_reply_source(msg)
            if marker:
                _v160_set_pending(chat_id, user_id, command_mode, marker, source)
                pending = _v160_get_pending(chat_id, user_id)
            else:
                send_and_auto_delete(chat_id, 'ℹ️ Используйте кнопки /iz-mr или /tz прямо под нужным окном.', 10)
                return
        send_and_auto_delete(chat_id, f"✍️ Теперь пришлите {('название окна' if command_mode == 'marker' else 'текст ТЗ')} одним сообщением.", 8)
        return
    pending = _v160_get_pending(chat_id, user_id, pop=True)
    if not pending:
        return
    if text.casefold() in {'/cancel', 'отмена'}:
        send_and_auto_delete(chat_id, '❌ Ввод отменён.', 6)
        return
    marker = str(pending.get('marker') or '')
    source = dict(pending.get('source') or {})
    if str(pending.get('mode')) == 'marker':
        row = _v160_save_marker_name(chat_id, user_id, marker, text, source)
        send_and_auto_delete(chat_id, f"✅ Запомнил: {marker} = {row.get('name')}", 8)
    else:
        _v160_save_tz(chat_id, user_id, marker, text, source)
        send_and_auto_delete(chat_id, f'✅ ТЗ для {marker} сохранено.', 8)

def _v160_install_message_capture() -> int:
    try:
        decorator = bot.message_handler(func=_v160_capture_filter, content_types=['text'])
        decorator(_v160_capture_message)
        handlers = getattr(bot, 'message_handlers', None)
        if isinstance(handlers, list) and handlers:
            row = handlers.pop()
            handlers.insert(0, row)
        return 1
    except Exception:
        return 0
_V160_CALLBACK_HANDLERS = 0
_V160_MESSAGE_HANDLERS = _v160_install_message_capture()

def _v177_legacy_0285_v153_validate_restore_gz(gz_path: str) -> tuple[dict, str]:
    folder = _v160_tempfile.mkdtemp(prefix='v160_restore_validate_')
    raw = _v160_os.path.join(folder, 'restore.sqlite3')
    try:
        with _v160_gzip.open(gz_path, 'rb') as fin, open(raw, 'wb') as fout:
            _v160_shutil.copyfileobj(fin, fout, 1024 * 1024)
        conn = _v160_sqlite3.connect(raw)
        try:
            integrity = str(conn.execute('PRAGMA integrity_check').fetchone()[0])
            if integrity.lower() != 'ok':
                raise RuntimeError(f'SQLite integrity_check: {integrity}')
            row = conn.execute("SELECT v FROM meta WHERE kind='v153_export' AND k='manifest'").fetchone()
            if not row:
                raise RuntimeError('manifest v153 not found')
            manifest = _v160_json.loads(row[0])
        finally:
            conn.close()
        if str(manifest.get('kind')) != 'telegram_bot_full_state_v153':
            raise RuntimeError('unknown export kind')
        if int(manifest.get('schema_version') or 0) != int(V153_EXPORT_SCHEMA):
            raise RuntimeError('unsupported export schema')
        export_version = str(manifest.get('bot_version') or '')
        if not export_version.startswith(('bot_v153_', 'bot_v154_', 'bot_v155_', 'bot_v156_', 'bot_v157_', 'bot_v158_', 'bot_v159_', 'bot_v160_')):
            raise RuntimeError(f"unsupported bot version: {export_version or 'missing'}")
        checksum = _v153_db_logical_checksum(raw)
        if checksum != str(manifest.get('checksum') or ''):
            raise RuntimeError('checksum mismatch')
        return (manifest, raw)
    except Exception:
        _v160_shutil.rmtree(folder, ignore_errors=True)
        raise
try:
    _v177_legacy_0285_v153_validate_restore_gz.__name__ = '_v153_validate_restore_gz'
except Exception:
    pass

def _v160_cleanup_legacy_transient_windows() -> None:
    touched = []
    try:
        chats = list((data.get('chats') or {}).items())
    except Exception:
        chats = []
    for cid_s, store in chats:
        try:
            cid = int(cid_s)
        except Exception:
            continue
        if not isinstance(store, dict):
            continue
        mids = set()
        for key in ('command_window_id', '_v160_file_status_msg_id'):
            try:
                mid = int(store.get(key) or 0)
                if mid:
                    mids.add(mid)
            except Exception:
                pass
            if key in store:
                store[key] = None
        if mids:
            touched.append(cid)
            for mid in mids:
                try:
                    bot.delete_message(cid, mid)
                except Exception:
                    pass
                try:
                    unregister_open_window(cid, mid)
                except Exception:
                    pass
    if touched:
        try:
            save_data(data, chat_ids=touched)
        except Exception:
            pass
        for cid in touched:
            try:
                schedule_quick_backup(cid, 0.5)
            except Exception:
                pass
    try:
        bot_journal('v160_transient_window_cleanup', None, f'chats={len(touched)}')
    except Exception:
        pass
_V160_PREV_RUNTIME_MARK_READY = _v177_legacy_0084_runtime_mark_ready

def _v179_legacy_runtime_mark_ready(detail: str=''):
    result = _V160_PREV_RUNTIME_MARK_READY(detail) if callable(_V160_PREV_RUNTIME_MARK_READY) else None
    try:
        _v160_schedule('v160-transient-cleanup', 2.0, _v160_cleanup_legacy_transient_windows)
    except Exception:
        pass
    return result
try:
    _v177_legacy_0007_bot_journal('v160_stability_parallel_windows_annotations_installed', int(OWNER_ID or 0), f'generic_process_ui=off; service_ui=Ф233 unified_file_and_helper; parallel_windows=on; callback_handlers={_V160_CALLBACK_HANDLERS}; annotation_handler={_V160_MESSAGE_HANDLERS}')
except Exception:
    pass
_V179_WINDOW_LAZY_LOCK = _v160_threading.RLock()
_V179_WINDOW_LAZY_LAST = 0.0

def v179_window_registry_lazy_cleanup(force: bool=False):
    global _V179_WINDOW_LAZY_LAST
    now_m = _v160_time.monotonic()
    with _V179_WINDOW_LAZY_LOCK:
        if not force and now_m - float(_V179_WINDOW_LAZY_LAST or 0.0) < 600.0:
            return {'skipped': 'recent'}
        _V179_WINDOW_LAZY_LAST = now_m
    try:
        return cleanup_open_window_registry('v179_lazy')
    except Exception as exc:
        return {'error': str(exc)[:200]}
'v161: deterministic buttons/navigation, parallel-window stability, file-only progress UI, exact window tokens.'
import gzip as _v161_gzip
import json as _v161_json
import os as _v161_os
import re as _v161_re
import secrets as _v161_secrets
import shutil as _v161_shutil
import sqlite3 as _v161_sqlite3
import tempfile as _v161_tempfile
import threading as _v161_threading
import time as _v161_time
try:
    INTERNAL_TIMER_DEFS.pop('helper_process_close', None)
    if 'process_status_refresh' in INTERNAL_TIMER_DEFS:
        INTERNAL_TIMER_DEFS['process_status_refresh']['label'] = '📥📤 Обновление времени / этапа файлов Ф233'
    if 'file_status_close' in INTERNAL_TIMER_DEFS:
        INTERNAL_TIMER_DEFS['file_status_close']['label'] = '📥📤 Закрытие окна файла Ф233 после завершения'
except Exception:
    pass
try:
    if isinstance(WINDOW_MARKER_CLOCK_CODES, set):
        WINDOW_MARKER_CLOCK_CODES.discard('Ф232')
        WINDOW_MARKER_CLOCK_CODES.add('Ф233')
except Exception:
    pass

def _canon_process_visual_status_enabled__001(chat_id: int) -> bool:
    return False

def _canon_v156_process_status_arm__001(chat_id: int | None, hint: str='') -> None:
    """Finalize disabled visual-status state without creating a user-visible helper window."""
    if chat_id is None:
        return
    try:
        cid = int(chat_id)
    except Exception:
        return
    try:
        DELAYED_SCHEDULER.cancel(f'{_V156_PROCESS_STATUS_KEY_PREFIX}{cid}')
    except Exception:
        pass
    try:
        with _V156_PROCESS_UI_LOCK:
            _V156_PROCESS_UI.pop(cid, None)
    except Exception:
        pass

def _canon_v156_process_status_schedule__001(chat_id: int, delay: float) -> None:
    try:
        DELAYED_SCHEDULER.cancel(f'{_V156_PROCESS_STATUS_KEY_PREFIX}{int(chat_id)}')
    except Exception:
        pass

def _canon_v156_process_status_tick__001(chat_id: int) -> None:
    try:
        chat_id = int(chat_id)
    except Exception:
        return
    msg_id = 0
    try:
        with _V156_PROCESS_UI_LOCK:
            row = _V156_PROCESS_UI.pop(chat_id, None) or {}
            msg_id = int(row.get('message_id') or 0)
    except Exception:
        pass
    if msg_id:
        try:
            bot.delete_message(chat_id, msg_id)
        except Exception:
            pass
        try:
            unregister_open_window(chat_id, msg_id)
        except Exception:
            pass
_V161_DELETE_LOCK = _v161_threading.RLock()
_V161_DELETE_STATE = {}

def _v161_delete_already_gone(exc) -> bool:
    low = str(exc or '').casefold()
    return any((x in low for x in ('message to delete not found', 'message not found', 'message_id_invalid', 'message identifier is not specified')))

def _v161_cleanup_deleted_state(chat_id: int, message_id: int) -> None:
    try:
        unregister_open_window(int(chat_id), int(message_id))
    except Exception:
        pass
    try:
        store = get_chat_store(int(chat_id))
        changed = False
        for key in ('_v160_file_status_msg_id', 'command_window_id'):
            try:
                if int(store.get(key) or 0) == int(message_id):
                    store[key] = None
                    changed = True
            except Exception:
                pass
        if changed:
            save_data(data, chat_ids=[int(chat_id)])
            try:
                schedule_quick_backup(int(chat_id), 0.5)
            except Exception:
                pass
    except Exception:
        pass

def _v161_delete_attempt(chat_id: int, message_id: int, retry_key: str, attempt: int=1, max_attempts: int=3) -> None:
    chat_id = int(chat_id)
    message_id = int(message_id)
    attempt = int(attempt)
    ok = False
    err = ''
    try:
        bot.delete_message(chat_id, message_id)
        ok = True
    except Exception as exc:
        err = str(exc)[:260]
        ok = _v161_delete_already_gone(exc)
    if ok:
        _v161_cleanup_deleted_state(chat_id, message_id)
        with _V161_DELETE_LOCK:
            _V161_DELETE_STATE.pop(str(retry_key), None)
        try:
            bot_journal('helper_delete_done', chat_id, f'msg={message_id}; attempt={attempt}')
        except Exception:
            pass
        return
    if attempt >= int(max_attempts):
        with _V161_DELETE_LOCK:
            _V161_DELETE_STATE.pop(str(retry_key), None)
        try:
            bot_journal('helper_delete_failed', chat_id, f'msg={message_id}; attempts={attempt}; error={err}', 'WARN')
        except Exception:
            pass
        return
    wait = 0.8 if attempt == 1 else 2.0
    with _V161_DELETE_LOCK:
        _V161_DELETE_STATE[str(retry_key)] = attempt + 1
    try:
        _v160_schedule(str(retry_key), wait, _v161_delete_attempt, chat_id, message_id, str(retry_key), attempt + 1, max_attempts)
    except Exception:
        t = _v161_threading.Timer(wait, _v161_delete_attempt, args=(chat_id, message_id, str(retry_key), attempt + 1, max_attempts))
        t.daemon = True
        t.start()

def _canon_v160_delete_quiet__001(chat_id: int, message_id: int) -> None:
    key = f'v161:delete:{int(chat_id)}:{int(message_id)}'
    _v161_delete_attempt(int(chat_id), int(message_id), key, 1, 3)

def _canon_v160_schedule_delete__001(chat_id: int, message_id: int, delay: float, prefix: str='delete') -> None:
    key = f'v161:{str(prefix)}:{int(chat_id)}:{int(message_id)}'
    wait = max(0.05, float(delay))
    try:
        _v160_schedule(key, wait, _v161_delete_attempt, int(chat_id), int(message_id), key, 1, 3)
    except Exception:
        t = _v161_threading.Timer(wait, _v161_delete_attempt, args=(int(chat_id), int(message_id), key, 1, 3))
        t.daemon = True
        t.start()
_V161_FORCE_MAIN = _v161_threading.local()
_V161_PREV_BACKUP_WINDOW = _v177_legacy_0240_backup_window_for_owner
_V161_PREV_UPDATE_OR_SEND = _v177_legacy_0229_update_or_send_day_window

def _v161_callback_data() -> str:
    try:
        return str((_current_telegram_update_context() or {}).get('callback_data') or '')
    except Exception:
        return ''

def _v161_explicit_main_action() -> bool:
    if bool(getattr(_V161_FORCE_MAIN, 'value', False)):
        return True
    raw = _v161_callback_data()
    if raw == 'nav_prev' or raw.endswith(':back_main'):
        return True
    if raw.startswith('d:'):
        try:
            cmd = raw.split(':', 2)[2]
        except Exception:
            cmd = ''
        if cmd in {'open', 'prev', 'next', 'today'}:
            return True
    return False

def _v161_window_is_auxiliary(chat_id: int, message_id: int) -> bool:
    if not message_id:
        return False
    try:
        with _V160_ANNOTATION_LOCK:
            meta = dict(_V160_LAST_WINDOW_META.get((int(chat_id), int(message_id))) or {})
        marker = str(meta.get('marker') or '').upper()
        if marker:
            return marker != 'Ф91'
    except Exception:
        pass
    try:
        row = get_registered_open_window(int(chat_id), int(message_id)) or {}
    except Exception:
        row = {}
    if not row:
        return False
    return str(row.get('window_type') or '') != 'main_day'

def _canon_backup_window_for_owner__001(chat_id: int, day_key: str, message_id_override: int | None=None):
    chat_id = int(chat_id)
    day_key = str(day_key)[:10]
    try:
        primary_mid, primary_day = get_primary_main_window(chat_id)
    except Exception:
        primary_mid, primary_day = (None, day_key)
    if primary_mid and message_id_override is None and (str(primary_day)[:10] != day_key):
        try:
            bot_journal('main_refresh_skipped_nonprimary_v189', chat_id, f'requested={day_key}; primary={primary_day}')
        except Exception:
            pass
        return False
    try:
        mid = int(message_id_override or get_active_window_id(chat_id, day_key) or 0)
    except Exception:
        mid = 0
    if mid and (not _v161_explicit_main_action()) and _v161_window_is_auxiliary(chat_id, mid):
        try:
            bot_journal('main_refresh_deferred_aux_window', chat_id, f'msg={mid}; day={day_key}')
        except Exception:
            pass
        return False
    if callable(_V161_PREV_BACKUP_WINDOW):
        return _V161_PREV_BACKUP_WINDOW(chat_id, day_key, message_id_override=message_id_override)
    return False

def _canon_update_or_send_day_window__001(chat_id: int, day_key: str):
    chat_id = int(chat_id)
    day_key = str(day_key)[:10]
    try:
        primary_mid, primary_day = get_primary_main_window(chat_id)
    except Exception:
        primary_mid, primary_day = (None, day_key)
    if primary_mid and str(primary_day)[:10] != day_key:
        try:
            bot_journal('day_window_send_skipped_nonprimary_v189', chat_id, f'requested={day_key}; primary={primary_day}')
        except Exception:
            pass
        return False
    try:
        mid = int(get_active_window_id(chat_id, day_key) or 0)
    except Exception:
        mid = 0
    if mid and (not _v161_explicit_main_action()) and _v161_window_is_auxiliary(chat_id, mid):
        try:
            bot_journal('day_window_refresh_deferred_aux_window', chat_id, f'msg={mid}; day={day_key}')
        except Exception:
            pass
        return False
    if callable(_V161_PREV_UPDATE_OR_SEND):
        return _V161_PREV_UPDATE_OR_SEND(chat_id, day_key)
    return False

def _v177_legacy_0324_v161_edit_retry(chat_id: int, message_id: int, text: str, reply_markup=None, parse_mode=None, purpose: str='ui') -> str:
    last = 'failed'
    for attempt in range(3):
        try:
            result = fast_ui_edit_message_text(int(chat_id), int(message_id), text, reply_markup=reply_markup, parse_mode=parse_mode, purpose=purpose)
        except Exception:
            result = 'failed'
        last = str(result or 'failed')
        if last == 'ok':
            return 'ok'
        if last == 'not_found':
            return 'not_found'
        if attempt < 2:
            _v161_time.sleep(0.15 if last != 'rate_limited' else 0.35 if attempt == 0 else 0.65)
    return last
try:
    _v177_legacy_0324_v161_edit_retry.__name__ = '_v161_edit_retry'
except Exception:
    pass

def _v177_safe_edit_fallback_send(bot_obj, chat_id: int, msg_id: int, raw_action: str, text: str, reply_markup=None, parse_mode=None):
    """Create a replacement window outside the callback thread when the old Telegram message is unusable."""
    started = _v161_time.monotonic()
    try:
        sent = _tg_call_retry(bot_obj.send_message, int(chat_id), text, reply_markup=reply_markup, parse_mode=parse_mode, attempts=1, purpose='safe_edit_fallback_v177')
        try:
            _touch_v98_auto_close_for_callback(int(chat_id), int(sent.message_id), raw_action)
        except Exception:
            pass
        try:
            _v161_register_from_render(int(chat_id), int(sent.message_id), text)
        except Exception:
            pass
    except Exception as exc:
        try:
            log_error(f'safe_edit_v177 async fallback {chat_id}/{msg_id}: {exc}')
        except Exception:
            pass
    finally:
        try:
            stage = globals().get('v177_perf_stage')
            if callable(stage):
                stage('telegram_fallback_send', _v161_time.monotonic() - started)
        except Exception:
            pass

def _canon_safe_edit__001(bot_obj, call, text, reply_markup=None, parse_mode=None):
    prep_started = _v161_time.monotonic()
    chat_id = int(call.message.chat.id)
    msg_id = int(call.message.message_id)
    raw_action = str(getattr(call, 'data', '') or '')
    if raw_action != 'nav_prev' and (not _v161_state_preserving_callback(raw_action)):
        try:
            remember_previous_window(call)
        except Exception:
            pass
    try:
        code = window_code_for_callback(raw_action, owner_chat=is_owner_chat(chat_id))
        if not window_marker_is_declared(raw_action):
            journal_missing_window_marker(raw_action, chat_id, msg_id, text, reply_markup, 'safe_edit_v161')
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
    try:
        stage = globals().get('v177_perf_stage')
        if callable(stage):
            stage('ui_prepare', _v161_time.monotonic() - prep_started)
    except Exception:
        pass
    result = _v161_edit_retry(chat_id, msg_id, text, reply_markup=reply_markup, parse_mode=parse_mode, purpose='safe_edit_v177')
    if result in {'ok', 'scheduled'}:
        try:
            _touch_v98_auto_close_for_callback(chat_id, msg_id, raw_action)
        except Exception:
            pass
        return result
    try:
        pool = globals().get('GENERAL_TASK_POOL')
        key = f'v177-safe-edit-fallback:{chat_id}:{msg_id}'
        queued = bool(pool and pool.submit_unique(key, _v177_safe_edit_fallback_send, bot_obj, chat_id, msg_id, raw_action, text, reply_markup, parse_mode))
        if queued:
            return 'scheduled_fallback'
    except Exception:
        pass
    try:
        bot_obj.answer_callback_query(call.id, 'Telegram не подтвердил обновление. Нажмите ещё раз.', show_alert=False)
    except Exception:
        pass
    return result

def _canon_safe_edit_current_only__001(bot_obj, call, text, reply_markup=None, parse_mode=None):
    chat_id = int(call.message.chat.id)
    msg_id = int(call.message.message_id)
    raw_action = str(getattr(call, 'data', '') or '')
    if raw_action != 'nav_prev' and (not _v161_state_preserving_callback(raw_action)):
        try:
            remember_previous_window(call)
        except Exception:
            pass
    try:
        code = window_code_for_callback(raw_action, owner_chat=is_owner_chat(chat_id))
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
    result = _v161_edit_retry(chat_id, msg_id, text, reply_markup=reply_markup, parse_mode=parse_mode, purpose='safe_edit_current_v177')
    if result not in {'ok', 'scheduled'}:
        try:
            bot_obj.answer_callback_query(call.id, 'Это окно устарело. Откройте его заново.', show_alert=False)
        except Exception:
            pass
    return result

def _v161_register_from_render(chat_id: int, message_id: int, text: str, day_key: str | None=None, code_hint: str='') -> None:
    try:
        marker = _v160_marker_from_text(str(text or ''))
    except Exception:
        marker = ''
    try:
        day = str(day_key or get_chat_store(int(chat_id)).get('current_view_day') or today_key())
        if marker == 'Ф91':
            register_open_window(int(chat_id), int(message_id), 'main_day', code='О1', day_key=day, params={'parallel_allowed': True})
            try:
                set_active_window_id(int(chat_id), day, int(message_id))
            except Exception:
                pass
        else:
            register_open_window(int(chat_id), int(message_id), 'local_fin_view', code=str(code_hint or marker or 'view'), day_key=day, params={'parallel_allowed': True})
    except Exception:
        pass

def _canon_restore_previous_window__001(call) -> bool:
    try:
        chat_id = int(call.message.chat.id)
        message_id = int(call.message.message_id)
    except Exception:
        return False
    key = _window_nav_key(chat_id, message_id)
    snap = _nav_history_peek_v248(key)
    if not snap:
        return False
    markup = _deserialize_inline_keyboard(snap.get('markup'))
    try:
        markup = ensure_previous_back_nav_keyboard(markup, chat_id, message_id)
        markup = ensure_main_back_nav_keyboard(markup, chat_id)
    except Exception:
        pass
    result = _v161_edit_retry(chat_id, message_id, str(snap.get('text') or ''), reply_markup=markup, parse_mode=snap.get('parse_mode'), purpose='nav_prev_restore')
    if result != 'ok':
        try:
            bot_journal('nav_prev_not_committed', chat_id, f'msg={message_id}; result={result}; history_kept=1', 'WARN')
        except Exception:
            pass
        return False
    _nav_history_pop_v248(key)
    _v161_register_from_render(chat_id, message_id, str(snap.get('text') or ''))
    try:
        bot_journal('nav_prev_committed', chat_id, f'msg={message_id}; edit=ok; history_backend=kv_or_local')
    except Exception:
        pass
    return True

def _v161_send_main(chat_id: int, day_key: str) -> int:
    txt, _ = render_day_window(int(chat_id), str(day_key))
    kb = build_main_keyboard(str(day_key), int(chat_id))
    sent = bot.send_message(int(chat_id), txt, reply_markup=kb, parse_mode='HTML')
    mid = int(getattr(sent, 'message_id', 0) or 0)
    if mid:
        set_active_window_id(int(chat_id), str(day_key), mid)
    try:
        schedule_balance_panel_refresh(int(chat_id), 0.05)
    except Exception:
        pass
    return mid

def _canon_return_to_main_window_closing_previous__001(chat_id: int, day_key: str, current_message_id: int | None=None):
    chat_id = int(chat_id)
    day_key = str(day_key)[:10]
    try:
        current_mid = int(current_message_id or 0)
    except Exception:
        current_mid = 0
    try:
        old_mid = int(get_active_window_id(chat_id, day_key) or 0)
    except Exception:
        old_mid = 0
    txt, _ = render_day_window(chat_id, day_key)
    kb = build_main_keyboard(day_key, chat_id)
    if current_mid:
        try:
            cancel_auto_delete_for_message(chat_id, current_mid)
            cancel_fast_ui_edit(chat_id, current_mid)
        except Exception:
            pass
        result = _v161_edit_retry(chat_id, current_mid, txt, reply_markup=kb, parse_mode='HTML', purpose='back_main_instant')
        try:
            bot_journal('back_main_v161', chat_id, f'msg={current_mid}; old={old_mid or None}; result={result}; preserve_parallel=1')
        except Exception:
            pass
        if result == 'ok':
            set_active_window_id(chat_id, day_key, current_mid)
            try:
                schedule_balance_panel_refresh(chat_id, 0.05)
            except Exception:
                pass
            return True
        if result == 'not_found':
            try:
                unregister_open_window(chat_id, current_mid)
            except Exception:
                pass
    if old_mid and old_mid != current_mid:
        try:
            row = get_registered_open_window(chat_id, old_mid) or {}
            if str(row.get('window_type') or '') == 'main_day':
                _V161_FORCE_MAIN.value = True
                try:
                    if callable(_V161_PREV_BACKUP_WINDOW):
                        _V161_PREV_BACKUP_WINDOW(chat_id, day_key, message_id_override=old_mid)
                finally:
                    _V161_FORCE_MAIN.value = False
                set_active_window_id(chat_id, day_key, old_mid)
                return True
        except Exception:
            try:
                _V161_FORCE_MAIN.value = False
            except Exception:
                pass
    try:
        _V161_FORCE_MAIN.value = True
        _v161_send_main(chat_id, day_key)
        return True
    finally:
        _V161_FORCE_MAIN.value = False

def _v161_known_main_candidates(chat_id: int, day_key: str) -> list[int]:
    rows = []
    try:
        with _V146_WINDOW_LOCK:
            for item in (_open_window_registry() or {}).values():
                if not isinstance(item, dict):
                    continue
                try:
                    if int(item.get('chat_id') or 0) == int(chat_id) and str(item.get('window_type') or '') == 'main_day' and (str(item.get('day_key') or '') == str(day_key)):
                        rows.append((str(item.get('updated_at') or ''), int(item.get('message_id') or 0)))
                except Exception:
                    continue
    except Exception:
        pass
    try:
        active = int(get_active_window_id(int(chat_id), str(day_key)) or 0)
        if active:
            rows.append(('9999', active))
    except Exception:
        pass
    seen = set()
    out = []
    for _, mid in sorted(rows, reverse=True):
        if mid and mid not in seen:
            seen.add(mid)
            out.append(mid)
    return out

def _v161_cmd_start(msg):
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
    except Exception as exc:
        try:
            log_error(f'v161 tenant start payload: {exc}')
        except Exception:
            pass
    try:
        chat_id = int(msg.chat.id)
    except Exception:
        return
    try:
        set_total_secret_mode(chat_id, False)
    except Exception:
        pass
    try:
        if is_finance_output_suppressed(chat_id):
            return
    except Exception:
        pass
    try:
        stop_dozvon_for_target(chat_id)
    except Exception:
        pass
    try:
        if guard_non_owner_finance_for_command(msg, {'ok', 'help'}):
            return
    except Exception:
        pass
    try:
        if not require_finance(chat_id):
            return
    except Exception:
        pass
    try:
        day_key = finance_today_key() if is_finance_mode(chat_id) else today_key()
    except Exception:
        day_key = today_key()
    try:
        get_chat_store(chat_id)['current_view_day'] = day_key
    except Exception:
        pass
    txt, _ = render_day_window(chat_id, day_key)
    kb = build_main_keyboard(day_key, chat_id)
    for mid in _v161_known_main_candidates(chat_id, day_key):
        result = _v161_edit_retry(chat_id, mid, txt, reply_markup=kb, parse_mode='HTML', purpose='start_reuse_main')
        if result == 'ok':
            set_active_window_id(chat_id, day_key, mid)
            try:
                schedule_balance_panel_refresh(chat_id, 0.05)
            except Exception:
                pass
            try:
                bot_journal('start_v161_reused', chat_id, f'day={day_key}; msg={mid}')
            except Exception:
                pass
            return
        if result == 'not_found':
            try:
                unregister_open_window(chat_id, mid)
            except Exception:
                pass
    try:
        mid = _v161_send_main(chat_id, day_key)
        try:
            bot_journal('start_v161_created', chat_id, f'day={day_key}; msg={mid}')
        except Exception:
            pass
    except Exception as exc:
        try:
            log_error(f'/start v161 failed {chat_id}: {exc}')
            send_and_auto_delete(chat_id, '⚠️ Не удалось открыть основное окно. Повторите /start.', 8)
        except Exception:
            pass

def _v161_install_start_handler() -> int:
    try:
        bot.message_handler(commands=['start'])(_v161_cmd_start)
        handlers = getattr(bot, 'message_handlers', None)
        if isinstance(handlers, list) and handlers:
            row = handlers.pop()
            handlers.insert(0, row)
        return 1
    except Exception:
        return 0
_V161_SOURCE_CONTEXT = _v161_threading.local()

def _v161_ack(call, text: str | None=None) -> None:
    try:
        bot.answer_callback_query(call.id, text or None, show_alert=False)
    except Exception:
        pass

def _v161_permission_ok(call, action: str) -> bool:
    if action == 'nav_prev' or action.endswith(':back_main'):
        return True
    try:
        fn = globals().get('safety_permission_allowed')
        if callable(fn):
            return bool(fn(int(getattr(getattr(call, 'from_user', None), 'id', 0) or 0), int(call.message.chat.id), action))
    except Exception:
        return False
    return True

def _v161_open_info(call, day_key: str) -> bool:
    chat_id = int(call.message.chat.id)
    mid = int(call.message.message_id)
    action = f'd:{day_key}:info'
    if not _v161_permission_ok(call, action):
        try:
            bot.answer_callback_query(call.id, 'Недостаточно прав', show_alert=True)
        except Exception:
            pass
        return True
    try:
        remember_previous_window(call)
    except Exception:
        pass
    text = window_mark(build_info_text(chat_id), 'Ф54')
    kb = build_info_keyboard(chat_id)
    result = _v161_edit_retry(chat_id, mid, text, reply_markup=kb, purpose='info_v161')
    if result == 'ok':
        try:
            register_open_window(chat_id, mid, 'local_fin_view', code='info', day_key=str(day_key), params={'view_action': 'info', 'parallel_allowed': True})
        except Exception:
            pass
        return True
    try:
        sent = bot.send_message(chat_id, text, reply_markup=kb)
        register_open_window(chat_id, int(sent.message_id), 'local_fin_view', code='info', day_key=str(day_key), params={'view_action': 'info', 'parallel_allowed': True})
    except Exception as exc:
        try:
            log_error(f'info_v161 fallback {chat_id}: {exc}')
        except Exception:
            pass
    return True

def _canon_v161_critical_callback__001(call, resolved: str) -> bool:
    raw = str(resolved or '')
    if raw == 'nav_prev':
        _v161_ack(call)
        if restore_previous_window(call):
            return True
        try:
            chat_id = int(call.message.chat.id)
            mid = int(call.message.message_id)
            day = get_chat_store(chat_id).get('current_view_day') or today_key()
            return_to_main_window_closing_previous(chat_id, day, current_message_id=mid)
            try:
                bot_journal('nav_prev_v161_fallback_main', chat_id, f'msg={mid}')
            except Exception:
                pass
        except Exception:
            pass
        return True
    if raw.startswith('d:'):
        try:
            _, day_key, cmd = raw.split(':', 2)
        except Exception:
            return False
        if cmd == 'back_main':
            _v161_ack(call)
            try:
                return_to_main_window_closing_previous(int(call.message.chat.id), str(day_key), current_message_id=int(call.message.message_id))
            except Exception as exc:
                try:
                    log_error(f'back_main v161: {exc}')
                except Exception:
                    pass
            return True
        if cmd == 'info':
            _v161_ack(call)
            return _v161_open_info(call, str(day_key))
    return False

def _v161_extract_token(text: str) -> str:
    body = str(text or '')
    m = _v161_re.search('(?m)^\\s*[СФПОВсов]\\d{1,6}-\\((W[A-Z0-9]{6,12})\\)(?:\\s*[⏳⏰])?\\s*$', body, flags=_v161_re.IGNORECASE)
    if not m:
        m = _v161_re.search('(?m)^\\s*(W[A-Z0-9]{6,12})\\s*$', body, flags=_v161_re.IGNORECASE)
    return str(m.group(1)).upper() if m else ''
_V161_TOKEN_LOCK = _v161_threading.RLock()
_V161_WINDOW_TOKENS = {}

def _v161_new_token() -> str:
    return 'w' + _v161_secrets.token_hex(4).upper()

def _v161_state_preserving_callback(raw: str) -> bool:
    low = str(raw or '').casefold()
    if low.startswith('v160:marker_capture') or low.startswith('v160:tz_capture'):
        return True
    try:
        fn = globals().get('_v160_is_switch_callback')
        if callable(fn) and fn(raw):
            return True
    except Exception:
        pass
    return any((x in low for x in ('toggle', 'enable', 'disable', ':on', ':off')))

def _v161_tokenize_text(text: str, chat_id: int, message_id: int | None=None) -> tuple[str, str]:
    body = str(text or '')
    try:
        marker = _v160_marker_from_text(body)
    except Exception:
        marker = ''
    if not marker:
        return (body, '')
    # R10: short service/progress windows keep their marker internally but do
    # not expose Ф232/Ф233 or Wxxxxxxxx diagnostic ids to ordinary users.
    if str(marker).upper() in {'Ф232', 'Ф233'}:
        plain = str(body or '')
        plain = _v161_re.sub(r'(?m)^\s*[Фф](?:232|233)(?:-\(W[A-Z0-9]{6,12}\))?(?:\s*[⏳⏰])?\s*$', '', plain, flags=_v161_re.IGNORECASE).strip()
        return (plain or '⏳ Выполняю…', '')
    body = _v161_re.sub('(?m)^\\s*W[A-Z0-9]{6,12}\\s*\\n?', '', body)
    body = _v161_re.sub('(?m)([СФПОВсов]\\d{1,6})-\\(W[A-Z0-9]{6,12}\\)', '\\1', body, flags=_v161_re.IGNORECASE)
    cb = str(getattr(_V161_SOURCE_CONTEXT, 'callback', '') or _v161_callback_data() or '')
    source_token = str(getattr(_V161_SOURCE_CONTEXT, 'token', '') or '')
    key = (int(chat_id), int(message_id or 0))
    with _V161_TOKEN_LOCK:
        existing = str(_V161_WINDOW_TOKENS.get(key) or '') if message_id else ''
        if _v161_state_preserving_callback(cb):
            token = source_token or existing or _v161_new_token()
        elif not cb and existing:
            token = existing
        else:
            token = _v161_new_token()
        token = str(token or _v161_new_token()).upper()
        if message_id:
            _V161_WINDOW_TOKENS[key] = token
    lines = body.rstrip().splitlines()
    marker_re = _v161_re.compile('^\\s*([СФПОВсов]\\d{1,6})(\\s*[⏳⏰])?\\s*$', flags=_v161_re.IGNORECASE)
    for idx in range(len(lines) - 1, -1, -1):
        m = marker_re.match(lines[idx])
        if not m:
            continue
        code = str(m.group(1)).upper()
        glyph = str(m.group(2) or '')
        lines[idx] = f'{code}-({token}){glyph}'
        return ('\n'.join(lines), token)
    return (body, token)
_V161_PREV_SEND = getattr(bot, 'send_message', None)
_V161_PREV_EDIT_TEXT = getattr(bot, 'edit_message_text', None)
_V161_PREV_EDIT_CAPTION = getattr(bot, 'edit_message_caption', None)
if callable(_V161_PREV_SEND):

    def _v161_send_message(chat_id, text, *args, **kwargs):
        decorated, token = _v161_tokenize_text(str(text or ''), int(chat_id), None)
        result = _V161_PREV_SEND(chat_id, decorated, *args, **kwargs)
        try:
            mid = int(getattr(result, 'message_id', 0) or 0)
            if token and mid:
                with _V161_TOKEN_LOCK:
                    _V161_WINDOW_TOKENS[int(chat_id), mid] = token
        except Exception:
            pass
        return result
    bot.send_message = _v161_send_message
if callable(_V161_PREV_EDIT_TEXT):

    def _v161_edit_message_text(text, *args, **kwargs):
        chat_id = int(kwargs.get('chat_id') or 0)
        message_id = int(kwargs.get('message_id') or 0)
        decorated, token = _v161_tokenize_text(str(text or ''), chat_id, message_id)
        result = _V161_PREV_EDIT_TEXT(decorated, *args, **kwargs)
        if token and chat_id and message_id:
            with _V161_TOKEN_LOCK:
                _V161_WINDOW_TOKENS[chat_id, message_id] = token
        return result
    bot.edit_message_text = _v161_edit_message_text
if callable(_V161_PREV_EDIT_CAPTION):

    def _v161_edit_message_caption(*args, **kwargs):
        positional = list(args)
        caption = kwargs.get('caption')
        if caption is None and positional:
            caption = positional.pop(0)
        chat_id = int(kwargs.get('chat_id') or 0)
        message_id = int(kwargs.get('message_id') or 0)
        decorated, token = _v161_tokenize_text(str(caption or ''), chat_id, message_id)
        kwargs['caption'] = decorated
        result = _V161_PREV_EDIT_CAPTION(*positional, **kwargs)
        if token and chat_id and message_id:
            with _V161_TOKEN_LOCK:
                _V161_WINDOW_TOKENS[chat_id, message_id] = token
        return result
    bot.edit_message_caption = _v161_edit_message_caption
_V161_PREV_SOURCE_META = _v177_legacy_0319_v160_source_meta

def _canon_v160_source_meta__001(chat_id: int, message_id: int, marker: str, text: str='') -> dict:
    try:
        meta = dict(_V161_PREV_SOURCE_META(chat_id, message_id, marker, text) or {}) if callable(_V161_PREV_SOURCE_META) else {}
    except Exception:
        meta = {}
    token = _v161_extract_token(text)
    if not token:
        with _V161_TOKEN_LOCK:
            token = str(_V161_WINDOW_TOKENS.get((int(chat_id), int(message_id))) or '')
    meta['window_token'] = token
    meta['version'] = VERSION
    return meta

def _v212_legacy_v161_capture_filter(msg) -> bool:
    try:
        text = str(getattr(msg, 'text', '') or '').strip()
        low = text.casefold()
        chat_id = int(msg.chat.id)
        user_id = int(getattr(getattr(msg, 'from_user', None), 'id', 0) or 0)
        if low.startswith('/iz-mr') or low.startswith('/iz_mr') or low.startswith('/tz'):
            return True
        if low in {'/cancel', 'отмена'} and _v160_get_pending(chat_id, user_id):
            return True
        if text.startswith('/'):
            return False
        return bool(_v160_get_pending(chat_id, user_id))
    except Exception:
        return False

def _v212_legacy_v161_capture_message(msg):
    chat_id = int(msg.chat.id)
    user_id = int(getattr(getattr(msg, 'from_user', None), 'id', 0) or 0)
    if not _v160_can_annotate(user_id):
        return
    text = str(getattr(msg, 'text', '') or '').strip()
    low = text.casefold()
    pending = _v160_get_pending(chat_id, user_id, pop=False)
    mode = None
    rest = ''
    if low.startswith('/iz-mr'):
        mode = 'marker'
        rest = text[len('/iz-mr'):].strip()
    elif low.startswith('/iz_mr'):
        mode = 'marker'
        rest = text[len('/iz_mr'):].strip()
    elif low.startswith('/tz'):
        mode = 'tz'
        rest = text[len('/tz'):].strip()
    if mode is not None:
        m = _v161_re.match('^([СФПОВсов]\\d{1,6})(?:\\s+(w[A-Z0-9]{6,12}))?\\s+(.+)$', rest, flags=_v161_re.IGNORECASE | _v161_re.DOTALL)
        if m:
            marker = str(m.group(1)).upper()
            token = str(m.group(2) or '').upper()
            body = str(m.group(3)).strip()
            _, reply_marker, source = _v160_reply_source(msg)
            if not source or reply_marker != marker:
                source = _v160_source_meta(chat_id, int(getattr(msg, 'message_id', 0) or 0), marker, '')
            if token:
                source['window_token'] = token
            old_pending = _v160_get_pending(chat_id, user_id, pop=True)
            _v207_delete_capture_prompt(chat_id, old_pending)
            if mode == 'marker':
                row = _v160_save_marker_name(chat_id, user_id, marker, body, source)
                send_and_auto_delete(chat_id, f"✅ {marker} {token or ''} = {row.get('name')}", 8)
            else:
                _v160_save_tz(chat_id, user_id, marker, body, source)
                send_and_auto_delete(chat_id, f"✅ ТЗ для {marker} {token or ''} сохранено.", 8)
            return
        if not pending:
            _, marker, source = _v160_reply_source(msg)
            if marker:
                _v160_set_pending(chat_id, user_id, mode, marker, source)
                pending = _v160_get_pending(chat_id, user_id)
            else:
                send_and_auto_delete(chat_id, 'ℹ️ Нажмите /iz-mr или /tz под нужным окном.', 10)
                return
        send_and_auto_delete(chat_id, f"✍️ Теперь пришлите {('название окна' if mode == 'marker' else 'текст ТЗ')} одним сообщением.", 8)
        return
    pending = _v160_get_pending(chat_id, user_id, pop=True)
    if not pending:
        return
    _v207_delete_capture_prompt(chat_id, pending)
    if low in {'/cancel', 'отмена'}:
        send_and_auto_delete(chat_id, '❌ Ввод отменён.', 6)
        return
    marker = str(pending.get('marker') or '')
    source = dict(pending.get('source') or {})
    if str(pending.get('mode')) == 'marker':
        row = _v160_save_marker_name(chat_id, user_id, marker, text, source)
        send_and_auto_delete(chat_id, f"✅ Запомнил: {marker} {source.get('window_token') or ''} = {row.get('name')}", 8)
    else:
        _v160_save_tz(chat_id, user_id, marker, text, source)
        send_and_auto_delete(chat_id, f"✅ ТЗ для {marker} {source.get('window_token') or ''} сохранено.", 8)

def _v161_install_capture() -> int:
    try:
        bot.message_handler(func=_v161_capture_filter, content_types=['text'])(_v161_capture_message)
        handlers = getattr(bot, 'message_handlers', None)
        if isinstance(handlers, list) and handlers:
            row = handlers.pop()
            handlers.insert(0, row)
        return 1
    except Exception:
        return 0
try:
    WINDOW_MARKER_CONSTANTS.update({'v149:rem:merge:*': 'Ф191', 'v149:rem:command:*': 'Ф191', 'v149:rem:item_merge:*': 'Ф191', 'v149:rem:item_complete:*': 'Ф191', 'v149:rem:done:*': 'Ф191', 'v149:rem:history': 'Ф191', 'v160:marker_capture': 'Ф235', 'v160:tz_capture': 'Ф236', 'v160:export_markers': 'Ф237', 'v160:export_tz': 'Ф238', 'journal_name_edit': 'Ф252', 'journal_name_cancel': 'Ф89', 'journal_name_reset': 'Ф89'})
except Exception:
    pass
_V161_PREV_EXPECTED = _v177_legacy_0295_v155_expected_marker

def _canon_v155_expected_marker__001(action: str, chat_id: int) -> str:
    raw = str(action or '')
    if raw == 'nav_prev':
        return ''
    if raw.endswith(':back_main'):
        return 'Ф91'
    if raw.startswith('d:') and raw.endswith(':info'):
        return 'Ф54'
    if raw.startswith('v149:rem:'):
        return 'Ф191'
    if callable(_V161_PREV_EXPECTED):
        try:
            return str(_V161_PREV_EXPECTED(raw, int(chat_id)) or '')
        except Exception:
            pass
    return ''

def _v177_legacy_0286_v153_validate_restore_gz(gz_path: str) -> tuple[dict, str]:
    folder = _v161_tempfile.mkdtemp(prefix='v161_restore_validate_')
    raw = _v161_os.path.join(folder, 'restore.sqlite3')
    try:
        with _v161_gzip.open(gz_path, 'rb') as fin, open(raw, 'wb') as fout:
            _v161_shutil.copyfileobj(fin, fout, 1024 * 1024)
        conn = _v161_sqlite3.connect(raw)
        try:
            integrity = str(conn.execute('PRAGMA integrity_check').fetchone()[0])
            if integrity.lower() != 'ok':
                raise RuntimeError(f'SQLite integrity_check: {integrity}')
            row = conn.execute("SELECT v FROM meta WHERE kind='v153_export' AND k='manifest'").fetchone()
            if not row:
                raise RuntimeError('manifest v153 not found')
            manifest = _v161_json.loads(row[0])
        finally:
            conn.close()
        if str(manifest.get('kind')) != 'telegram_bot_full_state_v153':
            raise RuntimeError('unknown export kind')
        if int(manifest.get('schema_version') or 0) != int(V153_EXPORT_SCHEMA):
            raise RuntimeError('unsupported export schema')
        export_version = str(manifest.get('bot_version') or '')
        if not export_version.startswith(('bot_v153_', 'bot_v154_', 'bot_v155_', 'bot_v156_', 'bot_v157_', 'bot_v158_', 'bot_v159_', 'bot_v160_', 'bot_v161_')):
            raise RuntimeError(f"unsupported bot version: {export_version or 'missing'}")
        if _v153_db_logical_checksum(raw) != str(manifest.get('checksum') or ''):
            raise RuntimeError('checksum mismatch')
        return (manifest, raw)
    except Exception:
        _v161_shutil.rmtree(folder, ignore_errors=True)
        raise
try:
    _v177_legacy_0286_v153_validate_restore_gz.__name__ = '_v153_validate_restore_gz'
except Exception:
    pass
_V161_START_HANDLER = _v161_install_start_handler()
_V161_CALLBACK_HANDLERS = 0
V212_TZ_MAX_CHARS = 200000
V212_TZ_DEBOUNCE_SECONDS = 2.8
_V212_TZ_SESSION_SEQ = 0

def _v212_tz_next_session_id(chat_id: int, user_id: int) -> str:
    global _V212_TZ_SESSION_SEQ
    _V212_TZ_SESSION_SEQ += 1
    return f'tz212-{int(chat_id)}-{int(user_id)}-{int(_v160_time.time() * 1000)}-{_V212_TZ_SESSION_SEQ}'

def _canon_v160_set_pending__001(chat_id: int, user_id: int, mode: str, marker: str, source: dict, prompt_message_id: int=0) -> None:
    now_m = _v160_time.monotonic()
    with _V160_ANNOTATION_LOCK:
        for key, row in list(_V160_ANNOTATION_PENDING.items()):
            if now_m - float((row or {}).get('created_mono') or 0.0) > _V160_PENDING_TTL:
                _V160_ANNOTATION_PENDING.pop(key, None)
        row = {'mode': str(mode), 'marker': str(marker), 'source': _v160_copy.deepcopy(source), 'created_mono': now_m, 'prompt_message_id': int(prompt_message_id or 0)}
        if str(mode) == 'tz':
            row.update({'session_id': _v212_tz_next_session_id(chat_id, user_id), 'generation': 0, 'last_part_mono': 0.0, 'parts': [], 'seen_message_ids': [], 'total_chars': 0, 'overflow': False})
        _V160_ANNOTATION_PENDING[_v160_pending_key(chat_id, user_id)] = row

def _v212_tz_cancel_timer(chat_id: int, user_id: int) -> None:
    try:
        DELAYED_SCHEDULER.cancel(f'v212-tz-finalize:{int(chat_id)}:{int(user_id)}')
    except Exception:
        pass

def _v212_tz_finalize(chat_id: int, user_id: int, session_id: str='', generation: int | None=None, manual: bool=False) -> bool:
    key = _v160_pending_key(chat_id, user_id)
    with _V160_ANNOTATION_LOCK:
        row = _V160_ANNOTATION_PENDING.get(key)
        if not isinstance(row, dict) or str(row.get('mode')) != 'tz':
            return False
        if session_id and str(row.get('session_id') or '') != str(session_id):
            return False
        if generation is not None and int(row.get('generation') or 0) != int(generation):
            return False
        if bool(row.get('overflow')):
            return False
        parts = list(row.get('parts') or [])
        if not parts:
            return False
        marker = str(row.get('marker') or '')
        source = _v160_copy.deepcopy(row.get('source') or {})
        prompt_id = int(row.get('prompt_message_id') or 0)
        sid = str(row.get('session_id') or '')
    unique = {}
    for part in parts:
        try:
            mid = int((part or {}).get('message_id') or 0)
        except Exception:
            mid = 0
        if mid and mid not in unique:
            unique[mid] = str((part or {}).get('text') or '')
    ordered = [unique[mid].rstrip() for mid in sorted(unique)]
    body = '\n'.join(ordered)
    if len(body) > V212_TZ_MAX_CHARS:
        with _V160_ANNOTATION_LOCK:
            cur = _V160_ANNOTATION_PENDING.get(key)
            if isinstance(cur, dict) and str(cur.get('session_id') or '') == sid:
                cur['overflow'] = True
        try:
            send_and_auto_delete(int(chat_id), f'❌ ТЗ не сохранено: {len(body)} символов. Максимум {V212_TZ_MAX_CHARS}. Используйте /cancel и разделите ТЗ.', 20)
        except Exception:
            pass
        return False
    try:
        _v160_save_tz(int(chat_id), int(user_id), marker, body, source)
    except Exception as exc:
        try:
            send_and_auto_delete(int(chat_id), f'❌ ТЗ не сохранено: {exc}', 20)
        except Exception:
            pass
        return False
    with _V160_ANNOTATION_LOCK:
        cur = _V160_ANNOTATION_PENDING.get(key)
        if isinstance(cur, dict) and str(cur.get('session_id') or '') == sid:
            _V160_ANNOTATION_PENDING.pop(key, None)
    _v212_tz_cancel_timer(chat_id, user_id)
    _v207_delete_capture_prompt(int(chat_id), {'prompt_message_id': prompt_id})
    try:
        send_and_auto_delete(int(chat_id), f"✅ ТЗ для {marker} {source.get('window_token') or ''} сохранено.", 8)
    except Exception:
        pass
    try:
        bot_journal('window_tz_session_saved_v212', int(chat_id), f'marker={marker}; parts={len(unique)}; chars={len(body)}; manual={int(bool(manual))}')
    except Exception:
        pass
    return True

def _v212_tz_schedule_finalize(chat_id: int, user_id: int, session_id: str, generation: int) -> None:
    key = f'v212-tz-finalize:{int(chat_id)}:{int(user_id)}'
    try:
        DELAYED_SCHEDULER.cancel(key)
        DELAYED_SCHEDULER.schedule(key, V212_TZ_DEBOUNCE_SECONDS, lambda: _v212_tz_finalize(int(chat_id), int(user_id), str(session_id), int(generation), False))
    except Exception:
        try:
            import threading as _v212_threading
            timer = _v212_threading.Timer(V212_TZ_DEBOUNCE_SECONDS, lambda: _v212_tz_finalize(int(chat_id), int(user_id), str(session_id), int(generation), False))
            timer.daemon = True
            timer.start()
        except Exception:
            pass

def _canon_v212_tz_add_part__001(chat_id: int, user_id: int, message_id: int, text: str) -> bool:
    key = _v160_pending_key(chat_id, user_id)
    now_m = _v160_time.monotonic()
    with _V160_ANNOTATION_LOCK:
        row = _V160_ANNOTATION_PENDING.get(key)
        if not isinstance(row, dict) or str(row.get('mode')) != 'tz':
            return False
        mid = int(message_id or 0)
        seen = set((int(x) for x in row.get('seen_message_ids') or [] if str(x).lstrip('-').isdigit()))
        if mid in seen:
            return True
        raw = str(text or '')
        prospective = int(row.get('total_chars') or 0) + len(raw) + (1 if row.get('parts') else 0)
        if prospective > V212_TZ_MAX_CHARS:
            row['overflow'] = True
            row['generation'] = int(row.get('generation') or 0) + 1
            sid = str(row.get('session_id') or '')
            gen = int(row.get('generation') or 0)
        else:
            row.setdefault('parts', []).append({'message_id': mid, 'text': raw})
            row.setdefault('seen_message_ids', []).append(mid)
            row['total_chars'] = prospective
            row['last_part_mono'] = now_m
            row['generation'] = int(row.get('generation') or 0) + 1
            row['overflow'] = False
            sid = str(row.get('session_id') or '')
            gen = int(row.get('generation') or 0)
    if prospective > V212_TZ_MAX_CHARS:
        _v212_tz_cancel_timer(chat_id, user_id)
        try:
            send_and_auto_delete(int(chat_id), f'❌ Эта часть превысила лимит ТЗ {V212_TZ_MAX_CHARS} символов. Ничего не обрезано и ТЗ пока не сохранено. Используйте /cancel.', 20)
        except Exception:
            pass
        return True
    _v212_tz_schedule_finalize(chat_id, user_id, sid, gen)
    return True

def _v212_tz_cancel(chat_id: int, user_id: int) -> bool:
    pending = _v160_get_pending(chat_id, user_id, pop=True)
    if not pending:
        return False
    _v212_tz_cancel_timer(chat_id, user_id)
    _v207_delete_capture_prompt(chat_id, pending)
    return True

def _v161_capture_filter(msg) -> bool:
    try:
        raw = str(getattr(msg, 'text', '') or '')
        low = raw.strip().casefold()
        chat_id = int(msg.chat.id)
        user_id = int(getattr(getattr(msg, 'from_user', None), 'id', 0) or 0)
        pending = _v160_get_pending(chat_id, user_id)
        if low.startswith('/iz-mr') or low.startswith('/iz_mr') or low.startswith('/tz'):
            return True
        if low in {'/cancel', 'отмена', '/готово', '/done'} and pending:
            return True
        if raw.strip().startswith('/'):
            return False
        return bool(pending)
    except Exception:
        return False

def _v161_capture_message(msg):
    chat_id = int(msg.chat.id)
    user_id = int(getattr(getattr(msg, 'from_user', None), 'id', 0) or 0)
    if not _v160_can_annotate(user_id):
        return
    raw_text = str(getattr(msg, 'text', '') or '')
    stripped = raw_text.strip()
    low = stripped.casefold()
    pending = _v160_get_pending(chat_id, user_id, pop=False)
    if low in {'/cancel', 'отмена'} and pending:
        _v212_tz_cancel(chat_id, user_id) if str(pending.get('mode')) == 'tz' else _v207_delete_capture_prompt(chat_id, _v160_get_pending(chat_id, user_id, pop=True))
        send_and_auto_delete(chat_id, '❌ Ввод отменён.', 6)
        return
    if low in {'/готово', '/done'} and pending and (str(pending.get('mode')) == 'tz'):
        if not _v212_tz_finalize(chat_id, user_id, str(pending.get('session_id') or ''), None, True):
            send_and_auto_delete(chat_id, 'ℹ️ В ТЗ пока нет текста для сохранения.', 6)
        return
    mode = None
    rest = ''
    if low.startswith('/iz-mr'):
        mode = 'marker'
        rest = stripped[len('/iz-mr'):].strip()
    elif low.startswith('/iz_mr'):
        mode = 'marker'
        rest = stripped[len('/iz_mr'):].strip()
    elif low.startswith('/tz'):
        mode = 'tz'
        rest = stripped[len('/tz'):].strip()
    if mode is not None:
        if pending:
            if str(pending.get('mode')) == 'tz':
                _v212_tz_cancel(chat_id, user_id)
            else:
                old = _v160_get_pending(chat_id, user_id, pop=True)
                _v207_delete_capture_prompt(chat_id, old)
            pending = None
        m = _v161_re.match('^([СФПОВсов]\\d{1,6})(?:\\s+(w[A-Z0-9]{6,12}))?(?:\\s+(.+))?$', rest, flags=_v161_re.IGNORECASE | _v161_re.DOTALL)
        if m:
            marker = str(m.group(1)).upper()
            token = str(m.group(2) or '').upper()
            body = str(m.group(3) or '')
            _, reply_marker, source = _v160_reply_source(msg)
            if not source or reply_marker != marker:
                source = _v160_source_meta(chat_id, int(getattr(msg, 'message_id', 0) or 0), marker, '')
            if token:
                source['window_token'] = token
            if mode == 'marker':
                if not body.strip():
                    _v160_set_pending(chat_id, user_id, 'marker', marker, source)
                    send_and_auto_delete(chat_id, '✍️ Теперь пришлите название окна одним сообщением.', 8)
                    return
                row = _v160_save_marker_name(chat_id, user_id, marker, body, source)
                send_and_auto_delete(chat_id, f"✅ {marker} {token or ''} = {row.get('name')}", 8)
                return
            _v160_set_pending(chat_id, user_id, 'tz', marker, source)
            if body:
                _v212_tz_add_part(chat_id, user_id, int(getattr(msg, 'message_id', 0) or 0), body)
            else:
                send_and_auto_delete(chat_id, '✍️ Пришлите текст ТЗ. Можно несколькими сообщениями; /готово — завершить, /cancel — отменить.', 10)
            return
        _, marker, source = _v160_reply_source(msg)
        if marker:
            _v160_set_pending(chat_id, user_id, mode, marker, source)
            send_and_auto_delete(chat_id, f"✍️ Теперь пришлите {('название окна' if mode == 'marker' else 'текст ТЗ; можно несколькими сообщениями')}.", 8)
            return
        send_and_auto_delete(chat_id, 'ℹ️ Нажмите /iz-mr или /tz под нужным окном.', 10)
        return
    pending = _v160_get_pending(chat_id, user_id, pop=False)
    if not pending:
        return
    marker = str(pending.get('marker') or '')
    source = dict(pending.get('source') or {})
    if str(pending.get('mode')) == 'tz':
        if stripped.startswith('/'):
            return
        _v212_tz_add_part(chat_id, user_id, int(getattr(msg, 'message_id', 0) or 0), raw_text)
        return
    pending = _v160_get_pending(chat_id, user_id, pop=True)
    _v207_delete_capture_prompt(chat_id, pending)
    row = _v160_save_marker_name(chat_id, user_id, marker, stripped, source)
    send_and_auto_delete(chat_id, f"✅ Запомнил: {marker} {source.get('window_token') or ''} = {row.get('name')}", 8)
_V161_CAPTURE_HANDLER = _v161_install_capture()
try:
    globals()['_V160_FAST_EDIT_MIN_GAP'] = 0.02
except Exception:
    pass
try:
    _v177_legacy_0007_bot_journal('v161_button_window_stability_installed', int(OWNER_ID or 0), f'start={_V161_START_HANDLER}; callbacks={_V161_CALLBACK_HANDLERS}; capture={_V161_CAPTURE_HANDLER}; F232=off; F233=file-only; delete_retries=3; nav_commit_after_edit=1; parallel=1; token=wXXXXXXXX')
except Exception:
    pass
'v162: hard /start path. Bare /start bypasses legacy message-handler routing and always gives a visible result.'
import gzip as _v162_gzip
import json as _v162_json
import os as _v162_os
import shutil as _v162_shutil
import sqlite3 as _v162_sqlite3
import tempfile as _v162_tempfile
import threading as _v162_threading
_V162_START_LOCK_GUARD = _v162_threading.RLock()
_V162_START_LOCKS = {}

def _v162_start_lock(chat_id: int):
    cid = int(chat_id)
    with _V162_START_LOCK_GUARD:
        lock = _V162_START_LOCKS.get(cid)
        if lock is None:
            lock = _v162_threading.RLock()
            _V162_START_LOCKS[cid] = lock
        return lock

def _v162_is_start_message(msg) -> bool:
    try:
        text = str(getattr(msg, 'text', '') or '').strip()
        if not text:
            return False
        cmd = text.split(None, 1)[0].split('@', 1)[0].casefold()
        return cmd in {'/start', '/старт'}
    except Exception:
        return False

def _v162_start_payload_present(msg) -> bool:
    try:
        text = str(getattr(msg, 'text', '') or '').strip()
        return len(text.split(None, 1)) > 1
    except Exception:
        return False

def _canon_v162_force_start__001(msg) -> bool:
    """Always produce a visible /start result. Never reuse/edit an old main window."""
    try:
        chat_id = int(msg.chat.id)
    except Exception:
        return True
    with _v162_start_lock(chat_id):
        try:
            update_chat_info_from_message(msg)
        except Exception:
            pass
        if _v162_start_payload_present(msg):
            try:
                fn = globals().get('tenant_handle_start_payload')
                if callable(fn) and fn(msg):
                    try:
                        schedule_command_delete(msg)
                    except Exception:
                        pass
                    try:
                        bot_journal('start_v162_payload', chat_id, 'handled=tenant_payload')
                    except Exception:
                        pass
                    return True
            except Exception as exc:
                try:
                    log_error(f'v162 tenant /start payload {chat_id}: {exc}')
                except Exception:
                    pass
        try:
            set_total_secret_mode(chat_id, False)
        except Exception:
            pass
        try:
            stop_dozvon_for_target(chat_id)
        except Exception:
            pass
        try:
            if is_finance_output_suppressed(chat_id) and (not is_owner_chat(chat_id)):
                bot.send_message(chat_id, 'ℹ️ Основное финансовое окно скрыто настройками этого чата.')
                try:
                    schedule_command_delete(msg)
                except Exception:
                    pass
                try:
                    bot_journal('start_v162_visible_block', chat_id, 'reason=finance_output_suppressed')
                except Exception:
                    pass
                return True
        except Exception:
            pass
        try:
            if not is_finance_mode(chat_id):
                bot.send_message(chat_id, '⚙️ Финансовый режим выключен.\nАктивируйте командой /ok')
                try:
                    schedule_command_delete(msg)
                except Exception:
                    pass
                try:
                    bot_journal('start_v162_visible_block', chat_id, 'reason=finance_mode_off')
                except Exception:
                    pass
                return True
        except Exception:
            pass
        try:
            day_key = finance_today_key()
        except Exception:
            try:
                day_key = today_key()
            except Exception:
                day_key = ''
        try:
            store = get_chat_store(chat_id)
            store['current_view_day'] = day_key
        except Exception:
            pass
        try:
            mid = int(_v161_send_main(chat_id, day_key) or 0)
            if not mid:
                raise RuntimeError('send_message returned no message_id')
            try:
                schedule_command_delete(msg)
            except Exception:
                pass
            try:
                bot_journal('start_v162_created', chat_id, f'day={day_key}; msg={mid}; always_new=1')
            except Exception:
                pass
            return True
        except Exception as exc:
            try:
                log_error(f'/start v162 hard path failed {chat_id}: {exc}')
            except Exception:
                pass
            try:
                bot.send_message(chat_id, '⚠️ Команда /start получена, но Telegram не дал открыть Ф91. Ошибка записана в журнал.')
            except Exception:
                pass
            return True
_V162_ORIGINAL_PROCESS_NEW_UPDATES = getattr(bot, 'process_new_updates', None)

def _v162_process_new_updates(updates):
    remaining = []
    for update in list(updates or []):
        msg = getattr(update, 'message', None)
        if msg is not None and _v162_is_start_message(msg):
            try:
                _v162_force_start(msg)
            except Exception as exc:
                try:
                    log_error(f'v162 /start interceptor: {exc}')
                except Exception:
                    pass
            continue
        remaining.append(update)
    if remaining and callable(_V162_ORIGINAL_PROCESS_NEW_UPDATES):
        return _V162_ORIGINAL_PROCESS_NEW_UPDATES(remaining)
    return None
if callable(_V162_ORIGINAL_PROCESS_NEW_UPDATES):
    bot.process_new_updates = _v162_process_new_updates

def _v177_legacy_0287_v153_validate_restore_gz(gz_path: str) -> tuple[dict, str]:
    folder = _v162_tempfile.mkdtemp(prefix='v162_restore_validate_')
    raw = _v162_os.path.join(folder, 'restore.sqlite3')
    try:
        with _v162_gzip.open(gz_path, 'rb') as fin, open(raw, 'wb') as fout:
            _v162_shutil.copyfileobj(fin, fout, 1024 * 1024)
        conn = _v162_sqlite3.connect(raw)
        try:
            integrity = str(conn.execute('PRAGMA integrity_check').fetchone()[0])
            if integrity.lower() != 'ok':
                raise RuntimeError(f'SQLite integrity_check: {integrity}')
            row = conn.execute("SELECT v FROM meta WHERE kind='v153_export' AND k='manifest'").fetchone()
            if not row:
                raise RuntimeError('manifest v153 not found')
            manifest = _v162_json.loads(row[0])
        finally:
            conn.close()
        if str(manifest.get('kind')) != 'telegram_bot_full_state_v153':
            raise RuntimeError('unknown export kind')
        if int(manifest.get('schema_version') or 0) != int(V153_EXPORT_SCHEMA):
            raise RuntimeError('unsupported export schema')
        export_version = str(manifest.get('bot_version') or '')
        if not export_version.startswith(('bot_v153_', 'bot_v154_', 'bot_v155_', 'bot_v156_', 'bot_v157_', 'bot_v158_', 'bot_v159_', 'bot_v160_', 'bot_v161_', 'bot_v162_')):
            raise RuntimeError(f"unsupported bot version: {export_version or 'missing'}")
        if _v153_db_logical_checksum(raw) != str(manifest.get('checksum') or ''):
            raise RuntimeError('checksum mismatch')
        return (manifest, raw)
    except Exception:
        _v162_shutil.rmtree(folder, ignore_errors=True)
        raise
try:
    _v177_legacy_0287_v153_validate_restore_gz.__name__ = '_v153_validate_restore_gz'
except Exception:
    pass
try:
    _v177_legacy_0007_bot_journal('v162_start_hard_fix_installed', int(OWNER_ID or 0), 'process_new_updates_intercept=1; start_always_new_f91=1; silent_returns=0')
except Exception:
    pass
try:
    WINDOW_MARKER_CLOCK_CODES.discard('Ф234')
    WINDOW_MARKER_CLOCK_CODES.add('Ф233')
except Exception:
    pass
# v262
