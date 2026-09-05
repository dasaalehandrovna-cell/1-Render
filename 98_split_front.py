# v262
"""Render #1 fast split bridge for vys-262.

Render #1 keeps Telegram/webhook/UI and the working SQLite commit path.
Remote durability and Google Sheets network work are delegated to Render #2.
MEGA is disabled during normal runtime on the front; start_front.py keeps only the
cold emergency restore path for deploy/startup recovery.
"""
import gzip as _split_gzip
import json as _split_json
import base64 as _split_base64
import hashlib as _split_hashlib
import collections as _split_collections
import os as _split_os
import secrets as _split_secrets
import shutil as _split_shutil
import tempfile as _split_tempfile
import threading as _split_threading
import time as _split_time
try:
    import redis as _split_redis
except Exception:
    _split_redis = None

_SPLIT_FRONT_VERSION = "vys-262-front-per-r24-ordered-hot-ram-fast"
_SPLIT_SYNC_LOCK = _split_threading.RLock()
_SPLIT_SYNC_TIMER = None
_SPLIT_SYNC_DUE_AT = 0.0
_SPLIT_SYNC_FIRST_DIRTY_AT = 0.0
_SPLIT_LAST_CHANGE_AT = _split_time.time()
_SPLIT_FULL_LOCK = _split_threading.RLock()
_SPLIT_FULL_TIMER = None
_SPLIT_CONTINUITY_LOCK = _split_threading.RLock()
_SPLIT_CONTINUITY_TIMER = None
_SPLIT_CONTINUITY_CHAT_ID = None
_SPLIT_CONTINUITY_REASON = ''
_SPLIT_CONTINUITY_FIRST_DIRTY_AT = 0.0
_SPLIT_CHANGE_LOCK = _split_threading.RLock()
_SPLIT_CHANGE_EPOCH = _split_secrets.token_hex(6)
_SPLIT_CHANGE_SEQ = 0
_SPLIT_STATE_TOKEN = f"{_SPLIT_CHANGE_EPOCH}:0"
_SPLIT_UPDATE_CONTEXT = _split_threading.local()
_SPLIT_GOOGLE_RESULT_LOCK = _split_threading.RLock()
_SPLIT_GOOGLE_RESULTS = {}
_SPLIT_STATE = {
    "peer_last_attempt": 0.0,
    "peer_last_ok": 0.0,
    "peer_last_error": "",
    "peer_status": None,
    "worker_health": {},
    "sync_last_attempt": 0.0,
    "sync_last_ok": 0.0,
    "sync_last_error": "",
    "sync_pending": False,
    "sync_reason": "",
    "google_last_attempt": 0.0,
    "google_last_ok": 0.0,
    "google_last_error": "",
    "google_last_job": "",
    "state_token": _SPLIT_STATE_TOKEN,
    "state_change_reason": "boot",
    "redis_fallback_last_ok": 0.0,
    "redis_fallback_last_error": "",
    "delta_last_ok": 0.0,
    "delta_last_error": "",
    "delta_last_bytes": 0,
    "delta_last_pages": 0,
    "delta_total_bytes": 0,
    "delta_total_pages": 0,
    "delta_full_fallbacks": 0,
    "full_reconcile_pending": False,
    "full_reconcile_last_ok": 0.0,
    "full_reconcile_last_error": "",
    "delta_baseline_sha256": "",
    "event_last_receipt_ok": 0.0,
    "event_last_commit_ok": 0.0,
    "event_last_error": "",
    "event_received": 0,
    "event_committed": 0,
    "event_mirrored": 0,
    "event_redis_fallbacks": 0,
    "event_recovered": 0,
    "capsule_last_attempt": 0.0,
    "capsule_last_ok": 0.0,
    "capsule_last_error": "",
    "capsule_last_seq": 0,
    "capsule_last_generation": 0,
}


_SPLIT_DELTA_LOCK = _split_threading.RLock()
_SPLIT_DELTA_DIR = _split_os.path.join(str(_split_os.getenv('MEGA_LOCAL_TMP_DIR', '/tmp') or '/tmp'), 'vys262_delta_front')
_split_os.makedirs(_SPLIT_DELTA_DIR, exist_ok=True)
_SPLIT_DELTA_BASELINE = _split_os.path.join(_SPLIT_DELTA_DIR, 'acked_baseline.sqlite3')

def _split_sha256_file_v267(path):
    h = _split_hashlib.sha256()
    with open(path, 'rb') as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()

def _split_sqlite_page_size_v267(path):
    with open(path, 'rb') as fh:
        head = fh.read(100)
    if len(head) < 18 or head[:16] != b'SQLite format 3\x00':
        raise RuntimeError('not a SQLite database')
    page_size = int.from_bytes(head[16:18], 'big')
    if page_size == 1:
        page_size = 65536
    if page_size < 512 or page_size > 65536 or (page_size & (page_size - 1)):
        raise RuntimeError(f'invalid SQLite page size {page_size}')
    return page_size

def _split_snapshot_raw_v267(prefix='delta'):
    workdir = _split_tempfile.mkdtemp(prefix=f'v267_{prefix}_')
    raw = _split_os.path.join(workdir, 'state.sqlite3')
    SQLITE.backup_to(raw)
    return workdir, raw

def _split_init_delta_baseline_v267(force=False):
    with _SPLIT_DELTA_LOCK:
        if (not force) and _split_os.path.isfile(_SPLIT_DELTA_BASELINE) and _split_os.path.getsize(_SPLIT_DELTA_BASELINE) > 0:
            try:
                sha = _split_sha256_file_v267(_SPLIT_DELTA_BASELINE)
                _SPLIT_STATE['delta_baseline_sha256'] = sha
                return True
            except Exception:
                pass
        workdir = None
        try:
            workdir, raw = _split_snapshot_raw_v267('baseline')
            tmp = _SPLIT_DELTA_BASELINE + '.tmp'
            _split_shutil.copy2(raw, tmp)
            _split_os.replace(tmp, _SPLIT_DELTA_BASELINE)
            _SPLIT_STATE['delta_baseline_sha256'] = _split_sha256_file_v267(_SPLIT_DELTA_BASELINE)
            return True
        except Exception as exc:
            _SPLIT_STATE['delta_last_error'] = 'baseline: ' + str(exc)[:180]
            return False
        finally:
            if workdir:
                _split_shutil.rmtree(workdir, ignore_errors=True)

def _split_build_delta_v267(reason='change'):
    """Build a page-level delta against the last Worker-acknowledged SQLite image.

    Returns (payload_dict, current_raw, workdir, fallback_reason).  current_raw stays
    alive until the caller receives Worker acknowledgement and promotes it to baseline.
    """
    with _SPLIT_DELTA_LOCK:
        if not _split_os.path.isfile(_SPLIT_DELTA_BASELINE):
            return None, None, None, 'baseline_missing'
        workdir = None
        try:
            workdir, current = _split_snapshot_raw_v267('delta')
            base = _SPLIT_DELTA_BASELINE
            page_size = _split_sqlite_page_size_v267(current)
            if _split_sqlite_page_size_v267(base) != page_size:
                return None, current, workdir, 'page_size_changed'
            base_sha = _split_sha256_file_v267(base)
            new_sha = _split_sha256_file_v267(current)
            base_size = _split_os.path.getsize(base)
            new_size = _split_os.path.getsize(current)
            if base_sha == new_sha and base_size == new_size:
                return {'schema':1,'noop':True,'base_sha256':base_sha,'new_sha256':new_sha,'db_size':new_size,'page_size':page_size,'pages':[], 'state_token':_split_current_state_token_v264(), 'reason':str(reason or '')[:160], 'event_ids':_split_pending_event_ids_v268()}, current, workdir, ''
            pages=[]
            page_count=(new_size + page_size - 1)//page_size
            with open(base,'rb') as old, open(current,'rb') as new:
                for idx in range(page_count):
                    ob=old.read(page_size)
                    nb=new.read(page_size)
                    if ob != nb:
                        pages.append([idx, _split_base64.b64encode(nb).decode('ascii')])
            payload={'schema':1,'base_sha256':base_sha,'new_sha256':new_sha,'base_size':base_size,'db_size':new_size,'page_size':page_size,'pages':pages,'state_token':_split_current_state_token_v264(),'reason':str(reason or '')[:160],'created_at':_split_time.time(),'event_ids':_split_pending_event_ids_v268()}
            raw_json=_split_json.dumps(payload,separators=(',',':')).encode('utf-8')
            compressed=_split_gzip.compress(raw_json, compresslevel=9)
            max_pages=max(8,min(4096,int(_split_os.getenv('SPLIT_DELTA_MAX_PAGES','256') or '256')))
            max_bytes=max(32768,min(8*1024*1024,int(_split_os.getenv('SPLIT_DELTA_MAX_BYTES','524288') or '524288')))
            if len(pages) > max_pages or len(compressed) > max_bytes:
                return None, current, workdir, f'delta_too_large pages={len(pages)} bytes={len(compressed)}'
            payload['_wire_gzip']=compressed
            return payload,current,workdir,''
        except Exception as exc:
            if workdir:
                _split_shutil.rmtree(workdir, ignore_errors=True)
            return None,None,None,f'{type(exc).__name__}: {str(exc)[:180]}'

def _split_promote_delta_baseline_v267(current_raw):
    if not current_raw or not _split_os.path.isfile(current_raw):
        return False
    with _SPLIT_DELTA_LOCK:
        tmp=_SPLIT_DELTA_BASELINE+'.tmp'
        _split_shutil.copy2(current_raw,tmp)
        _split_os.replace(tmp,_SPLIT_DELTA_BASELINE)
        _SPLIT_STATE['delta_baseline_sha256']=_split_sha256_file_v267(_SPLIT_DELTA_BASELINE)
        return True

def _split_send_delta_v267(reason='change'):
    base, secret = _split_peer_base(), _split_secret()
    if not base or not secret:
        return False, 'worker URL/secret not configured', False
    payload,current,workdir,fallback = _split_build_delta_v267(reason)
    if payload is None:
        if workdir:
            _split_shutil.rmtree(workdir, ignore_errors=True)
        return False, fallback or 'delta unavailable', True
    try:
        wire=payload.pop('_wire_gzip', None)
        if wire is None:
            wire=_split_gzip.compress(_split_json.dumps(payload,separators=(',',':')).encode('utf-8'),compresslevel=9)
        r=requests.post(base+'/internal/delta',data=wire,headers={**_split_headers('vys-262-front-delta-r12'),'Content-Type':'application/json','Content-Encoding':'gzip'},timeout=15)
        if 200 <= r.status_code < 300:
            body={}
            try: body=r.json() if r.content else {}
            except Exception: body={}
            status=str(body.get('status') or 'applied')
            if status in {'applied','up_to_date','noop'}:
                _split_promote_delta_baseline_v267(current)
                _SPLIT_STATE['delta_last_ok']=_split_time.time()
                _SPLIT_STATE['delta_last_error']=''
                _SPLIT_STATE['delta_last_bytes']=len(wire)
                _SPLIT_STATE['delta_last_pages']=len(payload.get('pages') or [])
                _SPLIT_STATE['delta_total_bytes']=int(_SPLIT_STATE.get('delta_total_bytes') or 0)+len(wire)
                _SPLIT_STATE['delta_total_pages']=int(_SPLIT_STATE.get('delta_total_pages') or 0)+len(payload.get('pages') or [])
                _split_ack_mirrored_events_v268(payload.get('event_ids') or [])
                return True,status,False
        if r.status_code in {409, 412, 422}:
            return False, f'worker requests full: HTTP {r.status_code} {r.text[:180]}', True
        return False,f'HTTP {r.status_code}: {r.text[:180]}',False
    except Exception as exc:
        return False,f'{type(exc).__name__}: {str(exc)[:180]}',False
    finally:
        if workdir:
            _split_shutil.rmtree(workdir, ignore_errors=True)

def _split_env_bool(name, default=True):
    return str(_split_os.getenv(name, "1" if default else "0") or "").strip().lower() in {"1", "true", "yes", "on", "да"}


def _split_peer_base():
    raw = str(_split_os.getenv("PEER_SERVICE_URL", "") or "").strip().rstrip("/")
    if raw and not raw.startswith(("http://", "https://")):
        raw = "https://" + raw
    return raw


def _split_secret():
    return str(_split_os.getenv("PEER_SHARED_SECRET", "") or "").strip()


def _split_headers(agent="vys-262-front-peer"):
    return {"X-Peer-Secret": _split_secret(), "User-Agent": agent}


# R13: remote Telegram event witness.  The raw event is made durable on Worker/Redis
# before Telegram is acknowledged.  Business execution still happens only on Front.
_SPLIT_EVENT_LOCK = _split_threading.RLock()
_SPLIT_EVENT_PENDING_MIRROR = _split_collections.OrderedDict()

def _split_event_prefix_v268():
    return str(_split_os.getenv('WORKER_REDIS_EVENT_PREFIX','vys262:tg_events:v1') or 'vys262:tg_events:v1').strip()

def _split_event_id_v268(update_id):
    return str(update_id)

def _split_event_row_v268(update_id, payload, chat_id=None, update_type='other'):
    raw = _split_json.dumps(payload if isinstance(payload,dict) else {}, ensure_ascii=False, separators=(',',':'), default=str)
    return {
        'schema': 1, 'event_id': _split_event_id_v268(update_id), 'update_id': str(update_id),
        'chat_id': chat_id, 'update_type': str(update_type or 'other')[:40],
        'payload': payload if isinstance(payload,dict) else {},
        'payload_sha256': _split_hashlib.sha256(raw.encode('utf-8')).hexdigest(),
        'state': 'received', 'received_at': _split_time.time(),
        'front_version': _SPLIT_FRONT_VERSION,
    }

def _split_event_redis_write_v268(row, state=None, error=''):
    if _split_redis is None:
        return False, 'redis package unavailable'
    url=str(_split_os.getenv('REDIS_URL','') or '').strip()
    if not url:
        return False, 'REDIS_URL empty'
    try:
        client=_split_redis.Redis.from_url(url,socket_connect_timeout=float(_split_os.getenv('SPLIT_REDIS_FALLBACK_CONNECT_TIMEOUT_SEC','0.7') or '0.7'),socket_timeout=float(_split_os.getenv('SPLIT_REDIS_FALLBACK_SOCKET_TIMEOUT_SEC','1.2') or '1.2'),health_check_interval=30)
        event_id=str((row or {}).get('event_id') or (row or {}).get('update_id') or '')
        if not event_id:
            return False,'event id empty'
        prefix=_split_event_prefix_v268(); key=f'{prefix}:event:{event_id}'; pending=f'{prefix}:pending'
        current={}
        try:
            existing=client.get(key)
            if existing: current=_split_json.loads(existing.decode('utf-8') if isinstance(existing,(bytes,bytearray)) else existing)
        except Exception: current={}
        merged=dict(current or {}); merged.update(row or {})
        _rank={'received':1,'failed_retry':1,'committed':2,'mirrored':3,'checkpointed':4,'done':4}
        old_state=str((current or {}).get('state') or '')
        new_state=str(state or merged.get('state') or '')
        if _rank.get(old_state,0) > _rank.get(new_state,0): new_state=old_state
        if new_state: merged['state']=new_state
        if error and _rank.get(new_state,0) < 3: merged['last_error']=str(error)[:300]
        merged['updated_at']=_split_time.time()
        ttl=max(86400,min(2592000,int(_split_os.getenv('WORKER_EVENT_RETENTION_SEC','604800') or '604800')))
        pipe=client.pipeline(transaction=True)
        pipe.set(key,_split_json.dumps(merged,ensure_ascii=False,separators=(',',':'),default=str),ex=ttl)
        if str(merged.get('state') or '') in {'mirrored','checkpointed','done'}:
            pipe.zrem(pending,event_id)
        else:
            pipe.zadd(pending,{event_id:float(merged.get('received_at') or _split_time.time())})
        pipe.execute()
        return True,'redis event stored'
    except Exception as exc:
        return False,f'{type(exc).__name__}: {str(exc)[:180]}'

def split_witness_event_v268(update_id, payload, chat_id=None, update_type='other'):
    """R16: Redis is the first remote durable witness; Worker HTTP is fallback only.

    This removes an entire Render#1 -> Render#2 -> Redis hop from the Telegram hot path.
    Render#2 hydrates pending events from Redis in its reconcile loop.
    """
    row=_split_event_row_v268(update_id,payload,chat_id,update_type)
    ok,rdetail=_split_event_redis_write_v268(row,'received','')
    if ok:
        _SPLIT_STATE['event_last_receipt_ok']=_split_time.time(); _SPLIT_STATE['event_last_error']=''
        _SPLIT_STATE['event_received']=int(_SPLIT_STATE.get('event_received') or 0)+1
        return True
    base,secret=_split_peer_base(),_split_secret(); detail=f'redis={rdetail}'
    if base and secret:
        try:
            raw=_split_json.dumps(row,ensure_ascii=False,separators=(',',':'),default=str).encode('utf-8')
            wire=_split_gzip.compress(raw,compresslevel=1)
            r=requests.post(base+'/internal/event/receipt',data=wire,headers={**_split_headers('vys-262-front-event-r16-fallback'),'Content-Type':'application/json','Content-Encoding':'gzip'},timeout=max(0.35,min(2.5,float(_split_os.getenv('SPLIT_EVENT_RECEIPT_TIMEOUT_SEC','1.2') or '1.2'))))
            if 200 <= r.status_code < 300:
                _SPLIT_STATE['event_last_receipt_ok']=_split_time.time(); _SPLIT_STATE['event_last_error']=''
                _SPLIT_STATE['event_received']=int(_SPLIT_STATE.get('event_received') or 0)+1
                _SPLIT_STATE['event_redis_fallbacks']=int(_SPLIT_STATE.get('event_redis_fallbacks') or 0)+1
                return True
            detail=f'{detail}; worker HTTP {r.status_code}: {r.text[:160]}'
        except Exception as exc:
            detail=f'{detail}; worker {type(exc).__name__}: {str(exc)[:160]}'
    _SPLIT_STATE['event_last_error']=detail[:260]
    return False

def _split_event_status_send_v268(update_id, chat_id=None, update_type='other', success=True, error=''):
    event_id=_split_event_id_v268(update_id)
    row={'schema':1,'event_id':event_id,'update_id':str(update_id),'chat_id':chat_id,'update_type':str(update_type or 'other')[:40],
         'state':'committed' if success else 'failed_retry','committed_at':_split_time.time() if success else 0.0,
         'state_token':_split_current_state_token_v264(),'last_error':str(error or '')[:300]}
    ok,rdetail=_split_event_redis_write_v268(row,row['state'],error)
    if ok:
        if success:
            _SPLIT_STATE['event_last_commit_ok']=_split_time.time(); _SPLIT_STATE['event_committed']=int(_SPLIT_STATE.get('event_committed') or 0)+1
        _SPLIT_STATE['event_last_error']=''
        return True
    base,secret=_split_peer_base(),_split_secret(); detail=f'redis={rdetail}'
    if base and secret:
        try:
            r=requests.post(base+'/internal/event/commit',json=row,headers=_split_headers('vys-262-front-event-commit-r16-fallback'),timeout=4)
            if 200 <= r.status_code < 300:
                if success:
                    _SPLIT_STATE['event_last_commit_ok']=_split_time.time(); _SPLIT_STATE['event_committed']=int(_SPLIT_STATE.get('event_committed') or 0)+1
                _SPLIT_STATE['event_last_error']=''
                return True
            detail=f'{detail}; worker HTTP {r.status_code}: {r.text[:160]}'
        except Exception as exc:
            detail=f'{detail}; worker {type(exc).__name__}: {str(exc)[:160]}'
    _SPLIT_STATE['event_last_error']=detail[:260]
    return False

def _split_event_bg_v268(fn,*args):
    try:
        pool=globals().get('BACKGROUND_TASK_POOL')
        if pool is not None and hasattr(pool,'submit'):
            key=f'event-r13:{args[0] if args else _split_time.time_ns()}'
            if pool.submit(key,fn,*args): return True
    except Exception: pass
    try:
        _split_threading.Thread(target=fn,args=args,daemon=True,name='vys262-event-r13').start(); return True
    except Exception: return False

def split_event_committed_v268(update_id, chat_id=None, update_type='other', success=True, error=''):
    event_id=_split_event_id_v268(update_id)
    if success:
        with _SPLIT_EVENT_LOCK:
            _SPLIT_EVENT_PENDING_MIRROR[event_id]=_split_time.time()
            while len(_SPLIT_EVENT_PENDING_MIRROR)>512:
                _SPLIT_EVENT_PENDING_MIRROR.popitem(last=False)
        # R15: the post-update wrapper schedules one trailing-edge mirror attempt.
        # Do not arm a second snapshot timer from the event-status path.
    return _split_event_bg_v268(_split_event_status_send_v268,update_id,chat_id,update_type,success,error)

def _split_pending_event_ids_v268(limit=96):
    with _SPLIT_EVENT_LOCK:
        return list(_SPLIT_EVENT_PENDING_MIRROR.keys())[:max(1,int(limit))]

def _split_ack_mirrored_events_v268(event_ids):
    ids=[str(x) for x in (event_ids or []) if str(x)]
    if not ids: return
    with _SPLIT_EVENT_LOCK:
        for event_id in ids: _SPLIT_EVENT_PENDING_MIRROR.pop(event_id,None)
    _SPLIT_STATE['event_mirrored']=int(_SPLIT_STATE.get('event_mirrored') or 0)+len(ids)

def _split_remote_pending_rows_v268(limit=100):
    # R16: query the authoritative Redis event journal first; Worker is a fallback.
    if _split_redis is not None:
        url=str(_split_os.getenv('REDIS_URL','') or '').strip()
        if url:
            try:
                client=_split_redis.Redis.from_url(url,socket_connect_timeout=1.5,socket_timeout=3)
                prefix=_split_event_prefix_v268(); ids=client.zrange(f'{prefix}:pending',0,max(0,min(249,int(limit)-1))) or []
                rows=[]
                for raw_id in ids:
                    eid=raw_id.decode() if isinstance(raw_id,(bytes,bytearray)) else str(raw_id)
                    raw=client.get(f'{prefix}:event:{eid}')
                    if not raw: continue
                    try: row=_split_json.loads(raw.decode('utf-8') if isinstance(raw,(bytes,bytearray)) else raw)
                    except Exception: continue
                    if str((row or {}).get('state') or '') in {'received','failed_retry','committed'}: rows.append(row)
                return rows
            except Exception:
                pass
    base,secret=_split_peer_base(),_split_secret()
    if base and secret:
        try:
            r=requests.get(base+'/internal/events/pending',params={'limit':max(1,min(250,int(limit)))},headers=_split_headers('vys-262-front-event-recover-r16-fallback'),timeout=8)
            if 200 <= r.status_code < 300:
                body=r.json() if r.content else {}; return list(body.get('events') or [])
        except Exception: pass
    return []

def split_recover_remote_events_v268(limit=100):
    """Replay remote witnessed-but-not-mirrored Telegram updates after abrupt deploy."""
    recovered=0
    for row in _split_remote_pending_rows_v268(limit):
        try:
            update_id=row.get('update_id') or row.get('event_id'); payload=row.get('payload') or {}
            chat_id=row.get('chat_id'); update_type=str(row.get('update_type') or 'other')
            if update_id is None or not isinstance(payload,dict): continue
            state_fn=globals().get('_v260_webhook_inbox_state'); put_fn=globals().get('_v260_webhook_inbox_put'); submit_fn=globals().get('_v260_submit_webhook_inbox_row'); row_fn=globals().get('_v260_webhook_inbox_row')
            if not all(callable(x) for x in (state_fn,put_fn,submit_fn,row_fn)): continue
            if state_fn(update_id)=='done':
                split_event_committed_v268(update_id,chat_id,update_type,True,'already local done')
                continue
            if not put_fn(update_id,payload,chat_id,update_type): continue
            if submit_fn(row_fn(update_id)):
                recovered+=1
        except Exception: continue
    _SPLIT_STATE['event_recovered']=int(_SPLIT_STATE.get('event_recovered') or 0)+recovered
    return recovered


def _split_authorized_request():
    secret = _split_secret()
    supplied = str(request.headers.get("X-Peer-Secret", "") or "")
    return bool(secret and _split_secrets.compare_digest(secret, supplied))


_SPLIT_STATE_REV_KIND_R18 = 'split_state_revision_r18'
_SPLIT_STATE_REV_KEY_R18 = 'latest'
_SPLIT_STATE_REV_LOCK_R18 = _split_threading.RLock()
try:
    _SPLIT_STATE_REV_MEM_R27 = dict(SQLITE.get_meta(_SPLIT_STATE_REV_KIND_R18, _SPLIT_STATE_REV_KEY_R18, {}) or {})
except Exception:
    _SPLIT_STATE_REV_MEM_R27 = {}
_SPLIT_STATE_REV_DIRTY_R27 = False

def _r27_flush_state_revision():
    global _SPLIT_STATE_REV_DIRTY_R27
    try:
        with _SPLIT_STATE_REV_LOCK_R18:
            if not _SPLIT_STATE_REV_DIRTY_R27:
                return True
            payload = dict(_SPLIT_STATE_REV_MEM_R27 or {})
        SQLITE.set_meta(_SPLIT_STATE_REV_KIND_R18, _SPLIT_STATE_REV_KEY_R18, payload)
        with _SPLIT_STATE_REV_LOCK_R18:
            if int((_SPLIT_STATE_REV_MEM_R27 or {}).get('seq') or 0) <= int(payload.get('seq') or 0):
                _SPLIT_STATE_REV_DIRTY_R27 = False
        return True
    except Exception as exc:
        try: log_error(f'R27 state revision flush: {exc}')
        except Exception: pass
        return False

def _r27_schedule_state_revision_flush(delay=4.0):
    try:
        scheduler = globals().get('DELAYED_SCHEDULER')
        if scheduler is not None:
            scheduler.schedule('r27-state-revision-flush', max(1.0, float(delay)), _r27_flush_state_revision)
            return True
    except Exception:
        pass
    return False

def _split_touch_state_revision_r18(reason='update', update_id=None):
    """R27: monotonic revision is RAM-only on the Telegram hot path.

    The durable meta row is flushed later by the scheduler / before an idle snapshot.
    A UI callback therefore never waits on SQLITE just to update this bookkeeping row.
    """
    global _SPLIT_STATE_REV_DIRTY_R27
    try:
        with _SPLIT_STATE_REV_LOCK_R18:
            seq = int((_SPLIT_STATE_REV_MEM_R27 or {}).get('seq') or 0) + 1
            payload = {'schema':1, 'seq':seq, 'saved_at':_split_time.time(), 'reason':str(reason or '')[:140],
                       'update_id':str(update_id)[:80] if update_id is not None else '',
                       'state_token':_split_current_state_token_v264() if '_split_current_state_token_v264' in globals() else ''}
            _SPLIT_STATE_REV_MEM_R27.clear(); _SPLIT_STATE_REV_MEM_R27.update(payload)
            _SPLIT_STATE_REV_DIRTY_R27 = True
        # R28: do not schedule any SQLite write from a Telegram/user update.
        # The RAM revision is flushed only immediately before an idle/full durability snapshot.
        return payload
    except Exception as exc:
        try: log_error(f'R27 state revision touch: {exc}')
        except Exception: pass
        return {}


def _split_mark_state_changed_v264(reason='change'):
    global _SPLIT_CHANGE_SEQ, _SPLIT_STATE_TOKEN, _SPLIT_LAST_CHANGE_AT
    with _SPLIT_CHANGE_LOCK:
        _SPLIT_CHANGE_SEQ += 1
        _SPLIT_LAST_CHANGE_AT = _split_time.time()
        _SPLIT_STATE_TOKEN = f"{_SPLIT_CHANGE_EPOCH}:{_SPLIT_CHANGE_SEQ}"
        _SPLIT_STATE['state_token'] = _SPLIT_STATE_TOKEN
        _SPLIT_STATE['state_change_reason'] = str(reason or 'change')[:160]
        return _SPLIT_STATE_TOKEN


def _split_current_state_token_v264():
    with _SPLIT_CHANGE_LOCK:
        return str(_SPLIT_STATE_TOKEN)


def _split_snapshot_meta():
    try:
        root = SQLITE.load_root() or {}
        state_meta = root.get("_state_meta") if isinstance(root, dict) else {}
        return {
            "last_saved_at": str((state_meta or {}).get("last_saved_at") or ""),
            "cold_records": int(SQLITE.cold_count() or 0),
            "db_file": str(globals().get("DB_FILE") or "bot_state.sqlite3"),
        }
    except Exception as exc:
        return {"error": str(exc)[:160]}


@app.route('/peer/health', methods=['GET', 'HEAD'])
def split_front_peer_health_v262():
    # Keep the legacy keep_alive diagnostics in sync with the real split peer.
    try:
        ua = str(request.headers.get('User-Agent', '') or '').casefold()
        if 'worker-peer' in ua and _split_authorized_request():
            ks = globals().get('KEEP_ALIVE_STATE')
            if isinstance(ks, dict):
                now_txt = now_local().isoformat(timespec='milliseconds') if callable(globals().get('now_local')) else str(_split_time.time())
                ks['peer_received_at'] = now_txt
                ks['last_inbound_activity_at'] = now_txt
                ks['last_inbound_activity_kind'] = 'peer_worker'
    except Exception:
        pass
    if request.method == 'HEAD':
        return ('', 200)
    return ({
        'ok': True,
        'role': 'front',
        'version': _SPLIT_FRONT_VERSION,
        'bot_version': str(globals().get('VERSION') or ''),
        'ready': bool(globals().get('runtime_is_ready', lambda: False)()),
        'phase': (globals().get('_RUNTIME_STATE') or {}).get('phase'),
        'snapshot': _split_snapshot_meta(),
        'peer': dict(_SPLIT_STATE),
    }, 200)


@app.route('/internal/split/state', methods=['GET'])
def split_front_state_download_v262():
    """Return a transactionally consistent SQLite gzip to the worker."""
    if not _split_authorized_request():
        return ({'ok': False}, 404)
    workdir = _split_tempfile.mkdtemp(prefix='v262_front_state_')
    raw = _split_os.path.join(workdir, 'bot_state.sqlite3')
    gz = raw + '.gz'
    try:
        try:
            _quiet_fn = globals().get('r27_user_quiet_for')
            _quiet_for = float(_quiet_fn()) if callable(_quiet_fn) else 999999.0
            _guard = max(2.0, min(60.0, float(_split_os.getenv('R28_FULL_SNAPSHOT_USER_QUIET_SEC','30') or '15')))
            if bool(globals().get('runtime_is_ready', lambda: False)()) and _quiet_for < _guard:
                return ({'ok': False, 'busy': 'user_active', 'retry_after': max(1, int(_guard - _quiet_for) + 1)}, 423)
        except Exception:
            pass
        try: _r27_flush_state_revision()
        except Exception: pass
        _r25_state_started = _split_time.monotonic()
        snapshot_token = _split_current_state_token_v264()
        try: log_info(f'SPLITTRACE full_state_start token={snapshot_token[:48]}')
        except Exception: pass
        SQLITE.backup_to(raw)
        with open(raw, 'rb') as src, _split_gzip.open(gz, 'wb', compresslevel=1) as dst:
            _split_shutil.copyfileobj(src, dst, length=1024 * 1024)
        # R19: this raw SQLite image is exactly the full image HEAVY is about to receive.
        # Promote that SAME image to FAST's acknowledged delta baseline. R18 left the
        # old baseline in place after a full rebase, so every next tiny change produced
        # another 409 -> full /internal/split/state GET (~1.3 MB) loop.
        try:
            _split_promote_delta_baseline_v267(raw)
            _SPLIT_STATE['full_reconcile_last_ok'] = _split_time.time()
            _SPLIT_STATE['full_reconcile_pending'] = False
        except Exception as _r19_base_exc:
            _SPLIT_STATE['full_reconcile_last_error'] = 'R19 served baseline: ' + str(_r19_base_exc)[:180]
        with open(gz, 'rb') as fh:
            payload = fh.read()
        response = app.response_class(payload, status=200, mimetype='application/gzip')
        response.headers['Content-Disposition'] = 'attachment; filename="latest_bot_state.sqlite3.gz"'
        response.headers['X-Split-Version'] = _SPLIT_FRONT_VERSION
        response.headers['X-Split-Size'] = str(len(payload))
        response.headers['X-Split-State-Token'] = snapshot_token
        try: log_info(f'SPLITTRACE full_state_done token={snapshot_token[:48]} bytes={len(payload)} elapsed={_split_time.monotonic()-_r25_state_started:.3f}s')
        except Exception: pass
        return response
    except Exception as exc:
        return ({'ok': False, 'error': str(exc)[:240]}, 500)
    finally:
        _split_shutil.rmtree(workdir, ignore_errors=True)



@app.route('/internal/split/hash', methods=['GET'])
def split_front_state_hash_v268():
    """Rare reconciliation probe: hash a consistent SQLite image without sending it."""
    if not _split_authorized_request():
        return ({'ok':False},404)
    workdir=None
    try:
        workdir,raw=_split_snapshot_raw_v267('hash')
        return ({'ok':True,'sha256':_split_sha256_file_v267(raw),'size':_split_os.path.getsize(raw),'state_token':_split_current_state_token_v264(),'version':_SPLIT_FRONT_VERSION},200)
    except Exception as exc:
        return ({'ok':False,'error':f'{type(exc).__name__}: {str(exc)[:180]}'},500)
    finally:
        if workdir: _split_shutil.rmtree(workdir,ignore_errors=True)


def _split_redis_snapshot_keys_v266():
    key = str(_split_os.getenv('WORKER_REDIS_SNAPSHOT_KEY', 'vys262:bot_state:latest_gz') or 'vys262:bot_state:latest_gz').strip()
    return key, key + ':meta'


def _split_cache_snapshot_to_redis_v266(reason='front_fallback', existing_gz=None):
    """Best-effort durable bridge when worker is unavailable or being redeployed.

    Runs only from background sync/shutdown paths, never inline in Telegram handling.
    """
    if _split_redis is None:
        _SPLIT_STATE['redis_fallback_last_error'] = 'redis package unavailable'
        return False
    url = str(_split_os.getenv('REDIS_URL', '') or '').strip()
    if not url:
        _SPLIT_STATE['redis_fallback_last_error'] = 'REDIS_URL empty'
        return False
    workdir = None
    try:
        if existing_gz:
            gz = str(existing_gz)
        else:
            workdir = _split_tempfile.mkdtemp(prefix='v266_front_redis_')
            raw = _split_os.path.join(workdir, 'bot_state.sqlite3')
            gz = raw + '.gz'
            SQLITE.backup_to(raw)
            with open(raw, 'rb') as src, _split_gzip.open(gz, 'wb', compresslevel=1) as dst:
                _split_shutil.copyfileobj(src, dst, length=1024 * 1024)
        payload = open(gz, 'rb').read()
        max_mb = max(1, min(128, int(_split_os.getenv('WORKER_REDIS_SNAPSHOT_MAX_MB', '16') or '16')))
        if len(payload) > max_mb * 1024 * 1024:
            raise RuntimeError(f'snapshot too large for Redis: {len(payload)}')
        # revision is derived from the same SQLite image by the worker; the side meta is informational.
        revision = 0.0
        try:
            for kind in ('split_state_revision_r18', 'user_state_shadow_v265', 'runtime_continuity_v263'):
                row = SQLITE.get_meta(kind, 'latest', {}) or {}
                revision = max(revision, float((row or {}).get('saved_at') or 0.0))
        except Exception:
            pass
        key, meta_key = _split_redis_snapshot_keys_v266()
        client = _split_redis.Redis.from_url(url, socket_connect_timeout=3, socket_timeout=8, health_check_interval=30)
        existing_revision = 0.0
        try:
            existing_raw = client.get(meta_key)
            if isinstance(existing_raw, (bytes, bytearray)):
                existing_raw = existing_raw.decode('utf-8', 'replace')
            existing_meta = _split_json.loads(existing_raw) if isinstance(existing_raw, str) and existing_raw else {}
            existing_revision = float((existing_meta or {}).get('revision') or 0.0)
        except Exception:
            existing_revision = 0.0
        if existing_revision > revision + 0.000001:
            _SPLIT_STATE['redis_fallback_last_ok'] = _split_time.time()
            _SPLIT_STATE['redis_fallback_last_error'] = 'newer Redis snapshot preserved'
            return True
        meta = {'revision': revision, 'size': len(payload), 'saved_at': _split_time.time(), 'reason': str(reason or '')[:160], 'source': 'front-r18'}
        pipe = client.pipeline(transaction=True)
        pipe.set(key, payload)
        pipe.set(meta_key, _split_json.dumps(meta, separators=(',', ':')))
        pipe.execute()
        _SPLIT_STATE['redis_fallback_last_ok'] = _split_time.time()
        _SPLIT_STATE['redis_fallback_last_error'] = ''
        return True
    except Exception as exc:
        _SPLIT_STATE['redis_fallback_last_error'] = f'{type(exc).__name__}: {str(exc)[:180]}'
        return False
    finally:
        if workdir:
            _split_shutil.rmtree(workdir, ignore_errors=True)


def _split_ping_once():
    base = _split_peer_base()
    _SPLIT_STATE['peer_last_attempt'] = _split_time.time()
    try:
        ks = globals().get('KEEP_ALIVE_STATE')
        if isinstance(ks, dict):
            ks['peer_last_attempt_at'] = now_local().isoformat(timespec='milliseconds') if callable(globals().get('now_local')) else str(_split_time.time())
    except Exception:
        pass
    if not base:
        _SPLIT_STATE['peer_last_error'] = 'PEER_SERVICE_URL empty'
        return False
    try:
        r = requests.get(base + '/peer/health', headers=_split_headers('vys-262-front-peer-r11'), timeout=12)
        _SPLIT_STATE['peer_status'] = int(r.status_code)
        if 200 <= r.status_code < 300:
            payload = {}
            try: payload = r.json() if r.content else {}
            except Exception: payload = {}
            _SPLIT_STATE['peer_last_ok'] = _split_time.time()
            _SPLIT_STATE['peer_last_error'] = ''
            try:
                ks = globals().get('KEEP_ALIVE_STATE')
                if isinstance(ks, dict):
                    ks['peer_last_ok_at'] = now_local().isoformat(timespec='milliseconds') if callable(globals().get('now_local')) else str(_split_time.time())
                    ks['peer_last_error'] = ''
                    ks['peer_last_status_code'] = int(r.status_code)
                    ks['peer_ok_count'] = int(ks.get('peer_ok_count') or 0) + 1
            except Exception:
                pass
            _SPLIT_STATE['worker_health'] = dict(payload or {})
            _SPLIT_STATE['worker_health']['seen_at'] = _split_time.time()
            return True
        _SPLIT_STATE['peer_last_error'] = f'HTTP {r.status_code}'
    except Exception as exc:
        _SPLIT_STATE['peer_last_error'] = str(exc)[:220]
        _SPLIT_STATE['peer_status'] = None
    try:
        ks = globals().get('KEEP_ALIVE_STATE')
        if isinstance(ks, dict):
            ks['peer_last_error'] = str(_SPLIT_STATE.get('peer_last_error') or '')[:220]
            ks['peer_last_status_code'] = _SPLIT_STATE.get('peer_status')
            ks['peer_fail_count'] = int(ks.get('peer_fail_count') or 0) + 1
    except Exception:
        pass
    return False


def _split_peer_loop():
    _split_time.sleep(5.0)
    while True:
        if _split_env_bool('PEER_PING_ENABLED', True):
            _split_ping_once()
        try:
            interval = int(_split_os.getenv('PEER_PING_INTERVAL_SEC', '120') or '120')
        except Exception:
            interval = 120
        _split_time.sleep(max(30, min(1800, interval)))


def _split_request_worker_full_sync_r18(reason='need_full'):
    """Queue a full rebase on HEAVY; FAST never waits for snapshot/MEGA work."""
    base, secret = _split_peer_base(), _split_secret()
    if not base or not secret:
        return False, 'worker URL/secret not configured'
    try:
        body = {'type':'sync_state', 'reason':str(reason or 'need_full')[:160], 'state_token':_split_current_state_token_v264()}
        r = requests.post(base + '/internal/job', json=body, headers=_split_headers('vys-262-front-r18-rebase'), timeout=2.5)
        if 200 <= r.status_code < 300:
            return True, f'worker full rebase queued HTTP {r.status_code}'
        return False, f'worker full rebase HTTP {r.status_code}: {r.text[:160]}'
    except Exception as exc:
        return False, f'{type(exc).__name__}: {str(exc)[:160]}'


def _split_request_sync_now(reason='change'):
    """R12 normal durability path: send only changed SQLite pages.

    A full SQLite image is sent only when the Worker reports a base mismatch, when the
    delta is abnormally large, or during the explicit graceful-shutdown checkpoint.
    """
    _SPLIT_STATE['sync_last_attempt'] = _split_time.time()
    _SPLIT_STATE['sync_reason'] = str(reason or 'change')[:160]
    ok, detail, need_full = _split_send_delta_v267(_SPLIT_STATE['sync_reason'])
    if ok:
        _SPLIT_STATE['sync_last_ok'] = _split_time.time()
        _SPLIT_STATE['sync_last_error'] = ''
        _SPLIT_STATE['sync_pending'] = False
        return True
    _SPLIT_STATE['delta_last_error'] = str(detail or '')[:220]
    if need_full:
        # R25 FAST-priority rule: never make HEAVY repeatedly pull full SQLite while
        # the user is clicking. A mismatch is reconciled after a short quiet period by
        # a Front->HEAVY snapshot push. The snapshot itself uses the R25 online SQLite
        # backup connection and therefore never owns FAST's shared SQLITE.lock.
        _SPLIT_STATE['delta_full_fallbacks'] = int(_SPLIT_STATE.get('delta_full_fallbacks') or 0) + 1
        _SPLIT_STATE['full_reconcile_pending'] = True
        try:
            _split_schedule_idle_full_reconcile_v270('delta_resync_r25:' + str(reason or 'change')[:80])
            _SPLIT_STATE['full_reconcile_last_error'] = 'R25 deferred full reconcile until UI quiet'
        except Exception as _r25_reconcile_exc:
            _SPLIT_STATE['full_reconcile_last_error'] = str(_r25_reconcile_exc)[:220]
    _SPLIT_STATE['sync_last_error'] = str(detail or 'delta sync failed')[:220]
    return False


def _split_sync_timer_fire():
    global _SPLIT_SYNC_TIMER, _SPLIT_SYNC_DUE_AT, _SPLIT_SYNC_FIRST_DIRTY_AT
    try:
        reason = str(_SPLIT_STATE.get('sync_reason') or 'change')
        # R28: page-delta generation itself required a full local SQLite backup, so
        # "tiny delta" still hammered FAST every few seconds. Raw Telegram events are
        # already durable remotely; mirror the canonical SQLite only after UI quiet.
        _split_schedule_idle_full_reconcile_v270('r28-idle:' + reason[:100], delay=float(_split_os.getenv('R28_STATE_MIRROR_DELAY_SEC','30') or '30'))
    finally:
        with _SPLIT_SYNC_LOCK:
            _SPLIT_SYNC_TIMER = None
            _SPLIT_SYNC_DUE_AT = 0.0
            _SPLIT_SYNC_FIRST_DIRTY_AT = 0.0


def _split_inside_telegram_update_v264():
    return bool(getattr(_SPLIT_UPDATE_CONTEXT, 'active', False))


def split_schedule_worker_sync_v262(reason='change', delay=None):
    """Coalesced state handoff; Telegram never waits for MEGA or snapshot transfer."""
    global _SPLIT_SYNC_TIMER, _SPLIT_SYNC_DUE_AT, _SPLIT_SYNC_FIRST_DIRTY_AT
    if not _split_env_bool('SPLIT_WORKER_SYNC_ENABLED', True):
        return False
    # One Telegram update may call save_data/config/finance hooks many times. R4
    # could arm the worker while the handler was still executing, then arm it again
    # at the post-update continuity checkpoint. Defer all those requests and emit
    # exactly one notification after the update completes.
    if _split_inside_telegram_update_v264():
        _SPLIT_STATE['sync_pending'] = True
        _SPLIT_STATE['sync_reason'] = str(reason or 'change')[:160]
        return True
    try:
        wait = float(delay if delay is not None else _split_os.getenv('SPLIT_STATE_SYNC_DELAY_SEC', '8') or '8')
    except Exception:
        wait = 1.5
    try:
        min_interval = float(_split_os.getenv('SPLIT_STATE_SYNC_MIN_INTERVAL_SEC', '30') or '30')
    except Exception:
        min_interval = 12.0
    wait = max(0.08, min(30.0, wait))
    min_interval = max(0.2, min(120.0, min_interval))
    # R15: RAW events are already remotely witnessed.  State mirroring may therefore
    # debounce short finance bursts instead of snapshotting/gzipping on every message.
    _reason_l = str(reason or '').lower()
    if 'finance' in _reason_l or 'critical' in _reason_l or 'event_commit' in _reason_l:
        wait = max(wait, 0.8)
        min_interval = max(min_interval, 1.5)
    now = _split_time.time()
    last = float(_SPLIT_STATE.get('sync_last_attempt') or 0.0)
    with _SPLIT_SYNC_LOCK:
        if _SPLIT_SYNC_FIRST_DIRTY_AT <= 0.0:
            _SPLIT_SYNC_FIRST_DIRTY_AT = now
        first_dirty = _SPLIT_SYNC_FIRST_DIRTY_AT
    try:
        max_latency = max(1.0, min(12.0, float(_split_os.getenv('SPLIT_SYNC_MAX_LATENCY_SEC','60') or '60')))
    except Exception:
        max_latency = 3.0
    due = max(now + wait, last + min_interval if last else now + wait)
    due = min(due, first_dirty + max_latency)
    due = max(now + 0.05, due)
    _SPLIT_STATE['sync_pending'] = True
    _SPLIT_STATE['sync_reason'] = str(reason or 'change')[:160]
    with _SPLIT_SYNC_LOCK:
        # R15 trailing-edge debounce: a burst of ten messages produces one mirror
        # attempt after the burst, not ten competing SQLite backups.
        if _SPLIT_SYNC_TIMER is not None:
            try:
                _SPLIT_SYNC_TIMER.cancel()
            except Exception:
                pass
        _SPLIT_SYNC_DUE_AT = due
        _SPLIT_SYNC_TIMER = _split_threading.Timer(max(0.05, due - now), _split_sync_timer_fire)
        _SPLIT_SYNC_TIMER.daemon = True
        _SPLIT_SYNC_TIMER.start()
    return True


# Final durability bindings for split mode. SQLite has already been committed by the
# normal save path; these hooks only request remote durability from Render #2.
def _v262_split_schedule_delta_backup(chat_id=None, delay=None, reason='change'):
    split_schedule_worker_sync_v262(reason=f'delta:{reason}', delay=delay)
    return True


def _v262_split_persist_critical_delta_now(chat_id):
    split_schedule_worker_sync_v262(reason=f'critical:{int(chat_id)}', delay=0.08)
    return True


def _v262_split_schedule_full_backup_only(chat_id, delay=3.0):
    split_schedule_worker_sync_v262(reason=f'full:{int(chat_id)}', delay=min(float(delay or 1.0), 5.0))
    return True


def _v262_split_mega_upload_latest_database_backup(force=False):
    split_schedule_worker_sync_v262(reason='manual_db_snapshot' if force else 'db_snapshot', delay=0.08 if force else 0.5)
    return True


def _v262_split_schedule_config_backup_for_chats(*chat_ids, delay=3.0):
    # R20: the original v262 config hook is the authoritative signal that a
    # user-visible setting changed.  Capture a small independent durable capsule
    # immediately in a background timer; do not wait for full SQLite/delta sync.
    try:
        _r25_cp = _r20_latest_config_checkpoint() if '_r20_latest_config_checkpoint' in globals() else {}
        _r25_gen = int((_r25_cp or {}).get('generation') or 0)
        if _r25_gen > int(globals().get('_R20_CAPSULE_LAST_GEN_SENT', 0) or 0):
            r20_schedule_durable_capsule('config_hook:' + ','.join(map(str, chat_ids[:8])), delay=2.0)
    except Exception:
        pass
    split_schedule_worker_sync_v262(reason='config:' + ','.join(map(str, chat_ids[:8])), delay=min(float(delay or 1.0), 5.0))
    return True


def _split_google_target(target_chat_id=None, tenant_id=None):
    try:
        tid = str(_v149_tenant_id(tenant_id, target_chat_id))
    except Exception:
        tid = str(tenant_id or globals().get('TENANT_PLATFORM_ID') or 'platform')
    cfg = tenant_google_config(tid, create=False) if callable(globals().get('tenant_google_config')) else {}
    raw = str((cfg or {}).get('spreadsheet_id') or '').strip()
    if not raw and tid == str(globals().get('TENANT_PLATFORM_ID') or ''):
        raw = str(_split_os.getenv('GOOGLE_SHEETS_SPREADSHEET_ID', '') or '').strip()
    if not raw:
        raise RuntimeError('Google Таблица не выбрана. Откройте /google → «Куда выгружать Excel» и пришлите ссылку таблицы.')
    try:
        sheet_id = _v149_google_id(raw, 'sheet')
    except Exception:
        sheet_id = str(raw).strip()
    return tid, sheet_id


def _split_annotations_for_google(rows, layout, annotations_override, include_annotations):
    if not include_annotations:
        return {}
    try:
        if layout == 'compact':
            _styles, ann, _freeze, _widths = _modern_compact_excel_styles_comments(rows, annotations_override or {})
        elif layout == 'category_compact':
            _styles, ann, _freeze, _widths = _modern_category_no_description_styles_comments(rows, annotations_override or {})
        else:
            _styles, ann, _freeze, _widths = _modern_category_excel_styles_comments(rows)
            if annotations_override is not None:
                ann = dict(annotations_override or {})
        return ann or {}
    except Exception:
        return dict(annotations_override or {})


def _v262_split_google_sheets_create_category_report(title, rows, layout='category', annotations_override=None, include_annotations=True, **kwargs):
    """Queue Google Sheets work on Render #2 and return immediately with a job token."""
    if not _split_env_bool('SPLIT_GOOGLE_REMOTE_ENABLED', True):
        raise RuntimeError('Google Sheets worker delegation disabled')
    base, secret = _split_peer_base(), _split_secret()
    if not base or not secret:
        raise RuntimeError('Google Sheets worker is not configured')
    target_chat_id = kwargs.get('target_chat_id')
    notify_result = bool(kwargs.get('notify_result', True))
    recipient_chat_id = kwargs.get('recipient_chat_id') or target_chat_id
    tid, spreadsheet_id = _split_google_target(target_chat_id=target_chat_id, tenant_id=kwargs.get('tenant_id'))
    _SPLIT_STATE['google_last_attempt'] = _split_time.time()
    annotations = _split_annotations_for_google(rows, str(layout or 'category'), annotations_override, bool(include_annotations))
    encoded_notes = {f'{int(r)},{int(c)}': str(note) for (r, c), note in annotations.items() if str(note or '').strip()}
    client_job_id = _split_secrets.token_hex(12)
    body = {
        'job_id': client_job_id,
        'title': str(title or 'Статьи')[:300],
        'rows': rows,
        'layout': str(layout or 'category'),
        'annotations': encoded_notes,
        'include_annotations': bool(include_annotations),
        'spreadsheet_id': spreadsheet_id,
        'tenant_id': tid,
        'target_chat_id': target_chat_id,
        'recipient_chat_id': recipient_chat_id,
        'notify_result': notify_result,
    }
    try:
        r = requests.post(base + '/internal/google/sheet', json=body, headers=_split_headers('vys-262-front-google'), timeout=30)
        payload = r.json() if r.content and 'json' in str(r.headers.get('content-type', '')).lower() else {}
        if r.status_code == 202:
            job_id = str(payload.get('job_id') or client_job_id)
            _SPLIT_STATE['google_last_job'] = job_id
            _SPLIT_STATE['google_last_error'] = ''
            return 'worker-job:' + job_id
        if 200 <= r.status_code < 300 and payload.get('url'):
            _SPLIT_STATE['google_last_ok'] = _split_time.time()
            _SPLIT_STATE['google_last_error'] = ''
            return str(payload.get('url'))
        _SPLIT_STATE['google_last_error'] = f'HTTP {r.status_code}: {r.text[:220]}'
        raise RuntimeError('Google Sheets worker: ' + _SPLIT_STATE['google_last_error'])
    except Exception as exc:
        _SPLIT_STATE['google_last_error'] = str(exc)[:240]
        raise


def _split_google_result_seen(job_id):
    now = _split_time.time()
    with _SPLIT_GOOGLE_RESULT_LOCK:
        stale = [k for k, ts in _SPLIT_GOOGLE_RESULTS.items() if now - float(ts) > 86400]
        for key in stale:
            _SPLIT_GOOGLE_RESULTS.pop(key, None)
        if job_id in _SPLIT_GOOGLE_RESULTS:
            return True
        _SPLIT_GOOGLE_RESULTS[job_id] = now
        return False


@app.route('/internal/split/google-result', methods=['POST'])
def split_front_google_result_v262():
    """Worker callback. Duplicate callbacks are acknowledged without duplicate Telegram messages."""
    if not _split_authorized_request():
        return ({'ok': False}, 404)
    body = request.get_json(silent=True) or {}
    job_id = str(body.get('job_id') or '').strip()
    if not job_id:
        return ({'ok': False, 'error': 'job_id required'}, 400)
    if _split_google_result_seen(job_id):
        return ({'ok': True, 'duplicate': True}, 200)
    try:
        recipient_chat_id = int(body.get('recipient_chat_id') or 0)
    except Exception:
        recipient_chat_id = 0
    if not recipient_chat_id:
        return ({'ok': False, 'error': 'recipient_chat_id required'}, 400)
    ok = bool(body.get('ok'))
    notify_result = bool(body.get('notify_result', True))
    if ok:
        url = str(body.get('url') or '').strip()
        title = str(body.get('title') or 'Google Excel').strip()[:180]
        _SPLIT_STATE['google_last_ok'] = _split_time.time()
        _SPLIT_STATE['google_last_error'] = ''
        if notify_result:
            text = f'✅ 📊 Google Excel готов\n{title}\n\n{url}'
            bot.send_message(recipient_chat_id, text, disable_web_page_preview=True)
    else:
        err = str(body.get('error') or 'неизвестная ошибка')[:700]
        _SPLIT_STATE['google_last_error'] = err[:240]
        if notify_result:
            bot.send_message(recipient_chat_id, '❌ Google Excel не создан на Render #2:\n' + err)
    return ({'ok': True}, 200)


def _split_tenant_google_status_text(tenant_id):
    tid = str(tenant_id)
    row = tenant_get(tid) or {}
    cfg = tenant_google_config(tid)
    raw = str(cfg.get('spreadsheet_id') or '')
    if not raw and tid == str(globals().get('TENANT_PLATFORM_ID') or ''):
        raw = str(_split_os.getenv('GOOGLE_SHEETS_SPREADSHEET_ID', '') or '')
    try:
        shown = _v149_mask_id(raw) if raw else 'не выбрана'
    except Exception:
        shown = (raw[:8] + '…' + raw[-6:]) if len(raw) > 18 else (raw or 'не выбрана')
    settings = cfg.get('export_settings') or {}
    return (
        f"📊 GOOGLE EXCEL · {row.get('name') or tid}\n\n"
        f"Service account: ✅ Render #2\n"
        f"Куда выгружать: {shown}\n"
        f"Google Sheets: {'✅ ВКЛ' if settings.get('sheet_enabled', True) else '⬜ ВЫКЛ'}\n"
        f"История: {len(cfg.get('history') or [])}\n"
        f"Ошибки: {len(cfg.get('errors') or [])}\n\n"
        "Нажмите «Куда выгружать Excel» и пришлите ссылку или ID Google Таблицы. "
        "Сам service_account хранится только на Render #2. Выбранную таблицу нужно расшарить его client_email как Редактору."
    )[:3900]


def _split_tenant_google_keyboard(tenant_id):
    tid = str(tenant_id)
    cfg = tenant_google_config(tid)
    settings = cfg.get('export_settings') or {}
    kb = types.InlineKeyboardMarkup(row_width=1)
    kb.row(IB('📊 Куда выгружать Excel', callback_data='v149:google:sheet'))
    kb.row(IB(f"{('✅' if settings.get('sheet_enabled', True) else '⬜')} Google Sheets: {('ВКЛ' if settings.get('sheet_enabled', True) else 'ВЫКЛ')}", callback_data='v149:google:toggle_sheet'))
    kb.row(IB('🧪 Проверить выбранную таблицу', callback_data='v149:google:test'))
    kb.row(IB(f"📜 История ({len(cfg.get('history') or [])})", callback_data='v149:google:history'), IB(f"⚠️ Ошибки ({len(cfg.get('errors') or [])})", callback_data='v149:google:errors'))
    return kb


def _split_tenant_google_test(tenant_id):
    try:
        tid, spreadsheet_id = _split_google_target(tenant_id=str(tenant_id))
        base = _split_peer_base()
        if not base or not _split_secret():
            return False, '❌ Render #2 не настроен.'
        r = requests.post(base + '/internal/google/test', json={'spreadsheet_id': spreadsheet_id, 'tenant_id': tid}, headers=_split_headers('vys-262-front-google-test'), timeout=35)
        payload = r.json() if r.content else {}
        if 200 <= r.status_code < 300 and payload.get('ok'):
            return True, f"✅ Google Таблица доступна через Render #2.\nНазвание: {payload.get('title') or '—'}\nService account: {payload.get('service_email') or '—'}"
        return False, '❌ Проверка Google: ' + str(payload.get('error') or r.text[:500])
    except Exception as exc:
        return False, '❌ Проверка Google: ' + str(exc)[:600]


def _split_reject_front_google_credentials(*args, **kwargs):
    raise RuntimeError('Service account не загружается в Telegram-фронт. GOOGLE_SERVICE_ACCOUNT_JSON задаётся только в Environment Render #2.')


# New split Google callbacks are legitimate windows and must be declared.
try:
    WINDOW_MARKER_CONSTANTS.setdefault('v149:google:*', 'Ф233')
except Exception:
    pass


def _split_v167_google_upsert_named_tab(tab_title, rows, target_chat_id, layout='category', annotations_override=None):
    """Route legacy v167/v261 scheduled Google refreshes to Render #2."""
    return _v262_split_google_sheets_create_category_report(
        tab_title, rows, layout=layout, annotations_override=annotations_override,
        include_annotations=True, target_chat_id=int(target_chat_id),
        recipient_chat_id=int(target_chat_id), notify_result=False,
    )


# Apply final bindings after 89_callback_final.py.
globals()['schedule_delta_backup'] = _v262_split_schedule_delta_backup
globals()['persist_critical_delta_now'] = _v262_split_persist_critical_delta_now
globals()['schedule_full_backup_only'] = _v262_split_schedule_full_backup_only
globals()['mega_upload_latest_database_backup'] = _v262_split_mega_upload_latest_database_backup
globals()['schedule_config_backup_for_chats'] = _v262_split_schedule_config_backup_for_chats
globals()['_google_sheets_create_category_report'] = _v262_split_google_sheets_create_category_report
globals()['_v167_google_upsert_named_tab'] = _split_v167_google_upsert_named_tab
globals()['tenant_google_status_text'] = _split_tenant_google_status_text
globals()['tenant_google_keyboard'] = _split_tenant_google_keyboard
globals()['tenant_google_test'] = _split_tenant_google_test
globals()['tenant_google_set_credentials'] = _split_reject_front_google_credentials

# R11: no legacy MEGA delta is allowed to execute on the fast Front. Some old
# delayed callbacks may have been armed before this final split module loaded; make
# their runtime target a harmless drain so diagnostics do not keep reporting
# `shard delta upload failed` while Worker owns Redis/MEGA durability.
def _r11_split_legacy_delta_noop():
    try:
        lock = globals().get('_delta_state_lock')
        pending = globals().get('_delta_pending_chats')
        if lock is not None:
            with lock:
                if isinstance(pending, set): pending.clear()
        elif isinstance(pending, set):
            pending.clear()
        domains = globals().get('_V240_PENDING_DOMAINS')
        if isinstance(domains, dict): domains.clear()
        globals()['_delta_last_error'] = ''
    except Exception:
        pass
    return True

globals()['_run_delta_batch'] = _r11_split_legacy_delta_noop
globals()['_V234_MEGA_RUN_DELTA_BATCH'] = _r11_split_legacy_delta_noop
_r11_split_legacy_delta_noop()

# R11: note the exact moment a finance row became durable on Front. During a
# Telegram update the remote handoff waits until the handler has finished; finance
# forwarding/background commits that happen outside the update schedule their own
# coalesced Worker handoff.
_R11_BASE_PERSIST_FINANCE_LOCAL = globals().get('persist_finance_chat_local_fast')
def _r11_persist_finance_chat_local_fast(chat_id: int) -> bool:
    ok = bool(_R11_BASE_PERSIST_FINANCE_LOCAL(int(chat_id))) if callable(_R11_BASE_PERSIST_FINANCE_LOCAL) else False
    if not ok:
        return False
    try:
        if _split_inside_telegram_update_v264():
            _SPLIT_UPDATE_CONTEXT.finance_dirty = True
        else:
            _split_mark_state_changed_v264(f'finance_commit:{int(chat_id)}')
            split_schedule_worker_sync_v262(reason=f'finance_commit:{int(chat_id)}', delay=0.35)
    except Exception:
        pass
    return True

if callable(_R11_BASE_PERSIST_FINANCE_LOCAL):
    globals()['persist_finance_chat_local_fast'] = _r11_persist_finance_chat_local_fast

_split_threading.Thread(target=_split_peer_loop, name='v262-front-peer', daemon=True).start()

# ---------------------------------------------------------------------------
# r4 continuity layer: deploy/restart must be invisible to the Telegram user.
# Canonical business/config state already lives in SQLite.  This layer adds the
# small RAM-only interaction state that makes existing buttons/windows/sessions
# continue working after a new Render instance starts.
# ---------------------------------------------------------------------------
_CONTINUITY_META_KIND_V263 = 'runtime_continuity_v263'
_CONTINUITY_META_KEY_V263 = 'latest'
_CONTINUITY_MAX_ITEMS_V263 = 6000
_CONTINUITY_SKIP_V263 = object()
_CONTINUITY_NAMES_V263 = (
    '_short_callback_store',
    '_WINDOW_NAV_HISTORY',
    '_category_order_selection',
    '_category_other_sort_state',
    '_timer_input_sessions',
    '_careful_restore_sessions',
    '_dozvon_sessions',
    '_dozvon_target_index',
    '_JOURNAL_FILENAME_WAIT',
    '_REMINDER_UI_BINDINGS',
    '_REMINDER_COMPLETED_DELETE_SELECTION',
    '_V172_INPUT_WAIT',
    '_V172_SEARCH_CACHE',
    '_V174_INPUT_WAIT',
    '_V221_OWNER_MSG_PENDING',
    '_V221_LIVE_MARKUP',
    '_V224_INLINE_HELPER_STATE',
    '_V160_ANNOTATION_PENDING',
    '_V160_LAST_WINDOW_META',
    '_V160_CALLBACK_IDS',
    '_V161_DELETE_STATE',
    '_V161_WINDOW_TOKENS',
    '_V164_WINDOW_VIEW',
    '_V196_SESSIONS',
    '_V196_PANEL_MESSAGES',
    '_V196_LAST_BASE_BY_KEY',
    '_V196_LAST_META_BY_TOKEN',
    '_V196_ACTIVE_WORKING_BY_KEY',
    '_V212_LAST_BASE_BY_SCOPE_KEY',
    '_V212_CATALOG_BY_SCOPE',
    '_KEEPALIVE_INPUT_WAIT',
    '_secret_sequence_state',
    '_o9_secret_clicks',
    '_V153_RESTORE_PENDING',
    '_V153_CALLBACK_RECEIPTS',
    '_V153_CALLBACK_SIGNATURES',
    # R6: additional user-facing interaction state discovered by full runtime audit.
    '_V153_WAITING_EXPORTS',
    '_V178_MEGA_PRIORITY_WAITING',
    '_V240_PAR_WAITING',
    # R6 full interaction audit: serializable user-visible sessions that previously
    # vanished on deploy even when the canonical chat/settings data survived.
    '_owner_json_restore_prompts',
    '_timer_input_sessions',
    '_careful_restore_sessions',
    '_dozvon_sessions',
    '_category_order_selection',
    '_category_other_sort_state',
    '_INLINE_FALLBACK_TEXT',
    '_V153_READY_EXPORTS',
    '_V153_UI_CACHE',
    '_V156_PROCESS_UI',
    '_V160_FAST_EDIT_LAST',
    '_V146_FAILED_TASK_RUNTIME_ERRORS',
)
_CONTINUITY_SCALARS_V263 = ('restore_mode', '_short_callback_counter')

# R17: automatically include safe RAM-only interaction containers that future UI
# modules may add without remembering to extend the static whitelist.  We purposely
# exclude process/runtime/network objects so a deploy never resurrects old locks,
# queues, timers, transport caches or worker state.
_CONTINUITY_DYNAMIC_HINTS_R17 = ('SESSION', 'WAIT', 'PENDING', 'SELECTION', 'BINDING', 'CALLBACK', 'WINDOW', 'INPUT')
_CONTINUITY_DYNAMIC_DENY_R17 = ('LOCK', 'THREAD', 'TIMER', 'QUEUE', 'POOL', 'CLIENT', 'SOCKET', 'EXECUTOR', 'SPLIT_', 'MEGA_', 'REDIS_', 'TG_', 'TELEGRAM_', 'MEDIA_GROUP', 'FORWARD_OUTCOME')

def _continuity_dynamic_names_r17():
    out = []
    for name, value in list(globals().items()):
        if name in _CONTINUITY_NAMES_V263 or name in _CONTINUITY_SCALARS_V263:
            continue
        upper = str(name).upper()
        if not str(name).startswith('_') or not any(h in upper for h in _CONTINUITY_DYNAMIC_HINTS_R17):
            continue
        if any(bad in upper for bad in _CONTINUITY_DYNAMIC_DENY_R17):
            continue
        if isinstance(value, (dict, list, set, tuple, _split_collections.deque)):
            out.append(str(name))
    return tuple(sorted(set(out)))

# R6 persistent user-state shadow. The normal SQLite root/chats remain canonical,
# but this compact duplicate protects settings/UI/task/tenant metadata from any
# missed point-save or cross-chat mutation. Financial cold ledgers are deliberately
# excluded so this layer can never roll back accounting records.
_USER_STATE_META_KIND_V265 = 'user_state_shadow_v265'
_USER_STATE_META_KEY_V265 = 'latest'
_USER_STATE_ROOT_EXCLUDE_V265 = {'overall_balance', 'records', 'bot_errors', '_state_meta'}
_USER_STATE_CHAT_EXCLUDE_V265 = set(globals().get('LOWRAM_COLD_KEYS') or set()) | {'balance', 'next_id'}

def _user_state_json_copy_v265(value):
    try:
        return _split_json.loads(_split_json.dumps(value, ensure_ascii=False, separators=(',', ':'), default=str))
    except Exception:
        return None

def user_state_shadow_capture_v265(reason='checkpoint', persist=True):
    try:
        root_src = _sqlite_pack_root(data) if callable(globals().get('_sqlite_pack_root')) else {k:v for k,v in (data or {}).items() if k != 'chats'}
        root = {}
        for key, value in (root_src or {}).items():
            if str(key) in _USER_STATE_ROOT_EXCLUDE_V265:
                continue
            copied = _user_state_json_copy_v265(value)
            if copied is not None:
                root[str(key)] = copied
        chats = {}
        for cid, store in ((data or {}).get('chats') or {}).items():
            if not isinstance(store, dict):
                continue
            meta = {}
            try:
                items = dict.items(store)
            except Exception:
                items = []
            for key, value in items:
                if str(key) in _USER_STATE_CHAT_EXCLUDE_V265:
                    continue
                copied = _user_state_json_copy_v265(value)
                if copied is not None:
                    meta[str(key)] = copied
            chats[str(cid)] = meta
        previous = SQLITE.get_meta(_USER_STATE_META_KIND_V265, _USER_STATE_META_KEY_V265, {}) or {}
        seq = int((previous or {}).get('seq') or 0) + 1
        payload = {
            'schema': 2, 'seq': seq, 'saved_at': _split_time.time(),
            'reason': str(reason or 'checkpoint')[:180], 'front_version': _SPLIT_FRONT_VERSION,
            'root': root, 'chats': chats,
            'counts': {'root_keys': len(root), 'chats': len(chats),
                       'chat_settings': sum(1 for v in chats.values() if isinstance(v, dict) and isinstance(v.get('settings'), dict)),
                       'tasks': len((root.get('_tasks_v172') or {})) if isinstance(root.get('_tasks_v172'), dict) else 0,
                       'reminders': len((root.get('reminders') or root.get('_reminders') or {})) if isinstance((root.get('reminders') or root.get('_reminders') or {}), dict) else 0,
                       'tenants': len((((root.get('_global_settings') or {}).get('tenants_v148') or {}).get('tenants') or {})) if isinstance(((root.get('_global_settings') or {}).get('tenants_v148') or {}), dict) else 0,
                       'additional_owners': len(root.get('additional_owners') or root.get('additional_owner_ids') or []) if isinstance((root.get('additional_owners') or root.get('additional_owner_ids') or []), (list, tuple, set, dict)) else 0},
        }
        if persist:
            SQLITE.set_meta(_USER_STATE_META_KIND_V265, _USER_STATE_META_KEY_V265, payload)
        return payload
    except Exception as exc:
        try: log_error(f'USER_STATE shadow capture R6: {exc}')
        except Exception: pass
        return {}

def user_state_shadow_apply_v265(loaded):
    if not isinstance(loaded, dict):
        return loaded
    try:
        payload = SQLITE.get_meta(_USER_STATE_META_KIND_V265, _USER_STATE_META_KEY_V265, {}) or {}
    except Exception:
        payload = {}
    if not isinstance(payload, dict) or not payload:
        return loaded
    try:
        incoming_seq = int(payload.get('seq') or 0)
        applied_seq = int(globals().get('_USER_STATE_APPLIED_SEQ_R19', 0) or 0)
        if applied_seq and incoming_seq and incoming_seq < applied_seq:
            log_error(f'USER_STATE R19 stale shadow rejected seq={incoming_seq} < applied={applied_seq}')
            return loaded
        globals()['_USER_STATE_APPLIED_SEQ_R19'] = max(applied_seq, incoming_seq)
    except Exception:
        pass
    restored_root = 0; restored_chats = 0; restored_settings = 0
    root = payload.get('root') or {}
    if isinstance(root, dict):
        for key, value in root.items():
            if str(key) in _USER_STATE_ROOT_EXCLUDE_V265:
                continue
            loaded[str(key)] = _user_state_json_copy_v265(value)
            restored_root += 1
    chats = loaded.setdefault('chats', {})
    shadow_chats = payload.get('chats') or {}
    if isinstance(shadow_chats, dict):
        for cid, meta in shadow_chats.items():
            if not isinstance(meta, dict):
                continue
            current = chats.get(str(cid))
            if not isinstance(current, dict):
                current = {}
                chats[str(cid)] = current
            for key, value in meta.items():
                if str(key) in _USER_STATE_CHAT_EXCLUDE_V265:
                    continue
                current[str(key)] = _user_state_json_copy_v265(value)
            try:
                if LOWRAM_ENABLED and not isinstance(current, ColdChatStore):
                    current = _lowram_wrap_store(int(cid), current)
                    chats[str(cid)] = current
            except Exception:
                pass
            restored_chats += 1
            if isinstance(meta.get('settings'), dict):
                restored_settings += 1
    try:
        log_info(f"USER_STATE R6 restored shadow seq={payload.get('seq')} root={restored_root} chats={restored_chats} settings={restored_settings}")
    except Exception:
        pass
    return loaded

# Apply the shadow as part of canonical load, before tenant/bootstrap defaults can
# create a factory profile. This is intentionally after normal SQLite unpacking.
_V265_BASE_LOAD_DATA = load_data
def load_data():
    loaded = _V265_BASE_LOAD_DATA()
    return user_state_shadow_apply_v265(loaded)


def _continuity_encode_v263(value, depth=0):
    if depth > 12:
        return _CONTINUITY_SKIP_V263
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, bytes):
        # No user interaction state should require raw binary; storing it as hex
        # avoids invalid JSON if a small identifier ever appears here.
        return {'__v263_type__': 'bytes', 'value': value.hex()[:131072]}
    if isinstance(value, dict):
        try:
            items = list(value.items())[:_CONTINUITY_MAX_ITEMS_V263]
        except Exception:
            return _CONTINUITY_SKIP_V263
        out = []
        for key, item in items:
            ek = _continuity_encode_v263(key, depth + 1)
            ev = _continuity_encode_v263(item, depth + 1)
            if ek is _CONTINUITY_SKIP_V263 or ev is _CONTINUITY_SKIP_V263:
                continue
            out.append([ek, ev])
        return {'__v263_type__': 'dict', 'items': out}
    if isinstance(value, tuple):
        vals = []
        for item in list(value)[:_CONTINUITY_MAX_ITEMS_V263]:
            enc = _continuity_encode_v263(item, depth + 1)
            if enc is not _CONTINUITY_SKIP_V263:
                vals.append(enc)
        return {'__v263_type__': 'tuple', 'items': vals}
    if isinstance(value, (list, set, _split_collections.deque)):
        typ = 'set' if isinstance(value, set) else 'deque' if isinstance(value, _split_collections.deque) else 'list'
        vals = []
        try:
            source = list(value)[:_CONTINUITY_MAX_ITEMS_V263]
        except Exception:
            return _CONTINUITY_SKIP_V263
        for item in source:
            enc = _continuity_encode_v263(item, depth + 1)
            if enc is not _CONTINUITY_SKIP_V263:
                vals.append(enc)
        return {'__v263_type__': typ, 'items': vals}
    # datetime/date values are rare in UI sessions; preserve their text instead
    # of failing the whole continuity snapshot.
    iso = getattr(value, 'isoformat', None)
    if callable(iso):
        try:
            return {'__v263_type__': 'iso', 'value': str(iso())}
        except Exception:
            pass
    return _CONTINUITY_SKIP_V263


def _continuity_decode_v263(value, depth=0):
    if depth > 12:
        return None
    if not isinstance(value, dict) or '__v263_type__' not in value:
        if isinstance(value, list):
            return [_continuity_decode_v263(x, depth + 1) for x in value]
        return value
    typ = str(value.get('__v263_type__') or '')
    if typ == 'bytes':
        try:
            return bytes.fromhex(str(value.get('value') or ''))
        except Exception:
            return b''
    if typ == 'dict':
        out = {}
        for pair in value.get('items') or []:
            if not isinstance(pair, list) or len(pair) != 2:
                continue
            key = _continuity_decode_v263(pair[0], depth + 1)
            val = _continuity_decode_v263(pair[1], depth + 1)
            try:
                out[key] = val
            except Exception:
                pass
        return out
    vals = [_continuity_decode_v263(x, depth + 1) for x in (value.get('items') or [])]
    if typ == 'tuple':
        return tuple(vals)
    if typ == 'set':
        try:
            return set(vals)
        except Exception:
            return set()
    if typ == 'deque':
        return _split_collections.deque(vals)
    if typ == 'list':
        return vals
    if typ == 'iso':
        return str(value.get('value') or '')
    return value


def _continuity_apply_v263(name, restored):
    current = globals().get(name, _CONTINUITY_SKIP_V263)
    try:
        if isinstance(current, dict) and isinstance(restored, dict):
            current.clear(); current.update(restored); return True
        if isinstance(current, set) and isinstance(restored, (set, list, tuple)):
            current.clear(); current.update(restored); return True
        if isinstance(current, list) and isinstance(restored, (list, tuple)):
            current[:] = list(restored); return True
        if isinstance(current, _split_collections.deque) and isinstance(restored, (list, tuple, _split_collections.deque)):
            current.clear(); current.extend(restored); return True
        globals()[name] = restored
        return True
    except Exception:
        return False


def continuity_capture_v263(reason='checkpoint'):
    """Persist RAM-only user interaction continuity inside canonical SQLite."""
    payload = {
        'schema': 2,
        'saved_at': _split_time.time(),
        'reason': str(reason or 'checkpoint')[:180],
        'front_version': _SPLIT_FRONT_VERSION,
        'globals': {},
        'dynamic_globals_r17': {},
        'scalars': {},
    }
    for name in _CONTINUITY_NAMES_V263:
        if name not in globals():
            continue
        enc = _continuity_encode_v263(globals().get(name))
        if enc is not _CONTINUITY_SKIP_V263:
            payload['globals'][name] = enc
    for name in _CONTINUITY_SCALARS_V263:
        if name not in globals():
            continue
        enc = _continuity_encode_v263(globals().get(name))
        if enc is not _CONTINUITY_SKIP_V263:
            payload['scalars'][name] = enc
    for name in _continuity_dynamic_names_r17():
        enc = _continuity_encode_v263(globals().get(name))
        if enc is not _CONTINUITY_SKIP_V263:
            payload['dynamic_globals_r17'][name] = enc
    # Existing Telegram message IDs/windows are logical root state; add a compact
    # count here for diagnostics while the actual records stay in the normal root.
    try:
        payload['ui_counts'] = {
            'active_message_chats': len((data.get('active_messages') or {})),
            'open_windows': len((data.get('open_window_registry') or {})),
            'chat_count': len((data.get('chats') or {})),
        }
    except Exception:
        payload['ui_counts'] = {}
    SQLITE.set_meta(_CONTINUITY_META_KIND_V263, _CONTINUITY_META_KEY_V263, payload)
    return payload


def continuity_restore_v263():
    """Restore interaction state before main() starts accepting Telegram updates."""
    try:
        payload = SQLITE.get_meta(_CONTINUITY_META_KIND_V263, _CONTINUITY_META_KEY_V263, {}) or {}
    except Exception:
        return {'ok': False, 'reason': 'meta_read_failed'}
    if not isinstance(payload, dict) or not payload:
        return {'ok': False, 'reason': 'no_snapshot'}
    restored_names = []
    for name, raw in (payload.get('globals') or {}).items():
        if name not in _CONTINUITY_NAMES_V263:
            continue
        if _continuity_apply_v263(name, _continuity_decode_v263(raw)):
            restored_names.append(name)
    dynamic_allowed = set(_continuity_dynamic_names_r17())
    for name, raw in (payload.get('dynamic_globals_r17') or {}).items():
        if name not in dynamic_allowed:
            continue
        if _continuity_apply_v263(name, _continuity_decode_v263(raw)):
            restored_names.append(name)
    for name, raw in (payload.get('scalars') or {}).items():
        if name not in _CONTINUITY_SCALARS_V263:
            continue
        if _continuity_apply_v263(name, _continuity_decode_v263(raw)):
            restored_names.append(name)
    # Remove expired short callbacks; valid old Telegram buttons remain clickable.
    try:
        now = _split_time.time()
        ttl = float(globals().get('SHORT_CALLBACK_TTL_SECONDS') or 21600)
        store = globals().get('_short_callback_store')
        if isinstance(store, dict):
            for token, row in list(store.items()):
                if now - float((row or {}).get('ts') or 0.0) > ttl:
                    store.pop(token, None)
    except Exception:
        pass
    try:
        log_info(f"CONTINUITY R20 restored names={len(restored_names)} saved_at={payload.get('saved_at')} ui={payload.get('ui_counts') or {}}")
    except Exception:
        pass
    return {'ok': True, 'restored': restored_names, 'saved_at': payload.get('saved_at')}


def continuity_checkpoint_v263(chat_id=None, reason='update', full=False, schedule=True):
    """Commit logical + RAM continuity locally, then asynchronously hand it to worker."""
    try:
        if full:
            _V263_BASE_SAVE_DATA(data, full=True)
        elif chat_id is not None:
            _V263_BASE_SAVE_DATA(data, chat_ids=[int(chat_id)])
        else:
            _V263_BASE_SAVE_DATA(data, root_only=True)
    except Exception as exc:
        try: log_error(f'CONTINUITY local save R4: {exc}')
        except Exception: pass
    try:
        user_state_shadow_capture_v265(reason)
        continuity_capture_v263(reason)
        _split_mark_state_changed_v264(f'continuity:{reason}')
    except Exception as exc:
        try: log_error(f'CONTINUITY snapshot R5: {exc}')
        except Exception: pass
    if schedule:
        try:
            split_schedule_worker_sync_v262(reason=f'continuity:{reason}', delay=0.35)
        except Exception:
            pass
    return True



# R20: v262-style independent durable configuration/user-state capsule.
# Full SQLite remains the accounting/state baseline, but user settings must never rely
# on a full snapshot completing.  This compact checkpoint is built off the Telegram
# handler thread and stored monotonically by HEAVY/Redis.
_R20_CAPSULE_LOCK = _split_threading.RLock()
_R20_CAPSULE_TIMER = None
_R20_CAPSULE_FIRST_DIRTY_AT = 0.0
_R20_CAPSULE_REASON = ''
_R20_CAPSULE_LAST_GEN_SENT = 0
_R20_CAPSULE_LAST_SEQ_SENT = 0

def _r20_latest_config_checkpoint():
    try:
        fn = globals().get('config_guard_latest_local_v234')
        row = fn() if callable(fn) else {}
        return row if isinstance(row, dict) else {}
    except Exception:
        return {}

def _r20_capsule_build(reason='state_change'):
    # Capture the logical shadow in this background lane. Financial cold ledgers are
    # excluded by user_state_shadow_capture_v265 by design.
    user_state = user_state_shadow_capture_v265('r25-capsule:' + str(reason or '')[:120], persist=False) or {}
    config_cp = _r20_latest_config_checkpoint()
    try:
        with _SPLIT_STATE_REV_LOCK_R18:
            rev = dict(_SPLIT_STATE_REV_MEM_R27 or {})
        if not rev:
            rev = SQLITE.get_meta(_SPLIT_STATE_REV_KIND_R18, _SPLIT_STATE_REV_KEY_R18, {}) or {}
    except Exception:
        rev = {}
    return {
        'kind': 'vys262_durable_capsule_r20', 'schema': 1,
        'saved_at': _split_time.time(), 'reason': str(reason or '')[:160],
        'front_version': _SPLIT_FRONT_VERSION,
        'user_state': user_state,
        'config_checkpoint': config_cp,
        'state_revision': rev,
        'user_state_seq': int((user_state or {}).get('seq') or 0),
        'config_generation': int((config_cp or {}).get('generation') or 0),
    }

def _r20_capsule_redis_key():
    return str(_split_os.getenv('WORKER_REDIS_CAPSULE_KEY', 'vys262:durable_capsule:r20') or 'vys262:durable_capsule:r20').strip()

def _r20_capsule_store_redis(payload: dict, packed: bytes):
    if _split_redis is None:
        return False, 'redis package unavailable'
    url = str(_split_os.getenv('REDIS_URL', '') or '').strip()
    if not url:
        return False, 'REDIS_URL empty'
    try:
        client = _split_redis.Redis.from_url(url, socket_connect_timeout=0.5, socket_timeout=1.5, health_check_interval=30)
        key = _r20_capsule_redis_key()
        merged = dict(payload or {})
        try:
            old_raw = client.get(key)
            old = _split_json.loads(_split_gzip.decompress(old_raw).decode('utf-8')) if old_raw else {}
        except Exception:
            old = {}
        if isinstance(old, dict) and old:
            old_seq = int(old.get('user_state_seq') or ((old.get('user_state') or {}).get('seq') or 0))
            new_seq = int(merged.get('user_state_seq') or ((merged.get('user_state') or {}).get('seq') or 0))
            if old_seq > new_seq:
                merged['user_state'] = old.get('user_state') or {}
                merged['user_state_seq'] = old_seq
            old_gen = int(old.get('config_generation') or ((old.get('config_checkpoint') or {}).get('generation') or 0))
            new_gen = int(merged.get('config_generation') or ((merged.get('config_checkpoint') or {}).get('generation') or 0))
            if old_gen > new_gen:
                merged['config_checkpoint'] = old.get('config_checkpoint') or {}
                merged['config_generation'] = old_gen
            try:
                if float(((old.get('state_revision') or {}).get('saved_at') or 0.0)) > float(((merged.get('state_revision') or {}).get('saved_at') or 0.0)):
                    merged['state_revision'] = old.get('state_revision') or {}
            except Exception:
                pass
            merged['saved_at'] = max(float(old.get('saved_at') or 0.0), float(merged.get('saved_at') or 0.0))
        packed = _split_gzip.compress(_split_json.dumps(merged, ensure_ascii=False, separators=(',',':'), default=str).encode('utf-8'), compresslevel=3)
        seq = int(merged.get('user_state_seq') or 0); gen = int(merged.get('config_generation') or 0)
        meta = {'user_state_seq': seq, 'config_generation': gen,
                'saved_at': float(merged.get('saved_at') or _split_time.time()),
                'size': len(packed), 'source': 'front-r20'}
        pipe = client.pipeline(transaction=True)
        pipe.set(key, packed)
        pipe.set(key + ':meta', _split_json.dumps(meta, separators=(',',':')))
        pipe.execute()
        return True, f'redis capsule stored seq={seq} gen={gen}'
    except Exception as exc:
        return False, f'{type(exc).__name__}: {str(exc)[:180]}'

def _r20_capsule_push_now(reason='state_change'):
    global _R20_CAPSULE_LAST_GEN_SENT, _R20_CAPSULE_LAST_SEQ_SENT
    _SPLIT_STATE['capsule_last_attempt'] = _split_time.time()
    try:
        payload = _r20_capsule_build(reason)
        raw = _split_json.dumps(payload, ensure_ascii=False, separators=(',',':'), default=str).encode('utf-8')
        packed = _split_gzip.compress(raw, compresslevel=3)
        max_bytes = 8 * 1024 * 1024
        if len(packed) > max_bytes:
            raise RuntimeError(f'capsule too large: {len(packed)}')
        seq = int(payload.get('user_state_seq') or 0)
        gen = int(payload.get('config_generation') or 0)
        # Shared Redis is the fastest durable witness and survives either Render being redeployed.
        redis_ok, redis_detail = _r20_capsule_store_redis(payload, packed)
        worker_ok = False; worker_detail = ''
        base, secret = _split_peer_base(), _split_secret()
        if base and secret:
            try:
                r = requests.post(base + '/internal/capsule', data=packed,
                    headers={**_split_headers('vys-262-front-capsule-r20'), 'Content-Type':'application/json', 'Content-Encoding':'gzip'}, timeout=3.0)
                worker_ok = 200 <= r.status_code < 300
                worker_detail = f'HTTP {r.status_code}' if worker_ok else f'HTTP {r.status_code}: {r.text[:120]}'
            except Exception as exc:
                worker_detail = f'{type(exc).__name__}: {str(exc)[:140]}'
        if redis_ok or worker_ok:
            _R20_CAPSULE_LAST_GEN_SENT = max(_R20_CAPSULE_LAST_GEN_SENT, gen)
            _R20_CAPSULE_LAST_SEQ_SENT = max(_R20_CAPSULE_LAST_SEQ_SENT, seq)
            _SPLIT_STATE['capsule_last_ok'] = _split_time.time()
            _SPLIT_STATE['capsule_last_error'] = ''
            _SPLIT_STATE['capsule_last_seq'] = seq
            _SPLIT_STATE['capsule_last_generation'] = gen
            return True
        _SPLIT_STATE['capsule_last_error'] = f'redis={redis_detail}; worker={worker_detail}'[:240]
    except Exception as exc:
        _SPLIT_STATE['capsule_last_error'] = f'{type(exc).__name__}: {str(exc)[:220]}'
        try: log_error('R20 durable capsule: ' + _SPLIT_STATE['capsule_last_error'])
        except Exception: pass
    return False

def _r20_capsule_timer_fire():
    global _R20_CAPSULE_TIMER, _R20_CAPSULE_FIRST_DIRTY_AT, _R20_CAPSULE_REASON
    with _R20_CAPSULE_LOCK:
        reason = str(_R20_CAPSULE_REASON or 'coalesced')
        _R20_CAPSULE_TIMER = None
        _R20_CAPSULE_FIRST_DIRTY_AT = 0.0
        _R20_CAPSULE_REASON = ''
    return _r20_capsule_push_now(reason)

def r20_schedule_durable_capsule(reason='state_change', delay=None):
    global _R20_CAPSULE_TIMER, _R20_CAPSULE_FIRST_DIRTY_AT, _R20_CAPSULE_REASON
    try:
        wait = float(delay if delay is not None else _split_os.getenv('SPLIT_CAPSULE_DELAY_SEC','0.35') or '0.35')
    except Exception:
        wait = 0.35
    try:
        max_latency = float(_split_os.getenv('SPLIT_CAPSULE_MAX_LATENCY_SEC','1.0') or '1.0')
    except Exception:
        max_latency = 1.0
    now = _split_time.time()
    with _R20_CAPSULE_LOCK:
        if _R20_CAPSULE_FIRST_DIRTY_AT <= 0.0:
            _R20_CAPSULE_FIRST_DIRTY_AT = now
        _R20_CAPSULE_REASON = str(reason or 'state_change')[:160]
        due = min(now + max(0.05, wait), _R20_CAPSULE_FIRST_DIRTY_AT + max(0.2, max_latency))
        if _R20_CAPSULE_TIMER is not None:
            try: _R20_CAPSULE_TIMER.cancel()
            except Exception: pass
        _R20_CAPSULE_TIMER = _split_threading.Timer(max(0.03, due-now), _r20_capsule_timer_fire)
        _R20_CAPSULE_TIMER.daemon = True
        _R20_CAPSULE_TIMER.start()
    return True

# R20: redirect the original v262 config-guard remote sync to the HEAVY capsule.
# This preserves the semantic trigger/generation of v262 without allowing FAST to
# log into MEGA or perform a remote upload. HEAVY persists Redis + MEGA asynchronously.
_R20_BASE_CONFIG_GUARD_SYNC_REMOTE = globals().get('config_guard_sync_remote_v234')
def _r20_config_guard_sync_remote(*, recovery_write=False):
    try:
        r20_schedule_durable_capsule('config_guard_remote_sync', delay=2.0)
        split_schedule_worker_sync_v262(reason='config_guard_remote_sync', delay=0.7)
        return True
    except Exception as exc:
        try: log_error(f'R20 config durable schedule: {exc}')
        except Exception: pass
        return False
globals()['config_guard_sync_remote_v234'] = _r20_config_guard_sync_remote

# R15: full user-state shadow/continuity is a coalesced background checkpoint.
# The finance record itself has already been committed by persist_finance_chat_local_fast;
# serializing every chat after every message was pure foreground latency.
def _split_continuity_checkpoint_fire_v270():
    global _SPLIT_CONTINUITY_TIMER, _SPLIT_CONTINUITY_CHAT_ID, _SPLIT_CONTINUITY_REASON, _SPLIT_CONTINUITY_FIRST_DIRTY_AT
    with _SPLIT_CONTINUITY_LOCK:
        cid = _SPLIT_CONTINUITY_CHAT_ID
        reason = str(_SPLIT_CONTINUITY_REASON or 'coalesced')
        _SPLIT_CONTINUITY_TIMER = None
        _SPLIT_CONTINUITY_CHAT_ID = None
        _SPLIT_CONTINUITY_REASON = ''
        _SPLIT_CONTINUITY_FIRST_DIRTY_AT = 0.0
    # R28: continuity is background durability, never a competitor of a fresh button.
    try:
        quiet_fn = globals().get('r27_user_quiet_for')
        quiet_for = float(quiet_fn()) if callable(quiet_fn) else 10**9
        quiet_need = max(3.0, min(60.0, float(_split_os.getenv('R28_CONTINUITY_USER_QUIET_SEC','12') or '12')))
        if quiet_for < quiet_need:
            split_schedule_continuity_checkpoint_v270(cid, reason, delay=max(1.0, quiet_need - quiet_for))
            return
    except Exception:
        pass
    try:
        if cid is not None:
            _V263_BASE_SAVE_DATA(data, chat_ids=[int(cid)])
        else:
            _V263_BASE_SAVE_DATA(data, root_only=True)
        user_state_shadow_capture_v265('bg:' + reason)
        continuity_capture_v263('bg:' + reason)
        _split_mark_state_changed_v264('bg_continuity:' + reason)
        split_schedule_worker_sync_v262(reason='bg_continuity:' + reason, delay=1.2)
    except Exception as exc:
        try: log_error(f'R15 background continuity: {exc}')
        except Exception: pass

def split_schedule_continuity_checkpoint_v270(chat_id=None, reason='update', delay=4.0):
    global _SPLIT_CONTINUITY_TIMER, _SPLIT_CONTINUITY_CHAT_ID, _SPLIT_CONTINUITY_REASON, _SPLIT_CONTINUITY_FIRST_DIRTY_AT
    with _SPLIT_CONTINUITY_LOCK:
        if chat_id is not None:
            try: _SPLIT_CONTINUITY_CHAT_ID = int(chat_id)
            except Exception: pass
        _SPLIT_CONTINUITY_REASON = str(reason or 'update')[:160]
        now = _split_time.time()
        if _SPLIT_CONTINUITY_FIRST_DIRTY_AT <= 0.0:
            _SPLIT_CONTINUITY_FIRST_DIRTY_AT = now
        try:
            max_latency = max(1.0, min(15.0, float(_split_os.getenv('SPLIT_CONTINUITY_MAX_LATENCY_SEC','5.0') or '5.0')))
        except Exception:
            max_latency = 5.0
        due = min(now + max(0.5, float(delay or 4.0)), _SPLIT_CONTINUITY_FIRST_DIRTY_AT + max_latency)
        if _SPLIT_CONTINUITY_TIMER is not None:
            try: _SPLIT_CONTINUITY_TIMER.cancel()
            except Exception: pass
        _SPLIT_CONTINUITY_TIMER = _split_threading.Timer(max(0.05, due - now), _split_continuity_checkpoint_fire_v270)
        _SPLIT_CONTINUITY_TIMER.daemon = True
        _SPLIT_CONTINUITY_TIMER.start()
    return True

# Any logical save, not only finance, now requests remote durability.  The worker
# coalesces these calls, so Telegram handlers do not wait for MEGA.
_V263_BASE_SAVE_DATA = save_data

def save_data(d, chat_ids=None, full=False, root_only=False):
    result = _V263_BASE_SAVE_DATA(d, chat_ids=chat_ids, full=full, root_only=root_only)
    # Non-Telegram/background mutations need their own freshness marker.  Telegram
    # updates receive exactly one marker after the handler, avoiding extra hot-path IO.
    try:
        if not _split_inside_telegram_update_v264():
            _split_touch_state_revision_r18('logical_save_bg')
    except Exception:
        pass
    try:
        # Heavy all-chat shadow is background-only during normal READY operation.
        ready_fn = globals().get('runtime_is_ready')
        if full or not (callable(ready_fn) and ready_fn()):
            user_state_shadow_capture_v265('logical_save')
        else:
            _cid = None
            if chat_ids is not None:
                try:
                    _src = list(chat_ids) if isinstance(chat_ids,(list,tuple,set)) else [chat_ids]
                    _cid = int(_src[0]) if _src else None
                except Exception: _cid = None
            split_schedule_continuity_checkpoint_v270(_cid, 'logical_save', delay=4.0)
    except Exception:
        pass
    try:
        # R20: only meaningful configuration generations arm the independent capsule.
        # Normal finance/window saves therefore do not serialize the full user-state
        # shadow and cannot steal CPU from FAST navigation.
        _r20_cp = _r20_latest_config_checkpoint() if '_r20_latest_config_checkpoint' in globals() else {}
        _r20_gen = int((_r20_cp or {}).get('generation') or 0)
        if _r20_gen > int(globals().get('_R20_CAPSULE_LAST_GEN_SENT', 0) or 0):
            r20_schedule_durable_capsule('config_generation:' + str(_r20_gen), delay=2.0)
    except Exception:
        pass
    try:
        if not bool(globals().get('_V241_RESTORE_ACTIVE', False)):
            _split_mark_state_changed_v264('logical_save')
            # Boot migrations can call save_data many times. They are local-only until
            # READY, then R6 emits one final canonical snapshot instead of 4-10 GETs.
            ready_fn = globals().get('runtime_is_ready')
            is_ready = bool(ready_fn()) if callable(ready_fn) else False
            if is_ready or _split_inside_telegram_update_v264():
                split_schedule_worker_sync_v262(reason='logical_save', delay=0.6)
            else:
                _SPLIT_STATE['sync_pending'] = True
                _SPLIT_STATE['sync_reason'] = 'boot_coalesced'
    except Exception:
        pass
    return result


# Persist RAM-only sessions after every successfully executed Telegram update.
_V263_BASE_EXECUTE_TELEGRAM_PAYLOAD = _execute_telegram_payload

def _execute_telegram_payload(payload: dict, update_id=None, update_chat_id=None, update_type: str='other'):
    _SPLIT_UPDATE_CONTEXT.active = True
    _SPLIT_UPDATE_CONTEXT.finance_dirty = False
    finance_dirty = False
    try:
        result = _V263_BASE_EXECUTE_TELEGRAM_PAYLOAD(payload, update_id, update_chat_id, update_type)
    finally:
        finance_dirty = bool(getattr(_SPLIT_UPDATE_CONTEXT, 'finance_dirty', False))
        _SPLIT_UPDATE_CONTEXT.active = False
        _SPLIT_UPDATE_CONTEXT.finance_dirty = False
    try:
        _split_touch_state_revision_r18(f'tg:{str(update_type or "other")}', update_id)
    except Exception:
        pass
    try:
        cid = update_chat_id
        if cid is None and isinstance(payload, dict):
            cid = _extract_update_chat_id(payload)
        prefix = 'finance' if finance_dirty else 'tg'
        _reason = f'{prefix}:{str(update_type or "other")}'
        # Fast hot path: the business handler already committed its own SQLite rows.
        # Persist RAM/UI continuity once after the burst, not inline for every update.
        split_schedule_continuity_checkpoint_v270(cid, _reason, delay=float(_split_os.getenv('SPLIT_CONTINUITY_FINANCE_DELAY_SEC','4.0') or '4.0') if finance_dirty else float(_split_os.getenv('SPLIT_CONTINUITY_OTHER_DELAY_SEC','2.5') or '2.5'))
        split_schedule_worker_sync_v262(reason=f'continuity:{_reason}', delay=float(_split_os.getenv('SPLIT_FINANCE_SYNC_DELAY_SEC','0.8') or '0.8') if finance_dirty else float(_split_os.getenv('SPLIT_STATE_SYNC_DELAY_SEC','1.2') or '1.2'))
    except Exception as exc:
        try: log_error(f'CONTINUITY post-update R11: {exc}')
        except Exception: pass
    return result


def _split_push_snapshot_now_v263(reason='shutdown'):
    """Directly hand the final SQLite image to worker so shutdown cannot race a fetch job."""
    base, secret = _split_peer_base(), _split_secret()
    if not base or not secret:
        return False
    workdir = _split_tempfile.mkdtemp(prefix='v263_front_push_')
    raw = _split_os.path.join(workdir, 'bot_state.sqlite3')
    gz = raw + '.gz'
    try:
        SQLITE.backup_to(raw)
        with open(raw, 'rb') as src, _split_gzip.open(gz, 'wb', compresslevel=1) as dst:
            _split_shutil.copyfileobj(src, dst, length=1024 * 1024)
        # Seed shared durable cache before contacting worker; this survives worker deploys.
        try:
            _split_cache_snapshot_to_redis_v266(reason=str(reason or 'shutdown'), existing_gz=gz)
        except Exception:
            pass
        with open(gz, 'rb') as fh:
            body = fh.read()
        r = requests.post(
            base + '/internal/snapshot/upload', data=body,
            headers={**_split_headers('vys-262-front-final-push'), 'Content-Type': 'application/gzip', 'X-Snapshot-Reason': str(reason or '')[:120], 'X-Split-State-Token': _split_current_state_token_v264()},
            timeout=20,
        )
        if 200 <= r.status_code < 300:
            row={}
            try: row=r.json() if r.content else {}
            except Exception: row={}
            if str(row.get('status') or '') != 'stale_ignored':
                try:
                    _split_promote_delta_baseline_v267(raw)
                except Exception:
                    pass
                return True
            _SPLIT_STATE['sync_last_error'] = 'worker has a newer full state; stale front snapshot ignored'
            return False
        try: _SPLIT_STATE['sync_last_error'] = f'final push HTTP {r.status_code}: {r.text[:160]}'
        except Exception: pass
    except Exception as exc:
        try: _SPLIT_STATE['sync_last_error'] = 'final push: ' + str(exc)[:180]
        except Exception: pass
    finally:
        _split_shutil.rmtree(workdir, ignore_errors=True)
    return False


# R15 idle-only full rebase.  This replaces the old immediate full fallback that
# uploaded ~1.1 MB repeatedly during finance bursts.
def _split_idle_full_reconcile_fire_v270(reason='idle_reconcile'):
    global _SPLIT_FULL_TIMER
    with _SPLIT_FULL_LOCK:
        _SPLIT_FULL_TIMER = None
    try:
        _quiet_fn = globals().get('r27_user_quiet_for')
        quiet_for = float(_quiet_fn()) if callable(_quiet_fn) else max(0.0, _split_time.time() - float(globals().get('_SPLIT_LAST_CHANGE_AT') or 0.0))
    except Exception:
        quiet_for = 999999.0
    quiet_need = float(_split_os.getenv('R28_FULL_SNAPSHOT_USER_QUIET_SEC','30') or '30')
    if quiet_for < quiet_need:
        return _split_schedule_idle_full_reconcile_v270(reason, delay=max(3.0, quiet_need - quiet_for))
    min_gap = max(20.0, min(1800.0, float(_split_os.getenv('R28_FULL_SNAPSHOT_MIN_INTERVAL_SEC','300') or '300')))
    last_ok = float(_SPLIT_STATE.get('full_reconcile_last_ok') or 0.0)
    if last_ok > 0.0 and _split_time.time() - last_ok < min_gap:
        return _split_schedule_idle_full_reconcile_v270(reason, delay=max(3.0, min_gap - (_split_time.time() - last_ok)))
    ok = False
    try:
        try: _r27_flush_state_revision()
        except Exception: pass
        ok = bool(_split_push_snapshot_now_v263('idle:' + str(reason or '')[:100]))
    except Exception as exc:
        _SPLIT_STATE['full_reconcile_last_error'] = f'{type(exc).__name__}: {str(exc)[:180]}'
    if ok:
        _SPLIT_STATE['full_reconcile_pending'] = False
        _SPLIT_STATE['full_reconcile_last_ok'] = _split_time.time()
        _SPLIT_STATE['full_reconcile_last_error'] = ''
    else:
        _SPLIT_STATE['full_reconcile_pending'] = True
    return ok

def _split_schedule_idle_full_reconcile_v270(reason='need_full', delay=None):
    global _SPLIT_FULL_TIMER
    wait = float(delay if delay is not None else _split_os.getenv('R28_FULL_SNAPSHOT_USER_QUIET_SEC','30') or '20')
    with _SPLIT_FULL_LOCK:
        if _SPLIT_FULL_TIMER is not None:
            try: _SPLIT_FULL_TIMER.cancel()
            except Exception: pass
        _SPLIT_FULL_TIMER = _split_threading.Timer(max(5.0, wait), _split_idle_full_reconcile_fire_v270, args=(str(reason or 'need_full'),))
        _SPLIT_FULL_TIMER.daemon = True
        _SPLIT_FULL_TIMER.start()
    _SPLIT_STATE['full_reconcile_pending'] = True
    return True

# Snapshot download always captures the latest RAM continuity first.
_V263_BASE_SPLIT_FRONT_STATE_DOWNLOAD = split_front_state_download_v262

def split_front_state_download_v263():
    # R5: a worker fetch must be read-only. R4 rewrote continuity.saved_at on every
    # GET, making two identical snapshots look different and causing needless follow-ups.
    if not _split_authorized_request():
        return ({'ok': False}, 404)
    return _V263_BASE_SPLIT_FRONT_STATE_DOWNLOAD()

# Replace Flask endpoint function while keeping the already registered URL rule.
try:
    app.view_functions['split_front_state_download_v262'] = split_front_state_download_v263
except Exception:
    pass


# Final graceful shutdown: original code drains queues and saves full SQLite; then
# push that exact DB to worker cache immediately, before the process exits.
_V263_BASE_RUNTIME_GRACEFUL_SHUTDOWN = runtime_graceful_shutdown

def runtime_graceful_shutdown(signal_name: str='SIGTERM'):
    # R18 deploy handoff order is deliberate: do NOT put slow MEGA/archive work in
    # front of the only state copy a replacement instance needs.  First serialize all
    # user/config/RAM interaction state, immediately seed Redis + HEAVY, and only then
    # run the legacy drain/archive shutdown.  A second post-drain push closes the tail.
    try:
        continuity_checkpoint_v263(None, reason=f'shutdown-pre:{signal_name}', full=True, schedule=False)
        _split_touch_state_revision_r18(f'shutdown-pre:{signal_name}')
        _r20_capsule_push_now(f'shutdown-pre:{signal_name}')
        _split_push_snapshot_now_v263(f'shutdown-pre-fast:{signal_name}')
    except Exception as exc:
        try: log_error(f'CONTINUITY shutdown-pre R18: {exc}')
        except Exception: pass
    result = None
    try:
        result = _V263_BASE_RUNTIME_GRACEFUL_SHUTDOWN(signal_name)
    finally:
        try:
            continuity_checkpoint_v263(None, reason=f'shutdown-post:{signal_name}', full=True, schedule=False)
            _split_touch_state_revision_r18(f'shutdown-post:{signal_name}')
            _split_push_snapshot_now_v263(f'shutdown-post:{signal_name}')
        except Exception as exc:
            try: log_error(f'CONTINUITY shutdown-post R18: {exc}')
            except Exception: pass
    return result


# R6 loader-order safety: 99_web_runtime loads data before this final module.
# The base load_data now restores the shadow early, and this second idempotent overlay
# protects already-loaded data if a future module order changes again.
try:
    data = user_state_shadow_apply_v265(data)
    try:
        _fac = (data or {}).get('finance_active_chats') or {}
        finance_active_chats.clear()
        for _cid, _enabled in _fac.items():
            if _enabled:
                try: finance_active_chats.add(int(_cid))
                except Exception: pass
    except Exception:
        pass
    try:
        _bf = (data or {}).get('backup_flags') or {}
        backup_flags['drive'] = bool(_bf.get('drive', backup_flags.get('drive', True)))
        backup_flags['channel'] = bool(_bf.get('channel', backup_flags.get('channel', True)))
    except Exception:
        pass
except Exception as _r6_live_apply_exc:
    try: log_error(f'R6 live user-state apply: {_r6_live_apply_exc}')
    except Exception: pass

# The DB was restored by start_front.py before bot.py was loaded, so RAM continuity
# can safely be rehydrated here, before main() marks the bot READY.
_CONTINUITY_BOOT_REPORT_V263 = continuity_restore_v263()


# R5 deploy-continuity rule: Telegram already keeps the old messages on its side.
# Re-sending/re-editing every restored chat on boot is both unnecessary and unsafe:
# stale historic chat ids can return 400 "chat not found".  Preserve the restored
# message ids/state and resume lazily when that chat next interacts with the bot.
def _split_schedule_startup_main_windows_v264(delay: float=3.0):
    try:
        log_info('CONTINUITY R5: startup UI replay skipped; restored Telegram messages are kept in place')
    except Exception:
        pass
    return True

schedule_startup_main_windows = _split_schedule_startup_main_windows_v264

# R6: all callback families emitted by the current bot must have a declared marker.
# Broad family declarations are intentional: dynamic task/space/reminder IDs vary,
# while the marker family is stable. This removes recurring NOT_DECLARED failures.
_R6_MARKER_FAMILIES = {
    'cat_page:*':'Ф3201', 'sp:*':'Ф3202', 'v149:*':'Ф3203', 'v152:*':'Ф3204',
    'v153:file:*':'Ф3205', 'v153:restore:*':'Ф3205', 'v156:*':'Ф3206', 'v157:*':'Ф3207',
    'v160:*':'Ф3208', 'v164:*':'Ф3209', 'v167:*':'Ф3210', 'v169:*':'Ф3211',
    'v171:*':'Ф3212', 'v172:*':'Ф3213', 'v174:*':'Ф3214', 'v176:*':'Ф3215',
    'v196:*':'Ф3216', 'v213:*':'Ф3217', 'v217:*':'Ф3218', 'v218:*':'Ф3219',
    'v219:*':'Ф3220', 'v221:*':'Ф3221', 'v223:*':'Ф3222', 'v229:*':'Ф3223',
    'v232:*':'Ф3224', 'v233:*':'Ф3225', 'v242:system_snapshot:*':'Ф3226', 'v261:*':'Ф3227',
    'expense_quick_buttons_toggle':'Ф3228', 'reminder_ui_mode_toggle':'Ф3229',
    'journal_toggle_open':'Ф3230', 'journal_name_edit:*':'Ф3231', 'journal_name_reset:*':'Ф3231',
    'keepalive_self_toggle':'Ф3232', 'keepalive_self_now':'Ф3232', 'keepalive_self_interval':'Ф3232',
    'keepalive_auto_toggle':'Ф3233', 'keepalive_auto_interval':'Ф3233',
    'keepalive_peer':'Ф3234', 'keepalive_peer_toggle':'Ф3234', 'keepalive_peer_now':'Ф3234',
    'keepalive_peer_clear':'Ф3234', 'keepalive_peer_interval':'Ф3234', 'keepalive_peer_url':'Ф3234',
    'keepalive_peer_url_cancel':'Ф3234',
    'keepalive_peer_set:*':'Ф3234', 'keepalive_self_set:*':'Ф3232', 'keepalive_auto_set:*':'Ф3233',
    # R6 second-pass audit: callbacks created through helper functions / variables.
    'v163_exp_end_today:*':'Ф116', 'v220:*':'Ф3235', 'exp_excel_dollar_toggle:*':'Ф179',
    'exp_send:*':'Ф3236',
    'fvcat_show:*':'Ф3237', 'fvcat_wthu:*':'Ф3237', 'fvcat_today:*':'Ф3237',
    'fvcat_desc:*':'Ф3237', 'fvcat_add:*':'Ф3237', 'fvcat_edit_menu:*':'Ф3237',
    'fvcat_edit_pick:*':'Ф3237', 'fvcat_del_menu:*':'Ф3237', 'fvcat_del_toggle:*':'Ф3237',
    'fvcat_del_selected:*':'Ф3237',
}
try:
    for _r6_key, _r6_marker in _R6_MARKER_FAMILIES.items():
        WINDOW_MARKER_CONSTANTS.setdefault(_r6_key, _r6_marker)
except Exception:
    pass

# Render liveness must stay HTTP 200 during boot; /readyz remains the strict readiness gate.
def _r6_root_liveness():
    ready = bool(globals().get('runtime_is_ready', lambda: False)())
    return ({'ok': True, 'role': 'front', 'ready': ready, 'phase': (globals().get('_RUNTIME_STATE') or {}).get('phase')}, 200)
try:
    app.view_functions['index'] = _r6_root_liveness
except Exception:
    pass

# Suppress boot-time snapshot storms and publish exactly one fully migrated state at READY.
_V265_BASE_RUNTIME_MARK_READY = runtime_mark_ready
def runtime_mark_ready(detail: str=''):
    result = _V265_BASE_RUNTIME_MARK_READY(detail)
    try:
        user_state_shadow_capture_v265('boot_ready')
        continuity_capture_v263('boot_ready')
        _split_touch_state_revision_r18('boot_ready')
        _split_mark_state_changed_v264('boot_ready')
        # Establish an exact binary base on HEAVY immediately after every boot.
        # The POST is tiny; HEAVY performs the job asynchronously and pulls the snapshot.
        _split_request_worker_full_sync_r18('boot_ready_exact_rebase')
        r20_schedule_durable_capsule('boot_ready', delay=1.0)
        split_schedule_worker_sync_v262(reason='boot_ready', delay=0.8)
    except Exception as exc:
        try: log_error(f'R6 boot-ready sync: {exc}')
        except Exception: pass
    return result

try:
    _r6_missing = [k for k in ('v229:tasks:single_window','v149:google:sheet','v149:google:test','v149:google:history') if not window_marker_is_declared(k)]
    if _r6_missing:
        log_error('R6 marker registry incomplete: ' + ','.join(_r6_missing))
except Exception:
    pass

# ---------------------------------------------------------------------------
# R7 system polish: fast finance post-commit, definitive chat removal,
# beginner-friendly Google setup, and heavy CSV/XLSX/Drive generation on worker.
R7_SYSTEM_POLISH = 'vys262-r7-system-polish'

# --- Finance: one derived-state pass and one visual repaint per logical change. ---
def _r7_rebuild_month_short_ids_after_normalize(chat_id: int, store: dict) -> None:
    daily = store.get('daily_records', {}) or {}
    month_counters = {}
    usd_month_counters = {}
    for dk in sorted(daily.keys()):
        month_key = str(dk)[:7]
        month_counters.setdefault(month_key, 1)
        usd_month_counters.setdefault(month_key, 1)
        recs = sorted(daily.get(dk, []) or [], key=record_sort_key)
        daily[dk] = recs
        for rec in recs:
            if not isinstance(rec, dict):
                continue
            try:
                if callable(globals().get('ensure_finance_record_uid')):
                    ensure_finance_record_uid(int(chat_id), rec)
            except Exception:
                pass
            has_usd = bool(float(rec.get('usd_amount', 0) or 0))
            usd_only = bool(rec.get('usd_only', False))
            if not usd_only:
                rec['short_id'] = f"R{month_counters[month_key]}"
                month_counters[month_key] += 1
            elif has_usd:
                rec['short_id'] = f"U{usd_month_counters[month_key]}"
            if has_usd:
                rec['usd_short_id'] = f"U{usd_month_counters[month_key]}"
                usd_month_counters[month_key] += 1
    store['records'] = [r for dk in sorted(daily.keys()) for r in daily.get(dk, []) if isinstance(r, dict)]


def _r7_finance_changed_now(chat_id: int, day_key: str | None=None, reason: str='change'):
    """R7: local finance commit stays synchronous; all derived work is one debounced pass."""
    chat_id = int(chat_id)
    day_key = str(day_key or get_chat_store(chat_id).get('current_view_day') or today_key())[:10]
    try:
        finance_cache_invalidate(chat_id, f'finance_changed:{reason}:r7')
    except Exception:
        pass
    with locked_chat(chat_id):
        store = get_chat_store(chat_id)
        store['current_view_day'] = day_key
        # One normalization only.  Older path normalized inside recalc and again in
        # rebuild_month_short_ids, which was noticeable on chats with long histories.
        normalize_chat_records(chat_id)
        store = get_chat_store(chat_id)
        store.pop('_finance_hotpath_pending_normalize_r15', None)
        store.pop('_finance_hotpath_pending_normalize_r16', None)
        store['balance'] = sum(float(r.get('amount', 0) or 0) for r in store.get('records', []) or [] if isinstance(r, dict))
        _r7_rebuild_month_short_ids_after_normalize(chat_id, store)
        try:
            _snapshot_active_currency_ledger(store, _ensure_currency_ledgers(store))
        except Exception:
            pass
        if callable(globals().get('persist_finance_chat_local_fast')):
            persist_finance_chat_local_fast(chat_id)
    # Nothing below blocks the Telegram handler or holds chat_lock.
    try:
        schedule_quick_backup(chat_id, MEGA_DELTA_PRIORITY_DELAY_SECONDS if mega_backup_priority_enabled() else MEGA_DELTA_DELAY_SECONDS)
    except Exception:
        pass
    try:
        schedule_financial_window_refresh(chat_id, day_key, reason=f'r7:{reason}', delay=0.015)
    except Exception:
        pass
    try:
        schedule_finance_postcommit_background_v243(chat_id, reason=f'r7:{reason}', delay=0.30)
    except Exception:
        pass

# finance_changed() resolves this name at execution time.
globals()['_finance_changed_now'] = _r7_finance_changed_now


def _r7_linked_edit_postcommit(origin_chat_id: int, origin_msg_id: int, touched_days: dict, repaint_copies: bool):
    """Linked edit already normalized, renumbered and committed each touched chat.

    Do not immediately run finance_changed() and repeat the same DB work.  Only repaint
    each affected UI once and schedule the common background aggregate/durability pass.
    """
    for cid, day_key in list((touched_days or {}).items()):
        try:
            schedule_financial_window_refresh(int(cid), str(day_key or ''), reason='linked_edit_r16_fast', delay=0.01)
        except Exception:
            pass
        # R16 hot edit intentionally skipped full normalize; schedule exactly one
        # delayed canonical reconcile after the immediate user-visible repaint.
        try:
            finance_changed(int(cid), str(day_key or ''), reason='linked_edit_r16_reconcile', delay=0.18)
        except Exception:
            pass
    if repaint_copies and origin_chat_id and origin_msg_id:
        try:
            _v262_background_repaint_copies(int(origin_chat_id), int(origin_msg_id))
        except Exception:
            pass

globals()['_v262_postcommit_linked_edit'] = _r7_linked_edit_postcommit


# R7 finance bulk-delete postcommit: callers already committed the normalized chat.
def _r7_v262_finance_postcommit_job(chat_id: int, day_key: str, reason: str):
    cid=int(chat_id); dk=str(day_key or '')
    try: finance_cache_invalidate(cid, f'r7:{reason}')
    except Exception: pass
    try: schedule_financial_window_refresh(cid, dk, reason=f'r16-fast:{reason}', delay=0.01)
    except Exception: pass
    try: finance_changed(cid, dk, reason=f'r16-reconcile:{reason}', delay=0.18)
    except Exception: pass

globals()['_v262_finance_postcommit_job']=_r7_v262_finance_postcommit_job

# R9.2: chat-removal classification is implemented canonically in 00_core.py.
# Do not rebind probe_bot_in_chat here: bot.py runtime-contract requires its
# owner to remain 00_core.py.

# --- Google UX: three-step setup, service email, open current sheet, auto-test. ---
_R7_GOOGLE_INFO_CACHE = {'ts': 0.0, 'data': {}}

def _r7_google_worker_info(fetch: bool=True):
    now=_split_time.time()
    cached=dict(_R7_GOOGLE_INFO_CACHE.get('data') or {})
    if cached and (not fetch or now-float(_R7_GOOGLE_INFO_CACHE.get('ts') or 0) < 600):
        return cached
    if not fetch:
        return cached
    base = _split_peer_base()
    if not base or not _split_secret():
        return cached
    try:
        r = requests.get(base + '/internal/google/info', headers=_split_headers('vys-262-front-google-info'), timeout=8)
        payload = r.json() if r.content else {}
        if 200 <= r.status_code < 300 and payload.get('ok'):
            _R7_GOOGLE_INFO_CACHE.update(ts=now, data=dict(payload))
            return dict(payload)
    except Exception:
        pass
    return cached


def _r7_google_status_text(tenant_id):
    tid = str(tenant_id)
    row = tenant_get(tid) or {}
    cfg = tenant_google_config(tid)
    raw = str(cfg.get('spreadsheet_id') or '')
    if not raw and tid == str(globals().get('TENANT_PLATFORM_ID') or ''):
        raw = str(_split_os.getenv('GOOGLE_SHEETS_SPREADSHEET_ID', '') or '')
    # Opening /google must be instant: use cached/persisted email only. The worker is
    # contacted when the user presses step 1 or when access is tested.
    info = _r7_google_worker_info(fetch=False)
    email = str(cfg.get('service_account_email') or info.get('service_email') or '')
    title = str(cfg.get('spreadsheet_title') or '')
    ready = bool(raw and title)
    target = title or ((_v149_mask_id(raw) if raw else 'не выбрана'))
    return (
        f"📊 GOOGLE EXCEL · {row.get('name') or tid}\n\n"
        f"Статус: {'✅ готово к выгрузке' if ready else '🟡 нужно подключить таблицу'}\n"
        f"Таблица: {target}\n"
        f"Service account: {email or 'Render #2'}\n\n"
        "Как подключить первый раз:\n"
        "1️⃣ Нажмите «Email для доступа» и добавьте этот email в Google Таблице: Поделиться → Редактор.\n"
        "2️⃣ Нажмите «Подключить таблицу» и пришлите ссылку на неё.\n"
        "3️⃣ Бот сам проверит доступ. Если всё хорошо — больше ничего настраивать не нужно.\n\n"
        "После этого кнопки Google-выгрузки сами используют выбранную таблицу."
    )[:3900]


def _r7_google_keyboard(tenant_id):
    tid = str(tenant_id)
    cfg = tenant_google_config(tid)
    raw = str(cfg.get('spreadsheet_id') or '')
    if not raw and tid == str(globals().get('TENANT_PLATFORM_ID') or ''):
        raw = str(_split_os.getenv('GOOGLE_SHEETS_SPREADSHEET_ID', '') or '')
    kb = types.InlineKeyboardMarkup(row_width=1)
    kb.row(IB('1️⃣ Email для доступа', callback_data='v149:google:service_email'))
    kb.row(IB('2️⃣ Подключить / сменить таблицу', callback_data='v149:google:sheet'))
    kb.row(IB('3️⃣ Проверить доступ', callback_data='v149:google:test'))
    if raw:
        try:
            sid = _v149_google_id(raw, 'sheet')
            kb.row(types.InlineKeyboardButton('🔗 Открыть текущую таблицу', url=f'https://docs.google.com/spreadsheets/d/{sid}/edit'))
        except Exception:
            pass
    settings = cfg.get('export_settings') or {}
    kb.row(IB(f"{('✅' if settings.get('sheet_enabled', True) else '⬜')} Автовыгрузка Sheets: {('ВКЛ' if settings.get('sheet_enabled', True) else 'ВЫКЛ')}", callback_data='v149:google:toggle_sheet'))
    kb.row(IB(f"📜 История ({len(cfg.get('history') or [])})", callback_data='v149:google:history'), IB(f"⚠️ Ошибки ({len(cfg.get('errors') or [])})", callback_data='v149:google:errors'))
    return kb


def _r7_google_test(tenant_id):
    ok, text = _split_tenant_google_test(str(tenant_id))
    if ok:
        try:
            m = re.search(r'Название:\s*(.+)', str(text))
            cfg = tenant_google_config(str(tenant_id))
            if m:
                cfg['spreadsheet_title'] = str(m.group(1)).strip()[:200]
            info = _r7_google_worker_info()
            if info.get('service_email'):
                cfg['service_account_email'] = str(info.get('service_email'))[:250]
            cfg['updated_at'] = _v149_now_iso()
            tenant_google_history(str(tenant_id), 'sheet_access_verified_r7', cfg.get('spreadsheet_title') or 'access OK', ok=True)
            tenant_google_persist(str(tenant_id), 'tenant_google_update')
        except Exception:
            pass
    return ok, text

_R7_BASE_GOOGLE_HANDLE = globals().get('tenant_google_handle_message')
_R7_BASE_V149_CALLBACK = globals().get('v149_extension_callback')


def _r7_google_handle_message(msg) -> bool:
    # Handle the table-link step ourselves so save + access test is one action.
    try:
        cid = int(msg.chat.id)
        uid = int(getattr(getattr(msg, 'from_user', None), 'id', 0) or 0)
        tid = str(tenant_id_for_chat(cid, create=False) or '')
        cfg = tenant_google_config(tid, create=False) if tid else {}
        wait = dict((cfg or {}).get('input_wait') or {})
        if wait and str(wait.get('kind') or '') == 'sheet' and int(wait.get('chat_id') or 0) == cid and int(wait.get('user_id') or 0) == uid:
            if str(getattr(msg, 'content_type', '')) != 'text':
                send_and_auto_delete(cid, 'Пришлите ссылку на Google Таблицу обычным текстом.', 10)
                return True
            value = str(getattr(msg, 'text', '') or '').strip()
            cfg['spreadsheet_id'] = _v149_google_id(value, 'sheet')
            cfg['spreadsheet_title'] = ''
            cfg['input_wait'] = {}
            cfg['updated_at'] = _v149_now_iso()
            tenant_google_persist(tid, 'tenant_google_update')
            try:
                DELAYED_SCHEDULER.cancel(f'v213-input-google:{tid}:{cid}:{uid}')
                _v172_delete_quiet(cid, int(wait.get('cancel_message_id') or 0))
                bot.delete_message(cid, msg.message_id)
            except Exception:
                pass
            ok, test_text = _r7_google_test(tid)
            if ok:
                bot.send_message(cid, '✅ Таблица подключена и доступ проверен.\n\n' + _r7_google_status_text(tid), reply_markup=_r7_google_keyboard(tid))
            else:
                bot.send_message(cid, '🟡 Ссылка сохранена, но доступа пока нет.\n\n' + test_text + '\n\nНажмите «Email для доступа», добавьте его как Редактора и затем «Проверить доступ».', reply_markup=_r7_google_keyboard(tid))
            return True
    except Exception as exc:
        try: send_and_auto_delete(int(msg.chat.id), '❌ Google: ' + str(exc)[:600], 20)
        except Exception: pass
        return True
    return bool(_R7_BASE_GOOGLE_HANDLE(msg)) if callable(_R7_BASE_GOOGLE_HANDLE) else False


def _r7_v149_extension_callback(call, data_str: str) -> bool:
    raw = str(data_str or '')
    if raw.startswith('v149:google:'):
        action = raw.split(':', 2)[2]
        cid = int(call.message.chat.id)
        uid = int(getattr(getattr(call, 'from_user', None), 'id', 0) or 0)
        ok_manage, tid = _v149_google_can_manage(cid, uid, owner_only=True)
        if not ok_manage:
            try: bot.answer_callback_query(call.id, 'Только владелец пространства', show_alert=True)
            except Exception: pass
            return True
        if action in {'service_email', 'connect'}:
            info = _r7_google_worker_info(fetch=False)
            email = str(info.get('service_email') or '')
            if email:
                bot.send_message(cid, '📧 Email service account:\n\n<code>' + email + '</code>\n\nОткройте свою Google Таблицу → «Поделиться» → добавьте этот email → права «Редактор».', parse_mode='HTML')
            else:
                _status = bot.send_message(cid, '⏳ Получаю email service account с Render #2…')
                _status_mid = int(getattr(_status, 'message_id', 0) or 0)
                def _r24_google_email_fetch(_cid=cid, _mid=_status_mid):
                    info2 = _r7_google_worker_info(fetch=True)
                    email2 = str(info2.get('service_email') or '')
                    text2 = ('📧 Email service account:\n\n<code>' + email2 + '</code>\n\nОткройте свою Google Таблицу → «Поделиться» → добавьте этот email → права «Редактор».') if email2 else '❌ Render #2 не отдал email service account. Проверьте GOOGLE_SERVICE_ACCOUNT_JSON.'
                    try: bot.edit_message_text(text2, chat_id=_cid, message_id=_mid, parse_mode='HTML')
                    except Exception: pass
                try: GENERAL_TASK_POOL.submit_unique(f'r24-google-email:{cid}', _r24_google_email_fetch)
                except Exception: pass
            try: bot.answer_callback_query(call.id)
            except Exception: pass
            return True
        if action == 'test':
            _status = bot.send_message(cid, '⏳ Проверяю доступ к Google на Render #2…')
            _status_mid = int(getattr(_status, 'message_id', 0) or 0)
            def _r24_google_test_fetch(_tid=str(tid), _cid=cid, _mid=_status_mid):
                try:
                    _ok, _text = _r7_google_test(_tid)
                    prefix = '✅ ' if _ok else '🟡 '
                    out = prefix + str(_text or '')
                except Exception as exc:
                    out = '❌ Google: ' + str(exc)[:600]
                try: bot.edit_message_text(out, chat_id=_cid, message_id=_mid)
                except Exception: pass
            try: GENERAL_TASK_POOL.submit_unique(f'r24-google-test:{tid}', _r24_google_test_fetch)
            except Exception: pass
            try: bot.answer_callback_query(call.id)
            except Exception: pass
            return True
        if action == 'sheet':
            _v149_google_wait(tid, 'sheet', cid, uid)
            bot.send_message(cid, '2️⃣ Пришлите сюда ссылку на Google Таблицу.\n\nПример: https://docs.google.com/spreadsheets/d/...\n\nСразу после ссылки бот сам проверит доступ. JSON-ключ сюда присылать не нужно.')
            try: bot.answer_callback_query(call.id)
            except Exception: pass
            return True
    return bool(_R7_BASE_V149_CALLBACK(call, raw)) if callable(_R7_BASE_V149_CALLBACK) else False

# Final Google bindings.
globals()['tenant_google_status_text'] = _r7_google_status_text
globals()['tenant_google_keyboard'] = _r7_google_keyboard
globals()['tenant_google_test'] = _r7_google_test
globals()['tenant_google_handle_message'] = _r7_google_handle_message
globals()['v149_extension_callback'] = _r7_v149_extension_callback
try:
    WINDOW_MARKER_CONSTANTS.setdefault('v149:google:service_email', 'Ф233')
except Exception:
    pass

# --- Heavy file export bridge: front prepares business rows, worker serializes/uploads. ---
_R7_BASE_SEND_EXPORT = globals().get('send_export_for_chat_to')
_R7_EXPORT_SEEN = {}
_R7_EXPORT_SEEN_LOCK = _split_threading.RLock()


def _r7_json_rows(rows):
    out = []
    for row in rows or []:
        vals = []
        for value in list(row or []):
            if isinstance(value, (str, int, float, bool)) or value is None:
                vals.append(value)
            elif isinstance(value, dict):
                vals.append({str(k): v for k, v in value.items() if isinstance(v, (str, int, float, bool)) or v is None})
            else:
                vals.append(str(value))
        out.append(vals)
    return out


def _r7_export_annotations_payload(annotations):
    out = {}
    for key, val in (annotations or {}).items():
        try:
            r, c = key
            out[f'{int(r)},{int(c)}'] = str(val)
        except Exception:
            pass
    return out


def _r7_worker_file_submit(body: dict):
    base = _split_peer_base()
    if not base or not _split_secret():
        raise RuntimeError('Render #2 не настроен для файлового экспорта')
    r = requests.post(base + '/internal/export/file', json=body, headers=_split_headers('vys-262-front-export-r7'), timeout=25)
    payload = r.json() if r.content else {}
    if 200 <= r.status_code < 300 and payload.get('ok'):
        return str(payload.get('job_id') or body.get('job_id') or '')
    raise RuntimeError(str(payload.get('error') or r.text[:500] or f'HTTP {r.status_code}'))


def _r7_send_export_for_chat_to(recipient_chat_id: int, target_chat_id: int, mode: str, day_key: str, file_type: str='csv', excel_style_override=None, excel_options_override=None, delivery: str='chat'):
    recipient_chat_id = int(recipient_chat_id); target_chat_id = int(target_chat_id)
    file_type = str(file_type or 'csv').lower().lstrip('.')
    delivery = str(delivery or 'chat').strip().lower()
    custom_options = normalize_excel_export_options(excel_options_override) if isinstance(excel_options_override, dict) else None
    style = str(excel_style_override or (excel_export_options_style(custom_options) if custom_options else excel_table_style(target_chat_id)) or 'old').strip().lower()
    force_google = delivery == 'google' or style == 'google_notes'
    # Google Sheets already has a dedicated worker path with richer formatting.
    if force_google:
        return _R7_BASE_SEND_EXPORT(recipient_chat_id, target_chat_id, mode, day_key, file_type, excel_style_override, excel_options_override, delivery) if callable(_R7_BASE_SEND_EXPORT) else False
    try:
        raw_mode = str(mode or 'all')
        if raw_mode.startswith('xlsxstat_'):
            raw_mode = raw_mode[len('xlsxstat_'):]
        clean_mode = raw_mode.replace('csv_', '').replace('xlsx_', '')
        if clean_mode == 'all_real': clean_mode = 'all'
        rows, label = _period_export_rows(target_chat_id, clean_mode, day_key)
        ext = 'xlsx' if file_type in {'xlsx', 'xlsxstat'} else 'csv'
        if not rows and ext != 'xlsx':
            send_info(recipient_chat_id, f'Нет данных {label}.')
            return True
        annotations = {}
        category_layout = False
        sheet_name = 'Экспорт'
        description_column = True if not custom_options else bool(custom_options.get('description_column'))
        annotations_enabled = bool(not custom_options or custom_options.get('comments') or custom_options.get('notes'))
        if file_type == 'xlsxstat':
            store = get_chat_store(target_chat_id)
            start_key, end_key = _period_export_bounds(store, clean_mode, day_key)
            payload_rows = build_exact_category_stats_xlsx_rows(target_chat_id, start_key, 0, end_key, 0)
            category_layout = True
            sheet_name = 'Статьи'
            if custom_options and not description_column:
                payload_rows, annotations = _category_rows_without_description(payload_rows)
                category_layout = 'category_compact'
            if not annotations_enabled: annotations = {}
            safe_chat = mega_safe_name(get_chat_display_name(target_chat_id), 'chat')
            display_name = f'{safe_chat}_{clean_mode}_{day_key}_excel_статьи.xlsx'
        elif ext == 'xlsx':
            store = get_chat_store(target_chat_id)
            start_key, _end_key = _period_export_bounds(store, clean_mode, day_key)
            opening = _opening_balance_before_exact(store, start_key, 0)
            if description_column:
                payload_rows = [['Дата', 'Описание', 'Приход', 'Расход']]
                for date_v, amount_v, note_v in rows:
                    try: parsed = parse_csv_amount(amount_v)
                    except Exception: parsed = 0.0
                    payload_rows.append(_xlsx_record_row(date_v, parsed, note_v))
                payload_rows = insert_blank_rows_between_days(payload_rows, header_rows=1)
                payload_rows = _xlsx_simple_rows_with_balances(payload_rows, opening, target_chat_id)
            else:
                payload_rows, annotations = _compact_simple_excel_rows_and_annotations(rows, opening, target_chat_id)
                if not annotations_enabled: annotations = {}
            display_name = export_display_filename(target_chat_id, clean_mode, day_key, 'xlsx')
        else:
            payload_rows = [['date', 'amount', 'note']]
            prev_day = None
            for row in rows or []:
                vals = list(row or [])
                cur_day = str(vals[0] if vals else '')
                if prev_day is not None and cur_day != prev_day:
                    payload_rows.append(['', '', ''])
                payload_rows.append(vals[:3] + [''] * max(0, 3-len(vals)))
                prev_day = cur_day
            display_name = export_display_filename(target_chat_id, clean_mode, day_key, 'csv')
        tenant_id = str(tenant_id_for_chat(target_chat_id, create=False) or TENANT_PLATFORM_ID)
        cfg = tenant_google_config(tenant_id, create=False) or {}
        body = {
            'job_id': _split_secrets.token_hex(12), 'recipient_chat_id': recipient_chat_id,
            'target_chat_id': target_chat_id, 'tenant_id': tenant_id,
            'file_type': ext, 'source_file_type': file_type, 'style': style,
            'sheet_name': sheet_name, 'category_layout': category_layout,
            'rows': _r7_json_rows(payload_rows), 'annotations': _r7_export_annotations_payload(annotations),
            'filename': display_name, 'label': str(label), 'chat_name': get_chat_display_name(target_chat_id),
            'delivery': delivery,
            'drive_folder_id': str(cfg.get('drive_folder_id') or ''),
        }
        jid = _r7_worker_file_submit(body)
        what = 'Google Drive' if delivery == 'drive' else ('Excel' if ext == 'xlsx' else 'CSV')
        bot.send_message(recipient_chat_id, f'⚡ {what} готовится на Render #2. Можно продолжать пользоваться ботом — результат придёт отдельным сообщением.')
        try: file_job_mark_external_delivery('Render #2 export', jid)
        except Exception: pass
        return True
    except Exception as exc:
        try: log_error(f'R7 worker export {get_chat_display_name(target_chat_id)}: {exc}')
        except Exception: pass
        # Safety fallback preserves monolith behaviour if worker is temporarily unavailable.
        if callable(_R7_BASE_SEND_EXPORT):
            return _R7_BASE_SEND_EXPORT(recipient_chat_id, target_chat_id, mode, day_key, file_type, excel_style_override, excel_options_override, delivery)
        return False


def _r7_export_result_seen(job_id: str) -> bool:
    now = _split_time.time()
    with _R7_EXPORT_SEEN_LOCK:
        for key, ts in list(_R7_EXPORT_SEEN.items()):
            if now - float(ts or 0) > 86400:
                _R7_EXPORT_SEEN.pop(key, None)
        if job_id in _R7_EXPORT_SEEN:
            return True
        _R7_EXPORT_SEEN[job_id] = now
        return False


def _r7_deliver_worker_export(body: dict):
    jid = str(body.get('job_id') or '')
    cid = int(body.get('recipient_chat_id') or 0)
    if not jid or not cid: return
    if not body.get('ok'):
        try: bot.send_message(cid, '❌ Экспорт Render #2: ' + str(body.get('error') or 'неизвестная ошибка')[:800])
        except Exception: pass
        return
    if str(body.get('delivery') or '') == 'drive':
        try: bot.send_message(cid, f"☁️ Google Drive · {body.get('label') or ''}: {body.get('chat_name') or ''}\n\n{body.get('url') or ''}", disable_web_page_preview=True)
        except Exception: pass
        return
    base = _split_peer_base()
    try:
        r = requests.get(base + '/internal/export/file/' + jid, headers=_split_headers('vys-262-front-export-fetch-r7'), timeout=90)
        if r.status_code != 200:
            raise RuntimeError(f'worker file HTTP {r.status_code}: {r.text[:240]}')
        import io as _r7_io
        fobj = _r7_io.BytesIO(r.content)
        fobj.name = str(body.get('filename') or ('export.' + str(body.get('file_type') or 'bin')))
        caption = str(body.get('caption') or '') or f"📂 {('Excel' if str(body.get('file_type')) == 'xlsx' else 'CSV')} {body.get('label') or ''}: {body.get('chat_name') or ''}"
        _tg_call_retry(bot.send_document, cid, fobj, caption=caption, timeout=120, purpose='r7_worker_export_send_document')
    except Exception as exc:
        try: bot.send_message(cid, '❌ Не удалось получить готовый файл с Render #2: ' + str(exc)[:600])
        except Exception: pass


@app.route('/internal/split/export-result', methods=['POST'])
def split_front_export_result_r7():
    if not _split_authorized_request():
        return ({'ok': False}, 404)
    body = request.get_json(silent=True) or {}
    jid = str(body.get('job_id') or '')
    if not jid:
        return ({'ok': False, 'error': 'job_id required'}, 400)
    if _r7_export_result_seen(jid):
        return ({'ok': True, 'duplicate': True}, 200)
    try:
        pool = globals().get('GENERAL_TASK_POOL') or globals().get('BACKGROUND_TASK_POOL')
        submitted = False
        if pool is not None and hasattr(pool, 'submit'):
            submitted = bool(pool.submit('r7-export-delivery:' + jid, _r7_deliver_worker_export, dict(body)))
        if not submitted:
            _split_threading.Thread(target=_r7_deliver_worker_export, args=(dict(body),), daemon=True).start()
    except Exception:
        _split_threading.Thread(target=_r7_deliver_worker_export, args=(dict(body),), daemon=True).start()
    return ({'ok': True, 'accepted': True}, 202)

globals()['send_export_for_chat_to'] = _r7_send_export_for_chat_to

# R7 marker coverage for the task callback that was seen in production plus Google UX.
try:
    WINDOW_MARKER_CONSTANTS.setdefault('v229:tasks:single_window', 'Ф54')
    WINDOW_MARKER_CONSTANTS.setdefault('v149:google:service_email', 'Ф233')
except Exception:
    pass

try:
    bot_journal('r7_system_polish_loaded', int(OWNER_ID or 0), 'finance=single-derived-pass; chat_probe=removed-classifier; google=3-step; export=worker')
except Exception:
    pass

# --- R7 exact-range export and strict Front Google isolation. ---
_R7_BASE_EXACT_EXPORT = globals().get('send_exact_range_export')


def _r7_send_exact_range_export(recipient_chat_id: int, target_chat_id: int, start_key: str, start_rid: int, end_key: str, end_rid: int, file_type: str, excel_style_override=None, excel_options_override=None, delivery: str='chat'):
    recipient_chat_id=int(recipient_chat_id); target_chat_id=int(target_chat_id)
    file_type=str(file_type or 'csv').lower()
    if file_type not in {'csv','xlsx','xlsxstat'}: file_type='csv'
    custom_options=normalize_excel_export_options(excel_options_override) if isinstance(excel_options_override,dict) else None
    style=str(excel_style_override or (excel_export_options_style(custom_options) if custom_options else excel_table_style(target_chat_id)) or 'old').strip().lower()
    delivery=str(delivery or 'chat').strip().lower()
    force_google=delivery=='google' or style=='google_notes'
    description_column=True if not custom_options else bool(custom_options.get('description_column'))
    annotations_enabled=bool(not custom_options or custom_options.get('comments') or custom_options.get('notes'))
    try:
        rows=_exact_export_rows(target_chat_id,start_key,int(start_rid),end_key,int(end_rid))
        if not rows:
            send_and_auto_delete(recipient_chat_id,'Нет записей в выбранном точном диапазоне.',10)
            return True
        if force_google:
            xrows=build_exact_category_stats_xlsx_rows(target_chat_id,start_key,int(start_rid),end_key,int(end_rid))
            annotations={}; layout='category'
            if custom_options and not description_column:
                xrows,annotations=_category_rows_without_description(xrows); layout='category_compact'
            title=f'{get_chat_display_name(target_chat_id)} — статьи — точный период'
            token=_v262_split_google_sheets_create_category_report(title,xrows,layout=layout,annotations_override=annotations if annotations_enabled else {},include_annotations=annotations_enabled,target_chat_id=target_chat_id,recipient_chat_id=recipient_chat_id,notify_result=True)
            jid=str(token).split(':',1)[1] if str(token).startswith('worker-job:') else ''
            if jid:
                bot.send_message(recipient_chat_id,'⚡ Google Excel точного периода готовится на Render #2. Ссылка придёт отдельным сообщением.')
            return True
        ext='xlsx' if file_type in {'xlsx','xlsxstat'} else 'csv'
        annotations={}; layout=False; sheet_name='Точный период'
        if file_type=='xlsxstat':
            payload_rows=build_exact_category_stats_xlsx_rows(target_chat_id,start_key,int(start_rid),end_key,int(end_rid))
            layout=True; sheet_name='Excel стат'
            if custom_options and not description_column:
                payload_rows,annotations=_category_rows_without_description(payload_rows); layout='category_compact'
            if not annotations_enabled: annotations={}
        elif ext=='xlsx':
            opening=_opening_balance_before_exact(get_chat_store(target_chat_id),start_key,int(start_rid))
            if description_column:
                payload_rows=[['Дата','Описание','Приход','Расход']]
                for date_v,amount_v,note_v in rows:
                    try: parsed=parse_csv_amount(amount_v)
                    except Exception: parsed=0.0
                    payload_rows.append(_xlsx_record_row(date_v,parsed,note_v))
                payload_rows=insert_blank_rows_between_days(payload_rows,header_rows=1)
                payload_rows=_xlsx_simple_rows_with_balances(payload_rows,opening,target_chat_id)
            else:
                payload_rows,annotations=_compact_simple_excel_rows_and_annotations(rows,opening,target_chat_id)
                if not annotations_enabled: annotations={}
        else:
            payload_rows=[['date','amount','note']]; prev=None
            for row in rows or []:
                vals=list(row or []); cur=str(vals[0] if vals else '')
                if prev is not None and cur!=prev: payload_rows.append(['','',''])
                payload_rows.append(vals[:3]+['']*max(0,3-len(vals))); prev=cur
        chat_name=_safe_export_name_part(get_chat_name_for_filename(target_chat_id) or get_chat_display_name(target_chat_id),f'chat_{target_chat_id}')
        start_label=fmt_date_backup(start_key).replace(':','.')
        end_label=fmt_date_backup(end_key).replace(':','.')
        display_name=f"{chat_name}_({start_label}-{end_label})_{('excel_стат' if file_type=='xlsxstat' else 'точный')}.{ext}"
        store=get_chat_store(target_chat_id)
        caption=f"🎯 {(('Excel стат ' if file_type=='xlsxstat' else 'Excel ') + _export_style_caption(style) if ext=='xlsx' else 'CSV')} — точный период\n▶️ {exact_boundary_text(store,start_key,start_rid,True)}\n⏹ {exact_boundary_text(store,end_key,end_rid,False)}"
        tid=str(tenant_id_for_chat(target_chat_id,create=False) or TENANT_PLATFORM_ID); cfg=tenant_google_config(tid,create=False) or {}
        body={'job_id':_split_secrets.token_hex(12),'recipient_chat_id':recipient_chat_id,'target_chat_id':target_chat_id,'tenant_id':tid,
              'file_type':ext,'source_file_type':file_type,'style':style,'sheet_name':sheet_name,'category_layout':layout,
              'rows':_r7_json_rows(payload_rows),'annotations':_r7_export_annotations_payload(annotations),'filename':display_name,
              'label':'точный период','chat_name':get_chat_display_name(target_chat_id),'caption':caption,'delivery':delivery,
              'drive_folder_id':str(cfg.get('drive_folder_id') or '')}
        _r7_worker_file_submit(body)
        bot.send_message(recipient_chat_id,f"⚡ {('Google Drive' if delivery=='drive' else 'Excel' if ext=='xlsx' else 'CSV')} точного периода готовится на Render #2. Можно продолжать пользоваться ботом.")
        return True
    except Exception as exc:
        try: log_error(f'R7 exact worker export {target_chat_id}: {exc}')
        except Exception: pass
        # If worker is down, keep the old local export only as an emergency compatibility fallback.
        if callable(_R7_BASE_EXACT_EXPORT):
            return _R7_BASE_EXACT_EXPORT(recipient_chat_id,target_chat_id,start_key,start_rid,end_key,end_rid,file_type,excel_style_override,excel_options_override,delivery)
        return False


globals()['send_exact_range_export']=_r7_send_exact_range_export

# Active front hooks must never perform Google OAuth/Drive/Sheets network work.
def _r7_front_google_forbidden(*args, **kwargs):
    raise RuntimeError('Google network work is isolated on Render #2. Use /google or the worker export path.')

def _r7_front_create_sheet_disabled(tenant_id: str, title: str='Финансы бота'):
    raise RuntimeError('Создайте Google Таблицу в своём аккаунте, расшарьте её service-account как Редактору и подключите через /google. Создание таблиц сервисным аккаунтом отключено, чтобы владельцем файла оставались вы.')

globals()['_google_access_token']=_r7_front_google_forbidden
globals()['tenant_google_upload_export']=_r7_front_google_forbidden
globals()['tenant_google_create_spreadsheet']=_r7_front_create_sheet_disabled

# v262

# --- R9 release note: Google visual formatting restored to original vys-262 on Worker. ---
R9_GOOGLE_STYLE = 'vys262-r9-google-style'
try:
    bot_journal('r9_release_loaded', int(OWNER_ID or 0), 'google=original-v262-colors; startup-summary=concise; r8-chat-removal=kept')
except Exception:
    pass


# --- R10 unified user UI, Worker status and menu entry points. ---
def _r10_age_text(ts):
    try:
        sec=max(0,int(_split_time.time()-float(ts or 0)))
    except Exception:
        return '—'
    if not ts: return '—'
    if sec < 5: return 'только что'
    if sec < 60: return f'{sec} сек назад'
    if sec < 3600: return f'{sec//60} мин назад'
    return f'{sec//3600} ч назад'


def _r10_worker_health_text(force=False):
    # R24: this formatter is cache-only. Network health refresh is always a second
    # stage so opening the status window can never wait up to 12 seconds.
    h=dict(_SPLIT_STATE.get('worker_health') or {})
    st=dict(h.get('state') or {})
    interval=max(30,min(1800,int(_split_os.getenv('PEER_PING_INTERVAL_SEC','120') or '120')))
    front_ok=bool(_SPLIT_STATE.get('peer_last_ok')) and (_split_time.time()-float(_SPLIT_STATE.get('peer_last_ok') or 0) <= interval*2.5)
    reverse_ok=bool(st.get('peer_last_ok')) and (_split_time.time()-float(st.get('peer_last_ok') or 0) <= interval*2.5)
    worker_ok=bool(h.get('ok')) and int(_SPLIT_STATE.get('peer_status') or 0) in range(200,300)
    google_ok=bool(h.get('google_configured'))
    redis_ok=bool(st.get('redis_cache_ok'))
    mega_ok=bool(h.get('mega_configured'))
    q=int(h.get('queue_size') or 0); gq=int(h.get('google_queue_size') or 0)
    linked='✅ связаны в обе стороны' if (front_ok and reverse_ok) else ('🟠 связь только в одну сторону' if (front_ok or reverse_ok) else '⛔ связи нет')
    err=str(_SPLIT_STATE.get('peer_last_error') or st.get('peer_last_error') or '').strip()
    lines=[
        '🛰 RENDER #2 · ТЯЖЁЛЫЙ КОНТУР', '',
        f"Worker: {('✅ жив' if worker_ok else '⛔ недоступен')} · {str(h.get('version') or '—')}",
        f'Пеленг: {linked}',
        f"Front → Worker: {('✅' if front_ok else '⛔')} · {_r10_age_text(_SPLIT_STATE.get('peer_last_ok'))}",
        f"Worker → Front: {('✅' if reverse_ok else '⛔')} · {_r10_age_text(st.get('peer_last_ok'))}",
        '',
        f'Очередь: обычная {q} · Google {gq}',
        f"Google: {('✅ настроен' if google_ok else '⛔ не настроен')} · последний успех {_r10_age_text(st.get('google_last_ok'))}",
        f"Redis: {('✅' if redis_ok else '🟠')} · delta {int(st.get('delta_since_checkpoint') or 0)} · rev {str(st.get('cache_revision') or '—')}",
        f"Delta sync: {int(st.get('delta_last_pages') or 0)} стр. · {int(st.get('delta_bytes') or 0)//1024} КБ всего",
        f"События: получено {int(st.get('event_received') or 0)} · commit {int(st.get('event_committed') or 0)} · зеркало {int(st.get('event_mirrored') or 0)} · ждут {int(st.get('event_pending') or 0)}",
        f"Hash-сверка: {_r10_age_text(st.get('reconcile_last_ok'))} · full-resync {int(st.get('reconcile_full_resyncs') or 0)}",
        f"MEGA checkpoint: {('✅ настроена' if mega_ok else '⛔ не настроена')} · {_r10_age_text(st.get('last_mega_upload_at'))}",
        f"Последняя синхронизация: {_r10_age_text(st.get('delta_last_at') or st.get('job_last_done') or st.get('last_snapshot_at'))}",
    ]
    if err and not worker_ok:
        lines += ['', 'Ошибка: '+err[:240]]
    return window_mark('\n'.join(lines), 'Ф270')


def _r10_worker_health_keyboard():
    kb=types.InlineKeyboardMarkup(row_width=2)
    kb.row(IB('🔄 Проверить сейчас', callback_data='r10:worker:refresh'))
    kb.row(IB('📊 Google Excel', callback_data='v149:google:status'))
    kb.row(IB('🔙 В Инфо', callback_data='r10:worker:back'), IB('❌ Закрыть', callback_data='info_close'))
    return kb


_R10_BASE_INFO_KB = globals().get('build_info_keyboard')
def _r10_build_info_keyboard(chat_id: int):
    kb=_R10_BASE_INFO_KB(int(chat_id)) if callable(_R10_BASE_INFO_KB) else types.InlineKeyboardMarkup()
    if int(chat_id) != int(OWNER_ID or 0): return kb
    rows=_v177_info_rows(kb)
    callbacks={_v177_info_btn_cb(b) for row in rows for b in row or []}
    additions=[]
    if 'r10:worker:status' not in callbacks:
        additions.append([IB('🛰 Render #2 · состояние', callback_data='r10:worker:status')])
    if 'v149:google:status' not in callbacks:
        additions.append([IB('📊 Google Excel', callback_data='v149:google:status')])
    if additions:
        insert_at=len(rows)
        for i,row in enumerate(rows):
            if any((_v218_info_is_nav(b) for b in row or [])): insert_at=i; break
        rows[insert_at:insert_at]=additions
        kb=_v177_info_set_rows(kb,rows)
    return kb

globals()['build_info_keyboard']=_r10_build_info_keyboard

_R10_BASE_MAIN_KB = globals().get('build_main_keyboard')
def _r10_build_main_keyboard(day_key: str, chat_id=None):
    kb=_R10_BASE_MAIN_KB(day_key,chat_id) if callable(_R10_BASE_MAIN_KB) else types.InlineKeyboardMarkup()
    try: cid=int(chat_id if chat_id is not None else current_state_chat_id() or 0)
    except Exception: cid=0
    if cid != int(OWNER_ID or 0): return kb
    rows=_v217_rows(kb)
    callbacks={_v217_btn_cb(b) for row in rows for b in row or []}
    if 'v149:google:status' not in callbacks:
        rows.append([IB('📊 Google Excel', callback_data='v149:google:status'), IB('🛰 Render #2', callback_data='r10:worker:status')])
        kb=_v217_set_rows(kb,rows)
    return kb

globals()['build_main_keyboard']=_r10_build_main_keyboard

_R10_BASE_CONTOUR_GUARD = globals().get('contour_callback_guard')
def _r10_contour_callback_guard(call, resolved: str) -> bool:
    raw=str(resolved or '')
    if raw.startswith('r10:worker:'):
        try:
            cid=int(call.message.chat.id); uid=int(getattr(getattr(call,'from_user',None),'id',0) or 0)
        except Exception:
            return True
        if cid != int(OWNER_ID or 0) or uid != int(OWNER_ID or 0):
            try: bot.answer_callback_query(call.id,'Только основной владелец.',show_alert=True)
            except Exception: pass
            return True
        try: bot.answer_callback_query(call.id)
        except Exception: pass
        if raw == 'r10:worker:back':
            safe_edit(bot,call,build_info_text(cid),reply_markup=build_info_keyboard(cid)); return True
        # First render is always local/cache-only. Then Render #2 health is refreshed
        # in background and the same window is updated when the result arrives.
        safe_edit(bot,call,_r10_worker_health_text(force=False),reply_markup=_r10_worker_health_keyboard())
        try:
            _mid = int(call.message.message_id)
            _need_refresh = (raw == 'r10:worker:refresh') or (_split_time.time()-float(_SPLIT_STATE.get('peer_last_attempt') or 0) > 25)
            if _need_refresh:
                def _r24_refresh_worker_card(_cid=cid, _mid=_mid):
                    try: _split_ping_once()
                    except Exception: pass
                    try:
                        fast_ui_edit_message_text(_cid, _mid, _r10_worker_health_text(False), reply_markup=_r10_worker_health_keyboard(), purpose='r24_worker_health_refresh')
                    except Exception: pass
                _pool = globals().get('GENERAL_TASK_POOL')
                if _pool is not None:
                    _pool.submit_unique(f'r24-worker-health:{cid}', _r24_refresh_worker_card)
        except Exception:
            pass
        return True
    return bool(_R10_BASE_CONTOUR_GUARD(call,raw)) if callable(_R10_BASE_CONTOUR_GUARD) else False

globals()['contour_callback_guard']=_r10_contour_callback_guard
try:
    WINDOW_MARKER_CONSTANTS.setdefault('r10:worker:*','Ф270')
    WINDOW_MARKER_CONSTANTS.setdefault('r10:worker:status','Ф270')
    WINDOW_MARKER_CONSTANTS.setdefault('r10:worker:refresh','Ф270')
    WINDOW_MARKER_CONSTANTS.setdefault('r10:worker:back','Ф89')
    bot_journal('r10_unified_ui_loaded',int(OWNER_ID or 0),'service-ui=simple; worker-card=1; google-menu=1; peer=bidirectional')
    bot_journal('r11_fast_finance_loaded',int(OWNER_ID or 0),'finance-derived=async; chat-journal-default=on; legacy-front-delta=off')
except Exception:
    pass

# R12: establish the local delta base after all migrations/continuity wrappers are loaded.
# If the first Worker delta later reports a mismatch, the bridge automatically performs
# one full resync and re-bases; normal updates never GET the full SQLite again.
try:
    _split_init_delta_baseline_v267(force=True)
    bot_journal('r12_delta_sync_loaded', int(OWNER_ID or 0), 'sqlite-page-delta=on; full=checkpoint-or-mismatch')
    bot_journal('r13_event_journal_loaded', int(OWNER_ID or 0), 'raw-event-witness=worker/redis; commit-ack=on; reconcile-hash=rare')
except Exception as _r12_delta_boot_exc:
    try: log_error(f'R13 delta/event baseline init: {_r12_delta_boot_exc}')
    except Exception: pass

try:
    bot_journal('r14_internal_config_loaded', int(OWNER_ID or 0), 'Render ENV=credentials/addresses only; tunables=runtime_config.py')
except Exception:
    pass

R15_FAST_HOTPATH = 'vys262-r15-fast-hotpath'
try: bot_journal('r15_fast_hotpath_loaded', int(OWNER_ID or 0), 'remote witness fast; continuity background; full fallback idle-only')
except Exception: pass


# R21: every button has an immediate FAST stage. Heavy execution is a second stage.
# This override intentionally runs after 89_callback_final.py so it replaces the canonical
# monolith submitter without changing the v262 business handlers themselves.
R25_TRACE_FAST_PRIORITY_STAGE = 'per-r25-trace-fast-priority'
R24_ORDERED_HOT_RAM_STAGE = R25_TRACE_FAST_PRIORITY_STAGE
R22_ZERO_BLOCKING_BUTTON_STAGE = R24_ORDERED_HOT_RAM_STAGE
R21_EVERY_BUTTON_FAST_STAGE = R22_ZERO_BLOCKING_BUTTON_STAGE  # compatibility alias
try:
    R21_HEAVY_DISPATCH_TASK_POOL = KeyedTaskPool(
        'heavy-dispatch',
        _env_int('R21_HEAVY_DISPATCH_WORKERS', 4, 2, 8),
        _env_int('R21_HEAVY_DISPATCH_MAX_PENDING', 500, 50, 2000),
    )
except Exception:
    R21_HEAVY_DISPATCH_TASK_POOL = globals().get('GENERAL_TASK_POOL') or globals().get('EXPORT_TASK_POOL')

_R21_REMOTE_FILE_KINDS = {'period_export', 'exact_export', 'xlsx', 'csv'}
_R21_REMOTE_FILE_FUNCS = {'_r7_send_export_for_chat_to', '_r7_send_exact_range_export'}

def _r21_file_job_remote_capable(kind, func) -> bool:
    name = str(getattr(func, '__name__', '') or '')
    return str(kind or '') in _R21_REMOTE_FILE_KINDS or name in _R21_REMOTE_FILE_FUNCS

def _r21_file_job_key(chat_id: int, kind: str) -> str:
    # Coalesce only duplicate taps for the same chat+operation. R20's single global
    # file key made an unrelated download in another chat look busy.
    return f'r21:file:{int(chat_id)}:{str(kind or "file")[:80]}'

def _r21_file_job_lock_denied(meta: dict, text: str='Такая задача уже выполняется.'):
    key = str((meta or {}).get('key') or '')
    cid = int((meta or {}).get('chat_id') or 0)
    mid = int((meta or {}).get('status_msg_id') or 0)
    try:
        if mid:
            bot.edit_message_text(window_mark('⏳ '+str(text), 'Ф233'), chat_id=cid, message_id=mid)
    except Exception:
        pass
    try:
        with _FILE_JOB_LOCK:
            _FILE_JOB_STATE.pop(key, None)
    except Exception:
        pass

def _r21_interactive_file_dispatch_runner(job_meta: dict, func, args, kwargs):
    """Acquire distributed single-flight only after the callback has returned.

    No Redis/Key Value RTT is ever in front of a Telegram button in R21.  For split-capable
    exports this runner only prepares/dispatches the Render #2 job; the expensive file
    generation happens on HEAVY.  Runtime-only diagnostics that require live FAST process
    data stay on the low-priority export pool, never on the callback lane.
    """
    meta = dict(job_meta or {})
    cid = int(meta.get('chat_id') or 0)
    kind = str(meta.get('kind') or 'file')
    kv_name = f'interactive_file_job:r21:{cid}:{kind}'
    token = None
    backend = 'local'
    fn = globals().get('kv_distributed_lock_try_v248')
    if callable(fn):
        try:
            allowed, token, backend = fn(kv_name, 900)
        except Exception:
            allowed, token, backend = (True, None, 'local_fallback')
        if not allowed:
            _r21_file_job_lock_denied(meta)
            return False
    meta['kv_lock_token_v248'] = token
    meta['kv_lock_backend_v248'] = backend
    meta['kv_lock_name_v259'] = kv_name
    return _interactive_file_job_runner(meta, func, args, kwargs)

def _r21_submit_interactive_file_job(chat_id: int, kind: str, label: str, func, *args, **kwargs) -> tuple[bool, str]:
    """R21 FAST half of every file/export button.

    Synchronous path: RAM duplicate check -> Telegram status window -> local queue submit.
    It performs no Redis lock, save_data(), backup, MEGA, Google or file construction.
    """
    cid = int(chat_id)
    kind_s = str(kind or 'file')
    label_s = str(label or 'Задача')
    key = _r21_file_job_key(cid, kind_s)
    now_m = time.monotonic()
    with _FILE_JOB_LOCK:
        existing = _FILE_JOB_STATE.get(key)
        if isinstance(existing, dict):
            return (False, 'Такая задача уже выполняется')
        meta = {
            'key': key, 'chat_id': cid, 'kind': kind_s, 'label': label_s,
            'queued_monotonic': now_m, 'started_monotonic': 0.0,
            'phase': 'передаю Render #2' if _r21_file_job_remote_capable(kind_s, func) else 'в фоне',
            'status_msg_id': None, 'last_ui_monotonic': 0.0,
        }
        _FILE_JOB_STATE[key] = meta

    # One visible UI operation is allowed in the FAST half. Do not persist this transient
    # message id: after deploy it is intentionally disposable.
    try:
        phase = str(meta.get('phase') or 'в фоне')
        text = _v159_file_status_text(label_s, '0:00', phase) if callable(globals().get('_v159_file_status_text')) else f'⏳ {label_s}\nЭтап: {phase}'
        msg = bot.send_message(cid, text)
        mid = int(getattr(msg, 'message_id', 0) or 0)
        if mid:
            with _FILE_JOB_LOCK:
                if isinstance(_FILE_JOB_STATE.get(key), dict):
                    _FILE_JOB_STATE[key]['status_msg_id'] = mid
            meta['status_msg_id'] = mid
    except Exception:
        pass

    pool = R21_HEAVY_DISPATCH_TASK_POOL if _r21_file_job_remote_capable(kind_s, func) else EXPORT_TASK_POOL
    try:
        ok = bool(pool.submit_unique(key, _r21_interactive_file_dispatch_runner, dict(meta), func, args, kwargs))
    except Exception:
        ok = False
    if not ok:
        with _FILE_JOB_LOCK:
            _FILE_JOB_STATE.pop(key, None)
        return (False, 'Очередь фоновых задач заполнена')
    try:
        _v160_schedule(f'v160:file-tick:{key}', internal_timer_seconds('process_status_refresh', 10.0), _file_job_tick, key)
    except Exception:
        pass
    try:
        bot_journal('r21_fast_file_stage', cid, f'kind={kind_s}; remote={int(_r21_file_job_remote_capable(kind_s, func))}; pool={getattr(pool,"name","")}')
    except Exception:
        pass
    return (True, 'Запущено')

globals()['submit_interactive_file_job'] = _r21_submit_interactive_file_job

try:
    bot_journal('r21_every_button_fast_loaded', int(OWNER_ID or 0),
                'all_callbacks=fast-stage; heavy=second-stage; redis-lock=background; file-singleflight=chat+kind')
except Exception:
    pass
# v262
