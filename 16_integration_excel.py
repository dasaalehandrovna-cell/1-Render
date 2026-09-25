# v266
"""ОЧНИСЬ 12.35 · physical owner: excel.

Этот файл — единственное физическое место тел функций домена.
Он НЕ запускается отдельно и НЕ импортируется как Python-модуль.
bot.py читает его как каталог исходников и устанавливает нужную стадию в исторической точке runtime.
Последняя версия каждого публичного символа сохраняет обычное имя; старые стадии помечены _legacy_sXXXX_.
"""

# --- excel:0001 · from 01_core_data.py:6724 · public _v177_legacy_0026_backup_excel_all_enabled ---
def _v177_legacy_0026_backup_excel_all_enabled() -> bool:
    try:
        return bool((data or {}).setdefault('_global_settings', {}).get('backup_excel_all_enabled', True))
    except Exception:
        return True

# --- excel:0002 · from 01_core_data.py:6734 · public _v177_legacy_0027_set_backup_excel_all_enabled ---
def _v177_legacy_0027_set_backup_excel_all_enabled(enabled: bool):
    data.setdefault('_global_settings', {})['backup_excel_all_enabled'] = bool(enabled)
    save_data(data, full=True)

# --- excel:0003 · from 01_core_data.py:6742 · public toggle_backup_excel_all_enabled ---
def toggle_backup_excel_all_enabled() -> bool:
    new_value = not backup_excel_all_enabled()
    set_backup_excel_all_enabled(new_value)
    return new_value

# --- excel:0004 · from 01_core_data.py:6747 · public backup_excel_all_label ---
def backup_excel_all_label() -> str:
    return '✅ ВКЛ' if backup_excel_all_enabled() else '⬜ ВЫКЛ'

# --- excel:0005 · from 01_core_data.py:6750 · public _normalize_excel_table_style ---
def _normalize_excel_table_style(value) -> str:
    raw = str(value or '').strip().lower()
    aliases = {'new': 'new_notes', 'notes': 'new_notes', 'note': 'new_notes', 'comments': 'new_comments', 'comment': 'new_comments', 'plain': 'new_plain', 'new_plain': 'new_plain', 'google': 'google_notes', 'sheets': 'google_notes', 'google_sheets': 'google_notes', 'google_notes': 'google_notes'}
    mode = aliases.get(raw, raw)
    return mode if mode in {'old', 'new_plain', 'new_comments', 'new_notes', 'google_notes'} else ''

# --- excel:0006 · from 01_core_data.py:6756 · public _v177_legacy_0028_excel_interface_mode ---
def _v177_legacy_0028_excel_interface_mode(chat_id: int | None=None) -> str:
    """INFO switch: old interface (v136 chooser) or new checkbox recipe."""
    gs = data.setdefault('_global_settings', {})
    mode = str(gs.get('excel_interface_mode') or 'old').strip().lower()
    if mode not in {'old', 'new'}:
        mode = 'old'
        gs['excel_interface_mode'] = mode
    return mode

# --- excel:0007 · from 01_core_data.py:6769 · public _v177_legacy_0029_set_excel_interface_mode ---
def _v177_legacy_0029_set_excel_interface_mode(mode: str) -> str:
    mode = 'new' if str(mode or '').strip().lower() == 'new' else 'old'
    data.setdefault('_global_settings', {})['excel_interface_mode'] = mode
    save_data(data, root_only=True)
    try:
        if OWNER_ID:
            schedule_config_backup_for_chats(int(OWNER_ID), delay=1.0)
    except Exception:
        pass
    return mode

# --- excel:0008 · from 01_core_data.py:6784 · public toggle_excel_interface_mode ---
def toggle_excel_interface_mode(chat_id: int | None=None) -> str:
    return set_excel_interface_mode('new' if excel_interface_mode(chat_id) == 'old' else 'old')

# --- excel:0009 · from 01_core_data.py:6787 · public _v177_legacy_0030_excel_new_export_options ---
def _v177_legacy_0030_excel_new_export_options() -> dict:
    gs = data.setdefault('_global_settings', {})
    raw = gs.get('excel_new_export_options')
    if not isinstance(raw, dict):
        raw = {}
    options = {'old_table': bool(raw.get('old_table', False)), 'comments': bool(raw.get('comments', False)), 'notes': bool(raw.get('notes', True)), 'description_column': bool(raw.get('description_column', False))}
    if options['old_table']:
        options.update({'comments': False, 'notes': False, 'description_column': True})
    elif options['comments'] and options['notes']:
        options['comments'] = False
    gs['excel_new_export_options'] = dict(options)
    return options

# --- excel:0010 · from 01_core_data.py:6804 · public _v177_legacy_0031_toggle_excel_new_export_option ---
def _v177_legacy_0031_toggle_excel_new_export_option(option: str) -> dict:
    option = str(option or '').strip().lower()
    options = excel_new_export_options()
    if option == 'old_table':
        enabled = not options['old_table']
        options['old_table'] = enabled
        if enabled:
            options.update({'comments': False, 'notes': False, 'description_column': True})
    elif option == 'comments':
        enabled = not options['comments']
        options.update({'old_table': False, 'comments': enabled})
        if enabled:
            options['notes'] = False
    elif option == 'notes':
        enabled = not options['notes']
        options.update({'old_table': False, 'notes': enabled})
        if enabled:
            options['comments'] = False
    elif option == 'description_column':
        enabled = not options['description_column']
        options['description_column'] = enabled
        if not enabled:
            options['old_table'] = False
    data.setdefault('_global_settings', {})['excel_new_export_options'] = dict(options)
    save_data(data, root_only=True)
    try:
        if OWNER_ID:
            schedule_config_backup_for_chats(int(OWNER_ID), delay=1.0)
    except Exception:
        pass
    return dict(options)

# --- excel:0011 · from 01_core_data.py:6840 · public normalize_excel_export_options ---
def normalize_excel_export_options(value: dict | None=None) -> dict:
    src = dict(value or excel_new_export_options())
    out = {'old_table': bool(src.get('old_table', False)), 'comments': bool(src.get('comments', False)), 'notes': bool(src.get('notes', False)), 'description_column': bool(src.get('description_column', False))}
    if out['old_table']:
        out.update({'comments': False, 'notes': False, 'description_column': True})
    elif out['comments'] and out['notes']:
        out['comments'] = False
    return out

# --- excel:0012 · from 01_core_data.py:6849 · public excel_export_options_style ---
def excel_export_options_style(options: dict | None=None) -> str:
    opts = normalize_excel_export_options(options)
    if opts['old_table']:
        return 'old'
    if opts['comments']:
        return 'new_comments'
    if opts['notes']:
        return 'new_notes'
    return 'new_plain'

# --- excel:0013 · from 01_core_data.py:6859 · public _v177_legacy_0032_excel_table_style ---
def _v177_legacy_0032_excel_table_style(chat_id: int) -> str:
    gs = data.setdefault('_global_settings', {})
    mode = _normalize_excel_table_style(gs.get('excel_table_style_global'))
    if not mode:
        candidates = [gs.get('excel_table_style')]
        try:
            if OWNER_ID:
                candidates.append(get_chat_store(int(OWNER_ID)).setdefault('settings', {}).get('excel_table_style'))
        except Exception:
            pass
        try:
            candidates.append(get_chat_store(int(chat_id)).setdefault('settings', {}).get('excel_table_style'))
        except Exception:
            pass
        mode = next((_normalize_excel_table_style(v) for v in candidates if _normalize_excel_table_style(v)), 'new_notes')
        gs['excel_table_style_global'] = mode
        gs['excel_table_style'] = mode
    return mode

# --- excel:0014 · from 01_core_data.py:6882 · public _v177_legacy_0033_set_excel_table_style ---
def _v177_legacy_0033_set_excel_table_style(chat_id: int, mode: str) -> str:
    chat_id = int(chat_id)
    mode = _normalize_excel_table_style(mode) or 'new_notes'
    gs = data.setdefault('_global_settings', {})
    gs['excel_table_style_global'] = mode
    gs['excel_table_style'] = mode
    touched = []
    for cid in (chat_id, int(OWNER_ID or 0)):
        if not cid or cid in touched:
            continue
        try:
            get_chat_store(cid).setdefault('settings', {})['excel_table_style'] = mode
            touched.append(cid)
        except Exception:
            pass
    save_data(data, chat_ids=touched or None, root_only=not bool(touched))
    try:
        schedule_config_backup_for_chats(*(touched or [chat_id]), delay=1.0)
    except Exception:
        pass
    return mode

# --- excel:0015 · from 01_core_data.py:6908 · public toggle_excel_table_style ---
def toggle_excel_table_style(chat_id: int) -> str:
    order = ['old', 'new_comments', 'new_notes', 'google_notes']
    current = excel_table_style(chat_id)
    try:
        next_mode = order[(order.index(current) + 1) % len(order)]
    except Exception:
        next_mode = 'new_notes'
    return set_excel_table_style(chat_id, next_mode)

# --- excel:0016 · from 01_core_data.py:6917 · public excel_table_style_caption ---
def excel_table_style_caption(chat_id: int) -> str:
    if excel_interface_mode(chat_id) == 'new':
        return 'ПО-НОВОМУ'
    return 'ПО-СТАРОМУ'

# --- excel:0017 · from 01_core_data.py:6922 · public excel_annotation_mode ---
def excel_annotation_mode(chat_id: int) -> str | None:
    mode = excel_table_style(chat_id)
    if mode == 'new_comments':
        return 'comments'
    if mode in {'new_notes', 'google_notes'}:
        return 'notes'
    return None

# --- excel:0018 · from 01_core_data.py:6930 · public excel_table_style_label ---
def excel_table_style_label(chat_id: int) -> str:
    return '📊 Excel: по новому' if excel_interface_mode(chat_id) == 'new' else '📊 Excel: по старому'

# --- excel:0019 · from 01_core_data.py:6933 · public build_excel_style_text ---
def build_excel_style_text(chat_id: int) -> str:
    return wm_owner(f'📊 Excel\\n\\nКнопка в INFO теперь только переключает интерфейс экспорта.\\n• По старому — меню выбора формата v136.\\n• По новому — настройки с галочками в Ф179/Ф181.\\n\\nСейчас: {excel_table_style_caption(chat_id)}', 9)

# --- excel:0020 · from 01_core_data.py:6936 · public build_excel_style_keyboard ---
def build_excel_style_keyboard(chat_id: int):
    kb = types.InlineKeyboardMarkup(row_width=1)
    kb.row(IB(excel_table_style_label(chat_id), callback_data='excel_style_toggle'))
    kb.row(IB('🔙 Назад в Инфо', callback_data='journal_back'))
    return kb

# --- excel:0021 · from 01_core_data.py:16597 · public chat_xlsx_file ---
def chat_xlsx_file(chat_id: int) -> str:
    return f'data_{chat_id}.xlsx'

# --- excel:0022 · from 01_core_data.py:16756 · public _xlsx_col_name ---
def _xlsx_col_name(n: int) -> str:
    """1 -> A, 27 -> AA."""
    out = ''
    n = int(n)
    while n > 0:
        n, rem = divmod(n - 1, 26)
        out = chr(65 + rem) + out
    return out or 'A'

# --- excel:0023 · from 01_core_data.py:16765 · public _xlsx_xml_escape ---
def _xlsx_xml_escape(value) -> str:
    text = '' if value is None else str(value)
    return text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('"', '&quot;').replace("'", '&apos;')

# --- excel:0024 · from 01_core_data.py:16769 · public _xlsx_cell_xml ---
def _xlsx_cell_xml(row_idx: int, col_idx: int, value, style: int | None=None) -> str:
    ref = f'{_xlsx_col_name(col_idx)}{row_idx}'
    s_attr = f' s="{int(style)}"' if style is not None else ''
    if isinstance(value, dict) and value.get('formula'):
        formula = _xlsx_xml_escape(str(value.get('formula') or '').lstrip('='))
        cached = value.get('value', 0)
        try:
            cached = float(cached)
            if cached.is_integer():
                cached = int(cached)
        except Exception:
            cached = 0
        return f'<c r="{ref}"{s_attr}><f>{formula}</f><v>{cached}</v></c>'
    if isinstance(value, (int, float)) and (not isinstance(value, bool)):
        return f'<c r="{ref}"{s_attr}><v>{value}</v></c>'
    return f'<c r="{ref}" t="inlineStr"{s_attr}><is><t>{_xlsx_xml_escape(value)}</t></is></c>'

# --- excel:0025 · from 01_core_data.py:16786 · public _v177_legacy_0089_write_simple_xlsx ---
def _v177_legacy_0089_write_simple_xlsx(path: str, rows: list[list], sheet_name: str='Данные') -> None:
    """Минимальный XLSX; sheet XML пишется потоково во временный файл."""
    rows = rows or [['date', 'amount', 'note']]
    workbook_xml = f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">\n<sheets><sheet name="{_xlsx_xml_escape(sheet_name)[:31]}" sheetId="1" r:id="rId1"/></sheets>\n<calcPr calcId="191029" fullCalcOnLoad="1" forceFullCalc="1"/>\n</workbook>'
    rels_xml = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">\n<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>\n</Relationships>'
    workbook_rels_xml = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">\n<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>\n<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>\n</Relationships>'
    content_types_xml = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">\n<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>\n<Default Extension="xml" ContentType="application/xml"/>\n<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>\n<Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>\n<Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>\n</Types>'
    styles_xml = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">\n<fonts count="2"><font><sz val="11"/><name val="Calibri"/></font><font><b/><sz val="11"/><name val="Calibri"/></font></fonts>\n<fills count="1"><fill><patternFill patternType="none"/></fill></fills>\n<borders count="1"><border><left/><right/><top/><bottom/><diagonal/></border></borders>\n<cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>\n<cellXfs count="2"><xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/><xf numFmtId="0" fontId="1" fillId="0" borderId="0" xfId="0" applyFont="1"/></cellXfs>\n<cellStyles count="1"><cellStyle name="Normal" xfId="0" builtinId="0"/></cellStyles>\n</styleSheet>'
    sheet_tmp = None
    try:
        fd, sheet_tmp = tempfile.mkstemp(prefix='xlsx_sheet_', suffix='.xml', dir=MEGA_LOCAL_TMP_DIR if os.path.isdir(MEGA_LOCAL_TMP_DIR) else None)
        os.close(fd)
        with open(sheet_tmp, 'w', encoding='utf-8', newline='') as sheet:
            sheet.write('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n')
            sheet.write('<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">\n')
            sheet.write('<sheetViews><sheetView workbookViewId="0"><pane ySplit="1" topLeftCell="A2" activePane="bottomLeft" state="frozen"/></sheetView></sheetViews>\n')
            sheet.write('<cols><col min="1" max="1" width="13" customWidth="1"/><col min="2" max="2" width="42" customWidth="1"/><col min="3" max="3" width="14" customWidth="1"/><col min="4" max="4" width="14" customWidth="1"/><col min="5" max="10" width="18" customWidth="1"/></cols>\n<sheetData>')
            for r_idx, row in enumerate(rows, start=1):
                sheet.write(f'<row r="{r_idx}">')
                for c_idx, value in enumerate(row, start=1):
                    sheet.write(_xlsx_cell_xml(r_idx, c_idx, value, style=1 if r_idx == 1 else None))
                sheet.write('</row>')
            sheet.write('</sheetData>\n</worksheet>')
        with zipfile.ZipFile(path, 'w', zipfile.ZIP_DEFLATED) as z:
            z.writestr('[Content_Types].xml', content_types_xml)
            z.writestr('_rels/.rels', rels_xml)
            z.writestr('xl/workbook.xml', workbook_xml)
            z.writestr('xl/_rels/workbook.xml.rels', workbook_rels_xml)
            z.write(sheet_tmp, 'xl/worksheets/sheet1.xml')
            z.writestr('xl/styles.xml', styles_xml)
    finally:
        try:
            if sheet_tmp and os.path.exists(sheet_tmp):
                os.remove(sheet_tmp)
        except Exception:
            pass

# --- excel:0026 · from 01_core_data.py:16827 · public _xlsx_income_expense_values ---
def _xlsx_income_expense_values(amount):
    """Возвращает (приход, расход) для Excel: сумма разбита по двум колонкам."""
    try:
        v = float(amount or 0)
    except Exception:
        v = 0.0
    if v >= 0:
        income = int(v) if float(v).is_integer() else v
        return (income, '')
    expense = abs(v)
    expense = int(expense) if float(expense).is_integer() else expense
    return ('', expense)

# --- excel:0027 · from 01_core_data.py:16840 · public _xlsx_record_row ---
def _xlsx_record_row(date_value, amount, note):
    income, expense = _xlsx_income_expense_values(amount)
    return [date_value, note or '', income, expense]

# --- excel:0028 · from 01_core_data.py:16886 · public _v177_legacy_0090_xlsx_simple_rows_with_balances ---
def _v177_legacy_0090_xlsx_simple_rows_with_balances(rows: list[list], opening_balance: float, target_chat_id: int | None=None) -> list[list]:
    """Add opening balance, period totals and real closing cash balance to 4-column XLSX."""
    src = [list(r or []) for r in rows or []]
    if not src:
        src = [['Дата', 'Описание', 'Приход', 'Расход']]
    header = src[0]
    body = src[1:]
    opening = float(opening_balance or 0.0)
    income_total = 0.0
    expense_total = 0.0
    for row in body:
        try:
            val = row[2] if len(row) > 2 else ''
            if _excel_nonempty(val) and (not isinstance(val, dict)):
                income_total += float(val)
        except Exception:
            pass
        try:
            val = row[3] if len(row) > 3 else ''
            if _excel_nonempty(val) and (not isinstance(val, dict)):
                expense_total += float(val)
        except Exception:
            pass
    out = [header, ['', 'Остаток с прошлого раза', opening, ''], []]
    data_start_row = 4
    out.extend(body)
    data_end_row = max(data_start_row, len(out))
    out.append([])
    income_row = len(out) + 1
    out.append(['', 'Приход за период', {'formula': f'SUM(C{data_start_row}:C{data_end_row})', 'value': income_total}, ''])
    expense_row = len(out) + 1
    out.append(['', 'Расход за период', '', {'formula': f'SUM(D{data_start_row}:D{data_end_row})', 'value': expense_total}])
    closing = opening + income_total - expense_total
    out.append(['', 'Остаток на руках', {'formula': f'C2+C{income_row}-D{expense_row}', 'value': closing}, ''])
    return out

# --- excel:0029 · from 01_core_data.py:16926 · public _v177_legacy_0093_compact_simple_excel_rows_and_annotations ---
def _v177_legacy_0093_compact_simple_excel_rows_and_annotations(raw_rows: list[tuple], opening_balance: float, target_chat_id: int | None=None) -> tuple[list[list], dict[tuple[int, int], str]]:
    """3-column Excel: Date / Income / Expense; description lives only in Comment/Note."""
    opening = float(opening_balance or 0.0)
    rows = [['Дата', 'Приход', 'Расход'], ['Остаток с прошлого раза', opening, ''], []]
    annotations: dict[tuple[int, int], str] = {}
    income_total = 0.0
    expense_total = 0.0
    prev_day = None
    for date_value, amount_value, note_value in raw_rows or []:
        if prev_day is not None and str(date_value) != str(prev_day):
            rows.append([])
        prev_day = date_value
        try:
            amount = parse_csv_amount(amount_value)
        except Exception:
            try:
                amount = float(amount_value or 0)
            except Exception:
                amount = 0.0
        income, expense = _xlsx_income_expense_values(amount)
        rows.append([date_value, income, expense])
        row_idx = len(rows)
        note = str(note_value or '').strip()
        if note:
            annotations[row_idx, 2 if _excel_nonempty(income) else 3] = note
        if amount >= 0:
            income_total += amount
        else:
            expense_total += abs(amount)
    data_start_row = 4
    data_end_row = max(data_start_row, len(rows))
    rows.append([])
    income_row = len(rows) + 1
    rows.append(['Приход за период', {'formula': f'SUM(B{data_start_row}:B{data_end_row})', 'value': income_total}, ''])
    expense_row = len(rows) + 1
    rows.append(['Расход за период', '', {'formula': f'SUM(C{data_start_row}:C{data_end_row})', 'value': expense_total}])
    closing = opening + income_total - expense_total
    rows.append(['Остаток на руках', {'formula': f'B2+B{income_row}-C{expense_row}', 'value': closing}, ''])
    return (rows, annotations)

# --- excel:0030 · from 01_core_data.py:16996 · public _tabl_lsx_category ---
def _tabl_lsx_category(note: str) -> str:
    text = str(note or '').casefold()
    checks = [('Еда доп и ШБ', ('шб', 'шамп', 'мыло', 'зуб', 'паста', 'гигиен')), ('Продукты', ('продукт', 'еда', 'хлеб', 'мол', 'фрукт', 'овощ', 'банан', 'лук', 'масло', 'йогурт', 'кофе', 'чай', 'курица', 'мясо')), ('Хоз общ', ('хоз', 'салф', 'порош', 'клей', 'краск', 'саморез', 'инструмент', 'батарей', 'розет', 'шнур', 'пульт', 'ключ')), ('Авто и (бус)', ('авто', 'бенз', 'соляр', 'заправ', 'машин', 'шина', 'масло авто', 'пикап', 'бус')), ('орг. техника', ('орг', 'двд', 'dvd', 'переходник', 'блок питание', 'провод', 'кабель', 'монитор', 'паяль', 'заряд', 'науш', 'мыш', 'принтер')), ('Связь', ('тел', 'связ', 'пополнение', 'сим', 'интернет')), ('переводы', ('перевод', 'вестерн', 'western', 'банковский', 'mercado', 'меркадо')), ('Проживание', ('прож', 'аренд', 'квар', 'отель', 'дом')), ('Хоз за ашр', ('ашр', 'ашрам')), ('аптечка', ('аптеч', 'аптек', 'лекар', 'ибуп', 'витамин', 'стоматолог'))]
    for name, words in checks:
        if any((w in text for w in words)):
            return name
    return 'прочие'

# --- excel:0031 · from 01_core_data.py:17004 · public _tabl_lsx_weeks ---
def _tabl_lsx_weeks(reference_day: str | None=None, count: int=4) -> list[tuple[str, str]]:
    ref = reference_day or today_key()
    start_key = week_start_thursday(ref)
    start = datetime.strptime(start_key, '%Y-%m-%d').date()
    weeks = []
    first = start - timedelta(days=7 * (int(count) - 1))
    for i in range(int(count)):
        s = first + timedelta(days=7 * i)
        e = s + timedelta(days=6)
        weeks.append((s.strftime('%Y-%m-%d'), e.strftime('%Y-%m-%d')))
    return weeks

# --- excel:0032 · from 01_core_data.py:17016 · public _tabl_lsx_opening_balance ---
def _tabl_lsx_opening_balance(store: dict, start_key: str, chat_id: int | None=None) -> float:
    helper = globals().get('_excel_canonical_opening_balance')
    if callable(helper) and chat_id is not None:
        return float(helper(int(chat_id), 'ars', str(start_key)[:10], 0, False))
    total = 0.0
    for r in store.get('records', []) or []:
        try:
            if _record_day_key(r) < start_key:
                total += float(r.get('amount', 0) or 0)
        except Exception:
            pass
    return float(total)

# --- excel:0033 · from 01_core_data.py:17029 · public _xlsx_cell_xml2 ---
def _xlsx_cell_xml2(row_idx: int, col_idx: int, value, style: int=0) -> str:
    if value is None:
        value = ''
    ref = f'{_xlsx_col_name(col_idx)}{row_idx}'
    s_attr = f' s="{int(style)}"' if int(style or 0) else ''
    if isinstance(value, dict) and value.get('formula'):
        formula = _xlsx_xml_escape(str(value.get('formula') or '').lstrip('='))
        cached = value.get('value', 0)
        try:
            cached = float(cached)
            cached = int(cached) if cached.is_integer() else cached
        except Exception:
            cached = 0
        return f'<c r="{ref}"{s_attr}><f>{formula}</f><v>{cached}</v></c>'
    if isinstance(value, (int, float)) and (not isinstance(value, bool)):
        return f'<c r="{ref}"{s_attr}><v>{float(value):.2f}</v></c>'
    text = str(value)
    return f'<c r="{ref}" t="inlineStr"{s_attr}><is><t>{_xlsx_xml_escape(text)}</t></is></c>'

# --- excel:0034 · from 01_core_data.py:17048 · public _v177_legacy_0098_write_tabl_lsx_xlsx ---
def _v177_legacy_0098_write_tabl_lsx_xlsx(path: str, rows: list[list], styles: list[list], sheet_name: str='4 недели', comments: dict | None=None, freeze_rows: int=3, widths: list[float] | None=None, annotation_mode: str | None='notes') -> None:
    """Minimal XLSX writer with two genuinely different annotation types.

    annotation_mode="notes"    -> classic Excel Notes (legacy comments XML + VML ObjectType=Note)
    annotation_mode="comments" -> modern threaded Excel Comments (threadedComments + person)
    annotation_mode=None        -> no annotations
    """
    comments = comments or {}
    annotation_mode = str(annotation_mode or '').strip().lower() or None
    if annotation_mode not in {None, 'notes', 'comments'}:
        annotation_mode = 'notes'
    if not comments:
        annotation_mode = None
    max_cols = max((len(r) for r in rows), default=1)
    widths = list(widths or [13, 16, 28] + [20] * max(0, max_cols - 3))
    if len(widths) < max_cols:
        widths.extend([18] * (max_cols - len(widths)))
    freeze_rows = max(0, int(freeze_rows or 0))
    cols_xml = ''.join((f'<col min="{i}" max="{i}" width="{min(widths[i - 1] if i - 1 < len(widths) else 18, 34)}" customWidth="1"/>' for i in range(1, max_cols + 1)))
    legacy_drawing = '<legacyDrawing r:id="rId2"/>' if annotation_mode == 'notes' else ''
    workbook_xml = f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">\n<sheets><sheet name="{_xlsx_xml_escape(sheet_name)[:31]}" sheetId="1" r:id="rId1"/></sheets>\n<calcPr calcId="191029" fullCalcOnLoad="1" forceFullCalc="1"/>\n</workbook>'
    rels_xml = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">\n<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>\n</Relationships>'
    person_rel = ''
    if annotation_mode == 'comments':
        person_rel = '\n<Relationship Id="rId3" Type="http://schemas.microsoft.com/office/2017/10/relationships/person" Target="persons/person.xml"/>'
    workbook_rels_xml = f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">\n<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>\n<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>{person_rel}\n</Relationships>'
    category_colors = ['FFC6EFCE', 'FFDDEBF7', 'FFFCE4D6', 'FFE4DFEC', 'FFFFF2CC', 'FFD9EAD3', 'FFCFE2F3', 'FFF4CCCC', 'FFD0E0E3', 'FFEAD1DC', 'FFD9D2E9']
    extra_fills = ''.join((f'<fill><patternFill patternType="solid"><fgColor rgb="{rgb}"/></patternFill></fill>' for rgb in category_colors))
    header_xfs = ''.join((f'<xf numFmtId="0" fontId="1" fillId="{7 + i}" borderId="1" xfId="0" applyFill="1" applyFont="1"/>' for i in range(len(category_colors))))
    data_xfs = ''.join((f'<xf numFmtId="0" fontId="0" fillId="{7 + i}" borderId="1" xfId="0" applyFill="1"/>' for i in range(len(category_colors))))
    styles_xml = f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">\n<fonts count="3"><font><sz val="10"/><name val="Calibri"/></font><font><b/><sz val="10"/><name val="Calibri"/></font><font><b/><sz val="14"/><name val="Calibri"/></font></fonts>\n<fills count="18"><fill><patternFill patternType="none"/></fill><fill><patternFill patternType="gray125"/></fill><fill><patternFill patternType="solid"><fgColor rgb="FF00E000"/></patternFill></fill><fill><patternFill patternType="solid"><fgColor rgb="FFFFC000"/></patternFill></fill><fill><patternFill patternType="solid"><fgColor rgb="FFFF9999"/></patternFill></fill><fill><patternFill patternType="solid"><fgColor rgb="FFE2F0D9"/></patternFill></fill><fill><patternFill patternType="solid"><fgColor rgb="FFD9EAD3"/></patternFill></fill>{extra_fills}</fills>\n<borders count="2"><border><left/><right/><top/><bottom/><diagonal/></border><border><left style="thin"/><right style="thin"/><top style="thin"/><bottom style="thin"/><diagonal/></border></borders>\n<cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>\n<cellXfs count="30"><xf numFmtId="0" fontId="0" fillId="0" borderId="1" xfId="0"/><xf numFmtId="0" fontId="2" fillId="0" borderId="0" xfId="0"/><xf numFmtId="0" fontId="1" fillId="2" borderId="1" xfId="0" applyFill="1" applyFont="1"/><xf numFmtId="0" fontId="1" fillId="3" borderId="1" xfId="0" applyFill="1" applyFont="1"/><xf numFmtId="0" fontId="0" fillId="0" borderId="1" xfId="0"/><xf numFmtId="0" fontId="1" fillId="4" borderId="1" xfId="0" applyFill="1" applyFont="1"/><xf numFmtId="0" fontId="1" fillId="5" borderId="1" xfId="0" applyFill="1" applyFont="1"/><xf numFmtId="0" fontId="1" fillId="6" borderId="1" xfId="0" applyFill="1" applyFont="1"/>{header_xfs}{data_xfs}</cellXfs>\n<cellStyles count="1"><cellStyle name="Normal" xfId="0" builtinId="0"/></cellStyles>\n</styleSheet>'
    content_types_extra = ''
    sheet_rels_xml = None
    notes_xml = None
    vml_xml = None
    threaded_xml = None
    persons_xml = None
    if annotation_mode == 'notes':
        content_types_extra = '<Default Extension="vml" ContentType="application/vnd.openxmlformats-officedocument.vmlDrawing"/>\n<Override PartName="/xl/comments1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.comments+xml"/>'
        comment_nodes = []
        shapes = []
        for idx, ((row_idx, col_idx), text) in enumerate(sorted(comments.items()), start=1):
            ref = f'{_xlsx_col_name(int(col_idx))}{int(row_idx)}'
            safe_text = _xlsx_xml_escape(str(text or ''))
            comment_nodes.append(f'<comment ref="{ref}" authorId="0"><text><t xml:space="preserve">{safe_text}</t></text></comment>')
            shapes.append(f'<v:shape id="_x0000_s{1024 + idx}" type="#_x0000_t202" style="position:absolute;margin-left:59.25pt;margin-top:1.5pt;width:144pt;height:79.5pt;z-index:{idx};visibility:hidden" fillcolor="#ffffe1" o:insetmode="auto">\n<v:fill color2="#ffffe1"/><v:shadow on="t" color="black" obscured="t"/><v:path o:connecttype="none"/><v:textbox style="mso-direction-alt:auto"><div style="text-align:left"/></v:textbox>\n<x:ClientData ObjectType="Note"><x:MoveWithCells/><x:SizeWithCells/><x:Anchor>{max(0, int(col_idx) - 1)}, 15, {max(0, int(row_idx) - 1)}, 2, {int(col_idx) + 2}, 15, {int(row_idx) + 4}, 4</x:Anchor><x:AutoFill>False</x:AutoFill><x:Row>{max(0, int(row_idx) - 1)}</x:Row><x:Column>{max(0, int(col_idx) - 1)}</x:Column></x:ClientData></v:shape>')
        notes_xml = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n<comments xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><authors><author></author></authors><commentList>{''.join(comment_nodes)}</commentList></comments>"""
        vml_xml = f"""<?xml version="1.0" encoding="UTF-8"?>\n<xml xmlns:v="urn:schemas-microsoft-com:vml" xmlns:o="urn:schemas-microsoft-com:office:office" xmlns:x="urn:schemas-microsoft-com:office:excel">\n<o:shapelayout v:ext="edit"><o:idmap v:ext="edit" data="1"/></o:shapelayout><v:shapetype id="_x0000_t202" coordsize="21600,21600" o:spt="202" path="m,l,21600r21600,l21600,xe"><v:stroke joinstyle="miter"/><v:path gradientshapeok="t" o:connecttype="rect"/></v:shapetype>{''.join(shapes)}</xml>"""
        sheet_rels_xml = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">\n<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/comments" Target="../comments1.xml"/>\n<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/vmlDrawing" Target="../drawings/vmlDrawing1.vml"/>\n</Relationships>'
    elif annotation_mode == 'comments':
        content_types_extra = '<Override PartName="/xl/threadedComments/threadedComment1.xml" ContentType="application/vnd.ms-excel.threadedcomments+xml"/>\n<Override PartName="/xl/persons/person.xml" ContentType="application/vnd.ms-excel.person+xml"/>'
        person_id = '{7C441D5B-9D3A-4B84-95C4-5BCE02D746A1}'
        comment_nodes = []
        comment_time = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')
        for row_idx, col_idx in sorted(comments.keys()):
            ref = f'{_xlsx_col_name(int(col_idx))}{int(row_idx)}'
            safe_text = _xlsx_xml_escape(str(comments[row_idx, col_idx] or ''))
            comment_nodes.append(f'<threadedComment ref="{ref}" dT="{comment_time}" personId="{person_id}"><text>{safe_text}</text></threadedComment>')
        threaded_xml = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n<ThreadedComments xmlns="http://schemas.microsoft.com/office/spreadsheetml/2018/threadedcomments">{''.join(comment_nodes)}</ThreadedComments>"""
        persons_xml = f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n<personList xmlns="http://schemas.microsoft.com/office/spreadsheetml/2018/person"><person displayName="Telegram Finance Bot" id="{person_id}" userId="telegram-finance-bot" providerId="None"/></personList>'
        sheet_rels_xml = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">\n<Relationship Id="rId1" Type="http://schemas.microsoft.com/office/2017/10/relationships/threadedComment" Target="../threadedComments/threadedComment1.xml"/>\n</Relationships>'
    content_types_xml = f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">\n<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>\n<Default Extension="xml" ContentType="application/xml"/>{content_types_extra}\n<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>\n<Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>\n<Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>\n</Types>'
    sheet_tmp = None
    try:
        temp_dir = MEGA_LOCAL_TMP_DIR if os.path.isdir(MEGA_LOCAL_TMP_DIR) else None
        fd, sheet_tmp = tempfile.mkstemp(prefix='xlsx_sheet_', suffix='.xml', dir=temp_dir)
        os.close(fd)
        with open(sheet_tmp, 'w', encoding='utf-8', newline='') as sheet:
            sheet.write('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n')
            sheet.write('<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">\n')
            pane = f'<pane ySplit="{freeze_rows}" topLeftCell="A{freeze_rows + 1}" activePane="bottomLeft" state="frozen"/>' if freeze_rows else ''
            sheet.write(f'<sheetViews><sheetView workbookViewId="0">{pane}</sheetView></sheetViews>\n')
            sheet.write(f'<cols>{cols_xml}</cols>\n<sheetData>')
            for r_idx, row in enumerate(rows, start=1):
                st_row = styles[r_idx - 1] if r_idx - 1 < len(styles) else []
                height = ' ht="22" customHeight="1"' if r_idx <= max(1, freeze_rows) else ''
                sheet.write(f'<row r="{r_idx}"{height}>')
                for c_idx in range(1, max_cols + 1):
                    value = row[c_idx - 1] if c_idx - 1 < len(row) else ''
                    style = st_row[c_idx - 1] if c_idx - 1 < len(st_row) else 0
                    sheet.write(_xlsx_cell_xml2(r_idx, c_idx, value, style=style))
                sheet.write('</row>')
            sheet.write(f'</sheetData>{legacy_drawing}\n</worksheet>')
        with zipfile.ZipFile(path, 'w', zipfile.ZIP_DEFLATED) as z:
            z.writestr('[Content_Types].xml', content_types_xml)
            z.writestr('_rels/.rels', rels_xml)
            z.writestr('xl/workbook.xml', workbook_xml)
            z.writestr('xl/_rels/workbook.xml.rels', workbook_rels_xml)
            z.write(sheet_tmp, 'xl/worksheets/sheet1.xml')
            z.writestr('xl/styles.xml', styles_xml)
            if sheet_rels_xml:
                z.writestr('xl/worksheets/_rels/sheet1.xml.rels', sheet_rels_xml)
            if annotation_mode == 'notes':
                z.writestr('xl/comments1.xml', notes_xml)
                z.writestr('xl/drawings/vmlDrawing1.vml', vml_xml)
            elif annotation_mode == 'comments':
                z.writestr('xl/threadedComments/threadedComment1.xml', threaded_xml)
                z.writestr('xl/persons/person.xml', persons_xml)
    finally:
        try:
            if sheet_tmp and os.path.exists(sheet_tmp):
                os.remove(sheet_tmp)
        except Exception:
            pass

# --- excel:0035 · from 01_core_data.py:17157 · public _validate_xlsx_annotation_package ---
def _validate_xlsx_annotation_package(path: str, annotation_mode: str | None) -> None:
    """Fail closed if Notes and Comments OOXML parts ever get mixed.

    Excel Notes are the legacy comments1.xml + VML note shapes. Modern Excel
    Comments are threadedComments + persons. In notes mode the threaded parts
    must be completely absent.
    """
    mode = str(annotation_mode or '').strip().lower() or None
    if mode not in {None, 'notes', 'comments'}:
        return
    with zipfile.ZipFile(path, 'r') as z:
        names = set(z.namelist())
        legacy_xml = z.read('xl/comments1.xml').decode('utf-8', 'replace') if 'xl/comments1.xml' in names else ''
        vml_text = z.read('xl/drawings/vmlDrawing1.vml').decode('utf-8', 'replace') if 'xl/drawings/vmlDrawing1.vml' in names else ''
    has_legacy_notes = 'xl/comments1.xml' in names and 'xl/drawings/vmlDrawing1.vml' in names
    has_threaded_comments = 'xl/threadedComments/threadedComment1.xml' in names or 'xl/persons/person.xml' in names
    if mode == 'notes':
        if has_threaded_comments:
            raise RuntimeError('XLSX notes mode contains threaded Comments parts')
        if has_legacy_notes:
            if 'ObjectType="Note"' not in vml_text:
                raise RuntimeError('XLSX notes VML does not declare ObjectType=Note')
            if 'Telegram Finance Bot' in legacy_xml:
                raise RuntimeError('XLSX notes mode must not carry a comment author')
            if '<comment ' in legacy_xml and (not re.search('<comment\\b[^>]*>.*?<t(?:\\s[^>]*)?>(?!\\s*</t>).*?</t>', legacy_xml, flags=re.S)):
                raise RuntimeError('XLSX notes mode contains empty note bodies')
    if mode == 'comments' and has_legacy_notes:
        raise RuntimeError('XLSX comments mode contains legacy Notes parts')

# --- excel:0036 · from 01_core_data.py:17186 · public _excel_nonempty ---
def _excel_nonempty(value) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    return True

# --- excel:0037 · from 01_core_data.py:17193 · public _excel_category_color_index ---
def _excel_category_color_index(note: str) -> int:
    try:
        category = _tabl_lsx_category(note)
        return TABL_LSX_CATEGORIES.index(category) if category in TABL_LSX_CATEGORIES else TABL_LSX_CATEGORIES.index('прочие')
    except Exception:
        return 0

# --- excel:0038 · from 01_core_data.py:17200 · public _v177_legacy_0099_modern_simple_excel_styles_comments ---
def _v177_legacy_0099_modern_simple_excel_styles_comments(rows: list[list]) -> tuple[list[list], dict, int, list[float]]:
    """Modern 4-column/backup Excel: colored amounts + annotations on expenses."""
    max_cols = max((len(r) for r in rows), default=4)
    styles = []
    comments = {}
    header_row = 1
    data_started = False
    for r_idx, row in enumerate(rows, start=1):
        row = list(row or [])
        normalized0 = str(row[0] if row else '').strip().casefold()
        normalized1 = str(row[1] if len(row) > 1 else '').strip().casefold()
        is_header = normalized0 in {'дата', 'date'} and normalized1 in {'описание', 'description', 'amount'}
        if is_header:
            header_row = r_idx
            data_started = True
            styles.append([2] * max_cols)
            continue
        st = [4] * max_cols if any((_excel_nonempty(v) for v in row)) else [0] * max_cols
        if not data_started:
            if r_idx == 1 and any((_excel_nonempty(v) for v in row)):
                st = [1] + [4] * max(0, max_cols - 1)
            styles.append(st)
            continue
        note = str(row[1] if len(row) > 1 else '').strip()
        note_key = note.casefold()
        if note_key in {'остаток с прошлого раза', 'остаток на руках'}:
            styles.append([6] * max_cols)
            continue
        if note_key in {'приход за период', 'расход за период'}:
            styles.append([5] * max_cols)
            continue
        income = row[2] if len(row) > 2 else ''
        expense = row[3] if len(row) > 3 else ''
        if _excel_nonempty(income) and len(st) > 2:
            st[2] = 7
        if _excel_nonempty(expense) and len(st) > 3:
            cat_idx = _excel_category_color_index(note)
            st[3] = 19 + cat_idx
            if note:
                comments[r_idx, 4] = note
        styles.append(st)
    widths = [13, 38, 15, 15] + [14] * max(0, max_cols - 4)
    return (styles, comments, header_row, widths)

# --- excel:0039 · from 01_core_data.py:17248 · public _v177_legacy_0100_modern_compact_excel_styles_comments ---
def _v177_legacy_0100_modern_compact_excel_styles_comments(rows: list[list], annotations: dict[tuple[int, int], str]) -> tuple[list[list], dict, int, list[float]]:
    """Modern 3-column Excel without Description column; annotations are on amount cells."""
    max_cols = max((len(r) for r in rows), default=3)
    styles = []
    for r_idx, row in enumerate(rows or [], start=1):
        row = list(row or [])
        first = str(row[0] if row else '').strip().casefold()
        is_header = first in {'дата', 'date'}
        if is_header:
            styles.append([2] * max_cols)
            continue
        if not any((_excel_nonempty(v) for v in row)):
            styles.append([0] * max_cols)
            continue
        if first in {'остаток с прошлого раза', 'остаток на руках'}:
            styles.append([6] * max_cols)
            continue
        if first in {'приход за период', 'расход за период'}:
            styles.append([5] * max_cols)
            continue
        st = [4] * max_cols
        if len(row) > 1 and _excel_nonempty(row[1]):
            st[1] = 7
        if len(row) > 2 and _excel_nonempty(row[2]):
            note = str((annotations or {}).get((r_idx, 3)) or '')
            st[2] = 19 + _excel_category_color_index(note)
        styles.append(st)
    return (styles, dict(annotations or {}), 1, [22, 16, 16])

# --- excel:0040 · from 01_core_data.py:17281 · public _v177_legacy_0101_modern_category_excel_styles_comments ---
def _v177_legacy_0101_modern_category_excel_styles_comments(rows: list[list]) -> tuple[list[list], dict, int, list[float]]:
    """Modern category/stat Excel: each expense column gets its own fill and annotation."""
    max_cols = max((len(r) for r in rows), default=4)
    styles = []
    comments = {}
    header_row = 1
    header_found = False
    for r_idx, row in enumerate(rows, start=1):
        row = list(row or [])
        first = str(row[0] if row else '').strip().casefold()
        second = str(row[1] if len(row) > 1 else '').strip().casefold()
        is_header = first in {'дата', 'date'} and second in {'описание', 'description', 'приход/выдача'}
        if is_header:
            header_row = r_idx
            header_found = True
            st = [2] * min(3, max_cols) + [8 + (c - 3) % len(TABL_LSX_CATEGORIES) for c in range(3, max_cols)]
            styles.append(st)
            continue
        if not any((_excel_nonempty(v) for v in row)):
            styles.append([0] * max_cols)
            continue
        label = second
        if label in {'сумма по статьям', 'расход'}:
            styles.append([5] * max_cols)
            continue
        if label in {'приход', 'остаток с прошлого раза', 'остаток на руках', 'на руках:'}:
            styles.append([6] * max_cols)
            continue
        st = [4] * max_cols
        note = str(row[1] if len(row) > 1 else '').strip()
        if header_found:
            if len(row) > 2 and _excel_nonempty(row[2]):
                st[2] = 7
            for c in range(3, max_cols):
                if c < len(row) and _excel_nonempty(row[c]):
                    st[c] = 19 + (c - 3) % len(TABL_LSX_CATEGORIES)
                    if note:
                        comments[r_idx, c + 1] = note
        styles.append(st)
    widths = [13, 36, 15] + [18] * max(0, max_cols - 3)
    return (styles, comments, header_row, widths)

# --- excel:0041 · from 01_core_data.py:17357 · public _v177_legacy_0104_category_excel_expected_annotations ---
def _v177_legacy_0104_category_excel_expected_annotations(rows: list[list]) -> dict[tuple[int, int], str]:
    """Return the exact expense cells that must carry an annotation in category Excel.

    This mirrors _modern_category_excel_styles_comments(). Summary / balance rows
    intentionally do not receive expense notes, even if they contain category totals.
    """
    expected: dict[tuple[int, int], str] = {}
    header_found = False
    skip_labels = {'сумма по статьям', 'расход', 'приход', 'остаток с прошлого раза', 'остаток на руках', 'на руках:'}
    for r_idx, row in enumerate(rows or [], start=1):
        row = list(row or [])
        first = str(row[0] if row else '').strip().casefold()
        second = str(row[1] if len(row) > 1 else '').strip().casefold()
        is_header = first in {'дата', 'date'} and second in {'описание', 'description', 'приход/выдача'}
        if is_header:
            header_found = True
            continue
        if not header_found or not any((_excel_nonempty(v) for v in row)):
            continue
        if second in skip_labels:
            continue
        note_text = str(row[1] if len(row) > 1 else '').strip()
        if not note_text:
            continue
        for c in range(3, len(row)):
            if _excel_nonempty(row[c]):
                expected[r_idx, c + 1] = note_text
    return expected

# --- excel:0042 · from 01_core_data.py:17390 · public _validate_xlsx_expected_notes ---
def _validate_xlsx_expected_notes(path: str, expected: dict[tuple[int, int], str]) -> None:
    """Verify that every intended Excel Note cell contains the exact description text.

    This checks the generated XLSX package itself, not only the in-memory mapping.
    """
    if not expected:
        return
    import xml.etree.ElementTree as ET
    with zipfile.ZipFile(path, 'r') as z:
        names = set(z.namelist())
        if 'xl/comments1.xml' not in names:
            raise RuntimeError('Excel статьи: файл не содержит xl/comments1.xml для Примечаний')
        raw = z.read('xl/comments1.xml')
    root = ET.fromstring(raw)
    ns = {'m': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
    actual: dict[str, str] = {}
    for node in root.findall('.//m:comment', ns):
        ref = str(node.attrib.get('ref') or '')
        text = ''.join(node.itertext()).strip()
        if ref:
            actual[ref] = text
    missing = []
    wrong = []
    for (row_idx, col_idx), text in expected.items():
        ref = f'{_xlsx_col_name(int(col_idx))}{int(row_idx)}'
        if ref not in actual:
            missing.append(ref)
        elif actual.get(ref, '') != str(text).strip():
            wrong.append(ref)
    if missing or wrong:
        raise RuntimeError(f'Excel статьи: повреждены примечания missing={missing[:8]} wrong={wrong[:8]} expected={len(expected)} actual={len(actual)}')

# --- excel:0043 · from 01_core_data.py:17422 · public _write_excel_by_selected_style ---
def _write_excel_by_selected_style(path: str, rows: list[list], chat_id: int, sheet_name: str='Данные', category_layout: bool=False, mode_override: str | None=None, compact_annotations: dict[tuple[int, int], str] | None=None) -> None:
    """XLSX writer with per-export style override: OLD / Comments / Notes."""
    mode = str(mode_override or excel_table_style(int(chat_id)) or 'old').strip().lower()
    if mode not in {'old', 'new_plain', 'new_comments', 'new_notes', 'google_notes'}:
        mode = 'old'
    local_mode = 'new_notes' if mode == 'google_notes' else mode
    # R16: ALL XLSX files are colored.  'old' now means old layout/annotation
    # behaviour only; it no longer bypasses the canonical vys-262 palette.
    if category_layout == 'category_compact':
        styles, annotations, freeze_rows, widths = _modern_category_no_description_styles_comments(rows, compact_annotations or {})
    elif category_layout:
        styles, annotations, freeze_rows, widths = _modern_category_excel_styles_comments(rows)
    elif compact_annotations is not None:
        styles, annotations, freeze_rows, widths = _modern_compact_excel_styles_comments(rows, compact_annotations)
    else:
        styles, annotations, freeze_rows, widths = _modern_simple_excel_styles_comments(rows)
    annotation_mode = None if local_mode in {'old', 'new_plain'} else 'comments' if local_mode == 'new_comments' else 'notes'
    if annotation_mode is None:
        annotations = {}
    expected_annotations: dict[tuple[int, int], str] = {}
    if annotation_mode == 'notes':
        if category_layout == 'category_compact':
            expected_annotations = {k: str(v).strip() for k, v in (compact_annotations or {}).items() if str(v or '').strip()}
        elif category_layout:
            expected_annotations = _category_excel_expected_annotations(rows)
        elif compact_annotations is not None:
            expected_annotations = {k: str(v).strip() for k, v in compact_annotations.items() if str(v or '').strip()}
        if expected_annotations:
            annotations = dict(expected_annotations)
    _write_tabl_lsx_xlsx(path, rows, styles, sheet_name=sheet_name, comments=annotations, freeze_rows=freeze_rows, widths=widths, annotation_mode=annotation_mode)
    _validate_xlsx_annotation_package(path, annotation_mode)
    if expected_annotations:
        _validate_xlsx_expected_notes(path, expected_annotations)

# --- excel:0044 · from 01_core_data.py:17456 · public create_tabl_lsx_file ---
def create_tabl_lsx_file(chat_id: int, reference_day: str | None=None) -> str:
    chat_id = int(chat_id)
    store = get_chat_store(chat_id)
    modern_excel = excel_table_style(chat_id) != 'old'
    weeks = _tabl_lsx_weeks(reference_day or today_key(), 4)
    cols = ['Дата', 'Приход/выдача', 'Откуда/кому'] + TABL_LSX_CATEGORIES
    rows, styles = ([], [])
    comments = {}
    title = f'сегодня {fmt_date_ddmmyy(today_key())} — {get_chat_display_name(chat_id)}'
    rows.append([title])
    styles.append([1] + [0] * (len(cols) - 1))
    rows.append(['Таблица за последние 4 недели: четверг–среда'])
    styles.append([1] + [0] * (len(cols) - 1))
    rows.append([])
    styles.append([])
    daily = {}
    range_builder = globals().get('_excel_canonical_records_for_range')
    if callable(range_builder) and weeks:
        canonical_rows = range_builder(chat_id, 'ars', weeks[0][0], weeks[-1][1])
        for _rec in canonical_rows or []:
            _dk = str(globals().get('_v151_day_key', _record_day_key)(_rec))[:10]
            daily.setdefault(_dk, []).append(_rec)
    else:
        daily = store.get('daily_records', {}) or {}
    for start_key, end_key in weeks:
        rows.append(['Неделя', f'{fmt_date_ddmmyy(start_key)} — {fmt_date_ddmmyy(end_key)}'])
        styles.append([3, 3] + [3] * (len(cols) - 2))
        rows.append(cols)
        styles.append([2, 2, 2] + [8 + i for i in range(len(TABL_LSX_CATEGORIES))] if modern_excel else [2] * len(cols))
        opening = _tabl_lsx_opening_balance(store, start_key, chat_id=chat_id)
        rows.append([fmt_date_ddmmyy(start_key), int(round(opening)), 'Остаток с прошлого раза'] + [''] * len(TABL_LSX_CATEGORIES))
        styles.append([7, 7, 7] + [4] * len(TABL_LSX_CATEGORIES))
        income_total = 0.0
        expense_total = 0.0
        cat_totals = {cat: 0.0 for cat in TABL_LSX_CATEGORIES}
        week_canonical_records = []
        start_dt = datetime.strptime(start_key, '%Y-%m-%d').date()
        for offset in range(7):
            dk = (start_dt + timedelta(days=offset)).strftime('%Y-%m-%d')
            recs = sorted(daily.get(dk, []) or [], key=record_sort_key)
            if not recs:
                rows.append([fmt_date_ddmmyy(dk)] + [''] * (len(cols) - 1))
                styles.append([3] + [4] * (len(cols) - 1))
                continue
            first_for_day = True
            for rec in recs:
                week_canonical_records.append(rec)
                try:
                    amount = float(rec.get('_v151_amount', rec.get('amount', 0)) or 0)
                except Exception:
                    amount = 0.0
                note = str(rec.get('_v151_note', rec.get('note') or '') or '').strip()
                row = [fmt_date_ddmmyy(dk) if first_for_day else '', '', ''] + [''] * len(TABL_LSX_CATEGORIES)
                row_styles = [3 if row[0] else 4, 4, 4] + [4] * len(TABL_LSX_CATEGORIES)
                first_for_day = False
                if amount >= 0:
                    income_total += amount
                    row[1] = int(round(amount))
                    row[2] = note
                else:
                    value = abs(amount)
                    expense_total += value
                    cat = None
                    try:
                        resolved = resolve_expense_category_for_record(rec, store)
                        resolved_cf = str(resolved or '').strip().casefold()
                        for _cat_name in TABL_LSX_CATEGORIES:
                            if str(_cat_name).strip().casefold() == resolved_cf:
                                cat = _cat_name
                                break
                    except Exception:
                        cat = None
                    if not cat:
                        cat = _tabl_lsx_category(note)
                    cat_idx = TABL_LSX_CATEGORIES.index(cat)
                    cat_totals[cat] = cat_totals.get(cat, 0.0) + value
                    col_idx = 3 + cat_idx
                    if modern_excel:
                        row[col_idx] = int(value) if float(value).is_integer() else value
                        row_styles[col_idx] = 19 + cat_idx
                        if note:
                            comments[len(rows) + 1, col_idx + 1] = note
                    else:
                        shown = fmt_num_plain(value)
                        row[col_idx] = (shown + (' ' + note if note else '')).strip()
                rows.append(row)
                styles.append(row_styles)
        total_row = ['Итог:', int(round(income_total)), ''] + [int(round(cat_totals.get(cat, 0))) if cat_totals.get(cat, 0) else '' for cat in TABL_LSX_CATEGORIES]
        rows.append(total_row)
        styles.append([5] * len(cols))
        rows.append(['расход:', int(round(expense_total))] + [''] * (len(cols) - 2))
        styles.append([5] * len(cols))
        _v150_week_closing = float(opening + income_total - expense_total)
        rows.append(['Остаток на руках', int(round(_v150_week_closing))] + [''] * (len(cols) - 2))
        styles.append([6] * len(cols))
        _v150_week_reserve = float(_v150_export_reserve(chat_id)) if '_v150_export_reserve' in globals() else 0.0
        rows.append(['Гомонковые', int(round(_v150_week_reserve)) if float(_v150_week_reserve).is_integer() else _v150_week_reserve] + [''] * (len(cols) - 2))
        styles.append([6] * len(cols))
        _v150_week_turnover = _v150_week_closing - _v150_week_reserve
        rows.append(['Остаток в обороте', int(round(_v150_week_turnover)) if float(_v150_week_turnover).is_integer() else _v150_week_turnover] + [''] * (len(cols) - 2))
        styles.append([6] * len(cols))
        rows.append([])
        styles.append([])
        _v150_products_total = float(cat_totals.get('Продукты', 0.0) or 0.0)
        _v150_food_metric_value = 0.0
        try:
            if callable(globals().get('_v151_food_metric')):
                _v150_products_total, _v150_food_metric_value, _v194_days, _v194_rate = _v151_food_metric(int(chat_id), week_canonical_records, start_key, end_key)
            elif '_v150_food_per_person' in globals():
                _v150_food_metric_value = _v150_food_per_person(_v150_products_total)
        except Exception:
            _v150_food_metric_value = 0.0
        rows.append(['Расход еды на человека в сутки', _v150_food_metric_value] + [''] * (len(cols) - 2))
        styles.append([5] * len(cols))
        rows.append([])
        styles.append([])
    os.makedirs(MEGA_LOCAL_TMP_DIR, exist_ok=True)
    start_all, end_all = (weeks[0][0], weeks[-1][1])
    mode_tag = excel_table_style(chat_id)
    fname = f"tabl_lsx_{mode_tag}_{mega_safe_name(get_chat_display_name(chat_id), 'chat')}_{start_all}_{end_all}.xlsx"
    path = os.path.join(MEGA_LOCAL_TMP_DIR, fname)
    annotation_mode = excel_annotation_mode(chat_id)
    try:
        usd_builder = globals().get('_v151_simple_table')
        usd_enabled = globals().get('excel_usd_table_enabled')
        ctx_local = globals().get('_V151_EXPORT_LOCAL')
        if callable(usd_builder) and (not callable(usd_enabled) or bool(usd_enabled(int(chat_id)))) and (ctx_local is not None):
            prev_ctx = getattr(ctx_local, 'value', None)
            try:
                ctx_local.value = {'kind': 'exact', 'target_chat_id': int(chat_id), 'start_key': str(start_all), 'start_rid': 0, 'end_key': str(end_all), 'end_rid': 0, 'file_type': 'xlsx'}
                usd_rows, _usd_notes = usd_builder(int(chat_id), 'usd', compact=False)
            finally:
                ctx_local.value = prev_ctx
            if usd_rows:
                offset = len(rows) + 2
                rows.extend([[], []])
                styles.extend([[], []])
                shifter = globals().get('_v193_shift_formula_rows')
                shifted_usd = shifter(usd_rows, offset) if callable(shifter) else usd_rows
                if modern_excel and callable(globals().get('_modern_simple_excel_styles_comments')):
                    usd_styles, usd_comments, _freeze, _widths = _modern_simple_excel_styles_comments(shifted_usd)
                    styles.extend(usd_styles)
                    for (rr, cc), text in (usd_comments or {}).items():
                        comments[int(rr) + offset, int(cc)] = text
                else:
                    styles.extend([[4] * len(r or []) for r in shifted_usd])
                rows.extend(shifted_usd)
                validator = globals().get('_v193_validate_currency_formula_domains')
                if callable(validator):
                    validator(rows)
    except Exception as _v192_usd_exc:
        try:
            log_error(f'tabl_lsx USD append({chat_id}): {_v192_usd_exc}')
        except Exception:
            pass
    _write_tabl_lsx_xlsx(path, rows, styles, sheet_name='4 недели', comments=comments if modern_excel else None, annotation_mode=annotation_mode)
    if modern_excel:
        _validate_xlsx_annotation_package(path, annotation_mode)
    return path

# --- excel:0045 · from 01_core_data.py:17616 · public send_tabl_lsx_for_chat ---
def _legacy_s0045_send_tabl_lsx_for_chat(recipient_chat_id: int, target_chat_id: int):
    path = None
    try:
        _file_job_progress('собираю Excel', force=True)
        path = create_tabl_lsx_file(target_chat_id, today_key())
        _file_job_progress('отправляю Excel в Telegram', force=True)
        display = os.path.basename(path)
        fobj = file_bytesio_named(path, display)
        if not fobj:
            raise RuntimeError('Excel создан, но не удалось открыть файл для отправки в Telegram')
        _tg_call_retry(bot.send_document, recipient_chat_id, fobj, caption=f'📊 Таблица LSX ({excel_table_style_caption(target_chat_id)}) за последние 4 недели Чт–Ср: {get_chat_display_name(target_chat_id)}', timeout=120, purpose='tabl_lsx_send_document')
        return True
    except Exception as e:
        log_error(f'send_tabl_lsx_for_chat({target_chat_id}): {e}')
        send_and_auto_delete(recipient_chat_id, '❌ Не удалось создать /tabl_lsx.', 15)
        return False
    finally:
        if path:
            try:
                os.remove(path)
            except Exception:
                pass

# --- excel:0046 · from 01_core_data.py:17639 · public save_chat_xlsx ---
def save_chat_xlsx(chat_id: int, path: str | None=None, store: dict | None=None) -> str | None:
    """Создаёт Excel .xlsx для чата; date в формате DD:MM:YY."""
    try:
        store = store or data.get('chats', {}).get(str(chat_id)) or get_chat_store(chat_id)
        path = path or chat_xlsx_file(chat_id)
        rows = [['Дата', 'Описание', 'Приход', 'Расход']]
        daily = store.get('daily_records', {}) or {}
        for dk in sorted(daily.keys()):
            recs_sorted = sorted(daily.get(dk, []) or [], key=record_sort_key)
            for r in recs_sorted:
                rows.append(_xlsx_record_row(fmt_date_table(dk), r.get('amount', 0), r.get('note', '')))
        rows = insert_blank_rows_between_days(rows, header_rows=1)
        first_key = sorted(daily.keys())[0] if daily else today_key()
        opening = _opening_balance_before_exact(store, first_key, 0)
        rows = _xlsx_simple_rows_with_balances(rows, opening, chat_id)
        _write_excel_by_selected_style(path, rows, chat_id, sheet_name='Данные', category_layout=False)
        return path
    except Exception as e:
        log_error(f'save_chat_xlsx({get_chat_display_name(chat_id)}): {e}')
        return None

# --- excel:0047 · from 05_finance_ui.py:1476 · public _excel_checkbox ---
def _excel_checkbox(mark: bool, label: str) -> str:
    return f"{('✅' if mark else '⬜')} {label}"

# --- excel:0048 · from 05_finance_ui.py:1479 · public _v177_legacy_0172_period_excel_style_keyboard ---
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

# --- excel:0049 · from 05_finance_ui.py:1506 · public _exact_excel_style_keyboard ---
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

# --- excel:0050 · from 05_finance_ui.py:1547 · public _v177_legacy_0174_build_exact_category_stats_xlsx_rows ---
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

# --- excel:0051 · from 07_state_web.py:1373 · public _canon_backup_excel_all_enabled__001 ---
def _canon_backup_excel_all_enabled__001(chat_id: int | None=None) -> bool:
    return bool(_tenant_settings_for_context(chat_id).get('backup_excel_all_enabled', True))

# --- excel:0052 · from 07_state_web.py:1376 · public _canon_set_backup_excel_all_enabled__001 ---
def _canon_set_backup_excel_all_enabled__001(enabled: bool, chat_id: int | None=None):
    _tenant_settings_for_context(chat_id)['backup_excel_all_enabled'] = bool(enabled)
    save_data(data, root_only=True)

# --- excel:0053 · from 07_state_web.py:1380 · public _canon_excel_interface_mode__001 ---
def _canon_excel_interface_mode__001(chat_id: int | None=None) -> str:
    mode = str(_tenant_settings_for_context(chat_id).get('excel_interface_mode') or 'new').lower()
    return mode if mode in {'old', 'new'} else 'new'

# --- excel:0054 · from 07_state_web.py:1384 · public _canon_set_excel_interface_mode__001 ---
def _canon_set_excel_interface_mode__001(mode: str) -> str:
    mode = 'old' if str(mode).lower() == 'old' else 'new'
    _tenant_settings_for_context()['excel_interface_mode'] = mode
    save_data(data, root_only=True)
    return mode

# --- excel:0055 · from 07_state_web.py:1390 · public _canon_excel_new_export_options__001 ---
def _canon_excel_new_export_options__001() -> dict:
    settings = _tenant_settings_for_context()
    options = settings.get('excel_new_export_options')
    if not isinstance(options, dict):
        options = {'old_table': False, 'comments': False, 'notes': True, 'description_column': False}
        settings['excel_new_export_options'] = options
    return normalize_excel_export_options(options)

# --- excel:0056 · from 07_state_web.py:1398 · public _canon_toggle_excel_new_export_option__001 ---
def _canon_toggle_excel_new_export_option__001(option: str) -> dict:
    opts = excel_new_export_options()
    option = str(option or '')
    if option in opts:
        opts[option] = not bool(opts.get(option))
    if option == 'old_table' and opts.get('old_table'):
        opts['comments'] = opts['notes'] = opts['description_column'] = False
    elif option in {'comments', 'notes', 'description_column'} and opts.get(option):
        opts['old_table'] = False
        if option in {'comments', 'notes'}:
            for other in {'comments', 'notes'} - {option}:
                opts[other] = False
    _tenant_settings_for_context()['excel_new_export_options'] = dict(opts)
    save_data(data, root_only=True)
    return opts

# --- excel:0057 · from 07_state_web.py:1414 · public _canon_excel_table_style__001 ---
def _canon_excel_table_style__001(chat_id: int) -> str:
    mode = _normalize_excel_table_style(_tenant_settings_for_context(chat_id).get('excel_table_style'))
    return mode or 'new_notes'

# --- excel:0058 · from 07_state_web.py:1418 · public _canon_set_excel_table_style__001 ---
def _canon_set_excel_table_style__001(chat_id: int, mode: str) -> str:
    mode = _normalize_excel_table_style(mode) or 'new_notes'
    _tenant_settings_for_context(chat_id)['excel_table_style'] = mode
    try:
        get_chat_store(int(chat_id)).setdefault('settings', {})['excel_table_style'] = mode
    except Exception:
        pass
    save_data(data, chat_ids=[int(chat_id)])
    return mode

# --- excel:0059 · from 07_state_web.py:6480 · public _v177_legacy_0175_build_exact_category_stats_xlsx_rows ---
def _v177_legacy_0175_build_exact_category_stats_xlsx_rows(target_chat_id: int, start_key: str, start_rid: int, end_key: str, end_rid: int) -> list[list]:
    rows = _V150_BASE_CATEGORY_ROWS(target_chat_id, start_key, start_rid, end_key, end_rid)
    closing = 0.0
    for row in reversed(rows or []):
        if len(row) > 2 and str(row[1] if len(row) > 1 else '').strip().casefold() == 'остаток на руках':
            closing = _v150_cell_value(row[2])
            break
    try:
        records = exact_record_range(get_chat_store(int(target_chat_id)), start_key, start_rid, end_key, end_rid)
        products_total = _v150_product_total_from_records(int(target_chat_id), records)
    except Exception:
        products_total = 0.0
    return _v150_append_summary_rows(rows, int(target_chat_id), closing, products_total, 'wide')

# --- excel:0060 · from 07_state_web.py:6498 · public _v177_legacy_0091_xlsx_simple_rows_with_balances ---
def _v177_legacy_0091_xlsx_simple_rows_with_balances(rows: list[list], opening_balance: float, target_chat_id: int | None=None) -> list[list]:
    base = _V150_BASE_SIMPLE_ROWS(rows, opening_balance, target_chat_id) if _V150_BASE_SIMPLE_ROWS.__code__.co_argcount >= 3 else _V150_BASE_SIMPLE_ROWS(rows, opening_balance)
    closing = 0.0
    for row in reversed(base or []):
        if len(row) > 2 and str(row[1] if len(row) > 1 else '').strip().casefold() == 'остаток на руках':
            closing = _v150_cell_value(row[2])
            break
    products_total = 0.0
    if target_chat_id is not None:
        store = get_chat_store(int(target_chat_id))
        for row in (rows or [])[1:]:
            if len(row) < 4:
                continue
            note = str(row[1] or '')
            expense = _v150_float(row[3])
            if expense <= 0:
                continue
            try:
                category = resolve_expense_category(note, store)
            except Exception:
                category = ''
            if _v150_is_products_category(category):
                products_total += expense
    return _v150_append_summary_rows(base, target_chat_id, closing, products_total, 'wide')

# --- excel:0061 · from 07_state_web.py:6527 · public _v177_legacy_0094_compact_simple_excel_rows_and_annotations ---
def _v177_legacy_0094_compact_simple_excel_rows_and_annotations(raw_rows: list[tuple], opening_balance: float, target_chat_id: int | None=None) -> tuple[list[list], dict[tuple[int, int], str]]:
    if _V150_BASE_COMPACT_ROWS.__code__.co_argcount >= 3:
        base, notes = _V150_BASE_COMPACT_ROWS(raw_rows, opening_balance, target_chat_id)
    else:
        base, notes = _V150_BASE_COMPACT_ROWS(raw_rows, opening_balance)
    closing = 0.0
    for row in reversed(base or []):
        if row and str(row[0] or '').strip().casefold() == 'остаток на руках':
            closing = _v150_cell_value(row[1] if len(row) > 1 else 0)
            break
    products_total = 0.0
    if target_chat_id is not None:
        store = get_chat_store(int(target_chat_id))
        for _date, amount_raw, note in raw_rows or []:
            try:
                amount = parse_csv_amount(amount_raw)
            except Exception:
                amount = _v150_float(amount_raw)
            if amount >= 0:
                continue
            try:
                category = resolve_expense_category(str(note or ''), store)
            except Exception:
                category = ''
            if _v150_is_products_category(category):
                products_total += abs(amount)
    return (_v150_append_summary_rows(base, target_chat_id, closing, products_total, 'compact'), notes)

# --- excel:0062 · from 07_state_web.py:7637 · public _v177_legacy_0176_build_exact_category_stats_xlsx_rows ---
def _v177_legacy_0176_build_exact_category_stats_xlsx_rows(target_chat_id: int, start_key: str, start_rid: int, end_key: str, end_rid: int) -> list[list]:
    previous = getattr(_V151_EXPORT_LOCAL, 'value', None)
    if not previous:
        _V151_EXPORT_LOCAL.value = {'kind': 'exact', 'target_chat_id': int(target_chat_id), 'start_key': str(start_key)[:10], 'start_rid': int(start_rid or 0), 'end_key': str(end_key)[:10], 'end_rid': int(end_rid or 0), 'file_type': 'xlsxstat'}
    try:
        ars_rows = _v151_category_table(int(target_chat_id), 'ars')
        usd_rows = _v151_category_table(int(target_chat_id), 'usd')
        return ars_rows + [[], []] + usd_rows
    finally:
        if not previous:
            _V151_EXPORT_LOCAL.value = None

# --- excel:0063 · from 07_state_web.py:7653 · public _v177_legacy_0092_xlsx_simple_rows_with_balances ---
def _v177_legacy_0092_xlsx_simple_rows_with_balances(rows: list[list], opening_balance: float, target_chat_id: int | None=None) -> list[list]:
    if target_chat_id is None:
        return globals().get('_V150_BASE_SIMPLE_ROWS', lambda r, o, *_: r)(rows, opening_balance, target_chat_id)
    ars_rows, _ = _v151_simple_table(int(target_chat_id), 'ars', compact=False)
    usd_rows, _ = _v151_simple_table(int(target_chat_id), 'usd', compact=False)
    return ars_rows + [[], []] + usd_rows

# --- excel:0064 · from 07_state_web.py:7664 · public _v177_legacy_0095_compact_simple_excel_rows_and_annotations ---
def _v177_legacy_0095_compact_simple_excel_rows_and_annotations(raw_rows: list[tuple], opening_balance: float, target_chat_id: int | None=None) -> tuple[list[list], dict[tuple[int, int], str]]:
    if target_chat_id is None:
        base = globals().get('_V150_BASE_COMPACT_ROWS')
        return base(raw_rows, opening_balance, target_chat_id) if callable(base) else ([], {})
    ars_rows, ars_notes = _v151_simple_table(int(target_chat_id), 'ars', compact=True)
    offset = len(ars_rows) + 2
    usd_rows, usd_notes = _v151_simple_table(int(target_chat_id), 'usd', compact=True)
    notes = dict(ars_notes)
    for (row_idx, col_idx), text in usd_notes.items():
        notes[int(row_idx) + offset, int(col_idx)] = text
    return (ars_rows + [[], []] + usd_rows, notes)

# --- excel:0065 · from 07_state_web.py:7680 · public _v151_excel_options_for_style ---
def _v151_excel_options_for_style(style: str | None, options: dict | None) -> dict | None:
    if isinstance(options, dict):
        return options
    mode = str(style or '').strip().lower()
    if not mode:
        try:
            return normalize_excel_export_options()
        except Exception:
            return {'old_table': True, 'comments': False, 'notes': False, 'description_column': True}
    mapping = {'old': {'old_table': True, 'comments': False, 'notes': False, 'description_column': True}, 'new_plain': {'old_table': False, 'comments': False, 'notes': False, 'description_column': True}, 'new_comments': {'old_table': False, 'comments': True, 'notes': False, 'description_column': True}, 'new_notes': {'old_table': False, 'comments': False, 'notes': True, 'description_column': True}, 'google_notes': {'old_table': False, 'comments': False, 'notes': True, 'description_column': True}}
    return mapping.get(mode) or normalize_excel_export_options()

# --- excel:0066 · from 07_state_web.py:10852 · public excel_usd_table_enabled ---
def excel_usd_table_enabled(chat_id: int) -> bool:
    """Whether a separate USD operation table is appended to Excel/Google exports."""
    try:
        settings = get_chat_store(int(chat_id)).setdefault('settings', {})
        return bool(settings.get('excel_include_usd_table', True))
    except Exception:
        return True

# --- excel:0067 · from 07_state_web.py:10860 · public set_excel_usd_table_enabled ---
def set_excel_usd_table_enabled(chat_id: int, enabled: bool) -> bool:
    chat_id = int(chat_id)
    settings = get_chat_store(chat_id).setdefault('settings', {})
    settings['excel_include_usd_table'] = bool(enabled)
    save_data(data, chat_ids=[chat_id])
    try:
        schedule_config_backup_for_chats(chat_id, delay=0.5)
    except Exception:
        pass
    try:
        bot_journal('excel_usd_table_toggle', chat_id, f'enabled={bool(enabled)}')
    except Exception:
        pass
    return bool(enabled)

# --- excel:0068 · from 07_state_web.py:10875 · public toggle_excel_usd_table_enabled ---
def toggle_excel_usd_table_enabled(chat_id: int) -> bool:
    return set_excel_usd_table_enabled(int(chat_id), not excel_usd_table_enabled(int(chat_id)))

# --- excel:0069 · from 07_state_web.py:10878 · public _canon_period_excel_style_keyboard__001 ---
def _canon_period_excel_style_keyboard__001(scope: str, target_chat_id: int, mode: str, file_type: str, day_key: str, owner_day_key: str):
    """F179: original controls + an explicit independent USD-table switch."""
    kb = _V154_BASE_PERIOD_EXCEL_KEYBOARD(scope, target_chat_id, mode, file_type, day_key, owner_day_key)
    enabled = excel_usd_table_enabled(int(target_chat_id))
    label = f"{('✅' if enabled else '⬜')} 💵 USD расходы в таблице: {('ВКЛ' if enabled else 'ВЫКЛ')}"
    row = [IB(label, callback_data=export_callback(f'exp_excel_dollar_toggle:{scope}:{int(target_chat_id)}:{mode}:{file_type}:{day_key}:{owner_day_key}'))]
    try:
        insert_at = max(0, len(kb.keyboard) - 2)
        kb.keyboard.insert(insert_at, row)
    except Exception:
        kb.row(*row)
    return kb

# --- excel:0070 · from 07_state_web.py:10955 · public _excel_canonical_opening_balance ---
def _excel_canonical_opening_balance(chat_id: int, currency: str, start_day: str, start_rid: int | None=0, exact: bool=False) -> float:
    cid = int(chat_id)
    cur = 'usd' if str(currency or 'ars').strip().lower() == 'usd' else 'ars'
    start = str(start_day or '')[:10]
    try:
        start_rid = int(start_rid or 0)
    except Exception:
        start_rid = 0
    total = 0.0
    rows = list(_v151_all_records(cid, cur) or [])
    try:
        rows = sorted(rows, key=record_sort_key)
    except Exception:
        pass
    target_sort_key = None
    if bool(exact) and start_rid and (cur == 'ars'):
        try:
            target = next((r for r in rows if _v151_day_key(r) == start and int(r.get('id') or 0) == start_rid), None)
            if target is not None:
                target_sort_key = record_sort_key(target)
        except Exception:
            target_sort_key = None
    for rec in rows:
        day = _v151_day_key(rec)
        if not day:
            continue
        amount = _v151_float(rec.get('_v151_amount'))
        if day < start:
            total += amount
            continue
        if day > start:
            break
        if not bool(exact) or not start_rid or cur != 'ars':
            break
        if target_sort_key is not None:
            try:
                if record_sort_key(rec) < target_sort_key:
                    total += amount
                    continue
            except Exception:
                pass
            break
        try:
            if int(rec.get('id') or 0) < start_rid:
                total += amount
                continue
        except Exception:
            pass
        break
    return float(total)

# --- excel:0071 · from 07_state_web.py:11006 · public _excel_canonical_records_for_range ---
def _excel_canonical_records_for_range(chat_id: int, currency: str, start_day: str, end_day: str) -> list[dict]:
    cid = int(chat_id)
    cur = 'usd' if str(currency or 'ars').strip().lower() == 'usd' else 'ars'
    start = str(start_day or '')[:10]
    end = str(end_day or start)[:10]
    if end < start:
        start, end = (end, start)
    out = []
    for rec in _v151_all_records(cid, cur) or []:
        day = _v151_day_key(rec)
        if day and start <= day <= end:
            out.append(rec)
    try:
        return sorted(out, key=record_sort_key)
    except Exception:
        return out

# --- excel:0072 · from 07_state_web.py:11023 · public _excel_chat_id_for_store ---
def _excel_chat_id_for_store(store: dict | None) -> int | None:
    if not isinstance(store, dict):
        return None
    try:
        ctx = _v151_context()
        cid = int(ctx.get('target_chat_id') or 0)
        if cid:
            return cid
    except Exception:
        pass
    try:
        for raw_cid, row in (data.get('chats', {}) or {}).items():
            if row is store:
                return int(raw_cid)
    except Exception:
        pass
    try:
        owner_scope = int((store.get('settings', {}) or {}).get('owner_scope_id') or 0)
        if owner_scope:
            return owner_scope
    except Exception:
        pass
    return None

# --- excel:0073 · from 07_state_web.py:11190 · public _canon_build_exact_category_stats_xlsx_rows__001 ---
def _canon_build_exact_category_stats_xlsx_rows__001(target_chat_id: int, start_key: str, start_rid: int, end_key: str, end_rid: int) -> list[list]:
    """ARS keeps category layout; USD is always a clean four-column operation table."""
    previous = getattr(_V151_EXPORT_LOCAL, 'value', None)
    if not previous:
        _V151_EXPORT_LOCAL.value = {'kind': 'exact', 'target_chat_id': int(target_chat_id), 'start_key': str(start_key)[:10], 'start_rid': int(start_rid or 0), 'end_key': str(end_key)[:10], 'end_rid': int(end_rid or 0), 'file_type': 'xlsxstat'}
    try:
        ars_rows = _v151_category_table(int(target_chat_id), 'ars')
        usd_rows, _ = _v151_simple_table(int(target_chat_id), 'usd', compact=False)
        return _v154_join_ars_usd(ars_rows, usd_rows, int(target_chat_id))
    finally:
        if not previous:
            _V151_EXPORT_LOCAL.value = None

# --- excel:0074 · from 07_state_web.py:11203 · public _canon_xlsx_simple_rows_with_balances__001 ---
def _canon_xlsx_simple_rows_with_balances__001(rows: list[list], opening_balance: float, target_chat_id: int | None=None) -> list[list]:
    if target_chat_id is None:
        return globals().get('_V150_BASE_SIMPLE_ROWS', lambda r, o, *_: r)(rows, opening_balance, target_chat_id)
    ars_rows, _ = _v151_simple_table(int(target_chat_id), 'ars', compact=False)
    usd_rows, _ = _v151_simple_table(int(target_chat_id), 'usd', compact=False)
    return _v154_join_ars_usd(ars_rows, usd_rows, int(target_chat_id))

# --- excel:0075 · from 07_state_web.py:11210 · public _v177_legacy_0096_compact_simple_excel_rows_and_annotations ---
def _v177_legacy_0096_compact_simple_excel_rows_and_annotations(raw_rows: list[tuple], opening_balance: float, target_chat_id: int | None=None) -> tuple[list[list], dict[tuple[int, int], str]]:
    if target_chat_id is None:
        base = globals().get('_V150_BASE_COMPACT_ROWS')
        return base(raw_rows, opening_balance, target_chat_id) if callable(base) else ([], {})
    ars_rows, ars_notes = _v151_simple_table(int(target_chat_id), 'ars', compact=True)
    if not excel_usd_table_enabled(int(target_chat_id)):
        return (ars_rows, dict(ars_notes))
    usd_rows, _ = _v151_simple_table(int(target_chat_id), 'usd', compact=False)
    prefix = list(ars_rows or []) + [[], []]
    shifted_usd = _v193_shift_formula_rows(usd_rows, len(prefix))
    joined = prefix + shifted_usd
    _v193_validate_currency_formula_domains(joined)
    return (joined, dict(ars_notes))

# --- excel:0076 · from 07_state_web.py:11272 · public _canon_modern_compact_excel_styles_comments__001 ---
def _canon_modern_compact_excel_styles_comments__001(rows: list[list], annotations: dict[tuple[int, int], str]):
    """Compact ARS may stay 3-column, while appended USD keeps its four-column simple layout."""
    idx = _v154_find_usd_section(rows)
    if idx is None or not callable(_V154_BASE_MODERN_COMPACT) or (not callable(_V154_BASE_MODERN_SIMPLE)):
        return _V154_BASE_MODERN_COMPACT(rows, annotations)
    prefix, suffix = (list(rows[:idx]), list(rows[idx:]))
    p = _V154_BASE_MODERN_COMPACT(prefix, annotations)
    s = _V154_BASE_MODERN_SIMPLE(suffix)
    return _v154_merge_styles(prefix, suffix, p, s, keep_suffix_comments=False)

# --- excel:0077 · from 07_state_web.py:11282 · public _v177_legacy_0102_modern_category_excel_styles_comments ---
def _v177_legacy_0102_modern_category_excel_styles_comments(rows: list[list]):
    idx = _v154_find_usd_section(rows)
    if idx is None or not callable(_V154_BASE_MODERN_CATEGORY) or (not callable(_V154_BASE_MODERN_SIMPLE)):
        return _V154_BASE_MODERN_CATEGORY(rows)
    prefix, suffix = (list(rows[:idx]), list(rows[idx:]))
    return _v154_merge_styles(prefix, suffix, _V154_BASE_MODERN_CATEGORY(prefix), _V154_BASE_MODERN_SIMPLE(suffix), keep_suffix_comments=True)

# --- excel:0078 · from 08_reliability_tasks.py:1584 · public _canon_modern_simple_excel_styles_comments__001 ---
def _canon_modern_simple_excel_styles_comments__001(rows: list[list]):
    if callable(_V158_PREV_MODERN_SIMPLE):
        styles, comments, header_row, widths = _V158_PREV_MODERN_SIMPLE(rows)
    else:
        max_cols = max((len(r) for r in rows or []), default=4)
        styles, comments, header_row, widths = ([[0] * max_cols for _ in rows or []], {}, 1, [13, 38, 15, 15])
    comments = _v158_add_income_annotations_from_description(rows, comments)
    return (styles, comments, header_row, widths)

# --- excel:0079 · from 08_reliability_tasks.py:1593 · public _canon_modern_category_excel_styles_comments__001 ---
def _canon_modern_category_excel_styles_comments__001(rows: list[list]):
    if callable(_V158_PREV_MODERN_CATEGORY):
        styles, comments, header_row, widths = _V158_PREV_MODERN_CATEGORY(rows)
    else:
        max_cols = max((len(r) for r in rows or []), default=4)
        styles, comments, header_row, widths = ([[0] * max_cols for _ in rows or []], {}, 1, [13, 36, 15, 18])
    comments = _v158_add_income_annotations_from_description(rows, comments)
    return (styles, comments, header_row, widths)

# --- excel:0080 · from 08_reliability_tasks.py:1602 · public _canon_category_excel_expected_annotations__001 ---
def _canon_category_excel_expected_annotations__001(rows: list[list]) -> dict[tuple[int, int], str]:
    expected = {}
    if callable(_V158_PREV_CATEGORY_EXPECTED):
        try:
            expected.update(_V158_PREV_CATEGORY_EXPECTED(rows) or {})
        except Exception:
            pass
    return _v158_add_income_annotations_from_description(rows, expected)

# --- excel:0081 · from 08_reliability_tasks.py:1637 · public _canon_compact_simple_excel_rows_and_annotations__001 ---
def _canon_compact_simple_excel_rows_and_annotations__001(raw_rows: list[tuple], opening_balance: float, target_chat_id: int | None=None):
    if callable(_V158_PREV_COMPACT_ROWS):
        rows, annotations = _V158_PREV_COMPACT_ROWS(raw_rows, opening_balance, target_chat_id)
    else:
        rows, annotations = ([], {})
    annotations = dict(annotations or {})
    in_usd = False
    header_seen = False
    for r_idx, raw in enumerate(rows or [], start=1):
        row = list(raw or [])
        first_raw = str(row[0] if row else '').strip()
        if first_raw.upper() == 'USD':
            in_usd = True
            header_seen = False
            continue
        if not in_usd:
            continue
        first = first_raw.casefold()
        desc = str(row[1] if len(row) > 1 else '').strip()
        if first in {'дата', 'date'} and desc.casefold() in {'описание', 'description'}:
            header_seen = True
            continue
        if not header_seen or len(row) < 3:
            continue
        note = _v158_real_operation_description(desc)
        if note and _excel_nonempty(row[2]):
            annotations[r_idx, 3] = note
    return (rows, annotations)

# --- excel:0082 · from 08_reliability_tasks.py:8375 · public _v167_patch_xlsx_package ---
def _v167_patch_xlsx_package(path: str) -> None:
    if not path or not _v167_os.path.exists(path):
        return
    tmp = path + '.v167.tmp'
    ns = 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'
    _v167_ET.register_namespace('', ns)
    with _v167_zipfile.ZipFile(path, 'r') as zin, _v167_zipfile.ZipFile(tmp, 'w', _v167_zipfile.ZIP_DEFLATED) as zout:
        for item in zin.infolist():
            raw = zin.read(item.filename)
            if item.filename == 'xl/styles.xml':
                try:
                    root = _v167_ET.fromstring(raw)
                    numfmts = root.find(f'{{{ns}}}numFmts')
                    if numfmts is None:
                        numfmts = _v167_ET.Element(f'{{{ns}}}numFmts', {'count': '1'})
                        insert_at = 0
                        root.insert(insert_at, numfmts)
                    existing = None
                    for nf in list(numfmts):
                        if nf.attrib.get('formatCode') in {'#,##0', '#,###'}:
                            existing = nf
                            break
                    if existing is None:
                        used = {int(x.attrib.get('numFmtId', '0') or 0) for x in list(numfmts)}
                        fmt_id = next((n for n in range(164, 300) if n not in used), 164)
                        _v167_ET.SubElement(numfmts, f'{{{ns}}}numFmt', {'numFmtId': str(fmt_id), 'formatCode': '#,##0'})
                    else:
                        fmt_id = int(existing.attrib.get('numFmtId', '164') or 164)
                    numfmts.set('count', str(len(list(numfmts))))
                    borders = root.find(f'{{{ns}}}borders')
                    thin_id = 0
                    if borders is not None:
                        thin_id = len(list(borders))
                        border = _v167_ET.SubElement(borders, f'{{{ns}}}border')
                        for side in ('left', 'right', 'top', 'bottom'):
                            _v167_ET.SubElement(border, f'{{{ns}}}{side}', {'style': 'thin'})
                        _v167_ET.SubElement(border, f'{{{ns}}}diagonal')
                        borders.set('count', str(len(list(borders))))
                    cell_xfs = root.find(f'{{{ns}}}cellXfs')
                    if cell_xfs is not None:
                        for xf in list(cell_xfs):
                            xf.set('numFmtId', str(fmt_id))
                            xf.set('applyNumberFormat', '1')
                            if borders is not None:
                                xf.set('borderId', str(thin_id))
                                xf.set('applyBorder', '1')
                            align = xf.find(f'{{{ns}}}alignment')
                            if align is None:
                                align = _v167_ET.SubElement(xf, f'{{{ns}}}alignment')
                            align.set('wrapText', '1')
                            align.set('vertical', 'top')
                            xf.set('applyAlignment', '1')
                    raw = _v167_ET.tostring(root, encoding='utf-8', xml_declaration=True)
                except Exception:
                    pass
            elif item.filename == 'xl/worksheets/sheet1.xml':
                try:
                    root = _v167_ET.fromstring(raw)
                    cols = root.find(f'{{{ns}}}cols')
                    if cols is not None:
                        for col in list(cols):
                            lo = int(col.attrib.get('min', '0') or 0)
                            hi = int(col.attrib.get('max', '0') or 0)
                            if lo <= 2 <= hi:
                                col.set('width', '42')
                                col.set('customWidth', '1')
                    raw = _v167_ET.tostring(root, encoding='utf-8', xml_declaration=True)
                except Exception:
                    pass
            zout.writestr(item, raw)
    _v167_os.replace(tmp, path)

# --- excel:0083 · from 08_reliability_tasks.py:8523 · public _canon_write_simple_xlsx__001 ---
def _canon_write_simple_xlsx__001(path: str, rows: list[list], sheet_name: str='Данные') -> None:
    # R10: even the emergency/local simple XLSX path uses the original vys-262
    # colored financial palette. Normal exports run on Worker, but fallback files
    # must look the same instead of reverting to a black/white workbook.
    if callable(_V167_BASE_WRITE_TABL):
        try:
            styles, comments, freeze_rows, widths = _canon_modern_simple_excel_styles_comments__001(rows)
            _V167_BASE_WRITE_TABL(path, rows, styles, sheet_name=sheet_name, comments=comments, freeze_rows=freeze_rows, widths=widths, annotation_mode='notes')
            _v167_patch_xlsx_package(path)
            return
        except Exception:
            pass
    if not callable(_V167_BASE_WRITE_SIMPLE):
        raise RuntimeError('XLSX writer is unavailable')
    _V167_BASE_WRITE_SIMPLE(path, rows, sheet_name=sheet_name)
    _v167_patch_xlsx_package(path)

# --- excel:0084 · from 08_reliability_tasks.py:8540 · public _canon_write_tabl_lsx_xlsx__001 ---
def _canon_write_tabl_lsx_xlsx__001(path: str, rows: list[list], styles: list[list], sheet_name: str='4 недели', comments: dict | None=None, freeze_rows: int=3, widths: list[float] | None=None, annotation_mode: str | None='notes') -> None:
    if not callable(_V167_BASE_WRITE_TABL):
        raise RuntimeError('Styled XLSX writer is unavailable')
    widths2 = list(widths or [])
    if len(widths2) >= 2:
        widths2[1] = max(42, float(widths2[1] or 0))
    rows2 = _v167_formulaize_four_week_rows(rows) if str(sheet_name or '').strip().casefold() == '4 недели' else rows
    _V167_BASE_WRITE_TABL(path, rows2, styles, sheet_name=sheet_name, comments=comments, freeze_rows=freeze_rows, widths=widths2 or widths, annotation_mode=annotation_mode)
    _v167_patch_xlsx_package(path)

# --- excel:0085 · from 10_split_policy_offload.py:6919 · public send_tabl_lsx_for_chat ---
def send_tabl_lsx_for_chat(recipient_chat_id:int,target_chat_id:int):
    ok,_info=submit_interactive_file_job(int(recipient_chat_id),'tabl_lsx','Excel /tabl_lsx',_r34_export_marker,int(recipient_chat_id),int(target_chat_id))
    return bool(ok)

# --- excel:0086 · from 10_split_policy_offload.py:9089 · public _r71_local_tabl_lsx ---
def _r71_local_tabl_lsx(recipient_chat_id, target_chat_id):
    path = None
    try:
        _file_job_progress('R1 FAST · собираю Excel', force=True)
        path = create_tabl_lsx_file(int(target_chat_id), today_key())
        _file_job_progress('R1 FAST · отправляю Excel', force=True)
        display = _split_os.path.basename(path)
        fobj = file_bytesio_named(path, display)
        if not fobj:
            raise RuntimeError('Excel создан, но не удалось открыть файл')
        _tg_call_retry(bot.send_document, int(recipient_chat_id), fobj, caption=f'📊 Таблица LSX ({excel_table_style_caption(int(target_chat_id))}) за последние 4 недели Чт–Ср: {get_chat_display_name(int(target_chat_id))}', timeout=120, purpose='r71_local_tabl_lsx')
        return True
    except Exception as exc:
        try: log_error(f'R71 local tabl_lsx: {exc}')
        except Exception: pass
        return False
    finally:
        if path:
            try: _split_os.remove(path)
            except Exception: pass

# v266
