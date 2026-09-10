# v262
GOMONKI_INSERT_TOKEN = 'GOMONKI'
USD_RATE_URL = os.getenv('USD_RATE_URL', 'https://dolarapi.com/v1/dolares/blue').strip()
USD_RATE_CACHE_SECONDS = max(300, int(os.getenv('USD_RATE_CACHE_SECONDS', '1800') or '1800'))

def _v85_enabled(feature: str) -> bool:
    """Доступность функций v85+ определяется самим активным профилем.

    Старый жёсткий список профилей обрывался на v97. Поэтому в современных
    профилях v119-v127 кнопка «Гомонковые» отображалась, но callback молча
    завершался. version_mode_feature() уже является единственным источником
    истины и корректно работает для новых и исторических профилей.
    """
    try:
        return bool(version_mode_feature(feature))
    except Exception as exc:
        log_error(f'v85 feature gate {feature}: {exc}')
        return False

def _gomonk_currency(chat_id: int, currency: str | None=None) -> str:
    explicit = str(currency or '').strip().lower()
    if explicit in {'usd', 'ars'}:
        return explicit
    try:
        store = get_chat_store(int(chat_id))
        settings = store.setdefault('settings', {})
        is_usd = bool(usd_transactions_view_enabled(int(chat_id)) or financial_view_is_usd(store) or str(settings.get('currency_mode') or '').lower() == 'usd' or (str(settings.get('_active_currency_ledger') or '').lower() == 'usd'))
        return 'usd' if is_usd else 'ars'
    except Exception:
        return 'ars'

def _gomonk_is_usd_view(chat_id: int) -> bool:
    return _gomonk_currency(chat_id) == 'usd'

def _gomonk_keys(chat_id: int, currency: str | None=None) -> tuple[str, str, str]:
    if _gomonk_currency(chat_id, currency) == 'usd':
        return ('usd_gomonk_enabled', 'usd_gomonk_entries', 'usd_remaining_with_gomonk')
    return ('gomonk_enabled', 'gomonk_entries', 'remaining_with_gomonk')

def _gomonk_settings(chat_id: int, currency: str | None=None) -> dict:
    settings = get_chat_store(int(chat_id)).setdefault('settings', {})
    enabled_key, entries_key, remaining_key = _gomonk_keys(chat_id, currency)
    settings.setdefault(enabled_key, False)
    settings.setdefault(entries_key, [])
    settings.setdefault(remaining_key, True)
    settings.setdefault('gomonk_enabled', False)
    settings.setdefault('gomonk_entries', [])
    settings.setdefault('remaining_with_gomonk', True)
    settings.setdefault('usd_gomonk_enabled', False)
    settings.setdefault('usd_gomonk_entries', [])
    settings.setdefault('usd_remaining_with_gomonk', True)
    return settings

def gomonk_enabled(chat_id: int, currency: str | None=None) -> bool:
    settings = _gomonk_settings(chat_id, currency)
    enabled_key, _entries_key, _remaining_key = _gomonk_keys(chat_id, currency)
    return bool(settings.get(enabled_key, False))

def gomonk_entries(chat_id: int, currency: str | None=None) -> list[dict]:
    settings = _gomonk_settings(chat_id, currency)
    _enabled_key, entries_key, _remaining_key = _gomonk_keys(chat_id, currency)
    out = []
    for item in settings.get(entries_key) or []:
        if not isinstance(item, dict):
            continue
        try:
            amount = abs(float(item.get('amount', 0) or 0))
        except Exception:
            continue
        name = str(item.get('name') or 'Сумма').strip() or 'Сумма'
        if amount:
            out.append({'name': name[:80], 'amount': amount})
    return out

def _gomonk_target_key(chat_id: int, currency: str | None=None) -> str:
    return 'usd_gomonk_target_total_v209' if _gomonk_currency(chat_id, currency) == 'usd' else 'gomonk_target_total_v209'

def gomonk_configured_entries_total(chat_id: int, currency: str | None=None) -> float:
    return sum((float(x.get('amount', 0) or 0) for x in gomonk_entries(chat_id, currency)))

def _gomonk_derive_legacy_target(settings: dict, currency: str, current_total: float) -> float:
    """Recover the last user-defined reserve before v150/v151 physically consumed entries.

    Auto-cover history forms continuous reserve_before -> reserve_after chains. A manual edit
    breaks that chain. We therefore use the beginning of the LAST continuous segment, not the
    historical maximum (which could resurrect an intentionally lowered old reserve).
    """
    rows = []
    for key in ('gomonk_rebalance_history_v151', 'gomonk_rebalance_history_v150'):
        for row in settings.get(key) or []:
            if isinstance(row, dict) and str(row.get('currency') or 'ars').lower() == currency:
                try:
                    rows.append({'before': max(0.0, float(row.get('reserve_before', 0) or 0)), 'after': max(0.0, float(row.get('reserve_after', 0) or 0))})
                except Exception:
                    pass
        if rows:
            break
    if not rows:
        return max(0.0, float(current_total or 0))
    last = rows[-1]
    if abs(float(current_total or 0) - float(last.get('after', 0) or 0)) > 1e-06:
        return max(0.0, float(current_total or 0))
    segment_start = float(last.get('before', 0) or 0)
    expected_before = segment_start
    for prev in reversed(rows[:-1]):
        if abs(float(prev.get('after', 0) or 0) - expected_before) > 1e-06:
            break
        segment_start = float(prev.get('before', 0) or 0)
        expected_before = segment_start
    return max(float(current_total or 0), segment_start)

def gomonk_target_total(chat_id: int, currency: str | None=None) -> float:
    cid = int(chat_id)
    cur = _gomonk_currency(cid, currency)
    settings = _gomonk_settings(cid, cur)
    key = _gomonk_target_key(cid, cur)
    if key in settings:
        try:
            return max(0.0, float(settings.get(key, 0) or 0))
        except Exception:
            return 0.0
    current = gomonk_configured_entries_total(cid, cur)
    target = _gomonk_derive_legacy_target(settings, cur, current)
    settings[key] = target
    settings[('usd_' if cur == 'usd' else '') + 'gomonk_target_migrated_v209'] = {'at': now_local().isoformat(timespec='seconds'), 'entries_total': current, 'target_total': target}
    try:
        bot_journal('gomonk_constant_target_migrated_v209', cid, f'currency={cur}; entries={current}; target={target}')
    except Exception:
        pass
    try:
        save_data(data, chat_ids=[cid])
        schedule_config_backup_for_chats(cid, delay=0.5)
    except Exception:
        pass
    return target

def gomonk_total(chat_id: int, currency: str | None=None) -> float:
    return gomonk_target_total(chat_id, currency)

def gomonk_effective_reserve(chat_id: int, balance: float, currency: str | None=None) -> float:
    if not gomonk_enabled(int(chat_id), currency):
        return 0.0
    target = gomonk_total(int(chat_id), currency)
    return min(target, max(0.0, float(balance or 0)))

def gomonk_turnover_after_reserve(chat_id: int, balance: float, currency: str | None=None) -> float:
    b = float(balance or 0)
    return b - gomonk_effective_reserve(int(chat_id), b, currency)

def toggle_gomonk_enabled(chat_id: int, currency: str | None=None) -> bool:
    settings = _gomonk_settings(chat_id, currency)
    enabled_key, _entries_key, _remaining_key = _gomonk_keys(chat_id, currency)
    settings[enabled_key] = not bool(settings.get(enabled_key, False))
    save_data(data, chat_ids=[int(chat_id)])
    schedule_config_backup_for_chats(int(chat_id))
    return bool(settings[enabled_key])

def _v177_legacy_0158_parse_gomonk_entries(text: str) -> list[dict]:
    raw = sanitize_telegram_inserted_text(str(text or ''))
    raw = re.sub('(?is)^\\s*\\(?\\s*GOMONKI\\s*\\)?\\s*[:|\\-]*\\s*', '', raw).strip()
    parts = [p.strip() for p in raw.split(':') if p.strip()]
    result = []
    for idx, part in enumerate(parts, start=1):
        number_pattern = '(?<![A-Za-zА-Яа-яЁё0-9_])[-+]?(?:\\d{1,3}(?:[ .]\\d{3})+(?:,\\d+)?|\\d+(?:[.,]\\d+)?)'
        matches = list(re.finditer(number_pattern, part))
        if not matches:
            continue
        match = matches[-1]
        num_text = match.group(0).replace(' ', '').replace('.', '').replace(',', '.')
        try:
            amount = abs(float(num_text))
        except Exception:
            continue
        name = (part[:match.start()] + ' ' + part[match.end():]).strip(' -–—,.;')
        if not name:
            name = f'Сумма {idx}'
        if amount:
            result.append({'name': name[:80], 'amount': amount})
    return result
try:
    _v177_legacy_0158_parse_gomonk_entries.__name__ = 'parse_gomonk_entries'
except Exception:
    pass

def set_gomonk_entries(chat_id: int, entries: list[dict], currency: str | None=None):
    cid = int(chat_id)
    cur = _gomonk_currency(cid, currency)
    settings = _gomonk_settings(cid, cur)
    _enabled_key, entries_key, _remaining_key = _gomonk_keys(cid, cur)
    settings[entries_key] = list(entries or [])[:30]
    settings[_gomonk_target_key(cid, cur)] = gomonk_configured_entries_total(cid, cur)
    settings[('usd_' if cur == 'usd' else '') + 'gomonk_target_migrated_v209'] = {'at': now_local().isoformat(timespec='seconds'), 'explicit': True, 'target_total': settings[_gomonk_target_key(cid, cur)]}
    save_data(data, chat_ids=[cid])
    schedule_config_backup_for_chats(cid, delay=1.0)

def gomonk_toggle_label(chat_id: int, currency: str | None=None) -> str:
    cur = _gomonk_currency(chat_id, currency).upper()
    return f'✅ Гомонковые {cur} ВКЛ' if gomonk_enabled(chat_id, currency) else f'⬜ Гомонковые {cur} ВЫКЛ'

def gomonk_info_label(chat_id: int, currency: str | None=None) -> str:
    cur = _gomonk_currency(chat_id, currency).upper()
    return f'🧳 Гомонковые {cur} ВКЛ' if gomonk_enabled(chat_id, currency) else f'🧳 Гомонковые {cur} ВЫКЛ'

def _ensure_currency_ledgers(store: dict) -> str:
    """Инициализирует независимые ARS/USD контуры без потери старых данных."""
    settings = store.setdefault('settings', {})
    active = str(settings.get('_active_currency_ledger') or '').lower()
    if active not in {'ars', 'usd'}:
        active = 'ars'
        settings['_active_currency_ledger'] = active
        store.setdefault('ars_records', copy.deepcopy(store.get('records', []) or []))
        store.setdefault('ars_daily_records', copy.deepcopy(store.get('daily_records', {}) or {}))
        store.setdefault('ars_balance', float(store.get('balance', 0) or 0))
        store.setdefault('ars_next_id', int(store.get('next_id', 1) or 1))
    store.setdefault('usd_records', [])
    store.setdefault('usd_daily_records', {})
    store.setdefault('usd_balance', 0.0)
    store.setdefault('usd_next_id', 1)
    return active

def _snapshot_active_currency_ledger(store: dict, ledger: str | None=None) -> None:
    ledger = ledger or _ensure_currency_ledgers(store)
    if ledger not in {'ars', 'usd'}:
        return
    store[f'{ledger}_records'] = copy.deepcopy(store.get('records', []) or [])
    store[f'{ledger}_daily_records'] = copy.deepcopy(store.get('daily_records', {}) or {})
    store[f'{ledger}_balance'] = float(store.get('balance', 0) or 0)
    store[f'{ledger}_next_id'] = int(store.get('next_id', 1) or 1)

def _load_currency_ledger(store: dict, ledger: str) -> None:
    ledger = 'usd' if str(ledger).lower() == 'usd' else 'ars'
    store['records'] = copy.deepcopy(store.get(f'{ledger}_records', []) or [])
    store['daily_records'] = copy.deepcopy(store.get(f'{ledger}_daily_records', {}) or {})
    store['balance'] = float(store.get(f'{ledger}_balance', 0) or 0)
    store['next_id'] = int(store.get(f'{ledger}_next_id', 1) or 1)
    store.setdefault('settings', {})['_active_currency_ledger'] = ledger

def active_currency_ledger_from_store(store: dict | None) -> str:
    try:
        return _ensure_currency_ledgers(store or {})
    except Exception:
        return 'ars'

def active_currency_ledger(chat_id: int) -> str:
    return active_currency_ledger_from_store(get_chat_store(int(chat_id)))

def _switch_currency_ledger(chat_id: int, target: str) -> bool:
    """Переключает основной рабочий набор records/daily_records на выбранную валюту."""
    store = get_chat_store(int(chat_id))
    current = _ensure_currency_ledgers(store)
    target = 'usd' if str(target).lower() == 'usd' else 'ars'
    if current == target:
        return False
    _snapshot_active_currency_ledger(store, current)
    _load_currency_ledger(store, target)
    return True

def currency_mode(chat_id: int) -> str:
    """Режим финансовых окон: ARS, ARS-USD (ARS с эквивалентом), либо отдельный USD-контур."""
    try:
        store = get_chat_store(int(chat_id))
        settings = store.setdefault('settings', {})
        mode = str(settings.get('currency_mode') or '').strip().lower()
        if mode not in {'ars', 'ars_usd', 'usd'}:
            mode = 'ars_usd' if bool(settings.get('usd_display_enabled', False)) else 'ars'
            settings['currency_mode'] = mode
        _ensure_currency_ledgers(store)
        return mode
    except Exception:
        return 'ars'

def currency_mode_from_store(store: dict | None) -> str:
    try:
        settings = (store or {}).setdefault('settings', {})
        mode = str(settings.get('currency_mode') or '').strip().lower()
        if mode not in {'ars', 'ars_usd', 'usd'}:
            mode = 'ars_usd' if bool(settings.get('usd_display_enabled', False)) else 'ars'
        return mode
    except Exception:
        return 'ars'

def set_currency_mode(chat_id: int, mode: str):
    mode = str(mode or 'ars').strip().lower()
    if mode not in {'ars', 'ars_usd', 'usd'}:
        mode = 'ars'
    chat_id = int(chat_id)
    store = get_chat_store(chat_id)
    target_ledger = 'usd' if mode == 'usd' else 'ars'
    _switch_currency_ledger(chat_id, target_ledger)
    settings = store.setdefault('settings', {})
    settings['currency_mode'] = mode
    settings['usd_display_enabled'] = mode != 'ars'
    _snapshot_active_currency_ledger(store, target_ledger)
    save_data(data, chat_ids=[chat_id])
    schedule_config_backup_for_chats(chat_id)
    if mode == 'ars_usd':
        GENERAL_TASK_POOL.submit('usd-rate-refresh', usd_rate_cached, False)

def currency_mode_label(chat_id: int) -> str:
    labels = {'ars': 'ARS', 'ars_usd': 'ARS-USD', 'usd': 'USD'}
    return f"💵 Доллар: {labels.get(currency_mode(chat_id), 'ARS')}"

def currency_menu_text(chat_id: int) -> str:
    mode = currency_mode(chat_id)
    labels = {'ars': 'ARS — только песо', 'ars_usd': 'ARS-USD — песо и доллар в скобках', 'usd': 'USD — все суммы только в долларах'}
    rate_info = usd_rate_cached(force=False) if mode != 'ars' else None
    lines = ['💱 Валюта финансовых окон', '', f"Текущий режим: {labels.get(mode, labels['ars'])}", '', 'ARS — все значения в аргентинских песо.', 'ARS-USD — основная сумма в песо, рядом эквивалент в долларах.', 'USD — финансовые значения выводятся только в долларах.']
    if rate_info and rate_info.get('rate'):
        lines.extend(['', f"Курс: 1 USD = {fmt_num(rate_info.get('rate')).lstrip('+')} ARS"])
    return wm_common('\n'.join(lines), 9)

def build_currency_menu_keyboard(chat_id: int):
    current = currency_mode(chat_id)
    kb = types.InlineKeyboardMarkup(row_width=1)
    for mode, label in (('ars', 'ARS'), ('ars_usd', 'ARS-USD'), ('usd', 'USD')):
        mark = '✅' if current == mode else '▫️'
        kb.row(IB(f'{mark} {label}', callback_data=f'currency_select:{mode}'))
    kb.row(IB('⏪', callback_data='currency_back'))
    return kb

def usd_display_enabled(chat_id: int) -> bool:
    """Совместимость со старым v86: True для ARS-USD и USD."""
    return currency_mode(int(chat_id)) != 'ars'

def set_usd_display_enabled(chat_id: int, enabled: bool):
    set_currency_mode(int(chat_id), 'ars_usd' if enabled else 'ars')

def toggle_usd_display(chat_id: int) -> bool:
    new_mode = 'ars' if currency_mode(int(chat_id)) != 'ars' else 'ars_usd'
    set_currency_mode(int(chat_id), new_mode)
    return new_mode != 'ars'

def usd_display_label(chat_id: int) -> str:
    return currency_mode_label(chat_id)

def remaining_ost_label_enabled(chat_id: int) -> bool:
    try:
        return bool(get_chat_store(int(chat_id)).setdefault('settings', {}).get('remaining_show_ost_label', True))
    except Exception:
        return True

def toggle_remaining_ost_label(chat_id: int) -> bool:
    store = get_chat_store(int(chat_id))
    settings = store.setdefault('settings', {})
    new_value = not bool(settings.get('remaining_show_ost_label', True))
    settings['remaining_show_ost_label'] = new_value
    save_data(data, chat_ids=[int(chat_id)])
    schedule_config_backup_for_chats(int(chat_id))
    return new_value

def fmt_usd_compact(amount: float, rate_info: dict | None, signed: bool=True, absolute: bool=False) -> str:
    """Конвертация ARS→USD для режима ARS-USD."""
    if not rate_info or not rate_info.get('rate'):
        return '$—'
    amount = float(amount or 0)
    value = int(round(abs(amount) / float(rate_info['rate'])))
    if absolute or not signed:
        sign = ''
    else:
        sign = '+' if amount >= 0 else '-'
    return f'{sign}${value:,}'.replace(',', ' ')

def fmt_usd_native(amount: float, signed: bool=True, absolute: bool=False) -> str:
    """Формат суммы, которая уже хранится в отдельном USD-контуре."""
    amount = float(amount or 0)
    value = abs(amount)
    if abs(value - round(value)) < 1e-09:
        body = f'{int(round(value)):,}'.replace(',', ' ')
    else:
        body = f'{value:,.2f}'.replace(',', ' ').rstrip('0').rstrip('.')
    sign = '' if absolute or not signed else '+' if amount >= 0 else '-'
    return f'{sign}${body}'

def format_chat_amount(chat_id: int, amount: float, mixed_space: bool=False) -> str:
    """Единый формат: ARS, ARS-USD либо нативные суммы отдельного USD-контура."""
    mode = currency_mode(int(chat_id))
    if mode == 'ars':
        return fmt_num(amount)
    if mode == 'usd':
        return fmt_usd_native(amount, signed=True)
    rate_info = usd_rate_cached(force=False)
    spacer = ' ' if mixed_space else ''
    return f'{fmt_num(amount)}{spacer}({fmt_usd_compact(amount, rate_info, signed=False, absolute=True)})'

def format_store_amount(store: dict, amount: float, mixed_space: bool=False, ars_plain: bool=False) -> str:
    mode = currency_mode_from_store(store)
    if mode == 'ars':
        return fmt_num_plain(amount) if ars_plain else fmt_num(amount)
    if mode == 'usd':
        return fmt_usd_native(amount, signed=not ars_plain, absolute=ars_plain)
    rate_info = usd_rate_cached(force=False)
    ars = fmt_num_plain(amount) if ars_plain else fmt_num(amount)
    spacer = ' ' if mixed_space else ''
    return f'{ars}{spacer}({fmt_usd_compact(amount, rate_info, signed=False, absolute=True)})'

def format_category_amount(store: dict, amount: float, category_mixed: bool=False) -> str:
    mode = currency_mode_from_store(store)
    if mode == 'usd':
        return fmt_usd_native(amount, signed=False, absolute=True)
    rate_info = usd_rate_cached(force=False) if mode == 'ars_usd' or category_mixed else None
    ars = fmt_num_plain(amount)
    if mode == 'ars_usd' or category_mixed:
        return f'{ars} ({fmt_usd_compact(amount, rate_info, signed=False, absolute=True)})'
    return ars

def gomonk_summary_lines(chat_id: int, currency: str | None=None) -> list[str]:
    currency = _gomonk_currency(chat_id, currency)
    if not (_v85_enabled('gomonk_wallets') and gomonk_enabled(chat_id, currency)):
        return []
    store = get_chat_store(chat_id)
    balance = usd_balance_for_chat(chat_id) if currency == 'usd' and usd_transactions_view_enabled(chat_id) else float(store.get('balance', 0) or 0)
    target = gomonk_total(chat_id, currency)
    effective = gomonk_effective_reserve(chat_id, balance, currency)
    turnover = balance - effective
    fmt = (lambda value: fmt_usd_native(value)) if currency == 'usd' else lambda value: format_chat_amount(chat_id, value, mixed_space=True)
    lines = ['', f'🧮 Сумма гомонковых {currency.upper()} (константа): {fmt(target)}']
    if effective + 1e-09 < target:
        lines.append(f'🧳 Доступно сейчас в резерве: {fmt(effective)}')
    lines.append(f'🏦 Остаток в обороте: {fmt(turnover)}')
    return lines

def _v177_legacy_0159_build_gomonk_menu_text(chat_id: int, currency: str | None=None) -> str:
    currency = _gomonk_currency(chat_id, currency)
    entries = gomonk_entries(chat_id, currency)
    currency_label = currency.upper()
    target = gomonk_total(chat_id, currency)
    entries_total = gomonk_configured_entries_total(chat_id, currency)
    lines = [f'🧳 Гомонковые • {currency_label}', '', 'ARS и USD хранятся отдельно. Итог — константа: расходы не уменьшают заданный резерв; при пополнении доступная часть автоматически восстанавливается.', 'Формат нескольких сумм через двоеточие:', 'Имя1 1000 : Имя2 5777 : 3000', '', f"Режим: {('✅ ВКЛ' if gomonk_enabled(chat_id, currency) else '⬜ ВЫКЛ')}"]
    fmt = (lambda value: fmt_usd_native(value)) if currency == 'usd' else fmt_num
    if entries:
        lines.append('Сохранено:')
        for item in entries:
            lines.append(f"• {item['name']}: {fmt(item['amount'])}")
        if target > entries_total + 1e-09:
            lines.append(f'• ↩️ Восстанавливаемая часть старого резерва: {fmt(target - entries_total)}')
        lines.append(f'Итого (константа): {fmt(target)}')
    else:
        lines.append(f'Сохранённых сумм пока нет. Итого (константа): {fmt(target)}')
    return wm_common('\n'.join(lines), 9)
try:
    _v177_legacy_0159_build_gomonk_menu_text.__name__ = 'build_gomonk_menu_text'
except Exception:
    pass

def _v177_legacy_0160_build_gomonk_menu_keyboard(chat_id: int, currency: str | None=None):
    currency = _gomonk_currency(chat_id, currency)
    kb = types.InlineKeyboardMarkup(row_width=1)
    kb.row(IB(gomonk_toggle_label(chat_id, currency), callback_data=f'gomonk_toggle:{currency}'))
    template = f'({GOMONKI_INSERT_TOKEN}|{currency.upper()})\nИмя1 1000 : Имя2 5777'
    kb.row(make_copy_or_inline_button('💰 Сумма', template, viewer_chat_id=chat_id))
    kb.row(IB('🔙 Назад в Инфо', callback_data=f'gomonk_back:{currency}'))
    return kb
try:
    _v177_legacy_0160_build_gomonk_menu_keyboard.__name__ = 'build_gomonk_menu_keyboard'
except Exception:
    pass

def _v177_legacy_0161_handle_gomonk_insert_message(msg) -> bool:
    if getattr(msg, 'content_type', None) != 'text' or not _v85_enabled('gomonk_wallets'):
        return False
    raw = str(getattr(msg, 'text', '') or '')
    if GOMONKI_INSERT_TOKEN not in raw.upper():
        return False
    _durable_note_source_consumed('gomonk_insert')
    chat_id = int(msg.chat.id)
    token = re.search('\\(GOMONKI\\|(USD|ARS)\\)', raw, flags=re.IGNORECASE)
    currency = token.group(1).lower() if token else _gomonk_currency(chat_id)
    cleaned = re.sub('\\(GOMONKI\\|(?:USD|ARS)\\)', '', raw, flags=re.IGNORECASE)
    entries = parse_gomonk_entries(cleaned)
    try:
        bot.delete_message(chat_id, msg.message_id)
    except Exception:
        pass
    if not entries:
        send_and_auto_delete(chat_id, '❌ Не нашёл сумм. Пример: Имя1 1000 : Имя2 5777', 12)
        return True
    set_gomonk_entries(chat_id, entries, currency)
    settings = _gomonk_settings(chat_id, currency)
    enabled_key, _entries_key, _remaining_key = _gomonk_keys(chat_id, currency)
    settings[enabled_key] = True
    save_data(data, chat_ids=[chat_id])
    total = gomonk_total(chat_id, currency)
    shown = fmt_usd_native(total) if currency == 'usd' else fmt_num(total)
    bot_journal('gomonk_values_saved', chat_id, f'currency={currency} count={len(entries)} total={total}')
    send_and_auto_delete(chat_id, f'✅ Гомонковые {currency.upper()} сохранены: {len(entries)}, сумма {shown}', 10)
    try:
        open_gomonk_window(chat_id, currency=currency)
        finance_changed(chat_id, get_chat_store(chat_id).get('current_view_day') or today_key(), reason='gomonk_update', delay=0.05)
    except Exception:
        pass
    return True
try:
    _v177_legacy_0161_handle_gomonk_insert_message.__name__ = 'handle_gomonk_insert_message'
except Exception:
    pass

def open_gomonk_window(chat_id: int, message_id: int | None=None, currency: str | None=None):
    currency = _gomonk_currency(chat_id, currency)
    if message_id:
        fast_ui_edit_message_text(chat_id, message_id, build_gomonk_menu_text(chat_id, currency), reply_markup=build_gomonk_menu_keyboard(chat_id, currency), purpose='gomonk_window')
    else:
        send_or_edit_stored_window(chat_id, 'info_msg_id', build_gomonk_menu_text(chat_id, currency), reply_markup=build_gomonk_menu_keyboard(chat_id, currency), delay=None)

def _opening_balance_before_day(store: dict, day_key: str, chat_id: int | None=None) -> float:
    """Official opening balance before ``day_key``.

    v195 keeps ONE runtime authority with Excel/Google: when the canonical export
    helper is loaded, the remaining window calls that exact helper too.  The
    fallback below exists only for bootstrap/isolated tests and sums the stored
    accounting ledger losslessly; it never re-parses historical source text.
    """
    canonical = globals().get('_excel_canonical_opening_balance')
    if callable(canonical) and chat_id is not None:
        try:
            return float(canonical(int(chat_id), 'ars', str(day_key or '')[:10], 0, False))
        except Exception:
            pass
    total = 0.0
    target = str(day_key or '')[:10]
    try:
        rows = sorted(store.get('records', []) or [], key=record_sort_key)
    except Exception:
        rows = list(store.get('records', []) or [])
    for rec in rows:
        if not isinstance(rec, dict):
            continue
        try:
            if _record_day_key(rec) >= target:
                break
            total += float(rec.get('amount', 0) or 0)
        except Exception:
            continue
    return float(total)

def _remaining_state(chat_id: int, currency: str | None=None) -> bool:
    settings = _gomonk_settings(int(chat_id), currency)
    _enabled_key, _entries_key, remaining_key = _gomonk_keys(int(chat_id), currency)
    return bool(settings.get(remaining_key, True))

def _set_remaining_state(chat_id: int, enabled: bool, currency: str | None=None) -> bool:
    """Atomically set remaining-window gomonk mode to an explicit state."""
    cid = int(chat_id)
    cur = _gomonk_currency(cid, currency)
    with data_lock:
        settings = _gomonk_settings(cid, cur)
        _enabled_key, _entries_key, remaining_key = _gomonk_keys(cid, cur)
        settings[remaining_key] = bool(enabled)
        value = bool(settings[remaining_key])
    return value

def _toggle_remaining_state(chat_id: int, currency: str | None=None) -> bool:
    cid = int(chat_id)
    cur = _gomonk_currency(cid, currency)
    with data_lock:
        settings = _gomonk_settings(cid, cur)
        _enabled_key, _entries_key, remaining_key = _gomonk_keys(cid, cur)
        settings[remaining_key] = not bool(settings.get(remaining_key, True))
        value = bool(settings[remaining_key])
    return value

def _persist_remaining_state_async(chat_id: int) -> None:
    """Persist after the visible Telegram update; never block the button on MEGA."""
    cid = int(chat_id)

    def _persist():
        try:
            save_data(data, chat_ids=[cid])
        except Exception as exc:
            try:
                log_error(f'remaining state save {cid}: {exc}')
            except Exception:
                pass
        try:
            schedule_config_backup_for_chats(cid, delay=0.5)
        except Exception:
            pass
    try:
        pool = globals().get('GENERAL_TASK_POOL')
        submit_unique = getattr(pool, 'submit_unique', None) if pool is not None else None
        if callable(submit_unique):
            if submit_unique(f'remaining-state-save:{cid}', _persist):
                return
        if pool is not None and hasattr(pool, 'submit'):
            pool.submit(f'remaining-state-save:{cid}', _persist)
            return
    except Exception:
        pass
    _persist()

def build_remaining_text(chat_id: int, day_key: str, with_gomonk: bool | None=None) -> str:
    store = get_chat_store(chat_id)
    currency = _gomonk_currency(chat_id)
    settings = _gomonk_settings(chat_id, currency)
    _enabled_key, _entries_key, remaining_key = _gomonk_keys(chat_id, currency)
    if with_gomonk is None:
        with_gomonk = bool(settings.get(remaining_key, True))
    gomonk_is_on = bool(gomonk_enabled(chat_id, currency))
    reserve_total = gomonk_total(chat_id, currency) if gomonk_is_on else 0.0
    reserve = reserve_total if bool(with_gomonk) else 0.0
    view_usd = currency == 'usd' and usd_transactions_view_enabled(int(chat_id))
    if view_usd:
        canonical_open = globals().get('_excel_canonical_opening_balance')
        canonical_range = globals().get('_excel_canonical_records_for_range')
        canonical_all = globals().get('_v151_all_records')
        if callable(canonical_open) and callable(canonical_range) and callable(canonical_all):
            running = float(canonical_open(int(chat_id), 'usd', str(day_key), 0, False))
            day_records = list(canonical_range(int(chat_id), 'usd', str(day_key), str(day_key)) or [])
            current_balance = sum((float(r.get('_v151_amount', 0) or 0) for r in canonical_all(int(chat_id), 'usd') or []))
            canonical_mode = True
        else:
            running = 0.0
            for rec in sorted(store.get('records', []) or [], key=record_sort_key):
                try:
                    if _record_day_key(rec) >= str(day_key):
                        break
                    if financial_view_record_visible(store, rec):
                        running += float(rec.get('usd_amount', 0) or 0)
                except Exception:
                    pass
            day_records = usd_records_for_day(int(chat_id), str(day_key))
            current_balance = usd_balance_for_chat(int(chat_id))
            canonical_mode = False
        amount_fmt = lambda value: fmt_usd_native(value)
    else:
        running = _opening_balance_before_day(store, str(day_key), chat_id=int(chat_id))
        day_records = sorted((store.get('daily_records', {}) or {}).get(str(day_key), []) or [], key=record_sort_key)
        current_balance = float(store.get('balance', 0) or 0)
        canonical_mode = False
        amount_fmt = lambda value: format_chat_amount(chat_id, value, mixed_space=False)
    lines = [f'🧮 Остаток после каждой операции • {currency.upper()}', f'📅 {fmt_date_ddmmyy(day_key)}', f"Режим: {('с гомонковыми' if bool(with_gomonk) else 'без гомонковых')}", '']
    show_ost = remaining_ost_label_enabled(chat_id)
    shown = 0
    for rec in day_records:
        try:
            if view_usd and canonical_mode:
                amount = float(rec.get('_v151_amount', rec.get('usd_amount', 0)) or 0)
            elif view_usd:
                amount = float(rec.get('usd_amount', 0) or 0)
            else:
                amount = float(rec.get('amount', 0) or 0)
        except Exception:
            continue
        running += amount
        shown += 1
        rid = rec.get('usd_short_id') or f"U{rec.get('id', '')}" if view_usd else rec.get('short_id') or f"R{rec.get('id', '')}"
        if view_usd and canonical_mode:
            note_raw = rec.get('_v151_note', rec.get('usd_note') or rec.get('note')) or ''
        else:
            note_raw = rec.get('usd_note') or rec.get('note') or '' if view_usd else rec.get('note') or ''
        note = html.escape(str(note_raw).strip())
        if bool(with_gomonk) and gomonk_is_on:
            active_reserve = min(reserve_total, max(0.0, float(running or 0)))
            after = float(running or 0) - active_reserve
        else:
            after = float(running or 0)
        label = 'ост:' if show_ost else ''
        lines.append(f'{rid} {amount_fmt(amount)} {note} ({label}{amount_fmt(after)})'.rstrip())
    if not shown:
        lines.append(f'За этот день операций {currency.upper()} нет.')
    if bool(with_gomonk) and gomonk_is_on:
        current_active_reserve = min(reserve_total, max(0.0, float(current_balance or 0)))
        current_remaining = float(current_balance or 0) - current_active_reserve
    else:
        current_active_reserve = 0.0
        current_remaining = float(current_balance or 0)
    lines.extend(['', f'🏦 Текущий остаток по чату: {amount_fmt(current_remaining)}'])
    if bool(with_gomonk) and gomonk_is_on:
        lines.append(f'🧳 Гомонковые {currency.upper()} (константа): {amount_fmt(reserve_total)}')
        if current_active_reserve + 1e-09 < reserve_total:
            lines.append(f'🧳 Доступно сейчас: {amount_fmt(current_active_reserve)}')
    return wm_common('\n'.join(lines), 9, html_mode=True)

def build_remaining_keyboard(chat_id: int, day_key: str, with_gomonk: bool | None=None):
    currency = _gomonk_currency(chat_id)
    settings = _gomonk_settings(chat_id, currency)
    _enabled_key, _entries_key, remaining_key = _gomonk_keys(chat_id, currency)
    with_g = bool(settings.get(remaining_key, True)) if with_gomonk is None else bool(with_gomonk)
    try:
        dt = datetime.strptime(day_key, '%Y-%m-%d')
    except Exception:
        dt = now_local()
        day_key = dt.strftime('%Y-%m-%d')
    prev_key = (dt - timedelta(days=1)).strftime('%Y-%m-%d')
    next_key = (dt + timedelta(days=1)).strftime('%Y-%m-%d')
    kb = types.InlineKeyboardMarkup(row_width=3)
    if effective_main_financial_value_buttons_enabled(chat_id):
        for rec in financial_value_records_for_day(chat_id, day_key)[:84]:
            try:
                rid = int(rec.get('id'))
            except Exception:
                continue
            kb.row(IB(financial_record_button_label(rec, chat_id), callback_data=f'd:{day_key}:value_rec_{rid}'))
    nav = [IB('⬅️ День', callback_data=f'remaining_open:{prev_key}')]
    if day_key != today_key():
        nav.append(IB('📅 Сегодня', callback_data=f'remaining_open:{today_key()}'))
    nav.append(IB('День ➡️', callback_data=f'remaining_open:{next_key}'))
    kb.row(*nav)
    target = 0 if with_g else 1
    kb.row(IB('Без гомонковых' if with_g else 'С гомонковыми', callback_data=f'remaining_toggle:{day_key}:{target}'))
    kb.row(IB('⬅️ Назад осн. окно', callback_data=f'd:{day_key}:back_main'), IB('❌ Закрыть', callback_data='aux_close'))
    return kb

def open_remaining_window(chat_id: int, day_key: str, message_id: int | None=None, with_gomonk: bool | None=None):
    text = build_remaining_text(chat_id, day_key, with_gomonk=with_gomonk)
    kb = build_remaining_keyboard(chat_id, day_key, with_gomonk=with_gomonk)
    if message_id:
        fast_ui_edit_message_text(chat_id, message_id, text, reply_markup=kb, parse_mode='HTML', purpose='remaining_window')
    else:
        send_or_edit_stored_window(chat_id, 'remaining_msg_id', text, reply_markup=kb, parse_mode='HTML', delay=None)

def _clean_category_display_name(value: str) -> str:
    s = str(value or '').strip()
    s = re.sub('(?i)@[A-Za-z0-9_]{3,}\\s*', '', s)
    return re.sub('\\s+', ' ', s).strip(' :,-')

def usd_rate_cached(force: bool=False) -> dict | None:
    gs = data.setdefault('_global_settings', {})
    cache = gs.get('usd_rate_cache') if isinstance(gs.get('usd_rate_cache'), dict) else {}
    gate = globals().get('external_access_allowed_v233')
    if callable(gate) and (not gate('currency')):
        try:
            logger_fn = globals().get('external_block_log_v233')
            if callable(logger_fn):
                logger_fn('currency', 'usd_rate')
        except Exception:
            pass
        return cache if cache.get('rate') else None
    age = time.time() - float(cache.get('fetched_ts', 0) or 0)
    if not force and cache.get('rate') and (age < USD_RATE_CACHE_SECONDS):
        return cache
    if not force:
        kv_get = globals().get('kv_get_json_v248')
        if callable(kv_get):
            try:
                shared_cache = kv_get('cache:usd_rate', None)
                if isinstance(shared_cache, dict) and shared_cache.get('rate'):
                    shared_age = time.time() - float(shared_cache.get('fetched_ts', 0) or 0)
                    if shared_age < USD_RATE_CACHE_SECONDS:
                        gs['usd_rate_cache'] = dict(shared_cache)
                        return dict(shared_cache)
            except Exception:
                pass
    if threading.current_thread().name.startswith('webhook'):
        GENERAL_TASK_POOL.submit('usd-rate-refresh', usd_rate_cached, True)
        return cache if cache.get('rate') else None
    try:
        resp = requests.get(USD_RATE_URL, timeout=8)
        resp.raise_for_status()
        payload = resp.json()
        rate = float(payload.get('venta') or payload.get('promedio') or payload.get('compra') or 0)
        if rate <= 0:
            raise ValueError('курс venta отсутствует')
        cache = {'rate': rate, 'source': str(payload.get('nombre') or payload.get('casa') or 'DolarAPI dólar blue'), 'fetched_at': str(payload.get('fechaActualizacion') or now_local().isoformat(timespec='seconds')), 'fetched_ts': time.time(), 'url': USD_RATE_URL}
        gs['usd_rate_cache'] = cache
        kv_set = globals().get('kv_set_json_v248')
        if callable(kv_set):
            try:
                kv_set('cache:usd_rate', cache, USD_RATE_CACHE_SECONDS)
            except Exception:
                pass
        save_data(data, root_only=True)
        bot_journal('usd_rate_updated', None, f"rate={rate} source={cache['source']} shared_kv={bool(callable(kv_set))}")
        return cache
    except Exception as e:
        bot_journal('usd_rate_error', None, str(e), 'WARN')
        return cache if cache.get('rate') else None

def _usd_rate_refresh_tick():
    try:
        gate = globals().get('external_access_allowed_v233')
        if not (callable(gate) and (not gate('currency'))):
            usd_rate_cached(force=True)
    except Exception:
        pass
    finally:
        try:
            DELAYED_SCHEDULER.schedule('usd-rate-refresh', USD_RATE_CACHE_SECONDS, _usd_rate_refresh_tick)
        except Exception:
            pass

def _usd_rate_refresh_loop():
    return _usd_rate_refresh_tick()

def fmt_usd_from_ars(amount: float, rate_info: dict | None) -> str:
    """Совместимый короткий USD-формат для старых окон."""
    return fmt_usd_compact(amount, rate_info, signed=False, absolute=True)

def usd_transactions_view_enabled(chat_id: int) -> bool:
    try:
        return bool(get_chat_store(int(chat_id)).setdefault('settings', {}).get('usd_transactions_view', False))
    except Exception:
        return False

def set_usd_transactions_view(chat_id: int, enabled: bool):
    store = get_chat_store(int(chat_id))
    store.setdefault('settings', {})['usd_transactions_view'] = bool(enabled)
    save_data(data, chat_ids=[int(chat_id)])
    schedule_config_backup_for_chats(int(chat_id))

def toggle_usd_transactions_view(chat_id: int) -> bool:
    new_value = not usd_transactions_view_enabled(int(chat_id))
    set_usd_transactions_view(int(chat_id), new_value)
    return new_value

def usd_transactions_toggle_label(chat_id: int) -> str:
    return '🇦🇷 ARS операции' if usd_transactions_view_enabled(int(chat_id)) else '💵 USD операции'

def ensure_usd_migration_for_chat(chat_id: int) -> int:
    """Однократно подхватывает USD из старых v92-записей текущей базы.

    Новые v93-записи сразу имеют usd_amount. Для старых реконструируем исходную строку
    из amount + note и применяем тот же парсер. Миграция не создаёт дублей.
    """
    store = get_chat_store(int(chat_id))
    settings = store.setdefault('settings', {})
    if settings.get('usd_transactions_migrated_v93'):
        return 0
    changed = 0
    with locked_chat(int(chat_id)):
        for rec in store.get('records', []) or []:
            if rec.get('usd_amount') is not None:
                continue
            note = str(rec.get('note') or '').strip()
            low = note.casefold()
            likely = bool(re.search('usd|усд|\\$', low) or (('к' in low or re.search('\\bk\\b', low)) and (USD_EXCHANGE_RE.search(low) or re.search('\\bот\\b', low) or '+к' in low or ('+k' in low))))
            if not likely:
                continue
            try:
                old_amount = float(rec.get('amount', 0) or 0)
            except Exception:
                old_amount = 0.0
            if re.search('(?i)(?:^|\\s)и\\s*\\+[kк]\\b', low):
                rec['usd_amount'] = abs(old_amount) * 1000.0
                rec['usd_note'] = ''
                rec['usd_only'] = True
                rec['source_finance_text'] = f'И {fmt_num_compact(abs(old_amount))}+к'
                rec['amount'] = 0.0
                changed += 1
                continue
            sign = '+' if old_amount > 0 else ''
            amount_text = fmt_num_compact(abs(old_amount))
            explicit_note_usd = extract_usd_transaction(note)
            if explicit_note_usd is None and re.search('(?i)(?:usd|усд|\\$)', note):
                if USD_EXCHANGE_RE.search(low):
                    sign = ''
                insert_value = sign + amount_text
                mcur = re.search('(?i)(?P<mult>[kк]\\s*)?(?P<cur>usd|усд|\\$)', note)
                if mcur:
                    replacement = insert_value + (mcur.group('mult') or '') + mcur.group('cur')
                    reconstructed = (note[:mcur.start()] + replacement + note[mcur.end():]).strip()
                else:
                    reconstructed = f'{insert_value} {note}'.strip()
            else:
                reconstructed = f'{sign}{amount_text} {note}'.strip()
            try:
                comp = parse_financial_components(reconstructed)
            except Exception:
                continue
            if comp.get('usd_amount') is None:
                continue
            rec['usd_amount'] = float(comp.get('usd_amount') or 0)
            rec['usd_note'] = str(comp.get('usd_note') or '')
            rec['usd_only'] = bool(comp.get('usd_only', False))
            rec['source_finance_text'] = reconstructed
            rec['amount'] = float(comp.get('amount', 0) or 0)
            rec['note'] = str(comp.get('note') or rec.get('note') or '')
            changed += 1
        settings['usd_transactions_migrated_v93'] = True
        if changed:
            normalize_chat_records(int(chat_id))
            recalc_balance(int(chat_id))
            rebuild_month_short_ids(int(chat_id))
            rebuild_global_records()
        save_data(data, chat_ids=[int(chat_id)])
    if changed:
        try:
            bot_journal('usd_v93_migration', int(chat_id), f'records={changed}')
        except Exception:
            pass
    return changed

def usd_records_for_month(chat_id: int, month_key: str) -> list[dict]:
    ensure_usd_migration_for_chat(int(chat_id))
    store = get_chat_store(int(chat_id))
    records = list(store.get('records', []) or [])
    key = ('usd_month', int(chat_id), str(month_key)[:7], len(records), int(store.get('next_id', 0) or 0))

    def _build():
        rows = []
        for rec in records:
            try:
                if not _record_day_key(rec).startswith(str(month_key)[:7]):
                    continue
                usd_amount = float(rec.get('usd_amount', 0) or 0)
                if not usd_amount:
                    continue
                rows.append(rec)
            except Exception:
                continue
        return sorted(rows, key=record_sort_key)
    return finance_cache_get(key, _build, ttl=30.0) if 'finance_cache_get' in globals() else _build()

def usd_balance_for_chat(chat_id: int) -> float:
    ensure_usd_migration_for_chat(int(chat_id))
    total = 0.0
    for rec in get_chat_store(int(chat_id)).get('records', []) or []:
        try:
            total += float(rec.get('usd_amount', 0) or 0)
        except Exception:
            pass
    return total

def usd_records_for_day(chat_id: int, day_key: str) -> list[dict]:
    ensure_usd_migration_for_chat(int(chat_id))
    store = get_chat_store(int(chat_id))
    records = list(store.get('records', []) or [])
    key = ('usd_day', int(chat_id), str(day_key), len(records), int(store.get('next_id', 0) or 0))

    def _build():
        return [r for r in financial_view_records_for_day_store(store, str(day_key)) if abs(float(r.get('usd_amount', 0) or 0)) > 0]
    return finance_cache_get(key, _build, ttl=20.0) if 'finance_cache_get' in globals() else _build()

def render_usd_day_window(chat_id: int, day_key: str):
    """Daily USD shell: same navigation/sections as ARS, but every value comes from usd_amount/usd_note."""
    ensure_usd_migration_for_chat(int(chat_id))
    store = get_chat_store(int(chat_id))
    recs = usd_records_for_day(int(chat_id), day_key)
    d = datetime.strptime(day_key, '%Y-%m-%d')
    wd = ['пн', 'вт', 'ср', 'чт', 'пт', 'сб', 'вс'][d.weekday()]
    t = now_local()
    td = t.strftime('%Y-%m-%d')
    yd = (t - timedelta(days=1)).strftime('%Y-%m-%d')
    tm = (t + timedelta(days=1)).strftime('%Y-%m-%d')
    tag = 'сегодня' if day_key == td else 'вчера' if day_key == yd else 'завтра' if day_key == tm else ''
    dk = fmt_date_ddmmyy(day_key)
    label = f'{dk} ({tag}, {wd})' if tag else f'{dk} ({wd})'
    header = ['💵 USD операции', f'📅 {label}', '']
    total_income = 0.0
    total_expense = 0.0
    record_lines = []
    for rec in recs:
        amt = float(rec.get('usd_amount', 0) or 0)
        if amt >= 0:
            total_income += amt
        else:
            total_expense += -amt
        sid = str(rec.get('usd_short_id') or f"U{rec.get('id', '')}")
        note = html.escape(str(rec.get('usd_note') or rec.get('note') or ''))
        sign = '+' if amt >= 0 else '-'
        record_lines.append(f'{sid} {sign}${fmt_num_plain(abs(amt))} {note}'.rstrip())
    day_balance = financial_view_balance_through_day(store, day_key)
    total_balance = financial_view_total_balance(store)
    footer = ['']
    if recs:
        footer.append(f'📉 Расход за день: -${fmt_num_plain(total_expense)}')
        footer.append(f'📈 Приход за день: +${fmt_num_plain(total_income)}')
    footer.append(f"📆 Остаток на конец дня: {('+' if day_balance >= 0 else '-')}${fmt_num_plain(abs(day_balance))}")
    footer.append(f"🏦 Остаток по чату: {('+' if total_balance >= 0 else '-')}${fmt_num_plain(abs(total_balance))}")
    footer.extend(gomonk_summary_lines(chat_id, 'usd'))
    total = total_income - total_expense
    if not record_lines:
        return (wm_common('\n'.join(header + ['Нет USD-записей за этот день.'] + footer), 1, html_mode=True), total)
    if effective_main_financial_value_buttons_enabled(int(chat_id)):
        hint = [f'💳 USD-записей за день: {len(recs)}', 'Нажмите сумму-кнопку ниже, чтобы изменить запись.']
        return (wm_common('\n'.join(header + hint + footer), 1, html_mode=True), total)
    hidden = 0
    visible = list(record_lines)
    if len(visible) > DAY_WINDOW_MAX_RECORDS:
        hidden = len(visible) - DAY_WINDOW_MAX_RECORDS
        visible = visible[-DAY_WINDOW_MAX_RECORDS:]
    while True:
        prefix = [f'… скрыто ранних записей: {hidden}', ''] if hidden > 0 else []
        text = '\n'.join(header + prefix + visible + footer)
        if len(text) <= DAY_WINDOW_MAX_CHARS or len(visible) <= 5:
            return (wm_common(text[:DAY_WINDOW_MAX_CHARS], 1, html_mode=True), total)
        hidden += 1
        visible = visible[1:]

def _v177_legacy_0163_render_usd_month_window(chat_id: int, day_key: str):
    month_key = str(day_key or today_key())[:7]
    try:
        month_dt = datetime.strptime(month_key + '-01', '%Y-%m-%d')
        month_label = month_dt.strftime('%m.%Y')
    except Exception:
        month_label = month_key
    rows = usd_records_for_month(int(chat_id), month_key)
    income = sum((float(r.get('usd_amount', 0) or 0) for r in rows if float(r.get('usd_amount', 0) or 0) > 0))
    expense = sum((abs(float(r.get('usd_amount', 0) or 0)) for r in rows if float(r.get('usd_amount', 0) or 0) < 0))
    lines = [f'💵 USD операции за {month_label}', '']
    if rows:
        for rec in rows:
            amt = float(rec.get('usd_amount', 0) or 0)
            sid = str(rec.get('usd_short_id') or rec.get('short_id') or f"U{rec.get('id', '')}")
            dk = fmt_date_ddmmyy(_record_day_key(rec))
            note = html.escape(str(rec.get('usd_note') or rec.get('note') or ''))
            sign = '+' if amt >= 0 else '-'
            val = fmt_num_plain(abs(amt))
            lines.append(f'{sid} {dk} {sign}${val} {note}'.rstrip())
    else:
        lines.append('Нет USD-транзакций за этот месяц.')
    lines.extend(['', f'📉 Расход за месяц: -${fmt_num_plain(expense)}', f'📈 Приход за месяц: +${fmt_num_plain(income)}', f"💵 Итог месяца: {('+' if income - expense >= 0 else '-')}${fmt_num_plain(abs(income - expense))}", f"🏦 USD остаток по чату: {('+' if usd_balance_for_chat(chat_id) >= 0 else '-')}${fmt_num_plain(abs(usd_balance_for_chat(chat_id)))}"])
    return (wm_common('\n'.join(lines), 1, html_mode=True), income - expense)
try:
    _v177_legacy_0163_render_usd_month_window.__name__ = 'render_usd_month_window'
except Exception:
    pass

def _v177_legacy_0164_build_usd_month_keyboard(day_key: str):
    try:
        dt = datetime.strptime(str(day_key)[:10], '%Y-%m-%d').replace(day=1)
    except Exception:
        dt = now_local().replace(day=1)
    prev_dt = (dt - timedelta(days=1)).replace(day=1)
    next_dt = (dt.replace(day=28) + timedelta(days=4)).replace(day=1)
    current_month = now_local().strftime('%Y-%m')
    kb = types.InlineKeyboardMarkup(row_width=3)
    nav = [IB('⬅️ Пред. месяц', callback_data=f"d:{prev_dt.strftime('%Y-%m-01')}:usd_month")]
    if dt.strftime('%Y-%m') != current_month:
        nav.append(IB('📅 Этот месяц', callback_data=f'd:{today_key()}:usd_month'))
    nav.append(IB('След. месяц ➡️', callback_data=f"d:{next_dt.strftime('%Y-%m-01')}:usd_month"))
    kb.row(*nav)
    kb.row(IB('⬅️ Назад осн. окно', callback_data=f'd:{str(day_key)[:10]}:back_main'))
    return kb
try:
    _v177_legacy_0164_build_usd_month_keyboard.__name__ = 'build_usd_month_keyboard'
except Exception:
    pass

def render_day_window(chat_id: int, day_key: str):
    if version_mode_feature('usd_transactions') and usd_transactions_view_enabled(int(chat_id)):
        return render_usd_day_window(int(chat_id), day_key)
    store = get_chat_store(chat_id)
    recs = [r for r in store.get('daily_records', {}).get(day_key, []) or [] if not bool(r.get('usd_only', False))]
    d = datetime.strptime(day_key, '%Y-%m-%d')
    wd = ['пн', 'вт', 'ср', 'чт', 'пт', 'сб', 'вс'][d.weekday()]
    t = now_local()
    td = t.strftime('%Y-%m-%d')
    yd = (t - timedelta(days=1)).strftime('%Y-%m-%d')
    tm = (t + timedelta(days=1)).strftime('%Y-%m-%d')
    tag = 'сегодня' if day_key == td else 'вчера' if day_key == yd else 'завтра' if day_key == tm else ''
    dk = fmt_date_ddmmyy(day_key)
    label = f'{dk} ({tag}, {wd})' if tag else f'{dk} ({wd})'
    header = [f'📅 {label}', '']
    try:
        _cr = careful_restore_status(int(chat_id))
        if _cr.get('active'):
            header += [f"🩹 Аккуратное восстановление ВКЛ: пересланные значения → {fmt_date_ddmmyy(day_key)} · ⏰ {_format_duration_short(_cr.get('remaining', 0))}", '']
    except Exception:
        pass
    mode = currency_mode(chat_id) if version_mode_feature('daily_usd') else 'ars'
    rate_info = usd_rate_cached(force=False) if mode != 'ars' else None
    total_income = 0.0
    total_expense = 0.0
    recs_sorted = sorted(recs, key=lambda x: x.get('timestamp'))
    all_record_lines = []
    for r in recs_sorted:
        amt = float(r.get('amount', 0) or 0)
        if amt >= 0:
            total_income += amt
        else:
            total_expense += -amt
        note = html.escape(r.get('note', ''))
        sid = r.get('short_id', f"R{r['id']}")
        all_record_lines.append(f'{sid} {format_chat_amount(chat_id, amt, mixed_space=False)} {note}'.rstrip())
    day_balance = calc_day_balance(store, day_key)
    bal_chat = store.get('balance', 0)
    footer = ['']
    if recs_sorted:
        expense_value = -total_expense if total_expense else 0.0
        income_value = total_income if total_income else 0.0
        footer.append(f'📉 Расход за день: {format_chat_amount(chat_id, expense_value, mixed_space=True)}')
        footer.append(f'📈 Приход за день: {format_chat_amount(chat_id, income_value, mixed_space=True)}')
    footer.append(f'📆 Остаток на конец дня: {format_chat_amount(chat_id, day_balance, mixed_space=True)}')
    footer.append(f'🏦 Остаток по чату: {format_chat_amount(chat_id, bal_chat, mixed_space=True)}')
    if mode != 'ars' and rate_info:
        footer.append(f"💵 Курс: 1 USD = {fmt_num(rate_info.get('rate')).lstrip('+')} ARS")
    footer.extend(gomonk_summary_lines(chat_id))
    total = total_income - total_expense
    if not all_record_lines:
        return (wm_common('\n'.join(header + ['Нет записей за этот день.'] + footer), 1, html_mode=True), total)
    if effective_main_financial_value_buttons_enabled(chat_id):
        hint = [f'💳 Записей за день: {len(recs_sorted)}', 'Нажмите сумму-кнопку ниже, чтобы изменить запись.']
        return (wm_common('\n'.join(header + hint + footer), 1, html_mode=True), total)
    hidden = 0
    visible = list(all_record_lines)
    if len(visible) > DAY_WINDOW_MAX_RECORDS:
        hidden = len(visible) - DAY_WINDOW_MAX_RECORDS
        visible = visible[-DAY_WINDOW_MAX_RECORDS:]
    while True:
        prefix = []
        if hidden > 0:
            prefix = [f'… скрыто ранних записей: {hidden}', '']
        text = '\n'.join(header + prefix + visible + footer)
        if len(text) <= DAY_WINDOW_MAX_CHARS:
            return (wm_common(text, 1, html_mode=True), total)
        if len(visible) <= 5:
            return (wm_common(text[:DAY_WINDOW_MAX_CHARS], 1, html_mode=True), total)
        hidden += 1
        visible = visible[1:]

def _collect_known_chat_items():
    """Известные чаты + владелец, без дублей; общий список для служебных меню."""
    items = {}
    try:
        known = collect_forward_menu_chats()
        for cid, ch in (known or {}).items():
            try:
                int_cid = int(cid)
            except Exception:
                continue
            title = (ch or {}).get('title') or get_chat_display_name(int_cid)
            items[int_cid] = title
    except Exception as e:
        log_error(f'_collect_known_chat_items known: {e}')
    try:
        for cid in (data.get('chats', {}) or {}).keys():
            try:
                int_cid = int(cid)
            except Exception:
                continue
            items.setdefault(int_cid, get_chat_display_name(int_cid))
    except Exception as e:
        log_error(f'_collect_known_chat_items data: {e}')
    if OWNER_ID:
        try:
            owner_id = int(OWNER_ID)
            items.setdefault(owner_id, get_chat_display_name(owner_id))
        except Exception:
            pass
    return sorted(items.items(), key=lambda x: (x[1] or '').lower())

def _collect_backup_menu_items():
    """Чаты для меню BACKUP: известные чаты + владелец, без дублей."""
    return _collect_known_chat_items()

def build_backup_owner_menu(day_key: str):
    """Ф41: верхняя строка массово включает/выключает три вида бэкапа."""
    kb = types.InlineKeyboardMarkup(row_width=4)
    owner_id = int(OWNER_ID) if OWNER_ID else None
    headers = []
    for target, label in (('chat', 'чат'), ('channel', 'канал'), ('mega', 'MEGA')):
        enabled, total = _backup_target_all_state(target)
        all_on = bool(total and enabled == total)
        headers.append(IB(('✅' if all_on else '⬜') + f' все {label}', callback_data=f'd:{day_key}:backup_mass_{target}'))
    kb.row(IB('Чаты', callback_data='none'), *headers)
    for cid, title in _collect_backup_menu_items():
        title_cb = f'd:{day_key}:removed_{cid}' if is_chat_bot_removed(cid) else 'none'
        chat_btn = IB(f'💬 {chat_button_title(cid, title)}', callback_data=title_cb)
        chat_label = _backup_toggle_label(cid, 'chat', 'чат') if owner_id is not None and int(cid) == owner_id else '➖ чат'
        chat_cb = f'd:{day_key}:backup_toggle_chat_{cid}' if owner_id is not None and int(cid) == owner_id else f'd:{day_key}:removed_{cid}' if is_chat_bot_removed(cid) else 'none'
        kb.row(chat_btn, IB(chat_label, callback_data=chat_cb), IB(_backup_toggle_label(cid, 'channel', 'канал'), callback_data=f'd:{day_key}:backup_toggle_channel_{cid}'), IB(_backup_toggle_label(cid, 'mega', 'MEGA'), callback_data=f'd:{day_key}:backup_toggle_mega_{cid}'))
    kb.row(IB('🔙 Назад', callback_data=f'd:{day_key}:back_main'))
    return kb

def build_backup_owner_menu_text() -> str:
    return wm_owner(f'💾 BACKUP\nНастройка авто-бэкапов по чатам. По умолчанию все бэкапы включены.\nКанал = JSON + Excel (Excel сейчас {backup_excel_all_label()}). MEGA = только JSON. В чат = только для владельца. Верхняя строка переключает сразу все чаты.', 7)

def _v177_legacy_0165_build_main_keyboard(day_key: str, chat_id=None):
    """One identical finance shell for ARS and 💵 USD operations."""
    kb = types.InlineKeyboardMarkup(row_width=3)
    nav_row = [IB('⬅️ Вчера', callback_data=f'd:{day_key}:prev')]
    if day_key != today_key():
        nav_row.append(IB('📅 Сегодня', callback_data=f'd:{day_key}:today'))
    nav_row.append(IB('➡️ Завтра', callback_data=f'd:{day_key}:next'))
    kb.row(*nav_row)
    kb.row(IB('📅 Календарь', callback_data=f'd:{day_key}:calendar'), IB('📊 Отчёт', callback_data=f'd:{day_key}:report'), IB('💰 Общий итог', callback_data=f'd:{day_key}:total'))
    kb.row(IB('📝 Редактировать', callback_data=f'd:{day_key}:edit_list'), IB('📂 CSV', callback_data=f'd:{day_key}:csv_all'), IB('📊 Статьи', callback_data=cat_callback('cat_today')))
    if chat_id is not None and usd_transactions_view_enabled(int(chat_id)):
        kb.row(IB('📆 За месяц', callback_data=f'd:{day_key}:usd_month'))
    if chat_id is not None and version_mode_feature('usd_transactions'):
        kb.row(IB(usd_transactions_toggle_label(int(chat_id)), callback_data=f'd:{day_key}:usd_tx_toggle'))
    if chat_id is not None and effective_main_financial_value_buttons_enabled(int(chat_id)):
        value_buttons = []
        for rec in financial_value_records_for_day(int(chat_id), day_key):
            try:
                rid = int(rec.get('id'))
            except Exception:
                continue
            value_buttons.append(IB(financial_record_button_label(rec, int(chat_id)), callback_data=f'd:{day_key}:value_rec_{rid}'))
        per_row = max(1, int(active_bot_behavior_profile_info().get('financial_buttons_per_row', 2) or 2))
        add_buttons_in_rows(kb, value_buttons[:84], per_row)
        if len(value_buttons) > 84:
            kb.row(IB(f'Ещё записей: {len(value_buttons) - 84}', callback_data=f'd:{day_key}:edit_list'))
    if chat_id is not None and effective_main_article_buttons_enabled(int(chat_id)):
        article_buttons = []
        for item in category_edit_items_for_chat(int(chat_id)):
            slug = str(item.get('slug') or '').strip()
            name = _clean_category_display_name(str(item.get('name') or slug or 'Статья').strip())
            if slug:
                article_buttons.append(IB(f'✏️ {name}', callback_data=cat_callback(f'cat_main_edit:{slug}:{day_key}')))
        add_buttons_in_rows(kb, article_buttons[:84], 2)
    if chat_id is not None and _v85_enabled('remaining_window'):
        kb.row(IB('ℹ️ Инфо', callback_data=f'd:{day_key}:info'), IB('с ост', callback_data=f'remaining_open:{day_key}'))
    else:
        kb.row(IB('ℹ️ Инфо', callback_data=f'd:{day_key}:info'))
    if is_owner_chat(chat_id):
        kb.row(IB('🔁 Пересылка', callback_data=f'd:{day_key}:forward_menu'), IB('💰 Фин режим', callback_data=f'd:{day_key}:forward_finmode_menu'))
        kb.row(IB('⏰ Напоминалка', callback_data=f'rem:list:0:{day_key}'), IB('💾 BACKUP', callback_data=f'd:{day_key}:backup_menu'))
        kb.row(IB('📝 Скачать ТЗ окон', callback_data='v160:export_tz'))
    kb.row(IB('❌ Закрыть', callback_data=f'main_close:{day_key}'))
    return kb
try:
    _v177_legacy_0165_build_main_keyboard.__name__ = 'build_main_keyboard'
except Exception:
    pass

def start_record_edit_prompt(chat_id: int, day_key: str, rid: int) -> bool:
    try:
        chat_id = int(chat_id)
        rid = int(rid)
        store = get_chat_store(chat_id)
        rec = next((r for r in store.get('records', []) if int(r.get('id', 0) or 0) == rid), None)
        if not rec:
            send_and_auto_delete(chat_id, '❌ Запись не найдена.')
            return False
        if usd_transactions_view_enabled(chat_id):
            amount = float(rec.get('usd_amount', 0) or 0)
            if not amount:
                send_and_auto_delete(chat_id, '❌ USD-часть записи не найдена.')
                return False
            note = str(rec.get('usd_note') or rec.get('note') or '')
            sid = str(rec.get('usd_short_id') or f'U{rid}')
            text = f"✏️ Редактирование USD-записи {sid}\n\nТекущие данные:\n{('+' if amount >= 0 else '-')}${fmt_num_plain(abs(amount))} {note}\n\n✍️ Напишите новые данные.\n\n⏳ Это сообщение и режим редактирования будут автоматически отменены через 40 секунд."
            insert_value = compose_usd_edit_insert_value(chat_id, rid, day_key, amount, note)
        else:
            text = f"✏️ Редактирование записи R{rid}\n\nТекущие данные:\n{fmt_num(rec.get('amount', 0))} {rec.get('note', '')}\n\n✍️ Напишите новые данные.\n\n⏳ Это сообщение и режим редактирования будут автоматически отменены через 40 секунд."
            insert_value = compose_edit_input_value(rec.get('amount'), rec.get('note', ''))
        text = wm_common(text, 10)
        kb = build_cancel_edit_keyboard(day_key, insert_text=insert_value, chat_id=chat_id)
        prompt_id = send_or_edit_edit_prompt(chat_id, 'edit_wait', text, reply_markup=kb)
        store['edit_wait'] = {'type': 'edit', 'rid': rid, 'day_key': day_key, 'prompt_msg_id': prompt_id, 'insert_text': insert_value, 'countdown_base_text': text, 'expires_at': time.time() + 40}
        if callable(globals().get('_v262_schedule_transient_chat_persist')):
            _v262_schedule_transient_chat_persist(chat_id)
        schedule_cancel_edit(chat_id, prompt_id, delay=None)
        return True
    except Exception as e:
        log_error(f'start_record_edit_prompt({chat_id},{day_key},{rid}): {e}')
        return False

def build_report_keyboard(month_key: str):
    """
    month_key: YYYY-MM. В о3 навигация по месяцам — первый ряд, назад/закрыть — второй ряд.
    """
    kb = types.InlineKeyboardMarkup(row_width=3)
    try:
        dt = datetime.strptime(month_key + '-01', '%Y-%m-%d')
    except Exception:
        dt = now_local().replace(day=1)
        month_key = dt.strftime('%Y-%m')
    current_month = now_local().strftime('%Y-%m')
    prev_month = (dt.replace(day=1) - timedelta(days=1)).replace(day=1)
    next_month = (dt.replace(day=28) + timedelta(days=4)).replace(day=1)
    nav_row = [IB('⬅️ Пред. месяц', callback_data=f"rep:{prev_month.strftime('%Y-%m')}")]
    if month_key != current_month:
        nav_row.append(IB('📅 Сегодня', callback_data='rep_today'))
    nav_row.append(IB('След. месяц ➡️', callback_data=f"rep:{next_month.strftime('%Y-%m')}"))
    kb.row(*nav_row)
    kb.row(IB('⬅️ Назад осн. окно', callback_data=f'd:{today_key()}:back_main'), IB('❌ Закрыть', callback_data='rep_close'))
    return kb

def build_month_report_text(chat_id: int, month_key: str=None):
    store = get_chat_store(chat_id)
    if usd_transactions_view_enabled(int(chat_id)):
        ensure_usd_migration_for_chat(int(chat_id))
    if not month_key:
        month_key = now_local().strftime('%Y-%m')
    try:
        month_dt = datetime.strptime(month_key + '-01', '%Y-%m-%d')
    except Exception:
        month_dt = now_local().replace(day=1)
        month_key = month_dt.strftime('%Y-%m')
    year, month = (month_dt.year, month_dt.month)
    next_month = datetime(year + 1, 1, 1) if month == 12 else datetime(year, month + 1, 1)
    days_in_month = (next_month - timedelta(days=1)).day
    view_usd = usd_transactions_view_enabled(int(chat_id))
    mode = currency_mode(chat_id)
    lines = [('💵 USD ОТЧЁТ ЗА ' if view_usd else 'ОТЧЁТ ЗА ') + month_dt.strftime('%m.%Y'), '']
    if view_usd or mode == 'ars':
        lines.extend([f"{'Дата':<8}|{'Приход':>10}|{'Расход':>10}|{'Остаток':>10}", ''])
    has_any = False
    for day in range(1, days_in_month + 1):
        day_key = f'{year}-{month:02d}-{day:02d}'
        if view_usd:
            recs = usd_records_for_day(int(chat_id), day_key)
            total_expense = sum((-float(r.get('usd_amount', 0) or 0) for r in recs if float(r.get('usd_amount', 0) or 0) < 0))
            total_income = sum((float(r.get('usd_amount', 0) or 0) for r in recs if float(r.get('usd_amount', 0) or 0) >= 0))
            day_balance = financial_view_balance_through_day(store, day_key)
        else:
            recs = [r for r in store.get('daily_records', {}).get(day_key, []) or [] if not bool(r.get('usd_only', False))]
            total_expense = sum((-float(r.get('amount', 0) or 0) for r in recs if float(r.get('amount', 0) or 0) < 0))
            total_income = sum((float(r.get('amount', 0) or 0) for r in recs if float(r.get('amount', 0) or 0) >= 0))
            day_balance = calc_day_balance(store, day_key)
        has_any = has_any or bool(recs)
        date_str = datetime.strptime(day_key, '%Y-%m-%d').strftime('%d.%m.%y')
        if view_usd:
            inc = f'${fmt_num_plain(total_income)}' if total_income else '-'
            exp = f'${fmt_num_plain(total_expense)}' if total_expense else '-'
            bal = f"{('+' if day_balance >= 0 else '-')}${fmt_num_plain(abs(day_balance))}"
            lines.append(f'{date_str:<8}|{inc:>10}|{exp:>10}|{bal:>10}')
        elif mode == 'ars':
            lines.append(f'{date_str:<8}|{report_cell(int(total_income), 7)}|{report_cell(int(total_expense), 7)}|{report_cell(int(day_balance), 7)}')
        else:
            lines.append(f'{date_str} | приход {format_chat_amount(chat_id, total_income, True)} | расход {format_chat_amount(chat_id, -total_expense, True)} | ост {format_chat_amount(chat_id, day_balance, True)}')
    if not has_any:
        lines.append('Нет данных за этот месяц.')
    return (wm_common('<pre>' + html.escape('\n'.join(lines)) + '</pre>', 3, html_mode=True), month_key)

def build_calendar_keyboard(center_day: datetime, chat_id=None):
    """Monthly financial calendar with explicit month/year and separate year navigation."""
    kb = types.InlineKeyboardMarkup(row_width=7)
    daily = {}
    back_day_key = today_key()
    if chat_id is not None:
        store = get_chat_store(chat_id)
        if usd_transactions_view_enabled(int(chat_id)):
            daily = {dk: recs for dk, recs in (store.get('daily_records', {}) or {}).items() if any((abs(float((r or {}).get('usd_amount', 0) or 0)) > 0 for r in recs or []))}
        else:
            daily = store.get('daily_records', {})
        back_day_key = store.get('current_view_day', today_key())
    kb.row(*[IB(x, callback_data='none') for x in ('Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс')])
    for week in calendar.Calendar(firstweekday=0).monthdayscalendar(center_day.year, center_day.month):
        row = []
        for day_num in week:
            if not day_num:
                row.append(IB(' ', callback_data='none'))
                continue
            key = f'{center_day.year:04d}-{center_day.month:02d}-{day_num:02d}'
            label = f'📝{day_num}' if daily.get(key) else str(day_num)
            row.append(IB(label, callback_data=f'd:{key}:open'))
        kb.row(*row)
    prev_month = (center_day.replace(day=1) - timedelta(days=1)).replace(day=1)
    next_month = (center_day.replace(day=28) + timedelta(days=4)).replace(day=1)
    kb.row(IB('⬅️ Месяц', callback_data=f"c:{prev_month.strftime('%Y-%m-%d')}"), IB(f'{russian_month_name(center_day.month)} {center_day.year}', callback_data='none'), IB('Месяц ➡️', callback_data=f"c:{next_month.strftime('%Y-%m-%d')}"))
    try:
        prev_year = center_day.replace(year=center_day.year - 1, day=1)
    except ValueError:
        prev_year = center_day.replace(year=center_day.year - 1, month=2, day=28)
    try:
        next_year = center_day.replace(year=center_day.year + 1, day=1)
    except ValueError:
        next_year = center_day.replace(year=center_day.year + 1, month=2, day=28)
    kb.row(IB('◀️ Год', callback_data=f"c:{prev_year.strftime('%Y-%m-%d')}"), IB(str(center_day.year), callback_data='none'), IB('Год ▶️', callback_data=f"c:{next_year.strftime('%Y-%m-%d')}"))
    current_month = now_local().strftime('%Y-%m')
    shown_month = center_day.strftime('%Y-%m')
    bottom_row = []
    if shown_month != current_month:
        bottom_row.append(IB('📅 Сегодня', callback_data=f"c:{now_local().strftime('%Y-%m-%d')}"))
    elif back_day_key != today_key():
        bottom_row.append(IB('📅 Сегодня', callback_data=f'd:{today_key()}:open'))
    bottom_row.append(IB('🔙 Назад', callback_data=f'd:{back_day_key}:back_main'))
    kb.row(*bottom_row)
    return kb

def _backup_toggle_label(chat_id: int, target: str, label: str) -> str:
    icon = '✅' if is_backup_target_enabled(chat_id, target) else '⬜'
    return f'{icon} {label}'

def _v177_legacy_0167_add_export_period_rows(kb, day_key: str, prefix: str, owner_day_key: str | None=None, target_chat_id: int | None=None):
    """F47: period / CSV / Excel menu / Excel articles menu."""
    periods = [('📅 День', 'day'), ('🗓 Неделя', 'week'), ('📆 Месяц', 'month'), ('📊 Ср–Чт', 'wedthu'), ('📂 Всё время', 'all')]
    scope = 'fv' if prefix == 'fv' else 'd'
    target = int(target_chat_id or 0)
    owner_day = str(owner_day_key or day_key)
    for label, mode in periods:
        if prefix == 'fv':
            csv_cb = f'fv:{target}:{day_key}:csv_{mode}:{owner_day}'
        else:
            csv_action = 'csv_all_real' if mode == 'all' else f'csv_{mode}'
            csv_cb = f'd:{day_key}:{csv_action}'
        xlsx_cb = export_callback(f'exp_style_period:{scope}:{target}:{mode}:xlsx:{day_key}:{owner_day}')
        xlsxstat_cb = export_callback(f'exp_style_period:{scope}:{target}:{mode}:xlsxstat:{day_key}:{owner_day}')
        kb.row(IB(label, callback_data='none'), IB('CSV', callback_data=csv_cb), IB('Excel', callback_data=xlsx_cb), IB('Excel статьи', callback_data=xlsxstat_cb))
try:
    _v177_legacy_0167_add_export_period_rows.__name__ = '_add_export_period_rows'
except Exception:
    pass

def _v177_legacy_0168_export_calendar_start_keyboard(view_year: int, view_month: int, return_day_key: str):
    kb = types.InlineKeyboardMarkup(row_width=7)
    last_day = calendar.monthrange(int(view_year), int(view_month))[1]
    buttons = [IB(str(day_num), callback_data=export_callback(f'exp_pick_set_start:{view_year}:{view_month}:{day_num}:{return_day_key}')) for day_num in range(1, last_day + 1)]
    for idx in range(0, len(buttons), 7):
        kb.row(*buttons[idx:idx + 7])
    prev_y, prev_m = _shift_month(view_year, view_month, -1)
    next_y, next_m = _shift_month(view_year, view_month, 1)
    kb.row(IB('⬅️ Месяц', callback_data=export_callback(f'exp_pick_start:{prev_y}:{prev_m}:{return_day_key}')), IB(f'{russian_month_name(view_month)} {view_year}', callback_data='none'), IB('Месяц ➡️', callback_data=export_callback(f'exp_pick_start:{next_y}:{next_m}:{return_day_key}')))
    kb.row(IB('◀️ Год', callback_data=export_callback(f'exp_pick_start:{view_year - 1}:{view_month}:{return_day_key}')), IB(str(view_year), callback_data='none'), IB('Год ▶️', callback_data=export_callback(f'exp_pick_start:{view_year + 1}:{view_month}:{return_day_key}')))
    kb.row(IB('🔙 Назад в CSV / Excel', callback_data=f'd:{return_day_key}:csv_all'))
    return kb
try:
    _v177_legacy_0168_export_calendar_start_keyboard.__name__ = '_export_calendar_start_keyboard'
except Exception:
    pass

def _export_start_record_keyboard(chat_id: int, start_key: str, return_day_key: str):
    store = get_chat_store(chat_id)
    kb = types.InlineKeyboardMarkup(row_width=1)
    _expense_anchor_rows(kb, store, start_key, lambda rid: export_callback(f'exp_pick_start_record:{start_key}:{rid}:{return_day_key}'))
    kb.row(IB('➡️ Продолжить с начала дня', callback_data=export_callback(f'exp_pick_start_record:{start_key}:0:{return_day_key}')))
    dt = datetime.strptime(start_key, '%Y-%m-%d')
    kb.row(IB('🔙 Назад к календарю', callback_data=export_callback(f'exp_pick_start:{dt.year}:{dt.month}:{return_day_key}')))
    return kb

def _v177_legacy_0170_export_end_calendar_keyboard(start_key: str, start_rid: int, view_year: int, view_month: int, return_day_key: str):
    kb = types.InlineKeyboardMarkup(row_width=7)
    last_day = calendar.monthrange(int(view_year), int(view_month))[1]
    buttons = []
    for day_num in range(1, last_day + 1):
        day_key = _date_key_from_ymd(view_year, view_month, day_num)
        if day_key < start_key:
            buttons.append(IB('·', callback_data='none'))
        else:
            buttons.append(IB(str(day_num), callback_data=export_callback(f'exp_pick_set_end:{start_key}:{int(start_rid)}:{view_year}:{view_month}:{day_num}:{return_day_key}')))
    for idx in range(0, len(buttons), 7):
        kb.row(*buttons[idx:idx + 7])
    prev_y, prev_m = _shift_month(view_year, view_month, -1)
    next_y, next_m = _shift_month(view_year, view_month, 1)
    nav = []
    if f'{prev_y:04d}-{prev_m:02d}' >= start_key[:7]:
        nav.append(IB('⬅️ Месяц', callback_data=export_callback(f'exp_pick_end:{start_key}:{int(start_rid)}:{prev_y}:{prev_m}:{return_day_key}')))
    else:
        nav.append(IB(' ', callback_data='none'))
    nav.append(IB(f'{russian_month_name(view_month)} {view_year}', callback_data='none'))
    nav.append(IB('Месяц ➡️', callback_data=export_callback(f'exp_pick_end:{start_key}:{int(start_rid)}:{next_y}:{next_m}:{return_day_key}')))
    kb.row(*nav)
    kb.row(IB('◀️ Год', callback_data=export_callback(f'exp_pick_end:{start_key}:{int(start_rid)}:{view_year - 1}:{view_month}:{return_day_key}')), IB(str(view_year), callback_data='none'), IB('Год ▶️', callback_data=export_callback(f'exp_pick_end:{start_key}:{int(start_rid)}:{view_year + 1}:{view_month}:{return_day_key}')))
    kb.row(IB('🔙 Изменить начало', callback_data=export_callback(f"exp_pick_set_start:{datetime.strptime(start_key, '%Y-%m-%d').year}:{datetime.strptime(start_key, '%Y-%m-%d').month}:{datetime.strptime(start_key, '%Y-%m-%d').day}:{return_day_key}")))
    return kb
try:
    _v177_legacy_0170_export_end_calendar_keyboard.__name__ = '_export_end_calendar_keyboard'
except Exception:
    pass

def _export_end_record_keyboard(chat_id: int, start_key: str, start_rid: int, end_key: str, return_day_key: str):
    store = get_chat_store(chat_id)
    kb = types.InlineKeyboardMarkup(row_width=1)
    all_recs = sorted_records_for_day(store, end_key)
    positions = {_record_int_id(rec): idx for idx, rec in enumerate(all_recs)}
    displayed = 0
    for rec in expense_anchor_records_for_day(store, end_key):
        rid = _record_int_id(rec)
        if end_key == start_key and start_rid and (positions.get(rid, -1) < positions.get(int(start_rid), 0)):
            continue
        displayed += 1
        kb.row(IB(expense_anchor_button_label(rec, store), callback_data=export_callback(f'exp_pick_end_record:{start_key}:{int(start_rid)}:{end_key}:{rid}:{return_day_key}')))
    if not displayed:
        kb.row(IB('Нет подходящих расходов в этот день', callback_data='none'))
    kb.row(IB('✅ Продолжить до конца дня', callback_data=export_callback(f'exp_pick_end_record:{start_key}:{int(start_rid)}:{end_key}:0:{return_day_key}')))
    end_dt = datetime.strptime(end_key, '%Y-%m-%d')
    kb.row(IB('🔙 Назад к календарю', callback_data=export_callback(f'exp_pick_end:{start_key}:{int(start_rid)}:{end_dt.year}:{end_dt.month}:{return_day_key}')))
    return kb

def _export_style_caption(style: str) -> str:
    return {'old': 'Старая таблица', 'new_comments': 'Новая • комментарии', 'new_notes': 'Новая • примечания', 'google_notes': 'Google Sheets • примечания'}.get(str(style), str(style))

def _excel_checkbox(mark: bool, label: str) -> str:
    return f"{('✅' if mark else '⬜')} {label}"

def _v177_legacy_0172_period_excel_style_keyboard(scope: str, target_chat_id: int, mode: str, file_type: str, day_key: str, owner_day_key: str):
    if excel_interface_mode(target_chat_id) == 'new':
        opts = excel_new_export_options()
        kb = types.InlineKeyboardMarkup(row_width=1)
        for option, label in (('old_table', 'Старая таблица'), ('comments', 'С комментариями'), ('notes', 'С примечаниями'), ('description_column', 'Описание в столбце')):
            kb.row(IB(_excel_checkbox(bool(opts.get(option)), label), callback_data=export_callback(f'exp_new_period_toggle:{scope}:{int(target_chat_id)}:{mode}:{file_type}:{option}:{day_key}:{owner_day_key}')))
        kb.row(IB(' ', callback_data='none'))
        kb.row(IB('📥 Скачать в чат', callback_data=export_callback(f'exp_new_period_send:{scope}:{int(target_chat_id)}:{mode}:{file_type}:chat:{day_key}:{owner_day_key}')))
        kb.row(IB('☁️ Залить в Google Sheets', callback_data=export_callback(f'exp_new_period_send:{scope}:{int(target_chat_id)}:{mode}:{file_type}:google:{day_key}:{owner_day_key}')))
        kb.row(IB('📁 Залить файл в Google Drive', callback_data=export_callback(f'exp_new_period_send:{scope}:{int(target_chat_id)}:{mode}:{file_type}:drive:{day_key}:{owner_day_key}')))
    else:
        kb = types.InlineKeyboardMarkup(row_width=1)
        for style, label in (('old', '📥 Скачать: старая таблица'), ('new_comments', '📥 Скачать: новая с комментариями'), ('new_notes', '📥 Скачать: новая с примечаниями'), ('google_notes', '☁️ Залить в Google Sheets с примечаниями')):
            kb.row(IB(label, callback_data=export_callback(f'exp_send_period_style:{scope}:{int(target_chat_id)}:{mode}:{file_type}:{style}:{day_key}:{owner_day_key}')))
        kb.row(IB('📁 Залить Excel в Google Drive', callback_data=export_callback(f'exp_new_period_send:{scope}:{int(target_chat_id)}:{mode}:{file_type}:drive:{day_key}:{owner_day_key}')))
    if scope == 'fv':
        back_cb = f'fv:{int(target_chat_id)}:{day_key}:csv_menu:{owner_day_key}'
    else:
        back_cb = f'd:{day_key}:csv_all'
    kb.row(IB('🔙 Назад в CSV / Excel', callback_data=back_cb))
    kb.row(IB('⬅️ Назад осн. окно', callback_data=f'd:{owner_day_key}:back_main'))
    return kb
try:
    _v177_legacy_0172_period_excel_style_keyboard.__name__ = '_period_excel_style_keyboard'
except Exception:
    pass

def _exact_excel_style_keyboard(start_key: str, start_rid: int, end_key: str, end_rid: int, file_type: str, return_day_key: str):
    if excel_interface_mode(OWNER_ID or 0) == 'new':
        opts = excel_new_export_options()
        kb = types.InlineKeyboardMarkup(row_width=1)
        for option, label in (('old_table', 'Старая таблица'), ('comments', 'С комментариями'), ('notes', 'С примечаниями'), ('description_column', 'Описание в столбце')):
            kb.row(IB(_excel_checkbox(bool(opts.get(option)), label), callback_data=export_callback(f'exp_new_exact_toggle:{start_key}:{int(start_rid)}:{end_key}:{int(end_rid)}:{file_type}:{option}:{return_day_key}')))
        kb.row(IB(' ', callback_data='none'))
        kb.row(IB('📥 Скачать в чат', callback_data=export_callback(f'exp_new_exact_send:{start_key}:{int(start_rid)}:{end_key}:{int(end_rid)}:{file_type}:chat:{return_day_key}')))
        kb.row(IB('☁️ Залить в Google Sheets', callback_data=export_callback(f'exp_new_exact_send:{start_key}:{int(start_rid)}:{end_key}:{int(end_rid)}:{file_type}:google:{return_day_key}')))
        kb.row(IB('📁 Залить файл в Google Drive', callback_data=export_callback(f'exp_new_exact_send:{start_key}:{int(start_rid)}:{end_key}:{int(end_rid)}:{file_type}:drive:{return_day_key}')))
    else:
        kb = types.InlineKeyboardMarkup(row_width=1)
        for style, label in (('old', '📥 Скачать: старая таблица'), ('new_comments', '📥 Скачать: новая с комментариями'), ('new_notes', '📥 Скачать: новая с примечаниями'), ('google_notes', '☁️ Залить в Google Sheets с примечаниями')):
            kb.row(IB(label, callback_data=export_callback(f'exp_send_exact_style:{start_key}:{int(start_rid)}:{end_key}:{int(end_rid)}:{file_type}:{style}:{return_day_key}')))
        kb.row(IB('📁 Залить Excel в Google Drive', callback_data=export_callback(f'exp_new_exact_send:{start_key}:{int(start_rid)}:{end_key}:{int(end_rid)}:{file_type}:drive:{return_day_key}')))
    kb.row(IB('🔙 Назад к форматам', callback_data=export_callback(f'exp_pick_end_record:{start_key}:{int(start_rid)}:{end_key}:{int(end_rid)}:{return_day_key}')))
    kb.row(IB('⬅️ Назад осн. окно', callback_data=f'd:{return_day_key}:back_main'))
    return kb

def _export_format_keyboard(start_key: str, start_rid: int, end_key: str, end_rid: int, return_day_key: str):
    kb = types.InlineKeyboardMarkup(row_width=3)
    kb.row(IB('📄 CSV', callback_data=export_callback(f'exp_send:{start_key}:{int(start_rid)}:{end_key}:{int(end_rid)}:csv:{return_day_key}')), IB('📊 Excel', callback_data=export_callback(f'exp_style_exact:{start_key}:{int(start_rid)}:{end_key}:{int(end_rid)}:xlsx:{return_day_key}')), IB('📊 Excel стат', callback_data=export_callback(f'exp_style_exact:{start_key}:{int(start_rid)}:{end_key}:{int(end_rid)}:xlsxstat:{return_day_key}')))
    end_dt = datetime.strptime(end_key, '%Y-%m-%d')
    kb.row(IB('🔙 Изменить конец', callback_data=export_callback(f'exp_pick_set_end:{start_key}:{int(start_rid)}:{end_dt.year}:{end_dt.month}:{end_dt.day}:{return_day_key}')))
    kb.row(IB('❌ Вернуться в CSV / Excel', callback_data=f'd:{return_day_key}:csv_all'))
    kb.row(IB('⬅️ Назад осн. окно', callback_data=f'd:{return_day_key}:back_main'))
    return kb

def _v177_legacy_0173_exact_export_rows(chat_id: int, start_key: str, start_rid: int, end_key: str, end_rid: int):
    store = get_chat_store(chat_id)
    if financial_view_is_usd(store):
        ensure_usd_migration_for_chat(int(chat_id))
    rows = []
    for day_key, rec in exact_record_range(store, start_key, start_rid, end_key, end_rid):
        rows.append((fmt_date_table(day_key), fmt_csv_amount(financial_view_amount(store, rec)), financial_view_note(store, rec)))
    return rows
try:
    _v177_legacy_0173_exact_export_rows.__name__ = '_exact_export_rows'
except Exception:
    pass

def _v177_legacy_0174_build_exact_category_stats_xlsx_rows(target_chat_id: int, start_key: str, start_rid: int, end_key: str, end_rid: int) -> list[list]:
    """Excel stat with formulas, opening balance and real closing balance."""
    store = get_chat_store(target_chat_id)
    records = exact_record_range(store, start_key, start_rid, end_key, end_rid)
    cats_map = calc_categories_for_record_range(store, start_key, start_rid, end_key, end_rid)
    categories = get_ordered_category_names(cats=cats_map, store=store)
    clean_categories = [_clean_category_display_name(x) for x in categories]
    headers = ['Дата', 'Описание', 'Приход'] + clean_categories
    opening = _opening_balance_before_exact(store, start_key, start_rid)
    rows = [headers, ['', 'Остаток с прошлого раза', opening] + [''] * len(categories), []]
    data_start_row = 4
    income_total = 0.0
    expense_total = 0.0
    cat_totals = {cat: 0.0 for cat in categories}
    prev_day = None
    for day_key, rec in records:
        try:
            amount = financial_view_amount(store, rec)
        except Exception:
            amount = 0.0
        if prev_day is not None and day_key != prev_day:
            rows.append([])
        prev_day = day_key
        row = [fmt_date_table(day_key), financial_view_note(store, rec), ''] + [''] * len(categories)
        if amount >= 0:
            income_total += amount
            row[2] = int(round(amount)) if float(amount).is_integer() else amount
        else:
            value = abs(amount)
            expense_total += value
            category = resolve_expense_category(financial_view_note(store, rec), store)
            try:
                override_slug = str((rec or {}).get('category_override_slug') or '').strip()
                if override_slug:
                    category = get_category_by_slug(override_slug, store) or category
            except Exception:
                pass
            if category in cat_totals:
                cat_totals[category] += value
                idx = categories.index(category)
                row[3 + idx] = int(round(value)) if float(value).is_integer() else value
        rows.append(row)
    data_last_row = max(data_start_row, len(rows))
    rows.append([])
    sum_row_num = len(rows) + 1
    sum_row = ['', 'Сумма по статьям', {'formula': f'SUM(C{data_start_row}:C{data_last_row})', 'value': income_total}]
    for idx, cat in enumerate(categories, start=4):
        col = _xlsx_col_name(idx)
        sum_row.append({'formula': f'SUM({col}{data_start_row}:{col}{data_last_row})', 'value': cat_totals.get(cat, 0.0)})
    rows.append(sum_row)
    rows.append([])
    expense_row_num = len(rows) + 1
    if categories:
        first_cat = _xlsx_col_name(4)
        last_cat = _xlsx_col_name(3 + len(categories))
        expense_formula = f'SUM({first_cat}{sum_row_num}:{last_cat}{sum_row_num})'
    else:
        expense_formula = '0'
    rows.append(['', 'Расход', {'formula': expense_formula, 'value': expense_total}] + [''] * len(categories))
    income_row_num = len(rows) + 1
    rows.append(['', 'Приход', {'formula': f'C{sum_row_num}', 'value': income_total}] + [''] * len(categories))
    closing = opening + income_total - expense_total
    rows.append(['', 'Остаток на руках', {'formula': f'C2+C{income_row_num}-C{expense_row_num}', 'value': closing}] + [''] * len(categories))
    return rows
try:
    _v177_legacy_0174_build_exact_category_stats_xlsx_rows.__name__ = 'build_exact_category_stats_xlsx_rows'
except Exception:
    pass

def _v177_legacy_0177_category_rows_without_description(rows: list[list]) -> tuple[list[list], dict[tuple[int, int], str]]:
    """Удаляет столбец «Описание», переносит подписи итогов в A и кладёт описания в примечания сумм."""
    out = []
    annotations = {}
    for r_idx, raw in enumerate(rows or [], start=1):
        row = list(raw or [])
        desc = str(row[1] if len(row) > 1 else '').strip()
        is_header = str(row[0] if row else '').strip().casefold() in {'дата', 'date'} and desc.casefold() in {'описание', 'description'}
        if len(row) > 1:
            if not is_header and desc and (not str(row[0] if row else '').strip()) and (desc.casefold() in {'остаток с прошлого раза', 'сумма по статьям', 'расход', 'приход', 'остаток на руках', 'на руках:', 'гомонковые', 'остаток в обороте', 'расход еды на человека в сутки'}):
                row[0] = desc
            row.pop(1)
        if desc and (not is_header) and (desc.casefold() not in {'остаток с прошлого раза', 'сумма по статьям', 'расход', 'приход', 'остаток на руках', 'на руках:', 'гомонковые', 'остаток в обороте', 'расход еды на человека в сутки'}):
            for original_c in range(3, len(raw or [])):
                try:
                    if _excel_nonempty((raw or [])[original_c]):
                        annotations[r_idx, original_c] = desc
                except Exception:
                    pass
        out.append(row)
    return (out, annotations)
try:
    _v177_legacy_0177_category_rows_without_description.__name__ = '_category_rows_without_description'
except Exception:
    pass

def _v177_legacy_0179_send_exact_range_export(recipient_chat_id: int, target_chat_id: int, start_key: str, start_rid: int, end_key: str, end_rid: int, file_type: str, excel_style_override: str | None=None, excel_options_override: dict | None=None, delivery: str='chat'):
    """Фоновый экспорт между двумя точными границами включительно."""
    tmp_name = None
    try:
        file_type = str(file_type or 'csv').lower()
        if file_type not in {'csv', 'xlsx', 'xlsxstat'}:
            file_type = 'csv'
        custom_options = normalize_excel_export_options(excel_options_override) if isinstance(excel_options_override, dict) else None
        excel_style_override = str(excel_style_override or (excel_export_options_style(custom_options) if custom_options else excel_table_style(target_chat_id)) or 'old').strip().lower()
        if excel_style_override not in {'old', 'new_plain', 'new_comments', 'new_notes', 'google_notes'}:
            excel_style_override = 'old'
        delivery = str(delivery or 'chat').strip().lower()
        force_google = delivery == 'google' or excel_style_override == 'google_notes'
        description_column = True if not custom_options else bool(custom_options.get('description_column'))
        annotations_enabled = bool(not custom_options or custom_options.get('comments') or custom_options.get('notes'))
        _file_job_progress('собираю данные', force=True)
        rows = _exact_export_rows(target_chat_id, start_key, int(start_rid), end_key, int(end_rid))
        if not rows:
            send_and_auto_delete(recipient_chat_id, 'Нет записей в выбранном точном диапазоне.', 10)
            return True
        ext = 'xlsx' if file_type in {'xlsx', 'xlsxstat'} else 'csv'
        tmp_name = os.path.join(MEGA_LOCAL_TMP_DIR, f'exact_export_{target_chat_id}_{int(time.time() * 1000)}.{ext}')
        if file_type == 'xlsxstat':
            xlsx_rows = build_exact_category_stats_xlsx_rows(target_chat_id, start_key, int(start_rid), end_key, int(end_rid))
            annotations_override = None
            category_layout = True
            if custom_options and (not description_column):
                xlsx_rows, annotations_override = _category_rows_without_description(xlsx_rows)
                category_layout = 'category_compact'
            if force_google:
                title = f'{get_chat_display_name(target_chat_id)} — статьи — точный период'
                sheet_url = _google_sheets_create_category_report(title, xlsx_rows, layout='category' if category_layout is True else 'category_compact', annotations_override=annotations_override if annotations_enabled else {}, include_annotations=annotations_enabled, target_chat_id=target_chat_id)
                bot.send_message(recipient_chat_id, f'📊 Google Таблица — статьи, точный период\n\n{sheet_url}', disable_web_page_preview=True)
                try:
                    file_job_mark_external_delivery('Google Sheets', sheet_url)
                except Exception:
                    pass
                return True
            _write_excel_by_selected_style(tmp_name, xlsx_rows, target_chat_id, sheet_name='Excel стат', category_layout=category_layout, mode_override=excel_style_override, compact_annotations=annotations_override if category_layout == 'category_compact' and annotations_enabled else {} if category_layout == 'category_compact' else None)
        elif ext == 'xlsx':
            opening = _opening_balance_before_exact(get_chat_store(target_chat_id), start_key, int(start_rid))
            if force_google:
                xlsx_rows = build_exact_category_stats_xlsx_rows(target_chat_id, start_key, int(start_rid), end_key, int(end_rid))
                annotations_override = None
                layout_name = 'category'
                if custom_options and (not description_column):
                    xlsx_rows, annotations_override = _category_rows_without_description(xlsx_rows)
                    layout_name = 'category_compact'
                title = f'{get_chat_display_name(target_chat_id)} — статьи — точный период'
                sheet_url = _google_sheets_create_category_report(title, xlsx_rows, layout=layout_name, annotations_override=annotations_override if annotations_enabled else {}, include_annotations=annotations_enabled, target_chat_id=target_chat_id)
                bot.send_message(recipient_chat_id, f'📊 Google Таблица — точный период\n\n{sheet_url}', disable_web_page_preview=True)
                try:
                    file_job_mark_external_delivery('Google Sheets', sheet_url)
                except Exception:
                    pass
                return True
            if excel_style_override != 'old':
                if description_column:
                    xlsx_rows = [['Дата', 'Описание', 'Приход', 'Расход']]
                    for date_v, amount_v, note_v in rows:
                        try:
                            parsed_amount = parse_csv_amount(amount_v)
                        except Exception:
                            parsed_amount = 0.0
                        xlsx_rows.append(_xlsx_record_row(date_v, parsed_amount, note_v))
                    xlsx_rows = insert_blank_rows_between_days(xlsx_rows, header_rows=1)
                    xlsx_rows = _xlsx_simple_rows_with_balances(xlsx_rows, opening, target_chat_id)
                    _write_excel_by_selected_style(tmp_name, xlsx_rows, target_chat_id, sheet_name='Точный период', category_layout=False, mode_override=excel_style_override)
                else:
                    xlsx_rows, compact_annotations = _compact_simple_excel_rows_and_annotations(rows, opening, target_chat_id)
                    _write_excel_by_selected_style(tmp_name, xlsx_rows, target_chat_id, sheet_name='Точный период', category_layout=False, mode_override=excel_style_override, compact_annotations=compact_annotations if annotations_enabled else {})
            else:
                xlsx_rows = [['Дата', 'Описание', 'Приход', 'Расход']]
                for date_v, amount_v, note_v in rows:
                    try:
                        parsed_amount = parse_csv_amount(amount_v)
                    except Exception:
                        parsed_amount = 0.0
                    xlsx_rows.append(_xlsx_record_row(date_v, parsed_amount, note_v))
                xlsx_rows = insert_blank_rows_between_days(xlsx_rows, header_rows=1)
                xlsx_rows = _xlsx_simple_rows_with_balances(xlsx_rows, opening, target_chat_id)
                _write_excel_by_selected_style(tmp_name, xlsx_rows, target_chat_id, sheet_name='Точный период', category_layout=False, mode_override='old')
        else:
            with open(tmp_name, 'w', newline='', encoding='utf-8') as fh:
                writer = csv.writer(fh)
                writer.writerow(['date', 'amount', 'note'])
                write_csv_rows_with_day_gaps(writer, rows, 3)
        chat_name = _safe_export_name_part(get_chat_name_for_filename(target_chat_id) or get_chat_display_name(target_chat_id), f'chat_{target_chat_id}')
        start_label = fmt_date_backup(start_key).replace(':', '.')
        end_label = fmt_date_backup(end_key).replace(':', '.')
        display_name = f"{chat_name}_({start_label}-{end_label})_{('excel_стат' if file_type == 'xlsxstat' else 'точный')}.{ext}"
        store = get_chat_store(target_chat_id)
        caption = f"🎯 {(('Excel стат ' if file_type == 'xlsxstat' else 'Excel ') + _export_style_caption(excel_style_override) if ext == 'xlsx' else 'CSV')} — точный период\n▶️ {exact_boundary_text(store, start_key, start_rid, True)}\n⏹ {exact_boundary_text(store, end_key, end_rid, False)}"
        if delivery == 'drive':
            _file_job_progress('загружаю файл в Google Drive', force=True)
            drive_url = tenant_google_upload_export(tmp_name, display_name, target_chat_id)
            bot.send_message(recipient_chat_id, f'☁️ Google Drive — точный период\n\n{drive_url}', disable_web_page_preview=True)
            try:
                file_job_mark_external_delivery('Google Drive', drive_url)
            except Exception:
                pass
            return True
        fobj = file_bytesio_named(tmp_name, display_name)
        if not fobj:
            raise RuntimeError('Точный экспорт создан, но файл не удалось открыть для отправки в Telegram')
        _file_job_progress('отправляю файл в Telegram', force=True)
        _tg_call_retry(bot.send_document, recipient_chat_id, fobj, caption=caption, timeout=120, purpose='exact_export_send_document')
        return True
    except Exception as exc:
        log_error(f'send_exact_range_export({target_chat_id}): {exc}')
        return False
    finally:
        if tmp_name:
            try:
                os.remove(tmp_name)
            except Exception:
                pass
try:
    _v177_legacy_0179_send_exact_range_export.__name__ = 'send_exact_range_export'
except Exception:
    pass

def build_csv_menu(day_key: str, chat_id: int | None=None):
    kb = types.InlineKeyboardMarkup(row_width=4)
    _add_export_period_rows(kb, day_key, 'd')
    try:
        ref_dt = datetime.strptime(day_key, '%Y-%m-%d')
    except Exception:
        ref_dt = now_local()
    kb.row(IB('🎯 Произвольный точный период', callback_data=export_callback(f'exp_pick_start:{ref_dt.year}:{ref_dt.month}:{day_key}')))
    kb.row(IB('⬅️ Назад', callback_data=f'd:{day_key}:edit_menu'))
    kb.row(IB('⬅️ Назад осн. окно', callback_data=f'd:{day_key}:back_main'))
    return kb

def build_edit_menu_keyboard(day_key: str, chat_id=None):
    """Совместимость со старыми callback: отдельного подменю больше нет."""
    return build_main_keyboard(day_key, chat_id)
_INLINE_FALLBACK_TEXT_LOCK = threading.RLock()
_INLINE_FALLBACK_TEXT = {}
_INLINE_FALLBACK_TEXT_SEQ = 0
_INLINE_FALLBACK_TEXT_TTL = 180.0
_INLINE_FALLBACK_TEXT_MAX = 300

def _chat_type_for_buttons(chat_id: int | None) -> str:
    try:
        if chat_id is None:
            return ''
        info = get_chat_store(int(chat_id)).get('info') or {}
        return str(info.get('type') or '').strip().lower()
    except Exception:
        return ''

def _inline_current_chat_supported(chat_id: int | None) -> bool:
    """Telegram forbids switch_inline_query_current_chat in channel posts."""
    return _chat_type_for_buttons(chat_id) != 'channel'

def _inline_fallback_register(chat_id: int | None, text: str) -> str:
    """Small RAM-only token for channel-safe 'show/copy text' buttons.

    It is intentionally ephemeral: these buttons are only helpers for an already-open
    edit window. Business state stays in SQLite/MEGA.
    """
    global _INLINE_FALLBACK_TEXT_SEQ
    now = time.time()
    with _INLINE_FALLBACK_TEXT_LOCK:
        for key, item in list(_INLINE_FALLBACK_TEXT.items()):
            if now - float((item or {}).get('ts', 0.0) or 0.0) > _INLINE_FALLBACK_TEXT_TTL:
                _INLINE_FALLBACK_TEXT.pop(key, None)
        _INLINE_FALLBACK_TEXT_SEQ += 1
        token = f'{int(now * 1000):x}{_INLINE_FALLBACK_TEXT_SEQ:x}'[-18:]
        _INLINE_FALLBACK_TEXT[token] = {'chat_id': int(chat_id) if chat_id is not None else None, 'text': str(text or '')[:3500], 'ts': now}
        if len(_INLINE_FALLBACK_TEXT) > _INLINE_FALLBACK_TEXT_MAX:
            oldest = sorted(_INLINE_FALLBACK_TEXT.items(), key=lambda kv: float((kv[1] or {}).get('ts', 0.0) or 0.0))
            for key, _item in oldest[:len(_INLINE_FALLBACK_TEXT) - _INLINE_FALLBACK_TEXT_MAX]:
                _INLINE_FALLBACK_TEXT.pop(key, None)
    return f'itxt:{token}'

def _inline_fallback_get(data_str: str, chat_id: int) -> str:
    token = str(data_str or '').split(':', 1)[1] if ':' in str(data_str or '') else ''
    now = time.time()
    with _INLINE_FALLBACK_TEXT_LOCK:
        item = _INLINE_FALLBACK_TEXT.get(token) or {}
        if not item:
            return ''
        if now - float(item.get('ts', 0.0) or 0.0) > _INLINE_FALLBACK_TEXT_TTL:
            _INLINE_FALLBACK_TEXT.pop(token, None)
            return ''
        expected = item.get('chat_id')
        if expected is not None and int(expected) != int(chat_id):
            return ''
        return str(item.get('text') or '')

def make_copy_or_inline_button(label: str, text: str, viewer_chat_id: int | None=None):
    """Insert text in normal chats; never create Telegram-invalid inline buttons in channels."""
    if not _inline_current_chat_supported(viewer_chat_id):
        safe_label = str(label or '✍️')
        if 'Вставить' in safe_label:
            safe_label = safe_label.replace('Вставить', 'Показать')
        elif safe_label.strip() in {'✏️', '✍️'}:
            safe_label = safe_label
        else:
            safe_label = safe_label + ' · показать'
        return IB(safe_label, callback_data=_inline_fallback_register(viewer_chat_id, text))
    return IB(label, switch_inline_query_current_chat=str(text)[:256])
_BOT_USERNAME_CACHE = None

def get_bot_username_cached() -> str:
    """Имя бота нужно только для очистки текста, вставленного через inline-поле Telegram."""
    global _BOT_USERNAME_CACHE
    if _BOT_USERNAME_CACHE is not None:
        return _BOT_USERNAME_CACHE
    try:
        me = bot.get_me()
        _BOT_USERNAME_CACHE = (getattr(me, 'username', '') or '').lstrip('@')
    except Exception:
        _BOT_USERNAME_CACHE = ''
    return _BOT_USERNAME_CACHE

def sanitize_telegram_inserted_text(text: str) -> str:
    """Убирает @имя_бота, которое Telegram может добавить при inline-вставке."""
    s = str(text or '').strip()
    username = get_bot_username_cached()
    if username:
        s = re.sub(f'(?im)^\\s*@{re.escape(username)}\\b[:\\s,]*', '', s)
        s = re.sub(f'(?i)\\s*@{re.escape(username)}\\b', '', s)
    s = re.sub('(?m)^\\s*@[A-Za-z0-9_]{3,}\\s+(?=(?:\\(|[+\\-–]?\\s*\\d))', '', s)
    return re.sub('[ \\t]+', ' ', s).strip()
DIRECT_EDIT_TOKEN = 'EDITREC'
USD_DIRECT_EDIT_TOKEN = 'EDITUSD'

def compose_direct_edit_insert_value(target_chat_id: int, rid: int, day_key: str, amount, note: str='') -> str:
    """Текст для быстрой вставки редактирования записи через inline-поле Telegram.
    Метаданные спрятаны в скобках. Пользователь меняет только строку суммы ниже.
    После отправки бот удалит служебную строку/сообщение и обновит запись.
    """
    value = compose_edit_input_value(amount, note)
    meta = f'{DIRECT_EDIT_TOKEN}|{int(target_chat_id)}|{int(rid)}|{str(day_key)[:10]}|'
    return f'({meta} служебное — можно не трогать)\n\n{value}'

def compose_usd_edit_insert_value(target_chat_id: int, rid: int, day_key: str, amount, note: str='') -> str:
    value = compose_edit_input_value(amount, note)
    meta = f'{USD_DIRECT_EDIT_TOKEN}|{int(target_chat_id)}|{int(rid)}|{str(day_key)[:10]}|'
    return f'({meta} служебное — можно не трогать)\n\n{value}'

def make_direct_edit_insert_button(label: str, insert_text: str, viewer_chat_id: int | None=None):
    """Direct edit insert with a safe channel fallback instead of Telegram HTTP 400."""
    return make_copy_or_inline_button(label, insert_text, viewer_chat_id=viewer_chat_id)

def _delete_direct_edit_service_message(chat_id: int, message_id: int) -> None:
    """Удаляет служебную EDITREC/EDITUSD вставку и повторяет удаление при сетевом сбое."""
    chat_id = int(chat_id)
    message_id = int(message_id)
    try:
        _tg_call_retry(bot.delete_message, chat_id, message_id, attempts=2, purpose='direct_edit_service_delete')
        bot_journal('direct_edit_service_deleted', chat_id, f'message_id={message_id}')
        return
    except Exception as exc:
        bot_journal('direct_edit_service_delete_retry', chat_id, f'message_id={message_id} error={str(exc)[:120]}')

    def _retry():
        try:
            _tg_call_retry(bot.delete_message, chat_id, message_id, attempts=3, purpose='direct_edit_service_delete_retry')
            bot_journal('direct_edit_service_deleted', chat_id, f'message_id={message_id} retry=1')
        except Exception as exc2:
            log_error(f'direct_edit service delete failed {chat_id}:{message_id}: {exc2}')
    try:
        DELAYED_SCHEDULER.schedule(f'direct-edit-delete:{chat_id}:{message_id}', 1.2, _retry)
    except Exception:
        _retry()

def handle_direct_edit_insert_message(msg) -> bool:
    """Обрабатывает отправленный пользователем текст, который был вставлен кнопкой ✏️ из О6.
    Формат: EDITREC|chat_id|rid|day_key| сумма описание
    """
    try:
        if getattr(msg, 'content_type', None) != 'text':
            return False
        chat_id = int(msg.chat.id)
        text = (msg.text or '').strip()
        token_kind = USD_DIRECT_EDIT_TOKEN if USD_DIRECT_EDIT_TOKEN + '|' in text else DIRECT_EDIT_TOKEN if DIRECT_EDIT_TOKEN + '|' in text else None
        if not token_kind:
            return False
        _durable_note_source_consumed('direct_edit_insert')
        _delete_direct_edit_service_message(chat_id, int(msg.message_id))
        m = re.search('\\((%s\\|[^)]*)\\)' % re.escape(token_kind), text)
        if m:
            meta_text = m.group(1)
            parts = meta_text.split('|', 4)
            if len(parts) < 4:
                return False
            _, target_s, rid_s, day_key = parts[:4]
            value_text = (text[:m.start()] + ' ' + text[m.end():]).strip()
        else:
            text = text[text.find(token_kind + '|'):]
            parts = text.split('|', 4)
            if len(parts) < 5:
                return False
            _, target_s, rid_s, day_key, value_text = parts
            value_text = (value_text or '').strip()
        target_chat_id = int(target_s)
        rid = int(rid_s)
        day_key = (day_key or today_key())[:10]
        value_text = sanitize_telegram_inserted_text(value_text)
        if not value_text:
            send_and_auto_delete(chat_id, '❌ Нет нового значения для редактирования.', 10)
            return True
        if not is_owner_chat(chat_id) and int(chat_id) != int(target_chat_id):
            send_and_auto_delete(chat_id, '⛔ Нельзя редактировать запись другого чата.', 10)
            return True
        if token_kind == USD_DIRECT_EDIT_TOKEN:
            amount, note = parse_usd_edit_value(value_text)
            # v262: USD direct edit must use the same immutable finance-origin transaction
            # as native Telegram edit, /izm and main-window ARS edit.  Do not mutate only
            # one local row here, otherwise source/copies can diverge after a deploy.
            with locked_chat(target_chat_id):
                rec = next((r for r in get_chat_store(target_chat_id).get('records', []) if int(r.get('id', -1)) == int(rid)), None)
                usd_only = bool(
                    isinstance(rec, dict)
                    and rec.get('usd_only', False)
                    and (not float(rec.get('amount', 0) or 0))
                )
            linked_edit = globals().get('apply_linked_finance_edit_v262')
            ok = bool(
                isinstance(rec, dict)
                and callable(linked_edit)
                and linked_edit(
                    int(target_chat_id),
                    rec,
                    update_ars=False,
                    replace_usd=True,
                    usd_amount=float(amount),
                    usd_note=str(note or rec.get('usd_note') or rec.get('note') or ''),
                    usd_only=usd_only,
                    full_text_replace=False,
                    repaint_copies=True,
                    source_kind='usd_direct_edit',
                )
            )
        else:
            amount, note = split_amount_and_note(value_text)
            with locked_chat(target_chat_id):
                ok = update_record_in_chat(target_chat_id, rid, amount, note, source_finance_text=value_text)
        if not ok:
            send_and_auto_delete(chat_id, '❌ Запись для редактирования не найдена.', 10)
            return True
        if token_kind == USD_DIRECT_EDIT_TOKEN:
            _durable_note_record_edit_witness(_durable_record_edit_witness(target_chat_id, rid, usd_amount=amount, usd_note=note, kind='usd_direct'))
        else:
            _durable_note_record_edit_witness(_durable_record_edit_witness(target_chat_id, rid, amount=amount, note=note, source_finance_text=value_text, kind='direct_edit'))
        finance_changed(target_chat_id, day_key, reason='direct_edit_insert', delay=0.1)
        if token_kind == USD_DIRECT_EDIT_TOKEN:
            send_and_auto_delete(chat_id, f'✅ USD-запись обновлена: {fmt_num(amount)} USD {note}', 8)
        else:
            send_and_auto_delete(chat_id, f'✅ Запись обновлена: {fmt_num(amount)} {note}', 8)
        return True
    except Exception as e:
        log_error(f'handle_direct_edit_insert_message: {e}')
        try:
            send_and_auto_delete(msg.chat.id, '❌ Не удалось применить вставленное редактирование.', 10)
        except Exception:
            pass
        return True

def build_cancel_edit_keyboard(day_key: str, insert_text: str | None=None, chat_id: int | None=None):
    kb = types.InlineKeyboardMarkup()
    if insert_text:
        kb.row(make_copy_or_inline_button('✍️ Вставить текст', '\n' + str(insert_text), viewer_chat_id=chat_id))
    kb.row(IB('❌ Закрыть', callback_data=f'd:{day_key}:cancel_edit'), IB('⬅️ Назад осн. окно', callback_data=f'd:{day_key}:back_main'))
    return kb

def build_finwin_cancel_edit_keyboard(target_chat_id: int, day_key: str, owner_day_key: str, insert_text: str | None=None):
    kb = types.InlineKeyboardMarkup()
    if insert_text:
        kb.row(make_copy_or_inline_button('✍️ Вставить текст', str(insert_text), viewer_chat_id=int(OWNER_ID) if OWNER_ID else target_chat_id))
    kb.row(IB('❌ Закрыть', callback_data=f'fv:{target_chat_id}:{day_key}:cancel_edit:{owner_day_key}'), IB('⬅️ Назад осн. окно', callback_data=f'fv:{target_chat_id}:{day_key}:open:{owner_day_key}'))
    return kb

def send_or_edit_edit_prompt(chat_id: int, store_key: str, text: str, reply_markup=None, parse_mode=None):
    """Окно редактирования записи не плодится: старое сообщение редактируется, новое создаётся только если старое недоступно."""
    store = get_chat_store(chat_id)
    prev = store.get(store_key) or {}
    prev_id = prev.get('prompt_msg_id') if isinstance(prev, dict) else None
    if prev_id:
        try:
            _tg_call_retry(bot.edit_message_text, text, chat_id=chat_id, message_id=int(prev_id), reply_markup=reply_markup, parse_mode=parse_mode, purpose='edit_prompt_edit_message')
            return int(prev_id)
        except Exception as e:
            err = str(e).lower()
            if 'message is not modified' in err:
                return int(prev_id)
            try:
                bot.delete_message(chat_id, int(prev_id))
            except Exception:
                pass
    sent = _tg_call_retry(bot.send_message, chat_id, text, reply_markup=reply_markup, parse_mode=parse_mode, purpose='edit_prompt_send_message')
    return sent.message_id
# v262
