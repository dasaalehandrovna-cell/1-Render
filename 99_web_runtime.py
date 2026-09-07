# v262
def _v205_http_audit_operation() -> str:
    try:
        path = str(request.path or '/')
        if path.startswith('/tg/'):
            path = '/tg/<webhook>'
        elif path.startswith('/expense-ping/'):
            path = '/expense-ping/<token>'
        return f'http-server:{request.method}:{path[:80]}'
    except Exception:
        return 'http-server'

@app.after_request
def _v205_traffic_after_request(response):
    try:
        inbound = int(request.content_length or 0)
        body_len = response.calculate_content_length()
        if body_len is None:
            body_len = len(response.get_data() or b'')
        hdr = sum((len(str(k)) + len(str(v)) + 4 for k, v in response.headers.items()))
        traffic_audit_record('web_http', _v205_http_audit_operation(), int(body_len or 0) + hdr, inbound, int(getattr(response, 'status_code', 200) or 200) >= 500)
    except Exception:
        pass
    return response

@app.route('/', methods=['GET'])
def index():
    return ('OK', 200) if runtime_is_ready() else ('BOOTING', 503)

@app.route('/healthz', methods=['GET'])
def healthz():
    return ({'ok': True, 'version': VERSION, 'phase': _RUNTIME_STATE.get('phase'), 'ready': runtime_is_ready(), 'shutting_down': runtime_is_shutting_down()}, 200)

@app.route('/readyz', methods=['GET'])
def readyz():
    code = 200 if runtime_is_ready() else 503
    return ({'ok': runtime_is_ready(), 'version': VERSION, 'phase': _RUNTIME_STATE.get('phase'), 'task_recovery_remaining': _RUNTIME_STATE.get('task_recovery_remaining', 0)}, code)

@app.route('/keepalive', methods=['GET', 'HEAD'])
def keepalive_endpoint():
    ping_at = _journal_ts()
    user_agent = str(request.headers.get('User-Agent', '') or '')[:240]
    KEEP_ALIVE_STATE['external_ping_at'] = ping_at
    KEEP_ALIVE_STATE['last_keepalive_user_agent'] = user_agent
    if user_agent == _keepalive_wire_user_agent_v250('keepalive'):
        KEEP_ALIVE_STATE['self_ping_at'] = ping_at
    else:
        KEEP_ALIVE_STATE['external_monitor_at'] = ping_at
        is_peer = 'peer-keepalive' in user_agent.casefold() or 'peer-watchdog' in user_agent.casefold()
        if is_peer:
            KEEP_ALIVE_STATE['peer_received_at'] = ping_at
        try:
            keepalive_note_inbound_activity('peer_watchdog' if is_peer else 'external_keepalive')
        except Exception:
            pass
    if request.method == 'HEAD':
        return ('', 200)
    return ({'ok': True, 'version': VERSION, 'time': ping_at, 'profile': active_bot_behavior_profile(), 'keep_alive': bool(globals().get('keepalive_self_enabled', lambda: KEEP_ALIVE_ENABLED)()), 'self_interval_seconds': int(globals().get('keepalive_self_interval_seconds', lambda: KEEP_ALIVE_INTERVAL_SECONDS)()), 'auto_keep_alive': bool(globals().get('keepalive_auto_enabled', lambda: True)()), 'auto_idle_seconds': int(globals().get('keepalive_auto_idle_seconds', lambda: 720)()), 'peer_keep_alive': bool(globals().get('keepalive_peer_enabled', lambda: False)()), 'ready': runtime_is_ready(), 'phase': _RUNTIME_STATE.get('phase'), 'uptime_seconds': round(max(0.0, time.monotonic() - _RUNTIME_STARTED_MONO), 1), 'external_monitor_seen': bool(KEEP_ALIVE_STATE.get('external_monitor_at'))}, 200)

@app.route('/expense-ping/<token>', methods=['GET', 'POST'])
def expense_ping_endpoint(token: str):
    """Защищённый endpoint для iPhone Shortcuts/Back Tap.

    Событие сначала сохраняется в постоянную очередь бота, поэтому временная ошибка
    Telegram не стирает отметку расхода: доставка будет повторена.
    """
    try:
        keepalive_note_inbound_activity('expense_ping')
    except Exception:
        pass
    if not runtime_is_ready() or runtime_is_shutting_down():
        return ({'ok': False, 'status': 'booting'}, 503)
    cfg = expense_shortcut_config(False) or {}
    expected = str(cfg.get('token') or '')
    if not expected or not secrets.compare_digest(str(token or ''), expected):
        return ({'ok': False}, 404)
    if 'safety_profile_new_enabled' in globals() and safety_profile_new_enabled():
        try:
            rate_key = f"{request.remote_addr or 'unknown'}:{str(token)[-8:]}"
            now_ts = time.time()
            bucket = _IPHONE_ENDPOINT_RUNTIME[rate_key]
            while bucket and now_ts - float(bucket[0]) > 60.0:
                bucket.popleft()
            if len(bucket) >= 10:
                try:
                    bot_journal('expense_ping_rate_limited', None, f'key={rate_key}', 'WARN')
                except Exception:
                    pass
                return ({'ok': False, 'error': 'rate_limited'}, 429)
            bucket.append(now_ts)
        except Exception:
            pass
    try:
        event_id, duplicate = enqueue_expense_ping_event('iphone_back_tap', force=False)
        target_chat_id = int(expense_shortcut_config(True).get('target_chat_id') or 0)
        return ({'ok': True, 'queued': True, 'duplicate_suppressed': bool(duplicate), 'event': event_id, 'target_chat_id': target_chat_id, 'time': now_local().isoformat(timespec='seconds')}, 202 if not duplicate else 200)
    except Exception as exc:
        log_error(f'expense ping endpoint: {exc}')
        return ({'ok': False, 'error': 'queue_failed'}, 503)

def _refresh_callback_window_timers(chat_id: int, message_id: int, raw_callback: str):
    """v135: любой клик в связанном окне начинает ВСЕ его авто-таймеры заново."""
    chat_id = int(chat_id)
    message_id = int(message_id)
    raw = str(raw_callback or '')
    resolved = resolve_short_callback(raw) or raw
    try:
        _touch_v98_auto_close_for_callback(chat_id, message_id, resolved)
    except Exception:
        pass
    store = get_chat_store(chat_id)
    try:
        for timer_chat_id, store_key in list(_aux_window_timers.keys()):
            if int(timer_chat_id) == chat_id and int(store.get(str(store_key)) or 0) == message_id:
                schedule_stored_window_delete(chat_id, str(store_key), None)
    except Exception:
        pass
    try:
        wait = store.get('edit_wait') or {}
        if int(wait.get('prompt_msg_id') or 0) == message_id:
            schedule_cancel_edit(chat_id, message_id, delay=None)
    except Exception:
        pass
    try:
        wait = store.get('finwin_edit_wait') or {}
        if int(wait.get('prompt_msg_id') or 0) == message_id:
            schedule_cancel_finwin_edit(chat_id, message_id, delay=None)
    except Exception:
        pass
    for field in ('category_add_wait', 'category_edit_wait'):
        try:
            wait = store.get(field) or {}
            if int(wait.get('prompt_msg_id') or 0) == message_id:
                schedule_cancel_category_wait(chat_id, field, message_id, delay=None)
        except Exception:
            pass
    try:
        wait = store.get('forward_copy_edit_wait') or {}
        if int(wait.get('prompt_msg_id') or 0) == message_id:
            schedule_forward_copy_edit_wait_cancel(chat_id, message_id, delay=None)
    except Exception:
        pass
    try:
        active = store.get('secret_active_window') or {}
        if int(active.get('message_id') or 0) == message_id:
            schedule_secret_calendar_close(chat_id, message_id)
    except Exception:
        pass
    try:
        if (chat_id, message_id) in _secret_media_timer_generation:
            schedule_secret_media_close(chat_id, message_id)
    except Exception:
        pass
    try:
        secret_wait = store.get('secret_wait') or {}
        if int(secret_wait.get('prompt_msg_id') or 0) == message_id:
            schedule_o9_secret_wait_timeout(chat_id, message_id, O9_SECRET_WAIT_SECONDS)
    except Exception:
        pass

def _protect_pending_ui_timers_on_receipt(payload: dict):
    """Продлевает связанные авто-close/auto-cancel/auto-return уже в момент receipt webhook."""
    try:
        if not isinstance(payload, dict):
            return
        msg = payload.get('message') or payload.get('edited_message')
        if isinstance(msg, dict):
            chat = msg.get('chat') or {}
            chat_id = int(chat.get('id'))
            store = get_chat_store(chat_id)
            wait = store.get('edit_wait') or {}
            if isinstance(wait, dict) and wait.get('prompt_msg_id'):
                schedule_cancel_edit(chat_id, int(wait['prompt_msg_id']), delay=None)
            wait = store.get('finwin_edit_wait') or {}
            if isinstance(wait, dict) and wait.get('prompt_msg_id'):
                schedule_cancel_finwin_edit(chat_id, int(wait['prompt_msg_id']), delay=None)
            for field in ('category_add_wait', 'category_edit_wait'):
                wait = store.get(field) or {}
                if isinstance(wait, dict) and wait.get('prompt_msg_id'):
                    schedule_cancel_category_wait(chat_id, field, int(wait['prompt_msg_id']), delay=None)
            wait = store.get('forward_copy_edit_wait') or {}
            if isinstance(wait, dict) and wait.get('prompt_msg_id'):
                schedule_forward_copy_edit_wait_cancel(chat_id, int(wait['prompt_msg_id']), delay=None)
            try:
                secret_wait = store.get('secret_wait') or {}
                if isinstance(secret_wait, dict) and secret_wait.get('prompt_msg_id'):
                    schedule_o9_secret_wait_timeout(chat_id, int(secret_wait['prompt_msg_id']), O9_SECRET_WAIT_SECONDS)
            except Exception:
                pass
            return
        cq = payload.get('callback_query')
        if isinstance(cq, dict):
            cmsg = cq.get('message') or {}
            chat = cmsg.get('chat') or {}
            chat_id = int(chat.get('id'))
            message_id = int(cmsg.get('message_id') or 0)
            if message_id:
                _refresh_callback_window_timers(chat_id, message_id, str(cq.get('data') or ''))
    except Exception as e:
        try:
            log_error(f'receipt timer protection: {e}')
        except Exception:
            pass
import hashlib as _v163_webhook_hashlib
_v163_webhook_seed = os.getenv('WEBHOOK_SECRET', '').strip() or _v163_webhook_hashlib.sha256(('telegram-webhook-v163|' + str(BOT_TOKEN) + '|' + str(os.getenv('RENDER_SERVICE_ID', '') or WEBHOOK_URL)).encode('utf-8')).hexdigest()[:40]
WEBHOOK_SECRET_PATH = _v163_webhook_seed
WEBHOOK_ROUTE_PATH = f'/tg/{WEBHOOK_SECRET_PATH}'
WEBHOOK_HEADER_SECRET = _v163_webhook_hashlib.sha256(('header|' + WEBHOOK_SECRET_PATH + '|' + str(BOT_TOKEN)).encode('utf-8')).hexdigest()[:48]
WEBHOOK_HEADER_SECRET_ENABLED = False

_V260_WEBHOOK_INBOX_KIND = 'webhook_inbox_v260'
_V260_WEBHOOK_MAX_ATTEMPTS = 5

# R36: Telegram admission/replay bookkeeping has its own tiny SQLite file.
# The old implementation shared SQLITE.lock with the full finance/history database,
# so a long finance JSON commit could delay webhook admission and vice versa.
_V260_INBOX_DB = Path(os.getenv('WEBHOOK_INBOX_DB_FILE', str(DB_FILE) + '.webhook_inbox.sqlite3') or (str(DB_FILE) + '.webhook_inbox.sqlite3')).resolve()
_V260_INBOX_LOCK = threading.RLock()
_V260_INBOX_READY = False

def _v260_inbox_connect():
    global _V260_INBOX_READY
    _V260_INBOX_DB.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(_V260_INBOX_DB), timeout=1.5, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute('PRAGMA journal_mode=WAL')
        conn.execute('PRAGMA synchronous=FULL')
        conn.execute('PRAGMA busy_timeout=1500')
        conn.execute('CREATE TABLE IF NOT EXISTS inbox(update_id TEXT PRIMARY KEY, v TEXT NOT NULL, updated_ts REAL NOT NULL DEFAULT 0)')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_inbox_updated ON inbox(updated_ts)')
        conn.commit()
        _V260_INBOX_READY = True
        return conn
    except Exception:
        conn.close()
        raise

def _v260_inbox_write(row: dict) -> bool:
    if not isinstance(row, dict) or not row.get('update_id'):
        return False
    payload = json.dumps(row, ensure_ascii=False, separators=(',', ':'), default=str)
    with _V260_INBOX_LOCK:
        conn = _v260_inbox_connect()
        try:
            conn.execute('INSERT INTO inbox(update_id,v,updated_ts) VALUES(?,?,?) ON CONFLICT(update_id) DO UPDATE SET v=excluded.v,updated_ts=excluded.updated_ts', (str(row.get('update_id')), payload, float(row.get('updated_ts') or time.time())))
            conn.commit(); return True
        finally:
            conn.close()

def _v260_webhook_inbox_row(update_id) -> dict:
    try:
        with _V260_INBOX_LOCK:
            conn = _v260_inbox_connect()
            try:
                row = conn.execute('SELECT v FROM inbox WHERE update_id=?', (str(update_id),)).fetchone()
            finally:
                conn.close()
        if not row: return {}
        obj = json.loads(row[0])
        return obj if isinstance(obj, dict) else {}
    except Exception:
        return {}

def _v260_webhook_inbox_put(update_id, payload, chat_id=None, update_type='other') -> bool:
    """Durably register a Telegram update without touching the finance SQLite lock."""
    try:
        old = _v260_webhook_inbox_row(update_id) or {}
        state = str(old.get('state') or '')
        row = {
            'update_id': str(update_id), 'chat_id': chat_id, 'type': str(update_type or 'other'),
            'payload': payload,
            'state': state if state in {'queued','running','done','failed','external_pending','external_running','external_failed_review','needs_review'} else 'queued',
            'attempts': max(0, int(old.get('attempts') or 0)),
            'error': str(old.get('error') or '')[:500],
            'updated_at': now_local().isoformat(timespec='milliseconds'), 'updated_ts': time.time()
        }
        return _v260_inbox_write(row)
    except Exception as exc:
        log_error(f'WEBHOOK INBOX R36 put update={update_id}: {exc}')
        return False

def _v260_webhook_inbox_mark(update_id, state: str, error: str=''):
    try:
        row = _v260_webhook_inbox_row(update_id) or {'update_id': str(update_id), 'payload': {}, 'type': 'other'}
        new_state = str(state or '')
        attempts = max(0, int(row.get('attempts') or 0))
        if new_state in {'running', 'external_running'} and str(row.get('state') or '') not in {'running', 'external_running'}:
            attempts += 1
        row.update({'state': new_state, 'attempts': attempts, 'error': str(error or '')[:500], 'updated_at': now_local().isoformat(timespec='milliseconds'), 'updated_ts': time.time()})
        _v260_inbox_write(row)
        return row
    except Exception as exc:
        log_error(f'WEBHOOK INBOX R36 mark update={update_id}: {exc}')
        return {}

def _v260_webhook_inbox_state(update_id) -> str:
    return str((_v260_webhook_inbox_row(update_id) or {}).get('state') or '')

def _v260_inbox_scan_rows() -> list[dict]:
    out=[]
    with _V260_INBOX_LOCK:
        conn=_v260_inbox_connect()
        try: raw=conn.execute('SELECT update_id,v,updated_ts FROM inbox').fetchall()
        finally: conn.close()
    for r in raw:
        try:
            obj=json.loads(r[1]) if isinstance(r[1],str) else {}
            if isinstance(obj,dict): out.append(obj)
        except Exception: pass
    return out

def _v260_inbox_delete_keys(keys) -> None:
    vals=[(str(k),) for k in keys if str(k)]
    if not vals: return
    with _V260_INBOX_LOCK:
        conn=_v260_inbox_connect()
        try:
            conn.executemany('DELETE FROM inbox WHERE update_id=?', vals); conn.commit()
        finally: conn.close()

def _v260_inbox_migrate_legacy_once() -> int:
    """Best-effort one-time read of R35 rows without taking SQLITE.lock."""
    marker = _V260_INBOX_DB.with_suffix(_V260_INBOX_DB.suffix + '.migrated_r36')
    if marker.exists(): return 0
    moved=0
    try:
        conn=sqlite3.connect(str(DB_FILE),timeout=.5,check_same_thread=False)
        try:
            rows=conn.execute('SELECT k,v FROM meta WHERE kind=?', (_V260_WEBHOOK_INBOX_KIND,)).fetchall()
        finally: conn.close()
        for _k, raw in rows:
            try:
                obj=json.loads(raw) if isinstance(raw,str) else {}
                if isinstance(obj,dict) and obj.get('update_id') and _v260_inbox_write(obj): moved+=1
            except Exception: pass
    except Exception:
        pass
    try: marker.write_text(str(time.time()),encoding='utf-8')
    except Exception: pass
    return moved

def _v260_submit_webhook_inbox_row(row: dict) -> bool:
    """Replay on the SAME keyed lane as a live update so per-chat order is kept."""
    if not isinstance(row, dict):
        return False
    update_id = row.get('update_id')
    payload = row.get('payload') or {}
    chat_id = row.get('chat_id')
    update_type = str(row.get('type') or 'other')
    update_key = chat_id if chat_id is not None else update_id
    selector = globals().get('v163_webhook_select_lane')
    try:
        if callable(selector):
            selected_pool, selected_key = selector(payload, update_type, update_key)
        else:
            selected_pool = UI_TASK_POOL if update_type == 'callback_query' else WEBHOOK_TASK_POOL
            selected_key = f'ui:{update_key}' if update_type == 'callback_query' else update_key
        return bool(selected_pool.submit(selected_key, _v260_replay_webhook_inbox_row, row))
    except Exception as exc:
        log_error(f'WEBHOOK INBOX V260 submit update={update_id}: {exc}')
        return False


def _v260_schedule_webhook_inbox_retry(row_or_update_id, delay: float | None=None) -> bool:
    try:
        row = row_or_update_id if isinstance(row_or_update_id, dict) else _v260_webhook_inbox_row(row_or_update_id)
        if not isinstance(row, dict) or not row:
            return False
        update_id = row.get('update_id')
        attempts = max(0, int(row.get('attempts') or 0))
        if attempts >= _V260_WEBHOOK_MAX_ATTEMPTS:
            _v260_webhook_inbox_mark(update_id, 'needs_review', str(row.get('error') or 'local retry exhausted'))
            return False
        delays = (1.0, 3.0, 8.0, 20.0, 45.0)
        wait = float(delay if delay is not None else delays[min(attempts, len(delays)-1)])
        scheduler = globals().get('DELAYED_SCHEDULER')
        if scheduler is None:
            return False
        scheduler.schedule(f'webhook-inbox-v260:{update_id}', wait, lambda: _v260_submit_webhook_inbox_row(_v260_webhook_inbox_row(update_id)))
        return True
    except Exception as exc:
        log_error(f'WEBHOOK INBOX V260 retry schedule: {exc}')
        return False


def _v260_replay_webhook_inbox_row(row: dict):
    update_id = row.get('update_id'); payload = row.get('payload') or {}
    chat_id = row.get('chat_id'); update_type = str(row.get('type') or 'other')
    current = _v260_webhook_inbox_row(update_id) or row
    if str(current.get('state') or '') == 'done':
        return True
    if int(current.get('attempts') or 0) >= _V260_WEBHOOK_MAX_ATTEMPTS:
        _v260_webhook_inbox_mark(update_id, 'needs_review', str(current.get('error') or 'local retry exhausted'))
        return False
    try:
        _v260_webhook_inbox_mark(update_id, 'running')
        _execute_telegram_payload(payload, update_id, chat_id, update_type)
        _v260_webhook_inbox_mark(update_id, 'done')
        _r13_commit_fn = globals().get('split_event_committed_v268')
        if callable(_r13_commit_fn): _r13_commit_fn(update_id, chat_id, update_type, True, '')
        bot_journal('webhook_inbox_recovered_v260', chat_id, f'update_id={update_id}; type={update_type}')
        return True
    except Exception as exc:
        failed_row = _v260_webhook_inbox_mark(update_id, 'failed', str(exc))
        _r13_commit_fn = globals().get('split_event_committed_v268')
        if callable(_r13_commit_fn): _r13_commit_fn(update_id, chat_id, update_type, False, str(exc))
        log_error(f'WEBHOOK INBOX V260 recovery failed update={update_id}: {exc}')
        _v260_schedule_webhook_inbox_retry(failed_row or update_id)
        return False


def recover_webhook_inbox_v260(limit: int=100) -> int:
    rows=[]
    try:
        _v260_inbox_migrate_legacy_once()
        raw=_v260_inbox_scan_rows()
        stale_done=[]
        now_ts=time.time()
        for row in raw:
            if not isinstance(row,dict): continue
            key=str(row.get('update_id') or '')
            state = str(row.get('state') or '')
            if state == 'done' and now_ts-float(row.get('updated_ts') or now_ts) > 172800:
                stale_done.append(str(key)); continue
            # Cloud/external work has its own MEGA task registry and must never be
            # replayed by the local-only inbox after a restart.
            if state.startswith('external_') or state == 'done':
                continue
            if state not in {'queued','running','failed'}:
                continue
            if int(row.get('attempts') or 0) >= _V260_WEBHOOK_MAX_ATTEMPTS:
                _v260_webhook_inbox_mark(row.get('update_id'), 'needs_review', str(row.get('error') or 'local retry exhausted'))
                continue
            rows.append(row)
        if stale_done:
            _v260_inbox_delete_keys(stale_done)
    except Exception as exc:
        log_error(f'WEBHOOK INBOX V260 scan: {exc}'); return 0
    submitted=0
    for row in rows[:max(1,int(limit))]:
        if _v260_submit_webhook_inbox_row(row):
            submitted+=1
    return submitted

def _r19_update_journal_start(update_id, update_chat_id, update_type, wait, durable_cloud):
    try:
        bot_journal('update_process_start', update_chat_id, f'update_id={update_id} type={update_type} queue_wait={wait:.3f}s durable={durable_cloud}')
    except Exception:
        pass


def _r19_post_update_cleanup(update_id, update_chat_id, update_type, wait, started, success, durable_cloud):
    # Never hold the user-facing callback worker while flushing cold chat state or
    # writing diagnostic rows. These actions are important, but not interactive.
    try:
        bot_journal('update_process_done', update_chat_id, f'update_id={update_id} type={update_type} queue_wait={wait:.3f}s process={time.time() - started:.3f}s total={time.time() - (started - wait):.3f}s success={success} durable={durable_cloud}')
    except Exception:
        pass
    # R24: do not throw an active chat out of RAM after every button. Memory-pressure
    # eviction is handled centrally by the idle sweep / durable cleanup only.


def _r19_schedule_post_update_cleanup(update_id, update_chat_id, update_type, wait, started, success, durable_cloud):
    pool = globals().get('UI_CLEANUP_TASK_POOL') or globals().get('BACKGROUND_TASK_POOL')
    if pool is not None:
        try:
            if pool.submit(f'cleanup:{update_id}', _r19_post_update_cleanup, update_id, update_chat_id, update_type, wait, started, success, durable_cloud):
                return True
        except Exception:
            pass
    try:
        threading.Thread(target=_r19_post_update_cleanup, args=(update_id, update_chat_id, update_type, wait, started, success, durable_cloud), name=f'r19-cleanup-{update_id}', daemon=True).start()
        return True
    except Exception:
        return False



def _r22_callback_inbox_mark_background(update_id, state: str, error: str='') -> None:
    """SQLite inbox bookkeeping outside the callback worker."""
    try:
        _v260_webhook_inbox_mark(update_id, state, error)
    except Exception:
        pass


def _r22_callback_commit_background(update_id, chat_id, success: bool, error: str='') -> None:
    try:
        fn = globals().get('split_event_committed_v268')
        if callable(fn):
            fn(update_id, chat_id, 'callback_query', bool(success), str(error or ''))
    except Exception:
        pass


def _r22_callback_sidejobs(payload: dict, update_id, update_chat_id) -> None:
    """Remote witness/timer/journal work that must never precede FAST dispatch."""
    try:
        fn = globals().get('split_witness_event_v268')
        if callable(fn):
            if not fn(update_id, payload, update_chat_id, 'callback_query'):
                log_error(f'R22 CALLBACK REMOTE WITNESS FAILED update={update_id}')
    except Exception as exc:
        try: log_error(f'R22 CALLBACK REMOTE WITNESS ERROR update={update_id}: {exc}')
        except Exception: pass
    try:
        _protect_pending_ui_timers_on_receipt(payload)
    except Exception:
        pass


def _r25_callback_durable_admission(payload: dict, update_id, update_chat_id) -> None:
    """Persist/mirror a callback after FAST admission; never delays HTTP 200 or UI."""
    try:
        if not _v260_webhook_inbox_put(update_id, payload, update_chat_id, 'callback_query'):
            log_error(f'R26 CALLBACK LOCAL INBOX BACKGROUND FAILED update={update_id}')
    except Exception as exc:
        try: log_error(f'R26 CALLBACK LOCAL INBOX ERROR update={update_id}: {exc}')
        except Exception: pass
    try:
        _r22_callback_sidejobs(payload, update_id, update_chat_id)
    except Exception:
        pass

def _r22_accept_callback_fast(payload: dict, update_id, update_chat_id, update_key):
    """R22 callback admission.

    Ordering guarantee: claim + FAST enqueue happen before any SQLite/Redis/network
    durability work.  HTTP 200 is still withheld until the local SQLite inbox is
    durable, so deploy/crash safety is retained while the visible UI can already run.
    """
    claim_state, ticket = UPDATE_DISPATCHER.claim(update_id, update_chat_id, 'callback_query')
    if claim_state == 'new':
        update_enqueued_at = time.time()

        def _process_callback():
            started = time.time()
            wait = started - update_enqueued_at
            UPDATE_DISPATCHER.mark_started(update_id)
            try:
                _cq = payload.get('callback_query') or {}
                r25_trace_begin(update_id, update_chat_id, 'callback_query', str(_cq.get('data') or ''))
                r25_trace_stage('HANDLER_ENTER')
            except Exception:
                pass
            try:
                UI_CLEANUP_TASK_POOL.submit(f'r22-inbox-running:{update_id}', _r22_callback_inbox_mark_background, update_id, 'running', '')
                UI_CLEANUP_TASK_POOL.submit(f'r22-journal-start:{update_id}', _r19_update_journal_start, update_id, update_chat_id, 'callback_query', wait, False)
            except Exception:
                pass
            success = False
            error_text = ''
            try:
                try: r25_trace_stage('EXECUTE_TELEGRAM_PAYLOAD_START')
                except Exception: pass
                _execute_telegram_payload(payload, update_id, update_chat_id, 'callback_query')
                try: r25_trace_stage('EXECUTE_TELEGRAM_PAYLOAD_DONE')
                except Exception: pass
                success = True
                try:
                    UI_CLEANUP_TASK_POOL.submit(f'r22-inbox-done:{update_id}', _r22_callback_inbox_mark_background, update_id, 'done', '')
                    UI_CLEANUP_TASK_POOL.submit(f'r22-event-commit:{update_id}', _r22_callback_commit_background, update_id, update_chat_id, True, '')
                except Exception:
                    pass
            except Exception as exc:
                error_text = str(exc)
                try:
                    UI_CLEANUP_TASK_POOL.submit(f'r22-inbox-failed:{update_id}', _r22_callback_inbox_mark_background, update_id, 'failed', error_text)
                    UI_CLEANUP_TASK_POOL.submit(f'r22-event-failed:{update_id}', _r22_callback_commit_background, update_id, update_chat_id, False, error_text)
                except Exception:
                    pass
                try:
                    _v260_schedule_webhook_inbox_retry(update_id)
                except Exception:
                    pass
                try:
                    log_error(f'R22 CALLBACK PROCESS FAILED update={update_id} chat={update_chat_id}: {exc}')
                except Exception:
                    pass
                raise
            finally:
                try:
                    r25_trace_stage('HANDLER_DONE', time.time()-started, str(error_text or '')[:160])
                    log_info(f'FASTBTN handler update={update_id} chat={update_chat_id} wait={wait:.3f}s process={time.time()-started:.3f}s success={int(bool(success))} error={str(error_text or "")[:120]}')
                except Exception:
                    pass
                UPDATE_DISPATCHER.finish(update_id, success, error_text)
                try: r25_trace_end()
                except Exception: pass
                _r19_schedule_post_update_cleanup(update_id, update_chat_id, 'callback_query', wait, started, success, False)

        selector = globals().get('v163_webhook_select_lane')
        if callable(selector):
            selected_pool, selected_key = selector(payload, 'callback_query', update_key)
        else:
            selected_pool, selected_key = (FAST_UI_TASK_POOL, f'fast-callback:{update_key}')
        if not selected_pool.submit(selected_key, _process_callback):
            UPDATE_DISPATCHER.release_failed_enqueue(update_id, f'{selected_pool.name}_queue_full')
            return ('BUSY', 503)
    elif claim_state == 'done':
        # Keep the local durable row healthy if Telegram redelivered after a network race.
        try:
            if not _v260_webhook_inbox_put(update_id, payload, update_chat_id, 'callback_query'):
                return ('LOCAL DURABLE INBOX FAILED', 503)
        except Exception:
            return ('LOCAL DURABLE INBOX FAILED', 503)
        return ('OK', 200)

    # R26: FAST enqueue is the webhook admission point. SQLite inbox + remote witness
    # happen after admission on a background lane. This removes the 4-5 second POST /tg
    # tail seen when the shared SQLite connection was busy, while exact business ordering
    # remains inside the keyed callback actor.
    try:
        pool = globals().get('UI_CLEANUP_TASK_POOL') or globals().get('BACKGROUND_TASK_POOL')
        queued = bool(pool and pool.submit_unique(f'r25-callback-durable:{update_id}', _r25_callback_durable_admission, payload, update_id, update_chat_id))
        if not queued:
            threading.Thread(target=_r25_callback_durable_admission, args=(payload, update_id, update_chat_id), name=f'r25-cb-durable-{update_id}', daemon=True).start()
    except Exception:
        pass
    try:
        _cq = payload.get('callback_query') or {}
        log_info(f'BTNTRACE update={update_id} chat={update_chat_id} action={str(_cq.get("data") or "")[:180]} stage=FAST_ENQUEUED_HTTP200')
    except Exception:
        pass
    return ('OK', 200)

@app.route(WEBHOOK_ROUTE_PATH, methods=['POST'])
def telegram_webhook():
    if WEBHOOK_HEADER_SECRET_ENABLED:
        supplied = str(request.headers.get('X-Telegram-Bot-Api-Secret-Token', '') or '')
        if supplied != WEBHOOK_HEADER_SECRET:
            return ('FORBIDDEN', 403)
    try:
        keepalive_note_inbound_activity('telegram_webhook')
    except Exception:
        pass
    try:
        payload = request.get_json(force=True, silent=False)
        try:
            _r27_note = globals().get('r27_note_user_activity')
            if callable(_r27_note) and isinstance(payload, dict) and any(k in payload for k in ('callback_query','message','edited_message')):
                _r27_note('telegram')
        except Exception:
            pass
    except Exception as e:
        log_error(f'WEBHOOK: get_json failed: {e}')
        return ('BAD REQUEST', 400)
    if runtime_is_shutting_down():
        runtime_mark_webhook(payload if isinstance(payload, dict) else None, blocked='shutdown')
        return ('SHUTTING DOWN', 503)
    if not runtime_is_ready():
        runtime_mark_webhook(payload if isinstance(payload, dict) else None, blocked='boot')
        return ('BOOTING', 503)
    runtime_mark_webhook(payload if isinstance(payload, dict) else None)
    # R26 forensic receipt marker (normal Render log only; no DB/network dependency).
    if isinstance(payload, dict) and 'callback_query' in payload:
        try:
            _r25_cq = payload.get('callback_query') or {}
            _r25_msg = _r25_cq.get('message') or {}; _r25_chat = _r25_msg.get('chat') or {}
            log_info(f'BTNTRACE update={payload.get("update_id")} chat={_r25_chat.get("id")} action={str(_r25_cq.get("data") or "")[:180]} stage=RECEIVE')
        except Exception:
            pass
    # R18 absolute UI hot path: start Telegram callback ACK immediately after the
    # READY/shutdown gate, before logging, Update.de_json, SQLite inbox, Redis/Worker
    # witness, locks or routing.  The ACK uses a dedicated pool, so Telegram network
    # RTT runs in parallel with local window rendering.
    if isinstance(payload, dict) and 'callback_query' in payload:
        try:
            _r18_cq = payload.get('callback_query') or {}
            _r18_msg = _r18_cq.get('message') or {}
            _r18_chat = _r18_msg.get('chat') or {}
            _r18_cid = _r18_chat.get('id')
            try:
                _r25_reg = globals().get('r25_register_callback_update')
                if callable(_r25_reg): _r25_reg(str(_r18_cq.get('id') or ''), payload.get('update_id'), _r18_cid, str(_r18_cq.get('data') or ''))
            except Exception:
                pass
            schedule_callback_receipt_ack(str(_r18_cq.get('id') or ''), _r18_cid, delay=0.0)
        except Exception as ack_exc:
            log_error(f'CALLBACK IMMEDIATE ACK: {ack_exc}')
    try:
        if isinstance(payload, dict):
            if 'edited_message' in payload:
                log_info('WEBHOOK: получен update с edited_message ✅')
            elif 'message' in payload:
                log_info('WEBHOOK: получен update с message')
            elif 'callback_query' in payload:
                log_info('WEBHOOK: получен update с callback_query')
            try:
                upd_type = 'edited_message' if 'edited_message' in payload else 'message' if 'message' in payload else 'callback_query' if 'callback_query' in payload else 'other'
                if upd_type == 'callback_query':
                    cid_j = _extract_update_chat_id(payload)
                    UI_CLEANUP_TASK_POOL.submit(f'r22-webhook-journal:{payload.get("update_id", time.time_ns())}', bot_journal, 'webhook_update', cid_j, upd_type)
                else:
                    bot_journal('webhook_update', _extract_update_chat_id(payload), upd_type)
            except Exception:
                pass
        update = telebot.types.Update.de_json(payload)
        update_chat_id = _extract_update_chat_id(payload) if isinstance(payload, dict) else None
        update_id = getattr(update, 'update_id', None)
        if update_id is None:
            update_id = time.time_ns()
        update_key = update_chat_id if update_chat_id is not None else update_id
        update_type = 'edited_message' if isinstance(payload, dict) and 'edited_message' in payload else 'callback_query' if isinstance(payload, dict) and 'callback_query' in payload else 'message' if isinstance(payload, dict) and 'message' in payload else 'other'
        if update_type == 'callback_query':
            # Rare finance toggles keep the pre-execution cloud witness because replaying
            # a toggle twice can reverse state. All normal/navigation callbacks take R22.
            _r22_cloud_critical, _r22_cloud_reason = durable_task_required(payload)
            if not _r22_cloud_critical:
                return _r22_accept_callback_fast(payload, update_id, update_chat_id, update_key)
        _r25_adm_action = ''
        try:
            if update_type == 'callback_query': _r25_adm_action = str((payload.get('callback_query') or {}).get('data') or '')[:180]
            elif update_type in {'message','edited_message'}: _r25_adm_action = str(((payload.get(update_type) or payload.get('message') or {}).get('text') or update_type))[:180]
            log_info(f'BTNTRACE update={update_id} chat={update_chat_id} action={_r25_adm_action} stage=ADMISSION_SQLITE_START')
        except Exception: pass
        _r25_adm_started = time.monotonic()
        _inbox_state_v260 = _v260_webhook_inbox_state(update_id)
        if _inbox_state_v260 == 'done':
            return ('OK', 200)
        if not _v260_webhook_inbox_put(update_id, payload, update_chat_id, update_type):
            return ('LOCAL DURABLE INBOX FAILED', 503)
        try: log_info(f'BTNTRACE update={update_id} chat={update_chat_id} action={_r25_adm_action} stage=ADMISSION_SQLITE_DONE elapsed={time.monotonic()-_r25_adm_started:.3f}s')
        except Exception: pass
        # R13: before Telegram gets HTTP 200 and before business execution starts,
        # make the raw update durable on Worker/Redis.  If both remote witnesses are
        # unavailable, return 503 so Telegram retries instead of risking a deploy gap.
        _r13_witness_fn = globals().get('split_witness_event_v268')
        if callable(_r13_witness_fn):
            if update_type == 'callback_query':
                # UI callbacks are already in the local durable inbox.  Mirror the raw
                # event remotely on DELTA lane, but never put Redis/Worker RTT in front
                # of a user's button.  Message/finance traffic keeps the strict witness.
                def _r18_callback_witness():
                    try:
                        if not _r13_witness_fn(update_id, payload, update_chat_id, update_type):
                            log_error(f'R18 CALLBACK REMOTE WITNESS FAILED update={update_id}')
                    except Exception as _r18w_exc:
                        log_error(f'R18 CALLBACK REMOTE WITNESS ERROR update={update_id}: {_r18w_exc}')
                if not DELTA_TASK_POOL.submit_unique(f'callback-witness:{update_id}', _r18_callback_witness):
                    try:
                        threading.Thread(target=_r18_callback_witness, name=f'r18-cb-witness-{update_id}', daemon=True).start()
                    except Exception:
                        pass
            else:
                _r25_witness_started = time.monotonic()
                try: log_info(f'BTNTRACE update={update_id} chat={update_chat_id} action={_r25_adm_action} stage=REMOTE_WITNESS_START')
                except Exception: pass
                _r25_witness_ok = _r13_witness_fn(update_id, payload, update_chat_id, update_type)
                try: log_info(f'BTNTRACE update={update_id} chat={update_chat_id} action={_r25_adm_action} stage=REMOTE_WITNESS_DONE elapsed={time.monotonic()-_r25_witness_started:.3f}s detail={int(bool(_r25_witness_ok))}')
                except Exception: pass
                if not _r25_witness_ok:
                    log_error(f'R13 REMOTE EVENT WITNESS FAILED update={update_id}')
                    return ('REMOTE DURABLE WITNESS FAILED', 503)
        _protect_pending_ui_timers_on_receipt(payload)
        if durable_update_processed(update_id):
            _v260_webhook_inbox_mark(update_id, 'done')
            with _MEGA_TASK_LOCK:
                _mega_task_counters['skipped_done'] += 1
            return ('OK', 200)
        durable_cloud, durable_reason = durable_task_required(payload)
        durable_expected = _durable_expected_effects(payload) if durable_cloud else {}
        if durable_cloud:
            _v260_webhook_inbox_mark(update_id, 'external_pending')
            cloud_state = mega_task_known_state(update_id)
            if cloud_state == 'done':
                _v260_webhook_inbox_mark(update_id, 'done')
                with _MEGA_TASK_LOCK:
                    _mega_task_counters['skipped_done'] += 1
                return ('OK', 200)
            if cloud_state == 'running':
                schedule_mega_task_recovery(0.2)
                return ('TASK RUNNING', 503)
            if cloud_state == 'failed':
                _v260_webhook_inbox_mark(update_id, 'external_failed_review')
                return ('TASK NEEDS REVIEW', 200)
            if cloud_state != 'pending':
                task_payload = _build_mega_task_payload(update_id, payload, update_chat_id, update_type, durable_reason)
                durable_expected = _durable_expected_from_task_or_payload(task_payload, payload)
                if not _mega_task_upload_new_pending(update_id, task_payload):
                    return ('TASK BACKUP UNAVAILABLE', 503)
        claim_state, ticket = UPDATE_DISPATCHER.claim(update_id, update_chat_id, update_type)
        if claim_state == 'done':
            return ('OK', 200)
        update_enqueued_at = time.time()
        if claim_state == 'new':

            def _process_update():
                started = time.time()
                wait = started - update_enqueued_at
                UPDATE_DISPATCHER.mark_started(update_id)
                try:
                    _r25_worker_action = ''
                    if update_type == 'callback_query': _r25_worker_action = str((payload.get('callback_query') or {}).get('data') or '')
                    elif update_type in {'message','edited_message'}: _r25_worker_action = str(((payload.get(update_type) or payload.get('message') or {}).get('text') or update_type))
                    r25_trace_begin(update_id, update_chat_id, update_type, _r25_worker_action)
                    r25_trace_stage('GENERAL_HANDLER_ENTER')
                except Exception: pass
                _v260_webhook_inbox_mark(update_id, 'external_running' if durable_cloud else 'running')
                if update_type == 'callback_query':
                    try:
                        UI_CLEANUP_TASK_POOL.submit(f'journal-start:{update_id}', _r19_update_journal_start, update_id, update_chat_id, update_type, wait, durable_cloud)
                    except Exception:
                        pass
                else:
                    _r19_update_journal_start(update_id, update_chat_id, update_type, wait, durable_cloud)
                success = False
                error_text = ''
                durable_started = False
                try:
                    if durable_cloud:
                        durable_started = mega_task_begin(update_id, allow_existing_running=False)
                        if not durable_started:
                            raise RuntimeError('MEGA durable task could not enter running state')
                    try: r25_trace_stage('EXECUTE_TELEGRAM_PAYLOAD_START')
                    except Exception: pass
                    execution_ctx = _execute_telegram_payload(payload, update_id, update_chat_id, update_type)
                    try: r25_trace_stage('EXECUTE_TELEGRAM_PAYLOAD_DONE')
                    except Exception: pass
                    success = True
                    _v260_webhook_inbox_mark(update_id, 'done')
                    _r13_commit_fn = globals().get('split_event_committed_v268')
                    if callable(_r13_commit_fn): _r13_commit_fn(update_id, update_chat_id, update_type, True, '')
                    if durable_cloud:
                        durable_expected_after = _durable_expected_after_execution(durable_expected, execution_ctx, payload)
                        queued_finalize = enqueue_durable_finalize_background(update_id, update_chat_id, update_type, payload, durable_expected_after)
                        if not queued_finalize:
                            finalized = finalize_durable_task_after_business(update_id, update_chat_id, update_type, payload=payload, expected_effects=durable_expected_after)
                            if not finalized:
                                schedule_durable_task_finalize_retry(update_id, update_chat_id, update_type, 1.0, payload=payload, expected_effects=durable_expected_after)
                                log_error(f'MEGA TASK FINALIZE DEFERRED update={update_id}; durable effects still pending')
                except Exception as exc:
                    error_text = str(exc)
                    _failed_inbox_v260 = _v260_webhook_inbox_mark(update_id, 'external_failed_review' if durable_cloud else 'failed', error_text)
                    _r13_commit_fn = globals().get('split_event_committed_v268')
                    if callable(_r13_commit_fn): _r13_commit_fn(update_id, update_chat_id, update_type, False, error_text)
                    if not durable_cloud:
                        _v260_schedule_webhook_inbox_retry(_failed_inbox_v260 or update_id)
                    if durable_cloud and durable_started:
                        mega_task_finish(update_id, False, error_text)
                    log_error(f'WEBHOOK PROCESS FAILED update={update_id} chat={update_chat_id}: {exc}')
                    raise
                finally:
                    try: r25_trace_stage('HANDLER_DONE', time.time()-started, str(error_text or '')[:160])
                    except Exception: pass
                    UPDATE_DISPATCHER.finish(update_id, success, error_text)
                    try: r25_trace_end()
                    except Exception: pass
                    # R19: release the callback/content worker immediately. Cleanup is
                    # serialized on a separate pool and can never keep a UI key active.
                    _r19_schedule_post_update_cleanup(update_id, update_chat_id, update_type, wait, started, success, durable_cloud)
            selector = globals().get('v163_webhook_select_lane')
            if callable(selector):
                selected_pool, selected_key = selector(payload, update_type, update_key)
            else:
                selected_pool = UI_TASK_POOL if update_type == 'callback_query' else WEBHOOK_TASK_POOL
                selected_key = f'ui:{update_key}' if update_type == 'callback_query' else update_key
            if not selected_pool.submit(selected_key, _process_update):
                log_error(f'{selected_pool.name.upper()} QUEUE FULL: chat={update_chat_id}')
                UPDATE_DISPATCHER.release_failed_enqueue(update_id, f'{selected_pool.name}_queue_full')
                return ('BUSY', 503)
            # v260: every non-cloud update is first committed to the local SQLite inbox.
            # Once accepted into its keyed worker queue Telegram can be acknowledged at once:
            # a restart will replay the local inbox, while source/forward operation keys make
            # that replay exact-once.  Cloud-durable updates retain their external witness path.
            if not durable_cloud:
                return ('OK', 200)
        if claim_state == 'pending' and _v260_webhook_inbox_state(update_id) in {'queued','running','done'} and not durable_cloud:
            return ('OK', 200)
        state, dispatch_error = UPDATE_DISPATCHER.wait_result(ticket, WEBHOOK_ACK_WAIT_SECONDS)
        if state == 'done':
            return ('OK', 200)
        if state == 'failed':
            return ('RETRY', 503)
        return ('PENDING', 503)
    except Exception as e:
        log_error(f'WEBHOOK: enqueue/update dispatcher error: {e}')
        return ('ERROR', 500)

def _v177_legacy_0269_set_webhook():
    global WEBHOOK_HEADER_SECRET_ENABLED
    if not WEBHOOK_URL:
        log_info('WEBHOOK_URL / APP_URL / RENDER_EXTERNAL_URL не указаны — webhook не установлен.')
        return
    wh_url = WEBHOOK_URL.rstrip('/') + WEBHOOK_ROUTE_PATH
    force_reset = str(os.getenv('WEBHOOK_FORCE_RESET', '0') or '0').strip().casefold() in {'1', 'true', 'yes', 'on'}
    if force_reset:
        bot.remove_webhook()
        time.sleep(0.5)
    try:
        webhook_connections = max(1, min(100, int(os.getenv('WEBHOOK_MAX_CONNECTIONS', '40') or '40')))
    except Exception:
        webhook_connections = 40
    kwargs = dict(url=wh_url, max_connections=webhook_connections, allowed_updates=['message', 'edited_message', 'callback_query', 'channel_post', 'edited_channel_post', 'deleted_business_messages'])
    try:
        bot.set_webhook(secret_token=WEBHOOK_HEADER_SECRET, **kwargs)
        WEBHOOK_HEADER_SECRET_ENABLED = True
    except TypeError:
        bot.set_webhook(**kwargs)
        WEBHOOK_HEADER_SECRET_ENABLED = False
    log_info(f'Webhook установлен: /tg/<secret> (max_connections={webhook_connections}; force_reset={force_reset}; secret_header={WEBHOOK_HEADER_SECRET_ENABLED})')
try:
    _v177_legacy_0269_set_webhook.__name__ = 'set_webhook'
except Exception:
    pass

def _v177_start_web_server_early():
    """Compatibility server starter; v211 decides WHEN the production port is bound."""

    def _serve():
        app.run(host='0.0.0.0', port=PORT, threaded=True, use_reloader=False)
    thread = threading.Thread(target=_serve, name='v177-web-early', daemon=True)
    thread.start()
    return thread
_V211_WEB_BIND_LOCK = threading.RLock()
_V211_WEB_THREAD = None
try:
    V211_BOOT_BIND_FAILSAFE_SECONDS = max(15.0, min(60.0, float(os.getenv('BOOT_BIND_FAILSAFE_SECONDS', '30') or '30')))
except Exception:
    V211_BOOT_BIND_FAILSAFE_SECONDS = 30.0
try:
    V211_DEPLOY_HANDOFF_GRACE_SECONDS = max(2.0, min(12.0, float(os.getenv('DEPLOY_HANDOFF_GRACE_SECONDS', '5') or '5')))
except Exception:
    V211_DEPLOY_HANDOFF_GRACE_SECONDS = 5.0

def _v211_ensure_web_server_started(reason: str='ready-handoff'):
    global _V211_WEB_THREAD
    with _V211_WEB_BIND_LOCK:
        if _V211_WEB_THREAD is not None and _V211_WEB_THREAD.is_alive():
            return _V211_WEB_THREAD
        _V211_WEB_THREAD = _v177_start_web_server_early()
    try:
        runtime_event('web_server_bound_v211', f'reason={reason}; ready={int(runtime_is_ready())}')
    except Exception:
        pass
    return _V211_WEB_THREAD

def _v211_boot_bind_failsafe():
    time.sleep(float(V211_BOOT_BIND_FAILSAFE_SECONDS))
    if runtime_is_shutting_down():
        return
    with _V211_WEB_BIND_LOCK:
        alive = bool(_V211_WEB_THREAD is not None and _V211_WEB_THREAD.is_alive())
    if not alive:
        try:
            runtime_event('web_bind_failsafe_v211', f'after={V211_BOOT_BIND_FAILSAFE_SECONDS:g}s', 'WARN')
        except Exception:
            pass
        _v211_ensure_web_server_started('failsafe')
_V211_POST_READY_STARTED = False
_V211_POST_READY_LOCK = threading.RLock()
STARTUP_RELEASE_SUMMARY = (
    '• ⚡ Пер-R37: FAST не ждёт SQLite I/O под глобальным data_lock; lock-диагностика показывает держателя.\n'
    '• 🧩 R36 HEAVY: job принимается только после durable Redis/MEGA spool; после рестарта поднимается с тем же job_id.\n'
    '• 🧭 Третий вариант: настройки сгруппированы по Финансам / Пересылке / Напоминаниям / Задачам / Контурам / Общим / Журналам / Владельцу.\n'
    '• 🏷 Мастер ТЗ окон + маркеры и 🧩 мастер Конструкторов; центр Конструкторов доступен даже когда кнопки в рабочих окнах скрыты.\n'
    '• 🛰 Активный чат остаётся горячим в RAM; LOWRAM выгружает данные только при реальном давлении памяти, а HEAVY/split остаётся на Render #2.\n'
    '• 💾 Сохраняется надёжная R20/v262 схема durable capsule: максимум config generation + максимум user-state seq без отката.\n'
    '• 🔒 Полный SQLite + delta/event journal остаются вторым уровнем защиты финансов и остальных данных; capsule не содержит финансовые cold-ledger записи.\n'
    '• 🚀 Redis callback-токены зеркалируются пакетно в фоне; UI и render сохраняют строгий порядок FIFO.'
)


def _v211_start_post_ready_runtime():
    """Start user-visible/background business schedulers only after true READY."""
    global _V211_POST_READY_STARTED
    if not runtime_is_ready() or runtime_is_shutting_down():
        return False
    with _V211_POST_READY_LOCK:
        if _V211_POST_READY_STARTED:
            return True
        _V211_POST_READY_STARTED = True
    try:
        schedule_expense_ping_recovery(1.5)
    except Exception as e:
        log_error(f'expense ping recovery schedule: {e}')
    try:
        start_keep_alive_thread()
    except Exception as e:
        log_error(f'keepalive start: {e}')
    try:
        start_reminder_scheduler()
    except Exception as e:
        log_error(f'reminder scheduler start: {e}')
    try:
        start_safety_schedulers()
    except Exception as e:
        log_error(f'safety schedulers start: {e}')
    try:
        pending = SQLITE.get_meta('restore_control_v240', 'remote_reanchor_pending', {}) or {}
        retry_fn = globals().get('_v240_schedule_pending_restore_reanchor_retry')
        if pending and callable(retry_fn):
            retry_fn(10.0)
    except Exception as e:
        log_error(f'v240 pending restore re-anchor schedule: {e}')
    try:
        st_fn = globals().get('telegram_durable_status_v234')
        sched_fn = globals().get('telegram_schedule_full_snapshot_v234')
        if callable(st_fn) and callable(sched_fn):
            _tgst = st_fn()
            if _tgst.get('configured') and int(_tgst.get('snapshot_parts') or 0) <= 0:
                sched_fn('first_generation', delay=15.0)
    except Exception as e:
        log_error(f'telegram durable initial snapshot schedule: {e}')
    try:
        try:
            _inbox_recovered_v260 = recover_webhook_inbox_v260(100)
            _remote_recover_fn = globals().get('split_recover_remote_events_v268')
            _remote_recovered_v268 = _remote_recover_fn(100) if callable(_remote_recover_fn) else 0
            _fin_recovered_v260 = recover_partial_finance_forwards_v260(200) if callable(globals().get('recover_partial_finance_forwards_v260')) else 0
            runtime_event('v260_local_recovery_started', f'webhook={_inbox_recovered_v260}; remote_event={_remote_recovered_v268}; finance_forward={_fin_recovered_v260}')
        except Exception as _v260_recovery_exc:
            log_error(f'v260 local recovery start: {_v260_recovery_exc}')
        runtime_event('post_ready_runtime_started_v211', 'expense/keepalive/reminder/safety/telegram-durable/v260-local-inbox')
    except Exception:
        pass
    return True

def _v211_notify_owner_ready_once():
    try:
        if not runtime_is_ready() or not OWNER_ID:
            return False
        with _RUNTIME_LOCK:
            if _RUNTIME_STATE.get('owner_ready_notice_sent'):
                return True
            _RUNTIME_STATE['owner_ready_notice_sent'] = True
        owner_id = int(OWNER_ID)
        bot.send_message(owner_id, f"{('🚨' if RESTORE_GUARD_ACTIVE else '✅')} {version_animal_badge()} Бот запущен и READY (Пер-R37 · версия {VERSION}).\n🛠 Правки версии:\n{STARTUP_RELEASE_SUMMARY}\nСтарт Python: {_RUNTIME_STATE.get('started_at') or '—'}; READY: {_RUNTIME_STATE.get('ready_at') or '—'}; boot {_RUNTIME_STATE.get('boot_duration_seconds') or '—'}с\nВосстановление: {_RUNTIME_STATE.get('restore_detail') or '—'}\nRender instance: {str(os.getenv('RENDER_INSTANCE_ID', '') or '—')[-28:]}; commit: {str(os.getenv('RENDER_GIT_COMMIT', '') or '—')[:12]}\nDurable-задачи ({mega_task_registry_stats().get('backend', 'mega')}): pending {mega_task_registry_stats().get('pending', 0)}, running {mega_task_registry_stats().get('running', 0)}, failed {mega_task_registry_stats().get('failed', 0)}\nЖурнал: {('✅ ВКЛ' if is_journal_registration_enabled() else '⬜ ВЫКЛ')}; keep-alive: {('✅ ВКЛ' if globals().get('keepalive_self_enabled', lambda: KEEP_ALIVE_ENABLED)() else '⬜ ВЫКЛ')}\n/start")
        return True
    except Exception as exc:
        try:
            log_error(f'notify owner READY v211: {exc}')
        except Exception:
            pass
        return False

def _v211_deploy_handoff_catchup(db_restored: bool) -> int:
    """Late cut-over gate: bind near the end of boot, settle briefly, then re-read remote durability.

    During normal deploy the previous healthy instance can continue serving while this new
    process restores MEGA.  The second delta/task pass picks up remote changes that appeared
    during that overlap before this process declares READY.  It deliberately does not assume
    an exact Render SIGTERM/cut-over ordering; business durability remains protected by the
    existing write-before-execute tasks + delta/Data Constitution contracts.
    """
    if str(os.getenv('SPLIT_PREBOOT_AUTHORITATIVE_R20', '') or '').strip().casefold() in {'1','true','yes','on'}:
        # start_front already settled Worker/Redis handoff. Never re-apply legacy
        # Telegram/MEGA deltas over the authoritative split database.
        runtime_event('boot_handoff_r20_split_authority', 'legacy remote delta catch-up skipped')
        return 0
    runtime_set_phase('boot_deploy_handoff', 'порт готов; финальная сверка remote delta/tasks перед READY')
    _v211_ensure_web_server_started('deploy-handoff')
    time.sleep(float(V211_DEPLOY_HANDOFF_GRACE_SECONDS))
    caught = 0
    if db_restored:
        try:
            caught = int(lowram_apply_deltas_after_db_snapshot() or 0)
            runtime_event('boot_handoff_delta_catchup_v211', f'applied={caught}')
        except Exception as exc:
            runtime_event('boot_handoff_delta_catchup_error_v211', str(exc), 'WARN')
    try:
        if mega_tasks_active():
            mega_task_refresh_registry()
            runtime_recover_tasks_blocking(min(10.0, float(BOOT_SYNC_RECOVERY_SECONDS)))
    except Exception as exc:
        runtime_event('boot_handoff_task_refresh_error_v211', str(exc), 'WARN')
    return caught

def main():
    global data
    runtime_install_signal_handlers()
    # v250: Render must see an open port before any remote storage/login/restore.
    # /healthz is available immediately; / and /readyz remain BOOTING/503 until
    # the durability restore and verification have actually completed.
    _v211_ensure_web_server_started('boot-immediate-v250')
    runtime_set_phase('boot_port_bound_v250', 'порт Render открыт; начинаю выбор storage и восстановление')
    threading.Thread(target=_v211_boot_bind_failsafe, name='v211-web-bind-failsafe', daemon=True).start()
    try:
        _boot_profile = storage_profile_bootstrap_v237_1()
    except Exception:
        _boot_profile = storage_profile_v237_1()
    try:
        runtime_event('boot_storage_authority_v238', f"profile={_boot_profile}; source={globals().get('_STORAGE_PROFILE_BOOT_SOURCE_V238', 'unknown')}; mega_root={globals().get('MEGA_BACKUP_DIR', '')}")
    except Exception:
        pass
    _restore_backend = str(globals().get('_STORAGE_PROFILE_RESTORE_BACKEND_V246') or '').strip().casefold()
    if _restore_backend not in {'telegram', 'mega', 'local'}:
        _restore_backend = 'telegram' if _boot_profile == STORAGE_PROFILE_TELEGRAM_V237_1 else 'mega' if _boot_profile == STORAGE_PROFILE_MEGA_V237_1 else 'local'
    _tg_primary = bool(_restore_backend == 'telegram' and telegram_durable_available_v237_1())
    _mega_primary = bool(_restore_backend == 'mega' and MEGA_ENABLED and MEGA_EMAIL and MEGA_PASSWORD)
    _local_primary = not (_tg_primary or _mega_primary)
    _render_selected = bool(_boot_profile == STORAGE_PROFILE_LOCAL_V237_1)
    _backend_name = 'Telegram durable' if _tg_primary else 'MEGA' if _mega_primary else 'Render local'
    _split_preboot_authoritative_r19 = str(os.getenv('SPLIT_PREBOOT_AUTHORITATIVE_R20', '') or '').strip().casefold() in {'1','true','yes','on'}
    _split_preboot_revision_r19 = str(os.getenv('SPLIT_PREBOOT_REVISION_R20', '') or '').strip()
    if _split_preboot_authoritative_r19:
        # R19: start_front has already chosen the freshest Worker/Redis/local SQLite.
        # Disable every legacy boot source for this process so there is exactly one
        # restore authority and no fresh->old rollback during bot.main().
        _tg_primary = False
        _mega_primary = False
        _local_primary = True
        _restore_backend = 'split'
        _backend_name = 'Split Worker/Redis authoritative'
    try:
        runtime_event('boot_restore_backend_v246', f"selected_profile={_boot_profile}; restore_backend={_restore_backend}; evidence={json.dumps(globals().get('_STORAGE_PROFILE_REMOTE_EVIDENCE_V246', {}), ensure_ascii=False, default=str)[:1200]}")
    except Exception:
        pass
    _v246_prev_recovery_authority = bool(globals().get('_V240_RECOVERY_AUTHORITY_ACTIVE', False))
    if _render_selected and (_tg_primary or _mega_primary):
        globals()['_V240_RECOVERY_AUTHORITY_ACTIVE'] = True
    runtime_set_phase('boot_local_load', f'восстанавливаю рабочую SQLite из {_backend_name} / локального диска')
    restored = bool(_split_preboot_authoritative_r19)
    db_restored = bool(_split_preboot_authoritative_r19)
    db_detail = (f'Пер-R37 split authoritative revision={_split_preboot_revision_r19 or "unknown"}' if _split_preboot_authoritative_r19 else '')
    if LOWRAM_ENABLED and (not _split_preboot_authoritative_r19):
        try:
            if _tg_primary:
                if storage_mode_feature_enabled_v240('telegram_durable', 'boot_restore', recovery=_render_selected):
                    db_restored, db_detail = telegram_restore_sqlite_snapshot_v234()
                else:
                    db_restored, db_detail = (False, 'Telegram boot restore disabled by mode feature')
            elif _mega_primary:
                if storage_mode_feature_enabled_v240('mega', 'boot_restore', recovery=_render_selected):
                    db_restored, db_detail = mega_restore_sqlite_snapshot_from_cloud()
                else:
                    db_restored, db_detail = (False, 'MEGA boot restore disabled by mode feature')
            else:
                db_restored, db_detail = (False, 'No remote restore backend selected')

            # v246 Render-only recovery: evidence chooses the best source first, but
            # a remote snapshot can disappear or fail verification between probe and
            # download. If that happens, try the other *complete* remote source before
            # falling back to local state. The running profile still remains Render-only.
            if _render_selected and not db_restored and (_tg_primary or _mega_primary):
                evidence = globals().get('_STORAGE_PROFILE_REMOTE_EVIDENCE_V246', {}) or {}
                alt_backend = 'mega' if _tg_primary else 'telegram'
                alt = evidence.get(alt_backend) if isinstance(evidence, dict) else None
                alt_ok = bool(isinstance(alt, dict) and alt.get('available') and alt.get('full'))
                if alt_backend == 'telegram':
                    alt_ok = bool(alt_ok and telegram_durable_available_v237_1())
                else:
                    alt_ok = bool(alt_ok and MEGA_ENABLED and MEGA_EMAIL and MEGA_PASSWORD)
                if alt_ok:
                    try:
                        if alt_backend == 'telegram' and storage_mode_feature_enabled_v240('telegram_durable', 'boot_restore', recovery=True):
                            alt_restored, alt_detail = telegram_restore_sqlite_snapshot_v234()
                        elif alt_backend == 'mega' and storage_mode_feature_enabled_v240('mega', 'boot_restore', recovery=True):
                            alt_restored, alt_detail = mega_restore_sqlite_snapshot_from_cloud()
                        else:
                            alt_restored, alt_detail = (False, 'alternate recovery feature disabled')
                        runtime_event('boot_restore_fallback_v246', f'from={_restore_backend}; to={alt_backend}; ok={alt_restored}; {alt_detail}')
                        if alt_restored:
                            db_restored, db_detail = True, f'fallback {alt_backend}: {alt_detail}'
                            _restore_backend = alt_backend
                            _tg_primary = alt_backend == 'telegram'
                            _mega_primary = alt_backend == 'mega'
                            _local_primary = False
                            _backend_name = 'Telegram durable' if _tg_primary else 'MEGA'
                    except Exception as alt_exc:
                        runtime_event('boot_restore_fallback_error_v246', f'to={alt_backend}; {alt_exc}', 'WARN')
            runtime_event('boot_sqlite_snapshot', f'backend={_backend_name}; ok={db_restored} {db_detail}')
        except Exception as e:
            runtime_event('boot_sqlite_snapshot_error', f'backend={_backend_name}; {e}', 'WARN')
    data = load_data()
    try:
        storage_profile_apply_boot_hint_v237_1()
    except Exception as exc:
        try:
            runtime_event('storage_profile_apply_v246', str(exc), 'WARN')
        except Exception:
            pass
    if _tg_primary:
        try:
            telegram_durable_bootstrap_v234(True)
            delta_count = telegram_apply_remote_deltas_v234()
            restored = bool(db_restored or delta_count)
            runtime_event('boot_telegram_deltas', f'applied={delta_count}')
        except Exception as e:
            runtime_event('boot_telegram_deltas_error', str(e), 'ERROR')
    elif db_restored and _mega_primary:
        try:
            delta_count = lowram_apply_deltas_after_db_snapshot()
            restored = True
            runtime_event('boot_sqlite_deltas', f'applied={delta_count}')
            try:
                config_guard_bind_recovered_state_v242()
            except Exception as _cfg_bind_exc:
                runtime_event('boot_config_binding_finalize_error_v242', str(_cfg_bind_exc), 'ERROR')
                raise
        except Exception as e:
            restored = False
            runtime_event('boot_sqlite_deltas_error', str(e), 'ERROR')
    runtime_set_phase('boot_remote_restore', f'проверяю snapshot / fallback / delta в {_backend_name}')
    with _RUNTIME_LOCK:
        _RUNTIME_STATE['restore_attempted'] = True
    try:
        if _tg_primary:
            if not db_restored and (not restored):
                _lowram_prepare_loaded_data(data, migrate_existing=True)
                _lowram_flush_all_hot(evict=True)
            with _RUNTIME_LOCK:
                _RUNTIME_STATE['restore_ok'] = bool(not RESTORE_GUARD_ACTIVE)
                suffix = '; running profile remains Render-only' if _render_selected else ''
                _RUNTIME_STATE['restore_detail'] = (f'Telegram SQLite snapshot + deltas ({db_detail})' if db_restored else 'Telegram deltas applied' if restored else 'restore guard active' if RESTORE_GUARD_ACTIVE else 'local state retained; Telegram snapshot not yet available') + suffix
        elif _mega_primary:
            if not db_restored:
                restored = mega_autorestore_if_needed()
                _lowram_prepare_loaded_data(data, migrate_existing=True)
                _lowram_flush_all_hot(evict=True)
            if not (db_restored or restored):
                try:
                    _set_restore_guard('MEGA boot restore did not find a valid canonical snapshot/generation')
                except Exception:
                    pass
            with _RUNTIME_LOCK:
                _RUNTIME_STATE['restore_ok'] = bool(db_restored or restored)
                suffix = '; running profile remains Render-only' if _render_selected else ''
                _RUNTIME_STATE['restore_detail'] = ('MEGA SQLite generation + verified deltas' if db_restored else 'MEGA legacy-global fallback applied' if restored else 'MEGA restore failed: no valid snapshot/generation') + suffix
        else:
            _lowram_prepare_loaded_data(data, migrate_existing=True)
            _lowram_flush_all_hot(evict=True)
            with _RUNTIME_LOCK:
                _RUNTIME_STATE['restore_ok'] = bool(not RESTORE_GUARD_ACTIVE)
                _RUNTIME_STATE['restore_detail'] = (db_detail if _split_preboot_authoritative_r19 else 'Local Render state retained; no remote recovery source available')
    except Exception as e:
        log_error(f'main durable restore: {e}')
        restored = False
        with _RUNTIME_LOCK:
            _RUNTIME_STATE['restore_ok'] = False
            _RUNTIME_STATE['restore_detail'] = str(e)[:500]
        runtime_event('boot_restore_error', str(e), 'ERROR')
    finally:
        globals()['_V240_RECOVERY_AUTHORITY_ACTIVE'] = _v246_prev_recovery_authority
    try:
        purge = globals().get('purge_legacy_mega_root_state_v238')
        if callable(purge):
            purge(True)
    except Exception as exc:
        runtime_event('mega_root_legacy_state_purge_warn_v238', str(exc), 'WARN')
    try:
        cfg_report = config_guard_boot_verify_v234()
        runtime_event('boot_config_guard_v234', json.dumps(cfg_report, ensure_ascii=False, default=str)[:1200], 'INFO' if cfg_report.get('ok') else 'ERROR')
        if not bool(cfg_report.get('ok')):
            with _RUNTIME_LOCK:
                _RUNTIME_STATE['restore_ok'] = False
                _RUNTIME_STATE['restore_detail'] = 'CONFIG GUARD: ' + str(cfg_report.get('reason') or 'configuration verification failed')[:420]
    except Exception as exc:
        with _RUNTIME_LOCK:
            _RUNTIME_STATE['restore_ok'] = False
            _RUNTIME_STATE['restore_detail'] = 'CONFIG GUARD ERROR: ' + str(exc)[:420]
        runtime_event('boot_config_guard_error_v234', str(exc), 'ERROR')
    try:
        protected_ok, protected_detail = constitution_verify_protected_symbols()
        if not protected_ok:
            raise RuntimeError('storage-core redefined: ' + str(protected_detail))
        constitution_report = constitution_boot_verify_after_restore()
        if not bool(constitution_report.get('ok')):
            with _RUNTIME_LOCK:
                _RUNTIME_STATE['restore_ok'] = False
                _RUNTIME_STATE['restore_detail'] = 'DATA CONSTITUTION GUARD: ' + str(constitution_report.get('reason') or 'semantic verification failed')[:420]
        runtime_event('boot_data_constitution', json.dumps({'ok': bool(constitution_report.get('ok')), 'mode': constitution_report.get('mode'), 'reason': constitution_report.get('reason'), 'records': (constitution_report.get('live') or {}).get('total_records')}, ensure_ascii=False), 'INFO' if bool(constitution_report.get('ok')) else 'ERROR')
    except Exception as exc:
        try:
            constitution_set_quarantine(f'BOOT constitution exception: {exc}')
        except Exception:
            pass
        with _RUNTIME_LOCK:
            _RUNTIME_STATE['restore_ok'] = False
            _RUNTIME_STATE['restore_detail'] = 'DATA CONSTITUTION ERROR: ' + str(exc)[:420]
        runtime_event('boot_data_constitution_error', str(exc), 'ERROR')
    runtime_set_phase('boot_watcher_previous', 'читаю предыдущий runtime snapshot')
    try:
        prev_runtime = runtime_load_previous_snapshot()
        prev_reason = runtime_classify_previous(prev_runtime)
        with _RUNTIME_LOCK:
            _RUNTIME_STATE['previous_reason'] = prev_reason
        runtime_event('previous_runtime', prev_reason)
    except Exception as e:
        runtime_event('previous_runtime_error', str(e), 'WARN')
    runtime_set_phase('boot_journal_deferred', 'диагностический журнал прогревается после READY; бизнес-durability уже проверена')
    if not RESTORE_GUARD_ACTIVE:
        migrate_legacy_owner_secrets()
    try:
        gs = data.setdefault('_global_settings', {})
        if not bool(gs.get('journal_default_off_v83_applied', False)):
            gs['bot_journal_enabled'] = False
            for _cid, _store in (data.get('chats', {}) or {}).items():
                if isinstance(_store, dict):
                    _store.setdefault('settings', {})['journal_enabled'] = False
            gs['journal_default_off_v83_applied'] = True
        gs.setdefault('bot_behavior_profile', DEFAULT_BOT_BEHAVIOR_PROFILE)
        if not bool(gs.get('version_mode_v88_migrated', False)):
            if str(gs.get('bot_behavior_profile') or '') == 'v87_current':
                gs['bot_behavior_profile'] = 'v88_current'
            gs['version_mode_v88_migrated'] = True
        if not bool(gs.get('version_mode_v90_migrated', False)):
            if str(gs.get('bot_behavior_profile') or '') == 'v88_current':
                gs['bot_behavior_profile'] = 'v90_current'
            gs['version_mode_v90_migrated'] = True
        if not bool(gs.get('version_mode_v91_migrated', False)):
            if str(gs.get('bot_behavior_profile') or '') == 'v90_current':
                gs['bot_behavior_profile'] = 'v91_current'
            gs['version_mode_v91_migrated'] = True
        if not bool(gs.get('version_mode_v92_migrated', False)):
            if str(gs.get('bot_behavior_profile') or '') == 'v91_current':
                gs['bot_behavior_profile'] = 'v92_current'
            gs['version_mode_v92_migrated'] = True
        if not bool(gs.get('category_names_clean_v88_applied', False)):
            for _cid, _store in (data.get('chats', {}) or {}).items():
                if not isinstance(_store, dict):
                    continue
                _custom_category_list(_store)
                _base_category_items(_store)
            gs['category_names_clean_v88_applied'] = True
    except Exception as e:
        log_error(f'v88 defaults migration: {e}')
    try:
        migrated_v208 = bool(journal_v208_apply_defaults())
        try:
            _v176_apply_runtime_flags()
        except Exception:
            pass
        runtime_event('journal_v208_boot_policy', f'migrated={int(migrated_v208)} full={int(is_journal_registration_enabled())} compact={int(journal_compact_remote_effective_enabled())} interval={journal_compact_interval_seconds()}s')
    except Exception as e:
        runtime_event('journal_v208_boot_policy_error', str(e), 'ERROR')
    journal_start_durable_loop()
    try:
        if 'tenant_v148_bootstrap' in globals():
            tenant_report = tenant_v148_bootstrap()
            runtime_event('tenant_v148_bootstrap', json.dumps(tenant_report, ensure_ascii=False))
    except Exception as e:
        log_error(f'tenant_v148_bootstrap: {e}')
        runtime_event('tenant_v148_bootstrap_error', str(e), 'ERROR')
    try:
        marker_report = audit_window_marker_registry()
        log_info(f'Маркеры окон проверены: {marker_report}')
    except Exception as e:
        log_error(f'audit_window_marker_registry: {e}')
    try:
        DELAYED_SCHEDULER.schedule('usd-rate-refresh', 2.0, _usd_rate_refresh_tick)
    except Exception as e:
        log_error(f'usd rate refresh start: {e}')
    for cid in list((data.get('chats', {}) or {}).keys()):
        try:
            store = get_chat_store(int(cid))
            settings = store.setdefault('settings', {})
            settings.setdefault('quick_balance_enabled', False)
            settings.setdefault('quick_balance_behavior', 'normal')
            settings.setdefault('quick_balance_user_selected', False)
            settings.setdefault('hidden_finance', False)
            settings.setdefault('auto_backup_enabled', True)
            settings.setdefault('auto_backup_to_mega_enabled', False)
            settings.setdefault('journal_enabled', True)
            settings.setdefault('main_article_buttons_enabled', False)
            settings.setdefault('main_financial_value_buttons_enabled', False)
            settings.setdefault('currency_mode', 'ars_usd' if settings.get('usd_display_enabled', False) else 'ars')
            settings.setdefault('remaining_show_ost_label', True)
            settings.setdefault('total_secret_mode', False)
        except Exception:
            pass
    runtime_set_phase('boot_runtime_state', 'восстанавливаю индексы и окна')
    _restore_runtime_state_from_data(data)
    restore_finance_window_runtime_state()
    if not RESTORE_GUARD_ACTIVE:
        save_data(data)
        data['forward_rules'] = load_forward_rules()
        try:
            if 'tenant_v148_enforce_forward_isolation' in globals():
                removed = tenant_v148_enforce_forward_isolation()
                if removed:
                    runtime_event('tenant_cross_links_removed_after_load', f'count={removed}', 'WARN')
        except Exception as e:
            log_error(f'tenant forward isolation after load: {e}')
    else:
        data.setdefault('forward_rules', {})
        log_error('v91 emergency mode: local writes and all automatic backups remain blocked')
    try:
        initialize_delta_baseline(data)
    except Exception as e:
        log_error(f'initialize_delta_baseline: {e}')
    runtime_set_phase('boot_task_registry', 'читаю durable tasks pending/running')
    boot_recovery_remaining = 0
    if mega_tasks_active():
        try:
            task_stats = mega_task_refresh_registry()
            log_info(f"[DURABLE TASKS STARTUP:{task_stats.get('backend', 'mega')}] pending={task_stats.get('pending', 0)} running={task_stats.get('running', 0)} failed={task_stats.get('failed', 0)} done={task_stats.get('done', 0)}")
            runtime_recover_tasks_blocking(BOOT_SYNC_RECOVERY_SECONDS)
            boot_recovery_remaining = len(_runtime_pending_recovery_rows())
        except Exception as e:
            log_error(f'mega_task_refresh/recovery startup: {e}')
            runtime_event('boot_task_recovery_error', str(e), 'ERROR')
            try:
                boot_recovery_remaining = len(_runtime_pending_recovery_rows())
            except Exception:
                boot_recovery_remaining = 1
    with _RUNTIME_LOCK:
        _RUNTIME_STATE['task_recovery_remaining'] = int(boot_recovery_remaining)
    if OWNER_ID:
        try:
            finance_active_chats.add(int(OWNER_ID))
        except Exception:
            pass
    log_info(f'Данные загружены из SQLite ({DB_FILE}). Версия бота: {VERSION}')
    runtime_set_phase('boot_webhook', 'устанавливаю Telegram webhook')
    set_webhook()
    try:
        start_memory_runtime_schedulers()
    except Exception as e:
        log_error(f'memory guard start: {e}')
    if boot_recovery_remaining > 0:
        _v211_ensure_web_server_started('boot-recovery-pending')
        runtime_set_phase('boot_recovery_background', f'осталось {boot_recovery_remaining}; webhook временно 503')
        try:
            RECOVERY_TASK_POOL.submit_unique('boot-task-recovery', runtime_continue_boot_recovery_background)
        except Exception:
            runtime_continue_boot_recovery_background()
    else:
        _v211_deploy_handoff_catchup(bool(db_restored))
        _remaining_after_handoff = len(_runtime_pending_recovery_rows()) if mega_tasks_active() else 0
        with _RUNTIME_LOCK:
            _RUNTIME_STATE['task_recovery_remaining'] = int(_remaining_after_handoff)
        if _remaining_after_handoff:
            runtime_set_phase('boot_recovery_background', f'после handoff осталось {_remaining_after_handoff}; webhook временно 503')
            try:
                RECOVERY_TASK_POOL.submit_unique('boot-task-recovery', runtime_continue_boot_recovery_background)
            except Exception:
                runtime_continue_boot_recovery_background()
        else:
            runtime_mark_ready('SQLite/config + final deploy delta catch-up; настройки и durable tasks проверены')
            try:
                journal_flush_to_mega(True)
            except Exception:
                pass
    try:
        if bool(globals().get('mega_contour_enabled_v234', lambda: False)()):
            if not MAINTENANCE_TASK_POOL.submit('archive-current-bot-source', archive_current_bot_source_to_mega):
                log_error('bot source archive maintenance queue full')
    except Exception as exc:
        log_error(f'bot source archive schedule: {exc}')
    if LOWRAM_ENABLED and (not db_restored) and (not RESTORE_GUARD_ACTIVE) and bool(globals().get('CONFIG_GUARD_BOOT_VERIFIED_V234', False)):

        def _seed_primary_db_snapshot():
            try:
                time.sleep(2.0)
                if bool(globals().get('telegram_durable_primary_v234', lambda: False)()):
                    telegram_upload_sqlite_snapshot_v234(force=True)
                elif bool(globals().get('mega_contour_enabled_v234', lambda: False)()):
                    mega_upload_latest_database_backup(force=True)
            except Exception as exc:
                log_error(f'LOWRAM initial DB snapshot: {exc}')
        try:
            MAINTENANCE_TASK_POOL.submit_unique('lowram-db-seed', _seed_primary_db_snapshot)
        except Exception:
            pass
    try:
        schedule_safe_failed_task_repairs(8.0, 20)
    except Exception as exc:
        log_error(f'safe failed task repair schedule: {exc}')
    if runtime_is_ready():
        _v211_notify_owner_ready_once()
    try:
        _v211_web_thread = _v211_ensure_web_server_started('main-loop')
        while _v211_web_thread.is_alive():
            _v211_web_thread.join(timeout=3600.0)
    finally:
        try:
            runtime_graceful_shutdown('APP_EXIT')
        except Exception as e:
            log_error(f'final graceful shutdown: {e}')
# v262
