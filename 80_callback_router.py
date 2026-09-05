# v262
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
# v262
