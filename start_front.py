# v262
#!/usr/bin/env python3
"""Render #1 launcher: fast Telegram front + worker restore + emergency MEGA restore."""
from __future__ import annotations
import gzip
import json
import os
import runpy
import shutil
import sqlite3
import subprocess
import tempfile
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import requests
from runtime_config import install_internal_runtime_config, CONFIG_VERSION as INTERNAL_CONFIG_VERSION
install_internal_runtime_config("front")
try:
    import redis as _redis
except Exception:
    _redis = None


class _BootHealthHandler(BaseHTTPRequestHandler):
    def _reply(self, status: int, body: bool):
        raw = b'{"ok":true,"role":"front","phase":"restoring"}' if body else b''
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(raw)))
        self.end_headers()
        if raw:
            self.wfile.write(raw)
    def do_GET(self): self._reply(200, True)
    def do_HEAD(self): self._reply(200, False)
    def do_POST(self): self._reply(503, True)
    def log_message(self, fmt, *args): return


def _bool(name: str, default=False):
    return str(os.getenv(name, '1' if default else '0') or '').strip().lower() in {'1','true','yes','on','да'}


def _start_boot_port():
    port = int(os.getenv('PORT', '5000') or '5000')
    server = ThreadingHTTPServer(('0.0.0.0', port), _BootHealthHandler)
    server.daemon_threads = True
    threading.Thread(target=server.serve_forever, name='v262-front-boot-http', daemon=True).start()
    print(f'[SPLIT FRONT] preboot port open on 0.0.0.0:{port}', flush=True)
    return server


def _stop_boot_port(server):
    try: server.shutdown()
    except Exception: pass
    try: server.server_close()
    except Exception: pass


def _db_path():
    return Path(os.getenv('DB_FILE', 'bot_state.sqlite3') or 'bot_state.sqlite3').resolve()


def _db_valid(path: Path):
    if not path.exists() or path.stat().st_size < 4096:
        return False
    try:
        con = sqlite3.connect(str(path))
        try:
            row = con.execute('PRAGMA quick_check').fetchone()
            return bool(row and str(row[0]).lower() == 'ok')
        finally:
            con.close()
    except Exception:
        return False



def _db_revision(path: Path) -> float:
    if not _db_valid(path):
        return 0.0
    try:
        con = sqlite3.connect(str(path))
        try:
            rev = 0.0
            for kind in ('split_state_revision_r18', 'user_state_shadow_v265', 'runtime_continuity_v263'):
                row = con.execute("SELECT v FROM meta WHERE kind=? AND k='latest'", (kind,)).fetchone()
                if row:
                    try:
                        obj = json.loads(row[0]) or {}
                        rev = max(rev, float(obj.get('saved_at') or 0.0))
                    except Exception:
                        pass
            # legacy/fallback monotonic-ish timestamp if continuity metadata predates R4.
            row = con.execute("SELECT v FROM kv WHERE k='root'").fetchone()
            if row:
                try:
                    root = json.loads(row[0]) or {}
                    stamp = str((root.get('_state_meta') or {}).get('last_saved_at') or '')
                    if stamp and rev <= 0.0:
                        from datetime import datetime
                        rev = datetime.fromisoformat(stamp.replace('Z','+00:00')).timestamp()
                except Exception:
                    pass
            return float(rev or 0.0)
        finally:
            con.close()
    except Exception:
        return 0.0

def _install_gzip_db(gz_path: Path, target: Path):
    tmp = target.with_suffix(target.suffix + '.restore.tmp')
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        with gzip.open(gz_path, 'rb') as src, open(tmp, 'wb') as dst:
            shutil.copyfileobj(src, dst, length=1024 * 1024)
        if not _db_valid(tmp):
            return False
        incoming_revision = _db_revision(tmp)
        current_revision = _db_revision(target) if target.exists() else 0.0
        # Never roll back a newer local user state to a delayed worker/MEGA image.
        if _db_valid(target) and current_revision > 0.0 and (incoming_revision <= 0.0 or incoming_revision < current_revision):
            print(f'[SPLIT FRONT] stale restore rejected incoming={incoming_revision} local={current_revision}', flush=True)
            return False
        os.replace(tmp, target)
        for suffix in ('-wal', '-shm'):
            try: Path(str(target) + suffix).unlink(missing_ok=True)
            except Exception: pass
        return True
    finally:
        try: tmp.unlink(missing_ok=True)
        except Exception: pass


def _peer_base():
    raw = str(os.getenv('PEER_PRIVATE_URL', '') or '').strip().rstrip('/')
    private = bool(raw)
    if not raw:
        raw = str(os.getenv('PEER_SERVICE_URL', '') or '').strip().rstrip('/')
    if raw and not raw.startswith(('http://','https://')):
        looks_private = private or raw.endswith('.internal') or '.internal:' in raw or (raw.startswith('render-') and ':' in raw)
        raw = ('http://' if looks_private else 'https://') + raw
    return raw


def _secret():
    return str(os.getenv('PEER_SHARED_SECRET', '') or '').strip()


def _redis_snapshot_revision_r18(client=None):
    """Return shared Redis snapshot revision without replacing anything."""
    if _redis is None:
        return 0.0
    url = str(os.getenv('REDIS_URL', '') or '').strip()
    if not url:
        return 0.0
    key = str(os.getenv('WORKER_REDIS_SNAPSHOT_KEY', 'vys262:bot_state:latest_gz') or 'vys262:bot_state:latest_gz').strip()
    try:
        client = client or _redis.Redis.from_url(url, socket_connect_timeout=1.0, socket_timeout=2.0, health_check_interval=30)
        raw = client.get(key + ':meta')
        if not raw:
            return 0.0
        if isinstance(raw, (bytes, bytearray)):
            raw = raw.decode('utf-8', 'replace')
        meta = json.loads(raw) if isinstance(raw, str) else (raw or {})
        return float((meta or {}).get('revision') or 0.0)
    except Exception:
        return 0.0


def _restore_from_redis_direct_r18(target: Path):
    """Freshness arbiter: use Redis snapshot only when it is newer than current target.

    This is intentionally boot-only.  It closes the race where Worker /tmp is stale
    while the shared Redis durable cache already contains the final old-front state.
    """
    if _redis is None:
        return False, 'redis package unavailable'
    url = str(os.getenv('REDIS_URL', '') or '').strip()
    if not url:
        return False, 'REDIS_URL empty'
    key = str(os.getenv('WORKER_REDIS_SNAPSHOT_KEY', 'vys262:bot_state:latest_gz') or 'vys262:bot_state:latest_gz').strip()
    tmpdir = Path(tempfile.mkdtemp(prefix='r18_redis_restore_'))
    try:
        client = _redis.Redis.from_url(url, socket_connect_timeout=2.0, socket_timeout=5.0, health_check_interval=30)
        remote_rev = _redis_snapshot_revision_r18(client)
        local_rev = _db_revision(target) if _db_valid(target) else 0.0
        if remote_rev <= 0.0 or (_db_valid(target) and remote_rev <= local_rev + 0.000001):
            return False, f'Redis not newer remote={remote_rev} local={local_rev}'
        payload = client.get(key)
        if not payload:
            return False, 'Redis snapshot missing'
        gz = tmpdir / 'latest.sqlite3.gz'
        gz.write_bytes(payload)
        if _install_gzip_db(gz, target):
            return True, f'Redis newer snapshot installed revision={remote_rev}'
        return False, 'Redis snapshot rejected/invalid'
    except Exception as exc:
        return False, f'{type(exc).__name__}: {str(exc)[:180]}'
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


def _restore_from_worker(target: Path):
    base, secret = _peer_base(), _secret()
    if not base or not secret:
        return False, 'worker URL/secret not configured'
    attempts = max(1, min(8, int(os.getenv('SPLIT_BOOT_WORKER_ATTEMPTS', '3') or '3')))
    timeout = max(5.0, min(120.0, float(os.getenv('SPLIT_BOOT_WORKER_TIMEOUT', '12') or '12')))
    detail = 'worker unavailable'
    for attempt in range(1, attempts + 1):
        tmpdir = Path(tempfile.mkdtemp(prefix='v262_worker_restore_'))
        try:
            r = requests.get(base + '/internal/restore/latest', headers={'X-Peer-Secret': secret, 'User-Agent':'vys-262-front-restore'}, timeout=timeout, stream=True)
            if r.status_code == 200:
                gz = tmpdir / 'latest.sqlite3.gz'
                with open(gz, 'wb') as fh:
                    for chunk in r.iter_content(1024 * 1024):
                        if chunk: fh.write(chunk)
                if _install_gzip_db(gz, target):
                    return True, f'worker restore OK attempt={attempt}'
            detail = f'worker HTTP {r.status_code}: {r.text[:180] if not r.ok else "invalid DB"}'
        except Exception as exc:
            detail = f'worker {type(exc).__name__}: {str(exc)[:180]}'
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)
        if attempt < attempts:
            time.sleep(min(2.0 * attempt, 5.0))
    return False, detail



def _worker_cache_revision():
    base, secret = _peer_base(), _secret()
    if not base or not secret:
        return 0.0
    try:
        r = requests.get(base + '/internal/status', headers={'X-Peer-Secret':secret, 'User-Agent':'vys-262-front-handoff'}, timeout=5)
        if r.status_code != 200:
            return 0.0
        body = r.json() or {}
        return float(((body.get('state') or {}).get('cache_revision')) or 0.0)
    except Exception:
        return 0.0


def _preboot_capture_old_front_r18_legacy():
    """Ask HEAVY to capture the still-live old FAST before Render cuts traffic over.

    During a rolling deploy the public FAST URL normally still points at the old
    instance while the new instance is in preboot.  This closes the R17->R18 bridge:
    even if the old process later gets a short SIGTERM grace period, HEAVY has already
    pulled its live SQLite state.  Failure is harmless; normal Worker/Redis restore
    follows immediately.
    """
    base, secret = _peer_base(), _secret()
    if not base or not secret:
        return False, 'worker URL/secret not configured'
    started = time.time()
    try:
        before_rev = _worker_cache_revision()
        body = {'type':'sync_state', 'reason':'preboot_capture_old_front_r18', 'state_token':f'preboot:{int(started*1000)}'}
        r = requests.post(base + '/internal/job', json=body, headers={'X-Peer-Secret':secret, 'User-Agent':'vys-262-front-r18-preboot-capture'}, timeout=2.5)
        if r.status_code not in (200, 202):
            return False, f'worker preboot queue HTTP {r.status_code}: {r.text[:160]}'
        try:
            wait = max(0.0, min(8.0, float(os.getenv('SPLIT_PREBOOT_CAPTURE_WAIT_SEC','4.0') or '4.0')))
        except Exception:
            wait = 4.0
        deadline = time.time() + wait
        last_detail = f'queued HTTP {r.status_code}'
        while time.time() < deadline:
            try:
                st = requests.get(base + '/internal/status', headers={'X-Peer-Secret':secret, 'User-Agent':'vys-262-front-r18-preboot-status'}, timeout=2.0)
                if st.status_code == 200:
                    row = (st.json() or {}).get('state') or {}
                    rev = float(row.get('cache_revision') or 0.0)
                    snap_at = float(row.get('last_snapshot_at') or 0.0)
                    done_at = float(row.get('job_last_done') or 0.0)
                    reason = str(row.get('job_last_reason') or '')
                    err = str(row.get('job_last_error') or '')
                    if snap_at >= started - 0.5 or rev > before_rev + 0.000001:
                        return True, f'old FAST captured cache_revision={rev}'
                    if done_at >= started - 0.5 and 'preboot_capture_old_front_r18' in reason:
                        return (not bool(err)), (f'preboot capture finished revision={rev}' if not err else f'preboot capture failed: {err[:160]}')
                    last_detail = f'waiting worker revision={rev} reason={reason[:60]}'
            except Exception as exc:
                last_detail = f'poll {type(exc).__name__}: {str(exc)[:120]}'
            time.sleep(0.25)
        return False, 'preboot capture wait expired; ' + last_detail
    except Exception as exc:
        return False, f'{type(exc).__name__}: {str(exc)[:180]}'


def _settle_worker_handoff(target: Path):
    """Catch the old front's final SIGTERM snapshot during a rolling deploy."""
    try:
        grace = max(0.0, min(30.0, float(os.getenv('SPLIT_BOOT_HANDOFF_GRACE_SEC', '10') or '10')))
    except Exception:
        grace = 10.0
    if grace <= 0:
        return
    deadline = time.time() + grace
    local_rev = _db_revision(target)
    highest = local_rev
    while time.time() < deadline:
        worker_rev = _worker_cache_revision()
        redis_rev = _redis_snapshot_revision_r18()
        remote_rev = max(worker_rev, redis_rev)
        if remote_rev > highest + 0.000001:
            if redis_rev >= worker_rev and redis_rev > highest + 0.000001:
                ok, detail = _restore_from_redis_direct_r18(target)
                print('[SPLIT FRONT] rolling handoff newer Redis snapshot:', ok, detail, 'remote_revision=', redis_rev, flush=True)
            else:
                ok, detail = _restore_from_worker(target)
                print('[SPLIT FRONT] rolling handoff newer Worker snapshot:', ok, detail, 'remote_revision=', worker_rev, flush=True)
            if ok:
                highest = max(highest, _db_revision(target), remote_rev)
        time.sleep(0.75)


def _run(cmd, timeout=60):
    return subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=timeout, check=False)


def _mega_login(timeout):
    try:
        who = _run(['mega-whoami'], timeout=min(20, timeout))
        if who.returncode == 0:
            return True, 'existing session'
    except Exception:
        pass
    session = str(os.getenv('MEGA_SESSION', '') or '').strip()
    email = str(os.getenv('MEGA_EMAIL', '') or '').strip()
    password = str(os.getenv('MEGA_PASSWORD', '') or '').strip()
    if not session and (not email or not password):
        return False, 'MEGA credentials/session missing'
    cmd = ['mega-login', session] if session else ['mega-login', email, password]
    for attempt in (1, 2):
        if attempt == 2:
            try: _run(['mega-logout'], timeout=20)
            except Exception: pass
            time.sleep(.6)
        try:
            p = _run(cmd, timeout=timeout)
            if p.returncode == 0:
                return True, 'login OK'
        except subprocess.TimeoutExpired:
            return False, f'mega-login timeout after {timeout}s'
        except FileNotFoundError:
            return False, 'MEGAcmd is not installed'
        except Exception as exc:
            return False, f'mega-login {type(exc).__name__}'
    return False, 'mega-login rejected'


def _restore_from_mega_emergency(target: Path):
    if not _bool('SPLIT_EMERGENCY_MEGA', True):
        return False, 'emergency MEGA disabled'
    root = '/' + str(os.getenv('MEGA_BACKUP_DIR', 'TelegramBotBackups2-2') or 'TelegramBotBackups2-2').strip('/')
    legacy_raw = str(os.getenv('MEGA_LEGACY_BACKUP_DIRS', '/TelegramBotBackups-2T,/TelegramBotBackups') or '')
    roots = [root]
    for item in legacy_raw.split(','):
        p = '/' + str(item or '').strip().strip('/')
        if p != '/' and p not in roots:
            roots.append(p)
    mega_timeout = max(45, min(900, int(os.getenv('MEGA_TIMEOUT', '120') or '120')))
    login_timeout = max(45, min(300, int(os.getenv('MEGA_LOGIN_TIMEOUT', '120') or '120')))
    logged, detail = _mega_login(login_timeout)
    if not logged:
        return False, detail
    tmpdir = Path(tempfile.mkdtemp(prefix='v262_emergency_mega_'))
    try:
        for idx, candidate_root in enumerate(roots):
            attempt = tmpdir / f'r{idx}'
            attempt.mkdir(parents=True, exist_ok=True)
            remotes = [candidate_root.rstrip('/') + '/database/latest_bot_state.sqlite3.gz']
            manifest_dir = attempt / 'manifest'
            manifest_dir.mkdir(exist_ok=True)
            try:
                mg = _run(['mega-get', candidate_root.rstrip('/') + '/database/current_manifest.json', str(manifest_dir)], timeout=mega_timeout)
            except Exception:
                mg = None
            if mg is not None and mg.returncode == 0:
                rows = list(manifest_dir.rglob('current_manifest.json')) + list(manifest_dir.rglob('*.json'))
                if rows:
                    try: payload = json.loads(rows[0].read_text(encoding='utf-8')) or {}
                    except Exception: payload = {}
                    generation_remote = str(payload.get('remote_generation') or '').strip()
                    if not generation_remote and payload.get('generation'):
                        generation_remote = candidate_root.rstrip('/') + '/database/generations/' + str(payload.get('generation'))
                    if generation_remote:
                        remotes.append(generation_remote)
            for ridx, remote in enumerate(remotes):
                dl = attempt / f'd{ridx}'
                dl.mkdir(exist_ok=True)
                try: get = _run(['mega-get', remote, str(dl)], timeout=mega_timeout)
                except Exception: continue
                if get.returncode != 0:
                    continue
                candidates = list(dl.rglob('*.sqlite3.gz')) + list(dl.rglob('*.gz'))
                for gz in candidates:
                    if _install_gzip_db(gz, target):
                        return True, f'emergency MEGA restore OK from {candidate_root}'
        return False, 'MEGA snapshot not available in current or legacy roots'
    finally:
        try: _run(['mega-quit'], timeout=12)
        except Exception: pass
        shutil.rmtree(tmpdir, ignore_errors=True)




def _r20_capsule_key():
    return str(os.getenv('WORKER_REDIS_CAPSULE_KEY','vys262:durable_capsule:r20') or 'vys262:durable_capsule:r20').strip()

def _r20_sqlite_meta_get(con, kind, key='latest'):
    try:
        row=con.execute('SELECT v FROM meta WHERE kind=? AND k=?',(kind,key)).fetchone()
        return json.loads(row[0]) if row and row[0] else {}
    except Exception:
        return {}

def _r20_sqlite_meta_set(con, kind, key, obj):
    con.execute('CREATE TABLE IF NOT EXISTS meta (kind TEXT NOT NULL, k TEXT NOT NULL, v TEXT NOT NULL, PRIMARY KEY(kind,k))')
    con.execute('INSERT INTO meta(kind,k,v) VALUES(?,?,?) ON CONFLICT(kind,k) DO UPDATE SET v=excluded.v',
                (str(kind),str(key),json.dumps(obj,ensure_ascii=False,separators=(',',':'),default=str)))

def _r20_apply_capsule_to_db(target: Path, capsule: dict):
    if not _db_valid(target) or not isinstance(capsule,dict):
        return False, 'invalid DB/capsule'
    us=capsule.get('user_state') or {}; cp=capsule.get('config_checkpoint') or {}; rev=capsule.get('state_revision') or {}
    in_seq=int((us or {}).get('seq') or capsule.get('user_state_seq') or 0)
    in_gen=int((cp or {}).get('generation') or capsule.get('config_generation') or 0)
    con=sqlite3.connect(str(target))
    try:
        cur_us=_r20_sqlite_meta_get(con,'user_state_shadow_v265','latest') or {}
        cur_cp=_r20_sqlite_meta_get(con,'config_guard_v234','latest') or {}
        cur_seq=int((cur_us or {}).get('seq') or 0); cur_gen=int((cur_cp or {}).get('generation') or 0)
        applied=[]
        if isinstance(us,dict) and us and in_seq >= cur_seq:
            _r20_sqlite_meta_set(con,'user_state_shadow_v265','latest',us); applied.append(f'user_state {cur_seq}->{in_seq}')
        if isinstance(cp,dict) and cp and in_gen >= cur_gen:
            _r20_sqlite_meta_set(con,'config_guard_v234','latest',cp)
            _r20_sqlite_meta_set(con,'config_guard_v234','generation',in_gen)
            _r20_sqlite_meta_set(con,'config_guard_v234','last_signature',str(cp.get('config_hash') or ''))
            _r20_sqlite_meta_set(con,'config_guard_v234','synced_hash',str(cp.get('config_hash') or ''))
            applied.append(f'config {cur_gen}->{in_gen}')
        if isinstance(rev,dict) and rev:
            cur_rev=_r20_sqlite_meta_get(con,'split_state_revision_r18','latest') or {}
            if float(rev.get('saved_at') or 0.0) >= float(cur_rev.get('saved_at') or 0.0):
                _r20_sqlite_meta_set(con,'split_state_revision_r18','latest',rev)
        con.commit()
        return bool(applied), ', '.join(applied) if applied else f'capsule not newer seq={in_seq}/{cur_seq} gen={in_gen}/{cur_gen}'
    finally:
        con.close()

def _r20_merge_capsules(*rows):
    candidates=[x for x in rows if isinstance(x,dict) and x]
    if not candidates:
        return {}
    base=dict(max(candidates,key=lambda x: float(x.get('saved_at') or 0.0)))
    best_us=max(candidates,key=lambda x: int((x.get('user_state') or {}).get('seq') or x.get('user_state_seq') or 0))
    best_cp=max(candidates,key=lambda x: int((x.get('config_checkpoint') or {}).get('generation') or x.get('config_generation') or 0))
    base['user_state']=best_us.get('user_state') or {}
    base['user_state_seq']=int((base['user_state'] or {}).get('seq') or best_us.get('user_state_seq') or 0)
    base['config_checkpoint']=best_cp.get('config_checkpoint') or {}
    base['config_generation']=int((base['config_checkpoint'] or {}).get('generation') or best_cp.get('config_generation') or 0)
    try:
        best_rev=max(candidates,key=lambda x: float(((x.get('state_revision') or {}).get('saved_at') or 0.0)))
        base['state_revision']=best_rev.get('state_revision') or {}
    except Exception:
        pass
    base['saved_at']=max(float(x.get('saved_at') or 0.0) for x in candidates)
    base['kind']='vys262_durable_capsule_r20'; base['schema']=1
    return base

def _r20_load_capsule_from_redis():
    if _redis is None: return {}, 'redis package unavailable'
    url=str(os.getenv('REDIS_URL','') or '').strip()
    if not url: return {}, 'REDIS_URL empty'
    try:
        client=_redis.Redis.from_url(url,socket_connect_timeout=1.0,socket_timeout=2.5,health_check_interval=30)
        raw=client.get(_r20_capsule_key())
        if not raw: return {}, 'capsule missing in Redis'
        payload=json.loads(gzip.decompress(raw).decode('utf-8'))
        return (payload if isinstance(payload,dict) else {}), 'Redis capsule OK'
    except Exception as exc:
        return {}, f'{type(exc).__name__}: {str(exc)[:180]}'

def _r20_load_capsule_from_worker():
    base,secret=_peer_base(),_secret()
    if not base or not secret: return {}, 'worker URL/secret not configured'
    try:
        r=requests.get(base+'/internal/capsule/latest?deep=1',headers={'X-Peer-Secret':secret,'User-Agent':'vys-262-front-capsule-restore-r20'},timeout=max(5.0,min(30.0,float(os.getenv('SPLIT_CAPSULE_BOOT_TIMEOUT','15') or '15'))))
        if r.status_code!=200: return {}, f'worker HTTP {r.status_code}'
        raw=r.content
        if str(r.headers.get('Content-Encoding') or '').lower()=='gzip' or raw[:2]==b'\x1f\x8b':
            raw=gzip.decompress(raw)
        payload=json.loads(raw.decode('utf-8'))
        return (payload if isinstance(payload,dict) else {}), 'Worker capsule OK'
    except Exception as exc:
        return {}, f'{type(exc).__name__}: {str(exc)[:180]}'

def _r20_restore_capsule(target: Path):
    # Boot-only quorum: query both small capsule sources and merge the independently
    # monotonic components. This prevents a newer user-state in one source from
    # hiding a newer config generation in the other source.
    redis_payload,redis_detail=_r20_load_capsule_from_redis()
    worker_payload,worker_detail=_r20_load_capsule_from_worker()
    payload=_r20_merge_capsules(redis_payload,worker_payload)
    if not payload:
        return False, 'redis='+redis_detail+'; worker='+worker_detail
    try:
        ok,apply_detail=_r20_apply_capsule_to_db(target,payload)
        return True, 'redis='+redis_detail+'; worker='+worker_detail+'; '+apply_detail
    except Exception as exc:
        return False, f'capsule apply {type(exc).__name__}: {str(exc)[:180]}'

def _redis_seed_current_db(target: Path, reason='front_boot'):
    """Best-effort seed of shared durable snapshot before worker can be redeployed."""
    if _redis is None or not _db_valid(target):
        return False, 'redis unavailable or DB invalid'
    url = str(os.getenv('REDIS_URL', '') or '').strip()
    if not url:
        return False, 'REDIS_URL empty'
    key = str(os.getenv('WORKER_REDIS_SNAPSHOT_KEY', 'vys262:bot_state:latest_gz') or 'vys262:bot_state:latest_gz').strip()
    tmpdir = Path(tempfile.mkdtemp(prefix='v266_front_seed_'))
    try:
        gz = tmpdir / 'latest.sqlite3.gz'
        # DB has already been installed/restored and is not open by the bot yet.
        with open(target, 'rb') as src, gzip.open(gz, 'wb', compresslevel=9) as dst:
            shutil.copyfileobj(src, dst, length=1024 * 1024)
        payload = gz.read_bytes()
        max_mb = max(1, min(128, int(os.getenv('WORKER_REDIS_SNAPSHOT_MAX_MB', '16') or '16')))
        if len(payload) > max_mb * 1024 * 1024:
            return False, f'snapshot too large for Redis: {len(payload)}'
        revision = 0.0
        try:
            con = sqlite3.connect(str(target))
            try:
                for kind in ('split_state_revision_r18', 'user_state_shadow_v265', 'runtime_continuity_v263'):
                    row = con.execute("SELECT v FROM meta WHERE kind=? AND k='latest'", (kind,)).fetchone()
                    if row:
                        obj = json.loads(row[0])
                        revision = max(revision, float((obj or {}).get('saved_at') or 0.0))
            finally:
                con.close()
        except Exception:
            pass
        client = _redis.Redis.from_url(url, socket_connect_timeout=3, socket_timeout=8, health_check_interval=30)
        existing_revision = _redis_snapshot_revision_r18(client)
        if existing_revision > revision + 0.000001:
            return True, f'Redis newer state kept existing={existing_revision} incoming={revision}'
        meta = {'revision':revision, 'size':len(payload), 'saved_at':time.time(), 'reason':str(reason or '')[:120], 'source':'front-start-r18'}
        pipe = client.pipeline(transaction=True)
        pipe.set(key, payload)
        pipe.set(key + ':meta', json.dumps(meta, separators=(',', ':')))
        pipe.execute()
        return True, f'Redis durable seed OK size={len(payload)} revision={revision}'
    except Exception as exc:
        return False, f'{type(exc).__name__}: {str(exc)[:180]}'
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)



def _r32_seed_marker_client():
    if _redis is None:
        return None
    url=str(os.getenv('REDIS_URL','') or '').strip()
    if not url:
        return None
    return _redis.Redis.from_url(url,socket_connect_timeout=1.5,socket_timeout=3,health_check_interval=30)

def _r32_migration_seeded():
    try:
        c=_r32_seed_marker_client();
        if c is None: return False
        return bool(c.get('vys262:state_events:r32:migration_seeded'))
    except Exception:
        return False

def _r32_mark_migration_seeded():
    try:
        c=_r32_seed_marker_client();
        if c is None: return False
        c.set('vys262:state_events:r32:migration_seeded','1')
        return True
    except Exception:
        return False

def _preboot_capture_old_front_r18():
    # R32 needs one exact migration seed from the old R31 instance. After that,
    # HEAVY is rebuilt from immutable row events and no full preboot capture is sent.
    if _bool('R32_EVENT_STREAM_ENABLED', True) and _r32_migration_seeded():
        return True, 'R32 event stream already seeded; full preboot capture skipped'
    ok,detail=_preboot_capture_old_front_r18_legacy()
    if ok and _bool('R32_EVENT_STREAM_ENABLED', True):
        _r32_mark_migration_seeded()
        detail=str(detail)+'; R32 migration seed marked'
    return ok,detail

def main():
    server = _start_boot_port()
    target = _db_path()
    try:
        # Capture the old live instance before Render switches the primary URL to this
        # new preboot process.  This is the migration bridge from stale R17 caches.
        _cap_ok, _cap_detail = _preboot_capture_old_front_r18()
        print('[SPLIT FRONT] preboot old-front capture:', _cap_ok, _cap_detail, flush=True)
        force = _bool('SPLIT_FORCE_BOOT_RESTORE', False)
        always_remote = _bool('SPLIT_BOOT_ALWAYS_RESTORE', True)
        local_valid = _db_valid(target)
        if force or always_remote or not local_valid:
            while True:
                ok, detail = _restore_from_worker(target)
                print('[SPLIT FRONT] worker restore:', ok, detail, flush=True)
                if ok:
                    break
                # A valid local DB can be newer than MEGA during a temporary worker outage.
                # Never overwrite it with an older cloud snapshot merely because the peer is down.
                if local_valid and not force:
                    print('[SPLIT FRONT] worker unavailable; keeping valid local SQLite:', detail, flush=True)
                    break
                ok, detail = _restore_from_mega_emergency(target)
                print('[SPLIT FRONT] emergency MEGA:', ok, detail, flush=True)
                if ok:
                    break
                if _bool('SPLIT_ALLOW_EMPTY_BOOT', False):
                    print('[SPLIT FRONT] empty boot explicitly allowed', flush=True)
                    break
                time.sleep(max(5, min(120, int(os.getenv('SPLIT_RESTORE_RETRY_SEC', '20') or '20'))))
        # R32/R18 freshness quorum: Worker /tmp can lag behind the shared Redis durable
        # snapshot during a rolling deploy.  Prefer whichever has the newest revision.
        if _db_valid(target):
            if _bool('R32_EVENT_STREAM_ENABLED', True):
                print('[SPLIT FRONT] R32 restore authority: HEAVY assembled checkpoint + event journal; Redis full-snapshot arbitration skipped', flush=True)
            else:
                _r18_ok, _r18_detail = _restore_from_redis_direct_r18(target)
                print('[SPLIT FRONT] Redis freshness arbitration:', _r18_ok, _r18_detail, flush=True)
                # Old instance can publish an even newer final checkpoint after cut-over.
                _settle_worker_handoff(target)
        # R20: restore the newest independent v262-style settings/user-state capsule
        # even when the full Worker SQLite image is slightly older.
        if _db_valid(target):
            _cap20_ok, _cap20_detail = _r20_restore_capsule(target)
            print('[SPLIT FRONT] R20 durable capsule restore:', _cap20_ok, _cap20_detail, flush=True)
        # R14: packaged runtime_config.py is authoritative for all internal tunables.
        install_internal_runtime_config('front')
        # Service-account private key must never be loaded by the Telegram front.
        os.environ.pop('GOOGLE_SERVICE_ACCOUNT_JSON', None)
        # R6 migration/deploy bridge: persist the exact restored/current DB in shared
        # Redis before the worker can be redeployed and lose its /tmp cache.
        if _bool('R32_EVENT_STREAM_ENABLED', True):
            print('[SPLIT FRONT] R32: full FAST->Redis boot seed skipped; HEAVY owns assembled restore state', flush=True)
        else:
            redis_ok, redis_detail = _redis_seed_current_db(target, reason='front_boot_after_restore')
            print('[SPLIT FRONT] Redis durable seed:', redis_ok, redis_detail, flush=True)
        # R19 single restore authority: start_front has already arbitrated Worker/Redis/
        # local freshness. The legacy bot.main restore path must never run a second,
        # potentially older Telegram/MEGA restore over this exact database.
        if _db_valid(target):
            _r19_revision = _db_revision(target)
            os.environ['SPLIT_PREBOOT_AUTHORITATIVE_R20'] = '1'
            os.environ['SPLIT_PREBOOT_REVISION_R20'] = str(_r19_revision)
            print(f'[SPLIT FRONT] R20 authoritative preboot DB revision={_r19_revision}', flush=True)
        _stop_boot_port(server)
        runpy.run_path(str(Path(__file__).with_name('bot.py')), run_name='__main__')
    finally:
        try: _stop_boot_port(server)
        except Exception: pass


if __name__ == '__main__':
    main()
# v262
