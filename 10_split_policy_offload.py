# v262

# --- ИСТОЧНИК: 92_v262_linked_finance_speed.py ---
"""v262: one logical finance operation across all edit paths + hot UI path decoupling.

The immutable origin is source Telegram chat/message.  Copies keep their own Telegram
message ids, but edits always resolve back to that origin and update every finance row
that represents the same logical operation.  UI/navigation state stays RAM-first;
remote mirrors run after the user-visible edit.
"""
import copy as _v262_copy
import datetime as _v262_datetime
import re as _v262_re
import threading as _v262_threading
import time as _v262_time
from collections import defaultdict as _v262_defaultdict, deque as _v262_deque

_V262_BASE_STRONG_KEYS = globals().get('_v258_record_strong_keys')
_V262_BASE_NORMALIZE = globals().get('normalize_chat_records')
_V262_BASE_ADD_RECORD = globals().get('add_record_to_chat')
_V262_BASE_BIND_FORWARD = globals().get('_v260_bind_forward_finance_record')
_V262_BASE_CONFIG_PROJECTION = globals().get('_v234_config_projection_from_payload')
_V262_FINANCE_LINK_LOCK = _v262_threading.RLock()
_V262_NAV_MIRROR_LOCK = _v262_threading.RLock()
_V262_NAV_MIRROR_QUEUES = _v262_defaultdict(_v262_deque)
_V262_NAV_MIRROR_RUNNING = set()
_V262_TRANSIENT_PERSIST_PENDING = set()
_V262_TRANSIENT_PERSIST_LOCK = _v262_threading.RLock()


def _v262_int(value, default=0):
    try:
        return int(value or 0)
    except Exception:
        return int(default or 0)


def _v262_origin_tuple_from_key(value):
    m = _v262_re.fullmatch(r'fin-origin:(-?\d+):(\d+)', str(value or '').strip())
    return (int(m.group(1)), int(m.group(2))) if m else (0, 0)


def _v262_origin_tuple_from_operation(value):
    op = str(value or '').strip()
    m = _v262_re.fullmatch(r'fwd-fin:(-?\d+):(\d+):-?\d+', op)
    if m:
        return (int(m.group(1)), int(m.group(2)))
    m = _v262_re.fullmatch(r'finance:(-?\d+):[^:]+:(\d+)', op)
    if m:
        return (int(m.group(1)), int(m.group(2)))
    return (0, 0)


def finance_origin_identity_v262(chat_id: int, rec: dict | None, fallback_msg_id: int=0):
    """Return immutable (source_chat_id, source_message_id, origin_key)."""
    cid = _v262_int(chat_id)
    rec = rec if isinstance(rec, dict) else {}
    src_chat, src_msg = _v262_origin_tuple_from_key(rec.get('finance_origin_key_v262'))
    if not (src_chat and src_msg):
        src_chat = _v262_int(rec.get('forward_source_chat_id'))
        src_msg = _v262_int(rec.get('forward_source_msg_id'))
    if not (src_chat and src_msg):
        src_chat, src_msg = _v262_origin_tuple_from_operation(rec.get('operation_key'))
    if not (src_chat and src_msg):
        try:
            ident = globals().get('_forward_copy_record_identity')
            if callable(ident):
                is_copy, _dst_mid, rchat, rmsg = ident(cid, rec)
                if is_copy and rchat and rmsg:
                    src_chat, src_msg = int(rchat), int(rmsg)
        except Exception:
            pass
    if not src_chat:
        src_chat = cid
    if not src_msg:
        for key in ('source_msg_id', 'origin_msg_id', 'msg_id', 'source_order_msg_id'):
            src_msg = _v262_int(rec.get(key))
            if src_msg:
                break
    if not src_msg:
        src_msg = _v262_int(fallback_msg_id)
    key = f'fin-origin:{int(src_chat)}:{int(src_msg)}' if src_chat and src_msg else ''
    return (int(src_chat or 0), int(src_msg or 0), key)


def _ensure_finance_origin_key_v262(chat_id: int, rec: dict | None, fallback_msg_id: int=0) -> str:
    if not isinstance(rec, dict):
        return ''
    src_chat, src_msg, key = finance_origin_identity_v262(int(chat_id), rec, fallback_msg_id)
    if key:
        rec['finance_origin_key_v262'] = key
        rec.setdefault('finance_origin_chat_id_v262', int(src_chat))
        rec.setdefault('finance_origin_msg_id_v262', int(src_msg))
    return key


def _v258_record_strong_keys(rec: dict, chat_id: int) -> list[str]:
    """v262 extends dedupe proof to forwarded copies and the immutable origin."""
    out = []
    if callable(_V262_BASE_STRONG_KEYS):
        try:
            out.extend(_V262_BASE_STRONG_KEYS(rec, int(chat_id)) or [])
        except Exception:
            pass
    try:
        origin = _ensure_finance_origin_key_v262(int(chat_id), rec)
        if origin:
            out.append('origin:' + origin)
    except Exception:
        pass
    try:
        op = str((rec or {}).get('operation_key') or '').strip()
        if op.startswith('fwd-fin:'):
            out.append('op:' + op)
    except Exception:
        pass
    return list(dict.fromkeys((str(x) for x in out if x)))


def _v262_tag_store_origins(chat_id: int) -> int:
    changed = 0
    try:
        store = get_chat_store(int(chat_id))
    except Exception:
        return 0
    seen = set()
    for key in ('records', 'ars_records', 'usd_records'):
        for rec in store.get(key, []) or []:
            if not isinstance(rec, dict) or id(rec) in seen:
                continue
            seen.add(id(rec))
            before = str(rec.get('finance_origin_key_v262') or '')
            after = _ensure_finance_origin_key_v262(int(chat_id), rec)
            if after and after != before:
                changed += 1
    return changed


def normalize_chat_records(chat_id: int) -> None:
    _v262_tag_store_origins(int(chat_id))
    if callable(_V262_BASE_NORMALIZE):
        _V262_BASE_NORMALIZE(int(chat_id))
    _v262_tag_store_origins(int(chat_id))


def add_record_to_chat(chat_id: int, amount: float, note: str, owner: int, source_msg=None, day_key=None, usd_amount=None, usd_note: str='', usd_only: bool=False, source_finance_text: str=''):
    if not callable(_V262_BASE_ADD_RECORD):
        return None
    rec = _V262_BASE_ADD_RECORD(int(chat_id), amount, note, owner, source_msg=source_msg, day_key=day_key, usd_amount=usd_amount, usd_note=usd_note, usd_only=usd_only, source_finance_text=source_finance_text)
    if isinstance(rec, dict):
        _ensure_finance_origin_key_v262(int(chat_id), rec, _v262_int(getattr(source_msg, 'message_id', 0) if source_msg is not None else 0))
    return rec


def _v260_bind_forward_finance_record(rec: dict, source_msg, dst_chat_id: int, dst_msg_id: int) -> dict:
    if callable(_V262_BASE_BIND_FORWARD):
        rec = _V262_BASE_BIND_FORWARD(rec, source_msg, int(dst_chat_id), int(dst_msg_id))
    if isinstance(rec, dict):
        _ensure_finance_origin_key_v262(int(dst_chat_id), rec, int(dst_msg_id))
    return rec


def _v262_records_for_origin(chat_id: int, origin_key: str):
    store = get_chat_store(int(chat_id))
    seen = set()
    rows = []
    for list_key in ('records', 'ars_records', 'usd_records'):
        for rec in store.get(list_key, []) or []:
            if not isinstance(rec, dict) or id(rec) in seen:
                continue
            seen.add(id(rec))
            if _ensure_finance_origin_key_v262(int(chat_id), rec) == origin_key:
                rows.append((list_key, rec))
    return rows


def _v262_find_anchor_record(chat_id: int, rid: int | None=None, source_msg_id: int | None=None):
    cid = int(chat_id)
    if source_msg_id:
        try:
            rec = find_record_by_message_id(cid, int(source_msg_id))
            if isinstance(rec, dict) and (rid is None or _v262_int(rec.get('id'), -1) == int(rid)):
                return rec
        except Exception:
            pass
    try:
        store = get_chat_store(cid)
        for key in ('records', 'ars_records', 'usd_records'):
            for rec in store.get(key, []) or []:
                if isinstance(rec, dict) and (rid is None or _v262_int(rec.get('id'), -1) == int(rid)):
                    return rec
    except Exception:
        pass
    return None


def _v262_float_text(value) -> str:
    try:
        x = float(value or 0)
    except Exception:
        return '0'
    if x.is_integer():
        return str(int(x))
    return ('%.6f' % x).rstrip('0').rstrip('.')


def _v262_input_amount_text(value) -> str:
    """Convert internal finance sign back to user input sign semantics.

    Internally expenses are negative, while Telegram input writes an expense without
    a minus. Incomes are positive and must be rendered with an explicit +.
    """
    try:
        x = float(value or 0)
    except Exception:
        x = 0.0
    base = _v262_float_text(abs(x))
    if x > 0:
        return '+' + base
    return base


def _v262_record_canonical_text(rec: dict) -> str:
    amount = float((rec or {}).get('amount') or 0)
    note = str((rec or {}).get('note') or '').strip()
    usd_amount = float((rec or {}).get('usd_amount') or 0)
    usd_note = str((rec or {}).get('usd_note') or '').strip()
    usd_only = bool((rec or {}).get('usd_only', False))
    parts = []
    if (not usd_only) or amount:
        parts.append((_v262_input_amount_text(amount) + (' ' + note if note else '')).strip())
    if usd_amount or usd_only:
        low_note = usd_note.casefold()
        if low_note == 'usd' or low_note.startswith('usd '):
            usd_part = _v262_input_amount_text(usd_amount) + (' ' + usd_note if usd_note else '')
        else:
            usd_part = _v262_input_amount_text(usd_amount) + ' USD' + (' ' + usd_note if usd_note else '')
        parts.append(usd_part.strip())
    return ' '.join((p for p in parts if p)).strip()


def _v262_update_one_record(rec: dict, *, update_ars: bool, amount=None, note=None, replace_usd: bool=False, usd_amount=None, usd_note=None, usd_only=None, source_text: str | None=None, full_text_replace: bool=False):
    before = _v262_copy.deepcopy(rec)
    if update_ars:
        rec['amount'] = float(amount or 0)
        rec['note'] = str(note or '')
    if replace_usd:
        if usd_amount is None:
            rec['usd_amount'] = 0.0
            rec['usd_note'] = ''
            rec['usd_only'] = False
        else:
            rec['usd_amount'] = float(usd_amount or 0)
            rec['usd_note'] = str(usd_note or '')
            rec['usd_only'] = bool(usd_only)
    if full_text_replace and source_text is not None:
        rec['source_finance_text'] = str(source_text or '').strip()
    elif update_ars or replace_usd:
        rec['source_finance_text'] = _v262_record_canonical_text(rec)
    return before


def _v262_shadow_source_message(origin_chat_id: int, origin_msg_id: int, anchor_rec: dict):
    chat_obj = type('V262SourceChat', (), {'id': int(origin_chat_id)})()
    owner = _v262_int((anchor_rec or {}).get('owner'))
    user_obj = type('V262SourceUser', (), {'id': int(owner)})()
    dt = None
    try:
        raw = str((anchor_rec or {}).get('timestamp') or '')
        if raw:
            dt = _v262_datetime.datetime.fromisoformat(raw)
    except Exception:
        dt = None
    if dt is None:
        try:
            dt = now_local()
        except Exception:
            dt = _v262_datetime.datetime.now()
    return type('V262SourceMessage', (), {
        'message_id': int(origin_msg_id),
        'source_order_msg_id': int(origin_msg_id),
        'date': dt,
        'chat': chat_obj,
        'from_user': user_obj,
    })()


def _v262_heal_missing_source(origin_chat_id: int, origin_msg_id: int, origin_key: str, anchor_rec: dict, *, update_ars: bool, amount=None, note=None, replace_usd: bool=False, usd_amount=None, usd_note=None, usd_only=None, source_text: str | None=None):
    if not (origin_chat_id and origin_msg_id and callable(globals().get('is_finance_mode'))):
        return None
    try:
        if not is_finance_mode(int(origin_chat_id)):
            return None
    except Exception:
        return None
    try:
        source_store = get_chat_store(int(origin_chat_id))
        active_existing = next((r for r in source_store.get('records', []) or [] if isinstance(r, dict) and callable(globals().get('_record_has_message_id')) and _record_has_message_id(r, int(origin_msg_id))), None)
        if isinstance(active_existing, dict):
            return active_existing
        # A deployment can restore the currency mirror while the active records list is stale.
        # Promote that exact source row back to active instead of creating a second operation.
        active_ledger = _ensure_currency_ledgers(source_store) if callable(globals().get('_ensure_currency_ledgers')) else 'ars'
        mirror_rows = source_store.get(f'{active_ledger}_records', []) or []
        mirror = next((r for r in mirror_rows if isinstance(r, dict) and callable(globals().get('_record_has_message_id')) and _record_has_message_id(r, int(origin_msg_id))), None)
        if isinstance(mirror, dict):
            restored = _v262_copy.deepcopy(mirror)
            restored['finance_origin_key_v262'] = origin_key
            restored['finance_origin_chat_id_v262'] = int(origin_chat_id)
            restored['finance_origin_msg_id_v262'] = int(origin_msg_id)
            source_store.setdefault('records', []).append(restored)
            normalize_chat_records(int(origin_chat_id))
            persist_finance_chat_local_fast(int(origin_chat_id))
            return find_record_by_message_id(int(origin_chat_id), int(origin_msg_id))
    except Exception:
        pass
    # Recreate only when the source chat itself is a finance chat. This heals the
    # exact post-deploy case without inventing finance in a non-finance sender chat.
    base_amount = float(amount or 0) if update_ars else float((anchor_rec or {}).get('amount') or 0)
    base_note = str(note or '') if update_ars else str((anchor_rec or {}).get('note') or '')
    if replace_usd:
        base_usd = None if usd_amount is None else float(usd_amount or 0)
        base_usd_note = '' if usd_amount is None else str(usd_note or '')
        base_usd_only = False if usd_amount is None else bool(usd_only)
    else:
        base_usd = (anchor_rec or {}).get('usd_amount') if (anchor_rec or {}).get('usd_amount') is not None else None
        base_usd_note = str((anchor_rec or {}).get('usd_note') or '')
        base_usd_only = bool((anchor_rec or {}).get('usd_only', False))
    day_key = str((anchor_rec or {}).get('day_key') or '') or None
    msg = _v262_shadow_source_message(int(origin_chat_id), int(origin_msg_id), anchor_rec or {})
    try:
        rec = add_record_to_chat(int(origin_chat_id), base_amount, base_note, _v262_int((anchor_rec or {}).get('owner')), source_msg=msg, day_key=day_key, usd_amount=base_usd, usd_note=base_usd_note, usd_only=base_usd_only, source_finance_text=str(source_text or _v262_record_canonical_text({'amount': base_amount, 'note': base_note, 'usd_amount': base_usd or 0, 'usd_note': base_usd_note, 'usd_only': base_usd_only})))
        if isinstance(rec, dict):
            rec['finance_origin_key_v262'] = origin_key
            rec['finance_origin_chat_id_v262'] = int(origin_chat_id)
            rec['finance_origin_msg_id_v262'] = int(origin_msg_id)
            try:
                bot_journal('finance_origin_healed_v262', int(origin_chat_id), f'origin={origin_key}; record=R{rec.get("id")}; reason=linked_edit_missing_source')
            except Exception:
                pass
            return rec
    except Exception as exc:
        try:
            log_error(f'v262 heal source {origin_key}: {exc}')
        except Exception:
            pass
    return None


def _v262_linked_locations(origin_chat_id: int, origin_msg_id: int, anchor_chat_id: int, anchor_rec: dict):
    locations = {(int(anchor_chat_id), _v262_int((anchor_rec or {}).get('forward_dst_msg_id') or (anchor_rec or {}).get('source_msg_id') or (anchor_rec or {}).get('msg_id')))}
    if origin_chat_id and origin_msg_id:
        locations.add((int(origin_chat_id), int(origin_msg_id)))
        try:
            for dst_chat, dst_msg in get_forward_links(int(origin_chat_id), int(origin_msg_id)) or []:
                locations.add((int(dst_chat), int(dst_msg)))
        except Exception:
            pass
    return sorted(locations, key=lambda x: (x[0], x[1]))


def _v262_background_repaint_copies(origin_chat_id: int, origin_msg_id: int):
    try:
        links = list(get_forward_links(int(origin_chat_id), int(origin_msg_id)) or [])
    except Exception:
        links = []
    for dst_chat_id, dst_msg_id in links:
        try:
            rec = find_record_by_message_id(int(dst_chat_id), int(dst_msg_id))
            if not isinstance(rec, dict):
                continue
            text = str(rec.get('source_finance_text') or _v262_record_canonical_text(rec))
            mode = forward_copy_edit_mode(int(dst_chat_id)) if callable(globals().get('forward_copy_edit_mode')) else 'slash'
            display = _forward_copy_display_text(text, rec, mode) if callable(globals().get('_forward_copy_display_text')) else text
            kb = _forward_copy_edit_keyboard(mode) if callable(globals().get('_forward_copy_edit_keyboard')) else None
            ct = str(rec.get('forward_copy_content_type') or 'text')
            if ct == 'text':
                _tg_call_retry(bot.edit_message_text, display, chat_id=int(dst_chat_id), message_id=int(dst_msg_id), reply_markup=kb, attempts=1, purpose='finance_linked_repaint_v262')
            elif ct in {'photo', 'video', 'document', 'audio', 'animation', 'voice'}:
                _tg_call_retry(bot.edit_message_caption, caption=display, chat_id=int(dst_chat_id), message_id=int(dst_msg_id), reply_markup=kb, attempts=1, purpose='finance_linked_repaint_v262')
        except Exception as exc:
            if 'message is not modified' not in str(exc).lower():
                try:
                    log_error(f'v262 linked repaint {dst_chat_id}:{dst_msg_id}: {exc}')
                except Exception:
                    pass


def _v262_postcommit_linked_edit(origin_chat_id: int, origin_msg_id: int, touched_days: dict, repaint_copies: bool):
    try:
        if callable(globals().get('rebuild_global_records')):
            rebuild_global_records()
    except Exception:
        pass
    for cid, day_key in list((touched_days or {}).items()):
        try:
            if callable(globals().get('finance_changed')):
                finance_changed(int(cid), str(day_key or ''), reason='linked_edit_v262', delay=0.05)
        except Exception:
            pass
    if repaint_copies and origin_chat_id and origin_msg_id:
        _v262_background_repaint_copies(int(origin_chat_id), int(origin_msg_id))


def apply_linked_finance_edit_v262(anchor_chat_id: int, anchor_rec: dict, *, update_ars: bool=True, amount=None, note=None, replace_usd: bool=False, usd_amount=None, usd_note=None, usd_only=None, source_text: str | None=None, full_text_replace: bool=False, repaint_copies: bool=True, source_kind: str='edit') -> bool:
    """Atomically mutate all locally known rows for one Telegram-origin operation.

    Local SQLite is committed before returning. Heavy window repaint, Google/MEGA/delta and
    copy rendering are allowed to run on the established background paths.
    """
    if not isinstance(anchor_rec, dict):
        return False
    try:
        if globals().get('constitution_finance_write_blocked_v232') and constitution_finance_write_blocked_v232():
            return False
    except Exception:
        pass
    anchor_chat_id = int(anchor_chat_id)
    origin_chat_id, origin_msg_id, origin_key = finance_origin_identity_v262(anchor_chat_id, anchor_rec)
    if not origin_key:
        return False
    op_id = ''
    try:
        if callable(globals().get('operation_begin')):
            op_id = operation_begin('finance_linked_edit_v262', anchor_chat_id, target=origin_key, payload={'source': source_kind, 'update_ars': bool(update_ars), 'replace_usd': bool(replace_usd)}, critical=True)
    except Exception:
        op_id = ''
    touched_days = {}
    changed_total = 0
    changed_by_chat = {}
    with _V262_FINANCE_LINK_LOCK:
        _ensure_finance_origin_key_v262(anchor_chat_id, anchor_rec)
        try:
            source_store = get_chat_store(int(origin_chat_id)) if origin_chat_id and origin_msg_id else {}
            source_rec = next((r for r in source_store.get('records', []) or [] if isinstance(r, dict) and callable(globals().get('_record_has_message_id')) and _record_has_message_id(r, int(origin_msg_id))), None)
        except Exception:
            source_rec = None
        if not isinstance(source_rec, dict):
            source_rec = _v262_heal_missing_source(origin_chat_id, origin_msg_id, origin_key, anchor_rec, update_ars=update_ars, amount=amount, note=note, replace_usd=replace_usd, usd_amount=usd_amount, usd_note=usd_note, usd_only=usd_only, source_text=source_text)
        locations = _v262_linked_locations(origin_chat_id, origin_msg_id, anchor_chat_id, anchor_rec)
        target_chats = {int(cid) for cid, _mid in locations if cid}
        target_chats.add(anchor_chat_id)
        if origin_chat_id:
            target_chats.add(int(origin_chat_id))
        for cid in sorted(target_chats):
            try:
                with locked_chat(int(cid)):
                    _v262_tag_store_origins(int(cid))
                    rows = _v262_records_for_origin(int(cid), origin_key)
                    if not rows:
                        # Exact message fallback keeps old pre-v260 rows editable.
                        for loc_cid, loc_mid in locations:
                            if int(loc_cid) != int(cid) or not loc_mid:
                                continue
                            rec = find_record_by_message_id(int(cid), int(loc_mid))
                            if isinstance(rec, dict):
                                rec['finance_origin_key_v262'] = origin_key
                                rec['finance_origin_chat_id_v262'] = int(origin_chat_id)
                                rec['finance_origin_msg_id_v262'] = int(origin_msg_id)
                                rows = _v262_records_for_origin(int(cid), origin_key)
                                if rows:
                                    break
                    if not rows:
                        continue
                    before_primary = None
                    changed_here = 0
                    try:
                        _active_before = sum(float(r.get('amount', 0) or 0) for r in get_chat_store(int(cid)).get('records', []) or [] if isinstance(r, dict) and _ensure_finance_origin_key_v262(int(cid), r) == origin_key)
                        _usd_before = sum(float(r.get('usd_amount', 0) or 0) for r in get_chat_store(int(cid)).get('records', []) or [] if isinstance(r, dict) and _ensure_finance_origin_key_v262(int(cid), r) == origin_key)
                    except Exception:
                        _active_before = 0.0; _usd_before = 0.0
                    for _ledger, rec in rows:
                        before = _v262_update_one_record(rec, update_ars=update_ars, amount=amount, note=note, replace_usd=replace_usd, usd_amount=usd_amount, usd_note=usd_note, usd_only=usd_only, source_text=source_text, full_text_replace=full_text_replace)
                        _ensure_finance_origin_key_v262(int(cid), rec)
                        if before != rec:
                            changed_here += 1
                            if before_primary is None:
                                before_primary = before
                    store = get_chat_store(int(cid))
                    # Keep daily mirrors/currency mirrors coherent even if they are separate objects.
                    for daily_key in ('daily_records', 'ars_daily_records', 'usd_daily_records'):
                        for _dk, arr in (store.get(daily_key, {}) or {}).items():
                            for rec in arr or []:
                                if isinstance(rec, dict) and _ensure_finance_origin_key_v262(int(cid), rec) == origin_key:
                                    _v262_update_one_record(rec, update_ars=update_ars, amount=amount, note=note, replace_usd=replace_usd, usd_amount=usd_amount, usd_note=usd_note, usd_only=usd_only, source_text=source_text, full_text_replace=full_text_replace)
                    try:
                        active = _ensure_currency_ledgers(store)
                        _snapshot_active_currency_ledger(store, active)
                    except Exception:
                        pass
                    # R16: edit only the touched operation. Avoid normalize/sort/short-id rebuild
                    # and a full balance sum in the Telegram hot transaction.
                    try:
                        _active_after = sum(float(r.get('amount', 0) or 0) for r in store.get('records', []) or [] if isinstance(r, dict) and _ensure_finance_origin_key_v262(int(cid), r) == origin_key)
                        store['balance'] = float(store.get('balance', 0) or 0) + (_active_after - _active_before)
                    except Exception:
                        pass
                    store['_finance_hotpath_pending_normalize_r16'] = True
                    store['_finance_fast_generation_r16'] = int(store.get('_finance_fast_generation_r16', 0) or 0) + 1
                    store.pop('_finance_day_balance_cache_r16', None)
                    if replace_usd and '_usd_balance_cache_r16' in store:
                        try:
                            _usd_after = sum(float(r.get('usd_amount', 0) or 0) for r in store.get('records', []) or [] if isinstance(r, dict) and _ensure_finance_origin_key_v262(int(cid), r) == origin_key)
                            store['_usd_balance_cache_r16'] = float(store.get('_usd_balance_cache_r16', 0) or 0) + (_usd_after - _usd_before)
                        except Exception: store.pop('_usd_balance_cache_r16', None)
                    current = _v262_records_for_origin(int(cid), origin_key)
                    primary = current[0][1] if current else rows[0][1]
                    touched_days[int(cid)] = str(primary.get('day_key') or store.get('current_view_day') or today_key())
                    _r48_primary = copy.deepcopy(primary) if isinstance(primary, dict) else primary
                    _r48_before_primary = copy.deepcopy(before_primary or {})
                    _r48_changed_here = int(changed_here or 0)
                if not persist_finance_chat_local_fast(int(cid)):
                    raise RuntimeError('local SQLite finance persist failed')
                if _r48_changed_here:
                    changed_total += _r48_changed_here
                    changed_by_chat[int(cid)] = _r48_changed_here
                    try: finance_cache_invalidate(int(cid), 'linked_edit_v262')
                    except Exception: pass
                    try: finance_integrity_append(int(cid), 'edit', _r48_primary, details={'before': _r48_before_primary, 'source': source_kind, 'origin_key': origin_key})
                    except Exception as exc:
                        try: log_error(f'v262 finance integrity {cid}: {exc}')
                        except Exception: pass
            except Exception as exc:
                try:
                    log_error(f'v262 linked edit {origin_key} chat={cid}: {exc}')
                except Exception:
                    pass
                if op_id and callable(globals().get('operation_review')):
                    try: operation_review(op_id, f'chat={cid}: {exc}')
                    except Exception: pass
                return False
    # No-op is success: repeated Telegram delivery must never create a duplicate.
    try:
        bot_journal('finance_linked_edit_v262', anchor_chat_id, f'origin={origin_key}; source={source_kind}; chats={len(touched_days)}; changed={changed_total}; per_chat={changed_by_chat}')
    except Exception:
        pass
    try:
        pool = globals().get('GENERAL_TASK_POOL') or globals().get('FINANCE_TASK_POOL')
        key = f'v262-linked-post:{origin_chat_id}:{origin_msg_id}'
        if pool is not None and hasattr(pool, 'submit'):
            # Ordered per-origin queue: a fast second edit must not lose its final repaint.
            pool.submit(key, _v262_postcommit_linked_edit, int(origin_chat_id), int(origin_msg_id), dict(touched_days), bool(repaint_copies))
        else:
            _v262_postcommit_linked_edit(int(origin_chat_id), int(origin_msg_id), dict(touched_days), bool(repaint_copies))
    except Exception:
        pass
    if op_id and callable(globals().get('operation_complete')):
        try:
            operation_complete(op_id, f'origin={origin_key}; chats={len(touched_days)}; changed={changed_total}')
        except Exception:
            pass
    return True


def update_record_in_chat(chat_id: int, rid: int, amount: float, note: str, source_finance_text: str | None=None, source_msg_id: int | None=None) -> bool:
    bot_journal('record_update_start', int(chat_id), f'rid={rid} amount={amount} note={note} msg={source_msg_id or ""} linked=v262')
    anchor = _v262_find_anchor_record(int(chat_id), int(rid), int(source_msg_id) if source_msg_id else None)
    if not isinstance(anchor, dict):
        return False
    return apply_linked_finance_edit_v262(int(chat_id), anchor, update_ars=True, amount=float(amount or 0), note=str(note or ''), replace_usd=False, source_text=source_finance_text, full_text_replace=False, repaint_copies=True, source_kind='record_edit')


def edit_forward_copy_and_record(chat_id: int, dst_msg_id: int, new_text: str) -> bool:
    clean_text = sanitize_telegram_inserted_text(str(new_text or '').strip())
    try:
        comp = parse_financial_components(clean_text)
    except Exception:
        return False
    rec = find_record_by_message_id(int(chat_id), int(dst_msg_id))
    if not isinstance(rec, dict):
        return False
    try:
        is_copy, _mid, source_chat_id, source_msg_id = _forward_copy_record_identity(int(chat_id), rec)
        if not is_copy:
            return False
        _hydrate_legacy_forward_copy_metadata(int(chat_id), rec, int(dst_msg_id), source_chat_id, source_msg_id)
    except Exception:
        return False
    ok = apply_linked_finance_edit_v262(int(chat_id), rec, update_ars=True, amount=float(comp.get('amount') or 0), note=str(comp.get('note') or ''), replace_usd=True, usd_amount=comp.get('usd_amount'), usd_note=str(comp.get('usd_note') or ''), usd_only=bool(comp.get('usd_only', False)), source_text=str(comp.get('source_finance_text') or clean_text), full_text_replace=True, repaint_copies=True, source_kind='slash_forward_copy')
    if ok:
        try:
            _durable_note_source_consumed('forward_copy_manual_edit_v262')
        except Exception:
            pass
    return bool(ok)


def handle_finance_edit(msg):
    """Native Telegram long-tap edit uses the same linked-edit transaction."""
    chat_id = int(msg.chat.id)
    try:
        uid = _v262_int(getattr(getattr(msg, 'from_user', None), 'id', 0))
        if 'v152_chat_permission_allowed' in globals() and '_v152_actor_is_platform_owner' in globals():
            if not _v152_actor_is_platform_owner(uid) and (not v152_chat_permission_allowed(chat_id, 'finance.edit')):
                try: send_and_auto_delete(chat_id, '⛔ Редактирование операций запрещено правами этого чата.', 8)
                except Exception: pass
                return False
    except Exception:
        pass
    try:
        if globals().get('constitution_finance_write_blocked_v232') and constitution_finance_write_blocked_v232():
            return True
    except Exception:
        pass
    text = str(getattr(msg, 'text', None) or getattr(msg, 'caption', None) or '').strip()
    target = find_record_by_message_id(chat_id, int(msg.message_id)) if callable(globals().get('find_record_by_message_id')) else None
    if not isinstance(target, dict):
        try:
            store = get_chat_store(chat_id)
            for rec in store.get('records', []) or []:
                if isinstance(rec, dict) and int(msg.message_id) in {_v262_int(rec.get(k)) for k in ('source_msg_id', 'origin_msg_id', 'msg_id', 'source_order_msg_id')}:
                    target = rec
                    break
        except Exception:
            pass
    if not isinstance(target, dict):
        try: log_info(f'[EDIT-FIN v262] record not found msg={msg.message_id}')
        except Exception: pass
        return False
    if text and looks_like_amount(text):
        try:
            comp = parse_financial_components(text)
        except Exception:
            comp = {'amount': 0.0, 'note': 'удалено', 'usd_amount': None, 'usd_note': '', 'usd_only': False, 'source_finance_text': text}
    else:
        comp = {'amount': 0.0, 'note': 'удалено', 'usd_amount': None, 'usd_note': '', 'usd_only': False, 'source_finance_text': text}
    return apply_linked_finance_edit_v262(chat_id, target, update_ars=True, amount=float(comp.get('amount') or 0), note=str(comp.get('note') or ''), replace_usd=True, usd_amount=comp.get('usd_amount'), usd_note=str(comp.get('usd_note') or ''), usd_only=bool(comp.get('usd_only', False)), source_text=str(comp.get('source_finance_text') or text), full_text_replace=True, repaint_copies=False, source_kind='telegram_native_edit')


def _v262_finance_postcommit_job(chat_id: int, day_key: str, reason: str):
    try:
        if callable(globals().get('rebuild_global_records')):
            rebuild_global_records()
    except Exception:
        pass
    try:
        if callable(globals().get('schedule_financial_window_refresh')):
            schedule_financial_window_refresh(int(chat_id), str(day_key or ''), reason=str(reason or 'finance_postcommit_v262'))
    except Exception:
        pass
    try:
        if callable(globals().get('finance_changed')):
            finance_changed(int(chat_id), str(day_key or ''), reason=str(reason or 'finance_postcommit_v262'), delay=0.05)
    except Exception:
        pass


def _v262_schedule_finance_postcommit(chat_id: int, day_key: str, reason: str='finance_postcommit_v262'):
    cid = int(chat_id); key = f'v262-fin-post:{cid}'
    try:
        pool = globals().get('FINANCE_TASK_POOL') or globals().get('GENERAL_TASK_POOL')
        if pool is not None and hasattr(pool, 'submit') and pool.submit(key, _v262_finance_postcommit_job, cid, str(day_key or ''), str(reason or 'finance_postcommit_v262')):
            return True
    except Exception:
        pass
    try:
        DELAYED_SCHEDULER.schedule(key, 0.05, _v262_finance_postcommit_job, cid, str(day_key or ''), str(reason or 'finance_postcommit_v262'))
        return True
    except Exception:
        return False


def _v262_async_chat_persist(chat_id: int):
    cid = int(chat_id)
    try:
        persist_finance_chat_local_fast(cid)
    finally:
        with _V262_TRANSIENT_PERSIST_LOCK:
            _V262_TRANSIENT_PERSIST_PENDING.discard(cid)


def _v262_schedule_transient_chat_persist(chat_id: int):
    cid = int(chat_id)
    with _V262_TRANSIENT_PERSIST_LOCK:
        if cid in _V262_TRANSIENT_PERSIST_PENDING:
            return
        _V262_TRANSIENT_PERSIST_PENDING.add(cid)
    try:
        pool = globals().get('GENERAL_TASK_POOL')
        if pool is not None and hasattr(pool, 'submit_unique') and pool.submit_unique(f'v262-transient-chat:{cid}', _v262_async_chat_persist, cid):
            return
    except Exception:
        pass
    try:
        DELAYED_SCHEDULER.schedule(f'v262-transient-chat:{cid}', 0.25, _v262_async_chat_persist, cid)
    except Exception:
        _v262_async_chat_persist(cid)


def toggle_usd_edit_delete_selection(chat_id: int, day_key: str, rid: int):
    store = get_chat_store(int(chat_id)); all_sel = store.setdefault('usd_edit_delete_selected', {})
    selected = {int(x) for x in all_sel.get(str(day_key), []) or []}; rid = int(rid)
    selected.discard(rid) if rid in selected else selected.add(rid)
    if selected: all_sel[str(day_key)] = sorted(selected)
    else: all_sel.pop(str(day_key), None)


def clear_usd_edit_delete_selection(chat_id: int, day_key: str | None=None):
    all_sel = get_chat_store(int(chat_id)).setdefault('usd_edit_delete_selected', {})
    all_sel.clear() if day_key is None else all_sel.pop(str(day_key), None)


def toggle_edit_delete_selection(chat_id: int, day_key: str, rid: int):
    store = get_chat_store(int(chat_id)); all_sel = store.setdefault('edit_delete_selected', {})
    selected = {int(x) for x in all_sel.get(str(day_key), []) or []}; rid = int(rid)
    selected.discard(rid) if rid in selected else selected.add(rid)
    if selected: all_sel[str(day_key)] = sorted(selected)
    else: all_sel.pop(str(day_key), None)


def clear_edit_delete_selection(chat_id: int, day_key: str | None=None):
    all_sel = get_chat_store(int(chat_id)).setdefault('edit_delete_selected', {})
    all_sel.clear() if day_key is None else all_sel.pop(str(day_key), None)


def set_usd_transactions_view(chat_id: int, enabled: bool):
    """Display preference: apply instantly, persist chat asynchronously, never config-checkpoint it."""
    store = get_chat_store(int(chat_id))
    store.setdefault('settings', {})['usd_transactions_view'] = bool(enabled)
    _v262_schedule_transient_chat_persist(int(chat_id))


def _v262_nav_mirror_drain(key):
    try:
        while True:
            with _V262_NAV_MIRROR_LOCK:
                q = _V262_NAV_MIRROR_QUEUES.get(key)
                if not q:
                    _V262_NAV_MIRROR_QUEUES.pop(key, None)
                    _V262_NAV_MIRROR_RUNNING.discard(key)
                    return
                action, payload = q.popleft()
            try:
                if action == 'push':
                    fn = globals().get('kv_nav_push_v248')
                    if callable(fn): fn(int(key[0]), int(key[1]), payload, _WINDOW_NAV_HISTORY_LIMIT)
                elif action == 'pop':
                    fn = globals().get('kv_nav_pop_v248')
                    if callable(fn): fn(int(key[0]), int(key[1]))
                elif action == 'clear':
                    fn = globals().get('kv_nav_clear_v248')
                    if callable(fn): fn(int(key[0]), int(key[1]))
            except Exception:
                pass
    finally:
        with _V262_NAV_MIRROR_LOCK:
            _V262_NAV_MIRROR_RUNNING.discard(key)


def _v262_nav_mirror_enqueue(key, action: str, payload=None):
    key = (int(key[0]), int(key[1]))
    start = False
    with _V262_NAV_MIRROR_LOCK:
        _V262_NAV_MIRROR_QUEUES[key].append((str(action), payload))
        if key not in _V262_NAV_MIRROR_RUNNING:
            _V262_NAV_MIRROR_RUNNING.add(key); start = True
    if not start:
        return
    try:
        pool = globals().get('GENERAL_TASK_POOL')
        if pool is not None and hasattr(pool, 'submit_unique') and pool.submit_unique(f'v262-nav-mirror:{key[0]}:{key[1]}', _v262_nav_mirror_drain, key):
            return
    except Exception:
        pass
    # No UI-thread network fallback: drop only the optional mirror, not navigation itself.
    with _V262_NAV_MIRROR_LOCK:
        _V262_NAV_MIRROR_RUNNING.discard(key)


def _nav_history_push_v248(key, snap: dict) -> bool:
    key = (int(key[0]), int(key[1]))
    with _WINDOW_NAV_HISTORY_LOCK:
        stack = _WINDOW_NAV_HISTORY[key]
        if stack and stack[-1].get('text') == snap.get('text') and stack[-1].get('markup') == snap.get('markup'):
            return True
        stack.append(snap)
        if len(stack) > _WINDOW_NAV_HISTORY_LIMIT:
            del stack[:-_WINDOW_NAV_HISTORY_LIMIT]
    _v262_nav_mirror_enqueue(key, 'push', dict(snap))
    return True


def _nav_history_pop_v248(key) -> bool:
    key = (int(key[0]), int(key[1]))
    with _WINDOW_NAV_HISTORY_LOCK:
        stack = _WINDOW_NAV_HISTORY.get(key) or []
        if stack:
            stack.pop()
            if not stack: _WINDOW_NAV_HISTORY.pop(key, None)
            _v262_nav_mirror_enqueue(key, 'pop')
            return True
    # Rare post-restart fallback only; normal UI never waits for KV.
    fn = globals().get('kv_nav_pop_v248')
    if callable(fn):
        try: return bool(fn(int(key[0]), int(key[1])))
        except Exception: pass
    return False


def _nav_history_clear_v248(chat_id: int, message_id: int) -> None:
    key = (int(chat_id), int(message_id))
    with _WINDOW_NAV_HISTORY_LOCK:
        _WINDOW_NAV_HISTORY.pop(key, None)
    _v262_nav_mirror_enqueue(key, 'clear')


def window_has_previous(chat_id: int, message_id: int) -> bool:
    """Hot render path is RAM-only; nav_prev itself can still use KV after a restart."""
    key = (int(chat_id), int(message_id))
    with _WINDOW_NAV_HISTORY_LOCK:
        return bool(_WINDOW_NAV_HISTORY.get(key))


def _v234_config_projection_from_payload(payload: dict) -> dict:
    """v262 removes view/lifecycle telemetry from Configuration Constitution."""
    if callable(_V262_BASE_CONFIG_PROJECTION):
        projected = _V262_BASE_CONFIG_PROJECTION(payload)
    else:
        projected = {'root': {}, 'chats': {}}
    chats = (projected or {}).get('chats') or {}
    for _cid, row in chats.items():
        if not isinstance(row, dict):
            continue
        settings = row.get('settings')
        if isinstance(settings, dict):
            for key in ('usd_transactions_view', 'finance_window_page', 'finance_window_mode', 'current_view_day', 'edit_delete_selected', 'usd_edit_delete_selected'):
                settings.pop(key, None)
        life = row.get('chat_lifecycle_v150')
        if isinstance(life, dict):
            # Status/migration are configuration. Heartbeat timestamps/counters are runtime state.
            for key in ('last_seen_at', 'last_success_at', 'last_failure_at', 'last_error', 'consecutive_failures', 'probe_count', 'updated_at'):
                life.pop(key, None)
    return projected


# Keep the explicit exclusion set consistent for restore-side preservation too.
try:
    _V234_CHAT_SETTINGS_EXCLUDE = set(_V234_CHAT_SETTINGS_EXCLUDE) | {
        'usd_transactions_view', 'finance_window_page', 'finance_window_mode',
        'current_view_day', 'edit_delete_selected', 'usd_edit_delete_selected'
    }
except Exception:
    pass

# Make the current release visible in owner mode text without changing mode semantics.
try:
    _V262_BASE_STORAGE_MODES_TEXT = globals().get('storage_modes_text_v240')
    if callable(_V262_BASE_STORAGE_MODES_TEXT):
        def storage_modes_text_v240() -> str:
            return str(_V262_BASE_STORAGE_MODES_TEXT()).replace('РЕЖИМЫ · выс-260', 'РЕЖИМЫ · выс-262')
except Exception:
    pass

try:
    bot_journal('v262_linked_finance_fast_ui_ready', int(globals().get('OWNER_ID') or 0), 'finance_origin=1; linked_edits=telegram/slash/window; source_heal=finance_only; nav_ram_first=1; transient_ui_async=1; config_runtime_excluded=1')
except Exception:
    pass

# --- ИСТОЧНИК: 98_split_front.py ---
"""Render #1 fast split bridge for vys-262.

Render #1 keeps Telegram/webhook/UI and the working SQLite commit path.
Remote durability and Google Sheets network work are delegated to Render #2.
MEGA is disabled during normal runtime on the front; start_front.py keeps only the
cold emergency restore path for deploy/startup recovery.
"""
import gzip as _split_gzip
import json as _split_json
import base64 as _split_base64
import hashlib as _split_hashlib
import collections as _split_collections
import os as _split_os
import secrets as _split_secrets
import shutil as _split_shutil
import tempfile as _split_tempfile
import threading as _split_threading
import time as _split_time
try:
    import redis as _split_redis
except Exception:
    _split_redis = None

_SPLIT_FRONT_VERSION = "vys-262-front-per-r24-ordered-hot-ram-fast"
_SPLIT_SYNC_LOCK = _split_threading.RLock()
_SPLIT_SYNC_TIMER = None
_SPLIT_SYNC_DUE_AT = 0.0
_SPLIT_SYNC_FIRST_DIRTY_AT = 0.0
_SPLIT_LAST_CHANGE_AT = _split_time.time()
_SPLIT_FULL_LOCK = _split_threading.RLock()
_SPLIT_FULL_TIMER = None
_SPLIT_CONTINUITY_LOCK = _split_threading.RLock()
_SPLIT_CONTINUITY_TIMER = None
_SPLIT_CONTINUITY_CHAT_ID = None
_SPLIT_CONTINUITY_REASON = ''
_SPLIT_CONTINUITY_FIRST_DIRTY_AT = 0.0
_SPLIT_CHANGE_LOCK = _split_threading.RLock()
_SPLIT_CHANGE_EPOCH = _split_secrets.token_hex(6)
_SPLIT_CHANGE_SEQ = 0
_SPLIT_STATE_TOKEN = f"{_SPLIT_CHANGE_EPOCH}:0"
_SPLIT_UPDATE_CONTEXT = _split_threading.local()
_SPLIT_GOOGLE_RESULT_LOCK = _split_threading.RLock()
_SPLIT_GOOGLE_RESULTS = {}
_SPLIT_STATE = {
    "peer_last_attempt": 0.0,
    "peer_last_ok": 0.0,
    "peer_last_error": "",
    "peer_status": None,
    "worker_health": {},
    "sync_last_attempt": 0.0,
    "sync_last_ok": 0.0,
    "sync_last_error": "",
    "sync_pending": False,
    "sync_reason": "",
    "google_last_attempt": 0.0,
    "google_last_ok": 0.0,
    "google_last_error": "",
    "google_last_job": "",
    "state_token": _SPLIT_STATE_TOKEN,
    "state_change_reason": "boot",
    "redis_fallback_last_ok": 0.0,
    "redis_fallback_last_error": "",
    "delta_last_ok": 0.0,
    "delta_last_error": "",
    "delta_last_bytes": 0,
    "delta_last_pages": 0,
    "delta_total_bytes": 0,
    "delta_total_pages": 0,
    "delta_full_fallbacks": 0,
    "full_reconcile_pending": False,
    "full_reconcile_last_ok": 0.0,
    "full_reconcile_last_error": "",
    "delta_baseline_sha256": "",
    "event_last_receipt_ok": 0.0,
    "event_last_commit_ok": 0.0,
    "event_last_error": "",
    "event_received": 0,
    "event_committed": 0,
    "event_mirrored": 0,
    "event_redis_fallbacks": 0,
    "event_recovered": 0,
    "capsule_last_attempt": 0.0,
    "capsule_last_ok": 0.0,
    "capsule_last_error": "",
    "capsule_last_seq": 0,
    "capsule_last_generation": 0,
}


_SPLIT_DELTA_LOCK = _split_threading.RLock()
_SPLIT_DELTA_DIR = _split_os.path.join(str(_split_os.getenv('MEGA_LOCAL_TMP_DIR', '/tmp') or '/tmp'), 'vys262_delta_front')
_split_os.makedirs(_SPLIT_DELTA_DIR, exist_ok=True)
_SPLIT_DELTA_BASELINE = _split_os.path.join(_SPLIT_DELTA_DIR, 'acked_baseline.sqlite3')

def _split_sha256_file_v267(path):
    h = _split_hashlib.sha256()
    with open(path, 'rb') as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()

def _split_sqlite_page_size_v267(path):
    with open(path, 'rb') as fh:
        head = fh.read(100)
    if len(head) < 18 or head[:16] != b'SQLite format 3\x00':
        raise RuntimeError('not a SQLite database')
    page_size = int.from_bytes(head[16:18], 'big')
    if page_size == 1:
        page_size = 65536
    if page_size < 512 or page_size > 65536 or (page_size & (page_size - 1)):
        raise RuntimeError(f'invalid SQLite page size {page_size}')
    return page_size

def _split_snapshot_raw_v267(prefix='delta'):
    workdir = _split_tempfile.mkdtemp(prefix=f'v267_{prefix}_')
    raw = _split_os.path.join(workdir, 'state.sqlite3')
    SQLITE.backup_to(raw)
    return workdir, raw

def _split_init_delta_baseline_v267(force=False):
    with _SPLIT_DELTA_LOCK:
        if (not force) and _split_os.path.isfile(_SPLIT_DELTA_BASELINE) and _split_os.path.getsize(_SPLIT_DELTA_BASELINE) > 0:
            try:
                sha = _split_sha256_file_v267(_SPLIT_DELTA_BASELINE)
                _SPLIT_STATE['delta_baseline_sha256'] = sha
                return True
            except Exception:
                pass
        workdir = None
        try:
            workdir, raw = _split_snapshot_raw_v267('baseline')
            tmp = _SPLIT_DELTA_BASELINE + '.tmp'
            _split_shutil.copy2(raw, tmp)
            _split_os.replace(tmp, _SPLIT_DELTA_BASELINE)
            _SPLIT_STATE['delta_baseline_sha256'] = _split_sha256_file_v267(_SPLIT_DELTA_BASELINE)
            return True
        except Exception as exc:
            _SPLIT_STATE['delta_last_error'] = 'baseline: ' + str(exc)[:180]
            return False
        finally:
            if workdir:
                _split_shutil.rmtree(workdir, ignore_errors=True)

def _split_build_delta_v267(reason='change'):
    """Build a page-level delta against the last Worker-acknowledged SQLite image.

    Returns (payload_dict, current_raw, workdir, fallback_reason).  current_raw stays
    alive until the caller receives Worker acknowledgement and promotes it to baseline.
    """
    with _SPLIT_DELTA_LOCK:
        if not _split_os.path.isfile(_SPLIT_DELTA_BASELINE):
            return None, None, None, 'baseline_missing'
        workdir = None
        try:
            workdir, current = _split_snapshot_raw_v267('delta')
            base = _SPLIT_DELTA_BASELINE
            page_size = _split_sqlite_page_size_v267(current)
            if _split_sqlite_page_size_v267(base) != page_size:
                return None, current, workdir, 'page_size_changed'
            base_sha = _split_sha256_file_v267(base)
            new_sha = _split_sha256_file_v267(current)
            base_size = _split_os.path.getsize(base)
            new_size = _split_os.path.getsize(current)
            if base_sha == new_sha and base_size == new_size:
                return {'schema':1,'noop':True,'base_sha256':base_sha,'new_sha256':new_sha,'db_size':new_size,'page_size':page_size,'pages':[], 'state_token':_split_current_state_token_v264(), 'reason':str(reason or '')[:160], 'event_ids':_split_pending_event_ids_v268()}, current, workdir, ''
            pages=[]
            page_count=(new_size + page_size - 1)//page_size
            with open(base,'rb') as old, open(current,'rb') as new:
                for idx in range(page_count):
                    ob=old.read(page_size)
                    nb=new.read(page_size)
                    if ob != nb:
                        pages.append([idx, _split_base64.b64encode(nb).decode('ascii')])
            payload={'schema':1,'base_sha256':base_sha,'new_sha256':new_sha,'base_size':base_size,'db_size':new_size,'page_size':page_size,'pages':pages,'state_token':_split_current_state_token_v264(),'reason':str(reason or '')[:160],'created_at':_split_time.time(),'event_ids':_split_pending_event_ids_v268()}
            raw_json=_split_json.dumps(payload,separators=(',',':')).encode('utf-8')
            compressed=_split_gzip.compress(raw_json, compresslevel=9)
            max_pages=max(8,min(4096,int(_split_os.getenv('SPLIT_DELTA_MAX_PAGES','256') or '256')))
            max_bytes=max(32768,min(8*1024*1024,int(_split_os.getenv('SPLIT_DELTA_MAX_BYTES','524288') or '524288')))
            if len(pages) > max_pages or len(compressed) > max_bytes:
                return None, current, workdir, f'delta_too_large pages={len(pages)} bytes={len(compressed)}'
            payload['_wire_gzip']=compressed
            return payload,current,workdir,''
        except Exception as exc:
            if workdir:
                _split_shutil.rmtree(workdir, ignore_errors=True)
            return None,None,None,f'{type(exc).__name__}: {str(exc)[:180]}'

def _split_promote_delta_baseline_v267(current_raw):
    if not current_raw or not _split_os.path.isfile(current_raw):
        return False
    with _SPLIT_DELTA_LOCK:
        tmp=_SPLIT_DELTA_BASELINE+'.tmp'
        _split_shutil.copy2(current_raw,tmp)
        _split_os.replace(tmp,_SPLIT_DELTA_BASELINE)
        _SPLIT_STATE['delta_baseline_sha256']=_split_sha256_file_v267(_SPLIT_DELTA_BASELINE)
        return True

def _split_send_delta_v267(reason='change'):
    base, secret = _split_peer_base(), _split_secret()
    if not base or not secret:
        return False, 'worker URL/secret not configured', False
    payload,current,workdir,fallback = _split_build_delta_v267(reason)
    if payload is None:
        if workdir:
            _split_shutil.rmtree(workdir, ignore_errors=True)
        return False, fallback or 'delta unavailable', True
    try:
        wire=payload.pop('_wire_gzip', None)
        if wire is None:
            wire=_split_gzip.compress(_split_json.dumps(payload,separators=(',',':')).encode('utf-8'),compresslevel=9)
        r=requests.post(base+'/internal/delta',data=wire,headers={**_split_headers('vys-262-front-delta-r12'),'Content-Type':'application/json','Content-Encoding':'gzip'},timeout=15)
        if 200 <= r.status_code < 300:
            body={}
            try: body=r.json() if r.content else {}
            except Exception: body={}
            status=str(body.get('status') or 'applied')
            if status in {'applied','up_to_date','noop'}:
                _split_promote_delta_baseline_v267(current)
                _SPLIT_STATE['delta_last_ok']=_split_time.time()
                _SPLIT_STATE['delta_last_error']=''
                _SPLIT_STATE['delta_last_bytes']=len(wire)
                _SPLIT_STATE['delta_last_pages']=len(payload.get('pages') or [])
                _SPLIT_STATE['delta_total_bytes']=int(_SPLIT_STATE.get('delta_total_bytes') or 0)+len(wire)
                _SPLIT_STATE['delta_total_pages']=int(_SPLIT_STATE.get('delta_total_pages') or 0)+len(payload.get('pages') or [])
                _split_ack_mirrored_events_v268(payload.get('event_ids') or [])
                return True,status,False
        if r.status_code in {409, 412, 422}:
            return False, f'worker requests full: HTTP {r.status_code} {r.text[:180]}', True
        return False,f'HTTP {r.status_code}: {r.text[:180]}',False
    except Exception as exc:
        return False,f'{type(exc).__name__}: {str(exc)[:180]}',False
    finally:
        if workdir:
            _split_shutil.rmtree(workdir, ignore_errors=True)

def _split_env_bool(name, default=True):
    return str(_split_os.getenv(name, "1" if default else "0") or "").strip().lower() in {"1", "true", "yes", "on", "да"}


def _split_peer_base():
    raw = str(_split_os.getenv("PEER_SERVICE_URL", "") or "").strip().rstrip("/")
    if raw and not raw.startswith(("http://", "https://")):
        raw = "https://" + raw
    return raw


def _split_secret():
    return str(_split_os.getenv("PEER_SHARED_SECRET", "") or "").strip()


def _split_headers(agent="vys-262-front-peer"):
    return {"X-Peer-Secret": _split_secret(), "User-Agent": agent}


# R13: remote Telegram event witness.  The raw event is made durable on Worker/Redis
# before Telegram is acknowledged.  Business execution still happens only on Front.
_SPLIT_EVENT_LOCK = _split_threading.RLock()
_SPLIT_EVENT_PENDING_MIRROR = _split_collections.OrderedDict()

def _split_event_prefix_v268():
    return str(_split_os.getenv('WORKER_REDIS_EVENT_PREFIX','vys262:tg_events:v1') or 'vys262:tg_events:v1').strip()

def _r61_effective_redis_url():
    """R61: operational Redis URL from runtime_config; Render env is never mutated."""
    try:
        from runtime_config import redis_effective_url
        return str(redis_effective_url() or '').strip()
    except Exception:
        return ''

def _r61_render_redis_url():
    try:
        from runtime_config import redis_render_url
        return str(redis_render_url() or '').strip()
    except Exception:
        return ''

def _split_event_id_v268(update_id):
    return str(update_id)

def _split_event_row_v268(update_id, payload, chat_id=None, update_type='other'):
    raw = _split_json.dumps(payload if isinstance(payload,dict) else {}, ensure_ascii=False, separators=(',',':'), default=str)
    return {
        'schema': 1, 'event_id': _split_event_id_v268(update_id), 'update_id': str(update_id),
        'chat_id': chat_id, 'update_type': str(update_type or 'other')[:40],
        'payload': payload if isinstance(payload,dict) else {},
        'payload_sha256': _split_hashlib.sha256(raw.encode('utf-8')).hexdigest(),
        'state': 'received', 'received_at': _split_time.time(),
        'front_version': _SPLIT_FRONT_VERSION,
    }

def _split_event_redis_write_v268(row, state=None, error=''):
    if _split_redis is None:
        return False, 'redis package unavailable'
    url=_r61_effective_redis_url()
    if not url:
        return False, 'REDIS_URL empty'
    try:
        client=_split_redis.Redis.from_url(url,socket_connect_timeout=float(_split_os.getenv('SPLIT_REDIS_FALLBACK_CONNECT_TIMEOUT_SEC','0.7') or '0.7'),socket_timeout=float(_split_os.getenv('SPLIT_REDIS_FALLBACK_SOCKET_TIMEOUT_SEC','1.2') or '1.2'),health_check_interval=30)
        event_id=str((row or {}).get('event_id') or (row or {}).get('update_id') or '')
        if not event_id:
            return False,'event id empty'
        prefix=_split_event_prefix_v268(); key=f'{prefix}:event:{event_id}'; pending=f'{prefix}:pending'
        current={}
        try:
            existing=client.get(key)
            if existing: current=_split_json.loads(existing.decode('utf-8') if isinstance(existing,(bytes,bytearray)) else existing)
        except Exception: current={}
        merged=dict(current or {}); merged.update(row or {})
        _rank={'received':1,'failed_retry':1,'committed':2,'mirrored':3,'checkpointed':4,'done':4}
        old_state=str((current or {}).get('state') or '')
        new_state=str(state or merged.get('state') or '')
        if _rank.get(old_state,0) > _rank.get(new_state,0): new_state=old_state
        if new_state: merged['state']=new_state
        if error and _rank.get(new_state,0) < 3: merged['last_error']=str(error)[:300]
        merged['updated_at']=_split_time.time()
        ttl=max(86400,min(2592000,int(_split_os.getenv('WORKER_EVENT_RETENTION_SEC','604800') or '604800')))
        pipe=client.pipeline(transaction=True)
        pipe.set(key,_split_json.dumps(merged,ensure_ascii=False,separators=(',',':'),default=str),ex=ttl)
        if str(merged.get('state') or '') in {'mirrored','checkpointed','done'}:
            pipe.zrem(pending,event_id)
        else:
            pipe.zadd(pending,{event_id:float(merged.get('received_at') or _split_time.time())})
        pipe.execute()
        return True,'redis event stored'
    except Exception as exc:
        return False,f'{type(exc).__name__}: {str(exc)[:180]}'

def split_witness_event_v268(update_id, payload, chat_id=None, update_type='other'):
    """R57: keep Redis completely out of the Telegram hot path.

    FAST sends the small raw-update witness only to HEAVY. HEAVY owns any optional
    Redis mirroring/cache work in background. This means turning Redis ON from the
    Info menu cannot add Redis network latency to a button or message callback.
    """
    row=_split_event_row_v268(update_id,payload,chat_id,update_type)
    base,secret=_split_peer_base(),_split_secret(); detail='worker not configured'
    if base and secret:
        try:
            raw=_split_json.dumps(row,ensure_ascii=False,separators=(',',':'),default=str).encode('utf-8')
            wire=_split_gzip.compress(raw,compresslevel=1)
            r=requests.post(base+'/internal/event/receipt',data=wire,headers={**_split_headers('vys-262-front-event-r57'),'Content-Type':'application/json','Content-Encoding':'gzip'},timeout=max(0.35,min(2.5,float(_split_os.getenv('SPLIT_EVENT_RECEIPT_TIMEOUT_SEC','1.2') or '1.2'))))
            if 200 <= r.status_code < 300:
                _SPLIT_STATE['event_last_receipt_ok']=_split_time.time(); _SPLIT_STATE['event_last_error']=''
                _SPLIT_STATE['event_received']=int(_SPLIT_STATE.get('event_received') or 0)+1
                return True
            detail=f'worker HTTP {r.status_code}: {r.text[:160]}'
        except Exception as exc:
            detail=f'worker {type(exc).__name__}: {str(exc)[:160]}'
    _SPLIT_STATE['event_last_error']=detail[:260]
    return False

def _split_event_status_send_v268(update_id, chat_id=None, update_type='other', success=True, error=''):
    """R57: commit witness also goes through HEAVY; FAST never blocks on Redis."""
    event_id=_split_event_id_v268(update_id)
    row={'schema':1,'event_id':event_id,'update_id':str(update_id),'chat_id':chat_id,'update_type':str(update_type or 'other')[:40],
         'state':'committed' if success else 'failed_retry','committed_at':_split_time.time() if success else 0.0,
         'state_token':_split_current_state_token_v264(),'last_error':str(error or '')[:300]}
    base,secret=_split_peer_base(),_split_secret(); detail='worker not configured'
    if base and secret:
        try:
            r=requests.post(base+'/internal/event/commit',json=row,headers=_split_headers('vys-262-front-event-commit-r57'),timeout=4)
            if 200 <= r.status_code < 300:
                if success:
                    _SPLIT_STATE['event_last_commit_ok']=_split_time.time(); _SPLIT_STATE['event_committed']=int(_SPLIT_STATE.get('event_committed') or 0)+1
                _SPLIT_STATE['event_last_error']=''
                return True
            detail=f'worker HTTP {r.status_code}: {r.text[:160]}'
        except Exception as exc:
            detail=f'worker {type(exc).__name__}: {str(exc)[:160]}'
    _SPLIT_STATE['event_last_error']=detail[:260]
    return False

def _split_event_bg_v268(fn,*args):
    key=f'event-r13:{args[0] if args else _split_time.time_ns()}'
    try:
        pool=globals().get('BACKGROUND_TASK_POOL')
        if pool is not None and hasattr(pool,'submit') and pool.submit(key,fn,*args):
            return True
    except Exception:
        pass
    try:
        sched=globals().get('DELAYED_SCHEDULER')
        if sched is not None:
            sched.schedule(key,0.25,fn,*args)
            return True
    except Exception:
        pass
    return False

def split_event_committed_v268(update_id, chat_id=None, update_type='other', success=True, error=''):
    event_id=_split_event_id_v268(update_id)
    if success:
        with _SPLIT_EVENT_LOCK:
            _SPLIT_EVENT_PENDING_MIRROR[event_id]=_split_time.time()
            while len(_SPLIT_EVENT_PENDING_MIRROR)>512:
                _SPLIT_EVENT_PENDING_MIRROR.popitem(last=False)
        # R15: the post-update wrapper schedules one trailing-edge mirror attempt.
        # Do not arm a second snapshot timer from the event-status path.
    return _split_event_bg_v268(_split_event_status_send_v268,update_id,chat_id,update_type,success,error)

def _split_pending_event_ids_v268(limit=96):
    with _SPLIT_EVENT_LOCK:
        return list(_SPLIT_EVENT_PENDING_MIRROR.keys())[:max(1,int(limit))]

def _split_ack_mirrored_events_v268(event_ids):
    ids=[str(x) for x in (event_ids or []) if str(x)]
    if not ids: return
    with _SPLIT_EVENT_LOCK:
        for event_id in ids: _SPLIT_EVENT_PENDING_MIRROR.pop(event_id,None)
    _SPLIT_STATE['event_mirrored']=int(_SPLIT_STATE.get('event_mirrored') or 0)+len(ids)

def _split_remote_pending_rows_v268(limit=100):
    # R16: query the authoritative Redis event journal first; Worker is a fallback.
    if _split_redis is not None:
        url=_r61_effective_redis_url()
        if url:
            try:
                client=_split_redis.Redis.from_url(url,socket_connect_timeout=1.5,socket_timeout=3)
                prefix=_split_event_prefix_v268(); ids=client.zrange(f'{prefix}:pending',0,max(0,min(249,int(limit)-1))) or []
                rows=[]
                for raw_id in ids:
                    eid=raw_id.decode() if isinstance(raw_id,(bytes,bytearray)) else str(raw_id)
                    raw=client.get(f'{prefix}:event:{eid}')
                    if not raw: continue
                    try: row=_split_json.loads(raw.decode('utf-8') if isinstance(raw,(bytes,bytearray)) else raw)
                    except Exception: continue
                    if str((row or {}).get('state') or '') in {'received','failed_retry','committed'}: rows.append(row)
                return rows
            except Exception:
                pass
    base,secret=_split_peer_base(),_split_secret()
    if base and secret:
        try:
            r=requests.get(base+'/internal/events/pending',params={'limit':max(1,min(250,int(limit)))},headers=_split_headers('vys-262-front-event-recover-r16-fallback'),timeout=8)
            if 200 <= r.status_code < 300:
                body=r.json() if r.content else {}; return list(body.get('events') or [])
        except Exception: pass
    return []

def split_recover_remote_events_v268(limit=100):
    """Replay remote witnessed-but-not-mirrored Telegram updates after abrupt deploy."""
    recovered=0
    for row in _split_remote_pending_rows_v268(limit):
        try:
            update_id=row.get('update_id') or row.get('event_id'); payload=row.get('payload') or {}
            chat_id=row.get('chat_id'); update_type=str(row.get('update_type') or 'other')
            if update_id is None or not isinstance(payload,dict): continue
            state_fn=globals().get('_v260_webhook_inbox_state'); put_fn=globals().get('_v260_webhook_inbox_put'); submit_fn=globals().get('_v260_submit_webhook_inbox_row'); row_fn=globals().get('_v260_webhook_inbox_row')
            if not all(callable(x) for x in (state_fn,put_fn,submit_fn,row_fn)): continue
            if state_fn(update_id)=='done':
                split_event_committed_v268(update_id,chat_id,update_type,True,'already local done')
                continue
            if not put_fn(update_id,payload,chat_id,update_type): continue
            if submit_fn(row_fn(update_id)):
                recovered+=1
        except Exception: continue
    _SPLIT_STATE['event_recovered']=int(_SPLIT_STATE.get('event_recovered') or 0)+recovered
    return recovered


def _split_authorized_request():
    secret = _split_secret()
    supplied = str(request.headers.get("X-Peer-Secret", "") or "")
    return bool(secret and _split_secrets.compare_digest(secret, supplied))


_SPLIT_STATE_REV_KIND_R18 = 'split_state_revision_r18'
_SPLIT_STATE_REV_KEY_R18 = 'latest'
_SPLIT_STATE_REV_LOCK_R18 = _split_threading.RLock()
try:
    _SPLIT_STATE_REV_MEM_R27 = dict(SQLITE.get_meta(_SPLIT_STATE_REV_KIND_R18, _SPLIT_STATE_REV_KEY_R18, {}) or {})
except Exception:
    _SPLIT_STATE_REV_MEM_R27 = {}
_SPLIT_STATE_REV_DIRTY_R27 = False

def _r27_flush_state_revision():
    global _SPLIT_STATE_REV_DIRTY_R27
    try:
        with _SPLIT_STATE_REV_LOCK_R18:
            if not _SPLIT_STATE_REV_DIRTY_R27:
                return True
            payload = dict(_SPLIT_STATE_REV_MEM_R27 or {})
        SQLITE.set_meta(_SPLIT_STATE_REV_KIND_R18, _SPLIT_STATE_REV_KEY_R18, payload)
        with _SPLIT_STATE_REV_LOCK_R18:
            if int((_SPLIT_STATE_REV_MEM_R27 or {}).get('seq') or 0) <= int(payload.get('seq') or 0):
                _SPLIT_STATE_REV_DIRTY_R27 = False
        return True
    except Exception as exc:
        try: log_error(f'R27 state revision flush: {exc}')
        except Exception: pass
        return False

def _r27_schedule_state_revision_flush(delay=4.0):
    try:
        scheduler = globals().get('DELAYED_SCHEDULER')
        if scheduler is not None:
            scheduler.schedule('r27-state-revision-flush', max(1.0, float(delay)), _r27_flush_state_revision)
            return True
    except Exception:
        pass
    return False

def _split_touch_state_revision_r18(reason='update', update_id=None):
    """R27: monotonic revision is RAM-only on the Telegram hot path.

    The durable meta row is flushed later by the scheduler / before an idle snapshot.
    A UI callback therefore never waits on SQLITE just to update this bookkeeping row.
    """
    global _SPLIT_STATE_REV_DIRTY_R27
    try:
        with _SPLIT_STATE_REV_LOCK_R18:
            seq = int((_SPLIT_STATE_REV_MEM_R27 or {}).get('seq') or 0) + 1
            payload = {'schema':1, 'seq':seq, 'saved_at':_split_time.time(), 'reason':str(reason or '')[:140],
                       'update_id':str(update_id)[:80] if update_id is not None else '',
                       'state_token':_split_current_state_token_v264() if '_split_current_state_token_v264' in globals() else ''}
            _SPLIT_STATE_REV_MEM_R27.clear(); _SPLIT_STATE_REV_MEM_R27.update(payload)
            _SPLIT_STATE_REV_DIRTY_R27 = True
        # R28: do not schedule any SQLite write from a Telegram/user update.
        # The RAM revision is flushed only immediately before an idle/full durability snapshot.
        return payload
    except Exception as exc:
        try: log_error(f'R27 state revision touch: {exc}')
        except Exception: pass
        return {}


def _split_mark_state_changed_v264(reason='change'):
    global _SPLIT_CHANGE_SEQ, _SPLIT_STATE_TOKEN, _SPLIT_LAST_CHANGE_AT
    with _SPLIT_CHANGE_LOCK:
        _SPLIT_CHANGE_SEQ += 1
        _SPLIT_LAST_CHANGE_AT = _split_time.time()
        _SPLIT_STATE_TOKEN = f"{_SPLIT_CHANGE_EPOCH}:{_SPLIT_CHANGE_SEQ}"
        _SPLIT_STATE['state_token'] = _SPLIT_STATE_TOKEN
        _SPLIT_STATE['state_change_reason'] = str(reason or 'change')[:160]
        return _SPLIT_STATE_TOKEN


def _split_current_state_token_v264():
    with _SPLIT_CHANGE_LOCK:
        return str(_SPLIT_STATE_TOKEN)



def _split_snapshot_meta():
    try:
        state_meta = ((data or {}).get('_state_meta') or {}) if isinstance(data, dict) else {}
        with _LOWRAM_LOCK:
            stats = dict(_LOWRAM_STATS or {})
        return {
            'last_saved_at': str((state_meta or {}).get('last_saved_at') or ''),
            'cold_records': int(stats.get('cold_saves') or 0),
            'db_file': str(globals().get('DB_FILE') or 'bot_state.sqlite3'),
            'source': 'ram_r48',
        }
    except Exception as exc:
        return {'error': str(exc)[:160], 'source': 'ram_r48'}



@app.route('/peer/health', methods=['GET', 'HEAD'])
def split_front_peer_health_v262():
    # Keep the legacy keep_alive diagnostics in sync with the real split peer.
    try:
        ua = str(request.headers.get('User-Agent', '') or '').casefold()
        if 'worker-peer' in ua and _split_authorized_request():
            ks = globals().get('KEEP_ALIVE_STATE')
            if isinstance(ks, dict):
                now_txt = now_local().isoformat(timespec='milliseconds') if callable(globals().get('now_local')) else str(_split_time.time())
                ks['peer_received_at'] = now_txt
                ks['last_inbound_activity_at'] = now_txt
                ks['last_inbound_activity_kind'] = 'peer_worker'
    except Exception:
        pass
    if request.method == 'HEAD':
        return ('', 200)
    return ({
        'ok': True,
        'role': 'front',
        'version': _SPLIT_FRONT_VERSION,
        'bot_version': str(globals().get('VERSION') or ''),
        'ready': bool(globals().get('runtime_is_ready', lambda: False)()),
        'phase': (globals().get('_RUNTIME_STATE') or {}).get('phase'),
        'snapshot': _split_snapshot_meta(),
        'peer': dict(_SPLIT_STATE),
    }, 200)


@app.route('/internal/split/state', methods=['GET'])
def split_front_state_download_v262():
    """Return a transactionally consistent SQLite gzip to the worker."""
    if not _split_authorized_request():
        return ({'ok': False}, 404)
    workdir = _split_tempfile.mkdtemp(prefix='v262_front_state_')
    raw = _split_os.path.join(workdir, 'bot_state.sqlite3')
    gz = raw + '.gz'
    try:
        try:
            _quiet_fn = globals().get('r27_user_quiet_for')
            _quiet_for = float(_quiet_fn()) if callable(_quiet_fn) else 999999.0
            _guard = max(2.0, min(60.0, float(_split_os.getenv('R28_FULL_SNAPSHOT_USER_QUIET_SEC','30') or '15')))
            _r43_direct_job = str(request.headers.get('X-R43-Job-Snapshot','') or '').strip() == '1'
            if (not _r43_direct_job) and bool(globals().get('runtime_is_ready', lambda: False)()) and _quiet_for < _guard:
                return ({'ok': False, 'busy': 'user_active', 'retry_after': max(1, int(_guard - _quiet_for) + 1)}, 423)
        except Exception:
            pass
        try: _r27_flush_state_revision()
        except Exception: pass
        _r25_state_started = _split_time.monotonic()
        snapshot_token = _split_current_state_token_v264()
        try: log_info(f'SPLITTRACE full_state_start token={snapshot_token[:48]}')
        except Exception: pass
        SQLITE.backup_to(raw)
        with open(raw, 'rb') as src, _split_gzip.open(gz, 'wb', compresslevel=1) as dst:
            _split_shutil.copyfileobj(src, dst, length=1024 * 1024)
        # R19: this raw SQLite image is exactly the full image HEAVY is about to receive.
        # Promote that SAME image to FAST's acknowledged delta baseline. R18 left the
        # old baseline in place after a full rebase, so every next tiny change produced
        # another 409 -> full /internal/split/state GET (~1.3 MB) loop.
        try:
            _split_promote_delta_baseline_v267(raw)
            _SPLIT_STATE['full_reconcile_last_ok'] = _split_time.time()
            _SPLIT_STATE['full_reconcile_pending'] = False
        except Exception as _r19_base_exc:
            _SPLIT_STATE['full_reconcile_last_error'] = 'R19 served baseline: ' + str(_r19_base_exc)[:180]
        with open(gz, 'rb') as fh:
            payload = fh.read()
        response = app.response_class(payload, status=200, mimetype='application/gzip')
        response.headers['Content-Disposition'] = 'attachment; filename="latest_bot_state.sqlite3.gz"'
        response.headers['X-Split-Version'] = _SPLIT_FRONT_VERSION
        response.headers['X-Split-Size'] = str(len(payload))
        response.headers['X-Split-State-Token'] = snapshot_token
        try: log_info(f'SPLITTRACE full_state_done token={snapshot_token[:48]} bytes={len(payload)} elapsed={_split_time.monotonic()-_r25_state_started:.3f}s')
        except Exception: pass
        return response
    except Exception as exc:
        return ({'ok': False, 'error': str(exc)[:240]}, 500)
    finally:
        _split_shutil.rmtree(workdir, ignore_errors=True)



@app.route('/internal/split/hash', methods=['GET'])
def split_front_state_hash_v268():
    """Rare reconciliation probe: hash a consistent SQLite image without sending it."""
    if not _split_authorized_request():
        return ({'ok':False},404)
    workdir=None
    try:
        workdir,raw=_split_snapshot_raw_v267('hash')
        return ({'ok':True,'sha256':_split_sha256_file_v267(raw),'size':_split_os.path.getsize(raw),'state_token':_split_current_state_token_v264(),'version':_SPLIT_FRONT_VERSION},200)
    except Exception as exc:
        return ({'ok':False,'error':f'{type(exc).__name__}: {str(exc)[:180]}'},500)
    finally:
        if workdir: _split_shutil.rmtree(workdir,ignore_errors=True)


def _split_redis_snapshot_keys_v266():
    key = str(_split_os.getenv('WORKER_REDIS_SNAPSHOT_KEY', 'vys262:bot_state:latest_gz') or 'vys262:bot_state:latest_gz').strip()
    return key, key + ':meta'


def _split_cache_snapshot_to_redis_v266(reason='front_fallback', existing_gz=None, *, verify=True, use_render_url=False):
    """Write one canonical full SQLite snapshot to Redis and verify it.

    R64: FAST owns its Redis baseline.  HEAVY may mirror/checkpoint the same keys,
    but a successful manual restore no longer depends on HEAVY being online.
    Background checkpoints use the active runtime URL; the manual-restore seal may
    use the Render-owned URL whenever REDIS_ENABLED=1 so REDIS_START_ENABLED does
    not prevent protecting a user-confirmed restore.
    """
    if _split_redis is None:
        _SPLIT_STATE['redis_fallback_last_error'] = 'redis package unavailable'
        return False
    url = _r61_render_redis_url() if use_render_url else _r61_effective_redis_url()
    if use_render_url:
        try:
            import runtime_config as _r64_rc
            _r64_state = dict(_r64_rc.redis_runtime_state() or {})
            if not bool(_r64_state.get('master_enabled')):
                _SPLIT_STATE['redis_fallback_last_error'] = 'REDIS_ENABLED=0'
                return False
        except Exception as _r64_state_exc:
            _SPLIT_STATE['redis_fallback_last_error'] = f'redis state: {type(_r64_state_exc).__name__}: {str(_r64_state_exc)[:120]}'
            return False
    if not url:
        _SPLIT_STATE['redis_fallback_last_error'] = 'REDIS_URL empty/inactive'
        return False
    workdir = None
    client = None
    try:
        capture_started = _split_time.time()
        if existing_gz:
            gz = str(existing_gz)
        else:
            workdir = _split_tempfile.mkdtemp(prefix='r64_front_redis_')
            raw = _split_os.path.join(workdir, 'bot_state.sqlite3')
            gz = raw + '.gz'
            SQLITE.backup_to(raw)
            with open(raw, 'rb') as src, _split_gzip.open(gz, 'wb', compresslevel=1) as dst:
                _split_shutil.copyfileobj(src, dst, length=1024 * 1024)
        with open(gz, 'rb') as _r64_fh:
            payload = _r64_fh.read()
        max_mb = max(1, min(128, int(_split_os.getenv('WORKER_REDIS_SNAPSHOT_MAX_MB', '16') or '16')))
        if len(payload) > max_mb * 1024 * 1024:
            raise RuntimeError(f'snapshot too large for Redis: {len(payload)}')
        digest = _split_hashlib.sha256(payload).hexdigest()
        revision = 0.0
        try:
            for kind in ('split_state_revision_r18', 'user_state_shadow_v265', 'runtime_continuity_v263'):
                row = SQLITE.get_meta(kind, 'latest', {}) or {}
                revision = max(revision, float((row or {}).get('saved_at') or 0.0))
        except Exception:
            pass
        key, meta_key = _split_redis_snapshot_keys_v266()
        client = _split_redis.Redis.from_url(url, socket_connect_timeout=3, socket_timeout=12, health_check_interval=30)
        existing_revision = 0.0
        try:
            existing_raw = client.get(meta_key)
            if isinstance(existing_raw, (bytes, bytearray)):
                existing_raw = existing_raw.decode('utf-8', 'replace')
            existing_meta = _split_json.loads(existing_raw) if isinstance(existing_raw, str) and existing_raw else {}
            existing_revision = float((existing_meta or {}).get('revision') or 0.0)
        except Exception:
            existing_revision = 0.0
        # A manual restore is an explicit re-anchor and must overwrite any older-lineage
        # revision comparison.  Background checkpoints still preserve a provably newer image.
        is_manual = str(reason or '').startswith('manual_restore:')
        if (not is_manual) and existing_revision > revision + 0.000001:
            _SPLIT_STATE['redis_fallback_last_ok'] = _split_time.time()
            _SPLIT_STATE['redis_fallback_last_error'] = 'newer Redis snapshot preserved'
            return True
        meta = {
            'revision': revision, 'size': len(payload), 'sha256': digest,
            'saved_at': _split_time.time(), 'event_cutoff_score': float(capture_started),
            'reason': str(reason or '')[:160], 'source': 'fast-r64', 'schema': 2,
        }
        pipe = client.pipeline(transaction=True)
        pipe.set(key, payload)
        pipe.set(meta_key, _split_json.dumps(meta, separators=(',', ':')))
        pipe.execute()
        if verify:
            back = client.get(key)
            if not isinstance(back, (bytes, bytearray)):
                raise RuntimeError('Redis verify: snapshot key unreadable')
            if len(back) != len(payload):
                raise RuntimeError(f'Redis verify: size mismatch {len(back)} != {len(payload)}')
            back_digest = _split_hashlib.sha256(bytes(back)).hexdigest()
            if back_digest != digest:
                raise RuntimeError('Redis verify: sha256 mismatch')
            meta_back = client.get(meta_key)
            if isinstance(meta_back, (bytes, bytearray)):
                meta_back = meta_back.decode('utf-8', 'replace')
            meta_obj = _split_json.loads(meta_back) if isinstance(meta_back, str) and meta_back else {}
            if str((meta_obj or {}).get('sha256') or '') != digest:
                raise RuntimeError('Redis verify: meta sha256 mismatch')
        _SPLIT_STATE['redis_fallback_last_ok'] = _split_time.time()
        _SPLIT_STATE['redis_fallback_last_error'] = ''
        _SPLIT_STATE['redis_fallback_last_size'] = len(payload)
        _SPLIT_STATE['redis_fallback_last_sha256'] = digest
        _SPLIT_STATE['redis_fallback_last_reason'] = str(reason or '')[:160]
        return True
    except Exception as exc:
        _SPLIT_STATE['redis_fallback_last_error'] = f'{type(exc).__name__}: {str(exc)[:220]}'
        return False
    finally:
        try:
            if client is not None:
                client.close()
        except Exception:
            pass
        if workdir:
            _split_shutil.rmtree(workdir, ignore_errors=True)


def r64_publish_restore_snapshot_v271(reason='restore'):
    """Synchronously seal a successful manual restore into Redis on FAST.

    Returns a structured result so every restore path can report whether the new
    canonical SQLite was actually recoverable before telling the owner it is sealed.
    """
    try:
        import runtime_config as _r64_rc
        st = dict(_r64_rc.redis_runtime_state() or {})
    except Exception as exc:
        return {'required': False, 'ok': False, 'detail': f'runtime_config: {type(exc).__name__}: {str(exc)[:180]}'}
    required = bool(st.get('master_enabled') and st.get('configured'))
    if not required:
        return {'required': False, 'ok': False, 'detail': 'Redis recovery not configured in Render'}
    ok = bool(_split_cache_snapshot_to_redis_v266(
        reason='manual_restore:' + str(reason or 'restore')[:120],
        verify=True, use_render_url=True,
    ))
    detail = 'Redis full SQLite snapshot verified' if ok else str(_SPLIT_STATE.get('redis_fallback_last_error') or 'unknown Redis snapshot error')[:300]
    try:
        bot_journal('r64_restore_redis_snapshot', int(OWNER_ID or 0), f'ok={int(ok)}; reason={str(reason)[:120]}; detail={detail}')
    except Exception:
        pass
    if not ok and _r61_effective_redis_url():
        try:
            retry_fn = globals().get('r64_schedule_fast_redis_snapshot_v271')
            if callable(retry_fn): retry_fn('manual_restore_retry')
        except Exception:
            pass
    return {
        'required': True, 'ok': ok, 'detail': detail,
        'size': int(_SPLIT_STATE.get('redis_fallback_last_size') or 0),
        'sha256': str(_SPLIT_STATE.get('redis_fallback_last_sha256') or '')[:64],
    }


_R64_REDIS_SNAPSHOT_TIMER = None
_R64_REDIS_SNAPSHOT_LOCK = _split_threading.RLock()
_R64_REDIS_SNAPSHOT_DIRTY = False
_R64_REDIS_SNAPSHOT_LAST_AT = 0.0

def _r64_periodic_redis_snapshot_fire_v271():
    global _R64_REDIS_SNAPSHOT_TIMER, _R64_REDIS_SNAPSHOT_DIRTY, _R64_REDIS_SNAPSHOT_LAST_AT
    with _R64_REDIS_SNAPSHOT_LOCK:
        _R64_REDIS_SNAPSHOT_TIMER = None
        dirty = bool(_R64_REDIS_SNAPSHOT_DIRTY)
        _R64_REDIS_SNAPSHOT_DIRTY = False
    if not dirty or not _r61_effective_redis_url():
        return
    ok = bool(_split_cache_snapshot_to_redis_v266('periodic_fast_checkpoint', verify=True, use_render_url=False))
    now = _split_time.time()
    if ok:
        _R64_REDIS_SNAPSHOT_LAST_AT = now
        return
    # Keep one bounded retry armed.  The latest SQLite stays authoritative locally.
    with _R64_REDIS_SNAPSHOT_LOCK:
        _R64_REDIS_SNAPSHOT_DIRTY = True
        if _R64_REDIS_SNAPSHOT_TIMER is None:
            _R64_REDIS_SNAPSHOT_TIMER = _split_threading.Timer(30.0, _r64_periodic_redis_snapshot_fire_v271)
            _R64_REDIS_SNAPSHOT_TIMER.daemon = True
            _R64_REDIS_SNAPSHOT_TIMER.start()

def r64_schedule_fast_redis_snapshot_v271(reason='state_change'):
    """Debounced FAST-owned Redis checkpoint; never runs in the Telegram hot path."""
    global _R64_REDIS_SNAPSHOT_TIMER, _R64_REDIS_SNAPSHOT_DIRTY
    if not _r61_effective_redis_url():
        return False
    with _R64_REDIS_SNAPSHOT_LOCK:
        _R64_REDIS_SNAPSHOT_DIRTY = True
        now = _split_time.time()
        since = max(0.0, now - float(_R64_REDIS_SNAPSHOT_LAST_AT or 0.0))
        delay = 12.0 if since >= 60.0 else max(12.0, 60.0 - since)
        if _R64_REDIS_SNAPSHOT_TIMER is not None:
            return True
        _R64_REDIS_SNAPSHOT_TIMER = _split_threading.Timer(delay, _r64_periodic_redis_snapshot_fire_v271)
        _R64_REDIS_SNAPSHOT_TIMER.daemon = True
        _R64_REDIS_SNAPSHOT_TIMER.start()
    return True


def _split_ping_once():
    base = _split_peer_base()
    _SPLIT_STATE['peer_last_attempt'] = _split_time.time()
    try:
        ks = globals().get('KEEP_ALIVE_STATE')
        if isinstance(ks, dict):
            ks['peer_last_attempt_at'] = now_local().isoformat(timespec='milliseconds') if callable(globals().get('now_local')) else str(_split_time.time())
    except Exception:
        pass
    if not base:
        _SPLIT_STATE['peer_last_error'] = 'PEER_SERVICE_URL empty'
        return False
    try:
        r = requests.get(base + '/peer/health', headers=_split_headers('vys-262-front-peer-r11'), timeout=12)
        _SPLIT_STATE['peer_status'] = int(r.status_code)
        if 200 <= r.status_code < 300:
            payload = {}
            try: payload = r.json() if r.content else {}
            except Exception: payload = {}
            _SPLIT_STATE['peer_last_ok'] = _split_time.time()
            _SPLIT_STATE['peer_last_error'] = ''
            try:
                ks = globals().get('KEEP_ALIVE_STATE')
                if isinstance(ks, dict):
                    ks['peer_last_ok_at'] = now_local().isoformat(timespec='milliseconds') if callable(globals().get('now_local')) else str(_split_time.time())
                    ks['peer_last_error'] = ''
                    ks['peer_last_status_code'] = int(r.status_code)
                    ks['peer_ok_count'] = int(ks.get('peer_ok_count') or 0) + 1
            except Exception:
                pass
            _SPLIT_STATE['worker_health'] = dict(payload or {})
            _SPLIT_STATE['worker_health']['seen_at'] = _split_time.time()
            return True
        _SPLIT_STATE['peer_last_error'] = f'HTTP {r.status_code}'
    except Exception as exc:
        _SPLIT_STATE['peer_last_error'] = str(exc)[:220]
        _SPLIT_STATE['peer_status'] = None
    try:
        ks = globals().get('KEEP_ALIVE_STATE')
        if isinstance(ks, dict):
            ks['peer_last_error'] = str(_SPLIT_STATE.get('peer_last_error') or '')[:220]
            ks['peer_last_status_code'] = _SPLIT_STATE.get('peer_status')
            ks['peer_fail_count'] = int(ks.get('peer_fail_count') or 0) + 1
    except Exception:
        pass
    return False


def _split_peer_loop():
    _split_time.sleep(5.0)
    while True:
        if _split_env_bool('PEER_PING_ENABLED', True):
            _split_ping_once()
        try:
            interval = int(_split_os.getenv('PEER_PING_INTERVAL_SEC', '120') or '120')
        except Exception:
            interval = 120
        _split_time.sleep(max(30, min(1800, interval)))


def _split_request_worker_full_sync_r18(reason='need_full'):
    """Queue a full rebase on HEAVY; FAST never waits for snapshot/MEGA work."""
    base, secret = _split_peer_base(), _split_secret()
    if not base or not secret:
        return False, 'worker URL/secret not configured'
    try:
        body = {'type':'sync_state', 'reason':str(reason or 'need_full')[:160], 'state_token':_split_current_state_token_v264()}
        r = requests.post(base + '/internal/job', json=body, headers=_split_headers('vys-262-front-r18-rebase'), timeout=2.5)
        if 200 <= r.status_code < 300:
            return True, f'worker full rebase queued HTTP {r.status_code}'
        return False, f'worker full rebase HTTP {r.status_code}: {r.text[:160]}'
    except Exception as exc:
        return False, f'{type(exc).__name__}: {str(exc)[:160]}'


def _split_request_sync_now(reason='change'):
    """R12 normal durability path: send only changed SQLite pages.

    A full SQLite image is sent only when the Worker reports a base mismatch, when the
    delta is abnormally large, or during the explicit graceful-shutdown checkpoint.
    """
    _SPLIT_STATE['sync_last_attempt'] = _split_time.time()
    _SPLIT_STATE['sync_reason'] = str(reason or 'change')[:160]
    ok, detail, need_full = _split_send_delta_v267(_SPLIT_STATE['sync_reason'])
    if ok:
        _SPLIT_STATE['sync_last_ok'] = _split_time.time()
        _SPLIT_STATE['sync_last_error'] = ''
        _SPLIT_STATE['sync_pending'] = False
        return True
    _SPLIT_STATE['delta_last_error'] = str(detail or '')[:220]
    if need_full:
        # R25 FAST-priority rule: never make HEAVY repeatedly pull full SQLite while
        # the user is clicking. A mismatch is reconciled after a short quiet period by
        # a Front->HEAVY snapshot push. The snapshot itself uses the R25 online SQLite
        # backup connection and therefore never owns FAST's shared SQLITE.lock.
        _SPLIT_STATE['delta_full_fallbacks'] = int(_SPLIT_STATE.get('delta_full_fallbacks') or 0) + 1
        _SPLIT_STATE['full_reconcile_pending'] = True
        try:
            _split_schedule_idle_full_reconcile_v270('delta_resync_r25:' + str(reason or 'change')[:80])
            _SPLIT_STATE['full_reconcile_last_error'] = 'R25 deferred full reconcile until UI quiet'
        except Exception as _r25_reconcile_exc:
            _SPLIT_STATE['full_reconcile_last_error'] = str(_r25_reconcile_exc)[:220]
    _SPLIT_STATE['sync_last_error'] = str(detail or 'delta sync failed')[:220]
    return False


def _split_sync_timer_fire():
    global _SPLIT_SYNC_TIMER, _SPLIT_SYNC_DUE_AT, _SPLIT_SYNC_FIRST_DIRTY_AT
    try:
        reason = str(_SPLIT_STATE.get('sync_reason') or 'change')
        # R28: page-delta generation itself required a full local SQLite backup, so
        # "tiny delta" still hammered FAST every few seconds. Raw Telegram events are
        # already durable remotely; mirror the canonical SQLite only after UI quiet.
        _split_schedule_idle_full_reconcile_v270('r28-idle:' + reason[:100], delay=float(_split_os.getenv('R28_STATE_MIRROR_DELAY_SEC','30') or '30'))
    finally:
        with _SPLIT_SYNC_LOCK:
            _SPLIT_SYNC_TIMER = None
            _SPLIT_SYNC_DUE_AT = 0.0
            _SPLIT_SYNC_FIRST_DIRTY_AT = 0.0


def _split_inside_telegram_update_v264():
    return bool(getattr(_SPLIT_UPDATE_CONTEXT, 'active', False))


def split_schedule_worker_sync_v262(reason='change', delay=None):
    """Coalesced state handoff; Telegram never waits for MEGA or snapshot transfer."""
    global _SPLIT_SYNC_TIMER, _SPLIT_SYNC_DUE_AT, _SPLIT_SYNC_FIRST_DIRTY_AT
    if not _split_env_bool('SPLIT_WORKER_SYNC_ENABLED', True):
        return False
    # One Telegram update may call save_data/config/finance hooks many times. R4
    # could arm the worker while the handler was still executing, then arm it again
    # at the post-update continuity checkpoint. Defer all those requests and emit
    # exactly one notification after the update completes.
    if _split_inside_telegram_update_v264():
        _SPLIT_STATE['sync_pending'] = True
        _SPLIT_STATE['sync_reason'] = str(reason or 'change')[:160]
        return True
    try:
        wait = float(delay if delay is not None else _split_os.getenv('SPLIT_STATE_SYNC_DELAY_SEC', '8') or '8')
    except Exception:
        wait = 1.5
    try:
        min_interval = float(_split_os.getenv('SPLIT_STATE_SYNC_MIN_INTERVAL_SEC', '30') or '30')
    except Exception:
        min_interval = 12.0
    wait = max(0.08, min(30.0, wait))
    min_interval = max(0.2, min(120.0, min_interval))
    # R15: RAW events are already remotely witnessed.  State mirroring may therefore
    # debounce short finance bursts instead of snapshotting/gzipping on every message.
    _reason_l = str(reason or '').lower()
    if 'finance' in _reason_l or 'critical' in _reason_l or 'event_commit' in _reason_l:
        wait = max(wait, 0.8)
        min_interval = max(min_interval, 1.5)
    now = _split_time.time()
    last = float(_SPLIT_STATE.get('sync_last_attempt') or 0.0)
    with _SPLIT_SYNC_LOCK:
        if _SPLIT_SYNC_FIRST_DIRTY_AT <= 0.0:
            _SPLIT_SYNC_FIRST_DIRTY_AT = now
        first_dirty = _SPLIT_SYNC_FIRST_DIRTY_AT
    try:
        max_latency = max(1.0, min(12.0, float(_split_os.getenv('SPLIT_SYNC_MAX_LATENCY_SEC','60') or '60')))
    except Exception:
        max_latency = 3.0
    due = max(now + wait, last + min_interval if last else now + wait)
    due = min(due, first_dirty + max_latency)
    due = max(now + 0.05, due)
    _SPLIT_STATE['sync_pending'] = True
    _SPLIT_STATE['sync_reason'] = str(reason or 'change')[:160]
    with _SPLIT_SYNC_LOCK:
        # R15 trailing-edge debounce: a burst of ten messages produces one mirror
        # attempt after the burst, not ten competing SQLite backups.
        if _SPLIT_SYNC_TIMER is not None:
            try:
                _SPLIT_SYNC_TIMER.cancel()
            except Exception:
                pass
        _SPLIT_SYNC_DUE_AT = due
        _SPLIT_SYNC_TIMER = _split_threading.Timer(max(0.05, due - now), _split_sync_timer_fire)
        _SPLIT_SYNC_TIMER.daemon = True
        _SPLIT_SYNC_TIMER.start()
    return True


# Final durability bindings for split mode. SQLite has already been committed by the
# normal save path; these hooks only request remote durability from Render #2.
def _v262_split_schedule_delta_backup(chat_id=None, delay=None, reason='change'):
    split_schedule_worker_sync_v262(reason=f'delta:{reason}', delay=delay)
    return True


def _v262_split_persist_critical_delta_now(chat_id):
    split_schedule_worker_sync_v262(reason=f'critical:{int(chat_id)}', delay=0.08)
    return True


def _v262_split_schedule_full_backup_only(chat_id, delay=3.0):
    split_schedule_worker_sync_v262(reason=f'full:{int(chat_id)}', delay=min(float(delay or 1.0), 5.0))
    return True


def _v262_split_mega_upload_latest_database_backup(force=False):
    split_schedule_worker_sync_v262(reason='manual_db_snapshot' if force else 'db_snapshot', delay=0.08 if force else 0.5)
    return True


def _v262_split_schedule_config_backup_for_chats(*chat_ids, delay=3.0):
    # R20: the original v262 config hook is the authoritative signal that a
    # user-visible setting changed.  Capture a small independent durable capsule
    # immediately in a background timer; do not wait for full SQLite/delta sync.
    try:
        _r25_cp = _r20_latest_config_checkpoint() if '_r20_latest_config_checkpoint' in globals() else {}
        _r25_gen = int((_r25_cp or {}).get('generation') or 0)
        if _r25_gen > int(globals().get('_R20_CAPSULE_LAST_GEN_SENT', 0) or 0):
            r20_schedule_durable_capsule('config_hook:' + ','.join(map(str, chat_ids[:8])), delay=2.0)
    except Exception:
        pass
    split_schedule_worker_sync_v262(reason='config:' + ','.join(map(str, chat_ids[:8])), delay=min(float(delay or 1.0), 5.0))
    return True


def _split_google_target(target_chat_id=None, tenant_id=None):
    try:
        tid = str(_v149_tenant_id(tenant_id, target_chat_id))
    except Exception:
        tid = str(tenant_id or globals().get('TENANT_PLATFORM_ID') or 'platform')
    cfg = tenant_google_config(tid, create=False) if callable(globals().get('tenant_google_config')) else {}
    raw = str((cfg or {}).get('spreadsheet_id') or '').strip()
    if not raw and tid == str(globals().get('TENANT_PLATFORM_ID') or ''):
        raw = str(_split_os.getenv('GOOGLE_SHEETS_SPREADSHEET_ID', '') or '').strip()
    if not raw:
        raise RuntimeError('Google Таблица не выбрана. Откройте /google → «Куда выгружать Excel» и пришлите ссылку таблицы.')
    try:
        sheet_id = _v149_google_id(raw, 'sheet')
    except Exception:
        sheet_id = str(raw).strip()
    return tid, sheet_id


def _split_annotations_for_google(rows, layout, annotations_override, include_annotations):
    if not include_annotations:
        return {}
    try:
        if layout == 'compact':
            _styles, ann, _freeze, _widths = _modern_compact_excel_styles_comments(rows, annotations_override or {})
        elif layout == 'category_compact':
            _styles, ann, _freeze, _widths = _modern_category_no_description_styles_comments(rows, annotations_override or {})
        else:
            _styles, ann, _freeze, _widths = _modern_category_excel_styles_comments(rows)
            if annotations_override is not None:
                ann = dict(annotations_override or {})
        return ann or {}
    except Exception:
        return dict(annotations_override or {})


def _v262_split_google_sheets_create_category_report(title, rows, layout='category', annotations_override=None, include_annotations=True, **kwargs):
    """Queue Google Sheets work on Render #2 and return immediately with a job token."""
    if not _split_env_bool('SPLIT_GOOGLE_REMOTE_ENABLED', True):
        raise RuntimeError('Google Sheets worker delegation disabled')
    base, secret = _split_peer_base(), _split_secret()
    if not base or not secret:
        raise RuntimeError('Google Sheets worker is not configured')
    target_chat_id = kwargs.get('target_chat_id')
    notify_result = bool(kwargs.get('notify_result', True))
    recipient_chat_id = kwargs.get('recipient_chat_id') or target_chat_id
    tid, spreadsheet_id = _split_google_target(target_chat_id=target_chat_id, tenant_id=kwargs.get('tenant_id'))
    _SPLIT_STATE['google_last_attempt'] = _split_time.time()
    annotations = _split_annotations_for_google(rows, str(layout or 'category'), annotations_override, bool(include_annotations))
    encoded_notes = {f'{int(r)},{int(c)}': str(note) for (r, c), note in annotations.items() if str(note or '').strip()}
    client_job_id = _split_secrets.token_hex(12)
    body = {
        'job_id': client_job_id,
        'title': str(title or 'Статьи')[:300],
        'rows': rows,
        'layout': str(layout or 'category'),
        'annotations': encoded_notes,
        'include_annotations': bool(include_annotations),
        'spreadsheet_id': spreadsheet_id,
        'tenant_id': tid,
        'target_chat_id': target_chat_id,
        'recipient_chat_id': recipient_chat_id,
        'notify_result': notify_result,
    }
    try:
        r = requests.post(base + '/internal/google/sheet', json=body, headers=_split_headers('vys-262-front-google'), timeout=30)
        payload = r.json() if r.content and 'json' in str(r.headers.get('content-type', '')).lower() else {}
        if r.status_code == 202:
            job_id = str(payload.get('job_id') or client_job_id)
            _SPLIT_STATE['google_last_job'] = job_id
            _SPLIT_STATE['google_last_error'] = ''
            return 'worker-job:' + job_id
        if 200 <= r.status_code < 300 and payload.get('url'):
            _SPLIT_STATE['google_last_ok'] = _split_time.time()
            _SPLIT_STATE['google_last_error'] = ''
            return str(payload.get('url'))
        _SPLIT_STATE['google_last_error'] = f'HTTP {r.status_code}: {r.text[:220]}'
        raise RuntimeError('Google Sheets worker: ' + _SPLIT_STATE['google_last_error'])
    except Exception as exc:
        _SPLIT_STATE['google_last_error'] = str(exc)[:240]
        raise


def _split_google_result_seen(job_id):
    now = _split_time.time()
    with _SPLIT_GOOGLE_RESULT_LOCK:
        stale = [k for k, ts in _SPLIT_GOOGLE_RESULTS.items() if now - float(ts) > 86400]
        for key in stale:
            _SPLIT_GOOGLE_RESULTS.pop(key, None)
        if job_id in _SPLIT_GOOGLE_RESULTS:
            return True
        _SPLIT_GOOGLE_RESULTS[job_id] = now
        return False


@app.route('/internal/split/google-result', methods=['POST'])
def split_front_google_result_v262():
    """Worker callback. Duplicate callbacks are acknowledged without duplicate Telegram messages."""
    if not _split_authorized_request():
        return ({'ok': False}, 404)
    body = request.get_json(silent=True) or {}
    job_id = str(body.get('job_id') or '').strip()
    if not job_id:
        return ({'ok': False, 'error': 'job_id required'}, 400)
    if _split_google_result_seen(job_id):
        return ({'ok': True, 'duplicate': True}, 200)
    try:
        recipient_chat_id = int(body.get('recipient_chat_id') or 0)
    except Exception:
        recipient_chat_id = 0
    if not recipient_chat_id:
        return ({'ok': False, 'error': 'recipient_chat_id required'}, 400)
    ok = bool(body.get('ok'))
    notify_result = bool(body.get('notify_result', True))
    if ok:
        url = str(body.get('url') or '').strip()
        title = str(body.get('title') or 'Google Excel').strip()[:180]
        _SPLIT_STATE['google_last_ok'] = _split_time.time()
        _SPLIT_STATE['google_last_error'] = ''
        if notify_result:
            text = f'✅ 📊 Google Excel готов\n{title}\n\n{url}'
            bot.send_message(recipient_chat_id, text, disable_web_page_preview=True)
    else:
        err = str(body.get('error') or 'неизвестная ошибка')[:700]
        _SPLIT_STATE['google_last_error'] = err[:240]
        if notify_result:
            bot.send_message(recipient_chat_id, '❌ Google Excel не создан на Render #2:\n' + err)
    return ({'ok': True}, 200)


def _split_tenant_google_status_text(tenant_id):
    tid = str(tenant_id)
    row = tenant_get(tid) or {}
    cfg = tenant_google_config(tid)
    raw = str(cfg.get('spreadsheet_id') or '')
    if not raw and tid == str(globals().get('TENANT_PLATFORM_ID') or ''):
        raw = str(_split_os.getenv('GOOGLE_SHEETS_SPREADSHEET_ID', '') or '')
    try:
        shown = _v149_mask_id(raw) if raw else 'не выбрана'
    except Exception:
        shown = (raw[:8] + '…' + raw[-6:]) if len(raw) > 18 else (raw or 'не выбрана')
    settings = cfg.get('export_settings') or {}
    return (
        f"📊 GOOGLE EXCEL · {row.get('name') or tid}\n\n"
        f"Service account: ✅ Render #2\n"
        f"Куда выгружать: {shown}\n"
        f"Google Sheets: {'✅ ВКЛ' if settings.get('sheet_enabled', True) else '⬜ ВЫКЛ'}\n"
        f"История: {len(cfg.get('history') or [])}\n"
        f"Ошибки: {len(cfg.get('errors') or [])}\n\n"
        "Нажмите «Куда выгружать Excel» и пришлите ссылку или ID Google Таблицы. "
        "Сам service_account хранится только на Render #2. Выбранную таблицу нужно расшарить его client_email как Редактору."
    )[:3900]


def _split_tenant_google_keyboard(tenant_id):
    tid = str(tenant_id)
    cfg = tenant_google_config(tid)
    settings = cfg.get('export_settings') or {}
    kb = types.InlineKeyboardMarkup(row_width=1)
    kb.row(IB('📊 Куда выгружать Excel', callback_data='v149:google:sheet'))
    kb.row(IB(f"{('✅' if settings.get('sheet_enabled', True) else '⬜')} Google Sheets: {('ВКЛ' if settings.get('sheet_enabled', True) else 'ВЫКЛ')}", callback_data='v149:google:toggle_sheet'))
    kb.row(IB('🧪 Проверить выбранную таблицу', callback_data='v149:google:test'))
    kb.row(IB(f"📜 История ({len(cfg.get('history') or [])})", callback_data='v149:google:history'), IB(f"⚠️ Ошибки ({len(cfg.get('errors') or [])})", callback_data='v149:google:errors'))
    return kb


def _split_tenant_google_test(tenant_id):
    try:
        tid, spreadsheet_id = _split_google_target(tenant_id=str(tenant_id))
        base = _split_peer_base()
        if not base or not _split_secret():
            return False, '❌ Render #2 не настроен.'
        r = requests.post(base + '/internal/google/test', json={'spreadsheet_id': spreadsheet_id, 'tenant_id': tid}, headers=_split_headers('vys-262-front-google-test'), timeout=35)
        payload = r.json() if r.content else {}
        if 200 <= r.status_code < 300 and payload.get('ok'):
            return True, f"✅ Google Таблица доступна через Render #2.\nНазвание: {payload.get('title') or '—'}\nService account: {payload.get('service_email') or '—'}"
        return False, '❌ Проверка Google: ' + str(payload.get('error') or r.text[:500])
    except Exception as exc:
        return False, '❌ Проверка Google: ' + str(exc)[:600]


def _split_reject_front_google_credentials(*args, **kwargs):
    raise RuntimeError('Service account не загружается в Telegram-фронт. GOOGLE_SERVICE_ACCOUNT_JSON задаётся только в Environment Render #2.')


# New split Google callbacks are legitimate windows and must be declared.
try:
    WINDOW_MARKER_CONSTANTS.setdefault('v149:google:*', 'Ф233')
except Exception:
    pass


def _split_v167_google_upsert_named_tab(tab_title, rows, target_chat_id, layout='category', annotations_override=None):
    """Route legacy v167/v261 scheduled Google refreshes to Render #2."""
    return _v262_split_google_sheets_create_category_report(
        tab_title, rows, layout=layout, annotations_override=annotations_override,
        include_annotations=True, target_chat_id=int(target_chat_id),
        recipient_chat_id=int(target_chat_id), notify_result=False,
    )


# Apply final bindings after 89_callback_final.py.
schedule_delta_backup = _v262_split_schedule_delta_backup
persist_critical_delta_now = _v262_split_persist_critical_delta_now
schedule_full_backup_only = _v262_split_schedule_full_backup_only
mega_upload_latest_database_backup = _v262_split_mega_upload_latest_database_backup
schedule_config_backup_for_chats = _v262_split_schedule_config_backup_for_chats
_google_sheets_create_category_report = _v262_split_google_sheets_create_category_report
_v167_google_upsert_named_tab = _split_v167_google_upsert_named_tab
tenant_google_status_text = _split_tenant_google_status_text
tenant_google_keyboard = _split_tenant_google_keyboard
tenant_google_test = _split_tenant_google_test
tenant_google_set_credentials = _split_reject_front_google_credentials

# R11: no legacy MEGA delta is allowed to execute on the fast Front. Some old
# delayed callbacks may have been armed before this final split module loaded; make
# their runtime target a harmless drain so diagnostics do not keep reporting
# `shard delta upload failed` while Worker owns Redis/MEGA durability.
def _r11_split_legacy_delta_noop():
    try:
        lock = globals().get('_delta_state_lock')
        pending = globals().get('_delta_pending_chats')
        if lock is not None:
            with lock:
                if isinstance(pending, set): pending.clear()
        elif isinstance(pending, set):
            pending.clear()
        domains = globals().get('_V240_PENDING_DOMAINS')
        if isinstance(domains, dict): domains.clear()
        globals()['_delta_last_error'] = ''
    except Exception:
        pass
    return True

_run_delta_batch = _r11_split_legacy_delta_noop
_V234_MEGA_RUN_DELTA_BATCH = _r11_split_legacy_delta_noop
_r11_split_legacy_delta_noop()

# R48 FINAL: R11 persistence wrapper folded into persist_finance_chat_local_fast in 04.

_split_threading.Thread(target=_split_peer_loop, name='v262-front-peer', daemon=True).start()

# ---------------------------------------------------------------------------
# r4 continuity layer: deploy/restart must be invisible to the Telegram user.
# Canonical business/config state already lives in SQLite.  This layer adds the
# small RAM-only interaction state that makes existing buttons/windows/sessions
# continue working after a new Render instance starts.
# ---------------------------------------------------------------------------
_CONTINUITY_META_KIND_V263 = 'runtime_continuity_v263'
_CONTINUITY_META_KEY_V263 = 'latest'
_CONTINUITY_MAX_ITEMS_V263 = 6000
_CONTINUITY_SKIP_V263 = object()
_CONTINUITY_NAMES_V263 = (
    '_short_callback_store',
    '_WINDOW_NAV_HISTORY',
    '_category_order_selection',
    '_category_other_sort_state',
    '_timer_input_sessions',
    '_careful_restore_sessions',
    '_dozvon_sessions',
    '_dozvon_target_index',
    '_JOURNAL_FILENAME_WAIT',
    '_REMINDER_UI_BINDINGS',
    '_REMINDER_COMPLETED_DELETE_SELECTION',
    '_V172_INPUT_WAIT',
    '_V172_SEARCH_CACHE',
    '_V174_INPUT_WAIT',
    '_V221_OWNER_MSG_PENDING',
    '_V221_LIVE_MARKUP',
    '_V224_INLINE_HELPER_STATE',
    '_V160_ANNOTATION_PENDING',
    '_V160_LAST_WINDOW_META',
    '_V160_CALLBACK_IDS',
    '_V161_DELETE_STATE',
    '_V161_WINDOW_TOKENS',
    '_V164_WINDOW_VIEW',
    '_V196_SESSIONS',
    '_V196_PANEL_MESSAGES',
    '_V196_LAST_BASE_BY_KEY',
    '_V196_LAST_META_BY_TOKEN',
    '_V196_ACTIVE_WORKING_BY_KEY',
    '_V212_LAST_BASE_BY_SCOPE_KEY',
    '_V212_CATALOG_BY_SCOPE',
    '_KEEPALIVE_INPUT_WAIT',
    '_secret_sequence_state',
    '_o9_secret_clicks',
    '_V153_RESTORE_PENDING',
    '_V153_CALLBACK_RECEIPTS',
    '_V153_CALLBACK_SIGNATURES',
    # R6: additional user-facing interaction state discovered by full runtime audit.
    '_V153_WAITING_EXPORTS',
    '_V178_MEGA_PRIORITY_WAITING',
    '_V240_PAR_WAITING',
    # R6 full interaction audit: serializable user-visible sessions that previously
    # vanished on deploy even when the canonical chat/settings data survived.
    '_owner_json_restore_prompts',
    '_timer_input_sessions',
    '_careful_restore_sessions',
    '_dozvon_sessions',
    '_category_order_selection',
    '_category_other_sort_state',
    '_INLINE_FALLBACK_TEXT',
    '_V153_READY_EXPORTS',
    '_V153_UI_CACHE',
    '_V156_PROCESS_UI',
    '_V160_FAST_EDIT_LAST',
    '_V146_FAILED_TASK_RUNTIME_ERRORS',
)
_CONTINUITY_SCALARS_V263 = ('restore_mode', '_short_callback_counter')

# R17: automatically include safe RAM-only interaction containers that future UI
# modules may add without remembering to extend the static whitelist.  We purposely
# exclude process/runtime/network objects so a deploy never resurrects old locks,
# queues, timers, transport caches or worker state.
_CONTINUITY_DYNAMIC_HINTS_R17 = ('SESSION', 'WAIT', 'PENDING', 'SELECTION', 'BINDING', 'CALLBACK', 'WINDOW', 'INPUT')
_CONTINUITY_DYNAMIC_DENY_R17 = ('LOCK', 'THREAD', 'TIMER', 'QUEUE', 'POOL', 'CLIENT', 'SOCKET', 'EXECUTOR', 'SPLIT_', 'MEGA_', 'REDIS_', 'TG_', 'TELEGRAM_', 'MEDIA_GROUP', 'FORWARD_OUTCOME')

def _continuity_dynamic_names_r17():
    out = []
    for name, value in list(globals().items()):
        if name in _CONTINUITY_NAMES_V263 or name in _CONTINUITY_SCALARS_V263:
            continue
        upper = str(name).upper()
        if not str(name).startswith('_') or not any(h in upper for h in _CONTINUITY_DYNAMIC_HINTS_R17):
            continue
        if any(bad in upper for bad in _CONTINUITY_DYNAMIC_DENY_R17):
            continue
        if isinstance(value, (dict, list, set, tuple, _split_collections.deque)):
            out.append(str(name))
    return tuple(sorted(set(out)))

# R6 persistent user-state shadow. The normal SQLite root/chats remain canonical,
# but this compact duplicate protects settings/UI/task/tenant metadata from any
# missed point-save or cross-chat mutation. Financial cold ledgers are deliberately
# excluded so this layer can never roll back accounting records.
_USER_STATE_META_KIND_V265 = 'user_state_shadow_v265'
_USER_STATE_META_KEY_V265 = 'latest'
_USER_STATE_ROOT_EXCLUDE_V265 = {'overall_balance', 'records', 'bot_errors', '_state_meta'}
_USER_STATE_CHAT_EXCLUDE_V265 = set(globals().get('LOWRAM_COLD_KEYS') or set()) | {'balance', 'next_id'}

def _user_state_json_copy_v265(value):
    try:
        return _split_json.loads(_split_json.dumps(value, ensure_ascii=False, separators=(',', ':'), default=str))
    except Exception:
        return None

def user_state_shadow_capture_v265(reason='checkpoint', persist=True):
    try:
        root_src = _sqlite_pack_root(data) if callable(globals().get('_sqlite_pack_root')) else {k:v for k,v in (data or {}).items() if k != 'chats'}
        root = {}
        for key, value in (root_src or {}).items():
            if str(key) in _USER_STATE_ROOT_EXCLUDE_V265:
                continue
            copied = _user_state_json_copy_v265(value)
            if copied is not None:
                root[str(key)] = copied
        chats = {}
        for cid, store in ((data or {}).get('chats') or {}).items():
            if not isinstance(store, dict):
                continue
            meta = {}
            try:
                items = dict.items(store)
            except Exception:
                items = []
            for key, value in items:
                if str(key) in _USER_STATE_CHAT_EXCLUDE_V265:
                    continue
                copied = _user_state_json_copy_v265(value)
                if copied is not None:
                    meta[str(key)] = copied
            chats[str(cid)] = meta
        previous = SQLITE.get_meta(_USER_STATE_META_KIND_V265, _USER_STATE_META_KEY_V265, {}) or {}
        seq = int((previous or {}).get('seq') or 0) + 1
        payload = {
            'schema': 2, 'seq': seq, 'saved_at': _split_time.time(),
            'reason': str(reason or 'checkpoint')[:180], 'front_version': _SPLIT_FRONT_VERSION,
            'root': root, 'chats': chats,
            'counts': {'root_keys': len(root), 'chats': len(chats),
                       'chat_settings': sum(1 for v in chats.values() if isinstance(v, dict) and isinstance(v.get('settings'), dict)),
                       'tasks': len((root.get('_tasks_v172') or {})) if isinstance(root.get('_tasks_v172'), dict) else 0,
                       'reminders': len((root.get('reminders') or root.get('_reminders') or {})) if isinstance((root.get('reminders') or root.get('_reminders') or {}), dict) else 0,
                       'tenants': len((((root.get('_global_settings') or {}).get('tenants_v148') or {}).get('tenants') or {})) if isinstance(((root.get('_global_settings') or {}).get('tenants_v148') or {}), dict) else 0,
                       'additional_owners': len(root.get('additional_owners') or root.get('additional_owner_ids') or []) if isinstance((root.get('additional_owners') or root.get('additional_owner_ids') or []), (list, tuple, set, dict)) else 0},
        }
        if persist:
            SQLITE.set_meta(_USER_STATE_META_KIND_V265, _USER_STATE_META_KEY_V265, payload)
        return payload
    except Exception as exc:
        try: log_error(f'USER_STATE shadow capture R6: {exc}')
        except Exception: pass
        return {}

def user_state_shadow_apply_v265(loaded):
    if not isinstance(loaded, dict):
        return loaded
    try:
        payload = SQLITE.get_meta(_USER_STATE_META_KIND_V265, _USER_STATE_META_KEY_V265, {}) or {}
    except Exception:
        payload = {}
    if not isinstance(payload, dict) or not payload:
        return loaded
    try:
        incoming_seq = int(payload.get('seq') or 0)
        applied_seq = int(globals().get('_USER_STATE_APPLIED_SEQ_R19', 0) or 0)
        if applied_seq and incoming_seq and incoming_seq < applied_seq:
            log_error(f'USER_STATE R19 stale shadow rejected seq={incoming_seq} < applied={applied_seq}')
            return loaded
        globals()['_USER_STATE_APPLIED_SEQ_R19'] = max(applied_seq, incoming_seq)
    except Exception:
        pass
    restored_root = 0; restored_chats = 0; restored_settings = 0
    root = payload.get('root') or {}
    if isinstance(root, dict):
        for key, value in root.items():
            if str(key) in _USER_STATE_ROOT_EXCLUDE_V265:
                continue
            loaded[str(key)] = _user_state_json_copy_v265(value)
            restored_root += 1
    chats = loaded.setdefault('chats', {})
    shadow_chats = payload.get('chats') or {}
    if isinstance(shadow_chats, dict):
        for cid, meta in shadow_chats.items():
            if not isinstance(meta, dict):
                continue
            current = chats.get(str(cid))
            if not isinstance(current, dict):
                current = {}
                chats[str(cid)] = current
            for key, value in meta.items():
                if str(key) in _USER_STATE_CHAT_EXCLUDE_V265:
                    continue
                current[str(key)] = _user_state_json_copy_v265(value)
            try:
                if LOWRAM_ENABLED and not isinstance(current, ColdChatStore):
                    current = _lowram_wrap_store(int(cid), current)
                    chats[str(cid)] = current
            except Exception:
                pass
            restored_chats += 1
            if isinstance(meta.get('settings'), dict):
                restored_settings += 1
    try:
        log_info(f"USER_STATE R6 restored shadow seq={payload.get('seq')} root={restored_root} chats={restored_chats} settings={restored_settings}")
    except Exception:
        pass
    return loaded

# Apply the shadow as part of canonical load, before tenant/bootstrap defaults can
# create a factory profile. This is intentionally after normal SQLite unpacking.
_LOAD_DATA_CORE = load_data
def load_data():
    loaded = _LOAD_DATA_CORE()
    return user_state_shadow_apply_v265(loaded)


def _continuity_encode_v263(value, depth=0):
    if depth > 12:
        return _CONTINUITY_SKIP_V263
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, bytes):
        # No user interaction state should require raw binary; storing it as hex
        # avoids invalid JSON if a small identifier ever appears here.
        return {'__v263_type__': 'bytes', 'value': value.hex()[:131072]}
    if isinstance(value, dict):
        try:
            items = list(value.items())[:_CONTINUITY_MAX_ITEMS_V263]
        except Exception:
            return _CONTINUITY_SKIP_V263
        out = []
        for key, item in items:
            ek = _continuity_encode_v263(key, depth + 1)
            ev = _continuity_encode_v263(item, depth + 1)
            if ek is _CONTINUITY_SKIP_V263 or ev is _CONTINUITY_SKIP_V263:
                continue
            out.append([ek, ev])
        return {'__v263_type__': 'dict', 'items': out}
    if isinstance(value, tuple):
        vals = []
        for item in list(value)[:_CONTINUITY_MAX_ITEMS_V263]:
            enc = _continuity_encode_v263(item, depth + 1)
            if enc is not _CONTINUITY_SKIP_V263:
                vals.append(enc)
        return {'__v263_type__': 'tuple', 'items': vals}
    if isinstance(value, (list, set, _split_collections.deque)):
        typ = 'set' if isinstance(value, set) else 'deque' if isinstance(value, _split_collections.deque) else 'list'
        vals = []
        try:
            source = list(value)[:_CONTINUITY_MAX_ITEMS_V263]
        except Exception:
            return _CONTINUITY_SKIP_V263
        for item in source:
            enc = _continuity_encode_v263(item, depth + 1)
            if enc is not _CONTINUITY_SKIP_V263:
                vals.append(enc)
        return {'__v263_type__': typ, 'items': vals}
    # datetime/date values are rare in UI sessions; preserve their text instead
    # of failing the whole continuity snapshot.
    iso = getattr(value, 'isoformat', None)
    if callable(iso):
        try:
            return {'__v263_type__': 'iso', 'value': str(iso())}
        except Exception:
            pass
    return _CONTINUITY_SKIP_V263


def _continuity_decode_v263(value, depth=0):
    if depth > 12:
        return None
    if not isinstance(value, dict) or '__v263_type__' not in value:
        if isinstance(value, list):
            return [_continuity_decode_v263(x, depth + 1) for x in value]
        return value
    typ = str(value.get('__v263_type__') or '')
    if typ == 'bytes':
        try:
            return bytes.fromhex(str(value.get('value') or ''))
        except Exception:
            return b''
    if typ == 'dict':
        out = {}
        for pair in value.get('items') or []:
            if not isinstance(pair, list) or len(pair) != 2:
                continue
            key = _continuity_decode_v263(pair[0], depth + 1)
            val = _continuity_decode_v263(pair[1], depth + 1)
            try:
                out[key] = val
            except Exception:
                pass
        return out
    vals = [_continuity_decode_v263(x, depth + 1) for x in (value.get('items') or [])]
    if typ == 'tuple':
        return tuple(vals)
    if typ == 'set':
        try:
            return set(vals)
        except Exception:
            return set()
    if typ == 'deque':
        return _split_collections.deque(vals)
    if typ == 'list':
        return vals
    if typ == 'iso':
        return str(value.get('value') or '')
    return value


def _continuity_apply_v263(name, restored):
    current = globals().get(name, _CONTINUITY_SKIP_V263)
    try:
        if isinstance(current, dict) and isinstance(restored, dict):
            current.clear(); current.update(restored); return True
        if isinstance(current, set) and isinstance(restored, (set, list, tuple)):
            current.clear(); current.update(restored); return True
        if isinstance(current, list) and isinstance(restored, (list, tuple)):
            current[:] = list(restored); return True
        if isinstance(current, _split_collections.deque) and isinstance(restored, (list, tuple, _split_collections.deque)):
            current.clear(); current.extend(restored); return True
        globals()[name] = restored
        return True
    except Exception:
        return False


def continuity_capture_v263(reason='checkpoint'):
    """Persist RAM-only user interaction continuity inside canonical SQLite."""
    payload = {
        'schema': 2,
        'saved_at': _split_time.time(),
        'reason': str(reason or 'checkpoint')[:180],
        'front_version': _SPLIT_FRONT_VERSION,
        'globals': {},
        'dynamic_globals_r17': {},
        'scalars': {},
    }
    for name in _CONTINUITY_NAMES_V263:
        if name not in globals():
            continue
        enc = _continuity_encode_v263(globals().get(name))
        if enc is not _CONTINUITY_SKIP_V263:
            payload['globals'][name] = enc
    for name in _CONTINUITY_SCALARS_V263:
        if name not in globals():
            continue
        enc = _continuity_encode_v263(globals().get(name))
        if enc is not _CONTINUITY_SKIP_V263:
            payload['scalars'][name] = enc
    for name in _continuity_dynamic_names_r17():
        enc = _continuity_encode_v263(globals().get(name))
        if enc is not _CONTINUITY_SKIP_V263:
            payload['dynamic_globals_r17'][name] = enc
    # Existing Telegram message IDs/windows are logical root state; add a compact
    # count here for diagnostics while the actual records stay in the normal root.
    try:
        payload['ui_counts'] = {
            'active_message_chats': len((data.get('active_messages') or {})),
            'open_windows': len((data.get('open_window_registry') or {})),
            'chat_count': len((data.get('chats') or {})),
        }
    except Exception:
        payload['ui_counts'] = {}
    SQLITE.set_meta(_CONTINUITY_META_KIND_V263, _CONTINUITY_META_KEY_V263, payload)
    return payload


def continuity_restore_v263():
    """Restore interaction state before main() starts accepting Telegram updates."""
    try:
        payload = SQLITE.get_meta(_CONTINUITY_META_KIND_V263, _CONTINUITY_META_KEY_V263, {}) or {}
    except Exception:
        return {'ok': False, 'reason': 'meta_read_failed'}
    if not isinstance(payload, dict) or not payload:
        return {'ok': False, 'reason': 'no_snapshot'}
    restored_names = []
    for name, raw in (payload.get('globals') or {}).items():
        if name not in _CONTINUITY_NAMES_V263:
            continue
        if _continuity_apply_v263(name, _continuity_decode_v263(raw)):
            restored_names.append(name)
    dynamic_allowed = set(_continuity_dynamic_names_r17())
    for name, raw in (payload.get('dynamic_globals_r17') or {}).items():
        if name not in dynamic_allowed:
            continue
        if _continuity_apply_v263(name, _continuity_decode_v263(raw)):
            restored_names.append(name)
    for name, raw in (payload.get('scalars') or {}).items():
        if name not in _CONTINUITY_SCALARS_V263:
            continue
        if _continuity_apply_v263(name, _continuity_decode_v263(raw)):
            restored_names.append(name)
    # Remove expired short callbacks; valid old Telegram buttons remain clickable.
    try:
        now = _split_time.time()
        ttl = float(globals().get('SHORT_CALLBACK_TTL_SECONDS') or 21600)
        store = globals().get('_short_callback_store')
        if isinstance(store, dict):
            for token, row in list(store.items()):
                if now - float((row or {}).get('ts') or 0.0) > ttl:
                    store.pop(token, None)
    except Exception:
        pass
    try:
        log_info(f"CONTINUITY R20 restored names={len(restored_names)} saved_at={payload.get('saved_at')} ui={payload.get('ui_counts') or {}}")
    except Exception:
        pass
    return {'ok': True, 'restored': restored_names, 'saved_at': payload.get('saved_at')}


def continuity_checkpoint_v263(chat_id=None, reason='update', full=False, schedule=True):
    """Commit logical + RAM continuity locally, then asynchronously hand it to worker."""
    try:
        if full:
            _SAVE_DATA_CORE(data, full=True)
        elif chat_id is not None:
            _SAVE_DATA_CORE(data, chat_ids=[int(chat_id)])
        else:
            _SAVE_DATA_CORE(data, root_only=True)
    except Exception as exc:
        try: log_error(f'CONTINUITY local save R4: {exc}')
        except Exception: pass
    try:
        user_state_shadow_capture_v265(reason)
        continuity_capture_v263(reason)
        _split_mark_state_changed_v264(f'continuity:{reason}')
    except Exception as exc:
        try: log_error(f'CONTINUITY snapshot R5: {exc}')
        except Exception: pass
    if schedule:
        try:
            split_schedule_worker_sync_v262(reason=f'continuity:{reason}', delay=0.35)
        except Exception:
            pass
    return True



# R20: v262-style independent durable configuration/user-state capsule.
# Full SQLite remains the accounting/state baseline, but user settings must never rely
# on a full snapshot completing.  This compact checkpoint is built off the Telegram
# handler thread and stored monotonically by HEAVY/Redis.
_R20_CAPSULE_LOCK = _split_threading.RLock()
_R20_CAPSULE_TIMER = None
_R20_CAPSULE_FIRST_DIRTY_AT = 0.0
_R20_CAPSULE_REASON = ''
_R20_CAPSULE_LAST_GEN_SENT = 0
_R20_CAPSULE_LAST_SEQ_SENT = 0

def _r20_latest_config_checkpoint():
    try:
        fn = globals().get('config_guard_latest_local_v234')
        row = fn() if callable(fn) else {}
        return row if isinstance(row, dict) else {}
    except Exception:
        return {}

def _r20_capsule_build(reason='state_change'):
    # Capture the logical shadow in this background lane. Financial cold ledgers are
    # excluded by user_state_shadow_capture_v265 by design.
    user_state = user_state_shadow_capture_v265('r25-capsule:' + str(reason or '')[:120], persist=False) or {}
    config_cp = _r20_latest_config_checkpoint()
    try:
        with _SPLIT_STATE_REV_LOCK_R18:
            rev = dict(_SPLIT_STATE_REV_MEM_R27 or {})
        if not rev:
            rev = SQLITE.get_meta(_SPLIT_STATE_REV_KIND_R18, _SPLIT_STATE_REV_KEY_R18, {}) or {}
    except Exception:
        rev = {}
    return {
        'kind': 'vys262_durable_capsule_r20', 'schema': 1,
        'saved_at': _split_time.time(), 'reason': str(reason or '')[:160],
        'front_version': _SPLIT_FRONT_VERSION,
        'user_state': user_state,
        'config_checkpoint': config_cp,
        'state_revision': rev,
        'user_state_seq': int((user_state or {}).get('seq') or 0),
        'config_generation': int((config_cp or {}).get('generation') or 0),
    }

def _r20_capsule_redis_key():
    return str(_split_os.getenv('WORKER_REDIS_CAPSULE_KEY', 'vys262:durable_capsule:r20') or 'vys262:durable_capsule:r20').strip()

def _r20_capsule_store_redis(payload: dict, packed: bytes):
    if _split_redis is None:
        return False, 'redis package unavailable'
    url = _r61_effective_redis_url()
    if not url:
        return False, 'REDIS_URL empty'
    try:
        client = _split_redis.Redis.from_url(url, socket_connect_timeout=0.5, socket_timeout=1.5, health_check_interval=30)
        key = _r20_capsule_redis_key()
        merged = dict(payload or {})
        try:
            old_raw = client.get(key)
            old = _split_json.loads(_split_gzip.decompress(old_raw).decode('utf-8')) if old_raw else {}
        except Exception:
            old = {}
        if isinstance(old, dict) and old:
            old_seq = int(old.get('user_state_seq') or ((old.get('user_state') or {}).get('seq') or 0))
            new_seq = int(merged.get('user_state_seq') or ((merged.get('user_state') or {}).get('seq') or 0))
            if old_seq > new_seq:
                merged['user_state'] = old.get('user_state') or {}
                merged['user_state_seq'] = old_seq
            old_gen = int(old.get('config_generation') or ((old.get('config_checkpoint') or {}).get('generation') or 0))
            new_gen = int(merged.get('config_generation') or ((merged.get('config_checkpoint') or {}).get('generation') or 0))
            if old_gen > new_gen:
                merged['config_checkpoint'] = old.get('config_checkpoint') or {}
                merged['config_generation'] = old_gen
            try:
                if float(((old.get('state_revision') or {}).get('saved_at') or 0.0)) > float(((merged.get('state_revision') or {}).get('saved_at') or 0.0)):
                    merged['state_revision'] = old.get('state_revision') or {}
            except Exception:
                pass
            merged['saved_at'] = max(float(old.get('saved_at') or 0.0), float(merged.get('saved_at') or 0.0))
        packed = _split_gzip.compress(_split_json.dumps(merged, ensure_ascii=False, separators=(',',':'), default=str).encode('utf-8'), compresslevel=3)
        seq = int(merged.get('user_state_seq') or 0); gen = int(merged.get('config_generation') or 0)
        meta = {'user_state_seq': seq, 'config_generation': gen,
                'saved_at': float(merged.get('saved_at') or _split_time.time()),
                'size': len(packed), 'source': 'front-r20'}
        pipe = client.pipeline(transaction=True)
        pipe.set(key, packed)
        pipe.set(key + ':meta', _split_json.dumps(meta, separators=(',',':')))
        pipe.execute()
        return True, f'redis capsule stored seq={seq} gen={gen}'
    except Exception as exc:
        return False, f'{type(exc).__name__}: {str(exc)[:180]}'

def _r20_capsule_push_now(reason='state_change'):
    global _R20_CAPSULE_LAST_GEN_SENT, _R20_CAPSULE_LAST_SEQ_SENT
    _SPLIT_STATE['capsule_last_attempt'] = _split_time.time()
    try:
        payload = _r20_capsule_build(reason)
        raw = _split_json.dumps(payload, ensure_ascii=False, separators=(',',':'), default=str).encode('utf-8')
        packed = _split_gzip.compress(raw, compresslevel=3)
        max_bytes = 8 * 1024 * 1024
        if len(packed) > max_bytes:
            raise RuntimeError(f'capsule too large: {len(packed)}')
        seq = int(payload.get('user_state_seq') or 0)
        gen = int(payload.get('config_generation') or 0)
        # Shared Redis is the fastest durable witness and survives either Render being redeployed.
        redis_ok, redis_detail = _r20_capsule_store_redis(payload, packed)
        worker_ok = False; worker_detail = ''
        base, secret = _split_peer_base(), _split_secret()
        if base and secret:
            try:
                r = requests.post(base + '/internal/capsule', data=packed,
                    headers={**_split_headers('vys-262-front-capsule-r20'), 'Content-Type':'application/json', 'Content-Encoding':'gzip'}, timeout=3.0)
                worker_ok = 200 <= r.status_code < 300
                worker_detail = f'HTTP {r.status_code}' if worker_ok else f'HTTP {r.status_code}: {r.text[:120]}'
            except Exception as exc:
                worker_detail = f'{type(exc).__name__}: {str(exc)[:140]}'
        if redis_ok or worker_ok:
            _R20_CAPSULE_LAST_GEN_SENT = max(_R20_CAPSULE_LAST_GEN_SENT, gen)
            _R20_CAPSULE_LAST_SEQ_SENT = max(_R20_CAPSULE_LAST_SEQ_SENT, seq)
            _SPLIT_STATE['capsule_last_ok'] = _split_time.time()
            _SPLIT_STATE['capsule_last_error'] = ''
            _SPLIT_STATE['capsule_last_seq'] = seq
            _SPLIT_STATE['capsule_last_generation'] = gen
            return True
        _SPLIT_STATE['capsule_last_error'] = f'redis={redis_detail}; worker={worker_detail}'[:240]
    except Exception as exc:
        _SPLIT_STATE['capsule_last_error'] = f'{type(exc).__name__}: {str(exc)[:220]}'
        try: log_error('R20 durable capsule: ' + _SPLIT_STATE['capsule_last_error'])
        except Exception: pass
    return False

def _r20_capsule_timer_fire():
    global _R20_CAPSULE_TIMER, _R20_CAPSULE_FIRST_DIRTY_AT, _R20_CAPSULE_REASON
    with _R20_CAPSULE_LOCK:
        reason = str(_R20_CAPSULE_REASON or 'coalesced')
        _R20_CAPSULE_TIMER = None
        _R20_CAPSULE_FIRST_DIRTY_AT = 0.0
        _R20_CAPSULE_REASON = ''
    return _r20_capsule_push_now(reason)

def r20_schedule_durable_capsule(reason='state_change', delay=None):
    global _R20_CAPSULE_TIMER, _R20_CAPSULE_FIRST_DIRTY_AT, _R20_CAPSULE_REASON
    try:
        wait = float(delay if delay is not None else _split_os.getenv('SPLIT_CAPSULE_DELAY_SEC','0.35') or '0.35')
    except Exception:
        wait = 0.35
    try:
        max_latency = float(_split_os.getenv('SPLIT_CAPSULE_MAX_LATENCY_SEC','1.0') or '1.0')
    except Exception:
        max_latency = 1.0
    now = _split_time.time()
    with _R20_CAPSULE_LOCK:
        if _R20_CAPSULE_FIRST_DIRTY_AT <= 0.0:
            _R20_CAPSULE_FIRST_DIRTY_AT = now
        _R20_CAPSULE_REASON = str(reason or 'state_change')[:160]
        due = min(now + max(0.05, wait), _R20_CAPSULE_FIRST_DIRTY_AT + max(0.2, max_latency))
        if _R20_CAPSULE_TIMER is not None:
            try: _R20_CAPSULE_TIMER.cancel()
            except Exception: pass
        _R20_CAPSULE_TIMER = _split_threading.Timer(max(0.03, due-now), _r20_capsule_timer_fire)
        _R20_CAPSULE_TIMER.daemon = True
        _R20_CAPSULE_TIMER.start()
    return True

# R20: redirect the original v262 config-guard remote sync to the HEAVY capsule.
# This preserves the semantic trigger/generation of v262 without allowing FAST to
# log into MEGA or perform a remote upload. HEAVY persists Redis + MEGA asynchronously.
_CONFIG_GUARD_SYNC_CORE = globals().get('config_guard_sync_remote_v234')
def _r20_config_guard_sync_remote(*, recovery_write=False):
    try:
        r20_schedule_durable_capsule('config_guard_remote_sync', delay=2.0)
        split_schedule_worker_sync_v262(reason='config_guard_remote_sync', delay=0.7)
        return True
    except Exception as exc:
        try: log_error(f'R20 config durable schedule: {exc}')
        except Exception: pass
        return False
config_guard_sync_remote_v234 = _r20_config_guard_sync_remote

# R15: full user-state shadow/continuity is a coalesced background checkpoint.
# The finance record itself has already been committed by persist_finance_chat_local_fast;
# serializing every chat after every message was pure foreground latency.
def _split_continuity_checkpoint_fire_v270():
    global _SPLIT_CONTINUITY_TIMER, _SPLIT_CONTINUITY_CHAT_ID, _SPLIT_CONTINUITY_REASON, _SPLIT_CONTINUITY_FIRST_DIRTY_AT
    with _SPLIT_CONTINUITY_LOCK:
        cid = _SPLIT_CONTINUITY_CHAT_ID
        reason = str(_SPLIT_CONTINUITY_REASON or 'coalesced')
        _SPLIT_CONTINUITY_TIMER = None
        _SPLIT_CONTINUITY_CHAT_ID = None
        _SPLIT_CONTINUITY_REASON = ''
        _SPLIT_CONTINUITY_FIRST_DIRTY_AT = 0.0
    # R28: continuity is background durability, never a competitor of a fresh button.
    try:
        quiet_fn = globals().get('r27_user_quiet_for')
        quiet_for = float(quiet_fn()) if callable(quiet_fn) else 10**9
        quiet_need = max(3.0, min(60.0, float(_split_os.getenv('R28_CONTINUITY_USER_QUIET_SEC','12') or '12')))
        if quiet_for < quiet_need:
            split_schedule_continuity_checkpoint_v270(cid, reason, delay=max(1.0, quiet_need - quiet_for))
            return
    except Exception:
        pass
    try:
        if cid is not None:
            _SAVE_DATA_CORE(data, chat_ids=[int(cid)])
        else:
            _SAVE_DATA_CORE(data, root_only=True)
        user_state_shadow_capture_v265('bg:' + reason)
        continuity_capture_v263('bg:' + reason)
        _split_mark_state_changed_v264('bg_continuity:' + reason)
        split_schedule_worker_sync_v262(reason='bg_continuity:' + reason, delay=1.2)
    except Exception as exc:
        try: log_error(f'R15 background continuity: {exc}')
        except Exception: pass

def split_schedule_continuity_checkpoint_v270(chat_id=None, reason='update', delay=4.0):
    global _SPLIT_CONTINUITY_TIMER, _SPLIT_CONTINUITY_CHAT_ID, _SPLIT_CONTINUITY_REASON, _SPLIT_CONTINUITY_FIRST_DIRTY_AT
    with _SPLIT_CONTINUITY_LOCK:
        if chat_id is not None:
            try: _SPLIT_CONTINUITY_CHAT_ID = int(chat_id)
            except Exception: pass
        _SPLIT_CONTINUITY_REASON = str(reason or 'update')[:160]
        now = _split_time.time()
        if _SPLIT_CONTINUITY_FIRST_DIRTY_AT <= 0.0:
            _SPLIT_CONTINUITY_FIRST_DIRTY_AT = now
        try:
            max_latency = max(1.0, min(15.0, float(_split_os.getenv('SPLIT_CONTINUITY_MAX_LATENCY_SEC','5.0') or '5.0')))
        except Exception:
            max_latency = 5.0
        due = min(now + max(0.5, float(delay or 4.0)), _SPLIT_CONTINUITY_FIRST_DIRTY_AT + max_latency)
        if _SPLIT_CONTINUITY_TIMER is not None:
            try: _SPLIT_CONTINUITY_TIMER.cancel()
            except Exception: pass
        _SPLIT_CONTINUITY_TIMER = _split_threading.Timer(max(0.05, due - now), _split_continuity_checkpoint_fire_v270)
        _SPLIT_CONTINUITY_TIMER.daemon = True
        _SPLIT_CONTINUITY_TIMER.start()
    return True

# Any logical save, not only finance, now requests remote durability.  The worker
# coalesces these calls, so Telegram handlers do not wait for MEGA.
_SAVE_DATA_CORE = save_data

def save_data(d, chat_ids=None, full=False, root_only=False):
    result = _SAVE_DATA_CORE(d, chat_ids=chat_ids, full=full, root_only=root_only)
    # Non-Telegram/background mutations need their own freshness marker.  Telegram
    # updates receive exactly one marker after the handler, avoiding extra hot-path IO.
    try:
        if not _split_inside_telegram_update_v264():
            _split_touch_state_revision_r18('logical_save_bg')
    except Exception:
        pass
    try:
        # Heavy all-chat shadow is background-only during normal READY operation.
        ready_fn = globals().get('runtime_is_ready')
        if full or not (callable(ready_fn) and ready_fn()):
            user_state_shadow_capture_v265('logical_save')
        else:
            _cid = None
            if chat_ids is not None:
                try:
                    _src = list(chat_ids) if isinstance(chat_ids,(list,tuple,set)) else [chat_ids]
                    _cid = int(_src[0]) if _src else None
                except Exception: _cid = None
            split_schedule_continuity_checkpoint_v270(_cid, 'logical_save', delay=4.0)
    except Exception:
        pass
    try:
        # R20: only meaningful configuration generations arm the independent capsule.
        # Normal finance/window saves therefore do not serialize the full user-state
        # shadow and cannot steal CPU from FAST navigation.
        _r20_cp = _r20_latest_config_checkpoint() if '_r20_latest_config_checkpoint' in globals() else {}
        _r20_gen = int((_r20_cp or {}).get('generation') or 0)
        if _r20_gen > int(globals().get('_R20_CAPSULE_LAST_GEN_SENT', 0) or 0):
            r20_schedule_durable_capsule('config_generation:' + str(_r20_gen), delay=2.0)
    except Exception:
        pass
    try:
        if not bool(globals().get('_V241_RESTORE_ACTIVE', False)):
            _split_mark_state_changed_v264('logical_save')
            # Boot migrations can call save_data many times. They are local-only until
            # READY, then R6 emits one final canonical snapshot instead of 4-10 GETs.
            ready_fn = globals().get('runtime_is_ready')
            is_ready = bool(ready_fn()) if callable(ready_fn) else False
            if is_ready or _split_inside_telegram_update_v264():
                split_schedule_worker_sync_v262(reason='logical_save', delay=0.6)
            else:
                _SPLIT_STATE['sync_pending'] = True
                _SPLIT_STATE['sync_reason'] = 'boot_coalesced'
    except Exception:
        pass
    try:
        if not bool(globals().get('_V241_RESTORE_ACTIVE', False)):
            r64_schedule_fast_redis_snapshot_v271('logical_save')
    except Exception:
        pass
    return result


# Persist RAM-only sessions after every successfully executed Telegram update.
# FINAL owner: this is the sole public execution function; core locking lives in 75.
def _execute_telegram_payload(payload: dict, update_id=None, update_chat_id=None, update_type: str='other'):
    _SPLIT_UPDATE_CONTEXT.active = True
    _SPLIT_UPDATE_CONTEXT.finance_dirty = False
    finance_dirty = False
    try:
        result = _execute_telegram_payload_core(payload, update_id, update_chat_id, update_type)
    finally:
        finance_dirty = bool(getattr(_SPLIT_UPDATE_CONTEXT, 'finance_dirty', False))
        _SPLIT_UPDATE_CONTEXT.active = False
        _SPLIT_UPDATE_CONTEXT.finance_dirty = False
    try:
        _split_touch_state_revision_r18(f'tg:{str(update_type or "other")}', update_id)
    except Exception:
        pass
    try:
        cid = update_chat_id
        if cid is None and isinstance(payload, dict):
            cid = _extract_update_chat_id(payload)
        prefix = 'finance' if finance_dirty else 'tg'
        _reason = f'{prefix}:{str(update_type or "other")}'
        # Fast hot path: the business handler already committed its own SQLite rows.
        # Persist RAM/UI continuity once after the burst, not inline for every update.
        split_schedule_continuity_checkpoint_v270(cid, _reason, delay=float(_split_os.getenv('SPLIT_CONTINUITY_FINANCE_DELAY_SEC','4.0') or '4.0') if finance_dirty else float(_split_os.getenv('SPLIT_CONTINUITY_OTHER_DELAY_SEC','2.5') or '2.5'))
        split_schedule_worker_sync_v262(reason=f'continuity:{_reason}', delay=float(_split_os.getenv('SPLIT_FINANCE_SYNC_DELAY_SEC','0.8') or '0.8') if finance_dirty else float(_split_os.getenv('SPLIT_STATE_SYNC_DELAY_SEC','1.2') or '1.2'))
    except Exception as exc:
        try: log_error(f'CONTINUITY post-update R11: {exc}')
        except Exception: pass
    return result


# R15 idle-only full rebase.  This replaces the old immediate full fallback that
# uploaded ~1.1 MB repeatedly during finance bursts.
def _split_idle_full_reconcile_fire_v270(reason='idle_reconcile'):
    global _SPLIT_FULL_TIMER
    with _SPLIT_FULL_LOCK:
        _SPLIT_FULL_TIMER = None
    try:
        _quiet_fn = globals().get('r27_user_quiet_for')
        quiet_for = float(_quiet_fn()) if callable(_quiet_fn) else max(0.0, _split_time.time() - float(globals().get('_SPLIT_LAST_CHANGE_AT') or 0.0))
    except Exception:
        quiet_for = 999999.0
    quiet_need = float(_split_os.getenv('R28_FULL_SNAPSHOT_USER_QUIET_SEC','30') or '30')
    if quiet_for < quiet_need:
        return _split_schedule_idle_full_reconcile_v270(reason, delay=max(3.0, quiet_need - quiet_for))
    min_gap = max(20.0, min(1800.0, float(_split_os.getenv('R28_FULL_SNAPSHOT_MIN_INTERVAL_SEC','300') or '300')))
    last_ok = float(_SPLIT_STATE.get('full_reconcile_last_ok') or 0.0)
    if last_ok > 0.0 and _split_time.time() - last_ok < min_gap:
        return _split_schedule_idle_full_reconcile_v270(reason, delay=max(3.0, min_gap - (_split_time.time() - last_ok)))
    ok = False
    try:
        try: _r27_flush_state_revision()
        except Exception: pass
        ok = bool(_split_push_snapshot_now_v263('idle:' + str(reason or '')[:100]))
    except Exception as exc:
        _SPLIT_STATE['full_reconcile_last_error'] = f'{type(exc).__name__}: {str(exc)[:180]}'
    if ok:
        _SPLIT_STATE['full_reconcile_pending'] = False
        _SPLIT_STATE['full_reconcile_last_ok'] = _split_time.time()
        _SPLIT_STATE['full_reconcile_last_error'] = ''
    else:
        _SPLIT_STATE['full_reconcile_pending'] = True
    return ok

def _split_schedule_idle_full_reconcile_v270(reason='need_full', delay=None):
    global _SPLIT_FULL_TIMER
    wait = float(delay if delay is not None else _split_os.getenv('R28_FULL_SNAPSHOT_USER_QUIET_SEC','30') or '20')
    with _SPLIT_FULL_LOCK:
        if _SPLIT_FULL_TIMER is not None:
            try: _SPLIT_FULL_TIMER.cancel()
            except Exception: pass
        _SPLIT_FULL_TIMER = _split_threading.Timer(max(5.0, wait), _split_idle_full_reconcile_fire_v270, args=(str(reason or 'need_full'),))
        _SPLIT_FULL_TIMER.daemon = True
        _SPLIT_FULL_TIMER.start()
    _SPLIT_STATE['full_reconcile_pending'] = True
    return True

# Snapshot download always captures the latest RAM continuity first.
_STATE_DOWNLOAD_CORE = split_front_state_download_v262

def split_front_state_download_v263():
    # R5: a worker fetch must be read-only. R4 rewrote continuity.saved_at on every
    # GET, making two identical snapshots look different and causing needless follow-ups.
    if not _split_authorized_request():
        return ({'ok': False}, 404)
    return _STATE_DOWNLOAD_CORE()

# Replace Flask endpoint function while keeping the already registered URL rule.
try:
    app.view_functions['split_front_state_download_v262'] = split_front_state_download_v263
except Exception:
    pass


# Final graceful shutdown: original code drains queues and saves full SQLite; then
# push that exact DB to worker cache immediately, before the process exits.
_RUNTIME_SHUTDOWN_CORE = runtime_graceful_shutdown

def runtime_graceful_shutdown(signal_name: str='SIGTERM'):
    # R18 deploy handoff order is deliberate: do NOT put slow MEGA/archive work in
    # front of the only state copy a replacement instance needs.  First serialize all
    # user/config/RAM interaction state, immediately seed Redis + HEAVY, and only then
    # run the legacy drain/archive shutdown.  A second post-drain push closes the tail.
    try:
        continuity_checkpoint_v263(None, reason=f'shutdown-pre:{signal_name}', full=True, schedule=False)
        _split_touch_state_revision_r18(f'shutdown-pre:{signal_name}')
        _r20_capsule_push_now(f'shutdown-pre:{signal_name}')
        _split_push_snapshot_now_v263(f'shutdown-pre-fast:{signal_name}')
    except Exception as exc:
        try: log_error(f'CONTINUITY shutdown-pre R18: {exc}')
        except Exception: pass
    result = None
    try:
        result = _RUNTIME_SHUTDOWN_CORE(signal_name)
    finally:
        try:
            continuity_checkpoint_v263(None, reason=f'shutdown-post:{signal_name}', full=True, schedule=False)
            _split_touch_state_revision_r18(f'shutdown-post:{signal_name}')
            # R51: the final deploy image is not complete until HEAVY confirms that
            # the exact post-drain SQLite snapshot is durable in canonical MEGA.
            if not _split_push_snapshot_now_v263(f'shutdown-post:{signal_name}', sync_mega=True):
                raise RuntimeError('final shutdown SQLite snapshot was not synchronously promoted to MEGA')
        except Exception as exc:
            try: log_error(f'CONTINUITY shutdown-post R18: {exc}')
            except Exception: pass
    return result


# R6 loader-order safety: 99_web_runtime loads data before this final module.
# The base load_data now restores the shadow early, and this second idempotent overlay
# protects already-loaded data if a future module order changes again.
try:
    data = user_state_shadow_apply_v265(data)
    try:
        _fac = (data or {}).get('finance_active_chats') or {}
        finance_active_chats.clear()
        for _cid, _enabled in _fac.items():
            if _enabled:
                try: finance_active_chats.add(int(_cid))
                except Exception: pass
    except Exception:
        pass
    try:
        _bf = (data or {}).get('backup_flags') or {}
        backup_flags['drive'] = bool(_bf.get('drive', backup_flags.get('drive', True)))
        backup_flags['channel'] = bool(_bf.get('channel', backup_flags.get('channel', True)))
    except Exception:
        pass
except Exception as _r6_live_apply_exc:
    try: log_error(f'R6 live user-state apply: {_r6_live_apply_exc}')
    except Exception: pass

# The DB was restored by start_front.py before bot.py was loaded, so RAM continuity
# can safely be rehydrated here, before main() marks the bot READY.
_CONTINUITY_BOOT_REPORT_V263 = continuity_restore_v263()


# R5 deploy-continuity rule: Telegram already keeps the old messages on its side.
# Re-sending/re-editing every restored chat on boot is both unnecessary and unsafe:
# stale historic chat ids can return 400 "chat not found".  Preserve the restored
# message ids/state and resume lazily when that chat next interacts with the bot.
def _split_schedule_startup_main_windows_v264(delay: float=3.0):
    try:
        log_info('CONTINUITY R5: startup UI replay skipped; restored Telegram messages are kept in place')
    except Exception:
        pass
    return True

schedule_startup_main_windows = _split_schedule_startup_main_windows_v264

# R6: all callback families emitted by the current bot must have a declared marker.
# Broad family declarations are intentional: dynamic task/space/reminder IDs vary,
# while the marker family is stable. This removes recurring NOT_DECLARED failures.
_R6_MARKER_FAMILIES = {
    'cat_page:*':'Ф3201', 'sp:*':'Ф3202', 'v149:*':'Ф3203', 'v152:*':'Ф3204',
    'v153:file:*':'Ф3205', 'v153:restore:*':'Ф3205', 'v156:*':'Ф3206', 'v157:*':'Ф3207',
    'v160:*':'Ф3208', 'v164:*':'Ф3209', 'v167:*':'Ф3210', 'v169:*':'Ф3211',
    'v171:*':'Ф3212', 'v172:*':'Ф3213', 'v174:*':'Ф3214', 'v176:*':'Ф3215',
    'v196:*':'Ф3216', 'v213:*':'Ф3217', 'v217:*':'Ф3218', 'v218:*':'Ф3219',
    'v219:*':'Ф3220', 'v221:*':'Ф3221', 'v223:*':'Ф3222', 'v229:*':'Ф3223',
    'v232:*':'Ф3224', 'v233:*':'Ф3225', 'v242:system_snapshot:*':'Ф3226', 'v261:*':'Ф3227',
    'expense_quick_buttons_toggle':'Ф3228', 'reminder_ui_mode_toggle':'Ф3229',
    'journal_toggle_open':'Ф3230', 'journal_name_edit:*':'Ф3231', 'journal_name_reset:*':'Ф3231',
    'keepalive_self_toggle':'Ф3232', 'keepalive_self_now':'Ф3232', 'keepalive_self_interval':'Ф3232',
    'keepalive_auto_toggle':'Ф3233', 'keepalive_auto_interval':'Ф3233',
    'keepalive_peer':'Ф3234', 'keepalive_peer_toggle':'Ф3234', 'keepalive_peer_now':'Ф3234',
    'keepalive_peer_clear':'Ф3234', 'keepalive_peer_interval':'Ф3234', 'keepalive_peer_url':'Ф3234',
    'keepalive_peer_url_cancel':'Ф3234',
    'keepalive_peer_set:*':'Ф3234', 'keepalive_self_set:*':'Ф3232', 'keepalive_auto_set:*':'Ф3233',
    # R6 second-pass audit: callbacks created through helper functions / variables.
    'v163_exp_end_today:*':'Ф116', 'v220:*':'Ф3235', 'exp_excel_dollar_toggle:*':'Ф179',
    'exp_send:*':'Ф3236',
    'fvcat_show:*':'Ф3237', 'fvcat_wthu:*':'Ф3237', 'fvcat_today:*':'Ф3237',
    'fvcat_desc:*':'Ф3237', 'fvcat_add:*':'Ф3237', 'fvcat_edit_menu:*':'Ф3237',
    'fvcat_edit_pick:*':'Ф3237', 'fvcat_del_menu:*':'Ф3237', 'fvcat_del_toggle:*':'Ф3237',
    'fvcat_del_selected:*':'Ф3237',
}
try:
    for _r6_key, _r6_marker in _R6_MARKER_FAMILIES.items():
        WINDOW_MARKER_CONSTANTS.setdefault(_r6_key, _r6_marker)
except Exception:
    pass

# Render liveness must stay HTTP 200 during boot; /readyz remains the strict readiness gate.
def _r6_root_liveness():
    ready = bool(globals().get('runtime_is_ready', lambda: False)())
    return ({'ok': True, 'role': 'front', 'ready': ready, 'phase': (globals().get('_RUNTIME_STATE') or {}).get('phase')}, 200)
try:
    app.view_functions['index'] = _r6_root_liveness
except Exception:
    pass

# Suppress boot-time snapshot storms and publish exactly one fully migrated state at READY.
_RUNTIME_MARK_READY_CORE = runtime_mark_ready
def runtime_mark_ready(detail: str=''):
    result = _RUNTIME_MARK_READY_CORE(detail)
    try:
        user_state_shadow_capture_v265('boot_ready')
        continuity_capture_v263('boot_ready')
        _split_touch_state_revision_r18('boot_ready')
        _split_mark_state_changed_v264('boot_ready')
        # Establish an exact binary base on HEAVY immediately after every boot.
        # The POST is tiny; HEAVY performs the job asynchronously and pulls the snapshot.
        _split_request_worker_full_sync_r18('boot_ready_exact_rebase')
        r20_schedule_durable_capsule('boot_ready', delay=1.0)
        split_schedule_worker_sync_v262(reason='boot_ready', delay=0.8)
    except Exception as exc:
        try: log_error(f'R6 boot-ready sync: {exc}')
        except Exception: pass
    return result

try:
    _r6_missing = [k for k in ('v229:tasks:single_window','v149:google:sheet','v149:google:test','v149:google:history') if not window_marker_is_declared(k)]
    if _r6_missing:
        log_error('R6 marker registry incomplete: ' + ','.join(_r6_missing))
except Exception:
    pass

# ---------------------------------------------------------------------------
# R7 system polish: fast finance post-commit, definitive chat removal,
# beginner-friendly Google setup, and heavy CSV/XLSX/Drive generation on worker.
R7_SYSTEM_POLISH = 'vys262-r7-system-polish'

# --- Finance: one derived-state pass and one visual repaint per logical change. ---
def _r7_rebuild_month_short_ids_after_normalize(chat_id: int, store: dict) -> None:
    daily = store.get('daily_records', {}) or {}
    month_counters = {}
    usd_month_counters = {}
    for dk in sorted(daily.keys()):
        month_key = str(dk)[:7]
        month_counters.setdefault(month_key, 1)
        usd_month_counters.setdefault(month_key, 1)
        recs = sorted(daily.get(dk, []) or [], key=record_sort_key)
        daily[dk] = recs
        for rec in recs:
            if not isinstance(rec, dict):
                continue
            try:
                if callable(globals().get('ensure_finance_record_uid')):
                    ensure_finance_record_uid(int(chat_id), rec)
            except Exception:
                pass
            has_usd = bool(float(rec.get('usd_amount', 0) or 0))
            usd_only = bool(rec.get('usd_only', False))
            if not usd_only:
                rec['short_id'] = f"R{month_counters[month_key]}"
                month_counters[month_key] += 1
            elif has_usd:
                rec['short_id'] = f"U{usd_month_counters[month_key]}"
            if has_usd:
                rec['usd_short_id'] = f"U{usd_month_counters[month_key]}"
                usd_month_counters[month_key] += 1
    store['records'] = [r for dk in sorted(daily.keys()) for r in daily.get(dk, []) if isinstance(r, dict)]


def _r7_finance_changed_now(chat_id: int, day_key: str | None=None, reason: str='change'):
    """R7: local finance commit stays synchronous; all derived work is one debounced pass."""
    chat_id = int(chat_id)
    day_key = str(day_key or get_chat_store(chat_id).get('current_view_day') or today_key())[:10]
    try:
        finance_cache_invalidate(chat_id, f'finance_changed:{reason}:r7')
    except Exception:
        pass
    with locked_chat(chat_id):
        store = get_chat_store(chat_id)
        store['current_view_day'] = day_key
        # One normalization only.  Older path normalized inside recalc and again in
        # rebuild_month_short_ids, which was noticeable on chats with long histories.
        normalize_chat_records(chat_id)
        store = get_chat_store(chat_id)
        store.pop('_finance_hotpath_pending_normalize_r15', None)
        store.pop('_finance_hotpath_pending_normalize_r16', None)
        store['balance'] = sum(float(r.get('amount', 0) or 0) for r in store.get('records', []) or [] if isinstance(r, dict))
        _r7_rebuild_month_short_ids_after_normalize(chat_id, store)
        try:
            _snapshot_active_currency_ledger(store, _ensure_currency_ledgers(store))
        except Exception:
            pass
        _r48_need_persist = True
    if callable(globals().get('persist_finance_chat_local_fast')):
        persist_finance_chat_local_fast(chat_id)
    # Nothing below blocks the Telegram handler or holds chat_lock.
    try:
        schedule_quick_backup(chat_id, MEGA_DELTA_PRIORITY_DELAY_SECONDS if mega_backup_priority_enabled() else MEGA_DELTA_DELAY_SECONDS)
    except Exception:
        pass
    try:
        schedule_financial_window_refresh(chat_id, day_key, reason=f'r7:{reason}', delay=0.015)
    except Exception:
        pass
    try:
        schedule_finance_postcommit_background_v243(chat_id, reason=f'r7:{reason}', delay=0.30)
    except Exception:
        pass

# finance_changed() resolves this name at execution time.
_finance_changed_now = _r7_finance_changed_now


def _r7_linked_edit_postcommit(origin_chat_id: int, origin_msg_id: int, touched_days: dict, repaint_copies: bool):
    """Linked edit already normalized, renumbered and committed each touched chat.

    Do not immediately run finance_changed() and repeat the same DB work.  Only repaint
    each affected UI once and schedule the common background aggregate/durability pass.
    """
    for cid, day_key in list((touched_days or {}).items()):
        try:
            schedule_financial_window_refresh(int(cid), str(day_key or ''), reason='linked_edit_r16_fast', delay=0.01)
        except Exception:
            pass
        # R16 hot edit intentionally skipped full normalize; schedule exactly one
        # delayed canonical reconcile after the immediate user-visible repaint.
        try:
            finance_changed(int(cid), str(day_key or ''), reason='linked_edit_r16_reconcile', delay=0.18)
        except Exception:
            pass
    if repaint_copies and origin_chat_id and origin_msg_id:
        try:
            _v262_background_repaint_copies(int(origin_chat_id), int(origin_msg_id))
        except Exception:
            pass

_v262_postcommit_linked_edit = _r7_linked_edit_postcommit


# R7 finance bulk-delete postcommit: callers already committed the normalized chat.
def _r7_v262_finance_postcommit_job(chat_id: int, day_key: str, reason: str):
    cid=int(chat_id); dk=str(day_key or '')
    try: finance_cache_invalidate(cid, f'r7:{reason}')
    except Exception: pass
    try: schedule_financial_window_refresh(cid, dk, reason=f'r16-fast:{reason}', delay=0.01)
    except Exception: pass
    try: finance_changed(cid, dk, reason=f'r16-reconcile:{reason}', delay=0.18)
    except Exception: pass

_v262_finance_postcommit_job = _r7_v262_finance_postcommit_job

# R9.2: chat-removal classification is implemented canonically in 00_core.py.
# Do not rebind probe_bot_in_chat here: bot.py runtime-contract requires its
# owner to remain 00_core.py.

# --- Google UX: three-step setup, service email, open current sheet, auto-test. ---
_R7_GOOGLE_INFO_CACHE = {'ts': 0.0, 'data': {}}

def _r7_google_worker_info(fetch: bool=True):
    now=_split_time.time()
    cached=dict(_R7_GOOGLE_INFO_CACHE.get('data') or {})
    if cached and (not fetch or now-float(_R7_GOOGLE_INFO_CACHE.get('ts') or 0) < 600):
        return cached
    if not fetch:
        return cached
    base = _split_peer_base()
    if not base or not _split_secret():
        return cached
    try:
        r = requests.get(base + '/internal/google/info', headers=_split_headers('vys-262-front-google-info'), timeout=8)
        payload = r.json() if r.content else {}
        if 200 <= r.status_code < 300 and payload.get('ok'):
            _R7_GOOGLE_INFO_CACHE.update(ts=now, data=dict(payload))
            return dict(payload)
    except Exception:
        pass
    return cached


def _r7_google_status_text(tenant_id):
    tid = str(tenant_id)
    row = tenant_get(tid) or {}
    cfg = tenant_google_config(tid)
    raw = str(cfg.get('spreadsheet_id') or '')
    if not raw and tid == str(globals().get('TENANT_PLATFORM_ID') or ''):
        raw = str(_split_os.getenv('GOOGLE_SHEETS_SPREADSHEET_ID', '') or '')
    # Opening /google must be instant: use cached/persisted email only. The worker is
    # contacted when the user presses step 1 or when access is tested.
    info = _r7_google_worker_info(fetch=False)
    email = str(cfg.get('service_account_email') or info.get('service_email') or '')
    title = str(cfg.get('spreadsheet_title') or '')
    ready = bool(raw and title)
    target = title or ((_v149_mask_id(raw) if raw else 'не выбрана'))
    return (
        f"📊 GOOGLE EXCEL · {row.get('name') or tid}\n\n"
        f"Статус: {'✅ готово к выгрузке' if ready else '🟡 нужно подключить таблицу'}\n"
        f"Таблица: {target}\n"
        f"Service account: {email or 'Render #2'}\n\n"
        "Как подключить первый раз:\n"
        "1️⃣ Нажмите «Email для доступа» и добавьте этот email в Google Таблице: Поделиться → Редактор.\n"
        "2️⃣ Нажмите «Подключить таблицу» и пришлите ссылку на неё.\n"
        "3️⃣ Бот сам проверит доступ. Если всё хорошо — больше ничего настраивать не нужно.\n\n"
        "После этого кнопки Google-выгрузки сами используют выбранную таблицу."
    )[:3900]


def _r7_google_keyboard(tenant_id):
    tid = str(tenant_id)
    cfg = tenant_google_config(tid)
    raw = str(cfg.get('spreadsheet_id') or '')
    if not raw and tid == str(globals().get('TENANT_PLATFORM_ID') or ''):
        raw = str(_split_os.getenv('GOOGLE_SHEETS_SPREADSHEET_ID', '') or '')
    kb = types.InlineKeyboardMarkup(row_width=1)
    kb.row(IB('1️⃣ Email для доступа', callback_data='v149:google:service_email'))
    kb.row(IB('2️⃣ Подключить / сменить таблицу', callback_data='v149:google:sheet'))
    kb.row(IB('3️⃣ Проверить доступ', callback_data='v149:google:test'))
    if raw:
        try:
            sid = _v149_google_id(raw, 'sheet')
            kb.row(types.InlineKeyboardButton('🔗 Открыть текущую таблицу', url=f'https://docs.google.com/spreadsheets/d/{sid}/edit'))
        except Exception:
            pass
    settings = cfg.get('export_settings') or {}
    kb.row(IB(f"{('✅' if settings.get('sheet_enabled', True) else '⬜')} Автовыгрузка Sheets: {('ВКЛ' if settings.get('sheet_enabled', True) else 'ВЫКЛ')}", callback_data='v149:google:toggle_sheet'))
    kb.row(IB(f"📜 История ({len(cfg.get('history') or [])})", callback_data='v149:google:history'), IB(f"⚠️ Ошибки ({len(cfg.get('errors') or [])})", callback_data='v149:google:errors'))
    return kb


def _r7_google_test(tenant_id):
    ok, text = _split_tenant_google_test(str(tenant_id))
    if ok:
        try:
            m = re.search(r'Название:\s*(.+)', str(text))
            cfg = tenant_google_config(str(tenant_id))
            if m:
                cfg['spreadsheet_title'] = str(m.group(1)).strip()[:200]
            info = _r7_google_worker_info()
            if info.get('service_email'):
                cfg['service_account_email'] = str(info.get('service_email'))[:250]
            cfg['updated_at'] = _v149_now_iso()
            tenant_google_history(str(tenant_id), 'sheet_access_verified_r7', cfg.get('spreadsheet_title') or 'access OK', ok=True)
            tenant_google_persist(str(tenant_id), 'tenant_google_update')
        except Exception:
            pass
    return ok, text

_GOOGLE_HANDLE_CORE = globals().get('tenant_google_handle_message')


def _r7_google_handle_message(msg) -> bool:
    # Handle the table-link step ourselves so save + access test is one action.
    try:
        cid = int(msg.chat.id)
        uid = int(getattr(getattr(msg, 'from_user', None), 'id', 0) or 0)
        tid = str(tenant_id_for_chat(cid, create=False) or '')
        cfg = tenant_google_config(tid, create=False) if tid else {}
        wait = dict((cfg or {}).get('input_wait') or {})
        if wait and str(wait.get('kind') or '') == 'sheet' and int(wait.get('chat_id') or 0) == cid and int(wait.get('user_id') or 0) == uid:
            if str(getattr(msg, 'content_type', '')) != 'text':
                send_and_auto_delete(cid, 'Пришлите ссылку на Google Таблицу обычным текстом.', 10)
                return True
            value = str(getattr(msg, 'text', '') or '').strip()
            cfg['spreadsheet_id'] = _v149_google_id(value, 'sheet')
            cfg['spreadsheet_title'] = ''
            cfg['input_wait'] = {}
            cfg['updated_at'] = _v149_now_iso()
            tenant_google_persist(tid, 'tenant_google_update')
            try:
                DELAYED_SCHEDULER.cancel(f'v213-input-google:{tid}:{cid}:{uid}')
                _v172_delete_quiet(cid, int(wait.get('cancel_message_id') or 0))
                bot.delete_message(cid, msg.message_id)
            except Exception:
                pass
            ok, test_text = _r7_google_test(tid)
            if ok:
                bot.send_message(cid, '✅ Таблица подключена и доступ проверен.\n\n' + _r7_google_status_text(tid), reply_markup=_r7_google_keyboard(tid))
            else:
                bot.send_message(cid, '🟡 Ссылка сохранена, но доступа пока нет.\n\n' + test_text + '\n\nНажмите «Email для доступа», добавьте его как Редактора и затем «Проверить доступ».', reply_markup=_r7_google_keyboard(tid))
            return True
    except Exception as exc:
        try: send_and_auto_delete(int(msg.chat.id), '❌ Google: ' + str(exc)[:600], 20)
        except Exception: pass
        return True
    return bool(_GOOGLE_HANDLE_CORE(msg)) if callable(_GOOGLE_HANDLE_CORE) else False


# R47 FINALIZATION: obsolete R7 callback wrapper removed; R29 Google router is canonical.

# Final Google bindings.
tenant_google_status_text = _r7_google_status_text
tenant_google_keyboard = _r7_google_keyboard
tenant_google_test = _r7_google_test
tenant_google_handle_message = _r7_google_handle_message
try:
    WINDOW_MARKER_CONSTANTS.setdefault('v149:google:service_email', 'Ф233')
except Exception:
    pass

# --- Heavy file export bridge: front prepares business rows, worker serializes/uploads. ---
_SEND_EXPORT_CORE = globals().get('send_export_for_chat_to')
_R7_EXPORT_SEEN = {}
_R7_EXPORT_SEEN_LOCK = _split_threading.RLock()


def _r7_json_rows(rows):
    out = []
    for row in rows or []:
        vals = []
        for value in list(row or []):
            if isinstance(value, (str, int, float, bool)) or value is None:
                vals.append(value)
            elif isinstance(value, dict):
                vals.append({str(k): v for k, v in value.items() if isinstance(v, (str, int, float, bool)) or v is None})
            else:
                vals.append(str(value))
        out.append(vals)
    return out


def _r7_export_annotations_payload(annotations):
    out = {}
    for key, val in (annotations or {}).items():
        try:
            r, c = key
            out[f'{int(r)},{int(c)}'] = str(val)
        except Exception:
            pass
    return out


def _r7_worker_file_submit(body: dict):
    base = _split_peer_base()
    if not base or not _split_secret():
        raise RuntimeError('Render #2 не настроен для файлового экспорта')
    r = requests.post(base + '/internal/export/file', json=body, headers=_split_headers('vys-262-front-export-r7'), timeout=25)
    payload = r.json() if r.content else {}
    if 200 <= r.status_code < 300 and payload.get('ok'):
        return str(payload.get('job_id') or body.get('job_id') or '')
    raise RuntimeError(str(payload.get('error') or r.text[:500] or f'HTTP {r.status_code}'))


def _r7_send_export_for_chat_to(recipient_chat_id: int, target_chat_id: int, mode: str, day_key: str, file_type: str='csv', excel_style_override=None, excel_options_override=None, delivery: str='chat'):
    recipient_chat_id = int(recipient_chat_id); target_chat_id = int(target_chat_id)
    file_type = str(file_type or 'csv').lower().lstrip('.')
    delivery = str(delivery or 'chat').strip().lower()
    custom_options = normalize_excel_export_options(excel_options_override) if isinstance(excel_options_override, dict) else None
    style = str(excel_style_override or (excel_export_options_style(custom_options) if custom_options else excel_table_style(target_chat_id)) or 'old').strip().lower()
    force_google = delivery == 'google' or style == 'google_notes'
    # Google Sheets already has a dedicated worker path with richer formatting.
    if force_google:
        return _SEND_EXPORT_CORE(recipient_chat_id, target_chat_id, mode, day_key, file_type, excel_style_override, excel_options_override, delivery) if callable(_SEND_EXPORT_CORE) else False
    try:
        raw_mode = str(mode or 'all')
        if raw_mode.startswith('xlsxstat_'):
            raw_mode = raw_mode[len('xlsxstat_'):]
        clean_mode = raw_mode.replace('csv_', '').replace('xlsx_', '')
        if clean_mode == 'all_real': clean_mode = 'all'
        rows, label = _period_export_rows(target_chat_id, clean_mode, day_key)
        ext = 'xlsx' if file_type in {'xlsx', 'xlsxstat'} else 'csv'
        if not rows and ext != 'xlsx':
            send_info(recipient_chat_id, f'Нет данных {label}.')
            return True
        annotations = {}
        category_layout = False
        sheet_name = 'Экспорт'
        description_column = True if not custom_options else bool(custom_options.get('description_column'))
        annotations_enabled = bool(not custom_options or custom_options.get('comments') or custom_options.get('notes'))
        if file_type == 'xlsxstat':
            store = get_chat_store(target_chat_id)
            start_key, end_key = _period_export_bounds(store, clean_mode, day_key)
            payload_rows = build_exact_category_stats_xlsx_rows(target_chat_id, start_key, 0, end_key, 0)
            category_layout = True
            sheet_name = 'Статьи'
            if custom_options and not description_column:
                payload_rows, annotations = _category_rows_without_description(payload_rows)
                category_layout = 'category_compact'
            if not annotations_enabled: annotations = {}
            safe_chat = mega_safe_name(get_chat_display_name(target_chat_id), 'chat')
            display_name = f'{safe_chat}_{clean_mode}_{day_key}_excel_статьи.xlsx'
        elif ext == 'xlsx':
            store = get_chat_store(target_chat_id)
            start_key, _end_key = _period_export_bounds(store, clean_mode, day_key)
            opening = _opening_balance_before_exact(store, start_key, 0)
            if description_column:
                payload_rows = [['Дата', 'Описание', 'Приход', 'Расход']]
                for date_v, amount_v, note_v in rows:
                    try: parsed = parse_csv_amount(amount_v)
                    except Exception: parsed = 0.0
                    payload_rows.append(_xlsx_record_row(date_v, parsed, note_v))
                payload_rows = insert_blank_rows_between_days(payload_rows, header_rows=1)
                payload_rows = _xlsx_simple_rows_with_balances(payload_rows, opening, target_chat_id)
            else:
                payload_rows, annotations = _compact_simple_excel_rows_and_annotations(rows, opening, target_chat_id)
                if not annotations_enabled: annotations = {}
            display_name = export_display_filename(target_chat_id, clean_mode, day_key, 'xlsx')
        else:
            payload_rows = [['date', 'amount', 'note']]
            prev_day = None
            for row in rows or []:
                vals = list(row or [])
                cur_day = str(vals[0] if vals else '')
                if prev_day is not None and cur_day != prev_day:
                    payload_rows.append(['', '', ''])
                payload_rows.append(vals[:3] + [''] * max(0, 3-len(vals)))
                prev_day = cur_day
            display_name = export_display_filename(target_chat_id, clean_mode, day_key, 'csv')
        tenant_id = str(tenant_id_for_chat(target_chat_id, create=False) or TENANT_PLATFORM_ID)
        cfg = tenant_google_config(tenant_id, create=False) or {}
        body = {
            'job_id': _split_secrets.token_hex(12), 'recipient_chat_id': recipient_chat_id,
            'target_chat_id': target_chat_id, 'tenant_id': tenant_id,
            'file_type': ext, 'source_file_type': file_type, 'style': style,
            'sheet_name': sheet_name, 'category_layout': category_layout,
            'rows': _r7_json_rows(payload_rows), 'annotations': _r7_export_annotations_payload(annotations),
            'filename': display_name, 'label': str(label), 'chat_name': get_chat_display_name(target_chat_id),
            'delivery': delivery,
            'drive_folder_id': str(cfg.get('drive_folder_id') or ''),
        }
        jid = _r7_worker_file_submit(body)
        what = 'Google Drive' if delivery == 'drive' else ('Excel' if ext == 'xlsx' else 'CSV')
        bot.send_message(recipient_chat_id, f'⚡ {what} готовится на Render #2. Можно продолжать пользоваться ботом — результат придёт отдельным сообщением.')
        try: file_job_mark_external_delivery('Render #2 export', jid)
        except Exception: pass
        return True
    except Exception as exc:
        try: log_error(f'R7 worker export {get_chat_display_name(target_chat_id)}: {exc}')
        except Exception: pass
        # Safety fallback preserves monolith behaviour if worker is temporarily unavailable.
        if callable(_SEND_EXPORT_CORE):
            return _SEND_EXPORT_CORE(recipient_chat_id, target_chat_id, mode, day_key, file_type, excel_style_override, excel_options_override, delivery)
        return False


def _r7_export_result_seen(job_id: str) -> bool:
    now = _split_time.time()
    with _R7_EXPORT_SEEN_LOCK:
        for key, ts in list(_R7_EXPORT_SEEN.items()):
            if now - float(ts or 0) > 86400:
                _R7_EXPORT_SEEN.pop(key, None)
        if job_id in _R7_EXPORT_SEEN:
            return True
        _R7_EXPORT_SEEN[job_id] = now
        return False


_R34_EXPORT_DELIVERY_LOCK = _split_threading.RLock()
_R34_EXPORT_DELIVERY = {}

def _r7_deliver_worker_export(body: dict):
    jid = str(body.get('job_id') or ''); cid = int(body.get('recipient_chat_id') or 0)
    if not jid or not cid: return False
    try:
        if not body.get('ok'):
            bot.send_message(cid, '❌ Экспорт Render #2: ' + str(body.get('error') or 'неизвестная ошибка')[:800]); return True
        if str(body.get('delivery') or '') == 'drive':
            bot.send_message(cid, f"☁️ Google Drive · {body.get('label') or ''}: {body.get('chat_name') or ''}\n\n{body.get('url') or ''}", disable_web_page_preview=True); return True
        if str(body.get('delivery') or '') == 'google':
            if body.get('url'): bot.send_message(cid, f"✅ Google Excel готов.\n{body.get('url')}", disable_web_page_preview=True)
            return True
        base = _split_peer_base()
        r = requests.get(base + '/internal/export/file/' + jid, headers=_split_headers('vys-262-front-export-fetch-r34'), timeout=90, stream=True)
        if r.status_code != 200: raise RuntimeError(f'worker file HTTP {r.status_code}: {r.text[:240]}')
        import tempfile as _r34_tempfile, os as _r34_os
        suffix=_r34_os.path.splitext(str(body.get('filename') or 'export.bin'))[1]
        tmp=_r34_tempfile.NamedTemporaryFile(prefix='r34_export_',suffix=suffix,delete=False)
        try:
            for chunk in r.iter_content(chunk_size=256*1024):
                if chunk: tmp.write(chunk)
            tmp.close()
            with open(tmp.name,'rb') as fobj:
                caption = str(body.get('caption') or '') or f"📂 {body.get('label') or 'Файл'}: {body.get('chat_name') or ''}"
                _tg_call_retry(bot.send_document, cid, fobj, caption=caption, timeout=120, purpose='r34_worker_export_send_document')
        finally:
            try: _r34_os.unlink(tmp.name)
            except Exception: pass
        return True
    except Exception as exc:
        try: log_error(f'R34 export delivery {jid}: {type(exc).__name__}: {str(exc)[:500]}')
        except Exception: pass
        return False

def _r34_export_delivery_task(body):
    jid=str(body.get('job_id') or '')
    ok=_r7_deliver_worker_export(body)
    with _R34_EXPORT_DELIVERY_LOCK:
        _R34_EXPORT_DELIVERY[jid]={'state':'done' if ok else 'failed','ts':_split_time.time(),'body':dict(body)}

@app.route('/internal/split/export-result', methods=['POST'])
def split_front_export_result_r7():
    if not _split_authorized_request(): return ({'ok': False}, 404)
    body=request.get_json(silent=True) or {}; jid=str(body.get('job_id') or '')
    if not jid: return ({'ok':False,'error':'job_id required'},400)
    now=_split_time.time()
    with _R34_EXPORT_DELIVERY_LOCK:
        for k,row in list(_R34_EXPORT_DELIVERY.items()):
            if now-float((row or {}).get('ts') or now)>86400: _R34_EXPORT_DELIVERY.pop(k,None)
        state=str((_R34_EXPORT_DELIVERY.get(jid) or {}).get('state') or '')
        if state=='done': return ({'ok':True,'delivered':True,'duplicate':True},200)
        if state=='running': return ({'ok':True,'accepted':True,'delivered':False},202)
        _R34_EXPORT_DELIVERY[jid]={'state':'running','ts':now,'body':dict(body)}
    try:
        key='r34-export-delivery:'+jid
        pool=globals().get('GENERAL_TASK_POOL') or globals().get('BACKGROUND_TASK_POOL'); submitted=False
        if pool is not None and hasattr(pool,'submit'):
            submitted=bool(pool.submit(key,_r34_export_delivery_task,dict(body)))
        if not submitted:
            sched=globals().get('DELAYED_SCHEDULER')
            if sched is None:
                raise RuntimeError('bounded export delivery queue unavailable')
            sched.schedule(key,0.25,_r34_export_delivery_task,dict(body))
    except Exception as exc:
        with _R34_EXPORT_DELIVERY_LOCK:
            _R34_EXPORT_DELIVERY[jid]={'state':'failed','ts':_split_time.time(),'error':str(exc)[:200],'body':dict(body)}
        return ({'ok':False,'error':'delivery queue busy'},503)
    return ({'ok':True,'accepted':True,'delivered':False},202)

send_export_for_chat_to = _r7_send_export_for_chat_to

# R7 marker coverage for the task callback that was seen in production plus Google UX.
try:
    WINDOW_MARKER_CONSTANTS.setdefault('v229:tasks:single_window', 'Ф54')
    WINDOW_MARKER_CONSTANTS.setdefault('v149:google:service_email', 'Ф233')
except Exception:
    pass

try:
    bot_journal('r7_system_polish_loaded', int(OWNER_ID or 0), 'finance=single-derived-pass; chat_probe=removed-classifier; google=3-step; export=worker')
except Exception:
    pass

# --- R7 exact-range export and strict Front Google isolation. ---
_EXACT_EXPORT_CORE = globals().get('send_exact_range_export')


def _r7_send_exact_range_export(recipient_chat_id: int, target_chat_id: int, start_key: str, start_rid: int, end_key: str, end_rid: int, file_type: str, excel_style_override=None, excel_options_override=None, delivery: str='chat'):
    recipient_chat_id=int(recipient_chat_id); target_chat_id=int(target_chat_id)
    file_type=str(file_type or 'csv').lower()
    if file_type not in {'csv','xlsx','xlsxstat'}: file_type='csv'
    custom_options=normalize_excel_export_options(excel_options_override) if isinstance(excel_options_override,dict) else None
    style=str(excel_style_override or (excel_export_options_style(custom_options) if custom_options else excel_table_style(target_chat_id)) or 'old').strip().lower()
    delivery=str(delivery or 'chat').strip().lower()
    force_google=delivery=='google' or style=='google_notes'
    description_column=True if not custom_options else bool(custom_options.get('description_column'))
    annotations_enabled=bool(not custom_options or custom_options.get('comments') or custom_options.get('notes'))
    try:
        rows=_exact_export_rows(target_chat_id,start_key,int(start_rid),end_key,int(end_rid))
        if not rows:
            send_and_auto_delete(recipient_chat_id,'Нет записей в выбранном точном диапазоне.',10)
            return True
        if force_google:
            xrows=build_exact_category_stats_xlsx_rows(target_chat_id,start_key,int(start_rid),end_key,int(end_rid))
            annotations={}; layout='category'
            if custom_options and not description_column:
                xrows,annotations=_category_rows_without_description(xrows); layout='category_compact'
            title=f'{get_chat_display_name(target_chat_id)} — статьи — точный период'
            token=_v262_split_google_sheets_create_category_report(title,xrows,layout=layout,annotations_override=annotations if annotations_enabled else {},include_annotations=annotations_enabled,target_chat_id=target_chat_id,recipient_chat_id=recipient_chat_id,notify_result=True)
            jid=str(token).split(':',1)[1] if str(token).startswith('worker-job:') else ''
            if jid:
                bot.send_message(recipient_chat_id,'⚡ Google Excel точного периода готовится на Render #2. Ссылка придёт отдельным сообщением.')
            return True
        ext='xlsx' if file_type in {'xlsx','xlsxstat'} else 'csv'
        annotations={}; layout=False; sheet_name='Точный период'
        if file_type=='xlsxstat':
            payload_rows=build_exact_category_stats_xlsx_rows(target_chat_id,start_key,int(start_rid),end_key,int(end_rid))
            layout=True; sheet_name='Excel стат'
            if custom_options and not description_column:
                payload_rows,annotations=_category_rows_without_description(payload_rows); layout='category_compact'
            if not annotations_enabled: annotations={}
        elif ext=='xlsx':
            opening=_opening_balance_before_exact(get_chat_store(target_chat_id),start_key,int(start_rid))
            if description_column:
                payload_rows=[['Дата','Описание','Приход','Расход']]
                for date_v,amount_v,note_v in rows:
                    try: parsed=parse_csv_amount(amount_v)
                    except Exception: parsed=0.0
                    payload_rows.append(_xlsx_record_row(date_v,parsed,note_v))
                payload_rows=insert_blank_rows_between_days(payload_rows,header_rows=1)
                payload_rows=_xlsx_simple_rows_with_balances(payload_rows,opening,target_chat_id)
            else:
                payload_rows,annotations=_compact_simple_excel_rows_and_annotations(rows,opening,target_chat_id)
                if not annotations_enabled: annotations={}
        else:
            payload_rows=[['date','amount','note']]; prev=None
            for row in rows or []:
                vals=list(row or []); cur=str(vals[0] if vals else '')
                if prev is not None and cur!=prev: payload_rows.append(['','',''])
                payload_rows.append(vals[:3]+['']*max(0,3-len(vals))); prev=cur
        chat_name=_safe_export_name_part(get_chat_name_for_filename(target_chat_id) or get_chat_display_name(target_chat_id),f'chat_{target_chat_id}')
        start_label=fmt_date_backup(start_key).replace(':','.')
        end_label=fmt_date_backup(end_key).replace(':','.')
        display_name=f"{chat_name}_({start_label}-{end_label})_{('excel_стат' if file_type=='xlsxstat' else 'точный')}.{ext}"
        store=get_chat_store(target_chat_id)
        caption=f"🎯 {(('Excel стат ' if file_type=='xlsxstat' else 'Excel ') + _export_style_caption(style) if ext=='xlsx' else 'CSV')} — точный период\n▶️ {exact_boundary_text(store,start_key,start_rid,True)}\n⏹ {exact_boundary_text(store,end_key,end_rid,False)}"
        tid=str(tenant_id_for_chat(target_chat_id,create=False) or TENANT_PLATFORM_ID); cfg=tenant_google_config(tid,create=False) or {}
        body={'job_id':_split_secrets.token_hex(12),'recipient_chat_id':recipient_chat_id,'target_chat_id':target_chat_id,'tenant_id':tid,
              'file_type':ext,'source_file_type':file_type,'style':style,'sheet_name':sheet_name,'category_layout':layout,
              'rows':_r7_json_rows(payload_rows),'annotations':_r7_export_annotations_payload(annotations),'filename':display_name,
              'label':'точный период','chat_name':get_chat_display_name(target_chat_id),'caption':caption,'delivery':delivery,
              'drive_folder_id':str(cfg.get('drive_folder_id') or '')}
        _r7_worker_file_submit(body)
        bot.send_message(recipient_chat_id,f"⚡ {('Google Drive' if delivery=='drive' else 'Excel' if ext=='xlsx' else 'CSV')} точного периода готовится на Render #2. Можно продолжать пользоваться ботом.")
        return True
    except Exception as exc:
        try: log_error(f'R7 exact worker export {target_chat_id}: {exc}')
        except Exception: pass
        # If worker is down, keep the old local export only as an emergency compatibility fallback.
        if callable(_EXACT_EXPORT_CORE):
            return _EXACT_EXPORT_CORE(recipient_chat_id,target_chat_id,start_key,start_rid,end_key,end_rid,file_type,excel_style_override,excel_options_override,delivery)
        return False


send_exact_range_export = _r7_send_exact_range_export

# Active front hooks must never perform Google OAuth/Drive/Sheets network work.
def _r7_front_google_forbidden(*args, **kwargs):
    raise RuntimeError('Google network work is isolated on Render #2. Use /google or the worker export path.')

def _r7_front_create_sheet_disabled(tenant_id: str, title: str='Финансы бота'):
    raise RuntimeError('Создайте Google Таблицу в своём аккаунте, расшарьте её service-account как Редактору и подключите через /google. Создание таблиц сервисным аккаунтом отключено, чтобы владельцем файла оставались вы.')

_google_access_token = _r7_front_google_forbidden
tenant_google_upload_export = _r7_front_google_forbidden
tenant_google_create_spreadsheet = _r7_front_create_sheet_disabled

# v262

# --- R9 release note: Google visual formatting restored to original vys-262 on Worker. ---
R9_GOOGLE_STYLE = 'vys262-r9-google-style'
try:
    bot_journal('r9_release_loaded', int(OWNER_ID or 0), 'google=original-v262-colors; startup-summary=concise; r8-chat-removal=kept')
except Exception:
    pass


# --- R10 unified user UI, Worker status and menu entry points. ---
def _r10_age_text(ts):
    try:
        sec=max(0,int(_split_time.time()-float(ts or 0)))
    except Exception:
        return '—'
    if not ts: return '—'
    if sec < 5: return 'только что'
    if sec < 60: return f'{sec} сек назад'
    if sec < 3600: return f'{sec//60} мин назад'
    return f'{sec//3600} ч назад'


def _r10_worker_health_text(force=False):
    # R24: this formatter is cache-only. Network health refresh is always a second
    # stage so opening the status window can never wait up to 12 seconds.
    h=dict(_SPLIT_STATE.get('worker_health') or {})
    st=dict(h.get('state') or {})
    interval=max(30,min(1800,int(_split_os.getenv('PEER_PING_INTERVAL_SEC','120') or '120')))
    front_ok=bool(_SPLIT_STATE.get('peer_last_ok')) and (_split_time.time()-float(_SPLIT_STATE.get('peer_last_ok') or 0) <= interval*2.5)
    reverse_ok=bool(st.get('peer_last_ok')) and (_split_time.time()-float(st.get('peer_last_ok') or 0) <= interval*2.5)
    worker_ok=bool(h.get('ok')) and int(_SPLIT_STATE.get('peer_status') or 0) in range(200,300)
    google_ok=bool(h.get('google_configured'))
    redis_ok=bool(st.get('redis_cache_ok'))
    mega_ok=bool(h.get('mega_configured'))
    q=int(h.get('queue_size') or 0); gq=int(h.get('google_queue_size') or 0)
    linked='✅ связаны в обе стороны' if (front_ok and reverse_ok) else ('🟠 связь только в одну сторону' if (front_ok or reverse_ok) else '⛔ связи нет')
    err=str(_SPLIT_STATE.get('peer_last_error') or st.get('peer_last_error') or '').strip()
    lines=[
        '🛰 RENDER #2 · ТЯЖЁЛЫЙ КОНТУР', '',
        f"Worker: {('✅ жив' if worker_ok else '⛔ недоступен')} · {str(h.get('version') or '—')}",
        f'Пеленг: {linked}',
        f"Front → Worker: {('✅' if front_ok else '⛔')} · {_r10_age_text(_SPLIT_STATE.get('peer_last_ok'))}",
        f"Worker → Front: {('✅' if reverse_ok else '⛔')} · {_r10_age_text(st.get('peer_last_ok'))}",
        '',
        f'Очередь: обычная {q} · Google {gq}',
        f"Google: {('✅ настроен' if google_ok else '⛔ не настроен')} · последний успех {_r10_age_text(st.get('google_last_ok'))}",
        f"Redis: {('✅' if redis_ok else '🟠')} · delta {int(st.get('delta_since_checkpoint') or 0)} · rev {str(st.get('cache_revision') or '—')}",
        f"Delta sync: {int(st.get('delta_last_pages') or 0)} стр. · {int(st.get('delta_bytes') or 0)//1024} КБ всего",
        f"События: получено {int(st.get('event_received') or 0)} · commit {int(st.get('event_committed') or 0)} · зеркало {int(st.get('event_mirrored') or 0)} · ждут {int(st.get('event_pending') or 0)}",
        f"Hash-сверка: {_r10_age_text(st.get('reconcile_last_ok'))} · full-resync {int(st.get('reconcile_full_resyncs') or 0)}",
        f"MEGA checkpoint: {('✅ настроена' if mega_ok else '⛔ не настроена')} · {_r10_age_text(st.get('last_mega_upload_at'))}",
        f"Последняя синхронизация: {_r10_age_text(st.get('delta_last_at') or st.get('job_last_done') or st.get('last_snapshot_at'))}",
    ]
    if err and not worker_ok:
        lines += ['', 'Ошибка: '+err[:240]]
    return window_mark('\n'.join(lines), 'Ф270')


def _r10_worker_health_keyboard():
    kb=types.InlineKeyboardMarkup(row_width=2)
    kb.row(IB('🔄 Проверить сейчас', callback_data='r10:worker:refresh'))
    kb.row(IB('📊 Google Excel', callback_data='v149:google:status'))
    kb.row(IB('🔙 В Инфо', callback_data='r10:worker:back'), IB('❌ Закрыть', callback_data='info_close'))
    return kb


_INFO_KB_CORE = globals().get('build_info_keyboard')
def _r10_build_info_keyboard(chat_id: int):
    kb=_INFO_KB_CORE(int(chat_id)) if callable(_INFO_KB_CORE) else types.InlineKeyboardMarkup()
    if int(chat_id) != int(OWNER_ID or 0): return kb
    rows=_v177_info_rows(kb)
    callbacks={_v177_info_btn_cb(b) for row in rows for b in row or []}
    additions=[]
    if 'r10:worker:status' not in callbacks:
        additions.append([IB('🛰 Render #2 · состояние', callback_data='r10:worker:status')])
    if 'v149:google:status' not in callbacks:
        additions.append([IB('📊 Google Excel', callback_data='v149:google:status')])
    if additions:
        insert_at=len(rows)
        for i,row in enumerate(rows):
            if any((_v218_info_is_nav(b) for b in row or [])): insert_at=i; break
        rows[insert_at:insert_at]=additions
        kb=_v177_info_set_rows(kb,rows)
    return kb

build_info_keyboard = _r10_build_info_keyboard

_MAIN_KB_CORE = globals().get('build_main_keyboard')
def _r10_build_main_keyboard(day_key: str, chat_id=None):
    kb=_MAIN_KB_CORE(day_key,chat_id) if callable(_MAIN_KB_CORE) else types.InlineKeyboardMarkup()
    try: cid=int(chat_id if chat_id is not None else current_state_chat_id() or 0)
    except Exception: cid=0
    if cid != int(OWNER_ID or 0): return kb
    rows=_v217_rows(kb)
    callbacks={_v217_btn_cb(b) for row in rows for b in row or []}
    if 'v149:google:status' not in callbacks:
        rows.append([IB('📊 Google Excel', callback_data='v149:google:status'), IB('🛰 Render #2', callback_data='r10:worker:status')])
        kb=_v217_set_rows(kb,rows)
    return kb

build_main_keyboard = _r10_build_main_keyboard

_CONTOUR_GUARD_CORE = globals().get('contour_callback_guard')
def _r10_contour_callback_guard(call, resolved: str) -> bool:
    raw=str(resolved or '')
    if raw.startswith('r10:worker:'):
        try:
            cid=int(call.message.chat.id); uid=int(getattr(getattr(call,'from_user',None),'id',0) or 0)
        except Exception:
            return True
        if cid != int(OWNER_ID or 0) or uid != int(OWNER_ID or 0):
            try: bot.answer_callback_query(call.id,'Только основной владелец.',show_alert=True)
            except Exception: pass
            return True
        try: bot.answer_callback_query(call.id)
        except Exception: pass
        if raw == 'r10:worker:back':
            safe_edit(bot,call,build_info_text(cid),reply_markup=build_info_keyboard(cid)); return True
        # First render is always local/cache-only. Then Render #2 health is refreshed
        # in background and the same window is updated when the result arrives.
        safe_edit(bot,call,_r10_worker_health_text(force=False),reply_markup=_r10_worker_health_keyboard())
        try:
            _mid = int(call.message.message_id)
            _need_refresh = (raw == 'r10:worker:refresh') or (_split_time.time()-float(_SPLIT_STATE.get('peer_last_attempt') or 0) > 25)
            if _need_refresh:
                def _r24_refresh_worker_card(_cid=cid, _mid=_mid):
                    try: _split_ping_once()
                    except Exception: pass
                    try:
                        fast_ui_edit_message_text(_cid, _mid, _r10_worker_health_text(False), reply_markup=_r10_worker_health_keyboard(), purpose='r24_worker_health_refresh')
                    except Exception: pass
                _pool = globals().get('GENERAL_TASK_POOL')
                if _pool is not None:
                    _pool.submit_unique(f'r24-worker-health:{cid}', _r24_refresh_worker_card)
        except Exception:
            pass
        return True
    return bool(_CONTOUR_GUARD_CORE(call,raw)) if callable(_CONTOUR_GUARD_CORE) else False

contour_callback_guard = _r10_contour_callback_guard
try:
    WINDOW_MARKER_CONSTANTS.setdefault('r10:worker:*','Ф270')
    WINDOW_MARKER_CONSTANTS.setdefault('r10:worker:status','Ф270')
    WINDOW_MARKER_CONSTANTS.setdefault('r10:worker:refresh','Ф270')
    WINDOW_MARKER_CONSTANTS.setdefault('r10:worker:back','Ф89')
    bot_journal('r10_unified_ui_loaded',int(OWNER_ID or 0),'service-ui=simple; worker-card=1; google-menu=1; peer=bidirectional')
    bot_journal('r11_fast_finance_loaded',int(OWNER_ID or 0),'finance-derived=async; chat-journal-default=on; legacy-front-delta=off')
except Exception:
    pass

# R12: establish the local delta base after all migrations/continuity wrappers are loaded.
# If the first Worker delta later reports a mismatch, the bridge automatically performs
# one full resync and re-bases; normal updates never GET the full SQLite again.
try:
    _split_init_delta_baseline_v267(force=True)
    bot_journal('r12_delta_sync_loaded', int(OWNER_ID or 0), 'sqlite-page-delta=on; full=checkpoint-or-mismatch')
    bot_journal('r13_event_journal_loaded', int(OWNER_ID or 0), 'raw-event-witness=worker/redis; commit-ack=on; reconcile-hash=rare')
except Exception as _r12_delta_boot_exc:
    try: log_error(f'R13 delta/event baseline init: {_r12_delta_boot_exc}')
    except Exception: pass

try:
    bot_journal('r14_internal_config_loaded', int(OWNER_ID or 0), 'Render ENV=credentials/addresses only; tunables=runtime_config.py')
except Exception:
    pass

R15_FAST_HOTPATH = 'vys262-r15-fast-hotpath'
try: bot_journal('r15_fast_hotpath_loaded', int(OWNER_ID or 0), 'remote witness fast; continuity background; full fallback idle-only')
except Exception: pass


# R21: every button has an immediate FAST stage. Heavy execution is a second stage.
# This override intentionally runs after 89_callback_final.py so it replaces the canonical
# monolith submitter without changing the v262 business handlers themselves.
R25_TRACE_FAST_PRIORITY_STAGE = 'per-r25-trace-fast-priority'
R24_ORDERED_HOT_RAM_STAGE = R25_TRACE_FAST_PRIORITY_STAGE
R22_ZERO_BLOCKING_BUTTON_STAGE = R24_ORDERED_HOT_RAM_STAGE
R21_EVERY_BUTTON_FAST_STAGE = R22_ZERO_BLOCKING_BUTTON_STAGE  # compatibility alias
try:
    R21_HEAVY_DISPATCH_TASK_POOL = KeyedTaskPool(
        'heavy-dispatch',
        _env_int('R21_HEAVY_DISPATCH_WORKERS', 4, 2, 8),
        _env_int('R21_HEAVY_DISPATCH_MAX_PENDING', 500, 50, 2000),
    )
except Exception:
    R21_HEAVY_DISPATCH_TASK_POOL = globals().get('GENERAL_TASK_POOL') or globals().get('EXPORT_TASK_POOL')

_R21_REMOTE_FILE_KINDS = {'period_export', 'exact_export', 'xlsx', 'csv'}
_R21_REMOTE_FILE_FUNCS = {'_r7_send_export_for_chat_to', '_r7_send_exact_range_export'}

def _r21_file_job_remote_capable(kind, func) -> bool:
    name = str(getattr(func, '__name__', '') or '')
    return str(kind or '') in _R21_REMOTE_FILE_KINDS or name in _R21_REMOTE_FILE_FUNCS

def _r21_file_job_key(chat_id: int, kind: str) -> str:
    # Coalesce only duplicate taps for the same chat+operation. R20's single global
    # file key made an unrelated download in another chat look busy.
    return f'r21:file:{int(chat_id)}:{str(kind or "file")[:80]}'

def _r21_file_job_lock_denied(meta: dict, text: str='Такая задача уже выполняется.'):
    key = str((meta or {}).get('key') or '')
    cid = int((meta or {}).get('chat_id') or 0)
    mid = int((meta or {}).get('status_msg_id') or 0)
    try:
        if mid:
            bot.edit_message_text(window_mark('⏳ '+str(text), 'Ф233'), chat_id=cid, message_id=mid)
    except Exception:
        pass
    try:
        with _FILE_JOB_LOCK:
            _FILE_JOB_STATE.pop(key, None)
    except Exception:
        pass

def _r21_interactive_file_dispatch_runner(job_meta: dict, func, args, kwargs):
    """Acquire distributed single-flight only after the callback has returned.

    No Redis/Key Value RTT is ever in front of a Telegram button in R21.  For split-capable
    exports this runner only prepares/dispatches the Render #2 job; the expensive file
    generation happens on HEAVY.  Runtime-only diagnostics that require live FAST process
    data stay on the low-priority export pool, never on the callback lane.
    """
    meta = dict(job_meta or {})
    cid = int(meta.get('chat_id') or 0)
    kind = str(meta.get('kind') or 'file')
    kv_name = f'interactive_file_job:r21:{cid}:{kind}'
    token = None
    backend = 'local'
    fn = globals().get('kv_distributed_lock_try_v248')
    if callable(fn):
        try:
            allowed, token, backend = fn(kv_name, 900)
        except Exception:
            allowed, token, backend = (True, None, 'local_fallback')
        if not allowed:
            _r21_file_job_lock_denied(meta)
            return False
    meta['kv_lock_token_v248'] = token
    meta['kv_lock_backend_v248'] = backend
    meta['kv_lock_name_v259'] = kv_name
    return _interactive_file_job_runner(meta, func, args, kwargs)

def _r21_submit_interactive_file_job(chat_id: int, kind: str, label: str, func, *args, **kwargs) -> tuple[bool, str]:
    """R21 FAST half of every file/export button.

    Synchronous path: RAM duplicate check -> Telegram status window -> local queue submit.
    It performs no Redis lock, save_data(), backup, MEGA, Google or file construction.
    """
    cid = int(chat_id)
    kind_s = str(kind or 'file')
    label_s = str(label or 'Задача')
    key = _r21_file_job_key(cid, kind_s)
    now_m = time.monotonic()
    with _FILE_JOB_LOCK:
        existing = _FILE_JOB_STATE.get(key)
        if isinstance(existing, dict):
            return (False, 'Такая задача уже выполняется')
        meta = {
            'key': key, 'chat_id': cid, 'kind': kind_s, 'label': label_s,
            'queued_monotonic': now_m, 'started_monotonic': 0.0,
            'phase': 'передаю Render #2' if _r21_file_job_remote_capable(kind_s, func) else 'в фоне',
            'status_msg_id': None, 'last_ui_monotonic': 0.0,
        }
        _FILE_JOB_STATE[key] = meta

    # One visible UI operation is allowed in the FAST half. Do not persist this transient
    # message id: after deploy it is intentionally disposable.
    try:
        phase = str(meta.get('phase') or 'в фоне')
        text = _v159_file_status_text(label_s, '0:00', phase) if callable(globals().get('_v159_file_status_text')) else f'⏳ {label_s}\nЭтап: {phase}'
        msg = bot.send_message(cid, text)
        mid = int(getattr(msg, 'message_id', 0) or 0)
        if mid:
            with _FILE_JOB_LOCK:
                if isinstance(_FILE_JOB_STATE.get(key), dict):
                    _FILE_JOB_STATE[key]['status_msg_id'] = mid
            meta['status_msg_id'] = mid
    except Exception:
        pass

    pool = R21_HEAVY_DISPATCH_TASK_POOL if _r21_file_job_remote_capable(kind_s, func) else EXPORT_TASK_POOL
    try:
        ok = bool(pool.submit_unique(key, _r21_interactive_file_dispatch_runner, dict(meta), func, args, kwargs))
    except Exception:
        ok = False
    if not ok:
        with _FILE_JOB_LOCK:
            _FILE_JOB_STATE.pop(key, None)
        return (False, 'Очередь фоновых задач заполнена')
    try:
        _v160_schedule(f'v160:file-tick:{key}', internal_timer_seconds('process_status_refresh', 10.0), _file_job_tick, key)
    except Exception:
        pass
    try:
        bot_journal('r21_fast_file_stage', cid, f'kind={kind_s}; remote={int(_r21_file_job_remote_capable(kind_s, func))}; pool={getattr(pool,"name","")}')
    except Exception:
        pass
    return (True, 'Запущено')

submit_interactive_file_job = _r21_submit_interactive_file_job

try:
    bot_journal('r21_every_button_fast_loaded', int(OWNER_ID or 0),
                'all_callbacks=fast-stage; heavy=second-stage; redis-lock=background; file-singleflight=chat+kind')
except Exception:
    pass

# --- ИСТОЧНИК: 97_r30_policy_ui.py ---
"""Пер-R31 UX/policy layer.

R31 extends the stable R30 layer with a third owner Info-menu mode:
NEW = compact grouped menu, OLD = pre-R29 legacy, THIRD = functional settings hub.
The user-confirmed R28/R29 hot path stays intact: ordinary callback -> handler ->
non-blocking render admission. Telegram network I/O runs only in the dedicated
window-render executor; no remote HTTP or heavy snapshot is inserted before admission.
"""

R31_RELEASE_NAME = 'Пер-R43'
R30_RELEASE_NAME = R31_RELEASE_NAME
R29_RELEASE_NAME = R31_RELEASE_NAME
R29_RELEASE_STAGE = 'directive-google-info-input-sources-three-menu-modes'
R31_MENU_MODE_THIRD = 'third'
R30_MENU_MODE_KEY = 'r30_info_menu_mode'
R30_MENU_MODE_DEFAULT = 'new'
R29_INPUT_SETTINGS_KEY = 'r29_input_sources'
R29_INPUT_DEFAULTS = {'forwarded': True, 'other_bots': True}

def r29_assert_r28_fast_ui_contract() -> bool:
    """Semantic startup guard for the R49 non-blocking button-render contract.

    The callback owner may prepare a payload in RAM, but Telegram network RTT must
    run only in WINDOW_RENDER_TASK_POOL.
    """
    fn = globals().get('fast_ui_edit_message_text')
    canonical = globals().get('_canon_fast_ui_edit_message_text__001')
    if not callable(fn):
        raise RuntimeError('R29 FAST UI CONTRACT: fast_ui_edit_message_text is missing')
    if not callable(canonical) or fn is not canonical:
        raise RuntimeError('R29 FAST UI CONTRACT: active renderer is not the canonical owner')
    try:
        source = inspect.getsource(canonical)
    except Exception as exc:
        raise RuntimeError('R29 FAST UI CONTRACT: cannot inspect canonical renderer: ' + str(exc))
    if 'WINDOW_RENDER_TASK_POOL.submit_latest' not in source or '_r22_execute_window_render' not in source:
        raise RuntimeError('R29 FAST UI CONTRACT: latest-wins render admission is missing')
    if '_perform_fast_ui_edit(payload)' in source or '_v160_time.sleep(' in source:
        raise RuntimeError('R29 FAST UI CONTRACT: Telegram RTT/sleep leaked back into callback renderer')
    return True

# Enforce immediately after all R28 modules have loaded and before accepting traffic.
r29_assert_r28_fast_ui_contract()

# ---------------------------------------------------------------------------
# Input sources: local per-chat/contour switches.  Defaults preserve R28.
# ---------------------------------------------------------------------------

def r29_input_source_settings(chat_id: int, create: bool=True) -> dict:
    cid = int(chat_id)
    store = get_chat_store(cid)
    settings = store.setdefault('settings', {})
    row = settings.get(R29_INPUT_SETTINGS_KEY)
    if not isinstance(row, dict):
        if not create:
            return dict(R29_INPUT_DEFAULTS)
        row = dict(R29_INPUT_DEFAULTS)
        settings[R29_INPUT_SETTINGS_KEY] = row
    for key, value in R29_INPUT_DEFAULTS.items():
        row.setdefault(key, value)
    row['forwarded'] = bool(row.get('forwarded', True))
    row['other_bots'] = bool(row.get('other_bots', True))
    return row


def r29_input_source_enabled(chat_id: int, key: str) -> bool:
    key = str(key or '')
    if key not in R29_INPUT_DEFAULTS:
        return True
    try:
        return bool(r29_input_source_settings(int(chat_id), False).get(key, True))
    except Exception:
        return True


def r30_info_menu_mode(chat_id: int, create: bool=False) -> str:
    """Persistent presentation-only mode for the owner's Info menu.

    NEW keeps the compact grouped R29/R30 menu. OLD renders the exact legacy
    Info content captured before R29 and only injects the mode/source controls.
    This is a RAM/local setting read on the UI hot path; persistence is deferred.
    """
    cid = int(chat_id)
    store = get_chat_store(cid)
    settings = store.setdefault('settings', {})
    mode = str(settings.get(R30_MENU_MODE_KEY, R30_MENU_MODE_DEFAULT) or R30_MENU_MODE_DEFAULT).strip().lower()
    if mode not in {'new', 'old', R31_MENU_MODE_THIRD}:
        mode = R30_MENU_MODE_DEFAULT
    if create:
        settings[R30_MENU_MODE_KEY] = mode
    return mode


def r30_set_info_menu_mode(chat_id: int, mode: str) -> str:
    cid = int(chat_id)
    value = str(mode or '').strip().lower()
    if value not in {'new', 'old', R31_MENU_MODE_THIRD}:
        value = R30_MENU_MODE_DEFAULT
    store = get_chat_store(cid)
    settings = store.setdefault('settings', {})
    settings[R30_MENU_MODE_KEY] = value
    return value


def _r30_menu_mode_button(chat_id: int):
    mode = r30_info_menu_mode(int(chat_id), False)
    label = {
        'new': '🧭 Меню: Новое',
        'old': '🧭 Меню: Старое',
        R31_MENU_MODE_THIRD: '🧭 Меню: Третий вариант',
    }.get(mode, '🧭 Меню: Новое')
    return IB(label, callback_data='r30:menu:toggle')


def _r29_is_self_bot_message(msg) -> bool:
    try:
        sender = getattr(msg, 'from_user', None)
        if sender is None or not bool(getattr(sender, 'is_bot', False)):
            return False
        sender_id = int(getattr(sender, 'id', 0) or 0)
        # Hot-path invariant: derive our bot id from BOT_TOKEN only; never call getMe here.
        token = str(globals().get('BOT_TOKEN') or '').strip()
        head = token.split(':', 1)[0].strip()
        me_id = int(head) if head.isdigit() else 0
        return bool(me_id and sender_id == me_id)
    except Exception:
        return False


def r29_inbound_message_allowed(msg):
    """Return (allowed, reason).  Called at the very top of the common router.

    This is a RAM-only check: no SQLite/Redis/network is allowed on the hot path.
    """
    try:
        cid = int(msg.chat.id)
    except Exception:
        return (True, '')
    if _r29_is_self_bot_message(msg):
        return (False, 'self_bot_loop_guard')
    try:
        if bool(globals().get('is_forwarded_telegram_message', lambda _m: False)(msg)) and not r29_input_source_enabled(cid, 'forwarded'):
            return (False, 'forwarded_disabled')
    except Exception:
        pass
    try:
        sender = getattr(msg, 'from_user', None)
        is_bot = bool(getattr(sender, 'is_bot', False)) if sender is not None else False
        # Anonymous/send-as-chat admins are treated as human-originated by the legacy helper.
        anon = bool(globals().get('_forward_anonymous_admin_message', lambda _m: False)(msg))
        if is_bot and not anon and not r29_input_source_enabled(cid, 'other_bots'):
            return (False, 'other_bots_disabled')
    except Exception:
        pass
    return (True, '')


def _r29_inputs_can_manage(chat_id: int, user_id: int) -> bool:
    cid, uid = int(chat_id), int(user_id or 0)
    if uid == int(OWNER_ID or 0):
        return True
    try:
        fn = globals().get('tenant_can_manage')
        if callable(fn):
            return bool(fn(uid, chat_id=cid))
    except Exception:
        pass
    return False


def _r29_inputs_text(chat_id: int) -> str:
    cid = int(chat_id)
    row = r29_input_source_settings(cid, False)
    directive = bool(globals().get('directive_chat_enabled_v223', lambda _c: False)(cid))
    return window_mark(
        '📥 ИСТОЧНИКИ СООБЩЕНИЙ\n\n'
        f"📨 Пересланные сообщения: {'✅ принимаются' if row.get('forwarded', True) else '⬜ игнорируются'}\n"
        f"🤖 Сообщения других ботов: {'✅ принимаются' if row.get('other_bots', True) else '⬜ игнорируются'}\n\n"
        'Сообщения самого этого бота всегда блокируются для защиты от циклов.\n'
        + ('\n🔒 Директивный режим включён. Эти параметры считаются внутренними и остаются доступными.' if directive else ''),
        'Ф3237'
    )


def _r29_inputs_keyboard(chat_id: int):
    row = r29_input_source_settings(int(chat_id), False)
    kb = types.InlineKeyboardMarkup(row_width=1)
    kb.row(IB(('✅ ' if row.get('forwarded', True) else '⬜ ') + 'Принимать пересланные', callback_data='r29:inputs:toggle:forwarded'))
    kb.row(IB(('✅ ' if row.get('other_bots', True) else '⬜ ') + 'Принимать от других ботов', callback_data='r29:inputs:toggle:other_bots'))
    kb.row(IB('🔙 Назад', callback_data='nav_prev'), IB('❌ Закрыть', callback_data='info_close'))
    return kb


def _r29_persist_chat_settings_background(chat_id: int, reason: str='r29_settings') -> None:
    cid = int(chat_id)
    def _job():
        try:
            save_data(data, chat_ids=[cid])
        except TypeError:
            try: save_data(data)
            except Exception: pass
        except Exception:
            pass
        try:
            bot_journal('r29_settings_persist', cid, str(reason)[:100])
        except Exception:
            pass
    try:
        pool = globals().get('GENERAL_TASK_POOL')
        if pool is not None:
            submit_unique = getattr(pool, 'submit_unique', None)
            if callable(submit_unique):
                submit_unique(f'r29-settings:{cid}', _job)
            else:
                pool.submit(f'r29-settings:{cid}', _job)
            return
    except Exception:
        pass
    # Never make a visual callback wait for persistence.
    try:
        threading.Thread(target=_job, daemon=True, name='r29-settings-persist').start()
    except Exception:
        pass

# ---------------------------------------------------------------------------
# Directive mode: business-logic mutation is owner-controlled; internal settings
# and normal business actions stay available.
# ---------------------------------------------------------------------------

def _r29_is_business_mutation_callback(raw: str) -> bool:
    value = str(raw or '')
    try:
        old = globals().get('_v223_is_mode_mutation_callback')
        if callable(old) and old(value):
            return True
    except Exception:
        pass
    # Forward routing/finance switches alter the contour's business topology.
    if value.startswith(('fw_new_mode:', 'fw_new_fin:', 'fw_new_clear:')):
        return True
    # Task dispatcher/branch enablement alters which business workflow is active.
    if value.startswith(('v172:task:toggle:', 'v174:td:toggle:', 'v174:td:branch:toggle:', 'v174:td:branch:add', 'v174:td:branch:delete:')):
        return True
    # Finance mode/quick-balance mode selectors.
    if value.startswith('d:') and any(token in value for token in (
        'fin_mode_toggle_', 'fin_mode_off_', 'qb_mode_normal_', 'qb_mode_open_',
        'qb_mode_first_', 'qb_hidden_toggle_', 'qb_finwin_open_')):
        return True
    return False


def _r29_directive_block_text(chat_id: int) -> str:
    return window_mark(
        '🔒 ДИРЕКТИВНЫЙ РЕЖИМ\n\n'
        'Владелец зафиксировал бизнес-логику этого контура.\n'
        'Переключать рабочие режимы, маршруты пересылки и другие бизнес-настройки здесь нельзя.\n\n'
        'То, что было включено владельцем, продолжает работать. Внутренние настройки можно менять.\n\n'
        'Если нужно изменить бизнес-логику — напишите владельцу.',
        'Ф3237'
    )


def _r29_directive_block_keyboard():
    kb = types.InlineKeyboardMarkup(row_width=1)
    kb.row(IB('✉️ Написать владельцу', callback_data='r29:directive:contact_owner'))
    kb.row(IB('🔙 Назад', callback_data='nav_prev'), IB('❌ Закрыть', callback_data='aux_close'))
    return kb

# ---------------------------------------------------------------------------
# Compact INFO.  The old INFO keyboard is retained as a source of functionality,
# but grouped behind six local submenus.
# ---------------------------------------------------------------------------

_R29_LEGACY_INFO_TEXT = globals().get('build_info_text')
_R29_LEGACY_INFO_KB = globals().get('build_info_keyboard')


def _r29_button_text(btn) -> str:
    return str(getattr(btn, 'text', '') or '')


def _r29_button_callback(btn) -> str:
    return str(getattr(btn, 'callback_data', '') or '')


def _r29_legacy_info_rows(chat_id: int):
    try:
        kb = _R29_LEGACY_INFO_KB(int(chat_id)) if callable(_R29_LEGACY_INFO_KB) else types.InlineKeyboardMarkup()
        rows = globals().get('_v177_info_rows')
        if callable(rows):
            return list(rows(kb) or [])
        return list(getattr(kb, 'keyboard', None) or [])
    except Exception:
        return []


def _r29_info_group_for_button(btn) -> str:
    text = _r29_button_text(btn).casefold()
    cb = _r29_button_callback(btn).casefold()
    if cb.startswith(('r29:',)):
        return ''
    if cb in {'info_close', 'aux_close', 'nav_prev'} or 'назад' in text or 'закры' in text:
        return ''
    if any(k in text for k in ('журнал', 'лог', 'ошибк')) or any(k in cb for k in ('journal', 'log', 'error')):
        return 'journals'
    if any(k in text for k in ('google', 'render #2', 'mega', 'telegram durable', 'хранилищ')) or any(k in cb for k in ('google', 'worker', 'storage', 'external')):
        return 'integrations'
    if any(k in text for k in ('скорост', 'диагност', 'очеред', 'трафик', 'watcher', 'состояние')) or any(k in cb for k in ('speed', 'diag', 'queue', 'traffic', 'watcher')):
        return 'status'
    if any(k in text for k in ('режим', 'таймер', 'восстанов', 'кнопк', 'настройк', 'защит')) or any(k in cb for k in ('mode', 'timer', 'restore', 'config', 'constitution')):
        return 'settings'
    return 'owner'


def _r29_info_group_keyboard(chat_id: int, group: str):
    cid = int(chat_id)
    kb = types.InlineKeyboardMarkup(row_width=2)
    for row in _r29_legacy_info_rows(cid):
        selected = [b for b in (row or []) if _r29_info_group_for_button(b) == group]
        if selected:
            kb.row(*selected[:3])
    if group == 'settings':
        kb.row(IB('📥 Источники сообщений', callback_data='r29:inputs:open'))
    kb.row(IB('🔙 В Инфо', callback_data='r29:info:main'), IB('❌ Закрыть', callback_data='info_close'))
    return kb


def _r29_info_group_text(group: str) -> str:
    title = {
        'status': '📊 СОСТОЯНИЕ И ДИАГНОСТИКА',
        'integrations': '🔗 ИНТЕГРАЦИИ И ХРАНИЛИЩЕ',
        'settings': '⚙️ НАСТРОЙКИ И ПРОЦЕССЫ',
        'journals': '📁 ЖУРНАЛЫ И ОШИБКИ',
        'owner': '🛠 ИНСТРУМЕНТЫ ВЛАДЕЛЬЦА',
    }.get(group, 'ℹ️ ИНФО')
    return window_mark(title + '\n\nВыберите нужный пункт. Тяжёлые проверки выполняются только после открытия локального окна.', 'Ф89')


# ---------------------------------------------------------------------------
# R31 THIRD INFO MODE: functional owner settings hub.
# It reuses the exact legacy buttons/callbacks and only changes navigation.
# ---------------------------------------------------------------------------

def _r31_third_group_for_button(btn) -> str:
    text = _r29_button_text(btn).casefold()
    cb = _r29_button_callback(btn).casefold()
    if not cb or cb == 'none':
        return ''
    if cb.startswith(('r29:', 'r30:', 'r31:')):
        return ''
    if cb in {'info_close', 'aux_close', 'nav_prev'} or 'назад' in text or 'закры' in text:
        return ''

    # Business modes first.  Broad matching is deliberate: every historical
    # finance/forward/reminder/task setting remains reachable without copying it.
    if (any(k in text for k in ('фин', 'гомон', 'валют', 'usd', 'ars', 'остат', 'excel', 'google'))
            or cb.startswith(('fin:', 'fin_', 'finance:', 'finance_'))
            or any(k in cb for k in ('gomonk', 'usd', 'currency', 'remaining', 'google', 'gsync', 'gmenu'))):
        return 'finance'
    if (any(k in text for k in ('пересыл', 'форвард', 'forward'))
            or cb.startswith(('fw_', 'fw:', 'forward')) or 'forward' in cb):
        return 'forward'
    if (any(k in text for k in ('напомин', 'reminder')) or 'remind' in cb):
        return 'reminders'
    if (any(k in text for k in ('задач', 'диспетчер задач', 'task')) or 'task' in cb):
        return 'tasks'

    if (any(k in text for k in ('контур', 'круг', 'пространств', 'директив', 'доступ к меню', 'владельц пространств'))
            or any(k in cb for k in ('directive', 'contour', 'circle', 'tenant', 'space', 'owners'))):
        return 'contours'
    if (any(k in text for k in ('журнал', 'лог', 'ошибк', 'тз окон', 'маркиров'))
            or any(k in cb for k in ('journal', 'log', 'error', 'export_tz', 'export_markers'))):
        return 'journals'
    if (any(k in text for k in ('render #2', 'mega', 'хранилищ', 'constitution', 'защит', 'процесс', 'скорост', 'исходник', 'депло', 'восстанов', 'ветк', 'telegram durable', 'самопеленг'))
            or any(k in cb for k in ('r10:worker', 'storage', 'constitution', 'v176:', 'v234:config', 'v233:external', 'branch', 'source', 'keepalive'))):
        return 'owner'
    return 'general'


def _r31_third_group_title(group: str) -> str:
    return {
        'finance': '💰 НАСТР. ФИН',
        'forward': '📤 НАСТР. ПЕРЕСЫЛКИ',
        'reminders': '⏰ НАСТР. НАПОМИНАНИЙ',
        'tasks': '📋 НАСТР. ЗАДАЧ',
        'contours': '🏢 НАСТРОЙКИ КОНТУРОВ',
        'general': '⚙️ ОБЩИЕ НАСТРОЙКИ',
        'journals': '📁 ЖУРНАЛЫ',
        'owner': '🛠 ДЛЯ ВЛАДЕЛЬЦА',
    }.get(str(group or ''), 'ℹ️ НАСТРОЙКИ')


def _r31_third_group_text(group: str) -> str:
    return window_mark(_r31_third_group_title(group) + '\n\nЗдесь собраны штатные настройки этого раздела. Сами обработчики не дублируются: используются существующие кнопки бота.', 'Ф89')


def _r31_third_group_keyboard(chat_id: int, group: str):
    cid = int(chat_id)
    kb = types.InlineKeyboardMarkup(row_width=2)
    seen = set()
    for row in _r29_legacy_info_rows(cid):
        selected = []
        for b in (row or []):
            if _r31_third_group_for_button(b) != group:
                continue
            cb = _r29_button_callback(b)
            if not cb or cb in seen:
                continue
            seen.add(cb)
            selected.append(b)
        if selected:
            kb.row(*selected[:3])
    if group == 'general':
        kb.row(IB('📥 Источники сообщений', callback_data='r29:inputs:open'))
    if group == 'owner' and not _r31_constructors_enabled():
        kb.row(IB('🧩 Конструкторы', callback_data='r31:constructors:open'))
    kb.row(IB('🔙 В меню', callback_data='r31:info:main'), IB('❌ Закрыть', callback_data='info_close'))
    return kb


def _r31_tz_markers_state() -> str:
    try:
        tz = bool(circle_annotation_global_enabled_v219('tz'))
        mr = bool(circle_annotation_global_enabled_v219('iz_mr'))
    except Exception:
        tz = mr = True
    if tz and mr:
        return 'on'
    if not tz and not mr:
        return 'off'
    return 'mixed'


def _r31_tz_markers_button():
    state = _r31_tz_markers_state()
    icon = '✅' if state == 'on' else '⬜' if state == 'off' else '🟨'
    return IB(f'{icon} ТЗ окон + маркеры', callback_data='r31:toggle:tz_markers')


def _r31_constructors_enabled() -> bool:
    try:
        return bool(_v196_flags().get('enabled', True))
    except Exception:
        return True


def _r31_constructors_toggle_button():
    return IB(('✅ ' if _r31_constructors_enabled() else '⬜ ') + 'Конструкторы в окнах', callback_data='r31:toggle:constructors')


def _r31_constructors_text() -> str:
    enabled = _r31_constructors_enabled()
    try:
        flags = dict(_v196_flags())
    except Exception:
        flags = {}
    return window_mark(
        '🧩 КОНСТРУКТОРЫ\n\n'
        f"Мастер-переключатель: {'✅ ВКЛ' if enabled else '⬜ ВЫКЛ'}\n"
        f"Конструктор 1 после включения: {'✅ показывать' if flags.get('show_c1', True) else '⬜ скрывать'}\n"
        f"Конструктор 2 после включения: {'✅ показывать' if flags.get('show_c2', True) else '⬜ скрывать'}\n\n"
        'Если мастер-переключатель выключен, кнопки Конструктор 1/2 не добавляются в рабочие окна. Этот центр управления остаётся доступным всегда.',
        'Ф89')


def _r31_constructors_keyboard():
    kb = types.InlineKeyboardMarkup(row_width=1)
    kb.row(_r31_constructors_toggle_button())
    kb.row(IB('🛠 Открыть Конструктор 2', callback_data='r31:constructors:launch_c2'))
    kb.row(IB('🔙 В меню', callback_data='r31:info:main'), IB('❌ Закрыть', callback_data='info_close'))
    return kb


def _r31_persist_global_background(reason: str='r31_global') -> None:
    def _job():
        try:
            save_data(data, root_only=True)
        except TypeError:
            try: save_data(data)
            except Exception: pass
        except Exception:
            pass
        try:
            fn = globals().get('schedule_delta_backup')
            if callable(fn):
                fn(int(OWNER_ID or 0), delay=0.8, reason=str(reason)[:90])
        except Exception:
            pass
        try: bot_journal('r31_global_setting_persist', int(OWNER_ID or 0), str(reason)[:120])
        except Exception: pass
    try:
        pool = globals().get('GENERAL_TASK_POOL')
        submit_unique = getattr(pool, 'submit_unique', None) if pool is not None else None
        if callable(submit_unique):
            submit_unique('r31-global:' + str(reason)[:70], _job)
            return
        if pool is not None:
            pool.submit('r31-global:' + str(reason)[:70], _job)
            return
    except Exception:
        pass
    try: threading.Thread(target=_job, daemon=True, name='r31-global-persist').start()
    except Exception: pass


def _r31_schedule_constructor_markup_refresh() -> None:
    """Refresh already-open owner keyboards after the visible toggle response.

    New windows already honor _v196_flags()['enabled']; this only removes/restores
    Constructor 1/2 buttons in owner windows that are currently still open.
    """
    def _job():
        try:
            lock = globals().get('_V221_LIVE_MARKUP_LOCK')
            reg = globals().get('_V221_LIVE_MARKUP')
            if lock is None or not isinstance(reg, dict):
                return
            with lock:
                rows = [(k, dict(v or {})) for k, v in reg.items()]
        except Exception:
            return
        changed = 0
        for (cid, mid), row in rows:
            try:
                if int(cid) != int(OWNER_ID or 0):
                    continue
                source = row.get('source_markup') if row.get('source_markup') is not None else row.get('markup')
                render = globals().get('v227_render_effective_contour_markup')
                if not callable(render):
                    continue
                after = render(source, str(row.get('text') or ''), int(cid))
                fp = globals().get('_v221_markup_fingerprint')
                if callable(fp) and fp(row.get('markup')) == fp(after):
                    continue
                bot.edit_message_reply_markup(chat_id=int(cid), message_id=int(mid), reply_markup=after)
                rec = globals().get('v221_record_live_markup')
                if callable(rec):
                    rec(int(cid), int(mid), after, str(row.get('text') or ''), source_markup=source)
                changed += 1
            except Exception:
                continue
        try: bot_journal('r31_constructor_markup_refresh', int(OWNER_ID or 0), f'changed={changed}')
        except Exception: pass
    try:
        pool = globals().get('GENERAL_TASK_POOL')
        submit_unique = getattr(pool, 'submit_unique', None) if pool is not None else None
        if callable(submit_unique):
            submit_unique('r31-constructor-markup-refresh', _job)
            return
    except Exception:
        pass
    try: threading.Thread(target=_job, daemon=True, name='r31-constructor-refresh').start()
    except Exception: pass


def _r31_third_info_text(chat_id: int) -> str:
    return window_mark(
        'ℹ️ ИНФО · Пер-R43 · ТРЕТИЙ ВАРИАНТ\n\n'
        'Настройки собраны по рабочим режимам и административным разделам.\n'
        'ТЗ/маркеры и Конструкторы имеют отдельные мастер-переключатели.\n\n'
        '⚡ FAST UI R28: прямой render защищён.',
        'Ф89')


def _r31_third_info_keyboard(chat_id: int):
    kb = types.InlineKeyboardMarkup(row_width=2)
    kb.row(IB('💰 Настр. фин', callback_data='r31:info:finance'), IB('📤 Настр. пересылки', callback_data='r31:info:forward'))
    kb.row(IB('⏰ Настр. напоминаний', callback_data='r31:info:reminders'), IB('📋 Настр. задач', callback_data='r31:info:tasks'))
    kb.row(IB('🏢 Настройки контуров', callback_data='r31:info:contours'))
    kb.row(IB('⚙️ Общие настройки', callback_data='r31:info:general'))
    kb.row(IB('📁 Журналы', callback_data='r31:info:journals'), IB('🛠 Для владельца', callback_data='r31:info:owner'))
    kb.row(_r31_tz_markers_button())
    kb.row(_r31_constructors_toggle_button())
    # Always present even when constructors are globally hidden.
    kb.row(IB('🧩 Конструкторы', callback_data='r31:constructors:open'))
    kb.row(_r30_menu_mode_button(int(chat_id)))
    kb.row(IB('🔙 Назад', callback_data='nav_prev'), IB('❌ Закрыть', callback_data='info_close'))
    return kb

def _r30_legacy_info_keyboard_with_controls(chat_id: int):
    """Legacy pre-R29 Info keyboard + only the two R29/R30 local controls."""
    cid = int(chat_id)
    kb = _R29_LEGACY_INFO_KB(cid) if callable(_R29_LEGACY_INFO_KB) else types.InlineKeyboardMarkup()
    try:
        rows_fn = globals().get('_v177_info_rows')
        set_fn = globals().get('_v177_info_set_rows')
        rows = list(rows_fn(kb) or []) if callable(rows_fn) else list(getattr(kb, 'keyboard', None) or [])
        # Remove stale copies so repeated toggles never multiply buttons.
        clean = []
        for row in rows:
            kept = [b for b in (row or []) if _r29_button_callback(b) not in {'r29:inputs:open', 'r30:menu:toggle'}]
            if kept:
                clean.append(kept)
        rows = clean
        insert_at = len(rows)
        for i, row in enumerate(rows):
            if any((_r29_button_callback(b) in {'info_close', 'aux_close', 'nav_prev'} or 'назад' in _r29_button_text(b).casefold() or 'закры' in _r29_button_text(b).casefold()) for b in (row or [])):
                insert_at = i
                break
        rows.insert(insert_at, [IB('📥 Источники сообщений', callback_data='r29:inputs:open')])
        cursor = insert_at + 1
        if not _r31_constructors_enabled():
            rows.insert(cursor, [IB('🧩 Конструкторы', callback_data='r31:constructors:open')])
            cursor += 1
        rows.insert(cursor, [_r30_menu_mode_button(cid)])
        if callable(set_fn):
            return set_fn(kb, rows)
        # Fallback if the historical row helpers are unavailable.
        out = types.InlineKeyboardMarkup(row_width=2)
        for row in rows:
            out.row(*row)
        return out
    except Exception:
        try:
            kb.row(IB('📥 Источники сообщений', callback_data='r29:inputs:open'))
            kb.row(_r30_menu_mode_button(cid))
        except Exception:
            pass
        return kb


_R49_REDIS_CONTROL_LOCK = __import__('threading').RLock()
_R49_REDIS_CONTROL = {'switching': False, 'target': False, 'peer_ok': None, 'detail': ''}


# R59 owner diagnostics: distinguish immutable Render input ENV from packaged/effective
# runtime values.  Secrets are never printed verbatim.
_R59_ENV_PAGE_SIZE = 18
_R59_RENDER_IMPORTANT = {
    'APP_URL','WEBHOOK_URL','PORT','BOT_SPLIT_ROLE','RENDER_TELEGRAM_ONLY',
    'B_T','BOT_TOKEN','OWNER_ID','ID','BACKUP_CHAT_ID','TELEGRAM_BACKUP_ENABLED',
    'MEGA_ENABLED','MEGA_BACKUP_DIR','MEGA_EMAIL','MEGA_PASSWORD','MEGA_SESSION','MEGA_TIMEOUT',
    'REDIS_ENABLED','REDIS_START_ENABLED','REDIS_URL','RENDER_KEY_VALUE_URL','KEY_VALUE_URL','VALKEY_URL',
    'PEER_SERVICE_URL','FRONT_SERVICE_URL','FRONT_PRIVATE_URL','PEER_SHARED_SECRET',
    'GOOGLE_SERVICE_ACCOUNT_JSON','GOOGLE_SHEETS_SHARE_EMAIL','QUICK_EXPENSE_CHAT_ID','QUICK_EXPENSE_KEY',
}
_R59_RENDER_PREFIXES = ('MEGA_','REDIS_','TELEGRAM_','TG_','PEER_','FRONT_','SPLIT_','GOOGLE_','QUICK_','WEBHOOK_','BOT_','R43_','R38_')
_R59_SECRET_TOKENS = ('TOKEN','SECRET','PASSWORD','PRIVATE','CREDENTIAL','SERVICE_ACCOUNT_JSON','QUICK_EXPENSE_KEY')

def _r59_mask_value(name, value):
    key=str(name or '').upper(); raw=str(value if value is not None else '')
    if not raw:
        return '<empty>'
    if key in {'B_T','BOT_TOKEN'} or any(tok in key for tok in _R59_SECRET_TOKENS):
        return f'<set len={len(raw)}>'
    if 'URL' in key and '://' in raw:
        try:
            from urllib.parse import urlsplit, urlunsplit
            p=urlsplit(raw)
            host=p.hostname or ''
            if p.port: host += ':'+str(p.port)
            if p.username or p.password: host='***@'+host
            return urlunsplit((p.scheme,host,p.path or '', '', ''))[:180]
        except Exception:
            return '<configured URL>'
    return raw.replace('\n','\\n')[:220]

def _r59_render_env_rows():
    try:
        import runtime_config as rc
        snap=dict(rc.render_env_snapshot() or {})
    except Exception:
        snap={}
    keys=set(k for k in snap if k in _R59_RENDER_IMPORTANT or str(k).startswith(_R59_RENDER_PREFIXES))
    # Always expose the master switches even when they were omitted in Render.
    keys.update({'MEGA_ENABLED','MEGA_BACKUP_DIR','REDIS_ENABLED','REDIS_START_ENABLED','REDIS_URL','TELEGRAM_BACKUP_ENABLED','BACKUP_CHAT_ID','PEER_SERVICE_URL'})
    return [f'{k}={_r59_mask_value(k, snap.get(k) if k in snap else "<not set>")}' for k in sorted(keys)]

def _r59_code_runtime_rows():
    rows=[]
    try:
        import runtime_config as rc
        st=dict(rc.redis_runtime_state() or {})
        rows.extend([
            f'CONFIG_VERSION={getattr(rc,"CONFIG_VERSION","?")}',
            f'MEGA_ENABLED(effective)={str(_split_os.getenv("MEGA_ENABLED","") or "")}',
            f'MEGA_BACKUP_DIR(effective)={str(_split_os.getenv("MEGA_BACKUP_DIR","") or "")}',
            f'REDIS master(Render)={int(bool(st.get("master_enabled")))} start(Render)={int(bool(st.get("start_enabled")))} configured={int(bool(st.get("configured")))}',
            f'REDIS runtime={int(bool(st.get("enabled")))} mode={str(st.get("mode") or "?")} · restart={"ON" if bool(st.get("restart_enabled")) else "OFF"}',
            f'REDIS effective URL={"<active>" if _r61_effective_redis_url() else "<inactive>"} · source=Render only',
            f'REDIS last_switch={str(_R49_REDIS_CONTROL.get("detail") or "-")[:180]}',
            f'TELEGRAM_BACKUP_ENABLED(effective)={str(_split_os.getenv("TELEGRAM_BACKUP_ENABLED","") or "")}',
            '--- packaged FRONT_INTERNAL_ENV ---',
        ])
        cfg=dict(rc.internal_runtime_config('front') or {})
        rows.extend(f'{k}={_r59_mask_value(k,v)}' for k,v in sorted(cfg.items()))
    except Exception as exc:
        rows.append(f'ERROR={type(exc).__name__}: {str(exc)[:180]}')
    return rows

def _r59_vars_text(kind, page=0):
    kind='render' if str(kind)=='render' else 'code'
    rows=_r59_render_env_rows() if kind=='render' else _r59_code_runtime_rows()
    size=_R59_ENV_PAGE_SIZE; pages=max(1,(len(rows)+size-1)//size); page=max(0,min(int(page or 0),pages-1))
    chunk=rows[page*size:(page+1)*size]
    title='🌐 RENDER ENV · FAST (#1)' if kind=='render' else '🧩 ПЕРЕМЕННЫЕ КОДА / RUNTIME · FAST (#1)'
    note='Снимок Render ENV до runtime. Секреты замаскированы; REDIS_ENABLED/REDIS_START_ENABLED/REDIS_URL принадлежат только Render.' if kind=='render' else 'Эффективное runtime-состояние. Redis master/start/url не создаются кодом.'
    return window_mark(title+f'\nСтраница {page+1}/{pages}\n{note}\n\n'+'\n'.join(chunk), 'Ф89'), pages, page

def _r59_vars_keyboard(kind, page=0):
    text,pages,page=_r59_vars_text(kind,page)
    kb=types.InlineKeyboardMarkup(row_width=2)
    nav=[]
    if page>0: nav.append(IB('◀️',callback_data=f'r59:vars:{kind}:{page-1}'))
    if page+1<pages: nav.append(IB('▶️',callback_data=f'r59:vars:{kind}:{page+1}'))
    if nav: kb.row(*nav)
    kb.row(IB('🌐 Render ENV',callback_data='r59:vars:render:0'),IB('🧩 Код/runtime',callback_data='r59:vars:code:0'))
    kb.row(IB('🔙 В Инфо',callback_data='r29:info:main'),IB('❌ Закрыть',callback_data='info_close'))
    return text,kb

def _r59_fast_redis_probe():
    url=_r61_effective_redis_url()
    if not url: return False,'FAST REDIS_URL empty'
    if _split_redis is None: return False,'FAST redis package unavailable'
    client=None
    try:
        client=_split_redis.Redis.from_url(url,socket_connect_timeout=0.8,socket_timeout=1.2,health_check_interval=30)
        ok=bool(client.ping())
        return (ok,'FAST PING=PONG' if ok else 'FAST PING failed')
    except Exception as exc:
        return False,f'FAST {type(exc).__name__}: {str(exc)[:180]}'
    finally:
        try:
            if client is not None: client.close()
        except Exception: pass

def _r59_refresh_fast_redis_consumers():
    try:
        fn=globals().get('key_value_refresh_runtime_v248')
        if callable(fn): fn()
    except Exception: pass

def _r49_redis_runtime_state() -> dict:
    try:
        import runtime_config as _r49_runtime_config
        row = dict(_r49_runtime_config.redis_runtime_state() or {})
    except Exception as exc:
        row = {'configured': False, 'enabled': False, 'error': f'{type(exc).__name__}: {str(exc)[:160]}'}
    with _R49_REDIS_CONTROL_LOCK:
        row['switching'] = bool(_R49_REDIS_CONTROL.get('switching'))
        row['target'] = bool(_R49_REDIS_CONTROL.get('target'))
        row['peer_ok'] = _R49_REDIS_CONTROL.get('peer_ok')
        row['detail'] = str(_R49_REDIS_CONTROL.get('detail') or '')[:180]
    return row

def _r60_redis_mode_label(st):
    if not st.get('master_enabled'):
        return '⛔ HARD OFF (Render)'
    if not st.get('configured'):
        return '⚠️ URL НЕ НАСТРОЕН'
    if st.get('switching'):
        return '⏳ ПЕРЕКЛЮЧЕНИЕ'
    if st.get('enabled'):
        return '🟢 CACHE ON'
    return '⚪ RUNTIME OFF'


def _r49_redis_button():
    st=_r49_redis_runtime_state()
    return IB('🧱 Redis: '+_r60_redis_mode_label(st), callback_data='r60:redis:menu')


def _r60_redis_menu_text(extra=''):
    st=_r49_redis_runtime_state()
    enabled=bool(st.get('enabled'))
    lines=[
        '🧱 REDIS · R66',
        '',
        f'Render REDIS_ENABLED={1 if st.get("master_enabled") else 0}',
        f'URL={"настроен" if st.get("configured") else "не настроен"}',
        f'FAST runtime={"ON" if enabled else "OFF"}',
        f'Режим={_r60_redis_mode_label(st)}',
        'Роль=фон/кэш/outbox; SQLite остаётся основной базой',
        '',
        'Логика после рестарта:',
        '• REDIS_ENABLED=1 → Redis разрешён',
        '• REDIS_ENABLED=0 → Redis жёстко ВЫКЛ',
        '• REDIS_START_ENABLED=1 → после deploy runtime стартует ON',
        '• REDIS_START_ENABLED=0 → после deploy runtime стартует OFF',
        '• кнопки ниже меняют только runtime до следующего рестарта',
    ]
    detail=str(st.get('detail') or '')[:260]
    if detail:
        lines += ['', 'Последнее переключение: '+detail]
    lines += [f'Render REDIS_START_ENABLED={1 if st.get("start_enabled") else 0}']
    if extra:
        lines += ['', str(extra)[:700]]
    return window_mark('\n'.join(lines),'Ф89')


def _r60_redis_menu_keyboard():
    kb=types.InlineKeyboardMarkup(row_width=2)
    kb.row(IB('🟢 Включить сейчас',callback_data='r60:redis:on'),IB('⚪ Выключить сейчас',callback_data='r60:redis:off'))
    kb.row(IB('🧠 Что внутри Redis',callback_data='r60:redis:inspect:0'),IB('🔄 Обновить',callback_data='r60:redis:menu'))
    kb.row(IB('🔙 В Инфо',callback_data='r29:info:main'),IB('❌ Закрыть',callback_data='info_close'))
    return kb


def _r60_redis_ttl_text(ttl_ms):
    try: ttl=int(ttl_ms)
    except Exception: return '?'
    if ttl == -1: return '∞'
    if ttl < 0: return '-'
    sec=max(0,ttl//1000)
    if sec < 60: return f'{sec}с'
    if sec < 3600: return f'{sec//60}м'
    if sec < 86400: return f'{sec//3600}ч'
    return f'{sec//86400}д'


def _r60_redis_inspect_text(payload, error=''):
    if error:
        return window_mark('🧠 REDIS · СОДЕРЖИМОЕ\n\n❌ '+str(error)[:700], 'Ф89')
    mem=dict(payload.get('memory') or {}); stats=dict(payload.get('stats') or {})
    page=int(payload.get('page') or 0); pages=max(1,int(payload.get('pages') or 1))
    lines=[
        '🧠 REDIS · СОДЕРЖИМОЕ',
        '',
        f'PING={payload.get("ping") or "?"}',
        f'Ключей в DB={int(payload.get("dbsize") or 0)} · просканировано={int(payload.get("scanned") or 0)}'+(' (лимит 500)' if payload.get('truncated') else ''),
        f'Память={mem.get("used_memory_human") or mem.get("used_memory") or 0} · max={mem.get("maxmemory_human") or mem.get("maxmemory") or 0}',
        f'Клиенты={int(stats.get("connected_clients") or 0)} · hits={int(stats.get("keyspace_hits") or 0)} · misses={int(stats.get("keyspace_misses") or 0)}',
        f'evicted={int(stats.get("evicted_keys") or 0)} · expired={int(stats.get("expired_keys") or 0)}',
        '',
        'Готовность к восстановлению:',
        f'• full SQLite={"✅" if (payload.get("recovery") or {}).get("full_snapshot") else "❌"} · deltas={int((payload.get("recovery") or {}).get("deltas") or 0)} · capsule={"✅" if (payload.get("recovery") or {}).get("capsule") else "❌"} · events≈{int((payload.get("recovery") or {}).get("events") or 0)}',
        '',
        'Группы ключей:',
    ]
    prefs=list(payload.get('prefixes') or [])
    if prefs:
        for row in prefs[:10]: lines.append(f'• {row.get("prefix")}: {int(row.get("count") or 0)}')
    else: lines.append('• пусто')
    lines += ['', f'Ключи · страница {page+1}/{pages}:']
    entries=list(payload.get('entries') or [])
    if not entries: lines.append('• Redis пуст')
    for row in entries:
        key=str(row.get('key') or '')
        typ=str(row.get('type') or '?')
        ttl=_r60_redis_ttl_text(row.get('ttl_ms'))
        mem_bytes=int(row.get('bytes') or 0)
        count=row.get('count')
        meta=f'{typ} · TTL {ttl} · {mem_bytes} B'
        if count is not None: meta += f' · n={count}'
        lines.append('• '+key[:170])
        lines.append('  '+meta)
        prev=str(row.get('preview') or '').strip()
        if prev: lines.append('  ↳ '+prev[:190])
    lines += ['', 'Значения с признаками token/password/secret/session маскируются автоматически.']
    return window_mark('\n'.join(lines),'Ф89')


def _r60_redis_inspect_keyboard(page=0,pages=1):
    page=max(0,int(page or 0)); pages=max(1,int(pages or 1))
    kb=types.InlineKeyboardMarkup(row_width=2)
    nav=[]
    if page>0: nav.append(IB('◀️',callback_data=f'r60:redis:inspect:{page-1}'))
    if page+1<pages: nav.append(IB('▶️',callback_data=f'r60:redis:inspect:{page+1}'))
    if nav: kb.row(*nav)
    kb.row(IB('🔄 Обновить',callback_data=f'r60:redis:inspect:{page}'),IB('🧱 Redis режим',callback_data='r60:redis:menu'))
    kb.row(IB('🔙 В Инфо',callback_data='r29:info:main'),IB('❌ Закрыть',callback_data='info_close'))
    return kb


def _r61_redis_preview(value, key='', limit=220):
    name=str(key or '').casefold()
    if any(tok in name for tok in ('token','password','passwd','secret','session','credential','authorization','cookie','private_key')):
        return '<masked>'
    if value is None:
        return ''
    if isinstance(value,(bytes,bytearray)):
        raw=bytes(value)
        # Full SQLite/gzip/blob data is never dumped into Telegram.
        if len(raw)>256 or any(b < 9 or (13 < b < 32) for b in raw[:80]):
            return f'<binary {len(raw)} B>'
        text=raw.decode('utf-8',errors='replace')
    else:
        text=str(value)
    import re as _re
    text=text.replace('\x00','').replace('\r',' ').replace('\n',' ')
    text=_re.sub(r'(?i)(redis|rediss)://[^@\s]+@',r'\1://***@',text)
    text=_re.sub(r'\b\d{6,12}:[A-Za-z0-9_-]{20,}\b','<bot-token>',text)
    text=_re.sub(r'(?i)(password|passwd|secret|token|authorization|cookie)["\'\s:=]+[^,}\]\s]{4,}',r'\1=<masked>',text)
    return text[:max(40,int(limit))]


def _r61_redis_key_row_local(client, raw_key):
    name=raw_key.decode('utf-8',errors='replace') if isinstance(raw_key,(bytes,bytearray)) else str(raw_key)
    try:
        typ=client.type(raw_key)
        if isinstance(typ,(bytes,bytearray)): typ=typ.decode('utf-8',errors='replace')
        typ=str(typ or '?')
    except Exception: typ='?'
    try: ttl=int(client.pttl(raw_key))
    except Exception: ttl=-2
    try: mem=int(client.memory_usage(raw_key) or 0)
    except Exception: mem=0
    count=None; preview=''
    try:
        if typ=='string':
            val=client.get(raw_key); count=len(val) if isinstance(val,(bytes,bytearray,str)) else None
            preview=_r61_redis_preview(val,name)
        elif typ=='hash':
            count=int(client.hlen(raw_key) or 0); vals=client.hscan(raw_key,count=4)[1] or {}
            preview=_r61_redis_preview({(_r61_redis_preview(k,name,60)): _r61_redis_preview(v,name,100) for k,v in list(vals.items())[:4]},name)
        elif typ=='list':
            count=int(client.llen(raw_key) or 0); preview=_r61_redis_preview(client.lrange(raw_key,0,3),name)
        elif typ=='set':
            count=int(client.scard(raw_key) or 0); preview=_r61_redis_preview(list(client.sscan(raw_key,count=4)[1] or [])[:4],name)
        elif typ=='zset':
            count=int(client.zcard(raw_key) or 0); preview=_r61_redis_preview(client.zrange(raw_key,0,3,withscores=True),name)
        elif typ=='stream':
            info=client.xinfo_stream(raw_key); count=int(info.get('length') or 0) if isinstance(info,dict) else None
            preview=_r61_redis_preview(client.xrevrange(raw_key,count=2),name)
    except Exception as exc:
        preview=f'<preview error {type(exc).__name__}>'
    return {'key':name[:220],'type':typ,'ttl_ms':ttl,'bytes':mem,'count':count,'preview':preview}


def _r61_redis_prefix_local(name):
    parts=str(name or '').split(':')
    if not parts: return '(empty)'
    if parts[0]=='vysbot' and len(parts)>=3: return ':'.join(parts[:3])+':*'
    if parts[0]=='vys262' and len(parts)>=2: return ':'.join(parts[:2])+':*'
    if parts[0]=='per' and len(parts)>=4: return ':'.join(parts[:4])+':*'
    return ':'.join(parts[:min(3,len(parts))])+(':*' if len(parts)>3 else '')


def _r61_fetch_redis_inspect_direct(page=0):
    url=_r61_effective_redis_url()
    if not url:
        raise RuntimeError('Redis runtime is OFF or REDIS_URL is not configured in Render')
    try:
        import redis as _redis_pkg
    except Exception as exc:
        raise RuntimeError('redis package unavailable') from exc
    client=None
    try:
        page=max(0,min(99,int(page or 0))); page_size=10
        client=_redis_pkg.Redis.from_url(url,socket_connect_timeout=0.9,socket_timeout=1.5,health_check_interval=30)
        pong=bool(client.ping())
        info_mem=client.info('memory') or {}; info_stats=client.info('stats') or {}; info_clients=client.info('clients') or {}
        try: dbsize=int(client.dbsize() or 0)
        except Exception: dbsize=0
        keys=[]; truncated=False
        for raw in client.scan_iter(match='*',count=200):
            keys.append(raw)
            if len(keys)>=500: truncated=True; break
        keys.sort(key=lambda x: x.decode('utf-8',errors='replace') if isinstance(x,(bytes,bytearray)) else str(x))
        decoded=[]; prefix_counts={}
        for raw in keys:
            name=raw.decode('utf-8',errors='replace') if isinstance(raw,(bytes,bytearray)) else str(raw)
            decoded.append((name,raw)); pref=_r61_redis_prefix_local(name); prefix_counts[pref]=prefix_counts.get(pref,0)+1
        pages=max(1,(len(decoded)+page_size-1)//page_size); page=max(0,min(page,pages-1))
        chosen=decoded[page*page_size:(page+1)*page_size]
        # R61 recovery readiness: these are the durable state primitives already
        # produced by HEAVY. This is diagnostic only; FAST startup policy is unchanged.
        try: full_snapshot=bool(client.exists('vys262:bot_state:latest_gz'))
        except Exception: full_snapshot=False
        try: deltas=int(client.llen('vys262:bot_state:latest_gz:deltas_v1') or 0)
        except Exception: deltas=0
        try: capsule=bool(client.exists('vys262:durable_capsule:r20'))
        except Exception: capsule=False
        try:
            events=sum(1 for _ in client.scan_iter(match='vys262:tg_events:v1:event:*',count=200))
        except Exception: events=0
        return {
            'ok':True,'role':'fast-direct','source':'FAST direct Redis','ping':'PONG' if pong else 'FAIL',
            'recovery':{'full_snapshot':full_snapshot,'deltas':deltas,'capsule':capsule,'events':events},
            'dbsize':dbsize,'scanned':len(decoded),'truncated':truncated,'page':page,'pages':pages,'page_size':page_size,
            'entries':[_r61_redis_key_row_local(client,raw) for _,raw in chosen],
            'prefixes':[{'prefix':k,'count':v} for k,v in sorted(prefix_counts.items(),key=lambda kv:(-kv[1],kv[0]))[:12]],
            'memory':{'used_memory':int(info_mem.get('used_memory') or 0),'used_memory_human':str(info_mem.get('used_memory_human') or ''),'maxmemory':int(info_mem.get('maxmemory') or 0),'maxmemory_human':str(info_mem.get('maxmemory_human') or '')},
            'stats':{'keyspace_hits':int(info_stats.get('keyspace_hits') or 0),'keyspace_misses':int(info_stats.get('keyspace_misses') or 0),'evicted_keys':int(info_stats.get('evicted_keys') or 0),'expired_keys':int(info_stats.get('expired_keys') or 0),'connected_clients':int(info_clients.get('connected_clients') or 0)},
        }
    finally:
        try:
            if client is not None: client.close()
        except Exception: pass


def _r60_fetch_redis_inspect(page=0):
    # R61: inspect Redis directly from FAST. This removes dependency on a matching
    # HEAVY HTTP route and fixes the R60 404 when HEAVY was still on an older build.
    return _r61_fetch_redis_inspect_direct(page)


def _r60_render_redis_menu(chat_id,message_id,extra=''):
    try:
        fast_ui_edit_message_text(int(chat_id),int(message_id),_r60_redis_menu_text(extra),reply_markup=_r60_redis_menu_keyboard(),purpose='safe_edit:r60_redis_menu')
    except Exception: pass


def _r60_redis_inspect_job(page,chat_id,message_id):
    try:
        payload=_r60_fetch_redis_inspect(page)
        text=_r60_redis_inspect_text(payload)
        kb=_r60_redis_inspect_keyboard(payload.get('page',0),payload.get('pages',1))
    except Exception as exc:
        text=_r60_redis_inspect_text({},f'{type(exc).__name__}: {str(exc)[:520]}')
        kb=_r60_redis_inspect_keyboard(0,1)
    try:
        fast_ui_edit_message_text(int(chat_id),int(message_id),text,reply_markup=kb,purpose='safe_edit:r60_redis_inspect')
    except Exception: pass


def _r49_info_inject_redis_toggle(kb, chat_id: int):
    if int(chat_id) != int(OWNER_ID or 0):
        return kb
    try:
        rows_fn = globals().get('_v177_info_rows')
        set_fn = globals().get('_v177_info_set_rows')
        rows = list(rows_fn(kb) or []) if callable(rows_fn) else list(getattr(kb, 'keyboard', None) or [])
        remove_callbacks={'r49:redis:toggle','r60:redis:menu','r60:redis:inspect:0','r59:vars:render:0','r59:vars:code:0'}
        rows = [list(row or []) for row in rows if not any(_r29_button_callback(b) in remove_callbacks for b in (row or []))]
        insert_at = len(rows)
        for i, row in enumerate(rows):
            if any((_r29_button_callback(b) in {'info_close', 'aux_close', 'nav_prev'} or 'назад' in _r29_button_text(b).casefold()) for b in (row or [])):
                insert_at = i
                break
        rows.insert(insert_at, [IB('🌐 Render ENV', callback_data='r59:vars:render:0'), IB('🧩 Код/runtime', callback_data='r59:vars:code:0')])
        rows.insert(insert_at + 1, [_r49_redis_button(),IB('🧠 Redis: содержимое',callback_data='r60:redis:inspect:0')])
        if callable(set_fn):
            return set_fn(kb, rows)
        setattr(kb, 'keyboard', rows)
    except Exception:
        try:
            kb.row(IB('🌐 Render ENV', callback_data='r59:vars:render:0'), IB('🧩 Код/runtime', callback_data='r59:vars:code:0'))
            kb.row(_r49_redis_button(),IB('🧠 Redis: содержимое',callback_data='r60:redis:inspect:0'))
        except Exception: pass
    return kb


def _r49_render_info_after_redis(chat_id: int, message_id: int):
    _r60_render_redis_menu(chat_id,message_id)

def _r49_apply_redis_runtime_job(enabled: bool, chat_id: int, message_id: int) -> None:
    """R59 transactional Redis switch with real connectivity verification.

    The callback itself never waits for Redis.  This detached job changes HEAVY and
    FAST, refreshes import-time FAST consumers, and verifies PING on both sides.
    """
    enabled = bool(enabled)
    ok = False
    detail = ''
    base = ''
    headers = {}
    try:
        base = globals().get('_split_peer_base', lambda: '')()
        secret = globals().get('_split_secret', lambda: '')()
        if not base or not secret:
            raise RuntimeError('Render #2 peer is not configured')
        headers_fn = globals().get('_split_headers')
        headers = dict(headers_fn('vys-262-r61-render-owned-redis-control') or {}) if callable(headers_fn) else {'X-Peer-Secret': secret}

        # HEAVY first.  Its endpoint now validates its own Render master switch,
        # configured URL and an actual short PING before reporting enabled=True.
        response = __import__('requests').post(
            base.rstrip('/') + '/internal/runtime/redis',
            json={'enabled': enabled}, headers=headers, timeout=(2.0, 5.0))
        try: payload = response.json() if response.content else {}
        except Exception: payload = {}
        peer_state = (payload or {}).get('redis') or {}
        if not (200 <= int(response.status_code) < 300 and bool(payload.get('ok'))):
            peer_error = str((payload or {}).get('error') or peer_state.get('error') or response.text or '')[:260]
            raise RuntimeError(f'HEAVY HTTP {response.status_code}: {peer_error}')
        if bool(peer_state.get('enabled')) != enabled:
            raise RuntimeError(str(peer_state.get('error') or 'HEAVY Redis state did not match request')[:220])

        import runtime_config as _r49_runtime_config
        local_state = _r49_runtime_config.set_redis_runtime_enabled(enabled)
        _r59_refresh_fast_redis_consumers()
        if bool(local_state.get('enabled')) != enabled:
            raise RuntimeError(str(local_state.get('error') or 'FAST Redis state did not match request')[:220])

        if enabled:
            ping_ok, ping_detail = _r59_fast_redis_probe()
            if not ping_ok:
                raise RuntimeError(ping_detail)
            # Also force the native Key Value client to re-read the new runtime URL.
            kv_ping = globals().get('key_value_ping_v248')
            if callable(kv_ping) and not bool(kv_ping(force=True)):
                raise RuntimeError('FAST KeyValue PING failed after runtime refresh')
            detail = 'FAST + HEAVY: Redis CACHE ON; PING=PONG'
        else:
            detail = 'FAST + HEAVY: Redis runtime OFF'
        ok = True
    except Exception as exc:
        detail = f'{type(exc).__name__}: {str(exc)[:280]}'
        # Enabling is transactional.  Any failure rolls both sides back to OFF.
        if enabled:
            try:
                import runtime_config as _r49_runtime_config
                _r49_runtime_config.set_redis_runtime_enabled(False)
                _r59_refresh_fast_redis_consumers()
            except Exception:
                pass
            try:
                if base and headers:
                    __import__('requests').post(base.rstrip('/') + '/internal/runtime/redis',
                                                json={'enabled': False}, headers=headers, timeout=(1.5, 3.0))
            except Exception:
                pass
    finally:
        with _R49_REDIS_CONTROL_LOCK:
            _R49_REDIS_CONTROL.update({'switching': False, 'target': enabled, 'peer_ok': bool(ok), 'detail': detail})
        try: bot_journal('r59_redis_runtime_switch', int(chat_id), f'enabled={int(enabled)}; ok={int(ok)}; {detail}')
        except Exception: pass
        _r49_render_info_after_redis(int(chat_id), int(message_id))

def _r29_build_info_text(chat_id: int, *args, **kwargs) -> str:
    cid = int(chat_id)
    if cid != int(OWNER_ID or 0):
        try:
            return str(_R29_LEGACY_INFO_TEXT(cid, *args, **kwargs)) if callable(_R29_LEGACY_INFO_TEXT) else 'ℹ️ Инфо'
        except Exception:
            return 'ℹ️ Инфо'
    mode = r30_info_menu_mode(cid, False)
    if mode == 'old':
        try:
            return str(_R29_LEGACY_INFO_TEXT(cid, *args, **kwargs)) if callable(_R29_LEGACY_INFO_TEXT) else 'ℹ️ Инфо'
        except Exception:
            return 'ℹ️ Инфо'
    if mode == R31_MENU_MODE_THIRD:
        return _r31_third_info_text(cid)
    return window_mark(
        'ℹ️ ИНФО · R66\n\n'
        'Меню собрано по разделам, чтобы служебные кнопки не занимали несколько экранов.\n'
        'Доступны три режима Info: Новое, Старое и Третий вариант.\n\n'
        '⚡ FAST UI: callback не ждёт Telegram; рендер идёт отдельной latest-wins очередью.\n'
        '🛰 HEAVY: тяжёлая работа после UI.\n'
        '🔒 Директивный режим: бизнес-логика владельца не переключается контуром.',
        'Ф89'
    )


def _r29_build_info_keyboard(chat_id: int):
    cid = int(chat_id)
    if cid != int(OWNER_ID or 0):
        kb = _R29_LEGACY_INFO_KB(cid) if callable(_R29_LEGACY_INFO_KB) else types.InlineKeyboardMarkup()
        try:
            rows_fn = globals().get('_v177_info_rows')
            set_fn = globals().get('_v177_info_set_rows')
            rows = list(rows_fn(kb) or []) if callable(rows_fn) else []
            callbacks = {_r29_button_callback(b) for row in rows for b in (row or [])}
            if 'r29:inputs:open' not in callbacks:
                insert_at = len(rows)
                for i, row in enumerate(rows):
                    if any((_r29_button_callback(b) in {'info_close', 'aux_close'} or 'назад' in _r29_button_text(b).casefold()) for b in (row or [])):
                        insert_at = i
                        break
                rows.insert(insert_at, [IB('📥 Источники сообщений', callback_data='r29:inputs:open')])
                if callable(set_fn):
                    kb = set_fn(kb, rows)
        except Exception:
            pass
        return kb
    mode = r30_info_menu_mode(cid, False)
    if mode == 'old':
        return _r49_info_inject_redis_toggle(_r30_legacy_info_keyboard_with_controls(cid), cid)
    if mode == R31_MENU_MODE_THIRD:
        return _r49_info_inject_redis_toggle(_r31_third_info_keyboard(cid), cid)
    kb = types.InlineKeyboardMarkup(row_width=2)
    kb.row(IB('📊 Состояние', callback_data='r29:info:status'), IB('🔗 Интеграции', callback_data='r29:info:integrations'))
    kb.row(IB('⚙️ Настройки', callback_data='r29:info:settings'), IB('📁 Журналы', callback_data='r29:info:journals'))
    kb.row(IB('📥 Источники сообщений', callback_data='r29:inputs:open'))
    kb.row(IB('🛠 Владельцу', callback_data='r29:info:owner'))
    if not _r31_constructors_enabled():
        kb.row(IB('🧩 Конструкторы', callback_data='r31:constructors:open'))
    kb.row(_r30_menu_mode_button(cid))
    kb.row(IB('🔙 Назад', callback_data='nav_prev'), IB('❌ Закрыть', callback_data='info_close'))
    return _r49_info_inject_redis_toggle(kb, cid)


build_info_text = _r29_build_info_text
build_info_keyboard = _r29_build_info_keyboard

# ---------------------------------------------------------------------------
# Google single-window UX.
# ---------------------------------------------------------------------------

_R29_GOOGLE_BASE_HANDLE = globals().get('tenant_google_handle_message')
_R29_GOOGLE_BASE_KB = globals().get('tenant_google_keyboard')
_R29_GOOGLE_BASE_STATUS = globals().get('tenant_google_status_text')
_R29_GOOGLE_BASE_TEST = globals().get('tenant_google_test')


def _r29_google_keyboard(tenant_id):
    kb = _R29_GOOGLE_BASE_KB(tenant_id) if callable(_R29_GOOGLE_BASE_KB) else types.InlineKeyboardMarkup()
    try:
        rows = list(getattr(kb, 'keyboard', None) or [])
        callbacks = {_r29_button_callback(b) for row in rows for b in (row or [])}
        if 'nav_prev' not in callbacks:
            kb.row(IB('🔙 Назад', callback_data='nav_prev'), IB('❌ Закрыть', callback_data='info_close'))
    except Exception:
        pass
    return kb


def _r29_google_status(tenant_id) -> str:
    try:
        return str(_R29_GOOGLE_BASE_STATUS(tenant_id)) if callable(_R29_GOOGLE_BASE_STATUS) else '📊 Google'
    except Exception as exc:
        return '📊 Google\n\nОшибка локального статуса: ' + str(exc)[:300]


def _r29_google_back_keyboard():
    kb = types.InlineKeyboardMarkup(row_width=1)
    kb.row(IB('🔙 В Google', callback_data='v149:google:status'))
    kb.row(IB('❌ Закрыть', callback_data='info_close'))
    return kb


def _r29_google_edit(chat_id: int, message_id: int, text: str, kb=None, parse_mode=None, purpose='r29_google'):
    return fast_ui_edit_message_text(int(chat_id), int(message_id), str(text)[:4000], reply_markup=kb, parse_mode=parse_mode, purpose=purpose)


def _r29_google_persist_background(tenant_id: str, reason: str):
    tid = str(tenant_id)
    def _job():
        try: tenant_google_persist(tid, reason)
        except Exception: pass
    try:
        pool = globals().get('GENERAL_TASK_POOL')
        if pool is not None:
            submit_unique = getattr(pool, 'submit_unique', None)
            if callable(submit_unique): submit_unique(f'r29-google-persist:{tid}', _job)
            else: pool.submit(f'r29-google-persist:{tid}', _job)
            return
    except Exception:
        pass
    try: threading.Thread(target=_job, daemon=True, name='r29-google-persist').start()
    except Exception: pass


def _r29_google_begin_wait(tid: str, kind: str, cid: int, uid: int, panel_mid: int):
    cfg = tenant_google_config(str(tid))
    sid = f'r29-{int(time.time()*1000)}-{int(uid)}'
    delay = 120.0
    try:
        delay = float(globals().get('_v213_input_timeout_seconds', lambda: 120)())
    except Exception:
        pass
    cfg['input_wait'] = {
        'kind': str(kind), 'chat_id': int(cid), 'user_id': int(uid),
        'expires_at': time.time() + delay, 'session_id': sid,
        'panel_message_id': int(panel_mid), 'r29_single_window': True,
    }
    cfg['updated_at'] = globals().get('_v149_now_iso', lambda: '')()
    _r29_google_persist_background(str(tid), 'r29_google_wait')
    key = f'r29-google-input:{tid}:{cid}:{uid}'
    try: DELAYED_SCHEDULER.cancel(key)
    except Exception: pass
    def _expire():
        try:
            live = (tenant_google_config(str(tid), create=False) or {}).get('input_wait') or {}
            if str(live.get('session_id') or '') != sid:
                return
            tenant_google_config(str(tid))['input_wait'] = {}
            _r29_google_persist_background(str(tid), 'r29_google_wait_expire')
            _r29_google_edit(cid, panel_mid, _r29_google_status(tid) + '\n\n⌛ Ввод отменён по таймеру.', _r29_google_keyboard(tid), purpose='r29_google_wait_expire')
        except Exception:
            pass
    try: DELAYED_SCHEDULER.schedule(key, delay, _expire)
    except Exception: pass
    return sid


def _google_extension_callback(call, data_str: str) -> bool:
    raw = str(data_str or '')
    if not raw.startswith('v149:google:'):
        return False
    try:
        cid = int(call.message.chat.id)
        uid = int(getattr(getattr(call, 'from_user', None), 'id', 0) or 0)
        mid = int(call.message.message_id)
    except Exception:
        return True
    try:
        ok_manage, tid = _v149_google_can_manage(cid, uid, owner_only=True)
    except Exception:
        ok_manage, tid = (uid == int(OWNER_ID or 0), str(globals().get('TENANT_PLATFORM_ID') or 'platform'))
    if not ok_manage:
        try: bot.answer_callback_query(call.id, 'Только владелец пространства', show_alert=True)
        except Exception: pass
        return True
    action = raw.split(':', 2)[2]
    try: bot.answer_callback_query(call.id)
    except Exception: pass

    if action == 'status':
        _r29_google_edit(cid, mid, _r29_google_status(tid), _r29_google_keyboard(tid), purpose='r29_google_status')
        return True
    if action in {'service_email', 'connect'}:
        try:
            info = globals().get('_r7_google_worker_info', lambda fetch=False: {})(fetch=False)
            email = str((info or {}).get('service_email') or '')
        except Exception:
            email = ''
        if email:
            _r29_google_edit(cid, mid, '📧 EMAIL ДЛЯ ДОСТУПА\n\n<code>' + email + '</code>\n\nДобавьте этот email в Google Таблице: Поделиться → Редактор.', _r29_google_back_keyboard(), parse_mode='HTML', purpose='r29_google_email')
            return True
        _r29_google_edit(cid, mid, '⏳ Получаю email service account с Render #2…', _r29_google_back_keyboard(), purpose='r29_google_email_wait')
        def _fetch_email():
            try:
                info2 = globals().get('_r7_google_worker_info', lambda fetch=True: {})(fetch=True)
                email2 = str((info2 or {}).get('service_email') or '')
                text = ('📧 EMAIL ДЛЯ ДОСТУПА\n\n<code>' + email2 + '</code>\n\nДобавьте этот email в Google Таблице: Поделиться → Редактор.') if email2 else '❌ Render #2 не отдал email service account.'
                _r29_google_edit(cid, mid, text, _r29_google_back_keyboard(), parse_mode='HTML' if email2 else None, purpose='r29_google_email_done')
            except Exception as exc:
                _r29_google_edit(cid, mid, '❌ Google: ' + str(exc)[:500], _r29_google_back_keyboard(), purpose='r29_google_email_error')
        try: GENERAL_TASK_POOL.submit_unique(f'r29-google-email:{cid}', _fetch_email)
        except Exception: pass
        return True
    if action in {'sheet', 'folder', 'owner_email'}:
        prompt = {
            'sheet': '2️⃣ Пришлите сюда ссылку на Google Таблицу.\n\nПосле сообщения бот сохранит ссылку и проверит доступ в этом же окне.',
            'folder': '📁 Пришлите ссылку или ID папки Google Drive.',
            'owner_email': '👤 Пришлите email Google-аккаунта владельца пространства.',
        }[action]
        _r29_google_edit(cid, mid, prompt, _r29_google_back_keyboard(), purpose=f'r29_google_wait_{action}')
        _r29_google_begin_wait(str(tid), action, cid, uid, mid)
        return True
    if action in {'history', 'errors'}:
        text = _v149_google_history_text(str(tid), action == 'errors')
        _r29_google_edit(cid, mid, text, _r29_google_back_keyboard(), purpose=f'r29_google_{action}')
        return True
    if action in {'toggle_sheet', 'toggle_drive'}:
        cfg = tenant_google_config(str(tid))
        settings = cfg.setdefault('export_settings', {})
        key = 'sheet_enabled' if action == 'toggle_sheet' else 'drive_enabled'
        settings[key] = not bool(settings.get(key, True))
        cfg['updated_at'] = globals().get('_v149_now_iso', lambda: '')()
        try: tenant_google_history(str(tid), action, f'{key}={settings[key]}', ok=True)
        except Exception: pass
        _r29_google_edit(cid, mid, _r29_google_status(tid), _r29_google_keyboard(tid), purpose='r29_google_toggle')
        _r29_google_persist_background(str(tid), 'tenant_google_settings_r29')
        return True
    if action == 'test':
        _r29_google_edit(cid, mid, '⏳ Проверяю доступ к Google на Render #2…', _r29_google_back_keyboard(), purpose='r29_google_test_start')
        def _test():
            try:
                fn = _R29_GOOGLE_BASE_TEST or globals().get('_r7_google_test')
                ok, text = fn(str(tid)) if callable(fn) else (False, 'Проверка недоступна')
                prefix = '✅ ' if ok else '🟡 '
                _r29_google_edit(cid, mid, prefix + str(text or '') + '\n\n' + _r29_google_status(tid), _r29_google_keyboard(tid), purpose='r29_google_test_done')
            except Exception as exc:
                _r29_google_edit(cid, mid, '❌ Google: ' + str(exc)[:600], _r29_google_keyboard(tid), purpose='r29_google_test_error')
        try: GENERAL_TASK_POOL.submit_unique(f'r29-google-test:{tid}', _test)
        except Exception: pass
        return True
    if action == 'create_sheet':
        _r29_google_edit(cid, mid, '⏳ Создаю Google Таблицу на Render #2…', _r29_google_back_keyboard(), purpose='r29_google_create_start')
        def _create():
            try:
                name = f"Финансы · {(tenant_get(str(tid)) or {}).get('name') or tid}"
                url = tenant_google_create_spreadsheet(str(tid), name)
                _r29_google_edit(cid, mid, '✅ Таблица создана и закреплена за пространством:\n' + str(url) + '\n\n' + _r29_google_status(tid), _r29_google_keyboard(tid), purpose='r29_google_create_done')
            except Exception as exc:
                _r29_google_edit(cid, mid, '❌ Google: ' + str(exc)[:600], _r29_google_keyboard(tid), purpose='r29_google_create_error')
        try: GENERAL_TASK_POOL.submit_unique(f'r29-google-create:{tid}', _create)
        except Exception: pass
        return True
    if action == 'disconnect_confirm':
        kb = types.InlineKeyboardMarkup(row_width=2)
        kb.row(IB('🧹 Да, отключить', callback_data='v149:google:disconnect'), IB('Отмена', callback_data='v149:google:status'))
        _r29_google_edit(cid, mid, 'Отключить Google только у этого пространства? Таблицы и файлы в Google удалены не будут.', kb, purpose='r29_google_disconnect_confirm')
        return True
    if action == 'disconnect':
        cfg = tenant_google_config(str(tid))
        keep_history = list(cfg.get('history') or [])
        keep_errors = list(cfg.get('errors') or [])
        try: (tenant_get(str(tid)) or {}).pop('google_v149', None)
        except Exception: pass
        fresh = tenant_google_config(str(tid))
        fresh['history'] = keep_history
        fresh['errors'] = keep_errors
        try: tenant_google_history(str(tid), 'account_disconnected', 'Google отключён', ok=True)
        except Exception: pass
        _r29_google_edit(cid, mid, '✅ Google этого пространства отключён.\n\n' + _r29_google_status(tid), _r29_google_keyboard(tid), purpose='r29_google_disconnect')
        _r29_google_persist_background(str(tid), 'tenant_google_disconnect_r29')
        return True
    # Unknown Google action is consumed here; there is no predecessor callback chain.
    return True


def _r29_google_handle_message(msg) -> bool:
    try:
        cid = int(msg.chat.id)
        uid = int(getattr(getattr(msg, 'from_user', None), 'id', 0) or 0)
        tid = str(tenant_id_for_chat(cid, create=False) or '')
        cfg = tenant_google_config(tid, create=False) if tid else {}
        wait = dict((cfg or {}).get('input_wait') or {})
        if not wait or not bool(wait.get('r29_single_window')):
            return bool(_R29_GOOGLE_BASE_HANDLE(msg)) if callable(_R29_GOOGLE_BASE_HANDLE) else False
        if int(wait.get('chat_id') or 0) != cid or int(wait.get('user_id') or 0) != uid:
            return False
        panel_mid = int(wait.get('panel_message_id') or 0)
        kind = str(wait.get('kind') or '')
        if str(getattr(msg, 'content_type', '')) != 'text':
            if panel_mid:
                _r29_google_edit(cid, panel_mid, 'Пришлите данные обычным текстом.', _r29_google_back_keyboard(), purpose='r29_google_input_type')
            return True
        value = str(getattr(msg, 'text', '') or '').strip()
        if kind == 'sheet':
            cfg['spreadsheet_id'] = _v149_google_id(value, 'sheet')
            cfg['spreadsheet_title'] = ''
        elif kind == 'folder':
            cfg['drive_folder_id'] = _v149_google_id(value, 'folder')
            cfg['drive_folder_name'] = ''
        elif kind == 'owner_email':
            import re as _r29_re
            if not _r29_re.fullmatch(r'[^@\s]+@[^@\s]+\.[^@\s]+', value):
                raise RuntimeError('Неверный email')
            cfg['owner_google_email'] = value[:250]
        else:
            return False
        cfg['input_wait'] = {}
        cfg['updated_at'] = globals().get('_v149_now_iso', lambda: '')()
        try: DELAYED_SCHEDULER.cancel(f'r29-google-input:{tid}:{cid}:{uid}')
        except Exception: pass
        _r29_google_persist_background(tid, 'tenant_google_update_r29')
        try:
            deleter = globals().get('_v172_delete_quiet')
            if callable(deleter): deleter(cid, int(msg.message_id))
        except Exception: pass
        if kind != 'sheet':
            if panel_mid:
                _r29_google_edit(cid, panel_mid, '✅ Настройка сохранена.\n\n' + _r29_google_status(tid), _r29_google_keyboard(tid), purpose='r29_google_input_saved')
            return True
        if panel_mid:
            _r29_google_edit(cid, panel_mid, '✅ Ссылка сохранена. Проверяю доступ на Render #2…', _r29_google_back_keyboard(), purpose='r29_google_sheet_saved')
        def _test_saved():
            try:
                fn = _R29_GOOGLE_BASE_TEST or globals().get('_r7_google_test')
                ok, text = fn(str(tid)) if callable(fn) else (False, 'Проверка недоступна')
                out = ('✅ Таблица подключена и доступ проверен.\n\n' if ok else '🟡 Ссылка сохранена, но доступа пока нет.\n\n') + str(text or '') + '\n\n' + _r29_google_status(tid)
                if panel_mid:
                    _r29_google_edit(cid, panel_mid, out, _r29_google_keyboard(tid), purpose='r29_google_sheet_test_done')
            except Exception as exc:
                if panel_mid:
                    _r29_google_edit(cid, panel_mid, '❌ Google: ' + str(exc)[:600], _r29_google_keyboard(tid), purpose='r29_google_sheet_test_error')
        try: GENERAL_TASK_POOL.submit_unique(f'r29-google-sheet-test:{tid}', _test_saved)
        except Exception: pass
        return True
    except Exception as exc:
        try:
            cid = int(msg.chat.id)
            tid = str(tenant_id_for_chat(cid, create=False) or '')
            wait = (tenant_google_config(tid, create=False) or {}).get('input_wait') or {}
            panel_mid = int(wait.get('panel_message_id') or 0)
            if panel_mid:
                _r29_google_edit(cid, panel_mid, '❌ Google: ' + str(exc)[:600], _r29_google_back_keyboard(), purpose='r29_google_input_error')
        except Exception:
            pass
        return True


tenant_google_keyboard = _r29_google_keyboard
tenant_google_handle_message = _r29_google_handle_message

# ---------------------------------------------------------------------------
# Final callback guard wrapper.  It is local and synchronous only for the first
# visual response; persistence/network work is explicitly backgrounded.
# ---------------------------------------------------------------------------

_R29_PREV_CONTOUR_GUARD = globals().get('contour_callback_guard')


def _r29_contour_callback_guard(call, resolved: str) -> bool:
    raw = str(resolved or '')
    try:
        cid = int(call.message.chat.id)
        uid = int(getattr(getattr(call, 'from_user', None), 'id', 0) or 0)
        mid = int(call.message.message_id)
    except Exception:
        return bool(_R29_PREV_CONTOUR_GUARD(call, raw)) if callable(_R29_PREV_CONTOUR_GUARD) else False

    if raw.startswith('r59:vars:'):
        if cid != int(OWNER_ID or 0) or uid != int(OWNER_ID or 0):
            try: bot.answer_callback_query(call.id, 'Только владелец может смотреть runtime-переменные.', show_alert=True)
            except Exception: pass
            return True
        parts=raw.split(':')
        kind=parts[2] if len(parts)>2 and parts[2] in {'render','code'} else 'render'
        try: page=int(parts[3]) if len(parts)>3 else 0
        except Exception: page=0
        text,kb=_r59_vars_keyboard(kind,page)
        try: bot.answer_callback_query(call.id)
        except Exception: pass
        safe_edit(bot, call, text, reply_markup=kb)
        return True

    if raw.startswith('r60:redis:'):
        if cid != int(OWNER_ID or 0) or uid != int(OWNER_ID or 0):
            try: bot.answer_callback_query(call.id, 'Только владелец может управлять Redis.', show_alert=True)
            except Exception: pass
            return True

        if raw == 'r60:redis:menu':
            try: bot.answer_callback_query(call.id)
            except Exception: pass
            safe_edit(bot, call, _r60_redis_menu_text(), reply_markup=_r60_redis_menu_keyboard())
            return True

        if raw.startswith('r60:redis:inspect:'):
            try: page=max(0,int(raw.rsplit(':',1)[-1] or 0))
            except Exception: page=0
            state=_r49_redis_runtime_state()
            if not state.get('master_enabled'):
                try: bot.answer_callback_query(call.id,'REDIS_ENABLED=0 в Render.',show_alert=True)
                except Exception: pass
                safe_edit(bot,call,_r60_redis_menu_text('Redis заблокирован переменной Render.'),reply_markup=_r60_redis_menu_keyboard())
                return True
            if not state.get('enabled'):
                try: bot.answer_callback_query(call.id,'Redis сейчас выключен. Включите его на странице режима.',show_alert=True)
                except Exception: pass
                safe_edit(bot,call,_r60_redis_menu_text('Для просмотра содержимого включите Redis.'),reply_markup=_r60_redis_menu_keyboard())
                return True
            try: bot.answer_callback_query(call.id,'Читаю Redis…')
            except Exception: pass
            safe_edit(bot,call,window_mark('🧠 REDIS · СОДЕРЖИМОЕ\n\n⏳ Читаю ключи и статистику…','Ф89'),reply_markup=_r60_redis_inspect_keyboard(page,1))
            pool=globals().get('GENERAL_TASK_POOL')
            queued=bool(pool and pool.submit_unique(f'r60-redis-inspect:{cid}:{mid}',_r60_redis_inspect_job,page,cid,mid))
            if not queued:
                safe_edit(bot,call,_r60_redis_inspect_text({},'Очередь диагностики занята. Повторите через несколько секунд.'),reply_markup=_r60_redis_inspect_keyboard(page,1))
            return True

        if raw in {'r60:redis:on','r60:redis:off'}:
            target=(raw=='r60:redis:on')
            state=_r49_redis_runtime_state()
            if state.get('switching'):
                try: bot.answer_callback_query(call.id,'Переключение Redis уже выполняется.')
                except Exception: pass
                return True
            if target and not bool(state.get('master_enabled')):
                try: bot.answer_callback_query(call.id,'REDIS_ENABLED=0 в Render. Это жёсткий OFF.',show_alert=True)
                except Exception: pass
                return True
            if target and not bool(state.get('configured')):
                try: bot.answer_callback_query(call.id,'REDIS_URL не настроен в Render.',show_alert=True)
                except Exception: pass
                return True
            if bool(state.get('enabled')) == target:
                try: bot.answer_callback_query(call.id,'Redis уже '+('включён.' if target else 'выключен.'))
                except Exception: pass
                safe_edit(bot,call,_r60_redis_menu_text(),reply_markup=_r60_redis_menu_keyboard())
                return True

            # OFF is fail-safe and immediate on FAST. ON is committed only after
            # HEAVY and FAST both pass a real PING in the detached control job.
            if not target:
                try:
                    import runtime_config as _r49_runtime_config
                    _r49_runtime_config.set_redis_runtime_enabled(False)
                    _r59_refresh_fast_redis_consumers()
                except Exception: pass
            with _R49_REDIS_CONTROL_LOCK:
                _R49_REDIS_CONTROL.update({'switching':True,'target':target,'peer_ok':None,'detail':''})
            try: bot.answer_callback_query(call.id,'Redis: '+('включаю…' if target else 'выключаю…'))
            except Exception: pass
            safe_edit(bot,call,_r60_redis_menu_text(),reply_markup=_r60_redis_menu_keyboard())
            pool=globals().get('GENERAL_TASK_POOL')
            queued=bool(pool and pool.submit_unique('r60-redis-runtime-control',_r49_apply_redis_runtime_job,target,cid,mid))
            if not queued:
                with _R49_REDIS_CONTROL_LOCK:
                    _R49_REDIS_CONTROL.update({'switching':False,'peer_ok':False,'detail':'control queue busy'})
                safe_edit(bot,call,_r60_redis_menu_text('Очередь управления занята.'),reply_markup=_r60_redis_menu_keyboard())
            return True


    if raw == 'r30:menu:toggle':
        # Presentation-only owner setting.  It is intentionally handled before
        # directive business-mutation gating and never waits for persistence.
        if cid != int(OWNER_ID or 0) or uid != int(OWNER_ID or 0):
            try: bot.answer_callback_query(call.id, 'Только владелец может менять режим Info-меню.', show_alert=True)
            except Exception: pass
            return True
        current = r30_info_menu_mode(cid, True)
        next_mode = {'new': 'old', 'old': R31_MENU_MODE_THIRD, R31_MENU_MODE_THIRD: 'new'}.get(current, 'new')
        r30_set_info_menu_mode(cid, next_mode)
        mode_label = {'new': 'Новое', 'old': 'Старое', R31_MENU_MODE_THIRD: 'Третий вариант'}.get(next_mode, 'Новое')
        try: bot.answer_callback_query(call.id, 'Меню: ' + mode_label)
        except Exception: pass
        # Direct R28/R29 render first. Persistence runs only after the window changed.
        safe_edit(bot, call, _r29_build_info_text(cid), reply_markup=_r29_build_info_keyboard(cid))
        _r29_persist_chat_settings_background(cid, 'r31_info_menu_mode')
        try: bot_journal('r31_info_menu_mode', cid, f'mode={next_mode}; user={uid}')
        except Exception: pass
        return True

    if raw.startswith('r31:info:'):
        if cid != int(OWNER_ID or 0) or uid != int(OWNER_ID or 0):
            return True
        group = raw.split(':', 2)[2]
        try: bot.answer_callback_query(call.id)
        except Exception: pass
        if group == 'main':
            safe_edit(bot, call, _r31_third_info_text(cid), reply_markup=_r31_third_info_keyboard(cid))
        elif group in {'finance', 'forward', 'reminders', 'tasks', 'contours', 'general', 'journals', 'owner'}:
            safe_edit(bot, call, _r31_third_group_text(group), reply_markup=_r31_third_group_keyboard(cid, group))
        return True

    if raw == 'r31:toggle:tz_markers':
        if cid != int(OWNER_ID or 0) or uid != int(OWNER_ID or 0):
            return True
        state = _r31_tz_markers_state()
        value = False if state == 'on' else True
        try:
            row = _v219_annotation_settings()
            row['tz'] = bool(value)
            row['iz_mr'] = bool(value)
        except Exception:
            pass
        try: bot.answer_callback_query(call.id, 'ТЗ окон и маркеры: ' + ('ВКЛ' if value else 'ВЫКЛ'))
        except Exception: pass
        # Visual response first.  Persistence and mass markup refresh follow after it.
        safe_edit(bot, call, _r31_third_info_text(cid), reply_markup=_r31_third_info_keyboard(cid))
        _r31_persist_global_background('tz_markers_master')
        try: v226_schedule_annotation_markup_refresh_all()
        except Exception: pass
        return True

    if raw == 'r31:toggle:constructors':
        if cid != int(OWNER_ID or 0) or uid != int(OWNER_ID or 0):
            return True
        value = not _r31_constructors_enabled()
        try: _v196_flags()['enabled'] = bool(value)
        except Exception: pass
        try: bot.answer_callback_query(call.id, 'Конструкторы: ' + ('ВКЛ' if value else 'ВЫКЛ'))
        except Exception: pass
        # Keep the dedicated Constructors entry visible regardless of this value.
        if r30_info_menu_mode(cid, False) == R31_MENU_MODE_THIRD:
            safe_edit(bot, call, _r31_third_info_text(cid), reply_markup=_r31_third_info_keyboard(cid))
        else:
            safe_edit(bot, call, _r31_constructors_text(), reply_markup=_r31_constructors_keyboard())
        _r31_persist_global_background('constructors_master')
        _r31_schedule_constructor_markup_refresh()
        return True

    if raw == 'r31:constructors:open':
        if cid != int(OWNER_ID or 0) or uid != int(OWNER_ID or 0):
            return True
        try: bot.answer_callback_query(call.id)
        except Exception: pass
        safe_edit(bot, call, _r31_constructors_text(), reply_markup=_r31_constructors_keyboard())
        return True

    if raw == 'r31:constructors:launch_c2':
        if cid != int(OWNER_ID or 0) or uid != int(OWNER_ID or 0):
            return True
        # Reuse the current panel message: no extra auxiliary Telegram window.
        try:
            fn = globals().get('_v196_open_c2')
            if callable(fn):
                fn(call, '', panel_message_id=mid)
                return True
        except Exception as exc:
            try: bot_journal('r31_constructor_launch_error', cid, str(exc)[:300], 'WARN')
            except Exception: pass
        try: bot.answer_callback_query(call.id, 'Не удалось открыть Конструктор 2', show_alert=True)
        except Exception: pass
        return True

    if raw.startswith('r29:inputs:'):
        if not _r29_inputs_can_manage(cid, uid):
            try: bot.answer_callback_query(call.id, 'Недостаточно прав для настройки этого контура.', show_alert=True)
            except Exception: pass
            return True
        parts = raw.split(':')
        action = parts[2] if len(parts) > 2 else 'open'
        if action == 'toggle' and len(parts) > 3 and parts[3] in R29_INPUT_DEFAULTS:
            key = parts[3]
            row = r29_input_source_settings(cid, True)
            row[key] = not bool(row.get(key, True))
            try: bot.answer_callback_query(call.id, 'Сохранено')
            except Exception: pass
            # Visual response first; persistence only after it.
            safe_edit(bot, call, _r29_inputs_text(cid), reply_markup=_r29_inputs_keyboard(cid))
            _r29_persist_chat_settings_background(cid, 'input_sources')
            return True
        try: bot.answer_callback_query(call.id)
        except Exception: pass
        safe_edit(bot, call, _r29_inputs_text(cid), reply_markup=_r29_inputs_keyboard(cid))
        return True

    if raw.startswith('r29:info:'):
        if cid != int(OWNER_ID or 0) or uid != int(OWNER_ID or 0):
            return True
        group = raw.split(':', 2)[2]
        try: bot.answer_callback_query(call.id)
        except Exception: pass
        if group == 'main':
            safe_edit(bot, call, _r29_build_info_text(cid), reply_markup=_r29_build_info_keyboard(cid))
        elif group in {'status', 'integrations', 'settings', 'journals', 'owner'}:
            safe_edit(bot, call, _r29_info_group_text(group), reply_markup=_r29_info_group_keyboard(cid, group))
        return True

    if raw == 'r29:directive:contact_owner':
        try: bot.answer_callback_query(call.id)
        except Exception: pass
        try:
            start_owner_message_input_v221(cid, uid, mid)
        except Exception:
            try: send_and_auto_delete(cid, 'Не удалось открыть ввод. Напишите основному владельцу напрямую.', 10)
            except Exception: pass
        return True

    # Directive-mode lock applies to contour users.  The primary owner keeps the
    # admin path in the owner-private directive panel, not through contour buttons.
    if bool(globals().get('directive_chat_enabled_v223', lambda _c: False)(cid)) and _r29_is_business_mutation_callback(raw):
        try: bot.answer_callback_query(call.id, '🔒 Бизнес-логика зафиксирована владельцем.', show_alert=False)
        except Exception: pass
        try:
            safe_edit(bot, call, _r29_directive_block_text(cid), reply_markup=_r29_directive_block_keyboard())
        except Exception:
            pass
        try:
            bot_journal('directive_business_mutation_block_r29', cid, f'action={raw}; user={uid}')
        except Exception:
            pass
        return True

    return bool(_R29_PREV_CONTOUR_GUARD(call, raw)) if callable(_R29_PREV_CONTOUR_GUARD) else False


contour_callback_guard = _r29_contour_callback_guard

# Marker declarations for the new local windows.
try:
    WINDOW_MARKER_CONSTANTS.setdefault('r29:inputs:*', 'Ф3237')
    WINDOW_MARKER_CONSTANTS.setdefault('r29:info:*', 'Ф89')
    WINDOW_MARKER_CONSTANTS.setdefault('r29:directive:*', 'Ф3237')
    WINDOW_MARKER_CONSTANTS.setdefault('r30:menu:*', 'Ф89')
    WINDOW_MARKER_CONSTANTS.setdefault('r31:info:*', 'Ф89')
    WINDOW_MARKER_CONSTANTS.setdefault('r31:toggle:*', 'Ф89')
    WINDOW_MARKER_CONSTANTS.setdefault('r31:constructors:*', 'Ф89')
    WINDOW_MARKER_CONSTANTS.setdefault('r59:vars:*', 'Ф89')
except Exception:
    pass

try:
    bot_journal('r31_policy_ui_ready', int(OWNER_ID or 0),
                'r28_direct_render_protected=1; directive_business_lock=1; google_single_window=1; info_menu_new_old_third=1; third_groups=finance+forward+reminders+tasks+contours+general+journals+owner; master_tz_markers=1; master_constructors=1; input_sources=forwarded+other_bots')
except Exception:
    pass

# --- ИСТОЧНИК: 96_r32_event_stream.py ---
"""R32 logical state event stream.

FAST hot-path rule is preserved: SQLite mutations only enqueue tiny descriptors.
Serialization and SQLite reads for remote state events happen later on a separate
connection/background thread.  HEAVY receives only changed logical rows, rebuilds
its restore DB, and archives immutable event segments.
"""
import gzip as _r32_gzip
import hashlib as _r32_hashlib
import json as _r32_json
import os as _r32_os
import queue as _r32_queue
import secrets as _r32_secrets
import sqlite3 as _r32_sqlite3
import threading as _r32_threading
try:
    import redis as _r43_redis
except Exception:
    _r43_redis = None
import time as _r32_time

_R32_EVENT_STREAM_ENABLED = str(_r32_os.getenv('R32_EVENT_STREAM_ENABLED','1') or '1').strip().lower() in {'1','true','yes','on','да'}
_R32_EVENT_Q = _r32_queue.Queue(maxsize=max(1000,min(50000,int(_r32_os.getenv('R32_EVENT_QUEUE_MAX','20000') or '20000'))))
_R32_EVENT_STATE={'queued':0,'sent':0,'batches':0,'bytes':0,'last_ok':0.0,'last_error':'','dropped':0,'full_runtime_uploads_blocked':0,'private_peer':False,'inflight':0}
_R32_SQLITE_PATCHED=False

# R40/R45-FIX2: durable FAST state-event outbox.
# IMPORTANT: the Telegram/finance hot path must never wait on this database.
# Descriptors are queued in RAM first; the dedicated sender thread persists them
# here before remote delivery.  The primary FAST SQLite remains authoritative.
_R40_EVENT_DB = _r32_os.path.join(str(_r32_os.getenv('R40_EVENT_OUTBOX_DIR','/tmp') or '/tmp'), 'per_r40_state_event_outbox.sqlite3')
_R40_EVENT_DB_READY=False
_R40_EVENT_DB_INIT_LOCK=_r32_threading.Lock()
try:
    _R40_EVENT_DB_BUSY_MS=max(25,min(500,int(_r32_os.getenv('R40_EVENT_DB_BUSY_MS','120') or '120')))
except Exception:
    _R40_EVENT_DB_BUSY_MS=120


def _r40_event_db_connect(timeout_ms=None):
    ms=int(timeout_ms or _R40_EVENT_DB_BUSY_MS)
    con=_r32_sqlite3.connect(_R40_EVENT_DB,timeout=max(0.025,ms/1000.0),check_same_thread=False)
    con.execute(f'PRAGMA busy_timeout={max(1,ms)}')
    return con


def _r40_event_db_init():
    global _R40_EVENT_DB_READY
    if _R40_EVENT_DB_READY:
        return True
    acquired=False
    try:
        # Never allow schema initialization to become another unbounded global lock.
        acquired=_R40_EVENT_DB_INIT_LOCK.acquire(timeout=max(0.05,_R40_EVENT_DB_BUSY_MS/1000.0))
        if not acquired:
            _R32_EVENT_STATE['outbox_init_busy']=int(_R32_EVENT_STATE.get('outbox_init_busy') or 0)+1
            return False
        if _R40_EVENT_DB_READY:
            return True
        _r32_os.makedirs(_r32_os.path.dirname(_R40_EVENT_DB) or '.', exist_ok=True)
        con=_r40_event_db_connect(max(100,_R40_EVENT_DB_BUSY_MS))
        try:
            con.execute('PRAGMA journal_mode=WAL')
            con.execute('PRAGMA synchronous=FULL')
            con.execute('CREATE TABLE IF NOT EXISTS pending(event_id TEXT PRIMARY KEY,revision INTEGER NOT NULL,row_json TEXT NOT NULL,created_at REAL NOT NULL,updated_at REAL NOT NULL)')
            con.execute('CREATE INDEX IF NOT EXISTS idx_r40_event_revision ON pending(revision,event_id)')
            con.commit()
            _R40_EVENT_DB_READY=True
        finally:
            con.close()
        return True
    except Exception as exc:
        _R32_EVENT_STATE['last_error']=f'R45 event outbox init {type(exc).__name__}: {str(exc)[:160]}'
        return False
    finally:
        if acquired:
            try: _R40_EVENT_DB_INIT_LOCK.release()
            except Exception: pass


def _r40_event_db_put(desc):
    return _r40_event_db_put_many([desc])


def _r40_event_db_put_many(rows):
    good=[x for x in (rows or []) if isinstance(x,dict) and str(x.get('event_id') or '')]
    if not good:
        return True
    try:
        if not _r40_event_db_init():
            return False
        now=_r32_time.time(); payload=[]
        for desc in good:
            raw=_r32_json.dumps(desc,ensure_ascii=False,separators=(',',':'),default=str)
            payload.append((str(desc.get('event_id')),int(desc.get('revision') or 0),raw,float(desc.get('created_at') or now),now))
        con=_r40_event_db_connect()
        try:
            con.executemany('INSERT INTO pending(event_id,revision,row_json,created_at,updated_at) VALUES(?,?,?,?,?) ON CONFLICT(event_id) DO UPDATE SET revision=excluded.revision,row_json=excluded.row_json,updated_at=excluded.updated_at',payload)
            con.commit()
        finally:
            con.close()
        _R32_EVENT_STATE['outbox_persisted']=int(_R32_EVENT_STATE.get('outbox_persisted') or 0)+len(good)
        return True
    except Exception as exc:
        _R32_EVENT_STATE['last_error']=f'R45 event outbox put {type(exc).__name__}: {str(exc)[:160]}'
        _R32_EVENT_STATE['outbox_put_fail']=int(_R32_EVENT_STATE.get('outbox_put_fail') or 0)+len(good)
        return False


def _r40_event_db_delete(rows):
    ids=[(str(row.get('event_id')), ) for row in (rows or []) if isinstance(row,dict) and str(row.get('event_id') or '')]
    if not ids:
        return True
    try:
        if not _r40_event_db_init():
            return False
        con=_r40_event_db_connect()
        try:
            con.executemany('DELETE FROM pending WHERE event_id=?',ids); con.commit()
        finally:
            con.close()
        return True
    except Exception as exc:
        _R32_EVENT_STATE['last_error']=f'R45 event outbox delete {type(exc).__name__}: {str(exc)[:160]}'
        return False


def _r40_event_db_pending(limit=128):
    out=[]
    try:
        if not _r40_event_db_init(): return out
        con=_r40_event_db_connect()
        try:
            rows=con.execute('SELECT row_json FROM pending ORDER BY revision,event_id LIMIT ?',(max(1,min(1000,int(limit or 128))),)).fetchall()
        finally:
            con.close()
        for row in rows:
            try:
                obj=_r32_json.loads(row[0])
                if isinstance(obj,dict): out.append(obj)
            except Exception: pass
    except Exception as exc:
        _R32_EVENT_STATE['last_error']=f'R45 event outbox pending {type(exc).__name__}: {str(exc)[:160]}'
    return out


def _r40_event_db_count():
    try:
        if not _r40_event_db_init(): return int(_R32_EVENT_STATE.get('durable_pending') or 0)
        con=_r40_event_db_connect()
        try:
            value=int(con.execute('SELECT COUNT(*) FROM pending').fetchone()[0] or 0)
        finally:
            con.close()
        _R32_EVENT_STATE['durable_pending']=value
        return value
    except Exception:
        # Status/diagnostics must also remain non-blocking and may use the cached value.
        return int(_R32_EVENT_STATE.get('durable_pending') or 0)

def _r32_ready():
    try:
        fn=globals().get('runtime_is_ready')
        return bool(fn()) if callable(fn) else False
    except Exception: return False


def _r32_peer_base_impl():
    raw=str(_r32_os.getenv('PEER_PRIVATE_URL','') or '').strip().rstrip('/')
    private=bool(raw)
    if not raw: raw=str(_r32_os.getenv('PEER_SERVICE_URL','') or '').strip().rstrip('/')
    if raw and not raw.startswith(('http://','https://')):
        looks_private=private or raw.endswith('.internal') or '.internal:' in raw or (raw.startswith('render-') and ':' in raw)
        raw=('http://' if looks_private else 'https://')+raw
    _R32_EVENT_STATE['private_peer']=bool(private or (raw.startswith('http://') if raw else False))
    return raw

if callable(globals().get('_split_peer_base')):
    _R32_LEGACY_SPLIT_PEER_BASE=globals().get('_split_peer_base')
    def _split_peer_base():
        return _r32_peer_base_impl() or _R32_LEGACY_SPLIT_PEER_BASE()


def _r32_descriptor(kind,key,ids=None):
    return {'kind':str(kind or '')[:60],'key':str(key or '')[:220],'ids':ids or {},'revision':int(_r32_time.time_ns()),'created_at':_r32_time.time(),'event_id':f'r32_{_r32_time.time_ns()}_{_r32_secrets.token_hex(5)}'}


def _r32_enqueue_descriptor(kind,key,ids=None):
    """Capture a tiny logical descriptor without any filesystem/SQLite wait.

    R45-FIX2: this function is called from patched SQLite mutations inside Telegram
    callbacks.  It must remain O(1) and network/disk/lock free.  The sender thread
    persists descriptors to the durable outbox before sending them onward.
    """
    if not _R32_EVENT_STREAM_ENABLED or not _r32_ready(): return False
    try:
        desc=_r32_descriptor(kind,key,ids)
        _R32_EVENT_Q.put_nowait(desc)
        _R32_EVENT_STATE['queued']=int(_R32_EVENT_STATE.get('queued') or 0)+1
        _R32_EVENT_STATE['last_revision_queued']=max(int(_R32_EVENT_STATE.get('last_revision_queued') or 0),int(desc.get('revision') or 0))
        _R32_EVENT_STATE['last_enqueue_durable']=False
        st=globals().get('_SPLIT_STATE')
        if isinstance(st,dict):
            st['r32_event_queued']=int(st.get('r32_event_queued') or 0)+1
            st['r32_event_pending']=max(_R32_EVENT_Q.qsize(),int(_R32_EVENT_STATE.get('durable_pending') or 0))
            st['r40_event_durable_pending']=int(_R32_EVENT_STATE.get('durable_pending') or 0)
        return True
    except _r32_queue.Full:
        _R32_EVENT_STATE['dropped']=int(_R32_EVENT_STATE.get('dropped') or 0)+1
        try: log_error('R45 state-event RAM queue full; primary FAST SQLite remains authoritative')
        except Exception: pass
        return False
    except Exception as exc:
        _R32_EVENT_STATE['last_error']=f'{type(exc).__name__}: {str(exc)[:180]}'; return False


def _r32_db_path():
    try:
        obj=globals().get('SQLITE')
        if obj is not None and getattr(obj,'path',None): return str(obj.path)
    except Exception: pass
    return str(_r32_os.getenv('DB_FILE','bot_state.sqlite3') or 'bot_state.sqlite3')


def _r32_decode(raw,default=None):
    try: return _r32_json.loads(raw) if raw is not None else default
    except Exception: return default


def _r32_materialize(desc):
    """Read the committed value on a separate SQLite connection, never SQLITE.lock."""
    kind=str(desc.get('kind') or ''); ids=desc.get('ids') or {}; payload={}
    if kind in {'delete_chat','delete_cold'}:
        payload=dict(ids)
    else:
        con=_r32_sqlite3.connect(_r32_db_path(),timeout=5)
        try:
            if kind=='set_kv':
                k=str(ids.get('k') or ''); row=con.execute('SELECT v FROM kv WHERE k=?',(k,)).fetchone()
                if row is None: return None
                payload={'k':k,'v':_r32_decode(row[0])}
            elif kind=='save_chat':
                cid=str(ids.get('chat_id') or ''); row=con.execute('SELECT v FROM chats WHERE chat_id=?',(cid,)).fetchone()
                if row is None: return _r32_make_event(desc,{'chat_id':cid},kind_override='delete_chat')
                payload={'chat_id':cid,'v':_r32_decode(row[0],{})}
            elif kind=='prune_chats':
                payload={'keep':[str(r[0]) for r in con.execute('SELECT chat_id FROM chats').fetchall()]}
            elif kind=='set_meta':
                mk=str(ids.get('kind') or ''); kk=str(ids.get('k') or ''); row=con.execute('SELECT v FROM meta WHERE kind=? AND k=?',(mk,kk)).fetchone()
                if row is None: return None
                payload={'kind':mk,'k':kk,'v':_r32_decode(row[0])}
            elif kind=='set_cold':
                cid=str(ids.get('chat_id') or ''); kk=str(ids.get('k') or ''); row=con.execute('SELECT v FROM cold_fields WHERE chat_id=? AND k=?',(cid,kk)).fetchone()
                if row is None: return _r32_make_event(desc,{'chat_id':cid,'k':kk},kind_override='delete_cold')
                payload={'chat_id':cid,'k':kk,'v':_r32_decode(row[0])}
            elif kind=='set_cold_many':
                cid=str(ids.get('chat_id') or ''); keys=[str(x) for x in (ids.get('keys') or [])]; items={}
                for kk in keys:
                    row=con.execute('SELECT v FROM cold_fields WHERE chat_id=? AND k=?',(cid,kk)).fetchone()
                    if row is not None: items[kk]=_r32_decode(row[0])
                payload={'chat_id':cid,'items':items}
            else: return None
        finally: con.close()
    return _r32_make_event(desc,payload)


def _r32_make_event(desc,payload,kind_override=None):
    body={'schema':32,'event_id':str(desc.get('event_id') or ''),'revision':int(desc.get('revision') or 0),'created_at':float(desc.get('created_at') or _r32_time.time()),'kind':str(kind_override or desc.get('kind') or '')[:60],'key':str(desc.get('key') or '')[:220],'payload':payload,'front_version':str(globals().get('VERSION') or 'Пер-R43')}
    raw=_r32_json.dumps(body,ensure_ascii=False,separators=(',',':'),default=str).encode('utf-8'); body['sha256']=_r32_hashlib.sha256(raw).hexdigest(); return body


def _r34_encode_events(events):
    obj={'schema':32,'sent_at':_r32_time.time(),'events':list(events or [])}
    return _r32_gzip.compress(_r32_json.dumps(obj,ensure_ascii=False,separators=(',',':'),default=str).encode('utf-8'),compresslevel=1)


def _r34_partition_events(events):
    """Freeze materialized events once, then split only the serialized event list.

    Target is deliberately well below the HEAVY hard limit.  A large single logical
    row is sent alone and may use the dedicated large-event endpoint.
    """
    target=max(64,min(2048,int(_r32_os.getenv('R34_EVENT_TARGET_WIRE_KB','384') or '384')))*1024
    packets=[]; cur=[]
    for ev in list(events or []):
        trial=cur+[ev]; wire=_r34_encode_events(trial)
        if cur and len(wire)>target:
            packets.append({'events':cur,'wire':_r34_encode_events(cur)})
            cur=[ev]
        else:
            cur=trial
    if cur: packets.append({'events':cur,'wire':_r34_encode_events(cur)})
    return packets


def _r32_build_packet(rows):
    """R34: materialize SQLite once, then create size-bounded immutable packets."""
    events=[]; latest={}
    for d in rows: latest[str(d.get('key') or d.get('event_id'))]=d
    for d in sorted(latest.values(),key=lambda x:int(x.get('revision') or 0)):
        ev=_r32_materialize(d)
        if ev: events.append(ev)
    return {'rows':rows,'events':events,'packets':_r34_partition_events(events)}


_R43_EVENT_STREAM_KEY='per:r43:front:state_events'

def _r43_event_redis_client():
    if _r43_redis is None: return None
    url=_r61_effective_redis_url()
    if not url: return None
    try:
        return _r43_redis.Redis.from_url(url,socket_connect_timeout=0.6,socket_timeout=1.5,health_check_interval=30)
    except Exception:
        return None

def _r43_store_events_redis(events):
    c=_r43_event_redis_client()
    if c is None: return False,'Redis unavailable'
    try:
        pipe=c.pipeline(transaction=False)
        for ev in events or []:
            raw=_r32_json.dumps(ev,ensure_ascii=False,separators=(',',':'),default=str)
            pipe.xadd(_R43_EVENT_STREAM_KEY,{'e':raw},maxlen=50000,approximate=True)
        pipe.expire(_R43_EVENT_STREAM_KEY,7*24*3600)
        pipe.execute()
        return True,f'redis-stream events={len(events or [])}'
    except Exception as exc:
        return False,f'{type(exc).__name__}: {str(exc)[:180]}'

def _r34_post_events(events, wire, large=False):
    # R43: Redis on FAST is the durable event authority. HEAVY is only a best-effort
    # warm mirror and must never stall finance/user mutations.
    if str(_r32_os.getenv('R43_FAST_AUTHORITY','1') or '1').strip().lower() in {'1','true','yes','on'}:
        rok,rdetail=_r43_store_events_redis(events)
        if not rok:
            raise RuntimeError('R43 durable event stream unavailable: '+str(rdetail)[:180])
        max_rev=max([int(x.get('revision') or 0) for x in events] or [0])
        base=_r32_peer_base_impl(); secret=str(_r32_os.getenv('PEER_SHARED_SECRET','') or '').strip()
        if base and secret:
            try:
                endpoint='/internal/state/event-large' if large else '/internal/state/events'
                requests.post(base+endpoint,data=wire,headers={'X-Peer-Secret':secret,'User-Agent':'per-r43-state-mirror','Content-Type':'application/json','Content-Encoding':'gzip'},timeout=1.5)
            except Exception:
                pass
        _R32_EVENT_STATE['last_revision_acked']=max(int(_R32_EVENT_STATE.get('last_revision_acked') or 0),max_rev)
        _R32_EVENT_STATE['last_revision_applied_peer']=max(int(_R32_EVENT_STATE.get('last_revision_applied_peer') or 0),max_rev)
        _R32_EVENT_STATE['sent']=int(_R32_EVENT_STATE.get('sent') or 0)+len(events)
        _R32_EVENT_STATE['batches']=int(_R32_EVENT_STATE.get('batches') or 0)+1
        _R32_EVENT_STATE['bytes']=int(_R32_EVENT_STATE.get('bytes') or 0)+len(wire)
        _R32_EVENT_STATE['last_ok']=_r32_time.time(); _R32_EVENT_STATE['last_error']=''
        st=globals().get('_SPLIT_STATE')
        if isinstance(st,dict):
            st['r32_event_sent']=int(st.get('r32_event_sent') or 0)+len(events); st['r32_event_batches']=int(st.get('r32_event_batches') or 0)+1; st['r32_event_last_ok']=_r32_time.time(); st['r32_event_last_error']=''; st['r34_event_last_revision_acked']=max_rev; st['r35_event_last_revision_applied_peer']=max_rev
        return True
    base=_r32_peer_base_impl(); secret=str(_r32_os.getenv('PEER_SHARED_SECRET','') or '').strip()
    if not base or not secret: raise RuntimeError('R34 peer URL/secret not configured')
    endpoint='/internal/state/event-large' if large else '/internal/state/events'
    r=requests.post(base+endpoint,data=wire,headers={'X-Peer-Secret':secret,'User-Agent':'per-r34-state-events','Content-Type':'application/json','Content-Encoding':'gzip'},timeout=max(2.0,min(120.0,float(_r32_os.getenv('R32_EVENT_POST_TIMEOUT_SEC','90') or '90'))))
    if r.status_code==413 and not large:
        if len(events)>1:
            mid=max(1,len(events)//2)
            _r34_post_events(events[:mid],_r34_encode_events(events[:mid]),False)
            _r34_post_events(events[mid:],_r34_encode_events(events[mid:]),False)
            return True
        return _r34_post_events(events,wire,True)
    if not (200 <= r.status_code < 300): raise RuntimeError(f'HEAVY state events HTTP {r.status_code}: {r.text[:220]}')
    try:
        payload=r.json() if r.content else {}
        ack=int(payload.get('durable_revision') or payload.get('max_revision') or max([int(x.get('revision') or 0) for x in events] or [0]))
        applied_ack=int(payload.get('applied_revision') or (ack if bool(payload.get('apply_ok',True)) else 0))
    except Exception:
        ack=max([int(x.get('revision') or 0) for x in events] or [0]); applied_ack=0
    _R32_EVENT_STATE['last_revision_acked']=max(int(_R32_EVENT_STATE.get('last_revision_acked') or 0),ack)
    _R32_EVENT_STATE['last_revision_applied_peer']=max(int(_R32_EVENT_STATE.get('last_revision_applied_peer') or 0),applied_ack)
    _R32_EVENT_STATE['sent']=int(_R32_EVENT_STATE.get('sent') or 0)+len(events)
    _R32_EVENT_STATE['batches']=int(_R32_EVENT_STATE.get('batches') or 0)+1
    _R32_EVENT_STATE['bytes']=int(_R32_EVENT_STATE.get('bytes') or 0)+len(wire)
    _R32_EVENT_STATE['last_ok']=_r32_time.time(); _R32_EVENT_STATE['last_error']=''
    st=globals().get('_SPLIT_STATE')
    if isinstance(st,dict):
        st['r32_event_sent']=int(st.get('r32_event_sent') or 0)+len(events); st['r32_event_batches']=int(st.get('r32_event_batches') or 0)+1
        st['r32_event_bytes']=int(st.get('r32_event_bytes') or 0)+len(wire); st['r32_event_pending']=_R32_EVENT_Q.qsize(); st['r32_event_last_ok']=_r32_time.time(); st['r32_event_last_error']=''; st['r34_event_last_revision_acked']=ack; st['r35_event_last_revision_applied_peer']=applied_ack
    return True


def _r32_send_packet(packet):
    packets=list(packet.get('packets') or [])
    for part in packets:
        _r34_post_events(list(part.get('events') or []),part.get('wire') or b'',False)
    return True


def _r32_send_batch(rows):
    return _r32_send_packet(_r32_build_packet(rows))


def _r32_sender_loop():
    packet=None; backoff=0.5
    while True:
        if packet is None:
            rows=[]; queue_count=0
            max_events=max(1,min(256,int(_r32_os.getenv('R32_EVENT_BATCH_MAX','96') or '96')))
            try:
                rows.append(_R32_EVENT_Q.get(timeout=0.7)); queue_count=1
            except _r32_queue.Empty:
                # R40 restart/overflow recovery: durable SQLite is authoritative for
                # descriptors not currently present in RAM.
                rows=_r40_event_db_pending(max_events); queue_count=0
                if not rows: continue
            if queue_count:
                delay=max(0.08,min(1.5,float(_r32_os.getenv('R32_EVENT_BATCH_DELAY_SEC','0.35') or '0.35'))); _r32_time.sleep(delay)
                while len(rows)<max_events:
                    try: rows.append(_R32_EVENT_Q.get_nowait()); queue_count+=1
                    except _r32_queue.Empty: break
            try:
                _R32_EVENT_STATE['inflight']=len(rows)
                # R45-FIX2: only the background sender touches the durable event outbox.
                # RAM-origin rows must become durable before materialization/remote send.
                if queue_count and not _r40_event_db_put_many(rows):
                    raise RuntimeError('R45 durable event outbox temporarily unavailable')
                _R32_EVENT_STATE['last_enqueue_durable']=True
                packet=_r32_build_packet(rows); packet['_r40_queue_count']=queue_count
            except Exception as exc:
                _R32_EVENT_STATE['last_error']=f'build {type(exc).__name__}: {str(exc)[:220]}'
                if queue_count:
                    for row in rows:
                        try: _R32_EVENT_Q.put_nowait(row)
                        except Exception: pass
                    for _ in range(queue_count):
                        try: _R32_EVENT_Q.task_done()
                        except Exception: pass
                _R32_EVENT_STATE['inflight']=0; _r32_time.sleep(min(5.0,backoff)); backoff=min(60.0,backoff*1.8); continue
        try:
            _r32_send_packet(packet); backoff=0.5
            for _ in range(int(packet.get('_r40_queue_count') or 0)):
                try: _R32_EVENT_Q.task_done()
                except Exception: pass
            # Delete only after HEAVY durable ACK. If FAST dies before this line the
            # exact same event_id is replayed and HEAVY deduplicates it.
            _r40_event_db_delete(packet.get('rows') or [])
            packet=None; _R32_EVENT_STATE['inflight']=0; _R32_EVENT_STATE['durable_pending']=_r40_event_db_count()
        except Exception as exc:
            _R32_EVENT_STATE['last_error']=f'{type(exc).__name__}: {str(exc)[:220]}'
            st=globals().get('_SPLIT_STATE')
            if isinstance(st,dict): st['r32_event_last_error']=_R32_EVENT_STATE['last_error']
            # Frozen materialized packet only; never reread SQLite on HTTP retries.
            _r32_time.sleep(backoff); backoff=min(60.0,backoff*1.8)


def r32_flush_state_events(timeout=8.0):
    deadline=_r32_time.time()+max(0.0,float(timeout or 0.0))
    while _r32_time.time()<deadline:
        if _R32_EVENT_Q.empty() and int(_R32_EVENT_STATE.get('inflight') or 0)==0 and _r40_event_db_count()==0: return True
        _r32_time.sleep(0.05)
    return _R32_EVENT_Q.empty() and int(_R32_EVENT_STATE.get('inflight') or 0)==0 and _r40_event_db_count()==0


def _r32_patch_sqlite():
    global _R32_SQLITE_PATCHED
    if _R32_SQLITE_PATCHED: return
    cls=globals().get('SQLiteState')
    if cls is None: return
    def patch(name,builder):
        old=getattr(cls,name,None)
        if not callable(old) or getattr(old,'_r32_patched',False): return
        def wrapped(self,*args,**kwargs):
            result=old(self,*args,**kwargs)
            try:
                for kind,key,ids in (builder(args,kwargs,result) or []): _r32_enqueue_descriptor(kind,key,ids)
            except Exception as exc: _R32_EVENT_STATE['last_error']=f'capture {name}: {type(exc).__name__}: {str(exc)[:160]}'
            return result
        wrapped.__name__=getattr(old,'__name__',name); wrapped.__doc__=getattr(old,'__doc__',None); wrapped._r32_patched=True; setattr(cls,name,wrapped)
    patch('set_kv',lambda a,k,r:[('set_kv',f'kv:{a[0] if a else k.get("key","")}',{'k':str(a[0] if a else k.get('key',''))})])
    patch('save_chat',lambda a,k,r:[('save_chat',f'chat:{a[0] if a else k.get("chat_id","")}',{'chat_id':str(a[0] if a else k.get('chat_id',''))})])
    patch('save_chats',lambda a,k,r:[('prune_chats','chats:index',{})]+[('save_chat',f'chat:{cid}',{'chat_id':str(cid)}) for cid in (((a[0] if a else k.get('chats')) or {}).keys() if isinstance((a[0] if a else k.get('chats')) or {},dict) else [])])
    patch('delete_chat',lambda a,k,r:[('delete_chat',f'chat:{a[0] if a else k.get("chat_id","")}',{'chat_id':str(a[0] if a else k.get('chat_id',''))})])
    patch('set_meta',lambda a,k,r:[('set_meta',f'meta:{a[0] if a else k.get("kind","")}:{a[1] if len(a)>1 else k.get("key","")}',{'kind':str(a[0] if a else k.get('kind','')),'k':str(a[1] if len(a)>1 else k.get('key',''))})])
    patch('set_cold',lambda a,k,r:[('set_cold',f'cold:{a[0] if a else k.get("chat_id","")}:{a[1] if len(a)>1 else k.get("key","")}',{'chat_id':str(a[0] if a else k.get('chat_id','')),'k':str(a[1] if len(a)>1 else k.get('key',''))})])
    def cold_many(a,k,r):
        cid=str(a[0] if a else k.get('chat_id','')); items=(a[1] if len(a)>1 else k.get('items')) or {}; return [('set_cold_many',f'coldmany:{cid}',{'chat_id':cid,'keys':[str(x) for x in items.keys()]})]
    patch('set_cold_many',cold_many)
    patch('delete_cold',lambda a,k,r:[('delete_cold',f'cold:{a[0] if a else k.get("chat_id","")}:{a[1] if len(a)>1 else k.get("key","")}',{'chat_id':str(a[0] if a else k.get('chat_id','')),'k':str(a[1] if len(a)>1 else k.get('key',''))})])
    _R32_SQLITE_PATCHED=True

_r32_patch_sqlite()

# Normal runtime full mirroring is disabled. Emergency/manual code remains available
# in R98, but these scheduler entry points no longer arm it.
def split_schedule_worker_sync_v262(reason='change',delay=None):
    st=globals().get('_SPLIT_STATE')
    if isinstance(st,dict): st['sync_pending']=False; st['sync_reason']='r32-events:'+str(reason or '')[:120]
    return True

def _split_schedule_idle_full_reconcile_v270(reason='need_full',delay=None):
    _R32_EVENT_STATE['full_runtime_uploads_blocked']=int(_R32_EVENT_STATE.get('full_runtime_uploads_blocked') or 0)+1
    st=globals().get('_SPLIT_STATE')
    if isinstance(st,dict): st['full_reconcile_pending']=False; st['full_reconcile_last_error']='R34 event-stream: periodic full snapshot suppressed'
    return True

def _split_request_worker_full_sync_r18(reason='need_full'):
    return True,'R34 event-stream mode: full rebase not required'

def _split_push_snapshot_now_v263(reason='shutdown', sync_mega=False):
    """Send one exact SQLite image to HEAVY; only HEAVY is allowed to publish it to MEGA."""
    try:
        r32_flush_state_events(timeout=float(_r32_os.getenv('R32_SHUTDOWN_EVENT_FLUSH_SEC','8') or '8'))
    except Exception:
        pass
    base, secret = _split_peer_base(), _split_secret()
    if not base or not secret:
        _R32_EVENT_STATE['last_error'] = 'HEAVY peer is not configured for exact snapshot handoff'
        return False
    workdir = _split_tempfile.mkdtemp(prefix='r49_front_heavy_snapshot_')
    raw = _split_os.path.join(workdir, 'bot_state.sqlite3')
    gz = raw + '.gz'
    try:
        SQLITE.backup_to(raw)
        with open(raw, 'rb') as src, _split_gzip.open(gz, 'wb', compresslevel=1) as dst:
            _split_shutil.copyfileobj(src, dst, length=1024 * 1024)
        with open(gz, 'rb') as fh:
            body = fh.read()
        headers = {**_split_headers('vys-262-r49-fast-heavy-snapshot'),
                   'Content-Type': 'application/gzip',
                   'X-Snapshot-Reason': str(reason or '')[:120],
                   'X-Split-State-Token': _split_current_state_token_v264(),
                   'X-Snapshot-Promote-Mode': 'sync' if bool(sync_mega) else 'async'}
        timeout = 240 if bool(sync_mega) else 30
        r = __import__('requests').post(base + '/internal/snapshot/upload', data=body, headers=headers, timeout=timeout)
        try: row = r.json() if r.content else {}
        except Exception: row = {}
        if 200 <= int(r.status_code) < 300:
            if str(row.get('status') or '') == 'stale_ignored':
                _R32_EVENT_STATE['last_error'] = 'HEAVY has newer snapshot; stale FAST image ignored'
                return False
            if bool(sync_mega) and not bool(row.get('mega_promoted')):
                _R32_EVENT_STATE['last_error'] = 'HEAVY accepted snapshot but did not confirm MEGA promotion'
                return False
            return True
        _R32_EVENT_STATE['last_error'] = f'HEAVY snapshot HTTP {r.status_code}: {str(row or r.text)[:220]}'
    except Exception as exc:
        _R32_EVENT_STATE['last_error'] = f'HEAVY snapshot {type(exc).__name__}: {str(exc)[:180]}'
    finally:
        _split_shutil.rmtree(workdir, ignore_errors=True)
    return False

def r32_event_stream_status():
    # R45-FIX2: diagnostics/UI reads cached counters only; never touch outbox SQLite.
    row=dict(_R32_EVENT_STATE); row['durable_pending']=int(row.get('durable_pending') or 0); row['pending']=max(_R32_EVENT_Q.qsize(),int(row.get('durable_pending') or 0)); row['enabled']=bool(_R32_EVENT_STREAM_ENABLED); row['peer_base']=_r32_peer_base_impl(); return row

_r32_threading.Thread(target=_r32_sender_loop,name='per-r32-state-events',daemon=True).start()

# --- ИСТОЧНИК: 100_r33_heavy_offload.py ---
"""Пер-R43: all user-requested heavy file/table/journal jobs are delegated to HEAVY.

This module is intentionally loaded last.  It does not touch the R28 direct-render
function.  The Telegram callback only creates the existing small status message and
queues a descriptor; state flush, serialization and HTTP happen on the background
heavy-dispatch pool.
"""
import datetime as _r33_datetime
import json as _r33_json
import os as _r33_os
import time as _r33_time

_LOCAL_SUBMIT_FILE_JOB = globals().get('submit_interactive_file_job')
_R33_HEAVY_FILE_KINDS = {
    'period_export','exact_export','xlsx','csv','tabl_lsx','json','json_full','sqlite',
    'runtime','journal','journal_current','window_markers','window_tz',
    'window_tz_archive'
}
# Future annotation/document buttons with the same prefix are heavy by contract.
try:
    _R21_REMOTE_FILE_KINDS.update(_R33_HEAVY_FILE_KINDS)
except Exception:
    pass


def _r33_safe_scalar(value):
    if value is None or isinstance(value,(str,int,float,bool)):
        return value
    if isinstance(value,(_r33_datetime.datetime,_r33_datetime.date)):
        return value.isoformat()
    if isinstance(value,(list,tuple,set)):
        return [_r33_safe_scalar(x) for x in value]
    if isinstance(value,dict):
        return {str(k):_r33_safe_scalar(v) for k,v in value.items()}
    return str(value)


def _r33_tenant_chat_ids(tid):
    try:
        fn=globals().get('tenant_chat_ids')
        return [int(x) for x in (fn(str(tid)) or [])] if callable(fn) and tid else []
    except Exception:
        return []


def _r33_export_body(kind,label,func_name,args,kwargs):
    a=list(args or ()); k=dict(kwargs or {})
    cid=int(a[0] if a else k.get('chat_id') or 0)
    body={
        'job_id': _split_secrets.token_hex(12) if '_split_secrets' in globals() else __import__('secrets').token_hex(12),
        'recipient_chat_id':cid,'target_chat_id':cid,'operation':str(kind),
        'label':str(label or kind),'chat_name':str(globals().get('get_chat_display_name',lambda x:str(x))(cid)),
        'delivery':'chat','front_release':'Пер-R43',
    }
    fn=str(func_name or '')
    if kind in {'period_export','xlsx'} or fn.endswith('send_export_for_chat_to'):
        # recipient, target, mode, day_key, file_type, style?, options?, delivery?
        if len(a)>=2: body['target_chat_id']=int(a[1])
        body['mode']=str(a[2] if len(a)>2 else k.get('mode') or 'all')
        body['day_key']=str(a[3] if len(a)>3 else k.get('day_key') or '')[:10]
        body['source_file_type']=str(a[4] if len(a)>4 else k.get('file_type') or ('xlsx' if kind=='xlsx' else 'csv')).lower().lstrip('.')
        body['file_type']='xlsx' if body['source_file_type'] in {'xlsx','xlsxstat','excel'} else 'csv'
        if len(a)>5 and a[5] is not None: body['style']=str(a[5])
        if len(a)>6 and isinstance(a[6],dict): body['excel_options']=_r33_safe_scalar(a[6])
        if len(a)>7: body['delivery']=str(a[7] or 'chat')
        body['operation']='period_export_query'
    elif kind=='exact_export' or fn.endswith('send_exact_range_export'):
        if len(a)>=2: body['target_chat_id']=int(a[1])
        body.update({'start_key':str(a[2] if len(a)>2 else '')[:10],'start_rid':int(a[3] if len(a)>3 else 0),
                     'end_key':str(a[4] if len(a)>4 else '')[:10],'end_rid':int(a[5] if len(a)>5 else 0)})
        body['source_file_type']=str(a[6] if len(a)>6 else 'csv').lower().lstrip('.')
        body['file_type']='xlsx' if body['source_file_type'] in {'xlsx','xlsxstat','excel'} else 'csv'
        if len(a)>7 and a[7] is not None: body['style']=str(a[7])
        if len(a)>8 and isinstance(a[8],dict): body['excel_options']=_r33_safe_scalar(a[8])
        if len(a)>9: body['delivery']=str(a[9] or 'chat')
        body['operation']='exact_export_query'
    elif kind=='csv':
        body.update({'operation':'period_export_query','mode':'all','day_key':'','source_file_type':'csv','file_type':'csv'})
    elif kind=='tabl_lsx':
        if len(a)>=2: body['target_chat_id']=int(a[1])
        body.update({'operation':'tabl_lsx','file_type':'xlsx','source_file_type':'xlsx'})
    elif kind=='json':
        body.update({'operation':'chat_json','file_type':'json'})
    elif kind=='json_full':
        scope=str(a[1] if len(a)>1 else k.get('scope') or 'global')
        tid=(a[2] if len(a)>2 else k.get('tenant_id'))
        body.update({'operation':'full_state','file_type':'gz','scope':scope,'tenant_id':str(tid or ''),
                     'tenant_chat_ids':_r33_tenant_chat_ids(tid) if scope=='tenant' else []})
    elif kind=='sqlite':
        body.update({'operation':'sqlite','file_type':'sqlite'})
    elif kind=='runtime':
        body.update({'operation':'runtime_zip','file_type':'zip','start_dt':_r33_safe_scalar(a[1] if len(a)>1 else None),
                     'end_dt':_r33_safe_scalar(a[2] if len(a)>2 else None)})
    elif kind in {'journal','journal_current'}:
        body.update({'operation':kind,'file_type':'txt','limit':int(a[1] if len(a)>1 else 5000)})
    elif kind=='bot_source':
        body.update({'operation':'bot_source','file_type':'py'})
    elif kind.startswith('window_'):
        body.update({'operation':kind,'file_type':'txt'})
    else:
        body.update({'operation':str(kind),'args':_r33_safe_scalar(a),'kwargs':_r33_safe_scalar(k)})
    # Google/Drive config lookup is small metadata only; all table construction/API calls stay on HEAVY.
    if str(body.get('delivery') or '').lower() in {'google','drive'}:
        try:
            tid=str(tenant_id_for_chat(int(body.get('target_chat_id') or cid),create=False) or TENANT_PLATFORM_ID)
            cfg=tenant_google_config(tid,create=False) or {}
            body['tenant_id']=tid
            body['spreadsheet_id']=str(cfg.get('spreadsheet_id') or cfg.get('sheet_id') or '')
            body['drive_folder_id']=str(cfg.get('drive_folder_id') or '')
        except Exception:
            pass
    # R35 diagnostics: capture only tiny RAM dictionaries on FAST; HEAVY still does
    # all serialization/archive construction. This keeps diagnostics about Render #1.
    if str(body.get('operation') or '') in {'runtime_zip','journal','journal_current'}:
        try:
            body['front_runtime_snapshot']=_r33_safe_scalar({
                'release':'R51',
                'bot_version':str(globals().get('VERSION') or ''),
                'render_instance_id':str(_r33_os.getenv('RENDER_INSTANCE_ID','') or ''),
                'render_git_commit':str(_r33_os.getenv('RENDER_GIT_COMMIT','') or ''),
                'captured_at':_r33_time.time(),
                'runtime':dict(globals().get('_RUNTIME_STATE') or {}),
                'split':dict(globals().get('_SPLIT_STATE') or {}),
                'state_events':dict(globals().get('_R32_EVENT_STATE') or {}),
            })
        except Exception: pass
    # R34 ordering fence: state-dependent jobs carry the newest queued revision.
    # FAST never waits for it; HEAVY waits/replays in its own queue.
    if str(body.get('operation') or '') in {'period_export_query','exact_export_query','tabl_lsx','chat_json','full_state','sqlite','window_markers','window_tz','window_tz_archive'}:
        try: body['required_revision']=int((_R32_EVENT_STATE or {}).get('last_revision_queued') or 0)
        except Exception: body['required_revision']=0
    # filename/caption are generated on HEAVY from the authoritative state.
    return body


def _r33_remote_file_adapter(kind,label,func_name,args,kwargs):
    # R34: never wait for global state synchronization on FAST.  The job carries a
    # revision fence and HEAVY waits for only the state it actually needs.
    body=_r33_export_body(str(kind),str(label),str(func_name),args,kwargs)
    try: _file_job_progress('передаю задание Render #2', force=True)
    except Exception: pass
    submit=globals().get('_r7_worker_file_submit')
    if not callable(submit): raise RuntimeError('R38 HEAVY export bridge unavailable')
    jid=submit(body)
    try: bot_journal('r35_heavy_file_accepted_legacy_guard',int(body.get('recipient_chat_id') or 0),f"kind={kind}; op={body.get('operation')}; job={jid}; required_revision={body.get('required_revision') or 0}")
    except Exception: pass
    # R35 intentionally does NOT mark accepted/queued as delivered here. The final
    # adapter defined below waits for the real FAST delivery callback.
    return True

# R47 FINALIZATION: no early submit override; R40 is the sole public owner.


# R34 parity: legacy direct CSV/XLSX helpers are also query-only HEAVY jobs.
# This catches commands/functions that historically bypassed submit_interactive_file_job.
def _r34_export_marker(*args,**kwargs): return True

def send_export_for_chat_to(recipient_chat_id:int,target_chat_id:int,mode:str,day_key:str,file_type:str='csv',excel_style_override=None,excel_options_override=None,delivery:str='chat'):
    kind='period_export'
    label=('Google Excel' if str(delivery or '').lower()=='google' else ('Excel' if str(file_type).lower().startswith('xlsx') else 'CSV'))+' экспорт'
    ok,_info=submit_interactive_file_job(int(recipient_chat_id),kind,label,_r34_export_marker,int(recipient_chat_id),int(target_chat_id),str(mode),str(day_key),str(file_type),excel_style_override,excel_options_override,str(delivery or 'chat'))
    return bool(ok)

def send_exact_range_export(recipient_chat_id:int,target_chat_id:int,start_key:str,start_rid:int,end_key:str,end_rid:int,file_type:str,excel_style_override=None,excel_options_override=None,delivery:str='chat'):
    label=('Google Excel' if str(delivery or '').lower()=='google' else ('Excel' if str(file_type).lower().startswith('xlsx') else 'CSV'))+' точный экспорт'
    ok,_info=submit_interactive_file_job(int(recipient_chat_id),'exact_export',label,_r34_export_marker,int(recipient_chat_id),int(target_chat_id),str(start_key),int(start_rid),str(end_key),int(end_rid),str(file_type),excel_style_override,excel_options_override,str(delivery or 'chat'))
    return bool(ok)

def send_tabl_lsx_for_chat(recipient_chat_id:int,target_chat_id:int):
    ok,_info=submit_interactive_file_job(int(recipient_chat_id),'tabl_lsx','Excel /tabl_lsx',_r34_export_marker,int(recipient_chat_id),int(target_chat_id))
    return bool(ok)

send_export_for_chat_to = send_export_for_chat_to
send_exact_range_export = send_exact_range_export
send_tabl_lsx_for_chat = send_tabl_lsx_for_chat

# Defensive R49 hot-path regression gate: callback renderer must only enqueue.
try:
    _src=__import__('inspect').getsource(globals().get('fast_ui_edit_message_text'))
    if 'WINDOW_RENDER_TASK_POOL.submit_latest' not in _src or '_r22_execute_window_render' not in _src or '_perform_fast_ui_edit(payload)' in _src:
        raise RuntimeError('R34 HOTPATH GUARD: R49 non-blocking render contract changed')
except OSError:
    pass

try:
    bot_journal('r34_heavy_offload_loaded',int(OWNER_ID or 0),'unified-bot: files/tables/journals/json/full-state/sqlite/runtime/window-docs -> HEAVY; no FAST state barrier')
except Exception:
    pass

# ---------------------------------------------------------------------------
# Пер-R43: end-to-end HEAVY delivery control.
# 202/queued is only an acceptance ACK. The FAST file job remains open until
# Render #2's callback has actually delivered the result to Telegram/Google.
_R35_REMOTE_RESULT_LOCK = __import__('threading').RLock()
_R35_REMOTE_RESULT = {}
# R36: separate tiny delivery ledger. This is intentionally NOT the finance DB and
# never takes data_lock/SQLITE.lock. Redis still covers cross-container durability.
_R36_DELIVERY_DB = str(globals().get('DB_FILE') or 'data.sqlite3') + '.r36_delivery.sqlite3'
_R36_DELIVERY_DB_LOCK = __import__('threading').RLock()

def _r36_delivery_db_init():
    sql=__import__('sqlite3')
    with _R36_DELIVERY_DB_LOCK:
        con=sql.connect(_R36_DELIVERY_DB,timeout=2,check_same_thread=False)
        try:
            con.execute('PRAGMA journal_mode=WAL'); con.execute('PRAGMA synchronous=FULL'); con.execute('PRAGMA busy_timeout=2000')
            con.execute('CREATE TABLE IF NOT EXISTS delivery(job_id TEXT PRIMARY KEY,row_json TEXT NOT NULL,ts REAL NOT NULL)')
            con.commit()
        finally: con.close()

def _r36_delivery_local_set(jid,row):
    try:
        _r36_delivery_db_init(); sql=__import__('sqlite3')
        raw=_r33_json.dumps(row,ensure_ascii=False,separators=(',',':'),default=str)
        with _R36_DELIVERY_DB_LOCK:
            con=sql.connect(_R36_DELIVERY_DB,timeout=2,check_same_thread=False)
            try:
                con.execute('PRAGMA busy_timeout=2000')
                con.execute('INSERT INTO delivery(job_id,row_json,ts) VALUES(?,?,?) ON CONFLICT(job_id) DO UPDATE SET row_json=excluded.row_json,ts=excluded.ts',(str(jid),raw,float(row.get('ts') or _r33_time.time())))
                con.commit()
            finally: con.close()
    except Exception: pass

def _r36_delivery_local_get(jid):
    try:
        _r36_delivery_db_init(); sql=__import__('sqlite3')
        with _R36_DELIVERY_DB_LOCK:
            con=sql.connect(_R36_DELIVERY_DB,timeout=2,check_same_thread=False)
            try:
                con.execute('PRAGMA busy_timeout=2000'); r=con.execute('SELECT row_json FROM delivery WHERE job_id=?',(str(jid),)).fetchone()
            finally: con.close()
        obj=_r33_json.loads(r[0]) if r else {}
        return obj if isinstance(obj,dict) else {}
    except Exception: return {}

def _r35_delivery_redis_client():
    try:
        pkg=globals().get('_split_redis')
        url=_r61_effective_redis_url()
        if pkg is None or not url: return None
        return pkg.Redis.from_url(url,socket_connect_timeout=1.0,socket_timeout=2.0,health_check_interval=30)
    except Exception:
        return None

def _r35_delivery_key(jid):
    return 'per:r35:front:delivery:'+str(jid or '')[:80]

def _r35_delivery_set(jid,state,body=None,error=''):
    row={'state':str(state or ''),'ts':_r33_time.time(),'body':_r33_safe_scalar(body or {}),'error':str(error or '')[:1000]}
    with _R35_REMOTE_RESULT_LOCK:
        _R35_REMOTE_RESULT[str(jid)]=row
    _r36_delivery_local_set(jid,row)
    try:
        c=_r35_delivery_redis_client()
        if c is not None:
            c.set(_r35_delivery_key(jid),_r33_json.dumps(row,ensure_ascii=False,separators=(',',':'),default=str),ex=172800)
    except Exception:
        pass
    return row

def _r35_delivery_get(jid):
    jid=str(jid or '')
    with _R35_REMOTE_RESULT_LOCK:
        row=dict(_R35_REMOTE_RESULT.get(jid) or {})
    local=_r36_delivery_local_get(jid)
    if isinstance(local,dict) and float(local.get('ts') or 0)>=float(row.get('ts') or 0): row=local
    try:
        c=_r35_delivery_redis_client()
        raw=c.get(_r35_delivery_key(jid)) if c is not None else None
        if raw:
            remote=_r33_json.loads(raw.decode('utf-8') if isinstance(raw,(bytes,bytearray)) else raw)
            if isinstance(remote,dict) and float(remote.get('ts') or 0)>=float(row.get('ts') or 0): row=remote
    except Exception:
        pass
    return row

def _r35_worker_file_submit(body:dict):
    base=globals().get('_split_peer_base',lambda:'')()
    headers_fn=globals().get('_split_headers')
    if not base or not globals().get('_split_secret',lambda:'')(): raise RuntimeError('Render #2 не настроен для файлового экспорта')
    # R36: assign once before the first network attempt. A lost 202 response can then
    # be retried safely without creating a second export.
    jid=str(body.get('job_id') or __import__('secrets').token_hex(12)).strip()[:80]
    body['job_id']=jid
    last=''
    attempts=max(2,min(6,int(__import__('os').getenv('R36_FILE_SUBMIT_ATTEMPTS','4') or '4')))
    timeout=max(8.0,min(90.0,float(__import__('os').getenv('R36_FILE_SUBMIT_TIMEOUT_SEC','45') or '45')))
    for attempt in range(1,attempts+1):
        try:
            hdr=headers_fn('per-r36-front-export') if callable(headers_fn) else {'X-Peer-Secret':str(__import__('os').getenv('PEER_SHARED_SECRET','') or '')}
            r=requests.post(base+'/internal/export/file',json=body,headers=hdr,timeout=timeout)
            payload={}
            if r.content:
                try:
                    obj=r.json(); payload=obj if isinstance(obj,dict) else {}
                except Exception:
                    payload={}
            status=str(payload.get('status') or '')
            accepted=200<=r.status_code<300 and (payload.get('ok') is True or status in {'queued','running','ready','delivering','delivered','done'})
            if accepted and payload.get('durable') is True:
                returned=str(payload.get('job_id') or jid)
                if returned!=jid:
                    last=f'Render #2 вернул другой job_id: {returned}'
                else:
                    return jid
            elif accepted:
                last='Render #2 принял задание без durable-подтверждения'
            else:
                body_text=''
                try: body_text=(r.text or '')[:500]
                except Exception: pass
                last=str(payload.get('error') or body_text or f'HTTP {r.status_code}')
            if 400<=r.status_code<500 and r.status_code not in {408,409,425,429}: break
        except Exception as exc:
            last=f'{type(exc).__name__}: {str(exc)[:400]}'
        if attempt<attempts: _r33_time.sleep(min(2.0,0.4*attempt))
    raise RuntimeError(last or 'Render #2 не подтвердил durable-приём задания')

_r7_worker_file_submit = _r35_worker_file_submit

def _r35_export_delivery_task(body):
    jid=str((body or {}).get('job_id') or '')
    delivered=False
    try:
        delivered=bool(globals().get('_r7_deliver_worker_export')(dict(body)))
    except Exception as exc:
        _r35_delivery_set(jid,'failed',body,error=f'{type(exc).__name__}: {str(exc)[:700]}')
        return
    if delivered:
        if bool((body or {}).get('ok')):
            _r35_delivery_set(jid,'done',body)
        else:
            _r35_delivery_set(jid,'done_error',body,error=str((body or {}).get('error') or 'HEAVY job failed'))
    else:
        _r35_delivery_set(jid,'failed',body,error='FAST delivery attempt failed')

def split_front_export_result_r35():
    if not globals().get('_split_authorized_request',lambda:False)(): return ({'ok':False},404)
    body=request.get_json(silent=True) or {}; jid=str(body.get('job_id') or '')
    if not jid: return ({'ok':False,'error':'job_id required'},400)
    row=_r35_delivery_get(jid); state=str(row.get('state') or ''); age=max(0.0,_r33_time.time()-float(row.get('ts') or 0))
    if state in {'done','done_error'}:
        return ({'ok':True,'delivered':True,'duplicate':True,'operation_ok':state=='done'},200)
    # A stale 'running' marker can survive a FAST restart. Allow HEAVY to retrigger it.
    if state=='running' and age<45:
        return ({'ok':True,'accepted':True,'delivered':False},202)
    _r35_delivery_set(jid,'running',body)
    try:
        pool=globals().get('GENERAL_TASK_POOL') or globals().get('BACKGROUND_TASK_POOL'); submitted=False
        if pool is not None and hasattr(pool,'submit'):
            submitted=bool(pool.submit('r36-export-delivery:'+jid,_r35_export_delivery_task,dict(body)))
        if not submitted:
            __import__('threading').Thread(target=_r35_export_delivery_task,args=(dict(body),),daemon=True,name='per-r36-front-delivery').start()
    except Exception:
        __import__('threading').Thread(target=_r35_export_delivery_task,args=(dict(body),),daemon=True,name='per-r36-front-delivery').start()
    return ({'ok':True,'accepted':True,'delivered':False},202)

try:
    # Keep the existing Flask route, replace only its implementation.
    app.view_functions['split_front_export_result_r7']=split_front_export_result_r35
except Exception:
    pass

def _r35_wait_remote_delivery(jid,body):
    timeout=max(60,min(7200,int(__import__('os').getenv('R36_FAST_JOB_WAIT_SEC','1800') or '1800')))
    deadline=_r33_time.time()+timeout; last_progress=0.0
    while _r33_time.time()<deadline:
        row=_r35_delivery_get(jid); state=str(row.get('state') or '')
        if state=='done': return True
        if state=='done_error':
            b=row.get('body') if isinstance(row.get('body'),dict) else {}
            raise RuntimeError(str(row.get('error') or b.get('error') or 'Render #2 завершил задачу с ошибкой')[:900])
        now=_r33_time.time()
        if now-last_progress>5:
            try:
                phase='ожидаю доставку результата' if state in {'running','failed'} else 'Render #2 выполняет задачу'
                _file_job_progress(phase,force=True)
            except Exception: pass
            last_progress=now
        _r33_time.sleep(0.45)
    raise RuntimeError(f'Render #2 не подтвердил доставку за {timeout} сек.; job_id={jid}')

def _r33_remote_file_adapter(kind,label,func_name,args,kwargs):
    body=_r33_export_body(str(kind),str(label),str(func_name),args,kwargs)
    body['front_release']='Пер-R43'
    try: _file_job_progress('передаю задание Render #2',force=True)
    except Exception: pass
    submit=globals().get('_r7_worker_file_submit')
    if not callable(submit): raise RuntimeError('R38 HEAVY export bridge unavailable')
    jid=submit(body)
    existing=_r35_delivery_get(jid)
    if str(existing.get('state') or '') not in {'running','done','done_error'}:
        _r35_delivery_set(jid,'accepted',{'job_id':jid,'operation':body.get('operation'),'recipient_chat_id':body.get('recipient_chat_id')})
    try: bot_journal('r36_heavy_file_accepted',int(body.get('recipient_chat_id') or 0),f"kind={kind}; op={body.get('operation')}; job={jid}; required_revision={body.get('required_revision') or 0}")
    except Exception: pass
    _r35_wait_remote_delivery(jid,body)
    # This call runs inside the original FAST file-job context, so only now may the
    # canonical runner close the status window and release its single-flight lock.
    delivery=str(body.get('delivery') or 'chat').lower()
    delivered_kind='Telegram через Render #2' if delivery=='chat' else ('Google Sheets' if delivery=='google' else 'Google Drive')
    if not file_job_mark_external_delivery(delivered_kind,jid):
        raise RuntimeError('R36 delivery was confirmed but FAST file-job context was lost')
    return True

try:
    bot_journal('r36_transport_fix_loaded',int(OWNER_ID or 0),'accepted!=delivered; local+redis delivery ledger; safe HTTP/JSON; same-job retry; stale callback recovery')
except Exception:
    pass

# ---------------------------------------------------------------------------
# R38 resilient FAST -> HEAVY transport.
# A user job is first persisted in a local/Redis outbox and only then dispatched.
# Public Render/Cloudflare 429/5xx/HTML challenges are transport states, not user errors.
import sqlite3 as _r38_sqlite3
import threading as _r38_threading
import random as _r38_random

_R38_OUTBOX_DB = _r33_os.path.join(str(_r33_os.getenv('R38_OUTBOX_DIR','/tmp') or '/tmp'), 'per_r38_peer_outbox.sqlite3')
_R38_OUTBOX_LOCK = _r38_threading.RLock()
_R38_OUTBOX_PENDING_KEY = 'per:r38:front:peer_outbox:pending'
_R38_OUTBOX_PREFIX = 'per:r38:front:peer_outbox:'
_R38_OUTBOX_WAKE = _r38_threading.Event()
_R38_PEER_HTTP_LOCK = _r38_threading.RLock()
_R38_PEER_LAST_HTTP = 0.0
_R38_PEER_BLOCK_UNTIL = 0.0
_R38_PEER_STATE = {'accepted':0,'retries':0,'cloudflare':0,'http_5xx':0,'last_error':'','last_ok':0.0,'last_status':0}


def _r38_outbox_db_init():
    try:
        _r33_os.makedirs(_r33_os.path.dirname(_R38_OUTBOX_DB) or '.', exist_ok=True)
        with _R38_OUTBOX_LOCK:
            con=_r38_sqlite3.connect(_R38_OUTBOX_DB,timeout=3,check_same_thread=False)
            try:
                con.execute('PRAGMA journal_mode=WAL'); con.execute('PRAGMA synchronous=FULL'); con.execute('PRAGMA busy_timeout=3000')
                con.execute('CREATE TABLE IF NOT EXISTS outbox(job_id TEXT PRIMARY KEY,row_json TEXT NOT NULL,state TEXT NOT NULL,updated_at REAL NOT NULL)')
                con.execute('CREATE INDEX IF NOT EXISTS idx_r38_outbox_state ON outbox(state,updated_at)')
                con.commit()
            finally: con.close()
        return True
    except Exception:
        return False


def _r38_outbox_local_put(row):
    if not isinstance(row,dict) or not str(row.get('job_id') or ''): return False
    try:
        _r38_outbox_db_init(); obj=dict(row); obj['updated_at']=float(obj.get('updated_at') or _r33_time.time())
        raw=_r33_json.dumps(obj,ensure_ascii=False,separators=(',',':'),default=str)
        with _R38_OUTBOX_LOCK:
            con=_r38_sqlite3.connect(_R38_OUTBOX_DB,timeout=3,check_same_thread=False)
            try:
                con.execute('PRAGMA busy_timeout=3000')
                con.execute('INSERT INTO outbox(job_id,row_json,state,updated_at) VALUES(?,?,?,?) ON CONFLICT(job_id) DO UPDATE SET row_json=excluded.row_json,state=excluded.state,updated_at=excluded.updated_at',(str(obj['job_id']),raw,str(obj.get('state') or 'pending'),float(obj['updated_at'])))
                con.commit()
            finally: con.close()
        return True
    except Exception:
        return False


def _r38_outbox_local_get(jid):
    try:
        _r38_outbox_db_init()
        with _R38_OUTBOX_LOCK:
            con=_r38_sqlite3.connect(_R38_OUTBOX_DB,timeout=2,check_same_thread=False)
            try:
                con.execute('PRAGMA busy_timeout=2000'); row=con.execute('SELECT row_json FROM outbox WHERE job_id=?',(str(jid),)).fetchone()
            finally: con.close()
        obj=_r33_json.loads(row[0]) if row else {}
        return obj if isinstance(obj,dict) else {}
    except Exception: return {}


def _r38_outbox_local_pending(limit=200):
    out=[]
    try:
        _r38_outbox_db_init()
        with _R38_OUTBOX_LOCK:
            con=_r38_sqlite3.connect(_R38_OUTBOX_DB,timeout=2,check_same_thread=False)
            try:
                con.execute('PRAGMA busy_timeout=2000'); rows=con.execute("SELECT row_json FROM outbox WHERE state IN ('pending','retry') ORDER BY updated_at ASC LIMIT ?",(max(1,min(1000,int(limit))),)).fetchall()
            finally: con.close()
        for row in rows:
            try:
                obj=_r33_json.loads(row[0]);
                if isinstance(obj,dict): out.append(obj)
            except Exception: pass
    except Exception: pass
    return out


def _r38_outbox_redis_client():
    try: return _r35_delivery_redis_client()
    except Exception: return None


def _r38_outbox_key(jid): return _R38_OUTBOX_PREFIX+str(jid or '')[:80]


def _r38_outbox_put(row,pending=None):
    obj=dict(row or {}); jid=str(obj.get('job_id') or '')[:80]
    if not jid: return False
    obj['job_id']=jid; obj['updated_at']=_r33_time.time()
    local_ok=_r38_outbox_local_put(obj)
    c=_r38_outbox_redis_client(); redis_ok=False
    if c is not None:
        try:
            raw=_r33_json.dumps(obj,ensure_ascii=False,separators=(',',':'),default=str)
            pipe=c.pipeline(transaction=False); pipe.set(_r38_outbox_key(jid),raw,ex=604800)
            is_pending=(str(obj.get('state') or '') in {'pending','retry'}) if pending is None else bool(pending)
            if is_pending: pipe.sadd(_R38_OUTBOX_PENDING_KEY,jid)
            else: pipe.srem(_R38_OUTBOX_PENDING_KEY,jid)
            pipe.expire(_R38_OUTBOX_PENDING_KEY,604800); pipe.execute(); redis_ok=True
        except Exception: pass
    return bool(local_ok or redis_ok)


def _r38_outbox_get(jid):
    best=_r38_outbox_local_get(jid)
    c=_r38_outbox_redis_client()
    if c is not None:
        try:
            raw=c.get(_r38_outbox_key(jid))
            if raw:
                obj=_r33_json.loads(raw.decode('utf-8') if isinstance(raw,(bytes,bytearray)) else raw)
                if isinstance(obj,dict) and float(obj.get('updated_at') or 0)>=float(best.get('updated_at') or 0): best=obj
        except Exception: pass
    return best if isinstance(best,dict) else {}


def _r38_outbox_pending_rows_core(limit=200):
    rows={str(x.get('job_id')):x for x in _r38_outbox_local_pending(limit) if str(x.get('job_id') or '')}
    c=_r38_outbox_redis_client()
    if c is not None:
        try:
            ids=list(c.smembers(_R38_OUTBOX_PENDING_KEY) or [])[:max(1,min(1000,int(limit)))]
            for raw_jid in ids:
                jid=raw_jid.decode() if isinstance(raw_jid,(bytes,bytearray)) else str(raw_jid)
                obj=_r38_outbox_get(jid)
                if obj and float(obj.get('updated_at') or 0)>=float((rows.get(jid) or {}).get('updated_at') or 0): rows[jid]=obj
        except Exception: pass
    return list(rows.values())


def _r38_peer_transient_response(r):
    try: status=int(getattr(r,'status_code',0) or 0)
    except Exception: status=0
    text=''
    try: text=str(r.text or '')[:1200].casefold()
    except Exception: pass
    ctype=''
    try: ctype=str(r.headers.get('content-type','') or '').casefold()
    except Exception: pass
    html=('text/html' in ctype or '<!doctype html' in text or '<html' in text)
    cloud=html and any(x in text for x in ('just a moment','cloudflare','challenge','cf-ray'))
    transient=status in {0,408,425,429,500,502,503,504,520,521,522,523,524} or cloud
    return transient,cloud,status


def _r38_retry_after(r,attempt):
    try:
        raw=str(r.headers.get('Retry-After','') or '').strip()
        if raw: return max(1.0,min(120.0,float(raw)))
    except Exception: pass
    base=min(60.0, max(1.0, 1.25*(2**min(5,max(0,int(attempt)-1)))))
    return base + _r38_random.uniform(0.0,min(1.5,base*0.15))


def _r38_peer_gate():
    global _R38_PEER_LAST_HTTP
    with _R38_PEER_HTTP_LOCK:
        now=_r33_time.time(); block=max(0.0,float(globals().get('_R38_PEER_BLOCK_UNTIL',0.0) or 0.0)-now)
        gap=max(0.0,float(_r33_os.getenv('R38_PEER_MIN_GAP_SEC','0.18') or '0.18')-(now-float(_R38_PEER_LAST_HTTP or 0.0)))
        wait=max(block,gap)
        if wait>0: _r33_time.sleep(wait)
        _R38_PEER_LAST_HTTP=_r33_time.time()


def _r38_peer_attempt(row):
    global _R38_PEER_BLOCK_UNTIL
    endpoint=str(row.get('endpoint') or '')
    body=row.get('body') if isinstance(row.get('body'),dict) else {}
    kind=str(row.get('kind') or 'peer')
    base=globals().get('_split_peer_base',lambda:'')()
    headers_fn=globals().get('_split_headers')
    if not base or not globals().get('_split_secret',lambda:'')():
        raise RuntimeError('Render #2 URL/secret not configured')
    _r38_peer_gate()
    hdr=headers_fn('per-r38-front-'+kind) if callable(headers_fn) else {'X-Peer-Secret':str(_r33_os.getenv('PEER_SHARED_SECRET','') or '')}
    r=requests.post(base+endpoint,json=body,headers=hdr,timeout=max(5.0,min(35.0,float(_r33_os.getenv('R38_PEER_POST_TIMEOUT_SEC','18') or '18'))))
    transient,cloud,status=_r38_peer_transient_response(r)
    _R38_PEER_STATE['last_status']=status
    if cloud: _R38_PEER_STATE['cloudflare']=int(_R38_PEER_STATE.get('cloudflare') or 0)+1
    if status>=500: _R38_PEER_STATE['http_5xx']=int(_R38_PEER_STATE.get('http_5xx') or 0)+1
    payload={}
    try:
        if r.content and 'json' in str(r.headers.get('content-type','') or '').casefold():
            obj=r.json(); payload=obj if isinstance(obj,dict) else {}
    except Exception: payload={}
    if transient:
        wait=_r38_retry_after(r,int(row.get('attempts') or 0)+1)
        with _R38_PEER_HTTP_LOCK:
            _R38_PEER_BLOCK_UNTIL=max(float(_R38_PEER_BLOCK_UNTIL or 0.0),_r33_time.time()+min(wait,15.0))
        safe=('Cloudflare/HTML challenge' if cloud else f'HTTP {status}')
        return False,True,safe,wait,payload
    status_name=str(payload.get('status') or '')
    accepted=200<=status<300 and (payload.get('ok') is True or status_name in {'queued','running','ready','delivering','delivered','done','failed'})
    # R38 contracts: user jobs are accepted only after HEAVY confirms its own durable spool.
    if accepted and payload.get('durable') is True:
        returned=str(payload.get('job_id') or body.get('job_id') or '')
        if returned and returned != str(body.get('job_id') or ''):
            return False,False,'Render #2 returned a different job_id',0.0,payload
        return True,False,'',0.0,payload
    if accepted and kind not in {'file','google'}:
        return True,False,'',0.0,payload
    if accepted:
        return False,True,'Render #2 accepted without durable confirmation',2.0,payload
    # Any terminal record for the same durable job is still proof HEAVY owns the job.
    if payload.get('durable') is True and str(payload.get('job_id') or '')==str(body.get('job_id') or '') and status_name in {'failed','closed'}:
        return True,False,'',0.0,payload
    msg=str(payload.get('error') or '')[:400]
    if not msg:
        try:
            raw=str(r.text or '')
            msg='non-JSON response' if '<html' in raw.casefold() else raw[:400]
        except Exception: msg=f'HTTP {status}'
    return False,False,msg or f'HTTP {status}',0.0,payload


def _r38_outbox_enqueue_core(kind,endpoint,body):
    obj=dict(body or {}); jid=str(obj.get('job_id') or __import__('secrets').token_hex(12)).strip()[:80]; obj['job_id']=jid
    existing=_r38_outbox_get(jid)
    if existing and str(existing.get('state') or '') in {'accepted','completed'}:
        return jid
    row=existing if isinstance(existing,dict) else {}
    row.update({'job_id':jid,'kind':str(kind),'endpoint':str(endpoint),'body':_r33_safe_scalar(obj),'state':'pending','created_at':float(row.get('created_at') or _r33_time.time()),'attempts':int(row.get('attempts') or 0),'next_try':_r33_time.time(),'last_error':''})
    if not _r38_outbox_put(row,pending=True):
        raise RuntimeError('FAST durable peer outbox unavailable')
    _R38_OUTBOX_WAKE.set()
    return jid


# R47 FINALIZATION: obsolete pre-R41 outbox dispatcher removed.
def _r38_outbox_loop():
    while True:
        worked=False; now=_r33_time.time()
        for row in _r38_outbox_pending_rows(250):
            if float(row.get('next_try') or 0)>now: continue
            # Jobs are kept for six hours by default. This survives ordinary Render maintenance
            # without turning a genuinely broken configuration into an infinite hidden loop.
            max_age=max(900,min(86400,int(_r33_os.getenv('R38_PEER_JOB_MAX_AGE_SEC','21600') or '21600')))
            if now-float(row.get('created_at') or now)>max_age:
                row.update({'state':'failed','last_error':'Render #2 did not accept the durable job before max age','failed_at':now}); _r38_outbox_put(row,pending=False)
                if str(row.get('kind') or '')=='file': _r35_delivery_set(str(row.get('job_id') or ''),'done_error',{'job_id':row.get('job_id'),'ok':False,'error':row['last_error']},error=row['last_error'])
                continue
            _r38_outbox_dispatch_one(row); worked=True
        _R38_OUTBOX_WAKE.wait(0.25 if worked else 0.8); _R38_OUTBOX_WAKE.clear()


def _r38_worker_file_submit(body:dict):
    # No network on this call. The canonical file runner is already background work;
    # persisting to the outbox is enough to make HEAVY dispatch restart-safe.
    return _r38_outbox_enqueue('file','/internal/export/file',body)

_r7_worker_file_submit = _r38_worker_file_submit


def _r38_wait_remote_delivery(jid,body):
    timeout=max(300,min(21600,int(_r33_os.getenv('R38_FAST_JOB_WAIT_SEC','3600') or '3600')))
    deadline=_r33_time.time()+timeout; last_progress=0.0
    while _r33_time.time()<deadline:
        row=_r35_delivery_get(jid); state=str(row.get('state') or '')
        if state=='done': return True
        if state=='done_error':
            b=row.get('body') if isinstance(row.get('body'),dict) else {}
            raise RuntimeError(str(row.get('error') or b.get('error') or 'Render #2 completed with an error')[:900])
        out=_r38_outbox_get(jid); ostate=str(out.get('state') or '')
        if ostate=='failed': raise RuntimeError(str(out.get('last_error') or 'Render #2 rejected the job')[:900])
        now=_r33_time.time()
        if now-last_progress>15:
            try:
                if ostate in {'pending','retry'}: phase='Render #2 перезапускается — задание сохранено, повторяю'
                elif ostate=='accepted': phase='Render #2 выполняет задачу'
                elif state in {'running','failed'}: phase='получаю результат Render #2'
                else: phase='ожидаю Render #2'
                _file_job_progress(phase,force=True)
            except Exception: pass
            last_progress=now
        _r33_time.sleep(0.5)
    raise RuntimeError(f'Render #2 did not deliver the result within {timeout} sec; job_id={jid}')


def _r33_remote_file_adapter(kind,label,func_name,args,kwargs):
    body=_r33_export_body(str(kind),str(label),str(func_name),args,kwargs); body['front_release']='Пер-R43'
    try: _file_job_progress('сохраняю задание для Render #2',force=True)
    except Exception: pass
    jid=_r38_worker_file_submit(body)
    cur=_r35_delivery_get(jid)
    if str(cur.get('state') or '') not in {'running','done','done_error','accepted'}:
        _r35_delivery_set(jid,'dispatching',{'job_id':jid,'operation':body.get('operation'),'recipient_chat_id':body.get('recipient_chat_id')})
    try: bot_journal('r38_heavy_job_outboxed',int(body.get('recipient_chat_id') or 0),f"kind={kind}; op={body.get('operation')}; job={jid}; revision={body.get('required_revision') or 0}")
    except Exception: pass
    _r38_wait_remote_delivery(jid,body)
    delivery=str(body.get('delivery') or 'chat').lower(); delivered_kind='Telegram через Render #2' if delivery=='chat' else ('Google Sheets' if delivery=='google' else 'Google Drive')
    if not file_job_mark_external_delivery(delivered_kind,jid): raise RuntimeError('R38 delivery confirmed but FAST file-job context was lost')
    return True


def _r38_google_submit_report(title,rows,layout='category',annotations_override=None,include_annotations=True,**kwargs):
    if not _split_env_bool('SPLIT_GOOGLE_REMOTE_ENABLED',True): raise RuntimeError('Google Sheets worker delegation disabled')
    target_chat_id=kwargs.get('target_chat_id'); notify_result=bool(kwargs.get('notify_result',True)); recipient_chat_id=kwargs.get('recipient_chat_id') or target_chat_id
    tid,spreadsheet_id=_split_google_target(target_chat_id=target_chat_id,tenant_id=kwargs.get('tenant_id'))
    annotations=_split_annotations_for_google(rows,str(layout or 'category'),annotations_override,bool(include_annotations))
    encoded={f'{int(r)},{int(c)}':str(note) for (r,c),note in annotations.items() if str(note or '').strip()}
    jid=__import__('secrets').token_hex(12)
    body={'job_id':jid,'title':str(title or 'Статьи')[:300],'rows':rows,'layout':str(layout or 'category'),'annotations':encoded,'include_annotations':bool(include_annotations),'spreadsheet_id':spreadsheet_id,'tenant_id':tid,'target_chat_id':target_chat_id,'recipient_chat_id':recipient_chat_id,'notify_result':notify_result,'front_release':'Пер-R43'}
    _r38_outbox_enqueue('google','/internal/google/sheet',body)
    try:
        _SPLIT_STATE['google_last_attempt']=_r33_time.time(); _SPLIT_STATE['google_last_job']=jid; _SPLIT_STATE['google_last_error']=''
    except Exception: pass
    return 'worker-job:'+jid

_v262_split_google_sheets_create_category_report = _r38_google_submit_report
# R38 must also replace the canonical alias rebound by 89_callback_final/98_split_front.
# Without this, several legacy/scheduled Google paths still call the old synchronous HTTP function.
_google_sheets_create_category_report = _r38_google_submit_report


def _r38_sync_peer_json(method,path,*,json_body=None,timeout=12,max_wait=45,agent='per-r38-front-sync'):
    """Short synchronous control-plane call with the same transient policy as the outbox.

    This is only for user diagnostics/settings such as Google test/info; heavy data jobs
    never use it and always go through the durable outbox.
    """
    deadline=_r33_time.time()+max(5.0,min(120.0,float(max_wait or 45)))
    attempt=0; last='Render #2 unavailable'
    while _r33_time.time()<deadline:
        attempt+=1
        try:
            base=globals().get('_split_peer_base',lambda:'')(); headers_fn=globals().get('_split_headers')
            if not base or not globals().get('_split_secret',lambda:'')():
                raise RuntimeError('Render #2 URL/secret not configured')
            _r38_peer_gate()
            hdr=headers_fn(agent) if callable(headers_fn) else {'X-Peer-Secret':str(_r33_os.getenv('PEER_SHARED_SECRET','') or '')}
            kw={'headers':hdr,'timeout':max(3.0,min(25.0,float(timeout or 12)))}
            if json_body is not None: kw['json']=json_body
            r=requests.request(str(method or 'GET').upper(),base+str(path),**kw)
            transient,cloud,status=_r38_peer_transient_response(r)
            payload={}
            try:
                if r.content and 'json' in str(r.headers.get('content-type','') or '').casefold():
                    x=r.json(); payload=x if isinstance(x,dict) else {}
            except Exception: payload={}
            if not transient:
                return r,payload
            wait=_r38_retry_after(r,attempt); last=('Cloudflare/HTML challenge' if cloud else f'HTTP {status}')
            if _r33_time.time()+wait>=deadline: break
            _r33_time.sleep(min(10.0,wait))
        except Exception as exc:
            last=f'{type(exc).__name__}: {str(exc)[:260]}'
            wait=min(8.0,1.2*(2**min(4,attempt-1)))
            if _r33_time.time()+wait>=deadline: break
            _r33_time.sleep(wait)
    raise RuntimeError(f'Render #2 temporarily unavailable after retry: {last}')


def _r38_tenant_google_test(tenant_id):
    try:
        tid,spreadsheet_id=_split_google_target(tenant_id=str(tenant_id))
        r,payload=_r38_sync_peer_json('POST','/internal/google/test',json_body={'spreadsheet_id':spreadsheet_id,'tenant_id':tid},timeout=18,max_wait=60,agent='per-r38-front-google-test')
        if 200<=int(r.status_code)<300 and payload.get('ok'):
            return True,f"✅ Google Таблица доступна через Render #2.\nНазвание: {payload.get('title') or '—'}\nService account: {payload.get('service_email') or '—'}"
        return False,'❌ Проверка Google: '+str(payload.get('error') or f'HTTP {r.status_code}')[:600]
    except Exception as exc:
        return False,'❌ Проверка Google: '+str(exc)[:600]


def _r38_google_worker_info(fetch=True):
    # Preserve R7 cache semantics but do not let a short Render restart surface as HTML/503.
    cache=globals().get('_R7_GOOGLE_INFO_CACHE')
    now=_r33_time.time(); cached=dict((cache or {}).get('data') or {}) if isinstance(cache,dict) else {}
    if cached and (not fetch or now-float((cache or {}).get('ts') or 0)<600): return cached
    if not fetch:return cached
    try:
        r,payload=_r38_sync_peer_json('GET','/internal/google/info',timeout=8,max_wait=30,agent='per-r38-front-google-info')
        if 200<=int(r.status_code)<300 and payload.get('ok'):
            if isinstance(cache,dict): cache.update(ts=now,data=dict(payload))
            return dict(payload)
    except Exception: pass
    return cached

tenant_google_test = _r38_tenant_google_test
_r7_google_worker_info = _r38_google_worker_info


def _r38_google_result_handler():
    if not globals().get('_split_authorized_request',lambda:False)(): return ({'ok':False},404)
    body=request.get_json(silent=True) or {}; jid=str(body.get('job_id') or '').strip()
    if not jid:return ({'ok':False,'error':'job_id required'},400)
    out=_r38_outbox_get(jid)
    if str(out.get('result_state') or '')=='done': return ({'ok':True,'duplicate':True,'delivered':True},200)
    try: cid=int(body.get('recipient_chat_id') or 0)
    except Exception: cid=0
    if not cid:return ({'ok':False,'error':'recipient_chat_id required'},400)
    try:
        if bool(body.get('notify_result',True)):
            if bool(body.get('ok')):
                text=f"✅ 📊 Google Excel готов\n{str(body.get('title') or 'Google Excel')[:180]}\n\n{str(body.get('url') or '').strip()}"
                bot.send_message(cid,text,disable_web_page_preview=True)
            else:
                err=str(body.get('error') or 'Render #2 завершил Google-задачу с ошибкой')[:700]
                bot.send_message(cid,'❌ Google Excel не создан на Render #2:\n'+err)
        out=out if isinstance(out,dict) else {'job_id':jid,'kind':'google'}
        out.update({'job_id':jid,'state':'completed','result_state':'done','result_ok':bool(body.get('ok')),'result_url':str(body.get('url') or ''),'result_title':str(body.get('title') or ''),'result_at':_r33_time.time(),'last_error':str(body.get('error') or '')[:500]})
        _r38_outbox_put(out,pending=False)
        try:
            if body.get('ok'):_SPLIT_STATE['google_last_ok']=_r33_time.time(); _SPLIT_STATE['google_last_error']=''
            else:_SPLIT_STATE['google_last_error']=str(body.get('error') or '')[:240]
        except Exception: pass
        return ({'ok':True,'delivered':True},200)
    except Exception as exc:
        return ({'ok':False,'error':f'{type(exc).__name__}: {str(exc)[:300]}'},503)

try: app.view_functions['split_front_google_result_v262']=_r38_google_result_handler
except Exception: pass


def _r38_post_events(events,wire,large=False):
    """R32/R34 frozen-event sender using the same peer congestion gate as user jobs."""
    base=globals().get('_r32_peer_base_impl',lambda:'')(); secret=str(_r33_os.getenv('PEER_SHARED_SECRET','') or '').strip()
    if not base or not secret: raise RuntimeError('R38 peer URL/secret not configured')
    endpoint='/internal/state/event-large' if large else '/internal/state/events'
    _r38_peer_gate()
    r=requests.post(base+endpoint,data=wire,headers={'X-Peer-Secret':secret,'User-Agent':'per-r38-state-events','Content-Type':'application/json','Content-Encoding':'gzip'},timeout=max(2.0,min(30.0,float(_r33_os.getenv('R32_EVENT_POST_TIMEOUT_SEC','8') or '8'))))
    transient,cloud,status=_r38_peer_transient_response(r)
    if status==413 and not large:
        if len(events)>1:
            mid=max(1,len(events)//2); _r38_post_events(events[:mid],_r34_encode_events(events[:mid]),False); _r38_post_events(events[mid:],_r34_encode_events(events[mid:]),False); return True
        return _r38_post_events(events,wire,True)
    if transient:
        wait=_r38_retry_after(r,1)
        global _R38_PEER_BLOCK_UNTIL
        with _R38_PEER_HTTP_LOCK:_R38_PEER_BLOCK_UNTIL=max(float(_R38_PEER_BLOCK_UNTIL or 0.0),_r33_time.time()+min(wait,15.0))
        raise RuntimeError(('Cloudflare/HTML challenge' if cloud else f'HEAVY state events HTTP {status}'))
    if not (200<=status<300):
        payload={}
        try:payload=r.json() if r.content and 'json' in str(r.headers.get('content-type','') or '').casefold() else {}
        except Exception:payload={}
        raise RuntimeError('HEAVY state events '+str(payload.get('error') or f'HTTP {status}')[:300])
    payload={}
    try:
        x=r.json() if r.content else {}; payload=x if isinstance(x,dict) else {}
    except Exception:payload={}
    # With no Redis on HEAVY every durable state batch is a synchronous MEGA write.
    # Pace the next peer request so background state mirroring cannot starve user jobs.
    if str(payload.get('durable') or '')=='mega-direct':
        try:
            gap=max(0.2,min(5.0,float(_r33_os.getenv('R38_MEGA_EVENT_MIN_GAP_SEC','1.0') or '1.0')))
            with _R38_PEER_HTTP_LOCK:
                _R38_PEER_BLOCK_UNTIL=max(float(_R38_PEER_BLOCK_UNTIL or 0.0),_r33_time.time()+gap)
        except Exception:pass
    ack=int(payload.get('durable_revision') or payload.get('max_revision') or max([int(x.get('revision') or 0) for x in events] or [0]))
    applied_ack=int(payload.get('applied_revision') or (ack if bool(payload.get('apply_ok',True)) else 0))
    evstate=globals().get('_R32_EVENT_STATE')
    if isinstance(evstate,dict):
        evstate['last_revision_acked']=max(int(evstate.get('last_revision_acked') or 0),ack); evstate['last_revision_applied_peer']=max(int(evstate.get('last_revision_applied_peer') or 0),applied_ack)
        evstate['sent']=int(evstate.get('sent') or 0)+len(events); evstate['batches']=int(evstate.get('batches') or 0)+1; evstate['bytes']=int(evstate.get('bytes') or 0)+len(wire); evstate['last_ok']=_r33_time.time(); evstate['last_error']=''
    st=globals().get('_SPLIT_STATE')
    if isinstance(st,dict):
        st['r32_event_sent']=int(st.get('r32_event_sent') or 0)+len(events); st['r32_event_batches']=int(st.get('r32_event_batches') or 0)+1; st['r32_event_bytes']=int(st.get('r32_event_bytes') or 0)+len(wire); st['r32_event_pending']=globals().get('_R32_EVENT_Q').qsize() if globals().get('_R32_EVENT_Q') is not None else 0; st['r32_event_last_ok']=_r33_time.time(); st['r32_event_last_error']=''; st['r34_event_last_revision_acked']=ack; st['r35_event_last_revision_applied_peer']=applied_ack
    return True

_r34_post_events = _r38_post_events


def _r38_deliver_worker_export(body):
    """Fetch/deliver a ready HEAVY result without treating Render/Cloudflare turbulence as final."""
    jid=str(body.get('job_id') or ''); cid=int(body.get('recipient_chat_id') or 0)
    if not jid or not cid:return False
    try:
        if not body.get('ok'):
            bot.send_message(cid,'❌ Экспорт Render #2: '+str(body.get('error') or 'неизвестная ошибка')[:800]); return True
        delivery=str(body.get('delivery') or '')
        if delivery=='drive':
            bot.send_message(cid,f"☁️ Google Drive · {body.get('label') or ''}: {body.get('chat_name') or ''}\n\n{body.get('url') or ''}",disable_web_page_preview=True); return True
        if delivery=='google':
            if body.get('url'):bot.send_message(cid,f"✅ Google Excel готов.\n{body.get('url')}",disable_web_page_preview=True)
            return True
        deadline=_r33_time.time()+max(60,min(900,int(_r33_os.getenv('R38_RESULT_FETCH_WINDOW_SEC','420') or '420'))); attempt=0; response=None
        while _r33_time.time()<deadline:
            attempt+=1; _r35_delivery_set(jid,'running',body)
            try:
                base=globals().get('_split_peer_base',lambda:'')(); headers_fn=globals().get('_split_headers'); _r38_peer_gate()
                hdr=headers_fn('per-r38-front-export-fetch') if callable(headers_fn) else {'X-Peer-Secret':str(_r33_os.getenv('PEER_SHARED_SECRET','') or '')}
                r=requests.get(base+'/internal/export/file/'+jid,headers=hdr,timeout=60,stream=True)
                transient,cloud,status=_r38_peer_transient_response(r)
                if status==200:
                    response=r; break
                if status in {404,409,425} or transient:
                    wait=_r38_retry_after(r,attempt); _r33_time.sleep(min(15.0,wait)); continue
                raise RuntimeError(f'worker file HTTP {status}: '+str(getattr(r,'text','') or '')[:240])
            except Exception as exc:
                if _r33_time.time()+2>=deadline:raise
                _r33_time.sleep(min(15.0,max(1.0,1.3*(2**min(4,attempt-1)))))
        if response is None:raise RuntimeError('Render #2 result fetch retry window expired')
        import tempfile as _r38_tempfile, os as _r38_os
        suffix=_r38_os.path.splitext(str(body.get('filename') or 'export.bin'))[1]; tmp=_r38_tempfile.NamedTemporaryFile(prefix='r38_export_',suffix=suffix,delete=False)
        try:
            for chunk in response.iter_content(chunk_size=256*1024):
                if chunk:tmp.write(chunk)
            tmp.close()
            with open(tmp.name,'rb') as fobj:
                caption=str(body.get('caption') or '') or f"📂 {body.get('label') or 'Файл'}: {body.get('chat_name') or ''}"
                _tg_call_retry(bot.send_document,cid,fobj,caption=caption,timeout=120,purpose='r38_worker_export_send_document')
        finally:
            try:_r38_os.unlink(tmp.name)
            except Exception:pass
        return True
    except Exception as exc:
        try:log_error(f'R38 export delivery {jid}: {type(exc).__name__}: {str(exc)[:500]}')
        except Exception:pass
        return False

_r7_deliver_worker_export = _r38_deliver_worker_export


def _r38_export_delivery_task_core(body):
    jid=str(body.get('job_id') or ''); delivered=False
    try:delivered=bool(_r38_deliver_worker_export(dict(body)))
    except Exception as exc:_r35_delivery_set(jid,'failed',body,error=f'{type(exc).__name__}: {str(exc)[:700]}'); return
    if delivered:
        if bool(body.get('ok')):_r35_delivery_set(jid,'done',body)
        else:_r35_delivery_set(jid,'done_error',body,error=str(body.get('error') or 'HEAVY job failed'))
    else:_r35_delivery_set(jid,'failed',body,error='FAST delivery attempt failed')


def _r38_export_result_handler():
    if not globals().get('_split_authorized_request',lambda:False)():return ({'ok':False},404)
    body=request.get_json(silent=True) or {}; jid=str(body.get('job_id') or '')
    if not jid:return ({'ok':False,'error':'job_id required'},400)
    row=_r35_delivery_get(jid); state=str(row.get('state') or ''); age=max(0.0,_r33_time.time()-float(row.get('ts') or 0))
    if state in {'done','done_error'}:return ({'ok':True,'delivered':True,'duplicate':True,'operation_ok':state=='done'},200)
    if state=='running' and age<180:return ({'ok':True,'accepted':True,'delivered':False},202)
    _r35_delivery_set(jid,'running',body)
    _r38_threading.Thread(target=_r38_export_delivery_task,args=(dict(body),),daemon=True,name='per-r38-front-delivery').start()
    return ({'ok':True,'accepted':True,'delivered':False},202)

try:app.view_functions['split_front_export_result_r7']=_r38_export_result_handler
except Exception:pass


# ---------------- Пер-R43 semantic single-flight / duplicate collapse ----------------
# R38 made transport durable, but a backlog could still contain several different job_id
# values for the same user action.  After a HEAVY restart they were dispatched together.
# Full-state exports are memory-heavy, so this could create three simultaneous snapshots.
import hashlib as _r39_hashlib
import threading as _r39_threading

_R39_SIG_LOCK = _r39_threading.RLock()
_R39_SIG_ACTIVE = {}


def _r39_job_signature(kind, endpoint, body):
    b = body if isinstance(body, dict) else {}
    # Only semantic fields.  Exclude job_id/revision/snapshots/timestamps so repeated taps
    # for the same requested artifact collapse to one durable execution.
    keys = (
        'operation','recipient_chat_id','target_chat_id','scope','tenant_id','tenant_chat_ids',
        'mode','day_key','start_key','start_rid','end_key','end_rid','source_file_type','file_type',
        'delivery','limit','start_dt','end_dt','spreadsheet_id','drive_folder_id','title','layout'
    )
    core = {'kind': str(kind or ''), 'endpoint': str(endpoint or '')}
    for k in keys:
        if k in b:
            core[k] = _r33_safe_scalar(b.get(k))
    # Legacy/future operations can carry their arguments only in args/kwargs.
    if 'args' in b: core['args'] = _r33_safe_scalar(b.get('args'))
    if 'kwargs' in b: core['kwargs'] = _r33_safe_scalar(b.get('kwargs'))
    raw = _r33_json.dumps(core, ensure_ascii=False, sort_keys=True, separators=(',',':'), default=str)
    return _r39_hashlib.sha256(raw.encode('utf-8','replace')).hexdigest()


def _r39_delivery_terminal(jid):
    try:
        st = str((_r35_delivery_get(jid) or {}).get('state') or '')
        return st in {'done','done_error'}
    except Exception:
        return False


def _r38_outbox_enqueue(kind, endpoint, body):
    obj = dict(body or {})
    if str(kind or '') in {'file','google'}:
        backend = _r41_front_outbox_backend() if '_r41_front_outbox_backend' in globals() else ''
        obj['front_outbox_durable'] = bool(backend)
        obj['front_outbox_backend'] = backend or 'local'
        obj['front_release'] = 'Пер-R43'
    sig = _r39_job_signature(kind, endpoint, obj)
    now = _r33_time.time()
    # Fast in-process single-flight: repeated callback taps reuse the same job_id.
    with _R39_SIG_LOCK:
        row = _R39_SIG_ACTIVE.get(sig) or {}
        jid0 = str(row.get('job_id') or '')
        if jid0 and now - float(row.get('ts') or 0) < 900 and not _r39_delivery_terminal(jid0):
            out = _r38_outbox_get(jid0) or {}
            if str(out.get('state') or '') not in {'failed','superseded'}:
                return jid0
    # Cross-restart collapse: inspect durable pending rows from Redis/local outbox.
    candidates = []
    try:
        for r in _r38_outbox_pending_rows_core(500):
            if not isinstance(r, dict):
                continue
            rb=r.get('body') if isinstance(r.get('body'),dict) else {}
            # R42 release barrier: never reuse a canonical job_id from R39-R41.
            # Those rows may represent already-delivered work whose HEAVY MEGA witness
            # survived a container replacement. New R42 actions always get an R42 job.
            if str(rb.get('front_release') or '') != 'Пер-R43':
                continue
            if now - float(r.get('created_at') or now) > 900:
                continue
            if _r39_job_signature(r.get('kind'), r.get('endpoint'), rb) == sig:
                candidates.append(r)
    except Exception:
        candidates = []
    if candidates:
        # Deterministic canonical id: both FAST and HEAVY choose the lexicographically
        # smallest job_id.  Keep the newest payload/revision under that id.
        canonical = min(candidates, key=lambda x: str((x or {}).get('job_id') or '~'))
        newest = max(candidates + [{'body':obj,'created_at':now}], key=lambda x: (int(((x.get('body') or {}).get('required_revision') or 0)), float(x.get('created_at') or 0)))
        jid0 = str(canonical.get('job_id') or '')
        if jid0:
            try:
                merged=dict(canonical); merged['body']=dict(newest.get('body') or obj); merged['body']['job_id']=jid0; merged['state']='pending'; merged['next_try']=min(float(merged.get('next_try') or now),now); merged['last_error']=''
                _r38_outbox_put(merged,pending=True)
            except Exception: pass
            with _R39_SIG_LOCK:
                _R39_SIG_ACTIVE[sig] = {'job_id': jid0, 'ts': now}
            return jid0
    jid = _r38_outbox_enqueue_core(kind, endpoint, obj)
    with _R39_SIG_LOCK:
        _R39_SIG_ACTIVE[sig] = {'job_id': str(jid), 'ts': now}
    return jid


def _r38_outbox_pending_rows(limit=250):
    rows = list(_r38_outbox_pending_rows_core(max(int(limit or 0), 500)) or [])
    grouped = {}
    passthrough = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        rb=row.get('body') if isinstance(row.get('body'),dict) else {}
        if str(rb.get('front_release') or '') != 'Пер-R43':
            # One-time deploy barrier. Old pending peer jobs are superseded instead of
            # being replayed forever after every HEAVY restart.
            try:
                oldrow=dict(row); oldrow.update({'state':'superseded','superseded_by':'R42-release-barrier','updated_at':_r33_time.time(),'last_error':'R42 dropped stale pending job from '+str(rb.get('front_release') or 'legacy')})
                _r38_outbox_put(oldrow,pending=False)
            except Exception:
                pass
            continue
        try:
            sig = _r39_job_signature(row.get('kind'), row.get('endpoint'), rb)
        except Exception:
            passthrough.append(row); continue
        cur = grouped.get(sig)
        if cur is None:
            grouped[sig] = row; continue
        # Deterministic canonical id across deploys.  Merge the newest requested revision
        # into the smallest job_id so HEAVY recovery makes the same choice.
        keep, drop = (row, cur) if str(row.get('job_id') or '~') < str(cur.get('job_id') or '~') else (cur, row)
        newest = max((row,cur), key=lambda x:(int(((x.get('body') or {}).get('required_revision') or 0)),float(x.get('created_at') or 0)))
        keep=dict(keep); keep['body']=dict(newest.get('body') or keep.get('body') or {}); keep['body']['job_id']=str(keep.get('job_id') or '')
        grouped[sig]=keep
        try:
            _r38_outbox_put(keep,pending=True)
            drop = dict(drop); drop.update({'state':'superseded','superseded_by':str(keep.get('job_id') or ''),'updated_at':_r33_time.time()})
            _r38_outbox_put(drop, pending=False)
        except Exception:
            pass
    out = passthrough + list(grouped.values())
    out.sort(key=lambda x: float((x or {}).get('created_at') or 0))
    return out[:max(1, int(limit or 250))]


# Replace the functions used dynamically by the already-defined dispatcher loop.

# Clear the in-process semantic latch when the canonical delivery reaches a terminal state.
def _r38_export_delivery_task(body):
    jid = str((body or {}).get('job_id') or '')
    try:
        result = _r38_export_delivery_task_core(body)
        return result
    finally:
        if jid:
            try:
                if _r39_delivery_terminal(jid):
                    out=_r38_outbox_get(jid) or {'job_id':jid,'kind':'file'}
                    out.update({'state':'completed','result_state':'done','provisional':False,'completed_at':_r33_time.time(),'last_error':''})
                    _r38_outbox_put(out,pending=False)
            except Exception:
                pass
            with _R39_SIG_LOCK:
                for sig, row in list(_R39_SIG_ACTIVE.items()):
                    if str((row or {}).get('job_id') or '') == jid and _r39_delivery_terminal(jid):
                        _R39_SIG_ACTIVE.pop(sig, None)

try:
    bot_journal('r39_singleflight_loaded', int(OWNER_ID or 0), 'semantic heavy-job dedupe; stale outbox collapse; same job_id for repeated taps')
except Exception:
    pass

# R47 FINALIZATION: outbox thread starts only after all final owners are defined.


# ---------------------------------------------------------------------------
# Пер-R43: true asynchronous FAST<->HEAVY supervision.
# Heavy file jobs no longer occupy EXPORT_TASK_POOL while waiting minutes for HEAVY.
# FAST persists the peer job, returns the UI handler immediately, and a tiny supervisor
# thread follows canonical/duplicate jobs until the real Telegram/Google delivery ACK.
_R40_SUP_LOCK = _r38_threading.RLock()
_R40_SUPERVISORS = {}


def _r40_canonical_job_id(jid):
    cur=str(jid or '')[:80]; seen=set()
    for _ in range(8):
        if not cur or cur in seen: break
        seen.add(cur)
        row=_r35_delivery_get(cur) or {}
        body=row.get('body') if isinstance(row.get('body'),dict) else {}
        nxt=str(body.get('canonical_job_id') or body.get('duplicate_of') or row.get('canonical_job_id') or row.get('duplicate_of') or '')[:80]
        if not nxt:
            out=_r38_outbox_get(cur) or {}
            nxt=str(out.get('canonical_job_id') or out.get('duplicate_of') or '')[:80]
        if not nxt or nxt==cur: break
        cur=nxt
    return cur or str(jid or '')[:80]


def _r40_export_result_handler():
    if not globals().get('_split_authorized_request',lambda:False)(): return ({'ok':False},404)
    body=request.get_json(silent=True) or {}; jid=str(body.get('job_id') or '')[:80]
    if not jid: return ({'ok':False,'error':'job_id required'},400)
    canonical=str(body.get('canonical_job_id') or body.get('duplicate_of') or '')[:80]
    if canonical and canonical!=jid:
        _r35_delivery_set(jid,'alias',{'job_id':jid,'canonical_job_id':canonical,'duplicate_of':canonical,'operation':body.get('operation'),'recipient_chat_id':body.get('recipient_chat_id')})
        return ({'ok':True,'delivered':True,'alias':True,'canonical_job_id':canonical},200)
    return _r38_export_result_handler()

try: app.view_functions['split_front_export_result_r7']=_r40_export_result_handler
except Exception: pass


def _r40_status_edit(chat_id,msg_id,text,purpose='r40_file_status'):
    if not msg_id: return
    try:
        fn=globals().get('_tg_call_retry')
        if callable(fn): fn(bot.edit_message_text,text,chat_id=int(chat_id),message_id=int(msg_id),purpose=purpose)
        else: bot.edit_message_text(text,chat_id=int(chat_id),message_id=int(msg_id))
    except Exception: pass


def _r40_status_delete_later(chat_id,msg_id,delay):
    try:
        fn=globals().get('_v161_schedule_delete') or globals().get('_v160_schedule_delete')
        if callable(fn): fn(int(chat_id),int(msg_id),float(delay),'r40-heavy-close'); return
    except Exception: pass
    def _delete():
        try: bot.delete_message(int(chat_id),int(msg_id))
        except Exception: pass
    try: _r38_threading.Timer(float(delay),_delete).start()
    except Exception: pass


def _r40_status_text(label,elapsed,phase,final=None):
    if final=='ok': return f'✅ {label}\nОтправлено за {elapsed}.\nОкно закроется через 15с.'
    if final=='error': return f'⚠️ {label}\nЗавершено за {elapsed}.\n{phase[:600]}\nОкно закроется через 15с.'
    return f'⏳ Выполнение · {label}\n\nВремя: {elapsed}\n\nЭтап: {phase}\n\nПосле завершения закроется через 15с.'


def _r40_elapsed(started):
    sec=max(0,int(_r33_time.time()-float(started or _r33_time.time())))
    return f'{sec//60}:{sec%60:02d}'


def _r40_supervise_remote(jid,body,label,chat_id,msg_id):
    original=str(jid or '')[:80]; started=_r33_time.time(); last_ui=0.0; timeout=max(300,min(21600,int(_r33_os.getenv('R40_FAST_JOB_WAIT_SEC','3600') or '3600'))); deadline=started+timeout
    err=''; ok=False
    try:
        while _r33_time.time()<deadline:
            canonical=_r40_canonical_job_id(original)
            row=_r35_delivery_get(canonical) or {}; state=str(row.get('state') or '')
            if state=='done': ok=True; break
            if state=='done_error':
                b=row.get('body') if isinstance(row.get('body'),dict) else {}
                err=str(row.get('error') or b.get('error') or 'Render #2 завершил задачу с ошибкой')[:900]; break
            out=_r38_outbox_get(original) or {}; ostate=str(out.get('state') or '')
            if ostate=='failed': err=str(out.get('last_error') or 'Render #2 отклонил задание')[:900]; break
            now=_r33_time.time()
            if now-last_ui>=12.0:
                if canonical!=original: phase=f'Render #2 объединил дубль с заданием {canonical[:12]}…'
                elif ostate in {'pending','retry'}: phase='Render #2 недоступен — запрос сохранён, повторяю автоматически'
                elif ostate=='accepted' and state in {'running','accepted','dispatching',''}: phase='Render #2 выполняет задачу'
                elif state in {'running','failed'}: phase='получаю и отправляю готовый результат'
                else: phase='ожидаю подтверждение Render #2'
                _r40_status_edit(chat_id,msg_id,_r40_status_text(label,_r40_elapsed(started),phase),'r40_file_progress')
                last_ui=now
            _r33_time.sleep(0.5)
        else: err=f'Render #2 не подтвердил доставку за {timeout} сек.; job_id={original}'
    except Exception as exc:
        err=f'{type(exc).__name__}: {str(exc)[:800]}'
    elapsed=_r40_elapsed(started)
    if ok:
        _r40_status_edit(chat_id,msg_id,_r40_status_text(label,elapsed,'',final='ok'),'r40_file_done')
    else:
        _r40_status_edit(chat_id,msg_id,_r40_status_text(label,elapsed,err or 'нет подтверждения доставки',final='error'),'r40_file_error')
        try: log_error(f'R40 async HEAVY job {original}: {err}')
        except Exception: pass
    _r40_status_delete_later(chat_id,msg_id,15)
    with _R40_SUP_LOCK: _R40_SUPERVISORS.pop(original,None)


def _r40_submit_heavy_file(chat_id,kind,label,func,*args,**kwargs):
    chat_id=int(chat_id); kind_s=str(kind or 'file'); fname=str(getattr(func,'__name__','') or '')
    try:
        body=_r33_export_body(kind_s,str(label),fname,args,kwargs); body['front_release']='Пер-R43'
        jid=_r38_worker_file_submit(body); body['job_id']=str(jid)
    except Exception as exc:
        detail=f'{type(exc).__name__}: {str(exc)[:500]}'
        try: send_and_auto_delete(chat_id,'⚠️ Не удалось сохранить задание для Render #2: '+detail,15)
        except Exception: pass
        return (False,detail)
    with _R40_SUP_LOCK:
        existing=_R40_SUPERVISORS.get(str(jid))
        if isinstance(existing,dict) and existing.get('thread') is not None and existing['thread'].is_alive():
            return (True,'Уже выполняется')
    msg_id=0
    try:
        text=_r40_status_text(str(label),'0:00','задание надёжно сохранено, передаю Render #2')
        fn=globals().get('_tg_call_retry')
        m=fn(bot.send_message,chat_id,text,purpose='r40_file_status_create') if callable(fn) else bot.send_message(chat_id,text)
        msg_id=int(getattr(m,'message_id',0) or 0)
    except Exception: msg_id=0
    t=_r38_threading.Thread(target=_r40_supervise_remote,args=(str(jid),dict(body),str(label),chat_id,msg_id),daemon=True,name='per-r40-heavy-supervisor-'+str(jid)[:8])
    with _R40_SUP_LOCK: _R40_SUPERVISORS[str(jid)]={'thread':t,'chat_id':chat_id,'message_id':msg_id,'label':str(label),'created_at':_r33_time.time()}
    t.start()
    try: bot_journal('r40_heavy_async_outboxed',chat_id,f'kind={kind_s}; op={body.get("operation")}; job={jid}; revision={body.get("required_revision") or 0}')
    except Exception: pass
    return (True,'Запущено')


def submit_interactive_file_job(chat_id:int,kind:str,label:str,func,*args,**kwargs):
    kind_s=str(kind or 'file'); heavy=(kind_s in _R33_HEAVY_FILE_KINDS or kind_s.startswith('window_'))
    if heavy: return _r40_submit_heavy_file(chat_id,kind_s,label,func,*args,**kwargs)
    return _LOCAL_SUBMIT_FILE_JOB(chat_id,kind,label,func,*args,**kwargs) if callable(_LOCAL_SUBMIT_FILE_JOB) else (False,'Экспорт недоступен')

submit_interactive_file_job = submit_interactive_file_job

try:
    bot_journal('r40_unified_transport_loaded',int(OWNER_ID or 0),'async FAST supervisor; canonical alias follow; per-job status; no EXPORT_TASK_POOL wait; window revision fence')
except Exception: pass


# R40 query-only Google helper for scheduled/legacy paths. FAST sends only period
# boundaries and a revision fence; HEAVY reconstructs category rows from its mirror.
def _r40_google_query_submit(title,target_chat_id,start_key,end_key,start_rid=0,end_rid=0,layout='category',include_annotations=True,notify_result=False,recipient_chat_id=None):
    target_chat_id=int(target_chat_id); recipient_chat_id=int(recipient_chat_id or target_chat_id)
    tid,spreadsheet_id=_split_google_target(target_chat_id=target_chat_id,tenant_id=None)
    jid=__import__('secrets').token_hex(12)
    try: required=int((_R32_EVENT_STATE or {}).get('last_revision_queued') or 0)
    except Exception: required=0
    body={'job_id':jid,'operation':'google_exact_query','title':str(title or 'Статьи')[:300],'layout':str(layout or 'category'),'include_annotations':bool(include_annotations),'spreadsheet_id':spreadsheet_id,'tenant_id':tid,'target_chat_id':target_chat_id,'recipient_chat_id':recipient_chat_id,'notify_result':bool(notify_result),'start_key':str(start_key or '')[:10],'start_rid':int(start_rid or 0),'end_key':str(end_key or '')[:10],'end_rid':int(end_rid or 0),'required_revision':required,'front_release':'Пер-R43'}
    jid2=_r38_outbox_enqueue('google','/internal/google/sheet',body)
    return str(jid2)


def _r40_google_wait(jid,timeout=900):
    deadline=_r33_time.time()+max(30,min(3600,int(timeout or 900)))
    while _r33_time.time()<deadline:
        row=_r38_outbox_get(str(jid)) or {}
        if str(row.get('result_state') or '')=='done':
            return bool(row.get('result_ok')),str(row.get('result_url') or ''),str(row.get('last_error') or '')
        if str(row.get('state') or '')=='failed': return False,'',str(row.get('last_error') or 'Google job dispatch failed')
        _r33_time.sleep(0.5)
    return False,'',f'Google job timeout {int(timeout)} sec'

_r40_google_query_submit = _r40_google_query_submit
_r40_google_wait = _r40_google_wait


# ---------------------------------------------------------------------------
# Пер-R43: two-phase FAST-owned durable admission.
# When HEAVY has no Redis, synchronous MEGA admission can take much longer than
# the FAST HTTP timeout.  FAST already owns a Redis-backed durable outbox, so a
# live HEAVY may start the same idempotent job immediately while FAST keeps the
# request pending until the real result callback.  A HEAVY crash therefore never
# loses the request: the same job_id is sent again by FAST.

def _r41_front_outbox_backend():
    try:
        c = _r38_outbox_redis_client()
        if c is not None:
            # A lightweight ping prevents advertising front durability when the
            # client exists but the service is currently unreachable.
            try:
                if bool(c.ping()):
                    return 'redis'
            except Exception:
                return ''
    except Exception:
        pass
    return ''


# R47 FINALIZATION: durability metadata is merged into _r39_outbox_enqueue.
def _r38_outbox_dispatch_one(row):
    """Dispatch one peer job while treating HEAVY provisional admission as healthy.

    A provisional response means HEAVY accepted/queued the idempotent job using
    FAST's Redis outbox as the durable authority.  Keep the row pending so a HEAVY
    restart causes automatic replay, but never tell the user that Render #2 is down.
    """
    jid = str((row or {}).get('job_id') or '')
    if not jid:
        return
    try:
        ok, transient, detail, wait, payload = _r38_peer_attempt(row)
        provisional = bool(isinstance(payload, dict) and payload.get('provisional') and payload.get('ok') is True)
        if provisional and str(row.get('kind') or '') in {'file','google'}:
            attempts = int(row.get('attempts') or 0) + 1
            canonical=str(payload.get('canonical_job_id') or payload.get('duplicate_of') or '')[:80]
            row.update({
                'state':'retry', 'provisional':True, 'peer_accepted':True,
                'peer_status':str(payload.get('status') or 'queued'),
                'durable_backend':str(payload.get('durable_backend') or 'front-redis'),
                'attempts':attempts, 'last_error':'',
                'next_try':_r33_time.time()+max(8.0, min(30.0, float(_r33_os.getenv('R41_PROVISIONAL_REPLAY_SEC','15') or '15'))),
                'provisional_at':float(row.get('provisional_at') or _r33_time.time()),
            })
            if canonical and canonical!=jid: row['canonical_job_id']=canonical
            _r38_outbox_put(row, pending=True)
            _R38_PEER_STATE['accepted']=int(_R38_PEER_STATE.get('accepted') or 0)+1
            _R38_PEER_STATE['last_ok']=_r33_time.time(); _R38_PEER_STATE['last_error']=''
            if str(row.get('kind') or '')=='file':
                cur=_r35_delivery_get(jid) or {}
                if canonical and canonical!=jid:
                    _r35_delivery_set(jid,'alias',{'job_id':jid,'canonical_job_id':canonical,'duplicate_of':canonical,'operation':(row.get('body') or {}).get('operation'),'recipient_chat_id':(row.get('body') or {}).get('recipient_chat_id'),'provisional':True})
                elif str(cur.get('state') or '') not in {'running','done','done_error'}:
                    _r35_delivery_set(jid,'accepted',{'job_id':jid,'operation':(row.get('body') or {}).get('operation'),'recipient_chat_id':(row.get('body') or {}).get('recipient_chat_id'),'provisional':True})
            return
        if ok:
            canonical=str(payload.get('canonical_job_id') or payload.get('duplicate_of') or '')[:80]
            row.update({'state':'accepted','accepted_at':_r33_time.time(),'last_error':'','provisional':False,'peer_accepted':True,'peer_status':str(payload.get('status') or ''),'durable_backend':str(payload.get('durable_backend') or '')})
            if canonical and canonical!=jid: row['canonical_job_id']=canonical
            _r38_outbox_put(row,pending=False); _R38_PEER_STATE['accepted']=int(_R38_PEER_STATE.get('accepted') or 0)+1; _R38_PEER_STATE['last_ok']=_r33_time.time(); _R38_PEER_STATE['last_error']=''
            if str(row.get('kind') or '')=='file':
                cur=_r35_delivery_get(jid) or {}
                if canonical and canonical!=jid:
                    _r35_delivery_set(jid,'alias',{'job_id':jid,'canonical_job_id':canonical,'duplicate_of':canonical,'operation':(row.get('body') or {}).get('operation'),'recipient_chat_id':(row.get('body') or {}).get('recipient_chat_id')})
                elif str(cur.get('state') or '') not in {'running','done','done_error'}:
                    _r35_delivery_set(jid,'accepted',{'job_id':jid,'operation':(row.get('body') or {}).get('operation'),'recipient_chat_id':(row.get('body') or {}).get('recipient_chat_id')})
            return
        attempts=int(row.get('attempts') or 0)+1; row['attempts']=attempts; row['last_error']=str(detail or '')[:500]; row['provisional']=False
        _R38_PEER_STATE['last_error']=row['last_error']
        if transient:
            row['state']='retry'; row['next_try']=_r33_time.time()+max(0.8,float(wait or 1.0)); _R38_PEER_STATE['retries']=int(_R38_PEER_STATE.get('retries') or 0)+1; _r38_outbox_put(row,pending=True)
        else:
            row['state']='failed'; row['failed_at']=_r33_time.time(); _r38_outbox_put(row,pending=False)
            if str(row.get('kind') or '')=='file': _r35_delivery_set(jid,'done_error',{'job_id':jid,'ok':False,'error':'Render #2 rejected job: '+row['last_error']},error=row['last_error'])
    except Exception as exc:
        attempts=int(row.get('attempts') or 0)+1; delay=min(60.0,max(1.0,1.25*(2**min(5,attempts-1))))+_r38_random.uniform(0,1.0)
        row.update({'state':'retry','provisional':False,'attempts':attempts,'next_try':_r33_time.time()+delay,'last_error':f'{type(exc).__name__}: {str(exc)[:420]}'})
        _R38_PEER_STATE['last_error']=row['last_error']; _R38_PEER_STATE['retries']=int(_R38_PEER_STATE.get('retries') or 0)+1; _r38_outbox_put(row,pending=True)



# R47 FINALIZATION: delivery completion is handled by the sole _r38_export_delivery_task owner.


# R40's R39 latch wrapper was installed before this patch.  It resolves
# _r38_export_delivery_task dynamically, so the R41 completion hook is canonical.


def _r41_supervise_remote(jid,body,label,chat_id,msg_id):
    original=str(jid or '')[:80]; started=_r33_time.time(); last_ui=0.0; timeout=max(300,min(21600,int(_r33_os.getenv('R40_FAST_JOB_WAIT_SEC','3600') or '3600'))); deadline=started+timeout
    err=''; ok=False
    try:
        while _r33_time.time()<deadline:
            canonical=_r40_canonical_job_id(original)
            row=_r35_delivery_get(canonical) or {}; state=str(row.get('state') or '')
            if state=='done': ok=True; break
            if state=='done_error':
                b=row.get('body') if isinstance(row.get('body'),dict) else {}
                err=str(row.get('error') or b.get('error') or 'Render #2 завершил задачу с ошибкой')[:900]; break
            out=_r38_outbox_get(original) or {}; ostate=str(out.get('state') or '')
            if ostate=='failed': err=str(out.get('last_error') or 'Render #2 отклонил задание')[:900]; break
            now=_r33_time.time()
            if now-last_ui>=12.0:
                if canonical!=original: phase=f'Render #2 объединил дубль с заданием {canonical[:12]}…'
                elif bool(out.get('provisional')) and bool(out.get('peer_accepted')): phase='Render #2 принял задачу и выполняет её · резервная копия запроса сохранена на FAST'
                elif ostate in {'pending','retry'}: phase='восстанавливаю связь с Render #2 · запрос сохранён, повторяю автоматически'
                elif ostate in {'accepted','completed'} and state in {'running','accepted','dispatching',''}: phase='Render #2 выполняет задачу'
                elif state in {'running','failed'}: phase='получаю и отправляю готовый результат'
                else: phase='ожидаю подтверждение Render #2'
                _r40_status_edit(chat_id,msg_id,_r40_status_text(label,_r40_elapsed(started),phase),'r41_file_progress')
                last_ui=now
            _r33_time.sleep(0.5)
        else: err=f'Render #2 не подтвердил доставку за {timeout} сек.; job_id={original}'
    except Exception as exc:
        err=f'{type(exc).__name__}: {str(exc)[:800]}'
    elapsed=_r40_elapsed(started)
    if ok:
        _r40_status_edit(chat_id,msg_id,_r40_status_text(label,elapsed,'',final='ok'),'r41_file_done')
    else:
        _r40_status_edit(chat_id,msg_id,_r40_status_text(label,elapsed,err or 'нет подтверждения доставки',final='error'),'r41_file_error')
        try: log_error(f'R41 async HEAVY job {original}: {err}')
        except Exception: pass
    _r40_status_delete_later(chat_id,msg_id,15)
    with _R40_SUP_LOCK: _R40_SUPERVISORS.pop(original,None)


# R40 submitter resolves this global at call time.
_r40_supervise_remote = _r41_supervise_remote

try:
    bot_journal('r41_two_phase_peer_loaded',int(OWNER_ID or 0),'FAST Redis outbox remains pending during HEAVY provisional admission; no false unavailable state; file outbox completes on real delivery')
except Exception:
    pass

# v262


# R42 reliability barrier: previous-release peer jobs are not replayed; content pool has 4 workers.
try:
    bot_journal('r42_recovery_barrier_loaded', int(OWNER_ID or 0), 'drop stale R39-R41 peer outbox; 4 content workers; current jobs use Пер-R43')
except Exception:
    pass
# ---------------------------------------------------------------------------
# R44 DIAGNOSTIC INTEROP LAYER
# Purpose: observe the real FAST <-> HEAVY protocol without changing production
# job semantics.  Adds owner-only Test menu, shared-Redis handshake diagnostics,
# MEGA browser/download via HEAVY, reverse HEAVY->FAST ping, snapshot probe, and a
# compact local JSONL journal that mirrors important button/process/traffic events.
import json as _r44_json, os as _r44_os, time as _r44_time, threading as _r44_threading
import secrets as _r44_secrets, tempfile as _r44_tempfile, hashlib as _r44_hashlib
import html as _r44_html, re as _r44_re, shutil as _r44_shutil
from pathlib import Path as _R44Path
import requests as _r44_requests

_R44_DIAG_RELEASE='Пер-R44-DIAG'
_R44_DIAG_LOCK=_r44_threading.RLock()
_R44_DIAG_PATH=_R44Path(str(_r44_os.getenv('R44_DIAG_JOURNAL_PATH','/tmp/per_r44_diag_journal.jsonl') or '/tmp/per_r44_diag_journal.jsonl'))
_R44_DIAG_MAX=max(262144,min(20*1024*1024,int(_r44_os.getenv('R44_DIAG_JOURNAL_MAX_BYTES','5242880') or '5242880')))
_R44_TEST_MODE={}
_R44_MEGA_TOKENS={}
_R44_MEGA_TOKEN_LOCK=_r44_threading.RLock()
_R44_TEST_KEY_PREFIX='per:r44:test:'
_R44_TRAFFIC_WORDS=('TRAFFIC_AUDIT','DISPATCHER STUCK','STUCK_STACK','LOCKTRACE','INTERACTIVE FILE JOB','SPLIT FRONT','HEAVY','peer','Render #2','R4','BTNTRACE','FASTBTN','WEBHOOK')

def _r44_redact(value):
    s=str(value if value is not None else '')
    try:
        sec=str(_r44_os.getenv('PEER_SHARED_SECRET','') or '')
        if sec and len(sec)>=6: s=s.replace(sec,'<peer-secret>')
    except Exception: pass
    for key in ('BOT_TOKEN','TELEGRAM_BOT_TOKEN','REDIS_URL','MEGA_PASSWORD','MEGA_SESSION','GOOGLE_SERVICE_ACCOUNT_JSON'):
        try:
            v=str(_r44_os.getenv(key,'') or '')
            if v and len(v)>=8: s=s.replace(v,f'<{key.lower()}>')
        except Exception: pass
    return s[:2400]

def _r44_diag(event, **fields):
    try:
        row={'ts':round(_r44_time.time(),3),'event':str(event or '')[:120],'thread':_r44_threading.current_thread().name[:80]}
        for k,v in fields.items(): row[str(k)[:80]]=_r44_redact(v)
        raw=_r44_json.dumps(row,ensure_ascii=False,separators=(',',':'),default=str)+'\n'
        with _R44_DIAG_LOCK:
            _R44_DIAG_PATH.parent.mkdir(parents=True,exist_ok=True)
            try:
                if _R44_DIAG_PATH.exists() and _R44_DIAG_PATH.stat().st_size>_R44_DIAG_MAX:
                    old=_R44_DIAG_PATH.with_suffix(_R44_DIAG_PATH.suffix+'.1')
                    try: old.unlink(missing_ok=True)
                    except Exception: pass
                    try: _R44_DIAG_PATH.replace(old)
                    except Exception: pass
            except Exception: pass
            with open(_R44_DIAG_PATH,'a',encoding='utf-8') as fh: fh.write(raw)
    except Exception:
        pass

def _r44_diag_tail(limit=30):
    try:
        if not _R44_DIAG_PATH.exists(): return []
        with open(_R44_DIAG_PATH,'r',encoding='utf-8',errors='replace') as fh:
            rows=fh.readlines()[-max(1,min(100,int(limit or 30))):]
        out=[]
        for line in rows:
            try: out.append(_r44_json.loads(line))
            except Exception: continue
        return out
    except Exception: return []

# R47 FINALIZATION: no global logger wrappers. Diagnostics write only explicit R44/R45 events.
def _r44_peer_base():
    fn=globals().get('_r32_peer_base_impl') or globals().get('_split_peer_base')
    try:
        base=str(fn() if callable(fn) else '')
    except Exception: base=''
    if not base:
        base=str(_r44_os.getenv('PEER_SERVICE_URL','') or '').strip().rstrip('/')
        if base and not base.startswith(('http://','https://')): base='https://'+base
    return base.rstrip('/')

def _r44_headers(agent='per-r44-diag'):
    fn=globals().get('_split_headers')
    if callable(fn):
        try: return dict(fn(agent) or {})
        except Exception: pass
    return {'X-Peer-Secret':str(_r44_os.getenv('PEER_SHARED_SECRET','') or ''),'User-Agent':agent}

def _r44_front_redis():
    for name in ('_r38_outbox_redis_client','_r35_delivery_redis_client'):
        fn=globals().get(name)
        if callable(fn):
            try:
                c=fn()
                if c is not None and bool(c.ping()): return c
            except Exception: pass
    try:
        import redis as _r44_redis
        url=_r61_effective_redis_url()
        if not url:return None
        c=_r44_redis.Redis.from_url(url,decode_responses=False,socket_connect_timeout=2,socket_timeout=3)
        if c.ping(): return c
    except Exception: pass
    return None

def _r44_mode(chat_id): return str(_R44_TEST_MODE.get(int(chat_id),'direct') or 'direct')
def _r44_set_mode(chat_id,mode): _R44_TEST_MODE[int(chat_id)]='redis' if str(mode)=='redis' else 'direct'; return _r44_mode(chat_id)

def _r44_request(chat_id, method, path, *, json_body=None, params=None, timeout=20, stream=False):
    cid=int(chat_id); mode=_r44_mode(cid); base=_r44_peer_base(); start=_r44_time.monotonic()
    if not base: return None,{'ok':False,'error':'PEER_SERVICE_URL не настроен','mode':mode,'elapsed':0}
    headers=_r44_headers('per-r44-diag-'+mode); nonce=''; rclient=None; rkey=''; redis_verified=None
    if mode=='redis':
        rclient=_r44_front_redis()
        if rclient is None:
            return None,{'ok':False,'error':'Redis на FAST недоступен','mode':mode,'elapsed':0,'redis_verified':False}
        nonce=_r44_secrets.token_hex(10); rkey=_R44_TEST_KEY_PREFIX+nonce
        try:
            rclient.setex(rkey,90,_r44_json.dumps({'side':'front','ts':_r44_time.time(),'chat':cid},separators=(',',':')))
            headers['X-R44-Redis-Test']=nonce
        except Exception as exc:
            return None,{'ok':False,'error':'FAST Redis write: '+str(exc)[:220],'mode':mode,'elapsed':0,'redis_verified':False}
    try:
        r=_r44_requests.request(str(method).upper(),base+str(path),headers=headers,json=json_body,params=params,timeout=timeout,stream=stream)
        elapsed=_r44_time.monotonic()-start
        if mode=='redis' and rclient is not None:
            try:
                raw=rclient.get(rkey)
                if isinstance(raw,bytes): raw=raw.decode('utf-8','replace')
                obj=_r44_json.loads(raw or '{}') if raw else {}
                redis_verified=(str(obj.get('side') or '')=='heavy' and bool(obj.get('front_seen')))
            except Exception: redis_verified=False
            try:rclient.delete(rkey)
            except Exception:pass
        meta={'ok':200<=int(r.status_code)<300,'status':int(r.status_code),'mode':mode,'elapsed':round(elapsed,3),'redis_verified':redis_verified,'content_type':str(r.headers.get('Content-Type') or '')[:120]}
        if not stream:
            try: meta['payload']=r.json() if r.content else {}
            except Exception: meta['payload']={'raw':(r.text or '')[:800]}
        _r44_diag('peer_http',method=method,path=path,status=r.status_code,elapsed=elapsed,mode=mode,redis_verified=redis_verified,bytes=r.headers.get('Content-Length',''))
        return r,meta
    except Exception as exc:
        elapsed=_r44_time.monotonic()-start
        try:
            if rclient is not None and rkey:rclient.delete(rkey)
        except Exception:pass
        _r44_diag('peer_http_error',method=method,path=path,elapsed=elapsed,mode=mode,error=f'{type(exc).__name__}: {exc}')
        return None,{'ok':False,'error':f'{type(exc).__name__}: {str(exc)[:500]}','mode':mode,'elapsed':round(elapsed,3),'redis_verified':False if mode=='redis' else None}

@app.route('/internal/r44/test/reverse',methods=['POST'])
def r44_front_reverse_probe():
    auth=globals().get('_split_authorized_request')
    if not callable(auth) or not bool(auth()): return ({'ok':False},404)
    body=request.get_json(silent=True) or {}; nonce=str(body.get('nonce') or '')[:120]
    _r44_diag('reverse_probe_received',nonce=nonce,remote=str(getattr(request,'remote_addr','') or ''))
    return ({'ok':True,'role':'front','release':_R44_DIAG_RELEASE,'nonce':nonce,'ts':_r44_time.time()},200)

def _r44_token(path,kind='dir'):
    raw=str(kind)+'\0'+str(path)
    tok=_r44_hashlib.sha1(raw.encode('utf-8','ignore')).hexdigest()[:14]
    with _R44_MEGA_TOKEN_LOCK:_R44_MEGA_TOKENS[tok]={'path':str(path),'kind':str(kind),'ts':_r44_time.time()}
    return tok

def _r44_token_get(tok):
    with _R44_MEGA_TOKEN_LOCK:return dict(_R44_MEGA_TOKENS.get(str(tok),{}) or {})

def _r44_test_menu_text(chat_id,remote=None):
    cid=int(chat_id); mode=_r44_mode(cid); rc=_r44_front_redis(); redis_front='✅' if rc is not None else '⛔'
    peer=_r44_peer_base() or '—'; host=_r44_re.sub(r'^https?://','',peer).split('/')[0]
    lines=['🧪 <b>ТЕСТ #1 FAST ↔ #2 HEAVY</b>','',f'Режим теста: <b>{"Redis handshake" if mode=="redis" else "прямой HTTP"}</b>',f'FAST Redis: {redis_front}',f'HEAVY URL: <code>{_r44_html.escape(host[:80])}</code>']
    if isinstance(remote,dict):
        lines+=['',f'HEAVY: {"✅ отвечает" if remote.get("ok") else "⛔ ошибка"}']
        if remote.get('status') is not None: lines.append(f'HTTP: {remote.get("status")} · {remote.get("elapsed",0)}с')
        if mode=='redis': lines.append(f'Общий Redis: {"✅ один и тот же" if remote.get("redis_verified") else "⛔ не подтверждён"}')
        p=remote.get('payload') if isinstance(remote.get('payload'),dict) else {}
        if p:
            lines.append(f'MEGA #2: {"✅" if p.get("mega_ok") else "🟠"} · <code>{_r44_html.escape(str(p.get("mega_root") or "—")[:90])}</code>')
            lines.append(f'Redis #2: {"✅" if p.get("redis_ok") else "⛔"} · configured={int(bool(p.get("redis_configured")))}')
            lines.append(f'Front виден #2: {"✅" if p.get("front_configured") else "⛔"}')
    lines+=['','Здесь тестируется реальная связь, MEGA и общий Redis. Производственный транспорт заданий этим переключателем не меняется.']
    return window_mark('\n'.join(lines),'Ф4044')

def _r44_test_menu_kb(chat_id):
    cid=int(chat_id); kb=types.InlineKeyboardMarkup(row_width=2); mode=_r44_mode(cid)
    kb.row(IB('🔗 #1 → #2 HTTP',callback_data='r44:test:echo'),IB('↩️ #2 → #1',callback_data='r44:test:reverse'))
    kb.row(IB('📁 MEGA #2',callback_data='r44:test:mega:root'),IB('🗃 Снимок БД',callback_data='r44:test:snapshot'))
    kb.row(IB(('🧠 Redis: ВКЛ' if mode=='redis' else '🧠 Redis: ВЫКЛ'),callback_data='r44:test:redis_toggle'),IB('🩺 Полный тест',callback_data='r44:test:full'))
    kb.row(IB('📜 Последние события',callback_data='r44:test:tail'),IB('📥 Скачать журнал',callback_data='r44:test:journal'))
    kb.row(IB('🔄 Статус #2',callback_data='r44:test:status'))
    day=str(get_chat_store(cid).get('current_view_day') or today_key())
    kb.row(IB('⬅️ Основное окно',callback_data=f'd:{day}:back_main'),IB('❌ Закрыть',callback_data='info_close'))
    return kb

def _r44_mega_screen(chat_id,path,page=0):
    r,meta=_r44_request(chat_id,'GET','/internal/r44/test/mega/list',params={'path':str(path)},timeout=45)
    p=meta.get('payload') if isinstance(meta.get('payload'),dict) else {}
    if not meta.get('ok') or not p.get('ok'):
        text=window_mark('📁 <b>MEGA #2</b>\n\n⛔ '+_r44_html.escape(str(p.get('error') or meta.get('error') or f'HTTP {meta.get("status")}')[:1200]),'Ф4045')
        kb=types.InlineKeyboardMarkup();kb.row(IB('🔙 В тест',callback_data='r44:test:open'));return text,kb
    entries=list(p.get('entries') or []); page=max(0,int(page or 0)); per=9; pages=max(1,(len(entries)+per-1)//per); page=min(page,pages-1)
    text=window_mark(f'📁 <b>MEGA #2</b>\n\nПуть: <code>{_r44_html.escape(str(p.get("path") or path)[:500])}</code>\nПапок/файлов: {len(entries)} · страница {page+1}/{pages}\nПолучено за {meta.get("elapsed",0)}с','Ф4045')
    kb=types.InlineKeyboardMarkup(row_width=1)
    for ent in entries[page*per:(page+1)*per]:
        ep=str(ent.get('path') or ''); kind=str(ent.get('type') or 'file'); name=str(ent.get('name') or ep.rsplit('/',1)[-1] or '/')
        tok=_r44_token(ep,kind); label=('📁 ' if kind=='dir' else '📄 ')+name[:46]
        kb.row(IB(label,callback_data=f'r44:test:mega:{"d" if kind=="dir" else "f"}:{tok}'))
    nav=[]
    ptok=_r44_token(str(p.get('path') or path),'dir')
    if page>0: nav.append(IB('◀️',callback_data=f'r44:test:mega:p:{ptok}:{page-1}'))
    if page+1<pages: nav.append(IB('▶️',callback_data=f'r44:test:mega:p:{ptok}:{page+1}'))
    if nav: kb.row(*nav)
    parent=str(p.get('parent') or '')
    if parent and parent!=str(p.get('path') or ''):
        kb.row(IB('⬆️ Вверх',callback_data=f'r44:test:mega:d:{_r44_token(parent,"dir")}'))
    kb.row(IB('🔄 Обновить',callback_data=f'r44:test:mega:d:{ptok}'),IB('🔙 В тест',callback_data='r44:test:open'))
    return text,kb

def _r44_send_mega_file(chat_id,path):
    cid=int(chat_id); r,meta=_r44_request(cid,'GET','/internal/r44/test/mega/file',params={'path':str(path)},timeout=120,stream=True)
    if r is None or not meta.get('ok'):
        return False,str(meta.get('error') or f'HTTP {meta.get("status")}')[:700]
    tmp=None
    try:
        name=str(path).rstrip('/').rsplit('/',1)[-1] or 'mega_file.bin'
        fd,tmp=_r44_tempfile.mkstemp(prefix='r44_mega_',suffix='_'+_r44_re.sub(r'[^A-Za-z0-9_.-]+','_',name)[-70:]);_r44_os.close(fd)
        size=0
        with open(tmp,'wb') as fh:
            for chunk in r.iter_content(1024*512):
                if not chunk: continue
                size+=len(chunk)
                if size>50*1024*1024: raise RuntimeError('Файл больше диагностического лимита 50 МБ')
                fh.write(chunk)
        with open(tmp,'rb') as fh: bot.send_document(cid,fh,caption=f'🧪 R44 · HEAVY передал из MEGA\n{name}')
        _r44_diag('mega_file_delivered',chat=cid,path=path,bytes=size,elapsed=meta.get('elapsed'))
        return True,f'{name} · {size} байт'
    except Exception as exc:
        _r44_diag('mega_file_error',chat=cid,path=path,error=exc);return False,f'{type(exc).__name__}: {str(exc)[:500]}'
    finally:
        try:
            if tmp:_r44_os.unlink(tmp)
        except Exception:pass

def _r44_render_tail():
    rows=_r44_diag_tail(28); lines=['📜 <b>R44 · последние события FAST</b>','']
    for row in rows[-24:]:
        ts=_r44_time.strftime('%H:%M:%S',_r44_time.localtime(float(row.get('ts') or 0)))
        ev=str(row.get('event') or '')[:40]; detail=str(row.get('name') or row.get('path') or row.get('message') or row.get('detail') or '')[:100]
        lines.append(f'<code>{ts}</code> · {_r44_html.escape(ev)} · {_r44_html.escape(detail)}')
    if len(lines)==2: lines.append('Пока пусто.')
    return window_mark('\n'.join(lines),'Ф4046')

def _r44_full_test(chat_id):
    cid=int(chat_id); results=[]
    for label,method,path,body,to in [
        ('#1→#2','POST','/internal/r44/test/echo',{'nonce':_r44_secrets.token_hex(6)},12),
        ('#2→#1','POST','/internal/r44/test/reverse',{'nonce':_r44_secrets.token_hex(6)},15),
        ('Статус','GET','/internal/r44/test/status',None,15),
    ]:
        r,m=_r44_request(cid,method,path,json_body=body,timeout=to); p=m.get('payload') if isinstance(m.get('payload'),dict) else {}
        results.append((label,bool(m.get('ok') and p.get('ok',True)),m,p))
    r,m=_r44_request(cid,'GET','/internal/r44/test/mega/list',params={'path':''},timeout=45);p=m.get('payload') if isinstance(m.get('payload'),dict) else {};results.append(('MEGA',bool(m.get('ok') and p.get('ok')),m,p))
    lines=['🩺 <b>ПОЛНЫЙ ТЕСТ #1 ↔ #2</b>','']
    for label,ok,m,p in results:
        extra=''
        if label=='MEGA' and ok: extra=f' · entries={len(p.get("entries") or [])}'
        if _r44_mode(cid)=='redis': extra+=f' · Redis={"OK" if m.get("redis_verified") else "NO"}'
        lines.append(f'{"✅" if ok else "⛔"} {label}: {m.get("elapsed",0)}с{extra}')
        if not ok: lines.append('   '+_r44_html.escape(str(p.get('error') or m.get('error') or f'HTTP {m.get("status")}')[:260]))
    return window_mark('\n'.join(lines),'Ф4047')

# Owner-only Test button in the actual main window.
_R44_MAIN_KB_CORE=globals().get('build_main_keyboard')
def _r44_build_main_keyboard(day_key,chat_id=None):
    kb=_R44_MAIN_KB_CORE(day_key,chat_id) if callable(_R44_MAIN_KB_CORE) else types.InlineKeyboardMarkup()
    try: cid=int(chat_id if chat_id is not None else current_state_chat_id() or 0)
    except Exception: cid=0
    if cid!=int(OWNER_ID or 0): return kb
    try:
        rows=globals().get('_v217_rows',lambda x:list(getattr(x,'keyboard',None) or []))(kb)
        cbfn=globals().get('_v217_btn_cb',lambda b:str(getattr(b,'callback_data','') or ''))
        if not any(cbfn(b)=='r44:test:open' for row in rows for b in (row or [])):
            rows.append([IB('🧪 Тест #1 ↔ #2',callback_data='r44:test:open')])
            setfn=globals().get('_v217_set_rows')
            if callable(setfn): kb=setfn(kb,rows)
            else: kb.row(IB('🧪 Тест #1 ↔ #2',callback_data='r44:test:open'))
    except Exception:
        try:kb.row(IB('🧪 Тест #1 ↔ #2',callback_data='r44:test:open'))
        except Exception:pass
    return kb
if callable(_R44_MAIN_KB_CORE): build_main_keyboard = _r44_build_main_keyboard

_R44_CONTOUR_GUARD_CORE=globals().get('contour_callback_guard')
# R47 FINALIZATION: R44 synchronous diagnostic guard removed; R45 is sole diagnostic callback owner.

# R47 FINALIZATION: no transport monkey-patching for diagnostics.
_r44_diag('r44_diag_loaded',release=_R44_DIAG_RELEASE,peer=_r44_peer_base(),redis_fast=bool(_r44_front_redis()))
try: bot_journal('r44_diag_loaded',int(OWNER_ID or 0),'owner test menu + FAST journal + HEAVY MEGA browser + direct/shared-Redis handshake diagnostics')
except Exception:pass



# ---------------------------------------------------------------------------
# R45 STABLE DIAGNOSTIC HOT-PATH FIX
# R44 diagnostic network calls were executed inside the same keyed callback actor
# as the visible Telegram window.  A 15-120 second HTTP/MEGA probe therefore held
# fast-window:<chat>:<message> and made every following button look "CLAIMED" with
# thread=None.  R45 makes diagnostics two-stage: the callback only enqueues work,
# while a completely separate network pool performs the slow probe and edits the
# test window later.  Production callbacks never share this pool.
import queue as _r45_queue, collections as _r45_collections

_R45_RELEASE='Пер-R45-STABLE'
_R45_DIAG_CALLBACK_POOL=KeyedTaskPool('r45-diag-callback',1,120)
_R45_DIAG_NET_POOL=KeyedTaskPool('r45-diag-net',1,60)
_R45_DIAG_SEQ_LOCK=_r44_threading.RLock()
_R45_DIAG_SEQ={}
_R45_DIAG_RING=_r45_collections.deque(maxlen=max(500,min(5000,int(_r44_os.getenv('R45_DIAG_RING_ROWS','1500') or '1500'))))
_R45_DIAG_Q=_r45_queue.Queue(maxsize=max(500,min(20000,int(_r44_os.getenv('R45_DIAG_QUEUE_ROWS','5000') or '5000'))))
_R45_DIAG_DROPPED=0

# Cache secret strings once.  R44 re-scanned the full environment for every traced
# line; that is unnecessary work on every button/traffic log.
_R45_REDACT_VALUES=[]
for _r45_key in ('PEER_SHARED_SECRET','BOT_TOKEN','TELEGRAM_BOT_TOKEN','REDIS_URL','MEGA_PASSWORD','MEGA_SESSION','GOOGLE_SERVICE_ACCOUNT_JSON'):
    try:
        _r45_val=str(_r44_os.getenv(_r45_key,'') or '')
        if _r45_val and len(_r45_val)>=6:_R45_REDACT_VALUES.append((_r45_val,'<'+_r45_key.lower()+'>'))
    except Exception:pass

def _r44_redact(value):
    s=str(value if value is not None else '')
    for old,repl in _R45_REDACT_VALUES:
        try:s=s.replace(old,repl)
        except Exception:pass
    return s[:2400]

def _r45_diag_rotate_and_append(lines):
    try:
        _R44_DIAG_PATH.parent.mkdir(parents=True,exist_ok=True)
        if _R44_DIAG_PATH.exists() and _R44_DIAG_PATH.stat().st_size>_R44_DIAG_MAX:
            old=_R44_DIAG_PATH.with_suffix(_R44_DIAG_PATH.suffix+'.1')
            try:old.unlink(missing_ok=True)
            except Exception:pass
            try:_R44_DIAG_PATH.replace(old)
            except Exception:pass
        with open(_R44_DIAG_PATH,'a',encoding='utf-8') as fh:
            fh.writelines(lines)
    except Exception:
        pass

def _r45_diag_writer_loop():
    batch=[]
    while True:
        try:
            try:line=_R45_DIAG_Q.get(timeout=.35)
            except _r45_queue.Empty:line=None
            if line:
                batch.append(line)
                _R45_DIAG_Q.task_done()
            while len(batch)<128:
                try:
                    line=_R45_DIAG_Q.get_nowait();batch.append(line);_R45_DIAG_Q.task_done()
                except _r45_queue.Empty:break
            if batch:
                _r45_diag_rotate_and_append(batch);batch=[]
        except Exception:
            batch=[];_r44_time.sleep(.25)

_r44_threading.Thread(target=_r45_diag_writer_loop,name='r45-diag-writer',daemon=True).start()

def _r44_diag(event, **fields):
    """Zero-blocking hot-path trace: RAM ring + nonblocking writer queue."""
    global _R45_DIAG_DROPPED
    try:
        row={'ts':round(_r44_time.time(),3),'event':str(event or '')[:120],'thread':_r44_threading.current_thread().name[:80]}
        for k,v in fields.items():row[str(k)[:80]]=_r44_redact(v)
        with _R45_DIAG_SEQ_LOCK:_R45_DIAG_RING.append(row)
        raw=_r44_json.dumps(row,ensure_ascii=False,separators=(',',':'),default=str)+'\n'
        try:_R45_DIAG_Q.put_nowait(raw)
        except _r45_queue.Full:_R45_DIAG_DROPPED+=1
    except Exception:pass

def _r44_diag_tail(limit=30):
    try:
        with _R45_DIAG_SEQ_LOCK:
            rows=list(_R45_DIAG_RING)[-max(1,min(100,int(limit or 30))):]
        if rows:return rows
    except Exception:pass
    try:
        if not _R44_DIAG_PATH.exists():return []
        with open(_R44_DIAG_PATH,'r',encoding='utf-8',errors='replace') as fh:raws=fh.readlines()[-max(1,min(100,int(limit or 30))):]
        out=[]
        for line in raws:
            try:out.append(_r44_json.loads(line))
            except Exception:pass
        return out
    except Exception:return []

def _r45_call_key(call):
    try:return (int(call.message.chat.id),int(call.message.message_id))
    except Exception:return (0,0)

def _r45_next_seq(call):
    key=_r45_call_key(call)
    with _R45_DIAG_SEQ_LOCK:
        seq=int(_R45_DIAG_SEQ.get(key,0))+1;_R45_DIAG_SEQ[key]=seq
    return key,seq

def _r45_is_current(key,seq):
    with _R45_DIAG_SEQ_LOCK:return int(_R45_DIAG_SEQ.get(key,0))==int(seq)

def _r45_safe_edit_if_current(call,key,seq,text,kb=None,parse_mode='HTML'):
    if not _r45_is_current(key,seq):return False
    try:
        safe_edit(bot,call,text,reply_markup=kb,parse_mode=parse_mode)
        return True
    except Exception as exc:
        _r44_diag('diag_edit_error',chat=key[0],message=key[1],error=f'{type(exc).__name__}: {exc}')
        return False

def _r45_pending_text(label):
    return window_mark('🧪 <b>ТЕСТ #1 ↔ #2</b>\n\n⏳ '+_r44_html.escape(str(label or 'Проверяю…'))+'\n\nОбычные кнопки бота в это время свободны.','Ф4053')

def _r45_diag_job(call,key,seq,raw):
    cid=key[0]
    _r44_diag('diag_job_start',chat=cid,action=raw,seq=seq,mode=_r44_mode(cid))
    started=_r44_time.monotonic()
    try:
        if raw=='r44:test:status':
            _,m=_r44_request(cid,'GET','/internal/r44/test/status',timeout=8)
            text=_r44_test_menu_text(cid,m);kb=_r44_test_menu_kb(cid)
        elif raw=='r44:test:echo':
            nonce=_r44_secrets.token_hex(8);_,m=_r44_request(cid,'POST','/internal/r44/test/echo',json_body={'nonce':nonce,'sent_at':_r44_time.time()},timeout=8);p=m.get('payload') if isinstance(m.get('payload'),dict) else {};ok=bool(m.get('ok') and p.get('nonce')==nonce)
            text=window_mark(f'🔗 <b>#1 FAST → #2 HEAVY</b>\n\n{"✅ Успех" if ok else "⛔ Ошибка"}\nHTTP: {m.get("status","—")} · {m.get("elapsed",0)}с\nNonce: <code>{nonce}</code>\nОтвет: <code>{_r44_html.escape(str(p.get("nonce") or "—"))}</code>\nRedis handshake: {m.get("redis_verified") if _r44_mode(cid)=="redis" else "не используется"}','Ф4048');kb=_r44_test_menu_kb(cid)
        elif raw=='r44:test:reverse':
            nonce=_r44_secrets.token_hex(8);_,m=_r44_request(cid,'POST','/internal/r44/test/reverse',json_body={'nonce':nonce},timeout=10);p=m.get('payload') if isinstance(m.get('payload'),dict) else {};rr=p.get('front_reply') if isinstance(p.get('front_reply'),dict) else {};ok=bool(m.get('ok') and p.get('ok') and rr.get('nonce')==nonce)
            text=window_mark(f'↩️ <b>#2 HEAVY → #1 FAST</b>\n\n{"✅ Успех" if ok else "⛔ Ошибка"}\nОбщее время: {m.get("elapsed",0)}с\nHEAVY увидел Front: {"✅" if p.get("front_http_ok") else "⛔"}\nNonce вернулся: {"✅" if rr.get("nonce")==nonce else "⛔"}\nRedis handshake: {m.get("redis_verified") if _r44_mode(cid)=="redis" else "не используется"}\n{_r44_html.escape(str(p.get("error") or m.get("error") or "")[:500])}','Ф4049');kb=_r44_test_menu_kb(cid)
        elif raw=='r44:test:snapshot':
            _,m=_r44_request(cid,'POST','/internal/r44/test/snapshot',json_body={'nonce':_r44_secrets.token_hex(6)},timeout=45);p=m.get('payload') if isinstance(m.get('payload'),dict) else {}
            text=window_mark(f'🗃 <b>Снимок данных #1 → #2</b>\n\n{"✅ HEAVY получил свежую SQLite" if m.get("ok") and p.get("ok") else "⛔ Ошибка"}\nВремя: {m.get("elapsed",0)}с\nBytes: {p.get("snapshot_bytes","—")}\nToken: <code>{_r44_html.escape(str(p.get("token") or "—")[:80])}</code>\n{_r44_html.escape(str(p.get("error") or m.get("error") or "")[:600])}','Ф4050');kb=_r44_test_menu_kb(cid)
        elif raw=='r44:test:mega:root':
            text,kb=_r44_mega_screen(cid,'',0)
        elif raw.startswith('r44:test:mega:d:'):
            tok=raw.split(':')[-1];rec=_r44_token_get(tok);text,kb=_r44_mega_screen(cid,rec.get('path') or '',0)
        elif raw.startswith('r44:test:mega:p:'):
            parts=raw.split(':');tok=parts[-2];page=int(parts[-1]);rec=_r44_token_get(tok);text,kb=_r44_mega_screen(cid,rec.get('path') or '',page)
        elif raw.startswith('r44:test:mega:f:'):
            tok=raw.split(':')[-1];rec=_r44_token_get(tok);path=rec.get('path') or ''
            ok,detail=_r44_send_mega_file(cid,path)
            text=window_mark(('✅ Передано: ' if ok else '⛔ Ошибка: ')+_r44_html.escape(detail),'Ф4051');kb=_r44_test_menu_kb(cid)
        elif raw=='r44:test:full':
            text=_r44_full_test(cid);kb=_r44_test_menu_kb(cid)
        elif raw=='r44:test:journal':
            _r44_diag('journal_download',chat=cid)
            # Give writer a short chance to flush queued lines without blocking callbacks.
            _r44_time.sleep(.15)
            if not _R44_DIAG_PATH.exists():
                _r44_diag('journal_created',chat=cid)
                try:_R44_DIAG_PATH.parent.mkdir(parents=True,exist_ok=True);_R44_DIAG_PATH.touch(exist_ok=True)
                except Exception:pass
            with open(_R44_DIAG_PATH,'rb') as fh:bot.send_document(cid,fh,caption='📜 R45 диагностический журнал FAST')
            text=_r44_test_menu_text(cid);kb=_r44_test_menu_kb(cid)
        else:
            text=window_mark('⛔ Неизвестный диагностический тест: '+_r44_html.escape(raw),'Ф4052');kb=_r44_test_menu_kb(cid)
        _r45_safe_edit_if_current(call,key,seq,text,kb,'HTML')
        _r44_diag('diag_job_done',chat=cid,action=raw,seq=seq,elapsed=round(_r44_time.monotonic()-started,3))
    except Exception as exc:
        _r44_diag('diag_job_error',chat=cid,action=raw,seq=seq,elapsed=round(_r44_time.monotonic()-started,3),error=f'{type(exc).__name__}: {exc}')
        _r45_safe_edit_if_current(call,key,seq,window_mark('⛔ <b>R45 TEST</b>\n\n'+_r44_html.escape(f'{type(exc).__name__}: {str(exc)[:1200]}'),'Ф4052'),_r44_test_menu_kb(cid),'HTML')

def _r45_enqueue_diag(call,raw,label='Проверяю связь…'):
    key,seq=_r45_next_seq(call);cid=key[0]
    try:safe_edit(bot,call,_r45_pending_text(label),reply_markup=_r44_test_menu_kb(cid),parse_mode='HTML')
    except Exception:pass
    queued=_R45_DIAG_NET_POOL.submit(f'{cid}:{seq}',_r45_diag_job,call,key,seq,raw)
    if not queued:
        _r45_safe_edit_if_current(call,key,seq,window_mark('⛔ Диагностическая очередь занята. Повтори через несколько секунд.','Ф4052'),_r44_test_menu_kb(cid),'HTML')
    return True

# Diagnostic callbacks are admitted on their own tiny lane.  Even a future bug in a
# diagnostic handler therefore cannot hold the production fast-window actor.
_R45_SELECTOR_CORE=globals().get('v163_webhook_select_lane')
def _r45_webhook_select_lane(payload,update_type,update_key):
    if str(update_type)=='callback_query':
        try:
            raw=str(((payload or {}).get('callback_query') or {}).get('data') or '')
            if raw.startswith('r44:test:') or raw.startswith('r45:test:'):
                return (_R45_DIAG_CALLBACK_POOL,f'diag-admit:{update_key}:{(payload or {}).get("update_id","")}')
        except Exception:pass
    if callable(_R45_SELECTOR_CORE):return _R45_SELECTOR_CORE(payload,update_type,update_key)
    return (UI_TASK_POOL if str(update_type)=='callback_query' else WEBHOOK_TASK_POOL,str(update_key))
v163_webhook_select_lane = _r45_webhook_select_lane

# Replace the synchronous R44 guard.  Only open/toggle/tail are local and immediate;
# every network/MEGA/file probe is detached before this callback worker returns.
_R45_CONTOUR_GUARD_CORE=_R44_CONTOUR_GUARD_CORE
def _r45_test_guard(call,resolved):
    raw=str(resolved or '')
    if not (raw.startswith('r44:test:') or raw.startswith('r45:test:')):
        return bool(_R45_CONTOUR_GUARD_CORE(call,raw)) if callable(_R45_CONTOUR_GUARD_CORE) else False
    try:cid=int(call.message.chat.id);uid=int(getattr(getattr(call,'from_user',None),'id',0) or 0)
    except Exception:return True
    if cid!=int(OWNER_ID or 0) or uid!=int(OWNER_ID or 0):
        try:bot.answer_callback_query(call.id,'Только владелец.',show_alert=True)
        except Exception:pass
        return True
    _r44_diag('test_button',chat=cid,action=raw,mode=_r44_mode(cid))
    try:
        if raw in {'r44:test:open','r45:test:open'}:
            safe_edit(bot,call,_r44_test_menu_text(cid),reply_markup=_r44_test_menu_kb(cid),parse_mode='HTML');return True
        if raw in {'r44:test:redis_toggle','r45:test:redis_toggle'}:
            _r44_set_mode(cid,'direct' if _r44_mode(cid)=='redis' else 'redis');safe_edit(bot,call,_r44_test_menu_text(cid),reply_markup=_r44_test_menu_kb(cid),parse_mode='HTML');return True
        if raw in {'r44:test:tail','r45:test:tail'}:
            safe_edit(bot,call,_r44_render_tail(),reply_markup=_r44_test_menu_kb(cid),parse_mode='HTML');return True
        labels={
            'r44:test:status':'Проверяю состояние Render #2…','r44:test:echo':'Проверяю #1 → #2…','r44:test:reverse':'Проверяю #2 → #1…',
            'r44:test:snapshot':'Проверяю передачу SQLite…','r44:test:mega:root':'Читаю папки MEGA через Render #2…','r44:test:full':'Запускаю полный тест…',
            'r44:test:journal':'Готовлю журнал…'
        }
        if raw.startswith('r44:test:mega:d:') or raw.startswith('r44:test:mega:p:'):label='Открываю папку MEGA через Render #2…'
        elif raw.startswith('r44:test:mega:f:'):label='Render #2 передаёт файл из MEGA…'
        else:label=labels.get(raw,'Проверяю…')
        return _r45_enqueue_diag(call,raw,label)
    except Exception as exc:
        _r44_diag('test_handler_error',chat=cid,action=raw,error=f'{type(exc).__name__}: {exc}')
        try:safe_edit(bot,call,window_mark('⛔ <b>R45 TEST</b>\n\n'+_r44_html.escape(f'{type(exc).__name__}: {str(exc)[:1200]}'),'Ф4052'),reply_markup=_r44_test_menu_kb(cid),parse_mode='HTML')
        except Exception:pass
        return True
contour_callback_guard = _r45_test_guard

# Make stuck logs actionable and less noisy.  The original watchdog reads this global
# on every pass, so changing it here affects the already-running watchdog thread.
try:WEBHOOK_STUCK_WARN_SECONDS=max(12.0,float(_r44_os.getenv('WEBHOOK_STUCK_WARN_SECONDS','12') or '12'))
except Exception:WEBHOOK_STUCK_WARN_SECONDS=12.0

_R45_LOCK_SNAPSHOT_CORE=globals().get('r36_lock_snapshot_text')
def _r45_lock_snapshot_text():
    parts=[]
    try:
        if callable(_R45_LOCK_SNAPSHOT_CORE):
            old=str(_R45_LOCK_SNAPSHOT_CORE() or '')
            if old and old!='none':parts.append(old)
    except Exception:pass
    for nm in ('WEBHOOK_TASK_POOL','V166_WINDOW_UI_TASK_POOL','V166_FINANCE_UI_TASK_POOL','FAST_UI_TASK_POOL','_R45_DIAG_CALLBACK_POOL','_R45_DIAG_NET_POOL'):
        try:
            pool=globals().get(nm)
            st=pool.stats() if pool is not None and hasattr(pool,'stats') else None
            if st and (int(st.get('active') or 0)>0 or int(st.get('pending') or 0)>0):parts.append(f"{st.get('name')} a={st.get('active')} p={st.get('pending')} keys={st.get('keys')} maxwait={st.get('max_wait')}")
        except Exception:pass
    return '; '.join(parts) or 'none'
r36_lock_snapshot_text = _r45_lock_snapshot_text

_r44_diag('r45_stable_loaded',release=_R45_RELEASE,diag_async=True,diag_workers=2,log_async=True)
try:bot_journal('r45_stable_loaded',int(OWNER_ID or 0),'diagnostic HTTP/MEGA detached from callback actors; async diagnostic journal; independent diagnostic admission lane')
except Exception:pass


# R45 snapshot conditional GET: HEAVY can cheaply ask whether its local SQLite mirror
# already matches FAST.  When the state token is unchanged, FAST returns 304 before
# creating/gzipping another full SQLite backup.
_R45_STATE_DOWNLOAD_CORE=(globals().get('app').view_functions.get('split_front_state_download_v262') if globals().get('app') is not None else None)
def _r45_split_state_download_conditional():
    try:
        auth=globals().get('_split_authorized_request')
        if callable(auth) and not auth():return ({'ok':False},404)
        flush=globals().get('_r27_flush_state_revision')
        if callable(flush):flush()
        tokfn=globals().get('_split_current_state_token_v264')
        token=str(tokfn() if callable(tokfn) else '')
        prior=str(request.headers.get('X-R45-If-State-Token','') or '')
        if prior and token and prior==token:
            resp=app.response_class(b'',status=304,mimetype='application/octet-stream')
            resp.headers['X-Split-State-Token']=token
            resp.headers['X-R45-State-Reused']='1'
            _r44_diag('snapshot_304',token=token[:80])
            return resp
    except Exception as exc:
        _r44_diag('snapshot_304_check_error',error=f'{type(exc).__name__}: {exc}')
    if callable(_R45_STATE_DOWNLOAD_CORE):return _R45_STATE_DOWNLOAD_CORE()
    return ({'ok':False,'error':'state endpoint unavailable'},503)
try:
    if callable(_R45_STATE_DOWNLOAD_CORE):app.view_functions['split_front_state_download_v262']=_r45_split_state_download_conditional
except Exception:pass




# ---------------------------------------------------------------------------
# R47 FINALIZATION: sole extension callback dispatcher.
# No PREV/ORIG callback chain: each feature handler is standalone and returns False
# when the callback does not belong to it.
def v149_extension_callback(call, data_str: str) -> bool:
    raw = str(data_str or '')
    try:
        if _google_extension_callback(call, raw):
            return True
        if _constructor_extension_callback(call, raw):
            return True
        if _reminder_extension_callback(call, raw):
            return True
        if _v153_extension_callback(call, raw):
            return True
        if _v152_handle_rights_callback(call, raw):
            return True
        if raw.startswith('v149:'):
            return bool(_v177_legacy_0266_v149_extension_callback(call, raw))
    except Exception as exc:
        try: log_error(f'final extension callback {raw[:180]}: {type(exc).__name__}: {exc}')
        except Exception: pass
        return True
    return False

try:
    if not globals().get('_R38_OUTBOX_THREAD_STARTED'):
        globals()['_R38_OUTBOX_THREAD_STARTED']=True
        _r38_threading.Thread(target=_r38_outbox_loop,name='per-r38-peer-outbox',daemon=True).start()
    bot_journal('r38_peer_transport_loaded',int(OWNER_ID or 0),'durable FAST outbox; final R47 dispatcher; same job_id; Google+file unified dispatch')
except Exception:
    pass

# v262
