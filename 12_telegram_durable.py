# v262
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
# v262
