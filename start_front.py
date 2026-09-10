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
        revision = 0.0
        try:
            con = sqlite3.connect(str(target))
            try:
                for kind in ('user_state_shadow_v265', 'runtime_continuity_v263'):
                    row = con.execute("SELECT v FROM meta WHERE kind=? AND k='latest'", (kind,)).fetchone()
                    if row:
                        obj = json.loads(row[0])
                        revision = max(revision, float((obj or {}).get('saved_at') or 0.0))
            finally:
                con.close()
        except Exception:
            pass
        client = _redis.Redis.from_url(url, socket_connect_timeout=3, socket_timeout=8, health_check_interval=30)
        meta = {'revision':revision, 'size':len(payload), 'saved_at':time.time(), 'reason':str(reason or '')[:120], 'source':'front-start-r6'}
        pipe = client.pipeline(transaction=True)
        pipe.set(key, payload)
        pipe.set(key + ':meta', json.dumps(meta, separators=(',', ':')))
        pipe.execute()
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
        os.environ['BOT_SPLIT_ROLE'] = 'front'
        os.environ['RENDER_TELEGRAM_ONLY'] = '1'
        # Normal MEGA runtime is strictly OFF on front. start_front itself already used
        # the credentials above only if emergency recovery was necessary.
        os.environ['MEGA_ENABLED'] = '0'
        os.environ['MEGA_AUTORESTORE'] = '0'
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
