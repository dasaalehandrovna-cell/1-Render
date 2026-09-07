# v262
def load_forward_rules():
    """
    Загружает forward_rules/forward_finance из SQLite,
    а если их там ещё нет — пытается импортировать из legacy owner JSON.
    """
    try:
        fr = data.get('forward_rules', {}) or {}
        ff = data.get('forward_finance', {}) or {}
        if fr or ff:
            data['forward_finance'] = ff if isinstance(ff, dict) else {}
            return fr if isinstance(fr, dict) else {}
        path = _owner_data_file()
        if not path or not os.path.exists(path):
            data['forward_finance'] = {}
            return {}
        payload = _load_json(path, {}) or {}
        raw_fr = payload.get('forward_rules', {})
        upgraded = {}
        for src, value in raw_fr.items():
            if isinstance(value, list):
                upgraded[src] = {}
                for dst in value:
                    upgraded[src][dst] = 'oneway_to'
            elif isinstance(value, dict):
                upgraded[src] = value
        ff = payload.get('forward_finance', {})
        if not isinstance(ff, dict):
            ff = {}
        data['forward_finance'] = ff
        data['forward_rules'] = upgraded
        save_data(data)
        return upgraded
    except Exception as e:
        log_error(f'load_forward_rules: {e}')
        data['forward_finance'] = {}
        return {}

def persist_forward_rules_to_owner():
    """
    Сохраняет forward_rules/forward_finance в SQLite
    и дополнительно пишет legacy owner JSON-снимок для совместимости.
    """
    try:
        save_data(data)
        path = _owner_data_file()
        if path:
            payload = _load_json(path, {}) or {}
            if not isinstance(payload, dict):
                payload = {}
            payload['forward_rules'] = data.get('forward_rules', {})
            payload['forward_finance'] = data.get('forward_finance', {})
            _save_json(path, payload)
            log_info(f'forward_rules snapshot persisted to {path}')
    except Exception as e:
        log_error(f'persist_forward_rules_to_owner: {e}')
V199_CHAT_ALIAS_KEY = 'chat_id_aliases_v199'
V199_FORWARD_SUSPENDED_KEY = 'forward_suspended_targets_v199'

def _v199_alias_root() -> dict:
    return data.setdefault('_global_settings', {}).setdefault(V199_CHAT_ALIAS_KEY, {})

def _v199_suspended_root() -> dict:
    return data.setdefault('_global_settings', {}).setdefault(V199_FORWARD_SUSPENDED_KEY, {})

def resolve_canonical_chat_id_v199(chat_id: int) -> int:
    """Follow persisted Telegram chat-id migrations with a loop guard."""
    current = int(chat_id)
    seen = set()
    root = _v199_alias_root()
    for _ in range(12):
        if current in seen:
            break
        seen.add(current)
        row = root.get(str(current))
        if not isinstance(row, dict):
            break
        try:
            nxt = int(row.get('new_chat_id') or 0)
        except Exception:
            nxt = 0
        if not nxt or nxt == current:
            break
        current = nxt
    return int(current)

def _v199_register_chat_alias(old_chat_id: int, new_chat_id: int, reason: str='telegram migration') -> bool:
    old_chat_id, new_chat_id = (int(old_chat_id), int(new_chat_id))
    if old_chat_id == new_chat_id:
        return False
    row = {'old_chat_id': old_chat_id, 'new_chat_id': new_chat_id, 'reason': str(reason or 'telegram migration')[:500], 'at': now_local().isoformat(timespec='seconds')}
    root = _v199_alias_root()
    changed = root.get(str(old_chat_id)) != row
    root[str(old_chat_id)] = row
    return changed

def is_forward_target_suspended_v199(chat_id: int) -> bool:
    try:
        cid = int(chat_id)
        if str(cid) in _v199_suspended_root():
            return True
        canonical = resolve_canonical_chat_id_v199(cid)
        return str(canonical) in _v199_suspended_root()
    except Exception:
        return False

def _v199_rewrite_pair_order_id(old_chat_id: int, new_chat_id: int | None=None, *, remove_only: bool=False) -> bool:
    old_chat_id = int(old_chat_id)
    changed = False
    order = data.get('forward_pair_order')
    if not isinstance(order, list):
        return False
    out = []
    seen = set()
    for raw in order:
        try:
            a_s, b_s = str(raw).split(':', 1)
            a, b = (int(a_s), int(b_s))
        except Exception:
            if raw not in seen:
                out.append(raw)
                seen.add(raw)
            continue
        if remove_only and old_chat_id in {a, b}:
            changed = True
            continue
        if new_chat_id is not None:
            na = int(new_chat_id) if a == old_chat_id else a
            nb = int(new_chat_id) if b == old_chat_id else b
            if (na, nb) != (a, b):
                changed = True
            if na == nb:
                changed = True
                continue
            key = f'{na}:{nb}'
        else:
            key = str(raw)
        if key not in seen:
            out.append(key)
            seen.add(key)
    if out != order:
        data['forward_pair_order'] = out
        changed = True
    return changed

def suspend_forward_target_v199(dst_chat_id: int, reason: str, *, persist: bool=True) -> bool:
    """Remove a confirmed-dead destination from live forwarding but keep a reversible audit copy."""
    dst_chat_id = int(dst_chat_id)
    key = str(dst_chat_id)
    root = _v199_suspended_root()
    existing = root.get(key) if isinstance(root.get(key), dict) else None
    # R17: even an already-suspended target is scrubbed again from live maps.  This
    # repairs stale R16 states where an audit row existed but a forwarding edge was
    # later reintroduced, which otherwise could keep hitting a removed chat forever.
    edges = list((existing or {}).get('edges') or [])
    changed_live = False
    fr = data.setdefault('forward_rules', {})
    ff = data.setdefault('forward_finance', {})
    for src, dsts in list(fr.items()):
        if not isinstance(dsts, dict) or key not in dsts:
            continue
        mode = dsts.pop(key)
        changed_live = True
        fin = bool((ff.get(str(src), {}) or {}).pop(key, False))
        edges.append({'src': int(src), 'mode': mode, 'finance': fin})
        if not dsts:
            fr.pop(str(src), None)
        frow = ff.get(str(src))
        if isinstance(frow, dict) and (not frow):
            ff.pop(str(src), None)
    for src, dsts in list(ff.items()):
        if not isinstance(dsts, dict) or key not in dsts:
            continue
        fin = bool(dsts.pop(key, False))
        changed_live = True
        if fin and (not any((int(e.get('src')) == int(src) for e in edges))):
            edges.append({'src': int(src), 'mode': 'oneway_to', 'finance': True, 'finance_only_legacy': True})
        if not dsts:
            ff.pop(str(src), None)
    pair_changed = bool(_v199_rewrite_pair_order_id(dst_chat_id, remove_only=True))
    changed_live = bool(changed_live or pair_changed)
    now_s = now_local().isoformat(timespec='seconds')
    if isinstance(existing, dict):
        existing['chat_id'] = dst_chat_id
        existing['title'] = existing.get('title') or get_chat_display_name(dst_chat_id)
        existing['reason'] = str(existing.get('reason') or reason or '')[:500]
        existing['last_reason'] = str(reason or '')[:500]
        existing['last_confirmed_at'] = now_s
        existing['edges'] = edges
        existing['auto_reactivate'] = True
        root[key] = existing
    else:
        root[key] = {'chat_id': dst_chat_id, 'title': get_chat_display_name(dst_chat_id), 'reason': str(reason or '')[:500], 'suspended_at': now_s, 'last_confirmed_at': now_s, 'edges': edges, 'auto_reactivate': True}
        changed_live = True
    try:
        fn = globals().get('set_chat_status_v150')
        lifecycle_fn = globals().get('_v150_lifecycle')
        current_status = ''
        if callable(lifecycle_fn):
            try:
                current_status = str((lifecycle_fn(dst_chat_id) or {}).get('status') or '')
            except Exception:
                current_status = ''
        # R17: a forwarding suspension must never downgrade a confirmed terminal
        # chat back to transient ``unreachable``.  The terminal lifecycle is the
        # authority that stops reminders/tasks/forwarding together.
        if callable(fn) and current_status not in {'bot_removed', 'migrated', 'archived'}:
            fn(dst_chat_id, 'unreachable', str(reason or '')[:500], source='forward_confirmed_unreachable')
    except Exception:
        pass
    if persist:
        try:
            persist_forward_rules_to_owner()
        except Exception:
            pass
        try:
            save_data(data, full=True)
        except Exception:
            save_data(data)
        try:
            schedule_config_backup_for_chats(dst_chat_id, int(OWNER_ID or 0), delay=0.5)
        except Exception:
            pass
    try:
        bot_journal('forward_target_suspended_v199', dst_chat_id, f'edges={len(edges)} reason={str(reason)[:240]}', 'WARN')
    except Exception:
        pass
    return bool(changed_live)

def reactivate_forward_target_v199(chat_id: int, *, migrated_to: int | None=None, persist: bool=True) -> bool:
    old_id = int(chat_id)
    target = int(migrated_to) if migrated_to is not None else resolve_canonical_chat_id_v199(old_id)
    root = _v199_suspended_root()
    row = root.pop(str(old_id), None)
    if row is None and target != old_id:
        row = root.pop(str(target), None)
    if not isinstance(row, dict):
        return False
    fr = data.setdefault('forward_rules', {})
    ff = data.setdefault('forward_finance', {})
    restored = 0
    for edge in row.get('edges') or []:
        try:
            src = resolve_canonical_chat_id_v199(int(edge.get('src')))
            if src == target:
                continue
            mode = edge.get('mode') or 'oneway_to'
            fr.setdefault(str(src), {})[str(target)] = mode
            if bool(edge.get('finance')):
                ff.setdefault(str(src), {})[str(target)] = True
            restored += 1
        except Exception:
            continue
    if persist:
        try:
            persist_forward_rules_to_owner()
        except Exception:
            pass
        try:
            save_data(data, full=True)
        except Exception:
            save_data(data)
    try:
        bot_journal('forward_target_reactivated_v199', target, f'from={old_id}; edges={restored}')
    except Exception:
        pass
    return True

def _v199_is_chat_not_found_error(err) -> bool:
    low = str(err or '').casefold()
    return 'chat not found' in low

def _v199_confirm_failed_forward_target(dst_chat_id: int, original_error: Exception) -> str:
    """Return migrated/suspended/transient. A single send error is never enough to suspend."""
    dst_chat_id = int(dst_chat_id)
    migrated = _handle_supergroup_migration_error(dst_chat_id, original_error)
    if migrated is not None:
        return f'migrated:{int(migrated)}'
    if not (_v199_is_chat_not_found_error(original_error) or _is_bot_removed_error(original_error)):
        return 'transient'
    try:
        bot.get_chat(dst_chat_id)
        return 'transient'
    except Exception as probe_error:
        migrated = _handle_supergroup_migration_error(dst_chat_id, probe_error)
        if migrated is not None:
            return f'migrated:{int(migrated)}'
        if _v199_is_chat_not_found_error(probe_error) or _is_bot_removed_error(probe_error):
            newly = suspend_forward_target_v199(dst_chat_id, str(probe_error)[:500], persist=True)
            if newly:
                try:
                    send_owner_technical_alert(f'⚠️ Пересылка на {get_chat_display_name(dst_chat_id)} приостановлена.\nID: {dst_chat_id}\nTelegram повторно подтвердил недоступность чата. Правила сохранены и восстановятся после успешной проверки/миграции чата.', 35)
                except Exception:
                    pass
            return 'suspended'
    return 'transient'

def _v177_legacy_0140_resolve_forward_targets(source_chat_id: int):
    with data_lock:
        fr = data.get('forward_rules', {})
        ff = data.get('forward_finance', {})
        source_raw = int(source_chat_id)
        source_canonical = resolve_canonical_chat_id_v199(source_raw)
        src = str(source_canonical if str(source_canonical) in fr else source_raw)
        if src not in fr:
            return []
        out = []
        seen = set()
        for dst, mode in list(fr[src].items()):
            try:
                raw_dst = int(dst)
                canonical_dst = resolve_canonical_chat_id_v199(raw_dst)
                if is_forward_target_suspended_v199(raw_dst) or is_forward_target_suspended_v199(canonical_dst):
                    continue
                if canonical_dst in seen:
                    continue
                seen.add(canonical_dst)
                out.append((canonical_dst, mode, bool(ff.get(src, {}).get(dst, ff.get(src, {}).get(str(canonical_dst), False)))))
            except Exception:
                continue
        return out
try:
    _v177_legacy_0140_resolve_forward_targets.__name__ = 'resolve_forward_targets'
except Exception:
    pass

def _v177_legacy_0141_add_forward_link(src_chat_id: int, dst_chat_id: int, mode: str):
    fr = data.setdefault('forward_rules', {})
    src = str(src_chat_id)
    dst = str(dst_chat_id)
    fr.setdefault(src, {})[dst] = mode
    persist_forward_rules_to_owner()
    save_data(data)
    schedule_config_backup_for_chats(src_chat_id, dst_chat_id)
try:
    _v177_legacy_0141_add_forward_link.__name__ = 'add_forward_link'
except Exception:
    pass

def _v177_legacy_0144_remove_forward_link(src_chat_id: int, dst_chat_id: int):
    fr = data.get('forward_rules', {})
    src = str(src_chat_id)
    dst = str(dst_chat_id)
    if src in fr and dst in fr[src]:
        del fr[src][dst]
    if src in fr and (not fr[src]):
        del fr[src]
    remove_forward_finance(src_chat_id, dst_chat_id)
    persist_forward_rules_to_owner()
    save_data(data)
    schedule_config_backup_for_chats(src_chat_id, dst_chat_id)
try:
    _v177_legacy_0144_remove_forward_link.__name__ = 'remove_forward_link'
except Exception:
    pass

def _v177_legacy_0145_clear_forward_all():
    """Полностью отключает всю пересылку."""
    data['forward_rules'] = {}
    data['forward_finance'] = {}
    persist_forward_rules_to_owner()
    save_data(data)
    schedule_config_backup_for_chats()
try:
    _v177_legacy_0145_clear_forward_all.__name__ = 'clear_forward_all'
except Exception:
    pass

def get_forward_finance(src_chat_id: int, dst_chat_id: int) -> bool:
    ff = data.setdefault('forward_finance', {})
    return bool(ff.get(str(src_chat_id), {}).get(str(dst_chat_id), False))
FORWARD_COPY_EDIT_MODES = ('normal', 'button', 'slash')

def _v177_legacy_0146_forward_copy_edit_mode(chat_id: int | None=None) -> str:
    """One GLOBAL 💰Перес mode for every chat/copy.

    v92-v123 stored this in owner/chat scopes. v124 imports that legacy value once and then
    keeps a single root value, so changing the mode in INFO changes all bot copies globally.
    """
    mode = ''
    try:
        gs = (data or {}).setdefault('_global_settings', {})
        mode = str(gs.get('forward_copy_edit_mode_global') or '').strip().lower()
        if mode not in FORWARD_COPY_EDIT_MODES:
            legacy = str(gs.get('forward_copy_edit_mode') or '').strip().lower()
            if legacy not in FORWARD_COPY_EDIT_MODES:
                try:
                    scope = owner_scope_id(chat_id)
                    legacy = str(owner_scoped_settings(scope).get('forward_copy_edit_mode') or '').strip().lower()
                except Exception:
                    legacy = ''
            if legacy not in FORWARD_COPY_EDIT_MODES:
                try:
                    scope = owner_scope_id(chat_id)
                    legacy = str(get_chat_store(scope).setdefault('settings', {}).get('forward_copy_edit_mode') or '').strip().lower()
                except Exception:
                    legacy = ''
            mode = legacy if legacy in FORWARD_COPY_EDIT_MODES else 'normal'
            gs['forward_copy_edit_mode_global'] = mode
            gs['forward_copy_edit_mode'] = mode
    except Exception:
        mode = 'normal'
    if mode not in FORWARD_COPY_EDIT_MODES or not version_mode_feature('forward_copy_edit'):
        return 'normal'
    return mode
try:
    _v177_legacy_0146_forward_copy_edit_mode.__name__ = 'forward_copy_edit_mode'
except Exception:
    pass

def _v177_legacy_0148_set_forward_copy_edit_mode(chat_id: int, mode: str):
    mode = str(mode or 'normal').strip().lower()
    if mode not in FORWARD_COPY_EDIT_MODES:
        mode = 'normal'
    gs = data.setdefault('_global_settings', {})
    gs['forward_copy_edit_mode_global'] = mode
    gs['forward_copy_edit_mode'] = mode
    scope_ids = []
    try:
        for scope in [int(OWNER_ID or 0)] + list(get_additional_owner_ids()):
            if not scope:
                continue
            try:
                scope = int(scope)
                owner_scoped_settings(scope)['forward_copy_edit_mode'] = mode
                get_chat_store(scope).setdefault('settings', {})['forward_copy_edit_mode'] = mode
                scope_ids.append(scope)
            except Exception:
                pass
    except Exception:
        pass
    save_data(data, chat_ids=scope_ids or None, root_only=not bool(scope_ids))
    schedule_config_backup_for_chats(*(scope_ids or []), delay=1.0)
    return mode
try:
    _v177_legacy_0148_set_forward_copy_edit_mode.__name__ = 'set_forward_copy_edit_mode'
except Exception:
    pass

def _v177_legacy_0150_cycle_forward_copy_edit_mode(chat_id: int) -> str:
    current = forward_copy_edit_mode(int(chat_id))
    try:
        idx = FORWARD_COPY_EDIT_MODES.index(current)
    except ValueError:
        idx = 0
    return set_forward_copy_edit_mode(int(chat_id), FORWARD_COPY_EDIT_MODES[(idx + 1) % len(FORWARD_COPY_EDIT_MODES)])
try:
    _v177_legacy_0150_cycle_forward_copy_edit_mode.__name__ = 'cycle_forward_copy_edit_mode'
except Exception:
    pass

def _v177_legacy_0151_forward_copy_edit_mode_label(chat_id: int) -> str:
    mode = forward_copy_edit_mode(int(chat_id))
    return {'normal': '💰Перес: обычно', 'button': '💰Перес: кнопка', 'slash': '💰Перес: слеш'}.get(mode, '💰Перес: обычно')
try:
    _v177_legacy_0151_forward_copy_edit_mode_label.__name__ = 'forward_copy_edit_mode_label'
except Exception:
    pass
try:
    FORWARD_COPY_RETRO_MIN_GAP_SECONDS = max(0.04, min(2.0, float(os.getenv('FORWARD_COPY_RETRO_MIN_GAP_SECONDS', '0.10') or '0.10')))
except Exception:
    FORWARD_COPY_RETRO_MIN_GAP_SECONDS = 0.1
try:
    FORWARD_COPY_RETRO_DAYS = max(1, min(7, int(os.getenv('FORWARD_COPY_RETRO_DAYS', '3') or '3')))
except Exception:
    FORWARD_COPY_RETRO_DAYS = 3
try:
    FORWARD_COPY_RETRO_MAX_PER_CHAT = max(3, min(30, int(os.getenv('FORWARD_COPY_RETRO_MAX_PER_CHAT', '12') or '12')))
except Exception:
    FORWARD_COPY_RETRO_MAX_PER_CHAT = 12
_FORWARD_COPY_RETRO_LOCK = threading.RLock()
_FORWARD_COPY_RETRO_GENERATION = {}

def _begin_forward_copy_retro_refresh(owner_chat_id: int) -> int:
    scope = 0
    with _FORWARD_COPY_RETRO_LOCK:
        generation = int(_FORWARD_COPY_RETRO_GENERATION.get(scope, 0) or 0) + 1
        _FORWARD_COPY_RETRO_GENERATION[scope] = generation
        return generation

def _forward_copy_retro_is_stale(owner_chat_id: int, generation: int | None) -> bool:
    if generation is None:
        return False
    with _FORWARD_COPY_RETRO_LOCK:
        return int(_FORWARD_COPY_RETRO_GENERATION.get(0, 0) or 0) != int(generation)

def _forward_copy_record_identity(chat_id: int, rec: dict):
    """Return (is_forward_copy, msg_id, src_chat_id, src_msg_id), including v92-era rows."""
    if not isinstance(rec, dict):
        return (False, 0, None, None)
    try:
        msg_id = int(rec.get('forward_dst_msg_id') or rec.get('source_msg_id') or rec.get('origin_msg_id') or rec.get('msg_id') or 0)
    except Exception:
        msg_id = 0
    if not msg_id:
        return (False, 0, None, None)
    src_chat_id = rec.get('forward_source_chat_id')
    src_msg_id = rec.get('forward_source_msg_id')
    try:
        src_chat_id = int(src_chat_id) if src_chat_id is not None else None
    except Exception:
        src_chat_id = None
    try:
        src_msg_id = int(src_msg_id) if src_msg_id is not None else None
    except Exception:
        src_msg_id = None
    if src_chat_id is None or src_msg_id is None:
        try:
            rev_chat, rev_msg = _find_forward_origin_by_copied_message(int(chat_id), int(msg_id))
            if rev_chat is not None:
                src_chat_id = int(rev_chat)
            if rev_msg is not None:
                src_msg_id = int(rev_msg)
        except Exception:
            pass
    legacy_flag = bool(rec.get('forwarded_by_bot') or rec.get('forwarded_finance') or rec.get('forward_source_chat_id') is not None)
    is_copy = bool(legacy_flag or src_chat_id is not None)
    return (is_copy, msg_id, src_chat_id, src_msg_id)

def _hydrate_legacy_forward_copy_metadata(chat_id: int, rec: dict, msg_id: int, src_chat_id=None, src_msg_id=None) -> bool:
    """Persist modern metadata when an old pre-deploy finance row is recognized as a copy."""
    changed = False
    try:
        if not rec.get('forwarded_by_bot'):
            rec['forwarded_by_bot'] = True
            changed = True
        if rec.get('forward_dst_chat_id') is None:
            rec['forward_dst_chat_id'] = int(chat_id)
            changed = True
        if rec.get('forward_dst_msg_id') is None:
            rec['forward_dst_msg_id'] = int(msg_id)
            changed = True
        if src_chat_id is not None and rec.get('forward_source_chat_id') is None:
            rec['forward_source_chat_id'] = int(src_chat_id)
            changed = True
        if src_msg_id is not None and rec.get('forward_source_msg_id') is None:
            rec['forward_source_msg_id'] = int(src_msg_id)
            changed = True
        if not rec.get('forward_copy_content_type'):
            rec['forward_copy_content_type'] = 'text'
            changed = True
        if changed:
            rid = rec.get('id')
            store = get_chat_store(int(chat_id))
            for daily_key in ('daily_records', 'ars_daily_records', 'usd_daily_records'):
                for arr in (store.get(daily_key, {}) or {}).values():
                    for rr in arr or []:
                        if not isinstance(rr, dict) or rr.get('id') != rid:
                            continue
                        if _record_has_message_id(rr, int(msg_id)):
                            rr.update(rec)
    except Exception:
        pass
    return changed

def _forward_copy_retro_record_is_recent(rec: dict, cutoff_key: str) -> bool:
    """True only for records in the bounded recent-history repaint window."""
    try:
        day = str((rec or {}).get('day_key') or '')[:10]
        if re.fullmatch('\\d{4}-\\d{2}-\\d{2}', day):
            return day >= cutoff_key
    except Exception:
        pass
    for key in ('timestamp', 'created_at', 'updated_at'):
        try:
            raw = str((rec or {}).get(key) or '')
            m = re.search('(20\\d{2}-\\d{2}-\\d{2})', raw)
            if m:
                return m.group(1) >= cutoff_key
        except Exception:
            pass
    return False

def refresh_existing_forward_copy_ui(owner_chat_id: int, mode: str | None=None, generation: int | None=None) -> int:
    """Quick repaint of only the newest bot copies.

    v124 could walk 600+ historical messages and Telegram answered 429/retry_after≈40s,
    making a cosmetic mode switch look frozen. v125 repaints at most the newest
    FORWARD_COPY_RETRO_MAX_PER_CHAT copies per chat from the last
    FORWARD_COPY_RETRO_DAYS calendar days, and interleaves chats round-robin.
    Old history is left untouched; newly created copies always use the selected mode.
    """
    owner_chat_id = int(owner_chat_id)
    mode = mode or forward_copy_edit_mode(owner_chat_id)
    try:
        today_dt = datetime.strptime(today_key(), '%Y-%m-%d').date()
        cutoff_key = (today_dt - timedelta(days=max(0, FORWARD_COPY_RETRO_DAYS - 1))).strftime('%Y-%m-%d')
    except Exception:
        cutoff_key = today_key()
    changed = 0
    attempted = 0
    hydrated = 0
    stopped_stale = False
    metadata_changed_chats = set()
    rate_limited_chats = set()
    candidates_by_chat = []
    try:
        bot_journal('forward_copy_retro_start', owner_chat_id, f'GLOBAL mode={mode} generation={generation} days={FORWARD_COPY_RETRO_DAYS} max_per_chat={FORWARD_COPY_RETRO_MAX_PER_CHAT} gap={FORWARD_COPY_RETRO_MIN_GAP_SECONDS}s')
    except Exception:
        pass
    for cid in collect_all_known_chat_ids(include_owner=True):
        if _forward_copy_retro_is_stale(owner_chat_id, generation):
            stopped_stale = True
            break
        try:
            store = get_chat_store(int(cid))
            rows = [rec for _ledger_key, rec in _finance_record_lists(store) if _forward_copy_retro_record_is_recent(rec, cutoff_key)]
            rows.sort(key=record_sort_key, reverse=True)
            seen = set()
            picked = []
            for rec in rows:
                is_copy, msg_id, src_chat_id, src_msg_id = _forward_copy_record_identity(int(cid), rec)
                if not is_copy or not msg_id or rec.get('forward_copy_deleted') or (int(msg_id) in seen):
                    continue
                seen.add(int(msg_id))
                picked.append((rec, int(msg_id), src_chat_id, src_msg_id))
                if len(picked) >= FORWARD_COPY_RETRO_MAX_PER_CHAT:
                    break
            if picked:
                candidates_by_chat.append((int(cid), picked))
        except Exception as e:
            log_error(f'refresh_existing_forward_copy_ui collect {cid}: {e}')
    max_depth = max((len(rows) for _cid, rows in candidates_by_chat), default=0)
    last_edit_mono = 0.0
    for depth in range(max_depth):
        for cid, picked in candidates_by_chat:
            if depth >= len(picked) or cid in rate_limited_chats:
                continue
            if _forward_copy_retro_is_stale(owner_chat_id, generation):
                stopped_stale = True
                break
            rec, msg_id, src_chat_id, src_msg_id = picked[depth]
            if _hydrate_legacy_forward_copy_metadata(cid, rec, msg_id, src_chat_id, src_msg_id):
                metadata_changed_chats.add(cid)
                hydrated += 1
            try:
                if last_edit_mono > 0:
                    wait = FORWARD_COPY_RETRO_MIN_GAP_SECONDS - (time.monotonic() - last_edit_mono)
                    if wait > 0:
                        time.sleep(wait)
                if _forward_copy_retro_is_stale(owner_chat_id, generation):
                    stopped_stale = True
                    break
                base_text = str(rec.get('source_finance_text') or '').strip() or compose_edit_input_value(rec.get('amount'), rec.get('note', ''))
                display_text = _forward_copy_display_text(base_text, rec, mode)
                markup = _forward_copy_edit_keyboard(mode)
                ct = str(rec.get('forward_copy_content_type') or 'text')
                attempted += 1
                last_edit_mono = time.monotonic()
                if ct == 'text':
                    _tg_call_retry(bot.edit_message_text, display_text, chat_id=cid, message_id=msg_id, reply_markup=markup, attempts=1, purpose='forward_copy_retro_text_fast')
                elif ct in {'photo', 'video', 'document', 'audio', 'animation', 'voice'}:
                    _tg_call_retry(bot.edit_message_caption, caption=display_text, chat_id=cid, message_id=msg_id, reply_markup=markup, attempts=1, purpose='forward_copy_retro_caption_fast')
                else:
                    _tg_call_retry(bot.edit_message_reply_markup, cid, msg_id, reply_markup=markup, attempts=1, purpose='forward_copy_retro_markup_fast')
                changed += 1
            except Exception as e:
                err = str(e).lower()
                if 'message is not modified' in err:
                    changed += 1
                elif 'message to edit not found' in err or 'message_id_invalid' in err or 'message not found' in err:
                    rec['forward_copy_deleted'] = True
                    metadata_changed_chats.add(cid)
                elif is_telegram_429(e):
                    rate_limited_chats.add(cid)
                    try:
                        bot_journal('forward_copy_retro_rate_skip', cid, f'msg={msg_id} mode={mode}; chat paused after 429', 'WARN')
                    except Exception:
                        pass
                else:
                    log_error(f"refresh_existing_forward_copy_ui {cid}:{rec.get('id')}: {e}")
        if stopped_stale:
            break
    for cid in metadata_changed_chats:
        try:
            store = get_chat_store(cid)
            _snapshot_active_currency_ledger(store, _ensure_currency_ledgers(store))
            save_data(data, chat_ids=[cid])
        except Exception:
            pass
    try:
        _persist_forward_index_in_data(data)
        save_data(data, root_only=True)
    except Exception:
        pass
    try:
        total_candidates = sum((len(rows) for _cid, rows in candidates_by_chat))
        bot_journal('forward_copy_retro_done', owner_chat_id, f'GLOBAL mode={mode} generation={generation} cutoff={cutoff_key} candidates={total_candidates} attempted={attempted} changed={changed} hydrated={hydrated} rate_limited_chats={len(rate_limited_chats)} stale={stopped_stale}')
    except Exception:
        pass
    return changed

def _v168_record_uid_seed(chat_id: int, rec: dict) -> str:
    """Stable seed that deliberately excludes mutable amount/note/short_id fields."""
    payload = {'chat_id': int(chat_id or 0), 'operation_key': str((rec or {}).get('operation_key') or ''), 'source_msg_id': int((rec or {}).get('source_msg_id') or 0), 'origin_msg_id': int((rec or {}).get('origin_msg_id') or 0), 'msg_id': int((rec or {}).get('msg_id') or 0), 'forward_source_chat_id': int((rec or {}).get('forward_source_chat_id') or 0), 'forward_source_msg_id': int((rec or {}).get('forward_source_msg_id') or 0), 'source_order_msg_id': int((rec or {}).get('source_order_msg_id') or 0), 'timestamp': str((rec or {}).get('timestamp') or ''), 'day_key': str((rec or {}).get('day_key') or ''), 'id': int((rec or {}).get('id') or 0), 'currency': 'usd' if bool((rec or {}).get('usd_only')) else 'ars'}
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(',', ':'))
    return hashlib.sha256(raw.encode('utf-8', errors='replace')).hexdigest()[:12].upper()

def ensure_finance_record_uid(chat_id: int, rec: dict) -> str:
    if not isinstance(rec, dict):
        return ''
    current = str(rec.get('record_uid') or '').strip().upper()
    if re.fullmatch('[A-F0-9]{12}', current):
        return current
    current = _v168_record_uid_seed(int(chat_id), rec)
    rec['record_uid'] = current
    return current

def find_finance_record_by_uid(chat_id: int, record_uid: str):
    uid = str(record_uid or '').strip().upper()
    if not re.fullmatch('[A-F0-9]{12}', uid):
        return None
    try:
        for _key, rec in _finance_record_lists(get_chat_store(int(chat_id))):
            if isinstance(rec, dict) and ensure_finance_record_uid(int(chat_id), rec) == uid:
                return rec
    except Exception:
        pass
    return None

def persist_finance_chat_local_fast(chat_id: int) -> bool:
    """Persist one finance chat without nesting data_lock -> SQLite.lock (R36)."""
    try:
        cid = int(chat_id)
        # The caller already serialises finance mutations with locked_chat(cid) on the
        # hot edit paths. get_chat_store only needs data_lock briefly; SQLite I/O must
        # happen after that global lock is released so another UI callback can render.
        store = get_chat_store(cid)
        if LOWRAM_ENABLED:
            _lowram_flush_chat(cid, store, evict=False)
            payload = _lowram_store_meta_payload(store)
        else:
            payload = store
        SQLITE.save_chat(cid, payload)
        return True
    except Exception as exc:
        try:
            log_error(f'v168 local finance persist {chat_id}: {exc}')
        except Exception:
            pass
        return False

def migrate_finance_record_uids(chat_id: int) -> int:
    changed = 0
    seen = set()
    try:
        for _key, rec in _finance_record_lists(get_chat_store(int(chat_id))):
            if not isinstance(rec, dict) or id(rec) in seen:
                continue
            seen.add(id(rec))
            before = str(rec.get('record_uid') or '')
            after = ensure_finance_record_uid(int(chat_id), rec)
            if after and after != before:
                changed += 1
        if changed:
            persist_finance_chat_local_fast(int(chat_id))
    except Exception as exc:
        try:
            log_error(f'v168 UID migration chat={chat_id}: {exc}')
        except Exception:
            pass
    return changed

def _strip_forward_copy_edit_command(text: str) -> str:
    raw = str(text or '').rstrip()
    return re.sub('(?:\\n|\\s)+/izm_[RU]\\d+(?:_u[A-F0-9]{12})?\\s*$', '', raw, flags=re.I).rstrip()

def _forward_copy_record_command(rec: dict) -> str:
    sid = str((rec or {}).get('short_id') or f"R{(rec or {}).get('id', '')}").strip().upper()
    if not re.fullmatch('[RU]\\d+', sid):
        sid = 'R' + re.sub('\\D+', '', sid)
    uid = str((rec or {}).get('record_uid') or '').strip().upper()
    return f'/izm_{sid}_u{uid}' if re.fullmatch('[A-F0-9]{12}', uid) else f'/izm_{sid}'

def _v169_forward_uid_for_copy(dst_chat_id: int, source_msg) -> str:
    """Deterministic UID known before Telegram creates the destination copy."""
    try:
        src_chat_id = int(getattr(getattr(source_msg, 'chat', None), 'id', 0) or 0)
        src_msg_id = int(getattr(source_msg, 'forward_source_msg_id', 0) or getattr(source_msg, 'message_id', 0) or 0)
        raw = f'forward-copy:{src_chat_id}:{src_msg_id}:{int(dst_chat_id)}'
        return hashlib.sha256(raw.encode('utf-8', errors='replace')).hexdigest()[:12].upper()
    except Exception:
        return ''

def _predict_forward_copy_record_command(dst_chat_id: int, source_msg, text: str) -> str | None:
    """Predict the final R/U + stable UID while caller holds locked_chat(dst_chat_id).

    The destination chat lock stays held through Telegram send + finance-row creation in
    _forward_single_to_target, so another finance insert cannot steal the predicted monthly
    position.  The UID is derived only from the immutable forwarding edge and is assigned to
    the concrete row immediately after it is created.
    """
    try:
        raw = str(text or '').strip()
        if not raw or not looks_like_amount(raw) or (not is_finance_mode(int(dst_chat_id))):
            return None
        comp = parse_financial_components(raw)
        store = get_chat_store(int(dst_chat_id))
        normalize_chat_records(int(dst_chat_id))
        day_key = finance_day_key_from_message(source_msg) if source_msg is not None else finance_today_key()
        month_key = str(day_key)[:7]
        temp = {'id': int(store.get('next_id', 1) or 1), 'day_key': str(day_key), 'timestamp': message_timestamp_iso(source_msg), 'source_order_msg_id': int(getattr(source_msg, 'message_id', 0) or 0), 'source_msg_id': 0, 'usd_only': bool(comp.get('usd_only', False)), 'usd_amount': float(comp.get('usd_amount', 0) or 0)}
        temp_key = record_sort_key(temp)
        rows = []
        for dk, arr in (store.get('daily_records', {}) or {}).items():
            if str(dk)[:7] != month_key:
                continue
            for rec in arr or []:
                if isinstance(rec, dict):
                    rows.append(rec)
        if bool(temp.get('usd_only')):
            relevant = [r for r in rows if bool(float(r.get('usd_amount', 0) or 0))]
            prefix = 'U'
        else:
            relevant = [r for r in rows if not bool(r.get('usd_only', False))]
            prefix = 'R'
        position = 1 + sum((1 for r in relevant if record_sort_key(r) < temp_key))
        uid = _v169_forward_uid_for_copy(int(dst_chat_id), source_msg)
        return f'/izm_{prefix}{position}_u{uid}' if uid else None
    except Exception as e:
        try:
            log_error(f'v169 predict forward copy command dst={dst_chat_id}: {e}')
        except Exception:
            pass
        return None

def _v169_apply_predicted_record_uid(dst_chat_id: int, rec: dict | None, command: str | None) -> dict | None:
    if not isinstance(rec, dict) or not command:
        return rec
    try:
        match = re.search('_u([A-F0-9]{12})$', str(command), flags=re.I)
        if not match:
            return rec
        uid = str(match.group(1)).upper()
        rec['record_uid'] = uid
        store = get_chat_store(int(dst_chat_id))
        rid = int(rec.get('id', -1) or -1)
        for _key, item in _finance_record_lists(store):
            try:
                if int(item.get('id', -2) or -2) == rid:
                    item['record_uid'] = uid
            except Exception:
                pass
        for arr in (store.get('daily_records', {}) or {}).values():
            for item in arr or []:
                try:
                    if int(item.get('id', -2) or -2) == rid:
                        item['record_uid'] = uid
                except Exception:
                    pass
        persist_finance_chat_local_fast(int(dst_chat_id))
    except Exception as exc:
        try:
            log_error(f'v169 apply predicted UID {dst_chat_id}: {exc}')
        except Exception:
            pass
    return rec

def _forward_copy_display_text(base_text: str, rec: dict | None, mode: str) -> str:
    base = _strip_forward_copy_edit_command(base_text)
    if mode == 'slash' and rec:
        return (base + '\n' + _forward_copy_record_command(rec)).strip()
    return base

def _forward_copy_edit_keyboard(mode: str):
    if mode != 'button':
        return None
    kb = types.InlineKeyboardMarkup()
    kb.row(IB('✏️ Изменить', callback_data='fwdcopy_edit'))
    return kb

def _forward_copy_origin_source_chat(dst_chat_id: int, dst_msg_id: int, rec: dict | None=None):
    try:
        if rec and rec.get('forward_source_chat_id') is not None:
            return int(rec.get('forward_source_chat_id'))
    except Exception:
        pass
    try:
        src_chat_id, _src_msg_id = _find_forward_origin_by_copied_message(int(dst_chat_id), int(dst_msg_id))
        return int(src_chat_id) if src_chat_id is not None else None
    except Exception:
        return None

def _set_forward_record_metadata(dst_chat_id: int, dst_msg_id: int, source_chat_id: int, source_msg):
    try:
        rec = find_record_by_message_id(int(dst_chat_id), int(dst_msg_id))
        if not rec:
            return None
        rec['forward_source_chat_id'] = int(source_chat_id)
        rec['forward_source_msg_id'] = int(getattr(source_msg, 'message_id', 0) or 0)
        rec['forward_copy_content_type'] = str(getattr(source_msg, 'content_type', 'text') or 'text')
        ensure_finance_record_uid(int(dst_chat_id), rec)
        for _key, item in _finance_record_lists(get_chat_store(int(dst_chat_id))):
            if int(item.get('id', -1)) == int(rec.get('id', -2)):
                item.update(rec)
                ensure_finance_record_uid(int(dst_chat_id), item)
        if not persist_finance_chat_local_fast(int(dst_chat_id)):
            return None
        return rec
    except Exception as e:
        log_error(f'_set_forward_record_metadata({dst_chat_id},{dst_msg_id}): {e}')
        return None

def apply_forward_copy_edit_ui(source_chat_id: int, dst_chat_id: int, dst_msg_id: int, source_msg, rec: dict | None=None) -> bool:
    """Apply edit UI only after the linked finance record is safely present in local SQLite."""
    if not version_mode_feature('forward_copy_edit'):
        return False
    mode = forward_copy_edit_mode(int(source_chat_id))
    if rec is None:
        rec = find_record_by_message_id(int(dst_chat_id), int(dst_msg_id))
    if not rec:
        rec = _set_forward_record_metadata(dst_chat_id, dst_msg_id, source_chat_id, source_msg)
    if not rec:
        log_error(f'[FWD COPY UI] record not found: {source_chat_id}->{dst_chat_id}:{dst_msg_id} mode={mode}')
        return False
    try:
        rec['forward_source_chat_id'] = int(source_chat_id)
        rec['forward_source_msg_id'] = int(getattr(source_msg, 'message_id', 0) or 0)
        rec['forward_copy_content_type'] = str(getattr(source_msg, 'content_type', 'text') or 'text')
        ensure_finance_record_uid(int(dst_chat_id), rec)
        for _key, item in _finance_record_lists(get_chat_store(int(dst_chat_id))):
            if not isinstance(item, dict):
                continue
            same_id = int(item.get('id', -1)) == int(rec.get('id', -2))
            same_msg = int(item.get('source_msg_id') or item.get('origin_msg_id') or item.get('msg_id') or 0) == int(dst_msg_id)
            if same_id or same_msg:
                item.update(rec)
                ensure_finance_record_uid(int(dst_chat_id), item)
        if not persist_finance_chat_local_fast(int(dst_chat_id)):
            log_error(f'[FWD COPY UI] local finance persist failed: {source_chat_id}->{dst_chat_id}:{dst_msg_id}')
            return False
    except Exception as exc:
        log_error(f'apply_forward_copy_edit_ui metadata {source_chat_id}->{dst_chat_id}:{dst_msg_id}: {exc}')
        return False
    try:
        base_text = _message_text_for_finance(source_msg) or compose_edit_input_value(rec.get('amount'), rec.get('note', ''))
        display_text = _forward_copy_display_text(base_text, rec, mode)
        reply_markup = _forward_copy_edit_keyboard(mode)
        ct = str(getattr(source_msg, 'content_type', None) or rec.get('forward_copy_content_type') or 'text')
        if ct == 'text':
            _tg_call_retry(bot.edit_message_text, display_text, chat_id=int(dst_chat_id), message_id=int(dst_msg_id), reply_markup=reply_markup, attempts=3, purpose='forward_copy_edit_apply_text')
        elif ct in {'photo', 'video', 'document', 'audio', 'animation', 'voice'}:
            _tg_call_retry(bot.edit_message_caption, caption=display_text, chat_id=int(dst_chat_id), message_id=int(dst_msg_id), reply_markup=reply_markup, attempts=3, purpose='forward_copy_edit_apply_caption')
        else:
            _tg_call_retry(bot.edit_message_reply_markup, chat_id=int(dst_chat_id), message_id=int(dst_msg_id), reply_markup=reply_markup, attempts=3, purpose='forward_copy_edit_apply_markup')
        try:
            schedule_config_backup_for_chats(int(dst_chat_id), delay=0.5)
        except Exception:
            pass
        return True
    except Exception as exc:
        if 'message is not modified' in str(exc).lower():
            return True
        log_error(f'apply_forward_copy_edit_ui Telegram {source_chat_id}->{dst_chat_id}:{dst_msg_id}: {exc}')
        return False

def schedule_forward_copy_edit_ui_retry(source_chat_id: int, dst_chat_id: int, dst_msg_id: int, source_msg, rec: dict | None=None, delay: float=0.8):
    """Одна отложенная повторная попытка, если Telegram ещё не дал изменить свежую copyMessage."""
    key = f'forward-copy-ui:{int(dst_chat_id)}:{int(dst_msg_id)}'

    def _job():
        try:
            apply_forward_copy_edit_ui(int(source_chat_id), int(dst_chat_id), int(dst_msg_id), source_msg, rec=rec)
        except Exception as e:
            log_error(f'schedule_forward_copy_edit_ui_retry {source_chat_id}->{dst_chat_id}:{dst_msg_id}: {e}')
    DELAYED_SCHEDULER.cancel(key)
    DELAYED_SCHEDULER.schedule(key, float(delay), _job)

def _forward_copy_edit_wait_scheduler_key(chat_id: int) -> str:
    return f'forward-copy-edit-wait:{int(chat_id)}'

def _forward_copy_clean_copy_button(text: str):
    """Compatibility helper kept for old code paths; v125 uses the main edit insert UX."""
    return make_copy_or_inline_button('✍️ Вставить текст', '\n' + str(text or ''), viewer_chat_id=None)

def _forward_copy_edit_prompt_text(rec: dict, current: str) -> str:
    sid = str(rec.get('short_id') or 'R' + str(rec.get('id')))
    return wm_common(f'✏️ Редактирование записи {sid}\n\nТекущие данные:\n{current}\n\n✍️ Напишите новые данные.\nБудет изменена эта бот-копия и связанная финансовая запись.\n\n⏳ Это сообщение и режим редактирования будут автоматически отменены через 40 секунд.', 10)

def _forward_copy_edit_prompt_keyboard(current: str, day_key: str | None=None, chat_id: int | None=None):
    kb = types.InlineKeyboardMarkup()
    day_key = str(day_key or today_key())[:10]
    chat_type = ''
    try:
        if chat_id is not None:
            chat_type = str((get_chat_store(int(chat_id)).get('info') or {}).get('type') or '').lower()
    except Exception:
        chat_type = ''
    if current:
        kb.row(make_copy_or_inline_button('✍️ Вставить текст', '\n' + str(current), viewer_chat_id=chat_id))
    kb.row(IB('❌ Закрыть', callback_data='fwdcopy_edit_cancel'), IB('⬅️ Назад осн. окно', callback_data=f'd:{day_key}:back_main'))
    return kb

def refresh_active_forward_copy_edit_prompt(chat_id: int, dst_msg_id: int, rec: dict | None=None) -> bool:
    """Keep an already-open 💰Перес edit window synchronized with auto-edited bot copies."""
    try:
        chat_id = int(chat_id)
        dst_msg_id = int(dst_msg_id)
        store = get_chat_store(chat_id)
        wait = store.get('forward_copy_edit_wait') or {}
        if wait.get('type') != 'forward_copy_edit' or int(wait.get('dst_msg_id') or 0) != dst_msg_id:
            return False
        rec = rec or find_record_by_message_id(chat_id, dst_msg_id)
        if not isinstance(rec, dict):
            return False
        current = str(rec.get('source_finance_text') or '').strip()
        if not current:
            current = compose_edit_input_value(rec.get('amount'), rec.get('note', ''))
        wait['insert_text'] = current
        prompt = _forward_copy_edit_prompt_text(rec, current)
        wait['countdown_base_text'] = prompt
        store['forward_copy_edit_wait'] = wait
        prompt_id = int(wait.get('prompt_msg_id') or 0)
        if prompt_id:
            try:
                _tg_call_retry(bot.edit_message_text, prompt, chat_id=chat_id, message_id=prompt_id, reply_markup=_forward_copy_edit_prompt_keyboard(current, rec.get('day_key'), chat_id=chat_id), purpose='forward_copy_edit_prompt_refresh')
            except Exception as e:
                if 'message is not modified' not in str(e).lower():
                    log_error(f'refresh_active_forward_copy_edit_prompt({chat_id},{dst_msg_id}): {e}')
        return True
    except Exception as e:
        log_error(f'refresh_active_forward_copy_edit_prompt({chat_id},{dst_msg_id}): {e}')
        return False

def clear_forward_copy_edit_wait(chat_id: int, delete_prompt: bool=True):
    store = get_chat_store(int(chat_id))
    wait = store.get('forward_copy_edit_wait') or {}
    prompt_id = wait.get('prompt_msg_id')
    force_reply_msg_id = wait.get('force_reply_msg_id')
    DELAYED_SCHEDULER.cancel(_forward_copy_edit_wait_scheduler_key(int(chat_id)))
    store['forward_copy_edit_wait'] = None
    if delete_prompt:
        for _mid in (prompt_id, force_reply_msg_id):
            if not _mid:
                continue
            try:
                bot.delete_message(int(chat_id), int(_mid))
            except Exception:
                pass

def schedule_forward_copy_edit_wait_cancel(chat_id: int, prompt_message_id: int, delay: float | None=None):
    if delay is None:
        delay = internal_timer_seconds('input_wait', 40)

    def _job():
        try:
            store = get_chat_store(int(chat_id))
            wait = store.get('forward_copy_edit_wait') or {}
            if int(wait.get('prompt_msg_id') or 0) != int(prompt_message_id):
                return
            clear_forward_copy_edit_wait(int(chat_id), delete_prompt=True)
            bot_journal('forward_copy_edit_timeout', int(chat_id), f'prompt={prompt_message_id}; window deleted')
        except Exception as e:
            log_error(f'schedule_forward_copy_edit_wait_cancel({chat_id}): {e}')
    DELAYED_SCHEDULER.cancel(_forward_copy_edit_wait_scheduler_key(int(chat_id)))
    DELAYED_SCHEDULER.schedule(_forward_copy_edit_wait_scheduler_key(int(chat_id)), float(delay), _job)

def start_forward_copy_edit(chat_id: int, dst_msg_id: int) -> bool:
    rec = find_record_by_message_id(int(chat_id), int(dst_msg_id))
    if not rec:
        send_and_auto_delete(int(chat_id), '❌ Связанная финансовая запись не найдена.', 8)
        return False
    is_copy, _msg_id, source_chat_id, source_msg_id = _forward_copy_record_identity(int(chat_id), rec)
    if not is_copy:
        send_and_auto_delete(int(chat_id), '❌ Это сообщение не связано с бот-копией пересылки.', 8)
        return False
    _hydrate_legacy_forward_copy_metadata(int(chat_id), rec, int(dst_msg_id), source_chat_id, source_msg_id)
    current = str(rec.get('source_finance_text') or '').strip()
    if not current:
        if float(rec.get('usd_amount', 0) or 0) and bool(rec.get('usd_only', False)):
            current = compose_edit_input_value(rec.get('usd_amount'), rec.get('usd_note') or rec.get('note', ''))
        else:
            current = compose_edit_input_value(rec.get('amount'), rec.get('note', ''))
    prompt = _forward_copy_edit_prompt_text(rec, current)
    sent = _tg_call_retry(bot.send_message, int(chat_id), prompt, reply_markup=_forward_copy_edit_prompt_keyboard(current, rec.get('day_key'), chat_id=int(chat_id)), purpose='forward_copy_edit_prompt')
    force_msg_id = 0
    get_chat_store(int(chat_id))['forward_copy_edit_wait'] = {'type': 'forward_copy_edit', 'dst_msg_id': int(dst_msg_id), 'rid': int(rec.get('id')), 'record_uid': ensure_finance_record_uid(int(chat_id), rec), 'source_chat_id': int(source_chat_id or 0), 'prompt_msg_id': int(sent.message_id), 'force_reply_msg_id': int(force_msg_id or 0), 'insert_text': current, 'countdown_base_text': prompt, 'expires_at': time.time() + 40}
    schedule_forward_copy_edit_wait_cancel(int(chat_id), int(sent.message_id), None)
    return True

def edit_forward_copy_and_record(chat_id: int, dst_msg_id: int, new_text: str) -> bool:
    clean_text = sanitize_telegram_inserted_text(str(new_text or '').strip())
    try:
        comp = parse_financial_components(clean_text)
        amount, note = (comp['amount'], comp['note'])
    except Exception:
        return False
    rec = find_record_by_message_id(int(chat_id), int(dst_msg_id))
    if not rec:
        return False
    rid = int(rec.get('id'))
    day_key = rec.get('day_key') or today_key()
    is_copy, _msg_id, source_chat_id, source_msg_id = _forward_copy_record_identity(int(chat_id), rec)
    if not is_copy:
        return False
    _hydrate_legacy_forward_copy_metadata(int(chat_id), rec, int(dst_msg_id), source_chat_id, source_msg_id)
    with locked_chat(int(chat_id)):
        if not update_record_in_chat(int(chat_id), rid, amount, note, source_finance_text=str(comp.get('source_finance_text') or clean_text), source_msg_id=int(dst_msg_id)):
            return False
        rec = find_record_by_message_id(int(chat_id), int(dst_msg_id))
        if rec is not None:
            rec['source_finance_text'] = str(comp.get('source_finance_text') or clean_text)
            if comp.get('usd_amount') is not None:
                rec['usd_amount'] = float(comp.get('usd_amount') or 0)
                rec['usd_note'] = str(comp.get('usd_note') or '')
                rec['usd_only'] = bool(comp.get('usd_only', False))
            elif rec.get('usd_amount') is not None:
                rec['usd_amount'] = 0.0
                rec['usd_note'] = ''
                rec['usd_only'] = False
            # R7: amount/note edit keeps monthly IDs unchanged.
            try:
                ensure_finance_record_uid(int(chat_id), rec)
            except Exception:
                pass
            if not persist_finance_chat_local_fast(int(chat_id)):
                return False
            try:
                schedule_financial_window_refresh(int(chat_id), str(day_key), reason='forward_copy_edit_immediate_v168')
            except Exception:
                pass
    mode = forward_copy_edit_mode(int(chat_id))
    display_text = _forward_copy_display_text(clean_text, rec, mode)
    reply_markup = _forward_copy_edit_keyboard(mode)
    ct = str((rec or {}).get('forward_copy_content_type') or 'text')
    try:
        if ct == 'text':
            _tg_call_retry(bot.edit_message_text, display_text, chat_id=int(chat_id), message_id=int(dst_msg_id), reply_markup=reply_markup, purpose='forward_copy_manual_edit')
        elif ct in {'photo', 'video', 'document', 'audio', 'animation', 'voice'}:
            _tg_call_retry(bot.edit_message_caption, caption=display_text, chat_id=int(chat_id), message_id=int(dst_msg_id), reply_markup=reply_markup, purpose='forward_copy_manual_edit')
        else:
            return False
    except Exception as e:
        if 'message is not modified' not in str(e).lower():
            log_error(f'edit_forward_copy_and_record({chat_id},{dst_msg_id}): {e}')
            return False
    _durable_note_source_consumed('forward_copy_manual_edit')
    if isinstance(rec, dict):
        _durable_note_record_edit_witness(_durable_record_edit_witness(int(chat_id), rid, amount=rec.get('amount', 0), note=rec.get('note', ''), source_finance_text=rec.get('source_finance_text', ''), usd_amount=rec.get('usd_amount') if rec.get('usd_amount') is not None else None, usd_note=rec.get('usd_note') if rec.get('usd_amount') is not None else None, kind='forward_copy_edit'))
    finance_changed(int(chat_id), day_key, reason='forward_copy_manual_edit', delay=0.1)
    return True

def _has_visible_fin_mode_selected(chat_id: int) -> bool:
    """v108: visible auto-window selection is independent from hidden accounting."""
    try:
        return bool(is_finance_mode(chat_id) and finance_window_mode(chat_id) in {'normal', 'open', 'first'})
    except Exception:
        return False

def _v177_legacy_0152_ensure_hidden_finance_for_forward_dst(dst_chat_id: int):
    """💰 forwarding enables hidden accounting without touching an already selected visible window mode."""
    try:
        dst_chat_id = int(dst_chat_id)
        was_finance = is_finance_mode(dst_chat_id)
        if not was_finance:
            set_finance_mode(dst_chat_id, True)
            set_finance_window_mode(dst_chat_id, 'off', persist_now=False)
        if not is_hidden_finance_mode(dst_chat_id):
            set_hidden_finance_mode(dst_chat_id, True)
        _persist_finance_window_mode_critical(dst_chat_id)
        bot_journal('forward_finance_auto_hidden', dst_chat_id, '💰 учёт пересылки включил скрытые финансы; оконный режим сохранён')
    except Exception as e:
        log_error(f'ensure_hidden_finance_for_forward_dst({dst_chat_id}): {e}')
try:
    _v177_legacy_0152_ensure_hidden_finance_for_forward_dst.__name__ = 'ensure_hidden_finance_for_forward_dst'
except Exception:
    pass

def _v177_legacy_0153_set_forward_finance(src_chat_id: int, dst_chat_id: int, enabled: bool):
    ff = data.setdefault('forward_finance', {})
    src = str(src_chat_id)
    dst = str(dst_chat_id)
    ff.setdefault(src, {})[dst] = bool(enabled)
    if bool(enabled):
        ensure_hidden_finance_for_forward_dst(int(dst_chat_id))
    persist_forward_rules_to_owner()
    save_data(data)
    schedule_config_backup_for_chats(src_chat_id, dst_chat_id)
try:
    _v177_legacy_0153_set_forward_finance.__name__ = 'set_forward_finance'
except Exception:
    pass

def _v177_legacy_0154_remove_forward_finance(src_chat_id: int, dst_chat_id: int):
    ff = data.setdefault('forward_finance', {})
    src = str(src_chat_id)
    dst = str(dst_chat_id)
    if src in ff and dst in ff[src]:
        del ff[src][dst]
    if src in ff and (not ff[src]):
        del ff[src]
    persist_forward_rules_to_owner()
    save_data(data)
    schedule_config_backup_for_chats(src_chat_id, dst_chat_id)
try:
    _v177_legacy_0154_remove_forward_finance.__name__ = 'remove_forward_finance'
except Exception:
    pass

def _forward_key(src_chat_id: int, src_msg_id: int) -> str:
    return f'{int(src_chat_id)}:{int(src_msg_id)}'

def _schedule_persist_forward_state(delay: float=0.25):
    global _forward_state_timer

    def _job():
        try:
            save_data(data, root_only=True)
        except Exception as e:
            log_error(f'_schedule_persist_forward_state: {e}')
    scheduler_key = 'forward-state-save'
    DELAYED_SCHEDULER.cancel(scheduler_key)
    _forward_state_timer = DELAYED_SCHEDULER.schedule(scheduler_key, delay, _job)

def _persist_forward_index_in_data(d: dict):
    with forward_map_lock:
        idx = {}
        for (src_chat_id, src_msg_id), pairs in forward_map.items():
            rows = []
            for pair in pairs:
                if not isinstance(pair, (list, tuple)) or len(pair) < 2:
                    continue
                dst_chat_id, dst_msg_id = (pair[0], pair[1])
                rows.append({'dst_chat_id': int(dst_chat_id), 'dst_msg_id': int(dst_msg_id), 'status': 'delivered'})
            if rows:
                idx[_forward_key(src_chat_id, src_msg_id)] = rows
        d['forward_index'] = idx

def _load_forward_index_from_data(d: dict):
    with forward_map_lock:
        forward_map.clear()
        idx = d.get('forward_index', {}) or {}
        for key, rows in idx.items():
            try:
                src_chat_id_s, src_msg_id_s = str(key).split(':', 1)
                src_chat_id = int(src_chat_id_s)
                src_msg_id = int(src_msg_id_s)
            except Exception:
                continue
            pairs = []
            for row in rows or []:
                try:
                    dst_chat_id = int(row.get('dst_chat_id'))
                    dst_msg_id = int(row.get('dst_msg_id'))
                    pairs.append((dst_chat_id, dst_msg_id))
                except Exception:
                    continue
            if pairs:
                forward_map[src_chat_id, src_msg_id] = pairs

def _store_forward_link(src_chat_id: int, src_msg_id: int, dst_chat_id: int, dst_msg_id: int):
    with forward_map_lock:
        key = (int(src_chat_id), int(src_msg_id))
        pair = (int(dst_chat_id), int(dst_msg_id))
        items = forward_map.setdefault(key, [])
        if pair not in items:
            items.append(pair)
    _schedule_persist_forward_state()

def _v177_legacy_0155_persist_forward_finance_delivery_now(src_chat_id: int, src_msg_id: int, dst_chat_id: int, dst_msg_id: int, rec: dict | None=None):
    """v260: synchronously commit only the local exact-once binding; remote backup is async."""
    try:
        if isinstance(rec, dict):
            tags = {'forwarded_by_bot': True, 'forward_source_chat_id': int(src_chat_id), 'forward_source_msg_id': int(src_msg_id), 'forward_dst_chat_id': int(dst_chat_id), 'forward_dst_msg_id': int(dst_msg_id), 'operation_key': _v260_forward_finance_operation_key(src_chat_id, src_msg_id, dst_chat_id)}
            rec.update(tags)
            store = get_chat_store(int(dst_chat_id)); rid = rec.get('id')
            for arr in (store.get('daily_records', {}) or {}).values():
                for rr in arr or []:
                    if isinstance(rr, dict) and rr.get('id') == rid: rr.update(tags)
            try: _remember_finance_source_identity_v257(int(dst_chat_id), rec, int(dst_msg_id), 'records')
            except Exception: pass
            if 'persist_finance_chat_local_fast' in globals() and not persist_finance_chat_local_fast(int(dst_chat_id)):
                raise RuntimeError('local finance SQLite commit failed')
            _v260_forward_finance_op_mark(src_chat_id, src_msg_id, dst_chat_id, 'committed', dst_msg_id=int(dst_msg_id), record_uid=str(rec.get('record_uid') or ''), record_id=int(rec.get('id') or 0))
        _persist_forward_index_in_data(data)
        try:
            pool = globals().get('BACKGROUND_TASK_POOL')
            if pool is not None:
                pool.submit_unique(f'fwd-root-v260:{src_chat_id}:{src_msg_id}:{dst_chat_id}', save_data, data, root_only=True)
        except Exception:
            pass
        def _remote_after_local():
            try:
                ok = persist_critical_delta_now(int(dst_chat_id))
                if not ok: schedule_quick_backup(int(dst_chat_id), MEGA_DELTA_PRIORITY_DELAY_SECONDS)
            except Exception as exc:
                log_error(f'[FWD FINANCE ASYNC BACKUP] {src_chat_id}:{src_msg_id}->{dst_chat_id}:{dst_msg_id}: {exc}')
        try:
            pool = globals().get('DELTA_TASK_POOL') or globals().get('BACKGROUND_TASK_POOL')
            if pool is not None:
                pool.submit_unique(f'fwd-delta-v260:{src_chat_id}:{src_msg_id}:{dst_chat_id}', _remote_after_local)
        except Exception:
            pass
        log_info(f'[FWD FINANCE DURABLE] local committed; remote async {src_chat_id}:{src_msg_id} -> {dst_chat_id}:{dst_msg_id}')
        return True
    except Exception as e:
        _v260_forward_finance_op_mark(src_chat_id, src_msg_id, dst_chat_id, 'partial_finance_missing', dst_msg_id=int(dst_msg_id), last_error=str(e)[:300])
        log_error(f'[FWD FINANCE DURABLE ERROR] {src_chat_id}:{src_msg_id} -> {dst_chat_id}:{dst_msg_id}: {e}')
        return False

try:
    _v177_legacy_0155_persist_forward_finance_delivery_now.__name__ = '_persist_forward_finance_delivery_now'
except Exception:
    pass

def _rebuild_forward_index_from_finance_records(d: dict) -> int:
    """После restore восстанавливает forward_index, сканируя по одному чату без удержания всей истории в RAM."""
    added = 0
    try:
        with forward_map_lock:
            for cid, store in ((d or {}).get('chats', {}) or {}).items():
                if not isinstance(store, dict):
                    continue
                try:
                    cid_i = int(cid)
                except Exception:
                    continue
                if LOWRAM_ENABLED and (not dict.__contains__(store, 'records')):
                    rows = SQLITE.get_cold(cid_i, 'records', []) or []
                else:
                    rows = store.get('records', []) or []
                for rec in rows:
                    if not isinstance(rec, dict) or not rec.get('forwarded_by_bot'):
                        continue
                    try:
                        src_chat = int(rec.get('forward_source_chat_id'))
                        src_msg = int(rec.get('forward_source_msg_id'))
                        dst_chat = int(rec.get('forward_dst_chat_id') or cid_i)
                        dst_msg = int(rec.get('forward_dst_msg_id') or rec.get('source_msg_id') or rec.get('msg_id'))
                    except Exception:
                        continue
                    key = (src_chat, src_msg)
                    pair = (dst_chat, dst_msg)
                    rows_map = forward_map.setdefault(key, [])
                    if pair not in rows_map:
                        rows_map.append(pair)
                        added += 1
                rows = None
            if added:
                _persist_forward_index_in_data(d)
        if added:
            log_info(f'[FORWARD INDEX RECOVERY] rebuilt {added} links from SQLite finance records')
        return added
    except Exception as e:
        log_error(f'_rebuild_forward_index_from_finance_records: {e}')
        return 0

def get_forward_links(src_chat_id: int, src_msg_id: int):
    with forward_map_lock:
        return list(forward_map.get((int(src_chat_id), int(src_msg_id)), []))

def delete_forward_copies_for_source(src_chat_id: int, src_msg_id: int):
    key = (int(src_chat_id), int(src_msg_id))
    with forward_map_lock:
        links = list(forward_map.get(key, []))
    for dst_chat_id, dst_msg_id in links:
        try:
            bot.delete_message(dst_chat_id, dst_msg_id)
        except Exception as e:
            log_error(f'delete_forward_copies_for_source {src_chat_id}:{src_msg_id} -> {dst_chat_id}:{dst_msg_id}: {e}')
        try:
            with locked_chat(dst_chat_id):
                delete_forwarded_finance_record_by_msg_id(dst_chat_id, dst_msg_id)
        except Exception as e:
            log_error(f'delete_forwarded_finance_record_by_msg_id {dst_chat_id}:{dst_msg_id}: {e}')
    with forward_map_lock:
        if key in forward_map:
            del forward_map[key]
            _schedule_persist_forward_state()

def is_forward_delete_command(text: str) -> bool:
    t = (text or '').strip().lower()
    return t in ('/del', '/дел', '/д')

def _finance_record_lists(store: dict):
    """Active + persistent currency ledgers, active first; duplicate objects are skipped."""
    seen = set()
    for key in ('records', 'ars_records', 'usd_records'):
        arr = store.get(key, []) or []
        if not isinstance(arr, list):
            continue
        for rec in arr:
            if not isinstance(rec, dict):
                continue
            oid = id(rec)
            if oid in seen:
                continue
            seen.add(oid)
            yield (key, rec)

def _finance_source_index_v257(store: dict) -> dict:
    idx = store.setdefault('_finance_source_index_v257', {})
    if not isinstance(idx, dict):
        idx = {}
        store['_finance_source_index_v257'] = idx
    return idx


def _record_message_ids_v257(rec: dict) -> set[int]:
    out = set()
    for key in ('forward_dst_msg_id', 'source_msg_id', 'origin_msg_id', 'msg_id', 'source_order_msg_id'):
        try:
            value = int((rec or {}).get(key) or 0)
            if value: out.add(value)
        except Exception:
            pass
    try:
        op = str((rec or {}).get('operation_key') or '')
        m = re.fullmatch(r'finance:-?\d+:[^:]+:(\d+)', op)
        if m: out.add(int(m.group(1)))
    except Exception:
        pass
    return out


def _remember_finance_source_identity_v257(chat_id: int, rec: dict, msg_id: int | None=None, ledger: str='records') -> bool:
    if not isinstance(rec, dict):
        return False
    try:
        cid = int(chat_id)
        mid = int(msg_id or 0)
    except Exception:
        return False
    if not mid:
        mids = _record_message_ids_v257(rec)
        mid = min(mids) if mids else 0
    if not mid:
        return False
    store = get_chat_store(cid)
    try:
        uid = ensure_finance_record_uid(cid, rec) if 'ensure_finance_record_uid' in globals() else str(rec.get('record_uid') or '')
    except Exception:
        uid = str(rec.get('record_uid') or '')
    row = {'record_uid': str(uid or ''), 'id': int(rec.get('id') or 0), 'ledger': str(ledger or 'records'), 'operation_key': str(rec.get('operation_key') or '')}
    _finance_source_index_v257(store)[str(mid)] = row
    # Heal old restored records: message identity is immutable and must not vanish.
    for key in ('source_msg_id', 'origin_msg_id', 'msg_id'):
        if not rec.get(key): rec[key] = mid
    if not rec.get('source_order_msg_id'): rec['source_order_msg_id'] = mid
    if not rec.get('operation_key') and 'finance_operation_key' in globals():
        try: rec['operation_key'] = finance_operation_key(cid, mid, 'main')
        except Exception: pass
    return True


def _record_has_message_id(rec: dict, msg_id: int) -> bool:
    try:
        mid = int(msg_id)
    except Exception:
        return False
    return mid in _record_message_ids_v257(rec)


def find_record_by_message_id(chat_id: int, msg_id: int):
    cid = int(chat_id); mid = int(msg_id)
    store = get_chat_store(cid)
    for key, r in _finance_record_lists(store):
        if _record_has_message_id(r, mid):
            _remember_finance_source_identity_v257(cid, r, mid, key)
            return r
    # Redundant persistent index survives deployment and heals a partially
    # normalized/restored record that lost one of its legacy message-id aliases.
    ref = _finance_source_index_v257(store).get(str(mid)) or {}
    uid = str(ref.get('record_uid') or '').strip().upper()
    rid = int(ref.get('id') or 0) if str(ref.get('id') or '').lstrip('-').isdigit() else 0
    ledger = str(ref.get('ledger') or '')
    for key, r in _finance_record_lists(store):
        try:
            if uid and str(r.get('record_uid') or '').strip().upper() == uid:
                _remember_finance_source_identity_v257(cid, r, mid, key); return r
            if rid and key == ledger and int(r.get('id') or 0) == rid:
                _remember_finance_source_identity_v257(cid, r, mid, key); return r
        except Exception:
            pass
    return None


def migrate_finance_source_index_v257(chat_id: int) -> int:
    cid=int(chat_id); store=get_chat_store(cid); changed=0
    for key, rec in _finance_record_lists(store):
        mids=_record_message_ids_v257(rec)
        for mid in mids:
            before=dict(_finance_source_index_v257(store).get(str(mid)) or {})
            if _remember_finance_source_identity_v257(cid, rec, mid, key):
                after=_finance_source_index_v257(store).get(str(mid)) or {}
                if before != after: changed += 1
    return changed

def delete_forwarded_finance_record_by_msg_id(chat_id: int, msg_id: int) -> bool:
    with locked_chat(chat_id):
        rec = find_record_by_message_id(chat_id, msg_id)
        if not rec:
            return False
        day_key = rec.get('day_key') or today_key()
        delete_record_in_chat(chat_id, rec['id'])
        schedule_finalize(chat_id, day_key)
        return True

def rebind_forwarded_finance_record(chat_id: int, old_msg_id: int, new_msg_id: int, text: str, owner: int=0, source_msg=None):
    with locked_chat(chat_id):
        store = get_chat_store(chat_id)
        rec = find_record_by_message_id(chat_id, old_msg_id)
        if rec is None and source_msg is not None:
            rec = _v260_find_forward_finance_record(int(chat_id), int(old_msg_id), source_msg)
        if rec:
            rec['source_msg_id'] = new_msg_id
            rec['origin_msg_id'] = new_msg_id
            rec['msg_id'] = new_msg_id
            rec['source_finance_text'] = str(text or '').strip()
            if text and looks_like_amount(text):
                try:
                    comp = parse_financial_components(text)
                    rec['amount'] = comp.get('amount', 0.0)
                    rec['note'] = comp.get('note', '')
                    if comp.get('usd_amount') is not None:
                        rec['usd_amount'] = float(comp.get('usd_amount') or 0)
                        rec['usd_note'] = str(comp.get('usd_note') or '')
                        rec['usd_only'] = bool(comp.get('usd_only', False))
                    elif rec.get('usd_amount') is not None:
                        rec['usd_amount'] = 0.0
                        rec['usd_note'] = ''
                        rec['usd_only'] = False
                except Exception:
                    pass
            rec_id = rec.get('id')
            for day, arr in store.get('daily_records', {}).items():
                for item in arr:
                    if item.get('id') == rec_id:
                        item.update(rec)
            store['balance'] = sum((r.get('amount', 0) for r in store.get('records', [])))
            # R7: rebind/edit does not change chronology; persist now and rebuild
            # derived aggregates once in the common finalize path.
            try:
                persist_finance_chat_local_fast(int(chat_id))
            except Exception:
                pass
            schedule_finalize(chat_id, rec.get('day_key') or today_key())
            return True
        if text and looks_like_amount(text):
            sync_forwarded_finance_message(chat_id, new_msg_id, text, owner, source_msg=source_msg)
            return True
        return False

def _replace_forward_link_pair(src_chat_id: int, src_msg_id: int, old_dst_chat_id: int, old_dst_msg_id: int, new_dst_chat_id: int, new_dst_msg_id: int):
    with forward_map_lock:
        key = (int(src_chat_id), int(src_msg_id))
        pairs = list(forward_map.get(key, []))
        updated = []
        replaced = False
        for pair in pairs:
            if int(pair[0]) == int(old_dst_chat_id) and int(pair[1]) == int(old_dst_msg_id):
                updated.append((int(new_dst_chat_id), int(new_dst_msg_id)))
                replaced = True
            else:
                updated.append(pair)
        if not replaced:
            updated.append((int(new_dst_chat_id), int(new_dst_msg_id)))
        forward_map[key] = updated
    _schedule_persist_forward_state()

def _v212_task_reconcile_forward_copy(dst_chat_id: int, dst_msg_id: int, source_chat_id: int, source_msg, *, is_edit: bool=False, previous_message_id: int=0):
    fn = globals().get('task_reconcile_source_message')
    if not callable(fn):
        return None
    try:
        body = str(_message_text_for_finance(source_msg) or getattr(source_msg, 'caption', None) or getattr(source_msg, 'text', None) or '')
        sender = getattr(source_msg, 'from_user', None)
        return fn(int(dst_chat_id), int(dst_msg_id), body, original_date=(globals().get('_v172_now')() if callable(globals().get('_v172_now')) else now_local()) if not is_edit else getattr(source_msg, 'date', None), sender_id=int(getattr(sender, 'id', 0) or 0), sender_name=getattr(sender, 'first_name', '') or getattr(sender, 'username', '') or '', sender_is_bot=True, trusted_forwarding_copy=True, origin_chat_id=int(source_chat_id), origin_message_id=int(getattr(source_msg, 'message_id', 0) or 0), is_edit=bool(is_edit), previous_message_id=int(previous_message_id or 0), content_type=str(getattr(source_msg, 'content_type', '') or 'text'))
    except Exception as exc:
        try:
            log_error(f'v212 forwarding task reconcile {dst_chat_id}:{dst_msg_id}: {exc}')
        except Exception:
            pass
        return None

def _v260_forward_finance_op_key(source_chat_id: int, source_msg_id: int, dst_chat_id: int) -> str:
    return f"{int(source_chat_id)}:{int(source_msg_id)}:{int(dst_chat_id)}"

def _v260_forward_finance_operation_key(source_chat_id: int, source_msg_id: int, dst_chat_id: int) -> str:
    return f"fwd-fin:{int(source_chat_id)}:{int(source_msg_id)}:{int(dst_chat_id)}"

def _v260_forward_finance_op_get(source_chat_id: int, source_msg_id: int, dst_chat_id: int) -> dict:
    try:
        return SQLITE.get_meta('forward_finance_ops_v260', _v260_forward_finance_op_key(source_chat_id, source_msg_id, dst_chat_id), {}) or {}
    except Exception:
        return {}

def _v260_forward_finance_op_mark(source_chat_id: int, source_msg_id: int, dst_chat_id: int, state: str, **extra) -> dict:
    key = _v260_forward_finance_op_key(source_chat_id, source_msg_id, dst_chat_id)
    row = _v260_forward_finance_op_get(source_chat_id, source_msg_id, dst_chat_id)
    row.update({
        'source_chat_id': int(source_chat_id), 'source_msg_id': int(source_msg_id),
        'dst_chat_id': int(dst_chat_id), 'state': str(state or ''),
        'updated_at': now_local().isoformat(timespec='milliseconds'),
        'operation_key': _v260_forward_finance_operation_key(source_chat_id, source_msg_id, dst_chat_id),
    })
    row.update({k:v for k,v in extra.items() if v is not None})
    try:
        SQLITE.set_meta('forward_finance_ops_v260', key, row)
    except Exception as exc:
        log_error(f'[FWD FIN V260] op persist {key}: {exc}')
    return row

def _v260_find_forward_finance_record(dst_chat_id: int, dst_msg_id: int, source_msg=None):
    try:
        rec = find_record_by_message_id(int(dst_chat_id), int(dst_msg_id))
        if isinstance(rec, dict):
            return rec
    except Exception:
        pass
    if source_msg is None:
        return None
    try:
        src_chat_id = int(getattr(getattr(source_msg, 'chat', None), 'id', 0) or 0)
        src_msg_id = int(getattr(source_msg, 'forward_source_msg_id', 0) or getattr(source_msg, 'message_id', 0) or 0)
    except Exception:
        return None
    if not src_chat_id or not src_msg_id:
        return None
    op_key = _v260_forward_finance_operation_key(src_chat_id, src_msg_id, int(dst_chat_id))
    try:
        rec = find_record_by_operation_key(int(dst_chat_id), op_key)
        if isinstance(rec, dict):
            return rec
    except Exception:
        pass
    try:
        for _ledger, rec in _finance_record_lists(int(dst_chat_id)):
            if not isinstance(rec, dict):
                continue
            if int(rec.get('forward_source_chat_id') or 0) == src_chat_id and int(rec.get('forward_source_msg_id') or 0) == src_msg_id:
                return rec
    except Exception:
        pass
    return None

def _v260_bind_forward_finance_record(rec: dict, source_msg, dst_chat_id: int, dst_msg_id: int) -> dict:
    if not isinstance(rec, dict) or source_msg is None:
        return rec
    try:
        src_chat_id = int(getattr(getattr(source_msg, 'chat', None), 'id', 0) or 0)
        src_msg_id = int(getattr(source_msg, 'forward_source_msg_id', 0) or getattr(source_msg, 'message_id', 0) or 0)
    except Exception:
        return rec
    if not src_chat_id or not src_msg_id:
        return rec
    rec.update({
        'forwarded_by_bot': True,
        'forward_source_chat_id': src_chat_id,
        'forward_source_msg_id': src_msg_id,
        'forward_dst_chat_id': int(dst_chat_id),
        'forward_dst_msg_id': int(dst_msg_id),
        'operation_key': _v260_forward_finance_operation_key(src_chat_id, src_msg_id, int(dst_chat_id)),
    })
    try:
        _remember_finance_source_identity_v257(int(dst_chat_id), rec, int(dst_msg_id), 'records')
    except Exception:
        pass
    return rec

def _v260_make_forward_shadow(source_chat_id: int, source_msg_id: int, dst_chat_id: int, dst_msg_id: int, owner: int=0, source_date=None):
    chat = type('ForwardSourceChatV260', (), {'id': int(source_chat_id)})()
    user = type('ForwardSourceUserV260', (), {'id': int(owner or 0)})()
    return type('ForwardShadowMsgV260', (), {
        'message_id': int(dst_msg_id),
        'date': source_date if source_date is not None else int(time.time()),
        'forward_source_msg_id': int(source_msg_id),
        'source_order_msg_id': int(source_msg_id),
        'forward_source_chat_id': int(source_chat_id),
        'forward_dst_chat_id': int(dst_chat_id),
        'forward_dst_msg_id': int(dst_msg_id),
        'finance_operation_key_override': _v260_forward_finance_operation_key(source_chat_id, source_msg_id, dst_chat_id),
        'chat': chat,
        'from_user': user,
    })()

def _v260_finance_forward_repair(source_chat_id: int, source_msg_id: int, dst_chat_id: int, dst_msg_id: int, text: str, owner: int=0, source_date=None, attempt: int=0):
    try:
        current = _v260_find_forward_finance_record(int(dst_chat_id), int(dst_msg_id), _v260_make_forward_shadow(source_chat_id, source_msg_id, dst_chat_id, dst_msg_id, owner, source_date))
        if isinstance(current, dict):
            _v260_bind_forward_finance_record(current, _v260_make_forward_shadow(source_chat_id, source_msg_id, dst_chat_id, dst_msg_id, owner, source_date), dst_chat_id, dst_msg_id)
            persist_finance_chat_local_fast(int(dst_chat_id))
            _v260_forward_finance_op_mark(source_chat_id, source_msg_id, dst_chat_id, 'committed', dst_msg_id=int(dst_msg_id), record_uid=str(current.get('record_uid') or ''), repaired=True)
            return True
        shadow = _v260_make_forward_shadow(source_chat_id, source_msg_id, dst_chat_id, dst_msg_id, owner, source_date)
        rec = sync_forwarded_finance_message(int(dst_chat_id), int(dst_msg_id), str(text or ''), int(owner or 0), source_msg=shadow)
        if isinstance(rec, dict):
            _persist_forward_finance_delivery_now(source_chat_id, source_msg_id, dst_chat_id, dst_msg_id, rec)
            bot_journal('forward_finance_partial_repaired_v260', int(dst_chat_id), f'src={source_chat_id}:{source_msg_id}; dst={dst_chat_id}:{dst_msg_id}; attempt={attempt}')
            return True
    except Exception as exc:
        log_error(f'[FWD FIN V260] repair attempt={attempt} {source_chat_id}:{source_msg_id}->{dst_chat_id}:{dst_msg_id}: {exc}')
    if int(attempt) < 5:
        delay = (1.0, 3.0, 8.0, 20.0, 45.0, 90.0)[min(int(attempt), 5)]
        try:
            DELAYED_SCHEDULER.schedule(f'finfwd-v260:{source_chat_id}:{source_msg_id}:{dst_chat_id}', delay, _v260_finance_forward_repair, source_chat_id, source_msg_id, dst_chat_id, dst_msg_id, text, owner, source_date, int(attempt)+1)
        except Exception:
            pass
    else:
        _v260_forward_finance_op_mark(source_chat_id, source_msg_id, dst_chat_id, 'needs_review', dst_msg_id=int(dst_msg_id), last_error='repair exhausted')
    return False

def _v260_schedule_finance_forward_repair(source_chat_id: int, source_msg_id: int, dst_chat_id: int, dst_msg_id: int, text: str, owner: int=0, source_date=None, attempt: int=0):
    _v260_forward_finance_op_mark(source_chat_id, source_msg_id, dst_chat_id, 'partial_finance_missing', dst_msg_id=int(dst_msg_id), text=str(text or '')[:4000], owner=int(owner or 0), source_date=source_date)
    try:
        DELAYED_SCHEDULER.schedule(f'finfwd-v260:{source_chat_id}:{source_msg_id}:{dst_chat_id}', 0.6, _v260_finance_forward_repair, source_chat_id, source_msg_id, dst_chat_id, dst_msg_id, text, owner, source_date, attempt)
        return True
    except Exception as exc:
        log_error(f'[FWD FIN V260] repair schedule: {exc}')
        return False

def recover_partial_finance_forwards_v260(limit: int=200) -> int:
    rows=[]
    try:
        with SQLITE.lock:
            raw_rows=SQLITE.conn.execute("SELECT k,v FROM meta WHERE kind='forward_finance_ops_v260'").fetchall()
        for _k,_v in raw_rows:
            try: row=json.loads(_v) if isinstance(_v,str) else _v
            except Exception: continue
            if isinstance(row,dict) and row.get('state') in {'copy_delivered','partial_finance_missing','repairing'}:
                rows.append(row)
    except Exception:
        return 0
    submitted=0
    for row in rows[:max(1,int(limit))]:
        try:
            if _v260_schedule_finance_forward_repair(int(row['source_chat_id']),int(row['source_msg_id']),int(row['dst_chat_id']),int(row.get('dst_msg_id') or 0),str(row.get('text') or ''),int(row.get('owner') or 0),row.get('source_date'),0): submitted+=1
        except Exception: pass
    return submitted

def sync_edited_copy_to_target(source_chat_id: int, msg, dst_chat_id: int, dst_msg_id: int, finance_enabled: bool):
    text = _message_text_for_finance(msg)
    ct = getattr(msg, 'content_type', None)
    owner_id = msg.from_user.id if getattr(msg, 'from_user', None) else 0
    rec = find_record_by_message_id(dst_chat_id, dst_msg_id) if finance_enabled else None
    edit_mode = forward_copy_edit_mode(source_chat_id) if finance_enabled else 'normal'
    display_text = _forward_copy_display_text(text, rec, edit_mode) if rec else text
    edit_markup = _forward_copy_edit_keyboard(edit_mode) if finance_enabled else None
    try:
        if is_total_secret_mode(int(dst_chat_id)):
            hidden_ok = sync_forwarded_secret_bot_copy_edit(int(dst_chat_id), int(dst_msg_id), int(source_chat_id), msg)
            if hidden_ok:
                if finance_enabled and text and is_finance_mode(int(dst_chat_id)):
                    sync_forwarded_finance_message(int(dst_chat_id), int(dst_msg_id), text, owner_id, source_msg=msg)
                return int(dst_msg_id)
            raise RuntimeError(f'TOTAL SECRET edit could not be stored safely for {dst_chat_id}:{dst_msg_id}')
    except Exception as secret_exc:
        try:
            if is_total_secret_mode(int(dst_chat_id)):
                log_error(f'sync_edited_copy_to_target secret-safe failed {dst_chat_id}:{dst_msg_id}: {secret_exc}')
                _notify_forward_failure(source_chat_id, msg.message_id, dst_chat_id, secret_exc)
                return None
        except Exception:
            pass
    try:
        if ct == 'text':
            try:
                bot.edit_message_text(display_text, chat_id=dst_chat_id, message_id=dst_msg_id, reply_markup=edit_markup)
            except Exception as e:
                err = str(e).lower()
                if 'message is not modified' not in err:
                    raise
        elif ct in ('photo', 'video', 'document', 'audio', 'animation'):
            media = _build_input_media_from_message(msg)
            if not media:
                raise RuntimeError(f'Unsupported edited media content_type={ct}')
            try:
                bot.edit_message_media(media=media, chat_id=dst_chat_id, message_id=dst_msg_id)
            except Exception as e:
                err = str(e).lower()
                if 'message is not modified' not in err:
                    raise
        elif getattr(msg, 'caption', None):
            try:
                bot.edit_message_caption(caption=display_text, chat_id=dst_chat_id, message_id=dst_msg_id, reply_markup=edit_markup)
            except Exception as e:
                err = str(e).lower()
                if 'message is not modified' not in err:
                    raise
        else:
            raise RuntimeError(f'Edited sync unsupported for content_type={ct}')
        if finance_enabled and text and is_finance_mode(dst_chat_id):
            sync_forwarded_finance_message(dst_chat_id, dst_msg_id, text, owner_id, source_msg=msg)
            apply_forward_copy_edit_ui(source_chat_id, dst_chat_id, dst_msg_id, msg)
        _v212_task_reconcile_forward_copy(dst_chat_id, dst_msg_id, source_chat_id, msg, is_edit=True)
        return dst_msg_id
    except Exception as e:
        log_error(f'sync_edited_copy_to_target direct edit failed {dst_chat_id}:{dst_msg_id}: {e}')
    reply_to_target_id = None
    try:
        reply_to_msg = getattr(msg, 'reply_to_message', None)
        if reply_to_msg is not None:
            reply_to_target_id = resolve_reply_target_message_id(source_chat_id, getattr(reply_to_msg, 'message_id', None), dst_chat_id)
    except Exception:
        pass
    try:
        try:
            bot.delete_message(dst_chat_id, dst_msg_id)
        except Exception:
            pass
        sent_msg = _fallback_send_single(dst_chat_id, msg, reply_to_message_id=reply_to_target_id)
        new_dst_msg_id = sent_msg.message_id
        _replace_forward_link_pair(source_chat_id, msg.message_id, dst_chat_id, dst_msg_id, dst_chat_id, new_dst_msg_id)
        if finance_enabled and is_finance_mode(dst_chat_id):
            rebind_forwarded_finance_record(dst_chat_id, dst_msg_id, new_dst_msg_id, text, owner_id, source_msg=msg)
        _v212_task_reconcile_forward_copy(dst_chat_id, new_dst_msg_id, source_chat_id, msg, is_edit=True, previous_message_id=dst_msg_id)
        return new_dst_msg_id
    except Exception as e:
        _notify_forward_failure(source_chat_id, msg.message_id, dst_chat_id, e)
        return None

def _cleanup_forward_storage_for_chat(chat_id: int):
    chat_id = int(chat_id)
    with forward_map_lock:
        for key in list(forward_map.keys()):
            src_chat_id, _ = key
            if src_chat_id == chat_id:
                del forward_map[key]
                continue
            pairs = [pair for pair in forward_map.get(key, []) if int(pair[0]) != chat_id]
            if pairs:
                forward_map[key] = pairs
            elif key in forward_map:
                del forward_map[key]
    _schedule_persist_forward_state()

def _telegram_migrate_to_chat_id(err: Exception):
    """Возвращает новый chat_id, когда Telegram сообщает migration group -> supergroup."""
    try:
        result_json = getattr(err, 'result_json', None) or {}
        params = result_json.get('parameters') or {}
        value = params.get('migrate_to_chat_id')
        if value is not None:
            return int(value)
    except Exception:
        pass
    text = str(err or '')
    for pat in ('"migrate_to_chat_id"\\s*:\\s*(-?\\d+)', 'migrate_to_chat_id\\s*[=:]\\s*(-?\\d+)'):
        m = re.search(pat, text, re.I)
        if m:
            try:
                return int(m.group(1))
            except Exception:
                pass
    return None

def _merge_chat_store_for_migration(old_id: int, new_id: int):
    chats = data.setdefault('chats', {})
    old_key, new_key = (str(int(old_id)), str(int(new_id)))
    old_store = chats.get(old_key)
    new_store = chats.get(new_key)
    if not isinstance(old_store, dict):
        return
    if not isinstance(new_store, dict):
        chats[new_key] = old_store
    else:
        for k, v in old_store.items():
            if k not in new_store or new_store.get(k) in (None, '', [], {}):
                new_store[k] = v
        for list_key in ('records', 'ars_records', 'usd_records'):
            old_rows = old_store.get(list_key) or []
            new_rows = new_store.setdefault(list_key, [])
            seen = {(r.get('id'), r.get('source_msg_id'), r.get('origin_msg_id')) for r in new_rows if isinstance(r, dict)}
            for r in old_rows:
                if not isinstance(r, dict):
                    continue
                sig = (r.get('id'), r.get('source_msg_id'), r.get('origin_msg_id'))
                if sig not in seen:
                    new_rows.append(r)
                    seen.add(sig)
        for daily_key in ('daily_records', 'ars_daily_records', 'usd_daily_records'):
            od = old_store.get(daily_key) or {}
            nd = new_store.setdefault(daily_key, {})
            for day, rows in od.items():
                dest = nd.setdefault(day, [])
                seen = {(r.get('id'), r.get('source_msg_id'), r.get('origin_msg_id')) for r in dest if isinstance(r, dict)}
                for r in rows or []:
                    if not isinstance(r, dict):
                        continue
                    sig = (r.get('id'), r.get('source_msg_id'), r.get('origin_msg_id'))
                    if sig not in seen:
                        dest.append(r)
                        seen.add(sig)
    chats.pop(old_key, None)

def _v177_legacy_0156_migrate_chat_id_everywhere(old_chat_id: int, new_chat_id: int, reason: str='telegram supergroup migration') -> bool:
    """Атомарно переносит известный chat_id старой group на новый supergroup chat_id."""
    old_chat_id, new_chat_id = (int(old_chat_id), int(new_chat_id))
    if old_chat_id == new_chat_id:
        return True
    try:
        with data_lock:
            _merge_chat_store_for_migration(old_chat_id, new_chat_id)
            for root_key in ('forward_rules', 'forward_finance'):
                root = data.setdefault(root_key, {})
                oldk, newk = (str(old_chat_id), str(new_chat_id))
                if oldk in root:
                    src_payload = root.pop(oldk) or {}
                    dst_payload = root.setdefault(newk, {})
                    if isinstance(src_payload, dict) and isinstance(dst_payload, dict):
                        dst_payload.update(src_payload)
                    elif src_payload:
                        root[newk] = src_payload
                for src, dsts in list(root.items()):
                    if not isinstance(dsts, dict):
                        continue
                    if oldk in dsts:
                        val = dsts.pop(oldk)
                        if newk not in dsts:
                            dsts[newk] = val
            try:
                for _cid, st in (data.get('chats', {}) or {}).items():
                    if not isinstance(st, dict):
                        continue
                    kc = st.get('known_chats')
                    if isinstance(kc, dict) and str(old_chat_id) in kc:
                        info = kc.pop(str(old_chat_id))
                        kc.setdefault(str(new_chat_id), info)
            except Exception:
                pass
            for root_key in ('active_messages',):
                root = data.get(root_key)
                if isinstance(root, dict) and str(old_chat_id) in root:
                    oldv = root.pop(str(old_chat_id))
                    root.setdefault(str(new_chat_id), oldv)
            reg = data.get('open_window_registry') or {}
            if isinstance(reg, dict):
                for item in reg.values():
                    if not isinstance(item, dict):
                        continue
                    if int(item.get('chat_id', 0) or 0) == old_chat_id:
                        item['chat_id'] = new_chat_id
                    params = item.get('params') or {}
                    if isinstance(params, dict):
                        for k in ('target_chat_id', 'source_chat_id', 'dst_chat_id'):
                            try:
                                if int(params.get(k, 0) or 0) == old_chat_id:
                                    params[k] = new_chat_id
                            except Exception:
                                pass
            for _cid, st in (data.get('chats', {}) or {}).items():
                if not isinstance(st, dict):
                    continue
                pools = [st.get('records') or [], st.get('ars_records') or [], st.get('usd_records') or []]
                for daily_key in ('daily_records', 'ars_daily_records', 'usd_daily_records'):
                    for rows in (st.get(daily_key) or {}).values():
                        pools.append(rows or [])
                for rows in pools:
                    for rec in rows:
                        if not isinstance(rec, dict):
                            continue
                        for k in ('forward_source_chat_id', 'forward_dst_chat_id'):
                            try:
                                if int(rec.get(k, 0) or 0) == old_chat_id:
                                    rec[k] = new_chat_id
                            except Exception:
                                pass
            try:
                if old_chat_id in finance_active_chats:
                    finance_active_chats.discard(old_chat_id)
                    finance_active_chats.add(new_chat_id)
            except Exception:
                pass
            fac = data.get('finance_active_chats')
            if isinstance(fac, list):
                data['finance_active_chats'] = [new_chat_id if int(x) == old_chat_id else x for x in fac]
            with forward_map_lock:
                rebuilt = {}
                for (src, mid), pairs in list(forward_map.items()):
                    nsrc = new_chat_id if int(src) == old_chat_id else int(src)
                    npairs = []
                    for dcid, dmid in pairs:
                        ndcid = new_chat_id if int(dcid) == old_chat_id else int(dcid)
                        pair = (ndcid, int(dmid))
                        if pair not in npairs:
                            npairs.append(pair)
                    key = (nsrc, int(mid))
                    rebuilt.setdefault(key, [])
                    for pair in npairs:
                        if pair not in rebuilt[key]:
                            rebuilt[key].append(pair)
                forward_map.clear()
                forward_map.update(rebuilt)
                _persist_forward_index_in_data(data)
            _v199_register_chat_alias(old_chat_id, new_chat_id, reason)
            _v199_rewrite_pair_order_id(old_chat_id, new_chat_id)
            gs = data.setdefault('_global_settings', {})
            try:
                tenants_root = gs.get('tenants_v148') or {}
                mapping = tenants_root.get('chat_to_tenant') or {}
                tenants = tenants_root.get('tenants') or {}
                old_tid = str(mapping.pop(str(old_chat_id), None) or '')
                new_tid = str(mapping.get(str(new_chat_id)) or '')
                canonical_tid = new_tid or old_tid
                if old_tid and new_tid and (old_tid != new_tid):
                    old_row = tenants.get(old_tid) if isinstance(tenants, dict) else None
                    new_row = tenants.get(new_tid) if isinstance(tenants, dict) else None
                    if isinstance(old_row, dict) and isinstance(new_row, dict):
                        merged_chats = []
                        for raw in list(new_row.get('chat_ids') or []) + list(old_row.get('chat_ids') or []):
                            try:
                                cid = int(raw)
                            except Exception:
                                continue
                            cid = new_chat_id if cid == old_chat_id else cid
                            if cid not in merged_chats:
                                merged_chats.append(cid)
                        new_row['chat_ids'] = merged_chats
                        old_users = old_row.get('users') or {}
                        if isinstance(old_users, dict):
                            nu = new_row.setdefault('users', {})
                            for uid, urow in old_users.items():
                                if uid not in nu:
                                    nu[uid] = urow
                        old_settings = old_row.get('settings') or {}
                        if isinstance(old_settings, dict):
                            ns = new_row.setdefault('settings', {})
                            for k, v in old_settings.items():
                                ns.setdefault(k, v)
                        if not int(new_row.get('owner_user_id') or 0):
                            new_row['owner_user_id'] = int(old_row.get('owner_user_id') or 0)
                        for cid in merged_chats:
                            mapping[str(cid)] = new_tid
                        tenants.pop(old_tid, None)
                    canonical_tid = new_tid
                elif canonical_tid:
                    mapping[str(new_chat_id)] = canonical_tid
                for tid, trow in list(tenants.items()) if isinstance(tenants, dict) else []:
                    if not isinstance(trow, dict):
                        continue
                    chats = []
                    for raw in trow.get('chat_ids') or []:
                        try:
                            cid = int(raw)
                        except Exception:
                            continue
                        if cid == old_chat_id:
                            cid = new_chat_id if str(tid) == str(canonical_tid) else 0
                        if cid and cid not in chats:
                            chats.append(cid)
                    trow['chat_ids'] = chats
                    try:
                        if int(trow.get('root_chat_id') or 0) == old_chat_id:
                            if str(tid) == str(canonical_tid):
                                trow['root_chat_id'] = new_chat_id
                            elif chats:
                                trow['root_chat_id'] = int(chats[0])
                            else:
                                trow['root_chat_id'] = 0
                    except Exception:
                        pass
                if canonical_tid:
                    mapping[str(new_chat_id)] = canonical_tid
            except Exception as exc:
                log_error(f'v199 tenant migration {old_chat_id}->{new_chat_id}: {exc}')
            try:
                reminders = (gs.get('reminders_v2') or {}).get('items') or {}
                legacy_rows = list(reminders.values())
                if isinstance(gs.get('reminder'), dict):
                    legacy_rows.append(gs.get('reminder'))
                for cfg in legacy_rows:
                    if not isinstance(cfg, dict):
                        continue
                    out_ids = []
                    for raw in cfg.get('chat_ids') or []:
                        try:
                            cid = int(raw)
                        except Exception:
                            continue
                        cid = new_chat_id if cid == old_chat_id else cid
                        if cid not in out_ids:
                            out_ids.append(cid)
                    cfg['chat_ids'] = out_ids
                    lm = cfg.get('last_message_ids')
                    if isinstance(lm, dict) and str(old_chat_id) in lm:
                        old_mid = lm.pop(str(old_chat_id))
                        lm.setdefault(str(new_chat_id), old_mid)
            except Exception as exc:
                log_error(f'v199 reminder migration {old_chat_id}->{new_chat_id}: {exc}')
            try:
                settings_root = data.get('_task_settings_v172')
                if isinstance(settings_root, dict) and str(old_chat_id) in settings_root:
                    old_settings = settings_root.pop(str(old_chat_id))
                    if str(new_chat_id) not in settings_root:
                        settings_root[str(new_chat_id)] = old_settings
                    elif isinstance(old_settings, dict) and isinstance(settings_root.get(str(new_chat_id)), dict):
                        for k, v in old_settings.items():
                            settings_root[str(new_chat_id)].setdefault(k, v)
                for task in (data.get('_tasks_v172') or {}).values():
                    if not isinstance(task, dict):
                        continue
                    for field in ('chat_id', 'source_chat_id', 'target_chat_id'):
                        try:
                            if int(task.get(field) or 0) == old_chat_id:
                                task[field] = new_chat_id
                        except Exception:
                            pass
                src_index = data.get('_task_source_index_v172')
                if isinstance(src_index, dict):
                    for key0 in list(src_index.keys()):
                        if str(key0).startswith(str(old_chat_id) + ':'):
                            newkey = str(new_chat_id) + str(key0)[len(str(old_chat_id)):]
                            src_index.setdefault(newkey, src_index.pop(key0))
            except Exception as exc:
                log_error(f'v199 task migration {old_chat_id}->{new_chat_id}: {exc}')
            try:
                ctor = gs.get('ui_constructor_v196') or {} if isinstance(gs, dict) else {}
                scopes = ctor.get('scopes') if isinstance(ctor, dict) else None
                if isinstance(scopes, dict) and str(old_chat_id) in scopes:
                    old_scope = scopes.pop(str(old_chat_id))
                    if str(new_chat_id) not in scopes:
                        scopes[str(new_chat_id)] = old_scope
                    elif isinstance(old_scope, dict) and isinstance(scopes.get(str(new_chat_id)), dict):
                        dst_scope = scopes[str(new_chat_id)]
                        for k, v in old_scope.items():
                            if k == 'windows' and isinstance(v, dict):
                                dst_scope.setdefault('windows', {}).update({wk: wv for wk, wv in v.items() if wk not in dst_scope.setdefault('windows', {})})
                            else:
                                dst_scope.setdefault(k, v)
                if isinstance(ctor, dict) and str(ctor.get('last_target_scope') or '') == str(old_chat_id):
                    ctor['last_target_scope'] = str(new_chat_id)
            except Exception as exc:
                log_error(f'v212 constructor scope migration {old_chat_id}->{new_chat_id}: {exc}')
            try:
                owners = gs.get('owner_access_chat_ids_v168')
                if isinstance(owners, list):
                    gs['owner_access_chat_ids_v168'] = sorted({new_chat_id if int(x) == old_chat_id else int(x) for x in owners})
            except Exception:
                pass
            try:
                reactivate_forward_target_v199(old_chat_id, migrated_to=new_chat_id, persist=False)
            except Exception:
                pass
            save_data(data, full=True)
            persist_forward_rules_to_owner()
            try:
                schedule_config_backup_for_chats(new_chat_id, delay=0.1)
                if OWNER_ID:
                    schedule_config_backup_for_chats(int(OWNER_ID), delay=0.1)
            except Exception:
                pass
            try:
                schedule_delta_backup(new_chat_id, delay=0.5, reason='chat_id_migration')
            except Exception:
                pass
        log_info(f'[CHAT MIGRATION] {old_chat_id} -> {new_chat_id}: {reason}')
        try:
            bot_journal('chat_id_migration', new_chat_id, f'{old_chat_id} -> {new_chat_id}; {reason}')
        except Exception:
            pass
        return True
    except Exception as e:
        log_error(f'migrate_chat_id_everywhere({old_chat_id}->{new_chat_id}): {e}')
        return False
try:
    _v177_legacy_0156_migrate_chat_id_everywhere.__name__ = 'migrate_chat_id_everywhere'
except Exception:
    pass

def _handle_supergroup_migration_error(old_chat_id: int, err: Exception):
    new_id = _telegram_migrate_to_chat_id(err)
    if new_id is None:
        resolver = globals().get('_v199_migration_target_from_probe_error')
        if callable(resolver):
            try:
                new_id = resolver(int(old_chat_id), err, None)
            except Exception:
                new_id = None
    if new_id is None:
        return None
    if migrate_chat_id_everywhere(int(old_chat_id), int(new_id), reason=str(err)[:300]):
        return int(new_id)
    return None

def _note_forward_target_migrated(source_chat_id: int, source_msg_id: int, old_chat_id: int, new_chat_id: int):
    """Mark old target as migrated so live/durable witnesses do not wait on it forever."""
    try:
        _forward_outcome_update(int(source_chat_id), int(source_msg_id), dst_chat_id=int(old_chat_id), dst_state='migrated')
    except Exception:
        pass
    try:
        fn = globals().get('_durable_note_forward_target_migration')
        if callable(fn):
            fn(int(source_chat_id), int(old_chat_id), int(new_chat_id))
    except Exception as e:
        try:
            log_error(f'forward migration witness {old_chat_id}->{new_chat_id}: {e}')
        except Exception:
            pass

def _notify_forward_failure(source_chat_id: int, msg_id: int, dst_chat_id: int, err: Exception):
    state = _v199_confirm_failed_forward_target(int(dst_chat_id), err)
    if state.startswith('migrated:'):
        return state
    if state == 'suspended':
        log_error(f'FORWARD TARGET SUSPENDED: {source_chat_id}:{msg_id}->{dst_chat_id}: {err}')
        return state
    if _is_bot_removed_error(err):
        set_chat_bot_removed(dst_chat_id, True, str(err)[:240])
    src_name = get_chat_display_name(source_chat_id)
    dst_name = get_chat_display_name(dst_chat_id)
    text = f'⚠️ Пересылка не доставлена\nиз: {src_name}\nсообщение: {msg_id}\nв: {dst_name}\n{err}'
    log_error(text)
    try:
        send_owner_technical_alert(text, 25, source_chat_id=int(source_chat_id))
    except Exception:
        if OWNER_ID:
            try:
                bot.send_message(int(OWNER_ID), text)
            except Exception:
                pass
    return 'transient'

def _message_text_for_finance(msg) -> str:
    return (getattr(msg, 'text', None) or getattr(msg, 'caption', None) or '').strip()

def _build_input_media_from_message(msg):
    caption = getattr(msg, 'caption', None)
    ct = getattr(msg, 'content_type', None)
    if ct == 'photo' and getattr(msg, 'photo', None):
        return InputMediaPhoto(msg.photo[-1].file_id, caption=caption)
    if ct == 'video' and getattr(msg, 'video', None):
        return InputMediaVideo(msg.video.file_id, caption=caption)
    if ct == 'document' and getattr(msg, 'document', None):
        return InputMediaDocument(msg.document.file_id, caption=caption)
    if ct == 'audio' and getattr(msg, 'audio', None):
        return InputMediaAudio(msg.audio.file_id, caption=caption)
    if ct == 'animation' and getattr(msg, 'animation', None):
        return InputMediaAnimation(msg.animation.file_id, caption=caption)
    return None

def _fallback_send_single(dst_chat_id: int, msg, reply_to_message_id=None):
    ct = getattr(msg, 'content_type', None)
    if ct == 'text':
        return _call_with_optional_reply(bot.send_message, dst_chat_id, msg.text or '', reply_to_message_id=reply_to_message_id)
    if ct == 'photo' and getattr(msg, 'photo', None):
        return _call_with_optional_reply(bot.send_photo, dst_chat_id, msg.photo[-1].file_id, caption=getattr(msg, 'caption', None), reply_to_message_id=reply_to_message_id)
    if ct == 'video' and getattr(msg, 'video', None):
        return _call_with_optional_reply(bot.send_video, dst_chat_id, msg.video.file_id, caption=getattr(msg, 'caption', None), reply_to_message_id=reply_to_message_id)
    if ct == 'audio' and getattr(msg, 'audio', None):
        return _call_with_optional_reply(bot.send_audio, dst_chat_id, msg.audio.file_id, caption=getattr(msg, 'caption', None), reply_to_message_id=reply_to_message_id)
    if ct == 'document' and getattr(msg, 'document', None):
        return _call_with_optional_reply(bot.send_document, dst_chat_id, msg.document.file_id, caption=getattr(msg, 'caption', None), reply_to_message_id=reply_to_message_id)
    if ct == 'voice' and getattr(msg, 'voice', None):
        return _call_with_optional_reply(bot.send_voice, dst_chat_id, msg.voice.file_id, caption=getattr(msg, 'caption', None), reply_to_message_id=reply_to_message_id)
    if ct == 'video_note' and getattr(msg, 'video_note', None):
        return _call_with_optional_reply(bot.send_video_note, dst_chat_id, msg.video_note.file_id, reply_to_message_id=reply_to_message_id)
    if ct == 'sticker' and getattr(msg, 'sticker', None):
        return _call_with_optional_reply(bot.send_sticker, dst_chat_id, msg.sticker.file_id, reply_to_message_id=reply_to_message_id)
    if ct == 'animation' and getattr(msg, 'animation', None):
        return _call_with_optional_reply(bot.send_animation, dst_chat_id, msg.animation.file_id, caption=getattr(msg, 'caption', None), reply_to_message_id=reply_to_message_id)
    if ct == 'location' and getattr(msg, 'location', None):
        return _call_with_optional_reply(bot.send_location, dst_chat_id, msg.location.latitude, msg.location.longitude, reply_to_message_id=reply_to_message_id)
    if ct == 'venue' and getattr(msg, 'venue', None):
        return _call_with_optional_reply(bot.send_venue, dst_chat_id, msg.venue.location.latitude, msg.venue.location.longitude, msg.venue.title, msg.venue.address, foursquare_id=getattr(msg.venue, 'foursquare_id', None), reply_to_message_id=reply_to_message_id)
    if ct == 'contact' and getattr(msg, 'contact', None):
        return _call_with_optional_reply(bot.send_contact, dst_chat_id, msg.contact.phone_number, msg.contact.first_name, last_name=getattr(msg.contact, 'last_name', None), reply_to_message_id=reply_to_message_id)
    if ct == 'dice' and getattr(msg, 'dice', None):
        return _call_with_optional_reply(bot.send_dice, dst_chat_id, emoji=getattr(msg.dice, 'emoji', None), reply_to_message_id=reply_to_message_id)
    if ct == 'poll' and getattr(msg, 'poll', None):
        options = [opt.text for opt in getattr(msg.poll, 'options', [])]
        return _call_with_optional_reply(bot.send_poll, dst_chat_id, msg.poll.question, options, is_anonymous=getattr(msg.poll, 'is_anonymous', True), allows_multiple_answers=getattr(msg.poll, 'allows_multiple_answers', False), type=getattr(msg.poll, 'type', 'regular'), reply_to_message_id=reply_to_message_id)
    raise RuntimeError(f'Unsupported fallback content_type={ct}')

def _forward_single_to_target(source_chat_id: int, msg, dst_chat_id: int, finance_enabled: bool, _migration_retry: bool=False):
    try:
        _src_mid_v260 = int(getattr(msg, 'message_id', 0) or 0)
        for _existing_dst_chat, _existing_dst_mid in list(get_forward_links(int(source_chat_id), _src_mid_v260) or []):
            if int(_existing_dst_chat) != int(dst_chat_id):
                continue
            if finance_enabled:
                _txt_v260 = _message_text_for_finance(msg)
                _owner_v260 = int(getattr(getattr(msg, 'from_user', None), 'id', 0) or 0)
                _rec_v260 = sync_forwarded_finance_message(int(dst_chat_id), int(_existing_dst_mid), _txt_v260, _owner_v260, source_msg=msg) if _txt_v260 else None
                if isinstance(_rec_v260, dict):
                    _persist_forward_finance_delivery_now(int(source_chat_id), _src_mid_v260, int(dst_chat_id), int(_existing_dst_mid), _rec_v260)
                elif _txt_v260 and text_has_any_digit(_txt_v260):
                    _v260_schedule_finance_forward_repair(int(source_chat_id), _src_mid_v260, int(dst_chat_id), int(_existing_dst_mid), _txt_v260, _owner_v260, getattr(msg, 'date', None))
            bot_journal('forward_duplicate_copy_blocked_v260', int(dst_chat_id), f'src={source_chat_id}:{_src_mid_v260}; reuse={dst_chat_id}:{_existing_dst_mid}')
            return int(_existing_dst_mid)
    except Exception as _v260_existing_exc:
        try: log_error(f'[FWD V260] existing-link exact-once check: {_v260_existing_exc}')
        except Exception: pass
    try:
        _forward_outcome_update(source_chat_id, int(getattr(msg, 'message_id', 0) or 0), state='dispatching', dst_chat_id=int(dst_chat_id), dst_state='attempted')
    except Exception:
        pass
    reply_to_target_id = None
    try:
        reply_to_msg = getattr(msg, 'reply_to_message', None)
        if reply_to_msg is not None:
            reply_to_target_id = resolve_reply_target_message_id(source_chat_id, getattr(reply_to_msg, 'message_id', None), dst_chat_id)
    except Exception as e:
        log_error(f'_forward_single_to_target reply resolve {source_chat_id}->{dst_chat_id}: {e}')
    pre_copy_markup = None
    initial_slash_command = None
    initial_slash_synced_rec = None
    initial_slash_sent = False
    text_for_finance = _message_text_for_finance(msg)
    copy_edit_mode = 'normal'
    try:
        if finance_enabled:
            copy_edit_mode = forward_copy_edit_mode(source_chat_id)
            if copy_edit_mode == 'button':
                pre_copy_markup = _forward_copy_edit_keyboard('button')
    except Exception:
        pre_copy_markup = None
        copy_edit_mode = 'normal'
    try:
        use_initial_slash = False
        try:
            use_initial_slash = bool(finance_enabled and copy_edit_mode == 'slash' and (str(getattr(msg, 'content_type', '') or '') == 'text') and text_for_finance and is_finance_mode(int(dst_chat_id)) and looks_like_amount(text_for_finance))
        except Exception:
            use_initial_slash = False
        if use_initial_slash:
            with locked_chat(int(dst_chat_id)):
                initial_slash_command = _predict_forward_copy_record_command(int(dst_chat_id), msg, text_for_finance)
                if initial_slash_command:
                    display_text = (_strip_forward_copy_edit_command(text_for_finance) + '\n' + initial_slash_command).strip()
                    send_kwargs = {}
                    entities = getattr(msg, 'entities', None)
                    if entities:
                        send_kwargs['entities'] = entities
                    if reply_to_target_id:
                        send_kwargs['reply_to_message_id'] = int(reply_to_target_id)
                        send_kwargs['allow_sending_without_reply'] = True
                    try:
                        sent = _tg_call_retry(bot.send_message, int(dst_chat_id), display_text, purpose='forward_send_text_initial_slash', **send_kwargs)
                    except TypeError:
                        send_kwargs.pop('allow_sending_without_reply', None)
                        sent = _tg_call_retry(bot.send_message, int(dst_chat_id), display_text, purpose='forward_send_text_initial_slash', **send_kwargs)
                    dst_msg_id = int(sent.message_id)
                    initial_slash_sent = True
                    _store_forward_link(source_chat_id, msg.message_id, dst_chat_id, dst_msg_id)
                    _forward_outcome_update(source_chat_id, int(msg.message_id), dst_chat_id=int(dst_chat_id), dst_state='delivered', dst_msg_id=int(dst_msg_id))
                    try:
                        _persist_forward_index_in_data(data)
                        save_data(data, root_only=True)
                    except Exception as e:
                        log_error(f'[FORWARD LINK DURABLE initial slash] {source_chat_id}:{msg.message_id}->{dst_chat_id}:{dst_msg_id}: {e}')
                    owner_id = msg.from_user.id if getattr(msg, 'from_user', None) else 0
                    initial_slash_synced_rec = sync_forwarded_finance_message(int(dst_chat_id), int(dst_msg_id), text_for_finance, owner_id, source_msg=msg)
                    if isinstance(initial_slash_synced_rec, dict):
                        initial_slash_synced_rec = _v169_apply_predicted_record_uid(int(dst_chat_id), initial_slash_synced_rec, initial_slash_command)
        if not initial_slash_sent:
            if reply_to_target_id:
                try:
                    sent = _tg_call_retry(bot.copy_message, dst_chat_id, source_chat_id, msg.message_id, reply_to_message_id=reply_to_target_id, allow_sending_without_reply=True, reply_markup=pre_copy_markup, purpose='forward_copy_message')
                except TypeError:
                    try:
                        sent = _tg_call_retry(bot.copy_message, dst_chat_id, source_chat_id, msg.message_id, reply_to_message_id=reply_to_target_id, reply_markup=pre_copy_markup, purpose='forward_copy_message')
                    except TypeError:
                        sent = _tg_call_retry(bot.copy_message, dst_chat_id, source_chat_id, msg.message_id, reply_markup=pre_copy_markup, purpose='forward_copy_message')
            else:
                sent = _tg_call_retry(bot.copy_message, dst_chat_id, source_chat_id, msg.message_id, reply_markup=pre_copy_markup, purpose='forward_copy_message')
            dst_msg_id = sent.message_id
    except Exception as e_copy:
        migrated_id = None if _migration_retry else _handle_supergroup_migration_error(dst_chat_id, e_copy)
        if migrated_id is not None:
            _note_forward_target_migrated(source_chat_id, int(getattr(msg, 'message_id', 0) or 0), dst_chat_id, migrated_id)
            return _forward_single_to_target(source_chat_id, msg, migrated_id, finance_enabled, _migration_retry=True)
        try:
            sent_forward = _tg_call_retry(bot.forward_message, dst_chat_id, source_chat_id, msg.message_id, purpose='forward_message_fallback')
            dst_msg_id = sent_forward.message_id
        except Exception as e_forward:
            migrated_id = None if _migration_retry else _handle_supergroup_migration_error(dst_chat_id, e_forward)
            if migrated_id is not None:
                _note_forward_target_migrated(source_chat_id, int(getattr(msg, 'message_id', 0) or 0), dst_chat_id, migrated_id)
                return _forward_single_to_target(source_chat_id, msg, migrated_id, finance_enabled, _migration_retry=True)
            try:
                sent_msg = _fallback_send_single(dst_chat_id, msg, reply_to_message_id=reply_to_target_id)
                dst_msg_id = sent_msg.message_id
            except Exception as e_send:
                migrated_id = None if _migration_retry else _handle_supergroup_migration_error(dst_chat_id, e_send)
                if migrated_id is not None:
                    _note_forward_target_migrated(source_chat_id, int(getattr(msg, 'message_id', 0) or 0), dst_chat_id, migrated_id)
                    return _forward_single_to_target(source_chat_id, msg, migrated_id, finance_enabled, _migration_retry=True)
                final_error = e_forward if 'Unsupported fallback content_type' in str(e_send) else e_send
                failure_state = _notify_forward_failure(source_chat_id, msg.message_id, dst_chat_id, final_error)
                if str(failure_state).startswith('migrated:') and (not _migration_retry):
                    try:
                        migrated_id = int(str(failure_state).split(':', 1)[1])
                        _note_forward_target_migrated(source_chat_id, int(getattr(msg, 'message_id', 0) or 0), dst_chat_id, migrated_id)
                        return _forward_single_to_target(source_chat_id, msg, migrated_id, finance_enabled, _migration_retry=True)
                    except Exception:
                        pass
                terminal_state = 'suspended' if failure_state == 'suspended' else 'failed'
                _forward_outcome_update(source_chat_id, int(getattr(msg, 'message_id', 0) or 0), dst_chat_id=int(dst_chat_id), dst_state=terminal_state, error=str(final_error))
                return None
    _store_forward_link(source_chat_id, msg.message_id, dst_chat_id, dst_msg_id)
    try:
        _v260_forward_finance_op_mark(int(source_chat_id), int(msg.message_id), int(dst_chat_id), 'copy_delivered', dst_msg_id=int(dst_msg_id), text=str(text_for_finance or '')[:4000], owner=int(getattr(getattr(msg,'from_user',None),'id',0) or 0), source_date=getattr(msg,'date',None))
    except Exception:
        pass
    _forward_outcome_update(source_chat_id, int(msg.message_id), dst_chat_id=int(dst_chat_id), dst_state='delivered', dst_msg_id=int(dst_msg_id))
    try:
        _persist_forward_index_in_data(data)
        save_data(data, root_only=True)
    except Exception as e:
        log_error(f'[FORWARD LINK DURABLE] {source_chat_id}:{msg.message_id}->{dst_chat_id}:{dst_msg_id}: {e}')
    bump_quick_balance_recreate_counter(dst_chat_id)
    _v212_task_reconcile_forward_copy(dst_chat_id, dst_msg_id, source_chat_id, msg, is_edit=False)
    if finance_enabled and text_for_finance:
        try:
            owner_id = msg.from_user.id if getattr(msg, 'from_user', None) else 0
            ok_fin = initial_slash_synced_rec or sync_forwarded_finance_message(dst_chat_id, dst_msg_id, text_for_finance, owner_id, source_msg=msg)
            if ok_fin:
                _rec = ok_fin if isinstance(ok_fin, dict) else find_record_by_message_id(dst_chat_id, dst_msg_id)
                if isinstance(_rec, dict) and initial_slash_sent:
                    _rec['forward_copy_content_type'] = 'text'
                _persist_forward_finance_delivery_now(source_chat_id, msg.message_id, dst_chat_id, dst_msg_id, _rec)
                if initial_slash_sent and isinstance(_rec, dict):
                    actual_command = _forward_copy_record_command(_rec)
                    if actual_command == initial_slash_command:
                        _ui_ok = True
                        try:
                            bot_journal('forward_copy_initial_slash', int(dst_chat_id), f'src={source_chat_id}:{msg.message_id} dst_msg={dst_msg_id} command={actual_command}')
                        except Exception:
                            pass
                    else:
                        _ui_ok = apply_forward_copy_edit_ui(source_chat_id, dst_chat_id, dst_msg_id, msg, rec=_rec)
                else:
                    _ui_ok = apply_forward_copy_edit_ui(source_chat_id, dst_chat_id, dst_msg_id, msg, rec=_rec)
                if not _ui_ok and forward_copy_edit_mode(source_chat_id) != 'normal':
                    schedule_forward_copy_edit_ui_retry(source_chat_id, dst_chat_id, dst_msg_id, msg, rec=_rec, delay=0.8)
            elif text_has_any_digit(text_for_finance):
                try:
                    _dst_fin_mode = bool(is_finance_mode(dst_chat_id))
                except Exception:
                    _dst_fin_mode = False
                if _dst_fin_mode:
                    log_error(f'[FWD FINANCE NOT RECORDED] {get_chat_display_name(source_chat_id)}:{msg.message_id} -> {get_chat_display_name(dst_chat_id)}:{dst_msg_id} text={text_for_finance[:220]!r}')
                    _v260_schedule_finance_forward_repair(int(source_chat_id), int(msg.message_id), int(dst_chat_id), int(dst_msg_id), text_for_finance, int(owner_id or 0), getattr(msg, 'date', None))
                else:
                    bot_journal('forward_finance_not_expected', dst_chat_id, f'src={source_chat_id}:{msg.message_id} dst_msg={dst_msg_id}')
        except Exception as e:
            log_error(f'_forward_single_to_target finance sync {get_chat_display_name(source_chat_id)}->{get_chat_display_name(dst_chat_id)}: {e}')
            try:
                _v260_schedule_finance_forward_repair(int(source_chat_id), int(msg.message_id), int(dst_chat_id), int(dst_msg_id), text_for_finance, int(getattr(getattr(msg,'from_user',None),'id',0) or 0), getattr(msg, 'date', None))
            except Exception:
                pass
    try:
        capture_forwarded_bot_copy_as_secret(dst_chat_id, dst_msg_id, msg)
    except Exception as e:
        log_error(f'forward secret capture {source_chat_id}->{dst_chat_id}:{dst_msg_id}: {e}')
    return dst_msg_id

def _flush_media_group_forward(source_chat_id: int, media_group_id: str):
    if not FORWARD_TASK_POOL.submit(int(source_chat_id), _flush_media_group_forward_locked, source_chat_id, media_group_id):
        log_error(f'MEDIA GROUP FORWARD QUEUE FULL: {source_chat_id}')

def _flush_media_group_forward_locked(source_chat_id: int, media_group_id: str):
    cache_key = (int(source_chat_id), str(media_group_id))
    messages = _media_group_cache.pop(cache_key, [])
    _media_group_timers.pop(cache_key, None)
    DELAYED_SCHEDULER.cancel(f'media-group:{int(source_chat_id)}:{str(media_group_id)}')
    if not messages:
        return
    messages = sorted(messages, key=lambda m: m.message_id)
    targets = sorted(list(resolve_forward_targets(source_chat_id) or []), key=lambda row: 0 if bool(row[2]) else 1)
    if not targets:
        for src_msg in messages:
            try:
                _forward_outcome_update(source_chat_id, int(src_msg.message_id), state='no_targets')
            except Exception:
                pass
        return
    for src_msg in messages:
        try:
            _forward_outcome_update(source_chat_id, int(src_msg.message_id), state='dispatching')
        except Exception:
            pass
    media = []
    for msg in messages:
        item = _build_input_media_from_message(msg)
        if not item:
            media = []
            break
        media.append(item)
    group_reply_source_id = None
    try:
        first_reply = getattr(messages[0], 'reply_to_message', None)
        if first_reply is not None:
            group_reply_source_id = getattr(first_reply, 'message_id', None)
    except Exception:
        pass
    for dst_chat_id, mode, finance_enabled in targets:
        for src_msg in messages:
            try:
                _forward_outcome_update(source_chat_id, int(src_msg.message_id), dst_chat_id=int(dst_chat_id), dst_state='attempted')
            except Exception:
                pass
        sent_ids = []
        reply_to_target_id = resolve_reply_target_message_id(source_chat_id, group_reply_source_id, dst_chat_id) if group_reply_source_id else None
        if media:
            try:
                if reply_to_target_id:
                    try:
                        sent_group = _tg_call_retry(bot.send_media_group, dst_chat_id, media, reply_to_message_id=reply_to_target_id, allow_sending_without_reply=True, purpose='forward_media_group')
                    except TypeError:
                        try:
                            sent_group = _tg_call_retry(bot.send_media_group, dst_chat_id, media, reply_to_message_id=reply_to_target_id, purpose='forward_media_group')
                        except TypeError:
                            sent_group = _tg_call_retry(bot.send_media_group, dst_chat_id, media, purpose='forward_media_group')
                else:
                    sent_group = _tg_call_retry(bot.send_media_group, dst_chat_id, media, purpose='forward_media_group')
                sent_ids = [m.message_id for m in sent_group]
            except Exception as e:
                migrated_id = _handle_supergroup_migration_error(dst_chat_id, e)
                if migrated_id is not None:
                    log_info(f'[MEDIA GROUP MIGRATION RETRY] {dst_chat_id} -> {migrated_id}')
                    for src_msg in messages:
                        _note_forward_target_migrated(source_chat_id, int(getattr(src_msg, 'message_id', 0) or 0), dst_chat_id, migrated_id)
                        _forward_single_to_target(source_chat_id, src_msg, migrated_id, finance_enabled, _migration_retry=True)
                    continue
                log_error(f'_flush_media_group_forward send_media_group failed {get_chat_display_name(source_chat_id)}->{get_chat_display_name(dst_chat_id)}: {e}')
        if len(sent_ids) == len(messages):
            for src_msg, dst_msg_id in zip(messages, sent_ids):
                _store_forward_link(source_chat_id, src_msg.message_id, dst_chat_id, dst_msg_id)
                _forward_outcome_update(source_chat_id, int(src_msg.message_id), dst_chat_id=int(dst_chat_id), dst_state='delivered', dst_msg_id=int(dst_msg_id))
                bump_quick_balance_recreate_counter(dst_chat_id)
                _v212_task_reconcile_forward_copy(dst_chat_id, dst_msg_id, source_chat_id, src_msg, is_edit=False)
                text_for_finance = _message_text_for_finance(src_msg)
                if finance_enabled and text_for_finance:
                    try:
                        owner_id = src_msg.from_user.id if getattr(src_msg, 'from_user', None) else 0
                        ok_fin = sync_forwarded_finance_message(dst_chat_id, dst_msg_id, text_for_finance, owner_id, source_msg=src_msg)
                        if ok_fin:
                            _rec = ok_fin if isinstance(ok_fin, dict) else None
                            _ui_ok = apply_forward_copy_edit_ui(source_chat_id, dst_chat_id, dst_msg_id, src_msg, rec=_rec)
                            if not _ui_ok and forward_copy_edit_mode(source_chat_id) != 'normal':
                                schedule_forward_copy_edit_ui_retry(source_chat_id, dst_chat_id, dst_msg_id, src_msg, rec=_rec, delay=0.8)
                        elif text_has_any_digit(text_for_finance):
                            log_error(f'[FWD MEDIA FINANCE NOT RECORDED] {get_chat_display_name(source_chat_id)}:{src_msg.message_id} -> {get_chat_display_name(dst_chat_id)}:{dst_msg_id} text={text_for_finance[:220]!r}')
                    except Exception as e:
                        log_error(f'_flush_media_group_forward finance sync {get_chat_display_name(source_chat_id)}->{get_chat_display_name(dst_chat_id)}: {e}')
                try:
                    capture_forwarded_bot_copy_as_secret(dst_chat_id, dst_msg_id, src_msg)
                except Exception as e:
                    log_error(f'media-group secret capture {source_chat_id}->{dst_chat_id}:{dst_msg_id}: {e}')
            continue
        for src_msg in messages:
            _forward_single_to_target(source_chat_id, src_msg, dst_chat_id, finance_enabled)
    for src_msg in messages:
        try:
            _forward_outcome_update(source_chat_id, int(src_msg.message_id), state='completed')
        except Exception:
            pass

def _collect_media_group_for_forward(source_chat_id: int, msg):
    cache_key = (int(source_chat_id), str(msg.media_group_id))
    bucket = _media_group_cache.setdefault(cache_key, [])
    if not any((m.message_id == msg.message_id for m in bucket)):
        bucket.append(msg)
    scheduler_key = f'media-group:{int(source_chat_id)}:{str(msg.media_group_id)}'
    DELAYED_SCHEDULER.cancel(scheduler_key)
    deadline = DELAYED_SCHEDULER.schedule(scheduler_key, 0.8, _flush_media_group_forward, source_chat_id, msg.media_group_id)
    _media_group_timers[cache_key] = deadline
_FIN_FORWARD_BATCH_LOCK = threading.RLock()
_FIN_FORWARD_BATCHES = {}

def _fin_forward_batch_id(source_chat_id: int, source_msg_id: int) -> str:
    return f'{int(source_chat_id)}:{int(source_msg_id)}'

def _v177_legacy_0157_fin_forward_batch_finish_target(batch_id: str, dst_chat_id: int, ok: bool, elapsed: float, error: str='') -> None:
    follow = None
    with _FIN_FORWARD_BATCH_LOCK:
        row = _FIN_FORWARD_BATCHES.get(str(batch_id))
        if not isinstance(row, dict):
            return
        row.setdefault('targets', {})[str(int(dst_chat_id))] = {'ok': bool(ok), 'elapsed': round(float(elapsed), 3), 'error': str(error or '')[:300]}
        row['remaining'] = max(0, int(row.get('remaining', 0)) - 1)
        if row['remaining'] == 0:
            follow = dict(row)
            _FIN_FORWARD_BATCHES.pop(str(batch_id), None)
    try:
        bot_journal('finance_forward_target_done', follow.get('source_chat_id') if follow else None, f"batch={batch_id} dst={int(dst_chat_id)} ok={bool(ok)} elapsed={elapsed:.3f}s error={str(error or '')[:180]}", 'INFO' if ok else 'ERROR')
    except Exception:
        pass
    if not follow:
        return
    source_chat_id = int(follow.get('source_chat_id'))
    source_msg_id = int(follow.get('source_msg_id'))
    normal_targets = list(follow.get('normal_targets') or [])
    started = float(follow.get('started_mono') or time.monotonic())
    if normal_targets:
        if not FORWARD_TASK_POOL.submit(source_chat_id, _forward_normal_stage, source_chat_id, follow.get('msg'), normal_targets):
            log_error(f'FORWARD QUEUE FULL AFTER FIN BATCH, INLINE FALLBACK: {source_chat_id}')
            _forward_normal_stage(source_chat_id, follow.get('msg'), normal_targets)
    elif source_msg_id:
        _forward_outcome_update(source_chat_id, source_msg_id, state='completed')
    try:
        target_rows = follow.get('targets') or {}
        failed = sum((1 for x in target_rows.values() if not bool((x or {}).get('ok'))))
        bot_journal('finance_forward_batch_done', source_chat_id, f'batch={batch_id} targets={len(target_rows)} failed={failed} elapsed={time.monotonic() - started:.3f}s')
    except Exception:
        pass
try:
    _v177_legacy_0157_fin_forward_batch_finish_target.__name__ = '_fin_forward_batch_finish_target'
except Exception:
    pass

def _fin_forward_target_job(batch_id: str, source_chat_id: int, msg, dst_chat_id: int, finance_enabled: bool) -> None:
    started = time.monotonic()
    ok = False
    err = ''
    try:
        ok = bool(_forward_single_to_target(int(source_chat_id), msg, int(dst_chat_id), bool(finance_enabled)))
    except Exception as exc:
        err = str(exc)
        log_error(f'FIN-FORWARD TARGET {source_chat_id}->{dst_chat_id}: {exc}')
    finally:
        _fin_forward_batch_finish_target(batch_id, int(dst_chat_id), ok, time.monotonic() - started, err)

def _start_financial_forward_batch(source_chat_id: int, msg, finance_targets: list, normal_targets: list) -> None:
    source_chat_id = int(source_chat_id)
    source_msg_id = int(getattr(msg, 'message_id', 0) or 0)
    batch_id = _fin_forward_batch_id(source_chat_id, source_msg_id)
    with _FIN_FORWARD_BATCH_LOCK:
        _FIN_FORWARD_BATCHES[batch_id] = {'source_chat_id': source_chat_id, 'source_msg_id': source_msg_id, 'msg': msg, 'normal_targets': list(normal_targets or []), 'remaining': len(finance_targets or []), 'targets': {}, 'started_mono': time.monotonic()}
    try:
        bot_journal('finance_forward_batch_started', source_chat_id, f'batch={batch_id} finance_targets={len(finance_targets or [])} normal_targets={len(normal_targets or [])}')
    except Exception:
        pass
    for dst_chat_id, _mode, finance_enabled in list(finance_targets or []):
        task_key = f'{source_chat_id}:{int(dst_chat_id)}'
        if not FIN_FORWARD_TASK_POOL.submit(task_key, _fin_forward_target_job, batch_id, source_chat_id, msg, int(dst_chat_id), bool(finance_enabled)):
            log_error(f'FIN-FORWARD TARGET QUEUE FULL, INLINE FALLBACK: {task_key}')
            _fin_forward_target_job(batch_id, source_chat_id, msg, int(dst_chat_id), bool(finance_enabled))

def _forward_targets_stage(source_chat_id: int, msg, targets: list, final_stage: bool=False) -> None:
    """Выполняет уже выбранную часть направлений, не смешивая очереди."""
    source_chat_id = int(source_chat_id)
    source_msg_id = int(getattr(msg, 'message_id', 0) or 0)
    try:
        for dst_chat_id, _mode, finance_enabled in list(targets or []):
            _forward_single_to_target(source_chat_id, msg, int(dst_chat_id), bool(finance_enabled))
    finally:
        if final_stage and source_msg_id:
            _forward_outcome_update(source_chat_id, source_msg_id, state='completed')

def _forward_normal_stage(source_chat_id: int, msg, targets: list) -> None:
    _forward_targets_stage(source_chat_id, msg, targets, final_stage=True)

def _forward_financial_stage(source_chat_id: int, msg, finance_targets: list, normal_targets: list) -> None:
    """Сначала финансовые копии и записи, затем обычные/секретные назначения."""
    source_chat_id = int(source_chat_id)
    source_msg_id = int(getattr(msg, 'message_id', 0) or 0)
    try:
        _forward_targets_stage(source_chat_id, msg, finance_targets, final_stage=False)
    finally:
        if normal_targets:
            if not FORWARD_TASK_POOL.submit(source_chat_id, _forward_normal_stage, source_chat_id, msg, list(normal_targets)):
                log_error(f'FORWARD QUEUE FULL AFTER FIN STAGE, INLINE FALLBACK: {source_chat_id}')
                _forward_normal_stage(source_chat_id, msg, list(normal_targets))
        elif source_msg_id:
            _forward_outcome_update(source_chat_id, source_msg_id, state='completed')

def schedule_financial_forward_pipeline(source_chat_id: int, msg) -> None:
    """Финансовые назначения идут раньше всех остальных, без потери exact-once защиты."""
    source_chat_id = int(source_chat_id)
    source_msg_id = int(getattr(msg, 'message_id', 0) or 0)
    try:
        if getattr(msg, 'media_group_id', None) and getattr(msg, 'content_type', None) in ('photo', 'video', 'document', 'audio'):
            if not FORWARD_TASK_POOL.submit(source_chat_id, _forward_with_finance_priority, source_chat_id, msg):
                log_error(f'MEDIA FORWARD QUEUE FULL, INLINE FALLBACK: {source_chat_id}')
                _forward_with_finance_priority(source_chat_id, msg)
            return
        targets = list(resolve_forward_targets(source_chat_id) or [])
        if not targets:
            if source_msg_id:
                _forward_outcome_update(source_chat_id, source_msg_id, state='no_targets')
            return
        finance_targets = [row for row in targets if bool(row[2])]
        normal_targets = [row for row in targets if not bool(row[2])]
        if source_msg_id:
            _forward_outcome_update(source_chat_id, source_msg_id, state='dispatching')
        if finance_targets:
            _start_financial_forward_batch(source_chat_id, msg, list(finance_targets), list(normal_targets))
        else:
            ok = FORWARD_TASK_POOL.submit(source_chat_id, _forward_normal_stage, source_chat_id, msg, list(normal_targets))
            if not ok:
                log_error(f'FORWARD QUEUE FULL, INLINE FALLBACK: {source_chat_id}')
                _forward_normal_stage(source_chat_id, msg, list(normal_targets))
    except Exception as exc:
        log_error(f'schedule_financial_forward_pipeline {source_chat_id}: {exc}')
        if source_msg_id:
            _forward_outcome_update(source_chat_id, source_msg_id, state='failed')

def _canon_forward_any_message__001(source_chat_id: int, msg):
    try:
        source_msg_id = int(getattr(msg, 'message_id', 0) or 0)
        sender_skip_reason = _forward_sender_skip_reason(msg)
        if sender_skip_reason:
            _forward_outcome_skip(source_chat_id, msg, sender_skip_reason)
            return
        if getattr(msg, 'edit_date', None):
            _forward_outcome_skip(source_chat_id, msg, 'edited_source')
            return
        targets = sorted(list(resolve_forward_targets(source_chat_id) or []), key=lambda row: 0 if bool(row[2]) else 1)
        if not targets:
            if source_msg_id:
                _forward_outcome_update(source_chat_id, source_msg_id, state='no_targets')
            return
        if getattr(msg, 'media_group_id', None) and getattr(msg, 'content_type', None) in ('photo', 'video', 'document', 'audio'):
            if source_msg_id:
                _forward_outcome_update(source_chat_id, source_msg_id, state='media_group_pending')
            _collect_media_group_for_forward(source_chat_id, msg)
            return
        if source_msg_id:
            _forward_outcome_update(source_chat_id, source_msg_id, state='dispatching')
        for dst_chat_id, mode, finance_enabled in targets:
            _forward_single_to_target(source_chat_id, msg, dst_chat_id, finance_enabled)
        if source_msg_id:
            _forward_outcome_update(source_chat_id, source_msg_id, state='completed')
    except Exception as e:
        log_error(f'forward_any_message fatal: {e}')
# v262
