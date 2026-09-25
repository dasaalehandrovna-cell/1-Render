# v267
# OCH12.34: infrastructure/wiring shell; business function bodies live only in 11-14 owner files.

# --- ИСТОЧНИК: 30_secret.py ---
SECRET_CODEWORDS = {'секрет', 'сикрет', 'secret', 'sicret', 'sekret', 'sikret', 'cekret', 'cikret', '🤫', '🙊', '🤐', '🔐', '🔏'}
OWNER_ACTIVATION_RE = re.compile('^/(?:владелец|vladelec)(?:1904|-1904|_1904)(?:@\\w+)?$', re.I)
SECRET_ACCESS_RE = re.compile('^/(?:секрет|secret|sekret|cekret)(?:(?:1904|-1904|_1904))?(?:@\\w+)?$', re.I)
_secret_sequence_state = {}
_secret_calendar_timers = {}
_secret_calendar_lock = threading.RLock()
_secret_mega_locks = defaultdict(threading.Lock)
_secret_media_timer_lock = threading.RLock()
_secret_media_timer_generation = {}
SECRET_AUTO_CLOSE_SECONDS = 90
SECRET_COUNTDOWN_STEP_SECONDS = 30

# [OCH12.35 OWNER] _secret_countdown_text -> 18_business_secret.py
_owner_install('secret', 'secret:0033')

# [OCH12.35 OWNER] _secret_close_label -> 18_business_secret.py
_owner_install('secret', 'secret:0034')

# [OCH12.35 OWNER] _secret_records -> 18_business_secret.py
_owner_install('secret', 'secret:0035')

# [OCH12.35 OWNER] _is_secret_media_record -> 18_business_secret.py
_owner_install('secret', 'secret:0036')

# [OCH12.35 OWNER] _ensure_secret_media_numbers -> 18_business_secret.py
_owner_install('secret', 'secret:0037')

# [OCH12.35 OWNER] _next_secret_media_number -> 18_business_secret.py
_owner_install('secret', 'secret:0038')

# [OCH12.35 OWNER] _secret_media_record_by_number -> 18_business_secret.py
_owner_install('secret', 'secret:0039')

# [OCH12.35 OWNER] migrate_legacy_owner_secrets -> 18_business_secret.py
_owner_install('secret', 'secret:0040')

# [OCH12.35 OWNER] _secret_file_id -> 18_business_secret.py
_owner_install('secret', 'secret:0041')

# [OCH12.35 OWNER] _secret_content_payload -> 18_business_secret.py
_owner_install('secret', 'secret:0042')

# [OCH12.35 OWNER] _secret_message_text -> 18_business_secret.py
_owner_install('secret', 'secret:0043')

# [OCH12.35 OWNER] _extract_secret_codeword -> 18_business_secret.py
_owner_install('secret', 'secret:0044')

# [OCH12.35 OWNER] _secret_chat_payload -> 18_business_secret.py
_owner_install('secret', 'secret:0045')

# [OCH12.35 OWNER] _secret_media_remote_name -> 18_business_secret.py
_owner_install('secret', 'secret:0046')

# [OCH12.35 OWNER] _compress_secret_video_low -> 18_business_secret.py
_owner_install('secret', 'secret:0047')

# [OCH12.35 OWNER] _upload_secret_record_media -> 18_business_secret.py
_owner_install('secret', 'secret:0048')

# [OCH12.35 OWNER] upload_chat_secrets_to_mega -> 18_business_secret.py
_owner_install('secret', 'secret:0049')
_secret_mega_upload_timers = {}
_secret_mega_upload_lock = threading.RLock()

# [OCH12.35 OWNER] schedule_secret_mega_upload -> 18_business_secret.py
_owner_install('secret', 'secret:0050')

# [OCH12.35 OWNER] save_secret_message -> 18_business_secret.py
_owner_install('secret', 'secret:0051')

# [OCH12.35 OWNER] save_secret_bot_copy -> 18_business_secret.py
_owner_install('secret', 'secret:0052')

# [OCH12.35 OWNER] capture_forwarded_bot_copy_as_secret -> 18_business_secret.py
_owner_install('secret', 'secret:0053')

# [OCH12.35 OWNER] sync_forwarded_secret_bot_copy_edit -> 18_business_secret.py
_owner_install('secret', 'secret:0054')

# [OCH12.35 OWNER] delete_secret_source_message -> 18_business_secret.py
_owner_install('secret', 'secret:0055')

# [OCH12.35 OWNER] is_total_secret_mode -> 18_business_secret.py
_owner_install('secret', 'secret:0056')

# [OCH12.35 OWNER] set_total_secret_mode -> 18_business_secret.py
_owner_install('secret', 'secret:0057')
TOTAL_SECRET_DECOY_PHRASES = ['Внимание и покой.', 'Осознанность здесь.', 'Тишина внутри.', 'Путь сердца.', 'Наблюдай себя.', 'Дыши глубже.', 'Присутствуй сейчас.', 'Свет внутри.', 'Любовь сильнее.', 'Мир в сердце.', 'Благодарность растёт.', 'Внутренняя работа.', 'Помни себя.', 'Будь свидетелем.', 'Не спи внутри.', 'Шаг к свету.', 'Сознание расширяется.', 'Тело помнит.', 'Душа учится.', 'Сердце открыто.', 'Молчание лечит.', 'Принятие есть.', 'Путь продолжается.', 'Воля и внимание.', 'Сила в тишине.', 'Радость без причины.', 'Любовь без условий.', 'Свидетель молчит.', 'Энергия вверх.', 'Чистое намерение.', 'Здесь и сейчас.', 'Осознанный выбор.', 'Божественное рядом.', 'Внутренний свет.', 'Учись видеть.', 'Покой глубже слов.', 'Смотри внутрь.', 'Развитие души.', 'Практика внимания.', 'Тишина ума.', 'Сердце знает.', 'Пусть будет свет.', 'Благость и мир.', 'Память о себе.', 'Человек пробуждается.', 'Дух ведёт.', 'Созерцай спокойно.', 'Истина проста.', 'Мягкая сила.', 'Светлая мысль.', 'Пробуждение рядом.', 'Душевный рост.', 'Путь любви.', 'Молитва сердца.', 'Чистое сознание.', 'Терпение и вера.', 'Гармония внутри.', 'Служение добру.', 'Внутренний учитель.', 'Свобода ума.', 'Осознай момент.', 'Сохрани тишину.', 'Открой сердце.', 'Иди глубже.', 'Будь настоящим.', 'Свети спокойно.', 'Доверяй пути.', 'Живи осознанно.']

# [OCH12.35 OWNER] total_secret_decoy_text -> 18_business_secret.py
_owner_install('secret', 'secret:0058')

# [OCH12.35 OWNER] maybe_send_total_secret_decoy -> 18_business_secret.py
_owner_install('secret', 'secret:0059')

# [OCH12.35 OWNER] forward_secret_message_now -> 18_business_secret.py
_owner_install('secret', 'secret:0060')

# [OCH12.35 OWNER] handle_secret_input_message -> 18_business_secret.py
_owner_install('secret', 'secret:0061')

# [OCH12.35 OWNER] handle_secret_edited_message -> 18_business_secret.py
_owner_install('secret', 'secret:0062')

# [OCH12.35 OWNER] secret_chats -> 18_business_secret.py
_owner_install('secret', 'secret:0063')

# [OCH12.35 OWNER] format_secret_records -> 18_business_secret.py
_owner_install('secret', 'secret:0064')

# [OCH12.35 OWNER] _secret_record_display_text -> 18_business_secret.py
_owner_install('secret', 'secret:0065')

# [OCH12.35 OWNER] _secret_media_caption -> 18_business_secret.py
_owner_install('secret', 'secret:0066')

# [OCH12.35 OWNER] build_secret_media_timer_keyboard -> 18_business_secret.py
_owner_install('secret', 'secret:0067')

# [OCH12.35 OWNER] cancel_secret_media_timer -> 18_business_secret.py
_owner_install('secret', 'secret:0068')

# [OCH12.35 OWNER] schedule_secret_media_close -> 18_business_secret.py
_owner_install('secret', 'secret:0069')

# [OCH12.35 OWNER] _send_secret_media_caption_message -> 18_business_secret.py
_owner_install('secret', 'secret:0070')

# [OCH12.35 OWNER] _send_secret_record_media -> 18_business_secret.py
_owner_install('secret', 'secret:0071')

# [OCH12.35 OWNER] send_secret_media -> 18_business_secret.py
_owner_install('secret', 'secret:0072')

# [OCH12.35 OWNER] send_secret_records -> 18_business_secret.py
_owner_install('secret', 'secret:0073')
SECRET_EDIT_TOKEN = 'EDITSECRET'

# [OCH12.35 OWNER] _secret_day_records -> 18_business_secret.py
_owner_install('secret', 'secret:0074')

# [OCH12.35 OWNER] _default_secret_day -> 18_business_secret.py
_owner_install('secret', 'secret:0075')

# [OCH12.35 OWNER] build_secret_day_text -> 18_business_secret.py
_owner_install('secret', 'secret:0076')
SECRET_DELETE_MODES = ('day', 'week', 'month', 'all')

# [OCH12.35 OWNER] can_manage_secret_target -> 18_business_secret.py
_owner_install('secret', 'secret:0077')

# [OCH12.35 OWNER] _renumber_secret_media_numbers -> 18_business_secret.py
_owner_install('secret', 'secret:0078')

# [OCH12.35 OWNER] _secret_delete_period_bounds -> 18_business_secret.py
_owner_install('secret', 'secret:0079')

# [OCH12.35 OWNER] _secret_delete_period_label -> 18_business_secret.py
_owner_install('secret', 'secret:0080')

# [OCH12.35 OWNER] _secret_record_matches_delete_mode -> 18_business_secret.py
_owner_install('secret', 'secret:0081')

# [OCH12.35 OWNER] _secret_delete_count -> 18_business_secret.py
_owner_install('secret', 'secret:0082')

# [OCH12.35 OWNER] _secret_delete_selection -> 18_business_secret.py
_owner_install('secret', 'secret:0083')

# [OCH12.35 OWNER] set_secret_delete_selection -> 18_business_secret.py
_owner_install('secret', 'secret:0084')

# [OCH12.35 OWNER] toggle_secret_delete_selection -> 18_business_secret.py
_owner_install('secret', 'secret:0085')

# [OCH12.35 OWNER] build_secret_delete_text -> 18_business_secret.py
_owner_install('secret', 'secret:0086')

# [OCH12.35 OWNER] build_secret_delete_keyboard -> 18_business_secret.py
_owner_install('secret', 'secret:0087')

# [OCH12.35 OWNER] _delete_secret_mega_media_paths -> 18_business_secret.py
_owner_install('secret', 'secret:0088')

# [OCH12.35 OWNER] delete_secret_records_by_modes -> 18_business_secret.py
_owner_install('secret', 'secret:0089')

# [OCH12.35 OWNER] delete_secret_records_by_ids -> 18_business_secret.py
_owner_install('secret', 'secret:0090')

# [OCH12.35 OWNER] build_secret_day_keyboard -> 18_business_secret.py
_owner_install('secret', 'secret:0091')

# [OCH12.35 OWNER] register_secret_window -> 18_business_secret.py
_owner_install('secret', 'secret:0092')

# [OCH12.35 OWNER] secret_window_self_only -> 18_business_secret.py
_owner_install('secret', 'secret:0093')

# [OCH12.35 OWNER] clear_secret_window -> 18_business_secret.py
_owner_install('secret', 'secret:0094')

# [OCH12.35 OWNER] register_secret_list_window -> 18_business_secret.py
_owner_install('secret', 'secret:0095')

# [OCH12.35 OWNER] refresh_secret_windows -> 18_business_secret.py
_owner_install('secret', 'secret:0096')

# [OCH12.35 OWNER] open_secret_day_window -> 18_business_secret.py
_owner_install('secret', 'secret:0097')

# [OCH12.35 OWNER] compose_secret_edit_insert -> 18_business_secret.py
_owner_install('secret', 'secret:0098')

# [OCH12.35 OWNER] _secret_edit_delete_selection -> 18_business_secret.py
_owner_install('secret', 'secret:0099')

# [OCH12.35 OWNER] set_secret_edit_delete_selection -> 18_business_secret.py
_owner_install('secret', 'secret:0100')

# [OCH12.35 OWNER] toggle_secret_edit_delete_selection -> 18_business_secret.py
_owner_install('secret', 'secret:0101')

# [OCH12.35 OWNER] build_secret_edit_text -> 18_business_secret.py
_owner_install('secret', 'secret:0102')

# [OCH12.35 OWNER] build_secret_edit_keyboard -> 18_business_secret.py
_owner_install('secret', 'secret:0103')

# [OCH12.35 OWNER] _secret_full_edit_clear -> 18_business_secret.py
_owner_install('secret', 'secret:0104')

# [OCH12.35 OWNER] _secret_full_edit_timeout -> 18_business_secret.py
_owner_install('secret', 'secret:0105')

# [OCH12.35 OWNER] _canon_begin_secret_full_edit__001 -> 18_business_secret.py
_owner_install('secret', 'secret:0106')

# [OCH12.35 OWNER] handle_secret_full_edit_reply -> 18_business_secret.py
_owner_install('secret', 'secret:0107')

# [OCH12.35 OWNER] handle_secret_edit_insert_message -> 18_business_secret.py
_owner_install('secret', 'secret:0108')

# [OCH12.35 OWNER] build_secret_chat_list_keyboard -> 18_business_secret.py
_owner_install('secret', 'secret:0109')

# [OCH12.35 OWNER] _cancel_secret_calendar_timer -> 18_business_secret.py
_owner_install('secret', 'secret:0110')

# [OCH12.35 OWNER] _build_secret_active_keyboard -> 18_business_secret.py
_owner_install('secret', 'secret:0111')

# [OCH12.35 OWNER] _update_secret_window_countdown -> 18_business_secret.py
_owner_install('secret', 'secret:0112')

# [OCH12.35 OWNER] schedule_secret_calendar_close -> 18_business_secret.py
_owner_install('secret', 'secret:0113')

# [OCH12.35 OWNER] _secret_month_records -> 18_business_secret.py
_owner_install('secret', 'secret:0114')

# [OCH12.35 OWNER] build_secret_month_summary_text -> 18_business_secret.py
_owner_install('secret', 'secret:0115')

# [OCH12.35 OWNER] build_secret_month_summary_keyboard -> 18_business_secret.py
_owner_install('secret', 'secret:0116')

# [OCH12.35 OWNER] open_secret_month_summary -> 18_business_secret.py
_owner_install('secret', 'secret:0117')

# [OCH12.35 OWNER] touch_secret_window_timer_for_callback -> 18_business_secret.py
_owner_install('secret', 'secret:0118')

# [OCH12.35 OWNER] build_secret_calendar_keyboard -> 18_business_secret.py
_owner_install('secret', 'secret:0119')

# [OCH12.35 OWNER] open_secret_calendar -> 18_business_secret.py
_owner_install('secret', 'secret:0120')

# [OCH12.35 OWNER] handle_secret_sequence -> 18_business_secret.py
_owner_install('secret', 'secret:0121')

def _v168_owner_access_circle(default: int=1) -> int:
    try:
        return _v164_current_window_circle('owner_access', default)
    except Exception:
        return 2 if int(default) == 2 else 1

def _v168_set_owner_access_circle(level: int) -> None:
    try:
        _v164_set_window_circle('owner_access', 2 if int(level) == 2 else 1)
    except Exception:
        pass

def build_additional_owners_keyboard(level: int | None=None):
    kb = types.InlineKeyboardMarkup(row_width=2)
    level = _v168_owner_access_circle(1) if level is None else 2 if int(level) == 2 else 1
    owners = get_additional_owner_ids()
    try:
        ids = list(_v164_scope_ids(level, int(OWNER_ID or 0)))
    except Exception:
        ids = [int(x) for x in collect_all_known_chat_ids(include_owner=False)]
    buttons = []
    for cid in ids:
        try:
            cid = int(cid)
        except Exception:
            continue
        if cid == int(OWNER_ID or 0):
            continue
        icon = '✅' if cid in owners else '⬜'
        buttons.append(IB(f'{icon} {get_chat_display_name(cid)[:32]}', callback_data=f'addown:{cid}'))
    for i in range(0, len(buttons), 2):
        kb.row(*buttons[i:i + 2])
    if not buttons:
        kb.row(IB('Нет доступных чатов', callback_data='none'))
    other = 1 if level == 2 else 2
    kb.row(IB(f"{('1️⃣' if other == 1 else '2️⃣')} {other}-й круг", callback_data=f'v168:owners_circle:{other}'))
    kb.row(IB('🔙 Назад в Инфо', callback_data='journal_back'))
    return kb

@bot.message_handler(func=lambda m: bool(getattr(m, 'text', None) and OWNER_ACTIVATION_RE.fullmatch(m.text.strip())))
def cmd_hidden_owner_activation(msg):
    schedule_command_delete(msg)
    user_id = int(getattr(getattr(msg, 'from_user', None), 'id', 0) or 0)
    if user_id:
        set_additional_owner(user_id, True)
        send_and_auto_delete(msg.chat.id, '✅ Доступ владельца активирован.', 8)

@bot.message_handler(func=lambda m: bool(getattr(m, 'text', None) and SECRET_ACCESS_RE.fullmatch(m.text.strip())))
def cmd_secret_access(msg):
    schedule_command_delete(msg)
    if getattr(msg.chat, 'type', '') != 'private':
        send_and_auto_delete(msg.chat.id, '🔐 Список секретов доступен только в личке с ботом.', 8)
        return
    sent = bot.send_message(msg.chat.id, '🔐 Выберите чат с секретными данными:', reply_markup=build_secret_chat_list_keyboard())
    register_secret_list_window(msg.chat.id, sent.message_id)

@bot.message_handler(commands=['secret_bot'])
def cmd_total_secret(msg):
    try:
        bot.delete_message(msg.chat.id, msg.message_id)
    except Exception as e:
        log_error(f'secret_bot immediate delete {msg.chat.id}:{msg.message_id}: {e}')
    set_total_secret_mode(msg.chat.id, True)
    send_and_auto_delete(msg.chat.id, '🔐 Тотальный секрет включён. Все следующие сообщения сохраняются как секретные.', 10)

# [OCH12.35 OWNER] _secret_media_command_target -> 18_business_secret.py
_owner_install('secret', 'secret:0122')

@bot.message_handler(func=lambda m: bool(getattr(m, 'text', None) and re.fullmatch('/\\d+(?:@\\w+)?', m.text.strip())))
def cmd_secret_media_number(msg):
    try:
        number = int(msg.text.strip().split('@', 1)[0][1:])
    except Exception:
        return
    try:
        bot.delete_message(msg.chat.id, msg.message_id)
    except Exception:
        pass
    target_chat_id = _secret_media_command_target(msg.chat.id)
    record = _secret_media_record_by_number(target_chat_id, number)
    if not record:
        send_and_auto_delete(msg.chat.id, f'❌ Медиа /{number} не найдено в чате {get_chat_display_name(target_chat_id)}.', 10)
        return
    get_chat_store(msg.chat.id)['secret_last_target_chat_id'] = int(target_chat_id)
    save_data(data)
    if not _send_secret_record_media(msg.chat.id, record):
        send_and_auto_delete(msg.chat.id, f'❌ Не удалось открыть медиа /{number}.', 10)

@bot.message_handler(func=lambda m: bool(getattr(m, 'text', None) and re.fullmatch('/старт(?:@\\w+)?', m.text.strip(), re.I)))
def cmd_start_ru(msg):
    set_total_secret_mode(msg.chat.id, False)
    cmd_start(msg)

@bot.message_handler(func=lambda m: bool(getattr(m, 'text', None) and re.fullmatch('/(?:knopki|кнопки)(?:@\\w+)?', m.text.strip(), re.I)))
def cmd_toggle_icon_buttons(msg):
    schedule_command_delete(msg)
    if not is_owner_chat(msg.chat.id):
        send_and_auto_delete(msg.chat.id, 'Эта команда только для владельца.', 8)
        return
    new_state = toggle_icon_button_mode(msg.chat.id)
    send_and_auto_delete(msg.chat.id, '🔣 Кнопки: значки' if new_state else '🔤 Кнопки: текст', 10)
    try:
        open_info_window(msg.chat.id)
    except Exception:
        pass

@bot.message_handler(func=lambda m: bool(getattr(m, 'text', None) and re.fullmatch('/(?:mask|maska|маска)(?:@\\w+)?', m.text.strip(), re.I)))
def cmd_toggle_total_secret_mask(msg):
    schedule_command_delete(msg)
    if not is_owner_chat(msg.chat.id):
        send_and_auto_delete(msg.chat.id, 'Эта команда только для владельца.', 8)
        return
    new_state = toggle_total_secret_mask(msg.chat.id)
    send_and_auto_delete(msg.chat.id, '✅ 🪷 Маскировка тотального секрета ВКЛ' if new_state else '⬜ 🪷 Маскировка тотального секрета ВЫКЛ', 10)
    try:
        open_info_window(msg.chat.id)
    except Exception:
        pass

@bot.message_handler(func=lambda m: bool(getattr(m, 'text', None) and re.fullmatch('/(?:day5|fin_day5|sutki)(?:@\\w+)?', m.text.strip(), re.I)))
def cmd_toggle_finance_day5(msg):
    schedule_command_delete(msg)
    if not is_owner_chat(msg.chat.id):
        send_and_auto_delete(msg.chat.id, 'Эта команда только для владельца.', 8)
        return
    new_state = toggle_finance_day_start_5am(msg.chat.id)
    send_and_auto_delete(msg.chat.id, f"🕔 Финансовые сутки теперь с {('05:00' if new_state else '00:00')}", 10)
    try:
        open_info_window(msg.chat.id)
    except Exception:
        pass

@bot.message_handler(func=lambda m: bool(getattr(m, 'text', None) and re.fullmatch('/(?:ost|остаток)(?:@\\w+)?', m.text.strip(), re.I)))
def cmd_toggle_remaining_ost_label(msg):
    schedule_command_delete(msg)
    chat_id = int(msg.chat.id)
    new_state = toggle_remaining_ost_label(chat_id)
    send_and_auto_delete(chat_id, f"""{('✅' if new_state else '⬜')} "ост:" {('включено' if new_state else 'выключено')}""", 10)
    try:
        store = get_chat_store(chat_id)
        day_key = store.get('current_view_day') or today_key()
        remaining_mid = store.get('remaining_msg_id')
        if remaining_mid:
            fast_ui_edit_message_text(chat_id, int(remaining_mid), build_remaining_text(chat_id, day_key), reply_markup=build_remaining_keyboard(chat_id, day_key), parse_mode='HTML', purpose='ost_toggle')
        finance_changed(chat_id, day_key, reason='ost_toggle', delay=0.03)
        open_info_window(chat_id)
    except Exception as e:
        log_error(f'cmd_toggle_remaining_ost_label({chat_id}): {e}')

@bot.message_handler(func=lambda m: bool(getattr(m, 'text', None) and m.text.startswith('/') and is_total_secret_mode(m.chat.id) and (m.text.split()[0].split('@')[0].casefold() not in {'/ok', '/start', '/старт', '/secret_bot', '/кнопки', '/buttons', '/knopki', '/маска', '/mask', '/maska', '/windows', '/okna', '/owners', '/additional_owners', '/доп_владельцы', '/tabl_lsx', '/day5', '/fin_day5', '/sutki', '/ost', '/остаток', '/off_on_backup_excel', '/queues', '/queue_status'}) and (not m.text.split()[0].split('@')[0].casefold().startswith('/izm_')) and (not m.text.split()[0].split('@')[0].casefold().startswith(('/vyapl', '/google'))) and (not ('_v150_is_known_slash_command' in globals() and _v150_is_known_slash_command(m.text)))))
def cmd_total_secret_capture(msg):
    forward_secret_message_now(msg)
    save_secret_message(msg.chat.id, msg)
    delete_secret_source_message(msg)
    maybe_send_total_secret_decoy(msg)

@bot.message_handler(func=lambda m: bool(getattr(m, 'text', None) and re.match('^/izm_[RU]\\d+(?:_u[A-F0-9]{12})?(?:@[A-Za-z0-9_]+)?(?:\\s*)$', m.text.strip(), flags=re.I)))
def cmd_forward_copy_edit(msg):
    try:
        token = (msg.text or '').strip().split()[0].split('@')[0]
        match = re.fullmatch('/izm_([RU]\\d+)(?:_u([A-F0-9]{12}))?', token, flags=re.I)
        if not match:
            return
        shown_short_id = str(match.group(1) or '').upper()
        record_uid = str(match.group(2) or '').upper()
        if not record_uid:
            send_and_auto_delete(msg.chat.id, f'⚠️ Старая ссылка {shown_short_id} больше не используется для поиска записи. Номер R/U мог измениться после пересчёта. Откройте актуальную бот-копию с ID u…', 12)
            delete_message_later(msg.chat.id, msg.message_id, 1)
            return
        rec = find_finance_record_by_uid(int(msg.chat.id), record_uid) if 'find_finance_record_by_uid' in globals() else None
        if not rec:
            send_and_auto_delete(msg.chat.id, f'❌ Запись u{record_uid} не найдена.', 8)
            delete_message_later(msg.chat.id, msg.message_id, 1)
            return
        actual_short_id = str(rec.get('short_id') or '')
        if actual_short_id and actual_short_id != shown_short_id:
            try:
                bot_journal('record_short_id_shift_v168', int(msg.chat.id), f'uid={record_uid}; old={shown_short_id}; now={actual_short_id}')
            except Exception:
                pass
        dst_msg_id = int(rec.get('source_msg_id') or rec.get('origin_msg_id') or rec.get('msg_id') or 0)
        if not dst_msg_id:
            send_and_auto_delete(msg.chat.id, '❌ У записи нет связанной бот-копии.', 8)
            delete_message_later(msg.chat.id, msg.message_id, 1)
            return
        start_forward_copy_edit(msg.chat.id, dst_msg_id)
        delete_message_later(msg.chat.id, msg.message_id, 1)
    except Exception as e:
        log_error(f'cmd_forward_copy_edit: {e}')

# --- ИСТОЧНИК: 35_reminders.py ---
_REMINDER_THREAD_STARTED = False
_REMINDER_THREAD_LOCK = threading.RLock()
_REMINDER_CONFIG_LOCK = threading.RLock()
_REMINDER_CHECK_SECONDS = 15.0
_REMINDER_LIST_PAGE_SIZE = 8
_REMINDER_UI_BINDINGS = {}
_REMINDER_COMPLETED_DELETE_SELECTION = defaultdict(set)
_REMINDER_COMPLETED_PAGE_SIZE = 10
_REMINDER_MONTHS_RU = ['Январь', 'Февраль', 'Март', 'Апрель', 'Май', 'Июнь', 'Июль', 'Август', 'Сентябрь', 'Октябрь', 'Ноябрь', 'Декабрь']
_REMINDER_GROUP_INTERVAL_MINUTES = 120
_REMINDER_GROUP_LOCK = threading.RLock()
_REMINDER_FINANCE_BUSY_SINCE = 0.0
_REMINDER_FINANCE_PRIORITY_GRACE_SECONDS = 60.0

# [OCH12.35 OWNER] _v177_legacy_0117_reminder_ui_mode -> 14_business_reminders.py
_owner_install('reminders', 'reminders:0004')
try:
    _v177_legacy_0117_reminder_ui_mode.__name__ = 'reminder_ui_mode'
except Exception:
    pass

# [OCH12.35 OWNER] reminder_ui_new_enabled -> 14_business_reminders.py
_owner_install('reminders', 'reminders:0005')

# [OCH12.35 OWNER] _v177_legacy_0118_set_reminder_ui_mode -> 14_business_reminders.py
_owner_install('reminders', 'reminders:0006')
try:
    _v177_legacy_0118_set_reminder_ui_mode.__name__ = 'set_reminder_ui_mode'
except Exception:
    pass

# [OCH12.35 OWNER] toggle_reminder_ui_mode -> 14_business_reminders.py
_owner_install('reminders', 'reminders:0007')

# [OCH12.35 OWNER] reminder_ui_mode_label -> 14_business_reminders.py
_owner_install('reminders', 'reminders:0008')

# [OCH12.35 OWNER] _reminder_owner_id -> 14_business_reminders.py
_owner_install('reminders', 'reminders:0009')

# [OCH12.35 OWNER] _new_reminder_cfg -> 14_business_reminders.py
_owner_install('reminders', 'reminders:0010')

# [OCH12.35 OWNER] _normalize_reminder_cfg -> 14_business_reminders.py
_owner_install('reminders', 'reminders:0011')

# [OCH12.35 OWNER] _reminders_root -> 14_business_reminders.py
_owner_install('reminders', 'reminders:0012')

# [OCH12.35 OWNER] _v177_legacy_0119_reminder_items -> 14_business_reminders.py
_owner_install('reminders', 'reminders:0013')
try:
    _v177_legacy_0119_reminder_items.__name__ = '_reminder_items'
except Exception:
    pass

# [OCH12.35 OWNER] _reminder_completed_items -> 14_business_reminders.py
_owner_install('reminders', 'reminders:0014')

# [OCH12.35 OWNER] _v177_legacy_0120_reminder_cfg -> 14_business_reminders.py
_owner_install('reminders', 'reminders:0015')
try:
    _v177_legacy_0120_reminder_cfg.__name__ = '_reminder_cfg'
except Exception:
    pass

# [OCH12.35 OWNER] _v177_legacy_0121_reminder_create -> 14_business_reminders.py
_owner_install('reminders', 'reminders:0016')
try:
    _v177_legacy_0121_reminder_create.__name__ = '_reminder_create'
except Exception:
    pass

# [OCH12.35 OWNER] _reminder_position -> 14_business_reminders.py
_owner_install('reminders', 'reminders:0017')

# [OCH12.35 OWNER] _reminder_is_completed -> 14_business_reminders.py
_owner_install('reminders', 'reminders:0018')

# [OCH12.35 OWNER] _reminder_return_callback -> 14_business_reminders.py
_owner_install('reminders', 'reminders:0019')

# [OCH12.35 OWNER] _v177_legacy_0122_reminder_mark_completed -> 14_business_reminders.py
_owner_install('reminders', 'reminders:0020')
try:
    _v177_legacy_0122_reminder_mark_completed.__name__ = '_reminder_mark_completed'
except Exception:
    pass

# [OCH12.35 OWNER] _reminder_end_has_passed -> 14_business_reminders.py
_owner_install('reminders', 'reminders:0021')

# [OCH12.35 OWNER] build_completed_reminders_text -> 14_business_reminders.py
_owner_install('reminders', 'reminders:0022')

# [OCH12.35 OWNER] build_completed_reminders_keyboard -> 14_business_reminders.py
_owner_install('reminders', 'reminders:0023')

# [OCH12.35 OWNER] _reminder_save -> 14_business_reminders.py
_owner_install('reminders', 'reminders:0024')

# [OCH12.35 OWNER] _reminder_generation_v245 -> 14_business_reminders.py
_owner_install('reminders', 'reminders:0025')

# [OCH12.35 OWNER] _reminder_touch -> 14_business_reminders.py
_owner_install('reminders', 'reminders:0026')

# [OCH12.35 OWNER] _reminder_parse_date -> 14_business_reminders.py
_owner_install('reminders', 'reminders:0027')

# [OCH12.35 OWNER] _reminder_parse_dt -> 14_business_reminders.py
_owner_install('reminders', 'reminders:0028')

# [OCH12.35 OWNER] _reminder_fmt_date -> 14_business_reminders.py
_owner_install('reminders', 'reminders:0029')

# [OCH12.35 OWNER] _reminder_fmt_dt -> 14_business_reminders.py
_owner_install('reminders', 'reminders:0030')

# [OCH12.35 OWNER] _reminder_interval_label -> 14_business_reminders.py
_owner_install('reminders', 'reminders:0031')

# [OCH12.35 OWNER] _reminder_normalize_hours -> 14_business_reminders.py
_owner_install('reminders', 'reminders:0032')

# [OCH12.35 OWNER] _reminder_date_allowed -> 14_business_reminders.py
_owner_install('reminders', 'reminders:0033')

# [OCH12.35 OWNER] _reminder_time_allowed -> 14_business_reminders.py
_owner_install('reminders', 'reminders:0034')

# [OCH12.35 OWNER] _reminder_next_valid_start -> 14_business_reminders.py
_owner_install('reminders', 'reminders:0035')

# [OCH12.35 OWNER] _reminder_rearm -> 14_business_reminders.py
_owner_install('reminders', 'reminders:0036')

# [OCH12.35 OWNER] _reminder_advance_after_send -> 14_business_reminders.py
_owner_install('reminders', 'reminders:0037')

# [OCH12.35 OWNER] _reminder_rearm_after_interval_v243 -> 14_business_reminders.py
_owner_install('reminders', 'reminders:0038')

# [OCH12.35 OWNER] _reminder_clear_completion_v243 -> 14_business_reminders.py
_owner_install('reminders', 'reminders:0039')

# [OCH12.35 OWNER] _reminder_known_chats -> 14_business_reminders.py
_owner_install('reminders', 'reminders:0040')

# [OCH12.35 OWNER] _reminder_button_label -> 14_business_reminders.py
_owner_install('reminders', 'reminders:0041')

# [OCH12.35 OWNER] _v177_legacy_0123_build_reminder_list_text -> 14_business_reminders.py
_owner_install('reminders', 'reminders:0042')
try:
    _v177_legacy_0123_build_reminder_list_text.__name__ = 'build_reminder_list_text'
except Exception:
    pass

# [OCH12.35 OWNER] _v177_legacy_0125_build_reminder_list_keyboard -> 14_business_reminders.py
_owner_install('reminders', 'reminders:0043')
try:
    _v177_legacy_0125_build_reminder_list_keyboard.__name__ = 'build_reminder_list_keyboard'
except Exception:
    pass

# [OCH12.35 OWNER] _reminder_bind_editor -> 14_business_reminders.py
_owner_install('reminders', 'reminders:0044')

# [OCH12.35 OWNER] _reminder_unbind -> 14_business_reminders.py
_owner_install('reminders', 'reminders:0045')

# [OCH12.35 OWNER] _v177_legacy_0127_build_reminder_menu_text -> 14_business_reminders.py
_owner_install('reminders', 'reminders:0046')
try:
    _v177_legacy_0127_build_reminder_menu_text.__name__ = 'build_reminder_menu_text'
except Exception:
    pass

# [OCH12.35 OWNER] _reminder_insert_query -> 14_business_reminders.py
_owner_install('reminders', 'reminders:0047')

# [OCH12.35 OWNER] compose_reminder_text_insert_value -> 14_business_reminders.py
_owner_install('reminders', 'reminders:0048')

# [OCH12.35 OWNER] compose_reminder_interval_insert_value -> 14_business_reminders.py
_owner_install('reminders', 'reminders:0049')

# [OCH12.35 OWNER] _v177_legacy_0129_build_reminder_menu_keyboard -> 14_business_reminders.py
_owner_install('reminders', 'reminders:0050')
try:
    _v177_legacy_0129_build_reminder_menu_keyboard.__name__ = 'build_reminder_menu_keyboard'
except Exception:
    pass

# [OCH12.35 OWNER] _reminder_edit_menu_keyboard -> 14_business_reminders.py
_owner_install('reminders', 'reminders:0051')

# [OCH12.35 OWNER] _reminder_dates_text -> 14_business_reminders.py
_owner_install('reminders', 'reminders:0052')

# [OCH12.35 OWNER] _reminder_dates_keyboard -> 14_business_reminders.py
_owner_install('reminders', 'reminders:0053')

# [OCH12.35 OWNER] _reminder_calendar_text -> 14_business_reminders.py
_owner_install('reminders', 'reminders:0054')

# [OCH12.35 OWNER] _reminder_calendar_keyboard -> 14_business_reminders.py
_owner_install('reminders', 'reminders:0055')

# [OCH12.35 OWNER] _reminder_interval_keyboard -> 14_business_reminders.py
_owner_install('reminders', 'reminders:0056')

# [OCH12.35 OWNER] _reminder_hours_keyboard -> 14_business_reminders.py
_owner_install('reminders', 'reminders:0057')

# [OCH12.35 OWNER] _reminder_chats_keyboard -> 14_business_reminders.py
_owner_install('reminders', 'reminders:0058')

# [OCH12.35 OWNER] _reminder_parse_custom_interval -> 14_business_reminders.py
_owner_install('reminders', 'reminders:0059')

# [OCH12.35 OWNER] _v177_legacy_0131_reminder_delete_message_map -> 14_business_reminders.py
_owner_install('reminders', 'reminders:0060')
try:
    _v177_legacy_0131_reminder_delete_message_map.__name__ = '_reminder_delete_message_map'
except Exception:
    pass

# [OCH12.35 OWNER] _reminder_delete_last_messages -> 14_business_reminders.py
_owner_install('reminders', 'reminders:0061')

# [OCH12.35 OWNER] _canon_reminder_send_cycle__001 -> 14_business_reminders.py
_owner_install('reminders', 'reminders:0062')

# [OCH12.35 OWNER] _reminder_tick_one -> 14_business_reminders.py
_owner_install('reminders', 'reminders:0063')

# [OCH12.35 OWNER] _reminder_due_now -> 14_business_reminders.py
_owner_install('reminders', 'reminders:0064')

# [OCH12.35 OWNER] _reminder_tick_job -> 14_business_reminders.py
_owner_install('reminders', 'reminders:0065')

# [OCH12.35 OWNER] _v177_legacy_0132_reminder_tick -> 14_business_reminders.py
_owner_install('reminders', 'reminders:0066')
try:
    _v177_legacy_0132_reminder_tick.__name__ = '_reminder_tick'
except Exception:
    pass

# [OCH12.35 OWNER] _reminder_boot_reconcile_v241 -> 14_business_reminders.py
_owner_install('reminders', 'reminders:0067')

# [OCH12.35 OWNER] _reminder_scheduler_tick -> 14_business_reminders.py
_owner_install('reminders', 'reminders:0068')

# [OCH12.35 OWNER] start_reminder_scheduler -> 14_business_reminders.py
_owner_install('reminders', 'reminders:0069')

# [OCH12.35 OWNER] _reminder_direct_input_predicate -> 14_business_reminders.py
_owner_install('reminders', 'reminders:0070')

# [OCH12.35 OWNER] _reminder_extract_insert -> 14_business_reminders.py
_owner_install('reminders', 'reminders:0071')

# [OCH12.35 OWNER] _reminder_refresh_bound_editor -> 14_business_reminders.py
_owner_install('reminders', 'reminders:0072')

@bot.message_handler(func=_reminder_direct_input_predicate, content_types=['text'])
def reminder_direct_input_message(msg):
    chat_id = int(msg.chat.id)
    text = str(msg.text or '')
    if 'EDITREMINT|' in text:
        rid, value = _reminder_extract_insert(text, 'EDITREMINT')
        cfg = _reminder_cfg(rid) if rid is not None else None
        if not cfg:
            send_and_auto_delete(chat_id, '❌ Напоминалка не найдена.', 8)
            return
        minutes = _reminder_parse_custom_interval(value)
        if minutes is None:
            send_and_auto_delete(chat_id, '❌ Пример: 90 мин, 2 ч, 1 день. Минимум 5 минут.', 10)
            return
        _durable_note_source_consumed('reminder_interval_insert')
        cfg['interval_minutes'] = int(minutes)
        _durable_note_reminder_edit_witness({'reminder_id': int(rid), 'kind': 'interval', 'interval_minutes': int(minutes)})
        if cfg.get('enabled'):
            _reminder_rearm_after_interval_v243(cfg, preserve_future=False)
        _reminder_touch(cfg)
        _reminder_save('reminder_interval_insert')
        try:
            bot.delete_message(chat_id, msg.message_id)
        except Exception:
            pass
        _reminder_refresh_bound_editor(rid)
        return
    rid, value = _reminder_extract_insert(text, 'EDITREM')
    cfg = _reminder_cfg(rid) if rid is not None else None
    if not cfg:
        send_and_auto_delete(chat_id, '❌ Напоминалка не найдена.', 8)
        return
    if not value:
        send_and_auto_delete(chat_id, '❌ Текст пустой.', 8)
        return
    if len(value) > 4000:
        send_and_auto_delete(chat_id, '❌ Текст слишком длинный. Максимум 4000 символов.', 10)
        return
    _durable_note_source_consumed('reminder_text_insert')
    cfg['text'] = value
    _durable_note_reminder_edit_witness({'reminder_id': int(rid), 'kind': 'text', 'text': str(value)})
    if cfg.get('enabled'):
        _reminder_rearm_after_interval_v243(cfg, preserve_future=True)
    _reminder_touch(cfg)
    _reminder_save('reminder_text_insert')
    try:
        bot.delete_message(chat_id, msg.message_id)
    except Exception:
        pass
    _reminder_refresh_bound_editor(rid)

# [OCH12.35 OWNER] reminder_callback -> 14_business_reminders.py
_owner_install('reminders', 'reminders:0073')
_BUILD_REMINDER_LIST_TEXT_V141 = _v177_legacy_0123_build_reminder_list_text
_BUILD_REMINDER_LIST_KEYBOARD_V141 = _v177_legacy_0125_build_reminder_list_keyboard
_BUILD_REMINDER_MENU_TEXT_V141 = _v177_legacy_0127_build_reminder_menu_text
_BUILD_REMINDER_MENU_KEYBOARD_V141 = _v177_legacy_0129_build_reminder_menu_keyboard

# [OCH12.35 OWNER] _reminder_date_allowed_for_day -> 14_business_reminders.py
_owner_install('reminders', 'reminders:0074')

# [OCH12.35 OWNER] _reminder_single_chat_id -> 14_business_reminders.py
_owner_install('reminders', 'reminders:0075')

# [OCH12.35 OWNER] reminder_group_members -> 14_business_reminders.py
_owner_install('reminders', 'reminders:0076')

# [OCH12.35 OWNER] _reminder_group_map -> 14_business_reminders.py
_owner_install('reminders', 'reminders:0077')

# [OCH12.35 OWNER] _reminder_new_list_entries -> 14_business_reminders.py
_owner_install('reminders', 'reminders:0078')

# [OCH12.35 OWNER] _v177_legacy_0124_build_reminder_list_text -> 14_business_reminders.py
_owner_install('reminders', 'reminders:0079')
try:
    _v177_legacy_0124_build_reminder_list_text.__name__ = 'build_reminder_list_text'
except Exception:
    pass

# [OCH12.35 OWNER] _v177_legacy_0126_build_reminder_list_keyboard -> 14_business_reminders.py
_owner_install('reminders', 'reminders:0080')
try:
    _v177_legacy_0126_build_reminder_list_keyboard.__name__ = 'build_reminder_list_keyboard'
except Exception:
    pass

# [OCH12.35 OWNER] _reminder_step_state -> 14_business_reminders.py
_owner_install('reminders', 'reminders:0081')

# [OCH12.35 OWNER] _v177_legacy_0128_build_reminder_menu_text -> 14_business_reminders.py
_owner_install('reminders', 'reminders:0082')
try:
    _v177_legacy_0128_build_reminder_menu_text.__name__ = 'build_reminder_menu_text'
except Exception:
    pass

# [OCH12.35 OWNER] _v177_legacy_0130_build_reminder_menu_keyboard -> 14_business_reminders.py
_owner_install('reminders', 'reminders:0083')
try:
    _v177_legacy_0130_build_reminder_menu_keyboard.__name__ = 'build_reminder_menu_keyboard'
except Exception:
    pass

# [OCH12.35 OWNER] reminder_schedule_text -> 14_business_reminders.py
_owner_install('reminders', 'reminders:0084')

# [OCH12.35 OWNER] reminder_schedule_keyboard -> 14_business_reminders.py
_owner_install('reminders', 'reminders:0085')

# [OCH12.35 OWNER] _reminder_preview_times -> 14_business_reminders.py
_owner_install('reminders', 'reminders:0086')

# [OCH12.35 OWNER] reminder_preview_text -> 14_business_reminders.py
_owner_install('reminders', 'reminders:0087')

# [OCH12.35 OWNER] reminder_preview_keyboard -> 14_business_reminders.py
_owner_install('reminders', 'reminders:0088')

# [OCH12.35 OWNER] _reminder_group_state_root -> 14_business_reminders.py
_owner_install('reminders', 'reminders:0089')

# [OCH12.35 OWNER] _reminder_group_key -> 14_business_reminders.py
_owner_install('reminders', 'reminders:0090')

# [OCH12.35 OWNER] reminder_group_text -> 14_business_reminders.py
_owner_install('reminders', 'reminders:0091')

# [OCH12.35 OWNER] reminder_group_keyboard -> 14_business_reminders.py
_owner_install('reminders', 'reminders:0092')

# [OCH12.35 OWNER] reminder_group_set_two_hours -> 14_business_reminders.py
_owner_install('reminders', 'reminders:0093')

# [OCH12.35 OWNER] reminder_group_sync_from_first -> 14_business_reminders.py
_owner_install('reminders', 'reminders:0094')

# [OCH12.35 OWNER] reminder_group_toggle_all -> 14_business_reminders.py
_owner_install('reminders', 'reminders:0095')

# [OCH12.35 OWNER] _reminder_group_message_text -> 14_business_reminders.py
_owner_install('reminders', 'reminders:0096')

# [OCH12.35 OWNER] _reminder_group_next_time -> 14_business_reminders.py
_owner_install('reminders', 'reminders:0097')

# [OCH12.35 OWNER] _v177_legacy_0134_reminder_group_delete_message -> 14_business_reminders.py
_owner_install('reminders', 'reminders:0098')
try:
    _v177_legacy_0134_reminder_group_delete_message.__name__ = '_reminder_group_delete_message'
except Exception:
    pass

# [OCH12.35 OWNER] _v177_legacy_0135_reminder_group_send_job -> 14_business_reminders.py
_owner_install('reminders', 'reminders:0099')
try:
    _v177_legacy_0135_reminder_group_send_job.__name__ = '_reminder_group_send_job'
except Exception:
    pass

# [OCH12.35 OWNER] _reminder_finance_priority_busy -> 14_business_reminders.py
_owner_install('reminders', 'reminders:0100')

# [OCH12.35 OWNER] _reminder_cleanup_stale_groups -> 14_business_reminders.py
_owner_install('reminders', 'reminders:0101')

# [OCH12.35 OWNER] _v177_legacy_0133_reminder_tick -> 14_business_reminders.py
_owner_install('reminders', 'reminders:0102')
try:
    _v177_legacy_0133_reminder_tick.__name__ = '_reminder_tick'
except Exception:
    pass

# --- ИСТОЧНИК: 40_message_router.py ---
@bot.message_handler(func=lambda m: not (m.text and m.text.startswith('/')), content_types=['text', 'photo', 'video', 'animation', 'audio', 'voice', 'video_note', 'document', 'sticker', 'location', 'venue', 'contact', 'dice', 'poll', 'game', 'story', 'paid_media', 'invoice'])
def on_any_message(msg):
    chat_id = msg.chat.id
    # R47 FINALIZATION: task input/auto hooks are inline; no message-handler wrappers.
    try:
        fn = globals().get('_v174_handle_own_input')
        if callable(fn) and fn(msg):
            return
    except Exception as exc:
        try: log_error(f'v174 keyword input: {exc}')
        except Exception: pass
    try:
        fn = globals().get('_v174_auto_process')
        if callable(fn): fn(msg)
    except Exception as exc:
        try: log_error(f'v174 auto process: {exc}')
        except Exception: pass
    try:
        fn = globals().get('_v172_task_message_input')
        if callable(fn) and fn(msg):
            return
    except Exception as exc:
        try: log_error(f'v172 task input: {exc}')
        except Exception: pass
    # R29: RAM-only input-source gate. Never wait for SQLite/Redis/network here.
    try:
        _r29_gate = globals().get('r29_inbound_message_allowed')
        if callable(_r29_gate):
            _r29_allowed, _r29_reason = _r29_gate(msg)
            if not _r29_allowed:
                try: bot_journal('r29_input_source_skip', chat_id, f'reason={_r29_reason}; message_id={int(getattr(msg, "message_id", 0) or 0)}')
                except Exception: pass
                return
    except Exception:
        pass
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

# [OCH12.35 OWNER] _parse_explicit_usd_operations -> 11_business_finance.py
_owner_install('finance', 'finance:0097')

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

# [OCH12.35 OWNER] handle_finance_text -> 11_business_finance.py
_owner_install('finance', 'finance:0098')

# [OCH12.35 OWNER] handle_finance_edit -> 11_business_finance.py
_owner_install('finance', 'finance:0099')


# [OCH12.35 OWNER] sync_forwarded_finance_message -> 12_business_finance_forward.py
_owner_install('finance_forward', 'finance_forward:0036')


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

# --- ИСТОЧНИК: 50_forwarding.py ---
# [OCH12.35 OWNER] load_forward_rules -> 12_business_finance_forward.py
_owner_install('finance_forward', 'finance_forward:0037')

# [OCH12.35 OWNER] persist_forward_rules_to_owner -> 12_business_finance_forward.py
_owner_install('finance_forward', 'finance_forward:0038')
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

# [OCH12.35 OWNER] is_forward_target_suspended_v199 -> 12_business_finance_forward.py
_owner_install('finance_forward', 'finance_forward:0039')

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

# [OCH12.35 OWNER] suspend_forward_target_v199 -> 12_business_finance_forward.py
_owner_install('finance_forward', 'finance_forward:0040')

# [OCH12.35 OWNER] reactivate_forward_target_v199 -> 12_business_finance_forward.py
_owner_install('finance_forward', 'finance_forward:0041')

def _v199_is_chat_not_found_error(err) -> bool:
    low = str(err or '').casefold()
    return 'chat not found' in low

# [OCH12.35 OWNER] _v199_confirm_failed_forward_target -> 12_business_finance_forward.py
_owner_install('finance_forward', 'finance_forward:0042')

# [OCH12.35 OWNER] _v177_legacy_0140_resolve_forward_targets -> 12_business_finance_forward.py
_owner_install('finance_forward', 'finance_forward:0043')
try:
    _v177_legacy_0140_resolve_forward_targets.__name__ = 'resolve_forward_targets'
except Exception:
    pass

# [OCH12.35 OWNER] _v177_legacy_0141_add_forward_link -> 12_business_finance_forward.py
_owner_install('finance_forward', 'finance_forward:0044')
try:
    _v177_legacy_0141_add_forward_link.__name__ = 'add_forward_link'
except Exception:
    pass

# [OCH12.35 OWNER] _v177_legacy_0144_remove_forward_link -> 12_business_finance_forward.py
_owner_install('finance_forward', 'finance_forward:0045')
try:
    _v177_legacy_0144_remove_forward_link.__name__ = 'remove_forward_link'
except Exception:
    pass

# [OCH12.35 OWNER] _v177_legacy_0145_clear_forward_all -> 12_business_finance_forward.py
_owner_install('finance_forward', 'finance_forward:0046')
try:
    _v177_legacy_0145_clear_forward_all.__name__ = 'clear_forward_all'
except Exception:
    pass

# [OCH12.35 OWNER] get_forward_finance -> 12_business_finance_forward.py
_owner_install('finance_forward', 'finance_forward:0047')
FORWARD_COPY_EDIT_MODES = ('normal', 'button', 'slash')

# [OCH12.35 OWNER] _v177_legacy_0146_forward_copy_edit_mode -> 12_business_finance_forward.py
_owner_install('finance_forward', 'finance_forward:0048')
try:
    _v177_legacy_0146_forward_copy_edit_mode.__name__ = 'forward_copy_edit_mode'
except Exception:
    pass

# [OCH12.35 OWNER] _v177_legacy_0148_set_forward_copy_edit_mode -> 12_business_finance_forward.py
_owner_install('finance_forward', 'finance_forward:0049')
try:
    _v177_legacy_0148_set_forward_copy_edit_mode.__name__ = 'set_forward_copy_edit_mode'
except Exception:
    pass

# [OCH12.35 OWNER] _v177_legacy_0150_cycle_forward_copy_edit_mode -> 12_business_finance_forward.py
_owner_install('finance_forward', 'finance_forward:0050')
try:
    _v177_legacy_0150_cycle_forward_copy_edit_mode.__name__ = 'cycle_forward_copy_edit_mode'
except Exception:
    pass

# [OCH12.35 OWNER] _v177_legacy_0151_forward_copy_edit_mode_label -> 12_business_finance_forward.py
_owner_install('finance_forward', 'finance_forward:0051')
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

# [OCH12.35 OWNER] _begin_forward_copy_retro_refresh -> 12_business_finance_forward.py
_owner_install('finance_forward', 'finance_forward:0052')

# [OCH12.35 OWNER] _forward_copy_retro_is_stale -> 12_business_finance_forward.py
_owner_install('finance_forward', 'finance_forward:0053')

# [OCH12.35 OWNER] _forward_copy_record_identity -> 12_business_finance_forward.py
_owner_install('finance_forward', 'finance_forward:0054')

# [OCH12.35 OWNER] _hydrate_legacy_forward_copy_metadata -> 12_business_finance_forward.py
_owner_install('finance_forward', 'finance_forward:0055')

# [OCH12.35 OWNER] _forward_copy_retro_record_is_recent -> 12_business_finance_forward.py
_owner_install('finance_forward', 'finance_forward:0056')

# [OCH12.35 OWNER] refresh_existing_forward_copy_ui -> 12_business_finance_forward.py
_owner_install('finance_forward', 'finance_forward:0057')

def _v168_record_uid_seed(chat_id: int, rec: dict) -> str:
    """Stable seed that deliberately excludes mutable amount/note/short_id fields."""
    payload = {'chat_id': int(chat_id or 0), 'operation_key': str((rec or {}).get('operation_key') or ''), 'source_msg_id': int((rec or {}).get('source_msg_id') or 0), 'origin_msg_id': int((rec or {}).get('origin_msg_id') or 0), 'msg_id': int((rec or {}).get('msg_id') or 0), 'forward_source_chat_id': int((rec or {}).get('forward_source_chat_id') or 0), 'forward_source_msg_id': int((rec or {}).get('forward_source_msg_id') or 0), 'source_order_msg_id': int((rec or {}).get('source_order_msg_id') or 0), 'timestamp': str((rec or {}).get('timestamp') or ''), 'day_key': str((rec or {}).get('day_key') or ''), 'id': int((rec or {}).get('id') or 0), 'currency': 'usd' if bool((rec or {}).get('usd_only')) else 'ars'}
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(',', ':'))
    return hashlib.sha256(raw.encode('utf-8', errors='replace')).hexdigest()[:12].upper()

# [OCH12.35 OWNER] ensure_finance_record_uid -> 11_business_finance.py
_owner_install('finance', 'finance:0100')

# [OCH12.35 OWNER] find_finance_record_by_uid -> 11_business_finance.py
_owner_install('finance', 'finance:0101')


def persist_finance_chat_local_fast(chat_id: int) -> bool:
    """R48 FINAL: one owner, short RAM snapshot, one SQLite commit, then split notification."""
    try:
        cid = int(chat_id)
        lock = chat_lock_for(cid)
        if hasattr(lock, 'held_by_current_thread') and lock.held_by_current_thread():
            raise RuntimeError('R48 invariant: finance persist called while chat_lock is held')
        with locked_chat(cid):
            store = get_chat_store(cid)
            if LOWRAM_ENABLED:
                payload, cold = _lowram_flush_chat(cid, store, evict=False)
            else:
                payload, cold = copy.deepcopy(dict(store)), {}
        saved = SQLITE.save_chat_bundle(cid, payload, cold)
        if saved:
            try:
                with _LOWRAM_LOCK:
                    _LOWRAM_STATS['cold_saves'] += int(saved)
            except Exception:
                pass
        # R48: folded former R11 wrapper into the single persistence owner.
        try:
            inside_fn = globals().get('_split_inside_telegram_update_v265')
            if callable(inside_fn) and inside_fn():
                ctx = globals().get('_SPLIT_UPDATE_CONTEXT')
                if ctx is not None:
                    ctx.finance_dirty = True
            else:
                mark_fn = globals().get('_split_mark_state_changed_v265')
                sync_fn = globals().get('split_schedule_worker_sync_v262')
                if callable(mark_fn):
                    mark_fn(f'finance_commit:{cid}')
                if callable(sync_fn):
                    sync_fn(reason=f'finance_commit:{cid}', delay=0.35)
        except Exception:
            pass
        return True
    except Exception as exc:
        try: log_error(f'R48 local finance persist {chat_id}: {exc}')
        except Exception: pass
        return False


# [OCH12.35 OWNER] migrate_finance_record_uids -> 11_business_finance.py
_owner_install('finance', 'finance:0102')

# [OCH12.35 OWNER] _strip_forward_copy_edit_command -> 12_business_finance_forward.py
_owner_install('finance_forward', 'finance_forward:0058')

# [OCH12.35 OWNER] _forward_copy_record_command -> 12_business_finance_forward.py
_owner_install('finance_forward', 'finance_forward:0059')

# [OCH12.35 OWNER] _v169_forward_uid_for_copy -> 12_business_finance_forward.py
_owner_install('finance_forward', 'finance_forward:0060')

# [OCH12.35 OWNER] _predict_forward_copy_record_command -> 12_business_finance_forward.py
_owner_install('finance_forward', 'finance_forward:0061')

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

# [OCH12.35 OWNER] _forward_copy_display_text -> 12_business_finance_forward.py
_owner_install('finance_forward', 'finance_forward:0062')

# [OCH12.35 OWNER] _forward_copy_edit_keyboard -> 12_business_finance_forward.py
_owner_install('finance_forward', 'finance_forward:0063')

# [OCH12.35 OWNER] _forward_copy_origin_source_chat -> 12_business_finance_forward.py
_owner_install('finance_forward', 'finance_forward:0064')

# [OCH12.35 OWNER] _set_forward_record_metadata -> 12_business_finance_forward.py
_owner_install('finance_forward', 'finance_forward:0065')

# [OCH12.35 OWNER] apply_forward_copy_edit_ui -> 12_business_finance_forward.py
_owner_install('finance_forward', 'finance_forward:0066')

# [OCH12.35 OWNER] schedule_forward_copy_edit_ui_retry -> 12_business_finance_forward.py
_owner_install('finance_forward', 'finance_forward:0067')

# [OCH12.35 OWNER] _forward_copy_edit_wait_scheduler_key -> 12_business_finance_forward.py
_owner_install('finance_forward', 'finance_forward:0068')

# [OCH12.35 OWNER] _forward_copy_clean_copy_button -> 12_business_finance_forward.py
_owner_install('finance_forward', 'finance_forward:0069')

# [OCH12.35 OWNER] _forward_copy_edit_prompt_text -> 12_business_finance_forward.py
_owner_install('finance_forward', 'finance_forward:0070')

# [OCH12.35 OWNER] _forward_copy_edit_prompt_keyboard -> 12_business_finance_forward.py
_owner_install('finance_forward', 'finance_forward:0071')

# [OCH12.35 OWNER] refresh_active_forward_copy_edit_prompt -> 12_business_finance_forward.py
_owner_install('finance_forward', 'finance_forward:0072')

# [OCH12.35 OWNER] clear_forward_copy_edit_wait -> 12_business_finance_forward.py
_owner_install('finance_forward', 'finance_forward:0073')

# [OCH12.35 OWNER] schedule_forward_copy_edit_wait_cancel -> 12_business_finance_forward.py
_owner_install('finance_forward', 'finance_forward:0074')

# [OCH12.35 OWNER] start_forward_copy_edit -> 12_business_finance_forward.py
_owner_install('finance_forward', 'finance_forward:0075')

# R48 FINAL: removed dead legacy owner edit_forward_copy_and_record; final owner is loaded later.

def _has_visible_fin_mode_selected(chat_id: int) -> bool:
    """v108: visible auto-window selection is independent from hidden accounting."""
    try:
        return bool(is_finance_mode(chat_id) and finance_window_mode(chat_id) in {'normal', 'open', 'first'})
    except Exception:
        return False

# [OCH12.35 OWNER] _v177_legacy_0152_ensure_hidden_finance_for_forward_dst -> 12_business_finance_forward.py
_owner_install('finance_forward', 'finance_forward:0076')
try:
    _v177_legacy_0152_ensure_hidden_finance_for_forward_dst.__name__ = 'ensure_hidden_finance_for_forward_dst'
except Exception:
    pass

# [OCH12.35 OWNER] _v177_legacy_0153_set_forward_finance -> 12_business_finance_forward.py
_owner_install('finance_forward', 'finance_forward:0077')
try:
    _v177_legacy_0153_set_forward_finance.__name__ = 'set_forward_finance'
except Exception:
    pass

# [OCH12.35 OWNER] _v177_legacy_0154_remove_forward_finance -> 12_business_finance_forward.py
_owner_install('finance_forward', 'finance_forward:0078')
try:
    _v177_legacy_0154_remove_forward_finance.__name__ = 'remove_forward_finance'
except Exception:
    pass

# [OCH12.35 OWNER] _forward_key -> 12_business_finance_forward.py
_owner_install('finance_forward', 'finance_forward:0079')

# [OCH12.35 OWNER] _schedule_persist_forward_state -> 12_business_finance_forward.py
_owner_install('finance_forward', 'finance_forward:0080')

# [OCH12.35 OWNER] _persist_forward_index_in_data -> 12_business_finance_forward.py
_owner_install('finance_forward', 'finance_forward:0081')

# [OCH12.35 OWNER] _load_forward_index_from_data -> 12_business_finance_forward.py
_owner_install('finance_forward', 'finance_forward:0082')

# [OCH12.35 OWNER] _store_forward_link -> 12_business_finance_forward.py
_owner_install('finance_forward', 'finance_forward:0083')

# [OCH12.35 OWNER] _v177_legacy_0155_persist_forward_finance_delivery_now -> 12_business_finance_forward.py
_owner_install('finance_forward', 'finance_forward:0084')

try:
    _v177_legacy_0155_persist_forward_finance_delivery_now.__name__ = '_persist_forward_finance_delivery_now'
except Exception:
    pass

# [OCH12.35 OWNER] _rebuild_forward_index_from_finance_records -> 12_business_finance_forward.py
_owner_install('finance_forward', 'finance_forward:0085')

# [OCH12.35 OWNER] get_forward_links -> 12_business_finance_forward.py
_owner_install('finance_forward', 'finance_forward:0086')

# [OCH12.35 OWNER] delete_forward_copies_for_source -> 12_business_finance_forward.py
_owner_install('finance_forward', 'finance_forward:0087')

# [OCH12.35 OWNER] is_forward_delete_command -> 12_business_finance_forward.py
_owner_install('finance_forward', 'finance_forward:0088')

# [OCH12.35 OWNER] _finance_record_lists -> 11_business_finance.py
_owner_install('finance', 'finance:0103')

# [OCH12.35 OWNER] _finance_source_index_v257 -> 11_business_finance.py
_owner_install('finance', 'finance:0104')


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


# [OCH12.35 OWNER] _remember_finance_source_identity_v257 -> 11_business_finance.py
_owner_install('finance', 'finance:0105')


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


# [OCH12.35 OWNER] migrate_finance_source_index_v257 -> 11_business_finance.py
_owner_install('finance', 'finance:0106')


# [OCH12.35 OWNER] delete_forwarded_finance_record_by_msg_id -> 12_business_finance_forward.py
_owner_install('finance_forward', 'finance_forward:0089')



# [OCH12.35 OWNER] rebind_forwarded_finance_record -> 12_business_finance_forward.py
_owner_install('finance_forward', 'finance_forward:0090')


# [OCH12.35 OWNER] _replace_forward_link_pair -> 12_business_finance_forward.py
_owner_install('finance_forward', 'finance_forward:0091')

# [OCH12.35 OWNER] _v212_task_reconcile_forward_copy -> 13_business_tasks.py
_owner_install('tasks', 'tasks:0001')

# [OCH12.35 OWNER] _v260_forward_finance_op_key -> 12_business_finance_forward.py
_owner_install('finance_forward', 'finance_forward:0092')

# [OCH12.35 OWNER] _v260_forward_finance_operation_key -> 12_business_finance_forward.py
_owner_install('finance_forward', 'finance_forward:0093')

# [OCH12.35 OWNER] _v260_forward_finance_op_get -> 12_business_finance_forward.py
_owner_install('finance_forward', 'finance_forward:0094')

# [OCH12.35 OWNER] _v260_forward_finance_op_mark -> 12_business_finance_forward.py
_owner_install('finance_forward', 'finance_forward:0095')

# [OCH12.35 OWNER] _v260_find_forward_finance_record -> 12_business_finance_forward.py
_owner_install('finance_forward', 'finance_forward:0096')

# [OCH12.35 OWNER] _v260_bind_forward_finance_record -> 12_business_finance_forward.py
_owner_install('finance_forward', 'finance_forward:0097')

# [OCH12.35 OWNER] _v260_make_forward_shadow -> 12_business_finance_forward.py
_owner_install('finance_forward', 'finance_forward:0098')

# [OCH12.35 OWNER] _v260_finance_forward_repair -> 12_business_finance_forward.py
_owner_install('finance_forward', 'finance_forward:0099')

# [OCH12.35 OWNER] _v260_schedule_finance_forward_repair -> 12_business_finance_forward.py
_owner_install('finance_forward', 'finance_forward:0100')

# [OCH12.35 OWNER] recover_partial_finance_forwards_v260 -> 12_business_finance_forward.py
_owner_install('finance_forward', 'finance_forward:0101')

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

# [OCH12.35 OWNER] _cleanup_forward_storage_for_chat -> 12_business_finance_forward.py
_owner_install('finance_forward', 'finance_forward:0102')

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
        # R49: forward reactivation can persist/normalize; run it only after releasing data_lock.
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

# [OCH12.35 OWNER] _note_forward_target_migrated -> 12_business_finance_forward.py
_owner_install('finance_forward', 'finance_forward:0103')

# [OCH12.35 OWNER] _notify_forward_failure -> 12_business_finance_forward.py
_owner_install('finance_forward', 'finance_forward:0104')

# [OCH12.35 OWNER] _message_text_for_finance -> 11_business_finance.py
_owner_install('finance', 'finance:0107')

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

# [OCH12.35 OWNER] _forward_single_to_target -> 12_business_finance_forward.py
_owner_install('finance_forward', 'finance_forward:0105')

# [OCH12.35 OWNER] _flush_media_group_forward -> 12_business_finance_forward.py
_owner_install('finance_forward', 'finance_forward:0106')

# [OCH12.35 OWNER] _flush_media_group_forward_locked -> 12_business_finance_forward.py
_owner_install('finance_forward', 'finance_forward:0107')

# [OCH12.35 OWNER] _collect_media_group_for_forward -> 12_business_finance_forward.py
_owner_install('finance_forward', 'finance_forward:0108')
_FIN_FORWARD_BATCH_LOCK = threading.RLock()
_FIN_FORWARD_BATCHES = {}

# [OCH12.35 OWNER] _fin_forward_batch_id -> 12_business_finance_forward.py
_owner_install('finance_forward', 'finance_forward:0109')

# [OCH12.35 OWNER] _v177_legacy_0157_fin_forward_batch_finish_target -> 12_business_finance_forward.py
_owner_install('finance_forward', 'finance_forward:0110')
try:
    _v177_legacy_0157_fin_forward_batch_finish_target.__name__ = '_fin_forward_batch_finish_target'
except Exception:
    pass

# [OCH12.35 OWNER] _fin_forward_target_job -> 12_business_finance_forward.py
_owner_install('finance_forward', 'finance_forward:0111')

# [OCH12.35 OWNER] _start_financial_forward_batch -> 12_business_finance_forward.py
_owner_install('finance_forward', 'finance_forward:0112')

# [OCH12.35 OWNER] _forward_targets_stage -> 12_business_finance_forward.py
_owner_install('finance_forward', 'finance_forward:0113')

# [OCH12.35 OWNER] _forward_normal_stage -> 12_business_finance_forward.py
_owner_install('finance_forward', 'finance_forward:0114')

# [OCH12.35 OWNER] _forward_financial_stage -> 12_business_finance_forward.py
_owner_install('finance_forward', 'finance_forward:0115')

# [OCH12.35 OWNER] schedule_financial_forward_pipeline -> 12_business_finance_forward.py
_owner_install('finance_forward', 'finance_forward:0116')

# [OCH12.35 OWNER] _canon_forward_any_message__001 -> 12_business_finance_forward.py
_owner_install('finance_forward', 'finance_forward:0117')
# v267
