#!/usr/bin/env python3
from __future__ import annotations
import ast, hashlib, json, py_compile, re, sys
from pathlib import Path

ROOT=Path(__file__).resolve().parent
ROLE='fast' if (ROOT/'bot.py').exists() else 'heavy' if (ROOT/'worker_service.py').exists() else 'unknown'
errors=[]; warnings=[]; checks=[]

def ok(name, cond, detail=''):
    checks.append((name,bool(cond),detail))
    if not cond: errors.append(f'{name}: {detail or "failed"}')

def text(name): return (ROOT/name).read_text(encoding='utf-8',errors='replace')
def count(pattern,s,flags=0): return len(re.findall(pattern,s,flags))

def compile_all():
    bad=[]
    for p in ROOT.rglob('*.py'):
        if '__pycache__' in p.parts: continue
        try: py_compile.compile(str(p),doraise=True)
        except Exception as exc: bad.append(f'{p.relative_to(ROOT)}: {exc}')
    ok('python_compile',not bad,'; '.join(bad[:5]))

compile_all()
for req in ['PROJECT_RULES.md','PATCH_PROTOCOL.md','FINALIZATION_REPORT.md','INFO/BOT_MAP.md','FINALIZATION_GATE.py']:
    ok('required_'+req,(ROOT/req).is_file(),req)

if ROLE=='fast':
    manifest=json.loads(text('modules_manifest.json'))
    files=manifest.get('files') or {}; markers=manifest.get('file_markers') or {}
    hash_bad=[]; marker_bad=[]
    for rel,sha in files.items():
        p=ROOT/rel
        if not p.is_file(): hash_bad.append(rel+':missing'); continue
        got=hashlib.sha256(p.read_bytes()).hexdigest()
        if got!=sha: hash_bad.append(rel)
        lines=p.read_text(encoding='utf-8',errors='replace').splitlines()
        marker=str(markers.get(rel) or '')
        if marker and (not lines or marker not in lines[0] or marker not in lines[-1]): marker_bad.append(rel)
    ok('manifest_sha256',not hash_bad,','.join(hash_bad[:8]))
    ok('module_markers',not marker_bad,','.join(marker_bad[:8]))

    all_py={p.name:p.read_text(encoding='utf-8',errors='replace') for p in ROOT.glob('*.py')}
    hot_methods=('send_message','edit_message_text','edit_message_caption','edit_message_reply_markup','delete_message','send_document','answer_callback_query','process_new_updates')
    binds=[]
    for fn,s in all_py.items():
        for m in hot_methods:
            for mat in re.finditer(rf'(?m)^\s*bot\.{re.escape(m)}\s*=',s): binds.append((fn,m))
    ok('telegram_bindings_only_89',all(fn=='89_callback_final.py' for fn,_ in binds),str(binds))
    ok('telegram_bindings_count',len(binds)==8,f'count={len(binds)} {binds}')

    runtime_py={k:v for k,v in all_py.items() if k!='FINALIZATION_GATE.py'}
    joined='\n'.join(runtime_py.values())
    runtime_ids=set()
    for src in runtime_py.values():
        try:
            tree=ast.parse(src)
            runtime_ids.update(n.id for n in ast.walk(tree) if isinstance(n,ast.Name))
            runtime_ids.update(n.name for n in ast.walk(tree) if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef,ast.ClassDef)))
        except Exception:
            pass
    for banned in ['PREV_PROCESS_NEW_UPDATES','ORIGINAL_PROCESS_NEW_UPDATES','_canon_execute_telegram_payload__001','_V263_BASE_EXECUTE_TELEGRAM_PAYLOAD','_canon_mega_run__001','ORIG_MEGA_RUN']:
        ok('absent_'+banned,banned not in runtime_ids,banned)
    ok('one_public_execute',count(r'(?m)^def _execute_telegram_payload\(',joined)==1,'expected one final execute')
    ok('one_execute_core',count(r'(?m)^def _execute_telegram_payload_core\(',joined)==1,'expected one execute core')
    ok('one_mega_public',count(r'(?m)^def _mega_run\(',joined)==1,'expected one _mega_run')
    ok('one_mega_raw',count(r'(?m)^def _mega_exec_raw\(',joined)==1,'expected one _mega_exec_raw')
    ok('one_extension_public',count(r'(?m)^def v149_extension_callback\(',joined)==1,'expected one final extension dispatcher')
    ok('no_extension_rebind',count(r'(?m)^\s*v149_extension_callback\s*=',joined)==0,'extension must be a direct def, not alias')
    ok('message_wrapper_v172_removed','def _v172_install_message_input_wrapper' not in joined,'old on_any_message wrapper installer')
    ok('message_wrapper_v174_removed','def _v174_install_message_wrapper' not in joined,'old on_any_message wrapper installer')
    def assigned_ids(src):
        try:
            tree=ast.parse(src); out=set()
            for n in ast.walk(tree):
                if isinstance(n,(ast.Assign,ast.AnnAssign,ast.NamedExpr)):
                    tgts=n.targets if isinstance(n,ast.Assign) else [n.target]
                    for t in tgts:
                        if isinstance(t,ast.Name): out.add(t.id)
            return out
        except Exception:return set()
    for mod,label in [('100_r33_heavy_offload.py','r100_no_prev_orig_base'),('98_split_front.py','r98_no_prev_orig_base')]:
        bad=sorted(x for x in assigned_ids(all_py.get(mod,'')) if re.search(r'_(?:PREV|ORIG|BASE)_',x))
        ok(label,not bad,','.join(bad[:8]))

    hot_public=['submit_interactive_file_job','v163_webhook_select_lane','contour_callback_guard','build_main_keyboard','v149_extension_callback','_r38_outbox_dispatch_one','_r38_outbox_enqueue','_r38_outbox_pending_rows']
    bad_globals=[]
    for fn,s in all_py.items():
        for name in hot_public:
            if re.search(rf"globals\(\)\[['\"]{re.escape(name)}['\"]\]\s*=",s): bad_globals.append((fn,name))
    ok('no_hot_globals_rebind',not bad_globals,str(bad_globals))

    ns={}; exec(text('runtime_config.py'),ns)
    env=ns.get('FRONT_INTERNAL_ENV') or {}
    limits={'BOT_THREAD_STACK_KB':512,'UI_WORKERS':2,'FAST_UI_WORKERS':2,'WINDOW_RENDER_WORKERS':2,'CALLBACK_ACK_WORKERS':1,'UI_CLEANUP_WORKERS':1,'UI_DELETE_WORKERS':1,'DELTA_WORKERS':1,'BACKGROUND_WORKERS':1,'SCHEDULER_WORKERS':2,'R21_HEAVY_DISPATCH_WORKERS':2,'BOT_JOURNAL_MAX':600,'R32_EVENT_QUEUE_MAX':5000}
    bad=[]
    for k,maxv in limits.items():
        try:
            if int(env.get(k,10**9))>maxv: bad.append(f'{k}={env.get(k)}>{maxv}')
        except Exception: bad.append(f'{k}=invalid')
    ok('fast_memory_budget',not bad,'; '.join(bad))
    ok('state_events_contract','/internal/state/events' in joined,'state events endpoint/transport missing')

elif ROLE=='heavy':
    s=text('worker_service.py')
    ok('heavy_no_prev_orig_base',not re.search(r'\b[A-Za-z0-9_]*_(?:PREV|ORIG|BASE)_[A-Za-z0-9_]*\b',s),'worker_service predecessor capture remains')
    ok('heavy_no_globals_rebind','globals()[' not in s,'worker_service should not monkey-patch globals')
    ok('heavy_final_file_owner',count(r'(?m)^process_file_job\s*=\s*process_file_job_r43\s*$',s)==1,'final R43 file owner')
    ok('heavy_final_google_owner',count(r'(?m)^process_google_job\s*=\s*process_google_job_r43\s*$',s)==1,'final R43 Google owner')
    ok('heavy_state_events_route','/internal/state/events' in s,'state events endpoint missing')
    ns={}; exec(text('runtime_config.py'),ns); env=ns.get('WORKER_INTERNAL_ENV') or {}
    try: threads=int(env.get('HEAVY_HTTP_THREADS',999))
    except Exception: threads=999
    ok('heavy_http_threads',threads<=4,f'HEAVY_HTTP_THREADS={threads}')
    try: q=int(env.get('WORKER_EVENT_REDIS_QUEUE_MAX',999999))
    except Exception: q=999999
    ok('heavy_event_queue',q<=1024,f'WORKER_EVENT_REDIS_QUEUE_MAX={q}')
else:
    errors.append('cannot detect role')

print(f'FINALIZATION_GATE role={ROLE}')
for name,passed,detail in checks:
    print(('PASS' if passed else 'FAIL')+f' {name}'+(f' :: {detail}' if detail and not passed else ''))
if errors:
    print(f'FINALIZATION_GATE FAILED ({len(errors)})')
    for e in errors: print(' - '+e)
    sys.exit(1)
print(f'FINALIZATION_GATE PASS ({len(checks)} checks)')
