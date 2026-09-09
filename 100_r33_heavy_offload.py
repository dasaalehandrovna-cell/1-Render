# v262
"""Пер-R43: all user-requested heavy file/table/journal jobs are delegated to HEAVY.

This module is intentionally loaded last.  It does not touch the R28 direct-render
function.  The Telegram callback only creates the existing small status message and
queues a descriptor; state flush, serialization and HTTP happen on the background
heavy-dispatch pool.
"""
import datetime as _r33_datetime
import json as _r33_json
import os as _r33_os
import time as _r33_time

_LOCAL_SUBMIT_FILE_JOB = globals().get('submit_interactive_file_job')
_R33_HEAVY_FILE_KINDS = {
    'period_export','exact_export','xlsx','csv','tabl_lsx','json','json_full','sqlite',
    'runtime','journal','journal_current','window_markers','window_tz',
    'window_tz_archive'
}
# Future annotation/document buttons with the same prefix are heavy by contract.
try:
    _R21_REMOTE_FILE_KINDS.update(_R33_HEAVY_FILE_KINDS)
except Exception:
    pass


def _r33_safe_scalar(value):
    if value is None or isinstance(value,(str,int,float,bool)):
        return value
    if isinstance(value,(_r33_datetime.datetime,_r33_datetime.date)):
        return value.isoformat()
    if isinstance(value,(list,tuple,set)):
        return [_r33_safe_scalar(x) for x in value]
    if isinstance(value,dict):
        return {str(k):_r33_safe_scalar(v) for k,v in value.items()}
    return str(value)


def _r33_tenant_chat_ids(tid):
    try:
        fn=globals().get('tenant_chat_ids')
        return [int(x) for x in (fn(str(tid)) or [])] if callable(fn) and tid else []
    except Exception:
        return []


def _r33_export_body(kind,label,func_name,args,kwargs):
    a=list(args or ()); k=dict(kwargs or {})
    cid=int(a[0] if a else k.get('chat_id') or 0)
    body={
        'job_id': _split_secrets.token_hex(12) if '_split_secrets' in globals() else __import__('secrets').token_hex(12),
        'recipient_chat_id':cid,'target_chat_id':cid,'operation':str(kind),
        'label':str(label or kind),'chat_name':str(globals().get('get_chat_display_name',lambda x:str(x))(cid)),
        'delivery':'chat','front_release':'Пер-R43',
    }
    fn=str(func_name or '')
    if kind in {'period_export','xlsx'} or fn.endswith('send_export_for_chat_to'):
        # recipient, target, mode, day_key, file_type, style?, options?, delivery?
        if len(a)>=2: body['target_chat_id']=int(a[1])
        body['mode']=str(a[2] if len(a)>2 else k.get('mode') or 'all')
        body['day_key']=str(a[3] if len(a)>3 else k.get('day_key') or '')[:10]
        body['source_file_type']=str(a[4] if len(a)>4 else k.get('file_type') or ('xlsx' if kind=='xlsx' else 'csv')).lower().lstrip('.')
        body['file_type']='xlsx' if body['source_file_type'] in {'xlsx','xlsxstat','excel'} else 'csv'
        if len(a)>5 and a[5] is not None: body['style']=str(a[5])
        if len(a)>6 and isinstance(a[6],dict): body['excel_options']=_r33_safe_scalar(a[6])
        if len(a)>7: body['delivery']=str(a[7] or 'chat')
        body['operation']='period_export_query'
    elif kind=='exact_export' or fn.endswith('send_exact_range_export'):
        if len(a)>=2: body['target_chat_id']=int(a[1])
        body.update({'start_key':str(a[2] if len(a)>2 else '')[:10],'start_rid':int(a[3] if len(a)>3 else 0),
                     'end_key':str(a[4] if len(a)>4 else '')[:10],'end_rid':int(a[5] if len(a)>5 else 0)})
        body['source_file_type']=str(a[6] if len(a)>6 else 'csv').lower().lstrip('.')
        body['file_type']='xlsx' if body['source_file_type'] in {'xlsx','xlsxstat','excel'} else 'csv'
        if len(a)>7 and a[7] is not None: body['style']=str(a[7])
        if len(a)>8 and isinstance(a[8],dict): body['excel_options']=_r33_safe_scalar(a[8])
        if len(a)>9: body['delivery']=str(a[9] or 'chat')
        body['operation']='exact_export_query'
    elif kind=='csv':
        body.update({'operation':'period_export_query','mode':'all','day_key':'','source_file_type':'csv','file_type':'csv'})
    elif kind=='tabl_lsx':
        if len(a)>=2: body['target_chat_id']=int(a[1])
        body.update({'operation':'tabl_lsx','file_type':'xlsx','source_file_type':'xlsx'})
    elif kind=='json':
        body.update({'operation':'chat_json','file_type':'json'})
    elif kind=='json_full':
        scope=str(a[1] if len(a)>1 else k.get('scope') or 'global')
        tid=(a[2] if len(a)>2 else k.get('tenant_id'))
        body.update({'operation':'full_state','file_type':'gz','scope':scope,'tenant_id':str(tid or ''),
                     'tenant_chat_ids':_r33_tenant_chat_ids(tid) if scope=='tenant' else []})
    elif kind=='sqlite':
        body.update({'operation':'sqlite','file_type':'sqlite'})
    elif kind=='runtime':
        body.update({'operation':'runtime_zip','file_type':'zip','start_dt':_r33_safe_scalar(a[1] if len(a)>1 else None),
                     'end_dt':_r33_safe_scalar(a[2] if len(a)>2 else None)})
    elif kind in {'journal','journal_current'}:
        body.update({'operation':kind,'file_type':'txt','limit':int(a[1] if len(a)>1 else 5000)})
    elif kind=='bot_source':
        body.update({'operation':'bot_source','file_type':'py'})
    elif kind.startswith('window_'):
        body.update({'operation':kind,'file_type':'txt'})
    else:
        body.update({'operation':str(kind),'args':_r33_safe_scalar(a),'kwargs':_r33_safe_scalar(k)})
    # Google/Drive config lookup is small metadata only; all table construction/API calls stay on HEAVY.
    if str(body.get('delivery') or '').lower() in {'google','drive'}:
        try:
            tid=str(tenant_id_for_chat(int(body.get('target_chat_id') or cid),create=False) or TENANT_PLATFORM_ID)
            cfg=tenant_google_config(tid,create=False) or {}
            body['tenant_id']=tid
            body['spreadsheet_id']=str(cfg.get('spreadsheet_id') or cfg.get('sheet_id') or '')
            body['drive_folder_id']=str(cfg.get('drive_folder_id') or '')
        except Exception:
            pass
    # R35 diagnostics: capture only tiny RAM dictionaries on FAST; HEAVY still does
    # all serialization/archive construction. This keeps diagnostics about Render #1.
    if str(body.get('operation') or '') in {'runtime_zip','journal','journal_current'}:
        try:
            body['front_runtime_snapshot']=_r33_safe_scalar({
                'release':'Пер-R43',
                'captured_at':_r33_time.time(),
                'runtime':dict(globals().get('_RUNTIME_STATE') or {}),
                'split':dict(globals().get('_SPLIT_STATE') or {}),
                'state_events':dict(globals().get('_R32_EVENT_STATE') or {}),
            })
        except Exception: pass
    # R34 ordering fence: state-dependent jobs carry the newest queued revision.
    # FAST never waits for it; HEAVY waits/replays in its own queue.
    if str(body.get('operation') or '') in {'period_export_query','exact_export_query','tabl_lsx','chat_json','full_state','sqlite','window_markers','window_tz','window_tz_archive'}:
        try: body['required_revision']=int((_R32_EVENT_STATE or {}).get('last_revision_queued') or 0)
        except Exception: body['required_revision']=0
    # filename/caption are generated on HEAVY from the authoritative state.
    return body


def _r33_remote_file_adapter(kind,label,func_name,args,kwargs):
    # R34: never wait for global state synchronization on FAST.  The job carries a
    # revision fence and HEAVY waits for only the state it actually needs.
    body=_r33_export_body(str(kind),str(label),str(func_name),args,kwargs)
    try: _file_job_progress('передаю задание Render #2', force=True)
    except Exception: pass
    submit=globals().get('_r7_worker_file_submit')
    if not callable(submit): raise RuntimeError('R38 HEAVY export bridge unavailable')
    jid=submit(body)
    try: bot_journal('r35_heavy_file_accepted_legacy_guard',int(body.get('recipient_chat_id') or 0),f"kind={kind}; op={body.get('operation')}; job={jid}; required_revision={body.get('required_revision') or 0}")
    except Exception: pass
    # R35 intentionally does NOT mark accepted/queued as delivered here. The final
    # adapter defined below waits for the real FAST delivery callback.
    return True

# R47 FINALIZATION: no early submit override; R40 is the sole public owner.


# R34 parity: legacy direct CSV/XLSX helpers are also query-only HEAVY jobs.
# This catches commands/functions that historically bypassed submit_interactive_file_job.
def _r34_export_marker(*args,**kwargs): return True

def send_export_for_chat_to(recipient_chat_id:int,target_chat_id:int,mode:str,day_key:str,file_type:str='csv',excel_style_override=None,excel_options_override=None,delivery:str='chat'):
    kind='period_export'
    label=('Google Excel' if str(delivery or '').lower()=='google' else ('Excel' if str(file_type).lower().startswith('xlsx') else 'CSV'))+' экспорт'
    ok,_info=submit_interactive_file_job(int(recipient_chat_id),kind,label,_r34_export_marker,int(recipient_chat_id),int(target_chat_id),str(mode),str(day_key),str(file_type),excel_style_override,excel_options_override,str(delivery or 'chat'))
    return bool(ok)

def send_exact_range_export(recipient_chat_id:int,target_chat_id:int,start_key:str,start_rid:int,end_key:str,end_rid:int,file_type:str,excel_style_override=None,excel_options_override=None,delivery:str='chat'):
    label=('Google Excel' if str(delivery or '').lower()=='google' else ('Excel' if str(file_type).lower().startswith('xlsx') else 'CSV'))+' точный экспорт'
    ok,_info=submit_interactive_file_job(int(recipient_chat_id),'exact_export',label,_r34_export_marker,int(recipient_chat_id),int(target_chat_id),str(start_key),int(start_rid),str(end_key),int(end_rid),str(file_type),excel_style_override,excel_options_override,str(delivery or 'chat'))
    return bool(ok)

def send_tabl_lsx_for_chat(recipient_chat_id:int,target_chat_id:int):
    ok,_info=submit_interactive_file_job(int(recipient_chat_id),'tabl_lsx','Excel /tabl_lsx',_r34_export_marker,int(recipient_chat_id),int(target_chat_id))
    return bool(ok)

send_export_for_chat_to = send_export_for_chat_to
send_exact_range_export = send_exact_range_export
send_tabl_lsx_for_chat = send_tabl_lsx_for_chat

# Defensive R28 hot-path regression gate stays active. R34 itself contains no render queue.
try:
    _src=__import__('inspect').getsource(globals().get('fast_ui_edit_message_text'))
    if 'WINDOW_RENDER_TASK_POOL' in _src or '_perform_fast_ui_edit' not in _src:
        raise RuntimeError('R34 HOTPATH GUARD: R28 direct render contract changed')
except OSError:
    pass

try:
    bot_journal('r34_heavy_offload_loaded',int(OWNER_ID or 0),'unified-bot: files/tables/journals/json/full-state/sqlite/runtime/window-docs -> HEAVY; no FAST state barrier')
except Exception:
    pass

# ---------------------------------------------------------------------------
# Пер-R43: end-to-end HEAVY delivery control.
# 202/queued is only an acceptance ACK. The FAST file job remains open until
# Render #2's callback has actually delivered the result to Telegram/Google.
_R35_REMOTE_RESULT_LOCK = __import__('threading').RLock()
_R35_REMOTE_RESULT = {}
# R36: separate tiny delivery ledger. This is intentionally NOT the finance DB and
# never takes data_lock/SQLITE.lock. Redis still covers cross-container durability.
_R36_DELIVERY_DB = str(globals().get('DB_FILE') or 'data.sqlite3') + '.r36_delivery.sqlite3'
_R36_DELIVERY_DB_LOCK = __import__('threading').RLock()

def _r36_delivery_db_init():
    sql=__import__('sqlite3')
    with _R36_DELIVERY_DB_LOCK:
        con=sql.connect(_R36_DELIVERY_DB,timeout=2,check_same_thread=False)
        try:
            con.execute('PRAGMA journal_mode=WAL'); con.execute('PRAGMA synchronous=FULL'); con.execute('PRAGMA busy_timeout=2000')
            con.execute('CREATE TABLE IF NOT EXISTS delivery(job_id TEXT PRIMARY KEY,row_json TEXT NOT NULL,ts REAL NOT NULL)')
            con.commit()
        finally: con.close()

def _r36_delivery_local_set(jid,row):
    try:
        _r36_delivery_db_init(); sql=__import__('sqlite3')
        raw=_r33_json.dumps(row,ensure_ascii=False,separators=(',',':'),default=str)
        with _R36_DELIVERY_DB_LOCK:
            con=sql.connect(_R36_DELIVERY_DB,timeout=2,check_same_thread=False)
            try:
                con.execute('PRAGMA busy_timeout=2000')
                con.execute('INSERT INTO delivery(job_id,row_json,ts) VALUES(?,?,?) ON CONFLICT(job_id) DO UPDATE SET row_json=excluded.row_json,ts=excluded.ts',(str(jid),raw,float(row.get('ts') or _r33_time.time())))
                con.commit()
            finally: con.close()
    except Exception: pass

def _r36_delivery_local_get(jid):
    try:
        _r36_delivery_db_init(); sql=__import__('sqlite3')
        with _R36_DELIVERY_DB_LOCK:
            con=sql.connect(_R36_DELIVERY_DB,timeout=2,check_same_thread=False)
            try:
                con.execute('PRAGMA busy_timeout=2000'); r=con.execute('SELECT row_json FROM delivery WHERE job_id=?',(str(jid),)).fetchone()
            finally: con.close()
        obj=_r33_json.loads(r[0]) if r else {}
        return obj if isinstance(obj,dict) else {}
    except Exception: return {}

def _r35_delivery_redis_client():
    try:
        pkg=globals().get('_split_redis')
        url=str(__import__('os').getenv('REDIS_URL','') or '').strip()
        if pkg is None or not url: return None
        return pkg.Redis.from_url(url,socket_connect_timeout=1.0,socket_timeout=2.0,health_check_interval=30)
    except Exception:
        return None

def _r35_delivery_key(jid):
    return 'per:r35:front:delivery:'+str(jid or '')[:80]

def _r35_delivery_set(jid,state,body=None,error=''):
    row={'state':str(state or ''),'ts':_r33_time.time(),'body':_r33_safe_scalar(body or {}),'error':str(error or '')[:1000]}
    with _R35_REMOTE_RESULT_LOCK:
        _R35_REMOTE_RESULT[str(jid)]=row
    _r36_delivery_local_set(jid,row)
    try:
        c=_r35_delivery_redis_client()
        if c is not None:
            c.set(_r35_delivery_key(jid),_r33_json.dumps(row,ensure_ascii=False,separators=(',',':'),default=str),ex=172800)
    except Exception:
        pass
    return row

def _r35_delivery_get(jid):
    jid=str(jid or '')
    with _R35_REMOTE_RESULT_LOCK:
        row=dict(_R35_REMOTE_RESULT.get(jid) or {})
    local=_r36_delivery_local_get(jid)
    if isinstance(local,dict) and float(local.get('ts') or 0)>=float(row.get('ts') or 0): row=local
    try:
        c=_r35_delivery_redis_client()
        raw=c.get(_r35_delivery_key(jid)) if c is not None else None
        if raw:
            remote=_r33_json.loads(raw.decode('utf-8') if isinstance(raw,(bytes,bytearray)) else raw)
            if isinstance(remote,dict) and float(remote.get('ts') or 0)>=float(row.get('ts') or 0): row=remote
    except Exception:
        pass
    return row

def _r35_worker_file_submit(body:dict):
    base=globals().get('_split_peer_base',lambda:'')()
    headers_fn=globals().get('_split_headers')
    if not base or not globals().get('_split_secret',lambda:'')(): raise RuntimeError('Render #2 не настроен для файлового экспорта')
    # R36: assign once before the first network attempt. A lost 202 response can then
    # be retried safely without creating a second export.
    jid=str(body.get('job_id') or __import__('secrets').token_hex(12)).strip()[:80]
    body['job_id']=jid
    last=''
    attempts=max(2,min(6,int(__import__('os').getenv('R36_FILE_SUBMIT_ATTEMPTS',__import__('os').getenv('R35_FILE_SUBMIT_ATTEMPTS','4')) or '4')))
    timeout=max(8.0,min(90.0,float(__import__('os').getenv('R36_FILE_SUBMIT_TIMEOUT_SEC','45') or '45')))
    for attempt in range(1,attempts+1):
        try:
            hdr=headers_fn('per-r36-front-export') if callable(headers_fn) else {'X-Peer-Secret':str(__import__('os').getenv('PEER_SHARED_SECRET','') or '')}
            r=requests.post(base+'/internal/export/file',json=body,headers=hdr,timeout=timeout)
            payload={}
            if r.content:
                try:
                    obj=r.json(); payload=obj if isinstance(obj,dict) else {}
                except Exception:
                    payload={}
            status=str(payload.get('status') or '')
            accepted=200<=r.status_code<300 and (payload.get('ok') is True or status in {'queued','running','ready','delivering','delivered','done'})
            if accepted and payload.get('durable') is True:
                returned=str(payload.get('job_id') or jid)
                if returned!=jid:
                    last=f'Render #2 вернул другой job_id: {returned}'
                else:
                    return jid
            elif accepted:
                last='Render #2 принял задание без durable-подтверждения'
            else:
                body_text=''
                try: body_text=(r.text or '')[:500]
                except Exception: pass
                last=str(payload.get('error') or body_text or f'HTTP {r.status_code}')
            if 400<=r.status_code<500 and r.status_code not in {408,409,425,429}: break
        except Exception as exc:
            last=f'{type(exc).__name__}: {str(exc)[:400]}'
        if attempt<attempts: _r33_time.sleep(min(2.0,0.4*attempt))
    raise RuntimeError(last or 'Render #2 не подтвердил durable-приём задания')

_r7_worker_file_submit = _r35_worker_file_submit

def _r35_export_delivery_task(body):
    jid=str((body or {}).get('job_id') or '')
    delivered=False
    try:
        delivered=bool(globals().get('_r7_deliver_worker_export')(dict(body)))
    except Exception as exc:
        _r35_delivery_set(jid,'failed',body,error=f'{type(exc).__name__}: {str(exc)[:700]}')
        return
    if delivered:
        if bool((body or {}).get('ok')):
            _r35_delivery_set(jid,'done',body)
        else:
            _r35_delivery_set(jid,'done_error',body,error=str((body or {}).get('error') or 'HEAVY job failed'))
    else:
        _r35_delivery_set(jid,'failed',body,error='FAST delivery attempt failed')

def split_front_export_result_r35():
    if not globals().get('_split_authorized_request',lambda:False)(): return ({'ok':False},404)
    body=request.get_json(silent=True) or {}; jid=str(body.get('job_id') or '')
    if not jid: return ({'ok':False,'error':'job_id required'},400)
    row=_r35_delivery_get(jid); state=str(row.get('state') or ''); age=max(0.0,_r33_time.time()-float(row.get('ts') or 0))
    if state in {'done','done_error'}:
        return ({'ok':True,'delivered':True,'duplicate':True,'operation_ok':state=='done'},200)
    # A stale 'running' marker can survive a FAST restart. Allow HEAVY to retrigger it.
    if state=='running' and age<45:
        return ({'ok':True,'accepted':True,'delivered':False},202)
    _r35_delivery_set(jid,'running',body)
    try:
        pool=globals().get('GENERAL_TASK_POOL') or globals().get('BACKGROUND_TASK_POOL'); submitted=False
        if pool is not None and hasattr(pool,'submit'):
            submitted=bool(pool.submit('r36-export-delivery:'+jid,_r35_export_delivery_task,dict(body)))
        if not submitted:
            __import__('threading').Thread(target=_r35_export_delivery_task,args=(dict(body),),daemon=True,name='per-r36-front-delivery').start()
    except Exception:
        __import__('threading').Thread(target=_r35_export_delivery_task,args=(dict(body),),daemon=True,name='per-r36-front-delivery').start()
    return ({'ok':True,'accepted':True,'delivered':False},202)

try:
    # Keep the existing Flask route, replace only its implementation.
    app.view_functions['split_front_export_result_r7']=split_front_export_result_r35
except Exception:
    pass

def _r35_wait_remote_delivery(jid,body):
    timeout=max(60,min(7200,int(__import__('os').getenv('R36_FAST_JOB_WAIT_SEC',__import__('os').getenv('R35_FAST_JOB_WAIT_SEC','1800')) or '1800')))
    deadline=_r33_time.time()+timeout; last_progress=0.0
    while _r33_time.time()<deadline:
        row=_r35_delivery_get(jid); state=str(row.get('state') or '')
        if state=='done': return True
        if state=='done_error':
            b=row.get('body') if isinstance(row.get('body'),dict) else {}
            raise RuntimeError(str(row.get('error') or b.get('error') or 'Render #2 завершил задачу с ошибкой')[:900])
        now=_r33_time.time()
        if now-last_progress>5:
            try:
                phase='ожидаю доставку результата' if state in {'running','failed'} else 'Render #2 выполняет задачу'
                _file_job_progress(phase,force=True)
            except Exception: pass
            last_progress=now
        _r33_time.sleep(0.45)
    raise RuntimeError(f'Render #2 не подтвердил доставку за {timeout} сек.; job_id={jid}')

def _r33_remote_file_adapter(kind,label,func_name,args,kwargs):
    body=_r33_export_body(str(kind),str(label),str(func_name),args,kwargs)
    body['front_release']='Пер-R43'
    try: _file_job_progress('передаю задание Render #2',force=True)
    except Exception: pass
    submit=globals().get('_r7_worker_file_submit')
    if not callable(submit): raise RuntimeError('R38 HEAVY export bridge unavailable')
    jid=submit(body)
    existing=_r35_delivery_get(jid)
    if str(existing.get('state') or '') not in {'running','done','done_error'}:
        _r35_delivery_set(jid,'accepted',{'job_id':jid,'operation':body.get('operation'),'recipient_chat_id':body.get('recipient_chat_id')})
    try: bot_journal('r36_heavy_file_accepted',int(body.get('recipient_chat_id') or 0),f"kind={kind}; op={body.get('operation')}; job={jid}; required_revision={body.get('required_revision') or 0}")
    except Exception: pass
    _r35_wait_remote_delivery(jid,body)
    # This call runs inside the original FAST file-job context, so only now may the
    # canonical runner close the status window and release its single-flight lock.
    delivery=str(body.get('delivery') or 'chat').lower()
    delivered_kind='Telegram через Render #2' if delivery=='chat' else ('Google Sheets' if delivery=='google' else 'Google Drive')
    if not file_job_mark_external_delivery(delivered_kind,jid):
        raise RuntimeError('R36 delivery was confirmed but FAST file-job context was lost')
    return True

try:
    bot_journal('r36_transport_fix_loaded',int(OWNER_ID or 0),'accepted!=delivered; local+redis delivery ledger; safe HTTP/JSON; same-job retry; stale callback recovery')
except Exception:
    pass

# ---------------------------------------------------------------------------
# R38 resilient FAST -> HEAVY transport.
# A user job is first persisted in a local/Redis outbox and only then dispatched.
# Public Render/Cloudflare 429/5xx/HTML challenges are transport states, not user errors.
import sqlite3 as _r38_sqlite3
import threading as _r38_threading
import random as _r38_random

_R38_OUTBOX_DB = _r33_os.path.join(str(_r33_os.getenv('R38_OUTBOX_DIR','/tmp') or '/tmp'), 'per_r38_peer_outbox.sqlite3')
_R38_OUTBOX_LOCK = _r38_threading.RLock()
_R38_OUTBOX_PENDING_KEY = 'per:r38:front:peer_outbox:pending'
_R38_OUTBOX_PREFIX = 'per:r38:front:peer_outbox:'
_R38_OUTBOX_WAKE = _r38_threading.Event()
_R38_PEER_HTTP_LOCK = _r38_threading.RLock()
_R38_PEER_LAST_HTTP = 0.0
_R38_PEER_BLOCK_UNTIL = 0.0
_R38_PEER_STATE = {'accepted':0,'retries':0,'cloudflare':0,'http_5xx':0,'last_error':'','last_ok':0.0,'last_status':0}


def _r38_outbox_db_init():
    try:
        _r33_os.makedirs(_r33_os.path.dirname(_R38_OUTBOX_DB) or '.', exist_ok=True)
        with _R38_OUTBOX_LOCK:
            con=_r38_sqlite3.connect(_R38_OUTBOX_DB,timeout=3,check_same_thread=False)
            try:
                con.execute('PRAGMA journal_mode=WAL'); con.execute('PRAGMA synchronous=FULL'); con.execute('PRAGMA busy_timeout=3000')
                con.execute('CREATE TABLE IF NOT EXISTS outbox(job_id TEXT PRIMARY KEY,row_json TEXT NOT NULL,state TEXT NOT NULL,updated_at REAL NOT NULL)')
                con.execute('CREATE INDEX IF NOT EXISTS idx_r38_outbox_state ON outbox(state,updated_at)')
                con.commit()
            finally: con.close()
        return True
    except Exception:
        return False


def _r38_outbox_local_put(row):
    if not isinstance(row,dict) or not str(row.get('job_id') or ''): return False
    try:
        _r38_outbox_db_init(); obj=dict(row); obj['updated_at']=float(obj.get('updated_at') or _r33_time.time())
        raw=_r33_json.dumps(obj,ensure_ascii=False,separators=(',',':'),default=str)
        with _R38_OUTBOX_LOCK:
            con=_r38_sqlite3.connect(_R38_OUTBOX_DB,timeout=3,check_same_thread=False)
            try:
                con.execute('PRAGMA busy_timeout=3000')
                con.execute('INSERT INTO outbox(job_id,row_json,state,updated_at) VALUES(?,?,?,?) ON CONFLICT(job_id) DO UPDATE SET row_json=excluded.row_json,state=excluded.state,updated_at=excluded.updated_at',(str(obj['job_id']),raw,str(obj.get('state') or 'pending'),float(obj['updated_at'])))
                con.commit()
            finally: con.close()
        return True
    except Exception:
        return False


def _r38_outbox_local_get(jid):
    try:
        _r38_outbox_db_init()
        with _R38_OUTBOX_LOCK:
            con=_r38_sqlite3.connect(_R38_OUTBOX_DB,timeout=2,check_same_thread=False)
            try:
                con.execute('PRAGMA busy_timeout=2000'); row=con.execute('SELECT row_json FROM outbox WHERE job_id=?',(str(jid),)).fetchone()
            finally: con.close()
        obj=_r33_json.loads(row[0]) if row else {}
        return obj if isinstance(obj,dict) else {}
    except Exception: return {}


def _r38_outbox_local_pending(limit=200):
    out=[]
    try:
        _r38_outbox_db_init()
        with _R38_OUTBOX_LOCK:
            con=_r38_sqlite3.connect(_R38_OUTBOX_DB,timeout=2,check_same_thread=False)
            try:
                con.execute('PRAGMA busy_timeout=2000'); rows=con.execute("SELECT row_json FROM outbox WHERE state IN ('pending','retry') ORDER BY updated_at ASC LIMIT ?",(max(1,min(1000,int(limit))),)).fetchall()
            finally: con.close()
        for row in rows:
            try:
                obj=_r33_json.loads(row[0]);
                if isinstance(obj,dict): out.append(obj)
            except Exception: pass
    except Exception: pass
    return out


def _r38_outbox_redis_client():
    try: return _r35_delivery_redis_client()
    except Exception: return None


def _r38_outbox_key(jid): return _R38_OUTBOX_PREFIX+str(jid or '')[:80]


def _r38_outbox_put(row,pending=None):
    obj=dict(row or {}); jid=str(obj.get('job_id') or '')[:80]
    if not jid: return False
    obj['job_id']=jid; obj['updated_at']=_r33_time.time()
    local_ok=_r38_outbox_local_put(obj)
    c=_r38_outbox_redis_client(); redis_ok=False
    if c is not None:
        try:
            raw=_r33_json.dumps(obj,ensure_ascii=False,separators=(',',':'),default=str)
            pipe=c.pipeline(transaction=False); pipe.set(_r38_outbox_key(jid),raw,ex=604800)
            is_pending=(str(obj.get('state') or '') in {'pending','retry'}) if pending is None else bool(pending)
            if is_pending: pipe.sadd(_R38_OUTBOX_PENDING_KEY,jid)
            else: pipe.srem(_R38_OUTBOX_PENDING_KEY,jid)
            pipe.expire(_R38_OUTBOX_PENDING_KEY,604800); pipe.execute(); redis_ok=True
        except Exception: pass
    return bool(local_ok or redis_ok)


def _r38_outbox_get(jid):
    best=_r38_outbox_local_get(jid)
    c=_r38_outbox_redis_client()
    if c is not None:
        try:
            raw=c.get(_r38_outbox_key(jid))
            if raw:
                obj=_r33_json.loads(raw.decode('utf-8') if isinstance(raw,(bytes,bytearray)) else raw)
                if isinstance(obj,dict) and float(obj.get('updated_at') or 0)>=float(best.get('updated_at') or 0): best=obj
        except Exception: pass
    return best if isinstance(best,dict) else {}


def _r38_outbox_pending_rows_core(limit=200):
    rows={str(x.get('job_id')):x for x in _r38_outbox_local_pending(limit) if str(x.get('job_id') or '')}
    c=_r38_outbox_redis_client()
    if c is not None:
        try:
            ids=list(c.smembers(_R38_OUTBOX_PENDING_KEY) or [])[:max(1,min(1000,int(limit)))]
            for raw_jid in ids:
                jid=raw_jid.decode() if isinstance(raw_jid,(bytes,bytearray)) else str(raw_jid)
                obj=_r38_outbox_get(jid)
                if obj and float(obj.get('updated_at') or 0)>=float((rows.get(jid) or {}).get('updated_at') or 0): rows[jid]=obj
        except Exception: pass
    return list(rows.values())


def _r38_peer_transient_response(r):
    try: status=int(getattr(r,'status_code',0) or 0)
    except Exception: status=0
    text=''
    try: text=str(r.text or '')[:1200].casefold()
    except Exception: pass
    ctype=''
    try: ctype=str(r.headers.get('content-type','') or '').casefold()
    except Exception: pass
    html=('text/html' in ctype or '<!doctype html' in text or '<html' in text)
    cloud=html and any(x in text for x in ('just a moment','cloudflare','challenge','cf-ray'))
    transient=status in {0,408,425,429,500,502,503,504,520,521,522,523,524} or cloud
    return transient,cloud,status


def _r38_retry_after(r,attempt):
    try:
        raw=str(r.headers.get('Retry-After','') or '').strip()
        if raw: return max(1.0,min(120.0,float(raw)))
    except Exception: pass
    base=min(60.0, max(1.0, 1.25*(2**min(5,max(0,int(attempt)-1)))))
    return base + _r38_random.uniform(0.0,min(1.5,base*0.15))


def _r38_peer_gate():
    global _R38_PEER_LAST_HTTP
    with _R38_PEER_HTTP_LOCK:
        now=_r33_time.time(); block=max(0.0,float(globals().get('_R38_PEER_BLOCK_UNTIL',0.0) or 0.0)-now)
        gap=max(0.0,float(_r33_os.getenv('R38_PEER_MIN_GAP_SEC','0.18') or '0.18')-(now-float(_R38_PEER_LAST_HTTP or 0.0)))
        wait=max(block,gap)
        if wait>0: _r33_time.sleep(wait)
        _R38_PEER_LAST_HTTP=_r33_time.time()


def _r38_peer_attempt(row):
    global _R38_PEER_BLOCK_UNTIL
    endpoint=str(row.get('endpoint') or '')
    body=row.get('body') if isinstance(row.get('body'),dict) else {}
    kind=str(row.get('kind') or 'peer')
    base=globals().get('_split_peer_base',lambda:'')()
    headers_fn=globals().get('_split_headers')
    if not base or not globals().get('_split_secret',lambda:'')():
        raise RuntimeError('Render #2 URL/secret not configured')
    _r38_peer_gate()
    hdr=headers_fn('per-r38-front-'+kind) if callable(headers_fn) else {'X-Peer-Secret':str(_r33_os.getenv('PEER_SHARED_SECRET','') or '')}
    r=requests.post(base+endpoint,json=body,headers=hdr,timeout=max(5.0,min(35.0,float(_r33_os.getenv('R38_PEER_POST_TIMEOUT_SEC','18') or '18'))))
    transient,cloud,status=_r38_peer_transient_response(r)
    _R38_PEER_STATE['last_status']=status
    if cloud: _R38_PEER_STATE['cloudflare']=int(_R38_PEER_STATE.get('cloudflare') or 0)+1
    if status>=500: _R38_PEER_STATE['http_5xx']=int(_R38_PEER_STATE.get('http_5xx') or 0)+1
    payload={}
    try:
        if r.content and 'json' in str(r.headers.get('content-type','') or '').casefold():
            obj=r.json(); payload=obj if isinstance(obj,dict) else {}
    except Exception: payload={}
    if transient:
        wait=_r38_retry_after(r,int(row.get('attempts') or 0)+1)
        with _R38_PEER_HTTP_LOCK:
            _R38_PEER_BLOCK_UNTIL=max(float(_R38_PEER_BLOCK_UNTIL or 0.0),_r33_time.time()+min(wait,15.0))
        safe=('Cloudflare/HTML challenge' if cloud else f'HTTP {status}')
        return False,True,safe,wait,payload
    status_name=str(payload.get('status') or '')
    accepted=200<=status<300 and (payload.get('ok') is True or status_name in {'queued','running','ready','delivering','delivered','done','failed'})
    # R38 contracts: user jobs are accepted only after HEAVY confirms its own durable spool.
    if accepted and payload.get('durable') is True:
        returned=str(payload.get('job_id') or body.get('job_id') or '')
        if returned and returned != str(body.get('job_id') or ''):
            return False,False,'Render #2 returned a different job_id',0.0,payload
        return True,False,'',0.0,payload
    if accepted and kind not in {'file','google'}:
        return True,False,'',0.0,payload
    if accepted:
        return False,True,'Render #2 accepted without durable confirmation',2.0,payload
    # Any terminal record for the same durable job is still proof HEAVY owns the job.
    if payload.get('durable') is True and str(payload.get('job_id') or '')==str(body.get('job_id') or '') and status_name in {'failed','closed'}:
        return True,False,'',0.0,payload
    msg=str(payload.get('error') or '')[:400]
    if not msg:
        try:
            raw=str(r.text or '')
            msg='non-JSON response' if '<html' in raw.casefold() else raw[:400]
        except Exception: msg=f'HTTP {status}'
    return False,False,msg or f'HTTP {status}',0.0,payload


def _r38_outbox_enqueue_core(kind,endpoint,body):
    obj=dict(body or {}); jid=str(obj.get('job_id') or __import__('secrets').token_hex(12)).strip()[:80]; obj['job_id']=jid
    existing=_r38_outbox_get(jid)
    if existing and str(existing.get('state') or '') in {'accepted','completed'}:
        return jid
    row=existing if isinstance(existing,dict) else {}
    row.update({'job_id':jid,'kind':str(kind),'endpoint':str(endpoint),'body':_r33_safe_scalar(obj),'state':'pending','created_at':float(row.get('created_at') or _r33_time.time()),'attempts':int(row.get('attempts') or 0),'next_try':_r33_time.time(),'last_error':''})
    if not _r38_outbox_put(row,pending=True):
        raise RuntimeError('FAST durable peer outbox unavailable')
    _R38_OUTBOX_WAKE.set()
    return jid


# R47 FINALIZATION: obsolete pre-R41 outbox dispatcher removed.
def _r38_outbox_loop():
    while True:
        worked=False; now=_r33_time.time()
        for row in _r38_outbox_pending_rows(250):
            if float(row.get('next_try') or 0)>now: continue
            # Jobs are kept for six hours by default. This survives ordinary Render maintenance
            # without turning a genuinely broken configuration into an infinite hidden loop.
            max_age=max(900,min(86400,int(_r33_os.getenv('R38_PEER_JOB_MAX_AGE_SEC','21600') or '21600')))
            if now-float(row.get('created_at') or now)>max_age:
                row.update({'state':'failed','last_error':'Render #2 did not accept the durable job before max age','failed_at':now}); _r38_outbox_put(row,pending=False)
                if str(row.get('kind') or '')=='file': _r35_delivery_set(str(row.get('job_id') or ''),'done_error',{'job_id':row.get('job_id'),'ok':False,'error':row['last_error']},error=row['last_error'])
                continue
            _r38_outbox_dispatch_one(row); worked=True
        _R38_OUTBOX_WAKE.wait(0.25 if worked else 0.8); _R38_OUTBOX_WAKE.clear()


def _r38_worker_file_submit(body:dict):
    # No network on this call. The canonical file runner is already background work;
    # persisting to the outbox is enough to make HEAVY dispatch restart-safe.
    return _r38_outbox_enqueue('file','/internal/export/file',body)

_r7_worker_file_submit = _r38_worker_file_submit


def _r38_wait_remote_delivery(jid,body):
    timeout=max(300,min(21600,int(_r33_os.getenv('R38_FAST_JOB_WAIT_SEC','3600') or '3600')))
    deadline=_r33_time.time()+timeout; last_progress=0.0
    while _r33_time.time()<deadline:
        row=_r35_delivery_get(jid); state=str(row.get('state') or '')
        if state=='done': return True
        if state=='done_error':
            b=row.get('body') if isinstance(row.get('body'),dict) else {}
            raise RuntimeError(str(row.get('error') or b.get('error') or 'Render #2 completed with an error')[:900])
        out=_r38_outbox_get(jid); ostate=str(out.get('state') or '')
        if ostate=='failed': raise RuntimeError(str(out.get('last_error') or 'Render #2 rejected the job')[:900])
        now=_r33_time.time()
        if now-last_progress>15:
            try:
                if ostate in {'pending','retry'}: phase='Render #2 перезапускается — задание сохранено, повторяю'
                elif ostate=='accepted': phase='Render #2 выполняет задачу'
                elif state in {'running','failed'}: phase='получаю результат Render #2'
                else: phase='ожидаю Render #2'
                _file_job_progress(phase,force=True)
            except Exception: pass
            last_progress=now
        _r33_time.sleep(0.5)
    raise RuntimeError(f'Render #2 did not deliver the result within {timeout} sec; job_id={jid}')


def _r33_remote_file_adapter(kind,label,func_name,args,kwargs):
    body=_r33_export_body(str(kind),str(label),str(func_name),args,kwargs); body['front_release']='Пер-R43'
    try: _file_job_progress('сохраняю задание для Render #2',force=True)
    except Exception: pass
    jid=_r38_worker_file_submit(body)
    cur=_r35_delivery_get(jid)
    if str(cur.get('state') or '') not in {'running','done','done_error','accepted'}:
        _r35_delivery_set(jid,'dispatching',{'job_id':jid,'operation':body.get('operation'),'recipient_chat_id':body.get('recipient_chat_id')})
    try: bot_journal('r38_heavy_job_outboxed',int(body.get('recipient_chat_id') or 0),f"kind={kind}; op={body.get('operation')}; job={jid}; revision={body.get('required_revision') or 0}")
    except Exception: pass
    _r38_wait_remote_delivery(jid,body)
    delivery=str(body.get('delivery') or 'chat').lower(); delivered_kind='Telegram через Render #2' if delivery=='chat' else ('Google Sheets' if delivery=='google' else 'Google Drive')
    if not file_job_mark_external_delivery(delivered_kind,jid): raise RuntimeError('R38 delivery confirmed but FAST file-job context was lost')
    return True


def _r38_google_submit_report(title,rows,layout='category',annotations_override=None,include_annotations=True,**kwargs):
    if not _split_env_bool('SPLIT_GOOGLE_REMOTE_ENABLED',True): raise RuntimeError('Google Sheets worker delegation disabled')
    target_chat_id=kwargs.get('target_chat_id'); notify_result=bool(kwargs.get('notify_result',True)); recipient_chat_id=kwargs.get('recipient_chat_id') or target_chat_id
    tid,spreadsheet_id=_split_google_target(target_chat_id=target_chat_id,tenant_id=kwargs.get('tenant_id'))
    annotations=_split_annotations_for_google(rows,str(layout or 'category'),annotations_override,bool(include_annotations))
    encoded={f'{int(r)},{int(c)}':str(note) for (r,c),note in annotations.items() if str(note or '').strip()}
    jid=__import__('secrets').token_hex(12)
    body={'job_id':jid,'title':str(title or 'Статьи')[:300],'rows':rows,'layout':str(layout or 'category'),'annotations':encoded,'include_annotations':bool(include_annotations),'spreadsheet_id':spreadsheet_id,'tenant_id':tid,'target_chat_id':target_chat_id,'recipient_chat_id':recipient_chat_id,'notify_result':notify_result,'front_release':'Пер-R43'}
    _r38_outbox_enqueue('google','/internal/google/sheet',body)
    try:
        _SPLIT_STATE['google_last_attempt']=_r33_time.time(); _SPLIT_STATE['google_last_job']=jid; _SPLIT_STATE['google_last_error']=''
    except Exception: pass
    return 'worker-job:'+jid

_v262_split_google_sheets_create_category_report = _r38_google_submit_report
# R38 must also replace the canonical alias rebound by 89_callback_final/98_split_front.
# Without this, several legacy/scheduled Google paths still call the old synchronous HTTP function.
_google_sheets_create_category_report = _r38_google_submit_report


def _r38_sync_peer_json(method,path,*,json_body=None,timeout=12,max_wait=45,agent='per-r38-front-sync'):
    """Short synchronous control-plane call with the same transient policy as the outbox.

    This is only for user diagnostics/settings such as Google test/info; heavy data jobs
    never use it and always go through the durable outbox.
    """
    deadline=_r33_time.time()+max(5.0,min(120.0,float(max_wait or 45)))
    attempt=0; last='Render #2 unavailable'
    while _r33_time.time()<deadline:
        attempt+=1
        try:
            base=globals().get('_split_peer_base',lambda:'')(); headers_fn=globals().get('_split_headers')
            if not base or not globals().get('_split_secret',lambda:'')():
                raise RuntimeError('Render #2 URL/secret not configured')
            _r38_peer_gate()
            hdr=headers_fn(agent) if callable(headers_fn) else {'X-Peer-Secret':str(_r33_os.getenv('PEER_SHARED_SECRET','') or '')}
            kw={'headers':hdr,'timeout':max(3.0,min(25.0,float(timeout or 12)))}
            if json_body is not None: kw['json']=json_body
            r=requests.request(str(method or 'GET').upper(),base+str(path),**kw)
            transient,cloud,status=_r38_peer_transient_response(r)
            payload={}
            try:
                if r.content and 'json' in str(r.headers.get('content-type','') or '').casefold():
                    x=r.json(); payload=x if isinstance(x,dict) else {}
            except Exception: payload={}
            if not transient:
                return r,payload
            wait=_r38_retry_after(r,attempt); last=('Cloudflare/HTML challenge' if cloud else f'HTTP {status}')
            if _r33_time.time()+wait>=deadline: break
            _r33_time.sleep(min(10.0,wait))
        except Exception as exc:
            last=f'{type(exc).__name__}: {str(exc)[:260]}'
            wait=min(8.0,1.2*(2**min(4,attempt-1)))
            if _r33_time.time()+wait>=deadline: break
            _r33_time.sleep(wait)
    raise RuntimeError(f'Render #2 temporarily unavailable after retry: {last}')


def _r38_tenant_google_test(tenant_id):
    try:
        tid,spreadsheet_id=_split_google_target(tenant_id=str(tenant_id))
        r,payload=_r38_sync_peer_json('POST','/internal/google/test',json_body={'spreadsheet_id':spreadsheet_id,'tenant_id':tid},timeout=18,max_wait=60,agent='per-r38-front-google-test')
        if 200<=int(r.status_code)<300 and payload.get('ok'):
            return True,f"✅ Google Таблица доступна через Render #2.\nНазвание: {payload.get('title') or '—'}\nService account: {payload.get('service_email') or '—'}"
        return False,'❌ Проверка Google: '+str(payload.get('error') or f'HTTP {r.status_code}')[:600]
    except Exception as exc:
        return False,'❌ Проверка Google: '+str(exc)[:600]


def _r38_google_worker_info(fetch=True):
    # Preserve R7 cache semantics but do not let a short Render restart surface as HTML/503.
    cache=globals().get('_R7_GOOGLE_INFO_CACHE')
    now=_r33_time.time(); cached=dict((cache or {}).get('data') or {}) if isinstance(cache,dict) else {}
    if cached and (not fetch or now-float((cache or {}).get('ts') or 0)<600): return cached
    if not fetch:return cached
    try:
        r,payload=_r38_sync_peer_json('GET','/internal/google/info',timeout=8,max_wait=30,agent='per-r38-front-google-info')
        if 200<=int(r.status_code)<300 and payload.get('ok'):
            if isinstance(cache,dict): cache.update(ts=now,data=dict(payload))
            return dict(payload)
    except Exception: pass
    return cached

tenant_google_test = _r38_tenant_google_test
_r7_google_worker_info = _r38_google_worker_info


def _r38_google_result_handler():
    if not globals().get('_split_authorized_request',lambda:False)(): return ({'ok':False},404)
    body=request.get_json(silent=True) or {}; jid=str(body.get('job_id') or '').strip()
    if not jid:return ({'ok':False,'error':'job_id required'},400)
    out=_r38_outbox_get(jid)
    if str(out.get('result_state') or '')=='done': return ({'ok':True,'duplicate':True,'delivered':True},200)
    try: cid=int(body.get('recipient_chat_id') or 0)
    except Exception: cid=0
    if not cid:return ({'ok':False,'error':'recipient_chat_id required'},400)
    try:
        if bool(body.get('notify_result',True)):
            if bool(body.get('ok')):
                text=f"✅ 📊 Google Excel готов\n{str(body.get('title') or 'Google Excel')[:180]}\n\n{str(body.get('url') or '').strip()}"
                bot.send_message(cid,text,disable_web_page_preview=True)
            else:
                err=str(body.get('error') or 'Render #2 завершил Google-задачу с ошибкой')[:700]
                bot.send_message(cid,'❌ Google Excel не создан на Render #2:\n'+err)
        out=out if isinstance(out,dict) else {'job_id':jid,'kind':'google'}
        out.update({'job_id':jid,'state':'completed','result_state':'done','result_ok':bool(body.get('ok')),'result_url':str(body.get('url') or ''),'result_title':str(body.get('title') or ''),'result_at':_r33_time.time(),'last_error':str(body.get('error') or '')[:500]})
        _r38_outbox_put(out,pending=False)
        try:
            if body.get('ok'):_SPLIT_STATE['google_last_ok']=_r33_time.time(); _SPLIT_STATE['google_last_error']=''
            else:_SPLIT_STATE['google_last_error']=str(body.get('error') or '')[:240]
        except Exception: pass
        return ({'ok':True,'delivered':True},200)
    except Exception as exc:
        return ({'ok':False,'error':f'{type(exc).__name__}: {str(exc)[:300]}'},503)

try: app.view_functions['split_front_google_result_v262']=_r38_google_result_handler
except Exception: pass


def _r38_post_events(events,wire,large=False):
    """R32/R34 frozen-event sender using the same peer congestion gate as user jobs."""
    base=globals().get('_r32_peer_base_impl',lambda:'')(); secret=str(_r33_os.getenv('PEER_SHARED_SECRET','') or '').strip()
    if not base or not secret: raise RuntimeError('R38 peer URL/secret not configured')
    endpoint='/internal/state/event-large' if large else '/internal/state/events'
    _r38_peer_gate()
    r=requests.post(base+endpoint,data=wire,headers={'X-Peer-Secret':secret,'User-Agent':'per-r38-state-events','Content-Type':'application/json','Content-Encoding':'gzip'},timeout=max(2.0,min(30.0,float(_r33_os.getenv('R32_EVENT_POST_TIMEOUT_SEC','8') or '8'))))
    transient,cloud,status=_r38_peer_transient_response(r)
    if status==413 and not large:
        if len(events)>1:
            mid=max(1,len(events)//2); _r38_post_events(events[:mid],_r34_encode_events(events[:mid]),False); _r38_post_events(events[mid:],_r34_encode_events(events[mid:]),False); return True
        return _r38_post_events(events,wire,True)
    if transient:
        wait=_r38_retry_after(r,1)
        global _R38_PEER_BLOCK_UNTIL
        with _R38_PEER_HTTP_LOCK:_R38_PEER_BLOCK_UNTIL=max(float(_R38_PEER_BLOCK_UNTIL or 0.0),_r33_time.time()+min(wait,15.0))
        raise RuntimeError(('Cloudflare/HTML challenge' if cloud else f'HEAVY state events HTTP {status}'))
    if not (200<=status<300):
        payload={}
        try:payload=r.json() if r.content and 'json' in str(r.headers.get('content-type','') or '').casefold() else {}
        except Exception:payload={}
        raise RuntimeError('HEAVY state events '+str(payload.get('error') or f'HTTP {status}')[:300])
    payload={}
    try:
        x=r.json() if r.content else {}; payload=x if isinstance(x,dict) else {}
    except Exception:payload={}
    # With no Redis on HEAVY every durable state batch is a synchronous MEGA write.
    # Pace the next peer request so background state mirroring cannot starve user jobs.
    if str(payload.get('durable') or '')=='mega-direct':
        try:
            gap=max(0.2,min(5.0,float(_r33_os.getenv('R38_MEGA_EVENT_MIN_GAP_SEC','1.0') or '1.0')))
            with _R38_PEER_HTTP_LOCK:
                _R38_PEER_BLOCK_UNTIL=max(float(_R38_PEER_BLOCK_UNTIL or 0.0),_r33_time.time()+gap)
        except Exception:pass
    ack=int(payload.get('durable_revision') or payload.get('max_revision') or max([int(x.get('revision') or 0) for x in events] or [0]))
    applied_ack=int(payload.get('applied_revision') or (ack if bool(payload.get('apply_ok',True)) else 0))
    evstate=globals().get('_R32_EVENT_STATE')
    if isinstance(evstate,dict):
        evstate['last_revision_acked']=max(int(evstate.get('last_revision_acked') or 0),ack); evstate['last_revision_applied_peer']=max(int(evstate.get('last_revision_applied_peer') or 0),applied_ack)
        evstate['sent']=int(evstate.get('sent') or 0)+len(events); evstate['batches']=int(evstate.get('batches') or 0)+1; evstate['bytes']=int(evstate.get('bytes') or 0)+len(wire); evstate['last_ok']=_r33_time.time(); evstate['last_error']=''
    st=globals().get('_SPLIT_STATE')
    if isinstance(st,dict):
        st['r32_event_sent']=int(st.get('r32_event_sent') or 0)+len(events); st['r32_event_batches']=int(st.get('r32_event_batches') or 0)+1; st['r32_event_bytes']=int(st.get('r32_event_bytes') or 0)+len(wire); st['r32_event_pending']=globals().get('_R32_EVENT_Q').qsize() if globals().get('_R32_EVENT_Q') is not None else 0; st['r32_event_last_ok']=_r33_time.time(); st['r32_event_last_error']=''; st['r34_event_last_revision_acked']=ack; st['r35_event_last_revision_applied_peer']=applied_ack
    return True

_r34_post_events = _r38_post_events


def _r38_deliver_worker_export(body):
    """Fetch/deliver a ready HEAVY result without treating Render/Cloudflare turbulence as final."""
    jid=str(body.get('job_id') or ''); cid=int(body.get('recipient_chat_id') or 0)
    if not jid or not cid:return False
    try:
        if not body.get('ok'):
            bot.send_message(cid,'❌ Экспорт Render #2: '+str(body.get('error') or 'неизвестная ошибка')[:800]); return True
        delivery=str(body.get('delivery') or '')
        if delivery=='drive':
            bot.send_message(cid,f"☁️ Google Drive · {body.get('label') or ''}: {body.get('chat_name') or ''}\n\n{body.get('url') or ''}",disable_web_page_preview=True); return True
        if delivery=='google':
            if body.get('url'):bot.send_message(cid,f"✅ Google Excel готов.\n{body.get('url')}",disable_web_page_preview=True)
            return True
        deadline=_r33_time.time()+max(60,min(900,int(_r33_os.getenv('R38_RESULT_FETCH_WINDOW_SEC','420') or '420'))); attempt=0; response=None
        while _r33_time.time()<deadline:
            attempt+=1; _r35_delivery_set(jid,'running',body)
            try:
                base=globals().get('_split_peer_base',lambda:'')(); headers_fn=globals().get('_split_headers'); _r38_peer_gate()
                hdr=headers_fn('per-r38-front-export-fetch') if callable(headers_fn) else {'X-Peer-Secret':str(_r33_os.getenv('PEER_SHARED_SECRET','') or '')}
                r=requests.get(base+'/internal/export/file/'+jid,headers=hdr,timeout=60,stream=True)
                transient,cloud,status=_r38_peer_transient_response(r)
                if status==200:
                    response=r; break
                if status in {404,409,425} or transient:
                    wait=_r38_retry_after(r,attempt); _r33_time.sleep(min(15.0,wait)); continue
                raise RuntimeError(f'worker file HTTP {status}: '+str(getattr(r,'text','') or '')[:240])
            except Exception as exc:
                if _r33_time.time()+2>=deadline:raise
                _r33_time.sleep(min(15.0,max(1.0,1.3*(2**min(4,attempt-1)))))
        if response is None:raise RuntimeError('Render #2 result fetch retry window expired')
        import tempfile as _r38_tempfile, os as _r38_os
        suffix=_r38_os.path.splitext(str(body.get('filename') or 'export.bin'))[1]; tmp=_r38_tempfile.NamedTemporaryFile(prefix='r38_export_',suffix=suffix,delete=False)
        try:
            for chunk in response.iter_content(chunk_size=256*1024):
                if chunk:tmp.write(chunk)
            tmp.close()
            with open(tmp.name,'rb') as fobj:
                caption=str(body.get('caption') or '') or f"📂 {body.get('label') or 'Файл'}: {body.get('chat_name') or ''}"
                _tg_call_retry(bot.send_document,cid,fobj,caption=caption,timeout=120,purpose='r38_worker_export_send_document')
        finally:
            try:_r38_os.unlink(tmp.name)
            except Exception:pass
        return True
    except Exception as exc:
        try:log_error(f'R38 export delivery {jid}: {type(exc).__name__}: {str(exc)[:500]}')
        except Exception:pass
        return False

_r7_deliver_worker_export = _r38_deliver_worker_export


def _r38_export_delivery_task_core(body):
    jid=str(body.get('job_id') or ''); delivered=False
    try:delivered=bool(_r38_deliver_worker_export(dict(body)))
    except Exception as exc:_r35_delivery_set(jid,'failed',body,error=f'{type(exc).__name__}: {str(exc)[:700]}'); return
    if delivered:
        if bool(body.get('ok')):_r35_delivery_set(jid,'done',body)
        else:_r35_delivery_set(jid,'done_error',body,error=str(body.get('error') or 'HEAVY job failed'))
    else:_r35_delivery_set(jid,'failed',body,error='FAST delivery attempt failed')


def _r38_export_result_handler():
    if not globals().get('_split_authorized_request',lambda:False)():return ({'ok':False},404)
    body=request.get_json(silent=True) or {}; jid=str(body.get('job_id') or '')
    if not jid:return ({'ok':False,'error':'job_id required'},400)
    row=_r35_delivery_get(jid); state=str(row.get('state') or ''); age=max(0.0,_r33_time.time()-float(row.get('ts') or 0))
    if state in {'done','done_error'}:return ({'ok':True,'delivered':True,'duplicate':True,'operation_ok':state=='done'},200)
    if state=='running' and age<180:return ({'ok':True,'accepted':True,'delivered':False},202)
    _r35_delivery_set(jid,'running',body)
    _r38_threading.Thread(target=_r38_export_delivery_task,args=(dict(body),),daemon=True,name='per-r38-front-delivery').start()
    return ({'ok':True,'accepted':True,'delivered':False},202)

try:app.view_functions['split_front_export_result_r7']=_r38_export_result_handler
except Exception:pass


# ---------------- Пер-R43 semantic single-flight / duplicate collapse ----------------
# R38 made transport durable, but a backlog could still contain several different job_id
# values for the same user action.  After a HEAVY restart they were dispatched together.
# Full-state exports are memory-heavy, so this could create three simultaneous snapshots.
import hashlib as _r39_hashlib
import threading as _r39_threading

_R39_SIG_LOCK = _r39_threading.RLock()
_R39_SIG_ACTIVE = {}


def _r39_job_signature(kind, endpoint, body):
    b = body if isinstance(body, dict) else {}
    # Only semantic fields.  Exclude job_id/revision/snapshots/timestamps so repeated taps
    # for the same requested artifact collapse to one durable execution.
    keys = (
        'operation','recipient_chat_id','target_chat_id','scope','tenant_id','tenant_chat_ids',
        'mode','day_key','start_key','start_rid','end_key','end_rid','source_file_type','file_type',
        'delivery','limit','start_dt','end_dt','spreadsheet_id','drive_folder_id','title','layout'
    )
    core = {'kind': str(kind or ''), 'endpoint': str(endpoint or '')}
    for k in keys:
        if k in b:
            core[k] = _r33_safe_scalar(b.get(k))
    # Legacy/future operations can carry their arguments only in args/kwargs.
    if 'args' in b: core['args'] = _r33_safe_scalar(b.get('args'))
    if 'kwargs' in b: core['kwargs'] = _r33_safe_scalar(b.get('kwargs'))
    raw = _r33_json.dumps(core, ensure_ascii=False, sort_keys=True, separators=(',',':'), default=str)
    return _r39_hashlib.sha256(raw.encode('utf-8','replace')).hexdigest()


def _r39_delivery_terminal(jid):
    try:
        st = str((_r35_delivery_get(jid) or {}).get('state') or '')
        return st in {'done','done_error'}
    except Exception:
        return False


def _r38_outbox_enqueue(kind, endpoint, body):
    obj = dict(body or {})
    if str(kind or '') in {'file','google'}:
        backend = _r41_front_outbox_backend() if '_r41_front_outbox_backend' in globals() else ''
        obj['front_outbox_durable'] = bool(backend)
        obj['front_outbox_backend'] = backend or 'local'
        obj['front_release'] = 'Пер-R43'
    sig = _r39_job_signature(kind, endpoint, obj)
    now = _r33_time.time()
    # Fast in-process single-flight: repeated callback taps reuse the same job_id.
    with _R39_SIG_LOCK:
        row = _R39_SIG_ACTIVE.get(sig) or {}
        jid0 = str(row.get('job_id') or '')
        if jid0 and now - float(row.get('ts') or 0) < 900 and not _r39_delivery_terminal(jid0):
            out = _r38_outbox_get(jid0) or {}
            if str(out.get('state') or '') not in {'failed','superseded'}:
                return jid0
    # Cross-restart collapse: inspect durable pending rows from Redis/local outbox.
    candidates = []
    try:
        for r in _r38_outbox_pending_rows_core(500):
            if not isinstance(r, dict):
                continue
            rb=r.get('body') if isinstance(r.get('body'),dict) else {}
            # R42 release barrier: never reuse a canonical job_id from R39-R41.
            # Those rows may represent already-delivered work whose HEAVY MEGA witness
            # survived a container replacement. New R42 actions always get an R42 job.
            if str(rb.get('front_release') or '') != 'Пер-R43':
                continue
            if now - float(r.get('created_at') or now) > 900:
                continue
            if _r39_job_signature(r.get('kind'), r.get('endpoint'), rb) == sig:
                candidates.append(r)
    except Exception:
        candidates = []
    if candidates:
        # Deterministic canonical id: both FAST and HEAVY choose the lexicographically
        # smallest job_id.  Keep the newest payload/revision under that id.
        canonical = min(candidates, key=lambda x: str((x or {}).get('job_id') or '~'))
        newest = max(candidates + [{'body':obj,'created_at':now}], key=lambda x: (int(((x.get('body') or {}).get('required_revision') or 0)), float(x.get('created_at') or 0)))
        jid0 = str(canonical.get('job_id') or '')
        if jid0:
            try:
                merged=dict(canonical); merged['body']=dict(newest.get('body') or obj); merged['body']['job_id']=jid0; merged['state']='pending'; merged['next_try']=min(float(merged.get('next_try') or now),now); merged['last_error']=''
                _r38_outbox_put(merged,pending=True)
            except Exception: pass
            with _R39_SIG_LOCK:
                _R39_SIG_ACTIVE[sig] = {'job_id': jid0, 'ts': now}
            return jid0
    jid = _r38_outbox_enqueue_core(kind, endpoint, obj)
    with _R39_SIG_LOCK:
        _R39_SIG_ACTIVE[sig] = {'job_id': str(jid), 'ts': now}
    return jid


def _r38_outbox_pending_rows(limit=250):
    rows = list(_r38_outbox_pending_rows_core(max(int(limit or 0), 500)) or [])
    grouped = {}
    passthrough = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        rb=row.get('body') if isinstance(row.get('body'),dict) else {}
        if str(rb.get('front_release') or '') != 'Пер-R43':
            # One-time deploy barrier. Old pending peer jobs are superseded instead of
            # being replayed forever after every HEAVY restart.
            try:
                oldrow=dict(row); oldrow.update({'state':'superseded','superseded_by':'R42-release-barrier','updated_at':_r33_time.time(),'last_error':'R42 dropped stale pending job from '+str(rb.get('front_release') or 'legacy')})
                _r38_outbox_put(oldrow,pending=False)
            except Exception:
                pass
            continue
        try:
            sig = _r39_job_signature(row.get('kind'), row.get('endpoint'), rb)
        except Exception:
            passthrough.append(row); continue
        cur = grouped.get(sig)
        if cur is None:
            grouped[sig] = row; continue
        # Deterministic canonical id across deploys.  Merge the newest requested revision
        # into the smallest job_id so HEAVY recovery makes the same choice.
        keep, drop = (row, cur) if str(row.get('job_id') or '~') < str(cur.get('job_id') or '~') else (cur, row)
        newest = max((row,cur), key=lambda x:(int(((x.get('body') or {}).get('required_revision') or 0)),float(x.get('created_at') or 0)))
        keep=dict(keep); keep['body']=dict(newest.get('body') or keep.get('body') or {}); keep['body']['job_id']=str(keep.get('job_id') or '')
        grouped[sig]=keep
        try:
            _r38_outbox_put(keep,pending=True)
            drop = dict(drop); drop.update({'state':'superseded','superseded_by':str(keep.get('job_id') or ''),'updated_at':_r33_time.time()})
            _r38_outbox_put(drop, pending=False)
        except Exception:
            pass
    out = passthrough + list(grouped.values())
    out.sort(key=lambda x: float((x or {}).get('created_at') or 0))
    return out[:max(1, int(limit or 250))]


# Replace the functions used dynamically by the already-defined dispatcher loop.

# Clear the in-process semantic latch when the canonical delivery reaches a terminal state.
def _r38_export_delivery_task(body):
    jid = str((body or {}).get('job_id') or '')
    try:
        result = _r38_export_delivery_task_core(body)
        return result
    finally:
        if jid:
            try:
                if _r39_delivery_terminal(jid):
                    out=_r38_outbox_get(jid) or {'job_id':jid,'kind':'file'}
                    out.update({'state':'completed','result_state':'done','provisional':False,'completed_at':_r33_time.time(),'last_error':''})
                    _r38_outbox_put(out,pending=False)
            except Exception:
                pass
            with _R39_SIG_LOCK:
                for sig, row in list(_R39_SIG_ACTIVE.items()):
                    if str((row or {}).get('job_id') or '') == jid and _r39_delivery_terminal(jid):
                        _R39_SIG_ACTIVE.pop(sig, None)

try:
    bot_journal('r39_singleflight_loaded', int(OWNER_ID or 0), 'semantic heavy-job dedupe; stale outbox collapse; same job_id for repeated taps')
except Exception:
    pass

# R47 FINALIZATION: outbox thread starts only after all final owners are defined.


# ---------------------------------------------------------------------------
# Пер-R43: true asynchronous FAST<->HEAVY supervision.
# Heavy file jobs no longer occupy EXPORT_TASK_POOL while waiting minutes for HEAVY.
# FAST persists the peer job, returns the UI handler immediately, and a tiny supervisor
# thread follows canonical/duplicate jobs until the real Telegram/Google delivery ACK.
_R40_SUP_LOCK = _r38_threading.RLock()
_R40_SUPERVISORS = {}


def _r40_canonical_job_id(jid):
    cur=str(jid or '')[:80]; seen=set()
    for _ in range(8):
        if not cur or cur in seen: break
        seen.add(cur)
        row=_r35_delivery_get(cur) or {}
        body=row.get('body') if isinstance(row.get('body'),dict) else {}
        nxt=str(body.get('canonical_job_id') or body.get('duplicate_of') or row.get('canonical_job_id') or row.get('duplicate_of') or '')[:80]
        if not nxt:
            out=_r38_outbox_get(cur) or {}
            nxt=str(out.get('canonical_job_id') or out.get('duplicate_of') or '')[:80]
        if not nxt or nxt==cur: break
        cur=nxt
    return cur or str(jid or '')[:80]


def _r40_export_result_handler():
    if not globals().get('_split_authorized_request',lambda:False)(): return ({'ok':False},404)
    body=request.get_json(silent=True) or {}; jid=str(body.get('job_id') or '')[:80]
    if not jid: return ({'ok':False,'error':'job_id required'},400)
    canonical=str(body.get('canonical_job_id') or body.get('duplicate_of') or '')[:80]
    if canonical and canonical!=jid:
        _r35_delivery_set(jid,'alias',{'job_id':jid,'canonical_job_id':canonical,'duplicate_of':canonical,'operation':body.get('operation'),'recipient_chat_id':body.get('recipient_chat_id')})
        return ({'ok':True,'delivered':True,'alias':True,'canonical_job_id':canonical},200)
    return _r38_export_result_handler()

try: app.view_functions['split_front_export_result_r7']=_r40_export_result_handler
except Exception: pass


def _r40_status_edit(chat_id,msg_id,text,purpose='r40_file_status'):
    if not msg_id: return
    try:
        fn=globals().get('_tg_call_retry')
        if callable(fn): fn(bot.edit_message_text,text,chat_id=int(chat_id),message_id=int(msg_id),purpose=purpose)
        else: bot.edit_message_text(text,chat_id=int(chat_id),message_id=int(msg_id))
    except Exception: pass


def _r40_status_delete_later(chat_id,msg_id,delay):
    try:
        fn=globals().get('_v161_schedule_delete') or globals().get('_v160_schedule_delete')
        if callable(fn): fn(int(chat_id),int(msg_id),float(delay),'r40-heavy-close'); return
    except Exception: pass
    def _delete():
        try: bot.delete_message(int(chat_id),int(msg_id))
        except Exception: pass
    try: _r38_threading.Timer(float(delay),_delete).start()
    except Exception: pass


def _r40_status_text(label,elapsed,phase,final=None):
    if final=='ok': return f'✅ {label}\nОтправлено за {elapsed}.\nОкно закроется через 15с.'
    if final=='error': return f'⚠️ {label}\nЗавершено за {elapsed}.\n{phase[:600]}\nОкно закроется через 15с.'
    return f'⏳ Выполнение · {label}\n\nВремя: {elapsed}\n\nЭтап: {phase}\n\nПосле завершения закроется через 15с.'


def _r40_elapsed(started):
    sec=max(0,int(_r33_time.time()-float(started or _r33_time.time())))
    return f'{sec//60}:{sec%60:02d}'


def _r40_supervise_remote(jid,body,label,chat_id,msg_id):
    original=str(jid or '')[:80]; started=_r33_time.time(); last_ui=0.0; timeout=max(300,min(21600,int(_r33_os.getenv('R40_FAST_JOB_WAIT_SEC','3600') or '3600'))); deadline=started+timeout
    err=''; ok=False
    try:
        while _r33_time.time()<deadline:
            canonical=_r40_canonical_job_id(original)
            row=_r35_delivery_get(canonical) or {}; state=str(row.get('state') or '')
            if state=='done': ok=True; break
            if state=='done_error':
                b=row.get('body') if isinstance(row.get('body'),dict) else {}
                err=str(row.get('error') or b.get('error') or 'Render #2 завершил задачу с ошибкой')[:900]; break
            out=_r38_outbox_get(original) or {}; ostate=str(out.get('state') or '')
            if ostate=='failed': err=str(out.get('last_error') or 'Render #2 отклонил задание')[:900]; break
            now=_r33_time.time()
            if now-last_ui>=12.0:
                if canonical!=original: phase=f'Render #2 объединил дубль с заданием {canonical[:12]}…'
                elif ostate in {'pending','retry'}: phase='Render #2 недоступен — запрос сохранён, повторяю автоматически'
                elif ostate=='accepted' and state in {'running','accepted','dispatching',''}: phase='Render #2 выполняет задачу'
                elif state in {'running','failed'}: phase='получаю и отправляю готовый результат'
                else: phase='ожидаю подтверждение Render #2'
                _r40_status_edit(chat_id,msg_id,_r40_status_text(label,_r40_elapsed(started),phase),'r40_file_progress')
                last_ui=now
            _r33_time.sleep(0.5)
        else: err=f'Render #2 не подтвердил доставку за {timeout} сек.; job_id={original}'
    except Exception as exc:
        err=f'{type(exc).__name__}: {str(exc)[:800]}'
    elapsed=_r40_elapsed(started)
    if ok:
        _r40_status_edit(chat_id,msg_id,_r40_status_text(label,elapsed,'',final='ok'),'r40_file_done')
    else:
        _r40_status_edit(chat_id,msg_id,_r40_status_text(label,elapsed,err or 'нет подтверждения доставки',final='error'),'r40_file_error')
        try: log_error(f'R40 async HEAVY job {original}: {err}')
        except Exception: pass
    _r40_status_delete_later(chat_id,msg_id,15)
    with _R40_SUP_LOCK: _R40_SUPERVISORS.pop(original,None)


def _r40_submit_heavy_file(chat_id,kind,label,func,*args,**kwargs):
    chat_id=int(chat_id); kind_s=str(kind or 'file'); fname=str(getattr(func,'__name__','') or '')
    try:
        body=_r33_export_body(kind_s,str(label),fname,args,kwargs); body['front_release']='Пер-R43'
        jid=_r38_worker_file_submit(body); body['job_id']=str(jid)
    except Exception as exc:
        detail=f'{type(exc).__name__}: {str(exc)[:500]}'
        try: send_and_auto_delete(chat_id,'⚠️ Не удалось сохранить задание для Render #2: '+detail,15)
        except Exception: pass
        return (False,detail)
    with _R40_SUP_LOCK:
        existing=_R40_SUPERVISORS.get(str(jid))
        if isinstance(existing,dict) and existing.get('thread') is not None and existing['thread'].is_alive():
            return (True,'Уже выполняется')
    msg_id=0
    try:
        text=_r40_status_text(str(label),'0:00','задание надёжно сохранено, передаю Render #2')
        fn=globals().get('_tg_call_retry')
        m=fn(bot.send_message,chat_id,text,purpose='r40_file_status_create') if callable(fn) else bot.send_message(chat_id,text)
        msg_id=int(getattr(m,'message_id',0) or 0)
    except Exception: msg_id=0
    t=_r38_threading.Thread(target=_r40_supervise_remote,args=(str(jid),dict(body),str(label),chat_id,msg_id),daemon=True,name='per-r40-heavy-supervisor-'+str(jid)[:8])
    with _R40_SUP_LOCK: _R40_SUPERVISORS[str(jid)]={'thread':t,'chat_id':chat_id,'message_id':msg_id,'label':str(label),'created_at':_r33_time.time()}
    t.start()
    try: bot_journal('r40_heavy_async_outboxed',chat_id,f'kind={kind_s}; op={body.get("operation")}; job={jid}; revision={body.get("required_revision") or 0}')
    except Exception: pass
    return (True,'Запущено')


def submit_interactive_file_job(chat_id:int,kind:str,label:str,func,*args,**kwargs):
    kind_s=str(kind or 'file'); heavy=(kind_s in _R33_HEAVY_FILE_KINDS or kind_s.startswith('window_'))
    if heavy: return _r40_submit_heavy_file(chat_id,kind_s,label,func,*args,**kwargs)
    return _LOCAL_SUBMIT_FILE_JOB(chat_id,kind,label,func,*args,**kwargs) if callable(_LOCAL_SUBMIT_FILE_JOB) else (False,'Экспорт недоступен')

submit_interactive_file_job = submit_interactive_file_job

try:
    bot_journal('r40_unified_transport_loaded',int(OWNER_ID or 0),'async FAST supervisor; canonical alias follow; per-job status; no EXPORT_TASK_POOL wait; window revision fence')
except Exception: pass


# R40 query-only Google helper for scheduled/legacy paths. FAST sends only period
# boundaries and a revision fence; HEAVY reconstructs category rows from its mirror.
def _r40_google_query_submit(title,target_chat_id,start_key,end_key,start_rid=0,end_rid=0,layout='category',include_annotations=True,notify_result=False,recipient_chat_id=None):
    target_chat_id=int(target_chat_id); recipient_chat_id=int(recipient_chat_id or target_chat_id)
    tid,spreadsheet_id=_split_google_target(target_chat_id=target_chat_id,tenant_id=None)
    jid=__import__('secrets').token_hex(12)
    try: required=int((_R32_EVENT_STATE or {}).get('last_revision_queued') or 0)
    except Exception: required=0
    body={'job_id':jid,'operation':'google_exact_query','title':str(title or 'Статьи')[:300],'layout':str(layout or 'category'),'include_annotations':bool(include_annotations),'spreadsheet_id':spreadsheet_id,'tenant_id':tid,'target_chat_id':target_chat_id,'recipient_chat_id':recipient_chat_id,'notify_result':bool(notify_result),'start_key':str(start_key or '')[:10],'start_rid':int(start_rid or 0),'end_key':str(end_key or '')[:10],'end_rid':int(end_rid or 0),'required_revision':required,'front_release':'Пер-R43'}
    jid2=_r38_outbox_enqueue('google','/internal/google/sheet',body)
    return str(jid2)


def _r40_google_wait(jid,timeout=900):
    deadline=_r33_time.time()+max(30,min(3600,int(timeout or 900)))
    while _r33_time.time()<deadline:
        row=_r38_outbox_get(str(jid)) or {}
        if str(row.get('result_state') or '')=='done':
            return bool(row.get('result_ok')),str(row.get('result_url') or ''),str(row.get('last_error') or '')
        if str(row.get('state') or '')=='failed': return False,'',str(row.get('last_error') or 'Google job dispatch failed')
        _r33_time.sleep(0.5)
    return False,'',f'Google job timeout {int(timeout)} sec'

_r40_google_query_submit = _r40_google_query_submit
_r40_google_wait = _r40_google_wait


# ---------------------------------------------------------------------------
# Пер-R43: two-phase FAST-owned durable admission.
# When HEAVY has no Redis, synchronous MEGA admission can take much longer than
# the FAST HTTP timeout.  FAST already owns a Redis-backed durable outbox, so a
# live HEAVY may start the same idempotent job immediately while FAST keeps the
# request pending until the real result callback.  A HEAVY crash therefore never
# loses the request: the same job_id is sent again by FAST.

def _r41_front_outbox_backend():
    try:
        c = _r38_outbox_redis_client()
        if c is not None:
            # A lightweight ping prevents advertising front durability when the
            # client exists but the service is currently unreachable.
            try:
                if bool(c.ping()):
                    return 'redis'
            except Exception:
                return ''
    except Exception:
        pass
    return ''


# R47 FINALIZATION: durability metadata is merged into _r39_outbox_enqueue.
def _r38_outbox_dispatch_one(row):
    """Dispatch one peer job while treating HEAVY provisional admission as healthy.

    A provisional response means HEAVY accepted/queued the idempotent job using
    FAST's Redis outbox as the durable authority.  Keep the row pending so a HEAVY
    restart causes automatic replay, but never tell the user that Render #2 is down.
    """
    jid = str((row or {}).get('job_id') or '')
    if not jid:
        return
    try:
        ok, transient, detail, wait, payload = _r38_peer_attempt(row)
        provisional = bool(isinstance(payload, dict) and payload.get('provisional') and payload.get('ok') is True)
        if provisional and str(row.get('kind') or '') in {'file','google'}:
            attempts = int(row.get('attempts') or 0) + 1
            canonical=str(payload.get('canonical_job_id') or payload.get('duplicate_of') or '')[:80]
            row.update({
                'state':'retry', 'provisional':True, 'peer_accepted':True,
                'peer_status':str(payload.get('status') or 'queued'),
                'durable_backend':str(payload.get('durable_backend') or 'front-redis'),
                'attempts':attempts, 'last_error':'',
                'next_try':_r33_time.time()+max(8.0, min(30.0, float(_r33_os.getenv('R41_PROVISIONAL_REPLAY_SEC','15') or '15'))),
                'provisional_at':float(row.get('provisional_at') or _r33_time.time()),
            })
            if canonical and canonical!=jid: row['canonical_job_id']=canonical
            _r38_outbox_put(row, pending=True)
            _R38_PEER_STATE['accepted']=int(_R38_PEER_STATE.get('accepted') or 0)+1
            _R38_PEER_STATE['last_ok']=_r33_time.time(); _R38_PEER_STATE['last_error']=''
            if str(row.get('kind') or '')=='file':
                cur=_r35_delivery_get(jid) or {}
                if canonical and canonical!=jid:
                    _r35_delivery_set(jid,'alias',{'job_id':jid,'canonical_job_id':canonical,'duplicate_of':canonical,'operation':(row.get('body') or {}).get('operation'),'recipient_chat_id':(row.get('body') or {}).get('recipient_chat_id'),'provisional':True})
                elif str(cur.get('state') or '') not in {'running','done','done_error'}:
                    _r35_delivery_set(jid,'accepted',{'job_id':jid,'operation':(row.get('body') or {}).get('operation'),'recipient_chat_id':(row.get('body') or {}).get('recipient_chat_id'),'provisional':True})
            return
        if ok:
            canonical=str(payload.get('canonical_job_id') or payload.get('duplicate_of') or '')[:80]
            row.update({'state':'accepted','accepted_at':_r33_time.time(),'last_error':'','provisional':False,'peer_accepted':True,'peer_status':str(payload.get('status') or ''),'durable_backend':str(payload.get('durable_backend') or '')})
            if canonical and canonical!=jid: row['canonical_job_id']=canonical
            _r38_outbox_put(row,pending=False); _R38_PEER_STATE['accepted']=int(_R38_PEER_STATE.get('accepted') or 0)+1; _R38_PEER_STATE['last_ok']=_r33_time.time(); _R38_PEER_STATE['last_error']=''
            if str(row.get('kind') or '')=='file':
                cur=_r35_delivery_get(jid) or {}
                if canonical and canonical!=jid:
                    _r35_delivery_set(jid,'alias',{'job_id':jid,'canonical_job_id':canonical,'duplicate_of':canonical,'operation':(row.get('body') or {}).get('operation'),'recipient_chat_id':(row.get('body') or {}).get('recipient_chat_id')})
                elif str(cur.get('state') or '') not in {'running','done','done_error'}:
                    _r35_delivery_set(jid,'accepted',{'job_id':jid,'operation':(row.get('body') or {}).get('operation'),'recipient_chat_id':(row.get('body') or {}).get('recipient_chat_id')})
            return
        attempts=int(row.get('attempts') or 0)+1; row['attempts']=attempts; row['last_error']=str(detail or '')[:500]; row['provisional']=False
        _R38_PEER_STATE['last_error']=row['last_error']
        if transient:
            row['state']='retry'; row['next_try']=_r33_time.time()+max(0.8,float(wait or 1.0)); _R38_PEER_STATE['retries']=int(_R38_PEER_STATE.get('retries') or 0)+1; _r38_outbox_put(row,pending=True)
        else:
            row['state']='failed'; row['failed_at']=_r33_time.time(); _r38_outbox_put(row,pending=False)
            if str(row.get('kind') or '')=='file': _r35_delivery_set(jid,'done_error',{'job_id':jid,'ok':False,'error':'Render #2 rejected job: '+row['last_error']},error=row['last_error'])
    except Exception as exc:
        attempts=int(row.get('attempts') or 0)+1; delay=min(60.0,max(1.0,1.25*(2**min(5,attempts-1))))+_r38_random.uniform(0,1.0)
        row.update({'state':'retry','provisional':False,'attempts':attempts,'next_try':_r33_time.time()+delay,'last_error':f'{type(exc).__name__}: {str(exc)[:420]}'})
        _R38_PEER_STATE['last_error']=row['last_error']; _R38_PEER_STATE['retries']=int(_R38_PEER_STATE.get('retries') or 0)+1; _r38_outbox_put(row,pending=True)



# R47 FINALIZATION: delivery completion is handled by the sole _r38_export_delivery_task owner.


# R40's R39 latch wrapper was installed before this patch.  It resolves
# _r38_export_delivery_task dynamically, so the R41 completion hook is canonical.


def _r41_supervise_remote(jid,body,label,chat_id,msg_id):
    original=str(jid or '')[:80]; started=_r33_time.time(); last_ui=0.0; timeout=max(300,min(21600,int(_r33_os.getenv('R40_FAST_JOB_WAIT_SEC','3600') or '3600'))); deadline=started+timeout
    err=''; ok=False
    try:
        while _r33_time.time()<deadline:
            canonical=_r40_canonical_job_id(original)
            row=_r35_delivery_get(canonical) or {}; state=str(row.get('state') or '')
            if state=='done': ok=True; break
            if state=='done_error':
                b=row.get('body') if isinstance(row.get('body'),dict) else {}
                err=str(row.get('error') or b.get('error') or 'Render #2 завершил задачу с ошибкой')[:900]; break
            out=_r38_outbox_get(original) or {}; ostate=str(out.get('state') or '')
            if ostate=='failed': err=str(out.get('last_error') or 'Render #2 отклонил задание')[:900]; break
            now=_r33_time.time()
            if now-last_ui>=12.0:
                if canonical!=original: phase=f'Render #2 объединил дубль с заданием {canonical[:12]}…'
                elif bool(out.get('provisional')) and bool(out.get('peer_accepted')): phase='Render #2 принял задачу и выполняет её · резервная копия запроса сохранена на FAST'
                elif ostate in {'pending','retry'}: phase='восстанавливаю связь с Render #2 · запрос сохранён, повторяю автоматически'
                elif ostate in {'accepted','completed'} and state in {'running','accepted','dispatching',''}: phase='Render #2 выполняет задачу'
                elif state in {'running','failed'}: phase='получаю и отправляю готовый результат'
                else: phase='ожидаю подтверждение Render #2'
                _r40_status_edit(chat_id,msg_id,_r40_status_text(label,_r40_elapsed(started),phase),'r41_file_progress')
                last_ui=now
            _r33_time.sleep(0.5)
        else: err=f'Render #2 не подтвердил доставку за {timeout} сек.; job_id={original}'
    except Exception as exc:
        err=f'{type(exc).__name__}: {str(exc)[:800]}'
    elapsed=_r40_elapsed(started)
    if ok:
        _r40_status_edit(chat_id,msg_id,_r40_status_text(label,elapsed,'',final='ok'),'r41_file_done')
    else:
        _r40_status_edit(chat_id,msg_id,_r40_status_text(label,elapsed,err or 'нет подтверждения доставки',final='error'),'r41_file_error')
        try: log_error(f'R41 async HEAVY job {original}: {err}')
        except Exception: pass
    _r40_status_delete_later(chat_id,msg_id,15)
    with _R40_SUP_LOCK: _R40_SUPERVISORS.pop(original,None)


# R40 submitter resolves this global at call time.
_r40_supervise_remote = _r41_supervise_remote

try:
    bot_journal('r41_two_phase_peer_loaded',int(OWNER_ID or 0),'FAST Redis outbox remains pending during HEAVY provisional admission; no false unavailable state; file outbox completes on real delivery')
except Exception:
    pass

# v262


# R42 reliability barrier: previous-release peer jobs are not replayed; content pool has 4 workers.
try:
    bot_journal('r42_recovery_barrier_loaded', int(OWNER_ID or 0), 'drop stale R39-R41 peer outbox; 4 content workers; current jobs use Пер-R43')
except Exception:
    pass
# ---------------------------------------------------------------------------
# R44 DIAGNOSTIC INTEROP LAYER
# Purpose: observe the real FAST <-> HEAVY protocol without changing production
# job semantics.  Adds owner-only Test menu, shared-Redis handshake diagnostics,
# MEGA browser/download via HEAVY, reverse HEAVY->FAST ping, snapshot probe, and a
# compact local JSONL journal that mirrors important button/process/traffic events.
import json as _r44_json, os as _r44_os, time as _r44_time, threading as _r44_threading
import secrets as _r44_secrets, tempfile as _r44_tempfile, hashlib as _r44_hashlib
import html as _r44_html, re as _r44_re, shutil as _r44_shutil
from pathlib import Path as _R44Path
import requests as _r44_requests

_R44_DIAG_RELEASE='Пер-R44-DIAG'
_R44_DIAG_LOCK=_r44_threading.RLock()
_R44_DIAG_PATH=_R44Path(str(_r44_os.getenv('R44_DIAG_JOURNAL_PATH','/tmp/per_r44_diag_journal.jsonl') or '/tmp/per_r44_diag_journal.jsonl'))
_R44_DIAG_MAX=max(262144,min(20*1024*1024,int(_r44_os.getenv('R44_DIAG_JOURNAL_MAX_BYTES','5242880') or '5242880')))
_R44_TEST_MODE={}
_R44_MEGA_TOKENS={}
_R44_MEGA_TOKEN_LOCK=_r44_threading.RLock()
_R44_TEST_KEY_PREFIX='per:r44:test:'
_R44_TRAFFIC_WORDS=('TRAFFIC_AUDIT','DISPATCHER STUCK','STUCK_STACK','LOCKTRACE','INTERACTIVE FILE JOB','SPLIT FRONT','HEAVY','peer','Render #2','R4','BTNTRACE','FASTBTN','WEBHOOK')

def _r44_redact(value):
    s=str(value if value is not None else '')
    try:
        sec=str(_r44_os.getenv('PEER_SHARED_SECRET','') or '')
        if sec and len(sec)>=6: s=s.replace(sec,'<peer-secret>')
    except Exception: pass
    for key in ('BOT_TOKEN','TELEGRAM_BOT_TOKEN','REDIS_URL','MEGA_PASSWORD','MEGA_SESSION','GOOGLE_SERVICE_ACCOUNT_JSON'):
        try:
            v=str(_r44_os.getenv(key,'') or '')
            if v and len(v)>=8: s=s.replace(v,f'<{key.lower()}>')
        except Exception: pass
    return s[:2400]

def _r44_diag(event, **fields):
    try:
        row={'ts':round(_r44_time.time(),3),'event':str(event or '')[:120],'thread':_r44_threading.current_thread().name[:80]}
        for k,v in fields.items(): row[str(k)[:80]]=_r44_redact(v)
        raw=_r44_json.dumps(row,ensure_ascii=False,separators=(',',':'),default=str)+'\n'
        with _R44_DIAG_LOCK:
            _R44_DIAG_PATH.parent.mkdir(parents=True,exist_ok=True)
            try:
                if _R44_DIAG_PATH.exists() and _R44_DIAG_PATH.stat().st_size>_R44_DIAG_MAX:
                    old=_R44_DIAG_PATH.with_suffix(_R44_DIAG_PATH.suffix+'.1')
                    try: old.unlink(missing_ok=True)
                    except Exception: pass
                    try: _R44_DIAG_PATH.replace(old)
                    except Exception: pass
            except Exception: pass
            with open(_R44_DIAG_PATH,'a',encoding='utf-8') as fh: fh.write(raw)
    except Exception:
        pass

def _r44_diag_tail(limit=30):
    try:
        if not _R44_DIAG_PATH.exists(): return []
        with open(_R44_DIAG_PATH,'r',encoding='utf-8',errors='replace') as fh:
            rows=fh.readlines()[-max(1,min(100,int(limit or 30))):]
        out=[]
        for line in rows:
            try: out.append(_r44_json.loads(line))
            except Exception: continue
        return out
    except Exception: return []

# R47 FINALIZATION: no global logger wrappers. Diagnostics write only explicit R44/R45 events.
def _r44_peer_base():
    fn=globals().get('_r32_peer_base_impl') or globals().get('_split_peer_base')
    try:
        base=str(fn() if callable(fn) else '')
    except Exception: base=''
    if not base:
        base=str(_r44_os.getenv('PEER_SERVICE_URL','') or '').strip().rstrip('/')
        if base and not base.startswith(('http://','https://')): base='https://'+base
    return base.rstrip('/')

def _r44_headers(agent='per-r44-diag'):
    fn=globals().get('_split_headers')
    if callable(fn):
        try: return dict(fn(agent) or {})
        except Exception: pass
    return {'X-Peer-Secret':str(_r44_os.getenv('PEER_SHARED_SECRET','') or ''),'User-Agent':agent}

def _r44_front_redis():
    for name in ('_r38_outbox_redis_client','_r35_delivery_redis_client'):
        fn=globals().get(name)
        if callable(fn):
            try:
                c=fn()
                if c is not None and bool(c.ping()): return c
            except Exception: pass
    try:
        import redis as _r44_redis
        url=str(_r44_os.getenv('REDIS_URL','') or '').strip()
        if not url:return None
        c=_r44_redis.Redis.from_url(url,decode_responses=False,socket_connect_timeout=2,socket_timeout=3)
        if c.ping(): return c
    except Exception: pass
    return None

def _r44_mode(chat_id): return str(_R44_TEST_MODE.get(int(chat_id),'direct') or 'direct')
def _r44_set_mode(chat_id,mode): _R44_TEST_MODE[int(chat_id)]='redis' if str(mode)=='redis' else 'direct'; return _r44_mode(chat_id)

def _r44_request(chat_id, method, path, *, json_body=None, params=None, timeout=20, stream=False):
    cid=int(chat_id); mode=_r44_mode(cid); base=_r44_peer_base(); start=_r44_time.monotonic()
    if not base: return None,{'ok':False,'error':'PEER_SERVICE_URL не настроен','mode':mode,'elapsed':0}
    headers=_r44_headers('per-r44-diag-'+mode); nonce=''; rclient=None; rkey=''; redis_verified=None
    if mode=='redis':
        rclient=_r44_front_redis()
        if rclient is None:
            return None,{'ok':False,'error':'Redis на FAST недоступен','mode':mode,'elapsed':0,'redis_verified':False}
        nonce=_r44_secrets.token_hex(10); rkey=_R44_TEST_KEY_PREFIX+nonce
        try:
            rclient.setex(rkey,90,_r44_json.dumps({'side':'front','ts':_r44_time.time(),'chat':cid},separators=(',',':')))
            headers['X-R44-Redis-Test']=nonce
        except Exception as exc:
            return None,{'ok':False,'error':'FAST Redis write: '+str(exc)[:220],'mode':mode,'elapsed':0,'redis_verified':False}
    try:
        r=_r44_requests.request(str(method).upper(),base+str(path),headers=headers,json=json_body,params=params,timeout=timeout,stream=stream)
        elapsed=_r44_time.monotonic()-start
        if mode=='redis' and rclient is not None:
            try:
                raw=rclient.get(rkey)
                if isinstance(raw,bytes): raw=raw.decode('utf-8','replace')
                obj=_r44_json.loads(raw or '{}') if raw else {}
                redis_verified=(str(obj.get('side') or '')=='heavy' and bool(obj.get('front_seen')))
            except Exception: redis_verified=False
            try:rclient.delete(rkey)
            except Exception:pass
        meta={'ok':200<=int(r.status_code)<300,'status':int(r.status_code),'mode':mode,'elapsed':round(elapsed,3),'redis_verified':redis_verified,'content_type':str(r.headers.get('Content-Type') or '')[:120]}
        if not stream:
            try: meta['payload']=r.json() if r.content else {}
            except Exception: meta['payload']={'raw':(r.text or '')[:800]}
        _r44_diag('peer_http',method=method,path=path,status=r.status_code,elapsed=elapsed,mode=mode,redis_verified=redis_verified,bytes=r.headers.get('Content-Length',''))
        return r,meta
    except Exception as exc:
        elapsed=_r44_time.monotonic()-start
        try:
            if rclient is not None and rkey:rclient.delete(rkey)
        except Exception:pass
        _r44_diag('peer_http_error',method=method,path=path,elapsed=elapsed,mode=mode,error=f'{type(exc).__name__}: {exc}')
        return None,{'ok':False,'error':f'{type(exc).__name__}: {str(exc)[:500]}','mode':mode,'elapsed':round(elapsed,3),'redis_verified':False if mode=='redis' else None}

@app.route('/internal/r44/test/reverse',methods=['POST'])
def r44_front_reverse_probe():
    auth=globals().get('_split_authorized_request')
    if not callable(auth) or not bool(auth()): return ({'ok':False},404)
    body=request.get_json(silent=True) or {}; nonce=str(body.get('nonce') or '')[:120]
    _r44_diag('reverse_probe_received',nonce=nonce,remote=str(getattr(request,'remote_addr','') or ''))
    return ({'ok':True,'role':'front','release':_R44_DIAG_RELEASE,'nonce':nonce,'ts':_r44_time.time()},200)

def _r44_token(path,kind='dir'):
    raw=str(kind)+'\0'+str(path)
    tok=_r44_hashlib.sha1(raw.encode('utf-8','ignore')).hexdigest()[:14]
    with _R44_MEGA_TOKEN_LOCK:_R44_MEGA_TOKENS[tok]={'path':str(path),'kind':str(kind),'ts':_r44_time.time()}
    return tok

def _r44_token_get(tok):
    with _R44_MEGA_TOKEN_LOCK:return dict(_R44_MEGA_TOKENS.get(str(tok),{}) or {})

def _r44_test_menu_text(chat_id,remote=None):
    cid=int(chat_id); mode=_r44_mode(cid); rc=_r44_front_redis(); redis_front='✅' if rc is not None else '⛔'
    peer=_r44_peer_base() or '—'; host=_r44_re.sub(r'^https?://','',peer).split('/')[0]
    lines=['🧪 <b>ТЕСТ #1 FAST ↔ #2 HEAVY</b>','',f'Режим теста: <b>{"Redis handshake" if mode=="redis" else "прямой HTTP"}</b>',f'FAST Redis: {redis_front}',f'HEAVY URL: <code>{_r44_html.escape(host[:80])}</code>']
    if isinstance(remote,dict):
        lines+=['',f'HEAVY: {"✅ отвечает" if remote.get("ok") else "⛔ ошибка"}']
        if remote.get('status') is not None: lines.append(f'HTTP: {remote.get("status")} · {remote.get("elapsed",0)}с')
        if mode=='redis': lines.append(f'Общий Redis: {"✅ один и тот же" if remote.get("redis_verified") else "⛔ не подтверждён"}')
        p=remote.get('payload') if isinstance(remote.get('payload'),dict) else {}
        if p:
            lines.append(f'MEGA #2: {"✅" if p.get("mega_ok") else "🟠"} · <code>{_r44_html.escape(str(p.get("mega_root") or "—")[:90])}</code>')
            lines.append(f'Redis #2: {"✅" if p.get("redis_ok") else "⛔"} · configured={int(bool(p.get("redis_configured")))}')
            lines.append(f'Front виден #2: {"✅" if p.get("front_configured") else "⛔"}')
    lines+=['','Здесь тестируется реальная связь, MEGA и общий Redis. Производственный транспорт заданий этим переключателем не меняется.']
    return window_mark('\n'.join(lines),'Ф4044')

def _r44_test_menu_kb(chat_id):
    cid=int(chat_id); kb=types.InlineKeyboardMarkup(row_width=2); mode=_r44_mode(cid)
    kb.row(IB('🔗 #1 → #2 HTTP',callback_data='r44:test:echo'),IB('↩️ #2 → #1',callback_data='r44:test:reverse'))
    kb.row(IB('📁 MEGA #2',callback_data='r44:test:mega:root'),IB('🗃 Снимок БД',callback_data='r44:test:snapshot'))
    kb.row(IB(('🧠 Redis: ВКЛ' if mode=='redis' else '🧠 Redis: ВЫКЛ'),callback_data='r44:test:redis_toggle'),IB('🩺 Полный тест',callback_data='r44:test:full'))
    kb.row(IB('📜 Последние события',callback_data='r44:test:tail'),IB('📥 Скачать журнал',callback_data='r44:test:journal'))
    kb.row(IB('🔄 Статус #2',callback_data='r44:test:status'))
    day=str(get_chat_store(cid).get('current_view_day') or today_key())
    kb.row(IB('⬅️ Основное окно',callback_data=f'd:{day}:back_main'),IB('❌ Закрыть',callback_data='info_close'))
    return kb

def _r44_mega_screen(chat_id,path,page=0):
    r,meta=_r44_request(chat_id,'GET','/internal/r44/test/mega/list',params={'path':str(path)},timeout=45)
    p=meta.get('payload') if isinstance(meta.get('payload'),dict) else {}
    if not meta.get('ok') or not p.get('ok'):
        text=window_mark('📁 <b>MEGA #2</b>\n\n⛔ '+_r44_html.escape(str(p.get('error') or meta.get('error') or f'HTTP {meta.get("status")}')[:1200]),'Ф4045')
        kb=types.InlineKeyboardMarkup();kb.row(IB('🔙 В тест',callback_data='r44:test:open'));return text,kb
    entries=list(p.get('entries') or []); page=max(0,int(page or 0)); per=9; pages=max(1,(len(entries)+per-1)//per); page=min(page,pages-1)
    text=window_mark(f'📁 <b>MEGA #2</b>\n\nПуть: <code>{_r44_html.escape(str(p.get("path") or path)[:500])}</code>\nПапок/файлов: {len(entries)} · страница {page+1}/{pages}\nПолучено за {meta.get("elapsed",0)}с','Ф4045')
    kb=types.InlineKeyboardMarkup(row_width=1)
    for ent in entries[page*per:(page+1)*per]:
        ep=str(ent.get('path') or ''); kind=str(ent.get('type') or 'file'); name=str(ent.get('name') or ep.rsplit('/',1)[-1] or '/')
        tok=_r44_token(ep,kind); label=('📁 ' if kind=='dir' else '📄 ')+name[:46]
        kb.row(IB(label,callback_data=f'r44:test:mega:{"d" if kind=="dir" else "f"}:{tok}'))
    nav=[]
    ptok=_r44_token(str(p.get('path') or path),'dir')
    if page>0: nav.append(IB('◀️',callback_data=f'r44:test:mega:p:{ptok}:{page-1}'))
    if page+1<pages: nav.append(IB('▶️',callback_data=f'r44:test:mega:p:{ptok}:{page+1}'))
    if nav: kb.row(*nav)
    parent=str(p.get('parent') or '')
    if parent and parent!=str(p.get('path') or ''):
        kb.row(IB('⬆️ Вверх',callback_data=f'r44:test:mega:d:{_r44_token(parent,"dir")}'))
    kb.row(IB('🔄 Обновить',callback_data=f'r44:test:mega:d:{ptok}'),IB('🔙 В тест',callback_data='r44:test:open'))
    return text,kb

def _r44_send_mega_file(chat_id,path):
    cid=int(chat_id); r,meta=_r44_request(cid,'GET','/internal/r44/test/mega/file',params={'path':str(path)},timeout=120,stream=True)
    if r is None or not meta.get('ok'):
        return False,str(meta.get('error') or f'HTTP {meta.get("status")}')[:700]
    tmp=None
    try:
        name=str(path).rstrip('/').rsplit('/',1)[-1] or 'mega_file.bin'
        fd,tmp=_r44_tempfile.mkstemp(prefix='r44_mega_',suffix='_'+_r44_re.sub(r'[^A-Za-z0-9_.-]+','_',name)[-70:]);_r44_os.close(fd)
        size=0
        with open(tmp,'wb') as fh:
            for chunk in r.iter_content(1024*512):
                if not chunk: continue
                size+=len(chunk)
                if size>50*1024*1024: raise RuntimeError('Файл больше диагностического лимита 50 МБ')
                fh.write(chunk)
        with open(tmp,'rb') as fh: bot.send_document(cid,fh,caption=f'🧪 R44 · HEAVY передал из MEGA\n{name}')
        _r44_diag('mega_file_delivered',chat=cid,path=path,bytes=size,elapsed=meta.get('elapsed'))
        return True,f'{name} · {size} байт'
    except Exception as exc:
        _r44_diag('mega_file_error',chat=cid,path=path,error=exc);return False,f'{type(exc).__name__}: {str(exc)[:500]}'
    finally:
        try:
            if tmp:_r44_os.unlink(tmp)
        except Exception:pass

def _r44_render_tail():
    rows=_r44_diag_tail(28); lines=['📜 <b>R44 · последние события FAST</b>','']
    for row in rows[-24:]:
        ts=_r44_time.strftime('%H:%M:%S',_r44_time.localtime(float(row.get('ts') or 0)))
        ev=str(row.get('event') or '')[:40]; detail=str(row.get('name') or row.get('path') or row.get('message') or row.get('detail') or '')[:100]
        lines.append(f'<code>{ts}</code> · {_r44_html.escape(ev)} · {_r44_html.escape(detail)}')
    if len(lines)==2: lines.append('Пока пусто.')
    return window_mark('\n'.join(lines),'Ф4046')

def _r44_full_test(chat_id):
    cid=int(chat_id); results=[]
    for label,method,path,body,to in [
        ('#1→#2','POST','/internal/r44/test/echo',{'nonce':_r44_secrets.token_hex(6)},12),
        ('#2→#1','POST','/internal/r44/test/reverse',{'nonce':_r44_secrets.token_hex(6)},15),
        ('Статус','GET','/internal/r44/test/status',None,15),
    ]:
        r,m=_r44_request(cid,method,path,json_body=body,timeout=to); p=m.get('payload') if isinstance(m.get('payload'),dict) else {}
        results.append((label,bool(m.get('ok') and p.get('ok',True)),m,p))
    r,m=_r44_request(cid,'GET','/internal/r44/test/mega/list',params={'path':''},timeout=45);p=m.get('payload') if isinstance(m.get('payload'),dict) else {};results.append(('MEGA',bool(m.get('ok') and p.get('ok')),m,p))
    lines=['🩺 <b>ПОЛНЫЙ ТЕСТ #1 ↔ #2</b>','']
    for label,ok,m,p in results:
        extra=''
        if label=='MEGA' and ok: extra=f' · entries={len(p.get("entries") or [])}'
        if _r44_mode(cid)=='redis': extra+=f' · Redis={"OK" if m.get("redis_verified") else "NO"}'
        lines.append(f'{"✅" if ok else "⛔"} {label}: {m.get("elapsed",0)}с{extra}')
        if not ok: lines.append('   '+_r44_html.escape(str(p.get('error') or m.get('error') or f'HTTP {m.get("status")}')[:260]))
    return window_mark('\n'.join(lines),'Ф4047')

# Owner-only Test button in the actual main window.
_R44_MAIN_KB_CORE=globals().get('build_main_keyboard')
def _r44_build_main_keyboard(day_key,chat_id=None):
    kb=_R44_MAIN_KB_CORE(day_key,chat_id) if callable(_R44_MAIN_KB_CORE) else types.InlineKeyboardMarkup()
    try: cid=int(chat_id if chat_id is not None else current_state_chat_id() or 0)
    except Exception: cid=0
    if cid!=int(OWNER_ID or 0): return kb
    try:
        rows=globals().get('_v217_rows',lambda x:list(getattr(x,'keyboard',None) or []))(kb)
        cbfn=globals().get('_v217_btn_cb',lambda b:str(getattr(b,'callback_data','') or ''))
        if not any(cbfn(b)=='r44:test:open' for row in rows for b in (row or [])):
            rows.append([IB('🧪 Тест #1 ↔ #2',callback_data='r44:test:open')])
            setfn=globals().get('_v217_set_rows')
            if callable(setfn): kb=setfn(kb,rows)
            else: kb.row(IB('🧪 Тест #1 ↔ #2',callback_data='r44:test:open'))
    except Exception:
        try:kb.row(IB('🧪 Тест #1 ↔ #2',callback_data='r44:test:open'))
        except Exception:pass
    return kb
if callable(_R44_MAIN_KB_CORE): build_main_keyboard = _r44_build_main_keyboard

_R44_CONTOUR_GUARD_CORE=globals().get('contour_callback_guard')
# R47 FINALIZATION: R44 synchronous diagnostic guard removed; R45 is sole diagnostic callback owner.

# R47 FINALIZATION: no transport monkey-patching for diagnostics.
_r44_diag('r44_diag_loaded',release=_R44_DIAG_RELEASE,peer=_r44_peer_base(),redis_fast=bool(_r44_front_redis()))
try: bot_journal('r44_diag_loaded',int(OWNER_ID or 0),'owner test menu + FAST journal + HEAVY MEGA browser + direct/shared-Redis handshake diagnostics')
except Exception:pass



# ---------------------------------------------------------------------------
# R45 STABLE DIAGNOSTIC HOT-PATH FIX
# R44 diagnostic network calls were executed inside the same keyed callback actor
# as the visible Telegram window.  A 15-120 second HTTP/MEGA probe therefore held
# fast-window:<chat>:<message> and made every following button look "CLAIMED" with
# thread=None.  R45 makes diagnostics two-stage: the callback only enqueues work,
# while a completely separate network pool performs the slow probe and edits the
# test window later.  Production callbacks never share this pool.
import queue as _r45_queue, collections as _r45_collections

_R45_RELEASE='Пер-R45-STABLE'
_R45_DIAG_CALLBACK_POOL=KeyedTaskPool('r45-diag-callback',1,120)
_R45_DIAG_NET_POOL=KeyedTaskPool('r45-diag-net',1,60)
_R45_DIAG_SEQ_LOCK=_r44_threading.RLock()
_R45_DIAG_SEQ={}
_R45_DIAG_RING=_r45_collections.deque(maxlen=max(500,min(5000,int(_r44_os.getenv('R45_DIAG_RING_ROWS','1500') or '1500'))))
_R45_DIAG_Q=_r45_queue.Queue(maxsize=max(500,min(20000,int(_r44_os.getenv('R45_DIAG_QUEUE_ROWS','5000') or '5000'))))
_R45_DIAG_DROPPED=0

# Cache secret strings once.  R44 re-scanned the full environment for every traced
# line; that is unnecessary work on every button/traffic log.
_R45_REDACT_VALUES=[]
for _r45_key in ('PEER_SHARED_SECRET','BOT_TOKEN','TELEGRAM_BOT_TOKEN','REDIS_URL','MEGA_PASSWORD','MEGA_SESSION','GOOGLE_SERVICE_ACCOUNT_JSON'):
    try:
        _r45_val=str(_r44_os.getenv(_r45_key,'') or '')
        if _r45_val and len(_r45_val)>=6:_R45_REDACT_VALUES.append((_r45_val,'<'+_r45_key.lower()+'>'))
    except Exception:pass

def _r44_redact(value):
    s=str(value if value is not None else '')
    for old,repl in _R45_REDACT_VALUES:
        try:s=s.replace(old,repl)
        except Exception:pass
    return s[:2400]

def _r45_diag_rotate_and_append(lines):
    try:
        _R44_DIAG_PATH.parent.mkdir(parents=True,exist_ok=True)
        if _R44_DIAG_PATH.exists() and _R44_DIAG_PATH.stat().st_size>_R44_DIAG_MAX:
            old=_R44_DIAG_PATH.with_suffix(_R44_DIAG_PATH.suffix+'.1')
            try:old.unlink(missing_ok=True)
            except Exception:pass
            try:_R44_DIAG_PATH.replace(old)
            except Exception:pass
        with open(_R44_DIAG_PATH,'a',encoding='utf-8') as fh:
            fh.writelines(lines)
    except Exception:
        pass

def _r45_diag_writer_loop():
    batch=[]
    while True:
        try:
            try:line=_R45_DIAG_Q.get(timeout=.35)
            except _r45_queue.Empty:line=None
            if line:
                batch.append(line)
                _R45_DIAG_Q.task_done()
            while len(batch)<128:
                try:
                    line=_R45_DIAG_Q.get_nowait();batch.append(line);_R45_DIAG_Q.task_done()
                except _r45_queue.Empty:break
            if batch:
                _r45_diag_rotate_and_append(batch);batch=[]
        except Exception:
            batch=[];_r44_time.sleep(.25)

_r44_threading.Thread(target=_r45_diag_writer_loop,name='r45-diag-writer',daemon=True).start()

def _r44_diag(event, **fields):
    """Zero-blocking hot-path trace: RAM ring + nonblocking writer queue."""
    global _R45_DIAG_DROPPED
    try:
        row={'ts':round(_r44_time.time(),3),'event':str(event or '')[:120],'thread':_r44_threading.current_thread().name[:80]}
        for k,v in fields.items():row[str(k)[:80]]=_r44_redact(v)
        with _R45_DIAG_SEQ_LOCK:_R45_DIAG_RING.append(row)
        raw=_r44_json.dumps(row,ensure_ascii=False,separators=(',',':'),default=str)+'\n'
        try:_R45_DIAG_Q.put_nowait(raw)
        except _r45_queue.Full:_R45_DIAG_DROPPED+=1
    except Exception:pass

def _r44_diag_tail(limit=30):
    try:
        with _R45_DIAG_SEQ_LOCK:
            rows=list(_R45_DIAG_RING)[-max(1,min(100,int(limit or 30))):]
        if rows:return rows
    except Exception:pass
    try:
        if not _R44_DIAG_PATH.exists():return []
        with open(_R44_DIAG_PATH,'r',encoding='utf-8',errors='replace') as fh:raws=fh.readlines()[-max(1,min(100,int(limit or 30))):]
        out=[]
        for line in raws:
            try:out.append(_r44_json.loads(line))
            except Exception:pass
        return out
    except Exception:return []

def _r45_call_key(call):
    try:return (int(call.message.chat.id),int(call.message.message_id))
    except Exception:return (0,0)

def _r45_next_seq(call):
    key=_r45_call_key(call)
    with _R45_DIAG_SEQ_LOCK:
        seq=int(_R45_DIAG_SEQ.get(key,0))+1;_R45_DIAG_SEQ[key]=seq
    return key,seq

def _r45_is_current(key,seq):
    with _R45_DIAG_SEQ_LOCK:return int(_R45_DIAG_SEQ.get(key,0))==int(seq)

def _r45_safe_edit_if_current(call,key,seq,text,kb=None,parse_mode='HTML'):
    if not _r45_is_current(key,seq):return False
    try:
        safe_edit(bot,call,text,reply_markup=kb,parse_mode=parse_mode)
        return True
    except Exception as exc:
        _r44_diag('diag_edit_error',chat=key[0],message=key[1],error=f'{type(exc).__name__}: {exc}')
        return False

def _r45_pending_text(label):
    return window_mark('🧪 <b>ТЕСТ #1 ↔ #2</b>\n\n⏳ '+_r44_html.escape(str(label or 'Проверяю…'))+'\n\nОбычные кнопки бота в это время свободны.','Ф4053')

def _r45_diag_job(call,key,seq,raw):
    cid=key[0]
    _r44_diag('diag_job_start',chat=cid,action=raw,seq=seq,mode=_r44_mode(cid))
    started=_r44_time.monotonic()
    try:
        if raw=='r44:test:status':
            _,m=_r44_request(cid,'GET','/internal/r44/test/status',timeout=8)
            text=_r44_test_menu_text(cid,m);kb=_r44_test_menu_kb(cid)
        elif raw=='r44:test:echo':
            nonce=_r44_secrets.token_hex(8);_,m=_r44_request(cid,'POST','/internal/r44/test/echo',json_body={'nonce':nonce,'sent_at':_r44_time.time()},timeout=8);p=m.get('payload') if isinstance(m.get('payload'),dict) else {};ok=bool(m.get('ok') and p.get('nonce')==nonce)
            text=window_mark(f'🔗 <b>#1 FAST → #2 HEAVY</b>\n\n{"✅ Успех" if ok else "⛔ Ошибка"}\nHTTP: {m.get("status","—")} · {m.get("elapsed",0)}с\nNonce: <code>{nonce}</code>\nОтвет: <code>{_r44_html.escape(str(p.get("nonce") or "—"))}</code>\nRedis handshake: {m.get("redis_verified") if _r44_mode(cid)=="redis" else "не используется"}','Ф4048');kb=_r44_test_menu_kb(cid)
        elif raw=='r44:test:reverse':
            nonce=_r44_secrets.token_hex(8);_,m=_r44_request(cid,'POST','/internal/r44/test/reverse',json_body={'nonce':nonce},timeout=10);p=m.get('payload') if isinstance(m.get('payload'),dict) else {};rr=p.get('front_reply') if isinstance(p.get('front_reply'),dict) else {};ok=bool(m.get('ok') and p.get('ok') and rr.get('nonce')==nonce)
            text=window_mark(f'↩️ <b>#2 HEAVY → #1 FAST</b>\n\n{"✅ Успех" if ok else "⛔ Ошибка"}\nОбщее время: {m.get("elapsed",0)}с\nHEAVY увидел Front: {"✅" if p.get("front_http_ok") else "⛔"}\nNonce вернулся: {"✅" if rr.get("nonce")==nonce else "⛔"}\nRedis handshake: {m.get("redis_verified") if _r44_mode(cid)=="redis" else "не используется"}\n{_r44_html.escape(str(p.get("error") or m.get("error") or "")[:500])}','Ф4049');kb=_r44_test_menu_kb(cid)
        elif raw=='r44:test:snapshot':
            _,m=_r44_request(cid,'POST','/internal/r44/test/snapshot',json_body={'nonce':_r44_secrets.token_hex(6)},timeout=45);p=m.get('payload') if isinstance(m.get('payload'),dict) else {}
            text=window_mark(f'🗃 <b>Снимок данных #1 → #2</b>\n\n{"✅ HEAVY получил свежую SQLite" if m.get("ok") and p.get("ok") else "⛔ Ошибка"}\nВремя: {m.get("elapsed",0)}с\nBytes: {p.get("snapshot_bytes","—")}\nToken: <code>{_r44_html.escape(str(p.get("token") or "—")[:80])}</code>\n{_r44_html.escape(str(p.get("error") or m.get("error") or "")[:600])}','Ф4050');kb=_r44_test_menu_kb(cid)
        elif raw=='r44:test:mega:root':
            text,kb=_r44_mega_screen(cid,'',0)
        elif raw.startswith('r44:test:mega:d:'):
            tok=raw.split(':')[-1];rec=_r44_token_get(tok);text,kb=_r44_mega_screen(cid,rec.get('path') or '',0)
        elif raw.startswith('r44:test:mega:p:'):
            parts=raw.split(':');tok=parts[-2];page=int(parts[-1]);rec=_r44_token_get(tok);text,kb=_r44_mega_screen(cid,rec.get('path') or '',page)
        elif raw.startswith('r44:test:mega:f:'):
            tok=raw.split(':')[-1];rec=_r44_token_get(tok);path=rec.get('path') or ''
            ok,detail=_r44_send_mega_file(cid,path)
            text=window_mark(('✅ Передано: ' if ok else '⛔ Ошибка: ')+_r44_html.escape(detail),'Ф4051');kb=_r44_test_menu_kb(cid)
        elif raw=='r44:test:full':
            text=_r44_full_test(cid);kb=_r44_test_menu_kb(cid)
        elif raw=='r44:test:journal':
            _r44_diag('journal_download',chat=cid)
            # Give writer a short chance to flush queued lines without blocking callbacks.
            _r44_time.sleep(.15)
            if not _R44_DIAG_PATH.exists():
                _r44_diag('journal_created',chat=cid)
                try:_R44_DIAG_PATH.parent.mkdir(parents=True,exist_ok=True);_R44_DIAG_PATH.touch(exist_ok=True)
                except Exception:pass
            with open(_R44_DIAG_PATH,'rb') as fh:bot.send_document(cid,fh,caption='📜 R45 диагностический журнал FAST')
            text=_r44_test_menu_text(cid);kb=_r44_test_menu_kb(cid)
        else:
            text=window_mark('⛔ Неизвестный диагностический тест: '+_r44_html.escape(raw),'Ф4052');kb=_r44_test_menu_kb(cid)
        _r45_safe_edit_if_current(call,key,seq,text,kb,'HTML')
        _r44_diag('diag_job_done',chat=cid,action=raw,seq=seq,elapsed=round(_r44_time.monotonic()-started,3))
    except Exception as exc:
        _r44_diag('diag_job_error',chat=cid,action=raw,seq=seq,elapsed=round(_r44_time.monotonic()-started,3),error=f'{type(exc).__name__}: {exc}')
        _r45_safe_edit_if_current(call,key,seq,window_mark('⛔ <b>R45 TEST</b>\n\n'+_r44_html.escape(f'{type(exc).__name__}: {str(exc)[:1200]}'),'Ф4052'),_r44_test_menu_kb(cid),'HTML')

def _r45_enqueue_diag(call,raw,label='Проверяю связь…'):
    key,seq=_r45_next_seq(call);cid=key[0]
    try:safe_edit(bot,call,_r45_pending_text(label),reply_markup=_r44_test_menu_kb(cid),parse_mode='HTML')
    except Exception:pass
    queued=_R45_DIAG_NET_POOL.submit(f'{cid}:{seq}',_r45_diag_job,call,key,seq,raw)
    if not queued:
        _r45_safe_edit_if_current(call,key,seq,window_mark('⛔ Диагностическая очередь занята. Повтори через несколько секунд.','Ф4052'),_r44_test_menu_kb(cid),'HTML')
    return True

# Diagnostic callbacks are admitted on their own tiny lane.  Even a future bug in a
# diagnostic handler therefore cannot hold the production fast-window actor.
_R45_SELECTOR_CORE=globals().get('v163_webhook_select_lane')
def _r45_webhook_select_lane(payload,update_type,update_key):
    if str(update_type)=='callback_query':
        try:
            raw=str(((payload or {}).get('callback_query') or {}).get('data') or '')
            if raw.startswith('r44:test:') or raw.startswith('r45:test:'):
                return (_R45_DIAG_CALLBACK_POOL,f'diag-admit:{update_key}:{(payload or {}).get("update_id","")}')
        except Exception:pass
    if callable(_R45_SELECTOR_CORE):return _R45_SELECTOR_CORE(payload,update_type,update_key)
    return (UI_TASK_POOL if str(update_type)=='callback_query' else WEBHOOK_TASK_POOL,str(update_key))
v163_webhook_select_lane = _r45_webhook_select_lane

# Replace the synchronous R44 guard.  Only open/toggle/tail are local and immediate;
# every network/MEGA/file probe is detached before this callback worker returns.
_R45_CONTOUR_GUARD_CORE=_R44_CONTOUR_GUARD_CORE
def _r45_test_guard(call,resolved):
    raw=str(resolved or '')
    if not (raw.startswith('r44:test:') or raw.startswith('r45:test:')):
        return bool(_R45_CONTOUR_GUARD_CORE(call,raw)) if callable(_R45_CONTOUR_GUARD_CORE) else False
    try:cid=int(call.message.chat.id);uid=int(getattr(getattr(call,'from_user',None),'id',0) or 0)
    except Exception:return True
    if cid!=int(OWNER_ID or 0) or uid!=int(OWNER_ID or 0):
        try:bot.answer_callback_query(call.id,'Только владелец.',show_alert=True)
        except Exception:pass
        return True
    _r44_diag('test_button',chat=cid,action=raw,mode=_r44_mode(cid))
    try:
        if raw in {'r44:test:open','r45:test:open'}:
            safe_edit(bot,call,_r44_test_menu_text(cid),reply_markup=_r44_test_menu_kb(cid),parse_mode='HTML');return True
        if raw in {'r44:test:redis_toggle','r45:test:redis_toggle'}:
            _r44_set_mode(cid,'direct' if _r44_mode(cid)=='redis' else 'redis');safe_edit(bot,call,_r44_test_menu_text(cid),reply_markup=_r44_test_menu_kb(cid),parse_mode='HTML');return True
        if raw in {'r44:test:tail','r45:test:tail'}:
            safe_edit(bot,call,_r44_render_tail(),reply_markup=_r44_test_menu_kb(cid),parse_mode='HTML');return True
        labels={
            'r44:test:status':'Проверяю состояние Render #2…','r44:test:echo':'Проверяю #1 → #2…','r44:test:reverse':'Проверяю #2 → #1…',
            'r44:test:snapshot':'Проверяю передачу SQLite…','r44:test:mega:root':'Читаю папки MEGA через Render #2…','r44:test:full':'Запускаю полный тест…',
            'r44:test:journal':'Готовлю журнал…'
        }
        if raw.startswith('r44:test:mega:d:') or raw.startswith('r44:test:mega:p:'):label='Открываю папку MEGA через Render #2…'
        elif raw.startswith('r44:test:mega:f:'):label='Render #2 передаёт файл из MEGA…'
        else:label=labels.get(raw,'Проверяю…')
        return _r45_enqueue_diag(call,raw,label)
    except Exception as exc:
        _r44_diag('test_handler_error',chat=cid,action=raw,error=f'{type(exc).__name__}: {exc}')
        try:safe_edit(bot,call,window_mark('⛔ <b>R45 TEST</b>\n\n'+_r44_html.escape(f'{type(exc).__name__}: {str(exc)[:1200]}'),'Ф4052'),reply_markup=_r44_test_menu_kb(cid),parse_mode='HTML')
        except Exception:pass
        return True
contour_callback_guard = _r45_test_guard

# Make stuck logs actionable and less noisy.  The original watchdog reads this global
# on every pass, so changing it here affects the already-running watchdog thread.
try:WEBHOOK_STUCK_WARN_SECONDS=max(12.0,float(_r44_os.getenv('WEBHOOK_STUCK_WARN_SECONDS','12') or '12'))
except Exception:WEBHOOK_STUCK_WARN_SECONDS=12.0

_R45_LOCK_SNAPSHOT_CORE=globals().get('r36_lock_snapshot_text')
def _r45_lock_snapshot_text():
    parts=[]
    try:
        if callable(_R45_LOCK_SNAPSHOT_CORE):
            old=str(_R45_LOCK_SNAPSHOT_CORE() or '')
            if old and old!='none':parts.append(old)
    except Exception:pass
    for nm in ('WEBHOOK_TASK_POOL','V166_WINDOW_UI_TASK_POOL','V166_FINANCE_UI_TASK_POOL','FAST_UI_TASK_POOL','_R45_DIAG_CALLBACK_POOL','_R45_DIAG_NET_POOL'):
        try:
            pool=globals().get(nm)
            st=pool.stats() if pool is not None and hasattr(pool,'stats') else None
            if st and (int(st.get('active') or 0)>0 or int(st.get('pending') or 0)>0):parts.append(f"{st.get('name')} a={st.get('active')} p={st.get('pending')} keys={st.get('keys')} maxwait={st.get('max_wait')}")
        except Exception:pass
    return '; '.join(parts) or 'none'
r36_lock_snapshot_text = _r45_lock_snapshot_text

_r44_diag('r45_stable_loaded',release=_R45_RELEASE,diag_async=True,diag_workers=2,log_async=True)
try:bot_journal('r45_stable_loaded',int(OWNER_ID or 0),'diagnostic HTTP/MEGA detached from callback actors; async diagnostic journal; independent diagnostic admission lane')
except Exception:pass


# R45 snapshot conditional GET: HEAVY can cheaply ask whether its local SQLite mirror
# already matches FAST.  When the state token is unchanged, FAST returns 304 before
# creating/gzipping another full SQLite backup.
_R45_STATE_DOWNLOAD_CORE=(globals().get('app').view_functions.get('split_front_state_download_v262') if globals().get('app') is not None else None)
def _r45_split_state_download_conditional():
    try:
        auth=globals().get('_split_authorized_request')
        if callable(auth) and not auth():return ({'ok':False},404)
        flush=globals().get('_r27_flush_state_revision')
        if callable(flush):flush()
        tokfn=globals().get('_split_current_state_token_v264')
        token=str(tokfn() if callable(tokfn) else '')
        prior=str(request.headers.get('X-R45-If-State-Token','') or '')
        if prior and token and prior==token:
            resp=app.response_class(b'',status=304,mimetype='application/octet-stream')
            resp.headers['X-Split-State-Token']=token
            resp.headers['X-R45-State-Reused']='1'
            _r44_diag('snapshot_304',token=token[:80])
            return resp
    except Exception as exc:
        _r44_diag('snapshot_304_check_error',error=f'{type(exc).__name__}: {exc}')
    if callable(_R45_STATE_DOWNLOAD_CORE):return _R45_STATE_DOWNLOAD_CORE()
    return ({'ok':False,'error':'state endpoint unavailable'},503)
try:
    if callable(_R45_STATE_DOWNLOAD_CORE):app.view_functions['split_front_state_download_v262']=_r45_split_state_download_conditional
except Exception:pass




# ---------------------------------------------------------------------------
# R47 FINALIZATION: sole extension callback dispatcher.
# No PREV/ORIG callback chain: each feature handler is standalone and returns False
# when the callback does not belong to it.
def v149_extension_callback(call, data_str: str) -> bool:
    raw = str(data_str or '')
    try:
        if _google_extension_callback(call, raw):
            return True
        if _constructor_extension_callback(call, raw):
            return True
        if _reminder_extension_callback(call, raw):
            return True
        if _v153_extension_callback(call, raw):
            return True
        if _v152_handle_rights_callback(call, raw):
            return True
        if raw.startswith('v149:'):
            return bool(_v177_legacy_0266_v149_extension_callback(call, raw))
    except Exception as exc:
        try: log_error(f'final extension callback {raw[:180]}: {type(exc).__name__}: {exc}')
        except Exception: pass
        return True
    return False

try:
    if not globals().get('_R38_OUTBOX_THREAD_STARTED'):
        globals()['_R38_OUTBOX_THREAD_STARTED']=True
        _r38_threading.Thread(target=_r38_outbox_loop,name='per-r38-peer-outbox',daemon=True).start()
    bot_journal('r38_peer_transport_loaded',int(OWNER_ID or 0),'durable FAST outbox; final R47 dispatcher; same job_id; Google+file unified dispatch')
except Exception:
    pass

# v262
