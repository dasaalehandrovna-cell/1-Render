# v262

# --- ИСТОЧНИК: 60_finance_currency.py ---
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
    # R24: FAST/UI window construction never waits for Redis or DolarAPI. A stale
    # local rate is good enough for the first render; refresh happens after it.
    _r24_thread_name = threading.current_thread().name.casefold()
    _r24_ui_thread = _r24_thread_name.startswith(('fast-ui', 'ui-', 'start-ui', 'window-render'))
    if not force and _r24_ui_thread:
        try:
            submit_unique = getattr(GENERAL_TASK_POOL, 'submit_unique', None)
            if callable(submit_unique):
                submit_unique('r24-usd-rate-refresh', usd_rate_cached, True)
            else:
                GENERAL_TASK_POOL.submit('r24-usd-rate-refresh', usd_rate_cached, True)
        except Exception:
            pass
        return cache if cache.get('rate') else None
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
    """R48 migration: RAM mutation under chat lock, persistence after unlock."""
    cid=int(chat_id); changed=0
    with locked_chat(cid):
        store=get_chat_store(cid); settings=store.setdefault('settings',{})
        if settings.get('usd_transactions_migrated_v93'): return 0
        for rec in store.get('records',[]) or []:
            if rec.get('usd_amount') is not None: continue
            note=str(rec.get('note') or '').strip(); low=note.casefold()
            likely=bool(re.search('usd|усд|\\$',low) or (('к' in low or re.search('\\bk\\b',low)) and (USD_EXCHANGE_RE.search(low) or re.search('\\bот\\b',low) or '+к' in low or '+k' in low)))
            if not likely: continue
            try: old_amount=float(rec.get('amount',0) or 0)
            except Exception: old_amount=0.0
            if re.search('(?i)(?:^|\\s)и\\s*\\+[kк]\\b',low):
                rec['usd_amount']=abs(old_amount)*1000.0; rec['usd_note']=''; rec['usd_only']=True; rec['source_finance_text']=f'И {fmt_num_compact(abs(old_amount))}+к'; rec['amount']=0.0; changed+=1; continue
            sign='+' if old_amount>0 else ''; amount_text=fmt_num_compact(abs(old_amount)); explicit=extract_usd_transaction(note)
            if explicit is None and re.search('(?i)(?:usd|усд|\\$)',note):
                if USD_EXCHANGE_RE.search(low): sign=''
                insert_value=sign+amount_text; mcur=re.search('(?i)(?P<mult>[kк]\\s*)?(?P<cur>usd|усд|\\$)',note)
                reconstructed=(note[:mcur.start()]+insert_value+(mcur.group('mult') or '')+mcur.group('cur')+note[mcur.end():]).strip() if mcur else f'{insert_value} {note}'.strip()
            else: reconstructed=f'{sign}{amount_text} {note}'.strip()
            try: comp=parse_financial_components(reconstructed)
            except Exception: continue
            if comp.get('usd_amount') is None: continue
            rec['usd_amount']=float(comp.get('usd_amount') or 0); rec['usd_note']=str(comp.get('usd_note') or ''); rec['usd_only']=bool(comp.get('usd_only',False)); rec['source_finance_text']=reconstructed; rec['amount']=float(comp.get('amount',0) or 0); rec['note']=str(comp.get('note') or rec.get('note') or ''); changed+=1
        settings['usd_transactions_migrated_v93']=True
        if changed:
            normalize_chat_records(cid); recalc_balance(cid); rebuild_month_short_ids(cid)
    if changed:
        rebuild_global_records()
    save_data(data,chat_ids=[cid])
    if changed:
        try: bot_journal('usd_v93_migration',cid,f'records={changed}')
        except Exception: pass
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
    store = get_chat_store(int(chat_id))
    if '_usd_balance_cache_r16' in store:
        try: return float(store.get('_usd_balance_cache_r16', 0) or 0)
        except Exception: store.pop('_usd_balance_cache_r16', None)
    total = 0.0
    for rec in store.get('records', []) or []:
        try: total += float(rec.get('usd_amount', 0) or 0)
        except Exception: pass
    store['_usd_balance_cache_r16'] = float(total)
    return float(total)

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

# --- ИСТОЧНИК: 61_forwarding_ui.py ---
def build_forward_root_menu(day_key: str):
    """Корневое меню пересылки: старый режим или новый визуальный режим пары A/B."""
    if forward_menu_new_style_enabled():
        return build_forward_new_menu(day_key)
    return build_forward_source_menu(day_key)

def _v177_legacy_0180_collect_forward_picker_items(include_owner: bool=True, include_removed: bool=False):
    known = collect_forward_menu_chats()
    items = []
    owner_item = None
    for cid, ch in sorted(known.items(), key=lambda x: (x[1].get('title') or '').lower()):
        try:
            int_cid = int(cid)
        except Exception:
            continue
        title = ch.get('title') or f'Чат {cid}'
        if OWNER_ID and str(int_cid) == str(OWNER_ID):
            owner_item = (int_cid, title)
        else:
            if not include_removed and is_chat_bot_removed(int_cid):
                continue
            items.append((int_cid, title))
    if include_owner and OWNER_ID:
        try:
            owner_id = int(OWNER_ID)
            if owner_item is None:
                owner_item = (owner_id, get_chat_display_name(owner_id))
        except Exception:
            owner_item = None
    return (items, owner_item)
try:
    _v177_legacy_0180_collect_forward_picker_items.__name__ = '_collect_forward_picker_items'
except Exception:
    pass

def _chat_description_origin_back(origin: str, day_key: str) -> str:
    return f'd:{day_key}:forward_finmode_menu' if str(origin) == 'finmode' else f'd:{day_key}:forward_menu'

def _v177_legacy_0183_build_chat_description_menu(viewer_chat_id: int, origin: str, day_key: str):
    kb = types.InlineKeyboardMarkup(row_width=2)
    buttons = []
    for cid in collect_all_known_chat_ids(include_owner=True):
        try:
            if is_chat_bot_removed(int(cid)):
                continue
        except Exception:
            pass
        buttons.append(IB(chat_button_title(int(cid)), callback_data=f'chat_desc_open:{origin}:{int(cid)}'))
    add_buttons_in_rows(kb, buttons, 2)
    kb.row(IB('🔙 Назад', callback_data=_chat_description_origin_back(origin, day_key)))
    kb.row(IB('⬅️ Назад осн. окно', callback_data=f'd:{day_key}:back_main'))
    return kb
try:
    _v177_legacy_0183_build_chat_description_menu.__name__ = 'build_chat_description_menu'
except Exception:
    pass

def build_chat_description_menu_text() -> str:
    return 'ℹ️ Описание чатов\n\nВыберите чат. Бот покажет карточку Telegram, количество участников, администраторов и пользователей, которых он реально видел в сообщениях.'

def _chat_user_line(user, prefix: str='') -> str:
    try:
        uid = int(getattr(user, 'id', 0) or 0)
        first = str(getattr(user, 'first_name', '') or '')
        last = str(getattr(user, 'last_name', '') or '')
        name = (first + ' ' + last).strip() or 'Без имени'
        username = str(getattr(user, 'username', '') or '').lstrip('@')
        premium = 'Premium' if bool(getattr(user, 'is_premium', False)) else 'обычный'
        bot_mark = 'бот' if bool(getattr(user, 'is_bot', False)) else premium
        return f'{prefix}{name}' + (f' (@{username})' if username else '') + f' — ID {uid}; {bot_mark}'
    except Exception:
        return f'{prefix}не удалось прочитать пользователя'

def _known_user_line(row: dict, prefix: str='') -> str:
    row = row or {}
    name = (str(row.get('first_name') or '') + ' ' + str(row.get('last_name') or '')).strip() or 'Без имени'
    username = str(row.get('username') or '').lstrip('@')
    kind = 'бот' if row.get('is_bot') else 'Premium' if row.get('is_premium') else 'обычный'
    return f'{prefix}{name}' + (f' (@{username})' if username else '') + f" — ID {row.get('id')}; {kind}; видел: {row.get('last_seen') or 'неизвестно'}"
_CHAT_DESCRIPTION_CACHE_LOCK = threading.RLock()
_CHAT_DESCRIPTION_CACHE = {}
_CHAT_DESCRIPTION_CACHE_SECONDS = 300.0

def _split_chat_description_pages(text: str, limit: int=3300):
    lines = str(text or '').splitlines()
    pages, current, size = ([], [], 0)
    for line in lines:
        chunk = str(line)
        pieces = [chunk[i:i + limit] for i in range(0, len(chunk), limit)] or ['']
        for piece in pieces:
            add = len(piece) + 1
            if current and size + add > limit:
                pages.append('\n'.join(current))
                current, size = ([], 0)
            current.append(piece)
            size += add
    if current or not pages:
        pages.append('\n'.join(current))
    total = len(pages)
    return [f'{page}\n\nСтраница {idx}/{total}' for idx, page in enumerate(pages, 1)]

def get_chat_description_pages(target_chat_id: int, refresh: bool=False):
    key = int(target_chat_id)
    now_ts = time.time()
    if not refresh:
        with _CHAT_DESCRIPTION_CACHE_LOCK:
            cached = _CHAT_DESCRIPTION_CACHE.get(key)
            if cached and now_ts < float(cached.get('expires') or 0):
                return list(cached.get('pages') or [])
    text = build_chat_description_detail(key)
    pages = _split_chat_description_pages(text)
    with _CHAT_DESCRIPTION_CACHE_LOCK:
        _CHAT_DESCRIPTION_CACHE[key] = {'pages': list(pages), 'expires': now_ts + _CHAT_DESCRIPTION_CACHE_SECONDS}
    return pages

def build_chat_description_detail(target_chat_id: int) -> str:
    target_chat_id = int(target_chat_id)
    store = get_chat_store(target_chat_id)
    info = store.get('info') or {}
    chat_obj = None
    errors = []
    try:
        chat_obj = _tg_call_retry(bot.get_chat, target_chat_id, attempts=2, purpose='chat_description_get_chat')
        update_chat_info_from_chat_object(chat_obj)
    except Exception as exc:
        errors.append(f'getChat: {str(exc)[:180]}')

    def attr(name, default=None):
        return getattr(chat_obj, name, default) if chat_obj is not None else info.get(name, default)
    title = str(attr('title', '') or '').strip()
    first = str(attr('first_name', '') or '').strip()
    last = str(attr('last_name', '') or '').strip()
    if not title:
        title = (first + ' ' + last).strip() or get_chat_display_name(target_chat_id)
    username = str(attr('username', '') or '').strip().lstrip('@')
    chat_type = str(attr('type', info.get('type') or 'unknown') or 'unknown')
    member_count = None
    try:
        fn = getattr(bot, 'get_chat_member_count', None) or getattr(bot, 'get_chat_members_count', None)
        if fn:
            member_count = int(_tg_call_retry(fn, target_chat_id, attempts=2, purpose='chat_description_member_count'))
    except Exception as exc:
        errors.append(f'memberCount: {str(exc)[:160]}')
    admins = []
    if chat_type in {'group', 'supergroup', 'channel'}:
        try:
            admins = list(_tg_call_retry(bot.get_chat_administrators, target_chat_id, attempts=2, purpose='chat_description_admins') or [])
        except Exception as exc:
            errors.append(f'administrators: {str(exc)[:160]}')
    lines = ['ℹ️ Полное описание чата', '', f'Название: {title}', f'ID чата: {target_chat_id}', f'Тип: {chat_type}', f'Username: @{username}' if username else 'Username: нет']
    if member_count is not None:
        lines.append(f'Количество участников: {member_count}')
    for label, name in (('Описание', 'description'), ('Bio', 'bio'), ('Ссылка-приглашение', 'invite_link'), ('Связанный чат', 'linked_chat_id'), ('Автоудаление, сек', 'message_auto_delete_time'), ('Медленный режим, сек', 'slow_mode_delay')):
        value = attr(name, None)
        if value not in (None, '', 0, False):
            lines.append(f'{label}: {value}')
    lines.extend([f"Форум: {('да' if bool(attr('is_forum', False)) else 'нет')}", f"Защищённый контент: {('да' if bool(attr('has_protected_content', False)) else 'нет')}", f"Бот удалён/нет доступа: {('да' if is_chat_bot_removed(target_chat_id) else 'нет')}", f"Финансовый режим: {('включён' if is_finance_mode(target_chat_id) else 'выключен')}", f"Скрытые финансы: {('включены' if is_hidden_finance_mode(target_chat_id) else 'выключены')}", ''])
    if chat_type == 'private':
        try:
            member = _tg_call_retry(bot.get_chat_member, target_chat_id, target_chat_id, attempts=1, purpose='chat_description_private_member')
            user = getattr(member, 'user', None)
            if user:
                lines.append('Пользователь:')
                lines.append(_chat_user_line(user, '• '))
        except Exception:
            known = list((store.get('known_users') or {}).values())
            if known:
                lines.append('Пользователь, которого видел бот:')
                lines.append(_known_user_line(known[-1], '• '))
    else:
        lines.append(f'Администраторы: {len(admins)}')
        for member in admins[:100]:
            user = getattr(member, 'user', None)
            status = str(getattr(member, 'status', '') or '')
            custom_title = str(getattr(member, 'custom_title', '') or '')
            suffix = f'; статус {status}' + (f'; должность {custom_title}' if custom_title else '')
            lines.append((_chat_user_line(user, '• ') if user else '• неизвестный администратор') + suffix)
        known_users = list((store.get('known_users') or {}).values())
        known_users.sort(key=lambda row: float((row or {}).get('last_seen_ts') or 0), reverse=True)
        admin_ids = {int(getattr(getattr(m, 'user', None), 'id', 0) or 0) for m in admins}
        known_non_admin = [row for row in known_users if int((row or {}).get('id') or 0) not in admin_ids]
        lines.extend(['', f'Другие пользователи, которых видел бот: {len(known_non_admin)}'])
        for row in known_non_admin[:150]:
            lines.append(_known_user_line(row, '• '))
        lines.extend(['', 'Важно: обычный Telegram Bot API не отдаёт боту полный список всех участников группы. Поэтому здесь показаны точное количество, администраторы и накопленный список пользователей, писавших после включения этого учёта.'])
    if errors:
        lines.extend(['', 'Ограничения/ошибки получения:'] + [f'• {e}' for e in errors])
    return '\n'.join(lines)

def build_chat_description_detail_keyboard(viewer_chat_id: int, origin: str, day_key: str, target_chat_id: int=0, page: int=0, total_pages: int=1):
    kb = types.InlineKeyboardMarkup(row_width=2)
    target_chat_id = int(target_chat_id or 0)
    page = max(0, int(page or 0))
    total_pages = max(1, int(total_pages or 1))
    if total_pages > 1 and target_chat_id:
        nav = []
        if page > 0:
            nav.append(IB('⬅️ Предыдущая', callback_data=f'chat_desc_page:{origin}:{target_chat_id}:{page - 1}'))
        nav.append(IB(f'{page + 1}/{total_pages}', callback_data='none'))
        if page + 1 < total_pages:
            nav.append(IB('Следующая ➡️', callback_data=f'chat_desc_page:{origin}:{target_chat_id}:{page + 1}'))
        kb.row(*nav)
    kb.row(IB('🔄 Обновить данные', callback_data=f'chat_desc_open:{origin}:{target_chat_id}' if target_chat_id else f'chat_desc_menu:{origin}'))
    kb.row(IB('🔙 Назад к чатам', callback_data=f'chat_desc_menu:{origin}'))
    kb.row(IB('🔙 Назад в предыдущее меню', callback_data=_chat_description_origin_back(origin, day_key)))
    kb.row(IB('⬅️ Назад осн. окно', callback_data=f'd:{day_key}:back_main'))
    return kb

def _v177_legacy_0185_build_forward_source_menu(day_key: str | None=None):
    if forward_menu_new_style_enabled():
        return build_forward_new_menu(day_key)
    kb = types.InlineKeyboardMarkup(row_width=3)
    if not OWNER_ID:
        return kb
    items, owner_item = _collect_forward_picker_items(include_owner=True)
    buttons = [IB(chat_button_title(cid, title), callback_data=f'fw_src:{cid}') for cid, title in items]
    add_buttons_in_rows(kb, buttons, 2)
    if owner_item:
        kb.row(IB(chat_button_title(owner_item[0], owner_item[1]), callback_data=f'fw_src:{owner_item[0]}'))
    kb.row(IB('ℹ️ Описание чатов', callback_data='chat_desc_menu:forward'))
    kb.row(IB('📡 Проверить чаты', callback_data='fw_probe_all'), IB('🗑 Удалённые', callback_data='fw_removed_list'))
    if day_key:
        kb.row(IB('🔙 Назад', callback_data=f'd:{day_key}:back_main'))
    else:
        kb.row(IB('🔙 Назад', callback_data='fw_back_root'))
    return kb
try:
    _v177_legacy_0185_build_forward_source_menu.__name__ = 'build_forward_source_menu'
except Exception:
    pass

def _v177_legacy_0186_build_forward_target_menu(src_id: int):
    kb = types.InlineKeyboardMarkup()
    if not OWNER_ID:
        return kb
    items, owner_item = _collect_forward_picker_items(include_owner=True)
    buttons = []
    for int_cid, title in items:
        if int_cid == src_id:
            continue
        buttons.append(IB(chat_button_title(int_cid, title), callback_data=f'fw_tgt:{src_id}:{int_cid}'))
    add_buttons_in_rows(kb, buttons, 2)
    if owner_item and owner_item[0] != src_id:
        kb.row(IB(chat_button_title(owner_item[0], owner_item[1]), callback_data=f'fw_tgt:{src_id}:{owner_item[0]}'))
    kb.row(IB('🔙 Назад', callback_data='fw_back_src'))
    return kb
try:
    _v177_legacy_0186_build_forward_target_menu.__name__ = 'build_forward_target_menu'
except Exception:
    pass

def _forward_pair_key(A: int, B: int) -> str:
    return f'{int(A)}:{int(B)}'

def _forward_pair_undirected_key(A: int, B: int) -> tuple[int, int]:
    A = int(A)
    B = int(B)
    return (A, B) if A <= B else (B, A)

def _v177_legacy_0187_remember_forward_pair(A: int, B: int):
    """Сохраняет порядок создания пар для нового В22. Старую логику пересылки не трогает."""
    try:
        A, B = (int(A), int(B))
        if A == B:
            return
        key = _forward_pair_key(A, B)
        rev = _forward_pair_key(B, A)
        order = data.setdefault('forward_pair_order', [])
        if not isinstance(order, list):
            order = []
            data['forward_pair_order'] = order
        if key not in order and rev not in order:
            order.append(key)
            save_data(data)
    except Exception as e:
        log_error(f'_remember_forward_pair({A},{B}): {e}')
try:
    _v177_legacy_0187_remember_forward_pair.__name__ = '_remember_forward_pair'
except Exception:
    pass

def _v177_legacy_0188_forget_forward_pair_if_empty(A: int, B: int):
    """Убирает пару из порядка, только если уже нет ни пересылки, ни 💰 финучёта в обе стороны."""
    try:
        A, B = (int(A), int(B))
        arrow, fin, ab_on, ba_on, ab_fin, ba_fin = _forward_pair_icons(A, B)
        if ab_on or ba_on or ab_fin or ba_fin:
            return
        key = _forward_pair_key(A, B)
        rev = _forward_pair_key(B, A)
        order = data.setdefault('forward_pair_order', [])
        if isinstance(order, list) and (key in order or rev in order):
            data['forward_pair_order'] = [x for x in order if x not in {key, rev}]
            save_data(data)
    except Exception as e:
        log_error(f'_forget_forward_pair_if_empty({A},{B}): {e}')
try:
    _v177_legacy_0188_forget_forward_pair_if_empty.__name__ = '_forget_forward_pair_if_empty'
except Exception:
    pass

def _forward_pair_sort_key(pair):
    try:
        order = data.get('forward_pair_order', []) or []
        key = _forward_pair_key(pair[0], pair[1])
        rev = _forward_pair_key(pair[1], pair[0])
        if key in order:
            return (0, order.index(key))
        if rev in order:
            return (0, order.index(rev))
        a, b = pair
        return (1, get_chat_display_name(int(a)).lower(), get_chat_display_name(int(b)).lower(), int(a), int(b))
    except Exception:
        return (9, str(pair))

def _sorted_forward_pair(a: int, b: int):
    """Старый helper оставлен для совместимости. Новый В22 порядок выбора не сортирует."""
    a = int(a)
    b = int(b)
    ka = (get_chat_display_name(a).lower(), a)
    kb = (get_chat_display_name(b).lower(), b)
    return (a, b) if ka <= kb else (b, a)

def _v177_legacy_0189_collect_forward_pairs_for_menu() -> list[tuple[int, int]]:
    """Все пары, где есть пересылка или 💰 финучёт пересылки. Порядок пары берём из создания/первого обнаружения."""
    relation_pairs = []
    seen = set()
    fr = data.get('forward_rules', {}) or {}
    ff = data.get('forward_finance', {}) or {}

    def _add_pair(a, b):
        try:
            a = int(a)
            b = int(b)
        except Exception:
            return
        if a == b:
            return
        uk = _forward_pair_undirected_key(a, b)
        if uk in seen:
            return
        seen.add(uk)
        relation_pairs.append((a, b))
    order = data.get('forward_pair_order', []) or []
    if isinstance(order, list):
        for key in order:
            try:
                a_s, b_s = str(key).split(':', 1)
                a, b = (int(a_s), int(b_s))
            except Exception:
                continue
            arrow, fin, ab_on, ba_on, ab_fin, ba_fin = _forward_pair_icons(a, b)
            if ab_on or ba_on or ab_fin or ba_fin:
                _add_pair(a, b)
    for src, dsts in fr.items():
        for dst in (dsts or {}).keys():
            _add_pair(src, dst)
    for src, dsts in ff.items():
        for dst, enabled in (dsts or {}).items():
            if enabled:
                _add_pair(src, dst)
    try:
        order = data.setdefault('forward_pair_order', [])
        if not isinstance(order, list):
            order = []
            data['forward_pair_order'] = order
        changed = False
        for A, B in relation_pairs:
            key = _forward_pair_key(A, B)
            rev = _forward_pair_key(B, A)
            if key not in order and rev not in order:
                order.append(key)
                changed = True
        if changed:
            save_data(data)
    except Exception:
        pass
    return sorted(relation_pairs, key=_forward_pair_sort_key)
try:
    _v177_legacy_0189_collect_forward_pairs_for_menu.__name__ = 'collect_forward_pairs_for_menu'
except Exception:
    pass

def _forward_pair_icons(A: int, B: int):
    fr = data.get('forward_rules', {}) or {}
    ff = data.get('forward_finance', {}) or {}
    ab_on = str(B) in (fr.get(str(A), {}) or {})
    ba_on = str(A) in (fr.get(str(B), {}) or {})
    ab_fin = bool((ff.get(str(A), {}) or {}).get(str(B), False))
    ba_fin = bool((ff.get(str(B), {}) or {}).get(str(A), False))
    return (_forward_arrow_icon(ab_on, ba_on), _forward_fin_icon(ab_fin, ba_fin), ab_on, ba_on, ab_fin, ba_fin)

def _forward_new_pair_buttons(A: int, B: int):
    """Две кнопки пары сверху в новом В22.

    По уточнённому ТЗ:
    • кнопка Чата A сверху остаётся выбором этого чата как нового Чата A;
    • кнопка Чата B сверху открывает настройки именно этой пары и помечается 🛠️ перед именем;
    • ниже разделителя Чаты A из готовых пар не дублируются, чтобы список не захламлялся.
    """
    arrow, fin, *_ = _forward_pair_icons(A, B)
    return (IB(f'{chat_button_title(A)} ({arrow})', callback_data=f'fw_new_src:{A}'), IB(f'({fin}) 🛠️ {chat_button_title(B)}', callback_data=f'fw_new_pair:{A}:{B}'))

def _forward_new_toggle_label(enabled: bool, icon: str) -> str:
    return ('✅' if enabled else '⬜') + icon

def _visible_forward_items_for_new_menu(include_owner: bool=True):
    items, owner_item = _collect_forward_picker_items(include_owner=include_owner)
    all_items = list(items)
    if owner_item:
        all_items.append(owner_item)
    visible = []
    for cid, title in all_items:
        try:
            if is_chat_bot_removed(int(cid)):
                continue
        except Exception:
            pass
        visible.append((int(cid), title))
    return visible

def build_forward_new_text(A: int | None=None, B: int | None=None) -> str:
    """В22 новый режим: пары сверху, выбор A/B и настройка шести кнопок."""
    lines = ['🔁 Пересылка / В22', 'Режим: по-новому', '']
    if A and B:
        arrow, fin, *_ = _forward_pair_icons(A, B)
        lines.append(f'Чат А: {get_chat_display_name(A)} ({arrow})')
        lines.append(f'Чат Б: ({fin}) {get_chat_display_name(B)}')
        lines.append('Ниже выбери направление пересылки и 💰 финучёт.')
    elif A:
        lines.append(f'Чат А выбран: {get_chat_display_name(A)}')
        lines.append('Теперь выбери Чат Б. Остальные чаты остаются ниже по 2 кнопки в ряд.')
    else:
        lines.append('Сверху пары со связями. Ниже — все доступные чаты. Любой чат можно снова выбрать как Чат А.')
    return '\n'.join(lines)

def _v177_legacy_0193_build_forward_new_menu(day_key: str | None=None, A: int | None=None, B: int | None=None):
    """
    Новый В22 по уточнённому ТЗ:
    • старт: пары сверху по 2 кнопки (A слева, B справа), потом пустой разделитель, потом свободные чаты по 2 кнопки;
    • выбран A: кнопка Чат А сверху, остальные чаты остаются ниже по 2 кнопки;
    • выбран B: сверху Чат А / Чат Б, ниже 6 кнопок режимов, ниже кнопка возврата к выбору чатов.
    """
    kb = types.InlineKeyboardMarkup(row_width=2)
    if not OWNER_ID:
        return kb
    visible_items = _visible_forward_items_for_new_menu(include_owner=True)
    pair_rows = collect_forward_pairs_for_menu()
    if A and B:
        A, B = (int(A), int(B))
        arrow, fin, ab_on, ba_on, ab_fin, ba_fin = _forward_pair_icons(A, B)
        kb.row(IB(f'Чат А: {chat_button_title(A)}', callback_data=f'fw_new_pair:{A}:{B}'), IB(f'Чат Б: {chat_button_title(B)}', callback_data=f'fw_new_pair:{A}:{B}'))
        kb.row(IB(_forward_new_toggle_label(ba_on, '⏪️'), callback_data=f'fw_new_mode:{A}:{B}:from'), IB(_forward_new_toggle_label(ab_on, '⏩️'), callback_data=f'fw_new_mode:{A}:{B}:to'), IB(_forward_new_toggle_label(ab_on and ba_on, '🔄'), callback_data=f'fw_new_mode:{A}:{B}:two'), IB(_forward_new_toggle_label(ba_fin, '◀️'), callback_data=f'fw_new_fin:{A}:{B}:ba'), IB(_forward_new_toggle_label(ab_fin, '▶️'), callback_data=f'fw_new_fin:{A}:{B}:ab'), IB('❌', callback_data=f'fw_new_clear:{A}:{B}'))
        kb.row(IB('🔙 Назад в окно выбора чатов', callback_data='fw_new_back_src'))
        return kb
    if A:
        A = int(A)
        kb.row(IB(f'Чат А: {chat_button_title(A)}', callback_data=f'fw_new_src:{A}'))
        buttons = []
        for cid, title in visible_items:
            if int(cid) == int(A):
                continue
            buttons.append(IB(f'Чат Б: {chat_button_title(cid, title)}', callback_data=f'fw_new_tgt:{A}:{int(cid)}'))
        if buttons:
            add_buttons_in_rows(kb, buttons, 2)
        else:
            kb.row(IB('Нет чатов для выбора Чата Б', callback_data='none'))
        kb.row(IB('🔙 Назад в окно выбора чатов', callback_data='fw_new_back_src'))
        return kb
    shown_pairs = 0
    top_pair_a_ids = set()
    for A0, B0 in pair_rows:
        try:
            if is_chat_bot_removed(A0) or is_chat_bot_removed(B0):
                continue
        except Exception:
            pass
        top_pair_a_ids.add(int(A0))
        left_btn, right_btn = _forward_new_pair_buttons(A0, B0)
        kb.row(left_btn, right_btn)
        shown_pairs += 1
    chat_buttons = []
    for cid, title in visible_items:
        if int(cid) in top_pair_a_ids:
            continue
        chat_buttons.append(IB(chat_button_title(cid, title), callback_data=f'fw_new_src:{cid}'))
    if shown_pairs and chat_buttons:
        kb.row(IB('⠀', callback_data='none'))
    if chat_buttons:
        add_buttons_in_rows(kb, chat_buttons, 2)
    elif not shown_pairs:
        kb.row(IB('Нет доступных чатов', callback_data='none'))
    kb.row(IB('ℹ️ Описание чатов', callback_data='chat_desc_menu:forward'))
    kb.row(IB('📡 Проверить чаты', callback_data='fw_probe_all'), IB('🗑 Удалённые', callback_data='fw_removed_list'))
    if day_key:
        kb.row(IB('🔙 Назад', callback_data=f'd:{day_key}:back_main'))
    else:
        kb.row(IB('🔙 Назад', callback_data='fw_back_root'))
    return kb
try:
    _v177_legacy_0193_build_forward_new_menu.__name__ = 'build_forward_new_menu'
except Exception:
    pass

def _v177_legacy_0194_build_forward_menu_text_for_current_mode(title: str | None=None, A: int | None=None, B: int | None=None) -> str:
    if forward_menu_new_style_enabled():
        return build_forward_new_text(A, B)
    return build_forward_status_text(title or 'Пересылка:\nВыберите чат A:')
try:
    _v177_legacy_0194_build_forward_menu_text_for_current_mode.__name__ = 'build_forward_menu_text_for_current_mode'
except Exception:
    pass

def _v177_legacy_0195_build_forward_menu_keyboard_for_current_mode(day_key: str | None=None, A: int | None=None, B: int | None=None):
    if forward_menu_new_style_enabled():
        return build_forward_new_menu(day_key, A, B)
    if A and B:
        return build_forward_mode_menu(A, B)
    if A:
        return build_forward_target_menu(A)
    return build_forward_source_menu(day_key)
try:
    _v177_legacy_0195_build_forward_menu_keyboard_for_current_mode.__name__ = 'build_forward_menu_keyboard_for_current_mode'
except Exception:
    pass

# --- ИСТОЧНИК: 62_finance_ui.py ---
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
    chat_id=int(chat_id)
    with locked_chat(chat_id):
        store=get_chat_store(chat_id); selected={int(x) for x in store.setdefault('usd_edit_delete_selected',{}).get(str(day_key),[]) or []}
        if not selected: return 0
        deleted=0; remove_ids=set(); deleted_usd=0.0
        for rec in store.get('records',[]) or []:
            try: rid=int(rec.get('id',-1))
            except Exception: continue
            if rid not in selected or not float(rec.get('usd_amount',0) or 0): continue
            deleted+=1; deleted_usd+=float(rec.get('usd_amount',0) or 0)
            if abs(float(rec.get('amount',0) or 0))<=0 and bool(rec.get('usd_only',False)): remove_ids.add(rid)
            else: rec['usd_amount']=0.0; rec['usd_note']=''; rec['usd_only']=False
        if remove_ids: store['records']=[r for r in store.get('records',[]) or [] if int(r.get('id',-1)) not in remove_ids]
        for dk,arr in list((store.get('daily_records',{}) or {}).items()):
            new=[]
            for rec in arr or []:
                try: rid=int(rec.get('id',-1))
                except Exception: new.append(rec); continue
                if rid in remove_ids: continue
                if rid in selected and float(rec.get('usd_amount',0) or 0): rec['usd_amount']=0.0; rec['usd_note']=''; rec['usd_only']=False
                new.append(rec)
            if new: store['daily_records'][dk]=new
            else: store['daily_records'].pop(dk,None)
        store.setdefault('usd_edit_delete_selected',{}).pop(str(day_key),None)
        store['_finance_hotpath_pending_normalize_r16']=True; store['_finance_fast_generation_r16']=int(store.get('_finance_fast_generation_r16',0) or 0)+1; store.pop('_finance_day_balance_cache_r16',None)
        if '_usd_balance_cache_r16' in store:
            try: store['_usd_balance_cache_r16']=float(store.get('_usd_balance_cache_r16',0) or 0)-deleted_usd
            except Exception: store.pop('_usd_balance_cache_r16',None)
    persist_finance_chat_local_fast(chat_id)
    if callable(globals().get('_v262_schedule_finance_postcommit')): _v262_schedule_finance_postcommit(chat_id,str(day_key),'delete_selected_usd')
    else: rebuild_global_records(); finance_changed(chat_id,str(day_key),reason='delete_selected_usd',delay=0.1)
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
    if globals().get('constitution_finance_write_blocked_v232') and constitution_finance_write_blocked_v232(): return 0
    op_id=''; deleted_snapshot=[]; selected=set(); deleted=0
    # Read the selection under the short chat lock, then create durable operation intent outside it.
    with locked_chat(chat_id):
        store=get_chat_store(chat_id); all_sel=store.setdefault('edit_delete_selected',{}); selected={int(x) for x in all_sel.get(day_key,[])}
    if not selected: return 0
    op_id=operation_begin('finance_bulk_delete',chat_id,target=str(day_key),payload={'selected':sorted(selected)},critical=True) if 'operation_begin' in globals() else ''
    with locked_chat(chat_id):
        store=get_chat_store(chat_id); all_sel=store.setdefault('edit_delete_selected',{})
        selected={int(x) for x in all_sel.get(day_key,[]) if int(x) in selected}
        if not selected: return 0
        deleted_snapshot=[dict(r) for r in store.get('records',[]) or [] if int(r.get('id',-1)) in selected]
        before=len(store.get('records',[]) or []); store['records']=[r for r in store.get('records',[]) or [] if int(r.get('id',-1)) not in selected]
        daily=store.get('daily_records',{}) or {}
        for dk in list(daily.keys()):
            arr2=[r for r in (daily.get(dk,[]) or []) if int(r.get('id',-1)) not in selected]
            if arr2: daily[dk]=arr2
            else: daily.pop(dk,None)
        deleted=before-len(store.get('records',[]) or []); all_sel.pop(day_key,None)
        try: store['balance']=float(store.get('balance',0) or 0)-sum(float(r.get('amount',0) or 0) for r in deleted_snapshot)
        except Exception: pass
        store['_finance_hotpath_pending_normalize_r16']=True; store['_finance_fast_generation_r16']=int(store.get('_finance_fast_generation_r16',0) or 0)+1; store.pop('_finance_day_balance_cache_r16',None)
        if '_usd_balance_cache_r16' in store:
            try: store['_usd_balance_cache_r16']=float(store.get('_usd_balance_cache_r16',0) or 0)-sum(float(r.get('usd_amount',0) or 0) for r in deleted_snapshot)
            except Exception: store.pop('_usd_balance_cache_r16',None)
    persist_finance_chat_local_fast(chat_id)
    if callable(globals().get('_v262_schedule_finance_postcommit')): _v262_schedule_finance_postcommit(chat_id,day_key,'delete_selected')
    else:
        rebuild_global_records(); schedule_financial_window_refresh(chat_id,day_key,reason='record_delete_fast_v168'); finance_changed(chat_id,day_key,reason='delete_selected',delay=0.1)
    try: finance_cache_invalidate(chat_id,'finance_bulk_delete'); finance_integrity_append(chat_id,'bulk_delete',{'ids':sorted(selected)},details={'records':deleted_snapshot})
    except Exception as exc: log_error(f'finance bulk delete integrity: {exc}')
    if op_id and 'operation_complete' in globals(): operation_complete(op_id,f'deleted={deleted}')
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

# --- ИСТОЧНИК: 63_google_sheets.py ---
GOOGLE_SERVICE_ACCOUNT_JSON = os.getenv('GOOGLE_SERVICE_ACCOUNT_JSON', '').strip()
GOOGLE_SHEETS_SHARE_EMAIL = os.getenv('GOOGLE_SHEETS_SHARE_EMAIL', '').strip()
GOOGLE_SHEETS_SPREADSHEET_ID = os.getenv('GOOGLE_SHEETS_SPREADSHEET_ID', '1RXAdbNeNaURYH6-G-3OQtiZmpkQHXo789wY6w78QsH0').strip()
_GOOGLE_TOKEN_CACHE = {'token': '', 'expires_at': 0.0}
_GOOGLE_TOKEN_LOCK = threading.RLock()

def _google_request_guarded(name: str, method, *args, attempts: int=1, **kwargs):
    """Circuit breaker/retry for safe Google calls; mutating requests use attempts=1."""
    gate = globals().get('external_access_allowed_v233')
    if callable(gate) and (not gate('google')):
        try:
            logger_fn = globals().get('external_block_log_v233')
            if callable(logger_fn):
                logger_fn('google', name)
        except Exception:
            pass
        raise RuntimeError(f'external_local_only_v233:google:{name}')
    guard = globals().get('guarded_external_call')
    if callable(guard):
        return guard(f'google:{name}', method, *args, attempts=max(1, int(attempts)), base_delay=0.7, **kwargs)
    return method(*args, **kwargs)

def _b64url(data: bytes) -> str:
    import base64
    return base64.urlsafe_b64encode(data).rstrip(b'=').decode('ascii')

def _v177_legacy_0205_google_service_account_info() -> dict:
    raw = GOOGLE_SERVICE_ACCOUNT_JSON
    if not raw:
        raise RuntimeError('Google Sheets API не настроен: добавьте GOOGLE_SERVICE_ACCOUNT_JSON в Render Environment')
    try:
        if raw.lstrip().startswith('{'):
            info = json.loads(raw)
        else:
            import base64
            info = json.loads(base64.b64decode(raw).decode('utf-8'))
    except Exception as exc:
        raise RuntimeError(f'GOOGLE_SERVICE_ACCOUNT_JSON повреждён: {exc}')
    for key in ('client_email', 'private_key', 'token_uri'):
        if not info.get(key):
            raise RuntimeError(f'GOOGLE_SERVICE_ACCOUNT_JSON: отсутствует {key}')
    return info
try:
    _v177_legacy_0205_google_service_account_info.__name__ = '_google_service_account_info'
except Exception:
    pass

def _google_sign_rs256(message: bytes, private_key_pem: str) -> bytes:
    """Подписывает JWT через системный openssl, без дополнительных pip-зависимостей."""
    key_path = msg_path = sig_path = None
    try:
        with tempfile.NamedTemporaryFile('w', encoding='utf-8', delete=False) as key_file:
            key_file.write(private_key_pem)
            key_path = key_file.name
        with tempfile.NamedTemporaryFile('wb', delete=False) as msg_file:
            msg_file.write(message)
            msg_path = msg_file.name
        sig_fd, sig_path = tempfile.mkstemp(prefix='google_jwt_', suffix='.sig')
        os.close(sig_fd)
        proc = subprocess.run(['openssl', 'dgst', '-sha256', '-sign', key_path, '-out', sig_path, msg_path], stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=20)
        if proc.returncode != 0:
            raise RuntimeError(proc.stderr.decode('utf-8', 'replace')[-500:])
        return Path(sig_path).read_bytes()
    finally:
        for path in (key_path, msg_path, sig_path):
            if path:
                try:
                    os.remove(path)
                except Exception:
                    pass

def _v177_legacy_0206_google_access_token() -> str:
    with _GOOGLE_TOKEN_LOCK:
        now = time.time()
        if _GOOGLE_TOKEN_CACHE.get('token') and now < float(_GOOGLE_TOKEN_CACHE.get('expires_at', 0)) - 120:
            return str(_GOOGLE_TOKEN_CACHE['token'])
        info = _google_service_account_info()
        header = {'alg': 'RS256', 'typ': 'JWT'}
        claims = {'iss': info['client_email'], 'scope': 'https://www.googleapis.com/auth/spreadsheets https://www.googleapis.com/auth/drive', 'aud': info.get('token_uri') or 'https://oauth2.googleapis.com/token', 'iat': int(now), 'exp': int(now) + 3600}
        signing_input = (_b64url(json.dumps(header, separators=(',', ':')).encode('utf-8')) + '.' + _b64url(json.dumps(claims, separators=(',', ':')).encode('utf-8'))).encode('ascii')
        signature = _google_sign_rs256(signing_input, info['private_key'])
        assertion = signing_input.decode('ascii') + '.' + _b64url(signature)
        response = _google_request_guarded('oauth', requests.post, info.get('token_uri') or 'https://oauth2.googleapis.com/token', data={'grant_type': 'urn:ietf:params:oauth:grant-type:jwt-bearer', 'assertion': assertion}, timeout=30, attempts=2)
        if response.status_code >= 300:
            raise RuntimeError(f'Google OAuth {response.status_code}: {response.text[:500]}')
        payload = response.json()
        token = str(payload.get('access_token') or '')
        if not token:
            raise RuntimeError('Google OAuth не вернул access_token')
        _GOOGLE_TOKEN_CACHE.update(token=token, expires_at=now + int(payload.get('expires_in', 3600) or 3600))
        return token
try:
    _v177_legacy_0206_google_access_token.__name__ = '_google_access_token'
except Exception:
    pass

def _google_cell_value(value):
    if isinstance(value, dict) and value.get('formula'):
        return {'formulaValue': '=' + str(value.get('formula') or '').lstrip('=')}
    if isinstance(value, bool):
        return {'boolValue': value}
    if isinstance(value, (int, float)) and (not isinstance(value, bool)):
        return {'numberValue': float(value)}
    return {'stringValue': str(value or '')}

def _google_category_fill(col_idx_zero: int) -> dict:
    palette = [(0.78, 0.94, 0.81), (0.87, 0.92, 0.97), (0.99, 0.89, 0.84), (0.89, 0.87, 0.93), (1.0, 0.95, 0.8), (0.85, 0.92, 0.83), (0.81, 0.89, 0.95), (0.96, 0.8, 0.8), (0.82, 0.88, 0.89), (0.92, 0.82, 0.86), (0.85, 0.82, 0.91)]
    if col_idx_zero >= 3:
        rgb = palette[(col_idx_zero - 3) % len(palette)]
        return {'red': rgb[0], 'green': rgb[1], 'blue': rgb[2]}
    return {'red': 0.92, 'green': 0.95, 'blue': 0.9}

def _v177_legacy_0207_google_spreadsheet_id(value: str | None=None) -> str:
    """Accepts either raw spreadsheet ID or a full docs.google.com/spreadsheets URL."""
    raw = str(value if value is not None else GOOGLE_SHEETS_SPREADSHEET_ID).strip()
    if not raw:
        raise RuntimeError('GOOGLE_SHEETS_SPREADSHEET_ID не задан')
    match = re.search('/spreadsheets/d/([A-Za-z0-9_-]+)', raw)
    if match:
        raw = match.group(1)
    raw = raw.split('?')[0].split('#')[0].strip().strip('/')
    if not re.fullmatch('[A-Za-z0-9_-]{20,}', raw):
        raise RuntimeError('GOOGLE_SHEETS_SPREADSHEET_ID имеет неверный формат')
    return raw
try:
    _v177_legacy_0207_google_spreadsheet_id.__name__ = '_google_spreadsheet_id'
except Exception:
    pass

def _google_sheet_tab_title(title: str) -> str:
    """Creates a short unique Google Sheets tab title safe for repeated exports."""
    base = re.sub('[\\\\/\\?\\*\\[\\]:]', ' ', str(title or 'Статьи'))
    base = re.sub('\\s+', ' ', base).strip(" ' ") or 'Статьи'
    stamp = datetime.now().strftime('%d.%m %H-%M-%S')
    suffix = f' · {stamp}'
    limit = max(1, 100 - len(suffix))
    return base[:limit].rstrip() + suffix

def _v177_legacy_0208_google_sheets_create_category_report(title: str, rows: list[list], layout: str='category', annotations_override: dict | None=None, include_annotations: bool=True) -> str:
    """v129: writes a category report to a NEW TAB in an existing owner-shared spreadsheet.

    The service account does not create/own a Drive file. The owner creates one spreadsheet once
    and shares it to the service-account client_email as Editor. Each export adds a new sheet tab
    and writes descriptions into native Google Sheets CellData.note.
    """
    token = _google_access_token()
    info = _google_service_account_info()
    service_email = str(info.get('client_email') or '').strip()
    spreadsheet_id = _google_spreadsheet_id()
    headers = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}
    meta = _google_request_guarded('metadata', requests.get, f'https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}', headers=headers, params={'fields': 'spreadsheetId,properties.title,sheets.properties(sheetId,title)'}, timeout=45, attempts=2)
    if meta.status_code >= 300:
        detail = meta.text[:700]
        if meta.status_code in (401, 403):
            raise RuntimeError(f'Google Sheets target access 403: сервисный аккаунт не имеет доступа к таблице. Откройте таблицу → Поделиться → добавьте {service_email} как Редактор. spreadsheet_id={spreadsheet_id}; Google: {detail}')
        raise RuntimeError(f'Google Sheets target {meta.status_code}: {detail}')
    layout = str(layout or 'category').strip().lower()
    if layout == 'compact':
        _styles, annotations, _freeze, _widths = _modern_compact_excel_styles_comments(rows, annotations_override or {})
    elif layout == 'category_compact':
        _styles, annotations, _freeze, _widths = _modern_category_no_description_styles_comments(rows, annotations_override or {})
    else:
        _styles, annotations, _freeze, _widths = _modern_category_excel_styles_comments(rows)
        if annotations_override is not None:
            annotations = dict(annotations_override or {})
    if not include_annotations:
        annotations = {}
    max_cols = max((len(row) for row in rows), default=1)
    row_count = max(100, len(rows) + 20)
    col_count = max(26, max_cols + 3)
    tab_title = _google_sheet_tab_title(title)
    add_sheet = _google_request_guarded('add_sheet', requests.post, f'https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}:batchUpdate', headers=headers, json={'requests': [{'addSheet': {'properties': {'title': tab_title, 'gridProperties': {'rowCount': row_count, 'columnCount': col_count, 'frozenRowCount': 1 if layout in {'compact', 'category_compact'} else 2}}}}]}, timeout=60, attempts=1)
    if add_sheet.status_code >= 300:
        raise RuntimeError(f'Google Sheets add tab {add_sheet.status_code}: {add_sheet.text[:700]}')
    add_payload = add_sheet.json()
    try:
        sheet_id = int(add_payload['replies'][0]['addSheet']['properties']['sheetId'])
    except Exception as exc:
        raise RuntimeError(f'Google Sheets API не вернул sheetId новой вкладки: {exc}')
    cell_rows = []
    for r_idx, row in enumerate(rows, start=1):
        values = []
        for c_idx in range(1, max_cols + 1):
            value = row[c_idx - 1] if c_idx - 1 < len(row) else ''
            cell = {'userEnteredValue': _google_cell_value(value)}
            note = str(annotations.get((r_idx, c_idx)) or '').strip()
            if note:
                cell['note'] = note
            row_is_blank = not any((_excel_nonempty(v) for v in row))
            first_label = str(row[0] if row else '').strip().casefold()
            second_label = str(row[1] if len(row) > 1 else '').strip().casefold()
            if r_idx == 1:
                cell['userEnteredFormat'] = {'textFormat': {'bold': True}, 'backgroundColor': _google_category_fill(c_idx - 1)}
            elif row_is_blank and layout in {'category', 'category_compact'}:
                cell['userEnteredFormat'] = {'backgroundColor': {'red': 1.0, 'green': 0.6, 'blue': 0.0}}
            elif first_label in {'расход', 'сумма по статьям'} or second_label in {'расход', 'сумма по статьям'}:
                cell['userEnteredFormat'] = {'textFormat': {'bold': True}, 'backgroundColor': {'red': 1.0, 'green': 0.55, 'blue': 0.55}}
            elif first_label in {'приход'} or second_label in {'приход'}:
                cell['userEnteredFormat'] = {'textFormat': {'bold': True}, 'backgroundColor': {'red': 0.55, 'green': 0.78, 'blue': 1.0}}
            elif first_label in {'остаток на руках', 'на руках:', 'гомонковые', 'остаток в обороте'} or second_label in {'остаток на руках', 'на руках:', 'гомонковые', 'остаток в обороте'}:
                cell['userEnteredFormat'] = {'textFormat': {'bold': True}, 'backgroundColor': {'red': 0.55, 'green': 0.85, 'blue': 0.55}}
            elif first_label == 'расход еды на человека в сутки' or second_label == 'расход еды на человека в сутки':
                cell['userEnteredFormat'] = {'textFormat': {'bold': True}, 'backgroundColor': {'red': 0.74, 'green': 0.82, 'blue': 1.0}}
            elif layout == 'compact' and c_idx in {2, 3} and (value not in ('', None)):
                cell['userEnteredFormat'] = {'backgroundColor': _google_category_fill(3 if c_idx == 3 else 2)}
            elif layout == 'category_compact' and c_idx >= 3 and (value not in ('', None)):
                cell['userEnteredFormat'] = {'backgroundColor': _google_category_fill(c_idx)}
            elif layout == 'category' and c_idx >= 4 and (value not in ('', None)):
                cell['userEnteredFormat'] = {'backgroundColor': _google_category_fill(c_idx - 1)}
            values.append(cell)
        cell_rows.append({'values': values})
    requests_payload = [{'updateCells': {'range': {'sheetId': sheet_id, 'startRowIndex': 0, 'startColumnIndex': 0}, 'rows': cell_rows, 'fields': 'userEnteredValue,note,userEnteredFormat'}}, {'autoResizeDimensions': {'dimensions': {'sheetId': sheet_id, 'dimension': 'COLUMNS', 'startIndex': 0, 'endIndex': max_cols}}}]
    update = _google_request_guarded('update_sheet', requests.post, f'https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}:batchUpdate', headers=headers, json={'requests': requests_payload}, timeout=90, attempts=1)
    if update.status_code >= 300:
        raise RuntimeError(f'Google Sheets update {update.status_code}: {update.text[:700]}')
    expected_notes = {(r, c): str(note).strip() for (r, c), note in annotations.items() if str(note or '').strip()}
    if expected_notes:
        verify = _google_request_guarded('verify_notes', requests.get, f'https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}', headers=headers, params={'includeGridData': 'true', 'ranges': f"'{tab_title.replace(chr(39), chr(39) * 2)}'!A1:{_xlsx_col_name(max_cols)}{max(1, len(rows))}", 'fields': 'sheets(data(rowData(values(note))))'}, timeout=60, attempts=2)
        if verify.status_code >= 300:
            raise RuntimeError(f'Google Sheets note verify {verify.status_code}: {verify.text[:700]}')
        actual_notes = {}
        try:
            row_data = ((verify.json().get('sheets') or [{}])[0].get('data') or [{}])[0].get('rowData') or []
            for r0, row_obj in enumerate(row_data, start=1):
                for c0, cell in enumerate(row_obj.get('values') or [], start=1):
                    note = str(cell.get('note') or '').strip()
                    if note:
                        actual_notes[r0, c0] = note
        except Exception as exc:
            raise RuntimeError(f'Google Sheets note verify parse: {exc}')
        missing = [f'{_xlsx_col_name(c)}{r}' for (r, c), note in expected_notes.items() if actual_notes.get((r, c)) != note]
        if missing:
            raise RuntimeError(f'Google Sheets: нативные примечания не подтвердились после записи; missing={missing[:12]} expected={len(expected_notes)} actual={len(actual_notes)}')
    return f'https://docs.google.com/spreadsheets/d/{spreadsheet_id}/edit#gid={sheet_id}'
try:
    _v177_legacy_0208_google_sheets_create_category_report.__name__ = '_google_sheets_create_category_report'
except Exception:
    pass

def _v177_legacy_0209_send_export_for_chat_to(recipient_chat_id: int, target_chat_id: int, mode: str, day_key: str, file_type: str='csv', excel_style_override: str | None=None, excel_options_override: dict | None=None, delivery: str='chat'):
    """Отправка CSV/XLSX или создание Google Sheets по выбранному периоду."""
    tmp_name = None
    try:
        _file_job_progress('собираю экспорт', force=True)
        file_type = str(file_type or 'csv').lower().lstrip('.')
        custom_options = normalize_excel_export_options(excel_options_override) if isinstance(excel_options_override, dict) else None
        excel_style_override = str(excel_style_override or (excel_export_options_style(custom_options) if custom_options else excel_table_style(target_chat_id)) or 'old').strip().lower()
        if excel_style_override not in {'old', 'new_plain', 'new_comments', 'new_notes', 'google_notes'}:
            excel_style_override = 'old'
        delivery = str(delivery or 'chat').strip().lower()
        force_google = delivery == 'google' or excel_style_override == 'google_notes'
        description_column = True if not custom_options else bool(custom_options.get('description_column'))
        annotations_enabled = bool(not custom_options or custom_options.get('comments') or custom_options.get('notes'))
        raw_mode = str(mode or 'all')
        if raw_mode.startswith('xlsxstat_'):
            raw_mode = raw_mode[len('xlsxstat_'):]
        mode = raw_mode.replace('csv_', '').replace('xlsx_', '')
        if mode == 'all_real':
            mode = 'all'
        if delivery == 'chat' and mode == 'all' and (file_type == 'xlsx') and (not financial_view_is_usd(get_chat_store(target_chat_id))) and (excel_style_override == 'old' and (not custom_options) and (not force_google)):
            save_chat_json(target_chat_id)
            path = chat_xlsx_file(target_chat_id) if file_type == 'xlsx' else chat_csv_file(target_chat_id)
            label = 'за всё время'
            if os.path.exists(path):
                fobj = file_bytesio_named(path, export_display_filename(target_chat_id, mode, day_key, 'xlsx' if file_type == 'xlsx' else 'csv'))
                if not fobj:
                    raise RuntimeError('Готовый экспорт не удалось открыть для отправки в Telegram')
                _tg_call_retry(bot.send_document, recipient_chat_id, fobj, caption=f"📂 {('Excel ' + _export_style_caption(excel_style_override) if file_type == 'xlsx' else 'CSV')} {label}: {get_chat_display_name(target_chat_id)}", timeout=120, purpose='export_send_document')
                return True
        rows, label = _period_export_rows(target_chat_id, mode, day_key)
        ext = 'xlsx' if file_type in {'xlsx', 'xlsxstat'} else 'csv'
        if not rows and ext != 'xlsx':
            send_info(recipient_chat_id, f'Нет данных {label}.')
            try:
                file_job_mark_external_delivery('info', 'no_data')
            except Exception:
                pass
            return True
        tmp_name = os.path.join(MEGA_LOCAL_TMP_DIR, f'export_{target_chat_id}_{mode}_{int(time.time() * 1000)}.{ext}')
        if file_type == 'xlsxstat':
            safe_chat = mega_safe_name(get_chat_display_name(target_chat_id), 'chat')
            display_name = f'{safe_chat}_{mode}_{day_key}_excel_статьи.xlsx'
        else:
            display_name = export_display_filename(target_chat_id, mode, day_key, ext)
        if file_type == 'xlsxstat':
            store = get_chat_store(target_chat_id)
            start_key, end_key = _period_export_bounds(store, mode, day_key)
            xlsx_rows = build_exact_category_stats_xlsx_rows(target_chat_id, start_key, 0, end_key, 0)
            annotations_override = None
            category_layout = True
            if custom_options and (not description_column):
                xlsx_rows, annotations_override = _category_rows_without_description(xlsx_rows)
                category_layout = 'category_compact'
            if force_google:
                _file_job_progress('создаю визуальную вкладку Google Таблицы', force=True)
                title = f'{get_chat_display_name(target_chat_id)} — статьи — {label}'
                sheet_url = _google_sheets_create_category_report(title, xlsx_rows, layout='category' if category_layout is True else 'category_compact', annotations_override=annotations_override if annotations_enabled else {}, include_annotations=annotations_enabled, target_chat_id=target_chat_id, recipient_chat_id=recipient_chat_id)
                if str(sheet_url).startswith('worker-job:'):
                    job_id = str(sheet_url).split(':', 1)[1]
                    bot.send_message(recipient_chat_id, f'⚡ Google Excel передан на Render #2.\nЗадание: {job_id[:12]}…\nГотовая ссылка придёт отдельным сообщением.')
                    try:
                        file_job_mark_external_delivery('Google Sheets worker', job_id)
                    except Exception:
                        pass
                    return True
                bot.send_message(recipient_chat_id, f'📊 Google Таблица — статьи {label}: {get_chat_display_name(target_chat_id)}\n\n{sheet_url}\n\nВизуализация: статьи по колонкам, цветные суммы и разделители дней.', disable_web_page_preview=True)
                try:
                    file_job_mark_external_delivery('Google Sheets', sheet_url)
                except Exception:
                    pass
                return True
            _write_excel_by_selected_style(tmp_name, xlsx_rows, target_chat_id, sheet_name='Статьи', category_layout=category_layout, mode_override=excel_style_override, compact_annotations=annotations_override if category_layout == 'category_compact' and annotations_enabled else {} if category_layout == 'category_compact' else None)
        elif ext == 'xlsx':
            store = get_chat_store(target_chat_id)
            start_key, end_key = _period_export_bounds(store, mode, day_key)
            opening = _opening_balance_before_exact(store, start_key, 0)
            if force_google:
                xlsx_rows = build_exact_category_stats_xlsx_rows(target_chat_id, start_key, 0, end_key, 0)
                annotations_override = None
                layout_name = 'category'
                if custom_options and (not description_column):
                    xlsx_rows, annotations_override = _category_rows_without_description(xlsx_rows)
                    layout_name = 'category_compact'
                _file_job_progress('создаю визуальную вкладку Google Таблицы', force=True)
                title = f'{get_chat_display_name(target_chat_id)} — статьи — {label}'
                sheet_url = _google_sheets_create_category_report(title, xlsx_rows, layout=layout_name, annotations_override=annotations_override if annotations_enabled else {}, include_annotations=annotations_enabled, target_chat_id=target_chat_id, recipient_chat_id=recipient_chat_id)
                if str(sheet_url).startswith('worker-job:'):
                    job_id = str(sheet_url).split(':', 1)[1]
                    bot.send_message(recipient_chat_id, f'⚡ Google Excel передан на Render #2.\nЗадание: {job_id[:12]}…\nГотовая ссылка придёт отдельным сообщением.')
                    try:
                        file_job_mark_external_delivery('Google Sheets worker', job_id)
                    except Exception:
                        pass
                    return True
                bot.send_message(recipient_chat_id, f'📊 Google Таблица {label}: {get_chat_display_name(target_chat_id)}\n\n{sheet_url}\n\nВизуализация: статьи по колонкам, цветные суммы и разделители дней.', disable_web_page_preview=True)
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
                    _write_excel_by_selected_style(tmp_name, xlsx_rows, target_chat_id, sheet_name='Экспорт', category_layout=False, mode_override=excel_style_override)
                else:
                    xlsx_rows, compact_annotations = _compact_simple_excel_rows_and_annotations(rows, opening, target_chat_id)
                    _write_excel_by_selected_style(tmp_name, xlsx_rows, target_chat_id, sheet_name='Экспорт', category_layout=False, mode_override=excel_style_override, compact_annotations=compact_annotations if annotations_enabled else {})
            else:
                xlsx_rows = [['Дата', 'Описание', 'Приход', 'Расход']]
                for date_v, amount_v, note_v in rows:
                    try:
                        parsed_amount = parse_csv_amount(amount_v)
                    except Exception as e_amount:
                        log_error(f'xlsx export amount parse skip: chat={get_chat_display_name(target_chat_id)} amount={amount_v!r} note={note_v!r}: {e_amount}')
                        parsed_amount = 0.0
                    xlsx_rows.append(_xlsx_record_row(date_v, parsed_amount, note_v))
                xlsx_rows = insert_blank_rows_between_days(xlsx_rows, header_rows=1)
                xlsx_rows = _xlsx_simple_rows_with_balances(xlsx_rows, opening, target_chat_id)
                _write_excel_by_selected_style(tmp_name, xlsx_rows, target_chat_id, sheet_name='Экспорт', category_layout=False, mode_override='old')
        else:
            with open(tmp_name, 'w', newline='', encoding='utf-8') as f:
                w = csv.writer(f)
                w.writerow(['date', 'amount', 'note'])
                write_csv_rows_with_day_gaps(w, rows, 3)
        if delivery == 'drive':
            _file_job_progress('загружаю файл в Google Drive', force=True)
            drive_url = tenant_google_upload_export(tmp_name, display_name, target_chat_id)
            bot.send_message(recipient_chat_id, f'☁️ Google Drive {label}: {get_chat_display_name(target_chat_id)}\n\n{drive_url}', disable_web_page_preview=True)
            try:
                file_job_mark_external_delivery('Google Drive', drive_url)
            except Exception:
                pass
            return True
        _file_job_progress('отправляю файл в Telegram', force=True)
        fobj = file_bytesio_named(tmp_name, display_name)
        if not fobj:
            raise RuntimeError('Экспорт создан, но файл не удалось открыть для отправки в Telegram')
        _tg_call_retry(bot.send_document, recipient_chat_id, fobj, caption=f"📂 {('Excel статьи ' + _export_style_caption(excel_style_override) if file_type == 'xlsxstat' else 'Excel ' + _export_style_caption(excel_style_override) if ext == 'xlsx' else 'CSV')} {label}: {get_chat_display_name(target_chat_id)}", timeout=120, purpose='export_send_document')
        return True
    except Exception as e:
        log_error(f'send_export_for_chat_to({get_chat_display_name(target_chat_id)}): {e}')
        return False
    finally:
        if tmp_name:
            try:
                os.remove(tmp_name)
            except Exception:
                pass
try:
    _v177_legacy_0209_send_export_for_chat_to.__name__ = 'send_export_for_chat_to'
except Exception:
    pass

def build_fin_categories_summary_keyboard(target_chat_id: int, mode: str, start: str, end: str, owner_day_key: str):
    store = get_chat_store(target_chat_id)
    kb = types.InlineKeyboardMarkup(row_width=3)
    buttons = []
    for cat in get_ordered_category_names(include_all=True, store=store):
        slug = get_expense_category_slug(cat, store)
        if slug:
            buttons.append(IB(cat, callback_data=fvcat_callback(f'fvcat_show:{target_chat_id}:{start}:{end}:{slug}:{owner_day_key}')))
    add_buttons_in_rows(kb, buttons, 3)
    if mode == 'wthu':
        prev_key = (datetime.strptime(start, '%Y-%m-%d') - timedelta(days=7)).strftime('%Y-%m-%d')
        next_key = (datetime.strptime(start, '%Y-%m-%d') + timedelta(days=7)).strftime('%Y-%m-%d')
        kb.row(IB('⬅️ Чт–Ср', callback_data=fvcat_callback(f'fvcat_wthu:{target_chat_id}:{prev_key}:{owner_day_key}')), IB('📅 Сегодня', callback_data=fvcat_callback(f'fvcat_today:{target_chat_id}:{owner_day_key}')), IB('Чт–Ср ➡️', callback_data=fvcat_callback(f'fvcat_wthu:{target_chat_id}:{next_key}:{owner_day_key}')))
    kb.row(IB('📚 Описание статей', callback_data=fvcat_callback(f'fvcat_desc:{target_chat_id}:{start}:{owner_day_key}')))
    kb.row(IB('➕ Добавить статью', callback_data=fvcat_callback(f'fvcat_add:{target_chat_id}:{start}:{owner_day_key}')), IB('✏️ Изменить статью', callback_data=fvcat_callback(f'fvcat_edit_menu:{target_chat_id}:{start}:{owner_day_key}')))
    kb.row(IB('🗑 Удалить статью', callback_data=fvcat_callback(f'fvcat_del_menu:{target_chat_id}:{start}:{owner_day_key}')))
    kb.row(IB('⏪ Назад осн. окно', callback_data=f'fv:{target_chat_id}:{start}:open:{owner_day_key}'), IB('❌ Закрыть статьи', callback_data=f'fv:{target_chat_id}:{start}:open:{owner_day_key}'))
    return kb

def build_fin_category_edit_keyboard(target_chat_id: int, ref: str, owner_day_key: str):
    kb = types.InlineKeyboardMarkup(row_width=2)
    items = category_edit_items_for_chat(target_chat_id)
    if not items:
        kb.row(IB('Нет статей', callback_data='none'))
    for item in items:
        mark = 'Б' if item.get('base') else 'С'
        kb.row(IB(f"✏️ {item.get('name')} ({mark})", callback_data=fvcat_callback(f"fvcat_edit_pick:{target_chat_id}:{item.get('slug')}:{owner_day_key}")))
    kb.row(IB('🔙 Назад к статьям', callback_data=fvcat_callback(f'fvcat_wthu:{target_chat_id}:{ref}:{owner_day_key}')))
    kb.row(IB('⬅️ Назад осн. окно', callback_data=f'fv:{target_chat_id}:{ref}:open:{owner_day_key}'))
    return kb

def build_fin_category_delete_keyboard(target_chat_id: int, ref: str, owner_day_key: str):
    store = get_chat_store(target_chat_id)
    selected = set(store.get('category_delete_selection') or [])
    kb = types.InlineKeyboardMarkup(row_width=2)
    items = category_custom_items_for_chat(target_chat_id)
    if not items:
        kb.row(IB('Нет пользовательских статей', callback_data='none'))
    for item in items:
        slug = item.get('slug')
        icon = '☑️' if slug in selected else '⬛'
        kb.row(IB(f"{icon} {item.get('name')}", callback_data=fvcat_callback(f'fvcat_del_toggle:{target_chat_id}:{slug}:{ref}:{owner_day_key}')))
    kb.row(IB('🗑 Удалить выбранное', callback_data=fvcat_callback(f'fvcat_del_selected:{target_chat_id}:{ref}:{owner_day_key}')))
    kb.row(IB('🔙 Назад к статьям', callback_data=fvcat_callback(f'fvcat_wthu:{target_chat_id}:{ref}:{owner_day_key}')))
    kb.row(IB('⬅️ Назад осн. окно', callback_data=f'fv:{target_chat_id}:{ref}:open:{owner_day_key}'))
    return kb

def handle_finwindow_categories_callback(call, data_str: str) -> bool:
    if not data_str.startswith('fvcat_'):
        return False
    owner_chat_id = call.message.chat.id
    if not is_owner_chat(owner_chat_id):
        return True
    try:
        parts = data_str.split(':')
        action = parts[0]
        target_chat_id = int(parts[1])
    except Exception:
        return True
    store = get_chat_store(target_chat_id)
    try:
        register_static_open_view(owner_chat_id, call.message.message_id, code=action, day_key=parts[2] if len(parts) > 2 else None, params={'target_chat_id': target_chat_id, 'view_action': action})
    except Exception:
        pass
    if action == 'fvcat_today':
        owner_day_key = parts[2] if len(parts) > 2 else today_key()
        return handle_finwindow_categories_callback(call, f'fvcat_wthu:{target_chat_id}:{today_key()}:{owner_day_key}')
    if action == 'fvcat_desc':
        ref = parts[2] if len(parts) > 2 else today_key()
        owner_day_key = parts[3] if len(parts) > 3 else today_key()
        kb = types.InlineKeyboardMarkup()
        kb.row(IB('🔙 Назад к статьям', callback_data=fvcat_callback(f'fvcat_wthu:{target_chat_id}:{ref}:{owner_day_key}')))
        kb.row(IB('🔙 К окну чата', callback_data=f'fv:{target_chat_id}:{ref}:open:{owner_day_key}'))
        safe_edit(bot, call, f'👁 {get_chat_display_name(target_chat_id)}\n' + build_articles_description_text(target_chat_id), reply_markup=kb, parse_mode=None)
        return True
    if action == 'fvcat_add':
        try:
            owner_day_key = parts[3] if len(parts) > 3 else today_key()
        except Exception:
            owner_day_key = today_key()
        start_category_add_wait(owner_chat_id, target_chat_id, owner_day_key=owner_day_key)
        try:
            bot.answer_callback_query(call.id, 'Напиши название и ключи статьи', show_alert=False)
        except Exception:
            pass
        return True
    if action == 'fvcat_edit_menu':
        ref = parts[2] if len(parts) > 2 else today_key()
        owner_day_key = parts[3] if len(parts) > 3 else today_key()
        safe_edit(bot, call, wm_owner(f'✏️ Изменить статью\n👁 {get_chat_display_name(target_chat_id)}\n\nВыберите статью. Б = базовая, С = своя.', 18), reply_markup=build_fin_category_edit_keyboard(target_chat_id, ref, owner_day_key))
        return True
    if action == 'fvcat_edit_pick':
        try:
            target_chat_id = int(parts[1])
            slug = parts[2]
            owner_day_key = parts[3] if len(parts) > 3 else today_key()
        except Exception:
            return True
        start_category_edit_wait(owner_chat_id, target_chat_id, slug)
        try:
            bot.answer_callback_query(call.id, 'Напиши новую статью и ключи', show_alert=False)
        except Exception:
            pass
        return True
    if action == 'fvcat_del_menu':
        clear_category_wait_state(owner_chat_id, 'category_add_wait', delete_prompt=False)
        clear_category_wait_state(owner_chat_id, 'category_edit_wait', delete_prompt=False)
        ref = parts[2] if len(parts) > 2 else today_key()
        owner_day_key = parts[3] if len(parts) > 3 else today_key()
        get_chat_store(target_chat_id)['category_delete_selection'] = []
        save_data(data)
        safe_edit(bot, call, wm_owner(f'🗑 Удалить статью\n👁 {get_chat_display_name(target_chat_id)}\n\nВыберите пользовательские статьи галочками.', 19), reply_markup=build_fin_category_delete_keyboard(target_chat_id, ref, owner_day_key))
        return True
    if action == 'fvcat_del_toggle':
        try:
            target_chat_id = int(parts[1])
            slug = parts[2]
            ref = parts[3] if len(parts) > 3 else today_key()
            owner_day_key = parts[4] if len(parts) > 4 else today_key()
        except Exception:
            return True
        tstore = get_chat_store(target_chat_id)
        selected = set(tstore.get('category_delete_selection') or [])
        if slug in selected:
            selected.remove(slug)
        else:
            selected.add(slug)
        tstore['category_delete_selection'] = sorted(selected)
        save_data(data)
        safe_edit(bot, call, wm_owner(f'🗑 Удалить статью\n👁 {get_chat_display_name(target_chat_id)}\n\nВыберите пользовательские статьи галочками.', 19), reply_markup=build_fin_category_delete_keyboard(target_chat_id, ref, owner_day_key))
        return True
    if action == 'fvcat_del_selected':
        try:
            target_chat_id = int(parts[1])
            ref = parts[2] if len(parts) > 2 else today_key()
            owner_day_key = parts[3] if len(parts) > 3 else today_key()
        except Exception:
            return True
        selected = set(get_chat_store(target_chat_id).get('category_delete_selection') or [])
        if not selected:
            try:
                bot.answer_callback_query(call.id, 'Ничего не выбрано', show_alert=False)
            except Exception:
                pass
            return True
        count = remove_custom_expense_categories(target_chat_id, selected)
        try:
            bot.answer_callback_query(call.id, f'Удалено статей: {count}', show_alert=False)
        except Exception:
            pass
        return handle_finwindow_categories_callback(call, f'fvcat_wthu:{target_chat_id}:{ref}:{owner_day_key}')
    if action == 'fvcat_wthu':
        ref = parts[2] if len(parts) > 2 else today_key()
        owner_day_key = parts[3] if len(parts) > 3 else today_key()
        start_key = week_start_thursday(ref)
        start, end = week_bounds_thu_wed(start_key)
        label = f'{fmt_date_ddmmyy(start)} — {fmt_date_ddmmyy(end)} (Чт–Ср)'
        text, _ = summarize_categories(store, start, end, label)
        text = f'👁 {get_chat_display_name(target_chat_id)}\n' + text
        safe_edit(bot, call, text, reply_markup=build_fin_categories_summary_keyboard(target_chat_id, 'wthu', start, end, owner_day_key), parse_mode=None)
        register_open_window(owner_chat_id, call.message.message_id, 'fin_categories_view', code='fvcat:wthu', day_key=ref, params={'target_chat_id': target_chat_id, 'owner_day_key': owner_day_key, 'view_action': 'wthu', 'ref': ref})
        return True
    if action == 'fvcat_show':
        try:
            _, target_s, start, end, slug, owner_day_key = data_str.split(':', 5)
            target_chat_id = int(target_s)
        except Exception:
            return True
        category = get_category_by_slug(slug, store)
        if not category:
            return True
        label = f'{fmt_date_ddmmyy(start)} — {fmt_date_ddmmyy(end)}'
        text = f'👁 {get_chat_display_name(target_chat_id)}\n' + build_category_detail_text(store, start, end, category, label)
        kb = build_fin_categories_summary_keyboard(target_chat_id, 'detail', start, end, owner_day_key)
        kb.row(IB('🔙 Назад', callback_data=fvcat_callback(f'fvcat_wthu:{target_chat_id}:{start}:{owner_day_key}')))
        kb.row(IB('🔙 К окну чата', callback_data=f'fv:{target_chat_id}:{start}:open:{owner_day_key}'))
        safe_edit(bot, call, text, reply_markup=kb, parse_mode=None)
        register_open_window(owner_chat_id, call.message.message_id, 'fin_categories_view', code='fvcat:show', day_key=start, params={'target_chat_id': target_chat_id, 'owner_day_key': owner_day_key, 'view_action': 'show', 'start': start, 'end': end, 'slug': slug})
        return True
    return True

def render_fin_window_text(target_chat_id: int, day_key: str):
    txt, _ = render_day_window(target_chat_id, day_key)
    return wm_owner(f'👁 {html.escape(get_chat_display_name(target_chat_id))}\n\n{txt}', 6, html_mode=True)

def build_fin_calendar_keyboard(target_chat_id: int, center_day: datetime, owner_day_key: str):
    kb = types.InlineKeyboardMarkup(row_width=7)
    store = get_chat_store(target_chat_id)
    if financial_view_is_usd(store):
        daily = {dk: recs for dk, recs in (store.get('daily_records', {}) or {}).items() if any((abs(float((r or {}).get('usd_amount', 0) or 0)) > 0 for r in recs or []))}
    else:
        daily = store.get('daily_records', {})
    kb.row(*[IB(x, callback_data='none') for x in ('Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс')])
    for week in calendar.Calendar(firstweekday=0).monthdayscalendar(center_day.year, center_day.month):
        row = []
        for day_num in week:
            if not day_num:
                row.append(IB(' ', callback_data='none'))
                continue
            key = f'{center_day.year:04d}-{center_day.month:02d}-{day_num:02d}'
            label = f'📝{day_num}' if daily.get(key) else str(day_num)
            row.append(IB(label, callback_data=f'fv:{target_chat_id}:{key}:open:{owner_day_key}'))
        kb.row(*row)
    prev_month = (center_day.replace(day=1) - timedelta(days=1)).replace(day=1)
    next_month = (center_day.replace(day=28) + timedelta(days=4)).replace(day=1)
    kb.row(IB('⬅️ Месяц', callback_data=f"fc:{target_chat_id}:{prev_month.strftime('%Y-%m-%d')}:{owner_day_key}"), IB(f'{russian_month_name(center_day.month)} {center_day.year}', callback_data='none'), IB('Месяц ➡️', callback_data=f"fc:{target_chat_id}:{next_month.strftime('%Y-%m-%d')}:{owner_day_key}"))
    prev_year = center_day.replace(year=center_day.year - 1, day=1)
    next_year = center_day.replace(year=center_day.year + 1, day=1)
    kb.row(IB('◀️ Год', callback_data=f"fc:{target_chat_id}:{prev_year.strftime('%Y-%m-%d')}:{owner_day_key}"), IB(str(center_day.year), callback_data='none'), IB('Год ▶️', callback_data=f"fc:{target_chat_id}:{next_year.strftime('%Y-%m-%d')}:{owner_day_key}"))
    row = []
    if center_day.strftime('%Y-%m') != now_local().strftime('%Y-%m'):
        row.append(IB('📅 Сегодня', callback_data=f'fc:{target_chat_id}:{today_key()}:{owner_day_key}'))
    row.append(IB('🔙 Назад', callback_data=f"fv:{target_chat_id}:{store.get('current_view_day', today_key())}:open:{owner_day_key}"))
    kb.row(*row)
    return kb

def build_forward_mode_menu(A: int, B: int):
    """
    Меню выбора режима пересылки между чатами A и B.
    """
    kb = types.InlineKeyboardMarkup()
    name_a = chat_button_title(A)
    name_b = chat_button_title(B)
    fr = data.get('forward_rules', {}) or {}
    ab_link = str(B) in fr.get(str(A), {})
    ba_link = str(A) in fr.get(str(B), {})
    two_on = ab_link and ba_link
    ab_state = '✅ ВКЛ' if ab_link else '⬜ ВЫКЛ'
    ba_state = '✅ ВКЛ' if ba_link else '⬜ ВЫКЛ'
    two_state = '✅ ВКЛ' if two_on else '⬜ ВЫКЛ'
    ab_fin = '✅ ВКЛ' if get_forward_finance(A, B) else '⬜ ВЫКЛ'
    ba_fin = '✅ ВКЛ' if get_forward_finance(B, A) else '⬜ ВЫКЛ'
    kb.row(IB(f'➡️ {ab_state} {name_a} → {name_b}', callback_data=f'fw_mode:{A}:{B}:to'))
    kb.row(IB(f'⬅️ {ba_state} {name_b} → {name_a}', callback_data=f'fw_mode:{A}:{B}:from'))
    kb.row(IB(f'↔️ {two_state} {name_a} ⇄ {name_b}', callback_data=f'fw_mode:{A}:{B}:two'))
    kb.row(IB(f'💰 {ab_fin} Учёт {name_a} → {name_b}', callback_data=f'fw_finpair:{A}:{B}:ab'))
    kb.row(IB(f'💰 {ba_fin} Учёт {name_b} → {name_a}', callback_data=f'fw_finpair:{A}:{B}:ba'))
    kb.row(IB('❌ Удалить все связи A-B', callback_data=f'fw_mode:{A}:{B}:del'))
    kb.row(IB('🔙 Назад', callback_data=f'fw_back_tgt:{A}'))
    return kb

def _one_button_keyboard(label: str, callback_data: str):
    kb = types.InlineKeyboardMarkup()
    kb.row(IB(label, callback_data=callback_data))
    return kb

# --- ИСТОЧНИК: 70_fast_ui.py ---
UI_EDIT_MIN_INTERVAL_SECONDS = float(os.getenv('UI_EDIT_MIN_INTERVAL_SECONDS', '0.03') or '0.03')
_ui_edit_lock = threading.RLock()
_ui_edit_last_ts = {}
_ui_edit_pending = {}
_ui_edit_timers = {}
_ui_edit_last_fingerprint = {}
_ui_edit_last_fingerprint_ts = {}

def _ui_edit_key(chat_id: int, message_id: int):
    return (int(chat_id), int(message_id))

def _perform_fast_ui_edit(payload: dict) -> str:
    chat_id = int(payload.get('chat_id'))
    message_id = int(payload.get('message_id'))
    text = payload.get('text') or ''
    reply_markup = payload.get('reply_markup')
    parse_mode = payload.get('parse_mode')
    purpose = payload.get('purpose') or 'fast_ui_edit'

    def _call_with_window_context(method, *args, **kwargs):
        diag_context = globals().get('window_diag_context')
        values = {'purpose': purpose, 'request_id': payload.get('_window_diag_request_id'), 'expected_seq': payload.get('_window_diag_expected_seq'), 'window_force': True}
        if callable(diag_context):
            with diag_context(**values):
                return _tg_call_retry(method, *args, **kwargs)
        return _tg_call_retry(method, *args, **kwargs)
    try:
        _call_with_window_context(bot.edit_message_text, text, chat_id=chat_id, message_id=message_id, reply_markup=reply_markup, parse_mode=parse_mode, attempts=1, purpose=purpose + '_text')
        return 'ok'
    except Exception as e1:
        low = str(e1).lower()
        if 'message is not modified' in low:
            return 'ok'
        if is_telegram_429(e1):
            try:
                bot_journal('ui_edit_rate_limited', chat_id, f'{purpose}: {str(e1)[:220]}', 'WARN')
            except Exception:
                pass
            return 'rate_limited'
        if 'message to edit not found' in low or "message can't be edited" in low:
            return 'not_found'
        try:
            _call_with_window_context(bot.edit_message_caption, chat_id=chat_id, message_id=message_id, caption=text, reply_markup=reply_markup, parse_mode=parse_mode, attempts=1, purpose=purpose + '_caption')
            return 'ok'
        except Exception as e2:
            low2 = str(e2).lower()
            if 'message is not modified' in low2:
                return 'ok'
            if is_telegram_429(e2):
                try:
                    bot_journal('ui_edit_rate_limited', chat_id, f'{purpose}: {str(e2)[:220]}', 'WARN')
                except Exception:
                    pass
                return 'rate_limited'
            if 'message to edit not found' in low2 or "message can't be edited" in low2:
                return 'not_found'
            try:
                bot_journal('ui_edit_failed', chat_id, f'{purpose}: {str(e1)[:180]} / {str(e2)[:180]}', 'WARN')
            except Exception:
                pass
            return 'failed'

def _v177_legacy_0210_run_pending_ui_edit(key):
    with _ui_edit_lock:
        payload = _ui_edit_pending.pop(key, None)
        _ui_edit_timers.pop(key, None)
        if not payload:
            return
        _ui_edit_last_ts[key] = time.time()
    try:
        diag_apply = globals().get('window_diag_fast_ui_apply')
        if callable(diag_apply):
            diag_apply(payload, delayed=True)
    except Exception:
        pass
    _perform_fast_ui_edit(payload)
try:
    _v177_legacy_0210_run_pending_ui_edit.__name__ = '_run_pending_ui_edit'
except Exception:
    pass

def _v177_legacy_0211_fast_ui_edit_message_text(chat_id: int, message_id: int, text: str, reply_markup=None, parse_mode=None, purpose: str='fast_ui') -> str:
    try:
        if 'secret' not in str(purpose or '').lower():
            reply_markup = ensure_previous_back_nav_keyboard(reply_markup, int(chat_id), int(message_id))
            reply_markup = ensure_main_back_nav_keyboard(reply_markup, int(chat_id))
    except Exception:
        pass
    try:
        text = _ensure_window_marker_for_render(text, reply_markup, int(chat_id), int(message_id), purpose)
    except Exception:
        pass
    key = _ui_edit_key(chat_id, message_id)
    payload = {'chat_id': int(chat_id), 'message_id': int(message_id), 'text': text, 'reply_markup': reply_markup, 'parse_mode': parse_mode, 'purpose': purpose}
    try:
        diag_prepare = globals().get('window_diag_prepare_fast_ui_payload')
        if callable(diag_prepare):
            payload = diag_prepare(payload) or payload
    except Exception:
        pass
    # R37: suppress identical renders of the same Telegram message. Multiple background
    # refreshers used to repaint the exact same window and consume bot-token quota.
    try:
        _fp = hashlib.sha1((str(text) + '\n' + repr(reply_markup) + '\n' + str(parse_mode or '')).encode('utf-8', 'replace')).hexdigest()
        _now_fp = time.time()
        with _ui_edit_lock:
            if _ui_edit_last_fingerprint.get(key) == _fp and (_now_fp - float(_ui_edit_last_fingerprint_ts.get(key, 0) or 0)) < 2.0:
                return 'deduped'
            _ui_edit_last_fingerprint[key] = _fp
            _ui_edit_last_fingerprint_ts[key] = _now_fp
    except Exception:
        pass
    force_immediate = str(purpose or '') == 'back_main_instant'
    if force_immediate:
        cancel_fast_ui_edit(chat_id, message_id)
    now_ts = time.time()
    with _ui_edit_lock:
        last_ts = float(_ui_edit_last_ts.get(key, 0) or 0)
        wait = 0.0 if force_immediate else max(0.0, effective_ui_edit_interval() - (now_ts - last_ts))
        if wait > 0:
            replaced_payload = _ui_edit_pending.get(key)
            _ui_edit_pending[key] = payload
            scheduler_key = f'ui-edit:{int(chat_id)}:{int(message_id)}'
            DELAYED_SCHEDULER.cancel(scheduler_key)
            deadline = DELAYED_SCHEDULER.schedule(scheduler_key, wait + 0.05, _run_pending_ui_edit, key)
            _ui_edit_timers[key] = deadline
            try:
                diag_scheduled = globals().get('window_diag_fast_ui_scheduled')
                if callable(diag_scheduled):
                    diag_scheduled(payload, wait + 0.05, replaced_payload=replaced_payload)
            except Exception:
                pass
            return 'scheduled'
        _ui_edit_last_ts[key] = now_ts
    try:
        diag_apply = globals().get('window_diag_fast_ui_apply')
        if callable(diag_apply):
            diag_apply(payload, delayed=False)
    except Exception:
        pass
    return _perform_fast_ui_edit(payload)
try:
    _v177_legacy_0211_fast_ui_edit_message_text.__name__ = 'fast_ui_edit_message_text'
except Exception:
    pass

def v178_edit_reply_markup_async(chat_id: int, message_id: int, reply_markup=None, purpose: str='ui_markup') -> bool:
    """Non-blocking keyboard-only update for callback handlers in every contour."""
    cid = int(chat_id)
    mid = int(message_id)

    def _job():
        started = time.monotonic()
        try:
            _tg_call_retry(bot.edit_message_reply_markup, cid, mid, reply_markup=reply_markup, attempts=1, purpose=str(purpose or 'ui_markup') + '_async')
        except Exception:
            pass
        finally:
            try:
                stage = globals().get('v177_perf_stage')
                if callable(stage):
                    stage('telegram_reply_markup_async', time.monotonic() - started)
            except Exception:
                pass
    try:
        return bool(UI_TASK_POOL.submit_unique(f'v178-markup:{cid}:{mid}', _job))
    except Exception:
        return False

def v177_delete_message_async(chat_id: int, message_id: int, purpose: str='ui_close') -> bool:
    """Delete an obsolete UI message without making the callback wait for Telegram."""
    cid = int(chat_id)
    mid = int(message_id)

    def _job():
        started = time.monotonic()
        try:
            _tg_call_retry(bot.delete_message, cid, mid, attempts=1, purpose=str(purpose or 'ui_close') + '_async')
        except Exception:
            pass
        finally:
            try:
                stage = globals().get('v177_perf_stage')
                if callable(stage):
                    stage('telegram_delete_async', time.monotonic() - started)
            except Exception:
                pass
    try:
        pool = globals().get('UI_DELETE_TASK_POOL')
        if pool is not None:
            return bool(pool.submit_unique(f'r26-ui-delete:{cid}:{mid}', _job))
    except Exception:
        pass
    # R26: never fall back to a shared GENERAL worker from a callback. If the
    # dedicated pool is unavailable, a tiny daemon owns this best-effort delete.
    try:
        threading.Thread(target=_job, name=f'r26-ui-delete-{cid}-{mid}', daemon=True).start()
        return True
    except Exception:
        return False

def cancel_fast_ui_edit(chat_id: int, message_id: int):
    key = _ui_edit_key(chat_id, message_id)
    with _ui_edit_lock:
        _ui_edit_pending.pop(key, None)
        _ui_edit_timers.pop(key, None)
    DELAYED_SCHEDULER.cancel(f'ui-edit:{int(chat_id)}:{int(message_id)}')
_WINDOW_NAV_HISTORY_LOCK = threading.RLock()
_WINDOW_NAV_HISTORY = defaultdict(list)
_WINDOW_NAV_HISTORY_LIMIT = 12
_WINDOW_MARKER_MISSING_THROTTLE = {}

def _serialize_inline_keyboard(reply_markup):
    if reply_markup is None:
        return None
    rows_out = []
    try:
        for row in list(getattr(reply_markup, 'keyboard', None) or []):
            row_out = []
            for btn in row or []:
                try:
                    if hasattr(btn, 'to_dict'):
                        row_out.append(btn.to_dict())
                    else:
                        row_out.append({'text': getattr(btn, 'text', ''), 'callback_data': getattr(btn, 'callback_data', None), 'url': getattr(btn, 'url', None), 'switch_inline_query': getattr(btn, 'switch_inline_query', None), 'switch_inline_query_current_chat': getattr(btn, 'switch_inline_query_current_chat', None)})
                except Exception:
                    continue
            if row_out:
                rows_out.append(row_out)
    except Exception:
        return None
    return rows_out

def _deserialize_inline_keyboard(rows_data):
    if not rows_data:
        return None
    kb = types.InlineKeyboardMarkup()
    for row in rows_data:
        buttons = []
        for raw in row or []:
            try:
                if hasattr(types.InlineKeyboardButton, 'de_json'):
                    btn = types.InlineKeyboardButton.de_json(raw)
                else:
                    allowed = {k: v for k, v in dict(raw or {}).items() if k in {'url', 'callback_data', 'switch_inline_query', 'switch_inline_query_current_chat', 'callback_game', 'pay', 'login_url', 'web_app', 'copy_text'} and v is not None}
                    btn = types.InlineKeyboardButton(str((raw or {}).get('text') or ''), **allowed)
                buttons.append(btn)
            except Exception:
                continue
        if buttons:
            kb.row(*buttons)
    return kb

_R22_NAV_REMOTE_HAS = {}
_R22_NAV_REMOTE_PREFETCH = set()

def _window_nav_key(chat_id: int, message_id: int):
    return (int(chat_id), int(message_id))

def _nav_history_push_v248(key, snap: dict) -> bool:
    """R22 hot path: RAM first, KV durability later.

    Navigation history is UI continuity, so Redis/Key Value RTT must never be in
    front of a button.  The in-memory stack is authoritative for the live process;
    the remote copy is mirrored on the cleanup lane.
    """
    with _WINDOW_NAV_HISTORY_LOCK:
        stack = _WINDOW_NAV_HISTORY[key]
        if stack and stack[-1].get('text') == snap.get('text') and stack[-1].get('markup') == snap.get('markup'):
            return True
        stack.append(snap)
        if len(stack) > _WINDOW_NAV_HISTORY_LIMIT:
            del stack[:-_WINDOW_NAV_HISTORY_LIMIT]
    try:
        _R22_NAV_REMOTE_HAS[key] = True
    except Exception:
        pass

    def _mirror():
        push = globals().get('kv_nav_push_v248')
        if callable(push):
            try:
                push(int(key[0]), int(key[1]), dict(snap), _WINDOW_NAV_HISTORY_LIMIT)
            except Exception:
                pass
    try:
        pool = globals().get('UI_CLEANUP_TASK_POOL') or globals().get('BACKGROUND_TASK_POOL')
        if pool is not None:
            pool.submit(f'r22-nav-mirror:{int(key[0])}:{int(key[1])}', _mirror)
    except Exception:
        pass
    return True

def _nav_history_peek_v248(key):
    with _WINDOW_NAV_HISTORY_LOCK:
        stack = _WINDOW_NAV_HISTORY.get(key) or []
        if stack:
            return dict(stack[-1])
    fn = globals().get('kv_nav_peek_v248')
    if callable(fn):
        try:
            value = fn(int(key[0]), int(key[1]))
            return dict(value) if isinstance(value, dict) else None
        except Exception:
            pass
    return None

def _nav_history_pop_v248(key) -> bool:
    with _WINDOW_NAV_HISTORY_LOCK:
        stack = _WINDOW_NAV_HISTORY.get(key) or []
        if stack:
            stack.pop()
            if not stack:
                _WINDOW_NAV_HISTORY.pop(key, None)
            return True
    fn = globals().get('kv_nav_pop_v248')
    if callable(fn):
        try:
            return bool(fn(int(key[0]), int(key[1])))
        except Exception:
            pass
    return False

def _nav_history_clear_v248(chat_id: int, message_id: int) -> None:
    key = _window_nav_key(chat_id, message_id)
    with _WINDOW_NAV_HISTORY_LOCK:
        _WINDOW_NAV_HISTORY.pop(key, None)
    _R22_NAV_REMOTE_HAS.pop(key, None)
    fn = globals().get('kv_nav_clear_v248')
    if callable(fn):
        try:
            fn(int(chat_id), int(message_id))
        except Exception:
            pass

def r27_callback_is_back_navigation(call, data_str: str) -> bool:
    """True for a user-visible Back button (not backup operations).

    We inspect both callback token and the text of the clicked button. This lets old
    windows keep their historical callback names while R27 gives all Back buttons the
    same navigation semantics: previous window first, legacy fallback second.
    """
    raw = str(data_str or '').strip()
    low = raw.casefold()
    if 'backup' in low:
        return False
    if low == 'nav_prev' or low.endswith(':back_main'):
        return True
    normalized = low.replace(':', '_').replace('-', '_')
    parts = [x for x in normalized.split('_') if x]
    if 'back' in parts or low.startswith('back_') or low.endswith('_back'):
        return True
    try:
        markup = getattr(getattr(call, 'message', None), 'reply_markup', None)
        for row in list(getattr(markup, 'keyboard', None) or []):
            for btn in row or []:
                if str(getattr(btn, 'callback_data', '') or '') != raw:
                    continue
                label = str(getattr(btn, 'text', '') or '').casefold()
                if 'назад' in label:
                    return True
    except Exception:
        pass
    return False

def r27_cleanup_after_history_back(call):
    try:
        cid = int(call.message.chat.id)
    except Exception:
        return False
    def _job():
        try:
            fn = globals().get('cancel_pending_window_commands')
            if callable(fn): fn(cid, delete_prompt=False)
        except Exception:
            pass
        try:
            fn = globals().get('_v214_cancel_pending_before_navigation')
            if callable(fn): fn(call, 'nav_prev')
        except Exception:
            pass
    try:
        pool = globals().get('UI_CLEANUP_TASK_POOL') or globals().get('BACKGROUND_TASK_POOL')
        if pool is not None and pool.submit_unique(f'r27-back-clean:{cid}', _job):
            return True
    except Exception:
        pass
    return False

def remember_previous_window(call):
    try:
        msg = call.message
        key = _window_nav_key(msg.chat.id, msg.message_id)
        text = getattr(msg, 'text', None) or getattr(msg, 'caption', None) or ''
        markup = _serialize_inline_keyboard(getattr(msg, 'reply_markup', None))
        if not text and (not markup):
            return False
        snap = {'text': str(text), 'markup': markup, 'parse_mode': None, 'saved_at': time.time()}
        return _nav_history_push_v248(key, snap)
    except Exception:
        return False

def window_has_previous(chat_id: int, message_id: int) -> bool:
    """Non-blocking R22 check. Never contacts Redis on the render hot path."""
    key = _window_nav_key(chat_id, message_id)
    with _WINDOW_NAV_HISTORY_LOCK:
        if bool(_WINDOW_NAV_HISTORY.get(key)):
            return True
    if bool(_R22_NAV_REMOTE_HAS.get(key, False)):
        return True
    # One background prefetch is allowed for post-restart continuity. Its result
    # can affect the next render, never the current button latency.
    if key not in _R22_NAV_REMOTE_PREFETCH:
        _R22_NAV_REMOTE_PREFETCH.add(key)
        def _prefetch():
            try:
                fn = globals().get('kv_nav_has_v248')
                if callable(fn):
                    _R22_NAV_REMOTE_HAS[key] = bool(fn(int(key[0]), int(key[1])))
            except Exception:
                pass
            finally:
                _R22_NAV_REMOTE_PREFETCH.discard(key)
        try:
            pool = globals().get('UI_CLEANUP_TASK_POOL') or globals().get('BACKGROUND_TASK_POOL')
            if pool is not None:
                pool.submit_unique(f'r22-nav-has:{int(key[0])}:{int(key[1])}', _prefetch)
        except Exception:
            _R22_NAV_REMOTE_PREFETCH.discard(key)
    return False

def ensure_previous_back_nav_keyboard(reply_markup, chat_id: int, message_id: int):
    if reply_markup is None:
        reply_markup = types.InlineKeyboardMarkup()
    try:
        callbacks, labels = ([], [])
        for row in list(getattr(reply_markup, 'keyboard', None) or []):
            for btn in row or []:
                callbacks.append(str(getattr(btn, 'callback_data', '') or ''))
                labels.append(str(getattr(btn, 'text', '') or ''))
        has_own_back = any(('back' in cb.casefold() and 'back_main' not in cb.casefold() or cb.startswith('nav_prev') for cb in callbacks)) or any(('назад' in t.casefold() and 'осн' not in t.casefold() for t in labels))
        if not has_own_back and window_has_previous(chat_id, message_id):
            reply_markup.row(IB('🔙 Назад', callback_data='nav_prev'))
    except Exception:
        pass
    return reply_markup

def _v177_legacy_0212_restore_previous_window(call) -> bool:
    chat_id = int(call.message.chat.id)
    message_id = int(call.message.message_id)
    key = _window_nav_key(chat_id, message_id)
    snap = _nav_history_peek_v248(key)
    if not snap:
        try:
            bot.answer_callback_query(call.id, 'История окна очищена после перезапуска. Используйте «Назад осн. окно».')
        except Exception:
            pass
        return False
    markup = _deserialize_inline_keyboard(snap.get('markup'))
    try:
        markup = ensure_previous_back_nav_keyboard(markup, chat_id, message_id)
        markup = ensure_main_back_nav_keyboard(markup, chat_id)
    except Exception:
        pass
    result = fast_ui_edit_message_text(chat_id, message_id, str(snap.get('text') or ''), reply_markup=markup, parse_mode=snap.get('parse_mode'), purpose='nav_prev_restore')
    if result in {'ok', 'scheduled', 'rate_limited'}:
        _nav_history_pop_v248(key)
        return True
    return False
try:
    _v177_legacy_0212_restore_previous_window.__name__ = 'restore_previous_window'
except Exception:
    pass

def _suggest_window_marker(group: str) -> str:
    try:
        nums = []
        for value in WINDOW_MARKER_CONSTANTS.values():
            value = str(value or '')
            if value.startswith(group) and value[len(group):].isdigit():
                nums.append(int(value[len(group):]))
        return f'{group}{(max(nums) + 1 if nums else 1)}'
    except Exception:
        return f'{group}?'

def journal_missing_window_marker(raw_action: str, chat_id=None, message_id=None, text: str='', reply_markup=None, purpose: str=''):
    raw = str(raw_action or '')
    normalized = _normalize_window_action(raw)
    group = _window_group_for_action(normalized)
    first_line_rows = strip_window_mark(str(text or '')).strip().splitlines()[:1]
    first_line = (first_line_rows[0] if first_line_rows else '')[:140]
    try:
        marker_key = _window_key_from_markup(reply_markup) if reply_markup is not None else ''
    except Exception:
        marker_key = ''
    throttle_key = (normalized, int(chat_id or 0), int(message_id or 0), str(purpose or ''))
    now_ts = time.time()
    if now_ts - float(_WINDOW_MARKER_MISSING_THROTTLE.get(throttle_key, 0) or 0) < 30:
        return
    _WINDOW_MARKER_MISSING_THROTTLE[throttle_key] = now_ts
    detail = f'raw={raw[:220]}; normalized={normalized}; chat={chat_id}; msg={message_id}; purpose={purpose}; first_line={first_line!r}; markup_key={marker_key}; suggested={_suggest_window_marker(group)}'
    try:
        bot_journal('window_marker_missing', chat_id, detail, 'ERROR')
    except Exception:
        log_error('WINDOW_MARKER_MISSING_DETAIL: ' + detail)

def _ensure_window_marker_for_render(text: str, reply_markup, chat_id: int, message_id: int, purpose: str='') -> str:
    body = str(text or '')
    if has_window_mark(body) or reply_markup is None:
        return body
    key = _window_key_from_markup(reply_markup)
    code = _window_marker_code(key)
    if not window_marker_is_declared(key):
        journal_missing_window_marker(key, chat_id, message_id, body, reply_markup, purpose)
    return window_mark(body, code)

def _v177_legacy_0214_safe_edit(bot, call, text, reply_markup=None, parse_mode=None):
    """Быстрое обновление окна с маркером, историей и безопасным fallback."""
    chat_id = call.message.chat.id
    msg_id = call.message.message_id
    raw_action = str(getattr(call, 'data', '') or '')
    if raw_action != 'nav_prev':
        remember_previous_window(call)
    try:
        code = window_code_for_callback(raw_action, owner_chat=is_owner_chat(chat_id))
        if not window_marker_is_declared(raw_action):
            journal_missing_window_marker(raw_action, chat_id, msg_id, text, reply_markup, 'safe_edit')
        text = window_mark(text, code, html_mode=str(parse_mode or '').upper() == 'HTML')
    except Exception:
        pass
    if reply_markup is None:
        try:
            reply_markup = default_window_nav_keyboard(chat_id)
        except Exception:
            pass
    try:
        reply_markup = ensure_previous_back_nav_keyboard(reply_markup, chat_id, msg_id)
        reply_markup = ensure_main_back_nav_keyboard(reply_markup, chat_id)
    except Exception:
        pass
    result = fast_ui_edit_message_text(chat_id, msg_id, text, reply_markup=reply_markup, parse_mode=parse_mode, purpose='safe_edit_fast')
    if result in {'ok', 'scheduled', 'rate_limited'}:
        if result == 'rate_limited':
            try:
                bot.answer_callback_query(call.id, 'Обновление отложено: Telegram ограничил частые клики.', show_alert=False)
            except Exception:
                pass
        try:
            _touch_v98_auto_close_for_callback(chat_id, msg_id, raw_action)
        except Exception:
            pass
        return
    try:
        if chat_buttons_current_window_enabled(chat_id):
            try:
                bot.answer_callback_query(call.id, 'Текущее окно недоступно, новое не создаю.', show_alert=False)
            except Exception:
                pass
            return
    except Exception:
        pass
    try:
        try:
            diag_note = globals().get('window_diag_note_recreate')
            if callable(diag_note):
                diag_note(chat_id, msg_id, result, 'safe_edit_send_fallback')
        except Exception:
            pass
        diag_context = globals().get('window_diag_context')
        if callable(diag_context):
            with diag_context(purpose='safe_edit_send_fallback', recreate_from=msg_id, recreate_reason=result, window_force=True):
                sent = _tg_call_retry(bot.send_message, chat_id, text, reply_markup=reply_markup, parse_mode=parse_mode, attempts=1, purpose='safe_edit_send_fallback')
        else:
            sent = _tg_call_retry(bot.send_message, chat_id, text, reply_markup=reply_markup, parse_mode=parse_mode, attempts=1, purpose='safe_edit_send_fallback')
        try:
            _touch_v98_auto_close_for_callback(chat_id, sent.message_id, raw_action)
        except Exception:
            pass
    except Exception as e:
        if not is_telegram_429(e):
            log_error(f'safe_edit fallback send {chat_id}: {e}')
try:
    _v177_legacy_0214_safe_edit.__name__ = 'safe_edit'
except Exception:
    pass

def _v177_legacy_0215_safe_edit_current_only(bot, call, text, reply_markup=None, parse_mode=None):
    """Редактирует только текущее окно, без создания нового."""
    chat_id = call.message.chat.id
    msg_id = call.message.message_id
    raw_action = str(getattr(call, 'data', '') or '')
    if raw_action != 'nav_prev':
        remember_previous_window(call)
    try:
        code = window_code_for_callback(raw_action, owner_chat=is_owner_chat(chat_id))
        if not window_marker_is_declared(raw_action):
            journal_missing_window_marker(raw_action, chat_id, msg_id, text, reply_markup, 'safe_edit_current_only')
        text = window_mark(text, code, html_mode=str(parse_mode or '').upper() == 'HTML')
    except Exception:
        pass
    if reply_markup is None:
        try:
            reply_markup = default_window_nav_keyboard(chat_id)
        except Exception:
            pass
    try:
        reply_markup = ensure_previous_back_nav_keyboard(reply_markup, chat_id, msg_id)
        reply_markup = ensure_main_back_nav_keyboard(reply_markup, chat_id)
    except Exception:
        pass
    result = fast_ui_edit_message_text(chat_id, msg_id, text, reply_markup=reply_markup, parse_mode=parse_mode, purpose='safe_edit_current_only_fast')
    if result == 'rate_limited':
        try:
            bot.answer_callback_query(call.id, 'Обновление отложено: слишком много кликов.', show_alert=False)
        except Exception:
            pass
    try:
        _touch_v98_auto_close_for_callback(chat_id, msg_id, raw_action)
    except Exception:
        pass
    return result in {'ok', 'scheduled', 'rate_limited'}
try:
    _v177_legacy_0215_safe_edit_current_only.__name__ = 'safe_edit_current_only'
except Exception:
    pass
CATEGORY_PAGE_SAFE_CHARS = 3300

def _split_category_pages(text: str, limit: int=CATEGORY_PAGE_SAFE_CHARS) -> list[str]:
    text = str(text or '').strip()
    if not text:
        return ['']
    pages = []
    current = ''
    for raw_line in text.splitlines():
        line = raw_line
        chunks = []
        while len(line) > limit:
            cut = line.rfind(' ', 0, limit)
            if cut < max(200, limit // 3):
                cut = limit
            chunks.append(line[:cut].rstrip())
            line = line[cut:].lstrip()
        chunks.append(line)
        for chunk in chunks:
            candidate = chunk if not current else current + '\n' + chunk
            if len(candidate) > limit and current:
                pages.append(current.rstrip())
                current = chunk
            else:
                current = candidate
    if current or not pages:
        pages.append(current.rstrip())
    return pages

def _serialize_category_markup(markup) -> list[list[dict]]:
    rows = []
    for row in getattr(markup, 'keyboard', []) or []:
        out = []
        for btn in row or []:
            item = {'text': str(getattr(btn, 'text', '') or '')}
            cb = getattr(btn, 'callback_data', None)
            if cb is not None:
                full = None
                try:
                    full = resolve_short_callback(str(cb))
                except Exception:
                    full = None
                item['callback_data'] = str(full or cb)
            url = getattr(btn, 'url', None)
            if url:
                item['url'] = str(url)
            out.append(item)
        if out:
            rows.append(out)
    return rows

def _deserialize_category_markup(rows) -> object:
    kb = types.InlineKeyboardMarkup()
    for row in rows or []:
        buttons = []
        for item in row or []:
            text = str((item or {}).get('text') or '')
            cb = (item or {}).get('callback_data')
            url = (item or {}).get('url')
            if cb is not None:
                cb = str(cb)
                if cb.startswith('fvcat_'):
                    cb = fvcat_callback(cb)
                elif cb.startswith('cat_'):
                    cb = cat_callback(cb)
                else:
                    cb = make_short_callback(cb)
                buttons.append(IB(text, callback_data=cb))
            elif url:
                buttons.append(types.InlineKeyboardButton(text=text, url=str(url)))
            else:
                buttons.append(IB(text, callback_data='none'))
        if buttons:
            kb.row(*buttons)
    return kb

def _category_paged_keyboard(state: dict, page_index: int):
    kb = _deserialize_category_markup((state or {}).get('base_markup') or [])
    total = max(1, len((state or {}).get('pages') or []))
    page_index = max(0, min(int(page_index), total - 1))
    row = []
    if page_index > 0:
        row.append(IB('⬅️ Предыдущая', callback_data='cat_page:prev'))
    row.append(IB(f'{page_index + 1}/{total}', callback_data='none'))
    if page_index < total - 1:
        row.append(IB('Следующая ➡️', callback_data='cat_page:next'))
    kb.row(*row)
    return kb

def _category_page_text(state: dict, page_index: int) -> str:
    pages = (state or {}).get('pages') or ['']
    total = len(pages)
    page_index = max(0, min(int(page_index), total - 1))
    body = str(pages[page_index] or '').rstrip() + f'\n\n{page_index + 1}/{total}'
    return window_mark(body, str((state or {}).get('marker_code') or ''), html_mode=str((state or {}).get('parse_mode') or '').upper() == 'HTML')

def _show_category_page(chat_id: int, message_id: int, requested) -> bool:
    store = get_chat_store(int(chat_id))
    state = store.get('categories_pagination') or {}
    pages = state.get('pages') or []
    if not pages:
        return False
    current = int(state.get('page', 0) or 0)
    if requested == 'next':
        idx = current + 1
    elif requested == 'prev':
        idx = current - 1
    else:
        try:
            idx = int(requested)
        except Exception:
            idx = current
    idx = max(0, min(idx, len(pages) - 1))
    state['page'] = idx
    store['categories_pagination'] = state
    text = _category_page_text(state, idx)
    kb = _category_paged_keyboard(state, idx)
    try:
        result = fast_ui_edit_message_text(int(chat_id), int(message_id), text, reply_markup=kb, parse_mode=state.get('parse_mode') or None, purpose='category_page_v178')
        if str(result or '') not in {'ok', 'scheduled'}:
            return False
    except Exception as exc:
        log_error(f'category page edit failed {chat_id}:{message_id}: {exc}')
        return False
    store['categories_msg_id'] = int(message_id)
    save_data(data, chat_ids=[int(chat_id)])
    return True

def send_or_edit_categories_window(chat_id, text, reply_markup=None, parse_mode=None, preferred_message_id=None, marker_action: str | None=None):
    """One categories window. Long article text is split into Telegram-safe pages instead of truncation."""
    store = get_chat_store(chat_id)
    base_reply_markup = reply_markup
    try:
        marker_key = marker_action or _window_key_from_markup(base_reply_markup)
        marker_code = _window_marker_code(marker_key, 'Ф')
        body = strip_window_mark(str(text or ''))
        pages = _split_category_pages(body)
        if len(pages) > 1:
            state = {'pages': pages, 'page': 0, 'marker_code': marker_code, 'parse_mode': str(parse_mode or ''), 'base_markup': _serialize_category_markup(base_reply_markup), 'marker_action': str(marker_action or '')}
            store['categories_pagination'] = state
            text = _category_page_text(state, 0)
            reply_markup = _category_paged_keyboard(state, 0)
            try:
                bot_journal('categories_window_paginated', chat_id, f'pages={len(pages)} chars={len(body)} marker={marker_code}')
            except Exception:
                pass
        else:
            store.pop('categories_pagination', None)
            text = window_mark(body, marker_code, html_mode=str(parse_mode or '').upper() == 'HTML')
    except Exception:
        pass
    store['categories_refresh_state'] = {'marker_action': marker_action or '', 'callbacks': _markup_callback_values(base_reply_markup)}
    mid = store.get('categories_msg_id')
    candidates = []
    if preferred_message_id is not None:
        try:
            candidates.append(int(preferred_message_id))
        except Exception:
            pass
    if mid:
        try:
            mid_int = int(mid)
            if mid_int not in candidates:
                candidates.append(mid_int)
        except Exception:
            pass
    for target_id in candidates:
        try:
            result = fast_ui_edit_message_text(chat_id, target_id, text, reply_markup=reply_markup, parse_mode=parse_mode, purpose='categories_window_v178')
            if str(result or '') in {'ok', 'scheduled'}:
                store['categories_msg_id'] = target_id
                register_open_window(chat_id, target_id, 'categories', code=marker_action or '')
                save_data(data, chat_ids=[int(chat_id)])
                return target_id
            if str(result or '') != 'not_found':
                continue
            if store.get('categories_msg_id') == target_id:
                unregister_open_window(chat_id, target_id)
                store['categories_msg_id'] = None
                save_data(data, chat_ids=[int(chat_id)])
        except Exception as e:
            log_error(f'send_or_edit_categories_window edit failed {chat_id}:{target_id}: {e}')
    sent = bot.send_message(chat_id, text, reply_markup=reply_markup, parse_mode=parse_mode)
    store['categories_msg_id'] = sent.message_id
    register_open_window(chat_id, sent.message_id, 'categories', code=marker_action or '')
    save_data(data, chat_ids=[int(chat_id)])
    return sent.message_id

def open_report_window(chat_id: int, month_key: str=None, message_id: int=None):
    """
    Открывает или обновляет отдельное окно отчёта без размножения сообщений.
    """
    text, month_key = build_month_report_text(chat_id, month_key)
    kb = build_report_keyboard(month_key)
    store = get_chat_store(chat_id)
    if message_id and (not store.get('report_window_id')):
        store['report_window_id'] = message_id
    final_id = send_or_edit_stored_window(chat_id, 'report_window_id', text, reply_markup=kb, parse_mode='HTML', delay=None)
    store['report_window_id'] = final_id
    store['report_month'] = month_key
    save_data(data)

def build_owner_instruction_text() -> str:
    return '📘 Инструкция по кнопкам\n\n🏠 Основное финансовое окно\n⬅️ День / День ➡️ — перейти на соседний день. 📅 Сегодня — вернуться к текущей дате.\n📅 Дата — открыть календарь; в календаре можно менять месяц и год.\n📊 Отчёт — месячный отчёт. 🧮 Итог — общий итог. 🏦 с ост — остаток после каждого расхода.\n✏️ Изменить / 🗑 Удалить — работа с финансовыми записями. 📦 Статьи — расходы по категориям.\n📄 CSV — окно Ф47: пять периодов; в каждой строке Период / CSV / Excel / Excel статьи. Точный период открывается отдельной кнопкой ниже.\n\n💱 Валюта\nARS — отдельный учёт в песо. ARS-USD — тот же ARS с эквивалентом по курсу. USD — отдельный долларовый учёт со всеми финансовыми функциями.\n/ost — включает или выключает подпись «ост:» в окне остатка.\n\n💰Перес\nОбычно — бот-копия без кнопки и без /izm_R. Кнопка — под копией появляется ✏️ Изменить. Слеш — в текст копии добавляется /izm_R. При переключении обновляются существующие копии от открытой даты до сегодня.\n\n🔐 Секрет\nСекрет у выбранного чата — включает тотальный секрет именно для этого чата. В секрет участвуют и созданные ботом копии. 🪷 Маска — показывает нейтральное сообщение вместо удалённого секретного сообщения.\n\n📦 Статьи\nФ110 — точный диапазон операций; 💵 USD включает долларовое отображение статей. ↕️ Расположение открывает Ф152: сначала выберите статью, затем номер новой позиции.\n📚 Описание статей — ключевые слова категорий. ➕/✏️/🗑 — добавить, изменить или удалить пользовательскую статью.\n\nℹ️ INFO\n📓 Журнал / 🗂 Журналы чатов — журналы действий. Кнопки в текущем окне — режим обновления интерфейса. Финансы — настройка финансового режима.\n💵 Доллар — выбор ARS / ARS-USD / USD. 💰Перес — оформление бот-копий. Финансы-кнопки — записи как inline-кнопки.\n☁️ MEGA — приоритет резервного копирования. ⏱ Внутренние таймеры — единые таймеры обычных режимов. 🚦 Очереди — очереди и диспетчер-свидетель.\n\n📤 Пересылка\nМеню пересылки задаёт связанные чаты и финансовую обработку копий. Режим «как у владельца» создаёт отдельный owner scope: настройки такого владельца сохраняются независимо.\n\n💾 Сохранение\nПосле финансового изменения данные сначала сохраняются, затем ставится быстрый backup, после чего обновляются связанные открытые окна и планируется полный backup. В v106 содержательные message/edited_message, включая части Telegram-альбомов, сначала фиксируются маленьким task-файлом в MEGA. Задача пересылки не получает done, пока для исходного сообщения не подтверждены все требуемые направления и, при включённом финучёте, финансовая запись назначения. При deploy pending/running поднимаются из MEGA; потерянный RAM-коллектор альбома ремонтируется по сохранённому update. Callback-кнопки навигации остаются быстрыми.'

def build_owner_instruction_keyboard(chat_id: int):
    kb = types.InlineKeyboardMarkup()
    kb.row(IB('🚦 Очереди', callback_data='info_queues'))
    kb.row(IB('🔙 Назад в Инфо', callback_data=f"d:{get_chat_store(chat_id).get('current_view_day', today_key())}:info"))
    kb.row(IB('❌ Закрыть', callback_data='info_close'))
    return kb

def all_task_pool_stats() -> list[dict]:
    return [WEBHOOK_TASK_POOL.stats(), FAST_UI_TASK_POOL.stats(), UI_TASK_POOL.stats(), CALLBACK_ACK_TASK_POOL.stats(), RECOVERY_TASK_POOL.stats(), REMINDER_TASK_POOL.stats(), FINANCE_TASK_POOL.stats(), FIN_FORWARD_TASK_POOL.stats(), FORWARD_TASK_POOL.stats(), DELTA_TASK_POOL.stats(), BACKUP_TASK_POOL.stats(), EXPORT_TASK_POOL.stats(), GENERAL_TASK_POOL.stats(), MAINTENANCE_TASK_POOL.stats(), JOURNAL_TASK_POOL.stats(), DELAYED_TASK_POOL.stats(), DOZVON_TASK_POOL.stats()]

def build_queue_status_text() -> str:
    lines = ['🚦 Очереди и нагрузка', '']
    for st in all_task_pool_stats():
        lines.append(f"{st['name']}: {st['active']}/{st['workers']} работают, ожидают {st['pending']}, ключей {st['keys']}, отказов {st['rejected']}, ошибок {st['failed']}, max ожидание {st['max_wait']}с")
    with timer_lock:
        lines.append('')
        lines.append(f'Таймеров полного бэкапа: {len(_backup_timers)}')
        lines.append(f'Таймеров delta: {len(_quick_backup_timers)}')
        lines.append(f'Dirty чатов: {len(_backup_dirty_chats)}')
    with _delta_state_lock:
        lines.append(f'Delta pending chats: {len(_delta_pending_chats)}')
        lines.append(f"Global full pending: {('да' if _global_snapshot_pending else 'нет')}")
    ds = DELAYED_SCHEDULER.stats()
    lines.append(f"Планировщик: задач {ds['scheduled']}, отменено {ds['cancelled']}, выполнено {ds['executed']}")
    uds = UPDATE_DISPATCHER.stats()
    lines.append(f"Диспетчер-свидетель: pending {uds['pending']}, oldest {uds['oldest']}с, готово {uds['completed']}, повторы {uds['duplicates']}, timeout {uds['timeouts']}, retry {uds['retries']}, ACK ждёт до {uds['ack_wait']}с")
    mts = mega_task_registry_stats() if 'mega_task_registry_stats' in globals() else {}
    lines.append(f"☁️ MEGA-задачи: pending {mts.get('pending', 0)}, running {mts.get('running', 0)}, failed {mts.get('failed', 0)}, done {mts.get('done', 0)}, сейчас {mts.get('processing', 0)}")
    lines.append(f"MEGA task: сохранено {mts.get('persisted', 0)}, восстановлено {mts.get('recovered', 0)}, уже выполнено {mts.get('skipped_done', 0)}, ошибки записи {mts.get('persist_errors', 0)}, ошибки финализации {mts.get('finalize_errors', 0)}")
    if mts.get('last_error'):
        lines.append(f"Последняя ошибка MEGA task: {str(mts.get('last_error'))[:180]}")
    lines.append(f'Excel-бэкап всех чатов: {backup_excel_all_label()}')
    lines.append(f'Telegram общий интервал: {TELEGRAM_GLOBAL_MIN_GAP:.3f}с')
    return '\n'.join(lines)
CHAT_JOURNAL_PAGE_SIZE = 20

def _journal_chat_items():
    try:
        return _collect_known_chat_items()
    except Exception:
        items = []
        for cid in (data.get('chats', {}) or {}).keys():
            try:
                items.append((int(cid), get_chat_display_name(int(cid))))
            except Exception:
                pass
        return sorted(items, key=lambda x: str(x[1]).lower())

def build_chat_journal_menu_text(page: int=0) -> str:
    items = _journal_chat_items()
    pages = max(1, (len(items) + CHAT_JOURNAL_PAGE_SIZE - 1) // CHAT_JOURNAL_PAGE_SIZE)
    page = max(0, min(int(page), pages - 1))
    enabled = sum((1 for cid, _ in items if is_chat_journal_enabled(cid)))
    return wm_owner(f'📓 Журналы по чатам\n\nОбщий журнал по умолчанию выключен. Здесь можно включать запись только для нужных чатов.\n\nВключено: {enabled} из {len(items)}\nСтраница: {page + 1}/{pages}', 9)

def build_chat_journal_menu_keyboard(page: int=0):
    items = _journal_chat_items()
    pages = max(1, (len(items) + CHAT_JOURNAL_PAGE_SIZE - 1) // CHAT_JOURNAL_PAGE_SIZE)
    page = max(0, min(int(page), pages - 1))
    start = page * CHAT_JOURNAL_PAGE_SIZE
    chunk = items[start:start + CHAT_JOURNAL_PAGE_SIZE]
    kb = types.InlineKeyboardMarkup(row_width=1)
    for cid, title in chunk:
        icon = '✅' if is_chat_journal_enabled(cid) else '⬜'
        kb.row(IB(f'{icon} 📓 {chat_button_title(cid, title)}', callback_data=f'journal_chat_toggle:{cid}:{page}'))
    if pages > 1:
        row = []
        if page > 0:
            row.append(IB('⬅️', callback_data=f'journal_chats_open:{page - 1}'))
        row.append(IB(f'{page + 1}/{pages}', callback_data='none'))
        if page + 1 < pages:
            row.append(IB('➡️', callback_data=f'journal_chats_open:{page + 1}'))
        kb.row(*row)
    kb.row(IB('🔙 Назад в Инфо', callback_data='journal_chats_back'))
    return kb

def current_bot_sender_name() -> str:
    """Имя Telegram-бота, который прислал меню. Кэшируем, чтобы не дергать API на каждую кнопку."""
    try:
        global _BOT_DISPLAY_NAME_CACHE
    except Exception:
        pass
    try:
        cached = globals().get('_BOT_DISPLAY_NAME_CACHE')
        if cached:
            return str(cached)
        me = bot.get_me()
        first = str(getattr(me, 'first_name', '') or '').strip()
        username = str(getattr(me, 'username', '') or '').strip().lstrip('@')
        value = first or (f'@{username}' if username else 'Telegram bot')
        if username and first:
            value = f'{first} (@{username})'
        globals()['_BOT_DISPLAY_NAME_CACHE'] = value
        return value
    except Exception:
        username = get_bot_username_cached() if 'get_bot_username_cached' in globals() else ''
        return f'@{username}' if username else 'Telegram bot'

def bot_file_identity_lines() -> list[str]:
    return [f'🤖 Бот: {current_bot_sender_name()}', f'📄 Файл: {BOT_FILE_NAME}', f'🏷 Версия: {VERSION}']

def _keepalive_fmt(seconds: int) -> str:
    try:
        sec = max(0, int(seconds or 0))
    except Exception:
        sec = 0
    if sec and sec % 60 == 0:
        return f'{sec // 60} мин'
    return f'{sec} сек'

def _keepalive_countdown(seconds: float) -> str:
    try:
        sec = max(0, int(round(float(seconds or 0))))
    except Exception:
        sec = 0
    m, s = divmod(sec, 60)
    return f'{m} мин {s:02d} сек' if m else f'{s} сек'

def _toggle_state(enabled: bool) -> str:
    return '✅ ВКЛ' if bool(enabled) else '⬜ ВЫКЛ'

def keep_alive_status_text() -> str:
    """Combined owner diagnostic retained for compatibility and journal links."""
    state = globals().get('KEEP_ALIVE_STATE') or {}
    self_on = bool(globals().get('keepalive_self_enabled', lambda: KEEP_ALIVE_ENABLED)())
    self_sec = int(globals().get('keepalive_self_interval_seconds', lambda: KEEP_ALIVE_INTERVAL_SECONDS)())
    auto_on = bool(globals().get('keepalive_auto_enabled', lambda: True)())
    auto_idle = int(globals().get('keepalive_auto_idle_seconds', lambda: 720)())
    auto_state = globals().get('keepalive_auto_runtime_state', lambda: {})() or {}
    peer_on = bool(globals().get('keepalive_peer_enabled', lambda: False)())
    peer_sec = int(globals().get('keepalive_peer_interval_seconds', lambda: 600)())
    peer_url = str(globals().get('keepalive_peer_target_url', lambda: '')() or '')
    mode = str(auto_state.get('mode') or '')
    if mode == 'standby_manual':
        auto_now = '⬜ резерв не нужен — ручной self-ping активен'
    elif mode == 'standby_peer':
        auto_now = '⬜ ожидание — второй Render присылает ping'
    elif mode == 'standby_external':
        auto_now = '⬜ ожидание — есть внешний входящий трафик'
    elif mode == 'due':
        auto_now = '✅ порог достигнут — резервный self-ping сейчас сработает'
    else:
        auto_now = '⬜ авторежим выключен'
    lines = ['💓 ЗАЩИТА ОТ СНА / ПЕЛЕНГ', '', f'Ручной самопеленг: {_toggle_state(self_on)} · {_keepalive_fmt(self_sec)}', f'Авторежим-резерв: {_toggle_state(auto_on)} · порог {_keepalive_fmt(auto_idle)}', f'Авторежим сейчас: {auto_now}', f'Основной → второй Render: {_toggle_state(peer_on)} · {_keepalive_fmt(peer_sec)}', f"Второй сервис: {peer_url or 'адрес не задан'}", '', f"Последний self-ping: {state.get('last_ok_at') or 'ещё не было'}", f"Последний основной → второй: {state.get('peer_last_ok_at') or 'ещё не было'}", f"Последний второй → основной: {state.get('peer_received_at') or 'НЕ ОБНАРУЖЕН'}", f"Последний внешний запрос: {state.get('last_inbound_activity_at') or 'ещё не было'} · {state.get('last_inbound_activity_kind') or '—'}", f"Последний авто-self-ping: {state.get('auto_last_trigger_at') or 'ещё не было'}", f"Self ошибки: {state.get('fail_count', 0)}; peer ошибки: {state.get('peer_fail_count', 0)}", '', 'Авторежим — страховка: пока второй Render/Telegram/внешние запросы приходят, он молчит. Если трафик пропал, self-ping срабатывает до 15-минутного порога сна Render.', '', mega_traffic_stats_text(compact=True) if 'mega_traffic_stats_text' in globals() else 'MEGA traffic counter unavailable']
    return wm_owner('\n'.join(lines), 9)

def keepalive_self_status_text() -> str:
    state = globals().get('KEEP_ALIVE_STATE') or {}
    enabled = bool(globals().get('keepalive_self_enabled', lambda: KEEP_ALIVE_ENABLED)())
    seconds = int(globals().get('keepalive_self_interval_seconds', lambda: KEEP_ALIVE_INTERVAL_SECONDS)())
    auto_enabled = bool(globals().get('keepalive_auto_enabled', lambda: True)())
    auto_idle = int(globals().get('keepalive_auto_idle_seconds', lambda: 720)())
    auto_state = globals().get('keepalive_auto_runtime_state', lambda: {})() or {}
    mode = str(auto_state.get('mode') or '')
    if mode == 'standby_manual':
        auto_runtime = '⬜ ОЖИДАНИЕ — ручной самопеленг уже работает'
    elif mode == 'standby_peer':
        auto_runtime = '⬜ ОЖИДАНИЕ — ping второго Render приходит'
    elif mode == 'standby_external':
        auto_runtime = '⬜ ОЖИДАНИЕ — есть входящие запросы'
    elif mode == 'due':
        auto_runtime = '✅ СРАБАТЫВАЕТ — внешних запросов давно нет'
    else:
        auto_runtime = '⬜ ВЫКЛ'
    due = _keepalive_countdown(auto_state.get('due_in_seconds', 0))
    return wm_owner(f"💓 САМОПЕЛЕНГ RENDER\n\nРучной режим: {_toggle_state(enabled)}\nИнтервал ручного режима: {_keepalive_fmt(seconds)}\nАдрес: {APP_URL or 'не задан'}\n\nАвторежим-резерв: {_toggle_state(auto_enabled)}\nПорог без входящего трафика: {_keepalive_fmt(auto_idle)}\nСостояние авторежима: {auto_runtime}\nДо резервного self-ping: {(due if auto_enabled and (not enabled) else '—')}\nПоследний внешний запрос: {state.get('last_inbound_activity_at') or 'ещё не было'}\nИсточник: {state.get('last_inbound_activity_kind') or '—'}\nПоследний auto self-ping: {state.get('auto_last_trigger_at') or 'ещё не было'}\n\nПоследний self успех: {state.get('last_ok_at') or 'ещё не было'}\nПоследний HTTP: {state.get('last_status_code') or '—'}\nОшибок: {state.get('fail_count', 0)}\nПоследняя ошибка: {state.get('last_error') or 'нет'}\n\nРучной режим работает как раньше. Авторежим — независимая страховка: если ручной режим выключен и второй Render/Telegram/другие входящие запросы перестали приходить, бот сам делает один маленький HEAD /keepalive до засыпания Render. Когда входящий ping возвращается, авторежим автоматически снова ждёт и лишних self-запросов не делает.", 9)

def build_keepalive_self_keyboard(chat_id: int):
    enabled = bool(globals().get('keepalive_self_enabled', lambda: KEEP_ALIVE_ENABLED)())
    auto_enabled = bool(globals().get('keepalive_auto_enabled', lambda: True)())
    seconds = int(globals().get('keepalive_self_interval_seconds', lambda: KEEP_ALIVE_INTERVAL_SECONDS)())
    auto_idle = int(globals().get('keepalive_auto_idle_seconds', lambda: 720)())
    kb = types.InlineKeyboardMarkup(row_width=1)
    kb.row(IB(f"{('✅' if enabled else '⬜')} Ручной самопеленг", callback_data='keepalive_self_toggle'))
    kb.row(IB(f"{('✅' if auto_enabled else '⬜')} Авторежим-резерв", callback_data='keepalive_auto_toggle'))
    kb.row(IB(f'⏱ Ручной интервал: {_keepalive_fmt(seconds)}', callback_data='keepalive_self_interval'))
    kb.row(IB(f'🛡 Порог авторежима: {_keepalive_fmt(auto_idle)}', callback_data='keepalive_auto_interval'))
    kb.row(IB('🧪 Пеленговать себя сейчас', callback_data='keepalive_self_now'))
    kb.row(IB('🛰 Взаимный пеленг', callback_data='keepalive_peer'))
    kb.row(IB('🔙 Назад в Инфо', callback_data='journal_back'))
    return kb

def build_keepalive_interval_keyboard(kind: str, chat_id: int):
    kind = str(kind or 'self')
    if kind == 'peer':
        current = int(globals().get('keepalive_peer_interval_seconds', lambda: 600)())
        choices = tuple(globals().get('KEEPALIVE_SAFE_INTERVALS') or (300, 480, 600, 720, 840))
        prefix = 'keepalive_peer_set'
        back = 'keepalive_peer'
    elif kind == 'auto':
        current = int(globals().get('keepalive_auto_idle_seconds', lambda: 720)())
        choices = tuple(globals().get('KEEPALIVE_AUTO_SAFE_IDLE_SECONDS') or (600, 660, 720, 780, 840))
        prefix = 'keepalive_auto_set'
        back = 'keepalive_status'
    else:
        current = int(globals().get('keepalive_self_interval_seconds', lambda: 600)())
        choices = tuple(globals().get('KEEPALIVE_SAFE_INTERVALS') or (300, 480, 600, 720, 840))
        prefix = 'keepalive_self_set'
        back = 'keepalive_status'
    kb = types.InlineKeyboardMarkup(row_width=2)
    buttons = []
    for sec in choices:
        sec = int(sec)
        label = ('✅ ' if sec == current else '⬜ ') + _keepalive_fmt(sec)
        buttons.append(IB(label, callback_data=f'{prefix}:{sec}'))
    for i in range(0, len(buttons), 2):
        kb.row(*buttons[i:i + 2])
    kb.row(IB('🔙 Назад', callback_data=back))
    return kb

def keepalive_peer_status_text() -> str:
    state = globals().get('KEEP_ALIVE_STATE') or {}
    enabled = bool(globals().get('keepalive_peer_enabled', lambda: False)())
    seconds = int(globals().get('keepalive_peer_interval_seconds', lambda: 600)())
    peer_url = str(globals().get('keepalive_peer_target_url', lambda: '')() or '')
    incoming = state.get('peer_received_at') or 'НЕ ОБНАРУЖЕН'
    return wm_owner(f"🛰 ВЗАИМНЫЙ ПЕЛЕНГ / ВТОРОЙ RENDER\n\nОсновной бот → второй Render: {_toggle_state(enabled)}\nИнтервал исходящего пинга: {_keepalive_fmt(seconds)}\nАдрес второго Render: {peer_url or 'НЕ ЗАДАН'}\nПоследний успех основной → второй: {state.get('peer_last_ok_at') or 'ещё не было'}\n\nВторой Render → основной бот: {('✅ ПИНГ ПРИХОДИТ' if state.get('peer_received_at') else '⬜ ПИНГ ЕЩЁ НЕ ОБНАРУЖЕН')}\nПоследний входящий ping второго: {incoming}\nПоследняя исходящая ошибка: {state.get('peer_last_error') or 'нет'}\n\nЭто два независимых направления. Переключатель ниже управляет только Основной → второй. Направление Второй → основной задаётся TARGET_URL/PING_INTERVAL_SECONDS в peer_watchdog на втором Render. Входящий ping второго автоматически подавляет резервный auto-self-ping, пока приходит вовремя.", 9)

def build_keepalive_peer_keyboard(chat_id: int):
    enabled = bool(globals().get('keepalive_peer_enabled', lambda: False)())
    seconds = int(globals().get('keepalive_peer_interval_seconds', lambda: 600)())
    peer_url = str(globals().get('keepalive_peer_target_url', lambda: '')() or '')
    kb = types.InlineKeyboardMarkup(row_width=1)
    kb.row(IB(f"{('✅' if enabled else '⬜')} Основной → второй Render", callback_data='keepalive_peer_toggle'))
    kb.row(IB(f'⏱ Интервал: {_keepalive_fmt(seconds)}', callback_data='keepalive_peer_interval'))
    kb.row(IB('🔗 Изменить адрес второго сервиса' if peer_url else '🔗 Задать адрес второго сервиса', callback_data='keepalive_peer_url'))
    if peer_url:
        kb.row(IB('🧹 Очистить адрес', callback_data='keepalive_peer_clear'))
    kb.row(IB('🧪 Пеленговать второй сейчас', callback_data='keepalive_peer_now'))
    kb.row(IB('💓 Самопеленг / авторежим', callback_data='keepalive_status'))
    kb.row(IB('🔙 Назад в Инфо', callback_data='journal_back'))
    return kb
_EXPENSE_SHORTCUT_LOCK = threading.RLock()
_EXPENSE_SHORTCUT_EVENT_LIMIT = 200
_EXPENSE_SHORTCUT_RETRY_SECONDS = 30.0

def _expense_shortcut_root() -> dict:
    return data.setdefault('_global_settings', {}).setdefault('expense_shortcut', {})

def _expense_shortcut_persist():
    try:
        save_data(data, root_only=True)
    except TypeError:
        save_data(data)
    try:
        _mark_global_snapshot_pending()
    except Exception:
        pass
    try:
        if OWNER_ID:
            schedule_config_backup_for_chats(int(OWNER_ID), delay=0.4)
            schedule_quick_backup(int(OWNER_ID), 0.4)
    except Exception:
        pass

def expense_shortcut_config(create: bool=True) -> dict:
    with _EXPENSE_SHORTCUT_LOCK:
        cfg = _expense_shortcut_root()
        changed = False
        if create and (not str(cfg.get('token') or '').strip()):
            cfg['token'] = secrets.token_urlsafe(24)
            changed = True
        if create and (not cfg.get('target_chat_id')) and OWNER_ID:
            cfg['target_chat_id'] = int(OWNER_ID)
            changed = True
        if 'text' not in cfg:
            cfg['text'] = '💸 Был расход'
            changed = True
        if 'events' not in cfg or not isinstance(cfg.get('events'), list):
            cfg['events'] = []
            changed = True
        if changed:
            _expense_shortcut_persist()
        return cfg

def expense_shortcut_url() -> str:
    cfg = expense_shortcut_config(True)
    base = str(WEBHOOK_URL or APP_URL or '').strip().rstrip('/')
    if not base:
        return ''
    return f"{base}/expense-ping/{cfg.get('token')}"

def expense_shortcut_set_target(chat_id: int):
    with _EXPENSE_SHORTCUT_LOCK:
        cfg = expense_shortcut_config(True)
        cfg['target_chat_id'] = int(chat_id)
        _expense_shortcut_persist()
    return int(chat_id)

def expense_shortcut_regenerate_token() -> str:
    with _EXPENSE_SHORTCUT_LOCK:
        cfg = expense_shortcut_config(True)
        cfg['token'] = secrets.token_urlsafe(24)
        _expense_shortcut_persist()
        return str(cfg['token'])

def _expense_shortcut_find_event(event_id: str):
    cfg = expense_shortcut_config(True)
    for row in cfg.get('events') or []:
        if str((row or {}).get('id')) == str(event_id):
            return row
    return None

def _expense_shortcut_cleanup_events_locked(cfg: dict):
    events = list(cfg.get('events') or [])
    pending = [e for e in events if str((e or {}).get('status')) != 'sent']
    sent = [e for e in events if str((e or {}).get('status')) == 'sent'][-80:]
    cfg['events'] = (pending + sent)[-_EXPENSE_SHORTCUT_EVENT_LIMIT:]

def enqueue_expense_ping_event(source: str='iphone', force: bool=False) -> tuple[str, bool]:
    """Сначала сохраняет событие, затем фоном отправляет Telegram-сообщение."""
    with _EXPENSE_SHORTCUT_LOCK:
        cfg = expense_shortcut_config(True)
        now_ts = time.time()
        if not force:
            for old in reversed(cfg.get('events') or []):
                if now_ts - float((old or {}).get('created_ts') or 0) <= 6.0:
                    if str((old or {}).get('source')) == str(source):
                        return (str(old.get('id')), True)
                else:
                    break
        event_id = f'xp_{int(now_ts * 1000)}_{secrets.token_hex(4)}'
        row = {'id': event_id, 'created_ts': now_ts, 'created_at': now_local().isoformat(timespec='seconds'), 'target_chat_id': int(cfg.get('target_chat_id') or OWNER_ID or 0), 'text': str(cfg.get('text') or '💸 Был расход'), 'source': str(source or 'iphone'), 'status': 'pending', 'attempts': 0, 'last_error': ''}
        cfg.setdefault('events', []).append(row)
        _expense_shortcut_cleanup_events_locked(cfg)
        _expense_shortcut_persist()
    GENERAL_TASK_POOL.submit(f'expense-ping:{event_id}', _deliver_expense_ping_event, event_id)
    return (event_id, False)

def expense_compact_message_text(created_at: str | None=None) -> str:
    """Короткая отметка, чтобы не занимать место в финансовом чате."""
    try:
        dt = datetime.fromisoformat(str(created_at or ''))
    except Exception:
        dt = now_local()
    now_dt = now_local()
    if dt.date() == now_dt.date():
        stamp = dt.strftime('%H:%M')
    else:
        stamp = dt.strftime('%d.%m %H:%M')
    return f'💸 iPhone · {stamp}'

def _deliver_expense_ping_event(event_id: str):
    with _EXPENSE_SHORTCUT_LOCK:
        row = _expense_shortcut_find_event(event_id)
        if not row or str(row.get('status')) == 'sent':
            return True
        row['attempts'] = int(row.get('attempts') or 0) + 1
        target_chat_id = int(row.get('target_chat_id') or 0)
        created_at = str(row.get('created_at') or now_local().isoformat(timespec='seconds'))
    try:
        dt = datetime.fromisoformat(created_at)
    except Exception:
        dt = now_local()
    draft = expense_draft_for_event(event_id, target_chat_id, created_at) if 'expense_draft_for_event' in globals() else {'id': 0}
    draft_id = int((draft or {}).get('id') or 0)
    text = expense_compact_message_text(created_at)
    try:
        markup = expense_draft_message_keyboard(draft_id, target_chat_id) if draft_id and 'expense_draft_message_keyboard' in globals() else None
        sent = _tg_call_retry(bot.send_message, target_chat_id, text, reply_markup=markup, attempts=2, purpose='expense_ping_send')
        if draft_id and 'expense_draft_set_message' in globals():
            expense_draft_set_message(draft_id, int(getattr(sent, 'message_id', 0) or 0))
        with _EXPENSE_SHORTCUT_LOCK:
            row = _expense_shortcut_find_event(event_id)
            if row:
                row['status'] = 'sent'
                row['sent_at'] = now_local().isoformat(timespec='seconds')
                row['telegram_message_id'] = int(getattr(sent, 'message_id', 0) or 0)
                row['last_error'] = ''
                _expense_shortcut_cleanup_events_locked(expense_shortcut_config(True))
                _expense_shortcut_persist()
        try:
            bot_journal('expense_ping_sent', target_chat_id, f"event={event_id} source={(row.get('source') if row else '')}")
        except Exception:
            pass
        return True
    except Exception as exc:
        with _EXPENSE_SHORTCUT_LOCK:
            row = _expense_shortcut_find_event(event_id)
            if row:
                row['status'] = 'pending'
                row['last_error'] = str(exc)[:300]
                _expense_shortcut_persist()
        try:
            bot_journal('expense_ping_retry', target_chat_id, f'event={event_id} error={str(exc)[:240]}', 'WARN')
        except Exception:
            pass
        DELAYED_SCHEDULER.schedule(f'expense-ping-retry:{event_id}', _EXPENSE_SHORTCUT_RETRY_SECONDS, _deliver_expense_ping_event, event_id)
        return False

def schedule_expense_ping_recovery(delay: float=1.0):

    def _job():
        cfg = expense_shortcut_config(False)
        for row in list((cfg or {}).get('events') or []):
            if str((row or {}).get('status')) != 'sent' and row.get('id'):
                GENERAL_TASK_POOL.submit(f"expense-ping:{row.get('id')}", _deliver_expense_ping_event, str(row.get('id')))
    DELAYED_SCHEDULER.schedule('expense-ping-recovery', max(0.1, float(delay)), _job)

def build_expense_shortcut_text(chat_id: int) -> str:
    cfg = expense_shortcut_config(True)
    target = int(cfg.get('target_chat_id') or OWNER_ID or chat_id)
    url = expense_shortcut_url()
    pending = sum((1 for e in cfg.get('events') or [] if str((e or {}).get('status')) != 'sent'))
    url_text = html.escape(url) if url else 'APP_URL/WEBHOOK_URL не определён'
    return f"📱 Быстрый расход с iPhone\n\nЧат назначения: {html.escape(get_chat_display_name(target))}\nID: <code>{target}</code>\nОжидают доставки: {pending}\nКнопки в сообщении: {('✅ ВКЛ' if expense_quick_buttons_enabled() else '⬜ ВЫКЛ')}\nПодхвачены отметки за 2 дня: {html.escape(str(_expense_inbox_root().get('recent_event_migration_v142_at') or 'ещё нет'))}\n\nСкопируйте эту личную ссылку в приложение «Команды»:\n<code>{url_text}</code>\n\nТройное касание задней панели запустит команду, а бот отправит «💸 Был расход». Ссылка секретная: не публикуйте её."

def build_expense_shortcut_keyboard(chat_id: int):
    kb = types.InlineKeyboardMarkup(row_width=1)
    kb.row(IB('🎯 Выбрать чат', callback_data='expense_shortcut_pick'))
    kb.row(IB('📋 Прислать ссылку отдельно', callback_data='expense_shortcut_send_url'))
    kb.row(IB('🧪 Проверить сейчас', callback_data='expense_shortcut_test'))
    kb.row(IB(expense_quick_buttons_label(), callback_data='expense_quick_buttons_toggle'))
    kb.row(IB('🔐 Создать новую секретную ссылку', callback_data='expense_shortcut_regenerate'))
    day = get_chat_store(chat_id).get('current_view_day') or today_key()
    kb.row(IB('🔙 Назад в Инфо', callback_data=f'd:{day}:info'))
    kb.row(IB('⬅️ Назад осн. окно', callback_data=f'd:{day}:back_main'))
    return kb

def build_expense_shortcut_chat_menu(chat_id: int):
    kb = types.InlineKeyboardMarkup(row_width=2)
    current = int(expense_shortcut_config(True).get('target_chat_id') or OWNER_ID or chat_id)
    buttons = []
    for cid in collect_all_known_chat_ids(include_owner=True):
        if is_chat_bot_removed(cid):
            continue
        icon = '✅' if int(cid) == current else '▫️'
        buttons.append(IB(f'{icon} {chat_button_title(cid)}', callback_data=f'expense_shortcut_target:{cid}'))
    add_buttons_in_rows(kb, buttons, 2)
    kb.row(IB('🔙 Назад', callback_data='expense_shortcut_info'))
    day = get_chat_store(chat_id).get('current_view_day') or today_key()
    kb.row(IB('⬅️ Назад осн. окно', callback_data=f'd:{day}:back_main'))
    return kb

def build_journal_v208_menu_text() -> str:
    """Compact Telegram-safe menu; the full journal remains available as a file.

    v208 appended a ~3900-char tail to the status block, which deterministically
    crossed Telegram's 4096-char edit limit and made 📓 Журнал look unresponsive.
    """
    try:
        status = journal_v208_status_text()
    except Exception:
        status = '📓 Диагностический журнал'
    try:
        tail = format_journal_text(24)
    except Exception:
        tail = ''
    max_total = 3400
    tail_budget = 2100
    if len(tail) > tail_budget:
        tail = '…\n' + tail[-(tail_budget - 2):]
    header = '\n\n──────── Последние действия (компактно) ────────\n'
    text = status + (header + tail if tail else '')
    if len(text) > max_total:
        base = status + (header if tail else '')
        room = max(0, max_total - len(base))
        text = base + ('…\n' + tail[-max(0, room - 2):] if room and tail else '')
    return text[:max_total]

def build_journal_v208_menu_keyboard(chat_id: int):
    kb = types.InlineKeyboardMarkup(row_width=2)
    kb.row(IB(journal_toggle_label(), callback_data='journal_toggle_open'), IB('✅ MEGA gzip' if journal_compact_remote_effective_enabled() else '⬜ MEGA gzip', callback_data='journal_compact_toggle'))
    kb.row(IB(f'⏱ Batch: {journal_compact_interval_seconds() // 60} мин', callback_data='journal_compact_interval_menu'), IB('✅ Telegram API verbose' if verbose_telegram_journal_enabled() else '⬜ Telegram API verbose', callback_data='journal_verbose_toggle'))
    kb.row(IB('📄 Полный диагностический журнал', callback_data='journal_file'))
    kb.row(IB('📓 Журнал текущей версии', callback_data='journal_current_file'))
    _jfull = journal_download_base_name_for('full')
    _jf = _jfull if len(_jfull) <= 24 else _jfull[:21] + '…'
    _jcur = journal_download_base_name_for('current')
    _jc = _jcur if len(_jcur) <= 24 else _jcur[:21] + '…'
    kb.row(IB(f'✏️ Общий журнал: {_jf}', callback_data='journal_name_edit:full'))
    kb.row(IB(f'✏️ Текущий журнал: {_jc}', callback_data='journal_name_edit:current'))
    kb.row(IB('🤖 Скачать бот текущего деплоя', callback_data='journal_bot_source'))
    day = get_chat_store(int(chat_id)).get('current_view_day') or today_key()
    kb.row(IB('🔙 Назад', callback_data='journal_back'), IB('⬅️ Основное', callback_data=f'd:{day}:back_main'), IB('❌ Закрыть', callback_data='info_close'))
    return kb

def _v177_legacy_0216_build_info_keyboard(chat_id: int):
    kb = types.InlineKeyboardMarkup()
    layout = version_mode_layout()
    if is_owner_chat(chat_id):
        kb.row(IB('📓 Журнал', callback_data='journal_open'), IB(journal_toggle_label(), callback_data='journal_toggle'))
        if version_mode_feature('per_chat_journal'):
            kb.row(IB('🗂 Журналы чатов', callback_data='journal_chats_open'), IB(chat_journal_toggle_label(chat_id), callback_data=f'journal_chat_toggle:{chat_id}:0'))
        kb.row(IB(buttons_current_window_label(chat_id), callback_data='buttons_current_toggle'), IB(info_finance_toggle_label(chat_id), callback_data='info_finance_off'))
        if version_mode_feature('forward_copy_edit'):
            kb.row(IB(forward_copy_edit_mode_label(chat_id), callback_data='forward_copy_edit_mode_toggle'))
        kb.row(IB(forward_menu_style_label(chat_id), callback_data='forward_menu_style_toggle'), IB(icon_button_mode_label(chat_id), callback_data='icon_buttons_toggle'))
        kb.row(IB('🛡 Guard: ВКЛ — нажать отключить' if RESTORE_GUARD_ACTIVE else '🛡 Guard: ВЫКЛ — автобэкапы разрешены', callback_data='restore_guard_toggle'))
        kb.row(IB('☁️ Обновить JSON из MEGA', callback_data='mega_manual_restore'))
        kb.row(IB(total_secret_mask_label(chat_id), callback_data='total_secret_mask_toggle'), IB(f'🕔 {finance_day_start_label(chat_id)}', callback_data='finance_day5_toggle'))
        if version_mode_feature('mega_priority') and layout in {'v82', 'v83'}:
            kb.row(IB(mega_backup_priority_label(chat_id), callback_data='mega_priority_toggle'))
        elif version_mode_feature('mega_priority') and layout in {'v84', 'v85', 'v86', 'v87'}:
            kb.row(IB(mega_backup_priority_label(chat_id), callback_data='mega_priority_toggle'), IB(main_financial_value_buttons_label(chat_id), callback_data='main_financial_values_toggle'))
        if layout in {'v85', 'v86', 'v87'}:
            if layout == 'v87':
                kb.row(IB(gomonk_info_label(chat_id), callback_data=f'gomonk_open:{_gomonk_currency(chat_id)}'), IB(currency_mode_label(chat_id), callback_data='currency_menu'))
            elif layout == 'v86':
                kb.row(IB(gomonk_info_label(chat_id), callback_data=f'gomonk_open:{_gomonk_currency(chat_id)}'), IB(usd_display_label(chat_id), callback_data='usd_display_toggle'))
            else:
                kb.row(IB(gomonk_info_label(chat_id), callback_data=f'gomonk_open:{_gomonk_currency(chat_id)}'))
        if layout == 'v83':
            kb.row(IB(main_article_buttons_label(chat_id), callback_data='main_articles_toggle'))
        if version_mode_feature('keepalive_menu'):
            kb.row(IB('💓 Самопеленг', callback_data='keepalive_status'), IB('🛰 Второй сервер', callback_data='keepalive_peer'))
        kb.row(IB('⏱ Внутренние таймеры', callback_data='internal_timers'))
        kb.row(IB('☁️ Google Чт–Ср', callback_data=f'v169:gmenu:{int(chat_id)}'))
        kb.row(IB('📱 Быстрый расход iPhone', callback_data='expense_shortcut_info'))
        kb.row(IB(expense_quick_buttons_label(), callback_data='expense_quick_buttons_toggle'), IB(reminder_ui_mode_label(), callback_data='reminder_ui_mode_toggle'))
        kb.row(IB('⚠️ Неразобранные расходы', callback_data='expense_inbox_open'), IB('⚙️ Процессы', callback_data='process_center'))
        kb.row(IB(safety_profile_label(), callback_data='safety_profile_toggle'), IB('🧯 Проблемные задачи', callback_data='problem_tasks'))
        kb.row(IB('🔗 Целостность финансов', callback_data='integrity_status'))
        kb.row(IB(excel_table_style_label(chat_id), callback_data='excel_style_menu'))
        kb.row(IB('📘 Инструкция', callback_data='info_instruction'), IB('🚦 Очереди', callback_data='info_queues'))
        kb.row(IB('🖥 Render / Сервер', callback_data='runtime_watcher'))
        if active_bot_behavior_profile() in {'v93_current', 'v92_current', 'v91_current', 'v90_current'}:
            kb.row(IB('🧩 Delta / snapshots', callback_data='info_delta_status'))
        if is_primary_owner(chat_id):
            kb.row(IB('👥 /owners', callback_data='additional_owners'))
    else:
        kb.row(IB(info_finance_toggle_label(chat_id), callback_data='info_finance_off'))
        if version_mode_feature('forward_copy_edit'):
            kb.row(IB(forward_copy_edit_mode_label(chat_id), callback_data='forward_copy_edit_mode_toggle'))
        if layout in {'v84', 'v85', 'v86', 'v87'}:
            kb.row(IB(main_financial_value_buttons_label(chat_id), callback_data='main_financial_values_toggle'))
        if layout in {'v85', 'v86', 'v87'}:
            if layout == 'v87':
                kb.row(IB(gomonk_info_label(chat_id), callback_data=f'gomonk_open:{_gomonk_currency(chat_id)}'), IB(currency_mode_label(chat_id), callback_data='currency_menu'))
            elif layout == 'v86':
                kb.row(IB(gomonk_info_label(chat_id), callback_data=f'gomonk_open:{_gomonk_currency(chat_id)}'), IB(usd_display_label(chat_id), callback_data='usd_display_toggle'))
            else:
                kb.row(IB(gomonk_info_label(chat_id), callback_data=f'gomonk_open:{_gomonk_currency(chat_id)}'))
        elif layout == 'v83':
            kb.row(IB(main_article_buttons_label(chat_id), callback_data='main_articles_toggle'))
        kb.row(IB('⚙️ Процессы', callback_data='process_center'))
    kb.row(IB('⬅️ Назад осн. окно', callback_data=f"d:{get_chat_store(chat_id).get('current_view_day', today_key())}:back_main"), IB('❌ Закрыть', callback_data='info_close'))
    return kb
try:
    _v177_legacy_0216_build_info_keyboard.__name__ = 'build_info_keyboard'
except Exception:
    pass

def open_info_window(chat_id: int):
    info_text = wm_common(build_info_text(chat_id), 9)
    send_or_edit_stored_window(chat_id, 'info_msg_id', info_text, reply_markup=build_info_keyboard(chat_id), parse_mode=None, delay=None)

def _expense_anchor_rows(kb, store: dict, day_key: str, callback_builder, empty_text: str='Нет расходов в этот день'):
    records = expense_anchor_records_for_day(store, day_key)
    if records:
        for rec in records:
            rid = _record_int_id(rec)
            kb.row(IB(expense_anchor_button_label(rec, store), callback_data=callback_builder(rid)))
    else:
        kb.row(IB(empty_text, callback_data='none'))
    return records

def _send_category_pick_start_record(chat_id: int, message_id: int, start_key: str):
    store = get_chat_store(chat_id)
    kb = types.InlineKeyboardMarkup(row_width=1)
    _expense_anchor_rows(kb, store, start_key, lambda rid: cat_callback(f'cat_pick_start_record:{start_key}:{rid}'))
    kb.row(IB('➡️ Продолжить с начала дня', callback_data=cat_callback(f'cat_pick_start_record:{start_key}:0')))
    dt = datetime.strptime(start_key, '%Y-%m-%d')
    kb.row(IB('🔙 Назад к календарю', callback_data=cat_callback(f'cat_pick_start:{dt.year}:{dt.month}')))
    text = f'🎯 Точное начало периода\n📅 День: {fmt_date_ddmmyy(start_key)}\n\nВыберите расход, с которого начинать расчёт, или продолжите с начала дня.'
    send_or_edit_categories_window(chat_id, text, reply_markup=kb, preferred_message_id=message_id, marker_action='cat_pick_start_record:*')

def _category_end_day_buttons_precise(start_key: str, start_rid: int, view_year: int, view_month: int):
    kb = types.InlineKeyboardMarkup(row_width=7)
    last_day = calendar.monthrange(int(view_year), int(view_month))[1]
    buttons = []
    for dnum in range(1, last_day + 1):
        day_key = _date_key_from_ymd(view_year, view_month, dnum)
        if day_key < start_key:
            buttons.append(IB('·', callback_data='none'))
        else:
            buttons.append(IB(str(dnum), callback_data=cat_callback(f'cat_pick_set_end3:{start_key}:{int(start_rid)}:{view_year}:{view_month}:{dnum}')))
    for idx in range(0, len(buttons), 7):
        kb.row(*buttons[idx:idx + 7])
    return kb

def _send_category_pick_end_precise(chat_id: int, message_id: int, start_key: str, start_rid: int, view_year: int, view_month: int):
    store = get_chat_store(chat_id)
    kb = _category_end_day_buttons_precise(start_key, start_rid, view_year, view_month)
    prev_y, prev_m = _shift_month(view_year, view_month, -1)
    next_y, next_m = _shift_month(view_year, view_month, 1)
    start_month_key = start_key[:7]
    nav = []
    if f'{prev_y:04d}-{prev_m:02d}' >= start_month_key:
        nav.append(IB('⬅️ Месяц', callback_data=cat_callback(f'cat_pick_end3:{start_key}:{int(start_rid)}:{prev_y}:{prev_m}')))
    else:
        nav.append(IB(' ', callback_data='none'))
    nav.append(IB(f'{russian_month_name(view_month)} {view_year}', callback_data='none'))
    nav.append(IB('Месяц ➡️', callback_data=cat_callback(f'cat_pick_end3:{start_key}:{int(start_rid)}:{next_y}:{next_m}')))
    kb.row(*nav)
    kb.row(IB(f'⏹ По сегодняшний день · {fmt_date_ddmmyy(today_key())}', callback_data=cat_callback(f'cat_pick_today_end:{start_key}:{int(start_rid)}')))
    start_dt = datetime.strptime(start_key, '%Y-%m-%d')
    kb.row(IB('🔙 Изменить начало', callback_data=cat_callback(f'cat_pick_set_start:{start_dt.year}:{start_dt.month}:{start_dt.day}')))
    text = f'🎯 Точный период расходов\n▶️ Начало: {exact_boundary_text(store, start_key, start_rid, True)}\n\nВыберите конечный день: {russian_month_name(view_month)} {view_year}'
    send_or_edit_categories_window(chat_id, text, reply_markup=kb, preferred_message_id=message_id, marker_action='cat_pick_end3:*')

def _send_category_pick_end_record(chat_id: int, message_id: int, start_key: str, start_rid: int, end_key: str):
    store = get_chat_store(chat_id)
    kb = types.InlineKeyboardMarkup(row_width=1)
    records = expense_anchor_records_for_day(store, end_key)
    displayed = 0
    all_recs = sorted_records_for_day(store, end_key)
    pos = {_record_int_id(r): i for i, r in enumerate(all_recs)}
    for rec in records:
        rid = _record_int_id(rec)
        if end_key == start_key and start_rid:
            if pos.get(rid, -1) < pos.get(int(start_rid), 0):
                continue
        displayed += 1
        kb.row(IB(expense_anchor_button_label(rec, store), callback_data=cat_callback(f'cat_pick_end_record:{start_key}:{int(start_rid)}:{end_key}:{rid}')))
    if not displayed:
        kb.row(IB('Нет подходящих расходов в этот день', callback_data='none'))
    kb.row(IB('✅ Продолжить до конца дня', callback_data=cat_callback(f'cat_pick_end_record:{start_key}:{int(start_rid)}:{end_key}:0')))
    end_dt = datetime.strptime(end_key, '%Y-%m-%d')
    kb.row(IB('🔙 Назад к календарю', callback_data=cat_callback(f'cat_pick_end3:{start_key}:{int(start_rid)}:{end_dt.year}:{end_dt.month}')))
    text = f'🎯 Точный конец периода\n▶️ Начало: {exact_boundary_text(store, start_key, start_rid, True)}\n📅 Конечный день: {fmt_date_ddmmyy(end_key)}\n\nВыберите последний расход, который включить в расчёт, или продолжите до конца дня.'
    send_or_edit_categories_window(chat_id, text, reply_markup=kb, preferred_message_id=message_id, marker_action='cat_pick_end_record:*')

def build_categories_record_summary_keyboard(start_key: str, start_rid: int, end_key: str, end_rid: int, store: dict):
    kb = types.InlineKeyboardMarkup(row_width=3)
    cats = calc_categories_for_record_range(store, start_key, start_rid, end_key, end_rid)
    buttons = []
    for category in get_ordered_category_names(cats=cats, store=store):
        slug = get_expense_category_slug(category, store)
        if slug:
            buttons.append(IB(_clean_category_display_name(category), callback_data=cat_callback(f'cat_show_records:{start_key}:{int(start_rid)}:{end_key}:{int(end_rid)}:{slug}')))
    add_buttons_in_rows(kb, buttons, 3)
    if _v85_enabled('usd_categories') and (not financial_view_is_usd(store)):
        usd_on = bool(store.setdefault('settings', {}).get('category_usd_enabled', False))
        kb.row(IB('✅ 💵 USD: ВКЛ' if usd_on else '⬜ 💵 USD: ВЫКЛ', callback_data=cat_callback(f'cat_usd_toggle_records:{start_key}:{int(start_rid)}:{end_key}:{int(end_rid)}')))
    kb.row(IB('↕️ Расположение', callback_data=cat_callback(f'cat_order_open_exact:{start_key}:{int(start_rid)}:{end_key}:{int(end_rid)}')))
    start_dt = datetime.strptime(start_key, '%Y-%m-%d')
    end_dt = datetime.strptime(end_key, '%Y-%m-%d')
    kb.row(IB('⬅️ Назад', callback_data=cat_callback(f'cat_pick_set_end3:{start_key}:{int(start_rid)}:{end_dt.year}:{end_dt.month}:{end_dt.day}')), IB('🎯 Выбрать заново', callback_data=cat_callback(f'cat_pick_start:{start_dt.year}:{start_dt.month}')))
    kb.row(IB('⬅️ Назад осн. окно', callback_data=f'd:{today_key()}:back_main'), IB('❌ Закрыть', callback_data=cat_callback('cat_close')))
    return kb

def build_category_record_detail_text(store: dict, start_key: str, start_rid: int, end_key: str, end_rid: int, category: str):
    items = collect_items_for_category_record_range(store, start_key, start_rid, end_key, end_rid, category)
    view_usd = financial_view_is_usd(store)
    mode = currency_mode_from_store(store)
    category_mixed = bool(not view_usd and store.setdefault('settings', {}).get('category_usd_enabled', False) and _v85_enabled('usd_categories'))
    show_rate = not view_usd and (mode != 'ars' or category_mixed)
    rate_info = usd_rate_cached() if show_rate else None
    total = sum((amount for _, amount, _ in items))
    clean_category = _clean_category_display_name(category).upper()
    lines = [f'📦 {clean_category}', f'▶️ {exact_boundary_text(store, start_key, start_rid, True)}', f'⏹ {exact_boundary_text(store, end_key, end_rid, False)}', '', f'Итого: {format_category_view_amount(store, total, category_mixed)}']
    if show_rate and rate_info:
        lines.append(f"Курс: 1 USD = {fmt_num(rate_info['rate']).lstrip('+')} ARS ({_clean_category_display_name(rate_info.get('source') or 'DolarAPI')})")
    lines.append('')
    if not items:
        lines.append('Нет операций по этой статье.')
    else:
        for day_key, amount, note in items:
            clean_note = _clean_category_display_name(str(note or '').strip())
            lines.append(f'• {fmt_date_ddmmyy(day_key)}: {format_category_view_amount(store, amount, category_mixed)} {clean_note}'.rstrip())
    return wm_common('\n'.join(lines), 8)
_category_other_sort_state = {}

def _other_sort_key(chat_id: int, start_key: str, start_rid: int, end_key: str, end_rid: int):
    return (int(chat_id), str(start_key), int(start_rid), str(end_key), int(end_rid))

def other_sort_records(store: dict, start_key: str, start_rid: int, end_key: str, end_rid: int) -> list[dict]:
    out = []
    for _day, rec in exact_record_range(store, start_key, start_rid, end_key, end_rid):
        try:
            if financial_view_amount(store, rec) >= 0:
                continue
        except Exception:
            continue
        category = resolve_expense_category_for_record(rec, store)
        if get_expense_category_slug(category, store) == 'other':
            out.append(rec)
    return out

def build_other_sort_text(store: dict, start_key: str, start_rid: int, end_key: str, end_rid: int) -> str:
    count = len(other_sort_records(store, start_key, start_rid, end_key, end_rid))
    return wm_common(f'🔀 Сортировка статьи ПРОЧЕЕ\n\nВыберите финансовые значения, которые нужно перенести в другую статью. После выбора нажмите «Выбрать их».\n\nДоступно записей: {count}', 8)

def build_other_sort_keyboard(chat_id: int, store: dict, start_key: str, start_rid: int, end_key: str, end_rid: int):
    kb = types.InlineKeyboardMarkup(row_width=1)
    key = _other_sort_key(chat_id, start_key, start_rid, end_key, end_rid)
    selected = _category_other_sort_state.setdefault(key, set())
    valid_ids = set()
    for rec in other_sort_records(store, start_key, start_rid, end_key, end_rid):
        rid = _record_int_id(rec)
        valid_ids.add(rid)
        mark = '✅' if rid in selected else '▫️'
        label = f'{mark} {financial_record_button_label(rec, chat_id)}'
        kb.row(IB(label, callback_data=cat_callback(f'cat_other_sort_toggle:{rid}:{start_key}:{int(start_rid)}:{end_key}:{int(end_rid)}')))
    selected.intersection_update(valid_ids)
    if selected:
        kb.row(IB(f'✅ Выбрать их ({len(selected)})', callback_data=cat_callback(f'cat_other_sort_choose:{start_key}:{int(start_rid)}:{end_key}:{int(end_rid)}')))
    else:
        kb.row(IB('Выберите значения выше', callback_data='none'))
    kb.row(IB('⬅️ Назад', callback_data=cat_callback(f'cat_show_records:{start_key}:{int(start_rid)}:{end_key}:{int(end_rid)}:other')))
    kb.row(IB('⬅️ Назад осн. окно', callback_data=f'd:{today_key()}:back_main'), IB('❌ Закрыть', callback_data=cat_callback('cat_close')))
    return kb

def build_other_sort_target_text(chat_id: int, start_key: str, start_rid: int, end_key: str, end_rid: int) -> str:
    key = _other_sort_key(chat_id, start_key, start_rid, end_key, end_rid)
    selected = _category_other_sort_state.get(key, set())
    return wm_common(f'📦 Куда перенести выбранные записи?\n\nВыбрано: {len(selected)}', 8)

def build_other_sort_target_keyboard(chat_id: int, store: dict, start_key: str, start_rid: int, end_key: str, end_rid: int):
    kb = types.InlineKeyboardMarkup(row_width=2)
    buttons = []
    for slug in get_expense_category_order_slugs(store):
        if slug == 'other':
            continue
        name = _clean_category_display_name(get_category_by_slug(slug, store) or slug)
        buttons.append(IB(name, callback_data=cat_callback(f'cat_other_sort_target:{slug}:{start_key}:{int(start_rid)}:{end_key}:{int(end_rid)}')))
    add_buttons_in_rows(kb, buttons, 2)
    kb.row(IB('⬅️ Назад к выбору', callback_data=cat_callback(f'cat_other_sort:{start_key}:{int(start_rid)}:{end_key}:{int(end_rid)}')))
    kb.row(IB('⬅️ Назад осн. окно', callback_data=f'd:{today_key()}:back_main'), IB('❌ Закрыть', callback_data=cat_callback('cat_close')))
    return kb

def apply_other_sort_target(store: dict, selected_ids: set[int], target_slug: str) -> int:
    changed = 0
    ids = {int(x) for x in selected_ids}
    for rec in store.get('records', []) or []:
        if _record_int_id(rec) in ids:
            rec['category_override_slug'] = str(target_slug)
            changed += 1
    for arr in (store.get('daily_records', {}) or {}).values():
        for rec in arr or []:
            if _record_int_id(rec) in ids:
                rec['category_override_slug'] = str(target_slug)
    return changed

def build_category_record_detail_keyboard(start_key: str, start_rid: int, end_key: str, end_rid: int, category: str | None=None, store: dict | None=None):
    kb = types.InlineKeyboardMarkup()
    if category and get_expense_category_slug(category, store) == 'other':
        kb.row(IB('🔀 Сортировка', callback_data=cat_callback(f'cat_other_sort:{start_key}:{int(start_rid)}:{end_key}:{int(end_rid)}')))
    kb.row(IB('⬅️ Назад', callback_data=cat_callback(f'cat_back_records:{start_key}:{int(start_rid)}:{end_key}:{int(end_rid)}')))
    kb.row(IB('⬅️ Назад осн. окно', callback_data=f'd:{today_key()}:back_main'), IB('❌ Закрыть', callback_data=cat_callback('cat_close')))
    return kb

def _category_picker_day_buttons(year: int, month: int, stage: str, start_day: int | None=None, selected_day: int | None=None):
    kb = types.InlineKeyboardMarkup(row_width=7)
    last_day = calendar.monthrange(int(year), int(month))[1]
    buttons = []
    for dnum in range(1, last_day + 1):
        label = f'✅{dnum}' if selected_day == dnum else str(dnum)
        if stage == 'start':
            cb = cat_callback(f'cat_pick_set_start:{year}:{month}:{dnum}')
        else:
            cb = cat_callback(f'cat_pick_set_end:{year}:{month}:{int(start_day or 1)}:{dnum}')
        buttons.append(IB(label, callback_data=cb))
    for i in range(0, len(buttons), 7):
        kb.row(*buttons[i:i + 7])
    return kb

def _send_category_pick_start(chat_id: int, message_id: int, year: int, month: int, selected: int | None=None):
    kb = _category_picker_day_buttons(year, month, 'start', selected_day=selected)
    if selected:
        kb.row(IB('✅ Выбрать это', callback_data=cat_callback(f'cat_pick_end:{year}:{month}:{selected}')))
    kb.row(IB('🔙 Назад', callback_data=cat_callback(f'cat_m:{year}:{month}')))
    text = f'📅 Выберите начальную дату: {month:02d}.{year}'
    if selected:
        text += f'\n✅ Начало: {selected:02d}.{month:02d}.{year}'
    send_or_edit_categories_window(chat_id, wm_common(text, 13), reply_markup=kb, preferred_message_id=message_id, marker_action='cat_pick_start:*')

def _shift_month(year: int, month: int, delta: int=0) -> tuple[int, int]:
    base = datetime(int(year), int(month), 1)
    m0 = base.year * 12 + base.month - 1 + int(delta or 0)
    y = m0 // 12
    m = m0 % 12 + 1
    return (y, m)

def _date_key_from_ymd(year: int, month: int, day: int) -> str:
    last_day = calendar.monthrange(int(year), int(month))[1]
    d = max(1, min(int(day), last_day))
    return f'{int(year):04d}-{int(month):02d}-{d:02d}'

def _category_picker_day_buttons_end_any_month(start_key: str, view_year: int, view_month: int, selected_key: str | None=None):
    kb = types.InlineKeyboardMarkup(row_width=7)
    last_day = calendar.monthrange(int(view_year), int(view_month))[1]
    buttons = []
    for dnum in range(1, last_day + 1):
        dk = _date_key_from_ymd(view_year, view_month, dnum)
        label = f'✅{dnum}' if selected_key == dk else str(dnum)
        buttons.append(IB(label, callback_data=cat_callback(f'cat_pick_set_end2:{start_key}:{int(view_year)}:{int(view_month)}:{dnum}')))
    for i in range(0, len(buttons), 7):
        kb.row(*buttons[i:i + 7])
    return kb

def _send_category_pick_end_any_month(chat_id: int, message_id: int, start_key: str, view_year: int, view_month: int, selected_end_key: str | None=None):
    start_dt = datetime.strptime(str(start_key)[:10], '%Y-%m-%d')
    kb = _category_picker_day_buttons_end_any_month(start_key, view_year, view_month, selected_key=selected_end_key)
    prev_y, prev_m = _shift_month(view_year, view_month, -1)
    next_y, next_m = _shift_month(view_year, view_month, 1)
    kb.row(IB('⬅️ Месяц', callback_data=cat_callback(f'cat_pick_end2:{start_key}:{prev_y}:{prev_m}')), IB(f'{int(view_month):02d}.{int(view_year)}', callback_data='none'), IB('Месяц ➡️', callback_data=cat_callback(f'cat_pick_end2:{start_key}:{next_y}:{next_m}')))
    if selected_end_key:
        kb.row(IB('✅ Выбрать конечное', callback_data=cat_callback(f'cat_range_custom2:{start_key}:{selected_end_key}')))
    kb.row(IB('🔙 Назад к началу', callback_data=cat_callback(f'cat_pick_set_start:{start_dt.year}:{start_dt.month}:{start_dt.day}')))
    text = f'📅 Начало: {fmt_date_ddmmyy(start_key)}\nВыберите конечную дату: {int(view_month):02d}.{int(view_year)}'
    if selected_end_key:
        text += f'\n✅ Конец: {fmt_date_ddmmyy(selected_end_key)}'
    send_or_edit_categories_window(chat_id, wm_common(text, 13), reply_markup=kb, preferred_message_id=message_id)

def _send_category_pick_end(chat_id: int, message_id: int, year: int, month: int, start_day: int, selected_end: int | None=None):
    start_key = _date_key_from_ymd(year, month, start_day)
    selected_end_key = _date_key_from_ymd(year, month, selected_end) if selected_end else None
    _send_category_pick_end_any_month(chat_id, message_id, start_key, int(year), int(month), selected_end_key)

def handle_categories_callback(call, data_str: str) -> bool:
    """UI окна расходов по статьям."""
    chat_id = call.message.chat.id
    store = get_chat_store(chat_id)
    if data_str.startswith('cat_page:'):
        requested = data_str.split(':', 1)[1] if ':' in data_str else '0'
        _show_category_page(chat_id, call.message.message_id, requested)
        try:
            bot.answer_callback_query(call.id)
        except Exception:
            pass
        return True
    if data_str == 'cat_prompt_back':
        was_edit = bool(store.get('category_edit_wait'))
        clear_category_wait_state(chat_id, 'category_add_wait', call.message.message_id, delete_prompt=False)
        clear_category_wait_state(chat_id, 'category_edit_wait', call.message.message_id, delete_prompt=False)
        if was_edit:
            send_or_edit_categories_window(chat_id, wm_common('✏️ Изменить статью\n\nВыберите статью. Б = базовая, С = своя.', 14), reply_markup=build_category_edit_keyboard(chat_id), preferred_message_id=call.message.message_id)
        else:
            return handle_categories_callback(call, 'cat_today')
        return True
    if data_str == 'cat_add_cancel':
        clear_category_wait_state(chat_id, 'category_add_wait', call.message.message_id, delete_prompt=True)
        clear_category_wait_state(chat_id, 'category_edit_wait', call.message.message_id, delete_prompt=True)
        try:
            bot.answer_callback_query(call.id, 'Команда отменена')
        except Exception:
            pass
        return True
    if data_str.startswith('cat_main_edit:'):
        try:
            parts = data_str.split(':', 2)
            slug = parts[1]
        except Exception:
            return True
        start_category_edit_wait(chat_id, chat_id, slug)
        try:
            bot.answer_callback_query(call.id, 'Редактирование статьи', show_alert=False)
        except Exception:
            pass
        return True
    if data_str == 'cat_edit_menu':
        send_or_edit_categories_window(chat_id, wm_common('✏️ Изменить статью\n\nВыберите статью. Б = базовая, С = своя. Можно менять название и ключевые слова.', 14), reply_markup=build_category_edit_keyboard(chat_id), preferred_message_id=call.message.message_id)
        return True
    if data_str.startswith('cat_edit_pick:'):
        slug = data_str.split(':', 1)[1]
        start_category_edit_wait(chat_id, chat_id, slug)
        try:
            bot.answer_callback_query(call.id, 'Напиши новую статью и ключи', show_alert=False)
        except Exception:
            pass
        return True
    if data_str == 'cat_del_menu':
        clear_category_wait_state(chat_id, 'category_add_wait', delete_prompt=False)
        clear_category_wait_state(chat_id, 'category_edit_wait', delete_prompt=False)
        store['category_delete_selection'] = []
        save_data(data)
        send_or_edit_categories_window(chat_id, wm_common('🗑 Удалить статью\n\nВыберите пользовательские статьи галочками и нажмите «Удалить выбранное». Стандартные статьи не удаляем, чтобы не ломать базовую логику.', 15), reply_markup=build_category_delete_keyboard(chat_id), preferred_message_id=call.message.message_id)
        return True
    if data_str.startswith('cat_del_toggle:'):
        slug = data_str.split(':', 1)[1]
        selected = set(store.get('category_delete_selection') or [])
        if slug in selected:
            selected.remove(slug)
        else:
            selected.add(slug)
        store['category_delete_selection'] = sorted(selected)
        save_data(data)
        send_or_edit_categories_window(chat_id, wm_common('🗑 Удалить статью\n\nВыберите пользовательские статьи галочками и нажмите «Удалить выбранное».', 15), reply_markup=build_category_delete_keyboard(chat_id), preferred_message_id=call.message.message_id)
        return True
    if data_str == 'cat_del_selected':
        selected = set(store.get('category_delete_selection') or [])
        if not selected:
            try:
                bot.answer_callback_query(call.id, 'Ничего не выбрано', show_alert=False)
            except Exception:
                pass
            return True
        count = remove_custom_expense_categories(chat_id, selected)
        try:
            bot.answer_callback_query(call.id, f'Удалено статей: {count}', show_alert=False)
        except Exception:
            pass
        return handle_categories_callback(call, 'cat_today')
    if data_str == 'cat_close':
        mid = store.get('categories_msg_id')
        if mid:
            try:
                bot.delete_message(chat_id, mid)
            except Exception:
                pass
        if mid:
            unregister_open_window(chat_id, int(mid))
        store['categories_msg_id'] = None
        store['categories_refresh_state'] = None
        store.pop('categories_pagination', None)
        save_data(data, chat_ids=[int(chat_id)])
        return True
    if data_str == 'cat_today':
        return handle_categories_callback(call, f'cat_wthu:{today_key()}')
    if data_str == 'cat_add':
        start_category_add_wait(chat_id, chat_id)
        try:
            bot.answer_callback_query(call.id, 'Напиши название и ключи статьи', show_alert=False)
        except Exception:
            pass
        return True
    if data_str == 'cat_desc':
        kb = types.InlineKeyboardMarkup()
        kb.row(IB('🔙 Назад к статьям', callback_data=cat_callback(f'cat_wthu:{today_key()}')))
        kb.row(IB('⬅️ Назад осн. окно', callback_data=f'd:{today_key()}:back_main'), IB('❌ Закрыть статьи', callback_data=cat_callback('cat_close')))
        send_or_edit_categories_window(chat_id, build_articles_description_text(chat_id), reply_markup=kb, preferred_message_id=call.message.message_id)
        return True
    if data_str.startswith('cat_wthu:'):
        ref = data_str.split(':', 1)[1] or today_key()
        start_key = week_start_thursday(ref)
        start, end = week_bounds_thu_wed(start_key)
        label = f'{fmt_date_ddmmyy(start)} — {fmt_date_ddmmyy(end)} (Чт–Ср)'
        text, _ = summarize_categories(store, start, end, label)
        kb = build_categories_summary_keyboard('wthu', start, end, store=store)
        send_or_edit_categories_window(chat_id, text, reply_markup=kb, preferred_message_id=call.message.message_id)
        return True
    if data_str.startswith('cat_wk:'):
        start_key = data_str.split(':', 1)[1].strip() or week_start_monday(today_key())
        start, end = week_bounds_from_start(start_key)
        label = f'{fmt_date_ddmmyy(start)} — {fmt_date_ddmmyy(end)} (Пн–Вс)'
        text, _ = summarize_categories(store, start, end, label)
        kb = build_categories_summary_keyboard('wk', start, end, store=store)
        send_or_edit_categories_window(chat_id, text, reply_markup=kb, preferred_message_id=call.message.message_id)
        return True
    if data_str == 'cat_months' or data_str.startswith('cat_months_y:'):
        try:
            year = int(data_str.split(':', 1)[1]) if data_str.startswith('cat_months_y:') else now_local().year
        except Exception:
            year = now_local().year
        kb = types.InlineKeyboardMarkup(row_width=2)
        month_buttons = []
        current_ym = now_local().strftime('%Y-%m')
        for m in range(1, 13):
            ym = f'{year:04d}-{m:02d}'
            label = f'📍 {russian_month_name(m)} ({m}) — текущий' if ym == current_ym else f'{russian_month_name(m)} ({m})'
            month_buttons.append(IB(label, callback_data=cat_callback(f'cat_m:{year}:{m}')))
        for i in range(0, len(month_buttons), 2):
            kb.row(*month_buttons[i:i + 2])
        kb.row(IB('⬅️ Год', callback_data=cat_callback(f'cat_months_y:{year - 1}')), IB(str(year), callback_data='none'), IB('Год ➡️', callback_data=cat_callback(f'cat_months_y:{year + 1}')))
        kb.row(IB('📅 Сегодня', callback_data=cat_callback('cat_today')), IB('⬅️ Назад осн. окно', callback_data=f'd:{today_key()}:back_main'), IB('❌ Закрыть статьи', callback_data=cat_callback('cat_close')))
        send_or_edit_categories_window(chat_id, wm_common(f'📦 Выберите месяц, год {year}:', 12), reply_markup=kb, marker_action='markup:plain')
        return True
    if data_str.startswith('cat_m:'):
        try:
            parts = data_str.split(':')
            if len(parts) >= 3:
                year, month = (int(parts[1]), int(parts[2]))
            else:
                year, month = (now_local().year, int(parts[1]))
        except Exception:
            return True
        last_day = calendar.monthrange(year, month)[1]
        kb = types.InlineKeyboardMarkup(row_width=7)
        weeks = [(1, 7), (8, 14), (15, 21), (22, last_day)]
        kb.row(*[IB(f'{a:02d}–{b:02d}', callback_data=cat_callback(f'cat_rng:{year}:{month}:{a}:{b}')) for a, b in weeks])
        kb.row(IB('📅 Произвольный период', callback_data=cat_callback(f'cat_pick_start:{year}:{month}')))
        row = []
        if month != now_local().month or year != now_local().year:
            row.append(IB('📅 Сегодня', callback_data=cat_callback('cat_today')))
        row.append(IB('🔙 Назад', callback_data=cat_callback('cat_months')))
        kb.row(*row)
        send_or_edit_categories_window(chat_id, wm_common(f'📆 Выберите неделю: {russian_month_name(month)} ({month}) {year}', 13), reply_markup=kb, marker_action='cat_m:*')
        return True
    if data_str.startswith('cat_pick_start:'):
        try:
            _, y, m = data_str.split(':')
            _send_category_pick_start(chat_id, call.message.message_id, int(y), int(m))
        except Exception as e:
            log_error(f'cat_pick_start: {e}')
        return True
    if data_str.startswith('cat_pick_set_start:'):
        try:
            _, y, m, d = data_str.split(':')
            start_key = _date_key_from_ymd(int(y), int(m), int(d))
            _send_category_pick_start_record(chat_id, call.message.message_id, start_key)
        except Exception as e:
            log_error(f'cat_pick_set_start: {e}')
        return True
    if data_str.startswith('cat_pick_start_record:'):
        try:
            _, start_key, start_rid = data_str.split(':')
            start_dt = datetime.strptime(start_key, '%Y-%m-%d')
            _send_category_pick_end_precise(chat_id, call.message.message_id, start_key, int(start_rid), start_dt.year, start_dt.month)
        except Exception as e:
            log_error(f'cat_pick_start_record: {e}')
        return True
    if data_str.startswith('cat_pick_today_end:'):
        try:
            _, start_key, start_rid = data_str.split(':')
            end_key = today_key()
            if end_key < start_key:
                end_key = start_key
            _send_category_pick_end_record(chat_id, call.message.message_id, start_key, int(start_rid), end_key)
        except Exception as e:
            log_error(f'cat_pick_today_end: {e}')
        return True
    if data_str == 'cat_pick_today_start':
        try:
            start_key = today_key()
            now_dt = now_local()
            _send_category_pick_end_precise(chat_id, call.message.message_id, start_key, 0, now_dt.year, now_dt.month)
        except Exception as e:
            log_error(f'cat_pick_today_start: {e}')
        return True
    if data_str.startswith('cat_usd_toggle_period:'):
        try:
            _, mode, start, end = data_str.split(':', 3)
            settings = store.setdefault('settings', {})
            settings['category_usd_enabled'] = not bool(settings.get('category_usd_enabled', False))
            save_data(data, chat_ids=[chat_id])
            schedule_config_backup_for_chats(chat_id)
            if settings['category_usd_enabled']:
                usd_rate_cached(force=False)
            label = f'{fmt_date_ddmmyy(start)} — {fmt_date_ddmmyy(end)}'
            text, _ = summarize_categories(store, start, end, label)
            kb = build_categories_summary_keyboard(mode, start, end, store=store)
            marker = 'cat_wthu:*' if mode == 'wthu' else 'cat_wk:*' if mode == 'wk' else 'cat_range_custom2:*'
            send_or_edit_categories_window(chat_id, text, reply_markup=kb, preferred_message_id=call.message.message_id, marker_action=marker)
        except Exception as e:
            log_error(f'cat_usd_toggle_period: {e}')
        return True

    def _refresh_layout_same_message(context: str, params: tuple, marker_action: str):
        text = build_category_layout_text(store, context)
        kb = build_category_layout_keyboard(store, context, params, chat_id=chat_id)
        final_text = window_mark(strip_window_mark(text), _window_marker_code(marker_action, 'Ф'))
        result = fast_ui_edit_message_text(chat_id, call.message.message_id, final_text, reply_markup=kb, purpose='category_layout_v178')
        if str(result or '') not in {'ok', 'scheduled'}:
            raise RuntimeError(f'category layout edit failed: {result}')
        store['categories_msg_id'] = int(call.message.message_id)
        register_open_window(chat_id, int(call.message.message_id), 'categories', code=marker_action)
        save_data(data, chat_ids=[int(chat_id)])
        return int(call.message.message_id)
    if data_str.startswith('cat_order_open_sum:'):
        try:
            _, mode, start, end = data_str.split(':', 3)
            _refresh_layout_same_message('sum', (mode, start, end), 'cat_order_open_sum:*')
        except Exception as e:
            log_error(f'cat_order_open_sum: {e}')
        return True
    if data_str.startswith('cat_order_select_sum:'):
        try:
            _, slug, mode, start, end = data_str.split(':', 4)
            params = ('sum', mode, start, end)
            key = _category_order_selection_key(chat_id, params)
            _category_order_selection[key] = slug
            _refresh_layout_same_message('sum', (mode, start, end), 'cat_order_open_sum:*')
        except Exception as e:
            log_error(f'cat_order_select_sum: {e}')
        return True
    if data_str.startswith('cat_order_position_sum:'):
        try:
            _, position, mode, start, end = data_str.split(':', 4)
            params = ('sum', mode, start, end)
            key = _category_order_selection_key(chat_id, params)
            slug = _category_order_selection.get(key)
            if not slug:
                try:
                    bot.answer_callback_query(call.id, 'Сначала выберите статью')
                except Exception:
                    pass
                return True
            moved = move_expense_category_to_position(store, slug, int(position))
            _category_order_selection.pop(key, None)
            if moved:
                save_data(data, chat_ids=[chat_id])
                schedule_quick_backup(chat_id, MEGA_DELTA_PRIORITY_DELAY_SECONDS if mega_backup_priority_enabled() else MEGA_DELTA_DELAY_SECONDS)
                schedule_config_backup_for_chats(chat_id, delay=0.4)
            _refresh_layout_same_message('sum', (mode, start, end), 'cat_order_open_sum:*')
        except Exception as e:
            log_error(f'cat_order_position_sum: {e}')
        return True
    if data_str.startswith('cat_order_move_sum:'):
        try:
            _, slug, direction, mode, start, end = data_str.split(':', 5)
            if move_expense_category_order(store, slug, direction):
                save_data(data, chat_ids=[chat_id])
                schedule_config_backup_for_chats(chat_id)
            _refresh_layout_same_message('sum', (mode, start, end), 'cat_order_open_sum:*')
        except Exception as e:
            log_error(f'cat_order_move_sum: {e}')
        return True
    if data_str.startswith('cat_order_open_exact:'):
        try:
            _, start_key, start_rid, end_key, end_rid = data_str.split(':')
            _refresh_layout_same_message('exact', (start_key, int(start_rid), end_key, int(end_rid)), 'cat_order_open_exact:*')
        except Exception as e:
            log_error(f'cat_order_open_exact: {e}')
        return True
    if data_str.startswith('cat_order_select_exact:'):
        try:
            _, slug, start_key, start_rid, end_key, end_rid = data_str.split(':', 5)
            params = (start_key, int(start_rid), end_key, int(end_rid))
            key = _category_order_selection_key(chat_id, params)
            _category_order_selection[key] = slug
            _refresh_layout_same_message('exact', params, 'cat_order_open_exact:*')
        except Exception as e:
            log_error(f'cat_order_select_exact: {e}')
        return True
    if data_str.startswith('cat_order_position_exact:'):
        try:
            _, position, start_key, start_rid, end_key, end_rid = data_str.split(':', 5)
            params = (start_key, int(start_rid), end_key, int(end_rid))
            key = _category_order_selection_key(chat_id, params)
            slug = _category_order_selection.get(key)
            if not slug:
                try:
                    bot.answer_callback_query(call.id, 'Сначала выберите статью')
                except Exception:
                    pass
                return True
            moved = move_expense_category_to_position(store, slug, int(position))
            _category_order_selection.pop(key, None)
            if moved:
                save_data(data, chat_ids=[chat_id])
                schedule_quick_backup(chat_id, MEGA_DELTA_PRIORITY_DELAY_SECONDS if mega_backup_priority_enabled() else MEGA_DELTA_DELAY_SECONDS)
                schedule_config_backup_for_chats(chat_id, delay=0.4)
            _refresh_layout_same_message('exact', params, 'cat_order_open_exact:*')
        except Exception as e:
            log_error(f'cat_order_position_exact: {e}')
        return True
    if data_str.startswith('cat_order_move_exact:'):
        try:
            _, slug, direction, start_key, start_rid, end_key, end_rid = data_str.split(':', 6)
            if move_expense_category_order(store, slug, direction):
                save_data(data, chat_ids=[chat_id])
                schedule_config_backup_for_chats(chat_id)
            _refresh_layout_same_message('exact', (start_key, int(start_rid), end_key, int(end_rid)), 'cat_order_open_exact:*')
        except Exception as e:
            log_error(f'cat_order_move_exact: {e}')
        return True
    if data_str.startswith('cat_pick_end3:'):
        try:
            _, start_key, start_rid, y, m = data_str.split(':')
            _send_category_pick_end_precise(chat_id, call.message.message_id, start_key, int(start_rid), int(y), int(m))
        except Exception as e:
            log_error(f'cat_pick_end3: {e}')
        return True
    if data_str.startswith('cat_pick_set_end3:'):
        try:
            _, start_key, start_rid, y, m, d = data_str.split(':')
            end_key = _date_key_from_ymd(int(y), int(m), int(d))
            _send_category_pick_end_record(chat_id, call.message.message_id, start_key, int(start_rid), end_key)
        except Exception as e:
            log_error(f'cat_pick_set_end3: {e}')
        return True
    if data_str.startswith('cat_pick_end_record:'):
        try:
            _, start_key, start_rid, end_key, end_rid = data_str.split(':')
            text, _ = summarize_categories_record_range(store, start_key, int(start_rid), end_key, int(end_rid))
            kb = build_categories_record_summary_keyboard(start_key, int(start_rid), end_key, int(end_rid), store)
            send_or_edit_categories_window(chat_id, text, reply_markup=kb, preferred_message_id=call.message.message_id, marker_action='cat_range_records:*')
        except Exception as e:
            log_error(f'cat_pick_end_record: {e}')
        return True
    if data_str.startswith('cat_usd_toggle_records:'):
        try:
            _, start_key, start_rid, end_key, end_rid = data_str.split(':')
            settings = store.setdefault('settings', {})
            settings['category_usd_enabled'] = not bool(settings.get('category_usd_enabled', False))
            save_data(data, chat_ids=[chat_id])
            if settings['category_usd_enabled']:
                usd_rate_cached(force=False)
            text, _ = summarize_categories_record_range(store, start_key, int(start_rid), end_key, int(end_rid))
            kb = build_categories_record_summary_keyboard(start_key, int(start_rid), end_key, int(end_rid), store)
            send_or_edit_categories_window(chat_id, text, reply_markup=kb, preferred_message_id=call.message.message_id, marker_action='cat_range_records:*')
        except Exception as e:
            log_error(f'cat_usd_toggle_records: {e}')
        return True
    if data_str.startswith('cat_range_records:'):
        try:
            _, start_key, start_rid, end_key, end_rid = data_str.split(':')
            text, _ = summarize_categories_record_range(store, start_key, int(start_rid), end_key, int(end_rid))
            kb = build_categories_record_summary_keyboard(start_key, int(start_rid), end_key, int(end_rid), store)
            send_or_edit_categories_window(chat_id, text, reply_markup=kb, preferred_message_id=call.message.message_id, marker_action='cat_range_records:*')
        except Exception as e:
            log_error(f'cat_range_records: {e}')
        return True
    if data_str.startswith('cat_back_records:'):
        try:
            _, start_key, start_rid, end_key, end_rid = data_str.split(':')
            text, _ = summarize_categories_record_range(store, start_key, int(start_rid), end_key, int(end_rid))
            kb = build_categories_record_summary_keyboard(start_key, int(start_rid), end_key, int(end_rid), store)
            send_or_edit_categories_window(chat_id, text, reply_markup=kb, preferred_message_id=call.message.message_id, marker_action='cat_range_records:*')
        except Exception as e:
            log_error(f'cat_back_records: {e}')
        return True
    if data_str.startswith('cat_other_sort:'):
        try:
            _, start_key, start_rid, end_key, end_rid = data_str.split(':')
            send_or_edit_categories_window(chat_id, build_other_sort_text(store, start_key, int(start_rid), end_key, int(end_rid)), reply_markup=build_other_sort_keyboard(chat_id, store, start_key, int(start_rid), end_key, int(end_rid)), preferred_message_id=call.message.message_id, marker_action='cat_other_sort:*')
        except Exception as e:
            log_error(f'cat_other_sort: {e}')
        return True
    if data_str.startswith('cat_other_sort_toggle:'):
        try:
            _, rid, start_key, start_rid, end_key, end_rid = data_str.split(':')
            key = _other_sort_key(chat_id, start_key, int(start_rid), end_key, int(end_rid))
            selected = _category_other_sort_state.setdefault(key, set())
            rid_i = int(rid)
            if rid_i in selected:
                selected.remove(rid_i)
            else:
                selected.add(rid_i)
            send_or_edit_categories_window(chat_id, build_other_sort_text(store, start_key, int(start_rid), end_key, int(end_rid)), reply_markup=build_other_sort_keyboard(chat_id, store, start_key, int(start_rid), end_key, int(end_rid)), preferred_message_id=call.message.message_id, marker_action='cat_other_sort_toggle:*')
        except Exception as e:
            log_error(f'cat_other_sort_toggle: {e}')
        return True
    if data_str.startswith('cat_other_sort_choose:'):
        try:
            _, start_key, start_rid, end_key, end_rid = data_str.split(':')
            key = _other_sort_key(chat_id, start_key, int(start_rid), end_key, int(end_rid))
            if not _category_other_sort_state.get(key):
                bot.answer_callback_query(call.id, 'Сначала выберите записи', show_alert=False)
                return True
            send_or_edit_categories_window(chat_id, build_other_sort_target_text(chat_id, start_key, int(start_rid), end_key, int(end_rid)), reply_markup=build_other_sort_target_keyboard(chat_id, store, start_key, int(start_rid), end_key, int(end_rid)), preferred_message_id=call.message.message_id, marker_action='cat_other_sort_choose:*')
        except Exception as e:
            log_error(f'cat_other_sort_choose: {e}')
        return True
    if data_str.startswith('cat_other_sort_target:'):
        try:
            _, target_slug, start_key, start_rid, end_key, end_rid = data_str.split(':', 5)
            key = _other_sort_key(chat_id, start_key, int(start_rid), end_key, int(end_rid))
            selected = set(_category_other_sort_state.get(key, set()))
            changed = apply_other_sort_target(store, selected, target_slug)
            _category_other_sort_state.pop(key, None)
            if changed:
                save_data(data, chat_ids=[chat_id])
                finance_changed(chat_id, store.get('current_view_day') or today_key(), reason='category_manual_sort', delay=0.05)
                schedule_config_backup_for_chats(chat_id)
            text, _ = summarize_categories_record_range(store, start_key, int(start_rid), end_key, int(end_rid))
            kb = build_categories_record_summary_keyboard(start_key, int(start_rid), end_key, int(end_rid), store)
            send_or_edit_categories_window(chat_id, text, reply_markup=kb, preferred_message_id=call.message.message_id, marker_action='cat_range_records:*')
            try:
                bot.answer_callback_query(call.id, f'Перенесено записей: {changed}', show_alert=False)
            except Exception:
                pass
        except Exception as e:
            log_error(f'cat_other_sort_target: {e}')
        return True
    if data_str.startswith('cat_show_records:'):
        try:
            _, start_key, start_rid, end_key, end_rid, slug = data_str.split(':', 5)
            category = get_category_by_slug(slug, store)
            if not category:
                try:
                    bot.answer_callback_query(call.id, 'Статья не найдена', show_alert=False)
                except Exception:
                    pass
                return True
            text = build_category_record_detail_text(store, start_key, int(start_rid), end_key, int(end_rid), category)
            kb = build_category_record_detail_keyboard(start_key, int(start_rid), end_key, int(end_rid), category=category, store=store)
            send_or_edit_categories_window(chat_id, text, reply_markup=kb, preferred_message_id=call.message.message_id, marker_action='cat_show_records:*')
        except Exception as e:
            log_error(f'cat_show_records: {e}')
        return True
    if data_str.startswith('cat_pick_end:'):
        try:
            _, y, m, start_d = data_str.split(':')
            _send_category_pick_end(chat_id, call.message.message_id, int(y), int(m), int(start_d))
        except Exception as e:
            log_error(f'cat_pick_end: {e}')
        return True
    if data_str.startswith('cat_pick_set_end:'):
        try:
            _, y, m, start_d, end_d = data_str.split(':')
            _send_category_pick_end(chat_id, call.message.message_id, int(y), int(m), int(start_d), int(end_d))
        except Exception as e:
            log_error(f'cat_pick_set_end: {e}')
        return True
    if data_str.startswith('cat_pick_end2:'):
        try:
            _, start_key, y, m = data_str.split(':')
            _send_category_pick_end_any_month(chat_id, call.message.message_id, start_key, int(y), int(m))
        except Exception as e:
            log_error(f'cat_pick_end2: {e}')
        return True
    if data_str.startswith('cat_pick_set_end2:'):
        try:
            _, start_key, y, m, d = data_str.split(':')
            end_key = _date_key_from_ymd(int(y), int(m), int(d))
            _send_category_pick_end_any_month(chat_id, call.message.message_id, start_key, int(y), int(m), end_key)
        except Exception as e:
            log_error(f'cat_pick_set_end2: {e}')
        return True
    if data_str.startswith('cat_range_custom2:'):
        try:
            _, start, end = data_str.split(':', 2)
            if end < start:
                start, end = (end, start)
            label = f'{fmt_date_ddmmyy(start)} — {fmt_date_ddmmyy(end)}'
            text, _ = summarize_categories(store, start, end, label)
            kb = build_categories_summary_keyboard('rng', start, end, store=store)
            send_or_edit_categories_window(chat_id, text, reply_markup=kb, preferred_message_id=call.message.message_id)
        except Exception as e:
            log_error(f'cat_range_custom2: {e}')
        return True
    if data_str.startswith('cat_range_custom:'):
        try:
            _, y, m, a, b = data_str.split(':')
            y, m, a, b = map(int, (y, m, a, b))
            last_day = calendar.monthrange(y, m)[1]
            a = max(1, min(a, last_day))
            b = max(1, min(b, last_day))
            if b < a:
                a, b = (b, a)
            start = f'{y}-{m:02d}-{a:02d}'
            end = f'{y}-{m:02d}-{b:02d}'
            label = f'{fmt_date_ddmmyy(start)} — {fmt_date_ddmmyy(end)}'
            text, _ = summarize_categories(store, start, end, label)
            kb = build_categories_summary_keyboard('rng', start, end, store=store)
            send_or_edit_categories_window(chat_id, text, reply_markup=kb, preferred_message_id=call.message.message_id)
        except Exception as e:
            log_error(f'cat_range_custom: {e}')
        return True
    if data_str.startswith('cat_rng:'):
        try:
            _, y, m, a, b = data_str.split(':')
            y, m, a, b = map(int, (y, m, a, b))
        except Exception:
            return True
        if m == 12:
            last_day = (datetime(y + 1, 1, 1) - timedelta(days=1)).day
        else:
            last_day = (datetime(y, m + 1, 1) - timedelta(days=1)).day
        a = max(1, min(a, last_day))
        b = max(1, min(b, last_day))
        if b < a:
            b = a
        start = f'{y}-{m:02d}-{a:02d}'
        end = f'{y}-{m:02d}-{b:02d}'
        label = f'{fmt_date_ddmmyy(start)} — {fmt_date_ddmmyy(end)}'
        text, _ = summarize_categories(store, start, end, label)
        kb = build_categories_summary_keyboard('rng', start, end, store=store)
        send_or_edit_categories_window(chat_id, text, reply_markup=kb, preferred_message_id=call.message.message_id)
        return True
    if data_str.startswith('cat_show_wthu:'):
        _, ref, slug = data_str.split(':', 2)
        category = get_category_by_slug(slug, store)
        if not category:
            return True
        start_key = week_start_thursday(ref or today_key())
        start, end = week_bounds_thu_wed(start_key)
        label = f'{fmt_date_ddmmyy(start)} — {fmt_date_ddmmyy(end)} (Чт–Ср)'
        text = build_category_detail_text(store, start, end, category, label)
        kb = build_category_detail_keyboard(start, end, f'cat_wthu:{start}', mode='wthu', slug=slug, store=store)
        send_or_edit_categories_window(chat_id, text, reply_markup=kb, preferred_message_id=call.message.message_id)
        return True
    if data_str.startswith('cat_show_wk:'):
        _, ref, slug = data_str.split(':', 2)
        category = get_category_by_slug(slug, store)
        if not category:
            return True
        start_key = week_start_monday(ref or today_key())
        start, end = week_bounds_from_start(start_key)
        label = f'{fmt_date_ddmmyy(start)} — {fmt_date_ddmmyy(end)} (Пн–Вс)'
        text = build_category_detail_text(store, start, end, category, label)
        kb = build_category_detail_keyboard(start, end, f'cat_wk:{start}', mode='wk', slug=slug, store=store)
        send_or_edit_categories_window(chat_id, text, reply_markup=kb, preferred_message_id=call.message.message_id)
        return True
    if data_str.startswith('cat_show:'):
        _, start, end, slug = data_str.split(':', 3)
        category = get_category_by_slug(slug, store)
        if not category:
            return True
        start_dt = datetime.strptime(start, '%Y-%m-%d')
        end_dt = datetime.strptime(end, '%Y-%m-%d')
        label = f'{fmt_date_ddmmyy(start)} — {fmt_date_ddmmyy(end)}'
        if (end_dt - start_dt).days == 6 and start == week_start_thursday(start):
            back_callback = f'cat_wthu:{start}'
            label += ' (Чт–Ср)'
        elif (end_dt - start_dt).days == 6 and start == week_start_monday(start):
            back_callback = f'cat_wk:{start}'
            label += ' (Пн–Вс)'
        elif start_dt.year != end_dt.year or start_dt.month != end_dt.month:
            back_callback = f'cat_range_custom2:{start}:{end}'
        else:
            y, m = (start_dt.year, start_dt.month)
            back_callback = f'cat_rng:{y}:{m}:{start_dt.day}:{end_dt.day}'
        mode = None
        if (end_dt - start_dt).days == 6 and start == week_start_thursday(start):
            mode = 'wthu'
        elif (end_dt - start_dt).days == 6 and start == week_start_monday(start):
            mode = 'wk'
        text = build_category_detail_text(store, start, end, category, label)
        kb = build_category_detail_keyboard(start, end, back_callback, mode=mode, slug=slug, store=store)
        send_or_edit_categories_window(chat_id, text, reply_markup=kb, preferred_message_id=call.message.message_id)
        return True
    return False
_callback_debounce_state = {}

def _v177_legacy_0223_callback_should_debounce(call, data_str: str, min_interval: float=0.12) -> bool:
    """Защита от частых кликов: Telegram уже получил answer_callback_query, поэтому «Загрузка» не висит."""
    try:
        chat_id = int(call.message.chat.id)
        msg_id = int(call.message.message_id)
        data_str = str(data_str or '')
        if data_str == 'none':
            return True
        hot = False
        if data_str.startswith('d:'):
            parts = data_str.split(':', 2)
            action = parts[2] if len(parts) > 2 else ''
            hot = action in {'prev', 'next', 'today', 'open', 'back_main', 'calendar', 'csv_all'}
        elif data_str.startswith('fv:') or data_str.startswith('c:') or data_str.startswith('fc:'):
            hot = True
        elif data_str.startswith(('secday:', 'secview:', 'secchatcal:', 'secmon:', 'secmonthlist:')):
            hot = True
        if not hot:
            return False
        key = (chat_id, msg_id, data_str.split(':', 1)[0], data_str.split(':')[-1])
        now_ts = time.time()
        prev_ts = _callback_debounce_state.get(key, 0)
        _callback_debounce_state[key] = now_ts
        skipped = now_ts - prev_ts < float(min_interval)
        if skipped:
            try:
                bot_journal('button_debounced', chat_id, data_str)
            except Exception:
                pass
        return skipped
    except Exception:
        return False
try:
    _v177_legacy_0223_callback_should_debounce.__name__ = '_callback_should_debounce'
except Exception:
    pass
_secret_edit_refresh_lock = threading.RLock()
_secret_edit_refresh_timers = {}

def schedule_secret_edit_refresh_window(viewer_chat_id: int, message_id: int, target_chat_id: int, day_key: str, self_only: bool=False, delay: float=0.7):
    key = (int(viewer_chat_id), int(message_id))
    generation = time.time_ns()
    scheduler_key = f'secret-edit-refresh:{key[0]}:{key[1]}'

    def _job():
        try:
            with _secret_edit_refresh_lock:
                if _secret_edit_refresh_timers.get(key) != generation:
                    return
            text = build_secret_edit_text(int(target_chat_id), day_key)
            kb = build_secret_edit_keyboard(int(viewer_chat_id), int(target_chat_id), day_key, self_only=bool(self_only))
            try:
                fast_ui_edit_message_text(int(viewer_chat_id), int(message_id), text, reply_markup=kb, purpose='secret_edit_debounce')
            except Exception as e:
                if not is_telegram_429(e) and 'message is not modified' not in str(e).lower():
                    log_error(f'secret edit debounce refresh {viewer_chat_id}:{message_id}: {e}')
            register_secret_window(int(viewer_chat_id), int(message_id), int(target_chat_id), 'edit', day_key=day_key, self_only=bool(self_only))
            schedule_secret_calendar_close(int(viewer_chat_id), int(message_id))
        finally:
            with _secret_edit_refresh_lock:
                if _secret_edit_refresh_timers.get(key) == generation:
                    _secret_edit_refresh_timers.pop(key, None)
    with _secret_edit_refresh_lock:
        DELAYED_SCHEDULER.cancel(scheduler_key)
        _secret_edit_refresh_timers[key] = generation
        DELAYED_SCHEDULER.schedule(scheduler_key, float(delay), _job)
_CALLBACK_ACK_LOCK = threading.RLock()
_CALLBACK_ACK_STATE = {}
_CALLBACK_ACK_TTL_SECONDS = 180.0
try:
    CALLBACK_RECEIPT_ACK_DELAY_SECONDS = max(0.03, min(0.10, float(os.getenv('CALLBACK_RECEIPT_ACK_DELAY_SECONDS', '0.06') or '0.06')))
except Exception:
    CALLBACK_RECEIPT_ACK_DELAY_SECONDS = 0.06
_NATIVE_BOT_ANSWER_CALLBACK_QUERY = telebot.TeleBot.answer_callback_query
_R25_CALLBACK_TRACE_LOCK = threading.RLock()
_R25_CALLBACK_TRACE_MAP = {}

def r25_register_callback_update(callback_id: str, update_id=None, chat_id=None, action=''):
    callback_id = str(callback_id or '')
    if not callback_id:
        return
    with _R25_CALLBACK_TRACE_LOCK:
        _R25_CALLBACK_TRACE_MAP[callback_id] = {'update_id': str(update_id or ''), 'chat_id': chat_id, 'action': str(action or '')[:180], 'ts': time.time()}
        now = time.time()
        for key, row in list(_R25_CALLBACK_TRACE_MAP.items()):
            if now - float((row or {}).get('ts') or now) > 300:
                _R25_CALLBACK_TRACE_MAP.pop(key, None)

def _r25_callback_trace_row(callback_id: str):
    with _R25_CALLBACK_TRACE_LOCK:
        return dict(_R25_CALLBACK_TRACE_MAP.get(str(callback_id or '')) or {})

def _callback_ack_prune_locked(now_ts=None):
    now_ts = float(now_ts or time.time())
    for key, row in list(_CALLBACK_ACK_STATE.items()):
        if now_ts - float((row or {}).get('ts', now_ts)) > _CALLBACK_ACK_TTL_SECONDS:
            _CALLBACK_ACK_STATE.pop(key, None)

def _late_callback_notice(chat_id, text):
    try:
        if chat_id is not None and str(text or '').strip():
            send_and_auto_delete(int(chat_id), f'ℹ️ {str(text).strip()}', 8)
    except Exception:
        pass

def _tracked_answer_callback_query(callback_query_id, *args, **kwargs):
    callback_id = str(callback_query_id or '')
    text = kwargs.get('text')
    if text is None and args:
        text = args[0]
    with _CALLBACK_ACK_LOCK:
        _callback_ack_prune_locked()
        row = _CALLBACK_ACK_STATE.setdefault(callback_id, {'ts': time.time()})
        row['ts'] = time.time()
        # R18: an empty ACK must stay empty.  R17 converted every silent receipt ACK
        # into the visible Telegram toast "⏳ Выполняю…", which made navigation feel
        # delayed even when the actual window render was fast.  Long jobs must request
        # an explicit progress text themselves.
        if row.get('answered'):
            # R18: the receipt ACK wins immediately.  A later ordinary toast from a
            # handler must not create a new Telegram message (R17 could turn every
            # navigation click into extra chat noise).  Preserve only explicit alert
            # semantics, which are normally permission/error messages.
            chat_id = row.get('chat_id')
            if bool(kwargs.get('show_alert')) and str(text or '').strip() and (not row.get('late_notice_sent')):
                row['late_notice_sent'] = True
                # Keep the dedicated ACK pool pure: late permission/error feedback is
                # ordinary background Telegram work and must never queue ahead of ACKs.
                _late_pool = globals().get('GENERAL_TASK_POOL')
                if _late_pool is not None:
                    _late_pool.submit_unique(f'callback-late-alert:{callback_id}', _late_callback_notice, chat_id, text)
                else:
                    threading.Thread(target=_late_callback_notice, args=(chat_id, text), name=f'r18-late-alert-{callback_id}', daemon=True).start()
            return True
        if row.get('inflight'):
            return True
        row['inflight'] = True
    try:
        _r25_ack_row = _r25_callback_trace_row(callback_id)
        _r25_ack_started = time.monotonic()
        try: log_info(f'BTNTRACE update={_r25_ack_row.get("update_id") or "-"} chat={_r25_ack_row.get("chat_id")} action={str(_r25_ack_row.get("action") or "")[:180]} stage=ACK_START')
        except Exception: pass
        result = _NATIVE_BOT_ANSWER_CALLBACK_QUERY(bot, callback_query_id, *args, **kwargs)
        try: log_info(f'BTNTRACE update={_r25_ack_row.get("update_id") or "-"} chat={_r25_ack_row.get("chat_id")} action={str(_r25_ack_row.get("action") or "")[:180]} stage=ACK_DONE elapsed={time.monotonic()-_r25_ack_started:.3f}s')
        except Exception: pass
        with _CALLBACK_ACK_LOCK:
            row = _CALLBACK_ACK_STATE.setdefault(callback_id, {})
            row.update({'answered': True, 'inflight': False, 'ts': time.time()})
        try:
            CALLBACK_ACK_SCHEDULER.cancel(f'callback-receipt-ack:{callback_id}')
        except Exception:
            pass
        return result
    except Exception:
        with _CALLBACK_ACK_LOCK:
            row = _CALLBACK_ACK_STATE.setdefault(callback_id, {})
            row['inflight'] = False
            row['ts'] = time.time()
        raise
# FINALIZED: callback ACK is bound once in 89_callback_final.py.

def _answer_callback_query_quiet(callback_id: str, chat_id=None):
    try:
        bot.answer_callback_query(callback_id, show_alert=False)
    except Exception:
        pass

def answer_callback_query_background(callback_id: str):
    """Immediate ACK from a callback handler, isolated from GENERAL/MEGA work."""
    key = f'callback-ack:{callback_id}'
    if not CALLBACK_ACK_TASK_POOL.submit_unique(key, _answer_callback_query_quiet, callback_id, None):
        try:
            bot_journal('callback_ack_coalesced', None, str(callback_id))
        except Exception:
            pass

def _v177_legacy_0224_schedule_callback_receipt_ack(callback_id: str, chat_id=None, delay: float | None=None):
    """Fallback ACK scheduled as soon as Flask receives callback_query."""
    callback_id = str(callback_id or '')
    if not callback_id:
        return
    with _CALLBACK_ACK_LOCK:
        _callback_ack_prune_locked()
        row = _CALLBACK_ACK_STATE.setdefault(callback_id, {})
        row['chat_id'] = int(chat_id) if chat_id is not None else row.get('chat_id')
        row['ts'] = time.time()
        if row.get('answered'):
            return
    CALLBACK_ACK_SCHEDULER.schedule(f'callback-receipt-ack:{callback_id}', CALLBACK_RECEIPT_ACK_DELAY_SECONDS if delay is None else max(0.05, float(delay)), _answer_callback_query_quiet, callback_id, chat_id)
try:
    _v177_legacy_0224_schedule_callback_receipt_ack.__name__ = 'schedule_callback_receipt_ack'
except Exception:
    pass

def build_process_center_keyboard(chat_id: int):
    kb = types.InlineKeyboardMarkup(row_width=2)
    kb.row(IB('🔄 Обновить', callback_data='process_center'))
    if is_owner_chat(chat_id):
        kb.row(IB('🧯 Проблемные задачи', callback_data='problem_tasks'))
    day = get_chat_store(chat_id).get('current_view_day') or today_key()
    kb.row(IB('🔙 Назад в Инфо', callback_data=f'd:{day}:info'), IB('❌ Закрыть', callback_data='info_close'))
    return kb

def build_problem_tasks_keyboard(chat_id: int):
    kb = types.InlineKeyboardMarkup(row_width=1)
    kb.row(IB('🔄 Обновить', callback_data='problem_tasks'))
    day = get_chat_store(chat_id).get('current_view_day') or today_key()
    kb.row(IB('🔙 Назад в Инфо', callback_data=f'd:{day}:info'))
    kb.row(IB('❌ Закрыть', callback_data='info_close'))
    return kb

def _v177_legacy_0225_build_safety_profile_keyboard(chat_id: int):
    kb = types.InlineKeyboardMarkup(row_width=1)
    kb.row(IB(safety_profile_label(), callback_data='safety_profile_toggle'))
    kb.row(IB('👥 Права пользователей', callback_data='security_roles:0'))
    day = get_chat_store(chat_id).get('current_view_day') or today_key()
    kb.row(IB('🔙 Назад в Инфо', callback_data=f'd:{day}:info'))
    return kb
try:
    _v177_legacy_0225_build_safety_profile_keyboard.__name__ = 'build_safety_profile_keyboard'
except Exception:
    pass

def build_security_roles_text(page: int=0) -> str:
    rows = security_known_users()
    page_size = 10
    pages = max(1, (len(rows) + page_size - 1) // page_size)
    page = max(0, min(int(page or 0), pages - 1))
    return f'👥 ПРАВА ПОЛЬЗОВАТЕЛЕЙ\n\nРаботают только когда профиль защиты включён «ПО-НОВОМУ».\nОбычный — прежние разрешения. Ограниченные роли запрещают лишние действия.\n\nПользователей: {len(rows)}\nСтраница: {page + 1}/{pages}'

def build_security_roles_keyboard(page: int=0):
    rows = security_known_users()
    page_size = 10
    pages = max(1, (len(rows) + page_size - 1) // page_size)
    page = max(0, min(int(page or 0), pages - 1))
    kb = types.InlineKeyboardMarkup(row_width=1)
    start = page * page_size
    for row in rows[start:start + page_size]:
        uid = int(row.get('id') or 0)
        name = security_user_display(uid)
        if len(name) > 22:
            name = name[:21] + '…'
        kb.row(IB(f'{name} · {security_role_label(security_role_for_user(uid))}', callback_data=f'security_role_user:{uid}:{page}'))
    if pages > 1:
        nav = []
        if page > 0:
            nav.append(IB('⬅️', callback_data=f'security_roles:{page - 1}'))
        nav.append(IB(f'{page + 1}/{pages}', callback_data='none'))
        if page + 1 < pages:
            nav.append(IB('➡️', callback_data=f'security_roles:{page + 1}'))
        kb.row(*nav)
    kb.row(IB('⬅️ Назад', callback_data='safety_profile_open'))
    return kb

def build_security_role_user_text(user_id: int) -> str:
    uid = int(user_id)
    role = security_role_for_user(uid)
    return f'👤 ПРАВА ПОЛЬЗОВАТЕЛЯ\n\nИмя: {security_user_display(uid)}\nID: {uid}\nРоль: {security_role_label(role)}\n\nВыберите один понятный профиль. Владелец всегда имеет полный доступ.'

def build_security_role_user_keyboard(user_id: int, page: int=0):
    uid = int(user_id)
    kb = types.InlineKeyboardMarkup(row_width=1)
    for role in ('standard', 'view_only', 'expense_input', 'finance_admin', 'forward_manager', 'secret_manager', 'reminder_manager'):
        mark = '✅ ' if security_role_for_user(uid) == role else '▫️ '
        kb.row(IB(mark + security_role_label(role), callback_data=f'security_role_set:{uid}:{role}:{int(page)}'))
    kb.row(IB('⬅️ К пользователям', callback_data=f'security_roles:{int(page)}'))
    return kb

def build_integrity_keyboard(chat_id: int):
    kb = types.InlineKeyboardMarkup(row_width=1)
    kb.row(IB('🔍 Проверить заново', callback_data='integrity_status'))
    day = get_chat_store(chat_id).get('current_view_day') or today_key()
    kb.row(IB('🔙 Назад в Инфо', callback_data=f'd:{day}:info'))
    return kb

# v262
