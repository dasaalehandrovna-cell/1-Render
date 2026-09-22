# v262
#!/usr/bin/env python3
"""Render #1 launcher: local crash cache, Redis daily FULL+TAIL, then MEGA fallback.

OCH12.24 recovery policy:
- same-container local cache is only a crash breadcrumb;
- Redis is trusted only as one verified daily FULL plus its complete logical TAIL;
- legacy/incomplete Redis recovery is rejected before touching a valid live SQLite;
- MEGA startup recovery reads ONLY the current fixed compact_v80 objects: head.json, latest.sqlite3.gz, tail.json.gz;
- startup never scans database/current_manifest, database/generations, database/pre_restore or legacy latest mirrors;
- startup tries local cache, Redis and compact MEGA at most once; runtime enable flags do not suppress disaster recovery;
- if every source fails or is absent, startup creates a normal empty SQLite and continues;
- runtime MEGA work stays delegated to Render #2 / HEAVY by default.
"""
from __future__ import annotations

import gzip
import hashlib
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
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

from runtime_config import install_internal_runtime_config, CONFIG_VERSION as INTERNAL_CONFIG_VERSION

install_internal_runtime_config("front")


_PREBOOT_SPOOL_LOCK = threading.RLock()
_PREBOOT_SPOOL_PATH = Path(os.getenv('PREBOOT_WEBHOOK_SPOOL_FILE', '/tmp/vys262_preboot_webhooks.ndjson') or '/tmp/vys262_preboot_webhooks.ndjson')
_PREBOOT_MAX_BODY = 4 * 1024 * 1024
_PREBOOT_CAPTURED = 0


def _preboot_expected_route() -> str:
    token = str(os.getenv('B_T', '') or '').strip()
    host = str(os.getenv('RENDER_EXTERNAL_HOSTNAME', '') or '').strip()
    render_url = f'https://{host}' if host else str(os.getenv('RENDER_EXTERNAL_URL', '') or '').strip()
    webhook_url = render_url or str(os.getenv('WEBHOOK_URL', '') or os.getenv('APP_URL', '') or '').strip()
    seed = str(os.getenv('WEBHOOK_SECRET', '') or '').strip()
    if not seed:
        authority = str(os.getenv('RENDER_SERVICE_ID', '') or webhook_url)
        seed = hashlib.sha256(('telegram-webhook-v163|' + token + '|' + authority).encode('utf-8')).hexdigest()[:40]
    return '/tg/' + seed


def _preboot_capture(raw: bytes, path: str) -> tuple[bool, str, int]:
    global _PREBOOT_CAPTURED
    if str(path or '').split('?', 1)[0] != _preboot_expected_route():
        return False, 'route_mismatch', 0
    if not raw or len(raw) > _PREBOOT_MAX_BODY:
        return False, 'body_size', 0
    try:
        payload = json.loads(raw.decode('utf-8'))
    except Exception:
        return False, 'invalid_json', 0
    if not isinstance(payload, dict):
        return False, 'invalid_payload', 0
    try:
        update_id = int(payload.get('update_id'))
    except Exception:
        return False, 'missing_update_id', 0
    known = ('callback_query', 'message', 'edited_message', 'channel_post', 'edited_channel_post', 'deleted_business_messages')
    update_type = next((k for k in known if k in payload), 'other')
    if update_type == 'other':
        return False, 'unsupported_update', update_id
    line = json.dumps({'captured_at': time.time(), 'update_id': update_id, 'type': update_type, 'payload': payload}, ensure_ascii=False, separators=(',', ':')) + '\n'
    with _PREBOOT_SPOOL_LOCK:
        _PREBOOT_SPOOL_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(_PREBOOT_SPOOL_PATH, 'a', encoding='utf-8') as fh:
            fh.write(line)
            fh.flush()
            try: os.fsync(fh.fileno())
            except Exception: pass
        _PREBOOT_CAPTURED += 1
    print(f'[SPLIT FRONT] R54 preboot captured Telegram update={update_id} type={update_type} spool={_PREBOOT_CAPTURED}', flush=True)
    return True, update_type, update_id


class _ReusableBootHTTPServer(ThreadingHTTPServer):
    allow_reuse_address = True
    daemon_threads = True


class _BootHealthHandler(BaseHTTPRequestHandler):
    def _reply(self, status: int, body: bool, extra: dict | None=None):
        payload = {'ok': status < 400, 'role': 'front', 'phase': 'restoring_remote_state'}
        if extra:
            payload.update(extra)
        raw = json.dumps(payload, ensure_ascii=False, separators=(',', ':')).encode('utf-8') if body else b''
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(raw)))
        self.end_headers()
        if raw:
            self.wfile.write(raw)

    def do_GET(self): self._reply(200, True, {'telegram_spooled': _PREBOOT_CAPTURED})
    def do_HEAD(self): self._reply(200, False)
    def do_POST(self):
        try:
            length = int(self.headers.get('Content-Length', '0') or '0')
        except Exception:
            length = 0
        if length <= 0 or length > _PREBOOT_MAX_BODY:
            self._reply(503, True, {'captured': False, 'reason': 'body_size'})
            return
        raw = self.rfile.read(length)
        ok, detail, update_id = _preboot_capture(raw, self.path)
        # Keep Telegram retry semantics during BOOT even after the local durable spool
        # accepted the update.  Replayed/Telegram-redelivered duplicates are collapsed
        # later by the canonical update_id inbox/dispatcher.
        self._reply(503, True, {'captured': bool(ok), 'reason': detail, 'update_id': update_id})
    def log_message(self, fmt, *args): return


def _bool(name: str, default=False) -> bool:
    return str(os.getenv(name, '1' if default else '0') or '').strip().lower() in {'1', 'true', 'yes', 'on', 'да'}


def _start_boot_port():
    port = int(os.getenv('PORT', '5000') or '5000')
    server = _ReusableBootHTTPServer(('0.0.0.0', port), _BootHealthHandler)
    threading.Thread(target=server.serve_forever, name='v262-front-boot-http', daemon=True).start()
    print(f'[SPLIT FRONT] preboot port open on 0.0.0.0:{port}', flush=True)
    return server


def _stop_boot_port(server):
    try: server.shutdown()
    except Exception: pass
    try: server.server_close()
    except Exception: pass


def _db_path() -> Path:
    return Path(os.getenv('DB_FILE', 'bot_state.sqlite3') or 'bot_state.sqlite3').resolve()


def _db_valid(path: Path) -> bool:
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


def _ensure_empty_db(path: Path) -> tuple[bool, str]:
    """OCH12.11: initialize a normal empty SQLite when no recovery source exists."""
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        for suffix in ('-wal', '-shm'):
            try:
                Path(str(path) + suffix).unlink(missing_ok=True)
            except Exception:
                pass
        con = sqlite3.connect(str(path), timeout=20)
        try:
            con.execute('PRAGMA journal_mode=WAL')
            con.execute('PRAGMA synchronous=FULL')
            con.execute('CREATE TABLE IF NOT EXISTS kv (k TEXT PRIMARY KEY, v TEXT NOT NULL)')
            con.execute('CREATE TABLE IF NOT EXISTS chats (chat_id TEXT PRIMARY KEY, v TEXT NOT NULL)')
            con.execute('CREATE TABLE IF NOT EXISTS meta (kind TEXT NOT NULL, k TEXT NOT NULL, v TEXT NOT NULL, PRIMARY KEY(kind,k))')
            con.execute("CREATE TABLE IF NOT EXISTS cold_fields (chat_id TEXT NOT NULL, k TEXT NOT NULL, v TEXT NOT NULL, updated_at TEXT NOT NULL DEFAULT '', PRIMARY KEY(chat_id,k))")
            con.execute('CREATE TABLE IF NOT EXISTS r32_state_revisions (shard_key TEXT PRIMARY KEY, revision INTEGER NOT NULL, event_id TEXT NOT NULL, updated_at REAL NOT NULL)')
            con.commit()
        finally:
            con.close()
        # Make the file self-contained before runtime opens its own WAL connection.
        try:
            con = sqlite3.connect(str(path), timeout=20)
            try:
                con.execute('PRAGMA wal_checkpoint(TRUNCATE)')
            finally:
                con.close()
        except Exception:
            pass
        return bool(_db_valid(path)), 'normal empty SQLite initialized' if _db_valid(path) else 'empty SQLite init validation failed'
    except Exception as exc:
        return False, f'{type(exc).__name__}: {str(exc)[:300]}'


def _db_revision(path: Path, *, validated: bool=False) -> float:
    # OCH12.24: callers that already ran PRAGMA quick_check can reuse that result.
    # This avoids repeating SQLite integrity scans during the BOOT decision tree.
    if not validated and not _db_valid(path):
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
            row = con.execute("SELECT v FROM kv WHERE k='root'").fetchone()
            if row and rev <= 0.0:
                try:
                    root = json.loads(row[0]) or {}
                    stamp = str((root.get('_state_meta') or {}).get('last_saved_at') or '')
                    if stamp:
                        from datetime import datetime
                        rev = datetime.fromisoformat(stamp.replace('Z', '+00:00')).timestamp()
                except Exception:
                    pass
            return float(rev or 0.0)
        finally:
            con.close()
    except Exception:
        return 0.0


def _install_gzip_db(gz_path: Path, target: Path) -> tuple[bool, str]:
    tmp = target.with_suffix(target.suffix + '.restore.tmp')
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        with gzip.open(gz_path, 'rb') as src, open(tmp, 'wb') as dst:
            shutil.copyfileobj(src, dst, length=1024 * 1024)
        if not _db_valid(tmp):
            return False, 'downloaded gzip does not contain a valid SQLite DB'
        incoming_revision = _db_revision(tmp)
        current_revision = _db_revision(target) if _db_valid(target) else 0.0
        if current_revision > 0.0 and (incoming_revision <= 0.0 or incoming_revision < current_revision):
            detail = f'stale MEGA restore rejected incoming={incoming_revision} local={current_revision}'
            print('[SPLIT FRONT]', detail, flush=True)
            return False, detail
        os.replace(tmp, target)
        for suffix in ('-wal', '-shm'):
            try: Path(str(target) + suffix).unlink(missing_ok=True)
            except Exception: pass
        return True, f'installed revision={incoming_revision}'
    finally:
        try: tmp.unlink(missing_ok=True)
        except Exception: pass


def _run(args, timeout=120):
    return subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=timeout)


def _mega_login(timeout: int) -> tuple[bool, str]:
    session = str(os.getenv('MEGA_SESSION', '') or '').strip()
    email = str(os.getenv('MEGA_EMAIL', '') or '').strip()
    password = str(os.getenv('MEGA_PASSWORD', '') or '')
    if not session and not (email and password):
        return False, 'MEGA credentials are not configured on FAST startup'
    cmd = ['mega-login', session] if session else ['mega-login', email, password]
    for attempt in (1, 2):
        if attempt == 2:
            try: _run(['mega-logout'], timeout=20)
            except Exception: pass
            time.sleep(0.6)
        try:
            p = _run(cmd, timeout=timeout)
            if p.returncode == 0:
                return True, 'login OK'
        except subprocess.TimeoutExpired:
            return False, f'mega-login timeout after {timeout}s'
        except FileNotFoundError:
            return False, 'MEGAcmd is not installed'
        except Exception as exc:
            return False, f'mega-login {type(exc).__name__}: {str(exc)[:160]}'
    return False, 'mega-login rejected'


def _canonical_mega_root() -> str:
    """Return the *only* MEGA root allowed for this deployment.

    R58: the root must come from Render MEGA_BACKUP_DIR.  There is deliberately
    no historical/default root when MEGA is enabled: a missing variable is a
    deployment error, not permission to inspect another MEGA folder.
    """
    raw = str(os.getenv('MEGA_BACKUP_DIR', '') or '').strip().replace('\\', '/')
    root = '/' + raw.strip('/') if raw.strip('/') else ''
    return root.rstrip('/')


def _startup_mega_roots() -> list[str]:
    """R58 strict-root policy: startup may inspect exactly one Render root."""
    root = _canonical_mega_root()
    return [root] if root else []


def _mega_remote_within_root(remote: str, root: str) -> bool:
    root = '/' + str(root or '').strip().strip('/')
    remote = '/' + str(remote or '').strip().strip('/')
    if root == '/' or not root.strip('/'):
        return False
    return remote == root or remote.startswith(root.rstrip('/') + '/')


def _mega_missing(detail: str) -> bool:
    low = str(detail or '').casefold()
    return any(x in low for x in ('not found', 'no such', 'does not exist', "couldn't find", 'couldn\'t find'))


# OCH12.24: historical manifest/generation/pre_restore discovery intentionally removed.
# Startup recovery uses fixed compact_v80 objects only; no mega-find/tree scan is allowed.


def _r32_event_valid(ev: object) -> bool:
    if not isinstance(ev, dict) or int(ev.get('schema') or 0) != 32:
        return False
    if not str(ev.get('event_id') or '') or int(ev.get('revision') or 0) <= 0:
        return False
    return str(ev.get('kind') or '') in {'set_kv','save_chat','prune_chats','delete_chat','set_meta','set_cold','set_cold_many','delete_cold'}


def _r32_max_revision(path: Path) -> int:
    if not _db_valid(path):
        return 0
    try:
        con = sqlite3.connect(str(path))
        try:
            row = con.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='r32_state_revisions'").fetchone()
            if not row:
                return 0
            val = con.execute('SELECT MAX(revision) FROM r32_state_revisions').fetchone()
            return int((val or [0])[0] or 0)
        finally:
            con.close()
    except Exception:
        return 0


def _apply_r32_events(path: Path, events: list[dict]) -> tuple[int, int]:
    if not events:
        return 0, 0
    con = sqlite3.connect(str(path), timeout=30)
    applied = stale = 0
    try:
        con.execute('PRAGMA journal_mode=WAL')
        con.execute('PRAGMA synchronous=FULL')
        con.execute('CREATE TABLE IF NOT EXISTS kv (k TEXT PRIMARY KEY, v TEXT NOT NULL)')
        con.execute('CREATE TABLE IF NOT EXISTS chats (chat_id TEXT PRIMARY KEY, v TEXT NOT NULL)')
        con.execute('CREATE TABLE IF NOT EXISTS meta (kind TEXT NOT NULL, k TEXT NOT NULL, v TEXT NOT NULL, PRIMARY KEY(kind,k))')
        con.execute("CREATE TABLE IF NOT EXISTS cold_fields (chat_id TEXT NOT NULL, k TEXT NOT NULL, v TEXT NOT NULL, updated_at TEXT NOT NULL DEFAULT '', PRIMARY KEY(chat_id,k))")
        con.execute('CREATE TABLE IF NOT EXISTS r32_state_revisions (shard_key TEXT PRIMARY KEY, revision INTEGER NOT NULL, event_id TEXT NOT NULL, updated_at REAL NOT NULL)')
        con.execute('BEGIN IMMEDIATE')
        for ev in sorted(events, key=lambda x: int(x.get('revision') or 0)):
            if not _r32_event_valid(ev):
                continue
            kind = str(ev.get('kind') or '')
            key = str(ev.get('key') or '')[:220]
            rev = int(ev.get('revision') or 0)
            eid = str(ev.get('event_id') or '')
            payload = ev.get('payload') if isinstance(ev.get('payload'), dict) else {}
            row = con.execute('SELECT revision FROM r32_state_revisions WHERE shard_key=?', (key,)).fetchone()
            if row and int(row[0] or 0) >= rev:
                stale += 1
                continue
            if kind == 'set_kv':
                k = str(payload.get('k') or '')
                con.execute('INSERT INTO kv(k,v) VALUES(?,?) ON CONFLICT(k) DO UPDATE SET v=excluded.v', (k, json.dumps(payload.get('v'), ensure_ascii=False, separators=(',',':'), default=str)))
            elif kind == 'save_chat':
                cid = str(payload.get('chat_id') or '')
                con.execute('INSERT INTO chats(chat_id,v) VALUES(?,?) ON CONFLICT(chat_id) DO UPDATE SET v=excluded.v', (cid, json.dumps(payload.get('v') or {}, ensure_ascii=False, separators=(',',':'), default=str)))
            elif kind == 'prune_chats':
                keep = {str(x) for x in (payload.get('keep') or [])}
                for r in con.execute('SELECT chat_id FROM chats').fetchall():
                    if str(r[0]) not in keep:
                        con.execute('DELETE FROM chats WHERE chat_id=?', (str(r[0]),))
            elif kind == 'delete_chat':
                cid = str(payload.get('chat_id') or '')
                con.execute('DELETE FROM chats WHERE chat_id=?', (cid,))
                con.execute('DELETE FROM cold_fields WHERE chat_id=?', (cid,))
            elif kind == 'set_meta':
                mk = str(payload.get('kind') or ''); kk = str(payload.get('k') or '')
                con.execute('INSERT INTO meta(kind,k,v) VALUES(?,?,?) ON CONFLICT(kind,k) DO UPDATE SET v=excluded.v', (mk, kk, json.dumps(payload.get('v'), ensure_ascii=False, separators=(',',':'), default=str)))
            elif kind == 'set_cold':
                cid = str(payload.get('chat_id') or ''); kk = str(payload.get('k') or '')
                stamp = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
                con.execute('INSERT INTO cold_fields(chat_id,k,v,updated_at) VALUES(?,?,?,?) ON CONFLICT(chat_id,k) DO UPDATE SET v=excluded.v,updated_at=excluded.updated_at', (cid, kk, json.dumps(payload.get('v'), ensure_ascii=False, separators=(',',':'), default=str), stamp))
            elif kind == 'set_cold_many':
                cid = str(payload.get('chat_id') or ''); stamp = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
                for kk, vv in (payload.get('items') or {}).items():
                    con.execute('INSERT INTO cold_fields(chat_id,k,v,updated_at) VALUES(?,?,?,?) ON CONFLICT(chat_id,k) DO UPDATE SET v=excluded.v,updated_at=excluded.updated_at', (cid, str(kk), json.dumps(vv, ensure_ascii=False, separators=(',',':'), default=str), stamp))
            elif kind == 'delete_cold':
                con.execute('DELETE FROM cold_fields WHERE chat_id=? AND k=?', (str(payload.get('chat_id') or ''), str(payload.get('k') or '')))
            con.execute('INSERT INTO r32_state_revisions(shard_key,revision,event_id,updated_at) VALUES(?,?,?,?) ON CONFLICT(shard_key) DO UPDATE SET revision=excluded.revision,event_id=excluded.event_id,updated_at=excluded.updated_at', (key, rev, eid, time.time()))
            applied += 1
        con.commit()
        try: con.execute('PRAGMA wal_checkpoint(TRUNCATE)')
        except Exception: pass
    except Exception:
        try: con.rollback()
        except Exception: pass
        raise
    finally:
        con.close()
    return applied, stale


def _r68_local_runtime_dir() -> Path:
    return Path(os.getenv('LOCAL_RUNTIME_DIR', '/tmp/vys262_fast_local') or '/tmp/vys262_fast_local').resolve()


def _r68_local_snapshot_path() -> Path:
    raw = str(os.getenv('LOCAL_SQLITE_SNAPSHOT_FILE', '') or '').strip()
    return Path(raw).resolve() if raw else (_r68_local_runtime_dir() / 'state.sqlite3.gz')


def _r68_local_events_path() -> Path:
    raw = str(os.getenv('LOCAL_STATE_EVENT_JOURNAL_FILE', '') or '').strip()
    return Path(raw).resolve() if raw else (_r68_local_runtime_dir() / 'events.jsonl')


def _r68_restore_trace_path() -> Path:
    raw = str(os.getenv('LOCAL_RESTORE_TRACE_FILE', '') or '').strip()
    return Path(raw).resolve() if raw else (_r68_local_runtime_dir() / 'restore_trace.json')


def _r68_atomic_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + '.tmp')
    with open(tmp, 'w', encoding='utf-8') as fh:
        json.dump(payload, fh, ensure_ascii=False, separators=(',', ':'), default=str)
        fh.flush()
        try:
            os.fsync(fh.fileno())
        except Exception:
            pass
    os.replace(tmp, path)


def _r68_write_restore_trace_file(trace: dict) -> tuple[bool, str]:
    try:
        path = _r68_restore_trace_path()
        _r68_atomic_json(path, trace)
        return True, str(path)
    except Exception as exc:
        return False, f'{type(exc).__name__}: {str(exc)[:220]}'


def _r68_load_local_events(limit: int = 50000) -> tuple[list[dict], int]:
    """Read the bounded same-container JSONL tail. .1 is older, current is newer."""
    files = []
    current = _r68_local_events_path()
    rotated = Path(str(current) + '.1')
    if rotated.exists():
        files.append(rotated)
    if current.exists():
        files.append(current)
    out = []
    bad = 0
    cap = max(100, min(200000, int(limit or 50000)))
    for path in files:
        try:
            with open(path, 'r', encoding='utf-8') as fh:
                for line in fh:
                    if len(out) >= cap:
                        break
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        obj = json.loads(line)
                        ev = obj.get('event') if isinstance(obj, dict) and isinstance(obj.get('event'), dict) else obj
                        if _r32_event_valid(ev):
                            out.append(ev)
                        else:
                            bad += 1
                    except Exception:
                        bad += 1
        except Exception:
            bad += 1
        if len(out) >= cap:
            break
    return out, bad


def _restore_from_local_runtime_cache(target: Path) -> tuple[bool, str]:
    """R68 same-container recovery cache: local gzip SQLite + append-only state events.

    This layer is deliberately *not* treated as long-term durability because Render
    Free storage is ephemeral. It only helps when the process restarts while the
    container filesystem survives. Redis/MEGA remain the cross-deploy restore layers.
    """
    if _db_valid(target):
        return False, 'local main SQLite already valid; cache restore not needed'
    gz = _r68_local_snapshot_path()
    if not gz.exists() or gz.stat().st_size < 256:
        return False, f'local snapshot missing: {gz}'
    ok, detail = _install_gzip_db(gz, target)
    if not ok:
        return False, 'local snapshot invalid: ' + str(detail)[:320]
    events, bad = _r68_load_local_events(
        max(1000, min(200000, int(os.getenv('LOCAL_STATE_EVENT_RESTORE_MAX', '50000') or '50000')))
    )
    applied = stale = 0
    if events:
        applied, stale = _apply_r32_events(target, events)
    if not _db_valid(target):
        return False, 'local cache SQLite invalid after event replay'
    return True, (
        f'local-cache restore OK snapshot={gz.stat().st_size}B events={len(events)} '
        f'applied={applied} stale={stale} bad={bad} revision={_db_revision(target):.6f}'
    )


def _event_remote_upper_ns(remote: str) -> int | None:
    """Best-effort safe upper time/revision bound encoded by an immutable segment name."""
    name = str(remote or '').rsplit('/', 1)[-1]
    # R49+ direct archive: events_<min time_ns revision>_<max time_ns revision>_<digest>.json.gz
    m = re.match(r'^events_(\d{15,})_(\d{15,})_[0-9a-fA-F]+\.json\.gz$', name)
    if m:
        try:
            return int(m.group(2))
        except Exception:
            return None
    # Earlier R32 archive: events_YYYYMMDD_HHMMSS_micro_<id>_<id>.json.gz.
    # The filename timestamp is produced only after the batch was materialized, so it
    # is an upper bound for the event creation times inside that immutable segment.
    m = re.match(r'^events_(\d{8})_(\d{6})_(\d{6})_.*\.json\.gz$', name)
    if m:
        try:
            dt = datetime.strptime(''.join(m.groups()), '%Y%m%d%H%M%S%f').replace(tzinfo=timezone.utc)
            return int(dt.timestamp() * 1_000_000_000)
        except Exception:
            return None
    return None


def _replay_mega_event_segments(target: Path, root: str, mega_timeout: int) -> tuple[bool, str]:
    """Replay only the MEGA delta tail that can be newer than the full checkpoint.

    R55 removes the R54 O(N remote round-trip) startup.  The full SQLite carries the
    timestamp of the last committed logical state.  Every R32 event descriptor is
    created *after* its SQLite mutation returns, and immutable segment names contain
    either their max time_ns revision or a UTC creation timestamp.  Therefore a
    segment whose upper bound is comfortably older than the checkpoint cannot add
    state and may be skipped without downloading it.  A safety margin is replayed.
    Unknown/legacy filenames are never skipped.
    """
    event_root = root.rstrip('/') + '/events_r32'
    started = time.monotonic()
    try:
        found = _run(['mega-find', event_root, '--pattern=events_*.json.gz', '--type=f'], timeout=mega_timeout)
    except Exception as exc:
        return False, f'MEGA event listing {type(exc).__name__}: {str(exc)[:180]}'
    if found.returncode != 0:
        detail = (found.stderr or found.stdout or '').strip()
        low = detail.casefold()
        if any(x in low for x in ('not found', 'no such', 'does not exist', 'couldn')):
            return True, 'no MEGA event archive yet'
        return False, 'MEGA event listing failed: ' + detail[:220]
    rows = sorted({x.strip() for x in (found.stdout or '').splitlines() if x.strip().endswith('.json.gz')})
    if not rows:
        return True, 'no MEGA event segments'

    checkpoint_ts = float(_db_revision(target) or 0.0)
    margin_sec = max(2.0, min(120.0, float(os.getenv('MEGA_EVENT_REPLAY_MARGIN_SEC', '10') or '10')))
    safe_cutoff_ns = int(max(0.0, checkpoint_ts - margin_sec) * 1_000_000_000) if checkpoint_ts > 0 else 0
    needed: list[str] = []
    skipped = 0
    unknown = 0
    for remote in rows:
        upper = _event_remote_upper_ns(remote)
        if safe_cutoff_ns and upper is not None and int(upper) <= safe_cutoff_ns:
            skipped += 1
        else:
            needed.append(remote)
            if upper is None:
                unknown += 1
    print(
        f'[SPLIT FRONT] R56 MEGA event plan root={event_root} total={len(rows)} '
        f'skipped_checkpoint={skipped} replay={len(needed)} unknown={unknown} '
        f'checkpoint_ts={checkpoint_ts:.6f} margin={margin_sec:.1f}s',
        flush=True,
    )
    if not needed:
        return True, f'MEGA event replay tail empty total={len(rows)} skipped={skipped} checkpoint_ts={checkpoint_ts:.6f}'

    work = Path(tempfile.mkdtemp(prefix='v262_fast_mega_events_tail_'))
    download_workers = max(1, min(8, int(os.getenv('MEGA_EVENT_DOWNLOAD_WORKERS', '4') or '4')))

    def _download_one(idx_remote: tuple[int, str]):
        idx, remote = idx_remote
        name = remote.rsplit('/', 1)[-1]
        dl = work / f'e{idx:05d}'
        dl.mkdir(parents=True, exist_ok=True)
        t0 = time.monotonic()
        try:
            get = _run(['mega-get', remote, str(dl)], timeout=mega_timeout)
        except Exception as exc:
            return idx, remote, None, f'{type(exc).__name__}: {str(exc)[:180]}', time.monotonic() - t0
        if get.returncode != 0:
            return idx, remote, None, (get.stderr or get.stdout or 'mega-get failed')[:220], time.monotonic() - t0
        files = list(dl.rglob(name)) or list(dl.rglob('events_*.json.gz')) or list(dl.rglob('*.json.gz'))
        if not files:
            return idx, remote, None, 'downloaded event file missing', time.monotonic() - t0
        return idx, remote, files[0], '', time.monotonic() - t0

    downloaded: dict[int, Path] = {}
    try:
        print(f'[SPLIT FRONT] R56 MEGA event tail download start count={len(needed)} workers={download_workers}', flush=True)
        if download_workers == 1 or len(needed) == 1:
            results = [_download_one(x) for x in enumerate(needed)]
        else:
            results = []
            with ThreadPoolExecutor(max_workers=min(download_workers, len(needed)), thread_name_prefix='mega-tail') as ex:
                futs = [ex.submit(_download_one, x) for x in enumerate(needed)]
                for fut in as_completed(futs):
                    results.append(fut.result())
        slowest = 0.0
        for idx, remote, path, err, elapsed in results:
            slowest = max(slowest, float(elapsed or 0.0))
            if err or path is None:
                return False, f'MEGA event download failed {remote.rsplit("/",1)[-1]}: {err}'
            downloaded[int(idx)] = path
        print(
            f'[SPLIT FRONT] R56 MEGA event tail download done count={len(downloaded)} '
            f'slowest={slowest:.2f}s elapsed={time.monotonic()-started:.2f}s', flush=True,
        )

        applied = stale = segments = 0
        current_max = _r32_max_revision(target)
        for idx in range(len(needed)):
            file_path = downloaded[idx]
            name = file_path.name
            try:
                obj = json.loads(gzip.decompress(file_path.read_bytes()).decode('utf-8'))
                events = [ev for ev in ((obj or {}).get('events') or []) if _r32_event_valid(ev)]
            except Exception as exc:
                return False, f'MEGA event decode failed {name}: {type(exc).__name__}: {str(exc)[:150]}'
            if not events:
                return False, f'MEGA event segment has no valid events: {name}'
            a, st = _apply_r32_events(target, events)
            applied += a
            stale += st
            segments += 1
            current_max = max(current_max, max(int(ev.get('revision') or 0) for ev in events))
        if not _db_valid(target):
            return False, 'SQLite invalid after MEGA event replay'
        return True, (
            f'MEGA event replay tail total={len(rows)} skipped={skipped} segments={segments} '
            f'applied={applied} stale={stale} max_revision={current_max} '
            f'checkpoint_ts={checkpoint_ts:.6f} elapsed={time.monotonic()-started:.2f}s'
        )
    finally:
        shutil.rmtree(work, ignore_errors=True)


def _restore_from_mega_startup(target: Path) -> tuple[bool, str]:
    """OCH12.24 compatibility wrapper: exact compact_v80 only.

    No manifest, generation, pre_restore, legacy latest or MEGA tree scan is
    permitted from startup.  The actual fixed-object restore is centralized in
    _r80_compact_mega_compare_restore().
    """
    try:
        ok, detail, action = _r80_compact_mega_compare_restore(target, have_current=bool(_db_valid(target)))
    except Exception as exc:
        return False, f'compact_v80 exact recovery exception: {type(exc).__name__}: {str(exc)[:220]}'
    if action == 'RESTORE' and _db_valid(target):
        return True, str(detail)
    if _db_valid(target):
        return True, str(detail)
    return False, f'compact_v80 exact recovery unavailable: {detail}'

def _redis_render_url() -> str:
    return str(
        os.getenv('REDIS_URL')
        or os.getenv('RENDER_KEY_VALUE_URL')
        or os.getenv('KEY_VALUE_URL')
        or os.getenv('VALKEY_URL')
        or ''
    ).strip()


def _restore_from_redis_startup_once(target: Path) -> tuple[bool, str]:
    """OCH12.3: restore Redis daily FULL and replay its complete compressed TAIL.

    A FULL snapshot is never considered current by itself.  The metadata must carry
    the OCH12.3 tail contract and every indexed logical event after the exact FULL
    cutoff must be readable and valid.  Restoration is assembled in a temporary
    candidate DB first, so a stale/corrupt Redis image can never overwrite an
    already-valid local SQLite before MEGA fallback gets a chance.
    """
    url = _redis_render_url()
    if not url:
        return False, 'Redis URL not configured in Render'
    try:
        import redis as _redis_mod
    except Exception as exc:
        return False, f'redis package unavailable: {type(exc).__name__}: {str(exc)[:160]}'

    key = str(os.getenv('WORKER_REDIS_SNAPSHOT_KEY', 'vys262:bot_state:latest_gz') or 'vys262:bot_state:latest_gz').strip()
    meta_key = key + ':meta'
    prefix = str(os.getenv('WORKER_R32_STATE_EVENT_PREFIX', 'vys262:state_events:r32') or 'vys262:state_events:r32').strip()
    index_key = prefix + ':index'; head_key = prefix + ':head'
    max_events = max(1000, min(500000, int(os.getenv('REDIS_RESTORE_MAX_EVENTS', '200000') or '200000')))
    connect_timeout = max(0.5, min(10.0, float(os.getenv('REDIS_RESTORE_CONNECT_TIMEOUT_SEC', '3') or '3')))
    socket_timeout = max(2.0, min(60.0, float(os.getenv('REDIS_RESTORE_SOCKET_TIMEOUT_SEC', '15') or '15')))
    work = Path(tempfile.mkdtemp(prefix='v262_fast_startup_redis_'))
    gz_path = work / 'redis_latest.sqlite3.gz'
    candidate = work / 'redis_candidate.sqlite3'
    started = time.monotonic(); client = None; stage = 'CONNECT'
    try:
        print('[SPLIT FRONT] OCH12.24 REDIS stage=CONNECT', flush=True)
        client = _redis_mod.Redis.from_url(url, socket_connect_timeout=connect_timeout, socket_timeout=socket_timeout, health_check_interval=30)
        stage='PING'; print('[SPLIT FRONT] OCH12.24 REDIS stage=PING', flush=True)
        if not client.ping():
            return False, 'Redis PING returned false'
        stage='GET_FULL'; print('[SPLIT FRONT] OCH12.24 REDIS stage=GET_FULL', flush=True)
        payload = client.get(key)
        if not payload:
            return False, f'Redis daily FULL missing key={key}'
        max_bytes = max(1, min(128, int(os.getenv('WORKER_REDIS_SNAPSHOT_MAX_MB', '16') or '16'))) * 1024 * 1024
        if len(payload) > max_bytes:
            return False, f'Redis FULL too large: {len(payload)} > {max_bytes}'
        gz_path.write_bytes(bytes(payload))
        ok, install_detail = _install_gzip_db(gz_path, candidate)
        if not ok:
            return False, 'Redis FULL invalid: ' + str(install_detail)[:320]

        meta = {}
        try:
            stage='GET_META'; print('[SPLIT FRONT] OCH12.24 REDIS stage=GET_META', flush=True)
            raw_meta = client.get(meta_key)
            if isinstance(raw_meta, (bytes, bytearray)): raw_meta = raw_meta.decode('utf-8', 'replace')
            if raw_meta: meta = json.loads(raw_meta) if isinstance(raw_meta, str) else {}
        except Exception: meta = {}
        tail_schema = int((meta or {}).get('tail_schema') or 0)
        if tail_schema < 1 and not _bool('REDIS_ALLOW_LEGACY_FULL_RESTORE', False):
            return False, 'Redis FULL is legacy and has no complete TAIL contract; use HEAVY/MEGA fallback'
        try: cutoff = float((meta or {}).get('event_cutoff_score') or 0.0)
        except Exception: cutoff = 0.0
        if cutoff <= 0.0:
            return False, 'Redis FULL metadata has no valid event_cutoff_score'

        applied = stale = decoded = missing = invalid = 0; total_seen = 0
        replay_from = cutoff; stable_head = cutoff
        page = max(100, min(5000, int(os.getenv('REDIS_RESTORE_EVENT_PAGE', '1000') or '1000')))
        for _round in range(4):
            head = {}
            try:
                stage='GET_HEAD'; print('[SPLIT FRONT] OCH12.24 REDIS stage=GET_HEAD', flush=True)
                raw_head = client.get(head_key)
                if isinstance(raw_head, (bytes, bytearray)): raw_head = raw_head.decode('utf-8', 'replace')
                if raw_head: head = json.loads(raw_head) if isinstance(raw_head, str) else {}
            except Exception: head = {}
            try: head_score = max(replay_from, float((head or {}).get('score') or replay_from))
            except Exception: head_score = replay_from
            if head_score <= replay_from + 0.0000001:
                stable_head = replay_from
                break
            stage='TAIL_INDEX'; print('[SPLIT FRONT] OCH12.24 REDIS stage=TAIL_INDEX', flush=True)
            try: total = int(client.zcount(index_key, f'({replay_from}', head_score) or 0)
            except Exception: total = 0
            if total > max_events:
                return False, f'Redis TAIL too large for bounded replay: {total} > {max_events}'
            total_seen += total
            offset = 0; round_max_score = replay_from
            while offset < total:
                ids = client.zrangebyscore(index_key, f'({replay_from}', head_score, start=offset, num=page, withscores=True) or []
                if not ids: break
                id_text=[]; scores=[]
                for item in ids:
                    member,score=item
                    id_text.append(member.decode('utf-8','replace') if isinstance(member,(bytes,bytearray)) else str(member)); scores.append(float(score))
                stage='TAIL_MGET'; print(f'[SPLIT FRONT] OCH12.24 REDIS stage=TAIL_MGET batch={len(id_text)}', flush=True)
                raws = client.mget([f'{prefix}:event:{eid}' for eid in id_text]) or []
                events=[]
                for raw in raws:
                    if not raw:
                        missing += 1; continue
                    try:
                        b=bytes(raw) if isinstance(raw,(bytes,bytearray)) else str(raw).encode('utf-8')
                        if b[:2] == b'\x1f\x8b': b=gzip.decompress(b)
                        ev=json.loads(b.decode('utf-8'))
                        if _r32_event_valid(ev): events.append(ev); decoded += 1
                        else: invalid += 1
                    except Exception: invalid += 1
                if missing or invalid:
                    return False, f'Redis TAIL incomplete: missing={missing} invalid={invalid} after cutoff={cutoff:.6f}'
                if events:
                    a,st=_apply_r32_events(candidate,events); applied+=int(a or 0); stale+=int(st or 0)
                if scores: round_max_score=max(round_max_score,max(scores))
                offset += len(ids)
            if total and round_max_score + 0.0000001 < head_score:
                return False, f'Redis TAIL index gap: reached={round_max_score:.6f} head={head_score:.6f}'
            replay_from = head_score; stable_head = head_score
            try:
                raw_head2=client.get(head_key)
                if isinstance(raw_head2,(bytes,bytearray)): raw_head2=raw_head2.decode('utf-8','replace')
                head2=json.loads(raw_head2) if raw_head2 else {}
                head2_score=float((head2 or {}).get('score') or replay_from)
            except Exception: head2_score=replay_from
            if head2_score <= replay_from + 0.0000001: break
        else:
            return False, 'Redis TAIL kept advancing during startup; use HEAVY/MEGA for a stable restore'

        if not _db_valid(candidate):
            return False, 'SQLite invalid after Redis FULL+TAIL replay'
        # Force WAL content into the candidate main file before the atomic replace.
        try:
            con=sqlite3.connect(str(candidate),timeout=10)
            try: con.execute('PRAGMA wal_checkpoint(TRUNCATE)').fetchall()
            finally: con.close()
        except Exception as exc:
            return False, f'Redis candidate checkpoint failed: {type(exc).__name__}: {str(exc)[:180]}'

        local_rev = _db_revision(target) if _db_valid(target) else 0.0
        remote_freshness = max(float((meta or {}).get('revision') or 0.0), float((meta or {}).get('saved_at') or 0.0), float(stable_head or 0.0))
        if local_rev > remote_freshness + 0.000001:
            return False, f'valid local SQLite is newer than Redis FULL+TAIL local={local_rev:.6f} redis={remote_freshness:.6f}'
        final_tmp=target.with_suffix(target.suffix+'.redis-final.tmp')
        target.parent.mkdir(parents=True,exist_ok=True); shutil.copy2(candidate,final_tmp)
        if not _db_valid(final_tmp):
            return False,'Redis FULL+TAIL candidate failed final validation'
        os.replace(final_tmp,target)
        for suffix in ('-wal','-shm'):
            try: Path(str(target)+suffix).unlink(missing_ok=True)
            except Exception: pass
        final_rev=_db_revision(target); max_r32=_r32_max_revision(target)
        return True, (
            f'Redis startup FULL+TAIL OK snapshot={len(payload)}B meta_revision={float((meta or {}).get("revision") or 0.0):.6f} '
            f'event_cutoff={cutoff:.6f} tail_head={stable_head:.6f} events_tail={total_seen} replayed={decoded} '
            f'applied={applied} stale={stale} missing={missing} invalid={invalid} r32max={max_r32} '
            f'final_revision={final_rev:.6f} elapsed={time.monotonic()-started:.2f}s'
        )
    except Exception as exc:
        return False, f'Redis FULL+TAIL restore stage={stage} {type(exc).__name__}: {str(exc)[:320]}'
    finally:
        try:
            if client is not None: client.close()
        except Exception: pass
        shutil.rmtree(work, ignore_errors=True)



def _restore_from_redis_startup(target: Path) -> tuple[bool, str]:
    """OCH12.24 one logical Redis attempt with one transport reconnect.

    A server-side socket close does not mean the FULL is absent.  Retry once only for
    transport-level failures, using a completely new client.  Missing/corrupt data is
    never retried here and falls through to MEGA in the normal one-pass chain.
    """
    ok, detail = _restore_from_redis_startup_once(target)
    if ok:
        return ok, detail
    low = str(detail or '').casefold()
    transport = any(x in low for x in (
        'connectionerror', 'connection closed by server', 'timeout', 'timed out',
        'connection reset', 'broken pipe', 'server closed', 'eof',
    ))
    if not transport:
        return ok, detail
    print(f'[SPLIT FRONT] OCH12.24 Redis technical reconnect once after: {str(detail)[:260]}', flush=True)
    try:
        time.sleep(0.20)
    except Exception:
        pass
    ok2, detail2 = _restore_from_redis_startup_once(target)
    return ok2, ('technical reconnect: ' + str(detail2))[:900]


def _r32_legacy_descriptor(ev: object) -> bool:
    """Recognize the OCH12.18 compact-tail writer bug safely.

    12.18 could copy a durable outbox *descriptor* into compact_v80/tail.json.gz
    before materialization.  Such rows have event_id/revision/kind/key/ids but no
    schema=32 payload and therefore can never be replayed as state events.
    """
    if not isinstance(ev, dict):
        return False
    if int(ev.get('schema') or 0) == 32:
        return False
    return bool(
        str(ev.get('event_id') or '')
        and int(ev.get('revision') or 0) > 0
        and str(ev.get('kind') or '')
        and isinstance(ev.get('ids'), dict)
        and 'payload' not in ev
    )


def _redis_tail_events_after_cutoff(cutoff: float) -> tuple[list[dict], str]:
    """Recover canonical materialized R32 events without requiring Redis FULL.

    This is intentionally separate from _restore_from_redis_startup(): when the
    daily FULL key has expired/disappeared, the event stream may still contain
    the payloads needed to repair an OCH12.18 MEGA descriptor tail.
    """
    url = _redis_render_url()
    if not url:
        return [], 'Redis URL unavailable for tail repair'
    try:
        import redis as _redis_mod
    except Exception as exc:
        return [], f'redis package unavailable: {type(exc).__name__}: {str(exc)[:120]}'
    prefix = str(os.getenv('WORKER_R32_STATE_EVENT_PREFIX', 'vys262:state_events:r32') or 'vys262:state_events:r32').strip()
    index_key = prefix + ':index'
    max_events = max(1000, min(200000, int(os.getenv('REDIS_REPAIR_MAX_EVENTS', '50000') or '50000')))
    page = max(100, min(5000, int(os.getenv('REDIS_RESTORE_EVENT_PAGE', '1000') or '1000')))
    client = None
    try:
        client = _redis_mod.Redis.from_url(
            url,
            socket_connect_timeout=max(0.5, min(5.0, float(os.getenv('REDIS_RESTORE_CONNECT_TIMEOUT_SEC', '2') or '2'))),
            socket_timeout=max(2.0, min(20.0, float(os.getenv('REDIS_RESTORE_SOCKET_TIMEOUT_SEC', '8') or '8'))),
            health_check_interval=30,
        )
        if not client.ping():
            return [], 'Redis PING false during MEGA tail repair'
        try:
            total = int(client.zcount(index_key, f'({float(cutoff)}', '+inf') or 0)
        except Exception:
            total = 0
        if total > max_events:
            return [], f'Redis repair tail too large: {total} > {max_events}'
        out=[]; offset=0; missing=0; invalid=0
        while offset < total:
            members = client.zrangebyscore(index_key, f'({float(cutoff)}', '+inf', start=offset, num=page) or []
            if not members:
                break
            ids=[m.decode('utf-8','replace') if isinstance(m,(bytes,bytearray)) else str(m) for m in members]
            raws=client.mget([f'{prefix}:event:{eid}' for eid in ids]) or []
            for raw in raws:
                if not raw:
                    missing += 1
                    continue
                try:
                    b=bytes(raw) if isinstance(raw,(bytes,bytearray)) else str(raw).encode('utf-8')
                    if b[:2] == b'\x1f\x8b':
                        b=gzip.decompress(b)
                    ev=json.loads(b.decode('utf-8'))
                    if _r32_event_valid(ev):
                        out.append(ev)
                    else:
                        invalid += 1
                except Exception:
                    invalid += 1
            offset += len(members)
        return out, f'Redis repair events={len(out)} indexed={total} missing={missing} invalid={invalid}'
    except Exception as exc:
        return [], f'Redis tail repair {type(exc).__name__}: {str(exc)[:180]}'
    finally:
        try:
            if client is not None:
                client.close()
        except Exception:
            pass


def _r80_compact_mega_paths() -> tuple[str,str,str]:
    root=_canonical_mega_root().rstrip('/')
    base=root+'/compact_v80'
    return base+'/head.json', base+'/latest.sqlite3.gz', base+'/tail.json.gz'


def _r80_get_exact(remote: str, dest: Path, timeout: int) -> tuple[Path|None,str]:
    dest.mkdir(parents=True,exist_ok=True)
    try:
        proc=_run(['mega-get',str(remote),str(dest)],timeout=max(5,int(timeout)))
    except subprocess.TimeoutExpired:
        return None,f'timeout {timeout}s: {remote}'
    except Exception as exc:
        return None,f'{type(exc).__name__}: {str(exc)[:180]}'
    if proc.returncode!=0:
        return None,(proc.stderr or proc.stdout or 'mega-get failed').strip()[:240]
    name=str(remote).rstrip('/').rsplit('/',1)[-1]
    exact=dest/name
    if exact.is_file(): return exact,'ok'
    files=[x for x in dest.rglob('*') if x.is_file()]
    return (files[0],'ok') if len(files)==1 else (None,'downloaded file not found')


def _r80_compact_mega_compare_restore(target: Path, *, have_current: bool) -> tuple[bool,str,str]:
    """OCH12.7 bounded startup compare/restore. Never scans MEGA trees.

    Returns (ok, detail, action), where action is KEEP or RESTORE.
    If a verified Redis/local DB exists, only the tiny head.json is required to
    decide whether MEGA is newer. A missing/slow head never destroys that DB.
    """
    root=_canonical_mega_root()
    if not root:
        return False,'MEGA_BACKUP_DIR empty','KEEP'
    head_remote,latest_remote,tail_remote=_r80_compact_mega_paths()
    quick=bool(have_current and _db_valid(target))
    # OCH12.24: short compare timeouts are only safe when a verified local DB already exists.
    # On a cold restore MEGAcmd login can legitimately take tens of seconds; use the normal
    # recovery timeouts so removal of the obsolete deep fallback cannot strand startup.
    if quick:
        login_timeout=max(5,min(60,int(os.getenv('MEGA_STARTUP_COMPARE_LOGIN_TIMEOUT','12') or '12')))
        get_timeout=max(5,min(180,int(os.getenv('MEGA_STARTUP_COMPARE_GET_TIMEOUT','12') or '12')))
    else:
        # OCH12.24: one-pass cold recovery is bounded. A slow/unreachable MEGA must
        # not hold a Free Render boot for minutes; after this single attempt the
        # launcher falls through to an empty SQLite as explicitly requested.
        login_timeout=max(8,min(45,int(os.getenv('MEGA_STARTUP_RECOVERY_LOGIN_TIMEOUT','20') or '20')))
        get_timeout=max(10,min(60,int(os.getenv('MEGA_STARTUP_RECOVERY_GET_TIMEOUT','25') or '25')))
    logged,detail=_mega_login(login_timeout)
    if not logged:
        return (True,f'MEGA compare unavailable, current source kept: {detail[:220]}','KEEP') if quick else (False,detail,'KEEP')
    work=Path(tempfile.mkdtemp(prefix='ochnis124_mega_compact_'))
    try:
        head_path,head_detail=_r80_get_exact(head_remote,work/'head',get_timeout)
        head={}
        if head_path:
            try: head=json.loads(head_path.read_text(encoding='utf-8')) or {}
            except Exception as exc: head_detail=f'invalid head JSON: {type(exc).__name__}'
        local_db_rev=_db_revision(target) if _db_valid(target) else 0.0
        local_event_rev=_r32_max_revision(target) if _db_valid(target) else 0
        if isinstance(head,dict) and int(head.get('schema') or 0)>=80:
            mega_db_rev=float(head.get('full_db_revision') or 0.0)
            mega_event_rev=int(head.get('tail_max_revision') or head.get('full_event_revision') or 0)
            mega_newer=(mega_event_rev>local_event_rev) or (mega_event_rev<=local_event_rev and mega_db_rev>local_db_rev+0.000001)
            if quick and not mega_newer:
                return True,f'MEGA head checked; Redis/local kept local_db={local_db_rev:.6f} local_event={local_event_rev} mega_db={mega_db_rev:.6f} mega_event={mega_event_rev}','KEEP'
        elif quick:
            return True,f'MEGA compact head unavailable ({head_detail}); verified Redis/local kept; no tree scan','KEEP'

        # No usable current DB, or compact head proves MEGA is newer: exact latest only.
        latest_path,latest_detail=_r80_get_exact(latest_remote,work/'latest',get_timeout)
        if latest_path is None:
            return False,f'compact latest unavailable: {latest_detail}','KEEP'
        candidate=work/'candidate.sqlite3'
        ok,install_detail=_install_gzip_db(latest_path,candidate)
        if not ok:
            return False,f'compact latest invalid: {install_detail}','KEEP'
        head_valid=bool(isinstance(head,dict) and int(head.get('schema') or 0)>=80)
        tail_count=int((head or {}).get('tail_count') or 0) if head_valid else 0
        expected_tail_max=int((head or {}).get('tail_max_revision') or 0) if head_valid else 0
        tail_applied=0
        # OCH12.24: on a cold restore always inspect tail.json.gz even when HEAD says
        # tail_count=0.  A crash can happen after TAIL promotion and before HEAD; HEAD
        # is the commit record, but it must not make an already-durable newer TAIL invisible.
        tail_path,tail_detail=_r80_get_exact(tail_remote,work/'tail',get_timeout)
        if tail_path is None:
            if (not head_valid) or tail_count>0 or expected_tail_max>_r32_max_revision(candidate):
                return False,f'compact tail/head incomplete: {tail_detail}','KEEP'
        else:
            try:
                obj=json.loads(gzip.decompress(tail_path.read_bytes()).decode('utf-8')) or {}
                raw_events=list(obj.get('events') or [])
            except Exception as exc:
                return False,f'compact tail decode {type(exc).__name__}: {str(exc)[:160]}','KEEP'
            tail_base_db=float(obj.get('full_db_revision') or 0.0)
            candidate_db_before_tail=_db_revision(candidate)
            if tail_base_db and candidate_db_before_tail and abs(tail_base_db-candidate_db_before_tail)>0.000001:
                return False,f'compact tail belongs to different FULL tail_db={tail_base_db:.6f} latest_db={candidate_db_before_tail:.6f}','KEEP'

            # OCH12.24 repair path for the 12.18 writer bug.  12.18 could write
            # durable outbox descriptors into tail.json.gz.  They increased
            # tail_max_revision/tail_count but had no payload, so the old reader
            # rejected the same immutable backup forever in RECOVERY SAFE WAIT.
            valid_events=[ev for ev in raw_events if _r32_event_valid(ev)]
            legacy_desc=[ev for ev in raw_events if _r32_legacy_descriptor(ev)]
            invalid_other=[ev for ev in raw_events if not _r32_event_valid(ev) and not _r32_legacy_descriptor(ev)]
            if invalid_other:
                return False,f'compact tail contains {len(invalid_other)} unknown invalid rows; refusing unsafe recovery','KEEP'
            if tail_count and len(raw_events)<tail_count:
                return False,f'compact tail physically incomplete {len(raw_events)} < {tail_count}','KEEP'

            repair_detail=''
            merged={str(ev.get('event_id')):ev for ev in valid_events if str(ev.get('event_id') or '')}
            if legacy_desc:
                cutoff=float(obj.get('full_event_cutoff_score') or (head or {}).get('full_event_cutoff_score') or 0.0)
                redis_events,repair_detail=_redis_tail_events_after_cutoff(cutoff)
                for ev in redis_events:
                    eid=str(ev.get('event_id') or '')
                    if eid:
                        merged[eid]=ev
            events=sorted(merged.values(),key=lambda x:(int(x.get('revision') or 0),str(x.get('event_id') or '')))
            if events:
                a,_st=_apply_r32_events(candidate,events); tail_applied=int(a)

            tail_obj_max=int(obj.get('max_revision') or 0)
            claimed_tail_max=max(expected_tail_max,tail_obj_max)
            recovered_max=_r32_max_revision(candidate)
            degraded_desc=0
            if claimed_tail_max and recovered_max<claimed_tail_max:
                if legacy_desc:
                    # The missing ceiling is exactly the known 12.18 descriptor
                    # bug. Waiting cannot repair an immutable object. Accept the
                    # newest replayable state, but make degradation explicit.
                    repaired_ids={str(ev.get('event_id') or '') for ev in events}
                    degraded_desc=sum(1 for ev in legacy_desc if str(ev.get('event_id') or '') not in repaired_ids)
                else:
                    return False,f'compact tail revision incomplete {recovered_max} < {claimed_tail_max}','KEEP'
            if legacy_desc:
                trace_note=(
                    f'OCH12.24 repaired legacy descriptor tail raw={len(raw_events)} valid={len(valid_events)} '
                    f'descriptors={len(legacy_desc)} unrecovered={degraded_desc}; {repair_detail}'
                )
            else:
                trace_note=''
        if not _db_valid(candidate): return False,'compact candidate invalid after tail','KEEP'
        cand_db=_db_revision(candidate); cand_ev=_r32_max_revision(candidate)
        if quick and ((cand_ev<local_event_rev) or (cand_ev==local_event_rev and cand_db<local_db_rev-0.000001)):
            return True,f'MEGA candidate older; current kept candidate_db={cand_db:.6f} event={cand_ev}','KEEP'
        final_tmp=target.with_suffix(target.suffix+'.r80-mega.tmp'); target.parent.mkdir(parents=True,exist_ok=True); shutil.copy2(candidate,final_tmp)
        if not _db_valid(final_tmp): return False,'compact final validation failed','KEEP'
        os.replace(final_tmp,target)
        for suffix in ('-wal','-shm'):
            try: Path(str(target)+suffix).unlink(missing_ok=True)
            except Exception: pass
        _note = ((' · ' + trace_note) if 'trace_note' in locals() and trace_note else '')
        return True,f'MEGA compact restore OK db={_db_revision(target):.6f} event={_r32_max_revision(target)} tail_applied={tail_applied}{_note}','RESTORE'
    finally:
        try: _run(['mega-logout'],timeout=8)
        except Exception: pass
        try: _run(['mega-quit'],timeout=5)
        except Exception: pass
        shutil.rmtree(work,ignore_errors=True)

def _scrub_fast_runtime_mega_credentials() -> None:
    """R71: park FAST MEGA execution without deleting credentials.

    очнись_4 can route selected heavy modes back to Render #1 at runtime.  The
    credentials therefore stay in the process environment, while MEGA execution
    remains disabled by default until the owner explicitly selects R1 FAST.
    """
    os.environ['MEGA_ENABLED'] = '0'
    os.environ['MEGA_AUTORESTORE'] = '0'
    os.environ['FAST_RUNTIME_MEGA_DISABLED'] = '1'


def _och1224_hard_release_mega_processes() -> dict:
    """Best-effort MEGAcmd cleanup inside this isolated Render container.

    mega-quit is requested first.  Orphan mega-cmd-server / mega-exec children are
    then terminated so a failed recovery cannot leave 40+ MB resident into runtime.
    """
    out={'quit':False,'term':0,'kill':0}
    try:
        q=_run(['mega-quit'], timeout=5)
        out['quit']=bool(getattr(q,'returncode',1)==0)
    except Exception:
        pass
    try:
        me=os.getpid()
        victims=[]
        proc=Path('/proc')
        for ent in proc.iterdir():
            if not ent.name.isdigit() or int(ent.name)==me:
                continue
            try:
                name=(ent/'comm').read_text(errors='ignore').strip()
            except Exception:
                name=''
            if name in {'mega-cmd-server','mega-exec'}:
                victims.append(int(ent.name))
        for pid in victims:
            try: os.kill(pid, 15); out['term']+=1
            except Exception: pass
        if victims:
            time.sleep(0.15)
        for pid in victims:
            if Path(f'/proc/{pid}').exists():
                try: os.kill(pid, 9); out['kill']+=1
                except Exception: pass
    except Exception:
        pass
    return out


def _och1220_release_boot_memory() -> dict:
    """Return recovery-only allocations to the OS before importing the full bot.

    Remote restore can temporarily allocate compressed snapshots, JSON tails and
    MEGAcmd/Redis client objects.  On a 512 MB Render container we do not want
    that BOOT peak to become the runtime baseline through allocator retention.
    """
    result = {'gc': 0, 'malloc_trim': False, 'redis_modules_unloaded': 0}
    try:
        # If Redis is disabled for normal runtime, recovery was its only purpose.
        # Drop imported redis modules before bot.py is loaded; they can be imported
        # again later if runtime configuration changes.
        if not _bool('REDIS_ENABLED', False):
            import sys
            names = [n for n in list(sys.modules) if n == 'redis' or n.startswith('redis.')]
            for n in names:
                sys.modules.pop(n, None)
            result['redis_modules_unloaded'] = len(names)
    except Exception:
        pass
    try:
        import gc
        result['gc'] = int(gc.collect() or 0)
    except Exception:
        pass
    try:
        import ctypes
        libc = ctypes.CDLL(None)
        fn = getattr(libc, 'malloc_trim', None)
        if fn is not None:
            fn.argtypes = [ctypes.c_size_t]
            fn.restype = ctypes.c_int
            result['malloc_trim'] = bool(fn(0))
    except Exception:
        pass
    try:
        result['mega_cleanup'] = _och1224_hard_release_mega_processes()
    except Exception:
        pass
    return result


def main():
    server = _start_boot_port()
    render_host = str(os.getenv('RENDER_EXTERNAL_HOSTNAME', '') or '').strip()
    if render_host:
        render_base = 'https://' + render_host
        for legacy_key in ('APP_URL', 'WEBHOOK_URL'):
            legacy_value = str(os.getenv(legacy_key, '') or '').strip().rstrip('/')
            if legacy_value and legacy_value != render_base:
                print(
                    f'[SPLIT FRONT] R56 ENV WARN {legacy_key} points to another host; '
                    f'ignoring legacy value in favor of Render host={render_base}',
                    flush=True,
                )
    target = _db_path()
    started = time.time()

    # OCH12.24 ONE-PASS recovery. Render Free normally loses the local filesystem
    # on a redeploy, so every source is tried at most once and there is NEVER a
    # RECOVERY SAFE WAIT loop. Recovery ignores REDIS_ENABLED / MEGA_ENABLED: the
    # switches still control normal runtime, but disaster recovery uses any source
    # whose credentials/address are physically present. The first validated source
    # wins. If none is available, create a normal empty SQLite and start.
    local_found = bool(target.exists())
    local_valid_before = bool(_db_valid(target)) if local_found else False
    local_revision_before = _db_revision(target, validated=True) if local_valid_before else 0.0
    trace = {
        'schema': 5,
        'policy': 'OCH12.24_ONE_PASS_THEN_EMPTY',
        'started_at': started,
        'internal_config': INTERNAL_CONFIG_VERSION,
        'local_found': local_found,
        'local_valid_before': local_valid_before,
        'local_revision_before': local_revision_before,
        'local_probe': 'quick_check_once' if local_found else 'missing_no_sqlite_open',
        'local_cache_contacted': False,
        'redis_contacted': False,
        'mega_contacted': False,
        'heavy_contacted': False,
        'base_source': 'LOCAL_SQLITE_FAST' if local_valid_before else '',
        'recovery_one_pass': True,
    }
    try:
        current_valid = bool(local_valid_before)

        # 1) Same-container compressed cache, only when the file actually exists.
        local_gz = _r68_local_snapshot_path()
        if not current_valid and local_gz.exists() and local_gz.stat().st_size >= 256:
            trace['local_cache_contacted'] = True
            ok, detail = _restore_from_local_runtime_cache(target)
            trace['local_cache_ok'] = bool(ok)
            trace['local_cache_detail'] = str(detail)[:900]
            print(f'[SPLIT FRONT] OCH12.24 one-pass local-cache ok={int(bool(ok))} detail={str(detail)[:500]}', flush=True)
            if ok and _db_valid(target):
                current_valid = True
                trace['base_source'] = 'LOCAL_RUNTIME_CACHE_FAST'
        elif not current_valid:
            trace['local_cache_ok'] = False
            trace['local_cache_detail'] = f'absent: {local_gz}'
            print('[SPLIT FRONT] OCH12.24 local cache absent', flush=True)

        # 2) Redis FULL+TAIL exactly once whenever a URL exists, even when
        # REDIS_ENABLED=0 / REDIS_START_ENABLED=0 in Render. Runtime remains OFF.
        redis_url_present = bool(_redis_render_url())
        trace['redis_render_enabled'] = bool(_bool('REDIS_ENABLED', False))
        trace['redis_url_present'] = redis_url_present
        if not current_valid and redis_url_present:
            trace['redis_contacted'] = True
            print('[SPLIT FRONT] OCH12.24 one-pass Redis FULL+TAIL start (recovery ignores REDIS_ENABLED)', flush=True)
            try:
                ok, detail = _restore_from_redis_startup(target)
            except Exception as exc:
                ok, detail = False, f'{type(exc).__name__}: {exc}'
            trace['redis_ok'] = bool(ok)
            trace['redis_detail'] = str(detail)[:900]
            print(f'[SPLIT FRONT] OCH12.24 one-pass Redis ok={int(bool(ok))} detail={str(detail)[:700]}', flush=True)
            if ok and _db_valid(target):
                current_valid = True
                trace['base_source'] = 'REDIS_ONE_PASS'
        elif not current_valid:
            trace['redis_ok'] = False
            trace['redis_detail'] = 'Redis URL absent'

        # 3) MEGA compact exactly once whenever root+credentials exist, even when
        # MEGA_ENABLED=0. No compare loop, no tree scan, no retry.
        mega_root = _canonical_mega_root()
        mega_creds = bool(str(os.getenv('MEGA_SESSION', '') or '').strip() or
                          (str(os.getenv('MEGA_EMAIL', '') or '').strip() and str(os.getenv('MEGA_PASSWORD', '') or '')))
        trace['mega_render_enabled'] = bool(_bool('MEGA_ENABLED', False))
        trace['mega_root_present'] = bool(mega_root)
        trace['mega_credentials_present'] = bool(mega_creds)
        if not current_valid and mega_root and mega_creds:
            trace['mega_contacted'] = True
            try:
                ok, detail, action = _r80_compact_mega_compare_restore(target, have_current=False)
            except Exception as exc:
                ok, detail, action = False, f'{type(exc).__name__}: {exc}', 'KEEP'
            trace['mega_ok'] = bool(ok)
            trace['mega_detail'] = str(detail)[:900]
            trace['mega_action'] = str(action)
            print(f'[SPLIT FRONT] OCH12.24 one-pass MEGA ok={int(bool(ok))} action={action} detail={str(detail)[:700]}', flush=True)
            if ok and action == 'RESTORE' and _db_valid(target):
                current_valid = True
                trace['base_source'] = 'MEGA_COMPACT_ONE_PASS'
        elif not current_valid:
            trace['mega_ok'] = False
            trace['mega_detail'] = 'MEGA root/credentials absent'
            trace['mega_action'] = 'SKIP'

        # 4) User-requested terminal fallback: never wait/retry forever.
        if not current_valid:
            empty_ok, empty_detail = _ensure_empty_db(target)
            trace['empty_init_attempted'] = True
            trace['empty_init_ok'] = bool(empty_ok)
            trace['empty_init_detail'] = str(empty_detail)[:500]
            print(f'[SPLIT FRONT] OCH12.24 recovery sources exhausted -> EMPTY SQLite ok={int(bool(empty_ok))} detail={str(empty_detail)[:300]}', flush=True)
            if not empty_ok or not _db_valid(target):
                raise RuntimeError('OCH12.24 could not create fallback empty SQLite: ' + str(empty_detail))
            current_valid = True
            trace['base_source'] = 'EMPTY_INIT_AFTER_ONE_PASS'

        os.environ['SPLIT_PREBOOT_EMPTY_INIT_R1220'] = '1' if trace.get('base_source') == 'EMPTY_INIT_AFTER_ONE_PASS' else '0'

        # Re-apply packaged runtime settings: Redis remains OFF regardless of stale Render tunables.
        install_internal_runtime_config('front')
        # R71/очнись_4: keep Google/MEGA credentials available for the runtime
        # R1/R2 owner switch.  MEGA itself is still parked OFF until R1 is selected.
        _scrub_fast_runtime_mega_credentials()

        final_valid = bool(current_valid and target.exists())
        if not final_valid:
            final_valid = bool(_db_valid(target))
        if final_valid:
            revision = _db_revision(target, validated=True)
            trace['final_revision'] = revision
            trace['local_valid_after'] = True
            os.environ['SPLIT_PREBOOT_AUTHORITATIVE_R20'] = '1'
            os.environ['SPLIT_PREBOOT_REVISION_R20'] = str(revision)
        else:
            trace['final_revision'] = 0.0
            trace['local_valid_after'] = False
            # OCH12.11: start_front remains authoritative even if empty DB init itself
            # failed, so legacy bot.main() never performs a second MEGA scan/login.
            os.environ['SPLIT_PREBOOT_AUTHORITATIVE_R20'] = '1'
            os.environ['SPLIT_PREBOOT_REVISION_R20'] = '0'

        trace['runtime_mega_credentials_scrubbed'] = False
        trace['runtime_heavy_credentials_parked_for_r71'] = True
        
        try:
            from runtime_config import redis_runtime_state
            trace['redis_runtime_enabled'] = bool((redis_runtime_state() or {}).get('enabled'))
        except Exception:
            trace['redis_runtime_enabled'] = False
        trace['base_revision'] = float(trace.get('local_revision_before') or 0.0)
        if trace.get('base_source') in {'REDIS', 'REDIS_FAST', 'MEGA', 'MEGA_COMPACT', 'MEGA_COMPACT_FALLBACK', 'REDIS_ONE_PASS', 'MEGA_COMPACT_ONE_PASS', 'EMPTY_INIT_AFTER_ONE_PASS', 'LOCAL_RUNTIME_CACHE', 'LOCAL_RUNTIME_CACHE_FAST', 'LOCAL_SQLITE_FAST'}:
            trace['base_revision'] = float(trace.get('final_revision') or 0.0)
        trace['local_found'] = bool(trace.get('local_found'))
        trace['local_valid'] = bool(trace.get('local_valid_before'))
        trace['local_revision'] = float(trace.get('local_revision_before') or 0.0)
        trace['redis_full_attempted'] = bool(trace.get('redis_contacted'))
        trace['redis_full_ok'] = bool(trace.get('redis_ok'))
        trace['redis_full_detail'] = str(trace.get('redis_detail') or '')
        trace['elapsed_ms'] = round((time.time() - started) * 1000.0, 1)
        trace['finished_at'] = time.time()
        trace_file_ok, trace_file_detail = _r68_write_restore_trace_file(trace)
        trace['local_trace_file_ok'] = bool(trace_file_ok)
        trace['local_trace_file'] = str(trace_file_detail)[:500]
        trace_json = json.dumps(trace, ensure_ascii=False, separators=(',', ':'))
        os.environ['R68_RESTORE_TRACE_JSON'] = trace_json
        # Compatibility read-only alias for pre-R68 watcher code during rolling deploy.
        os.environ['R49_RESTORE_TRACE_JSON'] = trace_json
        print('[RESTORE TRACE R68]', trace_json, flush=True)
        boot_mem_release = _och1220_release_boot_memory()
        print(f'[SPLIT FRONT] OCH12.24 boot memory release {boot_mem_release}', flush=True)

        # R55 rolling-deploy handoff: keep the preboot gateway accepting/spooling
        # Telegram updates while the large modular runtime is imported.  Only after
        # every handler/route exists do we release PORT and enter main(), whose first
        # action binds the real Waitress server.  This removes the old live-but-503 gap.
        os.environ['PREBOOT_WEBHOOK_SPOOL_FILE'] = str(_PREBOOT_SPOOL_PATH)
        os.environ['BOT_DEFER_MAIN_R54'] = '1'
        runtime_ns = runpy.run_path(str(Path(__file__).with_name('bot.py')), run_name='__main__')
        os.environ.pop('BOT_DEFER_MAIN_R54', None)
        runtime_main = runtime_ns.get('main')
        if not callable(runtime_main):
            raise RuntimeError('R54 bot runtime loaded without callable main()')
        print(f'[SPLIT FRONT] R56 runtime imported; switching preboot -> Waitress; captured={_PREBOOT_CAPTURED}', flush=True)
        _stop_boot_port(server)
        time.sleep(0.05)
        runtime_main()
    finally:
        try: _stop_boot_port(server)
        except Exception: pass


if __name__ == '__main__':
    main()
# v262
