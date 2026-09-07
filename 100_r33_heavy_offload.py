# v262
"""Пер-R33: all user-requested heavy file/table/journal jobs are delegated to HEAVY.

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
        'delivery':'chat','front_release':'Пер-R33',
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
    # filename/caption are generated on HEAVY from the authoritative state.
    return body


def _r33_remote_file_adapter(kind,label,func_name,args,kwargs):
    # This runs only on R21_HEAVY_DISPATCH_TASK_POOL, never in the callback thread.
    try:
        _file_job_progress('синхронизирую изменения с Render #2', force=True)
    except Exception:
        pass
    flush=globals().get('r32_flush_state_events')
    if callable(flush):
        # Wait in background so an export requested immediately after a finance entry
        # sees that entry on HEAVY.  This cannot delay the visible button response.
        if not flush(timeout=float(_r33_os.getenv('R33_EXPORT_STATE_BARRIER_SEC','25') or '25')):
            raise RuntimeError('Render #2 ещё не подтвердил актуальное состояние; повторите файл через несколько секунд')
    body=_r33_export_body(str(kind),str(label),str(func_name),args,kwargs)
    try:
        _file_job_progress('передаю задание Render #2', force=True)
    except Exception:
        pass
    submit=globals().get('_r7_worker_file_submit')
    if not callable(submit):
        raise RuntimeError('R33 HEAVY export bridge unavailable')
    jid=submit(body)
    try: file_job_mark_external_delivery('Render #2 HEAVY',jid)
    except Exception: pass
    try:
        bot_journal('r33_heavy_file_delegated',int(body.get('recipient_chat_id') or 0),f"kind={kind}; op={body.get('operation')}; job={jid}")
    except Exception: pass
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

# Defensive R28 hot-path regression gate stays active. R33 itself contains no render queue.
try:
    _src=__import__('inspect').getsource(globals().get('fast_ui_edit_message_text'))
    if 'WINDOW_RENDER_TASK_POOL' in _src or '_perform_fast_ui_edit' not in _src:
        raise RuntimeError('R33 HOTPATH GUARD: R28 direct render contract changed')
except OSError:
    pass

try:
    bot_journal('r33_heavy_offload_loaded',int(OWNER_ID or 0),'files/tables/journals/json/full-state/sqlite/runtime/window-docs -> HEAVY')
except Exception:
    pass
# v262
