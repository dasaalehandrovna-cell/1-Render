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
            for kind in ('user_state_shadow_v265', 'runtime_continuity_v263'):
                row = con.execute("SELECT v FROM meta WHERE kind=? AND k='latest'", (kind,)).fetchone()
                if row:
                    try:
                        obj = json.loads(row[0]) or {}
                        change_ns = int((obj or {}).get('change_rev_ns') or 0)
                        candidate = (change_ns / 1_000_000_000.0) if change_ns > 0 else float((obj or {}).get('saved_at') or 0.0)
                        rev = max(rev, candidate)
                    except Exception:
                        pass
            # legacy/fallback monotonic-ish timestamp if continuity metadata predates R4.
            row = con.execute("SELECT v FROM kv WHERE k='root'").fetchone()
            if row:
                try:
                    root = json.loads(row[0]) or {}
                    state_meta = root.get('_state_meta') or {}
                    r17_ns = int(state_meta.get('r17_change_rev_ns') or 0)
                    if r17_ns > 0:
                        rev = max(rev, r17_ns / 1_000_000_000.0)
                    stamp = str(state_meta.get('last_saved_at') or '')
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


def _redis_deploy_state_key():
    return str(os.getenv('WORKER_REDIS_DEPLOY_STATE_KEY', 'vys262:deploy_state:r17') or 'vys262:deploy_state:r17').strip()


def _apply_redis_deploy_state_overlay(target: Path):
    """Overlay the newest compact R17 settings/UI capsule onto restored SQLite.

    Worker/MEGA snapshots remain canonical for finance.  This tiny Redis capsule only
    contains non-financial state and can therefore rescue the final clicks even when a
    rolling deploy cuts over before the old Front finishes a full SQLite handoff.
    """
    if _redis is None or not _db_valid(target):
        return False, 'redis unavailable or DB invalid'
    url = str(os.getenv('REDIS_URL', '') or '').strip()
    if not url:
        return False, 'REDIS_URL empty'
    key = _redis_deploy_state_key()
    try:
        client = _redis.Redis.from_url(url, socket_connect_timeout=1.0, socket_timeout=2.0, health_check_interval=30)
        wire = client.get(key)
        if not wire:
            return False, 'R17 deploy-state capsule missing'
        try:
            raw = gzip.decompress(wire)
            body = json.loads(raw.decode('utf-8')) or {}
        except Exception as exc:
            return False, f'R17 capsule decode failed: {type(exc).__name__}: {str(exc)[:160]}'
        if not isinstance(body, dict) or int(body.get('schema') or 0) < 17:
            return False, 'R17 deploy-state capsule schema invalid'
        expected = str(body.get('sha256') or '')
        if expected:
            check = dict(body); check.pop('sha256', None)
            digest = __import__('hashlib').sha256(json.dumps(check, ensure_ascii=False, separators=(',', ':'), default=str).encode('utf-8')).hexdigest()
            if digest != expected:
                return False, 'R17 deploy-state capsule hash mismatch'
        incoming_ns = int(body.get('change_rev_ns') or 0)
        incoming_rev = incoming_ns / 1_000_000_000.0 if incoming_ns > 0 else float(body.get('saved_at') or 0.0)
        local_rev = _db_revision(target)
        if incoming_rev <= 0.0 or incoming_rev <= local_rev + 0.0000005:
            return True, f'R17 capsule not newer incoming={incoming_rev:.6f} local={local_rev:.6f}'
        shadow = body.get('shadow') or {}
        continuity = body.get('continuity') or {}
        if not isinstance(shadow, dict) or not shadow:
            return False, 'R17 capsule shadow missing'
        con = sqlite3.connect(str(target))
        try:
            con.execute('CREATE TABLE IF NOT EXISTS meta (kind TEXT NOT NULL, k TEXT NOT NULL, v TEXT NOT NULL, PRIMARY KEY(kind, k))')
            con.execute("INSERT INTO meta(kind,k,v) VALUES(?,?,?) ON CONFLICT(kind,k) DO UPDATE SET v=excluded.v",
                        ('user_state_shadow_v265', 'latest', json.dumps(shadow, ensure_ascii=False, separators=(',', ':'))))
            if isinstance(continuity, dict) and continuity:
                con.execute("INSERT INTO meta(kind,k,v) VALUES(?,?,?) ON CONFLICT(kind,k) DO UPDATE SET v=excluded.v",
                            ('runtime_continuity_v263', 'latest', json.dumps(continuity, ensure_ascii=False, separators=(',', ':'))))
            con.commit()
        finally:
            con.close()
        return True, f'R17 capsule overlay applied incoming={incoming_rev:.6f} local={local_rev:.6f}'
    except Exception as exc:
        return False, f'R17 capsule {type(exc).__name__}: {str(exc)[:180]}'


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
    raw = str(os.getenv('PEER_SERVICE_URL', '') or '').strip().rstrip('/')
    if raw and not raw.startswith(('http://','https://')):
        raw = 'https://' + raw
    return raw


def _secret():
    return str(os.getenv('PEER_SHARED_SECRET', '') or '').strip()


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
        remote_rev = _worker_cache_revision()
        if remote_rev > highest + 0.000001:
            ok, detail = _restore_from_worker(target)
            print('[SPLIT FRONT] rolling handoff newer snapshot:', ok, detail, 'remote_revision=', remote_rev, flush=True)
            if ok:
                highest = max(highest, _db_revision(target), remote_rev)
        time.sleep(1.0)


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
        # R17 revision is the timestamp of the LAST REAL USER MUTATION, not
        # the time a snapshot happened to be captured.  Otherwise a late old
        # Render instance can look newer merely because it shut down later.
        revision = float(_db_revision(target) or 0.0)
        client = _redis.Redis.from_url(url, socket_connect_timeout=2, socket_timeout=4, health_check_interval=30)
        meta = {'revision':revision, 'size':len(payload), 'saved_at':time.time(), 'reason':str(reason or '')[:120], 'source':'front-start-r17'}
        meta_raw = json.dumps(meta, separators=(',', ':'))
        script = """
local old = redis.call('GET', KEYS[2])
local oldrev = 0
if old then
  local ok,obj = pcall(cjson.decode, old)
  if ok and obj and obj['revision'] then oldrev = tonumber(obj['revision']) or 0 end
end
local newrev = tonumber(ARGV[3]) or 0
if oldrev > newrev then return 0 end
redis.call('SET', KEYS[1], ARGV[1])
redis.call('SET', KEYS[2], ARGV[2])
return 1
"""
        accepted = int(client.eval(script, 2, key, key + ':meta', payload, meta_raw, str(revision)) or 0)
        if not accepted:
            return True, f'Redis durable seed stale-rejected revision={revision}'
        return True, f'Redis durable seed OK size={len(payload)} revision={revision}'
    except Exception as exc:
        return False, f'{type(exc).__name__}: {str(exc)[:180]}'
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


def main():
    server = _start_boot_port()
    target = _db_path()
    try:
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
        # Rolling deploy handoff: old instance can publish a newer final snapshot only
        # after Render sees this preboot instance as healthy. Pick that newer revision.
        if _db_valid(target):
            _settle_worker_handoff(target)
            capsule_ok, capsule_detail = _apply_redis_deploy_state_overlay(target)
            print('[SPLIT FRONT] R17 deploy-state overlay:', capsule_ok, capsule_detail, flush=True)
        # R14: packaged runtime_config.py is authoritative for all internal tunables.
        install_internal_runtime_config('front')
        # Service-account private key must never be loaded by the Telegram front.
        os.environ.pop('GOOGLE_SERVICE_ACCOUNT_JSON', None)
        # R6 migration/deploy bridge: persist the exact restored/current DB in shared
        # Redis before the worker can be redeployed and lose its /tmp cache.
        redis_ok, redis_detail = _redis_seed_current_db(target, reason='front_boot_after_restore')
        print('[SPLIT FRONT] Redis durable seed:', redis_ok, redis_detail, flush=True)
        _stop_boot_port(server)
        runpy.run_path(str(Path(__file__).with_name('bot.py')), run_name='__main__')
    finally:
        try: _stop_boot_port(server)
        except Exception: pass


if __name__ == '__main__':
    main()
# v262
