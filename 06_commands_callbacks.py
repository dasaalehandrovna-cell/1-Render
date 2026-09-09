# v262

# --- ИСТОЧНИК: 80_callback_router.py ---
def _forward_probe_all_background(owner_chat_id: int, message_id: int):
    try:
        ok, bad = probe_all_known_chats()
        owner_store = get_chat_store(int(OWNER_ID))
        owner_day_key = owner_store.get('current_view_day', today_key())
        summary = (data.get('_global_settings', {}) or {}).get('last_chat_probe_summary_v197') or {}
        checked = int(summary.get('checked') or ok + bad)
        changed = int(summary.get('changed') or 0)
        renamed = int(summary.get('renamed') or 0)
        errors = int(summary.get('errors') or 0)
        text = build_forward_status_text(f'📡 Полная проверка чатов завершена.\nПроверено: {checked} · доступно: {ok} · нет доступа: {bad} · ошибок API: {errors}\nОбновлено карточек: {changed} · изменено имён: {renamed}\n\nНазвания, username, тип и доступные Telegram-параметры синхронизированы и сохранены.\n\nПересылка:\nВыберите чат A:')
        fast_ui_edit_message_text(int(owner_chat_id), int(message_id), text, reply_markup=build_forward_source_menu(owner_day_key), purpose='forward_probe_all_done')
    except Exception as exc:
        log_error(f'forward_probe_all_background: {exc}')
        try:
            send_owner_technical_alert('❌ Проверка чатов завершилась с ошибкой. Смотрите журнал.', 20, source_chat_id=int(owner_chat_id))
        except Exception:
            pass

def _forward_probe_one_background(owner_chat_id: int, message_id: int, target_chat_id: int):
    try:
        ok = probe_bot_in_chat(int(target_chat_id))
        status = '✅ бот снова доступен' if ok else '➖ бот удалён/нет доступа'
        owner_store = get_chat_store(int(OWNER_ID))
        owner_day_key = owner_store.get('current_view_day', today_key())
        fast_ui_edit_message_text(int(owner_chat_id), int(message_id), build_forward_status_text(f'🗑 Удалённые чаты\n{get_chat_display_name(int(target_chat_id))}: {status}'), reply_markup=build_removed_chats_menu(owner_day_key), purpose='forward_probe_one_done')
    except Exception as exc:
        log_error(f'forward_probe_one_background({target_chat_id}): {exc}')

def _chat_description_background(viewer_chat_id: int, message_id: int, target_chat_id: int, origin: str, day_key: str, page: int=0, refresh: bool=False):
    try:
        pages = get_chat_description_pages(int(target_chat_id), refresh=bool(refresh))
        total = max(1, len(pages))
        page = max(0, min(int(page or 0), total - 1))
        text = pages[page] if pages else 'ℹ️ Нет доступной информации о чате.'
        kb = build_chat_description_detail_keyboard(int(viewer_chat_id), str(origin), str(day_key), int(target_chat_id), page, total)
        fast_ui_edit_message_text(int(viewer_chat_id), int(message_id), text, reply_markup=kb, purpose='chat_description_detail')
        register_open_window(int(viewer_chat_id), int(message_id), 'chat_description', code=f'chat_desc_open:{origin}:{int(target_chat_id)}', day_key=str(day_key), params={'target_chat_id': int(target_chat_id), 'origin': str(origin), 'page': page})
    except Exception as exc:
        log_error(f'chat description background {target_chat_id}: {exc}')
        try:
            fast_ui_edit_message_text(int(viewer_chat_id), int(message_id), f'❌ Не удалось получить описание чата {get_chat_display_name(int(target_chat_id))}.\n{str(exc)[:500]}', reply_markup=build_chat_description_detail_keyboard(int(viewer_chat_id), str(origin), str(day_key), int(target_chat_id), 0, 1), purpose='chat_description_error')
        except Exception:
            pass

def on_callback(call):
    try:
        raw_data_str = call.data or ''
        data_str = resolve_short_callback(raw_data_str)
        chat_id = call.message.chat.id
        try:
            _r25_action_fn = globals().get('r25_trace_set_action')
            if callable(_r25_action_fn) and data_str is not None:
                _r25_action_fn(str(data_str))
        except Exception:
            pass
        if data_str is None:
            try:
                bot.answer_callback_query(call.id, 'Кнопка устарела. Открой меню заново.', show_alert=True)
            except Exception:
                pass
            return
        # R27 must run before feature-specific extension routers (Google/tenant/etc.),
        # otherwise their historical Back callbacks can consume the click first.
        try:
            _r27_back_fn = globals().get('r27_callback_is_back_navigation')
            if callable(_r27_back_fn) and data_str != 'nav_prev' and _r27_back_fn(call, data_str):
                if restore_previous_window(call):
                    try:
                        _r27_clean = globals().get('r27_cleanup_after_history_back')
                        if callable(_r27_clean): _r27_clean(call)
                    except Exception:
                        pass
                    return
        except Exception:
            pass
        try:
            _v149_callback = globals().get('v149_extension_callback')
            if callable(_v149_callback) and _v149_callback(call, data_str):
                return
        except Exception as e:
            log_error(f'v149 extension callback: {e}')
        try:
            if raw_data_str != data_str:
                bot_journal('button_pressed', chat_id, f'{raw_data_str} -> {str(data_str)[:500]}')
            else:
                bot_journal('button_pressed', chat_id, str(data_str)[:500])
        except Exception:
            pass
        try:
            user_id = int(getattr(getattr(call, 'from_user', None), 'id', 0) or 0)
            if 'safety_permission_allowed' in globals() and (not safety_permission_allowed(user_id, chat_id, data_str)):
                bot.answer_callback_query(call.id, 'Недостаточно прав для этого действия.', show_alert=True)
                bot_journal('permission_denied', chat_id, f'user={user_id} action={data_str}', 'WARN')
                return
        except Exception as perm_exc:
            try:
                is_owner = bool(user_id and (int(user_id) == int(OWNER_ID or 0) or int(user_id) in {int(x) for x in get_additional_owner_ids()}))
            except Exception:
                is_owner = False
            log_error(f"SECURITY_PERMISSION_ERROR user={locals().get('user_id', 0)} chat={chat_id} action={data_str}: {perm_exc}")
            if not is_owner and ('safety_profile_new_enabled' in globals() and safety_profile_new_enabled()):
                try:
                    bot.answer_callback_query(call.id, 'Проверка прав временно недоступна. Действие заблокировано.', show_alert=True)
                except Exception:
                    pass
                return
        try:
            update_chat_info_from_message(call.message)
        except Exception:
            pass
        try:
            if 'tenant_handle_callback' in globals() and tenant_handle_callback(call, data_str):
                return
        except Exception as tenant_exc:
            log_error(f'tenant callback {data_str}: {tenant_exc}')
            try:
                bot.answer_callback_query(call.id, 'Не удалось открыть пространство.', show_alert=True)
            except Exception:
                pass
            return
        try:
            touch_secret_window_timer_for_callback(chat_id, call.message.message_id, data_str)
        except Exception:
            pass
        if _callback_should_debounce(call, data_str):
            return
        # R27 universal Back: every visible Back action first restores the actual
        # previous snapshot. If history is unavailable (e.g. after an old deploy),
        # the legacy callback continues below as a safe fallback.
        try:
            _r27_back_fn = globals().get('r27_callback_is_back_navigation')
            if callable(_r27_back_fn) and data_str != 'nav_prev' and _r27_back_fn(call, data_str):
                if restore_previous_window(call):
                    try:
                        _r27_clean = globals().get('r27_cleanup_after_history_back')
                        if callable(_r27_clean): _r27_clean(call)
                    except Exception:
                        pass
                    return
        except Exception:
            pass
        try:
            update_chat_info_from_message(call.message)
        except Exception:
            pass
        if data_str not in {'nav_prev', 'aux_close', 'info_close', 'secclose', 'secmclose'} and (not str(data_str).endswith(':back_main')):
            try:
                remember_previous_window(call)
            except Exception:
                pass
        if data_str == 'nav_prev':
            if restore_previous_window(call):
                try:
                    _r27_clean = globals().get('r27_cleanup_after_history_back')
                    if callable(_r27_clean): _r27_clean(call)
                except Exception:
                    pass
                return
            return
        if data_str.startswith('chat_desc_menu:'):
            if not is_owner_chat(chat_id):
                try:
                    bot.answer_callback_query(call.id, 'Описание чатов доступно владельцу.', show_alert=True)
                except Exception:
                    pass
                return
            origin = str(data_str.split(':', 1)[1] or 'forward')
            day_key = get_chat_store(chat_id).get('current_view_day') or today_key()
            safe_edit(bot, call, build_chat_description_menu_text(), reply_markup=build_chat_description_menu(chat_id, origin, day_key))
            return
        if data_str.startswith('chat_desc_open:'):
            if not is_owner_chat(chat_id):
                return
            try:
                _, origin, target_s = data_str.split(':', 2)
                target_chat_id = int(target_s)
            except Exception:
                return
            day_key = get_chat_store(chat_id).get('current_view_day') or today_key()
            safe_edit(bot, call, f'⏳ Собираю полную информацию о чате {get_chat_display_name(target_chat_id)}…', reply_markup=build_chat_description_detail_keyboard(chat_id, origin, day_key, target_chat_id, 0, 1))
            key = f'chat-description:{chat_id}:{call.message.message_id}:{target_chat_id}'
            if not GENERAL_TASK_POOL.submit_unique(key, _chat_description_background, chat_id, call.message.message_id, target_chat_id, origin, day_key, 0, True):
                try:
                    bot.answer_callback_query(call.id, 'Описание этого чата уже собирается.')
                except Exception:
                    pass
            return
        if data_str.startswith('chat_desc_page:'):
            if not is_owner_chat(chat_id):
                return
            try:
                _, origin, target_s, page_s = data_str.split(':', 3)
                target_chat_id = int(target_s)
                page = max(0, int(page_s))
            except Exception:
                return
            day_key = get_chat_store(chat_id).get('current_view_day') or today_key()
            key = f'chat-description:{chat_id}:{call.message.message_id}:{target_chat_id}'
            GENERAL_TASK_POOL.submit_unique(key, _chat_description_background, chat_id, call.message.message_id, target_chat_id, origin, day_key, page, False)
            return
        if data_str == 'process_center':
            safe_edit(bot, call, build_process_center_text(chat_id), reply_markup=build_process_center_keyboard(chat_id))
            return
        if data_str == 'problem_tasks':
            if not is_owner_chat(chat_id):
                return
            safe_edit(bot, call, build_problem_tasks_text(), reply_markup=build_problem_tasks_keyboard(chat_id))
            return
        if data_str == 'safety_profile_open':
            if not is_owner_chat(chat_id):
                return
            safe_edit(bot, call, safety_profile_text(), reply_markup=build_safety_profile_keyboard(chat_id))
            return
        if data_str == 'safety_profile_toggle':
            if not is_owner_chat(chat_id):
                return
            mode = toggle_safety_profile_mode()
            try:
                bot.answer_callback_query(call.id, f"Защита: {('по-новому' if mode == 'new' else 'по-старому')}")
            except Exception:
                pass
            safe_edit(bot, call, safety_profile_text(), reply_markup=build_safety_profile_keyboard(chat_id))
            return
        if data_str.startswith('security_roles:'):
            if not is_owner_chat(chat_id):
                return
            try:
                page = int(data_str.split(':', 1)[1])
            except Exception:
                page = 0
            safe_edit(bot, call, build_security_roles_text(page), reply_markup=build_security_roles_keyboard(page))
            return
        if data_str.startswith('security_role_user:'):
            if not is_owner_chat(chat_id):
                return
            try:
                _p, uid_raw, page_raw = data_str.split(':', 2)
                uid, page = (int(uid_raw), int(page_raw))
            except Exception:
                return
            safe_edit(bot, call, build_security_role_user_text(uid), reply_markup=build_security_role_user_keyboard(uid, page))
            return
        if data_str.startswith('security_role_set:'):
            if not is_owner_chat(chat_id):
                return
            try:
                _p, uid_raw, role, page_raw = data_str.split(':', 3)
                uid, page = (int(uid_raw), int(page_raw))
            except Exception:
                return
            security_set_role(uid, role)
            try:
                bot.answer_callback_query(call.id, f'Роль: {security_role_label(security_role_for_user(uid))}')
            except Exception:
                pass
            safe_edit(bot, call, build_security_role_user_text(uid), reply_markup=build_security_role_user_keyboard(uid, page))
            return
        if data_str == 'integrity_status':
            if not is_owner_chat(chat_id):
                return
            safe_edit(bot, call, finance_integrity_text(), reply_markup=build_integrity_keyboard(chat_id))
            return
        if data_str == 'expense_inbox_open':
            if not is_owner_chat(chat_id):
                return
            safe_edit(bot, call, expense_inbox_text(), reply_markup=build_expense_inbox_keyboard(chat_id))
            return
        if data_str.startswith('expense_draft_open:'):
            if not is_owner_chat(chat_id):
                return
            try:
                draft_id = int(data_str.split(':', 1)[1])
            except Exception:
                return
            safe_edit(bot, call, build_expense_draft_text(draft_id), reply_markup=build_expense_draft_detail_keyboard(draft_id, chat_id))
            return
        if data_str.startswith('expense_draft_resolved:') or data_str.startswith('expense_draft_dismiss:'):
            try:
                draft_id = int(data_str.split(':', 1)[1])
            except Exception:
                return
            status = 'resolved' if data_str.startswith('expense_draft_resolved:') else 'dismissed'
            if not (is_owner_chat(chat_id) or int(((_expense_inbox_root().get('items') or {}).get(str(draft_id)) or {}).get('target_chat_id') or 0) == int(chat_id)):
                return
            expense_draft_mark(draft_id, status)
            try:
                bot.answer_callback_query(call.id, 'Отметка закрыта')
            except Exception:
                pass
            if is_owner_chat(chat_id):
                safe_edit(bot, call, expense_inbox_text(), reply_markup=build_expense_inbox_keyboard(chat_id))
            else:
                try:
                    v178_edit_reply_markup_async(chat_id, call.message.message_id, None, 'expense_close_v178')
                except Exception:
                    pass
            return
        if data_str == 'expense_evening_toggle':
            if not is_owner_chat(chat_id):
                return
            enabled = toggle_evening_reconciliation()
            try:
                bot.answer_callback_query(call.id, 'Вечерняя сверка включена' if enabled else 'Вечерняя сверка выключена')
            except Exception:
                pass
            safe_edit(bot, call, expense_inbox_text(), reply_markup=build_expense_inbox_keyboard(chat_id))
            return
        if data_str == 'expense_evening_now':
            if not is_owner_chat(chat_id):
                return
            GENERAL_TASK_POOL.submit_unique('expense-evening-now', send_evening_reconciliation, True)
            try:
                bot.answer_callback_query(call.id, 'Сверка отправляется')
            except Exception:
                pass
            return
        if data_str == 'expense_evening_done':
            if not is_owner_chat(chat_id):
                return
            try:
                safe_edit(bot, call, '✅ Вечерняя сверка завершена. Все расходы внесены.')
            except Exception:
                pass
            return
        if data_str == 'expense_quick_buttons_toggle':
            if not is_owner_chat(chat_id):
                return
            enabled = toggle_expense_quick_buttons()
            GENERAL_TASK_POOL.submit_unique('expense-recent-migration-refresh', migrate_recent_expense_shortcut_events, 2, True)
            try:
                bot.answer_callback_query(call.id, 'Кнопки быстрых отметок включены' if enabled else 'Кнопки быстрых отметок убраны')
            except Exception:
                pass
            current_text = str(getattr(getattr(call, 'message', None), 'text', '') or '')
            if 'Быстрый расход' in current_text:
                safe_edit(bot, call, build_expense_shortcut_text(chat_id), reply_markup=build_expense_shortcut_keyboard(chat_id), parse_mode='HTML')
            else:
                day = get_chat_store(chat_id).get('current_view_day') or today_key()
                safe_edit(bot, call, build_info_text(chat_id, day), reply_markup=build_info_keyboard(chat_id))
            return
        if data_str == 'reminder_ui_mode_toggle':
            if not is_owner_chat(chat_id):
                return
            mode = toggle_reminder_ui_mode()
            try:
                bot.answer_callback_query(call.id, 'Напоминалка по-новому' if mode == 'new' else 'Напоминалка по-старому')
            except Exception:
                pass
            day = get_chat_store(chat_id).get('current_view_day') or today_key()
            safe_edit(bot, call, build_info_text(chat_id, day), reply_markup=build_info_keyboard(chat_id))
            return
        if data_str == 'expense_shortcut_info':
            if not is_owner_chat(chat_id):
                return
            safe_edit(bot, call, build_expense_shortcut_text(chat_id), reply_markup=build_expense_shortcut_keyboard(chat_id), parse_mode='HTML')
            return
        if data_str == 'expense_shortcut_pick':
            if not is_owner_chat(chat_id):
                return
            safe_edit(bot, call, '🎯 Выберите чат, куда отправлять отметку «Был расход».', reply_markup=build_expense_shortcut_chat_menu(chat_id))
            return
        if data_str.startswith('expense_shortcut_target:'):
            if not is_owner_chat(chat_id):
                return
            try:
                target_chat_id = int(data_str.split(':', 1)[1])
            except Exception:
                return
            if answer_removed_chat(call, target_chat_id):
                return
            expense_shortcut_set_target(target_chat_id)
            safe_edit(bot, call, build_expense_shortcut_text(chat_id), reply_markup=build_expense_shortcut_keyboard(chat_id), parse_mode='HTML')
            return
        if data_str == 'expense_shortcut_send_url':
            if not is_owner_chat(chat_id):
                return
            url = expense_shortcut_url()
            if not url:
                try:
                    bot.answer_callback_query(call.id, 'APP_URL/WEBHOOK_URL не определён', show_alert=True)
                except Exception:
                    pass
                return
            try:
                bot.send_message(chat_id, f'📋 Скопируйте ссылку целиком и вставьте её в действие URL приложения «Команды»:\n\n<code>{html.escape(url)}</code>\n\nНе пересылайте эту ссылку другим людям.', parse_mode='HTML', disable_web_page_preview=True)
            except Exception as exc:
                log_error(f'expense shortcut send url: {exc}')
            return
        if data_str == 'expense_shortcut_regenerate':
            if not is_owner_chat(chat_id):
                return
            expense_shortcut_regenerate_token()
            safe_edit(bot, call, build_expense_shortcut_text(chat_id), reply_markup=build_expense_shortcut_keyboard(chat_id), parse_mode='HTML')
            try:
                bot.answer_callback_query(call.id, 'Создана новая секретная ссылка')
            except Exception:
                pass
            return
        if data_str == 'expense_shortcut_test':
            if not is_owner_chat(chat_id):
                return
            event_id, duplicate = enqueue_expense_ping_event('telegram_test', force=True)
            try:
                bot.answer_callback_query(call.id, f'Тест поставлен в очередь: {event_id[-8:]}')
            except Exception:
                pass
            safe_edit(bot, call, build_expense_shortcut_text(chat_id), reply_markup=build_expense_shortcut_keyboard(chat_id), parse_mode='HTML')
            return
        if data_str.startswith('ojr:'):
            if not is_owner_chat(chat_id):
                return
            try:
                _, key_s, answer = data_str.split(':', 2)
                key = int(key_s)
            except Exception:
                return
            with _owner_json_restore_prompt_lock:
                item = _owner_json_restore_prompts.pop(key, None)
            try:
                bot.delete_message(chat_id, call.message.message_id)
            except Exception:
                pass
            if not item:
                try:
                    bot.answer_callback_query(call.id, 'Срок кнопки истёк', show_alert=True)
                except Exception:
                    pass
                return
            if answer != 'yes':
                tmp_path = item.get('tmp_path')
                if tmp_path and os.path.exists(tmp_path):
                    try:
                        os.remove(tmp_path)
                    except Exception:
                        pass
                try:
                    bot.answer_callback_query(call.id, 'Обновление JSON отменено')
                except Exception:
                    pass
                return
            try:
                bot.answer_callback_query(call.id, 'Принято, обновляю JSON…')
            except Exception:
                pass
            if not GENERAL_TASK_POOL.submit(f'restore:{chat_id}', run_owner_json_restore_prompt_job, chat_id, item):
                send_and_auto_delete(chat_id, '⛔ Очередь восстановления переполнена.', 15)
            return
        if data_str.startswith('ncb:'):
            if not is_owner_chat(chat_id):
                return
            try:
                _, target_s, answer = data_str.split(':', 2)
                target_chat_id = int(target_s)
            except Exception:
                return
            set_auto_backup_enabled(target_chat_id, answer == 'yes')
            try:
                bot.delete_message(chat_id, call.message.message_id)
            except Exception:
                pass
            try:
                bot.answer_callback_query(call.id, 'Автообновление бэкапов включено' if answer == 'yes' else 'Автообновление бэкапов выключено')
            except Exception:
                pass
            return
        if data_str == 'secmclose':
            cancel_secret_media_timer(chat_id, call.message.message_id)
            try:
                bot.delete_message(chat_id, call.message.message_id)
            except Exception:
                pass
            return
        if data_str == 'secmwait':
            schedule_secret_media_close(chat_id, call.message.message_id)
            try:
                v178_edit_reply_markup_async(chat_id, call.message.message_id, build_secret_media_timer_keyboard(), 'secret_media_wait_v178')
                bot.answer_callback_query(call.id, 'Продлено на 1 мин 30 сек')
            except Exception:
                pass
            return
        if data_str == 'secclose':
            _cancel_secret_calendar_timer(chat_id, call.message.message_id)
            clear_secret_window(chat_id, call.message.message_id)
            try:
                bot.delete_message(chat_id, call.message.message_id)
            except Exception:
                pass
            return
        if data_str == 'secbacklist':
            if secret_window_self_only(chat_id, call.message.message_id):
                _cancel_secret_calendar_timer(chat_id, call.message.message_id)
                clear_secret_window(chat_id, call.message.message_id)
                try:
                    bot.delete_message(chat_id, call.message.message_id)
                except Exception:
                    pass
                return
            _cancel_secret_calendar_timer(chat_id, call.message.message_id)
            clear_secret_window(chat_id, call.message.message_id)
            safe_edit_current_only(bot, call, '🔐 Выберите чат с секретными данными:', reply_markup=build_secret_chat_list_keyboard())
            register_secret_list_window(chat_id, call.message.message_id)
            return
        if data_str.startswith('seclist:'):
            try:
                target_chat_id = int(data_str.split(':', 1)[1])
                open_secret_day_window(chat_id, target_chat_id, message_id=call.message.message_id, self_only=False)
            except Exception as e:
                log_error(f'secret list callback: {e}')
            return
        if data_str.startswith('sectoggle:'):
            try:
                target_chat_id = int(data_str.split(':', 1)[1])
                set_total_secret_mode(target_chat_id, not is_total_secret_mode(target_chat_id))
                safe_edit_current_only(bot, call, '🔐 Выберите чат с секретными данными:', reply_markup=build_secret_chat_list_keyboard())
            except Exception as e:
                log_error(f'secret mode toggle callback: {e}')
            return
        if data_str.startswith('secdel:'):
            try:
                _, target_s, day_key = data_str.split(':', 2)
                target_chat_id = int(target_s)
                if not can_manage_secret_target(chat_id, target_chat_id):
                    bot.answer_callback_query(call.id, 'Нет доступа', show_alert=True)
                    return
                self_only = secret_window_self_only(chat_id, call.message.message_id)
                set_secret_delete_selection(chat_id, target_chat_id, day_key, set())
                safe_edit_current_only(bot, call, build_secret_delete_text(chat_id, target_chat_id, day_key), reply_markup=build_secret_delete_keyboard(chat_id, target_chat_id, day_key, self_only=self_only))
                register_secret_window(chat_id, call.message.message_id, target_chat_id, 'delete', day_key=day_key, self_only=self_only)
                schedule_secret_calendar_close(chat_id, call.message.message_id)
            except Exception as e:
                log_error(f'secret delete menu callback: {e}')
            return
        if data_str.startswith('secdelt:'):
            try:
                _, target_s, day_key, mode = data_str.split(':', 3)
                target_chat_id = int(target_s)
                if not can_manage_secret_target(chat_id, target_chat_id):
                    bot.answer_callback_query(call.id, 'Нет доступа', show_alert=True)
                    return
                self_only = secret_window_self_only(chat_id, call.message.message_id)
                toggle_secret_delete_selection(chat_id, target_chat_id, day_key, mode)
                safe_edit_current_only(bot, call, build_secret_delete_text(chat_id, target_chat_id, day_key), reply_markup=build_secret_delete_keyboard(chat_id, target_chat_id, day_key, self_only=self_only))
                register_secret_window(chat_id, call.message.message_id, target_chat_id, 'delete', day_key=day_key, self_only=self_only)
                schedule_secret_calendar_close(chat_id, call.message.message_id)
            except Exception as e:
                log_error(f'secret delete toggle callback: {e}')
            return
        if data_str.startswith('secdelgo:'):
            try:
                _, target_s, day_key = data_str.split(':', 2)
                target_chat_id = int(target_s)
                if not can_manage_secret_target(chat_id, target_chat_id):
                    bot.answer_callback_query(call.id, 'Нет доступа', show_alert=True)
                    return
                selected = _secret_delete_selection(chat_id, target_chat_id, day_key)
                if not selected:
                    bot.answer_callback_query(call.id, 'Сначала поставь галочку', show_alert=True)
                    return
                count = delete_secret_records_by_modes(target_chat_id, selected, day_key)
                set_secret_delete_selection(chat_id, target_chat_id, day_key, set())
                self_only = secret_window_self_only(chat_id, call.message.message_id)
                try:
                    bot.answer_callback_query(call.id, f'Удалено: {count}', show_alert=False)
                except Exception:
                    pass
                open_secret_calendar(chat_id, target_chat_id, day_key[:7], message_id=call.message.message_id, self_only=self_only)
            except Exception as e:
                log_error(f'secret delete selected callback: {e}')
            return
        if data_str.startswith('secmedia:'):
            try:
                _, target_s, period = data_str.split(':', 2)
                target_chat_id = int(target_s)
                day_key = None if period == 'all' else period
                try:
                    bot.answer_callback_query(call.id, 'Отправляю медиа…')
                except Exception:
                    pass
                if not EXPORT_TASK_POOL.submit(f'secret-media:{chat_id}', send_secret_media, chat_id, target_chat_id, day_key):
                    send_and_auto_delete(chat_id, '⛔ Очередь медиа переполнена.', 12)
            except Exception as e:
                log_error(f'secret media callback: {e}')
            return
        if data_str.startswith('secmonthlist:'):
            try:
                _, target_s, month_key = data_str.split(':', 2)
                target_chat_id = int(target_s)
                self_only = secret_window_self_only(chat_id, call.message.message_id)
                open_secret_month_summary(chat_id, target_chat_id, month_key, message_id=call.message.message_id, self_only=self_only)
            except Exception as e:
                log_error(f'secret month summary callback: {e}')
            return
        if data_str.startswith('secchatcal:'):
            try:
                parts = data_str.split(':', 2)
                target_chat_id = int(parts[1])
                month_key = parts[2] if len(parts) > 2 and parts[2] else now_local().strftime('%Y-%m')
                self_only = secret_window_self_only(chat_id, call.message.message_id)
                open_secret_calendar(chat_id, target_chat_id, month_key, call.message.message_id, self_only=self_only)
            except Exception as e:
                log_error(f'secret chat calendar callback: {e}')
            return
        if data_str.startswith('secview:'):
            try:
                _, target_s, day_key = data_str.split(':', 2)
                self_only = secret_window_self_only(chat_id, call.message.message_id)
                open_secret_day_window(chat_id, int(target_s), day_key, call.message.message_id, self_only=self_only)
            except Exception as e:
                log_error(f'secret day view callback: {e}')
            return
        if data_str.startswith('secedfull:'):
            try:
                _, target_s, day_key, record_s = data_str.split(':', 3)
                target_chat_id = int(target_s)
                record_id = int(record_s)
                if not can_manage_secret_target(chat_id, target_chat_id):
                    bot.answer_callback_query(call.id, 'Нет доступа', show_alert=True)
                    return
                begin_secret_full_edit(chat_id, target_chat_id, day_key, record_id, source_window_msg_id=call.message.message_id)
                try:
                    bot.answer_callback_query(call.id, 'Полный текст показан ниже. Ответьте новым текстом.')
                except Exception:
                    pass
            except Exception as e:
                log_error(f'secret full edit callback: {e}')
            return
        if data_str.startswith('secedtoggle:'):
            try:
                _, target_s, day_key, record_s = data_str.split(':', 3)
                target_chat_id = int(target_s)
                record_id = int(record_s)
                if not can_manage_secret_target(chat_id, target_chat_id):
                    bot.answer_callback_query(call.id, 'Нет доступа', show_alert=True)
                    return
                self_only = secret_window_self_only(chat_id, call.message.message_id)
                toggle_secret_edit_delete_selection(chat_id, target_chat_id, day_key, record_id)
                try:
                    bot.answer_callback_query(call.id, '✅', show_alert=False)
                except Exception:
                    pass
                schedule_secret_edit_refresh_window(chat_id, call.message.message_id, target_chat_id, day_key, self_only=self_only, delay=0.7)
            except Exception as e:
                log_error(f'secret edit delete toggle callback: {e}')
            return
        if data_str.startswith('secedselected:'):
            try:
                _, target_s, day_key = data_str.split(':', 2)
                target_chat_id = int(target_s)
                if not can_manage_secret_target(chat_id, target_chat_id):
                    bot.answer_callback_query(call.id, 'Нет доступа', show_alert=True)
                    return
                selected = _secret_edit_delete_selection(chat_id, target_chat_id, day_key)
                if not selected:
                    bot.answer_callback_query(call.id, 'Сначала выбери записи', show_alert=True)
                    return
                count = delete_secret_records_by_ids(target_chat_id, selected)
                set_secret_edit_delete_selection(chat_id, target_chat_id, day_key, set())
                self_only = secret_window_self_only(chat_id, call.message.message_id)
                try:
                    bot.answer_callback_query(call.id, f'Удалено: {count}', show_alert=False)
                except Exception:
                    pass
                safe_edit_current_only(bot, call, build_secret_edit_text(target_chat_id, day_key), reply_markup=build_secret_edit_keyboard(chat_id, target_chat_id, day_key, self_only=self_only))
                register_secret_window(chat_id, call.message.message_id, target_chat_id, 'edit', day_key=day_key, self_only=self_only)
                schedule_secret_calendar_close(chat_id, call.message.message_id)
            except Exception as e:
                log_error(f'secret edit delete selected callback: {e}')
            return
        if data_str.startswith('secedit:'):
            try:
                _, target_s, day_key = data_str.split(':', 2)
                target_chat_id = int(target_s)
                self_only = secret_window_self_only(chat_id, call.message.message_id)
                set_secret_edit_delete_selection(chat_id, target_chat_id, day_key, set())
                safe_edit_current_only(bot, call, build_secret_edit_text(target_chat_id, day_key), reply_markup=build_secret_edit_keyboard(chat_id, target_chat_id, day_key, self_only=self_only))
                register_secret_window(chat_id, call.message.message_id, target_chat_id, 'edit', day_key=day_key, self_only=self_only)
                schedule_secret_calendar_close(chat_id, call.message.message_id)
            except Exception as e:
                log_error(f'secret edit menu callback: {e}')
            return
        if data_str.startswith('secmon:'):
            try:
                _, target_s, month_key = data_str.split(':', 2)
                self_only = secret_window_self_only(chat_id, call.message.message_id)
                open_secret_calendar(chat_id, int(target_s), month_key, call.message.message_id, self_only=self_only)
            except Exception as e:
                log_error(f'secret month callback: {e}')
            return
        if data_str.startswith('secday:'):
            try:
                _, target_s, day_key = data_str.split(':', 2)
                self_only = secret_window_self_only(chat_id, call.message.message_id)
                open_secret_day_window(chat_id, int(target_s), day_key, call.message.message_id, self_only=self_only)
            except Exception as e:
                log_error(f'secret day callback: {e}')
            return
        if data_str.startswith('v168:owners_circle:'):
            if not tenant_is_platform_owner_user(tenant_current_actor_user_id()):
                return
            try:
                level = 2 if int(data_str.rsplit(':', 1)[1]) == 2 else 1
                _v168_set_owner_access_circle(level)
                title = '1️⃣ Первый круг' if level == 1 else '2️⃣ Второй круг'
                safe_edit(bot, call, window_mark(f'👥 Доступ владельца к чатам\n\n{title}\n\n✅ — владелец может пользоваться ботом, смотреть и проверять этот чат\n⬜ — дополнительный доступ выключен', 'Ф2'), reply_markup=build_additional_owners_keyboard(level))
            except Exception as e:
                log_error(f'owner access circle callback: {e}')
            return
        if data_str.startswith('addown:'):
            if not tenant_is_platform_owner_user(tenant_current_actor_user_id()):
                return
            try:
                target_id = int(data_str.split(':', 1)[1])
                set_additional_owner(target_id, target_id not in get_additional_owner_ids())
                level = _v168_owner_access_circle(1)
                title = '1️⃣ Первый круг' if level == 1 else '2️⃣ Второй круг'
                safe_edit(bot, call, window_mark(f'👥 Доступ владельца к чатам\n\n{title}\n\n✅ — владелец может пользоваться ботом, смотреть и проверять этот чат\n⬜ — дополнительный доступ выключен', 'Ф2'), reply_markup=build_additional_owners_keyboard(level))
            except Exception as e:
                log_error(f'additional owner callback: {e}')
            return
        if data_str == 'additional_owners':
            if not tenant_is_platform_owner_user(tenant_current_actor_user_id()):
                return
            _v168_set_owner_access_circle(1)
            safe_edit(bot, call, window_mark('👥 Доступ владельца к чатам\n\n1️⃣ Первый круг\n\n✅ — владелец может пользоваться ботом, смотреть и проверять этот чат\n⬜ — дополнительный доступ выключен', 'Ф1'), reply_markup=build_additional_owners_keyboard(1))
            return
        if data_str.startswith('fvcat_'):
            if handle_finwindow_categories_callback(call, data_str):
                return
        if data_str == 'cat_months' or data_str.startswith('cat_'):
            if handle_categories_callback(call, data_str):
                return
        if data_str.startswith('itxt:'):
            current = _inline_fallback_get(data_str, int(chat_id))
            if not current:
                try:
                    bot.answer_callback_query(call.id, 'Кнопка устарела. Откройте окно заново.', show_alert=True)
                except Exception:
                    pass
                return
            try:
                bot.answer_callback_query(call.id, 'Текст показан ниже', show_alert=False)
            except Exception:
                pass
            helper = _tg_call_retry(bot.send_message, int(chat_id), current, purpose='inline_text_channel_fallback')
            if helper is not None and getattr(helper, 'message_id', None):
                delete_message_later(int(chat_id), int(helper.message_id), 25)
            return
        if data_str == 'fwdcopy_edit':
            start_forward_copy_edit(chat_id, call.message.message_id)
            return
        if data_str == 'fwdcopy_edit_cancel':
            clear_forward_copy_edit_wait(chat_id, delete_prompt=True)
            return
        if data_str == 'fwdcopy_edit_copy':
            wait = get_chat_store(int(chat_id)).get('forward_copy_edit_wait') or {}
            current = str(wait.get('insert_text') or '').strip()
            try:
                bot.answer_callback_query(call.id, 'Текст без @бот показан ниже', show_alert=False)
            except Exception:
                pass
            if current:
                helper = _tg_call_retry(bot.send_message, int(chat_id), current, purpose='forward_copy_edit_copy_fallback')
                if helper is not None and getattr(helper, 'message_id', None):
                    delete_message_later(int(chat_id), int(helper.message_id), 25)
            return
        if data_str == 'forward_copy_edit_mode_toggle':
            if not version_mode_feature('forward_copy_edit'):
                return
            new_mode = cycle_forward_copy_edit_mode(chat_id)
            try:
                bot.answer_callback_query(call.id, forward_copy_edit_mode_label(chat_id), show_alert=False)
            except Exception:
                pass
            safe_edit(bot, call, build_info_text(chat_id), reply_markup=build_info_keyboard(chat_id))
            retro_generation = _begin_forward_copy_retro_refresh(chat_id)
            retro_queued = MAINTENANCE_TASK_POOL.submit('fwdcopy-retro:global', refresh_existing_forward_copy_ui, chat_id, new_mode, retro_generation)
            if not retro_queued:
                log_error(f'FORWARD COPY RETRO MAINTENANCE QUEUE FULL: chat={chat_id} mode={new_mode}')
            bot_journal('forward_copy_edit_mode', chat_id, f'mode={new_mode} retro_queued={retro_queued} generation={retro_generation} days={FORWARD_COPY_RETRO_DAYS} max_per_chat={FORWARD_COPY_RETRO_MAX_PER_CHAT}')
            return
        if guard_non_owner_finance_for_callback(chat_id, data_str):
            return
        if data_str == 'dzv:close':
            try:
                bot.delete_message(chat_id, call.message.message_id)
            except Exception:
                pass
            return
        if data_str.startswith('dzv:'):
            try:
                target_chat_id = int(data_str.split(':', 1)[1])
            except Exception:
                return
            start_dozvon(chat_id, target_chat_id)
            safe_edit(bot, call, f'📞 Дозвон: {get_chat_display_name(target_chat_id)}', reply_markup=build_dozvon_menu(chat_id))
            return
        store = get_chat_store(chat_id)
        if data_str == 'secret_cancel':
            _clear_secret_wait(chat_id, delete_prompt=False)
            try:
                bot.delete_message(chat_id, call.message.message_id)
            except Exception:
                pass
            return
        try:
            wait = store.get('secret_wait') or {}
            wait_msg_id = int(wait.get('prompt_msg_id') or wait.get('window_msg_id') or 0)
            if wait_msg_id == int(call.message.message_id) and str(data_str).startswith('d:') and str(data_str).endswith(':back_main'):
                _clear_secret_wait(chat_id, delete_prompt=False)
        except Exception:
            pass
        try:
            fwait = store.get('forward_copy_edit_wait') or {}
            fwait_msg_id = int(fwait.get('prompt_msg_id') or 0)
            if fwait_msg_id == int(call.message.message_id) and str(data_str).startswith('d:') and str(data_str).endswith(':back_main'):
                clear_forward_copy_edit_wait(chat_id, delete_prompt=False)
        except Exception:
            pass
        if handle_o9_secret_triple_click(call, data_str):
            return
        if call.message.message_id == store.get('balance_panel_id') and data_str != 'bp:open':
            schedule_balance_panel_collapse(chat_id)
        if data_str == 'bp:open':
            open_balance_panel_in_message(chat_id, call.message.message_id)
            try:
                bot.answer_callback_query(call.id, f"Остаток: {format_chat_amount(chat_id, get_chat_store(chat_id).get('balance', 0), True)}")
            except Exception:
                pass
            return
        if data_str == 'bp:collapse':
            collapse_balance_panel(chat_id)
            return
        if data_str == 'rep_today':
            open_report_window(chat_id, now_local().strftime('%Y-%m'), call.message.message_id)
            return
        if data_str == 'rep_close':
            try:
                bot.delete_message(chat_id, call.message.message_id)
            except Exception as e:
                log_error(f'rep_close delete failed: {e}')
            store = get_chat_store(chat_id)
            if store.get('report_window_id') == call.message.message_id:
                store['report_window_id'] = None
                store['report_month'] = None
                save_data(data)
            return
        if data_str.startswith('main_close:'):
            try:
                day_key = data_str.split(':', 1)[1] or today_key()
            except Exception:
                day_key = today_key()
            cancel_pending_window_commands(chat_id, delete_prompt=False)
            mid = int(call.message.message_id)
            try:
                bot.delete_message(chat_id, mid)
            except Exception:
                pass
            try:
                aw = get_or_create_active_windows(chat_id)
                for key, value in list(aw.items()):
                    try:
                        if int(value or 0) == mid:
                            aw.pop(key, None)
                    except Exception:
                        pass
                store = get_chat_store(chat_id)
                if int(store.get('balance_panel_id') or 0) == mid:
                    store['balance_panel_id'] = None
                    store['balance_panel_mode'] = 'mini'
                unregister_open_window(chat_id, mid)
                state = _finance_window_state(chat_id)
                state['main_windows'] = {str(k): int(v) for k, v in aw.items() if v}
                state['balance_panel_id'] = int(store.get('balance_panel_id')) if store.get('balance_panel_id') else None
                state['auto_reopen_on_boot'] = False
                state['updated_at'] = now_local().isoformat(timespec='seconds')
                save_data(data, chat_ids=[chat_id])
                _persist_finance_window_mode_critical(chat_id)
            except Exception as e:
                log_error(f'main_close({chat_id},{day_key}): {e}')
            return
        if data_str in {'aux_close', 'info_close'}:
            cancel_pending_window_commands(chat_id, delete_prompt=False)
            v177_delete_message_async(chat_id, call.message.message_id, purpose=data_str)
            unregister_open_window(chat_id, call.message.message_id)
            return
        if data_str.startswith('rep:'):
            month_key = data_str.split(':', 1)[1].strip()
            open_report_window(chat_id, month_key, call.message.message_id)
            return
        if data_str.startswith('fvcat_'):
            if handle_finwindow_categories_callback(call, data_str):
                return
        if data_str == 'cat_months' or data_str.startswith('cat_'):
            if handle_categories_callback(call, data_str):
                return
        if data_str.startswith('fw_'):
            if not is_owner_chat(chat_id):
                try:
                    bot.answer_callback_query(call.id, 'Меню пересылки доступно только владельцу.', show_alert=True)
                except Exception:
                    pass
                return
            if data_str == 'fw_new_back_src':
                owner_store = get_chat_store(int(OWNER_ID))
                owner_day_key = owner_store.get('current_view_day', today_key())
                safe_edit(bot, call, build_forward_new_text(), reply_markup=build_forward_new_menu(owner_day_key))
                return
            if data_str.startswith('fw_new_pair:'):
                parts = data_str.split(':')
                if len(parts) != 3:
                    return
                try:
                    A = int(parts[1])
                    B = int(parts[2])
                except Exception:
                    return
                if answer_removed_chat(call, A) or answer_removed_chat(call, B):
                    return
                safe_edit(bot, call, build_forward_new_text(A, B), reply_markup=build_forward_new_menu(None, A, B))
                return
            if data_str.startswith('fw_new_src:'):
                try:
                    A = int(data_str.split(':', 1)[1])
                except Exception:
                    return
                if answer_removed_chat(call, A):
                    return
                safe_edit(bot, call, build_forward_new_text(A, None), reply_markup=build_forward_new_menu(None, A, None))
                return
            if data_str.startswith('fw_new_tgt:'):
                parts = data_str.split(':')
                if len(parts) != 3:
                    return
                try:
                    A = int(parts[1])
                    B = int(parts[2])
                except Exception:
                    return
                if answer_removed_chat(call, A) or answer_removed_chat(call, B):
                    return
                safe_edit(bot, call, build_forward_new_text(A, B), reply_markup=build_forward_new_menu(None, A, B))
                return
            if data_str.startswith('fw_new_fin:'):
                parts = data_str.split(':')
                if len(parts) != 4:
                    return
                try:
                    A = int(parts[1])
                    B = int(parts[2])
                    which = parts[3]
                except Exception:
                    return
                if answer_removed_chat(call, A) or answer_removed_chat(call, B):
                    return
                if which == 'ab':
                    new_val = not get_forward_finance(A, B)
                    set_forward_finance(A, B, new_val)
                    if new_val:
                        _remember_forward_pair(A, B)
                elif which == 'ba':
                    new_val = not get_forward_finance(B, A)
                    set_forward_finance(B, A, new_val)
                    if new_val:
                        _remember_forward_pair(A, B)
                _forget_forward_pair_if_empty(A, B)
                safe_edit(bot, call, build_forward_new_text(A, B), reply_markup=build_forward_new_menu(None, A, B))
                return
            if data_str.startswith('fw_new_mode:'):
                parts = data_str.split(':')
                if len(parts) != 4:
                    return
                try:
                    A = int(parts[1])
                    B = int(parts[2])
                    mode = parts[3]
                except Exception:
                    return
                if answer_removed_chat(call, A) or answer_removed_chat(call, B):
                    return
                fr = data.get('forward_rules', {}) or {}
                if mode == 'to':
                    if str(B) in (fr.get(str(A), {}) or {}):
                        remove_forward_link(A, B)
                    else:
                        add_forward_link(A, B, 'oneway_to')
                        _remember_forward_pair(A, B)
                elif mode == 'from':
                    if str(A) in (fr.get(str(B), {}) or {}):
                        remove_forward_link(B, A)
                    else:
                        add_forward_link(B, A, 'oneway_to')
                        _remember_forward_pair(A, B)
                elif mode == 'two':
                    ab_on = str(B) in (fr.get(str(A), {}) or {})
                    ba_on = str(A) in (fr.get(str(B), {}) or {})
                    if ab_on and ba_on:
                        remove_forward_link(A, B)
                        remove_forward_link(B, A)
                    else:
                        add_forward_link(A, B, 'twoway')
                        add_forward_link(B, A, 'twoway')
                        _remember_forward_pair(A, B)
                _forget_forward_pair_if_empty(A, B)
                safe_edit(bot, call, build_forward_new_text(A, B), reply_markup=build_forward_new_menu(None, A, B))
                return
            if data_str.startswith('fw_new_clear:'):
                parts = data_str.split(':')
                if len(parts) != 3:
                    return
                try:
                    A = int(parts[1])
                    B = int(parts[2])
                except Exception:
                    return
                remove_forward_link(A, B)
                remove_forward_link(B, A)
                remove_forward_finance(A, B)
                remove_forward_finance(B, A)
                _forget_forward_pair_if_empty(A, B)
                safe_edit(bot, call, build_forward_new_text(A, B), reply_markup=build_forward_new_menu(None, A, B))
                return
            if data_str == 'fw_probe_all':
                owner_store = get_chat_store(int(OWNER_ID))
                owner_day_key = owner_store.get('current_view_day', today_key())
                safe_edit_current_only(bot, call, build_forward_status_text('📡 Проверяю чаты в фоне...\nОкно обновится здесь же.'), reply_markup=build_forward_source_menu(owner_day_key))
                queued = MAINTENANCE_TASK_POOL.submit_unique(f'forward-probe-all:{int(chat_id)}', _forward_probe_all_background, int(chat_id), int(call.message.message_id))
                try:
                    bot.answer_callback_query(call.id, build_all_processes_toast(chat_id) if queued else 'Проверка чатов уже выполняется', show_alert=False)
                except Exception:
                    pass
                return
            if data_str == 'fw_removed_list':
                owner_store = get_chat_store(int(OWNER_ID))
                owner_day_key = owner_store.get('current_view_day', today_key())
                safe_edit(bot, call, '🗑 Удалённые чаты\nНажмите чат, чтобы перепроверить наличие бота.', reply_markup=build_removed_chats_menu(owner_day_key))
                return
            if data_str.startswith('fw_probe_one:'):
                try:
                    cid = int(data_str.split(':', 1)[1])
                except Exception:
                    return
                owner_store = get_chat_store(int(OWNER_ID))
                owner_day_key = owner_store.get('current_view_day', today_key())
                safe_edit_current_only(bot, call, build_forward_status_text(f'📡 Проверяю {get_chat_display_name(cid)} в фоне...'), reply_markup=build_removed_chats_menu(owner_day_key))
                queued = MAINTENANCE_TASK_POOL.submit_unique(f'forward-probe-one:{cid}', _forward_probe_one_background, int(chat_id), int(call.message.message_id), int(cid))
                try:
                    bot.answer_callback_query(call.id, build_all_processes_toast(chat_id) if queued else 'Проверка уже выполняется')
                except Exception:
                    pass
                return
            if data_str == 'fw_open':
                owner_store = get_chat_store(int(OWNER_ID))
                owner_day_key = owner_store.get('current_view_day', today_key())
                kb = build_forward_menu_keyboard_for_current_mode(owner_day_key)
                safe_edit(bot, call, build_forward_menu_text_for_current_mode('Пересылка:\nВыберите чат A:'), reply_markup=kb)
                return
            if data_str == 'fw_back_root':
                owner_store = get_chat_store(int(OWNER_ID))
                day_key = owner_store.get('current_view_day', today_key())
                txt, _ = render_day_window(chat_id, day_key)
                safe_edit(bot, call, txt, reply_markup=build_main_keyboard(day_key, chat_id), parse_mode='HTML')
                return
            if data_str == 'fw_back_src':
                owner_store = get_chat_store(int(OWNER_ID))
                owner_day_key = owner_store.get('current_view_day', today_key())
                kb = build_forward_menu_keyboard_for_current_mode(owner_day_key)
                safe_edit(bot, call, build_forward_menu_text_for_current_mode('Пересылка:\nВыберите чат A:'), reply_markup=kb)
                return
            if data_str.startswith('fw_back_tgt:'):
                try:
                    A = int(data_str.split(':', 1)[1])
                except Exception:
                    return
                if answer_removed_chat(call, A):
                    return
                kb = build_forward_target_menu(A)
                safe_edit(bot, call, build_forward_status_text(f'Источник: {get_chat_display_name(A)}\nВыберите чат B:'), reply_markup=kb)
                return
            if data_str.startswith('fw_src:'):
                try:
                    A = int(data_str.split(':', 1)[1])
                except Exception:
                    return
                if answer_removed_chat(call, A):
                    return
                kb = build_forward_target_menu(A)
                safe_edit(bot, call, build_forward_status_text(f'Источник: {get_chat_display_name(A)}\nВыберите чат B:'), reply_markup=kb)
                return
            if data_str.startswith('fw_tgt:'):
                parts = data_str.split(':')
                if len(parts) != 3:
                    return
                _, A_str, B_str = parts
                try:
                    A = int(A_str)
                    B = int(B_str)
                except Exception:
                    return
                if answer_removed_chat(call, A) or answer_removed_chat(call, B):
                    return
                kb = build_forward_mode_menu(A, B)
                safe_edit(bot, call, build_forward_status_text(f'Настройка пересылки: {get_chat_display_name(A)} ⇄ {get_chat_display_name(B)}'), reply_markup=kb)
                return
            if data_str.startswith('fw_finpair:'):
                parts = data_str.split(':')
                if len(parts) != 4:
                    return
                _, A_str, B_str, which = parts
                try:
                    A = int(A_str)
                    B = int(B_str)
                except Exception:
                    return
                if answer_removed_chat(call, A) or answer_removed_chat(call, B):
                    return
                if which == 'ab':
                    set_forward_finance(A, B, not get_forward_finance(A, B))
                elif which == 'ba':
                    set_forward_finance(B, A, not get_forward_finance(B, A))
                kb = build_forward_mode_menu(A, B)
                safe_edit(bot, call, build_forward_status_text(f'Настройка пересылки: {get_chat_display_name(A)} ⇄ {get_chat_display_name(B)}'), reply_markup=kb)
                return
            if data_str.startswith('fw_mode:'):
                parts = data_str.split(':')
                if len(parts) != 4:
                    return
                _, A_str, B_str, mode = parts
                try:
                    A = int(A_str)
                    B = int(B_str)
                except Exception:
                    return
                if answer_removed_chat(call, A) or answer_removed_chat(call, B):
                    return
                if mode == 'to':
                    if str(B) in (data.get('forward_rules', {}) or {}).get(str(A), {}):
                        remove_forward_link(A, B)
                    else:
                        add_forward_link(A, B, 'oneway_to')
                elif mode == 'from':
                    if str(A) in (data.get('forward_rules', {}) or {}).get(str(B), {}):
                        remove_forward_link(B, A)
                    else:
                        add_forward_link(B, A, 'oneway_to')
                elif mode == 'two':
                    fr = data.get('forward_rules', {}) or {}
                    ab_on = str(B) in fr.get(str(A), {})
                    ba_on = str(A) in fr.get(str(B), {})
                    if ab_on and ba_on:
                        remove_forward_link(A, B)
                        remove_forward_link(B, A)
                    else:
                        add_forward_link(A, B, 'twoway')
                        add_forward_link(B, A, 'twoway')
                elif mode == 'del':
                    remove_forward_link(A, B)
                    remove_forward_link(B, A)
                kb = build_forward_mode_menu(A, B)
                safe_edit(bot, call, build_forward_status_text(f'Настройка пересылки: {get_chat_display_name(A)} ⇄ {get_chat_display_name(B)}'), reply_markup=kb)
                return
            return
        if data_str.startswith('c:'):
            center = data_str[2:]
            try:
                center_dt = datetime.strptime(center, '%Y-%m-%d')
            except Exception:
                center_dt = now_local()
            kb = build_calendar_keyboard(center_dt, chat_id)
            safe_edit(bot, call, calendar_window_text(center_dt), reply_markup=kb)
            register_open_window(chat_id, call.message.message_id, 'local_fin_view', code='calendar', day_key=center_dt.strftime('%Y-%m-%d'), params={'view_action': 'calendar', 'center_day': center_dt.strftime('%Y-%m-%d')})
            return
        if data_str.startswith('fc:'):
            if not is_owner_chat(chat_id):
                return
            try:
                _, target_s, center_s, owner_day_key = data_str.split(':', 3)
                target_chat_id = int(target_s)
                center_dt = datetime.strptime(center_s, '%Y-%m-%d')
            except Exception:
                return
            safe_edit(bot, call, f'📅 Выберите день: {html.escape(get_chat_display_name(target_chat_id))}\n{russian_month_name(center_dt.month)} {center_dt.year}', reply_markup=build_fin_calendar_keyboard(target_chat_id, center_dt, owner_day_key), parse_mode='HTML')
            register_open_window(chat_id, call.message.message_id, 'fin_view', code='fv:calendar', day_key=center_dt.strftime('%Y-%m-%d'), params={'target_chat_id': target_chat_id, 'owner_day_key': owner_day_key, 'view_action': 'calendar', 'center_day': center_dt.strftime('%Y-%m-%d')})
            return
        if data_str == 'articles_desc':
            if not is_owner_chat(chat_id):
                return
            kb = types.InlineKeyboardMarkup()
            kb.row(IB('🔙 Назад', callback_data='journal_back'))
            safe_edit(bot, call, build_articles_description_text(chat_id), reply_markup=kb)
            return
        if data_str == 'journal_open':
            if not is_owner_chat(chat_id):
                return
            safe_edit(bot, call, build_journal_v208_menu_text(), reply_markup=build_journal_v208_menu_keyboard(chat_id))
            return
        if data_str == 'journal_toggle_open':
            if not is_owner_chat(chat_id):
                return
            new_state = toggle_journal_registration()
            bot_journal('journal_toggle', chat_id, f'enabled={new_state}')
            safe_edit(bot, call, build_journal_v208_menu_text(), reply_markup=build_journal_v208_menu_keyboard(chat_id))
            return
        if data_str == 'journal_compact_toggle':
            if not is_owner_chat(chat_id):
                return
            new_state = set_journal_compact_remote_enabled(not journal_compact_remote_effective_enabled())
            try:
                gate = globals().get('v176_set_process')
                if callable(gate):
                    gate('journal_mega', bool(new_state), int(chat_id))
            except Exception:
                pass
            bot_journal('journal_compact_remote_toggle_v208', chat_id, f'enabled={new_state}')
            if new_state:
                try:
                    DELAYED_SCHEDULER.schedule('journal-v208-enable-flush', 2.0, journal_flush_to_mega, True)
                except Exception:
                    pass
            safe_edit(bot, call, build_journal_v208_menu_text(), reply_markup=build_journal_v208_menu_keyboard(chat_id))
            return
        if data_str == 'journal_compact_interval_menu':
            if not is_owner_chat(chat_id):
                return
            safe_edit(bot, call, journal_v208_status_text() + '\n\nВыберите максимальный интервал между сжатыми фиксациями в MEGA.', reply_markup=journal_v208_interval_keyboard())
            return
        if data_str.startswith('journal_compact_interval:'):
            if not is_owner_chat(chat_id):
                return
            try:
                sec = int(data_str.split(':', 1)[1])
            except Exception:
                sec = 600
            value = set_journal_compact_interval_seconds(sec)
            bot_journal('journal_compact_interval_v208', chat_id, f'seconds={value}')
            safe_edit(bot, call, build_journal_v208_menu_text(), reply_markup=build_journal_v208_menu_keyboard(chat_id))
            return
        if data_str == 'journal_verbose_toggle':
            if not is_owner_chat(chat_id):
                return
            new_state = toggle_verbose_telegram_journal()
            bot_journal('journal_verbose_telegram_toggle_v208', chat_id, f'enabled={new_state}')
            safe_edit(bot, call, build_journal_v208_menu_text(), reply_markup=build_journal_v208_menu_keyboard(chat_id))
            return
        if data_str == 'journal_name_edit':
            if not is_owner_chat(chat_id):
                return
            kb = types.InlineKeyboardMarkup()
            kb.row(IB(f"📚 Общий: {journal_download_base_name_for('full')[:28]}", callback_data='journal_name_edit:full'))
            kb.row(IB(f"📓 Текущий: {journal_download_base_name_for('current')[:28]}", callback_data='journal_name_edit:current'))
            kb.row(IB('🔙 Назад в журналы', callback_data='journal_open'))
            safe_edit(bot, call, '✏️ <b>Какой журнал переименовать?</b>', reply_markup=kb, parse_mode='HTML')
            return
        if data_str.startswith('journal_name_edit:'):
            if not is_owner_chat(chat_id):
                return
            kind = 'current' if data_str.rsplit(':', 1)[-1] == 'current' else 'full'
            journal_filename_begin_wait(chat_id, 120.0, kind=kind)
            label = 'журнала текущей версии' if kind == 'current' else 'общего журнала'
            kb = types.InlineKeyboardMarkup()
            kb.row(IB('♻️ Сбросить имя', callback_data=f'journal_name_reset:{kind}'))
            kb.row(IB('🔙 Назад в журналы', callback_data='journal_open'), IB('❌ Отмена', callback_data='journal_name_cancel'))
            safe_edit(bot, call, f'✏️ <b>Имя {label}</b>\n\nСейчас: <code>{journal_download_base_name_for(kind)}</code>\n\nОтправьте одним сообщением новое имя. Расширение .txt добавится автоматически.\n⏰ Ожидание ввода: 2 минуты.', reply_markup=kb, parse_mode='HTML')
            return
        if data_str == 'journal_name_cancel':
            if not is_owner_chat(chat_id):
                return
            journal_filename_cancel_wait(chat_id)
            safe_edit(bot, call, build_journal_v208_menu_text(), reply_markup=build_journal_v208_menu_keyboard(chat_id))
            return
        if data_str == 'journal_name_reset' or data_str.startswith('journal_name_reset:'):
            if not is_owner_chat(chat_id):
                return
            journal_filename_cancel_wait(chat_id)
            kind = 'current' if data_str.endswith(':current') else 'full'
            default = 'Журнал_текущей_версии' if kind == 'current' else 'Журнал_бота'
            base = set_journal_download_base_name(default, kind=kind)
            try:
                bot.answer_callback_query(call.id, f'Имя сброшено: {base}')
            except Exception:
                pass
            safe_edit(bot, call, build_journal_v208_menu_text(), reply_markup=build_journal_v208_menu_keyboard(chat_id))
            return
        if data_str == 'journal_file':
            if not is_owner_chat(chat_id):
                return
            send_journal_file_to_owner(chat_id, 3000)
            return
        if data_str == 'journal_current_file':
            if not is_owner_chat(chat_id):
                return
            send_current_version_journal_to_owner(chat_id, 5000)
            return
        if data_str == 'journal_bot_source':
            if not is_owner_chat(chat_id):
                return
            send_current_bot_source_to_owner(chat_id)
            return
        if data_str == 'journal_toggle':
            if not is_owner_chat(chat_id):
                return
            new_state = toggle_journal_registration()
            bot_journal('journal_toggle', chat_id, f'enabled={new_state}')
            safe_edit(bot, call, build_info_text(chat_id), reply_markup=build_info_keyboard(chat_id))
            return
        if data_str == 'journal_chats_open' or data_str.startswith('journal_chats_open:'):
            if not is_owner_chat(chat_id):
                return
            try:
                page = int(data_str.split(':', 1)[1]) if ':' in data_str else 0
            except Exception:
                page = 0
            safe_edit(bot, call, build_chat_journal_menu_text(page), reply_markup=build_chat_journal_menu_keyboard(page))
            return
        if data_str.startswith('journal_chat_toggle:'):
            if not is_owner_chat(chat_id):
                return
            try:
                parts = data_str.split(':')
                target_chat_id = int(parts[1])
                page = int(parts[2]) if len(parts) > 2 else 0
            except Exception:
                return
            new_state = toggle_chat_journal(target_chat_id)
            bot_journal('journal_chat_toggle', target_chat_id, f'enabled={new_state}')
            if int(target_chat_id) == int(chat_id) and (not str(getattr(call.message, 'text', '') or '').startswith('📓 Журналы по чатам')):
                safe_edit(bot, call, build_info_text(chat_id), reply_markup=build_info_keyboard(chat_id))
            else:
                safe_edit(bot, call, build_chat_journal_menu_text(page), reply_markup=build_chat_journal_menu_keyboard(page))
            return
        if data_str == 'journal_chats_back':
            if not is_owner_chat(chat_id):
                return
            safe_edit(bot, call, build_info_text(chat_id), reply_markup=build_info_keyboard(chat_id))
            return
        if data_str == 'currency_menu':
            if version_mode_layout() != 'v87':
                return
            fast_ui_edit_message_text(chat_id, call.message.message_id, currency_menu_text(chat_id), reply_markup=build_currency_menu_keyboard(chat_id), purpose='currency_menu')
            return
        if data_str.startswith('currency_select:'):
            if version_mode_layout() != 'v87':
                return
            mode = data_str.split(':', 1)[1]
            set_currency_mode(chat_id, mode)
            bot_journal('currency_mode_changed', chat_id, f'mode={mode}')
            fast_ui_edit_message_text(chat_id, call.message.message_id, currency_menu_text(chat_id), reply_markup=build_currency_menu_keyboard(chat_id), purpose='currency_select')
            try:
                day_key = get_chat_store(chat_id).get('current_view_day') or today_key()
                finance_changed(chat_id, day_key, reason='currency_mode_changed', delay=0.03)
            except Exception:
                pass
            return
        if data_str == 'currency_back':
            fast_ui_edit_message_text(chat_id, call.message.message_id, build_info_text(chat_id), reply_markup=build_info_keyboard(chat_id), purpose='currency_back')
            return
        if data_str == 'usd_display_toggle':
            if not version_mode_feature('daily_usd'):
                return
            new_state = toggle_usd_display(chat_id)
            bot_journal('usd_display_toggle', chat_id, f'enabled={new_state}')
            try:
                bot.answer_callback_query(call.id, 'Доллар включён' if new_state else 'Доллар выключен', show_alert=False)
            except Exception:
                pass
            safe_edit(bot, call, build_info_text(chat_id), reply_markup=build_info_keyboard(chat_id))
            try:
                day_key = get_chat_store(chat_id).get('current_view_day') or today_key()
                finance_changed(chat_id, day_key, reason='usd_display_toggle', delay=0.05)
            except Exception:
                pass
            return
        if data_str == 'gomonk_open' or data_str.startswith('gomonk_open:'):
            if not _v85_enabled('gomonk_wallets'):
                bot_journal('gomonk_blocked', chat_id, f'profile={active_bot_behavior_profile()}')
                try:
                    bot.answer_callback_query(call.id, 'Гомонковые недоступны в выбранном историческом профиле', show_alert=True)
                except Exception:
                    pass
                return
            currency = data_str.split(':', 1)[1] if ':' in data_str else _gomonk_currency(chat_id)
            bot_journal('gomonk_open', chat_id, f'currency={currency} profile={active_bot_behavior_profile()}')
            open_gomonk_window(chat_id, call.message.message_id, currency=currency)
            return
        if data_str == 'gomonk_toggle' or data_str.startswith('gomonk_toggle:'):
            if not _v85_enabled('gomonk_wallets'):
                return
            currency = data_str.split(':', 1)[1] if ':' in data_str else _gomonk_currency(chat_id)
            new_state = toggle_gomonk_enabled(chat_id, currency)
            bot_journal('gomonk_toggle', chat_id, f'currency={currency} enabled={new_state}')
            open_gomonk_window(chat_id, call.message.message_id, currency=currency)
            return
        if data_str == 'gomonk_back' or data_str.startswith('gomonk_back:'):
            fast_ui_edit_message_text(chat_id, call.message.message_id, build_info_text(chat_id), reply_markup=build_info_keyboard(chat_id), purpose='gomonk_back')
            return
        if data_str.startswith('remaining_open:'):
            if not _v85_enabled('remaining_window'):
                return
            day_key = data_str.split(':', 1)[1] or today_key()
            open_remaining_window(chat_id, day_key, call.message.message_id)
            return
        if data_str.startswith('remaining_toggle:'):
            if not _v85_enabled('remaining_window'):
                return
            parts = data_str.split(':')
            day_key = (parts[1] if len(parts) > 1 else '') or today_key()
            currency = _gomonk_currency(chat_id)
            desired = None
            if len(parts) > 2 and parts[2] in {'0', '1'}:
                desired = parts[2] == '1'
            if desired is None:
                new_state = _toggle_remaining_state(chat_id, currency)
            else:
                new_state = _set_remaining_state(chat_id, desired, currency)
            try:
                bot.answer_callback_query(call.id, 'С гомонковыми' if new_state else 'Без гомонковых', show_alert=False)
            except Exception:
                pass
            open_remaining_window(chat_id, day_key, call.message.message_id, with_gomonk=new_state)
            _persist_remaining_state_async(chat_id)
            try:
                bot_journal('remaining_gomonk_state_v195', chat_id, f'currency={currency}; day={day_key}; enabled={int(new_state)}; explicit={int(desired is not None)}')
            except Exception:
                pass
            return
        if data_str == 'careful_restore_toggle':
            if not is_owner_chat(chat_id) or int(getattr(getattr(call, 'from_user', None), 'id', 0) or 0) != int(OWNER_ID or 0):
                try:
                    bot.answer_callback_query(call.id, 'Только основной владелец.', show_alert=True)
                except Exception:
                    pass
                return
            enabled = careful_restore_toggle(chat_id)
            st = careful_restore_status(chat_id)
            try:
                if enabled:
                    bot.answer_callback_query(call.id, f"ВКЛ → {fmt_date_ddmmyy(st.get('day_key') or today_key())}; авто-ВЫКЛ через {_format_duration_short(internal_timer_seconds('careful_restore_idle', 120))}", show_alert=False)
                else:
                    bot.answer_callback_query(call.id, 'Аккуратное восстановление выключено', show_alert=False)
            except Exception:
                pass
            fast_ui_edit_message_text(chat_id, call.message.message_id, build_info_text(chat_id), reply_markup=build_info_keyboard(chat_id), purpose='careful_restore_toggle')
            return
        if data_str == 'main_articles_toggle':
            if not version_mode_feature('article_buttons'):
                return
            new_state = toggle_main_article_buttons(chat_id)
            try:
                bot.answer_callback_query(call.id, 'Статьи-кнопки включены' if new_state else 'Статьи-кнопки выключены', show_alert=False)
            except Exception:
                pass
            safe_edit(bot, call, build_info_text(chat_id), reply_markup=build_info_keyboard(chat_id))
            try:
                finance_changed(chat_id, get_chat_store(chat_id).get('current_view_day') or today_key(), reason='main_articles_toggle', delay=0.03)
            except Exception:
                pass
            return
        if data_str == 'main_financial_values_toggle':
            if not version_mode_feature('financial_value_buttons'):
                return
            new_state = toggle_main_financial_value_buttons(chat_id)
            try:
                bot.answer_callback_query(call.id, 'Финансовые значения теперь кнопками' if new_state else 'Финансовые кнопки выключены', show_alert=False)
            except Exception:
                pass
            safe_edit(bot, call, build_info_text(chat_id), reply_markup=build_info_keyboard(chat_id))
            try:
                finance_changed(chat_id, get_chat_store(chat_id).get('current_view_day') or today_key(), reason='main_financial_values_toggle', delay=0.03)
            except Exception:
                pass
            return
        if data_str == 'internal_timers':
            if not is_owner_chat(chat_id):
                return
            _reset_timer_input_session(chat_id, None)
            fast_ui_edit_message_text(chat_id, call.message.message_id, build_internal_timers_text(), reply_markup=build_internal_timers_keyboard(chat_id), purpose='internal_timers')
            return
        if data_str.startswith('itmr_pick:'):
            if not is_owner_chat(chat_id):
                return
            key = data_str.split(':', 1)[1]
            if key not in INTERNAL_TIMER_DEFS:
                return
            _reset_timer_input_session(chat_id, key)
            fast_ui_edit_message_text(chat_id, call.message.message_id, build_internal_timer_input_text(chat_id), reply_markup=build_internal_timer_input_keyboard(chat_id), purpose='internal_timer_pick')
            return
        if data_str.startswith('itmr_digit:'):
            if not is_owner_chat(chat_id):
                return
            digit = data_str.split(':', 1)[1]
            if digit not in '0123456789':
                return
            session = _timer_input_session(chat_id)
            if session.get('key') not in INTERNAL_TIMER_DEFS:
                return
            session['buffer'] = (str(session.get('buffer') or '') + digit)[-5:]
            fast_ui_edit_message_text(chat_id, call.message.message_id, build_internal_timer_input_text(chat_id), reply_markup=build_internal_timer_input_keyboard(chat_id), purpose='internal_timer_digit')
            return
        if data_str.startswith('itmr_unit:'):
            if not is_owner_chat(chat_id):
                return
            unit = data_str.split(':', 1)[1]
            session = _timer_input_session(chat_id)
            if session.get('key') not in INTERNAL_TIMER_DEFS:
                return
            buf = str(session.get('buffer') or '')
            if not buf:
                try:
                    bot.answer_callback_query(call.id, 'Сначала наберите число', show_alert=False)
                except Exception:
                    pass
                return
            value = int(buf)
            if unit == 'm':
                session['minutes'] = value
            elif unit == 's':
                session['seconds'] = value
            session['buffer'] = ''
            fast_ui_edit_message_text(chat_id, call.message.message_id, build_internal_timer_input_text(chat_id), reply_markup=build_internal_timer_input_keyboard(chat_id), purpose='internal_timer_unit')
            return
        if data_str == 'itmr_backspace':
            if not is_owner_chat(chat_id):
                return
            session = _timer_input_session(chat_id)
            session['buffer'] = str(session.get('buffer') or '')[:-1]
            fast_ui_edit_message_text(chat_id, call.message.message_id, build_internal_timer_input_text(chat_id), reply_markup=build_internal_timer_input_keyboard(chat_id), purpose='internal_timer_backspace')
            return
        if data_str == 'itmr_clear':
            if not is_owner_chat(chat_id):
                return
            key = _timer_input_session(chat_id).get('key')
            _reset_timer_input_session(chat_id, key)
            fast_ui_edit_message_text(chat_id, call.message.message_id, build_internal_timer_input_text(chat_id), reply_markup=build_internal_timer_input_keyboard(chat_id), purpose='internal_timer_clear')
            return
        if data_str == 'itmr_apply':
            if not is_owner_chat(chat_id):
                return
            session = _timer_input_session(chat_id)
            key = session.get('key')
            if key not in INTERNAL_TIMER_DEFS:
                return
            total = _timer_input_total_preview(session)
            cfg = INTERNAL_TIMER_DEFS[key]
            minimum = int(cfg.get('min', 1))
            if total < minimum:
                try:
                    bot.answer_callback_query(call.id, f'Минимум: {_format_duration_short(minimum)}', show_alert=True)
                except Exception:
                    pass
                return
            value = set_internal_timer_seconds(key, total)
            bot_journal('internal_timer_changed', chat_id, f'{key}={value}')
            _reset_timer_input_session(chat_id, None)
            fast_ui_edit_message_text(chat_id, call.message.message_id, build_internal_timers_text() + f"\n\n✅ Сохранено: {cfg['label']} = {_format_duration_short(value)}", reply_markup=build_internal_timers_keyboard(chat_id), purpose='internal_timer_apply')
            return
        if data_str == 'itmr_back_info':
            if not is_owner_chat(chat_id):
                return
            _reset_timer_input_session(chat_id, None)
            fast_ui_edit_message_text(chat_id, call.message.message_id, build_info_text(chat_id), reply_markup=build_info_keyboard(chat_id), purpose='internal_timer_back_info')
            return
        if data_str == 'version_menu' or data_str.startswith('version_page:') or data_str.startswith('version_select:') or (data_str == 'version_back'):
            try:
                bot.answer_callback_query(call.id, 'Переключение версий удалено', show_alert=False)
            except Exception:
                pass
            safe_edit(bot, call, build_info_text(chat_id), reply_markup=build_info_keyboard(chat_id))
            return
        if data_str == 'keepalive_status' or data_str.startswith('keepalive_self_') or data_str.startswith('keepalive_auto_') or (data_str == 'keepalive_peer') or data_str.startswith('keepalive_peer_'):
            uid = int(getattr(getattr(call, 'from_user', None), 'id', 0) or 0)
            primary_owner = bool(int(OWNER_ID or 0) and int(chat_id) == int(OWNER_ID) and (uid == int(OWNER_ID)))
            if not primary_owner:
                try:
                    bot.answer_callback_query(call.id, 'Настройки сервера доступны только основному владельцу.', show_alert=True)
                except Exception:
                    pass
                return
            if data_str == 'keepalive_status':
                try:
                    keepalive_cancel_input(chat_id)
                except Exception:
                    pass
                fast_ui_edit_message_text(chat_id, call.message.message_id, keepalive_self_status_text(), reply_markup=build_keepalive_self_keyboard(chat_id), purpose='keepalive_self_menu')
                return
            if data_str == 'keepalive_self_toggle':
                state = set_keepalive_self_enabled(not keepalive_self_enabled())
                try:
                    bot.answer_callback_query(call.id, 'Самопеленг включён' if state else 'Самопеленг выключен')
                except Exception:
                    pass
                fast_ui_edit_message_text(chat_id, call.message.message_id, keepalive_self_status_text(), reply_markup=build_keepalive_self_keyboard(chat_id), purpose='keepalive_self_toggle')
                return
            if data_str == 'keepalive_auto_toggle':
                state = set_keepalive_auto_enabled(not keepalive_auto_enabled())
                try:
                    bot.answer_callback_query(call.id, f"Авторежим: {('✅ ВКЛ' if state else '⬜ ВЫКЛ')}")
                except Exception:
                    pass
                fast_ui_edit_message_text(chat_id, call.message.message_id, keepalive_self_status_text(), reply_markup=build_keepalive_self_keyboard(chat_id), purpose='keepalive_auto_toggle')
                return
            if data_str == 'keepalive_auto_interval':
                fast_ui_edit_message_text(chat_id, call.message.message_id, keepalive_self_status_text() + '\n\nВыберите порог без входящих запросов:', reply_markup=build_keepalive_interval_keyboard('auto', chat_id), purpose='keepalive_auto_interval')
                return
            if data_str.startswith('keepalive_auto_set:'):
                seconds = int(data_str.split(':', 1)[1])
                set_keepalive_auto_idle_seconds(seconds)
                try:
                    bot.answer_callback_query(call.id, f'Авторежим: порог {seconds // 60} мин')
                except Exception:
                    pass
                fast_ui_edit_message_text(chat_id, call.message.message_id, keepalive_self_status_text(), reply_markup=build_keepalive_self_keyboard(chat_id), purpose='keepalive_auto_interval_set')
                return
            if data_str == 'keepalive_self_interval':
                fast_ui_edit_message_text(chat_id, call.message.message_id, keepalive_self_status_text() + '\n\nВыберите интервал:', reply_markup=build_keepalive_interval_keyboard('self', chat_id), purpose='keepalive_self_interval')
                return
            if data_str.startswith('keepalive_self_set:'):
                seconds = int(data_str.split(':', 1)[1])
                set_keepalive_self_interval(seconds)
                try:
                    bot.answer_callback_query(call.id, f'Интервал: {_keepalive_fmt(seconds)}')
                except Exception:
                    pass
                fast_ui_edit_message_text(chat_id, call.message.message_id, keepalive_self_status_text(), reply_markup=build_keepalive_self_keyboard(chat_id), purpose='keepalive_self_interval_set')
                return
            if data_str == 'keepalive_self_now':
                try:
                    bot.answer_callback_query(call.id, 'Проверяю self-ping…')
                except Exception:
                    pass
                mid = int(call.message.message_id)

                def _manual_self_ping():
                    ok, detail = keepalive_ping_self_once()
                    suffix = f"\n\n{('✅' if ok else '❌')} Проверка сейчас: {detail}"
                    try:
                        fast_ui_edit_message_text(chat_id, mid, keepalive_self_status_text() + suffix, reply_markup=build_keepalive_self_keyboard(chat_id), purpose='keepalive_self_now_done')
                    except Exception as exc:
                        log_error(f'manual self ping ui: {exc}')
                pool = globals().get('BACKGROUND_TASK_POOL') or globals().get('GENERAL_TASK_POOL')
                if pool is not None and hasattr(pool, 'submit_unique'):
                    pool.submit_unique(f'keepalive-self-now:{chat_id}', _manual_self_ping)
                else:
                    _manual_self_ping()
                return
            if data_str == 'keepalive_peer':
                try:
                    keepalive_cancel_input(chat_id)
                except Exception:
                    pass
                fast_ui_edit_message_text(chat_id, call.message.message_id, keepalive_peer_status_text(), reply_markup=build_keepalive_peer_keyboard(chat_id), purpose='keepalive_peer_menu')
                return
            if data_str == 'keepalive_peer_toggle':
                if not keepalive_peer_enabled() and (not keepalive_peer_target_url()):
                    try:
                        bot.answer_callback_query(call.id, 'Сначала задайте адрес второго сервиса.', show_alert=True)
                    except Exception:
                        pass
                    return
                state = set_keepalive_peer_enabled(not keepalive_peer_enabled())
                try:
                    bot.answer_callback_query(call.id, 'Взаимный пеленг включён' if state else 'Взаимный пеленг выключен')
                except Exception:
                    pass
                fast_ui_edit_message_text(chat_id, call.message.message_id, keepalive_peer_status_text(), reply_markup=build_keepalive_peer_keyboard(chat_id), purpose='keepalive_peer_toggle')
                return
            if data_str == 'keepalive_peer_interval':
                fast_ui_edit_message_text(chat_id, call.message.message_id, keepalive_peer_status_text() + '\n\nВыберите интервал:', reply_markup=build_keepalive_interval_keyboard('peer', chat_id), purpose='keepalive_peer_interval')
                return
            if data_str.startswith('keepalive_peer_set:'):
                seconds = int(data_str.split(':', 1)[1])
                set_keepalive_peer_interval(seconds)
                try:
                    bot.answer_callback_query(call.id, f'Интервал: {_keepalive_fmt(seconds)}')
                except Exception:
                    pass
                fast_ui_edit_message_text(chat_id, call.message.message_id, keepalive_peer_status_text(), reply_markup=build_keepalive_peer_keyboard(chat_id), purpose='keepalive_peer_interval_set')
                return
            if data_str == 'keepalive_peer_url':
                keepalive_begin_peer_url_input(chat_id, int(call.message.message_id))
                kb = types.InlineKeyboardMarkup()
                kb.row(IB('❌ Отмена', callback_data='keepalive_peer_url_cancel'))
                fast_ui_edit_message_text(chat_id, call.message.message_id, wm_owner('🔗 АДРЕС ВТОРОГО RENDER\n\nОтправьте следующим сообщением полный адрес второго сервиса, например:\nhttps://my-watchdog.onrender.com\n\nЭто сообщение будет перехвачено как настройка и не попадёт в финансы/пересылку.', 9), reply_markup=kb, purpose='keepalive_peer_url_wait')
                return
            if data_str == 'keepalive_peer_url_cancel':
                keepalive_cancel_input(chat_id)
                fast_ui_edit_message_text(chat_id, call.message.message_id, keepalive_peer_status_text(), reply_markup=build_keepalive_peer_keyboard(chat_id), purpose='keepalive_peer_url_cancel')
                return
            if data_str == 'keepalive_peer_clear':
                set_keepalive_peer_enabled(False)
                set_keepalive_peer_url('')
                try:
                    bot.answer_callback_query(call.id, 'Адрес очищен, взаимный пеленг выключен')
                except Exception:
                    pass
                fast_ui_edit_message_text(chat_id, call.message.message_id, keepalive_peer_status_text(), reply_markup=build_keepalive_peer_keyboard(chat_id), purpose='keepalive_peer_clear')
                return
            if data_str == 'keepalive_peer_now':
                if not keepalive_peer_target_url():
                    try:
                        bot.answer_callback_query(call.id, 'Сначала задайте адрес второго сервиса.', show_alert=True)
                    except Exception:
                        pass
                    return
                try:
                    bot.answer_callback_query(call.id, 'Проверяю второй сервис…')
                except Exception:
                    pass
                mid = int(call.message.message_id)

                def _manual_peer_ping():
                    ok, detail = keepalive_ping_peer_once()
                    suffix = f"\n\n{('✅' if ok else '❌')} Проверка сейчас: {detail}"
                    try:
                        fast_ui_edit_message_text(chat_id, mid, keepalive_peer_status_text() + suffix, reply_markup=build_keepalive_peer_keyboard(chat_id), purpose='keepalive_peer_now_done')
                    except Exception as exc:
                        log_error(f'manual peer ping ui: {exc}')
                pool = globals().get('BACKGROUND_TASK_POOL') or globals().get('GENERAL_TASK_POOL')
                if pool is not None and hasattr(pool, 'submit_unique'):
                    pool.submit_unique(f'keepalive-peer-now:{chat_id}', _manual_peer_ping)
                else:
                    _manual_peer_ping()
                return
        if data_str == 'journal_back':
            if not is_owner_chat(chat_id):
                return
            safe_edit(bot, call, build_info_text(chat_id), reply_markup=build_info_keyboard(chat_id))
            return
        if data_str == 'forward_menu_style_toggle':
            if not is_owner_chat(chat_id):
                return
            new_state = toggle_forward_menu_new_style(chat_id)
            safe_edit(bot, call, build_info_text(chat_id) + f"\n\nМеню пересылки: {('по-новому' if new_state else 'как обычно')}", reply_markup=build_info_keyboard(chat_id))
            return
        if data_str == 'buttons_current_toggle':
            if not is_owner_chat(chat_id):
                return
            new_state = toggle_buttons_current_window(chat_id)
            safe_edit(bot, call, build_info_text(chat_id) + f"\n\nРежим кнопок в текущем окне: {('✅ ВКЛ' if new_state else '⬜ ВЫКЛ')}", reply_markup=build_info_keyboard(chat_id))
            return
        if data_str == 'icon_buttons_toggle':
            if not is_owner_chat(chat_id):
                return
            new_state = toggle_icon_button_mode(chat_id)
            safe_edit(bot, call, build_info_text(chat_id) + f"\n\nКнопки: {('значки' if new_state else 'текст')}", reply_markup=build_info_keyboard(chat_id))
            return
        if data_str == 'restore_guard_toggle':
            if not is_owner_chat(chat_id):
                return
            if RESTORE_GUARD_ACTIVE or not restore_guard_manual_override_enabled():
                count = disable_restore_guard_and_enable_mega_backups()
                note = f'Restore guard отключён вручную. MEGA autobackup включён для {count} чатов.'
            else:
                set_restore_guard_manual_override(False)
                note = 'Ручной override отключён. Guard снова сможет включиться при следующей аварийной проверке/перезапуске.'
            safe_edit(bot, call, build_info_text(chat_id) + '\n\n' + note, reply_markup=build_info_keyboard(chat_id))
            return
        if data_str == 'mega_manual_restore':
            if not is_owner_chat(chat_id):
                return
            try:
                bot.answer_callback_query(call.id, 'Запускаю восстановление из MEGA…')
            except Exception:
                pass
            _restore_pool = globals().get('RECOVERY_TASK_POOL') or globals().get('GENERAL_TASK_POOL')
            if _restore_pool is None or not _restore_pool.submit(f'manual-mega-restore:{chat_id}', run_manual_mega_restore, chat_id):
                send_and_auto_delete(chat_id, '⛔ Очередь восстановления переполнена. Попробуйте позже.', 20)
            return
        if data_str == 'total_secret_mask_toggle':
            if not is_owner_chat(chat_id):
                return
            new_state = toggle_total_secret_mask(chat_id)
            safe_edit(bot, call, build_info_text(chat_id) + f"\n\nМаскировка тотального секрета: {('✅ ВКЛ' if new_state else '⬜ ВЫКЛ')}", reply_markup=build_info_keyboard(chat_id))
            return
        if data_str == 'finance_day5_toggle':
            if not is_owner_chat(chat_id):
                return
            new_state = toggle_finance_day_start_5am(chat_id)
            safe_edit(bot, call, build_info_text(chat_id) + f"\n\nФинансовые сутки: с {('05:00' if new_state else '00:00')}", reply_markup=build_info_keyboard(chat_id))
            return
        if data_str == 'mega_priority_toggle':
            if not is_owner_chat(chat_id):
                return
            new_state = toggle_mega_backup_priority(chat_id)
            mode_text = 'сначала и сразу в MEGA' if new_state else 'как обычно'
            bot_journal('mega_priority_toggle', chat_id, f'enabled={new_state}')
            safe_edit(bot, call, build_info_text(chat_id) + f'\n\nБэкап MEGA: {mode_text}', reply_markup=build_info_keyboard(chat_id))
            return
        if data_str in {'excel_style_toggle', 'excel_style_menu'}:
            if not is_owner_chat(chat_id):
                return
            mode = toggle_excel_interface_mode(chat_id)
            bot_journal('excel_interface_toggle', chat_id, f'mode={mode}')
            try:
                bot.answer_callback_query(call.id, 'Excel по новому' if mode == 'new' else 'Excel по старому', show_alert=False)
            except Exception:
                pass
            safe_edit(bot, call, build_info_text(chat_id), reply_markup=build_info_keyboard(chat_id))
            return
        if data_str.startswith('excel_style_set:'):
            if not is_owner_chat(chat_id):
                return
            selected = data_str.split(':', 1)[1].strip().lower()
            mode = set_excel_table_style(chat_id, selected)
            bot_journal('excel_style_set', chat_id, f'mode={mode}')
            try:
                bot.answer_callback_query(call.id, f'Excel: {excel_table_style_caption(chat_id)}', show_alert=False)
            except Exception:
                pass
            safe_edit(bot, call, build_excel_style_text(chat_id), reply_markup=build_excel_style_keyboard(chat_id))
            return
        if data_str == 'info_instruction':
            if not is_owner_chat(chat_id):
                try:
                    bot.answer_callback_query(call.id, 'Только для владельца', show_alert=True)
                except Exception:
                    pass
                return
            safe_edit(bot, call, build_owner_instruction_text(), reply_markup=build_owner_instruction_keyboard(chat_id))
            return
        if data_str == 'info_delta_status':
            if not is_owner_chat(chat_id):
                return
            kbd = types.InlineKeyboardMarkup()
            kbd.row(IB('🔄 Обновить', callback_data='info_delta_status'))
            kbd.row(IB('🔙 Назад в Инфо', callback_data=f"d:{get_chat_store(chat_id).get('current_view_day', today_key())}:info"))
            safe_edit(bot, call, delta_status_text(), reply_markup=kbd)
            return
        if data_str.startswith('traffic_audit:') or data_str == 'traffic_audit':
            if not is_owner_chat(chat_id):
                return
            scope = data_str.split(':', 1)[1] if ':' in data_str else 'month'
            if scope not in {'month', 'today', 'process', 'all'}:
                scope = 'month'
            kbt = types.InlineKeyboardMarkup(row_width=3)
            kbt.row(IB('📅 Месяц', callback_data='traffic_audit:month'), IB('Сегодня', callback_data='traffic_audit:today'), IB('Процесс', callback_data='traffic_audit:process'))
            kbt.row(IB('🔄 Обновить', callback_data=f'traffic_audit:{scope}'), IB('🖥 Watcher', callback_data='runtime_watcher'))
            kbt.row(IB('🔙 Назад в Инфо', callback_data=f"d:{get_chat_store(chat_id).get('current_view_day', today_key())}:info"), IB('❌ Закрыть', callback_data='info_close'))
            text = traffic_audit_text(scope) if 'traffic_audit_text' in globals() else '📶 Аудит трафика недоступен.'
            safe_edit(bot, call, text, reply_markup=kbt)
            return
        if data_str == 'runtime_watcher':
            if not is_owner_chat(chat_id):
                return
            kbw = types.InlineKeyboardMarkup(row_width=2)
            kbw.row(IB('🔄 Обновить', callback_data='runtime_watcher'), IB('📜 События', callback_data='runtime_events'))
            kbw.row(IB('☁️ Снимок Watcher в MEGA', callback_data='runtime_snapshot_now'))
            kbw.row(IB('📦 Runtime ZIP', callback_data='runtime_export'), IB('📶 Трафик', callback_data='traffic_audit:month'))
            kbw.row(IB('🚦 Очереди', callback_data='info_queues'), IB('🧩 Delta', callback_data='info_delta_status'))
            kbw.row(IB('🔙 Назад в Инфо', callback_data=f"d:{get_chat_store(chat_id).get('current_view_day', today_key())}:info"), IB('❌ Закрыть', callback_data='info_close'))
            safe_edit(bot, call, build_runtime_watcher_text(), reply_markup=kbw)
            return
        if data_str == 'runtime_events':
            if not is_owner_chat(chat_id):
                return
            kbe = types.InlineKeyboardMarkup(row_width=2)
            kbe.row(IB('🔄 Обновить', callback_data='runtime_events'), IB('🖥 Watcher', callback_data='runtime_watcher'))
            kbe.row(IB('🔙 Назад в Инфо', callback_data=f"d:{get_chat_store(chat_id).get('current_view_day', today_key())}:info"), IB('❌ Закрыть', callback_data='info_close'))
            safe_edit(bot, call, build_runtime_events_text(), reply_markup=kbe)
            return
        if data_str == 'runtime_export':
            if not is_owner_chat(chat_id):
                return
            ok, info = submit_interactive_file_job(chat_id, 'runtime', 'Runtime / Watcher ZIP', send_runtime_export_zip, chat_id, None, None)
            try:
                bot.answer_callback_query(call.id, build_all_processes_toast(chat_id) if ok else info[:180], show_alert=False)
            except Exception:
                pass
            return
        if data_str == 'runtime_snapshot_now':
            if not is_owner_chat(chat_id):
                return
            ok = GENERAL_TASK_POOL.submit('runtime-manual-snapshot', runtime_upload_snapshot, 'manual', True)
            try:
                bot.answer_callback_query(call.id, 'Снимок Watcher поставлен в MEGA-очередь' if ok else 'Очередь занята', show_alert=False)
            except Exception:
                pass
            kbw = types.InlineKeyboardMarkup(row_width=2)
            kbw.row(IB('🔄 Обновить', callback_data='runtime_watcher'), IB('📜 События', callback_data='runtime_events'))
            kbw.row(IB('📦 Runtime ZIP', callback_data='runtime_export'))
            kbw.row(IB('🔙 Назад в Инфо', callback_data=f"d:{get_chat_store(chat_id).get('current_view_day', today_key())}:info"))
            safe_edit(bot, call, build_runtime_watcher_text(), reply_markup=kbw)
            return
        if data_str == 'info_queues':
            if not is_owner_chat(chat_id):
                try:
                    bot.answer_callback_query(call.id, 'Только для владельца', show_alert=True)
                except Exception:
                    pass
                return
            kbq = types.InlineKeyboardMarkup()
            kbq.row(IB('🔄 Обновить', callback_data='info_queues'))
            if mega_tasks_active():
                kbq.row(IB('☁️ Проверить MEGA-задачи', callback_data='mega_tasks_check'))
                kbq.row(IB('▶️ Поднять pending/running', callback_data='mega_tasks_recover'))
                if mega_task_registry_stats().get('failed', 0):
                    kbq.row(IB('🔁 Повторить до 20 ошибок', callback_data='mega_tasks_retry_failed'))
            kbq.row(IB('🔙 Назад в Инфо', callback_data=f"d:{get_chat_store(chat_id).get('current_view_day', today_key())}:info"))
            safe_edit(bot, call, build_queue_status_text(), reply_markup=kbq)
            return
        if data_str == 'mega_tasks_check':
            if not is_owner_chat(chat_id):
                return
            mega_task_refresh_registry()
            kbq = types.InlineKeyboardMarkup()
            kbq.row(IB('🔄 Обновить', callback_data='info_queues'))
            kbq.row(IB('▶️ Поднять pending/running', callback_data='mega_tasks_recover'))
            if mega_task_registry_stats().get('failed', 0):
                kbq.row(IB('🔁 Повторить до 20 ошибок', callback_data='mega_tasks_retry_failed'))
            kbq.row(IB('🔙 Назад в Инфо', callback_data=f"d:{get_chat_store(chat_id).get('current_view_day', today_key())}:info"))
            safe_edit(bot, call, build_queue_status_text(), reply_markup=kbq)
            return
        if data_str == 'mega_tasks_recover':
            if not is_owner_chat(chat_id):
                return
            schedule_mega_task_recovery(0.1)
            try:
                bot.answer_callback_query(call.id, 'Проверка и восстановление поставлены в очередь')
            except Exception:
                pass
            return
        if data_str == 'mega_tasks_retry_failed':
            if not is_owner_chat(chat_id):
                return
            moved = mega_task_requeue_failed(20)
            try:
                bot.answer_callback_query(call.id, f'Возвращено в pending: {moved}')
            except Exception:
                pass
            return
        if data_str == 'info_finance_off':
            try:
                if is_finance_mode(chat_id):
                    set_finance_window_mode(chat_id, 'off', persist_now=False)
                    delete_auto_finance_windows_for_chat(chat_id, persist_now=False)
                    set_hidden_finance_mode(chat_id, False)
                    set_finance_mode(chat_id, False)
                    state_text = 'выключен'
                else:
                    set_finance_mode(chat_id, True)
                    set_finance_window_mode(chat_id, 'off', persist_now=False)
                    set_hidden_finance_mode(chat_id, True)
                    delete_auto_finance_windows_for_chat(chat_id, persist_now=False)
                    state_text = 'включён (скрытые финансы ВКЛ)'
                _persist_finance_window_mode_critical(chat_id)
                try:
                    schedule_contour_home_after_mode_change(chat_id, 'info_finance_toggle', 0.2)
                except Exception:
                    pass
                open_info_window(chat_id)
                bot.answer_callback_query(call.id, f'Фин режим {state_text}', show_alert=False)
            except Exception as e:
                log_error(f'info_finance_off({chat_id}): {e}')
            return
        if data_str == 'info_close':
            v177_delete_message_async(chat_id, call.message.message_id, purpose='info_close')
            _clear_stored_window(chat_id, 'info_msg_id', call.message.message_id)
            return
        if data_str.startswith('fv:'):
            if not is_owner_chat(chat_id):
                return
            try:
                _, target_s, view_day, action, owner_day_key = data_str.split(':', 4)
                target_chat_id = int(target_s)
            except Exception:
                return
            target_store = get_chat_store(target_chat_id)
            target_store['current_view_day'] = view_day
            registry_action = action
            if action == 'clear_delete_back':
                registry_action = 'open'
            elif action.startswith('del_toggle_') or action == 'del_selected':
                registry_action = 'edit_list'
            if registry_action in {'open', 'back_main', 'menu', 'calendar', 'report', 'usd_month', 'total', 'info', 'edit_list', 'csv_menu'}:
                register_open_window(chat_id, call.message.message_id, 'fin_view', code=f'fv:{registry_action}', day_key=view_day, params={'target_chat_id': target_chat_id, 'owner_day_key': owner_day_key, 'view_action': registry_action})
            if action == 'clear_delete_back':
                clear_edit_delete_selection(target_chat_id, view_day)
                clear_usd_edit_delete_selection(target_chat_id, view_day)
                safe_edit(bot, call, render_fin_window_text(target_chat_id, view_day), reply_markup=build_fin_window_view_keyboard(target_chat_id, view_day, owner_day_key), parse_mode='HTML')
                return
            if action in {'open', 'back_main', 'menu'}:
                clear_edit_delete_selection(target_chat_id, view_day)
                clear_usd_edit_delete_selection(target_chat_id, view_day)
                safe_edit(bot, call, render_fin_window_text(target_chat_id, view_day), reply_markup=build_fin_window_view_keyboard(target_chat_id, view_day, owner_day_key), parse_mode='HTML')
                return
            if action == 'menu':
                clear_edit_delete_selection(target_chat_id, view_day)
                safe_edit(bot, call, render_fin_window_text(target_chat_id, view_day), reply_markup=build_fin_window_menu_keyboard(target_chat_id, view_day, owner_day_key), parse_mode='HTML')
                return
            if action == 'calendar':
                try:
                    cdt = datetime.strptime(view_day, '%Y-%m-%d')
                except Exception:
                    cdt = now_local()
                safe_edit(bot, call, f'📅 Календарь: {html.escape(get_chat_display_name(target_chat_id))}', reply_markup=build_fin_calendar_keyboard(target_chat_id, cdt, owner_day_key), parse_mode='HTML')
                return
            if action == 'report':
                try:
                    month_key = datetime.strptime(view_day, '%Y-%m-%d').strftime('%Y-%m')
                except Exception:
                    month_key = now_local().strftime('%Y-%m')
                report_html, _ = build_month_report_text(target_chat_id, month_key)
                safe_edit(bot, call, f'👁 {html.escape(get_chat_display_name(target_chat_id))}\n' + report_html, reply_markup=_one_button_keyboard('🔙 Назад', f'fv:{target_chat_id}:{view_day}:open:{owner_day_key}'), parse_mode='HTML')
                return
            if action == 'usd_month':
                if not usd_transactions_view_enabled(target_chat_id):
                    try:
                        bot.answer_callback_query(call.id, 'В этом чате не включены 💵 USD операции', show_alert=True)
                    except Exception:
                        pass
                    return
                month_html, _ = render_usd_month_window(target_chat_id, view_day)
                safe_edit(bot, call, f'👁 {html.escape(get_chat_display_name(target_chat_id))}\n' + month_html, reply_markup=build_fin_window_usd_month_keyboard(target_chat_id, view_day, owner_day_key), parse_mode='HTML')
                return
            if action == 'total':
                if usd_transactions_view_enabled(target_chat_id):
                    bal = usd_balance_for_chat(target_chat_id)
                    shown = f"{('+' if bal >= 0 else '-')}${fmt_num_plain(abs(bal))}"
                    text = f'👁 {html.escape(get_chat_display_name(target_chat_id))}\n\n💵 Общий итог по чату: {shown}'
                else:
                    text = f"👁 {html.escape(get_chat_display_name(target_chat_id))}\n\n💰 Общий итог по чату: {format_chat_amount(target_chat_id, target_store.get('balance', 0), True)}"
                safe_edit(bot, call, text, reply_markup=build_fin_window_view_keyboard(target_chat_id, view_day, owner_day_key), parse_mode='HTML')
                return
            if action == 'info':
                kb_info = build_fin_window_view_keyboard(target_chat_id, view_day, owner_day_key)
                safe_edit(bot, call, build_info_text(target_chat_id) + '\n\n' + build_articles_description_text(target_chat_id), reply_markup=kb_info)
                return
            if action == 'reset':
                owner_store = get_chat_store(chat_id)
                owner_store['finwin_reset_wait'] = {'type': 'finwin_reset', 'target_chat_id': target_chat_id, 'owner_day_key': owner_day_key, 'fin_window_msg_id': call.message.message_id, 'expires_at': time.time() + 20}
                save_data(data)
                send_and_auto_delete(chat_id, f'⚠️ Обнулить данные чата {get_chat_display_name(target_chat_id)}? Напишите ДА в течение 20 секунд или ОТМЕНА.', 20)
                return
            if action == 'cancel_edit':
                clear_finwin_edit_wait_state(chat_id, call.message.message_id, delete_prompt=True)
                try:
                    bot.answer_callback_query(call.id, 'Редактирование отменено')
                except Exception:
                    pass
                return
            if action == 'edit_list':
                if usd_transactions_view_enabled(target_chat_id):
                    day_recs = usd_records_for_day(target_chat_id, view_day)
                    edit_kb = build_usd_edit_records_keyboard(view_day, target_chat_id, prefix='fv', owner_day_key=owner_day_key)
                    empty_text = 'Нет USD-записей за этот день.'
                else:
                    day_recs = target_store.get('daily_records', {}).get(view_day, [])
                    edit_kb = build_edit_records_keyboard(view_day, target_chat_id, prefix='fv', owner_day_key=owner_day_key)
                    empty_text = 'Нет записей за этот день.'
                if not day_recs:
                    send_and_auto_delete(chat_id, empty_text, 8)
                    return
                safe_edit(bot, call, render_fin_window_text(target_chat_id, view_day), reply_markup=edit_kb, parse_mode='HTML')
                return
            if action.startswith('del_toggle_'):
                rid = int(action.split('_')[-1])
                if usd_transactions_view_enabled(target_chat_id):
                    toggle_usd_edit_delete_selection(target_chat_id, view_day, rid)
                    edit_kb = build_usd_edit_records_keyboard(view_day, target_chat_id, prefix='fv', owner_day_key=owner_day_key)
                else:
                    toggle_edit_delete_selection(target_chat_id, view_day, rid)
                    edit_kb = build_edit_records_keyboard(view_day, target_chat_id, prefix='fv', owner_day_key=owner_day_key)
                safe_edit(bot, call, render_fin_window_text(target_chat_id, view_day), reply_markup=edit_kb, parse_mode='HTML')
                return
            if action == 'del_selected':
                if usd_transactions_view_enabled(target_chat_id):
                    count = delete_selected_usd_records(target_chat_id, view_day)
                    edit_kb = build_usd_edit_records_keyboard(view_day, target_chat_id, prefix='fv', owner_day_key=owner_day_key)
                    notice = f'🗑 Удалено USD-записей: {count}'
                else:
                    count = delete_selected_records(target_chat_id, view_day)
                    edit_kb = build_edit_records_keyboard(view_day, target_chat_id, prefix='fv', owner_day_key=owner_day_key)
                    notice = f'🗑 Удалено записей: {count}'
                safe_edit(bot, call, render_fin_window_text(target_chat_id, view_day), reply_markup=edit_kb, parse_mode='HTML')
                send_and_auto_delete(chat_id, notice, 8)
                return
            if action.startswith('edit_rec_'):
                rid = int(action.split('_')[-1])
                rec = next((r for r in target_store.get('records', []) if int(r.get('id', -1)) == rid), None)
                if not rec:
                    send_and_auto_delete(chat_id, '❌ Запись не найдена.', 8)
                    return
                usd_mode = usd_transactions_view_enabled(target_chat_id)
                if usd_mode:
                    usd_amount = float(rec.get('usd_amount', 0) or 0)
                    if not usd_amount:
                        send_and_auto_delete(chat_id, '❌ USD-часть записи не найдена.', 8)
                        return
                    usd_note = str(rec.get('usd_note') or rec.get('note') or '')
                    sid = str(rec.get('usd_short_id') or f'U{rid}')
                    insert_value = compose_usd_edit_insert_value(target_chat_id, rid, view_day, usd_amount, usd_note)
                    current_line = f"{('+' if usd_amount >= 0 else '-')}${fmt_num_plain(abs(usd_amount))} {usd_note}".rstrip()
                    title_line = f'✏️ Редактирование USD-записи {sid}'
                else:
                    insert_value = compose_edit_input_value(rec.get('amount'), rec.get('note', ''))
                    current_line = f"{fmt_num(rec['amount'])} {rec.get('note', '')}".rstrip()
                    title_line = f"✏️ Редактирование записи {rec.get('short_id') or 'R' + str(rid)}"
                prompt_text = wm_owner(f'{title_line}\n👁 Чат: {get_chat_display_name(target_chat_id)}\n\nТекущие данные:\n{current_line}\n\n✍️ Напишите новые данные или нажмите «Вставить текущее значение».\n⏳ Это сообщение и режим редактирования будут автоматически отменены через 40 секунд.', 17)
                owner_store = get_chat_store(chat_id)
                prompt_id = send_or_edit_edit_prompt(chat_id, 'finwin_edit_wait', prompt_text, reply_markup=build_finwin_cancel_edit_keyboard(target_chat_id, view_day, owner_day_key, insert_text=insert_value))
                owner_store['finwin_edit_wait'] = {'type': 'finwin_edit', 'target_chat_id': target_chat_id, 'rid': rid, 'day_key': view_day, 'owner_day_key': owner_day_key, 'prompt_msg_id': prompt_id, 'fin_window_msg_id': call.message.message_id, 'insert_text': insert_value, 'usd_mode': bool(usd_mode), 'countdown_base_text': prompt_text, 'expires_at': time.time() + 40}
                if callable(globals().get('_v262_schedule_transient_chat_persist')):
                    _v262_schedule_transient_chat_persist(chat_id)
                schedule_cancel_finwin_edit(chat_id, prompt_id, delay=None)
                return
            if action == 'csv_menu':
                safe_edit(bot, call, wm_common(f'📂 CSV / Excel: {html.escape(get_chat_display_name(target_chat_id))}\nВыберите период:', 5), reply_markup=build_fin_window_csv_menu(target_chat_id, view_day, owner_day_key), parse_mode='HTML')
                return
            if action in {'bk_chat', 'bk_channel', 'bk_mega'}:
                target = action.replace('bk_', '')
                set_backup_target_enabled(target_chat_id, target, not is_backup_target_enabled(target_chat_id, target))
                safe_edit(bot, call, wm_common(f'📂 CSV / Excel: {html.escape(get_chat_display_name(target_chat_id))}\nВыберите период:', 5), reply_markup=build_fin_window_csv_menu(target_chat_id, view_day, owner_day_key), parse_mode='HTML')
                return
            if action in {'csv_all', 'csv_day', 'csv_week', 'csv_month', 'csv_wedthu', 'xlsx_all', 'xlsx_day', 'xlsx_week', 'xlsx_month', 'xlsx_wedthu', 'xlsxstat_all', 'xlsxstat_day', 'xlsxstat_week', 'xlsxstat_month', 'xlsxstat_wedthu'}:
                if action.startswith('xlsxstat_'):
                    file_type = 'xlsxstat'
                    mode = action.replace('xlsxstat_', '', 1)
                else:
                    file_type = 'xlsx' if action.startswith('xlsx_') else 'csv'
                    mode = action.replace('csv_', '').replace('xlsx_', '')
                ok, info = submit_interactive_file_job(chat_id, 'period_export', f"{('Excel' if file_type.startswith('xlsx') else 'CSV')} экспорт", send_export_for_chat_to, chat_id, target_chat_id, mode, view_day, file_type)
                try:
                    bot.answer_callback_query(call.id, build_all_processes_toast(chat_id) if ok else info[:180], show_alert=False)
                except Exception:
                    pass
                return
            return
        if data_str.startswith('exp_'):
            try:
                register_static_open_view(chat_id, call.message.message_id, code=data_str.split(':', 1)[0], day_key=get_chat_store(chat_id).get('current_view_day') or today_key(), params={'source': 'exact_export'})
            except Exception:
                pass
        if data_str.startswith('exp_style_period:'):
            try:
                _, scope, target_s, mode, file_type, day_key_s, owner_day_key = data_str.split(':')
                target_chat_id = chat_id if scope == 'd' or int(target_s or 0) == 0 else int(target_s)
                kind_label = 'Excel статьи' if file_type == 'xlsxstat' else 'Excel'
                safe_edit(bot, call, f'📊 {kind_label}\nПериод: {mode}\n\n' + ('Настройки включаются галочками:' if excel_interface_mode(target_chat_id) == 'new' else 'Выберите способ получения:'), reply_markup=_period_excel_style_keyboard(scope, target_chat_id, mode, file_type, day_key_s, owner_day_key))
            except Exception as e:
                log_error(f'exp_style_period: {e}')
            return
        if data_str.startswith('exp_new_period_toggle:'):
            try:
                _, scope, target_s, mode, file_type, option, day_key_s, owner_day_key = data_str.split(':')
                target_chat_id = chat_id if scope == 'd' or int(target_s or 0) == 0 else int(target_s)
                options = toggle_excel_new_export_option(option)
                safe_edit(bot, call, f'📊 Excel по новому\\nПериод: {mode}\\n\\nНастройки включаются галочками:', reply_markup=_period_excel_style_keyboard(scope, target_chat_id, mode, file_type, day_key_s, owner_day_key))
                try:
                    bot.answer_callback_query(call.id, 'Настройка обновлена', show_alert=False)
                except Exception:
                    pass
            except Exception as e:
                log_error(f'exp_new_period_toggle: {e}')
            return
        if data_str.startswith('exp_excel_dollar_toggle:'):
            try:
                _, scope, target_s, mode, file_type, day_key_s, owner_day_key = data_str.split(':')
                target_chat_id = chat_id if scope == 'd' or int(target_s or 0) == 0 else int(target_s)
                enabled = toggle_excel_usd_table_enabled(target_chat_id)
                kind_label = 'Excel статьи' if file_type == 'xlsxstat' else 'Excel'
                safe_edit(bot, call, f'📊 {kind_label}\nПериод: {mode}\n\n' + ('Настройки включаются галочками:' if excel_interface_mode(target_chat_id) == 'new' else 'Выберите способ получения:'), reply_markup=_period_excel_style_keyboard(scope, target_chat_id, mode, file_type, day_key_s, owner_day_key))
                try:
                    bot.answer_callback_query(call.id, f"USD в таблице: {('✅ ВКЛ' if enabled else '⬜ ВЫКЛ')}", show_alert=False)
                except Exception:
                    pass
            except Exception as e:
                log_error(f'exp_excel_dollar_toggle: {e}')
            return
        if data_str.startswith('exp_new_period_send:'):
            try:
                _, scope, target_s, mode, file_type, delivery, day_key_s, owner_day_key = data_str.split(':')
                target_chat_id = chat_id if scope == 'd' or int(target_s or 0) == 0 else int(target_s)
                options = normalize_excel_export_options(excel_new_export_options())
                ok, info = submit_interactive_file_job(chat_id, 'period_export', 'Google Excel' if delivery == 'google' else 'Excel по новому', send_export_for_chat_to, chat_id, target_chat_id, mode, day_key_s, file_type, None, options, delivery)
                try:
                    bot.answer_callback_query(call.id, build_all_processes_toast(chat_id) if ok else info[:180], show_alert=False)
                except Exception:
                    pass
            except Exception as e:
                log_error(f'exp_new_period_send: {e}')
            return
        if data_str.startswith('exp_send_period_style:'):
            try:
                _, scope, target_s, mode, file_type, style, day_key_s, owner_day_key = data_str.split(':')
                target_chat_id = chat_id if scope == 'd' or int(target_s or 0) == 0 else int(target_s)
                ok, info = submit_interactive_file_job(chat_id, 'period_export', f'{_export_style_caption(style)}', send_export_for_chat_to, chat_id, target_chat_id, mode, day_key_s, file_type, style)
                try:
                    bot.answer_callback_query(call.id, build_all_processes_toast(chat_id) if ok else info[:180], show_alert=False)
                except Exception:
                    pass
            except Exception as e:
                log_error(f'exp_send_period_style: {e}')
            return
        if data_str.startswith('exp_style_exact:'):
            try:
                _, start_key, start_rid, end_key, end_rid, file_type, return_day_key = data_str.split(':')
                kind_label = 'Excel статьи' if file_type == 'xlsxstat' else 'Excel'
                safe_edit(bot, call, f'🎯 {kind_label} — точный период\n\n' + ('Настройки включаются галочками:' if excel_interface_mode(chat_id) == 'new' else 'Выберите способ получения:'), reply_markup=_exact_excel_style_keyboard(start_key, int(start_rid), end_key, int(end_rid), file_type, return_day_key))
            except Exception as e:
                log_error(f'exp_style_exact: {e}')
            return
        if data_str.startswith('exp_new_exact_toggle:'):
            try:
                _, start_key, start_rid, end_key, end_rid, file_type, option, return_day_key = data_str.split(':')
                toggle_excel_new_export_option(option)
                safe_edit(bot, call, '🎯 Excel по новому — точный период\\n\\nНастройки включаются галочками:', reply_markup=_exact_excel_style_keyboard(start_key, int(start_rid), end_key, int(end_rid), file_type, return_day_key))
                try:
                    bot.answer_callback_query(call.id, 'Настройка обновлена', show_alert=False)
                except Exception:
                    pass
            except Exception as e:
                log_error(f'exp_new_exact_toggle: {e}')
            return
        if data_str.startswith('exp_new_exact_send:'):
            try:
                _, start_key, start_rid, end_key, end_rid, file_type, delivery, return_day_key = data_str.split(':')
                options = normalize_excel_export_options(excel_new_export_options())
                ok, info = submit_interactive_file_job(chat_id, 'exact_export', 'Google Excel точный' if delivery == 'google' else 'Excel по новому точный', send_exact_range_export, chat_id, chat_id, start_key, int(start_rid), end_key, int(end_rid), file_type, None, options, delivery)
                try:
                    bot.answer_callback_query(call.id, build_all_processes_toast(chat_id) if ok else info[:180], show_alert=False)
                except Exception:
                    pass
            except Exception as e:
                log_error(f'exp_new_exact_send: {e}')
            return
        if data_str.startswith('exp_send_exact_style:'):
            try:
                _, start_key, start_rid, end_key, end_rid, file_type, style, return_day_key = data_str.split(':')
                ok, info = submit_interactive_file_job(chat_id, 'exact_export', f'Точный {_export_style_caption(style)}', send_exact_range_export, chat_id, chat_id, start_key, int(start_rid), end_key, int(end_rid), file_type, style)
                try:
                    bot.answer_callback_query(call.id, build_all_processes_toast(chat_id) if ok else info[:180], show_alert=False)
                except Exception:
                    pass
            except Exception as e:
                log_error(f'exp_send_exact_style: {e}')
            return
        if data_str.startswith('exp_pick_start:'):
            try:
                _, y, m, return_day_key = data_str.split(':')
                y, m = (int(y), int(m))
                safe_edit(bot, call, f'🎯 Точный CSV / Excel\nВыберите начальную дату: {russian_month_name(m)} {y}', reply_markup=_export_calendar_start_keyboard(y, m, return_day_key, chat_id))
            except Exception as e:
                log_error(f'exp_pick_start: {e}')
            return
        if data_str.startswith('exp_pick_set_start:'):
            try:
                _, y, m, d, return_day_key = data_str.split(':')
                start_key = _date_key_from_ymd(int(y), int(m), int(d))
                store = get_chat_store(chat_id)
                safe_edit(bot, call, f'🎯 Точное начало экспорта\n📅 День: {fmt_date_ddmmyy(start_key)}\n\nВыберите расход, с которого начинать файл, или продолжите с начала дня.', reply_markup=_export_start_record_keyboard(chat_id, start_key, return_day_key))
            except Exception as e:
                log_error(f'exp_pick_set_start: {e}')
            return
        if data_str.startswith('exp_pick_start_record:'):
            try:
                _, start_key, start_rid, return_day_key = data_str.split(':')
                start_dt = datetime.strptime(start_key, '%Y-%m-%d')
                store = get_chat_store(chat_id)
                safe_edit(bot, call, f'🎯 Точный CSV / Excel\n▶️ Начало: {exact_boundary_text(store, start_key, int(start_rid), True)}\n\nВыберите конечную дату:', reply_markup=_export_end_calendar_keyboard(start_key, int(start_rid), start_dt.year, start_dt.month, return_day_key, chat_id))
            except Exception as e:
                log_error(f'exp_pick_start_record: {e}')
            return
        if data_str.startswith('exp_pick_end:'):
            try:
                _, start_key, start_rid, y, m, return_day_key = data_str.split(':')
                store = get_chat_store(chat_id)
                safe_edit(bot, call, f'🎯 Точный CSV / Excel\n▶️ Начало: {exact_boundary_text(store, start_key, int(start_rid), True)}\n\nВыберите конечную дату: {russian_month_name(int(m))} {int(y)}', reply_markup=_export_end_calendar_keyboard(start_key, int(start_rid), int(y), int(m), return_day_key, chat_id))
            except Exception as e:
                log_error(f'exp_pick_end: {e}')
            return
        if data_str.startswith('exp_pick_set_end:'):
            try:
                _, start_key, start_rid, y, m, d, return_day_key = data_str.split(':')
                end_key = _date_key_from_ymd(int(y), int(m), int(d))
                store = get_chat_store(chat_id)
                safe_edit(bot, call, f'🎯 Точный конец экспорта\n▶️ Начало: {exact_boundary_text(store, start_key, int(start_rid), True)}\n📅 Конечный день: {fmt_date_ddmmyy(end_key)}\n\nВыберите последний расход, который включить в файл, или продолжите до конца дня.', reply_markup=_export_end_record_keyboard(chat_id, start_key, int(start_rid), end_key, return_day_key))
            except Exception as e:
                log_error(f'exp_pick_set_end: {e}')
            return
        if data_str.startswith('exp_pick_end_record:'):
            try:
                _, start_key, start_rid, end_key, end_rid, return_day_key = data_str.split(':')
                store = get_chat_store(chat_id)
                text = f'🎯 Точный период выбран\n\n▶️ {exact_boundary_text(store, start_key, int(start_rid), True)}\n⏹ {exact_boundary_text(store, end_key, int(end_rid), False)}\n\nВыберите формат файла:'
                safe_edit(bot, call, text, reply_markup=_export_format_keyboard(start_key, int(start_rid), end_key, int(end_rid), return_day_key))
            except Exception as e:
                log_error(f'exp_pick_end_record: {e}')
            return
        if data_str.startswith('exp_send:'):
            try:
                _, start_key, start_rid, end_key, end_rid, file_type, return_day_key = data_str.split(':')
                ok, info = submit_interactive_file_job(chat_id, 'exact_export', f'Точный экспорт {str(file_type).upper()}', send_exact_range_export, chat_id, chat_id, start_key, int(start_rid), end_key, int(end_rid), file_type)
                try:
                    bot.answer_callback_query(call.id, build_all_processes_toast(chat_id) if ok else info[:180], show_alert=False)
                except Exception:
                    pass
            except Exception as e:
                log_error(f'exp_send: {e}')
            return
        if not data_str.startswith('d:'):
            return
        _, day_key, cmd = data_str.split(':', 2)
        store = get_chat_store(chat_id)
        if cmd != 'open':
            try:
                fn = globals().get('canonical_main_day')
                if callable(fn):
                    day_key = str(fn(chat_id))[:10]
            except Exception:
                pass
        if cmd.startswith('removed_'):
            try:
                removed_chat_id = int(cmd.rsplit('_', 1)[1])
            except Exception:
                return
            answer_removed_chat(call, removed_chat_id)
            return
        if cmd in {'open', 'prev', 'next', 'today'}:
            if cmd == 'open':
                nd = day_key
                clear_edit_delete_selection(chat_id, day_key)
            elif cmd == 'today':
                nd = today_key()
            else:
                try:
                    fn = globals().get('canonical_main_day')
                    base_day_key = str(fn(chat_id) if callable(fn) else store.get('current_view_day') or day_key)[:10]
                except Exception:
                    base_day_key = str(store.get('current_view_day') or day_key)[:10]
                shift = -1 if cmd == 'prev' else 1
                nd = (datetime.strptime(base_day_key, '%Y-%m-%d') + timedelta(days=shift)).strftime('%Y-%m-%d')
            store['current_view_day'] = nd
            render_started = time.monotonic()
            txt, _ = render_day_window(chat_id, nd)
            kb = build_main_keyboard(nd, chat_id)
            try:
                stage = globals().get('v177_perf_stage')
                if callable(stage):
                    stage('main_day_render', time.monotonic() - render_started)
            except Exception:
                pass
            safe_edit(bot, call, txt, reply_markup=kb, parse_mode='HTML')
            set_active_window_id(chat_id, nd, call.message.message_id)
            schedule_balance_panel_refresh(chat_id, 0.1)
            return
        if cmd == 'usd_tx_toggle':
            try:
                clear_edit_delete_selection(chat_id, day_key)
                clear_usd_edit_delete_selection(chat_id, day_key)
            except Exception:
                pass
            enabled = toggle_usd_transactions_view(chat_id)
            store['current_view_day'] = day_key
            txt, _ = render_day_window(chat_id, day_key)
            safe_edit(bot, call, txt, reply_markup=build_main_keyboard(day_key, chat_id), parse_mode='HTML')
            try:
                bot.answer_callback_query(call.id, 'USD операции' if enabled else 'ARS операции', show_alert=False)
            except Exception:
                pass
            return
        if cmd == 'usd_month':
            if not usd_transactions_view_enabled(chat_id):
                try:
                    bot.answer_callback_query(call.id, 'Сначала включите 💵 USD операции', show_alert=True)
                except Exception:
                    pass
                return
            month_html, _ = render_usd_month_window(chat_id, day_key)
            safe_edit(bot, call, month_html, reply_markup=build_usd_month_keyboard(day_key), parse_mode='HTML')
            register_open_window(chat_id, call.message.message_id, 'local_fin_view', code='usd_month', day_key=day_key, params={'view_action': 'usd_month', 'month_day': day_key})
            return
        if cmd == 'calendar':
            try:
                cdt = datetime.strptime(day_key, '%Y-%m-%d')
            except Exception:
                cdt = now_local()
            kb = build_calendar_keyboard(cdt, chat_id)
            safe_edit(bot, call, calendar_window_text(cdt), reply_markup=kb)
            register_open_window(chat_id, call.message.message_id, 'local_fin_view', code='calendar', day_key=day_key, params={'view_action': 'calendar', 'center_day': cdt.strftime('%Y-%m-%d')})
            return
        if cmd == 'report':
            try:
                month_key = datetime.strptime(day_key, '%Y-%m-%d').strftime('%Y-%m')
            except Exception:
                month_key = now_local().strftime('%Y-%m')
            if chat_buttons_current_window_enabled(chat_id):
                report_html, _ = build_month_report_text(chat_id, month_key)
                safe_edit(bot, call, report_html, reply_markup=build_report_keyboard(month_key), parse_mode='HTML')
                register_open_window(chat_id, call.message.message_id, 'local_fin_view', code='report', day_key=day_key, params={'view_action': 'report', 'month_key': month_key})
            else:
                open_report_window(chat_id, month_key)
            return
        if cmd == 'total':
            view_usd = usd_transactions_view_enabled(chat_id)
            chat_bal = usd_balance_for_chat(chat_id) if view_usd else store.get('balance', 0)
            if not is_owner_chat(chat_id):
                if view_usd:
                    usd_text = f"{('+' if chat_bal >= 0 else '-')}${fmt_num_plain(abs(chat_bal))}"
                    text = wm_common(f'💵 Общий итог по этому чату: {usd_text}', 4)
                else:
                    text = wm_common(f'💰 Общий итог по этому чату: {format_chat_amount(chat_id, chat_bal, True)}', 4)
                if chat_buttons_current_window_enabled(chat_id):
                    safe_edit(bot, call, text, parse_mode='HTML')
                    register_open_window(chat_id, call.message.message_id, 'local_fin_view', code='total', day_key=day_key, params={'view_action': 'total', 'depends_on_all': False})
                    return
                final_id = send_or_edit_stored_window(chat_id, 'total_msg_id', text, parse_mode='HTML', delay=None)
                store['total_msg_id'] = final_id
                save_data(data)
                return
            lines = []
            info = store.get('info', {})
            title = get_chat_display_name(chat_id)
            lines.append('💵 Общий итог (USD, для владельца)' if view_usd else '💰 Общий итог (для владельца)')
            lines.append('')
            if view_usd:
                lines.append(f"• Этот чат ({title}): {('+' if chat_bal >= 0 else '-')}${fmt_num_plain(abs(chat_bal))}")
            else:
                lines.append(f'• Этот чат ({title}): {format_chat_amount(chat_id, chat_bal, True)}')
            all_chats = data.get('chats', {})
            allowed_chat_ids = set(tenant_chat_ids(tenant_id_for_chat(chat_id, create=False))) if 'tenant_chat_ids' in globals() else {int(x) for x in all_chats.keys()}
            total_all = 0
            other_lines = []
            for cid, st in all_chats.items():
                try:
                    cid_int = int(cid)
                except Exception:
                    continue
                if cid_int not in allowed_chat_ids:
                    continue
                bal = usd_balance_for_chat(cid_int) if view_usd else st.get('balance', 0)
                total_all += bal
                if cid_int == chat_id:
                    continue
                info2 = st.get('info', {})
                title2 = get_chat_display_name(cid_int)
                if view_usd:
                    other_lines.append(f"   • {title2}: {('+' if bal >= 0 else '-')}${fmt_num_plain(abs(bal))}")
                else:
                    other_lines.append(f'   • {title2}: {format_chat_amount(chat_id, bal, True)}')
            if other_lines:
                lines.append('')
                lines.append('• Другие чаты:')
                lines.extend(other_lines)
            lines.append('')
            if view_usd:
                lines.append(f"• Всего по всем чатам: {('+' if total_all >= 0 else '-')}${fmt_num_plain(abs(total_all))}")
            else:
                lines.append(f'• Всего по всем чатам: {format_chat_amount(chat_id, total_all, True)}')
            text = '\n'.join(lines)
            if chat_buttons_current_window_enabled(chat_id):
                safe_edit(bot, call, wm_common(text, 4), parse_mode='HTML')
                register_open_window(chat_id, call.message.message_id, 'local_fin_view', code='total', day_key=day_key, params={'view_action': 'total', 'depends_on_all': True})
                return
            final_id = send_or_edit_stored_window(chat_id, 'total_msg_id', text, parse_mode='HTML', delay=None)
            store['total_msg_id'] = final_id
            save_data(data)
            schedule_owner_total_window_delete(chat_id, final_id)
            return
        if cmd == 'info':
            if chat_buttons_current_window_enabled(chat_id):
                safe_edit(bot, call, wm_common(build_info_text(chat_id), 9), reply_markup=build_info_keyboard(chat_id))
                register_open_window(chat_id, call.message.message_id, 'local_fin_view', code='info', day_key=day_key, params={'view_action': 'info'})
            else:
                open_info_window(chat_id)
            return
        if cmd == 'backup_menu':
            if not is_owner_chat(chat_id):
                try:
                    bot.answer_callback_query(call.id, 'BACKUP доступен только владельцу', show_alert=True)
                except Exception:
                    pass
                return
            safe_edit(bot, call, build_backup_owner_menu_text(), reply_markup=build_backup_owner_menu(day_key))
            return
        if cmd.startswith('backup_mass_'):
            if not is_owner_chat(chat_id):
                try:
                    bot.answer_callback_query(call.id, 'BACKUP доступен только владельцу', show_alert=True)
                except Exception:
                    pass
                return
            target = cmd.replace('backup_mass_', '', 1)
            enabled_count, total_count = _backup_target_all_state(target)
            new_value = not bool(total_count and enabled_count == total_count)
            count = set_backup_target_for_all(target, new_value)
            try:
                bot.answer_callback_query(call.id, f"{('Включено' if new_value else 'Выключено')} для чатов: {count}")
            except Exception:
                pass
            safe_edit(bot, call, build_backup_owner_menu_text(), reply_markup=build_backup_owner_menu(day_key))
            return
        if cmd.startswith('backup_toggle_'):
            if not is_owner_chat(chat_id):
                try:
                    bot.answer_callback_query(call.id, 'BACKUP доступен только владельцу', show_alert=True)
                except Exception:
                    pass
                return
            try:
                tail = cmd[len('backup_toggle_'):]
                target, cid_s = tail.rsplit('_', 1)
                target_chat_id = int(cid_s)
            except Exception:
                return
            if answer_removed_chat(call, target_chat_id):
                return
            if target == 'chat' and (not is_owner_chat(target_chat_id)):
                try:
                    bot.answer_callback_query(call.id, 'Бэкап в сам чат разрешён только владельцу', show_alert=True)
                except Exception:
                    pass
                return
            set_backup_target_enabled(target_chat_id, target, not is_backup_target_enabled(target_chat_id, target))
            try:
                bot.answer_callback_query(call.id, 'Бэкап включён' if is_backup_target_enabled(target_chat_id, target) else 'Бэкап выключен')
            except Exception:
                pass
            safe_edit(bot, call, build_backup_owner_menu_text(), reply_markup=build_backup_owner_menu(day_key))
            return
        if cmd in ('edit_menu', 'menu'):
            clear_edit_delete_selection(chat_id, day_key)
            store['current_view_day'] = day_key
            txt, _ = render_day_window(chat_id, day_key)
            safe_edit(bot, call, txt, reply_markup=build_main_keyboard(day_key, chat_id), parse_mode='HTML')
            set_active_window_id(chat_id, day_key, call.message.message_id)
            return
        if cmd == 'back_main':
            store['current_view_day'] = day_key
            return_to_main_window_closing_previous(chat_id, day_key, call.message.message_id)

            def _cleanup_after_fast_back():
                try:
                    cancel_pending_window_commands(chat_id, delete_prompt=False)
                except Exception:
                    pass
                try:
                    clear_edit_delete_selection(chat_id, day_key)
                except Exception:
                    pass
                try:
                    save_data(data, chat_ids=[chat_id])
                except Exception:
                    pass
            if not GENERAL_TASK_POOL.submit(f'back-cleanup:{chat_id}', _cleanup_after_fast_back):
                _cleanup_after_fast_back()
            return
        if cmd == 'csv_all':
            kb = build_csv_menu(day_key, chat_id)
            txt, _ = render_day_window(chat_id, day_key)
            safe_edit(bot, call, txt, reply_markup=kb, parse_mode='HTML')
            register_open_window(chat_id, call.message.message_id, 'local_fin_view', code='csv_menu', day_key=day_key, params={'view_action': 'csv_menu'})
            return
        if cmd in {'bk_chat', 'bk_channel', 'bk_mega'}:
            if not is_owner_chat(chat_id):
                try:
                    bot.answer_callback_query(call.id, 'Настройка бэкапа доступна только владельцу', show_alert=True)
                except Exception:
                    pass
                return
            target = cmd.replace('bk_', '')
            set_backup_target_enabled(chat_id, target, not is_backup_target_enabled(chat_id, target))
            kb = build_csv_menu(day_key, chat_id)
            txt, _ = render_day_window(chat_id, day_key)
            safe_edit(bot, call, txt, reply_markup=kb, parse_mode='HTML')
            return
        if cmd in {'csv_day', 'csv_week', 'csv_month', 'csv_wedthu', 'csv_all_real', 'xlsx_day', 'xlsx_week', 'xlsx_month', 'xlsx_wedthu', 'xlsx_all', 'xlsxstat_day', 'xlsxstat_week', 'xlsxstat_month', 'xlsxstat_wedthu', 'xlsxstat_all'}:
            if cmd.startswith('xlsxstat_'):
                file_type = 'xlsxstat'
                mode = cmd.replace('xlsxstat_', '', 1)
            else:
                file_type = 'xlsx' if cmd.startswith('xlsx_') else 'csv'
                mode = cmd.replace('csv_', '').replace('xlsx_', '')
            if mode == 'all_real':
                mode = 'all'
            ok, info = submit_interactive_file_job(chat_id, 'period_export', f"{('Excel' if file_type.startswith('xlsx') else 'CSV')} экспорт", send_export_for_chat_to, chat_id, chat_id, mode, day_key, file_type)
            try:
                bot.answer_callback_query(call.id, build_all_processes_toast(chat_id) if ok else info[:180], show_alert=False)
            except Exception:
                pass
            return
        if cmd == 'reset':
            send_and_auto_delete(chat_id, '⚙️ Обнуление доступно только командой /reset из окна ℹ️ Инфо.', 12)
            return
        if cmd == 'edit_list':
            if usd_transactions_view_enabled(chat_id):
                rows = usd_records_for_day(chat_id, day_key)
                if not rows:
                    send_and_auto_delete(chat_id, 'Нет USD-записей за этот день.')
                    return
                txt, _ = render_day_window(chat_id, day_key)
                safe_edit(bot, call, txt, reply_markup=build_usd_edit_records_keyboard(day_key, chat_id), parse_mode='HTML')
                register_open_window(chat_id, call.message.message_id, 'local_fin_view', code='edit_list', day_key=day_key, params={'view_action': 'edit_list'})
                return
            day_recs = store.get('daily_records', {}).get(day_key, [])
            if not day_recs:
                send_and_auto_delete(chat_id, 'Нет записей за этот день.')
                return
            txt, _ = render_day_window(chat_id, day_key)
            safe_edit(bot, call, txt, reply_markup=build_edit_records_keyboard(day_key, chat_id), parse_mode='HTML')
            register_open_window(chat_id, call.message.message_id, 'local_fin_view', code='edit_list', day_key=day_key, params={'view_action': 'edit_list'})
            return
        if cmd.startswith('value_rec_'):
            if not effective_main_financial_value_buttons_enabled(chat_id):
                send_and_auto_delete(chat_id, 'Этот режим финансовых кнопок сейчас выключен.', 8)
                return
            rid = int(cmd.split('_')[-1])
            start_record_edit_prompt(chat_id, day_key, rid)
            return
        if cmd.startswith('edit_rec_'):
            rid = int(cmd.split('_')[-1])
            start_record_edit_prompt(chat_id, day_key, rid)
            return
        if cmd.startswith('del_toggle_'):
            rid = int(cmd.split('_')[-1])
            if usd_transactions_view_enabled(chat_id):
                toggle_usd_edit_delete_selection(chat_id, day_key, rid)
                kb = build_usd_edit_records_keyboard(day_key, chat_id)
            else:
                toggle_edit_delete_selection(chat_id, day_key, rid)
                kb = build_edit_records_keyboard(day_key, chat_id)
            txt, _ = render_day_window(chat_id, day_key)
            safe_edit(bot, call, txt, reply_markup=kb, parse_mode='HTML')
            register_open_window(chat_id, call.message.message_id, 'local_fin_view', code='edit_list', day_key=day_key, params={'view_action': 'edit_list'})
            return
        if cmd == 'del_selected':
            if usd_transactions_view_enabled(chat_id):
                count = delete_selected_usd_records(chat_id, day_key)
                kb = build_usd_edit_records_keyboard(day_key, chat_id)
                notice = f'🗑 Удалено USD-записей: {count}'
            else:
                count = delete_selected_records(chat_id, day_key)
                kb = build_edit_records_keyboard(day_key, chat_id)
                notice = f'🗑 Удалено записей: {count}'
            txt, _ = render_day_window(chat_id, day_key)
            safe_edit(bot, call, txt, reply_markup=kb, parse_mode='HTML')
            register_open_window(chat_id, call.message.message_id, 'local_fin_view', code='edit_list', day_key=day_key, params={'view_action': 'edit_list'})
            send_and_auto_delete(chat_id, notice, 8)
            return
        if cmd == 'forward_menu':
            if not is_owner_chat(chat_id):
                send_and_auto_delete(chat_id, 'Меню доступно только владельцу.', HELPER_DELETE_DELAY)
                return
            kb = build_forward_menu_keyboard_for_current_mode(day_key)
            safe_edit(bot, call, build_forward_menu_text_for_current_mode('Пересылка:\nВыберите чат A:'), reply_markup=kb)
            return
        if cmd == 'forward_finmode_menu':
            kb = build_finance_toggle_chat_menu(day_key)
            safe_edit(bot, call, '💰 Фин режим / В24\nВыберите чат. Значок рядом с чатом показывает текущий режим:\n⬜ выкл | 🙈 скрыто | ✅🔟 как обычно | ✅3️⃣ открыть окно | ✅🥇 всегда первым', reply_markup=kb)
            return
        if cmd == 'quick_balance_menu':
            kb = build_quick_balance_chat_menu(day_key)
            safe_edit(bot, call, build_forward_status_text('Быстрый остаток:\nВыберите чат для включения или выключения режима.'), reply_markup=kb)
            return
        if cmd == 'hidden_finance_menu':
            kb = build_hidden_finance_chat_menu(day_key)
            safe_edit(bot, call, build_forward_status_text('Скрытые финансы:\nВыберите чат. Финансовый учёт и бэкапы работают, окна в чате не выводятся.'), reply_markup=kb)
            return
        if cmd.startswith('hf_pick_'):
            tgt = int(cmd.split('_')[-1])
            if answer_removed_chat(call, tgt):
                return
            set_hidden_finance_mode(tgt, not is_hidden_finance_mode(tgt))
            kb = build_hidden_finance_chat_menu(day_key)
            safe_edit(bot, call, build_forward_status_text('Скрытые финансы:\nВыберите чат.'), reply_markup=kb)
            return
        if cmd == 'fin_windows_menu':
            kb = build_fin_windows_chat_menu(day_key)
            safe_edit(bot, call, '🪟 Фин окна чатов\nВыберите чат для просмотра операций:', reply_markup=kb)
            return
        if cmd.startswith('finwin_open_'):
            tgt = int(cmd.split('_')[-1])
            if answer_removed_chat(call, tgt):
                return
            target_store = get_chat_store(tgt)
            view_day = target_store.get('current_view_day', today_key())
            safe_edit(bot, call, render_fin_window_text(tgt, view_day), reply_markup=build_fin_window_view_keyboard(tgt, view_day, day_key), parse_mode='HTML')
            register_open_window(chat_id, call.message.message_id, 'fin_view', code='fv:open', day_key=view_day, params={'target_chat_id': tgt, 'owner_day_key': day_key, 'view_action': 'open'})
            return
        if cmd.startswith('qb_cfg_'):
            tgt = int(cmd.split('_')[-1])
            if answer_removed_chat(call, tgt):
                return
            kb = build_quick_balance_mode_menu(day_key, tgt)
            safe_edit(bot, call, build_finance_mode_config_text(tgt), reply_markup=kb)
            return
        if cmd.startswith('qb_mode_normal_'):
            tgt = int(cmd.split('_')[-1])
            if answer_removed_chat(call, tgt):
                return
            _apply_finance_window_mode_choice(tgt, 'normal')
            safe_edit(bot, call, build_finance_mode_config_text(tgt), reply_markup=build_finance_mode_config_menu(day_key, tgt))
            return
        if cmd.startswith('qb_mode_open_'):
            tgt = int(cmd.split('_')[-1])
            if answer_removed_chat(call, tgt):
                return
            _apply_finance_window_mode_choice(tgt, 'open')
            safe_edit(bot, call, build_finance_mode_config_text(tgt), reply_markup=build_finance_mode_config_menu(day_key, tgt))
            return
        if cmd.startswith('qb_mode_first_'):
            tgt = int(cmd.split('_')[-1])
            if answer_removed_chat(call, tgt):
                return
            _apply_finance_window_mode_choice(tgt, 'first')
            safe_edit(bot, call, build_finance_mode_config_text(tgt), reply_markup=build_finance_mode_config_menu(day_key, tgt))
            return
        if cmd.startswith('qb_hidden_toggle_'):
            tgt = int(cmd.split('_')[-1])
            if answer_removed_chat(call, tgt):
                return
            new_hidden = not is_hidden_finance_mode(tgt)
            if new_hidden:
                set_finance_mode(tgt, True)
                set_hidden_finance_mode(tgt, True)
            else:
                set_hidden_finance_mode(tgt, False)
            _persist_finance_window_mode_critical(tgt)
            safe_edit(bot, call, build_finance_mode_config_text(tgt), reply_markup=build_finance_mode_config_menu(day_key, tgt))
            return
        if cmd.startswith('qb_finwin_open_'):
            tgt = int(cmd.split('_')[-1])
            if answer_removed_chat(call, tgt):
                return
            target_store = get_chat_store(tgt)
            view_day = target_store.get('current_view_day', today_key())
            safe_edit(bot, call, render_fin_window_text(tgt, view_day), reply_markup=build_fin_window_view_keyboard(tgt, view_day, day_key), parse_mode='HTML')
            register_open_window(chat_id, call.message.message_id, 'fin_view', code='fv:open', day_key=view_day, params={'target_chat_id': tgt, 'owner_day_key': day_key, 'view_action': 'open'})
            return
        if cmd.startswith('fw_finmode_pick_'):
            tgt = int(cmd.split('_')[-1])
            if answer_removed_chat(call, tgt):
                return
            safe_edit(bot, call, build_finance_mode_config_text(tgt), reply_markup=build_finance_mode_config_menu(day_key, tgt))
            return
        if cmd.startswith('fin_mode_toggle_'):
            tgt = int(cmd.split('_')[-1])
            if answer_removed_chat(call, tgt):
                return
            if is_finance_mode(tgt):
                set_finance_window_mode(tgt, 'off', persist_now=False)
                delete_auto_finance_windows_for_chat(tgt, persist_now=False)
                set_hidden_finance_mode(tgt, False)
                set_finance_mode(tgt, False)
            else:
                set_finance_mode(tgt, True)
                set_finance_window_mode(tgt, 'off', persist_now=False)
                set_hidden_finance_mode(tgt, True)
                delete_auto_finance_windows_for_chat(tgt, persist_now=False)
            _persist_finance_window_mode_critical(tgt)
            try:
                schedule_contour_home_after_mode_change(tgt, 'finance_toggle', 0.15)
            except Exception:
                pass
            safe_edit(bot, call, build_finance_mode_config_text(tgt), reply_markup=build_finance_mode_config_menu(day_key, tgt))
            return
        if cmd.startswith('fin_mode_off_'):
            tgt = int(cmd.split('_')[-1])
            if answer_removed_chat(call, tgt):
                return
            set_finance_window_mode(tgt, 'off', persist_now=False)
            delete_auto_finance_windows_for_chat(tgt, persist_now=False)
            set_hidden_finance_mode(tgt, False)
            set_finance_mode(tgt, False)
            save_data(data)
            _persist_finance_window_mode_critical(tgt)
            try:
                schedule_contour_home_after_mode_change(tgt, 'finance_off', 0.15)
            except Exception:
                pass
            safe_edit(bot, call, build_finance_mode_config_text(tgt), reply_markup=build_finance_mode_config_menu(day_key, tgt))
            return
        if cmd == 'pick_date':
            try:
                cdt = datetime.strptime(day_key, '%Y-%m-%d')
            except Exception:
                cdt = now_local()
            safe_edit(bot, call, calendar_window_text(cdt, marker=False), reply_markup=build_calendar_keyboard(cdt, chat_id))
            return
        if cmd == 'cancel_edit':
            clear_edit_wait_state(chat_id, call.message.message_id, delete_prompt=True)
            try:
                bot.answer_callback_query(call.id, 'Редактирование отменено')
            except Exception:
                pass
            return
        log_error(f'UNHANDLED_CALLBACK: chat={chat_id} data={str(data_str)[:500]}')
        try:
            bot.answer_callback_query(call.id, 'Эта кнопка не обработана. Откройте меню заново.', show_alert=True)
        except Exception:
            pass
    except Exception as e:
        log_error(f"on_callback error: data={locals().get('data_str', '')} chat={locals().get('chat_id', '')}: {e}")
        try:
            bot.answer_callback_query(call.id, 'Ошибка кнопки. Откройте окно заново.', show_alert=True)
        except Exception:
            pass

# --- ИСТОЧНИК: 90_commands_exports.py ---
def send_csv_week(chat_id: int, day_key: str):
    if is_finance_output_suppressed(chat_id):
        return
    return send_export_for_chat_to(int(chat_id), int(chat_id), 'week', day_key, 'csv')

def send_csv_month(chat_id: int, day_key: str):
    if is_finance_output_suppressed(chat_id):
        return
    return send_export_for_chat_to(int(chat_id), int(chat_id), 'month', day_key, 'csv')

def _v177_legacy_0226_send_csv_wedthu(chat_id: int, day_key: str):
    if is_finance_output_suppressed(chat_id):
        return
    return send_export_for_chat_to(int(chat_id), int(chat_id), 'wedthu', day_key, 'csv')
try:
    _v177_legacy_0226_send_csv_wedthu.__name__ = 'send_csv_wedthu'
except Exception:
    pass

def finance_operation_key(chat_id: int, source_msg_id, ledger: str='main') -> str:
    """Stable idempotency key for a finance effect created from a Telegram message."""
    try:
        mid = int(source_msg_id)
    except Exception:
        return ''
    return f"finance:{int(chat_id)}:{str(ledger or 'main')}:{mid}"

def find_record_by_operation_key(chat_id: int, operation_key: str):
    if not operation_key:
        return None
    try:
        store = get_chat_store(int(chat_id))
        for r in store.get('records', []) or []:
            if isinstance(r, dict) and str(r.get('operation_key') or '') == str(operation_key):
                return r
    except Exception:
        pass
    return None

def _finance_add_record_base(chat_id: int, amount: float, note: str, owner: int, source_msg=None, day_key=None, usd_amount=None, usd_note: str='', usd_only: bool=False, source_finance_text: str=''):
    bot_journal('record_add_start', chat_id, f'amount={amount} note={note}')
    if globals().get('constitution_finance_write_blocked_v232') and constitution_finance_write_blocked_v232():
        raise RuntimeError('DATA CONSTITUTION: финансовые изменения заблокированы до восстановления целостности')
    op_id = operation_begin('finance_add', chat_id, target=str(day_key or 'auto'), payload={'amount': amount, 'note': note}, critical=True) if 'operation_begin' in globals() else ''
    if op_id and 'operation_step' in globals():
        operation_step(op_id, 'saved_locally', 'intent recorded', persist=False)
    with locked_chat(chat_id):
        store = get_chat_store(chat_id)
        rid = store.get('next_id', 1)
        if not day_key:
            day_key = day_key_from_message(source_msg)
        source_msg_id = getattr(source_msg, 'message_id', None) if source_msg else None
        source_order_msg_id = getattr(source_msg, 'source_order_msg_id', None) or getattr(source_msg, 'forward_source_msg_id', None) or source_msg_id
        _op_override = str(getattr(source_msg, 'finance_operation_key_override', '') or '') if source_msg is not None else ''
        operation_key = _op_override or finance_operation_key(chat_id, source_msg_id, 'main')
        if operation_key:
            existing_op = find_record_by_operation_key(int(chat_id), operation_key) if 'find_record_by_operation_key' in globals() else None
            if isinstance(existing_op, dict):
                bot_journal('finance_duplicate_operation_blocked_v260', chat_id, f'operation_key={operation_key}')
                if op_id and 'operation_complete' in globals():
                    operation_complete(op_id, 'duplicate blocked by stable operation key; existing record reused')
                return existing_op
        if source_msg_id is not None:
            existing_any = find_record_by_message_id(int(chat_id), int(source_msg_id)) if 'find_record_by_message_id' in globals() else None
            if isinstance(existing_any, dict):
                if '_remember_finance_source_identity_v257' in globals():
                    _remember_finance_source_identity_v257(int(chat_id), existing_any, int(source_msg_id), 'records')
                bot_journal('finance_duplicate_blocked_v257', chat_id, f'source_msg_id={source_msg_id} operation_key={operation_key}; central=1')
                if op_id and 'operation_complete' in globals():
                    operation_complete(op_id, 'duplicate blocked by stable source identity; existing record reused')
                return existing_any
            for existing in store.get('records', []) or []:
                if not isinstance(existing, dict):
                    continue
                if operation_key and str(existing.get('operation_key') or '') == operation_key or int(existing.get('source_msg_id') or 0) == int(source_msg_id):
                    if operation_key and (not existing.get('operation_key')):
                        existing['operation_key'] = operation_key
                    bot_journal('finance_duplicate_blocked', chat_id, f'source_msg_id={source_msg_id} operation_key={operation_key}')
                    if op_id and 'operation_complete' in globals():
                        operation_complete(op_id, 'duplicate blocked; existing record reused')
                    return existing
        rec = {'id': rid, 'short_id': '', 'timestamp': message_timestamp_iso(source_msg), 'amount': amount, 'note': note, 'source_msg_id': source_msg_id, 'source_order_msg_id': source_order_msg_id, 'owner': owner, 'msg_id': source_msg_id, 'origin_msg_id': source_msg_id, 'day_key': day_key, 'operation_key': operation_key}
        if source_msg is not None:
            for _attr, _field in (('forward_source_chat_id','forward_source_chat_id'), ('forward_source_msg_id','forward_source_msg_id'), ('forward_dst_chat_id','forward_dst_chat_id'), ('forward_dst_msg_id','forward_dst_msg_id')):
                try:
                    _v = int(getattr(source_msg, _attr, 0) or 0)
                    if _v: rec[_field] = _v
                except Exception:
                    pass
            if rec.get('forward_source_chat_id') and rec.get('forward_source_msg_id'):
                rec['forwarded_by_bot'] = True
        if usd_amount is not None:
            rec['usd_amount'] = float(usd_amount or 0)
            rec['usd_note'] = str(usd_note or note or '')
            rec['usd_only'] = bool(usd_only)
        if source_finance_text:
            rec['source_finance_text'] = str(source_finance_text)
        # R15 hot path: do not run the historical full-ledger normalizer/dedupe
        # synchronously for every new message.  Exact-once guards above already protect
        # this Telegram effect.  Update the two authoritative in-memory indexes
        # incrementally, commit this chat, and let the debounced finance finalize do the
        # full normalize/reconcile in FINANCE_TASK_POOL.
        records = store.setdefault('records', [])
        _needs_sort = bool(records and record_sort_key(rec) < record_sort_key(records[-1]))
        records.append(rec)
        if _needs_sort:
            try: records.sort(key=record_sort_key)
            except Exception: pass
        daily = store.setdefault('daily_records', {})
        day_rows = daily.setdefault(str(day_key), [])
        _day_needs_sort = bool(day_rows and record_sort_key(rec) < record_sort_key(day_rows[-1]))
        day_rows.append(rec)
        if _day_needs_sort:
            try: day_rows.sort(key=record_sort_key)
            except Exception: pass
        try:
            store['next_id'] = max(int(store.get('next_id', 1) or 1), int(rid) + 1)
        except Exception:
            store['next_id'] = int(rid) + 1
        try:
            store['balance'] = float(store.get('balance', 0) or 0) + float(amount or 0)
        except Exception:
            store['balance'] = sum((float(r.get('amount', 0) or 0) for r in records if isinstance(r, dict)))
        store['_finance_hotpath_pending_normalize_r16'] = True
        store['_finance_fast_generation_r16'] = int(store.get('_finance_fast_generation_r16', 0) or 0) + 1
        store.pop('_finance_day_balance_cache_r16', None)
        if usd_amount is not None and '_usd_balance_cache_r16' in store:
            try: store['_usd_balance_cache_r16'] = float(store.get('_usd_balance_cache_r16', 0) or 0) + float(usd_amount or 0)
            except Exception: store.pop('_usd_balance_cache_r16', None)
        # R48: no SQLite/integrity/root persistence while chat_lock is held.
        try:
            if 'ensure_finance_record_uid' in globals():
                ensure_finance_record_uid(int(chat_id), rec)
        except Exception:
            pass
        result_rec = rec
    # Durable record commit after chat_lock release.
    try:
        if 'persist_finance_chat_local_fast' in globals() and not persist_finance_chat_local_fast(int(chat_id)):
            raise RuntimeError('local SQLite finance persist failed')
    except Exception as _v168_local_exc:
        try: log_error(f'R48 record local commit {chat_id}: {_v168_local_exc}')
        except Exception: pass
    try:
        finance_cache_invalidate(chat_id, 'finance_add')
        finance_integrity_append(chat_id, 'add', result_rec)
    except Exception as _integrity_exc:
        log_error(f'finance add integrity: {_integrity_exc}')
    try:
        if source_msg_id is not None and '_remember_finance_source_identity_v257' in globals():
            _remember_finance_source_identity_v257(int(chat_id), result_rec, int(source_msg_id), 'records')
    except Exception as _v257_idx_exc:
        try: log_error(f'v257 finance source identity index: {_v257_idx_exc}')
        except Exception: pass
    if op_id and 'operation_complete' in globals():
        operation_complete(op_id, f"record={result_rec.get('id')}")
    return result_rec

def delete_record_in_chat(chat_id: int, rid: int):
    if globals().get('constitution_finance_write_blocked_v232') and constitution_finance_write_blocked_v232():
        raise RuntimeError('DATA CONSTITUTION: удаление заблокировано до восстановления целостности')
    op_id = operation_begin('finance_delete', chat_id, target=str(rid), payload={'rid': rid}, critical=True) if 'operation_begin' in globals() else ''
    with locked_chat(chat_id):
        store = get_chat_store(chat_id)
        deleted_record = next((copy.deepcopy(x) for x in store.get('records', []) if int(x.get('id', -1)) == int(rid)), None)
        store['records'] = [x for x in store['records'] if int(x.get('id', -1)) != int(rid)]
        for day, arr in list(store.get('daily_records', {}).items()):
            arr2 = [x for x in arr if int(x.get('id', -1)) != int(rid)]
            if arr2:
                store['daily_records'][day] = arr2
            else:
                del store['daily_records'][day]
        # R16: record IDs are stable. Do not renumber the whole history on deletion.
        # Adjust only the affected aggregate and leave full normalize/self-check to background.
        try: store['balance'] = float(store.get('balance', 0) or 0) - float((deleted_record or {}).get('amount', 0) or 0)
        except Exception: pass
        store['_finance_hotpath_pending_normalize_r16'] = True
        store['_finance_fast_generation_r16'] = int(store.get('_finance_fast_generation_r16', 0) or 0) + 1
        store.pop('_finance_day_balance_cache_r16', None)
        if isinstance(deleted_record, dict) and '_usd_balance_cache_r16' in store:
            try: store['_usd_balance_cache_r16'] = float(store.get('_usd_balance_cache_r16', 0) or 0) - float(deleted_record.get('usd_amount', 0) or 0)
            except Exception: store.pop('_usd_balance_cache_r16', None)
        pass
    try:
        if 'persist_finance_chat_local_fast' in globals() and not persist_finance_chat_local_fast(int(chat_id)):
            raise RuntimeError('local SQLite finance persist failed')
    except Exception as _r7_delete_persist_exc:
        try: log_error(f'R48 delete local persist {chat_id}: {_r7_delete_persist_exc}')
        except Exception: pass
    try:
        finance_cache_invalidate(chat_id, 'finance_delete')
        finance_integrity_append(chat_id, 'delete', deleted_record or {'id': rid})
    except Exception as _integrity_exc:
        log_error(f'finance delete integrity: {_integrity_exc}')
    if op_id and 'operation_complete' in globals():
        operation_complete(op_id, f'record={rid}')

def renumber_chat_records(chat_id: int):
    """Перенумеровывает записи по реальной хронологии поступления сообщений."""
    store = get_chat_store(chat_id)
    normalize_chat_records(chat_id)
    all_recs = list(store.get('records', []) or [])
    all_recs.sort(key=record_sort_key)
    for new_id, r in enumerate(all_recs, 1):
        r['id'] = new_id
    store['records'] = all_recs
    rebuilt_daily = {}
    for r in all_recs:
        rebuilt_daily.setdefault(_record_day_key(r), []).append(r)
    store['daily_records'] = rebuilt_daily
    store['next_id'] = len(all_recs) + 1
    try:
        helper = globals().get('_r7_rebuild_month_short_ids_after_normalize')
        if callable(helper):
            helper(int(chat_id), store)
        else:
            rebuild_month_short_ids(chat_id)
    except Exception:
        rebuild_month_short_ids(chat_id)

def get_or_create_active_windows(chat_id: int) -> dict:
    return data.setdefault('active_messages', {}).setdefault(str(chat_id), {})

def get_primary_main_window(chat_id: int) -> tuple[int | None, str]:
    """Return the single authoritative main window for this chat."""
    chat_id = int(chat_id)
    store = get_chat_store(chat_id)
    mid = 0
    try:
        mid = int(store.get('primary_main_window_id') or 0)
    except Exception:
        mid = 0
    day = str(store.get('primary_main_window_day') or store.get('current_view_day') or today_key())[:10]
    if mid:
        return (mid, day)
    aw = get_or_create_active_windows(chat_id)
    if aw:
        preferred = aw.get(day)
        if preferred:
            try:
                mid = int(preferred)
            except Exception:
                mid = 0
        if not mid:
            try:
                last_day, last_mid = list(aw.items())[-1]
                day = str(last_day)[:10]
                mid = int(last_mid)
            except Exception:
                mid = 0
        if mid:
            store['primary_main_window_id'] = mid
            store['primary_main_window_day'] = day
            store['current_view_day'] = day
            aw.clear()
            aw[day] = mid
    return (mid or None, day)

def canonical_main_day(chat_id: int) -> str:
    _mid, day = get_primary_main_window(int(chat_id))
    return str(day or today_key())[:10]

def is_primary_main_message(chat_id: int, message_id: int) -> bool:
    mid, _day = get_primary_main_window(int(chat_id))
    try:
        return bool(mid and int(mid) == int(message_id))
    except Exception:
        return False

def _v189_delete_stale_main_message(chat_id: int, message_id: int):
    try:
        fn = globals().get('v177_delete_message_async')
        if callable(fn):
            fn(int(chat_id), int(message_id), 'v189_stale_main')
            return
    except Exception:
        pass
    try:
        pool = globals().get('GENERAL_TASK_POOL')
        if pool is not None:
            pool.submit(f'v189-stale-main:{int(chat_id)}:{int(message_id)}', lambda: _tg_call_retry(bot.delete_message, int(chat_id), int(message_id), attempts=1, purpose='v189_stale_main_delete'))
            return
    except Exception:
        pass

def _v186_persist_active_window_state(chat_id: int):
    """Persist UI-only window state outside callback latency path."""
    try:
        _finance_window_state(int(chat_id))['auto_reopen_on_boot'] = True
        _sync_finance_window_state_from_runtime(int(chat_id), schedule_delta=False)
        save_data(data, chat_ids=[int(chat_id)])
        try:
            schedule_config_backup_for_chats(int(chat_id), delay=3.0)
        except Exception:
            pass
    except Exception as exc:
        try:
            log_error(f'v186 active window persist {chat_id}: {exc}')
        except Exception:
            pass

def set_active_window_id(chat_id: int, day_key: str, message_id: int):
    """Promote exactly one Telegram message as the authoritative main window."""
    chat_id = int(chat_id)
    day_key = str(day_key)[:10]
    message_id = int(message_id)
    aw = get_or_create_active_windows(chat_id)
    stale_ids = set()
    for _dk, _mid in list(aw.items()):
        try:
            if int(_mid or 0) and int(_mid) != message_id:
                stale_ids.add(int(_mid))
        except Exception:
            pass
    store = get_chat_store(chat_id)
    try:
        prev_primary = int(store.get('primary_main_window_id') or 0)
        if prev_primary and prev_primary != message_id:
            stale_ids.add(prev_primary)
    except Exception:
        pass
    aw.clear()
    aw[day_key] = message_id
    store['primary_main_window_id'] = message_id
    store['primary_main_window_day'] = day_key
    store['current_view_day'] = day_key
    register_open_window(chat_id, message_id, 'main_day', code='О1', day_key=day_key, params={'parallel_allowed': False, 'primary': True})
    for stale_mid in sorted(stale_ids):
        try:
            unregister_open_window(chat_id, stale_mid)
        except Exception:
            pass
        _v189_delete_stale_main_message(chat_id, stale_mid)
    try:
        DELAYED_SCHEDULER.schedule(f'v186-active-window-persist:{chat_id}', 0.15, _v186_persist_active_window_state, chat_id)
    except Exception:
        pass

def get_active_window_id(chat_id: int, day_key: str):
    mid, active_day = get_primary_main_window(int(chat_id))
    return mid if mid and str(active_day) == str(day_key)[:10] else None

def clear_active_window_id(chat_id: int, day_key: str):
    try:
        chat_id = int(chat_id)
        day_key = str(day_key)[:10]
        aw = get_or_create_active_windows(chat_id)
        old_mid = aw.pop(day_key, None)
        store = get_chat_store(chat_id)
        primary_mid = int(store.get('primary_main_window_id') or 0)
        primary_day = str(store.get('primary_main_window_day') or '')[:10]
        if old_mid:
            unregister_open_window(chat_id, int(old_mid))
        if primary_day == day_key or (old_mid and primary_mid == int(old_mid)):
            store['primary_main_window_id'] = None
            store['primary_main_window_day'] = ''
        try:
            DELAYED_SCHEDULER.schedule(f'v186-active-window-persist:{chat_id}', 0.15, _v186_persist_active_window_state, chat_id)
        except Exception:
            pass
    except Exception as e:
        log_error(f'clear_active_window_id({chat_id},{day_key}): {e}')

def close_previous_main_window_before_back(chat_id: int, day_key: str, current_message_id: int | None=None):
    """При возврате в основное окно удаляет прежнее О1, чтобы не оставалось дубля."""
    try:
        old_mid = get_active_window_id(chat_id, day_key)
        if not old_mid:
            return
        if current_message_id is not None and int(old_mid) == int(current_message_id):
            return
        try:
            bot.delete_message(int(chat_id), int(old_mid))
        except Exception:
            pass
        clear_active_window_id(chat_id, day_key)
    except Exception as e:
        log_error(f'close_previous_main_window_before_back({chat_id},{day_key}): {e}')

def _v177_legacy_0229_update_or_send_day_window(chat_id: int, day_key: str):
    if is_owner_chat(chat_id):
        backup_window_for_owner(chat_id, day_key)
        schedule_balance_panel_refresh(chat_id, 0.5)
        return
    lock = window_locks[chat_id, day_key]
    with lock:
        txt, _ = render_day_window(chat_id, day_key)
        kb = build_main_keyboard(day_key, chat_id)
        old_mid = get_active_window_id(chat_id, day_key)
        if len(txt) > 3900:
            log_error(f'update_or_send_day_window: text too long for {chat_id} {day_key}, len={len(txt)}')
        if old_mid:
            try:
                bot.edit_message_text(txt, chat_id=chat_id, message_id=old_mid, reply_markup=kb, parse_mode='HTML')
                set_active_window_id(chat_id, day_key, old_mid)
                schedule_balance_panel_refresh(chat_id, 0.5)
                return
            except Exception as e:
                err = str(e).lower()
                if 'message is not modified' in err:
                    schedule_balance_panel_refresh(chat_id, 0.5)
                    return
                try:
                    bot.delete_message(chat_id, old_mid)
                except Exception:
                    pass
        sent = bot.send_message(chat_id, txt, reply_markup=kb, parse_mode='HTML')
        set_active_window_id(chat_id, day_key, sent.message_id)
    schedule_balance_panel_refresh(chat_id, 0.5)
try:
    _v177_legacy_0229_update_or_send_day_window.__name__ = 'update_or_send_day_window'
except Exception:
    pass

def is_finance_mode(chat_id):
    store = get_chat_store(chat_id)
    return store.get('finance_mode', False)

def set_finance_mode(chat_id: int, enabled: bool):
    """v108: finance accounting and visible finance windows are separate states.

    A fresh OFF -> ON transition always enables hidden finance and starts with all three
    automatic window modes OFF.  Visible modes are selected independently in F39.
    """
    chat_id = int(chat_id)
    store = get_chat_store(chat_id)
    enabled = bool(enabled)
    was_enabled = bool(store.get('finance_mode', False))
    store['finance_mode'] = enabled
    settings = store.setdefault('settings', {})
    if enabled:
        finance_active_chats.add(chat_id)
        if not was_enabled:
            settings['hidden_finance'] = True
            settings['quick_balance_enabled'] = False
            settings['quick_balance_behavior'] = 'normal'
            settings['quick_balance_user_selected'] = True
            state = store.get('finance_window_state')
            if not isinstance(state, dict):
                state = {}
            state.update({'mode': 'off', 'main_windows': {}, 'balance_panel_id': None, 'balance_panel_mode': 'mini', 'current_view_day': str(store.get('current_view_day') or today_key()), 'auto_reopen_on_boot': False, 'updated_at': now_local().isoformat(timespec='seconds')})
            store['finance_window_state'] = state
            try:
                delete_auto_finance_windows_for_chat(chat_id, persist_now=False)
            except Exception:
                pass
    else:
        finance_active_chats.discard(chat_id)
        settings['hidden_finance'] = False
        settings['quick_balance_enabled'] = False
        settings['quick_balance_behavior'] = 'normal'
        settings['quick_balance_user_selected'] = True
        state = store.get('finance_window_state')
        if not isinstance(state, dict):
            state = {}
        state.update({'mode': 'off', 'main_windows': {}, 'balance_panel_id': None, 'balance_panel_mode': 'mini', 'auto_reopen_on_boot': False, 'updated_at': now_local().isoformat(timespec='seconds')})
        store['finance_window_state'] = state
        try:
            delete_auto_finance_windows_for_chat(chat_id, persist_now=False)
        except Exception:
            pass
    save_data(data, chat_ids=[chat_id])
    try:
        schedule_quick_backup(chat_id, 0.5)
    except Exception:
        pass
    schedule_config_backup_for_chats(chat_id)

def require_finance(chat_id: int) -> bool:
    """
    Проверка: включён ли финансовый режим.
    Если нет — показываем подсказку /поехали.
    """
    if not is_finance_mode(chat_id):
        send_and_auto_delete(chat_id, '⚙️ Финансовый режим выключен.\nАктивируйте командой /ok')
        return False
    return True

def _v177_legacy_0230_refresh_total_message_if_any(chat_id: int):
    """
    Если в чате есть активное сообщение '💰 Общий итог',
    пересчитывает и обновляет его текст.
    """
    store = get_chat_store(chat_id)
    msg_id = store.get('total_msg_id')
    if not msg_id:
        return
    try:
        chat_bal = store.get('balance', 0)
        if not is_owner_chat(chat_id):
            text = wm_common(f'💰 Общий итог по этому чату: {format_chat_amount(chat_id, chat_bal, True)}', 4)
        else:
            lines = []
            info = store.get('info', {})
            title = get_chat_display_name(chat_id)
            lines.append('💰 Общий итог (для владельца)')
            lines.append('')
            lines.append(f'• Этот чат ({title}): {format_chat_amount(chat_id, chat_bal, True)}')
            all_chats = data.get('chats', {})
            allowed_chat_ids = set(tenant_chat_ids(tenant_id_for_chat(chat_id, create=False))) if 'tenant_chat_ids' in globals() else {int(x) for x in all_chats.keys()}
            total_all = 0
            other_lines = []
            for cid, st in all_chats.items():
                try:
                    cid_int = int(cid)
                except Exception:
                    continue
                if cid_int not in allowed_chat_ids:
                    continue
                bal = st.get('balance', 0)
                total_all += bal
                if cid_int == chat_id:
                    continue
                info2 = st.get('info', {})
                title2 = get_chat_display_name(cid_int)
                other_lines.append(f'   • {title2}: {format_chat_amount(chat_id, bal, True)}')
            if other_lines:
                lines.append('')
                lines.append('• Другие чаты:')
                lines.extend(other_lines)
            lines.append('')
            lines.append(f'• Всего по всем чатам: {format_chat_amount(chat_id, total_all, True)}')
            text = '\n'.join(lines)
        bot.edit_message_text(text, chat_id=chat_id, message_id=msg_id, parse_mode='HTML')
        if is_owner_chat(chat_id):
            schedule_owner_total_window_delete(chat_id, msg_id)
    except Exception as e:
        if 'message is not modified' in str(e).lower():
            if is_owner_chat(chat_id):
                schedule_owner_total_window_delete(chat_id, msg_id)
            return
        log_error(f'refresh_total_message_if_any({chat_id}): {e}')
        store['total_msg_id'] = None
        save_data(data)
try:
    _v177_legacy_0230_refresh_total_message_if_any.__name__ = 'refresh_total_message_if_any'
except Exception:
    pass

def refresh_owner_after_chat_change(source_chat_id: int):
    if not OWNER_ID:
        return
    try:
        owner_chat_id = int(OWNER_ID)
    except Exception:
        return
    if int(source_chat_id) == owner_chat_id:
        return
    try:
        owner_store = get_chat_store(owner_chat_id)
        owner_day_key = owner_store.get('current_view_day', today_key())
        backup_window_for_owner(owner_chat_id, owner_day_key, None)
        refresh_balance_panel_now(owner_chat_id)
        refresh_total_message_if_any(owner_chat_id)
    except Exception as e:
        log_error(f'refresh_owner_after_chat_change({source_chat_id}): {e}')

def cancel_pending_window_commands(chat_id: int, delete_prompt: bool=False):
    """Назад в основное окно отменяет режимы ожидания предыдущих окон и их таймеры."""
    try:
        clear_forward_copy_edit_wait(chat_id, delete_prompt=delete_prompt)
    except Exception:
        pass
    try:
        clear_edit_wait_state(chat_id, delete_prompt=delete_prompt)
    except Exception:
        pass
    try:
        clear_finwin_edit_wait_state(chat_id, delete_prompt=delete_prompt)
    except Exception:
        pass
    try:
        clear_category_wait_state(chat_id, 'category_add_wait', delete_prompt=delete_prompt)
    except Exception:
        pass
    try:
        clear_category_wait_state(chat_id, 'category_edit_wait', delete_prompt=delete_prompt)
    except Exception:
        pass
    try:
        _clear_secret_wait(chat_id, delete_prompt=delete_prompt)
    except Exception:
        pass
    try:
        store = get_chat_store(chat_id)
        if store.get('reset_wait'):
            store['reset_wait'] = False
            store['reset_time'] = 0
            save_data(data)
    except Exception:
        pass

def send_info(chat_id: int, text: str):
    send_and_auto_delete(chat_id, text, HELPER_DELETE_DELAY)

@bot.message_handler(commands=['owners', 'additional_owners', 'доп_владельцы'])
def cmd_additional_owners(msg):
    schedule_command_delete(msg)
    if '_tenant_send_dashboard' in globals():
        _tenant_send_dashboard(msg)
        return
    if not is_primary_owner(msg.chat.id):
        return
    bot.send_message(msg.chat.id, wm_owner('👥 Дополнительные владельцы\n\n✅ — доступ владельца включён\n⬜ — доступ выключен', 36), reply_markup=build_additional_owners_keyboard())

@bot.message_handler(commands=['windows', 'okna', 'окна'])
def cmd_windows_in_current_message(msg):
    schedule_command_delete(msg)
    enabled = toggle_chat_buttons_current_window(msg.chat.id)
    send_and_auto_delete(msg.chat.id, f"{('✅' if enabled else '⬜')} Режим открытия в текущем окне: {('ВКЛ' if enabled else 'ВЫКЛ')}", 8)

@bot.message_handler(commands=['ok', 'поехали'])
def cmd_ok(msg):
    try:
        update_chat_info_from_message(msg)
    except Exception:
        pass
    schedule_command_delete(msg)
    chat_id = msg.chat.id
    # R10: /ok (and /поехали) is owner/legacy finance activation only.
    # Contours 1/2 must use their explicit business-mode menu so a command
    # cannot bypass the owner's mode policy.
    try:
        if bool(globals().get('_v215_circle_business_chat', lambda _c: False)(int(chat_id))):
            try:
                send_and_auto_delete(chat_id, '🔒 /ok недоступна в контурах 1/2. Используйте «☰ Меню режимов».', 10)
            except Exception:
                pass
            try:
                globals().get('show_contour_start_modes', lambda *_a, **_k: None)(int(chat_id), int(getattr(getattr(msg, 'from_user', None), 'id', 0) or 0), 0)
            except Exception:
                pass
            return
    except Exception:
        pass
    set_total_secret_mode(chat_id, False)
    if is_finance_output_suppressed(chat_id):
        return
    stop_dozvon_for_target(chat_id)
    store = get_chat_store(chat_id)
    set_finance_mode(chat_id, True)
    view_day = finance_today_key()
    store['current_view_day'] = view_day
    store.setdefault('settings', {})['auto_add'] = True
    save_data(data)
    schedule_finalize(chat_id, view_day)
    send_and_auto_delete(chat_id, '✅ Финансовый режим включён', HELPER_DELETE_DELAY)

@bot.message_handler(commands=['start'])
def cmd_start(msg):
    try:
        update_chat_info_from_message(msg)
    except Exception:
        pass
    schedule_command_delete(msg)
    try:
        if 'tenant_handle_start_payload' in globals() and tenant_handle_start_payload(msg):
            return
    except Exception as e:
        log_error(f'tenant start payload: {e}')
    chat_id = msg.chat.id
    set_total_secret_mode(chat_id, False)
    if is_finance_output_suppressed(chat_id):
        return
    stop_dozvon_for_target(chat_id)
    if guard_non_owner_finance_for_command(msg, {'ok', 'help'}):
        return
    if not require_finance(chat_id):
        return
    day_key = finance_today_key() if is_finance_mode(chat_id) else today_key()
    get_chat_store(chat_id)['current_view_day'] = day_key
    force_new_day_window(chat_id, day_key)

@bot.message_handler(commands=['help'])
def cmd_help(msg):
    try:
        update_chat_info_from_message(msg)
    except Exception:
        pass
    schedule_command_delete(msg)
    chat_id = msg.chat.id
    if is_finance_output_suppressed(chat_id):
        return
    stop_dozvon_for_target(chat_id)
    help_text = build_help_text(chat_id)
    send_and_auto_delete(chat_id, help_text, HELPER_DELETE_DELAY)

@bot.message_handler(commands=['articles', 'статьи'])
def cmd_articles(msg):
    try:
        update_chat_info_from_message(msg)
    except Exception:
        pass
    schedule_command_delete(msg)
    chat_id = msg.chat.id
    if is_finance_output_suppressed(chat_id):
        return
    send_and_auto_delete(chat_id, build_articles_description_text(chat_id), 40)

@bot.message_handler(commands=['restore'])
def cmd_restore(msg):
    """Compatibility registration. Final v182 handler replaces this function in runtime_control."""
    fn = globals().get('v182_cmd_restore')
    if callable(fn) and fn is not cmd_restore:
        return fn(msg)
    global restore_mode
    restore_mode = int(msg.chat.id)
    send_and_auto_delete(msg.chat.id, '📥 Режим восстановления включён. Отправьте GZ / JSON / ISON / CSV.')

@bot.message_handler(commands=['restore_off'])
def cmd_restore_off(msg):
    try:
        schedule_command_delete(msg)
    except Exception:
        pass
    global restore_mode
    restore_mode = None
    data.pop('_restore_mode_chat_v150', None)
    send_and_auto_delete(msg.chat.id, '🔒 Режим восстановления выключен.')

@bot.message_handler(commands=['ping'])
def cmd_ping(msg):
    try:
        update_chat_info_from_message(msg)
    except Exception:
        pass
    schedule_command_delete(msg)
    if guard_non_owner_finance_for_command(msg, {'ok', 'help'}):
        return
    stop_dozvon_for_target(msg.chat.id)
    send_and_auto_delete(msg.chat.id, 'PONG — бот работает 🟢', HELPER_DELETE_DELAY)

@bot.message_handler(commands=['prev'])
def cmd_prev(msg):
    try:
        update_chat_info_from_message(msg)
    except Exception:
        pass
    schedule_command_delete(msg)
    chat_id = msg.chat.id
    if is_finance_output_suppressed(chat_id):
        return
    stop_dozvon_for_target(chat_id)
    if guard_non_owner_finance_for_command(msg, {'ok', 'help'}):
        return
    if not require_finance(chat_id):
        return
    d = datetime.strptime(today_key(), '%Y-%m-%d') - timedelta(days=1)
    day_key = d.strftime('%Y-%m-%d')
    get_chat_store(chat_id)['current_view_day'] = day_key
    update_or_send_day_window(chat_id, day_key)

@bot.message_handler(commands=['next'])
def cmd_next(msg):
    try:
        update_chat_info_from_message(msg)
    except Exception:
        pass
    schedule_command_delete(msg)
    chat_id = msg.chat.id
    if is_finance_output_suppressed(chat_id):
        return
    stop_dozvon_for_target(chat_id)
    if guard_non_owner_finance_for_command(msg, {'ok', 'help'}):
        return
    if not require_finance(chat_id):
        return
    d = datetime.strptime(today_key(), '%Y-%m-%d') + timedelta(days=1)
    day_key = d.strftime('%Y-%m-%d')
    get_chat_store(chat_id)['current_view_day'] = day_key
    update_or_send_day_window(chat_id, day_key)

@bot.message_handler(commands=['balance'])
def cmd_balance(msg):
    try:
        update_chat_info_from_message(msg)
    except Exception:
        pass
    schedule_command_delete(msg)
    chat_id = msg.chat.id
    if is_finance_output_suppressed(chat_id):
        return
    stop_dozvon_for_target(chat_id)
    if guard_non_owner_finance_for_command(msg, {'ok', 'help'}):
        return
    if not require_finance(chat_id):
        return
    store = get_chat_store(chat_id)
    bal = store.get('balance', 0)
    send_info(chat_id, f'💰 Баланс: {fmt_num(bal)}')

@bot.message_handler(commands=['report'])
def cmd_report(msg):
    try:
        update_chat_info_from_message(msg)
    except Exception:
        pass
    schedule_command_delete(msg)
    chat_id = msg.chat.id
    if is_finance_output_suppressed(chat_id):
        return
    stop_dozvon_for_target(chat_id)
    if guard_non_owner_finance_for_command(msg, {'ok', 'help'}):
        return
    if not require_finance(chat_id):
        return
    lines = build_day_report_lines(chat_id)
    report_html = '<pre>' + html.escape('\n'.join(lines)) + '</pre>'
    send_html_and_auto_delete(chat_id, report_html, 20)

def cmd_csv_all(chat_id: int):
    """Canonical CSV for all history of the current ARS/USD view."""
    if is_finance_output_suppressed(chat_id):
        return
    if not require_finance(chat_id):
        return
    return send_export_for_chat_to(int(chat_id), int(chat_id), 'all', today_key(), 'csv')

def cmd_csv_day(chat_id: int, day_key: str):
    """CSV for one day from the same canonical ARS/USD ledger as Excel/Google."""
    if is_finance_output_suppressed(chat_id):
        return
    if not require_finance(chat_id):
        return
    return send_export_for_chat_to(int(chat_id), int(chat_id), 'day', str(day_key)[:10], 'csv')

@bot.message_handler(commands=['runtime_export'])
def cmd_runtime_export(msg):
    try:
        update_chat_info_from_message(msg)
    except Exception:
        pass
    schedule_command_delete(msg)
    chat_id = int(msg.chat.id)
    if 'tenant_require_platform_owner' in globals():
        if not tenant_require_platform_owner(msg):
            return
    elif not is_owner_chat(chat_id):
        send_and_auto_delete(chat_id, 'Эта команда только для владельца платформы.', 8)
        return
    start_dt, end_dt = _runtime_export_parse_range(getattr(msg, 'text', '') or '')
    ok, info = submit_interactive_file_job(chat_id, 'runtime', 'Runtime / Watcher ZIP', send_runtime_export_zip, chat_id, start_dt, end_dt)
    if not ok:
        send_and_auto_delete(chat_id, f'⏳ {info}. Новая копия в очередь не добавлена.', 12)

@bot.message_handler(commands=['tabl_lsx'])
def cmd_tabl_lsx(msg):
    try:
        update_chat_info_from_message(msg)
    except Exception:
        pass
    schedule_command_delete(msg)
    chat_id = msg.chat.id
    if is_finance_output_suppressed(chat_id):
        return
    stop_dozvon_for_target(chat_id)
    if guard_non_owner_finance_for_command(msg, {'ok', 'help', 'tabl_lsx'}):
        return
    if not require_finance(chat_id):
        return
    ok, info = submit_interactive_file_job(chat_id, 'tabl_lsx', 'Excel /tabl_lsx', send_tabl_lsx_for_chat, chat_id, chat_id)
    if not ok:
        send_and_auto_delete(chat_id, f'⏳ {info}. Новая копия в очередь не добавлена.', 12)

@bot.message_handler(commands=['xlsx', 'excel'])
def cmd_xlsx(msg):
    try:
        update_chat_info_from_message(msg)
    except Exception:
        pass
    schedule_command_delete(msg)
    chat_id = msg.chat.id
    if is_finance_output_suppressed(chat_id):
        return
    stop_dozvon_for_target(chat_id)
    if guard_non_owner_finance_for_command(msg, {'ok', 'help'}):
        return
    if not require_finance(chat_id):
        return
    ok, info = submit_interactive_file_job(chat_id, 'xlsx', 'Excel за всё время', send_export_for_chat_to, chat_id, chat_id, 'all', today_key(), 'xlsx')
    if not ok:
        send_and_auto_delete(chat_id, f'⏳ {info}. Новая копия в очередь не добавлена.', 10)

def _send_csv_current_chat_job(chat_id: int):
    """Canonical current-ledger CSV; same source as all Excel/Google tables."""
    try:
        _file_job_progress('собираю канонический CSV', force=True)
        ok = send_export_for_chat_to(int(chat_id), int(chat_id), 'all', today_key(), 'csv')
        try:
            send_backup_to_channel(chat_id)
        except Exception:
            pass
        return bool(ok is not False)
    except Exception as e:
        log_error(f'_send_csv_current_chat_job: {e}')
        return False

@bot.message_handler(commands=['csv'])
def cmd_csv(msg):
    try:
        update_chat_info_from_message(msg)
    except Exception:
        pass
    '\n    Экспортирует CSV текущего чата.\n    '
    schedule_command_delete(msg)
    chat_id = msg.chat.id
    if is_finance_output_suppressed(chat_id):
        return
    stop_dozvon_for_target(chat_id)
    if guard_non_owner_finance_for_command(msg, {'ok', 'help'}):
        return
    if not require_finance(chat_id):
        return
    ok, info = submit_interactive_file_job(chat_id, 'csv', 'CSV этого чата', _send_csv_current_chat_job, chat_id)
    if not ok:
        send_and_auto_delete(chat_id, f'⏳ {info}. Новая копия в очередь не добавлена.', 10)

def _send_json_snapshot_job(chat_id: int):
    started = time.time()
    try:
        bot_journal('json_export_start', chat_id, 'создание атомарного снимка')
        store = snapshot_chat_store(chat_id)
        payload = build_chat_backup_payload(chat_id, store)
        raw = json.dumps(payload, ensure_ascii=False, indent=2).encode('utf-8')
        buf = io.BytesIO(raw)
        buf.name = f"{mega_safe_name(get_chat_display_name(chat_id), 'chat')}_{now_local().strftime('%Y%m%d_%H%M%S')}.json"
        _file_job_progress('отправляю JSON в Telegram', force=True)
        sent = _tg_call_retry(bot.send_document, chat_id, buf, caption='🧾 JSON этого чата — последние операции сверху', timeout=120, purpose='manual_json_export')
        elapsed = time.time() - started
        bot_journal('json_export_sent', chat_id, f"bytes={len(raw)} message_id={getattr(sent, 'message_id', '')} elapsed={elapsed:.3f}s")
        return True
    except Exception as e:
        bot_journal('json_export_error', chat_id, f'elapsed={time.time() - started:.3f}s error={e}', 'ERROR')
        send_and_auto_delete(chat_id, '❌ Не удалось создать JSON. Ошибка записана в журнал.', 15)
        return False

@bot.message_handler(commands=['json'])
def cmd_json(msg):
    try:
        update_chat_info_from_message(msg)
    except Exception:
        pass
    schedule_command_delete(msg)
    chat_id = int(msg.chat.id)
    if is_finance_output_suppressed(chat_id):
        return
    stop_dozvon_for_target(chat_id)
    if guard_non_owner_finance_for_command(msg, {'ok', 'help'}):
        return
    if not require_finance(chat_id):
        return
    bot_journal('json_command', chat_id, f"message_id={getattr(msg, 'message_id', '')}")
    ok, info = submit_interactive_file_job(chat_id, 'json', 'JSON снимок чата', _send_json_snapshot_job, chat_id)
    if not ok:
        send_and_auto_delete(chat_id, f'⏳ {info}. Новая копия в очередь не добавлена.', 10)

@bot.message_handler(commands=['reset'])
def cmd_reset(msg):
    try:
        update_chat_info_from_message(msg)
    except Exception:
        pass
    schedule_command_delete(msg)
    chat_id = msg.chat.id
    if is_finance_output_suppressed(chat_id):
        return
    stop_dozvon_for_target(chat_id)
    if guard_non_owner_finance_for_command(msg, {'ok', 'help'}):
        return
    if not require_finance(chat_id):
        return
    store = get_chat_store(chat_id)
    store['reset_wait'] = True
    store['reset_time'] = time.time()
    save_data(data)
    send_and_auto_delete(chat_id, '⚠️ Вы уверены, что хотите обнулить данные? Напишите ДА в течение 15 секунд.', 15)
    schedule_cancel_wait(chat_id, 15)

@bot.message_handler(commands=['stopforward'])
def cmd_stopforward(msg):
    try:
        update_chat_info_from_message(msg)
    except Exception:
        pass
    schedule_command_delete(msg)
    chat_id = msg.chat.id
    if is_finance_output_suppressed(chat_id):
        return
    stop_dozvon_for_target(chat_id)
    if guard_non_owner_finance_for_command(msg, {'ok', 'help'}):
        return
    if not is_owner_chat(chat_id):
        send_info(chat_id, 'Эта команда только для владельца.')
        schedule_command_delete(msg)
        return
    clear_forward_all()
    send_info(chat_id, 'Пересылка полностью отключена.')

@bot.message_handler(commands=['backup_channel_on'])
def cmd_on_channel(msg):
    try:
        update_chat_info_from_message(msg)
    except Exception:
        pass
    schedule_command_delete(msg)
    chat_id = msg.chat.id
    if is_finance_output_suppressed(chat_id):
        return
    stop_dozvon_for_target(chat_id)
    if guard_non_owner_finance_for_command(msg, {'ok', 'help'}):
        return
    if 'tenant_require_platform_owner' in globals():
        if not tenant_require_platform_owner(msg):
            return
    elif not is_owner_chat(chat_id):
        send_and_auto_delete(chat_id, 'Эта команда только для владельца платформы.', HELPER_DELETE_DELAY)
        return
    backup_flags['channel'] = True
    try:
        set_storage_profile_v237_1('telegram_durable')
    except Exception:
        pass
    save_data(data)
    send_info(chat_id, '📡 Telegram durable включён; MEGA и «Только Render» выключены')

@bot.message_handler(commands=['backup_channel_off'])
def cmd_off_channel(msg):
    try:
        update_chat_info_from_message(msg)
    except Exception:
        pass
    schedule_command_delete(msg)
    chat_id = msg.chat.id
    if is_finance_output_suppressed(chat_id):
        return
    stop_dozvon_for_target(chat_id)
    if guard_non_owner_finance_for_command(msg, {'ok', 'help'}):
        return
    if 'tenant_require_platform_owner' in globals():
        if not tenant_require_platform_owner(msg):
            return
    elif not is_owner_chat(chat_id):
        send_and_auto_delete(chat_id, 'Эта команда только для владельца платформы.', HELPER_DELETE_DELAY)
        return
    backup_flags['channel'] = False
    try:
        if storage_profile_v237_1() == STORAGE_PROFILE_TELEGRAM_V237_1:
            set_storage_profile_v237_1('render')
    except Exception:
        pass
    save_data(data)
    send_info(chat_id, '📡 Telegram durable выключен; выбран «Только Render»')

@bot.message_handler(commands=['dozvon'])
def cmd_dozvon(msg):
    try:
        update_chat_info_from_message(msg)
    except Exception:
        pass
    schedule_command_delete(msg)
    chat_id = msg.chat.id
    if is_finance_output_suppressed(chat_id):
        return
    stop_dozvon_for_target(chat_id)
    if guard_non_owner_finance_for_command(msg, {'ok', 'help'}):
        return
    connected = get_connected_chat_ids(chat_id)
    if not connected:
        send_and_auto_delete(chat_id, '📞 Нет связанных чатов для дозвона.', HELPER_DELETE_DELAY)
        return
    bot.send_message(chat_id, '📞 Выберите чат для дозвона:', reply_markup=build_dozvon_menu(chat_id))

def _v177_legacy_0231_send_and_auto_delete(chat_id: int, text: str, delay: int=HELPER_DELETE_DELAY):
    if is_finance_output_suppressed(chat_id):
        return
    if chat_buttons_current_window_enabled(chat_id):
        send_or_edit_stored_window(chat_id, 'command_window_id', text, delay=delay)
        return
    try:
        msg = bot.send_message(chat_id, text)

        def _delete():
            try:
                bot.delete_message(chat_id, msg.message_id)
            except Exception:
                pass
        DELAYED_SCHEDULER.schedule(f'auto-delete:{chat_id}:{msg.message_id}', delay, _delete)
    except Exception as e:
        log_error(f'send_and_auto_delete: {e}')
try:
    _v177_legacy_0231_send_and_auto_delete.__name__ = 'send_and_auto_delete'
except Exception:
    pass

def _v177_legacy_0233_send_html_and_auto_delete(chat_id: int, html_text: str, delay: int=HELPER_DELETE_DELAY):
    if is_finance_output_suppressed(chat_id):
        return
    if chat_buttons_current_window_enabled(chat_id):
        send_or_edit_stored_window(chat_id, 'command_window_id', html_text, parse_mode='HTML', delay=delay)
        return
    try:
        msg = bot.send_message(chat_id, html_text, parse_mode='HTML')

        def _delete():
            try:
                bot.delete_message(chat_id, msg.message_id)
            except Exception:
                pass
        DELAYED_SCHEDULER.schedule(f'auto-delete-html:{chat_id}:{msg.message_id}', delay, _delete)
    except Exception as e:
        log_error(f'send_html_and_auto_delete: {e}')
try:
    _v177_legacy_0233_send_html_and_auto_delete.__name__ = 'send_html_and_auto_delete'
except Exception:
    pass

def delete_message_later(chat_id: int, message_id: int, delay: int=30):
    """
    Отложенное удаление сообщения пользователя (например, команд).
    """
    try:

        def _job():
            try:
                bot.delete_message(chat_id, message_id)
            except Exception:
                pass
        DELAYED_SCHEDULER.schedule(f'delete-later:{chat_id}:{message_id}', delay, _job)
    except Exception as e:
        log_error(f'delete_message_later: {e}')
_edit_cancel_timers = {}

def clear_edit_wait_state(chat_id: int, expected_prompt_id: int | None=None, delete_prompt: bool=True):
    store = get_chat_store(chat_id)
    edit_wait = store.get('edit_wait') or {}
    prompt_id = edit_wait.get('prompt_msg_id')
    if expected_prompt_id is not None and prompt_id and (int(prompt_id) != int(expected_prompt_id)):
        return False
    key = (int(chat_id), 'edit_wait')
    _edit_cancel_timers.pop(key, None)
    DELAYED_SCHEDULER.cancel(f'edit-wait:{int(chat_id)}')
    store['edit_wait'] = None
    if callable(globals().get('_v262_schedule_transient_chat_persist')):
        _v262_schedule_transient_chat_persist(chat_id)
    if delete_prompt and prompt_id:
        try:
            bot.delete_message(chat_id, int(prompt_id))
        except Exception:
            pass
    return True

def clear_finwin_edit_wait_state(chat_id: int, expected_prompt_id: int | None=None, delete_prompt: bool=True):
    store = get_chat_store(chat_id)
    edit_wait = store.get('finwin_edit_wait') or {}
    prompt_id = edit_wait.get('prompt_msg_id')
    if expected_prompt_id is not None and prompt_id and (int(prompt_id) != int(expected_prompt_id)):
        return False
    key = (int(chat_id), 'finwin_edit_wait')
    _edit_cancel_timers.pop(key, None)
    DELAYED_SCHEDULER.cancel(f'finwin-edit-wait:{int(chat_id)}')
    store['finwin_edit_wait'] = None
    if callable(globals().get('_v262_schedule_transient_chat_persist')):
        _v262_schedule_transient_chat_persist(chat_id)
    if delete_prompt and prompt_id:
        try:
            bot.delete_message(chat_id, int(prompt_id))
        except Exception:
            pass
    return True

def _edit_countdown_text(base_text: str, remaining: int) -> str:
    base = strip_window_mark(str(base_text or '')).rstrip()
    return wm_common(base + f'\n\n⏳ До закрытия: {int(remaining)} сек.', 10)

def schedule_cancel_finwin_edit(chat_id: int, prompt_message_id: int, delay: float | None=None):
    """Единый таймер фин-редактирования; timeout отменяет ввод и возвращает основное окно."""
    key = (int(chat_id), 'finwin_edit_wait')
    scheduler_key = f'finwin-edit-wait:{int(chat_id)}'
    if delay is None:
        delay = internal_timer_seconds('input_wait', 40)

    def _job():
        try:
            store = get_chat_store(chat_id)
            wait = store.get('finwin_edit_wait') or {}
            if not wait or int(wait.get('prompt_msg_id') or 0) != int(prompt_message_id):
                return
            cleared = clear_finwin_edit_wait_state(chat_id, prompt_message_id, delete_prompt=False)
            if cleared:
                day_key = store.get('current_view_day') or today_key()
                return_to_main_window_closing_previous(chat_id, day_key, int(prompt_message_id))
                log_info(f'finwin edit_wait auto-cancelled for chat {chat_id}')
        except Exception as e:
            log_error(f'schedule_cancel_finwin_edit({chat_id},{prompt_message_id}): {e}')
    DELAYED_SCHEDULER.cancel(scheduler_key)
    deadline = DELAYED_SCHEDULER.schedule(scheduler_key, float(delay), _job)
    _edit_cancel_timers[key] = deadline

def schedule_cancel_edit(chat_id: int, prompt_message_id: int, delay: float | None=None):
    """Единый таймер обычного редактирования; timeout отменяет ввод и возвращает основное окно."""
    key = (int(chat_id), 'edit_wait')
    scheduler_key = f'edit-wait:{int(chat_id)}'
    if delay is None:
        delay = internal_timer_seconds('input_wait', 40)

    def _job():
        try:
            store = get_chat_store(chat_id)
            wait = store.get('edit_wait') or {}
            if not wait or int(wait.get('prompt_msg_id') or 0) != int(prompt_message_id):
                return
            cleared = clear_edit_wait_state(chat_id, prompt_message_id, delete_prompt=False)
            if cleared:
                day_key = store.get('current_view_day') or today_key()
                return_to_main_window_closing_previous(chat_id, day_key, int(prompt_message_id))
        except Exception as e:
            log_error(f'schedule_cancel_edit({chat_id},{prompt_message_id}): {e}')
    DELAYED_SCHEDULER.cancel(scheduler_key)
    deadline = DELAYED_SCHEDULER.schedule(scheduler_key, float(delay), _job)
    _edit_cancel_timers[key] = deadline

def schedule_cancel_wait(chat_id: int, delay: float=15.0):
    """Через delay секунд сбрасывает reset_wait через общий планировщик."""
    scheduler_key = f'reset-wait:{int(chat_id)}'

    def _job():
        try:
            store = get_chat_store(chat_id)
            changed = False
            if store.get('reset_wait', False):
                store['reset_wait'] = False
                store['reset_time'] = 0
                changed = True
            if changed:
                save_data(data)
        except Exception as e:
            log_error(f'schedule_cancel_wait job: {e}')
    DELAYED_SCHEDULER.cancel(scheduler_key)
    deadline = DELAYED_SCHEDULER.schedule(scheduler_key, float(delay), _job)
    _edit_cancel_timers[int(chat_id)] = deadline

def _remember_known_chat_user(store: dict, msg) -> bool:
    """Кэширует пользователей, которых бот реально видел в чате.

    Telegram Bot API не выдаёт полный список участников группы, поэтому этот кэш
    дополняет список администраторов в окне «Описание чатов».
    """
    try:
        user = getattr(msg, 'from_user', None)
        if user is None or not getattr(user, 'id', None):
            return False
        uid = str(int(user.id))
        users = store.setdefault('known_users', {})
        old = dict(users.get(uid) or {})
        now_ts = time.time()
        row = {'id': int(user.id), 'first_name': str(getattr(user, 'first_name', '') or ''), 'last_name': str(getattr(user, 'last_name', '') or ''), 'username': str(getattr(user, 'username', '') or '').lstrip('@') or None, 'is_bot': bool(getattr(user, 'is_bot', False)), 'is_premium': bool(getattr(user, 'is_premium', False)), 'language_code': str(getattr(user, 'language_code', '') or '') or None, 'last_seen': old.get('last_seen') or now_local().isoformat(timespec='seconds'), 'last_seen_ts': float(old.get('last_seen_ts') or 0)}
        if now_ts - float(row.get('last_seen_ts') or 0) >= 3600 or not old:
            row['last_seen'] = now_local().isoformat(timespec='seconds')
            row['last_seen_ts'] = now_ts
        changed = old != row
        if changed:
            users[uid] = row
            if len(users) > 500:
                ordered = sorted(users.items(), key=lambda item: float((item[1] or {}).get('last_seen_ts') or 0))
                for old_uid, _ in ordered[:len(users) - 500]:
                    users.pop(old_uid, None)
        return changed
    except Exception:
        return False

def _v177_legacy_0235_update_chat_info_from_message(msg):
    """
    Обновляет информацию о чате в памяти.
    На диск пишем только если реально что-то изменилось.
    """
    chat_id = msg.chat.id
    was_new_chat = str(chat_id) not in (data.get('chats', {}) if isinstance(data, dict) else {})
    try:
        if not getattr(getattr(msg, 'from_user', None), 'is_bot', False):
            stop_dozvon_for_target(chat_id)
    except Exception:
        pass
    store = get_chat_store(chat_id)
    try:
        if store.setdefault('settings', {}).get('bot_removed'):
            store['settings']['bot_removed'] = False
            store['settings'].pop('bot_removed_reason', None)
            store['settings'].pop('bot_removed_at', None)
            save_data(data)
    except Exception:
        pass
    info = store.setdefault('info', {})
    info.setdefault('title', '')
    info.setdefault('username', None)
    info.setdefault('type', getattr(msg.chat, 'type', None))
    changed = False
    try:
        if getattr(getattr(msg, 'from_user', None), 'is_bot', False) and (not getattr(msg.chat, 'title', None)):
            return
    except Exception:
        pass
    new_title = _chat_title_from_message(msg, info.get('title') or '')
    new_username = _chat_username_from_message(msg)
    new_type = msg.chat.type
    if _remember_known_chat_user(store, msg):
        changed = True
    if info.get('title') != new_title:
        info['title'] = new_title
        changed = True
    if info.get('username') != new_username:
        info['username'] = new_username
        changed = True
    if info.get('type') != new_type:
        info['type'] = new_type
        changed = True
    if OWNER_ID and str(chat_id) != str(OWNER_ID):
        owner_store = get_chat_store(int(OWNER_ID))
        kc = owner_store.setdefault('known_chats', {})
        new_known = {'title': info.get('title') or get_chat_display_name(chat_id), 'username': info.get('username'), 'type': info.get('type')}
        new_identity = _chat_identity_key(chat_id, new_known)
        for old_cid, old_info in list(kc.items()):
            try:
                old_id_int = int(old_cid)
            except Exception:
                kc.pop(old_cid, None)
                changed = True
                continue
            if str(old_cid) != str(chat_id) and _chat_identity_key(old_id_int, old_info if isinstance(old_info, dict) else {}) == new_identity:
                kc.pop(old_cid, None)
                changed = True
        if kc.get(str(chat_id)) != new_known:
            kc[str(chat_id)] = new_known
            changed = True
    if changed:
        save_data(data)
        try:
            ids_for_backup = [chat_id]
            if OWNER_ID:
                ids_for_backup.append(int(OWNER_ID))
            schedule_config_backup_for_chats(*ids_for_backup, delay=2.0)
        except Exception as e:
            log_error(f'chat info changed backup schedule {chat_id}: {e}')
    try:
        if was_new_chat and OWNER_ID and (str(chat_id) != str(OWNER_ID)):
            maybe_prompt_owner_for_new_chat_auto_backup(chat_id)
    except Exception as e:
        log_error(f'new chat auto-backup prompt failed for {get_chat_display_name(chat_id)}: {e}')
try:
    _v177_legacy_0235_update_chat_info_from_message.__name__ = 'update_chat_info_from_message'
except Exception:
    pass

def maybe_prompt_owner_for_new_chat_auto_backup(chat_id: int):
    """При первом появлении чата спрашиваем владельца, обновлять ли JSON/CSV бэкапы автоматически."""
    if not OWNER_ID:
        return
    store = get_chat_store(chat_id)
    settings = store.setdefault('settings', {})
    if settings.get('owner_auto_backup_prompted'):
        return
    settings['owner_auto_backup_prompted'] = True
    settings.setdefault('auto_backup_enabled', True)
    save_data(data)
    owner_id = int(OWNER_ID)
    title = get_chat_display_name(chat_id)
    text = f'🆕 Новый чат появился в картотеке\n\n{title}\nАвтоматически обновлять JSON/CSV бэкапы по этому чату?'
    kb = types.InlineKeyboardMarkup(row_width=2)
    kb.row(IB('✅ Да', callback_data=f'ncb:{chat_id}:yes'), IB('❌ Нет', callback_data=f'ncb:{chat_id}:no'))
    msg = bot.send_message(owner_id, text, reply_markup=kb)
    settings['owner_auto_backup_prompt_msg_id'] = msg.message_id
    save_data(data)
    delete_message_later(owner_id, msg.message_id, 10)

def _safe_tmp_json_name(fname: str) -> str:
    base = os.path.basename(str(fname or 'backup.json'))
    base = re.sub('[^0-9A-Za-zА-Яа-я_.\\-]+', '_', base)
    if not base.lower().endswith('.json'):
        base += '.json'
    return base[:80]

def _extract_chat_id_from_json_filename(fname: str):
    """Пытается вытащить chat_id из имени data_<chat_id>.json."""
    try:
        m = re.search('(?:data|chat)_(-?\\d+)\\.(?:json|ison)$', str(fname or '').strip().lower())
        if m:
            return int(m.group(1))
    except Exception:
        pass
    return None

def _describe_json_restore_payload(payload, fname: str=''):
    """Возвращает короткое описание JSON перед подтверждением восстановления."""
    fname_l = str(fname or '').lower()
    if fname_l == 'csv_meta.json':
        return ('метаданные CSV', None)
    if isinstance(payload, dict) and isinstance(payload.get('chats'), dict):
        return (f"глобальный data.json, чатов: {len(payload.get('chats') or {})}", None)
    if isinstance(payload, dict):
        cid = payload.get('chat_id')
        if cid is None:
            cid = _extract_chat_id_from_json_filename(fname)
        if cid is not None:
            try:
                cid = int(cid)
                rec_count = len(payload.get('records') or []) if isinstance(payload.get('records'), list) else 0
                daily = payload.get('daily_records') or {}
                if isinstance(daily, dict):
                    rec_count = rec_count or sum((len(v or []) for v in daily.values()))
                return (f'JSON чата {get_chat_display_name(cid)} / ID {cid}, записей: {rec_count}', cid)
            except Exception:
                pass
    return ('JSON-файл неизвестного формата', None)

def _apply_json_restore_from_owner_prompt(owner_chat_id: int, tmp_path: str, fname: str) -> str:
    """
    Восстановление JSON, когда владелец прислал файл без /restore и нажал ✅ Да.
    Поддерживает:
    • глобальный data.json / JSON с ключом chats;
    • csv_meta.json;
    • per-chat JSON data_<chat_id>.json или JSON с chat_id.
    """
    global data, restore_mode
    fname_l = str(fname or '').lower()
    payload = _load_json(tmp_path, None)
    if not isinstance(payload, dict):
        raise RuntimeError('JSON повреждён или не является объектом')
    if fname_l == 'csv_meta.json':
        os.replace(tmp_path, CSV_META_FILE)
        _save_csv_meta(_load_json(CSV_META_FILE, {}) or {})
        restore_mode = None
        return '🟢 csv_meta.json обновлён'
    if fname_l == 'data.json' or isinstance(payload.get('chats'), dict):
        result = restore_from_json(int(owner_chat_id), tmp_path, actor_user_id=int(OWNER_ID or owner_chat_id))
        export_global_csv(data)
        restore_mode = None
        return f"🟢 Глобальный JSON полностью восстановлен; чатов: {result.get('chats', 0)}"
    target_chat_id = payload.get('chat_id')
    if target_chat_id is None:
        target_chat_id = _extract_chat_id_from_json_filename(fname_l)
    if target_chat_id is None:
        raise RuntimeError('В JSON нет chat_id и его нельзя понять из имени файла')
    target_chat_id = int(target_chat_id)
    result = restore_from_json(target_chat_id, tmp_path, actor_user_id=int(OWNER_ID or owner_chat_id))
    restore_mode = None
    return f"🟢 JSON/ISON чата восстановлен СТРОГО ИЗ ФАЙЛА: {get_chat_display_name(target_chat_id)}; в файле={result.get('backup_records', 0)}, итог={result.get('records_after', 0)}, предыдущее live-состояние заменено={result.get('replaced_live_records', 0)}"

def _cleanup_owner_json_restore_prompt(key: int, remove_prompt: bool=False):
    try:
        with _owner_json_restore_prompt_lock:
            item = _owner_json_restore_prompts.pop(int(key), None)
        if not item:
            return
        if remove_prompt:
            try:
                bot.delete_message(int(OWNER_ID), int(item.get('prompt_msg_id')))
            except Exception:
                pass
        tmp_path = item.get('tmp_path')
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except Exception:
                pass
    except Exception as e:
        log_error(f'_cleanup_owner_json_restore_prompt({key}): {e}')

def _schedule_owner_json_restore_prompt_cleanup(key: int, delay: int=12):

    def _job():
        _cleanup_owner_json_restore_prompt(key, remove_prompt=True)
    try:
        DELAYED_SCHEDULER.schedule(f'owner-json-restore-cleanup:{int(key)}', delay, _job)
    except Exception as e:
        log_error(f'_schedule_owner_json_restore_prompt_cleanup({key}): {e}')

def maybe_prompt_owner_for_json_restore(msg, fname: str) -> bool:
    """
    Если владелец прислал .json в личку без /restore — спрашиваем, обновлять данные или нет.
    Кнопки/окно удаляются через 10 секунд в любом случае.
    """
    try:
        if not is_owner_chat(msg.chat.id):
            return False
        if restore_mode is not None:
            return False
        if not str(fname or '').lower().endswith(('.json', '.ison')):
            return False
        file_info = bot.get_file(msg.document.file_id)
        tmp_name = f'owner_json_restore_{int(msg.chat.id)}_{int(msg.message_id)}_{_safe_tmp_json_name(fname)}'
        stream_fn = globals().get('telegram_download_to_file')
        if callable(stream_fn):
            max_restore = max(1024 * 1024, int(os.getenv('RESTORE_FILE_MAX_BYTES', str(100 * 1024 * 1024)) or str(100 * 1024 * 1024)))
            stream_fn(file_info.file_path, tmp_name, max_bytes=max_restore)
        else:
            raw = bot.download_file(file_info.file_path)
            with open(tmp_name, 'wb') as f:
                f.write(raw)
            raw = None
        payload = _load_json(tmp_name, None)
        if not isinstance(payload, dict):
            try:
                os.remove(tmp_name)
            except Exception:
                pass
            send_and_auto_delete(int(msg.chat.id), f'⚠️ JSON не прочитан или повреждён: {fname}', 10)
            return True
        desc, target_chat_id = _describe_json_restore_payload(payload, fname)
        key = int(msg.message_id)
        text = f'🧾 В чате владельца появился JSON-файл без /restore\n\nФайл: {fname}\nЧто внутри: {desc}\n\nОбновить данные бота из этого JSON?'
        kb = types.InlineKeyboardMarkup(row_width=2)
        kb.row(IB('✅ Да', callback_data=f'ojr:{key}:yes'), IB('❌ Нет', callback_data=f'ojr:{key}:no'))
        sent = bot.send_message(int(msg.chat.id), text, reply_markup=kb)
        with _owner_json_restore_prompt_lock:
            _owner_json_restore_prompts[key] = {'tmp_path': tmp_name, 'fname': fname, 'prompt_msg_id': sent.message_id, 'created_at': time.time(), 'target_chat_id': target_chat_id}
        delete_message_later(int(msg.chat.id), sent.message_id, 10)
        _schedule_owner_json_restore_prompt_cleanup(key, 12)
        return True
    except Exception as e:
        log_error(f'maybe_prompt_owner_for_json_restore({fname}): {e}')
        return False

def run_owner_json_restore_prompt_job(owner_chat_id: int, item: dict):
    tmp_path = item.get('tmp_path')
    fname = item.get('fname') or 'backup.json'
    pre_restore_dir = ''
    restore_epoch = 0
    restore_success = False
    try:
        backup_fn = globals().get('_v153_backup_before_restore')
        if not callable(backup_fn):
            raise RuntimeError('pre_restore backup helper недоступен')
        durable_ready = bool(globals().get('telegram_durable_primary_v234', lambda: False)())
        if not durable_ready and callable(globals().get('mega_is_configured')) and (not mega_is_configured()):
            raise RuntimeError('Внешнее durable-хранилище не настроено — восстановление остановлено')
        pre_restore_dir = backup_fn()
        bot_journal('restore_pre_backup_owner_prompt_v184', int(owner_chat_id), f'file={fname}')
        begin_restore = globals().get('_v241_restore_storage_barrier_begin')
        if callable(begin_restore):
            restore_epoch = int(begin_restore() or 0)
        with data_lock:
            result = _apply_json_restore_from_owner_prompt(owner_chat_id, tmp_path, fname)
        _v240_restore_reanchor_guaranteed(f'owner_json_prompt:{fname}')
        restore_success = True
        send_and_auto_delete(owner_chat_id, result + '\n🏛 DATA CONSTITUTION: состояние закреплено новым generation.', 15)
    except Exception as e:
        send_and_auto_delete(owner_chat_id, f'❌ JSON/ISON не восстановлен: {e}', 15)
    finally:
        if restore_epoch:
            end_restore = globals().get('_v241_restore_storage_barrier_end')
            if callable(end_restore):
                try:
                    end_restore(restore_epoch, restore_success)
                except Exception:
                    pass
        try:
            if pre_restore_dir:
                shutil.rmtree(pre_restore_dir, ignore_errors=True)
        except Exception:
            pass
        try:
            if tmp_path and os.path.exists(tmp_path):
                os.remove(tmp_path)
        except Exception:
            pass

# --- ИСТОЧНИК: 91_finance_records_handlers.py ---
def _canon_record_day_key__001(rec: dict) -> str:
    """Безопасно возвращает day_key для записи."""
    dk = rec.get('day_key')
    if dk:
        return str(dk)[:10]
    ts = rec.get('timestamp') or ''
    if isinstance(ts, str) and len(ts) >= 10 and re.match('\\d{4}-\\d{2}-\\d{2}', ts[:10]):
        rec['day_key'] = ts[:10]
        return ts[:10]
    rec['day_key'] = today_key()
    return rec['day_key']

def _v258_record_strong_keys(rec: dict, chat_id: int) -> list[str]:
    """Stable keys that prove two finance rows are the same Telegram effect.

    Deliberately excludes source_order_msg_id: forwarded copies may legitimately
    share an upstream order id while being different messages in this chat.
    """
    out = []
    try:
        op = str((rec or {}).get('operation_key') or '').strip()
        if op and op.startswith(f'finance:{int(chat_id)}:'):
            out.append('op:' + op)
    except Exception:
        pass
    for key in ('source_msg_id', 'origin_msg_id', 'msg_id'):
        try:
            mid = int((rec or {}).get(key) or 0)
            if mid:
                out.append(f'msg:{mid}')
        except Exception:
            pass
    return list(dict.fromkeys(out))

def _v258_merge_duplicate_finance_records(chat_id: int, records: list[dict]) -> tuple[list[dict], int]:
    """Collapse historical deploy/edit duplicates without merging real operations.

    Same Telegram message must produce one finance record.  The oldest record id
    is kept for button/reference stability, while editable finance fields are
    taken from the newest duplicate (the usual post-deploy edited copy).
    """
    cid = int(chat_id)
    out = []
    key_to_idx = {}
    removed = 0
    editable = ('amount','note','usd_amount','usd_note','usd_only','source_finance_text',
                'timestamp','day_key','owner','category_override_slug','currency')
    identity_fill = ('source_msg_id','origin_msg_id','msg_id','source_order_msg_id','operation_key')
    for raw in records or []:
        if not isinstance(raw, dict):
            continue
        rec = raw
        keys = _v258_record_strong_keys(rec, cid)
        matches = sorted({key_to_idx[k] for k in keys if k in key_to_idx})
        if not matches:
            idx = len(out)
            out.append(rec)
            for k in keys:
                key_to_idx[k] = idx
            continue
        idx = matches[0]
        base = out[idx]
        # If older corrupted state already created more than one canonical bucket
        # that this row bridges, fold those buckets too.
        for other_idx in reversed(matches[1:]):
            if other_idx == idx or other_idx >= len(out):
                continue
            other = out[other_idx]
            try:
                base_id = int(base.get('id') or 0)
                other_id = int(other.get('id') or 0)
            except Exception:
                base_id = other_id = 0
            newer = other if other_id >= base_id else base
            for fld in editable:
                if fld in newer:
                    base[fld] = newer.get(fld)
            for fld in identity_fill:
                if not base.get(fld) and other.get(fld):
                    base[fld] = other.get(fld)
            out.pop(other_idx)
            removed += 1
            # Rebuild map after structural fold; duplicate migrations are tiny and
            # correctness is more important than micro-optimizing this path.
            key_to_idx = {}
            for oi, rr in enumerate(out):
                for kk in _v258_record_strong_keys(rr, cid):
                    key_to_idx[kk] = oi
            idx = min(idx, len(out)-1)
            base = out[idx]
        try:
            base_id = int(base.get('id') or 0)
            rec_id = int(rec.get('id') or 0)
        except Exception:
            base_id = rec_id = 0
        newer = rec if rec_id >= base_id else base
        # Keep the canonical (usually oldest) record id/record_uid, but apply the
        # newest financial edit so an old dragon/emoji/text variant disappears.
        for fld in editable:
            if fld in newer:
                base[fld] = newer.get(fld)
        for fld in identity_fill:
            if not base.get(fld) and rec.get(fld):
                base[fld] = rec.get(fld)
        for k in set(keys + _v258_record_strong_keys(base, cid)):
            key_to_idx[k] = idx
        removed += 1
    return out, removed

def normalize_chat_records(chat_id: int) -> None:
    """
    v258: records — основной источник, daily_records строится из него.
    Сортировка стабильная: Telegram date + исходный message_id. Исторические
    дубли одной Telegram-записи после deploy/edit схлопываются по сильной
    идентичности, но независимые одинаковые суммы/описания не объединяются.
    """
    store = get_chat_store(chat_id)
    records = store.get('records')
    daily = store.get('daily_records') or {}
    if not isinstance(records, list) or not records:
        rebuilt = []
        for dk in sorted(daily.keys()):
            for rec in daily.get(dk, []) or []:
                if isinstance(rec, dict):
                    rec.setdefault('day_key', dk)
                    rebuilt.append(rec)
        records = rebuilt
    try:
        records, _v258_removed = _v258_merge_duplicate_finance_records(int(chat_id), list(records or []))
    except Exception as _v258_dedupe_exc:
        _v258_removed = 0
        try: log_error(f'v258 finance duplicate migration {chat_id}: {_v258_dedupe_exc}')
        except Exception: pass
    clean = []
    for rec in records or []:
        if not isinstance(rec, dict):
            continue
        rec.setdefault('timestamp', now_local().isoformat(timespec='seconds'))
        rec.setdefault('amount', 0)
        rec.setdefault('note', '')
        rec.setdefault('owner', '')
        rec.setdefault('source_order_msg_id', rec.get('source_msg_id') or rec.get('origin_msg_id') or rec.get('msg_id') or rec.get('id') or 0)
        _record_day_key(rec)
        try:
            if 'ensure_finance_record_uid' in globals():
                ensure_finance_record_uid(int(chat_id), rec)
        except Exception:
            pass
        clean.append(rec)
    clean.sort(key=record_sort_key)
    store['records'] = clean
    rebuilt_daily = {}
    for rec in clean:
        rebuilt_daily.setdefault(_record_day_key(rec), []).append(rec)
    store['daily_records'] = rebuilt_daily
    if _v258_removed:
        try:
            store['balance'] = sum((float(r.get('amount', 0) or 0) for r in clean))
            store['next_id'] = max([int(r.get('id', 0) or 0) for r in clean] + [0]) + 1
            store['_finance_dedupe_v258_removed'] = int(store.get('_finance_dedupe_v258_removed') or 0) + int(_v258_removed)
            if 'migrate_finance_source_index_v257' in globals():
                migrate_finance_source_index_v257(int(chat_id))
            bot_journal('finance_duplicate_collapsed_v258', int(chat_id), f'removed={int(_v258_removed)}')
        except Exception as _v258_post_exc:
            try: log_error(f'v258 finance duplicate post-normalize {chat_id}: {_v258_post_exc}')
            except Exception: pass

def recalc_balance(chat_id: int):
    normalize_chat_records(chat_id)
    store = get_chat_store(chat_id)
    store['balance'] = sum((float(r.get('amount', 0) or 0) for r in store.get('records', [])))

def rebuild_month_short_ids(chat_id: int):
    """Пересчитывает short_id как месячную нумерацию по стабильной хронологии."""
    normalize_chat_records(chat_id)
    store = get_chat_store(chat_id)
    daily = store.get('daily_records', {}) or {}
    month_counters = {}
    usd_month_counters = {}
    for dk in sorted(daily.keys()):
        month_key = dk[:7]
        month_counters.setdefault(month_key, 1)
        usd_month_counters.setdefault(month_key, 1)
        recs = sorted(daily.get(dk, []) or [], key=record_sort_key)
        daily[dk] = recs
        for r in recs:
            try:
                if 'ensure_finance_record_uid' in globals():
                    ensure_finance_record_uid(int(chat_id), r)
            except Exception:
                pass
            has_usd = bool(float(r.get('usd_amount', 0) or 0))
            usd_only = bool(r.get('usd_only', False))
            if not usd_only:
                r['short_id'] = f'R{month_counters[month_key]}'
                month_counters[month_key] += 1
            elif has_usd:
                r['short_id'] = f'U{usd_month_counters[month_key]}'
            if has_usd:
                r['usd_short_id'] = f'U{usd_month_counters[month_key]}'
                usd_month_counters[month_key] += 1
    store['records'] = [r for dk in sorted(daily.keys()) for r in daily.get(dk, [])]

def calc_day_balance(store: dict, day_key: str) -> float:
    """R16 fast closing balance: O(1) for the latest day, cached for history."""
    day_key = str(day_key or '')[:10]
    daily = store.get('daily_records', {}) or {}
    if not daily:
        return 0.0
    try:
        latest = max(str(k)[:10] for k in daily.keys())
        if day_key >= latest:
            return float(store.get('balance', 0) or 0)
    except Exception:
        pass
    gen = int(store.get('_finance_fast_generation_r16', 0) or 0)
    cache = store.setdefault('_finance_day_balance_cache_r16', {})
    cached = cache.get(day_key) if isinstance(cache, dict) else None
    if isinstance(cached, dict) and int(cached.get('generation', -1)) == gen:
        try: return float(cached.get('value', 0) or 0)
        except Exception: pass
    total = 0.0
    for dk in sorted(daily.keys()):
        if str(dk)[:10] > day_key:
            break
        for r in daily.get(dk, []) or []:
            total += float(r.get('amount', 0) or 0)
    try:
        cache[day_key] = {'generation': gen, 'value': float(total)}
        if len(cache) > 64:
            for key in list(cache)[:-64]: cache.pop(key, None)
    except Exception:
        pass
    return float(total)

def rebuild_global_records():
    """Быстрый общий итог без копирования всех записей всех чатов при каждом сообщении."""
    with data_lock:
        total = 0.0
        for _cid, store in (data.get('chats', {}) or {}).items():
            try:
                if 'balance' in store:
                    total += float(store.get('balance', 0) or 0)
                else:
                    total += sum((float(r.get('amount', 0) or 0) for r in store.get('records', []) or []))
            except Exception:
                pass
        data['records'] = []
        data['overall_balance'] = total
_finalize_timers = {}
_backup_timers = {}
_quick_backup_timers = {}
_balance_panel_refresh_timers = {}
_balance_panel_collapse_timers = {}
_balance_panel_first_timers = {}
_balance_panel_recreate_timers = {}
_total_message_timers = {}
_backup_dirty_chats = set()
_quick_backup_dirty_chats = set()
_global_mega_timer = None

def collect_finance_chat_ids():
    ids = set()
    try:
        for cid, enabled in (data.get('finance_active_chats', {}) or {}).items():
            if enabled:
                ids.add(int(cid))
    except Exception:
        pass
    try:
        for cid in list(finance_active_chats):
            ids.add(int(cid))
    except Exception:
        pass
    try:
        for cid, store in (data.get('chats', {}) or {}).items():
            try:
                int_cid = int(cid)
            except Exception:
                continue
            if store.get('finance_mode') or (OWNER_ID and str(int_cid) == str(OWNER_ID)):
                ids.add(int_cid)
    except Exception:
        pass
    return sorted(ids)

def _canon_schedule_startup_main_windows__001(delay: float=3.0):
    """v108: restore only automatic finance windows that were actually open before deploy."""

    def _job():
        try:
            for cid in collect_finance_chat_ids():
                try:
                    if is_chat_bot_removed(cid):
                        continue
                    store = get_chat_store(cid)
                    state = _finance_window_state(cid)
                    mode = finance_window_mode(cid)
                    if mode == 'off' or not bool(state.get('auto_reopen_on_boot', False)):
                        continue
                    day_key = store.get('current_view_day') or today_key()
                    if mode == 'normal':
                        update_or_send_day_window(cid, day_key)
                    elif mode in {'open', 'first'}:
                        if store.get('balance_panel_id'):
                            refresh_balance_panel_now(cid)
                        else:
                            send_minimized_balance_panel(cid)
                        if mode == 'first':
                            schedule_quick_balance_first_recreate(cid, 60.0)
                    time.sleep(0.2)
                except Exception as e:
                    log_error(f'startup_finance_window({get_chat_display_name(cid)}): {e}')
        except Exception as e:
            log_error(f'schedule_startup_main_windows job: {e}')
    try:
        DELAYED_SCHEDULER.schedule('startup-main-windows', delay, _job)
    except Exception as e:
        log_error(f'schedule_startup_main_windows: {e}')

def schedule_all_finance_backups(delay: float=10.0):
    for cid in collect_finance_chat_ids():
        schedule_backup_flush(cid, delay=delay)

def _schedule_global_mega_snapshot(delay: float=30.0):
    """Совместимость старых вызовов: v90 лишь отмечает pending full snapshot.

    Полный global больше не создаётся через 20–30 секунд после каждого чата.
    Его запускает общий quiet/max scheduler.
    """
    _mark_global_snapshot_pending()

def _run_quick_chat_backup(chat_id: int):
    """v90 quick backup = маленький immutable delta, а не полная копия чата/global."""
    chat_id = int(chat_id)
    if RESTORE_GUARD_ACTIVE:
        log_error(f'QUICK DELTA BLOCKED {chat_id}: {RESTORE_GUARD_REASON}')
        return
    with state_chat_context(chat_id):
        try:
            save_data(data, chat_ids=[chat_id])
            with _delta_state_lock:
                _delta_pending_chats.add(chat_id)
                if not _delta_chat_generation.get(chat_id):
                    _delta_chat_generation[chat_id] = int(time.time_ns())
            if not durable_run_pending_delta_now_v234():
                schedule_delta_backup(chat_id, BACKUP_BUSY_RETRY_SECONDS, reason='delta_retry')
        finally:
            with timer_lock:
                _quick_backup_dirty_chats.discard(chat_id)

def _run_full_chat_backup(chat_id: int, expected_epoch: int | None=None):
    chat_id = int(chat_id)
    if expected_epoch is not None and int(expected_epoch) != int(globals().get('_V241_STORAGE_EPOCH', 0) or 0):
        try:
            bot_journal('stale_full_backup_skipped_v241', chat_id, f"job={expected_epoch}; current={globals().get('_V241_STORAGE_EPOCH', 0)}")
        except Exception:
            pass
        return
    if globals().get('_V241_RESTORE_ACTIVE', False):
        return
    if RESTORE_GUARD_ACTIVE:
        log_error(f'FULL BACKUP BLOCKED {chat_id}: {RESTORE_GUARD_REASON}')
        return
    with state_chat_context(chat_id):
        try:
            if not is_finance_mode(chat_id):
                return
            if not is_auto_backup_enabled(chat_id):
                return
            save_data(data, chat_ids=[chat_id])
            save_chat_json(chat_id)
            if expected_epoch is not None and int(expected_epoch) != int(globals().get('_V241_STORAGE_EPOCH', 0) or 0):
                try:
                    bot_journal('stale_full_backup_midflight_skipped_v241', chat_id, f"job={expected_epoch}; current={globals().get('_V241_STORAGE_EPOCH', 0)}")
                except Exception:
                    pass
                return
            if globals().get('_V241_RESTORE_ACTIVE', False):
                return
            if is_backup_to_chat_enabled(chat_id) and can_receive_direct_json_backup(chat_id) and (not is_finance_output_suppressed(chat_id)):
                send_backup_to_chat(chat_id, ensure_files=False)
            if is_backup_to_channel_enabled(chat_id):
                send_backup_to_channel(chat_id, ensure_files=False)
            if is_backup_to_mega_enabled(chat_id):
                mega_upload_chat_backup_bundle(chat_id, current_month_key())
                _mark_global_snapshot_pending()
        except Exception as exc:
            log_error(f'_run_full_chat_backup({chat_id}): {exc}')
        finally:
            with timer_lock:
                _backup_dirty_chats.discard(chat_id)
                _backup_timers.pop(chat_id, None)
            try:
                _r24_lowram_release_if_pressure(chat_id)
            except Exception as _lr_exc:
                log_error(f'LOWRAM full-backup release {chat_id}: {_lr_exc}')

def schedule_quick_backup(chat_id: int, delay: float | None=None):
    """Debounce delta for one chat. Critical toggle callbacks defer async delta until their sync commit.

    Without this tiny guard, an async delta could persist the toggled state a fraction of a second
    before its idempotency marker. A deploy in that microscopic gap could replay the toggle twice.
    """
    chat_id = int(chat_id)
    try:
        ctx = getattr(_TELEGRAM_UPDATE_CONTEXT, 'value', None)
        if isinstance(ctx, dict) and ctx.get('critical_callback'):
            ctx.setdefault('deferred_quick_chats', set()).add(chat_id)
            return
    except Exception:
        pass
    if RESTORE_GUARD_ACTIVE:
        return
    if delay is None:
        delay = MEGA_DELTA_PRIORITY_DELAY_SECONDS if mega_backup_priority_enabled() else MEGA_DELTA_DELAY_SECONDS
    due = time.time() + max(0.5, float(delay))
    expected_epoch = int(globals().get('_V241_STORAGE_EPOCH', 0) or 0)
    with timer_lock:
        _quick_backup_dirty_chats.add(chat_id)
        _quick_backup_timers[chat_id] = due
    with _delta_state_lock:
        global _delta_generation
        _delta_generation += 1
        _delta_pending_chats.add(chat_id)
        _delta_chat_generation[chat_id] = _delta_generation

    def _fire():
        if expected_epoch != int(globals().get('_V241_STORAGE_EPOCH', 0) or 0) or globals().get('_V241_RESTORE_ACTIVE', False):
            with timer_lock:
                _quick_backup_dirty_chats.discard(chat_id)
            return

        def _job():
            if expected_epoch != int(globals().get('_V241_STORAGE_EPOCH', 0) or 0) or globals().get('_V241_RESTORE_ACTIVE', False):
                return
            if not durable_run_pending_delta_now_v234():
                schedule_delta_backup(None, delay=BACKUP_BUSY_RETRY_SECONDS, reason='quick_upload_retry')
        if not DELTA_TASK_POOL.submit('mega-delta-v90', _job):
            log_error(f'QUICK DELTA QUEUE FULL, RETRY: {chat_id}')
            schedule_quick_backup(chat_id, BACKUP_BUSY_RETRY_SECONDS)
    DELAYED_SCHEDULER.cancel('mega-delta-batch-v90')
    DELAYED_SCHEDULER.schedule('mega-delta-batch-v90', max(0.5, float(delay)), _fire)

def schedule_full_backup_only(chat_id: int, delay: float=3.0):
    """Тяжёлый JSON/канал/MEGA-файл чата — отдельно от быстрого delta."""
    chat_id = int(chat_id)
    if RESTORE_GUARD_ACTIVE:
        log_error(f'FULL BACKUP SCHEDULE BLOCKED {chat_id}: {RESTORE_GUARD_REASON}')
        return
    try:
        delay = max(float(delay or 0), BACKUP_MIN_DELAY_SECONDS)
    except Exception:
        delay = BACKUP_MIN_DELAY_SECONDS
    due = time.time() + delay
    expected_epoch = int(globals().get('_V241_STORAGE_EPOCH', 0) or 0)
    with timer_lock:
        _backup_dirty_chats.add(chat_id)
        _backup_timers[chat_id] = due

    def _fire():
        with timer_lock:
            _backup_timers.pop(chat_id, None)
        if expected_epoch != int(globals().get('_V241_STORAGE_EPOCH', 0) or 0) or globals().get('_V241_RESTORE_ACTIVE', False):
            with timer_lock:
                _backup_dirty_chats.discard(chat_id)
            return
        if not BACKUP_TASK_POOL.submit(f'full:{chat_id}', _run_full_chat_backup, chat_id, expected_epoch):
            log_error(f'FULL BACKUP QUEUE FULL, RETRY: {chat_id}')
            schedule_full_backup_only(chat_id, BACKUP_BUSY_RETRY_SECONDS)
    DELAYED_SCHEDULER.cancel(f'full-backup:{chat_id}')
    DELAYED_SCHEDULER.schedule(f'full-backup:{chat_id}', delay, _fire)

def schedule_backup_flush(chat_id: int, delay: float=3.0):
    """SQLite уже сохранена; delta быстро; тяжёлый файл чата — после экономичного idle debounce."""
    chat_id = int(chat_id)
    if RESTORE_GUARD_ACTIVE:
        log_error(f'BACKUP SCHEDULE BLOCKED {chat_id}: {RESTORE_GUARD_REASON}')
        return
    quick_delay = MEGA_DELTA_PRIORITY_DELAY_SECONDS if mega_backup_priority_enabled() else MEGA_DELTA_DELAY_SECONDS
    schedule_quick_backup(chat_id, quick_delay)
    schedule_full_backup_only(chat_id, delay)

def _safe_stabilize(action_name, func):
    try:
        return func()
    except Exception as e:
        log_error(f'[STABILIZE ERROR] {action_name}: {e}')
        try:
            bot_journal('stabilize_error', None, f'{action_name}: {e}', 'ERROR')
        except Exception:
            pass
        return None

# R48 FINAL: removed dead legacy owner _v177_legacy_0237_finance_changed_now; final owner is loaded later.

def _v177_legacy_0238_finance_changed(chat_id: int, day_key: str | None=None, reason: str='change', delay: float=0.35):
    """Debounced универсальный финальный пересчёт для одного чата."""
    chat_id = int(chat_id)
    bot_journal('finance_changed_scheduled', chat_id, f'day={day_key} reason={reason} delay={delay}')
    day_key = day_key or get_chat_store(chat_id).get('current_view_day') or today_key()

    def _job():
        if not FINANCE_TASK_POOL.submit(chat_id, _finance_changed_now, chat_id, day_key, reason):
            log_error(f'FINANCE QUEUE FULL, RETRY: {chat_id}')
            with timer_lock:
                _finalize_timers[chat_id] = time.time() + 1.0
            DELAYED_SCHEDULER.schedule(f'finance-finalize:{chat_id}', 1.0, _fire_finance)
    with timer_lock:
        _finalize_timers[chat_id] = time.time() + max(0.0, float(delay))

    def _fire_finance():
        with timer_lock:
            _finalize_timers.pop(chat_id, None)
        _job()
    DELAYED_SCHEDULER.schedule(f'finance-finalize:{chat_id}', delay, _fire_finance)

def _v177_legacy_0239_schedule_finalize(chat_id: int, day_key: str, delay: float=0.35):
    """Совместимость со старым кодом: теперь всё идёт через finance_changed()."""
    return finance_changed(chat_id, day_key, reason='schedule_finalize', delay=delay)

def _v177_legacy_0240_backup_window_for_owner(chat_id: int, day_key: str, message_id_override: int | None=None):
    """
    Окно дня для владельца без document-caption.
    JSON-бэкапы отправляются отдельно через schedule_backup_flush().
    """
    lock = window_locks[chat_id, day_key]
    with lock:
        txt, _ = render_day_window(chat_id, day_key)
        kb = build_main_keyboard(day_key, chat_id)
        if len(txt) > 3900:
            log_error(f'backup_window_for_owner: text too long for {chat_id} {day_key}, len={len(txt)}')
        mid = message_id_override or get_active_window_id(chat_id, day_key)
        if message_id_override:
            try:
                set_active_window_id(chat_id, day_key, message_id_override)
            except Exception:
                pass
        if mid:
            try:
                result = fast_ui_edit_message_text(chat_id, mid, txt, reply_markup=kb, parse_mode='HTML', purpose='main_day_background_v178')
            except Exception:
                result = 'failed'
            if str(result or '') in {'ok', 'scheduled'}:
                set_active_window_id(chat_id, day_key, mid)
                return result
            if str(result or '') == 'not_found':
                try:
                    aw = get_or_create_active_windows(chat_id)
                    if aw.get(day_key) == mid:
                        aw.pop(day_key, None)
                        save_data(data)
                except Exception:
                    pass
                try:
                    delete_async = globals().get('v177_delete_message_async')
                    if callable(delete_async):
                        delete_async(chat_id, mid, 'main_day_replace_v178')
                except Exception:
                    pass
            elif str(result or '') not in {'rate_limited', 'failed'}:
                return result
        sent = bot.send_message(chat_id, txt, reply_markup=kb, parse_mode='HTML')
        set_active_window_id(chat_id, day_key, sent.message_id)
try:
    _v177_legacy_0240_backup_window_for_owner.__name__ = 'backup_window_for_owner'
except Exception:
    pass

def cancel_auto_delete_for_message(chat_id: int, message_id: int):
    """Если окно с автоудалением превращается кнопкой «Назад» в основное — его старый таймер больше не должен удалить О1."""
    chat_id = int(chat_id)
    message_id = int(message_id)
    try:
        _cancel_v98_auto_close(chat_id, message_id)
    except Exception:
        pass
    for key in (f'auto-delete:{chat_id}:{message_id}', f'auto-delete-html:{chat_id}:{message_id}', f'delete-later:{chat_id}:{message_id}'):
        try:
            DELAYED_SCHEDULER.cancel(key)
        except Exception:
            pass
    try:
        store = get_chat_store(chat_id)
        was_total_window = int(store.get('total_msg_id') or 0) == message_id
        for timer_key in list(_aux_window_timers.keys()):
            try:
                timer_chat_id, store_key = timer_key
                if int(timer_chat_id) != chat_id:
                    continue
                if int(store.get(str(store_key)) or 0) != message_id:
                    continue
            except Exception:
                continue
            DELAYED_SCHEDULER.cancel(f'stored-window-delete:{chat_id}:{store_key}')
            _aux_window_timers.pop(timer_key, None)
            store[str(store_key)] = None
        if was_total_window:
            DELAYED_SCHEDULER.cancel(f'owner-total-delete:{chat_id}')
            _total_message_timers.pop(chat_id, None)
            store['total_msg_id'] = None
    except Exception as e:
        log_error(f'cancel_auto_delete_for_message({chat_id},{message_id}): {e}')

def recreate_main_window_now(chat_id: int, day_key: str):
    """Удаляет старое о1, если возможно, и создаёт новое основное окно."""
    try:
        old_mid = get_active_window_id(chat_id, day_key)
        if old_mid:
            try:
                bot.delete_message(chat_id, int(old_mid))
            except Exception:
                pass
            try:
                clear_active_window_id(chat_id, day_key)
            except Exception:
                pass
    except Exception:
        pass
    force_new_day_window(chat_id, day_key)

def _v177_legacy_0241_force_new_day_window(chat_id: int, day_key: str):
    txt, _ = render_day_window(chat_id, day_key)
    kb = build_main_keyboard(day_key, chat_id)
    sent = bot.send_message(chat_id, txt, reply_markup=kb, parse_mode='HTML')
    set_active_window_id(chat_id, day_key, sent.message_id)
    schedule_balance_panel_refresh(chat_id, 0.5)
try:
    _v177_legacy_0241_force_new_day_window.__name__ = 'force_new_day_window'
except Exception:
    pass

def _v177_legacy_0242_return_to_main_window_closing_previous(chat_id: int, day_key: str, current_message_id: int | None=None):
    """Return to О1 without promoting a missing/stale Telegram message to active."""
    chat_id = int(chat_id)
    try:
        current_message_id = int(current_message_id) if current_message_id is not None else None
    except Exception:
        current_message_id = None
    try:
        if current_message_id is not None:
            cancel_auto_delete_for_message(chat_id, current_message_id)
            cancel_fast_ui_edit(chat_id, current_message_id)
    except Exception:
        pass
    try:
        old_mid = get_active_window_id(chat_id, day_key)
        old_mid = int(old_mid) if old_mid else None
    except Exception:
        old_mid = None
    txt, _ = render_day_window(chat_id, day_key)
    kb = build_main_keyboard(day_key, chat_id)
    if current_message_id is not None:
        result = fast_ui_edit_message_text(chat_id, current_message_id, txt, reply_markup=kb, parse_mode='HTML', purpose='back_main_instant')
        bot_journal('back_main_fast', chat_id, f'day={day_key} result={result} old={old_mid} current={current_message_id}')
        if result in {'ok', 'scheduled'}:
            set_active_window_id(chat_id, day_key, current_message_id)
            if old_mid and old_mid != current_message_id:

                def _delete_old():
                    try:
                        _tg_call_retry(bot.delete_message, chat_id, int(old_mid), attempts=1, purpose='back_main_delete_old')
                    except Exception:
                        pass
                    finally:
                        try:
                            unregister_open_window(chat_id, int(old_mid))
                        except Exception:
                            pass
                GENERAL_TASK_POOL.submit(f'back-delete:{chat_id}:{old_mid}', _delete_old)
            schedule_balance_panel_refresh(chat_id, 0.05)
            return
        if result == 'not_found':
            try:
                unregister_open_window(chat_id, current_message_id)
            except Exception:
                pass
            try:
                if get_active_window_id(chat_id, day_key) == current_message_id:
                    clear_active_window_id(chat_id, day_key)
                    old_mid = None
            except Exception:
                pass
        if old_mid and old_mid != current_message_id:

            def _refresh_existing():
                try:
                    backup_window_for_owner(chat_id, day_key, message_id_override=old_mid)
                except Exception as exc:
                    log_error(f'back_main preserve old({chat_id},{day_key},{old_mid}): {exc}')
            GENERAL_TASK_POOL.submit(f'back-preserve:{chat_id}:{old_mid}', _refresh_existing)
            return

    def _send_fallback():
        try:
            update_or_send_day_window(chat_id, day_key)
        except Exception as e:
            log_error(f'return_to_main fallback({chat_id},{day_key}): {e}')
    if not GENERAL_TASK_POOL.submit(f'back-send:{chat_id}', _send_fallback):
        _send_fallback()
try:
    _v177_legacy_0242_return_to_main_window_closing_previous.__name__ = 'return_to_main_window_closing_previous'
except Exception:
    pass


def reset_chat_data(chat_id: int):
    """R48: reset mutates RAM under lock; cleanup/UI/SQLite run after unlock."""
    try:
        with locked_chat(chat_id):
            store=get_chat_store(chat_id)
            store['balance']=0; store['records']=[]; store['daily_records']={}; store['next_id']=1; store['active_windows']={}
            store['edit_target']=None; store['reset_wait']=False; store['reset_time']=0
            day_key=store.get('current_view_day',today_key())
        try: cleanup_forward_links(chat_id)
        except Exception: pass
        try: clear_edit_wait_state(chat_id,delete_prompt=True)
        except Exception: pass
        save_data(data,chat_ids=[int(chat_id)])
        finance_changed(chat_id,day_key,reason='reset',delay=0.1)
    except Exception as e:
        log_error(f'reset_chat_data({chat_id}): {e}')


def handle_document(msg):
    global restore_mode, data
    chat_id = msg.chat.id
    update_chat_info_from_message(msg)
    if handle_secret_input_message(msg):
        return
    try:
        if not getattr(getattr(msg, 'from_user', None), 'is_bot', False):
            bump_quick_balance_recreate_counter(chat_id)
            stop_dozvon_for_target(chat_id)
    except Exception:
        pass
    file = msg.document
    fname = (file.file_name or '').lower()
    log_info(f'[DOC] recv chat={chat_id} restore={restore_mode} fname={fname}')
    if restore_mode is None and is_owner_chat(chat_id) and fname.endswith(('.json', '.ison')):
        if maybe_prompt_owner_for_json_restore(msg, fname):
            return
    if restore_mode is not None and restore_mode == chat_id:
        if not (fname.endswith('.json') or fname.endswith('.ison') or fname.endswith('.csv') or fname.endswith('.gz')):
            send_and_auto_delete(chat_id, '⚠️ В режиме восстановления принимаются GZ / JSON / ISON / CSV.')
            return
        if fname.endswith('.gz'):
            try:
                prep = globals().get('v182_prepare_gz_restore_document')
                if not callable(prep):
                    raise RuntimeError('GZ restore helper не загружен')
                prep(msg, file)
            except Exception as e:
                send_and_auto_delete(chat_id, f'❌ GZ не подготовлен: {e}', 15)
            return
        tmp_path = f'restore_{chat_id}_{fname}'
        try:
            file_info = bot.get_file(file.file_id)
            stream_fn = globals().get('telegram_download_to_file')
            if callable(stream_fn):
                max_restore = max(1024 * 1024, int(os.getenv('RESTORE_FILE_MAX_BYTES', str(100 * 1024 * 1024)) or str(100 * 1024 * 1024)))
                stream_fn(file_info.file_path, tmp_path, max_bytes=max_restore)
            else:
                raw = bot.download_file(file_info.file_path)
                with open(tmp_path, 'wb') as f:
                    f.write(raw)
                raw = None
        except Exception as e:
            try:
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)
            except Exception:
                pass
            send_and_auto_delete(chat_id, f'❌ Ошибка скачивания: {e}')
            return
        backup_dir = ''
        restore_epoch = 0
        restore_success = False
        try:
            begin_restore = globals().get('_v241_restore_storage_barrier_begin')
            if callable(begin_restore):
                restore_epoch = int(begin_restore() or 0)
            try:
                backup_fn = globals().get('_v153_backup_before_restore')
                if callable(backup_fn):
                    backup_dir = str(backup_fn() or '')
                    bot_journal('restore_pre_backup_ok_v240', chat_id, f'file={fname}')
                else:
                    bot_journal('restore_pre_backup_unavailable_v240', chat_id, f'file={fname}', 'WARN')
            except Exception as pre_exc:
                log_error(f'pre_restore best-effort before file restore: {pre_exc}')
                try:
                    bot_journal('restore_pre_backup_failed_v240', chat_id, str(pre_exc)[:400], 'WARN')
                except Exception:
                    pass
            if fname == 'csv_meta.json':
                os.replace(tmp_path, CSV_META_FILE)
                _save_csv_meta(_load_json(CSV_META_FILE, {}) or {})
                restore_mode = None
                data.pop('_restore_mode_chat_v150', None)
                save_data(data, chat_ids=[chat_id])
                _v240_restore_reanchor_guaranteed('csv_meta_restore_exact')
                restore_success = True
                send_and_auto_delete(chat_id, '🟢 csv_meta.json импортирован и точно закреплён в durable-хранилище')
                return
            if fname.endswith(('.json', '.ison')):
                payload = _load_json(tmp_path, None)
                if not isinstance(payload, dict):
                    raise RuntimeError('JSON/ISON не является объектом')
                uid = int(getattr(getattr(msg, 'from_user', None), 'id', 0) or 0)
                platform_owner = bool(uid and (uid == int(OWNER_ID or 0) or ('_v153_platform_owner' in globals() and _v153_platform_owner(uid))))
                if isinstance(payload.get('chats'), dict) or fname in {'data.json', 'data.ison'}:
                    result = restore_from_json(chat_id, tmp_path, actor_user_id=uid)
                    restore_mode = None
                    data.pop('_restore_mode_chat_v150', None)
                    _v240_restore_reanchor_guaranteed('global_json_restore_exact')
                    restore_success = True
                    send_and_auto_delete(chat_id, f"🟢 Полный JSON/ISON всего бота восстановлен и закреплён. Чатов: {result.get('chats', 0)}", 18)
                    return
                inner_chat_id = payload.get('chat_id')
                if inner_chat_id is None:
                    inner_chat_id = _extract_chat_id_from_json_filename(fname) if '_extract_chat_id_from_json_filename' in globals() else None
                if inner_chat_id is None:
                    raise RuntimeError('В JSON/ISON нет chat_id')
                target_chat_id = int(inner_chat_id)
                if target_chat_id != int(chat_id) and (not platform_owner):
                    allowed = False
                    try:
                        allowed = bool(_v153_can_manage_tenant(uid, _v153_tenant_for_chat(target_chat_id)) and _v153_tenant_for_chat(target_chat_id) == _v153_tenant_for_chat(chat_id))
                    except Exception:
                        allowed = False
                    if not allowed:
                        raise RuntimeError(f'Файл относится к чату {target_chat_id}; нет прав восстановить его из текущего контура')
                result = restore_from_json(target_chat_id, tmp_path, actor_user_id=uid)
                restore_mode = None
                data.pop('_restore_mode_chat_v150', None)
                _v240_restore_reanchor_guaranteed(f'chat_json_restore_exact:{target_chat_id}')
                restore_success = True
                settings_count = int((result.get('settings') or {}).get('settings_keys') or 0)
                send_and_auto_delete(chat_id, f"🟢 JSON/ISON восстановлен СТРОГО ИЗ ФАЙЛА: {get_chat_display_name(target_chat_id)}\nЗаписей в файле: {result.get('backup_records', 0)}\nЗаписей после restore: {result.get('records_after', 0)}\nПредыдущее live-состояние заменено: {result.get('replaced_live_records', 0)} записей\nВосстановлено настроек: {settings_count}\nНичего из текущего состояния не подмешивалось.", 22)
                return
            if fname.startswith('data_') and fname.endswith('.csv'):
                restore_from_csv(chat_id, tmp_path)
                day_key = get_chat_store(chat_id).get('current_view_day', today_key())
                finance_changed(chat_id, day_key, reason='restore_csv', delay=0.1)
                restore_mode = None
                data.pop('_restore_mode_chat_v150', None)
                save_data(data, chat_ids=[chat_id])
                _v240_restore_reanchor_guaranteed(f'chat_csv_restore_exact:{chat_id}')
                restore_success = True
                send_and_auto_delete(chat_id, f'🟢 CSV чата восстановлен и точно закреплён ({fname})')
                return
            send_and_auto_delete(chat_id, f'⚠️ Неизвестный файл: {fname}')
        except Exception as e:
            send_and_auto_delete(chat_id, f'❌ Ошибка восстановления: {e}')
        finally:
            if restore_epoch:
                end_restore = globals().get('_v241_restore_storage_barrier_end')
                if callable(end_restore):
                    try:
                        end_restore(restore_epoch, restore_success)
                    except Exception:
                        pass
            try:
                os.remove(tmp_path)
            except Exception:
                pass
            try:
                if backup_dir:
                    shutil.rmtree(backup_dir, ignore_errors=True)
            except Exception:
                pass
        return
    try:
        schedule_forward_any_message(chat_id, msg)
    except Exception as e:
        log_error(f'handle_document forward failed: {e}')

def cleanup_forward_links(chat_id: int):
    """
    Удаляет все связи пересылки для чата из памяти и из сохранённого индекса.
    """
    _cleanup_forward_storage_for_chat(chat_id)
KEEP_ALIVE_SEND_TO_OWNER = False
KEEPALIVE_CONFIG_KEY = 'keepalive_v205'
KEEPALIVE_SAFE_INTERVALS = (300, 480, 600, 720, 840)
KEEPALIVE_AUTO_SAFE_IDLE_SECONDS = (600, 660, 720, 780, 840)
KEEPALIVE_AUTO_DEFAULT_IDLE_SECONDS = 720
KEEPALIVE_MIN_SECONDS = 60
KEEPALIVE_MAX_SECONDS = 3600
KEEP_ALIVE_STATE = {'started_at': None, 'last_attempt_at': None, 'last_ok_at': None, 'last_error': '', 'last_status_code': None, 'ok_count': 0, 'fail_count': 0, 'self_ping_at': None, 'external_ping_at': None, 'external_monitor_at': None, 'peer_received_at': None, 'last_keepalive_user_agent': '', 'last_inbound_activity_at': None, 'last_inbound_activity_kind': '', 'auto_last_trigger_at': None, 'auto_last_reason': '', 'auto_trigger_count': 0, 'peer_started_at': None, 'peer_last_attempt_at': None, 'peer_last_ok_at': None, 'peer_last_error': '', 'peer_last_status_code': None, 'peer_ok_count': 0, 'peer_fail_count': 0}
_keep_alive_thread = None
_peer_keep_alive_thread = None
_keep_alive_thread_lock = threading.RLock()
_keep_alive_wakeup = threading.Event()
_peer_keep_alive_wakeup = threading.Event()
_KEEPALIVE_INPUT_LOCK = threading.RLock()
_KEEPALIVE_INPUT_WAIT = {}
_KEEPALIVE_RUNTIME_STARTED_MONO = time.monotonic()
_KEEPALIVE_LAST_EXTERNAL_MONO = _KEEPALIVE_RUNTIME_STARTED_MONO
_KEEPALIVE_AUTO_LAST_PING_MONO = 0.0
_KEEPALIVE_ACTIVITY_LOCK = threading.RLock()
_PEER_FAIL_LOG_LOCK_V238 = threading.RLock()
_PEER_FAIL_LAST_KEY_V238 = ''
_PEER_FAIL_LAST_LOG_MONO_V238 = 0.0
_PEER_FAIL_LOG_COOLDOWN_V238 = 1800.0

def _keepalive_env_bool(name: str, default: bool=False) -> bool:
    raw = str(os.getenv(name, '1' if default else '0') or '').strip().lower()
    return raw in {'1', 'true', 'yes', 'y', 'on', 'да'}

def _keepalive_clamp_interval(value, default: int=600) -> int:
    try:
        return max(KEEPALIVE_MIN_SECONDS, min(KEEPALIVE_MAX_SECONDS, int(value)))
    except Exception:
        return int(default)

def _keepalive_root(create: bool=True) -> dict:
    try:
        gs = data.setdefault('_global_settings', {}) if create else data.get('_global_settings') or {}
    except Exception:
        return {}
    root = gs.get(KEEPALIVE_CONFIG_KEY)
    if not isinstance(root, dict):
        if not create:
            return {}
        root = {}
        gs[KEEPALIVE_CONFIG_KEY] = root
    root['schema'] = 2
    root.setdefault('self_enabled', bool(KEEP_ALIVE_ENABLED))
    root.setdefault('self_interval_seconds', int(KEEP_ALIVE_INTERVAL_SECONDS))
    root.setdefault('auto_enabled', _keepalive_env_bool('KEEP_ALIVE_AUTO_ENABLED', True))
    root.setdefault('auto_idle_seconds', _keepalive_clamp_interval(os.getenv('KEEP_ALIVE_AUTO_IDLE_SECONDS', str(KEEPALIVE_AUTO_DEFAULT_IDLE_SECONDS)), KEEPALIVE_AUTO_DEFAULT_IDLE_SECONDS))
    root.setdefault('peer_enabled', _keepalive_env_bool('PEER_KEEPALIVE_ENABLED', False))
    root.setdefault('peer_interval_seconds', _keepalive_clamp_interval(os.getenv('PEER_KEEPALIVE_INTERVAL_SECONDS', '600'), 600))
    root.setdefault('peer_url', str(os.getenv('PEER_KEEPALIVE_URL', '') or '').strip())
    root.setdefault('updated_at', '')
    return root

def _keepalive_persist(reason: str='settings') -> None:
    root = _keepalive_root(True)
    try:
        root['updated_at'] = now_local().isoformat(timespec='seconds')
    except Exception:
        root['updated_at'] = _journal_ts()
    try:
        save_data(data, root_only=True)
    except TypeError:
        save_data(data)
    except Exception as exc:
        try:
            log_error(f'keepalive save: {exc}')
        except Exception:
            pass
    try:
        fn = globals().get('schedule_delta_backup')
        if callable(fn):
            fn(None, delay=0.8, reason=f'keepalive:{str(reason)[:80]}')
    except Exception:
        pass
    try:
        bot_journal('keepalive_setting', int(OWNER_ID or 0) or None, str(reason)[:300])
    except Exception:
        pass

def keepalive_self_enabled() -> bool:
    gate = globals().get('external_access_allowed_v233')
    if callable(gate) and (not gate('self_http')):
        return False
    return bool(_keepalive_root(True).get('self_enabled', bool(KEEP_ALIVE_ENABLED)))

def keepalive_self_interval_seconds() -> int:
    root = _keepalive_root(True)
    value = _keepalive_clamp_interval(root.get('self_interval_seconds', KEEP_ALIVE_INTERVAL_SECONDS), int(KEEP_ALIVE_INTERVAL_SECONDS))
    root['self_interval_seconds'] = value
    return value

def set_keepalive_self_enabled(enabled: bool, persist: bool=True) -> bool:
    enabled = bool(enabled)
    _keepalive_root(True)['self_enabled'] = enabled
    globals()['KEEP_ALIVE_ENABLED'] = enabled
    _keep_alive_wakeup.set()
    if persist:
        _keepalive_persist(f'self_enabled={int(enabled)}')
    return enabled

def set_keepalive_self_interval(seconds: int, persist: bool=True) -> int:
    value = _keepalive_clamp_interval(seconds, 600)
    _keepalive_root(True)['self_interval_seconds'] = value
    globals()['KEEP_ALIVE_INTERVAL_SECONDS'] = value
    _keep_alive_wakeup.set()
    if persist:
        _keepalive_persist(f'self_interval={value}')
    return value

def keepalive_auto_enabled() -> bool:
    gate = globals().get('external_access_allowed_v233')
    if callable(gate) and (not gate('self_http')):
        return False
    return bool(_keepalive_root(True).get('auto_enabled', True))

def keepalive_auto_idle_seconds() -> int:
    root = _keepalive_root(True)
    value = _keepalive_clamp_interval(root.get('auto_idle_seconds', KEEPALIVE_AUTO_DEFAULT_IDLE_SECONDS), KEEPALIVE_AUTO_DEFAULT_IDLE_SECONDS)
    value = max(300, min(840, int(value)))
    root['auto_idle_seconds'] = value
    return value

def set_keepalive_auto_enabled(enabled: bool, persist: bool=True) -> bool:
    enabled = bool(enabled)
    _keepalive_root(True)['auto_enabled'] = enabled
    _keep_alive_wakeup.set()
    if persist:
        _keepalive_persist(f'auto_enabled={int(enabled)}')
    return enabled

def set_keepalive_auto_idle_seconds(seconds: int, persist: bool=True) -> int:
    value = max(300, min(840, _keepalive_clamp_interval(seconds, KEEPALIVE_AUTO_DEFAULT_IDLE_SECONDS)))
    _keepalive_root(True)['auto_idle_seconds'] = value
    _keep_alive_wakeup.set()
    if persist:
        _keepalive_persist(f'auto_idle={value}')
    return value

def keepalive_note_inbound_activity(kind: str='external') -> None:
    """Record real inbound traffic that can keep Render awake.

    Self-ping is deliberately NOT recorded here. Telegram/web/user/peer traffic
    postpones the automatic fallback. Render local health checks are not routed here.
    """
    global _KEEPALIVE_LAST_EXTERNAL_MONO
    now_m = time.monotonic()
    with _KEEPALIVE_ACTIVITY_LOCK:
        _KEEPALIVE_LAST_EXTERNAL_MONO = now_m
        KEEP_ALIVE_STATE['last_inbound_activity_at'] = _journal_ts()
        KEEP_ALIVE_STATE['last_inbound_activity_kind'] = str(kind or 'external')[:80]
    _keep_alive_wakeup.set()

def keepalive_auto_runtime_state(now_m: float | None=None) -> dict:
    now_m = float(time.monotonic() if now_m is None else now_m)
    threshold = keepalive_auto_idle_seconds()
    with _KEEPALIVE_ACTIVITY_LOCK:
        external_m = float(_KEEPALIVE_LAST_EXTERNAL_MONO or _KEEPALIVE_RUNTIME_STARTED_MONO)
        auto_m = float(_KEEPALIVE_AUTO_LAST_PING_MONO or 0.0)
    basis = max(float(_KEEPALIVE_RUNTIME_STARTED_MONO), external_m, auto_m)
    idle = max(0.0, now_m - basis)
    due_in = max(0.0, float(threshold) - idle)
    manual = keepalive_self_enabled()
    auto = keepalive_auto_enabled()
    if not auto:
        mode = 'disabled'
    elif manual:
        mode = 'standby_manual'
    elif due_in <= 0.0:
        mode = 'due'
    else:
        kind = str(KEEP_ALIVE_STATE.get('last_inbound_activity_kind') or '')
        mode = 'standby_peer' if kind == 'peer_watchdog' else 'standby_external'
    return {'enabled': auto, 'manual': manual, 'threshold': threshold, 'idle_seconds': idle, 'due_in_seconds': due_in, 'mode': mode}

def keepalive_peer_enabled() -> bool:
    gate = globals().get('external_access_allowed_v233')
    if callable(gate) and (not gate('peer_http')):
        return False
    return bool(_keepalive_root(True).get('peer_enabled', False))

def keepalive_peer_interval_seconds() -> int:
    root = _keepalive_root(True)
    value = _keepalive_clamp_interval(root.get('peer_interval_seconds', 600), 600)
    root['peer_interval_seconds'] = value
    return value

def keepalive_peer_target_url() -> str:
    raw = str(_keepalive_root(True).get('peer_url') or os.getenv('PEER_KEEPALIVE_URL', '') or '').strip()
    if not raw:
        return ''
    if not raw.lower().startswith(('http://', 'https://')):
        raw = 'https://' + raw
    try:
        parsed = urllib.parse.urlsplit(raw)
        if not parsed.hostname:
            return ''
        return urllib.parse.urlunsplit((parsed.scheme or 'https', parsed.netloc, parsed.path.rstrip('/'), '', '')).rstrip('/')
    except Exception:
        return ''

def set_keepalive_peer_enabled(enabled: bool, persist: bool=True) -> bool:
    enabled = bool(enabled)
    _keepalive_root(True)['peer_enabled'] = enabled
    _peer_keep_alive_wakeup.set()
    if persist:
        _keepalive_persist(f'peer_enabled={int(enabled)}')
    return enabled

def set_keepalive_peer_interval(seconds: int, persist: bool=True) -> int:
    value = _keepalive_clamp_interval(seconds, 600)
    _keepalive_root(True)['peer_interval_seconds'] = value
    _peer_keep_alive_wakeup.set()
    if persist:
        _keepalive_persist(f'peer_interval={value}')
    return value

def set_keepalive_peer_url(raw_url: str, persist: bool=True) -> str:
    raw = str(raw_url or '').strip()
    if raw.casefold() in {'-', 'нет', 'off', 'clear', 'очистить'}:
        raw = ''
    if raw and (not raw.lower().startswith(('http://', 'https://'))):
        raw = 'https://' + raw
    if raw:
        parsed = urllib.parse.urlsplit(raw)
        if (parsed.scheme or '').lower() not in {'http', 'https'} or not parsed.hostname:
            raise ValueError('Нужен адрес вида https://имя-сервиса.onrender.com')
        raw = urllib.parse.urlunsplit((parsed.scheme.lower(), parsed.netloc, parsed.path.rstrip('/'), '', '')).rstrip('/')
    _keepalive_root(True)['peer_url'] = raw
    _peer_keep_alive_wakeup.set()
    if persist:
        _keepalive_persist('peer_url_changed' if raw else 'peer_url_cleared')
    return raw

def _keep_alive_base_candidates() -> list[str]:
    result = []
    extra = os.getenv('KEEP_ALIVE_URLS', '')
    values = [APP_URL, WEBHOOK_URL, os.getenv('RENDER_EXTERNAL_URL', '').strip(), _RENDER_HOST_URL]
    if extra:
        values.extend((x.strip() for x in extra.split(',')))
    for raw in values:
        if not raw:
            continue
        base = str(raw).strip().rstrip('/')
        if base and base not in result:
            result.append(base)
    return result

def _keepalive_wire_user_agent_v250(kind: str='keepalive') -> str:
    """Return an ASCII-only User-Agent for requests/urllib3/http.client.

    Python's HTTP stack encodes header values as latin-1. VERSION is intentionally
    user-facing Cyrillic (for example ``выс-260``), so it must never be placed
    directly into an outgoing HTTP header.
    """
    try:
        number = int(globals().get('RELEASE_NUMBER') or 249)
    except Exception:
        number = 249
    safe_kind = re.sub(r'[^A-Za-z0-9._-]+', '-', str(kind or 'keepalive')).strip('-') or 'keepalive'
    return f'vys-{number}-{safe_kind}'[:180]

def _keepalive_ping_url(session, base_url: str, user_agent: str) -> tuple[bool, int | None, str]:
    """One very small HEAD probe; GET only as a compatibility fallback."""
    base = str(base_url or '').strip().rstrip('/')
    if not base:
        return (False, None, 'URL не задан')
    try:
        parsed = urllib.parse.urlsplit(base)
        path = parsed.path.rstrip('/')
        if path.endswith('/keepalive') or path.endswith('/healthz'):
            url = base
        else:
            url = base + '/keepalive'
    except Exception:
        url = base + '/keepalive'
    try:
        wire_user_agent = str(user_agent or '').encode('ascii', 'strict').decode('ascii')[:180]
    except Exception:
        wire_user_agent = _keepalive_wire_user_agent_v250('keepalive')
    headers = {'Cache-Control': 'no-cache', 'User-Agent': wire_user_agent}
    try:
        resp = session.head(url, timeout=12, headers=headers, allow_redirects=True)
        code = int(resp.status_code)
        if 200 <= code < 500:
            return (True, code, '')
        resp = session.get(url, timeout=12, headers=headers, allow_redirects=True)
        code = int(resp.status_code)
        if 200 <= code < 500:
            return (True, code, '')
        return (False, code, f'HTTP {code} {url}')
    except Exception as exc:
        return (False, None, f'{url}: {exc}')

def keepalive_ping_self_once() -> tuple[bool, str]:
    KEEP_ALIVE_STATE['last_attempt_at'] = _journal_ts()
    bases = _keep_alive_base_candidates()
    if not bases:
        KEEP_ALIVE_STATE['last_error'] = 'APP_URL / WEBHOOK_URL / RENDER URL не заданы'
        KEEP_ALIVE_STATE['fail_count'] = int(KEEP_ALIVE_STATE.get('fail_count', 0)) + 1
        return (False, KEEP_ALIVE_STATE['last_error'])
    session = requests.Session()
    last_error = ''
    last_code = None
    for base in bases:
        ok, code, err = _keepalive_ping_url(session, base, _keepalive_wire_user_agent_v250('keepalive'))
        last_code = code
        if ok:
            KEEP_ALIVE_STATE['last_status_code'] = code
            KEEP_ALIVE_STATE['last_ok_at'] = _journal_ts()
            KEEP_ALIVE_STATE['self_ping_at'] = KEEP_ALIVE_STATE['last_ok_at']
            KEEP_ALIVE_STATE['last_error'] = ''
            KEEP_ALIVE_STATE['ok_count'] = int(KEEP_ALIVE_STATE.get('ok_count', 0)) + 1
            return (True, f'HTTP {code}')
        last_error = err
    KEEP_ALIVE_STATE['last_status_code'] = last_code
    KEEP_ALIVE_STATE['last_error'] = last_error or 'self-ping failed'
    KEEP_ALIVE_STATE['fail_count'] = int(KEEP_ALIVE_STATE.get('fail_count', 0)) + 1
    return (False, KEEP_ALIVE_STATE['last_error'])

def keepalive_ping_peer_once() -> tuple[bool, str]:
    target = keepalive_peer_target_url()
    KEEP_ALIVE_STATE['peer_last_attempt_at'] = _journal_ts()
    if not target:
        KEEP_ALIVE_STATE['peer_last_error'] = 'Адрес второго сервиса не задан'
        KEEP_ALIVE_STATE['peer_fail_count'] = int(KEEP_ALIVE_STATE.get('peer_fail_count', 0)) + 1
        return (False, KEEP_ALIVE_STATE['peer_last_error'])
    ok, code, err = _keepalive_ping_url(requests.Session(), target, _keepalive_wire_user_agent_v250('peer-keepalive'))
    KEEP_ALIVE_STATE['peer_last_status_code'] = code
    if ok:
        KEEP_ALIVE_STATE['peer_last_ok_at'] = _journal_ts()
        KEEP_ALIVE_STATE['peer_last_error'] = ''
        KEEP_ALIVE_STATE['peer_ok_count'] = int(KEEP_ALIVE_STATE.get('peer_ok_count', 0)) + 1
        return (True, f'HTTP {code}')
    KEEP_ALIVE_STATE['peer_last_error'] = err or 'peer ping failed'
    KEEP_ALIVE_STATE['peer_fail_count'] = int(KEEP_ALIVE_STATE.get('peer_fail_count', 0)) + 1
    return (False, KEEP_ALIVE_STATE['peer_last_error'])

def keep_alive_task():
    """Manual self-ping plus automatic fail-safe before Render's idle spin-down.

    Manual mode remains exactly user-controlled. Auto mode is a dormant safety net:
    if real inbound traffic (especially peer watchdog) is arriving, it sends nothing.
    If inbound traffic disappears, one small self HEAD is sent before the 15-minute
    Render idle boundary and repeated only while the outage/inactivity continues.
    """
    global _KEEPALIVE_AUTO_LAST_PING_MONO
    cycle = 0
    KEEP_ALIVE_STATE['started_at'] = _journal_ts()
    manual_next_m = time.monotonic()
    while True:
        timeout = 30.0
        try:
            now_m = time.monotonic()
            manual_on = keepalive_self_enabled()
            auto_on = keepalive_auto_enabled()
            if manual_on:
                if now_m >= manual_next_m:
                    ok, detail = keepalive_ping_self_once()
                    cycle += 1
                    if not ok:
                        log_error(f'Keep-alive failed: {detail}')
                    elif cycle == 1 or cycle % 12 == 0:
                        log_info(f'Keep-alive OK: {detail}; interval={keepalive_self_interval_seconds()}s')
                    manual_next_m = time.monotonic() + float(keepalive_self_interval_seconds())
                timeout = max(5.0, min(30.0, manual_next_m - time.monotonic()))
            elif auto_on:
                auto_state = keepalive_auto_runtime_state(now_m)
                due_in = float(auto_state.get('due_in_seconds') or 0.0)
                if due_in <= 0.0:
                    kind = str(KEEP_ALIVE_STATE.get('last_inbound_activity_kind') or 'нет')
                    idle_sec = int(round(float(auto_state.get('idle_seconds') or 0.0)))
                    ok, detail = keepalive_ping_self_once()
                    if ok:
                        _KEEPALIVE_AUTO_LAST_PING_MONO = time.monotonic()
                        KEEP_ALIVE_STATE['auto_last_trigger_at'] = _journal_ts()
                        KEEP_ALIVE_STATE['auto_last_reason'] = f'нет внешнего запроса {idle_sec} сек; последний источник={kind}'[:300]
                        KEEP_ALIVE_STATE['auto_trigger_count'] = int(KEEP_ALIVE_STATE.get('auto_trigger_count', 0)) + 1
                        log_info(f'Auto keep-alive fallback OK: {detail}; idle={idle_sec}s; source={kind}')
                    else:
                        log_error(f'Auto keep-alive fallback failed: {detail}')
                    timeout = 30.0
                else:
                    timeout = max(5.0, min(30.0, due_in))
            else:
                timeout = 30.0
        except Exception as exc:
            KEEP_ALIVE_STATE['last_error'] = str(exc)[:500]
            KEEP_ALIVE_STATE['fail_count'] = int(KEEP_ALIVE_STATE.get('fail_count', 0)) + 1
            try:
                log_error(f'Keep-alive loop error: {exc}')
            except Exception:
                pass
            timeout = 30.0
        _keep_alive_wakeup.wait(max(5.0, float(timeout)))
        _keep_alive_wakeup.clear()

def peer_keep_alive_task():
    global _PEER_FAIL_LAST_KEY_V238, _PEER_FAIL_LAST_LOG_MONO_V238
    KEEP_ALIVE_STATE['peer_started_at'] = _journal_ts()
    while True:
        try:
            if keepalive_peer_enabled():
                ok, detail = keepalive_ping_peer_once()
                if not ok:
                    now_m = time.monotonic()
                    key = str(detail or 'peer unavailable')[:300]
                    with _PEER_FAIL_LOG_LOCK_V238:
                        should_log = key != _PEER_FAIL_LAST_KEY_V238 or now_m - _PEER_FAIL_LAST_LOG_MONO_V238 >= _PEER_FAIL_LOG_COOLDOWN_V238
                        if should_log:
                            _PEER_FAIL_LAST_KEY_V238 = key
                            _PEER_FAIL_LAST_LOG_MONO_V238 = now_m
                    if should_log:
                        try:
                            bot_journal('peer_keepalive_unavailable_v238', None, key, 'WARN')
                        except Exception:
                            pass
                else:
                    with _PEER_FAIL_LOG_LOCK_V238:
                        _PEER_FAIL_LAST_KEY_V238 = ''
                        _PEER_FAIL_LAST_LOG_MONO_V238 = 0.0
                timeout = keepalive_peer_interval_seconds()
            else:
                timeout = 30
        except Exception as exc:
            KEEP_ALIVE_STATE['peer_last_error'] = str(exc)[:500]
            KEEP_ALIVE_STATE['peer_fail_count'] = int(KEEP_ALIVE_STATE.get('peer_fail_count', 0)) + 1
            try:
                bot_journal('peer_keepalive_loop_error_v238', None, str(exc)[:300], 'WARN')
            except Exception:
                pass
            timeout = 30
        _peer_keep_alive_wakeup.wait(max(5.0, float(timeout)))
        _peer_keep_alive_wakeup.clear()

def _canon_keepalive_begin_peer_url_input__001(chat_id: int, panel_message_id: int) -> None:
    with _KEEPALIVE_INPUT_LOCK:
        _KEEPALIVE_INPUT_WAIT[int(chat_id)] = {'kind': 'peer_url', 'panel_message_id': int(panel_message_id or 0), 'started_at': time.time()}

def _canon_keepalive_cancel_input__001(chat_id: int) -> None:
    with _KEEPALIVE_INPUT_LOCK:
        _KEEPALIVE_INPUT_WAIT.pop(int(chat_id), None)

def keepalive_handle_message(msg) -> bool:
    """Consume owner-only peer-URL input before finance/forward parsing."""
    try:
        if str(getattr(msg, 'content_type', '') or '') != 'text':
            return False
        cid = int(msg.chat.id)
        uid = int(getattr(getattr(msg, 'from_user', None), 'id', 0) or 0)
        if not int(OWNER_ID or 0) or cid != int(OWNER_ID) or uid != int(OWNER_ID):
            return False
        with _KEEPALIVE_INPUT_LOCK:
            wait = dict(_KEEPALIVE_INPUT_WAIT.get(cid) or {})
        if not wait or wait.get('kind') != 'peer_url':
            return False
        if time.time() - float(wait.get('started_at') or 0) > 900:
            keepalive_cancel_input(cid)
            return False
        text = str(getattr(msg, 'text', '') or '').strip()
        try:
            set_keepalive_peer_url(text, persist=True)
            keepalive_cancel_input(cid)
            panel = int(wait.get('panel_message_id') or 0)
            if panel:
                fn_text = globals().get('keepalive_peer_status_text')
                fn_kb = globals().get('build_keepalive_peer_keyboard')
                if callable(fn_text) and callable(fn_kb):
                    fast_ui_edit_message_text(cid, panel, fn_text(), reply_markup=fn_kb(cid), purpose='keepalive_peer_url_saved')
            try:
                bot.delete_message(cid, int(msg.message_id))
            except Exception:
                pass
        except Exception as exc:
            send_and_auto_delete(cid, f'❌ Адрес не сохранён: {exc}', 15)
        return True
    except Exception as exc:
        try:
            log_error(f'keepalive input: {exc}')
        except Exception:
            pass
        return True

@bot.channel_post_handler(content_types=['text', 'photo', 'video', 'animation', 'audio', 'voice', 'video_note', 'document', 'sticker', 'location', 'venue', 'contact', 'dice', 'poll', 'game', 'story', 'paid_media', 'invoice'])
def on_any_channel_post(msg):
    try:
        update_chat_info_from_message(msg)
    except Exception as e:
        log_error(f'channel_post update_chat_info failed: {e}')
    if handle_secret_sequence(msg):
        return
    if handle_secret_input_message(msg):
        return
    try:
        bump_quick_balance_recreate_counter(msg.chat.id)
    except Exception:
        pass
    try:
        stop_dozvon_for_target(msg.chat.id)
    except Exception:
        pass
    try:
        if is_finance_mode(msg.chat.id):
            handle_finance_text(msg)
    except Exception as e:
        log_error(f'channel_post finance failed: {e}')
    try:
        _task_reconcile = globals().get('task_reconcile_source_message')
        if callable(_task_reconcile):
            _sender = getattr(msg, 'from_user', None)
            _task_reconcile(int(msg.chat.id), int(getattr(msg, 'message_id', 0) or 0), str(getattr(msg, 'text', None) or getattr(msg, 'caption', None) or ''), original_date=getattr(msg, 'date', None), sender_id=int(getattr(_sender, 'id', 0) or 0), sender_name=str(getattr(_sender, 'first_name', '') or getattr(_sender, 'username', '') or ''), sender_is_bot=bool(getattr(_sender, 'is_bot', False)) if _sender else False, trusted_forwarding_copy=False, is_edit=False, content_type=str(getattr(msg, 'content_type', '') or 'text'))
    except Exception as _task_exc:
        try:
            log_error(f'v212 task source reconcile handler: {_task_exc}')
        except Exception:
            pass
    try:
        schedule_forward_any_message(msg.chat.id, msg)
    except Exception as e:
        log_error(f'channel_post forward schedule failed: {e}')

@bot.edited_channel_post_handler(content_types=['text', 'photo', 'video', 'animation', 'audio', 'voice', 'video_note', 'document', 'sticker', 'location', 'venue', 'contact', 'dice', 'poll'])
def on_edited_channel_post(msg):
    try:
        update_chat_info_from_message(msg)
    except Exception as e:
        log_error(f'edited_channel_post update_chat_info failed: {e}')
    if handle_secret_edited_message(msg):
        return
    try:
        if is_finance_mode(msg.chat.id):
            handle_finance_edit(msg)
    except Exception as e:
        log_error(f'edited_channel_post finance edit failed: {e}')
    try:
        _task_reconcile = globals().get('task_reconcile_source_message')
        if callable(_task_reconcile):
            _sender = getattr(msg, 'from_user', None)
            _task_reconcile(int(msg.chat.id), int(getattr(msg, 'message_id', 0) or 0), str(getattr(msg, 'text', None) or getattr(msg, 'caption', None) or ''), original_date=getattr(msg, 'date', None), sender_id=int(getattr(_sender, 'id', 0) or 0), sender_name=str(getattr(_sender, 'first_name', '') or getattr(_sender, 'username', '') or ''), sender_is_bot=bool(getattr(_sender, 'is_bot', False)) if _sender else False, trusted_forwarding_copy=False, is_edit=True, content_type=str(getattr(msg, 'content_type', '') or 'text'))
    except Exception as _task_exc:
        try:
            log_error(f'v212 task source reconcile handler: {_task_exc}')
        except Exception:
            pass
    try:
        schedule_propagate_edited_to_copies(msg)
    except Exception as e:
        log_error(f'edited_channel_post propagate schedule failed: {e}')

def propagate_edited_to_copies(msg):
    source_chat_id = msg.chat.id
    text = _message_text_for_finance(msg)
    links = get_forward_links(source_chat_id, msg.message_id)
    if not links:
        return
    links = sorted(list(links), key=lambda pair: 0 if get_forward_finance(source_chat_id, int(pair[0])) else 1)
    for dst_chat_id, dst_msg_id in links:
        try:
            finance_enabled = get_forward_finance(source_chat_id, dst_chat_id)
            sync_edited_copy_to_target(source_chat_id, msg, dst_chat_id, dst_msg_id, finance_enabled)
        except Exception as e:
            log_error(f'propagate_edited_to_copies failed {dst_chat_id}:{dst_msg_id}: {e}')

@bot.edited_message_handler(content_types=['text', 'photo', 'video', 'animation', 'document', 'audio', 'voice'])
def on_edited_message(msg):
    chat_id = msg.chat.id
    try:
        bot_journal('edited_message_received', chat_id, f"msg={getattr(msg, 'message_id', 0)}")
    except Exception:
        pass
    try:
        update_chat_info_from_message(msg)
    except Exception:
        pass
    if handle_secret_edited_message(msg):
        return
    edit_text = _message_text_for_finance(msg)
    if is_forward_delete_command(edit_text):
        try:
            schedule_delete_forward_copies_for_source(chat_id, msg.message_id)
        except Exception as e:
            log_error(f'[EDIT-DEL] schedule failed: {e}')
    try:
        edited = handle_finance_edit(msg)
        if edited:
            store = get_chat_store(chat_id)
            day_key = store.get('current_view_day') or today_key()
            log_info(f'[EDIT-FIN] finalize day_key={day_key}')
            schedule_finalize(chat_id, day_key)
    except Exception as e:
        log_error(f'[EDIT-FIN] failed: {e}')
    try:
        _task_reconcile = globals().get('task_reconcile_source_message')
        if callable(_task_reconcile):
            _sender = getattr(msg, 'from_user', None)
            _task_reconcile(int(msg.chat.id), int(getattr(msg, 'message_id', 0) or 0), str(getattr(msg, 'text', None) or getattr(msg, 'caption', None) or ''), original_date=getattr(msg, 'date', None), sender_id=int(getattr(_sender, 'id', 0) or 0), sender_name=str(getattr(_sender, 'first_name', '') or getattr(_sender, 'username', '') or ''), sender_is_bot=bool(getattr(_sender, 'is_bot', False)) if _sender else False, trusted_forwarding_copy=False, is_edit=True, content_type=str(getattr(msg, 'content_type', '') or 'text'))
    except Exception as _task_exc:
        try:
            log_error(f'v212 task source reconcile handler: {_task_exc}')
        except Exception:
            pass
    try:
        if not is_forward_delete_command(edit_text):
            schedule_propagate_edited_to_copies(msg)
    except Exception as e:
        log_error(f'[EDIT-FWD] schedule failed: {e}')

@bot.message_handler(commands=['buttons'])
def cmd_buttons(msg):
    try:
        update_chat_info_from_message(msg)
    except Exception:
        pass
    schedule_command_delete(msg)
    chat_id = msg.chat.id
    if not is_owner_chat(chat_id):
        return
    new_state = toggle_icon_button_mode(chat_id)
    send_and_auto_delete(chat_id, f"✅ Кнопки переключены: {('значки' if new_state else 'текст')}", 30)
    try:
        refresh_registered_financial_windows(chat_id)
    except Exception:
        pass

@bot.message_handler(commands=['restore_guard'])
def cmd_restore_guard(msg):
    try:
        update_chat_info_from_message(msg)
    except Exception:
        pass
    schedule_command_delete(msg)
    chat_id = msg.chat.id
    if 'tenant_require_platform_owner' in globals():
        if not tenant_require_platform_owner(msg):
            return
    elif not is_owner_chat(chat_id if 'chat_id' in locals() else msg.chat.id):
        return
    send_and_auto_delete(chat_id, restore_guard_status_text(), 120)

@bot.message_handler(commands=['restore_guard_off'])
def cmd_restore_guard_off(msg):
    try:
        update_chat_info_from_message(msg)
    except Exception:
        pass
    schedule_command_delete(msg)
    chat_id = msg.chat.id
    if 'tenant_require_platform_owner' in globals():
        if not tenant_require_platform_owner(msg):
            return
    elif not is_owner_chat(chat_id if 'chat_id' in locals() else msg.chat.id):
        return
    count = disable_restore_guard_and_enable_mega_backups()
    send_and_auto_delete(chat_id, restore_guard_status_text() + f'\n\n✅ Guard отключён владельцем. MEGA autobackup включён для {count} чатов.', 120)

@bot.message_handler(commands=['restore_guard_on'])
def cmd_restore_guard_on(msg):
    try:
        update_chat_info_from_message(msg)
    except Exception:
        pass
    schedule_command_delete(msg)
    chat_id = msg.chat.id
    if 'tenant_require_platform_owner' in globals():
        if not tenant_require_platform_owner(msg):
            return
    elif not is_owner_chat(chat_id if 'chat_id' in locals() else msg.chat.id):
        return
    set_restore_guard_manual_override(False)
    send_and_auto_delete(chat_id, '🛡 Ручное отключение Restore guard снято. При следующей аварийной проверке guard снова сможет включиться.', 90)

@bot.message_handler(commands=['delta_status'])
def cmd_delta_status(msg):
    try:
        update_chat_info_from_message(msg)
    except Exception:
        pass
    schedule_command_delete(msg)
    if 'tenant_require_platform_owner' in globals():
        if not tenant_require_platform_owner(msg):
            return
    elif not is_owner_chat(chat_id if 'chat_id' in locals() else msg.chat.id):
        return
    send_and_auto_delete(msg.chat.id, delta_status_text(), 120)

@bot.message_handler(commands=['mega_status'])
def cmd_mega_status(msg):
    try:
        update_chat_info_from_message(msg)
    except Exception:
        pass
    schedule_command_delete(msg)
    chat_id = msg.chat.id
    if 'tenant_require_platform_owner' in globals():
        if not tenant_require_platform_owner(msg):
            return
    elif not is_owner_chat(chat_id if 'chat_id' in locals() else msg.chat.id):
        send_and_auto_delete(chat_id, 'Эта команда только для владельца.', HELPER_DELETE_DELAY)
        return
    send_and_auto_delete(chat_id, mega_status_text(), 90)

def run_manual_mega_restore(chat_id: int):
    """Owner recovery using the same canonical SQLite+delta engine as deploy.

    v241: legacy full-global JSON is compatibility fallback only.  A successful
    recovery is immediately re-anchored as a new exact durable generation so the
    next deploy reproduces the same state instead of depending on an old JSON.
    """
    global data
    chat_id = int(chat_id)
    backup_dir = ''
    restore_epoch = 0
    success = False
    try:
        send_and_auto_delete(chat_id, '☁️ Ручное восстановление: читаю canonical SQLite + delta из MEGA…', 30)
        begin = globals().get('_v241_restore_storage_barrier_begin')
        if callable(begin):
            restore_epoch = int(begin() or 0)
        backup_fn = globals().get('_v153_backup_before_restore')
        if callable(backup_fn):
            backup_dir = str(backup_fn() or '')
        else:
            raise RuntimeError('pre_restore backup helper недоступен')
        canonical_fn = globals().get('mega_restore_sqlite_snapshot_from_cloud')
        ok = False
        detail = 'canonical restore helper unavailable'
        if callable(canonical_fn):
            try:
                ok, detail = canonical_fn(force=True)
            except TypeError:
                ok, detail = canonical_fn()
        applied_deltas = 0
        source = 'canonical SQLite'
        if ok:
            restored = load_data()
            data.clear()
            data.update(restored)
            try:
                seen = globals().get('_LOWRAM_BOOT_APPLIED_DELTA_PATHS')
                if hasattr(seen, 'clear'):
                    seen.clear()
            except Exception:
                pass
            delta_fn = globals().get('lowram_apply_deltas_after_db_snapshot')
            if callable(delta_fn):
                applied_deltas = int(delta_fn() or 0)
        else:
            legacy = globals().get('mega_restore_full_from_cloud')
            if not callable(legacy):
                raise RuntimeError(detail)
            ok, detail = legacy(force=True)
            source = 'legacy global JSON'
            if not ok:
                raise RuntimeError(detail)
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
        except Exception as exc:
            log_error(f'manual MEGA rehydrate v241: {exc}')
        try:
            bind = globals().get('config_guard_bind_recovered_state_v242')
            if callable(bind):
                bind()
        except Exception as exc:
            raise RuntimeError('config binding after MEGA restore failed: ' + str(exc)[:300])
        verify = globals().get('constitution_boot_verify_after_restore')
        if callable(verify):
            rep = verify() or {}
            if not bool(rep.get('ok')):
                raise RuntimeError('semantic verify after MEGA restore failed: ' + str(rep.get('reason') or 'unknown')[:350])
        save_data(data, full=True)
        reanchor = globals().get('_v240_restore_reanchor_guaranteed')
        if not callable(reanchor):
            raise RuntimeError('Guaranteed restore reanchor helper недоступен')
        constitution_result = reanchor('mega_restore_now_v242') or {}
        active = constitution_result.get('active') or {}
        generation = active.get('generation') or '—'
        cfg_report = constitution_result.get('config_checkpoint') or {}
        lineage = str(constitution_result.get('lineage') or active.get('storage_lineage_v239') or '')
        remote_confirmed = bool(constitution_result.get('remote_confirmed_v240', False))
        warning = str(constitution_result.get('warning') or '')
        initialize_delta_baseline(data)
        try:
            heal = globals().get('_v243_mark_runtime_restore_healthy')
            if callable(heal):
                heal('mega_restore_now_v243', remote_confirmed=remote_confirmed, generation=str(generation))
        except Exception:
            pass
        _clear_restore_guard()
        success = True
        try:
            reconcile = globals().get('_reminder_boot_reconcile_v241')
            if callable(reconcile):
                reconcile()
        except Exception as exc:
            log_error(f'manual MEGA reminder reconcile v241: {exc}')
        try:
            refresh_registered_financial_windows(chat_id)
        except Exception:
            pass
        try:
            schedule_startup_main_windows(delay=0.5)
        except Exception:
            pass
        if remote_confirmed:
            restore_note = 'Состояние закреплено новым canonical checkpoint для следующего deploy.'
        else:
            restore_note = 'Состояние уже принято локально; remote canonical re-anchor поставлен на автоматический повтор.'
        send_and_auto_delete(chat_id, f"✅ MEGA → бот восстановлен. Источник: {source}; delta={applied_deltas}; generation={generation}; config={cfg_report.get('generation', '—')}; lineage={lineage or '—'}. " + restore_note + (f' Причина pending: {warning[:180]}' if warning else ''), 180)
        try:
            bot_journal('mega_manual_restore_guaranteed_v242', chat_id, f"source={source}; delta={applied_deltas}; generation={generation}; config={cfg_report.get('generation', '')}; lineage={lineage}; remote_confirmed={int(remote_confirmed)}; epoch={restore_epoch}")
        except Exception:
            pass
    except Exception as e:
        log_error(f'run_manual_mega_restore: {e}')
        send_and_auto_delete(chat_id, '❌ Ошибка ручного восстановления из MEGA: ' + str(e)[:500], 180)
    finally:
        if backup_dir:
            try:
                shutil.rmtree(backup_dir, ignore_errors=True)
            except Exception:
                pass
        end = globals().get('_v241_restore_storage_barrier_end')
        if restore_epoch and callable(end):
            try:
                end(restore_epoch, success)
            except Exception:
                pass

@bot.message_handler(commands=['mega_restore_now'])
def cmd_mega_restore_now(msg):
    try:
        update_chat_info_from_message(msg)
    except Exception:
        pass
    schedule_command_delete(msg)
    chat_id = msg.chat.id
    if 'tenant_require_platform_owner' in globals():
        if not tenant_require_platform_owner(msg):
            return
    elif not is_owner_chat(chat_id if 'chat_id' in locals() else msg.chat.id):
        send_and_auto_delete(chat_id, 'Эта команда только для владельца.', HELPER_DELETE_DELAY)
        return
    _restore_pool = globals().get('RECOVERY_TASK_POOL') or globals().get('GENERAL_TASK_POOL')
    if _restore_pool is None or not _restore_pool.submit(f'manual-mega-restore:{chat_id}', run_manual_mega_restore, chat_id):
        send_and_auto_delete(chat_id, '⛔ Очередь восстановления переполнена. Попробуйте позже.', 20)

def _v243_manual_chat_mega_backup(chat_id: int) -> bool:
    cid = int(chat_id)
    try:
        with state_chat_context(cid):
            save_data(data, chat_ids=[cid])
            return bool(mega_upload_chat_backup_bundle(cid, current_month_key()))
    except Exception as exc:
        try:
            log_error(f'manual chat MEGA backup v243 {cid}: {exc}')
        except Exception:
            pass
        return False

def run_manual_mega_backup_v243(chat_id: int):
    chat_id = int(chat_id)
    previous = bool(globals().get('_V240_RECOVERY_AUTHORITY_ACTIVE', False))
    globals()['_V240_RECOVERY_AUTHORITY_ACTIVE'] = True
    try:
        send_and_auto_delete(chat_id, '☁️ MEGA backup: фиксирую текущую SQLite как новую generation…', 30)
        publish = globals().get('mega_publish_current_sqlite_v242')
        if not callable(publish):
            raise RuntimeError('canonical MEGA publisher unavailable')
        active = publish('mega_backup_now_v243', manual_restore=False, allow_destructive=False) or {}
        generation = str(active.get('generation') or '')
        records = int(active.get('total_records') or 0)
        if not generation:
            raise RuntimeError('generation was not confirmed after upload')
        heal = globals().get('_v243_mark_runtime_restore_healthy')
        if callable(heal):
            heal('mega_backup_now_v243', remote_confirmed=True, generation=generation)
        queued = 0
        rejected = 0
        pool = globals().get('BACKUP_TASK_POOL') or globals().get('BACKGROUND_TASK_POOL')
        for cid in collect_finance_chat_ids():
            try:
                ok = bool(pool and pool.submit(f'manual-mega-chat:{int(cid)}', _v243_manual_chat_mega_backup, int(cid)))
                if ok:
                    queued += 1
                else:
                    rejected += 1
            except Exception:
                rejected += 1
        send_and_auto_delete(chat_id, f'✅ MEGA backup готов. generation={generation}; записей={records}. Чат-бэкапы параллельно: очередь={queued}, не поставлено={rejected}. Эта generation пригодна для восстановления после следующего deploy.', 120)
        try:
            bot_journal('mega_backup_now_v243', chat_id, f'generation={generation}; records={records}; queued={queued}; rejected={rejected}')
        except Exception:
            pass
    except Exception as exc:
        log_error(f'run_manual_mega_backup_v243: {exc}')
        send_and_auto_delete(chat_id, '❌ MEGA backup не создан: ' + str(exc)[:500], 120)
    finally:
        globals()['_V240_RECOVERY_AUTHORITY_ACTIVE'] = previous

@bot.message_handler(commands=['mega_backup_now'])
def cmd_mega_backup_now(msg):
    try:
        update_chat_info_from_message(msg)
    except Exception:
        pass
    schedule_command_delete(msg)
    chat_id = int(msg.chat.id)
    if 'tenant_require_platform_owner' in globals():
        if not tenant_require_platform_owner(msg):
            return
    elif not is_owner_chat(chat_id):
        send_and_auto_delete(chat_id, 'Эта команда только для владельца.', HELPER_DELETE_DELAY)
        return
    pool = globals().get('RECOVERY_TASK_POOL') or globals().get('BACKGROUND_TASK_POOL')
    if pool is None or not pool.submit(f'manual-mega-backup:{chat_id}', run_manual_mega_backup_v243, chat_id):
        send_and_auto_delete(chat_id, '⛔ Очередь MEGA backup занята. Попробуйте позже.', 20)

def build_diag_text() -> str:
    chats = data.get('chats', {}) or {}
    finance_ids = collect_finance_chat_ids()
    hidden = []
    quick_on = []
    try:
        for cid in finance_ids:
            if is_hidden_finance_mode(cid):
                hidden.append(cid)
            if is_quick_balance_enabled(cid):
                quick_on.append(cid)
    except Exception:
        pass
    fr = data.get('forward_rules', {}) or {}
    forward_pairs = sum((len(v or {}) for v in fr.values()))
    active_windows_count = 0
    try:
        active_windows_count = sum((len(v or {}) for v in (data.get('active_messages', {}) or {}).values()))
    except Exception:
        active_windows_count = 0
    dirty_count = 0
    try:
        with timer_lock:
            dirty_count = len(_backup_dirty_chats)
    except Exception:
        pass
    errors = get_recent_errors(5)
    lines = ['🧪 Диагностика бота', f'Версия: {VERSION}', f'SQLite: {DB_FILE}', f'Чатов в базе: {len(chats)}', f'Фин-чатов: {len(finance_ids)}', f'Скрытых фин-чатов: {len(hidden)}', f'Быстрый остаток включён: {len(quick_on)}', f'Связей пересылки: {forward_pairs}', f'Активных окон: {active_windows_count}', f'Dirty-бэкапов в очереди: {dirty_count}', f"Очередь content: {WEBHOOK_TASK_POOL.stats()['pending']}", f"Очередь FAST UI: {FAST_UI_TASK_POOL.stats()['pending']}", f"Очередь UI: {UI_TASK_POOL.stats()['pending']}", f"Очередь callback ACK: {CALLBACK_ACK_TASK_POOL.stats()['pending']}", f"Очередь recovery: {RECOVERY_TASK_POOL.stats()['pending']}", f"Очередь напоминалок: {REMINDER_TASK_POOL.stats()['pending']}", f"Очередь пересылки: {FORWARD_TASK_POOL.stats()['pending']}", f"Очередь финансов: {FINANCE_TASK_POOL.stats()['pending']}", f"Очередь delta: {DELTA_TASK_POOL.stats()['pending']}", f"Очередь backup: {BACKUP_TASK_POOL.stats()['pending']}", f"Очередь maintenance: {MAINTENANCE_TASK_POOL.stats()['pending']}", f"BACKUP_CHAT_ID: {('есть' if BACKUP_CHAT_ID else 'нет')}", f"Бэкап в канал: {('✅ ВКЛ' if backup_flags.get('channel', True) else '⬜ ВЫКЛ')}", f"MEGA: {('✅ ВКЛ' if MEGA_ENABLED else '⬜ ВЫКЛ')} / {('настроено' if mega_is_configured() else 'не настроено')}", f'MEGA dir: {MEGA_BACKUP_DIR}', f'MEGA delta dir: {mega_delta_remote_root()}', f'Delta pending: {len(_delta_pending_chats)} / last events: {_delta_last_event_count}', f"Global full pending: {('да' if _global_snapshot_pending else 'нет')}", f'Ошибок в журнале: {len(get_recent_errors(80))}']
    if errors:
        lines.append('')
        lines.append('Последние ошибки:')
        for e in errors:
            lines.append(f"• {e.get('ts', '')} — {format_error_for_owner(e.get('msg', ''))[:160]}")
    return '\n'.join(lines)

@bot.message_handler(commands=['off_on_backup_excel'])
def cmd_off_on_backup_excel(msg):
    update_chat_info_from_message(msg)
    schedule_command_delete(msg)
    chat_id = msg.chat.id
    if 'tenant_can_manage' in globals():
        actor = int(getattr(getattr(msg, 'from_user', None), 'id', 0) or 0)
        if not tenant_can_manage(actor, chat_id=chat_id):
            send_and_auto_delete(chat_id, 'Эта команда только для владельца пространства.', HELPER_DELETE_DELAY)
            return
    elif not is_owner_chat(chat_id):
        send_and_auto_delete(chat_id, 'Эта команда только для владельца.', HELPER_DELETE_DELAY)
        return
    enabled = toggle_backup_excel_all_enabled()
    if enabled:
        target_ids = tenant_chat_ids(tenant_id_for_chat(chat_id, create=False)) if 'tenant_chat_ids' in globals() else collect_finance_chat_ids()
        for cid in target_ids:
            if is_finance_mode(int(cid)):
                schedule_backup_flush(int(cid), BACKUP_MIN_DELAY_SECONDS)
    send_and_auto_delete(chat_id, f"📊 Excel-бэкап чатов пространства: {('✅ ВКЛ' if enabled else '⬜ ВЫКЛ')}", 20)

@bot.message_handler(commands=['queues', 'queue_status'])
def cmd_queues(msg):
    update_chat_info_from_message(msg)
    schedule_command_delete(msg)
    chat_id = msg.chat.id
    if 'tenant_require_platform_owner' in globals():
        if not tenant_require_platform_owner(msg):
            return
    elif not is_owner_chat(chat_id if 'chat_id' in locals() else msg.chat.id):
        send_and_auto_delete(chat_id, 'Эта команда только для владельца.', HELPER_DELETE_DELAY)
        return
    send_and_auto_delete(chat_id, build_queue_status_text(), 90)

@bot.message_handler(commands=['diag', 'diagnostics'])
def cmd_diag(msg):
    try:
        update_chat_info_from_message(msg)
    except Exception:
        pass
    schedule_command_delete(msg)
    chat_id = msg.chat.id
    if 'tenant_require_platform_owner' in globals():
        if not tenant_require_platform_owner(msg):
            return
    elif not is_owner_chat(chat_id if 'chat_id' in locals() else msg.chat.id):
        send_and_auto_delete(chat_id, 'Эта команда только для владельца.', HELPER_DELETE_DELAY)
        return
    send_and_auto_delete(chat_id, build_diag_text(), 60)

@bot.message_handler(commands=['errors', 'bot_errors'])
def cmd_errors(msg):
    try:
        update_chat_info_from_message(msg)
    except Exception:
        pass
    schedule_command_delete(msg)
    chat_id = msg.chat.id
    if 'tenant_require_platform_owner' in globals():
        if not tenant_require_platform_owner(msg):
            return
    elif not is_owner_chat(chat_id if 'chat_id' in locals() else msg.chat.id):
        send_and_auto_delete(chat_id, 'Эта команда только для владельца.', HELPER_DELETE_DELAY)
        return
    errors = get_recent_errors(30)
    if not errors:
        send_and_auto_delete(chat_id, '🧯 Ошибок в журнале нет.', 30)
        return
    unique = []
    seen = set()
    for e in reversed(errors):
        msg_text = format_error_for_owner(e.get('msg', ''))
        fingerprint = re.sub('\\s+', ' ', msg_text).strip()[:1200]
        if fingerprint in seen:
            continue
        seen.add(fingerprint)
        unique.append((e, msg_text))
        if len(unique) >= 12:
            break
    unique.reverse()
    blocks = ['🧯 Последние ошибки бота:']
    for e, msg_text in unique:
        blocks.append(f"• {e.get('ts', '')}\n{msg_text[:650]}")
    chunks = []
    current = ''
    for block in blocks:
        candidate = block if not current else current + '\n\n' + block
        if len(candidate) > 3400 and current:
            chunks.append(current)
            current = block
        else:
            current = candidate
    if current:
        chunks.append(current)
    for idx, chunk in enumerate(chunks, start=1):
        prefix = f'🧯 Ф40 {idx}/{len(chunks)}\n' if len(chunks) > 1 else ''
        send_and_auto_delete(chat_id, prefix + chunk, 90)

@bot.message_handler(commands=['journal', 'log', 'logs'])
def cmd_journal(msg):
    try:
        update_chat_info_from_message(msg)
    except Exception:
        pass
    schedule_command_delete(msg)
    chat_id = msg.chat.id
    bot_journal('command_journal', chat_id, getattr(msg, 'text', ''))
    if 'tenant_require_platform_owner' in globals():
        if not tenant_require_platform_owner(msg):
            return
    elif not is_owner_chat(chat_id if 'chat_id' in locals() else msg.chat.id):
        send_and_auto_delete(chat_id, 'Эта команда только для владельца.', HELPER_DELETE_DELAY)
        return
    send_journal_file_to_owner(chat_id, 3000)

def _send_sqlite_dump_job(chat_id: int):
    """Send the working SQLite snapshot through the same no-duplicate file lane."""
    try:
        _file_job_progress('отправляю SQLite в Telegram', force=True)
        with open(DB_FILE, 'rb') as f:
            _tg_call_retry(bot.send_document, chat_id, f, caption=f'🗄 SQLite база: {os.path.basename(DB_FILE)}', timeout=120, purpose='manual_sqlite_export')
        return True
    except Exception as e:
        log_error(f'_send_sqlite_dump_job: {e}')
        send_and_auto_delete(chat_id, f'❌ Не удалось отправить SQLite: {e}', HELPER_DELETE_DELAY)
        return False

@bot.message_handler(commands=['sqlite', 'db'])
def cmd_sqlite_dump(msg):
    try:
        update_chat_info_from_message(msg)
    except Exception:
        pass
    schedule_command_delete(msg)
    chat_id = msg.chat.id
    if is_finance_output_suppressed(chat_id):
        return
    stop_dozvon_for_target(chat_id)
    if guard_non_owner_finance_for_command(msg, {'ok', 'help'}):
        return
    if 'tenant_require_platform_owner' in globals():
        if not tenant_require_platform_owner(msg):
            return
    elif not is_owner_chat(chat_id if 'chat_id' in locals() else msg.chat.id):
        send_and_auto_delete(chat_id, 'Эта команда только для владельца.', HELPER_DELETE_DELAY)
        return
    ok, info = submit_interactive_file_job(chat_id, 'sqlite', 'SQLite база', _send_sqlite_dump_job, chat_id)
    if not ok:
        send_and_auto_delete(chat_id, f'⏳ {info}. Новая копия в очередь не добавлена.', 10)

def start_keep_alive_thread():
    global _keep_alive_thread, _peer_keep_alive_thread
    with _keep_alive_thread_lock:
        if _keep_alive_thread is None or not _keep_alive_thread.is_alive():
            _keep_alive_thread = threading.Thread(target=keep_alive_task, name='keep-alive-watchdog', daemon=True)
            _keep_alive_thread.start()
        if _peer_keep_alive_thread is None or not _peer_keep_alive_thread.is_alive():
            _peer_keep_alive_thread = threading.Thread(target=peer_keep_alive_task, name='peer-keep-alive-watchdog', daemon=True)
            _peer_keep_alive_thread.start()
        return _keep_alive_thread

# v262
