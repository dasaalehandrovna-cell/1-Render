# v262
#!/usr/bin/env python3
"""Render #1 launcher: restore its SQLite directly from MEGA, then run FAST.

R50 root-fix policy:
- startup/restart recovery belongs to FAST and contacts MEGA directly;
- Redis and HEAVY are not part of startup recovery;
- after startup, FAST logs out of MEGA and removes MEGA credentials from its process;
- all normal runtime MEGA work is therefore delegated to Render #2 / HEAVY.
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
        payload = {'ok': status < 400, 'role': 'front', 'phase': 'restoring_from_mega'}
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


def _manifest_generation_remote(root: str, tmpdir: Path, mega_timeout: int) -> tuple[str, str]:
    """Return manifest-selected immutable generation, if one exists."""
    manifest_remote = root.rstrip('/') + '/database/current_manifest.json'
    md = tmpdir / ('manifest_' + str(abs(hash(root))))
    md.mkdir(exist_ok=True)
    try:
        mg = _run(['mega-get', manifest_remote, str(md)], timeout=mega_timeout)
    except Exception as exc:
        return '', f'{manifest_remote}: {type(exc).__name__}'
    if mg.returncode != 0:
        detail = (mg.stderr or mg.stdout or 'mega-get failed').strip()
        return '', f'{manifest_remote}: {detail[:180]}'
    rows = list(md.rglob('current_manifest.json')) + list(md.rglob('*.json'))
    if not rows:
        return '', f'{manifest_remote}: downloaded manifest missing'
    try:
        payload = json.loads(rows[0].read_text(encoding='utf-8')) or {}
    except Exception as exc:
        return '', f'{manifest_remote}: invalid JSON {type(exc).__name__}'
    generation_remote = str(payload.get('remote_generation') or '').strip()
    if generation_remote and not generation_remote.startswith('/'):
        generation_remote = root.rstrip('/') + '/database/generations/' + generation_remote.rsplit('/', 1)[-1]
    if not generation_remote and payload.get('generation'):
        generation_remote = root.rstrip('/') + '/database/generations/' + str(payload.get('generation')).rsplit('/', 1)[-1]
    if not generation_remote:
        return '', f'{manifest_remote}: no generation pointer'
    # R58: a stale manifest must never escape the Render-configured MEGA root.
    if not _mega_remote_within_root(generation_remote, root):
        return '', f'{manifest_remote}: rejected external generation pointer={generation_remote}'
    return generation_remote, f'{manifest_remote}: generation={generation_remote.rsplit("/",1)[-1]}'


def _discover_generation_remotes(root: str, mega_timeout: int, limit: int = 3) -> tuple[list[str], str]:
    """Find newest immutable generations when current_manifest is absent/stale."""
    generations = root.rstrip('/') + '/database/generations'
    try:
        found = _run(['mega-find', generations, '--pattern=generation_*.sqlite3.gz', '--type=f'], timeout=mega_timeout)
    except Exception as exc:
        return [], f'{generations}: {type(exc).__name__}'
    if found.returncode != 0:
        detail = (found.stderr or found.stdout or 'mega-find failed').strip()
        return [], f'{generations}: {detail[:180]}'
    rows = sorted({x.strip() for x in (found.stdout or '').splitlines() if x.strip().endswith('.sqlite3.gz')}, reverse=True)
    return rows[:max(1, int(limit))], f'{generations}: found={len(rows)}'


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
    """Restore FAST from MEGA once per process start, then leave MEGA completely.

    R58 strict-root recovery.  FAST is allowed to inspect only MEGA_BACKUP_DIR
    supplied by Render.  No legacy/default roots are consulted and a manifest
    pointer outside that root is rejected.
      configured latest -> configured manifest generation -> configured generation scan.
    """
    roots = _startup_mega_roots()
    if not roots:
        return False, 'MEGA_ENABLED=1 but MEGA_BACKUP_DIR is empty; strict root policy refuses fallback'
    canonical_root = roots[0]
    mega_timeout = max(45, min(900, int(os.getenv('MEGA_TIMEOUT', '120') or '120')))
    login_timeout = max(45, min(300, int(os.getenv('MEGA_LOGIN_TIMEOUT', '120') or '120')))
    print(f'[SPLIT FRONT] R58 MEGA STRICT ROOT={canonical_root} login start timeout={login_timeout}s', flush=True)
    logged, detail = _mega_login(login_timeout)
    print(f'[SPLIT FRONT] R56 MEGA login done ok={int(bool(logged))} detail={detail[:220]}', flush=True)
    if not logged:
        return False, detail
    tmpdir = Path(tempfile.mkdtemp(prefix='v262_fast_startup_mega_'))
    errors: list[str] = []
    discovery: list[str] = []
    candidate_index = 0

    def try_remote(source_root: str, remote: str, source_kind: str) -> tuple[bool, str]:
        nonlocal candidate_index
        candidate_index += 1
        idx = candidate_index
        dl = tmpdir / f'd{idx}'
        dl.mkdir(exist_ok=True)
        print(f'[SPLIT FRONT] R56 MEGA candidate start idx={idx} kind={source_kind} remote={remote}', flush=True)
        t0 = time.monotonic()
        try:
            get = _run(['mega-get', remote, str(dl)], timeout=mega_timeout)
        except Exception as exc:
            err = f'{remote}: {type(exc).__name__}: {str(exc)[:160]}'
            errors.append(err)
            print(f'[SPLIT FRONT] R56 MEGA candidate fail idx={idx} elapsed={time.monotonic()-t0:.2f}s {err}', flush=True)
            return False, err
        if get.returncode != 0:
            detail2 = (get.stderr or get.stdout or 'mega-get failed').strip()
            err = f'{remote}: {detail2[:180]}'
            errors.append(err)
            print(f'[SPLIT FRONT] R56 MEGA candidate miss idx={idx} elapsed={time.monotonic()-t0:.2f}s detail={detail2[:220]}', flush=True)
            return False, err
        candidates_local = list(dl.rglob('*.sqlite3.gz')) + [x for x in dl.rglob('*.gz') if x.name != 'latest_bot_state.sqlite3.gz']
        if not candidates_local:
            err = f'{remote}: download contains no SQLite gzip'
            errors.append(err)
            return False, err
        for gz_path in candidates_local:
            ok, install_detail = _install_gzip_db(gz_path, target)
            if not ok:
                errors.append(f'{remote}: {install_detail}')
                continue
            replay_parts: list[str] = []
            # R58: replay deltas only from the same configured root as the base.
            for event_root in [canonical_root]:
                print(f'[SPLIT FRONT] R56 MEGA event replay start root={event_root}', flush=True)
                replay_ok, replay_detail = _replay_mega_event_segments(target, event_root, mega_timeout)
                replay_parts.append(f'{event_root}: {replay_detail}')
                print(f'[SPLIT FRONT] R56 MEGA event replay done root={event_root} ok={int(bool(replay_ok))} detail={replay_detail[:260]}', flush=True)
                if not replay_ok:
                    errors.append(f'{remote}: base installed but event replay failed at {event_root}: {replay_detail}')
                    return False, errors[-1]
            source_note = 'configured-root'
            detail3 = (
                f'MEGA startup restore OK source={source_note}/{source_kind} root={source_root} '
                f'remote={remote}; {install_detail}; ' + '; '.join(replay_parts)
            )[:1200]
            print(f'[SPLIT FRONT] R56 MEGA candidate success idx={idx} elapsed={time.monotonic()-t0:.2f}s', flush=True)
            return True, detail3
        return False, errors[-1] if errors else f'{remote}: invalid downloaded snapshot'

    try:
        for root_no, root in enumerate(roots, 1):
            print(f'[SPLIT FRONT] R58 MEGA root start {root_no}/{len(roots)} root={root}', flush=True)

            # HEAVY's active runtime checkpoint writer promotes this object on every
            # successful full snapshot.  It is therefore the freshest control file
            # in the current split architecture and must be tried before a possibly
            # stale immutable-generation manifest left by an older release.
            latest = root.rstrip('/') + '/database/latest_bot_state.sqlite3.gz'
            ok, done = try_remote(root, latest, 'latest')
            if ok:
                return True, done

            generation_remote, manifest_detail = _manifest_generation_remote(root, tmpdir, mega_timeout)
            discovery.append(manifest_detail)
            print(f'[SPLIT FRONT] R55 manifest root={root} detail={manifest_detail[:260]}', flush=True)
            if generation_remote:
                ok, done = try_remote(root, generation_remote, 'manifest-fallback')
                if ok:
                    return True, done

            generations, find_detail = _discover_generation_remotes(root, mega_timeout)
            discovery.append(find_detail)
            print(f'[SPLIT FRONT] R55 generation scan root={root} detail={find_detail[:260]}', flush=True)
            for remote in generations:
                ok, done = try_remote(root, remote, 'generation-scan')
                if ok:
                    return True, done

        useful_discovery = [x for x in discovery if x and not _mega_missing(x)]
        tail = errors[-6:] + useful_discovery[-3:]
        return False, ('; '.join(tail) or 'no valid MEGA snapshot/generation found inside configured MEGA_BACKUP_DIR')[:1200]
    finally:
        try: _run(['mega-logout'], timeout=20)
        except Exception: pass
        try: _run(['mega-quit'], timeout=12)
        except Exception: pass
        shutil.rmtree(tmpdir, ignore_errors=True)


def _scrub_fast_runtime_mega_credentials() -> None:
    for key in ('MEGA_SESSION', 'MEGA_EMAIL', 'MEGA_PASSWORD'):
        os.environ.pop(key, None)
    os.environ['MEGA_ENABLED'] = '0'
    os.environ['MEGA_AUTORESTORE'] = '0'
    os.environ['FAST_RUNTIME_MEGA_DISABLED'] = '1'


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
    trace = {
        'schema': 2,
        'policy': 'R56_RENDER_MASTER_SWITCHES',
        'started_at': started,
        'internal_config': INTERNAL_CONFIG_VERSION,
        'local_found': target.exists(),
        'local_valid_before': _db_valid(target),
        'local_revision_before': _db_revision(target),
        'mega_contacted': False,
        'mega_ok': False,
        'mega_detail': '',
        'redis_contacted': False,
        'heavy_contacted': False,
        'base_source': '',
    }
    try:
        had_valid_local_before_restore = bool(trace['local_valid_before'])
        mega_master_enabled = _bool('MEGA_ENABLED', True)
        trace['mega_master_enabled'] = bool(mega_master_enabled)
        if not mega_master_enabled:
            trace['mega_contacted'] = False
            trace['mega_ok'] = False
            trace['mega_detail'] = 'MEGA disabled by Render MEGA_ENABLED=0'
            trace['base_source'] = 'LOCAL_SQLITE' if had_valid_local_before_restore else 'EMPTY_INIT_MEGA_DISABLED'
            print('[SPLIT FRONT] R56 MEGA disabled by MEGA_ENABLED=0; startup restore skipped', flush=True)
        else:
            strict_root = _canonical_mega_root()
            if not strict_root:
                raise RuntimeError('R58: MEGA_ENABLED=1 requires MEGA_BACKUP_DIR in Render; no fallback root is allowed')
            trace['mega_strict_root'] = strict_root
            print(f'[SPLIT FRONT] R58 MEGA STRICT ROOT locked to {strict_root}', flush=True)
            trace['mega_contacted'] = True
            max_attempts = max(1, min(12, int(os.getenv('SPLIT_RESTORE_BOOT_ATTEMPTS', '3') or '3')))
            retry_sec = max(2, min(60, int(os.getenv('SPLIT_RESTORE_RETRY_SEC', '5') or '5')))
            last_detail = ''
            for attempt in range(1, max_attempts + 1):
                ok, detail = _restore_from_mega_startup(target)
                last_detail = str(detail)
                trace['mega_ok'] = bool(ok)
                trace['mega_detail'] = last_detail[:700]
                trace['mega_attempt'] = attempt
                trace['mega_attempts_max'] = max_attempts
                print(f'[SPLIT FRONT] R56 FAST MEGA startup restore attempt={attempt}/{max_attempts}:', ok, detail, flush=True)
                if ok:
                    trace['base_source'] = 'MEGA'
                    break
                if had_valid_local_before_restore and _db_valid(target):
                    trace['base_source'] = 'LOCAL_SQLITE_NEWER_OR_MEGA_UNAVAILABLE'
                    print('[SPLIT FRONT] keeping pre-existing valid local SQLite after MEGA attempt:', detail, flush=True)
                    break
                if _bool('SPLIT_ALLOW_EMPTY_BOOT', False):
                    trace['base_source'] = 'EMPTY_INIT'
                    print('[SPLIT FRONT] empty boot explicitly allowed', flush=True)
                    break
                if attempt < max_attempts:
                    time.sleep(retry_sec)
            else:
                trace['base_source'] = 'MEGA_RESTORE_FAILED'
                trace['local_valid_after'] = _db_valid(target)
                print('[SPLIT FRONT] R56 FATAL: no valid MEGA startup snapshot after bounded attempts:', last_detail, flush=True)
                raise RuntimeError('R56 MEGA startup restore failed: ' + last_detail[:700])

        # Re-apply packaged runtime settings: Redis remains OFF regardless of stale Render tunables.
        install_internal_runtime_config('front')
        os.environ.pop('GOOGLE_SERVICE_ACCOUNT_JSON', None)
        _scrub_fast_runtime_mega_credentials()

        if _db_valid(target):
            revision = _db_revision(target)
            trace['final_revision'] = revision
            trace['local_valid_after'] = True
            os.environ['SPLIT_PREBOOT_AUTHORITATIVE_R20'] = '1'
            os.environ['SPLIT_PREBOOT_REVISION_R20'] = str(revision)
        else:
            trace['final_revision'] = 0.0
            trace['local_valid_after'] = False

        trace['runtime_mega_credentials_scrubbed'] = True
        trace['redis_runtime_enabled'] = bool(os.getenv('REDIS_URL'))
        trace['elapsed_ms'] = round((time.time() - started) * 1000.0, 1)
        trace['finished_at'] = time.time()
        trace_json = json.dumps(trace, ensure_ascii=False, separators=(',', ':'))
        os.environ['R49_RESTORE_TRACE_JSON'] = trace_json
        print('[RESTORE TRACE R49]', trace_json, flush=True)

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
