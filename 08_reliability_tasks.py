# v262

# --- ИСТОЧНИК: 74_ui_reliability_runtime.py ---
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
_V159_TIMER_PURPOSE_MARKERS = {'internal_timers': 'Ф183', 'internal_timer_pick': 'Ф184', 'internal_timer_digit': 'Ф185', 'internal_timer_unit': 'Ф186', 'internal_timer_backspace': 'Ф187', 'internal_timer_clear': 'Ф188', 'internal_timer_apply': 'Ф189', 'internal_timer_back_info': 'Ф54'}

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
_V160_CALLBACK_LOCK = _v160_threading.RLock()
_V160_CALLBACK_IDS = {}

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
_V199_SERVICE_FAST_CACHE = {}  # R34: transient service ids are process-local; never take data_lock before ordinary render.

def _v199_service_message_id(chat_id: int) -> int:
    """R34 hot-path: transient F233 ownership is RAM-only.

    Reading persistent chat state here used to put get_chat_store/data_lock in front
    of Telegram editMessageText.  A service message never needs to survive a process
    restart, so an absent RAM entry simply means "create a fresh service window".
    """
    try: return int(_V199_SERVICE_FAST_CACHE.get(int(chat_id)) or 0)
    except Exception: return 0

def _v199_clear_service_message(chat_id: int, message_id: int) -> None:
    try:
        if int(_V199_SERVICE_FAST_CACHE.get(int(chat_id)) or 0) == int(message_id): _V199_SERVICE_FAST_CACHE.pop(int(chat_id), None)
    except Exception:
        pass
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
        _V199_SERVICE_FAST_CACHE[chat_id] = mid
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

def _r22_render_stage(payload: dict, stage: str, elapsed: float=0.0, result: str='') -> None:
    """Record render timings without borrowing callback-thread locals."""
    try:
        action = str(payload.get('_r22_action') or '')[:120]
        rows = globals().get('_V177_PERF_STAGES')
        if rows is not None:
            rows.append({'ts': _v160_time.time(), 'action': action, 'stage': str(stage or '')[:80], 'elapsed': max(0.0, float(elapsed or 0.0))})
    except Exception:
        pass
    if stage == 'telegram_render_done':
        try:
            _msg = f"FASTBTN render chat={int(payload.get('chat_id') or 0)} msg={int(payload.get('message_id') or 0)} action={str(payload.get('_r22_action') or '')[:120]} purpose={str(payload.get('purpose') or '')[:80]} queue={float(payload.get('_r22_queue_wait') or 0.0):.3f}s telegram={float(elapsed or 0.0):.3f}s result={result}"
            log_info(_msg)
            bot_journal('button_chain_render', int(payload.get('chat_id') or 0),
                        f"action={str(payload.get('_r22_action') or '')[:120]}; purpose={str(payload.get('purpose') or '')[:80]}; queue_wait={float(payload.get('_r22_queue_wait') or 0.0):.3f}s; telegram={float(elapsed or 0.0):.3f}s; result={result}")
        except Exception:
            pass


def _r22_execute_window_render(payload: dict) -> None:
    """Actual Telegram network stage; R25 emits per-update render/TG timings."""
    _r25_uid = str(payload.get('_r25_update_id') or '')
    _r25_action = str(payload.get('_r22_action') or payload.get('_r25_action') or '')[:180]
    try:
        log_info(f'BTNTRACE update={_r25_uid or "-"} chat={payload.get("chat_id")} action={_r25_action} stage=RENDER_WORKER_START')
        r52_diag('RENDER_WORKER_ENTER', update=_r25_uid or '-', chat=payload.get('chat_id'), msg=payload.get('message_id'), action=_r25_action, purpose=payload.get('purpose'), render_pool=WINDOW_RENDER_TASK_POOL.stats())
    except Exception:
        pass
    try:
        payload['_r22_queue_wait'] = max(0.0, _v160_time.monotonic() - float(payload.get('_r22_enqueued_mono') or _v160_time.monotonic()))
        _r22_render_stage(payload, 'render_queue_wait', payload['_r22_queue_wait'])
    except Exception:
        pass
    try:
        apply_fn = globals().get('window_diag_fast_ui_apply')
        if callable(apply_fn):
            apply_fn(payload, delayed=bool(payload.get('_r22_queue_wait', 0.0) > 0.01))
    except Exception:
        pass
    started = _v160_time.monotonic()
    result = 'failed'
    try:
        try: log_info(f'BTNTRACE update={_r25_uid or "-"} chat={payload.get("chat_id")} action={_r25_action} stage=TELEGRAM_EDIT_START')
        except Exception: pass
        result = str(_perform_fast_ui_edit(payload) or 'failed')
    except Exception as exc:
        result = 'failed'
        try:
            log_error(f'R22 WINDOW RENDER FAILED chat={payload.get("chat_id")} msg={payload.get("message_id")}: {exc}')
        except Exception:
            pass
    elapsed = max(0.0, _v160_time.monotonic() - started)
    try:
        log_info(f'BTNTRACE update={_r25_uid or "-"} chat={payload.get("chat_id")} action={_r25_action} stage=TELEGRAM_EDIT_DONE elapsed={elapsed:.3f}s detail={result}')
        r52_diag('RENDER_WORKER_EXIT', update=_r25_uid or '-', chat=payload.get('chat_id'), msg=payload.get('message_id'), action=_r25_action, purpose=payload.get('purpose'), elapsed=elapsed, result=result, queue_wait=float(payload.get('_r22_queue_wait') or 0.0), render_pool=WINDOW_RENDER_TASK_POOL.stats())
    except Exception: pass
    _r22_render_stage(payload, 'telegram_render_done', elapsed, result)
    # Preserve the old safe_edit recovery semantics, but recovery is also outside
    # the callback worker. It is intentionally only for unusable Telegram messages.
    if result in {'not_found', 'failed'} and str(payload.get('purpose') or '').startswith('safe_edit'):
        try:
            fallback = globals().get('_v177_safe_edit_fallback_send')
            if callable(fallback):
                fallback(bot, int(payload.get('chat_id')), int(payload.get('message_id')), str(payload.get('_r22_action') or ''),
                         str(payload.get('text') or ''), payload.get('reply_markup'), payload.get('parse_mode'))
        except Exception:
            pass


def _canon_fast_ui_edit_message_text__001(chat_id: int, message_id: int, text: str, reply_markup=None, parse_mode=None, purpose: str='fast_ui') -> str:
    """R49 root-fix: enqueue latest window render; callback never waits for Telegram RTT."""
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
        ctx_fn = globals().get('r25_trace_current')
        ctx = ctx_fn() if callable(ctx_fn) else {}
        payload['_r25_update_id'] = str((ctx or {}).get('update_id') or '')
        payload['_r22_action'] = str((ctx or {}).get('action') or '')[:180]
    except Exception:
        payload['_r25_update_id'] = ''
        payload['_r22_action'] = ''
    payload['_r22_enqueued_mono'] = _v160_time.monotonic()
    key = f'{chat_id}:{message_id}'
    try:
        r52_diag('RENDER_SUBMIT_START', update=payload.get('_r25_update_id') or '-', chat=chat_id, msg=message_id, action=payload.get('_r22_action') or '', purpose=purpose, key=key, text_len=len(str(text or '')), render_pool=WINDOW_RENDER_TASK_POOL.stats())
        seq = WINDOW_RENDER_TASK_POOL.submit_latest(key, _r22_execute_window_render, payload)
        r52_diag('RENDER_SUBMIT_DONE', update=payload.get('_r25_update_id') or '-', chat=chat_id, msg=message_id, action=payload.get('_r22_action') or '', purpose=purpose, key=key, seq=seq, render_pool=WINDOW_RENDER_TASK_POOL.stats())
    except Exception as exc:
        try: log_error(f'R49 WINDOW RENDER ENQUEUE FAILED chat={chat_id} msg={message_id}: {exc}')
        except Exception: pass
        return 'failed'
    if not seq:
        try: log_error(f'R49 WINDOW RENDER QUEUE FULL chat={chat_id} msg={message_id}')
        except Exception: pass
        return 'failed'
    try:
        st = globals().get('r25_trace_stage')
        if callable(st): st('RENDER_ENQUEUED', 0.0, f'seq={seq}')
    except Exception:
        pass
    return 'scheduled'

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
        if result in {'ok', 'scheduled'}:
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
# FINALIZED: v160 markup/meta logic is called by 89_callback_final.py; no bot override here.

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
    # R28 direct renderer normally returns 'ok'. Keep 'scheduled' accepted only for
    # compatibility with any retained legacy delayed path; both mean navigation committed.
    if result not in {'ok', 'scheduled'}:
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
        if result in {'ok', 'scheduled'}:
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
        if result in {'ok', 'scheduled'}:
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
    if result in {'ok', 'scheduled'}:
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
# FINALIZED: v161 tokenization is called by 89_callback_final.py; no bot override here.
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
# FINALIZED: /start interception is executed by the single dispatcher in 89_callback_final.py.

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

# --- ИСТОЧНИК: 75_platform_features_runtime.py ---
"""v163: priority /start, per-window navigation lanes, fast callback ACK, export reliability, TZ window fixes."""
import calendar as _v163_calendar
import contextlib as _v163_contextlib
import threading as _v163_threading
import time as _v163_time
START_UI_TASK_POOL = KeyedTaskPool('start-ui', _env_int('START_UI_WORKERS', 1, 1, 4), _env_int('START_UI_MAX_PENDING', 120, 20, 600))
WINDOW_UI_TASK_POOL = UI_TASK_POOL
_V163_WINDOW_EXEC_LOCK_GUARD = _v163_threading.RLock()
_V163_WINDOW_EXEC_LOCKS = {}
_V163_START_EXEC_LOCK_GUARD = _v163_threading.RLock()
_V163_START_EXEC_LOCKS = {}

def _v163_lock_for(table: dict, guard, key):
    with guard:
        lock = table.get(key)
        if lock is None:
            lock = _v163_threading.RLock()
            table[key] = lock
        return lock

def _v163_start_payload(payload: dict) -> bool:
    try:
        msg = (payload or {}).get('message') or {}
        text = str(msg.get('text') or '').strip()
        if not text:
            return False
        cmd = text.split(None, 1)[0].split('@', 1)[0].casefold()
        return cmd in {'/start', '/старт'}
    except Exception:
        return False

def _v163_callback_parts(payload: dict):
    try:
        cq = (payload or {}).get('callback_query') or {}
        msg = cq.get('message') or {}
        chat = msg.get('chat') or {}
        return (str(cq.get('data') or ''), int(chat.get('id') or 0), int(msg.get('message_id') or 0))
    except Exception:
        return ('', 0, 0)

def _v163_is_switch_callback(raw: str) -> bool:
    low = str(raw or '').casefold()
    try:
        fn = globals().get('_v160_is_switch_callback')
        if callable(fn) and fn(raw):
            return True
    except Exception:
        pass
    return any((x in low for x in ('toggle', ':on', ':off', 'enable', 'disable')))

def _v163_is_navigation_callback(raw: str) -> bool:
    """Only UI/navigation actions are allowed to bypass the chat-wide business lock."""
    raw = str(raw or '')
    low = raw.casefold()
    if _v163_is_switch_callback(raw):
        return False
    if raw in {'nav_prev', 'info_close', 'journal_back', 'journal_chats_back', 'itmr_back_info', 'fw_back_src', 'process_center', 'problem_tasks'}:
        return True
    if low.startswith('d:'):
        try:
            cmd = raw.split(':', 2)[2].casefold()
        except Exception:
            cmd = ''
        if cmd in {'back_main', 'info'}:
            return True
    if 'back' in low or low.endswith('_close') or low.startswith('close_'):
        dangerous = ('delete', 'remove', 'confirm', 'save', 'apply', 'send', 'pay', 'expense', 'income')
        if not any((x in low for x in dangerous)):
            return True
    return False

def _v177_legacy_0325_v163_webhook_select_lane(payload: dict, update_type: str, update_key):
    """Called by 99_web_runtime at request time after every module is loaded."""
    if str(update_type) == 'message' and _v163_start_payload(payload):
        chat_id = _extract_update_chat_id(payload)
        return (START_UI_TASK_POOL, f'start:{(chat_id if chat_id is not None else update_key)}')
    if str(update_type) == 'callback_query':
        raw, chat_id, message_id = _v163_callback_parts(payload)
        if _v163_is_navigation_callback(raw) and chat_id and message_id:
            return (WINDOW_UI_TASK_POOL, f'window:{chat_id}:{message_id}')
        return (UI_TASK_POOL, f'ui:{(chat_id if chat_id else update_key)}')
    return (WEBHOOK_TASK_POOL, update_key)
try:
    _v177_legacy_0325_v163_webhook_select_lane.__name__ = 'v163_webhook_select_lane'
except Exception:
    pass

def _v177_legacy_0074_execute_telegram_payload(payload: dict, update_id=None, update_chat_id=None, update_type: str='other'):
    update = telebot.types.Update.de_json(payload)
    if update_chat_id is None:
        update_chat_id = _extract_update_chat_id(payload) if isinstance(payload, dict) else None
    previous_ctx = getattr(_TELEGRAM_UPDATE_CONTEXT, 'value', None)
    critical_callback_target = _durable_callback_target_chat(payload) if isinstance(payload, dict) else None
    callback_data = ''
    source_message_id = None
    source_user_id = None
    try:
        if isinstance(payload, dict):
            callback = payload.get('callback_query') or {}
            if isinstance(callback, dict):
                callback_data = str(callback.get('data') or '')
                source_user_id = (callback.get('from') or {}).get('id') if isinstance(callback.get('from'), dict) else None
                callback_message = callback.get('message') or {}
                if isinstance(callback_message, dict):
                    source_message_id = callback_message.get('message_id')
            if source_message_id is None:
                message_payload = payload.get('message') or payload.get('edited_message') or payload.get('channel_post') or payload.get('edited_channel_post') or {}
                if isinstance(message_payload, dict):
                    source_message_id = message_payload.get('message_id')
                    source_user_id = source_user_id or ((message_payload.get('from') or {}).get('id') if isinstance(message_payload.get('from'), dict) else None)
    except Exception:
        callback_data = ''
    _TELEGRAM_UPDATE_CONTEXT.value = {'update_id': update_id, 'chat_id': update_chat_id, 'update_type': str(update_type or 'other'), 'callback_data': callback_data, 'message_id': source_message_id, 'user_id': source_user_id, 'critical_callback': critical_callback_target is not None, 'critical_callback_target': critical_callback_target, 'deferred_quick_chats': set()}
    execution_ctx = {}
    try:
        with state_chat_context(update_chat_id):
            if update_chat_id is None:
                lock_ctx = _v163_contextlib.nullcontext()
            elif str(update_type) == 'message' and _v163_start_payload(payload):
                lock_ctx = _v163_lock_for(_V163_START_EXEC_LOCKS, _V163_START_EXEC_LOCK_GUARD, int(update_chat_id))
            elif str(update_type) == 'callback_query' and _v163_is_navigation_callback(callback_data) and source_message_id:
                lock_ctx = _v163_lock_for(_V163_WINDOW_EXEC_LOCKS, _V163_WINDOW_EXEC_LOCK_GUARD, (int(update_chat_id), int(source_message_id)))
            else:
                lock_ctx = telegram_execution_chat_lock(int(update_chat_id))
            with lock_ctx:
                bot.process_new_updates([update])
        execution_ctx = _durable_execution_context_snapshot()
        try:
            fn = globals().get('_v150_store_receipt')
            if callable(fn):
                fn(payload)
        except Exception as exc:
            try:
                log_error(f'v163 command receipt: {exc}')
            except Exception:
                pass
    finally:
        if not execution_ctx:
            execution_ctx = _durable_execution_context_snapshot()
        if previous_ctx is None:
            try:
                delattr(_TELEGRAM_UPDATE_CONTEXT, 'value')
            except Exception:
                pass
        else:
            _TELEGRAM_UPDATE_CONTEXT.value = previous_ctx
    return execution_ctx
try:
    _v177_legacy_0074_execute_telegram_payload.__name__ = '_execute_telegram_payload'
except Exception:
    pass

def _v163_export_day_label(chat_id: int | None, day_key: str, day_num: int) -> str:
    if str(day_key) == str(today_key()):
        return f'📅{int(day_num)}'
    try:
        if _v154_day_has_expense(chat_id, day_key):
            return f'📝{int(day_num)}'
    except Exception:
        pass
    return str(int(day_num))

def _canon_export_calendar_start_keyboard__001(view_year: int, view_month: int, return_day_key: str, chat_id: int | None=None):
    kb = types.InlineKeyboardMarkup(row_width=7)
    last_day = _v163_calendar.monthrange(int(view_year), int(view_month))[1]
    buttons = []
    for day_num in range(1, last_day + 1):
        day_key = _date_key_from_ymd(view_year, view_month, day_num)
        buttons.append(IB(_v163_export_day_label(chat_id, day_key, day_num), callback_data=export_callback(f'exp_pick_set_start:{view_year}:{view_month}:{day_num}:{return_day_key}')))
    for idx in range(0, len(buttons), 7):
        kb.row(*buttons[idx:idx + 7])
    prev_y, prev_m = _shift_month(view_year, view_month, -1)
    next_y, next_m = _shift_month(view_year, view_month, 1)
    kb.row(IB('⬅️ Месяц', callback_data=export_callback(f'exp_pick_start:{prev_y}:{prev_m}:{return_day_key}')), IB(f'{russian_month_name(view_month)} {view_year}', callback_data='none'), IB('Месяц ➡️', callback_data=export_callback(f'exp_pick_start:{next_y}:{next_m}:{return_day_key}')))
    kb.row(IB('◀️ Год', callback_data=export_callback(f'exp_pick_start:{view_year - 1}:{view_month}:{return_day_key}')), IB(str(view_year), callback_data='none'), IB('Год ▶️', callback_data=export_callback(f'exp_pick_start:{view_year + 1}:{view_month}:{return_day_key}')))
    kb.row(IB('🔙 Назад в CSV / Excel', callback_data=f'd:{return_day_key}:csv_all'))
    return kb

def _canon_export_end_calendar_keyboard__001(start_key: str, start_rid: int, view_year: int, view_month: int, return_day_key: str, chat_id: int | None=None):
    kb = types.InlineKeyboardMarkup(row_width=7)
    last_day = _v163_calendar.monthrange(int(view_year), int(view_month))[1]
    buttons = []
    for day_num in range(1, last_day + 1):
        day_key = _date_key_from_ymd(view_year, view_month, day_num)
        if day_key < start_key:
            buttons.append(IB('·', callback_data='none'))
        else:
            buttons.append(IB(_v163_export_day_label(chat_id, day_key, day_num), callback_data=export_callback(f'exp_pick_set_end:{start_key}:{int(start_rid)}:{view_year}:{view_month}:{day_num}:{return_day_key}')))
    for idx in range(0, len(buttons), 7):
        kb.row(*buttons[idx:idx + 7])
    prev_y, prev_m = _shift_month(view_year, view_month, -1)
    next_y, next_m = _shift_month(view_year, view_month, 1)
    nav = []
    if f'{prev_y:04d}-{prev_m:02d}' >= start_key[:7]:
        nav.append(IB('⬅️ Месяц', callback_data=export_callback(f'exp_pick_end:{start_key}:{int(start_rid)}:{prev_y}:{prev_m}:{return_day_key}')))
    else:
        nav.append(IB(' ', callback_data='none'))
    nav.append(IB(f'{russian_month_name(view_month)} {view_year}', callback_data='none'))
    nav.append(IB('Месяц ➡️', callback_data=export_callback(f'exp_pick_end:{start_key}:{int(start_rid)}:{next_y}:{next_m}:{return_day_key}')))
    kb.row(*nav)
    kb.row(IB('◀️ Год', callback_data=export_callback(f'exp_pick_end:{start_key}:{int(start_rid)}:{view_year - 1}:{view_month}:{return_day_key}')), IB(str(view_year), callback_data='none'), IB('Год ▶️', callback_data=export_callback(f'exp_pick_end:{start_key}:{int(start_rid)}:{view_year + 1}:{view_month}:{return_day_key}')))
    td = str(today_key())
    if td >= str(start_key):
        kb.row(IB(f'⏹ До конца текущего дня · {fmt_date_ddmmyy(td)}', callback_data=export_callback(f'v163_exp_end_today:{start_key}:{int(start_rid)}:{return_day_key}')))
    start_dt = datetime.strptime(start_key, '%Y-%m-%d')
    kb.row(IB('🔙 Изменить начало', callback_data=export_callback(f'exp_pick_set_start:{start_dt.year}:{start_dt.month}:{start_dt.day}:{return_day_key}')))
    return kb
try:
    WINDOW_ACTION_CODES.update({'v163_exp_end_today:*': 'Ф116'})
except Exception:
    pass

def _v163_exact_today_callback(call):
    raw = str(getattr(call, 'data', '') or '')
    try:
        resolver = globals().get('resolve_short_callback')
        if callable(resolver):
            raw = str(resolver(raw) or raw)
    except Exception:
        pass
    if not raw.startswith('v163_exp_end_today:'):
        return
    try:
        _, start_key, start_rid, return_day_key = raw.split(':', 3)
        chat_id = int(call.message.chat.id)
        end_key = str(today_key())
        if end_key < str(start_key):
            try:
                bot.answer_callback_query(call.id, 'Текущий день раньше начала периода', show_alert=True)
            except Exception:
                pass
            return
        try:
            bot.answer_callback_query(call.id)
        except Exception:
            pass
        store = get_chat_store(chat_id)
        text = f'🎯 Точный период выбран\n\n▶️ {exact_boundary_text(store, start_key, int(start_rid), True)}\n⏹ {exact_boundary_text(store, end_key, 0, False)}\n\nВыберите формат файла:'
        safe_edit(bot, call, text, reply_markup=_export_format_keyboard(start_key, int(start_rid), end_key, 0, return_day_key))
    except Exception as exc:
        try:
            log_error(f'v163 exact today: {exc}')
        except Exception:
            pass

def _v163_exact_today_filter(call) -> bool:
    raw = str(getattr(call, 'data', '') or '')
    try:
        resolver = globals().get('resolve_short_callback')
        if callable(resolver):
            raw = str(resolver(raw) or raw)
    except Exception:
        pass
    return raw.startswith('v163_exp_end_today:')

def _v163_forward_scope_ids() -> list[int]:
    ids = set()
    try:
        tid = str(tenant_current_id())
    except Exception:
        tid = 'platform'
    try:
        for cid in tenant_chat_ids(tid) or []:
            ids.add(int(cid))
    except Exception:
        pass
    try:
        for cid in (data.get('chats', {}) or {}).keys():
            ic = int(cid)
            if str(tenant_id_for_chat(ic, create=False)) == tid:
                ids.add(ic)
    except Exception:
        pass
    try:
        scope = owner_scope_id(current_state_chat_id())
        known = get_chat_store(int(scope)).get('known_chats') or {}
        for cid in known.keys():
            ic = int(cid)
            if str(tenant_id_for_chat(ic, create=False)) == tid:
                ids.add(ic)
    except Exception:
        pass
    try:
        for src, dsts in (data.get('forward_rules', {}) or {}).items():
            for cid in [src] + list((dsts or {}).keys()):
                ic = int(cid)
                if str(tenant_id_for_chat(ic, create=False)) == tid:
                    ids.add(ic)
    except Exception:
        pass
    try:
        root = int(owner_scope_id(current_state_chat_id()))
        if root:
            ids.add(root)
    except Exception:
        pass
    return sorted(ids, key=lambda cid: get_chat_display_name(cid).casefold())

def _v177_legacy_0181_collect_forward_picker_items(include_owner: bool=True, include_removed: bool=False):
    items = []
    owner_item = None
    try:
        root_id = int(owner_scope_id(current_state_chat_id()))
    except Exception:
        root_id = int(OWNER_ID or 0)
    for cid in _v163_forward_scope_ids():
        try:
            if not include_removed and is_chat_bot_removed(int(cid)):
                continue
        except Exception:
            pass
        title = get_chat_display_name(int(cid)) or f'Чат {cid}'
        if root_id and int(cid) == root_id:
            owner_item = (int(cid), title)
        else:
            items.append((int(cid), title))
    if include_owner and root_id and (owner_item is None):
        owner_item = (root_id, get_chat_display_name(root_id) or f'Чат {root_id}')
    if not include_owner:
        owner_item = None
    return (items, owner_item)
try:
    _v177_legacy_0181_collect_forward_picker_items.__name__ = '_collect_forward_picker_items'
except Exception:
    pass
def _v163_transient_send_error(exc) -> bool:
    low = str(exc or '').casefold()
    return any((x in low for x in ('too many requests', 'retry after', 'internal server error', 'bad gateway', 'service unavailable', 'connection reset', 'remote disconnected', 'temporarily unavailable')))
# FINALIZED: send_document retry/accounting is called by 89_callback_final.py; no bot override here.
_V163_BASE_FILE_RUNNER = _v177_legacy_0015_interactive_file_job_runner

def file_job_mark_external_delivery(kind: str, reference: str='') -> bool:
    """Mark a successful non-document export (Google Sheets/Drive) in current file job."""
    try:
        ctx = getattr(_FILE_JOB_CONTEXT, 'value', None)
        if not isinstance(ctx, dict):
            return False
        key = str(ctx.get('key') or '')
        with _FILE_JOB_LOCK:
            st = _FILE_JOB_STATE.get(key)
            if not isinstance(st, dict):
                return False
            st['external_deliveries_sent'] = int(st.get('external_deliveries_sent') or 0) + 1
            st['external_delivery_kind'] = str(kind or 'external')[:40]
            st['external_delivery_reference'] = str(reference or '')[:500]
        return True
    except Exception:
        return False

def _canon_interactive_file_job_runner__001(job_meta: dict, func, args, kwargs):
    key = str(job_meta.get('key') or _INTERACTIVE_FILE_JOB_KEY)
    previous = getattr(_FILE_JOB_CONTEXT, 'value', None)
    _FILE_JOB_CONTEXT.value = {'key': key}
    ok = False
    error_text = ''
    try:
        with _FILE_JOB_LOCK:
            st = _FILE_JOB_STATE.get(key)
            if isinstance(st, dict):
                st['started_monotonic'] = _v163_time.monotonic()
                st['phase'] = 'запуск'
                st['telegram_documents_sent'] = 0
                st['external_deliveries_sent'] = 0
                st['external_delivery_kind'] = ''
        _file_job_progress('запуск', force=True)
        mem_ctx = globals().get('memory_operation')
        if callable(mem_ctx):
            with mem_ctx(f"file:{job_meta.get('kind') or 'export'}", {'chat_id': job_meta.get('chat_id'), 'label': job_meta.get('label')}, heavy=True):
                result = func(*args, **kwargs)
        else:
            result = func(*args, **kwargs)
        with _FILE_JOB_LOCK:
            st = _FILE_JOB_STATE.get(key)
            sent = int((st or {}).get('telegram_documents_sent') or 0) if isinstance(st, dict) else 0
            external = int((st or {}).get('external_deliveries_sent') or 0) if isinstance(st, dict) else 0
        ok = result is not False and (sent > 0 or external > 0)
        if not ok:
            error_text = 'экспорт завершился без подтверждённой доставки в Telegram/Google'
    except Exception as exc:
        error_text = str(exc)[:300]
        try:
            log_error(f"INTERACTIVE FILE JOB v163 {job_meta.get('kind')}: {exc}")
        except Exception:
            pass
    finally:
        now_m = _v163_time.monotonic()
        with _FILE_JOB_LOCK:
            st = _FILE_JOB_STATE.get(key)
            if isinstance(st, dict):
                chat_id = int(st.get('chat_id'))
                msg_id = st.get('status_msg_id')
                label = str(st.get('label') or 'Файл')
                started = float(st.get('started_monotonic') or st.get('queued_monotonic') or now_m)
                sent = int(st.get('telegram_documents_sent') or 0)
                external = int(st.get('external_deliveries_sent') or 0)
                external_kind = str(st.get('external_delivery_kind') or '')
                elapsed = _file_job_elapsed_text(now_m - started)
            else:
                chat_id = int(job_meta.get('chat_id') or 0)
                msg_id = None
                label = str(job_meta.get('label') or 'Файл')
                sent = 0
                external = 0
                external_kind = ''
                elapsed = '0:00'
        try:
            if msg_id:
                close_s = internal_timer_seconds('file_status_close', 15)
                if ok:
                    delivered_text = f"Выгружено в {external_kind or 'Google'}" if external > 0 and sent <= 0 else 'Отправлено в чат'
                    final = f'✅ {label}\n{delivered_text} за {elapsed}.\nОкно закроется через {_format_duration_short(close_s)}.'
                else:
                    final = f"⚠️ {label}\nЗавершено за {elapsed}.\n{error_text or 'Telegram не подтвердил отправку.'}\nОкно закроется через {_format_duration_short(close_s)}."
                final = _v159_force_marker(final, 'Ф233', '⏳')
                bot.edit_message_text(final, chat_id=chat_id, message_id=int(msg_id))
                _v161_schedule_delete(chat_id, int(msg_id), close_s, 'file-close')
        except Exception:
            pass
        try:
            bot_journal('file_job_done' if ok else 'file_job_send_missing', chat_id, f"kind={job_meta.get('kind')} elapsed={elapsed} sent_documents={sent} external_deliveries={external} error={error_text}", 'INFO' if ok else 'WARN')
        except Exception:
            pass
        try:
            _v160_cancel_timer(f'v160:file-tick:{key}')
        except Exception:
            pass
        try:
            DELAYED_SCHEDULER.cancel(f'file-job-tick:{key}')
        except Exception:
            pass
        # v259: final runtime uses this canonical runner (not the older runner in
        # 74_ui_reliability_runtime). Release the shared Render Key Value lock
        # here too; otherwise the first CSV/XLSX/journal action after deploy
        # leaves every later file action blocked until Redis TTL expiry.
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
                log_error(f'canonical file job Key Value release v259: {kv_release_exc}')
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
_V163_EXACT_TODAY_HANDLERS = 0
try:
    _v177_legacy_0007_bot_journal('v163_audit_hardening_installed', int(OWNER_ID or 0), 'start_lane=priority; navigation_lane=per_window; ack=0.15; webhook_secret_path=1; F111_today=calendar; F113_today_shortcut=1; F52_F53_scope_union=1; F233_send_verified=1')
except Exception:
    pass
"v164: explicit owner / first-circle / second-circle hierarchy with isolated tenants.\n\nRules:\n- OWNER_ID private owner contour is circle 0 / platform tenant only.\n- A chat that appears directly (normal /start/message, not through a first-circle invite) is circle 1\n  and gets its own dedicated tenant.\n- A chat joined with a chat-link created from a circle-1 chat is circle 2. It also gets its own\n  dedicated tenant and stores parent_first_chat_id instead of joining the parent's tenant.\n- Platform owner can administer circle lists globally without mixing their data into platform tenant.\n- Circle-1 managers can administer their own circle-2 descendants.\n"
import hashlib as _v164_hashlib
import threading as _v164_threading
import time as _v164_time
V164_CIRCLE_SCHEMA = 1
_V164_LOCK = _v164_threading.RLock()
_V164_WINDOW_VIEW_LOCK = _v164_threading.RLock()
_V164_WINDOW_VIEW = {}
_V164_MIGRATING = False
_V164_PREV_TENANT_ID_FOR_CHAT = _v177_legacy_0248_tenant_id_for_chat
_V164_PREV_TENANT_NOTE_CHAT_SEEN = _v177_legacy_0251_tenant_note_chat_seen
_V164_PREV_TENANT_BIND_CHAT = globals().get('tenant_bind_chat')
_V164_PREV_TENANT_CAN_MANAGE = _v177_legacy_0249_tenant_can_manage
_V164_PREV_TENANT_CREATE_INVITE = _v177_legacy_0252_tenant_create_invite
_V164_PREV_TENANT_CONSUME_INVITE = _v177_legacy_0253_tenant_consume_invite
_V164_PREV_TENANT_SAME_SPACE = _v177_legacy_0250_tenant_same_space
_V164_PREV_ADD_FORWARD_LINK = _v177_legacy_0142_add_forward_link
_V164_PREV_COLLECT_FORWARD_PAIRS = _v177_legacy_0190_collect_forward_pairs_for_menu
_V164_PREV_BUILD_FORWARD_NEW_MENU = _v177_legacy_0193_build_forward_new_menu
_V164_PREV_BUILD_FORWARD_SOURCE_MENU = _v177_legacy_0185_build_forward_source_menu
_V164_PREV_BUILD_FORWARD_TARGET_MENU = _v177_legacy_0186_build_forward_target_menu
_V164_PREV_BUILD_QUICK_BALANCE_MODE_MENU = _v177_legacy_0198_build_quick_balance_mode_menu
_V164_PREV_BUILD_CHAT_DESCRIPTION_MENU = _v177_legacy_0183_build_chat_description_menu
_V164_PREV_RESTORE_VALIDATE = _v177_legacy_0287_v153_validate_restore_gz

def _v164_owner_id() -> int:
    try:
        return int(OWNER_ID or 0)
    except Exception:
        return 0

def _v164_now() -> str:
    try:
        return _tenant_now()
    except Exception:
        return _v164_time.strftime('%Y-%m-%dT%H:%M:%S')

def _v164_root() -> dict:
    gs = data.setdefault('global_settings', {})
    root = gs.get('circle_hierarchy_v164')
    if not isinstance(root, dict):
        root = {}
        gs['circle_hierarchy_v164'] = root
    root.setdefault('schema_version', V164_CIRCLE_SCHEMA)
    root.setdefault('chat_meta', {})
    root.setdefault('migration_runs', 0)
    root.setdefault('global_forward_pairs', {})
    root.setdefault('created_at', _v164_now())
    return root

def _v164_mapping() -> dict:
    try:
        return _tenants_root().setdefault('chat_to_tenant', {})
    except Exception:
        return {}

def _v164_tenant_id_for_root_chat(chat_id: int) -> str:
    seed = _v164_hashlib.sha256(f'chat:{int(chat_id)}'.encode('utf-8')).hexdigest()[:12]
    return f'chat_{seed}'

def _v164_meta_raw(chat_id: int) -> dict | None:
    try:
        row = (_v164_root().get('chat_meta') or {}).get(str(int(chat_id)))
        return row if isinstance(row, dict) else None
    except Exception:
        return None

def _v164_set_meta(chat_id: int, circle: int, parent_first_chat_id: int=0, source: str='', tenant_id: str='') -> dict:
    cid = int(chat_id)
    circle = int(circle)
    parent = int(parent_first_chat_id or 0)
    if circle != 2:
        parent = 0
    root = _v164_root()
    meta = root.setdefault('chat_meta', {}).setdefault(str(cid), {})
    old_circle = int(meta.get('circle') or -1)
    old_parent = int(meta.get('parent_first_chat_id') or 0)
    meta.update({'chat_id': cid, 'circle': circle, 'parent_first_chat_id': parent, 'tenant_id': str(tenant_id or meta.get('tenant_id') or ''), 'source': str(source or meta.get('source') or ('owner' if circle == 0 else 'direct')), 'updated_at': _v164_now()})
    meta.setdefault('created_at', _v164_now())
    if old_circle != circle or old_parent != parent:
        meta['classification_changed_at'] = _v164_now()
    return meta

def _v164_circle_from_legacy(chat_id: int) -> tuple[int, int, str]:
    """Infer legacy v148 relation without mutating state."""
    cid = int(chat_id)
    if cid == _v164_owner_id() and cid:
        return (0, 0, TENANT_PLATFORM_ID)
    mapping = _v164_mapping()
    tid = str(mapping.get(str(cid)) or '')
    row = tenant_get(tid) if tid else None
    if row:
        root_chat = int(row.get('root_chat_id') or 0)
        if tid == TENANT_PLATFORM_ID:
            return (1, 0, tid)
        if root_chat and cid != root_chat:
            return (2, root_chat, tid)
        return (1, 0, tid)
    return (1, 0, '')

def _v164_circle_info(chat_id: int, create: bool=False, source: str='direct') -> dict:
    cid = int(chat_id)
    meta = _v164_meta_raw(cid)
    if meta:
        return meta
    circle, parent, tid = _v164_circle_from_legacy(cid)
    if not create:
        return {'chat_id': cid, 'circle': int(circle), 'parent_first_chat_id': int(parent or 0), 'tenant_id': str(tid or ''), 'source': 'legacy_inferred'}
    return _v164_ensure_isolated_chat(cid, circle, parent, actor_user_id=0, source=source)

def circle_level_for_chat(chat_id: int) -> int:
    try:
        return int(_v164_circle_info(int(chat_id), create=False).get('circle') or 0)
    except Exception:
        return 0 if int(chat_id or 0) == _v164_owner_id() else 1

def circle_parent_for_chat(chat_id: int) -> int:
    try:
        return int(_v164_circle_info(int(chat_id), create=False).get('parent_first_chat_id') or 0)
    except Exception:
        return 0

def _v164_parent_tenant_row(parent_first_chat_id: int) -> dict:
    parent_tid = str(_v164_mapping().get(str(int(parent_first_chat_id))) or _v164_tenant_id_for_root_chat(int(parent_first_chat_id)))
    return tenant_get(parent_tid) or {}

def _v164_copy_parent_managers_to_child(child_tid: str, parent_first_chat_id: int, consuming_admin: int=0) -> None:
    parent = _v164_parent_tenant_row(parent_first_chat_id)
    parent_owner = int(parent.get('owner_user_id') or 0)
    if parent_owner:
        try:
            tenant_set_user_role(child_tid, parent_owner, 'tenant_owner', changed_by=parent_owner, save=False)
        except Exception:
            pass
    for uid, item in list((parent.get('users') or {}).items()):
        try:
            iuid = int(uid)
        except Exception:
            continue
        role = str((item or {}).get('role') or 'viewer')
        if role == 'tenant_owner':
            role = 'tenant_owner' if iuid == parent_owner else 'tenant_admin'
        if role not in {'tenant_owner', 'tenant_admin', 'operator', 'viewer'}:
            continue
        try:
            tenant_set_user_role(child_tid, iuid, role, changed_by=parent_owner, save=False)
        except Exception:
            pass
    if consuming_admin and consuming_admin != parent_owner:
        try:
            tenant_set_user_role(child_tid, int(consuming_admin), 'tenant_admin', changed_by=parent_owner or consuming_admin, save=False)
        except Exception:
            pass

def _v164_ensure_isolated_chat(chat_id: int, circle: int, parent_first_chat_id: int=0, actor_user_id: int=0, source: str='direct') -> dict:
    """Ensure one Telegram chat == one tenant. This is the key isolation rule in v164."""
    global _V164_MIGRATING
    cid = int(chat_id)
    circle = int(circle)
    parent = int(parent_first_chat_id or 0)
    owner_id = _v164_owner_id()
    if cid == owner_id and owner_id:
        circle, parent = (0, 0)
        tid = TENANT_PLATFORM_ID
        try:
            if callable(_V164_PREV_TENANT_BIND_CHAT):
                _V164_PREV_TENANT_BIND_CHAT(cid, tid, changed_by=int(actor_user_id or owner_id), force=True)
        except Exception:
            pass
        return _v164_set_meta(cid, 0, 0, source='owner', tenant_id=tid)
    if circle not in {1, 2}:
        circle = 1
    if circle == 2 and (not parent):
        circle = 1
    tid = _v164_tenant_id_for_root_chat(cid)
    _v164_set_meta(cid, circle, parent, source=source, tenant_id=tid)
    row = tenant_get(tid)
    if not row:
        parent_row = _v164_parent_tenant_row(parent) if circle == 2 and parent else {}
        parent_owner = int(parent_row.get('owner_user_id') or 0)
        actor = int(actor_user_id or 0)
        owner_uid = parent_owner if circle == 2 and parent_owner else actor if actor and tenant_user_is_chat_admin(cid, actor) else 0
        try:
            row_tid = tenant_create(_tenant_default_name(cid), owner_uid, cid, created_by=actor, deterministic_chat_id=cid)
            tid = str(row_tid or tid)
            row = tenant_get(tid)
        except Exception:
            row = tenant_get(tid)
    if not row:
        root = _tenants_root()
        row = _tenant_normalize(tid, {'name': _tenant_default_name(cid), 'owner_user_id': 0, 'root_chat_id': cid, 'chat_ids': [cid], 'users': {}, 'settings': {}, 'created_by': int(actor_user_id or 0), 'created_at': _v164_now(), 'updated_at': _v164_now()})
        root.setdefault('tenants', {})[tid] = row
    row['root_chat_id'] = cid
    row['chat_ids'] = [cid]
    row['updated_at'] = _v164_now()
    row.setdefault('settings', {})['circle_level'] = circle
    row['settings']['parent_first_chat_id'] = parent if circle == 2 else 0
    row['settings']['isolation_v164'] = True
    try:
        if callable(_V164_PREV_TENANT_BIND_CHAT):
            _V164_PREV_TENANT_BIND_CHAT(cid, tid, changed_by=int(actor_user_id or 0), force=True)
        else:
            _v164_mapping()[str(cid)] = tid
    except Exception:
        _v164_mapping()[str(cid)] = tid
    if circle == 2 and parent:
        _v164_copy_parent_managers_to_child(tid, parent, consuming_admin=int(actor_user_id or 0))
    meta = _v164_set_meta(cid, circle, parent, source=source, tenant_id=tid)
    try:
        store = get_chat_store(cid)
        settings = store.setdefault('settings', {})
        settings['tenant_id'] = tid
        settings['owner_scope_id'] = cid
        settings['circle_level'] = circle
        settings['parent_first_chat_id'] = parent if circle == 2 else 0
    except Exception:
        pass
    return meta

def _v164_known_chat_ids() -> set[int]:
    ids = set()
    try:
        for raw in (data.get('chats', {}) or {}).keys():
            ids.add(int(raw))
    except Exception:
        pass
    try:
        for raw in (_v164_mapping() or {}).keys():
            ids.add(int(raw))
    except Exception:
        pass
    try:
        for row in tenant_all() or []:
            for raw in row.get('chat_ids') or []:
                ids.add(int(raw))
    except Exception:
        pass
    if _v164_owner_id():
        ids.add(_v164_owner_id())
    return ids

def _v164_migrate_legacy_hierarchy(force: bool=False) -> bool:
    """Split v148 multi-chat tenants into isolated chat tenants while preserving parent relation."""
    global _V164_MIGRATING
    with _V164_LOCK:
        if _V164_MIGRATING:
            return False
        root = _v164_root()
        signature_parts = []
        try:
            for tid, row in sorted((_tenants_root().get('tenants') or {}).items()):
                signature_parts.append(f"{tid}:{int((row or {}).get('root_chat_id') or 0)}:{','.join((str(int(x)) for x in (row or {}).get('chat_ids') or []))}")
        except Exception:
            pass
        sig = _v164_hashlib.sha256('|'.join(signature_parts).encode('utf-8')).hexdigest()[:20]
        if not force and str(root.get('legacy_signature') or '') == sig and (int(root.get('schema_version') or 0) == V164_CIRCLE_SCHEMA):
            return False
        _V164_MIGRATING = True
        changed = False
        try:
            owner = _v164_owner_id()
            if owner:
                _v164_ensure_isolated_chat(owner, 0, source='owner')
            tenant_rows = list((_tenants_root().get('tenants') or {}).items())
            for tid, raw_row in tenant_rows:
                row = raw_row if isinstance(raw_row, dict) else {}
                root_chat = int(row.get('root_chat_id') or 0)
                chats = []
                for raw in row.get('chat_ids') or []:
                    try:
                        chats.append(int(raw))
                    except Exception:
                        pass
                if str(tid) == str(TENANT_PLATFORM_ID):
                    for cid in list(chats):
                        if cid and cid != owner:
                            _v164_ensure_isolated_chat(cid, 1, actor_user_id=0, source='legacy_platform_split')
                            changed = True
                    continue
                if root_chat:
                    _v164_ensure_isolated_chat(root_chat, 1, actor_user_id=int(row.get('owner_user_id') or 0), source='legacy_first_circle')
                    for cid in list(chats):
                        if cid and cid != root_chat:
                            _v164_ensure_isolated_chat(cid, 2, parent_first_chat_id=root_chat, actor_user_id=int(row.get('owner_user_id') or 0), source='legacy_second_circle')
                            changed = True
            for cid in sorted(_v164_known_chat_ids()):
                if cid == owner:
                    continue
                if not _v164_meta_raw(cid):
                    circle, parent, _ = _v164_circle_from_legacy(cid)
                    _v164_ensure_isolated_chat(cid, circle, parent, actor_user_id=0, source='legacy_known_chat')
                    changed = True
            root['schema_version'] = V164_CIRCLE_SCHEMA
            root['legacy_signature'] = sig
            root['migration_runs'] = int(root.get('migration_runs') or 0) + 1
            root['last_migration_at'] = _v164_now()
            if changed:
                try:
                    save_data(data, full=True)
                    schedule_delta_backup(owner or 0, delay=0.5, reason='v164_circle_migration')
                except Exception:
                    pass
                try:
                    bot_journal('v164_circle_migration', owner or 0, f'known={len(_v164_known_chat_ids())}; changed=1')
                except Exception:
                    pass
            return changed
        finally:
            _V164_MIGRATING = False

def _canon_tenant_id_for_chat__001(chat_id: int | None, create: bool=False, actor_user_id: int | None=None) -> str:
    explicit = getattr(_TENANT_CONTEXT, 'tenant_id', None)
    if explicit:
        return str(explicit)
    try:
        cid = int(chat_id or 0)
    except Exception:
        cid = 0
    if not cid:
        return TENANT_PLATFORM_ID if not create else ''
    if cid == _v164_owner_id() and cid:
        if create:
            _v164_ensure_isolated_chat(cid, 0, actor_user_id=int(actor_user_id or 0), source='owner')
        return TENANT_PLATFORM_ID
    tid = str(_v164_mapping().get(str(cid)) or '')
    meta = _v164_meta_raw(cid)
    if tid and tenant_get(tid):
        if create:
            circle, parent, _ = _v164_circle_from_legacy(cid) if not meta else (int(meta.get('circle') or 1), int(meta.get('parent_first_chat_id') or 0), tid)
            fixed = _v164_ensure_isolated_chat(cid, circle, parent, actor_user_id=int(actor_user_id or 0), source=str((meta or {}).get('source') or 'lazy_repair'))
            return str(fixed.get('tenant_id') or _v164_mapping().get(str(cid)) or tid)
        return tid
    if not create:
        return ''
    fixed = _v164_ensure_isolated_chat(cid, 1, 0, actor_user_id=int(actor_user_id or 0), source='direct')
    return str(fixed.get('tenant_id') or _v164_mapping().get(str(cid)) or '')

def _canon_tenant_note_chat_seen__001(msg) -> None:
    try:
        cid = int(msg.chat.id)
        uid = int(getattr(getattr(msg, 'from_user', None), 'id', 0) or 0)
    except Exception:
        return
    meta = _v164_meta_raw(cid)
    if not meta:
        meta = _v164_ensure_isolated_chat(cid, 0 if cid == _v164_owner_id() else 1, actor_user_id=uid, source='direct_seen')
    else:
        meta = _v164_ensure_isolated_chat(cid, int(meta.get('circle') or 1), int(meta.get('parent_first_chat_id') or 0), actor_user_id=uid, source=str(meta.get('source') or 'seen'))
    tid = str(meta.get('tenant_id') or tenant_id_for_chat(cid, create=True, actor_user_id=uid))
    row = tenant_get(tid) or {}
    if not int(row.get('owner_user_id') or 0) and uid and tenant_user_is_chat_admin(cid, uid):
        try:
            tenant_set_user_role(tid, uid, 'tenant_owner', changed_by=uid, save=False)
        except Exception:
            pass
    try:
        store = get_chat_store(cid)
        settings = store.setdefault('settings', {})
        settings['tenant_id'] = tid
        settings['owner_scope_id'] = cid
        settings['circle_level'] = int(meta.get('circle') or 1)
        settings['parent_first_chat_id'] = int(meta.get('parent_first_chat_id') or 0)
    except Exception:
        pass

def _v164_circle_parent_root_for_context(chat_id: int) -> int:
    cid = int(chat_id)
    level = circle_level_for_chat(cid)
    if level == 1:
        return cid
    if level == 2:
        return circle_parent_for_chat(cid)
    return 0

def _v164_circle_children(parent_first_chat_id: int) -> list[int]:
    parent = int(parent_first_chat_id or 0)
    out = []
    for raw_cid, meta in list((_v164_root().get('chat_meta') or {}).items()):
        if not isinstance(meta, dict):
            continue
        try:
            cid = int(raw_cid)
        except Exception:
            continue
        if int(meta.get('circle') or 0) == 2 and int(meta.get('parent_first_chat_id') or 0) == parent:
            out.append(cid)
    return sorted(set(out), key=lambda x: get_chat_display_name(x).casefold())

def _v164_all_circle_ids(level: int) -> list[int]:
    _v164_migrate_legacy_hierarchy()
    out = []
    for cid in _v164_known_chat_ids():
        if cid == _v164_owner_id():
            continue
        try:
            info = _v164_circle_info(cid, create=False)
            if int(info.get('circle') or 0) == int(level):
                out.append(int(cid))
        except Exception:
            pass
    return sorted(set(out), key=lambda x: get_chat_display_name(x).casefold())

def _v164_scope_ids(level: int, context_chat_id: int | None=None) -> list[int]:
    _v164_migrate_legacy_hierarchy()
    level = 2 if int(level) == 2 else 1
    try:
        ctx = int(context_chat_id if context_chat_id is not None else current_state_chat_id() or 0)
    except Exception:
        ctx = 0
    if ctx == _v164_owner_id() and ctx:
        return _v164_all_circle_ids(level)
    root_first = _v164_circle_parent_root_for_context(ctx) if ctx else 0
    if not root_first:
        return []
    if level == 1:
        return [root_first]
    return _v164_circle_children(root_first)

def _v164_actor_manages_parent(user_id: int, parent_first_chat_id: int) -> bool:
    parent_tid = str(_v164_mapping().get(str(int(parent_first_chat_id))) or '')
    if not parent_tid:
        return False
    try:
        role = tenant_role_for_user(int(user_id), tenant_id=parent_tid)
        return role in {'platform_owner', 'tenant_owner', 'tenant_admin'}
    except Exception:
        return False

def _canon_tenant_can_manage__001(user_id: int | None, tenant_id: str | None=None, chat_id: int | None=None, owner_only: bool=False) -> bool:
    try:
        uid = int(user_id or 0)
    except Exception:
        uid = 0
    if tenant_is_platform_owner_user(uid):
        return True
    try:
        if callable(_V164_PREV_TENANT_CAN_MANAGE) and _V164_PREV_TENANT_CAN_MANAGE(uid, tenant_id, chat_id, owner_only):
            return True
    except Exception:
        pass
    target_chat = 0
    if chat_id:
        try:
            target_chat = int(chat_id)
        except Exception:
            target_chat = 0
    if not target_chat and tenant_id:
        try:
            row = tenant_get(str(tenant_id)) or {}
            target_chat = int(row.get('root_chat_id') or 0)
        except Exception:
            target_chat = 0
    if target_chat and circle_level_for_chat(target_chat) == 2:
        parent = circle_parent_for_chat(target_chat)
        return bool(parent and _v164_actor_manages_parent(uid, parent))
    return False

def _canon_tenant_same_space__001(chat_a: int, chat_b: int) -> bool:
    """Isolation is storage-level. Explicit forwarding is allowed inside a first-circle family.

    Platform-owner UI may intentionally connect isolated chats; add_forward_link performs that authorization.
    """
    try:
        a, b = (int(chat_a), int(chat_b))
    except Exception:
        return False
    if a == b:
        return True
    ma, mb = (_v164_circle_info(a, False), _v164_circle_info(b, False))
    la, lb = (int(ma.get('circle') or 0), int(mb.get('circle') or 0))
    pa = a if la == 1 else int(ma.get('parent_first_chat_id') or 0)
    pb = b if lb == 1 else int(mb.get('parent_first_chat_id') or 0)
    if pa and pb and (pa == pb):
        return True
    pair_key = f'{min(a, b)}:{max(a, b)}'
    if pair_key in (_v164_root().get('global_forward_pairs') or {}):
        return True
    ta, tb = (str(_v164_mapping().get(str(a)) or ''), str(_v164_mapping().get(str(b)) or ''))
    return bool(ta and ta == tb)

def _v177_legacy_0143_add_forward_link(src_chat_id: int, dst_chat_id: int, mode: str):
    src, dst = (int(src_chat_id), int(dst_chat_id))
    actor = 0
    try:
        actor = int(tenant_current_actor_user_id() or 0)
    except Exception:
        pass
    if not tenant_same_space(src, dst):
        if not tenant_is_platform_owner_user(actor):
            raise PermissionError('Можно связывать только свой 1-й круг и его 2-й круг')
        key = f'{min(src, dst)}:{max(src, dst)}'
        _v164_root().setdefault('global_forward_pairs', {})[key] = {'src': src, 'dst': dst, 'created_by': actor, 'created_at': _v164_now()}
        try:
            save_data(data, root_only=True)
        except Exception:
            pass
    base = globals().get('_V148_ORIG_ADD_FORWARD_LINK')
    if callable(base):
        return base(src, dst, mode)
    if callable(_V164_PREV_ADD_FORWARD_LINK):
        return _V164_PREV_ADD_FORWARD_LINK(src, dst, mode)
    raise RuntimeError('add_forward_link is unavailable')
try:
    _v177_legacy_0143_add_forward_link.__name__ = 'add_forward_link'
except Exception:
    pass

def _canon_tenant_create_invite__001(tenant_id: str, kind: str, role: str, created_by: int, max_uses: int=1, ttl_hours: int=72) -> str:
    kind = 'chat' if str(kind) == 'chat' else 'user'
    tenant = tenant_get(str(tenant_id)) or {}
    try:
        context_chat = int(current_state_chat_id() or tenant.get('root_chat_id') or 0)
    except Exception:
        context_chat = int(tenant.get('root_chat_id') or 0)
    tenant_root_chat = int(tenant.get('root_chat_id') or 0)
    if kind == 'chat' and tenant_root_chat and (circle_level_for_chat(tenant_root_chat) == 1):
        root_first = tenant_root_chat
    else:
        root_first = _v164_circle_parent_root_for_context(context_chat) if kind == 'chat' else 0
    if kind == 'chat' and (not root_first or circle_level_for_chat(root_first) != 1):
        raise PermissionError('Ссылку 2-го круга нужно создавать из чата 1-го круга')
    payload = _V164_PREV_TENANT_CREATE_INVITE(tenant_id, kind, role, created_by, max_uses=max_uses, ttl_hours=ttl_hours)
    if kind != 'chat':
        return payload
    row = (_tenants_root().get('invite_tokens') or {}).get(_tenant_token_hash(payload))
    if isinstance(row, dict):
        row['circle_parent_chat_id'] = int(root_first)
        row['circle_parent_tenant_id'] = str(_v164_mapping().get(str(root_first)) or '')
        row['circle_schema'] = V164_CIRCLE_SCHEMA
        row['created_from_chat_id'] = int(context_chat or root_first)
        row['created_at'] = _v164_now()
        try:
            save_data(data, root_only=True)
        except Exception:
            pass
    return payload

def _canon_tenant_consume_invite__001(payload: str, user_id: int, chat_id: int, chat_type: str='') -> tuple[bool, str, str]:
    key = _tenant_token_hash(str(payload or '').strip())
    token = (_tenants_root().get('invite_tokens') or {}).get(key)
    if not isinstance(token, dict) or str(token.get('kind') or 'user') != 'chat':
        return _V164_PREV_TENANT_CONSUME_INVITE(payload, user_id, chat_id, chat_type)
    if token.get('revoked') or float(token.get('expires_ts') or 0) < _v164_time.time() or int(token.get('uses') or 0) >= int(token.get('max_uses') or 1):
        return (False, 'Срок действия ссылки закончился.', '')
    cid, uid = (int(chat_id), int(user_id or 0))
    if str(chat_type or '') == 'private' or cid > 0:
        return (False, 'Эту ссылку нужно использовать при добавлении бота в группу/канал.', '')
    if not tenant_user_is_chat_admin(cid, uid):
        return (False, 'Привязать чат может только его администратор.', '')
    parent = int(token.get('circle_parent_chat_id') or 0)
    if not parent:
        legacy_tid = str(token.get('tenant_id') or '')
        legacy_parent = tenant_get(legacy_tid) or {}
        parent = int(legacy_parent.get('root_chat_id') or 0)
    if not parent or circle_level_for_chat(parent) != 1:
        return (False, 'Ссылка не привязана к чату 1-го круга. Создайте новую ссылку в меню пространства.', '')
    parent_tid = str(_v164_mapping().get(str(parent)) or tenant_id_for_chat(parent, create=True, actor_user_id=uid))
    if not tenant_can_manage(int(token.get('created_by') or uid), parent_tid, parent):
        return (False, 'Эта ссылка больше не имеет права подключать чат.', '')
    meta = _v164_ensure_isolated_chat(cid, 2, parent_first_chat_id=parent, actor_user_id=uid, source='first_circle_link')
    child_tid = str(meta.get('tenant_id') or tenant_id_for_chat(cid, create=True, actor_user_id=uid))
    _v164_copy_parent_managers_to_child(child_tid, parent, consuming_admin=uid)
    token['uses'] = int(token.get('uses') or 0) + 1
    token['last_used_at'] = _v164_now()
    token['last_used_by'] = uid
    token['child_chat_id'] = cid
    token['child_tenant_id'] = child_tid
    try:
        save_data(data, full=True)
        schedule_delta_backup(parent, delay=0.5, reason='v164_second_circle_join')
    except Exception:
        pass
    try:
        bot_journal('v164_second_circle_join', cid, f'parent={parent}; tenant={child_tid}; by={uid}')
    except Exception:
        pass
    return (True, f'✅ Чат подключён как 2-й круг к «{get_chat_display_name(parent)}».\nДанные и настройки этого чата изолированы.', child_tid)

def _v164_circle_label(cid: int, include_parent: bool=False) -> str:
    title = get_chat_display_name(int(cid)) or f'Чат {int(cid)}'
    if include_parent and circle_level_for_chat(cid) == 2:
        parent = circle_parent_for_chat(cid)
        return f'{title} ← {get_chat_display_name(parent)}'
    return title

def _canon_tenant_dashboard_text__001(chat_id: int, user_id: int) -> str:
    _v164_migrate_legacy_hierarchy()
    cid, uid = (int(chat_id), int(user_id or 0))
    level = circle_level_for_chat(cid)
    if cid == _v164_owner_id():
        first, second = (_v164_all_circle_ids(1), _v164_all_circle_ids(2))
        return f'🏠 ПРОСТРАНСТВО ВЛАДЕЛЬЦА\n\nЗдесь находится только ваш собственный контур.\nЧаты 1-го и 2-го круга имеют отдельные пространства и не смешиваются с ним.\n\n1️⃣ Первый круг: {len(first)}\n2️⃣ Второй круг: {len(second)}'
    root_first = _v164_circle_parent_root_for_context(cid)
    if level == 1:
        children = _v164_circle_children(cid)
        return f'1️⃣ ПРОСТРАНСТВО ПЕРВОГО КРУГА\n\nЧат: {get_chat_display_name(cid)}\n2-й круг: {len(children)} чат(ов)\n\nФинансы, настройки, напоминания и Google этого пространства изолированы от владельца бота.\nПо ссылке из этого меню можно подключать только свой 2-й круг.'
    parent = circle_parent_for_chat(cid)
    return f"2️⃣ ПРОСТРАНСТВО ВТОРОГО КРУГА\n\nЧат: {get_chat_display_name(cid)}\nРодитель 1-го круга: {(get_chat_display_name(parent) if parent else 'не определён')}\n\nУ этого чата собственное изолированное пространство. Он не становится частью пространства владельца бота."

def _canon_tenant_dashboard_keyboard__001(chat_id: int, user_id: int):
    cid, uid = (int(chat_id), int(user_id or 0))
    kb = types.InlineKeyboardMarkup(row_width=1)
    level = circle_level_for_chat(cid)
    if cid == _v164_owner_id():
        kb.row(IB(f'1️⃣ Первый круг · {len(_v164_all_circle_ids(1))}', callback_data='v164:space_circle:1'))
        kb.row(IB(f'2️⃣ Второй круг · {len(_v164_all_circle_ids(2))}', callback_data='v164:space_circle:2'))
    elif level == 1:
        if tenant_can_manage(uid, chat_id=cid):
            kb.row(IB(f'2️⃣ Второй круг · {len(_v164_circle_children(cid))}', callback_data='v164:space_circle:2'))
            kb.row(IB('🔗 Подключить чат 2-го круга', callback_data=f'sp:chatlink:{tenant_id_for_chat(cid, create=True, actor_user_id=uid)}'))
            kb.row(IB('👥 Пользователи', callback_data=f'sp:users:{tenant_id_for_chat(cid, create=True, actor_user_id=uid)}'))
    else:
        tid = tenant_id_for_chat(cid, create=True, actor_user_id=uid)
        if tenant_can_manage(uid, tid, cid):
            kb.row(IB('👥 Пользователи', callback_data=f'sp:users:{tid}'))
    kb.row(IB('❌ Закрыть', callback_data='info_close'))
    return kb

def _v164_space_list_text(context_chat_id: int, level: int) -> str:
    ids = _v164_scope_ids(level, context_chat_id)
    title = '1️⃣ ПЕРВЫЙ КРУГ' if int(level) == 1 else '2️⃣ ВТОРОЙ КРУГ'
    lines = [title, '']
    if not ids:
        lines.append('Нет подключённых чатов.')
    else:
        for cid in ids:
            if int(level) == 2:
                lines.append(f'• {_v164_circle_label(cid, include_parent=True)}')
            else:
                lines.append(f'• {_v164_circle_label(cid)}')
    lines += ['', 'Каждый чат хранит собственные настройки и данные.']
    return '\n'.join(lines)[:3900]

def _v164_space_list_keyboard(context_chat_id: int, user_id: int, level: int):
    kb = types.InlineKeyboardMarkup(row_width=1)
    ids = _v164_scope_ids(level, context_chat_id)
    for cid in ids[:60]:
        tid = tenant_id_for_chat(cid, create=True, actor_user_id=user_id)
        kb.row(IB(_v164_circle_label(cid, include_parent=int(level) == 2), callback_data=f'sp:open:{tid}'))
    if int(level) == 2 and circle_level_for_chat(context_chat_id) == 1 and tenant_can_manage(user_id, chat_id=context_chat_id):
        tid = tenant_id_for_chat(context_chat_id, create=True, actor_user_id=user_id)
        kb.row(IB('🔗 Подключить чат 2-го круга', callback_data=f'sp:chatlink:{tid}'))
    kb.row(IB('🔙 Назад', callback_data='sp:dashboard:x'))
    return kb

def _canon_tenant_detail_text__001(tenant_id: str, viewer_user_id: int) -> str:
    row = tenant_get(tenant_id) or {}
    cid = int(row.get('root_chat_id') or 0)
    if not cid:
        return '❌ Пространство недоступно.'
    level = circle_level_for_chat(cid)
    lines = ['1️⃣ ПЕРВЫЙ КРУГ' if level == 1 else '2️⃣ ВТОРОЙ КРУГ' if level == 2 else '🏠 ПРОСТРАНСТВО ВЛАДЕЛЬЦА', '', f'Чат: {get_chat_display_name(cid)}', f'ID: {cid}', f"Владелец пространства: {(security_user_display(int(row.get('owner_user_id') or 0)) if int(row.get('owner_user_id') or 0) else 'не назначен')}", 'Изоляция: ✅ отдельные данные/настройки']
    if level == 1:
        lines.append(f'2-й круг: {len(_v164_circle_children(cid))}')
    elif level == 2:
        parent = circle_parent_for_chat(cid)
        lines.append(f"Родитель 1-го круга: {(get_chat_display_name(parent) if parent else 'не определён')}")
    return '\n'.join(lines)[:3900]

def _canon_tenant_chats_text__001(tenant_id: str) -> str:
    row = tenant_get(tenant_id) or {}
    cid = int(row.get('root_chat_id') or 0)
    if not cid:
        return '💬 ЧАТЫ\n\nНет чатов.'
    return f'💬 ЧАТ ПРОСТРАНСТВА\n\n• {get_chat_display_name(cid)} · {cid}\n\nДругие круги сюда не смешиваются.'

def _canon_tenant_visible_spaces__001(user_id: int) -> list[dict]:
    """Keep legacy APIs safe, but do not use this as the v164 owner dashboard.

    The platform owner can still administer all isolated tenants. Non-owner users see direct memberships.
    """
    if tenant_is_platform_owner_user(user_id):
        return tenant_all()
    return tenant_user_spaces(user_id)

def _canon_tenant_handle_callback__001(call, data_str: str) -> bool:
    raw = str(data_str or '')
    if not raw.startswith('sp:'):
        return False
    cid = int(call.message.chat.id)
    uid = int(getattr(call.from_user, 'id', 0) or 0)
    parts = raw.split(':')
    action = parts[1] if len(parts) > 1 else ''
    tid = parts[2] if len(parts) > 2 and parts[2] not in {'x', ''} else tenant_id_for_chat(cid, create=True, actor_user_id=uid)
    if action in {'dashboard', 'list'}:
        safe_edit(bot, call, tenant_dashboard_text(cid, uid), reply_markup=tenant_dashboard_keyboard(cid, uid))
        return True
    row = tenant_get(tid) or {}
    target_chat = int(row.get('root_chat_id') or 0)
    if not target_chat:
        bot.answer_callback_query(call.id, 'Пространство недоступно.', show_alert=True)
        return True
    if not (tenant_is_platform_owner_user(uid) or tenant_can_manage(uid, tid, target_chat) or tenant_role_for_user(uid, tenant_id=tid) in {'operator', 'viewer'}):
        bot.answer_callback_query(call.id, 'Пространство недоступно.', show_alert=True)
        return True
    if action == 'open':
        kb = types.InlineKeyboardMarkup(row_width=1)
        level = circle_level_for_chat(target_chat)
        if tenant_can_manage(uid, tid, target_chat):
            if level == 1:
                kb.row(IB(f'2️⃣ Второй круг · {len(_v164_circle_children(target_chat))}', callback_data='v164:space_circle:2'))
                kb.row(IB('🔗 Подключить чат 2-го круга', callback_data=f'sp:chatlink:{tid}'))
            kb.row(IB('👥 Пользователи', callback_data=f'sp:users:{tid}'))
        kb.row(IB('🔙 Назад', callback_data='sp:dashboard:x'))
        safe_edit(bot, call, tenant_detail_text(tid, uid), reply_markup=kb)
        return True
    if action == 'chats':
        kb = types.InlineKeyboardMarkup()
        kb.row(IB('🔙 Назад', callback_data=f'sp:open:{tid}'))
        safe_edit(bot, call, tenant_chats_text(tid), reply_markup=kb)
        return True
    if action == 'users':
        kb = types.InlineKeyboardMarkup()
        kb.row(IB('🔙 Назад', callback_data=f'sp:open:{tid}'))
        safe_edit(bot, call, tenant_users_text(tid), reply_markup=kb)
        return True
    if action == 'chatlink':
        if circle_level_for_chat(target_chat) != 1 or not tenant_can_manage(uid, tid, target_chat):
            bot.answer_callback_query(call.id, 'Ссылку 2-го круга создаёт только управляющий чата 1-го круга.', show_alert=True)
            return True
        try:
            payload = tenant_create_invite(tid, 'chat', 'tenant_admin', uid, max_uses=1, ttl_hours=72)
        except Exception as exc:
            bot.answer_callback_query(call.id, str(exc)[:180], show_alert=True)
            return True
        text = '🔗 ПОДКЛЮЧЕНИЕ 2-ГО КРУГА\n\n' + tenant_invite_link(payload) + f'\n\nКод: {payload}' + '\n\nДобавленный по этой ссылке чат получит собственное изолированное пространство и будет привязан к этому 1-му кругу.'
        kb = types.InlineKeyboardMarkup()
        kb.row(IB('🔙 Назад', callback_data=f'sp:open:{tid}'))
        safe_edit(bot, call, text, reply_markup=kb)
        return True
    if action == 'userlink':
        if not tenant_can_manage(uid, tid, target_chat):
            bot.answer_callback_query(call.id, 'Недостаточно прав.', show_alert=True)
            return True
        role = parts[3] if len(parts) > 3 else 'operator'
        payload = tenant_create_invite(tid, 'user', role, uid, max_uses=20, ttl_hours=72)
        text = f'👤 ССЫЛКА ДЛЯ ПОЛЬЗОВАТЕЛЯ\n\n{tenant_invite_link(payload)}\n\nРоль: {TENANT_ROLE_LABELS.get(role, role)}.'
        kb = types.InlineKeyboardMarkup()
        kb.row(IB('🔙 Назад', callback_data=f'sp:open:{tid}'))
        safe_edit(bot, call, text, reply_markup=kb)
        return True
    return True

def _v164_update_context() -> dict:
    try:
        value = getattr(_TELEGRAM_UPDATE_CONTEXT, 'value', None)
        return value if isinstance(value, dict) else {}
    except Exception:
        return {}

def _v164_window_key(kind: str) -> tuple[int, int, str]:
    ctx = _v164_update_context()
    try:
        cid = int(ctx.get('chat_id') or current_state_chat_id() or 0)
    except Exception:
        cid = 0
    try:
        mid = int(ctx.get('message_id') or 0)
    except Exception:
        mid = 0
    return (cid, mid, str(kind))

def _v164_set_window_circle(kind: str, level: int) -> None:
    key = _v164_window_key(kind)
    with _V164_WINDOW_VIEW_LOCK:
        _V164_WINDOW_VIEW[key] = {'circle': 2 if int(level) == 2 else 1, 'at': _v164_time.time()}
        if len(_V164_WINDOW_VIEW) > 600:
            cutoff = _v164_time.time() - 86400
            for k, row in list(_V164_WINDOW_VIEW.items()):
                if float((row or {}).get('at') or 0) < cutoff:
                    _V164_WINDOW_VIEW.pop(k, None)

def _v164_current_window_circle(kind: str, default: int=1) -> int:
    key = _v164_window_key(kind)
    ctx = _v164_update_context()
    raw = str(ctx.get('callback_data') or '')
    if str(kind) == 'forward' and raw.startswith('d:') and raw.endswith(':forward_menu'):
        _v164_set_window_circle(kind, 1)
        return 1
    if str(kind) == 'finmode' and raw.startswith('d:') and raw.endswith(':forward_finmode_menu'):
        _v164_set_window_circle(kind, 1)
        return 1
    with _V164_WINDOW_VIEW_LOCK:
        row = _V164_WINDOW_VIEW.get(key) or {}
    return 2 if int(row.get('circle') or default) == 2 else 1

def _v164_circle_switch_button(kind: str, level: int, selected_a: int=0):
    other = 1 if int(level) == 2 else 2
    label = '1️⃣ 1-й круг' if other == 1 else '2️⃣ 2-й круг'
    suffix = f':{int(selected_a)}' if selected_a else ''
    return IB(label, callback_data=f'v164:circle:{kind}:{other}{suffix}')

def _v164_scoped_picker_ids(kind: str, level: int | None=None) -> list[int]:
    if level is None:
        level = _v164_current_window_circle(kind, 1)
    return _v164_scope_ids(int(level), current_state_chat_id())

def _v177_legacy_0182_collect_forward_picker_items(include_owner: bool=True, include_removed: bool=False):
    level = _v164_current_window_circle('forward', 1)
    items = []
    for cid in _v164_scoped_picker_ids('forward', level):
        try:
            if not include_removed and is_chat_bot_removed(int(cid)):
                continue
        except Exception:
            pass
        items.append((int(cid), get_chat_display_name(int(cid)) or f'Чат {cid}'))
    return (items, None)
try:
    _v177_legacy_0182_collect_forward_picker_items.__name__ = '_collect_forward_picker_items'
except Exception:
    pass

def _v177_legacy_0191_collect_forward_pairs_for_menu() -> list[tuple[int, int]]:
    rows = _V164_PREV_COLLECT_FORWARD_PAIRS() if callable(_V164_PREV_COLLECT_FORWARD_PAIRS) else []
    allowed = set(_v164_scoped_picker_ids('forward'))
    out = []
    for pair in rows or []:
        try:
            a, b = (int(pair[0]), int(pair[1]))
        except Exception:
            continue
        if a in allowed:
            out.append((a, b))
    return out
try:
    _v177_legacy_0191_collect_forward_pairs_for_menu.__name__ = 'collect_forward_pairs_for_menu'
except Exception:
    pass

def _v164_insert_before_nav(kb, button) -> None:
    try:
        rows = kb.keyboard
        idx = max(0, len(rows) - 3)
        rows.insert(idx, [button])
    except Exception:
        try:
            kb.row(button)
        except Exception:
            pass

def _canon_build_forward_new_menu__001(day_key: str | None=None, A: int | None=None, B: int | None=None):
    level = _v164_current_window_circle('forward', circle_level_for_chat(A) if A else 1)
    kb = _V164_PREV_BUILD_FORWARD_NEW_MENU(day_key, A, B)
    if not B:
        _v164_insert_before_nav(kb, _v164_circle_switch_button('forward', level, int(A or 0)))
    return kb

def _canon_build_forward_source_menu__001(day_key: str | None=None):
    if forward_menu_new_style_enabled():
        return build_forward_new_menu(day_key)
    level = _v164_current_window_circle('forward', 1)
    kb = _V164_PREV_BUILD_FORWARD_SOURCE_MENU(day_key)
    _v164_insert_before_nav(kb, _v164_circle_switch_button('forward', level))
    return kb

def _canon_build_forward_target_menu__001(src_id: int):
    src = int(src_id)
    if circle_level_for_chat(src) in {1, 2}:
        key = _v164_window_key('forward')
        with _V164_WINDOW_VIEW_LOCK:
            if key not in _V164_WINDOW_VIEW:
                _V164_WINDOW_VIEW[key] = {'circle': circle_level_for_chat(src), 'at': _v164_time.time()}
    level = _v164_current_window_circle('forward', circle_level_for_chat(src))
    kb = _V164_PREV_BUILD_FORWARD_TARGET_MENU(src)
    _v164_insert_before_nav(kb, _v164_circle_switch_button('forward', level, src))
    return kb

def _canon_build_forward_menu_text_for_current_mode__001(title: str | None=None, A: int | None=None, B: int | None=None) -> str:
    level = _v164_current_window_circle('forward', circle_level_for_chat(A) if A else 1)
    prefix = '1️⃣ 1-й круг' if level == 1 else '2️⃣ 2-й круг'
    if forward_menu_new_style_enabled():
        body = build_forward_new_text(A, B)
    else:
        body = build_forward_status_text(title or 'Пересылка:\nВыберите чат A:')
    return f'{prefix}\n{body}'

def _canon_build_forward_menu_keyboard_for_current_mode__001(day_key: str | None=None, A: int | None=None, B: int | None=None):
    if forward_menu_new_style_enabled():
        return build_forward_new_menu(day_key, A, B)
    if A and B:
        return build_forward_mode_menu(A, B)
    if A:
        return build_forward_target_menu(A)
    return build_forward_source_menu(day_key)

def _v177_legacy_0197_build_finance_toggle_chat_menu(day_key: str):
    level = _v164_current_window_circle('finmode', 1)
    kb = types.InlineKeyboardMarkup(row_width=2)
    buttons = []
    for cid in _v164_scope_ids(level, current_state_chat_id()):
        try:
            if is_chat_bot_removed(cid):
                continue
        except Exception:
            pass
        icon = finance_mode_compact_icon(cid)
        buttons.append(IB(f'{icon} {chat_button_title(cid, get_chat_display_name(cid))}', callback_data=f'd:{day_key}:fw_finmode_pick_{cid}'))
    add_buttons_in_rows(kb, buttons, 2)
    if not buttons:
        kb.row(IB('Нет чатов этого круга', callback_data='none'))
    kb.row(_v164_circle_switch_button('finmode', level))
    kb.row(IB('ℹ️ Описание чатов', callback_data='chat_desc_menu:finmode'))
    kb.row(IB('🔙 Назад', callback_data=f'd:{day_key}:back_main'))
    return kb
try:
    _v177_legacy_0197_build_finance_toggle_chat_menu.__name__ = 'build_finance_toggle_chat_menu'
except Exception:
    pass

def _canon_build_quick_balance_mode_menu__001(day_key: str, target_chat_id: int):
    kb = _V164_PREV_BUILD_QUICK_BALANCE_MODE_MENU(day_key, target_chat_id)
    level = _v164_current_window_circle('finmode', circle_level_for_chat(int(target_chat_id)))
    try:
        if kb.keyboard:
            last = kb.keyboard[-1]
            if last and 'Назад' in str(getattr(last[0], 'text', '')):
                kb.keyboard[-1] = [IB('🔙 Назад к чатам', callback_data=f'v164:finback:{level}:{day_key}')]
    except Exception:
        pass
    return kb

def _canon_build_finance_mode_config_menu__001(day_key: str, target_chat_id: int):
    return build_quick_balance_mode_menu(day_key, target_chat_id)

def _v177_legacy_0184_build_chat_description_menu(viewer_chat_id: int, origin: str, day_key: str):
    if str(origin) not in {'forward', 'finmode'}:
        return _V164_PREV_BUILD_CHAT_DESCRIPTION_MENU(viewer_chat_id, origin, day_key)
    kind = 'finmode' if str(origin) == 'finmode' else 'forward'
    level = _v164_current_window_circle(kind, 1)
    kb = types.InlineKeyboardMarkup(row_width=2)
    buttons = []
    for cid in _v164_scope_ids(level, viewer_chat_id):
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
    _v177_legacy_0184_build_chat_description_menu.__name__ = 'build_chat_description_menu'
except Exception:
    pass

def _v164_circle_callback_filter(call) -> bool:
    try:
        raw = str(getattr(call, 'data', '') or '')
        resolver = globals().get('resolve_short_callback')
        if callable(resolver):
            raw = str(resolver(raw) or raw)
        return raw.startswith('v164:')
    except Exception:
        return False

def _v164_current_day_for_ui(chat_id: int) -> str:
    try:
        return str(get_chat_store(int(chat_id)).get('current_view_day') or today_key())
    except Exception:
        return today_key()

def _v164_circle_callback(call):
    raw = str(getattr(call, 'data', '') or '')
    try:
        resolver = globals().get('resolve_short_callback')
        if callable(resolver):
            raw = str(resolver(raw) or raw)
    except Exception:
        pass
    cid = int(call.message.chat.id)
    uid = int(getattr(call.from_user, 'id', 0) or 0)
    parts = raw.split(':')
    try:
        if raw.startswith('v164:circle:') and len(parts) >= 4:
            kind = str(parts[2])
            level = 2 if int(parts[3]) == 2 else 1
            selected_a = int(parts[4]) if len(parts) > 4 and str(parts[4]).lstrip('-').isdigit() else 0
            if kind not in {'forward', 'finmode'}:
                return
            if cid != _v164_owner_id() and (not tenant_can_manage(uid, chat_id=_v164_circle_parent_root_for_context(cid) or cid)):
                bot.answer_callback_query(call.id, 'Недостаточно прав.', show_alert=True)
                return
            _v164_set_window_circle(kind, level)
            day = _v164_current_day_for_ui(cid)
            if kind == 'forward':
                if selected_a:
                    kb = build_forward_new_menu(day, selected_a) if forward_menu_new_style_enabled() else build_forward_target_menu(selected_a)
                    text = build_forward_menu_text_for_current_mode(f'Источник: {get_chat_display_name(selected_a)}\nВыберите чат B:', A=selected_a)
                else:
                    kb = build_forward_menu_keyboard_for_current_mode(day)
                    text = build_forward_menu_text_for_current_mode('Пересылка:\nВыберите чат A:')
                safe_edit(bot, call, text, reply_markup=kb)
            else:
                safe_edit(bot, call, '💰 Фин режим / В24\n' + ('1️⃣ Первый круг' if level == 1 else '2️⃣ Второй круг') + '\nВыберите чат.', reply_markup=build_finance_toggle_chat_menu(day))
            return
        if raw.startswith('v164:finback:') and len(parts) >= 4:
            level = 2 if int(parts[2]) == 2 else 1
            day = str(parts[3] or _v164_current_day_for_ui(cid))
            _v164_set_window_circle('finmode', level)
            safe_edit(bot, call, '💰 Фин режим / В24\n' + ('1️⃣ Первый круг' if level == 1 else '2️⃣ Второй круг') + '\nВыберите чат.', reply_markup=build_finance_toggle_chat_menu(day))
            return
        if raw.startswith('v164:space_circle:') and len(parts) >= 3:
            level = 2 if int(parts[2]) == 2 else 1
            if cid != _v164_owner_id() and (not (tenant_can_manage(uid, chat_id=cid) or circle_level_for_chat(cid) == 2)):
                bot.answer_callback_query(call.id, 'Недостаточно прав.', show_alert=True)
                return
            safe_edit(bot, call, _v164_space_list_text(cid, level), reply_markup=_v164_space_list_keyboard(cid, uid, level))
            return
    except Exception as exc:
        try:
            log_error(f'v164 circle callback {raw}: {exc}')
        except Exception:
            pass
        try:
            bot.answer_callback_query(call.id, 'Не удалось открыть круг.', show_alert=True)
        except Exception:
            pass

def _v164_space_chat_link_handler(msg):
    try:
        uid, cid = (int(getattr(getattr(msg, 'from_user', None), 'id', 0) or 0), int(msg.chat.id))
        tenant_note_chat_seen(msg)
        if circle_level_for_chat(cid) != 1:
            bot.send_message(cid, '❌ Подключать 2-й круг можно только из чата 1-го круга.')
            return
        tid = tenant_id_for_chat(cid, create=True, actor_user_id=uid)
        if not tenant_can_manage(uid, tid, cid):
            bot.send_message(cid, '❌ Недостаточно прав.')
            return
        payload = tenant_create_invite(tid, 'chat', 'tenant_admin', uid, max_uses=1, ttl_hours=72)
        bot.send_message(cid, '🔗 Ссылка для подключения чата 2-го круга (72 часа):\n' + tenant_invite_link(payload) + f'\n\nКод: {payload}')
        try:
            schedule_command_delete(msg)
        except Exception:
            pass
    except Exception as exc:
        try:
            bot.send_message(msg.chat.id, f'❌ Не удалось создать ссылку: {str(exc)[:240]}')
        except Exception:
            pass

def _v164_install_space_command_handler() -> int:
    try:
        bot.message_handler(commands=['space_chat_link', 'tenant_chat_link'])(_v164_space_chat_link_handler)
        handlers = getattr(bot, 'message_handlers', None)
        if isinstance(handlers, list) and handlers:
            row = handlers.pop()
            handlers.insert(0, row)
        return 1
    except Exception:
        return 0
try:
    WINDOW_MARKER_CONSTANTS.update({'v164:circle:forward:*': 'Ф53', 'v164:circle:finmode:*': 'Ф52', 'v164:finback:*': 'Ф52', 'v164:space_circle:*': 'Ф239'})
except Exception:
    pass
_V164_CALLBACK_HANDLER = 0
_V164_SPACE_COMMAND_HANDLER = _v164_install_space_command_handler()
try:
    _v177_legacy_0007_bot_journal('v164_circle_hierarchy_installed', _v164_owner_id(), f'owner=isolated; direct=first_circle; invite=second_circle_isolated; owner_menus=circles; callbacks={_V164_CALLBACK_HANDLER}; command={_V164_SPACE_COMMAND_HANDLER}')
except Exception:
    pass
'v165: restore owner row in Forwarding and Finance-mode first-circle pickers.\n\nThe owner is visible in the same menus as in v163 and earlier, but remains circle 0 / platform tenant.\nCircle 1 continues to mean ordinary direct-connected chats with their own isolated settings.\nCircle 2 remains a separate picker and never receives the owner row.\n'
_V165_PREV_RESTORE_VALIDATE = _v177_legacy_0287_v153_validate_restore_gz

def _v165_is_platform_owner_context() -> bool:
    try:
        return int(current_state_chat_id() or 0) == int(OWNER_ID or 0) and int(OWNER_ID or 0) != 0
    except Exception:
        return False

def _v165_owner_item(include_removed: bool=False):
    try:
        oid = int(OWNER_ID or 0)
    except Exception:
        oid = 0
    if not oid:
        return None
    if not include_removed:
        try:
            if is_chat_bot_removed(oid) and (not _v165_is_platform_owner_context()):
                return None
        except Exception:
            pass
    return (oid, get_chat_display_name(oid) or f'Чат {oid}')

def _canon_collect_forward_picker_items__001(include_owner: bool=True, include_removed: bool=False):
    """v165: v163-compatible owner row + v164 circle-scoped ordinary chats."""
    level = _v164_current_window_circle('forward', 1)
    items = []
    owner_item = None
    for cid in _v164_scope_ids(level, current_state_chat_id()):
        try:
            icid = int(cid)
        except Exception:
            continue
        try:
            if not include_removed and is_chat_bot_removed(icid):
                continue
        except Exception:
            pass
        items.append((icid, get_chat_display_name(icid) or f'Чат {icid}'))
    if include_owner and int(level) == 1 and _v165_is_platform_owner_context():
        owner_item = _v165_owner_item(include_removed=include_removed)
    if owner_item:
        items = [(cid, title) for cid, title in items if int(cid) != int(owner_item[0])]
    items.sort(key=lambda row: (str(row[1]).casefold(), int(row[0])))
    return (items, owner_item)

def _v177_legacy_0192_collect_forward_pairs_for_menu() -> list[tuple[int, int]]:
    """Show historical owner pairs again on the 1st-circle page without mixing tenant storage."""
    try:
        rows = _V164_PREV_COLLECT_FORWARD_PAIRS() if callable(_V164_PREV_COLLECT_FORWARD_PAIRS) else []
    except Exception:
        rows = []
    level = _v164_current_window_circle('forward', 1)
    allowed = set((int(x) for x in _v164_scope_ids(level, current_state_chat_id()) or []))
    if int(level) == 1 and _v165_is_platform_owner_context():
        try:
            allowed.add(int(OWNER_ID))
        except Exception:
            pass
    out = []
    for pair in rows or []:
        try:
            a, b = (int(pair[0]), int(pair[1]))
        except Exception:
            continue
        if a in allowed:
            out.append((a, b))
    return out
try:
    _v177_legacy_0192_collect_forward_pairs_for_menu.__name__ = 'collect_forward_pairs_for_menu'
except Exception:
    pass

def _canon_build_finance_toggle_chat_menu__001(day_key: str):
    """Finance-mode picker: owner + ordinary first circle, or second circle only."""
    level = _v164_current_window_circle('finmode', 1)
    kb = types.InlineKeyboardMarkup(row_width=2)
    buttons = []
    if int(level) == 1 and _v165_is_platform_owner_context():
        owner_item = _v165_owner_item(include_removed=True)
        if owner_item:
            oid, title = owner_item
            icon = finance_mode_compact_icon(oid)
            kb.row(IB(f'{icon} {chat_button_title(oid, title)}', callback_data=f'd:{day_key}:fw_finmode_pick_{oid}'))
    for cid in _v164_scope_ids(level, current_state_chat_id()):
        try:
            cid = int(cid)
        except Exception:
            continue
        if OWNER_ID and str(cid) == str(OWNER_ID):
            continue
        try:
            if is_chat_bot_removed(cid):
                continue
        except Exception:
            pass
        icon = finance_mode_compact_icon(cid)
        buttons.append(IB(f'{icon} {chat_button_title(cid, get_chat_display_name(cid))}', callback_data=f'd:{day_key}:fw_finmode_pick_{cid}'))
    add_buttons_in_rows(kb, buttons, 2)
    if not buttons and (not (int(level) == 1 and _v165_is_platform_owner_context())):
        kb.row(IB('Нет чатов этого круга', callback_data='none'))
    kb.row(_v164_circle_switch_button('finmode', level))
    kb.row(IB('ℹ️ Описание чатов', callback_data='chat_desc_menu:finmode'))
    kb.row(IB('🔙 Назад', callback_data=f'd:{day_key}:back_main'))
    return kb

def _canon_build_chat_description_menu__001(viewer_chat_id: int, origin: str, day_key: str):
    """Description picker mirrors the visible owner/first/second-circle selection."""
    if str(origin) not in {'forward', 'finmode'}:
        return _V164_PREV_BUILD_CHAT_DESCRIPTION_MENU(viewer_chat_id, origin, day_key)
    kind = 'finmode' if str(origin) == 'finmode' else 'forward'
    level = _v164_current_window_circle(kind, 1)
    kb = types.InlineKeyboardMarkup(row_width=2)
    buttons = []
    try:
        viewer_is_owner = int(viewer_chat_id or 0) == int(OWNER_ID or 0) and int(OWNER_ID or 0) != 0
    except Exception:
        viewer_is_owner = False
    if int(level) == 1 and viewer_is_owner:
        owner_item = _v165_owner_item(include_removed=True)
        if owner_item:
            kb.row(IB(chat_button_title(owner_item[0], owner_item[1]), callback_data=f'chat_desc_open:{origin}:{owner_item[0]}'))
    for cid in _v164_scope_ids(level, viewer_chat_id):
        try:
            cid = int(cid)
        except Exception:
            continue
        if OWNER_ID and str(cid) == str(OWNER_ID):
            continue
        try:
            if is_chat_bot_removed(cid):
                continue
        except Exception:
            pass
        buttons.append(IB(chat_button_title(cid), callback_data=f'chat_desc_open:{origin}:{cid}'))
    add_buttons_in_rows(kb, buttons, 2)
    kb.row(IB('🔙 Назад', callback_data=_chat_description_origin_back(origin, day_key)))
    kb.row(IB('⬅️ Назад осн. окно', callback_data=f'd:{day_key}:back_main'))
    return kb
try:
    _v177_legacy_0007_bot_journal('v165_owner_first_circle_compat_installed', int(OWNER_ID or 0), 'owner_row=restored_in_forward_and_finmode_first_circle; owner_settings=preserved; circle1=ordinary_isolated_chats; circle2=separate')
except Exception:
    pass
'v166: restore forwarding pairs, fast callbacks, parallel per-window UI and fast finance refresh.\n\nSafety rule: actual finance mutations remain chat-serialized. Independent window UI, forwarding-pair\nconfiguration and post-commit finance-window refreshes are separated into dedicated keyed lanes.\n'
import contextlib as _v166_contextlib
import threading as _v166_threading
import time as _v166_time
V166_WINDOW_UI_TASK_POOL = globals().get('FAST_UI_TASK_POOL', UI_TASK_POOL)
V166_FORWARD_CONFIG_TASK_POOL = GENERAL_TASK_POOL
V166_FINANCE_UI_TASK_POOL = UI_TASK_POOL
V166_CONFIG_IO_TASK_POOL = GENERAL_TASK_POOL
V166_CONFIG_IO_SCHEDULER = DELAYED_SCHEDULER
V166_FINANCE_DEBOUNCE_TASK_POOL = GENERAL_TASK_POOL
V166_FINANCE_DEBOUNCE_SCHEDULER = DELAYED_SCHEDULER
_V166_PAIR_EXEC_GUARD = _v166_threading.RLock()
_V166_PAIR_EXEC_LOCKS = {}
_V166_FORWARD_STATE_LOCK = _v166_threading.RLock()
_V166_FORWARD_DIRTY_LOCK = _v166_threading.RLock()
_V166_FORWARD_DIRTY_CHATS = set()
_V166_PREV_ACK = _v177_legacy_0224_schedule_callback_receipt_ack
_V166_PREV_REFRESH_BALANCE = _v177_legacy_0062_refresh_balance_panel_now
_V166_PREV_REFRESH_TOTAL = _v177_legacy_0230_refresh_total_message_if_any
_V166_PREV_RESTORE_VALIDATE = _v177_legacy_0287_v153_validate_restore_gz

def _v166_callback_raw_parts(payload: dict):
    try:
        cq = (payload or {}).get('callback_query') or {}
        msg = cq.get('message') or {}
        chat = msg.get('chat') or {}
        return (str(cq.get('data') or ''), int(chat.get('id') or 0), int(msg.get('message_id') or 0))
    except Exception:
        return ('', 0, 0)

def _v166_forward_pair_from_callback(raw: str):
    raw = str(raw or '')
    prefixes = ('fw_new_mode:', 'fw_new_fin:', 'fw_new_clear:', 'fw_mode:', 'fw_finpair:', 'fw_clear:')
    if not raw.startswith(prefixes):
        return None
    nums = []
    for part in raw.split(':')[1:]:
        try:
            nums.append(int(part))
        except Exception:
            continue
        if len(nums) >= 2:
            break
    if len(nums) < 2:
        return None
    a, b = (nums[0], nums[1])
    return (a, b) if a <= b else (b, a)

def _v166_is_finance_business_callback(raw: str) -> bool:
    """Callbacks that can create/delete/edit money stay serialized per chat."""
    low = str(raw or '').casefold()
    if low.startswith(('fw_new_fin:', 'fw_new_mode:', 'fw_new_clear:', 'fw_mode:', 'fw_finpair:', 'fw_clear:')):
        return False
    hard_prefixes = ('fv:', 'fv_', 'edit_', 'del_', 'delete_', 'expense_', 'income_', 'rec_', 'record_', 'usd_edit', 'usd_del', 'cat_move', 'cat_delete')
    if low.startswith(hard_prefixes):
        return True
    dangerous = ('delete_selected', 'apply', 'save', 'confirm', 'finance_off', 'fin_mode_', 'qb_mode_', 'qb_hidden_')
    if any((token in low for token in dangerous)):
        return True
    if low.startswith('d:'):
        try:
            cmd = low.split(':', 2)[2]
        except Exception:
            cmd = low
        safe_tokens = ('info', 'back_main', 'forward_menu', 'forward_finmode_menu', 'calendar', 'articles_toggle', 'financial_values_toggle', 'usd_tx_toggle', 'usd_display_toggle')
        if any((token in cmd for token in safe_tokens)):
            return False
        if any((token in cmd for token in ('delete', 'edit', 'save', 'apply', 'fin_mode_', 'qb_mode_', 'qb_hidden_'))):
            return True
    return False

def _v166_is_safe_window_callback(raw: str) -> bool:
    low = str(raw or '').casefold()
    if not low:
        return False
    if _v166_is_finance_business_callback(raw):
        return False
    if low.startswith(('secret', 'sec:', 'o9:')) and (not any((x in low for x in ('back', 'close', 'menu', 'page', 'list', 'view')))):
        return False
    if _v166_forward_pair_from_callback(raw) is not None:
        return False
    if low in {'forward_menu_style_toggle', 'buttons_current_toggle', 'icon_buttons_toggle', 'reminder_ui_mode_toggle', 'internal_timers', 'process_center', 'problem_tasks', 'journal_open', 'journal_back', 'keepalive_status', 'info_queues', 'info_delta_status'}:
        return True
    # R20: FAST means truly light navigation only. File generation, journal export,
    # Google/backup work and broad d:* actions must never share this lane.
    heavy_tokens = ('csv', 'xlsx', 'export', 'journal_file', 'journal_download', 'backup_now',
                    'mega_', 'google:', 'gsync', 'sheet_create', 'sheet_test', 'drive_',
                    'report_build', 'full_journal', 'download')
    if any(token in low for token in heavy_tokens):
        return False
    if low.startswith(('fw_back', 'fw_new_back', 'chat_desc_', 'v164:circle:', 'rem:list', 'rem:open',
                       'rem:completed', 'itmr_', 'version_')):
        return True
    if low in {'journal_open','journal_back','journal_toggle','keepalive_status','info_queues','info_delta_status'}:
        return True
    if low == 'nav_prev' or 'back' in low or low.endswith('_close') or low.startswith('close_'):
        return True
    if low.startswith('d:') and (not _v166_is_finance_business_callback(raw)):
        try:
            cmd = low.split(':',2)[2]
        except Exception:
            cmd = low
        return any(token in cmd for token in ('info','back_main','calendar','prev','next','today','forward_menu','forward_finmode_menu'))
    return any((token in low for token in ('menu', 'page', 'list', 'view', 'status', 'open'))) and not any(token in low for token in heavy_tokens)

def _canon_v163_webhook_select_lane__001(payload: dict, update_type: str, update_key):
    """R24 ordered every-button FAST stage routing.

    A Telegram button is *always* a FAST/front event.  We no longer classify a button as
    "heavy" and send that callback itself to a slow UI lane.  The callback handler must
    perform only its immediate UI/state stage and, when needed, enqueue the heavy stage
    separately (Render #2 for split-capable work).

    Finance mutations keep their own short chat-serial lane for exact ordering, but that
    lane contains finance mutations only; exports/Google/backup/journal buttons never sit
    in front of them.  Forward-pair configuration is also kept on FAST_UI and serialized
    only by the concrete pair key.
    """
    if str(update_type) == 'message' and _v163_start_payload(payload):
        chat_id = _extract_update_chat_id(payload)
        return (START_UI_TASK_POOL, f'start:{(chat_id if chat_id is not None else update_key)}')
    if str(update_type) == 'callback_query':
        raw, chat_id, message_id = _v166_callback_raw_parts(payload)
        pair = _v166_forward_pair_from_callback(raw)
        if pair is not None:
            return (V166_WINDOW_UI_TASK_POOL, f'fast-pair:{pair[0]}:{pair[1]}')
        if _v166_is_finance_business_callback(raw):
            # Correctness-critical money mutations remain ordered, but no heavy/file
            # callback shares this state lane in R22.
            return (V166_FINANCE_UI_TASK_POOL, f'finance-ui:{(chat_id if chat_id else update_key)}')
        if chat_id and message_id:
            # R24: one small FIFO actor per visible Telegram window. Every click is
            # processed exactly in arrival order; no parallel state races and no click
            # is sacrificed as "stale". Heavy work is dispatched only after this
            # short FAST stage by the existing R21 split helpers.
            return (V166_WINDOW_UI_TASK_POOL, f'fast-window:{chat_id}:{message_id}')
        return (V166_WINDOW_UI_TASK_POOL, f'fast-callback:{update_key}')
    return (WEBHOOK_TASK_POOL, update_key)

def _v166_pair_lock(pair):
    with _V166_PAIR_EXEC_GUARD:
        lock = _V166_PAIR_EXEC_LOCKS.get(pair)
        if lock is None:
            lock = _v166_threading.RLock()
            _V166_PAIR_EXEC_LOCKS[pair] = lock
        return lock

def _v199_apply_raw_chat_migration(payload: dict) -> bool:
    if not isinstance(payload, dict):
        return False
    changed = False
    for field in ('message', 'edited_message', 'channel_post', 'edited_channel_post'):
        msg = payload.get(field)
        if not isinstance(msg, dict):
            continue
        chat = msg.get('chat') or {}
        try:
            chat_id = int(chat.get('id'))
        except Exception:
            continue
        try:
            migrate_to = int(msg.get('migrate_to_chat_id') or 0)
        except Exception:
            migrate_to = 0
        try:
            migrate_from = int(msg.get('migrate_from_chat_id') or 0)
        except Exception:
            migrate_from = 0
        try:
            if migrate_to and migrate_to != chat_id:
                changed = bool(migrate_chat_id_everywhere(chat_id, migrate_to, 'Telegram service migrate_to_chat_id')) or changed
            if migrate_from and migrate_from != chat_id:
                changed = bool(migrate_chat_id_everywhere(migrate_from, chat_id, 'Telegram service migrate_from_chat_id')) or changed
        except Exception as exc:
            try:
                log_error(f'v199 raw chat migration {chat_id}: {exc}')
            except Exception:
                pass
    return changed


def _execute_telegram_payload_core(payload: dict, update_id=None, update_chat_id=None, update_type: str='other'):
    """R48: lane serialization + narrow business locks; never lock a chat for the whole handler."""
    try:
        _v199_apply_raw_chat_migration(payload)
    except Exception as exc:
        try: log_error(f'v199 pre-update migration: {exc}')
        except Exception: pass
    update = telebot.types.Update.de_json(payload)
    if update_chat_id is None:
        update_chat_id = _extract_update_chat_id(payload) if isinstance(payload, dict) else None
    previous_ctx = getattr(_TELEGRAM_UPDATE_CONTEXT, 'value', None)
    critical_callback_target = _durable_callback_target_chat(payload) if isinstance(payload, dict) else None
    callback_data = ''; source_message_id = None; source_user_id = None
    try:
        if isinstance(payload, dict):
            callback = payload.get('callback_query') or {}
            if isinstance(callback, dict):
                callback_data = str(callback.get('data') or '')
                source_user_id = (callback.get('from') or {}).get('id') if isinstance(callback.get('from'), dict) else None
                callback_message = callback.get('message') or {}
                if isinstance(callback_message, dict): source_message_id = callback_message.get('message_id')
            if source_message_id is None:
                message_payload = payload.get('message') or payload.get('edited_message') or payload.get('channel_post') or payload.get('edited_channel_post') or {}
                if isinstance(message_payload, dict):
                    source_message_id = message_payload.get('message_id')
                    source_user_id = source_user_id or ((message_payload.get('from') or {}).get('id') if isinstance(message_payload.get('from'), dict) else None)
    except Exception:
        callback_data = ''
    _TELEGRAM_UPDATE_CONTEXT.value = {'update_id': update_id, 'chat_id': update_chat_id, 'update_type': str(update_type or 'other'), 'callback_data': callback_data, 'message_id': source_message_id, 'user_id': source_user_id, 'critical_callback': critical_callback_target is not None, 'critical_callback_target': critical_callback_target, 'deferred_quick_chats': set()}
    execution_ctx = {}
    try:
        try: r52_diag('TELEBOT_PROCESS_ENTER', update=update_id, chat=update_chat_id, type=update_type, action=callback_data[:240], msg=source_message_id, user=source_user_id, callback_handlers=len(getattr(bot,'callback_query_handlers',[]) or []), message_handlers=len(getattr(bot,'message_handlers',[]) or []), threaded=getattr(bot,'threaded',None))
        except Exception: pass
        _r52_process_started=time.monotonic()
        with state_chat_context(update_chat_id):
            bot.process_new_updates([update])
        try: r52_diag('TELEBOT_PROCESS_EXIT', update=update_id, chat=update_chat_id, type=update_type, action=callback_data[:240], elapsed=time.monotonic()-_r52_process_started, pools=r52_hot_pool_snapshot())
        except Exception: pass
        execution_ctx = _durable_execution_context_snapshot()
        try:
            fn = globals().get('_v150_store_receipt')
            if callable(fn): fn(payload)
        except Exception as exc:
            try: log_error(f'v166 command receipt: {exc}')
            except Exception: pass
    finally:
        if not execution_ctx:
            execution_ctx = _durable_execution_context_snapshot()
        if previous_ctx is None:
            try: delattr(_TELEGRAM_UPDATE_CONTEXT, 'value')
            except Exception: pass
        else:
            _TELEGRAM_UPDATE_CONTEXT.value = previous_ctx
    return execution_ctx


def _canon_schedule_callback_receipt_ack__001(callback_id: str, chat_id=None, delay: float | None=None):
    # R18: receipt ACK is a dedicated immediate lane, not a delayed scheduler job.
    callback_id = str(callback_id or '')
    if not callback_id:
        return False
    try:
        with _CALLBACK_ACK_LOCK:
            _callback_ack_prune_locked()
            row = _CALLBACK_ACK_STATE.setdefault(callback_id, {})
            row['chat_id'] = int(chat_id) if chat_id is not None else row.get('chat_id')
            row['ts'] = time.time()
            if row.get('answered') or row.get('inflight'):
                return True
        _r52_ack_ok=bool(CALLBACK_ACK_TASK_POOL.submit_unique(f'callback-receipt-ack:{callback_id}', _answer_callback_query_quiet, callback_id, chat_id))
        try: r52_diag('ACK_POOL_ADMISSION', callback_id=callback_id, chat=chat_id, queued=int(_r52_ack_ok), ack_pool=CALLBACK_ACK_TASK_POOL.stats())
        except Exception: pass
        return _r52_ack_ok
    except Exception:
        if callable(_V166_PREV_ACK):
            return _V166_PREV_ACK(callback_id, chat_id, 0.03)
        return False

def _v166_pair_key(a: int, b: int):
    a, b = (int(a), int(b))
    return (a, b) if a <= b else (b, a)

def _v166_raw_forward_pairs():
    with data_lock:
        fr = {str(k): dict(v or {}) for k, v in (data.get('forward_rules', {}) or {}).items()}
        ff = {str(k): dict(v or {}) for k, v in (data.get('forward_finance', {}) or {}).items()}
        order = list(data.get('forward_pair_order', []) or [])
    pairs = []
    seen = set()

    def add(a, b):
        try:
            a, b = (int(a), int(b))
        except Exception:
            return
        if a == b:
            return
        key = _v166_pair_key(a, b)
        if key in seen:
            return
        ab = str(b) in (fr.get(str(a), {}) or {})
        ba = str(a) in (fr.get(str(b), {}) or {})
        af = bool((ff.get(str(a), {}) or {}).get(str(b), False))
        bf = bool((ff.get(str(b), {}) or {}).get(str(a), False))
        if not (ab or ba or af or bf):
            return
        seen.add(key)
        pairs.append((a, b))
    if isinstance(order, list):
        for raw in order:
            try:
                a_s, b_s = str(raw).split(':', 1)
                add(int(a_s), int(b_s))
            except Exception:
                continue
    for src, dsts in fr.items():
        for dst in (dsts or {}).keys():
            add(src, dst)
    for src, dsts in ff.items():
        for dst, enabled in (dsts or {}).items():
            if enabled:
                add(src, dst)
    return pairs

def _v166_forward_allowed_ids():
    level = _v164_current_window_circle('forward', 1)
    try:
        ctx = int(current_state_chat_id() or 0)
    except Exception:
        ctx = 0
    allowed = set((int(x) for x in _v164_scope_ids(level, ctx) or []))
    if int(level) == 1 and _v165_is_platform_owner_context():
        try:
            allowed.add(int(OWNER_ID))
        except Exception:
            pass
    return (int(level), allowed)

def _canon_collect_forward_pairs_for_menu__001() -> list[tuple[int, int]]:
    level, allowed = _v166_forward_allowed_ids()
    out = []
    for a, b in _v166_raw_forward_pairs():
        if a in allowed:
            out.append((a, b))
        elif b in allowed:
            out.append((b, a))
    try:
        bot_journal('v166_forward_pairs_menu', current_state_chat_id(), f'circle={level} raw={len(_v166_raw_forward_pairs())} shown={len(out)}')
    except Exception:
        pass
    return out

def _canon_build_forward_status_lines__001() -> list[str]:
    lines = []
    for a, b in collect_forward_pairs_for_menu():
        try:
            arrow, fin, ab_on, ba_on, ab_fin, ba_fin = _forward_pair_icons(a, b)
            if ab_on or ba_on or ab_fin or ba_fin:
                lines.append(f'• {chat_button_title(a)} -({arrow})-({fin})-{chat_button_title(b)}')
        except Exception:
            continue
    return lines

def _v166_schedule_forward_persist(*chat_ids):
    with _V166_FORWARD_DIRTY_LOCK:
        for cid in chat_ids:
            try:
                _V166_FORWARD_DIRTY_CHATS.add(int(cid))
            except Exception:
                pass

    def _fire():

        def _persist():
            with _V166_FORWARD_DIRTY_LOCK:
                ids = sorted(_V166_FORWARD_DIRTY_CHATS)
                _V166_FORWARD_DIRTY_CHATS.clear()
            try:
                save_data(data, full=True)
            except Exception as exc:
                try:
                    log_error(f'v166 forward local persist: {exc}')
                except Exception:
                    pass
            try:
                path = _owner_data_file()
                if path:
                    payload = _load_json(path, {}) or {}
                    if not isinstance(payload, dict):
                        payload = {}
                    payload['forward_rules'] = data.get('forward_rules', {}) or {}
                    payload['forward_finance'] = data.get('forward_finance', {}) or {}
                    payload['forward_pair_order'] = data.get('forward_pair_order', []) or []
                    _save_json(path, payload)
            except Exception as exc:
                try:
                    log_error(f'v166 forward legacy persist: {exc}')
                except Exception:
                    pass
            try:
                if ids:
                    schedule_config_backup_for_chats(*ids, delay=0.3)
                else:
                    schedule_config_backup_for_chats(delay=0.3)
            except Exception:
                pass
        if not V166_CONFIG_IO_TASK_POOL.submit('forward-persist', _persist):
            try:
                log_error('V166 CONFIG IO QUEUE FULL: forward-persist')
            except Exception:
                pass
    try:
        V166_CONFIG_IO_SCHEDULER.cancel('v166-forward-persist')
        V166_CONFIG_IO_SCHEDULER.schedule('v166-forward-persist', 0.12, _fire)
    except Exception:
        _fire()

def _v166_authorize_pair(src: int, dst: int):
    src, dst = (int(src), int(dst))
    if tenant_same_space(src, dst):
        return
    try:
        actor = int(tenant_current_actor_user_id() or 0)
    except Exception:
        actor = 0
    if not tenant_is_platform_owner_user(actor):
        raise PermissionError('Можно связывать только свой 1-й круг и его 2-й круг')
    try:
        key = f'{min(src, dst)}:{max(src, dst)}'
        _v164_root().setdefault('global_forward_pairs', {})[key] = {'src': src, 'dst': dst, 'created_by': actor, 'created_at': _v164_now()}
    except Exception:
        pass

def _v166_cleanup_global_pair(a: int, b: int):
    try:
        arrow, fin, ab_on, ba_on, ab_fin, ba_fin = _forward_pair_icons(a, b)
        if ab_on or ba_on or ab_fin or ba_fin:
            return
        _v164_root().setdefault('global_forward_pairs', {}).pop(f'{min(int(a), int(b))}:{max(int(a), int(b))}', None)
    except Exception:
        pass

def _v166_enable_hidden_finance_memory(dst_chat_id: int):
    dst_chat_id = int(dst_chat_id)
    with locked_chat(dst_chat_id):
        store = get_chat_store(dst_chat_id)
        settings = store.setdefault('settings', {})
        was_enabled = bool(store.get('finance_mode', False))
        store['finance_mode'] = True
        try:
            finance_active_chats.add(dst_chat_id)
        except Exception:
            pass
        settings['hidden_finance'] = True
        if not was_enabled:
            settings['quick_balance_enabled'] = False
            settings['quick_balance_behavior'] = 'normal'
            settings['quick_balance_user_selected'] = True
            state = store.get('finance_window_state')
            if not isinstance(state, dict):
                state = {}
            state.update({'mode': 'off', 'main_windows': {}, 'balance_panel_id': None, 'balance_panel_mode': 'mini', 'current_view_day': str(store.get('current_view_day') or today_key()), 'auto_reopen_on_boot': False, 'updated_at': now_local().isoformat(timespec='seconds')})
            store['finance_window_state'] = state
    _v166_schedule_forward_persist(dst_chat_id)

def _canon_ensure_hidden_finance_for_forward_dst__001(dst_chat_id: int):
    try:
        _v166_enable_hidden_finance_memory(int(dst_chat_id))
        bot_journal('forward_finance_auto_hidden', int(dst_chat_id), 'v166 fast: hidden finance enabled; durable config queued')
    except Exception as exc:
        log_error(f'v166 ensure_hidden_finance_for_forward_dst({dst_chat_id}): {exc}')

def _canon_add_forward_link__001(src_chat_id: int, dst_chat_id: int, mode: str):
    src, dst = (int(src_chat_id), int(dst_chat_id))
    _v166_authorize_pair(src, dst)
    with data_lock, _V166_FORWARD_STATE_LOCK:
        data.setdefault('forward_rules', {}).setdefault(str(src), {})[str(dst)] = str(mode)
    _v166_schedule_forward_persist(src, dst)

def _canon_remove_forward_link__001(src_chat_id: int, dst_chat_id: int):
    src, dst = (int(src_chat_id), int(dst_chat_id))
    with data_lock, _V166_FORWARD_STATE_LOCK:
        fr = data.setdefault('forward_rules', {})
        ff = data.setdefault('forward_finance', {})
        (fr.get(str(src)) or {}).pop(str(dst), None)
        if str(src) in fr and (not fr.get(str(src))):
            fr.pop(str(src), None)
        (ff.get(str(src)) or {}).pop(str(dst), None)
        if str(src) in ff and (not ff.get(str(src))):
            ff.pop(str(src), None)
    _v166_cleanup_global_pair(src, dst)
    _v166_schedule_forward_persist(src, dst)

def _canon_set_forward_finance__001(src_chat_id: int, dst_chat_id: int, enabled: bool):
    src, dst = (int(src_chat_id), int(dst_chat_id))
    _v166_authorize_pair(src, dst)
    with data_lock, _V166_FORWARD_STATE_LOCK:
        data.setdefault('forward_finance', {}).setdefault(str(src), {})[str(dst)] = bool(enabled)
    if enabled:
        ensure_hidden_finance_for_forward_dst(dst)
    _v166_schedule_forward_persist(src, dst)

def _canon_remove_forward_finance__001(src_chat_id: int, dst_chat_id: int):
    src, dst = (int(src_chat_id), int(dst_chat_id))
    with data_lock, _V166_FORWARD_STATE_LOCK:
        ff = data.setdefault('forward_finance', {})
        (ff.get(str(src)) or {}).pop(str(dst), None)
        if str(src) in ff and (not ff.get(str(src))):
            ff.pop(str(src), None)
    _v166_cleanup_global_pair(src, dst)
    _v166_schedule_forward_persist(src, dst)

def _canon_remember_forward_pair__001(A: int, B: int):
    A, B = (int(A), int(B))
    if A == B:
        return
    key, rev = (f'{A}:{B}', f'{B}:{A}')
    with data_lock, _V166_FORWARD_STATE_LOCK:
        order = data.setdefault('forward_pair_order', [])
        if not isinstance(order, list):
            order = []
            data['forward_pair_order'] = order
        if key not in order and rev not in order:
            order.append(key)
    _v166_schedule_forward_persist(A, B)

def _canon_forget_forward_pair_if_empty__001(A: int, B: int):
    A, B = (int(A), int(B))
    try:
        arrow, fin, ab_on, ba_on, ab_fin, ba_fin = _forward_pair_icons(A, B)
        if ab_on or ba_on or ab_fin or ba_fin:
            return
    except Exception:
        return
    key, rev = (f'{A}:{B}', f'{B}:{A}')
    with data_lock, _V166_FORWARD_STATE_LOCK:
        order = data.setdefault('forward_pair_order', [])
        if isinstance(order, list):
            data['forward_pair_order'] = [x for x in order if x not in {key, rev}]
    _v166_cleanup_global_pair(A, B)
    _v166_schedule_forward_persist(A, B)

def _canon_set_forward_menu_new_style_enabled__001(enabled: bool, chat_id: int | None=None):
    cid = int(chat_id) if chat_id is not None else current_state_chat_id()
    if cid is not None:
        owner_scoped_settings(int(cid))['forward_menu_new_style'] = bool(enabled)

        def _persist():
            try:
                save_data(data, chat_ids=[int(cid)])
                schedule_config_backup_for_chats(int(cid), delay=0.3)
            except Exception as exc:
                try:
                    log_error(f'v166 forward style persist: {exc}')
                except Exception:
                    pass
        V166_CONFIG_IO_TASK_POOL.submit(f'style:{int(cid)}', _persist)
    else:
        data.setdefault('_global_settings', {})['forward_menu_new_style'] = bool(enabled)
        V166_CONFIG_IO_TASK_POOL.submit('style:global', save_data, data)

def _canon_toggle_forward_menu_new_style__001(chat_id: int | None=None) -> bool:
    new_value = not forward_menu_new_style_enabled(chat_id)
    set_forward_menu_new_style_enabled(new_value, chat_id)
    return new_value

def _v166_fin_submit(key, fn, *args):
    if not V166_FINANCE_UI_TASK_POOL.submit(str(key), fn, *args):
        try:
            log_error(f'V166 FINANCE UI QUEUE FULL: {key}')
        except Exception:
            pass
        return False
    return True

def _canon_refresh_balance_panel_now__001(chat_id: int):
    if callable(_V166_PREV_REFRESH_BALANCE):
        _v166_fin_submit(f'balance:{int(chat_id)}', _V166_PREV_REFRESH_BALANCE, int(chat_id))

def _canon_refresh_total_message_if_any__001(chat_id: int):
    if callable(_V166_PREV_REFRESH_TOTAL):
        _v166_fin_submit(f'total:{int(chat_id)}', _V166_PREV_REFRESH_TOTAL, int(chat_id))

def _v166_refresh_main_one(chat_id: int, day_key: str, mid: int):
    try:
        actual = get_registered_open_window(int(chat_id), int(mid))
        if actual and str(actual.get('window_type') or '') not in {'', 'main_day'}:
            return
        text, _ = render_day_window(int(chat_id), str(day_key))
        bot.edit_message_text(text, chat_id=int(chat_id), message_id=int(mid), reply_markup=build_main_keyboard(str(day_key), int(chat_id)))
        register_open_window(int(chat_id), int(mid), 'main_day', code='О1', day_key=str(day_key))
    except Exception as exc:
        if 'message is not modified' in str(exc).lower():
            return
        if _message_missing_error(exc):
            try:
                if int(get_active_window_id(int(chat_id), str(day_key)) or 0) == int(mid):
                    clear_active_window_id(int(chat_id), str(day_key))
            except Exception:
                pass
            try:
                unregister_open_window(int(chat_id), int(mid))
            except Exception:
                pass
            return
        try:
            log_error(f'v166 refresh main {chat_id}:{mid}: {exc}')
        except Exception:
            pass

def _v166_refresh_remaining(chat_id: int, mid: int):
    store = get_chat_store(int(chat_id))
    day_key = store.get('current_view_day') or today_key()
    try:
        bot.edit_message_text(build_remaining_text(int(chat_id), day_key), chat_id=int(chat_id), message_id=int(mid), reply_markup=build_remaining_keyboard(int(chat_id), day_key), parse_mode='HTML')
        register_open_window(int(chat_id), int(mid), 'remaining', code='Ф91', day_key=day_key)
    except Exception as exc:
        if _message_missing_error(exc):
            store['remaining_msg_id'] = None
            try:
                unregister_open_window(int(chat_id), int(mid))
            except Exception:
                pass

def _v166_refresh_registry_item(item: dict, target_chat_id: int):
    try:
        wtype = str((item or {}).get('window_type') or '')
        if wtype == 'fin_view':
            _refresh_registered_fin_view(item, int(target_chat_id))
        elif wtype == 'local_fin_view':
            _refresh_registered_local_fin_view(item, int(target_chat_id))
        elif wtype == 'fin_categories_view':
            _refresh_registered_fin_categories_view(item, int(target_chat_id))
        elif wtype == 'stored':
            _refresh_registered_stored_window(item, int(target_chat_id))
    except Exception as exc:
        try:
            log_error(f'v166 finance registry refresh: {exc}')
        except Exception:
            pass

def _v168_fin_window_is_recent(item: dict, max_age_seconds: float=900.0) -> bool:
    """Old parallel Telegram windows remain usable, but do not auto-repaint forever on every transaction."""
    try:
        raw = str((item or {}).get('last_interaction_at') or (item or {}).get('updated_at') or '')
        if not raw:
            return False
        dt = datetime.fromisoformat(raw)
        now = now_local()
        if dt.tzinfo is None and getattr(now, 'tzinfo', None) is not None:
            dt = dt.replace(tzinfo=now.tzinfo)
        return (now - dt).total_seconds() <= float(max_age_seconds)
    except Exception:
        return False

def _canon_refresh_registered_financial_windows__001(chat_id: int):
    """Refresh only the single authoritative main window plus actually open auxiliaries.

    v189 rule: historical main windows never auto-refresh. This removes cross-day repaint
    races and guarantees that background finance changes cannot resurrect an older main window.
    """
    chat_id = int(chat_id)
    store = get_chat_store(chat_id)
    submitted_messages = set()
    try:
        fn = globals().get('get_primary_main_window')
        primary_mid, primary_day = fn(chat_id) if callable(fn) else (None, str(store.get('current_view_day') or today_key())[:10])
    except Exception:
        primary_mid, primary_day = (None, str(store.get('current_view_day') or today_key())[:10])
    if primary_mid:
        try:
            mid_i = int(primary_mid)
            submitted_messages.add(mid_i)
            _v166_fin_submit(f'msg:{chat_id}:{mid_i}', _v166_refresh_main_one, chat_id, str(primary_day), mid_i)
        except Exception:
            pass
    registry_snapshot = list((_open_window_registry() or {}).items())
    rem_mid = int(store.get('remaining_msg_id') or 0)
    if rem_mid and rem_mid not in submitted_messages:
        submitted_messages.add(rem_mid)
        _v166_fin_submit(f'msg:{chat_id}:{rem_mid}', _v166_refresh_remaining, chat_id, rem_mid)
    cat_mid = int(store.get('categories_msg_id') or 0)
    if cat_mid:
        _v166_fin_submit(f'msg:{chat_id}:{cat_mid}', _refresh_categories_window_from_state, chat_id)
    for _key, item in registry_snapshot:
        try:
            wtype = str((item or {}).get('window_type') or '')
            if wtype == 'main_day':
                continue
            if wtype not in {'fin_view', 'local_fin_view', 'fin_categories_view', 'stored'}:
                continue
            if not _v168_fin_window_is_recent(item):
                continue
            params = (item or {}).get('params') or {}
            if wtype == 'fin_view' and int(params.get('target_chat_id') or 0) != chat_id:
                continue
            if wtype in {'local_fin_view', 'fin_categories_view'}:
                target_hint = int(params.get('target_chat_id') or (item or {}).get('chat_id') or 0)
                if target_hint not in {0, chat_id}:
                    continue
            host = int((item or {}).get('chat_id') or (item or {}).get('host_chat_id') or chat_id)
            mid2 = int((item or {}).get('message_id') or 0)
            if not mid2:
                continue
            _v166_fin_submit(f'msg:{host}:{mid2}', _v166_refresh_registry_item, dict(item or {}), chat_id)
        except Exception:
            continue
    return True

def _finance_root_persist_job_v243(chat_id: int) -> None:
    """Persist derived finance root state without nesting data_lock -> SQLite.lock (R36)."""
    try:
        import copy as _r36_copy
        with data_lock:
            data.setdefault('_state_meta', {})['last_saved_at'] = now_local().isoformat(timespec='seconds')
            data['_state_meta']['bot_version'] = VERSION
            root_snapshot = _r36_copy.deepcopy(_sqlite_pack_root(data))
        SQLITE.save_root(root_snapshot)
        try:
            bot_journal('finance_root_persist_v243', int(chat_id), 'background root persisted')
        except Exception:
            pass
    except Exception as exc:
        try:
            log_error(f'finance root persist v243 {chat_id}: {exc}')
        except Exception:
            pass

def schedule_finance_root_persist_v243(chat_id: int, delay: float=0.45) -> None:
    cid = int(chat_id)

    def _fire():
        pool = globals().get('BACKGROUND_TASK_POOL')
        if pool is None or not pool.submit(f'finance-root:{cid}', _finance_root_persist_job_v243, cid):
            _finance_root_persist_job_v243(cid)
    try:
        DELAYED_SCHEDULER.cancel(f'finance-root-persist:{cid}')
        DELAYED_SCHEDULER.schedule(f'finance-root-persist:{cid}', max(0.05, float(delay)), _fire)
    except Exception:
        _fire()

def _finance_postcommit_background_v243(chat_id: int, reason: str='change') -> None:
    cid = int(chat_id)
    try:
        rebuild_global_records()
    except Exception as exc:
        try:
            log_error(f'rebuild_global_records background v243 {cid}: {exc}')
        except Exception:
            pass
    _finance_root_persist_job_v243(cid)
    try:
        schedule_full_backup_only(cid, BACKUP_MIN_DELAY_SECONDS)
    except Exception:
        pass
    try:
        bot_journal('finance_postcommit_background_v243', cid, f'reason={reason}')
    except Exception:
        pass

def schedule_finance_postcommit_background_v243(chat_id: int, reason: str='change', delay: float=0.25) -> None:
    cid = int(chat_id)

    def _fire():
        pool = globals().get('BACKGROUND_TASK_POOL')
        if pool is None or not pool.submit(f'finance-post:{cid}', _finance_postcommit_background_v243, cid, str(reason)):
            _finance_postcommit_background_v243(cid, str(reason))
    try:
        DELAYED_SCHEDULER.cancel(f'finance-postcommit:{cid}')
        DELAYED_SCHEDULER.schedule(f'finance-postcommit:{cid}', max(0.05, float(delay)), _fire)
    except Exception:
        _fire()

def schedule_financial_window_refresh(chat_id: int, day_key: str | None=None, reason: str='finance_changed', delay: float=0.0):
    """Single final finance repaint path. Only the authoritative main window may repaint."""
    chat_id = int(chat_id)
    try:
        switch = globals().get('v176_process_enabled')
        if callable(switch) and (not switch('fin_refresh')):
            return False
    except Exception:
        pass
    try:
        main_day_fn = globals().get('canonical_main_day')
        visual_day = str(main_day_fn(chat_id) if callable(main_day_fn) else get_chat_store(chat_id).get('current_view_day') or today_key())[:10]
    except Exception:
        visual_day = str(get_chat_store(chat_id).get('current_view_day') or today_key())[:10]
    day_key = str(day_key or visual_day)[:10]

    def _dispatch():
        try:
            refresh_balance_panel_now(chat_id)
            refresh_total_message_if_any(chat_id)
            refresh_registered_financial_windows(chat_id)
            bot_journal('finance_window_refresh_parallel', chat_id, f'day={day_key} reason={reason} v166=1')
        except Exception as exc:
            try:
                log_error(f'v166 finance window dispatch {chat_id}: {exc}')
            except Exception:
                pass

    def _fire_visual():
        if not V166_FINANCE_UI_TASK_POOL.submit(f'dispatch:{chat_id}', _dispatch):
            try:
                log_error(f'V166 FINANCE UI DISPATCH QUEUE FULL: {chat_id}')
            except Exception:
                pass
    try:
        key = f'finance-visual:{chat_id}'
        V166_FINANCE_DEBOUNCE_SCHEDULER.cancel(key)
        V166_FINANCE_DEBOUNCE_SCHEDULER.schedule(key, max(0.01, min(float(delay or 0.0), 0.05)), _fire_visual)
        scheduled = True
    except Exception:
        _fire_visual()
        scheduled = True
    try:
        switch = globals().get('v176_process_enabled')
        google_allowed = not callable(switch) or switch('google_auto')
        hook = globals().get('_v169_schedule_google_after_change')
        if google_allowed and callable(hook):
            hook(chat_id, reason)
    except Exception:
        pass
    return scheduled

def finance_changed(chat_id: int, day_key: str | None=None, reason: str='change', delay: float=0.05):
    chat_id = int(chat_id)
    day_key = day_key or get_chat_store(chat_id).get('current_view_day') or today_key()
    try:
        requested = max(0.0, float(delay))
    except Exception:
        requested = 0.05
    effective = min(requested, 0.1)
    bot_journal('finance_changed_scheduled', chat_id, f'day={day_key} reason={reason} delay={effective} v189=single_refresh')

    def _job():
        if not FINANCE_TASK_POOL.submit(chat_id, _finance_changed_now, chat_id, day_key, reason):
            try:
                log_error(f'FINANCE QUEUE FULL, RETRY: {chat_id}')
            except Exception:
                pass
            V166_FINANCE_DEBOUNCE_SCHEDULER.schedule(f'finance-finalize:{chat_id}', 0.25, _fire)

    def _fire():
        with timer_lock:
            _finalize_timers.pop(chat_id, None)
        _job()
    with timer_lock:
        _finalize_timers[chat_id] = _v166_time.time() + effective
    try:
        V166_FINANCE_DEBOUNCE_SCHEDULER.cancel(f'finance-finalize:{chat_id}')
    except Exception:
        pass
    V166_FINANCE_DEBOUNCE_SCHEDULER.schedule(f'finance-finalize:{chat_id}', effective, _fire)

def schedule_finalize(chat_id: int, day_key: str, delay: float=0.05):
    return finance_changed(int(chat_id), str(day_key), reason='schedule_finalize', delay=min(float(delay or 0.05), 0.1))
try:
    _v177_legacy_0007_bot_journal('v166_fast_parallel_forward_pairs_installed', int(OWNER_ID or 0), 'pairs=raw_rules_not_v148_filter; callback_ack=0.05s; safe_ui=per_window; forward_config=per_pair; config_io=dedicated; finance_ui=per_message; finance_debounce=dedicated; finance_finalize<=0.10s')
except Exception:
    pass
'v167: Excel formulas/formatting, Thu-Wed period, rolling Google tab, TZ lifecycle.\n\nThis module deliberately patches only the active public hooks after v166 so older callbacks\nremain compatible while the visible semantics become Thursday -> Wednesday.\n'
import copy as _v167_copy
import os as _v167_os
import tempfile as _v167_tempfile
import threading as _v167_threading
import time as _v167_time
import zipfile as _v167_zipfile
import xml.etree.ElementTree as _v167_ET
from datetime import datetime as _v167_datetime, timedelta as _v167_timedelta
V167_FILE_MARKER = 'v170_clear_journal_names'
_V167_BASE_V151_CATEGORIES = _v177_legacy_0275_v151_categories
_V167_BASE_V151_SIMPLE_TABLE = _v177_legacy_0274_v151_simple_table
_V167_BASE_V151_CATEGORY_TABLE = _v177_legacy_0276_v151_category_table
_V167_BASE_V151_CONTEXT_BOUNDS = _v177_legacy_0273_v151_context_bounds
_V167_BASE_PERIOD_BOUNDS = _v177_legacy_0097_period_export_bounds
_V167_BASE_PERIOD_ROWS = _v177_legacy_0204_period_export_rows
_V167_BASE_SEND_CSV_FOR_CHAT = _v177_legacy_0202_send_csv_for_chat_to
_V167_BASE_SEND_CSV_WEDTHU = _v177_legacy_0226_send_csv_wedthu
_V167_BASE_WRITE_SIMPLE = _v177_legacy_0089_write_simple_xlsx
_V167_BASE_WRITE_TABL = _v177_legacy_0098_write_tabl_lsx_xlsx
_V167_BASE_ADD_EXPORT_ROWS = _v177_legacy_0167_add_export_period_rows
_V167_BASE_SAVE_TZ = _v177_legacy_0320_v160_save_tz
_V167_BASE_EXPORT_TZ = _v177_legacy_0322_v160_export_text
_V167_BASE_SPECIAL_CALLBACK = _v177_legacy_0323_v160_handle_special_callback
_V167_BASE_AUGMENT_MARKUP = _v177_legacy_0317_v160_augment_markup
_V167_GOOGLE_LOCK = _v167_threading.RLock()
_V167_GOOGLE_RUNNING = set()
_V167_GOOGLE_SCHEDULER_STARTED = False
_V167_TZ_ARCHIVE_VERSION = ''

def _v167_cached(value):
    if isinstance(value, dict):
        value = value.get('value', 0)
    try:
        return float(value or 0)
    except Exception:
        return 0.0

def _v251_google_formula_canonical(formula) -> str:
    """Canonicalize only transformations Google itself performs harmlessly.

    Google Sheets rewrites a one-cell SUM range such as SUM(C38:C38) to
    SUM(C38). Those formulas are semantically identical, so generation and
    verification must agree on one representation. We intentionally keep this
    normalization narrow instead of trying to parse arbitrary Sheets formulas.
    """
    text = str(formula or '').strip().lstrip('=').strip()
    if not text:
        return text
    try:
        pattern = r'(?i)\bSUM\(\s*(\$?[A-Z]{1,3}\$?\d+)\s*:\s*\1\s*\)'
        text = re.sub(pattern, lambda m: f'SUM({m.group(1)})', text)
    except Exception:
        pass
    return text


def _v167_formula(formula: str, cached):
    val = _v167_cached(cached)
    if abs(val - round(val)) < 1e-09:
        val = int(round(val))
    return {'formula': _v251_google_formula_canonical(formula), 'value': val}

def _v167_col(index1: int) -> str:
    try:
        return _xlsx_col_name(int(index1))
    except Exception:
        n = max(1, int(index1))
        out = ''
        while n:
            n, rem = divmod(n - 1, 26)
            out = chr(65 + rem) + out
        return out

def _v167_find_label(rows, label: str, preferred_col: int | None=None):
    needle = str(label).strip().casefold()
    for idx, row in enumerate(rows or [], start=1):
        row = list(row or [])
        if preferred_col is not None:
            if preferred_col < len(row) and str(row[preferred_col] or '').strip().casefold() == needle:
                return idx
            continue
        for value in row[:3]:
            if str(value or '').strip().casefold() == needle:
                return idx
    return 0

def _v167_find_label_last(rows, label: str, preferred_col: int | None=None):
    needle = str(label).strip().casefold()
    for idx in range(len(rows or []), 0, -1):
        row = list((rows or [])[idx - 1] or [])
        if preferred_col is not None:
            if preferred_col < len(row) and str(row[preferred_col] or '').strip().casefold() == needle:
                return idx
            continue
        for value in row[:3]:
            if str(value or '').strip().casefold() == needle:
                return idx
    return 0

def _v167_thuwed_bounds(day_key: str) -> tuple[str, str]:
    base = _v167_datetime.strptime(str(day_key)[:10], '%Y-%m-%d')
    start = base - _v167_timedelta(days=(base.weekday() - 3) % 7)
    end = start + _v167_timedelta(days=6)
    return (start.strftime('%Y-%m-%d'), end.strftime('%Y-%m-%d'))

def _v167_period_title(start_key: str, end_key: str) -> str:
    start = _v167_datetime.strptime(str(start_key)[:10], '%Y-%m-%d')
    end = _v167_datetime.strptime(str(end_key)[:10], '%Y-%m-%d')
    if start.year == end.year and start.month == end.month:
        return f'{start:%d}-{end:%d.%m.%y}'
    if start.year == end.year:
        return f'{start:%d.%m}-{end:%d.%m.%y}'
    return f'{start:%d.%m.%y}-{end:%d.%m.%y}'

def _canon_v151_context_bounds__001(chat_id: int, ctx: dict | None=None) -> tuple[str, str]:
    ctx2 = dict(ctx or (globals().get('_v151_context', lambda: {})() or {}))
    mode = str(ctx2.get('mode') or 'all').replace('csv_', '').replace('xlsx_', '')
    if str(ctx2.get('kind') or 'period') != 'exact' and mode == 'wedthu':
        return _v167_thuwed_bounds(str(ctx2.get('day_key') or today_key())[:10])
    if callable(_V167_BASE_V151_CONTEXT_BOUNDS):
        return _V167_BASE_V151_CONTEXT_BOUNDS(chat_id, ctx2)
    return (str(ctx2.get('day_key') or today_key())[:10], str(ctx2.get('day_key') or today_key())[:10])

def _canon_period_export_bounds__001(store: dict, mode: str, day_key: str) -> tuple[str, str]:
    normalized = str(mode or 'all').replace('csv_', '').replace('xlsx_', '')
    if normalized == 'wedthu':
        return _v167_thuwed_bounds(day_key)
    if callable(_V167_BASE_PERIOD_BOUNDS):
        return _V167_BASE_PERIOD_BOUNDS(store, mode, day_key)
    return (day_key, day_key)

def _canon_period_export_rows__001(chat_id: int, mode: str, day_key: str):
    if callable(_V167_BASE_PERIOD_ROWS):
        rows, label = _V167_BASE_PERIOD_ROWS(chat_id, mode, day_key)
    else:
        rows, label = ([], 'за всё время')
    normalized = str(mode or 'all').replace('csv_', '').replace('xlsx_', '')
    if normalized == 'wedthu':
        label = ('USD ' if str(label).startswith('USD ') else '') + 'Чт–Ср'
    return (rows, label)

def _canon_send_csv_for_chat_to__001(recipient_chat_id: int, target_chat_id: int, mode: str, day_key: str):
    if str(mode or '').replace('csv_', '') == 'wedthu':
        return send_export_for_chat_to(int(recipient_chat_id), int(target_chat_id), 'wedthu', day_key, 'csv')
    if callable(_V167_BASE_SEND_CSV_FOR_CHAT):
        return _V167_BASE_SEND_CSV_FOR_CHAT(recipient_chat_id, target_chat_id, mode, day_key)

def _canon_send_csv_wedthu__001(chat_id: int, day_key: str):
    return send_export_for_chat_to(int(chat_id), int(chat_id), 'wedthu', day_key, 'csv')

def _canon_v151_categories__001(chat_id: int, records: list[dict]) -> list[str]:
    store = get_chat_store(int(chat_id))
    used = []
    for rec in records or []:
        try:
            amount = float(rec.get('_v151_amount') or 0)
        except Exception:
            amount = 0.0
        if amount >= 0:
            continue
        note = str(rec.get('_v151_note') or '')
        try:
            category = resolve_expense_category(note, store)
            override_slug = str(rec.get('category_override_slug') or '').strip()
            if override_slug:
                category = get_category_by_slug(override_slug, store) or category
        except Exception:
            category = 'прочие'
        category = str(category or 'прочие')
        if category not in used:
            used.append(category)
    try:
        categories = list(get_ordered_category_names(include_all=True, cats={x: 0 for x in used}, store=store) or [])
    except Exception:
        categories = []
    for cat in used:
        if cat not in categories:
            categories.append(cat)
    return categories or ['прочие']

def _v167_formulaize_simple(rows: list[list], compact: bool, chat_id: int, currency: str):
    rows = _v167_copy.deepcopy(rows or [])
    label_col = 0 if compact else 1
    opening_row = _v167_find_label(rows, 'Остаток с прошлого раза', label_col)
    income_row = _v167_find_label_last(rows, 'Приход за период', label_col)
    expense_row = _v167_find_label_last(rows, 'Расход за период', label_col)
    closing_row = _v167_find_label_last(rows, 'Остаток на руках', label_col)
    reserve_row = _v167_find_label_last(rows, 'Гомонковые', label_col)
    turnover_row = _v167_find_label_last(rows, 'Остаток в обороте', label_col)
    if not (opening_row and income_row and expense_row and closing_row):
        return rows
    data_start = opening_row + 2
    data_end = max(data_start, income_row - 2)

    if not compact:
        # v258 hotfix3: one signed amount column C, but only simple locale-safe
        # formulas (same style as ARS): SUM(range), direct cell refs and arithmetic.
        # No SUMIF/FILTER/locale-dependent argument separators.
        col = 'C'
        while len(rows[income_row - 1]) < 3: rows[income_row - 1].append('')
        while len(rows[expense_row - 1]) < 3: rows[expense_row - 1].append('')
        while len(rows[closing_row - 1]) < 3: rows[closing_row - 1].append('')

        positive_rows = []
        negative_rows = []
        for _r in range(int(data_start), int(data_end) + 1):
            _row = list(rows[_r - 1] or []) if 0 < _r <= len(rows) else []
            _amount = _v167_cached(_row[2] if len(_row) > 2 else 0)
            if _amount > 0:
                positive_rows.append(_r)
            elif _amount < 0:
                negative_rows.append(_r)

        def _simple_sum_terms(_row_numbers):
            nums = sorted({int(x) for x in (_row_numbers or []) if int(x) > 0})
            if not nums:
                return []
            runs = []
            start = prev = nums[0]
            for cur in nums[1:]:
                if cur == prev + 1:
                    prev = cur
                    continue
                runs.append((start, prev))
                start = prev = cur
            runs.append((start, prev))
            terms = []
            for a, b in runs:
                terms.append(f'{col}{a}' if a == b else f'SUM({col}{a}:{col}{b})')
            return terms

        _income_terms = _simple_sum_terms(positive_rows)
        _expense_terms = _simple_sum_terms(negative_rows)
        _income_formula = '+'.join(_income_terms) if _income_terms else '0'
        _expense_formula = ''.join(f'-{term}' for term in _expense_terms) if _expense_terms else '0'

        rows[income_row - 1][2] = _v167_formula(_income_formula, rows[income_row - 1][2])
        rows[expense_row - 1][2] = _v167_formula(_expense_formula, rows[expense_row - 1][2])
        rows[closing_row - 1][2] = _v167_formula(f'C{opening_row}+C{income_row}-C{expense_row}', rows[closing_row - 1][2])
        if reserve_row and turnover_row:
            while len(rows[turnover_row - 1]) < 3: rows[turnover_row - 1].append('')
            rows[turnover_row - 1][2] = _v167_formula(f'C{closing_row}-C{reserve_row}', rows[turnover_row - 1][2])
        products_row = _v167_find_label_last(rows, 'Продукты', label_col)
        metric_row = _v167_find_label_last(rows, 'Расход еды на человека в сутки', label_col)
        if str(currency).lower() == 'ars' and products_row and metric_row:
            try:
                start_key, end_key = _v151_context_bounds(int(chat_id))
                records = _v151_records_in_context(int(chat_id), 'ars', _v151_context())
                _products, _metric, days, rate = _v151_food_metric(int(chat_id), records, start_key, end_key)
                if float(rate or 0) > 0:
                    rows[metric_row - 1][2] = _v167_formula(f'C{products_row}/({max(1, int(days))}*5*{float(rate):g})', rows[metric_row - 1][2])
            except Exception:
                pass
        return rows

    # Compact legacy layout remains split B/C.
    income_col, expense_col = 2, 3
    ic, ec = (_v167_col(income_col), _v167_col(expense_col))
    rows[income_row - 1][income_col - 1] = _v167_formula(f'SUM({ic}{data_start}:{ic}{data_end})', rows[income_row - 1][income_col - 1])
    rows[expense_row - 1][expense_col - 1] = _v167_formula(f'SUM({ec}{data_start}:{ec}{data_end})', rows[expense_row - 1][expense_col - 1])
    rows[closing_row - 1][income_col - 1] = _v167_formula(f'{ic}{opening_row}+{ic}{income_row}-{ec}{expense_row}', rows[closing_row - 1][income_col - 1])
    if reserve_row and turnover_row:
        rows[turnover_row - 1][income_col - 1] = _v167_formula(f'{ic}{closing_row}-{ic}{reserve_row}', rows[turnover_row - 1][income_col - 1])
    return rows

def _v167_formulaize_category(rows: list[list], chat_id: int, currency: str):
    rows = _v167_copy.deepcopy(rows or [])
    opening_row = _v167_find_label(rows, 'Остаток с прошлого раза', 1)
    sums_row = _v167_find_label_last(rows, 'Сумма по статьям', 1)
    expense_row = _v167_find_label_last(rows, 'Расход', 1)
    income_row = _v167_find_label_last(rows, 'Приход', 1)
    closing_row = _v167_find_label_last(rows, 'Остаток на руках', 1)
    reserve_row = _v167_find_label_last(rows, 'Гомонковые', 1)
    turnover_row = _v167_find_label_last(rows, 'Остаток в обороте', 1)
    header_row = 0
    for i, row in enumerate(rows, start=1):
        if len(row or []) >= 3 and str(row[0] or '').strip().casefold() == 'дата' and (str(row[1] or '').strip().casefold() == 'описание'):
            header_row = i
            break
    if not (opening_row and sums_row and expense_row and income_row and closing_row and header_row):
        return rows
    max_cols = max((len(r or []) for r in rows), default=3)
    data_start = opening_row + 2
    data_end = max(data_start, sums_row - 2)
    for col in range(3, max_cols + 1):
        letter = _v167_col(col)
        old = rows[sums_row - 1][col - 1] if col - 1 < len(rows[sums_row - 1]) else 0
        while len(rows[sums_row - 1]) < max_cols:
            rows[sums_row - 1].append('')
        rows[sums_row - 1][col - 1] = _v167_formula(f'SUM({letter}{data_start}:{letter}{data_end})', old)
    last_letter = _v167_col(max_cols)
    rows[expense_row - 1][2] = _v167_formula(f'SUM(D{sums_row}:{last_letter}{sums_row})', rows[expense_row - 1][2])
    rows[income_row - 1][2] = _v167_formula(f'C{sums_row}', rows[income_row - 1][2])
    rows[closing_row - 1][2] = _v167_formula(f'C{opening_row}+C{income_row}-C{expense_row}', rows[closing_row - 1][2])
    if reserve_row and turnover_row:
        rows[turnover_row - 1][2] = _v167_formula(f'C{closing_row}-C{reserve_row}', rows[turnover_row - 1][2])
    if str(currency).lower() == 'ars':
        products_row = _v167_find_label_last(rows, 'Продукты', 1)
        metric_row = _v167_find_label_last(rows, 'Расход еды на человека в сутки', 1)
        product_col = 0
        header = list(rows[header_row - 1] or [])
        for idx, value in enumerate(header, start=1):
            if 'продукт' in str(value or '').casefold():
                product_col = idx
                break
        if products_row and product_col >= 4:
            rows[products_row - 1][2] = _v167_formula(f'{_v167_col(product_col)}{sums_row}', rows[products_row - 1][2])
        if products_row and metric_row:
            try:
                start_key, end_key = _v151_context_bounds(int(chat_id))
                records = _v151_records_in_context(int(chat_id), 'ars', _v151_context())
                _products, _metric, days, rate = _v151_food_metric(int(chat_id), records, start_key, end_key)
                if float(rate or 0) > 0:
                    rows[metric_row - 1][2] = _v167_formula(f'C{products_row}/({max(1, int(days))}*5*{float(rate):g})', rows[metric_row - 1][2])
            except Exception:
                pass
    return rows

def _canon_v151_simple_table__001(chat_id: int, currency: str, compact: bool=False):
    if not callable(_V167_BASE_V151_SIMPLE_TABLE):
        return ([], {})
    rows, annotations = _V167_BASE_V151_SIMPLE_TABLE(chat_id, currency, compact=compact)
    return (_v167_formulaize_simple(rows, bool(compact), int(chat_id), str(currency)), annotations)

def _canon_v151_category_table__001(chat_id: int, currency: str):
    if not callable(_V167_BASE_V151_CATEGORY_TABLE):
        return []
    rows = _V167_BASE_V151_CATEGORY_TABLE(chat_id, currency)
    return _v167_formulaize_category(rows, int(chat_id), str(currency))

def _v167_patch_xlsx_package(path: str) -> None:
    if not path or not _v167_os.path.exists(path):
        return
    tmp = path + '.v167.tmp'
    ns = 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'
    _v167_ET.register_namespace('', ns)
    with _v167_zipfile.ZipFile(path, 'r') as zin, _v167_zipfile.ZipFile(tmp, 'w', _v167_zipfile.ZIP_DEFLATED) as zout:
        for item in zin.infolist():
            raw = zin.read(item.filename)
            if item.filename == 'xl/styles.xml':
                try:
                    root = _v167_ET.fromstring(raw)
                    numfmts = root.find(f'{{{ns}}}numFmts')
                    if numfmts is None:
                        numfmts = _v167_ET.Element(f'{{{ns}}}numFmts', {'count': '1'})
                        insert_at = 0
                        root.insert(insert_at, numfmts)
                    existing = None
                    for nf in list(numfmts):
                        if nf.attrib.get('formatCode') in {'#,##0', '#,###'}:
                            existing = nf
                            break
                    if existing is None:
                        used = {int(x.attrib.get('numFmtId', '0') or 0) for x in list(numfmts)}
                        fmt_id = next((n for n in range(164, 300) if n not in used), 164)
                        _v167_ET.SubElement(numfmts, f'{{{ns}}}numFmt', {'numFmtId': str(fmt_id), 'formatCode': '#,##0'})
                    else:
                        fmt_id = int(existing.attrib.get('numFmtId', '164') or 164)
                    numfmts.set('count', str(len(list(numfmts))))
                    borders = root.find(f'{{{ns}}}borders')
                    thin_id = 0
                    if borders is not None:
                        thin_id = len(list(borders))
                        border = _v167_ET.SubElement(borders, f'{{{ns}}}border')
                        for side in ('left', 'right', 'top', 'bottom'):
                            _v167_ET.SubElement(border, f'{{{ns}}}{side}', {'style': 'thin'})
                        _v167_ET.SubElement(border, f'{{{ns}}}diagonal')
                        borders.set('count', str(len(list(borders))))
                    cell_xfs = root.find(f'{{{ns}}}cellXfs')
                    if cell_xfs is not None:
                        for xf in list(cell_xfs):
                            xf.set('numFmtId', str(fmt_id))
                            xf.set('applyNumberFormat', '1')
                            if borders is not None:
                                xf.set('borderId', str(thin_id))
                                xf.set('applyBorder', '1')
                            align = xf.find(f'{{{ns}}}alignment')
                            if align is None:
                                align = _v167_ET.SubElement(xf, f'{{{ns}}}alignment')
                            align.set('wrapText', '1')
                            align.set('vertical', 'top')
                            xf.set('applyAlignment', '1')
                    raw = _v167_ET.tostring(root, encoding='utf-8', xml_declaration=True)
                except Exception:
                    pass
            elif item.filename == 'xl/worksheets/sheet1.xml':
                try:
                    root = _v167_ET.fromstring(raw)
                    cols = root.find(f'{{{ns}}}cols')
                    if cols is not None:
                        for col in list(cols):
                            lo = int(col.attrib.get('min', '0') or 0)
                            hi = int(col.attrib.get('max', '0') or 0)
                            if lo <= 2 <= hi:
                                col.set('width', '42')
                                col.set('customWidth', '1')
                    raw = _v167_ET.tostring(root, encoding='utf-8', xml_declaration=True)
                except Exception:
                    pass
            zout.writestr(item, raw)
    _v167_os.replace(tmp, path)

def _v167_formulaize_four_week_rows(rows: list[list]) -> list[list]:
    """Restore formulas in the legacy 4-week Thursday-Wednesday workbook too."""
    out = _v167_copy.deepcopy(rows or [])
    i = 0
    while i < len(out):
        row = list(out[i] or [])
        if str(row[0] if row else '').strip().casefold() != 'неделя':
            i += 1
            continue
        header_idx = i + 1
        opening_idx = i + 2
        if opening_idx >= len(out):
            break
        total_idx = 0
        j = opening_idx + 1
        while j < len(out):
            first = str((out[j] or [''])[0] if out[j] or [] else '').strip().casefold()
            if first == 'итог:':
                total_idx = j
                break
            if first == 'неделя':
                break
            j += 1
        if not total_idx:
            i += 1
            continue
        header = list(out[header_idx] or [])
        max_cols = max(2, len(header))
        data_start = opening_idx + 2
        data_end = max(data_start, total_idx)
        total_excel = total_idx + 1
        while len(out[total_idx]) < max_cols:
            out[total_idx].append('')
        out[total_idx][1] = _v167_formula(f'SUM(B{data_start}:B{data_end})', out[total_idx][1])
        for col in range(4, max_cols + 1):
            letter = _v167_col(col)
            out[total_idx][col - 1] = _v167_formula(f'SUM({letter}{data_start}:{letter}{data_end})', out[total_idx][col - 1])
        expense_idx = total_idx + 1
        closing_idx = total_idx + 2
        reserve_idx = total_idx + 3
        turnover_idx = total_idx + 4
        if expense_idx < len(out):
            while len(out[expense_idx]) < 2:
                out[expense_idx].append('')
            out[expense_idx][1] = _v167_formula(f'SUM(D{total_excel}:{_v167_col(max_cols)}{total_excel})', out[expense_idx][1])
        if closing_idx < len(out):
            while len(out[closing_idx]) < 2:
                out[closing_idx].append('')
            out[closing_idx][1] = _v167_formula(f'B{opening_idx + 1}+B{total_excel}-B{expense_idx + 1}', out[closing_idx][1])
        if turnover_idx < len(out) and reserve_idx < len(out):
            while len(out[turnover_idx]) < 2:
                out[turnover_idx].append('')
            out[turnover_idx][1] = _v167_formula(f'B{closing_idx + 1}-B{reserve_idx + 1}', out[turnover_idx][1])
        product_col = 0
        for col_idx, name in enumerate(header, start=1):
            if 'продукт' in str(name or '').casefold():
                product_col = col_idx
                break
        next_week = len(out)
        k = turnover_idx + 1
        while k < len(out):
            first = str((out[k] or [''])[0] if out[k] or [] else '').strip().casefold()
            if first == 'неделя':
                next_week = k
                break
            if first == 'расход еды на человека в сутки' and product_col >= 4:
                cached_metric = _v167_cached((out[k] or ['', 0])[1] if len(out[k] or []) > 1 else 0)
                cached_product = _v167_cached(out[total_idx][product_col - 1])
                if cached_metric > 0 and cached_product > 0:
                    denom = cached_product / cached_metric
                    out[k][1] = _v167_formula(f'{_v167_col(product_col)}{total_excel}/{denom:.12g}', cached_metric)
                break
            k += 1
        i = next_week if next_week > i else i + 1
    return out

def _canon_write_simple_xlsx__001(path: str, rows: list[list], sheet_name: str='Данные') -> None:
    # R10: even the emergency/local simple XLSX path uses the original vys-262
    # colored financial palette. Normal exports run on Worker, but fallback files
    # must look the same instead of reverting to a black/white workbook.
    if callable(_V167_BASE_WRITE_TABL):
        try:
            styles, comments, freeze_rows, widths = _canon_modern_simple_excel_styles_comments__001(rows)
            _V167_BASE_WRITE_TABL(path, rows, styles, sheet_name=sheet_name, comments=comments, freeze_rows=freeze_rows, widths=widths, annotation_mode='notes')
            _v167_patch_xlsx_package(path)
            return
        except Exception:
            pass
    if not callable(_V167_BASE_WRITE_SIMPLE):
        raise RuntimeError('XLSX writer is unavailable')
    _V167_BASE_WRITE_SIMPLE(path, rows, sheet_name=sheet_name)
    _v167_patch_xlsx_package(path)

def _canon_write_tabl_lsx_xlsx__001(path: str, rows: list[list], styles: list[list], sheet_name: str='4 недели', comments: dict | None=None, freeze_rows: int=3, widths: list[float] | None=None, annotation_mode: str | None='notes') -> None:
    if not callable(_V167_BASE_WRITE_TABL):
        raise RuntimeError('Styled XLSX writer is unavailable')
    widths2 = list(widths or [])
    if len(widths2) >= 2:
        widths2[1] = max(42, float(widths2[1] or 0))
    rows2 = _v167_formulaize_four_week_rows(rows) if str(sheet_name or '').strip().casefold() == '4 недели' else rows
    _V167_BASE_WRITE_TABL(path, rows2, styles, sheet_name=sheet_name, comments=comments, freeze_rows=freeze_rows, widths=widths2 or widths, annotation_mode=annotation_mode)
    _v167_patch_xlsx_package(path)

def _v167_google_schedule_cfg(target_chat_id: int, create: bool=True) -> dict:
    store = get_chat_store(int(target_chat_id))
    cfg = store.get('google_thuwed_v167')
    if not isinstance(cfg, dict):
        if not create:
            return {}
        cfg = {}
        store['google_thuwed_v167'] = cfg
    cfg.setdefault('enabled', True)
    cfg.setdefault('time', '05:01')
    if str(cfg.get('mode') or '') not in {'manual', 'change', 'm15', 'h1', 'd0001', 'd0501'}:
        if not bool(cfg.get('enabled', True)):
            cfg['mode'] = 'manual'
        else:
            cfg['mode'] = 'd0001' if str(cfg.get('time') or '05:01') == '00:01' else 'd0501'
    cfg['enabled'] = str(cfg.get('mode')) != 'manual'
    if str(cfg.get('mode')) == 'd0001':
        cfg['time'] = '00:01'
    if str(cfg.get('mode')) == 'd0501':
        cfg['time'] = '05:01'
    legacy_schema = int(cfg.get('schema', 1) or 1)
    cfg.setdefault('last_run_key', '')
    if 'last_success_key' not in cfg:
        cfg['last_success_key'] = '' if legacy_schema < 3 else str(cfg.get('last_run_key') or '')
    cfg.setdefault('last_attempt_key', '')
    cfg.setdefault('last_attempt_at', '')
    cfg.setdefault('pending_run_key', '')
    cfg.setdefault('pending_since_ts', 0.0)
    cfg.setdefault('retry_count', 0)
    cfg.setdefault('next_retry_ts', 0.0)
    cfg.setdefault('last_target_day', '')
    cfg.setdefault('last_target_period', '')
    cfg.setdefault('last_ok_at', '')
    cfg.setdefault('last_error', '')
    cfg.setdefault('last_period', '')
    cfg['schema'] = max(3, int(cfg.get('schema', 1) or 1))
    return cfg

def _v167_persist_schedule(target_chat_id: int):
    """Persist only the changed settings on the callback thread.

    v176 measurements exposed that the old implementation rebuilt JSON + CSV +
    optional XLSX for a simple Google schedule toggle.  SQLite is the immediate
    source of truth; external/config backup remains debounced in the background.
    """
    cid = int(target_chat_id)
    started = _v167_time.monotonic()
    try:
        trace = globals().get('r25_trace_stage')
        if callable(trace): trace('SQLITE_GOOGLE_SETTINGS_START', emit=False)
        store = get_chat_store(cid)
        if bool(globals().get('LOWRAM_ENABLED', False)):
            payload = _lowram_store_meta_payload(store)
        else:
            payload = dict(store)
        # R26: google_thuwed_v167 lives in the hot chat meta row. Do not call
        # save_data() here: that serializes root state and flushes every loaded
        # cold finance field although this callback changed only one setting.
        SQLITE.save_chat(cid, payload)
        elapsed = _v167_time.monotonic() - started
        if callable(trace): trace('SQLITE_GOOGLE_SETTINGS_DONE', elapsed, emit=elapsed >= 0.020)
    except Exception as exc:
        try:
            log_error(f'R26 google schedule SQLite meta persist {cid}: {exc}')
        except Exception:
            pass
    try:
        schedule_config_backup_for_chats(cid, delay=2.0)
    except Exception:
        pass
    try:
        stage = globals().get('v177_perf_stage')
        if callable(stage):
            stage('sqlite_google_settings', _v167_time.monotonic() - started)
    except Exception:
        pass

def _canon_add_export_period_rows__001(kb, day_key: str, prefix: str, owner_day_key: str | None=None, target_chat_id: int | None=None):
    periods = [('📅 День', 'day'), ('🗓 Неделя', 'week'), ('📆 Месяц', 'month'), ('📊 Чт–Ср', 'wedthu'), ('📂 Всё время', 'all')]
    scope = 'fv' if prefix == 'fv' else 'd'
    target = int(target_chat_id or (OWNER_ID or 0))
    owner_day = str(owner_day_key or day_key)
    for label, mode in periods:
        if prefix == 'fv':
            csv_cb = f'fv:{target}:{day_key}:csv_{mode}:{owner_day}'
        else:
            csv_action = 'csv_all_real' if mode == 'all' else f'csv_{mode}'
            csv_cb = f'd:{day_key}:{csv_action}'
        xlsx_cb = export_callback(f"exp_style_period:{scope}:{(target if prefix == 'fv' else 0)}:{mode}:xlsx:{day_key}:{owner_day}")
        xlsxstat_cb = export_callback(f"exp_style_period:{scope}:{(target if prefix == 'fv' else 0)}:{mode}:xlsxstat:{day_key}:{owner_day}")
        kb.row(IB(label, callback_data='none'), IB('CSV', callback_data=csv_cb), IB('Excel', callback_data=xlsx_cb), IB('Excel статьи', callback_data=xlsxstat_cb))
    if target:
        cfg = _v167_google_schedule_cfg(target)
        mode = str(cfg.get('mode') or 'd0501')
        enabled = mode != 'manual'
        selected = str(cfg.get('time') or '05:01') if mode in {'d0001', 'd0501'} else ''
        kb.row(IB(('✅ ' if enabled else '⬜ ') + 'Google Чт–Ср авто', callback_data=f'v167:gtoggle:{target}'), IB(('✅ ' if selected == '00:01' else '') + '00:01', callback_data=f'v167:gtime:{target}:0001'), IB(('✅ ' if selected == '05:01' else '') + '05:01', callback_data=f'v167:gtime:{target}:0501'))
        kb.row(IB('☁️ Обновить лист Чт–Ср сейчас', callback_data=f'v167:gnow:{target}'))

def _v167_google_color_format(row, r_idx: int, c_idx: int, max_cols: int, layout: str, annotations: dict):
    value = row[c_idx - 1] if c_idx - 1 < len(row) else ''
    row_is_blank = not any((_excel_nonempty(v) for v in row))
    first = str(row[0] if row else '').strip().casefold()
    second = str(row[1] if len(row) > 1 else '').strip().casefold()
    fmt = {'verticalAlignment': 'TOP', 'wrapStrategy': 'CLIP' if c_idx == 2 else 'WRAP', 'borders': {side: {'style': 'SOLID', 'color': {'red': 0.65, 'green': 0.65, 'blue': 0.65}} for side in ('top', 'bottom', 'left', 'right')}}
    if isinstance(value, (int, float)) or (isinstance(value, dict) and value.get('formula')):
        fmt['numberFormat'] = {'type': 'NUMBER', 'pattern': '#,##0'}
    if first == 'ars':
        fmt.update({'textFormat': {'bold': True}, 'backgroundColor': {'red': 0.78, 'green': 0.94, 'blue': 0.81}})
    elif first == 'usd':
        fmt.update({'textFormat': {'bold': True}, 'backgroundColor': {'red': 0.72, 'green': 0.86, 'blue': 1.0}})
    elif first in {'дата', 'date'}:
        fmt.update({'textFormat': {'bold': True}, 'backgroundColor': _google_category_fill(c_idx - 1)})
    elif row_is_blank:
        fmt['backgroundColor'] = {'red': 1.0, 'green': 0.6, 'blue': 0.0}
    elif first in {'расход', 'сумма по статьям'} or second in {'расход', 'сумма по статьям'}:
        fmt.update({'textFormat': {'bold': True}, 'backgroundColor': {'red': 1.0, 'green': 0.55, 'blue': 0.55}})
    elif first in {'приход', 'приход за период'} or second in {'приход', 'приход за период'}:
        fmt.update({'textFormat': {'bold': True}, 'backgroundColor': {'red': 0.55, 'green': 0.78, 'blue': 1.0}})
    elif first in {'остаток с прошлого раза', 'остаток на руках', 'гомонковые', 'остаток в обороте'} or second in {'остаток с прошлого раза', 'остаток на руках', 'гомонковые', 'остаток в обороте'}:
        fmt.update({'textFormat': {'bold': True}, 'backgroundColor': {'red': 0.55, 'green': 0.85, 'blue': 0.55}})
    elif first == 'расход еды на человека в сутки' or second == 'расход еды на человека в сутки':
        fmt.update({'textFormat': {'bold': True}, 'backgroundColor': {'red': 0.74, 'green': 0.82, 'blue': 1.0}})
    elif layout == 'category' and c_idx >= 4 and _excel_nonempty(value):
        fmt['backgroundColor'] = _google_category_fill(c_idx - 1)
    return fmt

def _v244_google_try_reconcile_stale_restore_gate() -> bool:
    """Repair only the known stale CONFIG-binding gate after a verified MEGA restore.

    This deliberately does NOT waive a failed/missing database restore.  It is limited
    to the case where Data Constitution verifies the recovered data but the old config
    generation/hash binding is stale.
    """
    try:
        state = globals().get('_RUNTIME_STATE') or {}
        if not isinstance(state, dict) or not bool(state.get('restore_attempted')) or state.get('restore_ok') is not False:
            return False
        detail = str(state.get('restore_detail') or '').casefold()
        if 'config guard' not in detail and 'config binding' not in detail and ('binding mismatch' not in detail):
            return False
        if bool(globals().get('RESTORE_GUARD_ACTIVE', False)):
            return False
        q = globals().get('constitution_quarantine_active')
        if callable(q) and bool(q()):
            return False
        verify = globals().get('constitution_boot_verify_after_restore')
        if callable(verify):
            rep = verify() or {}
            if not bool(rep.get('ok')):
                return False
        bind = globals().get('config_guard_bind_recovered_state_v242')
        if not callable(bind):
            return False
        bind()
        boot_verify = globals().get('config_guard_boot_verify_v234')
        if callable(boot_verify):
            rep2 = boot_verify() or {}
            if not bool(rep2.get('ok')):
                return False
        heal = globals().get('_v243_mark_runtime_restore_healthy')
        if callable(heal):
            heal('google_config_binding_reconciled_v244', remote_confirmed=False, generation='RECOVERED')
        try:
            bot_journal('google_restore_gate_reconciled_v244', int(OWNER_ID or 0) or None, 'verified data + config binding accepted')
        except Exception:
            pass
        return True
    except Exception as exc:
        try:
            bot_journal('google_restore_gate_reconcile_failed_v244', int(OWNER_ID or 0) or None, str(exc)[:300], 'WARN')
        except Exception:
            pass
        return False

def _v244_google_values_equivalent(want, got) -> bool:
    """Compare Google user-entered values semantically, not by fragile JSON type."""
    if want == got:
        return True
    try:
        wt, wv = want
        gt, gv = got
    except Exception:
        return False
    if wt == gt == 'formula':
        # v251: Google canonicalizes SUM(C38:C38) -> SUM(C38). Treat that
        # server-side rewrite as equivalent instead of failing the whole sync.
        try:
            return _v251_google_formula_canonical(wv).replace('\r\n', '\n') == _v251_google_formula_canonical(gv).replace('\r\n', '\n')
        except Exception:
            return str(wv).strip().replace('\r\n', '\n') == str(gv).strip().replace('\r\n', '\n')
    if wt == gt == 'bool':
        return bool(wv) == bool(gv)
    if wt == 'string' and gt == 'string':
        return str(wv).replace('\r\n', '\n').strip() == str(gv).replace('\r\n', '\n').strip()
    if {wt, gt}.issubset({'number', 'string'}):

        def _num(v):
            s = str(v).replace('\xa0', '').replace(' ', '').replace(',', '.').strip()
            if s == '':
                return 0.0
            return float(s)
        try:
            return abs(_num(wv) - _num(gv)) <= 1e-09
        except Exception:
            pass
    if str(wv or '').strip() == '' and str(gv or '').strip() == '':
        return True
    return False

def _v244_google_resolve_or_create_spreadsheet(tid: str) -> str:
    try:
        return _google_spreadsheet_id(tenant_id=tid)
    except Exception:
        creator = globals().get('tenant_google_create_spreadsheet')
        if not callable(creator):
            raise
        row = tenant_get(tid) if callable(globals().get('tenant_get')) else {}
        creator(tid, f"Финансы · {(row or {}).get('name') or tid}")
        return _google_spreadsheet_id(tenant_id=tid)

def _v239_google_recovery_write_gate() -> tuple[bool, str]:
    """Never let an unhealthy boot/restore overwrite a previously good Google sheet."""
    _v244_google_try_reconcile_stale_restore_gate()
    try:
        gate = globals().get('v239_external_durable_write_allowed')
        if callable(gate):
            ok, why = gate()
            if not ok:
                return (False, str(why or 'durable recovery gate'))
    except Exception:
        pass
    try:
        state = globals().get('_RUNTIME_STATE') or {}
        if isinstance(state, dict) and bool(state.get('restore_attempted')) and (state.get('restore_ok') is False):
            return (False, 'восстановление после deploy не прошло проверку')
    except Exception:
        pass
    try:
        q = globals().get('constitution_quarantine_active')
        if callable(q) and bool(q()):
            return (False, 'DATA CONSTITUTION/restore guard активен')
    except Exception:
        pass
    return (True, 'ok')

def _v239_google_plain_user_value(cell: dict):
    uv = (cell or {}).get('userEnteredValue') or {}
    if not isinstance(uv, dict):
        return ''
    if 'formulaValue' in uv:
        return ('formula', str(uv.get('formulaValue') or ''))
    if 'numberValue' in uv:
        try:
            return ('number', round(float(uv.get('numberValue') or 0.0), 10))
        except Exception:
            return ('number', str(uv.get('numberValue') or ''))
    if 'boolValue' in uv:
        return ('bool', bool(uv.get('boolValue')))
    return ('string', str(uv.get('stringValue') or ''))

def _v239_google_target_plain(value):
    uv = _google_cell_value(value)
    return _v239_google_plain_user_value({'userEnteredValue': uv})

def _v239_google_sync_meta_key(tid: str, target_chat_id: int, tab_title: str) -> str:
    raw = f'{tid}:{int(target_chat_id)}:{tab_title}'
    return hashlib.sha256(raw.encode('utf-8')).hexdigest()[:32]

def _v261_google_upsert_previous(tab_title: str, rows: list[list], target_chat_id: int, layout: str = "category", annotations_override: dict | None = None) -> str:
    """v239 incremental upsert for the stable Thu-Wed tab.

    The old implementation cleared the entire sheet before every rewrite. v239 reads the
    bot-managed range, updates only changed rows/cells, appends newly appearing rows, and
    clears only a previously managed stale tail *after* the new content was verified.
    """
    gate_ok, gate_reason = _v239_google_recovery_write_gate()
    if not gate_ok:
        raise RuntimeError("Google sync blocked v239: " + gate_reason)
    target_chat_id = int(target_chat_id)
    tid = _v149_tenant_id(None, target_chat_id) if callable(globals().get("_v149_tenant_id")) else tenant_id_for_chat(target_chat_id, create=False)
    if callable(globals().get("_v149_chat_belongs_to_tenant")) and not _v149_chat_belongs_to_tenant(target_chat_id, tid):
        raise RuntimeError("Google export blocked: target chat is not connected to this space")
    cfg = tenant_google_config(tid)
    if not bool((cfg.get("export_settings") or {}).get("sheet_enabled", True)):
        raise RuntimeError("Выгрузка в Google Sheets выключена для этого пространства")
    with tenant_google_context(tid):
        token = _google_access_token(); info = _google_service_account_info(); spreadsheet_id = _v244_google_resolve_or_create_spreadsheet(str(tid))
        service_email = str(info.get("client_email") or "")
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        meta = _google_request_guarded("v239_metadata", requests.get, f"https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}", headers=headers, params={"fields": "spreadsheetId,properties.title,sheets.properties(sheetId,title,gridProperties)"}, timeout=45, attempts=2)
        if meta.status_code >= 300:
            if meta.status_code in (401,403):
                raise RuntimeError(f"Google Sheets access denied. Добавьте {service_email} как Редактор.")
            raise RuntimeError(f"Google Sheets metadata {meta.status_code}: {meta.text[:500]}")
        payload = meta.json(); sheet_id = None; grid_rows=0; grid_cols=0
        for sh in payload.get("sheets") or []:
            props = sh.get("properties") or {}
            if str(props.get("title") or "") == tab_title:
                sheet_id = int(props.get("sheetId")); gp=props.get("gridProperties") or {}; grid_rows=int(gp.get("rowCount") or 0); grid_cols=int(gp.get("columnCount") or 0); break
        max_cols = max((len(r or []) for r in rows), default=1); row_count = max(100, len(rows)+20); col_count=max(26,max_cols+3)
        created_new = False
        if sheet_id is None:
            add = _google_request_guarded("v239_add_sheet", requests.post, f"https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}:batchUpdate", headers=headers, json={"requests":[{"addSheet":{"properties":{"title":tab_title,"gridProperties":{"rowCount":row_count,"columnCount":col_count,"frozenRowCount":2}}}}]}, timeout=60, attempts=1)
            if add.status_code >= 300:
                raise RuntimeError(f"Google Sheets add tab {add.status_code}: {add.text[:500]}")
            sheet_id = int(add.json()["replies"][0]["addSheet"]["properties"]["sheetId"]); grid_rows=row_count; grid_cols=col_count; created_new=True
        annotations = dict(annotations_override or {})
        if not annotations and layout == "category":
            try:
                _styles, annotations, _freeze, _widths = _modern_category_excel_styles_comments(rows)
            except Exception:
                annotations = {}
        cell_rows=[]
        for r_idx,row0 in enumerate(rows,start=1):
            row=list(row0 or []); vals=[]
            for c_idx in range(1,max_cols+1):
                value=row[c_idx-1] if c_idx-1<len(row) else ""
                cell={"userEnteredValue":_google_cell_value(value),"userEnteredFormat":_v167_google_color_format(row,r_idx,c_idx,max_cols,layout,annotations)}
                note=str(annotations.get((r_idx,c_idx)) or "").strip()
                if note: cell["note"]=note
                vals.append(cell)
            cell_rows.append({"values":vals})

        # Read only the currently managed-sized area. This lets us diff values/notes and
        # avoids a destructive clear-first cycle.
        sync_key = _v239_google_sync_meta_key(str(tid), target_chat_id, tab_title)
        sync_meta = {}
        try: sync_meta = SQLITE.get_meta("google_sync_v239", sync_key, {}) or {}
        except Exception: sync_meta = {}
        prev_managed_rows = int((sync_meta or {}).get("managed_rows") or 0)
        prev_managed_cols = int((sync_meta or {}).get("managed_cols") or 0)
        read_rows = max(len(rows), prev_managed_rows, 1)
        read_cols = max(max_cols, prev_managed_cols, 1)
        existing_rows=[]
        try:
            escaped = str(tab_title).replace("'", "''")
            read = _google_request_guarded("v239_read_managed", requests.get, f"https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}", headers=headers, params={
                "includeGridData":"true", "ranges":f"'{escaped}'!A1:{_xlsx_col_name(read_cols)}{read_rows}",
                "fields":"sheets(data(rowData(values(userEnteredValue,note))))",
            }, timeout=60, attempts=2)
            if read.status_code < 300:
                existing_rows = (((read.json().get("sheets") or [{}])[0].get("data") or [{}])[0].get("rowData") or [])
        except Exception as exc:
            try: bot_journal("google_incremental_read_warn_v239", target_chat_id, str(exc)[:300], "WARN")
            except Exception: pass
            existing_rows=[]

        changed_indices=[]; added=0; updated=0; unchanged=0
        for idx, row0 in enumerate(rows):
            target=list(row0 or [])
            old_vals=((existing_rows[idx] or {}).get("values") or []) if idx < len(existing_rows) else []
            value_changed=False; note_changed=False
            for c in range(max_cols):
                want=_v239_google_target_plain(target[c] if c < len(target) else "")
                got=_v239_google_plain_user_value(old_vals[c] if c < len(old_vals) else {})
                if not _v244_google_values_equivalent(want, got): value_changed=True; break
            if not value_changed:
                for c in range(max_cols):
                    want_note=str(annotations.get((idx+1,c+1)) or "").strip()
                    got_note=str((old_vals[c] if c < len(old_vals) else {}).get("note") or "").strip()
                    if want_note != got_note: note_changed=True; break
            if value_changed or note_changed or created_new:
                changed_indices.append(idx)
                if idx >= len(existing_rows) or not any(_v239_google_plain_user_value(x) != ("string", "") for x in old_vals): added += 1
                else: updated += 1
            else:
                unchanged += 1

        req=[]
        if grid_rows < row_count or grid_cols < col_count:
            req.append({"updateSheetProperties":{"properties":{"sheetId":sheet_id,"gridProperties":{"rowCount":max(grid_rows,row_count),"columnCount":max(grid_cols,col_count),"frozenRowCount":2}},"fields":"gridProperties(rowCount,columnCount,frozenRowCount)"}})
        for idx in changed_indices:
            req.append({"updateCells":{"range":{"sheetId":sheet_id,"startRowIndex":idx,"endRowIndex":idx+1,"startColumnIndex":0,"endColumnIndex":max_cols},"rows":[cell_rows[idx]],"fields":"userEnteredValue,note,userEnteredFormat"}})
        # Dimensions are cheap and non-destructive; keep the old visual layout.
        req.append({"updateDimensionProperties":{"range":{"sheetId":sheet_id,"dimension":"COLUMNS","startIndex":0,"endIndex":1},"properties":{"pixelSize":95},"fields":"pixelSize"}})
        if max_cols >= 2: req.append({"updateDimensionProperties":{"range":{"sheetId":sheet_id,"dimension":"COLUMNS","startIndex":1,"endIndex":2},"properties":{"pixelSize":320},"fields":"pixelSize"}})
        if max_cols >= 3: req.append({"updateDimensionProperties":{"range":{"sheetId":sheet_id,"dimension":"COLUMNS","startIndex":2,"endIndex":max_cols},"properties":{"pixelSize":115},"fields":"pixelSize"}})
        if req:
            upd=_google_request_guarded("v239_incremental_upsert", requests.post, f"https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}:batchUpdate", headers=headers, json={"requests":req}, timeout=90, attempts=1)
            if upd.status_code >= 300:
                raise RuntimeError(f"Google Sheets incremental update {upd.status_code}: {upd.text[:500]}")

        # Verify the complete new managed range BEFORE clearing stale rows.
        escaped = str(tab_title).replace("'", "''")
        verify = _google_request_guarded("v239_verify_incremental", requests.get, f"https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}", headers=headers, params={
            "includeGridData":"true", "ranges":f"'{escaped}'!A1:{_xlsx_col_name(max_cols)}{max(1,len(rows))}",
            "fields":"sheets(data(rowData(values(userEnteredValue,note))))",
        }, timeout=60, attempts=2)
        if verify.status_code >= 300:
            raise RuntimeError(f"Google Sheets incremental verify {verify.status_code}: {verify.text[:500]}")
        vr = (((verify.json().get("sheets") or [{}])[0].get("data") or [{}])[0].get("rowData") or [])
        for idx,row0 in enumerate(rows):
            old_vals=((vr[idx] or {}).get("values") or []) if idx < len(vr) else []
            for c in range(max_cols):
                want=_v239_google_target_plain((row0 or [])[c] if c < len(row0 or []) else "")
                got=_v239_google_plain_user_value(old_vals[c] if c < len(old_vals) else {})
                if not _v244_google_values_equivalent(want, got):
                    raise RuntimeError(f"Google incremental verify mismatch row={idx+1} col={c+1}; want={want}; got={got}")

        # Only after verification may we clear the stale BOT-MANAGED tail. We never clear
        # the whole sheet and never touch rows beyond the last managed_rows marker.
        stale_tail = max(0, prev_managed_rows - len(rows))
        if stale_tail > 0:
            clear_cols=max(max_cols,prev_managed_cols,1)
            clr=_google_request_guarded("v239_clear_stale_tail", requests.post, f"https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}:batchUpdate", headers=headers, json={"requests":[{"updateCells":{"range":{"sheetId":sheet_id,"startRowIndex":len(rows),"endRowIndex":prev_managed_rows,"startColumnIndex":0,"endColumnIndex":clear_cols},"fields":"userEnteredValue,note"}}]}, timeout=60, attempts=1)
            if clr.status_code >= 300:
                raise RuntimeError(f"Google Sheets stale-tail clear {clr.status_code}: {clr.text[:500]}")

        row_hash=hashlib.sha256(json.dumps(rows,ensure_ascii=False,sort_keys=False,separators=(",",":"),default=str).encode("utf-8")).hexdigest()
        try:
            SQLITE.set_meta("google_sync_v239", sync_key, {"tab":tab_title,"tenant_id":str(tid),"chat_id":target_chat_id,"managed_rows":len(rows),"managed_cols":max_cols,"row_hash":row_hash,"synced_at":now_local().isoformat(timespec="microseconds")})
        except Exception: pass
        url=f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}/edit#gid={sheet_id}"
    try:
        tenant_google_history(tid,"thuwed_incremental_upsert_v239",tab_title,ok=True,chat_id=target_chat_id,url=url,added=added,updated=updated,unchanged=unchanged,stale_tail=stale_tail)
        tenant_google_persist(tid,"tenant_google_runtime_v239")
        try: bot_journal("google_incremental_upsert_v239",target_chat_id,f"tab={tab_title}; added={added}; updated={updated}; unchanged={unchanged}; stale_tail={stale_tail}")
        except Exception: pass
    except Exception:
        pass
    return url

def _v261_google_upsert_fixed(tab_title: str, rows: list[list], target_chat_id: int, layout: str='category', annotations_override: dict | None=None) -> str:
    """v254 non-destructive upsert for the stable Thu-Wed tab.

    Contract for an existing sheet:
    - bot values may be refreshed inside the previously managed table;
    - existing CellData.note is NEVER cleared/replaced;
    - existing userEnteredFormat is NEVER replaced (manual colors/styles survive);
    - when the bot table grows, real rows are inserted at the detected logical
      insertion point (with a safe boundary fallback), and columns at the previous
      managed boundary, so user notes/colors and content below/right are shifted,
      not overwritten;
    - a shrinking table never performs a blind tail clear.  From v252 onward a
      stored value snapshot lets us clear only values that are still exactly the
      previous bot-owned values, while notes/formatting remain untouched.
    """
    gate_ok, gate_reason = _v239_google_recovery_write_gate()
    if not gate_ok:
        raise RuntimeError('Google sync blocked v255: ' + gate_reason)
    target_chat_id = int(target_chat_id)
    tid = _v149_tenant_id(None, target_chat_id) if callable(globals().get('_v149_tenant_id')) else tenant_id_for_chat(target_chat_id, create=False)
    if callable(globals().get('_v149_chat_belongs_to_tenant')) and (not _v149_chat_belongs_to_tenant(target_chat_id, tid)):
        raise RuntimeError('Google export blocked: target chat is not connected to this space')
    cfg = tenant_google_config(tid)
    if not bool((cfg.get('export_settings') or {}).get('sheet_enabled', True)):
        raise RuntimeError('Выгрузка в Google Sheets выключена для этого пространства')

    def _plain_json(value):
        p = _v239_google_target_plain(value)
        return [p[0], p[1]]

    def _plain_from_json(value):
        try:
            if isinstance(value, (list, tuple)) and len(value) == 2:
                return (str(value[0]), value[1])
        except Exception:
            pass
        return ('string', '')

    def _is_blank_plain(value) -> bool:
        try:
            t, v = value
            return t == 'string' and str(v or '').strip() == ''
        except Exception:
            return True

    def _segments(cols):
        cols = sorted(set(int(c) for c in cols if int(c) >= 0))
        if not cols:
            return []
        out = []
        a = b = cols[0]
        for c in cols[1:]:
            if c == b + 1:
                b = c
            else:
                out.append((a, b + 1))
                a = b = c
        out.append((a, b + 1))
        return out

    def _identity_token(plain):
        try:
            t, v = plain
        except Exception:
            return ''
        if t == 'formula':
            return '=' + _v251_google_formula_canonical(v)
        if t == 'number':
            try:
                return f'{float(v):.12g}'
            except Exception:
                return str(v or '').strip()
        if t == 'bool':
            return 'TRUE' if bool(v) else 'FALSE'
        return str(v or '').replace('\r\n', '\n').strip()

    def _row_identity(plains):
        vals = [_identity_token(x) for x in list(plains or [])]
        first = vals[0] if len(vals) > 0 else ''
        second = vals[1] if len(vals) > 1 else ''
        if first or second:
            # In the financial sheet the first two columns are the stable row
            # identity (date/description or a summary label). Numeric/formula
            # totals are deliberately ignored so recalculation does not look
            # like a row replacement.
            return ('row', first.casefold(), second.casefold())
        if not any(vals):
            return ('blank',)
        return ('other', *(x.casefold() for x in vals[:3]))

    # v254: the generated period title is only a logical key. The actual Google
    # worksheet is pinned by immutable sheetId, so a user's manual tab rename
    # never makes the bot create a second tab or lose its ownership snapshot.
    sync_key = _v239_google_sync_meta_key(str(tid), target_chat_id, tab_title)
    try:
        sync_meta = SQLITE.get_meta('google_sync_v239', sync_key, {}) or {}
    except Exception:
        sync_meta = {}
    prev_managed_rows = int((sync_meta or {}).get('managed_rows') or 0)
    prev_managed_cols = int((sync_meta or {}).get('managed_cols') or 0)
    prev_snapshot = (sync_meta or {}).get('managed_values_v252')
    if not isinstance(prev_snapshot, list):
        prev_snapshot = []
    try:
        preferred_sheet_id_v254 = int((sync_meta or {}).get('sheet_id_v254') or 0)
    except Exception:
        preferred_sheet_id_v254 = 0

    with tenant_google_context(tid):
        token = _google_access_token()
        info = _google_service_account_info()
        spreadsheet_id = _v244_google_resolve_or_create_spreadsheet(str(tid))
        service_email = str(info.get('client_email') or '')
        headers = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}
        meta = _google_request_guarded('v252_metadata', requests.get, f'https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}', headers=headers, params={'fields': 'spreadsheetId,properties.title,sheets.properties(sheetId,title,gridProperties)'}, timeout=45, attempts=2)
        if meta.status_code >= 300:
            if meta.status_code in (401, 403):
                raise RuntimeError(f'Google Sheets access denied. Добавьте {service_email} как Редактор.')
            raise RuntimeError(f'Google Sheets metadata {meta.status_code}: {meta.text[:500]}')
        payload = meta.json()
        sheet_id = None
        actual_tab_title = str(tab_title)
        grid_rows = 0
        grid_cols = 0
        sheets_meta = list(payload.get('sheets') or [])

        # First choice: immutable sheetId saved by v254. Title is intentionally
        # ignored here because users are allowed to rename tabs freely.
        if preferred_sheet_id_v254:
            for sh in sheets_meta:
                props = sh.get('properties') or {}
                if int(props.get('sheetId') or 0) == preferred_sheet_id_v254:
                    sheet_id = int(props.get('sheetId'))
                    actual_tab_title = str(props.get('title') or tab_title)
                    gp = props.get('gridProperties') or {}
                    grid_rows = int(gp.get('rowCount') or 0)
                    grid_cols = int(gp.get('columnCount') or 0)
                    break

        # Compatibility with older builds / a tab that has never been renamed.
        if sheet_id is None:
            for sh in sheets_meta:
                props = sh.get('properties') or {}
                if str(props.get('title') or '') == tab_title:
                    sheet_id = int(props.get('sheetId'))
                    actual_tab_title = str(props.get('title') or tab_title)
                    gp = props.get('gridProperties') or {}
                    grid_rows = int(gp.get('rowCount') or 0)
                    grid_cols = int(gp.get('columnCount') or 0)
                    break

        # One-time v253 -> v254 migration for a tab renamed BEFORE v254 had a
        # chance to save sheetId. Match the previous managed snapshot against
        # the first two identity columns of existing tabs. Only a strong unique
        # match is accepted; otherwise we fail safe and create the logical tab.
        if sheet_id is None and prev_snapshot and prev_managed_rows > 0:
            try:
                import difflib as _v254_difflib
                old_plain_rows = []
                for prow in prev_snapshot[:prev_managed_rows]:
                    prow = prow if isinstance(prow, list) else []
                    old_plain_rows.append([_plain_from_json(prow[c]) if c < len(prow) else ('string', '') for c in range(min(2, max(1, prev_managed_cols)))])
                old_keys = [_row_identity(x) for x in old_plain_rows]
                scored = []
                probe_rows = max(1, min(prev_managed_rows, 120))
                probe_cols = max(1, min(2, prev_managed_cols or 2))
                for sh in sheets_meta:
                    props = sh.get('properties') or {}
                    cand_id = int(props.get('sheetId') or 0)
                    cand_title = str(props.get('title') or '')
                    if not cand_id or not cand_title:
                        continue
                    escaped_cand = cand_title.replace("'", "''")
                    probe = _google_request_guarded('v254_probe_renamed_tab', requests.get, f'https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}', headers=headers, params={'includeGridData': 'true', 'ranges': f"'{escaped_cand}'!A1:{_xlsx_col_name(probe_cols)}{probe_rows}", 'fields': 'sheets(data(rowData(values(userEnteredValue))))'}, timeout=30, attempts=1)
                    if probe.status_code >= 300:
                        continue
                    prowdata = ((probe.json().get('sheets') or [{}])[0].get('data') or [{}])[0].get('rowData') or []
                    cand_keys = []
                    for i in range(probe_rows):
                        vals = (prowdata[i] or {}).get('values') or [] if i < len(prowdata) else []
                        cand_keys.append(_row_identity([_v239_google_plain_user_value(vals[c] if c < len(vals) else {}) for c in range(probe_cols)]))
                    ratio = _v254_difflib.SequenceMatcher(a=old_keys[:probe_rows], b=cand_keys, autojunk=False).ratio()
                    scored.append((float(ratio), cand_id, cand_title, props.get('gridProperties') or {}))
                scored.sort(reverse=True, key=lambda x: x[0])
                best = scored[0] if scored else None
                second = scored[1][0] if len(scored) > 1 else 0.0
                if best and best[0] >= 0.72 and (best[0] - second >= 0.08 or best[0] >= 0.94):
                    _ratio, sheet_id, actual_tab_title, gp = best
                    grid_rows = int((gp or {}).get('rowCount') or 0)
                    grid_cols = int((gp or {}).get('columnCount') or 0)
                    try:
                        bot_journal('google_renamed_tab_rebound_v254', target_chat_id, f'logical={tab_title}; actual={actual_tab_title}; sheetId={sheet_id}; score={_ratio:.3f}')
                    except Exception:
                        pass
            except Exception as exc:
                try:
                    bot_journal('google_renamed_tab_probe_warn_v254', target_chat_id, str(exc)[:300], 'WARN')
                except Exception:
                    pass

        max_cols = max((len(r or []) for r in rows), default=1)
        row_count = max(100, len(rows) + 20)
        col_count = max(26, max_cols + 3)
        created_new = False
        if sheet_id is None:
            add = _google_request_guarded('v252_add_sheet', requests.post, f'https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}:batchUpdate', headers=headers, json={'requests': [{'addSheet': {'properties': {'title': tab_title, 'gridProperties': {'rowCount': row_count, 'columnCount': col_count, 'frozenRowCount': 2}}}}]}, timeout=60, attempts=1)
            if add.status_code >= 300:
                raise RuntimeError(f'Google Sheets add tab {add.status_code}: {add.text[:500]}')
            sheet_id = int(add.json()['replies'][0]['addSheet']['properties']['sheetId'])
            actual_tab_title = str(tab_title)
            grid_rows = row_count
            grid_cols = col_count
            created_new = True

        annotations = dict(annotations_override or {})
        if not annotations and layout == 'category':
            try:
                _styles, annotations, _freeze, _widths = _modern_category_excel_styles_comments(rows)
            except Exception:
                annotations = {}

        cell_rows = []
        for r_idx, row0 in enumerate(rows, start=1):
            row = list(row0 or [])
            vals = []
            for c_idx in range(1, max_cols + 1):
                value = row[c_idx - 1] if c_idx - 1 < len(row) else ''
                cell = {'userEnteredValue': _google_cell_value(value), 'userEnteredFormat': _v167_google_color_format(row, r_idx, c_idx, max_cols, layout, annotations)}
                note = str(annotations.get((r_idx, c_idx)) or '').strip()
                if note:
                    cell['note'] = note
                vals.append(cell)
            cell_rows.append({'values': vals})

        # HOTFIX v258: probe beyond the remembered managed boundary.
        # Older incremental builds could leave stale bot rows below managed_rows
        # after a failed/partial compaction. If we only read managed_rows, those
        # rows stay invisible forever and can preserve duplicate summaries /
        # broken USD formulas. The probe is read-only; user rows below the bot
        # table are never modified just because they were read.
        _probe_tail_rows_v258 = 80
        _remembered_read_rows_v258 = max(len(rows), prev_managed_rows, 1)
        if grid_rows > 0:
            read_rows = min(int(grid_rows), _remembered_read_rows_v258 + _probe_tail_rows_v258)
        else:
            read_rows = _remembered_read_rows_v258 + _probe_tail_rows_v258
        read_cols = max(max_cols, prev_managed_cols, 1)
        existing_rows = []
        try:
            escaped = str(actual_tab_title).replace("'", "''")
            read = _google_request_guarded('v252_read_managed', requests.get, f'https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}', headers=headers, params={'includeGridData': 'true', 'ranges': f"'{escaped}'!A1:{_xlsx_col_name(read_cols)}{read_rows}", 'fields': 'sheets(data(rowData(values(userEnteredValue,note))))'}, timeout=60, attempts=2)
            if read.status_code < 300:
                existing_rows = ((read.json().get('sheets') or [{}])[0].get('data') or [{}])[0].get('rowData') or []
        except Exception as exc:
            try:
                bot_journal('google_incremental_read_warn_v252', target_chat_id, str(exc)[:300], 'WARN')
            except Exception:
                pass
            existing_rows = []

        # HOTFIX v258: recover the REAL bot-table boundary from the sheet.
        # A failed older compaction could leave valid-looking bot rows below the
        # remembered managed_rows.  The strongest terminal marker of each finance
        # section is "Остаток в обороте"; the last occurrence is therefore the
        # real end of the generated table.  Anything below that boundary remains
        # user territory and is never cleared/moved by this repair.
        actual_managed_rows_v258 = int(prev_managed_rows or 0)
        repair_extra_rows_v258 = False
        try:
            for _ri, _rr in enumerate(existing_rows, start=1):
                _vals = (_rr or {}).get('values') or []
                _a = str((_v239_google_plain_user_value(_vals[0]) if len(_vals) > 0 else ('string',''))[1] or '').strip().casefold()
                _b = str((_v239_google_plain_user_value(_vals[1]) if len(_vals) > 1 else ('string',''))[1] or '').strip().casefold()
                if _a == 'остаток в обороте' or _b == 'остаток в обороте':
                    actual_managed_rows_v258 = max(actual_managed_rows_v258, int(_ri))
            repair_extra_rows_v258 = actual_managed_rows_v258 > int(prev_managed_rows or 0)
            if repair_extra_rows_v258:
                try:
                    bot_journal('google_boundary_repair_v258', target_chat_id, f'remembered={prev_managed_rows}; actual={actual_managed_rows_v258}; target={len(rows)}', 'WARN')
                except Exception:
                    pass
        except Exception:
            actual_managed_rows_v258 = int(prev_managed_rows or 0)
            repair_extra_rows_v258 = False
        old_managed_rows_v258 = max(int(prev_managed_rows or 0), int(actual_managed_rows_v258 or 0))

        # v258 migration from the temporary v256 grid. D was a bot-owned
        # generic Expense column. Deleting D shifts E+ categories, their notes,
        # colors and all user content to the right one column left intact.
        remove_v256_expense_col = False
        try:
            for _rr in existing_rows[:12]:
                _vals = (_rr or {}).get('values') or []
                _plain = [str((_v239_google_plain_user_value(_vals[i]) if i < len(_vals) else ('string',''))[1] or '').strip().casefold() for i in range(4)]
                if _plain[0] == 'дата' and _plain[1] == 'описание' and _plain[2] == 'приход' and _plain[3] == 'расход':
                    remove_v256_expense_col = True
                    break
        except Exception:
            remove_v256_expense_col = False
        prev_managed_cols_raw_v257 = prev_managed_cols
        if remove_v256_expense_col and prev_managed_cols > 3:
            prev_managed_cols = max(3, prev_managed_cols - 1)

        req = []
        if remove_v256_expense_col:
            # Preserve USD expense-cell formatting/notes while collapsing the old
            # D expense column into C. Copy only rows where old C is blank and D
            # is used; then deleting D leaves the copied C cell intact. Values are
            # subsequently regenerated from canonical finance data.
            in_usd_v257 = False
            for _ri, _rr in enumerate(existing_rows):
                _vals = (_rr or {}).get('values') or []
                _a = str((_v239_google_plain_user_value(_vals[0]) if len(_vals) > 0 else ('string',''))[1] or '').strip().upper()
                if _a == 'USD':
                    in_usd_v257 = True
                    continue
                if not in_usd_v257:
                    continue
                _c = _v239_google_plain_user_value(_vals[2] if len(_vals) > 2 else {})
                _d = _v239_google_plain_user_value(_vals[3] if len(_vals) > 3 else {})
                _d_note = str((_vals[3] if len(_vals) > 3 else {}).get('note') or '')
                if _is_blank_plain(_c) and ((not _is_blank_plain(_d)) or _d_note):
                    req.append({'copyPaste': {'source': {'sheetId': sheet_id, 'startRowIndex': _ri, 'endRowIndex': _ri + 1, 'startColumnIndex': 3, 'endColumnIndex': 4}, 'destination': {'sheetId': sheet_id, 'startRowIndex': _ri, 'endRowIndex': _ri + 1, 'startColumnIndex': 2, 'endColumnIndex': 3}, 'pasteType': 'PASTE_NORMAL', 'pasteOrientation': 'NORMAL'}})
            req.append({'deleteDimension': {'range': {'sheetId': sheet_id, 'dimension': 'COLUMNS', 'startIndex': 3, 'endIndex': 4}}})
        # Grow grid only if there is no managed boundary to insert at.  Once a
        # boundary exists, insertDimension is what protects user content below/right.
        if created_new:
            pass
        elif prev_managed_rows <= 0 and (grid_rows < row_count or grid_cols < col_count):
            req.append({'updateSheetProperties': {'properties': {'sheetId': sheet_id, 'gridProperties': {'rowCount': max(grid_rows, row_count), 'columnCount': max(grid_cols, col_count)}}, 'fields': 'gridProperties(rowCount,columnCount)'}})

        row_delta_v258 = 0 if created_new or old_managed_rows_v258 <= 0 else (len(rows) - old_managed_rows_v258)
        row_growth = max(0, row_delta_v258)
        row_shrink_v258 = max(0, -row_delta_v258)
        col_growth = 0 if created_new or prev_managed_cols <= 0 else max(0, max_cols - prev_managed_cols)
        row_insert_plan = []
        inserted_row_indices = set()
        target_to_old_row = {i: i for i in range(min(len(rows), old_managed_rows_v258))}
        row_copy_map_v258 = {}
        # v258: run logical row alignment for BOTH growth and shrink.  v257 only
        # aligned on growth, so after a duplicate disappeared the bot updated
        # individual cells in-place and could create mixed rows (old description
        # in A/B + a summary formula in C).  On shrink we compact logical rows by
        # copying the whole previous row (values + note + format) to its new slot,
        # then refresh only bot-owned values.  No physical row deletion is used,
        # so user content below the managed table never moves or disappears.
        if row_delta_v258:
            try:
                import difflib as _v258_difflib
                old_plain_rows = []
                if (not repair_extra_rows_v258) and len(prev_snapshot) >= old_managed_rows_v258:
                    for i in range(old_managed_rows_v258):
                        prow = prev_snapshot[i] if isinstance(prev_snapshot[i], list) else []
                        old_plain_rows.append([_plain_from_json(x) for x in prow])
                else:
                    for i in range(old_managed_rows_v258):
                        vals = (existing_rows[i] or {}).get('values') or [] if i < len(existing_rows) else []
                        old_plain_rows.append([_v239_google_plain_user_value(x) for x in vals[:max(prev_managed_cols, max_cols)]])
                new_plain_rows = [[_v239_google_target_plain((r or [])[c] if c < len(r or []) else '') for c in range(max_cols)] for r in rows]
                old_keys = [_row_identity(x) for x in old_plain_rows]
                new_keys = [_row_identity(x) for x in new_plain_rows]
                matcher = _v258_difflib.SequenceMatcher(a=old_keys, b=new_keys, autojunk=False)
                candidate_plan = []
                candidate_inserted = set()
                candidate_map = {}
                deleted_old = 0
                for tag, i1, i2, j1, j2 in matcher.get_opcodes():
                    old_n, new_n = i2 - i1, j2 - j1
                    if tag == 'equal':
                        for k in range(new_n):
                            candidate_map[j1 + k] = i1 + k
                    elif tag == 'insert':
                        if new_n:
                            candidate_plan.append((j1, new_n))
                            candidate_inserted.update(range(j1, j2))
                    elif tag == 'replace':
                        common = min(old_n, new_n)
                        for k in range(common):
                            candidate_map[j1 + k] = i1 + k
                        if new_n > old_n:
                            start_new = j1 + common
                            extra = new_n - old_n
                            candidate_plan.append((start_new, extra))
                            candidate_inserted.update(range(start_new, start_new + extra))
                        elif old_n > new_n:
                            deleted_old += old_n - new_n
                    elif tag == 'delete':
                        deleted_old += old_n
                planned = sum(n for _, n in candidate_plan)
                # Pure shrink (or pure growth) can be mapped deterministically.
                # Mixed delete+insert migrations remain on conservative fallback.
                if (row_shrink_v258 and planned == 0 and deleted_old == row_shrink_v258) or (row_growth and deleted_old == 0 and planned == row_growth):
                    row_insert_plan = sorted(candidate_plan)
                    inserted_row_indices = set(candidate_inserted)
                    target_to_old_row = candidate_map
                    if row_shrink_v258:
                        row_copy_map_v258 = {int(j): int(i) for j, i in candidate_map.items() if int(i) != int(j)}
            except Exception as _v258_rowdiff_exc:
                try: bot_journal('google_row_compact_warn_v258', target_chat_id, str(_v258_rowdiff_exc)[:300], 'WARN')
                except Exception: pass
                row_insert_plan = []
                row_copy_map_v258 = {}
            if row_growth and not row_insert_plan:
                # Conservative fallback for ambiguous growth: still protect all
                # user content below the previous table boundary.
                row_insert_plan = [(old_managed_rows_v258, row_growth)]
                inserted_row_indices = set(range(old_managed_rows_v258, old_managed_rows_v258 + row_growth))
                target_to_old_row = {i: i for i in range(min(len(rows), old_managed_rows_v258))}
            # For ambiguous shrink we never delete physical Google rows. Values
            # remain protected; a later clean alignment can compact them safely.
            for start_idx, count in row_insert_plan:
                req.append({'insertDimension': {'range': {'sheetId': sheet_id, 'dimension': 'ROWS', 'startIndex': start_idx, 'endIndex': start_idx + count}, 'inheritFromBefore': True}})
        if col_growth:
            req.append({'insertDimension': {'range': {'sheetId': sheet_id, 'dimension': 'COLUMNS', 'startIndex': prev_managed_cols, 'endIndex': prev_managed_cols + col_growth}, 'inheritFromBefore': True}})

        added = 0
        updated = 0
        unchanged = 0
        manual_values_preserved = 0
        manual_preserved_cells = set()

        if created_new:
            if cell_rows:
                req.append({'updateCells': {'range': {'sheetId': sheet_id, 'startRowIndex': 0, 'endRowIndex': len(rows), 'startColumnIndex': 0, 'endColumnIndex': max_cols}, 'rows': cell_rows, 'fields': 'userEnteredValue,note,userEnteredFormat'}})
                added = len(rows)
            req.append({'updateDimensionProperties': {'range': {'sheetId': sheet_id, 'dimension': 'COLUMNS', 'startIndex': 0, 'endIndex': 1}, 'properties': {'pixelSize': 95}, 'fields': 'pixelSize'}})
            if max_cols >= 2:
                req.append({'updateDimensionProperties': {'range': {'sheetId': sheet_id, 'dimension': 'COLUMNS', 'startIndex': 1, 'endIndex': 2}, 'properties': {'pixelSize': 320}, 'fields': 'pixelSize'}})
            if max_cols >= 3:
                req.append({'updateDimensionProperties': {'range': {'sheetId': sheet_id, 'dimension': 'COLUMNS', 'startIndex': 2, 'endIndex': max_cols}, 'properties': {'pixelSize': 115}, 'fields': 'pixelSize'}})
        else:
            for idx, row0 in enumerate(rows):
                target = list(row0 or [])
                # Rows added beyond the previous managed boundary are physically
                # inserted above the user's tail, so it is safe to apply bot style
                # and generated notes only to those brand-new rows.
                if idx in inserted_row_indices:
                    req.append({'updateCells': {'range': {'sheetId': sheet_id, 'startRowIndex': idx, 'endRowIndex': idx + 1, 'startColumnIndex': 0, 'endColumnIndex': max_cols}, 'rows': [cell_rows[idx]], 'fields': 'userEnteredValue,note,userEnteredFormat'}})
                    added += 1
                    continue

                old_idx = int(target_to_old_row.get(idx, idx))
                old_vals = (existing_rows[old_idx] or {}).get('values') or [] if old_idx < len(existing_rows) else []
                if idx in row_copy_map_v258 and old_idx != idx:
                    # Move the logical row as a whole so user note/color follows
                    # the finance row during compaction. Only managed columns are
                    # copied; anything to the right is untouched.
                    req.append({'copyPaste': {'source': {'sheetId': sheet_id, 'startRowIndex': old_idx, 'endRowIndex': old_idx + 1, 'startColumnIndex': 0, 'endColumnIndex': max_cols}, 'destination': {'sheetId': sheet_id, 'startRowIndex': idx, 'endRowIndex': idx + 1, 'startColumnIndex': 0, 'endColumnIndex': max_cols}, 'pasteType': 'PASTE_NORMAL', 'pasteOrientation': 'NORMAL'}})
                changed_cols = []
                # Existing columns: values only. Notes and formatting are owned by
                # the user once the cell exists and are never touched again.
                existing_col_limit = min(max_cols, prev_managed_cols if prev_managed_cols > 0 else max_cols)
                for c in range(existing_col_limit):
                    want = _v239_google_target_plain(target[c] if c < len(target) else '')
                    old_c = c + 1 if remove_v256_expense_col and c >= 3 else c
                    got = _v239_google_plain_user_value(old_vals[old_c] if old_c < len(old_vals) else {})
                    prev = None
                    if old_idx < len(prev_snapshot) and isinstance(prev_snapshot[old_idx], list) and old_c < len(prev_snapshot[old_idx]):
                        prev = _plain_from_json(prev_snapshot[old_idx][old_c])
                    google_formula_damaged_v258 = bool(isinstance(got, tuple) and len(got) == 2 and got[0] == 'formula' and '#REF!' in str(got[1] or '').upper())
                    manual_owned = prev is not None and (not google_formula_damaged_v258) and (not _v244_google_values_equivalent(got, prev)) and (not _is_blank_plain(got))
                    if manual_owned and (not _v244_google_values_equivalent(want, got)):
                        manual_values_preserved += 1
                        manual_preserved_cells.add((idx, c))
                        continue

                    # v254: Google automatically rewrites formula references when
                    # insertDimension moves rows. Our comparison was made against
                    # the PRE-insert grid, so a formula that looked unchanged can
                    # become SUM(C34) while the intended bot formula is SUM(C33).
                    # Re-assert every bot-owned formula in the same batch whenever
                    # physical rows are inserted. User-edited formulas remain safe.
                    force_formula_after_insert = bool(row_insert_plan and want[0] == 'formula' and (prev is None or _v244_google_values_equivalent(got, prev)))
                    if _v244_google_values_equivalent(want, got) and not force_formula_after_insert:
                        continue
                    if manual_owned:
                        manual_values_preserved += 1
                        manual_preserved_cells.add((idx, c))
                        continue
                    changed_cols.append(c)
                for a, b in _segments(changed_cols):
                    vals = [{'userEnteredValue': _google_cell_value(target[c] if c < len(target) else '')} for c in range(a, b)]
                    req.append({'updateCells': {'range': {'sheetId': sheet_id, 'startRowIndex': idx, 'endRowIndex': idx + 1, 'startColumnIndex': a, 'endColumnIndex': b}, 'rows': [{'values': vals}], 'fields': 'userEnteredValue'}})

                # Newly added columns are physically inserted before anything the
                # user may have placed to the right. They are blank/new, so bot
                # formatting and generated notes are safe there.
                if col_growth and max_cols > prev_managed_cols:
                    a, b = prev_managed_cols, max_cols
                    vals = cell_rows[idx]['values'][a:b]
                    if vals:
                        req.append({'updateCells': {'range': {'sheetId': sheet_id, 'startRowIndex': idx, 'endRowIndex': idx + 1, 'startColumnIndex': a, 'endColumnIndex': b}, 'rows': [{'values': vals}], 'fields': 'userEnteredValue,note,userEnteredFormat'}})

                if changed_cols or (col_growth and max_cols > prev_managed_cols):
                    updated += 1
                else:
                    unchanged += 1

            # Shrink safely: never blind-clear the old tail. We only remove an
            # old bot value if v252 has a snapshot proving the current value is
            # still exactly what the bot wrote previously. Notes/colors survive.
            stale_tail = max(0, old_managed_rows_v258 - len(rows))
            if stale_tail > 0 and repair_extra_rows_v258:
                # These rows are inside the bot's REAL terminal boundary but were
                # invisible to the old metadata. Clear only VALUES in the stale
                # bot tail; notes/colors remain untouched, and rows below the final
                # bot terminal marker are not addressed at all. This removes old
                # duplicate summaries / mixed USD rows without erasing user data.
                for idx in range(len(rows), old_managed_rows_v258):
                    old_vals = (existing_rows[idx] or {}).get('values') or [] if idx < len(existing_rows) else []
                    clear_cols = []
                    for c in range(min(max_cols, len(old_vals))):
                        got = _v239_google_plain_user_value(old_vals[c] if c < len(old_vals) else {})
                        if not _is_blank_plain(got):
                            clear_cols.append(c)
                    for a, b in _segments(clear_cols):
                        req.append({'updateCells': {'range': {'sheetId': sheet_id, 'startRowIndex': idx, 'endRowIndex': idx + 1, 'startColumnIndex': a, 'endColumnIndex': b}, 'rows': [{'values': [{} for _ in range(a, b)]}], 'fields': 'userEnteredValue'}})
            elif stale_tail > 0 and prev_snapshot:
                for idx in range(len(rows), min(old_managed_rows_v258, len(prev_snapshot))):
                    old_vals = (existing_rows[idx] or {}).get('values') or [] if idx < len(existing_rows) else []
                    clear_cols = []
                    prev_row = prev_snapshot[idx] if idx < len(prev_snapshot) and isinstance(prev_snapshot[idx], list) else []
                    for c in range(min(prev_managed_cols, len(prev_row))):
                        got = _v239_google_plain_user_value(old_vals[c] if c < len(old_vals) else {})
                        prev = _plain_from_json(prev_row[c])
                        damaged_formula_v258 = bool(isinstance(got, tuple) and len(got) == 2 and got[0] == 'formula' and '#REF!' in str(got[1] or '').upper())
                        if (not _is_blank_plain(got)) and (_v244_google_values_equivalent(got, prev) or damaged_formula_v258):
                            clear_cols.append(c)
                    for a, b in _segments(clear_cols):
                        req.append({'updateCells': {'range': {'sheetId': sheet_id, 'startRowIndex': idx, 'endRowIndex': idx + 1, 'startColumnIndex': a, 'endColumnIndex': b}, 'rows': [{'values': [{} for _ in range(a, b)]}], 'fields': 'userEnteredValue'}})

        if req:
            upd = _google_request_guarded('v252_non_destructive_upsert', requests.post, f'https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}:batchUpdate', headers=headers, json={'requests': req}, timeout=90, attempts=1)
            if upd.status_code >= 300:
                raise RuntimeError(f'Google Sheets non-destructive update {upd.status_code}: {upd.text[:500]}')

        escaped = str(actual_tab_title).replace("'", "''")
        verify = _google_request_guarded('v252_verify_incremental', requests.get, f'https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}', headers=headers, params={'includeGridData': 'true', 'ranges': f"'{escaped}'!A1:{_xlsx_col_name(max_cols)}{max(1, len(rows))}", 'fields': 'sheets(data(rowData(values(userEnteredValue,note))))'}, timeout=60, attempts=2)
        if verify.status_code >= 300:
            raise RuntimeError(f'Google Sheets incremental verify {verify.status_code}: {verify.text[:500]}')
        vr = ((verify.json().get('sheets') or [{}])[0].get('data') or [{}])[0].get('rowData') or []
        for idx, row0 in enumerate(rows):
            old_vals = (vr[idx] or {}).get('values') or [] if idx < len(vr) else []
            for c in range(max_cols):
                if (idx, c) in manual_preserved_cells:
                    continue
                want = _v239_google_target_plain((row0 or [])[c] if c < len(row0 or []) else '')
                got = _v239_google_plain_user_value(old_vals[c] if c < len(old_vals) else {})
                if not _v244_google_values_equivalent(want, got):
                    raise RuntimeError(f'Google incremental verify mismatch row={idx + 1} col={c + 1}; want={want}; got={got}')

        row_hash = hashlib.sha256(json.dumps(rows, ensure_ascii=False, sort_keys=False, separators=(',', ':'), default=str).encode('utf-8')).hexdigest()
        snapshot = [[_plain_json((row or [])[c] if c < len(row or []) else '') for c in range(max_cols)] for row in rows]
        try:
            SQLITE.set_meta('google_sync_v239', sync_key, {'tab': tab_title, 'sheet_id_v254': int(sheet_id), 'sheet_title_actual_v254': str(actual_tab_title), 'tenant_id': str(tid), 'chat_id': target_chat_id, 'managed_rows': len(rows), 'managed_cols': max_cols, 'managed_values_v252': snapshot, 'row_hash': row_hash, 'synced_at': now_local().isoformat(timespec='microseconds'), 'manual_values_preserved': manual_values_preserved})
        except Exception:
            pass
        url = f'https://docs.google.com/spreadsheets/d/{spreadsheet_id}/edit#gid={sheet_id}'

    try:
        tenant_google_history(tid, 'thuwed_non_destructive_upsert_v254', actual_tab_title, ok=True, chat_id=target_chat_id, url=url, added=added, updated=updated, unchanged=unchanged, stale_tail=stale_tail if 'stale_tail' in locals() else 0, manual_values_preserved=manual_values_preserved, row_growth=row_growth, col_growth=col_growth)
        tenant_google_persist(tid, 'tenant_google_runtime_v252')
        try:
            bot_journal('google_non_destructive_upsert_v254', target_chat_id, f'logical_tab={tab_title}; actual_tab={actual_tab_title}; sheetId={sheet_id}; added={added}; updated={updated}; unchanged={unchanged}; row_growth={row_growth}; row_shrink={row_shrink_v258}; row_copies={len(row_copy_map_v258)}; col_growth={col_growth}; manual_values_preserved={manual_values_preserved}; stale_tail_preserved={stale_tail if "stale_tail" in locals() else 0}')
        except Exception:
            pass
    except Exception:
        pass
    return url

def _v261_google_upsert_new(tab_title: str, rows: list[list], target_chat_id: int, layout: str='category', annotations_override: dict | None=None) -> str:
    """v260 non-destructive upsert for the stable Thu-Wed tab.

    Contract for an existing sheet:
    - bot values may be refreshed inside the previously managed table;
    - existing CellData.note is NEVER cleared/replaced;
    - existing userEnteredFormat is NEVER replaced (manual colors/styles survive);
    - when the bot table grows, real rows are inserted at the detected logical
      insertion point (with a safe boundary fallback), and columns at the previous
      managed boundary, so user notes/colors and content below/right are shifted,
      not overwritten;
    - a shrinking table never performs a blind tail clear.  From v252 onward a
      stored value snapshot lets us clear only values that are still exactly the
      previous bot-owned values, while notes/formatting remain untouched.
    - v260: a Data-Constitution snapshot/ledger lag never overwrites the stable
      worksheet. Instead a NEW recovery worksheet is created from the current
      canonical rows in the SAME tenant spreadsheet.
    """
    target_chat_id = int(target_chat_id)
    tid = _v149_tenant_id(None, target_chat_id) if callable(globals().get('_v149_tenant_id')) else tenant_id_for_chat(target_chat_id, create=False)
    if callable(globals().get('_v149_chat_belongs_to_tenant')) and (not _v149_chat_belongs_to_tenant(target_chat_id, tid)):
        raise RuntimeError('Google export blocked: target chat is not connected to this space')
    cfg = tenant_google_config(tid)
    if not bool((cfg.get('export_settings') or {}).get('sheet_enabled', True)):
        raise RuntimeError('Выгрузка в Google Sheets выключена для этого пространства')

    gate_ok, gate_reason = _v239_google_recovery_write_gate()
    if not gate_ok:
        _reason_v260 = str(gate_reason or '')
        _fallback_allowed_v260 = ('ledger is behind finance integrity' in _reason_v260 or 'snapshot rejected' in _reason_v260)
        _creator_v260 = globals().get('_google_sheets_create_category_report')
        if _fallback_allowed_v260 and callable(_creator_v260):
            _fallback_title_v260 = f"{str(tab_title or 'Чт–Ср')} · восстановление"
            # The canonical v149 creator is tenant-aware. Pass the resolved tenant
            # explicitly so a blocked child-space sync can never spill into the
            # platform spreadsheet. Keep a compatibility fallback for old creators.
            try:
                _url_v260 = _creator_v260(
                    _fallback_title_v260, rows, layout=layout,
                    annotations_override=annotations_override, include_annotations=True,
                    tenant_id=str(tid), target_chat_id=int(target_chat_id),
                )
            except TypeError:
                _ctx_v260 = globals().get('tenant_google_context')
                if callable(_ctx_v260):
                    with _ctx_v260(str(tid)):
                        _url_v260 = _creator_v260(_fallback_title_v260, rows, layout=layout, annotations_override=annotations_override, include_annotations=True)
                else:
                    _url_v260 = _creator_v260(_fallback_title_v260, rows, layout=layout, annotations_override=annotations_override, include_annotations=True)
            try:
                bot_journal('google_constitution_fallback_new_tab_v260', int(target_chat_id), f'tenant={tid}; reason={_reason_v260[:220]}; url={str(_url_v260)[:140]}', 'WARN')
            except Exception:
                pass
            try:
                log_info(f'[GOOGLE V260] stable sheet blocked; new SAME-TENANT fallback tab created chat={target_chat_id} tenant={tid}: {_reason_v260}')
            except Exception:
                pass
            return _url_v260
        raise RuntimeError('Google sync blocked v260: ' + _reason_v260)

    def _plain_json(value):
        p = _v239_google_target_plain(value)
        return [p[0], p[1]]

    def _plain_from_json(value):
        try:
            if isinstance(value, (list, tuple)) and len(value) == 2:
                return (str(value[0]), value[1])
        except Exception:
            pass
        return ('string', '')

    def _is_blank_plain(value) -> bool:
        try:
            t, v = value
            return t == 'string' and str(v or '').strip() == ''
        except Exception:
            return True

    def _segments(cols):
        cols = sorted(set(int(c) for c in cols if int(c) >= 0))
        if not cols:
            return []
        out = []
        a = b = cols[0]
        for c in cols[1:]:
            if c == b + 1:
                b = c
            else:
                out.append((a, b + 1))
                a = b = c
        out.append((a, b + 1))
        return out

    def _identity_token(plain):
        try:
            t, v = plain
        except Exception:
            return ''
        if t == 'formula':
            return '=' + _v251_google_formula_canonical(v)
        if t == 'number':
            try:
                return f'{float(v):.12g}'
            except Exception:
                return str(v or '').strip()
        if t == 'bool':
            return 'TRUE' if bool(v) else 'FALSE'
        return str(v or '').replace('\r\n', '\n').strip()

    def _row_identity(plains):
        vals = [_identity_token(x) for x in list(plains or [])]
        first = vals[0] if len(vals) > 0 else ''
        second = vals[1] if len(vals) > 1 else ''
        if first or second:
            # In the financial sheet the first two columns are the stable row
            # identity (date/description or a summary label). Numeric/formula
            # totals are deliberately ignored so recalculation does not look
            # like a row replacement.
            return ('row', first.casefold(), second.casefold())
        if not any(vals):
            return ('blank',)
        return ('other', *(x.casefold() for x in vals[:3]))

    # v254: the generated period title is only a logical key. The actual Google
    # worksheet is pinned by immutable sheetId, so a user's manual tab rename
    # never makes the bot create a second tab or lose its ownership snapshot.
    sync_key = _v239_google_sync_meta_key(str(tid), target_chat_id, tab_title)
    try:
        sync_meta = SQLITE.get_meta('google_sync_v239', sync_key, {}) or {}
    except Exception:
        sync_meta = {}
    prev_managed_rows = int((sync_meta or {}).get('managed_rows') or 0)
    prev_managed_cols = int((sync_meta or {}).get('managed_cols') or 0)
    prev_snapshot = (sync_meta or {}).get('managed_values_v252')
    if not isinstance(prev_snapshot, list):
        prev_snapshot = []
    try:
        preferred_sheet_id_v254 = int((sync_meta or {}).get('sheet_id_v254') or 0)
    except Exception:
        preferred_sheet_id_v254 = 0

    with tenant_google_context(tid):
        token = _google_access_token()
        info = _google_service_account_info()
        spreadsheet_id = _v244_google_resolve_or_create_spreadsheet(str(tid))
        service_email = str(info.get('client_email') or '')
        headers = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}
        meta = _google_request_guarded('v252_metadata', requests.get, f'https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}', headers=headers, params={'fields': 'spreadsheetId,properties.title,sheets.properties(sheetId,title,gridProperties)'}, timeout=45, attempts=2)
        if meta.status_code >= 300:
            if meta.status_code in (401, 403):
                raise RuntimeError(f'Google Sheets access denied. Добавьте {service_email} как Редактор.')
            raise RuntimeError(f'Google Sheets metadata {meta.status_code}: {meta.text[:500]}')
        payload = meta.json()
        sheet_id = None
        actual_tab_title = str(tab_title)
        grid_rows = 0
        grid_cols = 0
        sheets_meta = list(payload.get('sheets') or [])

        # First choice: immutable sheetId saved by v254. Title is intentionally
        # ignored here because users are allowed to rename tabs freely.
        if preferred_sheet_id_v254:
            for sh in sheets_meta:
                props = sh.get('properties') or {}
                if int(props.get('sheetId') or 0) == preferred_sheet_id_v254:
                    sheet_id = int(props.get('sheetId'))
                    actual_tab_title = str(props.get('title') or tab_title)
                    gp = props.get('gridProperties') or {}
                    grid_rows = int(gp.get('rowCount') or 0)
                    grid_cols = int(gp.get('columnCount') or 0)
                    break

        # Compatibility with older builds / a tab that has never been renamed.
        if sheet_id is None:
            for sh in sheets_meta:
                props = sh.get('properties') or {}
                if str(props.get('title') or '') == tab_title:
                    sheet_id = int(props.get('sheetId'))
                    actual_tab_title = str(props.get('title') or tab_title)
                    gp = props.get('gridProperties') or {}
                    grid_rows = int(gp.get('rowCount') or 0)
                    grid_cols = int(gp.get('columnCount') or 0)
                    break

        # One-time v253 -> v254 migration for a tab renamed BEFORE v254 had a
        # chance to save sheetId. Match the previous managed snapshot against
        # the first two identity columns of existing tabs. Only a strong unique
        # match is accepted; otherwise we fail safe and create the logical tab.
        if sheet_id is None and prev_snapshot and prev_managed_rows > 0:
            try:
                import difflib as _v254_difflib
                old_plain_rows = []
                for prow in prev_snapshot[:prev_managed_rows]:
                    prow = prow if isinstance(prow, list) else []
                    old_plain_rows.append([_plain_from_json(prow[c]) if c < len(prow) else ('string', '') for c in range(min(2, max(1, prev_managed_cols)))])
                old_keys = [_row_identity(x) for x in old_plain_rows]
                scored = []
                probe_rows = max(1, min(prev_managed_rows, 120))
                probe_cols = max(1, min(2, prev_managed_cols or 2))
                for sh in sheets_meta:
                    props = sh.get('properties') or {}
                    cand_id = int(props.get('sheetId') or 0)
                    cand_title = str(props.get('title') or '')
                    if not cand_id or not cand_title:
                        continue
                    escaped_cand = cand_title.replace("'", "''")
                    probe = _google_request_guarded('v254_probe_renamed_tab', requests.get, f'https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}', headers=headers, params={'includeGridData': 'true', 'ranges': f"'{escaped_cand}'!A1:{_xlsx_col_name(probe_cols)}{probe_rows}", 'fields': 'sheets(data(rowData(values(userEnteredValue))))'}, timeout=30, attempts=1)
                    if probe.status_code >= 300:
                        continue
                    prowdata = ((probe.json().get('sheets') or [{}])[0].get('data') or [{}])[0].get('rowData') or []
                    cand_keys = []
                    for i in range(probe_rows):
                        vals = (prowdata[i] or {}).get('values') or [] if i < len(prowdata) else []
                        cand_keys.append(_row_identity([_v239_google_plain_user_value(vals[c] if c < len(vals) else {}) for c in range(probe_cols)]))
                    ratio = _v254_difflib.SequenceMatcher(a=old_keys[:probe_rows], b=cand_keys, autojunk=False).ratio()
                    scored.append((float(ratio), cand_id, cand_title, props.get('gridProperties') or {}))
                scored.sort(reverse=True, key=lambda x: x[0])
                best = scored[0] if scored else None
                second = scored[1][0] if len(scored) > 1 else 0.0
                if best and best[0] >= 0.72 and (best[0] - second >= 0.08 or best[0] >= 0.94):
                    _ratio, sheet_id, actual_tab_title, gp = best
                    grid_rows = int((gp or {}).get('rowCount') or 0)
                    grid_cols = int((gp or {}).get('columnCount') or 0)
                    try:
                        bot_journal('google_renamed_tab_rebound_v254', target_chat_id, f'logical={tab_title}; actual={actual_tab_title}; sheetId={sheet_id}; score={_ratio:.3f}')
                    except Exception:
                        pass
            except Exception as exc:
                try:
                    bot_journal('google_renamed_tab_probe_warn_v254', target_chat_id, str(exc)[:300], 'WARN')
                except Exception:
                    pass

        max_cols = max((len(r or []) for r in rows), default=1)
        row_count = max(100, len(rows) + 20)
        col_count = max(26, max_cols + 3)
        created_new = False
        if sheet_id is None:
            add = _google_request_guarded('v252_add_sheet', requests.post, f'https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}:batchUpdate', headers=headers, json={'requests': [{'addSheet': {'properties': {'title': tab_title, 'gridProperties': {'rowCount': row_count, 'columnCount': col_count, 'frozenRowCount': 2}}}}]}, timeout=60, attempts=1)
            if add.status_code >= 300:
                raise RuntimeError(f'Google Sheets add tab {add.status_code}: {add.text[:500]}')
            sheet_id = int(add.json()['replies'][0]['addSheet']['properties']['sheetId'])
            actual_tab_title = str(tab_title)
            grid_rows = row_count
            grid_cols = col_count
            created_new = True

        annotations = dict(annotations_override or {})
        if not annotations and layout == 'category':
            try:
                _styles, annotations, _freeze, _widths = _modern_category_excel_styles_comments(rows)
            except Exception:
                annotations = {}

        cell_rows = []
        for r_idx, row0 in enumerate(rows, start=1):
            row = list(row0 or [])
            vals = []
            for c_idx in range(1, max_cols + 1):
                value = row[c_idx - 1] if c_idx - 1 < len(row) else ''
                cell = {'userEnteredValue': _google_cell_value(value), 'userEnteredFormat': _v167_google_color_format(row, r_idx, c_idx, max_cols, layout, annotations)}
                note = str(annotations.get((r_idx, c_idx)) or '').strip()
                if note:
                    cell['note'] = note
                vals.append(cell)
            cell_rows.append({'values': vals})

        # HOTFIX v258: probe beyond the remembered managed boundary.
        # Older incremental builds could leave stale bot rows below managed_rows
        # after a failed/partial compaction. If we only read managed_rows, those
        # rows stay invisible forever and can preserve duplicate summaries /
        # broken USD formulas. The probe is read-only; user rows below the bot
        # table are never modified just because they were read.
        _probe_tail_rows_v258 = 80
        _remembered_read_rows_v258 = max(len(rows), prev_managed_rows, 1)
        if grid_rows > 0:
            read_rows = min(int(grid_rows), _remembered_read_rows_v258 + _probe_tail_rows_v258)
        else:
            read_rows = _remembered_read_rows_v258 + _probe_tail_rows_v258
        read_cols = max(max_cols, prev_managed_cols, 1)
        existing_rows = []
        try:
            escaped = str(actual_tab_title).replace("'", "''")
            read = _google_request_guarded('v252_read_managed', requests.get, f'https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}', headers=headers, params={'includeGridData': 'true', 'ranges': f"'{escaped}'!A1:{_xlsx_col_name(read_cols)}{read_rows}", 'fields': 'sheets(data(rowData(values(userEnteredValue,note))))'}, timeout=60, attempts=2)
            if read.status_code < 300:
                existing_rows = ((read.json().get('sheets') or [{}])[0].get('data') or [{}])[0].get('rowData') or []
        except Exception as exc:
            try:
                bot_journal('google_incremental_read_warn_v252', target_chat_id, str(exc)[:300], 'WARN')
            except Exception:
                pass
            existing_rows = []

        # HOTFIX v258: recover the REAL bot-table boundary from the sheet.
        # A failed older compaction could leave valid-looking bot rows below the
        # remembered managed_rows.  The strongest terminal marker of each finance
        # section is "Остаток в обороте"; the last occurrence is therefore the
        # real end of the generated table.  Anything below that boundary remains
        # user territory and is never cleared/moved by this repair.
        actual_managed_rows_v258 = int(prev_managed_rows or 0)
        repair_extra_rows_v258 = False
        try:
            for _ri, _rr in enumerate(existing_rows, start=1):
                _vals = (_rr or {}).get('values') or []
                _a = str((_v239_google_plain_user_value(_vals[0]) if len(_vals) > 0 else ('string',''))[1] or '').strip().casefold()
                _b = str((_v239_google_plain_user_value(_vals[1]) if len(_vals) > 1 else ('string',''))[1] or '').strip().casefold()
                if _a == 'остаток в обороте' or _b == 'остаток в обороте':
                    actual_managed_rows_v258 = max(actual_managed_rows_v258, int(_ri))
            repair_extra_rows_v258 = actual_managed_rows_v258 > int(prev_managed_rows or 0)
            if repair_extra_rows_v258:
                try:
                    bot_journal('google_boundary_repair_v258', target_chat_id, f'remembered={prev_managed_rows}; actual={actual_managed_rows_v258}; target={len(rows)}', 'WARN')
                except Exception:
                    pass
        except Exception:
            actual_managed_rows_v258 = int(prev_managed_rows or 0)
            repair_extra_rows_v258 = False
        old_managed_rows_v258 = max(int(prev_managed_rows or 0), int(actual_managed_rows_v258 or 0))

        # v258 migration from the temporary v256 grid. D was a bot-owned
        # generic Expense column. Deleting D shifts E+ categories, their notes,
        # colors and all user content to the right one column left intact.
        remove_v256_expense_col = False
        try:
            for _rr in existing_rows[:12]:
                _vals = (_rr or {}).get('values') or []
                _plain = [str((_v239_google_plain_user_value(_vals[i]) if i < len(_vals) else ('string',''))[1] or '').strip().casefold() for i in range(4)]
                if _plain[0] == 'дата' and _plain[1] == 'описание' and _plain[2] == 'приход' and _plain[3] == 'расход':
                    remove_v256_expense_col = True
                    break
        except Exception:
            remove_v256_expense_col = False
        prev_managed_cols_raw_v257 = prev_managed_cols
        if remove_v256_expense_col and prev_managed_cols > 3:
            prev_managed_cols = max(3, prev_managed_cols - 1)

        req = []
        if remove_v256_expense_col:
            # Preserve USD expense-cell formatting/notes while collapsing the old
            # D expense column into C. Copy only rows where old C is blank and D
            # is used; then deleting D leaves the copied C cell intact. Values are
            # subsequently regenerated from canonical finance data.
            in_usd_v257 = False
            for _ri, _rr in enumerate(existing_rows):
                _vals = (_rr or {}).get('values') or []
                _a = str((_v239_google_plain_user_value(_vals[0]) if len(_vals) > 0 else ('string',''))[1] or '').strip().upper()
                if _a == 'USD':
                    in_usd_v257 = True
                    continue
                if not in_usd_v257:
                    continue
                _c = _v239_google_plain_user_value(_vals[2] if len(_vals) > 2 else {})
                _d = _v239_google_plain_user_value(_vals[3] if len(_vals) > 3 else {})
                _d_note = str((_vals[3] if len(_vals) > 3 else {}).get('note') or '')
                if _is_blank_plain(_c) and ((not _is_blank_plain(_d)) or _d_note):
                    req.append({'copyPaste': {'source': {'sheetId': sheet_id, 'startRowIndex': _ri, 'endRowIndex': _ri + 1, 'startColumnIndex': 3, 'endColumnIndex': 4}, 'destination': {'sheetId': sheet_id, 'startRowIndex': _ri, 'endRowIndex': _ri + 1, 'startColumnIndex': 2, 'endColumnIndex': 3}, 'pasteType': 'PASTE_NORMAL', 'pasteOrientation': 'NORMAL'}})
            req.append({'deleteDimension': {'range': {'sheetId': sheet_id, 'dimension': 'COLUMNS', 'startIndex': 3, 'endIndex': 4}}})
        # Grow grid only if there is no managed boundary to insert at.  Once a
        # boundary exists, insertDimension is what protects user content below/right.
        if created_new:
            pass
        elif prev_managed_rows <= 0 and (grid_rows < row_count or grid_cols < col_count):
            req.append({'updateSheetProperties': {'properties': {'sheetId': sheet_id, 'gridProperties': {'rowCount': max(grid_rows, row_count), 'columnCount': max(grid_cols, col_count)}}, 'fields': 'gridProperties(rowCount,columnCount)'}})

        row_delta_v258 = 0 if created_new or old_managed_rows_v258 <= 0 else (len(rows) - old_managed_rows_v258)
        row_growth = max(0, row_delta_v258)
        row_shrink_v258 = max(0, -row_delta_v258)
        col_growth = 0 if created_new or prev_managed_cols <= 0 else max(0, max_cols - prev_managed_cols)
        row_insert_plan = []
        inserted_row_indices = set()
        target_to_old_row = {i: i for i in range(min(len(rows), old_managed_rows_v258))}
        row_copy_map_v258 = {}
        # v258: run logical row alignment for BOTH growth and shrink.  v257 only
        # aligned on growth, so after a duplicate disappeared the bot updated
        # individual cells in-place and could create mixed rows (old description
        # in A/B + a summary formula in C).  On shrink we compact logical rows by
        # copying the whole previous row (values + note + format) to its new slot,
        # then refresh only bot-owned values.  No physical row deletion is used,
        # so user content below the managed table never moves or disappears.
        if row_delta_v258:
            try:
                import difflib as _v258_difflib
                old_plain_rows = []
                if (not repair_extra_rows_v258) and len(prev_snapshot) >= old_managed_rows_v258:
                    for i in range(old_managed_rows_v258):
                        prow = prev_snapshot[i] if isinstance(prev_snapshot[i], list) else []
                        old_plain_rows.append([_plain_from_json(x) for x in prow])
                else:
                    for i in range(old_managed_rows_v258):
                        vals = (existing_rows[i] or {}).get('values') or [] if i < len(existing_rows) else []
                        old_plain_rows.append([_v239_google_plain_user_value(x) for x in vals[:max(prev_managed_cols, max_cols)]])
                new_plain_rows = [[_v239_google_target_plain((r or [])[c] if c < len(r or []) else '') for c in range(max_cols)] for r in rows]
                old_keys = [_row_identity(x) for x in old_plain_rows]
                new_keys = [_row_identity(x) for x in new_plain_rows]
                matcher = _v258_difflib.SequenceMatcher(a=old_keys, b=new_keys, autojunk=False)
                candidate_plan = []
                candidate_inserted = set()
                candidate_map = {}
                deleted_old = 0
                for tag, i1, i2, j1, j2 in matcher.get_opcodes():
                    old_n, new_n = i2 - i1, j2 - j1
                    if tag == 'equal':
                        for k in range(new_n):
                            candidate_map[j1 + k] = i1 + k
                    elif tag == 'insert':
                        if new_n:
                            candidate_plan.append((j1, new_n))
                            candidate_inserted.update(range(j1, j2))
                    elif tag == 'replace':
                        common = min(old_n, new_n)
                        for k in range(common):
                            candidate_map[j1 + k] = i1 + k
                        if new_n > old_n:
                            start_new = j1 + common
                            extra = new_n - old_n
                            candidate_plan.append((start_new, extra))
                            candidate_inserted.update(range(start_new, start_new + extra))
                        elif old_n > new_n:
                            deleted_old += old_n - new_n
                    elif tag == 'delete':
                        deleted_old += old_n
                planned = sum(n for _, n in candidate_plan)
                # Pure shrink (or pure growth) can be mapped deterministically.
                # Mixed delete+insert migrations remain on conservative fallback.
                if (row_shrink_v258 and planned == 0 and deleted_old == row_shrink_v258) or (row_growth and deleted_old == 0 and planned == row_growth):
                    row_insert_plan = sorted(candidate_plan)
                    inserted_row_indices = set(candidate_inserted)
                    target_to_old_row = candidate_map
                    if row_shrink_v258:
                        row_copy_map_v258 = {int(j): int(i) for j, i in candidate_map.items() if int(i) != int(j)}
            except Exception as _v258_rowdiff_exc:
                try: bot_journal('google_row_compact_warn_v258', target_chat_id, str(_v258_rowdiff_exc)[:300], 'WARN')
                except Exception: pass
                row_insert_plan = []
                row_copy_map_v258 = {}
            if row_growth and not row_insert_plan:
                # Conservative fallback for ambiguous growth: still protect all
                # user content below the previous table boundary.
                row_insert_plan = [(old_managed_rows_v258, row_growth)]
                inserted_row_indices = set(range(old_managed_rows_v258, old_managed_rows_v258 + row_growth))
                target_to_old_row = {i: i for i in range(min(len(rows), old_managed_rows_v258))}
            # For ambiguous shrink we never delete physical Google rows. Values
            # remain protected; a later clean alignment can compact them safely.
            for start_idx, count in row_insert_plan:
                req.append({'insertDimension': {'range': {'sheetId': sheet_id, 'dimension': 'ROWS', 'startIndex': start_idx, 'endIndex': start_idx + count}, 'inheritFromBefore': True}})
        if col_growth:
            req.append({'insertDimension': {'range': {'sheetId': sheet_id, 'dimension': 'COLUMNS', 'startIndex': prev_managed_cols, 'endIndex': prev_managed_cols + col_growth}, 'inheritFromBefore': True}})

        added = 0
        updated = 0
        unchanged = 0
        manual_values_preserved = 0
        manual_preserved_cells = set()

        if created_new:
            if cell_rows:
                req.append({'updateCells': {'range': {'sheetId': sheet_id, 'startRowIndex': 0, 'endRowIndex': len(rows), 'startColumnIndex': 0, 'endColumnIndex': max_cols}, 'rows': cell_rows, 'fields': 'userEnteredValue,note,userEnteredFormat'}})
                added = len(rows)
            req.append({'updateDimensionProperties': {'range': {'sheetId': sheet_id, 'dimension': 'COLUMNS', 'startIndex': 0, 'endIndex': 1}, 'properties': {'pixelSize': 95}, 'fields': 'pixelSize'}})
            if max_cols >= 2:
                req.append({'updateDimensionProperties': {'range': {'sheetId': sheet_id, 'dimension': 'COLUMNS', 'startIndex': 1, 'endIndex': 2}, 'properties': {'pixelSize': 320}, 'fields': 'pixelSize'}})
            if max_cols >= 3:
                req.append({'updateDimensionProperties': {'range': {'sheetId': sheet_id, 'dimension': 'COLUMNS', 'startIndex': 2, 'endIndex': max_cols}, 'properties': {'pixelSize': 115}, 'fields': 'pixelSize'}})
        else:
            for idx, row0 in enumerate(rows):
                target = list(row0 or [])
                # Rows added beyond the previous managed boundary are physically
                # inserted above the user's tail, so it is safe to apply bot style
                # and generated notes only to those brand-new rows.
                if idx in inserted_row_indices:
                    req.append({'updateCells': {'range': {'sheetId': sheet_id, 'startRowIndex': idx, 'endRowIndex': idx + 1, 'startColumnIndex': 0, 'endColumnIndex': max_cols}, 'rows': [cell_rows[idx]], 'fields': 'userEnteredValue,note,userEnteredFormat'}})
                    added += 1
                    continue

                old_idx = int(target_to_old_row.get(idx, idx))
                old_vals = (existing_rows[old_idx] or {}).get('values') or [] if old_idx < len(existing_rows) else []
                if idx in row_copy_map_v258 and old_idx != idx:
                    # Move the logical row as a whole so user note/color follows
                    # the finance row during compaction. Only managed columns are
                    # copied; anything to the right is untouched.
                    req.append({'copyPaste': {'source': {'sheetId': sheet_id, 'startRowIndex': old_idx, 'endRowIndex': old_idx + 1, 'startColumnIndex': 0, 'endColumnIndex': max_cols}, 'destination': {'sheetId': sheet_id, 'startRowIndex': idx, 'endRowIndex': idx + 1, 'startColumnIndex': 0, 'endColumnIndex': max_cols}, 'pasteType': 'PASTE_NORMAL', 'pasteOrientation': 'NORMAL'}})
                changed_cols = []
                # Existing columns: values only. Notes and formatting are owned by
                # the user once the cell exists and are never touched again.
                existing_col_limit = min(max_cols, prev_managed_cols if prev_managed_cols > 0 else max_cols)
                for c in range(existing_col_limit):
                    want = _v239_google_target_plain(target[c] if c < len(target) else '')
                    old_c = c + 1 if remove_v256_expense_col and c >= 3 else c
                    got = _v239_google_plain_user_value(old_vals[old_c] if old_c < len(old_vals) else {})
                    prev = None
                    if old_idx < len(prev_snapshot) and isinstance(prev_snapshot[old_idx], list) and old_c < len(prev_snapshot[old_idx]):
                        prev = _plain_from_json(prev_snapshot[old_idx][old_c])
                    google_formula_damaged_v258 = bool(isinstance(got, tuple) and len(got) == 2 and got[0] == 'formula' and '#REF!' in str(got[1] or '').upper())
                    manual_owned = prev is not None and (not google_formula_damaged_v258) and (not _v244_google_values_equivalent(got, prev)) and (not _is_blank_plain(got))
                    if manual_owned and (not _v244_google_values_equivalent(want, got)):
                        manual_values_preserved += 1
                        manual_preserved_cells.add((idx, c))
                        continue

                    # v254: Google automatically rewrites formula references when
                    # insertDimension moves rows. Our comparison was made against
                    # the PRE-insert grid, so a formula that looked unchanged can
                    # become SUM(C34) while the intended bot formula is SUM(C33).
                    # Re-assert every bot-owned formula in the same batch whenever
                    # physical rows are inserted. User-edited formulas remain safe.
                    force_formula_after_insert = bool(row_insert_plan and want[0] == 'formula' and (prev is None or _v244_google_values_equivalent(got, prev)))
                    if _v244_google_values_equivalent(want, got) and not force_formula_after_insert:
                        continue
                    if manual_owned:
                        manual_values_preserved += 1
                        manual_preserved_cells.add((idx, c))
                        continue
                    changed_cols.append(c)
                for a, b in _segments(changed_cols):
                    vals = [{'userEnteredValue': _google_cell_value(target[c] if c < len(target) else '')} for c in range(a, b)]
                    req.append({'updateCells': {'range': {'sheetId': sheet_id, 'startRowIndex': idx, 'endRowIndex': idx + 1, 'startColumnIndex': a, 'endColumnIndex': b}, 'rows': [{'values': vals}], 'fields': 'userEnteredValue'}})

                # Newly added columns are physically inserted before anything the
                # user may have placed to the right. They are blank/new, so bot
                # formatting and generated notes are safe there.
                if col_growth and max_cols > prev_managed_cols:
                    a, b = prev_managed_cols, max_cols
                    vals = cell_rows[idx]['values'][a:b]
                    if vals:
                        req.append({'updateCells': {'range': {'sheetId': sheet_id, 'startRowIndex': idx, 'endRowIndex': idx + 1, 'startColumnIndex': a, 'endColumnIndex': b}, 'rows': [{'values': vals}], 'fields': 'userEnteredValue,note,userEnteredFormat'}})

                if changed_cols or (col_growth and max_cols > prev_managed_cols):
                    updated += 1
                else:
                    unchanged += 1

            # Shrink safely: never blind-clear the old tail. We only remove an
            # old bot value if v252 has a snapshot proving the current value is
            # still exactly what the bot wrote previously. Notes/colors survive.
            stale_tail = max(0, old_managed_rows_v258 - len(rows))
            if stale_tail > 0 and repair_extra_rows_v258:
                # These rows are inside the bot's REAL terminal boundary but were
                # invisible to the old metadata. Clear only VALUES in the stale
                # bot tail; notes/colors remain untouched, and rows below the final
                # bot terminal marker are not addressed at all. This removes old
                # duplicate summaries / mixed USD rows without erasing user data.
                for idx in range(len(rows), old_managed_rows_v258):
                    old_vals = (existing_rows[idx] or {}).get('values') or [] if idx < len(existing_rows) else []
                    clear_cols = []
                    for c in range(min(max_cols, len(old_vals))):
                        got = _v239_google_plain_user_value(old_vals[c] if c < len(old_vals) else {})
                        if not _is_blank_plain(got):
                            clear_cols.append(c)
                    for a, b in _segments(clear_cols):
                        req.append({'updateCells': {'range': {'sheetId': sheet_id, 'startRowIndex': idx, 'endRowIndex': idx + 1, 'startColumnIndex': a, 'endColumnIndex': b}, 'rows': [{'values': [{} for _ in range(a, b)]}], 'fields': 'userEnteredValue'}})
            elif stale_tail > 0 and prev_snapshot:
                for idx in range(len(rows), min(old_managed_rows_v258, len(prev_snapshot))):
                    old_vals = (existing_rows[idx] or {}).get('values') or [] if idx < len(existing_rows) else []
                    clear_cols = []
                    prev_row = prev_snapshot[idx] if idx < len(prev_snapshot) and isinstance(prev_snapshot[idx], list) else []
                    for c in range(min(prev_managed_cols, len(prev_row))):
                        got = _v239_google_plain_user_value(old_vals[c] if c < len(old_vals) else {})
                        prev = _plain_from_json(prev_row[c])
                        damaged_formula_v258 = bool(isinstance(got, tuple) and len(got) == 2 and got[0] == 'formula' and '#REF!' in str(got[1] or '').upper())
                        if (not _is_blank_plain(got)) and (_v244_google_values_equivalent(got, prev) or damaged_formula_v258):
                            clear_cols.append(c)
                    for a, b in _segments(clear_cols):
                        req.append({'updateCells': {'range': {'sheetId': sheet_id, 'startRowIndex': idx, 'endRowIndex': idx + 1, 'startColumnIndex': a, 'endColumnIndex': b}, 'rows': [{'values': [{} for _ in range(a, b)]}], 'fields': 'userEnteredValue'}})

        if req:
            upd = _google_request_guarded('v252_non_destructive_upsert', requests.post, f'https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}:batchUpdate', headers=headers, json={'requests': req}, timeout=90, attempts=1)
            if upd.status_code >= 300:
                raise RuntimeError(f'Google Sheets non-destructive update {upd.status_code}: {upd.text[:500]}')

        escaped = str(actual_tab_title).replace("'", "''")
        verify = _google_request_guarded('v252_verify_incremental', requests.get, f'https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}', headers=headers, params={'includeGridData': 'true', 'ranges': f"'{escaped}'!A1:{_xlsx_col_name(max_cols)}{max(1, len(rows))}", 'fields': 'sheets(data(rowData(values(userEnteredValue,note))))'}, timeout=60, attempts=2)
        if verify.status_code >= 300:
            raise RuntimeError(f'Google Sheets incremental verify {verify.status_code}: {verify.text[:500]}')
        vr = ((verify.json().get('sheets') or [{}])[0].get('data') or [{}])[0].get('rowData') or []
        for idx, row0 in enumerate(rows):
            old_vals = (vr[idx] or {}).get('values') or [] if idx < len(vr) else []
            for c in range(max_cols):
                if (idx, c) in manual_preserved_cells:
                    continue
                want = _v239_google_target_plain((row0 or [])[c] if c < len(row0 or []) else '')
                got = _v239_google_plain_user_value(old_vals[c] if c < len(old_vals) else {})
                if not _v244_google_values_equivalent(want, got):
                    raise RuntimeError(f'Google incremental verify mismatch row={idx + 1} col={c + 1}; want={want}; got={got}')

        row_hash = hashlib.sha256(json.dumps(rows, ensure_ascii=False, sort_keys=False, separators=(',', ':'), default=str).encode('utf-8')).hexdigest()
        snapshot = [[_plain_json((row or [])[c] if c < len(row or []) else '') for c in range(max_cols)] for row in rows]
        try:
            SQLITE.set_meta('google_sync_v239', sync_key, {'tab': tab_title, 'sheet_id_v254': int(sheet_id), 'sheet_title_actual_v254': str(actual_tab_title), 'tenant_id': str(tid), 'chat_id': target_chat_id, 'managed_rows': len(rows), 'managed_cols': max_cols, 'managed_values_v252': snapshot, 'row_hash': row_hash, 'synced_at': now_local().isoformat(timespec='microseconds'), 'manual_values_preserved': manual_values_preserved})
        except Exception:
            pass
        url = f'https://docs.google.com/spreadsheets/d/{spreadsheet_id}/edit#gid={sheet_id}'

    try:
        tenant_google_history(tid, 'thuwed_non_destructive_upsert_v254', actual_tab_title, ok=True, chat_id=target_chat_id, url=url, added=added, updated=updated, unchanged=unchanged, stale_tail=stale_tail if 'stale_tail' in locals() else 0, manual_values_preserved=manual_values_preserved, row_growth=row_growth, col_growth=col_growth)
        tenant_google_persist(tid, 'tenant_google_runtime_v252')
        try:
            bot_journal('google_non_destructive_upsert_v254', target_chat_id, f'logical_tab={tab_title}; actual_tab={actual_tab_title}; sheetId={sheet_id}; added={added}; updated={updated}; unchanged={unchanged}; row_growth={row_growth}; row_shrink={row_shrink_v258}; row_copies={len(row_copy_map_v258)}; col_growth={col_growth}; manual_values_preserved={manual_values_preserved}; stale_tail_preserved={stale_tail if "stale_tail" in locals() else 0}')
        except Exception:
            pass
    except Exception:
        pass
    return url

_V261_GOOGLE_SYNC_ENGINES = {'previous', 'fixed', 'new'}

def _v261_google_sync_engine(target_chat_id: int) -> str:
    """Per-space Google sync engine. v261 defaults to the historical incremental sync."""
    cid = int(target_chat_id)
    mode = ''
    try:
        tid = _v149_tenant_id(None, cid) if callable(globals().get('_v149_tenant_id')) else tenant_id_for_chat(cid, create=False)
        cfg = tenant_google_config(str(tid))
        mode = str(cfg.setdefault('export_settings', {}).get('sync_engine_v261') or '').strip().lower()
    except Exception:
        try:
            mode = str(get_chat_store(cid).setdefault('settings', {}).get('google_sync_engine_v261') or '').strip().lower()
        except Exception:
            mode = ''
    return mode if mode in _V261_GOOGLE_SYNC_ENGINES else 'previous'

def _v261_google_sync_engine_label(mode: str) -> str:
    return {
        'previous': 'ПРЕДЫДУЩАЯ',
        'fixed': 'ИСПРАВЛЕННАЯ',
        'new': 'НОВАЯ',
    }.get(str(mode or '').strip().lower(), 'ПРЕДЫДУЩАЯ')

def _v261_set_google_sync_engine(target_chat_id: int, mode: str) -> str:
    cid = int(target_chat_id)
    mode = str(mode or '').strip().lower()
    if mode not in _V261_GOOGLE_SYNC_ENGINES:
        mode = 'previous'
    tid = ''
    persisted = False
    try:
        tid = _v149_tenant_id(None, cid) if callable(globals().get('_v149_tenant_id')) else tenant_id_for_chat(cid, create=False)
        cfg = tenant_google_config(str(tid))
        cfg.setdefault('export_settings', {})['sync_engine_v261'] = mode
        try:
            tenant_google_history(str(tid), 'sync_engine_v261', mode, ok=True, chat_id=cid)
        except Exception:
            pass
        tenant_google_persist(str(tid), 'google_sync_engine_v261')
        persisted = True
    except Exception:
        try:
            get_chat_store(cid).setdefault('settings', {})['google_sync_engine_v261'] = mode
            save_data(data, root_only=True)
            persisted = True
        except Exception:
            pass
    try:
        bot_journal('google_sync_engine_v261', cid, f'mode={mode}; tenant={tid or "fallback"}; persisted={int(persisted)}')
    except Exception:
        pass
    return mode

def _v167_google_upsert_named_tab(tab_title: str, rows: list[list], target_chat_id: int, layout: str='category', annotations_override: dict | None=None) -> str:
    """v261 selectable Google sync engine.

    previous — v239 incremental sync: bot data wins inside the managed table;
    fixed    — v259 non-destructive sync preserving manual user edits where possible;
    new      — v260 non-destructive sync plus new-sheet fallback on Constitution block.
    """
    mode = _v261_google_sync_engine(int(target_chat_id))
    fn = _v261_google_upsert_previous
    if mode == 'fixed':
        fn = _v261_google_upsert_fixed
    elif mode == 'new':
        fn = _v261_google_upsert_new
    try:
        bot_journal('google_sync_engine_run_v261', int(target_chat_id), f'mode={mode}; tab={str(tab_title)[:120]}')
    except Exception:
        pass
    return fn(tab_title, rows, int(target_chat_id), layout=layout, annotations_override=annotations_override)


def _v228_google_retry_delay_seconds(retry_count: int) -> int:
    n = max(1, int(retry_count or 1))
    if n == 1:
        return 60
    if n == 2:
        return 180
    if n == 3:
        return 600
    return 900

def _v228_google_latest_due(now_dt, mode: str):
    """Return (run_key, target_day, selected_hhmm) for the latest due daily run.

    A daily backup at 05:01 finalizes the PREVIOUS calendar day.  Before today's
    05:01, yesterday's 05:01 remains the latest due run, which makes deploy/hibernate
    catch-up reliable instead of silently skipping a missed day.
    """
    mode = str(mode or '')
    selected = '00:01' if mode == 'd0001' else '05:01'
    hh, mm = [int(x) for x in selected.split(':', 1)]
    due = now_dt.replace(hour=hh, minute=mm, second=0, microsecond=0)
    if now_dt < due:
        due = due - _v167_timedelta(days=1)
    run_date = due.strftime('%Y-%m-%d')
    target_day = (due - _v167_timedelta(days=1)).strftime('%Y-%m-%d')
    return (f'{run_date}@{selected}', target_day, selected)

def _v228_google_next_daily(now_dt, mode: str):
    selected = '00:01' if str(mode) == 'd0001' else '05:01'
    hh, mm = [int(x) for x in selected.split(':', 1)]
    nxt = now_dt.replace(hour=hh, minute=mm, second=0, microsecond=0)
    if nxt <= now_dt:
        nxt = nxt + _v167_timedelta(days=1)
    target_day = (nxt - _v167_timedelta(days=1)).strftime('%Y-%m-%d')
    return (nxt, target_day)

def _v19_google_target_configured(target_chat_id: int) -> bool:
    """Local-only preflight. Missing Google target is a configuration wait state, not a retry storm."""
    try:
        tid = str(_v149_tenant_id(target_chat_id=int(target_chat_id)))
        gcfg = tenant_google_config(tid, create=False) if callable(globals().get('tenant_google_config')) else {}
        raw = str((gcfg or {}).get('spreadsheet_id') or '').strip()
        if (not raw) and tid == str(globals().get('TENANT_PLATFORM_ID') or ''):
            raw = str(globals().get('_V149_PLATFORM_GOOGLE_SHEET') or _v167_os.getenv('GOOGLE_SHEETS_SPREADSHEET_ID', '') or '').strip()
        return bool(raw)
    except Exception:
        return False


def _v19_google_suspend_missing_target(target_chat_id: int, cfg: dict | None=None, reason: str='schedule') -> bool:
    cfg = cfg if isinstance(cfg, dict) else _v167_google_schedule_cfg(int(target_chat_id))
    first = not bool(cfg.get('paused_missing_target_r19'))
    if not first:
        return False
    cfg['paused_missing_target_r19'] = True
    cfg['paused_missing_target_at_r19'] = now_local().isoformat(timespec='seconds')
    cfg['pending_run_key'] = ''
    cfg['pending_since_ts'] = 0.0
    cfg['retry_count'] = 0
    cfg['next_retry_ts'] = 0.0
    cfg['last_error'] = 'Google Таблица не выбрана — автообновление ожидает настройки /google.'
    _v167_persist_schedule(int(target_chat_id))
    if first:
        try:
            bot_journal('google_auto_paused_missing_target_r19', int(target_chat_id), str(reason or 'schedule')[:160], 'WARN')
        except Exception:
            pass
    return False


def _v19_google_resume_if_target_ready(target_chat_id: int, cfg: dict | None=None) -> bool:
    cfg = cfg if isinstance(cfg, dict) else _v167_google_schedule_cfg(int(target_chat_id), create=False)
    if not isinstance(cfg, dict) or not cfg:
        return False
    if not _v19_google_target_configured(int(target_chat_id)):
        return False
    if cfg.pop('paused_missing_target_r19', None) is not None:
        cfg.pop('paused_missing_target_at_r19', None)
        if str(cfg.get('last_error') or '').startswith('Google Таблица не выбрана'):
            cfg['last_error'] = ''
        cfg['last_attempt_key'] = ''
        cfg['pending_run_key'] = ''
        cfg['pending_since_ts'] = 0.0
        cfg['retry_count'] = 0
        cfg['next_retry_ts'] = 0.0
        _v167_persist_schedule(int(target_chat_id))
        try:
            bot_journal('google_auto_resumed_target_ready_r19', int(target_chat_id), 'Google target configured')
        except Exception:
            pass
    return True


def _v167_google_update_target(target_chat_id: int, reason: str='schedule', run_key: str='', target_day: str=''):
    target_chat_id = int(target_chat_id)
    run_key = str(run_key or '')
    target_day = str(target_day or '')[:10]
    with _V167_GOOGLE_LOCK:
        if target_chat_id in _V167_GOOGLE_RUNNING:
            return False
        _V167_GOOGLE_RUNNING.add(target_chat_id)
    cfg = _v167_google_schedule_cfg(target_chat_id)
    try:
        if not _v19_google_target_configured(target_chat_id):
            return _v19_google_suspend_missing_target(target_chat_id, cfg, reason)
        _v19_google_resume_if_target_ready(target_chat_id, cfg)
        day = target_day or today_key()
        start_key, end_key = _v167_thuwed_bounds(day)
        tab = _v167_period_title(start_key, end_key)
        if run_key:
            cfg['last_attempt_key'] = run_key
            cfg['last_attempt_at'] = now_local().isoformat(timespec='seconds')
            cfg['pending_run_key'] = run_key
            cfg['pending_since_ts'] = _v163_time.time()
            cfg['last_target_day'] = day
            cfg['last_target_period'] = tab
            try:
                bot_journal('google_schedule_started_v228', target_chat_id, f'run={run_key}; day={day}; tab={tab}; reason={reason}')
            except Exception:
                pass
        _r40_q = globals().get('_r40_google_query_submit')
        _r40_w = globals().get('_r40_google_wait')
        if callable(_r40_q) and callable(_r40_w):
            _r40_jid = _r40_q(tab, target_chat_id, start_key, end_key, 0, 0, layout='category', include_annotations=True, notify_result=False, recipient_chat_id=target_chat_id)
            _r40_ok, url, _r40_err = _r40_w(_r40_jid, timeout=900)
            if not _r40_ok:
                raise RuntimeError(_r40_err or f'Google HEAVY job {_r40_jid} failed')
        else:
            rows = build_exact_category_stats_xlsx_rows(target_chat_id, start_key, 0, end_key, 0)
            url = _v167_google_upsert_named_tab(tab, rows, target_chat_id, layout='category')
        cfg['last_ok_at'] = now_local().isoformat(timespec='seconds')
        cfg['last_error'] = ''
        cfg['last_period'] = tab
        if run_key:
            cfg['last_success_key'] = run_key
            cfg['last_run_key'] = run_key
            cfg['pending_run_key'] = ''
            cfg['pending_since_ts'] = 0.0
            cfg['retry_count'] = 0
            cfg['next_retry_ts'] = 0.0
        _v167_persist_schedule(target_chat_id)
        try:
            bot_journal('google_thuwed_updated', target_chat_id, f"tab={tab}; day={day}; run={run_key or '-'}; reason={reason}; url={url[:120]}")
        except Exception:
            pass
        return True
    except Exception as exc:
        cfg['last_error'] = str(exc)[:500]
        if run_key:
            cfg['pending_run_key'] = ''
            cfg['pending_since_ts'] = 0.0
            cfg['retry_count'] = int(cfg.get('retry_count') or 0) + 1
            delay = _v228_google_retry_delay_seconds(cfg['retry_count'])
            cfg['next_retry_ts'] = _v163_time.time() + delay
            try:
                bot_journal('google_schedule_retry_v228', target_chat_id, f"run={run_key}; day={target_day}; retry={cfg['retry_count']}; in={delay}s; error={str(exc)[:220]}", 'WARN')
            except Exception:
                pass
        _v167_persist_schedule(target_chat_id)
        try:
            log_error(f'v167 google Thu-Wed update chat={target_chat_id}: {exc}')
        except Exception:
            pass
        return False
    finally:
        with _V167_GOOGLE_LOCK:
            _V167_GOOGLE_RUNNING.discard(target_chat_id)

def _v167_known_chat_ids():
    out = set()
    try:
        if OWNER_ID:
            out.add(int(OWNER_ID))
    except Exception:
        pass
    try:
        for key in (data.get('chats', {}) or {}).keys():
            try:
                out.add(int(key))
            except Exception:
                pass
    except Exception:
        pass
    return sorted(out)

def _v169_google_mode(cfg: dict | None) -> str:
    cfg = cfg if isinstance(cfg, dict) else {}
    mode = str(cfg.get('mode') or '').strip().lower()
    if mode not in {'manual', 'change', 'm15', 'h1', 'd0001', 'd0501'}:
        if not bool(cfg.get('enabled', True)):
            mode = 'manual'
        else:
            mode = 'd0001' if str(cfg.get('time') or '05:01') == '00:01' else 'd0501'
    return mode

def _v169_google_mode_label(mode: str) -> str:
    return {'manual': '✋ Только вручную', 'change': '⚡ После изменений', 'm15': '🕒 Каждые 15 минут', 'h1': '🕐 Каждый час', 'd0001': '🌙 Ежедневно 00:01', 'd0501': '🌅 Ежедневно 05:01'}.get(str(mode), '✋ Только вручную')

def _v244_google_initial_sync_fire(target_chat_id: int, reason: str='mode-change-initial', retry: int=0) -> None:
    cid = int(target_chat_id)
    cfg = _v167_google_schedule_cfg(cid, create=False)
    if not cfg or _v169_google_mode(cfg) != 'change':
        return
    if _v169_google_enqueue(cid, str(reason or 'mode-change-initial')):
        try:
            bot_journal('google_change_initial_enqueued_v244', cid, str(reason or 'mode-change-initial'))
        except Exception:
            pass
        return
    if int(retry or 0) >= 6:
        try:
            bot_journal('google_change_initial_queue_busy_v244', cid, f'reason={reason}; retries={retry}', 'WARN')
        except Exception:
            pass
        return
    delay = min(30.0, 1.5 * 2 ** int(retry or 0))
    try:
        DELAYED_SCHEDULER.schedule(f'google-change-initial:{cid}', delay, _v244_google_initial_sync_fire, cid, str(reason or 'mode-change-initial'), int(retry or 0) + 1)
    except Exception:
        pass

def _v244_google_resume_after_recovery(reason: str='recovery') -> None:
    """After verified recovery, refresh every chat that is configured for change-sync."""
    for cid in _v167_known_chat_ids():
        try:
            cfg = _v167_google_schedule_cfg(int(cid), create=False)
            if cfg and _v169_google_mode(cfg) == 'change':
                DELAYED_SCHEDULER.schedule(f'google-recovery-sync:{int(cid)}', 0.5, _v244_google_initial_sync_fire, int(cid), 'recovery-sync:' + str(reason or 'recovery'), 0)
        except Exception:
            continue

def _v169_set_google_mode(target_chat_id: int, mode: str) -> dict:
    mode = str(mode or 'manual').strip().lower()
    if mode not in {'manual', 'change', 'm15', 'h1', 'd0001', 'd0501'}:
        mode = 'manual'
    cfg = _v167_google_schedule_cfg(int(target_chat_id))
    previous_mode = _v169_google_mode(cfg)
    cfg['mode'] = mode
    cfg['enabled'] = mode != 'manual'
    if mode == 'd0001':
        cfg['time'] = '00:01'
    elif mode == 'd0501':
        cfg['time'] = '05:01'
    cfg['last_run_key'] = ''
    cfg['last_success_key'] = ''
    cfg['last_attempt_key'] = ''
    cfg['pending_run_key'] = ''
    cfg['pending_since_ts'] = 0.0
    cfg['retry_count'] = 0
    cfg['next_retry_ts'] = 0.0
    _v167_persist_schedule(int(target_chat_id))
    if mode == 'change' and previous_mode != 'change':
        try:
            DELAYED_SCHEDULER.cancel(f'google-change-initial:{int(target_chat_id)}')
            DELAYED_SCHEDULER.schedule(f'google-change-initial:{int(target_chat_id)}', 0.25, _v244_google_initial_sync_fire, int(target_chat_id), 'mode-change-initial', 0)
        except Exception:
            pass
    return cfg

def _v169_google_settings_text(target_chat_id: int) -> str:
    target_chat_id = int(target_chat_id)
    cfg = _v167_google_schedule_cfg(target_chat_id)
    if _v19_google_target_configured(target_chat_id):
        _v19_google_resume_if_target_ready(target_chat_id, cfg)
    mode = _v169_google_mode(cfg)
    start_key, end_key = _v167_thuwed_bounds(today_key())
    tab = _v167_period_title(start_key, end_key)
    last_ok = str(cfg.get('last_ok_at') or '—')
    last_attempt = str(cfg.get('last_attempt_at') or '—')
    last_error = str(cfg.get('last_error') or '').strip()
    upcoming = '—'
    upcoming_period = '—'
    if mode in {'d0001', 'd0501'}:
        nxt, target_day = _v228_google_next_daily(now_local(), mode)
        s2, e2 = _v167_thuwed_bounds(target_day)
        upcoming_period = _v167_period_title(s2, e2)
        upcoming = f"{nxt.strftime('%d.%m.%y %H:%M')} → день {fmt_date_ddmmyy(target_day)}"
    lines = ['☁️ GOOGLE ТАБЛИЦА ЧТ–СР', '', f'Чат: {get_chat_display_name(target_chat_id)}', f'Текущий лист: {tab}', f'Режим обновления: {_v169_google_mode_label(mode)}', f'Sync: {_v261_google_sync_engine_label(_v261_google_sync_engine(target_chat_id))}', f'Последняя попытка: {last_attempt}', f'Последнее успешное: {last_ok}', f'Следующий автобэкап: {upcoming}', f'Лист следующего автобэкапа: {upcoming_period}']
    if last_error:
        lines.append(f'Последняя ошибка: {last_error[:350]}')
    lines += ['', 'Период листа всегда четверг → среда. При наступлении нового четверга создаётся новый лист; внутри периода обновляется тот же лист.', '', 'Выберите способ/период обновления ниже.', '', 'Ф240⏰']
    return '\n'.join(lines)[:3900]

def _v169_google_settings_keyboard(target_chat_id: int, day_key: str | None=None):
    target_chat_id = int(target_chat_id)
    day_key = str(day_key or get_chat_store(target_chat_id).get('current_view_day') or today_key())[:10]
    mode = _v169_google_mode(_v167_google_schedule_cfg(target_chat_id))
    kb = types.InlineKeyboardMarkup(row_width=2)

    def _b(label, value):
        mark = '✅ ' if mode == value else ''
        return IB(mark + label, callback_data=f'v169:gmode:{target_chat_id}:{value}')
    kb.row(_b('✋ Вручную', 'manual'), _b('⚡ После изменений', 'change'))
    kb.row(_b('🕒 15 минут', 'm15'), _b('🕐 1 час', 'h1'))
    kb.row(_b('🌙 00:01', 'd0001'), _b('🌅 05:01', 'd0501'))
    kb.row(IB('☁️ Обновить Чт–Ср сейчас', callback_data=f'v169:gnow:{target_chat_id}'))
    kb.row(IB('🔙 Назад в Инфо', callback_data=f'd:{day_key}:info'), IB('⬅️ Осн. окно', callback_data=f'd:{day_key}:back_main'))
    return kb

def _v169_google_enqueue(target_chat_id: int, reason: str, run_key: str='', target_day: str='') -> bool:
    target_chat_id = int(target_chat_id)
    key = f'google-thuwed:{target_chat_id}'
    pool = globals().get('EXPORT_TASK_POOL')
    if pool is not None:
        try:
            ok = bool(pool.submit_unique(key, _v167_google_update_target, target_chat_id, str(reason), str(run_key or ''), str(target_day or '')))
            if not ok:
                try:
                    bot_journal('google_thuwed_coalesced', target_chat_id, f'reason={reason}')
                except Exception:
                    pass
            return ok
        except Exception as exc:
            try:
                log_error(f'v169 Google queue {target_chat_id}: {exc}')
            except Exception:
                pass
    return False

def _v169_google_change_fire(target_chat_id: int):
    cfg = _v167_google_schedule_cfg(int(target_chat_id), create=False)
    if _v169_google_mode(cfg) != 'change':
        return
    if not _v19_google_target_configured(int(target_chat_id)):
        _v19_google_suspend_missing_target(int(target_chat_id), cfg, 'finance-change')
        return
    _v19_google_resume_if_target_ready(int(target_chat_id), cfg)
    if not _v169_google_enqueue(int(target_chat_id), 'finance-change'):
        try:
            DELAYED_SCHEDULER.schedule(f'google-change-retry:{int(target_chat_id)}', 15.0, _v169_google_change_fire, int(target_chat_id))
        except Exception:
            pass

def _v169_schedule_google_after_change(target_chat_id: int, reason: str='finance_changed') -> None:
    try:
        gate = globals().get('external_access_allowed_v233')
        if callable(gate) and (not gate('google')):
            return
        safe, _why = _v239_google_recovery_write_gate()
        if (not safe) and _v261_google_sync_engine(int(target_chat_id)) != 'new':
            return
        cfg = _v167_google_schedule_cfg(int(target_chat_id), create=False)
        if not cfg or _v169_google_mode(cfg) != 'change':
            return
        low = str(reason or '').casefold()
        mutation = low.startswith('finalize:') or any((x in low for x in ('finance', 'record', 'forward', 'edit', 'delete', 'add', 'new', 'insert', 'create', 'change', 'currency', 'reset', 'restore_csv')))
        if low and (not mutation):
            return
        DELAYED_SCHEDULER.schedule(f'google-change:{int(target_chat_id)}', 8.0, _v169_google_change_fire, int(target_chat_id))
    except Exception as exc:
        try:
            log_error(f'v169 schedule Google after change {target_chat_id}: {exc}')
        except Exception:
            pass

def _v167_google_scheduler_tick():
    try:
        gate = globals().get('external_access_allowed_v233')
        if callable(gate) and (not gate('google')):
            return
        if callable(globals().get('runtime_is_shutting_down')) and runtime_is_shutting_down():
            return
        if callable(globals().get('runtime_is_ready')) and (not runtime_is_ready()):
            return
        safe, why = _v239_google_recovery_write_gate()
        if not safe:
            try:
                last = float(globals().get('_V239_GOOGLE_RECOVERY_BLOCK_LOG', 0.0) or 0.0)
                nowm = time.monotonic()
                if nowm - last >= 900.0:
                    globals()['_V239_GOOGLE_RECOVERY_BLOCK_LOG'] = nowm
                    bot_journal('google_scheduler_blocked_recovery_v239', int(OWNER_ID or 0) or None, str(why)[:300], 'WARN')
            except Exception:
                pass
        now = now_local()
        date_key = now.strftime('%Y-%m-%d')
        minute = int(now.strftime('%M'))
        hour = int(now.strftime('%H'))
        now_ts = _v163_time.time()
        for cid in _v167_known_chat_ids():
            if (not safe) and _v261_google_sync_engine(int(cid)) != 'new':
                continue
            cfg = _v167_google_schedule_cfg(cid, create=False)
            if not cfg:
                continue
            mode = _v169_google_mode(cfg)
            if mode in {'manual', 'change'}:
                continue
            if not _v19_google_target_configured(int(cid)):
                _v19_google_suspend_missing_target(int(cid), cfg, 'scheduler')
                continue
            _v19_google_resume_if_target_ready(int(cid), cfg)
            run_key = ''
            reason = mode
            target_day = date_key
            if mode == 'm15':
                run_key = f'{date_key}@{hour:02d}:{minute // 15 * 15:02d}'
            elif mode == 'h1':
                run_key = f'{date_key}@{hour:02d}'
            elif mode in {'d0001', 'd0501'}:
                run_key, target_day, _selected = _v228_google_latest_due(now, mode)
            if not run_key or str(cfg.get('last_success_key') or '') == run_key:
                continue
            if str(cfg.get('pending_run_key') or '') == run_key and now_ts - float(cfg.get('pending_since_ts') or 0) < 300:
                continue
            if str(cfg.get('last_attempt_key') or '') == run_key and float(cfg.get('next_retry_ts') or 0) > now_ts:
                continue
            cfg['last_attempt_key'] = run_key
            cfg['last_attempt_at'] = now.isoformat(timespec='seconds')
            cfg['pending_run_key'] = run_key
            cfg['pending_since_ts'] = now_ts
            cfg['last_target_day'] = target_day
            s2, e2 = _v167_thuwed_bounds(target_day)
            cfg['last_target_period'] = _v167_period_title(s2, e2)
            _v167_persist_schedule(cid)
            queued = _v169_google_enqueue(cid, reason, run_key, target_day)
            if queued:
                try:
                    bot_journal('google_schedule_enqueued_v228', cid, f"run={run_key}; day={target_day}; tab={cfg['last_target_period']}; mode={mode}")
                except Exception:
                    pass
            else:
                cfg['pending_run_key'] = ''
                cfg['pending_since_ts'] = 0.0
                cfg['retry_count'] = int(cfg.get('retry_count') or 0) + 1
                delay = _v228_google_retry_delay_seconds(cfg['retry_count'])
                cfg['next_retry_ts'] = now_ts + delay
                _v167_persist_schedule(cid)
                try:
                    bot_journal('google_schedule_enqueue_retry_v228', cid, f"run={run_key}; retry={cfg['retry_count']}; in={delay}s", 'WARN')
                except Exception:
                    pass
    except Exception as exc:
        try:
            log_error(f'v169 google scheduler: {exc}')
        except Exception:
            pass
    finally:
        try:
            if not (callable(globals().get('runtime_is_shutting_down')) and runtime_is_shutting_down()):
                DELAYED_SCHEDULER.schedule('google-thuwed-scheduler', 20.0, _v167_google_scheduler_tick)
        except Exception:
            pass

def _v167_google_scheduler_loop():
    return _v167_google_scheduler_tick()

def _v167_start_google_scheduler():
    global _V167_GOOGLE_SCHEDULER_STARTED
    if _V167_GOOGLE_SCHEDULER_STARTED:
        return
    _V167_GOOGLE_SCHEDULER_STARTED = True
    DELAYED_SCHEDULER.schedule('google-thuwed-scheduler', 3.0, _v167_google_scheduler_tick)

def _v167_schedule_callback_filter(call):
    try:
        raw = str(getattr(call, 'data', '') or '')
        return raw.startswith('v167:g') or raw.startswith('v169:g') or raw.startswith('v261:gsync:')
    except Exception:
        return False

def _v167_schedule_callback(call):
    raw = str(getattr(call, 'data', '') or '')
    parts = raw.split(':')
    try:
        if raw.startswith('v261:gsync:'):
            target = int(parts[2]) if len(parts) > 2 else int(getattr(getattr(call, 'message', None), 'chat', None).id)
            mode = str(parts[3] if len(parts) > 3 else 'previous')
            uid = int(getattr(getattr(call, 'from_user', None), 'id', 0) or 0)
            if not (tenant_is_platform_owner_user(uid) or tenant_can_manage(uid, chat_id=target)):
                bot.answer_callback_query(call.id, 'Недостаточно прав', show_alert=True)
                return
            selected = _v261_set_google_sync_engine(target, mode)
            try:
                bot.answer_callback_query(call.id, 'Sync: ' + _v261_google_sync_engine_label(selected), show_alert=False)
            except Exception:
                pass
            try:
                safe_edit(bot, call, build_info_text(target), reply_markup=build_info_keyboard(target), parse_mode=None)
            except Exception:
                try:
                    v178_edit_reply_markup_async(call.message.chat.id, call.message.message_id, build_info_keyboard(target), 'google_sync_engine_v261')
                except Exception:
                    pass
            return
        if raw.startswith('v169:'):
            action = str(parts[1] if len(parts) > 1 else '')
            target = int(parts[2]) if len(parts) > 2 else int(getattr(getattr(call, 'message', None), 'chat', None).id)
            uid = int(getattr(getattr(call, 'from_user', None), 'id', 0) or 0)
            if not (tenant_is_platform_owner_user(uid) or tenant_can_manage(uid, chat_id=target)):
                bot.answer_callback_query(call.id, 'Недостаточно прав', show_alert=True)
                return
            if action == 'gmenu':
                try:
                    bot.answer_callback_query(call.id)
                except Exception:
                    pass
                safe_edit(bot, call, _v169_google_settings_text(target), reply_markup=_v169_google_settings_keyboard(target))
                return
            if action == 'gmode':
                mode = str(parts[3] if len(parts) > 3 else 'manual')
                cfg = _v169_set_google_mode(target, mode)
                try:
                    bot.answer_callback_query(call.id, _v169_google_mode_label(_v169_google_mode(cfg)))
                except Exception:
                    pass
                safe_edit(bot, call, _v169_google_settings_text(target), reply_markup=_v169_google_settings_keyboard(target))
                return
            if action == 'gnow':
                queued = _v169_google_enqueue(target, 'manual-info')
                try:
                    bot.answer_callback_query(call.id, 'Обновление поставлено в очередь' if queued else 'Обновление уже выполняется')
                except Exception:
                    pass
                safe_edit(bot, call, _v169_google_settings_text(target), reply_markup=_v169_google_settings_keyboard(target))
                return
            return
        target = int(parts[2]) if len(parts) > 2 else int(OWNER_ID or 0)
        uid = int(getattr(getattr(call, 'from_user', None), 'id', 0) or 0)
        if not (tenant_is_platform_owner_user(uid) or tenant_can_manage(uid, chat_id=target)):
            bot.answer_callback_query(call.id, 'Недостаточно прав', show_alert=True)
            return
        cfg = _v167_google_schedule_cfg(target)
        if parts[1] == 'gtoggle':
            if _v169_google_mode(cfg) == 'manual':
                _v169_set_google_mode(target, 'd0001' if str(cfg.get('time') or '05:01') == '00:01' else 'd0501')
                msg = 'Автообновление включено'
            else:
                _v169_set_google_mode(target, 'manual')
                msg = 'Автообновление выключено'
            cfg = _v167_google_schedule_cfg(target)
        elif parts[1] == 'gtime':
            code = str(parts[3] if len(parts) > 3 else '0501')
            cfg = _v169_set_google_mode(target, 'd0001' if code == '0001' else 'd0501')
            msg = f"Чт–Ср: ежедневно в {cfg['time']}"
        elif parts[1] == 'gnow':
            msg = 'Обновляю текущий лист Чт–Ср'
            _v169_google_enqueue(target, 'manual-f47')
        else:
            return
        try:
            bot.answer_callback_query(call.id, msg)
        except Exception:
            pass
        try:
            kb = _v167_copy.deepcopy(getattr(getattr(call, 'message', None), 'reply_markup', None))
            mode = _v169_google_mode(cfg)
            for row in getattr(kb, 'keyboard', []) or []:
                for btn in row:
                    cb = str(getattr(btn, 'callback_data', '') or '')
                    if cb == f'v167:gtoggle:{target}':
                        btn.text = ('✅ ' if mode != 'manual' else '⬜ ') + 'Google Чт–Ср авто'
                    elif cb == f'v167:gtime:{target}:0001':
                        btn.text = ('✅ ' if mode == 'd0001' else '') + '00:01'
                    elif cb == f'v167:gtime:{target}:0501':
                        btn.text = ('✅ ' if mode == 'd0501' else '') + '05:01'
            v178_edit_reply_markup_async(call.message.chat.id, call.message.message_id, kb, 'google_schedule_markup_v178')
        except Exception:
            pass
    except Exception as exc:
        try:
            log_error(f'v169 schedule callback {raw}: {exc}')
        except Exception:
            pass
        try:
            bot.answer_callback_query(call.id, 'Ошибка настройки Google', show_alert=True)
        except Exception:
            pass
try:
    WINDOW_MARKER_CONSTANTS.update({'v169:gmenu:*': 'Ф240', 'v169:gmode:*': 'Ф240', 'v169:gnow:*': 'Ф240', 'v261:gsync:*': 'Ф54'})
except Exception:
    pass

def _v168_mark_resolved_tz_rows():
    """Mark only TZ items explicitly fixed by this release; other old rows are merely archived."""
    changed = False
    try:
        _catalog, rows = _v160_annotation_roots()
        for row in rows or []:
            if not isinstance(row, dict) or str(row.get('status') or 'open').lower() != 'open':
                continue
            marker = str(row.get('marker') or '').upper()
            body = str(row.get('text') or '').casefold()
            resolved = marker == 'Ф2' and 'переключ' in body and ('владель' in body) or (marker == 'Ф91' and 'быстро' in body and ('обнов' in body) and ('ввода' in body or 'пересыл' in body or 'редакт' in body))
            if resolved:
                row['status'] = 'fixed'
                row['fixed_by_version'] = VERSION
                row['fixed_at'] = now_local().isoformat(timespec='seconds')
                changed = True
        return changed
    except Exception:
        return False

def _v167_archive_old_tz_once(force: bool=False):
    global _V167_TZ_ARCHIVE_VERSION
    current_version = str(globals().get('VERSION') or VERSION)
    if not force and _V167_TZ_ARCHIVE_VERSION == current_version:
        return
    _V167_TZ_ARCHIVE_VERSION = current_version
    try:
        _catalog, rows = _v160_annotation_roots()
        changed = False
        for row in rows:
            if not isinstance(row, dict):
                continue
            row_version = str(row.get('version') or '')
            status = str(row.get('status') or '').lower()
            if row_version != current_version and status not in {'archived', 'fixed'}:
                row['status'] = 'archived'
                row['archived_by_version'] = current_version
                row['archived_at'] = now_local().isoformat(timespec='seconds')
                changed = True
            elif not row_version:
                row['version'] = 'legacy'
                changed = True
        if changed:
            try:
                _v160_persist_annotations(int(OWNER_ID or 0))
            except Exception:
                pass
    except Exception:
        pass

def _v177_legacy_0321_v160_save_tz(chat_id: int, user_id: int, marker: str, body: str, source: dict) -> dict:
    if not callable(_V167_BASE_SAVE_TZ):
        raise RuntimeError('TZ storage unavailable')
    row = _V167_BASE_SAVE_TZ(chat_id, user_id, marker, body, source)
    try:
        row['version'] = VERSION
        row['status'] = 'open'
        row['archived_by_version'] = ''
        _v160_persist_annotations(chat_id)
    except Exception:
        pass
    return row
try:
    _v177_legacy_0321_v160_save_tz.__name__ = '_v160_save_tz'
except Exception:
    pass

def _v177_legacy_0326_v167_tz_export(kind: str):
    catalog, rows = _v160_annotation_roots()
    now_s = now_local().strftime('%Y-%m-%d %H:%M:%S')
    archive = kind == 'tz_archive'
    selected = []
    for row in list(rows or []):
        if not isinstance(row, dict):
            continue
        status = str(row.get('status') or 'open').lower()
        ver = str(row.get('version') or 'legacy')
        if archive:
            if status in {'archived', 'fixed'} or ver != VERSION:
                selected.append(row)
        elif status == 'open' and ver == VERSION:
            selected.append(row)
    title = 'АРХИВ ТЗ ПО ОКНАМ' if archive else 'ТЗ ПО ОКНАМ — ТЕКУЩАЯ ВЕРСИЯ'
    lines = [title, f'Версия выгрузки: {VERSION}', f'Создано: {now_s}', f'Записей: {len(selected)}', '']
    for row in selected:
        src = dict(row.get('source') or {})
        marker = str(row.get('marker') or '')
        lines.extend([f"[{row.get('at')}] {marker} — {row.get('window_name') or (catalog.get(marker) or {}).get('name') or 'без имени'}", f"Статус: {row.get('status') or 'open'}; версия: {row.get('version') or 'legacy'}", f"Источник: chat={src.get('chat_id') or '—'} msg={src.get('message_id') or '—'} callback={src.get('callback') or '—'}", str(row.get('text') or ''), '', '---', ''])
    return ('Архив_ТЗ_окон' if archive else 'ТЗ_окон_текущая_версия', '\n'.join(lines).rstrip() + '\n')
try:
    _v177_legacy_0326_v167_tz_export.__name__ = '_v167_tz_export'
except Exception:
    pass

def _canon_v160_export_text__001(kind: str):
    if kind in {'tz', 'tz_archive'}:
        return _v167_tz_export(kind)
    if callable(_V167_BASE_EXPORT_TZ):
        return _V167_BASE_EXPORT_TZ(kind)
    return ('export', '')

def _v167_send_tz_archive(chat_id: int):
    _file_job_progress('формирую архив ТЗ', force=True)
    base, content = _v160_export_text('tz_archive')
    folder = _v167_tempfile.mkdtemp(prefix='v167_tz_')
    path = _v167_os.path.join(folder, f"{base}_{now_local().strftime('%Y_%m_%d_%H%M%S')}.txt")
    try:
        with open(path, 'w', encoding='utf-8') as fh:
            fh.write(content)
        with open(path, 'rb') as fh:
            bot.send_document(int(chat_id), fh, caption=f'🗃 Архив ТЗ окон · {VERSION}')
        return True
    finally:
        try:
            import shutil as _v167_shutil
            _v167_shutil.rmtree(folder, ignore_errors=True)
        except Exception:
            pass

def _canon_v160_handle_special_callback__001(call, resolved: str) -> bool:
    if str(resolved) == 'v167:export_tz_archive':
        uid = int(getattr(getattr(call, 'from_user', None), 'id', 0) or 0)
        if not _v160_can_annotate(uid):
            try:
                bot.answer_callback_query(call.id, 'Только для владельца платформы', show_alert=True)
            except Exception:
                pass
            return True
        cid = int(call.message.chat.id)
        ok, reason = submit_interactive_file_job(cid, 'window_tz_archive', 'Архив ТЗ окон', _v167_send_tz_archive, cid)
        try:
            bot.answer_callback_query(call.id, 'Формирую архив' if ok else 'Файл уже формируется')
        except Exception:
            pass
        if not ok:
            try:
                send_and_auto_delete(cid, f"⏳ {reason or 'Сейчас уже формируется другой файл.'}", 10)
            except Exception:
                pass
        return True
    if callable(_V167_BASE_SPECIAL_CALLBACK):
        return bool(_V167_BASE_SPECIAL_CALLBACK(call, resolved))
    return False

def _v177_legacy_0318_v160_augment_markup(reply_markup, text: str, chat_id=None):
    kb = _V167_BASE_AUGMENT_MARKUP(reply_markup, text, chat_id) if callable(_V167_BASE_AUGMENT_MARKUP) else reply_markup
    try:
        if _v160_marker_from_text(text) == 'Ф89' and isinstance(kb, types.InlineKeyboardMarkup):
            callbacks = _v160_markup_callbacks(kb)
            if 'v167:export_tz_archive' not in callbacks:
                kb.row(IB('🗃 Скачать архив ТЗ', callback_data='v167:export_tz_archive'))
    except Exception:
        pass
    return kb
try:
    _v177_legacy_0318_v160_augment_markup.__name__ = '_v160_augment_markup'
except Exception:
    pass
try:
    WINDOW_MARKER_CONSTANTS.update({'v167:gtoggle:*': 'Ф47', 'v167:gtime:*': 'Ф47', 'v167:gnow:*': 'Ф47', 'v167:export_tz_archive': 'Ф239'})
except Exception:
    pass
try:
    if OWNER_ID:
        _v167_google_schedule_cfg(int(OWNER_ID), create=True)
except Exception:
    pass

def _v168_migrate_all_record_uids_once():
    gs = data.setdefault('_global_settings', {})
    if str(gs.get('record_uid_schema') or '') == 'v168':
        return 0
    changed = 0
    for cid_s in list((data.get('chats') or {}).keys()):
        try:
            changed += int(migrate_finance_record_uids(int(cid_s)) or 0)
        except Exception as exc:
            try:
                log_error(f'v168 startup UID migration {cid_s}: {exc}')
            except Exception:
                pass
    gs['record_uid_schema'] = 'v168'
    if changed:
        try:
            initialize_delta_baseline(data)
        except Exception:
            pass
        try:
            _mark_global_snapshot_pending()
        except Exception:
            pass
    try:
        scheduler = globals().get('V166_CONFIG_IO_SCHEDULER')
        if scheduler is not None:
            scheduler.schedule('v168-record-uid-schema', 0.1, lambda: save_data(data, root_only=True))
        else:
            save_data(data, root_only=True)
    except Exception:
        pass
    try:
        bot_journal('record_uid_migration_v168', int(OWNER_ID or 0), f'changed={changed}')
    except Exception:
        pass
    return changed
try:
    _V168_PREV_SET_WEBHOOK = _canon_set_webhook__001
    if callable(_V168_PREV_SET_WEBHOOK):

        def set_webhook():
            _v168_migrate_all_record_uids_once()
            try:
                gs = data.setdefault('_global_settings', {})
                if str(gs.get('finance_source_index_schema') or '') != 'v257':
                    migrated = 0
                    for cid_s in list((data.get('chats') or {}).keys()):
                        try: migrated += int(migrate_finance_source_index_v257(int(cid_s)) or 0)
                        except Exception as exc:
                            try: log_error(f'v257 finance source index migration {cid_s}: {exc}')
                            except Exception: pass
                    gs['finance_source_index_schema'] = 'v257'
                    try: save_data(data)
                    except Exception: pass
                    try: bot_journal('finance_source_index_migration_v257', int(OWNER_ID or 0), f'changed={migrated}')
                    except Exception: pass
            except Exception as exc:
                try: log_error(f'v257 finance source index startup: {exc}')
                except Exception: pass
            return _V168_PREV_SET_WEBHOOK()
except Exception:
    pass
_v167_archive_old_tz_once()
_V167_SCHEDULE_CALLBACK = 0
_v167_start_google_scheduler()
try:
    _V167_BASE_RUNTIME_MARK_READY = _v179_legacy_runtime_mark_ready
    if callable(_V167_BASE_RUNTIME_MARK_READY):

        def runtime_mark_ready(detail: str=''):
            result = _V167_BASE_RUNTIME_MARK_READY(detail)
            try:
                if _v168_mark_resolved_tz_rows():
                    _v160_persist_annotations(int(OWNER_ID or 0))
            except Exception:
                pass
            try:
                _v167_archive_old_tz_once(force=True)
            except Exception:
                pass
            try:
                if OWNER_ID:
                    _v167_google_schedule_cfg(int(OWNER_ID), create=True)
                    _v167_persist_schedule(int(OWNER_ID))
            except Exception:
                pass
            return result
except Exception:
    pass
try:
    _v177_legacy_0007_bot_journal('v169_installed', int(OWNER_ID or 0), 'main TZ button + immediate finance-forward edit UI + tri-state reminder merge + Google Thu-Wed update modes')
    _v177_legacy_0007_bot_journal('v170_journal_names_installed', int(OWNER_ID or 0), 'distinct human filenames; version words no longer misclassify downloads')
except Exception:
    pass
'v171: implement all open v169 window TZ items and reliability fixes.\n\nThe patch is intentionally loaded last.  It repairs active runtime hooks instead of\nediting old historical implementations, so one source of truth wins after module load.\n'
import gzip as _v171_gzip
import json as _v171_json
import os as _v171_os
import shutil as _v171_shutil
import sqlite3 as _v171_sqlite3
import tempfile as _v171_tempfile
import threading as _v171_threading
V171_FILE_MARKER = 'v171_all_tz_reliability'
V171_TZ_SCOPE_POLICY = 'global_all_contours_if_unspecified'
V171_TZ_SCOPE_TEXT = 'ТЗ без явно указанного чата, направления или контура применяется ко всему боту: ко всем направлениям и всем контурам.'
try:
    _v171_gs = data.setdefault('_global_settings', {})
    _v171_gs['tz_scope_policy_v171'] = V171_TZ_SCOPE_POLICY
    _v171_gs['tz_scope_policy_text_v171'] = V171_TZ_SCOPE_TEXT
except Exception:
    pass

def _v161_schedule_delete(chat_id: int, message_id: int, delay: float, prefix: str='delete') -> None:
    fn = globals().get('_v160_schedule_delete')
    if callable(fn):
        fn(int(chat_id), int(message_id), float(delay), str(prefix or 'delete'))
        return
    scheduler = globals().get('DELAYED_SCHEDULER')
    if scheduler is not None:
        scheduler.schedule(f'v171:{prefix}:{int(chat_id)}:{int(message_id)}', max(0.0, float(delay or 0.0)), lambda: _v171_delete_message_quiet(int(chat_id), int(message_id)))

def _v171_delete_message_quiet(chat_id: int, message_id: int) -> None:
    try:
        bot.delete_message(int(chat_id), int(message_id))
    except Exception:
        pass
    try:
        unregister_open_window(int(chat_id), int(message_id))
    except Exception:
        pass
V171_FORWARD_COPY_EDIT_MODES = ('normal', 'button', 'slash')

def _v171_forward_mode_root() -> dict:
    try:
        return data.setdefault('_global_settings', {})
    except Exception:
        return {}

def _canon_forward_copy_edit_mode__001(chat_id: int | None=None) -> str:
    gs = _v171_forward_mode_root()
    mode = str(gs.get('forward_copy_edit_mode_global') or '').strip().lower()
    if mode not in V171_FORWARD_COPY_EDIT_MODES:
        candidates = [str(gs.get('forward_copy_edit_mode') or '').strip().lower()]
        try:
            owner = int(OWNER_ID or 0)
            if owner:
                candidates.append(str(owner_scoped_settings(owner).get('forward_copy_edit_mode') or '').strip().lower())
                candidates.append(str(get_chat_store(owner).setdefault('settings', {}).get('forward_copy_edit_mode') or '').strip().lower())
        except Exception:
            pass
        mode = next((x for x in candidates if x in V171_FORWARD_COPY_EDIT_MODES), 'normal')
        gs['forward_copy_edit_mode_global'] = mode
        gs['forward_copy_edit_mode'] = mode
    try:
        if not version_mode_feature('forward_copy_edit'):
            return 'normal'
    except Exception:
        pass
    return mode if mode in V171_FORWARD_COPY_EDIT_MODES else 'normal'

def _canon_set_forward_copy_edit_mode__001(chat_id: int, mode: str):
    mode = str(mode or 'normal').strip().lower()
    if mode not in V171_FORWARD_COPY_EDIT_MODES:
        mode = 'normal'
    gs = _v171_forward_mode_root()
    gs['forward_copy_edit_mode_global'] = mode
    gs['forward_copy_edit_mode'] = mode
    try:
        for cid in collect_all_known_chat_ids(include_owner=True):
            try:
                get_chat_store(int(cid)).setdefault('settings', {})['forward_copy_edit_mode'] = mode
            except Exception:
                pass
    except Exception:
        pass
    try:
        scheduler = globals().get('V166_CONFIG_IO_SCHEDULER')
        if scheduler is not None:
            scheduler.schedule('v171-forward-mode', 0.05, lambda: save_data(data, root_only=True))
        else:
            save_data(data, root_only=True)
    except Exception:
        pass
    try:
        schedule_config_backup_for_chats(delay=1.0)
    except Exception:
        pass
    return mode

def _canon_cycle_forward_copy_edit_mode__001(chat_id: int) -> str:
    current = forward_copy_edit_mode(chat_id)
    try:
        idx = V171_FORWARD_COPY_EDIT_MODES.index(current)
    except ValueError:
        idx = 0
    return set_forward_copy_edit_mode(int(chat_id), V171_FORWARD_COPY_EDIT_MODES[(idx + 1) % len(V171_FORWARD_COPY_EDIT_MODES)])

def _canon_forward_copy_edit_mode_label__001(chat_id: int) -> str:
    return {'normal': '💰фин.пересылка: обычно', 'button': '💰фин.пересылка: кнопка', 'slash': '💰фин.пересылка: слеш'}.get(forward_copy_edit_mode(chat_id), '💰фин.пересылка: обычно')
_V171_PREV_REMINDER_CHAT_ALLOWED = _v177_legacy_0264_v149_reminder_chat_allowed

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
try:
    _v177_legacy_0265_v149_reminder_chat_allowed.__name__ = '_v149_reminder_chat_allowed'
except Exception:
    pass
V171_REMINDER_MERGE_MODES = ('off', 'smart', 'single')

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

def _canon_reminder_merge_mode__001(tenant_id: str | None=None, chat_id: int | None=None) -> str:
    return _v171_reminder_global_mode(True)

def _canon_reminder_merge_enabled__001(tenant_id: str | None=None, chat_id: int | None=None) -> bool:
    return reminder_merge_mode(tenant_id, chat_id) != 'off'

def _canon_reminder_merge_mode_label__001(tenant_id: str | None=None, chat_id: int | None=None) -> str:
    return {'off': 'ВЫКЛ', 'smart': 'ВКЛ', 'single': '1 СООБЩЕНИЕ'}.get(reminder_merge_mode(tenant_id, chat_id), 'ВЫКЛ')

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
try:
    WINDOW_MARKER_CONSTANTS.update({'v171:desc': 'Ф241', 'v171:desc_close': 'Ф241'})
except Exception:
    pass

def _v171_kb_rows(kb):
    return list(getattr(kb, 'keyboard', None) or getattr(kb, 'inline_keyboard', None) or [])

def _v171_btn_text(btn) -> str:
    if isinstance(btn, dict):
        return str(btn.get('text') or '')
    return str(getattr(btn, 'text', '') or '')

def _v171_btn_cb(btn) -> str:
    if isinstance(btn, dict):
        return str(btn.get('callback_data') or '')
    return str(getattr(btn, 'callback_data', '') or '')

def _v171_set_kb_rows(kb, rows):
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

def _v171_markup_inventory(kb):
    rows = _v171_kb_rows(kb)
    buttons = [btn for row in rows for btn in row or []]
    return (rows, {_v171_btn_cb(b) for b in buttons if _v171_btn_cb(b)}, [(_v171_btn_text(b), _v171_btn_cb(b)) for b in buttons])
_V171_PREV_AUGMENT_MARKUP = _v177_legacy_0318_v160_augment_markup

def _canon_v160_augment_markup__001(reply_markup, text: str, chat_id=None):
    kb = _V171_PREV_AUGMENT_MARKUP(reply_markup, text, chat_id) if callable(_V171_PREV_AUGMENT_MARKUP) else reply_markup
    marker = ''
    try:
        marker = str(_v160_marker_from_text(text) or '').upper()
    except Exception:
        marker = ''
    if not marker:
        return kb
    try:
        if not isinstance(kb, types.InlineKeyboardMarkup):
            kb = types.InlineKeyboardMarkup()
        if marker == 'Ф241':
            return kb
        rows, callbacks, inventory = _v171_markup_inventory(kb)
        labels_cf = [str(label).strip().casefold() for label, _cb in inventory]
        has_back = any(('назад' in label and 'осн' not in label for label in labels_cf)) or 'nav_prev' in callbacks
        has_main = any(('назад' in label and ('осн' in label or 'глав' in label) for label in labels_cf)) or any((str(cb).endswith(':back_main') for cb in callbacks))
        has_close = any(('закры' in label for label in labels_cf)) or bool({'info_close', 'aux_close', 'secclose', 'secmclose'} & callbacks)
        has_desc = 'v171:desc' in callbacks
        has_marker = 'v160:marker_capture' in callbacks
        has_tz = 'v160:tz_capture' in callbacks
        show_marker = True
        show_tz = True
        try:
            cid = int(chat_id or getattr(_state_context, 'chat_id', 0) or 0)
            vis_fn = globals().get('circle_annotation_button_enabled_v219')
            if callable(vis_fn):
                show_marker = bool(vis_fn('iz_mr', cid))
                show_tz = bool(vis_fn('tz', cid))
        except Exception:
            show_marker = True
            show_tz = True
        if not show_marker or not show_tz:
            cleaned_rows = []
            for row in rows:
                keep = []
                for button in row or []:
                    cb = _v171_btn_cb(button)
                    if cb == 'v160:marker_capture' and (not show_marker):
                        continue
                    if cb == 'v160:tz_capture' and (not show_tz):
                        continue
                    keep.append(button)
                if keep:
                    cleaned_rows.append(keep)
            rows = cleaned_rows
            callbacks = {_v171_btn_cb(b) for row in rows for b in row or [] if _v171_btn_cb(b)}
            has_marker = 'v160:marker_capture' in callbacks
            has_tz = 'v160:tz_capture' in callbacks
        day = today_key()
        try:
            day = str(get_chat_store(int(getattr(_state_context, 'chat_id', 0) or 0)).get('current_view_day') or today_key())
        except Exception:
            day = today_key()
        if not has_desc:
            rows.append([IB('ℹ️ Описание', callback_data='v171:desc')])
        if not has_back:
            rows.append([IB('🔙 Назад', callback_data='nav_prev')])
        if not has_main:
            rows.append([IB('⬅️ Назад осн. окно', callback_data=f'd:{day}:back_main')])
        if not has_close:
            rows.append([IB('❌ Закрыть', callback_data='info_close')])
        if show_marker and (not has_marker) or (show_tz and (not has_tz)):
            add = []
            if show_marker and (not has_marker):
                add.append(IB('/iz-mr', callback_data='v160:marker_capture'))
            if show_tz and (not has_tz):
                add.append(IB('/tz', callback_data='v160:tz_capture'))
            if add:
                rows.append(add)
        return _v171_set_kb_rows(kb, rows)
    except Exception as exc:
        try:
            log_error(f'v171 augment markup {marker}: {exc}')
        except Exception:
            pass
        return kb

def _v171_button_help(label: str, cb: str) -> str:
    low = (str(label) + ' ' + str(cb)).casefold()
    rules = ((('журнал',), 'открывает журнал или его настройки'), (('фин', 'режим'), 'управляет финансовым режимом'), (('фин.пересыл',), 'выбирает оформление финансовой копии: обычно / кнопка / слеш'), (('перес',), 'открывает или настраивает пересылку'), (('google', 'чт'), 'настраивает обновление Google-таблицы Чт–Ср'), (('excel',), 'открывает настройки Excel/выгрузки'), (('напомин',), 'открывает или меняет настройки напоминаний'), (('таймер',), 'открывает внутренние таймеры окон и задач'), (('mega',), 'работает с долговечным MEGA-хранилищем'), (('guard',), 'управляет защитой восстановления/резервирования'), (('очеред',), 'показывает состояние рабочих очередей'), (('render', 'сервер'), 'показывает состояние Render и runtime'), (('проблем',), 'показывает задачи, требующие проверки'), (('целост',), 'проверяет целостность финансовых данных'), (('владел',), 'открывает управление владельцами/доступом'), (('назад осн',), 'возвращает в основное окно'), (('назад',), 'возвращает в предыдущее окно'), (('закры',), 'закрывает текущее окно'), (('/iz-mr',), 'позволяет изменить имя/маркер окна'), (('/tz',), 'добавляет ТЗ именно к этому окну'))
    for needles, text in rules:
        if all((n in low for n in needles)):
            return text
    if str(cb) == 'none':
        return 'разделитель или информационная строка'
    return 'выполняет действие этой кнопки в текущем меню'

def _v171_window_description(call) -> str:
    source_text = str(getattr(call.message, 'text', None) or getattr(call.message, 'caption', None) or '')
    try:
        marker = str(_v160_marker_from_text(source_text) or 'без маркера').upper()
    except Exception:
        marker = 'без маркера'
    name = ''
    try:
        catalog, _rows = _v160_annotation_roots()
        name = str((catalog.get(marker) or {}).get('name') or '')
    except Exception:
        name = ''
    rows = _v171_kb_rows(getattr(call.message, 'reply_markup', None))
    seen = set()
    lines = [f'ℹ️ ОПИСАНИЕ ОКНА {marker}']
    if name:
        lines.append(f'Название: {name}')
    lines += ['', 'Назначение: управление функциями текущего меню.', '', 'Кнопки:']
    for row in rows:
        for btn in row or []:
            label = _v171_btn_text(btn).strip()
            cb = _v171_btn_cb(btn).strip()
            if not label or cb in {'v171:desc', 'v171:desc_close'}:
                continue
            key = (label, cb)
            if key in seen:
                continue
            seen.add(key)
            line = f'• {label} — {_v171_button_help(label, cb)}'
            if len('\n'.join(lines + [line])) > 3500:
                lines.append('• … остальные кнопки работают по их подписи и назначению меню.')
                break
            lines.append(line)
        if lines and lines[-1].startswith('• …'):
            break
    lines += ['', 'Цепочка кнопки: нажатие → отклик → выполнение → результат.']
    try:
        return window_mark('\n'.join(lines), 'Ф241')
    except Exception:
        return '\n'.join(lines) + '\n\nФ241'

def _v171_desc_keyboard(chat_id: int):
    day = today_key()
    try:
        day = str(get_chat_store(int(chat_id)).get('current_view_day') or today_key())
    except Exception:
        pass
    kb = types.InlineKeyboardMarkup()
    kb.row(IB('🔙 Назад', callback_data='v171:desc_close'), IB('⬅️ Назад осн. окно', callback_data=f'd:{day}:back_main'))
    kb.row(IB('❌ Закрыть', callback_data='v171:desc_close'))
    ann = []
    try:
        vis_fn = globals().get('circle_annotation_button_enabled_v219')
        show_m = bool(vis_fn('iz_mr', int(chat_id))) if callable(vis_fn) else True
        show_t = bool(vis_fn('tz', int(chat_id))) if callable(vis_fn) else True
    except Exception:
        show_m = show_t = True
    if show_m:
        ann.append(IB('/iz-mr', callback_data='v160:marker_capture'))
    if show_t:
        ann.append(IB('/tz', callback_data='v160:tz_capture'))
    if ann:
        kb.row(*ann)
    return kb

def _v171_special_callback(call):
    raw = str(getattr(call, 'data', '') or '')
    try:
        resolver = globals().get('resolve_short_callback')
        if callable(resolver):
            raw = str(resolver(raw) or raw)
    except Exception:
        pass
    if raw == 'none':
        try:
            bot.answer_callback_query(call.id)
        except Exception:
            pass
        return True
    if raw == 'v171:desc':
        cid = int(call.message.chat.id)
        try:
            bot.answer_callback_query(call.id)
        except Exception:
            pass
        try:
            bot.send_message(cid, _v171_window_description(call), reply_markup=_v171_desc_keyboard(cid))
        except Exception as exc:
            try:
                bot.send_message(cid, f'❌ Не удалось открыть описание: {str(exc)[:180]}')
            except Exception:
                pass
        return True
    if raw == 'v171:desc_close':
        try:
            bot.answer_callback_query(call.id)
        except Exception:
            pass
        _v171_delete_message_quiet(int(call.message.chat.id), int(call.message.message_id))
        return True
    return False
_V171_PREV_BUILD_INFO_KEYBOARD = _v177_legacy_0220_build_info_keyboard

def _v171_info_group(row) -> str:
    tokens = ' '.join((_v171_btn_text(btn) + ' ' + _v171_btn_cb(btn) for btn in row or [])).casefold()
    if any((x in tokens for x in ('back_main', 'info_close', 'назад осн', 'закрыть'))):
        return 'nav'
    if any((x in tokens for x in ('forward_copy', 'forward_menu', 'пересыл', 'фин.пересыл', 'icon_buttons'))):
        return 'forward'
    if 'reminder' in tokens or 'напомин' in tokens:
        return 'reminder'
    if any((x in tokens for x in ('restore_guard', 'mega_manual', 'delta', 'backup', 'mega_priority'))):
        return 'storage'
    if any((x in tokens for x in ('journal', 'problem_tasks', 'integrity', 'runtime_watcher', 'info_queues', 'internal_timers', 'keepalive', 'safety_profile', 'buttons_current'))):
        return 'diag'
    if any((x in tokens for x in ('finance', 'фин', 'gomonk', 'currency', 'usd', 'expense', 'excel', 'google', 'article'))):
        return 'finance'
    if any((x in tokens for x in ('owners', 'space', 'владел'))):
        return 'access'
    if any((x in tokens for x in ('instruction', 'инструк'))):
        return 'help'
    return 'other'

def _v177_legacy_0221_build_info_keyboard(chat_id: int):
    kb = _V171_PREV_BUILD_INFO_KEYBOARD(int(chat_id)) if callable(_V171_PREV_BUILD_INFO_KEYBOARD) else types.InlineKeyboardMarkup()
    rows = _v171_kb_rows(kb)
    if not rows or not is_owner_chat(int(chat_id)):
        return kb
    order = ('diag', 'storage', 'finance', 'forward', 'reminder', 'access', 'help', 'other', 'nav')
    buckets = {k: [] for k in order}
    for row in rows:
        buckets.setdefault(_v171_info_group(row), []).append(row)
    out = []
    first = True
    for group in order:
        block = buckets.get(group) or []
        if not block:
            continue
        if not first and group != 'nav':
            out.append([IB('ㅤ', callback_data='none')])
        out.extend(block)
        first = False
    return _v171_set_kb_rows(kb, out)
try:
    _v177_legacy_0221_build_info_keyboard.__name__ = 'build_info_keyboard'
except Exception:
    pass

def _v171_contour_preack_allowed(call, raw: str) -> bool:
    if not str(raw).startswith('v164:'):
        return False
    try:
        cid = int(call.message.chat.id)
        uid = int(getattr(getattr(call, 'from_user', None), 'id', 0) or 0)
        if raw.startswith('v164:circle:'):
            return cid == int(OWNER_ID or 0) or bool(tenant_can_manage(uid, chat_id=_v164_circle_parent_root_for_context(cid) or cid))
        if raw.startswith('v164:space_circle:'):
            return cid == int(OWNER_ID or 0) or bool(tenant_can_manage(uid, chat_id=cid) or circle_level_for_chat(cid) == 2)
        return True
    except Exception:
        return False

def _v171_window_item_key(item: dict):
    try:
        return (int(item.get('chat_id') or 0), int(item.get('message_id') or 0))
    except Exception:
        return (0, 0)

def _v171_wrap_registered_refresh(name: str):
    previous = globals().get(name)
    if not callable(previous) or getattr(previous, '_v171_refresh_guard', False):
        return

    def guarded(item: dict, changed_chat_id: int, _previous=previous):
        cid, mid = _v171_window_item_key(item or {})
        if not cid or not mid:
            return False
        lock = window_locks[cid, mid]
        with lock:
            try:
                if not get_registered_open_window(cid, mid):
                    return False
            except Exception:
                pass
            return _previous(item, changed_chat_id)
    guarded._v171_refresh_guard = True
    guarded.__name__ = name
    globals()[name] = guarded
for _v171_refresh_name in ('_refresh_registered_fin_view', '_refresh_registered_local_fin_view', '_refresh_registered_fin_categories_view'):
    try:
        _v171_wrap_registered_refresh(_v171_refresh_name)
    except Exception:
        pass
try:
    V171_DELTA_SOFT_WARN_BYTES = max(128 * 1024, int(_v171_os.getenv('MEGA_DELTA_SOFT_WARN_BYTES', str(512 * 1024)) or 512 * 1024))
except Exception:
    V171_DELTA_SOFT_WARN_BYTES = 512 * 1024
try:
    V171_DELTA_HARD_MAX_BYTES = max(V171_DELTA_SOFT_WARN_BYTES + 1, int(_v171_os.getenv('MEGA_DELTA_HARD_MAX_BYTES', str(1024 * 1024)) or 1024 * 1024))
except Exception:
    V171_DELTA_HARD_MAX_BYTES = 1024 * 1024
_V171_DELTA_WARN_LOCK = _v171_threading.RLock()
_V171_DELTA_LAST_WARN = 0.0

def _v171_json_size(obj) -> int:
    try:
        return len(_v171_json.dumps(obj, ensure_ascii=False, separators=(',', ':'), default=str).encode('utf-8'))
    except Exception:
        return -1

def _v171_delta_breakdown(payload: dict) -> str:
    pieces = []
    for key in ('chat_changes', 'root_patch', 'root_map_patches', 'root_deletes', 'root_map_deletes'):
        size = _v171_json_size((payload or {}).get(key))
        pieces.append(f'{key}={size}')
    try:
        chats = payload.get('chat_changes') or {}
        top = sorted(((str(k), _v171_json_size(v)) for k, v in chats.items()), key=lambda x: x[1], reverse=True)[:3]
        if top:
            pieces.append('top_chats=' + ','.join((f'{k}:{s}' for k, s in top)))
    except Exception:
        pass
    return ' '.join(pieces)
_V171_PREV_SAVE_TZ = _v177_legacy_0321_v160_save_tz
_V171_PREV_TZ_EXPORT = _v177_legacy_0326_v167_tz_export

def _canon_v160_save_tz__001(chat_id: int, user_id: int, marker: str, body: str, source: dict) -> dict:
    if not callable(_V171_PREV_SAVE_TZ):
        raise RuntimeError('TZ storage unavailable')
    row = _V171_PREV_SAVE_TZ(chat_id, user_id, marker, body, source)
    try:
        row['scope_policy'] = V171_TZ_SCOPE_POLICY
        row['scope_note'] = V171_TZ_SCOPE_TEXT
        _v160_persist_annotations(int(chat_id))
    except Exception:
        pass
    return row

def _canon_v167_tz_export__001(kind: str):
    if not callable(_V171_PREV_TZ_EXPORT):
        return ('ТЗ_окон', '')
    base, content = _V171_PREV_TZ_EXPORT(kind)
    if str(kind) in {'tz', 'tz_archive'}:
        lines = str(content or '').splitlines()
        insert_at = 4 if len(lines) >= 4 else len(lines)
        lines[insert_at:insert_at] = [f'Правило области ТЗ: {V171_TZ_SCOPE_TEXT}', '']
        content = '\n'.join(lines).rstrip() + '\n'
    return (base, content)
_V171_TZ_FIX_SIGNATURES = (('Ф233', ('таймер', 'закрыв')), ('Ф91', ('когда даю тз', 'всего бота')), ('Ф54', ('переименуй', 'фин')), ('Ф54', ('проверь журнал', 'ошиб')), ('Ф191', ('напоминал', 'другие чаты')), ('Ф54', ('перес', 'момент пересыл')), ('Ф54', ('контур', 'все кнопки')), ('Ф54', ('отсортируй', 'логич')), ('Ф91', ('каждом меню', 'описание')), ('Ф91', ('новое окно', 'назад')), ('Ф91', ('кнопки не ломались', 'нажатие')))

def _v171_mark_all_v169_tz_fixed() -> int:
    changed = 0
    try:
        _catalog, rows = _v160_annotation_roots()
    except Exception:
        return 0
    for row in rows or []:
        if not isinstance(row, dict):
            continue
        ver = str(row.get('version') or '')
        if not ver.startswith('bot_v169_'):
            continue
        marker = str(row.get('marker') or '').upper()
        body = str(row.get('text') or '').casefold()
        matched = False
        for want_marker, needles in _V171_TZ_FIX_SIGNATURES:
            if marker == want_marker and all((str(n).casefold() in body for n in needles)):
                matched = True
                break
        if not matched:
            continue
        if str(row.get('status') or '').lower() != 'fixed' or str(row.get('fixed_by_version') or '') != VERSION:
            row['status'] = 'fixed'
            row['fixed_by_version'] = VERSION
            row['fixed_at'] = now_local().isoformat(timespec='seconds')
            row['scope_policy'] = V171_TZ_SCOPE_POLICY
            changed += 1
    if changed:
        try:
            _v160_persist_annotations(int(OWNER_ID or 0))
        except Exception:
            pass
    return changed
_V171_PREV_RESTORE_VALIDATOR = _v177_legacy_0287_v153_validate_restore_gz

def _v177_legacy_0288_v153_validate_restore_gz(gz_path: str):
    if callable(_V171_PREV_RESTORE_VALIDATOR):
        try:
            return _V171_PREV_RESTORE_VALIDATOR(gz_path)
        except Exception as exc:
            if 'unsupported bot version' not in str(exc):
                raise
    folder = _v171_tempfile.mkdtemp(prefix='v171_restore_validate_')
    raw = _v171_os.path.join(folder, 'restore.sqlite3')
    try:
        with _v171_gzip.open(gz_path, 'rb') as fin, open(raw, 'wb') as fout:
            _v171_shutil.copyfileobj(fin, fout, 1024 * 1024)
        conn = _v171_sqlite3.connect(raw)
        try:
            integrity = str(conn.execute('PRAGMA integrity_check').fetchone()[0])
            if integrity.lower() != 'ok':
                raise RuntimeError(f'SQLite integrity_check: {integrity}')
            row = conn.execute("SELECT v FROM meta WHERE kind='v153_export' AND k='manifest'").fetchone()
            if not row:
                raise RuntimeError('manifest v153 not found')
            manifest = _v171_json.loads(row[0])
        finally:
            conn.close()
        if str(manifest.get('kind')) != 'telegram_bot_full_state_v153':
            raise RuntimeError('unknown export kind')
        if int(manifest.get('schema_version') or 0) != int(V153_EXPORT_SCHEMA):
            raise RuntimeError('unsupported export schema')
        export_version = str(manifest.get('bot_version') or '')
        if not export_version.startswith(tuple((f'bot_v{i}_' for i in range(153, 172)))):
            raise RuntimeError(f"unsupported bot version: {export_version or 'missing'}")
        if _v153_db_logical_checksum(raw) != str(manifest.get('checksum') or ''):
            raise RuntimeError('checksum mismatch')
        return (manifest, raw)
    except Exception:
        _v171_shutil.rmtree(folder, ignore_errors=True)
        raise
try:
    _v177_legacy_0288_v153_validate_restore_gz.__name__ = '_v153_validate_restore_gz'
except Exception:
    pass
_V171_PREV_RUNTIME_MARK_READY = _v179_legacy_runtime_mark_ready
if callable(_V171_PREV_RUNTIME_MARK_READY):

    def runtime_mark_ready(detail: str=''):
        result = _V171_PREV_RUNTIME_MARK_READY(detail)
        try:
            fixed = _v171_mark_all_v169_tz_fixed()
            bot_journal('v171_tz_fixed', int(OWNER_ID or 0), f'fixed={fixed}; policy={V171_TZ_SCOPE_POLICY}')
        except Exception:
            pass
        try:
            _v171_reminder_global_mode(True)
            forward_copy_edit_mode(int(OWNER_ID or 0))
        except Exception:
            pass
        return result
_V171_SPECIAL_HANDLER_COUNT = 0
_V171_BUTTON_CHAIN_COUNT = 0
try:
    _v177_legacy_0007_bot_journal('v171_installed', int(OWNER_ID or 0), f'all_v169_tz=11; special_handlers={_V171_SPECIAL_HANDLER_COUNT}; wrapped_callbacks={_V171_BUTTON_CHAIN_COUNT}; delta_soft={V171_DELTA_SOFT_WARN_BYTES}; delta_hard={V171_DELTA_HARD_MAX_BYTES}')
except Exception:
    pass

# --- ИСТОЧНИК: 76_tasks_runtime.py ---
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
    """Persist root state without holding data_lock during SQLite I/O (R36)."""
    try:
        import copy as _r36_copy
        with data_lock:
            root_snapshot = _r36_copy.deepcopy(_sqlite_pack_root(data))
        SQLITE.save_root(root_snapshot)
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

# R47 FINALIZATION: _v172_install_message_input_wrapper removed; hook is inline in on_any_message.

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
_V172_MESSAGE_WRAPPERS = 0
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

# R47 FINALIZATION: _v174_install_message_wrapper removed; hook is inline in on_any_message.

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
_V174_MESSAGE_WRAP = 0
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
# FINALIZED: v217 interception is executed inline by the single dispatcher in 89_callback_final.py.
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
# FINALIZED: v218 interception is executed inline by the single dispatcher in 89_callback_final.py.

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
# FINALIZED: v219 interception is executed inline by the single dispatcher in 89_callback_final.py.

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
# FINALIZED: v221 interception is executed inline by the single dispatcher in 89_callback_final.py.

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
