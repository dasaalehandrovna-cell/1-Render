#!/usr/bin/env python3
from __future__ import annotations
import ast, hashlib, json, os, py_compile, re, runpy, sys, threading
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
# INFO is release documentation, not a runtime dependency.  A Render/Git deployment
# may legitimately transfer only root runtime files.  PACKAGE validation keeps the
# docs mandatory by default; Docker sets FINALIZATION_REQUIRE_INFO=0 so missing
# documentation can never prevent the production bot from starting.
_require_info = str(os.getenv('FINALIZATION_REQUIRE_INFO','1')).strip().lower() not in {'0','false','no','off'}
_runtime_build = str(os.getenv('FINALIZATION_RUNTIME_BUILD','0')).strip().lower() in {'1','true','yes','on'}
_run_startup_smoke = str(os.getenv('FINALIZATION_STARTUP_SMOKE','0')).strip().lower() in {'1','true','yes','on'}
ok('required_FINALIZATION_GATE.py',(ROOT/'FINALIZATION_GATE.py').is_file(),'FINALIZATION_GATE.py')
for req in ['INFO/PROJECT_RULES.md','INFO/PATCH_PROTOCOL.md','INFO/FINALIZATION_REPORT.md','INFO/BOT_MAP.md']:
    if _require_info:
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
    limits={'BOT_THREAD_STACK_KB':512,'UI_WORKERS':2,'FAST_UI_WORKERS':2,'NAV_UI_WORKERS':3,'WINDOW_RENDER_WORKERS':2,'SERVICE_UI_WORKERS':1,'CALLBACK_ACK_WORKERS':2,'UI_CLEANUP_WORKERS':1,'UI_DELETE_WORKERS':1,'DELTA_WORKERS':1,'BACKGROUND_WORKERS':1,'SCHEDULER_WORKERS':2,'R21_HEAVY_DISPATCH_WORKERS':2,'BOT_JOURNAL_MAX':600,'R32_EVENT_QUEUE_MAX':5000,'WEBHOOK_WORKERS':2}
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
    ok('r48_sqlite_dedicated_reader', all(x in core_src for x in ['PRAGMA query_only=ON','def _get_reader','self._reader_local = threading.local()','def _read_one','def _read_all']),'query-only thread-local SQLite reader channel missing')
    ok('r48_single_finance_persist_owner', count(r'(?m)^def persist_finance_chat_local_fast\(',joined)==1 and count(r'(?m)^\s*persist_finance_chat_local_fast\s*=',joined)==0,'finance persistence must have one direct owner')
    ok('r48_finance_persist_guard','held_by_current_thread' in _fn_sources(msg_src,{'persist_finance_chat_local_fast'}).get('persist_finance_chat_local_fast',''),'finance persist must reject SQLite while chat lock is held')
    ok('r48_navigation_coalesce', 'NAV_UI_TASK_POOL' in rel_src and 'submit_latest' in web_src and 'superseded_safe_navigation_r50' in web_src,'safe navigation latest-wins missing')
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
    if not _runtime_build:
        docker_src=text('Dockerfile') if (ROOT/'Dockerfile').is_file() else ''
        dockerignore_src=text('.dockerignore') if (ROOT/'.dockerignore').is_file() else ''
        ok('r48_docker_build_import_smoke',
           'FINALIZATION_REQUIRE_INFO=0 FINALIZATION_RUNTIME_BUILD=1 FINALIZATION_STARTUP_SMOKE=1' in docker_src and 'python FINALIZATION_GATE.py' in docker_src,
           'Dockerfile must run runtime-only gate with deterministic startup smoke before CMD')
        ok('r48_docker_no_copy_dot',
           not re.search(r'(?m)^\s*COPY\s+\.\s+\.?/?',docker_src),
           'Dockerfile must never COPY the whole repository into FAST')
        ok('r48_docker_explicit_compact_copy',
           all(name in docker_src for name in ['01_core_data.py','09_final_transport.py','10_split_policy_offload.py']) and 'COPY INFO/' not in docker_src,
           'Dockerfile must explicitly copy only compact runtime; INFO must not be a production dependency')
        ok('r48_dockerignore_allowlist',
           dockerignore_src.lstrip().startswith('# R51 FINAL CLEAN BUILD ALLOWLIST') and '\n*\n' in dockerignore_src and '!INFO/' not in dockerignore_src and '!10_split_policy_offload.py' in dockerignore_src,
           '.dockerignore must be a strict runtime-only compact allowlist; INFO is release-only')

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

    # R49 PERFORMANCE / RESTORE FINALIZATION invariants.
    start_src=all_py.get('start_front.py','')
    cfg_src=all_py.get('runtime_config.py','')
    req_src=text('requirements.txt') if (ROOT/'requirements.txt').is_file() else ''
    owner_src=all_py.get('09_final_transport.py','')

    ok('r49_sqlite_single_priority_writer',
       all(x in core_src for x in ["name='sqlite-writer-1'",'self._writer_heap','def _writer_loop','def _write','def writer_status']) and
       'PriorityQueue' not in core_src[core_src.find('class SQLiteState'):core_src.find('class SQLiteState')+5000],
       'main SQLite must have one heap/priority writer owner')
    direct_sqlite_owners=[]
    for fn,src in runtime_py.items():
        if fn=='01_core_data.py':
            # Direct conn/lock access is allowed only inside SQLiteState itself.
            try:
                tree=ast.parse(src)
                for node in ast.walk(tree):
                    if isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef)) and node.name not in {'__init__','_connect_read','_writer_loop','_write','_read_one','_read_all','backup_to','replace_database','close'}:
                        seg='\n'.join(src.splitlines()[node.lineno-1:node.end_lineno])
                        if 'SQLITE.lock' in seg or 'SQLITE.conn' in seg:
                            direct_sqlite_owners.append(f'{fn}:{node.name}')
            except Exception: pass
        else:
            try:
                tree=ast.parse(src)
                if any(isinstance(n,ast.Attribute) and isinstance(n.value,ast.Name) and n.value.id=='SQLITE' and n.attr in {'lock','conn'} for n in ast.walk(tree)):
                    direct_sqlite_owners.append(fn)
            except Exception:
                pass
    ok('r49_no_external_sqlite_conn_lock',not direct_sqlite_owners,','.join(direct_sqlite_owners[:12]))

    ok('r49_webhook_inbox_persistent_store',
       'class _V260WebhookInboxStore' in web_src and '_v260_inbox_connect' not in web_src and
       count(r'PRAGMA journal_mode=WAL', _fn_sources(web_src,{'__init__'}).get('__init__','')) <= 1 and
       '_v260_webhook_inbox_mark_async' in web_src,
       'webhook inbox must initialize once and mark done asynchronously')
    ok('r49_owner_message_callable',
       '_v221_owner_message_command' not in joined and '_v221_capture_owner_message(msg)' in owner_src and
       count(r'(?m)^def _v221_capture_owner_message\(',joined)==1,
       'owner-message interceptor must call the single existing canonical owner')
    ok('r49_waitress_bounded_http',
       'waitress' in req_src.lower() and 'from waitress import serve' in web_src and 'app.run(' not in web_src and
       "WEBHOOK_MAX_CONNECTIONS\": \"8\"" in cfg_src and "WAITRESS_THREADS\": \"6\"" in cfg_src,
       'FAST must use bounded Waitress and webhook max_connections=8')
    ok('r49_restore_trace_present',
       'R49_RESTORE_TRACE_JSON' in start_src and '[RESTORE TRACE R49]' in start_src and 'restore_trace' in web_src and 'RESTORE TRACE R49' in core_src,
       'restore source/revision trace missing from startup or Watcher')
    try:
        i_redis=start_src.index('R49 Redis-first restore:')
        i_heavy=start_src.index('R49 HEAVY restore:')
        i_mega=start_src.index('R49 MEGA disaster restore:')
        restore_order_ok=i_redis < i_heavy < i_mega
    except ValueError:
        restore_order_ok=False
    ok('r49_restore_order_redis_heavy_mega',restore_order_ok,'expected Redis -> HEAVY -> MEGA')
    ok('r49_redis_empty_falls_through',
       "Redis snapshot empty" in start_src and 'need_fallback' in start_src and 'not local_valid' in start_src,
       'empty/invalid Redis must not stop fallback recovery')
    ok('r49_redis_before_heavy_mega_seed',
       'r49_before_heavy_mega_fallback' in start_src and
       '_r43_store_events_redis(events)' in split_src and split_src.index('_r43_store_events_redis(events)') < split_src.index("requests.post(base+endpoint"),
       'current state/events must be persisted to Redis before HEAVY mirror/fallback when possible')
    ok('r49_watchdog_http_ack_state',
       'HTTP_200_SENT / INTERNAL_PROCESSING' in core_src and 'HTTP_NOT_ACKED / TELEGRAM_MAY_RETRY' in core_src and 'Telegram will retry until 2xx' not in core_src,
       'watchdog must distinguish already-ACKed HTTP from Telegram retry risk')
    ok('r49_runtime_lock_hold_trace',
       'LOCKHELD' in core_src and 'LOCKHELD_STACK' in core_src and '0.050' in core_src and '0.250' in core_src,
       'runtime central-lock hold thresholds/stack trace missing')

    # Lightweight transitive call-graph audit.  Only direct Name() calls are
    # followed to avoid conflating unrelated generic methods like dict.get().
    # This catches helpers that hide SQLite/network/persist under central locks.
    cg_calls={}; cg_locks=[]
    cg_danger={'save_data','persist_finance_chat_local_fast','finance_integrity_append','_tg_call_retry',
               '_split_cache_snapshot_to_redis_v266','_mega_run','_mega_exec_raw','run_cmd'}
    for fn,src in runtime_py.items():
        try: tree=ast.parse(src)
        except Exception: continue
        for node in ast.walk(tree):
            if not isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef)): continue
            calls={c.func.id for c in ast.walk(node) if isinstance(c,ast.Call) and isinstance(c.func,ast.Name)}
            if any(isinstance(c,ast.Call) and isinstance(c.func,ast.Attribute) and isinstance(c.func.value,ast.Name) and c.func.value.id in {'SQLITE','requests'} for c in ast.walk(node)):
                calls.add('__DIRECT_IO__')
            cg_calls.setdefault(node.name,set()).update(calls)
            if node.name.startswith('_v177_legacy_'): continue
            for w in [x for x in ast.walk(node) if isinstance(x,(ast.With,ast.AsyncWith))]:
                expr=' '.join(ast.unparse(i.context_expr) for i in w.items)
                kind='chat' if ('locked_chat' in expr or 'telegram_execution_chat_lock' in expr) else 'data' if re.search(r'\bdata_lock\b',expr) else ''
                if not kind: continue
                wcalls={c.func.id for c in ast.walk(w) if isinstance(c,ast.Call) and isinstance(c.func,ast.Name)}
                if any(isinstance(c,ast.Call) and isinstance(c.func,ast.Attribute) and isinstance(c.func.value,ast.Name) and c.func.value.id in {'SQLITE','requests'} for c in ast.walk(w)):
                    wcalls.add('__DIRECT_IO__')
                cg_locks.append((fn,node.name,kind,node.lineno,wcalls))
    def _cg_risk(name,seen=None):
        seen=set() if seen is None else set(seen)
        if name=='__DIRECT_IO__' or name in cg_danger: return [name]
        if name in seen: return []
        seen.add(name)
        for nxt in cg_calls.get(name,()):
            path=_cg_risk(nxt,seen)
            if path: return [name]+path
        return []
    cg_hits=[]
    for fn,owner,kind,line,wcalls in cg_locks:
        for call in wcalls:
            path=_cg_risk(call)
            if path:
                cg_hits.append(f'{fn}:{owner}:{kind}@{line}:'+' -> '.join(path)); break
    ok('r49_no_indirect_io_under_central_locks',not cg_hits,'; '.join(cg_hits[:12]))

    # R50 UI ACTOR / LOCK ORDER invariants.
    core_get=_fn_sources(core_src,{'get_chat_store'}).get('get_chat_store','')
    root_snap=_fn_sources(core_src,{'r50_root_snapshot'}).get('r50_root_snapshot','')
    main_sched=_fn_sources(core_src,{'schedule_main_window_recreate_after_quiet','schedule_quick_balance_recreate_after_quiet'})
    fast_edit=_fn_sources(rel_src,{'_canon_fast_ui_edit_message_text__001'}).get('_canon_fast_ui_edit_message_text__001','')
    ok('r50_chat_registry_independent','_CHAT_STORE_REGISTRY_LOCK' in core_get and 'data_lock' not in core_get,'get_chat_store must never wait for data_lock')
    ok('r50_root_deepcopy_outside_data_lock','refs = dict(_sqlite_pack_root(src))' in root_snap and 'return copy.deepcopy(refs)' in root_snap,'root snapshot must detach under lock and recurse outside')
    ok('r50_safe_nav_latest_pool','NAV_UI_TASK_POOL = LatestKeyedTaskPool' in core_src and 'return (NAV_UI_TASK_POOL' in rel_src and '_on_supersede' in web_src,'navigation must be latest-wins per window')
    ok('r50_stale_transport_epoch',all(x in joined for x in ['def r50_ui_note_interaction','def r50_ui_context_stale','r50_stale_edit_skipped','stale_skipped']),'stale callback transport fence missing')
    ok('r50_auto_recreate_epoch_quiet',all(('r50_ui_epoch_matches' in src and 'r50_ui_is_quiet' in src) for src in main_sched.values()),'auto window recreate must be epoch+quiet fenced')
    ok('r50_background_lock_yield',('R50_BG_LOCK_MAX_WAIT_SEC' in core_src or 'R51_BG_LOCK_MAX_WAIT_SEC' in core_src) and 'r27_user_quiet_for() < grace' in core_src,'background must yield outside locks while user active')

    # Detect any transitive data_lock acquisition reachable from a chat-lock body.
    fn_calls={}; fn_has_data=set(); chat_lock_callsets=[]
    for fn,src in runtime_py.items():
        try: tree=ast.parse(src)
        except Exception: continue
        for node in ast.walk(tree):
            if not isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef)): continue
            fn_calls.setdefault(node.name,set()).update(c.func.id for c in ast.walk(node) if isinstance(c,ast.Call) and isinstance(c.func,ast.Name))
            for w in [x for x in ast.walk(node) if isinstance(x,(ast.With,ast.AsyncWith))]:
                expr=' '.join(ast.unparse(i.context_expr) for i in w.items)
                if re.search(r'\bdata_lock\b',expr): fn_has_data.add(node.name)
                if 'locked_chat' in expr or 'telegram_execution_chat_lock' in expr:
                    chat_lock_callsets.append((fn,node.name,w.lineno,{c.func.id for c in ast.walk(w) if isinstance(c,ast.Call) and isinstance(c.func,ast.Name)}))
    def _r50_data_path(name,seen=None):
        if name in fn_has_data:return [name]
        seen=set() if seen is None else set(seen)
        if name in seen:return []
        seen.add(name)
        for nxt in fn_calls.get(name,()):
            path=_r50_data_path(nxt,seen)
            if path:return [name]+path
        return []
    lock_order_hits=[]
    for fn,owner,line,cs in chat_lock_callsets:
        for c in cs:
            path=_r50_data_path(c)
            if path: lock_order_hits.append(f'{fn}:{owner}@{line}:'+' -> '.join(path)); break
    ok('r50_no_chat_to_data_lock_order',not lock_order_hits,'; '.join(lock_order_hits[:12]))

    recursive_hits=[]
    for fn,src in runtime_py.items():
        try: tree=ast.parse(src)
        except Exception: continue
        for owner in [n for n in ast.walk(tree) if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef))]:
            for w in [x for x in ast.walk(owner) if isinstance(x,(ast.With,ast.AsyncWith))]:
                expr=' '.join(ast.unparse(i.context_expr) for i in w.items)
                if 'locked_chat' not in expr and 'telegram_execution_chat_lock' not in expr: continue
                for c in ast.walk(w):
                    if not isinstance(c,ast.Call): continue
                    name=ast.unparse(c.func)
                    if name in {'copy.deepcopy','json.dumps','json.loads'}: recursive_hits.append(f'{fn}:{owner.name}:{name}@{c.lineno}')
    ok('r50_no_recursive_copy_under_chat_lock',not recursive_hits,'; '.join(recursive_hits[:12]))

    # R51: network I/O and stale visual work must be detached from business actors.
    core = runtime_py.get('01_core_data.py','')
    state_web = runtime_py.get('07_state_web.py','')
    reliability = runtime_py.get('08_reliability_tasks.py','')
    policy = runtime_py.get('10_split_policy_offload.py','')
    fast_sources = _fn_sources(rel_src, {'_canon_fast_ui_edit_message_text__001','_v199_upsert_service_window','_r51_service_apply','_read_one','_read_all'})
    fast_owner = fast_sources.get('_canon_fast_ui_edit_message_text__001','')
    service_upsert = fast_sources.get('_v199_upsert_service_window','')
    service_apply = fast_sources.get('_r51_service_apply','')
    read_one = fast_sources.get('_read_one',''); read_all = fast_sources.get('_read_all','')
    ok('r51_window_render_latest_actor',
       "WINDOW_RENDER_TASK_POOL = LatestKeyedTaskPool('window-render'" in core and
       'WINDOW_RENDER_TASK_POOL.submit_latest' in fast_owner and
       '_r22_execute_window_render' in fast_owner and
       '_perform_fast_ui_edit(payload)' not in fast_owner,
       'window render still performs Telegram I/O in callback or is not latest-wins')
    ok('r51_service_window_actor',
       "SERVICE_UI_TASK_POOL = LatestKeyedTaskPool('service-ui'" in core and
       '_r51_service_submit' in service_upsert and 'bot.send_message' not in service_upsert and
       'bot.edit_message_text' not in service_upsert and '_tg_call_retry' in service_apply,
       'F233 service window is still synchronous in callback path')
    ok('r51_telegram_network_bounds',
       'R51_TELEGRAM_CONNECT_TIMEOUT' in core and 'R51_TELEGRAM_READ_TIMEOUT' in core and
       '_install_r51_telegram_request_timeout()' in core and "host == 'api.telegram.org'" in core,
       'Telegram ordinary calls have no hard connect/read timeout')
    ok('r51_all_callback_window_epoch',
       '_r50_nav_window_key, _r50_nav_epoch = r50_ui_note_interaction(int(cid), int(mid), raw)' in state_web and
       'if cid is not None and mid is not None:' in state_web,
       'business callbacks do not receive a stale-render epoch')
    ok('r51_business_backpressure',
       'R51_BUSINESS_MAX_QUEUED_PER_KEY' in state_web and 'fast_ui_business_backpressure' in state_web and
       "return ('BUSY', 503)" in state_web,
       'ordered business queue can still accept an unbounded minutes-long RAM backlog')
    ok('r51_thread_local_sqlite_readers',
       'self._reader_local = threading.local()' in core and '_get_reader().execute' in core and
       'with self.read_lock' not in read_one and 'with self.read_lock' not in read_all,
       'main SQLite reads are still serialized by one Python read lock')
    ok('r51_service_progress_no_direct_telegram',
       'bot.edit_message_text(rendered, chat_id=chat_id, message_id=int(msg_id))' not in reliability and
       'bot.edit_message_text(rendered, chat_id=int(target_chat_id), message_id=mid)' not in reliability,
       'F233 progress/helper still performs direct Telegram edit')
    ok('r51_runtime_contract_detached_render',
       'latest render actor missing' in policy and 'callback renderer performs Telegram I/O directly' in policy,
       'startup semantic guard does not enforce detached render actor')

    if _run_startup_smoke:
        # Deterministic build-time import smoke.  Execute the complete modular bot
        # and all startup contracts, but prevent daemon/background threads from
        # actually starting during Docker build.  This catches NameError/order/
        # contract regressions without requiring Telegram/Redis/MEGA network I/O.
        _orig_thread_start = threading.Thread.start
        threading.Thread.start = lambda self: None
        try:
            ns = runpy.run_path(str(ROOT/'bot.py'), run_name='r49_gate_startup_smoke')
            contract = ns.get('r29_assert_r28_fast_ui_contract')
            bot_obj = ns.get('bot')
            msg_n = len(getattr(bot_obj,'message_handlers',[]) or [])
            cb_n = len(getattr(bot_obj,'callback_query_handlers',[]) or [])
            smoke_ok = callable(contract) and contract() is True and msg_n > 0 and cb_n > 0
            ok('r48_deterministic_startup_smoke', smoke_ok, f'handlers={msg_n}/{cb_n}')
        except BaseException as exc:
            ok('r48_deterministic_startup_smoke', False, f'{type(exc).__name__}: {exc}')
        finally:
            threading.Thread.start = _orig_thread_start

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
