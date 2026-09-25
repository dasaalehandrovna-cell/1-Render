# v266
from pathlib import Path
import ast, hashlib, inspect, json, os, re
from runtime_config import install_internal_runtime_config
install_internal_runtime_config("front")
MODULAR_VERSION = "vys_266"
MODULE_FILE_VERSION = "v266"
MODULAR_SOURCE_PARTS = ['01_core_data.py', '02_transport_safety.py', '03_diagnostics_memory.py', '04_messages_features.py', '05_finance_ui.py', '06_commands_callbacks.py', '07_state_web.py', '08_reliability_tasks.py', '09_final_transport.py', '10_split_policy_offload.py']
OWNER_PARTS = ['11_business_finance.py', '12_business_finance_forward.py', '13_business_tasks.py', '14_business_reminders.py', '15_integration_google.py', '16_integration_excel.py', '17_integration_mega.py', '18_business_secret.py', '19_compat_legacy.py']
MODULAR_PACKAGE_PARTS = MODULAR_SOURCE_PARTS + OWNER_PARTS
_MODULAR_ROOT = Path(__file__).resolve().parent
_MANIFEST_PATH = _MODULAR_ROOT / "modules_manifest.json"
_OWNER_MANIFEST_PATH = _MODULAR_ROOT / "owners_manifest.json"
_OWNER_INDEX = {}
_OWNER_SOURCE_CACHE = {}
_OWNER_RUNTIME_INSTALLS = {}
_MODULAR_MERGED_CACHE = None

def _sha256_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()

def _validate_modular_package() -> None:
    manifest=json.loads(_MANIFEST_PATH.read_text(encoding='utf-8'))
    if str(manifest.get('version') or '') != MODULAR_VERSION: raise RuntimeError('modular version mismatch')
    files=manifest.get('files') or {}; markers=manifest.get('file_markers') or {}; problems=[]
    for rel in MODULAR_PACKAGE_PARTS:
        path=_MODULAR_ROOT/rel
        if not path.exists(): problems.append(f'missing {rel}'); continue
        raw=path.read_bytes()
        if _sha256_bytes(raw) != str(files.get(rel) or ''): problems.append(f'hash {rel}')
        rows=raw.decode('utf-8').splitlines(); expected='# '+str(markers.get(rel) or MODULE_FILE_VERSION)
        if not rows or rows[0].strip()!=expected or rows[-1].strip()!=expected: problems.append(f'marker {rel}')
    if set(files)!=set(MODULAR_PACKAGE_PARTS): problems.append('manifest parts mismatch')
    if problems: raise RuntimeError('MODULAR PACKAGE CHECK FAILED: '+'; '.join(problems[:16]))

def _load_owner_index() -> None:
    manifest=json.loads(_OWNER_MANIFEST_PATH.read_text(encoding='utf-8'))
    if str(manifest.get('release') or '') != 'очнись_12.35': raise RuntimeError('owner manifest release mismatch')
    for owner,row in (manifest.get('owners') or {}).items():
        rel=str((row or {}).get('file') or '')
        if rel not in OWNER_PARTS: raise RuntimeError(f'bad owner file {owner}:{rel}')
        for stage_id,stage in ((row or {}).get('stages') or {}).items():
            _OWNER_INDEX[(str(owner),str(stage_id))]={**dict(stage),'owner_file':rel}
        _OWNER_RUNTIME_INSTALLS[str(owner)]=0

def _owner_file_function_sources(rel: str):
    cached=_OWNER_SOURCE_CACHE.get(rel)
    if cached is not None: return cached
    text=(_MODULAR_ROOT/rel).read_text(encoding='utf-8'); lines=text.splitlines(True); tree=ast.parse(text,filename=rel)
    cached={n.name: ''.join(lines[n.lineno-1:n.end_lineno]) for n in tree.body if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef))}
    _OWNER_SOURCE_CACHE[rel]=cached
    return cached

def _owner_stage_source(owner: str, stage_id: str) -> str:
    row=_OWNER_INDEX.get((str(owner),str(stage_id)))
    if not row: raise RuntimeError(f'unknown owner stage {owner}:{stage_id}')
    rel=str(row['owner_file']); template=str(row['template']); public=str(row['public'])
    src=_owner_file_function_sources(rel).get(template)
    if src is None: raise RuntimeError(f'missing owner source {owner}:{stage_id}:{template}')
    if template!=public:
        src,n=re.subn(r'(?m)^(\s*(?:async\s+)?def\s+)'+re.escape(template)+r'\b',lambda m:m.group(1)+public,src,count=1)
        if n!=1: raise RuntimeError(f'cannot restore public name {owner}:{stage_id}')
    return src.rstrip()+"\n"

def _owner_install(owner: str, stage_id: str):
    """Execute one physical owner body at the exact historical runtime point.

    Owner files are source catalogs, not imported modules. This avoids a second live copy of
    business/integration functions, avoids sys.modules churn and evaluates defaults/annotations
    against the same globals that existed in the original monolith at this point.
    """
    src=_owner_stage_source(owner,stage_id)
    row=_OWNER_INDEX[(str(owner),str(stage_id))]
    exec(compile(src,str(_MODULAR_ROOT/str(row['owner_file'])),'exec'),globals(),globals())
    public=str(row['public']); fn=globals().get(public)
    if not callable(fn): raise RuntimeError(f'owner install did not define {public}')
    _OWNER_RUNTIME_INSTALLS[str(owner)]=int(_OWNER_RUNTIME_INSTALLS.get(str(owner),0) or 0)+1
    return fn

def _exec_source_part(relative_path: str) -> None:
    path=_MODULAR_ROOT/relative_path
    exec(compile(path.read_text(encoding='utf-8'),str(path),'exec'),globals(),globals())

def _owner_stage_gate_v266() -> None:
    manifest=json.loads(_OWNER_MANIFEST_PATH.read_text(encoding='utf-8')); problems=[]; owned=set()
    for owner,row in (manifest.get('owners') or {}).items():
        expected=int((row or {}).get('stage_occurrences') or 0); actual=int(_OWNER_RUNTIME_INSTALLS.get(owner,0) or 0)
        if actual!=expected: problems.append(f'{owner} stages {actual}!={expected}')
        owned.update((row or {}).get('symbols') or [])
    for rel in MODULAR_SOURCE_PARTS:
        tree=ast.parse((_MODULAR_ROOT/rel).read_text(encoding='utf-8'),filename=rel)
        bad=[n.name for n in tree.body if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)) and not n.decorator_list and n.name in owned]
        if bad: problems.append(f'{rel} duplicate owner bodies={bad[:8]}')
    if problems: raise RuntimeError('OCH12.35 OWNER GATE FAILED: '+'; '.join(problems[:16]))

def _runtime_contract_gate_v266() -> None:
    contracts={
      'probe_bot_in_chat':({'chat_id','deep','persist','schedule_backup','_migration_retry'},'01_core_data.py'),
      'update_chat_info_from_chat_object':({'chat_obj','persist','schedule_backup'},'07_state_web.py'),
      'set_chat_bot_removed':({'chat_id','removed','reason','persist','schedule_backup'},'07_state_web.py'),
      'set_chat_status_v150':({'chat_id','status','reason','source','migrated_to','force_history','persist','schedule_backup'},'07_state_web.py'),
      'collect_probe_chat_ids_v200':({'include_owner'},'01_core_data.py'),
      'migrate_chat_id_everywhere':({'old_chat_id','new_chat_id','reason'},'07_state_web.py'),
      'resolve_forward_targets':({'source_chat_id'},'12_business_finance_forward.py'),
      'send_and_auto_delete':({'chat_id','text','delay'},'08_reliability_tasks.py'),
      'send_html_and_auto_delete':({'chat_id','html_text','delay'},'08_reliability_tasks.py'),
      'submit_interactive_file_job':({'chat_id','kind','label','func'},'10_split_policy_offload.py'),
    }
    problems=[]
    for name,(required,owner_file) in contracts.items():
        fn=globals().get(name)
        if not callable(fn): problems.append(f'missing {name}'); continue
        try:
            sig=inspect.signature(fn); accepted=set(sig.parameters); has_kwargs=any(p.kind==inspect.Parameter.VAR_KEYWORD for p in sig.parameters.values())
            missing=sorted(required-accepted) if not has_kwargs else []
            if missing: problems.append(f'signature {name} missing={missing} actual={sig}')
        except Exception as exc: problems.append(f'signature {name}: {exc}')
        filename=str(getattr(getattr(fn,'__code__',None),'co_filename','') or '')
        if owner_file and not filename.endswith(owner_file): problems.append(f'owner {name}={filename or "?"} expected={owner_file}')
    if problems: raise RuntimeError('RUNTIME CONTRACT GATE v266 FAILED: '+'; '.join(problems[:16]))

def _domain_owner_gate_v266() -> None:
    owners={
      'handle_finance_message':'11_business_finance.py',
      'handle_finance_edit':'11_business_finance.py',
      'get_forward_links':'12_business_finance_forward.py',
      'resolve_forward_targets':'12_business_finance_forward.py',
      '_v229_command_tasks':'13_business_tasks.py',
      'task_dispatcher_callback_final':'13_business_tasks.py',
      '_reminder_send_cycle':'14_business_reminders.py',
      'build_reminder_menu_text':'14_business_reminders.py',
      'tenant_google_config':'15_integration_google.py',
      '_google_request_guarded':'15_integration_google.py',
      'write_simple_xlsx':'16_integration_excel.py',
      '_mega_run':'17_integration_mega.py',
      'handle_secret_note_message':'18_business_secret.py',
      'begin_secret_full_edit':'18_business_secret.py',
    }
    problems=[]
    for name,owner in owners.items():
        fn=globals().get(name)
        if not callable(fn): problems.append(f'missing {name}'); continue
        filename=str(getattr(getattr(fn,'__code__',None),'co_filename','') or '')
        if not filename.endswith(owner): problems.append(f'owner {name}={filename or "?"} expected={owner}')
    if problems: raise RuntimeError('OCH12.35 DOMAIN OWNER GATE FAILED: '+'; '.join(problems[:16]))

def _strip_part_version(text: str) -> str:
    rows=text.splitlines()
    if rows and rows[0].strip().startswith('# v'): rows=rows[1:]
    if rows and rows[-1].strip().startswith('# v'): rows=rows[:-1]
    return '\n'.join(rows).rstrip()+'\n'

def _modular_merged_source_path() -> str:
    global _MODULAR_MERGED_CACHE
    tmp_dir=os.getenv('MEGA_LOCAL_TMP_DIR','/tmp').strip() or '/tmp'; os.makedirs(tmp_dir,exist_ok=True)
    target=os.path.join(tmp_dir,f'{MODULAR_VERSION}_full.py')
    call_re=re.compile(r"^\s*_owner_install\((['\"])([^'\"]+)\1,\s*(['\"])([^'\"]+)\3\)\s*$")
    chunks=[]
    for rel in MODULAR_SOURCE_PARTS:
        out=[]
        for line in _strip_part_version((_MODULAR_ROOT/rel).read_text(encoding='utf-8')).splitlines(True):
            m=call_re.match(line.strip())
            if m: out.append(_owner_stage_source(m.group(2),m.group(4)))
            elif line.lstrip().startswith('# [OCH12.35 OWNER]'): continue
            else: out.append(line)
        chunks.append(''.join(out).rstrip()+'\n')
    with open(target,'w',encoding='utf-8') as fh:
        fh.write(f'# {MODULE_FILE_VERSION}\n'); fh.write('\n'.join(chunks).rstrip()+'\n'); fh.write('if __name__ == "__main__":\n    main()\n'); fh.write(f'# {MODULE_FILE_VERSION}\n')
    _MODULAR_MERGED_CACHE=target; return target

_validate_modular_package()
_load_owner_index()
for _part in MODULAR_SOURCE_PARTS: _exec_source_part(_part)
_owner_stage_gate_v266()
_runtime_contract_gate_v266()
_domain_owner_gate_v266()
# Source cache is useful only for merged-source download after startup; keep it lazy and empty now.
_OWNER_SOURCE_CACHE.clear()
if __name__ == '__main__' and str(os.getenv('BOT_DEFER_MAIN_R54','0') or '0').strip().casefold() not in {'1','true','yes','on'}: main()
# v266
