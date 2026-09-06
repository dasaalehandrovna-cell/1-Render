# v262
from pathlib import Path
import hashlib, json, os, inspect
from runtime_config import install_internal_runtime_config
install_internal_runtime_config("front")
MODULAR_VERSION = "vys_262"
MODULE_FILE_VERSION = "v262"
MODULAR_SOURCE_PARTS = ['00_core.py', '05_key_value_runtime.py', '10_mega_runtime.py', '11_data_constitution.py', '12_telegram_durable.py', '13_telegram_stable_slots.py', '14_mega_sharded_parallel.py', '15_operation_safety.py', '16_window_diagnostics.py', '17_memory_runtime.py', '20_callback_tokens.py', '30_secret.py', '35_reminders.py', '40_message_router.py', '50_forwarding.py', '60_finance_currency.py', '61_forwarding_ui.py', '62_finance_ui.py', '63_google_sheets.py', '70_fast_ui.py', '80_callback_router.py', '90_commands_exports.py', '91_finance_records_handlers.py', '72_multitenant_runtime.py', '99_web_runtime.py', '73_state_export_runtime.py', '74_ui_reliability_runtime.py', '75_platform_features_runtime.py', '76_tasks_runtime.py', '85_runtime_control.py', '88_ui_constructor.py', '89_callback_final.py', '92_v262_linked_finance_speed.py', '98_split_front.py', '97_r29_policy_ui.py']
_MODULAR_ROOT = Path(__file__).resolve().parent
_MODULAR_MERGED_CACHE = None
_MANIFEST_PATH = _MODULAR_ROOT / "modules_manifest.json"

def _sha256_bytes(raw: bytes) -> str: return hashlib.sha256(raw).hexdigest()

def _validate_modular_package() -> None:
    if not _MANIFEST_PATH.exists(): raise RuntimeError("modules_manifest.json is missing")
    manifest=json.loads(_MANIFEST_PATH.read_text(encoding="utf-8"))
    if str(manifest.get("version") or "") != MODULAR_VERSION: raise RuntimeError("modular version mismatch")
    files=manifest.get("files") or {}; markers=manifest.get("file_markers") or {}; problems=[]
    for rel in MODULAR_SOURCE_PARTS:
        path=_MODULAR_ROOT/rel
        if not path.exists(): problems.append(f"missing {rel}"); continue
        raw=path.read_bytes()
        if _sha256_bytes(raw) != str(files.get(rel) or ""): problems.append(f"hash {rel}")
        rows=raw.decode("utf-8").splitlines(); expected="# "+str(markers.get(rel) or MODULE_FILE_VERSION)
        if not rows or rows[0].strip()!=expected or rows[-1].strip()!=expected: problems.append(f"marker {rel}")
    if set(files)!=set(MODULAR_SOURCE_PARTS): problems.append("manifest parts mismatch")
    if problems: raise RuntimeError("MODULAR PACKAGE CHECK FAILED: "+"; ".join(problems[:12]))

def _exec_source_part(relative_path: str) -> None:
    path=_MODULAR_ROOT/relative_path; text=path.read_text(encoding="utf-8"); exec(compile(text,str(path),"exec"),globals(),globals())

def _strip_part_version(text: str) -> str:
    rows=text.splitlines()
    if rows and rows[0].strip().startswith("# v"): rows=rows[1:]
    if rows and rows[-1].strip().startswith("# v"): rows=rows[:-1]
    return "\n".join(rows).rstrip()+"\n"

def _modular_merged_source_path() -> str:
    global _MODULAR_MERGED_CACHE
    tmp_dir=os.getenv("MEGA_LOCAL_TMP_DIR","/tmp").strip() or "/tmp"; os.makedirs(tmp_dir,exist_ok=True)
    target=os.path.join(tmp_dir,f"{MODULAR_VERSION}_full.py")
    chunks=[_strip_part_version((_MODULAR_ROOT/rel).read_text(encoding="utf-8")) for rel in MODULAR_SOURCE_PARTS]
    with open(target,"w",encoding="utf-8") as fh:
        fh.write(f"# {MODULE_FILE_VERSION}\n"); fh.write("\n".join(chunks).rstrip()+"\n"); fh.write('if __name__ == "__main__":\n    main()\n'); fh.write(f"# {MODULE_FILE_VERSION}\n")
    _MODULAR_MERGED_CACHE=target; return target

def _runtime_contract_gate_v222() -> None:
    contracts = {
        "probe_bot_in_chat": ({"chat_id", "deep", "persist", "schedule_backup", "_migration_retry"}, "00_core.py"),
        "update_chat_info_from_chat_object": ({"chat_obj", "persist", "schedule_backup"}, "73_state_export_runtime.py"),
        "set_chat_bot_removed": ({"chat_id", "removed", "reason", "persist", "schedule_backup"}, "73_state_export_runtime.py"),
        "set_chat_status_v150": ({"chat_id", "status", "reason", "source", "migrated_to", "force_history", "persist", "schedule_backup"}, "73_state_export_runtime.py"),
        "collect_probe_chat_ids_v200": ({"include_owner"}, "00_core.py"),
        "migrate_chat_id_everywhere": ({"old_chat_id", "new_chat_id", "reason"}, "73_state_export_runtime.py"),
        "resolve_forward_targets": ({"source_chat_id"}, "72_multitenant_runtime.py"),
        "send_and_auto_delete": ({"chat_id", "text", "delay"}, "74_ui_reliability_runtime.py"),
        "send_html_and_auto_delete": ({"chat_id", "html_text", "delay"}, "74_ui_reliability_runtime.py"),
        "submit_interactive_file_job": ({"chat_id", "kind", "label", "func"}, "98_split_front.py"),
    }
    problems=[]
    for name,(required,owner_file) in contracts.items():
        fn=globals().get(name)
        if not callable(fn): problems.append(f"missing {name}"); continue
        try:
            sig=inspect.signature(fn); accepted=set(sig.parameters); has_kwargs=any(p.kind==inspect.Parameter.VAR_KEYWORD for p in sig.parameters.values())
            missing=sorted(required-accepted) if not has_kwargs else []
            if missing: problems.append(f"signature {name} missing={missing} actual={sig}")
        except Exception as exc: problems.append(f"signature {name}: {exc}")
        try:
            filename=str(getattr(getattr(fn,"__code__",None),"co_filename","") or "")
            if owner_file and not filename.endswith(owner_file): problems.append(f"owner {name}={filename or '?'} expected={owner_file}")
        except Exception as exc: problems.append(f"owner {name}: {exc}")
    if problems: raise RuntimeError("RUNTIME CONTRACT GATE v223 FAILED: "+"; ".join(problems[:12]))

_validate_modular_package()
for _part in MODULAR_SOURCE_PARTS: _exec_source_part(_part)
_runtime_contract_gate_v222()
if __name__ == "__main__": main()
# v262
