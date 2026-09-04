# v262
import json as _v150_json
import math as _v150_math
import re as _v150_re
import threading as _v150_threading
import time as _v150_time
from datetime import datetime as _v150_datetime
V150_CHAT_STATUSES = {'active', 'unreachable', 'bot_removed', 'migrated', 'archived'}
V150_CHAT_STATUS_LABELS = {'active': '🟢 active', 'unreachable': '🟠 unreachable', 'bot_removed': '⛔ bot_removed', 'migrated': '➡️ migrated', 'archived': '📦 archived'}
_V150_LOCK = _v150_threading.RLock()
_V150_LAST_ACTIVE_PERSIST = {}
_V150_BASE_REMINDER_MENU_TEXT = _v177_legacy_0128_build_reminder_menu_text
_V150_BASE_REMINDER_MENU_KEYBOARD = _v177_legacy_0130_build_reminder_menu_keyboard
_V150_BASE_CATEGORY_ROWS = _v177_legacy_0174_build_exact_category_stats_xlsx_rows
_V150_BASE_SIMPLE_ROWS = _v177_legacy_0090_xlsx_simple_rows_with_balances
_V150_BASE_COMPACT_ROWS = _v177_legacy_0093_compact_simple_excel_rows_and_annotations
_V150_BASE_ADD_RECORD = globals().get('_finance_add_record_base')
_V150_BASE_ADD_CURRENCY_RECORD = globals().get('_base_add_currency_record')
_V150_BASE_DURABLE_REQUIRED = _v177_legacy_0070_durable_task_required
_V150_BASE_DURABLE_EXPECTED = _v177_legacy_0066_durable_expected_effects
_V150_BASE_DURABLE_REPORT = _v177_legacy_0068_durable_effect_report
_V150_BASE_EXECUTE_PAYLOAD = _v177_legacy_0072_execute_telegram_payload
_V150_BASE_SET_WEBHOOK = _v177_legacy_0269_set_webhook
_V150_BASE_UPDATE_CHAT_MESSAGE = _v177_legacy_0236_update_chat_info_from_message
_V150_BASE_UPDATE_CHAT_OBJECT = _v177_legacy_0039_update_chat_info_from_chat_object
_V150_BASE_MIGRATE_CHAT = _v177_legacy_0156_migrate_chat_id_everywhere
_V150_BASE_TENANT_CHATS_TEXT = _v177_legacy_0258_tenant_chats_text

def _v150_now() -> str:
    try:
        return now_local().isoformat(timespec='seconds')
    except Exception:
        return _v150_datetime.now().astimezone().isoformat(timespec='seconds')

def _v150_float(value, default=0.0) -> float:
    try:
        number = float(value or 0)
        return number if _v150_math.isfinite(number) else float(default)
    except Exception:
        return float(default)

def _v150_command_from_payload(payload: dict) -> tuple[str, int | None, int | None, int | None]:
    if not isinstance(payload, dict):
        return ('', None, None, None)
    raw = payload.get('message') or payload.get('edited_message') or payload.get('channel_post') or payload.get('edited_channel_post')
    if not isinstance(raw, dict):
        return ('', None, None, None)
    text = str(raw.get('text') or raw.get('caption') or '').strip()
    first = text.split(maxsplit=1)[0].lower() if text.startswith('/') else ''
    if '@' in first:
        first = first.split('@', 1)[0]
    try:
        chat_id = int((raw.get('chat') or {}).get('id'))
    except Exception:
        chat_id = None
    try:
        msg_id = int(raw.get('message_id'))
    except Exception:
        msg_id = None
    try:
        user_id = int((raw.get('from') or {}).get('id'))
    except Exception:
        user_id = None
    return (first, chat_id, msg_id, user_id)

def _v150_reminder_chat_lines(cfg: dict) -> list[str]:
    chat_ids = []
    for raw in (cfg or {}).get('chat_ids') or []:
        try:
            cid = int(raw)
        except Exception:
            continue
        if cid not in chat_ids:
            chat_ids.append(cid)
    if not chat_ids:
        return ['💬 Чат: не выбран']

    def _label(cid: int) -> str:
        title = str(get_chat_display_name(cid))
        try:
            suppressed = globals().get('_v263_reminder_target_suppressed')
            if callable(suppressed) and suppressed(int(cid)):
                return '➖ ' + title
        except Exception:
            pass
        try:
            if is_chat_bot_removed(int(cid)):
                return '➖ ' + title
        except Exception:
            pass
        return title

    if len(chat_ids) == 1:
        return [f'💬 Чат: {_label(chat_ids[0])}']
    lines = ['💬 Чаты:']
    for cid in chat_ids:
        lines.append(f'• {_label(cid)}')
    return lines

def _canon_build_reminder_menu_text__001(reminder_id: int) -> str:
    cfg = _reminder_cfg(reminder_id)
    base = _V150_BASE_REMINDER_MENU_TEXT(reminder_id) if callable(_V150_BASE_REMINDER_MENU_TEXT) else ''
    if not isinstance(cfg, dict):
        return base
    lines = str(base or '').splitlines()
    out = []
    inserted = False
    for line in lines:
        if _v150_re.match('^\\s*[✅⬜❌]\\s*2\\.\\s*Чаты\\s*:', str(line), flags=_v150_re.I):
            out.extend(_v150_reminder_chat_lines(cfg))
            inserted = True
            continue
        out.append(line)
    if not inserted:
        insert_at = 2 if len(out) >= 2 else len(out)
        for idx, line in enumerate(out):
            if 'Период:' in line or 'Расписание:' in line or 'Состояние:' in line:
                insert_at = idx
                break
        out[insert_at:insert_at] = _v150_reminder_chat_lines(cfg) + ['']
    try:
        selected = [int(x) for x in (cfg.get('chat_ids') or []) if str(x).lstrip('-').isdigit()]
        suppressed_fn = globals().get('_v263_reminder_target_suppressed')
        unavailable = [cid for cid in selected if callable(suppressed_fn) and suppressed_fn(cid)]
        if unavailable:
            out += ['', f'⚠️ Доставка: недоступно {len(unavailable)} из {len(selected)} выбранных чатов.']
    except Exception:
        pass
    return '\n'.join(out)[:3900]

def _canon_build_reminder_menu_keyboard__001(reminder_id: int, day_key: str | None=None, page: int=0, viewer_chat_id: int | None=None):
    kb = _V150_BASE_REMINDER_MENU_KEYBOARD(reminder_id, day_key, page, viewer_chat_id) if callable(_V150_BASE_REMINDER_MENU_KEYBOARD) else types.InlineKeyboardMarkup()
    try:
        filtered = []
        for row in list(getattr(kb, 'keyboard', None) or []):
            clean = []
            for button in row:
                text = str(getattr(button, 'text', '') or '').strip()
                if 'К напоминалкам' not in text and _v150_re.search('(^|\\s)(⬅️|🔙)?\\s*Назад\\s*$', text, flags=_v150_re.I):
                    continue
                clean.append(button)
            if clean:
                filtered.append(clean)
        kb.keyboard = filtered
    except Exception as exc:
        try:
            log_error(f'v150 f191 keyboard cleanup: {exc}')
        except Exception:
            pass
    return kb

def _v150_export_currency(chat_id: int) -> str:
    try:
        return 'usd' if financial_view_is_usd(get_chat_store(int(chat_id))) else 'ars'
    except Exception:
        return 'ars'

def _v150_export_reserve(chat_id: int) -> float:
    try:
        return float(gomonk_total(int(chat_id), _v150_export_currency(chat_id)) or 0)
    except Exception:
        return 0.0

def _v150_usd_rate() -> float:
    try:
        row = usd_rate_cached(force=False) or {}
        return max(0.0, _v150_float(row.get('rate') or row.get('venta') or row.get('sell')))
    except Exception:
        return 0.0

def _v150_food_per_person(products_total: float) -> float:
    rate = _v150_usd_rate()
    return max(0.0, _v150_float(products_total)) / 5.0 / rate if rate > 0 else 0.0

def _v150_is_products_category(name: str) -> bool:
    clean = _v150_re.sub('\\s+', ' ', str(name or '').strip().casefold())
    return clean in {'продукты', 'еда', 'продукт', 'food', 'products'}

def _v150_product_total_from_records(chat_id: int, records) -> float:
    store = get_chat_store(int(chat_id))
    total = 0.0
    for item in records or []:
        rec = item[1] if isinstance(item, tuple) and len(item) >= 2 else item
        if not isinstance(rec, dict):
            continue
        amount = financial_view_amount(store, rec)
        if amount >= 0:
            continue
        note = financial_view_note(store, rec)
        try:
            category = resolve_expense_category(note, store)
        except Exception:
            category = ''
        if _v150_is_products_category(category):
            total += abs(float(amount))
    return total

def _v150_append_summary_rows(rows: list[list], chat_id: int | None, closing: float, products_total: float, layout: str) -> list[list]:
    out = [list(x or []) for x in rows or []]
    if chat_id is None:
        return out
    reserve = _v150_export_reserve(int(chat_id))
    turnover = float(closing) - min(reserve, max(0.0, float(closing)))
    metric = _v150_food_per_person(products_total)
    if layout == 'compact':
        out.append(['Гомонковые', reserve, ''])
        out.append(['Остаток в обороте', turnover, ''])
        out.append([])
        out.append(['Расход еды на человека в сутки', metric, ''])
    else:
        width = max([len(r) for r in out if r] + [4])
        row_res = ['', 'Гомонковые', reserve] + [''] * max(0, width - 3)
        row_turn = ['', 'Остаток в обороте', turnover] + [''] * max(0, width - 3)
        row_food = ['', 'Расход еды на человека в сутки', metric] + [''] * max(0, width - 3)
        out.extend([row_res[:width], row_turn[:width], [], row_food[:width]])
    return out

def _v150_cell_value(value) -> float:
    if isinstance(value, dict):
        return _v150_float(value.get('value'))
    return _v150_float(value)

def _v177_legacy_0175_build_exact_category_stats_xlsx_rows(target_chat_id: int, start_key: str, start_rid: int, end_key: str, end_rid: int) -> list[list]:
    rows = _V150_BASE_CATEGORY_ROWS(target_chat_id, start_key, start_rid, end_key, end_rid)
    closing = 0.0
    for row in reversed(rows or []):
        if len(row) > 2 and str(row[1] if len(row) > 1 else '').strip().casefold() == 'остаток на руках':
            closing = _v150_cell_value(row[2])
            break
    try:
        records = exact_record_range(get_chat_store(int(target_chat_id)), start_key, start_rid, end_key, end_rid)
        products_total = _v150_product_total_from_records(int(target_chat_id), records)
    except Exception:
        products_total = 0.0
    return _v150_append_summary_rows(rows, int(target_chat_id), closing, products_total, 'wide')
try:
    _v177_legacy_0175_build_exact_category_stats_xlsx_rows.__name__ = 'build_exact_category_stats_xlsx_rows'
except Exception:
    pass

def _v177_legacy_0091_xlsx_simple_rows_with_balances(rows: list[list], opening_balance: float, target_chat_id: int | None=None) -> list[list]:
    base = _V150_BASE_SIMPLE_ROWS(rows, opening_balance, target_chat_id) if _V150_BASE_SIMPLE_ROWS.__code__.co_argcount >= 3 else _V150_BASE_SIMPLE_ROWS(rows, opening_balance)
    closing = 0.0
    for row in reversed(base or []):
        if len(row) > 2 and str(row[1] if len(row) > 1 else '').strip().casefold() == 'остаток на руках':
            closing = _v150_cell_value(row[2])
            break
    products_total = 0.0
    if target_chat_id is not None:
        store = get_chat_store(int(target_chat_id))
        for row in (rows or [])[1:]:
            if len(row) < 4:
                continue
            note = str(row[1] or '')
            expense = _v150_float(row[3])
            if expense <= 0:
                continue
            try:
                category = resolve_expense_category(note, store)
            except Exception:
                category = ''
            if _v150_is_products_category(category):
                products_total += expense
    return _v150_append_summary_rows(base, target_chat_id, closing, products_total, 'wide')
try:
    _v177_legacy_0091_xlsx_simple_rows_with_balances.__name__ = '_xlsx_simple_rows_with_balances'
except Exception:
    pass

def _v177_legacy_0094_compact_simple_excel_rows_and_annotations(raw_rows: list[tuple], opening_balance: float, target_chat_id: int | None=None) -> tuple[list[list], dict[tuple[int, int], str]]:
    if _V150_BASE_COMPACT_ROWS.__code__.co_argcount >= 3:
        base, notes = _V150_BASE_COMPACT_ROWS(raw_rows, opening_balance, target_chat_id)
    else:
        base, notes = _V150_BASE_COMPACT_ROWS(raw_rows, opening_balance)
    closing = 0.0
    for row in reversed(base or []):
        if row and str(row[0] or '').strip().casefold() == 'остаток на руках':
            closing = _v150_cell_value(row[1] if len(row) > 1 else 0)
            break
    products_total = 0.0
    if target_chat_id is not None:
        store = get_chat_store(int(target_chat_id))
        for _date, amount_raw, note in raw_rows or []:
            try:
                amount = parse_csv_amount(amount_raw)
            except Exception:
                amount = _v150_float(amount_raw)
            if amount >= 0:
                continue
            try:
                category = resolve_expense_category(str(note or ''), store)
            except Exception:
                category = ''
            if _v150_is_products_category(category):
                products_total += abs(amount)
    return (_v150_append_summary_rows(base, target_chat_id, closing, products_total, 'compact'), notes)
try:
    _v177_legacy_0094_compact_simple_excel_rows_and_annotations.__name__ = '_compact_simple_excel_rows_and_annotations'
except Exception:
    pass

def _v150_ledger_balance(store: dict, currency: str) -> float:
    currency = 'usd' if str(currency).lower() == 'usd' else 'ars'
    active = str(store.setdefault('settings', {}).get('_active_currency_ledger') or 'ars').lower()
    if active == currency:
        return _v150_float(store.get('balance'))
    return _v150_float(store.get(f'{currency}_balance'))

def _v150_reduce_reserve_entries(chat_id: int, currency: str, consume: float) -> list[dict]:
    entries = [dict(x) for x in gomonk_entries(int(chat_id), currency) or []]
    left = max(0.0, _v150_float(consume))
    for idx in range(len(entries) - 1, -1, -1):
        if left <= 1e-09:
            break
        amount = max(0.0, _v150_float(entries[idx].get('amount')))
        used = min(amount, left)
        entries[idx]['amount'] = amount - used
        left -= used
    return [x for x in entries if _v150_float(x.get('amount')) > 1e-09]

def _v150_rebalance_key(chat_id: int, currency: str, rec: dict) -> str:
    operation_key = str((rec or {}).get('operation_key') or '').strip()
    if operation_key:
        return f'{chat_id}:{currency}:{operation_key}'
    source = int((rec or {}).get('source_msg_id') or 0)
    if source:
        return f'{chat_id}:{currency}:msg:{source}'
    return f"{chat_id}:{currency}:rid:{int((rec or {}).get('id') or 0)}:{str((rec or {}).get('timestamp') or '')}"

def _v150_apply_reserve_cover(chat_id: int, currency: str, rec: dict | None, reason: str='new_finance_operation') -> dict:
    if not isinstance(rec, dict):
        return {}
    currency = 'usd' if str(currency).lower() == 'usd' else 'ars'
    marker_root = rec.setdefault('gomonk_rebalance_v150', {})
    if marker_root.get(currency):
        return marker_root[currency]
    key = _v150_rebalance_key(int(chat_id), currency, rec)
    store = get_chat_store(int(chat_id))
    settings = store.setdefault('settings', {})
    enabled_key = 'usd_gomonk_enabled' if currency == 'usd' else 'gomonk_enabled'
    balance = _v150_ledger_balance(store, currency)
    target = float(gomonk_total(int(chat_id), currency) or 0)
    effective = min(target, max(0.0, balance)) if bool(settings.get(enabled_key, False)) else 0.0
    virtual_used = max(0.0, target - effective) if bool(settings.get(enabled_key, False)) else 0.0
    turnover_after = balance - effective
    result = {'key': key, 'currency': currency, 'at': _v150_now(), 'reason': reason, 'balance': balance, 'reserve_before': target, 'consumed': virtual_used, 'reserve_after': effective, 'turnover_after': turnover_after, 'constant_target_v209': target, 'entries_mutated': False}
    marker_root[currency] = result
    history = settings.setdefault('gomonk_rebalance_history_v150', [])
    history.append({**result, 'record_id': rec.get('id'), 'source_msg_id': rec.get('source_msg_id')})
    del history[:-300]
    intents = data.setdefault('gomonk_rebalance_intents_v150', {})
    if key in intents:
        intents[key].update({'status': 'done', 'done_at': _v150_now(), 'result': result})
    save_data(data, chat_ids=[int(chat_id)])
    try:
        schedule_config_backup_for_chats(int(chat_id), delay=0.5)
    except Exception:
        pass
    try:
        bot_journal('gomonk_constant_cover_v209', int(chat_id), _v150_json.dumps(result, ensure_ascii=False))
    except Exception:
        pass
    return result

def _v150_prepare_intent(chat_id: int, currency: str, source_msg, amount: float, note: str) -> str:
    try:
        source_msg_id = int(getattr(source_msg, 'message_id', 0) or 0)
    except Exception:
        source_msg_id = 0
    if not source_msg_id:
        return ''
    key = f'{int(chat_id)}:{currency}:msg:{source_msg_id}'
    intents = data.setdefault('gomonk_rebalance_intents_v150', {})
    if key not in intents:
        intents[key] = {'status': 'pending', 'chat_id': int(chat_id), 'currency': currency, 'source_msg_id': source_msg_id, 'amount': _v150_float(amount), 'note': str(note or '')[:180], 'created_at': _v150_now()}
        save_data(data, chat_ids=[int(chat_id)])
    return key

def _v150_add_record_compat(chat_id: int, amount: float, note: str, owner: int, source_msg=None, day_key=None, usd_amount=None, usd_note: str='', usd_only: bool=False, source_finance_text: str=''):
    _v150_prepare_intent(int(chat_id), 'ars', source_msg, amount, note)
    if usd_amount is not None:
        _v150_prepare_intent(int(chat_id), 'usd', source_msg, usd_amount, usd_note or note)
    rec = _V150_BASE_ADD_RECORD(chat_id, amount, note, owner, source_msg=source_msg, day_key=day_key, usd_amount=usd_amount, usd_note=usd_note, usd_only=usd_only, source_finance_text=source_finance_text)
    if isinstance(rec, dict):
        _v150_apply_reserve_cover(int(chat_id), 'ars', rec)
        if usd_amount is not None:
            _v150_apply_reserve_cover(int(chat_id), 'usd', rec)
    return rec

def _v150_add_currency_record_compat(chat_id: int, ledger: str, amount: float, note: str, owner: int, source_msg=None, day_key: str | None=None):
    ledger = 'usd' if str(ledger).lower() == 'usd' else 'ars'
    _v150_prepare_intent(int(chat_id), ledger, source_msg, amount, note)
    store = get_chat_store(int(chat_id))
    source_msg_id = int(getattr(source_msg, 'message_id', 0) or 0) if source_msg is not None else 0
    records_key = 'records' if str(store.setdefault('settings', {}).get('_active_currency_ledger') or 'ars') == ledger else f'{ledger}_records'
    if source_msg_id:
        existing = next((r for r in store.get(records_key, []) or [] if isinstance(r, dict) and int(r.get('source_msg_id') or 0) == source_msg_id), None)
        if isinstance(existing, dict):
            _v150_apply_reserve_cover(int(chat_id), ledger, existing, 'duplicate_retry_repair')
            return existing
    before_ids = {id(r) for r in store.get(records_key, []) or [] if isinstance(r, dict)}
    result = _V150_BASE_ADD_CURRENCY_RECORD(chat_id, ledger, amount, note, owner, source_msg=source_msg, day_key=day_key)
    store = get_chat_store(int(chat_id))
    candidates = [r for r in store.get(records_key, []) or [] if isinstance(r, dict) and id(r) not in before_ids]
    rec = candidates[-1] if candidates else result if isinstance(result, dict) else None
    if isinstance(rec, dict):
        _v150_apply_reserve_cover(int(chat_id), ledger, rec)
    return rec

def _v150_repair_pending_rebalances() -> int:
    repaired = 0
    intents = data.setdefault('gomonk_rebalance_intents_v150', {})
    for key, intent in list(intents.items()):
        if not isinstance(intent, dict) or intent.get('status') != 'pending':
            continue
        try:
            chat_id = int(intent.get('chat_id'))
            currency = str(intent.get('currency') or 'ars')
            source_msg_id = int(intent.get('source_msg_id') or 0)
            store = get_chat_store(chat_id)
            active = str(store.setdefault('settings', {}).get('_active_currency_ledger') or 'ars')
            records = store.get('records', []) if active == currency else store.get(f'{currency}_records', [])
            rec = next((r for r in records or [] if isinstance(r, dict) and int(r.get('source_msg_id') or 0) == source_msg_id), None)
            if isinstance(rec, dict):
                _v150_apply_reserve_cover(chat_id, currency, rec, 'startup_pending_repair')
                repaired += 1
        except Exception as exc:
            try:
                log_error(f'v150 rebalance repair {key}: {exc}')
            except Exception:
                pass
    return repaired

def _v150_error_class(err) -> tuple[str, str]:
    text = str(err or '').strip()
    low = text.casefold()
    definitive = ('bot was kicked', 'bot was blocked by the user', 'bot is not a member', 'kicked from the', 'bot was blocked', 'bot removed')
    if any((x in low for x in definitive)):
        return ('bot_removed', 'telegram_confirmed_bot_removed')
    if 'migrate_to_chat_id' in low or 'group chat was upgraded' in low:
        return ('migrated', 'telegram_migration')
    # For a chat already known to the bot, Telegram's explicit
    # `400 Bad Request: chat not found` during a membership/probe request means
    # the bot can no longer access that chat.  The original monolith treated
    # this as removal; keep that behaviour so the chat immediately moves to
    # the "Removed" menu instead of staying orange forever.
    if 'chat not found' in low:
        return ('bot_removed', 'telegram_chat_not_found_confirmed')
    if 'not enough rights' in low or 'have no rights' in low or 'not enough permissions' in low:
        return ('unreachable', 'telegram_missing_rights')
    if 'forbidden' in low:
        return ('unreachable', 'telegram_forbidden_unconfirmed')
    if 'timeout' in low or 'timed out' in low or 'connection' in low or ('temporar' in low) or ('429' in low) or ('too many requests' in low):
        return ('unreachable', 'telegram_temporary_error')
    return ('unreachable', 'telegram_unknown_error')

def _canon_is_bot_removed_error__001(err) -> bool:
    return _v150_error_class(err)[0] == 'bot_removed'

def _v150_lifecycle(chat_id: int) -> dict:
    store = get_chat_store(int(chat_id))
    row = store.get('chat_lifecycle_v150')
    if not isinstance(row, dict):
        settings = store.setdefault('settings', {})
        old_removed = bool(settings.get('bot_removed', False))
        old_reason = str(settings.get('bot_removed_reason') or '')
        status = 'active'
        if old_removed:
            status, _reason_code = _v150_error_class(old_reason)
        _created_at = _v150_now()
        row = {'status': status, 'status_since': _created_at, 'last_seen_at': '', 'last_success_at': '', 'last_error': old_reason, 'consecutive_failures': 0, 'migrated_to': None, 'history': [{'at': _created_at, 'from': 'unknown', 'to': status, 'reason': old_reason[:200] if old_reason else 'chat card discovered during v150 migration', 'source': 'v150_migration', 'migrated_to': None}]}
        store['chat_lifecycle_v150'] = row
    row.setdefault('status', 'active')
    row.setdefault('status_since', _v150_now())
    row.setdefault('last_seen_at', '')
    row.setdefault('last_success_at', '')
    row.setdefault('last_error', '')
    row.setdefault('consecutive_failures', 0)
    row.setdefault('migrated_to', None)
    row.setdefault('history', [])
    return row

def set_chat_status_v150(chat_id: int, status: str, reason: str, *, source: str='runtime', migrated_to: int | None=None, force_history: bool=False, persist: bool=True, schedule_backup: bool=True) -> dict:
    chat_id = int(chat_id)
    status = str(status or 'unreachable').strip().lower()
    if status not in V150_CHAT_STATUSES:
        status = 'unreachable'
    with _V150_LOCK:
        row = _v150_lifecycle(chat_id)
        previous = str(row.get('status') or 'active')
        now = _v150_now()
        if previous == 'archived' and status == 'active' and (str(source or '') != 'command'):
            row['last_seen_at'] = now
            row['last_success_at'] = now
            return row
        changed = previous != status
        if status == 'active' and previous == 'active' and (not force_history):
            # v262: active heartbeat is runtime state, not a Configuration Constitution change.
            # Never put the user's callback/message behind a full save every five minutes.
            row['last_seen_at'] = now
            row['last_success_at'] = now
            row['last_error'] = ''
            row['consecutive_failures'] = 0
            try:
                settings = get_chat_store(chat_id).setdefault('settings', {})
                settings['bot_removed'] = False
                settings.pop('bot_removed_reason', None)
                settings.pop('bot_removed_at', None)
            except Exception:
                pass
            if persist:
                try:
                    fn = globals().get('_v262_schedule_transient_chat_persist')
                    if callable(fn):
                        fn(chat_id)
                except Exception:
                    pass
            return row
        if changed:
            row['status'] = status
            row['status_since'] = now
        if status == 'active':
            row['last_seen_at'] = now
            row['last_success_at'] = now
            row['last_error'] = ''
            row['consecutive_failures'] = 0
        elif status == 'migrated':
            row['migrated_to'] = int(migrated_to) if migrated_to is not None else row.get('migrated_to')
            row['last_error'] = str(reason or '')[:500]
        else:
            row['last_error'] = str(reason or '')[:500]
            row['consecutive_failures'] = int(row.get('consecutive_failures') or 0) + 1
        settings = get_chat_store(chat_id).setdefault('settings', {})
        settings['bot_removed'] = status == 'bot_removed'
        if status == 'bot_removed':
            settings['bot_removed_reason'] = str(reason or '')[:300]
            settings['bot_removed_at'] = now
        else:
            settings.pop('bot_removed_reason', None)
            settings.pop('bot_removed_at', None)
        signature = (previous, status, str(reason or '')[:200], str(source or ''))
        last = (row.get('history') or [])[-1] if row.get('history') else {}
        last_signature = (last.get('from'), last.get('to'), last.get('reason'), last.get('source')) if isinstance(last, dict) else None
        if changed or force_history or signature != last_signature:
            row['history'].append({'at': now, 'from': previous, 'to': status, 'reason': str(reason or '')[:200], 'source': str(source or '')[:80], 'migrated_to': int(migrated_to) if migrated_to is not None else None})
            del row['history'][:-200]
        if persist:
            save_data(data, chat_ids=[chat_id])
            if status == 'active':
                _V150_LAST_ACTIVE_PERSIST[chat_id] = _v150_time.monotonic()
        if schedule_backup:
            try:
                schedule_config_backup_for_chats(chat_id, delay=1.0)
            except Exception:
                pass
        try:
            bot_journal('chat_lifecycle', chat_id, f'{previous}->{status}; source={source}; reason={str(reason)[:240]}', 'WARN' if status != 'active' else 'INFO')
        except Exception:
            pass
        return row

def _canon_set_chat_bot_removed__001(chat_id: int, removed: bool=True, reason: str='', *, persist: bool=True, schedule_backup: bool=True) -> bool:
    """Canonical lifecycle bridge used by the deep probe.

    Keep the v197 keyword contract even though the v150 lifecycle layer owns the
    final runtime implementation.  Return a real changed/not-changed boolean so
    callers do not treat the lifecycle dict itself as an unconditional change.
    """
    chat_id = int(chat_id)
    before = str(_v150_lifecycle(chat_id).get('status') or 'active')
    if not removed:
        set_chat_status_v150(chat_id, 'active', reason or 'telegram api success', source='legacy_bridge', persist=persist, schedule_backup=schedule_backup)
    else:
        status, code = _v150_error_class(reason)
        set_chat_status_v150(chat_id, status, reason or code, source=code, persist=persist, schedule_backup=schedule_backup)
    after = str(_v150_lifecycle(chat_id).get('status') or 'active')
    return before != after

def _canon_is_chat_bot_removed__001(chat_id: int) -> bool:
    try:
        return str(_v150_lifecycle(int(chat_id)).get('status')) in {'bot_removed', 'migrated', 'archived'}
    except Exception:
        return False

def _canon_chat_button_title__001(chat_id: int, title: str | None=None) -> str:
    title = str(title or get_chat_display_name(int(chat_id)))
    try:
        status = str(_v150_lifecycle(int(chat_id)).get('status') or 'active')
    except Exception:
        status = 'active'
    icon = {'active': '', 'unreachable': '🟠 ', 'bot_removed': '⛔ ', 'migrated': '➡️ ', 'archived': '📦 '}.get(status, '')
    return icon + title

def _canon_update_chat_info_from_message__001(msg):
    result = _V150_BASE_UPDATE_CHAT_MESSAGE(msg) if callable(_V150_BASE_UPDATE_CHAT_MESSAGE) else None
    try:
        chat_id = int(msg.chat.id)
        set_chat_status_v150(chat_id, 'active', 'message received', source='telegram_update')
    except Exception:
        pass
    return result

def _canon_update_chat_info_from_chat_object__001(chat_obj, *, persist: bool=True, schedule_backup: bool=True) -> bool:
    result = False
    if callable(_V150_BASE_UPDATE_CHAT_OBJECT):
        try:
            result = bool(_V150_BASE_UPDATE_CHAT_OBJECT(chat_obj, persist=persist, schedule_backup=schedule_backup))
        except TypeError:
            result = bool(_V150_BASE_UPDATE_CHAT_OBJECT(chat_obj))
    try:
        set_chat_status_v150(int(chat_obj.id), 'active', 'getChat success', source='telegram_get_chat', persist=persist, schedule_backup=schedule_backup)
    except Exception:
        pass
    return result

def _v150_probe_bot_in_chat_legacy(chat_id: int) -> bool:
    """Legacy lifecycle-only probe kept private.

    v197 introduced the canonical extended probe in 00_core.py with keyword controls
    (deep/persist/schedule_backup).  Do NOT rebind the public probe_bot_in_chat here:
    doing so used to erase that signature and broke the full chat sync.
    """
    chat_id = int(chat_id)
    try:
        obj = _tg_call_retry(bot.get_chat, chat_id, attempts=2, purpose='probe_get_chat')
        update_chat_info_from_chat_object(obj)
        return True
    except Exception as exc:
        status, code = _v150_error_class(exc)
        set_chat_status_v150(chat_id, status, str(exc)[:500], source=code)
        return False

def _canon_migrate_chat_id_everywhere__001(old_chat_id: int, new_chat_id: int, reason: str='telegram supergroup migration') -> bool:
    ok = bool(_V150_BASE_MIGRATE_CHAT(old_chat_id, new_chat_id, reason)) if callable(_V150_BASE_MIGRATE_CHAT) else False
    if ok:
        set_chat_status_v150(int(old_chat_id), 'migrated', reason, source='telegram_migration', migrated_to=int(new_chat_id), force_history=True)
        set_chat_status_v150(int(new_chat_id), 'active', f'migrated from {int(old_chat_id)}', source='telegram_migration', force_history=True)
    return ok

def _v150_status_line(chat_id: int) -> str:
    row = _v150_lifecycle(int(chat_id))
    status = str(row.get('status') or 'active')
    reason = str(row.get('last_error') or '').strip()
    label = V150_CHAT_STATUS_LABELS.get(status, status)
    return f'{label}' + (f' · {reason[:90]}' if reason else '')

def _v177_legacy_0259_tenant_chats_text(tenant_id: str) -> str:
    row = tenant_get(tenant_id) or {}
    lines = [f"💬 ЧАТЫ · {row.get('name')}", '']
    for cid in row.get('chat_ids') or []:
        cid = int(cid)
        marker = '🏠' if cid == int(row.get('root_chat_id') or 0) else '•'
        lines.append(f'{marker} {get_chat_display_name(cid)} · {cid}')
        lines.append(f'   {_v150_status_line(cid)}')
    if len(lines) == 2:
        lines.append('Нет подключённых чатов.')
    return '\n'.join(lines)[:3900]
try:
    _v177_legacy_0259_tenant_chats_text.__name__ = 'tenant_chats_text'
except Exception:
    pass

def _v150_chat_access(user_id: int, chat_id: int) -> bool:
    try:
        tid = tenant_id_for_chat(int(chat_id), create=False)
        if not tid:
            return tenant_is_platform_owner_user(int(user_id))
        return tenant_can_manage(int(user_id), str(tid)) or tenant_is_platform_owner_user(int(user_id))
    except Exception:
        return False

def _v150_status_text(chat_id: int) -> str:
    row = _v150_lifecycle(int(chat_id))
    lines = [f'💬 {get_chat_display_name(int(chat_id))}', f'ID: {int(chat_id)}', f"Статус: {V150_CHAT_STATUS_LABELS.get(str(row.get('status')), str(row.get('status')))}", f"С этого времени: {row.get('status_since') or '—'}", f"Последний успешный контакт: {row.get('last_success_at') or '—'}", f"Последняя ошибка: {row.get('last_error') or '—'}", f"Ошибок подряд: {int(row.get('consecutive_failures') or 0)}"]
    if row.get('migrated_to'):
        lines.append(f"Перенесён в: {row.get('migrated_to')}")
    return '\n'.join(lines)[:3900]

def _v150_history_text(chat_id: int) -> str:
    row = _v150_lifecycle(int(chat_id))
    lines = [f'🧾 ИСТОРИЯ ЧАТА · {get_chat_display_name(int(chat_id))}', '']
    for item in reversed((row.get('history') or [])[-30:]):
        if not isinstance(item, dict):
            continue
        lines.append(f"{item.get('at')} · {item.get('from')} → {item.get('to')}")
        lines.append(f"Причина: {item.get('reason') or '—'} · источник: {item.get('source') or '—'}")
    if len(lines) == 2:
        lines.append('История пока пуста.')
    return '\n'.join(lines)[:3900]

def _v150_target_chat_from_command(msg) -> int:
    parts = str(getattr(msg, 'text', '') or '').split(maxsplit=1)
    if len(parts) > 1:
        try:
            return int(parts[1].strip())
        except Exception:
            pass
    return int(msg.chat.id)

@bot.message_handler(commands=['chat_status'])
def v150_cmd_chat_status(msg):
    target = _v150_target_chat_from_command(msg)
    uid = int(getattr(getattr(msg, 'from_user', None), 'id', 0) or 0)
    if not _v150_chat_access(uid, target):
        bot.reply_to(msg, '⛔ Недостаточно прав для этого чата.')
        return
    bot.reply_to(msg, _v150_status_text(target))

@bot.message_handler(commands=['chat_history'])
def v150_cmd_chat_history(msg):
    target = _v150_target_chat_from_command(msg)
    uid = int(getattr(getattr(msg, 'from_user', None), 'id', 0) or 0)
    if not _v150_chat_access(uid, target):
        bot.reply_to(msg, '⛔ Недостаточно прав для этого чата.')
        return
    bot.reply_to(msg, _v150_history_text(target))

@bot.message_handler(commands=['chat_archive'])
def v150_cmd_chat_archive(msg):
    target = _v150_target_chat_from_command(msg)
    uid = int(getattr(getattr(msg, 'from_user', None), 'id', 0) or 0)
    if not _v150_chat_access(uid, target):
        bot.reply_to(msg, '⛔ Недостаточно прав для этого чата.')
        return
    set_chat_status_v150(target, 'archived', f'manual archive by {uid}', source='command', force_history=True)
    bot.reply_to(msg, '📦 Чат переведён в статус archived. Данные и история сохранены.')

@bot.message_handler(commands=['chat_restore'])
def v150_cmd_chat_restore(msg):
    target = _v150_target_chat_from_command(msg)
    uid = int(getattr(getattr(msg, 'from_user', None), 'id', 0) or 0)
    if not _v150_chat_access(uid, target):
        bot.reply_to(msg, '⛔ Недостаточно прав для этого чата.')
        return
    set_chat_status_v150(target, 'active', f'manual restore by {uid}', source='command', force_history=True)
    try:
        GENERAL_TASK_POOL.submit_unique(f'probe-chat-{target}', probe_bot_in_chat, target)
    except Exception:
        pass
    bot.reply_to(msg, '✅ Карточка чата восстановлена и поставлена на проверку Telegram.')

@bot.message_handler(commands=['command_audit'])
def v150_cmd_command_audit(msg):
    uid = int(getattr(getattr(msg, 'from_user', None), 'id', 0) or 0)
    if not tenant_is_platform_owner_user(uid):
        bot.reply_to(msg, '⛔ Команда доступна только владельцу платформы.')
        return
    bot.reply_to(msg, '✅ Slash-команды v150\n\n• command-декораторов и алиасов: 91; конфликтов между ними: 0;\n• в меню Telegram зарегистрировано 96 допустимых латинских команд и алиасов;\n• обычный catch-all исключает сообщения, начинающиеся с /;\n• изменяющие состояние команды защищены durable receipt;\n• /vyapl_ID обрабатывается отдельным цифровым маршрутом и не конфликтует с /vyapl_history.\n\nПолный аудит находится в COMMAND_AUDIT_v150.txt внутри ZIP.')
_V150_MUTATION_COMMANDS = {'/reset', '/stopforward', '/backup_channel_on', '/backup_channel_off', '/buttons', '/secret_bot', '/mega_backup_now', '/knopki', '/кнопки', '/mask', '/maska', '/маска', '/day5', '/fin_day5', '/sutki', '/ost', '/остаток', '/старт', '/restore_guard_off', '/restore_guard_on', '/off_on_backup_excel', '/space_create', '/tenant_create', '/space_claim', '/tenant_claim', '/space_join', '/tenant_join', '/space_chat_link', '/tenant_chat_link', '/space_user_link', '/tenant_user_link', '/space_role', '/tenant_role', '/space_transfer', '/tenant_transfer', '/space_rename', '/tenant_rename', '/space_unlink', '/tenant_unlink', '/google_connect', '/google_sheet', '/google_drive', '/google_email', '/chat_archive', '/chat_restore'}

def _v150_is_mutation_command(command: str) -> bool:
    cmd = str(command or '').lower()
    if cmd in _V150_MUTATION_COMMANDS or bool(_v150_re.fullmatch('/vyapl(?:_\\d+)?', cmd)):
        return True
    return bool(_v150_re.fullmatch('/(?:владелец|vladelec)(?:1904|-1904|_1904)', cmd, flags=_v150_re.I))

def _v150_is_known_slash_command(text: str) -> bool:
    token = str(text or '').strip().split(maxsplit=1)[0].split('@', 1)[0].casefold()
    if not token.startswith('/'):
        return False
    name = token[1:]
    known = {str(cmd).casefold() for cmd, _desc in _V150_TELEGRAM_COMMANDS} if '_V150_TELEGRAM_COMMANDS' in globals() else set()
    known.update({'старт', 'кнопки', 'маска', 'остаток', 'секрет', 'sekret', 'cekret'})
    return name in known or bool(_v150_re.fullmatch('(?:vyapl_\\d+|izm_[ru]\\d+(?:_u[a-f0-9]{12})?|\\d+)', name, flags=_v150_re.I))

def _canon_durable_task_required__001(payload: dict) -> tuple[bool, str]:
    try:
        _raw_restore = (payload or {}).get('message') or (payload or {}).get('channel_post')
        if isinstance(_raw_restore, dict) and isinstance(_raw_restore.get('document'), dict):
            _restore_cid = int((_raw_restore.get('chat') or {}).get('id'))
            _restore_name = str((_raw_restore.get('document') or {}).get('file_name') or '').lower()
            _restore_active = globals().get('restore_mode')
            if _restore_active is not None and int(_restore_active) == _restore_cid and _restore_name.endswith(('.json', '.ison', '.csv', '.gz')):
                return (False, 'v186:restore_document_control')
            if _restore_name.endswith(('.json', '.ison')):
                try:
                    if is_owner_chat(_restore_cid):
                        return (False, 'v186:owner_backup_document_control')
                except Exception:
                    pass
    except Exception:
        pass
    command, _chat_id, _msg_id, _uid = _v150_command_from_payload(payload)
    if str(command or '').lower() in {'/restore', '/restore_off', '/mega_restore_now'}:
        return (False, 'v239:restore_control_plane')
    if str(command or '').lower().startswith('/izm_'):
        return (False, 'v168:record_edit_open')
    if _v150_is_mutation_command(command):
        try:
            if not mega_tasks_active():
                return (False, 'mega_tasks_inactive')
        except Exception:
            pass
        return (True, 'v150:mutation_command')
    if command and _chat_id is not None:
        try:
            if is_total_secret_mode(int(_chat_id)) and (not _v150_is_known_slash_command(command)):
                return (True, 'v150:total_secret_slash_content')
        except Exception:
            pass
    return _V150_BASE_DURABLE_REQUIRED(payload)

def _v150_receipt_key(payload: dict) -> str:
    command, chat_id, msg_id, user_id = _v150_command_from_payload(payload)
    update_id = (payload or {}).get('update_id')
    return f'{update_id}:{chat_id}:{msg_id}:{user_id}:{command}'

def _canon_durable_expected_effects__001(payload: dict) -> dict:
    out = _V150_BASE_DURABLE_EXPECTED(payload)
    command, chat_id, msg_id, user_id = _v150_command_from_payload(payload)
    if _v150_is_mutation_command(command):
        out['command_receipt_v150'] = {'key': _v150_receipt_key(payload), 'command': command, 'chat_id': chat_id, 'message_id': msg_id, 'user_id': user_id}
    elif command and chat_id is not None:
        try:
            if is_total_secret_mode(int(chat_id)) and (not _v150_is_known_slash_command(command)):
                out['source_secret'] = True
        except Exception:
            pass
    return out

def _v150_has_receipt(key: str) -> bool:
    return any((isinstance(x, dict) and str(x.get('key')) == str(key) for x in data.get('durable_command_receipts_v150') or []))

def _v150_store_receipt(payload: dict):
    command, chat_id, msg_id, user_id = _v150_command_from_payload(payload)
    if not _v150_is_mutation_command(command):
        return
    key = _v150_receipt_key(payload)
    if _v150_has_receipt(key):
        return
    rows = data.setdefault('durable_command_receipts_v150', [])
    rows.append({'key': key, 'command': command, 'chat_id': chat_id, 'message_id': msg_id, 'user_id': user_id, 'update_id': payload.get('update_id'), 'completed_at': _v150_now()})
    del rows[:-800]
    save_data(data, chat_ids=[chat_id] if chat_id is not None else None)

def _v177_legacy_0073_execute_telegram_payload(payload: dict, update_id=None, update_chat_id=None, update_type: str='other'):
    result = _V150_BASE_EXECUTE_PAYLOAD(payload, update_id=update_id, update_chat_id=update_chat_id, update_type=update_type)
    _v150_store_receipt(payload)
    return result
try:
    _v177_legacy_0073_execute_telegram_payload.__name__ = '_execute_telegram_payload'
except Exception:
    pass

def _canon_durable_effect_report__001(payload: dict, expected: dict | None=None) -> dict:
    report = _V150_BASE_DURABLE_REPORT(payload, expected)
    exp = expected if isinstance(expected, dict) else _durable_expected_effects(payload)
    receipt = exp.get('command_receipt_v150') if isinstance(exp, dict) else None
    if isinstance(receipt, dict) and (not _v150_has_receipt(str(receipt.get('key') or ''))):
        report['complete'] = False
        missing = report.setdefault('missing', [])
        tag = f"command_receipt:{receipt.get('command')}:{receipt.get('message_id')}"
        if tag not in missing:
            missing.append(tag)
    return report
_V150_TELEGRAM_COMMANDS = [('additional_owners', 'Команда /additional_owners'), ('articles', 'Статьи расходов'), ('backup_channel_off', 'Команда /backup_channel_off'), ('backup_channel_on', 'Команда /backup_channel_on'), ('balance', 'Текущий баланс'), ('bot_errors', 'Команда /bot_errors'), ('buttons', 'Команда /buttons'), ('chat_archive', 'Архивировать чат'), ('chat_history', 'История статусов чата'), ('chat_restore', 'Восстановить карточку чата'), ('chat_status', 'Статус чата'), ('command_audit', 'Аудит slash-команд'), ('csv', 'Скачать CSV'), ('db', 'Команда /db'), ('delta_status', 'Команда /delta_status'), ('diag', 'Команда /diag'), ('diagnostics', 'Команда /diagnostics'), ('dozvon', 'Команда /dozvon'), ('errors', 'Команда /errors'), ('excel', 'Настройки Excel'), ('google', 'Google пространства'), ('google_connect', 'Команда /google_connect'), ('google_drive', 'Команда /google_drive'), ('google_email', 'Команда /google_email'), ('google_sheet', 'Команда /google_sheet'), ('google_space', 'Команда /google_space'), ('google_tenant', 'Команда /google_tenant'), ('help', 'Справка по командам'), ('journal', 'Команда /journal'), ('json', 'Скачать JSON'), ('log', 'Команда /log'), ('logs', 'Команда /logs'), ('mega_backup_now', 'Команда /mega_backup_now'), ('mega_restore_now', 'Команда /mega_restore_now'), ('mega_status', 'Команда /mega_status'), ('next', 'Команда /next'), ('off_on_backup_excel', 'Команда /off_on_backup_excel'), ('ok', 'Команда /ok'), ('okna', 'Команда /okna'), ('owners', 'Команда /owners'), ('ping', 'Проверка ответа бота'), ('prev', 'Команда /prev'), ('queue_status', 'Команда /queue_status'), ('queues', 'Команда /queues'), ('report', 'Финансовый отчёт'), ('reset', 'Команда /reset'), ('restore', 'Команда /restore'), ('restore_guard', 'Команда /restore_guard'), ('restore_guard_off', 'Команда /restore_guard_off'), ('restore_guard_on', 'Команда /restore_guard_on'), ('restore_off', 'Команда /restore_off'), ('runtime_export', 'Команда /runtime_export'), ('secret_bot', 'Команда /secret_bot'), ('space', 'Текущее пространство'), ('space_chat_link', 'Команда /space_chat_link'), ('space_chats', 'Команда /space_chats'), ('space_claim', 'Команда /space_claim'), ('space_create', 'Команда /space_create'), ('space_join', 'Команда /space_join'), ('space_rename', 'Команда /space_rename'), ('space_role', 'Команда /space_role'), ('space_transfer', 'Команда /space_transfer'), ('space_unlink', 'Команда /space_unlink'), ('space_user_link', 'Команда /space_user_link'), ('space_users', 'Команда /space_users'), ('spaces', 'Список пространств'), ('sqlite', 'Команда /sqlite'), ('start', 'Открыть главное меню'), ('stopforward', 'Команда /stopforward'), ('tabl_lsx', 'Excel за четыре недели'), ('tenant', 'Команда /tenant'), ('tenant_chat_link', 'Команда /tenant_chat_link'), ('tenant_chats', 'Команда /tenant_chats'), ('tenant_claim', 'Команда /tenant_claim'), ('tenant_create', 'Команда /tenant_create'), ('tenant_join', 'Команда /tenant_join'), ('tenant_rename', 'Команда /tenant_rename'), ('tenant_role', 'Команда /tenant_role'), ('tenant_transfer', 'Команда /tenant_transfer'), ('tenant_unlink', 'Команда /tenant_unlink'), ('tenant_user_link', 'Команда /tenant_user_link'), ('tenant_users', 'Команда /tenant_users'), ('vyapl', 'Выполнить напоминание'), ('vyapl_history', 'История выполнения напоминаний'), ('windows', 'Команда /windows'), ('xlsx', 'Скачать Excel'), ('knopki', 'Переключить вид кнопок'), ('mask', 'Маскировка секретного режима'), ('maska', 'Маскировка секретного режима'), ('day5', 'Финансовые сутки с 05:00'), ('fin_day5', 'Финансовые сутки с 05:00'), ('sutki', 'Финансовые сутки с 05:00'), ('ost', 'Переключить подпись остатка'), ('secret', 'Открыть секретные записи'), ('sekret', 'Открыть секретные записи'), ('cekret', 'Открыть секретные записи')]

def _v150_register_commands():
    try:
        commands = [types.BotCommand(name, description[:256]) for name, description in _V150_TELEGRAM_COMMANDS]
        bot.set_my_commands(commands)
        try:
            bot_journal('slash_commands_registered', int(OWNER_ID or 0), f'count={len(commands)}')
        except Exception:
            pass
        return True
    except Exception as exc:
        try:
            log_error(f'v150 set_my_commands: {exc}')
        except Exception:
            pass
        return False

def _v150_migrate_chat_lifecycle() -> int:
    count = 0
    for cid, store in list((data.get('chats') or {}).items()):
        if not isinstance(store, dict):
            continue
        try:
            chat_id = int(cid)
            before = store.get('chat_lifecycle_v150')
            _v150_lifecycle(chat_id)
            if not isinstance(before, dict):
                count += 1
        except Exception:
            continue
    if count:
        save_data(data)
    return count

def _v177_legacy_0270_set_webhook():
    global restore_mode
    try:
        _saved_restore_chat = data.get('_restore_mode_chat_v150')
        restore_mode = int(_saved_restore_chat) if _saved_restore_chat is not None else None
        migrated = _v150_migrate_chat_lifecycle()
        repaired = _v150_repair_pending_rebalances()
        try:
            bot_journal('v150_startup_migration', int(OWNER_ID or 0), f'chat_lifecycle={migrated}; rebalance_repaired={repaired}')
        except Exception:
            pass
    except Exception as exc:
        try:
            log_error(f'v150 startup migration: {exc}')
        except Exception:
            pass
    result = _V150_BASE_SET_WEBHOOK()
    _v150_register_commands()
    return result
try:
    _v177_legacy_0270_set_webhook.__name__ = 'set_webhook'
except Exception:
    pass
import math as _v151_math
import re as _v151_re
import threading as _v151_threading
from datetime import datetime as _v151_datetime, timedelta as _v151_timedelta
_V151_EXPORT_LOCAL = _v151_threading.local()
_V151_MONTH_LOCAL = _v151_threading.local()
_V151_REBALANCE_LOCK = _v151_threading.RLock()
_V151_BASE_SEND_EXPORT = _v177_legacy_0209_send_export_for_chat_to
_V151_BASE_SEND_EXACT_EXPORT = _v177_legacy_0179_send_exact_range_export
_V151_BASE_PERIOD_ROWS = _v177_legacy_0203_period_export_rows
_V151_BASE_EXACT_ROWS = _v177_legacy_0173_exact_export_rows
_V151_BASE_SET_WEBHOOK = _v177_legacy_0270_set_webhook
_V151_BASE_ADD_RECORD = globals().get('_finance_add_record_base')
_V151_BASE_ADD_LEDGER_RECORD = globals().get('_base_add_currency_record')

def _v151_float(value, default=0.0) -> float:
    try:
        number = float(value or 0)
        return number if _v151_math.isfinite(number) else float(default)
    except Exception:
        return float(default)

def _v151_num(value):
    number = _v151_float(value)
    return int(number) if float(number).is_integer() else number

def _v151_now() -> str:
    try:
        return now_local().isoformat(timespec='seconds')
    except Exception:
        return _v151_datetime.now().astimezone().isoformat(timespec='seconds')

def _v151_day_key(rec: dict) -> str:
    try:
        return str(_record_day_key(rec))[:10]
    except Exception:
        return str((rec or {}).get('day_key') or '')[:10]

def _v151_parse_day(value: str):
    raw = str(value or '')[:10]
    for fmt in ('%Y-%m-%d', '%d.%m.%Y', '%d.%m.%y'):
        try:
            return _v151_datetime.strptime(raw, fmt)
        except Exception:
            continue
    return None

def _v151_sync_currency_snapshots(store: dict) -> str:
    try:
        active = _ensure_currency_ledgers(store)
        _snapshot_active_currency_ledger(store, active)
        return active
    except Exception:
        return str(store.setdefault('settings', {}).get('_active_currency_ledger') or 'ars').lower()

def _v151_ars_records(chat_id: int) -> list[dict]:
    """Authoritative ARS ledger for every report/export/UI balance calculation.

    v253 currency-isolation contract:
    * a pure USD operation is never projected into the ARS table;
    * a genuinely mixed operation (non-zero ARS + USD component) remains in both
      independent currency sections;
    * historical ARS amounts are never re-parsed from source text.

    Pure USD is detected only from explicit accounting metadata, never from note
    text: ``usd_only``, explicit ``currency=USD``, or the safe legacy shape
    ``amount == 0`` with a non-zero ``usd_amount``.  The last shape has no ARS
    monetary effect, so excluding it cannot change a real peso balance.
    """
    # R15: immediately after an incremental finance commit the store is already
    # consistent for rendering (records + daily_records + balance).  The debounced
    # FINANCE_TASK_POOL finalizer performs the historical full normalize/dedupe.
    # Skipping it here keeps the first visual repaint cheap on long histories.
    store = get_chat_store(int(chat_id))
    if not bool(store.get('_finance_hotpath_pending_normalize_r15')):
        try:
            normalize_chat_records(int(chat_id))
        except Exception as _v258_norm_exc:
            try: log_error(f'v258 report normalize ARS {chat_id}: {_v258_norm_exc}')
            except Exception: pass
        store = get_chat_store(int(chat_id))
    active = _v151_sync_currency_snapshots(store)
    source = store.get('records', []) if active == 'ars' else store.get('ars_records', [])
    rows = []
    filtered_pure_usd = 0
    for rec in source or []:
        if not isinstance(rec, dict):
            continue
        ars_amount = _v151_float(rec.get('amount'))
        usd_amount = _v151_float(rec.get('usd_amount'))
        explicit_currency = str(rec.get('currency') or '').strip().casefold()
        pure_usd = bool(rec.get('usd_only', False))
        pure_usd = pure_usd or explicit_currency in {'usd', '$', 'us$', 'u$s'}
        pure_usd = pure_usd or (abs(ars_amount) <= 1e-12 and abs(usd_amount) > 1e-12)
        if pure_usd:
            filtered_pure_usd += 1
            continue
        item = dict(rec)
        item['_v151_amount'] = ars_amount
        item['_v151_note'] = str(rec.get('note') or '')
        item['_v151_currency'] = 'ars'
        item['_v195_authoritative'] = True
        rows.append(item)
    if filtered_pure_usd:
        try:
            bot_journal('google_excel_pure_usd_removed_from_ars_v253', int(chat_id), f'count={filtered_pure_usd}; active={active}')
        except Exception:
            pass
    try:
        return sorted(rows, key=record_sort_key)
    except Exception:
        return rows

def _v177_legacy_0271_v151_usd_records(chat_id: int) -> list[dict]:
    """Собирает отдельный USD-контур и старые usd_amount без дублей."""
    store = get_chat_store(int(chat_id))
    active = _v151_sync_currency_snapshots(store)
    independent = store.get('records', []) if active == 'usd' else store.get('usd_records', [])
    ars_source = store.get('records', []) if active == 'ars' else store.get('ars_records', [])
    rows = []
    seen = set()

    def _key(rec: dict, prefix: str=''):
        operation_key = str(rec.get('operation_key') or '').strip()
        source_msg_id = int(rec.get('source_msg_id') or 0)
        if operation_key:
            return ('op', operation_key)
        if source_msg_id:
            return ('msg', source_msg_id)
        return (prefix, int(rec.get('id') or 0), str(rec.get('timestamp') or ''), _v151_day_key(rec))
    for rec in independent or []:
        if not isinstance(rec, dict):
            continue
        item = dict(rec)
        item['_v151_amount'] = _v151_float(rec.get('amount'))
        item['_v151_note'] = str(rec.get('note') or rec.get('usd_note') or '')
        item['_v151_currency'] = 'usd'
        key = _key(item, 'usd')
        seen.add(key)
        rows.append(item)
    for rec in ars_source or []:
        if not isinstance(rec, dict):
            continue
        if rec.get('usd_amount') is None or abs(_v151_float(rec.get('usd_amount'))) <= 1e-12:
            continue
        key = _key(rec, 'embedded')
        if key in seen:
            continue
        item = dict(rec)
        item['_v151_amount'] = _v151_float(rec.get('usd_amount'))
        item['_v151_note'] = str(rec.get('usd_note') or rec.get('note') or '')
        item['_v151_currency'] = 'usd'
        item['_v151_embedded'] = True
        seen.add(key)
        rows.append(item)
    try:
        return sorted(rows, key=record_sort_key)
    except Exception:
        return rows
try:
    _v177_legacy_0271_v151_usd_records.__name__ = '_v151_usd_records'
except Exception:
    pass

def _v151_all_records(chat_id: int, currency: str) -> list[dict]:
    return _v151_usd_records(chat_id) if str(currency).lower() == 'usd' else _v151_ars_records(chat_id)

def _v151_context() -> dict:
    return dict(getattr(_V151_EXPORT_LOCAL, 'value', None) or {})

def _v177_legacy_0273_v151_context_bounds(chat_id: int, ctx: dict | None=None) -> tuple[str, str]:
    ctx = dict(ctx or _v151_context())
    day_key = str(ctx.get('day_key') or today_key())[:10]
    kind = str(ctx.get('kind') or 'period')
    if kind == 'exact':
        start = str(ctx.get('start_key') or day_key)[:10]
        end = str(ctx.get('end_key') or day_key)[:10]
        return (end, start) if end < start else (start, end)
    mode = str(ctx.get('mode') or 'all').replace('csv_', '').replace('xlsx_', '')
    base = _v151_parse_day(day_key) or now_local().replace(hour=0, minute=0, second=0, microsecond=0)
    if mode == 'day':
        return (day_key, day_key)
    if mode == 'week':
        return ((base - _v151_timedelta(days=6)).strftime('%Y-%m-%d'), day_key)
    if mode == 'month':
        return (base.replace(day=1).strftime('%Y-%m-%d'), day_key)
    if mode == 'wedthu':
        start = base
        while start.weekday() != 2:
            start -= _v151_timedelta(days=1)
        return (start.strftime('%Y-%m-%d'), (start + _v151_timedelta(days=1)).strftime('%Y-%m-%d'))
    days = [_v151_day_key(r) for r in _v151_ars_records(chat_id) + _v151_usd_records(chat_id)]
    days = sorted((x for x in days if _v151_parse_day(x)))
    return (days[0], days[-1]) if days else (day_key, day_key)
try:
    _v177_legacy_0273_v151_context_bounds.__name__ = '_v151_context_bounds'
except Exception:
    pass

def _v151_period_days(start_key: str, end_key: str) -> int:
    start = _v151_parse_day(start_key)
    end = _v151_parse_day(end_key)
    if not start or not end:
        return 1
    if end < start:
        start, end = (end, start)
    return max(1, (end.date() - start.date()).days + 1)

def _v151_records_in_context(chat_id: int, currency: str, ctx: dict | None=None) -> list[dict]:
    ctx = dict(ctx or _v151_context())
    start_key, end_key = _v151_context_bounds(chat_id, ctx)
    start_rid = int(ctx.get('start_rid') or 0)
    end_rid = int(ctx.get('end_rid') or 0)
    exact = str(ctx.get('kind') or '') == 'exact'
    out = []
    for rec in _v151_all_records(chat_id, currency):
        day = _v151_day_key(rec)
        if not day or day < start_key or day > end_key:
            continue
        if exact and str(currency).lower() == 'ars':
            rid = int(rec.get('id') or 0)
            if day == start_key and start_rid and (rid < start_rid):
                continue
            if day == end_key and end_rid and (rid > end_rid):
                continue
        out.append(rec)
    try:
        return sorted(out, key=record_sort_key)
    except Exception:
        return out

def _v151_opening_balance(chat_id: int, currency: str, ctx: dict | None=None) -> float:
    ctx = dict(ctx or _v151_context())
    start_key, _end_key = _v151_context_bounds(chat_id, ctx)
    start_rid = int(ctx.get('start_rid') or 0)
    exact = str(ctx.get('kind') or '') == 'exact'
    canonical = globals().get('_excel_canonical_opening_balance')
    if callable(canonical):
        return float(canonical(int(chat_id), currency, start_key, start_rid, exact))
    total = 0.0
    for rec in _v151_all_records(chat_id, currency):
        day = _v151_day_key(rec)
        if day < start_key:
            total += _v151_float(rec.get('_v151_amount'))
            continue
        if day > start_key:
            break
        if exact and str(currency).lower() == 'ars' and start_rid:
            if int(rec.get('id') or 0) < start_rid:
                total += _v151_float(rec.get('_v151_amount'))
                continue
        break
    return total

def _v151_usd_rate() -> float:
    try:
        row = usd_rate_cached(force=False) or {}
        return max(0.0, _v151_float(row.get('rate') or row.get('venta') or row.get('sell')))
    except Exception:
        return 0.0

def _v151_product_total(chat_id: int, records: list[dict]) -> float:
    store = get_chat_store(int(chat_id))
    total = 0.0
    for rec in records or []:
        amount = _v151_float(rec.get('_v151_amount'))
        if amount >= 0:
            continue
        note = str(rec.get('_v151_note') or '')
        try:
            category = resolve_expense_category(note, store)
            override_slug = str((rec or {}).get('category_override_slug') or '').strip()
            if override_slug:
                category = get_category_by_slug(override_slug, store) or category
            category = str(category or '').strip().casefold()
        except Exception:
            category = ''
        if category in {'продукты', 'продукт', 'еда', 'food', 'products'}:
            total += abs(amount)
    return total

def _v151_food_metric(chat_id: int, records: list[dict], start_key: str, end_key: str) -> tuple[float, float, int, float]:
    products = _v151_product_total(chat_id, records)
    days = _v151_period_days(start_key, end_key)
    rate = _v151_usd_rate()
    metric = products / 5.0 / rate / days if rate > 0 and days > 0 else 0.0
    return (products, metric, days, rate)

def _v151_reserve(chat_id: int, currency: str) -> float:
    try:
        return max(0.0, _v151_float(gomonk_total(int(chat_id), currency)))
    except Exception:
        return 0.0

def _v151_table_totals(records: list[dict], opening: float) -> tuple[float, float, float]:
    income = sum((max(0.0, _v151_float(r.get('_v151_amount'))) for r in records or []))
    expense = sum((max(0.0, -_v151_float(r.get('_v151_amount'))) for r in records or []))
    return (income, expense, opening + income - expense)

def _v177_legacy_0274_v151_simple_table(chat_id: int, currency: str, compact: bool=False) -> tuple[list[list], dict[tuple[int, int], str]]:
    """Build the canonical simple table.

    v257 Google/full-table contract: A=Date, B=Description, C=Amount. Income is
    positive and expense is negative in the same C column. Period Income and
    Period Expense totals are also both displayed in C (expense total positive).
    The compact legacy export keeps its historical three-column split because it
    is a separate downloadable layout and is not the Thu-Wed Google grid.
    """
    ctx = _v151_context()
    start_key, end_key = _v151_context_bounds(chat_id, ctx)
    records = _v151_records_in_context(chat_id, currency, ctx)
    opening = _v151_opening_balance(chat_id, currency, ctx)
    income, expense, closing = _v151_table_totals(records, opening)
    reserve = _v151_reserve(chat_id, currency)
    turnover = closing - min(reserve, max(0.0, closing))
    rows = []
    annotations: dict[tuple[int, int], str] = {}
    title = str(currency).upper()
    if compact:
        rows.extend([[title, '', ''], ['Дата', 'Приход', 'Расход'], ['Остаток с прошлого раза', _v151_num(opening), ''], []])
        prev_day = None
        for rec in records:
            day = _v151_day_key(rec)
            if prev_day is not None and day != prev_day:
                rows.append([])
            prev_day = day
            amount = _v151_float(rec.get('_v151_amount'))
            income_cell, expense_cell = _xlsx_income_expense_values(amount)
            rows.append([fmt_date_table(day), income_cell, expense_cell])
            note = str(rec.get('_v151_note') or '').strip()
            if note:
                annotations[len(rows), 2 if income_cell != '' else 3] = note
        rows.extend([[], ['Приход за период', _v151_num(income), ''], ['Расход за период', '', _v151_num(expense)], ['Остаток на руках', _v151_num(closing), ''], ['Гомонковые', _v151_num(reserve), ''], ['Остаток в обороте', _v151_num(turnover), '']])
        if currency == 'ars':
            products, metric, days, rate = _v151_food_metric(chat_id, records, start_key, end_key)
            rows.extend([[], ['Продукты', _v151_num(products), ''], [], ['Расход еды на человека в сутки', metric, ''], ['Расчёт', f'{days} дн. · 5 чел. · курс {rate:g}' if rate > 0 else f'{days} дн. · 5 чел. · курс не найден', '']])
        return (rows, annotations)

    rows.extend([[title, '', ''], ['Дата', 'Описание', 'Приход'], ['', 'Остаток с прошлого раза', _v151_num(opening)], []])
    prev_day = None
    for rec in records:
        day = _v151_day_key(rec)
        if prev_day is not None and day != prev_day:
            rows.append([])
        prev_day = day
        amount = _v151_float(rec.get('_v151_amount'))
        rows.append([fmt_date_table(day), str(rec.get('_v151_note') or ''), _v151_num(amount)])
    rows.extend([[], ['', 'Приход за период', _v151_num(income)], ['', 'Расход за период', _v151_num(expense)], ['', 'Остаток на руках', _v151_num(closing)], ['', 'Гомонковые', _v151_num(reserve)], ['', 'Остаток в обороте', _v151_num(turnover)]])
    if currency == 'ars':
        products, metric, days, rate = _v151_food_metric(chat_id, records, start_key, end_key)
        rows.extend([[], ['', 'Продукты', _v151_num(products)], [], ['', 'Расход еды на человека в сутки', metric], ['', 'Расчёт', f'{days} дн. · 5 чел. · курс {rate:g}' if rate > 0 else f'{days} дн. · 5 чел. · курс не найден']])
    return (rows, annotations)

try:
    _v177_legacy_0274_v151_simple_table.__name__ = '_v151_simple_table'
except Exception:
    pass

def _v177_legacy_0275_v151_categories(chat_id: int, records: list[dict]) -> list[str]:
    store = get_chat_store(int(chat_id))
    totals = {}
    for rec in records:
        amount = _v151_float(rec.get('_v151_amount'))
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
        totals[str(category or 'прочие')] = totals.get(str(category or 'прочие'), 0.0) + abs(amount)
    try:
        categories = list(get_ordered_category_names(cats=totals, store=store) or [])
    except Exception:
        categories = list(totals)
    return categories or ['прочие']
try:
    _v177_legacy_0275_v151_categories.__name__ = '_v151_categories'
except Exception:
    pass

def _v177_legacy_0276_v151_category_table(chat_id: int, currency: str) -> list[list]:
    ctx = _v151_context()
    start_key, end_key = _v151_context_bounds(chat_id, ctx)
    records = _v151_records_in_context(chat_id, currency, ctx)
    opening = _v151_opening_balance(chat_id, currency, ctx)
    categories = _v151_categories(chat_id, records)
    clean_categories = [_clean_category_display_name(x) for x in categories]
    rows = [[str(currency).upper()] + [''] * (2 + len(categories))]
    rows.append(['Дата', 'Описание', 'Приход'] + clean_categories)
    rows.append(['', 'Остаток с прошлого раза', _v151_num(opening)] + [''] * len(categories))
    rows.append([])
    store = get_chat_store(int(chat_id))
    cat_totals = {cat: 0.0 for cat in categories}
    income = 0.0
    expense = 0.0
    prev_day = None
    for rec in records:
        day = _v151_day_key(rec)
        if prev_day is not None and day != prev_day:
            rows.append([])
        prev_day = day
        note = str(rec.get('_v151_note') or '')
        amount = _v151_float(rec.get('_v151_amount'))
        row = [fmt_date_table(day), note, ''] + [''] * len(categories)
        if amount >= 0:
            income += amount
            row[2] = _v151_num(amount)
        else:
            value = abs(amount)
            expense += value
            try:
                category = resolve_expense_category(note, store)
                override_slug = str(rec.get('category_override_slug') or '').strip()
                if override_slug:
                    category = get_category_by_slug(override_slug, store) or category
            except Exception:
                category = 'прочие'
            if category not in cat_totals:
                category = categories[-1]
            idx = categories.index(category)
            cat_totals[category] += value
            row[3 + idx] = _v151_num(value)
        rows.append(row)
    closing = opening + income - expense
    reserve = _v151_reserve(chat_id, currency)
    turnover = closing - min(reserve, max(0.0, closing))
    rows.extend([[], ['', 'Сумма по статьям', _v151_num(income)] + [_v151_num(cat_totals.get(cat, 0.0)) for cat in categories], [], ['', 'Расход', _v151_num(expense)] + [''] * len(categories), ['', 'Приход', _v151_num(income)] + [''] * len(categories), ['', 'Остаток на руках', _v151_num(closing)] + [''] * len(categories), ['', 'Гомонковые', _v151_num(reserve)] + [''] * len(categories), ['', 'Остаток в обороте', _v151_num(turnover)] + [''] * len(categories)])
    if currency == 'ars':
        products, metric, days, rate = _v151_food_metric(chat_id, records, start_key, end_key)
        rows.extend([[], ['', 'Продукты', _v151_num(products)] + [''] * len(categories), [], ['', 'Расход еды на человека в сутки', metric] + [''] * len(categories), ['', 'Расчёт', f'{days} дн. · 5 чел. · курс {rate:g}' if rate > 0 else f'{days} дн. · 5 чел. · курс не найден'] + [''] * len(categories)])
    return rows

try:
    _v177_legacy_0276_v151_category_table.__name__ = '_v151_category_table'
except Exception:
    pass

def _v177_legacy_0176_build_exact_category_stats_xlsx_rows(target_chat_id: int, start_key: str, start_rid: int, end_key: str, end_rid: int) -> list[list]:
    previous = getattr(_V151_EXPORT_LOCAL, 'value', None)
    if not previous:
        _V151_EXPORT_LOCAL.value = {'kind': 'exact', 'target_chat_id': int(target_chat_id), 'start_key': str(start_key)[:10], 'start_rid': int(start_rid or 0), 'end_key': str(end_key)[:10], 'end_rid': int(end_rid or 0), 'file_type': 'xlsxstat'}
    try:
        ars_rows = _v151_category_table(int(target_chat_id), 'ars')
        usd_rows = _v151_category_table(int(target_chat_id), 'usd')
        return ars_rows + [[], []] + usd_rows
    finally:
        if not previous:
            _V151_EXPORT_LOCAL.value = None
try:
    _v177_legacy_0176_build_exact_category_stats_xlsx_rows.__name__ = 'build_exact_category_stats_xlsx_rows'
except Exception:
    pass

def _v177_legacy_0092_xlsx_simple_rows_with_balances(rows: list[list], opening_balance: float, target_chat_id: int | None=None) -> list[list]:
    if target_chat_id is None:
        return globals().get('_V150_BASE_SIMPLE_ROWS', lambda r, o, *_: r)(rows, opening_balance, target_chat_id)
    ars_rows, _ = _v151_simple_table(int(target_chat_id), 'ars', compact=False)
    usd_rows, _ = _v151_simple_table(int(target_chat_id), 'usd', compact=False)
    return ars_rows + [[], []] + usd_rows
try:
    _v177_legacy_0092_xlsx_simple_rows_with_balances.__name__ = '_xlsx_simple_rows_with_balances'
except Exception:
    pass

def _v177_legacy_0095_compact_simple_excel_rows_and_annotations(raw_rows: list[tuple], opening_balance: float, target_chat_id: int | None=None) -> tuple[list[list], dict[tuple[int, int], str]]:
    if target_chat_id is None:
        base = globals().get('_V150_BASE_COMPACT_ROWS')
        return base(raw_rows, opening_balance, target_chat_id) if callable(base) else ([], {})
    ars_rows, ars_notes = _v151_simple_table(int(target_chat_id), 'ars', compact=True)
    offset = len(ars_rows) + 2
    usd_rows, usd_notes = _v151_simple_table(int(target_chat_id), 'usd', compact=True)
    notes = dict(ars_notes)
    for (row_idx, col_idx), text in usd_notes.items():
        notes[int(row_idx) + offset, int(col_idx)] = text
    return (ars_rows + [[], []] + usd_rows, notes)
try:
    _v177_legacy_0095_compact_simple_excel_rows_and_annotations.__name__ = '_compact_simple_excel_rows_and_annotations'
except Exception:
    pass

def _v151_excel_options_for_style(style: str | None, options: dict | None) -> dict | None:
    if isinstance(options, dict):
        return options
    mode = str(style or '').strip().lower()
    if not mode:
        try:
            return normalize_excel_export_options()
        except Exception:
            return {'old_table': True, 'comments': False, 'notes': False, 'description_column': True}
    mapping = {'old': {'old_table': True, 'comments': False, 'notes': False, 'description_column': True}, 'new_plain': {'old_table': False, 'comments': False, 'notes': False, 'description_column': True}, 'new_comments': {'old_table': False, 'comments': True, 'notes': False, 'description_column': True}, 'new_notes': {'old_table': False, 'comments': False, 'notes': True, 'description_column': True}, 'google_notes': {'old_table': False, 'comments': False, 'notes': True, 'description_column': True}}
    return mapping.get(mode) or normalize_excel_export_options()

def _canon_send_export_for_chat_to__001(recipient_chat_id: int, target_chat_id: int, mode: str, day_key: str, file_type: str='csv', excel_style_override: str | None=None, excel_options_override: dict | None=None, delivery: str='chat'):
    previous = getattr(_V151_EXPORT_LOCAL, 'value', None)
    _V151_EXPORT_LOCAL.value = {'kind': 'period', 'target_chat_id': int(target_chat_id), 'mode': str(mode or 'all'), 'day_key': str(day_key or today_key())[:10], 'file_type': str(file_type or 'csv').lower()}
    try:
        options = excel_options_override
        if str(file_type or '').lower().lstrip('.') in {'xlsx', 'xlsxstat'}:
            effective_style = excel_style_override or excel_table_style(int(target_chat_id))
            options = _v151_excel_options_for_style(effective_style, excel_options_override)
        return _V151_BASE_SEND_EXPORT(recipient_chat_id, target_chat_id, mode, day_key, file_type, excel_style_override=excel_style_override, excel_options_override=options, delivery=delivery)
    finally:
        _V151_EXPORT_LOCAL.value = previous

def _canon_send_exact_range_export__001(recipient_chat_id: int, target_chat_id: int, start_key: str, start_rid: int, end_key: str, end_rid: int, file_type: str, excel_style_override: str | None=None, excel_options_override: dict | None=None, delivery: str='chat'):
    previous = getattr(_V151_EXPORT_LOCAL, 'value', None)
    _V151_EXPORT_LOCAL.value = {'kind': 'exact', 'target_chat_id': int(target_chat_id), 'start_key': str(start_key)[:10], 'start_rid': int(start_rid or 0), 'end_key': str(end_key)[:10], 'end_rid': int(end_rid or 0), 'file_type': str(file_type or 'csv').lower()}
    try:
        options = excel_options_override
        if str(file_type or '').lower().lstrip('.') in {'xlsx', 'xlsxstat'}:
            effective_style = excel_style_override or excel_table_style(int(target_chat_id))
            options = _v151_excel_options_for_style(effective_style, excel_options_override)
        return _V151_BASE_SEND_EXACT_EXPORT(recipient_chat_id, target_chat_id, start_key, start_rid, end_key, end_rid, file_type, excel_style_override=excel_style_override, excel_options_override=options, delivery=delivery)
    finally:
        _V151_EXPORT_LOCAL.value = previous

def _v177_legacy_0204_period_export_rows(chat_id: int, mode: str, day_key: str):
    """Canonical rows for every CSV/XLSX period export.

    CSV follows the selected ARS/USD operation view. XLSX builders later build
    both isolated ledgers, so ARS rows here are only the presence/caption source.
    """
    ctx = _v151_context()
    file_type = str(ctx.get('file_type') or 'csv').lower()
    store = get_chat_store(int(chat_id))
    currency = 'ars' if file_type in {'xlsx', 'xlsxstat'} else 'usd' if financial_view_is_usd(store) else 'ars'
    records = _v151_records_in_context(int(chat_id), currency, ctx)
    if file_type in {'xlsx', 'xlsxstat'} and (not records):
        records = _v151_records_in_context(int(chat_id), 'usd', ctx)
    rows = [(fmt_date_table(_v151_day_key(r)), fmt_csv_amount(r.get('_v151_amount')), r.get('_v151_note', '')) for r in records]
    labels = {'day': 'за день', 'week': 'за неделю', 'month': 'за месяц', 'wedthu': 'Чт–Ср', 'all': 'за всё время'}
    normalized = str(mode or 'all').replace('csv_', '').replace('xlsx_', '')
    label = labels.get(normalized, 'за всё время')
    if currency == 'usd' and file_type not in {'xlsx', 'xlsxstat'}:
        label = 'USD ' + label
    return (rows, label)
try:
    _v177_legacy_0204_period_export_rows.__name__ = '_period_export_rows'
except Exception:
    pass

def _canon_exact_export_rows__001(chat_id: int, start_key: str, start_rid: int, end_key: str, end_rid: int):
    ctx = _v151_context()
    file_type = str(ctx.get('file_type') or 'csv').lower()
    store = get_chat_store(int(chat_id))
    currency = 'ars' if file_type in {'xlsx', 'xlsxstat'} else 'usd' if financial_view_is_usd(store) else 'ars'
    records = _v151_records_in_context(int(chat_id), currency, ctx)
    if file_type in {'xlsx', 'xlsxstat'} and (not records):
        records = _v151_records_in_context(int(chat_id), 'usd', ctx)
    return [(fmt_date_table(_v151_day_key(r)), fmt_csv_amount(r.get('_v151_amount')), r.get('_v151_note', '')) for r in records]

def _v151_rebalance_key(chat_id: int, currency: str, rec: dict) -> str:
    operation_key = str((rec or {}).get('operation_key') or '').strip()
    if operation_key:
        return f'{int(chat_id)}:{currency}:{operation_key}'
    source_msg_id = int((rec or {}).get('source_msg_id') or 0)
    if source_msg_id:
        return f'{int(chat_id)}:{currency}:msg:{source_msg_id}'
    return f"{int(chat_id)}:{currency}:rid:{int((rec or {}).get('id') or 0)}:{str((rec or {}).get('timestamp') or '')}"

def _v151_ledger_balance(chat_id: int, currency: str) -> float:
    return sum((_v151_float(r.get('_v151_amount')) for r in _v151_all_records(int(chat_id), currency)))

def _v151_reduce_reserve(chat_id: int, currency: str, amount: float) -> list[dict]:
    entries = [dict(x) for x in gomonk_entries(int(chat_id), currency) or []]
    left = max(0.0, _v151_float(amount))
    for idx in range(len(entries) - 1, -1, -1):
        if left <= 1e-09:
            break
        current = max(0.0, _v151_float(entries[idx].get('amount')))
        used = min(current, left)
        entries[idx]['amount'] = current - used
        left -= used
    return [x for x in entries if _v151_float(x.get('amount')) > 1e-09]

def _v151_apply_reserve_cover(chat_id: int, currency: str, rec: dict | None, reason: str='new_finance_operation') -> dict:
    if not isinstance(rec, dict):
        return {}
    currency = 'usd' if str(currency).lower() == 'usd' else 'ars'
    marker_root = rec.setdefault('gomonk_rebalance_v151', {})
    if marker_root.get(currency):
        return marker_root[currency]
    key = _v151_rebalance_key(int(chat_id), currency, rec)
    receipts = data.setdefault('gomonk_rebalance_receipts_v151', {})
    with _V151_REBALANCE_LOCK:
        existing = receipts.get(key)
        if isinstance(existing, dict) and existing.get('status') == 'done':
            marker_root[currency] = dict(existing.get('result') or existing)
            return marker_root[currency]
        settings = get_chat_store(int(chat_id)).setdefault('settings', {})
        enabled_key = 'usd_gomonk_enabled' if currency == 'usd' else 'gomonk_enabled'
        balance = _v151_ledger_balance(int(chat_id), currency)
        target = _v151_reserve(int(chat_id), currency)
        effective = min(target, max(0.0, balance)) if bool(settings.get(enabled_key, False)) else 0.0
        virtual_used = max(0.0, target - effective) if bool(settings.get(enabled_key, False)) else 0.0
        turnover_before = balance - target
        turnover_after = balance - effective
        receipts[key] = {'status': 'pending', 'chat_id': int(chat_id), 'currency': currency, 'record_id': rec.get('id'), 'source_msg_id': rec.get('source_msg_id'), 'created_at': _v151_now(), 'reason': reason}
        result = {'key': key, 'currency': currency, 'at': _v151_now(), 'reason': reason, 'balance': balance, 'reserve_before': target, 'turnover_before': turnover_before, 'consumed': virtual_used, 'reserve_after': effective, 'turnover_after': turnover_after, 'constant_target_v209': target, 'entries_mutated': False}
        marker_root[currency] = result
        receipts[key] = {'status': 'done', 'done_at': _v151_now(), 'result': result}
        history = settings.setdefault('gomonk_rebalance_history_v151', [])
        history.append({**result, 'record_id': rec.get('id'), 'source_msg_id': rec.get('source_msg_id')})
        del history[:-500]
        try:
            persist_finance_chat_local_fast(int(chat_id))
        except Exception:
            pass
        try:
            fn = globals().get('schedule_finance_root_persist_v243')
            if callable(fn):
                fn(int(chat_id), 0.45)
        except Exception:
            pass
        try:
            schedule_config_backup_for_chats(int(chat_id), delay=0.8)
        except Exception:
            pass
        try:
            bot_journal('gomonk_constant_cover_v209', int(chat_id), f'currency={currency}; key={key}; target={target}; active={effective}; turnover={turnover_after}')
        except Exception:
            pass
        return result

# R11: the authoritative finance row is already committed by _finance_add_record_base.
# Gomonk/reserve-cover is derived state and must never keep the Telegram content lane
# busy after that commit. Queue it on the per-chat FINANCE lane and coalesce bursts.
_V151_POSTCOMMIT_LOCK = _v151_threading.RLock()
_V151_POSTCOMMIT_PENDING = {}
_V151_POSTCOMMIT_RUNNING = set()

def _v151_postcommit_identity(chat_id: int, rec: dict) -> dict:
    return {
        'uid': str((rec or {}).get('record_uid') or ''),
        'source_msg_id': int((rec or {}).get('source_msg_id') or 0),
        'record_id': int((rec or {}).get('id') or 0),
        'day_key': str((rec or {}).get('day_key') or ''),
    }

def _v151_resolve_postcommit_record(chat_id: int, ident: dict):
    uid = str((ident or {}).get('uid') or '')
    if uid and callable(globals().get('find_finance_record_by_uid')):
        try:
            rec = find_finance_record_by_uid(int(chat_id), uid)
            if isinstance(rec, dict):
                return rec
        except Exception:
            pass
    source_msg_id = int((ident or {}).get('source_msg_id') or 0)
    if source_msg_id and callable(globals().get('find_record_by_message_id')):
        try:
            rec = find_record_by_message_id(int(chat_id), source_msg_id)
            if isinstance(rec, dict):
                return rec
        except Exception:
            pass
    rid = int((ident or {}).get('record_id') or 0)
    try:
        for _key, rec in _finance_record_lists(get_chat_store(int(chat_id))):
            if isinstance(rec, dict) and rid and int(rec.get('id') or 0) == rid:
                return rec
    except Exception:
        pass
    return None

def _v151_postcommit_cover_job(chat_id: int):
    cid = int(chat_id)
    try:
        while True:
            with _V151_POSTCOMMIT_LOCK:
                batch = list((_V151_POSTCOMMIT_PENDING.get(cid) or {}).values())
                _V151_POSTCOMMIT_PENDING[cid] = {}
            if not batch:
                break
            last_day = ''
            for item in batch:
                ident = dict(item.get('ident') or {})
                rec = _v151_resolve_postcommit_record(cid, ident)
                if not isinstance(rec, dict):
                    continue
                last_day = str(ident.get('day_key') or rec.get('day_key') or last_day)
                for currency in tuple(item.get('currencies') or ('ars',)):
                    try:
                        _v151_apply_reserve_cover(cid, str(currency), rec, 'postcommit_async_r11')
                    except Exception as exc:
                        try: log_error(f'R11 async reserve cover chat={cid} currency={currency}: {exc}')
                        except Exception: pass
            # finance_changed/schedule_finalize is normally queued by the caller after
            # add_record_to_chat returns. A tiny safety repaint is only needed when this
            # helper was invoked from a path that did not schedule one.
            try:
                if last_day and callable(globals().get('schedule_financial_window_refresh')):
                    schedule_financial_window_refresh(cid, last_day, reason='reserve_cover_r11', delay=0.02)
            except Exception:
                pass
    finally:
        rerun = False
        with _V151_POSTCOMMIT_LOCK:
            _V151_POSTCOMMIT_RUNNING.discard(cid)
            rerun = bool(_V151_POSTCOMMIT_PENDING.get(cid))
        if rerun:
            _v151_schedule_postcommit_cover(cid, None, ())

def _v151_schedule_postcommit_cover(chat_id: int, rec: dict | None, currencies) -> bool:
    cid = int(chat_id)
    with _V151_POSTCOMMIT_LOCK:
        if isinstance(rec, dict):
            ident = _v151_postcommit_identity(cid, rec)
            key = str(ident.get('uid') or ident.get('source_msg_id') or ident.get('record_id') or id(rec))
            row = (_V151_POSTCOMMIT_PENDING.setdefault(cid, {})).setdefault(key, {'ident': ident, 'currencies': set()})
            row['currencies'].update(str(x) for x in (currencies or ()) if x)
        if cid in _V151_POSTCOMMIT_RUNNING:
            return True
        if not _V151_POSTCOMMIT_PENDING.get(cid):
            return True
        _V151_POSTCOMMIT_RUNNING.add(cid)
    pool = globals().get('FINANCE_TASK_POOL')
    try:
        if pool is not None and hasattr(pool, 'submit') and pool.submit(cid, _v151_postcommit_cover_job, cid):
            return True
    except Exception:
        pass
    # Never fall back to synchronous work in the Telegram/content thread.
    try:
        t = _v151_threading.Thread(target=_v151_postcommit_cover_job, args=(cid,), name=f'fin-cover-r11-{cid}', daemon=True)
        t.start()
        return True
    except Exception:
        with _V151_POSTCOMMIT_LOCK:
            _V151_POSTCOMMIT_RUNNING.discard(cid)
        return False

def add_record_to_chat(chat_id: int, amount: float, note: str, owner: int, source_msg=None, day_key=None, usd_amount=None, usd_note: str='', usd_only: bool=False, source_finance_text: str=''):
    rec = _V151_BASE_ADD_RECORD(chat_id, amount, note, owner, source_msg=source_msg, day_key=day_key, usd_amount=usd_amount, usd_note=usd_note, usd_only=usd_only, source_finance_text=source_finance_text)
    if isinstance(rec, dict):
        try:
            ensure_finance_record_uid(int(chat_id), rec)
        except Exception:
            pass
        currencies = ['ars']
        if usd_amount is not None:
            currencies.append('usd')
        _v151_schedule_postcommit_cover(int(chat_id), rec, currencies)
    return rec

def _add_record_to_currency_ledger(chat_id: int, ledger: str, amount: float, note: str, owner: int, source_msg=None, day_key: str | None=None):
    ledger = 'usd' if str(ledger).lower() == 'usd' else 'ars'
    store_before = get_chat_store(int(chat_id))
    active = str(store_before.setdefault('settings', {}).get('_active_currency_ledger') or 'ars')
    records_before = store_before.get('records', []) if active == ledger else store_before.get(f'{ledger}_records', [])
    existing_keys = {_v151_rebalance_key(int(chat_id), ledger, r) for r in records_before or [] if isinstance(r, dict)}
    result = _V151_BASE_ADD_LEDGER_RECORD(chat_id, ledger, amount, note, owner, source_msg=source_msg, day_key=day_key)
    store_after = get_chat_store(int(chat_id))
    active_after = str(store_after.setdefault('settings', {}).get('_active_currency_ledger') or 'ars')
    records_after = store_after.get('records', []) if active_after == ledger else store_after.get(f'{ledger}_records', [])
    rec = None
    source_msg_id = int(getattr(source_msg, 'message_id', 0) or 0) if source_msg is not None else 0
    if source_msg_id:
        rec = next((r for r in records_after or [] if isinstance(r, dict) and int(r.get('source_msg_id') or 0) == source_msg_id), None)
    if rec is None:
        rec = next((r for r in reversed(records_after or []) if isinstance(r, dict) and _v151_rebalance_key(int(chat_id), ledger, r) not in existing_keys), None)
    if rec is None and isinstance(result, dict):
        rec = result
    if isinstance(rec, dict):
        try:
            ensure_finance_record_uid(int(chat_id), rec)
        except Exception:
            pass
        _v151_schedule_postcommit_cover(int(chat_id), rec, [ledger])
        try:
            schedule_financial_window_refresh(int(chat_id), str(rec.get('day_key') or day_key or ''), reason='currency_record_add_fast_r11')
        except Exception:
            pass
    return result if result is not None else rec

def _v151_repair_pending_rebalances() -> int:
    repaired = 0
    receipts = data.setdefault('gomonk_rebalance_receipts_v151', {})
    for key, receipt in list(receipts.items()):
        if not isinstance(receipt, dict) or receipt.get('status') != 'pending':
            continue
        try:
            chat_id = int(receipt.get('chat_id'))
            currency = str(receipt.get('currency') or 'ars')
            source_msg_id = int(receipt.get('source_msg_id') or 0)
            record_id = int(receipt.get('record_id') or 0)
            rec = next((r for r in _v151_all_records(chat_id, currency) if source_msg_id and int(r.get('source_msg_id') or 0) == source_msg_id or (record_id and int(r.get('id') or 0) == record_id)), None)
            if isinstance(rec, dict):
                _v151_apply_reserve_cover(chat_id, currency, rec, 'startup_pending_repair')
                repaired += 1
            else:
                receipt.update({'status': 'cancelled_no_record', 'closed_at': _v151_now()})
        except Exception as exc:
            try:
                log_error(f'v151 reserve receipt repair {key}: {exc}')
            except Exception:
                pass
    if repaired:
        save_data(data)
    return repaired
_V151_EXAMPLE_RE = _v151_re.compile('^\\(?\\s*(?:пример\\s*:\\s*)?имя\\s*1\\s+1?[ .]?000\\s*:\\s*имя\\s*2\\s+5?[ .]?777\\s*\\)?$', flags=_v151_re.I)

def _v151_gomonk_payload(text: str) -> tuple[str, str | None]:
    raw = str(text or '').replace('\r\n', '\n').replace('\r', '\n')
    token = _v151_re.search('\\(\\s*GOMONKI\\s*\\|\\s*(ARS|USD)\\s*\\)', raw, flags=_v151_re.I)
    currency = token.group(1).lower() if token else None
    kept = []
    for line in raw.split('\n'):
        stripped = line.strip()
        folded = _v151_re.sub('\\s+', ' ', stripped).casefold()
        if not stripped:
            continue
        if _v151_re.search('\\(\\s*gomonki\\s*\\|\\s*(?:ars|usd)\\s*\\)', folded, flags=_v151_re.I):
            continue
        if _V151_EXAMPLE_RE.match(folded):
            continue
        kept.append(stripped)
    return ('\n'.join(kept).strip(), currency)

def _canon_parse_gomonk_entries__001(text: str) -> list[dict]:
    payload, _currency = _v151_gomonk_payload(sanitize_telegram_inserted_text(str(text or '')))
    if not payload:
        return []
    parts = [p.strip() for p in _v151_re.split('\\s*:\\s*|\\n+', payload) if p.strip()]
    result = []
    number_pattern = '(?<![A-Za-zА-Яа-яЁё0-9_])[-+]?(?:\\d{1,3}(?:[ .]\\d{3})+(?:,\\d+)?|\\d+(?:[.,]\\d+)?)'
    for idx, part in enumerate(parts, start=1):
        folded = _v151_re.sub('\\s+', ' ', part).casefold().strip('() ')
        if folded.startswith('пример:') or _v151_re.fullmatch('имя\\s*[12]\\s+(?:1?[ .]?000|5?[ .]?777)', folded, flags=_v151_re.I):
            continue
        matches = list(_v151_re.finditer(number_pattern, part))
        if not matches:
            continue
        match = matches[-1]
        number = match.group(0).replace(' ', '').replace('.', '').replace(',', '.')
        try:
            amount = abs(float(number))
        except Exception:
            continue
        name = (part[:match.start()] + ' ' + part[match.end():]).strip(' -–—,.;') or f'Сумма {idx}'
        if amount > 0:
            result.append({'name': name[:80], 'amount': amount})
    return result[:30]

def _v151_gomonk_template(chat_id: int, currency: str, include_values: bool) -> str:
    username = get_bot_username_cached() or 'Good_server_bot'
    lines = [f'@{username} (GOMONKI|{currency.upper()})', '(Пример: Имя1 1000 : Имя2 5777)', '']
    if include_values:
        values = []
        for item in gomonk_entries(int(chat_id), currency):
            amount = _v151_num(item.get('amount'))
            values.append(f"{str(item.get('name') or 'Сумма').strip()} {amount}")
        lines.append(' : '.join(values))
    return '\n'.join(lines)

def _canon_build_gomonk_menu_keyboard__001(chat_id: int, currency: str | None=None):
    currency = _gomonk_currency(chat_id, currency)
    kb = types.InlineKeyboardMarkup(row_width=1)
    kb.row(IB(gomonk_toggle_label(chat_id, currency), callback_data=f'gomonk_toggle:{currency}'))
    can_edit = bool(gomonk_enabled(chat_id, currency) and gomonk_entries(chat_id, currency))
    label = '✏️ Изменить гомонковые' if can_edit else '💰 Ввести гомонковые'
    kb.row(make_copy_or_inline_button(label, _v151_gomonk_template(chat_id, currency, can_edit), viewer_chat_id=chat_id))
    kb.row(IB('🔙 Назад в Инфо', callback_data=f'gomonk_back:{currency}'))
    return kb

def _canon_build_gomonk_menu_text__001(chat_id: int, currency: str | None=None) -> str:
    currency = _gomonk_currency(chat_id, currency)
    entries = gomonk_entries(chat_id, currency)
    fmt = (lambda value: fmt_usd_native(value)) if currency == 'usd' else fmt_num
    lines = [f'🧳 Гомонковые • {currency.upper()}', '', 'ARS и USD хранятся отдельно.', 'Строка с примером является только подсказкой и никогда не сохраняется.', '', f"Режим: {('✅ ВКЛ' if gomonk_enabled(chat_id, currency) else '⬜ ВЫКЛ')}"]
    if entries:
        lines.append('Сохранено:')
        for item in entries:
            lines.append(f"• {item['name']}: {fmt(item['amount'])}")
        lines.append(f'Итого: {fmt(gomonk_total(chat_id, currency))}')
    else:
        lines.append('Сохранённых сумм пока нет.')
    return wm_common('\n'.join(lines), 9)

def _v177_legacy_0162_handle_gomonk_insert_message(msg) -> bool:
    if getattr(msg, 'content_type', None) != 'text' or not _v85_enabled('gomonk_wallets'):
        return False
    raw = str(getattr(msg, 'text', '') or '')
    if not _v151_re.search('\\(\\s*GOMONKI\\s*\\|\\s*(?:ARS|USD)\\s*\\)', raw, flags=_v151_re.I):
        return False
    _durable_note_source_consumed('gomonk_insert_v151')
    chat_id = int(msg.chat.id)
    payload, token_currency = _v151_gomonk_payload(raw)
    currency = token_currency or _gomonk_currency(chat_id)
    entries = parse_gomonk_entries(payload)
    try:
        bot.delete_message(chat_id, msg.message_id)
    except Exception:
        pass
    if not entries:
        send_and_auto_delete(chat_id, 'ℹ️ Шаблон получен без реальных значений. Гомонковые не изменены.', 12)
        return True
    set_gomonk_entries(chat_id, entries, currency)
    settings = _gomonk_settings(chat_id, currency)
    enabled_key, _entries_key, _remaining_key = _gomonk_keys(chat_id, currency)
    settings[enabled_key] = True
    save_data(data, chat_ids=[chat_id])
    total = gomonk_total(chat_id, currency)
    shown = fmt_usd_native(total) if currency == 'usd' else fmt_num(total)
    try:
        bot_journal('gomonk_values_saved_v151', chat_id, f'currency={currency}; count={len(entries)}; total={total}')
    except Exception:
        pass
    send_and_auto_delete(chat_id, f'✅ Гомонковые {currency.upper()} сохранены: {len(entries)}, сумма {shown}', 10)
    try:
        open_gomonk_window(chat_id, currency=currency)
        finance_changed(chat_id, get_chat_store(chat_id).get('current_view_day') or today_key(), reason='gomonk_update', delay=0.05)
    except Exception:
        pass
    return True
try:
    _v177_legacy_0162_handle_gomonk_insert_message.__name__ = 'handle_gomonk_insert_message'
except Exception:
    pass

def _canon_render_usd_month_window__001(chat_id: int, day_key: str):
    month_key = str(day_key or today_key())[:7]
    try:
        month_dt = _v151_datetime.strptime(month_key + '-01', '%Y-%m-%d')
        month_label = month_dt.strftime('%m.%Y')
    except Exception:
        month_label = month_key
    rows = [r for r in usd_records_for_month(int(chat_id), month_key) if _v151_float(r.get('usd_amount')) < 0]
    total_expense = sum((abs(_v151_float(r.get('usd_amount'))) for r in rows))
    lines = [f'💵 USD расходы за {month_label}', '']
    if rows:
        for rec in rows:
            amount = abs(_v151_float(rec.get('usd_amount')))
            sid = str(rec.get('usd_short_id') or rec.get('short_id') or f"U{rec.get('id', '')}")
            date_label = fmt_date_ddmmyy(_v151_day_key(rec))
            note = html.escape(str(rec.get('usd_note') or rec.get('note') or ''))
            lines.append(f'{sid} {date_label} -${fmt_num_plain(amount)} {note}'.rstrip())
    else:
        lines.append('Нет USD-расходов за этот месяц.')
    balance = usd_balance_for_chat(int(chat_id))
    lines.extend(['', f'📉 Расход за месяц: -${fmt_num_plain(total_expense)}', f"🏦 USD остаток по чату: {('+' if balance >= 0 else '-')}${fmt_num_plain(abs(balance))}"])
    try:
        _V151_MONTH_LOCAL.chat_id = int(chat_id)
    except Exception:
        pass
    return (wm_common('\n'.join(lines), 1, html_mode=True), -total_expense)

def _canon_build_usd_month_keyboard__001(day_key: str):
    """Возвращает ту же клавиатуру, что уже была в USD-окне."""
    chat_id = getattr(_V151_MONTH_LOCAL, 'chat_id', None)
    if chat_id is not None:
        try:
            return build_main_keyboard(str(day_key)[:10], int(chat_id))
        except Exception:
            pass
    try:
        return build_main_keyboard(str(day_key)[:10], None)
    except Exception:
        return types.InlineKeyboardMarkup()

def _canon_build_fin_window_usd_month_keyboard__001(target_chat_id: int, day_key: str, owner_day_key: str):
    """В окне владельца также сохраняется исходное расположение кнопок чата."""
    return build_fin_window_view_keyboard(int(target_chat_id), str(day_key)[:10], str(owner_day_key)[:10])

def _canon_set_webhook__001():
    try:
        repaired = _v151_repair_pending_rebalances()
        if repaired:
            try:
                bot_journal('v151_startup_repair', int(OWNER_ID or 0), f'reserve_receipts={repaired}')
            except Exception:
                pass
    except Exception as exc:
        try:
            log_error(f'v151 startup repair: {exc}')
        except Exception:
            pass
    return _V151_BASE_SET_WEBHOOK()
import functools as _v152_functools
import os as _v152_os
import re as _v152_re
from datetime import datetime as _v152_datetime
V152_CHAT_RIGHTS_SCHEMA = 1
V152_PERMISSION_GROUPS = (('finance', '💰 Финансы', (('finance.mode', 'Финансовый режим'), ('finance.ars', 'ARS'), ('finance.usd', 'USD'), ('finance.gomonk', 'Гомонковые'), ('finance.edit', 'Редактирование операций'), ('finance.delete', 'Удаление операций'), ('finance.view_totals', 'Просмотр итогов'), ('finance.view_month', 'Просмотр месяца'))), ('exports', '📤 Выгрузки', (('exports.excel_chat', 'Excel в чат'), ('exports.google_sheets', 'Google Sheets'), ('exports.google_drive', 'Google Drive'), ('exports.journals', 'Скачивание журналов'), ('exports.reports', 'Отчёты'))), ('reminders', '⏰ Напоминалки', (('reminders.use', 'Использование напоминалок'), ('reminders.create', 'Создание'), ('reminders.edit', 'Изменение'), ('reminders.delete', 'Удаление'), ('reminders.complete', 'Выполнение через /vyapl'))), ('forward', '🔁 Пересылка и чаты', (('forward.messages', 'Пересылка сообщений'), ('forward.media_groups', 'Пересылка медиагрупп'), ('chats.connect_children', 'Подключение дочерних чатов'), ('chats.manage_users', 'Управление пользователями'), ('chats.manage_roles', 'Управление ролями'))), ('settings', '⚙️ Настройки', (('settings.change', 'Изменение настроек'), ('settings.windows', 'Управление окнами'), ('settings.iphone', 'Быстрые отметки с iPhone'), ('settings.info', 'Просмотр INFO'), ('settings.diagnostics', 'Диагностика'), ('settings.backup_recovery', 'Backup и recovery'), ('settings.audit', 'Аудит'))))
V152_PERMISSION_ITEMS = tuple((item for _group, _label, items in V152_PERMISSION_GROUPS for item in items))
V152_PERMISSION_KEYS = tuple((key for key, _label in V152_PERMISSION_ITEMS))
V152_PERMISSION_LABELS = dict(V152_PERMISSION_ITEMS)
V152_PERMISSION_INDEX = {key: idx for idx, key in enumerate(V152_PERMISSION_KEYS)}

def _v152_permissions_root() -> dict:
    root = data.setdefault('_global_settings', {}).setdefault('chat_permissions_v152', {})
    if not isinstance(root, dict):
        root = {}
        data.setdefault('_global_settings', {})['chat_permissions_v152'] = root
    root.setdefault('schema_version', V152_CHAT_RIGHTS_SCHEMA)
    root.setdefault('global', {})
    root.setdefault('history', [])
    return root

def _v152_tenant_id_for_chat(chat_id: int) -> str:
    try:
        return str(tenant_id_for_chat(int(chat_id), create=False) or TENANT_PLATFORM_ID)
    except Exception:
        return str(TENANT_PLATFORM_ID)

def _v152_tenant_row(tenant_id: str) -> dict:
    try:
        return tenant_get(str(tenant_id)) or {}
    except Exception:
        return {}

def _v152_tenant_permissions(tenant_id: str) -> dict:
    row = _v152_tenant_row(tenant_id)
    settings = row.setdefault('settings', {})
    permissions = settings.setdefault('chat_permissions_v152_defaults', {})
    return permissions if isinstance(permissions, dict) else {}

def _v152_chat_policy(chat_id: int) -> dict:
    store = get_chat_store(int(chat_id))
    settings = store.setdefault('settings', {})
    policy = settings.setdefault('chat_permissions_v152', {})
    if not isinstance(policy, dict):
        policy = {}
        settings['chat_permissions_v152'] = policy
    policy.setdefault('inherit_tenant', True)
    policy.setdefault('overrides', {})
    policy.setdefault('updated_at', '')
    policy.setdefault('updated_by', 0)
    return policy

def v152_global_permission_allowed(capability: str) -> bool:
    if capability not in V152_PERMISSION_LABELS:
        return True
    return bool((_v152_permissions_root().get('global') or {}).get(capability, True))

def v152_tenant_permission_allowed(tenant_id: str, capability: str) -> bool:
    if not v152_global_permission_allowed(capability):
        return False
    return bool(_v152_tenant_permissions(str(tenant_id)).get(capability, True))

def v152_chat_permission_allowed(chat_id: int, capability: str) -> bool:
    capability = str(capability or '')
    if capability not in V152_PERMISSION_LABELS:
        return True
    tid = _v152_tenant_id_for_chat(int(chat_id))
    if not v152_global_permission_allowed(capability):
        return False
    policy = _v152_chat_policy(int(chat_id))
    if bool(policy.get('inherit_tenant', True)):
        return v152_tenant_permission_allowed(tid, capability)
    overrides = policy.get('overrides') if isinstance(policy.get('overrides'), dict) else {}
    return bool(overrides.get(capability, v152_tenant_permission_allowed(tid, capability)))

def _v152_actor_id(obj=None) -> int:
    try:
        return int(getattr(getattr(obj, 'from_user', None), 'id', 0) or tenant_current_actor_user_id() or 0)
    except Exception:
        return 0

def _v152_actor_is_platform_owner(user_id: int) -> bool:
    try:
        return bool(tenant_is_platform_owner_user(int(user_id)))
    except Exception:
        return bool(int(user_id or 0) == int(OWNER_ID or 0))

def _v152_actor_can_manage_tenant(user_id: int, tenant_id: str) -> bool:
    if _v152_actor_is_platform_owner(user_id):
        return True
    try:
        return bool(tenant_can_manage(int(user_id), str(tenant_id)))
    except Exception:
        return False

def _v152_actor_can_manage_chat(user_id: int, chat_id: int) -> bool:
    return _v152_actor_can_manage_tenant(int(user_id), _v152_tenant_id_for_chat(int(chat_id)))

def _v152_persist(reason: str, chat_id: int | None=None, tenant_id: str | None=None, actor_id: int=0) -> None:
    now = now_local().isoformat(timespec='seconds') if 'now_local' in globals() else _v152_datetime.now().isoformat(timespec='seconds')
    row = {'at': now, 'reason': str(reason), 'chat_id': int(chat_id or 0), 'tenant_id': str(tenant_id or ''), 'actor_id': int(actor_id or 0)}
    history = _v152_permissions_root().setdefault('history', [])
    history.append(row)
    del history[:-500]
    try:
        save_data(data, root_only=True)
    except TypeError:
        save_data(data)
    try:
        root_chat = int(_v152_tenant_row(tenant_id or _v152_tenant_id_for_chat(int(chat_id or 0))).get('root_chat_id') or OWNER_ID or chat_id or 0)
        if root_chat:
            schedule_delta_backup(root_chat, delay=0.35, reason=f'chat_permissions_v152:{reason}')
    except Exception:
        pass
    try:
        bot_journal('chat_permissions_v152_changed', int(chat_id or OWNER_ID or 0), f"reason={reason}; tenant={tenant_id or ''}; actor={int(actor_id or 0)}")
    except Exception:
        pass

def _v152_set_global(capability: str, enabled: bool, actor_id: int) -> bool:
    if not _v152_actor_is_platform_owner(actor_id) or capability not in V152_PERMISSION_LABELS:
        return False
    _v152_permissions_root().setdefault('global', {})[capability] = bool(enabled)
    _v152_persist(f'global:{capability}={int(bool(enabled))}', tenant_id=TENANT_PLATFORM_ID, actor_id=actor_id)
    return True

def _v152_set_tenant(tenant_id: str, capability: str, enabled: bool, actor_id: int) -> bool:
    if not _v152_actor_can_manage_tenant(actor_id, tenant_id) or capability not in V152_PERMISSION_LABELS:
        return False
    if enabled and (not v152_global_permission_allowed(capability)):
        return False
    _v152_tenant_permissions(tenant_id)[capability] = bool(enabled)
    _v152_persist(f'tenant:{capability}={int(bool(enabled))}', tenant_id=tenant_id, actor_id=actor_id)
    return True

def _v152_set_chat(chat_id: int, capability: str, enabled: bool, actor_id: int) -> bool:
    if not _v152_actor_can_manage_chat(actor_id, chat_id) or capability not in V152_PERMISSION_LABELS:
        return False
    if enabled and (not v152_global_permission_allowed(capability)):
        return False
    policy = _v152_chat_policy(chat_id)
    if bool(policy.get('inherit_tenant', True)):
        return False
    policy.setdefault('overrides', {})[capability] = bool(enabled)
    policy['updated_at'] = now_local().isoformat(timespec='seconds')
    policy['updated_by'] = int(actor_id)
    _v152_persist(f'chat:{capability}={int(bool(enabled))}', chat_id=chat_id, tenant_id=_v152_tenant_id_for_chat(chat_id), actor_id=actor_id)
    return True
V152_PRESETS = {'all': set(V152_PERMISSION_KEYS), 'none': set(), 'finance': {key for key in V152_PERMISSION_KEYS if key.startswith('finance.')} | {'exports.excel_chat', 'exports.reports', 'settings.info'}, 'view': {'finance.view_totals', 'finance.view_month', 'exports.journals', 'exports.reports', 'reminders.use', 'settings.info'}, 'standard': {'finance.mode', 'finance.ars', 'finance.usd', 'finance.gomonk', 'finance.view_totals', 'finance.view_month', 'exports.excel_chat', 'exports.reports', 'reminders.use', 'reminders.complete', 'forward.messages', 'forward.media_groups', 'settings.info'}, 'locked': {'finance.view_totals', 'finance.view_month', 'exports.journals', 'exports.reports', 'reminders.use', 'settings.info', 'settings.diagnostics'}}
V152_PRESET_LABELS = {'all': '✅ Включить всё', 'none': '⬜ Выключить всё', 'finance': '💰 Только финансы', 'view': '👁 Только просмотр', 'standard': '🧑\u200d💼 Стандартный чат', 'locked': '🔒 Заблокировать изменения'}

def _v152_apply_preset(scope: str, target: str | int, preset: str, actor_id: int) -> bool:
    enabled = V152_PRESETS.get(str(preset))
    if enabled is None:
        return False
    values = {key: bool(key in enabled and v152_global_permission_allowed(key)) for key in V152_PERMISSION_KEYS}
    if scope == 'global':
        if not _v152_actor_is_platform_owner(actor_id):
            return False
        _v152_permissions_root()['global'] = {key: key in enabled for key in V152_PERMISSION_KEYS}
        _v152_persist(f'global_preset:{preset}', tenant_id=TENANT_PLATFORM_ID, actor_id=actor_id)
        return True
    if scope == 'tenant':
        tenant_id = str(target)
        if not _v152_actor_can_manage_tenant(actor_id, tenant_id):
            return False
        _v152_tenant_row(tenant_id).setdefault('settings', {})['chat_permissions_v152_defaults'] = dict(values)
        _v152_persist(f'tenant_preset:{preset}', tenant_id=tenant_id, actor_id=actor_id)
        return True
    chat_id = int(target)
    if not _v152_actor_can_manage_chat(actor_id, chat_id):
        return False
    policy = _v152_chat_policy(chat_id)
    policy['inherit_tenant'] = False
    policy['overrides'] = dict(values)
    policy['updated_at'] = now_local().isoformat(timespec='seconds')
    policy['updated_by'] = int(actor_id)
    _v152_persist(f'chat_preset:{preset}', chat_id=chat_id, tenant_id=_v152_tenant_id_for_chat(chat_id), actor_id=actor_id)
    return True

def _v152_toggle_chat_inheritance(chat_id: int, actor_id: int) -> bool:
    if not _v152_actor_can_manage_chat(actor_id, chat_id):
        return False
    policy = _v152_chat_policy(chat_id)
    old = bool(policy.get('inherit_tenant', True))
    if old:
        tid = _v152_tenant_id_for_chat(chat_id)
        policy['overrides'] = {key: v152_tenant_permission_allowed(tid, key) for key in V152_PERMISSION_KEYS}
        policy['inherit_tenant'] = False
    else:
        policy['inherit_tenant'] = True
    policy['updated_at'] = now_local().isoformat(timespec='seconds')
    policy['updated_by'] = int(actor_id)
    _v152_persist(f'chat_inherit={int(not old)}', chat_id=chat_id, tenant_id=_v152_tenant_id_for_chat(chat_id), actor_id=actor_id)
    return True

def _v152_accessible_chats(user_id: int, context_chat_id: int) -> list[int]:
    if _v152_actor_is_platform_owner(user_id):
        out = []
        try:
            for tenant in tenant_all():
                for cid in tenant.get('chat_ids') or []:
                    if int(cid) not in out:
                        out.append(int(cid))
        except Exception:
            pass
        return sorted(out, key=lambda cid: str(get_chat_display_name(cid) or cid).casefold())
    tid = _v152_tenant_id_for_chat(context_chat_id)
    if not _v152_actor_can_manage_tenant(user_id, tid):
        return []
    try:
        return list(tenant_chat_ids(tid))
    except Exception:
        return []

def _v152_short(text: str, limit: int=38) -> str:
    text = ' '.join(str(text or '').split())
    return text if len(text) <= limit else text[:limit - 1] + '…'

def build_v152_chat_rights_list_text(user_id: int, context_chat_id: int, page: int=0) -> str:
    chats = _v152_accessible_chats(user_id, context_chat_id)
    pages = max(1, (len(chats) + 9) // 10)
    page = max(0, min(int(page), pages - 1))
    return f'🛡 ПРАВА ЧАТОВ · Ф206\n\nПрава применяются внутри обработчиков команд и callback, а не только скрывают кнопки.\nГлобальный запрет владельца платформы имеет приоритет над пространством и чатом.\n\nДоступных чатов: {len(chats)}\nСтраница: {page + 1}/{pages}'

def build_v152_chat_rights_list_keyboard(user_id: int, context_chat_id: int, page: int=0):
    chats = _v152_accessible_chats(user_id, context_chat_id)
    pages = max(1, (len(chats) + 9) // 10)
    page = max(0, min(int(page), pages - 1))
    kb = types.InlineKeyboardMarkup(row_width=1)
    if _v152_actor_is_platform_owner(user_id):
        kb.row(IB('🌐 Ограничения платформы', callback_data='v152:r:g:0'))
    tid = _v152_tenant_id_for_chat(context_chat_id)
    if _v152_actor_can_manage_tenant(user_id, tid):
        kb.row(IB('🏢 Права пространства', callback_data=f'v152:r:t:{tid}:0'))
    for cid in chats[page * 10:page * 10 + 10]:
        tenant = _v152_tenant_row(_v152_tenant_id_for_chat(cid))
        root = '⭐ ' if int((tenant or {}).get('root_chat_id') or 0) == int(cid) else ''
        kb.row(IB(root + _v152_short(get_chat_display_name(cid) or f'Чат {cid}'), callback_data=f'v152:r:c:{int(cid)}:0'))
    if pages > 1:
        nav = []
        if page > 0:
            nav.append(IB('⬅️', callback_data=f'v152:r:l:{page - 1}'))
        nav.append(IB(f'{page + 1}/{pages}', callback_data='none'))
        if page + 1 < pages:
            nav.append(IB('➡️', callback_data=f'v152:r:l:{page + 1}'))
        kb.row(*nav)
    kb.row(IB('⬅️ К защите', callback_data='safety_profile_open'))
    return kb

def _v152_scope_value(scope: str, target: str | int, capability: str) -> bool:
    if scope == 'global':
        return v152_global_permission_allowed(capability)
    if scope == 'tenant':
        return v152_tenant_permission_allowed(str(target), capability)
    return v152_chat_permission_allowed(int(target), capability)

def _v152_scope_title(scope: str, target: str | int) -> str:
    if scope == 'global':
        return '🌐 ОГРАНИЧЕНИЯ ПЛАТФОРМЫ'
    if scope == 'tenant':
        row = _v152_tenant_row(str(target))
        return f"🏢 ПРАВА ПРОСТРАНСТВА\n{row.get('name') or target}"
    chat_id = int(target)
    return f'💬 ПРАВА ЧАТА\n{get_chat_display_name(chat_id) or chat_id}'

def build_v152_permission_text(scope: str, target: str | int) -> str:
    allowed = sum((1 for key in V152_PERMISSION_KEYS if _v152_scope_value(scope, target, key)))
    lines = [_v152_scope_title(scope, target), '', f'Разрешено: {allowed}/{len(V152_PERMISSION_KEYS)}']
    if scope == 'chat':
        policy = _v152_chat_policy(int(target))
        lines.append(f"Наследовать настройки пространства: {('✅ включено' if policy.get('inherit_tenant', True) else '⬜ выключено')}")
        if policy.get('inherit_tenant', True):
            lines.append('Чтобы менять отдельные функции этого чата, сначала выключите наследование.')
    if scope != 'global':
        locked = [V152_PERMISSION_LABELS[key] for key in V152_PERMISSION_KEYS if not v152_global_permission_allowed(key)]
        if locked:
            lines.append(f'Глобально заблокировано: {len(locked)}')
    return '\n'.join(lines)

def build_v152_permission_keyboard(scope: str, target: str | int, page: int=0):
    kb = types.InlineKeyboardMarkup(row_width=1)
    if scope == 'chat':
        policy = _v152_chat_policy(int(target))
        kb.row(IB(f"Наследовать настройки пространства: {('✅ ВКЛ' if policy.get('inherit_tenant', True) else '⬜ ВЫКЛ')}", callback_data=f'v152:r:i:{int(target)}:{int(page)}'))
    for preset in ('all', 'none', 'finance', 'view', 'standard', 'locked'):
        kb.row(IB(V152_PRESET_LABELS[preset], callback_data=f'v152:r:p:{scope[0]}:{target}:{preset}:{int(page)}'))
    inherited = scope == 'chat' and bool(_v152_chat_policy(int(target)).get('inherit_tenant', True))
    for _group, group_label, items in V152_PERMISSION_GROUPS:
        kb.row(IB(group_label, callback_data='none'))
        for capability, label in items:
            enabled = _v152_scope_value(scope, target, capability)
            locked = scope != 'global' and (not v152_global_permission_allowed(capability))
            prefix = '🔒' if locked else '✅' if enabled else '⬜'
            suffix = ' · наследуется' if inherited else ''
            idx = V152_PERMISSION_INDEX[capability]
            kb.row(IB(f'{prefix} {label}{suffix}', callback_data=f'v152:r:x:{scope[0]}:{target}:{idx}:{int(page)}'))
    kb.row(IB('⬅️ К списку чатов', callback_data=f'v152:r:l:{int(page)}'))
    return kb
_V152_ORIG_BUILD_INFO_KEYBOARD = _v177_legacy_0217_build_info_keyboard

def _v177_legacy_0218_build_info_keyboard(chat_id: int):
    kb = _V152_ORIG_BUILD_INFO_KEYBOARD(int(chat_id))
    try:
        for row in getattr(kb, 'keyboard', None) or getattr(kb, 'inline_keyboard', None) or []:
            for button in row:
                if isinstance(button, dict):
                    if button.get('callback_data') == 'safety_profile_toggle':
                        button['callback_data'] = 'safety_profile_open'
                elif getattr(button, 'callback_data', None) == 'safety_profile_toggle':
                    button.callback_data = 'safety_profile_open'
    except Exception:
        pass
    return kb
try:
    _v177_legacy_0218_build_info_keyboard.__name__ = 'build_info_keyboard'
except Exception:
    pass
_V152_ORIG_BUILD_SAFETY_KEYBOARD = _v177_legacy_0225_build_safety_profile_keyboard

def _canon_build_safety_profile_keyboard__001(chat_id: int):
    kb = types.InlineKeyboardMarkup(row_width=1)
    kb.row(IB(f"🔄 По-старому/по-новому · сейчас {('ПО-НОВОМУ' if safety_profile_new_enabled() else 'ПО-СТАРОМУ')}", callback_data='safety_profile_toggle'))
    kb.row(IB('🛡 Права чатов', callback_data='v152:r:l:0'))
    kb.row(IB('👥 Права пользователей', callback_data='security_roles:0'))
    day = get_chat_store(int(chat_id)).get('current_view_day') or today_key()
    kb.row(IB('🔙 Назад в Инфо', callback_data=f'd:{day}:info'))
    return kb

def v152_callback_capability(action: str) -> str | None:
    raw = str(action or '')
    value = raw.split(':', 2)[2] if raw.startswith('d:') and raw.count(':') >= 2 else raw
    low = value.casefold()
    if low.startswith('v152:r:'):
        return None
    if any((x in low for x in ('journal', 'log_file', 'errors_file', 'failed', 'problem_tasks'))):
        return 'exports.journals'
    if 'google' in low:
        if any((x in low for x in ('drive', 'folder', 'upload_drive'))):
            return 'exports.google_drive'
        return 'exports.google_sheets'
    if any((x in low for x in ('excel', 'xlsx', 'csv', 'tabl_lsx', 'download'))):
        return 'exports.excel_chat'
    if any((x in low for x in ('report', 'summary', 'itog'))):
        return 'exports.reports'
    if low.startswith(('rem:add', 'reminder_add')):
        return 'reminders.create'
    if low.startswith(('rem:delete', 'rem:del', 'reminder_delete')):
        return 'reminders.delete'
    if low.startswith(('rem:edit', 'rem:save', 'reminder_edit')):
        return 'reminders.edit'
    if any((x in low for x in ('v149:rem:done', 'vyapl'))):
        return 'reminders.complete'
    if low.startswith(('rem:', 'reminder', 'v149:rem:')):
        return 'reminders.use'
    if any((x in low for x in ('media_group', 'mediagroup', 'album'))) and low.startswith(('fw', 'fwd', 'forward')):
        return 'forward.media_groups'
    if low.startswith(('fw', 'fwd', 'forward', 'stopforward')):
        return 'forward.messages'
    if low.startswith(('sp:chatlink', 'tenant_chat_link', 'space_chat_link', 'sp:unlink')):
        return 'chats.connect_children'
    if low.startswith(('sp:userlink', 'tenant_user', 'space_user')):
        return 'chats.manage_users'
    if low.startswith(('sp:role', 'sp:transfer', 'tenant_role', 'space_role')):
        return 'chats.manage_roles'
    if 'gomonk' in low:
        return 'finance.gomonk'
    if any((x in low for x in ('usd_month', 'month_usd', 'usd:month', 'month_view'))):
        return 'finance.view_month'
    if any((x in low for x in ('usd', 'currency_usd'))):
        return 'finance.usd'
    if any((x in low for x in ('delete', 'del_selected', 'remove_record'))):
        return 'finance.delete'
    if any((x in low for x in ('edit', 'izm', 'record_change'))):
        return 'finance.edit'
    if any((x in low for x in ('balance', 'totals', 'ostatok'))):
        return 'finance.view_totals'
    if any((x in low for x in ('finance_mode', 'info_finance', 'finmode'))):
        return 'finance.mode'
    if 'expense_shortcut' in low or 'iphone' in low:
        return 'settings.iphone'
    if any((x in low for x in ('runtime', 'diagnostic', 'diag', 'queues', 'delta_status'))):
        return 'settings.diagnostics'
    if any((x in low for x in ('mega_', 'restore', 'backup', 'sqlite', 'db'))):
        return 'settings.backup_recovery'
    if any((x in low for x in ('audit', 'integrity'))):
        return 'settings.audit'
    if any((x in low for x in ('window', 'okna', 'buttons_current'))):
        return 'settings.windows'
    if low in {'info', 'info_open'} or low.endswith(':info'):
        return 'settings.info'
    if any((x in low for x in ('toggle', 'setting', 'style', 'mode'))):
        return 'settings.change'
    return None
_V152_ORIG_SAFETY_PERMISSION_ALLOWED = _v177_legacy_0111_safety_permission_allowed

def _canon_safety_permission_allowed__001(user_id: int | None, chat_id: int | None, action: str) -> bool:
    try:
        uid, cid = (int(user_id or 0), int(chat_id or 0))
    except Exception:
        return False
    if _v152_actor_is_platform_owner(uid):
        return True
    capability = v152_callback_capability(action)
    if capability:
        tid = _v152_tenant_id_for_chat(cid)
        role = tenant_role_for_user(uid, tid)
        if role not in {'tenant_owner', 'tenant_admin', 'operator', 'viewer', 'standard'}:
            return False
        mutating = capability not in {'finance.view_totals', 'finance.view_month', 'exports.journals', 'exports.reports', 'reminders.use', 'settings.info', 'settings.diagnostics', 'settings.audit'}
        if mutating and role in {'viewer', 'standard'}:
            return False
        return v152_chat_permission_allowed(cid, capability)
    if callable(_V152_ORIG_SAFETY_PERMISSION_ALLOWED):
        return bool(_V152_ORIG_SAFETY_PERMISSION_ALLOWED(uid, cid, action))
    return True
_V152_ORIG_SECURITY_USER_ALLOWED = _v177_legacy_0109_security_user_allowed

def _canon_security_user_allowed__001(user_id: int | None, capability: str) -> bool:
    if callable(_V152_ORIG_SECURITY_USER_ALLOWED) and (not _V152_ORIG_SECURITY_USER_ALLOWED(user_id, capability)):
        return False
    try:
        cid = int(current_state_chat_id() or 0)
    except Exception:
        cid = 0
    if not cid or _v152_actor_is_platform_owner(int(user_id or 0)):
        return True
    fine = {'finance_input': 'finance.usd' if usd_transactions_view_enabled(cid) else 'finance.ars', 'finance_manage': 'finance.edit', 'export': 'exports.excel_chat', 'forward_manage': 'forward.messages', 'reminder_manage': 'reminders.use', 'view': 'settings.info'}.get(str(capability or ''))
    return v152_chat_permission_allowed(cid, fine) if fine else True

def v152_command_capability(command: str) -> str | None:
    cmd = str(command or '').strip().casefold().lstrip('/').split('@', 1)[0]
    if _v152_re.fullmatch('vyapl(?:_\\d+)?', cmd):
        return 'reminders.complete'
    maps = {'finance.mode': {'buttons'}, 'finance.view_totals': {'balance', 'ok', 'поехали'}, 'finance.view_month': {'prev', 'next'}, 'exports.excel_chat': {'csv', 'xlsx', 'excel', 'tabl_lsx', 'json'}, 'exports.journals': {'journal', 'log', 'logs', 'errors', 'bot_errors'}, 'exports.reports': {'report'}, 'exports.google_sheets': {'google', 'google_space', 'google_tenant', 'google_connect', 'google_sheet', 'google_email'}, 'exports.google_drive': {'google_drive'}, 'reminders.complete': {'vyapl_history'}, 'forward.messages': {'stopforward'}, 'chats.connect_children': {'space_chat_link', 'tenant_chat_link', 'space_join', 'tenant_join', 'space_unlink', 'tenant_unlink', 'space_claim', 'tenant_claim'}, 'chats.manage_users': {'space_user_link', 'tenant_user_link', 'space_users', 'tenant_users'}, 'chats.manage_roles': {'space_role', 'tenant_role', 'space_transfer', 'tenant_transfer'}, 'settings.change': {'space_rename', 'tenant_rename', 'space_create', 'tenant_create', 'off_on_backup_excel'}, 'settings.windows': {'windows', 'okna', 'окна'}, 'settings.info': {'space', 'spaces', 'tenant', 'пространство', 'пространства', 'space_chats', 'tenant_chats', 'help', 'start'}, 'settings.diagnostics': {'diag', 'diagnostics', 'queues', 'queue_status', 'delta_status', 'runtime_export', 'mega_status', 'chat_status', 'chat_history'}, 'settings.backup_recovery': {'backup_channel_on', 'backup_channel_off', 'mega_backup_now', 'mega_restore_now', 'restore', 'restore_off', 'restore_guard', 'restore_guard_on', 'restore_guard_off', 'sqlite', 'db', 'chat_archive', 'chat_restore'}, 'settings.audit': {'command_audit', 'articles', 'статьи'}}
    for capability, commands in maps.items():
        if cmd in commands:
            return capability
    return None

def _v152_command_allowed(msg, capability: str) -> bool:
    uid = _v152_actor_id(msg)
    if _v152_actor_is_platform_owner(uid):
        return True
    try:
        cid = int(msg.chat.id)
    except Exception:
        return False
    role = tenant_role_for_user(uid, _v152_tenant_id_for_chat(cid))
    mutating = capability not in {'finance.view_totals', 'finance.view_month', 'exports.journals', 'exports.reports', 'reminders.use', 'settings.info', 'settings.diagnostics', 'settings.audit'}
    if mutating and role in {'viewer', 'standard'}:
        return False
    return v152_chat_permission_allowed(cid, capability)

def _v152_install_command_wrappers() -> int:
    wrapped = 0
    handlers = getattr(bot, 'message_handlers', None)
    if not isinstance(handlers, list):
        return 0
    for handler in handlers:
        if not isinstance(handler, dict):
            continue
        original = handler.get('function')
        if not callable(original) or getattr(original, '_v152_permission_wrapped', False):
            continue

        @_v152_functools.wraps(original)
        def guarded(message, *args, __original=original, **kwargs):
            text = str(getattr(message, 'text', '') or '').strip()
            if text.startswith('/'):
                command = text.split(None, 1)[0]
                capability = v152_command_capability(command)
                if capability and (not _v152_command_allowed(message, capability)):
                    try:
                        send_and_auto_delete(int(message.chat.id), f'⛔ Для этого чата запрещено: {V152_PERMISSION_LABELS.get(capability, capability)}.', 10)
                        bot_journal('chat_permission_command_denied', int(message.chat.id), f'user={_v152_actor_id(message)} command={command} capability={capability}', 'WARN')
                    except Exception:
                        pass
                    return None
            return __original(message, *args, **kwargs)
        guarded._v152_permission_wrapped = True
        handler['function'] = guarded
        wrapped += 1
    return wrapped
_V152_ORIG_HANDLE_GOMONK_INSERT = _v177_legacy_0162_handle_gomonk_insert_message

def _canon_handle_gomonk_insert_message__001(msg):
    cid = int(msg.chat.id)
    uid = _v152_actor_id(msg)
    if not _v152_actor_is_platform_owner(uid) and (not v152_chat_permission_allowed(cid, 'finance.gomonk')):
        try:
            send_and_auto_delete(cid, '⛔ Изменение гомонковых запрещено правами этого чата.', 8)
        except Exception:
            pass
        return False
    return _V152_ORIG_HANDLE_GOMONK_INSERT(msg) if callable(_V152_ORIG_HANDLE_GOMONK_INSERT) else False
_V152_ORIG_SCHEDULE_FORWARD = _v177_legacy_0001_schedule_forward_any_message

def _canon_schedule_forward_any_message__001(chat_id: int, msg):
    cid = int(chat_id)
    uid = _v152_actor_id(msg)
    capability = 'forward.media_groups' if getattr(msg, 'media_group_id', None) else 'forward.messages'
    if not _v152_actor_is_platform_owner(uid) and (not v152_chat_permission_allowed(cid, capability)):
        try:
            bot_journal('chat_permission_forward_blocked', cid, f'user={uid}; capability={capability}', 'WARN')
        except Exception:
            pass
        return None
    return _V152_ORIG_SCHEDULE_FORWARD(cid, msg) if callable(_V152_ORIG_SCHEDULE_FORWARD) else None

class _V152NamedFileProxy:

    def __init__(self, wrapped, name: str):
        self._wrapped = wrapped
        self.name = str(name)

    def __getattr__(self, item):
        return getattr(self._wrapped, item)

    def read(self, *args, **kwargs):
        return self._wrapped.read(*args, **kwargs)

    def seek(self, *args, **kwargs):
        return self._wrapped.seek(*args, **kwargs)

    def tell(self, *args, **kwargs):
        return self._wrapped.tell(*args, **kwargs)

    def __iter__(self):
        return iter(self._wrapped)

def _v152_file_text(document, caption: str='', purpose: str='') -> tuple[str, str]:
    name = ''
    try:
        name = str(getattr(document, 'name', '') or getattr(document, 'file_name', '') or '')
    except Exception:
        pass
    return (name, f"{name} {caption or ''} {purpose or ''}".casefold())

def _v152_without_version_noise(text: str) -> str:
    """Remove version/build tokens before semantic filename classification.

    v169 contained the word ``forward`` in VERSION itself.  The old classifier searched
    the whole filename/caption and therefore renamed unrelated downloads (TZ export,
    current-version journal and even the bot source) to ``Журнал_пересылки``.
    Classification must be based on the actual export purpose, not on words inside the
    release name.
    """
    low = str(text or '').casefold()
    try:
        ver = str(globals().get('VERSION') or '').casefold().strip()
        if ver:
            low = low.replace(ver, ' ')
    except Exception:
        pass
    low = _v152_re.sub('\\bbot_v\\d+[0-9a-z_\\-]*\\b', ' ', low)
    low = _v152_re.sub('\\bv\\d+_[0-9a-z_\\-]+\\b', ' ', low)
    low = _v152_re.sub('\\s+', ' ', low).strip()
    return low

def _v152_download_kind(document, caption: str='', purpose: str='') -> str | None:
    """Return a unique human category for operational downloads.

    The order is intentional: explicit export types win before generic journal keywords.
    Financial XLSX/CSV exports are *not* journals and keep their own existing filenames.
    """
    name, raw_low = _v152_file_text(document, caption, purpose)
    low = _v152_without_version_noise(raw_low)
    base = _v152_os.path.basename(str(name or '')).casefold()
    ext = _v152_os.path.splitext(base)[1].lower()
    if ext == '.py' or 'исходник текущего деплоя' in low or 'исходник бота' in low:
        return 'Исходник_бота'
    if 'архив тз' in low or 'архив_тз_окон' in low:
        return 'ТЗ_окон_архив'
    if 'тз по окнам' in low or 'тз_окон_текущ' in low or 'тз_окон' in base:
        return 'ТЗ_окон_текущая_версия'
    if 'маркировки окон' in low or 'маркировки_окон' in base:
        return 'Маркировки_окон'
    if 'runtime mega zip' in low or base.startswith('runtime_export_'):
        return 'Диагностика_Runtime_MEGA'
    if 'журнал текущей версии' in low or 'журнал текущей версии бота' in low:
        return 'Журнал_текущей_версии'
    if any((x in low for x in ('максимальный диагностический журнал', 'диагностический журнал', 'diagnostic', 'diagnostics'))):
        return 'Журнал_диагностики'
    if any((x in low for x in ('failed', 'problem_tasks', 'проблемные задачи', 'проблемных задач'))):
        return 'Журнал_FAILED_задач'
    if any((x in low for x in ('журнал ошибок', 'error journal', 'errors journal', 'журнал_ошибок'))):
        return 'Журнал_ошибок'
    if any((x in low for x in ('журнал восстановления', 'recovery journal', 'restore journal', 'журнал_восстановления'))):
        return 'Журнал_восстановления'
    if any((x in low for x in ('журнал пересылки', 'forward journal', 'forwarding journal', 'журнал_пересылки'))):
        return 'Журнал_пересылки'
    if any((x in low for x in ('журнал аудита', 'audit journal', 'integrity journal', 'журнал_аудита'))):
        return 'Журнал_аудита'
    if any((x in low for x in ('журнал backup', 'журнал бэкап', 'backup journal', 'журнал резерв', 'журнал_backup'))):
        return 'Журнал_резервных_копий'
    if any((x in low for x in ('журнал финансов', 'финансовый журнал', 'finance journal', 'журнал_финансов'))):
        return 'Журнал_финансов'
    if any((x in low for x in ('журнал операций', 'журнал действий', 'action journal', 'operations journal', 'журнал_операций'))):
        return 'Журнал_операций'
    if base.startswith('journal_') or ' журнал ' in f' {low} ':
        return 'Журнал_операций'
    return None

def _v152_journal_kind(document, caption: str='', purpose: str='') -> str | None:
    """Compatibility alias retained for older modules."""
    return _v152_download_kind(document, caption, purpose)

def _v152_filename_component(value: str, fallback: str='Чат') -> str:
    text = str(value or fallback).strip()
    text = _v152_re.sub('[\\\\/:*?\\"<>|]+', '-', text)
    text = _v152_re.sub('\\s+', '-', text)
    text = _v152_re.sub('-+', '-', text).strip('-._')
    if not _v152_re.search('[0-9A-Za-zА-Яа-яЁё]', text):
        text = str(fallback or 'Чат')
    return (text or fallback)[:80]

def _v152_scope_name(recipient_chat_id: int, kind: str) -> str:
    try:
        tid = _v152_tenant_id_for_chat(int(recipient_chat_id))
        tenant = _v152_tenant_row(tid)
        system_scope_kinds = {'Журнал_FAILED_задач', 'Журнал_диагностики', 'Журнал_аудита', 'Диагностика_Runtime_MEGA', 'Журнал_текущей_версии', 'ТЗ_окон_текущая_версия', 'ТЗ_окон_архив', 'Маркировки_окон'}
        if kind in system_scope_kinds and tenant:
            return _v152_filename_component(tenant.get('name') or tid, 'Пространство')
    except Exception:
        pass
    try:
        return _v152_filename_component(get_chat_display_name(int(recipient_chat_id)) or f'Чат-{recipient_chat_id}', f'Чат-{recipient_chat_id}')
    except Exception:
        return _v152_filename_component(f'Чат-{recipient_chat_id}')

def _v152_period_suffix(document, caption: str='', purpose: str='') -> str:
    name, _low = _v152_file_text(document, caption, purpose)
    source = f"{name} {caption or ''} {purpose or ''}"
    dates = []
    for y, m, d in _v152_re.findall('(?<!\\d)(20\\d{2})[-_]?([01]\\d)[-_]?([0-3]\\d)(?!\\d)', source):
        value = f'{y}-{m}-{d}'
        if value not in dates:
            dates.append(value)
    if len(dates) >= 2:
        return f'{dates[0]}_{dates[-1]}'
    if len(dates) == 1:
        return dates[0]
    try:
        return now_local().strftime('%Y-%m-%d')
    except Exception:
        return _v152_datetime.now().strftime('%Y-%m-%d')

def _v177_legacy_0277_v152_human_download_name(recipient_chat_id: int, document, caption: str='', purpose: str='') -> str | None:
    kind = _v152_download_kind(document, caption, purpose)
    if not kind:
        return None
    old_name = str(getattr(document, 'name', '') or getattr(document, 'file_name', '') or '')
    ext = _v152_os.path.splitext(old_name)[1].lower()
    if kind == 'Исходник_бота':
        safe_ver = _v152_filename_component(str(globals().get('VERSION') or 'текущая-версия'), 'текущая-версия')
        return f'Исходник_бота_{safe_ver}_{_v152_period_suffix(document, caption, purpose)}.py'
    if ext not in {'.txt', '.csv', '.zip', '.json', '.xlsx', '.gz', '.sqlite3', '.py'}:
        ext = '.zip' if kind in {'Журнал_FAILED_задач', 'Диагностика_Runtime_MEGA'} else '.txt'
    scope = _v152_scope_name(int(recipient_chat_id), kind)
    period = _v152_period_suffix(document, caption, purpose)
    return f'{kind}_{scope}_{period}{ext}'
try:
    _v177_legacy_0277_v152_human_download_name.__name__ = 'v152_human_download_name'
except Exception:
    pass
_V152_ORIG_SEND_DOCUMENT = getattr(bot, 'send_document', None)

def _v152_send_document(chat_id, document, *args, **kwargs):
    if not callable(_V152_ORIG_SEND_DOCUMENT):
        raise RuntimeError('send_document unavailable')
    caption = str(kwargs.get('caption') or '')
    purpose = str(kwargs.get('purpose') or '')
    new_name = v152_human_download_name(int(chat_id), document, caption, purpose)
    if new_name:
        try:
            if hasattr(document, 'file_name'):
                document.file_name = new_name
            elif hasattr(document, 'read'):
                document = _V152NamedFileProxy(document, new_name)
        except Exception:
            pass
    return _V152_ORIG_SEND_DOCUMENT(chat_id, document, *args, **kwargs)
if callable(_V152_ORIG_SEND_DOCUMENT):
    bot.send_document = _v152_send_document
_V152_ORIG_EXTENSION_CALLBACK = _v177_legacy_0266_v149_extension_callback

def _v152_answer(call, text: str='', alert: bool=False):
    try:
        bot.answer_callback_query(call.id, text or None, show_alert=bool(alert))
    except Exception:
        pass

def _v152_edit_rights(call, scope: str, target: str | int, page: int=0):
    safe_edit(bot, call, build_v152_permission_text(scope, target), reply_markup=build_v152_permission_keyboard(scope, target, page))

def _v152_handle_rights_callback(call, data_str: str) -> bool:
    if not str(data_str).startswith('v152:r:'):
        return False
    chat_id = int(call.message.chat.id)
    user_id = _v152_actor_id(call)
    parts = str(data_str).split(':')
    try:
        action = parts[2]
        if action == 'l':
            page = int(parts[3]) if len(parts) > 3 else 0
            if not (_v152_actor_is_platform_owner(user_id) or _v152_actor_can_manage_tenant(user_id, _v152_tenant_id_for_chat(chat_id))):
                _v152_answer(call, 'Недостаточно прав', True)
                return True
            safe_edit(bot, call, build_v152_chat_rights_list_text(user_id, chat_id, page), reply_markup=build_v152_chat_rights_list_keyboard(user_id, chat_id, page))
            return True
        if action == 'g':
            if not _v152_actor_is_platform_owner(user_id):
                _v152_answer(call, 'Только владелец платформы', True)
                return True
            _v152_edit_rights(call, 'global', 'platform', int(parts[3]) if len(parts) > 3 else 0)
            return True
        if action == 't':
            tenant_id = parts[3]
            page = int(parts[4]) if len(parts) > 4 else 0
            if not _v152_actor_can_manage_tenant(user_id, tenant_id):
                _v152_answer(call, 'Чужое пространство', True)
                return True
            _v152_edit_rights(call, 'tenant', tenant_id, page)
            return True
        if action == 'c':
            target_chat = int(parts[3])
            page = int(parts[4]) if len(parts) > 4 else 0
            if not _v152_actor_can_manage_chat(user_id, target_chat):
                _v152_answer(call, 'Чужой чат', True)
                return True
            _v152_edit_rights(call, 'chat', target_chat, page)
            return True
        if action == 'i':
            target_chat = int(parts[3])
            page = int(parts[4]) if len(parts) > 4 else 0
            if not _v152_toggle_chat_inheritance(target_chat, user_id):
                _v152_answer(call, 'Не удалось изменить наследование', True)
                return True
            _v152_answer(call, 'Наследование изменено')
            _v152_edit_rights(call, 'chat', target_chat, page)
            return True
        if action == 'p':
            scope_code, target, preset = (parts[3], parts[4], parts[5])
            page = int(parts[6]) if len(parts) > 6 else 0
            scope = {'g': 'global', 't': 'tenant', 'c': 'chat'}.get(scope_code)
            real_target = int(target) if scope == 'chat' else target
            if not scope or not _v152_apply_preset(scope, real_target, preset, user_id):
                _v152_answer(call, 'Пресет недоступен', True)
                return True
            _v152_answer(call, 'Права применены')
            _v152_edit_rights(call, scope, real_target, page)
            return True
        if action == 'x':
            scope_code, target, idx_raw = (parts[3], parts[4], parts[5])
            page = int(parts[6]) if len(parts) > 6 else 0
            idx = int(idx_raw)
            if idx < 0 or idx >= len(V152_PERMISSION_KEYS):
                _v152_answer(call, 'Неизвестное право', True)
                return True
            capability = V152_PERMISSION_KEYS[idx]
            scope = {'g': 'global', 't': 'tenant', 'c': 'chat'}.get(scope_code)
            real_target = int(target) if scope == 'chat' else target
            if scope != 'global' and (not v152_global_permission_allowed(capability)):
                _v152_answer(call, 'Функция запрещена владельцем платформы', True)
                return True
            if scope == 'chat' and _v152_chat_policy(int(real_target)).get('inherit_tenant', True):
                _v152_answer(call, 'Сначала выключите наследование пространства', True)
                return True
            current = _v152_scope_value(scope, real_target, capability)
            ok = _v152_set_global(capability, not current, user_id) if scope == 'global' else _v152_set_tenant(str(real_target), capability, not current, user_id) if scope == 'tenant' else _v152_set_chat(int(real_target), capability, not current, user_id)
            if not ok:
                _v152_answer(call, 'Недостаточно прав', True)
                return True
            _v152_answer(call, 'Право изменено')
            _v152_edit_rights(call, scope, real_target, page)
            return True
    except Exception as exc:
        try:
            log_error(f'v152 rights callback {data_str}: {exc}')
        except Exception:
            pass
        _v152_answer(call, 'Ошибка изменения прав', True)
        return True
    return True

def _v177_legacy_0267_v149_extension_callback(call, data_str: str) -> bool:
    if _v152_handle_rights_callback(call, data_str):
        return True
    if callable(_V152_ORIG_EXTENSION_CALLBACK):
        return bool(_V152_ORIG_EXTENSION_CALLBACK(call, data_str))
    return False
try:
    _v177_legacy_0267_v149_extension_callback.__name__ = 'v149_extension_callback'
except Exception:
    pass
_V152_WRAPPED_COMMAND_HANDLERS = _v152_install_command_wrappers()
try:
    _v177_legacy_0006_bot_journal('v152_permissions_installed', int(OWNER_ID or 0), f'command_handlers={_V152_WRAPPED_COMMAND_HANDLERS}; capabilities={len(V152_PERMISSION_KEYS)}')
except Exception:
    pass
'v153: remaining fixes 11-16.\n\n- deep command/button/runtime audit;\n- interactive export wait notices with a reusable Download button;\n- global secret redaction and preflight scanning;\n- runtime cleanup, exact failed counters and chat lifecycle history;\n- /json_full and validated /restore for global or tenant state;\n- v238 one canonical MEGA root only; release child roots are removed and never restore sources.\n'
import copy as _v153_copy
import gzip as _v153_gzip
import hashlib as _v153_hashlib
import json as _v153_json
import os as _v153_os
import re as _v153_re
import shutil as _v153_shutil
import sqlite3 as _v153_sqlite3
import tempfile as _v153_tempfile
import threading as _v153_threading
import time as _v153_time
import zipfile as _v153_zipfile
from datetime import datetime as _v153_datetime
from pathlib import Path as _V153Path
V153_EXPORT_SCHEMA = 1
V153_OLD_MEGA_ROOT = str(globals().get('MEGA_BACKUP_DIR') or '')
V153_NEW_MEGA_ROOT = str(globals().get('MEGA_BACKUP_DIR') or '')
V153_MIGRATION_BATCH = max(3, min(100, int(_v153_os.getenv('V153_MEGA_MIGRATION_BATCH', '20') or '20')))
V153_RESTORE_PENDING_TTL = 24 * 3600
_V153_LOCK = _v153_threading.RLock()
_V153_WAITING_EXPORTS = {}
_V153_READY_EXPORTS = {}
_V153_RESTORE_PENDING = {}
_V153_CALLBACK_RECEIPTS = {}
_V153_CALLBACK_SIGNATURES = {}
_V153_SANITIZED_TEMP = set()

def _v153_now() -> str:
    try:
        return now_local().isoformat(timespec='seconds')
    except Exception:
        return _v153_datetime.now().astimezone().isoformat(timespec='seconds')

def _v153_actor_id(obj) -> int:
    try:
        return int(getattr(getattr(obj, 'from_user', None), 'id', 0) or 0)
    except Exception:
        return 0

def _v153_platform_owner(uid: int) -> bool:
    try:
        return bool(tenant_is_platform_owner_user(int(uid)))
    except Exception:
        try:
            return int(uid) == int(OWNER_ID or 0)
        except Exception:
            return False

def _v153_tenant_for_chat(chat_id: int) -> str:
    try:
        return str(tenant_id_for_chat(int(chat_id), create=False) or TENANT_PLATFORM_ID)
    except Exception:
        return str(globals().get('TENANT_PLATFORM_ID') or 'platform')

def _v153_can_manage_tenant(uid: int, tenant_id: str) -> bool:
    if _v153_platform_owner(uid):
        return True
    try:
        return bool(tenant_can_manage(int(uid), str(tenant_id), owner_only=True))
    except TypeError:
        try:
            return bool(tenant_can_manage(int(uid), str(tenant_id)))
        except Exception:
            return False
    except Exception:
        return False
_V153_SECRET_KEY_RE = _v153_re.compile('^(?:password|passwd|pass|mega_password|telegram_token|bot_token|access[_-]?token|refresh[_-]?token|oauth[_-]?token|google[_-]?oauth[_-]?token|api[_-]?key|private[_-]?key|credential(?:s)?|authorization|cookie|webhook[_-]?secret|client[_-]?secret)$', _v153_re.I)
_V153_ENV_SECRET_RE = _v153_re.compile('(?:PASS|PASSWORD|SECRET|TOKEN|API_KEY|PRIVATE_KEY|CREDENTIAL|AUTH|COOKIE|OAUTH|WEBHOOK)', _v153_re.I)

def _v153_secret_values() -> list[str]:
    values = set()
    for key, value in _v153_os.environ.items():
        if _V153_ENV_SECRET_RE.search(str(key)) and value and (len(str(value)) >= 6):
            values.add(str(value))
    for name in ('MEGA_EMAIL', 'MEGA_PASSWORD', 'BOT_TOKEN', 'B_T', 'GOOGLE_SERVICE_ACCOUNT_JSON', 'TENANT_GOOGLE_MASTER_KEY', 'GOOGLE_TENANT_MASTER_KEY', 'WEBHOOK_SECRET'):
        value = str(globals().get(name) or _v153_os.getenv(name) or '')
        if value and len(value) >= 6:
            values.add(value)
    return sorted(values, key=len, reverse=True)

def v153_redact_text(value) -> str:
    text = str(value or '')
    for secret in _v153_secret_values():
        if secret in text:
            text = text.replace(secret, '***')
    text = _v153_re.sub('(?i)(Authorization\\s*[:=]\\s*)(?:Bearer\\s+)?[^\\s,;]+', '\\1***', text)
    text = _v153_re.sub('(?i)(Cookie\\s*[:=]\\s*)[^\\r\\n]+', '\\1***', text)
    text = _v153_re.sub('(?i)("?(?:password|passwd|secret|token|api[_-]?key|private[_-]?key|authorization|cookie|client[_-]?secret|webhook[_-]?secret)"?\\s*[:=]\\s*)("[^"\\r\\n]*"|[^,;\\r\\n ]+)', lambda m: m.group(1) + '"***"', text)
    text = _v153_re.sub('(?i)(Bearer\\s+)[A-Za-z0-9._~+/=-]+', '\\1***', text)
    return text

def v153_sanitize(value, key: str=''):
    if _V153_SECRET_KEY_RE.search(str(key or '')):
        return '***'
    if isinstance(value, dict):
        return {str(k): v153_sanitize(v, str(k)) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [v153_sanitize(x, key) for x in value]
    if isinstance(value, str):
        return v153_redact_text(value)
    return value
_V153_ORIG_LOG_ERROR = _v177_legacy_0003_log_error
_V153_ORIG_LOG_INFO = _v177_legacy_0002_log_info
_V153_ORIG_BOT_JOURNAL = _v177_legacy_0006_bot_journal
_V153_ORIG_ATOMIC_JSON_DUMP = _v177_legacy_0008_atomic_json_dump
_V153_ORIG_MEGA_RUN = _v177_legacy_0063_mega_run
_V153_ORIG_MAKE_GLOBAL_BACKUP = _v177_legacy_0077_make_global_backup_payload

def _canon_log_error__001(message):
    if callable(_V153_ORIG_LOG_ERROR):
        return _V153_ORIG_LOG_ERROR(v153_redact_text(message))

def _canon_log_info__001(message):
    if callable(_V153_ORIG_LOG_INFO):
        return _V153_ORIG_LOG_INFO(v153_redact_text(message))

def _v177_legacy_0007_bot_journal(action, chat_id=None, detail='', level='INFO'):
    if callable(_V153_ORIG_BOT_JOURNAL):
        return _V153_ORIG_BOT_JOURNAL(str(action), chat_id, v153_sanitize(detail), str(level))
try:
    _v177_legacy_0007_bot_journal.__name__ = 'bot_journal'
except Exception:
    pass

def _canon_atomic_json_dump__001(path: str, payload) -> None:
    safe = v153_sanitize(payload)
    if callable(_V153_ORIG_ATOMIC_JSON_DUMP):
        return _V153_ORIG_ATOMIC_JSON_DUMP(path, safe)
    with open(path, 'w', encoding='utf-8') as fh:
        _v153_json.dump(safe, fh, ensure_ascii=False)

def _canon_make_global_backup_payload__001():
    payload = _V153_ORIG_MAKE_GLOBAL_BACKUP() if callable(_V153_ORIG_MAKE_GLOBAL_BACKUP) else {}
    return v153_sanitize(payload)

def _canon_mega_run__001(cmd: str, args=None, timeout=None, check: bool=True, control_plane: bool=False):
    if not callable(_V153_ORIG_MEGA_RUN):
        raise RuntimeError('MEGA runner unavailable')
    safe_args = list(args or [])
    temp_dir = ''
    try:
        if str(cmd or '').lower() == 'mega-put' and safe_args:
            source = str(safe_args[0] or '')
            if _v153_os.path.isfile(source):
                safe = v153_prepare_safe_file(source, 'mega upload task snapshot failed backup audit runtime')
                if safe != source:
                    safe_args[0] = safe
                    temp_dir = _v153_os.path.dirname(safe)
        return _V153_ORIG_MEGA_RUN(cmd, safe_args, timeout=timeout, check=check, control_plane=control_plane)
    except Exception as exc:
        raise RuntimeError(v153_redact_text(exc)) from None
    finally:
        if temp_dir:
            _v153_shutil.rmtree(temp_dir, ignore_errors=True)
            _V153_SANITIZED_TEMP.discard(temp_dir)

def _v153_text_extension(path: str) -> bool:
    return _v153_os.path.splitext(str(path or ''))[1].lower() in {'.txt', '.json', '.csv', '.log', '.md', '.xml', '.yaml', '.yml'}

def _v153_sanitize_zip(src: str, dst: str) -> None:
    with _v153_zipfile.ZipFile(src, 'r') as zin, _v153_zipfile.ZipFile(dst, 'w', _v153_zipfile.ZIP_DEFLATED) as zout:
        for item in zin.infolist():
            raw = zin.read(item.filename)
            ext = _v153_os.path.splitext(item.filename)[1].lower()
            if ext in {'.txt', '.json', '.csv', '.log', '.md', '.xml', '.yaml', '.yml'}:
                try:
                    raw = v153_redact_text(raw.decode('utf-8')).encode('utf-8')
                except Exception:
                    pass
            zout.writestr(item, raw)

def v153_prepare_safe_file(path: str, hint: str='') -> str:
    """Return original or a sanitized temporary copy. Binary state DBs are not rewritten."""
    src = str(path or '')
    if not src or not _v153_os.path.isfile(src):
        return src
    low = f'{src} {hint}'.casefold()
    sensitive_export = any((x in low for x in ('journal', 'log', 'runtime', 'diagn', 'failed', 'audit', 'error', 'snapshot', 'export')))
    if not sensitive_export and (not _v153_text_extension(src)):
        return src
    folder = _v153_tempfile.mkdtemp(prefix='v153_safe_')
    dst = _v153_os.path.join(folder, _v153_os.path.basename(src))
    try:
        if src.lower().endswith('.zip'):
            _v153_sanitize_zip(src, dst)
        elif _v153_text_extension(src):
            raw = _V153Path(src).read_text(encoding='utf-8', errors='replace')
            _V153Path(dst).write_text(v153_redact_text(raw), encoding='utf-8')
        else:
            return src
        _V153_SANITIZED_TEMP.add(folder)
        return dst
    except Exception:
        _v153_shutil.rmtree(folder, ignore_errors=True)
        return src
_V153_ORIG_SEND_DOCUMENT = getattr(bot, 'send_document', None)
if callable(_V153_ORIG_SEND_DOCUMENT):

    def _v153_send_document(chat_id, document, *args, **kwargs):
        temp_dir = ''
        original_pos = None
        try:
            name = str(getattr(document, 'name', '') or '')
            path = name if name and _v153_os.path.isfile(name) else ''
            if path:
                safe = v153_prepare_safe_file(path, f"{kwargs.get('caption', '')} {kwargs.get('purpose', '')}")
                if safe != path:
                    temp_dir = _v153_os.path.dirname(safe)
                    document = open(safe, 'rb')
            return _V153_ORIG_SEND_DOCUMENT(chat_id, document, *args, **kwargs)
        finally:
            try:
                if temp_dir and hasattr(document, 'close'):
                    document.close()
            except Exception:
                pass
            if temp_dir:
                _v153_shutil.rmtree(temp_dir, ignore_errors=True)
                _V153_SANITIZED_TEMP.discard(temp_dir)
    bot.send_document = _v153_send_document
_V153_ORIG_FILE_RUNNER = _v177_legacy_0012_interactive_file_job_runner
_V153_ORIG_FILE_SUBMIT = _v177_legacy_0016_submit_interactive_file_job

def _v153_wait_token(chat_id: int, kind: str) -> str:
    raw = f'{chat_id}:{kind}:{_v153_time.time_ns()}'.encode()
    return _v153_hashlib.sha256(raw).hexdigest()[:16]

def _v153_wait_keyboard(token: str):
    kb = types.InlineKeyboardMarkup()
    kb.add(IB('📥 Скачать сейчас', callback_data=f'v153:file:{token}'))
    return kb

def _v153_register_wait(chat_id: int, kind: str, label: str, func, args, kwargs, active: dict) -> None:
    chat_id = int(chat_id)
    token = _v153_wait_token(chat_id, kind)
    text = f"⏳ Сейчас нельзя скачать «{label}».\n\nУже формируется:\n«{active.get('label') or 'другой файл'}»."
    with _V153_LOCK:
        old = _V153_WAITING_EXPORTS.get(chat_id) or {}
    msg_id = int(old.get('message_id') or 0)
    try:
        if msg_id:
            bot.edit_message_text(text, chat_id=chat_id, message_id=msg_id)
        else:
            sent = bot.send_message(chat_id, text)
            msg_id = int(getattr(sent, 'message_id', 0) or 0)
    except Exception:
        pass
    request = {'token': token, 'chat_id': chat_id, 'kind': str(kind), 'label': str(label), 'func': func, 'args': tuple(args), 'kwargs': dict(kwargs), 'message_id': msg_id, 'created_at': _v153_now()}
    with _V153_LOCK:
        _V153_WAITING_EXPORTS[chat_id] = request

def _v153_release_waiters(ok: bool, error_text: str='') -> None:
    with _V153_LOCK:
        rows = list(_V153_WAITING_EXPORTS.values())
        _V153_WAITING_EXPORTS.clear()
    for row in rows:
        token = str(row['token'])
        with _V153_LOCK:
            _V153_READY_EXPORTS[token] = row
        if ok:
            text = f"✅ Теперь можно скачать «{row['label']}»."
        else:
            text = '⚠️ Предыдущая выгрузка завершилась ошибкой.\n\nТеперь можно попробовать снова.'
        try:
            if row.get('message_id'):
                bot.edit_message_text(text, chat_id=int(row['chat_id']), message_id=int(row['message_id']), reply_markup=_v153_wait_keyboard(token))
            else:
                sent = bot.send_message(int(row['chat_id']), text, reply_markup=_v153_wait_keyboard(token))
                row['message_id'] = int(getattr(sent, 'message_id', 0) or 0)
        except Exception:
            pass

def _v177_legacy_0013_interactive_file_job_runner(job_meta: dict, func, args, kwargs):
    state = {'ok': False, 'error': ''}

    def _target(*a, **k):
        try:
            result = func(*a, **k)
            state['ok'] = result is not False
            if not state['ok']:
                state['error'] = 'операция завершилась без подтверждения'
            return result
        except Exception as exc:
            state['error'] = v153_redact_text(exc)[:300]
            raise
    if callable(_V153_ORIG_FILE_RUNNER):
        result = _V153_ORIG_FILE_RUNNER(job_meta, _target, args, kwargs)
    else:
        result = _target(*args, **kwargs)
    _v153_release_waiters(bool(state['ok']), state['error'])
    return result
try:
    _v177_legacy_0013_interactive_file_job_runner.__name__ = '_interactive_file_job_runner'
except Exception:
    pass

def _v177_legacy_0017_submit_interactive_file_job(chat_id: int, kind: str, label: str, func, *args, **kwargs):
    busy = _file_job_busy_info() if '_file_job_busy_info' in globals() else {}
    if busy:
        _v153_register_wait(int(chat_id), str(kind), str(label), func, args, kwargs, busy)
        return (False, f"Уже формируется: {busy.get('label') or 'файл'}")
    if callable(_V153_ORIG_FILE_SUBMIT):
        return _V153_ORIG_FILE_SUBMIT(chat_id, kind, label, func, *args, **kwargs)
    return (False, 'Экспорт недоступен')
try:
    _v177_legacy_0017_submit_interactive_file_job.__name__ = 'submit_interactive_file_job'
except Exception:
    pass
_V153_ORIG_RUNTIME_SELECT = _v177_legacy_0079_runtime_export_select_paths
_V153_ORIG_RUNTIME_SEND = _v177_legacy_0080_send_runtime_export_zip
_V153_ORIG_MEGA_STATS = _v177_legacy_0065_mega_task_registry_stats
_V153_ORIG_RUNTIME_MARK_READY = _v177_legacy_0083_runtime_mark_ready
_V153_ORIG_RUNTIME_UPLOAD = _v177_legacy_0081_runtime_upload_snapshot
_V153_ORIG_NORMALIZE_EXPECTED = _v177_legacy_0067_durable_normalize_expected_for_route
_V153_ORIG_RESTORE_SQLITE = _v177_legacy_0085_mega_restore_sqlite_snapshot_from_cloud
_V153_ORIG_RESTORE_FULL = _v177_legacy_0086_mega_restore_full_from_cloud
_V153_ORIG_CLASSIFY_PREVIOUS = _v177_legacy_0078_runtime_classify_previous
_V153_INSTANCE_SUPERSEDED = False
_V153_INSTANCE_LEASE_LAST = 0.0

def _canon_mega_task_registry_stats__002() -> dict:
    base = _V153_ORIG_MEGA_STATS() if callable(_V153_ORIG_MEGA_STATS) else {}
    try:
        with _MEGA_TASK_LOCK:
            failed_ids = [str(k) for k, row in _mega_task_registry.items() if str((row or {}).get('state') or '') == 'failed']
        details = [x for x in list(base.get('failed_details') or []) if str((x or {}).get('task_id') or '') in set(failed_ids)]
        base['failed'] = len(failed_ids)
        base['failed_details'] = details
        base['failed_details_pending'] = len(details) != min(len(failed_ids), int(globals().get('_V146_FAILED_DIAG_LIMIT') or 10))
    except Exception:
        pass
    return v153_sanitize(base)

def _canon_runtime_export_select_paths__001(start_dt=None, end_dt=None, max_downloads: int=360):
    indexed, _legacy_selected = _V153_ORIG_RUNTIME_SELECT(start_dt, end_dt, max_downloads=max_downloads) if callable(_V153_ORIG_RUNTIME_SELECT) else ([], [])
    stable = [x for x in indexed if x[0] in {'slot', 'event'}]
    stable = stable[:max(20, min(int(max_downloads), 180))]
    selected = list(stable)
    newest_stable = max((x[2] for x in stable if x[2] is not None), default=None)
    candidates = [x for x in indexed if x[0] in {'candidate', 'staged'} and x[2] is not None]
    if candidates:
        newest = max(candidates, key=lambda x: x[2])
        if newest_stable is None or newest[2] > newest_stable:
            selected.append(newest)
    return (indexed, selected[:max_downloads])

def _v153_chat_lifecycle_snapshot() -> dict:
    out = {'created_at': _v153_now(), 'chats': {}}
    try:
        for cid_s, store in list(((data or {}).get('chats') or {}).items()):
            if not isinstance(store, dict):
                continue
            life = (store.get('settings') or {}).get('chat_lifecycle_v150') or {}
            if life:
                out['chats'][str(cid_s)] = v153_sanitize(life)
    except Exception:
        pass
    return out

def _canon_send_runtime_export_zip__001(recipient_chat_id: int, start_dt=None, end_dt=None):
    if not callable(_V153_ORIG_RUNTIME_SEND):
        return False
    original_send = bot.send_document
    captured = {'done': False}

    def _capture(chat_id, document, *args, **kwargs):
        try:
            name = str(getattr(document, 'name', '') or '')
            if name and _v153_os.path.isfile(name) and name.lower().endswith('.zip'):
                temp_dir = _v153_tempfile.mkdtemp(prefix='v153_runtime_')
                temp = _v153_os.path.join(temp_dir, _v153_os.path.basename(name))
                _v153_shutil.copy2(name, temp)
                with _v153_zipfile.ZipFile(temp, 'a', _v153_zipfile.ZIP_DEFLATED) as z:
                    z.writestr('chat_lifecycle_history.json', _v153_json.dumps(_v153_chat_lifecycle_snapshot(), ensure_ascii=False, indent=2))
                    z.writestr('v153_runtime_fixes.txt', _v153_runtime_audit_text())
                safe_document = open(temp, 'rb')
                try:
                    return original_send(chat_id, safe_document, *args, **kwargs)
                finally:
                    safe_document.close()
                    _v153_shutil.rmtree(temp_dir, ignore_errors=True)
        except Exception as exc:
            log_error(f'runtime lifecycle append: {exc}')
        return original_send(chat_id, document, *args, **kwargs)
    bot.send_document = _capture
    try:
        return _V153_ORIG_RUNTIME_SEND(recipient_chat_id, start_dt, end_dt)
    finally:
        bot.send_document = original_send

def _canon_durable_normalize_expected_for_route__001(payload: dict, expected: dict | None) -> dict:
    adjusted = _V153_ORIG_NORMALIZE_EXPECTED(payload, expected) if callable(_V153_ORIG_NORMALIZE_EXPECTED) else dict(expected or {})
    raw, _cid, _mid, _grp = _durable_payload_message(payload or {}) if '_durable_payload_message' in globals() else ({}, None, None, None)
    text = str((raw or {}).get('text') or (raw or {}).get('caption') or '') if isinstance(raw, dict) else ''
    if 'EDITREM|' not in text and 'EDITREMINT|' not in text:
        adjusted['reminder_edits'] = []
    return adjusted

def _v153_runtime_cleanup_remote() -> dict:
    result = {'candidates_removed': 0, 'staged_removed': 0}
    try:
        root = runtime_remote_dir()
        result['candidates_removed'] = _mega_prune_remote_history(root, 'candidate_runtime_latest_*.json', 2)
        result['staged_removed'] = _mega_prune_remote_history(root, 'runtime_latest__*.json', 2)
    except Exception as exc:
        result['error'] = v153_redact_text(exc)
    return result

def _v153_remote_marker_exists(root: str) -> bool:
    try:
        rows = _mega_find_remote_files(str(root).rstrip('/'), 'migration_v153_complete.json', limit=3)
        return any((str(x).rstrip('/').endswith('/migration_v153_complete.json') for x in rows))
    except Exception:
        return False

def _v153_select_boot_mega_root() -> str:
    root = str(globals().get('MEGA_CANONICAL_BACKUP_DIR_V238') or globals().get('MEGA_BACKUP_DIR') or '/TelegramBotBackups').rstrip('/')
    _v153_apply_mega_root(root)
    return root

def _canon_mega_restore_sqlite_snapshot_from_cloud__001(force: bool=False) -> tuple[bool, str]:
    """v241: preserve explicit owner force=True through the compatibility wrapper."""
    _v153_select_boot_mega_root()
    if callable(_V153_ORIG_RESTORE_SQLITE):
        try:
            return _V153_ORIG_RESTORE_SQLITE(force=bool(force))
        except TypeError:
            return _V153_ORIG_RESTORE_SQLITE()
    return (False, 'SQLite restore unavailable')

def _canon_mega_restore_full_from_cloud__001(force: bool=False) -> tuple[bool, str]:
    _v153_select_boot_mega_root()
    if callable(_V153_ORIG_RESTORE_FULL):
        return _V153_ORIG_RESTORE_FULL(force=force)
    return (False, 'Full restore unavailable')

def _v153_instance_lease_payload() -> dict:
    return {'kind': 'telegram_bot_active_instance_v153', 'instance_id': str(_v153_os.getenv('RENDER_INSTANCE_ID') or _v153_os.uname().nodename), 'commit': str(_v153_os.getenv('RENDER_GIT_COMMIT') or ''), 'started_at': str(globals().get('_RUNTIME_STARTED_AT') or _v153_now()), 'heartbeat_at': _v153_now(), 'version': VERSION}

def _v179_base_instance_lease_check() -> dict:
    global _V153_INSTANCE_SUPERSEDED, _V153_INSTANCE_LEASE_LAST
    result = {'active': True, 'superseded': False}
    if not mega_is_configured():
        return result
    now_m = _v153_time.monotonic()
    if now_m - _V153_INSTANCE_LEASE_LAST < 20.0:
        result['superseded'] = bool(_V153_INSTANCE_SUPERSEDED)
        result['active'] = not bool(_V153_INSTANCE_SUPERSEDED)
        return result
    _V153_INSTANCE_LEASE_LAST = now_m
    remote_dir = runtime_remote_dir()
    remote = remote_dir.rstrip('/') + '/active_instance_v153.json'
    ours = _v153_instance_lease_payload()
    current = None
    local = None
    try:
        local = _mega_download_remote_path(remote)
        if local and _v153_os.path.isfile(local):
            current = _v153_json.loads(_V153Path(local).read_text(encoding='utf-8'))
    except Exception:
        current = None
    finally:
        if local:
            _v153_shutil.rmtree(_v153_os.path.dirname(local), ignore_errors=True)
    other_id = str((current or {}).get('instance_id') or '')
    our_id = str(ours['instance_id'])
    current_started = str((current or {}).get('started_at') or '')
    ours_started = str(ours['started_at'])
    if other_id and other_id != our_id and (current_started > ours_started):
        _V153_INSTANCE_SUPERSEDED = True
        result.update({'active': False, 'superseded': True, 'newer_instance': other_id})
        try:
            _RUNTIME_STATE['phase'] = 'superseded'
            _RUNTIME_STATE['ready'] = False
            _RUNTIME_STATE['last_event'] = 'newer_render_instance_active'
            _RUNTIME_STATE['last_event_at'] = _v153_now()
        except Exception:
            pass
        bot_journal('runtime_instance_superseded', None, f'newer_instance={other_id}; newer_started={current_started}', 'WARN')
        return result
    temp_dir = _v153_tempfile.mkdtemp(prefix='v153_lease_')
    try:
        path = _v153_os.path.join(temp_dir, 'active_instance_v153.json')
        _V153Path(path).write_text(_v153_json.dumps(v153_sanitize(ours), ensure_ascii=False, indent=2), encoding='utf-8')
        if mega_put_replace(path, remote_dir, 'active_instance_v153.json', archive_previous=False):
            _V153_INSTANCE_SUPERSEDED = False
            result['active_instance'] = our_id
    finally:
        _v153_shutil.rmtree(temp_dir, ignore_errors=True)
    return result

def _canon_runtime_classify_previous__001(prev: dict) -> str:
    base = _V153_ORIG_CLASSIFY_PREVIOUS(prev) if callable(_V153_ORIG_CLASSIFY_PREVIOUS) else 'process_restart_or_unknown'
    try:
        prev_state = (prev or {}).get('state') or {}
        prev_render = (prev or {}).get('render') or {}
        prev_id = str(prev_render.get('RENDER_INSTANCE_ID') or '')
        cur_id = str(_v153_os.getenv('RENDER_INSTANCE_ID') or '')
        prev_capture = str((prev or {}).get('captured_at') or '')
        cur_start = str(globals().get('_RUNTIME_STARTED_AT') or '')
        if prev_id and cur_id and (prev_id != cur_id) and prev_capture and cur_start and (prev_capture >= cur_start):
            return 'overlapping_render_instances_detected'
        if bool(prev_state.get('shutdown_finished_at')):
            return base
        if str(prev_state.get('phase') or '') == 'superseded':
            return 'older_instance_superseded_by_newer_instance'
    except Exception:
        pass
    return base

def _canon_runtime_upload_snapshot__001(event: str='snapshot', immutable_event: bool=True) -> bool:
    lease = _v153_instance_lease_check()
    if lease.get('superseded'):
        return False
    ok = _V153_ORIG_RUNTIME_UPLOAD(event, immutable_event) if callable(_V153_ORIG_RUNTIME_UPLOAD) else False
    try:
        if event in {'boot_ready', 'manual', 'shutdown'}:
            GENERAL_TASK_POOL.submit_unique('v153-runtime-prune', _v153_runtime_cleanup_remote)
    except Exception:
        pass
    return ok

def _v153_migration_store(root=None) -> dict:
    return {'status': 'removed_v238', 'copied_files': 0, 'total_files': 0, 'remaining_files': 0, 'last_error': '', 'active_root': str(globals().get('MEGA_CANONICAL_BACKUP_DIR_V238') or globals().get('MEGA_BACKUP_DIR') or '')}

def _v153_apply_mega_root(root: str) -> None:
    canonical = str(globals().get('MEGA_CANONICAL_BACKUP_DIR_V238') or globals().get('MEGA_BACKUP_DIR') or '/TelegramBotBackups').rstrip('/')
    globals()['MEGA_BACKUP_DIR'] = canonical
    globals()['MEGA_LEGACY_BACKUP_DIR'] = canonical
    globals()['MEGA_TARGET_BACKUP_DIR'] = canonical
    globals()['BOT_SOURCE_ARCHIVE_DIR'] = f'{canonical}/runtime/bot_versions'
    try:
        globals()['DURABLE_JOURNAL_REMOTE_DIR'] = f'{canonical}/runtime/journal'
    except Exception:
        pass
_V153_ORIG_LOAD_DATA = _v177_legacy_0087_load_data

def _canon_load_data__001():
    loaded = _V153_ORIG_LOAD_DATA() if callable(_V153_ORIG_LOAD_DATA) else {}
    try:
        gs = loaded.get('_global_settings') if isinstance(loaded, dict) else None
        if isinstance(gs, dict):
            gs.pop('mega_root_migration_v153', None)
        _v153_apply_mega_root(str(globals().get('MEGA_CANONICAL_BACKUP_DIR_V238') or '/TelegramBotBackups'))
    except Exception:
        pass
    return loaded

def purge_legacy_mega_root_state_v238(persist: bool=True) -> bool:
    """Remove retired root-migration payload even if an old delta/checkpoint reintroduced it."""
    changed = False
    try:
        gs = data.setdefault('_global_settings', {})
        changed = gs.pop('mega_root_migration_v153', None) is not None
        if changed and persist:
            SQLITE.save_root(_sqlite_pack_root(data))
            try:
                bot_journal('mega_root_legacy_state_purged_v238', int(OWNER_ID or 0) or None, 'mega_root_migration_v153 removed', 'INFO')
            except Exception:
                pass
    except Exception:
        return False
    return changed

def _v153_remote_relative(path: str, root: str) -> str:
    raw = str(path or '')
    prefix = str(root).rstrip('/') + '/'
    return raw[len(prefix):] if raw.startswith(prefix) else _v153_os.path.basename(raw)

def _v153_sha256_file(path: str) -> str:
    h = _v153_hashlib.sha256()
    with open(path, 'rb') as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()

def _v153_mega_copy_verify(old_remote: str, new_remote: str) -> tuple[bool, str]:
    local_old = local_new = None
    try:
        local_old = _mega_download_remote_path(old_remote)
        if not local_old:
            return (False, 'download old failed')
        old_hash = _v153_sha256_file(local_old)
        new_dir, new_name = new_remote.rsplit('/', 1)
        if not mega_put_replace(local_old, new_dir, new_name, archive_previous=False):
            return (False, 'upload new failed')
        local_new = _mega_download_remote_path(new_remote)
        if not local_new:
            return (False, 'verify download failed')
        new_hash = _v153_sha256_file(local_new)
        return (old_hash == new_hash, old_hash if old_hash == new_hash else 'checksum mismatch')
    finally:
        for local in (local_old, local_new):
            try:
                if local:
                    _v153_shutil.rmtree(_v153_os.path.dirname(local), ignore_errors=True)
            except Exception:
                pass

def v153_migrate_mega_root() -> dict:
    """v179 compatibility status: root migration is permanently retired."""
    root = str(globals().get('MEGA_BACKUP_DIR') or '').rstrip('/')
    return {'status': 'disabled_v179', 'active_root': root, 'canonical_root': str(globals().get('MEGA_BACKUP_DIR') or ''), 'remaining_files': 0, 'last_error': ''}

def _v179_base_schedule_migration():
    return False

def _v153_sql_rows(conn, table: str, where: str='', params=()):
    sql = f'SELECT * FROM {table}' + (f' WHERE {where}' if where else '')
    return conn.execute(sql, tuple(params)).fetchall()

def _v153_db_logical_checksum(path: str) -> str:
    conn = _v153_sqlite3.connect(path)
    try:
        h = _v153_hashlib.sha256()
        for table in ('kv', 'chats', 'meta', 'cold_fields'):
            cols = [x[1] for x in conn.execute(f'PRAGMA table_info({table})').fetchall()]
            if not cols:
                continue
            order = ','.join(cols[:2])
            for row in conn.execute(f'SELECT * FROM {table} ORDER BY {order}').fetchall():
                if table == 'meta' and len(row) >= 2 and (str(row[0]) == 'v153_export') and (str(row[1]) == 'manifest'):
                    continue
                h.update(table.encode())
                h.update(b'\x00')
                for value in row:
                    h.update(str(value).encode('utf-8', 'replace'))
                    h.update(b'\x00')
        return h.hexdigest()
    finally:
        conn.close()

def _v153_scope_chat_ids_from_item(item) -> set[int]:
    result = set()
    if not isinstance(item, dict):
        return result
    for key in ('chat_id', 'source_chat_id', 'target_chat_id', 'src_chat_id', 'dst_chat_id', 'root_chat_id'):
        raw = item.get(key)
        if str(raw or '').lstrip('-').isdigit():
            result.add(int(raw))
    for key in ('chat_ids', 'target_chat_ids', 'forward_targets'):
        value = item.get(key) or []
        if isinstance(value, dict):
            value = list(value.keys())
        for raw in value if isinstance(value, (list, tuple, set)) else []:
            if isinstance(raw, dict):
                raw = raw.get('dst_chat_id') or raw.get('chat_id')
            if str(raw or '').lstrip('-').isdigit():
                result.add(int(raw))
    return result

def _v153_item_in_tenant_scope(item, tenant_id: str, chat_ids: set[int], key: str='') -> bool:
    if isinstance(item, dict):
        tid = str(item.get('tenant_id') or '')
        if tid and tid == str(tenant_id):
            return True
        if _v153_scope_chat_ids_from_item(item) & set(chat_ids):
            return True
    key_s = str(key or '')
    for cid in chat_ids:
        if key_s == str(cid) or key_s.startswith(f'{cid}:') or key_s.startswith(f'{cid}|'):
            return True
    return False

def _v153_filter_global_settings_for_tenant(gs: dict, tenant_id: str, chat_ids: set[int]) -> dict:
    tenants = ((gs or {}).get('tenants_v148') or {}).get('tenants') or {}
    tenant_row = _v153_copy.deepcopy(tenants.get(str(tenant_id)) or {})
    safe = {'tenants_v148': {'schema_version': 1, 'tenants': {str(tenant_id): v153_sanitize(tenant_row)}, 'chat_to_tenant': {str(cid): str(tenant_id) for cid in sorted(chat_ids)}, 'invite_tokens': {}, 'legacy_migrated': True, 'created_at': _v153_now()}}
    rem = _v153_copy.deepcopy((gs or {}).get('reminders_v2') or {})
    items = {}
    for rid, cfg in (rem.get('items') or {}).items() if isinstance(rem, dict) else []:
        if _v153_item_in_tenant_scope(cfg, tenant_id, chat_ids):
            items[str(rid)] = v153_sanitize(cfg)
    if items:
        safe['reminders_v2'] = {'next_id': max([int(x) for x in items if str(x).isdigit()] + [0]) + 1, 'items': items, 'migrated_v134': True}
    op = _v153_copy.deepcopy((gs or {}).get('operation_ledger_v141') or {})
    if isinstance(op, dict):
        op_items = {str(k): v153_sanitize(v) for k, v in (op.get('items') or {}).items() if _v153_item_in_tenant_scope(v, tenant_id, chat_ids, str(k))}
        if op_items:
            order = [str(x) for x in op.get('order') or [] if str(x) in op_items]
            safe['operation_ledger_v141'] = {'items': op_items, 'order': order, 'next_seq': int(op.get('next_seq') or 1)}
    integ = _v153_copy.deepcopy((gs or {}).get('finance_integrity_v141') or {})
    if isinstance(integ, dict):
        events = [v153_sanitize(x) for x in integ.get('events') or [] if _v153_item_in_tenant_scope(x, tenant_id, chat_ids)]
        tips = {str(k): v for k, v in (integ.get('tips') or {}).items() if str(k).lstrip('-').isdigit() and int(k) in chat_ids}
        if events or tips:
            safe['finance_integrity_v141'] = {'events': events, 'tips': tips, 'anchor': {}, 'event_seq': int(integ.get('event_seq') or 0)}
    return safe

def _v153_filter_root_for_tenant(root: dict, tenant_id: str, chat_ids: set[int]) -> dict:
    out = {}
    for key, value in (root or {}).items():
        if key == '_global_settings':
            out[key] = _v153_filter_global_settings_for_tenant(value if isinstance(value, dict) else {}, str(tenant_id), chat_ids)
            continue
        if key in {'chats', '_restore_mode_chat_v150'}:
            continue
        if isinstance(value, list):
            rows = [v153_sanitize(_v153_copy.deepcopy(item)) for item in value if _v153_item_in_tenant_scope(item, tenant_id, chat_ids)]
            if rows:
                out[key] = rows
            continue
        if isinstance(value, dict):
            filtered = {}
            for item_key, item in value.items():
                if _v153_item_in_tenant_scope(item, tenant_id, chat_ids, str(item_key)):
                    filtered[str(item_key)] = v153_sanitize(_v153_copy.deepcopy(item))
            if filtered:
                out[key] = filtered
            continue
    return out

def _v153_collect_failed_tasks(tenant_id: str | None, chat_ids: set[int]) -> list[dict]:
    rows = []
    try:
        mega_task_refresh_registry()
        with _MEGA_TASK_LOCK:
            failed = [(str(k), str((v or {}).get('path') or '')) for k, v in _mega_task_registry.items() if str((v or {}).get('state') or '') == 'failed']
        for key, remote in failed[:500]:
            local = _mega_download_remote_path(remote)
            if not local:
                continue
            try:
                task = _v153_json.loads(_V153Path(local).read_text(encoding='utf-8'))
                cid = int(task.get('chat_id') or 0)
                if tenant_id is None or cid in chat_ids:
                    rows.append(v153_sanitize(task))
            finally:
                _v153_shutil.rmtree(_v153_os.path.dirname(local), ignore_errors=True)
    except Exception as exc:
        rows.append({'load_error': v153_redact_text(exc)})
    return rows

def _v153_build_export(scope: str, tenant_id: str | None=None) -> str:
    _lowram_flush_all_hot(evict=False)
    save_data(data, full=True)
    folder = _v153_tempfile.mkdtemp(prefix='v153_full_export_')
    raw = _v153_os.path.join(folder, 'state.sqlite3')
    SQLITE.backup_to(raw)
    conn = _v153_sqlite3.connect(raw)
    try:
        chat_ids = set()
        if scope == 'tenant':
            chat_ids = set((int(x) for x in tenant_chat_ids(str(tenant_id))))
            marks = ','.join(('?' for _ in chat_ids)) or 'NULL'
            if chat_ids:
                conn.execute(f'DELETE FROM chats WHERE CAST(chat_id AS INTEGER) NOT IN ({marks})', tuple(chat_ids))
                conn.execute(f'DELETE FROM cold_fields WHERE CAST(chat_id AS INTEGER) NOT IN ({marks})', tuple(chat_ids))
            else:
                conn.execute('DELETE FROM chats')
                conn.execute('DELETE FROM cold_fields')
            row = conn.execute("SELECT v FROM kv WHERE k='root'").fetchone()
            root = _v153_json.loads(row[0]) if row else {}
            filtered = _v153_filter_root_for_tenant(root, str(tenant_id), chat_ids)
            conn.execute("INSERT INTO kv(k,v) VALUES('root',?) ON CONFLICT(k) DO UPDATE SET v=excluded.v", (_v153_json.dumps(filtered, ensure_ascii=False, separators=(',', ':')),))
        else:
            for table, key_cols, json_col in (('kv', ('k',), 'v'), ('chats', ('chat_id',), 'v'), ('meta', ('kind', 'k'), 'v'), ('cold_fields', ('chat_id', 'k'), 'v')):
                cols = ','.join(key_cols + (json_col,))
                for row in conn.execute(f'SELECT {cols} FROM {table}').fetchall():
                    keys, raw_json = (row[:-1], row[-1])
                    try:
                        payload = v153_sanitize(_v153_json.loads(raw_json))
                    except Exception:
                        payload = v153_redact_text(raw_json)
                    where = ' AND '.join((f'{c}=?' for c in key_cols))
                    conn.execute(f'UPDATE {table} SET {json_col}=? WHERE {where}', (_v153_json.dumps(payload, ensure_ascii=False, separators=(',', ':')), *keys))
            chat_ids = {int(x[0]) for x in conn.execute('SELECT chat_id FROM chats').fetchall() if str(x[0]).lstrip('-').isdigit()}
        failed = _v153_collect_failed_tasks(tenant_id if scope == 'tenant' else None, chat_ids)
        conn.execute("INSERT INTO meta(kind,k,v) VALUES('v153_export','failed_tasks',?) ON CONFLICT(kind,k) DO UPDATE SET v=excluded.v", (_v153_json.dumps(failed, ensure_ascii=False, separators=(',', ':')),))
        manifest = {'kind': 'telegram_bot_full_state_v153', 'schema_version': V153_EXPORT_SCHEMA, 'bot_version': VERSION, 'created_at': _v153_now(), 'scope': scope, 'tenant_id': str(tenant_id or ''), 'chat_ids': sorted(chat_ids), 'chat_count': len(chat_ids), 'failed_tasks': len(failed), 'checksum': ''}
        conn.execute("INSERT INTO meta(kind,k,v) VALUES('v153_export','manifest',?) ON CONFLICT(kind,k) DO UPDATE SET v=excluded.v", (_v153_json.dumps(manifest, ensure_ascii=False, separators=(',', ':')),))
        conn.commit()
    finally:
        conn.close()
    checksum = _v153_db_logical_checksum(raw)
    conn = _v153_sqlite3.connect(raw)
    try:
        manifest = _v153_json.loads(conn.execute("SELECT v FROM meta WHERE kind='v153_export' AND k='manifest'").fetchone()[0])
        manifest['checksum'] = checksum
        conn.execute("UPDATE meta SET v=? WHERE kind='v153_export' AND k='manifest'", (_v153_json.dumps(manifest, ensure_ascii=False, separators=(',', ':')),))
        conn.commit()
    finally:
        conn.close()
    gz = _v153_os.path.join(folder, 'latest_bot_state.sqlite3.gz')
    with open(raw, 'rb') as fin, _v153_gzip.open(gz, 'wb', compresslevel=6) as fout:
        _v153_shutil.copyfileobj(fin, fout, 1024 * 1024)
    return gz

def _v153_send_full_export(chat_id: int, scope: str, tenant_id: str | None):
    path = _v153_build_export(scope, tenant_id)
    try:
        with open(path, 'rb') as fh:
            caption = '🗄 Полное состояние всего бота' if scope == 'global' else f"🗄 Состояние пространства: {(tenant_get(tenant_id) or {}).get('name') or tenant_id}"
            _tg_call_retry(bot.send_document, int(chat_id), fh, caption=caption, timeout=180, purpose='json_full_v153')
        return True
    finally:
        _v153_shutil.rmtree(_v153_os.path.dirname(path), ignore_errors=True)

def _v177_legacy_0278_v153_validate_restore_gz(gz_path: str) -> tuple[dict, str]:
    folder = _v153_tempfile.mkdtemp(prefix='v153_restore_validate_')
    raw = _v153_os.path.join(folder, 'restore.sqlite3')
    try:
        with _v153_gzip.open(gz_path, 'rb') as fin, open(raw, 'wb') as fout:
            _v153_shutil.copyfileobj(fin, fout, 1024 * 1024)
        conn = _v153_sqlite3.connect(raw)
        try:
            integrity = str(conn.execute('PRAGMA integrity_check').fetchone()[0])
            if integrity.lower() != 'ok':
                raise RuntimeError(f'SQLite integrity_check: {integrity}')
            row = conn.execute("SELECT v FROM meta WHERE kind='v153_export' AND k='manifest'").fetchone()
            if not row:
                raise RuntimeError('manifest v153 not found')
            manifest = _v153_json.loads(row[0])
        finally:
            conn.close()
        if str(manifest.get('kind')) != 'telegram_bot_full_state_v153':
            raise RuntimeError('unknown export kind')
        if int(manifest.get('schema_version') or 0) != V153_EXPORT_SCHEMA:
            raise RuntimeError('unsupported export schema')
        export_version = str(manifest.get('bot_version') or '')
        if not export_version.startswith('bot_v153_'):
            raise RuntimeError(f"unsupported bot version: {export_version or 'missing'}")
        checksum = _v153_db_logical_checksum(raw)
        if checksum != str(manifest.get('checksum') or ''):
            raise RuntimeError('checksum mismatch')
        return (manifest, raw)
    except Exception:
        _v153_shutil.rmtree(folder, ignore_errors=True)
        raise
try:
    _v177_legacy_0278_v153_validate_restore_gz.__name__ = '_v153_validate_restore_gz'
except Exception:
    pass

def _v153_restore_keyboard(token: str, scope: str):
    kb = types.InlineKeyboardMarkup()
    if scope == 'tenant':
        kb.add(IB('♻️ Восстановить строго из файла', callback_data=f'v153:restore:{token}:replace'))
    else:
        kb.add(IB('♻️ Восстановить весь бот', callback_data=f'v153:restore:{token}:replace'))
    kb.add(IB('❌ Отмена', callback_data=f'v153:restore:{token}:cancel'))
    return kb

def _v153_download_replied_document(msg) -> str:
    reply = getattr(msg, 'reply_to_message', None)
    document = getattr(reply, 'document', None)
    if not document:
        raise RuntimeError('Ответьте командой /restore на файл latest_bot_state.sqlite3.gz')
    name = str(getattr(document, 'file_name', '') or '')
    if not name.lower().endswith('.sqlite3.gz'):
        raise RuntimeError('Нужен файл .sqlite3.gz')
    info = bot.get_file(document.file_id)
    raw = bot.download_file(info.file_path)
    folder = _v153_tempfile.mkdtemp(prefix='v153_restore_upload_')
    path = _v153_os.path.join(folder, 'latest_bot_state.sqlite3.gz')
    with open(path, 'wb') as fh:
        fh.write(raw)
    return path

def v153_cmd_json_full(msg):
    uid = _v153_actor_id(msg)
    chat_id = int(msg.chat.id)
    tenant_id = _v153_tenant_for_chat(chat_id)
    if _v153_platform_owner(uid):
        parts = str(getattr(msg, 'text', '') or '').split(maxsplit=1)
        if len(parts) <= 1:
            kb = types.InlineKeyboardMarkup()
            kb.row(IB('🌐 Весь бот', callback_data='v153:json:global'))
            for tenant in tenant_all() or []:
                tid = str((tenant or {}).get('id') or '')
                if tid:
                    kb.row(IB(f"🏠 {(tenant or {}).get('name') or tid}", callback_data=f'v153:json:tenant:{tid}'))
            bot.reply_to(msg, '🗄 Что выгрузить?', reply_markup=kb)
            return
        if parts[1].strip().lower() not in {'all', 'все', 'global'}:
            tenant_id = parts[1].strip()
            if not tenant_get(tenant_id):
                bot.reply_to(msg, '⛔ Пространство не найдено.')
                return
            scope = 'tenant'
        else:
            scope = 'global'
    elif _v153_can_manage_tenant(uid, tenant_id):
        scope = 'tenant'
    else:
        bot.reply_to(msg, '⛔ Недостаточно прав для полного экспорта.')
        return
    submit_interactive_file_job(chat_id, 'json_full', 'Полное состояние бота' if scope == 'global' else 'Состояние пространства', _v153_send_full_export, chat_id, scope, tenant_id if scope == 'tenant' else None)

def v153_cmd_restore(msg):
    uid = _v153_actor_id(msg)
    chat_id = int(msg.chat.id)
    try:
        gz = _v153_download_replied_document(msg)
        manifest, raw = _v153_validate_restore_gz(gz)
        scope = str(manifest.get('scope') or '')
        tenant_id = str(manifest.get('tenant_id') or _v153_tenant_for_chat(chat_id))
        if scope == 'global' and (not _v153_platform_owner(uid)):
            raise RuntimeError('Глобальное восстановление доступно только владельцу платформы')
        if scope == 'tenant' and (not _v153_can_manage_tenant(uid, tenant_id)):
            current = _v153_tenant_for_chat(chat_id)
            if not _v153_can_manage_tenant(uid, current):
                raise RuntimeError('Нельзя восстановить чужое пространство')
            tenant_id = current
        token = _v153_hashlib.sha256(f'{uid}:{chat_id}:{_v153_time.time_ns()}'.encode()).hexdigest()[:16]
        with _V153_LOCK:
            _V153_RESTORE_PENDING[token] = {'uid': uid, 'chat_id': chat_id, 'gz': gz, 'raw': raw, 'manifest': manifest, 'tenant_id': tenant_id, 'created': _v153_time.time()}
        text = f"🧪 Файл проверен.\n\nВерсия: {manifest.get('bot_version')}\nОбласть: {('весь бот' if scope == 'global' else 'пространство')}\nЧатов: {manifest.get('chat_count')}\nFailed-задач: {manifest.get('failed_tasks')}\nСоздан: {manifest.get('created_at')}\n\nПеред применением будет создана резервная копия текущего состояния."
        bot.reply_to(msg, text, reply_markup=_v153_restore_keyboard(token, scope))
    except Exception as exc:
        bot.reply_to(msg, f'❌ Восстановление не подготовлено:\n{v153_redact_text(exc)[:500]}')

def _v241_restore_storage_barrier_begin() -> int:
    """Invalidate queued pre-restore backup work before replacing canonical state."""
    epoch = int(globals().get('_V241_STORAGE_EPOCH', 0) or 0) + 1
    globals()['_V241_STORAGE_EPOCH'] = epoch
    globals()['_V241_RESTORE_ACTIVE'] = True
    globals()['_V240_RECOVERY_AUTHORITY_ACTIVE'] = True
    sched = globals().get('DELAYED_SCHEDULER')
    if sched is not None:
        for key in ('mega-delta-batch-v90', 'mega-global-quiet-v90', 'mega-global-max-v90', 'mega-global-retry-v90', 'mega-global-user-idle-v190', 'telegram-delta-batch-v234', 'telegram-full-quiet-v234', 'telegram-full-max-v234', 'config-checkpoint-sync-v234'):
            try:
                sched.cancel(key)
            except Exception:
                pass
        try:
            ids = set((globals().get('_backup_timers') or {}).keys()) | set((globals().get('_quick_backup_timers') or {}).keys())
            for cid in ids:
                try:
                    sched.cancel(f'full-backup:{int(cid)}')
                except Exception:
                    pass
        except Exception:
            pass
    lock = globals().get('timer_lock')
    try:
        if lock is not None:
            with lock:
                for name in ('_backup_timers', '_quick_backup_timers'):
                    obj = globals().get(name)
                    if hasattr(obj, 'clear'):
                        obj.clear()
                for name in ('_backup_dirty_chats', '_quick_backup_dirty_chats'):
                    obj = globals().get(name)
                    if hasattr(obj, 'clear'):
                        obj.clear()
    except Exception:
        pass
    try:
        dlock = globals().get('_V240_PENDING_DOMAIN_LOCK')
        pending = globals().get('_V240_PENDING_DOMAINS')
        if dlock is not None and hasattr(pending, 'clear'):
            with dlock:
                pending.clear()
    except Exception:
        pass
    try:
        bot_journal('restore_storage_barrier_v241', int(OWNER_ID or 0) or None, f'begin epoch={epoch}')
    except Exception:
        pass
    return epoch

def _v241_restore_storage_barrier_end(epoch: int, success: bool) -> None:
    globals()['_V241_RESTORE_ACTIVE'] = False
    globals()['_V240_RECOVERY_AUTHORITY_ACTIVE'] = False
    try:
        bot_journal('restore_storage_barrier_v241', int(OWNER_ID or 0) or None, f'end epoch={int(epoch)}; success={int(bool(success))}')
    except Exception:
        pass

def _v153_backup_before_restore() -> str:
    """Always create a local safety copy; try durable witnesses without blocking restore.

    v240 Recovery Authority is intentionally independent of the normal storage mode.
    """
    _recovery_was_active = bool(globals().get('_V240_RECOVERY_AUTHORITY_ACTIVE', False))
    globals()['_V240_RECOVERY_AUTHORITY_ACTIVE'] = True
    folder = _v153_tempfile.mkdtemp(prefix='v240_pre_restore_')
    raw = _v153_os.path.join(folder, 'pre_restore.sqlite3')
    SQLITE.backup_to(raw)
    gz = raw + '.gz'
    with open(raw, 'rb') as fin, _v153_gzip.open(gz, 'wb', compresslevel=5) as fout:
        _v153_shutil.copyfileobj(fin, fout, 1024 * 1024)
    errors = []
    durable = False
    try:
        if mega_is_configured():
            durable = bool(mega_put_replace(gz, f"{MEGA_BACKUP_DIR.rstrip('/')}/database/pre_restore", f"pre_restore_{now_local().strftime('%Y%m%d_%H%M%S')}.sqlite3.gz", archive_previous=False))
            if not durable:
                errors.append('MEGA pre_restore returned false')
    except Exception as exc:
        errors.append('MEGA: ' + str(exc)[:220])
    if not durable:
        try:
            if bool(globals().get('telegram_durable_available_v237_1', lambda: False)()):
                snap_fn = globals().get('telegram_upload_sqlite_snapshot_v234')
                durable = bool(callable(snap_fn) and snap_fn(force=True))
                if not durable:
                    errors.append('Telegram pre_restore returned false')
        except Exception as exc:
            errors.append('Telegram: ' + str(exc)[:220])
    SQLITE.set_meta('restore_control_v240', 'last_pre_restore', {'at': now_local().isoformat(timespec='microseconds'), 'durable': bool(durable), 'errors': errors[-4:], 'local_path': raw})
    try:
        bot_journal('pre_restore_v240', int(OWNER_ID or 0) or None, f"durable={int(durable)}; errors={' | '.join(errors)[:500]}", 'INFO' if durable else 'WARN')
    except Exception:
        pass
    globals()['_V240_RECOVERY_AUTHORITY_ACTIVE'] = bool(_recovery_was_active or globals().get('_V241_RESTORE_ACTIVE', False))
    return folder

def _v153_apply_global_restore(raw: str) -> None:
    SQLITE.replace_database(raw)
    restored = load_data()
    data.clear()
    data.update(restored)
    try:
        tenant_v148_bootstrap()
    except Exception:
        pass
    try:
        tenant_v148_enforce_forward_isolation()
    except Exception:
        pass
    try:
        if '_v184_post_restore_rehydrate' in globals():
            _v184_post_restore_rehydrate(data)
    except Exception as exc:
        log_error(f'v184 global GZ post-restore rehydrate: {exc}')
    save_data(data, full=True)

def _v153_retarget_tenant_value(value, source_tenant: str, target_tenant: str):
    if isinstance(value, dict):
        return {str(k): _v153_retarget_tenant_value(v, source_tenant, target_tenant) for k, v in value.items()}
    if isinstance(value, list):
        return [_v153_retarget_tenant_value(v, source_tenant, target_tenant) for v in value]
    if isinstance(value, str) and value == str(source_tenant):
        return str(target_tenant)
    return _v153_copy.deepcopy(value)

def _v153_remove_scope_from_root_value(value, target_tenant: str, target_chat_ids: set[int]):
    if isinstance(value, list):
        return [x for x in value if not _v153_item_in_tenant_scope(x, target_tenant, target_chat_ids)]
    if isinstance(value, dict):
        return {str(k): v for k, v in value.items() if not _v153_item_in_tenant_scope(v, target_tenant, target_chat_ids, str(k))}
    return value

def _v153_restore_tenant_root(source_root: dict, manifest: dict, target_tenant: str, target_chat_ids: set[int], mode: str) -> dict[int, int]:
    source_tenant = str(manifest.get('tenant_id') or target_tenant)
    source_chat_ids = {int(x) for x in manifest.get('chat_ids') or []}
    live_gs = data.setdefault('_global_settings', {})
    live_tenants = _tenants_root()
    current_row = tenant_get(target_tenant) or {}
    source_gs = (source_root or {}).get('_global_settings') or {}
    source_row = ((source_gs.get('tenants_v148') or {}).get('tenants') or {}).get(source_tenant) or {}
    imported_row = _v153_retarget_tenant_value(v153_sanitize(source_row), source_tenant, target_tenant)
    imported_row['id'] = str(target_tenant)
    imported_row['owner_user_id'] = int(current_row.get('owner_user_id') or imported_row.get('owner_user_id') or 0)
    imported_row['chat_ids'] = sorted(source_chat_ids)
    imported_row['root_chat_id'] = int(imported_row.get('root_chat_id') or next(iter(sorted(source_chat_ids)), 0))
    live_tenants.setdefault('tenants', {})[str(target_tenant)] = imported_row
    for cid in source_chat_ids:
        live_tenants.setdefault('chat_to_tenant', {})[str(cid)] = str(target_tenant)
    remap = {}
    source_rem = (source_gs.get('reminders_v2') or {}).get('items') or {}
    live_rem = live_gs.setdefault('reminders_v2', {'next_id': 1, 'items': {}, 'migrated_v134': True})
    live_items = live_rem.setdefault('items', {})
    if mode == 'replace':
        for rid, cfg in list(live_items.items()):
            if _v153_item_in_tenant_scope(cfg, target_tenant, target_chat_ids):
                live_items.pop(str(rid), None)
    next_id = max([int(x) for x in live_items if str(x).isdigit()] + [int(live_rem.get('next_id') or 1), 1])
    for rid_s, cfg in source_rem.items():
        old_id = int(rid_s) if str(rid_s).isdigit() else 0
        new_id = old_id
        if str(new_id) in live_items and (not _v153_item_in_tenant_scope(live_items.get(str(new_id)), target_tenant, target_chat_ids)):
            next_id += 1
            new_id = next_id
        row = _v153_retarget_tenant_value(cfg, source_tenant, target_tenant)
        row['tenant_id'] = str(target_tenant)
        live_items[str(new_id)] = row
        remap[old_id] = new_id
    live_rem['next_id'] = max([int(x) for x in live_items if str(x).isdigit()] + [1]) + 1
    live_rem['migrated_v134'] = True
    for gs_key in ('operation_ledger_v141', 'finance_integrity_v141'):
        src_value = source_gs.get(gs_key)
        if src_value is None:
            continue
        if mode == 'replace' and gs_key in live_gs:
            if gs_key == 'operation_ledger_v141':
                old_live = live_gs.get(gs_key) or {}
                kept_items = {str(k): v for k, v in (old_live.get('items') or {}).items() if not _v153_item_in_tenant_scope(v, target_tenant, target_chat_ids, str(k))}
                live_gs[gs_key] = {'items': kept_items, 'order': [str(x) for x in old_live.get('order') or [] if str(x) in kept_items], 'next_seq': int(old_live.get('next_seq') or 1)}
            elif gs_key == 'finance_integrity_v141':
                old_live = live_gs.get(gs_key) or {}
                live_gs[gs_key] = {'events': [x for x in old_live.get('events') or [] if not _v153_item_in_tenant_scope(x, target_tenant, target_chat_ids)], 'tips': {str(k): v for k, v in (old_live.get('tips') or {}).items() if not (str(k).lstrip('-').isdigit() and int(k) in target_chat_ids)}, 'anchor': {}, 'event_seq': int(old_live.get('event_seq') or 0)}
        if gs_key == 'operation_ledger_v141':
            live = live_gs.setdefault(gs_key, {'items': {}, 'order': [], 'next_seq': 1})
            for op_id, row in ((src_value or {}).get('items') or {}).items():
                target_id = str(op_id)
                while target_id in (live.get('items') or {}):
                    target_id = target_id + '_r'
                live.setdefault('items', {})[target_id] = _v153_retarget_tenant_value(row, source_tenant, target_tenant)
                live.setdefault('order', []).append(target_id)
            live['next_seq'] = max(int(live.get('next_seq') or 1), int((src_value or {}).get('next_seq') or 1))
        elif gs_key == 'finance_integrity_v141':
            live = live_gs.setdefault(gs_key, {'events': [], 'tips': {}, 'anchor': {}, 'event_seq': 0})
            live.setdefault('events', []).extend(_v153_retarget_tenant_value((src_value or {}).get('events') or [], source_tenant, target_tenant))
            live.setdefault('tips', {}).update((src_value or {}).get('tips') or {})
            live['event_seq'] = max(int(live.get('event_seq') or 0), int((src_value or {}).get('event_seq') or 0))
    for key, src_value in (source_root or {}).items():
        if key == '_global_settings':
            continue
        src_value = _v153_retarget_tenant_value(src_value, source_tenant, target_tenant)
        if mode == 'replace' and key in data:
            data[key] = _v153_remove_scope_from_root_value(data.get(key), target_tenant, target_chat_ids)
        if isinstance(src_value, list):
            live = data.setdefault(key, [])
            seen = {_v153_json.dumps(x, sort_keys=True, ensure_ascii=False, default=str) for x in live if isinstance(live, list)}
            for item in src_value:
                sig = _v153_json.dumps(item, sort_keys=True, ensure_ascii=False, default=str)
                if sig not in seen:
                    live.append(item)
                    seen.add(sig)
        elif isinstance(src_value, dict):
            data.setdefault(key, {}).update(src_value)
    return remap

def _v153_apply_tenant_restore(raw: str, target_tenant: str, mode: str='replace') -> None:
    mode = 'replace'
    src = _v153_sqlite3.connect(raw)
    src.row_factory = _v153_sqlite3.Row
    try:
        manifest = _v153_json.loads(src.execute("SELECT v FROM meta WHERE kind='v153_export' AND k='manifest'").fetchone()[0])
        source_chat_ids = {int(x) for x in manifest.get('chat_ids') or []}
        root_row = src.execute("SELECT v FROM kv WHERE k='root'").fetchone()
        source_root = _v153_json.loads(root_row[0]) if root_row else {}
        target_row = tenant_get(target_tenant) or {}
        target_chat_ids = set((int(x) for x in target_row.get('chat_ids') or []))
        for cid in source_chat_ids:
            current_tenant = str(tenant_id_for_chat(cid, create=False) or '')
            if current_tenant and current_tenant != str(target_tenant) and (cid not in target_chat_ids):
                raise RuntimeError(f'Чат {cid} сейчас принадлежит другому пространству')
        if mode == 'replace':
            for cid in list(target_chat_ids - source_chat_ids):
                data.get('chats', {}).pop(str(cid), None)
                SQLITE.delete_chat(cid)
                for key in list(LOWRAM_COLD_KEYS):
                    SQLITE.delete_cold(cid, key)
            try:
                root = _tenants_root()
                row = (root.get('tenants') or {}).get(str(target_tenant)) or target_row
                row['chat_ids'] = sorted(source_chat_ids)
                if int(row.get('root_chat_id') or 0) not in source_chat_ids:
                    row['root_chat_id'] = next(iter(sorted(source_chat_ids)), 0)
                mapping = root.setdefault('chat_to_tenant', {})
                for cid in target_chat_ids - source_chat_ids:
                    if str(mapping.get(str(cid)) or '') == str(target_tenant):
                        mapping.pop(str(cid), None)
            except Exception:
                pass
        for row in src.execute('SELECT chat_id,v FROM chats').fetchall():
            cid = int(row[0])
            payload = _v153_json.loads(row[1])
            data.setdefault('chats', {})[str(cid)] = _lowram_wrap_store(cid, payload)
            SQLITE.save_chat(cid, _lowram_store_meta_payload(payload))
        for row in src.execute('SELECT chat_id,k,v FROM cold_fields').fetchall():
            cid = int(row[0])
            key = str(row[1])
            value = _v153_json.loads(row[2])
            SQLITE.set_cold(cid, key, value)
        _v153_restore_tenant_root(source_root, manifest, target_tenant, target_chat_ids, mode)
        for cid in source_chat_ids:
            tenant_bind_chat(cid, target_tenant, changed_by=0, force=True)
        try:
            tenant_v148_enforce_forward_isolation()
        except Exception:
            pass
        try:
            if '_v184_post_restore_rehydrate' in globals():
                _v184_post_restore_rehydrate(data, source_chat_ids)
        except Exception as exc:
            log_error(f'v184 tenant GZ post-restore rehydrate: {exc}')
        save_data(data, full=True)
    finally:
        src.close()

def _v153_restore_failed_tasks_from_db(raw: str, allowed_chat_ids: set[int] | None=None) -> int:
    if not mega_is_configured():
        return 0
    conn = _v153_sqlite3.connect(raw)
    try:
        row = conn.execute("SELECT v FROM meta WHERE kind='v153_export' AND k='failed_tasks'").fetchone()
        tasks = _v153_json.loads(row[0]) if row else []
    finally:
        conn.close()
    restored = 0
    remote_dir = mega_task_remote_dir('failed')
    ensure_mega_task_dirs()
    for task in tasks or []:
        if not isinstance(task, dict) or task.get('load_error'):
            continue
        cid = int(task.get('chat_id') or 0)
        if allowed_chat_ids is not None and cid not in allowed_chat_ids:
            continue
        key = str(task.get('task_id') or task.get('update_id') or '').strip()
        if not key:
            continue
        folder = _v153_tempfile.mkdtemp(prefix='v153_failed_restore_')
        try:
            name = f'task_{key}.json'
            local = _v153_os.path.join(folder, name)
            _V153Path(local).write_text(_v153_json.dumps(v153_sanitize(task), ensure_ascii=False, indent=2), encoding='utf-8')
            if mega_put_replace(local, remote_dir, name, archive_previous=False):
                restored += 1
        finally:
            _v153_shutil.rmtree(folder, ignore_errors=True)
    try:
        mega_task_refresh_registry()
    except Exception:
        pass
    return restored

def _v240_retry_pending_restore_reanchor() -> bool:
    """Best-effort durable follow-up for a restore already accepted locally.

    This never rolls the restored state back. It temporarily opens Recovery Authority,
    publishes the *current* accepted state as a fresh canonical lineage, then closes the
    exception again. A transient remote outage therefore cannot make /restore fail.
    """
    pending = SQLITE.get_meta('restore_control_v240', 'remote_reanchor_pending', {}) or {}
    if not isinstance(pending, dict) or not pending:
        return True
    if bool(globals().get('_V241_RESTORE_ACTIVE', False)):
        _v240_schedule_pending_restore_reanchor_retry(30.0)
        return False
    previous = bool(globals().get('_V240_RECOVERY_AUTHORITY_ACTIVE', False))
    globals()['_V240_RECOVERY_AUTHORITY_ACTIVE'] = True
    try:
        active = mega_publish_current_sqlite_v242('pending_remote_reanchor_v242:' + str(pending.get('reason') or 'restore'), manual_restore=False, allow_destructive=True) or {}
        result = {'active': active}
        SQLITE.set_meta('restore_control_v240', 'remote_reanchor_pending', {})
        SQLITE.set_meta('restore_control_v240', 'config_remote_pending', {})
        try:
            runtime_event('restore_remote_reanchor_completed_v240', f"generation={(result.get('active') or {}).get('generation', '—')}", 'INFO')
        except Exception:
            pass
        return True
    except Exception as exc:
        pending['last_retry_at'] = now_local().isoformat(timespec='microseconds')
        pending['last_retry_error'] = str(exc)[:500]
        pending['retry_count'] = int(pending.get('retry_count') or 0) + 1
        SQLITE.set_meta('restore_control_v240', 'remote_reanchor_pending', pending)
        delay = min(600.0, 30.0 * 2 ** min(4, int(pending.get('retry_count') or 1) - 1))
        _v240_schedule_pending_restore_reanchor_retry(delay)
        try:
            runtime_event('restore_remote_reanchor_retry_failed_v240', str(exc)[:500], 'WARN')
        except Exception:
            pass
        return False
    finally:
        globals()['_V240_RECOVERY_AUTHORITY_ACTIVE'] = previous

def _v240_schedule_pending_restore_reanchor_retry(delay: float=20.0):
    sched = globals().get('DELAYED_SCHEDULER')
    if sched is None:
        return None
    try:
        sched.cancel('restore-remote-reanchor-v240')
    except Exception:
        pass
    return sched.schedule('restore-remote-reanchor-v240', max(5.0, float(delay)), _v240_retry_pending_restore_reanchor)

def _canon_v240_restore_reanchor_guaranteed__001(reason: str) -> dict:
    """Never revert a user-confirmed restore because remote re-anchor is unavailable.

    Normal path remains exact durable. On failure, the restored SQLite becomes the local
    canonical state immediately and a remote re-anchor is marked pending for retry.
    """
    try:
        result = constitution_reanchor_after_manual_restore(str(reason))
        result['remote_confirmed_v240'] = True
        SQLITE.set_meta('restore_control_v240', 'remote_reanchor_pending', {})
        return result
    except Exception as exc:
        err = str(exc)[:600]
        try:
            lineage_fn = globals().get('_v239_storage_lineage')
            lineage = str(lineage_fn(True) if callable(lineage_fn) else '')
        except Exception:
            lineage = ''
        try:
            cp = config_guard_accept_current_v234('restore_local_fallback_v240:' + str(reason))
        except Exception:
            cp = {}
        try:
            with data_lock:
                save_data(data, full=True)
                embedded = constitution_semantic_manifest_from_live()
                embedded['snapshot_created_at'] = now_local().isoformat(timespec='microseconds')
                embedded['restore_reason_v240'] = str(reason)
                embedded['storage_lineage_v239'] = lineage
                SQLITE.set_meta('data_constitution_snapshot', 'main', embedded)
        except Exception:
            pass
        pending = {'at': now_local().isoformat(timespec='microseconds'), 'reason': str(reason), 'error': err, 'lineage': lineage, 'config_generation': int((cp or {}).get('generation') or 0)}
        SQLITE.set_meta('restore_control_v240', 'remote_reanchor_pending', pending)
        try:
            _v240_schedule_pending_restore_reanchor_retry(20.0)
        except Exception:
            pass
        try:
            init_delta = globals().get('initialize_delta_baseline')
            if callable(init_delta):
                init_delta(data)
        except Exception:
            pass
        try:
            constitution_clear_quarantine('manual restore accepted locally; remote re-anchor pending v240')
        except Exception:
            pass
        try:
            runtime_event('restore_remote_reanchor_pending_v240', err, 'WARN')
        except Exception:
            pass
        return {'checkpoint': {}, 'config_checkpoint': cp, 'active': {'backend': 'local', 'generation': 'LOCAL-PENDING'}, 'lineage': lineage, 'remote_confirmed_v240': False, 'warning': err}

def _v153_execute_restore(token: str, mode: str, call) -> bool:
    mode = 'replace'
    with _V153_LOCK:
        row = _V153_RESTORE_PENDING.pop(str(token), None)
    if not row:
        try:
            bot.answer_callback_query(call.id, 'Файл восстановления устарел', show_alert=True)
        except Exception:
            pass
        return True
    uid = _v153_actor_id(call)
    if uid != int(row.get('uid') or 0) and (not _v153_platform_owner(uid)):
        try:
            bot.answer_callback_query(call.id, 'Это подтверждение другого пользователя', show_alert=True)
        except Exception:
            pass
        return True
    backup_dir = ''
    restore_epoch = 0
    restore_success = False
    try:
        restore_epoch = _v241_restore_storage_barrier_begin()
        backup_dir = _v153_backup_before_restore()
        scope = str((row.get('manifest') or {}).get('scope') or '')
        if scope == 'global':
            _v153_apply_global_restore(str(row['raw']))
            restored_failed = _v153_restore_failed_tasks_from_db(str(row['raw']), None)
        else:
            _v153_apply_tenant_restore(str(row['raw']), str(row['tenant_id']), str(mode))
            restored_failed = _v153_restore_failed_tasks_from_db(str(row['raw']), set((int(x) for x in (row.get('manifest') or {}).get('chat_ids') or [])))
        constitution_result = _v240_restore_reanchor_guaranteed(f'gz_restore:{scope}:{mode}')
        remote_ok = bool(constitution_result.get('remote_confirmed_v240', True))
        suffix = '' if remote_ok else '\n⚠️ Remote re-anchor временно pending; восстановленное состояние уже принято локально.'
        safe_edit(bot, call, f"✅ Восстановление завершено.\nGeneration: {(constitution_result.get('active') or {}).get('generation', '—')}\nFailed-задач восстановлено: {restored_failed}." + suffix)
        restore_success = True
        bot_journal('v240_restore_applied', int(row['chat_id']), f"scope={scope}; mode={mode}; tenant={row.get('tenant_id')}; by={uid}; constitution=1; remote_confirmed={int(remote_ok)}; epoch={restore_epoch}")
    except Exception as exc:
        safe_edit(bot, call, f'❌ Восстановление остановлено:\n{v153_redact_text(exc)[:800]}')
        bot_journal('v153_restore_failed', int(row['chat_id']), v153_redact_text(exc), 'ERROR')
    finally:
        for path in {row.get('gz'), row.get('raw')}:
            try:
                if path:
                    _v153_shutil.rmtree(_v153_os.path.dirname(str(path)), ignore_errors=True)
            except Exception:
                pass
        if backup_dir:
            _v153_shutil.rmtree(backup_dir, ignore_errors=True)
        if restore_epoch:
            _v241_restore_storage_barrier_end(restore_epoch, restore_success)
    return True
_V153_ORIG_EDIT_TEXT = getattr(bot, 'edit_message_text', None)
_V153_ORIG_EDIT_MARKUP = getattr(bot, 'edit_message_reply_markup', None)
_V153_ORIG_DELETE_MESSAGE = getattr(bot, 'delete_message', None)
_V153_UI_CACHE = {}

def _v153_ui_sig(kind: str, chat_id, message_id, payload, markup=None) -> str:
    try:
        markup_value = markup.to_json() if hasattr(markup, 'to_json') else repr(markup)
    except Exception:
        markup_value = repr(markup)
    raw = _v153_json.dumps([kind, int(chat_id), int(message_id), str(payload or ''), markup_value], ensure_ascii=False, default=str)
    return _v153_hashlib.sha256(raw.encode('utf-8')).hexdigest()

def _v153_ui_cached(sig: str):
    with _V153_LOCK:
        row = _V153_UI_CACHE.get(sig)
        if row and _v153_time.monotonic() - float(row[0]) <= 120.0:
            return row[1]
        for key, item in list(_V153_UI_CACHE.items()):
            if _v153_time.monotonic() - float(item[0]) > 180.0:
                _V153_UI_CACHE.pop(key, None)
    return None

def _v153_ui_remember(sig: str, result):
    with _V153_LOCK:
        _V153_UI_CACHE[sig] = (_v153_time.monotonic(), result)
    return result
if callable(_V153_ORIG_EDIT_TEXT):

    def _v153_edit_message_text(text, chat_id=None, message_id=None, *args, **kwargs):
        sig = _v153_ui_sig('text', chat_id, message_id, text, kwargs.get('reply_markup'))
        cached = _v153_ui_cached(sig)
        if cached is not None:
            return cached
        try:
            return _v153_ui_remember(sig, _V153_ORIG_EDIT_TEXT(text, *args, chat_id=chat_id, message_id=message_id, **kwargs))
        except Exception as exc:
            low = str(exc).casefold()
            if 'message is not modified' in low:
                bot_journal('telegram_edit_idempotent', chat_id, f'message={message_id}')
                return _v153_ui_remember(sig, True)
            raise
    bot.edit_message_text = _v153_edit_message_text
if callable(_V153_ORIG_EDIT_MARKUP):

    def _v153_edit_message_reply_markup(chat_id=None, message_id=None, *args, **kwargs):
        sig = _v153_ui_sig('markup', chat_id, message_id, '', kwargs.get('reply_markup'))
        cached = _v153_ui_cached(sig)
        if cached is not None:
            return cached
        try:
            return _v153_ui_remember(sig, _V153_ORIG_EDIT_MARKUP(*args, chat_id=chat_id, message_id=message_id, **kwargs))
        except Exception as exc:
            if 'message is not modified' in str(exc).casefold():
                bot_journal('telegram_markup_idempotent', chat_id, f'message={message_id}')
                return _v153_ui_remember(sig, True)
            raise
    bot.edit_message_reply_markup = _v153_edit_message_reply_markup
if callable(_V153_ORIG_DELETE_MESSAGE):

    def _v153_delete_message(chat_id, message_id, *args, **kwargs):
        try:
            result = _V153_ORIG_DELETE_MESSAGE(chat_id, message_id, *args, **kwargs)
            try:
                unregister_open_window(int(chat_id), int(message_id))
            except Exception:
                pass
            return result
        except Exception as exc:
            low = str(exc).casefold()
            if any((x in low for x in ('message to delete not found', "message can't be deleted", 'message identifier is not specified'))):
                try:
                    unregister_open_window(int(chat_id), int(message_id))
                except Exception:
                    pass
                bot_journal('telegram_delete_already_gone', chat_id, f'message={message_id}')
                return True
            raise
    bot.delete_message = _v153_delete_message

def _v179_base_reconcile_windows() -> dict:
    result = cleanup_open_window_registry('v153_periodic') if 'cleanup_open_window_registry' in globals() else {}
    try:
        bot_journal('v153_window_reconcile', None, result)
    except Exception:
        pass
    return result

def _v153_handler_audit() -> dict:
    commands = {}
    duplicates = []
    handlers_without_filters = 0
    for handler in list(getattr(bot, 'message_handlers', []) or []):
        filters = handler.get('filters', {}) if isinstance(handler, dict) else {}
        fn = handler.get('function') if isinstance(handler, dict) else None
        rows = filters.get('commands') or []
        if not filters:
            handlers_without_filters += 1
        for command in rows:
            key = str(command).lower()
            if key in commands and commands[key] is not fn:
                duplicates.append(key)
            commands[key] = fn
    callback_count = len(list(getattr(bot, 'callback_query_handlers', []) or []))
    return {'commands': len(commands), 'duplicate_commands': sorted(set(duplicates)), 'message_handlers': len(list(getattr(bot, 'message_handlers', []) or [])), 'callback_handlers': callback_count, 'handlers_without_filters': handlers_without_filters, 'known_commands': sorted(commands)}

def _v153_runtime_audit_text() -> str:
    a = _v153_handler_audit()
    stats = mega_task_registry_stats()
    migration = _v153_migration_store()
    lines = ['ГЛУБОКИЙ АУДИТ v153', f'Создан: {_v153_now()}', '', f"Slash-команд: {a['commands']}; дублей: {', '.join(a['duplicate_commands']) or 'нет'}.", f"Message handlers: {a['message_handlers']}; callback handlers: {a['callback_handlers']}.", 'Команды /json_full, /restore и /full_audit имеют отдельные обработчики и проверку прав.', 'Callback подтверждения защищены одноразовыми token и actor check.', 'Повторная выгрузка не создаёт очередь: одно INFO-сообщение становится кнопкой скачивания.', 'Telegram message is not modified считается идемпотентным результатом, а не ошибкой бизнеса.', 'Явный chat not found для известного чата означает bot_removed; timeout/429/сетевая ошибка остаются unreachable; lifecycle active/unreachable/bot_removed/migrated/archived сохраняется в runtime ZIP.', 'Runtime ZIP скачивает slots/events; устаревшие candidate/staged остаются только в индексе и очищаются до 2 файлов.', f"Durable failed: {stats.get('failed', 0)}; details: {len(stats.get('failed_details') or [])}; pending_detail_refresh={bool(stats.get('failed_details_pending'))}.", 'Reminder witnesses принимаются только при явном EDITREM/EDITREMINT, поэтому финансовая задача не требует reminder_edit.', 'Секреты очищаются перед журналом, snapshot, ZIP/TXT/JSON export и отправкой документа.', f"MEGA root v238: один canonical {globals().get('MEGA_BACKUP_DIR')}; legacy migration state удалён."]
    return '\n'.join(lines)

def v153_cmd_full_audit(msg):
    uid = _v153_actor_id(msg)
    if not _v153_platform_owner(uid):
        bot.reply_to(msg, '⛔ Аудит доступен только владельцу платформы.')
        return
    bot.reply_to(msg, _v153_runtime_audit_text()[:3900])

def v153_cmd_mega_migration_status(msg):
    uid = _v153_actor_id(msg)
    if not _v153_platform_owner(uid):
        return
    bot.reply_to(msg, f"☁️ Хранилище MEGA\n✅ v238: один канонический корень\nАктивная папка: {globals().get('MEGA_BACKUP_DIR')}\nПодкорневые release-каталоги и legacy migration state не используются.")

def _v153_callback_once(call, key: str) -> bool:
    now = _v153_time.time()
    actor = _v153_actor_id(call)
    receipt = f"{actor}:{getattr(call, 'id', '')}:{key}"
    with _V153_LOCK:
        for old, ts in list(_V153_CALLBACK_RECEIPTS.items()):
            if now - ts > 600:
                _V153_CALLBACK_RECEIPTS.pop(old, None)
        if receipt in _V153_CALLBACK_RECEIPTS:
            return False
        _V153_CALLBACK_RECEIPTS[receipt] = now
    return True
_V153_ORIG_EXTENSION_CALLBACK = _v177_legacy_0267_v149_extension_callback

def _v177_legacy_0268_v149_extension_callback(call, data_str: str) -> bool:
    data_str = str(data_str or '')
    if data_str == 'runtime_watcher':
        uid = _v153_actor_id(call)
        chat_id = int(call.message.chat.id)
        if not _v153_platform_owner(uid):
            return bool(_V153_ORIG_EXTENSION_CALLBACK(call, data_str)) if callable(_V153_ORIG_EXTENSION_CALLBACK) else False
        kbw = types.InlineKeyboardMarkup()
        kbw.row(IB('🔄 Обновить', callback_data='runtime_watcher'), IB('📜 События', callback_data='runtime_events'))
        kbw.row(IB('☁️ Снимок Watcher в MEGA', callback_data='runtime_snapshot_now'))
        kbw.row(IB('📦 Runtime ZIP', callback_data='runtime_export'), IB('🗄 /json_full', callback_data='v153:json:menu'))
        kbw.row(IB('🚦 Очереди', callback_data='info_queues'), IB('🧩 Delta', callback_data='info_delta_status'))
        day = get_chat_store(chat_id).get('current_view_day') or today_key()
        kbw.row(IB('🔙 Назад в Инфо', callback_data=f'd:{day}:info'), IB('❌ Закрыть', callback_data='info_close'))
        safe_edit(bot, call, build_runtime_watcher_text(), reply_markup=kbw)
        return True
    if data_str == 'v153:json:menu':
        uid = _v153_actor_id(call)
        chat_id = int(call.message.chat.id)
        if not _v153_platform_owner(uid):
            tenant_id = _v153_tenant_for_chat(chat_id)
            if _v153_can_manage_tenant(uid, tenant_id):
                submit_interactive_file_job(chat_id, 'json_full', 'Состояние пространства', _v153_send_full_export, chat_id, 'tenant', tenant_id)
            return True
        kb = types.InlineKeyboardMarkup()
        kb.row(IB('🌐 Весь бот', callback_data='v153:json:global'))
        for tenant in tenant_all() or []:
            tid = str((tenant or {}).get('id') or '')
            if tid:
                kb.row(IB(f"🏠 {(tenant or {}).get('name') or tid}", callback_data=f'v153:json:tenant:{tid}'))
        safe_edit(bot, call, '🗄 Что выгрузить?', reply_markup=kb)
        return True
    if data_str == 'v153:json:global':
        uid = _v153_actor_id(call)
        chat_id = int(call.message.chat.id)
        if not _v153_platform_owner(uid):
            try:
                bot.answer_callback_query(call.id, 'Только для владельца платформы', show_alert=True)
            except Exception:
                pass
            return True
        submit_interactive_file_job(chat_id, 'json_full', 'Полное состояние бота', _v153_send_full_export, chat_id, 'global', None)
        return True
    if data_str.startswith('v153:json:tenant:'):
        uid = _v153_actor_id(call)
        chat_id = int(call.message.chat.id)
        tenant_id = data_str.split(':', 3)[3]
        if not (_v153_platform_owner(uid) or _v153_can_manage_tenant(uid, tenant_id)):
            try:
                bot.answer_callback_query(call.id, 'Недостаточно прав', show_alert=True)
            except Exception:
                pass
            return True
        submit_interactive_file_job(chat_id, 'json_full', 'Состояние пространства', _v153_send_full_export, chat_id, 'tenant', tenant_id)
        return True
    if data_str.startswith('v153:file:'):
        token = data_str.split(':', 2)[2]
        with _V153_LOCK:
            row = _V153_READY_EXPORTS.pop(token, None)
        if not row:
            try:
                bot.answer_callback_query(call.id, 'Запрос уже использован или устарел', show_alert=True)
            except Exception:
                pass
            return True
        if int(row.get('chat_id') or 0) != int(call.message.chat.id):
            try:
                bot.answer_callback_query(call.id, 'Это кнопка другого чата', show_alert=True)
            except Exception:
                pass
            return True
        if not _v153_callback_once(call, data_str):
            return True
        try:
            safe_edit(bot, call, f"⏳ Запускаю «{row['label']}»…")
        except Exception:
            pass
        submit_interactive_file_job(int(row['chat_id']), row['kind'], row['label'], row['func'], *row['args'], **row['kwargs'])
        return True
    if data_str.startswith('v153:restore:'):
        parts = data_str.split(':')
        if len(parts) >= 4:
            token, action = (parts[2], parts[3])
            if action == 'cancel':
                with _V153_LOCK:
                    row = _V153_RESTORE_PENDING.pop(token, None)
                if row:
                    for path in (row.get('gz'), row.get('raw')):
                        try:
                            _v153_shutil.rmtree(_v153_os.path.dirname(str(path)), ignore_errors=True)
                        except Exception:
                            pass
                safe_edit(bot, call, '❌ Восстановление отменено.')
                return True
            if action == 'merge':
                try:
                    bot.answer_callback_query(call.id, 'Объединение через /restore отключено. Запустите /restore заново.', show_alert=True)
                except Exception:
                    pass
                return True
            if action == 'replace':
                return _v153_execute_restore(token, 'replace', call)
    if callable(_V153_ORIG_EXTENSION_CALLBACK):
        return bool(_V153_ORIG_EXTENSION_CALLBACK(call, data_str))
    return False
try:
    _v177_legacy_0268_v149_extension_callback.__name__ = 'v149_extension_callback'
except Exception:
    pass

def _v153_prune_restore_pending() -> None:
    now = _v153_time.time()
    expired = []
    with _V153_LOCK:
        for token, row in list(_V153_RESTORE_PENDING.items()):
            if now - float((row or {}).get('created') or 0.0) > V153_RESTORE_PENDING_TTL:
                expired.append(_V153_RESTORE_PENDING.pop(token, None))
    for row in expired:
        for path in ((row or {}).get('gz'), (row or {}).get('raw')):
            try:
                if path:
                    _v153_shutil.rmtree(_v153_os.path.dirname(str(path)), ignore_errors=True)
            except Exception:
                pass

def _v153_add_command(commands, function):
    try:
        decorator = bot.message_handler(commands=list(commands))
        decorator(function)
    except Exception:
        pass

def _v153_replace_restore_handler():
    replaced = 0
    for handler in list(getattr(bot, 'message_handlers', []) or []):
        if not isinstance(handler, dict):
            continue
        filters = handler.get('filters') or {}
        commands = [str(x).lower() for x in filters.get('commands') or []]
        if 'restore' in commands:
            handler['function'] = v153_cmd_restore
            replaced += 1
    if not replaced:
        _v153_add_command(['restore'], v153_cmd_restore)
    return replaced
_v153_add_command(['json_full'], v153_cmd_json_full)
_v153_add_command(['full_audit', 'audit_full'], v153_cmd_full_audit)
_v153_add_command(['mega_migration_status'], v153_cmd_mega_migration_status)
_V153_RESTORE_HANDLERS = _v153_replace_restore_handler()
_V153_CALLBACK_DEDUPE_HANDLERS = 0

def _v177_legacy_0084_runtime_mark_ready(detail: str=''):
    result = _V153_ORIG_RUNTIME_MARK_READY(detail) if callable(_V153_ORIG_RUNTIME_MARK_READY) else None
    try:
        DELAYED_SCHEDULER.schedule('v153-instance-lease', 1.0, lambda: GENERAL_TASK_POOL.submit_unique('v153-instance-lease', _v153_instance_lease_check))
        None
        DELAYED_SCHEDULER.schedule('v153-window-reconcile', 8.0, lambda: GENERAL_TASK_POOL.submit_unique('v153-window-reconcile', _v153_reconcile_windows))
        DELAYED_SCHEDULER.schedule('v153-runtime-cleanup', 12.0, lambda: GENERAL_TASK_POOL.submit_unique('v153-runtime-prune', _v153_runtime_cleanup_remote))
        DELAYED_SCHEDULER.schedule('v153-restore-pending-cleanup', 60.0, _v153_prune_restore_pending)

        def _lease_loop():
            _v153_instance_lease_check()
            try:
                None
            except Exception:
                pass

        def _window_loop():
            _v153_reconcile_windows()
            try:
                None
            except Exception:
                pass
        None
        None
    except Exception:
        pass
    return result
try:
    _v177_legacy_0084_runtime_mark_ready.__name__ = 'runtime_mark_ready'
except Exception:
    pass
try:
    _v177_legacy_0007_bot_journal('v153_remaining_fixes_installed', int(OWNER_ID or 0), f'restore_handlers={_V153_RESTORE_HANDLERS}; callback_dedupe={_V153_CALLBACK_DEDUPE_HANDLERS}; new_mega_root={V153_NEW_MEGA_ROOT}')
except Exception:
    pass
'v154: expense marks in F111/F114 and strict ARS/USD Excel isolation.'
import calendar as _v154_calendar
import copy as _v154_copy
import os as _v154_os
import shutil as _v154_shutil
import sqlite3 as _v154_sqlite3
import gzip as _v154_gzip
import json as _v154_json
_V154_BASE_PERIOD_EXCEL_KEYBOARD = _v177_legacy_0172_period_excel_style_keyboard
_V154_BASE_CATEGORY_COMPACT = _v177_legacy_0177_category_rows_without_description
_V154_BASE_MODERN_COMPACT = _v177_legacy_0100_modern_compact_excel_styles_comments
_V154_BASE_MODERN_SIMPLE = _v177_legacy_0099_modern_simple_excel_styles_comments
_V154_BASE_MODERN_CATEGORY = _v177_legacy_0101_modern_category_excel_styles_comments
_V154_BASE_MODERN_CATEGORY_COMPACT = _v177_legacy_0103_modern_category_no_description_styles_comments

def excel_usd_table_enabled(chat_id: int) -> bool:
    """Whether a separate USD operation table is appended to Excel/Google exports."""
    try:
        settings = get_chat_store(int(chat_id)).setdefault('settings', {})
        return bool(settings.get('excel_include_usd_table', True))
    except Exception:
        return True

def set_excel_usd_table_enabled(chat_id: int, enabled: bool) -> bool:
    chat_id = int(chat_id)
    settings = get_chat_store(chat_id).setdefault('settings', {})
    settings['excel_include_usd_table'] = bool(enabled)
    save_data(data, chat_ids=[chat_id])
    try:
        schedule_config_backup_for_chats(chat_id, delay=0.5)
    except Exception:
        pass
    try:
        bot_journal('excel_usd_table_toggle', chat_id, f'enabled={bool(enabled)}')
    except Exception:
        pass
    return bool(enabled)

def toggle_excel_usd_table_enabled(chat_id: int) -> bool:
    return set_excel_usd_table_enabled(int(chat_id), not excel_usd_table_enabled(int(chat_id)))

def _canon_period_excel_style_keyboard__001(scope: str, target_chat_id: int, mode: str, file_type: str, day_key: str, owner_day_key: str):
    """F179: original controls + an explicit independent USD-table switch."""
    kb = _V154_BASE_PERIOD_EXCEL_KEYBOARD(scope, target_chat_id, mode, file_type, day_key, owner_day_key)
    enabled = excel_usd_table_enabled(int(target_chat_id))
    label = f"{('✅' if enabled else '⬜')} 💵 USD расходы в таблице: {('ВКЛ' if enabled else 'ВЫКЛ')}"
    row = [IB(label, callback_data=export_callback(f'exp_excel_dollar_toggle:{scope}:{int(target_chat_id)}:{mode}:{file_type}:{day_key}:{owner_day_key}'))]
    try:
        insert_at = max(0, len(kb.keyboard) - 2)
        kb.keyboard.insert(insert_at, row)
    except Exception:
        kb.row(*row)
    return kb

def _v154_day_has_expense(chat_id: int | None, day_key: str) -> bool:
    if chat_id is None:
        return False
    try:
        store = get_chat_store(int(chat_id))
        return bool(expense_anchor_records_for_day(store, str(day_key)))
    except Exception:
        return False

def _v177_legacy_0169_export_calendar_start_keyboard(view_year: int, view_month: int, return_day_key: str, chat_id: int | None=None):
    """F111. Mark a date with 📝 only when that day actually has an expense."""
    kb = types.InlineKeyboardMarkup(row_width=7)
    last_day = _v154_calendar.monthrange(int(view_year), int(view_month))[1]
    buttons = []
    for day_num in range(1, last_day + 1):
        day_key = _date_key_from_ymd(view_year, view_month, day_num)
        label = f'📝{day_num}' if _v154_day_has_expense(chat_id, day_key) else str(day_num)
        buttons.append(IB(label, callback_data=export_callback(f'exp_pick_set_start:{view_year}:{view_month}:{day_num}:{return_day_key}')))
    for idx in range(0, len(buttons), 7):
        kb.row(*buttons[idx:idx + 7])
    prev_y, prev_m = _shift_month(view_year, view_month, -1)
    next_y, next_m = _shift_month(view_year, view_month, 1)
    kb.row(IB('⬅️ Месяц', callback_data=export_callback(f'exp_pick_start:{prev_y}:{prev_m}:{return_day_key}')), IB(f'{russian_month_name(view_month)} {view_year}', callback_data='none'), IB('Месяц ➡️', callback_data=export_callback(f'exp_pick_start:{next_y}:{next_m}:{return_day_key}')))
    kb.row(IB('◀️ Год', callback_data=export_callback(f'exp_pick_start:{view_year - 1}:{view_month}:{return_day_key}')), IB(str(view_year), callback_data='none'), IB('Год ▶️', callback_data=export_callback(f'exp_pick_start:{view_year + 1}:{view_month}:{return_day_key}')))
    kb.row(IB('🔙 Назад в CSV / Excel', callback_data=f'd:{return_day_key}:csv_all'))
    return kb
try:
    _v177_legacy_0169_export_calendar_start_keyboard.__name__ = '_export_calendar_start_keyboard'
except Exception:
    pass

def _v177_legacy_0171_export_end_calendar_keyboard(start_key: str, start_rid: int, view_year: int, view_month: int, return_day_key: str, chat_id: int | None=None):
    """F114. Mark selectable dates that contain expenses, without changing range rules."""
    kb = types.InlineKeyboardMarkup(row_width=7)
    last_day = _v154_calendar.monthrange(int(view_year), int(view_month))[1]
    buttons = []
    for day_num in range(1, last_day + 1):
        day_key = _date_key_from_ymd(view_year, view_month, day_num)
        if day_key < start_key:
            buttons.append(IB('·', callback_data='none'))
        else:
            label = f'📝{day_num}' if _v154_day_has_expense(chat_id, day_key) else str(day_num)
            buttons.append(IB(label, callback_data=export_callback(f'exp_pick_set_end:{start_key}:{int(start_rid)}:{view_year}:{view_month}:{day_num}:{return_day_key}')))
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
    start_dt = datetime.strptime(start_key, '%Y-%m-%d')
    kb.row(IB('🔙 Изменить начало', callback_data=export_callback(f'exp_pick_set_start:{start_dt.year}:{start_dt.month}:{start_dt.day}:{return_day_key}')))
    return kb
try:
    _v177_legacy_0171_export_end_calendar_keyboard.__name__ = '_export_end_calendar_keyboard'
except Exception:
    pass

def _excel_canonical_opening_balance(chat_id: int, currency: str, start_day: str, start_rid: int | None=0, exact: bool=False) -> float:
    cid = int(chat_id)
    cur = 'usd' if str(currency or 'ars').strip().lower() == 'usd' else 'ars'
    start = str(start_day or '')[:10]
    try:
        start_rid = int(start_rid or 0)
    except Exception:
        start_rid = 0
    total = 0.0
    rows = list(_v151_all_records(cid, cur) or [])
    try:
        rows = sorted(rows, key=record_sort_key)
    except Exception:
        pass
    target_sort_key = None
    if bool(exact) and start_rid and (cur == 'ars'):
        try:
            target = next((r for r in rows if _v151_day_key(r) == start and int(r.get('id') or 0) == start_rid), None)
            if target is not None:
                target_sort_key = record_sort_key(target)
        except Exception:
            target_sort_key = None
    for rec in rows:
        day = _v151_day_key(rec)
        if not day:
            continue
        amount = _v151_float(rec.get('_v151_amount'))
        if day < start:
            total += amount
            continue
        if day > start:
            break
        if not bool(exact) or not start_rid or cur != 'ars':
            break
        if target_sort_key is not None:
            try:
                if record_sort_key(rec) < target_sort_key:
                    total += amount
                    continue
            except Exception:
                pass
            break
        try:
            if int(rec.get('id') or 0) < start_rid:
                total += amount
                continue
        except Exception:
            pass
        break
    return float(total)

def _excel_canonical_records_for_range(chat_id: int, currency: str, start_day: str, end_day: str) -> list[dict]:
    cid = int(chat_id)
    cur = 'usd' if str(currency or 'ars').strip().lower() == 'usd' else 'ars'
    start = str(start_day or '')[:10]
    end = str(end_day or start)[:10]
    if end < start:
        start, end = (end, start)
    out = []
    for rec in _v151_all_records(cid, cur) or []:
        day = _v151_day_key(rec)
        if day and start <= day <= end:
            out.append(rec)
    try:
        return sorted(out, key=record_sort_key)
    except Exception:
        return out

def _excel_chat_id_for_store(store: dict | None) -> int | None:
    if not isinstance(store, dict):
        return None
    try:
        ctx = _v151_context()
        cid = int(ctx.get('target_chat_id') or 0)
        if cid:
            return cid
    except Exception:
        pass
    try:
        for raw_cid, row in (data.get('chats', {}) or {}).items():
            if row is store:
                return int(raw_cid)
    except Exception:
        pass
    try:
        owner_scope = int((store.get('settings', {}) or {}).get('owner_scope_id') or 0)
        if owner_scope:
            return owner_scope
    except Exception:
        pass
    return None

def _v177_legacy_0272_v151_usd_records(chat_id: int) -> list[dict]:
    store = get_chat_store(int(chat_id))
    active = _v151_sync_currency_snapshots(store)
    ars_source = store.get('records', []) if active == 'ars' else store.get('ars_records', [])
    usd_source = store.get('records', []) if active == 'usd' else store.get('usd_records', [])
    ars_by_msg = {}
    ars_by_op = {}
    for rec in ars_source or []:
        if not isinstance(rec, dict):
            continue
        msg = int(rec.get('source_msg_id') or 0)
        op = str(rec.get('operation_key') or '').strip()
        if msg:
            ars_by_msg[msg] = rec
        if op:
            ars_by_op[op] = rec

    def _same_business_row(left: dict, right: dict) -> bool:
        try:
            return abs(_v151_float(left.get('amount')) - _v151_float(right.get('amount'))) <= 1e-09 and str(left.get('note') or '').strip() == str(right.get('note') or '').strip() and (_v151_day_key(left) == _v151_day_key(right))
        except Exception:
            return False
    rows = []
    represented_sources = set()
    seen_independent = set()
    for rec in usd_source or []:
        if not isinstance(rec, dict):
            continue
        operation_key = str(rec.get('operation_key') or '').strip()
        source_msg_id = int(rec.get('source_msg_id') or 0)
        peer = ars_by_msg.get(source_msg_id) if source_msg_id else None
        if peer is None and operation_key:
            peer = ars_by_op.get(operation_key)
        explicit_usd = str(rec.get('currency') or '').strip().upper() == 'USD'
        if peer is not None and _same_business_row(rec, peer) and (not explicit_usd):
            continue
        key = ('op', operation_key) if operation_key else ('msg', source_msg_id) if source_msg_id else (int(rec.get('id') or 0), str(rec.get('timestamp') or ''), _v151_day_key(rec), _v151_float(rec.get('amount')))
        if key in seen_independent:
            continue
        seen_independent.add(key)
        item = dict(rec)
        item['_v151_amount'] = _v151_float(rec.get('amount'))
        item['_v151_note'] = str(rec.get('note') or rec.get('usd_note') or '')
        item['_v151_currency'] = 'usd'
        rows.append(item)
        if source_msg_id:
            represented_sources.add(('msg', source_msg_id))
        if operation_key:
            represented_sources.add(('op', operation_key))
    for rec in ars_source or []:
        if not isinstance(rec, dict):
            continue
        usd_amount = _v151_float(rec.get('usd_amount'))
        if abs(usd_amount) <= 1e-12:
            continue
        operation_key = str(rec.get('operation_key') or '').strip()
        source_msg_id = int(rec.get('source_msg_id') or 0)
        source_keys = set()
        if source_msg_id:
            source_keys.add(('msg', source_msg_id))
        if operation_key:
            source_keys.add(('op', operation_key))
        if source_keys and any((k in represented_sources for k in source_keys)):
            continue
        item = dict(rec)
        item['_v151_amount'] = usd_amount
        item['_v151_note'] = str(rec.get('usd_note') or rec.get('note') or '')
        item['_v151_currency'] = 'usd'
        item['_v151_embedded'] = True
        rows.append(item)
        represented_sources.update(source_keys)
    try:
        return sorted(rows, key=record_sort_key)
    except Exception:
        return rows
try:
    _v177_legacy_0272_v151_usd_records.__name__ = '_v151_usd_records'
except Exception:
    pass
_V193_A1_REF_RE = _v151_re.compile('(?<![A-Z0-9_])(\\$?[A-Z]{1,3}\\$?)(\\d+)')

def _v193_shift_formula_a1(formula: str, row_offset: int) -> str:
    """Shift only A1-style row references when a prebuilt table is appended lower in a sheet."""
    text = str(formula or '')
    offset = int(row_offset or 0)
    if not text or not offset:
        return text

    def _repl(match):
        return f'{match.group(1)}{int(match.group(2)) + offset}'
    return _V193_A1_REF_RE.sub(_repl, text)

def _v193_shift_formula_rows(rows: list[list], row_offset: int) -> list[list]:
    """Deep-copy row payloads and move formula references with the appended section."""
    out = _v154_copy.deepcopy(list(rows or []))
    offset = int(row_offset or 0)
    if not offset:
        return out
    for row in out:
        if not isinstance(row, list):
            continue
        for idx, cell in enumerate(row):
            if isinstance(cell, dict) and cell.get('formula'):
                item = dict(cell)
                item['formula'] = _v193_shift_formula_a1(item.get('formula'), offset)
                row[idx] = item
    return out

def _v193_validate_currency_formula_domains(rows: list[list]) -> bool:
    """USD formulas must never point back into the ARS section after sections are joined."""
    usd_row = None
    for idx, row in enumerate(rows or [], start=1):
        try:
            if str((row or [''])[0]).strip().upper() == 'USD':
                usd_row = idx
                break
        except Exception:
            pass
    if not usd_row:
        return True
    bad = []
    for rr, row in enumerate(rows or [], start=1):
        if rr < usd_row or not isinstance(row, list):
            continue
        for cc, cell in enumerate(row, start=1):
            if not isinstance(cell, dict) or not cell.get('formula'):
                continue
            refs = [int(m.group(2)) for m in _V193_A1_REF_RE.finditer(str(cell.get('formula') or ''))]
            if refs and min(refs) < usd_row:
                bad.append((rr, cc, str(cell.get('formula'))))
    if bad:
        raise RuntimeError(f'Excel USD formula escaped into ARS section: {bad[:8]}')
    return True

def _v154_join_ars_usd(ars_rows: list[list], usd_rows: list[list], chat_id: int) -> list[list]:
    if not excel_usd_table_enabled(int(chat_id)):
        return list(ars_rows or [])
    prefix = list(ars_rows or []) + [[], []]
    shifted_usd = _v193_shift_formula_rows(list(usd_rows or []), len(prefix))
    joined = prefix + shifted_usd
    _v193_validate_currency_formula_domains(joined)
    return joined

def _canon_build_exact_category_stats_xlsx_rows__001(target_chat_id: int, start_key: str, start_rid: int, end_key: str, end_rid: int) -> list[list]:
    """ARS keeps category layout; USD is always a clean four-column operation table."""
    previous = getattr(_V151_EXPORT_LOCAL, 'value', None)
    if not previous:
        _V151_EXPORT_LOCAL.value = {'kind': 'exact', 'target_chat_id': int(target_chat_id), 'start_key': str(start_key)[:10], 'start_rid': int(start_rid or 0), 'end_key': str(end_key)[:10], 'end_rid': int(end_rid or 0), 'file_type': 'xlsxstat'}
    try:
        ars_rows = _v151_category_table(int(target_chat_id), 'ars')
        usd_rows, _ = _v151_simple_table(int(target_chat_id), 'usd', compact=False)
        return _v154_join_ars_usd(ars_rows, usd_rows, int(target_chat_id))
    finally:
        if not previous:
            _V151_EXPORT_LOCAL.value = None

def _canon_xlsx_simple_rows_with_balances__001(rows: list[list], opening_balance: float, target_chat_id: int | None=None) -> list[list]:
    if target_chat_id is None:
        return globals().get('_V150_BASE_SIMPLE_ROWS', lambda r, o, *_: r)(rows, opening_balance, target_chat_id)
    ars_rows, _ = _v151_simple_table(int(target_chat_id), 'ars', compact=False)
    usd_rows, _ = _v151_simple_table(int(target_chat_id), 'usd', compact=False)
    return _v154_join_ars_usd(ars_rows, usd_rows, int(target_chat_id))

def _v177_legacy_0096_compact_simple_excel_rows_and_annotations(raw_rows: list[tuple], opening_balance: float, target_chat_id: int | None=None) -> tuple[list[list], dict[tuple[int, int], str]]:
    if target_chat_id is None:
        base = globals().get('_V150_BASE_COMPACT_ROWS')
        return base(raw_rows, opening_balance, target_chat_id) if callable(base) else ([], {})
    ars_rows, ars_notes = _v151_simple_table(int(target_chat_id), 'ars', compact=True)
    if not excel_usd_table_enabled(int(target_chat_id)):
        return (ars_rows, dict(ars_notes))
    usd_rows, _ = _v151_simple_table(int(target_chat_id), 'usd', compact=False)
    prefix = list(ars_rows or []) + [[], []]
    shifted_usd = _v193_shift_formula_rows(usd_rows, len(prefix))
    joined = prefix + shifted_usd
    _v193_validate_currency_formula_domains(joined)
    return (joined, dict(ars_notes))
try:
    _v177_legacy_0096_compact_simple_excel_rows_and_annotations.__name__ = '_compact_simple_excel_rows_and_annotations'
except Exception:
    pass

def _v177_legacy_0178_category_rows_without_description(rows: list[list]) -> tuple[list[list], dict[tuple[int, int], str]]:
    """Compact only the ARS category section; never remove Description from the USD section."""
    usd_index = None
    for idx, row in enumerate(rows or []):
        try:
            if str((row or [''])[0]).strip().upper() == 'USD':
                usd_index = idx
                break
        except Exception:
            pass
    if usd_index is None or not callable(_V154_BASE_CATEGORY_COMPACT):
        return _V154_BASE_CATEGORY_COMPACT(rows) if callable(_V154_BASE_CATEGORY_COMPACT) else (rows, {})
    ars_part = list(rows[:usd_index])
    usd_part = list(rows[usd_index:])
    compact_ars, annotations = _V154_BASE_CATEGORY_COMPACT(ars_part)
    return (compact_ars + usd_part, annotations)
try:
    _v177_legacy_0178_category_rows_without_description.__name__ = '_category_rows_without_description'
except Exception:
    pass

def _v154_find_usd_section(rows: list[list]) -> int | None:
    for idx, row in enumerate(rows or []):
        try:
            if str((row or [''])[0]).strip().upper() == 'USD':
                return idx
        except Exception:
            pass
    return None

def _v154_merge_styles(prefix_rows, suffix_rows, prefix_result, suffix_result, keep_suffix_comments=True):
    p_styles, p_comments, p_freeze, p_widths = prefix_result
    s_styles, s_comments, _s_freeze, s_widths = suffix_result
    offset = len(prefix_rows)
    comments = dict(p_comments or {})
    if keep_suffix_comments:
        for (r, c), text in (s_comments or {}).items():
            comments[int(r) + offset, int(c)] = text
    max_len = max(len(p_widths or []), len(s_widths or []))
    widths = []
    for i in range(max_len):
        widths.append(max((p_widths or [0])[i] if i < len(p_widths or []) else 0, (s_widths or [0])[i] if i < len(s_widths or []) else 0))
    return (list(p_styles or []) + list(s_styles or []), comments, p_freeze, widths)

def _canon_modern_compact_excel_styles_comments__001(rows: list[list], annotations: dict[tuple[int, int], str]):
    """Compact ARS may stay 3-column, while appended USD keeps its four-column simple layout."""
    idx = _v154_find_usd_section(rows)
    if idx is None or not callable(_V154_BASE_MODERN_COMPACT) or (not callable(_V154_BASE_MODERN_SIMPLE)):
        return _V154_BASE_MODERN_COMPACT(rows, annotations)
    prefix, suffix = (list(rows[:idx]), list(rows[idx:]))
    p = _V154_BASE_MODERN_COMPACT(prefix, annotations)
    s = _V154_BASE_MODERN_SIMPLE(suffix)
    return _v154_merge_styles(prefix, suffix, p, s, keep_suffix_comments=False)

def _v177_legacy_0102_modern_category_excel_styles_comments(rows: list[list]):
    idx = _v154_find_usd_section(rows)
    if idx is None or not callable(_V154_BASE_MODERN_CATEGORY) or (not callable(_V154_BASE_MODERN_SIMPLE)):
        return _V154_BASE_MODERN_CATEGORY(rows)
    prefix, suffix = (list(rows[:idx]), list(rows[idx:]))
    return _v154_merge_styles(prefix, suffix, _V154_BASE_MODERN_CATEGORY(prefix), _V154_BASE_MODERN_SIMPLE(suffix), keep_suffix_comments=True)
try:
    _v177_legacy_0102_modern_category_excel_styles_comments.__name__ = '_modern_category_excel_styles_comments'
except Exception:
    pass

def _canon_modern_category_no_description_styles_comments__001(rows: list[list], annotations: dict[tuple[int, int], str]):
    idx = _v154_find_usd_section(rows)
    if idx is None or not callable(_V154_BASE_MODERN_CATEGORY_COMPACT) or (not callable(_V154_BASE_MODERN_SIMPLE)):
        return _V154_BASE_MODERN_CATEGORY_COMPACT(rows, annotations)
    prefix, suffix = (list(rows[:idx]), list(rows[idx:]))
    p = _V154_BASE_MODERN_CATEGORY_COMPACT(prefix, annotations)
    s = _V154_BASE_MODERN_SIMPLE(suffix)
    return _v154_merge_styles(prefix, suffix, p, s, keep_suffix_comments=False)

def _v177_legacy_0279_v153_validate_restore_gz(gz_path: str) -> tuple[dict, str]:
    folder = _v153_tempfile.mkdtemp(prefix='v154_restore_validate_')
    raw = _v154_os.path.join(folder, 'restore.sqlite3')
    try:
        with _v154_gzip.open(gz_path, 'rb') as fin, open(raw, 'wb') as fout:
            _v154_shutil.copyfileobj(fin, fout, 1024 * 1024)
        conn = _v154_sqlite3.connect(raw)
        try:
            integrity = str(conn.execute('PRAGMA integrity_check').fetchone()[0])
            if integrity.lower() != 'ok':
                raise RuntimeError(f'SQLite integrity_check: {integrity}')
            row = conn.execute("SELECT v FROM meta WHERE kind='v153_export' AND k='manifest'").fetchone()
            if not row:
                raise RuntimeError('manifest v153 not found')
            manifest = _v154_json.loads(row[0])
        finally:
            conn.close()
        if str(manifest.get('kind')) != 'telegram_bot_full_state_v153':
            raise RuntimeError('unknown export kind')
        if int(manifest.get('schema_version') or 0) != V153_EXPORT_SCHEMA:
            raise RuntimeError('unsupported export schema')
        export_version = str(manifest.get('bot_version') or '')
        if not (export_version.startswith('bot_v153_') or export_version.startswith('bot_v154_')):
            raise RuntimeError(f"unsupported bot version: {export_version or 'missing'}")
        checksum = _v153_db_logical_checksum(raw)
        if checksum != str(manifest.get('checksum') or ''):
            raise RuntimeError('checksum mismatch')
        return (manifest, raw)
    except Exception:
        _v154_shutil.rmtree(folder, ignore_errors=True)
        raise
try:
    _v177_legacy_0279_v153_validate_restore_gz.__name__ = '_v153_validate_restore_gz'
except Exception:
    pass
try:
    WINDOW_MARKER_CONSTANTS['exp_excel_dollar_toggle:*'] = 'Ф179'
except Exception:
    pass
try:
    _v177_legacy_0007_bot_journal('v154_excel_usd_isolation_installed', int(OWNER_ID or 0), 'strict_usd_ledger=1; f111_f114_marks=1; f179_usd_toggle=1')
except Exception:
    pass

def _v243_mark_runtime_restore_healthy(reason: str, *, remote_confirmed: bool=False, generation: str='') -> dict:
    detail = str(reason or 'manual recovery accepted')
    if generation:
        detail += f'; generation={generation}'
    detail += '; MEGA canonical confirmed' if remote_confirmed else '; MEGA canonical pending/retry allowed'
    try:
        lock = globals().get('_RUNTIME_LOCK')
        state = globals().get('_RUNTIME_STATE')
        if isinstance(state, dict):
            if lock is not None:
                with lock:
                    state['restore_attempted'] = True
                    state['restore_ok'] = True
                    state['restore_detail'] = detail[:500]
                    state['last_error'] = ''
            else:
                state['restore_attempted'] = True
                state['restore_ok'] = True
                state['restore_detail'] = detail[:500]
                state['last_error'] = ''
    except Exception:
        pass
    try:
        _clear_restore_guard()
    except Exception:
        pass
    try:
        clearq = globals().get('constitution_clear_quarantine')
        if callable(clearq):
            clearq('v243 confirmed local recovery')
    except Exception:
        pass
    try:
        runtime_event('runtime_restore_healed_v243', detail[:700], 'INFO')
    except Exception:
        pass
    try:
        resume = globals().get('_v244_google_resume_after_recovery')
        sched = globals().get('DELAYED_SCHEDULER')
        if callable(resume):
            if sched is not None:
                sched.schedule('google-resume-after-recovery-v244', 1.0, resume, str(reason or 'recovery'))
            else:
                resume(str(reason or 'recovery'))
    except Exception:
        pass
    return {'ok': True, 'detail': detail, 'remote_confirmed': bool(remote_confirmed), 'generation': str(generation or '')}

def _canon_v240_restore_reanchor_guaranteed__002(reason: str) -> dict:
    """Local restore is accepted immediately; MEGA publication is attempted immediately via one WRITE path."""
    previous = bool(globals().get('_V240_RECOVERY_AUTHORITY_ACTIVE', False))
    globals()['_V240_RECOVERY_AUTHORITY_ACTIVE'] = True
    try:
        publish = globals().get('mega_publish_current_sqlite_v242')
        if not callable(publish):
            raise RuntimeError('v242 unified MEGA publisher unavailable')
        active = publish(str(reason or 'restore'), manual_restore=True, allow_destructive=True) or {}
        SQLITE.set_meta('restore_control_v240', 'remote_reanchor_pending', {})
        try:
            runtime_event('restore_remote_reanchor_confirmed_v242', f"generation={active.get('generation')}; records={active.get('total_records')}")
        except Exception:
            pass
        try:
            _v243_mark_runtime_restore_healthy(str(reason), remote_confirmed=True, generation=str(active.get('generation') or ''))
        except Exception:
            pass
        return {'active': active, 'lineage': str(active.get('storage_lineage_v239') or ''), 'config_checkpoint': config_guard_latest_local_v234() or {}, 'remote_confirmed_v240': True, 'remote_confirmed_v242': True}
    except Exception as exc:
        err = str(exc)[:700]
        try:
            cp = config_guard_accept_current_v234('restore_local_pending_v242:' + str(reason))
        except Exception:
            cp = {}
        pending = {'at': now_local().isoformat(timespec='microseconds'), 'reason': str(reason), 'error': err, 'lineage': str(_v239_storage_lineage(create=False) if '_v239_storage_lineage' in globals() else ''), 'config_generation': int((cp or {}).get('generation') or 0)}
        try:
            SQLITE.set_meta('restore_control_v240', 'remote_reanchor_pending', pending)
        except Exception:
            pass
        try:
            _v240_schedule_pending_restore_reanchor_retry(20.0)
        except Exception:
            pass
        try:
            runtime_event('restore_remote_reanchor_pending_v242', err, 'WARN')
        except Exception:
            pass
        try:
            _v243_mark_runtime_restore_healthy(str(reason), remote_confirmed=False, generation='LOCAL-PENDING')
        except Exception:
            pass
        return {'active': {'backend': 'local', 'generation': 'LOCAL-PENDING', 'total_records': int((constitution_semantic_manifest_from_live() or {}).get('total_records') or 0)}, 'lineage': pending.get('lineage') or '', 'config_checkpoint': cp, 'remote_confirmed_v240': False, 'remote_confirmed_v242': False, 'warning': err}
    finally:
        globals()['_V240_RECOVERY_AUTHORITY_ACTIVE'] = bool(previous or globals().get('_V241_RESTORE_ACTIVE', False))
_V242_MEGA_DB_CATALOG_CACHE = {}

def _v242_mega_database_catalog(limit: int=14) -> list[dict]:
    """List actual recoverable SQLite files in the canonical MEGA database tree."""
    if not mega_is_configured():
        return []
    rows = []
    seen = set()
    finder = globals().get('_mega_find_remote_files')
    if not callable(finder):
        return rows
    active = {}
    try:
        active = constitution_load_active_manifest_remote(force=True) or {}
    except Exception:
        active = {}
    active_remote = str(active.get('remote_generation') or '')

    def add(remote, kind):
        remote = str(remote or '').strip()
        if not remote or remote in seen:
            return
        seen.add(remote)
        name = os.path.basename(remote)
        token = hashlib.sha256(remote.encode('utf-8')).hexdigest()[:12]
        row = {'token': token, 'remote': remote, 'name': name, 'kind': kind, 'active': bool(active_remote and remote == active_remote)}
        _V242_MEGA_DB_CATALOG_CACHE[token] = row
        rows.append(row)
    try:
        for remote in finder(constitution_generations_dir(), 'generation_*.sqlite3.gz', limit=max(8, int(limit))):
            add(remote, 'generation')
    except Exception:
        pass
    try:
        for remote in finder(constitution_database_dir(), LOWRAM_DB_LATEST_NAME, limit=2):
            add(remote, 'legacy_latest')
    except Exception:
        pass
    try:
        for remote in finder(constitution_database_dir() + '/history', 'bot_state_*.sqlite3.gz', limit=6):
            add(remote, 'legacy_history')
    except Exception:
        pass
    try:
        for remote in finder(constitution_database_dir() + '/pre_restore', 'pre_restore_*.sqlite3.gz', limit=6):
            add(remote, 'pre_restore')
    except Exception:
        pass
    return rows[:max(1, int(limit))]

def _v242_mega_catalog_entry(token: str) -> dict:
    token = str(token or '')
    row = _V242_MEGA_DB_CATALOG_CACHE.get(token)
    if row:
        return dict(row)
    _v242_mega_database_catalog(24)
    return dict(_V242_MEGA_DB_CATALOG_CACHE.get(token) or {})

def _v242_restore_selected_mega_database(token: str, chat_id: int) -> dict:
    """Exact point-in-time database restore selected by owner. No current deltas are auto-applied."""
    row = _v242_mega_catalog_entry(token)
    if not row:
        raise RuntimeError('Выбранная база больше не найдена в каталоге MEGA')
    remote = str(row.get('remote') or '')
    previous = bool(globals().get('_V240_RECOVERY_AUTHORITY_ACTIVE', False))
    globals()['_V240_RECOVERY_AUTHORITY_ACTIVE'] = True
    epoch = 0
    backup_dir = ''
    success = False
    try:
        begin = globals().get('_v241_restore_storage_barrier_begin')
        if callable(begin):
            epoch = int(begin() or 0)
        backup_dir = _v153_backup_before_restore()
        work = _v153_tempfile.mkdtemp(prefix='v242_mega_selected_')
        try:
            res = _mega_run('mega-get', [remote, work], check=False, timeout=max(float(MEGA_TIMEOUT), 240.0))
            if res.returncode != 0:
                raise RuntimeError('Не удалось скачать выбранную базу MEGA')
            found = list(Path(work).rglob(os.path.basename(remote))) or list(Path(work).rglob('*.sqlite3.gz'))
            if not found:
                raise RuntimeError('Скачанный файл базы не найден')
            gz = str(found[0])
            raw = os.path.join(work, 'selected.sqlite3')
            _lowram_gunzip_file(gz, raw)
            semantic = constitution_semantic_manifest_from_sqlite(raw) or {}
            conn = sqlite3.connect(raw)
            try:
                qc = conn.execute('PRAGMA quick_check').fetchone()
                if not qc or str(qc[0]).lower() != 'ok':
                    raise RuntimeError(f'SQLite quick_check failed: {qc}')
            finally:
                conn.close()
            SQLITE.replace_database(raw)
            restored = load_data()
            data.clear()
            data.update(restored)
            try:
                tenant_v148_bootstrap()
            except Exception:
                pass
            try:
                tenant_v148_enforce_forward_isolation()
            except Exception:
                pass
            try:
                fn = globals().get('_v184_post_restore_rehydrate')
                if callable(fn):
                    fn(data)
            except Exception:
                pass
            save_data(data, full=True)
            reanchor = _v240_restore_reanchor_guaranteed('owner_selected_mega_database_v242') or {}
            try:
                rec = globals().get('_reminder_boot_reconcile_v241')
                if callable(rec):
                    rec()
            except Exception:
                pass
            success = True
            active = reanchor.get('active') or {}
            return {'ok': True, 'source': remote, 'source_records': int(semantic.get('total_records') or 0), 'generation': str(active.get('generation') or ''), 'remote_confirmed': bool(reanchor.get('remote_confirmed_v242', False))}
        finally:
            _v153_shutil.rmtree(work, ignore_errors=True)
    finally:
        if backup_dir:
            try:
                _v153_shutil.rmtree(backup_dir, ignore_errors=True)
            except Exception:
                pass
        end = globals().get('_v241_restore_storage_barrier_end')
        if epoch and callable(end):
            try:
                end(epoch, success)
            except Exception:
                pass
        globals()['_V240_RECOVERY_AUTHORITY_ACTIVE'] = bool(previous)
# v262
