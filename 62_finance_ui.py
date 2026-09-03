# v262
def finance_mode_compact_icon(chat_id: int) -> str:
    """v108: hidden finance and visible auto-window mode are shown independently."""
    try:
        if not is_finance_mode(chat_id):
            return '⬜'
        hidden_prefix = '🙈' if is_hidden_finance_mode(chat_id) else ''
        mode = finance_window_mode(chat_id)
        if mode == 'first':
            return hidden_prefix + '✅🥇'
        if mode == 'open':
            return hidden_prefix + '✅3️⃣'
        if mode == 'normal':
            return hidden_prefix + '✅🔟'
        return hidden_prefix + '✅'
    except Exception:
        return '⬜'

def finance_mode_state_lines(chat_id: int) -> list[str]:
    """F39/v108: hidden accounting is independent; exactly one of the three visible modes may be active, or none."""
    fin_on = is_finance_mode(chat_id)
    hidden_on = bool(fin_on and is_hidden_finance_mode(chat_id))
    mode = finance_window_mode(chat_id) if fin_on else 'off'
    return [f'Чат: {chat_button_title(chat_id)}', '', f"{('✅' if fin_on else '⬜')} Фин режим", f"{('✅🙈' if hidden_on else '⬜🙈')} Скрытые финансы — независимо", f"{('✅🔟' if fin_on and mode == 'normal' else '⬜')} Как обычно — окно через 10 сообщений", f"{('✅3️⃣' if fin_on and mode == 'open' else '⬜')} Быстрый остаток — открывать окно", f"{('✅🥇' if fin_on and mode == 'first' else '⬜')} Быстрый остаток — всегда первым", '', 'Повторное нажатие активного режима окна выключает только окно; скрытые финансы остаются.']

def _v177_legacy_0196_build_finance_toggle_chat_menu(day_key: str):
    kb = types.InlineKeyboardMarkup(row_width=2)
    known = collect_forward_menu_chats()
    items = {}
    for cid, ch in known.items():
        try:
            int_cid = int(cid)
        except Exception:
            continue
        items[int_cid] = ch.get('title') or get_chat_display_name(int_cid)
    if OWNER_ID:
        try:
            owner_id = int(OWNER_ID)
            items.setdefault(owner_id, get_chat_display_name(owner_id))
        except Exception:
            pass
    buttons = []
    for int_cid, title in sorted(items.items(), key=lambda x: x[1].lower()):
        if is_chat_bot_removed(int_cid) and (not (OWNER_ID and str(int_cid) == str(OWNER_ID))):
            continue
        icon = finance_mode_compact_icon(int_cid)
        buttons.append(IB(f'{icon} {chat_button_title(int_cid, title)}', callback_data=f'd:{day_key}:fw_finmode_pick_{int_cid}'))
    add_buttons_in_rows(kb, buttons, 2)
    kb.row(IB('ℹ️ Описание чатов', callback_data='chat_desc_menu:finmode'))
    kb.row(IB('🔙 Назад', callback_data=f'd:{day_key}:back_main'))
    return kb
try:
    _v177_legacy_0196_build_finance_toggle_chat_menu.__name__ = 'build_finance_toggle_chat_menu'
except Exception:
    pass

def build_quick_balance_chat_menu(day_key: str):
    kb = types.InlineKeyboardMarkup(row_width=2)
    known = collect_forward_menu_chats()
    items = {}
    for cid, ch in known.items():
        try:
            int_cid = int(cid)
        except Exception:
            continue
        items[int_cid] = ch.get('title') or get_chat_display_name(int_cid)
    owner_item = None
    if OWNER_ID:
        try:
            owner_id = int(OWNER_ID)
            owner_item = (owner_id, get_chat_display_name(owner_id))
            items.setdefault(owner_id, owner_item[1])
        except Exception:
            owner_item = None
    buttons = []
    for int_cid, title in sorted(items.items(), key=lambda x: x[1].lower()):
        if owner_item and int_cid == owner_item[0]:
            continue
        mode = finance_window_mode(int_cid) if is_finance_mode(int_cid) else 'off'
        icon = '✅🥇' if mode == 'first' else '✅3️⃣' if mode == 'open' else '✅🔟' if mode == 'normal' else '⬜'
        buttons.append(IB(f'{icon} {chat_button_title(int_cid, title)}', callback_data=f'd:{day_key}:qb_cfg_{int_cid}'))
    add_buttons_in_rows(kb, buttons, 2)
    if owner_item:
        mode = finance_window_mode(owner_item[0]) if is_finance_mode(owner_item[0]) else 'off'
        icon = '✅🥇' if mode == 'first' else '✅3️⃣' if mode == 'open' else '✅🔟' if mode == 'normal' else '⬜'
        kb.row(IB(f'{icon} {chat_button_title(owner_item[0], owner_item[1])}', callback_data=f'd:{day_key}:qb_cfg_{owner_item[0]}'))
    kb.row(IB('🔙 Назад', callback_data=f'd:{day_key}:back_main'))
    return kb

def _v177_legacy_0198_build_quick_balance_mode_menu(day_key: str, target_chat_id: int):
    kb = types.InlineKeyboardMarkup(row_width=1)
    fin_on = is_finance_mode(target_chat_id)
    hidden_on = bool(fin_on and is_hidden_finance_mode(target_chat_id))
    mode = finance_window_mode(target_chat_id) if fin_on else 'off'
    fin_icon = '✅' if fin_on else '⬜'
    normal_icon = '✅🔟' if fin_on and mode == 'normal' else '⬜'
    open_icon = '✅3️⃣' if fin_on and mode == 'open' else '⬜'
    first_icon = '✅🥇' if fin_on and mode == 'first' else '⬜'
    hidden_icon = '✅🙈' if hidden_on else '⬜🙈'
    finwin_icon = '🪟✅' if fin_on else '🪟⬜'
    kb.row(IB(f'{fin_icon} Фин режим ВКЛ/ВЫКЛ', callback_data=f'd:{day_key}:fin_mode_toggle_{target_chat_id}'))
    kb.row(IB(f'{normal_icon} Как обычно — фин окно через 10 сообщений', callback_data=f'd:{day_key}:qb_mode_normal_{target_chat_id}'))
    kb.row(IB(f'{open_icon} Фин режим + быстрый остаток: открывать окно', callback_data=f'd:{day_key}:qb_mode_open_{target_chat_id}'))
    kb.row(IB(f'{first_icon} Фин режим + быстрый остаток: всегда первым', callback_data=f'd:{day_key}:qb_mode_first_{target_chat_id}'))
    kb.row(IB(f'{hidden_icon} Скрытые финансы', callback_data=f'd:{day_key}:qb_hidden_toggle_{target_chat_id}'), IB(f'{finwin_icon} Фин окно', callback_data=f'd:{day_key}:qb_finwin_open_{target_chat_id}'))
    kb.row(IB('🔙 Назад к чатам', callback_data=f'd:{day_key}:forward_finmode_menu'))
    return kb
try:
    _v177_legacy_0198_build_quick_balance_mode_menu.__name__ = 'build_quick_balance_mode_menu'
except Exception:
    pass

def _v177_legacy_0199_build_finance_mode_config_menu(day_key: str, target_chat_id: int):
    """Подменю после: Фин режим → выбор чата. Объединяет финрежим и старый быстрый остаток."""
    return build_quick_balance_mode_menu(day_key, target_chat_id)
try:
    _v177_legacy_0199_build_finance_mode_config_menu.__name__ = 'build_finance_mode_config_menu'
except Exception:
    pass

def build_finance_mode_config_text(target_chat_id: int) -> str:
    return '💰 Фин режим / В24\n' + '\n'.join(finance_mode_state_lines(target_chat_id))

def _canon_apply_finance_window_mode_choice__001(chat_id: int, selected_mode: str) -> str:
    """F39/v108: the three visible modes are mutually exclusive; clicking the active one turns only windows off."""
    chat_id = int(chat_id)
    selected_mode = str(selected_mode or 'off')
    if selected_mode not in {'normal', 'open', 'first'}:
        selected_mode = 'off'
    was_finance = is_finance_mode(chat_id)
    if not was_finance:
        set_finance_mode(chat_id, True)
        set_hidden_finance_mode(chat_id, True)
    current = finance_window_mode(chat_id)
    if current == selected_mode:
        set_finance_window_mode(chat_id, 'off', persist_now=False)
        delete_auto_finance_windows_for_chat(chat_id, persist_now=False)
        _persist_finance_window_mode_critical(chat_id)
        return 'off'
    delete_auto_finance_windows_for_chat(chat_id, persist_now=False)
    set_finance_window_mode(chat_id, selected_mode, persist_now=False)
    try:
        store = get_chat_store(chat_id)
        day_key = store.get('current_view_day') or today_key()
        if selected_mode == 'normal':
            store['main_window_msg_count'] = 0
            recreate_main_window_now(chat_id, day_key)
        else:
            store['balance_panel_msg_count'] = 0
            send_minimized_balance_panel(chat_id)
            if selected_mode == 'first':
                schedule_quick_balance_first_recreate(chat_id, 60.0)
    except Exception as e:
        log_error(f'_apply_finance_window_mode_choice({chat_id},{selected_mode}): {e}')
    _finance_window_state(chat_id)['auto_reopen_on_boot'] = True
    _persist_finance_window_mode_critical(chat_id)
    return selected_mode

def build_hidden_finance_chat_menu(day_key: str):
    kb = types.InlineKeyboardMarkup(row_width=2)
    known = collect_forward_menu_chats()
    items = {}
    for cid, ch in known.items():
        try:
            int_cid = int(cid)
        except Exception:
            continue
        items[int_cid] = ch.get('title') or get_chat_display_name(int_cid)
    if OWNER_ID:
        try:
            owner_id = int(OWNER_ID)
            items.setdefault(owner_id, get_chat_display_name(owner_id))
        except Exception:
            pass
    buttons = []
    for int_cid, title in sorted(items.items(), key=lambda x: x[1].lower()):
        if is_chat_bot_removed(int_cid) and (not (OWNER_ID and str(int_cid) == str(OWNER_ID))):
            continue
        enabled = is_hidden_finance_mode(int_cid)
        icon = '✅🙈' if enabled else '⬜🙈'
        buttons.append(IB(f'{icon} {chat_button_title(int_cid, title)}', callback_data=f'd:{day_key}:hf_pick_{int_cid}'))
    add_buttons_in_rows(kb, buttons, 2)
    kb.row(IB('🔙 Назад', callback_data=f'd:{day_key}:back_main'))
    return kb

def build_edit_records_keyboard(day_key: str, chat_id: int, prefix: str='d', owner_day_key: str | None=None):
    store = get_chat_store(chat_id)
    selected = set((int(x) for x in (store.get('edit_delete_selected', {}) or {}).get(day_key, [])))
    kb = types.InlineKeyboardMarkup(row_width=3)
    day_recs = store.get('daily_records', {}).get(day_key, [])
    for r in day_recs:
        rid = int(r['id'])
        lbl = f" {fmt_num(r['amount'])}"
        del_icon = '☑️' if rid in selected else '❌'
        if prefix == 'fv':
            del_cb = f'fv:{chat_id}:{day_key}:del_toggle_{rid}:{owner_day_key or today_key()}'
        else:
            del_cb = f'd:{day_key}:del_toggle_{rid}'
        insert_text = compose_direct_edit_insert_value(chat_id, rid, day_key, r.get('amount', 0), r.get('note', ''))
        kb.row(IB(lbl, callback_data='none'), make_direct_edit_insert_button('✏️', insert_text, viewer_chat_id=int(OWNER_ID) if prefix == 'fv' and OWNER_ID else chat_id), IB(del_icon, callback_data=del_cb))
    if selected:
        if prefix == 'fv':
            kb.row(IB('🗑 Удалить выбранное', callback_data=f'fv:{chat_id}:{day_key}:del_selected:{owner_day_key or today_key()}'))
        else:
            kb.row(IB('🗑 Удалить выбранное', callback_data=f'd:{day_key}:del_selected'))
    if prefix == 'fv':
        kb.row(IB('🔙 Назад', callback_data=f'fv:{chat_id}:{day_key}:clear_delete_back:{owner_day_key or today_key()}'))
    else:
        kb.row(IB('🔙 Назад', callback_data=f'd:{day_key}:back_main'))
    return kb

def build_usd_edit_records_keyboard(day_key: str, chat_id: int, prefix: str='d', owner_day_key: str | None=None):
    """USD counterpart of build_edit_records_keyboard, including owner-view callbacks."""
    store = get_chat_store(int(chat_id))
    selected = set((int(x) for x in (store.get('usd_edit_delete_selected', {}) or {}).get(str(day_key), [])))
    kb = types.InlineKeyboardMarkup(row_width=3)
    rows = usd_records_for_day(int(chat_id), str(day_key))
    viewer_chat_id = int(OWNER_ID) if prefix == 'fv' and OWNER_ID else int(chat_id)
    for rec in rows:
        rid = int(rec.get('id'))
        amt = float(rec.get('usd_amount', 0) or 0)
        sid = str(rec.get('usd_short_id') or f'U{rid}')
        label = f"{sid} {('+' if amt >= 0 else '-')}${fmt_num_plain(abs(amt))}"
        insert_text = compose_usd_edit_insert_value(chat_id, rid, _record_day_key(rec), amt, rec.get('usd_note') or rec.get('note', ''))
        del_icon = '☑️' if rid in selected else '❌'
        if prefix == 'fv':
            del_cb = f'fv:{chat_id}:{day_key}:del_toggle_{rid}:{owner_day_key or today_key()}'
        else:
            del_cb = f'd:{day_key}:del_toggle_{rid}'
        kb.row(IB(label, callback_data='none'), make_direct_edit_insert_button('✏️', insert_text, viewer_chat_id=viewer_chat_id), IB(del_icon, callback_data=del_cb))
    if selected:
        if prefix == 'fv':
            kb.row(IB('🗑 Удалить выбранное USD', callback_data=f'fv:{chat_id}:{day_key}:del_selected:{owner_day_key or today_key()}'))
        else:
            kb.row(IB('🗑 Удалить выбранное USD', callback_data=f'd:{day_key}:del_selected'))
    if prefix == 'fv':
        kb.row(IB('🔙 Назад', callback_data=f'fv:{chat_id}:{day_key}:clear_delete_back:{owner_day_key or today_key()}'))
    else:
        kb.row(IB('🔙 Назад', callback_data=f'd:{day_key}:back_main'))
    return kb

def toggle_usd_edit_delete_selection(chat_id: int, day_key: str, rid: int):
    store = get_chat_store(int(chat_id))
    all_sel = store.setdefault('usd_edit_delete_selected', {})
    selected = set((int(x) for x in all_sel.get(str(day_key), [])))
    rid = int(rid)
    if rid in selected:
        selected.remove(rid)
    else:
        selected.add(rid)
    if selected:
        all_sel[str(day_key)] = sorted(selected)
    else:
        all_sel.pop(str(day_key), None)
    save_data(data, chat_ids=[int(chat_id)])

def clear_usd_edit_delete_selection(chat_id: int, day_key: str | None=None):
    store = get_chat_store(int(chat_id))
    all_sel = store.setdefault('usd_edit_delete_selected', {})
    if day_key is None:
        all_sel.clear()
    else:
        all_sel.pop(str(day_key), None)
    save_data(data, chat_ids=[int(chat_id)])

def delete_selected_usd_records(chat_id: int, day_key: str) -> int:
    """Remove only the USD component. Pure USD rows are deleted completely; mixed ARS/USD rows keep ARS."""
    chat_id = int(chat_id)
    with locked_chat(chat_id):
        store = get_chat_store(chat_id)
        selected = {int(x) for x in store.setdefault('usd_edit_delete_selected', {}).get(str(day_key), []) or []}
        if not selected:
            return 0
        deleted = 0
        remove_ids = set()
        _r16_deleted_usd_total = 0.0
        for rec in store.get('records', []) or []:
            try:
                rid = int(rec.get('id', -1))
            except Exception:
                continue
            if rid not in selected or not float(rec.get('usd_amount', 0) or 0):
                continue
            deleted += 1
            try: _r16_deleted_usd_total += float(rec.get('usd_amount', 0) or 0)
            except Exception: pass
            if abs(float(rec.get('amount', 0) or 0)) <= 0 and bool(rec.get('usd_only', False)):
                remove_ids.add(rid)
            else:
                rec['usd_amount'] = 0.0
                rec['usd_note'] = ''
                rec['usd_only'] = False
        if remove_ids:
            store['records'] = [r for r in store.get('records', []) or [] if int(r.get('id', -1)) not in remove_ids]
        for dk, arr in list((store.get('daily_records', {}) or {}).items()):
            new_arr = []
            for rec in arr or []:
                try:
                    rid = int(rec.get('id', -1))
                except Exception:
                    new_arr.append(rec)
                    continue
                if rid in remove_ids:
                    continue
                if rid in selected and float(rec.get('usd_amount', 0) or 0):
                    rec['usd_amount'] = 0.0
                    rec['usd_note'] = ''
                    rec['usd_only'] = False
                new_arr.append(rec)
            if new_arr:
                store['daily_records'][dk] = new_arr
            else:
                store['daily_records'].pop(dk, None)
        store.setdefault('usd_edit_delete_selected', {}).pop(str(day_key), None)
        # R16: removing a USD component does not require a full ARS history normalize.
        # Pure-USD rows carry zero ARS amount, so ARS balance is unchanged.
        store['_finance_hotpath_pending_normalize_r16'] = True
        store['_finance_fast_generation_r16'] = int(store.get('_finance_fast_generation_r16', 0) or 0) + 1
        store.pop('_finance_day_balance_cache_r16', None)
        if '_usd_balance_cache_r16' in store:
            try: store['_usd_balance_cache_r16'] = float(store.get('_usd_balance_cache_r16', 0) or 0) - float(_r16_deleted_usd_total)
            except Exception: store.pop('_usd_balance_cache_r16', None)
        if 'persist_finance_chat_local_fast' in globals():
            persist_finance_chat_local_fast(chat_id)
        else:
            save_data(data, chat_ids=[chat_id])
        if callable(globals().get('_v262_schedule_finance_postcommit')):
            _v262_schedule_finance_postcommit(chat_id, str(day_key), 'delete_selected_usd')
        else:
            rebuild_global_records()
            finance_changed(chat_id, str(day_key), reason='delete_selected_usd', delay=0.1)
        return deleted

def toggle_edit_delete_selection(chat_id: int, day_key: str, rid: int):
    store = get_chat_store(chat_id)
    all_sel = store.setdefault('edit_delete_selected', {})
    selected = set((int(x) for x in all_sel.get(day_key, [])))
    rid = int(rid)
    if rid in selected:
        selected.remove(rid)
    else:
        selected.add(rid)
    if selected:
        all_sel[day_key] = sorted(selected)
    else:
        all_sel.pop(day_key, None)
    save_data(data)

def clear_edit_delete_selection(chat_id: int, day_key: str | None=None):
    store = get_chat_store(chat_id)
    all_sel = store.setdefault('edit_delete_selected', {})
    if day_key is None:
        all_sel.clear()
    else:
        all_sel.pop(day_key, None)
    save_data(data)

def update_record_in_chat(chat_id: int, rid: int, amount: float, note: str, source_finance_text: str | None=None, source_msg_id: int | None=None) -> bool:
    """Edit one finance row and persist the matching ARS/USD ledger mirror immediately.

    Normal edits target the active ledger by R-id.  💰Перес can additionally pass the bot-copy
    message id, which lets an old pre-deploy row be edited even when it currently lives in a
    non-active currency ledger with a colliding R-id.
    """
    bot_journal('record_update_start', chat_id, f"rid={rid} amount={amount} note={note} msg={source_msg_id or ''}")
    if globals().get('constitution_finance_write_blocked_v232') and constitution_finance_write_blocked_v232():
        return False
    chat_id = int(chat_id)
    rid = int(rid)
    op_id = operation_begin('finance_edit', chat_id, target=str(rid), payload={'amount': amount, 'note': note, 'source_msg_id': source_msg_id}, critical=True) if 'operation_begin' in globals() else ''
    store = get_chat_store(chat_id)
    active = _ensure_currency_ledgers(store)

    def _match(rec):
        if not isinstance(rec, dict):
            return False
        try:
            if int(rec.get('id', -1)) != rid:
                return False
        except Exception:
            return False
        return source_msg_id is None or _record_has_message_id(rec, int(source_msg_id))
    record_keys = ['records'] if source_msg_id is None else ['records', 'ars_records', 'usd_records']
    targets = []
    touched_ledgers = set()
    seen = set()
    for key in record_keys:
        for rec in store.get(key, []) or []:
            if not _match(rec):
                continue
            oid = id(rec)
            if oid in seen:
                continue
            seen.add(oid)
            targets.append((key, rec))
            if key == 'ars_records':
                touched_ledgers.add('ars')
            elif key == 'usd_records':
                touched_ledgers.add('usd')
            elif key == 'records':
                touched_ledgers.add(active)
    if not targets:
        if op_id and 'operation_review' in globals():
            operation_review(op_id, 'record not found')
        return False
    before_snapshot = copy.deepcopy(targets[0][1]) if targets else {}
    for _key, target in targets:
        target['amount'] = amount
        target['note'] = note
        if source_finance_text is not None:
            target['source_finance_text'] = str(source_finance_text or '').strip()
    daily_keys = ['daily_records'] if source_msg_id is None else ['daily_records', 'ars_daily_records', 'usd_daily_records']
    for dkey in daily_keys:
        for _dk, arr in (store.get(dkey, {}) or {}).items():
            for rec in arr or []:
                if not _match(rec):
                    continue
                rec['amount'] = amount
                rec['note'] = note
                if source_finance_text is not None:
                    rec['source_finance_text'] = str(source_finance_text or '').strip()
    store['balance'] = sum((float(r.get('amount', 0) or 0) for r in store.get('records', []) or []))
    for ledger in touched_ledgers:
        if ledger == active:
            continue
        store[f'{ledger}_balance'] = sum((float(r.get('amount', 0) or 0) for r in store.get(f'{ledger}_records', []) or []))
    _snapshot_active_currency_ledger(store, active)
    # R7: amount/note edit does not reorder records. Avoid full monthly/global
    # rebuild in the Telegram request path; derived aggregates run once later.
    try:
        for _key, _target in targets:
            ensure_finance_record_uid(chat_id, _target)
    except Exception:
        pass
    if 'persist_finance_chat_local_fast' in globals():
        persist_finance_chat_local_fast(chat_id)
    else:
        save_data(data, chat_ids=[chat_id])
    try:
        _dk = str((targets[0][1] if targets else {}).get('day_key') or store.get('current_view_day') or '')
        schedule_financial_window_refresh(chat_id, _dk, reason='record_edit_fast_v168')
    except Exception:
        pass
    try:
        schedule_finance_postcommit_background_v243(chat_id, reason='record_edit_r7', delay=0.25)
    except Exception:
        pass
    try:
        finance_cache_invalidate(chat_id, 'finance_edit')
        finance_integrity_append(chat_id, 'edit', targets[0][1] if targets else {'id': rid}, details={'before': before_snapshot})
    except Exception as _integrity_exc:
        log_error(f'finance edit integrity: {_integrity_exc}')
    if op_id and 'operation_complete' in globals():
        operation_complete(op_id, f'record={rid}')
    return True

def delete_selected_records(chat_id: int, day_key: str) -> int:
    if globals().get('constitution_finance_write_blocked_v232') and constitution_finance_write_blocked_v232():
        return 0
    with locked_chat(chat_id):
        'Удаляет все отмеченные ☑️ записи одним проходом, без ошибки из-за перенумерации id.'
        store = get_chat_store(chat_id)
        all_sel = store.setdefault('edit_delete_selected', {})
        selected = {int(x) for x in all_sel.get(day_key, [])}
        if not selected:
            return 0
        op_id = operation_begin('finance_bulk_delete', chat_id, target=str(day_key), payload={'selected': sorted(selected)}, critical=True) if 'operation_begin' in globals() else ''
        deleted_snapshot = [copy.deepcopy(r) for r in store.get('records', []) or [] if int(r.get('id', -1)) in selected]
        before = len(store.get('records', []) or [])
        store['records'] = [r for r in store.get('records', []) or [] if int(r.get('id', -1)) not in selected]
        daily = store.get('daily_records', {}) or {}
        for dk in list(daily.keys()):
            arr = daily.get(dk, []) or []
            arr2 = [r for r in arr if int(r.get('id', -1)) not in selected]
            if arr2:
                daily[dk] = arr2
            else:
                daily.pop(dk, None)
        deleted = before - len(store.get('records', []) or [])
        all_sel.pop(day_key, None)
        # R16: stable IDs; update only the aggregate affected by the deleted rows.
        try: store['balance'] = float(store.get('balance', 0) or 0) - sum(float(r.get('amount', 0) or 0) for r in deleted_snapshot)
        except Exception: pass
        store['_finance_hotpath_pending_normalize_r16'] = True
        store['_finance_fast_generation_r16'] = int(store.get('_finance_fast_generation_r16', 0) or 0) + 1
        store.pop('_finance_day_balance_cache_r16', None)
        if '_usd_balance_cache_r16' in store:
            try: store['_usd_balance_cache_r16'] = float(store.get('_usd_balance_cache_r16', 0) or 0) - sum(float(r.get('usd_amount', 0) or 0) for r in deleted_snapshot)
            except Exception: store.pop('_usd_balance_cache_r16', None)
        if 'persist_finance_chat_local_fast' in globals():
            persist_finance_chat_local_fast(chat_id)
        else:
            save_data(data, chat_ids=[chat_id])
        if callable(globals().get('_v262_schedule_finance_postcommit')):
            _v262_schedule_finance_postcommit(chat_id, day_key, 'delete_selected')
        else:
            rebuild_global_records()
            try:
                schedule_financial_window_refresh(chat_id, day_key, reason='record_delete_fast_v168')
            except Exception:
                pass
            finance_changed(chat_id, day_key, reason='delete_selected', delay=0.1)
        try:
            finance_cache_invalidate(chat_id, 'finance_bulk_delete')
            finance_integrity_append(chat_id, 'bulk_delete', {'ids': sorted(selected)}, details={'records': deleted_snapshot})
        except Exception as _integrity_exc:
            log_error(f'finance bulk delete integrity: {_integrity_exc}')
        if op_id and 'operation_complete' in globals():
            operation_complete(op_id, f'deleted={deleted}')
        return deleted

def _v177_legacy_0200_build_fin_windows_chat_menu(day_key: str):
    kb = types.InlineKeyboardMarkup(row_width=2)
    items = []
    for cid, store in (data.get('chats', {}) or {}).items():
        try:
            int_cid = int(cid)
        except Exception:
            continue
        if not is_finance_mode(int_cid):
            continue
        if is_chat_bot_removed(int_cid) and (not (OWNER_ID and str(int_cid) == str(OWNER_ID))):
            continue
        items.append((int_cid, get_chat_display_name(int_cid)))
    buttons = [IB(chat_button_title(cid, title), callback_data=f'd:{day_key}:finwin_open_{cid}') for cid, title in sorted(items, key=lambda x: x[1].lower())]
    if buttons:
        add_buttons_in_rows(kb, buttons, 2)
    else:
        kb.row(IB('Нет чатов с финрежимом', callback_data='none'))
    kb.row(IB('🔙 Назад', callback_data=f'd:{day_key}:back_main'))
    return kb
try:
    _v177_legacy_0200_build_fin_windows_chat_menu.__name__ = 'build_fin_windows_chat_menu'
except Exception:
    pass

def build_fin_window_view_keyboard(target_chat_id: int, day_key: str, owner_day_key: str):
    kb = types.InlineKeyboardMarkup(row_width=3)
    prev_day = (datetime.strptime(day_key, '%Y-%m-%d') - timedelta(days=1)).strftime('%Y-%m-%d')
    next_day = (datetime.strptime(day_key, '%Y-%m-%d') + timedelta(days=1)).strftime('%Y-%m-%d')
    nav_row = [IB('⬅️ Вчера', callback_data=f'fv:{target_chat_id}:{prev_day}:open:{owner_day_key}')]
    if day_key != today_key():
        nav_row.append(IB('📅 Сегодня', callback_data=f'fv:{target_chat_id}:{today_key()}:open:{owner_day_key}'))
    nav_row.append(IB('➡️ Завтра', callback_data=f'fv:{target_chat_id}:{next_day}:open:{owner_day_key}'))
    kb.row(*nav_row)
    kb.row(IB('📝 Редактировать', callback_data=f'fv:{target_chat_id}:{day_key}:edit_list:{owner_day_key}'), IB('📂 CSV', callback_data=f'fv:{target_chat_id}:{day_key}:csv_menu:{owner_day_key}'), IB('📊 Статьи', callback_data=fvcat_callback(f'fvcat_today:{target_chat_id}:{owner_day_key}')))
    kb.row(IB('📅 Календарь', callback_data=f'fv:{target_chat_id}:{day_key}:calendar:{owner_day_key}'), IB('📊 Отчёт', callback_data=f'fv:{target_chat_id}:{day_key}:report:{owner_day_key}'), IB('💰 Общий итог', callback_data=f'fv:{target_chat_id}:{day_key}:total:{owner_day_key}'))
    if usd_transactions_view_enabled(int(target_chat_id)):
        kb.row(IB('📆 За месяц', callback_data=f'fv:{target_chat_id}:{day_key}:usd_month:{owner_day_key}'))
    kb.row(IB('⚙️ Обнулить', callback_data=f'fv:{target_chat_id}:{day_key}:reset:{owner_day_key}'), IB('ℹ️ Инфо', callback_data=f'fv:{target_chat_id}:{day_key}:info:{owner_day_key}'), IB('🔙 Назад к списку', callback_data=f'd:{owner_day_key}:fin_windows_menu'))
    kb.row(IB('⬅️ Назад осн. окно', callback_data=f'd:{owner_day_key}:back_main'))
    return kb

def _v177_legacy_0201_build_fin_window_usd_month_keyboard(target_chat_id: int, day_key: str, owner_day_key: str):
    try:
        dt = datetime.strptime(str(day_key)[:10], '%Y-%m-%d').replace(day=1)
    except Exception:
        dt = now_local().replace(day=1)
    prev_dt = (dt - timedelta(days=1)).replace(day=1)
    next_dt = (dt.replace(day=28) + timedelta(days=4)).replace(day=1)
    kb = types.InlineKeyboardMarkup(row_width=3)
    kb.row(IB('⬅️ Пред. месяц', callback_data=f"fv:{target_chat_id}:{prev_dt.strftime('%Y-%m-01')}:usd_month:{owner_day_key}"), IB('📅 Этот месяц', callback_data=f'fv:{target_chat_id}:{today_key()}:usd_month:{owner_day_key}'), IB('След. месяц ➡️', callback_data=f"fv:{target_chat_id}:{next_dt.strftime('%Y-%m-01')}:usd_month:{owner_day_key}"))
    kb.row(IB('🔙 Назад к чату', callback_data=f'fv:{target_chat_id}:{day_key}:open:{owner_day_key}'))
    kb.row(IB('⬅️ Назад осн. окно', callback_data=f'd:{owner_day_key}:back_main'))
    return kb
try:
    _v177_legacy_0201_build_fin_window_usd_month_keyboard.__name__ = 'build_fin_window_usd_month_keyboard'
except Exception:
    pass

def build_fin_window_menu_keyboard(target_chat_id: int, day_key: str, owner_day_key: str):
    """Совместимость: отдельного меню больше нет."""
    return build_fin_window_view_keyboard(target_chat_id, day_key, owner_day_key)

def build_fin_window_csv_menu(target_chat_id: int, day_key: str, owner_day_key: str):
    kb = types.InlineKeyboardMarkup(row_width=3)
    _add_export_period_rows(kb, day_key, 'fv', owner_day_key=owner_day_key, target_chat_id=target_chat_id)
    kb.row(IB('🔙 Назад', callback_data=f'fv:{target_chat_id}:{day_key}:open:{owner_day_key}'))
    kb.row(IB('⬅️ Назад осн. окно', callback_data=f'd:{owner_day_key}:back_main'))
    return kb

def _v177_legacy_0202_send_csv_for_chat_to(recipient_chat_id: int, target_chat_id: int, mode: str, day_key: str):
    """Отправляет CSV владельцу, но данные берёт из target_chat_id."""
    try:
        store = get_chat_store(target_chat_id)
        if financial_view_is_usd(store):
            return send_export_for_chat_to(recipient_chat_id, target_chat_id, mode, day_key, 'csv')
        rows = []
        caption = f'📂 CSV: {get_chat_display_name(target_chat_id)}'
        if mode == 'all':
            save_chat_json(target_chat_id)
            path = chat_csv_file(target_chat_id)
            if os.path.exists(path):
                fobj = file_bytesio_named(path, export_display_filename(target_chat_id, mode, day_key, 'csv'))
                if fobj:
                    _tg_call_retry(bot.send_document, recipient_chat_id, fobj, caption=caption, purpose='send_csv_for_chat_to')
                return
        elif mode == 'day':
            for r in store.get('daily_records', {}).get(day_key, []) or []:
                rows.append((fmt_date_table(day_key), fmt_csv_amount(r.get('amount')), r.get('note', '')))
            caption = f'📅 CSV за день {fmt_date_table(day_key)}: {get_chat_display_name(target_chat_id)}'
        elif mode == 'week':
            base = datetime.strptime(day_key, '%Y-%m-%d')
            start = base - timedelta(days=6)
            for i in range(7):
                dk = (start + timedelta(days=i)).strftime('%Y-%m-%d')
                for r in store.get('daily_records', {}).get(dk, []) or []:
                    rows.append((fmt_date_table(dk), fmt_csv_amount(r.get('amount')), r.get('note', '')))
            caption = f'🗓 CSV за неделю: {get_chat_display_name(target_chat_id)}'
        elif mode == 'month':
            base = datetime.strptime(day_key, '%Y-%m-%d')
            start = base.replace(day=1)
            for dk, recs in (store.get('daily_records', {}) or {}).items():
                try:
                    dt = datetime.strptime(dk, '%Y-%m-%d')
                except Exception:
                    continue
                if start <= dt <= base:
                    for r in recs or []:
                        rows.append((fmt_date_table(dk), fmt_csv_amount(r.get('amount')), r.get('note', '')))
            caption = f'📆 CSV за месяц: {get_chat_display_name(target_chat_id)}'
        elif mode == 'wedthu':
            base = datetime.strptime(day_key, '%Y-%m-%d')
            while base.weekday() != 2:
                base -= timedelta(days=1)
            for i in range(2):
                dk = (base + timedelta(days=i)).strftime('%Y-%m-%d')
                for r in store.get('daily_records', {}).get(dk, []) or []:
                    rows.append((fmt_date_table(dk), fmt_csv_amount(r.get('amount')), r.get('note', '')))
            caption = f'📊 CSV Ср–Чт: {get_chat_display_name(target_chat_id)}'
        if not rows:
            send_and_auto_delete(recipient_chat_id, 'Нет данных для CSV.', 8)
            return
        tmp_name = os.path.join(MEGA_LOCAL_TMP_DIR, f'fv_csv_{target_chat_id}_{mode}_{int(time.time())}.csv')
        with open(tmp_name, 'w', newline='', encoding='utf-8') as f:
            w = csv.writer(f)
            w.writerow(['date', 'amount', 'note'])
            write_csv_rows_with_day_gaps(w, rows, 3)
        fobj = file_bytesio_named(tmp_name, export_display_filename(target_chat_id, mode, day_key, 'csv'))
        if fobj:
            _tg_call_retry(bot.send_document, recipient_chat_id, fobj, caption=caption, purpose='send_csv_for_chat_to')
        try:
            os.remove(tmp_name)
        except Exception:
            pass
    except Exception as e:
        log_error(f'send_csv_for_chat_to({get_chat_display_name(target_chat_id)}): {e}')
try:
    _v177_legacy_0202_send_csv_for_chat_to.__name__ = 'send_csv_for_chat_to'
except Exception:
    pass

def _v177_legacy_0203_period_export_rows(chat_id: int, mode: str, day_key: str):
    """Rows for CSV/XLSX in the currently selected ARS or 💵 USD operations view."""
    store = get_chat_store(chat_id)
    if financial_view_is_usd(store):
        ensure_usd_migration_for_chat(int(chat_id))
    mode = str(mode or 'all').replace('csv_', '').replace('xlsx_', '')
    if mode == 'all_real':
        mode = 'all'
    rows = []

    def _append_day(dk: str):
        for r in financial_view_records_for_day_store(store, dk):
            rows.append((fmt_date_table(dk), fmt_csv_amount(financial_view_amount(store, r)), financial_view_note(store, r)))
    if mode == 'day':
        _append_day(day_key)
        label = f'за день {fmt_date_table(day_key)}'
    elif mode == 'week':
        base = datetime.strptime(day_key, '%Y-%m-%d')
        start = base - timedelta(days=6)
        for i in range(7):
            _append_day((start + timedelta(days=i)).strftime('%Y-%m-%d'))
        label = 'за неделю'
    elif mode == 'month':
        base = datetime.strptime(day_key, '%Y-%m-%d')
        start = base.replace(day=1)
        for dk in sorted((store.get('daily_records', {}) or {}).keys()):
            try:
                dt = datetime.strptime(dk, '%Y-%m-%d')
            except Exception:
                continue
            if start <= dt <= base:
                _append_day(dk)
        label = 'за месяц'
    elif mode == 'wedthu':
        base = datetime.strptime(day_key, '%Y-%m-%d')
        while base.weekday() != 2:
            base -= timedelta(days=1)
        for i in range(2):
            _append_day((base + timedelta(days=i)).strftime('%Y-%m-%d'))
        label = 'Ср–Чт'
    else:
        for dk in sorted((store.get('daily_records', {}) or {}).keys()):
            _append_day(dk)
        label = 'за всё время'
    if financial_view_is_usd(store):
        label = 'USD ' + label
    return (rows, label)
try:
    _v177_legacy_0203_period_export_rows.__name__ = '_period_export_rows'
except Exception:
    pass
# v262
