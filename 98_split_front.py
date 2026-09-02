# v262
"""Render #1 fast split bridge for vys-262.

Render #1 keeps Telegram/webhook/UI and the working SQLite commit path.
Remote durability and Google Sheets network work are delegated to Render #2.
MEGA is disabled during normal runtime on the front; start_front.py keeps only the
cold emergency restore path for deploy/startup recovery.
"""
import gzip as _split_gzip
import json as _split_json
import collections as _split_collections
import os as _split_os
import secrets as _split_secrets
import shutil as _split_shutil
import tempfile as _split_tempfile
import threading as _split_threading
import time as _split_time
try:
    import redis as _split_redis
except Exception:
    _split_redis = None

_SPLIT_FRONT_VERSION = "vys-262-front-r9-google-style"
_SPLIT_SYNC_LOCK = _split_threading.RLock()
_SPLIT_SYNC_TIMER = None
_SPLIT_SYNC_DUE_AT = 0.0
_SPLIT_CHANGE_LOCK = _split_threading.RLock()
_SPLIT_CHANGE_EPOCH = _split_secrets.token_hex(6)
_SPLIT_CHANGE_SEQ = 0
_SPLIT_STATE_TOKEN = f"{_SPLIT_CHANGE_EPOCH}:0"
_SPLIT_UPDATE_CONTEXT = _split_threading.local()
_SPLIT_GOOGLE_RESULT_LOCK = _split_threading.RLock()
_SPLIT_GOOGLE_RESULTS = {}
_SPLIT_STATE = {
    "peer_last_attempt": 0.0,
    "peer_last_ok": 0.0,
    "peer_last_error": "",
    "peer_status": None,
    "sync_last_attempt": 0.0,
    "sync_last_ok": 0.0,
    "sync_last_error": "",
    "sync_pending": False,
    "sync_reason": "",
    "google_last_attempt": 0.0,
    "google_last_ok": 0.0,
    "google_last_error": "",
    "google_last_job": "",
    "state_token": _SPLIT_STATE_TOKEN,
    "state_change_reason": "boot",
    "redis_fallback_last_ok": 0.0,
    "redis_fallback_last_error": "",
}


def _split_env_bool(name, default=True):
    return str(_split_os.getenv(name, "1" if default else "0") or "").strip().lower() in {"1", "true", "yes", "on", "да"}


def _split_peer_base():
    raw = str(_split_os.getenv("PEER_SERVICE_URL", "") or "").strip().rstrip("/")
    if raw and not raw.startswith(("http://", "https://")):
        raw = "https://" + raw
    return raw


def _split_secret():
    return str(_split_os.getenv("PEER_SHARED_SECRET", "") or "").strip()


def _split_headers(agent="vys-262-front-peer"):
    return {"X-Peer-Secret": _split_secret(), "User-Agent": agent}


def _split_authorized_request():
    secret = _split_secret()
    supplied = str(request.headers.get("X-Peer-Secret", "") or "")
    return bool(secret and _split_secrets.compare_digest(secret, supplied))


def _split_mark_state_changed_v264(reason='change'):
    global _SPLIT_CHANGE_SEQ, _SPLIT_STATE_TOKEN
    with _SPLIT_CHANGE_LOCK:
        _SPLIT_CHANGE_SEQ += 1
        _SPLIT_STATE_TOKEN = f"{_SPLIT_CHANGE_EPOCH}:{_SPLIT_CHANGE_SEQ}"
        _SPLIT_STATE['state_token'] = _SPLIT_STATE_TOKEN
        _SPLIT_STATE['state_change_reason'] = str(reason or 'change')[:160]
        return _SPLIT_STATE_TOKEN


def _split_current_state_token_v264():
    with _SPLIT_CHANGE_LOCK:
        return str(_SPLIT_STATE_TOKEN)


def _split_snapshot_meta():
    try:
        root = SQLITE.load_root() or {}
        state_meta = root.get("_state_meta") if isinstance(root, dict) else {}
        return {
            "last_saved_at": str((state_meta or {}).get("last_saved_at") or ""),
            "cold_records": int(SQLITE.cold_count() or 0),
            "db_file": str(globals().get("DB_FILE") or "bot_state.sqlite3"),
        }
    except Exception as exc:
        return {"error": str(exc)[:160]}


@app.route('/peer/health', methods=['GET', 'HEAD'])
def split_front_peer_health_v262():
    if request.method == 'HEAD':
        return ('', 200)
    return ({
        'ok': True,
        'role': 'front',
        'version': _SPLIT_FRONT_VERSION,
        'bot_version': str(globals().get('VERSION') or ''),
        'ready': bool(globals().get('runtime_is_ready', lambda: False)()),
        'phase': (globals().get('_RUNTIME_STATE') or {}).get('phase'),
        'snapshot': _split_snapshot_meta(),
        'peer': dict(_SPLIT_STATE),
    }, 200)


@app.route('/internal/split/state', methods=['GET'])
def split_front_state_download_v262():
    """Return a transactionally consistent SQLite gzip to the worker."""
    if not _split_authorized_request():
        return ({'ok': False}, 404)
    workdir = _split_tempfile.mkdtemp(prefix='v262_front_state_')
    raw = _split_os.path.join(workdir, 'bot_state.sqlite3')
    gz = raw + '.gz'
    try:
        snapshot_token = _split_current_state_token_v264()
        SQLITE.backup_to(raw)
        with open(raw, 'rb') as src, _split_gzip.open(gz, 'wb', compresslevel=9) as dst:
            _split_shutil.copyfileobj(src, dst, length=1024 * 1024)
        with open(gz, 'rb') as fh:
            payload = fh.read()
        response = app.response_class(payload, status=200, mimetype='application/gzip')
        response.headers['Content-Disposition'] = 'attachment; filename="latest_bot_state.sqlite3.gz"'
        response.headers['X-Split-Version'] = _SPLIT_FRONT_VERSION
        response.headers['X-Split-Size'] = str(len(payload))
        response.headers['X-Split-State-Token'] = snapshot_token
        return response
    except Exception as exc:
        return ({'ok': False, 'error': str(exc)[:240]}, 500)
    finally:
        _split_shutil.rmtree(workdir, ignore_errors=True)



def _split_redis_snapshot_keys_v266():
    key = str(_split_os.getenv('WORKER_REDIS_SNAPSHOT_KEY', 'vys262:bot_state:latest_gz') or 'vys262:bot_state:latest_gz').strip()
    return key, key + ':meta'


def _split_cache_snapshot_to_redis_v266(reason='front_fallback', existing_gz=None):
    """Best-effort durable bridge when worker is unavailable or being redeployed.

    Runs only from background sync/shutdown paths, never inline in Telegram handling.
    """
    if _split_redis is None:
        _SPLIT_STATE['redis_fallback_last_error'] = 'redis package unavailable'
        return False
    url = str(_split_os.getenv('REDIS_URL', '') or '').strip()
    if not url:
        _SPLIT_STATE['redis_fallback_last_error'] = 'REDIS_URL empty'
        return False
    workdir = None
    try:
        if existing_gz:
            gz = str(existing_gz)
        else:
            workdir = _split_tempfile.mkdtemp(prefix='v266_front_redis_')
            raw = _split_os.path.join(workdir, 'bot_state.sqlite3')
            gz = raw + '.gz'
            SQLITE.backup_to(raw)
            with open(raw, 'rb') as src, _split_gzip.open(gz, 'wb', compresslevel=9) as dst:
                _split_shutil.copyfileobj(src, dst, length=1024 * 1024)
        payload = open(gz, 'rb').read()
        max_mb = max(1, min(128, int(_split_os.getenv('WORKER_REDIS_SNAPSHOT_MAX_MB', '16') or '16')))
        if len(payload) > max_mb * 1024 * 1024:
            raise RuntimeError(f'snapshot too large for Redis: {len(payload)}')
        # revision is derived from the same SQLite image by the worker; the side meta is informational.
        revision = 0.0
        try:
            for kind in ('user_state_shadow_v265', 'runtime_continuity_v263'):
                row = SQLITE.get_meta(kind, 'latest', {}) or {}
                revision = max(revision, float((row or {}).get('saved_at') or 0.0))
        except Exception:
            pass
        key, meta_key = _split_redis_snapshot_keys_v266()
        client = _split_redis.Redis.from_url(url, socket_connect_timeout=3, socket_timeout=8, health_check_interval=30)
        meta = {'revision': revision, 'size': len(payload), 'saved_at': _split_time.time(), 'reason': str(reason or '')[:160], 'source': 'front-r6'}
        pipe = client.pipeline(transaction=True)
        pipe.set(key, payload)
        pipe.set(meta_key, _split_json.dumps(meta, separators=(',', ':')))
        pipe.execute()
        _SPLIT_STATE['redis_fallback_last_ok'] = _split_time.time()
        _SPLIT_STATE['redis_fallback_last_error'] = ''
        return True
    except Exception as exc:
        _SPLIT_STATE['redis_fallback_last_error'] = f'{type(exc).__name__}: {str(exc)[:180]}'
        return False
    finally:
        if workdir:
            _split_shutil.rmtree(workdir, ignore_errors=True)


def _split_ping_once():
    base = _split_peer_base()
    _SPLIT_STATE['peer_last_attempt'] = _split_time.time()
    if not base:
        _SPLIT_STATE['peer_last_error'] = 'PEER_SERVICE_URL empty'
        return False
    try:
        r = requests.get(base + '/peer/health', headers=_split_headers(), timeout=12)
        _SPLIT_STATE['peer_status'] = int(r.status_code)
        if 200 <= r.status_code < 300:
            _SPLIT_STATE['peer_last_ok'] = _split_time.time()
            _SPLIT_STATE['peer_last_error'] = ''
            return True
        _SPLIT_STATE['peer_last_error'] = f'HTTP {r.status_code}'
    except Exception as exc:
        _SPLIT_STATE['peer_last_error'] = str(exc)[:220]
        _SPLIT_STATE['peer_status'] = None
    return False


def _split_peer_loop():
    _split_time.sleep(5.0)
    while True:
        if _split_env_bool('PEER_PING_ENABLED', True):
            _split_ping_once()
        _split_time.sleep(600)


def _split_request_sync_now(reason='change'):
    base, secret = _split_peer_base(), _split_secret()
    _SPLIT_STATE['sync_last_attempt'] = _split_time.time()
    _SPLIT_STATE['sync_reason'] = str(reason or 'change')[:160]
    if not base or not secret:
        _SPLIT_STATE['sync_last_error'] = 'worker URL/secret not configured'
        return False
    body = {
        'type': 'sync_state',
        'reason': _SPLIT_STATE['sync_reason'],
        'front_url': str(globals().get('APP_URL') or '').rstrip('/'),
        'state_token': _split_current_state_token_v264(),
    }
    try:
        r = requests.post(base + '/internal/job', json=body, headers=_split_headers(), timeout=10)
        if 200 <= r.status_code < 300:
            _SPLIT_STATE['sync_last_ok'] = _split_time.time()
            _SPLIT_STATE['sync_last_error'] = ''
            _SPLIT_STATE['sync_pending'] = False
            return True
        _SPLIT_STATE['sync_last_error'] = f'HTTP {r.status_code}: {r.text[:160]}'
    except Exception as exc:
        _SPLIT_STATE['sync_last_error'] = str(exc)[:220]
    # Worker may be between deploys. Preserve the newest exact SQLite in shared Redis
    # so neither a front nor a worker restart can roll user settings back.
    try:
        _split_cache_snapshot_to_redis_v266(reason='worker_sync_fallback:' + str(reason or 'change')[:100])
    except Exception:
        pass
    return False


def _split_sync_timer_fire():
    global _SPLIT_SYNC_TIMER, _SPLIT_SYNC_DUE_AT
    try:
        reason = str(_SPLIT_STATE.get('sync_reason') or 'change')
        _split_request_sync_now(reason)
    finally:
        with _SPLIT_SYNC_LOCK:
            _SPLIT_SYNC_TIMER = None
            _SPLIT_SYNC_DUE_AT = 0.0


def _split_inside_telegram_update_v264():
    return bool(getattr(_SPLIT_UPDATE_CONTEXT, 'active', False))


def split_schedule_worker_sync_v262(reason='change', delay=None):
    """Coalesced state handoff; Telegram never waits for MEGA or snapshot transfer."""
    global _SPLIT_SYNC_TIMER, _SPLIT_SYNC_DUE_AT
    if not _split_env_bool('SPLIT_WORKER_SYNC_ENABLED', True):
        return False
    # One Telegram update may call save_data/config/finance hooks many times. R4
    # could arm the worker while the handler was still executing, then arm it again
    # at the post-update continuity checkpoint. Defer all those requests and emit
    # exactly one notification after the update completes.
    if _split_inside_telegram_update_v264():
        _SPLIT_STATE['sync_pending'] = True
        _SPLIT_STATE['sync_reason'] = str(reason or 'change')[:160]
        return True
    try:
        wait = float(delay if delay is not None else _split_os.getenv('SPLIT_STATE_SYNC_DELAY_SEC', '1.5') or '1.5')
    except Exception:
        wait = 1.5
    try:
        min_interval = float(_split_os.getenv('SPLIT_STATE_SYNC_MIN_INTERVAL_SEC', '5') or '5')
    except Exception:
        min_interval = 12.0
    wait = max(0.08, min(30.0, wait))
    min_interval = max(1.0, min(120.0, min_interval))
    now = _split_time.time()
    last = float(_SPLIT_STATE.get('sync_last_attempt') or 0.0)
    due = max(now + wait, last + min_interval if last else now + wait)
    _SPLIT_STATE['sync_pending'] = True
    _SPLIT_STATE['sync_reason'] = str(reason or 'change')[:160]
    with _SPLIT_SYNC_LOCK:
        # Keep the earliest scheduled transfer. Repeated mutations are coalesced
        # instead of repeatedly postponing a full SQLite snapshot.
        if _SPLIT_SYNC_TIMER is not None and _SPLIT_SYNC_DUE_AT and _SPLIT_SYNC_DUE_AT <= due + 0.05:
            return True
        if _SPLIT_SYNC_TIMER is not None:
            try:
                _SPLIT_SYNC_TIMER.cancel()
            except Exception:
                pass
        _SPLIT_SYNC_DUE_AT = due
        _SPLIT_SYNC_TIMER = _split_threading.Timer(max(0.05, due - now), _split_sync_timer_fire)
        _SPLIT_SYNC_TIMER.daemon = True
        _SPLIT_SYNC_TIMER.start()
    return True


# Final durability bindings for split mode. SQLite has already been committed by the
# normal save path; these hooks only request remote durability from Render #2.
def _v262_split_schedule_delta_backup(chat_id=None, delay=None, reason='change'):
    split_schedule_worker_sync_v262(reason=f'delta:{reason}', delay=delay)
    return True


def _v262_split_persist_critical_delta_now(chat_id):
    split_schedule_worker_sync_v262(reason=f'critical:{int(chat_id)}', delay=0.08)
    return True


def _v262_split_schedule_full_backup_only(chat_id, delay=3.0):
    split_schedule_worker_sync_v262(reason=f'full:{int(chat_id)}', delay=min(float(delay or 1.0), 5.0))
    return True


def _v262_split_mega_upload_latest_database_backup(force=False):
    split_schedule_worker_sync_v262(reason='manual_db_snapshot' if force else 'db_snapshot', delay=0.08 if force else 0.5)
    return True


def _v262_split_schedule_config_backup_for_chats(*chat_ids, delay=3.0):
    split_schedule_worker_sync_v262(reason='config:' + ','.join(map(str, chat_ids[:8])), delay=min(float(delay or 1.0), 5.0))
    return True


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


@app.route('/internal/split/google-result', methods=['POST'])
def split_front_google_result_v262():
    """Worker callback. Duplicate callbacks are acknowledged without duplicate Telegram messages."""
    if not _split_authorized_request():
        return ({'ok': False}, 404)
    body = request.get_json(silent=True) or {}
    job_id = str(body.get('job_id') or '').strip()
    if not job_id:
        return ({'ok': False, 'error': 'job_id required'}, 400)
    if _split_google_result_seen(job_id):
        return ({'ok': True, 'duplicate': True}, 200)
    try:
        recipient_chat_id = int(body.get('recipient_chat_id') or 0)
    except Exception:
        recipient_chat_id = 0
    if not recipient_chat_id:
        return ({'ok': False, 'error': 'recipient_chat_id required'}, 400)
    ok = bool(body.get('ok'))
    notify_result = bool(body.get('notify_result', True))
    if ok:
        url = str(body.get('url') or '').strip()
        title = str(body.get('title') or 'Google Excel').strip()[:180]
        _SPLIT_STATE['google_last_ok'] = _split_time.time()
        _SPLIT_STATE['google_last_error'] = ''
        if notify_result:
            text = f'✅ 📊 Google Excel готов\n{title}\n\n{url}'
            bot.send_message(recipient_chat_id, text, disable_web_page_preview=True)
    else:
        err = str(body.get('error') or 'неизвестная ошибка')[:700]
        _SPLIT_STATE['google_last_error'] = err[:240]
        if notify_result:
            bot.send_message(recipient_chat_id, '❌ Google Excel не создан на Render #2:\n' + err)
    return ({'ok': True}, 200)


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


def _split_tenant_google_test(tenant_id):
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


def _split_reject_front_google_credentials(*args, **kwargs):
    raise RuntimeError('Service account не загружается в Telegram-фронт. GOOGLE_SERVICE_ACCOUNT_JSON задаётся только в Environment Render #2.')


# New split Google callbacks are legitimate windows and must be declared.
try:
    WINDOW_MARKER_CONSTANTS.setdefault('v149:google:*', 'Ф233')
except Exception:
    pass


def _split_v167_google_upsert_named_tab(tab_title, rows, target_chat_id, layout='category', annotations_override=None):
    """Route legacy v167/v261 scheduled Google refreshes to Render #2."""
    return _v262_split_google_sheets_create_category_report(
        tab_title, rows, layout=layout, annotations_override=annotations_override,
        include_annotations=True, target_chat_id=int(target_chat_id),
        recipient_chat_id=int(target_chat_id), notify_result=False,
    )


# Apply final bindings after 89_callback_final.py.
globals()['schedule_delta_backup'] = _v262_split_schedule_delta_backup
globals()['persist_critical_delta_now'] = _v262_split_persist_critical_delta_now
globals()['schedule_full_backup_only'] = _v262_split_schedule_full_backup_only
globals()['mega_upload_latest_database_backup'] = _v262_split_mega_upload_latest_database_backup
globals()['schedule_config_backup_for_chats'] = _v262_split_schedule_config_backup_for_chats
globals()['_google_sheets_create_category_report'] = _v262_split_google_sheets_create_category_report
globals()['_v167_google_upsert_named_tab'] = _split_v167_google_upsert_named_tab
globals()['tenant_google_status_text'] = _split_tenant_google_status_text
globals()['tenant_google_keyboard'] = _split_tenant_google_keyboard
globals()['tenant_google_test'] = _split_tenant_google_test
globals()['tenant_google_set_credentials'] = _split_reject_front_google_credentials

_split_threading.Thread(target=_split_peer_loop, name='v262-front-peer', daemon=True).start()

# ---------------------------------------------------------------------------
# r4 continuity layer: deploy/restart must be invisible to the Telegram user.
# Canonical business/config state already lives in SQLite.  This layer adds the
# small RAM-only interaction state that makes existing buttons/windows/sessions
# continue working after a new Render instance starts.
# ---------------------------------------------------------------------------
_CONTINUITY_META_KIND_V263 = 'runtime_continuity_v263'
_CONTINUITY_META_KEY_V263 = 'latest'
_CONTINUITY_MAX_ITEMS_V263 = 6000
_CONTINUITY_SKIP_V263 = object()
_CONTINUITY_NAMES_V263 = (
    '_short_callback_store',
    '_WINDOW_NAV_HISTORY',
    '_category_order_selection',
    '_category_other_sort_state',
    '_timer_input_sessions',
    '_careful_restore_sessions',
    '_dozvon_sessions',
    '_dozvon_target_index',
    '_JOURNAL_FILENAME_WAIT',
    '_REMINDER_UI_BINDINGS',
    '_REMINDER_COMPLETED_DELETE_SELECTION',
    '_V172_INPUT_WAIT',
    '_V172_SEARCH_CACHE',
    '_V174_INPUT_WAIT',
    '_V221_OWNER_MSG_PENDING',
    '_V221_LIVE_MARKUP',
    '_V224_INLINE_HELPER_STATE',
    '_V160_ANNOTATION_PENDING',
    '_V160_LAST_WINDOW_META',
    '_V160_CALLBACK_IDS',
    '_V161_DELETE_STATE',
    '_V161_WINDOW_TOKENS',
    '_V164_WINDOW_VIEW',
    '_V196_SESSIONS',
    '_V196_PANEL_MESSAGES',
    '_V196_LAST_BASE_BY_KEY',
    '_V196_LAST_META_BY_TOKEN',
    '_V196_ACTIVE_WORKING_BY_KEY',
    '_V212_LAST_BASE_BY_SCOPE_KEY',
    '_V212_CATALOG_BY_SCOPE',
    '_KEEPALIVE_INPUT_WAIT',
    '_secret_sequence_state',
    '_o9_secret_clicks',
    '_V153_RESTORE_PENDING',
    '_V153_CALLBACK_RECEIPTS',
    '_V153_CALLBACK_SIGNATURES',
    # R6: additional user-facing interaction state discovered by full runtime audit.
    '_V153_WAITING_EXPORTS',
    '_V178_MEGA_PRIORITY_WAITING',
    '_V240_PAR_WAITING',
    # R6 full interaction audit: serializable user-visible sessions that previously
    # vanished on deploy even when the canonical chat/settings data survived.
    '_owner_json_restore_prompts',
    '_timer_input_sessions',
    '_careful_restore_sessions',
    '_dozvon_sessions',
    '_category_order_selection',
    '_category_other_sort_state',
    '_INLINE_FALLBACK_TEXT',
    '_V153_READY_EXPORTS',
    '_V153_UI_CACHE',
    '_V156_PROCESS_UI',
    '_V160_FAST_EDIT_LAST',
    '_V146_FAILED_TASK_RUNTIME_ERRORS',
)
_CONTINUITY_SCALARS_V263 = ('restore_mode', '_short_callback_counter')

# R6 persistent user-state shadow. The normal SQLite root/chats remain canonical,
# but this compact duplicate protects settings/UI/task/tenant metadata from any
# missed point-save or cross-chat mutation. Financial cold ledgers are deliberately
# excluded so this layer can never roll back accounting records.
_USER_STATE_META_KIND_V265 = 'user_state_shadow_v265'
_USER_STATE_META_KEY_V265 = 'latest'
_USER_STATE_ROOT_EXCLUDE_V265 = {'overall_balance', 'records', 'bot_errors', '_state_meta'}
_USER_STATE_CHAT_EXCLUDE_V265 = set(globals().get('LOWRAM_COLD_KEYS') or set()) | {'balance', 'next_id'}

def _user_state_json_copy_v265(value):
    try:
        return _split_json.loads(_split_json.dumps(value, ensure_ascii=False, separators=(',', ':'), default=str))
    except Exception:
        return None

def user_state_shadow_capture_v265(reason='checkpoint'):
    try:
        root_src = _sqlite_pack_root(data) if callable(globals().get('_sqlite_pack_root')) else {k:v for k,v in (data or {}).items() if k != 'chats'}
        root = {}
        for key, value in (root_src or {}).items():
            if str(key) in _USER_STATE_ROOT_EXCLUDE_V265:
                continue
            copied = _user_state_json_copy_v265(value)
            if copied is not None:
                root[str(key)] = copied
        chats = {}
        for cid, store in ((data or {}).get('chats') or {}).items():
            if not isinstance(store, dict):
                continue
            meta = {}
            try:
                items = dict.items(store)
            except Exception:
                items = []
            for key, value in items:
                if str(key) in _USER_STATE_CHAT_EXCLUDE_V265:
                    continue
                copied = _user_state_json_copy_v265(value)
                if copied is not None:
                    meta[str(key)] = copied
            chats[str(cid)] = meta
        previous = SQLITE.get_meta(_USER_STATE_META_KIND_V265, _USER_STATE_META_KEY_V265, {}) or {}
        seq = int((previous or {}).get('seq') or 0) + 1
        payload = {
            'schema': 2, 'seq': seq, 'saved_at': _split_time.time(),
            'reason': str(reason or 'checkpoint')[:180], 'front_version': _SPLIT_FRONT_VERSION,
            'root': root, 'chats': chats,
            'counts': {'root_keys': len(root), 'chats': len(chats),
                       'chat_settings': sum(1 for v in chats.values() if isinstance(v, dict) and isinstance(v.get('settings'), dict))},
        }
        SQLITE.set_meta(_USER_STATE_META_KIND_V265, _USER_STATE_META_KEY_V265, payload)
        return payload
    except Exception as exc:
        try: log_error(f'USER_STATE shadow capture R6: {exc}')
        except Exception: pass
        return {}

def user_state_shadow_apply_v265(loaded):
    if not isinstance(loaded, dict):
        return loaded
    try:
        payload = SQLITE.get_meta(_USER_STATE_META_KIND_V265, _USER_STATE_META_KEY_V265, {}) or {}
    except Exception:
        payload = {}
    if not isinstance(payload, dict) or not payload:
        return loaded
    restored_root = 0; restored_chats = 0; restored_settings = 0
    root = payload.get('root') or {}
    if isinstance(root, dict):
        for key, value in root.items():
            if str(key) in _USER_STATE_ROOT_EXCLUDE_V265:
                continue
            loaded[str(key)] = _user_state_json_copy_v265(value)
            restored_root += 1
    chats = loaded.setdefault('chats', {})
    shadow_chats = payload.get('chats') or {}
    if isinstance(shadow_chats, dict):
        for cid, meta in shadow_chats.items():
            if not isinstance(meta, dict):
                continue
            current = chats.get(str(cid))
            if not isinstance(current, dict):
                current = {}
                chats[str(cid)] = current
            for key, value in meta.items():
                if str(key) in _USER_STATE_CHAT_EXCLUDE_V265:
                    continue
                current[str(key)] = _user_state_json_copy_v265(value)
            try:
                if LOWRAM_ENABLED and not isinstance(current, ColdChatStore):
                    current = _lowram_wrap_store(int(cid), current)
                    chats[str(cid)] = current
            except Exception:
                pass
            restored_chats += 1
            if isinstance(meta.get('settings'), dict):
                restored_settings += 1
    try:
        log_info(f"USER_STATE R6 restored shadow seq={payload.get('seq')} root={restored_root} chats={restored_chats} settings={restored_settings}")
    except Exception:
        pass
    return loaded

# Apply the shadow as part of canonical load, before tenant/bootstrap defaults can
# create a factory profile. This is intentionally after normal SQLite unpacking.
_V265_BASE_LOAD_DATA = load_data
def load_data():
    loaded = _V265_BASE_LOAD_DATA()
    return user_state_shadow_apply_v265(loaded)


def _continuity_encode_v263(value, depth=0):
    if depth > 12:
        return _CONTINUITY_SKIP_V263
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, bytes):
        # No user interaction state should require raw binary; storing it as hex
        # avoids invalid JSON if a small identifier ever appears here.
        return {'__v263_type__': 'bytes', 'value': value.hex()[:131072]}
    if isinstance(value, dict):
        try:
            items = list(value.items())[:_CONTINUITY_MAX_ITEMS_V263]
        except Exception:
            return _CONTINUITY_SKIP_V263
        out = []
        for key, item in items:
            ek = _continuity_encode_v263(key, depth + 1)
            ev = _continuity_encode_v263(item, depth + 1)
            if ek is _CONTINUITY_SKIP_V263 or ev is _CONTINUITY_SKIP_V263:
                continue
            out.append([ek, ev])
        return {'__v263_type__': 'dict', 'items': out}
    if isinstance(value, tuple):
        vals = []
        for item in list(value)[:_CONTINUITY_MAX_ITEMS_V263]:
            enc = _continuity_encode_v263(item, depth + 1)
            if enc is not _CONTINUITY_SKIP_V263:
                vals.append(enc)
        return {'__v263_type__': 'tuple', 'items': vals}
    if isinstance(value, (list, set, _split_collections.deque)):
        typ = 'set' if isinstance(value, set) else 'deque' if isinstance(value, _split_collections.deque) else 'list'
        vals = []
        try:
            source = list(value)[:_CONTINUITY_MAX_ITEMS_V263]
        except Exception:
            return _CONTINUITY_SKIP_V263
        for item in source:
            enc = _continuity_encode_v263(item, depth + 1)
            if enc is not _CONTINUITY_SKIP_V263:
                vals.append(enc)
        return {'__v263_type__': typ, 'items': vals}
    # datetime/date values are rare in UI sessions; preserve their text instead
    # of failing the whole continuity snapshot.
    iso = getattr(value, 'isoformat', None)
    if callable(iso):
        try:
            return {'__v263_type__': 'iso', 'value': str(iso())}
        except Exception:
            pass
    return _CONTINUITY_SKIP_V263


def _continuity_decode_v263(value, depth=0):
    if depth > 12:
        return None
    if not isinstance(value, dict) or '__v263_type__' not in value:
        if isinstance(value, list):
            return [_continuity_decode_v263(x, depth + 1) for x in value]
        return value
    typ = str(value.get('__v263_type__') or '')
    if typ == 'bytes':
        try:
            return bytes.fromhex(str(value.get('value') or ''))
        except Exception:
            return b''
    if typ == 'dict':
        out = {}
        for pair in value.get('items') or []:
            if not isinstance(pair, list) or len(pair) != 2:
                continue
            key = _continuity_decode_v263(pair[0], depth + 1)
            val = _continuity_decode_v263(pair[1], depth + 1)
            try:
                out[key] = val
            except Exception:
                pass
        return out
    vals = [_continuity_decode_v263(x, depth + 1) for x in (value.get('items') or [])]
    if typ == 'tuple':
        return tuple(vals)
    if typ == 'set':
        try:
            return set(vals)
        except Exception:
            return set()
    if typ == 'deque':
        return _split_collections.deque(vals)
    if typ == 'list':
        return vals
    if typ == 'iso':
        return str(value.get('value') or '')
    return value


def _continuity_apply_v263(name, restored):
    current = globals().get(name, _CONTINUITY_SKIP_V263)
    try:
        if isinstance(current, dict) and isinstance(restored, dict):
            current.clear(); current.update(restored); return True
        if isinstance(current, set) and isinstance(restored, (set, list, tuple)):
            current.clear(); current.update(restored); return True
        if isinstance(current, list) and isinstance(restored, (list, tuple)):
            current[:] = list(restored); return True
        if isinstance(current, _split_collections.deque) and isinstance(restored, (list, tuple, _split_collections.deque)):
            current.clear(); current.extend(restored); return True
        globals()[name] = restored
        return True
    except Exception:
        return False


def continuity_capture_v263(reason='checkpoint'):
    """Persist RAM-only user interaction continuity inside canonical SQLite."""
    payload = {
        'schema': 1,
        'saved_at': _split_time.time(),
        'reason': str(reason or 'checkpoint')[:180],
        'front_version': _SPLIT_FRONT_VERSION,
        'globals': {},
        'scalars': {},
    }
    for name in _CONTINUITY_NAMES_V263:
        if name not in globals():
            continue
        enc = _continuity_encode_v263(globals().get(name))
        if enc is not _CONTINUITY_SKIP_V263:
            payload['globals'][name] = enc
    for name in _CONTINUITY_SCALARS_V263:
        if name not in globals():
            continue
        enc = _continuity_encode_v263(globals().get(name))
        if enc is not _CONTINUITY_SKIP_V263:
            payload['scalars'][name] = enc
    # Existing Telegram message IDs/windows are logical root state; add a compact
    # count here for diagnostics while the actual records stay in the normal root.
    try:
        payload['ui_counts'] = {
            'active_message_chats': len((data.get('active_messages') or {})),
            'open_windows': len((data.get('open_window_registry') or {})),
            'chat_count': len((data.get('chats') or {})),
        }
    except Exception:
        payload['ui_counts'] = {}
    SQLITE.set_meta(_CONTINUITY_META_KIND_V263, _CONTINUITY_META_KEY_V263, payload)
    return payload


def continuity_restore_v263():
    """Restore interaction state before main() starts accepting Telegram updates."""
    try:
        payload = SQLITE.get_meta(_CONTINUITY_META_KIND_V263, _CONTINUITY_META_KEY_V263, {}) or {}
    except Exception:
        return {'ok': False, 'reason': 'meta_read_failed'}
    if not isinstance(payload, dict) or not payload:
        return {'ok': False, 'reason': 'no_snapshot'}
    restored_names = []
    for name, raw in (payload.get('globals') or {}).items():
        if name not in _CONTINUITY_NAMES_V263:
            continue
        if _continuity_apply_v263(name, _continuity_decode_v263(raw)):
            restored_names.append(name)
    for name, raw in (payload.get('scalars') or {}).items():
        if name not in _CONTINUITY_SCALARS_V263:
            continue
        if _continuity_apply_v263(name, _continuity_decode_v263(raw)):
            restored_names.append(name)
    # Remove expired short callbacks; valid old Telegram buttons remain clickable.
    try:
        now = _split_time.time()
        ttl = float(globals().get('SHORT_CALLBACK_TTL_SECONDS') or 21600)
        store = globals().get('_short_callback_store')
        if isinstance(store, dict):
            for token, row in list(store.items()):
                if now - float((row or {}).get('ts') or 0.0) > ttl:
                    store.pop(token, None)
    except Exception:
        pass
    try:
        log_info(f"CONTINUITY R4 restored names={len(restored_names)} saved_at={payload.get('saved_at')} ui={payload.get('ui_counts') or {}}")
    except Exception:
        pass
    return {'ok': True, 'restored': restored_names, 'saved_at': payload.get('saved_at')}


def continuity_checkpoint_v263(chat_id=None, reason='update', full=False, schedule=True):
    """Commit logical + RAM continuity locally, then asynchronously hand it to worker."""
    try:
        if full:
            _V263_BASE_SAVE_DATA(data, full=True)
        elif chat_id is not None:
            _V263_BASE_SAVE_DATA(data, chat_ids=[int(chat_id)])
        else:
            _V263_BASE_SAVE_DATA(data, root_only=True)
    except Exception as exc:
        try: log_error(f'CONTINUITY local save R4: {exc}')
        except Exception: pass
    try:
        user_state_shadow_capture_v265(reason)
        continuity_capture_v263(reason)
        _split_mark_state_changed_v264(f'continuity:{reason}')
    except Exception as exc:
        try: log_error(f'CONTINUITY snapshot R5: {exc}')
        except Exception: pass
    if schedule:
        try:
            split_schedule_worker_sync_v262(reason=f'continuity:{reason}', delay=0.35)
        except Exception:
            pass
    return True


# Any logical save, not only finance, now requests remote durability.  The worker
# coalesces these calls, so Telegram handlers do not wait for MEGA.
_V263_BASE_SAVE_DATA = save_data

def save_data(d, chat_ids=None, full=False, root_only=False):
    result = _V263_BASE_SAVE_DATA(d, chat_ids=chat_ids, full=full, root_only=root_only)
    try:
        user_state_shadow_capture_v265('logical_save')
    except Exception:
        pass
    try:
        if not bool(globals().get('_V241_RESTORE_ACTIVE', False)):
            _split_mark_state_changed_v264('logical_save')
            # Boot migrations can call save_data many times. They are local-only until
            # READY, then R6 emits one final canonical snapshot instead of 4-10 GETs.
            ready_fn = globals().get('runtime_is_ready')
            is_ready = bool(ready_fn()) if callable(ready_fn) else False
            if is_ready or _split_inside_telegram_update_v264():
                split_schedule_worker_sync_v262(reason='logical_save', delay=0.6)
            else:
                _SPLIT_STATE['sync_pending'] = True
                _SPLIT_STATE['sync_reason'] = 'boot_coalesced'
    except Exception:
        pass
    return result


# Persist RAM-only sessions after every successfully executed Telegram update.
_V263_BASE_EXECUTE_TELEGRAM_PAYLOAD = _execute_telegram_payload

def _execute_telegram_payload(payload: dict, update_id=None, update_chat_id=None, update_type: str='other'):
    _SPLIT_UPDATE_CONTEXT.active = True
    try:
        result = _V263_BASE_EXECUTE_TELEGRAM_PAYLOAD(payload, update_id, update_chat_id, update_type)
    finally:
        _SPLIT_UPDATE_CONTEXT.active = False
    try:
        cid = update_chat_id
        if cid is None and isinstance(payload, dict):
            cid = _extract_update_chat_id(payload)
        continuity_checkpoint_v263(cid, reason=f'tg:{str(update_type or "other")}', full=False, schedule=True)
    except Exception as exc:
        try: log_error(f'CONTINUITY post-update R5: {exc}')
        except Exception: pass
    return result


def _split_push_snapshot_now_v263(reason='shutdown'):
    """Directly hand the final SQLite image to worker so shutdown cannot race a fetch job."""
    base, secret = _split_peer_base(), _split_secret()
    if not base or not secret:
        return False
    workdir = _split_tempfile.mkdtemp(prefix='v263_front_push_')
    raw = _split_os.path.join(workdir, 'bot_state.sqlite3')
    gz = raw + '.gz'
    try:
        SQLITE.backup_to(raw)
        with open(raw, 'rb') as src, _split_gzip.open(gz, 'wb', compresslevel=9) as dst:
            _split_shutil.copyfileobj(src, dst, length=1024 * 1024)
        # Seed shared durable cache before contacting worker; this survives worker deploys.
        try:
            _split_cache_snapshot_to_redis_v266(reason=str(reason or 'shutdown'), existing_gz=gz)
        except Exception:
            pass
        with open(gz, 'rb') as fh:
            body = fh.read()
        r = requests.post(
            base + '/internal/snapshot/upload', data=body,
            headers={**_split_headers('vys-262-front-final-push'), 'Content-Type': 'application/gzip', 'X-Snapshot-Reason': str(reason or '')[:120]},
            timeout=20,
        )
        if 200 <= r.status_code < 300:
            return True
        try: _SPLIT_STATE['sync_last_error'] = f'final push HTTP {r.status_code}: {r.text[:160]}'
        except Exception: pass
    except Exception as exc:
        try: _SPLIT_STATE['sync_last_error'] = 'final push: ' + str(exc)[:180]
        except Exception: pass
    finally:
        _split_shutil.rmtree(workdir, ignore_errors=True)
    return False


# Snapshot download always captures the latest RAM continuity first.
_V263_BASE_SPLIT_FRONT_STATE_DOWNLOAD = split_front_state_download_v262

def split_front_state_download_v263():
    # R5: a worker fetch must be read-only. R4 rewrote continuity.saved_at on every
    # GET, making two identical snapshots look different and causing needless follow-ups.
    if not _split_authorized_request():
        return ({'ok': False}, 404)
    return _V263_BASE_SPLIT_FRONT_STATE_DOWNLOAD()

# Replace Flask endpoint function while keeping the already registered URL rule.
try:
    app.view_functions['split_front_state_download_v262'] = split_front_state_download_v263
except Exception:
    pass


# Final graceful shutdown: original code drains queues and saves full SQLite; then
# push that exact DB to worker cache immediately, before the process exits.
_V263_BASE_RUNTIME_GRACEFUL_SHUTDOWN = runtime_graceful_shutdown

def runtime_graceful_shutdown(signal_name: str='SIGTERM'):
    result = _V263_BASE_RUNTIME_GRACEFUL_SHUTDOWN(signal_name)
    try:
        continuity_checkpoint_v263(None, reason=f'shutdown:{signal_name}', full=True, schedule=False)
        _split_push_snapshot_now_v263(f'shutdown:{signal_name}')
    except Exception as exc:
        try: log_error(f'CONTINUITY shutdown R4: {exc}')
        except Exception: pass
    return result


# R6 loader-order safety: 99_web_runtime loads data before this final module.
# The base load_data now restores the shadow early, and this second idempotent overlay
# protects already-loaded data if a future module order changes again.
try:
    data = user_state_shadow_apply_v265(data)
    try:
        _fac = (data or {}).get('finance_active_chats') or {}
        finance_active_chats.clear()
        for _cid, _enabled in _fac.items():
            if _enabled:
                try: finance_active_chats.add(int(_cid))
                except Exception: pass
    except Exception:
        pass
    try:
        _bf = (data or {}).get('backup_flags') or {}
        backup_flags['drive'] = bool(_bf.get('drive', backup_flags.get('drive', True)))
        backup_flags['channel'] = bool(_bf.get('channel', backup_flags.get('channel', True)))
    except Exception:
        pass
except Exception as _r6_live_apply_exc:
    try: log_error(f'R6 live user-state apply: {_r6_live_apply_exc}')
    except Exception: pass

# The DB was restored by start_front.py before bot.py was loaded, so RAM continuity
# can safely be rehydrated here, before main() marks the bot READY.
_CONTINUITY_BOOT_REPORT_V263 = continuity_restore_v263()


# R5 deploy-continuity rule: Telegram already keeps the old messages on its side.
# Re-sending/re-editing every restored chat on boot is both unnecessary and unsafe:
# stale historic chat ids can return 400 "chat not found".  Preserve the restored
# message ids/state and resume lazily when that chat next interacts with the bot.
def _split_schedule_startup_main_windows_v264(delay: float=3.0):
    try:
        log_info('CONTINUITY R5: startup UI replay skipped; restored Telegram messages are kept in place')
    except Exception:
        pass
    return True

schedule_startup_main_windows = _split_schedule_startup_main_windows_v264

# R6: all callback families emitted by the current bot must have a declared marker.
# Broad family declarations are intentional: dynamic task/space/reminder IDs vary,
# while the marker family is stable. This removes recurring NOT_DECLARED failures.
_R6_MARKER_FAMILIES = {
    'cat_page:*':'Ф3201', 'sp:*':'Ф3202', 'v149:*':'Ф3203', 'v152:*':'Ф3204',
    'v153:file:*':'Ф3205', 'v153:restore:*':'Ф3205', 'v156:*':'Ф3206', 'v157:*':'Ф3207',
    'v160:*':'Ф3208', 'v164:*':'Ф3209', 'v167:*':'Ф3210', 'v169:*':'Ф3211',
    'v171:*':'Ф3212', 'v172:*':'Ф3213', 'v174:*':'Ф3214', 'v176:*':'Ф3215',
    'v196:*':'Ф3216', 'v213:*':'Ф3217', 'v217:*':'Ф3218', 'v218:*':'Ф3219',
    'v219:*':'Ф3220', 'v221:*':'Ф3221', 'v223:*':'Ф3222', 'v229:*':'Ф3223',
    'v232:*':'Ф3224', 'v233:*':'Ф3225', 'v242:system_snapshot:*':'Ф3226', 'v261:*':'Ф3227',
    'expense_quick_buttons_toggle':'Ф3228', 'reminder_ui_mode_toggle':'Ф3229',
    'journal_toggle_open':'Ф3230', 'journal_name_edit:*':'Ф3231', 'journal_name_reset:*':'Ф3231',
    'keepalive_self_toggle':'Ф3232', 'keepalive_self_now':'Ф3232', 'keepalive_self_interval':'Ф3232',
    'keepalive_auto_toggle':'Ф3233', 'keepalive_auto_interval':'Ф3233',
    'keepalive_peer':'Ф3234', 'keepalive_peer_toggle':'Ф3234', 'keepalive_peer_now':'Ф3234',
    'keepalive_peer_clear':'Ф3234', 'keepalive_peer_interval':'Ф3234', 'keepalive_peer_url':'Ф3234',
    'keepalive_peer_url_cancel':'Ф3234',
    'keepalive_peer_set:*':'Ф3234', 'keepalive_self_set:*':'Ф3232', 'keepalive_auto_set:*':'Ф3233',
    # R6 second-pass audit: callbacks created through helper functions / variables.
    'v163_exp_end_today:*':'Ф116', 'v220:*':'Ф3235', 'exp_excel_dollar_toggle:*':'Ф179',
    'exp_send:*':'Ф3236',
    'fvcat_show:*':'Ф3237', 'fvcat_wthu:*':'Ф3237', 'fvcat_today:*':'Ф3237',
    'fvcat_desc:*':'Ф3237', 'fvcat_add:*':'Ф3237', 'fvcat_edit_menu:*':'Ф3237',
    'fvcat_edit_pick:*':'Ф3237', 'fvcat_del_menu:*':'Ф3237', 'fvcat_del_toggle:*':'Ф3237',
    'fvcat_del_selected:*':'Ф3237',
}
try:
    for _r6_key, _r6_marker in _R6_MARKER_FAMILIES.items():
        WINDOW_MARKER_CONSTANTS.setdefault(_r6_key, _r6_marker)
except Exception:
    pass

# Render liveness must stay HTTP 200 during boot; /readyz remains the strict readiness gate.
def _r6_root_liveness():
    ready = bool(globals().get('runtime_is_ready', lambda: False)())
    return ({'ok': True, 'role': 'front', 'ready': ready, 'phase': (globals().get('_RUNTIME_STATE') or {}).get('phase')}, 200)
try:
    app.view_functions['index'] = _r6_root_liveness
except Exception:
    pass

# Suppress boot-time snapshot storms and publish exactly one fully migrated state at READY.
_V265_BASE_RUNTIME_MARK_READY = runtime_mark_ready
def runtime_mark_ready(detail: str=''):
    result = _V265_BASE_RUNTIME_MARK_READY(detail)
    try:
        user_state_shadow_capture_v265('boot_ready')
        continuity_capture_v263('boot_ready')
        _split_mark_state_changed_v264('boot_ready')
        split_schedule_worker_sync_v262(reason='boot_ready', delay=0.8)
    except Exception as exc:
        try: log_error(f'R6 boot-ready sync: {exc}')
        except Exception: pass
    return result

try:
    _r6_missing = [k for k in ('v229:tasks:single_window','v149:google:sheet','v149:google:test','v149:google:history') if not window_marker_is_declared(k)]
    if _r6_missing:
        log_error('R6 marker registry incomplete: ' + ','.join(_r6_missing))
except Exception:
    pass

# ---------------------------------------------------------------------------
# R7 system polish: fast finance post-commit, definitive chat removal,
# beginner-friendly Google setup, and heavy CSV/XLSX/Drive generation on worker.
R7_SYSTEM_POLISH = 'vys262-r7-system-polish'

# --- Finance: one derived-state pass and one visual repaint per logical change. ---
def _r7_rebuild_month_short_ids_after_normalize(chat_id: int, store: dict) -> None:
    daily = store.get('daily_records', {}) or {}
    month_counters = {}
    usd_month_counters = {}
    for dk in sorted(daily.keys()):
        month_key = str(dk)[:7]
        month_counters.setdefault(month_key, 1)
        usd_month_counters.setdefault(month_key, 1)
        recs = sorted(daily.get(dk, []) or [], key=record_sort_key)
        daily[dk] = recs
        for rec in recs:
            if not isinstance(rec, dict):
                continue
            try:
                if callable(globals().get('ensure_finance_record_uid')):
                    ensure_finance_record_uid(int(chat_id), rec)
            except Exception:
                pass
            has_usd = bool(float(rec.get('usd_amount', 0) or 0))
            usd_only = bool(rec.get('usd_only', False))
            if not usd_only:
                rec['short_id'] = f"R{month_counters[month_key]}"
                month_counters[month_key] += 1
            elif has_usd:
                rec['short_id'] = f"U{usd_month_counters[month_key]}"
            if has_usd:
                rec['usd_short_id'] = f"U{usd_month_counters[month_key]}"
                usd_month_counters[month_key] += 1
    store['records'] = [r for dk in sorted(daily.keys()) for r in daily.get(dk, []) if isinstance(r, dict)]


def _r7_finance_changed_now(chat_id: int, day_key: str | None=None, reason: str='change'):
    """R7: local finance commit stays synchronous; all derived work is one debounced pass."""
    chat_id = int(chat_id)
    day_key = str(day_key or get_chat_store(chat_id).get('current_view_day') or today_key())[:10]
    try:
        finance_cache_invalidate(chat_id, f'finance_changed:{reason}:r7')
    except Exception:
        pass
    with locked_chat(chat_id):
        store = get_chat_store(chat_id)
        store['current_view_day'] = day_key
        # One normalization only.  Older path normalized inside recalc and again in
        # rebuild_month_short_ids, which was noticeable on chats with long histories.
        normalize_chat_records(chat_id)
        store = get_chat_store(chat_id)
        store['balance'] = sum(float(r.get('amount', 0) or 0) for r in store.get('records', []) or [] if isinstance(r, dict))
        _r7_rebuild_month_short_ids_after_normalize(chat_id, store)
        try:
            _snapshot_active_currency_ledger(store, _ensure_currency_ledgers(store))
        except Exception:
            pass
        if callable(globals().get('persist_finance_chat_local_fast')):
            persist_finance_chat_local_fast(chat_id)
    # Nothing below blocks the Telegram handler or holds chat_lock.
    try:
        schedule_quick_backup(chat_id, MEGA_DELTA_PRIORITY_DELAY_SECONDS if mega_backup_priority_enabled() else MEGA_DELTA_DELAY_SECONDS)
    except Exception:
        pass
    try:
        schedule_financial_window_refresh(chat_id, day_key, reason=f'r7:{reason}', delay=0.015)
    except Exception:
        pass
    try:
        schedule_finance_postcommit_background_v243(chat_id, reason=f'r7:{reason}', delay=0.30)
    except Exception:
        pass

# finance_changed() resolves this name at execution time.
globals()['_finance_changed_now'] = _r7_finance_changed_now


def _r7_linked_edit_postcommit(origin_chat_id: int, origin_msg_id: int, touched_days: dict, repaint_copies: bool):
    """Linked edit already normalized, renumbered and committed each touched chat.

    Do not immediately run finance_changed() and repeat the same DB work.  Only repaint
    each affected UI once and schedule the common background aggregate/durability pass.
    """
    for cid, day_key in list((touched_days or {}).items()):
        try:
            schedule_financial_window_refresh(int(cid), str(day_key or ''), reason='linked_edit_r7', delay=0.015)
        except Exception:
            pass
        try:
            schedule_finance_postcommit_background_v243(int(cid), reason='linked_edit_r7', delay=0.30)
        except Exception:
            pass
    if repaint_copies and origin_chat_id and origin_msg_id:
        try:
            _v262_background_repaint_copies(int(origin_chat_id), int(origin_msg_id))
        except Exception:
            pass

globals()['_v262_postcommit_linked_edit'] = _r7_linked_edit_postcommit


# R7 finance bulk-delete postcommit: callers already committed the normalized chat.
def _r7_v262_finance_postcommit_job(chat_id: int, day_key: str, reason: str):
    cid=int(chat_id); dk=str(day_key or '')
    try: finance_cache_invalidate(cid, f'r7:{reason}')
    except Exception: pass
    try: schedule_financial_window_refresh(cid, dk, reason=f'r7:{reason}', delay=0.015)
    except Exception: pass
    try: schedule_finance_postcommit_background_v243(cid, reason=f'r7:{reason}', delay=0.25)
    except Exception: pass
    try: schedule_quick_backup(cid, MEGA_DELTA_PRIORITY_DELAY_SECONDS if mega_backup_priority_enabled() else MEGA_DELTA_DELAY_SECONDS)
    except Exception: pass

globals()['_v262_finance_postcommit_job']=_r7_v262_finance_postcommit_job

# --- Chat audit: distinguish temporary unreachable from confirmed bot removal. ---
_R7_BASE_REFRESH_CHAT_PROBE = globals().get('_v197_refresh_chat_probe_facts')
_R7_BASE_PROBE_BOT_IN_CHAT = globals().get('probe_bot_in_chat')


def _r7_refresh_chat_probe_facts(chat_id: int, chat_obj=None) -> bool:
    changed = bool(_R7_BASE_REFRESH_CHAT_PROBE(int(chat_id), chat_obj)) if callable(_R7_BASE_REFRESH_CHAT_PROBE) else False
    try:
        info = get_chat_store(int(chat_id)).setdefault('info', {})
        membership = info.get('bot_membership') or {}
        status = str(membership.get('status') or '').strip().lower()
        reason = ''
        if status in {'left', 'kicked'}:
            reason = f'getChatMember status={status}: bot is not a member'
        if not reason:
            for warning in info.get('probe_warnings') or []:
                low = str(warning or '').casefold()
                if str(warning).startswith('bot_member:') and any(x in low for x in ('bot is not a member', 'bot was kicked', 'kicked from the', 'bot removed')):
                    reason = str(warning)[len('bot_member:'):][:260]
                    break
        previous = str(info.get('_r7_bot_removed_probe_reason') or '')
        if reason:
            if previous != reason:
                info['_r7_bot_removed_probe_reason'] = reason
                changed = True
        elif previous:
            info.pop('_r7_bot_removed_probe_reason', None)
            changed = True
    except Exception:
        pass
    return changed


def _r7_probe_bot_in_chat(chat_id: int, *, deep: bool=True, persist: bool=True, schedule_backup: bool=True, _migration_retry: bool=False) -> bool:
    cid = int(chat_id)
    result = bool(_R7_BASE_PROBE_BOT_IN_CHAT(cid, deep=deep, persist=persist, schedule_backup=schedule_backup, _migration_retry=_migration_retry)) if callable(_R7_BASE_PROBE_BOT_IN_CHAT) else False
    try:
        store = get_chat_store(cid)
        info = store.get('info') or {}
        reason = str(info.get('_r7_bot_removed_probe_reason') or '')
        lifecycle = _v150_lifecycle(cid) if callable(globals().get('_v150_lifecycle')) else (store.get('chat_lifecycle_v150') or {})
        last_error = str((lifecycle or {}).get('last_error') or '')
        failures = int((lifecycle or {}).get('consecutive_failures') or 0)
        # Direct getChatMember left/kicked is definitive.  For an already known
        # chat, Telegram may answer 400 `chat not found` immediately after the
        # bot was removed.  Treat the first explicit deep-probe result as removed;
        # timeout/429/connection errors remain temporary orange states.
        if not reason and deep and (not result) and 'chat not found' in last_error.casefold():
            reason = f'confirmed by Telegram deep probe: {last_error[:220]}'
        if reason:
            set_chat_status_v150(cid, 'bot_removed', reason, source='r7_deep_probe', persist=persist, schedule_backup=schedule_backup)
            try:
                suspend = globals().get('suspend_forward_target_v199')
                if callable(suspend):
                    suspend(cid, reason, persist=persist)
            except Exception:
                pass
            return False
    except Exception as exc:
        try: log_error(f'R7 chat probe classify {cid}: {exc}')
        except Exception: pass
    return result

# The base probe calls this helper by global name.
globals()['_v197_refresh_chat_probe_facts'] = _r7_refresh_chat_probe_facts
globals()['probe_bot_in_chat'] = _r7_probe_bot_in_chat

# --- Google UX: three-step setup, service email, open current sheet, auto-test. ---
_R7_GOOGLE_INFO_CACHE = {'ts': 0.0, 'data': {}}

def _r7_google_worker_info(fetch: bool=True):
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

_R7_BASE_GOOGLE_HANDLE = globals().get('tenant_google_handle_message')
_R7_BASE_V149_CALLBACK = globals().get('v149_extension_callback')


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
    return bool(_R7_BASE_GOOGLE_HANDLE(msg)) if callable(_R7_BASE_GOOGLE_HANDLE) else False


def _r7_v149_extension_callback(call, data_str: str) -> bool:
    raw = str(data_str or '')
    if raw.startswith('v149:google:'):
        action = raw.split(':', 2)[2]
        cid = int(call.message.chat.id)
        uid = int(getattr(getattr(call, 'from_user', None), 'id', 0) or 0)
        ok_manage, tid = _v149_google_can_manage(cid, uid, owner_only=True)
        if not ok_manage:
            try: bot.answer_callback_query(call.id, 'Только владелец пространства', show_alert=True)
            except Exception: pass
            return True
        if action in {'service_email', 'connect'}:
            info = _r7_google_worker_info()
            email = str(info.get('service_email') or '')
            text = ('📧 Email service account:\n\n<code>' + email + '</code>\n\nОткройте свою Google Таблицу → «Поделиться» → добавьте этот email → права «Редактор».') if email else '❌ Render #2 не отдал email service account. Проверьте GOOGLE_SERVICE_ACCOUNT_JSON.'
            bot.send_message(cid, text, parse_mode='HTML')
            try: bot.answer_callback_query(call.id)
            except Exception: pass
            return True
        if action == 'sheet':
            _v149_google_wait(tid, 'sheet', cid, uid)
            bot.send_message(cid, '2️⃣ Пришлите сюда ссылку на Google Таблицу.\n\nПример: https://docs.google.com/spreadsheets/d/...\n\nСразу после ссылки бот сам проверит доступ. JSON-ключ сюда присылать не нужно.')
            try: bot.answer_callback_query(call.id)
            except Exception: pass
            return True
    return bool(_R7_BASE_V149_CALLBACK(call, raw)) if callable(_R7_BASE_V149_CALLBACK) else False

# Final Google bindings.
globals()['tenant_google_status_text'] = _r7_google_status_text
globals()['tenant_google_keyboard'] = _r7_google_keyboard
globals()['tenant_google_test'] = _r7_google_test
globals()['tenant_google_handle_message'] = _r7_google_handle_message
globals()['v149_extension_callback'] = _r7_v149_extension_callback
try:
    WINDOW_MARKER_CONSTANTS.setdefault('v149:google:service_email', 'Ф233')
except Exception:
    pass

# --- Heavy file export bridge: front prepares business rows, worker serializes/uploads. ---
_R7_BASE_SEND_EXPORT = globals().get('send_export_for_chat_to')
_R7_EXPORT_SEEN = {}
_R7_EXPORT_SEEN_LOCK = _split_threading.RLock()


def _r7_json_rows(rows):
    out = []
    for row in rows or []:
        vals = []
        for value in list(row or []):
            if isinstance(value, (str, int, float, bool)) or value is None:
                vals.append(value)
            elif isinstance(value, dict):
                vals.append({str(k): v for k, v in value.items() if isinstance(v, (str, int, float, bool)) or v is None})
            else:
                vals.append(str(value))
        out.append(vals)
    return out


def _r7_export_annotations_payload(annotations):
    out = {}
    for key, val in (annotations or {}).items():
        try:
            r, c = key
            out[f'{int(r)},{int(c)}'] = str(val)
        except Exception:
            pass
    return out


def _r7_worker_file_submit(body: dict):
    base = _split_peer_base()
    if not base or not _split_secret():
        raise RuntimeError('Render #2 не настроен для файлового экспорта')
    r = requests.post(base + '/internal/export/file', json=body, headers=_split_headers('vys-262-front-export-r7'), timeout=25)
    payload = r.json() if r.content else {}
    if 200 <= r.status_code < 300 and payload.get('ok'):
        return str(payload.get('job_id') or body.get('job_id') or '')
    raise RuntimeError(str(payload.get('error') or r.text[:500] or f'HTTP {r.status_code}'))


def _r7_send_export_for_chat_to(recipient_chat_id: int, target_chat_id: int, mode: str, day_key: str, file_type: str='csv', excel_style_override=None, excel_options_override=None, delivery: str='chat'):
    recipient_chat_id = int(recipient_chat_id); target_chat_id = int(target_chat_id)
    file_type = str(file_type or 'csv').lower().lstrip('.')
    delivery = str(delivery or 'chat').strip().lower()
    custom_options = normalize_excel_export_options(excel_options_override) if isinstance(excel_options_override, dict) else None
    style = str(excel_style_override or (excel_export_options_style(custom_options) if custom_options else excel_table_style(target_chat_id)) or 'old').strip().lower()
    force_google = delivery == 'google' or style == 'google_notes'
    # Google Sheets already has a dedicated worker path with richer formatting.
    if force_google:
        return _R7_BASE_SEND_EXPORT(recipient_chat_id, target_chat_id, mode, day_key, file_type, excel_style_override, excel_options_override, delivery) if callable(_R7_BASE_SEND_EXPORT) else False
    try:
        raw_mode = str(mode or 'all')
        if raw_mode.startswith('xlsxstat_'):
            raw_mode = raw_mode[len('xlsxstat_'):]
        clean_mode = raw_mode.replace('csv_', '').replace('xlsx_', '')
        if clean_mode == 'all_real': clean_mode = 'all'
        rows, label = _period_export_rows(target_chat_id, clean_mode, day_key)
        ext = 'xlsx' if file_type in {'xlsx', 'xlsxstat'} else 'csv'
        if not rows and ext != 'xlsx':
            send_info(recipient_chat_id, f'Нет данных {label}.')
            return True
        annotations = {}
        category_layout = False
        sheet_name = 'Экспорт'
        description_column = True if not custom_options else bool(custom_options.get('description_column'))
        annotations_enabled = bool(not custom_options or custom_options.get('comments') or custom_options.get('notes'))
        if file_type == 'xlsxstat':
            store = get_chat_store(target_chat_id)
            start_key, end_key = _period_export_bounds(store, clean_mode, day_key)
            payload_rows = build_exact_category_stats_xlsx_rows(target_chat_id, start_key, 0, end_key, 0)
            category_layout = True
            sheet_name = 'Статьи'
            if custom_options and not description_column:
                payload_rows, annotations = _category_rows_without_description(payload_rows)
                category_layout = 'category_compact'
            if not annotations_enabled: annotations = {}
            safe_chat = mega_safe_name(get_chat_display_name(target_chat_id), 'chat')
            display_name = f'{safe_chat}_{clean_mode}_{day_key}_excel_статьи.xlsx'
        elif ext == 'xlsx':
            store = get_chat_store(target_chat_id)
            start_key, _end_key = _period_export_bounds(store, clean_mode, day_key)
            opening = _opening_balance_before_exact(store, start_key, 0)
            if description_column:
                payload_rows = [['Дата', 'Описание', 'Приход', 'Расход']]
                for date_v, amount_v, note_v in rows:
                    try: parsed = parse_csv_amount(amount_v)
                    except Exception: parsed = 0.0
                    payload_rows.append(_xlsx_record_row(date_v, parsed, note_v))
                payload_rows = insert_blank_rows_between_days(payload_rows, header_rows=1)
                payload_rows = _xlsx_simple_rows_with_balances(payload_rows, opening, target_chat_id)
            else:
                payload_rows, annotations = _compact_simple_excel_rows_and_annotations(rows, opening, target_chat_id)
                if not annotations_enabled: annotations = {}
            display_name = export_display_filename(target_chat_id, clean_mode, day_key, 'xlsx')
        else:
            payload_rows = [['date', 'amount', 'note']]
            prev_day = None
            for row in rows or []:
                vals = list(row or [])
                cur_day = str(vals[0] if vals else '')
                if prev_day is not None and cur_day != prev_day:
                    payload_rows.append(['', '', ''])
                payload_rows.append(vals[:3] + [''] * max(0, 3-len(vals)))
                prev_day = cur_day
            display_name = export_display_filename(target_chat_id, clean_mode, day_key, 'csv')
        tenant_id = str(tenant_id_for_chat(target_chat_id, create=False) or TENANT_PLATFORM_ID)
        cfg = tenant_google_config(tenant_id, create=False) or {}
        body = {
            'job_id': _split_secrets.token_hex(12), 'recipient_chat_id': recipient_chat_id,
            'target_chat_id': target_chat_id, 'tenant_id': tenant_id,
            'file_type': ext, 'source_file_type': file_type, 'style': style,
            'sheet_name': sheet_name, 'category_layout': category_layout,
            'rows': _r7_json_rows(payload_rows), 'annotations': _r7_export_annotations_payload(annotations),
            'filename': display_name, 'label': str(label), 'chat_name': get_chat_display_name(target_chat_id),
            'delivery': delivery,
            'drive_folder_id': str(cfg.get('drive_folder_id') or ''),
        }
        jid = _r7_worker_file_submit(body)
        what = 'Google Drive' if delivery == 'drive' else ('Excel' if ext == 'xlsx' else 'CSV')
        bot.send_message(recipient_chat_id, f'⚡ {what} готовится на Render #2. Можно продолжать пользоваться ботом — результат придёт отдельным сообщением.')
        try: file_job_mark_external_delivery('Render #2 export', jid)
        except Exception: pass
        return True
    except Exception as exc:
        try: log_error(f'R7 worker export {get_chat_display_name(target_chat_id)}: {exc}')
        except Exception: pass
        # Safety fallback preserves monolith behaviour if worker is temporarily unavailable.
        if callable(_R7_BASE_SEND_EXPORT):
            return _R7_BASE_SEND_EXPORT(recipient_chat_id, target_chat_id, mode, day_key, file_type, excel_style_override, excel_options_override, delivery)
        return False


def _r7_export_result_seen(job_id: str) -> bool:
    now = _split_time.time()
    with _R7_EXPORT_SEEN_LOCK:
        for key, ts in list(_R7_EXPORT_SEEN.items()):
            if now - float(ts or 0) > 86400:
                _R7_EXPORT_SEEN.pop(key, None)
        if job_id in _R7_EXPORT_SEEN:
            return True
        _R7_EXPORT_SEEN[job_id] = now
        return False


def _r7_deliver_worker_export(body: dict):
    jid = str(body.get('job_id') or '')
    cid = int(body.get('recipient_chat_id') or 0)
    if not jid or not cid: return
    if not body.get('ok'):
        try: bot.send_message(cid, '❌ Экспорт Render #2: ' + str(body.get('error') or 'неизвестная ошибка')[:800])
        except Exception: pass
        return
    if str(body.get('delivery') or '') == 'drive':
        try: bot.send_message(cid, f"☁️ Google Drive · {body.get('label') or ''}: {body.get('chat_name') or ''}\n\n{body.get('url') or ''}", disable_web_page_preview=True)
        except Exception: pass
        return
    base = _split_peer_base()
    try:
        r = requests.get(base + '/internal/export/file/' + jid, headers=_split_headers('vys-262-front-export-fetch-r7'), timeout=90)
        if r.status_code != 200:
            raise RuntimeError(f'worker file HTTP {r.status_code}: {r.text[:240]}')
        import io as _r7_io
        fobj = _r7_io.BytesIO(r.content)
        fobj.name = str(body.get('filename') or ('export.' + str(body.get('file_type') or 'bin')))
        caption = str(body.get('caption') or '') or f"📂 {('Excel' if str(body.get('file_type')) == 'xlsx' else 'CSV')} {body.get('label') or ''}: {body.get('chat_name') or ''}"
        _tg_call_retry(bot.send_document, cid, fobj, caption=caption, timeout=120, purpose='r7_worker_export_send_document')
    except Exception as exc:
        try: bot.send_message(cid, '❌ Не удалось получить готовый файл с Render #2: ' + str(exc)[:600])
        except Exception: pass


@app.route('/internal/split/export-result', methods=['POST'])
def split_front_export_result_r7():
    if not _split_authorized_request():
        return ({'ok': False}, 404)
    body = request.get_json(silent=True) or {}
    jid = str(body.get('job_id') or '')
    if not jid:
        return ({'ok': False, 'error': 'job_id required'}, 400)
    if _r7_export_result_seen(jid):
        return ({'ok': True, 'duplicate': True}, 200)
    try:
        pool = globals().get('GENERAL_TASK_POOL') or globals().get('BACKGROUND_TASK_POOL')
        submitted = False
        if pool is not None and hasattr(pool, 'submit'):
            submitted = bool(pool.submit('r7-export-delivery:' + jid, _r7_deliver_worker_export, dict(body)))
        if not submitted:
            _split_threading.Thread(target=_r7_deliver_worker_export, args=(dict(body),), daemon=True).start()
    except Exception:
        _split_threading.Thread(target=_r7_deliver_worker_export, args=(dict(body),), daemon=True).start()
    return ({'ok': True, 'accepted': True}, 202)

globals()['send_export_for_chat_to'] = _r7_send_export_for_chat_to

# R7 marker coverage for the task callback that was seen in production plus Google UX.
try:
    WINDOW_MARKER_CONSTANTS.setdefault('v229:tasks:single_window', 'Ф54')
    WINDOW_MARKER_CONSTANTS.setdefault('v149:google:service_email', 'Ф233')
except Exception:
    pass

try:
    bot_journal('r7_system_polish_loaded', int(OWNER_ID or 0), 'finance=single-derived-pass; chat_probe=removed-classifier; google=3-step; export=worker')
except Exception:
    pass

# --- R7 exact-range export and strict Front Google isolation. ---
_R7_BASE_EXACT_EXPORT = globals().get('send_exact_range_export')


def _r7_send_exact_range_export(recipient_chat_id: int, target_chat_id: int, start_key: str, start_rid: int, end_key: str, end_rid: int, file_type: str, excel_style_override=None, excel_options_override=None, delivery: str='chat'):
    recipient_chat_id=int(recipient_chat_id); target_chat_id=int(target_chat_id)
    file_type=str(file_type or 'csv').lower()
    if file_type not in {'csv','xlsx','xlsxstat'}: file_type='csv'
    custom_options=normalize_excel_export_options(excel_options_override) if isinstance(excel_options_override,dict) else None
    style=str(excel_style_override or (excel_export_options_style(custom_options) if custom_options else excel_table_style(target_chat_id)) or 'old').strip().lower()
    delivery=str(delivery or 'chat').strip().lower()
    force_google=delivery=='google' or style=='google_notes'
    description_column=True if not custom_options else bool(custom_options.get('description_column'))
    annotations_enabled=bool(not custom_options or custom_options.get('comments') or custom_options.get('notes'))
    try:
        rows=_exact_export_rows(target_chat_id,start_key,int(start_rid),end_key,int(end_rid))
        if not rows:
            send_and_auto_delete(recipient_chat_id,'Нет записей в выбранном точном диапазоне.',10)
            return True
        if force_google:
            xrows=build_exact_category_stats_xlsx_rows(target_chat_id,start_key,int(start_rid),end_key,int(end_rid))
            annotations={}; layout='category'
            if custom_options and not description_column:
                xrows,annotations=_category_rows_without_description(xrows); layout='category_compact'
            title=f'{get_chat_display_name(target_chat_id)} — статьи — точный период'
            token=_v262_split_google_sheets_create_category_report(title,xrows,layout=layout,annotations_override=annotations if annotations_enabled else {},include_annotations=annotations_enabled,target_chat_id=target_chat_id,recipient_chat_id=recipient_chat_id,notify_result=True)
            jid=str(token).split(':',1)[1] if str(token).startswith('worker-job:') else ''
            if jid:
                bot.send_message(recipient_chat_id,'⚡ Google Excel точного периода готовится на Render #2. Ссылка придёт отдельным сообщением.')
            return True
        ext='xlsx' if file_type in {'xlsx','xlsxstat'} else 'csv'
        annotations={}; layout=False; sheet_name='Точный период'
        if file_type=='xlsxstat':
            payload_rows=build_exact_category_stats_xlsx_rows(target_chat_id,start_key,int(start_rid),end_key,int(end_rid))
            layout=True; sheet_name='Excel стат'
            if custom_options and not description_column:
                payload_rows,annotations=_category_rows_without_description(payload_rows); layout='category_compact'
            if not annotations_enabled: annotations={}
        elif ext=='xlsx':
            opening=_opening_balance_before_exact(get_chat_store(target_chat_id),start_key,int(start_rid))
            if description_column:
                payload_rows=[['Дата','Описание','Приход','Расход']]
                for date_v,amount_v,note_v in rows:
                    try: parsed=parse_csv_amount(amount_v)
                    except Exception: parsed=0.0
                    payload_rows.append(_xlsx_record_row(date_v,parsed,note_v))
                payload_rows=insert_blank_rows_between_days(payload_rows,header_rows=1)
                payload_rows=_xlsx_simple_rows_with_balances(payload_rows,opening,target_chat_id)
            else:
                payload_rows,annotations=_compact_simple_excel_rows_and_annotations(rows,opening,target_chat_id)
                if not annotations_enabled: annotations={}
        else:
            payload_rows=[['date','amount','note']]; prev=None
            for row in rows or []:
                vals=list(row or []); cur=str(vals[0] if vals else '')
                if prev is not None and cur!=prev: payload_rows.append(['','',''])
                payload_rows.append(vals[:3]+['']*max(0,3-len(vals))); prev=cur
        chat_name=_safe_export_name_part(get_chat_name_for_filename(target_chat_id) or get_chat_display_name(target_chat_id),f'chat_{target_chat_id}')
        start_label=fmt_date_backup(start_key).replace(':','.')
        end_label=fmt_date_backup(end_key).replace(':','.')
        display_name=f"{chat_name}_({start_label}-{end_label})_{('excel_стат' if file_type=='xlsxstat' else 'точный')}.{ext}"
        store=get_chat_store(target_chat_id)
        caption=f"🎯 {(('Excel стат ' if file_type=='xlsxstat' else 'Excel ') + _export_style_caption(style) if ext=='xlsx' else 'CSV')} — точный период\n▶️ {exact_boundary_text(store,start_key,start_rid,True)}\n⏹ {exact_boundary_text(store,end_key,end_rid,False)}"
        tid=str(tenant_id_for_chat(target_chat_id,create=False) or TENANT_PLATFORM_ID); cfg=tenant_google_config(tid,create=False) or {}
        body={'job_id':_split_secrets.token_hex(12),'recipient_chat_id':recipient_chat_id,'target_chat_id':target_chat_id,'tenant_id':tid,
              'file_type':ext,'source_file_type':file_type,'style':style,'sheet_name':sheet_name,'category_layout':layout,
              'rows':_r7_json_rows(payload_rows),'annotations':_r7_export_annotations_payload(annotations),'filename':display_name,
              'label':'точный период','chat_name':get_chat_display_name(target_chat_id),'caption':caption,'delivery':delivery,
              'drive_folder_id':str(cfg.get('drive_folder_id') or '')}
        _r7_worker_file_submit(body)
        bot.send_message(recipient_chat_id,f"⚡ {('Google Drive' if delivery=='drive' else 'Excel' if ext=='xlsx' else 'CSV')} точного периода готовится на Render #2. Можно продолжать пользоваться ботом.")
        return True
    except Exception as exc:
        try: log_error(f'R7 exact worker export {target_chat_id}: {exc}')
        except Exception: pass
        # If worker is down, keep the old local export only as an emergency compatibility fallback.
        if callable(_R7_BASE_EXACT_EXPORT):
            return _R7_BASE_EXACT_EXPORT(recipient_chat_id,target_chat_id,start_key,start_rid,end_key,end_rid,file_type,excel_style_override,excel_options_override,delivery)
        return False


globals()['send_exact_range_export']=_r7_send_exact_range_export

# Active front hooks must never perform Google OAuth/Drive/Sheets network work.
def _r7_front_google_forbidden(*args, **kwargs):
    raise RuntimeError('Google network work is isolated on Render #2. Use /google or the worker export path.')

def _r7_front_create_sheet_disabled(tenant_id: str, title: str='Финансы бота'):
    raise RuntimeError('Создайте Google Таблицу в своём аккаунте, расшарьте её service-account как Редактору и подключите через /google. Создание таблиц сервисным аккаунтом отключено, чтобы владельцем файла оставались вы.')

globals()['_google_access_token']=_r7_front_google_forbidden
globals()['tenant_google_upload_export']=_r7_front_google_forbidden
globals()['tenant_google_create_spreadsheet']=_r7_front_create_sheet_disabled

# v262

# --- R9 release note: Google visual formatting restored to original vys-262 on Worker. ---
R9_GOOGLE_STYLE = 'vys262-r9-google-style'
try:
    bot_journal('r9_release_loaded', int(OWNER_ID or 0), 'google=original-v262-colors; startup-summary=concise; r8-chat-removal=kept')
except Exception:
    pass

# v262
