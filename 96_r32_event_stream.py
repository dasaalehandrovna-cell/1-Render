# v262
"""R32 logical state event stream.

FAST hot-path rule is preserved: SQLite mutations only enqueue tiny descriptors.
Serialization and SQLite reads for remote state events happen later on a separate
connection/background thread.  HEAVY receives only changed logical rows, rebuilds
its restore DB, and archives immutable event segments.
"""
import gzip as _r32_gzip
import hashlib as _r32_hashlib
import json as _r32_json
import os as _r32_os
import queue as _r32_queue
import secrets as _r32_secrets
import sqlite3 as _r32_sqlite3
import threading as _r32_threading
import time as _r32_time

_R32_EVENT_STREAM_ENABLED = str(_r32_os.getenv('R32_EVENT_STREAM_ENABLED','1') or '1').strip().lower() in {'1','true','yes','on','да'}
_R32_EVENT_Q = _r32_queue.Queue(maxsize=max(1000,min(50000,int(_r32_os.getenv('R32_EVENT_QUEUE_MAX','20000') or '20000'))))
_R32_EVENT_STATE={'queued':0,'sent':0,'batches':0,'bytes':0,'last_ok':0.0,'last_error':'','dropped':0,'full_runtime_uploads_blocked':0,'private_peer':False,'inflight':0}
_R32_SQLITE_PATCHED=False


def _r32_ready():
    try:
        fn=globals().get('runtime_is_ready')
        return bool(fn()) if callable(fn) else False
    except Exception: return False


def _r32_peer_base_impl():
    raw=str(_r32_os.getenv('PEER_PRIVATE_URL','') or '').strip().rstrip('/')
    private=bool(raw)
    if not raw: raw=str(_r32_os.getenv('PEER_SERVICE_URL','') or '').strip().rstrip('/')
    if raw and not raw.startswith(('http://','https://')):
        looks_private=private or raw.endswith('.internal') or '.internal:' in raw or (raw.startswith('render-') and ':' in raw)
        raw=('http://' if looks_private else 'https://')+raw
    _R32_EVENT_STATE['private_peer']=bool(private or (raw.startswith('http://') if raw else False))
    return raw

if callable(globals().get('_split_peer_base')):
    _R32_LEGACY_SPLIT_PEER_BASE=globals().get('_split_peer_base')
    def _split_peer_base():
        return _r32_peer_base_impl() or _R32_LEGACY_SPLIT_PEER_BASE()


def _r32_descriptor(kind,key,ids=None):
    return {'kind':str(kind or '')[:60],'key':str(key or '')[:220],'ids':ids or {},'revision':int(_r32_time.time_ns()),'created_at':_r32_time.time(),'event_id':f'r32_{_r32_time.time_ns()}_{_r32_secrets.token_hex(5)}'}


def _r32_enqueue_descriptor(kind,key,ids=None):
    if not _R32_EVENT_STREAM_ENABLED or not _r32_ready(): return False
    try:
        _desc=_r32_descriptor(kind,key,ids)
        _R32_EVENT_Q.put_nowait(_desc)
        _R32_EVENT_STATE['queued']=int(_R32_EVENT_STATE.get('queued') or 0)+1
        _R32_EVENT_STATE['last_revision_queued']=max(int(_R32_EVENT_STATE.get('last_revision_queued') or 0),int(_desc.get('revision') or 0))
        st=globals().get('_SPLIT_STATE')
        if isinstance(st,dict): st['r32_event_queued']=int(st.get('r32_event_queued') or 0)+1; st['r32_event_pending']=_R32_EVENT_Q.qsize()
        return True
    except _r32_queue.Full:
        _R32_EVENT_STATE['dropped']=int(_R32_EVENT_STATE.get('dropped') or 0)+1
        try: log_error('R32 state-event queue full; raw Telegram witness remains authoritative')
        except Exception: pass
        return False
    except Exception as exc:
        _R32_EVENT_STATE['last_error']=f'{type(exc).__name__}: {str(exc)[:180]}'; return False


def _r32_db_path():
    try:
        obj=globals().get('SQLITE')
        if obj is not None and getattr(obj,'path',None): return str(obj.path)
    except Exception: pass
    return str(_r32_os.getenv('DB_FILE','bot_state.sqlite3') or 'bot_state.sqlite3')


def _r32_decode(raw,default=None):
    try: return _r32_json.loads(raw) if raw is not None else default
    except Exception: return default


def _r32_materialize(desc):
    """Read the committed value on a separate SQLite connection, never SQLITE.lock."""
    kind=str(desc.get('kind') or ''); ids=desc.get('ids') or {}; payload={}
    if kind in {'delete_chat','delete_cold'}:
        payload=dict(ids)
    else:
        con=_r32_sqlite3.connect(_r32_db_path(),timeout=5)
        try:
            if kind=='set_kv':
                k=str(ids.get('k') or ''); row=con.execute('SELECT v FROM kv WHERE k=?',(k,)).fetchone()
                if row is None: return None
                payload={'k':k,'v':_r32_decode(row[0])}
            elif kind=='save_chat':
                cid=str(ids.get('chat_id') or ''); row=con.execute('SELECT v FROM chats WHERE chat_id=?',(cid,)).fetchone()
                if row is None: return _r32_make_event(desc,{'chat_id':cid},kind_override='delete_chat')
                payload={'chat_id':cid,'v':_r32_decode(row[0],{})}
            elif kind=='prune_chats':
                payload={'keep':[str(r[0]) for r in con.execute('SELECT chat_id FROM chats').fetchall()]}
            elif kind=='set_meta':
                mk=str(ids.get('kind') or ''); kk=str(ids.get('k') or ''); row=con.execute('SELECT v FROM meta WHERE kind=? AND k=?',(mk,kk)).fetchone()
                if row is None: return None
                payload={'kind':mk,'k':kk,'v':_r32_decode(row[0])}
            elif kind=='set_cold':
                cid=str(ids.get('chat_id') or ''); kk=str(ids.get('k') or ''); row=con.execute('SELECT v FROM cold_fields WHERE chat_id=? AND k=?',(cid,kk)).fetchone()
                if row is None: return _r32_make_event(desc,{'chat_id':cid,'k':kk},kind_override='delete_cold')
                payload={'chat_id':cid,'k':kk,'v':_r32_decode(row[0])}
            elif kind=='set_cold_many':
                cid=str(ids.get('chat_id') or ''); keys=[str(x) for x in (ids.get('keys') or [])]; items={}
                for kk in keys:
                    row=con.execute('SELECT v FROM cold_fields WHERE chat_id=? AND k=?',(cid,kk)).fetchone()
                    if row is not None: items[kk]=_r32_decode(row[0])
                payload={'chat_id':cid,'items':items}
            else: return None
        finally: con.close()
    return _r32_make_event(desc,payload)


def _r32_make_event(desc,payload,kind_override=None):
    body={'schema':32,'event_id':str(desc.get('event_id') or ''),'revision':int(desc.get('revision') or 0),'created_at':float(desc.get('created_at') or _r32_time.time()),'kind':str(kind_override or desc.get('kind') or '')[:60],'key':str(desc.get('key') or '')[:220],'payload':payload,'front_version':str(globals().get('VERSION') or 'Пер-R36')}
    raw=_r32_json.dumps(body,ensure_ascii=False,separators=(',',':'),default=str).encode('utf-8'); body['sha256']=_r32_hashlib.sha256(raw).hexdigest(); return body


def _r34_encode_events(events):
    obj={'schema':32,'sent_at':_r32_time.time(),'events':list(events or [])}
    return _r32_gzip.compress(_r32_json.dumps(obj,ensure_ascii=False,separators=(',',':'),default=str).encode('utf-8'),compresslevel=1)


def _r34_partition_events(events):
    """Freeze materialized events once, then split only the serialized event list.

    Target is deliberately well below the HEAVY hard limit.  A large single logical
    row is sent alone and may use the dedicated large-event endpoint.
    """
    target=max(64,min(2048,int(_r32_os.getenv('R34_EVENT_TARGET_WIRE_KB','384') or '384')))*1024
    packets=[]; cur=[]
    for ev in list(events or []):
        trial=cur+[ev]; wire=_r34_encode_events(trial)
        if cur and len(wire)>target:
            packets.append({'events':cur,'wire':_r34_encode_events(cur)})
            cur=[ev]
        else:
            cur=trial
    if cur: packets.append({'events':cur,'wire':_r34_encode_events(cur)})
    return packets


def _r32_build_packet(rows):
    """R34: materialize SQLite once, then create size-bounded immutable packets."""
    events=[]; latest={}
    for d in rows: latest[str(d.get('key') or d.get('event_id'))]=d
    for d in sorted(latest.values(),key=lambda x:int(x.get('revision') or 0)):
        ev=_r32_materialize(d)
        if ev: events.append(ev)
    return {'rows':rows,'events':events,'packets':_r34_partition_events(events)}


def _r34_post_events(events, wire, large=False):
    base=_r32_peer_base_impl(); secret=str(_r32_os.getenv('PEER_SHARED_SECRET','') or '').strip()
    if not base or not secret: raise RuntimeError('R34 peer URL/secret not configured')
    endpoint='/internal/state/event-large' if large else '/internal/state/events'
    r=requests.post(base+endpoint,data=wire,headers={'X-Peer-Secret':secret,'User-Agent':'per-r34-state-events','Content-Type':'application/json','Content-Encoding':'gzip'},timeout=max(2.0,min(30.0,float(_r32_os.getenv('R32_EVENT_POST_TIMEOUT_SEC','8') or '8'))))
    if r.status_code==413 and not large:
        if len(events)>1:
            mid=max(1,len(events)//2)
            _r34_post_events(events[:mid],_r34_encode_events(events[:mid]),False)
            _r34_post_events(events[mid:],_r34_encode_events(events[mid:]),False)
            return True
        return _r34_post_events(events,wire,True)
    if not (200 <= r.status_code < 300): raise RuntimeError(f'HEAVY state events HTTP {r.status_code}: {r.text[:220]}')
    try:
        payload=r.json() if r.content else {}
        ack=int(payload.get('durable_revision') or payload.get('max_revision') or max([int(x.get('revision') or 0) for x in events] or [0]))
        applied_ack=int(payload.get('applied_revision') or (ack if bool(payload.get('apply_ok',True)) else 0))
    except Exception:
        ack=max([int(x.get('revision') or 0) for x in events] or [0]); applied_ack=0
    _R32_EVENT_STATE['last_revision_acked']=max(int(_R32_EVENT_STATE.get('last_revision_acked') or 0),ack)
    _R32_EVENT_STATE['last_revision_applied_peer']=max(int(_R32_EVENT_STATE.get('last_revision_applied_peer') or 0),applied_ack)
    _R32_EVENT_STATE['sent']=int(_R32_EVENT_STATE.get('sent') or 0)+len(events)
    _R32_EVENT_STATE['batches']=int(_R32_EVENT_STATE.get('batches') or 0)+1
    _R32_EVENT_STATE['bytes']=int(_R32_EVENT_STATE.get('bytes') or 0)+len(wire)
    _R32_EVENT_STATE['last_ok']=_r32_time.time(); _R32_EVENT_STATE['last_error']=''
    st=globals().get('_SPLIT_STATE')
    if isinstance(st,dict):
        st['r32_event_sent']=int(st.get('r32_event_sent') or 0)+len(events); st['r32_event_batches']=int(st.get('r32_event_batches') or 0)+1
        st['r32_event_bytes']=int(st.get('r32_event_bytes') or 0)+len(wire); st['r32_event_pending']=_R32_EVENT_Q.qsize(); st['r32_event_last_ok']=_r32_time.time(); st['r32_event_last_error']=''; st['r34_event_last_revision_acked']=ack; st['r35_event_last_revision_applied_peer']=applied_ack
    return True


def _r32_send_packet(packet):
    packets=list(packet.get('packets') or [])
    for part in packets:
        _r34_post_events(list(part.get('events') or []),part.get('wire') or b'',False)
    return True


def _r32_send_batch(rows):
    return _r32_send_packet(_r32_build_packet(rows))


def _r32_sender_loop():
    packet=None; backoff=0.5
    while True:
        if packet is None:
            rows=[]
            try: rows.append(_R32_EVENT_Q.get(timeout=1.0))
            except _r32_queue.Empty: continue
            delay=max(0.08,min(1.5,float(_r32_os.getenv('R32_EVENT_BATCH_DELAY_SEC','0.35') or '0.35'))); _r32_time.sleep(delay)
            max_events=max(1,min(256,int(_r32_os.getenv('R32_EVENT_BATCH_MAX','96') or '96')))
            while len(rows)<max_events:
                try: rows.append(_R32_EVENT_Q.get_nowait())
                except _r32_queue.Empty: break
            try:
                _R32_EVENT_STATE['inflight']=len(rows); packet=_r32_build_packet(rows)
            except Exception as exc:
                _R32_EVENT_STATE['last_error']=f'build {type(exc).__name__}: {str(exc)[:220]}'
                for row in rows:
                    try: _R32_EVENT_Q.put_nowait(row)
                    except Exception: pass
                    try: _R32_EVENT_Q.task_done()
                    except Exception: pass
                _R32_EVENT_STATE['inflight']=0; _r32_time.sleep(min(5.0,backoff)); backoff=min(60.0,backoff*1.8); continue
        try:
            _r32_send_packet(packet); backoff=0.5
            for _ in packet.get('rows') or []:
                try: _R32_EVENT_Q.task_done()
                except Exception: pass
            packet=None; _R32_EVENT_STATE['inflight']=0
        except Exception as exc:
            _R32_EVENT_STATE['last_error']=f'{type(exc).__name__}: {str(exc)[:220]}'
            st=globals().get('_SPLIT_STATE')
            if isinstance(st,dict): st['r32_event_last_error']=_R32_EVENT_STATE['last_error']
            # Frozen materialized packet only; never reread SQLite on HTTP retries.
            _r32_time.sleep(backoff); backoff=min(60.0,backoff*1.8)

def r32_flush_state_events(timeout=8.0):
    deadline=_r32_time.time()+max(0.0,float(timeout or 0.0))
    while _r32_time.time()<deadline:
        if _R32_EVENT_Q.empty() and int(_R32_EVENT_STATE.get('inflight') or 0)==0: return True
        _r32_time.sleep(0.05)
    return _R32_EVENT_Q.empty() and int(_R32_EVENT_STATE.get('inflight') or 0)==0


def _r32_patch_sqlite():
    global _R32_SQLITE_PATCHED
    if _R32_SQLITE_PATCHED: return
    cls=globals().get('SQLiteState')
    if cls is None: return
    def patch(name,builder):
        old=getattr(cls,name,None)
        if not callable(old) or getattr(old,'_r32_patched',False): return
        def wrapped(self,*args,**kwargs):
            result=old(self,*args,**kwargs)
            try:
                for kind,key,ids in (builder(args,kwargs,result) or []): _r32_enqueue_descriptor(kind,key,ids)
            except Exception as exc: _R32_EVENT_STATE['last_error']=f'capture {name}: {type(exc).__name__}: {str(exc)[:160]}'
            return result
        wrapped.__name__=getattr(old,'__name__',name); wrapped.__doc__=getattr(old,'__doc__',None); wrapped._r32_patched=True; setattr(cls,name,wrapped)
    patch('set_kv',lambda a,k,r:[('set_kv',f'kv:{a[0] if a else k.get("key","")}',{'k':str(a[0] if a else k.get('key',''))})])
    patch('save_chat',lambda a,k,r:[('save_chat',f'chat:{a[0] if a else k.get("chat_id","")}',{'chat_id':str(a[0] if a else k.get('chat_id',''))})])
    patch('save_chats',lambda a,k,r:[('prune_chats','chats:index',{})]+[('save_chat',f'chat:{cid}',{'chat_id':str(cid)}) for cid in (((a[0] if a else k.get('chats')) or {}).keys() if isinstance((a[0] if a else k.get('chats')) or {},dict) else [])])
    patch('delete_chat',lambda a,k,r:[('delete_chat',f'chat:{a[0] if a else k.get("chat_id","")}',{'chat_id':str(a[0] if a else k.get('chat_id',''))})])
    patch('set_meta',lambda a,k,r:[('set_meta',f'meta:{a[0] if a else k.get("kind","")}:{a[1] if len(a)>1 else k.get("key","")}',{'kind':str(a[0] if a else k.get('kind','')),'k':str(a[1] if len(a)>1 else k.get('key',''))})])
    patch('set_cold',lambda a,k,r:[('set_cold',f'cold:{a[0] if a else k.get("chat_id","")}:{a[1] if len(a)>1 else k.get("key","")}',{'chat_id':str(a[0] if a else k.get('chat_id','')),'k':str(a[1] if len(a)>1 else k.get('key',''))})])
    def cold_many(a,k,r):
        cid=str(a[0] if a else k.get('chat_id','')); items=(a[1] if len(a)>1 else k.get('items')) or {}; return [('set_cold_many',f'coldmany:{cid}',{'chat_id':cid,'keys':[str(x) for x in items.keys()]})]
    patch('set_cold_many',cold_many)
    patch('delete_cold',lambda a,k,r:[('delete_cold',f'cold:{a[0] if a else k.get("chat_id","")}:{a[1] if len(a)>1 else k.get("key","")}',{'chat_id':str(a[0] if a else k.get('chat_id','')),'k':str(a[1] if len(a)>1 else k.get('key',''))})])
    _R32_SQLITE_PATCHED=True

_r32_patch_sqlite()

# Normal runtime full mirroring is disabled. Emergency/manual code remains available
# in R98, but these scheduler entry points no longer arm it.
def split_schedule_worker_sync_v262(reason='change',delay=None):
    st=globals().get('_SPLIT_STATE')
    if isinstance(st,dict): st['sync_pending']=False; st['sync_reason']='r32-events:'+str(reason or '')[:120]
    return True

def _split_schedule_idle_full_reconcile_v270(reason='need_full',delay=None):
    _R32_EVENT_STATE['full_runtime_uploads_blocked']=int(_R32_EVENT_STATE.get('full_runtime_uploads_blocked') or 0)+1
    st=globals().get('_SPLIT_STATE')
    if isinstance(st,dict): st['full_reconcile_pending']=False; st['full_reconcile_last_error']='R34 event-stream: periodic full snapshot suppressed'
    return True

def _split_request_worker_full_sync_r18(reason='need_full'):
    return True,'R34 event-stream mode: full rebase not required'

def _split_push_snapshot_now_v263(reason='shutdown'):
    r32_flush_state_events(timeout=float(_r32_os.getenv('R32_SHUTDOWN_EVENT_FLUSH_SEC','8') or '8'))
    try: r20_schedule_durable_capsule('r32-shutdown:'+str(reason or '')[:80],delay=0.05)
    except Exception: pass
    return True

def r32_event_stream_status():
    row=dict(_R32_EVENT_STATE); row['pending']=_R32_EVENT_Q.qsize(); row['enabled']=bool(_R32_EVENT_STREAM_ENABLED); row['peer_base']=_r32_peer_base_impl(); return row

_r32_threading.Thread(target=_r32_sender_loop,name='per-r32-state-events',daemon=True).start()
# v262
