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


class _BootHealthHandler(BaseHTTPRequestHandler):
    def _reply(self, status: int, body: bool):
        raw = b'{"ok":true,"role":"front","phase":"restoring_from_mega"}' if body else b''
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


def _bool(name: str, default=False) -> bool:
    return str(os.getenv(name, '1' if default else '0') or '').strip().lower() in {'1', 'true', 'yes', 'on', 'да'}


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
    return '/' + str(os.getenv('MEGA_BACKUP_DIR', 'TelegramBotBackups2-2') or 'TelegramBotBackups2-2').strip('/')


def _startup_mega_roots() -> list[str]:
    """MEGA roots allowed only during FAST startup recovery.

    R50 keeps the configured root authoritative, but can bootstrap it from the
    historical roots that HEAVY itself already understands. This closes the
    empty-new-root race without re-enabling runtime MEGA access in FAST.
    """
    out: list[str] = []
    for raw in [_canonical_mega_root(), *str(os.getenv(
        'MEGA_LEGACY_BACKUP_DIRS',
        '/TelegramBotBackups-2T,/TelegramBotBackups',
    ) or '').split(',')]:
        root = '/' + str(raw or '').strip().strip('/')
        if root != '/' and root not in out:
            out.append(root)
    return out


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


def _replay_mega_event_segments(target: Path, root: str, mega_timeout: int) -> tuple[bool, str]:
    """Replay compact post-checkpoint state events directly from MEGA onto startup DB."""
    event_root = root.rstrip('/') + '/events_r32'
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
    # Correctness first: never truncate or globally skip archived event segments.
    # Revision idempotence is per shard inside _apply_r32_events(). A global max
    # can be ahead for shard A while shard B still needs an older segment.
    current_max = _r32_max_revision(target)
    work = Path(tempfile.mkdtemp(prefix='v262_fast_mega_events_'))
    segments = applied = stale = 0
    try:
        for idx, remote in enumerate(rows):
            name = remote.rsplit('/', 1)[-1]
            dl = work / f'e{idx}'
            dl.mkdir(exist_ok=True)
            get = _run(['mega-get', remote, str(dl)], timeout=mega_timeout)
            if get.returncode != 0:
                return False, f'MEGA event download failed {name}: {(get.stderr or get.stdout or "")[:180]}'
            files = list(dl.rglob(name)) or list(dl.rglob('events_*.json.gz')) or list(dl.rglob('*.json.gz'))
            if not files:
                return False, f'MEGA event file missing after download: {name}'
            try:
                obj = json.loads(gzip.decompress(files[0].read_bytes()).decode('utf-8'))
                events = [ev for ev in ((obj or {}).get('events') or []) if _r32_event_valid(ev)]
            except Exception as exc:
                return False, f'MEGA event decode failed {name}: {type(exc).__name__}: {str(exc)[:150]}'
            if not events:
                return False, f'MEGA event segment has no valid events: {name}'
            a, st = _apply_r32_events(target, events)
            applied += a; stale += st; segments += 1
            current_max = max(current_max, max(int(ev.get('revision') or 0) for ev in events))
            shutil.rmtree(dl, ignore_errors=True)
        if not _db_valid(target):
            return False, 'SQLite invalid after MEGA event replay'
        return True, f'MEGA event replay segments={segments} applied={applied} stale={stale} max_revision={current_max}'
    finally:
        shutil.rmtree(work, ignore_errors=True)


def _restore_from_mega_startup(target: Path) -> tuple[bool, str]:
    """Restore FAST from MEGA once per process start, then leave MEGA completely.

    R50 read order per root:
      current_manifest -> immutable generation -> latest -> newest generation fallback.
    Root order:
      configured canonical root -> explicitly configured legacy roots.
    """
    roots = _startup_mega_roots()
    canonical_root = roots[0]
    mega_timeout = max(45, min(900, int(os.getenv('MEGA_TIMEOUT', '120') or '120')))
    login_timeout = max(45, min(300, int(os.getenv('MEGA_LOGIN_TIMEOUT', '120') or '120')))
    logged, detail = _mega_login(login_timeout)
    if not logged:
        return False, detail
    tmpdir = Path(tempfile.mkdtemp(prefix='v262_fast_startup_mega_'))
    try:
        candidates: list[tuple[str, str, str]] = []
        discovery: list[str] = []
        seen: set[str] = set()

        def add(root: str, remote: str, source: str) -> None:
            remote = str(remote or '').strip()
            if remote and remote not in seen:
                seen.add(remote)
                candidates.append((root, remote, source))

        for root in roots:
            generation_remote, manifest_detail = _manifest_generation_remote(root, tmpdir, mega_timeout)
            discovery.append(manifest_detail)
            if generation_remote:
                add(root, generation_remote, 'manifest')

            # HEAVY R50 still publishes this compact canonical pointer. It is a
            # compatibility READ only; FAST never writes it at runtime.
            add(root, root.rstrip('/') + '/database/latest_bot_state.sqlite3.gz', 'latest')

            # A manifest can be missing after a partial/manual migration while an
            # immutable generation is still perfectly valid. Discover it once at
            # startup instead of polling one missing filename forever.
            generations, find_detail = _discover_generation_remotes(root, mega_timeout)
            discovery.append(find_detail)
            for remote in generations:
                add(root, remote, 'generation-scan')

        errors: list[str] = []
        for idx, (source_root, remote, source_kind) in enumerate(candidates):
            dl = tmpdir / f'd{idx}'
            dl.mkdir(exist_ok=True)
            try:
                get = _run(['mega-get', remote, str(dl)], timeout=mega_timeout)
            except Exception as exc:
                errors.append(f'{remote}: {type(exc).__name__}')
                continue
            if get.returncode != 0:
                detail = (get.stderr or get.stdout or 'mega-get failed').strip()
                errors.append(f'{remote}: {detail[:180]}')
                continue
            candidates_local = list(dl.rglob('*.sqlite3.gz')) + [p for p in dl.rglob('*.gz') if p.name != 'latest_bot_state.sqlite3.gz']
            if not candidates_local:
                errors.append(f'{remote}: download contains no SQLite gzip')
                continue
            for gz_path in candidates_local:
                ok, install_detail = _install_gzip_db(gz_path, target)
                if not ok:
                    errors.append(f'{remote}: {install_detail}')
                    continue

                # Event streams may span a migration boundary. Replaying all known
                # startup roots is safe because idempotence is tracked per shard.
                replay_parts: list[str] = []
                replay_failed = False
                ordered_event_roots = [source_root]
                if canonical_root != source_root:
                    ordered_event_roots.append(canonical_root)
                for event_root in ordered_event_roots:
                    replay_ok, replay_detail = _replay_mega_event_segments(target, event_root, mega_timeout)
                    replay_parts.append(f'{event_root}: {replay_detail}')
                    if not replay_ok:
                        replay_failed = True
                        errors.append(f'{remote}: base installed but event replay failed at {event_root}: {replay_detail}')
                        break
                if replay_failed:
                    continue
                source_note = 'canonical' if source_root == canonical_root else 'legacy-bootstrap'
                return True, (
                    f'MEGA startup restore OK source={source_note}/{source_kind} root={source_root} '
                    f'remote={remote}; {install_detail}; ' + '; '.join(replay_parts)
                )[:1200]

        useful_discovery = [x for x in discovery if x and not _mega_missing(x)]
        tail = errors[-6:] + useful_discovery[-3:]
        return False, ('; '.join(tail) or 'no valid MEGA snapshot/generation found in configured or legacy roots')[:1200]
    finally:
        # Runtime boundary: FAST must not keep an authenticated MEGAcmd session.
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
    target = _db_path()
    started = time.time()
    trace = {
        'schema': 2,
        'policy': 'R50_FAST_STARTUP_MEGA_ONLY',
        'started_at': started,
        'internal_config': INTERNAL_CONFIG_VERSION,
        'local_found': target.exists(),
        'local_valid_before': _db_valid(target),
        'local_revision_before': _db_revision(target),
        'mega_contacted': True,
        'mega_ok': False,
        'mega_detail': '',
        'redis_contacted': False,
        'heavy_contacted': False,
        'base_source': '',
    }
    try:
        had_valid_local_before_restore = bool(trace['local_valid_before'])
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
            print(f'[SPLIT FRONT] R50 FAST MEGA startup restore attempt={attempt}/{max_attempts}:', ok, detail, flush=True)
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
            # Never remain a healthy-looking web service that does no bot work. A
            # fresh container without a valid MEGA recovery source must fail fast;
            # Render can restart it and a later HEAVY checkpoint can then be picked up.
            trace['base_source'] = 'MEGA_RESTORE_FAILED'
            trace['local_valid_after'] = _db_valid(target)
            print('[SPLIT FRONT] R50 FATAL: no valid MEGA startup snapshot after bounded attempts:', last_detail, flush=True)
            raise RuntimeError('R50 MEGA startup restore failed: ' + last_detail[:700])

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

        _stop_boot_port(server)
        runpy.run_path(str(Path(__file__).with_name('bot.py')), run_name='__main__')
    finally:
        try: _stop_boot_port(server)
        except Exception: pass


if __name__ == '__main__':
    main()
# v262
