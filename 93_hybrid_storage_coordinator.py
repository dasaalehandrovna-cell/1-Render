# v263
"""v263 hybrid storage coordinator.

Compatibility layer over the mature Telegram durable + two-Render/MEGA code.
It adds one policy/control plane without deleting the historical per-process
switches.  Existing switches remain subordinate process gates.
"""
from concurrent.futures import ThreadPoolExecutor

HYBRID_STORAGE_CONTROL_KEY_V263 = 'hybrid_storage_control_v263'
HYBRID_STORAGE_PENDING_KEY_V263 = 'hybrid_storage_mirror_pending_v263'
HYBRID_STORAGE_SCHEMA_V263 = 1
HYBRID_STORAGE_POLICY_ENV_V263 = 'STORAGE_POLICY_BOOT_MODE'
HYBRID_STORAGE_MODES_V263 = {'auto', 'telegram_first', 'mega_first', 'newest_verified', 'render_only'}
HYBRID_STORAGE_DEFAULT_MODE_V263 = 'auto'
_HYBRID_STORAGE_LOCK_V263 = threading.RLock()
_HYBRID_STORAGE_RUNTIME_V263 = {
    'boot_source': '', 'last_error': '', 'last_sync_at': '', 'last_sync': {},
    'split_brain': {}, 'winner': {}, 'telegram': {}, 'mega': {}, 'heal_pending': False,
}
_HYBRID_CONTROL_WRITE_ACTIVE_V263 = False


def _hybrid_mode_norm_v263(value) -> str:
    raw = str(value or '').strip().casefold().replace('-', '_').replace(' ', '_')
    aliases = {
        'auto': 'auto', 'telegram': 'telegram_first', 'telegram_first': 'telegram_first',
        'tg_first': 'telegram_first', 'mega': 'mega_first', 'mega_first': 'mega_first',
        'newest': 'newest_verified', 'newest_verified': 'newest_verified', 'freshest': 'newest_verified',
        'render': 'render_only', 'render_only': 'render_only', 'local': 'render_only',
    }
    return aliases.get(raw, HYBRID_STORAGE_DEFAULT_MODE_V263)


def _hybrid_policy_fields_v263(mode: str) -> tuple[str, str, bool]:
    mode = _hybrid_mode_norm_v263(mode)
    if mode in {'auto', 'telegram_first'}:
        return 'telegram', 'mega', True
    if mode == 'mega_first':
        return 'mega', 'telegram', True
    if mode == 'newest_verified':
        return 'newest_verified', 'other_verified', True
    return 'render', 'none', False


def _hybrid_checksum_payload_v263(control: dict) -> dict:
    row = {k: v for k, v in dict(control or {}).items() if k != 'checksum'}
    return row


def _hybrid_checksum_v263(control: dict) -> str:
    raw = json.dumps(_hybrid_checksum_payload_v263(control), ensure_ascii=False, sort_keys=True, separators=(',', ':'), default=str).encode('utf-8')
    return hashlib.sha256(raw).hexdigest()


def _hybrid_control_build_v263(mode: str, epoch: int, changed_by=None, changed_at: str='') -> dict:
    mode = _hybrid_mode_norm_v263(mode)
    primary, secondary, fallback = _hybrid_policy_fields_v263(mode)
    row = {
        'schema_version': HYBRID_STORAGE_SCHEMA_V263,
        'epoch': max(0, int(epoch or 0)),
        'mode': mode,
        'primary': primary,
        'secondary': secondary,
        'allow_fallback': bool(fallback),
        'changed_at': str(changed_at or now_local().isoformat(timespec='microseconds')),
        'changed_by': int(changed_by or 0),
        'bot_version': str(globals().get('VERSION') or 'выс-263'),
    }
    row['checksum'] = _hybrid_checksum_v263(row)
    return row


def _hybrid_control_valid_v263(control) -> bool:
    if not isinstance(control, dict):
        return False
    try:
        if int(control.get('schema_version') or 0) != HYBRID_STORAGE_SCHEMA_V263:
            return False
        raw_mode = str(control.get('mode') or '').strip().lower().replace('-', '_').replace(' ', '_')
        if raw_mode not in HYBRID_STORAGE_MODES_V263:
            return False
        if int(control.get('epoch') or 0) < 0:
            return False
        checksum = str(control.get('checksum') or '')
        return bool(checksum and secrets.compare_digest(checksum, _hybrid_checksum_v263(control)))
    except Exception:
        return False


def _hybrid_local_control_v263() -> dict:
    try:
        row = dict(_tg_v234_root_settings().get(HYBRID_STORAGE_CONTROL_KEY_V263) or {})
        if _hybrid_control_valid_v263(row):
            return row
    except Exception:
        pass
    # During BOOT, global `data` is intentionally still empty. Read the SQLite root
    # directly without forcing load_data() or mutating canonical state.
    try:
        root = SQLITE.load_root() or {}
        gs = root.get('_global_settings') if isinstance(root.get('_global_settings'), dict) else {}
        row = dict((gs or {}).get(HYBRID_STORAGE_CONTROL_KEY_V263) or {})
        if _hybrid_control_valid_v263(row):
            return row
    except Exception:
        pass
    return _hybrid_control_build_v263(HYBRID_STORAGE_DEFAULT_MODE_V263, 0, OWNER_ID)


def _hybrid_save_local_control_v263(control: dict, reason: str='control') -> bool:
    if not _hybrid_control_valid_v263(control):
        return False
    try:
        # BOOT runs before load_data(). Merge only the control field into the persisted
        # root so a remote control read can never replace the database with an empty dict.
        if not (isinstance(data, dict) and 'chats' in data):
            persisted = SQLITE.load_root() or {}
            if not isinstance(persisted, dict): persisted = {}
            gs = persisted.setdefault('_global_settings', {})
            if not isinstance(gs, dict): gs = {}; persisted['_global_settings'] = gs
            gs[HYBRID_STORAGE_CONTROL_KEY_V263] = dict(control)
            SQLITE.save_root(persisted)
        else:
            root = _tg_v234_root_settings(); root[HYBRID_STORAGE_CONTROL_KEY_V263] = dict(control)
            try: save_data(data, root_only=True)
            except TypeError: save_data(data)
        SQLITE.set_meta('hybrid_storage_v263', 'control', control)
        return True
    except Exception:
        return False


def hybrid_storage_policy_env_v263() -> str:
    raw = str(os.getenv(HYBRID_STORAGE_POLICY_ENV_V263, '') or '').strip()
    return _hybrid_mode_norm_v263(raw) if raw else ''


def hybrid_storage_control_v263() -> dict:
    env_mode = hybrid_storage_policy_env_v263()
    local = _hybrid_local_control_v263()
    if env_mode:
        forced = _hybrid_control_build_v263(env_mode, int(local.get('epoch') or 0), 0, str(local.get('changed_at') or ''))
        forced['hard_override'] = HYBRID_STORAGE_POLICY_ENV_V263
        return forced
    return local


def _hybrid_gate_v263(category: str, source: str) -> bool:
    gate = globals().get('external_io_allowed_v263')
    if callable(gate):
        try: return bool(gate(category, source))
        except Exception: return False
    return True


def _hybrid_telegram_control_read_v263() -> dict:
    if not telegram_durable_available_v237_1() or not _hybrid_gate_v263('mega_backup', 'hybrid_control:telegram_read'):
        return {}
    try:
        head, _meta = _tg_durable_load_remote_head_v234()
        slot = dict(((head or {}).get(TG_STABLE_SLOT_KEY_V236) or {}).get('durable:storage_control') or {})
        if slot.get('file_id'):
            raw = _tg_durable_download_ref_v234(slot)
            row = json.loads(bytes(raw).decode('utf-8'))
            if _hybrid_control_valid_v263(row):
                return row
        controls = (head or {}).get('controls') or {}
        row = controls.get(HYBRID_STORAGE_CONTROL_KEY_V263) or {}
        if _hybrid_control_valid_v263(row):
            return dict(row)
    except Exception as exc:
        _HYBRID_STORAGE_RUNTIME_V263['last_error'] = f'telegram control read: {exc}'[:300]
    return {}


def _hybrid_telegram_control_write_v263(control: dict) -> bool:
    global _HYBRID_CONTROL_WRITE_ACTIVE_V263
    if not _hybrid_control_valid_v263(control) or not telegram_durable_available_v237_1():
        return False
    if not _hybrid_gate_v263('mega_backup', 'hybrid_control:telegram_write'):
        return False
    try:
        raw = (json.dumps(control, ensure_ascii=False, sort_keys=True, separators=(',', ':')) + '\n').encode('utf-8')
        _HYBRID_CONTROL_WRITE_ACTIVE_V263 = True
        ref = telegram_stable_document_upsert_v236(raw, 'STORAGE_CONTROL.json', f"💾 STORAGE CONTROL · epoch {int(control.get('epoch') or 0)} · {control.get('mode')}", slot_key='durable:storage_control', persist_head=True, reason='hybrid_storage_control_v263')
        if not ref:
            return False
        try:
            head = telegram_durable_bootstrap_v234(False)
            head.setdefault('controls', {})[HYBRID_STORAGE_CONTROL_KEY_V263] = dict(control)
            _tg_durable_persist_head_v234('hybrid_storage_control_v263')
        except Exception:
            pass
        return True
    except Exception as exc:
        _HYBRID_STORAGE_RUNTIME_V263['last_error'] = f'telegram control write: {exc}'[:300]
        return False
    finally:
        _HYBRID_CONTROL_WRITE_ACTIVE_V263 = False


def _hybrid_worker_base_v263() -> str:
    raw = str(os.getenv('PEER_SERVICE_URL', os.getenv('WORKER_SERVICE_URL', '')) or '').strip().rstrip('/')
    if raw and not raw.startswith(('http://', 'https://')):
        raw = 'https://' + raw
    return raw


def _hybrid_worker_headers_v263() -> dict:
    secret = str(os.getenv('PEER_SHARED_SECRET', '') or '').strip()
    return {'X-Peer-Secret': secret, 'User-Agent': 'vys-263-hybrid-storage'} if secret else {}


def _hybrid_worker_control_read_v263() -> dict:
    base = _hybrid_worker_base_v263(); headers = _hybrid_worker_headers_v263()
    if not base or not headers or not _hybrid_gate_v263('peer_http', 'hybrid_control:mega_read'):
        return {}
    try:
        r = requests.get(base + '/internal/storage/control', headers=headers, timeout=6)
        if int(r.status_code) != 200:
            return {}
        row = (r.json() or {}).get('control') or {}
        return dict(row) if _hybrid_control_valid_v263(row) else {}
    except Exception as exc:
        _HYBRID_STORAGE_RUNTIME_V263['last_error'] = f'mega control read: {exc}'[:300]
        return {}


def _hybrid_worker_control_write_v263(control: dict) -> bool:
    base = _hybrid_worker_base_v263(); headers = _hybrid_worker_headers_v263()
    if not base or not headers or not _hybrid_control_valid_v263(control) or not _hybrid_gate_v263('peer_http', 'hybrid_control:mega_write'):
        return False
    try:
        r = requests.post(base + '/internal/storage/control', json={'control': control}, headers=headers, timeout=10)
        body = r.json() if getattr(r, 'content', b'') else {}
        return int(r.status_code) in {200, 202} and bool((body or {}).get('accepted'))
    except Exception as exc:
        _HYBRID_STORAGE_RUNTIME_V263['last_error'] = f'mega control write: {exc}'[:300]
        return False


def _hybrid_worker_evidence_v263() -> dict:
    base = _hybrid_worker_base_v263(); headers = _hybrid_worker_headers_v263()
    if not base or not headers or not _hybrid_gate_v263('peer_http', 'hybrid_evidence:mega'):
        return {}
    try:
        r = requests.get(base + '/internal/storage/evidence', headers=headers, timeout=8)
        return dict((r.json() or {}).get('evidence') or {}) if int(r.status_code) == 200 else {}
    except Exception:
        return {}


def _hybrid_telegram_evidence_v263() -> dict:
    if not telegram_durable_available_v237_1() or not _hybrid_gate_v263('mega_backup', 'hybrid_evidence:telegram'):
        return {}
    try:
        head, _meta = _tg_durable_load_remote_head_v234()
        meta = dict((head or {}).get('hybrid_generation_v263') or {})
        snap = (head or {}).get('snapshot') or {}
        return {
            'backend': 'telegram', 'available': bool(head), 'generation': int((head or {}).get('generation') or 0),
            'user_state_seq': int(meta.get('user_state_seq') or 0), 'lineage': str(meta.get('lineage') or ''),
            'db_sha256': str(meta.get('db_sha256') or ''), 'snapshot_sha256': str((snap or {}).get('sha256') or ''),
            'created_at': str((snap or {}).get('created_at') or (head or {}).get('updated_at') or ''),
        }
    except Exception:
        return {}


def _hybrid_select_control_v263(tg: dict, mega: dict, local: dict) -> tuple[dict, str, dict]:
    valid = [(name, row) for name, row in [('telegram', tg), ('mega', mega), ('local', local)] if _hybrid_control_valid_v263(row)]
    if not valid:
        return _hybrid_control_build_v263(HYBRID_STORAGE_DEFAULT_MODE_V263, 0, OWNER_ID), 'default', {}
    remote = [(n, r) for n, r in valid if n != 'local']
    if remote:
        max_epoch = max(int(r.get('epoch') or 0) for _, r in remote)
        top = [(n, r) for n, r in remote if int(r.get('epoch') or 0) == max_epoch]
        checks = {str(r.get('checksum') or '') for _, r in top}
        if len(top) > 1 and len(checks) > 1:
            split = {'at': now_local().isoformat(timespec='seconds'), 'epoch': max_epoch, 'telegram': tg, 'mega': mega, 'reason': 'same_epoch_different_checksum'}
            # Last locally confirmed control wins while the conflict is unresolved.
            if _hybrid_control_valid_v263(local) and int(local.get('epoch') or 0) == max_epoch and str(local.get('checksum') or '') in checks:
                return dict(local), 'local:last_confirmed_split_brain', split
            preferred = 'telegram' if _hybrid_mode_norm_v263(local.get('mode')) in {'auto','telegram_first','newest_verified'} else 'mega'
            for n, r in top:
                if n == preferred:
                    return dict(r), n + ':split_brain_primary', split
            return dict(top[0][1]), top[0][0] + ':split_brain', split
        winner_name, winner = max(top, key=lambda nr: (1 if nr[0] == 'telegram' else 0))
        # A newer same-instance local control is allowed only as a pending mirror state.
        if _hybrid_control_valid_v263(local) and int(local.get('epoch') or 0) > int(winner.get('epoch') or 0):
            return dict(local), 'local:pending_remote_mirror', {}
        return dict(winner), winner_name, {}
    return dict(local), 'local', {}


def hybrid_storage_refresh_control_v263() -> dict:
    if external_io_profile_v263() in {'local_lab', 'safe_isolation'}:
        row = _hybrid_local_control_v263()
        _HYBRID_STORAGE_RUNTIME_V263.update({'boot_source': 'isolation:local', 'winner': dict(row), 'telegram': {}, 'mega': {}, 'split_brain': {}})
        return row
    local = _hybrid_local_control_v263()
    with ThreadPoolExecutor(max_workers=2, thread_name_prefix='v263-storage-control') as ex:
        ft = ex.submit(_hybrid_telegram_control_read_v263)
        fm = ex.submit(_hybrid_worker_control_read_v263)
        try: tg = ft.result(timeout=12)
        except Exception: tg = {}
        try: mega = fm.result(timeout=12)
        except Exception: mega = {}
    winner, source, split = _hybrid_select_control_v263(tg, mega, local)
    _hybrid_save_local_control_v263(winner, 'bootstrap')
    _HYBRID_STORAGE_RUNTIME_V263.update({'boot_source': source, 'winner': dict(winner), 'telegram': dict(tg or {}), 'mega': dict(mega or {}), 'split_brain': dict(split or {}), 'heal_pending': bool(split) or str((tg or {}).get('checksum') or '') != str(winner.get('checksum') or '') or str((mega or {}).get('checksum') or '') != str(winner.get('checksum') or '')})
    if split:
        try: bot_journal('STORAGE_SPLIT_BRAIN', int(OWNER_ID or 0) or None, f"epoch={split.get('epoch')}; same epoch different checksum", 'ERROR')
        except Exception: pass
    return winner


def _hybrid_primary_legacy_profile_v263(control: dict, *, bootstrap: bool=False) -> tuple[str, str]:
    mode = _hybrid_mode_norm_v263((control or {}).get('mode'))
    tg_ok = bool(telegram_durable_available_v237_1())
    mega_front_ok = bool(globals().get('MEGA_ENABLED') and globals().get('MEGA_EMAIL') and globals().get('MEGA_PASSWORD'))
    if mode == 'render_only':
        return STORAGE_PROFILE_LOCAL_V237_1, 'local'
    if mode in {'auto', 'telegram_first'}:
        return (STORAGE_PROFILE_TELEGRAM_V237_1, 'telegram') if tg_ok else (STORAGE_PROFILE_LOCAL_V237_1, 'local')
    if mode == 'mega_first':
        # In the split deployment Render #2 restores Redis/MEGA into the front DB before bot.py.
        return (STORAGE_PROFILE_MEGA_V237_1, 'mega') if mega_front_ok else (STORAGE_PROFILE_LOCAL_V237_1, 'local')
    # newest_verified: never choose by timestamp. Only compare evidence when lineage agrees.
    tg_ev = _hybrid_telegram_evidence_v263() if bootstrap else {}
    mg_ev = _hybrid_worker_evidence_v263() if bootstrap else {}
    tlin, mlin = str(tg_ev.get('lineage') or ''), str(mg_ev.get('lineage') or '')
    if tg_ev.get('available') and mg_ev.get('available') and tlin and mlin and tlin != mlin:
        _HYBRID_STORAGE_RUNTIME_V263['split_brain'] = {'at': now_local().isoformat(timespec='seconds'), 'reason': 'generation_lineage_mismatch', 'telegram_evidence': tg_ev, 'mega_evidence': mg_ev}
        try: bot_journal('STORAGE_SPLIT_BRAIN', int(OWNER_ID or 0) or None, f'lineage telegram={tlin}; mega={mlin}', 'ERROR')
        except Exception: pass
        return (STORAGE_PROFILE_TELEGRAM_V237_1, 'telegram') if tg_ok else (STORAGE_PROFILE_LOCAL_V237_1, 'local')
    if tg_ev.get('available') and (not mg_ev.get('available') or (tlin and mlin and tlin == mlin and int(tg_ev.get('user_state_seq') or tg_ev.get('generation') or 0) >= int(mg_ev.get('user_state_seq') or mg_ev.get('generation') or 0))):
        return (STORAGE_PROFILE_TELEGRAM_V237_1, 'telegram') if tg_ok else (STORAGE_PROFILE_LOCAL_V237_1, 'local')
    if mg_ev.get('available'):
        return (STORAGE_PROFILE_MEGA_V237_1, 'mega') if mega_front_ok else (STORAGE_PROFILE_LOCAL_V237_1, 'local')
    return (STORAGE_PROFILE_TELEGRAM_V237_1, 'telegram') if tg_ok else (STORAGE_PROFILE_LOCAL_V237_1, 'local')


def _hybrid_apply_local_policy_v263(control: dict, *, bootstrap: bool=False) -> tuple[str, str]:
    profile, restore_backend = _hybrid_primary_legacy_profile_v263(control, bootstrap=bootstrap)
    if bootstrap:
        # The chosen profile is committed only after load_data(), matching the old boot
        # barrier and preventing pre-restore writes into the canonical SQLite root.
        return profile, restore_backend
    root = _tg_v234_root_settings()
    root[STORAGE_PROFILE_KEY_V237_1] = profile
    root['render_telegram_only_v233'] = profile == STORAGE_PROFILE_LOCAL_V237_1
    root['mega_contour_enabled_v234'] = bool(_hybrid_mode_norm_v263(control.get('mode')) in {'auto','telegram_first','mega_first','newest_verified'} and globals().get('MEGA_ENABLED') and globals().get('MEGA_EMAIL') and globals().get('MEGA_PASSWORD'))
    root['telegram_durable_enabled_v237_1'] = bool(_hybrid_mode_norm_v263(control.get('mode')) != 'render_only' and telegram_durable_available_v237_1())
    root['secret_storage_backend_v234'] = 'mega' if _hybrid_mode_norm_v263(control.get('mode')) == 'mega_first' and globals().get('MEGA_ENABLED') else 'telegram'
    try: save_data(data, root_only=True)
    except Exception: pass
    return profile, restore_backend


_HYBRID_BOOTSTRAP_PREV_V263 = storage_profile_bootstrap_v237_1
_HYBRID_APPLY_BOOT_PREV_V263 = storage_profile_apply_boot_hint_v237_1
_HYBRID_TG_PRIMARY_PREV_V263 = telegram_durable_primary_v234
_HYBRID_MEGA_CONTOUR_PREV_V263 = mega_contour_enabled_v234
_HYBRID_TG_UPLOAD_PREV_V263 = telegram_upload_sqlite_snapshot_v234
_HYBRID_RUNTIME_READY_PREV_V263 = runtime_mark_ready


def storage_profile_bootstrap_v237_1() -> str:
    global _STORAGE_PROFILE_BOOT_HINT_V237_1, _STORAGE_PROFILE_BOOT_SOURCE_V238, _STORAGE_PROFILE_RESTORE_BACKEND_V246
    if external_io_profile_v263() in {'local_lab', 'safe_isolation'}:
        _STORAGE_PROFILE_BOOT_HINT_V237_1 = STORAGE_PROFILE_LOCAL_V237_1
        _STORAGE_PROFILE_BOOT_SOURCE_V238 = 'v263:external_io_isolation'
        _STORAGE_PROFILE_RESTORE_BACKEND_V246 = 'local'
        return STORAGE_PROFILE_LOCAL_V237_1
    control = hybrid_storage_refresh_control_v263()
    profile, backend = _hybrid_apply_local_policy_v263(control, bootstrap=True)
    _STORAGE_PROFILE_BOOT_HINT_V237_1 = profile
    _STORAGE_PROFILE_BOOT_SOURCE_V238 = 'v263:hybrid:' + str(_HYBRID_STORAGE_RUNTIME_V263.get('boot_source') or 'local')
    _STORAGE_PROFILE_RESTORE_BACKEND_V246 = backend
    return profile


def storage_profile_apply_boot_hint_v237_1() -> str:
    control = hybrid_storage_control_v263()
    profile, _backend = _hybrid_apply_local_policy_v263(control, bootstrap=False)
    return profile


def telegram_durable_primary_v234() -> bool:
    if _HYBRID_CONTROL_WRITE_ACTIVE_V263:
        return bool(telegram_durable_available_v237_1() and _hybrid_gate_v263('mega_backup', 'hybrid_control_plane:telegram'))
    mode = _hybrid_mode_norm_v263(hybrid_storage_control_v263().get('mode'))
    if mode == 'render_only':
        return False
    if not _hybrid_gate_v263('mega_backup', 'hybrid:telegram_storage'):
        return False
    return bool(telegram_durable_available_v237_1())


def mega_contour_enabled_v234() -> bool:
    mode = _hybrid_mode_norm_v263(hybrid_storage_control_v263().get('mode'))
    if mode == 'render_only' or not _hybrid_gate_v263('mega_backup', 'hybrid:mega_storage'):
        return False
    # Front may deliberately have no MEGA credentials; Render #2 is then the archive owner.
    return bool(globals().get('MEGA_ENABLED') and globals().get('MEGA_EMAIL') and globals().get('MEGA_PASSWORD'))


def _hybrid_local_generation_meta_v263() -> dict:
    try:
        path = str(getattr(SQLITE, 'path', '') or '')
        db_sha = ''
        if path and os.path.exists(path):
            h=hashlib.sha256()
            with open(path,'rb') as fh:
                for chunk in iter(lambda: fh.read(1024*1024), b''):
                    h.update(chunk)
            db_sha=h.hexdigest()
    except Exception: db_sha = ''
    try: lineage = str(_v239_storage_lineage(create=True) or '')
    except Exception: lineage = ''
    try:
        shadow = SQLITE.get_meta('user_state_shadow_v265', 'latest', {}) or {}
        seq = int((shadow or {}).get('seq') or 0) if isinstance(shadow, dict) else 0
    except Exception: seq = 0
    try:
        cfg = int((data.get('_global_settings') or {}).get(CONFIG_GUARD_GENERATION_KEY_V234) or SQLITE.get_meta(CONFIG_GUARD_META_KIND_V234, 'generation', 0) or 0)
    except Exception: cfg = 0
    return {'db_sha256': db_sha, 'lineage': lineage, 'user_state_seq': seq, 'config_generation': cfg, 'created_at': now_local().isoformat(timespec='microseconds'), 'bot_version': str(globals().get('VERSION') or '')}


def telegram_upload_sqlite_snapshot_v234(force: bool=False) -> bool:
    ok = bool(_HYBRID_TG_UPLOAD_PREV_V263(force=force))
    if not ok:
        return False
    try:
        head = telegram_durable_bootstrap_v234(False)
        head['hybrid_generation_v263'] = _hybrid_local_generation_meta_v263()
        _tg_durable_persist_head_v234('hybrid_generation_v263')
    except Exception as exc:
        try: log_error(f'hybrid generation metadata v263: {exc}')
        except Exception: pass
    return True


def _hybrid_write_target_v263(target: str, control: dict) -> bool:
    return _hybrid_telegram_control_write_v263(control) if target == 'telegram' else _hybrid_worker_control_write_v263(control) if target == 'mega' else True


def _hybrid_primary_control_target_v263(control: dict) -> str:
    mode = _hybrid_mode_norm_v263(control.get('mode'))
    if mode in {'auto','telegram_first'}: return 'telegram'
    if mode == 'mega_first': return 'mega'
    if mode == 'newest_verified': return 'telegram' if telegram_durable_available_v237_1() else 'mega'
    # render_only still needs one remote beacon so the choice survives an empty-disk deploy.
    return 'telegram' if telegram_durable_available_v237_1() else 'mega'


def hybrid_storage_set_mode_v263(mode: str, changed_by=None) -> dict:
    mode = _hybrid_mode_norm_v263(mode)
    forced = hybrid_storage_policy_env_v263()
    current = _hybrid_local_control_v263()
    if forced and mode != forced:
        _HYBRID_STORAGE_RUNTIME_V263['last_error'] = f'HARD OVERRIDE {HYBRID_STORAGE_POLICY_ENV_V263}={forced}'
        return current
    if external_io_profile_v263() in {'local_lab','safe_isolation'} and mode != 'render_only':
        _HYBRID_STORAGE_RUNTIME_V263['last_error'] = 'Storage policy change requiring remote confirmation is blocked by external I/O isolation.'
        return current
    new = _hybrid_control_build_v263(mode, int(current.get('epoch') or 0) + 1, changed_by or OWNER_ID)
    primary = _hybrid_primary_control_target_v263(new)
    primary_ok = _hybrid_write_target_v263(primary, new)
    if not primary_ok and bool(new.get('allow_fallback')):
        alternate = 'mega' if primary == 'telegram' else 'telegram'
        primary_ok = _hybrid_write_target_v263(alternate, new)
        if primary_ok: primary = alternate
    if not primary_ok:
        _HYBRID_STORAGE_RUNTIME_V263['last_error'] = f'control epoch {new["epoch"]} not confirmed by Telegram/MEGA'
        return current
    _hybrid_save_local_control_v263(new, 'mode_switch')
    _hybrid_apply_local_policy_v263(new, bootstrap=False)
    _HYBRID_STORAGE_RUNTIME_V263.update({'winner': dict(new), 'boot_source': f'owner:{primary}', 'heal_pending': True, 'last_error': ''})
    try: bot_journal('STORAGE_CONTROL_CHANGED_V263', int(changed_by or OWNER_ID or 0) or None, f"epoch={new['epoch']}; mode={mode}; confirmed={primary}")
    except Exception: pass
    hybrid_storage_schedule_heal_v263(0.05)
    return new


def hybrid_storage_heal_now_v263(control: dict | None=None) -> dict:
    control = dict(control or hybrid_storage_control_v263())
    if not _hybrid_control_valid_v263(control):
        return {'ok': False, 'telegram': False, 'mega': False, 'error': 'invalid control'}
    if external_io_profile_v263() in {'local_lab','safe_isolation'}:
        return {'ok': False, 'telegram': False, 'mega': False, 'error': 'external I/O isolation'}
    tg_ok = _hybrid_telegram_control_write_v263(control) if telegram_durable_available_v237_1() else False
    mg_ok = _hybrid_worker_control_write_v263(control)
    result = {'ok': bool(tg_ok or mg_ok), 'telegram': bool(tg_ok), 'mega': bool(mg_ok), 'epoch': int(control.get('epoch') or 0), 'at': now_local().isoformat(timespec='seconds')}
    _HYBRID_STORAGE_RUNTIME_V263.update({'last_sync_at': result['at'], 'last_sync': dict(result), 'heal_pending': not bool(tg_ok and mg_ok)})
    try: _tg_v234_root_settings()[HYBRID_STORAGE_PENDING_KEY_V263] = not bool(tg_ok and mg_ok)
    except Exception: pass
    return result


def hybrid_storage_schedule_heal_v263(delay: float=0.2) -> bool:
    if external_io_profile_v263() in {'local_lab','safe_isolation'}:
        return False
    def _job():
        hybrid_storage_heal_now_v263()
    try:
        sched = globals().get('DELAYED_SCHEDULER')
        if sched is not None:
            sched.schedule('hybrid-storage-heal-v263', max(0.05,float(delay)), _job); return True
    except Exception: pass
    try:
        pool = globals().get('MAINTENANCE_TASK_POOL') or globals().get('GENERAL_TASK_POOL')
        if pool is not None:
            return bool(pool.submit_unique('hybrid-storage-heal-v263', _job) if hasattr(pool,'submit_unique') else pool.submit('hybrid-storage-heal-v263', _job))
    except Exception: pass
    return False


def runtime_mark_ready(detail: str=''):
    result = _HYBRID_RUNTIME_READY_PREV_V263(detail)
    hybrid_storage_schedule_heal_v263(1.0)
    return result


def hybrid_storage_status_v263(refresh_evidence: bool=False) -> dict:
    control = hybrid_storage_control_v263()
    runtime = dict(_HYBRID_STORAGE_RUNTIME_V263)
    out = {'control': control, 'mode': _hybrid_mode_norm_v263(control.get('mode')), 'boot_source': runtime.get('boot_source') or '', 'split_brain': dict(runtime.get('split_brain') or {}), 'heal_pending': bool(runtime.get('heal_pending')), 'last_sync': dict(runtime.get('last_sync') or {}), 'last_error': str(runtime.get('last_error') or ''), 'telegram_control': dict(runtime.get('telegram') or {}), 'mega_control': dict(runtime.get('mega') or {}), 'env_override': hybrid_storage_policy_env_v263()}
    if refresh_evidence and external_io_profile_v263() == 'normal':
        with ThreadPoolExecutor(max_workers=2, thread_name_prefix='v263-storage-evidence') as ex:
            a=ex.submit(_hybrid_telegram_evidence_v263); b=ex.submit(_hybrid_worker_evidence_v263)
            try: out['telegram_evidence']=a.result(timeout=12)
            except Exception: out['telegram_evidence']={}
            try: out['mega_evidence']=b.result(timeout=12)
            except Exception: out['mega_evidence']={}
    return out


def hybrid_storage_mode_label_v263(mode: str) -> str:
    return {'auto':'✅ AUTO · Telegram → MEGA','telegram_first':'📡 Telegram первым','mega_first':'☁️ MEGA первым','newest_verified':'⚖️ Самое свежее из двух','render_only':'🏠 Только Render'}.get(_hybrid_mode_norm_v263(mode), str(mode))


def hybrid_storage_text_v263() -> str:
    st=hybrid_storage_status_v263(False); c=st['control']; mode=st['mode']; split=st.get('split_brain') or {}; sync=st.get('last_sync') or {}
    lines=['💾 ХРАНИЛИЩЕ И ВОССТАНОВЛЕНИЕ · '+str(globals().get('VERSION') or 'выс-263'),'',f'Политика: {hybrid_storage_mode_label_v263(mode)}',f"Control epoch: {int(c.get('epoch') or 0)}",f"Primary: {c.get('primary')} · Secondary: {c.get('secondary')} · fallback={bool(c.get('allow_fallback'))}",f"Boot source: {st.get('boot_source') or 'local/default'}"]
    if st.get('env_override'): lines.append(f"ENV HARD OVERRIDE: {HYBRID_STORAGE_POLICY_ENV_V263}={st.get('env_override')}")
    lines += ['',f"Telegram control: {('✅' if _hybrid_control_valid_v263(st.get('telegram_control')) else '⬜')} epoch {int((st.get('telegram_control') or {}).get('epoch') or 0)}",f"MEGA control: {('✅' if _hybrid_control_valid_v263(st.get('mega_control')) else '⬜')} epoch {int((st.get('mega_control') or {}).get('epoch') or 0)}",f"Mirror: {('🕐 pending' if st.get('heal_pending') else '✅ synced/idle')}"]
    if sync: lines.append(f"Последняя sync: TG={bool(sync.get('telegram'))} · MEGA={bool(sync.get('mega'))} · {sync.get('at') or '—'}")
    if split: lines += ['', '🚨 STORAGE_SPLIT_BRAIN', f"Причина: {split.get('reason') or 'control conflict'}", 'Автоматического смешивания/overwrite нет. До явного решения используется последний подтверждённый primary.']
    if st.get('last_error'): lines += ['', 'Последняя ошибка: '+str(st.get('last_error'))[:300]]
    lines += ['', 'HOT: Telegram durable stable slots. ARCHIVE: MEGA через Heavy Render. Secondary догоняется после READY; обычная пользовательская операция не ждёт full secondary snapshot.']
    return '\n'.join(lines)[:3900]


def hybrid_storage_keyboard_v263():
    mode=_hybrid_mode_norm_v263(hybrid_storage_control_v263().get('mode')); kb=types.InlineKeyboardMarkup()
    for key,label in [('auto','AUTO · Telegram → MEGA'),('telegram_first','Telegram первым'),('mega_first','MEGA первым'),('newest_verified','Самое свежее из двух'),('render_only','Только Render')]:
        kb.row(IB(('✅ ' if mode==key else '⬜ ')+label, callback_data=f'v263:hybrid:mode:{key}'))
    kb.row(IB('🔄 Синхронизировать сейчас', callback_data='v263:hybrid:sync'), IB('🩺 Проверить оба', callback_data='v263:hybrid:check'))
    kb.row(IB('📊 Состояние хранилищ', callback_data='v263:hybrid:open'))
    kb.row(IB('⬅️ Назад в INFO', callback_data='v176:back_info'), IB('✖️ Закрыть', callback_data='info_close'))
    return kb


# Final INFO wrapper: 89_callback_final.py intentionally rebinds the historic
# constructor after 85_runtime_control.py, so add both v263 controls here, last.
_HYBRID_INFO_KB_PREV_V263 = build_info_keyboard

def build_info_keyboard(chat_id: int):
    kb=_HYBRID_INFO_KB_PREV_V263(int(chat_id))
    if int(chat_id) != int(OWNER_ID or 0): return kb
    rows=_v177_info_rows(kb)
    wanted={'v263:io:open','v263:hybrid:open'}
    rows=[[b for b in (r or []) if _v177_info_btn_cb(b) not in wanted] for r in rows]; rows=[r for r in rows if r]
    insert=len(rows)
    for i,r in enumerate(rows):
        if any(_v218_info_is_nav(b) for b in (r or [])): insert=i; break
    rows.insert(insert,[IB('💾 Hybrid storage', callback_data='v263:hybrid:open')])
    rows.insert(insert+1,[IB('🧪 Контроль изоляции', callback_data='v263:io:open')])
    return _v177_info_set_rows(kb,rows)


def hybrid_storage_check_text_v263() -> str:
    st=hybrid_storage_status_v263(True); tg=st.get('telegram_evidence') or {}; mg=st.get('mega_evidence') or {}; split=st.get('split_brain') or {}
    lines=[hybrid_storage_text_v263(),'', '🩺 ПРОВЕРКА ОБОИХ ХРАНИЛИЩ',
           f"Telegram: {('✅' if tg.get('available') else '⬜')} gen={int(tg.get('generation') or 0)} seq={int(tg.get('user_state_seq') or 0)} lineage={tg.get('lineage') or '—'}",
           f"MEGA/Heavy: {('✅' if mg.get('available') else '⬜')} gen={int(mg.get('generation') or 0)} seq={int(mg.get('user_state_seq') or 0)} lineage={mg.get('lineage') or '—'}"]
    if tg.get('db_sha256'): lines.append('TG db sha: '+str(tg.get('db_sha256'))[:20]+'…')
    if mg.get('db_sha256'): lines.append('MEGA db sha: '+str(mg.get('db_sha256'))[:20]+'…')
    tlin,mlin=str(tg.get('lineage') or ''),str(mg.get('lineage') or '')
    if tlin and mlin and tlin != mlin:
        lines += ['', '🚨 Ветки расходятся. newest_verified НЕ будет выбирать по времени; silent merge/overwrite запрещён.']
    elif tlin and mlin and tlin == mlin:
        lines += ['', '✅ Lineage совпадает: сравнение свежести допускается по подтверждённой ветке/sequence, а не только по timestamp.']
    if split: lines += ['', '🚨 Активен STORAGE_SPLIT_BRAIN.']
    return '\n'.join(lines)[:3900]

# v263
