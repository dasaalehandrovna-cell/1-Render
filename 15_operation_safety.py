# v262
_OPERATION_LOCK = threading.RLock()
_PROCESS_CENTER_LOCK = threading.RLock()
_EXPENSE_INBOX_LOCK = threading.RLock()
_FINANCE_INTEGRITY_LOCK = threading.RLock()
_FINANCE_CACHE_LOCK = threading.RLock()
_SECURITY_BREAKER_LOCK = threading.RLock()
_OPERATION_KEEP = 400
_OPERATION_RECENT_KEEP = 100
_FINANCE_INTEGRITY_KEEP = max(400, min(2000, int(os.getenv('FINANCE_INTEGRITY_KEEP', '800') or '800')))
_EXPENSE_DRAFT_KEEP = 300
_PROCESS_RECENT_KEEP = 80
_FINANCE_VIEW_CACHE = {}
_PROCESS_RUNTIME = {'active': {}, 'recent': deque(maxlen=_PROCESS_RECENT_KEEP)}
_SECURITY_BREAKERS = {}
_IPHONE_ENDPOINT_RUNTIME = defaultdict(deque)
_SAFETY_SCHEDULERS_STARTED = False
_SAFETY_SCHEDULERS_LOCK = threading.RLock()

def _root_settings() -> dict:
    return data.setdefault('_global_settings', {})

def _root_save(reason: str='settings') -> None:
    try:
        save_data(data, root_only=True)
    except TypeError:
        save_data(data)
    except Exception as exc:
        try:
            log_error(f'root save {reason}: {exc}')
        except Exception:
            pass
    try:
        if OWNER_ID:
            schedule_delta_backup(int(OWNER_ID), delay=0.8, reason=reason)
    except Exception:
        pass

def _root_save_coalesced(reason: str='runtime', delay: float=1.5) -> None:
    """Diagnostic ledgers may lag briefly; business data/durable MEGA tasks do not."""
    scheduler = globals().get('DELAYED_SCHEDULER')
    if scheduler is None:
        _root_save(reason)
        return
    scheduler.schedule('v143-root-ledger-save', max(0.2, float(delay)), _root_save, str(reason))
EXTERNAL_LOCAL_ONLY_KEY_V233 = 'render_telegram_only_v233'
EXTERNAL_LOCAL_ONLY_ENV_V233 = 'RENDER_TELEGRAM_ONLY'
_EXTERNAL_BLOCK_LOG_V233 = {}

def external_local_only_v233_enabled() -> bool:
    try:
        raw = str(os.getenv(EXTERNAL_LOCAL_ONLY_ENV_V233, '') or '').strip().casefold()
        if raw in {'1', 'true', 'yes', 'on', 'вкл'}:
            return True
    except Exception:
        pass
    try:
        prof = globals().get('storage_profile_v237_1')
        if callable(prof):
            return str(prof()) in {'render', 'render_telegram'}
    except Exception:
        pass
    try:
        return bool(_root_settings().get(EXTERNAL_LOCAL_ONLY_KEY_V233, False))
    except Exception:
        return False

def external_access_allowed_v233(category: str='other_http') -> bool:
    """v246 Render-only means storage-only isolation, not an offline bot.

    Normal Telegram bot traffic, Google, FX and other user features stay available.
    Only the two remote backup contours (MEGA and Telegram backup-channel) are blocked.
    The tiny MEGA storage-control beacon is a control-plane exception so the next deploy
    can know which mode was selected before it restarted.
    """
    cat = str(category or 'other_http').strip().casefold()
    if cat in {'telegram', 'local', 'sqlite', 'memory', 'render_inbound', 'mega_control'}:
        return True
    if bool(globals().get('_V240_RECOVERY_AUTHORITY_ACTIVE', False)) and cat in {'mega', 'mega_put', 'mega_get', 'mega_critical', 'mega_backup', 'telegram_backup', 'telegram_durable'}:
        return True
    if not external_local_only_v233_enabled():
        return True
    return cat not in {'mega', 'mega_put', 'mega_get', 'mega_critical', 'mega_backup', 'telegram_backup', 'telegram_durable', 'backup_channel'}

def external_blocked_v233(category: str='other_http') -> bool:
    return not external_access_allowed_v233(category)

def _external_pause_schedulers_v233() -> None:
    """v246: pause only remote storage schedulers in Render-only mode."""
    sched = globals().get('DELAYED_SCHEDULER')
    if sched is None:
        return
    for key in ('telegram-delta-batch-v234', 'telegram-full-quiet-v234', 'telegram-full-max-v234', 'telegram-task-startup-recovery-v234', 'telegram-full-v238', 'mega-delta-batch-v90', 'mega-task-startup-recovery', 'mega-task-safe-failed-repair', 'mega-global-quiet-v90', 'mega-global-max-v90', 'mega-global-retry-v90', 'mega-global-user-idle-v190', 'mega-node-housekeeping-v211', 'mega-root-reseed-v190'):
        try:
            sched.cancel(key)
        except Exception:
            pass

def _external_resume_services_v233() -> None:

    def _job():
        try:
            flush = globals().get('constitution_flush_local_only_ledger_v233')
            if callable(flush):
                flush()
        except Exception as exc:
            try:
                log_error(f'external resume ledger v233: {exc}')
            except Exception:
                pass
        try:
            cfg = globals().get('config_guard_sync_remote_v234')
            if callable(cfg):
                cfg()
        except Exception as exc:
            try:
                log_error(f'external resume config v234: {exc}')
            except Exception:
                pass
        try:
            fn = globals().get('schedule_delta_backup')
            if callable(fn) and OWNER_ID:
                fn(int(OWNER_ID), delay=1.0, reason='external_resume_v233')
        except Exception:
            pass
        try:
            fn = globals().get('schedule_mega_task_recovery')
            if callable(fn):
                fn(2.0)
        except Exception:
            pass
        try:
            fn = globals().get('schedule_safe_failed_task_repairs')
            if callable(fn):
                fn(4.0)
        except Exception:
            pass
        try:
            fn = globals().get('usd_rate_cached')
            pool = globals().get('GENERAL_TASK_POOL')
            if callable(fn) and pool is not None:
                pool.submit('usd-rate-resume-v233', fn, True)
        except Exception:
            pass
        try:
            sched = globals().get('DELAYED_SCHEDULER')
            tick = globals().get('_v167_google_scheduler_tick')
            if sched is not None and callable(tick):
                sched.schedule('google-thuwed-scheduler', 3.0, tick)
        except Exception:
            pass
        try:
            if OWNER_ID:
                bot_journal('external_resume_sync_v233', int(OWNER_ID), 'ledger_flush=attempted; backups/recovery/resume=scheduled')
        except Exception:
            pass
    pool = globals().get('GENERAL_TASK_POOL')
    try:
        if pool is not None and pool.submit('external-resume-v233', _job):
            return
    except Exception:
        pass
    _job()

def set_external_local_only_v233(enabled: bool) -> bool:
    profile_setter = globals().get('set_storage_profile_v237_1')
    if callable(profile_setter):
        target = 'render' if bool(enabled) else 'telegram_durable'
        actual = str(profile_setter(target) or '')
        return actual == 'render'
    enabled = bool(enabled)
    previous = external_local_only_v233_enabled()
    try:
        _root_settings()[EXTERNAL_LOCAL_ONLY_KEY_V233] = enabled
        save_data(data, root_only=True)
    except Exception as exc:
        try:
            log_error(f'external local-only save v233: {exc}')
        except Exception:
            pass
    if enabled:
        _external_pause_schedulers_v233()
    else:
        _external_resume_services_v233()
    try:
        bot_journal('external_local_only_toggle_v233', int(OWNER_ID or 0) or None, f'enabled={int(enabled)}; previous={int(bool(previous))}; telegram=allowed')
    except Exception:
        pass
    return enabled

def external_block_log_v233(category: str, operation: str='') -> None:
    key = f"{str(category or '')}:{str(operation or '')[:80]}"
    now_m = time.monotonic()
    try:
        if now_m - float(_EXTERNAL_BLOCK_LOG_V233.get(key, 0.0) or 0.0) < 60.0:
            return
        _EXTERNAL_BLOCK_LOG_V233[key] = now_m
        bot_journal('external_call_blocked_v233', None, f'category={category}; operation={str(operation)[:160]}', 'INFO')
    except Exception:
        pass

def safety_profile_mode() -> str:
    mode = str(_root_settings().get('safety_profile_v141') or 'old').strip().lower()
    return 'new' if mode == 'new' else 'old'

def safety_profile_new_enabled() -> bool:
    return safety_profile_mode() == 'new'

def set_safety_profile_mode(mode: str) -> str:
    mode = 'new' if str(mode).strip().lower() == 'new' else 'old'
    _root_settings()['safety_profile_v141'] = mode
    _root_save('safety_profile')
    try:
        bot_journal('safety_profile_changed', OWNER_ID, f'mode={mode}')
    except Exception:
        pass
    return mode

def toggle_safety_profile_mode() -> str:
    return set_safety_profile_mode('old' if safety_profile_new_enabled() else 'new')

def safety_profile_label() -> str:
    return '🛡 Защита: ПО-НОВОМУ' if safety_profile_new_enabled() else '🛡 Защита: ПО-СТАРОМУ'

def safety_profile_text() -> str:
    mode = safety_profile_mode()
    return f"🛡 ПРОФИЛЬ ЗАЩИТЫ\n\nСейчас: {('ПО-НОВОМУ' if mode == 'new' else 'ПО-СТАРОМУ')}\n\nПо-старому: прежние timeout, ссылка iPhone и текущие проверки прав.\n\nПо-новому:\n• короткие timeout + повтор с увеличением задержки;\n• circuit breaker для нестабильных внешних сервисов;\n• защита iPhone-ссылки от частых и повторных запросов;\n• дополнительная проверка прав для опасных действий;\n• технические сомнения не пугают пользователя, а попадают в центр проверки."

def _breaker_state(name: str) -> dict:
    with _SECURITY_BREAKER_LOCK:
        return _SECURITY_BREAKERS.setdefault(str(name), {'failures': 0, 'opened_until': 0.0, 'last_error': '', 'last_ok': 0.0})

def guarded_external_call(name: str, func, *args, attempts: int=2, base_delay: float=0.35, **kwargs):
    """Новый режим: retry + circuit breaker. Старый режим вызывает функцию напрямую."""
    if not safety_profile_new_enabled():
        return func(*args, **kwargs)
    state = _breaker_state(name)
    now_m = time.monotonic()
    if float(state.get('opened_until') or 0) > now_m:
        raise RuntimeError(f'circuit_open:{name}')
    last_exc = None
    for attempt in range(max(1, int(attempts))):
        try:
            result = func(*args, **kwargs)
            with _SECURITY_BREAKER_LOCK:
                state['failures'] = 0
                state['opened_until'] = 0.0
                state['last_error'] = ''
                state['last_ok'] = time.time()
            return result
        except Exception as exc:
            last_exc = exc
            with _SECURITY_BREAKER_LOCK:
                state['failures'] = int(state.get('failures') or 0) + 1
                state['last_error'] = str(exc)[:300]
                if int(state['failures']) >= 4:
                    state['opened_until'] = time.monotonic() + min(180.0, 15.0 * int(state['failures']))
            if attempt + 1 < max(1, int(attempts)):
                time.sleep(min(3.0, float(base_delay) * 2 ** attempt))
    raise last_exc or RuntimeError(f'external_call_failed:{name}')
_SENSITIVE_ACTION_PREFIXES = ('mega_', 'restore_', 'additional_owners', 'addown:', 'expense_shortcut_regenerate', 'safety_profile', 'security_roles', 'integrity_', 'problem_tasks', 'owners', 'reset', 'fw_probe_all')
_SECURITY_ROLE_PRESETS = {'standard': ('Обычный', {'view', 'finance_input'}), 'view_only': ('Только просмотр', {'view', 'export'}), 'expense_input': ('Только ввод расходов', {'view', 'finance_input'}), 'finance_admin': ('Администратор финансов', {'view', 'finance_input', 'finance_manage', 'export'}), 'forward_manager': ('Управление пересылкой', {'view', 'forward_manage'}), 'secret_manager': ('Управление секретом', {'view', 'secret_manage'}), 'reminder_manager': ('Управление напоминаниями', {'view', 'reminder_manage'})}

def _security_roles_root() -> dict:
    root = _root_settings().setdefault('security_roles_v141', {})
    root.setdefault('users', {})
    return root

def _v177_legacy_0105_security_role_for_user(user_id: int | None) -> str:
    try:
        uid = int(user_id or 0)
    except Exception:
        uid = 0
    if uid and OWNER_ID and (uid == int(OWNER_ID)):
        return 'owner'
    try:
        if uid in get_additional_owner_ids():
            return 'owner'
    except Exception:
        pass
    role = str((_security_roles_root().get('users') or {}).get(str(uid)) or 'standard')
    return role if role in _SECURITY_ROLE_PRESETS else 'standard'
try:
    _v177_legacy_0105_security_role_for_user.__name__ = 'security_role_for_user'
except Exception:
    pass

def security_role_label(role: str) -> str:
    if role == 'owner':
        return 'Владелец'
    return _SECURITY_ROLE_PRESETS.get(str(role), _SECURITY_ROLE_PRESETS['standard'])[0]

def _v177_legacy_0106_security_set_role(user_id: int, role: str) -> str:
    uid = int(user_id)
    role = str(role or 'standard')
    if role not in _SECURITY_ROLE_PRESETS:
        role = 'standard'
    _security_roles_root().setdefault('users', {})[str(uid)] = role
    _root_save('security_role')
    try:
        bot_journal('security_role_changed', OWNER_ID, f'user={uid}; role={role}')
    except Exception:
        pass
    return role
try:
    _v177_legacy_0106_security_set_role.__name__ = 'security_set_role'
except Exception:
    pass

def _v177_legacy_0107_security_known_users() -> list[dict]:
    merged = {}
    try:
        chats = data.get('chats') or {} if isinstance(data, dict) else {}
        for cid_raw, store in chats.items():
            if not isinstance(store, dict):
                continue
            for row in (store.get('known_users') or {}).values():
                if not isinstance(row, dict):
                    continue
                try:
                    uid = int(row.get('id') or 0)
                except Exception:
                    continue
                if not uid or bool(row.get('is_bot')):
                    continue
                old = merged.get(uid) or {}
                if float(row.get('last_seen_ts') or 0) >= float(old.get('last_seen_ts') or 0):
                    merged[uid] = dict(row)
            try:
                cid = int(cid_raw)
                info = store.get('info') or {}
                if cid > 0 and cid not in merged:
                    merged[cid] = {'id': cid, 'first_name': info.get('first_name') or info.get('title') or '', 'username': info.get('username'), 'last_seen_ts': 0}
            except Exception:
                pass
    except Exception:
        pass
    try:
        owner = int(OWNER_ID or 0)
        if owner:
            merged.setdefault(owner, {'id': owner, 'first_name': 'Владелец', 'last_seen_ts': 10 ** 20})
        for uid in get_additional_owner_ids():
            merged.setdefault(int(uid), {'id': int(uid), 'first_name': 'Доп. владелец', 'last_seen_ts': 10 ** 19})
    except Exception:
        pass
    rows = list(merged.values())
    rows.sort(key=lambda r: (float(r.get('last_seen_ts') or 0), int(r.get('id') or 0)), reverse=True)
    return rows
try:
    _v177_legacy_0107_security_known_users.__name__ = 'security_known_users'
except Exception:
    pass

def security_user_display(user_id: int) -> str:
    uid = int(user_id)
    row = next((r for r in security_known_users() if int(r.get('id') or 0) == uid), {})
    name = ' '.join((x for x in (str(row.get('first_name') or '').strip(), str(row.get('last_name') or '').strip()) if x)).strip()
    username = str(row.get('username') or '').strip().lstrip('@')
    return name or ('@' + username if username else str(uid))

def _security_callback_capability(action: str) -> str:
    raw = str(action or '')
    resolved = raw.split(':', 2)[2] if raw.startswith('d:') and raw.count(':') >= 2 else raw
    low = resolved.lower()
    if low.startswith('rem:') or low.startswith('reminder'):
        return 'reminder_manage'
    if low.startswith(('fw_', 'fw:', 'forward_', 'forward:', 'fwd_')):
        return 'forward_manage'
    if low.startswith(('secret', 'sec_', 'total_secret', 'hidden_secret')):
        return 'secret_manage'
    if low.startswith(('expense_draft_', 'expense_inbox', 'expense_evening')):
        return 'finance_input'
    if any((token in low for token in ('delete', 'edit', 'izm', 'balance', 'category', 'cat_order', 'usd_tx', 'gomonk'))):
        return 'finance_manage'
    if any((token in low for token in ('csv', 'excel', 'xlsx', 'google', 'export', 'download'))):
        return 'export'
    return 'view'

def _v177_legacy_0108_security_user_allowed(user_id: int | None, capability: str) -> bool:
    role = security_role_for_user(user_id)
    if role == 'owner':
        return True
    allowed = _SECURITY_ROLE_PRESETS.get(role, _SECURITY_ROLE_PRESETS['standard'])[1]
    return str(capability or 'view') in allowed
try:
    _v177_legacy_0108_security_user_allowed.__name__ = 'security_user_allowed'
except Exception:
    pass

def _v177_legacy_0110_safety_permission_allowed(user_id: int | None, chat_id: int | None, action: str) -> bool:
    """Новый профиль усиливает только опасные действия; обычная работа чатов не ломается."""
    if not safety_profile_new_enabled():
        return True
    try:
        uid = int(user_id or 0)
    except Exception:
        uid = 0
    if uid and OWNER_ID and (uid == int(OWNER_ID)):
        return True
    try:
        if uid and uid in {int(x) for x in get_additional_owner_ids()}:
            return True
    except Exception:
        pass
    action = str(action or '')
    normalized = action.split(':', 2)[2] if action.startswith('d:') and action.count(':') >= 2 else action
    normalized = str(normalized or '').strip().lower()
    if normalized.startswith(tuple((str(x).lower() for x in _SENSITIVE_ACTION_PREFIXES))):
        return False
    return security_user_allowed(uid, _security_callback_capability(normalized))
try:
    _v177_legacy_0110_safety_permission_allowed.__name__ = 'safety_permission_allowed'
except Exception:
    pass

def _operation_root() -> dict:
    root = _root_settings().setdefault('operation_ledger_v141', {})
    root.setdefault('items', {})
    root.setdefault('order', [])
    root.setdefault('next_seq', 1)
    return root

def _operation_trim_locked(root: dict) -> None:
    order = list(root.get('order') or [])
    items = root.get('items') or {}
    if len(order) <= _OPERATION_KEEP:
        return
    keep = order[-_OPERATION_KEEP:]
    root['order'] = keep
    keep_set = set(keep)
    for key in list(items.keys()):
        if key not in keep_set:
            items.pop(key, None)

def _compact_operation_payload(payload: dict | None) -> dict:
    src = payload or {}
    if not isinstance(src, dict):
        return {'value': str(src)[:500]}
    out = {}
    for key, value in src.items():
        k = str(key)[:80]
        if k in {'expected_effects'} and isinstance(value, dict):
            out[k] = {'source_finance': bool(value.get('source_finance')), 'source_secret': bool(value.get('source_secret')), 'forward_targets': len(value.get('forward_targets') or []), 'record_edits': len(value.get('record_edits') or []), 'reminder_edits': len(value.get('reminder_edits') or [])}
        elif isinstance(value, (str, int, float, bool)) or value is None:
            out[k] = value if not isinstance(value, str) else value[:500]
        elif isinstance(value, (list, tuple)):
            out[k] = list(value)[:20]
        elif isinstance(value, dict):
            out[k] = {str(a)[:60]: b[:300] if isinstance(b, str) else b for a, b in list(value.items())[:20]}
        if len(out) >= 24:
            break
    return out

def operation_begin(kind: str, chat_id=None, target: str='', payload: dict | None=None, operation_id: str | None=None, critical: bool=True) -> str:
    with _OPERATION_LOCK:
        root = _operation_root()
        if operation_id:
            op_id = str(operation_id)
        else:
            seq = int(root.get('next_seq') or 1)
            root['next_seq'] = seq + 1
            op_id = f'op{seq}_{int(time.time() * 1000)}'
        existing = (root.get('items') or {}).get(op_id)
        if isinstance(existing, dict):
            return op_id
        row = {'id': op_id, 'kind': str(kind or 'operation'), 'chat_id': int(chat_id) if str(chat_id or '').lstrip('-').isdigit() else chat_id, 'target': str(target or ''), 'critical': bool(critical), 'status': 'created', 'level': 'green', 'created_at': now_local().isoformat(timespec='microseconds'), 'updated_at': now_local().isoformat(timespec='microseconds'), 'steps': [{'name': 'created', 'at': now_local().isoformat(timespec='microseconds')}], 'payload': _compact_operation_payload(payload), 'error': ''}
        root.setdefault('items', {})[op_id] = row
        root.setdefault('order', []).append(op_id)
        _operation_trim_locked(root)
    process_register(op_id, row['kind'], row.get('chat_id'), phase='создано', cancellable=False)
    _root_save_coalesced('operation_begin')
    return op_id

def operation_step(op_id: str, step: str, details: str='', persist: bool=True) -> bool:
    with _OPERATION_LOCK:
        row = (_operation_root().get('items') or {}).get(str(op_id))
        if not isinstance(row, dict):
            return False
        row['status'] = str(step or 'running')
        row['updated_at'] = now_local().isoformat(timespec='microseconds')
        row.setdefault('steps', []).append({'name': str(step or 'running'), 'details': str(details or '')[:500], 'at': now_local().isoformat(timespec='microseconds')})
        if len(row['steps']) > 12:
            row['steps'] = row['steps'][-12:]
    process_update(str(op_id), phase=str(step or 'running'), details=details)
    if persist:
        _root_save_coalesced('operation_step')
    return True

def operation_complete(op_id: str, details: str='') -> bool:
    with _OPERATION_LOCK:
        row = (_operation_root().get('items') or {}).get(str(op_id))
        if not isinstance(row, dict):
            return False
        row['status'] = 'completed'
        row['level'] = 'green'
        row['completed_at'] = now_local().isoformat(timespec='microseconds')
        row['updated_at'] = row['completed_at']
        row['error'] = ''
        row.setdefault('steps', []).append({'name': 'completed', 'details': str(details or '')[:500], 'at': row['completed_at']})
    process_finish(str(op_id), ok=True, details=details)
    _root_save_coalesced('operation_complete')
    return True

def operation_review(op_id: str, reason: str='') -> bool:
    with _OPERATION_LOCK:
        row = (_operation_root().get('items') or {}).get(str(op_id))
        if not isinstance(row, dict):
            return False
        row['status'] = 'needs_review'
        row['level'] = 'yellow'
        row['error'] = str(reason or '')[:1000]
        row['updated_at'] = now_local().isoformat(timespec='microseconds')
        row.setdefault('steps', []).append({'name': 'needs_review', 'details': row['error'], 'at': row['updated_at']})
    process_finish(str(op_id), ok=None, details=reason)
    _root_save_coalesced('operation_review')
    return True

def operation_fail(op_id: str, error: str='') -> bool:
    with _OPERATION_LOCK:
        row = (_operation_root().get('items') or {}).get(str(op_id))
        if not isinstance(row, dict):
            return False
        row['status'] = 'failed'
        row['level'] = 'red'
        row['error'] = str(error or '')[:1000]
        row['updated_at'] = now_local().isoformat(timespec='microseconds')
        row.setdefault('steps', []).append({'name': 'failed', 'details': row['error'], 'at': row['updated_at']})
    process_finish(str(op_id), ok=False, details=error)
    _root_save_coalesced('operation_fail')
    return True

def operation_for_update(update_id) -> str:
    return f'tg:{str(update_id)}'

def operation_begin_durable(update_id, task_payload: dict) -> str:
    payload = task_payload or {}
    return operation_begin('telegram_update', payload.get('chat_id'), target=str(payload.get('reason') or payload.get('update_type') or ''), payload={'update_id': payload.get('update_id'), 'expected_effects': payload.get('expected_effects') or {}}, operation_id=operation_for_update(update_id), critical=True)

def operation_recent(limit: int=30, levels: set[str] | None=None) -> list[dict]:
    with _OPERATION_LOCK:
        root = _operation_root()
        items = root.get('items') or {}
        order = list(root.get('order') or [])
        rows = []
        for op_id in reversed(order):
            row = items.get(op_id)
            if not isinstance(row, dict):
                continue
            if levels and str(row.get('level')) not in levels:
                continue
            rows.append(copy.deepcopy(row))
            if len(rows) >= max(1, int(limit)):
                break
        return rows

def operation_problem_count() -> tuple[int, int]:
    rows = operation_recent(500, {'yellow', 'red'})
    return (sum((1 for r in rows if r.get('level') == 'yellow')), sum((1 for r in rows if r.get('level') == 'red')))

def finance_currency_context(chat_id: int, currency: str | None=None) -> dict:
    """Одна оболочка ARS/USD без смешивания режима ARS+эквивалент с USD-контуром."""
    chat_id = int(chat_id)
    store = get_chat_store(chat_id)
    settings = store.setdefault('settings', {})
    requested = str(currency or '').strip().lower()
    if requested in {'usd', 'dollar', 'доллар'}:
        ledger = 'usd'
    elif requested in {'ars', 'peso', 'песо', 'ars_usd'}:
        ledger = 'ars'
    else:
        mode = str(settings.get('currency_mode') or 'ars').strip().lower()
        ledger = 'usd' if mode == 'usd' else 'ars'
    current = _ensure_currency_ledgers(store)
    prefix = ledger
    records_key = 'records' if current == ledger else f'{prefix}_records'
    daily_key = 'daily_records' if current == ledger else f'{prefix}_daily_records'
    return {'chat_id': chat_id, 'store': store, 'currency': ledger, 'symbol': 'USD' if ledger == 'usd' else 'ARS', 'records_key': records_key, 'daily_key': daily_key, 'balance_key': 'balance' if current == ledger else f'{prefix}_balance', 'next_id_key': 'next_id' if current == ledger else f'{prefix}_next_id'}

def finance_currency_records(chat_id: int, currency: str | None=None) -> list[dict]:
    ctx = finance_currency_context(chat_id, currency)
    return list(ctx['store'].get(ctx['records_key'], []) or [])

def finance_currency_daily(chat_id: int, currency: str | None=None) -> dict:
    ctx = finance_currency_context(chat_id, currency)
    return ctx['store'].get(ctx['daily_key'], {}) or {}

def process_register(process_id: str, label: str, chat_id=None, phase: str='ожидает', cancellable: bool=False, meta: dict | None=None):
    with _PROCESS_CENTER_LOCK:
        _PROCESS_RUNTIME['active'][str(process_id)] = {'id': str(process_id), 'label': str(label or process_id), 'chat_id': chat_id, 'phase': str(phase or ''), 'started_mono': time.monotonic(), 'started_at': now_local().isoformat(timespec='seconds'), 'details': '', 'cancellable': bool(cancellable), 'meta': dict(meta or {})}

def process_update(process_id: str, phase: str | None=None, details: str=''):
    with _PROCESS_CENTER_LOCK:
        row = _PROCESS_RUNTIME['active'].get(str(process_id))
        if not row:
            return False
        if phase is not None:
            row['phase'] = str(phase)
        if details:
            row['details'] = str(details)[:500]
        return True

def process_finish(process_id: str, ok: bool | None=True, details: str=''):
    with _PROCESS_CENTER_LOCK:
        row = _PROCESS_RUNTIME['active'].pop(str(process_id), None)
        if not row:
            return False
        row['finished_at'] = now_local().isoformat(timespec='seconds')
        row['elapsed'] = max(0.0, time.monotonic() - float(row.get('started_mono') or time.monotonic()))
        row['result'] = 'ok' if ok is True else 'error' if ok is False else 'review'
        row['details'] = str(details or row.get('details') or '')[:500]
        _PROCESS_RUNTIME['recent'].appendleft(row)
        return True

def _pool_process_rows() -> list[dict]:
    rows = []
    for name in ('UI_TASK_POOL', 'CONTENT_TASK_POOL', 'FINANCE_TASK_POOL', 'FIN_FORWARD_TASK_POOL', 'FORWARD_TASK_POOL', 'EXPORT_TASK_POOL', 'BACKUP_TASK_POOL', 'DELTA_TASK_POOL', 'RECOVERY_TASK_POOL', 'REMINDER_TASK_POOL', 'GENERAL_TASK_POOL', 'MAINTENANCE_TASK_POOL'):
        pool = globals().get(name)
        if pool is None:
            continue
        try:
            stat = pool.stats()
        except Exception:
            continue
        pending = int(stat.get('pending') or 0)
        active = int(stat.get('active') or 0)
        if pending or active:
            rows.append({'id': f'pool:{name}', 'label': name.replace('_TASK_POOL', '').replace('_', ' ').title(), 'phase': f'активно {active}, в очереди {pending}', 'elapsed': 0.0, 'chat_id': None})
    return rows

def process_center_rows(viewer_chat_id: int | None=None) -> list[dict]:
    with _PROCESS_CENTER_LOCK:
        rows = [copy.deepcopy(x) for x in _PROCESS_RUNTIME['active'].values()]
    try:
        busy = _file_job_busy_info()
        if busy:
            rows.append({'id': 'legacy-file-job', 'label': str(busy.get('label') or busy.get('kind') or 'Файл'), 'phase': str(busy.get('phase') or 'выполняется'), 'elapsed': float(busy.get('elapsed') or 0), 'chat_id': busy.get('chat_id')})
    except Exception:
        pass
    rows.extend(_pool_process_rows())
    if viewer_chat_id is not None and (not is_owner_chat(int(viewer_chat_id))):
        filtered = []
        for row in rows:
            cid = row.get('chat_id')
            if cid in {None, int(viewer_chat_id)}:
                filtered.append(row)
        rows = filtered
    rows.sort(key=lambda r: (str(r.get('label') or ''), str(r.get('id') or '')))
    return rows

def build_process_center_text(viewer_chat_id: int) -> str:
    rows = process_center_rows(viewer_chat_id)
    yellow, red = operation_problem_count()
    lines = ['⚙️ ПРОЦЕССЫ БОТА', '', f'Активных: {len(rows)}', f'Требуют проверки: {yellow}', f'Ошибок: {red}', '']
    if not rows:
        lines.append('Сейчас активных процессов нет.')
    for idx, row in enumerate(rows[:30], 1):
        elapsed = float(row.get('elapsed') or 0)
        if not elapsed and row.get('started_mono'):
            elapsed = max(0.0, time.monotonic() - float(row.get('started_mono')))
        lines.append(f"{idx}. {row.get('label')} — {row.get('phase') or 'выполняется'} · {int(elapsed)}с")
    if len(rows) > 30:
        lines.append(f'…ещё {len(rows) - 30}')
    return '\n'.join(lines)

def build_problem_tasks_text() -> str:
    rows = operation_recent(30, {'yellow', 'red'})
    lines = ['🧯 ПРОБЛЕМНЫЕ ЗАДАЧИ', '']
    if not rows:
        return '\n'.join(lines + ['Нет задач, требующих проверки.'])
    for row in rows:
        icon = '🔴' if row.get('level') == 'red' else '🟡'
        lines.append(f"{icon} {row.get('id')} · {row.get('kind')}\n{str(row.get('error') or row.get('status') or '')[:300]}")
    return '\n\n'.join(lines)
WINDOW_DEFINITION_REGISTRY = {}
for _wk, _wc in list((globals().get('WINDOW_MARKER_CONSTANTS') or {}).items()):
    WINDOW_DEFINITION_REGISTRY[str(_wk)] = {'action': str(_wk), 'marker': str(_wc), 'group': str(_wc)[:1], 'timer': str(_wc) in set(globals().get('WINDOW_MARKER_HOURGLASS_CODES') or set()) | set(globals().get('WINDOW_MARKER_CLOCK_CODES') or set())}

def window_definition_for_action(action: str) -> dict:
    raw = str(action or '')
    normalized = _normalize_window_action(raw) if '_normalize_window_action' in globals() else raw
    best = None
    try:
        code = _window_marker_code(normalized)
    except Exception:
        code = ''
    for key, row in WINDOW_DEFINITION_REGISTRY.items():
        if str(row.get('marker')) == str(code):
            best = dict(row)
            break
    return best or {'action': normalized, 'marker': code or '', 'group': str(code)[:1] if code else 'Ф', 'timer': False}
_ORIGINAL_REGISTER_OPEN_WINDOW = _v177_legacy_0041_register_open_window
if callable(_ORIGINAL_REGISTER_OPEN_WINDOW):

    def register_open_window(chat_id: int, message_id: int, window_type: str, code: str='', day_key: str | None=None, params: dict | None=None):
        params2 = dict(params or {})
        definition = window_definition_for_action(code or window_type)
        params2.setdefault('window_definition', definition)
        params2.setdefault('parent_window', params2.get('parent') or '')
        params2.setdefault('timer_enabled', bool(definition.get('timer')))
        return _ORIGINAL_REGISTER_OPEN_WINDOW(chat_id, message_id, window_type, code=code, day_key=day_key, params=params2)

def window_registry_summary() -> dict:
    total = len(WINDOW_DEFINITION_REGISTRY)
    timer = sum((1 for row in WINDOW_DEFINITION_REGISTRY.values() if row.get('timer')))
    missing = 0
    try:
        report = audit_window_marker_registry()
        missing = int((report or {}).get('missing') or 0) if isinstance(report, dict) else 0
    except Exception:
        pass
    return {'total': total, 'timer': timer, 'missing': missing}

def _expense_inbox_root() -> dict:
    root = _root_settings().setdefault('expense_inbox_v141', {})
    root.setdefault('next_id', 1)
    root.setdefault('items', {})
    root.setdefault('evening_enabled', True)
    root.setdefault('evening_hour', 21)
    root.setdefault('evening_last_date', '')
    root.setdefault('quick_message_buttons_enabled', True)
    root.setdefault('recent_event_migration_v142_at', '')
    return root

def expense_quick_buttons_enabled() -> bool:
    return bool(_expense_inbox_root().get('quick_message_buttons_enabled', True))

def expense_quick_buttons_label() -> str:
    return '📱 Отметка: С КНОПКАМИ' if expense_quick_buttons_enabled() else '📱 Отметка: БЕЗ КНОПОК'

def toggle_expense_quick_buttons() -> bool:
    root = _expense_inbox_root()
    root['quick_message_buttons_enabled'] = not bool(root.get('quick_message_buttons_enabled', True))
    _root_save('expense_quick_buttons_toggle')
    return bool(root['quick_message_buttons_enabled'])

def _expense_event_dt(row: dict):
    try:
        value = str((row or {}).get('created_at') or '')
        dt = datetime.fromisoformat(value)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=now_local().tzinfo)
        return dt
    except Exception:
        try:
            return datetime.fromtimestamp(float((row or {}).get('created_ts') or 0), tz=now_local().tzinfo)
        except Exception:
            return None

def _v177_legacy_0112_migrate_recent_expense_shortcut_events(days: int=2, refresh_messages: bool=False) -> dict:
    """Подхватывает быстрые отметки v140/v141 за последние 48 часов."""
    cfg_fn = globals().get('expense_shortcut_config')
    if not callable(cfg_fn):
        return {'imported': 0, 'updated': 0, 'seen': 0}
    try:
        shortcut = cfg_fn(False) or {}
    except Exception:
        shortcut = {}
    cutoff = now_local() - timedelta(days=max(1, int(days or 2)))
    imported = updated = seen = 0
    duplicate = too_old = missing_message_id = refresh_failed = 0
    total_events = len(list(shortcut.get('events') or []))
    for event in list(shortcut.get('events') or []):
        if not isinstance(event, dict) or not event.get('id'):
            continue
        dt = _expense_event_dt(event)
        if dt is None or dt < cutoff:
            too_old += 1
            continue
        seen += 1
        event_id = str(event.get('id'))
        target = int(event.get('target_chat_id') or shortcut.get('target_chat_id') or OWNER_ID or 0)
        before = None
        with _EXPENSE_INBOX_LOCK:
            for existing in (_expense_inbox_root().get('items') or {}).values():
                if str((existing or {}).get('source_event_id') or '') == event_id:
                    before = existing
                    break
        draft = expense_draft_for_event(event_id, target, dt.isoformat(timespec='seconds'))
        if before is None:
            imported += 1
        else:
            duplicate += 1
        mid = int(event.get('telegram_message_id') or 0)
        if not mid:
            missing_message_id += 1
        if mid and int((draft or {}).get('telegram_message_id') or 0) != mid:
            with _EXPENSE_INBOX_LOCK:
                draft['telegram_message_id'] = mid
        if refresh_messages and mid and target:
            try:
                text_fn = globals().get('expense_compact_message_text')
                text = text_fn(dt.isoformat(timespec='seconds')) if callable(text_fn) else f"💸 iPhone · {dt.strftime('%H:%M')}"
                markup = expense_draft_message_keyboard(int(draft.get('id') or 0), target)
                bot.edit_message_text(text, chat_id=target, message_id=mid, reply_markup=markup)
                updated += 1
            except Exception as exc:
                if 'message is not modified' not in str(exc).lower():
                    try:
                        bot.edit_message_reply_markup(chat_id=target, message_id=mid, reply_markup=expense_draft_message_keyboard(int(draft.get('id') or 0), target))
                        updated += 1
                    except Exception:
                        refresh_failed += 1
    root = _expense_inbox_root()
    root['recent_event_migration_v142_at'] = now_local().isoformat(timespec='seconds')
    _root_save('expense_recent_event_migration')
    try:
        bot_journal('expense_recent_events_migrated', OWNER_ID, f'total={total_events} seen_48h={seen} imported={imported} existing={duplicate} updated={updated} too_old_or_bad_date={too_old} missing_message_id={missing_message_id} refresh_failed={refresh_failed}')
    except Exception:
        pass
    return {'imported': imported, 'updated': updated, 'seen': seen, 'existing': duplicate, 'too_old': too_old, 'missing_message_id': missing_message_id, 'refresh_failed': refresh_failed}
try:
    _v177_legacy_0112_migrate_recent_expense_shortcut_events.__name__ = 'migrate_recent_expense_shortcut_events'
except Exception:
    pass

def expense_draft_create(source: str, target_chat_id: int, created_at: str | None=None, source_event_id: str='') -> dict:
    with _EXPENSE_INBOX_LOCK:
        root = _expense_inbox_root()
        rid = int(root.get('next_id') or 1)
        root['next_id'] = rid + 1
        row = {'id': rid, 'status': 'open', 'source': str(source or 'manual'), 'source_event_id': str(source_event_id or ''), 'target_chat_id': int(target_chat_id), 'created_at': str(created_at or now_local().isoformat(timespec='seconds')), 'amount': None, 'category': '', 'note': '', 'telegram_message_id': 0}
        root.setdefault('items', {})[str(rid)] = row
        items = root.get('items') or {}
        if len(items) > _EXPENSE_DRAFT_KEEP:
            closed = sorted((x for x in items.values() if x.get('status') != 'open'), key=lambda x: str(x.get('created_at') or ''))
            for old in closed[:max(0, len(items) - _EXPENSE_DRAFT_KEEP)]:
                items.pop(str(old.get('id')), None)
    _root_save('expense_draft_create')
    return row

def expense_draft_for_event(event_id: str, target_chat_id: int, created_at: str | None=None) -> dict:
    with _EXPENSE_INBOX_LOCK:
        for row in (_expense_inbox_root().get('items') or {}).values():
            if str(row.get('source_event_id') or '') == str(event_id):
                return row
    return expense_draft_create('iphone', target_chat_id, created_at, source_event_id=event_id)

def expense_draft_set_message(draft_id: int, message_id: int):
    with _EXPENSE_INBOX_LOCK:
        row = (_expense_inbox_root().get('items') or {}).get(str(int(draft_id)))
        if row:
            row['telegram_message_id'] = int(message_id)
    _root_save('expense_draft_message')

def expense_draft_mark(draft_id: int, status: str, amount=None, category: str='', note: str='') -> bool:
    with _EXPENSE_INBOX_LOCK:
        row = (_expense_inbox_root().get('items') or {}).get(str(int(draft_id)))
        if not isinstance(row, dict):
            return False
        row['status'] = str(status)
        if amount is not None:
            row['amount'] = float(amount)
        if category:
            row['category'] = str(category)
        if note:
            row['note'] = str(note)
        row['updated_at'] = now_local().isoformat(timespec='seconds')
    _root_save('expense_draft_mark')
    return True

def expense_open_rows(limit: int=100) -> list[dict]:
    with _EXPENSE_INBOX_LOCK:
        rows = [copy.deepcopy(x) for x in (_expense_inbox_root().get('items') or {}).values() if str(x.get('status')) == 'open']
    rows.sort(key=lambda x: str(x.get('created_at') or ''), reverse=True)
    return rows[:max(1, int(limit))]

def expense_inbox_text() -> str:
    rows = expense_open_rows(100)
    lines = ['⚠️ НЕРАЗОБРАННЫЕ РАСХОДЫ', '', f'Открытых отметок: {len(rows)}', '']
    if not rows:
        lines.append('Все быстрые отметки разобраны.')
    for row in rows[:30]:
        dt = _reminder_parse_dt(row.get('created_at')) if '_reminder_parse_dt' in globals() else None
        label = dt.strftime('%d.%m %H:%M') if dt else str(row.get('created_at') or '')[:16]
        lines.append(f"{row.get('id')}. {label} · {row.get('source')}")
    return '\n'.join(lines)

def _today_finance_total() -> float:
    total = 0.0
    day = today_key()
    for _cid, store in (data.get('chats', {}) or {}).items():
        if not isinstance(store, dict):
            continue
        for rec in (store.get('daily_records', {}) or {}).get(day, []) or []:
            try:
                amount = float(rec.get('amount', 0) or 0)
                if amount < 0:
                    total += abs(amount)
            except Exception:
                pass
    return total

def evening_reconciliation_enabled() -> bool:
    return bool(_expense_inbox_root().get('evening_enabled', True))

def toggle_evening_reconciliation() -> bool:
    root = _expense_inbox_root()
    root['evening_enabled'] = not bool(root.get('evening_enabled', True))
    _root_save('evening_reconciliation_toggle')
    return bool(root['evening_enabled'])

def evening_reconciliation_label() -> str:
    root = _expense_inbox_root()
    return f"🌙 Сверка: {('✅ ВКЛ' if root.get('evening_enabled', True) else '⬜ ВЫКЛ')} · {int(root.get('evening_hour', 21)):02d}:00"

def send_evening_reconciliation(force: bool=False) -> bool:
    if not OWNER_ID:
        return False
    root = _expense_inbox_root()
    today = today_key()
    if not force and (not root.get('evening_enabled', True) or str(root.get('evening_last_date') or '') == today):
        return False
    rows = expense_open_rows(500)
    kb = types.InlineKeyboardMarkup(row_width=1)
    kb.row(IB('⚠️ Проверить незаполненные', callback_data='expense_inbox_open'))
    kb.row(IB('➕ Добавить забытый расход', callback_data='expense_shortcut_test'))
    kb.row(IB('✅ Всё внесено', callback_data='expense_evening_done'))
    text = f'🌙 ВЕЧЕРНЯЯ СВЕРКА РАСХОДОВ\n\nСегодня расходов внесено: {_today_finance_total():,.0f}\nНеразобранных отметок: {len(rows)}\n\nВсе расходы за сегодня внесены?'.replace(',', ' ')
    try:
        bot.send_message(int(OWNER_ID), text, reply_markup=kb)
        root['evening_last_date'] = today
        _root_save('evening_reconciliation_sent')
        return True
    except Exception as exc:
        try:
            log_error(f'evening reconciliation: {exc}')
        except Exception:
            pass
        return False

def _evening_reconciliation_tick():
    try:
        if runtime_is_ready() and evening_reconciliation_enabled():
            root = _expense_inbox_root()
            now_dt = now_local()
            if now_dt.hour >= int(root.get('evening_hour', 21)):
                send_evening_reconciliation(False)
    except Exception as exc:
        try:
            log_error(f'evening reconciliation: {exc}')
        except Exception:
            pass
    finally:
        try:
            DELAYED_SCHEDULER.schedule('expense-evening-reconcile', 45.0, _evening_reconciliation_tick)
        except Exception:
            pass

def _evening_reconciliation_loop():
    return _evening_reconciliation_tick()

def finance_cache_invalidate(chat_id: int | None=None, reason: str=''):
    with _FINANCE_CACHE_LOCK:
        if chat_id is None:
            _FINANCE_VIEW_CACHE.clear()
        else:
            cid = int(chat_id)
            for key in list(_FINANCE_VIEW_CACHE.keys()):
                if isinstance(key, tuple) and cid in key:
                    _FINANCE_VIEW_CACHE.pop(key, None)
    try:
        if reason:
            bot_journal('finance_cache_invalidated', chat_id, reason)
    except Exception:
        pass

def finance_cache_get(key, builder, ttl: float=20.0):
    now_m = time.monotonic()
    with _FINANCE_CACHE_LOCK:
        row = _FINANCE_VIEW_CACHE.get(key)
        if row and now_m - float(row.get('created') or 0) <= float(ttl):
            return copy.deepcopy(row.get('value'))
    value = builder()
    with _FINANCE_CACHE_LOCK:
        _FINANCE_VIEW_CACHE[key] = {'created': now_m, 'value': copy.deepcopy(value)}
        if len(_FINANCE_VIEW_CACHE) > 400:
            oldest = sorted(_FINANCE_VIEW_CACHE.items(), key=lambda x: float((x[1] or {}).get('created') or 0))[:100]
            for old_key, _ in oldest:
                _FINANCE_VIEW_CACHE.pop(old_key, None)
    return value
_ORIGINAL_MONTH_RECORDS_FOR_CHAT = globals().get('month_records_for_chat')
if callable(_ORIGINAL_MONTH_RECORDS_FOR_CHAT):

    def month_records_for_chat(store: dict, month_key: str) -> list[dict]:
        records = list((store or {}).get('records', []) or [])
        fingerprint = (id(store), str(month_key), len(records), int((store or {}).get('next_id', 0) or 0), str((records[-1] or {}).get('timestamp') or '') if records else '')
        return finance_cache_get(('month_records',) + fingerprint, lambda: _ORIGINAL_MONTH_RECORDS_FOR_CHAT(store, month_key), ttl=30.0)
_ORIGINAL_CALC_CATEGORIES_RANGE = globals().get('calc_categories_for_record_range')
if callable(_ORIGINAL_CALC_CATEGORIES_RANGE):

    def calc_categories_for_record_range(store: dict, start_day: str, start_rid: int, end_day: str, end_rid: int) -> dict:
        records = list((store or {}).get('records', []) or [])
        fingerprint = (id(store), str(start_day), int(start_rid), str(end_day), int(end_rid), len(records), int((store or {}).get('next_id', 0) or 0))
        return finance_cache_get(('cat_range',) + fingerprint, lambda: _ORIGINAL_CALC_CATEGORIES_RANGE(store, start_day, start_rid, end_day, end_rid), ttl=20.0)
_ORIGINAL_SCHEDULE_FULL_BACKUP_ONLY = globals().get('schedule_full_backup_only')
if callable(_ORIGINAL_SCHEDULE_FULL_BACKUP_ONLY):

    def schedule_full_backup_only(chat_id: int, delay: float | None=None):
        effective = max(2.5, float(delay if delay is not None else 2.5))
        return _ORIGINAL_SCHEDULE_FULL_BACKUP_ONLY(chat_id, effective)

def _integrity_root() -> dict:
    root = _root_settings().setdefault('finance_integrity_v141', {})
    root.setdefault('events', [])
    root.setdefault('tips', {})
    root.setdefault('anchor', {})
    root.setdefault('event_seq', 0)
    try:
        head = data.get('_finance_integrity_head_v189') or {}
        if isinstance(head, dict) and int(head.get('event_seq') or 0) >= int(root.get('event_seq') or 0):
            root['event_seq'] = int(head.get('event_seq') or 0)
            if isinstance(head.get('tips'), dict):
                root['tips'] = copy.deepcopy(head.get('tips') or {})
            if isinstance(head.get('anchor'), dict):
                root['anchor'] = copy.deepcopy(head.get('anchor') or {})
    except Exception:
        pass
    return root

def _integrity_canonical(payload: dict) -> str:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(',', ':'), default=str)

def _integrity_compact_record(record: dict | None) -> dict:
    rec = record or {}
    if not isinstance(rec, dict):
        return {'value': str(rec)[:300]}
    keep = ('id', 'amount', 'note', 'date', 'day', 'timestamp', 'currency', 'source_msg_id', 'operation_key', 'ids')
    return {k: copy.deepcopy(rec.get(k)) for k in keep if k in rec}

def _finance_integrity_upload_anchor(anchor: dict) -> None:
    tmp = None
    try:
        if not globals().get('mega_is_configured') or not mega_is_configured():
            return
        remote = f"{str(globals().get('MEGA_BACKUP_DIR') or '').rstrip('/')}/integrity"
        mega_ensure_remote_path(remote)
        os.makedirs(MEGA_LOCAL_TMP_DIR, exist_ok=True)
        name = f"finance_anchor_{int(anchor.get('seq') or 0):08d}_{str(anchor.get('hash') or '')[:12]}.json"
        tmp = os.path.join(MEGA_LOCAL_TMP_DIR, name)
        _atomic_json_dump(tmp, {'kind': 'finance_integrity_anchor', 'bot_version': VERSION, **anchor})
        _mega_run('mega-put', [tmp, remote], check=True, timeout=MEGA_TIMEOUT)
        bot_journal('finance_integrity_anchor_saved', anchor.get('chat_id'), f"seq={anchor.get('seq')} hash={anchor.get('hash')}")
    except Exception as exc:
        log_error(f'finance integrity anchor: {exc}')
    finally:
        try:
            if tmp and os.path.exists(tmp):
                os.remove(tmp)
        except Exception:
            pass

def finance_integrity_append(chat_id: int, action: str, record: dict | None=None, details: dict | None=None) -> str:
    cid = int(chat_id)
    with _FINANCE_INTEGRITY_LOCK:
        root = _integrity_root()
        tips = root.setdefault('tips', {})
        prev = str(tips.get(str(cid)) or '')
        root['event_seq'] = int(root.get('event_seq') or 0) + 1
        seq = int(root['event_seq'])
        payload = {'seq': seq, 'chat_id': cid, 'action': str(action), 'record': _integrity_compact_record(record), 'details': _compact_operation_payload(details), 'at': now_local().isoformat(timespec='microseconds'), 'prev': prev}
        digest = hashlib.sha256((prev + '|' + _integrity_canonical(payload)).encode('utf-8')).hexdigest()
        event = dict(payload)
        event['hash'] = digest
        root.setdefault('events', []).append(event)
        tips[str(cid)] = digest
        if len(root['events']) > _FINANCE_INTEGRITY_KEEP:
            root['events'] = root['events'][-_FINANCE_INTEGRITY_KEEP:]
        anchor = None
        if seq % 50 == 0:
            anchor = {'seq': seq, 'chat_id': cid, 'hash': digest, 'at': payload['at']}
            root['anchor'] = dict(anchor)
    _root_save_coalesced('finance_integrity', 1.0)
    try:
        ledger_fn = globals().get('constitution_ledger_append')
        if callable(ledger_fn):
            ledger_fn(cid, str(action), record, details, digest, seq)
    except Exception as _constitution_ledger_exc:
        try:
            constitution_set_quarantine(f'finance ledger append exception seq={seq}: {_constitution_ledger_exc}')
        except Exception:
            pass
        log_error(f'DATA CONSTITUTION ledger append: {_constitution_ledger_exc}')
    if anchor:
        pool = globals().get('GENERAL_TASK_POOL')
        if pool is not None:
            pool.submit_unique(f'integrity-anchor:{seq}', _finance_integrity_upload_anchor, anchor)
    return digest

def finance_integrity_verify(limit: int=5000) -> dict:
    with _FINANCE_INTEGRITY_LOCK:
        events = copy.deepcopy((_integrity_root().get('events') or [])[-max(1, int(limit)):])
    previous_by_chat = {}
    checked = 0
    for event in events:
        cid = str(event.get('chat_id'))
        prev = str(event.get('prev') or '')
        expected_prev = previous_by_chat.get(cid)
        if expected_prev is not None and prev != expected_prev:
            return {'ok': False, 'checked': checked, 'error': f'разрыв цепочки chat={cid}'}
        payload = {k: copy.deepcopy(v) for k, v in event.items() if k != 'hash'}
        digest = hashlib.sha256((prev + '|' + _integrity_canonical(payload)).encode('utf-8')).hexdigest()
        if digest != str(event.get('hash') or ''):
            return {'ok': False, 'checked': checked, 'error': f'неверный hash chat={cid}'}
        previous_by_chat[cid] = digest
        checked += 1
    return {'ok': True, 'checked': checked, 'error': ''}

def finance_integrity_text() -> str:
    report = finance_integrity_verify()
    root = _integrity_root()
    return f"🔗 ЦЕЛОСТНОСТЬ ФИНАНСОВ\n\nСобытий в цепочке: {len(root.get('events') or [])}\nПроверено: {report.get('checked', 0)}\nРезультат: {('✅ цепочка цела' if report.get('ok') else '🔴 обнаружена проблема')}\nПодробности: {report.get('error') or 'нет'}"

def runtime_audit_metrics() -> dict:
    """Compact counters included in diagnostics without serializing large payloads."""
    try:
        op_root = _operation_root()
        integ = _integrity_root()
        inbox = _expense_inbox_root()
        lock = globals().get('_FORWARD_OUTCOME_LOCK')
        if lock is not None:
            with lock:
                forward_outcomes = len(globals().get('_FORWARD_OUTCOMES') or {})
        else:
            forward_outcomes = len(globals().get('_FORWARD_OUTCOMES') or {})
        batches = len(globals().get('_FIN_FORWARD_BATCHES') or {})
        return {'operation_items': len(op_root.get('items') or {}), 'operation_order': len(op_root.get('order') or []), 'integrity_events': len(integ.get('events') or []), 'integrity_anchor': dict(integ.get('anchor') or {}), 'expense_drafts': len(inbox.get('items') or {}), 'finance_cache_entries': len(_FINANCE_VIEW_CACHE), 'forward_outcomes': forward_outcomes, 'finance_forward_batches': batches, 'reminder_mode': reminder_ui_mode() if 'reminder_ui_mode' in globals() else '', 'reminder_groups': len((_reminder_group_state_root() if '_reminder_group_state_root' in globals() else {}) or {}), 'journal_buffer_rows': len(globals().get('_JOURNAL_DURABLE_BUFFER') or [])}
    except Exception as exc:
        return {'error': str(exc)[:300]}

def start_safety_schedulers():
    global _SAFETY_SCHEDULERS_STARTED
    with _SAFETY_SCHEDULERS_LOCK:
        if _SAFETY_SCHEDULERS_STARTED:
            return
        _SAFETY_SCHEDULERS_STARTED = True
        try:
            GENERAL_TASK_POOL.submit_unique('expense-recent-migration-v142', migrate_recent_expense_shortcut_events, 2, False)
        except Exception:
            pass
        DELAYED_SCHEDULER.schedule('expense-evening-reconcile', 5.0, _evening_reconciliation_tick)

def expense_draft_insert_value(draft_id: int) -> str:
    service = f'(EXPENSEDRAFT|{int(draft_id)}| служебное — можно не трогать)'
    return service + '\n\n0 продукты описание'

def expense_draft_message_keyboard(draft_id: int, viewer_chat_id: int):
    if not expense_quick_buttons_enabled():
        return None
    kb = types.InlineKeyboardMarkup(row_width=1)
    kb.row(make_copy_or_inline_button('✍️ Заполнить расход', expense_draft_insert_value(draft_id), viewer_chat_id=viewer_chat_id))
    kb.row(IB('❌ Это не расход', callback_data=f'expense_draft_dismiss:{int(draft_id)}'))
    return kb

def build_expense_inbox_keyboard(viewer_chat_id: int):
    kb = types.InlineKeyboardMarkup(row_width=1)
    rows = expense_open_rows(30)
    for row in rows:
        try:
            dt = datetime.fromisoformat(str(row.get('created_at') or ''))
            label = dt.strftime('%d.%m %H:%M')
        except Exception:
            label = str(row.get('created_at') or '')[:16]
        kb.row(IB(f"{row.get('id')}. {label} · заполнить", callback_data=f"expense_draft_open:{row.get('id')}"))
    kb.row(IB(evening_reconciliation_label(), callback_data='expense_evening_toggle'))
    kb.row(IB('🌙 Проверить сейчас', callback_data='expense_evening_now'))
    day = get_chat_store(viewer_chat_id).get('current_view_day') or today_key()
    kb.row(IB('🔙 Назад в Инфо', callback_data=f'd:{day}:info'))
    kb.row(IB('⬅️ Назад осн. окно', callback_data=f'd:{day}:back_main'))
    return kb

def build_expense_draft_text(draft_id: int) -> str:
    row = (_expense_inbox_root().get('items') or {}).get(str(int(draft_id))) or {}
    if not row:
        return '❌ Отметка расхода не найдена.'
    try:
        dt = datetime.fromisoformat(str(row.get('created_at') or ''))
        when = dt.strftime('%d.%m.%Y %H:%M')
    except Exception:
        when = str(row.get('created_at') or '—')
    return f"❓ НЕРАЗОБРАННЫЙ РАСХОД №{draft_id}\n\nВремя: {when}\nЧат: {get_chat_display_name(int(row.get('target_chat_id') or 0))}\nИсточник: {row.get('source') or 'быстрая отметка'}\n\nОткройте исходное сообщение в финансовом чате и нажмите «✍️ Заполнить расход»."

def build_expense_draft_detail_keyboard(draft_id: int, viewer_chat_id: int):
    row = (_expense_inbox_root().get('items') or {}).get(str(int(draft_id))) or {}
    kb = types.InlineKeyboardMarkup(row_width=1)
    target = int(row.get('target_chat_id') or viewer_chat_id)
    if target == int(viewer_chat_id):
        kb.row(make_copy_or_inline_button('✍️ Заполнить здесь', expense_draft_insert_value(draft_id), viewer_chat_id=viewer_chat_id))
    kb.row(IB('✅ Уже внесено', callback_data=f'expense_draft_resolved:{int(draft_id)}'))
    kb.row(IB('❌ Это не расход', callback_data=f'expense_draft_dismiss:{int(draft_id)}'))
    kb.row(IB('⬅️ К неразобранным', callback_data='expense_inbox_open'))
    return kb

def _expense_draft_input_predicate(msg) -> bool:
    try:
        return getattr(msg, 'content_type', None) == 'text' and bool(re.search('\\(EXPENSEDRAFT\\|\\d+\\|', str(getattr(msg, 'text', '') or '')))
    except Exception:
        return False

@bot.message_handler(func=_expense_draft_input_predicate, content_types=['text'])
def expense_draft_input_message(msg):
    raw = str(getattr(msg, 'text', '') or '')
    m = re.search('\\(EXPENSEDRAFT\\|(\\d+)\\|[^)]*\\)', raw)
    if not m:
        return
    draft_id = int(m.group(1))
    clean = (raw[:m.start()] + ' ' + raw[m.end():]).strip()
    try:
        clean = sanitize_telegram_inserted_text(clean)
    except Exception:
        clean = re.sub('(?m)^\\s*@[A-Za-z0-9_]{3,}\\s+', '', clean).strip()
    if not clean or not re.search('\\d', clean):
        send_and_auto_delete(int(msg.chat.id), '❌ Укажите сумму и описание, например: 5500 продукты хлеб', 10)
        return
    original_text = msg.text
    msg.text = clean
    op_id = operation_begin('expense_draft_fill', int(msg.chat.id), target=str(draft_id), payload={'text': clean}, critical=True)
    try:
        ok = bool(handle_finance_text(msg))
        if ok:
            expense_draft_mark(draft_id, 'resolved', note=clean)
            operation_complete(op_id, 'finance record created')
            try:
                bot.delete_message(int(msg.chat.id), int(msg.message_id))
            except Exception:
                pass
            send_and_auto_delete(int(msg.chat.id), f'✅ Расход №{draft_id} внесён.', 8)
        else:
            operation_review(op_id, 'finance mode did not accept the text')
            send_and_auto_delete(int(msg.chat.id), '⚠️ Финансовый режим не принял запись. Проверьте, включён ли ФИН.', 12)
    except Exception as exc:
        operation_fail(op_id, str(exc))
        raise
    finally:
        msg.text = original_text
# v262
