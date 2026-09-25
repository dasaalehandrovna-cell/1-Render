#!/usr/bin/env python3
from pathlib import Path
import ast, hashlib, json, os, py_compile, re, subprocess, sys, tempfile
ROOT=Path(__file__).resolve().parent
SOURCE_PARTS=['01_core_data.py','02_transport_safety.py','03_diagnostics_memory.py','04_messages_features.py','05_finance_ui.py','06_commands_callbacks.py','07_state_web.py','08_reliability_tasks.py','09_final_transport.py','10_split_policy_offload.py']
OWNER_PARTS=['11_business_finance.py','12_business_finance_forward.py','13_business_tasks.py','14_business_reminders.py','15_integration_google.py','16_integration_excel.py','17_integration_mega.py','18_business_secret.py','19_compat_legacy.py']
RUNTIME_BUILD=str(os.getenv('FINALIZATION_RUNTIME_BUILD','0')).strip().lower() in {'1','true','yes','on'}
APP_RUNTIME_FILES={'requirements.txt','bot.py','start_front.py','runtime_config.py','modules_manifest.json','owners_manifest.json','FINALIZATION_GATE.py',*SOURCE_PARTS,*OWNER_PARTS}
SOURCE_CONTROL_FILES={'Dockerfile','.dockerignore'}
RUNTIME_FILES=APP_RUNTIME_FILES if RUNTIME_BUILD else (APP_RUNTIME_FILES|SOURCE_CONTROL_FILES)
checks=[]
def ok(name,cond,detail=''):
    checks.append((name,bool(cond),detail));
    if not cond: print('FAIL',name,detail)
def text(name): return (ROOT/name).read_text('utf8') if (ROOT/name).is_file() else ''

# Presence + compile.
ok('runtime_files_present',all((ROOT/x).is_file() for x in RUNTIME_FILES))
for rel in ['bot.py','start_front.py','runtime_config.py',*SOURCE_PARTS,*OWNER_PARTS]:
    try: ast.parse(text(rel),filename=rel); good=True
    except Exception as e: good=False; detail=str(e)
    ok('ast_'+rel,good,'' if good else detail)

manifest=json.loads(text('owners_manifest.json') or '{}')
mods=json.loads(text('modules_manifest.json') or '{}')
ok('release',manifest.get('release')=='очнись_12.36')
ok('architecture',manifest.get('architecture')=='physical_domain_owner_v2')
ok('primary_owners',list((manifest.get('owners') or {}).keys())[:8]==['finance','finance_forward','tasks','reminders','google','excel','mega','secret'] and 'compat_legacy' in (manifest.get('owners') or {}))
ok('module_version',mods.get('version')=='vys_267')
# Hash/marker package integrity.
problems=[]
for rel in SOURCE_PARTS+OWNER_PARTS:
    p=ROOT/rel; raw=p.read_bytes() if p.exists() else b''
    if hashlib.sha256(raw).hexdigest()!=str((mods.get('files') or {}).get(rel) or ''): problems.append('hash:'+rel)
    rows=raw.decode('utf8',errors='replace').splitlines(); exp='# '+str((mods.get('file_markers') or {}).get(rel) or 'v267')
    if not rows or rows[0].strip()!=exp or rows[-1].strip()!=exp: problems.append('marker:'+rel)
ok('package_hashes_markers',not problems,','.join(problems[:8]))
# Every stage appears once in infrastructure and every owner body only once physically.
install_re=re.compile(r"_owner_install\((['\"])([^'\"]+)\1,\s*(['\"])([^'\"]+)\3\)")
infra='\n'.join(text(x) for x in SOURCE_PARTS)
installs=[(m.group(2),m.group(4)) for m in install_re.finditer(infra)]
expected=[]; duplicate_bodies=[]; owner_template_dups=[]
public_to_owner={}
for owner,row in (manifest.get('owners') or {}).items():
    stages=(row or {}).get('stages') or {}; expected += [(owner,s) for s in stages]
    for sym in (row or {}).get('symbols') or []:
        if sym in public_to_owner and public_to_owner[sym]!=owner: duplicate_bodies.append((sym,public_to_owner[sym],owner))
        public_to_owner[sym]=owner
    rel=(row or {}).get('file'); tree=ast.parse(text(rel),filename=str(rel)); defs=[n.name for n in tree.body if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef))]
    if len(defs)!=len(set(defs)): owner_template_dups.append(rel)
    if len(defs)!=int((row or {}).get('stage_occurrences') or 0): owner_template_dups.append(rel+':count')
ok('stage_install_exact',len(installs)==len(expected) and sorted(installs)==sorted(expected),f'actual={len(installs)} expected={len(expected)}')
ok('public_symbol_single_owner',not duplicate_bodies,str(duplicate_bodies[:5]))
ok('owner_template_unique',not owner_template_dups,str(owner_template_dups[:5]))
# No non-decorated owned body may remain in 01-10. Decorated route adapters are allowed by design.
leaks=[]
for rel in SOURCE_PARTS:
    tree=ast.parse(text(rel),filename=rel)
    for n in tree.body:
        if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)) and not n.decorator_list and n.name in public_to_owner:
            leaks.append((rel,n.lineno,n.name,public_to_owner[n.name]))
ok('zero_owner_body_leaks',not leaks,str(leaks[:8]))

# Infrastructure must have one final top-level def per name; old patch stages belong in 19_compat_legacy.py.
infra_dups=[]
seen_defs={}
for rel in SOURCE_PARTS:
    tree=ast.parse(text(rel),filename=rel)
    for n in tree.body:
        if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)):
            if n.name in seen_defs: infra_dups.append((n.name,seen_defs[n.name],(rel,n.lineno)))
            else: seen_defs[n.name]=(rel,n.lineno)
ok('zero_duplicate_infra_defs',not infra_dups,str(infra_dups[:8]))

# Strong name-boundary audit for newly separated integrations: no non-decorated obvious Google/Excel/MEGA functions in infra.
patterns={'google':re.compile(r'google|spreadsheet|drive_folder',re.I),'excel':re.compile(r'xlsx|excel|workbook|worksheet|tabl_lsx',re.I),'mega':re.compile(r'mega',re.I)}
name_leaks=[]
for rel in SOURCE_PARTS:
    tree=ast.parse(text(rel),filename=rel)
    for n in tree.body:
        if not isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)) or n.decorator_list: continue
        for dom,pat in patterns.items():
            if pat.search(n.name): name_leaks.append((dom,rel,n.lineno,n.name))
ok('integration_name_boundary',not name_leaks,str(name_leaks[:10]))
# Finance and finance-forward are physically distinct.
fin=set((manifest.get('owners',{}).get('finance') or {}).get('symbols') or [])
fwd=set((manifest.get('owners',{}).get('finance_forward') or {}).get('symbols') or [])
ok('finance_forward_disjoint',not (fin&fwd),str(sorted(fin&fwd)[:5]))
ok('forward_symbols_owned_by_forward',all(('forward' not in x.lower()) for x in fin),str([x for x in fin if 'forward' in x.lower()][:5]))
# Loader must be source-catalog based, not template-module import/cloning.
bot=text('bot.py')
ok('lean_owner_loader','_owner_install' in bot and 'importlib.util' not in bot and 'FunctionType' not in bot)
ok('loader_owner_files',all(x in bot for x in OWNER_PARTS))
# Docker deploy allowlist must include exactly current owner manifest/files and no old owner manifest.
docker=text('Dockerfile'); di=text('.dockerignore')
if RUNTIME_BUILD:
    # Dockerfile/.dockerignore are build-context controls and are intentionally not copied into /app.
    # Their source-mode validation already ran before packaging; do not create false runtime failures.
    ok('docker_current_owners',True,'source-only check skipped inside runtime image')
    ok('dockerignore_current_owners',True,'source-only check skipped inside runtime image')
else:
    ok('docker_current_owners','owners_manifest.json' in docker and all(x in docker for x in OWNER_PARTS) and 'business_manifest.json' not in docker)
    ok('dockerignore_current_owners','!owners_manifest.json' in di and all(('!'+x) in di for x in OWNER_PARTS) and '!business_manifest.json' not in di)
# Identity and R1/R2 authority invariants.
ok('display_name',"BOT_DISPLAY_NAME = 'очнись_12.36'" in text('01_core_data.py'))
split=text('10_split_policy_offload.py')
ok('r1_authority',"_R1234_CRITICAL_FAST_KEYS = ('mega', 'durability', 'checkpoints')" in split and '_r1234_probe_peer' in split and '_r1234_note_fallback' in split)
# Optional startup smoke inside Docker/runtime environment.
if str(os.getenv('FINALIZATION_STARTUP_SMOKE','0')).strip().lower() in {'1','true','yes','on'}:
    env=dict(os.environ); env['BOT_DEFER_MAIN_R54']='1'; env.setdefault('B_T','123456:STARTUPSMOKE')
    cp=subprocess.run([sys.executable,'-c','import bot; print("STARTUP_IMPORT_OK")'],cwd=str(ROOT),env=env,text=True,capture_output=True,timeout=120)
    ok('startup_import',cp.returncode==0 and 'STARTUP_IMPORT_OK' in cp.stdout,(cp.stdout+'\n'+cp.stderr)[-1200:])

passed=sum(1 for _,v,_ in checks if v); total=len(checks)
print(f'FINALIZATION 12.36: {passed}/{total} PASS' if passed==total else f'FINALIZATION 12.36: {passed}/{total} ({total-passed} FAIL)')
if passed!=total:
    for n,v,d in checks:
        if not v: print(' -',n,d)
    raise SystemExit(1)
