# v262
@bot.message_handler(func=lambda m: not (m.text and m.text.startswith('/')), content_types=['text', 'photo', 'video', 'animation', 'audio', 'voice', 'video_note', 'document', 'sticker', 'location', 'venue', 'contact', 'dice', 'poll', 'game', 'story', 'paid_media', 'invoice'])
def on_any_message(msg):
    chat_id = msg.chat.id
    if is_owner_chat(chat_id):
        finance_active_chats.add(chat_id)
    try:
        update_chat_info_from_message(msg)
    except Exception:
        pass
    try:
        bot_journal('message_received', chat_id, describe_msg_for_log(msg))
    except Exception:
        pass
    if msg.content_type == 'document':
        try:
            _restore_chat = globals().get('restore_mode')
            _doc = getattr(msg, 'document', None)
            _fname = str(getattr(_doc, 'file_name', '') or '').lower()
            _restore_ext = _fname.endswith(('.json', '.ison', '.csv', '.gz'))
            _owner_json_prompt = _restore_chat is None and is_owner_chat(chat_id) and _fname.endswith(('.json', '.ison'))
            if _restore_chat is not None and int(_restore_chat) == int(chat_id) and _restore_ext or _owner_json_prompt:
                _restore_doc_handler = globals().get('handle_document')
                if callable(_restore_doc_handler):
                    bot_journal('restore_document_routed_v183', chat_id, f'file={_fname}; mode={_restore_chat}')
                    return _restore_doc_handler(msg)
                raise RuntimeError('restore document handler is unavailable')
        except Exception as _restore_route_exc:
            log_error(f'v183 restore document route failed: {_restore_route_exc}')
            try:
                send_and_auto_delete(chat_id, f'❌ Файл восстановления не обработан: {_restore_route_exc}', 15)
            except Exception:
                pass
            return
    if msg.content_type == 'text':
        try:
            fn = globals().get('handle_journal_filename_input')
            if callable(fn) and fn(msg):
                return
        except Exception as _journal_name_exc:
            log_error(f'journal filename route: {_journal_name_exc}')
    if msg.content_type == 'text':
        try:
            _keepalive_input = globals().get('keepalive_handle_message')
            if callable(_keepalive_input) and _keepalive_input(msg):
                return
        except Exception as _keepalive_input_exc:
            log_error(f'v205 keepalive input route: {_keepalive_input_exc}')
        try:
            _constructor_input = globals().get('ui_constructor_handle_message')
            if callable(_constructor_input) and _constructor_input(msg):
                return
        except Exception as _constructor_input_exc:
            log_error(f'v205 constructor input route: {_constructor_input_exc}')
    try:
        _tenant_google_input = globals().get('tenant_google_handle_message')
        if callable(_tenant_google_input) and _tenant_google_input(msg):
            return
    except Exception as e:
        log_error(f'tenant google input handler error: {e}')
    if handle_secret_full_edit_reply(msg):
        return
    if handle_secret_sequence(msg):
        return
    if handle_secret_edit_insert_message(msg):
        return
    if handle_secret_input_message(msg):
        return
    try:
        if not getattr(getattr(msg, 'from_user', None), 'is_bot', False):
            bump_quick_balance_recreate_counter(chat_id)
    except Exception:
        pass
    if msg.content_type == 'text':
        try:
            if handle_secret_note_message(msg):
                return
            if handle_direct_edit_insert_message(msg):
                return
            if handle_gomonk_insert_message(msg):
                return
            if handle_category_edit_message(msg):
                return
            if handle_category_add_message(msg):
                return
        except Exception as e:
            log_error(f'secret/category_add/edit/direct-edit message handler error: {e}')
    if msg.content_type == 'text':
        try:
            store = get_chat_store(chat_id)
            if store.get('reset_wait'):
                text_up = (msg.text or '').strip().upper()
                if text_up == 'ДА':
                    _durable_note_source_consumed('reset_wait')
                    store['reset_wait'] = False
                    store['reset_time'] = 0
                    save_data(data)
                    cleanup_forward_links(chat_id)
                    reset_chat_data(chat_id)
                    send_and_auto_delete(chat_id, '✅ Данные чата обнулены.', 10)
                    try:
                        bot.delete_message(chat_id, msg.message_id)
                    except Exception:
                        pass
                    return
        except Exception as e:
            log_error(f'reset_wait handler error: {e}')
    if msg.content_type == 'text':
        try:
            store = get_chat_store(chat_id)
            finwin_reset_wait = store.get('finwin_reset_wait')
            if finwin_reset_wait and finwin_reset_wait.get('type') == 'finwin_reset':
                text_up = (msg.text or '').strip().upper()
                target_chat_id = int(finwin_reset_wait.get('target_chat_id'))
                fin_window_msg_id = finwin_reset_wait.get('fin_window_msg_id')
                owner_day_key = finwin_reset_wait.get('owner_day_key') or today_key()
                if text_up == 'ДА':
                    _durable_note_source_consumed('finwin_reset_wait')
                    store['finwin_reset_wait'] = None
                    save_data(data)
                    cleanup_forward_links(target_chat_id)
                    reset_chat_data(target_chat_id)
                    send_and_auto_delete(chat_id, f'✅ Данные чата {get_chat_display_name(target_chat_id)} обнулены.', 10)
                    try:
                        bot.delete_message(chat_id, msg.message_id)
                    except Exception:
                        pass
                    if fin_window_msg_id:
                        try:
                            safe_txt = render_fin_window_text(target_chat_id, today_key())
                            bot.edit_message_text(safe_txt, chat_id=chat_id, message_id=int(fin_window_msg_id), reply_markup=build_fin_window_view_keyboard(target_chat_id, today_key(), owner_day_key), parse_mode='HTML')
                        except Exception as e:
                            log_error(f'finwin reset refresh failed: {e}')
                    return
                elif text_up in {'НЕТ', 'ОТМЕНА', 'CANCEL'}:
                    _durable_note_source_consumed('finwin_reset_wait')
                    store['finwin_reset_wait'] = None
                    save_data(data)
                    send_and_auto_delete(chat_id, '❎ Обнуление отменено.', 8)
                    try:
                        bot.delete_message(chat_id, msg.message_id)
                    except Exception:
                        pass
                    return
        except Exception as e:
            log_error(f'finwin_reset_wait handler error: {e}')
    if msg.content_type == 'text':
        try:
            store = get_chat_store(chat_id)
            wait = store.get('finance_toggle_wait')
            if wait:
                text_up = (msg.text or '').strip().upper()
                if text_up == 'ДА':
                    _durable_note_source_consumed('finance_toggle_wait')
                    target_chat_id = int(wait.get('target_chat_id'))
                    set_finance_mode(target_chat_id, not is_finance_mode(target_chat_id))
                    store['finance_toggle_wait'] = None
                    save_data(data)
                    send_and_auto_delete(chat_id, f'💰 Финансовый режим для {get_chat_display_name(target_chat_id)}: {format_finance_mode_label(target_chat_id)}', 10)
                    try:
                        bot.delete_message(chat_id, msg.message_id)
                    except Exception:
                        pass
                    return
                elif text_up in {'НЕТ', 'ОТМЕНА', 'CANCEL'}:
                    _durable_note_source_consumed('finance_toggle_wait')
                    store['finance_toggle_wait'] = None
                    save_data(data)
                    send_and_auto_delete(chat_id, '❎ Переключение финансового режима отменено.', 8)
                    try:
                        bot.delete_message(chat_id, msg.message_id)
                    except Exception:
                        pass
                    return
        except Exception as e:
            log_error(f'finance_toggle_wait handler error: {e}')
    if restore_mode is not None and restore_mode == chat_id:
        return
    if msg.content_type == 'text':
        try:
            store = get_chat_store(chat_id)
            fwd_wait = store.get('forward_copy_edit_wait') or {}
            if fwd_wait.get('type') == 'forward_copy_edit':
                _durable_note_source_consumed('forward_copy_edit_wait')
                dst_msg_id = int(fwd_wait.get('dst_msg_id'))
                text = (msg.text or '').strip()
                if not edit_forward_copy_and_record(chat_id, dst_msg_id, text):
                    send_and_auto_delete(chat_id, '❌ Неверный формат или бот-копия не найдена. Пример: 1500 продукты', 10)
                    return
                _edited_rec = find_record_by_message_id(int(chat_id), int(dst_msg_id))
                if isinstance(_edited_rec, dict):
                    _durable_note_record_edit_witness(_durable_record_edit_witness(int(chat_id), int(_edited_rec.get('id')), amount=_edited_rec.get('amount', 0), note=_edited_rec.get('note', ''), source_finance_text=_edited_rec.get('source_finance_text', ''), usd_amount=_edited_rec.get('usd_amount') if _edited_rec.get('usd_amount') is not None else None, usd_note=_edited_rec.get('usd_note') if _edited_rec.get('usd_amount') is not None else None, kind='forward_copy_edit'))
                clear_forward_copy_edit_wait(chat_id, delete_prompt=True)
                try:
                    bot.delete_message(chat_id, msg.message_id)
                except Exception:
                    pass
                send_and_auto_delete(chat_id, '✅ Бот-копия и финансовая запись изменены.', 8)
                return
        except Exception as e:
            log_error(f'forward_copy_edit_wait handler error: {e}')
    if msg.content_type == 'text':
        try:
            store = get_chat_store(chat_id)
            finwin_wait = store.get('finwin_edit_wait')
            if finwin_wait and finwin_wait.get('type') == 'finwin_edit':
                _durable_note_source_consumed('finwin_edit_wait')
                text = sanitize_telegram_inserted_text((msg.text or '').strip())
                target_chat_id = int(finwin_wait.get('target_chat_id'))
                rid = int(finwin_wait.get('rid'))
                day_key = finwin_wait.get('day_key') or today_key()
                owner_day_key = finwin_wait.get('owner_day_key') or today_key()
                fin_window_msg_id = finwin_wait.get('fin_window_msg_id')
                usd_mode = bool(finwin_wait.get('usd_mode')) or usd_transactions_view_enabled(target_chat_id)
                try:
                    if usd_mode:
                        amount, note = parse_usd_edit_value(text)
                    else:
                        amount, note = split_amount_and_note(text)
                except Exception:
                    example = '100 USD продукты' if usd_mode else '1500 продукты'
                    send_and_auto_delete(chat_id, f'❌ Неверный формат. Пример: {example}', 10)
                    return
                if usd_mode:
                    target_store = get_chat_store(target_chat_id)
                    rec = next((r for r in target_store.get('records', []) if int(r.get('id', -1)) == rid), None)
                    ok = bool(rec is not None and callable(globals().get('apply_linked_finance_edit_v262')) and apply_linked_finance_edit_v262(
                        target_chat_id, rec, update_ars=False, replace_usd=True, usd_amount=float(amount),
                        usd_note=str(note or rec.get('usd_note') or rec.get('note') or ''),
                        usd_only=bool(rec.get('usd_only', False) and (not float(rec.get('amount', 0) or 0))),
                        source_text=None, full_text_replace=False, repaint_copies=True, source_kind='finwin_edit_usd'))
                else:
                    ok = update_record_in_chat(target_chat_id, rid, amount, note, source_finance_text=text)
                if ok:
                    if usd_mode:
                        _durable_note_record_edit_witness(_durable_record_edit_witness(target_chat_id, rid, usd_amount=amount, usd_note=note, kind='finwin_edit_usd'))
                    else:
                        _durable_note_record_edit_witness(_durable_record_edit_witness(target_chat_id, rid, amount=amount, note=note, source_finance_text=text, kind='finwin_edit'))
                clear_finwin_edit_wait_state(chat_id, delete_prompt=True)
                try:
                    bot.delete_message(chat_id, msg.message_id)
                except Exception:
                    pass
                if not ok:
                    send_and_auto_delete(chat_id, '❌ Запись для редактирования не найдена.', 10)
                    return
                if fin_window_msg_id:
                    try:
                        edit_kb = build_usd_edit_records_keyboard(day_key, target_chat_id, prefix='fv', owner_day_key=owner_day_key) if usd_mode else build_edit_records_keyboard(day_key, target_chat_id, prefix='fv', owner_day_key=owner_day_key)
                        bot.edit_message_text(render_fin_window_text(target_chat_id, day_key), chat_id=chat_id, message_id=int(fin_window_msg_id), reply_markup=edit_kb, parse_mode='HTML')
                    except Exception as e:
                        log_error(f'finwin edit refresh failed: {e}')
                schedule_finalize(target_chat_id, day_key, delay=0.1)
                if usd_mode:
                    send_and_auto_delete(chat_id, f'✅ USD-запись обновлена: {fmt_num_plain(amount)} USD {note}', 8)
                else:
                    send_and_auto_delete(chat_id, f'✅ Запись обновлена: {fmt_num(amount)} {note}', 8)
                return
        except Exception as e:
            log_error(f'finwin_edit_wait handler error: {e}')
    if msg.content_type == 'text':
        try:
            store = get_chat_store(chat_id)
            edit_wait = store.get('edit_wait')
            if edit_wait and edit_wait.get('type') == 'edit':
                _durable_note_source_consumed('edit_wait')
                text = sanitize_telegram_inserted_text((msg.text or '').strip())
                if not text:
                    return
                try:
                    amount, note = split_amount_and_note(text)
                except Exception:
                    send_and_auto_delete(chat_id, '❌ Неверный формат.\nПример: 1500 продукты', 10)
                    return
                rid = edit_wait.get('rid')
                day_key = edit_wait.get('day_key') or store.get('current_view_day') or today_key()
                target = next((r for r in store.get('records', []) if r.get('id') == rid), None)
                if not target:
                    store['edit_wait'] = None
                    save_data(data)
                    send_and_auto_delete(chat_id, '❌ Запись для редактирования не найдена.', 10)
                    return
                ok = update_record_in_chat(chat_id, int(rid), amount, note, source_finance_text=text)
                if not ok:
                    send_and_auto_delete(chat_id, '❌ Запись для редактирования не найдена.', 10)
                    return
                _durable_note_record_edit_witness(_durable_record_edit_witness(chat_id, int(rid), amount=amount, note=note, source_finance_text=text, kind='edit_wait'))
                clear_edit_wait_state(chat_id)
                send_and_auto_delete(chat_id, f'✅ Запись R{rid} обновлена: {fmt_num(amount)} {note}', 10)
                try:
                    bot.delete_message(chat_id, msg.message_id)
                except Exception:
                    pass
                return
        except Exception as e:
            log_error(f'edit_wait handler error: {e}')
    if msg.content_type == 'text':
        try:
            if is_finance_mode(chat_id):
                handle_finance_text(msg)
        except Exception as e:
            log_error(f'handle_finance_text error: {e}')
    schedule_forward_any_message(chat_id, msg)

def _parse_explicit_usd_operations(text: str) -> list[dict]:
    """Извлекает явные суммы вида 300 USD / +1700 USD / USD 500 / US$ 500."""
    raw = str(text or '')
    patterns = [re.compile('(?P<num>[+-]?(?:\\d{1,3}(?:[ .]\\d{3})+|\\d+)(?:[.,]\\d+)?)\\s*(?P<cur>USD|U\\$S|US\\$)', re.I), re.compile('(?P<cur>USD|U\\$S|US\\$)\\s*(?P<num>[+-]?(?:\\d{1,3}(?:[ .]\\d{3})+|\\d+)(?:[.,]\\d+)?)', re.I)]
    found = []
    occupied = []
    for pat in patterns:
        for m in pat.finditer(raw):
            span = m.span()
            if any((not (span[1] <= a or span[0] >= b) for a, b in occupied)):
                continue
            try:
                amount = parse_amount(m.group('num'))
            except Exception:
                continue
            found.append({'amount': float(amount), 'span': span, 'raw': m.group(0)})
            occupied.append(span)
    found.sort(key=lambda x: x['span'][0])
    return found

def _text_without_spans(text: str, spans: list[tuple[int, int]]) -> str:
    chars = list(str(text or ''))
    for a, b in spans:
        for i in range(max(0, a), min(len(chars), b)):
            chars[i] = ' '
    return re.sub('\\s+', ' ', ''.join(chars)).strip()

def _base_add_currency_record(chat_id: int, ledger: str, amount: float, note: str, owner: int, source_msg=None, day_key: str | None=None):
    """Добавляет запись в ARS или USD, даже если этот контур сейчас не открыт на экране."""
    chat_id = int(chat_id)
    if globals().get('constitution_finance_write_blocked_v232') and constitution_finance_write_blocked_v232():
        raise RuntimeError('DATA CONSTITUTION: финансовые изменения заблокированы до восстановления целостности')
    ledger = 'usd' if str(ledger).lower() == 'usd' else 'ars'
    store = get_chat_store(chat_id)
    active = _ensure_currency_ledgers(store)
    if active == ledger:
        add_record_to_chat(chat_id, amount, note, owner, source_msg=source_msg, day_key=day_key)
        return
    if not day_key:
        day_key = day_key_from_message(source_msg)
    records_key = f'{ledger}_records'
    daily_key = f'{ledger}_daily_records'
    next_key = f'{ledger}_next_id'
    balance_key = f'{ledger}_balance'
    records = store.setdefault(records_key, [])
    daily = store.setdefault(daily_key, {})
    rid = int(store.get(next_key, 1) or 1)
    op_id = operation_begin('finance_add', chat_id, target=f'{ledger}:{rid}', payload={'amount': amount, 'note': note, 'currency': ledger}, critical=True) if 'operation_begin' in globals() else ''
    source_msg_id = getattr(source_msg, 'message_id', None) if source_msg else None
    source_order_msg_id = getattr(source_msg, 'source_order_msg_id', None) or getattr(source_msg, 'forward_source_msg_id', None) or source_msg_id
    rec = {'id': rid, 'short_id': '', 'timestamp': message_timestamp_iso(source_msg), 'amount': float(amount), 'note': str(note or '').strip().lower(), 'source_msg_id': source_msg_id, 'source_order_msg_id': source_order_msg_id, 'owner': owner, 'msg_id': source_msg_id, 'origin_msg_id': source_msg_id, 'day_key': day_key, 'currency': ledger.upper()}
    records.append(rec)
    records.sort(key=record_sort_key)
    store[next_key] = max([int(r.get('id', 0) or 0) for r in records] + [0]) + 1
    rebuilt = {}
    for r in records:
        rebuilt.setdefault(_record_day_key(r), []).append(r)
    store[daily_key] = rebuilt
    store[balance_key] = sum((float(r.get('amount', 0) or 0) for r in records))
    try:
        finance_cache_invalidate(chat_id, f'finance_add_{ledger}')
        finance_integrity_append(chat_id, 'add', rec, details={'currency': ledger})
    except Exception as _integrity_exc:
        log_error(f'finance currency add integrity: {_integrity_exc}')
    if op_id and 'operation_complete' in globals():
        operation_complete(op_id, f'record={rid} currency={ledger}')

def handle_finance_text(msg):
    """
    Обработка обычного ввода для финучёта.
    Теперь принимает сумму не только из text, но и из caption
    у фото/видео/документов/аудио и т.п.
    """
    chat_id = msg.chat.id
    if globals().get('constitution_finance_write_blocked_v232') and constitution_finance_write_blocked_v232():
        try:
            if _v198_primary_owner_chat(chat_id):
                send_and_auto_delete(chat_id, '🚨 DATA CONSTITUTION: финансовая запись временно отложена до проверки/восстановления. После снятия карантина Durable Tasks попробует безопасно завершить её. /data_constitution', 20)
            else:
                send_owner_technical_alert('🚨 DATA CONSTITUTION: финансовая запись временно отложена до проверки/восстановления. После снятия карантина Durable Tasks попробует безопасно завершить её. /data_constitution', 20, source_chat_id=chat_id)
                send_plain_and_auto_delete(chat_id, '⏳ Финансовая запись временно отложена до восстановления данных.', 8)
        except Exception:
            pass
        return True
    try:
        uid = int(getattr(getattr(msg, 'from_user', None), 'id', 0) or 0)
        if 'safety_profile_new_enabled' in globals() and safety_profile_new_enabled() and (not security_user_allowed(uid, 'finance_input')):
            send_and_auto_delete(chat_id, '⛔ У вас нет права добавлять финансовые записи.', 8)
            try:
                bot_journal('security_finance_input_blocked', chat_id, f'user={uid}', 'WARN')
            except Exception:
                pass
            return True
    except Exception:
        pass
    try:
        uid = int(getattr(getattr(msg, 'from_user', None), 'id', 0) or 0)
        if 'v152_chat_permission_allowed' in globals() and '_v152_actor_is_platform_owner' in globals():
            capability = 'finance.usd' if 'usd_transactions_view_enabled' in globals() and usd_transactions_view_enabled(chat_id) else 'finance.ars'
            if not _v152_actor_is_platform_owner(uid) and (not v152_chat_permission_allowed(chat_id, 'finance.mode') or not v152_chat_permission_allowed(chat_id, capability)):
                try:
                    send_and_auto_delete(chat_id, '⛔ Добавление финансовых операций запрещено правами этого чата.', 8)
                except Exception:
                    pass
                return True
    except Exception:
        pass
    bot_journal('finance_text_start', chat_id, describe_msg_for_log(msg))
    text = _message_text_for_finance(msg)
    if not text:
        return False
    if not is_finance_mode(chat_id):
        return False
    store = get_chat_store(chat_id)
    settings = store.get('settings', {})
    if not settings.get('auto_add', True):
        return False
    if not looks_like_amount(text):
        if text_has_any_digit(text):
            log_error(f'[FINANCE SKIP] amount not recognized: {describe_msg_for_log(msg)} text={text[:220]!r}')
        return False
    try:
        comp = parse_financial_components(text)
        amount, note = (comp['amount'], comp['note'])
    except Exception as e:
        log_error(f'[FINANCE PARSE ERROR] {describe_msg_for_log(msg)} text={text[:220]!r}: {e}')
        return False
    careful_forward = bool(careful_restore_active(chat_id))
    if careful_forward:
        try:
            fn = globals().get('canonical_main_day')
            entry_day = str(fn(chat_id) if callable(fn) else store.get('current_view_day') or finance_today_key(chat_id))[:10]
        except Exception:
            entry_day = str(store.get('current_view_day') or finance_today_key(chat_id))[:10]
        try:
            bot_journal('careful_restore_route', chat_id, f"msg={getattr(msg, 'message_id', 0)} day={entry_day}", 'INFO')
        except Exception:
            pass
    else:
        entry_day = finance_day_key_from_message(msg)
    try:
        rec = add_record_to_chat(chat_id, amount, note, getattr(getattr(msg, 'from_user', None), 'id', 0), source_msg=msg, day_key=entry_day, usd_amount=comp.get('usd_amount'), usd_note=comp.get('usd_note', ''), usd_only=comp.get('usd_only', False), source_finance_text=comp.get('source_finance_text', text))
        if careful_forward:
            careful_restore_touch_value(chat_id, entry_day, msg=msg, record=rec)
        schedule_finalize(chat_id, entry_day)
        return True
    except Exception as e:
        log_error(f'[FINANCE ADD ERROR] {describe_msg_for_log(msg)} amount={amount} note={note!r}: {e}')
        return False

def handle_finance_edit(msg):
    chat_id = msg.chat.id
    try:
        uid = int(getattr(getattr(msg, 'from_user', None), 'id', 0) or 0)
        if 'v152_chat_permission_allowed' in globals() and '_v152_actor_is_platform_owner' in globals():
            if not _v152_actor_is_platform_owner(uid) and (not v152_chat_permission_allowed(chat_id, 'finance.edit')):
                try:
                    send_and_auto_delete(chat_id, '⛔ Редактирование операций запрещено правами этого чата.', 8)
                except Exception:
                    pass
                return False
    except Exception:
        pass
    if globals().get('constitution_finance_write_blocked_v232') and constitution_finance_write_blocked_v232():
        try:
            if _v198_primary_owner_chat(chat_id):
                send_and_auto_delete(chat_id, '🚨 DATA CONSTITUTION: финансовые изменения временно заблокированы. Используйте /data_constitution.', 20)
            else:
                send_owner_technical_alert('🚨 DATA CONSTITUTION: финансовые изменения временно заблокированы. Используйте /data_constitution.', 20, source_chat_id=chat_id)
                send_plain_and_auto_delete(chat_id, '⏳ Финансовая запись временно отложена до восстановления данных.', 8)
        except Exception:
            pass
        return True
    text = (msg.text or msg.caption or '').strip()
    store = get_chat_store(chat_id)
    target = find_record_by_message_id(chat_id, int(msg.message_id)) if 'find_record_by_message_id' in globals() else None
    if target is None:
        for r in store.get('records', []):
            try:
                if any(int(r.get(k) or 0) == int(msg.message_id) for k in ('source_msg_id','origin_msg_id','msg_id','source_order_msg_id')):
                    target = r
                    break
            except Exception:
                continue
    if isinstance(target, dict) and '_remember_finance_source_identity_v257' in globals():
        _remember_finance_source_identity_v257(int(chat_id), target, int(msg.message_id), 'records')
    if not target:
        log_info(f'[EDIT-FIN] record not found for msg_id={msg.message_id}')
        return False
    if text and looks_like_amount(text):
        try:
            comp = parse_financial_components(text)
            amount, note = (comp['amount'], comp['note'])
        except Exception:
            comp = {'usd_amount': 0.0, 'usd_note': '', 'usd_only': False}
            amount, note = (0, 'удалено')
    else:
        comp = {'usd_amount': 0.0, 'usd_note': '', 'usd_only': False}
        amount, note = (0, 'удалено')
    _constitution_before = copy.deepcopy(target)
    _next_source_text = str(comp.get('source_finance_text') or text)
    _next_usd_amount = float(comp.get('usd_amount') or 0) if comp.get('usd_amount') is not None else 0.0
    _next_usd_note = str(comp.get('usd_note') or '') if comp.get('usd_amount') is not None else ''
    _next_usd_only = bool(comp.get('usd_only', False)) if comp.get('usd_amount') is not None else False
    _same_edit = (
        float(target.get('amount') or 0) == float(amount or 0)
        and str(target.get('note') or '') == str(note or '')
        and str(target.get('source_finance_text') or '') == _next_source_text
        and float(target.get('usd_amount') or 0) == _next_usd_amount
        and str(target.get('usd_note') or '') == _next_usd_note
        and bool(target.get('usd_only', False)) == _next_usd_only
    )
    if _same_edit:
        log_info(f"[EDIT-FIN] no-op duplicate R{target.get('id')} ARS={float(amount or 0)} USD={_next_usd_amount} note={note}")
        return True
    target['amount'] = amount
    target['note'] = note
    target['source_finance_text'] = _next_source_text
    if comp.get('usd_amount') is not None:
        target['usd_amount'] = float(comp.get('usd_amount') or 0)
        target['usd_note'] = str(comp.get('usd_note') or '')
        target['usd_only'] = bool(comp.get('usd_only', False))
    elif target.get('usd_amount') is not None:
        target['usd_amount'] = 0.0
        target['usd_note'] = ''
        target['usd_only'] = False
    for day, arr in store.get('daily_records', {}).items():
        for r in arr:
            if r.get('id') == target.get('id'):
                r.update(target)
    store['balance'] = sum((r['amount'] for r in store.get('records', [])))
    _snapshot_active_currency_ledger(store, _ensure_currency_ledgers(store))
    log_info(f"[EDIT-FIN] updated record R{target['id']} ARS={float(amount or 0)} USD={float(target.get('usd_amount') or 0)} usd_only={bool(target.get('usd_only', False))} note={note}")
    save_data(data, chat_ids=[int(chat_id)])
    try:
        finance_integrity_append(int(chat_id), 'edit', target, details={'before': _constitution_before, 'source': 'telegram_edited_message'})
    except Exception as _constitution_edit_exc:
        log_error(f'DATA CONSTITUTION edited finance ledger: {_constitution_edit_exc}')
    return True

def sync_forwarded_finance_message(dst_chat_id: int, dst_msg_id: int, text: str, owner: int=0, source_msg=None):
    dst_chat_id = int(dst_chat_id); dst_msg_id = int(dst_msg_id)
    with locked_chat(dst_chat_id):
        if not is_finance_mode(dst_chat_id):
            if text_has_any_digit(text):
                log_error(f'[FWD FINANCE SKIP] finance mode off: dst={get_chat_display_name(dst_chat_id)} msg={dst_msg_id} text={str(text)[:220]!r}')
            return False
        store = get_chat_store(dst_chat_id)
        finder = globals().get('_v260_find_forward_finance_record')
        existing = finder(dst_chat_id, dst_msg_id, source_msg) if callable(finder) else (find_record_by_message_id(dst_chat_id, dst_msg_id) if 'find_record_by_message_id' in globals() else None)
        entry_day = finance_day_key_from_message(source_msg) if source_msg is not None else finance_today_key()
        changed = False
        before = copy.deepcopy(existing) if isinstance(existing, dict) else None
        result_rec = existing
        if text and looks_like_amount(text):
            try:
                comp = parse_financial_components(text)
                amount, note = (comp['amount'], comp['note'])
            except Exception as e:
                log_error(f'[FWD FINANCE PARSE ERROR] dst={get_chat_display_name(dst_chat_id)} msg={dst_msg_id} text={str(text)[:220]!r}: {e}')
                return False
            try:
                if isinstance(existing, dict):
                    next_usd = float(comp.get('usd_amount') or 0) if comp.get('usd_amount') is not None else 0.0
                    next_usd_note = str(comp.get('usd_note') or '') if comp.get('usd_amount') is not None else ''
                    next_usd_only = bool(comp.get('usd_only', False)) if comp.get('usd_amount') is not None else False
                    next_text = str(comp.get('source_finance_text') or text)
                    changed = not (
                        float(existing.get('amount') or 0) == float(amount or 0)
                        and str(existing.get('note') or '') == str(note or '')
                        and str(existing.get('source_finance_text') or '') == next_text
                        and float(existing.get('usd_amount') or 0) == next_usd
                        and str(existing.get('usd_note') or '') == next_usd_note
                        and bool(existing.get('usd_only', False)) == next_usd_only
                    )
                    if changed:
                        existing['amount'] = amount
                        existing['note'] = note
                        existing['source_finance_text'] = next_text
                        existing['usd_amount'] = next_usd
                        existing['usd_note'] = next_usd_note
                        existing['usd_only'] = next_usd_only
                        existing['timestamp'] = message_timestamp_iso(source_msg)
                    entry_day = existing.get('day_key') or entry_day
                    result_rec = existing
                else:
                    shadow_msg = None
                    if source_msg is not None and callable(globals().get('_v260_make_forward_shadow')):
                        try:
                            src_chat = int(getattr(getattr(source_msg, 'chat', None), 'id', 0) or 0)
                            src_mid = int(getattr(source_msg, 'forward_source_msg_id', 0) or getattr(source_msg, 'message_id', 0) or 0)
                            shadow_msg = _v260_make_forward_shadow(src_chat, src_mid, dst_chat_id, dst_msg_id, owner, getattr(source_msg, 'date', None))
                        except Exception:
                            shadow_msg = None
                    if shadow_msg is None:
                        shadow_msg = type('ForwardShadowMsg', (), {'message_id': dst_msg_id, 'date': getattr(source_msg, 'date', int(time.time())) if source_msg is not None else int(time.time()), 'forward_source_msg_id': getattr(source_msg, 'message_id', dst_msg_id) if source_msg is not None else dst_msg_id})()
                    result_rec = add_record_to_chat(dst_chat_id, amount, note, owner, source_msg=shadow_msg, day_key=entry_day, usd_amount=comp.get('usd_amount'), usd_note=comp.get('usd_note', ''), usd_only=comp.get('usd_only', False), source_finance_text=comp.get('source_finance_text', text))
                    changed = True
                if isinstance(result_rec, dict) and callable(globals().get('_v260_bind_forward_finance_record')) and source_msg is not None:
                    _v260_bind_forward_finance_record(result_rec, source_msg, dst_chat_id, dst_msg_id)
                if isinstance(result_rec, dict):
                    # R7: add_record_to_chat already normalized and committed locally.
                    helper = globals().get('_r7_rebuild_month_short_ids_after_normalize')
                    if callable(helper): helper(dst_chat_id, store)
                    else: rebuild_month_short_ids(dst_chat_id)
                    store['balance'] = sum((float(r.get('amount', 0) or 0) for r in store.get('records', [])))
            except Exception as e:
                log_error(f'[FWD FINANCE ADD ERROR] dst={get_chat_display_name(dst_chat_id)} msg={dst_msg_id} amount={amount} note={note!r}: {e}')
                return False
        elif isinstance(existing, dict):
            changed = not (float(existing.get('amount') or 0) == 0.0 and str(existing.get('note') or '') == 'удалено' and float(existing.get('usd_amount') or 0) == 0.0)
            if changed:
                existing['amount'] = 0
                existing['note'] = 'удалено'
                existing['source_finance_text'] = str(text or '').strip()
                existing['usd_amount'] = 0.0
                existing['usd_note'] = ''
                existing['usd_only'] = False
            entry_day = existing.get('day_key') or entry_day
            result_rec = existing
            # R7: amount/note replacement does not reorder records.
            store['balance'] = sum((float(r.get('amount', 0) or 0) for r in store.get('records', [])))
        else:
            if text_has_any_digit(text):
                log_error(f'[FWD FINANCE SKIP] amount not recognized: dst={get_chat_display_name(dst_chat_id)} msg={dst_msg_id} text={str(text)[:220]!r}')
            return False
        _snapshot_active_currency_ledger(store, _ensure_currency_ledgers(store))
        try:
            for _ledger, _rec in _finance_record_lists(int(dst_chat_id)):
                if isinstance(_rec, dict): ensure_finance_record_uid(int(dst_chat_id), _rec)
        except Exception:
            pass
        if 'persist_finance_chat_local_fast' in globals() and (not persist_finance_chat_local_fast(dst_chat_id)):
            log_error(f'[FWD FINANCE LOCAL PERSIST FAILED] dst={get_chat_display_name(dst_chat_id)} msg={dst_msg_id}')
            return False
        if changed and before is not None and isinstance(result_rec, dict):
            try:
                finance_integrity_append(dst_chat_id, 'edit', result_rec, details={'before': before, 'source': 'forwarded_edited_message_v260'})
            except Exception as exc:
                log_error(f'[FWD FIN V260] integrity edit: {exc}')
    if not isinstance(result_rec, dict):
        result_rec = find_record_by_message_id(dst_chat_id, dst_msg_id)
    try: refresh_active_forward_copy_edit_prompt(dst_chat_id, dst_msg_id, result_rec)
    except Exception: pass
    try: schedule_financial_window_refresh(dst_chat_id, str(entry_day), reason='forward_finance_exact_once_v260')
    except Exception: pass
    schedule_finalize(dst_chat_id, entry_day)
    return result_rec if isinstance(result_rec, dict) else False

def export_global_csv(d: dict):
    """Legacy global CSV with all chats (for backup channel), date DD:MM:YY."""
    try:
        with open(CSV_FILE, 'w', newline='', encoding='utf-8') as f:
            w = csv.writer(f)
            w.writerow(['date', 'amount', 'note'])
            rows = []
            for cid, cdata in d.get('chats', {}).items():
                for dk, records in (cdata.get('daily_records', {}) or {}).items():
                    for r in records or []:
                        rows.append((fmt_date_table(dk), fmt_csv_amount(r.get('amount')), r.get('note', '')))
            rows.sort(key=lambda row: str(row[0]))
            write_csv_rows_with_day_gaps(w, rows, 3)
    except Exception as e:
        log_error(f'export_global_csv: {e}')
EMOJI_DIGITS = {'0': '0️⃣', '1': '1️⃣', '2': '2️⃣', '3': '3️⃣', '4': '4️⃣', '5': '5️⃣', '6': '6️⃣', '7': '7️⃣', '8': '8️⃣', '9': '9️⃣'}
backup_channel_notified_chats = set()

def format_chat_id_emoji(chat_id: int) -> str:
    """Преобразует chat_id в emoji-цифры. Роль владельца не подменяет идентичность чата."""
    return ''.join((EMOJI_DIGITS.get(ch, ch) for ch in str(chat_id)))

def _safe_chat_title_for_filename(title) -> str:
    """Делает короткое безопасное имя чата для имени файла."""
    if not title:
        return ''
    title = str(title).strip()
    title = title.replace(' ', '_')
    title = re.sub('[^0-9A-Za-zА-Яа-я_\\-]+', '', title)
    return title[:32]

def get_chat_name_for_filename(chat_id: int) -> str:
    """
    Выбор имени для файла:
        1) username
        2) title (имя чата)
        3) chat_id
    Всё преобразуется в короткое безопасное имя.
    """
    try:
        store = get_chat_store(chat_id)
        info = store.get('info', {})
        username = info.get('username')
        title = info.get('title')
        if title:
            base = title
        elif username:
            base = username.lstrip('@')
        else:
            base = str(chat_id)
        return _safe_chat_title_for_filename(base)
    except Exception as e:
        log_error(f'get_chat_name_for_filename({chat_id}): {e}')
        return _safe_chat_title_for_filename(str(chat_id))

def _safe_export_name_part(value, fallback: str='chat') -> str:
    try:
        value = str(value or '').strip()
    except Exception:
        value = ''
    if not value:
        value = fallback
    value = value.replace(' ', '_')
    value = re.sub('[^0-9A-Za-zА-Яа-я_@.\\-]+', '', value)
    value = value.strip('._-')
    return (value or fallback)[:70]

def export_period_date_label(mode: str, day_key: str) -> str:
    """Дата/период для имени экспортируемого файла: _(03.06.26-04.06.26)."""
    mode = str(mode or 'all').replace('csv_', '').replace('xlsx_', '')
    if mode == 'all_real':
        mode = 'all'

    def _d(dk: str) -> str:
        return fmt_date_backup(dk).replace(':', '.')
    try:
        if mode == 'day':
            return f'({_d(day_key)})'
        if mode == 'week':
            base = datetime.strptime(day_key, '%Y-%m-%d')
            start = base - timedelta(days=6)
            return f"({_d(start.strftime('%Y-%m-%d'))}-{_d(day_key)})"
        if mode == 'month':
            base = datetime.strptime(day_key, '%Y-%m-%d')
            start = base.replace(day=1)
            return f"({_d(start.strftime('%Y-%m-%d'))}-{_d(day_key)})"
        if mode == 'wedthu':
            base = datetime.strptime(day_key, '%Y-%m-%d')
            start = base - timedelta(days=(base.weekday() - 3) % 7)
            end = start + timedelta(days=6)
            return f"({_d(start.strftime('%Y-%m-%d'))}-{_d(end.strftime('%Y-%m-%d'))})"
    except Exception:
        pass
    return '(all)'

def export_display_filename(chat_id: int, mode: str, day_key: str, ext: str) -> str:
    """Имя файла для CSV/Excel: имя_чата + дата/период файла."""
    chat_name = _safe_export_name_part(get_chat_name_for_filename(chat_id) or get_chat_display_name(chat_id), f'chat_{chat_id}')
    date_part = export_period_date_label(mode, day_key)
    ext = str(ext or 'csv').lower().lstrip('.')
    return f'{chat_name}_{date_part}.{ext}'

def file_bytesio_named(path: str, file_name: str) -> io.BytesIO | None:
    try:
        with open(path, 'rb') as f:
            payload = f.read()
        if not payload:
            return None
        buf = io.BytesIO(payload)
        buf.name = file_name
        buf.seek(0)
        return buf
    except Exception as e:
        log_error(f'file_bytesio_named({path}): {e}')
        return None

def _get_chat_title_for_backup(chat_id: int) -> str:
    """Always derive the Telegram filename from the chat's current stored name."""
    try:
        current_name = get_chat_name_for_filename(chat_id)
        if current_name:
            return current_name
    except Exception as e:
        log_error(f'_get_chat_title_for_backup({chat_id}): {e}')
    return f'chat_{chat_id}'

def send_backup_to_channel_for_file(base_path: str, meta_key_prefix: str, chat_title: str=None):
    """One logical backup file = one Telegram message slot.

    v236 stores message_id/file_id in the pinned Telegram HEAD, not only in
    Render-local csv_meta.json. Repeated backups edit the same channel message.
    If that message was manually deleted, edit fails, the slot is recreated once,
    and the new message_id is committed to HEAD for future edits.
    """
    if not BACKUP_CHAT_ID:
        return
    if not bool(globals().get('telegram_durable_primary_v234', lambda: False)()):
        return
    if not os.path.exists(base_path):
        log_error(f'send_backup_to_channel_for_file: {base_path} not found')
        return
    try:
        meta = _load_csv_meta()
        msg_key = f'msg_{meta_key_prefix}'
        ts_key = f'timestamp_{meta_key_prefix}'
        base_name = os.path.basename(base_path)
        name_without_ext, dot, ext = base_name.partition('.')
        safe_title = _safe_chat_title_for_filename(chat_title)
        file_name = safe_title + (f'.{ext}' if dot else '') if safe_title else base_name
        caption = f"📦 {file_name} — {now_local().strftime('%Y-%m-%d %H:%M')}"
        with open(base_path, 'rb') as src:
            raw = src.read()
        if not raw:
            log_error(f'send_backup_to_channel_for_file: {base_path} is empty, skip')
            return
        stable = globals().get('telegram_stable_document_upsert_v236')
        if callable(stable) and bool(globals().get('telegram_durable_configured_v234', lambda: False)()):
            row = stable(raw, file_name, caption, slot_key=f'chat_backup:{meta_key_prefix}', preferred_message_id=int(meta.get(msg_key) or 0) or None, persist_head=True, reason=f'chat_backup:{meta_key_prefix}')
            meta[msg_key] = int((row or {}).get('message_id') or 0)
            meta[ts_key] = now_local().isoformat(timespec='seconds')
            _save_csv_meta(meta)
            log_info(f'[BACKUP] stable slot updated: {base_path} mid={meta[msg_key]}')
            return

        def _open_for_telegram():
            buf = io.BytesIO(raw)
            buf.name = file_name
            buf.seek(0)
            return buf
        sent = False
        if meta.get(msg_key):
            try:
                _tg_call_retry(bot.edit_message_media, chat_id=int(BACKUP_CHAT_ID), message_id=meta[msg_key], media=types.InputMediaDocument(media=_open_for_telegram(), caption=caption), purpose='backup_channel_edit_message_media')
                sent = True
            except Exception as exc:
                log_error(f'[BACKUP] edit failed, will recreate: {exc}')
        if not sent:
            sent_msg = _tg_call_retry(bot.send_document, int(BACKUP_CHAT_ID), _open_for_telegram(), caption=caption, purpose='backup_channel_send_document')
            meta[msg_key] = sent_msg.message_id
        meta[ts_key] = now_local().isoformat(timespec='seconds')
        _save_csv_meta(meta)
    except Exception as e:
        log_error(f'send_backup_to_channel_for_file({base_path}): {e}')

def send_backup_to_channel(chat_id: int, ensure_files: bool=True):
    bot_journal('backup_to_channel_start', chat_id, 'send_backup_to_channel')
    if not bool(globals().get('telegram_durable_primary_v234', lambda: False)()):
        return
    if not is_backup_to_channel_enabled(chat_id):
        return
    '\n    Общий бэкап файлов чата в BACKUP_CHAT_ID.\n    Делает:\n    • проверку флага backup_flags["channel"]\n    • один раз (на первый бэкап чата) отправляет chat_id эмодзи в канал\n    • обновляет/создаёт в канале только:\n        - data_<chat_id>.json\n        - data_<chat_id>.xlsx\n      CSV в backup-канал больше не отправляется.\n    '
    try:
        if not BACKUP_CHAT_ID:
            return
        if not backup_flags.get('channel', True):
            log_info('send_backup_to_channel: channel backup disabled by flag.')
            return
        try:
            backup_chat_id = int(BACKUP_CHAT_ID)
        except Exception:
            log_error('send_backup_to_channel: BACKUP_CHAT_ID не является числом.')
            return
        if ensure_files:
            save_chat_json(chat_id)
        chat_title = _get_chat_title_for_backup(chat_id)
        meta = _load_csv_meta()
        notify_key = f'emoji_notified_{chat_id}'
        markers_enabled = str(os.getenv('BACKUP_CHAT_MARKERS_ENABLED', '0') or '0').strip().casefold() in {'1', 'true', 'yes', 'on', 'вкл'}
        if markers_enabled and (not meta.get(notify_key)):
            try:
                emoji_id = format_chat_id_emoji(chat_id)
                _tg_call_retry(bot.send_message, backup_chat_id, emoji_id, purpose='backup_channel_send_chat_marker')
                backup_channel_notified_chats.add(chat_id)
                meta[notify_key] = True
                _save_csv_meta(meta)
            except Exception as e:
                log_error(f'send_backup_to_channel: не удалось отправить emoji chat_id в канал: {e}')
        json_path = chat_json_file(chat_id)
        xlsx_path = chat_xlsx_file(chat_id)
        send_backup_to_channel_for_file(json_path, f'json_{chat_id}', chat_title)
        if backup_excel_all_enabled(chat_id) and os.path.exists(xlsx_path):
            send_backup_to_channel_for_file(xlsx_path, f'xlsx_{chat_id}', chat_title)
    except Exception as e:
        log_error(f'send_backup_to_channel({chat_id}): {e}')

def _owner_data_file() -> str | None:
    """Legacy JSON snapshot file for owner-compatible backups."""
    if not OWNER_ID:
        return None
    try:
        return f'data_{int(OWNER_ID)}.json'
    except Exception:
        return None
# v262
