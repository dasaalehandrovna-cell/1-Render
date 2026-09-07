# v262
"""Пер-R31 UX/policy layer.

R31 extends the stable R30 layer with a third owner Info-menu mode:
NEW = compact grouped menu, OLD = pre-R29 legacy, THIRD = functional settings hub.
The user-confirmed R28/R29 hot path stays intact: ordinary callback -> handler ->
direct Telegram edit. No render queue, remote HTTP or heavy snapshot is inserted
before a visual response.
"""

R31_RELEASE_NAME = 'Пер-R35'
R30_RELEASE_NAME = R31_RELEASE_NAME
R29_RELEASE_NAME = R31_RELEASE_NAME
R29_RELEASE_STAGE = 'directive-google-info-input-sources-three-menu-modes'
R31_MENU_MODE_THIRD = 'third'
R30_MENU_MODE_KEY = 'r30_info_menu_mode'
R30_MENU_MODE_DEFAULT = 'new'
R29_INPUT_SETTINGS_KEY = 'r29_input_sources'
R29_INPUT_DEFAULTS = {'forwarded': True, 'other_bots': True}

def r29_assert_r28_fast_ui_contract() -> bool:
    """Hard startup guard for the user-confirmed R28 button-speed contract.

    Future releases must fail loudly instead of silently re-introducing a render
    queue between an ordinary callback handler and Telegram editMessageText.
    """
    fn = globals().get('fast_ui_edit_message_text')
    if not callable(fn):
        raise RuntimeError('R29 FAST UI CONTRACT: fast_ui_edit_message_text is missing')
    try:
        filename = str(getattr(getattr(fn, '__code__', None), 'co_filename', '') or '')
        source = inspect.getsource(fn)
    except Exception as exc:
        raise RuntimeError('R29 FAST UI CONTRACT: cannot inspect active renderer: ' + str(exc))
    if not filename.endswith('74_ui_reliability_runtime.py'):
        raise RuntimeError('R29 FAST UI CONTRACT: renderer owner changed: ' + filename)
    if 'WINDOW_RENDER_TASK_POOL' in source:
        raise RuntimeError('R29 FAST UI CONTRACT: render queue reintroduced before Telegram')
    if '_perform_fast_ui_edit(payload)' not in source:
        raise RuntimeError('R29 FAST UI CONTRACT: direct Telegram render call is missing')
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
        'ℹ️ ИНФО · Пер-R35 · ТРЕТИЙ ВАРИАНТ\n\n'
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
        'ℹ️ ИНФО · Пер-R35\n\n'
        'Меню собрано по разделам, чтобы служебные кнопки не занимали несколько экранов.\n'
        'Доступны три режима Info: Новое, Старое и Третий вариант.\n\n'
        '⚡ FAST UI: прямой путь R28 защищён.\n'
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
        return _r30_legacy_info_keyboard_with_controls(cid)
    if mode == R31_MENU_MODE_THIRD:
        return _r31_third_info_keyboard(cid)
    kb = types.InlineKeyboardMarkup(row_width=2)
    kb.row(IB('📊 Состояние', callback_data='r29:info:status'), IB('🔗 Интеграции', callback_data='r29:info:integrations'))
    kb.row(IB('⚙️ Настройки', callback_data='r29:info:settings'), IB('📁 Журналы', callback_data='r29:info:journals'))
    kb.row(IB('📥 Источники сообщений', callback_data='r29:inputs:open'))
    kb.row(IB('🛠 Владельцу', callback_data='r29:info:owner'))
    if not _r31_constructors_enabled():
        kb.row(IB('🧩 Конструкторы', callback_data='r31:constructors:open'))
    kb.row(_r30_menu_mode_button(cid))
    kb.row(IB('🔙 Назад', callback_data='nav_prev'), IB('❌ Закрыть', callback_data='info_close'))
    return kb


globals()['build_info_text'] = _r29_build_info_text
globals()['build_info_keyboard'] = _r29_build_info_keyboard

# ---------------------------------------------------------------------------
# Google single-window UX.
# ---------------------------------------------------------------------------

_R29_GOOGLE_BASE_CALLBACK = globals().get('v149_extension_callback')
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


def _r29_google_extension_callback(call, data_str: str) -> bool:
    raw = str(data_str or '')
    if not raw.startswith('v149:google:'):
        return bool(_R29_GOOGLE_BASE_CALLBACK(call, raw)) if callable(_R29_GOOGLE_BASE_CALLBACK) else False
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
    # Unknown Google action: keep legacy compatibility, but only after known single-window paths.
    return bool(_R29_GOOGLE_BASE_CALLBACK(call, raw)) if callable(_R29_GOOGLE_BASE_CALLBACK) else True


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


globals()['tenant_google_keyboard'] = _r29_google_keyboard
globals()['v149_extension_callback'] = _r29_google_extension_callback
globals()['tenant_google_handle_message'] = _r29_google_handle_message

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


globals()['contour_callback_guard'] = _r29_contour_callback_guard

# Marker declarations for the new local windows.
try:
    WINDOW_MARKER_CONSTANTS.setdefault('r29:inputs:*', 'Ф3237')
    WINDOW_MARKER_CONSTANTS.setdefault('r29:info:*', 'Ф89')
    WINDOW_MARKER_CONSTANTS.setdefault('r29:directive:*', 'Ф3237')
    WINDOW_MARKER_CONSTANTS.setdefault('r30:menu:*', 'Ф89')
    WINDOW_MARKER_CONSTANTS.setdefault('r31:info:*', 'Ф89')
    WINDOW_MARKER_CONSTANTS.setdefault('r31:toggle:*', 'Ф89')
    WINDOW_MARKER_CONSTANTS.setdefault('r31:constructors:*', 'Ф89')
except Exception:
    pass

try:
    bot_journal('r31_policy_ui_ready', int(OWNER_ID or 0),
                'r28_direct_render_protected=1; directive_business_lock=1; google_single_window=1; info_menu_new_old_third=1; third_groups=finance+forward+reminders+tasks+contours+general+journals+owner; master_tz_markers=1; master_constructors=1; input_sources=forwarded+other_bots')
except Exception:
    pass
# v262
