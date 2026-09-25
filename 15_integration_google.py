# v267
"""ОЧНИСЬ 12.35 · physical owner: google.

Этот файл — единственное физическое место тел функций домена.
Он НЕ запускается отдельно и НЕ импортируется как Python-модуль.
bot.py читает его как каталог исходников и устанавливает нужную стадию в исторической точке runtime.
Последняя версия каждого публичного символа сохраняет обычное имя; старые стадии помечены _legacy_sXXXX_.
"""

# --- google:0001 · from 05_finance_ui.py:3226 · public _google_request_guarded ---
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

# --- google:0002 · from 05_finance_ui.py:3246 · public _v177_legacy_0205_google_service_account_info ---
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

# --- google:0003 · from 05_finance_ui.py:3267 · public _google_sign_rs256 ---
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

# --- google:0004 · from 05_finance_ui.py:3291 · public _v177_legacy_0206_google_access_token ---
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

# --- google:0005 · from 05_finance_ui.py:3316 · public _google_cell_value ---
def _google_cell_value(value):
    if isinstance(value, dict) and value.get('formula'):
        return {'formulaValue': '=' + str(value.get('formula') or '').lstrip('=')}
    if isinstance(value, bool):
        return {'boolValue': value}
    if isinstance(value, (int, float)) and (not isinstance(value, bool)):
        return {'numberValue': float(value)}
    return {'stringValue': str(value or '')}

# --- google:0006 · from 05_finance_ui.py:3325 · public _google_category_fill ---
def _google_category_fill(col_idx_zero: int) -> dict:
    palette = [(0.78, 0.94, 0.81), (0.87, 0.92, 0.97), (0.99, 0.89, 0.84), (0.89, 0.87, 0.93), (1.0, 0.95, 0.8), (0.85, 0.92, 0.83), (0.81, 0.89, 0.95), (0.96, 0.8, 0.8), (0.82, 0.88, 0.89), (0.92, 0.82, 0.86), (0.85, 0.82, 0.91)]
    if col_idx_zero >= 3:
        rgb = palette[(col_idx_zero - 3) % len(palette)]
        return {'red': rgb[0], 'green': rgb[1], 'blue': rgb[2]}
    return {'red': 0.92, 'green': 0.95, 'blue': 0.9}

# --- google:0007 · from 05_finance_ui.py:3332 · public _v177_legacy_0207_google_spreadsheet_id ---
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

# --- google:0008 · from 05_finance_ui.py:3349 · public _google_sheet_tab_title ---
def _google_sheet_tab_title(title: str) -> str:
    """Creates a short unique Google Sheets tab title safe for repeated exports."""
    base = re.sub('[\\\\/\\?\\*\\[\\]:]', ' ', str(title or 'Статьи'))
    base = re.sub('\\s+', ' ', base).strip(" ' ") or 'Статьи'
    stamp = datetime.now().strftime('%d.%m %H-%M-%S')
    suffix = f' · {stamp}'
    limit = max(1, 100 - len(suffix))
    return base[:limit].rstrip() + suffix

# --- google:0009 · from 05_finance_ui.py:3358 · public _v177_legacy_0208_google_sheets_create_category_report ---
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

# --- google:0010 · from 07_state_web.py:2341 · public tenant_google_config ---
def tenant_google_config(tenant_id: str | None=None, create: bool=True) -> dict:
    tid = _v149_tenant_id(tenant_id)
    row = tenant_get(tid)
    if not isinstance(row, dict):
        if not create:
            return {}
        raise RuntimeError('Пространство Google не найдено')
    cfg = row.get('google_v149')
    if not isinstance(cfg, dict):
        if not create:
            return {}
        cfg = {}
        row['google_v149'] = cfg
    cfg.setdefault('schema_version', V149_GOOGLE_SCHEMA_VERSION)
    cfg.setdefault('credentials_sealed', '')
    cfg.setdefault('credential_fingerprint', '')
    cfg.setdefault('service_account_email', '')
    cfg.setdefault('owner_google_email', '')
    cfg.setdefault('spreadsheet_id', '')
    cfg.setdefault('spreadsheet_title', '')
    cfg.setdefault('drive_folder_id', '')
    cfg.setdefault('drive_folder_name', '')
    cfg.setdefault('export_settings', {'sheet_enabled': True, 'drive_enabled': True, 'sheet_mode': 'new_tab', 'history_limit': 100, 'error_limit': 50})
    cfg.setdefault('history', [])
    cfg.setdefault('errors', [])
    cfg.setdefault('input_wait', {})
    cfg.setdefault('connected_at', '')
    cfg.setdefault('connected_by', 0)
    cfg.setdefault('updated_at', _v149_now_iso())
    return cfg

# --- google:0011 · from 07_state_web.py:2372 · public _v149_google_master_key ---
def _v149_google_master_key() -> bytes:
    raw = str(_v149_os.getenv('TENANT_GOOGLE_MASTER_KEY') or _v149_os.getenv('GOOGLE_TENANT_MASTER_KEY') or '').strip()
    if len(raw) < 24:
        raise RuntimeError('Для подключения Google пространств задайте в Render секрет TENANT_GOOGLE_MASTER_KEY длиной не менее 24 символов')
    return _v149_hashlib.sha256(raw.encode('utf-8')).digest()

# --- google:0012 · from 07_state_web.py:2419 · public _v149_parse_google_service_json ---
def _v149_parse_google_service_json(raw: str) -> dict:
    try:
        info = _v149_json.loads(str(raw))
    except Exception as exc:
        raise RuntimeError(f'JSON Google повреждён: {exc}')
    if not isinstance(info, dict):
        raise RuntimeError('JSON Google должен быть объектом')
    if str(info.get('type') or '') != 'service_account':
        raise RuntimeError('Нужен JSON ключ типа service_account')
    for key in ('client_email', 'private_key', 'token_uri'):
        if not str(info.get(key) or '').strip():
            raise RuntimeError(f'В Google JSON отсутствует {key}')
    return info

# --- google:0013 · from 07_state_web.py:2433 · public tenant_google_set_credentials ---
def tenant_google_set_credentials(tenant_id: str, raw: str, actor_user_id: int) -> dict:
    tid = _v149_tenant_id(tenant_id)
    info = _v149_parse_google_service_json(raw)
    cfg = tenant_google_config(tenant_id)
    cfg['credentials_sealed'] = _v149_seal_secret(_v149_json.dumps(info, ensure_ascii=False, separators=(',', ':')))
    cfg['credential_fingerprint'] = _v149_hashlib.sha256(str(info.get('client_email') or '').encode('utf-8') + str(info.get('private_key_id') or '').encode('utf-8')).hexdigest()[:20]
    cfg['service_account_email'] = str(info.get('client_email') or '')[:250]
    cfg['connected_at'] = _v149_now_iso()
    cfg['connected_by'] = int(actor_user_id or 0)
    cfg['updated_at'] = _v149_now_iso()
    cfg['input_wait'] = {}
    with _V149_GOOGLE_TOKEN_LOCK:
        for key in list(_V149_GOOGLE_TOKEN_CACHE):
            if str(key).startswith(str(tenant_id) + ':'):
                _V149_GOOGLE_TOKEN_CACHE.pop(key, None)
    tenant_google_history(tenant_id, 'account_connected', 'Google service account подключён', ok=True)
    tenant_google_persist(tid, 'tenant_google_update')
    return info

# --- google:0014 · from 07_state_web.py:2452 · public tenant_google_persist ---
def tenant_google_persist(tenant_id: str, reason: str='tenant_google') -> None:
    tid = _v149_tenant_id(tenant_id)
    save_data(data, root_only=True)
    try:
        row = tenant_get(tid) or {}
        scope_chat = int(row.get('root_chat_id') or OWNER_ID or 0)
        if scope_chat:
            schedule_delta_backup(scope_chat, delay=0.35, reason=str(reason or 'tenant_google'))
    except Exception as exc:
        try:
            log_error(f'tenant google delta schedule: {exc}')
        except Exception:
            pass

# --- google:0015 · from 07_state_web.py:2466 · public tenant_google_history ---
def tenant_google_history(tenant_id: str, action: str, detail: str='', ok: bool=True, **meta) -> None:
    cfg = tenant_google_config(tenant_id)
    row = {'at': _v149_now_iso(), 'action': str(action)[:80], 'ok': bool(ok), 'detail': str(detail or '')[:500]}
    if meta:
        row['meta'] = {str(k)[:50]: str(v)[:250] for k, v in meta.items() if k not in {'credentials', 'private_key', 'token'}}
    rows = cfg.setdefault('history', [])
    rows.append(row)
    limit = max(10, min(500, int((cfg.get('export_settings') or {}).get('history_limit', 100) or 100)))
    del rows[:-limit]
    cfg['updated_at'] = _v149_now_iso()

# --- google:0016 · from 07_state_web.py:2477 · public tenant_google_error ---
def tenant_google_error(tenant_id: str, action: str, exc) -> None:
    tid = _v149_tenant_id(tenant_id)
    cfg = tenant_google_config(tenant_id)
    message = str(exc or 'Ошибка')
    message = _v149_re.sub('-----BEGIN [^-]+-----.*?-----END [^-]+-----', '[REDACTED KEY]', message, flags=_v149_re.S)
    message = _v149_re.sub('(?i)(access_token|refresh_token|private_key|client_secret)\\s*[:=]\\s*[^,\\s]+', '\\1=[REDACTED]', message)
    rows = cfg.setdefault('errors', [])
    rows.append({'at': _v149_now_iso(), 'action': str(action)[:80], 'error': message[:1000]})
    limit = max(10, min(200, int((cfg.get('export_settings') or {}).get('error_limit', 50) or 50)))
    del rows[:-limit]
    cfg['updated_at'] = _v149_now_iso()
    try:
        tenant_google_persist(tid, 'tenant_google_update')
    except Exception:
        pass

# --- google:0017 · from 07_state_web.py:2493 · public _canon_google_service_account_info__001 ---
def _canon_google_service_account_info__001(tenant_id: str | None=None) -> dict:
    tid = _v149_tenant_id(tenant_id)
    cfg = tenant_google_config(tid, create=False)
    sealed = str(cfg.get('credentials_sealed') or '') if cfg else ''
    if sealed:
        return _v149_parse_google_service_json(_v149_open_secret(sealed))
    if tid == str(TENANT_PLATFORM_ID) and _V149_PLATFORM_GOOGLE_JSON:
        raw = _V149_PLATFORM_GOOGLE_JSON
        try:
            if raw.lstrip().startswith('{'):
                return _v149_parse_google_service_json(raw)
            return _v149_parse_google_service_json(_v149_base64.b64decode(raw).decode('utf-8'))
        except Exception as exc:
            raise RuntimeError(f'GOOGLE_SERVICE_ACCOUNT_JSON владельца платформы повреждён: {exc}')
    raise RuntimeError('Google-аккаунт этого пространства не подключён. Откройте /google')

# --- google:0018 · from 07_state_web.py:2509 · public _v149_google_id ---
def _v149_google_id(value: str, kind: str) -> str:
    raw = str(value or '').strip()
    if kind == 'sheet':
        match = _v149_re.search('/spreadsheets/d/([A-Za-z0-9_-]+)', raw)
    else:
        match = _v149_re.search('/folders/([A-Za-z0-9_-]+)', raw)
    if match:
        raw = match.group(1)
    raw = raw.split('?')[0].split('#')[0].strip().strip('/')
    if not _v149_re.fullmatch('[A-Za-z0-9_-]{10,}', raw):
        raise RuntimeError('Неверная ссылка или ID Google ' + ('таблицы' if kind == 'sheet' else 'папки'))
    return raw

# --- google:0019 · from 07_state_web.py:2522 · public _canon_google_spreadsheet_id__001 ---
def _canon_google_spreadsheet_id__001(value: str | None=None, tenant_id: str | None=None) -> str:
    if value is not None and str(value).strip():
        return _v149_google_id(str(value), 'sheet')
    tid = _v149_tenant_id(tenant_id)
    cfg = tenant_google_config(tid, create=False)
    raw = str((cfg or {}).get('spreadsheet_id') or '')
    if not raw and tid == str(TENANT_PLATFORM_ID):
        raw = _V149_PLATFORM_GOOGLE_SHEET
    if not raw:
        raise RuntimeError('Для этого пространства не выбрана Google Таблица. Откройте /google')
    return _v149_google_id(raw, 'sheet')

# --- google:0020 · from 07_state_web.py:2534 · public tenant_google_drive_folder_id ---
def tenant_google_drive_folder_id(tenant_id: str | None=None) -> str:
    tid = _v149_tenant_id(tenant_id)
    raw = str(tenant_google_config(tid, create=False).get('drive_folder_id') or '')
    if not raw:
        raise RuntimeError('Для этого пространства не выбрана папка Google Drive. Откройте /google')
    return _v149_google_id(raw, 'folder')

# --- google:0021 · from 07_state_web.py:2541 · public _canon_google_access_token__001 ---
def _canon_google_access_token__001(tenant_id: str | None=None) -> str:
    tid = _v149_tenant_id(tenant_id)
    info = _google_service_account_info(tid)
    fingerprint = _v149_hashlib.sha256((str(info.get('client_email')) + str(info.get('private_key_id'))).encode('utf-8')).hexdigest()[:20]
    cache_key = f'{tid}:{fingerprint}'
    with _V149_GOOGLE_TOKEN_LOCK:
        now = _v149_time.time()
        cached = _V149_GOOGLE_TOKEN_CACHE.get(cache_key) or {}
        if cached.get('token') and now < float(cached.get('expires_at', 0)) - 120:
            return str(cached['token'])
        header = {'alg': 'RS256', 'typ': 'JWT'}
        claims = {'iss': info['client_email'], 'scope': 'https://www.googleapis.com/auth/spreadsheets https://www.googleapis.com/auth/drive', 'aud': info.get('token_uri') or 'https://oauth2.googleapis.com/token', 'iat': int(now), 'exp': int(now) + 3600}
        signing_input = (_b64url(_v149_json.dumps(header, separators=(',', ':')).encode('utf-8')) + '.' + _b64url(_v149_json.dumps(claims, separators=(',', ':')).encode('utf-8'))).encode('ascii')
        signature = _google_sign_rs256(signing_input, info['private_key'])
        assertion = signing_input.decode('ascii') + '.' + _b64url(signature)
        response = _google_request_guarded('oauth', requests.post, info.get('token_uri') or 'https://oauth2.googleapis.com/token', data={'grant_type': 'urn:ietf:params:oauth:grant-type:jwt-bearer', 'assertion': assertion}, timeout=30, attempts=2)
        if response.status_code >= 300:
            raise RuntimeError(f'Google OAuth {response.status_code}: {response.text[:500]}')
        payload = response.json()
        token = str(payload.get('access_token') or '')
        if not token:
            raise RuntimeError('Google OAuth не вернул access_token')
        _V149_GOOGLE_TOKEN_CACHE[cache_key] = {'token': token, 'expires_at': now + int(payload.get('expires_in', 3600) or 3600)}
        return token

# --- google:0022 · from 07_state_web.py:2566 · public _canon_google_sheets_create_category_report__001 ---
def _canon_google_sheets_create_category_report__001(title: str, rows: list[list], layout: str='category', annotations_override: dict | None=None, include_annotations: bool=True, tenant_id: str | None=None, target_chat_id: int | None=None) -> str:
    if not callable(_V149_BASE_GOOGLE_SHEETS_CREATE):
        raise RuntimeError('Модуль Google Sheets не загружен')
    tid = _v149_tenant_id(tenant_id, target_chat_id)
    if target_chat_id is not None and (not _v149_chat_belongs_to_tenant(int(target_chat_id), tid)):
        raise RuntimeError('Google export blocked: target chat is not connected to this space')
    cfg = tenant_google_config(tid)
    if not bool((cfg.get('export_settings') or {}).get('sheet_enabled', True)):
        raise RuntimeError('Выгрузка в Google Sheets выключена для этого пространства')
    try:
        with tenant_google_context(tid):
            url = _V149_BASE_GOOGLE_SHEETS_CREATE(title, rows, layout=layout, annotations_override=annotations_override, include_annotations=include_annotations)
        tenant_google_history(tid, 'sheets_export', title, ok=True, chat_id=target_chat_id or 0, url=url)
        tenant_google_persist(tid, 'tenant_google_update')
        return url
    except Exception as exc:
        tenant_google_error(tid, 'sheets_export', exc)
        raise

# --- google:0023 · from 07_state_web.py:2585 · public tenant_google_upload_export ---
def tenant_google_upload_export(local_path: str, display_name: str, target_chat_id: int, mime_type: str | None=None) -> str:
    tid = _v149_tenant_id(target_chat_id=target_chat_id)
    if not _v149_chat_belongs_to_tenant(int(target_chat_id), tid):
        raise RuntimeError('Google Drive export blocked: target chat is not connected to this space')
    cfg = tenant_google_config(tid)
    if not bool((cfg.get('export_settings') or {}).get('drive_enabled', True)):
        raise RuntimeError('Выгрузка в Google Drive выключена для этого пространства')
    folder_id = tenant_google_drive_folder_id(tid)
    token = _google_access_token(tid)
    mime_type = str(mime_type or _v149_mimetypes.guess_type(display_name)[0] or 'application/octet-stream')
    headers = {'Authorization': f'Bearer {token}'}
    metadata = {'name': str(display_name or _v149_Path(local_path).name)[:240], 'parents': [folder_id], 'appProperties': {'tenant_id': tid, 'source_chat_id': str(int(target_chat_id))}}
    try:
        with open(local_path, 'rb') as fh:
            response = _google_request_guarded('drive_upload', requests.post, 'https://www.googleapis.com/upload/drive/v3/files', headers=headers, params={'uploadType': 'multipart', 'fields': 'id,name,webViewLink,parents'}, files={'metadata': (None, _v149_json.dumps(metadata, ensure_ascii=False), 'application/json; charset=UTF-8'), 'file': (metadata['name'], fh, mime_type)}, timeout=120, attempts=1)
        if response.status_code >= 300:
            raise RuntimeError(f'Google Drive upload {response.status_code}: {response.text[:700]}')
        payload = response.json()
        file_id = str(payload.get('id') or '')
        url = str(payload.get('webViewLink') or (f'https://drive.google.com/file/d/{file_id}/view' if file_id else ''))
        tenant_google_history(tid, 'drive_export', metadata['name'], ok=True, chat_id=target_chat_id, file_id=file_id)
        tenant_google_persist(tid, 'tenant_google_update')
        return url
    except Exception as exc:
        tenant_google_error(tid, 'drive_export', exc)
        raise

# --- google:0024 · from 07_state_web.py:2612 · public tenant_google_create_spreadsheet ---
def tenant_google_create_spreadsheet(tenant_id: str, title: str='Финансы бота') -> str:
    """v244: create a usable spreadsheet even when no Drive folder was configured.

    If a folder exists we place the file there. Otherwise Google creates it in the
    service account Drive root. When an owner/share email is known, grant writer
    access immediately so the owner can open the newly created file.
    """
    tid = _v149_tenant_id(tenant_id)
    token = _google_access_token(tid)
    cfg = tenant_google_config(tid)
    folder_raw = str(cfg.get('drive_folder_id') or '').strip()
    folder_id = _v149_google_id(folder_raw, 'folder') if folder_raw else ''
    headers = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}
    metadata = {'name': str(title or 'Финансы бота')[:200], 'mimeType': 'application/vnd.google-apps.spreadsheet', 'appProperties': {'tenant_id': tid, 'created_by_bot_version': VERSION}}
    if folder_id:
        metadata['parents'] = [folder_id]
    response = _google_request_guarded('drive_create_sheet_v244', requests.post, 'https://www.googleapis.com/drive/v3/files', headers=headers, params={'fields': 'id,name,webViewLink,parents'}, json=metadata, timeout=60, attempts=1)
    if response.status_code >= 300 and (not folder_id):
        sheet_create = _google_request_guarded('sheets_create_spreadsheet_v244', requests.post, 'https://sheets.googleapis.com/v4/spreadsheets', headers=headers, json={'properties': {'title': str(title or 'Финансы бота')[:200]}}, timeout=60, attempts=1)
        if sheet_create.status_code < 300:
            sp = sheet_create.json()
            sid = str(sp.get('spreadsheetId') or '')
            response = type('_V244GoogleCreateResponse', (), {'status_code': 200, 'json': lambda self, _sid=sid, _title=str((sp.get('properties') or {}).get('title') or title): {'id': _sid, 'name': _title, 'webViewLink': f'https://docs.google.com/spreadsheets/d/{_sid}/edit'}, 'text': ''})()
    if response.status_code >= 300:
        exc = RuntimeError(f'Google create spreadsheet {response.status_code}: {response.text[:700]}')
        tenant_google_error(tid, 'create_spreadsheet', exc)
        raise exc
    payload = response.json()
    spreadsheet_id = _v149_google_id(str(payload.get('id') or ''), 'sheet')
    cfg['spreadsheet_id'] = spreadsheet_id
    cfg['spreadsheet_title'] = str(payload.get('name') or title)[:200]
    cfg['updated_at'] = _v149_now_iso()
    share_email = str(cfg.get('owner_google_email') or '').strip()
    if not share_email and tid == str(TENANT_PLATFORM_ID):
        share_email = str(_V149_PLATFORM_GOOGLE_SHARE or '').strip()
    share_note = ''
    if share_email:
        try:
            perm = _google_request_guarded('drive_share_sheet_v244', requests.post, f'https://www.googleapis.com/drive/v3/files/{spreadsheet_id}/permissions', headers=headers, params={'sendNotificationEmail': 'false', 'fields': 'id'}, json={'type': 'user', 'role': 'writer', 'emailAddress': share_email}, timeout=45, attempts=1)
            if perm.status_code < 300:
                share_note = f'; shared={share_email}'
            else:
                share_note = f'; share_warning={perm.status_code}'
                tenant_google_error(tid, 'share_created_spreadsheet', RuntimeError(perm.text[:500]))
        except Exception as exc:
            share_note = '; share_warning=exception'
            try:
                tenant_google_error(tid, 'share_created_spreadsheet', exc)
            except Exception:
                pass
    tenant_google_history(tid, 'create_spreadsheet_v244', cfg['spreadsheet_title'] + share_note, ok=True, spreadsheet_id=spreadsheet_id, folder_id=folder_id or 'root')
    tenant_google_persist(tid, 'tenant_google_update')
    return str(payload.get('webViewLink') or f'https://docs.google.com/spreadsheets/d/{spreadsheet_id}/edit')

# --- google:0025 · from 07_state_web.py:2666 · public tenant_google_test ---
def tenant_google_test(tenant_id: str) -> tuple[bool, str]:
    tid = _v149_tenant_id(tenant_id)
    try:
        token = _google_access_token(tid)
        headers = {'Authorization': f'Bearer {token}'}
        parts = []
        folder_id = str(tenant_google_config(tid).get('drive_folder_id') or '')
        if folder_id:
            response = _google_request_guarded('drive_folder_test', requests.get, f"https://www.googleapis.com/drive/v3/files/{_v149_google_id(folder_id, 'folder')}", headers=headers, params={'fields': 'id,name,mimeType,trashed'}, timeout=30, attempts=2)
            if response.status_code >= 300:
                raise RuntimeError(f'Drive folder {response.status_code}: {response.text[:500]}')
            payload = response.json()
            tenant_google_config(tid)['drive_folder_name'] = str(payload.get('name') or '')[:200]
            parts.append('Drive: доступ есть')
        sheet_raw = str(tenant_google_config(tid).get('spreadsheet_id') or '')
        if not sheet_raw and tid == str(TENANT_PLATFORM_ID):
            sheet_raw = _V149_PLATFORM_GOOGLE_SHEET
        if sheet_raw:
            sid = _v149_google_id(sheet_raw, 'sheet')
            response = _google_request_guarded('sheet_test', requests.get, f'https://sheets.googleapis.com/v4/spreadsheets/{sid}', headers=headers, params={'fields': 'spreadsheetId,properties.title'}, timeout=30, attempts=2)
            if response.status_code >= 300:
                raise RuntimeError(f'Sheets {response.status_code}: {response.text[:500]}')
            payload = response.json()
            tenant_google_config(tid)['spreadsheet_title'] = str((payload.get('properties') or {}).get('title') or '')[:200]
            parts.append('Sheets: доступ есть')
        if not parts:
            parts.append('Аккаунт подключён; задайте таблицу и папку')
        tenant_google_history(tid, 'connection_test', '; '.join(parts), ok=True)
        tenant_google_persist(tid, 'tenant_google_update')
        return (True, '✅ ' + '; '.join(parts))
    except Exception as exc:
        tenant_google_error(tid, 'connection_test', exc)
        return (False, '❌ ' + str(exc)[:700])

# --- google:0026 · from 07_state_web.py:2706 · public tenant_google_status_text ---
def tenant_google_status_text(tenant_id: str) -> str:
    tid = _v149_tenant_id(tenant_id)
    row = tenant_get(tid) or {}
    cfg = tenant_google_config(tid)
    env_fallback = tid == str(TENANT_PLATFORM_ID) and (not cfg.get('credentials_sealed')) and bool(_V149_PLATFORM_GOOGLE_JSON)
    account = str(cfg.get('service_account_email') or ('Render Environment' if env_fallback else 'не подключён'))
    sheet = str(cfg.get('spreadsheet_title') or '')
    folder = str(cfg.get('drive_folder_name') or '')
    return f"☁️ GOOGLE · {row.get('name') or tid}\n\nАккаунт: {account}\nGoogle владельца: {cfg.get('owner_google_email') or 'не указан'}\nТаблица: {sheet or _v149_mask_id(cfg.get('spreadsheet_id') or (_V149_PLATFORM_GOOGLE_SHEET if env_fallback else ''))}\nПапка Drive: {folder or _v149_mask_id(cfg.get('drive_folder_id'))}\nВыгрузка Sheets: {('включена' if bool((cfg.get('export_settings') or {}).get('sheet_enabled', True)) else 'выключена')}\nВыгрузка Drive: {('включена' if bool((cfg.get('export_settings') or {}).get('drive_enabled', True)) else 'выключена')}\nИстория: {len(cfg.get('history') or [])}\nОшибки: {len(cfg.get('errors') or [])}\n\nДанные, токены, таблица, папка, история и ошибки принадлежат только этому пространству.\nДля подключения нужен JSON ключ service_account и общий мастер-ключ TENANT_GOOGLE_MASTER_KEY в Render."

# --- google:0027 · from 07_state_web.py:2716 · public tenant_google_keyboard ---
def tenant_google_keyboard(tenant_id: str):
    tid = str(tenant_id)
    cfg = tenant_google_config(tid)
    kb = types.InlineKeyboardMarkup(row_width=1)
    kb.row(IB('🔑 Подключить / заменить аккаунт', callback_data='v149:google:connect'))
    kb.row(IB('📊 Указать Google Таблицу', callback_data='v149:google:sheet'))
    kb.row(IB('📁 Указать папку Google Drive', callback_data='v149:google:folder'))
    kb.row(IB('👤 Указать email Google владельца', callback_data='v149:google:owner_email'))
    settings = cfg.get('export_settings') or {}
    kb.row(IB(f"{('✅' if settings.get('sheet_enabled', True) else '⬜')} 📊 Выгрузка Sheets: {('ВКЛ' if settings.get('sheet_enabled', True) else 'ВЫКЛ')}", callback_data='v149:google:toggle_sheet'))
    kb.row(IB(f"{('✅' if settings.get('drive_enabled', True) else '⬜')} 📁 Выгрузка Drive: {('ВКЛ' if settings.get('drive_enabled', True) else 'ВЫКЛ')}", callback_data='v149:google:toggle_drive'))
    kb.row(IB('➕ Создать таблицу в папке', callback_data='v149:google:create_sheet'))
    kb.row(IB('🧪 Проверить подключение', callback_data='v149:google:test'))
    kb.row(IB(f"📜 История ({len(cfg.get('history') or [])})", callback_data='v149:google:history'), IB(f"⚠️ Ошибки ({len(cfg.get('errors') or [])})", callback_data='v149:google:errors'))
    kb.row(IB('🧹 Отключить Google', callback_data='v149:google:disconnect_confirm'))
    return kb

# --- google:0028 · from 07_state_web.py:2733 · public _canon_v149_google_wait__001 ---
def _canon_v149_google_wait__001(tenant_id: str, kind: str, chat_id: int, user_id: int) -> None:
    tid = _v149_tenant_id(tenant_id)
    cfg = tenant_google_config(tid)
    cfg['input_wait'] = {'kind': str(kind), 'chat_id': int(chat_id), 'user_id': int(user_id), 'expires_at': _v149_time.time() + 900}
    cfg['updated_at'] = _v149_now_iso()
    tenant_google_persist(tid, 'tenant_google_update')

# --- google:0029 · from 07_state_web.py:2740 · public _v149_google_can_manage ---
def _v149_google_can_manage(chat_id: int, user_id: int, owner_only: bool=True) -> tuple[bool, str]:
    tid = str(tenant_id_for_chat(int(chat_id), create=True, actor_user_id=int(user_id)) or TENANT_PLATFORM_ID)
    return (bool(tenant_can_manage(int(user_id), tid, owner_only=owner_only)), tid)

# --- google:0030 · from 07_state_web.py:2744 · public _canon_tenant_google_handle_message__001 ---
def _canon_tenant_google_handle_message__001(msg) -> bool:
    """Called near the top of the common non-command message router."""
    try:
        chat_id = int(msg.chat.id)
        user_id = _v149_actor_id(msg)
        tid = str(tenant_id_for_chat(chat_id, create=False) or '')
        if not tid:
            return False
        cfg = tenant_google_config(tid, create=False)
        wait = (cfg or {}).get('input_wait') or {}
        if not wait:
            return False
        if not tenant_can_manage(user_id, tid, owner_only=True):
            return False
        if not wait or int(wait.get('chat_id') or 0) != chat_id or int(wait.get('user_id') or 0) != user_id:
            return False
        if _v149_time.time() > float(wait.get('expires_at') or 0):
            cfg['input_wait'] = {}
            tenant_google_persist(tid, 'tenant_google_update')
            return False
        kind = str(wait.get('kind') or '')
        if kind == 'credentials':
            if str(getattr(msg, 'content_type', '')) != 'document':
                send_and_auto_delete(chat_id, 'Пришлите JSON-файл service_account как документ.', 12)
                return True
            document = getattr(msg, 'document', None)
            if not document or int(getattr(document, 'file_size', 0) or 0) > 250000:
                send_and_auto_delete(chat_id, 'JSON-файл отсутствует или слишком большой.', 12)
                return True
            filename = str(getattr(document, 'file_name', '') or '').lower()
            if filename and (not filename.endswith('.json')):
                send_and_auto_delete(chat_id, 'Нужен файл с расширением .json.', 12)
                return True
            file_info = bot.get_file(document.file_id)
            raw_bytes = bot.download_file(file_info.file_path)
            raw = bytes(raw_bytes).decode('utf-8')
            info = tenant_google_set_credentials(tid, raw, user_id)
            try:
                bot.delete_message(chat_id, msg.message_id)
            except Exception:
                pass
            bot.send_message(chat_id, f"✅ Google-аккаунт подключён: {info.get('client_email')}\n\nТеперь укажите свою таблицу и папку Drive через /google.")
            return True
        if str(getattr(msg, 'content_type', '')) != 'text':
            send_and_auto_delete(chat_id, 'Пришлите ссылку или ID текстом.', 10)
            return True
        value = str(getattr(msg, 'text', '') or '').strip()
        if kind == 'sheet':
            cfg['spreadsheet_id'] = _v149_google_id(value, 'sheet')
            cfg['spreadsheet_title'] = ''
            action = 'sheet_configured'
            text = '✅ Google Таблица сохранена.'
        elif kind == 'folder':
            cfg['drive_folder_id'] = _v149_google_id(value, 'folder')
            cfg['drive_folder_name'] = ''
            action = 'drive_folder_configured'
            text = '✅ Папка Google Drive сохранена.'
        elif kind == 'owner_email':
            if not _v149_re.fullmatch('[^@\\s]+@[^@\\s]+\\.[^@\\s]+', value):
                raise RuntimeError('Неверный email')
            cfg['owner_google_email'] = value[:250]
            action = 'owner_email_configured'
            text = '✅ Email владельца Google сохранён.'
        else:
            return False
        cfg['input_wait'] = {}
        cfg['updated_at'] = _v149_now_iso()
        tenant_google_history(tid, action, text, ok=True)
        tenant_google_persist(tid, 'tenant_google_update')
        try:
            bot.delete_message(chat_id, msg.message_id)
        except Exception:
            pass
        bot.send_message(chat_id, text, reply_markup=tenant_google_keyboard(tid))
        return True
    except Exception as exc:
        try:
            tid = str(tenant_id_for_chat(int(msg.chat.id), create=False) or TENANT_PLATFORM_ID)
            tenant_google_error(tid, 'input', exc)
            send_and_auto_delete(int(msg.chat.id), '❌ ' + str(exc)[:700], 20)
        except Exception:
            pass
        return True

# --- google:0031 · from 07_state_web.py:2828 · public _v149_google_history_text ---
def _v149_google_history_text(tenant_id: str, errors: bool=False) -> str:
    cfg = tenant_google_config(tenant_id)
    rows = list(cfg.get('errors' if errors else 'history') or [])[-20:]
    title = '⚠️ ОШИБКИ GOOGLE' if errors else '📜 ИСТОРИЯ GOOGLE'
    if not rows:
        return title + '\n\nПока пусто.'
    lines = [title, '']
    for row in reversed(rows):
        if errors:
            lines.append(f"{row.get('at')} · {row.get('action')}\n{row.get('error')}")
        else:
            mark = '✅' if row.get('ok') else '❌'
            lines.append(f"{mark} {row.get('at')} · {row.get('action')}\n{row.get('detail')}")
    return '\n\n'.join(lines)[:3900]

# --- google:0032 · from 08_reliability_tasks.py:8082 · public _v251_google_formula_canonical ---
def _v251_google_formula_canonical(formula) -> str:
    """Canonicalize only transformations Google itself performs harmlessly.

    Google Sheets rewrites a one-cell SUM range such as SUM(C38:C38) to
    SUM(C38). Those formulas are semantically identical, so generation and
    verification must agree on one representation. We intentionally keep this
    normalization narrow instead of trying to parse arbitrary Sheets formulas.
    """
    text = str(formula or '').strip().lstrip('=').strip()
    if not text:
        return text
    try:
        pattern = r'(?i)\bSUM\(\s*(\$?[A-Z]{1,3}\$?\d+)\s*:\s*\1\s*\)'
        text = re.sub(pattern, lambda m: f'SUM({m.group(1)})', text)
    except Exception:
        pass
    return text

# --- google:0033 · from 08_reliability_tasks.py:8550 · public _v167_google_schedule_cfg ---
def _v167_google_schedule_cfg(target_chat_id: int, create: bool=True) -> dict:
    store = get_chat_store(int(target_chat_id))
    cfg = store.get('google_thuwed_v167')
    if not isinstance(cfg, dict):
        if not create:
            return {}
        cfg = {}
        store['google_thuwed_v167'] = cfg
    cfg.setdefault('enabled', True)
    cfg.setdefault('time', '05:01')
    if str(cfg.get('mode') or '') not in {'manual', 'change', 'm15', 'h1', 'd0001', 'd0501'}:
        if not bool(cfg.get('enabled', True)):
            cfg['mode'] = 'manual'
        else:
            cfg['mode'] = 'd0001' if str(cfg.get('time') or '05:01') == '00:01' else 'd0501'
    cfg['enabled'] = str(cfg.get('mode')) != 'manual'
    if str(cfg.get('mode')) == 'd0001':
        cfg['time'] = '00:01'
    if str(cfg.get('mode')) == 'd0501':
        cfg['time'] = '05:01'
    legacy_schema = int(cfg.get('schema', 1) or 1)
    cfg.setdefault('last_run_key', '')
    if 'last_success_key' not in cfg:
        cfg['last_success_key'] = '' if legacy_schema < 3 else str(cfg.get('last_run_key') or '')
    cfg.setdefault('last_attempt_key', '')
    cfg.setdefault('last_attempt_at', '')
    cfg.setdefault('pending_run_key', '')
    cfg.setdefault('pending_since_ts', 0.0)
    cfg.setdefault('retry_count', 0)
    cfg.setdefault('next_retry_ts', 0.0)
    cfg.setdefault('last_target_day', '')
    cfg.setdefault('last_target_period', '')
    cfg.setdefault('last_ok_at', '')
    cfg.setdefault('last_error', '')
    cfg.setdefault('last_period', '')
    cfg['schema'] = max(3, int(cfg.get('schema', 1) or 1))
    return cfg

# --- google:0034 · from 08_reliability_tasks.py:8649 · public _v167_google_color_format ---
def _v167_google_color_format(row, r_idx: int, c_idx: int, max_cols: int, layout: str, annotations: dict):
    value = row[c_idx - 1] if c_idx - 1 < len(row) else ''
    row_is_blank = not any((_excel_nonempty(v) for v in row))
    first = str(row[0] if row else '').strip().casefold()
    second = str(row[1] if len(row) > 1 else '').strip().casefold()
    fmt = {'verticalAlignment': 'TOP', 'wrapStrategy': 'CLIP' if c_idx == 2 else 'WRAP', 'borders': {side: {'style': 'SOLID', 'color': {'red': 0.65, 'green': 0.65, 'blue': 0.65}} for side in ('top', 'bottom', 'left', 'right')}}
    if isinstance(value, (int, float)) or (isinstance(value, dict) and value.get('formula')):
        fmt['numberFormat'] = {'type': 'NUMBER', 'pattern': '#,##0'}
    if first == 'ars':
        fmt.update({'textFormat': {'bold': True}, 'backgroundColor': {'red': 0.78, 'green': 0.94, 'blue': 0.81}})
    elif first == 'usd':
        fmt.update({'textFormat': {'bold': True}, 'backgroundColor': {'red': 0.72, 'green': 0.86, 'blue': 1.0}})
    elif first in {'дата', 'date'}:
        fmt.update({'textFormat': {'bold': True}, 'backgroundColor': _google_category_fill(c_idx - 1)})
    elif row_is_blank:
        fmt['backgroundColor'] = {'red': 1.0, 'green': 0.6, 'blue': 0.0}
    elif first in {'расход', 'сумма по статьям'} or second in {'расход', 'сумма по статьям'}:
        fmt.update({'textFormat': {'bold': True}, 'backgroundColor': {'red': 1.0, 'green': 0.55, 'blue': 0.55}})
    elif first in {'приход', 'приход за период'} or second in {'приход', 'приход за период'}:
        fmt.update({'textFormat': {'bold': True}, 'backgroundColor': {'red': 0.55, 'green': 0.78, 'blue': 1.0}})
    elif first in {'остаток с прошлого раза', 'остаток на руках', 'гомонковые', 'остаток в обороте'} or second in {'остаток с прошлого раза', 'остаток на руках', 'гомонковые', 'остаток в обороте'}:
        fmt.update({'textFormat': {'bold': True}, 'backgroundColor': {'red': 0.55, 'green': 0.85, 'blue': 0.55}})
    elif first == 'расход еды на человека в сутки' or second == 'расход еды на человека в сутки':
        fmt.update({'textFormat': {'bold': True}, 'backgroundColor': {'red': 0.74, 'green': 0.82, 'blue': 1.0}})
    elif layout == 'category' and c_idx >= 4 and _excel_nonempty(value):
        fmt['backgroundColor'] = _google_category_fill(c_idx - 1)
    return fmt

# --- google:0035 · from 08_reliability_tasks.py:8677 · public _v244_google_try_reconcile_stale_restore_gate ---
def _v244_google_try_reconcile_stale_restore_gate() -> bool:
    """Repair only the known stale CONFIG-binding gate after a verified MEGA restore.

    This deliberately does NOT waive a failed/missing database restore.  It is limited
    to the case where Data Constitution verifies the recovered data but the old config
    generation/hash binding is stale.
    """
    try:
        state = globals().get('_RUNTIME_STATE') or {}
        if not isinstance(state, dict) or not bool(state.get('restore_attempted')) or state.get('restore_ok') is not False:
            return False
        detail = str(state.get('restore_detail') or '').casefold()
        if 'config guard' not in detail and 'config binding' not in detail and ('binding mismatch' not in detail):
            return False
        if bool(globals().get('RESTORE_GUARD_ACTIVE', False)):
            return False
        q = globals().get('constitution_quarantine_active')
        if callable(q) and bool(q()):
            return False
        verify = globals().get('constitution_boot_verify_after_restore')
        if callable(verify):
            rep = verify() or {}
            if not bool(rep.get('ok')):
                return False
        bind = globals().get('config_guard_bind_recovered_state_v242')
        if not callable(bind):
            return False
        bind()
        boot_verify = globals().get('config_guard_boot_verify_v234')
        if callable(boot_verify):
            rep2 = boot_verify() or {}
            if not bool(rep2.get('ok')):
                return False
        heal = globals().get('_v243_mark_runtime_restore_healthy')
        if callable(heal):
            heal('google_config_binding_reconciled_v244', remote_confirmed=False, generation='RECOVERED')
        try:
            bot_journal('google_restore_gate_reconciled_v244', int(OWNER_ID or 0) or None, 'verified data + config binding accepted')
        except Exception:
            pass
        return True
    except Exception as exc:
        try:
            bot_journal('google_restore_gate_reconcile_failed_v244', int(OWNER_ID or 0) or None, str(exc)[:300], 'WARN')
        except Exception:
            pass
        return False

# --- google:0036 · from 08_reliability_tasks.py:8725 · public _v244_google_values_equivalent ---
def _v244_google_values_equivalent(want, got) -> bool:
    """Compare Google user-entered values semantically, not by fragile JSON type."""
    if want == got:
        return True
    try:
        wt, wv = want
        gt, gv = got
    except Exception:
        return False
    if wt == gt == 'formula':
        # v251: Google canonicalizes SUM(C38:C38) -> SUM(C38). Treat that
        # server-side rewrite as equivalent instead of failing the whole sync.
        try:
            return _v251_google_formula_canonical(wv).replace('\r\n', '\n') == _v251_google_formula_canonical(gv).replace('\r\n', '\n')
        except Exception:
            return str(wv).strip().replace('\r\n', '\n') == str(gv).strip().replace('\r\n', '\n')
    if wt == gt == 'bool':
        return bool(wv) == bool(gv)
    if wt == 'string' and gt == 'string':
        return str(wv).replace('\r\n', '\n').strip() == str(gv).replace('\r\n', '\n').strip()
    if {wt, gt}.issubset({'number', 'string'}):

        def _num(v):
            s = str(v).replace('\xa0', '').replace(' ', '').replace(',', '.').strip()
            if s == '':
                return 0.0
            return float(s)
        try:
            return abs(_num(wv) - _num(gv)) <= 1e-09
        except Exception:
            pass
    if str(wv or '').strip() == '' and str(gv or '').strip() == '':
        return True
    return False

# --- google:0037 · from 08_reliability_tasks.py:8760 · public _v244_google_resolve_or_create_spreadsheet ---
def _v244_google_resolve_or_create_spreadsheet(tid: str) -> str:
    try:
        return _google_spreadsheet_id(tenant_id=tid)
    except Exception:
        creator = globals().get('tenant_google_create_spreadsheet')
        if not callable(creator):
            raise
        row = tenant_get(tid) if callable(globals().get('tenant_get')) else {}
        creator(tid, f"Финансы · {(row or {}).get('name') or tid}")
        return _google_spreadsheet_id(tenant_id=tid)

# --- google:0038 · from 08_reliability_tasks.py:8771 · public _v239_google_recovery_write_gate ---
def _v239_google_recovery_write_gate() -> tuple[bool, str]:
    """Never let an unhealthy boot/restore overwrite a previously good Google sheet."""
    _v244_google_try_reconcile_stale_restore_gate()
    try:
        gate = globals().get('v239_external_durable_write_allowed')
        if callable(gate):
            ok, why = gate()
            if not ok:
                return (False, str(why or 'durable recovery gate'))
    except Exception:
        pass
    try:
        state = globals().get('_RUNTIME_STATE') or {}
        if isinstance(state, dict) and bool(state.get('restore_attempted')) and (state.get('restore_ok') is False):
            return (False, 'восстановление после deploy не прошло проверку')
    except Exception:
        pass
    try:
        q = globals().get('constitution_quarantine_active')
        if callable(q) and bool(q()):
            return (False, 'DATA CONSTITUTION/restore guard активен')
    except Exception:
        pass
    return (True, 'ok')

# --- google:0039 · from 08_reliability_tasks.py:8796 · public _v239_google_plain_user_value ---
def _v239_google_plain_user_value(cell: dict):
    uv = (cell or {}).get('userEnteredValue') or {}
    if not isinstance(uv, dict):
        return ''
    if 'formulaValue' in uv:
        return ('formula', str(uv.get('formulaValue') or ''))
    if 'numberValue' in uv:
        try:
            return ('number', round(float(uv.get('numberValue') or 0.0), 10))
        except Exception:
            return ('number', str(uv.get('numberValue') or ''))
    if 'boolValue' in uv:
        return ('bool', bool(uv.get('boolValue')))
    return ('string', str(uv.get('stringValue') or ''))

# --- google:0040 · from 08_reliability_tasks.py:8811 · public _v239_google_target_plain ---
def _v239_google_target_plain(value):
    uv = _google_cell_value(value)
    return _v239_google_plain_user_value({'userEnteredValue': uv})

# --- google:0041 · from 08_reliability_tasks.py:8815 · public _v239_google_sync_meta_key ---
def _v239_google_sync_meta_key(tid: str, target_chat_id: int, tab_title: str) -> str:
    raw = f'{tid}:{int(target_chat_id)}:{tab_title}'
    return hashlib.sha256(raw.encode('utf-8')).hexdigest()[:32]

# --- google:0042 · from 08_reliability_tasks.py:8819 · public _v261_google_upsert_previous ---
def _v261_google_upsert_previous(tab_title: str, rows: list[list], target_chat_id: int, layout: str = "category", annotations_override: dict | None = None) -> str:
    """v239 incremental upsert for the stable Thu-Wed tab.

    The old implementation cleared the entire sheet before every rewrite. v239 reads the
    bot-managed range, updates only changed rows/cells, appends newly appearing rows, and
    clears only a previously managed stale tail *after* the new content was verified.
    """
    gate_ok, gate_reason = _v239_google_recovery_write_gate()
    if not gate_ok:
        raise RuntimeError("Google sync blocked v239: " + gate_reason)
    target_chat_id = int(target_chat_id)
    tid = _v149_tenant_id(None, target_chat_id) if callable(globals().get("_v149_tenant_id")) else tenant_id_for_chat(target_chat_id, create=False)
    if callable(globals().get("_v149_chat_belongs_to_tenant")) and not _v149_chat_belongs_to_tenant(target_chat_id, tid):
        raise RuntimeError("Google export blocked: target chat is not connected to this space")
    cfg = tenant_google_config(tid)
    if not bool((cfg.get("export_settings") or {}).get("sheet_enabled", True)):
        raise RuntimeError("Выгрузка в Google Sheets выключена для этого пространства")
    with tenant_google_context(tid):
        token = _google_access_token(); info = _google_service_account_info(); spreadsheet_id = _v244_google_resolve_or_create_spreadsheet(str(tid))
        service_email = str(info.get("client_email") or "")
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        meta = _google_request_guarded("v239_metadata", requests.get, f"https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}", headers=headers, params={"fields": "spreadsheetId,properties.title,sheets.properties(sheetId,title,gridProperties)"}, timeout=45, attempts=2)
        if meta.status_code >= 300:
            if meta.status_code in (401,403):
                raise RuntimeError(f"Google Sheets access denied. Добавьте {service_email} как Редактор.")
            raise RuntimeError(f"Google Sheets metadata {meta.status_code}: {meta.text[:500]}")
        payload = meta.json(); sheet_id = None; grid_rows=0; grid_cols=0
        for sh in payload.get("sheets") or []:
            props = sh.get("properties") or {}
            if str(props.get("title") or "") == tab_title:
                sheet_id = int(props.get("sheetId")); gp=props.get("gridProperties") or {}; grid_rows=int(gp.get("rowCount") or 0); grid_cols=int(gp.get("columnCount") or 0); break
        max_cols = max((len(r or []) for r in rows), default=1); row_count = max(100, len(rows)+20); col_count=max(26,max_cols+3)
        created_new = False
        if sheet_id is None:
            add = _google_request_guarded("v239_add_sheet", requests.post, f"https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}:batchUpdate", headers=headers, json={"requests":[{"addSheet":{"properties":{"title":tab_title,"gridProperties":{"rowCount":row_count,"columnCount":col_count,"frozenRowCount":2}}}}]}, timeout=60, attempts=1)
            if add.status_code >= 300:
                raise RuntimeError(f"Google Sheets add tab {add.status_code}: {add.text[:500]}")
            sheet_id = int(add.json()["replies"][0]["addSheet"]["properties"]["sheetId"]); grid_rows=row_count; grid_cols=col_count; created_new=True
        annotations = dict(annotations_override or {})
        if not annotations and layout == "category":
            try:
                _styles, annotations, _freeze, _widths = _modern_category_excel_styles_comments(rows)
            except Exception:
                annotations = {}
        cell_rows=[]
        for r_idx,row0 in enumerate(rows,start=1):
            row=list(row0 or []); vals=[]
            for c_idx in range(1,max_cols+1):
                value=row[c_idx-1] if c_idx-1<len(row) else ""
                cell={"userEnteredValue":_google_cell_value(value),"userEnteredFormat":_v167_google_color_format(row,r_idx,c_idx,max_cols,layout,annotations)}
                note=str(annotations.get((r_idx,c_idx)) or "").strip()
                if note: cell["note"]=note
                vals.append(cell)
            cell_rows.append({"values":vals})

        # Read only the currently managed-sized area. This lets us diff values/notes and
        # avoids a destructive clear-first cycle.
        sync_key = _v239_google_sync_meta_key(str(tid), target_chat_id, tab_title)
        sync_meta = {}
        try: sync_meta = SQLITE.get_meta("google_sync_v239", sync_key, {}) or {}
        except Exception: sync_meta = {}
        prev_managed_rows = int((sync_meta or {}).get("managed_rows") or 0)
        prev_managed_cols = int((sync_meta or {}).get("managed_cols") or 0)
        read_rows = max(len(rows), prev_managed_rows, 1)
        read_cols = max(max_cols, prev_managed_cols, 1)
        existing_rows=[]
        try:
            escaped = str(tab_title).replace("'", "''")
            read = _google_request_guarded("v239_read_managed", requests.get, f"https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}", headers=headers, params={
                "includeGridData":"true", "ranges":f"'{escaped}'!A1:{_xlsx_col_name(read_cols)}{read_rows}",
                "fields":"sheets(data(rowData(values(userEnteredValue,note))))",
            }, timeout=60, attempts=2)
            if read.status_code < 300:
                existing_rows = (((read.json().get("sheets") or [{}])[0].get("data") or [{}])[0].get("rowData") or [])
        except Exception as exc:
            try: bot_journal("google_incremental_read_warn_v239", target_chat_id, str(exc)[:300], "WARN")
            except Exception: pass
            existing_rows=[]

        changed_indices=[]; added=0; updated=0; unchanged=0
        for idx, row0 in enumerate(rows):
            target=list(row0 or [])
            old_vals=((existing_rows[idx] or {}).get("values") or []) if idx < len(existing_rows) else []
            value_changed=False; note_changed=False
            for c in range(max_cols):
                want=_v239_google_target_plain(target[c] if c < len(target) else "")
                got=_v239_google_plain_user_value(old_vals[c] if c < len(old_vals) else {})
                if not _v244_google_values_equivalent(want, got): value_changed=True; break
            if not value_changed:
                for c in range(max_cols):
                    want_note=str(annotations.get((idx+1,c+1)) or "").strip()
                    got_note=str((old_vals[c] if c < len(old_vals) else {}).get("note") or "").strip()
                    if want_note != got_note: note_changed=True; break
            if value_changed or note_changed or created_new:
                changed_indices.append(idx)
                if idx >= len(existing_rows) or not any(_v239_google_plain_user_value(x) != ("string", "") for x in old_vals): added += 1
                else: updated += 1
            else:
                unchanged += 1

        req=[]
        if grid_rows < row_count or grid_cols < col_count:
            req.append({"updateSheetProperties":{"properties":{"sheetId":sheet_id,"gridProperties":{"rowCount":max(grid_rows,row_count),"columnCount":max(grid_cols,col_count),"frozenRowCount":2}},"fields":"gridProperties(rowCount,columnCount,frozenRowCount)"}})
        for idx in changed_indices:
            req.append({"updateCells":{"range":{"sheetId":sheet_id,"startRowIndex":idx,"endRowIndex":idx+1,"startColumnIndex":0,"endColumnIndex":max_cols},"rows":[cell_rows[idx]],"fields":"userEnteredValue,note,userEnteredFormat"}})
        # Dimensions are cheap and non-destructive; keep the old visual layout.
        req.append({"updateDimensionProperties":{"range":{"sheetId":sheet_id,"dimension":"COLUMNS","startIndex":0,"endIndex":1},"properties":{"pixelSize":95},"fields":"pixelSize"}})
        if max_cols >= 2: req.append({"updateDimensionProperties":{"range":{"sheetId":sheet_id,"dimension":"COLUMNS","startIndex":1,"endIndex":2},"properties":{"pixelSize":320},"fields":"pixelSize"}})
        if max_cols >= 3: req.append({"updateDimensionProperties":{"range":{"sheetId":sheet_id,"dimension":"COLUMNS","startIndex":2,"endIndex":max_cols},"properties":{"pixelSize":115},"fields":"pixelSize"}})
        if req:
            upd=_google_request_guarded("v239_incremental_upsert", requests.post, f"https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}:batchUpdate", headers=headers, json={"requests":req}, timeout=90, attempts=1)
            if upd.status_code >= 300:
                raise RuntimeError(f"Google Sheets incremental update {upd.status_code}: {upd.text[:500]}")

        # Verify the complete new managed range BEFORE clearing stale rows.
        escaped = str(tab_title).replace("'", "''")
        verify = _google_request_guarded("v239_verify_incremental", requests.get, f"https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}", headers=headers, params={
            "includeGridData":"true", "ranges":f"'{escaped}'!A1:{_xlsx_col_name(max_cols)}{max(1,len(rows))}",
            "fields":"sheets(data(rowData(values(userEnteredValue,note))))",
        }, timeout=60, attempts=2)
        if verify.status_code >= 300:
            raise RuntimeError(f"Google Sheets incremental verify {verify.status_code}: {verify.text[:500]}")
        vr = (((verify.json().get("sheets") or [{}])[0].get("data") or [{}])[0].get("rowData") or [])
        for idx,row0 in enumerate(rows):
            old_vals=((vr[idx] or {}).get("values") or []) if idx < len(vr) else []
            for c in range(max_cols):
                want=_v239_google_target_plain((row0 or [])[c] if c < len(row0 or []) else "")
                got=_v239_google_plain_user_value(old_vals[c] if c < len(old_vals) else {})
                if not _v244_google_values_equivalent(want, got):
                    raise RuntimeError(f"Google incremental verify mismatch row={idx+1} col={c+1}; want={want}; got={got}")

        # Only after verification may we clear the stale BOT-MANAGED tail. We never clear
        # the whole sheet and never touch rows beyond the last managed_rows marker.
        stale_tail = max(0, prev_managed_rows - len(rows))
        if stale_tail > 0:
            clear_cols=max(max_cols,prev_managed_cols,1)
            clr=_google_request_guarded("v239_clear_stale_tail", requests.post, f"https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}:batchUpdate", headers=headers, json={"requests":[{"updateCells":{"range":{"sheetId":sheet_id,"startRowIndex":len(rows),"endRowIndex":prev_managed_rows,"startColumnIndex":0,"endColumnIndex":clear_cols},"fields":"userEnteredValue,note"}}]}, timeout=60, attempts=1)
            if clr.status_code >= 300:
                raise RuntimeError(f"Google Sheets stale-tail clear {clr.status_code}: {clr.text[:500]}")

        row_hash=hashlib.sha256(json.dumps(rows,ensure_ascii=False,sort_keys=False,separators=(",",":"),default=str).encode("utf-8")).hexdigest()
        try:
            SQLITE.set_meta("google_sync_v239", sync_key, {"tab":tab_title,"tenant_id":str(tid),"chat_id":target_chat_id,"managed_rows":len(rows),"managed_cols":max_cols,"row_hash":row_hash,"synced_at":now_local().isoformat(timespec="microseconds")})
        except Exception: pass
        url=f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}/edit#gid={sheet_id}"
    try:
        tenant_google_history(tid,"thuwed_incremental_upsert_v239",tab_title,ok=True,chat_id=target_chat_id,url=url,added=added,updated=updated,unchanged=unchanged,stale_tail=stale_tail)
        tenant_google_persist(tid,"tenant_google_runtime_v239")
        try: bot_journal("google_incremental_upsert_v239",target_chat_id,f"tab={tab_title}; added={added}; updated={updated}; unchanged={unchanged}; stale_tail={stale_tail}")
        except Exception: pass
    except Exception:
        pass
    return url

# --- google:0043 · from 08_reliability_tasks.py:8973 · public _v261_google_upsert_fixed ---
def _v261_google_upsert_fixed(tab_title: str, rows: list[list], target_chat_id: int, layout: str='category', annotations_override: dict | None=None) -> str:
    """v254 non-destructive upsert for the stable Thu-Wed tab.

    Contract for an existing sheet:
    - bot values may be refreshed inside the previously managed table;
    - existing CellData.note is NEVER cleared/replaced;
    - existing userEnteredFormat is NEVER replaced (manual colors/styles survive);
    - when the bot table grows, real rows are inserted at the detected logical
      insertion point (with a safe boundary fallback), and columns at the previous
      managed boundary, so user notes/colors and content below/right are shifted,
      not overwritten;
    - a shrinking table never performs a blind tail clear.  From v252 onward a
      stored value snapshot lets us clear only values that are still exactly the
      previous bot-owned values, while notes/formatting remain untouched.
    """
    gate_ok, gate_reason = _v239_google_recovery_write_gate()
    if not gate_ok:
        raise RuntimeError('Google sync blocked v255: ' + gate_reason)
    target_chat_id = int(target_chat_id)
    tid = _v149_tenant_id(None, target_chat_id) if callable(globals().get('_v149_tenant_id')) else tenant_id_for_chat(target_chat_id, create=False)
    if callable(globals().get('_v149_chat_belongs_to_tenant')) and (not _v149_chat_belongs_to_tenant(target_chat_id, tid)):
        raise RuntimeError('Google export blocked: target chat is not connected to this space')
    cfg = tenant_google_config(tid)
    if not bool((cfg.get('export_settings') or {}).get('sheet_enabled', True)):
        raise RuntimeError('Выгрузка в Google Sheets выключена для этого пространства')

    def _plain_json(value):
        p = _v239_google_target_plain(value)
        return [p[0], p[1]]

    def _plain_from_json(value):
        try:
            if isinstance(value, (list, tuple)) and len(value) == 2:
                return (str(value[0]), value[1])
        except Exception:
            pass
        return ('string', '')

    def _is_blank_plain(value) -> bool:
        try:
            t, v = value
            return t == 'string' and str(v or '').strip() == ''
        except Exception:
            return True

    def _segments(cols):
        cols = sorted(set(int(c) for c in cols if int(c) >= 0))
        if not cols:
            return []
        out = []
        a = b = cols[0]
        for c in cols[1:]:
            if c == b + 1:
                b = c
            else:
                out.append((a, b + 1))
                a = b = c
        out.append((a, b + 1))
        return out

    def _identity_token(plain):
        try:
            t, v = plain
        except Exception:
            return ''
        if t == 'formula':
            return '=' + _v251_google_formula_canonical(v)
        if t == 'number':
            try:
                return f'{float(v):.12g}'
            except Exception:
                return str(v or '').strip()
        if t == 'bool':
            return 'TRUE' if bool(v) else 'FALSE'
        return str(v or '').replace('\r\n', '\n').strip()

    def _row_identity(plains):
        vals = [_identity_token(x) for x in list(plains or [])]
        first = vals[0] if len(vals) > 0 else ''
        second = vals[1] if len(vals) > 1 else ''
        if first or second:
            # In the financial sheet the first two columns are the stable row
            # identity (date/description or a summary label). Numeric/formula
            # totals are deliberately ignored so recalculation does not look
            # like a row replacement.
            return ('row', first.casefold(), second.casefold())
        if not any(vals):
            return ('blank',)
        return ('other', *(x.casefold() for x in vals[:3]))

    # v254: the generated period title is only a logical key. The actual Google
    # worksheet is pinned by immutable sheetId, so a user's manual tab rename
    # never makes the bot create a second tab or lose its ownership snapshot.
    sync_key = _v239_google_sync_meta_key(str(tid), target_chat_id, tab_title)
    try:
        sync_meta = SQLITE.get_meta('google_sync_v239', sync_key, {}) or {}
    except Exception:
        sync_meta = {}
    prev_managed_rows = int((sync_meta or {}).get('managed_rows') or 0)
    prev_managed_cols = int((sync_meta or {}).get('managed_cols') or 0)
    prev_snapshot = (sync_meta or {}).get('managed_values_v252')
    if not isinstance(prev_snapshot, list):
        prev_snapshot = []
    try:
        preferred_sheet_id_v254 = int((sync_meta or {}).get('sheet_id_v254') or 0)
    except Exception:
        preferred_sheet_id_v254 = 0

    with tenant_google_context(tid):
        token = _google_access_token()
        info = _google_service_account_info()
        spreadsheet_id = _v244_google_resolve_or_create_spreadsheet(str(tid))
        service_email = str(info.get('client_email') or '')
        headers = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}
        meta = _google_request_guarded('v252_metadata', requests.get, f'https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}', headers=headers, params={'fields': 'spreadsheetId,properties.title,sheets.properties(sheetId,title,gridProperties)'}, timeout=45, attempts=2)
        if meta.status_code >= 300:
            if meta.status_code in (401, 403):
                raise RuntimeError(f'Google Sheets access denied. Добавьте {service_email} как Редактор.')
            raise RuntimeError(f'Google Sheets metadata {meta.status_code}: {meta.text[:500]}')
        payload = meta.json()
        sheet_id = None
        actual_tab_title = str(tab_title)
        grid_rows = 0
        grid_cols = 0
        sheets_meta = list(payload.get('sheets') or [])

        # First choice: immutable sheetId saved by v254. Title is intentionally
        # ignored here because users are allowed to rename tabs freely.
        if preferred_sheet_id_v254:
            for sh in sheets_meta:
                props = sh.get('properties') or {}
                if int(props.get('sheetId') or 0) == preferred_sheet_id_v254:
                    sheet_id = int(props.get('sheetId'))
                    actual_tab_title = str(props.get('title') or tab_title)
                    gp = props.get('gridProperties') or {}
                    grid_rows = int(gp.get('rowCount') or 0)
                    grid_cols = int(gp.get('columnCount') or 0)
                    break

        # Compatibility with older builds / a tab that has never been renamed.
        if sheet_id is None:
            for sh in sheets_meta:
                props = sh.get('properties') or {}
                if str(props.get('title') or '') == tab_title:
                    sheet_id = int(props.get('sheetId'))
                    actual_tab_title = str(props.get('title') or tab_title)
                    gp = props.get('gridProperties') or {}
                    grid_rows = int(gp.get('rowCount') or 0)
                    grid_cols = int(gp.get('columnCount') or 0)
                    break

        # One-time v253 -> v254 migration for a tab renamed BEFORE v254 had a
        # chance to save sheetId. Match the previous managed snapshot against
        # the first two identity columns of existing tabs. Only a strong unique
        # match is accepted; otherwise we fail safe and create the logical tab.
        if sheet_id is None and prev_snapshot and prev_managed_rows > 0:
            try:
                import difflib as _v254_difflib
                old_plain_rows = []
                for prow in prev_snapshot[:prev_managed_rows]:
                    prow = prow if isinstance(prow, list) else []
                    old_plain_rows.append([_plain_from_json(prow[c]) if c < len(prow) else ('string', '') for c in range(min(2, max(1, prev_managed_cols)))])
                old_keys = [_row_identity(x) for x in old_plain_rows]
                scored = []
                probe_rows = max(1, min(prev_managed_rows, 120))
                probe_cols = max(1, min(2, prev_managed_cols or 2))
                for sh in sheets_meta:
                    props = sh.get('properties') or {}
                    cand_id = int(props.get('sheetId') or 0)
                    cand_title = str(props.get('title') or '')
                    if not cand_id or not cand_title:
                        continue
                    escaped_cand = cand_title.replace("'", "''")
                    probe = _google_request_guarded('v254_probe_renamed_tab', requests.get, f'https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}', headers=headers, params={'includeGridData': 'true', 'ranges': f"'{escaped_cand}'!A1:{_xlsx_col_name(probe_cols)}{probe_rows}", 'fields': 'sheets(data(rowData(values(userEnteredValue))))'}, timeout=30, attempts=1)
                    if probe.status_code >= 300:
                        continue
                    prowdata = ((probe.json().get('sheets') or [{}])[0].get('data') or [{}])[0].get('rowData') or []
                    cand_keys = []
                    for i in range(probe_rows):
                        vals = (prowdata[i] or {}).get('values') or [] if i < len(prowdata) else []
                        cand_keys.append(_row_identity([_v239_google_plain_user_value(vals[c] if c < len(vals) else {}) for c in range(probe_cols)]))
                    ratio = _v254_difflib.SequenceMatcher(a=old_keys[:probe_rows], b=cand_keys, autojunk=False).ratio()
                    scored.append((float(ratio), cand_id, cand_title, props.get('gridProperties') or {}))
                scored.sort(reverse=True, key=lambda x: x[0])
                best = scored[0] if scored else None
                second = scored[1][0] if len(scored) > 1 else 0.0
                if best and best[0] >= 0.72 and (best[0] - second >= 0.08 or best[0] >= 0.94):
                    _ratio, sheet_id, actual_tab_title, gp = best
                    grid_rows = int((gp or {}).get('rowCount') or 0)
                    grid_cols = int((gp or {}).get('columnCount') or 0)
                    try:
                        bot_journal('google_renamed_tab_rebound_v254', target_chat_id, f'logical={tab_title}; actual={actual_tab_title}; sheetId={sheet_id}; score={_ratio:.3f}')
                    except Exception:
                        pass
            except Exception as exc:
                try:
                    bot_journal('google_renamed_tab_probe_warn_v254', target_chat_id, str(exc)[:300], 'WARN')
                except Exception:
                    pass

        max_cols = max((len(r or []) for r in rows), default=1)
        row_count = max(100, len(rows) + 20)
        col_count = max(26, max_cols + 3)
        created_new = False
        if sheet_id is None:
            add = _google_request_guarded('v252_add_sheet', requests.post, f'https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}:batchUpdate', headers=headers, json={'requests': [{'addSheet': {'properties': {'title': tab_title, 'gridProperties': {'rowCount': row_count, 'columnCount': col_count, 'frozenRowCount': 2}}}}]}, timeout=60, attempts=1)
            if add.status_code >= 300:
                raise RuntimeError(f'Google Sheets add tab {add.status_code}: {add.text[:500]}')
            sheet_id = int(add.json()['replies'][0]['addSheet']['properties']['sheetId'])
            actual_tab_title = str(tab_title)
            grid_rows = row_count
            grid_cols = col_count
            created_new = True

        annotations = dict(annotations_override or {})
        if not annotations and layout == 'category':
            try:
                _styles, annotations, _freeze, _widths = _modern_category_excel_styles_comments(rows)
            except Exception:
                annotations = {}

        cell_rows = []
        for r_idx, row0 in enumerate(rows, start=1):
            row = list(row0 or [])
            vals = []
            for c_idx in range(1, max_cols + 1):
                value = row[c_idx - 1] if c_idx - 1 < len(row) else ''
                cell = {'userEnteredValue': _google_cell_value(value), 'userEnteredFormat': _v167_google_color_format(row, r_idx, c_idx, max_cols, layout, annotations)}
                note = str(annotations.get((r_idx, c_idx)) or '').strip()
                if note:
                    cell['note'] = note
                vals.append(cell)
            cell_rows.append({'values': vals})

        # HOTFIX v258: probe beyond the remembered managed boundary.
        # Older incremental builds could leave stale bot rows below managed_rows
        # after a failed/partial compaction. If we only read managed_rows, those
        # rows stay invisible forever and can preserve duplicate summaries /
        # broken USD formulas. The probe is read-only; user rows below the bot
        # table are never modified just because they were read.
        _probe_tail_rows_v258 = 80
        _remembered_read_rows_v258 = max(len(rows), prev_managed_rows, 1)
        if grid_rows > 0:
            read_rows = min(int(grid_rows), _remembered_read_rows_v258 + _probe_tail_rows_v258)
        else:
            read_rows = _remembered_read_rows_v258 + _probe_tail_rows_v258
        read_cols = max(max_cols, prev_managed_cols, 1)
        existing_rows = []
        try:
            escaped = str(actual_tab_title).replace("'", "''")
            read = _google_request_guarded('v252_read_managed', requests.get, f'https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}', headers=headers, params={'includeGridData': 'true', 'ranges': f"'{escaped}'!A1:{_xlsx_col_name(read_cols)}{read_rows}", 'fields': 'sheets(data(rowData(values(userEnteredValue,note))))'}, timeout=60, attempts=2)
            if read.status_code < 300:
                existing_rows = ((read.json().get('sheets') or [{}])[0].get('data') or [{}])[0].get('rowData') or []
        except Exception as exc:
            try:
                bot_journal('google_incremental_read_warn_v252', target_chat_id, str(exc)[:300], 'WARN')
            except Exception:
                pass
            existing_rows = []

        # HOTFIX v258: recover the REAL bot-table boundary from the sheet.
        # A failed older compaction could leave valid-looking bot rows below the
        # remembered managed_rows.  The strongest terminal marker of each finance
        # section is "Остаток в обороте"; the last occurrence is therefore the
        # real end of the generated table.  Anything below that boundary remains
        # user territory and is never cleared/moved by this repair.
        actual_managed_rows_v258 = int(prev_managed_rows or 0)
        repair_extra_rows_v258 = False
        try:
            for _ri, _rr in enumerate(existing_rows, start=1):
                _vals = (_rr or {}).get('values') or []
                _a = str((_v239_google_plain_user_value(_vals[0]) if len(_vals) > 0 else ('string',''))[1] or '').strip().casefold()
                _b = str((_v239_google_plain_user_value(_vals[1]) if len(_vals) > 1 else ('string',''))[1] or '').strip().casefold()
                if _a == 'остаток в обороте' or _b == 'остаток в обороте':
                    actual_managed_rows_v258 = max(actual_managed_rows_v258, int(_ri))
            repair_extra_rows_v258 = actual_managed_rows_v258 > int(prev_managed_rows or 0)
            if repair_extra_rows_v258:
                try:
                    bot_journal('google_boundary_repair_v258', target_chat_id, f'remembered={prev_managed_rows}; actual={actual_managed_rows_v258}; target={len(rows)}', 'WARN')
                except Exception:
                    pass
        except Exception:
            actual_managed_rows_v258 = int(prev_managed_rows or 0)
            repair_extra_rows_v258 = False
        old_managed_rows_v258 = max(int(prev_managed_rows or 0), int(actual_managed_rows_v258 or 0))

        # v258 migration from the temporary v256 grid. D was a bot-owned
        # generic Expense column. Deleting D shifts E+ categories, their notes,
        # colors and all user content to the right one column left intact.
        remove_v256_expense_col = False
        try:
            for _rr in existing_rows[:12]:
                _vals = (_rr or {}).get('values') or []
                _plain = [str((_v239_google_plain_user_value(_vals[i]) if i < len(_vals) else ('string',''))[1] or '').strip().casefold() for i in range(4)]
                if _plain[0] == 'дата' and _plain[1] == 'описание' and _plain[2] == 'приход' and _plain[3] == 'расход':
                    remove_v256_expense_col = True
                    break
        except Exception:
            remove_v256_expense_col = False
        prev_managed_cols_raw_v257 = prev_managed_cols
        if remove_v256_expense_col and prev_managed_cols > 3:
            prev_managed_cols = max(3, prev_managed_cols - 1)

        req = []
        if remove_v256_expense_col:
            # Preserve USD expense-cell formatting/notes while collapsing the old
            # D expense column into C. Copy only rows where old C is blank and D
            # is used; then deleting D leaves the copied C cell intact. Values are
            # subsequently regenerated from canonical finance data.
            in_usd_v257 = False
            for _ri, _rr in enumerate(existing_rows):
                _vals = (_rr or {}).get('values') or []
                _a = str((_v239_google_plain_user_value(_vals[0]) if len(_vals) > 0 else ('string',''))[1] or '').strip().upper()
                if _a == 'USD':
                    in_usd_v257 = True
                    continue
                if not in_usd_v257:
                    continue
                _c = _v239_google_plain_user_value(_vals[2] if len(_vals) > 2 else {})
                _d = _v239_google_plain_user_value(_vals[3] if len(_vals) > 3 else {})
                _d_note = str((_vals[3] if len(_vals) > 3 else {}).get('note') or '')
                if _is_blank_plain(_c) and ((not _is_blank_plain(_d)) or _d_note):
                    req.append({'copyPaste': {'source': {'sheetId': sheet_id, 'startRowIndex': _ri, 'endRowIndex': _ri + 1, 'startColumnIndex': 3, 'endColumnIndex': 4}, 'destination': {'sheetId': sheet_id, 'startRowIndex': _ri, 'endRowIndex': _ri + 1, 'startColumnIndex': 2, 'endColumnIndex': 3}, 'pasteType': 'PASTE_NORMAL', 'pasteOrientation': 'NORMAL'}})
            req.append({'deleteDimension': {'range': {'sheetId': sheet_id, 'dimension': 'COLUMNS', 'startIndex': 3, 'endIndex': 4}}})
        # Grow grid only if there is no managed boundary to insert at.  Once a
        # boundary exists, insertDimension is what protects user content below/right.
        if created_new:
            pass
        elif prev_managed_rows <= 0 and (grid_rows < row_count or grid_cols < col_count):
            req.append({'updateSheetProperties': {'properties': {'sheetId': sheet_id, 'gridProperties': {'rowCount': max(grid_rows, row_count), 'columnCount': max(grid_cols, col_count)}}, 'fields': 'gridProperties(rowCount,columnCount)'}})

        row_delta_v258 = 0 if created_new or old_managed_rows_v258 <= 0 else (len(rows) - old_managed_rows_v258)
        row_growth = max(0, row_delta_v258)
        row_shrink_v258 = max(0, -row_delta_v258)
        col_growth = 0 if created_new or prev_managed_cols <= 0 else max(0, max_cols - prev_managed_cols)
        row_insert_plan = []
        inserted_row_indices = set()
        target_to_old_row = {i: i for i in range(min(len(rows), old_managed_rows_v258))}
        row_copy_map_v258 = {}
        # v258: run logical row alignment for BOTH growth and shrink.  v257 only
        # aligned on growth, so after a duplicate disappeared the bot updated
        # individual cells in-place and could create mixed rows (old description
        # in A/B + a summary formula in C).  On shrink we compact logical rows by
        # copying the whole previous row (values + note + format) to its new slot,
        # then refresh only bot-owned values.  No physical row deletion is used,
        # so user content below the managed table never moves or disappears.
        if row_delta_v258:
            try:
                import difflib as _v258_difflib
                old_plain_rows = []
                if (not repair_extra_rows_v258) and len(prev_snapshot) >= old_managed_rows_v258:
                    for i in range(old_managed_rows_v258):
                        prow = prev_snapshot[i] if isinstance(prev_snapshot[i], list) else []
                        old_plain_rows.append([_plain_from_json(x) for x in prow])
                else:
                    for i in range(old_managed_rows_v258):
                        vals = (existing_rows[i] or {}).get('values') or [] if i < len(existing_rows) else []
                        old_plain_rows.append([_v239_google_plain_user_value(x) for x in vals[:max(prev_managed_cols, max_cols)]])
                new_plain_rows = [[_v239_google_target_plain((r or [])[c] if c < len(r or []) else '') for c in range(max_cols)] for r in rows]
                old_keys = [_row_identity(x) for x in old_plain_rows]
                new_keys = [_row_identity(x) for x in new_plain_rows]
                matcher = _v258_difflib.SequenceMatcher(a=old_keys, b=new_keys, autojunk=False)
                candidate_plan = []
                candidate_inserted = set()
                candidate_map = {}
                deleted_old = 0
                for tag, i1, i2, j1, j2 in matcher.get_opcodes():
                    old_n, new_n = i2 - i1, j2 - j1
                    if tag == 'equal':
                        for k in range(new_n):
                            candidate_map[j1 + k] = i1 + k
                    elif tag == 'insert':
                        if new_n:
                            candidate_plan.append((j1, new_n))
                            candidate_inserted.update(range(j1, j2))
                    elif tag == 'replace':
                        common = min(old_n, new_n)
                        for k in range(common):
                            candidate_map[j1 + k] = i1 + k
                        if new_n > old_n:
                            start_new = j1 + common
                            extra = new_n - old_n
                            candidate_plan.append((start_new, extra))
                            candidate_inserted.update(range(start_new, start_new + extra))
                        elif old_n > new_n:
                            deleted_old += old_n - new_n
                    elif tag == 'delete':
                        deleted_old += old_n
                planned = sum(n for _, n in candidate_plan)
                # Pure shrink (or pure growth) can be mapped deterministically.
                # Mixed delete+insert migrations remain on conservative fallback.
                if (row_shrink_v258 and planned == 0 and deleted_old == row_shrink_v258) or (row_growth and deleted_old == 0 and planned == row_growth):
                    row_insert_plan = sorted(candidate_plan)
                    inserted_row_indices = set(candidate_inserted)
                    target_to_old_row = candidate_map
                    if row_shrink_v258:
                        row_copy_map_v258 = {int(j): int(i) for j, i in candidate_map.items() if int(i) != int(j)}
            except Exception as _v258_rowdiff_exc:
                try: bot_journal('google_row_compact_warn_v258', target_chat_id, str(_v258_rowdiff_exc)[:300], 'WARN')
                except Exception: pass
                row_insert_plan = []
                row_copy_map_v258 = {}
            if row_growth and not row_insert_plan:
                # Conservative fallback for ambiguous growth: still protect all
                # user content below the previous table boundary.
                row_insert_plan = [(old_managed_rows_v258, row_growth)]
                inserted_row_indices = set(range(old_managed_rows_v258, old_managed_rows_v258 + row_growth))
                target_to_old_row = {i: i for i in range(min(len(rows), old_managed_rows_v258))}
            # For ambiguous shrink we never delete physical Google rows. Values
            # remain protected; a later clean alignment can compact them safely.
            for start_idx, count in row_insert_plan:
                req.append({'insertDimension': {'range': {'sheetId': sheet_id, 'dimension': 'ROWS', 'startIndex': start_idx, 'endIndex': start_idx + count}, 'inheritFromBefore': True}})
        if col_growth:
            req.append({'insertDimension': {'range': {'sheetId': sheet_id, 'dimension': 'COLUMNS', 'startIndex': prev_managed_cols, 'endIndex': prev_managed_cols + col_growth}, 'inheritFromBefore': True}})

        added = 0
        updated = 0
        unchanged = 0
        manual_values_preserved = 0
        manual_preserved_cells = set()

        if created_new:
            if cell_rows:
                req.append({'updateCells': {'range': {'sheetId': sheet_id, 'startRowIndex': 0, 'endRowIndex': len(rows), 'startColumnIndex': 0, 'endColumnIndex': max_cols}, 'rows': cell_rows, 'fields': 'userEnteredValue,note,userEnteredFormat'}})
                added = len(rows)
            req.append({'updateDimensionProperties': {'range': {'sheetId': sheet_id, 'dimension': 'COLUMNS', 'startIndex': 0, 'endIndex': 1}, 'properties': {'pixelSize': 95}, 'fields': 'pixelSize'}})
            if max_cols >= 2:
                req.append({'updateDimensionProperties': {'range': {'sheetId': sheet_id, 'dimension': 'COLUMNS', 'startIndex': 1, 'endIndex': 2}, 'properties': {'pixelSize': 320}, 'fields': 'pixelSize'}})
            if max_cols >= 3:
                req.append({'updateDimensionProperties': {'range': {'sheetId': sheet_id, 'dimension': 'COLUMNS', 'startIndex': 2, 'endIndex': max_cols}, 'properties': {'pixelSize': 115}, 'fields': 'pixelSize'}})
        else:
            for idx, row0 in enumerate(rows):
                target = list(row0 or [])
                # Rows added beyond the previous managed boundary are physically
                # inserted above the user's tail, so it is safe to apply bot style
                # and generated notes only to those brand-new rows.
                if idx in inserted_row_indices:
                    req.append({'updateCells': {'range': {'sheetId': sheet_id, 'startRowIndex': idx, 'endRowIndex': idx + 1, 'startColumnIndex': 0, 'endColumnIndex': max_cols}, 'rows': [cell_rows[idx]], 'fields': 'userEnteredValue,note,userEnteredFormat'}})
                    added += 1
                    continue

                old_idx = int(target_to_old_row.get(idx, idx))
                old_vals = (existing_rows[old_idx] or {}).get('values') or [] if old_idx < len(existing_rows) else []
                if idx in row_copy_map_v258 and old_idx != idx:
                    # Move the logical row as a whole so user note/color follows
                    # the finance row during compaction. Only managed columns are
                    # copied; anything to the right is untouched.
                    req.append({'copyPaste': {'source': {'sheetId': sheet_id, 'startRowIndex': old_idx, 'endRowIndex': old_idx + 1, 'startColumnIndex': 0, 'endColumnIndex': max_cols}, 'destination': {'sheetId': sheet_id, 'startRowIndex': idx, 'endRowIndex': idx + 1, 'startColumnIndex': 0, 'endColumnIndex': max_cols}, 'pasteType': 'PASTE_NORMAL', 'pasteOrientation': 'NORMAL'}})
                changed_cols = []
                # Existing columns: values only. Notes and formatting are owned by
                # the user once the cell exists and are never touched again.
                existing_col_limit = min(max_cols, prev_managed_cols if prev_managed_cols > 0 else max_cols)
                for c in range(existing_col_limit):
                    want = _v239_google_target_plain(target[c] if c < len(target) else '')
                    old_c = c + 1 if remove_v256_expense_col and c >= 3 else c
                    got = _v239_google_plain_user_value(old_vals[old_c] if old_c < len(old_vals) else {})
                    prev = None
                    if old_idx < len(prev_snapshot) and isinstance(prev_snapshot[old_idx], list) and old_c < len(prev_snapshot[old_idx]):
                        prev = _plain_from_json(prev_snapshot[old_idx][old_c])
                    google_formula_damaged_v258 = bool(isinstance(got, tuple) and len(got) == 2 and got[0] == 'formula' and '#REF!' in str(got[1] or '').upper())
                    manual_owned = prev is not None and (not google_formula_damaged_v258) and (not _v244_google_values_equivalent(got, prev)) and (not _is_blank_plain(got))
                    if manual_owned and (not _v244_google_values_equivalent(want, got)):
                        manual_values_preserved += 1
                        manual_preserved_cells.add((idx, c))
                        continue

                    # v254: Google automatically rewrites formula references when
                    # insertDimension moves rows. Our comparison was made against
                    # the PRE-insert grid, so a formula that looked unchanged can
                    # become SUM(C34) while the intended bot formula is SUM(C33).
                    # Re-assert every bot-owned formula in the same batch whenever
                    # physical rows are inserted. User-edited formulas remain safe.
                    force_formula_after_insert = bool(row_insert_plan and want[0] == 'formula' and (prev is None or _v244_google_values_equivalent(got, prev)))
                    if _v244_google_values_equivalent(want, got) and not force_formula_after_insert:
                        continue
                    if manual_owned:
                        manual_values_preserved += 1
                        manual_preserved_cells.add((idx, c))
                        continue
                    changed_cols.append(c)
                for a, b in _segments(changed_cols):
                    vals = [{'userEnteredValue': _google_cell_value(target[c] if c < len(target) else '')} for c in range(a, b)]
                    req.append({'updateCells': {'range': {'sheetId': sheet_id, 'startRowIndex': idx, 'endRowIndex': idx + 1, 'startColumnIndex': a, 'endColumnIndex': b}, 'rows': [{'values': vals}], 'fields': 'userEnteredValue'}})

                # Newly added columns are physically inserted before anything the
                # user may have placed to the right. They are blank/new, so bot
                # formatting and generated notes are safe there.
                if col_growth and max_cols > prev_managed_cols:
                    a, b = prev_managed_cols, max_cols
                    vals = cell_rows[idx]['values'][a:b]
                    if vals:
                        req.append({'updateCells': {'range': {'sheetId': sheet_id, 'startRowIndex': idx, 'endRowIndex': idx + 1, 'startColumnIndex': a, 'endColumnIndex': b}, 'rows': [{'values': vals}], 'fields': 'userEnteredValue,note,userEnteredFormat'}})

                if changed_cols or (col_growth and max_cols > prev_managed_cols):
                    updated += 1
                else:
                    unchanged += 1

            # Shrink safely: never blind-clear the old tail. We only remove an
            # old bot value if v252 has a snapshot proving the current value is
            # still exactly what the bot wrote previously. Notes/colors survive.
            stale_tail = max(0, old_managed_rows_v258 - len(rows))
            if stale_tail > 0 and repair_extra_rows_v258:
                # These rows are inside the bot's REAL terminal boundary but were
                # invisible to the old metadata. Clear only VALUES in the stale
                # bot tail; notes/colors remain untouched, and rows below the final
                # bot terminal marker are not addressed at all. This removes old
                # duplicate summaries / mixed USD rows without erasing user data.
                for idx in range(len(rows), old_managed_rows_v258):
                    old_vals = (existing_rows[idx] or {}).get('values') or [] if idx < len(existing_rows) else []
                    clear_cols = []
                    for c in range(min(max_cols, len(old_vals))):
                        got = _v239_google_plain_user_value(old_vals[c] if c < len(old_vals) else {})
                        if not _is_blank_plain(got):
                            clear_cols.append(c)
                    for a, b in _segments(clear_cols):
                        req.append({'updateCells': {'range': {'sheetId': sheet_id, 'startRowIndex': idx, 'endRowIndex': idx + 1, 'startColumnIndex': a, 'endColumnIndex': b}, 'rows': [{'values': [{} for _ in range(a, b)]}], 'fields': 'userEnteredValue'}})
            elif stale_tail > 0 and prev_snapshot:
                for idx in range(len(rows), min(old_managed_rows_v258, len(prev_snapshot))):
                    old_vals = (existing_rows[idx] or {}).get('values') or [] if idx < len(existing_rows) else []
                    clear_cols = []
                    prev_row = prev_snapshot[idx] if idx < len(prev_snapshot) and isinstance(prev_snapshot[idx], list) else []
                    for c in range(min(prev_managed_cols, len(prev_row))):
                        got = _v239_google_plain_user_value(old_vals[c] if c < len(old_vals) else {})
                        prev = _plain_from_json(prev_row[c])
                        damaged_formula_v258 = bool(isinstance(got, tuple) and len(got) == 2 and got[0] == 'formula' and '#REF!' in str(got[1] or '').upper())
                        if (not _is_blank_plain(got)) and (_v244_google_values_equivalent(got, prev) or damaged_formula_v258):
                            clear_cols.append(c)
                    for a, b in _segments(clear_cols):
                        req.append({'updateCells': {'range': {'sheetId': sheet_id, 'startRowIndex': idx, 'endRowIndex': idx + 1, 'startColumnIndex': a, 'endColumnIndex': b}, 'rows': [{'values': [{} for _ in range(a, b)]}], 'fields': 'userEnteredValue'}})

        if req:
            upd = _google_request_guarded('v252_non_destructive_upsert', requests.post, f'https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}:batchUpdate', headers=headers, json={'requests': req}, timeout=90, attempts=1)
            if upd.status_code >= 300:
                raise RuntimeError(f'Google Sheets non-destructive update {upd.status_code}: {upd.text[:500]}')

        escaped = str(actual_tab_title).replace("'", "''")
        verify = _google_request_guarded('v252_verify_incremental', requests.get, f'https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}', headers=headers, params={'includeGridData': 'true', 'ranges': f"'{escaped}'!A1:{_xlsx_col_name(max_cols)}{max(1, len(rows))}", 'fields': 'sheets(data(rowData(values(userEnteredValue,note))))'}, timeout=60, attempts=2)
        if verify.status_code >= 300:
            raise RuntimeError(f'Google Sheets incremental verify {verify.status_code}: {verify.text[:500]}')
        vr = ((verify.json().get('sheets') or [{}])[0].get('data') or [{}])[0].get('rowData') or []
        for idx, row0 in enumerate(rows):
            old_vals = (vr[idx] or {}).get('values') or [] if idx < len(vr) else []
            for c in range(max_cols):
                if (idx, c) in manual_preserved_cells:
                    continue
                want = _v239_google_target_plain((row0 or [])[c] if c < len(row0 or []) else '')
                got = _v239_google_plain_user_value(old_vals[c] if c < len(old_vals) else {})
                if not _v244_google_values_equivalent(want, got):
                    raise RuntimeError(f'Google incremental verify mismatch row={idx + 1} col={c + 1}; want={want}; got={got}')

        row_hash = hashlib.sha256(json.dumps(rows, ensure_ascii=False, sort_keys=False, separators=(',', ':'), default=str).encode('utf-8')).hexdigest()
        snapshot = [[_plain_json((row or [])[c] if c < len(row or []) else '') for c in range(max_cols)] for row in rows]
        try:
            SQLITE.set_meta('google_sync_v239', sync_key, {'tab': tab_title, 'sheet_id_v254': int(sheet_id), 'sheet_title_actual_v254': str(actual_tab_title), 'tenant_id': str(tid), 'chat_id': target_chat_id, 'managed_rows': len(rows), 'managed_cols': max_cols, 'managed_values_v252': snapshot, 'row_hash': row_hash, 'synced_at': now_local().isoformat(timespec='microseconds'), 'manual_values_preserved': manual_values_preserved})
        except Exception:
            pass
        url = f'https://docs.google.com/spreadsheets/d/{spreadsheet_id}/edit#gid={sheet_id}'

    try:
        tenant_google_history(tid, 'thuwed_non_destructive_upsert_v254', actual_tab_title, ok=True, chat_id=target_chat_id, url=url, added=added, updated=updated, unchanged=unchanged, stale_tail=stale_tail if 'stale_tail' in locals() else 0, manual_values_preserved=manual_values_preserved, row_growth=row_growth, col_growth=col_growth)
        tenant_google_persist(tid, 'tenant_google_runtime_v252')
        try:
            bot_journal('google_non_destructive_upsert_v254', target_chat_id, f'logical_tab={tab_title}; actual_tab={actual_tab_title}; sheetId={sheet_id}; added={added}; updated={updated}; unchanged={unchanged}; row_growth={row_growth}; row_shrink={row_shrink_v258}; row_copies={len(row_copy_map_v258)}; col_growth={col_growth}; manual_values_preserved={manual_values_preserved}; stale_tail_preserved={stale_tail if "stale_tail" in locals() else 0}')
        except Exception:
            pass
    except Exception:
        pass
    return url

# --- google:0044 · from 08_reliability_tasks.py:9543 · public _v261_google_upsert_new ---
def _v261_google_upsert_new(tab_title: str, rows: list[list], target_chat_id: int, layout: str='category', annotations_override: dict | None=None) -> str:
    """v260 non-destructive upsert for the stable Thu-Wed tab.

    Contract for an existing sheet:
    - bot values may be refreshed inside the previously managed table;
    - existing CellData.note is NEVER cleared/replaced;
    - existing userEnteredFormat is NEVER replaced (manual colors/styles survive);
    - when the bot table grows, real rows are inserted at the detected logical
      insertion point (with a safe boundary fallback), and columns at the previous
      managed boundary, so user notes/colors and content below/right are shifted,
      not overwritten;
    - a shrinking table never performs a blind tail clear.  From v252 onward a
      stored value snapshot lets us clear only values that are still exactly the
      previous bot-owned values, while notes/formatting remain untouched.
    - v260: a Data-Constitution snapshot/ledger lag never overwrites the stable
      worksheet. Instead a NEW recovery worksheet is created from the current
      canonical rows in the SAME tenant spreadsheet.
    """
    target_chat_id = int(target_chat_id)
    tid = _v149_tenant_id(None, target_chat_id) if callable(globals().get('_v149_tenant_id')) else tenant_id_for_chat(target_chat_id, create=False)
    if callable(globals().get('_v149_chat_belongs_to_tenant')) and (not _v149_chat_belongs_to_tenant(target_chat_id, tid)):
        raise RuntimeError('Google export blocked: target chat is not connected to this space')
    cfg = tenant_google_config(tid)
    if not bool((cfg.get('export_settings') or {}).get('sheet_enabled', True)):
        raise RuntimeError('Выгрузка в Google Sheets выключена для этого пространства')

    gate_ok, gate_reason = _v239_google_recovery_write_gate()
    if not gate_ok:
        _reason_v260 = str(gate_reason or '')
        _fallback_allowed_v260 = ('ledger is behind finance integrity' in _reason_v260 or 'snapshot rejected' in _reason_v260)
        _creator_v260 = globals().get('_google_sheets_create_category_report')
        if _fallback_allowed_v260 and callable(_creator_v260):
            _fallback_title_v260 = f"{str(tab_title or 'Чт–Ср')} · восстановление"
            # The canonical v149 creator is tenant-aware. Pass the resolved tenant
            # explicitly so a blocked child-space sync can never spill into the
            # platform spreadsheet. Keep a compatibility fallback for old creators.
            try:
                _url_v260 = _creator_v260(
                    _fallback_title_v260, rows, layout=layout,
                    annotations_override=annotations_override, include_annotations=True,
                    tenant_id=str(tid), target_chat_id=int(target_chat_id),
                )
            except TypeError:
                _ctx_v260 = globals().get('tenant_google_context')
                if callable(_ctx_v260):
                    with _ctx_v260(str(tid)):
                        _url_v260 = _creator_v260(_fallback_title_v260, rows, layout=layout, annotations_override=annotations_override, include_annotations=True)
                else:
                    _url_v260 = _creator_v260(_fallback_title_v260, rows, layout=layout, annotations_override=annotations_override, include_annotations=True)
            try:
                bot_journal('google_constitution_fallback_new_tab_v260', int(target_chat_id), f'tenant={tid}; reason={_reason_v260[:220]}; url={str(_url_v260)[:140]}', 'WARN')
            except Exception:
                pass
            try:
                log_info(f'[GOOGLE V260] stable sheet blocked; new SAME-TENANT fallback tab created chat={target_chat_id} tenant={tid}: {_reason_v260}')
            except Exception:
                pass
            return _url_v260
        raise RuntimeError('Google sync blocked v260: ' + _reason_v260)

    def _plain_json(value):
        p = _v239_google_target_plain(value)
        return [p[0], p[1]]

    def _plain_from_json(value):
        try:
            if isinstance(value, (list, tuple)) and len(value) == 2:
                return (str(value[0]), value[1])
        except Exception:
            pass
        return ('string', '')

    def _is_blank_plain(value) -> bool:
        try:
            t, v = value
            return t == 'string' and str(v or '').strip() == ''
        except Exception:
            return True

    def _segments(cols):
        cols = sorted(set(int(c) for c in cols if int(c) >= 0))
        if not cols:
            return []
        out = []
        a = b = cols[0]
        for c in cols[1:]:
            if c == b + 1:
                b = c
            else:
                out.append((a, b + 1))
                a = b = c
        out.append((a, b + 1))
        return out

    def _identity_token(plain):
        try:
            t, v = plain
        except Exception:
            return ''
        if t == 'formula':
            return '=' + _v251_google_formula_canonical(v)
        if t == 'number':
            try:
                return f'{float(v):.12g}'
            except Exception:
                return str(v or '').strip()
        if t == 'bool':
            return 'TRUE' if bool(v) else 'FALSE'
        return str(v or '').replace('\r\n', '\n').strip()

    def _row_identity(plains):
        vals = [_identity_token(x) for x in list(plains or [])]
        first = vals[0] if len(vals) > 0 else ''
        second = vals[1] if len(vals) > 1 else ''
        if first or second:
            # In the financial sheet the first two columns are the stable row
            # identity (date/description or a summary label). Numeric/formula
            # totals are deliberately ignored so recalculation does not look
            # like a row replacement.
            return ('row', first.casefold(), second.casefold())
        if not any(vals):
            return ('blank',)
        return ('other', *(x.casefold() for x in vals[:3]))

    # v254: the generated period title is only a logical key. The actual Google
    # worksheet is pinned by immutable sheetId, so a user's manual tab rename
    # never makes the bot create a second tab or lose its ownership snapshot.
    sync_key = _v239_google_sync_meta_key(str(tid), target_chat_id, tab_title)
    try:
        sync_meta = SQLITE.get_meta('google_sync_v239', sync_key, {}) or {}
    except Exception:
        sync_meta = {}
    prev_managed_rows = int((sync_meta or {}).get('managed_rows') or 0)
    prev_managed_cols = int((sync_meta or {}).get('managed_cols') or 0)
    prev_snapshot = (sync_meta or {}).get('managed_values_v252')
    if not isinstance(prev_snapshot, list):
        prev_snapshot = []
    try:
        preferred_sheet_id_v254 = int((sync_meta or {}).get('sheet_id_v254') or 0)
    except Exception:
        preferred_sheet_id_v254 = 0

    with tenant_google_context(tid):
        token = _google_access_token()
        info = _google_service_account_info()
        spreadsheet_id = _v244_google_resolve_or_create_spreadsheet(str(tid))
        service_email = str(info.get('client_email') or '')
        headers = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}
        meta = _google_request_guarded('v252_metadata', requests.get, f'https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}', headers=headers, params={'fields': 'spreadsheetId,properties.title,sheets.properties(sheetId,title,gridProperties)'}, timeout=45, attempts=2)
        if meta.status_code >= 300:
            if meta.status_code in (401, 403):
                raise RuntimeError(f'Google Sheets access denied. Добавьте {service_email} как Редактор.')
            raise RuntimeError(f'Google Sheets metadata {meta.status_code}: {meta.text[:500]}')
        payload = meta.json()
        sheet_id = None
        actual_tab_title = str(tab_title)
        grid_rows = 0
        grid_cols = 0
        sheets_meta = list(payload.get('sheets') or [])

        # First choice: immutable sheetId saved by v254. Title is intentionally
        # ignored here because users are allowed to rename tabs freely.
        if preferred_sheet_id_v254:
            for sh in sheets_meta:
                props = sh.get('properties') or {}
                if int(props.get('sheetId') or 0) == preferred_sheet_id_v254:
                    sheet_id = int(props.get('sheetId'))
                    actual_tab_title = str(props.get('title') or tab_title)
                    gp = props.get('gridProperties') or {}
                    grid_rows = int(gp.get('rowCount') or 0)
                    grid_cols = int(gp.get('columnCount') or 0)
                    break

        # Compatibility with older builds / a tab that has never been renamed.
        if sheet_id is None:
            for sh in sheets_meta:
                props = sh.get('properties') or {}
                if str(props.get('title') or '') == tab_title:
                    sheet_id = int(props.get('sheetId'))
                    actual_tab_title = str(props.get('title') or tab_title)
                    gp = props.get('gridProperties') or {}
                    grid_rows = int(gp.get('rowCount') or 0)
                    grid_cols = int(gp.get('columnCount') or 0)
                    break

        # One-time v253 -> v254 migration for a tab renamed BEFORE v254 had a
        # chance to save sheetId. Match the previous managed snapshot against
        # the first two identity columns of existing tabs. Only a strong unique
        # match is accepted; otherwise we fail safe and create the logical tab.
        if sheet_id is None and prev_snapshot and prev_managed_rows > 0:
            try:
                import difflib as _v254_difflib
                old_plain_rows = []
                for prow in prev_snapshot[:prev_managed_rows]:
                    prow = prow if isinstance(prow, list) else []
                    old_plain_rows.append([_plain_from_json(prow[c]) if c < len(prow) else ('string', '') for c in range(min(2, max(1, prev_managed_cols)))])
                old_keys = [_row_identity(x) for x in old_plain_rows]
                scored = []
                probe_rows = max(1, min(prev_managed_rows, 120))
                probe_cols = max(1, min(2, prev_managed_cols or 2))
                for sh in sheets_meta:
                    props = sh.get('properties') or {}
                    cand_id = int(props.get('sheetId') or 0)
                    cand_title = str(props.get('title') or '')
                    if not cand_id or not cand_title:
                        continue
                    escaped_cand = cand_title.replace("'", "''")
                    probe = _google_request_guarded('v254_probe_renamed_tab', requests.get, f'https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}', headers=headers, params={'includeGridData': 'true', 'ranges': f"'{escaped_cand}'!A1:{_xlsx_col_name(probe_cols)}{probe_rows}", 'fields': 'sheets(data(rowData(values(userEnteredValue))))'}, timeout=30, attempts=1)
                    if probe.status_code >= 300:
                        continue
                    prowdata = ((probe.json().get('sheets') or [{}])[0].get('data') or [{}])[0].get('rowData') or []
                    cand_keys = []
                    for i in range(probe_rows):
                        vals = (prowdata[i] or {}).get('values') or [] if i < len(prowdata) else []
                        cand_keys.append(_row_identity([_v239_google_plain_user_value(vals[c] if c < len(vals) else {}) for c in range(probe_cols)]))
                    ratio = _v254_difflib.SequenceMatcher(a=old_keys[:probe_rows], b=cand_keys, autojunk=False).ratio()
                    scored.append((float(ratio), cand_id, cand_title, props.get('gridProperties') or {}))
                scored.sort(reverse=True, key=lambda x: x[0])
                best = scored[0] if scored else None
                second = scored[1][0] if len(scored) > 1 else 0.0
                if best and best[0] >= 0.72 and (best[0] - second >= 0.08 or best[0] >= 0.94):
                    _ratio, sheet_id, actual_tab_title, gp = best
                    grid_rows = int((gp or {}).get('rowCount') or 0)
                    grid_cols = int((gp or {}).get('columnCount') or 0)
                    try:
                        bot_journal('google_renamed_tab_rebound_v254', target_chat_id, f'logical={tab_title}; actual={actual_tab_title}; sheetId={sheet_id}; score={_ratio:.3f}')
                    except Exception:
                        pass
            except Exception as exc:
                try:
                    bot_journal('google_renamed_tab_probe_warn_v254', target_chat_id, str(exc)[:300], 'WARN')
                except Exception:
                    pass

        max_cols = max((len(r or []) for r in rows), default=1)
        row_count = max(100, len(rows) + 20)
        col_count = max(26, max_cols + 3)
        created_new = False
        if sheet_id is None:
            add = _google_request_guarded('v252_add_sheet', requests.post, f'https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}:batchUpdate', headers=headers, json={'requests': [{'addSheet': {'properties': {'title': tab_title, 'gridProperties': {'rowCount': row_count, 'columnCount': col_count, 'frozenRowCount': 2}}}}]}, timeout=60, attempts=1)
            if add.status_code >= 300:
                raise RuntimeError(f'Google Sheets add tab {add.status_code}: {add.text[:500]}')
            sheet_id = int(add.json()['replies'][0]['addSheet']['properties']['sheetId'])
            actual_tab_title = str(tab_title)
            grid_rows = row_count
            grid_cols = col_count
            created_new = True

        annotations = dict(annotations_override or {})
        if not annotations and layout == 'category':
            try:
                _styles, annotations, _freeze, _widths = _modern_category_excel_styles_comments(rows)
            except Exception:
                annotations = {}

        cell_rows = []
        for r_idx, row0 in enumerate(rows, start=1):
            row = list(row0 or [])
            vals = []
            for c_idx in range(1, max_cols + 1):
                value = row[c_idx - 1] if c_idx - 1 < len(row) else ''
                cell = {'userEnteredValue': _google_cell_value(value), 'userEnteredFormat': _v167_google_color_format(row, r_idx, c_idx, max_cols, layout, annotations)}
                note = str(annotations.get((r_idx, c_idx)) or '').strip()
                if note:
                    cell['note'] = note
                vals.append(cell)
            cell_rows.append({'values': vals})

        # HOTFIX v258: probe beyond the remembered managed boundary.
        # Older incremental builds could leave stale bot rows below managed_rows
        # after a failed/partial compaction. If we only read managed_rows, those
        # rows stay invisible forever and can preserve duplicate summaries /
        # broken USD formulas. The probe is read-only; user rows below the bot
        # table are never modified just because they were read.
        _probe_tail_rows_v258 = 80
        _remembered_read_rows_v258 = max(len(rows), prev_managed_rows, 1)
        if grid_rows > 0:
            read_rows = min(int(grid_rows), _remembered_read_rows_v258 + _probe_tail_rows_v258)
        else:
            read_rows = _remembered_read_rows_v258 + _probe_tail_rows_v258
        read_cols = max(max_cols, prev_managed_cols, 1)
        existing_rows = []
        try:
            escaped = str(actual_tab_title).replace("'", "''")
            read = _google_request_guarded('v252_read_managed', requests.get, f'https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}', headers=headers, params={'includeGridData': 'true', 'ranges': f"'{escaped}'!A1:{_xlsx_col_name(read_cols)}{read_rows}", 'fields': 'sheets(data(rowData(values(userEnteredValue,note))))'}, timeout=60, attempts=2)
            if read.status_code < 300:
                existing_rows = ((read.json().get('sheets') or [{}])[0].get('data') or [{}])[0].get('rowData') or []
        except Exception as exc:
            try:
                bot_journal('google_incremental_read_warn_v252', target_chat_id, str(exc)[:300], 'WARN')
            except Exception:
                pass
            existing_rows = []

        # HOTFIX v258: recover the REAL bot-table boundary from the sheet.
        # A failed older compaction could leave valid-looking bot rows below the
        # remembered managed_rows.  The strongest terminal marker of each finance
        # section is "Остаток в обороте"; the last occurrence is therefore the
        # real end of the generated table.  Anything below that boundary remains
        # user territory and is never cleared/moved by this repair.
        actual_managed_rows_v258 = int(prev_managed_rows or 0)
        repair_extra_rows_v258 = False
        try:
            for _ri, _rr in enumerate(existing_rows, start=1):
                _vals = (_rr or {}).get('values') or []
                _a = str((_v239_google_plain_user_value(_vals[0]) if len(_vals) > 0 else ('string',''))[1] or '').strip().casefold()
                _b = str((_v239_google_plain_user_value(_vals[1]) if len(_vals) > 1 else ('string',''))[1] or '').strip().casefold()
                if _a == 'остаток в обороте' or _b == 'остаток в обороте':
                    actual_managed_rows_v258 = max(actual_managed_rows_v258, int(_ri))
            repair_extra_rows_v258 = actual_managed_rows_v258 > int(prev_managed_rows or 0)
            if repair_extra_rows_v258:
                try:
                    bot_journal('google_boundary_repair_v258', target_chat_id, f'remembered={prev_managed_rows}; actual={actual_managed_rows_v258}; target={len(rows)}', 'WARN')
                except Exception:
                    pass
        except Exception:
            actual_managed_rows_v258 = int(prev_managed_rows or 0)
            repair_extra_rows_v258 = False
        old_managed_rows_v258 = max(int(prev_managed_rows or 0), int(actual_managed_rows_v258 or 0))

        # v258 migration from the temporary v256 grid. D was a bot-owned
        # generic Expense column. Deleting D shifts E+ categories, their notes,
        # colors and all user content to the right one column left intact.
        remove_v256_expense_col = False
        try:
            for _rr in existing_rows[:12]:
                _vals = (_rr or {}).get('values') or []
                _plain = [str((_v239_google_plain_user_value(_vals[i]) if i < len(_vals) else ('string',''))[1] or '').strip().casefold() for i in range(4)]
                if _plain[0] == 'дата' and _plain[1] == 'описание' and _plain[2] == 'приход' and _plain[3] == 'расход':
                    remove_v256_expense_col = True
                    break
        except Exception:
            remove_v256_expense_col = False
        prev_managed_cols_raw_v257 = prev_managed_cols
        if remove_v256_expense_col and prev_managed_cols > 3:
            prev_managed_cols = max(3, prev_managed_cols - 1)

        req = []
        if remove_v256_expense_col:
            # Preserve USD expense-cell formatting/notes while collapsing the old
            # D expense column into C. Copy only rows where old C is blank and D
            # is used; then deleting D leaves the copied C cell intact. Values are
            # subsequently regenerated from canonical finance data.
            in_usd_v257 = False
            for _ri, _rr in enumerate(existing_rows):
                _vals = (_rr or {}).get('values') or []
                _a = str((_v239_google_plain_user_value(_vals[0]) if len(_vals) > 0 else ('string',''))[1] or '').strip().upper()
                if _a == 'USD':
                    in_usd_v257 = True
                    continue
                if not in_usd_v257:
                    continue
                _c = _v239_google_plain_user_value(_vals[2] if len(_vals) > 2 else {})
                _d = _v239_google_plain_user_value(_vals[3] if len(_vals) > 3 else {})
                _d_note = str((_vals[3] if len(_vals) > 3 else {}).get('note') or '')
                if _is_blank_plain(_c) and ((not _is_blank_plain(_d)) or _d_note):
                    req.append({'copyPaste': {'source': {'sheetId': sheet_id, 'startRowIndex': _ri, 'endRowIndex': _ri + 1, 'startColumnIndex': 3, 'endColumnIndex': 4}, 'destination': {'sheetId': sheet_id, 'startRowIndex': _ri, 'endRowIndex': _ri + 1, 'startColumnIndex': 2, 'endColumnIndex': 3}, 'pasteType': 'PASTE_NORMAL', 'pasteOrientation': 'NORMAL'}})
            req.append({'deleteDimension': {'range': {'sheetId': sheet_id, 'dimension': 'COLUMNS', 'startIndex': 3, 'endIndex': 4}}})
        # Grow grid only if there is no managed boundary to insert at.  Once a
        # boundary exists, insertDimension is what protects user content below/right.
        if created_new:
            pass
        elif prev_managed_rows <= 0 and (grid_rows < row_count or grid_cols < col_count):
            req.append({'updateSheetProperties': {'properties': {'sheetId': sheet_id, 'gridProperties': {'rowCount': max(grid_rows, row_count), 'columnCount': max(grid_cols, col_count)}}, 'fields': 'gridProperties(rowCount,columnCount)'}})

        row_delta_v258 = 0 if created_new or old_managed_rows_v258 <= 0 else (len(rows) - old_managed_rows_v258)
        row_growth = max(0, row_delta_v258)
        row_shrink_v258 = max(0, -row_delta_v258)
        col_growth = 0 if created_new or prev_managed_cols <= 0 else max(0, max_cols - prev_managed_cols)
        row_insert_plan = []
        inserted_row_indices = set()
        target_to_old_row = {i: i for i in range(min(len(rows), old_managed_rows_v258))}
        row_copy_map_v258 = {}
        # v258: run logical row alignment for BOTH growth and shrink.  v257 only
        # aligned on growth, so after a duplicate disappeared the bot updated
        # individual cells in-place and could create mixed rows (old description
        # in A/B + a summary formula in C).  On shrink we compact logical rows by
        # copying the whole previous row (values + note + format) to its new slot,
        # then refresh only bot-owned values.  No physical row deletion is used,
        # so user content below the managed table never moves or disappears.
        if row_delta_v258:
            try:
                import difflib as _v258_difflib
                old_plain_rows = []
                if (not repair_extra_rows_v258) and len(prev_snapshot) >= old_managed_rows_v258:
                    for i in range(old_managed_rows_v258):
                        prow = prev_snapshot[i] if isinstance(prev_snapshot[i], list) else []
                        old_plain_rows.append([_plain_from_json(x) for x in prow])
                else:
                    for i in range(old_managed_rows_v258):
                        vals = (existing_rows[i] or {}).get('values') or [] if i < len(existing_rows) else []
                        old_plain_rows.append([_v239_google_plain_user_value(x) for x in vals[:max(prev_managed_cols, max_cols)]])
                new_plain_rows = [[_v239_google_target_plain((r or [])[c] if c < len(r or []) else '') for c in range(max_cols)] for r in rows]
                old_keys = [_row_identity(x) for x in old_plain_rows]
                new_keys = [_row_identity(x) for x in new_plain_rows]
                matcher = _v258_difflib.SequenceMatcher(a=old_keys, b=new_keys, autojunk=False)
                candidate_plan = []
                candidate_inserted = set()
                candidate_map = {}
                deleted_old = 0
                for tag, i1, i2, j1, j2 in matcher.get_opcodes():
                    old_n, new_n = i2 - i1, j2 - j1
                    if tag == 'equal':
                        for k in range(new_n):
                            candidate_map[j1 + k] = i1 + k
                    elif tag == 'insert':
                        if new_n:
                            candidate_plan.append((j1, new_n))
                            candidate_inserted.update(range(j1, j2))
                    elif tag == 'replace':
                        common = min(old_n, new_n)
                        for k in range(common):
                            candidate_map[j1 + k] = i1 + k
                        if new_n > old_n:
                            start_new = j1 + common
                            extra = new_n - old_n
                            candidate_plan.append((start_new, extra))
                            candidate_inserted.update(range(start_new, start_new + extra))
                        elif old_n > new_n:
                            deleted_old += old_n - new_n
                    elif tag == 'delete':
                        deleted_old += old_n
                planned = sum(n for _, n in candidate_plan)
                # Pure shrink (or pure growth) can be mapped deterministically.
                # Mixed delete+insert migrations remain on conservative fallback.
                if (row_shrink_v258 and planned == 0 and deleted_old == row_shrink_v258) or (row_growth and deleted_old == 0 and planned == row_growth):
                    row_insert_plan = sorted(candidate_plan)
                    inserted_row_indices = set(candidate_inserted)
                    target_to_old_row = candidate_map
                    if row_shrink_v258:
                        row_copy_map_v258 = {int(j): int(i) for j, i in candidate_map.items() if int(i) != int(j)}
            except Exception as _v258_rowdiff_exc:
                try: bot_journal('google_row_compact_warn_v258', target_chat_id, str(_v258_rowdiff_exc)[:300], 'WARN')
                except Exception: pass
                row_insert_plan = []
                row_copy_map_v258 = {}
            if row_growth and not row_insert_plan:
                # Conservative fallback for ambiguous growth: still protect all
                # user content below the previous table boundary.
                row_insert_plan = [(old_managed_rows_v258, row_growth)]
                inserted_row_indices = set(range(old_managed_rows_v258, old_managed_rows_v258 + row_growth))
                target_to_old_row = {i: i for i in range(min(len(rows), old_managed_rows_v258))}
            # For ambiguous shrink we never delete physical Google rows. Values
            # remain protected; a later clean alignment can compact them safely.
            for start_idx, count in row_insert_plan:
                req.append({'insertDimension': {'range': {'sheetId': sheet_id, 'dimension': 'ROWS', 'startIndex': start_idx, 'endIndex': start_idx + count}, 'inheritFromBefore': True}})
        if col_growth:
            req.append({'insertDimension': {'range': {'sheetId': sheet_id, 'dimension': 'COLUMNS', 'startIndex': prev_managed_cols, 'endIndex': prev_managed_cols + col_growth}, 'inheritFromBefore': True}})

        added = 0
        updated = 0
        unchanged = 0
        manual_values_preserved = 0
        manual_preserved_cells = set()

        if created_new:
            if cell_rows:
                req.append({'updateCells': {'range': {'sheetId': sheet_id, 'startRowIndex': 0, 'endRowIndex': len(rows), 'startColumnIndex': 0, 'endColumnIndex': max_cols}, 'rows': cell_rows, 'fields': 'userEnteredValue,note,userEnteredFormat'}})
                added = len(rows)
            req.append({'updateDimensionProperties': {'range': {'sheetId': sheet_id, 'dimension': 'COLUMNS', 'startIndex': 0, 'endIndex': 1}, 'properties': {'pixelSize': 95}, 'fields': 'pixelSize'}})
            if max_cols >= 2:
                req.append({'updateDimensionProperties': {'range': {'sheetId': sheet_id, 'dimension': 'COLUMNS', 'startIndex': 1, 'endIndex': 2}, 'properties': {'pixelSize': 320}, 'fields': 'pixelSize'}})
            if max_cols >= 3:
                req.append({'updateDimensionProperties': {'range': {'sheetId': sheet_id, 'dimension': 'COLUMNS', 'startIndex': 2, 'endIndex': max_cols}, 'properties': {'pixelSize': 115}, 'fields': 'pixelSize'}})
        else:
            for idx, row0 in enumerate(rows):
                target = list(row0 or [])
                # Rows added beyond the previous managed boundary are physically
                # inserted above the user's tail, so it is safe to apply bot style
                # and generated notes only to those brand-new rows.
                if idx in inserted_row_indices:
                    req.append({'updateCells': {'range': {'sheetId': sheet_id, 'startRowIndex': idx, 'endRowIndex': idx + 1, 'startColumnIndex': 0, 'endColumnIndex': max_cols}, 'rows': [cell_rows[idx]], 'fields': 'userEnteredValue,note,userEnteredFormat'}})
                    added += 1
                    continue

                old_idx = int(target_to_old_row.get(idx, idx))
                old_vals = (existing_rows[old_idx] or {}).get('values') or [] if old_idx < len(existing_rows) else []
                if idx in row_copy_map_v258 and old_idx != idx:
                    # Move the logical row as a whole so user note/color follows
                    # the finance row during compaction. Only managed columns are
                    # copied; anything to the right is untouched.
                    req.append({'copyPaste': {'source': {'sheetId': sheet_id, 'startRowIndex': old_idx, 'endRowIndex': old_idx + 1, 'startColumnIndex': 0, 'endColumnIndex': max_cols}, 'destination': {'sheetId': sheet_id, 'startRowIndex': idx, 'endRowIndex': idx + 1, 'startColumnIndex': 0, 'endColumnIndex': max_cols}, 'pasteType': 'PASTE_NORMAL', 'pasteOrientation': 'NORMAL'}})
                changed_cols = []
                # Existing columns: values only. Notes and formatting are owned by
                # the user once the cell exists and are never touched again.
                existing_col_limit = min(max_cols, prev_managed_cols if prev_managed_cols > 0 else max_cols)
                for c in range(existing_col_limit):
                    want = _v239_google_target_plain(target[c] if c < len(target) else '')
                    old_c = c + 1 if remove_v256_expense_col and c >= 3 else c
                    got = _v239_google_plain_user_value(old_vals[old_c] if old_c < len(old_vals) else {})
                    prev = None
                    if old_idx < len(prev_snapshot) and isinstance(prev_snapshot[old_idx], list) and old_c < len(prev_snapshot[old_idx]):
                        prev = _plain_from_json(prev_snapshot[old_idx][old_c])
                    google_formula_damaged_v258 = bool(isinstance(got, tuple) and len(got) == 2 and got[0] == 'formula' and '#REF!' in str(got[1] or '').upper())
                    manual_owned = prev is not None and (not google_formula_damaged_v258) and (not _v244_google_values_equivalent(got, prev)) and (not _is_blank_plain(got))
                    if manual_owned and (not _v244_google_values_equivalent(want, got)):
                        manual_values_preserved += 1
                        manual_preserved_cells.add((idx, c))
                        continue

                    # v254: Google automatically rewrites formula references when
                    # insertDimension moves rows. Our comparison was made against
                    # the PRE-insert grid, so a formula that looked unchanged can
                    # become SUM(C34) while the intended bot formula is SUM(C33).
                    # Re-assert every bot-owned formula in the same batch whenever
                    # physical rows are inserted. User-edited formulas remain safe.
                    force_formula_after_insert = bool(row_insert_plan and want[0] == 'formula' and (prev is None or _v244_google_values_equivalent(got, prev)))
                    if _v244_google_values_equivalent(want, got) and not force_formula_after_insert:
                        continue
                    if manual_owned:
                        manual_values_preserved += 1
                        manual_preserved_cells.add((idx, c))
                        continue
                    changed_cols.append(c)
                for a, b in _segments(changed_cols):
                    vals = [{'userEnteredValue': _google_cell_value(target[c] if c < len(target) else '')} for c in range(a, b)]
                    req.append({'updateCells': {'range': {'sheetId': sheet_id, 'startRowIndex': idx, 'endRowIndex': idx + 1, 'startColumnIndex': a, 'endColumnIndex': b}, 'rows': [{'values': vals}], 'fields': 'userEnteredValue'}})

                # Newly added columns are physically inserted before anything the
                # user may have placed to the right. They are blank/new, so bot
                # formatting and generated notes are safe there.
                if col_growth and max_cols > prev_managed_cols:
                    a, b = prev_managed_cols, max_cols
                    vals = cell_rows[idx]['values'][a:b]
                    if vals:
                        req.append({'updateCells': {'range': {'sheetId': sheet_id, 'startRowIndex': idx, 'endRowIndex': idx + 1, 'startColumnIndex': a, 'endColumnIndex': b}, 'rows': [{'values': vals}], 'fields': 'userEnteredValue,note,userEnteredFormat'}})

                if changed_cols or (col_growth and max_cols > prev_managed_cols):
                    updated += 1
                else:
                    unchanged += 1

            # Shrink safely: never blind-clear the old tail. We only remove an
            # old bot value if v252 has a snapshot proving the current value is
            # still exactly what the bot wrote previously. Notes/colors survive.
            stale_tail = max(0, old_managed_rows_v258 - len(rows))
            if stale_tail > 0 and repair_extra_rows_v258:
                # These rows are inside the bot's REAL terminal boundary but were
                # invisible to the old metadata. Clear only VALUES in the stale
                # bot tail; notes/colors remain untouched, and rows below the final
                # bot terminal marker are not addressed at all. This removes old
                # duplicate summaries / mixed USD rows without erasing user data.
                for idx in range(len(rows), old_managed_rows_v258):
                    old_vals = (existing_rows[idx] or {}).get('values') or [] if idx < len(existing_rows) else []
                    clear_cols = []
                    for c in range(min(max_cols, len(old_vals))):
                        got = _v239_google_plain_user_value(old_vals[c] if c < len(old_vals) else {})
                        if not _is_blank_plain(got):
                            clear_cols.append(c)
                    for a, b in _segments(clear_cols):
                        req.append({'updateCells': {'range': {'sheetId': sheet_id, 'startRowIndex': idx, 'endRowIndex': idx + 1, 'startColumnIndex': a, 'endColumnIndex': b}, 'rows': [{'values': [{} for _ in range(a, b)]}], 'fields': 'userEnteredValue'}})
            elif stale_tail > 0 and prev_snapshot:
                for idx in range(len(rows), min(old_managed_rows_v258, len(prev_snapshot))):
                    old_vals = (existing_rows[idx] or {}).get('values') or [] if idx < len(existing_rows) else []
                    clear_cols = []
                    prev_row = prev_snapshot[idx] if idx < len(prev_snapshot) and isinstance(prev_snapshot[idx], list) else []
                    for c in range(min(prev_managed_cols, len(prev_row))):
                        got = _v239_google_plain_user_value(old_vals[c] if c < len(old_vals) else {})
                        prev = _plain_from_json(prev_row[c])
                        damaged_formula_v258 = bool(isinstance(got, tuple) and len(got) == 2 and got[0] == 'formula' and '#REF!' in str(got[1] or '').upper())
                        if (not _is_blank_plain(got)) and (_v244_google_values_equivalent(got, prev) or damaged_formula_v258):
                            clear_cols.append(c)
                    for a, b in _segments(clear_cols):
                        req.append({'updateCells': {'range': {'sheetId': sheet_id, 'startRowIndex': idx, 'endRowIndex': idx + 1, 'startColumnIndex': a, 'endColumnIndex': b}, 'rows': [{'values': [{} for _ in range(a, b)]}], 'fields': 'userEnteredValue'}})

        if req:
            upd = _google_request_guarded('v252_non_destructive_upsert', requests.post, f'https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}:batchUpdate', headers=headers, json={'requests': req}, timeout=90, attempts=1)
            if upd.status_code >= 300:
                raise RuntimeError(f'Google Sheets non-destructive update {upd.status_code}: {upd.text[:500]}')

        escaped = str(actual_tab_title).replace("'", "''")
        verify = _google_request_guarded('v252_verify_incremental', requests.get, f'https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}', headers=headers, params={'includeGridData': 'true', 'ranges': f"'{escaped}'!A1:{_xlsx_col_name(max_cols)}{max(1, len(rows))}", 'fields': 'sheets(data(rowData(values(userEnteredValue,note))))'}, timeout=60, attempts=2)
        if verify.status_code >= 300:
            raise RuntimeError(f'Google Sheets incremental verify {verify.status_code}: {verify.text[:500]}')
        vr = ((verify.json().get('sheets') or [{}])[0].get('data') or [{}])[0].get('rowData') or []
        for idx, row0 in enumerate(rows):
            old_vals = (vr[idx] or {}).get('values') or [] if idx < len(vr) else []
            for c in range(max_cols):
                if (idx, c) in manual_preserved_cells:
                    continue
                want = _v239_google_target_plain((row0 or [])[c] if c < len(row0 or []) else '')
                got = _v239_google_plain_user_value(old_vals[c] if c < len(old_vals) else {})
                if not _v244_google_values_equivalent(want, got):
                    raise RuntimeError(f'Google incremental verify mismatch row={idx + 1} col={c + 1}; want={want}; got={got}')

        row_hash = hashlib.sha256(json.dumps(rows, ensure_ascii=False, sort_keys=False, separators=(',', ':'), default=str).encode('utf-8')).hexdigest()
        snapshot = [[_plain_json((row or [])[c] if c < len(row or []) else '') for c in range(max_cols)] for row in rows]
        try:
            SQLITE.set_meta('google_sync_v239', sync_key, {'tab': tab_title, 'sheet_id_v254': int(sheet_id), 'sheet_title_actual_v254': str(actual_tab_title), 'tenant_id': str(tid), 'chat_id': target_chat_id, 'managed_rows': len(rows), 'managed_cols': max_cols, 'managed_values_v252': snapshot, 'row_hash': row_hash, 'synced_at': now_local().isoformat(timespec='microseconds'), 'manual_values_preserved': manual_values_preserved})
        except Exception:
            pass
        url = f'https://docs.google.com/spreadsheets/d/{spreadsheet_id}/edit#gid={sheet_id}'

    try:
        tenant_google_history(tid, 'thuwed_non_destructive_upsert_v254', actual_tab_title, ok=True, chat_id=target_chat_id, url=url, added=added, updated=updated, unchanged=unchanged, stale_tail=stale_tail if 'stale_tail' in locals() else 0, manual_values_preserved=manual_values_preserved, row_growth=row_growth, col_growth=col_growth)
        tenant_google_persist(tid, 'tenant_google_runtime_v252')
        try:
            bot_journal('google_non_destructive_upsert_v254', target_chat_id, f'logical_tab={tab_title}; actual_tab={actual_tab_title}; sheetId={sheet_id}; added={added}; updated={updated}; unchanged={unchanged}; row_growth={row_growth}; row_shrink={row_shrink_v258}; row_copies={len(row_copy_map_v258)}; col_growth={col_growth}; manual_values_preserved={manual_values_preserved}; stale_tail_preserved={stale_tail if "stale_tail" in locals() else 0}')
        except Exception:
            pass
    except Exception:
        pass
    return url

# --- google:0045 · from 08_reliability_tasks.py:10149 · public _v261_google_sync_engine ---
def _v261_google_sync_engine(target_chat_id: int) -> str:
    """Per-space Google sync engine. v261 defaults to the historical incremental sync."""
    cid = int(target_chat_id)
    mode = ''
    try:
        tid = _v149_tenant_id(None, cid) if callable(globals().get('_v149_tenant_id')) else tenant_id_for_chat(cid, create=False)
        cfg = tenant_google_config(str(tid))
        mode = str(cfg.setdefault('export_settings', {}).get('sync_engine_v261') or '').strip().lower()
    except Exception:
        try:
            mode = str(get_chat_store(cid).setdefault('settings', {}).get('google_sync_engine_v261') or '').strip().lower()
        except Exception:
            mode = ''
    return mode if mode in _V261_GOOGLE_SYNC_ENGINES else 'previous'

# --- google:0046 · from 08_reliability_tasks.py:10164 · public _v261_google_sync_engine_label ---
def _v261_google_sync_engine_label(mode: str) -> str:
    return {
        'previous': 'ПРЕДЫДУЩАЯ',
        'fixed': 'ИСПРАВЛЕННАЯ',
        'new': 'НОВАЯ',
    }.get(str(mode or '').strip().lower(), 'ПРЕДЫДУЩАЯ')

# --- google:0047 · from 08_reliability_tasks.py:10171 · public _v261_set_google_sync_engine ---
def _v261_set_google_sync_engine(target_chat_id: int, mode: str) -> str:
    cid = int(target_chat_id)
    mode = str(mode or '').strip().lower()
    if mode not in _V261_GOOGLE_SYNC_ENGINES:
        mode = 'previous'
    tid = ''
    persisted = False
    try:
        tid = _v149_tenant_id(None, cid) if callable(globals().get('_v149_tenant_id')) else tenant_id_for_chat(cid, create=False)
        cfg = tenant_google_config(str(tid))
        cfg.setdefault('export_settings', {})['sync_engine_v261'] = mode
        try:
            tenant_google_history(str(tid), 'sync_engine_v261', mode, ok=True, chat_id=cid)
        except Exception:
            pass
        tenant_google_persist(str(tid), 'google_sync_engine_v261')
        persisted = True
    except Exception:
        try:
            get_chat_store(cid).setdefault('settings', {})['google_sync_engine_v261'] = mode
            save_data(data, root_only=True)
            persisted = True
        except Exception:
            pass
    try:
        bot_journal('google_sync_engine_v261', cid, f'mode={mode}; tenant={tid or "fallback"}; persisted={int(persisted)}')
    except Exception:
        pass
    return mode

# --- google:0048 · from 08_reliability_tasks.py:10201 · public _v167_google_upsert_named_tab ---
def _v167_google_upsert_named_tab(tab_title: str, rows: list[list], target_chat_id: int, layout: str='category', annotations_override: dict | None=None) -> str:
    """v261 selectable Google sync engine.

    previous — v239 incremental sync: bot data wins inside the managed table;
    fixed    — v259 non-destructive sync preserving manual user edits where possible;
    new      — v260 non-destructive sync plus new-sheet fallback on Constitution block.
    """
    mode = _v261_google_sync_engine(int(target_chat_id))
    fn = _v261_google_upsert_previous
    if mode == 'fixed':
        fn = _v261_google_upsert_fixed
    elif mode == 'new':
        fn = _v261_google_upsert_new
    try:
        bot_journal('google_sync_engine_run_v261', int(target_chat_id), f'mode={mode}; tab={str(tab_title)[:120]}')
    except Exception:
        pass
    return fn(tab_title, rows, int(target_chat_id), layout=layout, annotations_override=annotations_override)

# --- google:0049 · from 08_reliability_tasks.py:10221 · public _v228_google_retry_delay_seconds ---
def _v228_google_retry_delay_seconds(retry_count: int) -> int:
    n = max(1, int(retry_count or 1))
    if n == 1:
        return 60
    if n == 2:
        return 180
    if n == 3:
        return 600
    return 900

# --- google:0050 · from 08_reliability_tasks.py:10231 · public _v228_google_latest_due ---
def _v228_google_latest_due(now_dt, mode: str):
    """Return (run_key, target_day, selected_hhmm) for the latest due daily run.

    A daily backup at 05:01 finalizes the PREVIOUS calendar day.  Before today's
    05:01, yesterday's 05:01 remains the latest due run, which makes deploy/hibernate
    catch-up reliable instead of silently skipping a missed day.
    """
    mode = str(mode or '')
    selected = '00:01' if mode == 'd0001' else '05:01'
    hh, mm = [int(x) for x in selected.split(':', 1)]
    due = now_dt.replace(hour=hh, minute=mm, second=0, microsecond=0)
    if now_dt < due:
        due = due - _v167_timedelta(days=1)
    run_date = due.strftime('%Y-%m-%d')
    target_day = (due - _v167_timedelta(days=1)).strftime('%Y-%m-%d')
    return (f'{run_date}@{selected}', target_day, selected)

# --- google:0051 · from 08_reliability_tasks.py:10248 · public _v228_google_next_daily ---
def _v228_google_next_daily(now_dt, mode: str):
    selected = '00:01' if str(mode) == 'd0001' else '05:01'
    hh, mm = [int(x) for x in selected.split(':', 1)]
    nxt = now_dt.replace(hour=hh, minute=mm, second=0, microsecond=0)
    if nxt <= now_dt:
        nxt = nxt + _v167_timedelta(days=1)
    target_day = (nxt - _v167_timedelta(days=1)).strftime('%Y-%m-%d')
    return (nxt, target_day)

# --- google:0052 · from 08_reliability_tasks.py:10257 · public _v19_google_target_configured ---
def _v19_google_target_configured(target_chat_id: int) -> bool:
    """Local-only preflight. Missing Google target is a configuration wait state, not a retry storm."""
    try:
        tid = str(_v149_tenant_id(target_chat_id=int(target_chat_id)))
        gcfg = tenant_google_config(tid, create=False) if callable(globals().get('tenant_google_config')) else {}
        raw = str((gcfg or {}).get('spreadsheet_id') or '').strip()
        if (not raw) and tid == str(globals().get('TENANT_PLATFORM_ID') or ''):
            raw = str(globals().get('_V149_PLATFORM_GOOGLE_SHEET') or _v167_os.getenv('GOOGLE_SHEETS_SPREADSHEET_ID', '') or '').strip()
        return bool(raw)
    except Exception:
        return False

# --- google:0053 · from 08_reliability_tasks.py:10270 · public _v19_google_suspend_missing_target ---
def _v19_google_suspend_missing_target(target_chat_id: int, cfg: dict | None=None, reason: str='schedule') -> bool:
    cfg = cfg if isinstance(cfg, dict) else _v167_google_schedule_cfg(int(target_chat_id))
    first = not bool(cfg.get('paused_missing_target_r19'))
    if not first:
        return False
    cfg['paused_missing_target_r19'] = True
    cfg['paused_missing_target_at_r19'] = now_local().isoformat(timespec='seconds')
    cfg['pending_run_key'] = ''
    cfg['pending_since_ts'] = 0.0
    cfg['retry_count'] = 0
    cfg['next_retry_ts'] = 0.0
    cfg['last_error'] = 'Google Таблица не выбрана — автообновление ожидает настройки /google.'
    _v167_persist_schedule(int(target_chat_id))
    if first:
        try:
            bot_journal('google_auto_paused_missing_target_r19', int(target_chat_id), str(reason or 'schedule')[:160], 'WARN')
        except Exception:
            pass
    return False

# --- google:0054 · from 08_reliability_tasks.py:10291 · public _v19_google_resume_if_target_ready ---
def _v19_google_resume_if_target_ready(target_chat_id: int, cfg: dict | None=None) -> bool:
    cfg = cfg if isinstance(cfg, dict) else _v167_google_schedule_cfg(int(target_chat_id), create=False)
    if not isinstance(cfg, dict) or not cfg:
        return False
    if not _v19_google_target_configured(int(target_chat_id)):
        return False
    if cfg.pop('paused_missing_target_r19', None) is not None:
        cfg.pop('paused_missing_target_at_r19', None)
        if str(cfg.get('last_error') or '').startswith('Google Таблица не выбрана'):
            cfg['last_error'] = ''
        cfg['last_attempt_key'] = ''
        cfg['pending_run_key'] = ''
        cfg['pending_since_ts'] = 0.0
        cfg['retry_count'] = 0
        cfg['next_retry_ts'] = 0.0
        _v167_persist_schedule(int(target_chat_id))
        try:
            bot_journal('google_auto_resumed_target_ready_r19', int(target_chat_id), 'Google target configured')
        except Exception:
            pass
    return True

# --- google:0055 · from 08_reliability_tasks.py:10314 · public _v167_google_update_target ---
def _v167_google_update_target(target_chat_id: int, reason: str='schedule', run_key: str='', target_day: str=''):
    target_chat_id = int(target_chat_id)
    run_key = str(run_key or '')
    target_day = str(target_day or '')[:10]
    with _V167_GOOGLE_LOCK:
        if target_chat_id in _V167_GOOGLE_RUNNING:
            return False
        _V167_GOOGLE_RUNNING.add(target_chat_id)
    cfg = _v167_google_schedule_cfg(target_chat_id)
    try:
        if not _v19_google_target_configured(target_chat_id):
            return _v19_google_suspend_missing_target(target_chat_id, cfg, reason)
        _v19_google_resume_if_target_ready(target_chat_id, cfg)
        day = target_day or today_key()
        start_key, end_key = _v167_thuwed_bounds(day)
        tab = _v167_period_title(start_key, end_key)
        if run_key:
            cfg['last_attempt_key'] = run_key
            cfg['last_attempt_at'] = now_local().isoformat(timespec='seconds')
            cfg['pending_run_key'] = run_key
            cfg['pending_since_ts'] = _v163_time.time()
            cfg['last_target_day'] = day
            cfg['last_target_period'] = tab
            try:
                bot_journal('google_schedule_started_v228', target_chat_id, f'run={run_key}; day={day}; tab={tab}; reason={reason}')
            except Exception:
                pass
        _r40_q = globals().get('_r40_google_query_submit')
        _r40_w = globals().get('_r40_google_wait')
        if callable(_r40_q) and callable(_r40_w):
            _r40_jid = _r40_q(tab, target_chat_id, start_key, end_key, 0, 0, layout='category', include_annotations=True, notify_result=False, recipient_chat_id=target_chat_id)
            _r40_ok, url, _r40_err = _r40_w(_r40_jid, timeout=900)
            if not _r40_ok:
                raise RuntimeError(_r40_err or f'Google HEAVY job {_r40_jid} failed')
        else:
            rows = build_exact_category_stats_xlsx_rows(target_chat_id, start_key, 0, end_key, 0)
            url = _v167_google_upsert_named_tab(tab, rows, target_chat_id, layout='category')
        cfg['last_ok_at'] = now_local().isoformat(timespec='seconds')
        cfg['last_error'] = ''
        cfg['last_period'] = tab
        if run_key:
            cfg['last_success_key'] = run_key
            cfg['last_run_key'] = run_key
            cfg['pending_run_key'] = ''
            cfg['pending_since_ts'] = 0.0
            cfg['retry_count'] = 0
            cfg['next_retry_ts'] = 0.0
        _v167_persist_schedule(target_chat_id)
        try:
            bot_journal('google_thuwed_updated', target_chat_id, f"tab={tab}; day={day}; run={run_key or '-'}; reason={reason}; url={url[:120]}")
        except Exception:
            pass
        return True
    except Exception as exc:
        cfg['last_error'] = str(exc)[:500]
        if run_key:
            cfg['pending_run_key'] = ''
            cfg['pending_since_ts'] = 0.0
            cfg['retry_count'] = int(cfg.get('retry_count') or 0) + 1
            delay = _v228_google_retry_delay_seconds(cfg['retry_count'])
            cfg['next_retry_ts'] = _v163_time.time() + delay
            try:
                bot_journal('google_schedule_retry_v228', target_chat_id, f"run={run_key}; day={target_day}; retry={cfg['retry_count']}; in={delay}s; error={str(exc)[:220]}", 'WARN')
            except Exception:
                pass
        _v167_persist_schedule(target_chat_id)
        try:
            log_error(f'v167 google Thu-Wed update chat={target_chat_id}: {exc}')
        except Exception:
            pass
        return False
    finally:
        with _V167_GOOGLE_LOCK:
            _V167_GOOGLE_RUNNING.discard(target_chat_id)

# --- google:0056 · from 08_reliability_tasks.py:10406 · public _v169_google_mode ---
def _v169_google_mode(cfg: dict | None) -> str:
    cfg = cfg if isinstance(cfg, dict) else {}
    mode = str(cfg.get('mode') or '').strip().lower()
    if mode not in {'manual', 'change', 'm15', 'h1', 'd0001', 'd0501'}:
        if not bool(cfg.get('enabled', True)):
            mode = 'manual'
        else:
            mode = 'd0001' if str(cfg.get('time') or '05:01') == '00:01' else 'd0501'
    return mode

# --- google:0057 · from 08_reliability_tasks.py:10416 · public _v169_google_mode_label ---
def _v169_google_mode_label(mode: str) -> str:
    return {'manual': '✋ Только вручную', 'change': '⚡ После изменений', 'm15': '🕒 Каждые 15 минут', 'h1': '🕐 Каждый час', 'd0001': '🌙 Ежедневно 00:01', 'd0501': '🌅 Ежедневно 05:01'}.get(str(mode), '✋ Только вручную')

# --- google:0058 · from 08_reliability_tasks.py:10419 · public _v244_google_initial_sync_fire ---
def _v244_google_initial_sync_fire(target_chat_id: int, reason: str='mode-change-initial', retry: int=0) -> None:
    cid = int(target_chat_id)
    cfg = _v167_google_schedule_cfg(cid, create=False)
    if not cfg or _v169_google_mode(cfg) != 'change':
        return
    if _v169_google_enqueue(cid, str(reason or 'mode-change-initial')):
        try:
            bot_journal('google_change_initial_enqueued_v244', cid, str(reason or 'mode-change-initial'))
        except Exception:
            pass
        return
    if int(retry or 0) >= 6:
        try:
            bot_journal('google_change_initial_queue_busy_v244', cid, f'reason={reason}; retries={retry}', 'WARN')
        except Exception:
            pass
        return
    delay = min(30.0, 1.5 * 2 ** int(retry or 0))
    try:
        DELAYED_SCHEDULER.schedule(f'google-change-initial:{cid}', delay, _v244_google_initial_sync_fire, cid, str(reason or 'mode-change-initial'), int(retry or 0) + 1)
    except Exception:
        pass

# --- google:0059 · from 08_reliability_tasks.py:10442 · public _v244_google_resume_after_recovery ---
def _v244_google_resume_after_recovery(reason: str='recovery') -> None:
    """After verified recovery, refresh every chat that is configured for change-sync."""
    for cid in _v167_known_chat_ids():
        try:
            cfg = _v167_google_schedule_cfg(int(cid), create=False)
            if cfg and _v169_google_mode(cfg) == 'change':
                DELAYED_SCHEDULER.schedule(f'google-recovery-sync:{int(cid)}', 0.5, _v244_google_initial_sync_fire, int(cid), 'recovery-sync:' + str(reason or 'recovery'), 0)
        except Exception:
            continue

# --- google:0060 · from 08_reliability_tasks.py:10452 · public _v169_set_google_mode ---
def _v169_set_google_mode(target_chat_id: int, mode: str) -> dict:
    mode = str(mode or 'manual').strip().lower()
    if mode not in {'manual', 'change', 'm15', 'h1', 'd0001', 'd0501'}:
        mode = 'manual'
    cfg = _v167_google_schedule_cfg(int(target_chat_id))
    previous_mode = _v169_google_mode(cfg)
    cfg['mode'] = mode
    cfg['enabled'] = mode != 'manual'
    if mode == 'd0001':
        cfg['time'] = '00:01'
    elif mode == 'd0501':
        cfg['time'] = '05:01'
    cfg['last_run_key'] = ''
    cfg['last_success_key'] = ''
    cfg['last_attempt_key'] = ''
    cfg['pending_run_key'] = ''
    cfg['pending_since_ts'] = 0.0
    cfg['retry_count'] = 0
    cfg['next_retry_ts'] = 0.0
    _v167_persist_schedule(int(target_chat_id))
    if mode == 'change' and previous_mode != 'change':
        try:
            DELAYED_SCHEDULER.cancel(f'google-change-initial:{int(target_chat_id)}')
            DELAYED_SCHEDULER.schedule(f'google-change-initial:{int(target_chat_id)}', 0.25, _v244_google_initial_sync_fire, int(target_chat_id), 'mode-change-initial', 0)
        except Exception:
            pass
    return cfg

# --- google:0061 · from 08_reliability_tasks.py:10480 · public _v169_google_settings_text ---
def _v169_google_settings_text(target_chat_id: int) -> str:
    target_chat_id = int(target_chat_id)
    cfg = _v167_google_schedule_cfg(target_chat_id)
    if _v19_google_target_configured(target_chat_id):
        _v19_google_resume_if_target_ready(target_chat_id, cfg)
    mode = _v169_google_mode(cfg)
    start_key, end_key = _v167_thuwed_bounds(today_key())
    tab = _v167_period_title(start_key, end_key)
    last_ok = str(cfg.get('last_ok_at') or '—')
    last_attempt = str(cfg.get('last_attempt_at') or '—')
    last_error = str(cfg.get('last_error') or '').strip()
    upcoming = '—'
    upcoming_period = '—'
    if mode in {'d0001', 'd0501'}:
        nxt, target_day = _v228_google_next_daily(now_local(), mode)
        s2, e2 = _v167_thuwed_bounds(target_day)
        upcoming_period = _v167_period_title(s2, e2)
        upcoming = f"{nxt.strftime('%d.%m.%y %H:%M')} → день {fmt_date_ddmmyy(target_day)}"
    lines = ['☁️ GOOGLE ТАБЛИЦА ЧТ–СР', '', f'Чат: {get_chat_display_name(target_chat_id)}', f'Текущий лист: {tab}', f'Режим обновления: {_v169_google_mode_label(mode)}', f'Sync: {_v261_google_sync_engine_label(_v261_google_sync_engine(target_chat_id))}', f'Последняя попытка: {last_attempt}', f'Последнее успешное: {last_ok}', f'Следующий автобэкап: {upcoming}', f'Лист следующего автобэкапа: {upcoming_period}']
    if last_error:
        lines.append(f'Последняя ошибка: {last_error[:350]}')
    lines += ['', 'Период листа всегда четверг → среда. При наступлении нового четверга создаётся новый лист; внутри периода обновляется тот же лист.', '', 'Выберите способ/период обновления ниже.', '', 'Ф240⏰']
    return '\n'.join(lines)[:3900]

# --- google:0062 · from 08_reliability_tasks.py:10504 · public _v169_google_settings_keyboard ---
def _v169_google_settings_keyboard(target_chat_id: int, day_key: str | None=None):
    target_chat_id = int(target_chat_id)
    day_key = str(day_key or get_chat_store(target_chat_id).get('current_view_day') or today_key())[:10]
    mode = _v169_google_mode(_v167_google_schedule_cfg(target_chat_id))
    kb = types.InlineKeyboardMarkup(row_width=2)

    def _b(label, value):
        mark = '✅ ' if mode == value else ''
        return IB(mark + label, callback_data=f'v169:gmode:{target_chat_id}:{value}')
    kb.row(_b('✋ Вручную', 'manual'), _b('⚡ После изменений', 'change'))
    kb.row(_b('🕒 15 минут', 'm15'), _b('🕐 1 час', 'h1'))
    kb.row(_b('🌙 00:01', 'd0001'), _b('🌅 05:01', 'd0501'))
    kb.row(IB('☁️ Обновить Чт–Ср сейчас', callback_data=f'v169:gnow:{target_chat_id}'))
    kb.row(IB('🔙 Назад в Инфо', callback_data=f'd:{day_key}:info'), IB('⬅️ Осн. окно', callback_data=f'd:{day_key}:back_main'))
    return kb

# --- google:0063 · from 08_reliability_tasks.py:10520 · public _v169_google_enqueue ---
def _v169_google_enqueue(target_chat_id: int, reason: str, run_key: str='', target_day: str='') -> bool:
    target_chat_id = int(target_chat_id)
    key = f'google-thuwed:{target_chat_id}'
    pool = globals().get('EXPORT_TASK_POOL')
    if pool is not None:
        try:
            ok = bool(pool.submit_unique(key, _v167_google_update_target, target_chat_id, str(reason), str(run_key or ''), str(target_day or '')))
            if not ok:
                try:
                    bot_journal('google_thuwed_coalesced', target_chat_id, f'reason={reason}')
                except Exception:
                    pass
            return ok
        except Exception as exc:
            try:
                log_error(f'v169 Google queue {target_chat_id}: {exc}')
            except Exception:
                pass
    return False

# --- google:0064 · from 08_reliability_tasks.py:10540 · public _v169_google_change_fire ---
def _v169_google_change_fire(target_chat_id: int):
    cfg = _v167_google_schedule_cfg(int(target_chat_id), create=False)
    if _v169_google_mode(cfg) != 'change':
        return
    if not _v19_google_target_configured(int(target_chat_id)):
        _v19_google_suspend_missing_target(int(target_chat_id), cfg, 'finance-change')
        return
    _v19_google_resume_if_target_ready(int(target_chat_id), cfg)
    if not _v169_google_enqueue(int(target_chat_id), 'finance-change'):
        try:
            DELAYED_SCHEDULER.schedule(f'google-change-retry:{int(target_chat_id)}', 15.0, _v169_google_change_fire, int(target_chat_id))
        except Exception:
            pass

# --- google:0065 · from 08_reliability_tasks.py:10554 · public _v169_schedule_google_after_change ---
def _v169_schedule_google_after_change(target_chat_id: int, reason: str='finance_changed') -> None:
    try:
        gate = globals().get('external_access_allowed_v233')
        if callable(gate) and (not gate('google')):
            return
        safe, _why = _v239_google_recovery_write_gate()
        if (not safe) and _v261_google_sync_engine(int(target_chat_id)) != 'new':
            return
        cfg = _v167_google_schedule_cfg(int(target_chat_id), create=False)
        if not cfg or _v169_google_mode(cfg) != 'change':
            return
        low = str(reason or '').casefold()
        mutation = low.startswith('finalize:') or any((x in low for x in ('finance', 'record', 'forward', 'edit', 'delete', 'add', 'new', 'insert', 'create', 'change', 'currency', 'reset', 'restore_csv')))
        if low and (not mutation):
            return
        DELAYED_SCHEDULER.schedule(f'google-change:{int(target_chat_id)}', 8.0, _v169_google_change_fire, int(target_chat_id))
    except Exception as exc:
        try:
            log_error(f'v169 schedule Google after change {target_chat_id}: {exc}')
        except Exception:
            pass

# --- google:0066 · from 08_reliability_tasks.py:10576 · public _v167_google_scheduler_tick ---
def _v167_google_scheduler_tick():
    try:
        gate = globals().get('external_access_allowed_v233')
        if callable(gate) and (not gate('google')):
            return
        if callable(globals().get('runtime_is_shutting_down')) and runtime_is_shutting_down():
            return
        if callable(globals().get('runtime_is_ready')) and (not runtime_is_ready()):
            return
        safe, why = _v239_google_recovery_write_gate()
        if not safe:
            try:
                last = float(globals().get('_V239_GOOGLE_RECOVERY_BLOCK_LOG', 0.0) or 0.0)
                nowm = time.monotonic()
                if nowm - last >= 900.0:
                    globals()['_V239_GOOGLE_RECOVERY_BLOCK_LOG'] = nowm
                    bot_journal('google_scheduler_blocked_recovery_v239', int(OWNER_ID or 0) or None, str(why)[:300], 'WARN')
            except Exception:
                pass
        now = now_local()
        date_key = now.strftime('%Y-%m-%d')
        minute = int(now.strftime('%M'))
        hour = int(now.strftime('%H'))
        now_ts = _v163_time.time()
        for cid in _v167_known_chat_ids():
            if (not safe) and _v261_google_sync_engine(int(cid)) != 'new':
                continue
            cfg = _v167_google_schedule_cfg(cid, create=False)
            if not cfg:
                continue
            mode = _v169_google_mode(cfg)
            if mode in {'manual', 'change'}:
                continue
            if not _v19_google_target_configured(int(cid)):
                _v19_google_suspend_missing_target(int(cid), cfg, 'scheduler')
                continue
            _v19_google_resume_if_target_ready(int(cid), cfg)
            run_key = ''
            reason = mode
            target_day = date_key
            if mode == 'm15':
                run_key = f'{date_key}@{hour:02d}:{minute // 15 * 15:02d}'
            elif mode == 'h1':
                run_key = f'{date_key}@{hour:02d}'
            elif mode in {'d0001', 'd0501'}:
                run_key, target_day, _selected = _v228_google_latest_due(now, mode)
            if not run_key or str(cfg.get('last_success_key') or '') == run_key:
                continue
            if str(cfg.get('pending_run_key') or '') == run_key and now_ts - float(cfg.get('pending_since_ts') or 0) < 300:
                continue
            if str(cfg.get('last_attempt_key') or '') == run_key and float(cfg.get('next_retry_ts') or 0) > now_ts:
                continue
            cfg['last_attempt_key'] = run_key
            cfg['last_attempt_at'] = now.isoformat(timespec='seconds')
            cfg['pending_run_key'] = run_key
            cfg['pending_since_ts'] = now_ts
            cfg['last_target_day'] = target_day
            s2, e2 = _v167_thuwed_bounds(target_day)
            cfg['last_target_period'] = _v167_period_title(s2, e2)
            _v167_persist_schedule(cid)
            queued = _v169_google_enqueue(cid, reason, run_key, target_day)
            if queued:
                try:
                    bot_journal('google_schedule_enqueued_v228', cid, f"run={run_key}; day={target_day}; tab={cfg['last_target_period']}; mode={mode}")
                except Exception:
                    pass
            else:
                cfg['pending_run_key'] = ''
                cfg['pending_since_ts'] = 0.0
                cfg['retry_count'] = int(cfg.get('retry_count') or 0) + 1
                delay = _v228_google_retry_delay_seconds(cfg['retry_count'])
                cfg['next_retry_ts'] = now_ts + delay
                _v167_persist_schedule(cid)
                try:
                    bot_journal('google_schedule_enqueue_retry_v228', cid, f"run={run_key}; retry={cfg['retry_count']}; in={delay}s", 'WARN')
                except Exception:
                    pass
    except Exception as exc:
        try:
            log_error(f'v169 google scheduler: {exc}')
        except Exception:
            pass
    finally:
        try:
            if not (callable(globals().get('runtime_is_shutting_down')) and runtime_is_shutting_down()):
                DELAYED_SCHEDULER.schedule('google-thuwed-scheduler', 20.0, _v167_google_scheduler_tick)
        except Exception:
            pass

# --- google:0067 · from 08_reliability_tasks.py:10665 · public _v167_google_scheduler_loop ---
def _v167_google_scheduler_loop():
    return _v167_google_scheduler_tick()

# --- google:0068 · from 08_reliability_tasks.py:10668 · public _v167_start_google_scheduler ---
def _v167_start_google_scheduler():
    global _V167_GOOGLE_SCHEDULER_STARTED
    if _V167_GOOGLE_SCHEDULER_STARTED:
        return
    _V167_GOOGLE_SCHEDULER_STARTED = True
    DELAYED_SCHEDULER.schedule('google-thuwed-scheduler', 3.0, _v167_google_scheduler_tick)

# --- google:0069 · from 08_reliability_tasks.py:15295 · public _canon_v149_google_wait__002 ---
def _canon_v149_google_wait__002(tenant_id: str, kind: str, chat_id: int, user_id: int) -> None:
    tid = _v149_tenant_id(tenant_id)
    cfg = tenant_google_config(tid)
    sid = _v213_input_sid()
    delay = _v213_input_timeout_seconds()
    cfg['input_wait'] = {'kind': str(kind), 'chat_id': int(chat_id), 'user_id': int(user_id), 'expires_at': _v149_time.time() + delay, 'session_id': sid, 'cancel_message_id': 0}
    cfg['updated_at'] = _v149_now_iso()
    tenant_google_persist(tid, 'tenant_google_update')
    try:
        sent = bot.send_message(int(chat_id), _v213_prompt_text(f'⏳ Ожидание данных Google. Автоотмена: {_format_duration_short(delay)}.'), reply_markup=_v213_cancel_markup('google', sid))
        cfg['input_wait']['cancel_message_id'] = int(getattr(sent, 'message_id', 0) or 0)
        tenant_google_persist(tid, 'tenant_google_update')
    except Exception:
        pass
    key = f'v213-input-google:{tid}:{int(chat_id)}:{int(user_id)}'
    DELAYED_SCHEDULER.cancel(key)

    def _expire():
        live = tenant_google_config(tid).get('input_wait') or {}
        if str(live.get('session_id') or '') != sid:
            return
        mid = int(live.get('cancel_message_id') or 0)
        tenant_google_config(tid)['input_wait'] = {}
        tenant_google_persist(tid, 'tenant_google_update')
        _v172_delete_quiet(int(chat_id), mid)
        try:
            send_and_auto_delete(int(chat_id), '⌛ Ввод Google отменён по таймеру.', 7)
        except Exception:
            pass
    DELAYED_SCHEDULER.schedule(key, delay, _expire)

# --- google:0070 · from 08_reliability_tasks.py:15326 · public _canon_tenant_google_handle_message__002 ---
def _canon_tenant_google_handle_message__002(msg) -> bool:
    wait = {}
    tid = ''
    cid = 0
    uid = 0
    try:
        cid = int(msg.chat.id)
        uid = int(getattr(getattr(msg, 'from_user', None), 'id', 0) or 0)
        tid = str(tenant_id_for_chat(cid, create=False) or '')
        wait = dict((tenant_google_config(tid, create=False) or {}).get('input_wait') or {}) if tid else {}
    except Exception:
        pass
    result = _V213_PREV_GOOGLE_HANDLE(msg)
    if result and wait:
        try:
            live = (tenant_google_config(tid, create=False) or {}).get('input_wait') or {}
            if not live:
                DELAYED_SCHEDULER.cancel(f'v213-input-google:{tid}:{cid}:{uid}')
                _v172_delete_quiet(cid, int(wait.get('cancel_message_id') or 0))
        except Exception:
            pass
    return result

# --- google:0071 · from 10_split_policy_offload.py:2126 · public _split_google_target ---
def _split_google_target(target_chat_id=None, tenant_id=None):
    try:
        tid = str(_v149_tenant_id(tenant_id, target_chat_id))
    except Exception:
        tid = str(tenant_id or globals().get('TENANT_PLATFORM_ID') or 'platform')
    cfg = tenant_google_config(tid, create=False) if callable(globals().get('tenant_google_config')) else {}
    raw = str((cfg or {}).get('spreadsheet_id') or '').strip()
    if not raw and tid == str(globals().get('TENANT_PLATFORM_ID') or ''):
        raw = str(_split_os.getenv('GOOGLE_SHEETS_SPREADSHEET_ID', '') or '').strip()
    if not raw:
        raise RuntimeError('Google Таблица не выбрана. Откройте /google → «Куда выгружать Excel» и пришлите ссылку таблицы.')
    try:
        sheet_id = _v149_google_id(raw, 'sheet')
    except Exception:
        sheet_id = str(raw).strip()
    return tid, sheet_id

# --- google:0072 · from 10_split_policy_offload.py:2144 · public _split_annotations_for_google ---
def _split_annotations_for_google(rows, layout, annotations_override, include_annotations):
    if not include_annotations:
        return {}
    try:
        if layout == 'compact':
            _styles, ann, _freeze, _widths = _modern_compact_excel_styles_comments(rows, annotations_override or {})
        elif layout == 'category_compact':
            _styles, ann, _freeze, _widths = _modern_category_no_description_styles_comments(rows, annotations_override or {})
        else:
            _styles, ann, _freeze, _widths = _modern_category_excel_styles_comments(rows)
            if annotations_override is not None:
                ann = dict(annotations_override or {})
        return ann or {}
    except Exception:
        return dict(annotations_override or {})

# --- google:0073 · from 10_split_policy_offload.py:2161 · public _v262_split_google_sheets_create_category_report ---
def _v262_split_google_sheets_create_category_report(title, rows, layout='category', annotations_override=None, include_annotations=True, **kwargs):
    """Queue Google Sheets work on Render #2 and return immediately with a job token."""
    if not _split_env_bool('SPLIT_GOOGLE_REMOTE_ENABLED', True):
        raise RuntimeError('Google Sheets worker delegation disabled')
    base, secret = _split_peer_base(), _split_secret()
    if not base or not secret:
        raise RuntimeError('Google Sheets worker is not configured')
    target_chat_id = kwargs.get('target_chat_id')
    notify_result = bool(kwargs.get('notify_result', True))
    recipient_chat_id = kwargs.get('recipient_chat_id') or target_chat_id
    tid, spreadsheet_id = _split_google_target(target_chat_id=target_chat_id, tenant_id=kwargs.get('tenant_id'))
    _SPLIT_STATE['google_last_attempt'] = _split_time.time()
    annotations = _split_annotations_for_google(rows, str(layout or 'category'), annotations_override, bool(include_annotations))
    encoded_notes = {f'{int(r)},{int(c)}': str(note) for (r, c), note in annotations.items() if str(note or '').strip()}
    client_job_id = _split_secrets.token_hex(12)
    body = {
        'job_id': client_job_id,
        'title': str(title or 'Статьи')[:300],
        'rows': rows,
        'layout': str(layout or 'category'),
        'annotations': encoded_notes,
        'include_annotations': bool(include_annotations),
        'spreadsheet_id': spreadsheet_id,
        'tenant_id': tid,
        'target_chat_id': target_chat_id,
        'recipient_chat_id': recipient_chat_id,
        'notify_result': notify_result,
    }
    try:
        r = requests.post(base + '/internal/google/sheet', json=body, headers=_split_headers('vys-262-front-google'), timeout=30)
        payload = r.json() if r.content and 'json' in str(r.headers.get('content-type', '')).lower() else {}
        if r.status_code == 202:
            job_id = str(payload.get('job_id') or client_job_id)
            _SPLIT_STATE['google_last_job'] = job_id
            _SPLIT_STATE['google_last_error'] = ''
            return 'worker-job:' + job_id
        if 200 <= r.status_code < 300 and payload.get('url'):
            _SPLIT_STATE['google_last_ok'] = _split_time.time()
            _SPLIT_STATE['google_last_error'] = ''
            return str(payload.get('url'))
        _SPLIT_STATE['google_last_error'] = f'HTTP {r.status_code}: {r.text[:220]}'
        raise RuntimeError('Google Sheets worker: ' + _SPLIT_STATE['google_last_error'])
    except Exception as exc:
        _SPLIT_STATE['google_last_error'] = str(exc)[:240]
        raise

# --- google:0074 · from 10_split_policy_offload.py:2208 · public _split_google_result_seen ---
def _split_google_result_seen(job_id):
    now = _split_time.time()
    with _SPLIT_GOOGLE_RESULT_LOCK:
        stale = [k for k, ts in _SPLIT_GOOGLE_RESULTS.items() if now - float(ts) > 86400]
        for key in stale:
            _SPLIT_GOOGLE_RESULTS.pop(key, None)
        if job_id in _SPLIT_GOOGLE_RESULTS:
            return True
        _SPLIT_GOOGLE_RESULTS[job_id] = now
        return False

# --- google:0075 · from 10_split_policy_offload.py:2255 · public _split_tenant_google_status_text ---
def _split_tenant_google_status_text(tenant_id):
    tid = str(tenant_id)
    row = tenant_get(tid) or {}
    cfg = tenant_google_config(tid)
    raw = str(cfg.get('spreadsheet_id') or '')
    if not raw and tid == str(globals().get('TENANT_PLATFORM_ID') or ''):
        raw = str(_split_os.getenv('GOOGLE_SHEETS_SPREADSHEET_ID', '') or '')
    try:
        shown = _v149_mask_id(raw) if raw else 'не выбрана'
    except Exception:
        shown = (raw[:8] + '…' + raw[-6:]) if len(raw) > 18 else (raw or 'не выбрана')
    settings = cfg.get('export_settings') or {}
    return (
        f"📊 GOOGLE EXCEL · {row.get('name') or tid}\n\n"
        f"Service account: ✅ Render #2\n"
        f"Куда выгружать: {shown}\n"
        f"Google Sheets: {'✅ ВКЛ' if settings.get('sheet_enabled', True) else '⬜ ВЫКЛ'}\n"
        f"История: {len(cfg.get('history') or [])}\n"
        f"Ошибки: {len(cfg.get('errors') or [])}\n\n"
        "Нажмите «Куда выгружать Excel» и пришлите ссылку или ID Google Таблицы. "
        "Сам service_account хранится только на Render #2. Выбранную таблицу нужно расшарить его client_email как Редактору."
    )[:3900]

# --- google:0076 · from 10_split_policy_offload.py:2279 · public _split_tenant_google_keyboard ---
def _split_tenant_google_keyboard(tenant_id):
    tid = str(tenant_id)
    cfg = tenant_google_config(tid)
    settings = cfg.get('export_settings') or {}
    kb = types.InlineKeyboardMarkup(row_width=1)
    kb.row(IB('📊 Куда выгружать Excel', callback_data='v149:google:sheet'))
    kb.row(IB(f"{('✅' if settings.get('sheet_enabled', True) else '⬜')} Google Sheets: {('ВКЛ' if settings.get('sheet_enabled', True) else 'ВЫКЛ')}", callback_data='v149:google:toggle_sheet'))
    kb.row(IB('🧪 Проверить выбранную таблицу', callback_data='v149:google:test'))
    kb.row(IB(f"📜 История ({len(cfg.get('history') or [])})", callback_data='v149:google:history'), IB(f"⚠️ Ошибки ({len(cfg.get('errors') or [])})", callback_data='v149:google:errors'))
    return kb

# --- google:0077 · from 10_split_policy_offload.py:2291 · public _split_tenant_google_test ---
def _legacy_s0077_split_tenant_google_test(tenant_id):
    try:
        tid, spreadsheet_id = _split_google_target(tenant_id=str(tenant_id))
        base = _split_peer_base()
        if not base or not _split_secret():
            return False, '❌ Render #2 не настроен.'
        r = requests.post(base + '/internal/google/test', json={'spreadsheet_id': spreadsheet_id, 'tenant_id': tid}, headers=_split_headers('vys-262-front-google-test'), timeout=35)
        payload = r.json() if r.content else {}
        if 200 <= r.status_code < 300 and payload.get('ok'):
            return True, f"✅ Google Таблица доступна через Render #2.\nНазвание: {payload.get('title') or '—'}\nService account: {payload.get('service_email') or '—'}"
        return False, '❌ Проверка Google: ' + str(payload.get('error') or r.text[:500])
    except Exception as exc:
        return False, '❌ Проверка Google: ' + str(exc)[:600]

# --- google:0078 · from 10_split_policy_offload.py:2306 · public _split_reject_front_google_credentials ---
def _split_reject_front_google_credentials(*args, **kwargs):
    raise RuntimeError('Service account не загружается в Telegram-фронт. GOOGLE_SERVICE_ACCOUNT_JSON задаётся только в Environment Render #2.')

# --- google:0079 · from 10_split_policy_offload.py:2317 · public _split_v167_google_upsert_named_tab ---
def _split_v167_google_upsert_named_tab(tab_title, rows, target_chat_id, layout='category', annotations_override=None):
    """Route legacy v167/v261 scheduled Google refreshes to Render #2."""
    return _v262_split_google_sheets_create_category_report(
        tab_title, rows, layout=layout, annotations_override=annotations_override,
        include_annotations=True, target_chat_id=int(target_chat_id),
        recipient_chat_id=int(target_chat_id), notify_result=False,
    )

# --- google:0080 · from 10_split_policy_offload.py:3485 · public _r7_google_worker_info ---
def _legacy_s0080_r7_google_worker_info(fetch: bool=True):
    now=_split_time.time()
    cached=dict(_R7_GOOGLE_INFO_CACHE.get('data') or {})
    if cached and (not fetch or now-float(_R7_GOOGLE_INFO_CACHE.get('ts') or 0) < 600):
        return cached
    if not fetch:
        return cached
    base = _split_peer_base()
    if not base or not _split_secret():
        return cached
    try:
        r = requests.get(base + '/internal/google/info', headers=_split_headers('vys-262-front-google-info'), timeout=8)
        payload = r.json() if r.content else {}
        if 200 <= r.status_code < 300 and payload.get('ok'):
            _R7_GOOGLE_INFO_CACHE.update(ts=now, data=dict(payload))
            return dict(payload)
    except Exception:
        pass
    return cached

# --- google:0081 · from 10_split_policy_offload.py:3506 · public _r7_google_status_text ---
def _r7_google_status_text(tenant_id):
    tid = str(tenant_id)
    row = tenant_get(tid) or {}
    cfg = tenant_google_config(tid)
    raw = str(cfg.get('spreadsheet_id') or '')
    if not raw and tid == str(globals().get('TENANT_PLATFORM_ID') or ''):
        raw = str(_split_os.getenv('GOOGLE_SHEETS_SPREADSHEET_ID', '') or '')
    # Opening /google must be instant: use cached/persisted email only. The worker is
    # contacted when the user presses step 1 or when access is tested.
    info = _r7_google_worker_info(fetch=False)
    email = str(cfg.get('service_account_email') or info.get('service_email') or '')
    title = str(cfg.get('spreadsheet_title') or '')
    ready = bool(raw and title)
    target = title or ((_v149_mask_id(raw) if raw else 'не выбрана'))
    return (
        f"📊 GOOGLE EXCEL · {row.get('name') or tid}\n\n"
        f"Статус: {'✅ готово к выгрузке' if ready else '🟡 нужно подключить таблицу'}\n"
        f"Таблица: {target}\n"
        f"Service account: {email or 'Render #2'}\n\n"
        "Как подключить первый раз:\n"
        "1️⃣ Нажмите «Email для доступа» и добавьте этот email в Google Таблице: Поделиться → Редактор.\n"
        "2️⃣ Нажмите «Подключить таблицу» и пришлите ссылку на неё.\n"
        "3️⃣ Бот сам проверит доступ. Если всё хорошо — больше ничего настраивать не нужно.\n\n"
        "После этого кнопки Google-выгрузки сами используют выбранную таблицу."
    )[:3900]

# --- google:0082 · from 10_split_policy_offload.py:3533 · public _r7_google_keyboard ---
def _r7_google_keyboard(tenant_id):
    tid = str(tenant_id)
    cfg = tenant_google_config(tid)
    raw = str(cfg.get('spreadsheet_id') or '')
    if not raw and tid == str(globals().get('TENANT_PLATFORM_ID') or ''):
        raw = str(_split_os.getenv('GOOGLE_SHEETS_SPREADSHEET_ID', '') or '')
    kb = types.InlineKeyboardMarkup(row_width=1)
    kb.row(IB('1️⃣ Email для доступа', callback_data='v149:google:service_email'))
    kb.row(IB('2️⃣ Подключить / сменить таблицу', callback_data='v149:google:sheet'))
    kb.row(IB('3️⃣ Проверить доступ', callback_data='v149:google:test'))
    if raw:
        try:
            sid = _v149_google_id(raw, 'sheet')
            kb.row(types.InlineKeyboardButton('🔗 Открыть текущую таблицу', url=f'https://docs.google.com/spreadsheets/d/{sid}/edit'))
        except Exception:
            pass
    settings = cfg.get('export_settings') or {}
    kb.row(IB(f"{('✅' if settings.get('sheet_enabled', True) else '⬜')} Автовыгрузка Sheets: {('ВКЛ' if settings.get('sheet_enabled', True) else 'ВЫКЛ')}", callback_data='v149:google:toggle_sheet'))
    kb.row(IB(f"📜 История ({len(cfg.get('history') or [])})", callback_data='v149:google:history'), IB(f"⚠️ Ошибки ({len(cfg.get('errors') or [])})", callback_data='v149:google:errors'))
    return kb

# --- google:0083 · from 10_split_policy_offload.py:3555 · public _r7_google_test ---
def _r7_google_test(tenant_id):
    ok, text = _split_tenant_google_test(str(tenant_id))
    if ok:
        try:
            m = re.search(r'Название:\s*(.+)', str(text))
            cfg = tenant_google_config(str(tenant_id))
            if m:
                cfg['spreadsheet_title'] = str(m.group(1)).strip()[:200]
            info = _r7_google_worker_info()
            if info.get('service_email'):
                cfg['service_account_email'] = str(info.get('service_email'))[:250]
            cfg['updated_at'] = _v149_now_iso()
            tenant_google_history(str(tenant_id), 'sheet_access_verified_r7', cfg.get('spreadsheet_title') or 'access OK', ok=True)
            tenant_google_persist(str(tenant_id), 'tenant_google_update')
        except Exception:
            pass
    return ok, text

# --- google:0084 · from 10_split_policy_offload.py:3576 · public _r7_google_handle_message ---
def _r7_google_handle_message(msg) -> bool:
    # Handle the table-link step ourselves so save + access test is one action.
    try:
        cid = int(msg.chat.id)
        uid = int(getattr(getattr(msg, 'from_user', None), 'id', 0) or 0)
        tid = str(tenant_id_for_chat(cid, create=False) or '')
        cfg = tenant_google_config(tid, create=False) if tid else {}
        wait = dict((cfg or {}).get('input_wait') or {})
        if wait and str(wait.get('kind') or '') == 'sheet' and int(wait.get('chat_id') or 0) == cid and int(wait.get('user_id') or 0) == uid:
            if str(getattr(msg, 'content_type', '')) != 'text':
                send_and_auto_delete(cid, 'Пришлите ссылку на Google Таблицу обычным текстом.', 10)
                return True
            value = str(getattr(msg, 'text', '') or '').strip()
            cfg['spreadsheet_id'] = _v149_google_id(value, 'sheet')
            cfg['spreadsheet_title'] = ''
            cfg['input_wait'] = {}
            cfg['updated_at'] = _v149_now_iso()
            tenant_google_persist(tid, 'tenant_google_update')
            try:
                DELAYED_SCHEDULER.cancel(f'v213-input-google:{tid}:{cid}:{uid}')
                _v172_delete_quiet(cid, int(wait.get('cancel_message_id') or 0))
                bot.delete_message(cid, msg.message_id)
            except Exception:
                pass
            ok, test_text = _r7_google_test(tid)
            if ok:
                bot.send_message(cid, '✅ Таблица подключена и доступ проверен.\n\n' + _r7_google_status_text(tid), reply_markup=_r7_google_keyboard(tid))
            else:
                bot.send_message(cid, '🟡 Ссылка сохранена, но доступа пока нет.\n\n' + test_text + '\n\nНажмите «Email для доступа», добавьте его как Редактора и затем «Проверить доступ».', reply_markup=_r7_google_keyboard(tid))
            return True
    except Exception as exc:
        try: send_and_auto_delete(int(msg.chat.id), '❌ Google: ' + str(exc)[:600], 20)
        except Exception: pass
        return True
    return bool(_GOOGLE_HANDLE_CORE(msg)) if callable(_GOOGLE_HANDLE_CORE) else False

# --- google:0085 · from 10_split_policy_offload.py:3936 · public _r7_front_google_forbidden ---
def _r7_front_google_forbidden(*args, **kwargs):
    raise RuntimeError('Google network work is isolated on Render #2. Use /google or the worker export path.')

# --- google:0086 · from 10_split_policy_offload.py:5470 · public _r29_google_keyboard ---
def _r29_google_keyboard(tenant_id):
    kb = _R29_GOOGLE_KB_CORE(tenant_id) if callable(_R29_GOOGLE_KB_CORE) else types.InlineKeyboardMarkup()
    try:
        rows = list(getattr(kb, 'keyboard', None) or [])
        callbacks = {_r29_button_callback(b) for row in rows for b in (row or [])}
        if 'nav_prev' not in callbacks:
            kb.row(IB('🔙 Назад', callback_data='nav_prev'), IB('❌ Закрыть', callback_data='info_close'))
    except Exception:
        pass
    return kb

# --- google:0087 · from 10_split_policy_offload.py:5482 · public _r29_google_status ---
def _r29_google_status(tenant_id) -> str:
    try:
        return str(_R29_GOOGLE_STATUS_CORE(tenant_id)) if callable(_R29_GOOGLE_STATUS_CORE) else '📊 Google'
    except Exception as exc:
        return '📊 Google\n\nОшибка локального статуса: ' + str(exc)[:300]

# --- google:0088 · from 10_split_policy_offload.py:5489 · public _r29_google_back_keyboard ---
def _r29_google_back_keyboard():
    kb = types.InlineKeyboardMarkup(row_width=1)
    kb.row(IB('🔙 В Google', callback_data='v149:google:status'))
    kb.row(IB('❌ Закрыть', callback_data='info_close'))
    return kb

# --- google:0089 · from 10_split_policy_offload.py:5496 · public _r29_google_edit ---
def _r29_google_edit(chat_id: int, message_id: int, text: str, kb=None, parse_mode=None, purpose='r29_google'):
    return fast_ui_edit_message_text(int(chat_id), int(message_id), str(text)[:4000], reply_markup=kb, parse_mode=parse_mode, purpose=purpose)

# --- google:0090 · from 10_split_policy_offload.py:5500 · public _r29_google_persist_background ---
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

# --- google:0091 · from 10_split_policy_offload.py:5518 · public _r29_google_begin_wait ---
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

# --- google:0092 · from 10_split_policy_offload.py:5551 · public _google_extension_callback ---
def _google_extension_callback(call, data_str: str) -> bool:
    raw = str(data_str or '')
    if not raw.startswith('v149:google:'):
        return False
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
                fn = _R29_GOOGLE_TEST_CORE or globals().get('_r7_google_test')
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
    # Unknown Google action is consumed here; there is no predecessor callback chain.
    return True

# --- google:0093 · from 10_split_policy_offload.py:5669 · public _r29_google_handle_message ---
def _r29_google_handle_message(msg) -> bool:
    try:
        cid = int(msg.chat.id)
        uid = int(getattr(getattr(msg, 'from_user', None), 'id', 0) or 0)
        tid = str(tenant_id_for_chat(cid, create=False) or '')
        cfg = tenant_google_config(tid, create=False) if tid else {}
        wait = dict((cfg or {}).get('input_wait') or {})
        if not wait or not bool(wait.get('r29_single_window')):
            return bool(_R29_GOOGLE_HANDLE_CORE(msg)) if callable(_R29_GOOGLE_HANDLE_CORE) else False
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
                fn = _R29_GOOGLE_TEST_CORE or globals().get('_r7_google_test')
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

# --- google:0094 · from 10_split_policy_offload.py:7457 · public _r38_google_submit_report ---
def _r38_google_submit_report(title,rows,layout='category',annotations_override=None,include_annotations=True,**kwargs):
    if not _split_env_bool('SPLIT_GOOGLE_REMOTE_ENABLED',True): raise RuntimeError('Google Sheets worker delegation disabled')
    target_chat_id=kwargs.get('target_chat_id'); notify_result=bool(kwargs.get('notify_result',True)); recipient_chat_id=kwargs.get('recipient_chat_id') or target_chat_id
    tid,spreadsheet_id=_split_google_target(target_chat_id=target_chat_id,tenant_id=kwargs.get('tenant_id'))
    annotations=_split_annotations_for_google(rows,str(layout or 'category'),annotations_override,bool(include_annotations))
    encoded={f'{int(r)},{int(c)}':str(note) for (r,c),note in annotations.items() if str(note or '').strip()}
    jid=__import__('secrets').token_hex(12)
    body={'job_id':jid,'title':str(title or 'Статьи')[:300],'rows':rows,'layout':str(layout or 'category'),'annotations':encoded,'include_annotations':bool(include_annotations),'spreadsheet_id':spreadsheet_id,'tenant_id':tid,'target_chat_id':target_chat_id,'recipient_chat_id':recipient_chat_id,'notify_result':notify_result,'front_release':'Пер-R43'}
    _r38_outbox_enqueue('google','/internal/google/sheet',body)
    try:
        _SPLIT_STATE['google_last_attempt']=_r33_time.time(); _SPLIT_STATE['google_last_job']=jid; _SPLIT_STATE['google_last_error']=''
    except Exception: pass
    return 'worker-job:'+jid

# --- google:0095 · from 10_split_policy_offload.py:7515 · public _r38_tenant_google_test ---
def _r38_tenant_google_test(tenant_id):
    try:
        tid,spreadsheet_id=_split_google_target(tenant_id=str(tenant_id))
        r,payload=_r38_sync_peer_json('POST','/internal/google/test',json_body={'spreadsheet_id':spreadsheet_id,'tenant_id':tid},timeout=18,max_wait=60,agent='per-r38-front-google-test')
        if 200<=int(r.status_code)<300 and payload.get('ok'):
            return True,f"✅ Google Таблица доступна через Render #2.\nНазвание: {payload.get('title') or '—'}\nService account: {payload.get('service_email') or '—'}"
        return False,'❌ Проверка Google: '+str(payload.get('error') or f'HTTP {r.status_code}')[:600]
    except Exception as exc:
        return False,'❌ Проверка Google: '+str(exc)[:600]

# --- google:0096 · from 10_split_policy_offload.py:7526 · public _r38_google_worker_info ---
def _r38_google_worker_info(fetch=True):
    # Preserve R7 cache semantics but do not let a short Render restart surface as HTML/503.
    cache=globals().get('_R7_GOOGLE_INFO_CACHE')
    now=_r33_time.time(); cached=dict((cache or {}).get('data') or {}) if isinstance(cache,dict) else {}
    if cached and (not fetch or now-float((cache or {}).get('ts') or 0)<600): return cached
    if not fetch:return cached
    try:
        r,payload=_r38_sync_peer_json('GET','/internal/google/info',timeout=8,max_wait=30,agent='per-r38-front-google-info')
        if 200<=int(r.status_code)<300 and payload.get('ok'):
            if isinstance(cache,dict): cache.update(ts=now,data=dict(payload))
            return dict(payload)
    except Exception: pass
    return cached

# --- google:0097 · from 10_split_policy_offload.py:7544 · public _r38_google_result_handler ---
def _r38_google_result_handler():
    if not globals().get('_split_authorized_request',lambda:False)(): return ({'ok':False},404)
    body=request.get_json(silent=True) or {}; jid=str(body.get('job_id') or '').strip()
    if not jid:return ({'ok':False,'error':'job_id required'},400)
    out=_r38_outbox_get(jid)
    if str(out.get('result_state') or '')=='done': return ({'ok':True,'duplicate':True,'delivered':True},200)
    try: cid=int(body.get('recipient_chat_id') or 0)
    except Exception: cid=0
    if not cid:return ({'ok':False,'error':'recipient_chat_id required'},400)
    try:
        if bool(body.get('notify_result',True)):
            if bool(body.get('ok')):
                text=f"✅ 📊 Google Excel готов\n{str(body.get('title') or 'Google Excel')[:180]}\n\n{str(body.get('url') or '').strip()}"
                bot.send_message(cid,text,disable_web_page_preview=True)
            else:
                err=str(body.get('error') or 'Render #2 завершил Google-задачу с ошибкой')[:700]
                bot.send_message(cid,'❌ Google Excel не создан на Render #2:\n'+err)
        out=out if isinstance(out,dict) else {'job_id':jid,'kind':'google'}
        out.update({'job_id':jid,'state':'completed','result_state':'done','result_ok':bool(body.get('ok')),'result_url':str(body.get('url') or ''),'result_title':str(body.get('title') or ''),'result_at':_r33_time.time(),'last_error':str(body.get('error') or '')[:500]})
        _r38_outbox_put(out,pending=False)
        try:
            if body.get('ok'):_SPLIT_STATE['google_last_ok']=_r33_time.time(); _SPLIT_STATE['google_last_error']=''
            else:_SPLIT_STATE['google_last_error']=str(body.get('error') or '')[:240]
        except Exception: pass
        return ({'ok':True,'delivered':True},200)
    except Exception as exc:
        return ({'ok':False,'error':f'{type(exc).__name__}: {str(exc)[:300]}'},503)

# --- google:0098 · from 10_split_policy_offload.py:8015 · public _r40_google_query_submit ---
def _legacy_s0098_r40_google_query_submit(title,target_chat_id,start_key,end_key,start_rid=0,end_rid=0,layout='category',include_annotations=True,notify_result=False,recipient_chat_id=None):
    target_chat_id=int(target_chat_id); recipient_chat_id=int(recipient_chat_id or target_chat_id)
    tid,spreadsheet_id=_split_google_target(target_chat_id=target_chat_id,tenant_id=None)
    jid=__import__('secrets').token_hex(12)
    try: required=int((_R32_EVENT_STATE or {}).get('last_revision_queued') or 0)
    except Exception: required=0
    body={'job_id':jid,'operation':'google_exact_query','title':str(title or 'Статьи')[:300],'layout':str(layout or 'category'),'include_annotations':bool(include_annotations),'spreadsheet_id':spreadsheet_id,'tenant_id':tid,'target_chat_id':target_chat_id,'recipient_chat_id':recipient_chat_id,'notify_result':bool(notify_result),'start_key':str(start_key or '')[:10],'start_rid':int(start_rid or 0),'end_key':str(end_key or '')[:10],'end_rid':int(end_rid or 0),'required_revision':required,'front_release':'Пер-R43'}
    jid2=_r38_outbox_enqueue('google','/internal/google/sheet',body)
    return str(jid2)

# --- google:0099 · from 10_split_policy_offload.py:8026 · public _r40_google_wait ---
def _legacy_s0099_r40_google_wait(jid,timeout=900):
    deadline=_r33_time.time()+max(30,min(3600,int(timeout or 900)))
    while _r33_time.time()<deadline:
        row=_r38_outbox_get(str(jid)) or {}
        if str(row.get('result_state') or '')=='done':
            return bool(row.get('result_ok')),str(row.get('result_url') or ''),str(row.get('last_error') or '')
        if str(row.get('state') or '')=='failed': return False,'',str(row.get('last_error') or 'Google job dispatch failed')
        _r33_time.sleep(0.5)
    return False,'',f'Google job timeout {int(timeout)} sec'

# --- google:0100 · from 10_split_policy_offload.py:8995 · public _r71_fast_google_ready ---
def _r71_fast_google_ready():
    try:
        fn = globals().get('_google_service_account_info')
        if callable(fn):
            info = fn()
            return bool(isinstance(info, dict) and info.get('client_email') and info.get('private_key'))
    except Exception:
        pass
    try:
        return bool(str(_split_os.getenv('GOOGLE_SERVICE_ACCOUNT_JSON', '') or '').strip())
    except Exception:
        return False

# --- google:0101 · from 10_split_policy_offload.py:9173 · public _r71_google_create ---
def _legacy_s0101_r71_google_create(title, rows, layout='category', annotations_override=None, include_annotations=True, **kwargs):
    if not _r71_route_is_fast('google'):
        return _R71_REMOTE_GOOGLE_CREATE(title, rows, layout=layout, annotations_override=annotations_override, include_annotations=include_annotations, **kwargs)
    creator = globals().get('_canon_google_sheets_create_category_report__001')
    if not callable(creator):
        raise RuntimeError('R1 Google creator unavailable')
    target_chat_id = kwargs.get('target_chat_id')
    tenant_id = kwargs.get('tenant_id')
    url = creator(title, rows, layout=layout, annotations_override=annotations_override, include_annotations=include_annotations, tenant_id=tenant_id, target_chat_id=target_chat_id)
    recipient = kwargs.get('recipient_chat_id') or target_chat_id
    if bool(kwargs.get('notify_result', False)) and recipient:
        try: bot.send_message(int(recipient), f'✅ 📊 Google Excel готов на R1 FAST\n{str(title or "Google Excel")[:180]}\n\n{url}', disable_web_page_preview=True)
        except Exception: pass
    try: _SPLIT_STATE['google_last_ok'] = _r33_time.time(); _SPLIT_STATE['google_last_error'] = ''
    except Exception: pass
    return str(url)

# --- google:0102 · from 10_split_policy_offload.py:9406 · public _r40_google_query_submit ---
def _legacy_s0102_r40_google_query_submit(title,target_chat_id,start_key,end_key,start_rid=0,end_rid=0,layout='category',include_annotations=True,notify_result=False,recipient_chat_id=None):
    if not _r71_route_is_fast('google'):
        return _R71_REMOTE_GOOGLE_QUERY_SUBMIT(title,target_chat_id,start_key,end_key,start_rid,end_rid,layout=layout,include_annotations=include_annotations,notify_result=notify_result,recipient_chat_id=recipient_chat_id)
    jid = 'r71local-' + __import__('secrets').token_hex(10)
    ok = False; url = ''; err = ''
    try:
        rows = build_exact_category_stats_xlsx_rows(int(target_chat_id), str(start_key), int(start_rid or 0), str(end_key), int(end_rid or 0))
        url = _r71_google_create(title, rows, layout=layout, annotations_override={}, include_annotations=include_annotations, target_chat_id=int(target_chat_id), recipient_chat_id=int(recipient_chat_id or target_chat_id), notify_result=bool(notify_result))
        ok = bool(url)
    except Exception as exc:
        err = f'{type(exc).__name__}: {str(exc)[:700]}'
    with _R71_LOCAL_GOOGLE_RESULTS_LOCK:
        _R71_LOCAL_GOOGLE_RESULTS[jid] = (bool(ok), str(url or ''), str(err or ''), _r33_time.time())
        cutoff = _r33_time.time() - 3600
        for key, row in list(_R71_LOCAL_GOOGLE_RESULTS.items()):
            if float((row or (False,'','',0))[3] or 0) < cutoff:
                _R71_LOCAL_GOOGLE_RESULTS.pop(key, None)
    return jid

# --- google:0103 · from 10_split_policy_offload.py:9426 · public _r40_google_wait ---
def _legacy_s0103_r40_google_wait(jid, timeout=900):
    key = str(jid or '')
    if key.startswith('r71local-'):
        with _R71_LOCAL_GOOGLE_RESULTS_LOCK:
            row = _R71_LOCAL_GOOGLE_RESULTS.pop(key, None)
        if row:
            return bool(row[0]), str(row[1]), str(row[2])
        return False, '', 'R1 Google local result not found'
    return _R71_REMOTE_GOOGLE_WAIT(jid, timeout=timeout)

# --- google:0104 · from 10_split_policy_offload.py:9437 · public _split_tenant_google_test ---
def _legacy_s0104_split_tenant_google_test(tenant_id):
    if _r71_route_is_fast('google'):
        fn = globals().get('tenant_google_test')
        if callable(fn):
            ok, text = fn(str(tenant_id))
            text = str(text or '')
            if ok and 'R1 FAST' not in text:
                text = text.replace('✅', '✅ R1 FAST ·', 1)
            return bool(ok), text
        return False, '❌ R1 Google test unavailable'
    return _R71_REMOTE_GOOGLE_TEST(tenant_id)

# --- google:0105 · from 10_split_policy_offload.py:9450 · public _r7_google_worker_info ---
def _legacy_s0105_r7_google_worker_info(fetch=True):
    if _r71_route_is_fast('google'):
        try:
            info = _google_service_account_info()
            return {'ok':True, 'service_email':str(info.get('client_email') or ''), 'owner':'R1 FAST'}
        except Exception as exc:
            return {'ok':False, 'error':str(exc)[:500], 'owner':'R1 FAST'}
    return _R71_REMOTE_GOOGLE_INFO(fetch)

# --- google:0106 · from 10_split_policy_offload.py:13845 · public _r1234_google_local_create ---
def _r1234_google_local_create(title, rows, layout='category', annotations_override=None, include_annotations=True, **kwargs):
    creator = globals().get('_canon_google_sheets_create_category_report__001')
    if not callable(creator):
        raise RuntimeError('R1 Google creator unavailable')
    target_chat_id = kwargs.get('target_chat_id')
    tenant_id = kwargs.get('tenant_id')
    url = creator(title, rows, layout=layout, annotations_override=annotations_override,
                  include_annotations=include_annotations, tenant_id=tenant_id, target_chat_id=target_chat_id)
    recipient = kwargs.get('recipient_chat_id') or target_chat_id
    if bool(kwargs.get('notify_result', False)) and recipient:
        try: bot.send_message(int(recipient), f'✅ 📊 Google Excel готов на R1 FAST\n{str(title or "Google Excel")[:180]}\n\n{url}', disable_web_page_preview=True)
        except Exception: pass
    try:
        _SPLIT_STATE['google_last_ok'] = _split_time.time(); _SPLIT_STATE['google_last_error'] = ''
    except Exception: pass
    return str(url)

# --- google:0107 · from 10_split_policy_offload.py:13863 · public _r71_google_create ---
def _r71_google_create(title, rows, layout='category', annotations_override=None, include_annotations=True, **kwargs):
    if _r1234_use_heavy('google'):
        try:
            return _R1234_REMOTE_GOOGLE_CREATE(title, rows, layout=layout, annotations_override=annotations_override,
                                                include_annotations=include_annotations, **kwargs)
        except Exception as exc:
            _r1234_note_fallback('google', f'remote submit: {type(exc).__name__}: {str(exc)[:160]}')
    elif _r1234_accel_requested('google'):
        _r1234_note_fallback('google', 'preflight unavailable')
    return _r1234_google_local_create(title, rows, layout=layout, annotations_override=annotations_override,
                                      include_annotations=include_annotations, **kwargs)

# --- google:0108 · from 10_split_policy_offload.py:13895 · public _r40_google_query_submit ---
def _r40_google_query_submit(title,target_chat_id,start_key,end_key,start_rid=0,end_rid=0,layout='category',include_annotations=True,notify_result=False,recipient_chat_id=None):
    if _r1234_use_heavy('google'):
        try:
            return _R1234_REMOTE_GOOGLE_QUERY(title,target_chat_id,start_key,end_key,start_rid,end_rid,layout=layout,
                                               include_annotations=include_annotations,notify_result=notify_result,
                                               recipient_chat_id=recipient_chat_id)
        except Exception as exc:
            _r1234_note_fallback('google-query', f'remote submit: {type(exc).__name__}: {str(exc)[:160]}')
    elif _r1234_accel_requested('google'):
        _r1234_note_fallback('google-query', 'preflight unavailable')
    jid = 'r1234local-' + __import__('secrets').token_hex(10)
    ok = False; url = ''; err = ''
    try:
        rows = build_exact_category_stats_xlsx_rows(int(target_chat_id), str(start_key), int(start_rid or 0), str(end_key), int(end_rid or 0))
        url = _r1234_google_local_create(title, rows, layout=layout, annotations_override={}, include_annotations=include_annotations,
                                         target_chat_id=int(target_chat_id), recipient_chat_id=int(recipient_chat_id or target_chat_id),
                                         notify_result=bool(notify_result))
        ok = bool(url)
    except Exception as exc:
        err = f'{type(exc).__name__}: {str(exc)[:700]}'
    with _R71_LOCAL_GOOGLE_RESULTS_LOCK:
        _R71_LOCAL_GOOGLE_RESULTS[jid] = (bool(ok), str(url or ''), str(err or ''), _r33_time.time())
    return jid

# --- google:0109 · from 10_split_policy_offload.py:13921 · public _r40_google_wait ---
def _r40_google_wait(jid, timeout=900):
    key = str(jid or '')
    if key.startswith('r1234local-'):
        with _R71_LOCAL_GOOGLE_RESULTS_LOCK:
            row = _R71_LOCAL_GOOGLE_RESULTS.pop(key, None)
        if row: return bool(row[0]), str(row[1]), str(row[2])
        return False, '', 'R1 Google local result not found'
    return _R1234_GOOGLE_WAIT_CHAIN(jid, timeout=timeout)

# --- google:0110 · from 10_split_policy_offload.py:13931 · public _split_tenant_google_test ---
def _split_tenant_google_test(tenant_id):
    if _r1234_use_heavy('google'):
        try: return _R1234_REMOTE_GOOGLE_TEST(tenant_id)
        except Exception as exc: _r1234_note_fallback('google-test', str(exc)[:180])
    try:
        fn = globals().get('tenant_google_test')
        if callable(fn):
            ok, text = fn(str(tenant_id)); text = str(text or '')
            if ok and 'R1 FAST' not in text: text = text.replace('✅', '✅ R1 FAST ·', 1)
            return bool(ok), text
    except Exception as exc:
        return False, '❌ R1 Google test: ' + str(exc)[:600]
    return False, '❌ R1 Google test unavailable'

# --- google:0111 · from 10_split_policy_offload.py:13946 · public _r7_google_worker_info ---
def _r7_google_worker_info(fetch=True):
    if _r1234_use_heavy('google'):
        try: return _R1234_REMOTE_GOOGLE_INFO(fetch)
        except Exception as exc: _r1234_note_fallback('google-info', str(exc)[:180])
    try:
        info = _google_service_account_info()
        return {'ok':True, 'service_email':str(info.get('client_email') or ''), 'owner':'R1 FAST', 'fallback':bool(_r1234_accel_requested('google'))}
    except Exception as exc:
        return {'ok':False, 'error':str(exc)[:500], 'owner':'R1 FAST'}

# v267
