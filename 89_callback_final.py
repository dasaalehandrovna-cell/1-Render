# v262
"""v179 single callback middleware for owner, circle 1, circle 2 and all users with feature access."""

def _v179_resolve_callback(call):
    raw = str(getattr(call, 'data', '') or '')
    try:
        fn = globals().get('resolve_short_callback')
        resolved = str(fn(raw) or raw) if callable(fn) else raw
    except Exception:
        resolved = raw
    return (raw, resolved)

def _v179_set_source_context(call, resolved):
    try:
        ctx = globals().get('_V161_SOURCE_CONTEXT')
        if ctx is None:
            return
        msg_text = str(getattr(call.message, 'text', None) or getattr(call.message, 'caption', None) or '')
        token_fn = globals().get('_v161_extract_token')
        ctx.token = token_fn(msg_text) if callable(token_fn) else ''
        ctx.callback = resolved
        ctx.chat_id = int(call.message.chat.id)
        ctx.message_id = int(call.message.message_id)
    except Exception:
        pass

def _v189_is_finance_window_callback(resolved: str) -> bool:
    """Callbacks that can originate from an old MAIN window. Auxiliary windows keep their own controls."""
    value = str(resolved or '')
    return value.startswith(('d:', 'c:', 'main_close:', 'remaining_open:'))

def _v189_redirect_stale_finance_window(call, resolved: str) -> bool:
    """Close any old finance window and recreate the ONE latest main window at chat bottom."""
    if not _v189_is_finance_window_callback(resolved):
        return False
    try:
        chat_id = int(call.message.chat.id)
        message_id = int(call.message.message_id)
        fn = globals().get('get_primary_main_window')
        if not callable(fn):
            return False
        primary_mid, primary_day = fn(chat_id)
        if not primary_mid or int(primary_mid) == message_id:
            return False
        day_key = str(primary_day or globals().get('today_key', lambda: '')())[:10]
    except Exception:
        return False
    try:
        bot.answer_callback_query(call.id, 'Старое окно закрыто → открываю последнее', show_alert=False)
    except Exception:
        pass

    def _redirect():
        try:
            deleter = globals().get('_v189_delete_stale_main_message')
            if callable(deleter):
                deleter(chat_id, message_id)
            else:
                try:
                    bot.delete_message(chat_id, message_id)
                except Exception:
                    pass
            force_new = globals().get('force_new_day_window')
            if callable(force_new):
                force_new(chat_id, day_key)
            else:
                recreate = globals().get('recreate_main_window_now')
                if callable(recreate):
                    recreate(chat_id, day_key)
            try:
                bot_journal('stale_main_redirect_v189', chat_id, f'old={message_id}; primary={primary_mid}; day={day_key}; action={resolved}', 'INFO')
            except Exception:
                pass
        except Exception as exc:
            try:
                log_error(f'v189 stale main redirect {chat_id}/{message_id}: {exc}')
            except Exception:
                pass
    try:
        pool = globals().get('UI_TASK_POOL') or globals().get('GENERAL_TASK_POOL')
        if pool is not None:
            submit_unique = getattr(pool, 'submit_unique', None)
            if callable(submit_unique):
                submit_unique(f'v189-stale-redirect:{chat_id}', _redirect)
            else:
                pool.submit(f'v189-stale-redirect:{chat_id}', _redirect)
        else:
            _redirect()
    except Exception:
        _redirect()
    return True

def _v179_dispatch_callback(call, raw: str, resolved: str):
    if str(resolved or '') in {'v160:tz_capture', 'v160:marker_capture'}:
        try:
            cid = int(call.message.chat.id)
            kind = 'tz' if str(resolved) == 'v160:tz_capture' else 'iz_mr'
            state_fn = globals().get('annotation_visibility_state_v226')
            state = state_fn(kind, cid) if callable(state_fn) else {'circle': False, 'effective': True}
            if bool(state.get('circle')) and (not bool(state.get('effective', True))):
                try:
                    bot.answer_callback_query(call.id, 'ТЗ окон выключено владельцем.' if kind == 'tz' else 'Маркеры выключены владельцем.', show_alert=False)
                except Exception:
                    pass
                try:
                    current_markup = getattr(call.message, 'reply_markup', None)
                    if current_markup is not None:
                        cleaned = _v221_final_filter_markup(cid, current_markup)
                        fp = globals().get('_v221_markup_fingerprint')
                        if not callable(fp) or fp(current_markup) != fp(cleaned):
                            bot.edit_message_reply_markup(chat_id=cid, message_id=int(call.message.message_id), reply_markup=cleaned)
                            try:
                                bot_journal('annotation_stale_button_pruned_v227', cid, f'kind={kind}; msg={int(call.message.message_id)}')
                            except Exception:
                                pass
                except Exception:
                    pass
                try:
                    bot_journal('annotation_gate_block_v226', cid, f"kind={kind}; global={int(bool(state.get('global')))}; directive={int(bool(state.get('directive')))}; local={int(bool(state.get('local')))}; action={resolved}")
                except Exception:
                    pass
                return True
        except Exception:
            pass
    guard = globals().get('contour_callback_guard')
    if callable(guard) and guard(call, resolved):
        return True
    if _v189_redirect_stale_finance_window(call, resolved):
        return True
    fn = globals().get('_v160_exact_callback_duplicate')
    if callable(fn) and fn(call):
        try:
            bot.answer_callback_query(call.id, 'Уже принято')
        except Exception:
            pass
        return True
    _v179_set_source_context(call, resolved)
    if resolved.startswith(('v196:c1:', 'v196:c2:')):
        ext = globals().get('v149_extension_callback')
        if callable(ext):
            try:
                bot_journal('constructor_direct_route_v209', int(call.message.chat.id), f'action={resolved}')
            except Exception:
                pass
            if ext(call, resolved):
                return True
    if resolved in {'journal_open', 'journal_back', 'journal_chats_back'}:
        try:
            chat_id = int(call.message.chat.id)
            if not is_owner_chat(chat_id):
                return True
            try:
                bot.answer_callback_query(call.id)
            except Exception:
                pass
            if resolved == 'journal_open':
                safe_edit(bot, call, build_journal_v208_menu_text(), reply_markup=build_journal_v208_menu_keyboard(chat_id))
            else:
                safe_edit(bot, call, build_info_text(chat_id), reply_markup=build_info_keyboard(chat_id))
            try:
                bot_journal('journal_direct_route_v209', chat_id, f'action={resolved}')
            except Exception:
                pass
            return True
        except Exception as exc:
            try:
                log_error(f'journal direct route v209: {exc}')
            except Exception:
                pass
    if resolved.startswith('v221:owner_msg:'):
        fn = globals().get('v221_owner_message_callback_final')
        if callable(fn) and fn(call, resolved):
            return True
    if resolved.startswith('v221:req:'):
        fn = globals().get('v221_owner_requests_callback_final')
        if callable(fn) and fn(call, resolved):
            return True
    if resolved.startswith('v234:config:'):
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
        if resolved == 'v234:config:open':
            try:
                bot.answer_callback_query(call.id)
            except Exception:
                pass
            safe_edit(bot, call, window_mark(config_guard_status_text_v234(), 'Ф233'), reply_markup=config_guard_keyboard_v234())
            return True
        if resolved == 'v234:config:accept':
            cp = config_guard_accept_current_v234('owner_accept_current_v234')
            try:
                bot.answer_callback_query(call.id, f"Текущее состояние принято · gen {int(cp.get('generation') or 0)}")
            except Exception:
                pass
            safe_edit(bot, call, window_mark(config_guard_status_text_v234(), 'Ф233'), reply_markup=config_guard_keyboard_v234())
            return True
        if resolved == 'v234:config:verify':
            try:
                bot.answer_callback_query(call.id, 'Проверяю настройки…')
            except Exception:
                pass
            try:
                rep = config_guard_boot_verify_v234()
                msg = 'Настройки проверены' + (' и восстановлены.' if rep.get('repaired') else '. Расхождений не найдено.')
            except Exception as exc:
                msg = 'Ошибка проверки: ' + str(exc)[:180]
            try:
                send_and_auto_delete(cid, msg, 15)
            except Exception:
                pass
            safe_edit(bot, call, window_mark(config_guard_status_text_v234(), 'Ф233'), reply_markup=config_guard_keyboard_v234())
            return True
    if resolved.startswith('v242:mdb:'):
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
        action = resolved.split(':', 2)[2]
        if action == 'list':
            try:
                bot.answer_callback_query(call.id, 'Читаю каталог MEGA…')
            except Exception:
                pass
            safe_edit(bot, call, window_mark(mega_database_browser_text_v242(), 'Ф233'), reply_markup=mega_database_browser_keyboard_v242())
            return True
        if action.startswith('pick:'):
            token = action.split(':', 1)[1]
            try:
                bot.answer_callback_query(call.id)
            except Exception:
                pass
            safe_edit(bot, call, window_mark(mega_database_confirm_text_v242(token), 'Ф233'), reply_markup=mega_database_confirm_keyboard_v242(token))
            return True
        if action.startswith('confirm:'):
            token = action.split(':', 1)[1]
            try:
                bot.answer_callback_query(call.id, 'Восстановление поставлено в очередь…')
            except Exception:
                pass
            pool = globals().get('RECOVERY_TASK_POOL') or globals().get('GENERAL_TASK_POOL')

            def _job():
                try:
                    rep = _v242_restore_selected_mega_database(token, cid)
                    send_and_auto_delete(cid, f"✅ База MEGA восстановлена. records={rep.get('source_records')} · новая generation={rep.get('generation') or 'LOCAL-PENDING'}", 180)
                    try:
                        schedule_startup_main_windows(delay=0.5)
                    except Exception:
                        pass
                except Exception as exc:
                    send_and_auto_delete(cid, '❌ Восстановление выбранной базы MEGA: ' + str(exc)[:500], 180)
            if pool is None or not pool.submit(f'v242-mega-db-restore:{cid}', _job):
                try:
                    send_and_auto_delete(cid, '⛔ Очередь восстановления переполнена.', 30)
                except Exception:
                    pass
            return True
    if resolved.startswith('v240:modes:'):
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
        action = resolved.split(':', 2)[2]
        if action == 'open':
            try:
                bot.answer_callback_query(call.id)
            except Exception:
                pass
            safe_edit(bot, call, window_mark(storage_modes_text_v240(), 'Ф237.1'), reply_markup=storage_modes_keyboard_v240())
            return True
        if action in {'render', 'telegram', 'mega'}:
            mode = {'render': 'render', 'telegram': 'telegram_durable', 'mega': 'mega'}[action]
            try:
                bot.answer_callback_query(call.id)
            except Exception:
                pass
            safe_edit(bot, call, window_mark(storage_mode_detail_text_v240(mode), 'Ф237.1'), reply_markup=storage_mode_detail_keyboard_v240(mode))
            return True
        if action.startswith('activate:'):
            mode = _storage_profile_normalize_v237_1(action.split(':', 1)[1])
            before = storage_profile_v237_1()
            env_forced = str(os.getenv('RENDER_TELEGRAM_ONLY', '') or '').strip().casefold() in {'1', 'true', 'yes', 'on', 'вкл'}
            blocked_msg = ''
            if before == mode:
                blocked_msg = 'Этот режим уже единственный активный. Чтобы выключить его, включите другой режим.'
            elif env_forced and mode != STORAGE_PROFILE_LOCAL_V237_1:
                blocked_msg = 'Переключение заблокировано Render Environment (RENDER_TELEGRAM_ONLY=1).'
            elif mode == STORAGE_PROFILE_MEGA_V237_1 and (not bool(MEGA_ENABLED and MEGA_EMAIL and MEGA_PASSWORD)):
                blocked_msg = 'MEGA не включена или нет credentials в Render.'
            elif mode == STORAGE_PROFILE_TELEGRAM_V237_1 and (not telegram_durable_available_v237_1()):
                blocked_msg = 'BACKUP_CHAT_ID / Telegram durable не настроены.'
            if blocked_msg:
                try:
                    bot.answer_callback_query(call.id, blocked_msg, show_alert=True)
                except Exception:
                    pass
            else:
                try:
                    bot.answer_callback_query(call.id, f'Переключаю: {_v240_mode_name(mode)}')
                except Exception:
                    pass
                set_storage_profile_v237_1(mode)
            safe_edit(bot, call, window_mark(storage_mode_detail_text_v240(mode), 'Ф237.1'), reply_markup=storage_mode_detail_keyboard_v240(mode))
            return True
        if action.startswith('feature:'):
            parts = action.split(':', 2)
            if len(parts) == 3:
                mode = _storage_profile_normalize_v237_1(parts[1])
                feature = parts[2]
                cur = bool(storage_mode_features_v240(mode).get(feature, False))
                requested = not cur
                try:
                    bot.answer_callback_query(call.id, f"{feature}: {('ВКЛ' if requested else 'ВЫКЛ')}")
                except Exception:
                    pass
                new = set_storage_mode_feature_v240(mode, feature, requested)
                fmap = {'delta': ['delta_auto', 'delta_critical'], 'tasks': ['mega_recover'], 'system_generation': ['full_global'], 'cleanup': ['mega_maint']}
                if mode == STORAGE_PROFILE_MEGA_V237_1:
                    for code in fmap.get(feature, []):
                        try:
                            if storage_profile_v237_1() == mode:
                                v176_set_process(code, new, int(OWNER_ID or 0))
                            else:
                                _v176_root()[code] = bool(new)
                        except Exception:
                            pass
                safe_edit(bot, call, window_mark(storage_mode_detail_text_v240(mode), 'Ф237.1'), reply_markup=storage_mode_detail_keyboard_v240(mode))
                return True
        return True
    if resolved == 'v242:system_snapshot:toggle':
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
        try:
            hours = toggle_system_snapshot_hours_v242()
            bot.answer_callback_query(call.id, f'SYSTEM SQLite generation: каждые {hours} ч при изменениях')
        except Exception as exc:
            try:
                bot.answer_callback_query(call.id, f'Не удалось изменить интервал: {str(exc)[:120]}', show_alert=True)
            except Exception:
                pass
            return True
        try:
            safe_edit(bot, call, window_mark(storage_mode_detail_text_v240('mega'), 'Ф237.1'), reply_markup=storage_mode_detail_keyboard_v240('mega'))
        except Exception:
            pass
        return True
    if resolved.startswith('v237:storage:'):
        action = resolved.split(':', 2)[-1]
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
        if action == 'open':
            try:
                bot.answer_callback_query(call.id)
            except Exception:
                pass
            safe_edit(bot, call, window_mark(storage_profiles_status_text_v237_1(), 'Ф237.1'), reply_markup=storage_profiles_keyboard_v237_1())
            return True
        if action in {'profile_local', 'profile_tg', 'profile_mega'}:
            target = {'profile_local': 'render', 'profile_tg': 'telegram_durable', 'profile_mega': 'mega'}[action]
            before = storage_profile_v237_1()
            env_forced = str(os.getenv('RENDER_TELEGRAM_ONLY', '') or '').strip().casefold() in {'1', 'true', 'yes', 'on', 'вкл'}
            if before == target:
                msg, alert = 'Этот режим уже активен.', False
            elif env_forced and target != 'render':
                msg, alert = 'Переключение заблокировано Render Environment (RENDER_TELEGRAM_ONLY=1).', True
            elif target == 'mega' and (not bool(MEGA_ENABLED and MEGA_EMAIL and MEGA_PASSWORD)):
                msg, alert = 'MEGA не включена или нет credentials в Render.', True
            elif target == 'telegram_durable' and (not telegram_durable_available_v237_1()):
                msg, alert = 'BACKUP_CHAT_ID / Telegram durable не настроены.', True
            else:
                names = {'render': 'Только Render', 'telegram_durable': 'Telegram durable', 'mega': 'MEGA'}
                try:
                    bot.answer_callback_query(call.id, f'Переключаю: {names.get(target, target)}')
                except Exception:
                    pass
                set_storage_profile_v237_1(target)
                msg, alert = '', False
            if msg:
                try:
                    bot.answer_callback_query(call.id, msg, show_alert=alert)
                except Exception:
                    pass
            try:
                safe_edit(bot, call, build_info_text(cid), reply_markup=build_info_keyboard(cid))
            except Exception:
                pass
            return True
        if action == 'tg_refresh':
            if not telegram_durable_primary_v234():
                try:
                    bot.answer_callback_query(call.id, 'Сначала включите Telegram durable.', show_alert=True)
                except Exception:
                    pass
                return True
            try:
                telegram_durable_bootstrap_v234(True)
                mega_task_refresh_registry()
                bot.answer_callback_query(call.id, 'HEAD перечитан')
            except Exception as exc:
                try:
                    bot.answer_callback_query(call.id, f'Ошибка HEAD: {str(exc)[:120]}', show_alert=True)
                except Exception:
                    pass
            safe_edit(bot, call, window_mark(storage_profiles_status_text_v237_1(), 'Ф237.1'), reply_markup=storage_profiles_keyboard_v237_1())
            return True
        if action == 'tg_snapshot':
            if not telegram_durable_primary_v234():
                try:
                    bot.answer_callback_query(call.id, 'Telegram durable сейчас выключен.', show_alert=True)
                except Exception:
                    pass
                return True
            try:
                bot.answer_callback_query(call.id, 'SQLite snapshot поставлен в Telegram backup-очередь')
            except Exception:
                pass
            try:
                pool = globals().get('BACKUP_TASK_POOL') or globals().get('GENERAL_TASK_POOL')
                if pool is not None:
                    pool.submit_unique('manual-telegram-snapshot-v237-1', telegram_upload_sqlite_snapshot_v234, True)
            except Exception:
                pass
            return True
        if action == 'secret_open':
            try:
                bot.answer_callback_query(call.id)
            except Exception:
                pass
            safe_edit(bot, call, window_mark(secret_storage_status_text_v234(), 'Ф237.1'), reply_markup=secret_storage_keyboard_v234())
            return True
        if action in {'secret_tg', 'secret_mega'}:
            requested = 'mega' if action == 'secret_mega' else 'telegram'
            set_secret_storage_backend_v234(requested)
            effective = secret_storage_effective_backend_v234()
            try:
                bot.answer_callback_query(call.id, 'SECRET → MEGA' if effective == 'mega' else 'SECRET → Telegram', show_alert=bool(requested != effective))
            except Exception:
                pass
            safe_edit(bot, call, window_mark(secret_storage_status_text_v234(), 'Ф237.1'), reply_markup=secret_storage_keyboard_v234())
            return True
    if resolved.startswith(('v236:storage:', 'v234:storage:')):
        action = resolved.split(':', 2)[-1]
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
        if action == 'tg_open':
            try:
                bot.answer_callback_query(call.id)
            except Exception:
                pass
            safe_edit(bot, call, window_mark(telegram_durable_status_text_v236(), 'Ф236'), reply_markup=telegram_durable_keyboard_v234())
            return True
        if action == 'tg_refresh':
            try:
                telegram_durable_bootstrap_v234(True)
                mega_task_refresh_registry()
                bot.answer_callback_query(call.id, 'HEAD перечитан')
            except Exception as exc:
                try:
                    bot.answer_callback_query(call.id, f'Ошибка HEAD: {str(exc)[:120]}', show_alert=True)
                except Exception:
                    pass
            safe_edit(bot, call, window_mark(telegram_durable_status_text_v236(), 'Ф236'), reply_markup=telegram_durable_keyboard_v234())
            return True
        if action == 'tg_snapshot':
            try:
                bot.answer_callback_query(call.id, 'SQLite snapshot поставлен в backup-очередь')
            except Exception:
                pass

            def _v236_manual_snapshot_job():
                ok = False
                try:
                    ok = bool(telegram_upload_sqlite_snapshot_v234(True))
                except Exception as exc:
                    try:
                        log_error(f'manual Telegram snapshot v236: {exc}')
                    except Exception:
                        pass
                try:
                    if OWNER_ID:
                        bot.send_message(int(OWNER_ID), '✅ Telegram SQLite snapshot обновлён в постоянном слоте' if ok else '⚠️ Telegram SQLite snapshot не создан')
                except Exception:
                    pass
            try:
                pool = globals().get('BACKUP_TASK_POOL') or globals().get('GENERAL_TASK_POOL')
                if pool is not None:
                    try:
                        pool.submit_unique('manual-telegram-snapshot-v236', _v236_manual_snapshot_job)
                    except Exception:
                        pool.submit('manual-telegram-snapshot-v236', _v236_manual_snapshot_job)
            except Exception:
                pass
            return True
        if action == 'mega_open':
            try:
                bot.answer_callback_query(call.id)
            except Exception:
                pass
            safe_edit(bot, call, window_mark(mega_contour_status_text_v234(), 'Ф236'), reply_markup=mega_contour_keyboard_v234())
            return True
        if action == 'mega_toggle':
            new_state = set_mega_contour_enabled_v234(not mega_contour_enabled_v234())
            blocked = False
            msg = 'Хранилище: MEGA' if new_state else 'Хранилище: Telegram durable'
            try:
                bot.answer_callback_query(call.id, msg, show_alert=blocked)
            except Exception:
                pass
            safe_edit(bot, call, window_mark(mega_contour_status_text_v234(), 'Ф236'), reply_markup=mega_contour_keyboard_v234())
            return True
        if action == 'secret_open':
            try:
                bot.answer_callback_query(call.id)
            except Exception:
                pass
            safe_edit(bot, call, window_mark(secret_storage_status_text_v234(), 'Ф236'), reply_markup=secret_storage_keyboard_v234())
            return True
        if action in {'secret_tg', 'secret_mega'}:
            requested = 'mega' if action == 'secret_mega' else 'telegram'
            set_secret_storage_backend_v234(requested)
            effective = secret_storage_effective_backend_v234()
            msg = 'MEGA выбрана, но сейчас недоступна. Работает Telegram fallback.' if requested != effective else 'SECRET → MEGA' if effective == 'mega' else 'SECRET → Telegram-канал'
            try:
                bot.answer_callback_query(call.id, msg, show_alert=bool(requested != effective))
            except Exception:
                pass
            safe_edit(bot, call, window_mark(secret_storage_status_text_v234(), 'Ф236'), reply_markup=secret_storage_keyboard_v234())
            return True
    if resolved.startswith('v233:external:'):
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
        if resolved == 'v233:external:open':
            try:
                bot.answer_callback_query(call.id)
            except Exception:
                pass
            safe_edit(bot, call, window_mark(external_local_only_status_text_v233(), 'Ф234'), reply_markup=external_local_only_keyboard_v233())
            return True
        if resolved == 'v233:external:toggle':
            env_forced = str(os.getenv('RENDER_TELEGRAM_ONLY', '') or '').strip().casefold() in {'1', 'true', 'yes', 'on', 'вкл'}
            if env_forced and external_local_only_v233_enabled():
                try:
                    bot.answer_callback_query(call.id, 'Режим зафиксирован Render Environment. Уберите RENDER_TELEGRAM_ONLY=1 для выключения.', show_alert=True)
                except Exception:
                    pass
                return True
            requested_state = not external_local_only_v233_enabled()
            try:
                bot.answer_callback_query(call.id, 'Только Render: ВКЛ' if requested_state else 'Переключаю хранилище…')
            except Exception:
                pass
            new_state = set_external_local_only_v233(requested_state)
            if not new_state:
                try:
                    if mega_contour_enabled_v234() and secret_storage_backend_v234() == 'mega':
                        schedule_secret_storage_migration_v234('mega')
                except Exception:
                    pass
            safe_edit(bot, call, window_mark(external_local_only_status_text_v233(), 'Ф234'), reply_markup=external_local_only_keyboard_v233())
            return True
    if resolved == 'v255:constitution:loss_toggle':
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
        new_state = set_constitution_loss_guard_v255(not constitution_loss_guard_enabled_v255())
        try:
            bot.answer_callback_query(call.id, 'Защита потери записей: ВКЛ' if new_state else 'Защита потери записей: ВЫКЛ')
        except Exception:
            pass
        try:
            safe_edit(bot, call, build_info_text(cid), reply_markup=build_info_keyboard(cid))
        except Exception:
            pass
        try:
            bot_journal('data_constitution_loss_guard_toggle_v255', cid, f'enabled={int(new_state)}')
        except Exception:
            pass
        return True
    if resolved.startswith('v232:constitution:'):
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
        if resolved == 'v232:constitution:open':
            try:
                bot.answer_callback_query(call.id)
            except Exception:
                pass
            try:
                safe_edit(bot, call, window_mark(constitution_status_text(), 'Ф233'), reply_markup=constitution_control_keyboard_v232())
            except Exception:
                pass
            return True
        fn = globals().get('v232_constitution_callback_final')
        if callable(fn) and fn(call, resolved):
            return True
    if resolved == 'v229:tasks:single_window':
        try:
            cid = int(call.message.chat.id)
            if cid != int(OWNER_ID or 0):
                return True
            new_state = set_tasks_single_window_v229(not tasks_single_window_enabled_v229())
            try:
                bot.answer_callback_query(call.id, 'Задачи в одном окне: ВКЛ' if new_state else 'Задачи в одном окне: ВЫКЛ')
            except Exception:
                pass
            safe_edit(bot, call, build_info_text(cid), reply_markup=build_info_keyboard(cid))
            try:
                bot_journal('tasks_single_window_toggle_v229', cid, f'enabled={int(new_state)}')
            except Exception:
                pass
            return True
        except Exception:
            return True
    if resolved.startswith('v223:directive:'):
        fn = globals().get('v223_directive_callback_final')
        if callable(fn) and fn(call, resolved):
            return True
    if resolved.startswith('v220:contour_access:'):
        fn = globals().get('v220_contour_access_callback_final')
        if callable(fn) and fn(call, resolved):
            return True
    if resolved.startswith('v219:annot:'):
        fn = globals().get('v219_annotation_callback_final')
        if callable(fn) and fn(call, resolved):
            return True
    if resolved.startswith('v218:demo:') or resolved.startswith('v149:rem:item_complete:') or resolved.startswith('v149:rem:done:'):
        fn = globals().get('v218_callback_final')
        if callable(fn) and fn(call, resolved):
            return True
    if resolved.startswith('v217:') or resolved.startswith('v149:rem:item_complete:'):
        fn = globals().get('v217_callback_final')
        if callable(fn) and fn(call, resolved):
            return True
    if resolved.startswith('v215:mode:'):
        fn = globals().get('v215_contour_mode_callback')
        if callable(fn) and fn(call, resolved):
            return True
    fn = globals().get('_v161_critical_callback')
    if callable(fn) and fn(call, resolved):
        return True
    fn = globals().get('_v157_handle_callback')
    if callable(fn) and fn(call):
        return True
    fn = globals().get('_v156_handle_process_toggle')
    if callable(fn) and fn(call):
        return True
    fn = globals().get('_v160_handle_special_callback')
    if callable(fn) and fn(call, resolved):
        return True
    fn = globals().get('_v176_filter')
    if callable(fn) and fn(call):
        globals()['_v176_callback'](call)
        return True
    fn = globals().get('_v196_branch_callback_filter')
    if callable(fn) and fn(call):
        globals()['_v196_branch_callback'](call)
        return True
    if resolved.startswith('rem:'):
        reminder_callback(call)
        return True
    fn = globals().get('_v163_exact_today_filter')
    if callable(fn) and fn(call):
        globals()['_v163_exact_today_callback'](call)
        return True
    fn = globals().get('_v164_circle_callback_filter')
    if callable(fn) and fn(call):
        globals()['_v164_circle_callback'](call)
        return True
    fn = globals().get('_v167_schedule_callback_filter')
    if callable(fn) and fn(call):
        globals()['_v167_schedule_callback'](call)
        return True
    if resolved.startswith('v171:') or resolved == 'none':
        globals()['_v171_special_callback'](call)
        return True
    fn = globals().get('task_dispatcher_callback_final')
    if callable(fn) and fn(call):
        return True
    on_callback(call)
    return True

def final_callback_router(call):
    clock = globals().get('_v176_time') or globals().get('time')
    started = clock.monotonic()
    raw, resolved = _v179_resolve_callback(call)
    try:
        _V177_PERF_LOCAL.action = resolved[:120]
    except Exception:
        pass
    cid = None
    seq_before = 0
    err = ''
    try:
        cid = int(call.message.chat.id)
        seq_before = int(globals().get('_WINDOW_DIAG_SEQ', 0) or 0)
    except Exception:
        pass
    if resolved != 'none':
        try:
            if v176_process_enabled('btn_chain'):
                bot_journal('button_chain_press', cid, f'action={resolved}')
        except Exception:
            pass
    try:
        return _v179_dispatch_callback(call, raw, resolved)
    except Exception as exc:
        err = f'{type(exc).__name__}: {exc}'
        try:
            log_error(f'FINAL_CALLBACK_ERROR action={resolved} chat={cid}: {exc}')
        except Exception:
            pass
        try:
            bot.answer_callback_query(call.id, 'Ошибка выполнения кнопки. Записано в журнал.', show_alert=True)
        except Exception:
            pass
        return None
    finally:
        try:
            elapsed = max(0.0, clock.monotonic() - started)
            if raw != 'v176:speed_clear':
                _V176_PERF.append({'ts': clock.time(), 'action': resolved[:120], 'elapsed': elapsed})
            if resolved != 'none' and v176_process_enabled('btn_chain'):
                bot_journal('button_chain_result', cid, f'action={resolved}; ok={int(not bool(err))}; elapsed={elapsed:.3f}s')
        except Exception:
            pass
        try:
            audit = globals().get('_v155_record_button_outcome')
            if callable(audit) and globals().get('V155_BUTTON_AUDIT_ENABLED', False):
                audit(call, raw, resolved, started, seq_before, err)
        except Exception:
            pass
        try:
            _V177_PERF_LOCAL.action = ''
        except Exception:
            pass
bot.callback_query_handler(func=lambda c: True)(final_callback_router)
_V179_FINAL_CALLBACK_HANDLERS = 1
_V221_FINAL_SEND = getattr(bot, 'send_message', None)
_V221_FINAL_EDIT_TEXT = getattr(bot, 'edit_message_text', None)
_V221_FINAL_EDIT_CAPTION = getattr(bot, 'edit_message_caption', None)
_V221_FINAL_EDIT_MARKUP = getattr(bot, 'edit_message_reply_markup', None)
_V221_FINAL_DELETE = getattr(bot, 'delete_message', None)

def _v221_final_filter_markup(chat_id, reply_markup):
    try:
        fn = globals().get('v221_finalize_contour_markup')
        return fn(reply_markup, int(chat_id or 0)) if callable(fn) else reply_markup
    except Exception:
        return reply_markup

def _v227_prepare_transport_markup(chat_id, reply_markup, text=''):
    """Prepare exactly what Telegram should receive: augment first, final policy last."""
    try:
        fn = globals().get('v227_render_effective_contour_markup')
        if callable(fn):
            return fn(reply_markup, str(text or ''), int(chat_id or 0))
    except Exception:
        pass
    prepared = reply_markup
    try:
        augment = globals().get('_v160_augment_markup')
        if callable(augment):
            prepared = augment(prepared, str(text or ''), int(chat_id or 0))
    except Exception:
        pass
    return _v221_final_filter_markup(chat_id, prepared)

def _v221_record_transport(chat_id, message_id, reply_markup, text='', source_markup=None):
    try:
        fn = globals().get('v221_record_live_markup')
        if callable(fn) and reply_markup is not None:
            try:
                fn(int(chat_id), int(message_id), reply_markup, str(text or ''), source_markup=source_markup)
            except TypeError:
                fn(int(chat_id), int(message_id), reply_markup, str(text or ''))
        elif callable(globals().get('v221_forget_live_markup')) and reply_markup is None:
            globals()['v221_forget_live_markup'](int(chat_id), int(message_id))
    except Exception:
        pass
if callable(_V221_FINAL_SEND):

    def _v221_send_message(chat_id, text, *args, **kwargs):
        source_markup = kwargs.get('reply_markup')
        prepared = _v227_prepare_transport_markup(chat_id, source_markup, text)
        kwargs['reply_markup'] = prepared
        result = _V221_FINAL_SEND(chat_id, text, *args, **kwargs)
        try:
            _v221_record_transport(int(chat_id), int(getattr(result, 'message_id', 0) or 0), prepared, text, source_markup=source_markup)
        except Exception:
            pass
        return result
    bot.send_message = _v221_send_message
if callable(_V221_FINAL_EDIT_TEXT):

    def _v221_edit_message_text(text, *args, **kwargs):
        chat_id = kwargs.get('chat_id') if kwargs.get('chat_id') is not None else args[0] if len(args) > 0 else None
        message_id = kwargs.get('message_id') if kwargs.get('message_id') is not None else args[1] if len(args) > 1 else None
        source_markup = kwargs.get('reply_markup')
        prepared = _v227_prepare_transport_markup(chat_id, source_markup, text)
        kwargs['reply_markup'] = prepared
        result = _V221_FINAL_EDIT_TEXT(text, *args, **kwargs)
        if chat_id is not None and message_id is not None:
            _v221_record_transport(chat_id, message_id, prepared, text, source_markup=source_markup)
        return result
    bot.edit_message_text = _v221_edit_message_text
if callable(_V221_FINAL_EDIT_CAPTION):

    def _v221_edit_message_caption(*args, **kwargs):
        positional = list(args)
        caption = kwargs.get('caption')
        if caption is None and positional:
            caption = positional[0]
        chat_id = kwargs.get('chat_id')
        message_id = kwargs.get('message_id')
        if chat_id is None and len(positional) > 1:
            chat_id = positional[1]
        if message_id is None and len(positional) > 2:
            message_id = positional[2]
        source_markup = kwargs.get('reply_markup')
        prepared = _v227_prepare_transport_markup(chat_id, source_markup, caption)
        kwargs['reply_markup'] = prepared
        result = _V221_FINAL_EDIT_CAPTION(*args, **kwargs)
        if chat_id is not None and message_id is not None:
            _v221_record_transport(chat_id, message_id, prepared, caption, source_markup=source_markup)
        return result
    bot.edit_message_caption = _v221_edit_message_caption
if callable(_V221_FINAL_EDIT_MARKUP):

    def _v221_edit_message_reply_markup(*args, **kwargs):
        positional = list(args)
        chat_id = kwargs.get('chat_id') if kwargs.get('chat_id') is not None else positional[0] if len(positional) > 0 else None
        message_id = kwargs.get('message_id') if kwargs.get('message_id') is not None else positional[1] if len(positional) > 1 else None
        source_markup = kwargs.get('reply_markup') if 'reply_markup' in kwargs else positional[2] if len(positional) > 2 else None
        prepared = _v221_final_filter_markup(chat_id, source_markup)
        if 'reply_markup' in kwargs:
            kwargs['reply_markup'] = prepared
        elif len(positional) > 2:
            positional[2] = prepared
            args = tuple(positional)
        result = _V221_FINAL_EDIT_MARKUP(*args, **kwargs)
        if chat_id is not None and message_id is not None:
            _v221_record_transport(chat_id, message_id, prepared, '', source_markup=source_markup)
        return result
    bot.edit_message_reply_markup = _v221_edit_message_reply_markup
if callable(_V221_FINAL_DELETE):

    def _v221_delete_message(chat_id, message_id, *args, **kwargs):
        result = _V221_FINAL_DELETE(chat_id, message_id, *args, **kwargs)
        try:
            fn = globals().get('v221_forget_live_markup')
            if callable(fn):
                fn(int(chat_id), int(message_id))
        except Exception:
            pass
        return result
    bot.delete_message = _v221_delete_message
try:
    _canon_bot_journal__001('v221_final_transport_policy_ready', int(OWNER_ID or 0), 'after_constructor=1; annotation/menu final_filter=1; live_markup_registry=1')
except Exception:
    pass
_add_export_period_rows = _canon_add_export_period_rows__001
_apply_finance_window_mode_choice = _canon_apply_finance_window_mode_choice__002
_atomic_json_dump = _canon_atomic_json_dump__001
_callback_should_debounce = _canon_callback_should_debounce__001
_category_excel_expected_annotations = _canon_category_excel_expected_annotations__001
_category_rows_without_description = _canon_category_rows_without_description__001
_collect_forward_picker_items = _canon_collect_forward_picker_items__002
_compact_simple_excel_rows_and_annotations = _canon_compact_simple_excel_rows_and_annotations__001
_delta_remote_candidates_after = _canon_delta_remote_candidates_after__002
_delta_upload_payload = _v240_delta_upload_payload
_durable_effect_report = _canon_durable_effect_report__001
_durable_expected_effects = _canon_durable_expected_effects__001
_durable_normalize_expected_for_route = _canon_durable_normalize_expected_for_route__001
_exact_export_rows = _canon_exact_export_rows__001
_execute_telegram_payload = _canon_execute_telegram_payload__001
_export_calendar_start_keyboard = _canon_export_calendar_start_keyboard__001
_export_end_calendar_keyboard = _canon_export_end_calendar_keyboard__001
_file_job_progress = _canon_file_job_progress__001
_file_job_tick = _canon_file_job_tick__001
_fin_forward_batch_finish_target = _canon_fin_forward_batch_finish_target__001
_forget_forward_pair_if_empty = _canon_forget_forward_pair_if_empty__001
_google_access_token = _canon_google_access_token__001
_google_service_account_info = _canon_google_service_account_info__001
_google_sheets_create_category_report = _canon_google_sheets_create_category_report__001
_google_spreadsheet_id = _canon_google_spreadsheet_id__001
_interactive_file_job_runner = _canon_interactive_file_job_runner__001
_is_bot_removed_error = _canon_is_bot_removed_error__001
_mega_run = _canon_mega_run__001
_mega_task_move = _canon_mega_task_move__002
_mega_task_prune_done_async = _canon_mega_task_prune_done_async__002
_mega_task_upload_new_pending = _canon_mega_task_upload_new_pending__004
_modern_category_excel_styles_comments = _canon_modern_category_excel_styles_comments__001
_modern_category_no_description_styles_comments = _canon_modern_category_no_description_styles_comments__001
_modern_compact_excel_styles_comments = _canon_modern_compact_excel_styles_comments__001
_modern_simple_excel_styles_comments = _canon_modern_simple_excel_styles_comments__001
_period_excel_style_keyboard = _canon_period_excel_style_keyboard__001
_period_export_bounds = _canon_period_export_bounds__001
_period_export_rows = _canon_period_export_rows__001
_persist_forward_finance_delivery_now = _canon_persist_forward_finance_delivery_now__001
_prune_delta_files_after_full_snapshot = _canon_prune_delta_files_after_full_snapshot__002
_record_day_key = _canon_record_day_key__001
_remember_forward_pair = _canon_remember_forward_pair__001
_reminder_cfg = _canon_reminder_cfg__001
_reminder_create = _canon_reminder_create__001
_reminder_delete_message_map = _canon_reminder_delete_message_map__001
_reminder_group_delete_message = _canon_reminder_group_delete_message__001
_reminder_group_send_job = _canon_reminder_group_send_job__002
_reminder_items = _canon_reminder_items__001
_reminder_mark_completed = _canon_reminder_mark_completed__001
_reminder_send_cycle = _canon_reminder_send_cycle__002
_reminder_tick = _canon_reminder_tick__001
_run_delta_batch = _canon_run_delta_batch__002
_run_pending_ui_edit = _canon_run_pending_ui_edit__001
_runtime_export_select_paths = _canon_runtime_export_select_paths__001
_runtime_heartbeat_job = _canon_runtime_heartbeat_job__001
_tg_durable_send_blob_v234 = _canon_tg_durable_send_blob_v234__002
_v149_complete_reminder = _v221_complete_reminder
_v149_google_wait = _canon_v149_google_wait__002
_v149_group_message_text = _v218_group_message_text
_v149_reminder_chat_allowed = _canon_v149_reminder_chat_allowed__001
_v149_reminder_message_text = _v218_reminder_message_text
_v149_reminders_for_completion = _v221_reminders_for_completion
_v151_categories = _canon_v151_categories__001
_v151_category_table = _canon_v151_category_table__001
_v151_context_bounds = _canon_v151_context_bounds__001
_v151_simple_table = _canon_v151_simple_table__001
_v151_usd_records = _canon_v151_usd_records__001
_v153_instance_lease_check = _canon_v153_instance_lease_check__001
_v153_reconcile_windows = _canon_v153_reconcile_windows__001
_v153_schedule_migration = _canon_v153_schedule_migration__001
_v153_validate_restore_gz = _canon_v153_validate_restore_gz__001
_v155_expected_marker = _canon_v155_expected_marker__001
_v156_process_status_arm = _canon_v156_process_status_arm__001
_v156_process_status_schedule = _canon_v156_process_status_schedule__001
_v156_process_status_tick = _canon_v156_process_status_tick__001
_v157_handle_callback = _canon_v157_handle_callback__001
_v160_augment_markup = _canon_v160_augment_markup__002
_v160_begin_capture = _canon_v160_begin_capture__002
_v160_delete_quiet = _canon_v160_delete_quiet__001
_v160_export_text = _canon_v160_export_text__001
_v160_get_pending = _canon_v160_get_pending__002
_v160_handle_special_callback = _canon_v160_handle_special_callback__001
_v160_save_tz = _canon_v160_save_tz__001
_v160_schedule_delete = _canon_v160_schedule_delete__001
_v160_set_pending = _canon_v160_set_pending__002
_v160_source_meta = _canon_v160_source_meta__001
_v161_critical_callback = _v214_critical_callback_final
_v161_edit_retry = _canon_v161_edit_retry__001
_v162_force_start = _v221_force_start
_v167_tz_export = _canon_v167_tz_export__001
_v172_clear_input = _v213_v172_clear_input
_v172_get_input = _v213_v172_get_input
_v172_is_complete = _canon_v172_is_complete__001
_v172_prompt = _v214_v172_prompt
_v172_set_input = _v213_v172_set_input
_v172_task_message_input = _v214_v172_task_message_input
_v174_auto_process = _v219_task_auto_process
_v174_callback = _v213_v174_callback
_v174_get_input = _v213_v174_get_input
_v174_handle_own_input = _canon_v174_handle_own_input__001
_v174_menu_text_kb = _v220_task_menu_text_kb
_v174_pop_input = _v213_v174_pop_input
_v174_prompt_input = _canon_v174_prompt_input__001
_v174_set_input = _v213_v174_set_input
_v177_download_remote_json_batch = _canon_v177_download_remote_json_batch__002
_v196_handle_c1_callback = _v213_v196_handle_c1_callback
_v196_handle_c2_callback = _v213_v196_handle_c2_callback
_v207_reminder_complete_button_enabled = _v218_reminder_complete_button_enabled
_v207_reminder_complete_keyboard = _v220_reminder_complete_keyboard
_v207_reminder_group_keyboard = _v220_reminder_group_keyboard
_v212_tz_add_part = _canon_v212_tz_add_part__002
_v213_cancel_markup = _v214_cancel_markup
_v213_show_neutral_home = _v220_show_neutral_home
_v213_task_input_timeout = _v214_task_input_timeout
_v215_go_mode = _v218_go_mode
_v217_chat_reminder_rows = _v221_chat_reminder_rows
_v217_find_reply_reminder = _v221_find_reply_reminder
_v218_complete_command = _v221_complete_command
_v240_restore_reanchor_guaranteed = _canon_v240_restore_reanchor_guaranteed__002
_window_diag_duplicate_marker = _canon_window_diag_duplicate_marker__001
_write_simple_xlsx = _canon_write_simple_xlsx__001
_write_tabl_lsx_xlsx = _canon_write_tabl_lsx_xlsx__001
_xlsx_simple_rows_with_balances = _canon_xlsx_simple_rows_with_balances__001
add_forward_link = _v217_add_forward_link
backup_excel_all_enabled = _canon_backup_excel_all_enabled__001
backup_window_for_owner = _canon_backup_window_for_owner__001
begin_secret_full_edit = _canon_begin_secret_full_edit__002
bind_chat_to_owner_scope = _canon_bind_chat_to_owner_scope__001
bot_journal = _canon_bot_journal__001
build_chat_description_menu = _canon_build_chat_description_menu__001
build_contour_menu_guide = _v223_build_contour_menu_guide
build_contour_mode_control = _v223_build_contour_mode_control
build_contour_start_modes = _v223_build_contour_start_modes
build_exact_category_stats_xlsx_rows = _canon_build_exact_category_stats_xlsx_rows__001
build_fin_window_usd_month_keyboard = _canon_build_fin_window_usd_month_keyboard__001
build_fin_windows_chat_menu = _canon_build_fin_windows_chat_menu__001
build_finance_mode_config_menu = _canon_build_finance_mode_config_menu__001
build_finance_toggle_chat_menu = _canon_build_finance_toggle_chat_menu__001
build_forward_menu_keyboard_for_current_mode = _v220_forward_menu_keyboard
build_forward_menu_text_for_current_mode = _canon_build_forward_menu_text_for_current_mode__001
build_forward_new_menu = _canon_build_forward_new_menu__001
build_forward_source_menu = _canon_build_forward_source_menu__001
build_forward_status_lines = _canon_build_forward_status_lines__001
build_forward_target_menu = _canon_build_forward_target_menu__001
build_gomonk_menu_keyboard = _canon_build_gomonk_menu_keyboard__001
build_gomonk_menu_text = _canon_build_gomonk_menu_text__001
build_help_text = _canon_build_help_text__001
build_info_keyboard = _canon_build_info_keyboard__002
build_info_text = _v237_1_storage_build_info_text
build_internal_timer_input_keyboard = _canon_build_internal_timer_input_keyboard__002
build_internal_timer_input_text = _canon_build_internal_timer_input_text__001
build_internal_timers_text = _canon_build_internal_timers_text__001
build_main_keyboard = _v220_build_main_keyboard
build_quick_balance_mode_menu = _canon_build_quick_balance_mode_menu__001
build_reminder_list_keyboard = _v220_reminder_list_keyboard
build_reminder_list_text = _canon_build_reminder_list_text__001
build_reminder_menu_keyboard = _v218_build_reminder_menu_keyboard
build_reminder_menu_text = _canon_build_reminder_menu_text__001
build_safety_profile_keyboard = _canon_build_safety_profile_keyboard__001
build_usd_month_keyboard = _canon_build_usd_month_keyboard__001
build_v217_chat_reminders_keyboard = _v220_chat_reminder_keyboard
build_v217_forward_scope_keyboard = _v220_forward_scope_keyboard
chat_button_title = _canon_chat_button_title__001
cleanup_open_window_registry = _canon_cleanup_open_window_registry__001
clear_forward_all = _canon_clear_forward_all__001
collect_all_known_chat_ids = _canon_collect_all_known_chat_ids__001
collect_forward_menu_chats = _canon_collect_forward_menu_chats__001
collect_forward_pairs_for_menu = _canon_collect_forward_pairs_for_menu__002
config_guard_boot_verify_v234 = _canon_config_guard_boot_verify_v234__002
config_guard_sync_remote_v234 = _canon_config_guard_sync_remote_v234__002
constitution_download_best_boot_generation_v235 = _canon_constitution_download_best_boot_generation_v235__002
contour_callback_guard = _v223_contour_callback_guard
cycle_forward_copy_edit_mode = _canon_cycle_forward_copy_edit_mode__001
delete_auto_finance_windows_for_chat = _canon_delete_auto_finance_windows_for_chat__001
durable_task_required = _canon_durable_task_required__001
ensure_hidden_finance_for_forward_dst = _canon_ensure_hidden_finance_for_forward_dst__001
excel_interface_mode = _canon_excel_interface_mode__001
excel_new_export_options = _canon_excel_new_export_options__001
excel_table_style = _canon_excel_table_style__001
fast_ui_edit_message_text = _canon_fast_ui_edit_message_text__001
force_new_day_window = _canon_force_new_day_window__001
forward_any_message = _canon_forward_any_message__002
forward_copy_edit_mode = _canon_forward_copy_edit_mode__001
forward_copy_edit_mode_label = _canon_forward_copy_edit_mode_label__001
get_additional_owner_ids = _canon_get_additional_owner_ids__001
get_connected_chat_ids = _canon_get_connected_chat_ids__001
get_registered_open_window = _canon_get_registered_open_window__001
handle_gomonk_insert_message = _canon_handle_gomonk_insert_message__001
handle_o9_secret_triple_click = _canon_handle_o9_secret_triple_click__001
internal_timer_seconds = _canon_internal_timer_seconds__001
is_chat_bot_removed = _canon_is_chat_bot_removed__001
is_owner_chat = _canon_is_owner_chat__001
is_primary_owner = _canon_is_primary_owner__001
keepalive_begin_peer_url_input = _canon_keepalive_begin_peer_url_input__002
keepalive_cancel_input = _canon_keepalive_cancel_input__002
load_data = _canon_load_data__001
log_error = _canon_log_error__001
log_info = _canon_log_info__001
lowram_apply_deltas_after_db_snapshot = _canon_lowram_apply_deltas_after_db_snapshot__002
make_global_backup_payload = _canon_make_global_backup_payload__001
mega_restore_full_from_cloud = _canon_mega_restore_full_from_cloud__001
mega_restore_sqlite_snapshot_from_cloud = _canon_mega_restore_sqlite_snapshot_from_cloud__001
mega_task_begin = _canon_mega_task_begin__002
mega_task_finish = _canon_mega_task_finish__002
mega_task_known_state = _canon_mega_task_known_state__002
mega_task_refresh_registry = _canon_mega_task_refresh_registry__003
mega_task_registry_stats = _canon_mega_task_registry_stats__002
mega_tasks_active = _canon_mega_tasks_active__002
mega_upload_chat_backup_bundle = _canon_mega_upload_chat_backup_bundle__002
mega_upload_chat_latest_json_only = _canon_mega_upload_chat_latest_json_only__002
mega_upload_latest_database_backup = _canon_mega_upload_latest_database_backup__002
memory_malloc_trim = _canon_memory_malloc_trim__001
migrate_chat_id_everywhere = _canon_migrate_chat_id_everywhere__001
migrate_recent_expense_shortcut_events = _canon_migrate_recent_expense_shortcut_events__001
owner_scope_id = _canon_owner_scope_id__001
owner_scoped_settings = _canon_owner_scoped_settings__001
parse_gomonk_entries = _canon_parse_gomonk_entries__001
pending_input_cancel_callback_final = _canon_pending_input_cancel_callback_final__001
persist_critical_delta_now = _canon_persist_critical_delta_now__003
process_visual_status_enabled = _canon_process_visual_status_enabled__001
refresh_balance_panel_now = _canon_refresh_balance_panel_now__001
refresh_registered_financial_windows = _canon_refresh_registered_financial_windows__001
refresh_total_message_if_any = _canon_refresh_total_message_if_any__001
register_open_window = _canon_register_open_window__001
reminder_merge_enabled = _canon_reminder_merge_enabled__001
reminder_merge_mode = _canon_reminder_merge_mode__001
reminder_merge_mode_label = _canon_reminder_merge_mode_label__001
reminder_ui_mode = _canon_reminder_ui_mode__001
remove_forward_finance = _canon_remove_forward_finance__002
remove_forward_link = _v217_remove_forward_link
render_usd_month_window = _canon_render_usd_month_window__001
resolve_forward_targets = _canon_resolve_forward_targets__001
restore_previous_window = _canon_restore_previous_window__001
return_to_main_window_closing_previous = _canon_return_to_main_window_closing_previous__002
runtime_classify_previous = _canon_runtime_classify_previous__001
runtime_mark_ready = _canon_runtime_mark_ready__001
runtime_upload_snapshot = _canon_runtime_upload_snapshot__001
safe_edit = _canon_safe_edit__001
safe_edit_current_only = _canon_safe_edit_current_only__001
safety_permission_allowed = _canon_safety_permission_allowed__001
schedule_callback_receipt_ack = _canon_schedule_callback_receipt_ack__001
schedule_config_backup_for_chats = _canon_schedule_config_backup_for_chats__002
schedule_delta_backup = _canon_schedule_delta_backup__003
schedule_forward_any_message = _canon_schedule_forward_any_message__001
schedule_mega_task_recovery = _canon_schedule_mega_task_recovery__003
schedule_safe_failed_task_repairs = _canon_schedule_safe_failed_task_repairs__002
schedule_startup_main_windows = _canon_schedule_startup_main_windows__002
security_known_users = _canon_security_known_users__001
security_role_for_user = _canon_security_role_for_user__001
security_set_role = _canon_security_set_role__001
security_user_allowed = _canon_security_user_allowed__001
send_and_auto_delete = _canon_send_and_auto_delete__001
send_csv_for_chat_to = _canon_send_csv_for_chat_to__001
send_csv_wedthu = _canon_send_csv_wedthu__001
send_exact_range_export = _canon_send_exact_range_export__001
send_export_for_chat_to = _canon_send_export_for_chat_to__001
send_html_and_auto_delete = _canon_send_html_and_auto_delete__001
send_runtime_export_zip = _canon_send_runtime_export_zip__001
set_additional_owner = _canon_set_additional_owner__001
set_backup_excel_all_enabled = _canon_set_backup_excel_all_enabled__001
set_chat_bot_removed = _canon_set_chat_bot_removed__001
set_excel_interface_mode = _canon_set_excel_interface_mode__001
set_excel_table_style = _canon_set_excel_table_style__001
set_forward_copy_edit_mode = _canon_set_forward_copy_edit_mode__001
set_forward_finance = _canon_set_forward_finance__002
set_forward_menu_new_style_enabled = _canon_set_forward_menu_new_style_enabled__001
set_internal_timer_seconds = _canon_set_internal_timer_seconds__001
set_reminder_ui_mode = _canon_set_reminder_ui_mode__001
set_webhook = _canon_set_webhook__001
show_contour_start_modes = _v224_show_contour_start_modes
submit_interactive_file_job = _canon_submit_interactive_file_job__001
task_dispatcher_callback_final = _v219_task_dispatcher_callback_final
telegram_apply_remote_deltas_v234 = _canon_telegram_apply_remote_deltas_v234__002
telegram_restore_sqlite_snapshot_v234 = _canon_telegram_restore_sqlite_snapshot_v234__002
telegram_schedule_delta_backup_v234 = _canon_telegram_schedule_delta_backup_v234__002
telegram_schedule_full_snapshot_v234 = _canon_telegram_schedule_full_snapshot_v234__002
telegram_upload_sqlite_snapshot_v234 = _canon_telegram_upload_sqlite_snapshot_v234__002
tenant_can_manage = _canon_tenant_can_manage__001
tenant_chats_text = _canon_tenant_chats_text__001
tenant_consume_invite = _canon_tenant_consume_invite__001
tenant_create_invite = _canon_tenant_create_invite__001
tenant_dashboard_keyboard = _canon_tenant_dashboard_keyboard__001
tenant_dashboard_text = _canon_tenant_dashboard_text__001
tenant_detail_text = _canon_tenant_detail_text__001
tenant_google_handle_message = _canon_tenant_google_handle_message__002
tenant_handle_callback = _canon_tenant_handle_callback__001
tenant_id_for_chat = _canon_tenant_id_for_chat__001
tenant_note_chat_seen = _canon_tenant_note_chat_seen__001
tenant_same_space = _canon_tenant_same_space__001
tenant_visible_spaces = _canon_tenant_visible_spaces__001
toggle_excel_new_export_option = _canon_toggle_excel_new_export_option__001
toggle_forward_menu_new_style = _canon_toggle_forward_menu_new_style__001
ui_constructor_handle_message = _v213_ui_constructor_handle_message
unregister_open_window = _canon_unregister_open_window__001
update_chat_info_from_chat_object = _canon_update_chat_info_from_chat_object__001
update_chat_info_from_message = _canon_update_chat_info_from_message__001
update_or_send_day_window = _canon_update_or_send_day_window__001
v149_extension_callback = _canon_v149_extension_callback__002
v152_human_download_name = _canon_v152_human_download_name__001
v163_webhook_select_lane = _canon_v163_webhook_select_lane__001
v217_callback_final = _canon_v217_callback_final__002
v218_callback_final = _v221_v218_callback_final
v219_annotation_callback_final = _v226_annotation_callback_final
v220_contour_access_callback_final = _v221_contour_access_callback_final
wait_durable_subtasks = _canon_wait_durable_subtasks__001
window_diag_fast_ui_apply = _canon_window_diag_fast_ui_apply__001
window_diag_prepare_fast_ui_payload = _canon_window_diag_prepare_fast_ui_payload__001
# v262
