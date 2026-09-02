# v262
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
                    normalize_chat_records(int(cid))
                    try:
                        rebuild_month_short_ids(int(cid))
                    except Exception:
                        pass
                    try:
                        store['balance'] = sum(float(r.get('amount', 0) or 0) for r in store.get('records', []) or [] if isinstance(r, dict))
                    except Exception:
                        pass
                    if not persist_finance_chat_local_fast(int(cid)):
                        raise RuntimeError('local SQLite finance persist failed')
                    current = _v262_records_for_origin(int(cid), origin_key)
                    primary = current[0][1] if current else rows[0][1]
                    touched_days[int(cid)] = str(primary.get('day_key') or store.get('current_view_day') or today_key())
                    if changed_here:
                        changed_total += changed_here
                        changed_by_chat[int(cid)] = int(changed_here)
                        try:
                            finance_cache_invalidate(int(cid), 'linked_edit_v262')
                        except Exception:
                            pass
                        try:
                            finance_integrity_append(int(cid), 'edit', primary, details={'before': before_primary or {}, 'source': source_kind, 'origin_key': origin_key})
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
# v262
