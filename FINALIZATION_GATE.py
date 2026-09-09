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
for req in ['INFO/PROJECT_RULES.md','INFO/PATCH_PROTOCOL.md','INFO/FINALIZATION_REPORT.md','INFO/BOT_MAP.md','FINALIZATION_GATE.py']:
    ok('required_'+req,(ROOT/req).is_file(),req)

if ROLE=='fast':
    manifest=json.loads(text('modules_manifest.json'))
    files=manifest.get('files') or {}; markers=manifest.get('file_markers') or {}
    expected_root_py={
        '01_core_data.py','02_transport_safety.py','03_diagnostics_memory.py','04_messages_features.py',
        '05_finance_ui.py','06_commands_callbacks.py','07_state_web.py','08_reliability_tasks.py',
        '09_final_transport.py','10_split_policy_offload.py','bot.py','start_front.py','runtime_config.py','FINALIZATION_GATE.py'
    }
    actual_root_py={p.name for p in ROOT.glob('*.py')}
    ok('r48_compact_root_exact',actual_root_py==expected_root_py,
       'extra='+','.join(sorted(actual_root_py-expected_root_py))+' missing='+','.join(sorted(expected_root_py-actual_root_py)))
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
    ok('telegram_bindings_only_09_final_transport',all(fn=='09_final_transport.py' for fn,_ in binds),str(binds))
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
    def merged_section(src, old_name):
        marker=f'# --- ИСТОЧНИК: {old_name} ---'
        if marker not in src: return ''
        tail=src.split(marker,1)[1]
        nxt=tail.find('# --- ИСТОЧНИК: ')
        return tail if nxt < 0 else tail[:nxt]
    merged=all_py.get('10_split_policy_offload.py','')
    for old_name,label in [('98_split_front.py','r98_no_prev_orig_base'),('100_r33_heavy_offload.py','r100_no_prev_orig_base')]:
        section=merged_section(merged,old_name)
        bad=sorted(x for x in assigned_ids(section) if re.search(r'_(?:PREV|ORIG|BASE)_',x))
        ok(label,bool(section) and not bad,('missing section' if not section else ','.join(bad[:8])))

    hot_public=['submit_interactive_file_job','v163_webhook_select_lane','contour_callback_guard','build_main_keyboard','v149_extension_callback','_r38_outbox_dispatch_one','_r38_outbox_enqueue','_r38_outbox_pending_rows']
    bad_globals=[]
    for fn,s in all_py.items():
        for name in hot_public:
            if re.search(rf"globals\(\)\[['\"]{re.escape(name)}['\"]\]\s*=",s): bad_globals.append((fn,name))
    ok('no_hot_globals_rebind',not bad_globals,str(bad_globals))

    ns={}; exec(text('runtime_config.py'),ns)
    env=ns.get('FRONT_INTERNAL_ENV') or {}
    limits={'BOT_THREAD_STACK_KB':512,'UI_WORKERS':2,'FAST_UI_WORKERS':2,'WINDOW_RENDER_WORKERS':2,'CALLBACK_ACK_WORKERS':2,'UI_CLEANUP_WORKERS':1,'UI_DELETE_WORKERS':1,'DELTA_WORKERS':1,'BACKGROUND_WORKERS':1,'SCHEDULER_WORKERS':2,'R21_HEAVY_DISPATCH_WORKERS':2,'BOT_JOURNAL_MAX':600,'R32_EVENT_QUEUE_MAX':5000,'WEBHOOK_WORKERS':2}
    bad=[]
    for k,maxv in limits.items():
        try:
            if int(env.get(k,10**9))>maxv: bad.append(f'{k}={env.get(k)}>{maxv}')
        except Exception: bad.append(f'{k}=invalid')
    ok('fast_memory_budget',not bad,'; '.join(bad))
    ok('state_events_contract','/internal/state/events' in joined,'state events endpoint/transport missing')

    # R48 performance/finalization invariants.
    def _fn_sources(src: str, wanted: set[str]):
        out={}
        try:
            tree=ast.parse(src); lines=src.splitlines()
            for node in ast.walk(tree):
                if isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef)) and node.name in wanted:
                    out[node.name]='\n'.join(lines[node.lineno-1:node.end_lineno])
        except Exception:
            pass
        return out

    core_src=all_py.get('01_core_data.py','')
    msg_src=all_py.get('04_messages_features.py','')
    web_src=all_py.get('07_state_web.py','')
    rel_src=all_py.get('08_reliability_tasks.py','')
    split_src=all_py.get('10_split_policy_offload.py','')
    core_fns=_fn_sources(core_src,{'_lowram_flush_chat','bump_quick_balance_recreate_counter','_tg_call_retry'})
    rel_fns=_fn_sources(rel_src,{'_execute_telegram_payload_core'})
    split_fns=_fn_sources(split_src,{'_split_snapshot_meta'})
    ok('r48_lowram_flush_ram_only','SQLITE.' not in core_fns.get('_lowram_flush_chat','') and 'save_data(' not in core_fns.get('_lowram_flush_chat',''),'LOW-RAM flush must only create a RAM snapshot')
    ok('r48_visual_counter_ram_only','save_data(' not in core_fns.get('bump_quick_balance_recreate_counter',''),'visual counter must not persist on every message')
    ok('r48_no_whole_handler_chat_lock','telegram_execution_chat_lock' not in rel_fns.get('_execute_telegram_payload_core','') and 'with locked_chat' not in rel_fns.get('_execute_telegram_payload_core',''),'whole Telegram handler must not hold chat lock')
    ok('r48_peer_health_ram_only','SQLITE.' not in split_fns.get('_split_snapshot_meta',''),'peer health must not touch SQLite')
    ok('r48_sqlite_dedicated_reader', all(x in core_src for x in ["R25TracedRLock('sqlite-read')",'PRAGMA query_only=ON','def _read_one','def _read_all']),'query-only SQLite reader channel missing')
    ok('r48_single_finance_persist_owner', count(r'(?m)^def persist_finance_chat_local_fast\(',joined)==1 and count(r'(?m)^\s*persist_finance_chat_local_fast\s*=',joined)==0,'finance persistence must have one direct owner')
    ok('r48_finance_persist_guard','held_by_current_thread' in _fn_sources(msg_src,{'persist_finance_chat_local_fast'}).get('persist_finance_chat_local_fast',''),'finance persist must reject SQLite while chat lock is held')
    ok('r48_navigation_coalesce', all(x in web_src for x in ['_R48_NAV_INFLIGHT','def _r48_nav_coalesce_key','R48 NAV COALESCE']),'safe navigation coalescing missing')
    ok('r48_recovery_yields_to_user','r27_user_quiet_for' in web_src and '5.0' in web_src,'webhook recovery user-activity yield missing')
    ok('r48_no_callback_witness_thread','r18-cb-witness-' not in web_src,'callback witness must use bounded pool/scheduler')
    ok('r48_no_event_thread_fallback','vys262-event-r13' not in split_src,'state event fallback must not spawn per-event thread')

    # R48 STARTUPFIX: COMPACT14 contracts must validate semantic owners, never
    # historical pre-compaction filenames. This exact regression made Render
    # expose the preboot port while the Telegram runtime crashed during import.
    r29_src=_fn_sources(split_src,{'r29_assert_r28_fast_ui_contract'}).get('r29_assert_r28_fast_ui_contract','')
    ok('r48_r29_semantic_renderer_contract',
       "fn is not canonical" in r29_src and "_perform_fast_ui_edit(payload)" in r29_src and "co_filename" not in r29_src,
       'R29 must validate canonical callable behavior, not source filename')
    ok('r48_no_historical_renderer_filename_contract',
       '74_ui_reliability_runtime.py' not in r29_src,
       'historical renderer filename contract remains')
    ok('r48_no_prev_fast_ui_wrapper',
       '_V159_PREV_FAST_UI_EDIT' not in rel_src and count(r'(?m)^\s*def fast_ui_edit_message_text\(',rel_src)==0,
       'inactive PREV fast-ui wrapper remains')
    final_transport=all_py.get('09_final_transport.py','')
    ok('r48_one_final_fast_ui_binding',
       count(r'(?m)^fast_ui_edit_message_text\s*=\s*_canon_fast_ui_edit_message_text__001\s*$',final_transport)==1 and
       count(r'(?m)^\s*fast_ui_edit_message_text\s*=',joined)==1,
       'fast_ui_edit_message_text must have one final binding')
    bot_src=all_py.get('bot.py','')
    try:
        parts_match=re.search(r'MODULAR_SOURCE_PARTS\s*=\s*(\[[^\n]+\])',bot_src)
        parts=ast.literal_eval(parts_match.group(1)) if parts_match else []
    except Exception:
        parts=[]
    ok('r48_final_transport_loaded_before_policy_contract',
       '09_final_transport.py' in parts and '10_split_policy_offload.py' in parts and
       parts.index('09_final_transport.py') < parts.index('10_split_policy_offload.py'),
       str(parts))
    docker_src=text('Dockerfile') if (ROOT/'Dockerfile').is_file() else ''
    dockerignore_src=text('.dockerignore') if (ROOT/'.dockerignore').is_file() else ''
    ok('r48_docker_build_import_smoke',
       'python FINALIZATION_GATE.py' in docker_src and 'import bot' in docker_src and 'R48 FAST IMPORT SMOKE PASS' in docker_src,
       'Dockerfile must run gate + real bot import before CMD')
    ok('r48_docker_no_copy_dot',
       not re.search(r'(?m)^\s*COPY\s+\.\s+\.?/?',docker_src),
       'Dockerfile must never COPY the whole repository into FAST')
    ok('r48_docker_explicit_compact_copy',
       all(name in docker_src for name in ['01_core_data.py','09_final_transport.py','10_split_policy_offload.py','COPY INFO/ ./INFO/']),
       'Dockerfile must explicitly copy compact runtime and INFO')
    ok('r48_dockerignore_allowlist',
       dockerignore_src.lstrip().startswith('# R48 CLEAN BUILD ALLOWLIST') and '\n*\n' in dockerignore_src and '!INFO/' in dockerignore_src and '!10_split_policy_offload.py' in dockerignore_src,
       '.dockerignore must be a strict compact allowlist')

    # Literal whole-project lock audit: direct disk/network persistence is forbidden
    # inside the two central state locks. Keep this broad so future regressions fail PACKAGE.
    hard_calls={'save_data','persist_finance_chat_local_fast','finance_integrity_append','_tg_call_retry',
                'send_message','edit_message_text','edit_message_caption','edit_message_reply_markup',
                'delete_message','send_document','answer_callback_query','set_cold','set_cold_many',
                'save_chat','save_chat_bundle','save_root','set_kv','set_meta','backup_to'}
    lock_hits=[]
    def _call_name(n):
        return n.id if isinstance(n,ast.Name) else n.attr if isinstance(n,ast.Attribute) else ''
    for fn,src in runtime_py.items():
        try: tree=ast.parse(src)
        except Exception: continue
        for owner in [n for n in ast.walk(tree) if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef))]:
            for w in [n for n in ast.walk(owner) if isinstance(n,(ast.With,ast.AsyncWith))]:
                exprs=[]
                for item in w.items:
                    try: exprs.append(ast.unparse(item.context_expr))
                    except Exception: pass
                lock_kind = 'chat' if any(('locked_chat' in e or 'telegram_execution_chat_lock' in e) for e in exprs) else 'data' if any(re.search(r'\bdata_lock\b',e) for e in exprs) else ''
                if not lock_kind: continue
                for call in [n for n in ast.walk(w) if isinstance(n,ast.Call)]:
                    name=_call_name(call.func)
                    sqlite_attr=isinstance(call.func,ast.Attribute) and isinstance(call.func.value,ast.Name) and call.func.value.id=='SQLITE'
                    if name in hard_calls or sqlite_attr:
                        lock_hits.append(f'{fn}:{owner.name}:{lock_kind}:{name}@{call.lineno}')
    ok('r48_no_direct_io_under_chat_or_data_lock',not lock_hits,'; '.join(lock_hits[:12]))

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
