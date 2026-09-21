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
for req in ['INFO/PROJECT_RULES.md','INFO/PATCH_PROTOCOL.md','INFO/FINALIZATION_REPORT.md','INFO/BOT_MAP.md','INFO/CHANGELOG.md','INFO/NEXT_CHAT_HANDOFF.md','INFO/DEPLOY_R69_RU.md']:
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
    # R69 release layout: PACKAGE root and Docker runtime root are intentionally different.
    # PACKAGE must contain Dockerfile/.dockerignore for deployment; Docker /app must NOT
    # require those build-context files because the explicit Docker COPY allowlist omits them.
    package_root_files = expected_root_py | {
        'Dockerfile','.dockerignore','requirements.txt','modules_manifest.json'
    }
    runtime_root_files = expected_root_py | {
        'requirements.txt','modules_manifest.json'
    }
    actual_root_files = {x.name for x in ROOT.iterdir() if x.is_file()}
    expected_mode_root = runtime_root_files if _runtime_build else package_root_files
    mode_check = 'r69_runtime_build_root_exact' if _runtime_build else 'r69_package_root_deploy_files_only'
    ok(mode_check, actual_root_files == expected_mode_root,
       'extra='+','.join(sorted(actual_root_files-expected_mode_root))+' missing='+','.join(sorted(expected_mode_root-actual_root_files)))
    hash_bad=[]; marker_bad=[]
    for rel,sha in files.items():
        p=ROOT/rel
        if not p.is_file(): hash_bad.append(rel+':missing'); continue
        got=hashlib.sha256(p.read_bytes()).hexdigest()
        if got!=sha: hash_bad.append(rel)
        lines=p.read_text(encoding='utf-8',errors='replace').splitlines()
        marker=str(markers.get(rel) or '')
        expected_marker = '# ' + marker if marker else ''
        if marker and (not lines or lines[0].strip() != expected_marker or lines[-1].strip() != expected_marker): marker_bad.append(rel)
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
    # R72 gate-speed: parse each large compact module once and reuse its AST in all audits.
    _ast_cache={}
    def _parse_src(src):
        tree=_ast_cache.get(src)
        if tree is None:
            tree=ast.parse(src)
            _ast_cache[src]=tree
        return tree
    runtime_ids=set()
    for src in runtime_py.values():
        try:
            tree=_parse_src(src)
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
            tree=_parse_src(src); out=set()
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
    limits={'BOT_THREAD_STACK_KB':512,'UI_WORKERS':2,'FAST_UI_WORKERS':2,'WINDOW_RENDER_WORKERS':2,'CALLBACK_ACK_WORKERS':2,'UI_CLEANUP_WORKERS':1,'UI_DELETE_WORKERS':1,'DELTA_WORKERS':1,'BACKGROUND_WORKERS':1,'SCHEDULER_WORKERS':1,'R21_HEAVY_DISPATCH_WORKERS':2,'BOT_JOURNAL_MAX':300,'R32_EVENT_QUEUE_MAX':5000,'WEBHOOK_WORKERS':2}
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
            tree=_parse_src(src); lines=src.splitlines()
            for node in ast.walk(tree):
                if isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef)) and node.name in wanted:
                    out[node.name]='\n'.join(lines[node.lineno-1:node.end_lineno])
        except Exception:
            pass
        return out

    core_src=all_py.get('01_core_data.py','')
    diag_src=all_py.get('03_diagnostics_memory.py','')
    msg_src=all_py.get('04_messages_features.py','')
    web_src=all_py.get('07_state_web.py','')
    cmd_src=all_py.get('06_commands_callbacks.py','')
    rel_src=all_py.get('08_reliability_tasks.py','')
    split_src=all_py.get('10_split_policy_offload.py','')
    core_fns=_fn_sources(core_src,{'_lowram_flush_chat','bump_quick_balance_recreate_counter','_tg_call_retry'})
    rel_fns=_fn_sources(rel_src,{'_execute_telegram_payload_core'})
    split_fns=_fn_sources(split_src,{'_split_snapshot_meta'})
    ok('r48_lowram_flush_ram_only','SQLITE.' not in core_fns.get('_lowram_flush_chat','') and 'save_data(' not in core_fns.get('_lowram_flush_chat',''),'LOW-RAM flush must only create a RAM snapshot')
    ok('r48_visual_counter_ram_only','save_data(' not in core_fns.get('bump_quick_balance_recreate_counter',''),'visual counter must not persist on every message')
    ok('r48_no_whole_handler_chat_lock','telegram_execution_chat_lock' not in rel_fns.get('_execute_telegram_payload_core','') and 'with locked_chat' not in rel_fns.get('_execute_telegram_payload_core',''),'whole Telegram handler must not hold chat lock')
    ok('r48_peer_health_ram_only','SQLITE.' not in split_fns.get('_split_snapshot_meta',''),'peer health must not touch SQLite')
    ok('r48_sqlite_dedicated_reader', all(x in core_src for x in ['self._read_tls = threading.local()', 'PRAGMA query_only=ON','def _reader_v111','def _read_one','def _read_all']),'thread-local query-only SQLite reader channels missing')
    ok('r48_single_finance_persist_owner', count(r'(?m)^def persist_finance_chat_local_fast\(',joined)==1 and count(r'(?m)^\s*persist_finance_chat_local_fast\s*=',joined)==0,'finance persistence must have one direct owner')
    ok('r48_finance_persist_guard','held_by_current_thread' in _fn_sources(msg_src,{'persist_finance_chat_local_fast'}).get('persist_finance_chat_local_fast',''),'finance persist must reject SQLite while chat lock is held')
    ok('r48_navigation_coalesce', all(x in web_src for x in ['_R48_NAV_INFLIGHT','def _r48_nav_coalesce_key','R48 NAV COALESCE']),'safe navigation coalescing missing')
    ok('r48_recovery_yields_to_user','r27_user_quiet_for' in web_src and '5.0' in web_src,'webhook recovery user-activity yield missing')
    ok('r67_boot_callback_recovery_policy', all(x in web_src for x in ['def _r67_callback_boot_recovery_policy','BOOT_REPLAY update=','boot_drop_r67','boot_review_r67']), 'boot callback replay classification/logging missing')
    ok('r67_no_blind_running_callback_boot_replay', "if state == 'queued':\n            return ('business_mutation', 'replay', action)" in web_src and "return ('business_mutation', 'needs_review', action)" in web_src, 'running/failed business callback must not blindly replay after restart')
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
    r67_final_symbols={
        '_google_access_token','_google_sheets_create_category_report','_run_delta_batch','build_info_keyboard','build_info_text','build_main_keyboard',
        'config_guard_sync_remote_v234','contour_callback_guard','load_data','mega_upload_latest_database_backup','persist_critical_delta_now',
        'runtime_mark_ready','schedule_config_backup_for_chats','schedule_delta_backup','schedule_startup_main_windows','send_exact_range_export',
        'send_export_for_chat_to','submit_interactive_file_job','tenant_google_handle_message','v163_webhook_select_lane'
    }
    r67_owners={name:[] for name in r67_final_symbols}
    def _r67_module_scope_nodes(body):
        for node in body:
            yield node
            # Module-level if/try/with branches still create globals.  Do not descend
            # into function/class bodies because assignments there are locals.
            if isinstance(node,(ast.If,ast.For,ast.While,ast.With,ast.Try)):
                for attr in ('body','orelse','finalbody'):
                    yield from _r67_module_scope_nodes(getattr(node,attr,[]) or [])
                if isinstance(node,ast.Try):
                    for handler in node.handlers:
                        yield from _r67_module_scope_nodes(handler.body)
            elif isinstance(node,ast.Match):
                for case in node.cases:
                    yield from _r67_module_scope_nodes(case.body)
    for fn,src in runtime_py.items():
        try: tree=_parse_src(src)
        except Exception: continue
        for node in _r67_module_scope_nodes(tree.body):
            if isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef)) and node.name in r67_owners:
                r67_owners[node.name].append((fn,node.lineno,'def'))
            elif isinstance(node,ast.Assign):
                for tgt in node.targets:
                    if isinstance(tgt,ast.Name) and tgt.id in r67_owners:
                        r67_owners[tgt.id].append((fn,node.lineno,'assign'))
            elif isinstance(node,ast.AnnAssign) and isinstance(node.target,ast.Name) and node.target.id in r67_owners:
                r67_owners[node.target.id].append((fn,node.lineno,'assign'))
    # R71/очнись_4 intentionally retains one final runtime router for the symbols
    # whose executor can be switched by the owner between R1 and R2.  Older owners
    # remain as named implementation cores; the final R71 router is the public gate.
    r71_switchable={'_google_sheets_create_category_report','contour_callback_guard','mega_upload_latest_database_backup',
                    'persist_critical_delta_now','schedule_config_backup_for_chats','schedule_delta_backup','submit_interactive_file_job'}
    r67_dup={k:v for k,v in r67_owners.items() if len(v)!=1 and k not in r71_switchable}
    ok('r67_single_public_runtime_owner',not r67_dup,str(r67_dup))
    ok('r71_runtime_owner_router',
       all(x in split_src for x in ['_R71_ROUTE_KEYS','def _r71_route_owner','def _r71_contour_callback_guard','def _r71_google_create','def _r71_submit_local_file_job']) and
       all(k in split_src for k in ["'google'","'files'","'diagnostics'","'mega'"]),
       'R71 owner router / all four switch groups missing')
    ok('r67_no_prev_contour_chain','_R29_PREV_CONTOUR_GUARD' not in split_src,'R29 PREV contour chain remains')
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
           dockerignore_src.lstrip().startswith('# R69 DEPLOY-ONLY ALLOWLIST') and '\n*\n' in dockerignore_src and '!INFO/' not in dockerignore_src and '!10_split_policy_offload.py' in dockerignore_src,
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
        try: tree=_parse_src(src)
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
                tree=_parse_src(src)
                for node in ast.walk(tree):
                    if isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef)) and node.name not in {'__init__','_connect_read','_writer_loop','_write','_read_one','_read_all','backup_to','replace_database','close'}:
                        seg='\n'.join(src.splitlines()[node.lineno-1:node.end_lineno])
                        if 'SQLITE.lock' in seg or 'SQLITE.conn' in seg:
                            direct_sqlite_owners.append(f'{fn}:{node.name}')
            except Exception: pass
        else:
            try:
                tree=_parse_src(src)
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
       "WEBHOOK_MAX_CONNECTIONS\": \"4\"" in cfg_src and "WAITRESS_THREADS\": \"2\"" in cfg_src,
       'FAST must use bounded Waitress with lean 2-thread/4-connection front')
    ok('r68_restore_trace_present',
       'R68_RESTORE_TRACE_JSON' in start_src and '[RESTORE TRACE R68]' in start_src and
       'LOCAL_RESTORE_TRACE_FILE' in cfg_src and '_r68_write_restore_trace_file' in start_src and
       'restore_trace' in web_src and 'RESTORE TRACE R68' in core_src,
       'R68 restore source/revision trace file or Watcher integration missing')
    # OCH12.6: Redis FULL+TAIL is assembled first. If Render MEGA_ENABLED=1,
    # FAST compares only compact_v80/head.json and downloads fixed latest/tail only
    # when MEGA proves newer or Redis/local recovery is unavailable. No tree scans.
    compact_src=_fn_sources(start_src,{'_r80_compact_mega_compare_restore'}).get('_r80_compact_mega_compare_restore','')
    start_main_src=_fn_sources(start_src,{'main'}).get('main','')
    ok('och1220_one_pass_recovery_ignores_switches',
       all(x in start_src for x in [
           "OCH12.22_ONE_PASS_THEN_EMPTY",
           "recovery ignores REDIS_ENABLED",
           "MEGA_ENABLED=0. No compare loop, no tree scan, no retry",
           "EMPTY_INIT_AFTER_ONE_PASS",
           "SPLIT_PREBOOT_EMPTY_INIT_R1220",
       ]) and
       'def _och1214_recovery_safe_wait' not in start_src and
       'mega-find' not in compact_src and '/internal/snapshot' not in start_src,
       '12.21 startup must try recovery sources once regardless runtime switches, then create empty SQLite')
    ok('och1220_redis_then_mega_single_pass',
       all(x in start_src for x in ['def _restore_from_redis_startup',
                                    'OCH12.22 one-pass Redis FULL+TAIL start',
                                    'WORKER_REDIS_SNAPSHOT_KEY','WORKER_R32_STATE_EVENT_PREFIX',
                                    'Redis TAIL incomplete:', '_apply_r32_events(candidate,events)',
                                    "trace['base_source'] = 'REDIS_ONE_PASS'",
                                    "trace['base_source'] = 'MEGA_COMPACT_ONE_PASS'",
                                    '_r80_compact_mega_compare_restore(target, have_current=False)']) and
       start_main_src.find('ok, detail = _restore_from_redis_startup(target)') < start_main_src.find('_r80_compact_mega_compare_restore(target, have_current=False)'),
       '12.21 must try Redis once before compact MEGA and never retry either source')
    ok('r68_local_cache_before_external_restore',
       all(x in start_src for x in ['def _restore_from_local_runtime_cache','def _r68_load_local_events',
                                    'LOCAL_SQLITE_SNAPSHOT_FILE','LOCAL_STATE_EVENT_JOURNAL_FILE',
                                    "trace['base_source'] = 'LOCAL_RUNTIME_CACHE_FAST'",
                                    'OCH12.22 local cache absent']) and
       start_main_src.find('ok, detail = _restore_from_local_runtime_cache(target)') <
       start_main_src.find('ok, detail = _restore_from_redis_startup(target)') <
       start_main_src.find('_r80_compact_mega_compare_restore(target, have_current=False)'),
       'same-container cache must be checked once before Redis and MEGA')
    ok('r68_local_files_packaged_config',
       all(x in cfg_src for x in [
           '"LOCAL_RUNTIME_DIR": "/tmp/vys262_fast_local"',
           '"LOCAL_STATE_EVENT_JOURNAL_FILE": "/tmp/vys262_fast_local/events.jsonl"',
           '"LOCAL_RUNTIME_STATE_FILE": "/tmp/vys262_fast_local/runtime_state.json"',
           '"LOCAL_SQLITE_SNAPSHOT_FILE": "/tmp/vys262_fast_local/state.sqlite3.gz"',
           '"LOCAL_RESTORE_TRACE_FILE": "/tmp/vys262_fast_local/restore_trace.json"',
           '"WEBHOOK_INBOX_DB_FILE": "/tmp/vys262_fast_local/webhook.sqlite3"',
       ]),
       'R68 local ephemeral file layout missing from runtime_config')
    enqueue_src=_fn_sources(split_src,{'_r32_enqueue_descriptor'}).get('_r32_enqueue_descriptor','')
    sender_src=_fn_sources(split_src,{'_r32_sender_loop'}).get('_r32_sender_loop','')
    ok('r68_event_jsonl_background_only',
       'def _r68_local_event_append' in split_src and
       '_r68_local_event_append' not in enqueue_src and
       '_r68_local_event_append(packet.get' in sender_src and
       'LOCAL_STATE_EVENT_JOURNAL_MAX_MB' in split_src,
       'events.jsonl must be written only by the background state-event sender, never callback capture')
    ok('r68_runtime_snapshot_background_only',
       'def _r68_write_local_runtime_state' in core_src and
       'def _r68_write_local_sqlite_snapshot' in core_src and
       'def _r68_local_runtime_tick' in core_src and
       "MAINTENANCE_TASK_POOL.submit('r68-local-sqlite-snapshot'" in core_src and
       "DELAYED_SCHEDULER.schedule('r68-local-runtime-tick'" in core_src,
       'runtime_state/local SQLite.gz must use existing background workers/scheduler')
    ok('r71_fast_runtime_heavy_credentials_parked',
       "os.environ['FAST_RUNTIME_MEGA_DISABLED'] = '1'" in start_src and
       "os.environ['MEGA_ENABLED'] = '0'" in start_src and
       "runtime_heavy_credentials_parked_for_r71" in start_src and
       "os.environ.pop('GOOGLE_SERVICE_ACCOUNT_JSON', None)" not in start_src,
       'FAST must park MEGA OFF by default while retaining credentials for explicit R71 switch')
    replay_src=_fn_sources(start_src,{'_replay_mega_event_segments'}).get('_replay_mega_event_segments','')
    ok('r55_mega_event_replay_checkpoint_tail_safe',
       'FAST_STARTUP_MEGA_EVENT_SEGMENTS' not in start_src and
       '_event_remote_upper_ns' in replay_src and 'MEGA_EVENT_REPLAY_MARGIN_SEC' in replay_src and
       'checkpoint_ts' in replay_src and 'safe_cutoff_ns' in replay_src and
       'if upper is None' in replay_src and '_apply_r32_events(target, events)' in replay_src and
       'current_max' not in replay_src.split('needed: list[str]')[0],
       'startup may skip only segments provably older than the full-checkpoint timestamp; unknown names must replay')
    ok('r61_redis_render_owned_master_and_start',
       '_REDIS_START_ENABLED = _render_flag("REDIS_START_ENABLED", False)' in cfg_src and
       '_apply_redis_runtime_state(_REDIS_RENDER_ENABLED and _REDIS_START_ENABLED)' in cfg_src and
       'def redis_effective_url' in cfg_src and 'def redis_render_url' in cfg_src and
       'os.environ["REDIS_ENABLED"]' not in cfg_src and 'os.environ["REDIS_URL"]' not in cfg_src,
       'Redis master/start/URL must remain Render-owned; runtime menu may change only in-memory state')
    ok('r61_info_redis_explicit_modes_and_direct_inspector',
       "callback_data='r60:redis:menu'" in split_src and "callback_data='r60:redis:on'" in split_src and
       "callback_data='r60:redis:off'" in split_src and "callback_data='r60:redis:inspect:0'" in split_src and
       'def _r61_fetch_redis_inspect_direct' in split_src and "raw.startswith('r60:redis:')" in split_src and
       'STARTUP_REOPEN_WINDOWS' in rel_src,
       'Info must expose explicit Redis modes/direct inspector and deploy must not reopen windows by default')
    restore_seal_src=_fn_sources(split_src,{'r64_publish_restore_snapshot_v271'}).get('r64_publish_restore_snapshot_v271','')
    redis_sched_src=_fn_sources(split_src,{'r64_schedule_fast_redis_snapshot_v271'}).get('r64_schedule_fast_redis_snapshot_v271','')
    redis_fire_src=_fn_sources(split_src,{'_r64_periodic_redis_snapshot_fire_v271'}).get('_r64_periodic_redis_snapshot_fire_v271','')
    ok('och1222_manual_restore_single_sync_seal',
       '_split_cache_snapshot_to_redis_v266' in restore_seal_src and 'sync_mega=True' not in restore_seal_src and '_r222_schedule_post_restore_mega' in restore_seal_src and "'redis_ok'" in restore_seal_src,
       '12.22 manual restore may synchronously seal Redis once; MEGA must be delayed/memory-gated')
    ok('och123_redis_daily_full_scheduler',
       'def _r79_daily_snapshot_now' in split_src and 'def _r79_daily_scheduler_loop' in split_src and
       "redis_daily_snapshot_time_r79" in split_src and "callback_data='r79:redis:sched'" in split_src and
       "callback_data='r79:redis:now'" in split_src and "_split_cache_snapshot_to_redis_v266" in split_src and
       "daily_local_date" in split_src and "event_cutoff_score" in split_src,
       'FAST must create one configurable daily Redis FULL and expose time/manual FULL controls in Info')
    ok('r64_redis_snapshot_event_cutoff',
       "'event_cutoff_score': float(capture_started)" in split_src and
       'client.zrangebyscore' in start_src and 'events_tail=' in start_src,
       'startup must replay only Redis events newer than the exact full snapshot')
    ok('r59_info_env_views',
       'def render_env_snapshot' in cfg_src and "callback_data='r59:vars:render:0'" in split_src and
       "callback_data='r59:vars:code:0'" in split_src and "raw.startswith('r59:vars:')" in split_src,
       'Render ENV / code runtime Info views missing')
    ok('r59_redis_runtime_refresh',
       'def key_value_refresh_runtime_v248' in core_src and 'def _r59_fast_redis_probe' in split_src and
       'FAST: Redis CACHE ON; PING=PONG' in split_src and "HEAVY: Redis удалён" in split_src and
       "/internal/runtime/redis" not in _fn_sources(split_src,{'_r49_apply_redis_runtime_job'}).get('_r49_apply_redis_runtime_job',''),
       'FAST-only Redis runtime refresh / PING verification missing or HEAVY Redis call remains')
    ok('r49_fast_ui_latest_wins_queue',
       "WINDOW_RENDER_TASK_POOL = LatestKeyedTaskPool" in core_src and
       'WINDOW_RENDER_TASK_POOL.submit_latest' in rel_src and '_r22_execute_window_render' in rel_src,
       'callback renderer must enqueue into latest-wins window-render workers')
    ok('r49_state_events_runtime_owned_by_heavy',
       '_r34_post_events = _r38_post_events' in split_src and
       "requests.post(base+endpoint" in _fn_sources(split_src,{'_r38_post_events'}).get('_r38_post_events','') and
       '_r43_store_events_redis' not in _fn_sources(split_src,{'_r38_post_events'}).get('_r38_post_events',''),
       'active state-event sender must go to HEAVY, not FAST Redis/MEGA')
    ok('och128_no_legacy_runtime_safe_mode',
       'RECOVERY SAFE MODE' not in web_src and 'SPLIT_RECOVERY_SAFE_MODE' not in web_src and
       'SPLIT_RECOVERY_SAFE_MODE' not in split_src and 'SPLIT_RECOVERY_SAFE_MODE' not in start_src,
       'legacy runtime SPLIT_RECOVERY_SAFE_MODE flag must stay removed; 12.14 preboot recovery-safe wait is a separate startup policy')
    ok('och1220_normal_empty_boot',
       'def _ensure_empty_db' in start_src and
       "trace['base_source'] = 'EMPTY_INIT_AFTER_ONE_PASS'" in start_src and
       "trace['empty_init_attempted'] = True" in start_src and
       'OCHNIS_ALLOW_EMPTY_INIT' not in _fn_sources(start_src,{'main'}).get('main',''),
       '12.21 must create empty SQLite automatically after the one recovery pass')


    ok('r82_manual_restore_failed_tasks_nonfatal',
       'def _v153_failed_tasks_pending_store' in web_src and
       'def _v153_retry_pending_failed_tasks' in web_src and
       "timeout=(2.0,8.0)" in web_src and
       'return 0' in _fn_sources(web_src,{'_v153_restore_failed_tasks_from_db'}).get('_v153_restore_failed_tasks_from_db','') and
       "raise RuntimeError(f'HEAVY failed-task restore HTTP" not in _fn_sources(web_src,{'_v153_restore_failed_tasks_from_db'}).get('_v153_restore_failed_tasks_from_db',''),
       'failed-task artifacts must be durable-pending/nonfatal when R2 is unavailable')
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
        try: tree=_parse_src(src)
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

    # R65: priority navigation, non-blocking chat probe and manual all-MEGA recovery via HEAVY.
    ok('r65_priority_navigation_lane',
       "NAVIGATION_TASK_POOL = LatestKeyedTaskPool('nav-ui'" in core_src and
       "return (NAVIGATION_TASK_POOL, f'nav-window:{chat_id}:{message_id}')" in rel_src,
       'safe navigation must bypass ordinary callback work')
    ok('r65_navigation_epoch_stale_render_guard',
       'def _r65_render_is_stale_after_navigation' in web_src and
       "globals().get('_r65_render_is_stale_after_navigation')" in rel_src and
       'R65_NAV_STALE_RENDER_SKIP' in rel_src,
       'older renders must not overwrite newer navigation')
    ack_direct_src=_fn_sources(rel_src,{'_canon_schedule_callback_receipt_ack__001'}).get('_canon_schedule_callback_receipt_ack__001','')
    render_direct_src=_fn_sources(rel_src,{'_canon_fast_ui_edit_message_text__001'}).get('_canon_fast_ui_edit_message_text__001','')
    ok('r77_ack_isolated_pool_first',
       'def _r77_schedule_callback_receipt_ack' in split_src and
       "pool.submit_unique(f'callback-receipt-ack:{callback_id}'" in split_src and
       'schedule_callback_receipt_ack = _r77_schedule_callback_receipt_ack' in split_src,
       'callback ACK network I/O must be isolated in the dedicated ACK pool, never performed in the Waitress/callback hot path')
    ok('och111_navigation_latest_actor',
       "if selected_pool is globals().get('NAVIGATION_TASK_POOL')" in web_src and
       'selected_pool.submit_latest(selected_key, _process_callback' in web_src and
       "UPDATE_DISPATCHER.mark_enqueued(update_id, 'nav-ui-latest', selected_key)" in web_src and
       'OCH11_NAV_ENQUEUE' in web_src and 'R67_DIRECT_NAV_START' not in web_src,
       'Waitress must enqueue safe navigation to the latest-wins actor and return without executing the callback inline')
    ok('r67_direct_callback_render_no_window_pool',
       'if direct_callback:' in render_direct_src and '_r22_execute_window_render(payload)' in render_direct_src and
       render_direct_src.find('_r22_execute_window_render(payload)') < render_direct_src.find('WINDOW_RENDER_TASK_POOL.submit_latest'),
       'live callback render must go straight to Telegram; window-render actor is background fallback only')
    ok('r67_background_render_still_latest_wins',
       'WINDOW_RENDER_TASK_POOL.submit_latest' in render_direct_src,
       'background/scheduler renders must remain latest-wins so they cannot flood Telegram')
    ok('r67_direct_fast_telegram_gap',
       'return max(0.02, min(0.08, requested))' in core_src and
       str(env.get('FAST_TELEGRAM_CHAT_GAP','')) == '0.03',
       'direct callback Telegram gap must default around 30ms while retaining 429 cooldown')
    ok('r77_ack_pytelegrambotapi_compatible',
       "kwargs.pop('timeout', None)" in all_py.get('05_finance_ui.py','') and
       "kwargs.setdefault('timeout', 3)" not in all_py.get('05_finance_ui.py',''),
       'answer_callback_query must never receive the unsupported timeout kwarg')
    r70_safe_src=_fn_sources(rel_src,{'_canon_safe_edit__001'}).get('_canon_safe_edit__001','')
    r70_render_src=_fn_sources(rel_src,{'_r22_execute_window_render'}).get('_r22_execute_window_render','')
    r70_retry_src=_fn_sources(final_transport,{'_canon_v161_edit_retry__001'}).get('_canon_v161_edit_retry__001','')
    ok('r70_direct_returns_real_telegram_result',
       "direct_result = str(_r22_execute_window_render(payload) or 'failed')" in render_direct_src and "return 'direct'" not in render_direct_src and 'return direct_result' in render_direct_src,
       'Direct UI must return ok/not_found/rate_limited/failed, never a transport-mode token')
    ok('r70_renderer_never_creates_replacement',
       '_v177_safe_edit_fallback_send' not in r70_render_src and "return str(result or 'failed')" in r70_render_src,
       'window renderer must only report status; it cannot send a second Telegram window')
    ok('r70_safe_edit_single_replacement_owner',
       "if result == 'not_found':" in r70_safe_src and 'r70-safe-edit-replacement:' in r70_safe_src and "if result in {'ok', 'scheduled', 'stale_after_navigation', 'stale_generation'}:" in r70_safe_src,
       'safe_edit must replace exactly once and only after an unambiguous not_found/uneditable result')
    ok('r70_ambiguous_errors_retry_same_edit',
       "result in {'failed', 'rate_limited'}" in r70_retry_src and 'r70-ui-retry:' in r70_retry_src and '_v177_deferred_ui_retry' in r70_retry_src,
       'timeout/5xx/rate-limit style failures must retry the same edit, never manufacture a new window')
    ok('r70_e2e_front_callback_and_test_menu',
       "@app.route('/internal/r70/test/result',methods=['POST'])" in split_src and 'r44:test:r70e2e' in split_src and 'r44:test:forward' in split_src and 'def _r70_e2e_test' in split_src and 'def _r70_forward_dry_run' in split_src,
       'R70 test menu must verify HEAVY write/read/process/callback and forwarding effective routes')
    sqlite_backup_src=_fn_sources(core_src,{'backup_to'}).get('backup_to','')
    forward_status_src=_fn_sources(core_src,{'build_forward_status_text'}).get('build_forward_status_text','')
    ok('r70_sqlite_snapshot_singleflight',
       '_backup_coalesce_lock' in core_src and '_backup_cache_mono' in core_src and 'self._backup_cache_mono >= requested_mono' in sqlite_backup_src and "self._backup_stats['reused']" in sqlite_backup_src,
       'concurrent Redis/HEAVY/MEGA snapshot requests must share one physical SQLite backup')
    ok('r70_forward_ui_effective_state',
       "globals().get('resolve_forward_targets')" in forward_status_src and 'Runtime-маршруты:' in forward_status_src and 'resolve_forward_targets() сейчас не даёт маршрут' in forward_status_src,
       'forwarding UI must distinguish configured rules from effective production routes')
    ok('r70_r1_r2_owner_matrix',
       'def _r70_routes_text' in split_src and "callback_data='r70:routes'" in split_src and 'Telegram окна / кнопки' in split_src and 'R70 E2E' in split_src,
       'INFO/Render status must expose actual single-owner R1/R2 processor routing')
    ok('r80_expanded_failover_routes',
       "_R80_ROUTE_KEYS=('google','files','diagnostics','mega','durability','checkpoints')" in split_src and
       '🚨 R2 НЕТ → ВСЁ #1' in split_src and 'MEGA master Render #1' in split_src,
       'R1/R2 menu must expose emergency failover for durability and checkpoints, not only files/google')
    r80_full_src=_fn_sources(split_src,{'_r80_snapshot_full_compact'}).get('_r80_snapshot_full_compact','')
    r80_tail_src=_fn_sources(split_src,{'_r80_flush_compact_tail'}).get('_r80_flush_compact_tail','')
    ok('r80_compact_mega_fixed_nodes',
       'compact_v80' in split_src and 'latest.sqlite3.gz' in split_src and 'tail.json.gz' in split_src and 'head.json' in split_src and
       'mega-find' not in r80_full_src and 'mega-find' not in r80_tail_src and 'archive_previous=False' in split_src,
       'R1 MEGA must use fixed compact FULL+TAIL+HEAD objects and never tree-scan/per-event history')
    ok('r80_hotpath_no_remote_mega',
       '_r80_mark_tail_dirty(); return True' in split_src and "submit_unique('r80-mega-compact-full'" in split_src and
       "submit_unique('r80-mega-tail'" in split_src,
       'MEGA checkpoint/tail work must be queued in background, never inline with user UI')
    ok('r80_all_to_r1_stops_raw_witness_r2',
       '_R80_HEAVY_WITNESS_EVENT=split_witness_event_v268' in split_src and
       "if not _r71_route_is_fast('durability'):" in split_src and
       "st['r80_witness_owner']='R1_FAST_LOCAL_INBOX+REDIS_BG'" in split_src,
       'R1 durability failover must stop synchronous/raw witness dependence on dead R2')
    ok('r80_all_to_r1_stops_snapshot_r2',
       '_R80_HEAVY_PUSH_SNAPSHOT=_split_push_snapshot_now_v263' in split_src and
       "if not (_r71_route_is_fast('checkpoints') or _r71_route_is_fast('mega')):" in split_src and
       "_r80_snapshot_full_compact('sync-'" in split_src,
       'R1 checkpoints failover must not send exact snapshot to dead R2')
    ok('r80_all_to_r1_stops_legacy_delta_r2',
       '_R80_HEAVY_SEND_DELTA=_split_send_delta_v267' in split_src and
       "R1 compact FULL+TAIL owns delta durability" in split_src,
       'R1 failover must suppress legacy R2 delta traffic')
    # очнись_2: global Window Actor + markup-only transport contract.
    ok('och2_window_actor_registry',
       'class WindowActorRegistry' in core_src and 'WINDOW_ACTOR_REGISTRY = WindowActorRegistry' in core_src and 'logical_window_id' in core_src and 'state_revision' in core_src,
       'each visible Telegram window must have one RAM actor with generation/state revision')
    ok('och2_actor_generation_on_fast_render',
       "payload['_window_actor_generation']" in rel_src and "payload['_window_actor_state_revision']" in rel_src and 'actor.set_latest_payload' in rel_src and 'WINDOW_ACTOR_STALE_RENDER_DROP' in rel_src,
       'FAST render must reserve actor generation before direct/background Telegram work')
    ok('och2_global_markup_diff',
       'WINDOW_ACTOR_MARKUP_ONLY' in final_transport and '_FINAL_NATIVE_EDIT_MARKUP' in final_transport and "snap.get('delivered_text_fp') == text_fp" in final_transport and 'WINDOW_ACTOR_NOOP' in final_transport,
       'same text must use editMessageReplyMarkup only; identical window must make no Telegram call')
    ok('och2_stale_callback_revision_guard',
       'def _window_actor_decode_callback_v2' in web_src and 'WINDOW_ACTOR_STALE_CALLBACK' in web_src and "payload['_window_actor_callback_revision']" in web_src and "return ('OK', 200)" in web_src,
       'stale keyboard callback must be stripped/rejected before business routing')
    ok('och2_window_actor_serializes_one_message',
       'lock = actor.execution_lock(chat_id, message_id)' in all_py.get('05_finance_ui.py','') and 'with actor.execution_lock(cid, mid)' in final_transport,
       'direct/background renders of one Telegram message must serialize under one actor lock')
    ok('och111_async_logging_hotpath',
       '_FAST_LOG_QUEUE = queue.Queue' in core_src and '_fast_log_enqueue_v111' in core_src and "R52_FORENSIC_BUTTON_LOG', '0'" in core_src and 'logger.info(msg)' not in _fn_sources(core_src,{'_v177_legacy_0002_log_info'}).get('_v177_legacy_0002_log_info',''),
       'hot-path info logging must be non-blocking and verbose forensic stdout disabled by default')
    ok('och111_thread_local_sqlite_reads',
       'self._read_tls = threading.local()' in core_src and 'def _reader_v111' in core_src and 'return self._reader_v111().execute' in core_src,
       'SQLite reads must use independent thread-local WAL readers instead of one global read mutex')
    ok('och111_chat_store_fast_cache',
       '_CHAT_STORE_FAST_CACHE_V111' in core_src and "_CHAT_STORE_FAST_CACHE_V111.get(_key) is store_now" in core_src,
       'existing initialized chat stores must return without reacquiring global data_lock')
    ok('och111_no_cold_ledger_fault_on_currency_read',
       '_ensure_currency_ledgers(store)\n        return mode' not in all_py.get('05_finance_ui.py','') and 'reading window currency must not fault full cold ARS/USD histories' in all_py.get('05_finance_ui.py',''),
       'window registration/currency labels must not load cold finance histories')
    ok('och111_start_noop_secret_save',
       "if bool(settings.get('total_secret_mode', False)) == target:" in all_py.get('04_messages_features.py','') and 'save_data(data, chat_ids=[int(chat_id)])' in all_py.get('04_messages_features.py',''),
       '/start must not serialize the whole state merely to write false over false')
    r34_events_src=_fn_sources(split_src,{'_r34_post_events'}).get('_r34_post_events','')
    r43_cache_src=_fn_sources(split_src,{'_r43_store_events_redis'}).get('_r43_store_events_redis','')
    capsule_push_src=_fn_sources(split_src,{'_r20_capsule_push_now'}).get('_r20_capsule_push_now','')
    ok('och124_switchable_state_durability',
       "if not _r71_route_is_fast('durability')" in r34_events_src and '_R80_HEAVY_POST_EVENTS' in r34_events_src and
       '_r43_store_events_redis(events)' in r34_events_src and '_r80_mark_tail_dirty()' in r34_events_src and
       'R1 failover Redis TAIL pending' in r34_events_src and 'requests.post(' not in r34_events_src,
       'R1 emergency durability must avoid synchronous R2/network MEGA and keep Redis/local-outbox safety')
    ok('och123_redis_tail_compressed_bounded_pruned',
       "R79_REDIS_TAIL_TTL_SEC','259200'" in r43_cache_src and '_r32_gzip.compress' in r43_cache_src and
       "pipe.set(f'{prefix}:event:{eid}',packed,ex=ttl)" in r43_cache_src and 'pipe.zadd(index_key' in r43_cache_src and
       "client.zrangebyscore(index_key,'-inf',float(capture_started)" in split_src and "client.delete('per:r43:front:state_events')" in split_src,
       'Redis must keep compressed canonical event tail only and prune events already covered by the daily FULL')
    ok('och124_capsule_owner_failover',
       "if not _r71_route_is_fast('durability')" in capsule_push_src and '_R80_HEAVY_CAPSULE_PUSH' in capsule_push_src and
       '_r20_capsule_store_redis(payload,packed)' in capsule_push_src and '_r80_mark_tail_dirty()' in capsule_push_src,
       'capsule durability must follow the R1/R2 owner switch without putting R2/MEGA I/O on the user lane')
    ok('r72_single_foreground_window_mutation',
       'safe_edit(bot, call, build_info_text(cid), reply_markup=_r10_kb)\n    try:\n        bot.edit_message_reply_markup' not in final_transport and
       "_v215_edit_or_send(cid, mid, text, kb, 'contour_mode_toggle_v215')\n            try:\n                bot.edit_message_reply_markup" not in rel_src,
       'a callback must not perform safe/full edit and then a second markup edit of the same window')
    cb_src=all_py.get('06_commands_callbacks.py','')
    ok('r72_back_single_decision',
       cb_src.count("globals().get('r27_callback_is_back_navigation')") == 0 and
       final_transport.count("globals().get('r27_callback_is_back_navigation')") == 1 and
       'history_back_r72' in final_transport and 'Back/history was already decided by the final callback router' in cb_src,
       'Back navigation must be classified/restored exactly once before every feature router')
    fin_src=all_py.get('05_finance_ui.py','')
    peek_src=_fn_sources(fin_src,{'_nav_history_peek_v248'}).get('_nav_history_peek_v248','')
    ok('r72_back_no_sync_kv_hotpath',
       'kv_nav_peek_v248' not in peek_src and '_nav_history_prefetch_v248(key)' in peek_src,
       'Back hot path must be RAM-only; KV prefetch is background-only')
    ok('r72_canonical_markup_only_path',
       'def fast_ui_edit_reply_markup' in fin_src and
       count(r'_tg_call_retry\(bot\.edit_message_reply_markup', joined) == 1 and count(r'(?m)^bot\.edit_message_reply_markup\s*=', joined) == 1,
       'application markup-only edits must use fast_ui_edit_reply_markup; only helper + final binding may call bot.edit_message_reply_markup')
    ok('r72_constructor_single_send',
       "send_message(owner, 'Открываю Конструктор 1…')" not in final_transport and
       "send_message(cid, 'Открываю Конструктор 2…')" not in final_transport and
       'create the constructor panel already complete' in final_transport,
       'constructor open must not send placeholder and immediately edit it')
    ok('r72_single_semantic_routes',
       "if resolved == 'runtime_watcher':" in final_transport and
       "runtime_watcher is owned exclusively" in cb_src and
       "journal_open is owned exclusively" in cb_src and
       "globals().get('_v156_handle_process_toggle')" not in final_transport,
       'known overlapping callback families must have one current semantic owner')
    # OCH12.6 / R81: every command/message must be locally admitted before any remote witness.
    webhook_src=_fn_sources(web_src,{'telegram_webhook'}).get('telegram_webhook','')
    preboot_src=_fn_sources(web_src,{'_r54_replay_preboot_webhooks'}).get('_r54_replay_preboot_webhooks','')
    pre_restore_src=_fn_sources(web_src,{'_v153_backup_before_restore'}).get('_v153_backup_before_restore','')
    durable_req_src=_fn_sources(web_src,{'_canon_durable_task_required__001'}).get('_canon_durable_task_required__001','')
    manual_mega_src=_fn_sources(cmd_src,{'run_manual_mega_restore'}).get('run_manual_mega_restore','')
    compact_restore_src=_fn_sources(split_src,{'r81_manual_compact_mega_restore'}).get('r81_manual_compact_mega_restore','')
    ok('r81_remote_witness_background_only',
       'REMOTE_WITNESS_QUEUED' in webhook_src and 'REMOTE DURABLE WITNESS FAILED' not in webhook_src and "return ('REMOTE DURABLE WITNESS FAILED', 503)" not in webhook_src,
       'R2/Redis witness may never return 503 before a user message/command handler')
    ok('r81_preboot_local_takeover',
       'R81 PREBOOT LOCAL TAKEOVER' in preboot_src and "_v260_webhook_inbox_state(update_id)" in preboot_src,
       'preboot spool must stop 2-second replay loops once local SQLite inbox owns the update')
    ok('r81_all_known_slash_local_admission',
       "return (False, 'r81:slash_local_admission')" in durable_req_src and '_v150_is_known_slash_command(command)' in durable_req_src,
       'registered slash commands must not require R2/MEGA pre-execution durability')
    ok('r81_restore_prebackup_multi_backend',
       '_split_cache_snapshot_to_redis_v266' in pre_restore_src and '_r80_store_pre_restore_gz' in pre_restore_src and "timeout=(2.5, 20.0)" in pre_restore_src and 'timeout=240' not in pre_restore_src,
       'pre_restore must survive dead R2 via Redis/R1 MEGA and bound any R2 wait')
    ok('r81_manual_mega_restore_compact_only',
       'r81_manual_compact_mega_restore' in manual_mega_src and 'mega_restore_sqlite_snapshot_from_cloud' not in manual_mega_src and 'mega_restore_full_from_cloud' not in manual_mega_src and "_mega_run('mega-find'" not in compact_restore_src and '"mega-find"' not in compact_restore_src,
       'manual MEGA restore must use exact compact head/latest/tail with zero tree/history scan')
    ok('och12_display_name',
       "BOT_DISPLAY_NAME = 'очнись_12.22'" in core_src and '✅ {BOT_DISPLAY_NAME} запущен' in web_src,
       'user-visible bot and READY message must identify as очнись_12.22')
    startup_details_src=_fn_sources(web_src,{'_r57_startup_details_text'}).get('_r57_startup_details_text','')
    ok('och1211_startup_redis_authoritative_state',
       'import runtime_config as _r57_runtime_config' in startup_details_src and
       '_r57_runtime_config.redis_runtime_state()' in startup_details_src and
       "globals().get('redis_runtime_state'" not in startup_details_src,
       'startup details must read Redis status from authoritative runtime_config instead of module globals')
    mega_list_src=_fn_sources(split_src,{'_r71_local_mega_list'}).get('_r71_local_mega_list','')
    ok('och1212_r1_mega_browser_type_flags',
       "runner('mega-ls', ['-l', path]" in mega_list_src and
       "line.upper().startswith('FLAGS ')" in mega_list_src and
       "parts = line.split(None, 5)" in mega_list_src and
       "kind = 'dir' if str(flags).lower().startswith('d') else 'file'" in mega_list_src and
       "runner('mega-ls', [path]" not in mega_list_src and
       "raw_name).rstrip().endswith('/')" not in mega_list_src and
       'len(entries) >= 500' not in mega_list_src,
       'R1 MEGA browser must classify folders from authoritative mega-ls -l FLAGS, never by row alignment/plain-list slash heuristics')
    ok('och1210_r1_only_normal_default',
       "_R71_ROUTE_DEFAULTS = {k: 'fast' for k in _R71_ROUTE_KEYS}" in split_src and
       'och12_10_r1_normal_profile' in split_src and "och12.10-normal-r2-off" in split_src and
       "✅ R2 НЕТ · ВСЁ #1" in split_src,
       '12.10 must default/migrate all switchable heavy contours to R1 with R2 opt-in only')
    ok('och1213_total_traffic_control',
       'def _install_och1213_traffic_guard' in split_src and
       "R2_OFF_R1_ONLY" in split_src and
       'def traffic_render_refresh' in split_src and
       "https://api.render.com/v1/metrics/bandwidth" in split_src and
       "https://api.render.com/v1/metrics/bandwidth-sources" in split_src and
       'def traffic_container_net_snapshot' in split_src,
       '12.13 must hard-block stale R2 traffic and expose official Render + container traffic counters')
    ok('och1213_traffic_ui_controls',
       "traffic_audit:render" in cb_src and "traffic_audit:guard" in cb_src and
       "☁️ Render API" in cb_src and "🛡 Guard" in cb_src,
       'traffic window must expose Render refresh and Traffic Guard status')
    ok('och1214_journal_queue_batched_bounded',
       "JOURNAL_TASK_POOL = KeyedTaskPool('journal-file'" in core_src and
       'def _journal_file_drain_v214' in core_src and 'def _journal_enqueue_file_v214' in core_src and
       "JOURNAL_TASK_POOL.submit('journal-file'" not in core_src and
       "BACKGROUND_MAX_PENDING', 400" in core_src,
       '12.14 must batch local journal IO outside GENERAL background and bound background backlog')
    ok('och1214_forward_index_latest_wins',
       'PERSIST_LATEST_TASK_POOL = LatestKeyedTaskPool' in core_src and
       "submit_latest('v263-fwd-index-root-v214'" in split_src and
       "f'v263-fwd-index:{src[0]}:{src[1]}'" not in split_src,
       'forward-index self-heal persistence must be one latest root save, not hundreds of per-message tasks')
    ok('och1220_empty_after_one_pass',
       "OCH12.22_ONE_PASS_THEN_EMPTY" in start_src and
       "trace['base_source'] = 'EMPTY_INIT_AFTER_ONE_PASS'" in start_src and
       "_ensure_empty_db(target)" in start_main_src and
       'def _och1214_recovery_safe_wait' not in start_src and
       'while not _db_valid(target)' not in start_src,
       '12.21 must never loop forever when recovery sources are missing; one pass then empty SQLite')
    ok('och1217_startup_compact_only_no_legacy_tree_scan',
       'def _r80_compact_mega_compare_restore' in start_src and
       'def _discover_pre_restore_remotes' not in start_src and
       '/database/current_manifest.json' not in start_src and
       '/database/generations' not in start_src and
       '/database/pre_restore' not in start_src and
       '/database/latest_bot_state.sqlite3.gz' not in start_src and
       'MEGA_IMMUTABLE_OR_PRERESTORE' not in start_src and
       start_src.count('_restore_from_mega_startup(target)') == 0,
       'cold startup must use only fixed compact_v80 objects and never scan historical MEGA trees')
    ok('och1220_cold_compact_bounded_once',
       "MEGA_STARTUP_RECOVERY_LOGIN_TIMEOUT','20" in start_src and
       "MEGA_STARTUP_RECOVERY_GET_TIMEOUT','25" in start_src and
       "MEGA_STARTUP_COMPARE_LOGIN_TIMEOUT','12" in start_src,
       '12.21 cold MEGA recovery must be bounded because there is no retry loop')
    ok('och1215_compact_tail_not_hidden_by_stale_head',
       'on a cold restore always inspect tail.json.gz' in start_src and
       'claimed_tail_max=max(expected_tail_max,tail_obj_max)' in start_src and
       '_r32_legacy_descriptor' in start_src and '_redis_tail_events_after_cutoff' in start_src and
       'tail belongs to different FULL' in start_src,
       'cold compact restore must inspect durable tail even with missing/stale head and reject a mismatched FULL baseline')
    constitution_boot_src=_fn_sources(core_src,{'constitution_boot_verify_after_restore'}).get('constitution_boot_verify_after_restore','')
    ok('och1215_constitution_immutable_publish_is_synchronous',
       "globals().get('mega_publish_current_sqlite_v242')" in constitution_boot_src and
       'mega_upload_latest_database_backup(force=True)' not in constitution_boot_src and
       'first immutable generation created synchronously' in constitution_boot_src,
       'DATA CONSTITUTION genesis must synchronously create database/generations + current_manifest, not queue R80 compact')
    genesis_guard_src=_fn_sources(core_src,{'_v215_constitution_genesis_publish_allowed'}).get('_v215_constitution_genesis_publish_allowed','')
    ok('och1215_zero_revision_redis_cannot_anchor_genesis',
       'meta_revision=' in genesis_guard_src and "base.startswith('REDIS')" in genesis_guard_src and
       'zero-revision Redis restore cannot auto-create immutable genesis' in genesis_guard_src and
       'immutable genesis deferred' in constitution_boot_src,
       'a structurally replayable zero-revision Redis image must not silently become the first immutable MEGA generation')
    pre_restore_fast=_fn_sources(web_src,{'_v153_backup_before_restore'}).get('_v153_backup_before_restore','')
    ok('och1215_pre_restore_path_and_writer_unified',
       "globals().get('_r80_store_pre_restore_gz')" in pre_restore_fast and
       "'/database/pre_restore'" in split_src and
       "constitution_database_dir() + '/pre_restore'" in web_src,
       'R1 named pre_restore writer and FAST catalog must use database/pre_restore')
    ok('och1215_compact_tail_baseline_metadata',
       "'full_db_revision':db_rev" in split_src and
       "'full_event_revision':event_rev" in split_src and
       "'full_db_revision':float(_R80_MEGA_STATE.get('full_db_revision') or 0.0)" in split_src,
       'new compact tail files must identify the FULL baseline they belong to')
    ok('och1210_r2_network_hard_gate',
       "_split_os.environ['PEER_PING_ENABLED'] = '0' if all_fast else '1'" in split_src and
       'R2 disabled by normal R1-only profile' in split_src and
       'def _och1210_split_ping_once' in split_src and 'def _och1210_keepalive_peer_enabled' in split_src,
       'R1-only normal profile must make old peer loops zero-network')
    ok('och1210_memory_economy',
       '"MEMORY_SAFE_RESTART_ENABLED": "0"' in cfg_src and '"MEMORY_HEAVY_BLOCK_MB": "320"' in cfg_src and
       '"R80_MEGA_COMPACT_FLUSH_SEC": "180"' in cfg_src and 'def _och1210_mega_idle_reaper_loop' in split_src and
       "_r83_shutil.which('mega-quit')" in split_src,
       'memory guard must trim/block instead of self-restart and release idle MEGAcmd server')
    ok('och1216_sqlite_reader_ram_bound',
       'SQLITE_READER_CACHE_KB' in cfg_src and 'SQLITE_READER_MMAP_MB' in cfg_src and 'mmap_size={mmap_mb * 1024 * 1024}' in core_src,
       'SQLite readers must use bounded cache and configurable zero mmap')
    ok('och1220_lowram_targeted_evict',
       'max(180.0' in core_src and 'R24_LOWRAM_EVICT_RSS_MB' in cfg_src and '"210"' in cfg_src and
       'if rss >= R24_LOWRAM_EVICT_RSS_MB:' in core_src and
       'if rss >= R24_LOWRAM_EVICT_RSS_MB and not _lowram_business_busy()' not in core_src,
       '12.21 must evict a touched chat under pressure even when unrelated pools are busy')
    ok('och1220_boot_memory_trim',
       'def _och1220_release_boot_memory' in start_src and 'malloc_trim' in start_src and
       'redis_modules_unloaded' in start_src and 'OCH12.22 boot memory release' in start_src and
       'SPLIT_PREBOOT_EMPTY_INIT_R1220' in split_src,
       '12.21 must return recovery allocator memory before loading runtime and suppress empty boot publish')
    ok('och1216_watcher_ram_sources',
       'RAM — источники:' in core_src and 'sqlite_readers' in all_py.get('03_diagnostics_memory.py','') and 'process_rollup' in all_py.get('03_diagnostics_memory.py',''),
       'Watcher must expose RAM sources, SQLite readers and proc rollup')
    ok('r73_identity_normalization',
       'def _final_bot_identity_text' in final_transport and "re.sub(r'очнись_\\d+(?:\\.\\d+)?'" in final_transport and
       final_transport.count('_final_bot_identity_text(') >= 4,
       'all visible legacy bot names must normalize to BOT_DISPLAY_NAME before Telegram send/edit')
    ok('r73_factory_three_scopes_four_off',
       "_R73_FEATURES = ('constructors', 'descriptions', 'tz', 'markers')" in split_src and
       "_R73_FACTORY_DEFAULTS = {key: False for key in _R73_FEATURES}" in split_src and
       all(x in split_src for x in ["'owner': '👤 Основной владелец'", "'circle1': '1️⃣ Контур 1'", "'circle2': '2️⃣ Контур 2'"]),
       'factory profiles must be independent owner/circle1/circle2 with all four presentation features OFF by default')
    ok('r73_factory_info_controls',
       "callback_data='r73:factory:open'" in split_src and
       "callback_data=f'r73:factory:toggle:{skey}:{feature}'" in split_src and
       "callback_data=f'r73:factory:reset_do:{skey}'" in split_src and
       'Заводские настройки / интерфейс' in split_src,
       'Info must expose per-scope factory reset and each individual feature toggle')
    ok('r73_factory_final_render_gate',
       'def _r73_filter_features_markup' in split_src and
       '_r73_is_injected_constructor_button' in split_src and
       "cb == 'v171:desc'" in split_src and "cb == 'v160:tz_capture'" in split_src and "cb == 'v160:marker_capture'" in split_src and
       'def v227_render_effective_contour_markup' in split_src,
       'factory feature visibility must be enforced after legacy/profile/annotation augmentation')
    ok('r73_factory_reset_non_destructive',
       'Сброс не удаляет финансы, пересылки, напоминания, задачи, чаты или сохранённые файлы.' in split_src and
       "row[feature] = False" in split_src,
       'factory reset must only reset the four presentation switches, never business data')
    ok('r74_strict_module_marker_parity',
       "lines[0].strip() != expected_marker" in text('FINALIZATION_GATE.py') and "lines[-1].strip() != expected_marker" in text('FINALIZATION_GATE.py'),
       'package gate must use the same exact first/last marker contract as bot.py startup validation')
    ok('r74_info_live_map_index',
       "callback_data='r74:map:open'" in split_src and "callback_data='r74:map:download:map'" in split_src and
       "callback_data='r74:map:download:index'" in split_src and 'def _r74_build_machine_index' in split_src and
       'def _r74_build_master_map' in split_src,
       'Info must expose a live MASTER map and machine index generated from current runtime sources')
    ok('r74_map_index_async_delivery',
       "submit(f'r74-artifact-{cid}-{artifact}', _job)" in split_src and "_tg_call_retry(bot.send_document" in split_src,
       'map/index document generation and Telegram delivery must stay off the callback hot path')
    ok('r75_final_transport_hard_feature_fence',
       'def _r75_transport_feature_fence' in split_src and
       "fence = globals().get('_r75_transport_feature_fence')" in final_transport and
       "stage='edit_message_reply_markup'" in final_transport and
       "stage='edit_message_text'" in final_transport and
       "stage='send_message'" in final_transport,
       'all send/edit/markup-only Telegram mutations must cross the hard four-feature fence')
    ok('r75_actor_revision_callback_normalization',
       'def _r75_base_callback' in split_src and 'window_actor_strip_callback_token' in split_src and
       'resolve_short_callback' in split_src and 'cb = _r75_base_callback(_r73_cb(button))' in split_src,
       'feature filtering must recognize callbacks even after Window Actor ~w revision stamping or short-callback indirection')
    ok('r75_augment_and_semantic_double_fence',
       "return _r73_filter_features_markup(result, int(chat_id))" in split_src and
       'def _r75_contour_callback_guard' in split_src and
       'r75_disabled_feature_callback_blocked' in split_src,
       'disabled presentation features must be filtered after augmentation and blocked before semantic routing')
    ok('r75_beetle_feature_leak_forensics',
       'r75_feature_leak_blocked' in split_src and 'producer' in split_src and 'by_stage' in split_src and
       'feature_visibility_fence_r75' in diag_src and "callback_data='r75:beetle:open'" in split_src and
       'def _r75_beetle_text' in split_src,
       'expanded bug-trap diagnostics must record producer/stage/scope/feature, expose counters in max diagnostics and be visible from Info')
    ok('r76_back_main_bypasses_history',
       "if raw == '__main__':\n        return False" in split_src and "if raw == '__previous__':\n        return True" in split_src,
       'Back/Main must reach its main-window semantic owner; only Previous uses history')
    ok('r76_final_semantic_button_dedupe',
       'def _r76_semantic_dedupe_markup' in split_src and "return ('cb', base)" in split_src and
       'prepared=_r76_semantic_dedupe_markup' in split_src,
       'final transport must collapse duplicate semantic actions after Window Actor token normalization')
    ok('r76_single_markup_build_no_final_reaugment',
       "def _final_prepare_markup(chat_id, reply_markup, text='', stage='prepare', message_id=None):" in split_src and
       "return _final_filter_markup(int(chat_id or 0), reply_markup, stage=stage, message_id=message_id)" in split_src,
       'FAST UI augmentation must happen once; final transport must not re-augment or pay the old caught TypeError path')
    ok('r76_scoped_latest_wins_factory_refresh',
       "def _r73_schedule_live_refresh(reason='settings', scope=None, feature=None, exclude=None)" in split_src and
       "DELAYED_SCHEDULER.schedule(key, 0.45, _job)" in split_src and "if excluded and (cid,mid)==excluded" in split_src,
       'factory toggles must refresh only affected scope after idle and never repaint the foreground window twice')
    ok('r76_fast_ui_no_verbose_journal_lock',
       "verbose_telegram_journal_enabled() and (not _is_fast_ui_purpose(purpose))" in core_src,
       'fast UI Telegram calls must not pay verbose journal/data-lock cost')
    ok('r76_beetle_latency_profiler',
       'def r76_ui_profile_snapshot' in split_src and 'R76 ПРОФИЛЬ ОТРИСОВКИ' in split_src and 'transport_recent' in split_src and 'callback_recent' in split_src,
       'beetle must expose callback total, transport time, filter time, dedupe and refresh counters')
    ok('r77_callback_service_lanes_split',
       "CALLBACK_DURABLE_TASK_POOL = KeyedTaskPool('callback-durable'" in core_src and
       "CALLBACK_JOURNAL_TASK_POOL = KeyedTaskPool('callback-journal'" in core_src and
       "globals().get('CALLBACK_DURABLE_TASK_POOL')" in web_src and
       "globals().get('CALLBACK_JOURNAL_TASK_POOL')" in web_src,
       'callback durable bookkeeping and diagnostic journal work must not share the old single-worker ui-cleanup lane')
    ok('r77_finance_one_foreground_commit_repaint',
       "globals().get('schedule_finance_reconcile_r77')" in all_py.get('04_messages_features.py','') and
       "reason='record_add'" in all_py.get('04_messages_features.py','') and
       'def schedule_finance_reconcile_r77' in split_src and
       'This path intentionally performs no Telegram repaint' in split_src,
       'new finance input must commit/repaint once; full normalize/persist is coalesced behind the user-visible path without a second repaint')
    ok('r77_forward_add_skips_duplicate_persist',
       'added_by_hotpath = isinstance(result_rec, dict)' in all_py.get('04_messages_features.py','') and
       "if (not added_by_hotpath) and 'persist_finance_chat_local_fast'" in all_py.get('04_messages_features.py','') and
       "reason='forward_finance'" in all_py.get('04_messages_features.py',''),
       'new forwarded finance rows must not immediately persist the same destination chat twice')
    ok('r77_finance_maintenance_isolated_latest_wins',
       "FINANCE_MAINT_TASK_POOL = KeyedTaskPool('finance-maint'" in core_src and
       "DELAYED_SCHEDULER.cancel(key)" in split_src and
       "pool.submit_unique(f'finance-maint:{cid}'" in split_src and
       'Never inline a full-ledger normalize into the user' in split_src,
       'full-ledger reconcile must be latest-wins background work on its own pool')
    ok('r77_fin_forward_parallel_default',
       "FIN_FORWARD_WORKERS', 3, 1, 8" in core_src,
       'financial forwarding destinations should run in parallel by default instead of a single global worker')
    ok('r77_beetle_fin_queue_profiler',
       'def r77_pipeline_snapshot' in split_src and 'R77 FIN / QUEUE PIPELINE' in split_src and
       "'callback_durable': _stats('CALLBACK_DURABLE_TASK_POOL')" in split_src and
       "'finance_maint': _stats('FINANCE_MAINT_TASK_POOL')" in split_src,
       'beetle must expose FIN reconcile plus ACK/durable/journal/forward queue pressure')
    ok('r78_status_edit_finalization_only',
       '_R77_PREV_R40_STATUS_EDIT' not in split_src and
       count(r'(?m)^def _r40_status_edit\(', split_src) == 1 and
       count(r'(?m)^def _r77_r40_status_edit_core\(', split_src) == 1 and
       'return _r77_r40_status_edit_core(chat_id,msg_id,text,purpose)' in split_src,
       'R77 HEAVY progress defer must use one canonical core + one public owner, never PREV/ORIG/BASE capture')
    if _require_info:
        rules_src=text('INFO/PROJECT_RULES.md')
        history_src=text('INFO/CHANGELOG.md')
        map_src=text('INFO/BOT_MAP.md')
        handoff_src=text('INFO/NEXT_CHAT_HANDOFF.md')
        ok('r69_info_version_increment_rule',
           'каждая следующая версия' in rules_src.lower() and '+1' in rules_src,
           'project rules must preserve the user version +1 rule')
        ok('r69_info_history_present',
           'R69' in history_src and 'R68' in history_src and 'R67' in history_src,
           'CHANGELOG must preserve previous and current release history')
        ok('r69_info_bot_map_for_fast_edits',
           'БЫСТРАЯ КАРТА ПРАВОК' in map_src and '01_core_data.py' in map_src and '10_split_policy_offload.py' in map_src,
           'BOT_MAP must tell the next chat where to edit common subsystems')
        ok('r69_info_next_chat_handoff',
           'PATCH → FINALIZE → TEST → PACKAGE' in handoff_src and 'R69' in handoff_src and 'R70' in handoff_src,
           'next-chat handoff must explain current base and next version')
    probe_src=_fn_sources(core_src,{'probe_all_known_chats'}).get('probe_all_known_chats','')
    ok('r65_parallel_chat_probe_idle_targeted_persist',
       'ThreadPoolExecutor' in probe_src and '_r65_schedule_chat_probe_persist' in probe_src and
       'save_data(data)' not in probe_src and 'save_data(data, chat_ids=' not in probe_src and
       'def _r65_chat_probe_persist_when_idle' in core_src and 'save_data(data, chat_ids=ids)' in core_src,
       'chat probe network phase must not persist while user interaction is active')
    ok('r65_all_mega_manual_recovery_via_heavy',
       '/internal/r65/mega/list' in final_transport and '/internal/r65/mega/file' in final_transport and
       'def _v265_heavy_download_mega_file' in final_transport and
       "globals().get('r64_publish_restore_snapshot_v271')" in web_src,
       'manual MEGA browser/restore must use HEAVY and seal selected restore into HEAVY/MEGA')


    # R66: every Telegram main window is independent; opening/navigating one
    # window must never retire or redirect another window.
    cmd_src=all_py.get('06_commands_callbacks.py','')
    set_active_src=_fn_sources(cmd_src,{'set_active_window_id'}).get('set_active_window_id','')
    on_callback_src=_fn_sources(cmd_src,{'on_callback'}).get('on_callback','')
    recreate_src=_fn_sources(cmd_src,{'recreate_main_window_now'}).get('recreate_main_window_now','')
    ok('r66_parallel_main_windows_no_auto_retire',
       "'parallel_allowed': True" in set_active_src and
       'stale_ids' not in set_active_src and 'aw.clear()' not in set_active_src and
       'delete_message' not in set_active_src and '_v189_delete_stale_main_message' not in cmd_src,
       'registering a main window must preserve all existing Telegram windows')
    ok('r66_no_stale_main_callback_redirect',
       '_v189_redirect_stale_finance_window' not in final_transport and
       'stale_main_redirect_v189' not in final_transport,
       'old main-window callbacks must execute normally instead of being deleted/redirected')
    ok('r66_window_local_day_navigation',
       "base_day_key = str(day_key)[:10]" in on_callback_src and
       "day_key = str(day_key)[:10]" in on_callback_src and
       "day_key = str(fn(chat_id))[:10]" not in on_callback_src,
       'prev/next/back actions must use the date encoded in the clicked window')
    ok('r66_recreate_preserves_existing_window',
       'force_new_day_window' in recreate_src and 'delete_message' not in recreate_src and
       'clear_active_window_id' not in recreate_src,
       'creating another main window must not delete the previous one')
    back_main_src=_fn_sources(rel_src,{'_canon_return_to_main_window_closing_previous__001'}).get('_canon_return_to_main_window_closing_previous__001','')
    ok('r66_no_back_main_sibling_delete',
       'back_main_delete_old' not in cmd_src and 'back-delete:' not in cmd_src and
       'close_previous_main_window_before_back' not in cmd_src and
       'delete_message' not in back_main_src,
       'Back/Main must edit only the clicked message and preserve sibling windows')

    # OCH12.9 / v263: finance-forward edit identity must survive deploy/restart.
    v263_src=all_py.get('10_split_policy_offload.py','')
    ok('v263_forward_map_cache_not_authority',
       'SQLite op-ledger+origin=authority' in v263_src and "kind='forward_finance_ops_v260'" in v263_src,
       'finance forwarding identity must recover from durable SQLite witnesses')
    ok('v263_replayed_message_reclassified_as_edit',
       'finance_message_reclassified_as_edit_v263' in v263_src and 'schedule_propagate_edited_to_copies(msg)' in v263_src,
       'same Telegram message_id after deploy must become linked edit, not a new finance operation')
    ok('v263_existing_copy_reconciled_not_resent',
       'forward_existing_copy_reconciled_v263' in v263_src and '_och129_reconcile_existing_forward_copy' in v263_src and
       'sync_edited_copy_to_target' in v263_src,
       'known old destination copy must be edited/reconciled instead of duplicated')
    recover_src=_fn_sources(v263_src,{'_och129_recover_forward_links_local'}).get('_och129_recover_forward_links_local','')
    ok('v263_identity_repair_local_only_hotpath',
       'requests.' not in recover_src and 'bot.' not in recover_src and 'mega_' not in recover_src.lower(),
       'identity repair before forwarding must be local SQLite/RAM only; no R2/MEGA/network in user hot path')
    ok('v263_all_edit_modes_share_resolver',
       count(r'(?m)^def get_forward_links\(',v263_src)>=1 and '_v262_linked_locations' in v263_src and
       'edit_forward_copy_and_record' in v263_src and 'handle_finance_edit' in v263_src,
       'native/button/slash/linked edit paths must converge on durable get_forward_links resolver')

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

    ok('och1221_global_restore_keeps_cold_ledgers',
       '_v221_restore_chat_cold_safe' in core_src and 'global_cold_safe' in core_src and "records_loaded = bool(dict.__contains__(store, 'records'))" in core_src,
       '12.21 global restore must not materialize every chat records/daily_records')
    ok('och1221_window_actor_delivered_revision',
       'delivered_state_revision' in core_src and "current = int(row.get('delivered_state_revision') or 0)" in core_src,
       '12.21 stale callback fence must follow Telegram-confirmed keyboard revision')
    ok('och1221_watcher_telegram_safe',
       'max_chars = 3300' in core_src and 'Watcher сокращён для Telegram' in core_src,
       '12.21 Watcher text must stay below Telegram edit_message_text limit')
    ok('och1221_manual_recovery_ignores_runtime_off',
       '_r221_manual_mega_ready' in split_src and '_r221_manual_redis_restore_sqlite' in split_src and "callback_data='r60:redis:restore'" in split_src,
       '12.21 owner manual MEGA/Redis recovery must work with runtime switches OFF')
    ok('och1221_redis_client_lazy_import',
       '_split_get_redis' in split_src and 'import redis as _split_redis' not in split_src,
       '12.21 FAST must not eagerly import Redis client while runtime Redis is OFF')


    _redis_loader_src=_fn_sources(split_src,{'_split_get_redis'}).get('_split_get_redis','')
    ok('och1222_redis_lazy_no_recursion',
       'if _split_redis is not None:' in _redis_loader_src and 'if _split_get_redis() is not None:' not in _redis_loader_src,
       '12.22 Redis lazy loader must never recursively call itself')
    _reanchor_src=_fn_sources(web_src,{'_canon_v240_restore_reanchor_guaranteed__002'}).get('_canon_v240_restore_reanchor_guaranteed__002','')
    ok('och1222_no_sync_mega_in_constitution_reanchor',
       'sync_mega=True' not in _reanchor_src and '_split_push_snapshot_now_v263' not in _reanchor_src,
       '12.22 local constitution acceptance may not publish MEGA in the restore callback')
    ok('och1222_restore_quiet_remote_io',
       'restore_quiet_active_v222' in core_src and "'_V222_RESTORE_QUIET_UNTIL'" in web_src and
       "return False, 'restore quiet/cooldown'" in split_src,
       '12.22 restore must pause nonessential remote work through cooldown')
    ok('och1222_restore_redis_first_prebackup',
       "if (not redis_ok) and route_fast and callable(compact_fn):" in web_src and
       "if (not redis_ok) and (not route_fast):" in web_src,
       '12.22 pre-restore must not write MEGA/R2 when Redis safety anchor already succeeded')
    _healthy_src=_fn_sources(web_src,{'_v243_mark_runtime_restore_healthy'}).get('_v243_mark_runtime_restore_healthy','')
    ok('och1222_no_fast_google_sync_on_restore',
       'google_recovery_sync_deferred_v222' in _healthy_src and 'google-resume-after-recovery-v244' not in _healthy_src,
       '12.22 restore must not auto-build Google exports during the memory peak')
    ok('och1222_post_restore_mega_deferred',
       '_r222_post_restore_mega_checkpoint' in split_src and "memory_heavy_allowed" in split_src and
       '_r222_release_mega_after_restore' in split_src,
       '12.22 MEGA checkpoint must be delayed, memory-gated and release MEGAcmd afterward')

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
