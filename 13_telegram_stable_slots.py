# v262
TG_STABLE_SLOT_SCHEMA_V236 = 1
TG_STABLE_SLOT_KEY_V236 = 'slots'
TG_STABLE_HEAD_FILENAMES_V236 = {'BOT_STATE_HEAD.json', 'BOT_STATE_HEAD_v234.json'}
TG_STABLE_CONFIG_FILENAME_V236 = 'BOT_CONFIG_CHECKPOINT.json.gz'

def _tg_stable_slot_spec_v236(filename: str, explicit_key: str | None=None) -> tuple[str, str]:
    """Return stable logical slot key and stable visible filename."""
    name = str(filename or 'blob.bin')
    if explicit_key:
        key = str(explicit_key)
        if key.startswith('chat_backup:'):
            return (key, name)
        if key == 'durable:config_checkpoint':
            return (key, TG_STABLE_CONFIG_FILENAME_V236)
        return (key, name)
    low = name.lower()
    if low.startswith('delta_') and low.endswith('.json.gz'):
        return ('durable:delta', 'BOT_STATE_DELTA.json.gz')
    if (low.startswith('ledger_') or low.startswith('ledger_genesis_')) and (low.endswith('.json') or low.endswith('.json.gz')):
        return ('durable:constitution_ledger', 'BOT_STATE_LEDGER.json.gz')
    if low.startswith('restore_checkpoint_') and low.endswith('.json.gz'):
        return ('durable:restore_checkpoint', 'BOT_STATE_RESTORE_CHECKPOINT.json.gz')
    m = re.search('\\.part(\\d{3})of(\\d{3})$', low)
    if low.startswith('bot_state_') and m:
        idx = int(m.group(1))
        return (f'durable:sqlite_part:{idx:03d}', f'BOT_STATE_SQLITE_PART_{idx:03d}.bin')
    if low.startswith('config_') and low.endswith('.json.gz'):
        return ('durable:config_checkpoint', TG_STABLE_CONFIG_FILENAME_V236)
    safe = re.sub('[^a-z0-9_.:-]+', '_', low)[:120] or 'blob'
    return (f'durable:blob:{safe}', name)

def _tg_stable_legacy_message_id_v236(head: dict, slot_key: str) -> int:
    """Best-effort migration: reuse the visible v234 message instead of creating a duplicate."""
    try:
        if slot_key == 'durable:delta':
            rows = list((head or {}).get('deltas') or [])
            return int((rows[-1] if rows else {}).get('message_id') or 0)
        if slot_key == 'durable:constitution_ledger':
            rows = list((head or {}).get('constitution_ledger') or [])
            return int((rows[-1] if rows else {}).get('message_id') or 0)
        if slot_key == 'durable:restore_checkpoint':
            rows = list((head or {}).get('constitution_checkpoints') or [])
            return int((rows[-1] if rows else {}).get('message_id') or 0)
        if slot_key.startswith('durable:sqlite_part:'):
            idx = int(slot_key.rsplit(':', 1)[-1])
            for row in list(((head or {}).get('snapshot') or {}).get('parts') or []):
                if int((row or {}).get('index') or 0) == idx:
                    return int((row or {}).get('message_id') or 0)
    except Exception:
        pass
    return 0

def _tg_stable_api_call_v236(func, *args, purpose: str='telegram_stable_slot', **kwargs):
    wrapper = globals().get('_tg_call_retry')
    if callable(wrapper):
        return wrapper(func, *args, purpose=purpose, **kwargs)
    return func(*args, **kwargs)

def telegram_stable_document_upsert_v236(raw: bytes, filename: str, caption: str, *, slot_key: str | None=None, preferred_message_id: int | None=None, persist_head: bool=True, reason: str='stable_slot') -> dict:
    """Create once, then edit one Telegram channel message for this logical slot.

    The slot registry is embedded in pinned HEAD, not only in Render-local metadata.
    Therefore normal redeploy/empty-disk recovery does not cause JSON/XLSX/durable files
    to be re-sent as new channel messages.
    """
    if not telegram_durable_primary_v234():
        raise RuntimeError('Telegram durable profile is not active')
    payload = bytes(raw or b'')
    if not payload:
        raise RuntimeError('stable slot payload is empty')
    logical_key, visible_name = _tg_stable_slot_spec_v236(filename, slot_key)
    with _TG_DURABLE_LOCK_V234:
        head = telegram_durable_bootstrap_v234(False)
        slots = head.setdefault(TG_STABLE_SLOT_KEY_V236, {})
        old = dict(slots.get(logical_key) or {})
        message_id = int(old.get('message_id') or preferred_message_id or _tg_stable_legacy_message_id_v236(head, logical_key) or 0)

        def _buffer():
            buf = io.BytesIO(payload)
            buf.name = visible_name
            buf.seek(0)
            return buf
        sent = None
        recreated = False
        if message_id:
            try:
                buf = _buffer()
                sent = _tg_stable_api_call_v236(bot.edit_message_media, chat_id=int(BACKUP_CHAT_ID), message_id=message_id, media=types.InputMediaDocument(media=buf, caption=str(caption or '')[:1024]), purpose=f'stable_slot_edit:{logical_key}')
            except Exception as exc:
                try:
                    bot_journal('telegram_stable_slot_recreate_v238', int(OWNER_ID or 0) or None, f'key={logical_key}; mid={message_id}; {str(exc)[:220]}', 'WARN')
                except Exception:
                    pass
                sent = None
        if sent is None:
            buf = _buffer()
            sent = _tg_stable_api_call_v236(bot.send_document, int(BACKUP_CHAT_ID), buf, caption=str(caption or '')[:1024], purpose=f'stable_slot_create:{logical_key}')
            message_id = int(getattr(sent, 'message_id', 0) or 0)
            recreated = True
            if not message_id:
                raise RuntimeError(f'stable slot {logical_key} create returned no message_id')
        document = getattr(sent, 'document', None)
        file_id = str(getattr(document, 'file_id', '') or '')
        file_name = str(getattr(document, 'file_name', '') or visible_name)
        if not file_id:
            raise RuntimeError(f'stable slot {logical_key} returned no document file_id')
        row = {'slot_schema': TG_STABLE_SLOT_SCHEMA_V236, 'slot_key': logical_key, 'message_id': int(getattr(sent, 'message_id', message_id) or message_id), 'file_id': file_id, 'file_name': file_name, 'size': len(payload), 'sha256': hashlib.sha256(payload).hexdigest(), 'updated_at': now_local().isoformat(timespec='microseconds'), 'recreated': bool(recreated)}
        slots[logical_key] = dict(row)
        must_commit_slot = bool(persist_head or recreated)
        if must_commit_slot and (not _tg_durable_persist_head_v234(f'slot:{reason}:{logical_key}'[:120])):
            if recreated:
                try:
                    _tg_stable_api_call_v236(bot.delete_message, int(BACKUP_CHAT_ID), int(row['message_id']), purpose=f'stable_slot_rollback:{logical_key}')
                except Exception:
                    pass
                if old:
                    slots[logical_key] = old
                else:
                    slots.pop(logical_key, None)
            raise RuntimeError(f'stable slot {logical_key} changed but HEAD commit failed')
        try:
            bot_journal('telegram_stable_slot_v236', int(OWNER_ID or 0) or None, f"key={logical_key}; mid={row['message_id']}; recreate={int(recreated)}; bytes={len(payload)}")
        except Exception:
            pass
        return row

def telegram_stable_prune_sqlite_parts_v238(active_total: int) -> int:
    """Delete obsolete visible SQLite-part messages after a smaller snapshot is committed."""
    if not telegram_durable_primary_v234():
        return 0
    active_total = max(0, int(active_total or 0))
    removed = 0
    with _TG_DURABLE_LOCK_V234:
        head = telegram_durable_bootstrap_v234(False)
        slots = head.setdefault(TG_STABLE_SLOT_KEY_V236, {})
        for key in list(slots):
            m = re.fullmatch('durable:sqlite_part:(\\d{3})', str(key))
            if not m or int(m.group(1)) <= active_total:
                continue
            row = dict(slots.get(key) or {})
            mid = int(row.get('message_id') or 0)
            if mid:
                try:
                    _tg_stable_api_call_v236(bot.delete_message, int(BACKUP_CHAT_ID), mid, purpose=f'stable_slot_prune:{key}')
                except Exception:
                    pass
            slots.pop(key, None)
            removed += 1
        if removed:
            if not _tg_durable_persist_head_v234('sqlite_part_prune_v238'):
                raise RuntimeError('SQLite stable-slot prune HEAD commit failed')
    return removed

def telegram_stable_slot_registry_v236() -> dict:
    try:
        head = telegram_durable_bootstrap_v234(False)
        return copy.deepcopy((head or {}).get(TG_STABLE_SLOT_KEY_V236) or {})
    except Exception:
        return {}

def telegram_stable_slot_status_v236() -> dict:
    slots = telegram_stable_slot_registry_v236()
    return {'count': len(slots), 'keys': sorted(slots), 'chat_backup_count': sum((1 for k in slots if str(k).startswith('chat_backup:'))), 'durable_count': sum((1 for k in slots if str(k).startswith('durable:')))}
_V236_TG_SEND_BLOB_PREV = _canon_tg_durable_send_blob_v234__001

def _canon_tg_durable_send_blob_v234__002(raw: bytes, filename: str, caption: str):
    slot_key, stable_name = _tg_stable_slot_spec_v236(filename)
    return telegram_stable_document_upsert_v236(raw, stable_name, caption, slot_key=slot_key, persist_head=False, reason='durable_blob')
_V236_CONFIG_GUARD_SYNC_MEGA = _canon_config_guard_sync_remote_v234__001
_V236_CONFIG_GUARD_BOOT_MEGA = _canon_config_guard_boot_verify_v234__001

def telegram_config_checkpoint_sync_v236(cp: dict | None=None) -> bool:
    cp = dict(cp or config_guard_latest_local_v234() or {})
    if not cp:
        return False
    packed = gzip.compress(json.dumps(cp, ensure_ascii=False, separators=(',', ':'), default=str).encode('utf-8'), compresslevel=6)
    ref = telegram_stable_document_upsert_v236(packed, TG_STABLE_CONFIG_FILENAME_V236, f"🧩 Configuration checkpoint · gen {int(cp.get('generation') or 0)}", slot_key='durable:config_checkpoint', persist_head=True, reason='config_checkpoint')
    if not ref:
        return False
    SQLITE.set_meta(CONFIG_GUARD_META_KIND_V234, 'synced_hash', str(cp.get('config_hash') or ''))
    try:
        bot_journal('config_checkpoint_telegram_v236', int(OWNER_ID or 0) or None, f"gen={cp.get('generation')}; mid={ref.get('message_id')}")
    except Exception:
        pass
    return True

def telegram_config_checkpoint_load_v236(force_remote: bool=True) -> dict:
    head = telegram_durable_bootstrap_v234(bool(force_remote))
    slot = dict(((head or {}).get(TG_STABLE_SLOT_KEY_V236) or {}).get('durable:config_checkpoint') or {})
    if not slot.get('file_id'):
        return {}
    try:
        raw = _tg_durable_download_ref_v234(slot)
        cp = json.loads(gzip.decompress(raw).decode('utf-8'))
        if not isinstance(cp, dict) or not isinstance(cp.get('config'), dict):
            return {}
        if _v234_config_hash(cp.get('config') or {}) != str(cp.get('config_hash') or ''):
            raise RuntimeError('Telegram config checkpoint hash mismatch')
        return cp
    except Exception as exc:
        try:
            log_error(f'Telegram config checkpoint load v236: {exc}')
        except Exception:
            pass
        return {}

def _canon_config_guard_sync_remote_v234__002(*, recovery_write: bool=False) -> bool:
    if recovery_write:
        try:
            if callable(_V236_CONFIG_GUARD_SYNC_MEGA) and bool(_V236_CONFIG_GUARD_SYNC_MEGA(recovery_write=True)):
                return True
        except Exception:
            pass
        try:
            return bool(telegram_durable_available_v237_1() and telegram_config_checkpoint_sync_v236())
        except Exception:
            return False
    if storage_profile_v237_1() == STORAGE_PROFILE_LOCAL_V237_1:
        return True
    if telegram_durable_primary_v234():
        feature_fn = globals().get('storage_mode_feature_enabled_v240')
        if callable(feature_fn) and (not feature_fn('telegram_durable', 'config')):
            return True
        ok = False
        try:
            ok = bool(telegram_config_checkpoint_sync_v236())
        except Exception as exc:
            try:
                log_error(f'config guard Telegram sync v236: {exc}')
            except Exception:
                pass
        try:
            if mega_contour_enabled_v234() and callable(_V236_CONFIG_GUARD_SYNC_MEGA):
                pool = globals().get('MAINTENANCE_TASK_POOL') or globals().get('BACKUP_TASK_POOL')
                if pool is not None:
                    pool.submit_unique('config-guard-mega-mirror-v236', _V236_CONFIG_GUARD_SYNC_MEGA)
        except Exception:
            pass
        return ok
    return bool(_V236_CONFIG_GUARD_SYNC_MEGA(recovery_write=recovery_write)) if callable(_V236_CONFIG_GUARD_SYNC_MEGA) else False

def _v236_config_guard_boot_telegram() -> dict:
    global CONFIG_GUARD_BOOT_VERIFIED_V234, CONFIG_GUARD_LAST_REPORT_V234
    with CONFIG_GUARD_LOCK_V234:
        report = {'ok': True, 'mode': 'telegram', 'repaired': False, 'backend': 'telegram'}
        remote = telegram_config_checkpoint_load_v236(True)
        local_lineage = str(globals().get('_v239_storage_lineage', lambda create=False: '')(False) or '')
        if remote and local_lineage and (str(remote.get('storage_lineage_v239') or '') != local_lineage):
            try:
                runtime_event('telegram_config_lineage_mismatch_ignored_v240', f"local={local_lineage}; remote={remote.get('storage_lineage_v239') or '-'}", 'WARN')
            except Exception:
                pass
            remote = {}
        if not remote:
            cp = config_guard_latest_local_v234()
            if not cp:
                cp = config_guard_accept_current_v234('bootstrap_telegram_v236')
            try:
                telegram_config_checkpoint_sync_v236(cp)
            except Exception as exc:
                report['sync_warning'] = str(exc)[:240]
            report.update({'mode': 'telegram_bootstrap', 'generation': int((cp or {}).get('generation') or 0), 'metrics': (cp or {}).get('metrics')})
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
                report.update({'mode': 'telegram_restore', 'repaired': True, 'generation': rgen, 'changed': changed, 'metrics': remote.get('metrics')})
            else:
                if curgen <= 0:
                    cp = config_guard_accept_current_v234('generation_reanchor_telegram_v236')
                    curgen = int(cp.get('generation') or 0)
                else:
                    cp = _v234_checkpoint_from_projection(cur, curgen, 'boot_current_telegram_v236')
                    SQLITE.set_meta(CONFIG_GUARD_META_KIND_V234, 'latest', cp)
                    SQLITE.set_meta(CONFIG_GUARD_META_KIND_V234, 'generation', curgen)
                    SQLITE.set_meta(CONFIG_GUARD_META_KIND_V234, 'last_signature', curhash)
                    if curhash == rhash:
                        SQLITE.set_meta(CONFIG_GUARD_META_KIND_V234, 'synced_hash', rhash)
                    else:
                        _v234_schedule_config_sync(1.0)
                report.update({'mode': 'telegram_current_ok' if curhash == rhash else 'telegram_current_newer', 'generation': curgen, 'metrics': _v234_config_metrics(cur)})
        CONFIG_GUARD_BOOT_VERIFIED_V234 = True
        CONFIG_GUARD_LAST_REPORT_V234 = report
        try:
            runtime_event('config_guard_boot_telegram_v236', json.dumps(report, ensure_ascii=False, default=str)[:1200], 'INFO')
        except Exception:
            pass
        return report

def _canon_config_guard_boot_verify_v234__002() -> dict:
    if storage_profile_v237_1() == STORAGE_PROFILE_LOCAL_V237_1:
        return _V236_CONFIG_GUARD_BOOT_MEGA() if callable(_V236_CONFIG_GUARD_BOOT_MEGA) else {'ok': True, 'mode': 'local_only_v237_1'}
    if telegram_durable_primary_v234():
        return _v236_config_guard_boot_telegram()
    return _V236_CONFIG_GUARD_BOOT_MEGA() if callable(_V236_CONFIG_GUARD_BOOT_MEGA) else {'ok': False, 'reason': 'config guard unavailable'}

def telegram_constitution_bootstrap_genesis_v236(live: dict) -> dict:
    seq = int((live or {}).get('integrity_seq') or 0)
    at = now_local().isoformat(timespec='microseconds')
    event = {'kind': 'telegram_bot_finance_ledger_genesis', 'schema_version': globals().get('DATA_CONSTITUTION_SCHEMA', 1), 'bot_version': globals().get('VERSION', ''), 'seq': seq, 'chat_id': int(OWNER_ID or 0), 'action': 'genesis', 'record': None, 'details': {'semantic_manifest': copy.deepcopy(live or {})}, 'integrity_hash': str((live or {}).get('integrity_anchor') or ''), 'at': at}
    event['event_hash'] = hashlib.sha256(json.dumps(event, ensure_ascii=False, sort_keys=True, separators=(',', ':'), default=str).encode('utf-8')).hexdigest()
    token = f"ledger_genesis_{re.sub('[^0-9]', '', at)[:20]}_{event['event_hash'][:16]}.json"
    SQLITE.set_meta('data_constitution_pending', token, event)
    try:
        with _CONSTITUTION_LEDGER_ASYNC_LOCK:
            _CONSTITUTION_LEDGER_ASYNC_STATE[token] = {'state': 'pending', 'seq': seq, 'at': time.monotonic(), 'backend': 'telegram'}
    except Exception:
        pass
    if not telegram_constitution_ledger_upload_v234(token, event, token, 0):
        raise RuntimeError('Telegram constitution genesis ledger witness failed')
    if not telegram_upload_sqlite_snapshot_v234(force=True):
        raise RuntimeError('Telegram constitution genesis SQLite snapshot failed')
    head = telegram_durable_bootstrap_v234(False)
    return {'ok': True, 'existing': False, 'seq': seq, 'backend': 'telegram', 'active': copy.deepcopy((head or {}).get('snapshot') or {})}
try:
    _v177_legacy_0006_bot_journal('telegram_stable_slots_ready_v236', int(OWNER_ID or 0) or None, 'stable_head_registry=1; edit_or_recreate=1; config_checkpoint=telegram')
except Exception:
    pass
# v262
