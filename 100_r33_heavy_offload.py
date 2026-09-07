# v262
"""Пер-R35: all user-requested heavy file/table/journal jobs are delegated to HEAVY.

This module is intentionally loaded last.  It does not touch the R28 direct-render
function.  The Telegram callback only creates the existing small status message and
queues a descriptor; state flush, serialization and HTTP happen on the background
heavy-dispatch pool.
"""
import datetime as _r33_datetime
import json as _r33_json
import os as _r33_os
import time as _r33_time

_R33_PREV_SUBMIT_FILE_JOB = globals().get('submit_interactive_file_job')
_R33_HEAVY_FILE_KINDS = {
    'period_export','exact_export','xlsx','csv','tabl_lsx','json','json_full','sqlite',
    'runtime','journal','journal_current','bot_source','window_markers','window_tz',
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
        'delivery':'chat','front_release':'Пер-R35',
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
                'release':'Пер-R35',
                'captured_at':_r33_time.time(),
                'runtime':dict(globals().get('_RUNTIME_STATE') or {}),
                'split':dict(globals().get('_SPLIT_STATE') or {}),
                'state_events':dict(globals().get('_R32_EVENT_STATE') or {}),
            })
        except Exception: pass
    # R34 ordering fence: state-dependent jobs carry the newest queued revision.
    # FAST never waits for it; HEAVY waits/replays in its own queue.
    if str(body.get('operation') or '') in {'period_export_query','exact_export_query','tabl_lsx','chat_json','full_state','sqlite'}:
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
    if not callable(submit): raise RuntimeError('R35 HEAVY export bridge unavailable')
    jid=submit(body)
    try: bot_journal('r35_heavy_file_accepted_legacy_guard',int(body.get('recipient_chat_id') or 0),f"kind={kind}; op={body.get('operation')}; job={jid}; required_revision={body.get('required_revision') or 0}")
    except Exception: pass
    # R35 intentionally does NOT mark accepted/queued as delivered here. The final
    # adapter defined below waits for the real FAST delivery callback.
    return True

def submit_interactive_file_job(chat_id:int,kind:str,label:str,func,*args,**kwargs):
    kind_s=str(kind or 'file')
    heavy=(kind_s in _R33_HEAVY_FILE_KINDS or kind_s.startswith('window_'))
    if not heavy or not callable(_R33_PREV_SUBMIT_FILE_JOB):
        return _R33_PREV_SUBMIT_FILE_JOB(chat_id,kind,label,func,*args,**kwargs) if callable(_R33_PREV_SUBMIT_FILE_JOB) else (False,'Экспорт недоступен')
    fname=str(getattr(func,'__name__','') or '')
    return _R33_PREV_SUBMIT_FILE_JOB(int(chat_id),kind_s,label,_r33_remote_file_adapter,kind_s,label,fname,args,kwargs)

# Replace the final global symbol used by all existing handlers without touching them.
globals()['submit_interactive_file_job']=submit_interactive_file_job


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

globals()['send_export_for_chat_to']=send_export_for_chat_to
globals()['send_exact_range_export']=send_exact_range_export
globals()['send_tabl_lsx_for_chat']=send_tabl_lsx_for_chat

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
# Пер-R35: end-to-end HEAVY delivery control.
# 202/queued is only an acceptance ACK. The FAST file job remains open until
# Render #2's callback has actually delivered the result to Telegram/Google.
_R35_REMOTE_RESULT_LOCK = __import__('threading').RLock()
_R35_REMOTE_RESULT = {}

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
    jid=str(body.get('job_id') or '')
    last=''
    attempts=max(2,min(5,int(__import__('os').getenv('R35_FILE_SUBMIT_ATTEMPTS','3') or '3')))
    for attempt in range(1,attempts+1):
        try:
            hdr=headers_fn('per-r35-front-export') if callable(headers_fn) else {'X-Peer-Secret':str(__import__('os').getenv('PEER_SHARED_SECRET','') or '')}
            r=requests.post(base+'/internal/export/file',json=body,headers=hdr,timeout=max(5.0,min(30.0,float(__import__('os').getenv('R35_FILE_SUBMIT_TIMEOUT_SEC','12') or '12'))))
            payload=r.json() if r.content else {}
            status=str(payload.get('status') or '')
            if 200<=r.status_code<300 and (payload.get('ok') is True or status in {'queued','running','ready','delivering','delivered','done'}):
                return str(payload.get('job_id') or jid)
            last=str(payload.get('error') or r.text[:500] or f'HTTP {r.status_code}')
            if 400<=r.status_code<500 and r.status_code not in {408,409,425,429}: break
        except Exception as exc:
            last=f'{type(exc).__name__}: {str(exc)[:400]}'
        if attempt<attempts: _r33_time.sleep(0.35*attempt)
    raise RuntimeError(last or 'Render #2 не подтвердил приём задания')

globals()['_r7_worker_file_submit']=_r35_worker_file_submit

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
            submitted=bool(pool.submit('r35-export-delivery:'+jid,_r35_export_delivery_task,dict(body)))
        if not submitted:
            __import__('threading').Thread(target=_r35_export_delivery_task,args=(dict(body),),daemon=True,name='per-r35-front-delivery').start()
    except Exception:
        __import__('threading').Thread(target=_r35_export_delivery_task,args=(dict(body),),daemon=True,name='per-r35-front-delivery').start()
    return ({'ok':True,'accepted':True,'delivered':False},202)

try:
    # Keep the existing Flask route, replace only its implementation.
    app.view_functions['split_front_export_result_r7']=split_front_export_result_r35
except Exception:
    pass

def _r35_wait_remote_delivery(jid,body):
    timeout=max(60,min(7200,int(__import__('os').getenv('R35_FAST_JOB_WAIT_SEC','1800') or '1800')))
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
    body['front_release']='Пер-R35'
    try: _file_job_progress('передаю задание Render #2',force=True)
    except Exception: pass
    submit=globals().get('_r7_worker_file_submit')
    if not callable(submit): raise RuntimeError('R35 HEAVY export bridge unavailable')
    jid=submit(body)
    existing=_r35_delivery_get(jid)
    if str(existing.get('state') or '') not in {'running','done','done_error'}:
        _r35_delivery_set(jid,'accepted',{'job_id':jid,'operation':body.get('operation'),'recipient_chat_id':body.get('recipient_chat_id')})
    try: bot_journal('r35_heavy_file_accepted',int(body.get('recipient_chat_id') or 0),f"kind={kind}; op={body.get('operation')}; job={jid}; required_revision={body.get('required_revision') or 0}")
    except Exception: pass
    _r35_wait_remote_delivery(jid,body)
    # This call runs inside the original FAST file-job context, so only now may the
    # canonical runner close the status window and release its single-flight lock.
    delivery=str(body.get('delivery') or 'chat').lower()
    delivered_kind='Telegram через Render #2' if delivery=='chat' else ('Google Sheets' if delivery=='google' else 'Google Drive')
    if not file_job_mark_external_delivery(delivered_kind,jid):
        raise RuntimeError('R35 delivery was confirmed but FAST file-job context was lost')
    return True

try:
    bot_journal('r35_transport_fix_loaded',int(OWNER_ID or 0),'accepted!=delivered; redis delivery ledger; idempotent submit retry; stale callback recovery')
except Exception:
    pass

# v262
