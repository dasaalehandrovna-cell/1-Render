#!/usr/bin/env python3
from __future__ import annotations

import ast
import os
import py_compile
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
RUNTIME_BUILD = str(os.getenv('FINALIZATION_RUNTIME_BUILD','0') or '0').strip().lower() in {'1','true','yes','on'}
STARTUP_SMOKE = str(os.getenv('FINALIZATION_STARTUP_SMOKE','0') or '0').strip().lower() in {'1','true','yes','on'}
checks=[]

def check(name, cond, detail=''):
    checks.append((name, bool(cond), str(detail or '')))
    if not cond:
        print('FAIL', name, detail)

def read(name):
    p=ROOT/name
    return p.read_text(encoding='utf-8',errors='replace') if p.is_file() else ''

required=['bot.py','runtime_flat.py','start_front.py','runtime_config.py','requirements.txt','FINALIZATION_GATE.py']
check('runtime_files', all((ROOT/x).is_file() for x in required), ','.join(x for x in required if not (ROOT/x).is_file()))

for rel in ['bot.py','runtime_flat.py','start_front.py','runtime_config.py','FINALIZATION_GATE.py']:
    try:
        py_compile.compile(str(ROOT/rel), doraise=True)
        ast.parse(read(rel), filename=rel)
        good=True; detail=''
    except Exception as exc:
        good=False; detail=str(exc)
    check('compile_'+rel, good, detail)

bot=read('bot.py'); runtime=read('runtime_flat.py'); start=read('start_front.py'); cfg=read('runtime_config.py'); docker=read('Dockerfile')

# OCHNIS 13 removes runtime source reconstruction completely.
check('release_name', "BOT_DISPLAY_NAME = 'очнись_13'" in runtime and "OCHNIS_RELEASE = 'очнись_13'" in bot)
check('no_owner_install_runtime', '_owner_install(' not in runtime and '_owner_install(' not in bot)
check('no_exec_compile_runtime', 'exec(compile(' not in runtime and 'exec(compile(' not in bot)
check('thin_bot_entry', 'import runtime_flat as _runtime' in bot and 'main = _runtime.main' in bot)
check('flat_runtime_source', runtime.startswith('# OCHNIS_13 FLAT RUNTIME'))

# Core user-visible domains must still be present in the flattened runtime.
for symbol in ['handle_finance_message','get_forward_links','_v229_command_tasks','_reminder_send_cycle','handle_secret_note_message','tenant_google_config','_write_simple_xlsx','_mega_run']:
    present = (('def '+symbol+'(' in runtime) or ('async def '+symbol+'(' in runtime) or (symbol+' =' in runtime))
    check('domain_'+symbol, present, symbol)

# R1/R2 contract: startup detection, R2 restore, standalone R1, dynamic accelerator fallback.
check('r2_boot_probe', 'def _och13_probe_r2()' in start and "'/peer/health'" in start)
check('r2_boot_restore', 'def _och13_restore_from_r2' in start and "'/internal/restore/latest'" in start and 'R2_VALIDATED_SNAPSHOT' in start)
check('r1_never_blocked_by_r2', "trace['policy'] = 'OCH13_R1_PRIMARY_R2_OPTIONAL'" in start and 'EMPTY R1' in start)
check('runtime_flat_launcher', "with_name('runtime_flat.py')" in start)
check('auto_accel', 'def _och13_auto_accel_routes()' in runtime and 'def _och13_boot_probe()' in runtime)
check('standalone_mode', "'STANDALONE_R1'" in runtime)
check('distributed_mode', "'DISTRIBUTED_R1_PLUS_R2'" in runtime)
check('fallback_wrapper', 'def _r1234_note_fallback' in runtime and 'def submit_interactive_file_job' in runtime)

ns={}
try:
    exec(compile(cfg,'runtime_config.py','exec'),ns,ns)
    front=ns.get('FRONT_INTERNAL_ENV') or {}
    cfg_ok=True
except Exception as exc:
    front={}; cfg_ok=False
    check('runtime_config_exec',False,exc)
if cfg_ok:
    check('runtime_config_exec',True)
    for key in ['OCH13_R2_AUTO_ACCEL','OCH13_R2_BOOT_PROBE','OCH13_R2_BOOT_RESTORE']:
        check('cfg_'+key, str(front.get(key))=='1', front.get(key))
    check('peer_watch_enabled', str(front.get('PEER_PING_ENABLED'))=='1', front.get('PEER_PING_ENABLED'))
    budgets={'UI_WORKERS':2,'FAST_UI_WORKERS':2,'WINDOW_RENDER_WORKERS':2,'UI_CLEANUP_WORKERS':1,'UI_DELETE_WORKERS':1,'BACKGROUND_WORKERS':1,'SCHEDULER_WORKERS':1,'R21_HEAVY_DISPATCH_WORKERS':1}
    bad=[]
    for k,lim in budgets.items():
        try:
            if int(front.get(k,999))>lim: bad.append(f'{k}={front.get(k)}>{lim}')
        except Exception: bad.append(f'{k}=invalid')
    check('memory_worker_budget',not bad,'; '.join(bad))

if not RUNTIME_BUILD:
    check('docker_present',(ROOT/'Dockerfile').is_file())
    check('docker_flat_only','runtime_flat.py' in docker and 'owners_manifest.json' not in docker and '01_core_data.py' not in docker)
    old=[p.name for p in ROOT.glob('[0-1][0-9]_*.py')]
    check('no_legacy_runtime_parts',not old,','.join(sorted(old)))
    check('source_archive_preserved',(ROOT/'SOURCE_12_36.zip').is_file(),'SOURCE_12_36.zip')

if STARTUP_SMOKE:
    env=dict(os.environ)
    env.update({
        'BOT_DEFER_MAIN_R54':'1','B_T':env.get('B_T') or '123456:STARTUPSMOKE',
        'DB_FILE':env.get('DB_FILE') or '/tmp/och13_gate.sqlite3',
        'MEGA_ENABLED':'0','REDIS_ENABLED':'0','TELEGRAM_BACKUP_ENABLED':'0','REDIS_URL':'',
        'PEER_PRIVATE_URL':'','PEER_SERVICE_URL':'','PEER_SHARED_SECRET':'',
        'MEGA_EMAIL':'','MEGA_PASSWORD':'','TRAFFIC_AUDIT_ENABLED':'0',
    })
    code=(
        "import bot; "
        "assert callable(bot.main); "
        "assert bot.BOT_DISPLAY_NAME=='очнись_13'; "
        "assert (getattr(bot,'_SPLIT_STATE',{}) or {}).get('och13_mode')=='STANDALONE_R1'; "
        "print('OCH13_STARTUP_IMPORT_OK')"
    )
    try:
        cp=subprocess.run([sys.executable,'-c',code],cwd=str(ROOT),env=env,text=True,capture_output=True,timeout=120)
        check('startup_without_r2',cp.returncode==0 and 'OCH13_STARTUP_IMPORT_OK' in cp.stdout,(cp.stdout+'\n'+cp.stderr)[-1800:])
    except Exception as exc:
        check('startup_without_r2',False,exc)

passed=sum(1 for _,v,_ in checks if v); total=len(checks)
print(f'FINALIZATION OCHNIS 13: {passed}/{total} PASS')
if passed!=total:
    for name,val,detail in checks:
        if not val: print(' -',name,detail)
    raise SystemExit(1)
