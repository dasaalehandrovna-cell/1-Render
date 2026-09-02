# v262
"""v185 DATA CONSTITUTION.

Immutable storage contract. UI/performance modules must not redefine these functions.
Canonical MEGA root is the immutable MEGA_BACKUP_DIR (default /TelegramBotBackups).
"""
DATA_CONSTITUTION_SCHEMA = 1
DATA_CONSTITUTION_QUARANTINE = False
DATA_CONSTITUTION_REASON = ''
DATA_CONSTITUTION_LAST_VERIFY = {}
DATA_CONSTITUTION_LOCK = threading.RLock()
DATA_CONSTITUTION_LEDGER_LOCK = threading.RLock()
DATA_CONSTITUTION_MANIFEST_CACHE = {'at': 0.0, 'value': None}
DATA_CONSTITUTION_RECOVERY_LAST_ATTEMPT = 0.0
DATA_CONSTITUTION_RECOVERY_COOLDOWN_SECONDS = 300.0
DATA_CONSTITUTION_GENERATION_KEEP_MIN = 12
STORAGE_LINEAGE_META_KIND_V239 = 'storage_lineage_v239'
STORAGE_LINEAGE_META_KEY_V239 = 'current'

def _v239_storage_lineage(create: bool=True) -> str:
    try:
        row = SQLITE.get_meta(STORAGE_LINEAGE_META_KIND_V239, STORAGE_LINEAGE_META_KEY_V239, {}) or {}
        if isinstance(row, dict):
            value = str(row.get('lineage') or '').strip()
        else:
            value = str(row or '').strip()
        if value or not create:
            return value
    except Exception:
        if not create:
            return ''
    seed = f'{time.time_ns()}:{os.getpid()}:{VERSION}:{id(data)}'
    value = 'L239_' + hashlib.sha256(seed.encode('utf-8')).hexdigest()[:24]
    try:
        SQLITE.set_meta(STORAGE_LINEAGE_META_KIND_V239, STORAGE_LINEAGE_META_KEY_V239, {'lineage': value, 'created_at': now_local().isoformat(timespec='microseconds'), 'reason': 'bootstrap_v239', 'bot_version': VERSION})
    except Exception:
        pass
    return value

def _v239_rotate_storage_lineage(reason: str='manual_restore') -> str:
    previous = _v239_storage_lineage(create=False)
    seed = f'{time.time_ns()}:{os.getpid()}:{VERSION}:{reason}:{previous}'
    value = 'L239_' + hashlib.sha256(seed.encode('utf-8')).hexdigest()[:24]
    SQLITE.set_meta(STORAGE_LINEAGE_META_KIND_V239, STORAGE_LINEAGE_META_KEY_V239, {'lineage': value, 'previous': previous, 'created_at': now_local().isoformat(timespec='microseconds'), 'reason': str(reason or 'manual_restore'), 'bot_version': VERSION})
    try:
        bot_journal('storage_lineage_rotated_v239', int(OWNER_ID or 0) or None, f"reason={reason}; previous={previous or '-'}; new={value}")
    except Exception:
        pass
    return value

def _v239_semantic_core(manifest: dict) -> dict:
    m = manifest if isinstance(manifest, dict) else {}
    chats = {}
    for cid, row in sorted((m.get('chats') or {}).items(), key=lambda kv: str(kv[0])):
        if not isinstance(row, dict):
            continue
        chats[str(cid)] = {'record_count': int(row.get('record_count') or 0), 'usd_event_count': int(row.get('usd_event_count') or 0), 'earliest_day': str(row.get('earliest_day') or ''), 'latest_day': str(row.get('latest_day') or ''), 'ars_sum': round(float(row.get('ars_sum') or 0.0), 6), 'usd_sum': round(float(row.get('usd_sum') or 0.0), 6), 'record_keys_hash': str(row.get('record_keys_hash') or '')}
    return {'total_records': int(m.get('total_records') or 0), 'finance_chat_count': int(m.get('finance_chat_count') or len(chats)), 'integrity_seq': int(m.get('integrity_seq') or 0), 'ledger_highwater_seq': int(m.get('ledger_highwater_seq') or 0), 'ledger_highwater_hash': str(m.get('ledger_highwater_hash') or ''), 'storage_lineage_v239': str(m.get('storage_lineage_v239') or ''), 'chats': chats}

def _v239_read_embedded_manifest_from_sqlite(path: str) -> dict:
    conn = sqlite3.connect(str(path))
    try:
        row = conn.execute("SELECT v FROM meta WHERE kind='data_constitution_snapshot' AND k='main'").fetchone()
        value = json.loads(row[0]) if row and row[0] else {}
        return value if isinstance(value, dict) else {}
    finally:
        conn.close()

def _v239_generation_exact_preflight(sqlite_path: str, external_manifest: dict | None=None, *, require_embedded: bool=True) -> dict:
    actual = constitution_semantic_manifest_from_sqlite(sqlite_path)
    embedded = _v239_read_embedded_manifest_from_sqlite(sqlite_path)
    if require_embedded and (not embedded):
        raise RuntimeError('v239 exact generation rejected: embedded Data Constitution manifest missing')
    a = _v239_semantic_core(actual)
    if embedded:
        e = _v239_semantic_core(embedded)
        if a != e:
            raise RuntimeError(f"v239 exact generation rejected: actual != embedded; actual_records={a.get('total_records')} embedded_records={e.get('total_records')}")
    if isinstance(external_manifest, dict) and external_manifest:
        x = _v239_semantic_core(external_manifest)
        if a != x:
            raise RuntimeError(f"v239 exact generation rejected: actual != external manifest; actual_records={a.get('total_records')} external_records={x.get('total_records')}")
    return {'ok': True, 'actual': actual, 'embedded': embedded, 'core': a}
DATA_CONSTITUTION_PROTECTION_KEY_V232 = 'data_constitution_protection_v232'
DATA_CONSTITUTION_LAST_WARNING_V232 = ''
DATA_CONSTITUTION_LOSS_GUARD_KEY_V255 = 'data_constitution_loss_guard_v255'

def _constitution_loss_guard_settings_v255() -> dict:
    """Owner-controlled semantic record-loss guard. Default OFF in v255.

    This switch only governs unexplained decreases in finance record counts/history.
    Structural integrity checks (manifest validity, ledger/integrity ordering and storage
    lineage mismatch) remain active regardless of this switch.
    """
    try:
        gs = data.setdefault('_global_settings', {})
        row = gs.setdefault(DATA_CONSTITUTION_LOSS_GUARD_KEY_V255, {})
        if not isinstance(row, dict):
            row = {}
            gs[DATA_CONSTITUTION_LOSS_GUARD_KEY_V255] = row
        # New key deliberately defaults to OFF even when legacy v232 protection was ON.
        row.setdefault('enabled', False)
        return row
    except Exception:
        return {'enabled': False}

def constitution_loss_guard_enabled_v255() -> bool:
    return bool(_constitution_loss_guard_settings_v255().get('enabled', False))

def set_constitution_loss_guard_v255(enabled: bool) -> bool:
    row = _constitution_loss_guard_settings_v255()
    row['enabled'] = bool(enabled)
    row['updated_at'] = now_local().isoformat(timespec='seconds')
    row['bot_version'] = str(VERSION)
    try:
        save_data(data, root_only=True)
    except Exception:
        pass
    try:
        SQLITE.set_meta('data_constitution', 'loss_guard_v255', {
            'enabled': bool(enabled),
            'at': now_local().isoformat(timespec='seconds'),
            'bot_version': str(VERSION),
        })
    except Exception:
        pass
    # Turning this particular guard OFF must release quarantine that was created
    # by its record-loss reasons, but must not clear unrelated restore guards.
    if not enabled:
        try:
            reason = str(globals().get('DATA_CONSTITUTION_REASON', '') or '')
            low = reason.casefold()
            if ('unauthorized total record loss' in low or ' record loss:' in low or ' history starts later:' in low):
                constitution_clear_quarantine('owner disabled v255 record-loss guard')
        except Exception:
            pass
    try:
        schedule_delta_backup(int(OWNER_ID or 0), delay=0.2, reason='constitution_loss_guard_v255')
    except Exception:
        pass
    return bool(enabled)

def _constitution_v232_settings() -> dict:
    try:
        gs = data.setdefault('_global_settings', {})
        row = gs.setdefault(DATA_CONSTITUTION_PROTECTION_KEY_V232, {})
        if not isinstance(row, dict):
            row = {}
            gs[DATA_CONSTITUTION_PROTECTION_KEY_V232] = row
        row.setdefault('enabled', True)
        row.setdefault('soft_mode', True)
        return row
    except Exception:
        return {'enabled': True, 'soft_mode': True}

def constitution_protection_enabled_v232() -> bool:
    return bool(_constitution_v232_settings().get('enabled', True))

def set_constitution_protection_v232(enabled: bool) -> bool:
    row = _constitution_v232_settings()
    row['enabled'] = bool(enabled)
    row['soft_mode'] = True
    try:
        save_data(data, root_only=True)
    except Exception:
        pass
    try:
        SQLITE.set_meta('data_constitution', 'protection_v232', {'enabled': bool(enabled), 'at': now_local().isoformat(timespec='seconds')})
    except Exception:
        pass
    if not enabled:
        constitution_clear_quarantine('owner disabled Data Constitution protection')
    try:
        schedule_delta_backup(int(OWNER_ID or 0), delay=0.2, reason='constitution_protection_v232')
    except Exception:
        pass
    return bool(enabled)

def constitution_finance_write_blocked_v232() -> bool:
    """Only a real/manual restore guard may freeze finance; Data Constitution quarantine never does."""
    try:
        if not bool(globals().get('RESTORE_GUARD_ACTIVE', False)):
            return False
        reason = str(globals().get('RESTORE_GUARD_REASON', '') or '')
        return not reason.startswith('DATA CONSTITUTION:')
    except Exception:
        return False

def constitution_continue_work_v232() -> bool:
    """Acknowledge the warning and release only a legacy constitution-owned global restore guard."""
    try:
        reason = str(globals().get('RESTORE_GUARD_REASON', '') or '')
        clear_guard = globals().get('_clear_restore_guard')
        if reason.startswith('DATA CONSTITUTION:') and callable(clear_guard):
            clear_guard()
    except Exception:
        pass
    try:
        SQLITE.set_meta('data_constitution', 'owner_continue_v232', {'at': now_local().isoformat(timespec='seconds'), 'reason': str(DATA_CONSTITUTION_REASON or '')})
    except Exception:
        pass
    return True

def constitution_accept_current_state_v232(reason: str='owner_accept_current') -> bool:
    """Explicit owner re-anchor: current live SQLite becomes the trusted immutable generation."""
    try:
        constitution_reanchor_after_manual_restore(str(reason or 'owner_accept_current_v232'))
        constitution_clear_quarantine('owner accepted current state')
        return True
    except Exception as exc:
        try:
            runtime_event('data_constitution_accept_current_failed_v232', str(exc)[:700], 'ERROR')
        except Exception:
            pass
        return False
try:
    LOWRAM_DB_HISTORY_KEEP = max(int(LOWRAM_DB_HISTORY_KEEP), DATA_CONSTITUTION_GENERATION_KEEP_MIN)
except Exception:
    LOWRAM_DB_HISTORY_KEEP = DATA_CONSTITUTION_GENERATION_KEEP_MIN

def constitution_root() -> str:
    return str(MEGA_BACKUP_DIR).rstrip('/')

def constitution_database_dir() -> str:
    return constitution_root() + '/database'

def constitution_generations_dir() -> str:
    return constitution_database_dir() + '/generations'

def constitution_manifests_dir() -> str:
    return constitution_database_dir() + '/manifests'

def constitution_manifest_history_dir() -> str:
    return constitution_database_dir() + '/manifest_history'

def constitution_current_manifest_remote() -> str:
    return constitution_database_dir() + '/current_manifest.json'

def constitution_ledger_root(chat_id: int | None=None) -> str:
    if chat_id is not None:
        shard = globals().get('mega_shard_domain_dir_v240')
        if callable(shard) and bool(globals().get('MEGA_SHARDED_STORAGE_V240', False)):
            try:
                return str(shard(int(chat_id), 'finance')).rstrip('/') + '/ledger'
            except Exception:
                pass
    return constitution_root() + '/ledger/finance'

def constitution_quarantine_active() -> bool:
    return bool(DATA_CONSTITUTION_QUARANTINE or globals().get('RESTORE_GUARD_ACTIVE', False))

def constitution_set_quarantine(reason: str) -> None:
    global DATA_CONSTITUTION_QUARANTINE, DATA_CONSTITUTION_REASON, DATA_CONSTITUTION_LAST_WARNING_V232
    reason = str(reason or 'DATA CONSTITUTION violation')[:800]
    DATA_CONSTITUTION_LAST_WARNING_V232 = reason
    low_reason_v255 = reason.casefold()
    loss_reason_v255 = ('unauthorized total record loss' in low_reason_v255 or ' record loss:' in low_reason_v255 or ' history starts later:' in low_reason_v255)
    if loss_reason_v255 and not constitution_loss_guard_enabled_v255():
        with DATA_CONSTITUTION_LOCK:
            DATA_CONSTITUTION_QUARANTINE = False
            DATA_CONSTITUTION_REASON = reason
        try:
            SQLITE.set_meta('data_constitution', 'quarantine', {'active': False, 'warning': True, 'reason': reason, 'guard': 'record_loss_v255_off', 'at': now_local().isoformat(timespec='seconds')})
        except Exception:
            pass
        try:
            runtime_event('data_constitution_record_loss_warning_bypassed_v255', reason, 'WARN')
        except Exception:
            pass
        return
    if not constitution_protection_enabled_v232():
        with DATA_CONSTITUTION_LOCK:
            DATA_CONSTITUTION_QUARANTINE = False
            DATA_CONSTITUTION_REASON = reason
        try:
            SQLITE.set_meta('data_constitution', 'quarantine', {'active': False, 'warning': True, 'reason': reason, 'at': now_local().isoformat(timespec='seconds')})
        except Exception:
            pass
        try:
            runtime_event('data_constitution_warning_bypassed_v232', reason, 'WARN')
        except Exception:
            pass
        return
    with DATA_CONSTITUTION_LOCK:
        DATA_CONSTITUTION_QUARANTINE = True
        DATA_CONSTITUTION_REASON = reason
    try:
        legacy_reason = str(globals().get('RESTORE_GUARD_REASON', '') or '')
        clear_guard = globals().get('_clear_restore_guard')
        if legacy_reason.startswith('DATA CONSTITUTION:') and callable(clear_guard):
            clear_guard()
    except Exception:
        pass
    try:
        SQLITE.set_meta('data_constitution', 'quarantine', {'active': True, 'reason': reason, 'soft_mode': True, 'at': now_local().isoformat(timespec='seconds')})
    except Exception:
        pass
    try:
        runtime_event('data_constitution_quarantine_soft_v232', reason, 'ERROR')
    except Exception:
        pass

def constitution_clear_quarantine(reason: str='verified') -> None:
    global DATA_CONSTITUTION_QUARANTINE, DATA_CONSTITUTION_REASON
    with DATA_CONSTITUTION_LOCK:
        DATA_CONSTITUTION_QUARANTINE = False
        DATA_CONSTITUTION_REASON = ''
    try:
        guard_reason = str(globals().get('RESTORE_GUARD_REASON', '') or '')
        clear_guard = globals().get('_clear_restore_guard')
        if guard_reason.startswith('DATA CONSTITUTION:') and callable(clear_guard):
            clear_guard()
    except Exception:
        pass
    try:
        SQLITE.set_meta('data_constitution', 'quarantine', {'active': False, 'reason': str(reason), 'at': now_local().isoformat(timespec='seconds')})
    except Exception:
        pass

def _constitution_json_clone(value):
    try:
        return json.loads(json.dumps(value, ensure_ascii=False, default=str))
    except Exception:
        return copy.deepcopy(value)

def _constitution_record_key(rec: dict, index: int=0) -> str:
    if not isinstance(rec, dict):
        return f'bad:{index}'
    for key in ('operation_key', 'record_uid', 'uid'):
        value = str(rec.get(key) or '').strip()
        if value:
            return key + ':' + value
    source = rec.get('source_msg_id') or rec.get('msg_id') or rec.get('origin_msg_id')
    if source not in (None, '', 0, '0'):
        return 'msg:' + str(source)
    return 'row:' + hashlib.sha256(json.dumps(rec, ensure_ascii=False, sort_keys=True, default=str).encode('utf-8')).hexdigest()[:24]

def _constitution_record_day(rec: dict) -> str:
    day = str((rec or {}).get('day_key') or (rec or {}).get('date') or '').strip()
    if re.fullmatch('\\d{2}:\\d{2}:\\d{2}', day):
        try:
            return datetime.strptime(day, '%d:%m:%y').strftime('%Y-%m-%d')
        except Exception:
            pass
    if re.fullmatch('\\d{4}-\\d{2}-\\d{2}', day):
        return day
    ts = str((rec or {}).get('timestamp') or '')[:10]
    return ts if re.fullmatch('\\d{4}-\\d{2}-\\d{2}', ts) else ''

def _constitution_collect_unique_records(store: dict) -> list[dict]:
    seen = {}
    for field in ('records', 'ars_records', 'usd_records'):
        try:
            rows = store.get(field, []) or []
        except Exception:
            rows = []
        for idx, rec in enumerate(rows):
            if not isinstance(rec, dict):
                continue
            key = _constitution_record_key(rec, idx)
            old = seen.get(key)
            if old is None or len(rec) > len(old):
                seen[key] = rec
    return list(seen.values())

def _constitution_chat_semantics(chat_id, store: dict) -> dict:
    rows = _constitution_collect_unique_records(store or {})
    days = sorted({d for d in (_constitution_record_day(r) for r in rows) if d})
    ars_sum = 0.0
    usd_sum = 0.0
    usd_events = 0
    keys = []
    for idx, rec in enumerate(rows):
        keys.append(_constitution_record_key(rec, idx))
        try:
            ars_sum += float(rec.get('amount', 0) or 0)
        except Exception:
            pass
        if 'usd_amount' in rec:
            try:
                u = float(rec.get('usd_amount', 0) or 0)
                usd_sum += u
                if abs(u) > 0 or bool(rec.get('usd_only')):
                    usd_events += 1
            except Exception:
                pass
        elif str(rec.get('currency') or '').upper() == 'USD':
            try:
                usd_sum += float(rec.get('amount', 0) or 0)
                usd_events += 1
            except Exception:
                pass
    keys.sort()
    return {'chat_id': int(chat_id), 'record_count': len(rows), 'usd_event_count': int(usd_events), 'earliest_day': days[0] if days else '', 'latest_day': days[-1] if days else '', 'ars_sum': round(ars_sum, 6), 'usd_sum': round(usd_sum, 6), 'record_keys_hash': hashlib.sha256('\n'.join(keys).encode('utf-8')).hexdigest()}

def _constitution_integrity_state() -> tuple[int, str]:
    try:
        root = _root_settings().get('finance_integrity_v141') or {} if '_root_settings' in globals() else {}
        return (int(root.get('event_seq') or 0), str((root.get('anchor') or {}).get('hash') or ''))
    except Exception:
        return (0, '')

def _constitution_advance_local_ledger_highwater_v260(event: dict, pending_name: str='') -> dict:
    if not isinstance(event, dict):
        return {}
    high = {
        'seq': int(event.get('seq') or 0),
        'hash': str(event.get('event_hash') or ''),
        'integrity_hash': str(event.get('integrity_hash') or ''),
        'at': str(event.get('at') or ''),
        'backend': 'sqlite_pending_v260',
        'pending_name': str(pending_name or ''),
        'remote': '',
    }
    if not high['seq']:
        return {}
    try:
        with DATA_CONSTITUTION_LEDGER_LOCK:
            previous = SQLITE.get_meta('data_constitution', 'ledger_highwater', {}) or {}
            if int(high['seq']) >= int((previous or {}).get('seq') or 0):
                if isinstance(previous, dict) and str(previous.get('remote') or '') and int(previous.get('seq') or 0) == int(high['seq']):
                    high['remote'] = str(previous.get('remote') or '')
                SQLITE.set_meta('data_constitution', 'ledger_highwater', high)
                if '_root_settings' in globals():
                    _root_settings()['data_constitution_ledger_highwater'] = copy.deepcopy(high)
                    if '_root_save_coalesced' in globals():
                        _root_save_coalesced('constitution_ledger_highwater_v260', 0.2)
    except Exception as exc:
        try: log_error(f'[DATA CONSTITUTION] local highwater advance v260: {exc}')
        except Exception: pass
    return high

def _constitution_reconcile_local_ledger_highwater_v260() -> dict:
    """Treat a ledger event durably stored in local SQLite as a valid local highwater.

    v259 advanced highwater only after the remote/Telegram ledger upload finished.  In
    Render-only mode (and during a slow remote flush) finance_integrity could therefore
    move ahead of ledger_highwater even though every immutable event was already safely
    committed in SQLite ``data_constitution_pending``.  That false lag blocked snapshots
    and Google.  The SQLite snapshot contains those pending events, so the local durable
    highwater is the correct recovery boundary; remote publication remains asynchronous.
    """
    best = {}
    try:
        current = SQLITE.get_meta('data_constitution', 'ledger_highwater', {}) or {}
        if isinstance(current, dict):
            best = dict(current)
    except Exception:
        best = {}
    try:
        with SQLITE.lock:
            rows = SQLITE.conn.execute("SELECT k,v FROM meta WHERE kind='data_constitution_pending'").fetchall()
        for key, raw in rows:
            try:
                ev = json.loads(raw) if isinstance(raw, str) else raw
            except Exception:
                continue
            if not isinstance(ev, dict) or ev.get('kind') != 'telegram_bot_finance_immutable_ledger':
                continue
            seq = int(ev.get('seq') or 0)
            if seq <= int(best.get('seq') or 0):
                continue
            best = {
                'seq': seq,
                'hash': str(ev.get('event_hash') or ''),
                'integrity_hash': str(ev.get('integrity_hash') or ''),
                'at': str(ev.get('at') or ''),
                'backend': 'sqlite_pending_v260',
                'pending_name': str(key or ''),
                'remote': str((best or {}).get('remote') or ''),
            }
    except Exception:
        pass
    try:
        if int(best.get('seq') or 0) > 0:
            SQLITE.set_meta('data_constitution', 'ledger_highwater', best)
            if '_root_settings' in globals():
                _root_settings()['data_constitution_ledger_highwater'] = copy.deepcopy(best)
                if '_root_save_coalesced' in globals():
                    _root_save_coalesced('constitution_ledger_highwater_v260', 0.2)
    except Exception:
        pass
    return best

def _constitution_ledger_highwater() -> dict:
    root_value = {}
    try:
        root_value = _root_settings().get('data_constitution_ledger_highwater') or {} if '_root_settings' in globals() else {}
    except Exception:
        root_value = {}
    try:
        value = SQLITE.get_meta('data_constitution', 'ledger_highwater', {}) or {}
    except Exception:
        value = {}
    best = root_value if isinstance(root_value, dict) else {}
    if isinstance(value, dict) and int(value.get('seq') or 0) > int(best.get('seq') or 0):
        best = value
    try:
        integrity_seq, _ = _constitution_integrity_state()
        if int(best.get('seq') or 0) < int(integrity_seq or 0):
            repaired = _constitution_reconcile_local_ledger_highwater_v260()
            if int((repaired or {}).get('seq') or 0) > int(best.get('seq') or 0):
                best = repaired
    except Exception:
        pass
    return best if isinstance(best, dict) else {}

def constitution_semantic_manifest_from_live() -> dict:
    chats_out = {}
    chat_ids = set()
    try:
        chat_ids.update((int(x) for x in (SQLITE.load_chats() or {}).keys()))
    except Exception:
        pass
    try:
        chat_ids.update((int(x) for x in (data.get('chats', {}) or {}).keys()))
    except Exception:
        pass
    try:
        cold_ids = SQLITE.cold_chat_ids(('records', 'ars_records', 'usd_records'))
        chat_ids.update((int(x) for x in cold_ids or []))
    except Exception as exc:
        try:
            log_error(f'constitution cold chat enumeration: {exc}')
        except Exception:
            pass
    total = 0
    for cid in sorted(chat_ids):
        try:
            store = get_chat_store(int(cid))
            row = _constitution_chat_semantics(cid, store)
            if row['record_count'] or is_finance_mode(int(cid)):
                chats_out[str(cid)] = row
                total += int(row['record_count'])
        except Exception as exc:
            try:
                log_error(f'constitution manifest chat {cid}: {exc}')
            except Exception:
                pass
    seq, anchor = _constitution_integrity_state()
    high = _constitution_ledger_highwater()
    manifest = {'kind': 'telegram_bot_data_constitution_manifest', 'schema_version': DATA_CONSTITUTION_SCHEMA, 'bot_version': VERSION, 'created_at': now_local().isoformat(timespec='microseconds'), 'total_records': int(total), 'finance_chat_count': len(chats_out), 'chats': chats_out, 'integrity_seq': int(seq), 'integrity_anchor': anchor, 'ledger_highwater_seq': int(high.get('seq') or 0), 'ledger_highwater_hash': str(high.get('hash') or ''), 'storage_lineage_v239': _v239_storage_lineage(create=True)}
    manifest['semantic_hash'] = hashlib.sha256(json.dumps(manifest, ensure_ascii=False, sort_keys=True, separators=(',', ':'), default=str).encode('utf-8')).hexdigest()
    return manifest

def constitution_semantic_manifest_from_sqlite(path: str) -> dict:
    conn = sqlite3.connect(str(path))
    try:
        qc = conn.execute('PRAGMA quick_check').fetchone()
        if not qc or str(qc[0]).lower() != 'ok':
            raise RuntimeError(f'SQLite quick_check failed: {qc}')
        chats_meta = {}
        for cid, raw in conn.execute('SELECT chat_id,v FROM chats').fetchall():
            try:
                chats_meta[str(cid)] = json.loads(raw) if raw else {}
            except Exception:
                chats_meta[str(cid)] = {}
        cold = defaultdict(dict)
        for cid, key, raw in conn.execute('SELECT chat_id,k,v FROM cold_fields').fetchall():
            if str(key) not in {'records', 'ars_records', 'usd_records'}:
                continue
            try:
                cold[str(cid)][str(key)] = json.loads(raw) if raw else []
            except Exception:
                cold[str(cid)][str(key)] = []
        chats_out = {}
        total = 0
        for cid in sorted(set(chats_meta) | set(cold), key=lambda x: int(x) if str(x).lstrip('-').isdigit() else str(x)):
            store = dict(chats_meta.get(cid) or {})
            store.update(cold.get(cid) or {})
            try:
                row = _constitution_chat_semantics(int(cid), store)
            except Exception:
                continue
            if row['record_count'] or bool((store.get('settings') or {}).get('finance_mode')):
                chats_out[str(cid)] = row
                total += int(row['record_count'])
        integrity_seq = 0
        ledger_seq = 0
        ledger_hash = ''
        root = {}
        try:
            root_raw = conn.execute("SELECT v FROM kv WHERE k='root'").fetchone()
            root = json.loads(root_raw[0]) if root_raw and root_raw[0] else {}
            integ = (root.get('_global_settings') or {}).get('finance_integrity_v141') or {}
            integrity_seq = int(integ.get('event_seq') or 0)
            root_high = (root.get('_global_settings') or {}).get('data_constitution_ledger_highwater') or {}
            ledger_seq = int(root_high.get('seq') or 0)
            ledger_hash = str(root_high.get('hash') or '')
        except Exception:
            pass
        try:
            hrow = conn.execute("SELECT v FROM meta WHERE kind='data_constitution' AND k='ledger_highwater'").fetchone()
            high = json.loads(hrow[0]) if hrow and hrow[0] else {}
            if int(high.get('seq') or 0) > ledger_seq:
                ledger_seq = int(high.get('seq') or 0)
                ledger_hash = str(high.get('hash') or '')
        except Exception:
            pass
        try:
            if int(ledger_seq or 0) < int(integrity_seq or 0):
                for _k, _raw in conn.execute("SELECT k,v FROM meta WHERE kind='data_constitution_pending'").fetchall():
                    try:
                        _ev = json.loads(_raw) if isinstance(_raw, str) else _raw
                    except Exception:
                        continue
                    if not isinstance(_ev, dict) or _ev.get('kind') != 'telegram_bot_finance_immutable_ledger':
                        continue
                    _seq = int(_ev.get('seq') or 0)
                    if _seq > ledger_seq:
                        ledger_seq = _seq
                        ledger_hash = str(_ev.get('event_hash') or '')
        except Exception:
            pass
        storage_lineage = ''
        try:
            lrow = conn.execute('SELECT v FROM meta WHERE kind=? AND k=?', (STORAGE_LINEAGE_META_KIND_V239, STORAGE_LINEAGE_META_KEY_V239)).fetchone()
            lval = json.loads(lrow[0]) if lrow and lrow[0] else {}
            storage_lineage = str((lval or {}).get('lineage') or '') if isinstance(lval, dict) else str(lval or '')
        except Exception:
            storage_lineage = ''
        manifest = {'kind': 'telegram_bot_data_constitution_manifest', 'schema_version': DATA_CONSTITUTION_SCHEMA, 'bot_version': VERSION, 'created_at': now_local().isoformat(timespec='microseconds'), 'total_records': int(total), 'finance_chat_count': len(chats_out), 'chats': chats_out, 'integrity_seq': int(integrity_seq), 'ledger_highwater_seq': int(ledger_seq), 'ledger_highwater_hash': ledger_hash, 'storage_lineage_v239': storage_lineage}
        manifest['semantic_hash'] = hashlib.sha256(json.dumps(manifest, ensure_ascii=False, sort_keys=True, separators=(',', ':'), default=str).encode('utf-8')).hexdigest()
        return manifest
    finally:
        conn.close()

def _constitution_authorized_deletes_since(old_seq: int) -> dict:
    out = defaultdict(int)
    try:
        events = list(_integrity_root().get('events') or [])
    except Exception:
        events = []
    for ev in events:
        try:
            if int(ev.get('seq') or 0) <= int(old_seq):
                continue
            cid = str(int(ev.get('chat_id')))
            action = str(ev.get('action') or '')
            if action == 'delete':
                out[cid] += 1
            elif action == 'bulk_delete':
                details = ev.get('details') or {}
                rows = details.get('records') if isinstance(details, dict) else []
                out[cid] += len(rows or []) or len((ev.get('record') or {}).get('ids') or [])
        except Exception:
            continue
    return dict(out)

def constitution_bootstrap_ledger_genesis() -> dict:
    """Anchor all pre-v185 history once, then immutable ledger covers mutations after that point."""
    current = constitution_load_active_manifest_remote(force=True)
    if current:
        return {'ok': True, 'existing': True}
    live = constitution_semantic_manifest_from_live()
    seq = int(live.get('integrity_seq') or 0)
    event = {'kind': 'telegram_bot_finance_ledger_genesis', 'schema_version': DATA_CONSTITUTION_SCHEMA, 'bot_version': VERSION, 'at': now_local().isoformat(timespec='microseconds'), 'integrity_seq': seq, 'semantic_manifest': live}
    event['event_hash'] = hashlib.sha256(json.dumps(event, ensure_ascii=False, sort_keys=True, separators=(',', ':'), default=str).encode('utf-8')).hexdigest()
    if mega_is_configured():
        workdir = tempfile.mkdtemp(prefix='constitution_genesis_')
        try:
            remote_dir = constitution_ledger_root() + '/genesis'
            mega_ensure_remote_path(remote_dir)
            name = f"ledger_genesis_{re.sub('[^0-9]', '', event['at'])[:20]}_{event['event_hash'][:16]}.json"
            local = os.path.join(workdir, name)
            _save_json(local, event)
            _mega_run('mega-put', [local, remote_dir], check=True, timeout=MEGA_TIMEOUT)
            high = {'seq': seq, 'hash': event['event_hash'], 'integrity_hash': str(live.get('integrity_anchor') or ''), 'at': event['at'], 'remote': remote_dir + '/' + name, 'genesis': True}
            SQLITE.set_meta('data_constitution', 'ledger_highwater', high)
            try:
                _root_settings()['data_constitution_ledger_highwater'] = copy.deepcopy(high)
                _root_save_coalesced('constitution_ledger_genesis', 0.1)
            except Exception:
                pass
            return {'ok': True, 'existing': False, 'seq': seq, 'remote': high['remote']}
        finally:
            shutil.rmtree(workdir, ignore_errors=True)
    raise RuntimeError('cannot bootstrap DATA CONSTITUTION ledger without MEGA')

def constitution_snapshot_rejection(candidate: dict, current: dict | None) -> str:
    if not isinstance(candidate, dict) or candidate.get('kind') != 'telegram_bot_data_constitution_manifest':
        return 'candidate manifest invalid'
    if int(candidate.get('ledger_highwater_seq') or 0) < int(candidate.get('integrity_seq') or 0):
        return f"ledger is behind finance integrity: {candidate.get('ledger_highwater_seq')} < {candidate.get('integrity_seq')}"
    if not current or not isinstance(current, dict):
        return ''
    old_lineage = str(current.get('storage_lineage_v239') or '')
    new_lineage = str(candidate.get('storage_lineage_v239') or '')
    if old_lineage and new_lineage and (old_lineage != new_lineage):
        return f'storage lineage mismatch: {old_lineage} != {new_lineage}'
    # v256: unexplained record-count/history shrink is optional and defaults OFF.
    # Keep all structural/integrity checks above active even when this guard is OFF.
    if not constitution_loss_guard_enabled_v255():
        return ''
    old_total = int(current.get('total_records') or 0)
    new_total = int(candidate.get('total_records') or 0)
    old_seq = int(current.get('integrity_seq') or 0)
    deletes = _constitution_authorized_deletes_since(old_seq)
    authorized_total = sum((int(x or 0) for x in deletes.values()))
    if new_total < old_total and old_total - new_total > authorized_total:
        return f'unauthorized total record loss: {old_total}->{new_total}; authorized deletes={authorized_total}'
    old_chats = current.get('chats') or {}
    new_chats = candidate.get('chats') or {}
    for cid, old in old_chats.items():
        old_n = int((old or {}).get('record_count') or 0)
        new_n = int((new_chats.get(str(cid)) or {}).get('record_count') or 0)
        allowed = int(deletes.get(str(cid), 0) or 0)
        if new_n < old_n and old_n - new_n > allowed:
            return f'chat {cid} record loss: {old_n}->{new_n}; authorized deletes={allowed}'
        if old_n >= 10 and new_n > 0:
            old_first = str((old or {}).get('earliest_day') or '')
            new_first = str((new_chats.get(str(cid)) or {}).get('earliest_day') or '')
            if old_first and new_first and (new_first > old_first) and (old_n - new_n > allowed):
                return f'chat {cid} history starts later: {old_first}->{new_first}'
    return ''

def constitution_load_active_manifest_remote(force: bool=False) -> dict | None:
    now_mono = time.monotonic()
    with DATA_CONSTITUTION_LOCK:
        if not force and DATA_CONSTITUTION_MANIFEST_CACHE.get('value') is not None and (now_mono - float(DATA_CONSTITUTION_MANIFEST_CACHE.get('at') or 0) < 120):
            return copy.deepcopy(DATA_CONSTITUTION_MANIFEST_CACHE.get('value'))
    if not mega_is_configured():
        return None
    workdir = tempfile.mkdtemp(prefix='constitution_manifest_')
    try:
        res = _mega_run('mega-get', [constitution_current_manifest_remote(), workdir], check=False, timeout=MEGA_TIMEOUT)
        if res.returncode != 0:
            return None
        candidates = list(Path(workdir).rglob('current_manifest.json')) + list(Path(workdir).rglob('*.json'))
        if not candidates:
            return None
        payload = _load_json(str(candidates[0]), None)
        if not isinstance(payload, dict):
            return None
        with DATA_CONSTITUTION_LOCK:
            DATA_CONSTITUTION_MANIFEST_CACHE['at'] = now_mono
            DATA_CONSTITUTION_MANIFEST_CACHE['value'] = copy.deepcopy(payload)
        return payload
    finally:
        shutil.rmtree(workdir, ignore_errors=True)

def constitution_try_auto_clear_quarantine(force: bool=False) -> bool:
    """Clear only a constitution-owned quarantine after a fresh semantic proof.

    A transient/inconsistent snapshot must not create an endless blocked-backup/error
    storm.  Safety is unchanged: no guard is cleared until live state is checked
    against the currently active immutable MEGA manifest with the normal rejection
    rules.
    """
    global DATA_CONSTITUTION_RECOVERY_LAST_ATTEMPT
    if not bool(DATA_CONSTITUTION_QUARANTINE):
        return True
    if not mega_is_configured():
        return False
    now_m = time.monotonic()
    with DATA_CONSTITUTION_LOCK:
        if not force and DATA_CONSTITUTION_RECOVERY_LAST_ATTEMPT and (now_m - float(DATA_CONSTITUTION_RECOVERY_LAST_ATTEMPT) < float(DATA_CONSTITUTION_RECOVERY_COOLDOWN_SECONDS)):
            return False
        DATA_CONSTITUTION_RECOVERY_LAST_ATTEMPT = now_m
    try:
        current = constitution_load_active_manifest_remote(force=True)
        if not isinstance(current, dict) or not current.get('generation'):
            return False
        live = constitution_semantic_manifest_from_live()
        rejection = constitution_snapshot_rejection(live, current)
        if rejection:
            try:
                runtime_event('data_constitution_quarantine_still_active', rejection, 'WARN')
            except Exception:
                pass
            return False
        constitution_clear_quarantine('automatic semantic re-verification passed')
        try:
            repair_failed = globals().get('schedule_safe_failed_task_repairs')
            if callable(repair_failed):
                repair_failed(1.0, 50)
        except Exception as exc:
            try:
                runtime_event('data_constitution_finance_repair_schedule_error', str(exc)[:500], 'WARN')
            except Exception:
                pass
        try:
            runtime_event('data_constitution_quarantine_recovered', f"records={int(live.get('total_records') or 0)} baseline={int(current.get('total_records') or 0)}", 'INFO')
        except Exception:
            pass
        return True
    except Exception as exc:
        try:
            runtime_event('data_constitution_quarantine_reverify_error', str(exc)[:500], 'WARN')
        except Exception:
            pass
        return False

def _constitution_prune_bounded_history(active_manifest: dict) -> dict:
    """v190 bounded MEGA history: keep enough rollback points, never unlimited file growth."""
    result = {'generations': 0, 'manifests': 0, 'pointer_history': 0, 'ledger': 0}
    try:
        prune = globals().get('_mega_prune_remote_history')
        if callable(prune):
            keep = max(DATA_CONSTITUTION_GENERATION_KEEP_MIN, min(48, int(os.getenv('DATA_CONSTITUTION_GENERATION_KEEP', str(DATA_CONSTITUTION_GENERATION_KEEP_MIN)) or DATA_CONSTITUTION_GENERATION_KEEP_MIN)))
            result['generations'] = int(prune(constitution_generations_dir(), 'generation_*.sqlite3.gz', keep) or 0)
            result['manifests'] = int(prune(constitution_manifests_dir(), 'generation_*.json', keep) or 0)
            result['pointer_history'] = int(prune(constitution_manifest_history_dir(), 'current_manifest_*.json', keep) or 0)
    except Exception as exc:
        try:
            log_error(f'constitution generation prune v190: {exc}')
        except Exception:
            pass
    try:
        cutoff = int((active_manifest or {}).get('previous_ledger_highwater_seq') or 0)
        finder = globals().get('_mega_find_remote_files')
        if cutoff > 0 and callable(finder):
            rows = list(finder(constitution_ledger_root(), 'ledger_*.json') or [])
            shard_root = str(globals().get('MEGA_SHARD_CHATS_ROOT_V240') or '')
            if shard_root and bool(globals().get('MEGA_SHARDED_STORAGE_V240', False)):
                try:
                    rows.extend(finder(shard_root, 'ledger_*.json') or [])
                except Exception:
                    pass
            rows = sorted(set(rows))
            removed = 0
            for remote_path in rows:
                name = os.path.basename(str(remote_path))
                m = re.match('ledger_(\\d+)_', name)
                if not m:
                    continue
                if int(m.group(1)) <= cutoff:
                    try:
                        res = _mega_run('mega-rm', [remote_path], check=False, timeout=30)
                        if res.returncode == 0:
                            removed += 1
                    except Exception:
                        pass
            result['ledger'] = removed
    except Exception as exc:
        try:
            log_error(f'constitution ledger prune v190: {exc}')
        except Exception:
            pass
    if any(result.values()):
        try:
            bot_journal('constitution_prune_v190', None, json.dumps(result, ensure_ascii=False, separators=(',', ':')))
        except Exception:
            pass
    return result

def _v240_config_binding_from_sqlite(raw_sqlite: str) -> dict:
    out = {'config_generation_v240': 0, 'config_hash_v240': '', 'config_lineage_v240': ''}
    conn = None
    try:
        conn = sqlite3.connect(str(raw_sqlite))
        row = conn.execute("SELECT v FROM meta WHERE kind='config_guard_v234' AND k='latest'").fetchone()
        cp = json.loads(row[0]) if row and row[0] else {}
        if isinstance(cp, dict):
            out['config_generation_v240'] = int(cp.get('generation') or 0)
            out['config_hash_v240'] = str(cp.get('config_hash') or '')
            out['config_lineage_v240'] = str(cp.get('storage_lineage_v239') or '')
    except Exception:
        pass
    finally:
        try:
            if conn is not None:
                conn.close()
        except Exception:
            pass
    return out

def constitution_publish_sqlite_generation(raw_sqlite: str, gz_path: str, created_at: str, *, allow_destructive: bool=False) -> dict:
    """Publish immutable generation first, then atomically move only the active pointer.

    v203 keeps the large legacy latest_bot_state.sqlite3.gz mirror OFF by default because it
    duplicates the same compressed SQLite bytes. Set MEGA_LEGACY_DB_MIRROR_ENABLED=1 only
    for temporary backward compatibility with an old runtime.
    """
    if not mega_is_configured():
        raise RuntimeError('MEGA unavailable')
    candidate = constitution_semantic_manifest_from_sqlite(raw_sqlite)
    exact = _v239_generation_exact_preflight(raw_sqlite, candidate, require_embedded=True)
    candidate = dict(exact.get('actual') or candidate)
    try:
        with open(raw_sqlite, 'rb') as _fh:
            candidate['sqlite_sha256'] = hashlib.sha256(_fh.read()).hexdigest()
        with open(gz_path, 'rb') as _fh:
            candidate['gzip_sha256'] = hashlib.sha256(_fh.read()).hexdigest()
    except Exception as _hash_exc:
        raise RuntimeError(f'v240 generation checksum preflight failed: {_hash_exc}')
    candidate.update(_v240_config_binding_from_sqlite(raw_sqlite))
    current = constitution_load_active_manifest_remote(force=True)
    rejection = '' if bool(allow_destructive) or not constitution_protection_enabled_v232() else constitution_snapshot_rejection(candidate, current)
    if rejection:
        live_rejection = 'live verification unavailable'
        try:
            live_now = constitution_semantic_manifest_from_live()
            live_rejection = constitution_snapshot_rejection(live_now, current)
        except Exception as exc:
            live_rejection = 'live verification failed: ' + str(exc)[:300]
        if not live_rejection:
            try:
                runtime_event('data_constitution_transient_snapshot_rejected', rejection, 'WARN')
            except Exception:
                pass
            raise RuntimeError('transient snapshot mismatch: ' + rejection)
        constitution_set_quarantine('snapshot rejected: ' + rejection + '; live=' + live_rejection)
        raise RuntimeError(rejection)
    stamp = re.sub('[^0-9]', '', str(created_at or now_local().isoformat(timespec='seconds')))[:20] or str(int(time.time()))
    digest = str(candidate.get('semantic_hash') or '')[:12]
    generation_name = f'generation_{stamp}_{digest}.sqlite3.gz'
    manifest_name = f'generation_{stamp}_{digest}.json'
    workdir = tempfile.mkdtemp(prefix='constitution_publish_')
    try:
        manifest_local = os.path.join(workdir, manifest_name)
        candidate.update({'generation': generation_name, 'remote_generation': constitution_generations_dir() + '/' + generation_name, 'previous_generation': str((current or {}).get('generation') or ''), 'previous_created_at': str((current or {}).get('created_at') or ''), 'previous_ledger_highwater_seq': int((current or {}).get('ledger_highwater_seq') or 0)})
        _save_json(manifest_local, candidate)
        mega_ensure_remote_path(constitution_generations_dir())
        mega_ensure_remote_path(constitution_manifests_dir())
        mega_ensure_remote_path(constitution_manifest_history_dir())
        upload_gz = os.path.join(workdir, generation_name)
        shutil.copy2(gz_path, upload_gz)
        _mega_run('mega-put', [upload_gz, constitution_generations_dir()], check=True, timeout=MEGA_TIMEOUT)
        _mega_run('mega-put', [manifest_local, constitution_manifests_dir()], check=True, timeout=MEGA_TIMEOUT)
        pointer_candidate_name = f'candidate_current_manifest_{stamp}_{digest}.json'
        pointer_local = os.path.join(workdir, pointer_candidate_name)
        _save_json(pointer_local, candidate)
        mega_ensure_remote_path(constitution_database_dir())
        _mega_run('mega-put', [pointer_local, constitution_database_dir()], check=True, timeout=MEGA_TIMEOUT)
        remote_pointer_candidate = constitution_database_dir() + '/' + pointer_candidate_name
        archive_name = f'current_manifest_{stamp}_{digest}.json'
        if not _mega_promote_remote_candidate(remote_pointer_candidate, constitution_current_manifest_remote(), history_dir=constitution_manifest_history_dir(), archive_name=archive_name):
            raise RuntimeError('cannot activate constitution current_manifest')
        if _env_bool('MEGA_LEGACY_DB_MIRROR_ENABLED', '0'):
            legacy_candidate_name = f'candidate_bot_state_{stamp}_{digest}.sqlite3.gz'
            legacy_local = os.path.join(workdir, legacy_candidate_name)
            shutil.copy2(gz_path, legacy_local)
            _mega_run('mega-put', [legacy_local, constitution_database_dir()], check=True, timeout=MEGA_TIMEOUT)
            remote_legacy_candidate = constitution_database_dir() + '/' + legacy_candidate_name
            history = constitution_database_dir() + '/history'
            mega_ensure_remote_path(history)
            archive_legacy = f'bot_state_{stamp[:14]}.sqlite3.gz'
            if not _mega_promote_remote_candidate(remote_legacy_candidate, lowram_database_remote_latest(), history_dir=history, archive_name=archive_legacy):
                log_error('[DATA CONSTITUTION] generation active, but optional legacy latest mirror update failed')
        with DATA_CONSTITUTION_LOCK:
            DATA_CONSTITUTION_MANIFEST_CACHE['at'] = time.monotonic()
            DATA_CONSTITUTION_MANIFEST_CACHE['value'] = copy.deepcopy(candidate)
        try:
            SQLITE.set_meta('data_constitution', 'active_manifest', candidate)
        except Exception:
            pass
        try:
            _constitution_prune_bounded_history(candidate)
        except Exception:
            pass
        return candidate
    finally:
        shutil.rmtree(workdir, ignore_errors=True)

def config_guard_reanchor_after_manual_restore_v241(reason: str='manual_restore') -> dict:
    """Make the just-restored configuration the newest durable checkpoint.

    A restored SQLite may contain an older config generation number than config
    checkpoints already present remotely.  If we publish the SQLite first, the
    next deploy can correctly restore that SQLite and then incorrectly overlay a
    newer *pre-restore* config checkpoint.  v241 reserves a generation greater
    than both local and remote, syncs it synchronously, and only then allows the
    full SQLite generation to be published.
    """
    local_gen = 0
    remote_gen = 0
    try:
        latest = config_guard_latest_local_v234() or {}
        local_gen = max(int(latest.get('generation') or 0), int(SQLITE.get_meta(CONFIG_GUARD_META_KIND_V234, 'generation', 0) or 0), int((data.get('_global_settings') or {}).get(CONFIG_GUARD_GENERATION_KEY_V234) or 0))
    except Exception:
        local_gen = 0
    try:
        for remote in (_v234_remote_config_rows(max(5, int(CONFIG_GUARD_REMOTE_KEEP_V234))) or [])[:5]:
            cp = _v234_load_remote_checkpoint(remote) or {}
            remote_gen = max(remote_gen, int(cp.get('generation') or 0))
    except Exception:
        remote_gen = 0
    next_gen = max(local_gen, remote_gen) + 1
    cp = config_guard_accept_current_v234('manual_restore_reanchor_v241:' + str(reason), force_generation=next_gen)
    synced = False
    sync_error = ''
    try:
        sync_fn = globals().get('config_guard_sync_remote_v234')
        synced = bool(callable(sync_fn) and sync_fn(recovery_write=True))
    except Exception as exc:
        sync_error = str(exc)[:300]
        synced = False
    if not synced:
        SQLITE.set_meta('restore_control_v240', 'config_remote_pending', {'at': now_local().isoformat(timespec='microseconds'), 'reason': str(reason), 'generation': int(cp.get('generation') or 0), 'config_hash': str(cp.get('config_hash') or ''), 'lineage': str(cp.get('storage_lineage_v239') or ''), 'error': sync_error})
        try:
            runtime_event('config_restore_remote_pending_v240', f"gen={cp.get('generation')}; {sync_error or 'no durable backend'}", 'WARN')
        except Exception:
            pass
    save_data(data, full=True)
    try:
        bot_journal('config_restore_reanchored_v241', int(OWNER_ID or 0) or None, f'reason={reason}; local={local_gen}; remote={remote_gen}; new={next_gen}')
    except Exception:
        pass
    return cp

def constitution_reanchor_after_manual_restore(reason: str='manual_restore') -> dict:
    """Explicit owner restore checkpoint. pre_restore must already exist before this is called."""
    lineage = _v239_rotate_storage_lineage(reason)
    config_cp = config_guard_reanchor_after_manual_restore_v241(reason)
    live = constitution_semantic_manifest_from_live()
    seq = int(live.get('integrity_seq') or 0)
    checkpoint = {'kind': 'telegram_bot_data_constitution_restore_checkpoint', 'schema_version': DATA_CONSTITUTION_SCHEMA, 'bot_version': VERSION, 'reason': str(reason), 'at': now_local().isoformat(timespec='microseconds'), 'integrity_seq': seq, 'semantic_manifest': live}
    checkpoint['event_hash'] = hashlib.sha256(json.dumps(checkpoint, ensure_ascii=False, sort_keys=True, separators=(',', ':'), default=str).encode('utf-8')).hexdigest()
    tg_primary_fn = globals().get('telegram_durable_primary_v234')
    tg_available_fn = globals().get('telegram_durable_available_v237_1')
    _tg_recovery_fallback = bool(globals().get('_V240_RECOVERY_AUTHORITY_ACTIVE', False)) and (not mega_is_configured()) and callable(tg_available_fn) and bool(tg_available_fn())
    if callable(tg_primary_fn) and bool(tg_primary_fn()) or _tg_recovery_fallback:
        checkpoint_fn = globals().get('telegram_constitution_restore_checkpoint_v234')
        if not callable(checkpoint_fn) or not bool(checkpoint_fn(checkpoint)):
            raise RuntimeError('Telegram Data Constitution restore checkpoint failed')
        high = {'seq': seq, 'hash': checkpoint['event_hash'], 'integrity_hash': str(live.get('integrity_anchor') or ''), 'at': checkpoint['at'], 'remote': 'telegram-durable-head', 'restore_checkpoint': True}
        SQLITE.set_meta('data_constitution', 'ledger_highwater', high)
        try:
            _root_settings()['data_constitution_ledger_highwater'] = copy.deepcopy(high)
        except Exception:
            pass
        try:
            save_data(data, full=True)
        except Exception:
            pass
        snap_fn = globals().get('telegram_upload_sqlite_snapshot_v234')
        if not callable(snap_fn) or not bool(snap_fn(force=True)):
            raise RuntimeError('Telegram Data Constitution SQLite generation failed')
        try:
            init_delta = globals().get('initialize_delta_baseline')
            if callable(init_delta):
                init_delta(data)
            lock = globals().get('_delta_state_lock')
            pending = globals().get('_delta_pending_chats')
            generations = globals().get('_delta_chat_generation')
            if lock is not None:
                with lock:
                    if hasattr(pending, 'clear'):
                        pending.clear()
                    if hasattr(generations, 'clear'):
                        generations.clear()
            sched = globals().get('DELAYED_SCHEDULER')
            if sched is not None:
                try:
                    sched.cancel('telegram-delta-batch-v234')
                except Exception:
                    pass
        except Exception as _delta_reanchor_exc:
            constitution_set_quarantine(f'delta baseline re-anchor failed after Telegram restore: {_delta_reanchor_exc}')
            raise
        constitution_clear_quarantine('manual restore checkpoint verified in Telegram durable')
        try:
            _clear_restore_guard()
        except Exception:
            pass
        active_tg = {'backend': 'telegram', 'generation': (telegram_durable_bootstrap_v234(False) or {}).get('generation')}
        try:
            state = globals().get('_RUNTIME_STATE')
            if isinstance(state, dict):
                state['restore_attempted'] = True
                state['restore_ok'] = True
                state['restore_detail'] = f"manual exact restore v239 Telegram; lineage={lineage}; generation={active_tg.get('generation', '')}"
        except Exception:
            pass
        return {'checkpoint': checkpoint, 'config_checkpoint': config_cp, 'active': active_tg, 'lineage': lineage}
    workdir = tempfile.mkdtemp(prefix='constitution_restore_checkpoint_')
    try:
        remote_dir = constitution_ledger_root() + '/checkpoints'
        mega_ensure_remote_path(remote_dir)
        name = f"restore_checkpoint_{re.sub('[^0-9]', '', checkpoint['at'])[:20]}_{checkpoint['event_hash'][:16]}.json"
        local = os.path.join(workdir, name)
        _save_json(local, checkpoint)
        _mega_run('mega-put', [local, remote_dir], check=True, timeout=MEGA_TIMEOUT)
        high = {'seq': seq, 'hash': checkpoint['event_hash'], 'integrity_hash': str(live.get('integrity_anchor') or ''), 'at': checkpoint['at'], 'remote': remote_dir + '/' + name, 'restore_checkpoint': True}
        SQLITE.set_meta('data_constitution', 'ledger_highwater', high)
        try:
            _root_settings()['data_constitution_ledger_highwater'] = copy.deepcopy(high)
        except Exception:
            pass
        try:
            save_data(data, full=True)
        except Exception:
            pass
        with data_lock:
            try:
                flush_fn = globals().get('_lowram_flush_all_hot')
                if callable(flush_fn):
                    flush_fn(evict=False)
            except Exception:
                pass
            embedded = constitution_semantic_manifest_from_live()
            embedded['snapshot_created_at'] = checkpoint['at']
            embedded['restore_reason_v239'] = str(reason or 'manual_restore')
            embedded['storage_lineage_v239'] = lineage
            SQLITE.set_meta('data_constitution_snapshot', 'main', embedded)
            SQLITE.set_meta('restore_control_v239', 'last_exact_restore', {'at': checkpoint['at'], 'reason': str(reason or 'manual_restore'), 'lineage': lineage, 'config_generation': int((config_cp or {}).get('generation') or 0)})
            raw = os.path.join(workdir, 'restored_state.sqlite3')
            gz = raw + '.gz'
            SQLITE.backup_to(raw)
        exact = _v239_generation_exact_preflight(raw, require_embedded=True)
        _lowram_gzip_file(raw, gz)
        active = constitution_publish_sqlite_generation(raw, gz, checkpoint['at'], allow_destructive=True)
        _v239_generation_exact_preflight(raw, active, require_embedded=True)
        try:
            init_delta = globals().get('initialize_delta_baseline')
            if callable(init_delta):
                init_delta(data)
            lock = globals().get('_delta_state_lock')
            pending = globals().get('_delta_pending_chats')
            generations = globals().get('_delta_chat_generation')
            if lock is not None:
                with lock:
                    if hasattr(pending, 'clear'):
                        pending.clear()
                    if hasattr(generations, 'clear'):
                        generations.clear()
            else:
                if hasattr(pending, 'clear'):
                    pending.clear()
                if hasattr(generations, 'clear'):
                    generations.clear()
            sched = globals().get('DELAYED_SCHEDULER')
            if sched is not None:
                try:
                    sched.cancel('mega-delta-batch-v90')
                except Exception:
                    pass
            try:
                bot_journal('constitution_delta_reanchored_v189', int(OWNER_ID or 0), f"reason={reason}; records={live.get('total_records', 0)}")
            except Exception:
                pass
        except Exception as _delta_reanchor_exc:
            constitution_set_quarantine(f'delta baseline re-anchor failed after restore: {_delta_reanchor_exc}')
            raise
        constitution_clear_quarantine('manual restore checkpoint verified')
        try:
            _clear_restore_guard()
        except Exception:
            pass
        try:
            state = globals().get('_RUNTIME_STATE')
            if isinstance(state, dict):
                state['restore_attempted'] = True
                state['restore_ok'] = True
                state['restore_detail'] = f"manual exact restore v239; lineage={lineage}; generation={active.get('generation', '')}"
        except Exception:
            pass
        return {'checkpoint': checkpoint, 'config_checkpoint': config_cp, 'active': active, 'lineage': lineage, 'exact_preflight': exact}
    finally:
        shutil.rmtree(workdir, ignore_errors=True)

def constitution_download_active_generation(workdir: str) -> tuple[str | None, dict | None, str]:
    manifest = constitution_load_active_manifest_remote(force=True)
    if not manifest:
        return (None, None, 'no constitution manifest')
    remote = str(manifest.get('remote_generation') or '')
    if not remote:
        return (None, manifest, 'manifest has no remote_generation')
    res = _mega_run('mega-get', [remote, workdir], check=False, timeout=max(float(MEGA_TIMEOUT), 180.0))
    if res.returncode != 0:
        return (None, manifest, 'active generation download failed')
    candidates = list(Path(workdir).rglob(os.path.basename(remote))) or list(Path(workdir).rglob('generation_*.sqlite3.gz'))
    return (str(candidates[0]) if candidates else None, manifest, 'constitution generation')

def _v235_manifest_created_ts(manifest: dict | None) -> float:
    try:
        return float(_parse_iso_timestamp(str((manifest or {}).get('created_at') or '')))
    except Exception:
        return 0.0

def _v235_download_generation_manifest(remote: str) -> dict:
    work = tempfile.mkdtemp(prefix='v235_manifest_get_')
    try:
        res = _mega_run('mega-get', [str(remote), work], check=False, timeout=max(float(MEGA_TIMEOUT), 90.0))
        if res.returncode != 0:
            return {}
        found = list(Path(work).rglob(os.path.basename(str(remote)))) or list(Path(work).rglob('generation_*.json'))
        if not found:
            return {}
        row = _load_json(str(found[0]), None)
        return row if isinstance(row, dict) else {}
    except Exception:
        return {}
    finally:
        shutil.rmtree(work, ignore_errors=True)

def _v235_recent_generation_manifests(limit: int=10) -> list[dict]:
    rows = []
    finder = globals().get('_mega_find_remote_files')
    if not callable(finder):
        return rows
    try:
        paths = finder(constitution_manifests_dir(), 'generation_*.json', limit=max(3, int(limit))) or []
    except Exception:
        paths = []
    seen = set()
    for remote in paths:
        row = _v235_download_generation_manifest(str(remote))
        generation = str((row or {}).get('generation') or '')
        if not generation or generation in seen:
            continue
        seen.add(generation)
        row = dict(row)
        row['_manifest_remote_v235'] = str(remote)
        rows.append(row)
    rows.sort(key=lambda x: (_v235_manifest_created_ts(x), str(x.get('generation') or '')), reverse=True)
    return rows

def _v235_generation_descends_from(candidate: dict, ancestor_generation: str, manifest_map: dict[str, dict]) -> bool:
    target = str(ancestor_generation or '')
    if not target:
        return True
    cur = dict(candidate or {})
    visited = set()
    for _ in range(24):
        gen = str(cur.get('generation') or '')
        if not gen or gen in visited:
            return False
        visited.add(gen)
        if gen == target:
            return True
        prev = str(cur.get('previous_generation') or '')
        if prev == target:
            return True
        cur = dict(manifest_map.get(prev) or {})
        if not cur:
            return False
    return False

def _v235_download_and_validate_generation(manifest: dict, workdir: str, label: str) -> tuple[str | None, str]:
    remote = str((manifest or {}).get('remote_generation') or '')
    if not remote:
        return (None, 'manifest has no remote_generation')
    sub = os.path.join(workdir, 'v235_' + re.sub('[^A-Za-z0-9_.-]', '_', str(manifest.get('generation') or label))[:100])
    os.makedirs(sub, exist_ok=True)
    try:
        res = _mega_run('mega-get', [remote, sub], check=False, timeout=max(float(MEGA_TIMEOUT), 180.0))
        if res.returncode != 0:
            return (None, 'generation download failed')
        found = list(Path(sub).rglob(os.path.basename(remote))) or list(Path(sub).rglob('generation_*.sqlite3.gz'))
        if not found:
            return (None, 'downloaded generation not found')
        gz = str(found[0])
        raw = os.path.join(sub, 'verify.sqlite3')
        _lowram_gunzip_file(gz, raw)
        conn = sqlite3.connect(raw)
        try:
            check = conn.execute('PRAGMA quick_check').fetchone()
            if not check or str(check[0]).lower() != 'ok':
                return (None, f'SQLite quick_check failed: {check}')
        finally:
            conn.close()
        semantic_fn = globals().get('constitution_semantic_manifest_from_sqlite')
        if callable(semantic_fn):
            semantic = semantic_fn(raw) or {}
            if int(semantic.get('total_records') or 0) != int((manifest or {}).get('total_records') or 0):
                return (None, f"semantic records mismatch {semantic.get('total_records')} != {manifest.get('total_records')}")
            if int(semantic.get('integrity_seq') or 0) != int((manifest or {}).get('integrity_seq') or 0):
                return (None, f"integrity_seq mismatch {semantic.get('integrity_seq')} != {manifest.get('integrity_seq')}")
            for cid, old in ((manifest or {}).get('chats') or {}).items():
                got = (semantic.get('chats') or {}).get(str(cid)) or {}
                if int(got.get('record_count') or 0) != int((old or {}).get('record_count') or 0):
                    return (None, f'chat {cid} record mismatch')
        return (gz, 'ok')
    except Exception as exc:
        return (None, str(exc)[:300])

def _canon_constitution_download_best_boot_generation_v235__001(workdir: str) -> tuple[str | None, dict | None, str]:
    """Choose the freshest trustworthy immutable generation for boot.

    Healthy current_manifest remains the normal source.  Newer orphan generations are
    eligible only when their manifest lineage descends from current_manifest (publish
    succeeded but pointer promotion was interrupted).  If the active generation itself
    is missing/corrupt, recent immutable generations become a newest-first fallback pool.
    """
    active = constitution_load_active_manifest_remote(force=True) or {}
    recent = _v235_recent_generation_manifests(10)
    by_gen = {str(x.get('generation') or ''): x for x in recent if str(x.get('generation') or '')}
    active_gen = str(active.get('generation') or '')
    if active_gen:
        by_gen.setdefault(active_gen, dict(active))
    active_gz = None
    active_err = 'no active manifest'
    if active_gen:
        active_gz, active_err = _v235_download_and_validate_generation(active, workdir, 'active')
    if active_gz:
        newer = [x for x in recent if _v235_manifest_created_ts(x) > _v235_manifest_created_ts(active)]
        for candidate in newer:
            if not _v235_generation_descends_from(candidate, active_gen, by_gen):
                continue
            gz, err = _v235_download_and_validate_generation(candidate, workdir, 'newer')
            if gz:
                try:
                    runtime_event('boot_generation_newer_descendant_v235', f"active={active_gen}; selected={candidate.get('generation')}", 'WARN')
                except Exception:
                    pass
                return (gz, candidate, 'newer verified constitution generation (pointer lag recovery v235)')
        return (active_gz, active, 'constitution active generation verified v235')
    for candidate in recent:
        gz, err = _v235_download_and_validate_generation(candidate, workdir, 'fallback')
        if gz:
            try:
                runtime_event('boot_generation_history_fallback_v235', f"active={active_gen or 'none'}; error={active_err}; selected={candidate.get('generation')}", 'WARN')
            except Exception:
                pass
            return (gz, candidate, 'recent verified generation history fallback v235')
    return (None, active or None, f'no verified generation; active_error={active_err}')

def constitution_boot_verify_after_restore() -> dict:
    """Fast semantic boot verification without a mandatory MEGA manifest round-trip.

    v190 snapshots embed their semantic manifest inside SQLite. Older protected snapshots
    normally contain the previous active manifest in SQLite metadata. Either local baseline
    is enough to prove that the restored+delta state did not silently lose history. Remote
    ``current_manifest.json`` remains the fallback and is reconciled by the next background
    full snapshot, keeping READY independent from MEGA metadata latency.
    """
    global DATA_CONSTITUTION_LAST_VERIFY
    live = constitution_semantic_manifest_from_live()
    local_baseline = {}
    baseline_source = ''
    try:
        local_baseline = SQLITE.get_meta('data_constitution_snapshot', 'main', {}) or {}
        if isinstance(local_baseline, dict) and local_baseline.get('kind'):
            baseline_source = 'embedded_snapshot'
        else:
            local_baseline = SQLITE.get_meta('data_constitution', 'active_manifest', {}) or {}
            if isinstance(local_baseline, dict) and local_baseline.get('kind'):
                baseline_source = 'sqlite_active_manifest'
    except Exception:
        local_baseline = {}
    if isinstance(local_baseline, dict) and local_baseline.get('kind') == 'telegram_bot_data_constitution_manifest':
        rejection = constitution_snapshot_rejection(live, local_baseline)
        protection = constitution_protection_enabled_v232()
        ok = not bool(rejection) or not protection
        result = {'ok': ok, 'mode': 'fast_local_verify', 'baseline_source': baseline_source, 'live': live, 'current': local_baseline, 'reason': rejection, 'protection_enabled': protection, 'warning_only': bool(rejection and (not protection))}
        DATA_CONSTITUTION_LAST_VERIFY = result
        if not ok:
            constitution_set_quarantine('BOOT local semantic verification failed: ' + rejection)
        else:
            with DATA_CONSTITUTION_LOCK:
                globals()['DATA_CONSTITUTION_QUARANTINE'] = False
                globals()['DATA_CONSTITUTION_REASON'] = ''
        try:
            runtime_event('data_constitution_boot_verify', f"ok={ok}; mode=fast_local; source={baseline_source}; records={live.get('total_records')}; baseline={local_baseline.get('total_records')}; {rejection}", 'INFO' if ok else 'ERROR')
        except Exception:
            pass
        return result
    tg_primary_fn = globals().get('telegram_durable_primary_v234')
    if callable(tg_primary_fn) and bool(tg_primary_fn()):
        try:
            genesis_fn = globals().get('telegram_constitution_bootstrap_genesis_v236')
            if not callable(genesis_fn):
                raise RuntimeError('Telegram constitution genesis helper unavailable')
            genesis = genesis_fn(live)
            live = constitution_semantic_manifest_from_live()
            result = {'ok': True, 'mode': 'telegram_bootstrap', 'live': live, 'genesis': genesis, 'active': genesis.get('active'), 'reason': 'constitution genesis + stable Telegram SQLite snapshot created'}
            DATA_CONSTITUTION_LAST_VERIFY = result
            with DATA_CONSTITUTION_LOCK:
                globals()['DATA_CONSTITUTION_QUARANTINE'] = False
                globals()['DATA_CONSTITUTION_REASON'] = ''
            return result
        except Exception as exc:
            constitution_set_quarantine(f'Telegram constitution genesis failed: {exc}')
            result = {'ok': False, 'mode': 'telegram_bootstrap', 'live': live, 'reason': str(exc)}
            DATA_CONSTITUTION_LAST_VERIFY = result
            return result
    gate = globals().get('external_access_allowed_v233')
    if callable(gate) and (not gate('mega')):
        result = {'ok': True, 'mode': 'local_only_v233', 'live': live, 'reason': 'remote constitution verification paused by Render+Telegram-only mode', 'warning_only': True}
        DATA_CONSTITUTION_LAST_VERIFY = result
        try:
            runtime_event('data_constitution_boot_verify', f"ok=True; mode=local_only_v233; records={live.get('total_records')}", 'INFO')
        except Exception:
            pass
        return result
    current = constitution_load_active_manifest_remote(force=True)
    if not current:
        try:
            genesis = constitution_bootstrap_ledger_genesis()
            live = constitution_semantic_manifest_from_live()
            snapshot_ok = bool(mega_upload_latest_database_backup(force=True))
            active_now = constitution_load_active_manifest_remote(force=True) if snapshot_ok else None
            if not snapshot_ok or not active_now:
                raise RuntimeError('genesis created but first immutable generation was not activated')
            result = {'ok': True, 'mode': 'bootstrap', 'live': live, 'genesis': genesis, 'active': active_now, 'reason': 'constitution genesis + first generation created'}
        except Exception as exc:
            constitution_set_quarantine(f'constitution genesis failed: {exc}')
            result = {'ok': False, 'mode': 'bootstrap', 'live': live, 'reason': str(exc)}
        DATA_CONSTITUTION_LAST_VERIFY = result
        return result
    rejection = constitution_snapshot_rejection(live, current)
    protection = constitution_protection_enabled_v232()
    ok = not bool(rejection) or not protection
    result = {'ok': ok, 'mode': 'remote_fallback_verify', 'live': live, 'current': current, 'reason': rejection, 'protection_enabled': protection, 'warning_only': bool(rejection and (not protection))}
    DATA_CONSTITUTION_LAST_VERIFY = result
    if not ok:
        constitution_set_quarantine('BOOT semantic verification failed: ' + rejection)
    else:
        with DATA_CONSTITUTION_LOCK:
            globals()['DATA_CONSTITUTION_QUARANTINE'] = False
            globals()['DATA_CONSTITUTION_REASON'] = ''
    try:
        runtime_event('data_constitution_boot_verify', f"ok={ok}; mode=remote_fallback; records={live.get('total_records')}; active={current.get('total_records')}; {rejection}", 'INFO' if ok else 'ERROR')
    except Exception:
        pass
    return result
_CONSTITUTION_LEDGER_ASYNC_LOCK = threading.RLock()
_CONSTITUTION_LEDGER_ASYNC_STATE = {}

def constitution_ledger_tokens_ready(tokens) -> tuple[bool, str]:
    """Used by the durable finalizer: a task stays recoverable until its ledger witness is in MEGA."""
    vals = [str(x) for x in tokens or [] if str(x or '').strip()]
    if not vals:
        return (True, '')
    with _CONSTITUTION_LEDGER_ASYNC_LOCK:
        states = {token: str((_CONSTITUTION_LEDGER_ASYNC_STATE.get(token) or {}).get('state') or 'pending') for token in vals}
    failed = [k for k, v in states.items() if v == 'failed']
    pending = [k for k, v in states.items() if v not in {'done', 'failed'}]
    if failed:
        return (False, 'failed:' + ','.join(failed[:4]))
    if pending:
        return (False, 'pending:' + ','.join(pending[:4]))
    return (True, '')

def _constitution_upload_ledger_event(token: str, event: dict, name: str, remote_dir: str) -> bool:
    workdir = tempfile.mkdtemp(prefix='constitution_ledger_async_')
    local = os.path.join(workdir, name)
    try:
        with open(local, 'w', encoding='utf-8') as fh:
            json.dump(event, fh, ensure_ascii=False, separators=(',', ':'), default=str)
        mega_ensure_remote_path(remote_dir)
        _mega_run('mega-put', [local, remote_dir], check=True, timeout=MEGA_TIMEOUT)
        high = {'seq': int(event.get('seq') or 0), 'hash': str(event.get('event_hash') or ''), 'integrity_hash': str(event.get('integrity_hash') or ''), 'at': str(event.get('at') or ''), 'remote': remote_dir + '/' + name}
        with DATA_CONSTITUTION_LEDGER_LOCK:
            previous = SQLITE.get_meta('data_constitution', 'ledger_highwater', {}) or {}
            if int(high.get('seq') or 0) >= int((previous or {}).get('seq') or 0):
                SQLITE.set_meta('data_constitution', 'ledger_highwater', high)
                try:
                    _root_settings()['data_constitution_ledger_highwater'] = copy.deepcopy(high)
                    _root_save_coalesced('constitution_ledger_highwater', 0.5)
                except Exception:
                    pass
        SQLITE.set_meta('data_constitution_pending', name, {'done': True, 'at': event.get('at')})
        with _CONSTITUTION_LEDGER_ASYNC_LOCK:
            _CONSTITUTION_LEDGER_ASYNC_STATE[token] = {'state': 'done', 'at': time.monotonic()}
        try:
            bot_journal('constitution_ledger_async_done_v190', int(event.get('chat_id') or 0), f"seq={event.get('seq')}")
        except Exception:
            pass
        return True
    except Exception as exc:
        with _CONSTITUTION_LEDGER_ASYNC_LOCK:
            _CONSTITUTION_LEDGER_ASYNC_STATE[token] = {'state': 'failed', 'error': str(exc)[:300], 'at': time.monotonic()}
        constitution_set_quarantine(f"immutable finance ledger write failed seq={event.get('seq')}: {exc}")
        try:
            log_error(f'[DATA CONSTITUTION LEDGER] {exc}')
        except Exception:
            pass
        return False
    finally:
        shutil.rmtree(workdir, ignore_errors=True)

def constitution_ledger_append(chat_id: int, action: str, record: dict | None, details: dict | None, integrity_hash: str, seq: int) -> bool:
    """v190 immutable ledger with v233 explicit local-only queue.

    In Render+Telegram-only mode the business mutation is allowed and the immutable event is
    retained in local SQLite as pending. Once external access is re-enabled, v233 flushes those
    events to MEGA in sequence before normal backup/recovery scheduling resumes.
    """
    event = {'kind': 'telegram_bot_finance_immutable_ledger', 'schema_version': DATA_CONSTITUTION_SCHEMA, 'bot_version': VERSION, 'seq': int(seq), 'chat_id': int(chat_id), 'action': str(action), 'record': _constitution_json_clone(record or {}), 'details': _constitution_json_clone(details or {}), 'integrity_hash': str(integrity_hash or ''), 'at': now_local().isoformat(timespec='microseconds')}
    event['event_hash'] = hashlib.sha256(json.dumps(event, ensure_ascii=False, sort_keys=True, separators=(',', ':'), default=str).encode('utf-8')).hexdigest()
    day = event['at'][:10].replace('-', '/')
    remote_dir = constitution_ledger_root(int(chat_id)) + '/' + day
    name = f"ledger_{int(seq):010d}_{int(chat_id)}_{event['event_hash'][:16]}.json"
    token = name
    SQLITE.set_meta('data_constitution_pending', name, event)
    try:
        _constitution_advance_local_ledger_highwater_v260(event, name)
    except Exception as _v260_highwater_exc:
        try: log_error(f'[DATA CONSTITUTION] local highwater v260: {_v260_highwater_exc}')
        except Exception: pass
    tg_primary_fn = globals().get('telegram_durable_primary_v234')
    if callable(tg_primary_fn) and bool(tg_primary_fn()):
        with _CONSTITUTION_LEDGER_ASYNC_LOCK:
            _CONSTITUTION_LEDGER_ASYNC_STATE[token] = {'state': 'pending', 'seq': int(seq), 'at': time.monotonic(), 'backend': 'telegram'}
        try:
            raw_ctx = getattr(globals().get('_TELEGRAM_UPDATE_CONTEXT'), 'value', None)
            if isinstance(raw_ctx, dict):
                raw_ctx.setdefault('constitution_ledger_tokens', []).append(token)
        except Exception:
            pass
        uploader = globals().get('telegram_constitution_ledger_upload_v234')
        if not callable(uploader):
            try:
                log_error('[DATA CONSTITUTION] Telegram ledger uploader unavailable')
            except Exception:
                pass
            return False
        pool = globals().get('RECOVERY_TASK_POOL')
        if pool is not None:
            try:
                if pool.submit_unique(f'constitution-ledger-tg:{token}', uploader, token, event, name, 0):
                    return True
            except Exception:
                pass
        return bool(uploader(token, event, name, 0))
    gate = globals().get('external_access_allowed_v233')
    if callable(gate) and (not gate('mega')):
        with _CONSTITUTION_LEDGER_ASYNC_LOCK:
            _CONSTITUTION_LEDGER_ASYNC_STATE[token] = {'state': 'local_only', 'seq': int(seq), 'at': time.monotonic()}
        try:
            bot_journal('constitution_ledger_local_only_v233', int(chat_id), f'seq={int(seq)}; queued={name}')
        except Exception:
            pass
        return True
    if not mega_is_configured():
        constitution_set_quarantine('finance ledger unavailable: MEGA is not configured')
        return False
    ctx = {}
    try:
        fn = globals().get('_current_telegram_update_context')
        if callable(fn):
            ctx = fn() or {}
    except Exception:
        ctx = {}
    update_id = ctx.get('update_id')
    durable_state = ''
    try:
        state_fn = globals().get('mega_task_known_state')
        if update_id is not None and callable(state_fn):
            durable_state = str(state_fn(update_id) or '')
    except Exception:
        durable_state = ''
    if update_id is not None and durable_state in {'pending', 'running'}:
        with _CONSTITUTION_LEDGER_ASYNC_LOCK:
            _CONSTITUTION_LEDGER_ASYNC_STATE[token] = {'state': 'pending', 'seq': int(seq), 'at': time.monotonic()}
        try:
            raw_ctx = getattr(globals().get('_TELEGRAM_UPDATE_CONTEXT'), 'value', None)
            if isinstance(raw_ctx, dict):
                raw_ctx.setdefault('constitution_ledger_tokens', []).append(token)
        except Exception:
            pass
        pool = globals().get('RECOVERY_TASK_POOL')
        if pool is not None:
            try:
                if pool.submit_unique(f'constitution-ledger:{token}', _constitution_upload_ledger_event, token, event, name, remote_dir):
                    return True
            except Exception:
                pass
    with _CONSTITUTION_LEDGER_ASYNC_LOCK:
        _CONSTITUTION_LEDGER_ASYNC_STATE[token] = {'state': 'pending', 'seq': int(seq), 'at': time.monotonic()}
    return bool(_constitution_upload_ledger_event(token, event, name, remote_dir))

def constitution_flush_local_only_ledger_v233(limit: int=5000) -> dict:
    """Upload locally queued immutable ledger events after the master external gate is reopened."""
    gate = globals().get('external_access_allowed_v233')
    if callable(gate) and (not gate('mega')):
        return {'ok': False, 'reason': 'external_local_only', 'uploaded': 0, 'pending': 0}
    rows = []
    try:
        with SQLITE.lock:
            dbrows = SQLITE.conn.execute("SELECT k,v FROM meta WHERE kind='data_constitution_pending'").fetchall()
        for row in dbrows:
            try:
                key = str(row[0])
                value = json.loads(row[1]) if isinstance(row[1], str) else row[1]
            except Exception:
                continue
            if not isinstance(value, dict) or value.get('done') is True or value.get('kind') != 'telegram_bot_finance_immutable_ledger':
                continue
            rows.append((int(value.get('seq') or 0), key, value))
    except Exception as exc:
        return {'ok': False, 'reason': str(exc)[:300], 'uploaded': 0, 'pending': 0}
    rows = sorted(rows, key=lambda x: (x[0], x[1]))[:max(1, int(limit))]
    uploaded = 0
    for _seq, name, event in rows:
        day = str(event.get('at') or now_local().isoformat(timespec='microseconds'))[:10].replace('-', '/')
        remote_dir = constitution_ledger_root(int(event.get('chat_id') or 0)) + '/' + day
        if not _constitution_upload_ledger_event(name, event, name, remote_dir):
            return {'ok': False, 'reason': f'upload_failed:{name}', 'uploaded': uploaded, 'pending': len(rows) - uploaded}
        uploaded += 1
    try:
        bot_journal('constitution_ledger_resume_flush_v233', int(OWNER_ID or 0) or None, f'uploaded={uploaded}; scanned={len(rows)}')
    except Exception:
        pass
    return {'ok': True, 'uploaded': uploaded, 'pending': max(0, len(rows) - uploaded)}

def constitution_status_text() -> str:
    active = constitution_load_active_manifest_remote(force=False) or {}
    live = constitution_semantic_manifest_from_live()
    protection = constitution_protection_enabled_v232()
    loss_guard = constitution_loss_guard_enabled_v255()
    own_quarantine = bool(DATA_CONSTITUTION_QUARANTINE)
    return f"🏛 КОНСТИТУЦИЯ ДАННЫХ · выс-262\nЗащита потери записей: {('✅ ВКЛ' if loss_guard else '⬜ ВЫКЛ')} (по умолчанию ВЫКЛ)\nБазовая целостность: {('✅ ВКЛ' if protection else '⬜ ВЫКЛ')}\nПроверка: {('⚠️ ТРЕБУЕТ ВНИМАНИЯ' if own_quarantine else '✅ НОРМА')}\nФинансовые операции: ✅ НЕ БЛОКИРУЮТСЯ\nCanonical snapshot: {('⛔ не продвигается' if own_quarantine and protection else '✅ разрешён')}\nПричина: {DATA_CONSTITUTION_REASON or DATA_CONSTITUTION_LAST_WARNING_V232 or '—'}\nLive finance records: {live.get('total_records', 0)}\nActive generation records: {active.get('total_records', '—')}\nIntegrity seq: {live.get('integrity_seq', 0)}\nLedger highwater: {live.get('ledger_highwater_seq', 0)}\nActive generation: {active.get('generation', '—')}\nMEGA root: {constitution_root()}"

def constitution_control_keyboard_v232():
    kb = types.InlineKeyboardMarkup()
    kb.row(IB('✅ Продолжить работу', callback_data='v232:constitution:continue'))
    kb.row(IB('🔄 Перепроверить данные', callback_data='v232:constitution:recheck'))
    kb.row(IB('⚠️ Принять текущее состояние', callback_data='v232:constitution:accept'))
    kb.row(IB('🛡 Снять текущий карантин', callback_data='v232:constitution:clear'))
    kb.row(IB(('✅ ВКЛ' if constitution_loss_guard_enabled_v255() else '⬜ ВЫКЛ') + ' · Защита потери записей', callback_data='v255:constitution:loss_toggle'))
    kb.row(IB(('✅ ВКЛ' if constitution_protection_enabled_v232() else '⬜ ВЫКЛ') + ' · Базовая Data Constitution', callback_data='v232:constitution:toggle'))
    kb.row(IB('❌ Закрыть', callback_data='info_close'))
    return kb

def _constitution_render_control_v232(call):
    text = constitution_status_text()
    kb = constitution_control_keyboard_v232()
    try:
        safe_edit(bot, call, window_mark(text, 'Ф233'), reply_markup=kb)
    except Exception:
        try:
            bot.edit_message_text(window_mark(text, 'Ф233'), chat_id=int(call.message.chat.id), message_id=int(call.message.message_id), reply_markup=kb)
        except Exception:
            pass

def v232_constitution_callback_final(call, resolved: str) -> bool:
    raw = str(resolved or '')
    if not raw.startswith('v232:constitution:'):
        return False
    try:
        cid = int(call.message.chat.id)
        uid = int(getattr(getattr(call, 'from_user', None), 'id', 0) or 0)
    except Exception:
        return True
    if cid != int(OWNER_ID or 0) or uid != int(OWNER_ID or 0):
        try:
            bot.answer_callback_query(call.id, 'Только основной владелец.', show_alert=True)
        except Exception:
            pass
        return True
    action = raw.rsplit(':', 1)[-1]
    try:
        bot.answer_callback_query(call.id)
    except Exception:
        pass
    if action == 'continue':
        constitution_continue_work_v232()
        try:
            bot_journal('data_constitution_owner_continue_v232', cid, 'finance_work=allowed; canonical_guard=kept')
        except Exception:
            pass
    elif action == 'recheck':
        ok = constitution_try_auto_clear_quarantine(force=True)
        try:
            bot_journal('data_constitution_owner_recheck_v232', cid, f'ok={int(bool(ok))}')
        except Exception:
            pass
    elif action == 'accept':
        ok = constitution_accept_current_state_v232('owner_accept_current_v232')
        try:
            bot_journal('data_constitution_owner_accept_v232', cid, f'ok={int(bool(ok))}', 'INFO' if ok else 'ERROR')
        except Exception:
            pass
    elif action == 'clear':
        constitution_clear_quarantine('owner manual clear v232')
        constitution_continue_work_v232()
        try:
            bot_journal('data_constitution_owner_clear_v232', cid, 'cleared=1')
        except Exception:
            pass
    elif action == 'toggle':
        enabled = set_constitution_protection_v232(not constitution_protection_enabled_v232())
        try:
            bot_journal('data_constitution_owner_toggle_v232', cid, f'enabled={int(enabled)}')
        except Exception:
            pass
    _constitution_render_control_v232(call)
    return True

@bot.message_handler(commands=['data_constitution', 'constitution'])
def cmd_data_constitution(msg):
    try:
        uid = int(getattr(getattr(msg, 'from_user', None), 'id', 0) or 0)
        if uid != int(OWNER_ID or 0):
            return
    except Exception:
        return
    try:
        cid = int(OWNER_ID or 0)
        sent = bot.send_message(cid, window_mark(constitution_status_text(), 'Ф233'), reply_markup=constitution_control_keyboard_v232())
        try:
            _v160_schedule_delete(cid, int(sent.message_id), internal_timer_seconds('helper_message_close', 180), 'constitution-v232')
        except Exception:
            pass
    except Exception as exc:
        try:
            if OWNER_ID:
                bot.send_message(int(OWNER_ID), f'❌ DATA CONSTITUTION status: {exc}')
        except Exception:
            pass
DATA_CONSTITUTION_PROTECTED_SYMBOLS = ('constitution_snapshot_rejection', 'constitution_publish_sqlite_generation', 'constitution_download_active_generation', 'constitution_boot_verify_after_restore', 'constitution_ledger_append', 'constitution_semantic_manifest_from_live', 'constitution_semantic_manifest_from_sqlite')
DATA_CONSTITUTION_PROTECTED_IDS = {name: id(globals().get(name)) for name in DATA_CONSTITUTION_PROTECTED_SYMBOLS}

def constitution_verify_protected_symbols() -> tuple[bool, str]:
    changed = [name for name, ident in DATA_CONSTITUTION_PROTECTED_IDS.items() if id(globals().get(name)) != ident]
    if changed:
        constitution_set_quarantine('storage-core symbol redefined: ' + ', '.join(changed))
        return (False, ', '.join(changed))
    return (True, 'ok')
CONFIG_GUARD_SCHEMA_V234 = 1
CONFIG_GUARD_REMOTE_KEEP_V234 = 5
CONFIG_GUARD_REMOTE_DIRNAME_V234 = 'config_checkpoints'
CONFIG_GUARD_META_KIND_V234 = 'config_guard_v234'
CONFIG_GUARD_GENERATION_KEY_V234 = 'config_generation_v234'
CONFIG_GUARD_BOOT_VERIFIED_V234 = False
CONFIG_GUARD_LAST_REPORT_V234 = {}
CONFIG_GUARD_LOCK_V234 = threading.RLock()
_V234_ROOT_CONFIG_KEYS = ('forward_rules', 'forward_finance', 'finance_active_chats', 'backup_flags')
_V234_GLOBAL_SETTINGS_EXCLUDE = {CONFIG_GUARD_GENERATION_KEY_V234, 'finance_integrity_v141', 'operation_ledger_v141', '_window_tz_v160', '_window_marker_catalog_v160', 'version_mode_snapshots', 'mega_root_migration_v153', 'buttons_current_window', 'data_constitution_ledger_highwater', 'usd_rate_cache', 'last_chat_probe_summary_v197', 'expense_inbox_v141', 'protected_branches_registry', 'journal_v208_applied_at', 'version_mode_v87_migrated', 'version_mode_v88_migrated', 'version_mode_v90_migrated', 'version_mode_v91_migrated', 'version_mode_v92_migrated', 'version_mode_v93_migrated', 'version_mode_v94_migrated'}
_V234_CHAT_SETTINGS_EXCLUDE = {'pending_input', 'input_wait', 'last_callback_at', 'last_ui_touch_at', 'buttons_current_window', '_active_currency_ledger', 'usd_transactions_migrated_v93', 'gomonk_rebalance_history_v151'}
_V234_GOMONK_KEYS = ('gomonk_enabled', 'gomonk_entries', 'remaining_with_gomonk', 'gomonk_target_total_v209', 'gomonk_target_migrated_v209', 'usd_gomonk_enabled', 'usd_gomonk_entries', 'usd_remaining_with_gomonk', 'usd_gomonk_target_total_v209', 'usd_gomonk_target_migrated_v209')

def config_guard_remote_dir_v234() -> str:
    root = str(globals().get('MEGA_BACKUP_DIR') or '').rstrip('/')
    return root + '/' + CONFIG_GUARD_REMOTE_DIRNAME_V234

def _v234_json_clone(value):
    return json.loads(json.dumps(value, ensure_ascii=False, default=str))

def _v239_config_guard_sanitize_transient(value, key_hint: str=''):
    """Drop runtime Google history/errors from CONFIG hash while preserving real settings."""
    if isinstance(value, list):
        return [_v239_config_guard_sanitize_transient(v, '') for v in value]
    if not isinstance(value, dict):
        return value
    if str(key_hint) == 'google_v149':
        stable_keys = {'schema_version', 'credentials_sealed', 'credential_fingerprint', 'service_account_email', 'owner_google_email', 'spreadsheet_id', 'spreadsheet_title', 'drive_folder_id', 'drive_folder_name', 'export_settings', 'connected_at', 'connected_by'}
        return {str(k): _v239_config_guard_sanitize_transient(v, str(k)) for k, v in value.items() if str(k) in stable_keys}
    out = {}
    for k, v in value.items():
        ks = str(k)
        if ks in {'google_sync_runtime_v239', 'google_last_sync_v239'}:
            continue
        out[ks] = _v239_config_guard_sanitize_transient(v, ks)
    return out

def _v234_config_projection_from_payload(payload: dict) -> dict:
    payload = payload if isinstance(payload, dict) else {}
    root = {}
    for key in _V234_ROOT_CONFIG_KEYS:
        value = payload.get(key)
        if isinstance(value, (dict, list)) or value is not None:
            root[key] = _v234_json_clone(value if value is not None else {})
    gs = payload.get('_global_settings') or {}
    if isinstance(gs, dict):
        root['_global_settings'] = {str(k): _v234_json_clone(_v239_config_guard_sanitize_transient(v, str(k))) for k, v in gs.items() if str(k) not in _V234_GLOBAL_SETTINGS_EXCLUDE}
    chats_out = {}
    for cid, store in (payload.get('chats') or {}).items():
        if not isinstance(store, dict):
            continue
        settings = store.get('settings') or {}
        if not isinstance(settings, dict):
            settings = {}
        cfg = {str(k): _v234_json_clone(_v239_config_guard_sanitize_transient(v, str(k))) for k, v in settings.items() if str(k) not in _V234_CHAT_SETTINGS_EXCLUDE}
        row = {'settings': cfg}
        if isinstance(store.get('info'), dict):
            row['info'] = _v234_json_clone(store.get('info'))
        if isinstance(store.get('known_chats'), dict):
            row['known_chats'] = _v234_json_clone(store.get('known_chats'))
        if isinstance(store.get('chat_lifecycle_v150'), dict):
            life = dict(store.get('chat_lifecycle_v150') or {})
            life.pop('history', None)
            row['chat_lifecycle_v150'] = _v234_json_clone(life)
        chats_out[str(cid)] = row
    return {'root': root, 'chats': chats_out}

def config_guard_projection_v234() -> dict:
    with data_lock:
        payload = {k: v for k, v in (data or {}).items() if k != 'chats'}
        chats = {}
        for cid, store in ((data or {}).get('chats') or {}).items():
            if isinstance(store, dict):
                try:
                    meta = _lowram_store_meta_payload(store) if globals().get('LOWRAM_ENABLED') else dict(store)
                except Exception:
                    meta = dict(store)
                chats[str(cid)] = meta
        payload['chats'] = chats
        return _v234_config_projection_from_payload(payload)

def _v234_config_hash(projection: dict) -> str:
    raw = json.dumps(projection or {}, ensure_ascii=False, sort_keys=True, separators=(',', ':'), default=str)
    return hashlib.sha256(raw.encode('utf-8')).hexdigest()

def _v234_config_metrics(proj: dict) -> dict:
    root = (proj or {}).get('root') or {}
    chats = (proj or {}).get('chats') or {}
    fr = root.get('forward_rules') or {}
    forward_edges = 0
    if isinstance(fr, dict):
        for v in fr.values():
            if isinstance(v, dict):
                forward_edges += len(v)
            elif isinstance(v, list):
                forward_edges += len(v)
    reminders = ((root.get('_global_settings') or {}).get('reminders_v2') or {}).get('items') or {}
    reminder_items = len(reminders) if isinstance(reminders, dict) else 0
    gomonk_entries = 0
    gomonk_enabled_count = 0
    settings_keys = 0
    for row in chats.values():
        st = (row or {}).get('settings') or {}
        if not isinstance(st, dict):
            continue
        settings_keys += len(st)
        for prefix in ('', 'usd_'):
            ent = st.get(prefix + 'gomonk_entries') or []
            if isinstance(ent, list):
                gomonk_entries += len(ent)
            if bool(st.get(prefix + 'gomonk_enabled', False)):
                gomonk_enabled_count += 1
    return {'forward_edges': forward_edges, 'reminder_items': reminder_items, 'gomonk_entries': gomonk_entries, 'gomonk_enabled': gomonk_enabled_count, 'settings_keys': settings_keys}

def _v234_checkpoint_from_projection(proj: dict, generation: int, reason: str) -> dict:
    return {'kind': 'telegram_bot_config_checkpoint_v234', 'schema_version': CONFIG_GUARD_SCHEMA_V234, 'bot_version': VERSION, 'created_at': now_local().isoformat(timespec='microseconds'), 'generation': int(generation), 'reason': str(reason or 'config'), 'storage_lineage_v239': _v239_storage_lineage(create=True), 'config_hash': _v234_config_hash(proj), 'metrics': _v234_config_metrics(proj), 'config': proj}

def config_guard_latest_local_v234() -> dict:
    try:
        row = SQLITE.get_meta(CONFIG_GUARD_META_KIND_V234, 'latest', {}) or {}
        return row if isinstance(row, dict) else {}
    except Exception:
        return {}

def _v234_schedule_config_sync(delay: float=1.5) -> None:
    sched = globals().get('DELAYED_SCHEDULER')
    fn = globals().get('config_guard_sync_remote_v234')
    if sched is not None and callable(fn):
        try:
            sched.schedule('config-checkpoint-sync-v234', max(0.2, float(delay)), fn)
        except Exception:
            pass

def config_guard_accept_current_v234(reason: str='accept_current', force_generation: int | None=None) -> dict:
    with CONFIG_GUARD_LOCK_V234:
        proj = config_guard_projection_v234()
        sig = _v234_config_hash(proj)
        latest = config_guard_latest_local_v234()
        old_gen = max(int((latest or {}).get('generation') or 0), int(SQLITE.get_meta(CONFIG_GUARD_META_KIND_V234, 'generation', 0) or 0))
        gen = max(1, int(force_generation) if force_generation is not None else old_gen + 1)
        gs = data.setdefault('_global_settings', {})
        gs[CONFIG_GUARD_GENERATION_KEY_V234] = gen
        try:
            SQLITE.save_root(_sqlite_pack_root(data))
        except Exception:
            pass
        cp = _v234_checkpoint_from_projection(proj, gen, reason)
        SQLITE.set_meta(CONFIG_GUARD_META_KIND_V234, 'latest', cp)
        SQLITE.set_meta(CONFIG_GUARD_META_KIND_V234, 'generation', gen)
        SQLITE.set_meta(CONFIG_GUARD_META_KIND_V234, 'last_signature', sig)
        SQLITE.set_meta(CONFIG_GUARD_META_KIND_V234, 'synced_hash', '')
        _v234_schedule_config_sync(0.8)
        return cp

def config_guard_note_after_save_v234(reason: str='save_data') -> dict:
    """Cheap semantic trigger: finance-only saves do not create another config generation."""
    try:
        if not globals().get('CONFIG_GUARD_BOOT_VERIFIED_V234', False):
            return {}
        proj = config_guard_projection_v234()
        sig = _v234_config_hash(proj)
        prev = str(SQLITE.get_meta(CONFIG_GUARD_META_KIND_V234, 'last_signature', '') or '')
        if prev == sig:
            return config_guard_latest_local_v234()
        latest = config_guard_latest_local_v234()
        gen = max(int((latest or {}).get('generation') or 0), int(SQLITE.get_meta(CONFIG_GUARD_META_KIND_V234, 'generation', 0) or 0)) + 1
        data.setdefault('_global_settings', {})[CONFIG_GUARD_GENERATION_KEY_V234] = gen
        SQLITE.save_root(_sqlite_pack_root(data))
        cp = _v234_checkpoint_from_projection(proj, gen, reason)
        SQLITE.set_meta(CONFIG_GUARD_META_KIND_V234, 'latest', cp)
        SQLITE.set_meta(CONFIG_GUARD_META_KIND_V234, 'generation', gen)
        SQLITE.set_meta(CONFIG_GUARD_META_KIND_V234, 'last_signature', sig)
        SQLITE.set_meta(CONFIG_GUARD_META_KIND_V234, 'synced_hash', '')
        _v234_schedule_config_sync(1.2)
        try:
            bot_journal('config_checkpoint_local_v234', int(OWNER_ID or 0) or None, f'gen={gen}; reason={reason}; hash={sig[:12]}')
        except Exception:
            pass
        return cp
    except Exception as exc:
        try:
            log_error(f'config guard note v234: {exc}')
        except Exception:
            pass
        return {}

def _v234_remote_config_rows(limit: int=5) -> list[str]:
    gate = globals().get('external_access_allowed_v233')
    if callable(gate) and (not gate('mega_control')):
        return []
    try:
        mega_ensure_remote_path(config_guard_remote_dir_v234())
        res = _mega_run('mega-find', [config_guard_remote_dir_v234(), '--pattern=config_*.json.gz', '--type=f'], check=False, timeout=60)
        rows = [x.strip() for x in (res.stdout or '').splitlines() if x.strip().endswith('.json.gz')]
        return sorted(set(rows), reverse=True)[:max(1, int(limit))]
    except Exception:
        return []

def _v234_load_remote_checkpoint(remote: str) -> dict:
    work = tempfile.mkdtemp(prefix='config_guard_get_v234_')
    try:
        _mega_run('mega-get', [remote, work], check=True, timeout=MEGA_TIMEOUT)
        found = list(Path(work).rglob(os.path.basename(remote))) or list(Path(work).rglob('config_*.json.gz'))
        if not found:
            return {}
        with gzip.open(str(found[0]), 'rt', encoding='utf-8') as fh:
            cp = json.load(fh)
        if not isinstance(cp, dict) or not isinstance(cp.get('config'), dict):
            return {}
        if _v234_config_hash(cp.get('config') or {}) != str(cp.get('config_hash') or ''):
            return {}
        return cp
    except Exception as exc:
        try:
            log_error(f'config checkpoint download v234: {exc}')
        except Exception:
            pass
        return {}
    finally:
        shutil.rmtree(work, ignore_errors=True)

def v239_external_durable_write_allowed(*, recovery_write: bool=False) -> tuple[bool, str]:
    """Fail closed for background/destructive remote writes after an unhealthy recovery.

    Dedicated recovery publication may pass recovery_write=True because it is exactly the
    operation that repairs the canonical branch. Ordinary delta/config/Google/background
    replication must not publish a partial/empty post-deploy state.
    """
    if recovery_write:
        return (True, 'recovery_write')
    try:
        state = globals().get('_RUNTIME_STATE') or {}
        if isinstance(state, dict) and bool(state.get('restore_attempted')) and (state.get('restore_ok') is False):
            return (False, 'deploy restore failed')
    except Exception:
        pass
    try:
        if bool(globals().get('DATA_CONSTITUTION_QUARANTINE', False)):
            return (False, str(globals().get('DATA_CONSTITUTION_REASON', '') or 'Data Constitution quarantine'))
    except Exception:
        pass
    try:
        if bool(globals().get('RESTORE_GUARD_ACTIVE', False)):
            return (False, str(globals().get('RESTORE_GUARD_REASON', '') or 'restore guard'))
    except Exception:
        pass
    return (True, 'ok')

def _canon_config_guard_sync_remote_v234__001(*, recovery_write: bool=False) -> bool:
    if not recovery_write:
        feature_fn = globals().get('storage_mode_feature_enabled_v240')
        profile_fn = globals().get('storage_profile_v237_1')
        try:
            if callable(feature_fn) and callable(profile_fn) and (str(profile_fn()) == 'mega') and (not feature_fn('mega', 'config')):
                return True
        except Exception:
            pass
    _ok, _why = v239_external_durable_write_allowed(recovery_write=recovery_write)
    if not _ok:
        try:
            runtime_event('remote_config_write_blocked_v239', _why, 'WARN')
        except Exception:
            pass
        return False
    gate = globals().get('external_access_allowed_v233')
    if callable(gate) and (not gate('mega_put')):
        return False
    if not mega_is_configured():
        return False
    cp = config_guard_latest_local_v234()
    if not cp:
        return False
    if str(SQLITE.get_meta(CONFIG_GUARD_META_KIND_V234, 'synced_hash', '') or '') == str(cp.get('config_hash') or ''):
        return True
    work = tempfile.mkdtemp(prefix='config_guard_put_v234_')
    try:
        stamp = re.sub('[^0-9]', '', str(cp.get('created_at') or now_local().isoformat(timespec='microseconds')))[:20]
        name = f"config_{int(cp.get('generation') or 0):08d}_{stamp}_{str(cp.get('config_hash') or '')[:12]}.json.gz"
        local = os.path.join(work, name)
        with gzip.open(local, 'wt', encoding='utf-8', compresslevel=6) as fh:
            json.dump(cp, fh, ensure_ascii=False, separators=(',', ':'), default=str)
        mega_ensure_remote_path(config_guard_remote_dir_v234())
        _mega_run('mega-put', [local, config_guard_remote_dir_v234()], check=True, timeout=MEGA_TIMEOUT)
        SQLITE.set_meta(CONFIG_GUARD_META_KIND_V234, 'synced_hash', str(cp.get('config_hash') or ''))
        rows = _v234_remote_config_rows(CONFIG_GUARD_REMOTE_KEEP_V234 + 20)
        for old in rows[CONFIG_GUARD_REMOTE_KEEP_V234:]:
            try:
                _mega_run('mega-rm', [old], check=False, timeout=60)
            except Exception:
                pass
        try:
            bot_journal('config_checkpoint_remote_v234', int(OWNER_ID or 0) or None, f"gen={cp.get('generation')}; bytes={os.path.getsize(local)}")
        except Exception:
            pass
        return True
    except Exception as exc:
        try:
            log_error(f'config checkpoint upload v234: {exc}')
        except Exception:
            pass
        return False
    finally:
        shutil.rmtree(work, ignore_errors=True)

def _v234_apply_config_projection(proj: dict, *, merge_missing_only: bool=False) -> dict:
    root = (proj or {}).get('root') or {}
    chats = (proj or {}).get('chats') or {}
    changed = {'root': 0, 'chats': 0}
    with data_lock:
        for key in _V234_ROOT_CONFIG_KEYS:
            if key not in root:
                continue
            if merge_missing_only and data.get(key):
                continue
            data[key] = _v234_json_clone(root.get(key))
            changed['root'] += 1
        remote_gs = root.get('_global_settings') or {}
        live_gs = data.setdefault('_global_settings', {})
        if isinstance(remote_gs, dict):
            remote_gs = {str(k): v for k, v in remote_gs.items() if str(k) not in _V234_GLOBAL_SETTINGS_EXCLUDE}
            if merge_missing_only:
                for k, v in remote_gs.items():
                    if k not in live_gs:
                        live_gs[k] = _v234_json_clone(v)
                        changed['root'] += 1
            else:
                for k in list(live_gs):
                    if k not in _V234_GLOBAL_SETTINGS_EXCLUDE and k not in remote_gs:
                        live_gs.pop(k, None)
                for k, v in remote_gs.items():
                    live_gs[k] = _v234_json_clone(v)
            live_gs.pop('mega_root_migration_v153', None)
        for cid, row in chats.items():
            try:
                store = get_chat_store(int(cid))
            except Exception:
                continue
            rst = (row or {}).get('settings') or {}
            live = store.setdefault('settings', {})
            if merge_missing_only:
                for k, v in rst.items():
                    if k not in live:
                        live[k] = _v234_json_clone(v)
            else:
                preserve = {k: v for k, v in live.items() if k in _V234_CHAT_SETTINGS_EXCLUDE}
                live.clear()
                live.update(_v234_json_clone(rst))
                live.update(preserve)
            for meta_key in ('info', 'known_chats', 'chat_lifecycle_v150'):
                if meta_key in (row or {}) and (not merge_missing_only or not store.get(meta_key)):
                    store[meta_key] = _v234_json_clone(row.get(meta_key))
            changed['chats'] += 1
        save_data(data, full=True)
    return changed

def _v234_projection_from_sqlite_gz_remote(remote: str) -> tuple[dict, str]:
    work = tempfile.mkdtemp(prefix='config_ancestry_v234_')
    try:
        _mega_run('mega-get', [remote, work], check=True, timeout=max(float(MEGA_TIMEOUT), 180.0))
        gzrows = list(Path(work).rglob(os.path.basename(remote))) or list(Path(work).rglob('generation_*.sqlite3.gz'))
        if not gzrows:
            return ({}, '')
        raw = os.path.join(work, 'state.sqlite3')
        _lowram_gunzip_file(str(gzrows[0]), raw)
        conn = sqlite3.connect(raw)
        try:
            r = conn.execute("SELECT v FROM kv WHERE k='root'").fetchone()
            root = json.loads(r[0]) if r and r[0] else {}
            chats = {}
            for cid, v in conn.execute('SELECT chat_id,v FROM chats').fetchall():
                try:
                    chats[str(cid)] = json.loads(v) if v else {}
                except Exception:
                    chats[str(cid)] = {}
            created = ''
            try:
                m = conn.execute("SELECT v FROM meta WHERE kind='db_snapshot' AND k='main'").fetchone()
                created = str((json.loads(m[0]) or {}).get('created_at') or '') if m else ''
            except Exception:
                pass
        finally:
            conn.close()
        payload = root if isinstance(root, dict) else {}
        payload = dict(payload)
        payload['chats'] = chats
        return (_v234_config_projection_from_payload(payload), created)
    except Exception:
        return ({}, '')
    finally:
        shutil.rmtree(work, ignore_errors=True)

def _v234_bootstrap_ancestry_repair() -> dict:
    """One-time pre-v234 rescue. Auto-merge only on a multi-domain collapse, never on a single intentional deletion."""
    current = config_guard_projection_v234()
    cm = _v234_config_metrics(current)
    try:
        res = _mega_run('mega-find', [constitution_generations_dir(), '--pattern=generation_*.sqlite3.gz', '--type=f'], check=False, timeout=60)
        rows = sorted(set((x.strip() for x in (res.stdout or '').splitlines() if x.strip().endswith('.sqlite3.gz'))), reverse=True)[:6]
    except Exception:
        rows = []
    best = None
    best_metrics = None
    best_remote = ''
    best_created = ''
    for remote in rows:
        proj, created = _v234_projection_from_sqlite_gz_remote(remote)
        if not proj:
            continue
        m = _v234_config_metrics(proj)
        collapsed = 0
        if cm['forward_edges'] == 0 and m['forward_edges'] > 0:
            collapsed += 1
        if cm['reminder_items'] == 0 and m['reminder_items'] > 0:
            collapsed += 1
        if cm['gomonk_entries'] < m['gomonk_entries'] and (cm['gomonk_entries'] == 0 or cm['gomonk_enabled'] < m['gomonk_enabled']):
            collapsed += 1
        if collapsed >= 2:
            best, best_metrics, best_remote, best_created = (proj, m, remote, created)
            break
    if not best:
        return {'repaired': False, 'reason': 'no multi-domain collapse ancestor', 'current': cm}
    broot = best.get('root') or {}
    croot = current.get('root') or {}
    if cm['forward_edges'] == 0 and best_metrics['forward_edges'] > 0:
        data['forward_rules'] = _v234_json_clone(broot.get('forward_rules') or {})
        data['forward_finance'] = _v234_json_clone(broot.get('forward_finance') or {})
    if cm['reminder_items'] == 0 and best_metrics['reminder_items'] > 0:
        oldrem = (broot.get('_global_settings') or {}).get('reminders_v2')
        if isinstance(oldrem, dict):
            data.setdefault('_global_settings', {})['reminders_v2'] = _v234_json_clone(oldrem)
    for cid, row in (best.get('chats') or {}).items():
        oldst = (row or {}).get('settings') or {}
        if not isinstance(oldst, dict):
            continue
        try:
            live = get_chat_store(int(cid)).setdefault('settings', {})
        except Exception:
            continue
        for k, v in oldst.items():
            if k not in live:
                live[k] = _v234_json_clone(v)
        for prefix in ('', 'usd_'):
            ekey = prefix + 'gomonk_entries'
            enkey = prefix + 'gomonk_enabled'
            tkey = prefix + 'gomonk_target_total_v209'
            olde = oldst.get(ekey) or []
            livee = live.get(ekey) or []
            if isinstance(olde, list) and olde and (not livee):
                live[ekey] = _v234_json_clone(olde)
            if bool(oldst.get(enkey)) and (not bool(live.get(enkey))) and (olde or oldst.get(tkey)):
                live[enkey] = True
            if oldst.get(tkey) not in (None, 0, 0.0, '') and live.get(tkey) in (None, 0, 0.0, ''):
                live[tkey] = _v234_json_clone(oldst.get(tkey))
    save_data(data, full=True)
    after = _v234_config_metrics(config_guard_projection_v234())
    try:
        runtime_event('config_ancestry_repaired_v234', f'source={os.path.basename(best_remote)}; created={best_created}; before={cm}; after={after}', 'WARN')
    except Exception:
        pass
    return {'repaired': True, 'source': best_remote, 'created_at': best_created, 'before': cm, 'after': after}

def _canon_config_guard_boot_verify_v234__001() -> dict:
    global CONFIG_GUARD_BOOT_VERIFIED_V234, CONFIG_GUARD_LAST_REPORT_V234
    with CONFIG_GUARD_LOCK_V234:
        report = {'ok': True, 'mode': 'boot', 'repaired': False}
        gate = globals().get('external_access_allowed_v233')
        if callable(gate) and (not gate('mega_get')):
            CONFIG_GUARD_BOOT_VERIFIED_V234 = True
            cp = config_guard_latest_local_v234()
            if not cp:
                cp = config_guard_accept_current_v234('bootstrap_local_only_v234')
            report.update({'mode': 'local_only', 'generation': int((cp or {}).get('generation') or 0)})
            CONFIG_GUARD_LAST_REPORT_V234 = report
            return report
        binding = SQLITE.get_meta('boot_restore_binding_v240', 'selected', {}) or {}
        expected_hash = str((binding or {}).get('config_hash_v240') or '')
        expected_gen = int((binding or {}).get('config_generation_v240') or 0)
        expected_lineage = str((binding or {}).get('config_lineage_v240') or (binding or {}).get('storage_lineage_v239') or '')
        local_lineage = _v239_storage_lineage(create=False)
        if expected_hash:
            cur = config_guard_projection_v234()
            curhash = _v234_config_hash(cur)
            curgen = int((data.get('_global_settings') or {}).get(CONFIG_GUARD_GENERATION_KEY_V234) or SQLITE.get_meta(CONFIG_GUARD_META_KIND_V234, 'generation', 0) or 0)
            if curhash == expected_hash and (not expected_gen or curgen == expected_gen) and (not expected_lineage or local_lineage == expected_lineage):
                cp = config_guard_latest_local_v234() or _v234_checkpoint_from_projection(cur, curgen or expected_gen or 1, 'canonical_generation_bound_v240')
                SQLITE.set_meta(CONFIG_GUARD_META_KIND_V234, 'latest', cp)
                SQLITE.set_meta(CONFIG_GUARD_META_KIND_V234, 'generation', int(cp.get('generation') or expected_gen or 1))
                SQLITE.set_meta(CONFIG_GUARD_META_KIND_V234, 'last_signature', curhash)
                report.update({'mode': 'canonical_generation_bound_v240', 'generation': int(cp.get('generation') or 0), 'metrics': _v234_config_metrics(cur), 'lineage': local_lineage, 'binding': True})
                CONFIG_GUARD_BOOT_VERIFIED_V234 = True
                CONFIG_GUARD_LAST_REPORT_V234 = report
                try:
                    runtime_event('config_guard_canonical_bound_v240', json.dumps(report, ensure_ascii=False, default=str)[:1200], 'INFO')
                except Exception:
                    pass
                return report
            exact_remote = {}
            for _remote_path in _v234_remote_config_rows(20):
                _cp = _v234_load_remote_checkpoint(_remote_path) or {}
                if expected_gen and int(_cp.get('generation') or 0) != expected_gen:
                    continue
                if str(_cp.get('config_hash') or '') != expected_hash:
                    continue
                if expected_lineage and str(_cp.get('storage_lineage_v239') or '') != expected_lineage:
                    continue
                exact_remote = _cp
                break
            if exact_remote:
                changed = _v234_apply_config_projection(exact_remote.get('config') or {}, merge_missing_only=False)
                rgen = int(exact_remote.get('generation') or expected_gen or 0)
                rhash = str(exact_remote.get('config_hash') or expected_hash)
                data.setdefault('_global_settings', {})[CONFIG_GUARD_GENERATION_KEY_V234] = rgen
                SQLITE.save_root(_sqlite_pack_root(data))
                SQLITE.set_meta(CONFIG_GUARD_META_KIND_V234, 'latest', exact_remote)
                SQLITE.set_meta(CONFIG_GUARD_META_KIND_V234, 'generation', rgen)
                SQLITE.set_meta(CONFIG_GUARD_META_KIND_V234, 'last_signature', rhash)
                SQLITE.set_meta(CONFIG_GUARD_META_KIND_V234, 'synced_hash', rhash)
                report.update({'mode': 'canonical_exact_config_repair_v240', 'repaired': True, 'generation': rgen, 'changed': changed, 'metrics': exact_remote.get('metrics'), 'lineage': expected_lineage, 'binding': True})
                CONFIG_GUARD_BOOT_VERIFIED_V234 = True
                CONFIG_GUARD_LAST_REPORT_V234 = report
                try:
                    runtime_event('config_guard_exact_binding_repair_v240', json.dumps(report, ensure_ascii=False, default=str)[:1200], 'WARN')
                except Exception:
                    pass
                return report
            report.update({'ok': False, 'mode': 'canonical_config_binding_failed_v240', 'reason': f'generation config binding mismatch expected_gen={expected_gen} expected_hash={expected_hash[:12]} local_gen={curgen} local_hash={curhash[:12]}', 'lineage': expected_lineage or local_lineage, 'binding': True})
            CONFIG_GUARD_BOOT_VERIFIED_V234 = True
            CONFIG_GUARD_LAST_REPORT_V234 = report
            try:
                runtime_event('config_guard_binding_failed_v240', json.dumps(report, ensure_ascii=False, default=str)[:1200], 'ERROR')
            except Exception:
                pass
            return report
        rows = _v234_remote_config_rows(12)
        remote = {}
        if local_lineage:
            for _remote_path in rows:
                _cp = _v234_load_remote_checkpoint(_remote_path) or {}
                if str(_cp.get('storage_lineage_v239') or '') == local_lineage:
                    remote = _cp
                    break
            if rows and (not remote):
                try:
                    runtime_event('config_lineage_mismatch_ignored_v239', f'local={local_lineage}; remote_candidates={len(rows)}', 'WARN')
                except Exception:
                    pass
        else:
            remote = _v234_load_remote_checkpoint(rows[0]) if rows else {}
        if not remote:
            if local_lineage:
                cp = config_guard_latest_local_v234()
                if not cp or str(cp.get('storage_lineage_v239') or '') != local_lineage:
                    current_gen = int((data.get('_global_settings') or {}).get(CONFIG_GUARD_GENERATION_KEY_V234) or SQLITE.get_meta(CONFIG_GUARD_META_KIND_V234, 'generation', 0) or 0)
                    cp = config_guard_accept_current_v234('lineage_local_authority_v239', force_generation=max(1, current_gen))
                else:
                    _v234_schedule_config_sync(0.8)
                report.update({'mode': 'lineage_local_authority_v239', 'generation': int((cp or {}).get('generation') or 0), 'metrics': (cp or {}).get('metrics') or _v234_config_metrics(config_guard_projection_v234()), 'lineage': local_lineage})
            else:
                rescue = _v234_bootstrap_ancestry_repair()
                report['ancestry'] = rescue
                report['repaired'] = bool(rescue.get('repaired'))
                cp = config_guard_accept_current_v234('bootstrap_after_ancestry_v234')
                report.update({'mode': 'bootstrap', 'generation': int(cp.get('generation') or 0), 'metrics': cp.get('metrics')})
        else:
            cur = config_guard_projection_v234()
            curhash = _v234_config_hash(cur)
            curgen = int((data.get('_global_settings') or {}).get(CONFIG_GUARD_GENERATION_KEY_V234) or SQLITE.get_meta(CONFIG_GUARD_META_KIND_V234, 'generation', 0) or 0)
            rgen = int(remote.get('generation') or 0)
            rhash = str(remote.get('config_hash') or '')
            if curgen < rgen or (curgen == rgen and curhash != rhash):
                changed = _v234_apply_config_projection(remote.get('config') or {}, merge_missing_only=False)
                data.setdefault('_global_settings', {})[CONFIG_GUARD_GENERATION_KEY_V234] = rgen
                SQLITE.save_root(_sqlite_pack_root(data))
                SQLITE.set_meta(CONFIG_GUARD_META_KIND_V234, 'latest', remote)
                SQLITE.set_meta(CONFIG_GUARD_META_KIND_V234, 'generation', rgen)
                SQLITE.set_meta(CONFIG_GUARD_META_KIND_V234, 'last_signature', rhash)
                SQLITE.set_meta(CONFIG_GUARD_META_KIND_V234, 'synced_hash', rhash)
                report.update({'mode': 'remote_restore', 'repaired': True, 'generation': rgen, 'changed': changed, 'metrics': remote.get('metrics')})
                try:
                    runtime_event('config_checkpoint_restored_v234', f"gen={rgen}; changed={changed}; metrics={remote.get('metrics')}", 'WARN')
                except Exception:
                    pass
            else:
                if curgen <= 0:
                    cp = config_guard_accept_current_v234('generation_reanchor_v234')
                    curgen = int(cp.get('generation') or 0)
                else:
                    cp = _v234_checkpoint_from_projection(cur, curgen, 'boot_current_v234')
                    SQLITE.set_meta(CONFIG_GUARD_META_KIND_V234, 'latest', cp)
                    SQLITE.set_meta(CONFIG_GUARD_META_KIND_V234, 'generation', curgen)
                    SQLITE.set_meta(CONFIG_GUARD_META_KIND_V234, 'last_signature', curhash)
                    if curhash == rhash:
                        SQLITE.set_meta(CONFIG_GUARD_META_KIND_V234, 'synced_hash', rhash)
                    else:
                        _v234_schedule_config_sync(1.0)
                report.update({'mode': 'current_ok' if curhash == rhash else 'current_newer', 'generation': curgen, 'metrics': _v234_config_metrics(cur)})
        CONFIG_GUARD_BOOT_VERIFIED_V234 = True
        CONFIG_GUARD_LAST_REPORT_V234 = report
        try:
            runtime_event('config_guard_boot_v234', json.dumps(report, ensure_ascii=False, default=str)[:1200], 'INFO' if report.get('ok') else 'ERROR')
        except Exception:
            pass
        return report

def config_guard_snapshot_preflight_v234(sqlite_path: str) -> tuple[bool, str]:
    if not CONFIG_GUARD_BOOT_VERIFIED_V234:
        return (False, 'configuration boot verification not completed')
    try:
        conn = sqlite3.connect(sqlite_path)
        try:
            r = conn.execute("SELECT v FROM kv WHERE k='root'").fetchone()
            root = json.loads(r[0]) if r and r[0] else {}
            chats = {str(cid): json.loads(v) if v else {} for cid, v in conn.execute('SELECT chat_id,v FROM chats').fetchall()}
        finally:
            conn.close()
        payload = dict(root if isinstance(root, dict) else {})
        payload['chats'] = chats
        snap = _v234_config_projection_from_payload(payload)
        sh = _v234_config_hash(snap)
        live = _v234_config_hash(config_guard_projection_v234())
        return (sh == live, 'ok' if sh == live else f'config snapshot/live mismatch {sh[:12]}!={live[:12]}')
    except Exception as exc:
        return (False, str(exc)[:300])

def config_guard_status_text_v234() -> str:
    cp = config_guard_latest_local_v234()
    rep = dict(CONFIG_GUARD_LAST_REPORT_V234 or {})
    metrics = (cp or {}).get('metrics') or _v234_config_metrics(config_guard_projection_v234())
    return f"🧩 ЗАЩИТА НАСТРОЕК v234\n\nBoot-проверка: {('✅' if CONFIG_GUARD_BOOT_VERIFIED_V234 else '⏳')}\nРежим последней проверки: {rep.get('mode') or '—'}\nАвтовосстановление: {('да' if rep.get('repaired') else 'нет')}\nПоколение config: {int((cp or {}).get('generation') or 0)}\nПересылки: {metrics.get('forward_edges', 0)} · Напоминания: {metrics.get('reminder_items', 0)}\nГомонковые entries: {metrics.get('gomonk_entries', 0)} · включено контуров/валют: {metrics.get('gomonk_enabled', 0)}\n\nПеред READY настройки сверяются независимо от финансов. Новый canonical SQLite snapshot не продвигается, пока его config-проекция не совпадает с живым состоянием."[:3900]
MEGA_STORAGE_CONTRACT_V242 = {'schema': 1, 'root': '/TelegramBotBackups', 'canonical_pointer': 'database/current_manifest.json', 'generations': 'database/generations/generation_*.sqlite3.gz', 'manifests': 'database/manifests/generation_*.json', 'legacy_latest': 'database/latest_bot_state.sqlite3.gz', 'pre_restore': 'database/pre_restore/pre_restore_*.sqlite3.gz', 'read_order': ['current_manifest', 'latest_generation_file', 'legacy_latest', 'legacy_global'], 'write_order': ['flush_sqlite', 'immutable_generation', 'manifest', 'current_manifest', 'verify']}

def _v242_embed_manifest_from_sqlite(raw_sqlite: str, created_at: str, reason: str='snapshot') -> dict:
    """Build embedded semantics FROM the immutable candidate itself, never from hot RAM.

    This removes the v240/v241 race where records matched but actual != embedded because
    ledger/config metadata changed between live-manifest capture and SQLite backup.
    """
    manifest = constitution_semantic_manifest_from_sqlite(raw_sqlite) or {}
    manifest = dict(manifest)
    manifest['snapshot_created_at'] = str(created_at or now_local().isoformat(timespec='microseconds'))
    manifest['snapshot_reason_v242'] = str(reason or 'snapshot')
    conn = sqlite3.connect(str(raw_sqlite))
    try:
        conn.execute('INSERT OR REPLACE INTO meta(kind,k,v) VALUES(?,?,?)', ('data_constitution_snapshot', 'main', json.dumps(manifest, ensure_ascii=False, separators=(',', ':'), default=str)))
        snap = {'created_at': manifest['snapshot_created_at'], 'bot_version': VERSION, 'schema': 3, 'data_constitution': 2, 'storage_contract': 'v242_simple'}
        conn.execute('INSERT OR REPLACE INTO meta(kind,k,v) VALUES(?,?,?)', ('db_snapshot', 'main', json.dumps(snap, ensure_ascii=False, separators=(',', ':'), default=str)))
        conn.commit()
    finally:
        conn.close()
    _v239_generation_exact_preflight(raw_sqlite, require_embedded=True)
    return constitution_semantic_manifest_from_sqlite(raw_sqlite) or manifest

def _v242_verify_published_generation(manifest: dict) -> dict:
    generation = str((manifest or {}).get('generation') or '')
    if not generation:
        raise RuntimeError('MEGA publish returned no generation')
    active = constitution_load_active_manifest_remote(force=True) or {}
    if str(active.get('generation') or '') != generation:
        raise RuntimeError(f"MEGA current_manifest verify failed: {active.get('generation')} != {generation}")
    finder = globals().get('_mega_find_remote_files')
    if callable(finder):
        found = finder(constitution_generations_dir(), generation, limit=2) or []
        if not any((str(x).endswith('/' + generation) or str(x).endswith(generation) for x in found)):
            raise RuntimeError('MEGA generation uploaded but not visible in generations directory')
    return active

def mega_publish_current_sqlite_v242(reason: str='snapshot', *, manual_restore: bool=False, allow_destructive: bool=False) -> dict:
    """The single canonical full-SQLite WRITE path for v242 and future compatible code.

    Normal scheduled backups and confirmed /restore use the same capture/publish format.
    Manual restore rotates lineage and reanchors config first; ordinary snapshots do not.
    """
    if not mega_is_configured():
        raise RuntimeError('MEGA unavailable')
    previous_recovery = bool(globals().get('_V240_RECOVERY_AUTHORITY_ACTIVE', False))
    if manual_restore:
        globals()['_V240_RECOVERY_AUTHORITY_ACTIVE'] = True
    try:
        if manual_restore:
            _v239_rotate_storage_lineage('v242:' + str(reason or 'manual_restore'))
            cfg_fn = globals().get('config_guard_reanchor_after_manual_restore_v241')
            if callable(cfg_fn):
                cfg_fn('v242:' + str(reason or 'manual_restore'))
        else:
            _v239_storage_lineage(create=True)
        workdir = tempfile.mkdtemp(prefix='v242_mega_publish_')
        try:
            with MEGA_GLOBAL_BACKUP_LOCK:
                created_at = now_local().isoformat(timespec='microseconds')
                raw = os.path.join(workdir, 'bot_state.sqlite3')
                gz = raw + '.gz'
                with data_lock:
                    flush_fn = globals().get('_lowram_flush_all_hot')
                    if callable(flush_fn):
                        flush_fn(evict=False)
                    save_data(data, full=True)
                    SQLITE.backup_to(raw)
                embedded = _v242_embed_manifest_from_sqlite(raw, created_at, reason)
                try:
                    SQLITE.set_meta('data_constitution_snapshot', 'main', dict(embedded, snapshot_created_at=created_at, snapshot_reason_v242=str(reason)))
                    SQLITE.set_meta('db_snapshot', 'main', {'created_at': created_at, 'bot_version': VERSION, 'schema': 3, 'data_constitution': 2, 'storage_contract': 'v242_simple'})
                except Exception:
                    pass
                _lowram_gzip_file(raw, gz)
                preflight = globals().get('config_guard_snapshot_preflight_v234')
                if callable(preflight):
                    cfg_ok, cfg_detail = preflight(raw)
                    if not cfg_ok:
                        raise RuntimeError('config snapshot mismatch: ' + str(cfg_detail))
                manifest = constitution_publish_sqlite_generation(raw, gz, created_at, allow_destructive=bool(allow_destructive or manual_restore))
                active = _v242_verify_published_generation(manifest)
                try:
                    SQLITE.set_meta('mega_storage_v242', 'last_publish', {'at': created_at, 'reason': str(reason), 'generation': str(active.get('generation') or ''), 'records': int(active.get('total_records') or 0)})
                except Exception:
                    pass
                if manual_restore:
                    init_delta = globals().get('initialize_delta_baseline')
                    if callable(init_delta):
                        init_delta(data)
                    try:
                        lock = globals().get('_delta_state_lock')
                        pending = globals().get('_delta_pending_chats')
                        gens = globals().get('_delta_chat_generation')
                        if lock is not None:
                            with lock:
                                if hasattr(pending, 'clear'):
                                    pending.clear()
                                if hasattr(gens, 'clear'):
                                    gens.clear()
                        else:
                            if hasattr(pending, 'clear'):
                                pending.clear()
                            if hasattr(gens, 'clear'):
                                gens.clear()
                    except Exception:
                        pass
                try:
                    runtime_event('mega_canonical_publish_v242', f"reason={reason}; generation={active.get('generation')}; records={active.get('total_records')}")
                except Exception:
                    pass
                return active
        finally:
            shutil.rmtree(workdir, ignore_errors=True)
    finally:
        globals()['_V240_RECOVERY_AUTHORITY_ACTIVE'] = bool(previous_recovery or globals().get('_V241_RESTORE_ACTIVE', False))

def _canon_mega_upload_latest_database_backup__002(force: bool=False) -> bool:
    """v242 unified scheduled/manual full DB uploader. Deltas remain parallel and separate."""
    if not mega_is_configured():
        return False
    if not force:
        gate = globals().get('v239_external_durable_write_allowed')
        if callable(gate):
            ok, why = gate()
            if not ok:
                try:
                    _constitution_snapshot_block_notice(str(why))
                except Exception:
                    pass
                return False
        if bool(globals().get('RESTORE_GUARD_ACTIVE', False)):
            return False
        if globals().get('constitution_quarantine_active') and constitution_quarantine_active():
            return False
    try:
        mega_publish_current_sqlite_v242('forced_backup' if force else 'scheduled_backup', manual_restore=False, allow_destructive=False)
        return True
    except Exception as exc:
        try:
            runtime_event('mega_canonical_publish_failed_v242', str(exc)[:700], 'ERROR')
        except Exception:
            pass
        try:
            log_error(f'[MEGA DB SNAPSHOT ERROR v242] {exc}')
        except Exception:
            pass
        return False

def _v242_direct_generation_fallback(workdir: str, limit: int=24) -> tuple[str | None, dict | None, str]:
    """If current_manifest and/or generation manifests disappeared, read latest immutable generation file directly."""
    finder = globals().get('_mega_find_remote_files')
    if not callable(finder):
        return (None, None, 'mega-find unavailable')
    try:
        remotes = finder(constitution_generations_dir(), 'generation_*.sqlite3.gz', limit=max(3, int(limit))) or []
    except Exception as exc:
        return (None, None, 'generation listing failed: ' + str(exc)[:200])
    for idx, remote in enumerate(remotes):
        sub = os.path.join(workdir, f'v242_direct_{idx:02d}')
        os.makedirs(sub, exist_ok=True)
        try:
            res = _mega_run('mega-get', [str(remote), sub], check=False, timeout=max(float(MEGA_TIMEOUT), 180.0))
            if res.returncode != 0:
                continue
            found = list(Path(sub).rglob(os.path.basename(str(remote)))) or list(Path(sub).rglob('generation_*.sqlite3.gz'))
            if not found:
                continue
            gz = str(found[0])
            raw = os.path.join(sub, 'verify.sqlite3')
            _lowram_gunzip_file(gz, raw)
            semantic = constitution_semantic_manifest_from_sqlite(raw) or {}
            embedded = _v239_read_embedded_manifest_from_sqlite(raw) or {}
            if embedded:
                _v239_generation_exact_preflight(raw, require_embedded=True)
            synthetic = dict(semantic)
            synthetic.update(_v240_config_binding_from_sqlite(raw))
            synthetic['generation'] = os.path.basename(str(remote))
            synthetic['remote_generation'] = str(remote)
            synthetic['created_at'] = str(embedded.get('snapshot_created_at') or embedded.get('created_at') or semantic.get('created_at') or '')
            synthetic['fallback_without_pointer_v242'] = True
            try:
                runtime_event('boot_generation_direct_fallback_v242', f"selected={synthetic.get('generation')}; records={synthetic.get('total_records')}", 'WARN')
            except Exception:
                pass
            return (gz, synthetic, 'latest immutable generation file fallback v242')
        except Exception as exc:
            try:
                log_error(f'v242 direct generation fallback {remote}: {exc}')
            except Exception:
                pass
            continue
    return (None, None, 'no valid generation file')
_V242_PREV_BEST_BOOT_GENERATION = _canon_constitution_download_best_boot_generation_v235__001

def _canon_constitution_download_best_boot_generation_v235__002(workdir: str) -> tuple[str | None, dict | None, str]:
    """Unified READ order: pointer/manifests first, then generation file itself."""
    gz = None
    manifest = None
    detail = ''
    try:
        gz, manifest, detail = _V242_PREV_BEST_BOOT_GENERATION(workdir)
    except Exception as exc:
        detail = 'normal generation resolver failed: ' + str(exc)[:220]
    if gz:
        return (gz, manifest, detail)
    dgz, dmanifest, ddetail = _v242_direct_generation_fallback(workdir)
    if dgz:
        return (dgz, dmanifest, ddetail)
    return (None, manifest or dmanifest, (detail + '; ' + ddetail).strip('; '))

def config_guard_bind_recovered_state_v242() -> dict:
    """After same-lineage deltas, bind Configuration Guard to the final recovered SQLite state.

    Snapshot + verified deltas are one recovery transaction. The old snapshot config hash
    must not reject legitimate config changes carried by those deltas.
    """
    cp = config_guard_accept_current_v234('mega_boot_final_state_v242')
    binding = SQLITE.get_meta('boot_restore_binding_v240', 'selected', {}) or {}
    binding = dict(binding) if isinstance(binding, dict) else {}
    binding['config_generation_v240'] = int(cp.get('generation') or 0)
    binding['config_hash_v240'] = str(cp.get('config_hash') or '')
    binding['config_lineage_v240'] = str(cp.get('storage_lineage_v239') or _v239_storage_lineage(create=False) or '')
    binding['storage_lineage_v239'] = str(binding.get('storage_lineage_v239') or binding['config_lineage_v240'])
    SQLITE.set_meta('boot_restore_binding_v240', 'selected', binding)
    try:
        runtime_event('config_guard_boot_binding_finalized_v242', f"gen={cp.get('generation')}; hash={str(cp.get('config_hash') or '')[:12]}")
    except Exception:
        pass
    return cp
# v262
