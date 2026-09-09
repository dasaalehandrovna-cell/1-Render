# v262
"""v205: restore the v196 non-destructive UI Constructor 1/2 lab.

The constructor changes only Telegram presentation (button text/order/visibility) for the
primary owner. Existing callback_data and business handlers remain authoritative.
"""
V196_CONSTRUCTOR_ROOT = 'ui_constructor_v196'
V196_CONSTRUCTOR_SCHEMA = 1
V196_CONSTRUCTOR_PREFIX = 'v196:'
V196_CATALOG_LIMIT = 1200
V196_VERSION_LIMIT = 30
_V196_LOCK = threading.RLock()
_V196_SESSIONS = {}
_V196_PANEL_MESSAGES = set()
_V196_LAST_BASE_BY_KEY = {}
_V196_LAST_META_BY_TOKEN = {}
_V196_ACTIVE_WORKING_BY_KEY = {}

def _v196_now():
    try:
        return now_local().isoformat(timespec='seconds')
    except Exception:
        return datetime.now().isoformat(timespec='seconds')

def _v196_root(create=True):
    try:
        gs = data.setdefault('_global_settings', {}) if create else data.get('_global_settings') or {}
    except Exception:
        return {}
    root = gs.get(V196_CONSTRUCTOR_ROOT)
    if not isinstance(root, dict):
        if not create:
            return {}
        root = {}
        gs[V196_CONSTRUCTOR_ROOT] = root
    root.setdefault('schema', V196_CONSTRUCTOR_SCHEMA)
    flags = root.setdefault('flags', {})
    defaults = {'enabled': True, 'show_c1': True, 'show_c2': True, 'compact_constructor_row': True, 'apply_profiles': True, 'freeze_timers': True, 'preserve_new_buttons': True, 'observe_catalog': True, 'developer_labels': False}
    for key, value in defaults.items():
        flags.setdefault(key, value)
    root.setdefault('windows', {})
    root.setdefault('catalog', {})
    root.setdefault('token_map', {})
    root.setdefault('global_versions', {})
    root.setdefault('ideas', [])
    root.setdefault('next_idea_id', 1)
    root.setdefault('updated_at', _v196_now())
    return root

def _v196_flags():
    return _v196_root(True).setdefault('flags', {})

def _v196_persist(reason='settings'):
    root = _v196_root(True)
    root['updated_at'] = _v196_now()
    try:
        save_data(data, root_only=True)
    except TypeError:
        try:
            save_data(data)
        except Exception:
            pass
    except Exception:
        try:
            save_data(data)
        except Exception:
            pass
    try:
        fn = globals().get('schedule_delta_backup')
        if callable(fn):
            fn(None, delay=0.8, reason=f'ui_constructor:{str(reason)[:90]}')
    except Exception:
        pass
    try:
        bot_journal('ui_constructor_v196_saved', int(OWNER_ID or 0), str(reason)[:180])
    except Exception:
        pass

def _v196_owner_context():
    try:
        cid = int(current_state_chat_id() or 0)
        return bool(cid and int(OWNER_ID or 0) and (cid == int(OWNER_ID)))
    except Exception:
        return False

def _v196_can_manage_call(call):
    try:
        cid = int(call.message.chat.id)
        uid = int(getattr(getattr(call, 'from_user', None), 'id', 0) or 0)
        return bool(int(OWNER_ID or 0) and cid == int(OWNER_ID) and (uid == int(OWNER_ID)))
    except Exception:
        return False

def _v196_rows(markup):
    if markup is None:
        return []
    try:
        ser = globals().get('_serialize_inline_keyboard')
        if callable(ser):
            rows = ser(markup)
            if isinstance(rows, list):
                return copy.deepcopy(rows)
    except Exception:
        pass
    out = []
    try:
        source = list(getattr(markup, 'keyboard', None) or getattr(markup, 'inline_keyboard', None) or [])
        for row in source:
            nr = []
            for btn in row or []:
                if hasattr(btn, 'to_dict'):
                    nr.append(dict(btn.to_dict() or {}))
                else:
                    nr.append({'text': str(getattr(btn, 'text', '') or ''), 'callback_data': getattr(btn, 'callback_data', None), 'url': getattr(btn, 'url', None)})
            if nr:
                out.append(nr)
    except Exception:
        pass
    return out

def _v196_is_constructor_button(raw):
    try:
        return str((raw or {}).get('callback_data') or '').startswith(V196_CONSTRUCTOR_PREFIX)
    except Exception:
        return False

def _v196_strip_constructor_rows(rows):
    out = []
    for row in rows or []:
        nr = [dict(btn or {}) for btn in row or [] if not _v196_is_constructor_button(btn)]
        if nr:
            out.append(nr)
    return out

def _v196_normalize_callback(cb):
    value = str(cb or '').strip()
    if not value:
        return ''
    value = re.sub('20\\d{2}-\\d{2}-\\d{2}', '{date}', value)
    value = re.sub('(?<!\\d)-?\\d{7,}(?!\\d)', '{id}', value)
    value = re.sub('(?<=:)[0-9a-fA-F]{8,}(?=[:$])', '{token}', value)
    return value[:180]

def _v196_annotate_rows(rows):
    counts = {}
    out = []
    for row in rows or []:
        nr = []
        for raw in row or []:
            btn = dict(raw or {})
            cb = str(btn.get('callback_data') or '')
            base = 'cb:' + _v196_normalize_callback(cb) if cb else 'url:' + str(btn.get('url') or btn.get('text') or '')[:150]
            counts[base] = int(counts.get(base, 0)) + 1
            btn['_v196_origin'] = f'{base}#{counts[base]}'
            nr.append(btn)
        if nr:
            out.append(nr)
    return out

def _v196_origins(rows):
    return [str(btn.get('_v196_origin') or '') for row in rows or [] for btn in row or [] if str(btn.get('_v196_origin') or '')]

def _v196_sanitize_button(raw):
    allowed = {'text', 'url', 'callback_data', 'switch_inline_query', 'switch_inline_query_current_chat', 'callback_game', 'pay', 'login_url', 'web_app', 'copy_text', 'switch_inline_query_chosen_chat'}
    return {key: value for key, value in dict(raw or {}).items() if key in allowed and value is not None}

def _v196_markup(rows):
    kb = types.InlineKeyboardMarkup()
    for row in rows or []:
        buttons = []
        for raw in row or []:
            clean = _v196_sanitize_button(raw)
            text = str(clean.pop('text', '') or '')
            try:
                buttons.append(types.InlineKeyboardButton(text, **clean))
            except Exception:
                try:
                    cb = clean.get('callback_data')
                    if cb is not None:
                        buttons.append(IB(text, callback_data=str(cb)))
                    elif clean.get('url'):
                        buttons.append(types.InlineKeyboardButton(text=text, url=str(clean.get('url'))))
                except Exception:
                    pass
        if buttons:
            kb.row(*buttons)
    return kb

def _v196_marker(text):
    try:
        fn = globals().get('_v160_marker_from_text')
        if callable(fn):
            marker = str(fn(str(text or '')) or '').upper()
            if marker:
                return marker
    except Exception:
        pass
    match = re.search('(?:^|\\n)\\s*([СФПОВсов]\\d{1,6})(?:\\s*[⏳⏰])?\\s*$', str(text or ''), flags=re.I)
    return str(match.group(1) if match else '').upper()

def _v196_window_label(text, key):
    raw = re.sub('<[^>]+>', '', str(text or ''))
    raw = re.sub('(?:^|\\n)\\s*[СФПОВсов]\\d{1,6}(?:\\s*[⏳⏰])?\\s*$', '', raw, flags=re.I).strip()
    first = next((re.sub('\\s+', ' ', line).strip() for line in raw.splitlines() if line.strip()), '')
    return first[:72] if first else str(key)

def _v196_window_key(text, annotated_base_rows):
    marker = _v196_marker(text) or 'NO-MARK'
    norms = []
    for row in annotated_base_rows or []:
        for btn in row or []:
            cb = str(btn.get('callback_data') or '')
            if cb.startswith(V196_CONSTRUCTOR_PREFIX):
                continue
            norms.append(_v196_normalize_callback(cb) if cb else 'url:' + str(btn.get('url') or btn.get('text') or '')[:80])
    digest = hashlib.sha1('|'.join(sorted(norms)).encode('utf-8', 'ignore')).hexdigest()[:12]
    return f'{marker}:{digest}'

def _v196_token_for_key(key, label=''):
    token = hashlib.sha1(str(key).encode('utf-8', 'ignore')).hexdigest()[:12]
    root = _v196_root(True)
    root.setdefault('token_map', {})[token] = str(key)
    _V196_LAST_META_BY_TOKEN[token] = {'key': str(key), 'label': str(label or key)[:100]}
    return token

def _v196_key_for_token(token):
    token = str(token or '')
    meta = _V196_LAST_META_BY_TOKEN.get(token) or {}
    if meta.get('key'):
        return str(meta['key'])
    return str((_v196_root(False).get('token_map') or {}).get(token) or '')

def _v212_legacy__v196_window_cfg(key, create=True):
    windows = _v196_root(create).setdefault('windows', {}) if create else _v196_root(False).get('windows') or {}
    cfg = windows.get(str(key))
    if not isinstance(cfg, dict):
        if not create:
            return {}
        cfg = {'current_rows': None, 'known_origins': [], 'versions': {}, 'active_version': None, 'label': str(key), 'marker': ''}
        windows[str(key)] = cfg
    cfg.setdefault('versions', {})
    cfg.setdefault('known_origins', [])
    return cfg

def _v196_catalog_capture(rows, marker='', source='observed'):
    if not _v196_flags().get('observe_catalog', True):
        return
    cat = _v196_root(True).setdefault('catalog', {})
    for row in rows or []:
        for raw in row or []:
            cb = str(raw.get('callback_data') or '').strip()
            label = str(raw.get('text') or '').strip()
            if not label or not cb or cb == 'none' or cb.startswith(V196_CONSTRUCTOR_PREFIX):
                continue
            token = hashlib.sha1(cb.encode('utf-8', 'ignore')).hexdigest()[:12]
            cat[token] = {'token': token, 'text': label[:100], 'callback_data': cb[:500], 'marker': str(marker or ''), 'source': str(source), 'seen_at': _v196_now()}
    if len(cat) > V196_CATALOG_LIMIT:
        items = sorted(cat.items(), key=lambda item: str((item[1] or {}).get('seen_at') or ''), reverse=True)[:V196_CATALOG_LIMIT]
        cat.clear()
        cat.update(items)

def ui_constructor_scan_source_catalog(persist=True):
    added = 0
    try:
        root = Path(__file__).resolve().parent if '__file__' in globals() else Path.cwd()
        manifest = json.loads((root / 'modules_manifest.json').read_text(encoding='utf-8'))
        cat = _v196_root(True).setdefault('catalog', {})
        pattern = re.compile('IB\\(\\s*([\\"\'])(.{1,100}?)\\1\\s*,\\s*callback_data\\s*=\\s*([\\"\'])(.{1,500}?)\\3', re.S)
        for rel in (manifest.get('files') or {}).keys():
            if str(rel).startswith('88_ui_constructor'):
                continue
            try:
                text = (root / rel).read_text(encoding='utf-8')
            except Exception:
                continue
            for match in pattern.finditer(text):
                label = str(match.group(2) or '').replace('\\n', ' ').strip()
                cb = str(match.group(4) or '').strip()
                if not label or not cb or cb == 'none' or ('{' in cb) or ('}' in cb):
                    continue
                token = hashlib.sha1(cb.encode('utf-8', 'ignore')).hexdigest()[:12]
                if token not in cat:
                    added += 1
                cat[token] = {'token': token, 'text': label[:100], 'callback_data': cb[:500], 'marker': '', 'source': 'source', 'seen_at': _v196_now()}
        if persist and added:
            _v196_persist(f'catalog scan +{added}')
    except Exception as exc:
        try:
            log_error(f'v196 source catalog scan: {exc}')
        except Exception:
            pass
    return added

def _v212_legacy__v196_apply_profile_to_base(key, base):
    cfg = _v196_window_cfg(key, False)
    stored = cfg.get('current_rows')
    if not _v196_flags().get('apply_profiles', True) or not isinstance(stored, list):
        return copy.deepcopy(base)
    current_by_origin = {str(btn.get('_v196_origin') or ''): btn for row in base or [] for btn in row or [] if str(btn.get('_v196_origin') or '')}
    out = []
    used = set()
    for row in stored:
        nr = []
        for saved in row or []:
            origin = str(saved.get('_v196_origin') or '')
            if bool(saved.get('_v196_manual')):
                nr.append(copy.deepcopy(saved))
                used.add(origin)
                continue
            cur = current_by_origin.get(origin)
            if cur is None:
                continue
            btn = copy.deepcopy(cur)
            btn['text'] = str(saved.get('text') or btn.get('text') or '')[:100]
            nr.append(btn)
            used.add(origin)
        if nr:
            out.append(nr)
    if _v196_flags().get('preserve_new_buttons', True):
        known = set((str(x) for x in cfg.get('known_origins') or []))
        for row in base or []:
            extras = [copy.deepcopy(btn) for btn in row or [] if str(btn.get('_v196_origin') or '') not in used and str(btn.get('_v196_origin') or '') not in known]
            if extras:
                out.append(extras)
    return out

def _v196_constructor_controls(rows, token):
    flags = _v196_flags()
    if not flags.get('enabled', True):
        return rows
    buttons = []
    if flags.get('show_c1', True):
        buttons.append({'text': '🧩 Конструктор 1', 'callback_data': f'v196:c1:{token}'})
    if flags.get('show_c2', True):
        buttons.append({'text': '🛠 Конструктор 2', 'callback_data': f'v196:c2:{token}'})
    if not buttons:
        return rows
    out = copy.deepcopy(rows)
    if flags.get('compact_constructor_row', True):
        out.append(buttons)
    else:
        for button in buttons:
            out.append([button])
    return out
_V196_PREV_AUGMENT_MARKUP = _canon_v160_augment_markup__001

def _v212_legacy__v160_augment_markup(reply_markup, text: str, chat_id=None):
    kb = _V196_PREV_AUGMENT_MARKUP(reply_markup, text, chat_id) if callable(_V196_PREV_AUGMENT_MARKUP) else reply_markup
    try:
        if not _v196_owner_context():
            return kb
        marker = _v196_marker(text)
        if not marker:
            return kb
        base = _v196_strip_constructor_rows(_v196_rows(kb))
        annotated = _v196_annotate_rows(base)
        key = _v196_window_key(text, annotated)
        label = _v196_window_label(text, key)
        token = _v196_token_for_key(key, label)
        _V196_LAST_BASE_BY_KEY[key] = copy.deepcopy(annotated)
        _v196_catalog_capture(annotated, marker, 'observed')
        cfg = _v196_window_cfg(key, True)
        cfg['label'] = label
        cfg['marker'] = marker
        cfg['last_seen_at'] = _v196_now()
        effective = _v196_apply_profile_to_base(key, annotated)
        effective = _v196_constructor_controls(effective, token)
        return _v196_markup(effective)
    except Exception as exc:
        try:
            log_error(f'v196 augment markup: {exc}')
        except Exception:
            pass
        return kb

def ui_constructor_window_frozen(chat_id, message_id):
    key = (int(chat_id), int(message_id))
    with _V196_LOCK:
        return any(((int(s.get('target_chat_id') or 0), int(s.get('target_message_id') or 0)) == key and s.get('freeze') for s in _V196_SESSIONS.values()))

def _v196_freeze_window(chat_id, message_id):
    if not _v196_flags().get('freeze_timers', True):
        return {}
    cid, mid = (int(chat_id), int(message_id))
    rearm = {'v98': False, 'stored': [], 'secret_media': False, 'secret_calendar': False}
    try:
        with _v98_auto_close_lock:
            rearm['v98'] = (cid, mid) in _v98_auto_close_timers
        _cancel_v98_auto_close(cid, mid)
    except Exception:
        pass
    try:
        store = get_chat_store(cid)
        for sk, value in list(store.items()):
            try:
                if int(value or 0) == mid:
                    key = f'stored-window-delete:{cid}:{sk}'
                    if DELAYED_SCHEDULER.deadline(key):
                        rearm['stored'].append(str(sk))
                        DELAYED_SCHEDULER.cancel(key)
            except Exception:
                continue
    except Exception:
        pass
    try:
        rearm['secret_media'] = (cid, mid) in globals().get('_secret_media_timer_generation', {})
        if rearm['secret_media']:
            cancel_secret_media_timer(cid, mid)
    except Exception:
        pass
    try:
        rearm['secret_calendar'] = (cid, mid) in globals().get('_secret_calendar_timers', {})
        if rearm['secret_calendar']:
            token = globals().get('_secret_calendar_timers', {}).pop((cid, mid), None)
            DELAYED_SCHEDULER.cancel(f'secret-calendar-close:{cid}:{mid}')
    except Exception:
        pass
    return rearm

def _v196_rearm_window(session):
    cid = int(session.get('target_chat_id') or 0)
    mid = int(session.get('target_message_id') or 0)
    rearm = session.get('rearm') or {}
    if not cid or not mid:
        return
    try:
        if rearm.get('v98'):
            _schedule_v98_auto_close(cid, mid, None)
    except Exception:
        pass
    for sk in rearm.get('stored') or []:
        try:
            schedule_stored_window_delete(cid, str(sk), None)
        except Exception:
            pass
    try:
        if rearm.get('secret_media'):
            schedule_secret_media_close(cid, mid)
    except Exception:
        pass
    try:
        if rearm.get('secret_calendar'):
            schedule_secret_calendar_close(cid, mid)
    except Exception:
        pass

def _v196_session(panel_message_id):
    with _V196_LOCK:
        return _V196_SESSIONS.get(int(panel_message_id))

def _v196_close_session(panel_message_id, delete_panel=False):
    with _V196_LOCK:
        session = _V196_SESSIONS.pop(int(panel_message_id), None)
        _V196_PANEL_MESSAGES.discard(int(panel_message_id))
    if session:
        _v196_rearm_window(session)
    if delete_panel and session:
        try:
            bot.delete_message(int(session.get('owner_chat_id') or OWNER_ID), int(panel_message_id))
        except Exception:
            pass
    return session

def _v196_panel_edit(call, text, kb):
    try:
        bot.edit_message_text(str(text), chat_id=int(call.message.chat.id), message_id=int(call.message.message_id), reply_markup=kb)
    except Exception as exc:
        if 'message is not modified' not in str(exc).lower():
            try:
                log_error(f'v196 panel edit: {exc}')
            except Exception:
                pass

def _v196_answer(call, text='', alert=False):
    try:
        bot.answer_callback_query(call.id, str(text or ''), show_alert=bool(alert))
    except Exception:
        pass

def _v212_legacy__v196_original_rows_for_key(key):
    return copy.deepcopy(_V196_LAST_BASE_BY_KEY.get(str(key)) or [])

def _v212_legacy__v196_apply_target(session):
    try:
        rows = copy.deepcopy(session.get('working_rows') or [])
        token = str(session.get('token') or _v196_token_for_key(str(session.get('window_key') or ''), str(session.get('window_label') or '')))
        rows = _v196_constructor_controls(rows, token)
        bot.edit_message_reply_markup(chat_id=int(session['target_chat_id']), message_id=int(session['target_message_id']), reply_markup=_v196_markup(rows))
        try:
            bot_journal('ui_constructor_target_apply_v208', int(OWNER_ID or 0), f"key={session.get('window_key')} target={session.get('target_chat_id')}:{session.get('target_message_id')} rows={len(rows)} buttons={sum((len(r or []) for r in rows))} selected={session.get('selected')}")
        except Exception:
            pass
        return True
    except Exception as exc:
        try:
            log_error(f'v196 apply target: {exc}')
        except Exception:
            pass
        return False

def _v212_legacy__v196_store_current(session, reason='change'):
    key = str(session.get('window_key') or '')
    cfg = _v196_window_cfg(key, True)
    cfg['current_rows'] = copy.deepcopy(session.get('working_rows') or [])
    if not cfg.get('known_origins'):
        cfg['known_origins'] = list(session.get('known_origins') or [])
    cfg['active_version'] = None
    cfg['updated_at'] = _v196_now()
    _V196_ACTIVE_WORKING_BY_KEY[key] = copy.deepcopy(cfg['current_rows'])
    _v196_persist(f'c1 {reason} {key}')

def _v212_legacy__v196_reset_session_to_original(session, persist=True):
    key = str(session.get('window_key') or '')
    base = _v196_original_rows_for_key(key)
    if base:
        session['working_rows'] = copy.deepcopy(base)
        session['known_origins'] = _v196_origins(base)
    cfg = _v196_window_cfg(key, True)
    cfg['current_rows'] = None
    cfg['known_origins'] = list(session.get('known_origins') or [])
    cfg['active_version'] = None
    _V196_ACTIVE_WORKING_BY_KEY.pop(key, None)
    if persist:
        _v196_persist(f'c1 reset {key}')
    _v196_apply_target(session)

def _v196_button_flat(rows):
    return [(ri, bi, btn) for ri, row in enumerate(rows or []) for bi, btn in enumerate(row or [])]

def _v196_short_button_label(btn, dev=False):
    label = str((btn or {}).get('text') or 'Кнопка').replace('\n', ' ')
    if dev:
        cb = str((btn or {}).get('callback_data') or '')
        if cb:
            label += ' · ' + cb[:22]
    return label if len(label) <= 52 else label[:51] + '…'

def _v212_legacy__v196_c1_text(session):
    key = str(session.get('window_key') or '')
    cfg = _v196_window_cfg(key, False)
    versions = cfg.get('versions') or {}
    count = sum((len(row or []) for row in session.get('working_rows') or []))
    base_count = len(session.get('known_origins') or [])
    active = cfg.get('active_version')
    return f"🧩 КОНСТРУКТОР 1 · ПРЕДСТАВЛЕНИЕ\n\nОкно: {session.get('window_label') or key}\nКнопок сейчас: {count}; исходных: {base_count}\nСохранённых версий: {len(versions)}; активная: {('v' + str(active) if active else 'текущая настройка')}\n⏸ Автовозврат/автозакрытие исходного окна заморожены, пока редактор открыт.\n\nМеняются только подписи, порядок и видимость кнопок. Действия/callback бизнес-логики не переписываются."

def _v212_legacy__v196_c1_main_keyboard(session):
    kb = types.InlineKeyboardMarkup(row_width=2)
    kb.row(IB('➖ Убирать', callback_data='v196:c1:remove'), IB('➕ Добавлять', callback_data='v196:c1:add:0'))
    kb.row(IB('✏️ Имена', callback_data='v196:c1:rename'), IB('↔️ Места', callback_data='v196:c1:move'))
    kb.row(IB('💾 Сохранить версию', callback_data='v196:c1:save'), IB('📚 Версии', callback_data='v196:c1:versions:0'))
    kb.row(IB('♻️ Откатить как было', callback_data='v196:c1:reset'), IB('🛠 Конструктор 2', callback_data='v196:c1:to_c2'))
    kb.row(IB('✅ Закончить', callback_data='v196:c1:done'))
    return kb

def _v196_c1_list_keyboard(session, action, page=0):
    items = _v196_button_flat(session.get('working_rows') or [])
    page_size = 10
    pages = max(1, (len(items) + page_size - 1) // page_size)
    page = max(0, min(int(page), pages - 1))
    kb = types.InlineKeyboardMarkup(row_width=1)
    dev = bool(_v196_flags().get('developer_labels'))
    for ri, bi, btn in items[page * page_size:(page + 1) * page_size]:
        prefix = {'remove': 'rm', 'rename': 'ren', 'move': 'sel'}.get(action, action)
        icon = {'remove': '➖', 'rename': '✏️', 'move': '↔️'}.get(action, '•')
        kb.row(IB(f'{icon} {_v196_short_button_label(btn, dev)}', callback_data=f'v196:c1:{prefix}:{ri}:{bi}'))
    if pages > 1:
        nav = []
        if page > 0:
            nav.append(IB('⬅️', callback_data=f'v196:c1:{action}:{page - 1}'))
        nav.append(IB(f'{page + 1}/{pages}', callback_data='none'))
        if page + 1 < pages:
            nav.append(IB('➡️', callback_data=f'v196:c1:{action}:{page + 1}'))
        kb.row(*nav)
    kb.row(IB('⬅️ В Конструктор 1', callback_data='v196:c1:main'))
    kb.row(IB('✅ Закончить', callback_data='v196:c1:done'))
    return kb

def _v207_move_preview(session):
    """Constructor 1 / Places: arrow controls + live keyboard-shaped selector in one panel."""
    rows = session.get('working_rows') or []
    selected = session.get('selected')
    try:
        sri, sbi = (int(selected[0]), int(selected[1])) if selected else (-1, -1)
        selected_btn = rows[sri][sbi] if sri >= 0 and sbi >= 0 else None
    except Exception:
        sri = sbi = -1
        selected_btn = None
        session['selected'] = None
    kb = types.InlineKeyboardMarkup(row_width=4)
    kb.row(IB('⬆️', callback_data='v196:c1:mv:up'), IB('⬇️', callback_data='v196:c1:mv:down'), IB('⬅️', callback_data='v196:c1:mv:left'), IB('➡️', callback_data='v196:c1:mv:right'))
    kb.row(IB('➗ Отдельно', callback_data='v196:c1:mv:solo'), IB('➕ В соседнюю', callback_data='v196:c1:mv:join'))
    dev = bool(_v196_flags().get('developer_labels'))
    for ri, row in enumerate(rows):
        controls = []
        for bi, btn in enumerate(row or []):
            label = _v196_short_button_label(btn, dev)
            if ri == sri and bi == sbi:
                label = '✅ ' + label
            controls.append(IB(label, callback_data=f'v196:c1:sel:{ri}:{bi}'))
        if controls:
            kb.row(*controls)
    kb.row(IB('⬅️ В Конструктор 1', callback_data='v196:c1:main'))
    kb.row(IB('✅ Закончить', callback_data='v196:c1:done'))
    if selected_btn is None:
        text = '↔️ МЕСТА КНОПОК\n\nНажмите нужную кнопку ниже. После выбора возле неё появится ✅, а стрелками сверху можно менять её место.'
    else:
        text = f'↔️ МЕСТА КНОПОК\n\nВыбрано: ✅ {_v196_short_button_label(selected_btn)}\nСтрока {sri + 1}, позиция {sbi + 1}.\n\nСтрелки сразу обновляют и это меню, и редактируемое окно.'
    return (text, kb)

def _v196_move_selected_keyboard(session):
    return _v207_move_preview(session)

def _v207_move_button(session, direction: str) -> tuple[bool, str]:
    rows = session.get('working_rows') or []
    selected = session.get('selected')
    if not selected:
        return (False, 'Сначала выберите кнопку')
    try:
        ri, bi = (int(selected[0]), int(selected[1]))
        if ri < 0 or ri >= len(rows) or bi < 0 or (bi >= len(rows[ri])):
            raise IndexError
    except Exception:
        session['selected'] = None
        return (False, 'Кнопка уже изменилась — выберите её заново')
    direction = str(direction or '')
    if direction == 'left':
        if bi <= 0:
            return (False, 'Кнопка уже крайняя слева')
        rows[ri][bi - 1], rows[ri][bi] = (rows[ri][bi], rows[ri][bi - 1])
        session['selected'] = (ri, bi - 1)
        return (True, 'Перемещено влево')
    if direction == 'right':
        if bi + 1 >= len(rows[ri]):
            return (False, 'Кнопка уже крайняя справа')
        rows[ri][bi + 1], rows[ri][bi] = (rows[ri][bi], rows[ri][bi + 1])
        session['selected'] = (ri, bi + 1)
        return (True, 'Перемещено вправо')
    if direction in {'up', 'down'}:
        target = ri - 1 if direction == 'up' else ri + 1
        if target < 0 or target >= len(rows):
            return (False, 'Выше строки нет' if direction == 'up' else 'Ниже строки нет')
        btn = rows[ri].pop(bi)
        source_removed = not rows[ri]
        if source_removed:
            rows.pop(ri)
            if target > ri:
                target -= 1
        target = max(0, min(target, len(rows) - 1))
        pos = min(bi, len(rows[target]))
        rows[target].insert(pos, btn)
        session['selected'] = (target, pos)
        return (True, 'Перемещено вверх' if direction == 'up' else 'Перемещено вниз')
    if direction == 'solo':
        if len(rows[ri]) == 1:
            return (False, 'Кнопка уже находится отдельной строкой')
        btn = rows[ri].pop(bi)
        insert_at = ri + 1
        rows.insert(insert_at, [btn])
        session['selected'] = (insert_at, 0)
        return (True, 'Кнопка вынесена в отдельную строку')
    if direction == 'join':
        if len(rows) <= 1:
            return (False, 'Соседней строки нет')
        btn = rows[ri].pop(bi)
        source_removed = not rows[ri]
        old_ri = ri
        if source_removed:
            rows.pop(ri)
        if old_ri > 0:
            target = old_ri - 1
        else:
            target = 0 if source_removed else 1
        target = max(0, min(target, len(rows) - 1))
        rows[target].append(btn)
        session['selected'] = (target, len(rows[target]) - 1)
        return (True, 'Кнопка добавлена в соседнюю строку')
    return (False, 'Неизвестное направление')

def _v196_catalog_rows():
    return sorted(list((_v196_root(True).get('catalog') or {}).values()), key=lambda row: (str(row.get('text') or '').casefold(), str(row.get('callback_data') or '')))

def _v196_c1_add_keyboard(session, page=0):
    rows = _v196_catalog_rows()
    page_size = 10
    pages = max(1, (len(rows) + page_size - 1) // page_size)
    page = max(0, min(int(page), pages - 1))
    kb = types.InlineKeyboardMarkup(row_width=1)
    for row in rows[page * page_size:(page + 1) * page_size]:
        label = str(row.get('text') or 'Кнопка')
        label = label if len(label) <= 48 else label[:47] + '…'
        kb.row(IB('➕ ' + label, callback_data=f"v196:c1:addpick:{row.get('token')}"))
    if not rows:
        kb.row(IB('Каталог пока пуст', callback_data='none'))
    if pages > 1:
        nav = []
        if page > 0:
            nav.append(IB('⬅️', callback_data=f'v196:c1:add:{page - 1}'))
        nav.append(IB(f'{page + 1}/{pages}', callback_data='none'))
        if page + 1 < pages:
            nav.append(IB('➡️', callback_data=f'v196:c1:add:{page + 1}'))
        kb.row(*nav)
    kb.row(IB('🔎 Пересканировать исходники', callback_data=f'v196:c1:addscan:{page}'))
    kb.row(IB('⬅️ В Конструктор 1', callback_data='v196:c1:main'))
    kb.row(IB('✅ Закончить', callback_data='v196:c1:done'))
    return kb

def _v196_save_window_version(session):
    key = str(session.get('window_key') or '')
    cfg = _v196_window_cfg(key, True)
    versions = cfg.setdefault('versions', {})
    ids = [int(x) for x in versions if str(x).isdigit()]
    vid = max(ids or [0]) + 1
    versions[str(vid)] = {'id': vid, 'created_at': _v196_now(), 'rows': copy.deepcopy(session.get('working_rows') or []), 'known_origins': list(session.get('known_origins') or []), 'label': str(session.get('window_label') or key)[:100]}
    if len(versions) > V196_VERSION_LIMIT:
        for old in sorted([int(x) for x in versions if str(x).isdigit()])[:-V196_VERSION_LIMIT]:
            versions.pop(str(old), None)
    cfg['current_rows'] = copy.deepcopy(session.get('working_rows') or [])
    cfg['known_origins'] = list(session.get('known_origins') or [])
    cfg['active_version'] = vid
    _V196_ACTIVE_WORKING_BY_KEY[key] = copy.deepcopy(cfg['current_rows'])
    _v196_persist(f'c1 save v{vid} {key}')
    return vid

def _v196_versions_keyboard(session, page=0):
    cfg = _v196_window_cfg(str(session.get('window_key') or ''), False)
    versions = cfg.get('versions') or {}
    items = sorted([(int(k), v) for k, v in versions.items() if str(k).isdigit()], reverse=True)
    page_size = 8
    pages = max(1, (len(items) + page_size - 1) // page_size)
    page = max(0, min(int(page), pages - 1))
    kb = types.InlineKeyboardMarkup(row_width=2)
    for vid, row in items[page * page_size:(page + 1) * page_size]:
        active = '✅ ' if int(cfg.get('active_version') or 0) == vid else ''
        kb.row(IB(f"{active}v{vid} · {str(row.get('created_at') or '')[5:16]}", callback_data=f'v196:c1:use:{vid}'), IB('🗑', callback_data=f'v196:c1:del:{vid}'))
    if not items:
        kb.row(IB('Версий пока нет', callback_data='none'))
    if pages > 1:
        nav = []
        if page > 0:
            nav.append(IB('⬅️', callback_data=f'v196:c1:versions:{page - 1}'))
        nav.append(IB(f'{page + 1}/{pages}', callback_data='none'))
        if page + 1 < pages:
            nav.append(IB('➡️', callback_data=f'v196:c1:versions:{page + 1}'))
        kb.row(*nav)
    kb.row(IB('⬅️ В Конструктор 1', callback_data='v196:c1:main'))
    kb.row(IB('✅ Закончить', callback_data='v196:c1:done'))
    return kb

def _v212_legacy__v196_open_c1(call, token):
    key = _v196_key_for_token(token)
    if not key:
        _v196_answer(call, 'Окно уже изменилось. Откройте его заново.', True)
        return True
    cid = int(call.message.chat.id)
    mid = int(call.message.message_id)
    base = _v196_original_rows_for_key(key)
    if not base:
        base = _v196_annotate_rows(_v196_strip_constructor_rows(_v196_rows(getattr(call.message, 'reply_markup', None))))
        _V196_LAST_BASE_BY_KEY[key] = copy.deepcopy(base)
    cfg = _v196_window_cfg(key, True)
    working = _v196_apply_profile_to_base(key, base)
    label = str(cfg.get('label') or (_V196_LAST_META_BY_TOKEN.get(token) or {}).get('label') or key)
    known = list(cfg.get('known_origins') or _v196_origins(base))
    sent = bot.send_message(cid, 'Открываю Конструктор 1…')
    session = {'kind': 'c1', 'owner_chat_id': cid, 'panel_message_id': int(sent.message_id), 'target_chat_id': cid, 'target_message_id': mid, 'window_key': key, 'window_label': label, 'token': str(token), 'working_rows': copy.deepcopy(working), 'known_origins': known, 'opened_at': _v196_now(), 'pending': None, 'selected': None, 'freeze': True}
    session['rearm'] = _v196_freeze_window(cid, mid)
    with _V196_LOCK:
        _V196_SESSIONS[int(sent.message_id)] = session
        _V196_PANEL_MESSAGES.add(int(sent.message_id))
    bot.edit_message_text(_v196_c1_text(session), chat_id=cid, message_id=int(sent.message_id), reply_markup=_v196_c1_main_keyboard(session))
    _v196_answer(call)
    return True

def _v212_legacy__v196_c2_stats_text():
    root = _v196_root(True)
    windows = root.get('windows') or {}
    custom = sum((1 for cfg in windows.values() if isinstance(cfg, dict) and isinstance(cfg.get('current_rows'), list)))
    versions = sum((len((cfg or {}).get('versions') or {}) for cfg in windows.values() if isinstance(cfg, dict)))
    return f"🛠 КОНСТРУКТОР 2 · ЦЕНТР\n\nИзвестно окон: {len(windows)}\nПользовательских профилей: {custom}\nВерсий окон: {versions}\nКаталог кнопок: {len(root.get('catalog') or {})}\nИдей: {len(root.get('ideas') or [])}\n\nЭто owner-only слой представления; бизнес-функции не заменяются."

def _v212_legacy__v196_c2_main_keyboard():
    kb = types.InlineKeyboardMarkup(row_width=2)
    kb.row(IB('🪟 Профили окон', callback_data='v196:c2:windows:0'), IB('📚 Общие версии', callback_data='v196:c2:gversions:0'))
    kb.row(IB('🧭 Каталог кнопок', callback_data='v196:c2:catalog:0'), IB('🧪 Настройки', callback_data='v196:c2:lab'))
    kb.row(IB('💡 Идеи развития', callback_data='v196:c2:ideas:0'), IB('💾 Снимок всех профилей', callback_data='v196:c2:gsave'))
    kb.row(IB('⚙️ Процессы', callback_data='process_center'), IB('📶 Трафик', callback_data='traffic_audit:month'))
    kb.row(IB('💓 Самопеленг', callback_data='keepalive_status'), IB('🌿 Ветки', callback_data='v196:c2:branches'))
    kb.row(IB('✅ Закончить', callback_data='v196:c2:done'))
    return kb

def _v212_legacy__v196_windows_rows():
    root = _v196_root(True)
    rows = []
    for key, cfg in (root.get('windows') or {}).items():
        if not isinstance(cfg, dict):
            continue
        token = _v196_token_for_key(key, str(cfg.get('label') or key))
        rows.append((str(cfg.get('label') or key), token, cfg))
    return sorted(rows, key=lambda x: x[0].casefold())

def _v196_c2_windows_keyboard(page=0):
    rows = _v196_windows_rows()
    page_size = 9
    pages = max(1, (len(rows) + page_size - 1) // page_size)
    page = max(0, min(int(page), pages - 1))
    kb = types.InlineKeyboardMarkup(row_width=1)
    for label, token, cfg in rows[page * page_size:(page + 1) * page_size]:
        icon = '✅' if isinstance(cfg.get('current_rows'), list) else '▫️'
        text = label if len(label) <= 45 else label[:44] + '…'
        kb.row(IB(f'{icon} {text}', callback_data=f'v196:c2:window:{token}'))
    if not rows:
        kb.row(IB('Окна появятся после открытия', callback_data='none'))
    if pages > 1:
        nav = []
        if page > 0:
            nav.append(IB('⬅️', callback_data=f'v196:c2:windows:{page - 1}'))
            nav.append(IB(f'{page + 1}/{pages}', callback_data='none'))
        if page + 1 < pages:
            nav.append(IB('➡️', callback_data=f'v196:c2:windows:{page + 1}'))
        kb.row(*nav)
    kb.row(IB('⬅️ Конструктор 2', callback_data='v196:c2:main'))
    kb.row(IB('✅ Закончить', callback_data='v196:c2:done'))
    return kb

def _v212_legacy__v196_c2_window_detail(token):
    key = _v196_key_for_token(token)
    cfg = _v196_window_cfg(key, False)
    versions = cfg.get('versions') or {}
    active = isinstance(cfg.get('current_rows'), list)
    text = f"🪟 ПРОФИЛЬ ОКНА\n\n{cfg.get('label') or key}\nМаркер: {cfg.get('marker') or '—'}\nПрофиль: {('✅ активен' if active else '▫️ штатный')}\nВерсий: {len(versions)}"
    kb = types.InlineKeyboardMarkup(row_width=1)
    if active:
        kb.row(IB('♻️ Сбросить профиль', callback_data=f'v196:c2:window_reset:{token}'))
    kb.row(IB('⬅️ Профили окон', callback_data='v196:c2:windows:0'))
    kb.row(IB('✅ Закончить', callback_data='v196:c2:done'))
    return (text, kb)

def _v196_c2_catalog_keyboard(page=0):
    rows = _v196_catalog_rows()
    page_size = 10
    pages = max(1, (len(rows) + page_size - 1) // page_size)
    page = max(0, min(int(page), pages - 1))
    kb = types.InlineKeyboardMarkup(row_width=1)
    dev = bool(_v196_flags().get('developer_labels'))
    for row in rows[page * page_size:(page + 1) * page_size]:
        label = str(row.get('text') or 'Кнопка')
        if dev:
            label += ' · ' + str(row.get('callback_data') or '')[:20]
        if len(label) > 54:
            label = label[:53] + '…'
        kb.row(IB(label, callback_data='none'))
    if pages > 1:
        nav = []
        if page > 0:
            nav.append(IB('⬅️', callback_data=f'v196:c2:catalog:{page - 1}'))
            nav.append(IB(f'{page + 1}/{pages}', callback_data='none'))
        if page + 1 < pages:
            nav.append(IB('➡️', callback_data=f'v196:c2:catalog:{page + 1}'))
        kb.row(*nav)
    kb.row(IB('🔎 Пересканировать исходники', callback_data=f'v196:c2:scan:{page}'))
    kb.row(IB('⬅️ Конструктор 2', callback_data='v196:c2:main'))
    kb.row(IB('✅ Закончить', callback_data='v196:c2:done'))
    return kb

def _v196_lab_keyboard():
    flags = _v196_flags()
    kb = types.InlineKeyboardMarkup(row_width=1)
    defs = [('show_c1', 'Показывать Конструктор 1'), ('show_c2', 'Показывать Конструктор 2'), ('compact_constructor_row', 'C1+C2 в одной строке'), ('apply_profiles', 'Автоприменять профили'), ('freeze_timers', 'Замораживать таймеры при редактировании'), ('preserve_new_buttons', 'Сохранять новые кнопки будущих версий'), ('observe_catalog', 'Учить каталог по открытым окнам'), ('developer_labels', 'Показывать callback в редакторе')]
    for key, label in defs:
        kb.row(IB(('✅ ' if flags.get(key) else '⬜ ') + label, callback_data=f'v196:c2:flag:{key}'))
    kb.row(IB('⬅️ Конструктор 2', callback_data='v196:c2:main'))
    kb.row(IB('✅ Закончить', callback_data='v196:c2:done'))
    return kb

def _v196_ideas_keyboard(page=0):
    ideas = list(_v196_root(True).get('ideas') or [])
    page_size = 8
    pages = max(1, (len(ideas) + page_size - 1) // page_size)
    page = max(0, min(int(page), pages - 1))
    kb = types.InlineKeyboardMarkup(row_width=1)
    for row in ideas[page * page_size:(page + 1) * page_size]:
        icon = '✅' if row.get('status') == 'ready' else '💡'
        text = str(row.get('text') or 'Идея')
        text = text if len(text) <= 42 else text[:41] + '…'
        kb.row(IB(f'{icon} {text}', callback_data=f"v196:c2:idea:{int(row.get('id') or 0)}"))
    kb.row(IB('➕ Добавить идею', callback_data='v196:c2:idea_add'))
    if pages > 1:
        nav = []
        if page > 0:
            nav.append(IB('⬅️', callback_data=f'v196:c2:ideas:{page - 1}'))
            nav.append(IB(f'{page + 1}/{pages}', callback_data='none'))
        if page + 1 < pages:
            nav.append(IB('➡️', callback_data=f'v196:c2:ideas:{page + 1}'))
        kb.row(*nav)
    kb.row(IB('⬅️ Конструктор 2', callback_data='v196:c2:main'))
    kb.row(IB('✅ Закончить', callback_data='v196:c2:done'))
    return kb

def _v212_legacy__v196_global_snapshot_save():
    root = _v196_root(True)
    versions = root.setdefault('global_versions', {})
    ids = [int(k) for k in versions if str(k).isdigit()]
    vid = max(ids or [0]) + 1
    versions[str(vid)] = {'id': vid, 'created_at': _v196_now(), 'windows': copy.deepcopy(root.get('windows') or {})}
    if len(versions) > V196_VERSION_LIMIT:
        for old in sorted([int(x) for x in versions if str(x).isdigit()])[:-V196_VERSION_LIMIT]:
            versions.pop(str(old), None)
    _v196_persist(f'global snapshot v{vid}')
    return vid

def _v196_global_versions_keyboard(page=0):
    versions = _v196_root(True).get('global_versions') or {}
    items = sorted([(int(k), v) for k, v in versions.items() if str(k).isdigit()], reverse=True)
    page_size = 8
    pages = max(1, (len(items) + page_size - 1) // page_size)
    page = max(0, min(int(page), pages - 1))
    kb = types.InlineKeyboardMarkup(row_width=2)
    for vid, row in items[page * page_size:(page + 1) * page_size]:
        kb.row(IB(f"v{vid} · {str(row.get('created_at') or '')[5:16]}", callback_data=f'v196:c2:guse:{vid}'), IB('🗑', callback_data=f'v196:c2:gdel:{vid}'))
    if not items:
        kb.row(IB('Общих версий пока нет', callback_data='none'))
    if pages > 1:
        nav = []
        if page > 0:
            nav.append(IB('⬅️', callback_data=f'v196:c2:gversions:{page - 1}'))
            nav.append(IB(f'{page + 1}/{pages}', callback_data='none'))
        if page + 1 < pages:
            nav.append(IB('➡️', callback_data=f'v196:c2:gversions:{page + 1}'))
        kb.row(*nav)
    kb.row(IB('⬅️ Конструктор 2', callback_data='v196:c2:main'))
    kb.row(IB('✅ Закончить', callback_data='v196:c2:done'))
    return kb

def _v212_legacy__v196_open_c2(call=None, token='', panel_message_id=None):
    cid = int(call.message.chat.id) if call is not None else int(OWNER_ID or 0)
    target_mid = int(call.message.message_id) if call is not None else 0
    key = _v196_key_for_token(token) if token else ''
    if panel_message_id:
        panel = int(panel_message_id)
        session = _v196_session(panel) or {}
        session.update({'kind': 'c2', 'owner_chat_id': cid, 'panel_message_id': panel, 'token': str(token or session.get('token') or ''), 'window_key': key or session.get('window_key') or ''})
        with _V196_LOCK:
            _V196_SESSIONS[panel] = session
            _V196_PANEL_MESSAGES.add(panel)
        if call is not None:
            _v196_panel_edit(call, _v196_c2_stats_text(), _v196_c2_main_keyboard())
        return True
    sent = bot.send_message(cid, _v196_c2_stats_text(), reply_markup=_v196_c2_main_keyboard())
    panel = int(sent.message_id)
    session = {'kind': 'c2', 'owner_chat_id': cid, 'panel_message_id': panel, 'target_chat_id': cid, 'target_message_id': target_mid, 'window_key': key, 'token': str(token or ''), 'opened_at': _v196_now(), 'pending': None, 'freeze': False, 'rearm': {}}
    with _V196_LOCK:
        _V196_SESSIONS[panel] = session
        _V196_PANEL_MESSAGES.add(panel)
    if call is not None:
        _v196_answer(call)
    return True

def _v212_legacy__v196_handle_c1_callback(call, raw):
    parts = raw.split(':')
    if len(parts) == 3 and parts[2] and _v196_key_for_token(parts[2]):
        return _v196_open_c1(call, parts[2])
    session = _v196_session(int(call.message.message_id))
    if not session or session.get('kind') != 'c1':
        _v196_answer(call, 'Редактор уже закрыт. Откройте Конструктор 1 из нужного окна.', True)
        return True
    cmd = parts[2] if len(parts) > 2 else ''
    try:
        bot_journal('ui_constructor_c1_callback_v208', int(OWNER_ID or 0), f"raw={raw[:500]} key={session.get('window_key')} target={session.get('target_chat_id')}:{session.get('target_message_id')} selected={session.get('selected')}")
    except Exception:
        pass
    if cmd == 'main':
        _v196_answer(call)
        _v196_panel_edit(call, _v196_c1_text(session), _v196_c1_main_keyboard(session))
        return True
    if cmd in {'remove', 'rename', 'move'}:
        page = int(parts[3]) if len(parts) > 3 and str(parts[3]).isdigit() else 0
        _v196_answer(call)
        if cmd == 'move':
            text, kb = _v207_move_preview(session)
            _v196_panel_edit(call, text, kb)
        else:
            title = {'remove': '➖ Выберите кнопку, которую убрать', 'rename': '✏️ Выберите кнопку для нового имени'}[cmd]
            _v196_panel_edit(call, title, _v196_c1_list_keyboard(session, cmd, page))
        return True
    if cmd == 'rm' and len(parts) >= 5:
        ri, bi = (int(parts[3]), int(parts[4]))
        try:
            session['working_rows'][ri].pop(bi)
            if not session['working_rows'][ri]:
                session['working_rows'].pop(ri)
            _v196_store_current(session, 'remove')
            _v196_apply_target(session)
            _v196_answer(call, 'Кнопка убрана')
        except Exception:
            _v196_answer(call, 'Кнопка уже изменилась', True)
        _v196_panel_edit(call, _v196_c1_text(session), _v196_c1_main_keyboard(session))
        return True
    if cmd == 'ren' and len(parts) >= 5:
        session['pending'] = {'kind': 'rename', 'row': int(parts[3]), 'button': int(parts[4])}
        _v196_answer(call)
        kb = types.InlineKeyboardMarkup()
        kb.row(IB('Отмена', callback_data='v196:c1:main'))
        kb.row(IB('✅ Закончить', callback_data='v196:c1:done'))
        _v196_panel_edit(call, '✏️ Отправьте следующим сообщением новое название кнопки.\nCallback и действие останутся прежними.', kb)
        return True
    if cmd == 'sel' and len(parts) >= 5:
        session['selected'] = (int(parts[3]), int(parts[4]))
        _v196_answer(call)
        text, kb = _v207_move_preview(session)
        _v196_panel_edit(call, text, kb)
        return True
    if cmd == 'mv' and len(parts) >= 4:
        changed, message = _v207_move_button(session, parts[3])
        if changed:
            _v196_store_current(session, 'move')
            _v196_apply_target(session)
            _v196_answer(call, message)
        else:
            _v196_answer(call, message, False)
        text, kb = _v207_move_preview(session)
        _v196_panel_edit(call, text, kb)
        return True
    if cmd == 'add':
        page = int(parts[3]) if len(parts) > 3 and str(parts[3]).isdigit() else 0
        _v196_answer(call)
        _v196_panel_edit(call, '➕ ДОБАВИТЬ КНОПКУ\n\nКаталог содержит только уже известные действия бота.', _v196_c1_add_keyboard(session, page))
        return True
    if cmd == 'addscan':
        page = int(parts[3]) if len(parts) > 3 and str(parts[3]).isdigit() else 0
        added = ui_constructor_scan_source_catalog(True)
        _v196_answer(call, f'Добавлено в каталог: {added}')
        _v196_panel_edit(call, '➕ ДОБАВИТЬ КНОПКУ', _v196_c1_add_keyboard(session, page))
        return True
    if cmd == 'addpick' and len(parts) >= 4:
        row = (_v196_root(True).get('catalog') or {}).get(parts[3]) or {}
        if row.get('callback_data'):
            btn = {'text': str(row.get('text') or 'Кнопка')[:100], 'callback_data': str(row.get('callback_data'))[:500], '_v196_origin': 'manual:' + str(parts[3]), '_v196_manual': True}
            session.setdefault('working_rows', []).append([btn])
            _v196_store_current(session, 'add')
            _v196_apply_target(session)
            _v196_answer(call, 'Кнопка добавлена')
        _v196_panel_edit(call, _v196_c1_text(session), _v196_c1_main_keyboard(session))
        return True
    if cmd == 'save':
        vid = _v196_save_window_version(session)
        _v196_apply_target(session)
        _v196_answer(call, f'Сохранена v{vid}')
        _v196_panel_edit(call, _v196_c1_text(session), _v196_c1_main_keyboard(session))
        return True
    if cmd == 'versions':
        page = int(parts[3]) if len(parts) > 3 and str(parts[3]).isdigit() else 0
        _v196_answer(call)
        _v196_panel_edit(call, '📚 ВЕРСИИ ЭТОГО ОКНА\n\n🎯 Контур: ' + _v212_contour_name(int(session.get('target_scope') or OWNER_ID)), _v196_versions_keyboard(session, page))
        return True
    if cmd == 'use' and len(parts) >= 4:
        vid = int(parts[3])
        cfg = _v196_window_cfg(str(session.get('window_key') or ''), True)
        row = (cfg.get('versions') or {}).get(str(vid))
        if row:
            session['working_rows'] = copy.deepcopy(row.get('rows') or [])
            session['known_origins'] = list(row.get('known_origins') or session.get('known_origins') or [])
            cfg['current_rows'] = copy.deepcopy(session['working_rows'])
            cfg['known_origins'] = list(session['known_origins'])
            cfg['active_version'] = vid
            _v196_persist(f'c1 apply v{vid}')
            _v196_apply_target(session)
            _v196_answer(call, f'Применена v{vid}')
        _v196_panel_edit(call, _v196_c1_text(session), _v196_c1_main_keyboard(session))
        return True
    if cmd == 'del' and len(parts) >= 4:
        vid = int(parts[3])
        cfg = _v196_window_cfg(str(session.get('window_key') or ''), True)
        (cfg.get('versions') or {}).pop(str(vid), None)
        if int(cfg.get('active_version') or 0) == vid:
            cfg['active_version'] = None
        _v196_persist(f'c1 delete v{vid}')
        _v196_answer(call, f'v{vid} удалена')
        _v196_panel_edit(call, '📚 ВЕРСИИ ЭТОГО ОКНА\n\n🎯 Контур: ' + _v212_contour_name(int(session.get('target_scope') or OWNER_ID)), _v196_versions_keyboard(session, 0))
        return True
    if cmd == 'reset':
        _v196_reset_session_to_original(session, True)
        _v196_answer(call, 'Штатная клавиатура восстановлена')
        _v196_panel_edit(call, _v196_c1_text(session), _v196_c1_main_keyboard(session))
        return True
    if cmd == 'to_c2':
        session['kind'] = 'c2'
        _v196_answer(call)
        _v196_open_c2(call, token=str(session.get('token') or ''), panel_message_id=int(call.message.message_id))
        return True
    if cmd == 'done':
        _v196_answer(call, 'Редактор закрыт. Обычные таймеры снова работают.')
        _v196_close_session(int(call.message.message_id), True)
        return True
    return True

def _v212_legacy__v196_handle_c2_callback(call, raw):
    parts = raw.split(':')
    if len(parts) == 3 and parts[2] and _v196_key_for_token(parts[2]):
        return _v196_open_c2(call, parts[2])
    session = _v196_session(int(call.message.message_id))
    if not session or session.get('kind') != 'c2':
        _v196_answer(call, 'Конструктор 2 уже закрыт', True)
        return True
    cmd = parts[2] if len(parts) > 2 else ''
    try:
        bot_journal('ui_constructor_c2_callback_v208', int(OWNER_ID or 0), f"raw={raw[:500]} target={session.get('target_chat_id')}:{session.get('target_message_id')}")
    except Exception:
        pass
    if cmd == 'main':
        _v196_answer(call)
        _v196_panel_edit(call, _v196_c2_stats_text(), _v196_c2_main_keyboard())
        return True
    if cmd == 'branches':
        _v196_answer(call)
        _v196_close_session(int(call.message.message_id), delete_panel=False)
        try:
            safe_edit(bot, call, build_protected_branches_text(0), reply_markup=build_protected_branches_keyboard(0))
        except Exception as exc:
            try:
                log_error(f'v196 branches shortcut: {exc}')
            except Exception:
                pass
        return True
    if cmd == 'windows':
        page = int(parts[3]) if len(parts) > 3 and str(parts[3]).isdigit() else 0
        _v196_answer(call)
        _v196_panel_edit(call, '🪟 ПРОФИЛИ ОКОН\n\n✅ — есть пользовательский профиль; ▫️ — штатный вид.', _v196_c2_windows_keyboard(page))
        return True
    if cmd == 'window' and len(parts) >= 4:
        text, kb = _v196_c2_window_detail(parts[3])
        _v196_answer(call)
        _v196_panel_edit(call, text, kb)
        return True
    if cmd == 'window_reset' and len(parts) >= 4:
        key = _v196_key_for_token(parts[3])
        cfg = _v196_window_cfg(key, True)
        cfg['current_rows'] = None
        cfg['known_origins'] = []
        cfg['active_version'] = None
        _V196_ACTIVE_WORKING_BY_KEY.pop(key, None)
        _v196_persist(f'c2 reset {key}')
        _v196_answer(call, 'Профиль сброшен')
        _v196_panel_edit(call, '🪟 ПРОФИЛИ ОКОН', _v196_c2_windows_keyboard(0))
        return True
    if cmd == 'catalog':
        page = int(parts[3]) if len(parts) > 3 and str(parts[3]).isdigit() else 0
        _v196_answer(call)
        _v196_panel_edit(call, '🧭 КАТАЛОГ КНОПОК', _v196_c2_catalog_keyboard(page))
        return True
    if cmd == 'scan':
        page = int(parts[3]) if len(parts) > 3 and str(parts[3]).isdigit() else 0
        added = ui_constructor_scan_source_catalog(True)
        _v196_answer(call, f'Добавлено: {added}')
        _v196_panel_edit(call, '🧭 КАТАЛОГ КНОПОК', _v196_c2_catalog_keyboard(page))
        return True
    if cmd == 'lab':
        _v196_answer(call)
        _v196_panel_edit(call, '🧪 НАСТРОЙКИ КОНСТРУКТОРА', _v196_lab_keyboard())
        return True
    if cmd == 'flag' and len(parts) >= 4:
        key = parts[3]
        if key in _v196_flags():
            _v196_flags()[key] = not bool(_v196_flags().get(key))
            _v196_persist(f'flag {key}={int(_v196_flags().get(key))}')
        _v196_answer(call)
        _v196_panel_edit(call, '🧪 НАСТРОЙКИ КОНСТРУКТОРА', _v196_lab_keyboard())
        return True
    if cmd == 'ideas':
        page = int(parts[3]) if len(parts) > 3 and str(parts[3]).isdigit() else 0
        _v196_answer(call)
        _v196_panel_edit(call, '💡 ИДЕИ РАЗВИТИЯ', _v196_ideas_keyboard(page))
        return True
    if cmd == 'idea_add':
        session['pending'] = {'kind': 'idea'}
        _v196_answer(call)
        kb = types.InlineKeyboardMarkup()
        kb.row(IB('Отмена', callback_data='v196:c2:ideas:0'))
        kb.row(IB('✅ Закончить', callback_data='v196:c2:done'))
        _v196_panel_edit(call, '💡 Отправьте следующим сообщением идею.', kb)
        return True
    if cmd == 'idea' and len(parts) >= 4:
        iid = int(parts[3])
        idea = next((x for x in _v196_root(True).get('ideas') or [] if int(x.get('id') or 0) == iid), None)
        if idea:
            idea['status'] = 'ready' if idea.get('status') != 'ready' else 'idea'
            _v196_persist(f'idea status {iid}')
        _v196_answer(call)
        _v196_panel_edit(call, '💡 ИДЕИ РАЗВИТИЯ', _v196_ideas_keyboard(0))
        return True
    if cmd == 'gsave':
        vid = _v196_global_snapshot_save()
        _v196_answer(call, f'Общий снимок v{vid}')
        _v196_panel_edit(call, _v196_c2_stats_text(), _v196_c2_main_keyboard())
        return True
    if cmd == 'gversions':
        page = int(parts[3]) if len(parts) > 3 and str(parts[3]).isdigit() else 0
        _v196_answer(call)
        _v196_panel_edit(call, '📚 ОБЩИЕ ВЕРСИИ ПРОФИЛЕЙ', _v196_global_versions_keyboard(page))
        return True
    if cmd == 'guse' and len(parts) >= 4:
        vid = int(parts[3])
        row = (_v196_root(True).get('global_versions') or {}).get(str(vid))
        if row and isinstance(row.get('windows'), dict):
            _v196_root(True)['windows'] = copy.deepcopy(row['windows'])
            if isinstance(row.get('scopes'), dict):
                _v196_root(True)['scopes'] = copy.deepcopy(row['scopes'])
            _V196_ACTIVE_WORKING_BY_KEY.clear()
            _v196_persist(f'global use v{vid}')
            _v196_answer(call, f'Применён общий снимок v{vid}')
        _v196_panel_edit(call, _v196_c2_stats_text(), _v196_c2_main_keyboard())
        return True
    if cmd == 'gdel' and len(parts) >= 4:
        vid = int(parts[3])
        (_v196_root(True).get('global_versions') or {}).pop(str(vid), None)
        _v196_persist(f'global delete v{vid}')
        _v196_answer(call, f'v{vid} удалён')
        _v196_panel_edit(call, '📚 ОБЩИЕ ВЕРСИИ ПРОФИЛЕЙ', _v196_global_versions_keyboard(0))
        return True
    if cmd == 'done':
        _v196_answer(call, 'Конструктор закрыт')
        _v196_close_session(int(call.message.message_id), True)
        return True
    return True

def _v212_legacy_ui_constructor_handle_message(msg):
    try:
        cid = int(msg.chat.id)
        uid = int(getattr(getattr(msg, 'from_user', None), 'id', 0) or 0)
        if cid != int(OWNER_ID or 0) or uid != int(OWNER_ID or 0) or str(getattr(msg, 'content_type', '') or '') != 'text':
            return False
        with _V196_LOCK:
            candidates = [s for s in _V196_SESSIONS.values() if int(s.get('owner_chat_id') or 0) == cid and isinstance(s.get('pending'), dict)]
        if not candidates:
            return False
        session = sorted(candidates, key=lambda s: str(s.get('opened_at') or ''))[-1]
        pending = session.get('pending') or {}
        text = str(getattr(msg, 'text', '') or '').strip()
        if not text:
            return True
        if pending.get('kind') == 'rename':
            ri = int(pending.get('row'))
            bi = int(pending.get('button'))
            session['working_rows'][ri][bi]['text'] = text[:100]
            session['pending'] = None
            _v196_store_current(session, 'rename')
            _v196_apply_target(session)
            try:
                bot.edit_message_text(_v196_c1_text(session), chat_id=cid, message_id=int(session['panel_message_id']), reply_markup=_v196_c1_main_keyboard(session))
            except Exception:
                pass
        elif pending.get('kind') == 'idea':
            root = _v196_root(True)
            iid = int(root.get('next_idea_id') or 1)
            root['next_idea_id'] = iid + 1
            root.setdefault('ideas', []).append({'id': iid, 'text': text[:1000], 'status': 'idea', 'created_at': _v196_now()})
            session['pending'] = None
            _v196_persist(f'c2 idea {iid}')
            try:
                bot.edit_message_text('💡 ИДЕИ РАЗВИТИЯ', chat_id=cid, message_id=int(session['panel_message_id']), reply_markup=_v196_ideas_keyboard(0))
            except Exception:
                pass
        else:
            return False
        try:
            bot.delete_message(cid, int(msg.message_id))
        except Exception:
            pass
        return True
    except Exception as exc:
        try:
            log_error(f'v196 constructor input: {exc}')
        except Exception:
            pass
        return True
import threading as _v212_ctor_threading
_V212_CTOR_SCOPE_LOCAL = _v212_ctor_threading.local()
_V212_LAST_BASE_BY_SCOPE_KEY = {}
_V212_CATALOG_BY_SCOPE = {}

def _v212_canonical_scope(chat_id: int) -> int:
    cid = int(chat_id or 0)
    fn = globals().get('resolve_canonical_chat_id_v199')
    if callable(fn):
        try:
            return int(fn(cid) or cid)
        except Exception:
            pass
    return cid

def _v212_scope_id(explicit=None) -> int:
    if explicit is not None:
        try:
            return _v212_canonical_scope(int(explicit))
        except Exception:
            pass
    try:
        local = int(getattr(_V212_CTOR_SCOPE_LOCAL, 'scope_id', 0) or 0)
        if local:
            return _v212_canonical_scope(local)
    except Exception:
        pass
    try:
        cid = int(current_state_chat_id() or 0)
        if cid:
            return _v212_canonical_scope(cid)
    except Exception:
        pass
    return int(OWNER_ID or 0)

def _v212_scope_root(scope_id: int, create=True):
    root = _v196_root(create)
    root['schema'] = max(2, int(root.get('schema') or 1))
    scopes = root.setdefault('scopes', {}) if create else root.get('scopes') or {}
    sid = str(_v212_canonical_scope(scope_id))
    row = scopes.get(sid)
    if not isinstance(row, dict):
        if not create:
            return {}
        row = {'scope_id': int(sid), 'windows': {}, 'snapshots': {}, 'created_at': _v196_now()}
        scopes[sid] = row
    row.setdefault('windows', {})
    row.setdefault('snapshots', {})
    return row

def _v212_legacy_cfg(key):
    cfg = (_v196_root(False).get('windows') or {}).get(str(key))
    return cfg if isinstance(cfg, dict) else {}

def _v196_windows_rows():
    """Scope-aware C2 window inventory; legacy/default keys remain visible as inherited profiles."""
    sid = _v212_scope_id()
    scope = _v212_scope_root(sid, True)
    legacy = _v196_root(True).get('windows') or {}
    scoped = scope.get('windows') or {}
    keys = set((str(k) for k in legacy.keys())) | set((str(k) for k in scoped.keys()))
    keys.update((str(k) for s, k in _V212_LAST_BASE_BY_SCOPE_KEY.keys() if int(s) == int(sid)))
    rows = []
    for key in keys:
        cfg, mode = _v212_effective_cfg(key, sid)
        label = str((cfg or {}).get('label') or (_v212_legacy_cfg(key) or {}).get('label') or key)
        token = _v196_token_for_key(key, label)
        view = copy.deepcopy(cfg or {})
        view['_v212_mode'] = mode
        view['label'] = label
        rows.append((label, token, view))
    return sorted(rows, key=lambda x: x[0].casefold())

def _v196_window_cfg(key, create=True, scope_id=None):
    sid = _v212_scope_id(scope_id)
    scope = _v212_scope_root(sid, create)
    windows = scope.setdefault('windows', {}) if create else scope.get('windows') or {}
    cfg = windows.get(str(key))
    if not isinstance(cfg, dict):
        if not create:
            return {}
        cfg = {'current_rows': None, 'known_origins': [], 'versions': {}, 'active_version': None, 'label': str(key), 'marker': '', 'mode': 'inherit'}
        windows[str(key)] = cfg
    cfg.setdefault('versions', {})
    cfg.setdefault('known_origins', [])
    cfg.setdefault('mode', 'custom' if isinstance(cfg.get('current_rows'), list) else 'inherit')
    return cfg

def _v212_effective_cfg(key, scope_id=None):
    sid = _v212_scope_id(scope_id)
    cfg = _v196_window_cfg(key, False, sid)
    if cfg and str(cfg.get('mode') or 'inherit') == 'stock':
        return (cfg, 'stock')
    if cfg and str(cfg.get('mode') or 'inherit') == 'custom' and isinstance(cfg.get('current_rows'), list):
        return (cfg, 'custom')
    legacy = _v212_legacy_cfg(key)
    if isinstance(legacy.get('current_rows'), list):
        return (legacy, 'default')
    return (cfg or legacy, 'stock')

def _v212_apply_rows_from_cfg(cfg, mode, base):
    if mode == 'stock' or not _v196_flags().get('apply_profiles', True):
        return copy.deepcopy(base)
    stored = (cfg or {}).get('current_rows')
    if not isinstance(stored, list):
        return copy.deepcopy(base)
    current_by_origin = {str(btn.get('_v196_origin') or ''): btn for row in base or [] for btn in row or [] if str(btn.get('_v196_origin') or '')}
    out = []
    used = set()
    for row in stored:
        nr = []
        for saved in row or []:
            origin = str(saved.get('_v196_origin') or '')
            cur = current_by_origin.get(origin)
            if cur is None:
                continue
            btn = copy.deepcopy(cur)
            btn['text'] = str(saved.get('text') or btn.get('text') or '')[:100]
            nr.append(btn)
            used.add(origin)
        if nr:
            out.append(nr)
    if _v196_flags().get('preserve_new_buttons', True):
        known = set((str(x) for x in (cfg or {}).get('known_origins') or []))
        for row in base or []:
            extras = [copy.deepcopy(btn) for btn in row or [] if str(btn.get('_v196_origin') or '') not in used and str(btn.get('_v196_origin') or '') not in known]
            if extras:
                out.append(extras)
    return out

def _v196_apply_profile_to_base(key, base):
    cfg, mode = _v212_effective_cfg(key)
    return _v212_apply_rows_from_cfg(cfg, mode, base)

def _v196_original_rows_for_key(key):
    sid = _v212_scope_id()
    return copy.deepcopy(_V212_LAST_BASE_BY_SCOPE_KEY.get((sid, str(key))) or _V196_LAST_BASE_BY_KEY.get(str(key)) or [])
_V212_PREV_AUGMENT_BASE = _V196_PREV_AUGMENT_MARKUP

def _canon_v160_augment_markup__002(reply_markup, text: str, chat_id=None):
    kb = _V212_PREV_AUGMENT_BASE(reply_markup, text, chat_id) if callable(_V212_PREV_AUGMENT_BASE) else reply_markup
    try:
        marker = _v196_marker(text)
        if not marker:
            return kb
        sid = _v212_scope_id()
        base = _v196_strip_constructor_rows(_v196_rows(kb))
        annotated = _v196_annotate_rows(base)
        key = _v196_window_key(text, annotated)
        label = _v196_window_label(text, key)
        token = _v196_token_for_key(key, label)
        _V196_LAST_BASE_BY_KEY[key] = copy.deepcopy(annotated)
        _V212_LAST_BASE_BY_SCOPE_KEY[sid, key] = copy.deepcopy(annotated)
        scope_cat = _V212_CATALOG_BY_SCOPE.setdefault(sid, {})
        for row in annotated:
            for btn in row or []:
                cb = str(btn.get('callback_data') or '')
                if cb:
                    scope_cat[_v196_normalize_callback(cb)] = copy.deepcopy(btn)
        _v196_catalog_capture(annotated, marker, 'observed')
        cfg = _v196_window_cfg(key, True, sid)
        cfg['label'] = label
        cfg['marker'] = marker
        cfg['last_seen_at'] = _v196_now()
        effective = _v196_apply_profile_to_base(key, annotated)
        if sid == int(OWNER_ID or 0) and _v196_owner_context():
            effective = _v196_constructor_controls(effective, token)
        return _v196_markup(effective)
    except Exception as exc:
        try:
            log_error(f'v212 constructor augment: {exc}')
        except Exception:
            pass
        return kb

def _v212_contour_name(chat_id: int) -> str:
    cid = int(chat_id)
    if cid == int(OWNER_ID or 0):
        return 'Основной владелец'
    try:
        return str(get_chat_display_name(cid) or f'Чат {cid}')
    except Exception:
        return f'Чат {cid}'

def _v212_available_contours():
    owner = int(OWNER_ID or 0)
    rows = []
    seen = set()

    def add(cid, group):
        try:
            cid = _v212_canonical_scope(int(cid))
        except Exception:
            return
        if not cid or cid in seen:
            return
        try:
            fn = globals().get('is_chat_bot_removed')
            if callable(fn) and fn(cid) and (cid != owner):
                return
        except Exception:
            pass
        seen.add(cid)
        rows.append({'chat_id': cid, 'name': _v212_contour_name(cid), 'group': group})
    add(owner, 'owner')
    for level, group in ((1, 'circle1'), (2, 'circle2')):
        fn = globals().get('_v164_all_circle_ids')
        if callable(fn):
            try:
                for cid in fn(level):
                    add(cid, group)
            except Exception:
                pass
    fn = globals().get('_v168_owner_access_ids')
    if callable(fn):
        try:
            for cid in fn():
                add(cid, 'access')
        except Exception:
            pass
    return rows

def _v212_find_live_target(scope_id: int, marker: str):
    sid = _v212_canonical_scope(scope_id)
    marker = str(marker or '').upper()
    try:
        reg = globals().get('_open_window_registry')
        values = list((reg() if callable(reg) else data.get('open_window_registry') or {}).values())
        cand = []
        for item in values:
            if not isinstance(item, dict) or int(item.get('chat_id') or 0) != sid:
                continue
            code = str(item.get('code') or '').upper()
            params = item.get('params') or {}
            if code == marker or str(params.get('marker') or '').upper() == marker:
                cand.append(item)
        if cand:
            cand.sort(key=lambda x: (int(x.get('epoch') or 0), str(x.get('updated_at') or '')), reverse=True)
            return int(cand[0].get('message_id') or 0)
    except Exception:
        pass
    return 0

def _v212_target_keyboard(session, page=0):
    rows = _v212_available_contours()
    per = 8
    pages = max(1, (len(rows) + per - 1) // per)
    page = max(0, min(int(page), pages - 1))
    current = int(session.get('target_scope') or OWNER_ID)
    kind = str(session.get('kind') or 'c1')
    kb = types.InlineKeyboardMarkup(row_width=1)
    for row in rows[page * per:(page + 1) * per]:
        cid = int(row['chat_id'])
        icon = '✅' if cid == current else '▫️'
        grp = {'owner': '👤', 'circle1': '1️⃣', 'circle2': '2️⃣', 'access': '🔐'}.get(row['group'], '▫️')
        kb.row(IB(f"{icon} {grp} {row['name'][:42]}", callback_data=f'v196:{kind}:target_pick:{cid}:{page}'))
    if pages > 1:
        nav = []
        if page > 0:
            nav.append(IB('⬅️', callback_data=f'v196:{kind}:target_page:{page - 1}'))
            nav.append(IB(f'{page + 1}/{pages}', callback_data='none'))
        if page + 1 < pages:
            nav.append(IB('➡️', callback_data=f'v196:{kind}:target_page:{page + 1}'))
            kb.row(*nav)
    kb.row(IB('⬅️ Назад', callback_data=f'v196:{kind}:main'))
    kb.row(IB('✅ Закончить', callback_data=f'v196:{kind}:done'))
    return kb

def _v212_switch_target(session, new_scope: int):
    new_scope = _v212_canonical_scope(new_scope)
    old = int(session.get('target_scope') or session.get('target_chat_id') or OWNER_ID)
    if old == new_scope:
        return
    _v196_rearm_window(session)
    session['rearm'] = {}
    session['freeze'] = False
    session['pending'] = None
    session['selected'] = None
    session['target_scope'] = new_scope
    session['target_chat_id'] = new_scope
    session['target_message_id'] = 0
    root = _v196_root(True)
    root['last_target_scope'] = str(new_scope)
    key = str(session.get('window_key') or '')
    with _v212_scope_context(new_scope):
        base = _v196_original_rows_for_key(key)
        cfg, mode = _v212_effective_cfg(key, new_scope)
        session['working_rows'] = _v212_apply_rows_from_cfg(cfg, mode, base)
        session['known_origins'] = list((cfg or {}).get('known_origins') or _v196_origins(base))
        session['window_label'] = str((cfg or {}).get('label') or session.get('window_label') or key)
        marker = str((cfg or {}).get('marker') or _v196_marker(session.get('window_label') or '') or str(key).split(':', 1)[0])
        mid = _v212_find_live_target(new_scope, marker) if (new_scope, key) in _V212_LAST_BASE_BY_SCOPE_KEY else 0
        session['target_message_id'] = mid
        if mid:
            session['freeze'] = True
            session['rearm'] = _v196_freeze_window(new_scope, mid)
    _v196_persist(f'v212 target {old}->{new_scope}')

class _v212_scope_context:

    def __init__(self, scope):
        self.scope = int(scope)
        self.prev = 0

    def __enter__(self):
        self.prev = int(getattr(_V212_CTOR_SCOPE_LOCAL, 'scope_id', 0) or 0)
        _V212_CTOR_SCOPE_LOCAL.scope_id = self.scope
        return self

    def __exit__(self, *a):
        _V212_CTOR_SCOPE_LOCAL.scope_id = self.prev

def _v196_apply_target(session):
    cid = int(session.get('target_chat_id') or session.get('target_scope') or 0)
    mid = int(session.get('target_message_id') or 0)
    if not cid or not mid:
        return True
    try:
        rows = copy.deepcopy(session.get('working_rows') or [])
        bot.edit_message_reply_markup(chat_id=cid, message_id=mid, reply_markup=_v196_markup(rows))
        return True
    except Exception as exc:
        try:
            _v196_rearm_window(session)
        except Exception:
            pass
        session['target_message_id'] = 0
        session['freeze'] = False
        session['rearm'] = {}
        try:
            bot_journal('ui_constructor_live_preview_stale_v212', int(OWNER_ID or 0), f'target={cid}:{mid}; {exc}')
        except Exception:
            pass
        return False

def _v196_store_current(session, reason='change'):
    sid = int(session.get('target_scope') or session.get('target_chat_id') or OWNER_ID)
    key = str(session.get('window_key') or '')
    with _v212_scope_context(sid):
        cfg = _v196_window_cfg(key, True, sid)
        cfg['mode'] = 'custom'
        cfg['current_rows'] = copy.deepcopy(session.get('working_rows') or [])
        cfg['known_origins'] = list(session.get('known_origins') or cfg.get('known_origins') or [])
        cfg['active_version'] = None
        cfg['updated_at'] = _v196_now()
    _v196_persist(f'c1 {reason} scope={sid} {key}')

def _v196_reset_session_to_original(session, persist=True):
    sid = int(session.get('target_scope') or OWNER_ID)
    key = str(session.get('window_key') or '')
    with _v212_scope_context(sid):
        base = _v196_original_rows_for_key(key)
        session['working_rows'] = copy.deepcopy(base)
        session['known_origins'] = _v196_origins(base)
        cfg = _v196_window_cfg(key, True, sid)
        cfg['mode'] = 'stock'
        cfg['current_rows'] = None
        cfg['known_origins'] = list(session['known_origins'])
        cfg['active_version'] = None
    if persist:
        _v196_persist(f'c1 stock reset scope={sid} {key}')
    _v196_apply_target(session)

def _v196_c1_text(session):
    sid = int(session.get('target_scope') or OWNER_ID)
    key = str(session.get('window_key') or '')
    with _v212_scope_context(sid):
        cfg, mode = _v212_effective_cfg(key, sid)
        versions = (cfg or {}).get('versions') or {}
    count = sum((len(r or []) for r in session.get('working_rows') or []))
    return '🧩 КОНСТРУКТОР 1 · ПРЕДСТАВЛЕНИЕ\n\n🎯 Контур: %s\nchat_id: %s\nОкно: %s\nРежим профиля: %s\nКнопок: %d · версий: %d\nLive-window: %s\n\nМеняется только presentation; business callback берётся из актуального runtime целевого контура.' % (_v212_contour_name(sid), sid, session.get('window_label') or key, {'custom': '🎯 свой', 'default': '🌐 общий/default', 'stock': '♻️ штатный'}.get(mode, mode), count, len(versions), '✅' if session.get('target_message_id') else '▫️ сохранение без live-window')

def _v196_c1_main_keyboard(session):
    kb = types.InlineKeyboardMarkup(row_width=2)
    sid = int(session.get('target_scope') or OWNER_ID)
    kb.row(IB(f'🎯 Контур: {_v212_contour_name(sid)[:28]}', callback_data='v196:c1:target'))
    kb.row(IB('➖ Убирать', callback_data='v196:c1:remove'), IB('➕ Добавлять', callback_data='v196:c1:add:0'))
    kb.row(IB('✏️ Имена', callback_data='v196:c1:rename'), IB('↔️ Места', callback_data='v196:c1:move'))
    kb.row(IB('💾 Сохранить версию', callback_data='v196:c1:save'), IB('📚 Версии', callback_data='v196:c1:versions:0'))
    kb.row(IB('♻️ Штатный вид', callback_data='v196:c1:reset'), IB('🛠 Конструктор 2', callback_data='v196:c1:to_c2'))
    kb.row(IB('✅ Закончить', callback_data='v196:c1:done'))
    return kb

def _v196_open_c1(call, token):
    key = _v196_key_for_token(token)
    if not key:
        _v196_answer(call, 'Окно уже изменилось. Откройте его заново.', True)
        return True
    owner = int(call.message.chat.id)
    owner_mid = int(call.message.message_id)
    sid = _v212_canonical_scope(int(_v196_root(True).get('last_target_scope') or OWNER_ID))
    if sid not in {int(x['chat_id']) for x in _v212_available_contours()}:
        sid = int(OWNER_ID or 0)
    with _v212_scope_context(sid):
        base = _v196_original_rows_for_key(key)
        if not base and sid == owner:
            base = _v196_annotate_rows(_v196_strip_constructor_rows(_v196_rows(getattr(call.message, 'reply_markup', None))))
            _V212_LAST_BASE_BY_SCOPE_KEY[sid, key] = copy.deepcopy(base)
            _V196_LAST_BASE_BY_KEY[key] = copy.deepcopy(base)
        cfg, mode = _v212_effective_cfg(key, sid)
        working = _v212_apply_rows_from_cfg(cfg, mode, base)
        label = str((cfg or {}).get('label') or (_V196_LAST_META_BY_TOKEN.get(token) or {}).get('label') or key)
        known = list((cfg or {}).get('known_origins') or _v196_origins(base))
        marker = str((cfg or {}).get('marker') or str(key).split(':', 1)[0])
        target_mid = owner_mid if sid == owner else _v212_find_live_target(sid, marker) if (sid, key) in _V212_LAST_BASE_BY_SCOPE_KEY else 0
    sent = bot.send_message(owner, 'Открываю Конструктор 1…')
    session = {'kind': 'c1', 'owner_chat_id': owner, 'panel_message_id': int(sent.message_id), 'target_scope': sid, 'target_chat_id': sid, 'target_message_id': target_mid, 'window_key': key, 'window_label': label, 'token': str(token), 'working_rows': copy.deepcopy(working), 'known_origins': known, 'opened_at': _v196_now(), 'pending': None, 'selected': None, 'freeze': bool(target_mid), 'rearm': {}}
    if target_mid:
        session['rearm'] = _v196_freeze_window(sid, target_mid)
    with _V196_LOCK:
        _V196_SESSIONS[int(sent.message_id)] = session
        _V196_PANEL_MESSAGES.add(int(sent.message_id))
    bot.edit_message_text(_v196_c1_text(session), chat_id=owner, message_id=int(sent.message_id), reply_markup=_v196_c1_main_keyboard(session))
    _v196_answer(call)
    return True

def _v196_c2_stats_text():
    root = _v196_root(True)
    sid = int(getattr(_V212_CTOR_SCOPE_LOCAL, 'scope_id', 0) or root.get('last_target_scope') or OWNER_ID)
    scope = _v212_scope_root(sid, True)
    windows = scope.get('windows') or {}
    custom = sum((1 for x in windows.values() if isinstance(x, dict) and str(x.get('mode')) == 'custom' and isinstance(x.get('current_rows'), list)))
    return f"🛠 КОНСТРУКТОР 2 · ЦЕНТР\n\n🎯 Сейчас редактируется: {_v212_contour_name(sid)}\nchat_id: {sid}\n\nПрофилей контура: {custom}/{len(windows)}\nГлобальный/default каталог: {len(root.get('windows') or {})} окон\nКаталог кнопок: {len(root.get('catalog') or {})}\n\nНастройки процессов/трафика/keepalive/веток ниже остаются глобальными owner/system."

def _v196_c2_main_keyboard():
    sid = _v212_scope_id()
    kb = types.InlineKeyboardMarkup(row_width=2)
    kb.row(IB(f'🎯 Контур: {_v212_contour_name(sid)[:28]}', callback_data='v196:c2:target'))
    kb.row(IB('🪟 Профили окон', callback_data='v196:c2:windows:0'), IB('📚 Снимки контура', callback_data='v196:c2:scope_versions:0'))
    kb.row(IB('🧭 Каталог кнопок', callback_data='v196:c2:catalog:0'), IB('🧪 Настройки', callback_data='v196:c2:lab'))
    kb.row(IB('💾 Снимок контура', callback_data='v196:c2:ssave'), IB('🌐 Снимок всех контуров', callback_data='v196:c2:gsave'))
    kb.row(IB('🌐 Глобальные снимки', callback_data='v196:c2:gversions:0'))
    kb.row(IB('⚙️ Процессы', callback_data='process_center'), IB('📶 Трафик', callback_data='traffic_audit:month'))
    kb.row(IB('💓 Самопеленг', callback_data='keepalive_status'), IB('🌿 Ветки', callback_data='v196:c2:branches'))
    kb.row(IB('✅ Закончить', callback_data='v196:c2:done'))
    return kb

def _v196_open_c2(call=None, token='', panel_message_id=None):
    cid = int(call.message.chat.id) if call is not None else int(OWNER_ID or 0)
    root = _v196_root(True)
    sid = _v212_canonical_scope(int(root.get('last_target_scope') or OWNER_ID))
    key = _v196_key_for_token(token) if token else ''
    if panel_message_id:
        panel = int(panel_message_id)
        session = _v196_session(panel) or {}
        session.update({'kind': 'c2', 'owner_chat_id': cid, 'panel_message_id': panel, 'target_scope': int(session.get('target_scope') or sid), 'target_chat_id': int(session.get('target_scope') or sid), 'token': str(token or session.get('token') or ''), 'window_key': key or session.get('window_key') or ''})
        with _V196_LOCK:
            _V196_SESSIONS[panel] = session
            _V196_PANEL_MESSAGES.add(panel)
        with _v212_scope_context(int(session['target_scope'])):
            if call is not None:
                _v196_panel_edit(call, _v196_c2_stats_text(), _v196_c2_main_keyboard())
        return True
    sent = bot.send_message(cid, 'Открываю Конструктор 2…')
    panel = int(sent.message_id)
    session = {'kind': 'c2', 'owner_chat_id': cid, 'panel_message_id': panel, 'target_scope': sid, 'target_chat_id': sid, 'target_message_id': 0, 'window_key': key, 'token': str(token or ''), 'opened_at': _v196_now(), 'pending': None, 'freeze': False, 'rearm': {}}
    with _V196_LOCK:
        _V196_SESSIONS[panel] = session
        _V196_PANEL_MESSAGES.add(panel)
    with _v212_scope_context(sid):
        bot.edit_message_text(_v196_c2_stats_text(), chat_id=cid, message_id=panel, reply_markup=_v196_c2_main_keyboard())
    if call is not None:
        _v196_answer(call)
        return True
    return True

def _v212_scope_snapshot_save(scope_id: int):
    scope = _v212_scope_root(scope_id, True)
    versions = scope.setdefault('snapshots', {})
    ids = [int(x) for x in versions if str(x).isdigit()]
    vid = max(ids or [0]) + 1
    versions[str(vid)] = {'id': vid, 'created_at': _v196_now(), 'scope_id': int(scope_id), 'windows': copy.deepcopy(scope.get('windows') or {})}
    _v196_persist(f'scope snapshot {scope_id} v{vid}')
    return vid

def _v212_scope_snapshots_keyboard(scope_id: int, page: int=0):
    sid = _v212_canonical_scope(scope_id)
    versions = _v212_scope_root(sid, True).get('snapshots') or {}
    ids = sorted((int(k) for k in versions if str(k).isdigit()), reverse=True)
    per = 7
    pages = max(1, (len(ids) + per - 1) // per)
    page = max(0, min(int(page or 0), pages - 1))
    kb = types.InlineKeyboardMarkup(row_width=2)
    for vid in ids[page * per:(page + 1) * per]:
        row = versions.get(str(vid)) or {}
        when = str(row.get('created_at') or '')[:16].replace('T', ' ')
        kb.row(IB(f'✅ v{vid} · {when}', callback_data=f'v196:c2:suse:{vid}'), IB('🗑', callback_data=f'v196:c2:sdel:{vid}'))
    if not ids:
        kb.row(IB('Снимков этого контура пока нет', callback_data='none'))
    if pages > 1:
        nav = []
        if page > 0:
            nav.append(IB('⬅️', callback_data=f'v196:c2:scope_versions:{page - 1}'))
        nav.append(IB(f'{page + 1}/{pages}', callback_data='none'))
        if page + 1 < pages:
            nav.append(IB('➡️', callback_data=f'v196:c2:scope_versions:{page + 1}'))
        kb.row(*nav)
    kb.row(IB('💾 Сохранить снимок сейчас', callback_data='v196:c2:ssave'))
    kb.row(IB('⬅️ Конструктор 2', callback_data='v196:c2:main'))
    kb.row(IB('✅ Закончить', callback_data='v196:c2:done'))
    return kb

def _v212_scope_snapshot_apply(scope_id: int, version_id: int) -> bool:
    sid = _v212_canonical_scope(scope_id)
    scope = _v212_scope_root(sid, True)
    row = (scope.get('snapshots') or {}).get(str(int(version_id)))
    if not isinstance(row, dict) or not isinstance(row.get('windows'), dict):
        return False
    scope['windows'] = copy.deepcopy(row.get('windows') or {})
    _V196_ACTIVE_WORKING_BY_KEY.clear()
    _v196_persist(f'scope snapshot apply {sid} v{int(version_id)}')
    return True

def _v212_scope_snapshot_delete(scope_id: int, version_id: int) -> bool:
    sid = _v212_canonical_scope(scope_id)
    versions = _v212_scope_root(sid, True).setdefault('snapshots', {})
    existed = versions.pop(str(int(version_id)), None) is not None
    if existed:
        _v196_persist(f'scope snapshot delete {sid} v{int(version_id)}')
    return existed

def _v196_global_snapshot_save():
    root = _v196_root(True)
    versions = root.setdefault('global_versions', {})
    ids = [int(k) for k in versions if str(k).isdigit()]
    vid = max(ids or [0]) + 1
    versions[str(vid)] = {'id': vid, 'created_at': _v196_now(), 'windows': copy.deepcopy(root.get('windows') or {}), 'scopes': copy.deepcopy(root.get('scopes') or {})}
    _v196_persist(f'global scoped snapshot v{vid}')
    return vid
_V212_PREV_C1_HANDLER = _v212_legacy__v196_handle_c1_callback

def _canon_v196_handle_c1_callback__001(call, raw):
    session = _v196_session(int(call.message.message_id))
    parts = str(raw).split(':')
    cmd = parts[2] if len(parts) > 2 else ''
    if session and session.get('kind') == 'c1':
        if cmd == 'target':
            _v196_answer(call)
            _v196_panel_edit(call, '🎯 ВЫБЕРИТЕ КОНТУР\n\nПрофили каждого chat_id независимы.', _v212_target_keyboard(session, 0))
            return True
        if cmd == 'target_page':
            page = int(parts[3]) if len(parts) > 3 and str(parts[3]).isdigit() else 0
            _v196_answer(call)
            _v196_panel_edit(call, '🎯 ВЫБЕРИТЕ КОНТУР', _v212_target_keyboard(session, page))
            return True
        if cmd == 'target_pick' and len(parts) > 3:
            target = int(parts[3])
            _v212_switch_target(session, target)
            _v196_answer(call, f'Контур: {_v212_contour_name(target)}')
            with _v212_scope_context(target):
                _v196_panel_edit(call, _v196_c1_text(session), _v196_c1_main_keyboard(session))
                return True
        sid = int(session.get('target_scope') or OWNER_ID)
        if cmd == 'addpick' and len(parts) >= 4:
            row = (_v196_root(True).get('catalog') or {}).get(parts[3]) or {}
            norm = _v196_normalize_callback(str(row.get('callback_data') or ''))
            actual = (_V212_CATALOG_BY_SCOPE.get(sid) or {}).get(norm)
            if not actual:
                _v196_answer(call, 'В выбранном контуре актуальный business callback этой кнопки ещё не наблюдался. Сначала откройте штатное окно с этой функцией.', True)
                return True
            btn = copy.deepcopy(actual)
            btn['text'] = str(row.get('text') or btn.get('text') or 'Кнопка')[:100]
            session.setdefault('working_rows', []).append([btn])
            _v196_store_current(session, 'add-runtime-safe')
            _v196_apply_target(session)
            _v196_answer(call, 'Кнопка добавлена с callback выбранного контура')
            _v196_panel_edit(call, _v196_c1_text(session), _v196_c1_main_keyboard(session))
            return True
        with _v212_scope_context(sid):
            return _V212_PREV_C1_HANDLER(call, raw)
    return _V212_PREV_C1_HANDLER(call, raw)
_V212_PREV_C2_HANDLER = _v212_legacy__v196_handle_c2_callback

def _canon_v196_handle_c2_callback__001(call, raw):
    session = _v196_session(int(call.message.message_id))
    parts = str(raw).split(':')
    cmd = parts[2] if len(parts) > 2 else ''
    if session and session.get('kind') == 'c2':
        sid = int(session.get('target_scope') or OWNER_ID)
        if cmd == 'target':
            _v196_answer(call)
            _v196_panel_edit(call, '🎯 ВЫБЕРИТЕ КОНТУР', _v212_target_keyboard(session, 0))
            return True
        if cmd == 'target_page':
            page = int(parts[3]) if len(parts) > 3 and str(parts[3]).isdigit() else 0
            _v196_answer(call)
            _v196_panel_edit(call, '🎯 ВЫБЕРИТЕ КОНТУР', _v212_target_keyboard(session, page))
            return True
        if cmd == 'target_pick' and len(parts) > 3:
            target = int(parts[3])
            _v212_switch_target(session, target)
            _v196_answer(call, f'Контур: {_v212_contour_name(target)}')
            with _v212_scope_context(target):
                _v196_panel_edit(call, _v196_c2_stats_text(), _v196_c2_main_keyboard())
                return True
        if cmd == 'ssave':
            vid = _v212_scope_snapshot_save(sid)
            _v196_answer(call, f'Снимок контура {_v212_contour_name(sid)}: v{vid}')
            with _v212_scope_context(sid):
                _v196_panel_edit(call, '📚 СНИМКИ ВЫБРАННОГО КОНТУРА\n\n🎯 ' + _v212_contour_name(sid), _v212_scope_snapshots_keyboard(sid, 0))
                return True
        if cmd == 'scope_versions':
            page = int(parts[3]) if len(parts) > 3 and str(parts[3]).isdigit() else 0
            _v196_answer(call)
            with _v212_scope_context(sid):
                _v196_panel_edit(call, '📚 СНИМКИ ВЫБРАННОГО КОНТУРА\n\n🎯 ' + _v212_contour_name(sid), _v212_scope_snapshots_keyboard(sid, page))
                return True
        if cmd == 'suse' and len(parts) >= 4:
            vid = int(parts[3])
            ok = _v212_scope_snapshot_apply(sid, vid)
            _v196_answer(call, f'Применён снимок {_v212_contour_name(sid)} v{vid}' if ok else 'Снимок не найден', not ok)
            with _v212_scope_context(sid):
                _v196_panel_edit(call, _v196_c2_stats_text(), _v196_c2_main_keyboard())
                return True
        if cmd == 'sdel' and len(parts) >= 4:
            vid = int(parts[3])
            ok = _v212_scope_snapshot_delete(sid, vid)
            _v196_answer(call, f'Удалён снимок {_v212_contour_name(sid)} v{vid}' if ok else 'Снимок не найден', not ok)
            with _v212_scope_context(sid):
                _v196_panel_edit(call, '📚 СНИМКИ ВЫБРАННОГО КОНТУРА\n\n🎯 ' + _v212_contour_name(sid), _v212_scope_snapshots_keyboard(sid, 0))
                return True
        if cmd in {'window_inherit', 'window_stock', 'window_custom'} and len(parts) >= 4:
            key = _v196_key_for_token(parts[3])
            cfg = _v196_window_cfg(key, True, sid)
            if cmd == 'window_inherit':
                cfg['mode'] = 'inherit'
                cfg['current_rows'] = None
            elif cmd == 'window_stock':
                cfg['mode'] = 'stock'
                cfg['current_rows'] = None
            else:
                base = _V212_LAST_BASE_BY_SCOPE_KEY.get((sid, key)) or _V196_LAST_BASE_BY_KEY.get(key) or []
                eff = _v196_apply_profile_to_base(key, base)
                cfg['mode'] = 'custom'
                cfg['current_rows'] = copy.deepcopy(eff)
                cfg['known_origins'] = _v196_origins(base)
            _v196_persist(f"scope mode {sid} {key} {cfg['mode']}")
            _v196_answer(call, 'Режим профиля изменён')
            return True
        with _v212_scope_context(sid):
            return _V212_PREV_C2_HANDLER(call, raw)
    return _V212_PREV_C2_HANDLER(call, raw)
_V212_PREV_C2_WINDOW_DETAIL = _v212_legacy__v196_c2_window_detail

def _v196_c2_window_detail(token):
    key = _v196_key_for_token(token)
    sid = _v212_scope_id()
    cfg, mode = _v212_effective_cfg(key, sid)
    text, kb = _V212_PREV_C2_WINDOW_DETAIL(token)
    text += f'\nКонтур: {_v212_contour_name(sid)}\nИсточник вида: {mode}'
    kb2 = types.InlineKeyboardMarkup()
    kb2.row(IB('🎯 Свой профиль', callback_data=f'v196:c2:window_custom:{token}'))
    kb2.row(IB('🌐 Общий/default', callback_data=f'v196:c2:window_inherit:{token}'), IB('♻️ Штатный вид', callback_data=f'v196:c2:window_stock:{token}'))
    kb2.row(IB('⬅️ Профили окон', callback_data='v196:c2:windows:0'))
    kb2.row(IB('✅ Закончить', callback_data='v196:c2:done'))
    return (text, kb2)
_V212_PREV_CTOR_MESSAGE = _v212_legacy_ui_constructor_handle_message

def _canon_ui_constructor_handle_message__001(msg):
    try:
        cid = int(msg.chat.id)
        with _V196_LOCK:
            candidates = [s for s in _V196_SESSIONS.values() if int(s.get('owner_chat_id') or 0) == cid and isinstance(s.get('pending'), dict)]
        if candidates:
            session = sorted(candidates, key=lambda s: str(s.get('opened_at') or ''))[-1]
            with _v212_scope_context(int(session.get('target_scope') or OWNER_ID)):
                return _V212_PREV_CTOR_MESSAGE(msg)
    except Exception:
        pass
    return _V212_PREV_CTOR_MESSAGE(msg)
def _constructor_extension_callback(call, data_str: str):
    raw = str(data_str or '')
    try:
        if raw.startswith('v196:'):
            if not _v196_can_manage_call(call):
                _v196_answer(call, 'Конструкторы доступны только основному владельцу.', True)
                return True
            if raw.startswith('v196:c1:'):
                return bool(_v196_handle_c1_callback(call, raw))
            if raw.startswith('v196:c2:'):
                return bool(_v196_handle_c2_callback(call, raw))
            return True
        if int(getattr(call.message, 'message_id', 0) or 0) in _V196_PANEL_MESSAGES:
            _v196_close_session(int(call.message.message_id), delete_panel=False)
    except Exception as exc:
        try:
            log_error(f'v196 callback pre-route: {exc}')
        except Exception:
            pass
    return False

@bot.message_handler(commands=['constructor2', 'constructor'])
def v196_constructor_command(msg):
    try:
        cid = int(msg.chat.id)
        uid = int(getattr(getattr(msg, 'from_user', None), 'id', 0) or 0)
        if cid != int(OWNER_ID or 0) or uid != int(OWNER_ID or 0):
            return
        _v196_open_c2(None, '', None)
        try:
            bot.delete_message(cid, int(msg.message_id))
        except Exception:
            pass
    except Exception as exc:
        try:
            log_error(f'/constructor: {exc}')
        except Exception:
            pass
try:
    WINDOW_MARKER_CONSTANTS.update({'v196:c1:*': 'Ф242', 'v196:c2:*': 'Ф243', 'keepalive_self_*': 'Ф253', 'keepalive_peer*': 'Ф254'})
except Exception:
    pass
try:
    ui_constructor_scan_source_catalog(False)
except Exception:
    pass
try:
    _canon_bot_journal__001('ui_constructor_v196_ready', int(OWNER_ID or 0), 'constructor1+constructor2 presentation layer installed in v205')
except Exception:
    pass

def _v213_ctor_timer_key(panel_message_id: int) -> str:
    return f'v213-input-constructor:{int(panel_message_id)}'

def _v213_ctor_cancel_timer(panel_message_id: int) -> None:
    try:
        DELAYED_SCHEDULER.cancel(_v213_ctor_timer_key(panel_message_id))
    except Exception:
        pass

def _v213_ctor_schedule_pending(session: dict) -> None:
    if not isinstance(session, dict):
        return
    panel = int(session.get('panel_message_id') or 0)
    if not panel:
        return
    pending = session.get('pending')
    if not isinstance(pending, dict):
        _v213_ctor_cancel_timer(panel)
        return
    gen = int(session.get('v213_pending_generation') or 0) + 1
    session['v213_pending_generation'] = gen
    delay = float(internal_timer_seconds('interactive_input_idle', 300))
    _v213_ctor_cancel_timer(panel)

    def _expire():
        live = _v196_session(panel)
        if not isinstance(live, dict) or int(live.get('v213_pending_generation') or 0) != gen or (not isinstance(live.get('pending'), dict)):
            return
        live['pending'] = None
        try:
            cid = int(live.get('owner_chat_id') or OWNER_ID or 0)
            if str(live.get('kind')) == 'c1':
                bot.edit_message_text(_v196_c1_text(live), chat_id=cid, message_id=panel, reply_markup=_v196_c1_main_keyboard(live))
            else:
                bot.edit_message_text(_v196_c2_stats_text(), chat_id=cid, message_id=panel, reply_markup=_v196_c2_main_keyboard())
            send_and_auto_delete(cid, '⌛ Ввод Конструктора отменён по таймеру.', 7)
        except Exception:
            pass
    DELAYED_SCHEDULER.schedule(_v213_ctor_timer_key(panel), delay, _expire)
_V213_PREV_C1_CALLBACK = _canon_v196_handle_c1_callback__001

def _v213_v196_handle_c1_callback(call, raw):
    result = _V213_PREV_C1_CALLBACK(call, raw)
    try:
        _v213_ctor_schedule_pending(_v196_session(int(call.message.message_id)))
    except Exception:
        pass
    return result
_V213_PREV_C2_CALLBACK = _canon_v196_handle_c2_callback__001

def _v213_v196_handle_c2_callback(call, raw):
    result = _V213_PREV_C2_CALLBACK(call, raw)
    try:
        _v213_ctor_schedule_pending(_v196_session(int(call.message.message_id)))
    except Exception:
        pass
    return result
_V213_PREV_CTOR_MESSAGE = _canon_ui_constructor_handle_message__001

def _v213_ui_constructor_handle_message(msg):
    result = _V213_PREV_CTOR_MESSAGE(msg)
    try:
        cid = int(msg.chat.id)
        with _V196_LOCK:
            sessions = [s for s in _V196_SESSIONS.values() if int(s.get('owner_chat_id') or 0) == cid]
        for session in sessions:
            _v213_ctor_schedule_pending(session)
    except Exception:
        pass
    return result
# v262
