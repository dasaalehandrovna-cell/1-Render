# v262

# --- ИСТОЧНИК: 12_telegram_durable.py ---
TG_DURABLE_SCHEMA_V234 = 1
TG_DURABLE_HEAD_KIND_V234 = 'telegram_bot_durable_head_v234'
TG_DURABLE_HEAD_FILENAME_V234 = 'BOT_STATE_HEAD.json'
TG_DURABLE_HEAD_LEGACY_FILENAMES_V236 = {'BOT_STATE_HEAD.json', 'BOT_STATE_HEAD_v234.json'}
TG_DURABLE_META_KIND_V234 = 'telegram_durable_v234'
TG_DURABLE_META_KEY_V234 = 'head'
TG_DURABLE_CHUNK_BYTES_V234 = max(2 * 1024 * 1024, min(18 * 1024 * 1024, int(os.getenv('TELEGRAM_DURABLE_CHUNK_BYTES', str(18 * 1024 * 1024)) or 18 * 1024 * 1024)))
TG_DURABLE_DELTA_KEEP_V234 = max(20, min(1500, int(os.getenv('TELEGRAM_DURABLE_DELTA_KEEP', '500') or '500')))
TG_DURABLE_TASK_DONE_KEEP_V234 = max(10, min(300, int(os.getenv('TELEGRAM_DURABLE_TASK_DONE_KEEP', '50') or '50')))
TG_DURABLE_FULL_QUIET_SECONDS_V234 = max(30.0, min(1800.0, float(os.getenv('TELEGRAM_DURABLE_FULL_QUIET_SECONDS', '180') or '180')))
TG_DURABLE_FULL_MAX_SECONDS_V234 = max(TG_DURABLE_FULL_QUIET_SECONDS_V234, min(7200.0, float(os.getenv('TELEGRAM_DURABLE_FULL_MAX_SECONDS', '900') or '900')))
TG_DURABLE_ENABLED_V234 = str(os.getenv('TELEGRAM_DURABLE_ENABLED', '1') or '1').strip().casefold() not in {'0', 'false', 'no', 'off', 'выкл'}
TG_DURABLE_PIN_HEAD_V234 = str(os.getenv('TELEGRAM_DURABLE_PIN_HEAD', '1') or '1').strip().casefold() not in {'0', 'false', 'no', 'off', 'выкл'}
_TG_DURABLE_LOCK_V234 = threading.RLock()
_TG_DURABLE_HEAD_CACHE_V234 = None
_TG_DURABLE_HEAD_META_V234 = {}
_TG_DURABLE_LAST_ERROR_V234 = ''
_TG_DURABLE_STATS_V234 = {'head_writes': 0, 'head_errors': 0, 'task_writes': 0, 'task_recovers': 0, 'delta_uploads': 0, 'delta_errors': 0, 'snapshot_uploads': 0, 'snapshot_errors': 0, 'restore_snapshots': 0, 'restore_deltas': 0, 'last_head_at': '', 'last_delta_at': '', 'last_snapshot_at': '', 'last_restore_at': ''}
_TG_DURABLE_SNAPSHOT_LAST_SUCCESS_MONO_V234 = time.monotonic()
_TG_DURABLE_SNAPSHOT_LAST_CHANGE_MONO_V234 = time.monotonic()
_TG_DURABLE_SNAPSHOT_PENDING_V234 = False
_TG_DURABLE_SNAPSHOT_EXEC_LOCK_V238 = threading.Lock()
TG_DURABLE_SNAPSHOT_MIN_REWRITE_SECONDS_V238 = max(15.0, min(300.0, float(os.getenv('TELEGRAM_DURABLE_SNAPSHOT_MIN_REWRITE_SECONDS', '60') or '60')))
_V234_MEGA_TASKS_ACTIVE = _canon_mega_tasks_active__001
_V234_MEGA_TASK_KNOWN_STATE = _canon_mega_task_known_state__001
_V234_MEGA_TASK_UPLOAD_PENDING = _canon_mega_task_upload_new_pending__001
_V234_MEGA_TASK_BEGIN = _canon_mega_task_begin__001
_V234_MEGA_TASK_FINISH = _v177_legacy_0071_mega_task_finish
_V234_MEGA_TASK_REFRESH = _canon_mega_task_refresh_registry__001
_V234_MEGA_TASK_RECOVERY = _canon_schedule_mega_task_recovery__001
_V234_MEGA_SAFE_FAILED_REPAIR = _canon_schedule_safe_failed_task_repairs__001
_V234_MEGA_TASK_STATS = _v177_legacy_0064_mega_task_registry_stats
_V234_MEGA_RUN_DELTA_BATCH = _canon_run_delta_batch__001
_V234_MEGA_SCHEDULE_DELTA = _canon_schedule_delta_backup__001
_V234_MEGA_CRITICAL_DELTA = _canon_persist_critical_delta_now__001
_V234_MEGA_CONFIG_BACKUP = _canon_schedule_config_backup_for_chats__001
_V234_MEGA_LOWRAM_APPLY_DELTAS = _canon_lowram_apply_deltas_after_db_snapshot__001

def _tg_v234_root_settings() -> dict:
    try:
        return data.setdefault('_global_settings', {})
    except Exception:
        return {}
STORAGE_PROFILE_KEY_V237_1 = 'storage_profile_v237_1'
STORAGE_PROFILE_LOCAL_V237_1 = 'render'
STORAGE_PROFILE_TELEGRAM_V237_1 = 'telegram_durable'
STORAGE_PROFILE_MEGA_V237_1 = 'mega'
_STORAGE_PROFILE_BOOT_HINT_V237_1 = ''
_STORAGE_PROFILE_BOOT_SOURCE_V238 = ''
_STORAGE_PROFILE_RESTORE_BACKEND_V246 = ''
_STORAGE_PROFILE_REMOTE_EVIDENCE_V246 = {}
_STORAGE_PROFILE_SWITCH_LOCK_V237_1 = threading.RLock()
_STORAGE_CONTROL_REMOTE_LOCK_V246 = threading.RLock()
STORAGE_CONTROL_FILENAME_V246 = 'storage_control.json'
STORAGE_CONTROL_KIND_V246 = 'telegram_bot_storage_control_v246'
STORAGE_CONTROL_SCHEMA_V246 = 1

def _storage_control_remote_v246() -> str:
    return str(globals().get('MEGA_BACKUP_DIR') or '/TelegramBotBackups').rstrip('/') + '/' + STORAGE_CONTROL_FILENAME_V246

def _v246_iso_epoch(value) -> float:
    raw = str(value or '').strip()
    if not raw:
        return 0.0
    try:
        dt = datetime.fromisoformat(raw.replace('Z', '+00:00'))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return float(dt.timestamp())
    except Exception:
        return 0.0

def mega_storage_control_read_v246() -> dict | None:
    """Read the tiny mode beacon even while normal MEGA storage is disabled."""
    if not bool(MEGA_ENABLED and MEGA_EMAIL and MEGA_PASSWORD):
        return None
    work = tempfile.mkdtemp(prefix='storage_control_v246_')
    try:
        if not mega_login_if_needed(control_plane=True):
            return None
        remote = _storage_control_remote_v246()
        res = _mega_run('mega-get', [remote, work], check=False, timeout=min(60, int(MEGA_TIMEOUT)), control_plane=True)
        if int(getattr(res, 'returncode', 1)) != 0:
            return None
        candidates = list(Path(work).rglob(STORAGE_CONTROL_FILENAME_V246))
        if not candidates:
            return None
        obj = json.loads(candidates[0].read_text(encoding='utf-8'))
        if not isinstance(obj, dict) or str(obj.get('kind') or '') != STORAGE_CONTROL_KIND_V246:
            return None
        raw_mode = str(obj.get('mode') or '').strip()
        if not raw_mode:
            return None
        mode = _storage_profile_normalize_v237_1(raw_mode)
        if mode not in {STORAGE_PROFILE_LOCAL_V237_1, STORAGE_PROFILE_TELEGRAM_V237_1, STORAGE_PROFILE_MEGA_V237_1}:
            return None
        obj['mode'] = mode
        return obj
    except Exception as exc:
        try:
            bot_journal('storage_control_read_v246', int(OWNER_ID or 0) or None, str(exc)[:240], 'WARN')
        except Exception:
            pass
        return None
    finally:
        shutil.rmtree(work, ignore_errors=True)

def mega_storage_control_write_v246(mode: str, reason: str='switch', epoch: int | None=None) -> bool:
    """Publish one canonical MEGA mode beacon using candidate -> replace."""
    mode = _storage_profile_normalize_v237_1(mode)
    if not bool(MEGA_ENABLED and MEGA_EMAIL and MEGA_PASSWORD):
        return False
    with _STORAGE_CONTROL_REMOTE_LOCK_V246:
        if epoch is not None and int(epoch) != int(globals().get('_V241_STORAGE_EPOCH', 0) or 0):
            return False
        work = tempfile.mkdtemp(prefix='storage_control_publish_v246_')
        candidate_remote = ''
        try:
            if not mega_login_if_needed(control_plane=True):
                return False
            root = str(globals().get('MEGA_BACKUP_DIR') or '/TelegramBotBackups').rstrip('/')
            payload = {
                'kind': STORAGE_CONTROL_KIND_V246,
                'schema_version': STORAGE_CONTROL_SCHEMA_V246,
                'mode': mode,
                'updated_at': now_local().isoformat(timespec='microseconds'),
                'bot_version': str(globals().get('VERSION') or 'выс-262'),
                'epoch': int(globals().get('_V241_STORAGE_EPOCH', 0) or 0),
                'reason': str(reason or 'switch')[:120],
            }
            stamp = now_local().strftime('%Y%m%d_%H%M%S_%f')
            candidate_name = f'storage_control_candidate_{stamp}.json'
            local = Path(work) / candidate_name
            local.write_text(json.dumps(payload, ensure_ascii=False, separators=(',', ':')) + '\n', encoding='utf-8')
            _mega_run('mega-mkdir', [root], check=False, timeout=30, control_plane=True)
            put = _mega_run('mega-put', [str(local), root], check=False, timeout=min(60, int(MEGA_TIMEOUT)), control_plane=True)
            if int(getattr(put, 'returncode', 1)) != 0:
                return False
            candidate_remote = root + '/' + candidate_name
            final_remote = root + '/' + STORAGE_CONTROL_FILENAME_V246
            _mega_run('mega-rm', [final_remote], check=False, timeout=30, control_plane=True)
            mv = _mega_run('mega-mv', [candidate_remote, final_remote], check=False, timeout=30, control_plane=True)
            if int(getattr(mv, 'returncode', 1)) != 0:
                return False
            verify = mega_storage_control_read_v246() or {}
            return str(verify.get('mode') or '') == mode and int(verify.get('epoch') or 0) == int(payload['epoch'])
        except Exception as exc:
            try:
                bot_journal('storage_control_write_v246', int(OWNER_ID or 0) or None, str(exc)[:240], 'WARN')
            except Exception:
                pass
            return False
        finally:
            if candidate_remote:
                try:
                    _mega_run('mega-rm', [candidate_remote], check=False, timeout=20, control_plane=True)
                except Exception:
                    pass
            shutil.rmtree(work, ignore_errors=True)

def _v246_telegram_restore_evidence() -> dict:
    out = {'backend': 'telegram', 'available': False, 'full': False, 'fresh_at': '', 'fresh_epoch': 0.0, 'richness': 1, 'detail': ''}
    if not telegram_durable_available_v237_1():
        return out
    try:
        head, _meta = _tg_durable_load_remote_head_v234()
        if not isinstance(head, dict):
            return out
        snap = head.get('snapshot') or {}
        deltas = [x for x in head.get('deltas') or [] if isinstance(x, dict)]
        stamps = [str(head.get('updated_at') or ''), str((snap or {}).get('created_at') or '')] + [str(x.get('created_at') or '') for x in deltas]
        fresh = max(stamps, key=_v246_iso_epoch) if stamps else ''
        parts = list((snap or {}).get('parts') or []) if isinstance(snap, dict) else []
        out.update({'available': True, 'full': bool(parts and (snap or {}).get('sha256')), 'fresh_at': fresh, 'fresh_epoch': _v246_iso_epoch(fresh), 'detail': f"snapshot_parts={len(parts)}; deltas={len(deltas)}; head_gen={int(head.get('generation') or 0)}"})
    except Exception as exc:
        out['detail'] = str(exc)[:240]
    return out

def _v246_mega_restore_evidence() -> dict:
    """Describe the effective MEGA truth: full DB generation plus newest recoverable delta."""
    out = {'backend': 'mega', 'available': False, 'full': False, 'fresh_at': '', 'fresh_epoch': 0.0, 'richness': 2, 'detail': ''}
    if not bool(MEGA_ENABLED and MEGA_EMAIL and MEGA_PASSWORD):
        return out
    work = tempfile.mkdtemp(prefix='mega_evidence_v246_')
    try:
        if not mega_login_if_needed(control_plane=True):
            return out
        remote = (constitution_current_manifest_remote() if callable(globals().get('constitution_current_manifest_remote')) else str(globals().get('MEGA_BACKUP_DIR') or '/TelegramBotBackups').rstrip('/') + '/database/current_manifest.json')
        res = _mega_run('mega-get', [remote, work], check=False, timeout=min(60, int(MEGA_TIMEOUT)), control_plane=True)
        if int(getattr(res, 'returncode', 1)) != 0:
            return out
        candidates = list(Path(work).rglob('current_manifest.json'))
        if not candidates:
            candidates = list(Path(work).rglob('*.json'))
        if not candidates:
            return out
        manifest = json.loads(candidates[0].read_text(encoding='utf-8'))
        if not isinstance(manifest, dict):
            return out
        created = str(manifest.get('created_at') or manifest.get('snapshot_created_at') or '')
        full = bool(manifest.get('remote_generation') and (manifest.get('sqlite_sha256') or manifest.get('semantic_hash')))

        latest_delta_path = ''
        latest_delta_epoch = 0.0
        latest_delta_at = ''
        roots = []
        try:
            roots.append(str(mega_delta_remote_root()))
        except Exception:
            pass
        try:
            shard_root = str(globals().get('MEGA_SHARD_CHATS_ROOT_V240') or '').strip()
            if shard_root:
                roots.append(shard_root)
        except Exception:
            pass
        for root in dict.fromkeys(x for x in roots if x):
            try:
                found = _mega_run('mega-find', [root, '--pattern=delta_*.json', '--type=f'], check=False, timeout=60, control_plane=True)
                if int(getattr(found, 'returncode', 1)) != 0:
                    continue
                for row in (getattr(found, 'stdout', '') or '').splitlines():
                    path = str(row or '').strip()
                    name = os.path.basename(path)
                    m = re.search(r'delta_(\d{8})_(\d{6})_(\d{6})_', name)
                    if not m:
                        continue
                    try:
                        dt = datetime.strptime(''.join(m.groups()), '%Y%m%d%H%M%S%f').replace(tzinfo=get_tz())
                        epoch = float(dt.timestamp())
                    except Exception:
                        continue
                    if epoch > latest_delta_epoch:
                        latest_delta_epoch = epoch
                        latest_delta_path = path
                        latest_delta_at = dt.isoformat(timespec='microseconds')
            except Exception:
                pass

        snapshot_epoch = _v246_iso_epoch(created)
        if latest_delta_epoch > snapshot_epoch:
            fresh_at, fresh_epoch = latest_delta_at, latest_delta_epoch
        else:
            fresh_at, fresh_epoch = created, snapshot_epoch
        out.update({
            'available': True,
            'full': full,
            'fresh_at': fresh_at,
            'fresh_epoch': fresh_epoch,
            'detail': (
                f"generation={manifest.get('generation') or '—'}; "
                f"records={manifest.get('total_records', '—')}; "
                f"ledger={manifest.get('ledger_highwater_seq', '—')}; "
                f"latest_delta={os.path.basename(latest_delta_path) if latest_delta_path else '—'}"
            ),
        })
    except Exception as exc:
        out['detail'] = str(exc)[:240]
    finally:
        shutil.rmtree(work, ignore_errors=True)
    return out

def _v246_best_render_restore_backend() -> str:
    """Prefer a complete snapshot first, then the freshest effective source; MEGA wins exact ties."""
    global _STORAGE_PROFILE_REMOTE_EVIDENCE_V246
    tg = _v246_telegram_restore_evidence()
    mega = _v246_mega_restore_evidence()
    _STORAGE_PROFILE_REMOTE_EVIDENCE_V246 = {'telegram': tg, 'mega': mega}
    rows = [x for x in (tg, mega) if x.get('available')]
    if not rows:
        return 'local'
    best = max(rows, key=lambda x: (1 if x.get('full') else 0, float(x.get('fresh_epoch') or 0.0), int(x.get('richness') or 0)))
    return str(best.get('backend') or 'local')

def _v246_schedule_storage_control_persist(mode: str, epoch: int, reason: str='switch') -> None:
    mode = _storage_profile_normalize_v237_1(mode)
    def _job(attempt: int=0):
        if int(epoch) != int(globals().get('_V241_STORAGE_EPOCH', 0) or 0):
            return
        mega_ok = mega_storage_control_write_v246(mode, reason=reason, epoch=epoch)
        try:
            if mode == STORAGE_PROFILE_TELEGRAM_V237_1 and telegram_durable_primary_v234():
                telegram_durable_persist_controls_v234()
        except Exception:
            pass
        if (not mega_ok) and attempt < 3 and int(epoch) == int(globals().get('_V241_STORAGE_EPOCH', 0) or 0):
            try:
                DELAYED_SCHEDULER.schedule('storage-control-retry-v246', 2.0 * (attempt + 1), _job, attempt + 1)
            except Exception:
                pass
    try:
        DELAYED_SCHEDULER.schedule('storage-control-persist-v246', 0.03, _job, 0)
    except Exception:
        try:
            pool = globals().get('GENERAL_TASK_POOL')
            if pool is not None:
                pool.submit('storage-control-persist-v246', _job, 0)
        except Exception:
            pass

def _storage_profile_normalize_v237_1(value: str) -> str:
    raw = str(value or '').strip().casefold()
    if raw in {'render', 'render_only', 'render_telegram', 'render+telegram', 'local', 'local_only', 'только render', 'только render + telegram'}:
        return STORAGE_PROFILE_LOCAL_V237_1
    if raw in {'mega', 'мега', 'return_mega', 'restore_mega'}:
        return STORAGE_PROFILE_MEGA_V237_1
    return STORAGE_PROFILE_TELEGRAM_V237_1

def _storage_profile_from_root_v237_1(root_obj) -> str:
    if not isinstance(root_obj, dict):
        return ''
    gs = root_obj.get('_global_settings') if isinstance(root_obj.get('_global_settings'), dict) else root_obj
    raw = str((gs or {}).get(STORAGE_PROFILE_KEY_V237_1) or '').strip()
    if raw:
        return _storage_profile_normalize_v237_1(raw)
    if bool((gs or {}).get('render_telegram_only_v233', False)):
        return STORAGE_PROFILE_LOCAL_V237_1
    if bool((gs or {}).get('mega_contour_enabled_v234', False)):
        return STORAGE_PROFILE_MEGA_V237_1
    return ''

def storage_profile_v237_1() -> str:
    try:
        raw = str(os.getenv('RENDER_TELEGRAM_ONLY', '') or '').strip().casefold()
        if raw in {'1', 'true', 'yes', 'on', 'вкл'}:
            return STORAGE_PROFILE_LOCAL_V237_1
    except Exception:
        pass
    try:
        found = _storage_profile_from_root_v237_1(_tg_v234_root_settings())
        if found:
            return found
    except Exception:
        pass
    if _STORAGE_PROFILE_BOOT_HINT_V237_1:
        return _storage_profile_normalize_v237_1(_STORAGE_PROFILE_BOOT_HINT_V237_1)
    return STORAGE_PROFILE_MEGA_V237_1

def telegram_durable_available_v237_1() -> bool:
    if not TG_DURABLE_ENABLED_V234 or not BACKUP_CHAT_ID:
        return False
    try:
        int(BACKUP_CHAT_ID)
        return True
    except Exception:
        return False

def telegram_durable_configured_v234() -> bool:
    return telegram_durable_available_v237_1()

def telegram_durable_primary_v234() -> bool:
    return bool(telegram_durable_available_v237_1() and storage_profile_v237_1() == STORAGE_PROFILE_TELEGRAM_V237_1)

def mega_contour_enabled_v234() -> bool:
    return storage_profile_v237_1() == STORAGE_PROFILE_MEGA_V237_1

def storage_profile_status_v237_1() -> dict:
    profile = storage_profile_v237_1()
    return {'profile': profile, 'render': profile == STORAGE_PROFILE_LOCAL_V237_1, 'render_telegram': profile == STORAGE_PROFILE_LOCAL_V237_1, 'telegram_durable': profile == STORAGE_PROFILE_TELEGRAM_V237_1 and telegram_durable_available_v237_1(), 'mega': profile == STORAGE_PROFILE_MEGA_V237_1, 'telegram_available': telegram_durable_available_v237_1(), 'mega_configured': bool(MEGA_ENABLED and MEGA_EMAIL and MEGA_PASSWORD), 'mega_root': str(globals().get('MEGA_BACKUP_DIR') or '')}

def secret_storage_backend_v234() -> str:
    raw_env = str(os.getenv('SECRET_STORAGE_BACKEND', '') or '').strip().casefold()
    if raw_env in {'telegram', 'tg', 'channel', 'канал'}:
        return 'telegram'
    if raw_env in {'mega', 'мега'}:
        return 'mega'
    try:
        raw = str(_tg_v234_root_settings().get('secret_storage_backend_v234') or 'telegram').strip().casefold()
    except Exception:
        raw = 'telegram'
    return 'mega' if raw == 'mega' else 'telegram'

def _secret_storage_migration_state_v234() -> dict:
    try:
        row = _tg_v234_root_settings().get('secret_storage_migration_v234') or {}
        return dict(row) if isinstance(row, dict) else {}
    except Exception:
        return {}

def _secret_mega_prerequisites_v234() -> bool:
    try:
        return bool(mega_contour_enabled_v234() and (not callable(globals().get('external_access_allowed_v233')) or external_access_allowed_v233('mega')) and MEGA_ENABLED and MEGA_EMAIL and MEGA_PASSWORD)
    except Exception:
        return False

def secret_storage_effective_backend_v234() -> str:
    requested = secret_storage_backend_v234()
    if requested != 'mega':
        return 'telegram'
    if not _secret_mega_prerequisites_v234():
        return 'telegram' if telegram_durable_configured_v234() else 'mega'
    migration = _secret_storage_migration_state_v234()
    if str(migration.get('target') or '') == 'mega' and str(migration.get('state') or '') not in {'done', 'not_needed'}:
        return 'telegram'
    return 'mega'

def _tg_durable_default_head_v234() -> dict:
    return {'kind': TG_DURABLE_HEAD_KIND_V234, 'schema_version': TG_DURABLE_SCHEMA_V234, 'bot_version': globals().get('VERSION', ''), 'generation': 0, 'created_at': now_local().isoformat(timespec='seconds') if 'now_local' in globals() else datetime.now(timezone.utc).isoformat(), 'updated_at': '', 'snapshot': None, 'deltas': [], 'tasks': {}, 'controls': {'storage_profile': storage_profile_v237_1(), 'render_telegram_only': storage_profile_v237_1() == STORAGE_PROFILE_LOCAL_V237_1, 'telegram_durable_enabled': storage_profile_v237_1() == STORAGE_PROFILE_TELEGRAM_V237_1, 'mega_contour_enabled': storage_profile_v237_1() == STORAGE_PROFILE_MEGA_V237_1, 'secret_storage_backend': 'mega' if storage_profile_v237_1() == STORAGE_PROFILE_MEGA_V237_1 else 'telegram'}}

def _tg_durable_valid_head_v234(obj) -> bool:
    return isinstance(obj, dict) and str(obj.get('kind') or '') == TG_DURABLE_HEAD_KIND_V234 and (int(obj.get('schema_version') or 0) == TG_DURABLE_SCHEMA_V234)

def _tg_durable_sync_controls_from_head_v234(head: dict) -> None:
    try:
        controls = (head or {}).get('controls') or {}
        root = _tg_v234_root_settings()
        remote_profile = str(controls.get('storage_profile') or '').strip()
        if remote_profile and STORAGE_PROFILE_KEY_V237_1 not in root:
            root[STORAGE_PROFILE_KEY_V237_1] = _storage_profile_normalize_v237_1(remote_profile)
        if 'mega_contour_enabled' in controls and 'mega_contour_enabled_v234' not in root:
            root['mega_contour_enabled_v234'] = bool(controls.get('mega_contour_enabled'))
        if controls.get('secret_storage_backend') in {'telegram', 'mega'} and 'secret_storage_backend_v234' not in root:
            root['secret_storage_backend_v234'] = str(controls.get('secret_storage_backend'))
    except Exception:
        pass

def _tg_durable_sync_head_controls_v234(head: dict) -> None:
    controls = head.setdefault('controls', {})
    profile = storage_profile_v237_1()
    controls['storage_profile'] = profile
    controls['render_telegram_only'] = profile == STORAGE_PROFILE_LOCAL_V237_1
    controls['telegram_durable_enabled'] = profile == STORAGE_PROFILE_TELEGRAM_V237_1
    controls['mega_contour_enabled'] = profile == STORAGE_PROFILE_MEGA_V237_1
    controls['secret_storage_backend'] = str(secret_storage_backend_v234())

def _tg_durable_load_local_v234() -> tuple[dict | None, dict]:
    try:
        row = SQLITE.get_meta(TG_DURABLE_META_KIND_V234, TG_DURABLE_META_KEY_V234, {}) or {}
        head = row.get('head') if isinstance(row, dict) else None
        meta = row.get('meta') if isinstance(row, dict) else {}
        if _tg_durable_valid_head_v234(head):
            return (head, dict(meta or {}))
    except Exception:
        pass
    return (None, {})

def _tg_durable_save_local_v234(head: dict, meta: dict | None=None) -> None:
    try:
        SQLITE.set_meta(TG_DURABLE_META_KIND_V234, TG_DURABLE_META_KEY_V234, {'head': head, 'meta': dict(meta or {})})
    except Exception as exc:
        try:
            log_error(f'TG durable local head save: {exc}')
        except Exception:
            pass

def _tg_durable_head_bytes_v234(head: dict) -> bytes:
    return (json.dumps(head, ensure_ascii=False, separators=(',', ':'), default=str) + '\n').encode('utf-8')

def _tg_durable_download_file_id_v234(file_id: str) -> bytes:
    info = bot.get_file(str(file_id))
    return bytes(bot.download_file(info.file_path) or b'')

def _tg_durable_load_remote_head_v234() -> tuple[dict | None, dict]:
    global _TG_DURABLE_LAST_ERROR_V234
    if not telegram_durable_configured_v234():
        return (None, {})
    try:
        chat = bot.get_chat(int(BACKUP_CHAT_ID))
        pinned = getattr(chat, 'pinned_message', None)
        doc = getattr(pinned, 'document', None) if pinned is not None else None
        if pinned is None or doc is None:
            return (None, {})
        fname = str(getattr(doc, 'file_name', '') or '')
        if fname not in TG_DURABLE_HEAD_LEGACY_FILENAMES_V236:
            return (None, {})
        raw = _tg_durable_download_file_id_v234(getattr(doc, 'file_id', ''))
        obj = json.loads(raw.decode('utf-8')) if raw else None
        if not _tg_durable_valid_head_v234(obj):
            raise RuntimeError('pinned durable HEAD has invalid schema')
        meta = {'message_id': int(getattr(pinned, 'message_id', 0) or 0), 'file_id': str(getattr(doc, 'file_id', '') or ''), 'pinned': True}
        _TG_DURABLE_LAST_ERROR_V234 = ''
        _tg_durable_sync_controls_from_head_v234(obj)
        return (obj, meta)
    except Exception as exc:
        _TG_DURABLE_LAST_ERROR_V234 = str(exc)[:500]
        try:
            log_error(f'TG durable HEAD load: {exc}')
        except Exception:
            pass
        return (None, {})

def telegram_durable_bootstrap_v234(force_remote: bool=False) -> dict:
    global _TG_DURABLE_HEAD_CACHE_V234, _TG_DURABLE_HEAD_META_V234
    with _TG_DURABLE_LOCK_V234:
        if _TG_DURABLE_HEAD_CACHE_V234 is not None and (not force_remote):
            return _TG_DURABLE_HEAD_CACHE_V234
        head = None
        meta = {}
        if force_remote:
            head, meta = _tg_durable_load_remote_head_v234()
        if head is None:
            head, meta = _tg_durable_load_local_v234()
        if head is None and (not force_remote):
            remote_head, remote_meta = _tg_durable_load_remote_head_v234()
            if remote_head is not None:
                head, meta = (remote_head, remote_meta)
        if head is None:
            head = _tg_durable_default_head_v234()
        _tg_durable_sync_head_controls_v234(head)
        _TG_DURABLE_HEAD_CACHE_V234 = head
        _TG_DURABLE_HEAD_META_V234 = dict(meta or {})
        _tg_durable_save_local_v234(head, meta)
        return head

def _tg_durable_persist_head_v234(reason: str='state') -> bool:
    global _TG_DURABLE_HEAD_CACHE_V234, _TG_DURABLE_HEAD_META_V234, _TG_DURABLE_LAST_ERROR_V234
    # v246: backup-channel writes belong only to the Telegram durable profile.
    # Render-only may read Telegram once during recovery, but never writes to the backup channel.
    if not telegram_durable_primary_v234():
        return False
    with _TG_DURABLE_LOCK_V234:
        head = telegram_durable_bootstrap_v234(False)
        _tg_durable_sync_head_controls_v234(head)
        head['generation'] = int(head.get('generation') or 0) + 1
        head['updated_at'] = now_local().isoformat(timespec='microseconds')
        head['bot_version'] = globals().get('VERSION', '')
        raw = _tg_durable_head_bytes_v234(head)
        buf = io.BytesIO(raw)
        buf.name = TG_DURABLE_HEAD_FILENAME_V234
        caption = f"🧭 BOT STATE HEAD · gen {head['generation']} · {str(reason)[:80]}"
        meta = dict(_TG_DURABLE_HEAD_META_V234 or {})
        message_id = int(meta.get('message_id') or 0)
        try:
            sent = None
            if message_id:
                try:
                    sent = bot.edit_message_media(chat_id=int(BACKUP_CHAT_ID), message_id=message_id, media=types.InputMediaDocument(media=buf, caption=caption))
                except Exception:
                    sent = None
            if sent is None:
                buf.seek(0)
                sent = bot.send_document(int(BACKUP_CHAT_ID), buf, caption=caption)
                message_id = int(getattr(sent, 'message_id', 0) or 0)
                if not message_id:
                    raise RuntimeError('HEAD send returned no message_id')
                if TG_DURABLE_PIN_HEAD_V234:
                    try:
                        bot.pin_chat_message(int(BACKUP_CHAT_ID), message_id, disable_notification=True)
                    except TypeError:
                        bot.pin_chat_message(int(BACKUP_CHAT_ID), message_id)
                    except Exception as pin_exc:
                        try:
                            bot.delete_message(int(BACKUP_CHAT_ID), message_id)
                        except Exception:
                            pass
                        raise RuntimeError(f'HEAD created but cannot be pinned: {pin_exc}')
            doc = getattr(sent, 'document', None)
            _TG_DURABLE_HEAD_META_V234 = {'message_id': int(getattr(sent, 'message_id', message_id) or message_id), 'file_id': str(getattr(doc, 'file_id', '') or ''), 'pinned': True}
            _TG_DURABLE_HEAD_CACHE_V234 = head
            _tg_durable_save_local_v234(head, _TG_DURABLE_HEAD_META_V234)
            _TG_DURABLE_STATS_V234['head_writes'] += 1
            _TG_DURABLE_STATS_V234['last_head_at'] = str(head.get('updated_at') or '')
            _TG_DURABLE_LAST_ERROR_V234 = ''
            return True
        except Exception as exc:
            _TG_DURABLE_STATS_V234['head_errors'] += 1
            _TG_DURABLE_LAST_ERROR_V234 = str(exc)[:500]
            try:
                log_error(f'TG durable HEAD persist({reason}): {exc}')
            except Exception:
                pass
            return False

def telegram_durable_persist_controls_v234() -> bool:
    if not telegram_durable_configured_v234():
        return False
    return _tg_durable_persist_head_v234('controls')

def storage_profile_bootstrap_v237_1() -> str:
    """v246 resolve selected mode from the MEGA control beacon before restore.

    The selected *running* profile and the one-time *restore backend* are separate.
    In Render-only mode the bot may recover from Telegram/MEGA, then continues with
    both remote backup contours disabled.
    """
    global _STORAGE_PROFILE_BOOT_HINT_V237_1, _STORAGE_PROFILE_BOOT_SOURCE_V238, _STORAGE_PROFILE_RESTORE_BACKEND_V246
    # v246: the MEGA control beacon is the canonical cross-deploy mode selector.
    # The legacy Render env flag is now only an emergency fallback when the beacon
    # is absent/unreadable, so a stale Render variable cannot override a deliberate
    # Telegram/MEGA selection made before deploy.
    control = mega_storage_control_read_v246()
    if isinstance(control, dict):
        selected = _storage_profile_normalize_v237_1(control.get('mode'))
        _STORAGE_PROFILE_BOOT_HINT_V237_1 = selected
        _STORAGE_PROFILE_BOOT_SOURCE_V238 = 'mega:storage_control_v246'
        if selected == STORAGE_PROFILE_LOCAL_V237_1:
            _STORAGE_PROFILE_RESTORE_BACKEND_V246 = _v246_best_render_restore_backend()
        elif selected == STORAGE_PROFILE_TELEGRAM_V237_1:
            _STORAGE_PROFILE_RESTORE_BACKEND_V246 = 'telegram' if telegram_durable_available_v237_1() else ('mega' if bool(MEGA_ENABLED and MEGA_EMAIL and MEGA_PASSWORD) else 'local')
        else:
            _STORAGE_PROFILE_RESTORE_BACKEND_V246 = 'mega' if bool(MEGA_ENABLED and MEGA_EMAIL and MEGA_PASSWORD) else ('telegram' if telegram_durable_available_v237_1() else 'local')
        return selected
    try:
        raw = str(os.getenv('RENDER_TELEGRAM_ONLY', '') or '').strip().casefold()
        if raw in {'1', 'true', 'yes', 'on', 'вкл'}:
            _STORAGE_PROFILE_BOOT_HINT_V237_1 = STORAGE_PROFILE_LOCAL_V237_1
            _STORAGE_PROFILE_BOOT_SOURCE_V238 = 'env:RENDER_TELEGRAM_ONLY:fallback'
            _STORAGE_PROFILE_RESTORE_BACKEND_V246 = _v246_best_render_restore_backend()
            return _STORAGE_PROFILE_BOOT_HINT_V237_1
    except Exception:
        pass
    if telegram_durable_available_v237_1():
        try:
            head, _meta = _tg_durable_load_remote_head_v234()
            controls = (head or {}).get('controls') or {}
            rawp = str(controls.get('storage_profile') or '').strip()
            if rawp:
                _STORAGE_PROFILE_BOOT_HINT_V237_1 = _storage_profile_normalize_v237_1(rawp)
                _STORAGE_PROFILE_BOOT_SOURCE_V238 = 'telegram:pinned_head_legacy_fallback'
                _STORAGE_PROFILE_RESTORE_BACKEND_V246 = 'telegram' if _STORAGE_PROFILE_BOOT_HINT_V237_1 == STORAGE_PROFILE_TELEGRAM_V237_1 else ('mega' if _STORAGE_PROFILE_BOOT_HINT_V237_1 == STORAGE_PROFILE_MEGA_V237_1 else _v246_best_render_restore_backend())
                return _STORAGE_PROFILE_BOOT_HINT_V237_1
            if bool(controls.get('mega_contour_enabled')):
                _STORAGE_PROFILE_BOOT_HINT_V237_1 = STORAGE_PROFILE_MEGA_V237_1
                _STORAGE_PROFILE_BOOT_SOURCE_V238 = 'telegram:pinned_head_legacy'
                _STORAGE_PROFILE_RESTORE_BACKEND_V246 = 'mega'
                return _STORAGE_PROFILE_BOOT_HINT_V237_1
        except Exception as exc:
            try:
                bot_journal('storage_profile_head_unavailable_v246', int(OWNER_ID or 0) or None, str(exc)[:240], 'WARN')
            except Exception:
                pass
    try:
        local_root = SQLITE.load_root() if 'SQLITE' in globals() else None
        found = _storage_profile_from_root_v237_1(local_root)
        if found:
            _STORAGE_PROFILE_BOOT_HINT_V237_1 = found
            _STORAGE_PROFILE_BOOT_SOURCE_V238 = 'sqlite:fallback'
            _STORAGE_PROFILE_RESTORE_BACKEND_V246 = _v246_best_render_restore_backend() if found == STORAGE_PROFILE_LOCAL_V237_1 else ('telegram' if found == STORAGE_PROFILE_TELEGRAM_V237_1 else 'mega')
            return found
    except Exception:
        pass
    _STORAGE_PROFILE_BOOT_HINT_V237_1 = storage_profile_v237_1()
    _STORAGE_PROFILE_BOOT_SOURCE_V238 = 'default'
    _STORAGE_PROFILE_RESTORE_BACKEND_V246 = _v246_best_render_restore_backend() if _STORAGE_PROFILE_BOOT_HINT_V237_1 == STORAGE_PROFILE_LOCAL_V237_1 else ('telegram' if _STORAGE_PROFILE_BOOT_HINT_V237_1 == STORAGE_PROFILE_TELEGRAM_V237_1 else 'mega')
    return _STORAGE_PROFILE_BOOT_HINT_V237_1
def storage_profile_apply_boot_hint_v237_1() -> str:
    """Commit only the selected running profile; v246 restore backend is one-shot."""
    root = _tg_v234_root_settings()
    chosen = _storage_profile_normalize_v237_1(_STORAGE_PROFILE_BOOT_HINT_V237_1 or storage_profile_v237_1())
    try:
        raw = str(os.getenv('RENDER_TELEGRAM_ONLY', '') or '').strip().casefold()
        if raw in {'1', 'true', 'yes', 'on', 'вкл'}:
            chosen = STORAGE_PROFILE_LOCAL_V237_1
    except Exception:
        pass
    changed = str(root.get(STORAGE_PROFILE_KEY_V237_1) or '') != chosen
    root[STORAGE_PROFILE_KEY_V237_1] = chosen
    root['render_telegram_only_v233'] = chosen == STORAGE_PROFILE_LOCAL_V237_1
    root['mega_contour_enabled_v234'] = chosen == STORAGE_PROFILE_MEGA_V237_1
    root['telegram_durable_enabled_v237_1'] = chosen == STORAGE_PROFILE_TELEGRAM_V237_1
    root['secret_storage_backend_v234'] = 'mega' if chosen == STORAGE_PROFILE_MEGA_V237_1 else 'telegram'
    if changed:
        try:
            save_data(data, root_only=True)
        except Exception:
            pass
    try:
        _v246_schedule_storage_control_persist(chosen, int(globals().get('_V241_STORAGE_EPOCH', 0) or 0), 'boot_apply')
    except Exception:
        pass
    return chosen
def _storage_cancel_telegram_jobs_v237_1() -> None:
    sched = globals().get('DELAYED_SCHEDULER')
    if sched is None:
        return
    for key in ('telegram-delta-batch-v234', 'telegram-full-quiet-v234', 'telegram-full-max-v234', 'telegram-task-startup-recovery-v234', 'constitution-ledger-tg-retry', 'telegram-full-v238'):
        try:
            sched.cancel(key)
        except Exception:
            pass

def _storage_cancel_mega_jobs_v237_1() -> None:
    sched = globals().get('DELAYED_SCHEDULER')
    if sched is None:
        return
    for key in ('mega-delta-batch-v90', 'mega-task-startup-recovery', 'mega-task-safe-failed-repair', 'mega-global-quiet-v90', 'mega-global-max-v90', 'mega-global-retry-v90', 'mega-global-user-idle-v190', 'mega-node-housekeeping-v211', 'mega-root-reseed-v190'):
        try:
            sched.cancel(key)
        except Exception:
            pass

def set_storage_profile_v237_1(profile: str) -> str:
    """Atomic radio switch; local state/UI first, remote control beacons in background."""
    target = _storage_profile_normalize_v237_1(profile)
    env_forced = str(os.getenv('RENDER_TELEGRAM_ONLY', '') or '').strip().casefold() in {'1', 'true', 'yes', 'on', 'вкл'}
    if env_forced and target != STORAGE_PROFILE_LOCAL_V237_1:
        return STORAGE_PROFILE_LOCAL_V237_1
    previous = storage_profile_v237_1()
    if target == STORAGE_PROFILE_TELEGRAM_V237_1 and (not telegram_durable_available_v237_1()):
        return previous
    if target == STORAGE_PROFILE_MEGA_V237_1 and (not bool(MEGA_ENABLED and MEGA_EMAIL and MEGA_PASSWORD)):
        return previous
    with _STORAGE_PROFILE_SWITCH_LOCK_V237_1:
        previous = storage_profile_v237_1()
        if previous == target:
            return target
        globals()['_V241_STORAGE_EPOCH'] = int(globals().get('_V241_STORAGE_EPOCH', 0) or 0) + 1
        mode_epoch = int(globals().get('_V241_STORAGE_EPOCH', 0) or 0)
        globals()['_V240_STORAGE_MODE_SWITCH_ACTIVE'] = True
        root = _tg_v234_root_settings()
        root[STORAGE_PROFILE_KEY_V237_1] = target
        root['render_telegram_only_v233'] = target == STORAGE_PROFILE_LOCAL_V237_1
        root['mega_contour_enabled_v234'] = target == STORAGE_PROFILE_MEGA_V237_1
        root['telegram_durable_enabled_v237_1'] = target == STORAGE_PROFILE_TELEGRAM_V237_1
        root['secret_storage_backend_v234'] = 'mega' if target == STORAGE_PROFILE_MEGA_V237_1 else 'telegram'
        try:
            save_data(data, root_only=True)
        except Exception:
            pass
        try:
            _v246_schedule_storage_control_persist(target, mode_epoch, 'mode_switch')
        except Exception:
            pass
        if target == STORAGE_PROFILE_LOCAL_V237_1:
            _storage_cancel_telegram_jobs_v237_1()
            _storage_cancel_mega_jobs_v237_1()
            try:
                fn = globals().get('_external_pause_schedulers_v233')
                if callable(fn):
                    fn()
            except Exception:
                pass
        else:
            try:
                fn = globals().get('_external_resume_services_v233')
                if previous == STORAGE_PROFILE_LOCAL_V237_1 and callable(fn):
                    fn()
            except Exception:
                pass
            if target == STORAGE_PROFILE_TELEGRAM_V237_1:
                _storage_cancel_mega_jobs_v237_1()
                try:
                    telegram_schedule_full_snapshot_v234('storage_profile_telegram_v246', delay=1.0)
                    if OWNER_ID:
                        telegram_schedule_delta_backup_v234(int(OWNER_ID), delay=0.35, reason='storage_profile_telegram_v246')
                except Exception:
                    pass
            else:
                _storage_cancel_telegram_jobs_v237_1()
                try:
                    if callable(_V234_MEGA_SCHEDULE_DELTA) and OWNER_ID:
                        _V234_MEGA_SCHEDULE_DELTA(int(OWNER_ID), delay=0.35, reason='storage_profile_mega_v246')
                    if secret_storage_backend_v234() == 'mega':
                        schedule_secret_storage_migration_v234('mega')
                except Exception:
                    pass
        globals()['_V240_STORAGE_MODE_SWITCH_ACTIVE'] = False
        try:
            bot_journal('storage_profile_v246', int(OWNER_ID or 0) or None, f"{previous}->{target}; epoch={mode_epoch}; mega_root={globals().get('MEGA_BACKUP_DIR', '')}")
        except Exception:
            pass
        return target
def set_telegram_durable_enabled_v237_1(enabled: bool) -> bool:
    if enabled:
        return set_storage_profile_v237_1(STORAGE_PROFILE_TELEGRAM_V237_1) == STORAGE_PROFILE_TELEGRAM_V237_1
    if storage_profile_v237_1() == STORAGE_PROFILE_TELEGRAM_V237_1:
        set_storage_profile_v237_1(STORAGE_PROFILE_LOCAL_V237_1)
    return False

def set_mega_contour_enabled_v234(enabled: bool) -> bool:
    if bool(enabled):
        return set_storage_profile_v237_1(STORAGE_PROFILE_MEGA_V237_1) == STORAGE_PROFILE_MEGA_V237_1
    if storage_profile_v237_1() == STORAGE_PROFILE_MEGA_V237_1:
        set_storage_profile_v237_1(STORAGE_PROFILE_TELEGRAM_V237_1)
    return False

def _run_secret_storage_migration_v234(target: str) -> bool:
    target = 'mega' if str(target or '').casefold() == 'mega' else 'telegram'
    root = _tg_v234_root_settings()
    state = {'target': target, 'state': 'running', 'started_at': now_local().isoformat(timespec='seconds'), 'error': ''}
    root['secret_storage_migration_v234'] = state
    try:
        save_data(data, root_only=True)
    except Exception:
        pass
    try:
        chats_fn = globals().get('secret_chats')
        chats = list(chats_fn() or []) if callable(chats_fn) else []
        if target == 'mega':
            if not _secret_mega_prerequisites_v234():
                state.update({'state': 'blocked', 'error': 'MEGA contour/master/config is not available'})
                root['secret_storage_migration_v234'] = state
                try:
                    save_data(data, root_only=True)
                except Exception:
                    pass
                return False
            uploader = globals().get('upload_chat_secrets_to_mega')
            if not callable(uploader):
                raise RuntimeError('MEGA secret uploader unavailable')
            failed = []
            for cid in chats:
                if not bool(uploader(int(cid))):
                    failed.append(int(cid))
            if failed:
                raise RuntimeError('MEGA secret migration failed for chats: ' + ','.join(map(str, failed[:20])))
        else:
            global _delta_generation
            with _delta_state_lock:
                for cid in chats:
                    _delta_generation += 1
                    _delta_pending_chats.add(int(cid))
                    _delta_chat_generation[int(cid)] = _delta_generation
            if chats and (not durable_run_pending_delta_now_v234()):
                raise RuntimeError('Telegram secret migration delta failed')
            telegram_schedule_full_snapshot_v234('secret_backend_migration', delay=30.0)
        state.update({'state': 'done', 'completed_at': now_local().isoformat(timespec='seconds'), 'chats': len(chats), 'error': ''})
        root['secret_storage_migration_v234'] = state
        try:
            save_data(data, root_only=True)
        except Exception:
            pass
        try:
            telegram_durable_persist_controls_v234()
        except Exception:
            pass
        try:
            bot_journal('secret_storage_migration_done_v234', int(OWNER_ID or 0) or None, f'target={target}; chats={len(chats)}')
        except Exception:
            pass
        return True
    except Exception as exc:
        state.update({'state': 'failed', 'completed_at': now_local().isoformat(timespec='seconds'), 'error': str(exc)[:500]})
        root['secret_storage_migration_v234'] = state
        try:
            save_data(data, root_only=True)
        except Exception:
            pass
        try:
            bot_journal('secret_storage_migration_failed_v234', int(OWNER_ID or 0) or None, f'target={target}; {exc}', 'ERROR')
        except Exception:
            pass
        return False

def schedule_secret_storage_migration_v234(target: str) -> bool:
    target = 'mega' if str(target or '').casefold() == 'mega' else 'telegram'
    state = _secret_storage_migration_state_v234()
    if str(state.get('target') or '') == target and str(state.get('state') or '') in {'running', 'done'}:
        return True
    row = {'target': target, 'state': 'pending', 'requested_at': now_local().isoformat(timespec='seconds'), 'error': ''}
    _tg_v234_root_settings()['secret_storage_migration_v234'] = row
    try:
        save_data(data, root_only=True)
    except Exception:
        pass
    pool = globals().get('RECOVERY_TASK_POOL') or globals().get('BACKUP_TASK_POOL')
    try:
        if pool is not None and pool.submit_unique(f'secret-storage-migrate:{target}', _run_secret_storage_migration_v234, target):
            return True
    except Exception:
        pass
    try:
        DELAYED_SCHEDULER.schedule(f'secret-storage-migrate:{target}', 0.2, _run_secret_storage_migration_v234, target)
        return True
    except Exception:
        return False

def set_secret_storage_backend_v234(backend: str) -> str:
    backend = 'mega' if str(backend or '').strip().casefold() == 'mega' else 'telegram'
    _tg_v234_root_settings()['secret_storage_backend_v234'] = backend
    state = _secret_storage_migration_state_v234()
    if str(state.get('target') or '') != backend:
        _tg_v234_root_settings()['secret_storage_migration_v234'] = {'target': backend, 'state': 'pending', 'requested_at': now_local().isoformat(timespec='seconds'), 'error': ''}
    try:
        save_data(data, root_only=True)
    except Exception:
        pass
    try:
        telegram_durable_persist_controls_v234()
    except Exception:
        pass
    if backend == 'telegram' or _secret_mega_prerequisites_v234():
        schedule_secret_storage_migration_v234(backend)
    else:
        row = _secret_storage_migration_state_v234()
        row.update({'target': 'mega', 'state': 'blocked', 'error': 'MEGA is blocked or not configured'})
        _tg_v234_root_settings()['secret_storage_migration_v234'] = row
        try:
            save_data(data, root_only=True)
        except Exception:
            pass
    try:
        bot_journal('secret_storage_backend_v234', int(OWNER_ID or 0) or None, f'requested={backend}; effective={secret_storage_effective_backend_v234()}')
    except Exception:
        pass
    return backend

def telegram_durable_status_v234() -> dict:
    head = telegram_durable_bootstrap_v234(False) if telegram_durable_primary_v234() else _tg_durable_default_head_v234()
    tasks = head.get('tasks') or {}
    states = defaultdict(int)
    for row in tasks.values():
        states[str((row or {}).get('state') or 'unknown')] += 1
    snap = head.get('snapshot') or {}
    return {'configured': telegram_durable_available_v237_1(), 'active': telegram_durable_primary_v234(), 'storage_profile': storage_profile_v237_1(), 'head_message_id': int((_TG_DURABLE_HEAD_META_V234 or {}).get('message_id') or 0), 'generation': int(head.get('generation') or 0), 'deltas': len(head.get('deltas') or []), 'snapshot_parts': len(snap.get('parts') or []) if isinstance(snap, dict) else 0, 'snapshot_at': str(snap.get('created_at') or '') if isinstance(snap, dict) else '', 'pending': int(states.get('pending', 0)), 'running': int(states.get('running', 0)), 'failed': int(states.get('failed', 0)), 'done': int(states.get('done', 0)), 'last_error': _TG_DURABLE_LAST_ERROR_V234, 'stats': dict(_TG_DURABLE_STATS_V234)}

def telegram_durable_status_text_v234() -> str:
    st = telegram_durable_status_v234()
    return f"📡 TELEGRAM DURABLE STORAGE · stable slots\n\nКанал: {('✅ доступен' if st['configured'] else '⛔ не настроен')}\nHEAD: {('✅ #' + str(st['head_message_id']) if st['head_message_id'] else '⬜ ещё не создан')} · generation {st['generation']}\nSQLite snapshot: {st['snapshot_parts']} частей · {st['snapshot_at'] or '—'}\nDelta после snapshot: {st['deltas']}\nDurable tasks: pending {st['pending']} · running {st['running']} · failed {st['failed']}\nПоследняя ошибка: {st['last_error'] or 'нет'}\n\nКритические update сначала получают маленький внешний Telegram-свидетель. Изменения состояния пишутся delta, а тяжёлый SQLite snapshot выполняется отдельно после периода тишины."[:3900]

def _canon_tg_durable_send_blob_v234__001(raw: bytes, filename: str, caption: str):
    buf = io.BytesIO(raw)
    buf.name = str(filename)
    sent = bot.send_document(int(BACKUP_CHAT_ID), buf, caption=str(caption)[:1024])
    doc = getattr(sent, 'document', None)
    file_id = str(getattr(doc, 'file_id', '') or '')
    if not file_id:
        raise RuntimeError('Telegram durable blob returned no file_id')
    return {'message_id': int(getattr(sent, 'message_id', 0) or 0), 'file_id': file_id, 'file_name': str(getattr(doc, 'file_name', '') or filename), 'size': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}

def telegram_constitution_ledger_upload_v234(token: str, event: dict, name: str, attempt: int=0) -> bool:
    """Persist one immutable Data Constitution ledger event in Telegram.

    The event itself is an append-only channel document; HEAD only keeps bounded refs/highwater.
    Retries reuse an already-uploaded local ref where possible so a HEAD-edit failure does not
    force another media upload.
    """
    token = str(token or name or '')
    if not token or not telegram_durable_configured_v234():
        return False
    state = {}
    try:
        with _CONSTITUTION_LEDGER_ASYNC_LOCK:
            state = dict(_CONSTITUTION_LEDGER_ASYNC_STATE.get(token) or {})
            if state.get('state') == 'done':
                return True
        ref = state.get('telegram_ref') if isinstance(state.get('telegram_ref'), dict) else None
        if not ref:
            raw_json = json.dumps(event, ensure_ascii=False, separators=(',', ':'), default=str).encode('utf-8')
            packed = gzip.compress(raw_json, compresslevel=6)
            fname = str(name or token)
            if not fname.endswith('.gz'):
                fname += '.gz'
            ref = _tg_durable_send_blob_v234(packed, fname, f"🏛 Data Constitution ledger · seq {int((event or {}).get('seq') or 0)}")
            ref.update({'token': token, 'seq': int((event or {}).get('seq') or 0), 'event_hash': str((event or {}).get('event_hash') or ''), 'integrity_hash': str((event or {}).get('integrity_hash') or ''), 'created_at': str((event or {}).get('at') or '')})
            with _CONSTITUTION_LEDGER_ASYNC_LOCK:
                cur = dict(_CONSTITUTION_LEDGER_ASYNC_STATE.get(token) or {})
                cur.update({'state': 'pending', 'telegram_ref': dict(ref), 'attempt': int(attempt)})
                _CONSTITUTION_LEDGER_ASYNC_STATE[token] = cur
        with _TG_DURABLE_LOCK_V234:
            head = telegram_durable_bootstrap_v234(False)
            refs = [dict(x or {}) for x in head.get('constitution_ledger') or [] if isinstance(x, dict)]
            if not any((str(x.get('token') or '') == token for x in refs)):
                refs.append(dict(ref))
            head['constitution_ledger'] = refs[-500:]
            head['constitution_ledger_highwater'] = {'seq': int((event or {}).get('seq') or 0), 'hash': str((event or {}).get('event_hash') or ''), 'integrity_hash': str((event or {}).get('integrity_hash') or ''), 'at': str((event or {}).get('at') or ''), 'backend': 'telegram', 'message_id': int((ref or {}).get('message_id') or 0)}
            if not _tg_durable_persist_head_v234('constitution_ledger'):
                raise RuntimeError('Telegram HEAD update failed for constitution ledger')
        high = dict(head.get('constitution_ledger_highwater') or {})
        try:
            SQLITE.set_meta('data_constitution', 'ledger_highwater', high)
        except Exception:
            pass
        try:
            SQLITE.set_meta('data_constitution_pending', str(name or token), {'done': True, 'at': (event or {}).get('at'), 'backend': 'telegram', 'message_id': int((ref or {}).get('message_id') or 0)})
        except Exception:
            pass
        try:
            _root_settings()['data_constitution_ledger_highwater'] = copy.deepcopy(high)
            _root_save_coalesced('constitution_ledger_highwater_v234', 0.5)
        except Exception:
            pass
        with _CONSTITUTION_LEDGER_ASYNC_LOCK:
            _CONSTITUTION_LEDGER_ASYNC_STATE[token] = {'state': 'done', 'at': time.monotonic(), 'backend': 'telegram', 'telegram_ref': dict(ref)}
        try:
            bot_journal('constitution_ledger_async_done_v234', int((event or {}).get('chat_id') or 0), f"seq={(event or {}).get('seq')}; backend=telegram")
        except Exception:
            pass
        return True
    except Exception as exc:
        next_attempt = int(attempt or 0) + 1
        if next_attempt <= 5:
            with _CONSTITUTION_LEDGER_ASYNC_LOCK:
                cur = dict(_CONSTITUTION_LEDGER_ASYNC_STATE.get(token) or {})
                cur.update({'state': 'pending', 'error': str(exc)[:300], 'attempt': next_attempt, 'at': time.monotonic()})
                _CONSTITUTION_LEDGER_ASYNC_STATE[token] = cur
            try:
                DELAYED_SCHEDULER.schedule(f'constitution-ledger-tg-retry:{token}', min(30.0, 2.0 * next_attempt), telegram_constitution_ledger_upload_v234, token, event, name, next_attempt)
                return True
            except Exception:
                pass
        with _CONSTITUTION_LEDGER_ASYNC_LOCK:
            _CONSTITUTION_LEDGER_ASYNC_STATE[token] = {'state': 'failed', 'error': str(exc)[:300], 'attempt': next_attempt, 'at': time.monotonic(), 'backend': 'telegram', 'telegram_ref': state.get('telegram_ref')}
        try:
            constitution_set_quarantine(f"immutable finance ledger Telegram write failed seq={(event or {}).get('seq')}: {exc}")
        except Exception:
            pass
        try:
            log_error(f'[DATA CONSTITUTION TG LEDGER] {exc}')
        except Exception:
            pass
        return False

def telegram_constitution_restore_checkpoint_v234(checkpoint: dict) -> bool:
    """Store an owner-initiated restore checkpoint before publishing the replacement snapshot."""
    if not telegram_durable_configured_v234():
        return False
    try:
        raw = gzip.compress(json.dumps(checkpoint, ensure_ascii=False, separators=(',', ':'), default=str).encode('utf-8'), compresslevel=6)
        stamp = re.sub('[^0-9]', '', str((checkpoint or {}).get('at') or now_local().isoformat()))[:20]
        name = f"restore_checkpoint_{stamp}_{str((checkpoint or {}).get('event_hash') or '')[:16]}.json.gz"
        ref = _tg_durable_send_blob_v234(raw, name, '🏛 Data Constitution restore checkpoint v234')
        ref.update({'event_hash': str((checkpoint or {}).get('event_hash') or ''), 'created_at': str((checkpoint or {}).get('at') or '')})
        with _TG_DURABLE_LOCK_V234:
            head = telegram_durable_bootstrap_v234(False)
            rows = [dict(x or {}) for x in head.get('constitution_checkpoints') or [] if isinstance(x, dict)]
            rows.append(ref)
            head['constitution_checkpoints'] = rows[-50:]
            return bool(_tg_durable_persist_head_v234('constitution_restore_checkpoint'))
    except Exception as exc:
        try:
            log_error(f'TG constitution restore checkpoint: {exc}')
        except Exception:
            pass
        return False

def _tg_durable_upload_delta_payload_v234(payload: dict) -> tuple[bool, dict | None]:
    try:
        raw_json = json.dumps(payload, ensure_ascii=False, separators=(',', ':'), default=str).encode('utf-8')
        raw = gzip.compress(raw_json, compresslevel=6)
        name = f"delta_{payload.get('delta_id')}.json.gz"
        row = _tg_durable_send_blob_v234(raw, name, f"🧩 TG durable delta · {payload.get('event_count', 0)} events")
        row.update({'created_at': str(payload.get('created_at') or ''), 'delta_id': str(payload.get('delta_id') or ''), 'event_count': int(payload.get('event_count') or 0)})
        with _TG_DURABLE_LOCK_V234:
            head = telegram_durable_bootstrap_v234(False)
            deltas = list(head.get('deltas') or [])
            deltas.append(row)
            if len(deltas) > TG_DURABLE_DELTA_KEEP_V234:
                deltas = deltas[-TG_DURABLE_DELTA_KEEP_V234:]
            head['deltas'] = deltas
            if not _tg_durable_persist_head_v234('delta'):
                return (False, None)
        _TG_DURABLE_STATS_V234['delta_uploads'] += 1
        _TG_DURABLE_STATS_V234['last_delta_at'] = str(payload.get('created_at') or '')
        return (True, row)
    except Exception as exc:
        _TG_DURABLE_STATS_V234['delta_errors'] += 1
        try:
            log_error(f'TG durable delta upload: {exc}')
        except Exception:
            pass
        return (False, None)

def _tg_durable_run_delta_batch_v234() -> bool:
    global _delta_last_success_at, _delta_last_file, _delta_last_event_count, _delta_last_error
    with _delta_state_lock:
        chat_ids = sorted(_delta_pending_chats)
        generation_map = {cid: int(_delta_chat_generation.get(cid, 0)) for cid in chat_ids}
    if not chat_ids:
        return True
    payload, baseline = _build_delta_payload(chat_ids, generation_map)
    if payload is not None:
        ok, row = _tg_durable_upload_delta_payload_v234(payload)
        if not ok:
            _delta_last_error = 'telegram durable delta upload failed'
            return False
        _delta_last_success_at = str(payload.get('created_at') or '')
        _delta_last_file = f"telegram:{(row or {}).get('message_id', 0)}"
        _delta_last_event_count = int(payload.get('event_count') or 0)
        _delta_last_error = ''
    _commit_delta_baseline(baseline)
    with _delta_state_lock:
        for cid, gen in generation_map.items():
            if int(_delta_chat_generation.get(cid, 0)) == int(gen):
                _delta_pending_chats.discard(cid)
    with timer_lock:
        for cid in generation_map:
            _quick_backup_timers.pop(int(cid), None)
            _quick_backup_dirty_chats.discard(int(cid))
    telegram_schedule_full_snapshot_v234('delta')
    return True

def _canon_telegram_schedule_delta_backup_v234__001(chat_id: int | None, delay: float | None=None, reason: str='change') -> bool:
    global _delta_generation, _delta_batch_timer
    if RESTORE_GUARD_ACTIVE or not telegram_durable_configured_v234():
        return False
    with _delta_state_lock:
        _delta_generation += 1
        if chat_id is not None:
            cid = int(chat_id)
            _delta_pending_chats.add(cid)
            _delta_chat_generation[cid] = _delta_generation
        elif not _delta_pending_chats:
            return False
    delay = max(0.5, float(delay if delay is not None else 2.5))

    def _fire():

        def _job():
            if not _tg_durable_run_delta_batch_v234():
                telegram_schedule_delta_backup_v234(None, delay=max(3.0, float(globals().get('BACKUP_BUSY_RETRY_SECONDS', 5.0) or 5.0)), reason='retry')
        pool = globals().get('DELTA_TASK_POOL')
        if pool is None or not pool.submit('telegram-delta-v234', _job):
            _job()
    DELAYED_SCHEDULER.cancel('telegram-delta-batch-v234')
    _delta_batch_timer = DELAYED_SCHEDULER.schedule('telegram-delta-batch-v234', delay, _fire)
    return True

def telegram_persist_critical_delta_now_v234(chat_id: int) -> bool:
    global _delta_generation
    if RESTORE_GUARD_ACTIVE or not telegram_durable_configured_v234():
        return False
    cid = int(chat_id)
    with CRITICAL_DELTA_LOCK:
        with _delta_state_lock:
            _delta_generation += 1
            _delta_pending_chats.add(cid)
            _delta_chat_generation[cid] = _delta_generation
        try:
            DELAYED_SCHEDULER.cancel('telegram-delta-batch-v234')
        except Exception:
            pass
        return bool(_tg_durable_run_delta_batch_v234())

def _canon_schedule_delta_backup__002(chat_id: int | None, delay: float | None=None, reason: str='change'):
    """v234 routing: Telegram primary delta; optional MEGA gets a background mirror only."""
    tg_ok = False
    if telegram_durable_primary_v234():
        tg_ok = bool(telegram_schedule_delta_backup_v234(chat_id, delay=delay, reason=reason))
        try:
            if mega_contour_enabled_v234() and callable(_V234_MEGA_SCHEDULE_DELTA) and (not callable(globals().get('external_access_allowed_v233')) or external_access_allowed_v233('mega')):
                _V234_MEGA_SCHEDULE_DELTA(chat_id, delay=max(8.0, float(delay or 8.0)), reason='mirror_v234:' + str(reason))
        except Exception:
            pass
        return tg_ok
    return _V234_MEGA_SCHEDULE_DELTA(chat_id, delay=delay, reason=reason) if callable(_V234_MEGA_SCHEDULE_DELTA) else False

def _canon_persist_critical_delta_now__002(chat_id: int) -> bool:
    if telegram_durable_primary_v234():
        return telegram_persist_critical_delta_now_v234(int(chat_id))
    return bool(_V234_MEGA_CRITICAL_DELTA(int(chat_id))) if callable(_V234_MEGA_CRITICAL_DELTA) else False

def _tg_durable_gzip_sqlite_v234() -> tuple[str, bytes]:
    os.makedirs(MEGA_LOCAL_TMP_DIR, exist_ok=True)
    stamp = now_local().strftime('%Y%m%d_%H%M%S_%f')
    db_tmp = os.path.join(MEGA_LOCAL_TMP_DIR, f'tg_v234_{stamp}.sqlite3')
    SQLITE.backup_to(db_tmp)
    try:
        with open(db_tmp, 'rb') as fh:
            raw = fh.read()
        return (stamp, gzip.compress(raw, compresslevel=6))
    finally:
        try:
            os.remove(db_tmp)
        except Exception:
            pass

def _canon_telegram_upload_sqlite_snapshot_v234__001(force: bool=False) -> bool:
    global _TG_DURABLE_SNAPSHOT_LAST_SUCCESS_MONO_V234, _TG_DURABLE_SNAPSHOT_PENDING_V234
    if RESTORE_GUARD_ACTIVE or not telegram_durable_primary_v234():
        try:
            bot_journal('tg_snapshot_skipped_profile_v238', int(OWNER_ID or 0) or None, f'profile={storage_profile_v237_1()}', 'INFO')
        except Exception:
            pass
        return False
    if not _TG_DURABLE_SNAPSHOT_EXEC_LOCK_V238.acquire(blocking=False):
        try:
            bot_journal('tg_snapshot_coalesced_v238', int(OWNER_ID or 0) or None, 'snapshot already in flight', 'INFO')
        except Exception:
            pass
        return True
    try:
        since = max(0.0, time.monotonic() - _TG_DURABLE_SNAPSHOT_LAST_SUCCESS_MONO_V234)
        if int(_TG_DURABLE_STATS_V234.get('snapshot_uploads') or 0) > 0 and (not _TG_DURABLE_SNAPSHOT_PENDING_V234) and (since < TG_DURABLE_SNAPSHOT_MIN_REWRITE_SECONDS_V238):
            return True
        stamp, packed = _tg_durable_gzip_sqlite_v234()
        parts = []
        total = max(1, (len(packed) + TG_DURABLE_CHUNK_BYTES_V234 - 1) // TG_DURABLE_CHUNK_BYTES_V234)
        for idx in range(total):
            if not telegram_durable_primary_v234():
                try:
                    bot_journal('tg_snapshot_aborted_profile_v238', int(OWNER_ID or 0) or None, f'part={idx + 1}/{total}; profile={storage_profile_v237_1()}', 'INFO')
                except Exception:
                    pass
                return False
            chunk = packed[idx * TG_DURABLE_CHUNK_BYTES_V234:(idx + 1) * TG_DURABLE_CHUNK_BYTES_V234]
            name = f'bot_state_{stamp}.sqlite3.gz.part{idx + 1:03d}of{total:03d}'
            row = _tg_durable_send_blob_v234(chunk, name, f'🗄 SQLite snapshot · {idx + 1}/{total}')
            row['index'] = idx + 1
            row['total'] = total
            parts.append(row)
        snapshot = {'created_at': now_local().isoformat(timespec='microseconds'), 'stamp': stamp, 'compression': 'gzip', 'sha256': hashlib.sha256(packed).hexdigest(), 'packed_size': len(packed), 'parts': parts}
        with _TG_DURABLE_LOCK_V234:
            if not telegram_durable_primary_v234():
                return False
            head = telegram_durable_bootstrap_v234(False)
            old_deltas = list(head.get('deltas') or [])
            head['snapshot'] = snapshot
            head['deltas'] = []
            if not _tg_durable_persist_head_v234('sqlite_snapshot'):
                head['deltas'] = old_deltas
                return False
        try:
            prune = globals().get('telegram_stable_prune_sqlite_parts_v238')
            if callable(prune):
                prune(total)
        except Exception as exc:
            try:
                bot_journal('tg_snapshot_part_prune_warn_v238', int(OWNER_ID or 0) or None, str(exc)[:240], 'WARN')
            except Exception:
                pass
        _TG_DURABLE_STATS_V234['snapshot_uploads'] += 1
        _TG_DURABLE_STATS_V234['last_snapshot_at'] = str(snapshot.get('created_at') or '')
        _TG_DURABLE_SNAPSHOT_LAST_SUCCESS_MONO_V234 = time.monotonic()
        _TG_DURABLE_SNAPSHOT_PENDING_V234 = False
        initialize_delta_baseline(data)
        return True
    except Exception as exc:
        _TG_DURABLE_STATS_V234['snapshot_errors'] += 1
        if telegram_durable_primary_v234():
            try:
                log_error(f'TG SQLite snapshot: {exc}')
            except Exception:
                pass
        else:
            try:
                bot_journal('tg_snapshot_stale_job_v238', int(OWNER_ID or 0) or None, str(exc)[:240], 'INFO')
            except Exception:
                pass
        return False
    finally:
        _TG_DURABLE_SNAPSHOT_EXEC_LOCK_V238.release()

def _canon_telegram_schedule_full_snapshot_v234__001(reason: str='change', delay: float | None=None) -> bool:
    global _TG_DURABLE_SNAPSHOT_LAST_CHANGE_MONO_V234, _TG_DURABLE_SNAPSHOT_PENDING_V234
    if RESTORE_GUARD_ACTIVE or not telegram_durable_primary_v234():
        return False
    _TG_DURABLE_SNAPSHOT_PENDING_V234 = True
    _TG_DURABLE_SNAPSHOT_LAST_CHANGE_MONO_V234 = time.monotonic()
    quiet = TG_DURABLE_FULL_QUIET_SECONDS_V234 if delay is None else max(5.0, float(delay))
    elapsed = max(0.0, time.monotonic() - _TG_DURABLE_SNAPSHOT_LAST_SUCCESS_MONO_V234)
    max_wait = max(5.0, TG_DURABLE_FULL_MAX_SECONDS_V234 - elapsed)

    def _quiet_fire():
        if not _TG_DURABLE_SNAPSHOT_PENDING_V234:
            return
        quiet_for = time.monotonic() - _TG_DURABLE_SNAPSHOT_LAST_CHANGE_MONO_V234
        if quiet_for + 0.2 < quiet:
            DELAYED_SCHEDULER.schedule('telegram-full-quiet-v234', quiet - quiet_for, _quiet_fire)
            return
        pool = globals().get('BACKUP_TASK_POOL')
        submit = getattr(pool, 'submit_unique', None) if pool is not None else None
        ok = bool(submit('telegram-full-v238', telegram_upload_sqlite_snapshot_v234, False)) if callable(submit) else bool(pool.submit('telegram-full-v238', telegram_upload_sqlite_snapshot_v234, False)) if pool is not None else False
        if not ok and pool is None:
            telegram_upload_sqlite_snapshot_v234(False)

    def _max_fire():
        if not _TG_DURABLE_SNAPSHOT_PENDING_V234:
            return
        pool = globals().get('BACKUP_TASK_POOL')
        submit = getattr(pool, 'submit_unique', None) if pool is not None else None
        ok = bool(submit('telegram-full-v238', telegram_upload_sqlite_snapshot_v234, True)) if callable(submit) else bool(pool.submit('telegram-full-v238', telegram_upload_sqlite_snapshot_v234, True)) if pool is not None else False
        if not ok and pool is None:
            telegram_upload_sqlite_snapshot_v234(True)
    DELAYED_SCHEDULER.cancel('telegram-full-quiet-v234')
    DELAYED_SCHEDULER.schedule('telegram-full-quiet-v234', quiet, _quiet_fire)
    if DELAYED_SCHEDULER.deadline('telegram-full-max-v234') is None:
        DELAYED_SCHEDULER.schedule('telegram-full-max-v234', max_wait, _max_fire)
    return True

def _canon_schedule_config_backup_for_chats__002(*chat_ids, delay: float=3.0):
    """Config/state changes always schedule Telegram durability; MEGA is an optional mirror."""
    ok = False
    try:
        if telegram_durable_primary_v234():
            for cid in {int(x) for x in chat_ids if x is not None}:
                telegram_schedule_delta_backup_v234(cid, delay=max(1.0, min(float(delay or 1.0), 5.0)), reason='config')
            telegram_schedule_full_snapshot_v234('config')
            ok = True
    except Exception as exc:
        try:
            log_error(f'TG config backup schedule: {exc}')
        except Exception:
            pass
    try:
        if mega_contour_enabled_v234() and callable(_V234_MEGA_CONFIG_BACKUP) and (not callable(globals().get('external_access_allowed_v233')) or external_access_allowed_v233('mega')):
            _V234_MEGA_CONFIG_BACKUP(*chat_ids, delay=max(8.0, float(delay or 8.0)))
    except Exception:
        pass
    return ok

def _tg_durable_download_ref_v234(ref: dict) -> bytes:
    raw = _tg_durable_download_file_id_v234(str((ref or {}).get('file_id') or ''))
    expected = str((ref or {}).get('sha256') or '')
    if expected and hashlib.sha256(raw).hexdigest() != expected:
        raise RuntimeError(f"Telegram durable SHA mismatch for {(ref or {}).get('file_name')}")
    return raw

def _canon_telegram_restore_sqlite_snapshot_v234__001() -> tuple[bool, str]:
    """Restore the latest discoverable SQLite generation from the pinned Telegram HEAD."""
    if not telegram_durable_configured_v234():
        return (False, 'Telegram durable channel is not configured')
    head = telegram_durable_bootstrap_v234(True)
    snap = head.get('snapshot') if isinstance(head, dict) else None
    if not isinstance(snap, dict) or not (snap.get('parts') or []):
        return (False, 'Telegram HEAD found; no SQLite snapshot yet')
    try:
        chunks = []
        for ref in sorted(list(snap.get('parts') or []), key=lambda r: int((r or {}).get('index') or 0)):
            chunks.append(_tg_durable_download_ref_v234(ref))
        packed = b''.join(chunks)
        if str(snap.get('sha256') or '') and hashlib.sha256(packed).hexdigest() != str(snap.get('sha256')):
            raise RuntimeError('Telegram SQLite packed SHA mismatch')
        raw = gzip.decompress(packed)
        os.makedirs(MEGA_LOCAL_TMP_DIR, exist_ok=True)
        tmp = os.path.join(MEGA_LOCAL_TMP_DIR, f'restore_tg_v234_{time.time_ns()}.sqlite3')
        with open(tmp, 'wb') as fh:
            fh.write(raw)
        try:
            check_conn = sqlite3.connect(tmp)
            try:
                row = check_conn.execute('PRAGMA integrity_check').fetchone()
                if not row or str(row[0]).lower() != 'ok':
                    raise RuntimeError(f'SQLite integrity_check={row}')
            finally:
                check_conn.close()
            SQLITE.replace_database(tmp)
        finally:
            try:
                os.remove(tmp)
            except Exception:
                pass
        _TG_DURABLE_STATS_V234['restore_snapshots'] += 1
        _TG_DURABLE_STATS_V234['last_restore_at'] = now_local().isoformat(timespec='seconds')
        return (True, f"Telegram SQLite snapshot {snap.get('created_at') or snap.get('stamp')} · {len(chunks)} parts")
    except Exception as exc:
        try:
            log_error(f'TG SQLite restore: {exc}')
        except Exception:
            pass
        return (False, f'Telegram SQLite restore failed: {exc}')

def _canon_telegram_apply_remote_deltas_v234__001() -> int:
    """Apply HEAD-listed deltas idempotently after local/snapshot SQLite has been loaded."""
    global data
    if not telegram_durable_configured_v234():
        return 0
    head = telegram_durable_bootstrap_v234(True)
    rows = list((head or {}).get('deltas') or [])
    if not rows:
        initialize_delta_baseline(data)
        return 0
    applied = 0
    state = data
    for ref in rows:
        try:
            raw = _tg_durable_download_ref_v234(ref)
            doc = json.loads(gzip.decompress(raw).decode('utf-8'))
            if str(doc.get('kind') or '') != 'telegram_finance_bot_delta':
                continue
            state = _apply_delta_payload_to_state(state, doc)
            applied += 1
        except Exception as exc:
            log_error(f"TG delta restore skip {str((ref or {}).get('delta_id') or '')}: {exc}")
            raise
    data = state
    try:
        _lowram_prepare_loaded_data(data, migrate_existing=True)
        _lowram_flush_all_hot(evict=True)
    except Exception:
        try:
            save_data(data)
        except Exception:
            pass
    initialize_delta_baseline(data)
    _TG_DURABLE_STATS_V234['restore_deltas'] += applied
    _TG_DURABLE_STATS_V234['last_restore_at'] = now_local().isoformat(timespec='seconds')
    return applied

def _canon_lowram_apply_deltas_after_db_snapshot__002() -> int:
    if telegram_durable_primary_v234():
        return telegram_apply_remote_deltas_v234()
    return int(_V234_MEGA_LOWRAM_APPLY_DELTAS() or 0) if callable(_V234_MEGA_LOWRAM_APPLY_DELTAS) else 0

def durable_run_pending_delta_now_v234() -> bool:
    """Flush the currently pending combined durable delta through the active v234 backend.

    Compatibility entrypoint for later modules that used to call the private
    MEGA-only ``_run_delta_batch`` directly. Telegram-primary mode must not
    fall through to that MEGA path while the MEGA contour is disabled.
    """
    if telegram_durable_primary_v234():
        return bool(_tg_durable_run_delta_batch_v234())
    try:
        return bool(_V234_MEGA_RUN_DELTA_BATCH()) if callable(_V234_MEGA_RUN_DELTA_BATCH) else False
    except Exception as exc:
        log_error(f'[V234 DURABLE] legacy MEGA combined delta failed: {exc}')
        return False

def _canon_mega_tasks_active__002() -> bool:
    if telegram_durable_primary_v234():
        return not RESTORE_GUARD_ACTIVE
    return bool(_V234_MEGA_TASKS_ACTIVE()) if callable(_V234_MEGA_TASKS_ACTIVE) else False

def _tg_task_row_v234(update_id) -> dict | None:
    key = _mega_task_id(update_id)
    head = telegram_durable_bootstrap_v234(False)
    row = (head.get('tasks') or {}).get(key)
    return row if isinstance(row, dict) else None

def _canon_mega_task_known_state__002(update_id) -> str:
    if telegram_durable_primary_v234():
        row = _tg_task_row_v234(update_id)
        return str((row or {}).get('state') or '')
    return str(_V234_MEGA_TASK_KNOWN_STATE(update_id) or '') if callable(_V234_MEGA_TASK_KNOWN_STATE) else ''

def _tg_task_prune_done_v234(tasks: dict) -> dict:
    done = [(k, v) for k, v in tasks.items() if str((v or {}).get('state') or '') == 'done']
    if len(done) <= TG_DURABLE_TASK_DONE_KEEP_V234:
        return tasks
    done.sort(key=lambda kv: str((kv[1] or {}).get('updated_at') or (kv[1] or {}).get('created_at') or ''))
    for key, _ in done[:-TG_DURABLE_TASK_DONE_KEEP_V234]:
        tasks.pop(key, None)
    return tasks

def _canon_mega_task_upload_new_pending__002(update_id, task_payload: dict) -> bool:
    if not telegram_durable_primary_v234():
        return bool(_V234_MEGA_TASK_UPLOAD_PENDING(update_id, task_payload)) if callable(_V234_MEGA_TASK_UPLOAD_PENDING) else False
    key = _mega_task_id(update_id)
    with _TG_DURABLE_LOCK_V234:
        head = telegram_durable_bootstrap_v234(False)
        tasks = head.setdefault('tasks', {})
        existing = tasks.get(key)
        if isinstance(existing, dict) and str(existing.get('state') or '') in {'pending', 'running', 'done', 'failed'}:
            return True
        row = _delta_json_clone(task_payload or {})
        row['state'] = 'pending'
        row['created_at'] = row.get('created_at') or now_local().isoformat(timespec='microseconds')
        row['updated_at'] = now_local().isoformat(timespec='microseconds')
        row['backend'] = 'telegram'
        tasks[key] = row
        _tg_task_prune_done_v234(tasks)
        if not _tg_durable_persist_head_v234(f'task_pending:{key}'):
            tasks.pop(key, None)
            return False
    with _MEGA_TASK_LOCK:
        _mega_task_registry[key] = {'state': 'pending', 'path': f'telegram-head:{key}', 'loaded_at': now_local().isoformat(timespec='seconds')}
        _mega_task_counters['persisted'] += 1
    _TG_DURABLE_STATS_V234['task_writes'] += 1
    return True

def _canon_mega_task_begin__002(update_id, allow_existing_running: bool=False) -> bool:
    if not telegram_durable_primary_v234():
        return bool(_V234_MEGA_TASK_BEGIN(update_id, allow_existing_running=allow_existing_running)) if callable(_V234_MEGA_TASK_BEGIN) else False
    key = _mega_task_id(update_id)
    with _TG_DURABLE_LOCK_V234:
        head = telegram_durable_bootstrap_v234(False)
        tasks = head.setdefault('tasks', {})
        row = tasks.get(key)
        if not isinstance(row, dict):
            return False
        state = str(row.get('state') or '')
        if state == 'running' and allow_existing_running:
            return True
        if state != 'pending':
            return False
        row['state'] = 'running'
        row['started_at'] = now_local().isoformat(timespec='microseconds')
        row['updated_at'] = row['started_at']
        if not _tg_durable_persist_head_v234(f'task_running:{key}'):
            row['state'] = 'pending'
            return False
    with _MEGA_TASK_LOCK:
        _mega_task_registry[key] = {'state': 'running', 'path': f'telegram-head:{key}', 'loaded_at': now_local().isoformat(timespec='seconds')}
        _mega_task_processing.add(key)
    return True

def _canon_mega_task_finish__001(update_id, success: bool, error: str='') -> bool:
    if not telegram_durable_primary_v234():
        return bool(_V234_MEGA_TASK_FINISH(update_id, success, error)) if callable(_V234_MEGA_TASK_FINISH) else False
    key = _mega_task_id(update_id)
    target = 'done' if success else 'failed'
    with _TG_DURABLE_LOCK_V234:
        head = telegram_durable_bootstrap_v234(False)
        tasks = head.setdefault('tasks', {})
        row = tasks.get(key)
        if not isinstance(row, dict):
            row = {'update_id': key, 'backend': 'telegram'}
            tasks[key] = row
        row['state'] = target
        row['updated_at'] = now_local().isoformat(timespec='microseconds')
        row['error'] = str(error or '')[:1200]
        _tg_task_prune_done_v234(tasks)
        if not _tg_durable_persist_head_v234(f'task_{target}:{key}'):
            return False
    with _MEGA_TASK_LOCK:
        _mega_task_processing.discard(key)
        _mega_task_registry[key] = {'state': target, 'path': f'telegram-head:{key}', 'loaded_at': now_local().isoformat(timespec='seconds')}
        if success:
            _mega_task_counters['completed'] += 1
        else:
            _mega_task_counters['failed'] += 1
    return True

def _canon_mega_task_refresh_registry__002() -> dict:
    global _mega_task_registry_loaded_at, _mega_task_last_error
    if not telegram_durable_primary_v234():
        return _V234_MEGA_TASK_REFRESH() if callable(_V234_MEGA_TASK_REFRESH) else mega_task_registry_stats()
    try:
        head = telegram_durable_bootstrap_v234(True)
        tasks = head.get('tasks') or {}
        with _MEGA_TASK_LOCK:
            _mega_task_registry.clear()
            for key, row in tasks.items():
                if not isinstance(row, dict):
                    continue
                _mega_task_registry[str(key)] = {'state': str(row.get('state') or ''), 'path': f'telegram-head:{key}', 'loaded_at': now_local().isoformat(timespec='seconds')}
            _mega_task_registry_loaded_at = now_local().isoformat(timespec='seconds')
            _mega_task_last_error = ''
        return mega_task_registry_stats()
    except Exception as exc:
        _mega_task_last_error = str(exc)[:500]
        return mega_task_registry_stats()

def _canon_mega_task_registry_stats__001() -> dict:
    if not telegram_durable_primary_v234() and callable(_V234_MEGA_TASK_STATS):
        return _V234_MEGA_TASK_STATS()
    with _MEGA_TASK_LOCK:
        states = defaultdict(int)
        for row in _mega_task_registry.values():
            states[str((row or {}).get('state') or 'unknown')] += 1
        counters = dict(_mega_task_counters)
    st = telegram_durable_status_v234() if telegram_durable_configured_v234() else {}
    return {'backend': 'telegram', 'pending': int(states.get('pending', 0)), 'running': int(states.get('running', 0)), 'done': int(states.get('done', 0)), 'failed': int(states.get('failed', 0)), 'processing': len(_mega_task_processing), 'loaded_at': globals().get('_mega_task_registry_loaded_at', ''), 'last_error': str(st.get('last_error') or globals().get('_mega_task_last_error', '')), **counters}

def _tg_task_recover_one_v234(update_id: str, row: dict):
    key = _mega_task_id(update_id)
    state = str((row or {}).get('state') or '')
    if mega_task_known_state(key) == 'done':
        return
    if not mega_task_begin(key, allow_existing_running=state == 'running'):
        return
    try:
        task = _delta_json_clone(row or {})
        payload = task.get('payload') or {}
        if not isinstance(payload, dict) or not payload:
            raise RuntimeError('task payload is empty')
        restore_mega_task_context(task)
        chat_id = task.get('chat_id')
        update_type = str(task.get('update_type') or 'recovered')
        expected = _durable_expected_from_task_or_payload(task, payload)
        if durable_update_processed(key):
            mega_task_finish(key, True, 'processed_marker_present')
            return
        if state == 'running':
            if globals().get('_v230_constitution_finance_wait') and _v230_constitution_finance_wait(payload, expected):
                schedule_durable_task_finalize_retry(key, chat_id, update_type, 15.0, payload=payload, expected_effects=expected)
                return
            if not _mega_task_effect_exists(payload, expected):
                _repair_safe_missing_finance_effects(payload, expected)
                _repair_safe_missing_forward_secret_effects(payload, expected)
            if _mega_task_effect_exists(payload, expected):
                finalize_durable_task_after_business(key, chat_id, update_type, payload=payload, expected_effects=expected)
                return
            report = _durable_effect_report(payload, expected)
            mega_task_finish(key, False, f"needs_review_running: business not replayed; missing={report.get('missing', [])}; ambiguous={report.get('ambiguous', [])}")
            return
        execution_ctx = _execute_telegram_payload(payload, key, chat_id, update_type)
        expected_after = _durable_expected_after_execution(expected, execution_ctx, payload)
        if not finalize_durable_task_after_business(key, chat_id, update_type, payload=payload, expected_effects=expected_after):
            schedule_durable_task_finalize_retry(key, chat_id, update_type, 1.0, payload=payload, expected_effects=expected_after)
        with _MEGA_TASK_LOCK:
            _mega_task_counters['recovered'] += 1
        _TG_DURABLE_STATS_V234['task_recovers'] += 1
    except Exception as exc:
        mega_task_finish(key, False, str(exc))
        try:
            log_error(f'TG TASK RECOVERY FAILED update={key}: {exc}')
        except Exception:
            pass

def _canon_schedule_mega_task_recovery__002(delay: float | None=None):
    if not telegram_durable_primary_v234():
        return _V234_MEGA_TASK_RECOVERY(delay) if callable(_V234_MEGA_TASK_RECOVERY) else None
    if not mega_tasks_active():
        return None
    delay = max(0.1, float(delay if delay is not None else 1.0))

    def _scan():
        head = telegram_durable_bootstrap_v234(True)
        rows = [(str(k), dict(v)) for k, v in (head.get('tasks') or {}).items() if isinstance(v, dict) and str(v.get('state') or '') in {'pending', 'running'}]
        rows.sort(key=lambda kv: int(kv[0]) if kv[0].isdigit() else kv[0])
        for key, row in rows[:MEGA_TASK_RECOVERY_LIMIT]:
            pool = globals().get('RECOVERY_TASK_POOL')
            if pool is None or not pool.submit('telegram-recover-global', _tg_task_recover_one_v234, key, row):
                _tg_task_recover_one_v234(key, row)
    DELAYED_SCHEDULER.cancel('telegram-task-startup-recovery-v234')
    return DELAYED_SCHEDULER.schedule('telegram-task-startup-recovery-v234', delay, _scan)

def _canon_schedule_safe_failed_task_repairs__002(delay: float=6.0, limit: int=20):
    if telegram_durable_primary_v234():
        return None
    return _V234_MEGA_SAFE_FAILED_REPAIR(delay, limit) if callable(_V234_MEGA_SAFE_FAILED_REPAIR) else None
_V234_SECRET_MEGA_UPLOAD = globals().get('schedule_secret_mega_upload')

def telegram_secret_checkpoint_v234(chat_id: int) -> bool:
    if not telegram_durable_primary_v234():
        return False
    return telegram_schedule_delta_backup_v234(int(chat_id), delay=0.5, reason='secret')
try:
    _v177_legacy_0006_bot_journal('telegram_durable_primary_ready_v234', int(OWNER_ID or 0) or None, 'primary=telegram_channel; mega=optional_off_default; head=pinned; sqlite_snapshot=chunked; delta=discoverable')
except Exception:
    pass
STORAGE_MODE_FEATURES_KEY_V240 = 'storage_mode_features_v240'
_STORAGE_MODE_FEATURE_DEFAULTS_V240 = {'render': {'local_sqlite': True, 'local_queues': True, 'local_runtime': True}, 'telegram_durable': {'snapshot': True, 'delta': True, 'config': True, 'tasks': True, 'boot_restore': True}, 'mega': {'delta': True, 'config': True, 'tasks': True, 'system_generation': True, 'boot_restore': True, 'cleanup': True}}
_STORAGE_MODE_LOCKED_FEATURES_V240 = {'render': {'local_sqlite', 'local_queues', 'local_runtime'}, 'telegram_durable': set(), 'mega': set()}

def storage_mode_features_v240(mode: str | None=None) -> dict:
    mode = _storage_profile_normalize_v237_1(mode or storage_profile_v237_1())
    gs = _tg_v234_root_settings()
    all_rows = gs.setdefault(STORAGE_MODE_FEATURES_KEY_V240, {})
    row = all_rows.setdefault(mode, {})
    for key, default in (_STORAGE_MODE_FEATURE_DEFAULTS_V240.get(mode) or {}).items():
        row.setdefault(key, bool(default))
    for key in _STORAGE_MODE_LOCKED_FEATURES_V240.get(mode, set()):
        row[key] = True
    return row

def storage_mode_feature_enabled_v240(mode: str, feature: str, *, recovery: bool=False) -> bool:
    mode = _storage_profile_normalize_v237_1(mode)
    if recovery or bool(globals().get('_V240_RECOVERY_AUTHORITY_ACTIVE', False)):
        return True
    if storage_profile_v237_1() != mode:
        return False
    return bool(storage_mode_features_v240(mode).get(str(feature), False))

def set_storage_mode_feature_v240(mode: str, feature: str, enabled: bool) -> bool:
    mode = _storage_profile_normalize_v237_1(mode)
    feature = str(feature or '')
    if feature in _STORAGE_MODE_LOCKED_FEATURES_V240.get(mode, set()):
        return True
    if feature not in (_STORAGE_MODE_FEATURE_DEFAULTS_V240.get(mode) or {}):
        return False
    row = storage_mode_features_v240(mode)
    row[feature] = bool(enabled)
    try:
        save_data(data, root_only=True)
    except Exception:
        pass
    try:
        telegram_durable_persist_controls_v234()
    except Exception:
        pass
    return bool(row[feature])
_V240_TG_SNAPSHOT_ORIG = _canon_telegram_upload_sqlite_snapshot_v234__001
_V240_TG_DELTA_SCHEDULE_ORIG = _canon_telegram_schedule_delta_backup_v234__001
_V240_TG_FULL_SCHEDULE_ORIG = _canon_telegram_schedule_full_snapshot_v234__001
_V240_TG_RESTORE_ORIG = _canon_telegram_restore_sqlite_snapshot_v234__001
_V240_TG_APPLY_DELTA_ORIG = _canon_telegram_apply_remote_deltas_v234__001
_V240_TASK_UPLOAD_PENDING_ORIG = _canon_mega_task_upload_new_pending__002
_V240_TASK_RECOVERY_ORIG = _canon_schedule_mega_task_recovery__002

def _canon_telegram_upload_sqlite_snapshot_v234__002(force: bool=False) -> bool:
    if not storage_mode_feature_enabled_v240('telegram_durable', 'snapshot'):
        return False
    return bool(_V240_TG_SNAPSHOT_ORIG(force=force))

def _canon_telegram_schedule_delta_backup_v234__002(chat_id: int | None, delay: float | None=None, reason: str='change') -> bool:
    if not storage_mode_feature_enabled_v240('telegram_durable', 'delta'):
        return False
    return bool(_V240_TG_DELTA_SCHEDULE_ORIG(chat_id, delay=delay, reason=reason))

def _canon_telegram_schedule_full_snapshot_v234__002(reason: str='change', delay: float | None=None) -> bool:
    if not storage_mode_feature_enabled_v240('telegram_durable', 'snapshot'):
        return False
    return bool(_V240_TG_FULL_SCHEDULE_ORIG(reason=reason, delay=delay))

def _canon_telegram_restore_sqlite_snapshot_v234__002() -> tuple[bool, str]:
    if not storage_mode_feature_enabled_v240('telegram_durable', 'boot_restore'):
        return (False, 'Telegram boot restore disabled by active mode feature')
    return _V240_TG_RESTORE_ORIG()

def _canon_telegram_apply_remote_deltas_v234__002() -> int:
    if not storage_mode_feature_enabled_v240('telegram_durable', 'delta'):
        return 0
    return int(_V240_TG_APPLY_DELTA_ORIG() or 0)

def _canon_mega_task_upload_new_pending__003(update_id, task_payload: dict) -> bool:
    p = storage_profile_v237_1()
    if p == STORAGE_PROFILE_TELEGRAM_V237_1 and (not storage_mode_feature_enabled_v240('telegram_durable', 'tasks')):
        return False
    if p == STORAGE_PROFILE_MEGA_V237_1 and (not storage_mode_feature_enabled_v240('mega', 'tasks')):
        return False
    return bool(_V240_TASK_UPLOAD_PENDING_ORIG(update_id, task_payload))

def _canon_schedule_mega_task_recovery__003(delay: float | None=None):
    p = storage_profile_v237_1()
    if p == STORAGE_PROFILE_TELEGRAM_V237_1 and (not storage_mode_feature_enabled_v240('telegram_durable', 'tasks')):
        return None
    if p == STORAGE_PROFILE_MEGA_V237_1 and (not storage_mode_feature_enabled_v240('mega', 'tasks')):
        return None
    return _V240_TASK_RECOVERY_ORIG(delay)

# --- ИСТОЧНИК: 13_telegram_stable_slots.py ---
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

# --- ИСТОЧНИК: 14_mega_sharded_parallel.py ---
from concurrent.futures import ThreadPoolExecutor, as_completed

def _v240_env_int(name: str, default: int, low: int=1, high: int=64) -> int:
    try:
        return max(low, min(high, int(os.getenv(name, str(default)) or default)))
    except Exception:
        return default

def _v240_env_bool(name: str, default: str='1') -> bool:
    return str(os.getenv(name, default) or default).strip().casefold() in {'1', 'true', 'yes', 'on', 'да', 'вкл'}
MEGA_SHARDED_STORAGE_V240 = _v240_env_bool('MEGA_SHARDED_STORAGE', '1')
MEGA_PARALLEL_MAX_V240 = _v240_env_int('MEGA_PARALLEL_MAX', 2, 1, 16)
MEGA_SHARD_DELTA_WORKERS_V240 = _v240_env_int('MEGA_SHARD_DELTA_WORKERS', 2, 1, 8)
MEGA_SHARD_HEAD_ENABLED_V240 = _v240_env_bool('MEGA_SHARD_HEAD_ENABLED', '1')
MEGA_SHARD_ROOT_V240 = MEGA_BACKUP_DIR.rstrip('/') + '/shards'
MEGA_SHARD_CHATS_ROOT_V240 = MEGA_SHARD_ROOT_V240 + '/chats'

def _v240_mega_business_active() -> bool:
    """True only when MEGA is the selected durable contour, not Telegram-primary."""
    try:
        tg = globals().get('telegram_durable_primary_v234')
        if callable(tg) and bool(tg()):
            return False
    except Exception:
        pass
    try:
        return bool(mega_is_configured())
    except Exception:
        return False
_V240_LANE_LIMITS = {'finance': _v240_env_int('MEGA_LANE_FINANCE', 2, 1, 8), 'forwarding': _v240_env_int('MEGA_LANE_FORWARD', 2, 1, 8), 'reminders': _v240_env_int('MEGA_LANE_REMINDERS', 1, 1, 8), 'tasks': _v240_env_int('MEGA_LANE_TASKS', 2, 1, 8), 'gomonk': _v240_env_int('MEGA_LANE_GOMONK', 1, 1, 8), 'settings': _v240_env_int('MEGA_LANE_SETTINGS', 1, 1, 8), 'snapshot': _v240_env_int('MEGA_LANE_SNAPSHOT', 1, 1, 2), 'restore': _v240_env_int('MEGA_LANE_RESTORE', 2, 1, 8), 'journal': _v240_env_int('MEGA_LANE_JOURNAL', 1, 1, 4), 'cleanup': _v240_env_int('MEGA_LANE_CLEANUP', 1, 1, 2), 'misc': _v240_env_int('MEGA_LANE_MISC', 1, 1, 8)}
_V240_LANE_SEM = {k: threading.BoundedSemaphore(v) for k, v in _V240_LANE_LIMITS.items()}
_V240_PAR_CV = threading.Condition(threading.RLock())
_V240_PAR_WAITING = {0: 0, 1: 0, 2: 0, 3: 0}
_V240_PAR_ACTIVE = 0
_V240_RESOURCE_GUARD = threading.RLock()
_V240_RESOURCE_LOCKS = {}
_V240_PAR_STATS_LOCK = threading.RLock()
_V240_PAR_STATS = {'active': 0, 'peak': 0, 'started': 0, 'completed': 0, 'errors': 0, 'by_lane': defaultdict(lambda: {'started': 0, 'completed': 0, 'errors': 0, 'active': 0, 'peak': 0})}

def mega_shard_chat_dir_v240(chat_id: int) -> str:
    return f'{MEGA_SHARD_CHATS_ROOT_V240}/chat_{int(chat_id)}'

def mega_shard_domain_dir_v240(chat_id: int, domain: str) -> str:
    safe = re.sub('[^a-z0-9_-]+', '_', str(domain or 'state').casefold()).strip('_') or 'state'
    return mega_shard_chat_dir_v240(int(chat_id)).rstrip('/') + '/' + safe

def _v240_chat_id_from_path(text: str):
    m = re.search('/shards/chats/chat_(-?\\d+)(?:/|$)', str(text or '').replace('\\', '/'))
    if m:
        try:
            return int(m.group(1))
        except Exception:
            return None
    return None

def _v240_lane_and_resource(cmd: str, args) -> tuple[str, str, int]:
    parts = [str(x or '').replace('\\', '/') for x in args or []]
    text = ' '.join(parts)
    low = text.casefold()
    chat_id = _v240_chat_id_from_path(text)
    domain = None
    if chat_id is not None:
        m = re.search('/shards/chats/chat_-?\\d+/([^/\\s]+)', low)
        domain = (m.group(1) if m else 'state').strip()
    lane = 'misc'
    pri = 1
    if domain in {'finance', 'forwarding', 'reminders', 'tasks', 'gomonk', 'settings'}:
        lane = domain
        pri = 0 if domain in {'finance', 'tasks'} else 1
    elif '/ledger/finance' in low:
        lane, pri = ('finance', 0)
    elif '/tasks/' in low:
        lane, pri = ('tasks', 0 if '/pending/' in low else 1)
    elif '/database/' in low or 'current_manifest' in low or 'generation_' in low or ('.sqlite' in low):
        lane = 'restore' if str(cmd) in {'mega-get', 'mega-find'} else 'snapshot'
        pri = 1 if lane == 'restore' else 2
    elif '/runtime/journal' in low or 'journal_' in low or '/runtime/' in low:
        lane, pri = ('journal', 3)
    elif str(cmd) == 'mega-rm':
        lane, pri = ('cleanup', 3)
    elif str(cmd) in {'mega-get', 'mega-find'}:
        lane, pri = ('restore', 1)
    canonical_tokens = ('current_manifest.json', 'storage_control.json', 'latest_global.json')
    if any((tok in low for tok in canonical_tokens)):
        resource = 'canonical:pointer'
    elif chat_id is not None:
        resource = f'chat:{chat_id}:{domain or lane}'
    elif lane == 'finance':
        m = re.search('ledger_\\d+_(-?\\d+)_', low)
        resource = f'finance:{m.group(1)}' if m else 'finance:legacy'
    elif lane == 'tasks':
        m = re.search('task_([a-z0-9_-]+)\\.json', low)
        resource = f'task:{m.group(1)}' if m else 'tasks:legacy'
    elif lane == 'snapshot':
        resource = 'snapshot:canonical'
    elif str(cmd) in {'mega-login', 'mega-logout', 'mega-whoami'}:
        resource = 'session'
    else:
        target = parts[-1] if parts else str(cmd or 'misc')
        resource = f'{lane}:{target[:220]}'
    return (lane, resource, pri)

def _v240_resource_lock(key: str):
    with _V240_RESOURCE_GUARD:
        lock = _V240_RESOURCE_LOCKS.get(key)
        if lock is None:
            lock = threading.RLock()
            _V240_RESOURCE_LOCKS[key] = lock
        return lock

def _v240_priority_enter(priority: int):
    global _V240_PAR_ACTIVE
    priority = max(0, min(3, int(priority)))
    with _V240_PAR_CV:
        _V240_PAR_WAITING[priority] += 1
        try:
            while _V240_PAR_ACTIVE >= MEGA_PARALLEL_MAX_V240 or any((_V240_PAR_WAITING[p] > 0 for p in range(priority))):
                _V240_PAR_CV.wait(timeout=0.25)
            _V240_PAR_ACTIVE += 1
        finally:
            _V240_PAR_WAITING[priority] = max(0, _V240_PAR_WAITING[priority] - 1)

def _v240_priority_exit():
    global _V240_PAR_ACTIVE
    with _V240_PAR_CV:
        _V240_PAR_ACTIVE = max(0, _V240_PAR_ACTIVE - 1)
        _V240_PAR_CV.notify_all()

def mega_parallel_execute_v240(exe: str, cmd: str, args, timeout_value):
    """Execute MEGAcmd with bounded parallelism and per-shard serialization."""
    if not MEGA_SHARDED_STORAGE_V240:
        with MEGA_COMMAND_LOCK:
            return subprocess.run([exe] + list(args or []), capture_output=True, text=True, timeout=timeout_value)
    lane, resource, priority = _v240_lane_and_resource(cmd, args)
    lane_sem = _V240_LANE_SEM.get(lane) or _V240_LANE_SEM['misc']
    resource_lock = _v240_resource_lock(resource)
    with resource_lock:
        lane_sem.acquire()
        _v240_priority_enter(priority)
        with _V240_PAR_STATS_LOCK:
            _V240_PAR_STATS['active'] += 1
            _V240_PAR_STATS['started'] += 1
            _V240_PAR_STATS['peak'] = max(_V240_PAR_STATS['peak'], _V240_PAR_STATS['active'])
            row = _V240_PAR_STATS['by_lane'][lane]
            row['active'] += 1
            row['started'] += 1
            row['peak'] = max(row['peak'], row['active'])
        try:
            cp = subprocess.run([exe] + list(args or []), capture_output=True, text=True, timeout=timeout_value)
            with _V240_PAR_STATS_LOCK:
                _V240_PAR_STATS['completed'] += 1
                _V240_PAR_STATS['by_lane'][lane]['completed'] += 1
            return cp
        except Exception:
            with _V240_PAR_STATS_LOCK:
                _V240_PAR_STATS['errors'] += 1
                _V240_PAR_STATS['by_lane'][lane]['errors'] += 1
            raise
        finally:
            with _V240_PAR_STATS_LOCK:
                _V240_PAR_STATS['active'] = max(0, _V240_PAR_STATS['active'] - 1)
                _V240_PAR_STATS['by_lane'][lane]['active'] = max(0, _V240_PAR_STATS['by_lane'][lane]['active'] - 1)
            _v240_priority_exit()
            lane_sem.release()

def mega_parallel_status_v240() -> dict:
    with _V240_PAR_STATS_LOCK:
        return {'enabled': bool(MEGA_SHARDED_STORAGE_V240), 'global_limit': int(MEGA_PARALLEL_MAX_V240), 'active': int(_V240_PAR_STATS['active']), 'peak': int(_V240_PAR_STATS['peak']), 'started': int(_V240_PAR_STATS['started']), 'completed': int(_V240_PAR_STATS['completed']), 'errors': int(_V240_PAR_STATS['errors']), 'lane_limits': dict(_V240_LANE_LIMITS), 'by_lane': {k: dict(v) for k, v in _V240_PAR_STATS['by_lane'].items()}}
_V240_META_LOCK = threading.RLock()
_V240_META_SEEDED = set()

def _v240_chat_meta_payload(chat_id: int) -> dict:
    cid = int(chat_id)
    info = {}
    try:
        info = dict(get_chat_store(cid).get('info') or {})
    except Exception:
        info = {}
    return {'kind': 'telegram_bot_mega_chat_shard', 'schema_version': 1, 'chat_id': cid, 'chat_type': str(info.get('type') or ('private' if cid > 0 else 'unknown')), 'title': str(info.get('title') or get_chat_display_name(cid) or f'Чат {cid}')[:250], 'bot_version': str(globals().get('VERSION') or ''), 'updated_at': now_local().isoformat(timespec='seconds')}

def _v240_seed_chat_meta_sync(chat_id: int):
    cid = int(chat_id)
    with _V240_META_LOCK:
        if cid in _V240_META_SEEDED:
            return True
    folder = mega_shard_chat_dir_v240(cid)
    tmp = ''
    try:
        os.makedirs(MEGA_LOCAL_TMP_DIR, exist_ok=True)
        fd, tmp = tempfile.mkstemp(prefix=f'mega_shard_meta_{cid}_', suffix='.json', dir=MEGA_LOCAL_TMP_DIR)
        os.close(fd)
        _save_json(tmp, _v240_chat_meta_payload(cid))
        ok = bool(mega_put_replace(tmp, folder, 'meta.json', archive_previous=False))
        if ok:
            with _V240_META_LOCK:
                _V240_META_SEEDED.add(cid)
        return ok
    except Exception as exc:
        try:
            log_error(f'mega shard meta {cid}: {exc}')
        except Exception:
            pass
        return False
    finally:
        try:
            if tmp and os.path.exists(tmp):
                os.remove(tmp)
        except Exception:
            pass

def _v240_schedule_chat_meta(chat_id: int):
    cid = int(chat_id)
    with _V240_META_LOCK:
        if cid in _V240_META_SEEDED:
            return
    pool = globals().get('BACKUP_TASK_POOL')
    if pool is not None:
        try:
            if pool.submit_unique(f'mega-shard-meta:{cid}', _v240_seed_chat_meta_sync, cid):
                return
        except Exception:
            pass
    threading.Thread(target=_v240_seed_chat_meta_sync, args=(cid,), daemon=True).start()

def _v240_publish_head_sync(chat_id: int, domain: str, remote_delta: str, payload: dict):
    cid = int(chat_id)
    domain = str(domain or 'state')
    expected_epoch = int((payload or {}).get('_storage_epoch_v241', globals().get('_V241_STORAGE_EPOCH', 0)) or 0)
    if expected_epoch != int(globals().get('_V241_STORAGE_EPOCH', 0) or 0) or globals().get('_V241_RESTORE_ACTIVE', False):
        return False
    tmp = ''
    try:
        folder = mega_shard_domain_dir_v240(cid, domain)
        head = {'kind': 'telegram_bot_mega_shard_head', 'schema_version': 1, 'chat_id': cid, 'domain': domain, 'latest_delta': str(remote_delta or ''), 'latest_delta_id': str((payload or {}).get('delta_id') or ''), 'event_count': int((payload or {}).get('event_count') or 0), 'updated_at': str((payload or {}).get('created_at') or now_local().isoformat(timespec='microseconds')), 'bot_version': str(globals().get('VERSION') or ''), 'storage_lineage_v239': str((payload or {}).get('storage_lineage_v239') or '')}
        fd, tmp = tempfile.mkstemp(prefix=f'mega_head_{cid}_{domain}_', suffix='.json', dir=MEGA_LOCAL_TMP_DIR)
        os.close(fd)
        _save_json(tmp, head)
        return bool(mega_put_replace(tmp, folder, 'HEAD.json', archive_previous=False))
    except Exception as exc:
        try:
            log_error(f'mega shard HEAD {cid}/{domain}: {exc}')
        except Exception:
            pass
        return False
    finally:
        try:
            if tmp and os.path.exists(tmp):
                os.remove(tmp)
        except Exception:
            pass

def _v240_schedule_head(chat_id: int, domain: str, remote_delta: str, payload: dict):
    if not MEGA_SHARD_HEAD_ENABLED_V240:
        return
    if globals().get('_V241_RESTORE_ACTIVE', False):
        return
    _v240_schedule_chat_meta(chat_id)
    payload = _delta_json_clone(payload or {})
    payload['_storage_epoch_v241'] = int(globals().get('_V241_STORAGE_EPOCH', 0) or 0)
    pool = globals().get('BACKUP_TASK_POOL')
    key = f'mega-shard-head:{int(chat_id)}:{domain}'
    if pool is not None:
        try:
            if pool.submit_unique(key, _v240_publish_head_sync, int(chat_id), str(domain), str(remote_delta), payload):
                return
        except Exception:
            pass
    threading.Thread(target=_v240_publish_head_sync, args=(int(chat_id), str(domain), str(remote_delta), payload), daemon=True).start()
_V240_ORIG_RUN_DELTA_BATCH = _canon_run_delta_batch__001
_V240_PENDING_DOMAIN_LOCK = threading.RLock()
_V240_PENDING_DOMAINS = defaultdict(set)
_V240_ORIG_SCHEDULE_DELTA = _canon_schedule_delta_backup__002
_V240_ORIG_CRITICAL_DELTA = _canon_persist_critical_delta_now__002

def _v240_domain_from_reason(reason: str) -> str:
    text = str(reason or 'change').casefold()
    if 'remind' in text or 'напомин' in text:
        return 'reminders'
    if 'forward' in text or 'пересыл' in text:
        return 'forwarding'
    if 'gomonk' in text or 'гомон' in text:
        return 'gomonk'
    if 'task' in text or 'задач' in text:
        return 'tasks'
    if any((x in text for x in ('finance', 'record', 'balance', 'expense', 'income', 'delta_retry', 'quick_upload'))):
        return 'finance'
    if any((x in text for x in ('setting', 'config', 'tenant', 'annotation', 'permission', 'google', 'contour', 'constitution'))):
        return 'settings'
    return 'state'

def _canon_schedule_delta_backup__003(chat_id=None, delay=None, reason='change'):
    if chat_id is not None and MEGA_SHARDED_STORAGE_V240 and _v240_mega_business_active():
        try:
            with _V240_PENDING_DOMAIN_LOCK:
                _V240_PENDING_DOMAINS[int(chat_id)].add(_v240_domain_from_reason(reason))
        except Exception:
            pass
    if callable(_V240_ORIG_SCHEDULE_DELTA):
        return _V240_ORIG_SCHEDULE_DELTA(chat_id, delay=delay, reason=reason)
    return False

def _canon_persist_critical_delta_now__003(chat_id: int) -> bool:
    if MEGA_SHARDED_STORAGE_V240 and _v240_mega_business_active():
        try:
            with _V240_PENDING_DOMAIN_LOCK:
                _V240_PENDING_DOMAINS[int(chat_id)].add('finance')
        except Exception:
            pass
    if callable(_V240_ORIG_CRITICAL_DELTA):
        return bool(_V240_ORIG_CRITICAL_DELTA(int(chat_id)))
    return False

def _v240_pick_pending_domain(chat_id: int) -> str:
    with _V240_PENDING_DOMAIN_LOCK:
        vals = set(_V240_PENDING_DOMAINS.get(int(chat_id)) or set())
    if len(vals) == 1:
        return next(iter(vals))
    if not vals:
        try:
            if is_finance_mode(int(chat_id)):
                return 'finance'
        except Exception:
            pass
        return 'state'
    return 'mixed'

def _v240_shard_delta_day_dir(chat_id: int, domain: str, day_key: str) -> str:
    return mega_shard_domain_dir_v240(int(chat_id), domain).rstrip('/') + '/deltas/' + str(day_key)

def _v240_delta_upload_payload(payload: dict) -> tuple[bool, str]:
    if not payload or not mega_is_configured():
        return (False, '')
    cid = payload.get('_v240_shard_chat_id')
    if not MEGA_SHARDED_STORAGE_V240 or cid is None:
        return _delta_upload_payload_legacy_v240(payload)
    domain = str(payload.get('_v240_shard_domain') or 'state')
    day = str(payload.get('created_at') or today_key())[:10]
    remote_dir = _v240_shard_delta_day_dir(int(cid), domain, day)
    clean = dict(payload)
    clean.pop('_v240_shard_chat_id', None)
    clean.pop('_v240_shard_domain', None)
    clean['storage_layout'] = 'mega_sharded_parallel_v240'
    clean['shard'] = {'chat_id': int(cid), 'domain': domain}
    name = f"delta_{clean.get('delta_id')}.json"
    tmp = ''
    try:
        soft = max(128 * 1024, int(os.getenv('MEGA_DELTA_SOFT_WARN_BYTES', str(512 * 1024)) or 512 * 1024))
        hard = max(soft + 1, int(os.getenv('MEGA_DELTA_HARD_MAX_BYTES', str(1024 * 1024)) or 1024 * 1024))
        encoded = json.dumps(clean, ensure_ascii=False, separators=(',', ':'), default=str).encode('utf-8')
        if len(encoded) > hard:
            try:
                log_error(f'[MEGA SHARD DELTA BLOCKED] chat={cid} domain={domain} bytes={len(encoded)} hard={hard}; full snapshot scheduled')
            except Exception:
                pass
            _mark_global_snapshot_pending()
            return (False, '')
        if len(encoded) > soft:
            try:
                bot_journal('mega_shard_delta_large_v240', int(cid), f'domain={domain}; bytes={len(encoded)}; soft={soft}', 'WARN')
            except Exception:
                pass
        os.makedirs(MEGA_LOCAL_TMP_DIR, exist_ok=True)
        tmp = os.path.join(MEGA_LOCAL_TMP_DIR, name)
        with open(tmp, 'wb') as fh:
            fh.write(encoded)
        mega_ensure_remote_path(remote_dir)
        _mega_run('mega-put', [tmp, remote_dir], check=True, timeout=MEGA_TIMEOUT)
        remote = remote_dir.rstrip('/') + '/' + name
        _v240_schedule_head(int(cid), domain, remote, clean)
        return (True, remote)
    except Exception as exc:
        try:
            log_error(f'[MEGA SHARD DELTA] chat={cid} domain={domain}: {exc}')
        except Exception:
            pass
        return (False, '')
    finally:
        try:
            if tmp and os.path.exists(tmp):
                os.remove(tmp)
        except Exception:
            pass
_delta_upload_payload_legacy_v240 = _canon_delta_upload_payload__001

def _canon_run_delta_batch__002():
    """Build one exact delta per chat and upload independent shards in parallel."""
    global _delta_last_success_at, _delta_last_file, _delta_last_event_count, _delta_last_error, _delta_root_baseline
    batch_epoch = int(globals().get('_V241_STORAGE_EPOCH', 0) or 0)
    if globals().get('_V241_RESTORE_ACTIVE', False):
        return False
    if not MEGA_SHARDED_STORAGE_V240:
        return bool(_V240_ORIG_RUN_DELTA_BATCH()) if callable(_V240_ORIG_RUN_DELTA_BATCH) else False
    with _delta_state_lock:
        chat_ids = sorted(_delta_pending_chats)
        generation_map = {cid: int(_delta_chat_generation.get(cid, 0)) for cid in chat_ids}
    if not chat_ids:
        return True
    built = []
    for cid in chat_ids:
        payload, baseline = _build_delta_payload([cid], {cid: generation_map[cid]})
        if payload is not None:
            payload['_v240_shard_chat_id'] = int(cid)
            payload['_v240_shard_domain'] = _v240_pick_pending_domain(cid)
            payload['_storage_epoch_v241'] = batch_epoch
            try:
                _lineage_fn = globals().get('_v239_storage_lineage')
                if callable(_lineage_fn):
                    payload['storage_lineage_v239'] = str(_lineage_fn(True) or '')
            except Exception:
                pass
        built.append((cid, payload, baseline))
    uploads = {}
    todo = [(cid, payload, baseline) for cid, payload, baseline in built if payload is not None]
    if batch_epoch != int(globals().get('_V241_STORAGE_EPOCH', 0) or 0) or globals().get('_V241_RESTORE_ACTIVE', False):
        try:
            bot_journal('stale_delta_batch_skipped_v241', None, f"job={batch_epoch}; current={globals().get('_V241_STORAGE_EPOCH', 0)}")
        except Exception:
            pass
        return False
    if todo:
        workers = min(MEGA_SHARD_DELTA_WORKERS_V240, len(todo))
        with ThreadPoolExecutor(max_workers=max(1, workers), thread_name_prefix='mega-shard-delta') as ex:
            future_map = {ex.submit(_v240_delta_upload_payload, payload): (cid, payload, baseline) for cid, payload, baseline in todo}
            for fut in as_completed(future_map):
                cid, payload, baseline = future_map[fut]
                try:
                    uploads[cid] = (fut.result(), payload, baseline)
                except Exception as exc:
                    uploads[cid] = ((False, ''), payload, baseline)
                    log_error(f'mega shard delta worker {cid}: {exc}')
    success_any = False
    failed = []
    latest_remote = ''
    total_events = 0
    root_candidate = None
    for cid, payload, baseline in built:
        if payload is None:
            ok, remote = (True, '')
        else:
            (ok, remote), _, _ = uploads.get(cid, ((False, ''), payload, baseline))
        if ok:
            with _delta_state_lock:
                for bid, sigs in (baseline.get('record_sigs') or {}).items():
                    _delta_record_baseline[int(bid)] = dict(sigs or {})
                for bid, sigs in (baseline.get('meta_sigs') or {}).items():
                    _delta_meta_baseline[int(bid)] = dict(sigs or {})
                if int(_delta_chat_generation.get(cid, 0)) == int(generation_map[cid]):
                    _delta_pending_chats.discard(cid)
            with _V240_PENDING_DOMAIN_LOCK:
                _V240_PENDING_DOMAINS.pop(int(cid), None)
            root_candidate = baseline.get('root_sigs') or root_candidate
            if payload is not None:
                success_any = True
                latest_remote = remote or latest_remote
                total_events += int(payload.get('event_count') or 0)
        else:
            failed.append(cid)
    if root_candidate is not None and (success_any or not todo):
        with _delta_state_lock:
            _delta_root_baseline = dict(root_candidate or {})
    with timer_lock:
        for cid in chat_ids:
            if cid not in failed:
                _quick_backup_timers.pop(int(cid), None)
                _quick_backup_dirty_chats.discard(int(cid))
    if success_any:
        _delta_last_success_at = now_local().isoformat(timespec='microseconds')
        _delta_last_file = latest_remote
        _delta_last_event_count = total_events
        _delta_last_error = ''
        _mark_global_snapshot_pending()
        try:
            bot_journal('mega_sharded_delta_batch_v240', None, f'chats={len(chat_ids) - len(failed)}; failed={len(failed)}; events={total_events}; workers={min(MEGA_SHARD_DELTA_WORKERS_V240, max(1, len(todo)))}')
        except Exception:
            pass
    if failed:
        _delta_last_error = 'shard delta upload failed: ' + ','.join((str(x) for x in failed[:8]))
        return False
    with _delta_state_lock:
        more_pending = bool(_delta_pending_chats)
    if more_pending:
        schedule_delta_backup(None, delay=1.0, reason='changes_during_upload')
    return True
try:
    _V234_MEGA_RUN_DELTA_BATCH = _canon_run_delta_batch__002
except Exception:
    pass

def _v240_delta_sort_key(path: str):
    name = os.path.basename(str(path or ''))
    m = re.search('delta_(\\d{8})_(\\d{6})_(\\d{6})_', name)
    if m:
        return ''.join(m.groups())
    return name

def _canon_delta_remote_candidates_after__002(created_at: str, limit: int | None=None) -> list[str]:
    rows = []
    try:
        rows.extend(_mega_find_remote_files(mega_delta_remote_root(), 'delta_*.json'))
    except Exception:
        pass
    if MEGA_SHARDED_STORAGE_V240:
        try:
            rows.extend(_mega_find_remote_files(MEGA_SHARD_CHATS_ROOT_V240, 'delta_*.json'))
        except Exception:
            pass
    base_ts = _parse_iso_timestamp(created_at)
    selected = []
    for path in sorted(set(rows), key=_v240_delta_sort_key):
        name = os.path.basename(path)
        match = re.search('delta_(\\d{8})_(\\d{6})_(\\d{6})_', name)
        if match:
            try:
                dt = datetime.strptime(''.join(match.groups()), '%Y%m%d%H%M%S%f').replace(tzinfo=get_tz())
                if dt.timestamp() <= base_ts:
                    continue
            except Exception:
                pass
        selected.append(path)
    return selected[:int(limit or MEGA_DELTA_RESTORE_LIMIT)]

def _canon_prune_delta_files_after_full_snapshot__002():
    try:
        rows = []
        try:
            rows.extend(_mega_find_remote_files(mega_delta_remote_root(), 'delta_*.json'))
        except Exception:
            pass
        if MEGA_SHARDED_STORAGE_V240:
            try:
                rows.extend(_mega_find_remote_files(MEGA_SHARD_CHATS_ROOT_V240, 'delta_*.json'))
            except Exception:
                pass
        rows = sorted(set(rows), key=_v240_delta_sort_key, reverse=True)
        keep = max(30, int(MEGA_DELTA_KEEP_FILES))
        removed = 0
        for remote_path in rows[keep:]:
            try:
                if _mega_run('mega-rm', [remote_path], check=False, timeout=30).returncode == 0:
                    removed += 1
            except Exception:
                pass
        if removed:
            try:
                bot_journal('mega_delta_pruned_v240', None, f'removed={removed}; keep={keep}; sharded=1')
            except Exception:
                pass
        return removed
    except Exception as exc:
        try:
            log_error(f'delta prune v240: {exc}')
        except Exception:
            pass
        return 0

def _canon_v177_download_remote_json_batch__002(remote_paths: list[str], batch_threshold: int=6) -> tuple[dict, list[str]]:
    paths = [str(x) for x in remote_paths or [] if str(x or '').strip()]
    if not paths:
        return ({}, [])
    grouped = defaultdict(list)
    for remote in paths:
        grouped[remote.rsplit('/', 1)[0] if '/' in remote else remote].append(remote)
    mapping = {}
    cleanup_dirs = []
    guard = threading.RLock()

    def fetch_group(parent, group):
        local_map = {}
        dirs = []
        if len(group) >= int(batch_threshold):
            workdir = tempfile.mkdtemp(prefix='v240_mega_batch_')
            dirs.append(workdir)
            try:
                _mega_run('mega-get', [parent, workdir], check=True, timeout=max(float(MEGA_TIMEOUT), 180.0))
                found = {}
                for base, _dirs, files in os.walk(workdir):
                    for name in files:
                        found.setdefault(name, os.path.join(base, name))
                for remote in group:
                    local = found.get(os.path.basename(remote))
                    if local and os.path.isfile(local):
                        local_map[remote] = local
            except Exception as exc:
                try:
                    log_error(f'[MEGA BATCH RESTORE v240] folder fallback {parent}: {str(exc)[:240]}')
                except Exception:
                    pass
        for remote in group:
            if remote in local_map:
                continue
            local = _mega_download_remote_path(remote)
            if local:
                local_map[remote] = local
                dirs.append(os.path.dirname(local))
        return (local_map, dirs)
    workers = min(_V240_LANE_LIMITS['restore'], len(grouped))
    with ThreadPoolExecutor(max_workers=max(1, workers), thread_name_prefix='mega-restore') as ex:
        futs = [ex.submit(fetch_group, parent, group) for parent, group in grouped.items()]
        for fut in as_completed(futs):
            try:
                lm, ds = fut.result()
                mapping.update(lm)
                cleanup_dirs.extend(ds)
            except Exception as exc:
                try:
                    log_error(f'mega restore parallel batch: {exc}')
                except Exception:
                    pass
    return (mapping, cleanup_dirs)
_V240_ORIG_CHAT_BACKUP_BUNDLE = _canon_mega_upload_chat_backup_bundle__001
_V240_ORIG_CHAT_LATEST_ONLY = _canon_mega_upload_chat_latest_json_only__001

def _canon_mega_upload_chat_backup_bundle__002(chat_id: int, month_key: str | None=None) -> bool:
    """Same public command semantics; files now live under chat/finance shard."""
    if not MEGA_SHARDED_STORAGE_V240 or not _v240_mega_business_active():
        return bool(_V240_ORIG_CHAT_BACKUP_BUNDLE(chat_id, month_key)) if callable(_V240_ORIG_CHAT_BACKUP_BUNDLE) else False
    if not is_backup_to_mega_enabled(chat_id):
        return False
    cid = int(chat_id)
    try:
        save_chat_json(cid)
        finance_root = mega_shard_domain_dir_v240(cid, 'finance')
        checkpoint_dir = finance_root + '/checkpoints'
        ok = bool(mega_put_replace(chat_json_file(cid), checkpoint_dir, 'latest.json', archive_previous=True))
        month_key = month_key or current_month_key()
        month_files = save_chat_monthly_backup_files(cid, month_key)
        json_month_path = month_files.get('json')
        if json_month_path:
            ok = bool(mega_put_replace(json_month_path, finance_root + '/monthly/' + str(month_key), 'current.json', archive_previous=True)) and ok
        _v240_schedule_chat_meta(cid)
        if ok:
            try:
                bot_journal('mega_chat_backup_sharded_v240', cid, f'month={month_key}')
            except Exception:
                pass
        return ok
    except Exception as exc:
        try:
            log_error(f'[MEGA SHARD CHAT BACKUP ERROR] {cid}: {exc}')
        except Exception:
            pass
        return False

def _canon_mega_upload_chat_latest_json_only__002(chat_id: int) -> bool:
    if not MEGA_SHARDED_STORAGE_V240 or not _v240_mega_business_active():
        return bool(_V240_ORIG_CHAT_LATEST_ONLY(chat_id)) if callable(_V240_ORIG_CHAT_LATEST_ONLY) else False
    cid = int(chat_id)
    if not is_backup_to_mega_enabled(cid):
        return False
    try:
        local_path = chat_json_file(cid)
        if not os.path.exists(local_path):
            local_path = save_chat_json_only(cid)
        if not local_path:
            return False
        _v240_schedule_chat_meta(cid)
        return bool(mega_put_replace(local_path, mega_shard_domain_dir_v240(cid, 'finance') + '/checkpoints', 'latest.json', archive_previous=True))
    except Exception as exc:
        try:
            log_error(f'mega_upload_chat_latest_json_only shard v240({cid}): {exc}')
        except Exception:
            pass
        return False
_V240_ORIG_TASK_UPLOAD_PENDING = _canon_mega_task_upload_new_pending__003
_V240_ORIG_TASK_MOVE = _canon_mega_task_move__001
_V240_ORIG_TASK_REFRESH = _canon_mega_task_refresh_registry__002

def _v240_task_dir(chat_id: int, state: str) -> str:
    state = str(state or 'pending').casefold()
    if state not in {'pending', 'running', 'done', 'failed'}:
        state = 'pending'
    return mega_shard_domain_dir_v240(int(chat_id), 'tasks').rstrip('/') + '/' + state

def _canon_mega_task_upload_new_pending__004(update_id, task_payload: dict) -> bool:
    global _mega_task_last_error
    try:
        tg = globals().get('telegram_durable_primary_v234')
        if callable(tg) and bool(tg()):
            return bool(_V240_ORIG_TASK_UPLOAD_PENDING(update_id, task_payload)) if callable(_V240_ORIG_TASK_UPLOAD_PENDING) else False
    except Exception:
        pass
    chat_id = (task_payload or {}).get('chat_id')
    if not MEGA_SHARDED_STORAGE_V240 or chat_id in (None, ''):
        return bool(_V240_ORIG_TASK_UPLOAD_PENDING(update_id, task_payload)) if callable(_V240_ORIG_TASK_UPLOAD_PENDING) else False
    key = _mega_task_id(update_id)
    local_path = ''
    started = time.monotonic()
    if not mega_tasks_active():
        return False
    try:
        known = mega_task_known_state(key)
        if known in {'pending', 'running', 'done'}:
            return True
        remote_dir = _v240_task_dir(int(chat_id), 'pending')
        mega_ensure_remote_path(remote_dir)
        os.makedirs(MEGA_LOCAL_TMP_DIR, exist_ok=True)
        local_path = os.path.join(MEGA_LOCAL_TMP_DIR, mega_task_filename(key))
        with open(local_path, 'w', encoding='utf-8') as fh:
            json.dump(task_payload, fh, ensure_ascii=False, separators=(',', ':'), default=str)
        try:
            _mega_run('mega-put', [local_path, remote_dir], check=True, timeout=MEGA_TIMEOUT)
        except Exception:
            existing = _mega_find_remote_files(remote_dir, mega_task_filename(key), limit=2)
            if not existing:
                raise
        remote_final = remote_dir.rstrip('/') + '/' + mega_task_filename(key)
        _mega_task_update_registry(key, 'pending', remote_final)
        with _MEGA_TASK_LOCK:
            _mega_task_counters['persisted'] += 1
        _v240_schedule_chat_meta(int(chat_id))
        try:
            bot_journal('mega_task_timing', int(chat_id), f'phase=sharded_pending_v240 update={key} elapsed={time.monotonic() - started:.3f}s')
        except Exception:
            pass
        return True
    except Exception as exc:
        _mega_task_last_error = str(exc)[:500]
        with _MEGA_TASK_LOCK:
            _mega_task_counters['persist_errors'] += 1
        try:
            log_error(f'[MEGA SHARD TASK PERSIST] update={key}: {exc}')
        except Exception:
            pass
        return False
    finally:
        try:
            if local_path and os.path.exists(local_path):
                os.remove(local_path)
        except Exception:
            pass

def _canon_mega_task_move__002(update_id, from_state: str, to_state: str) -> bool:
    global _mega_task_last_error
    if not MEGA_SHARDED_STORAGE_V240:
        return bool(_V240_ORIG_TASK_MOVE(update_id, from_state, to_state)) if callable(_V240_ORIG_TASK_MOVE) else False
    key = _mega_task_id(update_id)
    with _MEGA_TASK_LOCK:
        row = dict(_mega_task_registry.get(key) or {})
    src = str(row.get('path') or mega_task_remote_path(key, from_state))
    norm = src.replace('\\', '/')
    if f'/{from_state}/' in norm:
        dst = norm.replace(f'/{from_state}/', f'/{to_state}/', 1)
        dst_dir = dst.rsplit('/', 1)[0]
    else:
        dst_dir = mega_task_remote_dir(to_state)
        dst = dst_dir.rstrip('/') + '/' + mega_task_filename(key)
    try:
        mega_ensure_remote_path(dst_dir)
        res = _mega_run('mega-mv', [src, dst], check=False, timeout=60)
        if res.returncode != 0:
            found = _mega_find_remote_files(dst_dir, mega_task_filename(key), limit=2)
            if not found:
                raise RuntimeError((res.stderr or res.stdout or f'cannot move {src} -> {dst}')[:500])
        _mega_task_update_registry(key, to_state, dst)
        return True
    except Exception as exc:
        _mega_task_last_error = str(exc)[:500]
        try:
            log_error(f'[MEGA SHARD TASK MOVE] update={key} {from_state}->{to_state}: {exc}')
        except Exception:
            pass
        return False

def _canon_mega_task_refresh_registry__003() -> dict:
    global _mega_task_registry_loaded_at, _mega_task_last_error
    if not mega_tasks_active():
        return mega_task_registry_stats()
    try:
        tg = globals().get('telegram_durable_primary_v234')
        if callable(tg) and bool(tg()):
            return _V240_ORIG_TASK_REFRESH() if callable(_V240_ORIG_TASK_REFRESH) else mega_task_registry_stats()
    except Exception:
        pass
    if callable(_V240_ORIG_TASK_REFRESH):
        try:
            _V240_ORIG_TASK_REFRESH()
        except Exception:
            pass
    try:
        rows = _mega_find_remote_files(MEGA_SHARD_CHATS_ROOT_V240, 'task_*.json', limit=None) if MEGA_SHARDED_STORAGE_V240 else []
        rank = {'failed': 1, 'pending': 2, 'running': 3, 'done': 4}
        with _MEGA_TASK_LOCK:
            for path in rows:
                name = os.path.basename(path)
                m = re.fullmatch('task_([A-Za-z0-9_-]+)\\.json', name)
                if not m:
                    continue
                state = next((s for s in ('pending', 'running', 'done', 'failed') if f'/{s}/' in path.replace('\\', '/')), '')
                if not state:
                    continue
                key = m.group(1)
                old = _mega_task_registry.get(key)
                if old is None or rank[state] >= rank.get(str(old.get('state') or ''), 0):
                    _mega_task_registry[key] = {'state': state, 'path': path, 'loaded_at': now_local().isoformat(timespec='seconds')}
            _mega_task_registry_loaded_at = now_local().isoformat(timespec='seconds')
        return mega_task_registry_stats()
    except Exception as exc:
        _mega_task_last_error = str(exc)[:500]
        try:
            log_error(f'mega_task_refresh_registry shard v240: {exc}')
        except Exception:
            pass
        return mega_task_registry_stats()

def _canon_mega_task_prune_done_async__002():

    def worker():
        try:
            rows = []
            try:
                rows.extend(_mega_find_remote_files(mega_task_remote_root(), 'task_*.json'))
            except Exception:
                pass
            if MEGA_SHARDED_STORAGE_V240:
                try:
                    rows.extend(_mega_find_remote_files(MEGA_SHARD_CHATS_ROOT_V240, 'task_*.json'))
                except Exception:
                    pass
            groups = defaultdict(list)
            for p in rows:
                if '/done/' in p.replace('\\', '/'):
                    groups[p.rsplit('/', 1)[0]].append(p)
            for _parent, group in groups.items():
                for remote in sorted(group, reverse=True)[MEGA_TASK_DONE_KEEP:]:
                    try:
                        _mega_run('mega-rm', [remote], check=False, timeout=30)
                    except Exception:
                        pass
        except Exception as exc:
            try:
                log_error(f'_mega_task_prune_done_async v240: {exc}')
            except Exception:
                pass
    threading.Thread(target=worker, daemon=True).start()
try:
    runtime_event('mega_sharded_parallel_v240', f"enabled={int(MEGA_SHARDED_STORAGE_V240)}; global={MEGA_PARALLEL_MAX_V240}; lanes={json.dumps(_V240_LANE_LIMITS, separators=(',', ':'))}", 'INFO')
except Exception:
    pass

# --- ИСТОЧНИК: 15_operation_safety.py ---
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
