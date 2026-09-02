# v262
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
# v262
