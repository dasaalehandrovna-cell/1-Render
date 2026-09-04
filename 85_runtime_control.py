# v262
"""v178 GLOBAL FINAL: process control center + callback latency diagnostics for every contour.

This layer replaces the single v175 heavy-process switch with granular runtime gates.
The bot's mission-critical core remains visible and locked in the menu; optional/background
work can be toggled independently to isolate UI latency without rewriting business logic.
"""
import collections as _v176_collections
import json as _v176_json
import threading as _v176_threading
import time as _v176_time
import hashlib as _v196_hashlib
import os as _v196_os
import tempfile as _v196_tempfile
V176_FILE_MARKER = 'v178_global_performance_final'
V176_SETTINGS_KEY = 'process_control_v176'
_V176_LOCK = _v176_threading.RLock()
_V176_PERF = _v176_collections.deque(maxlen=240)
_V177_PERF_STAGES = _v176_collections.deque(maxlen=720)
_V177_PERF_LOCAL = _v176_threading.local()

def v177_perf_stage(name: str, elapsed: float) -> None:
    """Record a timed sub-stage inside the currently executing callback."""
    try:
        action = str(getattr(_V177_PERF_LOCAL, 'action', '') or '')[:120]
        _V177_PERF_STAGES.append({'ts': _v176_time.time(), 'action': action, 'stage': str(name or 'stage')[:80], 'elapsed': max(0.0, float(elapsed or 0.0))})
    except Exception:
        pass

def v177_perf_clear() -> None:
    try:
        _V176_PERF.clear()
    except Exception:
        pass
    try:
        _V177_PERF_STAGES.clear()
    except Exception:
        pass
_V176_MIGRATED_HEAVY = True
_V176_PROCESS_DEFS = {'ui_retry': ('ui', '🔁 Повторы edit Telegram', True, 'hot', 'Внешние повторы safe_edit при 429/ошибке. Кандидат на задержку кнопок.'), 'win_diag': ('ui', '🩺 Диагностика окон', True, 'hot', 'v208: включена для полноценного локального forensic-журнала; сеть не вызывается на каждое событие.'), 'win_reg': ('ui', '🗂 Реестр окон → SQLite/MEGA', _V176_MIGRATED_HEAVY, 'hot', 'Фоновое сохранение реестра открытых окон.'), 'win_rec': ('ui', '🔄 Reconcile окон', _V176_MIGRATED_HEAVY, 'hot', 'Сверка реестра окон, включая цикл v153 каждые 600 сек.'), 'btn_chain': ('ui', '🧾 Трассировка press/result', True, 'hot', 'v208: press/result пишутся локально и уходят в MEGA только сжатым batch.'), 'btn_press': ('ui', '📝 Журнал button_pressed', True, 'hot', 'v208: исходная кнопка нужна для разбора пользовательского сценария А→Я.'), 'win_journal': ('ui', '📐 Window-журнал', True, 'hot', 'v208: подробные window_* события снова включены для диагностики окон/конструктора.'), 'fin_refresh': ('ui', '💹 Автообновление фин. окон', True, 'medium', 'Автоперерисовка зарегистрированных финансовых окон после изменений.'), 'win_cleanup': ('ui', '🧹 Очистка реестра окон', _V176_MIGRATED_HEAVY, 'medium', 'Скан/очистка устаревших окон.'), 'delta_auto': ('mega', '☁️ MEGA delta авто', True, 'critical', 'Маленькие отложенные внешние delta-сохранения изменений.'), 'delta_critical': ('mega', '🛡 MEGA delta критическая', True, 'critical', 'Синхронный внешний свидетель критичных финансовых операций.'), 'full_chat': ('mega', '📦 Full backup чата', False, 'medium', 'Авто full-backup чатов выключен как дублирующая копия; ручной backup остаётся, а данные защищают SQLite generation + delta.'), 'full_global': ('mega', '🌐 SYSTEM SQLite generation', _V176_MIGRATED_HEAVY, 'medium', 'v242: редкий полный SQLite checkpoint только каждые 6/12 часов при наличии изменений; /restore и ручной backup остаются немедленными.'), 'journal_mega': ('mega', '📓 Сжатый MEGA-журнал', True, 'medium', 'v208: полноценный journal сохраняется gzip-пакетами; не по строке. ERROR/CRITICAL и shutdown/fatal остаются немедленными.'), 'runtime_upload': ('mega', '📡 Runtime watcher upload', False, 'medium', 'Частые heartbeat-snapshots выключены; lease и часовой traffic/health checkpoint остаются, shutdown/fatal сохраняются отдельно.'), 'source_archive': ('mega', '🗃 Архив исходника', False, 'low', 'Автоархив исходника выключен: 3+ MB на каждый старт были лишним outbound; ручная выгрузка остаётся.'), 'failed_repair': ('mega', '🩹 Repair failed-задач', False, 'medium', 'Автоматический безопасный ремонт failed durable tasks.'), 'failed_diag': ('mega', '🔬 Диагностика failed-задач', False, 'medium', 'Фоновый диагностический скан failed tasks.'), 'mega_maint': ('mega', '🧰 MEGA cleanup', True, 'medium', 'Очистка runtime-артефактов только внутри единственного канонического MEGA root.'), 'mega_recover': ('mega', '♻️ Startup recovery MEGA-задач', True, 'critical', 'Восстановление pending/running durable tasks после рестарта.'), 'lease': ('mega', '🔐 Instance lease', True, 'critical', 'Проверка второго одновременно работающего экземпляра.'), 'google_auto': ('auto', '📊 Google Sheets авто', _V176_MIGRATED_HEAVY, 'medium', 'Автоматическая синхронизация после финансовых изменений; ручная остаётся.'), 'reminders': ('auto', '⏰ Напоминалки', True, 'critical', 'Планировщик и отправка напоминаний.'), 'expense_ping': ('auto', '📲 Expense ping', True, 'medium', 'Автоматическая доставка shortcut-событий расходов и recovery.'), 'lowram': ('system', '🧊 Low-RAM idle sweep', True, 'medium', 'Выгрузка холодной истории из RAM в SQLite, когда бот свободен.'), 'memory_guard': ('system', '🧠 Memory guard', True, 'critical', 'Контроль RAM, trim и защитный restart при аварийной памяти.')}
_V176_PAGE_TITLES = {'ui': '⚡ ИНТЕРФЕЙС / КНОПКИ', 'mega': '☁️ MEGA / BACKUP', 'auto': '🔄 АВТОМАТИКА', 'system': '🧠 СИСТЕМА', 'core': '🔒 ОСНОВА БОТА'}
_V176_LOCKED_CORE = [('🌐 Telegram webhook / приём update', 'Всегда ВКЛ — без него бот не принимает события.'), ('💰 Финансовый учёт', 'Всегда ВКЛ — основная миссия бота.'), ('💸 Финансовая пересылка', 'Всегда ВКЛ — приоритетная бизнес-линия.'), ('➡️ Обычная пересылка', 'Всегда ВКЛ — штатная бизнес-функция.'), ('🪷 SECRET', 'Всегда ВКЛ — штатная бизнес-функция.'), ('📋 Диспетчер задач', 'Всегда ВКЛ — штатная бизнес-функция.'), ('💾 SQLite', 'Всегда ВКЛ — локальное рабочее состояние; не отключается диагностикой.'), ('🌐 Web endpoint / webhook', 'Всегда ВКЛ — приём HTTP/Telegram. Self-ping и smart fallback управляются отдельно в Инфо.')]

def _v176_root() -> dict:
    try:
        gs = data.setdefault('_global_settings', {})
        root = gs.setdefault(V176_SETTINGS_KEY, {})
    except Exception:
        return {}
    if not root.get('initialized'):
        for code, (_page, _label, default, _risk, _desc) in _V176_PROCESS_DEFS.items():
            root.setdefault(code, bool(default))
        root['initialized'] = True
        root['migrated_from_v175_heavy'] = bool(_V176_MIGRATED_HEAVY)
        try:
            root['created_at'] = now_local().isoformat(timespec='seconds')
        except Exception:
            pass
    return root

def _v240_process_allowed_for_mode(code: str) -> bool:
    row = _V176_PROCESS_DEFS.get(str(code))
    if not row:
        return True
    group = str(row[0])
    if group == 'mega':
        return storage_profile_v237_1() == STORAGE_PROFILE_MEGA_V237_1
    return True

def v176_process_enabled(code: str) -> bool:
    row = _V176_PROCESS_DEFS.get(str(code))
    if not row:
        return True
    if not _v240_process_allowed_for_mode(code):
        return False
    try:
        return bool(_v176_root().get(str(code), row[2]))
    except Exception:
        return bool(row[2])

def _v176_persist(reason: str='process_control') -> None:
    try:
        SQLITE.save_root(_sqlite_pack_root(data))
    except Exception:
        try:
            save_data(data, root_only=True)
        except Exception:
            pass
    try:
        if callable(_V176_ORIG_SCHEDULE_DELTA):
            _V176_ORIG_SCHEDULE_DELTA(int(OWNER_ID or 0) or None, delay=0.5, reason=f'v176_{reason}')
    except Exception:
        pass

def heavy_processes_enabled_v175() -> bool:
    return True

def light_mode_enabled_v175() -> bool:
    return False

def heavy_processes_label_v175() -> str:
    return '⚙️ Процессы / скорость'

def heavy_processes_status_v175() -> str:
    off = sum((1 for code in _V176_PROCESS_DEFS if not v176_process_enabled(code)))
    return f'⚙️ Центр процессов v179: отключено {off} из {len(_V176_PROCESS_DEFS)} управляемых процессов.'
_V176_ORIG_BOT_JOURNAL = _v177_legacy_0007_bot_journal
_V176_ORIG_WINDOW_REGISTRY = globals().get('_v168_schedule_window_registry_persist')
_V176_ORIG_WINDOW_RECONCILE = _v179_base_reconcile_windows
_V176_ORIG_WINDOW_CLEANUP = _canon_cleanup_open_window_registry__001
_V176_ORIG_FIN_REFRESH = globals().get('schedule_financial_window_refresh')
_V176_ORIG_SCHEDULE_DELTA = _canon_schedule_delta_backup__003
_V176_ORIG_CRITICAL_DELTA = _canon_persist_critical_delta_now__003
_V176_ORIG_FULL_BACKUP = globals().get('schedule_full_backup_only')
_V176_ORIG_GLOBAL_SNAPSHOT = globals().get('_mark_global_snapshot_pending')
_V176_ORIG_JOURNAL_FLUSH = globals().get('journal_flush_to_mega')
_V176_ORIG_JOURNAL_WARM = globals().get('_journal_warm_tail_job')
_V176_ORIG_RUNTIME_HEARTBEAT = _v179_base_runtime_heartbeat_job
_V176_ORIG_RUNTIME_UPLOAD = _canon_runtime_upload_snapshot__001
_V176_ORIG_SOURCE_ARCHIVE = globals().get('archive_current_bot_source_to_mega')
_V176_ORIG_FAILED_REPAIR = _canon_schedule_safe_failed_task_repairs__002
_V176_ORIG_FAILED_DIAG = globals().get('refresh_failed_task_diagnostics')
_V176_ORIG_MEGA_MIGRATION = _v179_base_schedule_migration
_V176_ORIG_RUNTIME_CLEANUP = globals().get('_v153_runtime_cleanup_remote')
_V176_ORIG_INSTANCE_LEASE = _v179_base_instance_lease_check
_V176_ORIG_MEGA_RECOVERY = _canon_schedule_mega_task_recovery__003
_V176_ORIG_GOOGLE_AFTER = globals().get('_v169_schedule_google_after_change')
_V176_ORIG_GOOGLE_ENQUEUE = globals().get('_v169_google_enqueue')
_V176_ORIG_REMINDER_TICK = _canon_reminder_tick__001
_V176_ORIG_EXPENSE_ENQUEUE = globals().get('enqueue_expense_ping_event')
_V176_ORIG_EXPENSE_RECOVERY = globals().get('schedule_expense_ping_recovery')
_V176_ORIG_LOWRAM_SWEEP = globals().get('_lowram_idle_sweep_job')
_V176_ORIG_MEMORY_GUARD = globals().get('memory_guard_tick')

def _canon_bot_journal__001(action: str, chat_id=None, detail: str='', level: str='INFO'):
    """Final journal gate: one public implementation, no v176→v153→core wrapper chain."""
    action_s = str(action or '')
    level_s = str(level or 'INFO')
    if level_s.upper() not in {'ERROR', 'CRITICAL'}:
        if action_s.startswith('button_chain_') and (not v176_process_enabled('btn_chain')):
            return None
        if action_s == 'button_pressed' and (not v176_process_enabled('btn_press')):
            return None
        if action_s.startswith('window_') and (not v176_process_enabled('win_journal')):
            return None
    base = globals().get('_V153_ORIG_BOT_JOURNAL')
    if callable(base):
        try:
            sanitizer = globals().get('v153_sanitize')
            clean_detail = sanitizer(detail) if callable(sanitizer) else detail
        except Exception:
            clean_detail = detail
        return base(action_s, chat_id, clean_detail, level_s)
    if callable(_V176_ORIG_BOT_JOURNAL):
        return _V176_ORIG_BOT_JOURNAL(action_s, chat_id, detail, level_s)
    return None

def _v177_deferred_ui_retry(chat_id: int, message_id: int, text: str, reply_markup=None, parse_mode=None, purpose: str='ui') -> None:
    """One non-blocking retry outside the callback thread."""
    try:
        fast_ui_edit_message_text(int(chat_id), int(message_id), text, reply_markup=reply_markup, parse_mode=parse_mode, purpose=str(purpose or 'ui') + '_deferred')
    except Exception:
        pass

def _canon_v161_edit_retry__001(chat_id: int, message_id: int, text: str, reply_markup=None, parse_mode=None, purpose: str='ui') -> str:
    """R22 UI policy: enqueue latest render; callback worker never waits for Telegram RTT."""
    started = _v176_time.monotonic()
    try:
        result = str(fast_ui_edit_message_text(int(chat_id), int(message_id), text, reply_markup=reply_markup, parse_mode=parse_mode, purpose=purpose) or 'failed')
    except Exception:
        result = 'failed'
    v177_perf_stage('render_enqueue', _v176_time.monotonic() - started)
    if result in {'rate_limited', 'failed'} and v176_process_enabled('ui_retry'):
        try:
            pool = globals().get('GENERAL_TASK_POOL')
            key = f'v177-ui-retry:{int(chat_id)}:{int(message_id)}'
            if pool is not None:
                pool.submit_unique(key, _v177_deferred_ui_retry, int(chat_id), int(message_id), text, reply_markup, parse_mode, purpose)
            return 'scheduled'
        except Exception:
            pass
    return result
if callable(_V176_ORIG_WINDOW_REGISTRY):

    def _v168_schedule_window_registry_persist():
        if not v176_process_enabled('win_reg'):
            return None
        return _V176_ORIG_WINDOW_REGISTRY()
if callable(_V176_ORIG_WINDOW_RECONCILE):

    def _v153_reconcile_windows():
        if not v176_process_enabled('win_rec'):
            return {'skipped': 'v176_win_rec_off'}
        return _V176_ORIG_WINDOW_RECONCILE()
if callable(_V176_ORIG_WINDOW_CLEANUP):

    def cleanup_open_window_registry(*args, **kwargs):
        if not v176_process_enabled('win_cleanup'):
            return {'skipped': 'v176_win_cleanup_off'}
        return _V176_ORIG_WINDOW_CLEANUP(*args, **kwargs)
if callable(_V176_ORIG_SCHEDULE_DELTA):

    def schedule_delta_backup(chat_id=None, delay=None, reason='change'):
        if not v176_process_enabled('delta_auto'):
            return False
        return _V176_ORIG_SCHEDULE_DELTA(chat_id, delay=delay, reason=reason)
if callable(_V176_ORIG_CRITICAL_DELTA):

    def persist_critical_delta_now(chat_id: int) -> bool:
        if not v176_process_enabled('delta_critical'):
            return True
        return bool(_V176_ORIG_CRITICAL_DELTA(int(chat_id)))
if callable(_V176_ORIG_FULL_BACKUP):

    def schedule_full_backup_only(chat_id: int, delay: float=3.0):
        if not v176_process_enabled('full_chat'):
            return None
        return _V176_ORIG_FULL_BACKUP(int(chat_id), delay)
if callable(_V176_ORIG_JOURNAL_FLUSH):

    def journal_flush_to_mega(force: bool=False) -> bool:
        if not v176_process_enabled('journal_mega'):
            fn = globals().get('journal_flush_critical_to_mega')
            return bool(fn(force)) if callable(fn) else True
        return bool(_V176_ORIG_JOURNAL_FLUSH(force))
if callable(_V176_ORIG_JOURNAL_WARM):

    def _journal_warm_tail_job():
        if not v176_process_enabled('journal_mega'):
            return None
        return _V176_ORIG_JOURNAL_WARM()
V178_RUNTIME_REMOTE_HEARTBEAT_SECONDS = max(300.0, min(3600.0, float(os.getenv('RUNTIME_REMOTE_HEARTBEAT_SECONDS', '900') or '900')))
if callable(_V176_ORIG_RUNTIME_HEARTBEAT):

    def _runtime_heartbeat_job():
        """v178: remote diagnostic heartbeat is slow-background, never 30-second MEGA churn."""
        if runtime_is_shutting_down() or not v176_process_enabled('runtime_upload'):
            return None
        next_delay = V178_RUNTIME_REMOTE_HEARTBEAT_SECONDS
        try:
            busy_fn = globals().get('_runtime_watcher_should_yield_to_critical_mega')
            if callable(busy_fn) and busy_fn():
                try:
                    runtime_event('watcher_heartbeat_deferred', 'critical MEGA work has priority')
                except Exception:
                    pass
                next_delay = min(90.0, V178_RUNTIME_REMOTE_HEARTBEAT_SECONDS)
            else:
                GENERAL_TASK_POOL.submit_unique('runtime-heartbeat-upload', runtime_upload_snapshot, 'heartbeat', False)
        finally:
            try:
                DELAYED_SCHEDULER.schedule('runtime-heartbeat', next_delay, _runtime_heartbeat_job)
            except Exception:
                pass
        return True
if callable(_V176_ORIG_RUNTIME_UPLOAD):

    def runtime_upload_snapshot(event: str='snapshot', immutable_event: bool=True) -> bool:
        low = str(event or '').casefold()
        if any((x in low for x in ('shutdown', 'fatal', 'thread_exception'))):
            try:
                fn = globals().get('traffic_audit_checkpoint_to_mega')
                if callable(fn):
                    fn('runtime_' + low[:60])
            except Exception:
                pass
        if not v176_process_enabled('runtime_upload') and (not any((x in low for x in ('shutdown', 'fatal', 'thread_exception')))):
            return True
        return bool(_V176_ORIG_RUNTIME_UPLOAD(event, immutable_event))
if callable(_V176_ORIG_SOURCE_ARCHIVE):

    def archive_current_bot_source_to_mega():
        if not v176_process_enabled('source_archive'):
            return True
        return _V176_ORIG_SOURCE_ARCHIVE()
if callable(_V176_ORIG_FAILED_REPAIR):

    def schedule_safe_failed_task_repairs(*args, **kwargs):
        if not v176_process_enabled('failed_repair'):
            return False
        return _V176_ORIG_FAILED_REPAIR(*args, **kwargs)
if callable(_V176_ORIG_FAILED_DIAG):

    def refresh_failed_task_diagnostics(*args, **kwargs):
        if not v176_process_enabled('failed_diag'):
            return []
        return _V176_ORIG_FAILED_DIAG(*args, **kwargs)
if callable(_V176_ORIG_MEGA_MIGRATION):

    def _v153_schedule_migration(*args, **kwargs):
        if not v176_process_enabled('mega_maint'):
            return False
        return _V176_ORIG_MEGA_MIGRATION(*args, **kwargs)
if callable(_V176_ORIG_RUNTIME_CLEANUP):

    def _v153_runtime_cleanup_remote(*args, **kwargs):
        if not v176_process_enabled('mega_maint'):
            return {'skipped': 'v176_mega_maint_off'}
        return _V176_ORIG_RUNTIME_CLEANUP(*args, **kwargs)
if callable(_V176_ORIG_INSTANCE_LEASE):

    def _v153_instance_lease_check(*args, **kwargs):
        if not v176_process_enabled('lease'):
            return {'skipped': 'v176_instance_lease_off'}
        return _V176_ORIG_INSTANCE_LEASE(*args, **kwargs)
if callable(_V176_ORIG_MEGA_RECOVERY):

    def schedule_mega_task_recovery(*args, **kwargs):
        if not v176_process_enabled('mega_recover'):
            return False
        return _V176_ORIG_MEGA_RECOVERY(*args, **kwargs)
if callable(_V176_ORIG_GOOGLE_AFTER):

    def _v169_schedule_google_after_change(target_chat_id: int, reason: str='finance_changed') -> None:
        if not v176_process_enabled('google_auto'):
            return None
        return _V176_ORIG_GOOGLE_AFTER(int(target_chat_id), reason)
if callable(_V176_ORIG_GOOGLE_ENQUEUE):

    def _v169_google_enqueue(target_chat_id: int, reason: str, run_key: str='', target_day: str='') -> bool:
        low = str(reason or '').casefold()
        if not v176_process_enabled('google_auto') and (not low.startswith('manual')):
            return False
        return bool(_V176_ORIG_GOOGLE_ENQUEUE(int(target_chat_id), reason, run_key, target_day))
if callable(_V176_ORIG_REMINDER_TICK):

    def _reminder_tick() -> None:
        if not v176_process_enabled('reminders'):
            return None
        return _V176_ORIG_REMINDER_TICK()
if callable(_V176_ORIG_EXPENSE_ENQUEUE):

    def enqueue_expense_ping_event(source: str='iphone', force: bool=False):
        if not v176_process_enabled('expense_ping'):
            return ('', False)
        return _V176_ORIG_EXPENSE_ENQUEUE(source, force)
if callable(_V176_ORIG_EXPENSE_RECOVERY):

    def schedule_expense_ping_recovery(*args, **kwargs):
        if not v176_process_enabled('expense_ping'):
            return False
        return _V176_ORIG_EXPENSE_RECOVERY(*args, **kwargs)
if callable(_V176_ORIG_LOWRAM_SWEEP):

    def _lowram_idle_sweep_job():
        if not v176_process_enabled('lowram'):
            return None
        return _V176_ORIG_LOWRAM_SWEEP()
if callable(_V176_ORIG_MEMORY_GUARD):

    def memory_guard_tick():
        if not v176_process_enabled('memory_guard'):
            return None
        return _V176_ORIG_MEMORY_GUARD()

def _v176_cancel_for(code: str) -> None:
    scheduler = globals().get('DELAYED_SCHEDULER')
    if scheduler is None:
        return
    keys = {'win_reg': ['window-registry-root-v168'], 'win_rec': ['v153-window-reconcile'], 'runtime_upload': ['runtime-heartbeat'], 'journal_mega': ['journal-warm-tail', 'journal-error-flush'], 'full_global': ['mega-global-quiet-v90', 'mega-global-max-v90', 'mega-global-retry-v90'], 'failed_repair': ['mega-task-safe-failed-repair'], 'failed_diag': ['v146-failed-task-diagnostics'], 'mega_maint': ['v153-runtime-cleanup'], 'mega_recover': ['mega-task-startup-recovery'], 'lowram': ['lowram-idle-sweep'], 'memory_guard': ['memory-guard'], 'expense_ping': ['expense-ping-recovery']}.get(code, [])
    for key in keys:
        try:
            scheduler.cancel(key)
        except Exception:
            pass

def _v176_resume_for(code: str) -> None:
    scheduler = globals().get('DELAYED_SCHEDULER')
    if scheduler is None:
        return
    try:
        if code == 'win_reg' and callable(globals().get('_v168_schedule_window_registry_persist')):
            globals()['_v168_schedule_window_registry_persist']()
        elif code == 'win_rec' and callable(globals().get('_v153_reconcile_windows')):
            GENERAL_TASK_POOL.submit_unique('v176-window-reconcile', globals()['_v153_reconcile_windows'])
        elif code == 'runtime_upload' and callable(globals().get('_runtime_heartbeat_job')):
            scheduler.schedule('runtime-heartbeat', 2.0, globals()['_runtime_heartbeat_job'])
        elif code == 'journal_mega' and callable(globals().get('_journal_warm_tail_job')):
            scheduler.schedule('journal-warm-tail', 3.0, globals()['_journal_warm_tail_job'])
        elif code == 'full_global' and bool(globals().get('_global_snapshot_pending', False)) and callable(globals().get('_mark_global_snapshot_pending')):
            globals()['_mark_global_snapshot_pending']()
        elif code == 'failed_repair' and callable(globals().get('schedule_safe_failed_task_repairs')):
            globals()['schedule_safe_failed_task_repairs'](2.0)
        elif code == 'failed_diag' and callable(globals().get('refresh_failed_task_diagnostics')):
            GENERAL_TASK_POOL.submit_unique('v176-failed-diag', globals()['refresh_failed_task_diagnostics'], True)
        elif code == 'mega_maint' and callable(globals().get('_v153_runtime_cleanup_job')):
            scheduler.schedule('v153-runtime-cleanup', 2.0, globals()['_v153_runtime_cleanup_job'])
        elif code == 'mega_recover' and callable(globals().get('schedule_mega_task_recovery')):
            globals()['schedule_mega_task_recovery'](0.5)
        elif code == 'lowram' and callable(globals().get('_lowram_idle_sweep_job')):
            scheduler.schedule('lowram-idle-sweep', 2.0, globals()['_lowram_idle_sweep_job'])
        elif code == 'memory_guard' and callable(globals().get('memory_guard_tick')):
            scheduler.schedule('memory-guard', 2.0, globals()['memory_guard_tick'])
        elif code == 'expense_ping' and callable(globals().get('schedule_expense_ping_recovery')):
            globals()['schedule_expense_ping_recovery'](0.5)
    except Exception:
        pass

def _v176_apply_runtime_flags() -> None:
    try:
        globals()['WINDOW_DIAGNOSTICS_ENABLED'] = bool(v176_process_enabled('win_diag'))
    except Exception:
        pass
    try:
        globals()['BOT_JOURNAL_DURABLE_ENABLED'] = bool(v176_process_enabled('journal_mega'))
    except Exception:
        pass
    for code in _V176_PROCESS_DEFS:
        if not v176_process_enabled(code):
            _v176_cancel_for(code)

def v176_set_process(code: str, enabled: bool, actor: int=0) -> bool:
    if code not in _V176_PROCESS_DEFS:
        return False
    if not _v240_process_allowed_for_mode(code):
        return bool(_v176_root().get(code, _V176_PROCESS_DEFS[code][2]))
    with _V176_LOCK:
        root = _v176_root()
        root[code] = bool(enabled)
        try:
            root['changed_at'] = now_local().isoformat(timespec='seconds')
            root['changed_by'] = int(actor or 0)
            root['last_changed'] = str(code)
        except Exception:
            pass
        if code == 'win_diag':
            globals()['WINDOW_DIAGNOSTICS_ENABLED'] = bool(enabled)
        if code == 'journal_mega':
            globals()['BOT_JOURNAL_DURABLE_ENABLED'] = bool(enabled)
        if enabled:
            _v176_resume_for(code)
        else:
            _v176_cancel_for(code)
        _v176_persist(f'toggle_{code}_{int(bool(enabled))}')
    try:
        _V176_ORIG_BOT_JOURNAL('v176_process_toggle', int(OWNER_ID or 0) or None, f'{code}={int(bool(enabled))} actor={int(actor or 0)}')
    except Exception:
        pass
    return bool(enabled)
_V176_FAST_PROFILE_OFF = {'ui_retry', 'win_diag', 'win_reg', 'win_rec', 'btn_chain', 'btn_press', 'win_journal', 'fin_refresh', 'win_cleanup', 'full_chat', 'journal_mega', 'runtime_upload', 'source_archive', 'failed_repair', 'failed_diag', 'mega_maint', 'google_auto'}
_V176_MIN_PROFILE_OFF = _V176_FAST_PROFILE_OFF | {'delta_auto', 'full_global', 'mega_recover', 'expense_ping', 'lowram'}

def v176_apply_profile(profile: str, actor: int=0) -> None:
    profile = str(profile or '')
    root = _v176_root()
    with _V176_LOCK:
        for code in _V176_PROCESS_DEFS:
            if profile == 'all':
                value = True
            elif profile == 'fast':
                value = code not in _V176_FAST_PROFILE_OFF
            elif profile == 'minimal':
                value = code not in _V176_MIN_PROFILE_OFF
            else:
                value = bool(_V176_PROCESS_DEFS[code][2])
            if code in {'delta_critical', 'memory_guard', 'reminders', 'lease'}:
                value = True
            root[code] = bool(value)
        try:
            root['profile'] = profile
            root['changed_at'] = now_local().isoformat(timespec='seconds')
            root['changed_by'] = int(actor or 0)
        except Exception:
            pass
        _v176_apply_runtime_flags()
        for code in _V176_PROCESS_DEFS:
            if v176_process_enabled(code):
                _v176_resume_for(code)
        _v176_persist(f'profile_{profile}')

def _v176_status_icon(code: str) -> str:
    return '✅' if v176_process_enabled(code) else '⛔'

def _v176_perf_summary() -> dict:
    rows = list(_V176_PERF)
    if not rows:
        return {'count': 0}
    vals = sorted((float(x.get('elapsed', 0.0)) for x in rows))
    n = len(vals)
    p50 = vals[n // 2]
    p90 = vals[min(n - 1, max(0, int((n - 1) * 0.9)))]
    by = {}
    for row in rows:
        action = str(row.get('action') or '?')[:80]
        by.setdefault(action, []).append(float(row.get('elapsed', 0.0)))
    top = sorted(((sum(v) / len(v), max(v), len(v), k) for k, v in by.items()), reverse=True)[:6]
    return {'count': n, 'p50': p50, 'p90': p90, 'max': vals[-1], 'slow05': sum((1 for x in vals if x >= 0.5)), 'slow10': sum((1 for x in vals if x >= 1.0)), 'top': top}

def _v176_pool_line(name: str) -> str:
    pool = globals().get(name)
    if pool is None:
        return ''
    try:
        s = pool.stats() or {}
        return f"{name.replace('_TASK_POOL', '')}: {int(s.get('active', 0))}/{int(s.get('pending', 0))}"
    except Exception:
        return ''

def _v176_speed_text() -> str:
    s = _v176_perf_summary()
    lines = ['📊 СКОРОСТЬ КНОПОК v178 GLOBAL FINAL', '', 'Полное время callback + отдельный замер тяжёлых внутренних этапов.']
    if not s.get('count'):
        lines += ['', 'Пока нет замеров после очистки/запуска v177.']
    else:
        lines += ['', f"Последних callback: {s['count']}", f"Медиана: {s['p50']:.3f} c · P90: {s['p90']:.3f} c · MAX: {s['max']:.3f} c", f"≥0.5 c: {s['slow05']} · ≥1.0 c: {s['slow10']}", '', 'Самые медленные действия:']
        for avg, mx, count, action in s.get('top', []):
            lines.append(f'• {action[:48]} — avg {avg:.3f} c / max {mx:.3f} c / n={count}')
    pools = [x for x in (_v176_pool_line(n) for n in ('FAST_UI_TASK_POOL', 'UI_TASK_POOL', 'V166_WINDOW_UI_TASK_POOL', 'FINANCE_TASK_POOL', 'FORWARD_TASK_POOL', 'GENERAL_TASK_POOL', 'DELTA_TASK_POOL', 'BACKUP_TASK_POOL', 'JOURNAL_TASK_POOL')) if x]
    if pools:
        lines += ['', 'Очереди active/pending:', ' · '.join(pools)]
    stages = list(_V177_PERF_STAGES)
    if stages:
        by_stage = {}
        for row in stages:
            by_stage.setdefault(str(row.get('stage') or 'stage'), []).append(float(row.get('elapsed', 0.0)))
        top_stages = sorted(((sum(v) / len(v), max(v), len(v), k) for k, v in by_stage.items()), reverse=True)[:6]
        lines += ['', 'Самые тяжёлые внутренние этапы:']
        for avg, mx, count, name in top_stages:
            lines.append(f'• {name[:38]} — avg {avg:.3f} c / max {mx:.3f} c / n={count}')
    lines += ['', 'Для чистого теста нажми «🧹 Очистить замер», затем 10–20 раз повтори один и тот же переход.']
    return '\n'.join(lines)[:3900]

def _v176_menu_text(page: str='ui') -> str:
    page = page if page in _V176_PAGE_TITLES else 'ui'
    if page == 'mega' and storage_profile_v237_1() != STORAGE_PROFILE_MEGA_V237_1:
        page = 'ui'
    enabled = sum((1 for c in _V176_PROCESS_DEFS if v176_process_enabled(c)))
    lines = ['⚙️ ЦЕНТР ПРОЦЕССОВ / СКОРОСТЬ v178 GLOBAL', f'Управляемых процессов: {len(_V176_PROCESS_DEFS)} · ВКЛ {enabled} · ВЫКЛ {len(_V176_PROCESS_DEFS) - enabled}', '', _V176_PAGE_TITLES[page]]
    if page == 'core':
        lines += ['', 'Основа показана здесь специально, чтобы было видно, что миссия бота не исчезает при диагностике:']
        for label, desc in _V176_LOCKED_CORE:
            lines.append(f'\n🔒 {label}\n{desc}')
        lines += ['', 'Эти пункты нельзя случайно выключить из диагностического меню.']
        return '\n'.join(lines)[:3900]
    for code, (group, label, _default, risk, desc) in _V176_PROCESS_DEFS.items():
        if group != page:
            continue
        mark = '🔥' if risk == 'hot' else '⚠️' if risk == 'critical' else ''
        lines.append(f'\n{_v176_status_icon(code)} {label} {mark}\n{desc}')
    if page == 'ui':
        lines += ['', '🔥 = особенно полезно проверить при медленных кнопках.']
    if page == 'mega':
        lines += ['', '⚠️ Критические пункты можно отключить вручную для теста, но это снижает устойчивость к deploy/restart.']
    return '\n'.join(lines)[:3900]

def _v176_nav_row(page: str):
    order = [('ui', '⚡ UI')]
    if storage_profile_v237_1() == STORAGE_PROFILE_MEGA_V237_1:
        order.append(('mega', '☁️ MEGA'))
    order += [('auto', '🔄 Авто'), ('system', '🧠 RAM'), ('core', '🔒 Ядро')]
    return [IB(('• ' if p == page else '') + label, callback_data=f'v176:p:{p}') for p, label in order]

def _v176_menu_keyboard(page: str='ui'):
    if page == 'mega' and storage_profile_v237_1() != STORAGE_PROFILE_MEGA_V237_1:
        page = 'ui'
    kb = types.InlineKeyboardMarkup()
    kb.row(*_v176_nav_row(page))
    if page != 'core':
        for code, (group, label, _default, _risk, _desc) in _V176_PROCESS_DEFS.items():
            if group == page:
                kb.row(IB(f'{_v176_status_icon(code)} {label}', callback_data=f'v176:t:{code}'))
    kb.row(IB('⚡ Быстрый тест', callback_data='v176:profile:fast'), IB('🧱 Всё ВКЛ', callback_data='v176:profile:all'))
    kb.row(IB('🧪 Минимум', callback_data='v176:profile:minimal'), IB('📊 Скорость кнопок', callback_data='v176:speed'))
    kb.row(IB('⬅️ Режимы', callback_data='v240:modes:open'), IB('✖️ Закрыть', callback_data='info_close'))
    return kb

def _v176_speed_keyboard():
    kb = types.InlineKeyboardMarkup()
    kb.row(IB('🔄 Обновить замер', callback_data='v176:speed'), IB('🧹 Очистить замер', callback_data='v176:speed_clear'))
    kb.row(IB('⬅️ Процессы', callback_data='v176:menu'), IB('✖️ Закрыть', callback_data='info_close'))
    return kb
V196_BRANCH_REGISTRY_KEY = 'protected_branches_registry'
V196_BRANCH_SCHEMA = 1
V196_BRANCH_PAGE_SIZE = 5
V196_BRANCH_CATALOG = {'finance.ars': {'group': '💰 Финансы', 'title': 'ARS · основной учёт', 'rev': 1, 'purpose': 'Принимать, хранить и считать финансовые операции в аргентинских песо.', 'entry': ['финансовый текст', 'редактирование/удаление записи', 'финансовые окна'], 'flow': ['ввод → распознавание', 'record.amount → SQLite', 'Constitution witness', 'один finalize → UI'], 'storage': ['records/daily_records', 'record.amount', 'finance integrity ledger'], 'depends': ['storage.sqlite', 'storage.constitution', 'ui.main'], 'invariants': ['record.amount — бухгалтерский источник истины ARS; старый текст не переразбирается для повторного расчёта', 'USD не попадает в ARS-суммы', 'одна логическая операция не создаёт дубль', 'финансовая запись переживает restart/deploy через durable storage'], 'tests': ['ARS add/edit/delete', 'duplicate guard', 'restart replay', 'ARS/USD isolation']}, 'finance.usd': {'group': '💰 Финансы', 'title': 'USD · независимый учёт', 'rev': 1, 'purpose': 'Вести долларовые операции независимо от ARS.', 'entry': ['USD финансовый ввод', 'USD операции', 'USD окна'], 'flow': ['USD ввод → USD record', 'USD ledger', 'USD итог/окно/export'], 'storage': ['usd_records / canonical USD ledger', 'usd_amount'], 'depends': ['finance.ars', 'storage.sqlite'], 'invariants': ['USD и ARS не складываются', 'чистый USD не создаёт фиктивный ARS', 'исторические ARS-клоны не считаются USD'], 'tests': ['pure USD', 'mixed ARS+USD', 'polluted legacy USD filter']}, 'finance.balance': {'group': '💰 Финансы', 'title': 'Остаток / с ост', 'rev': 2, 'purpose': 'Показывать остаток начала дня и остаток после каждой операции.', 'entry': ['кнопка «с ост»', 'remaining_open:*', 'переход день ←/→'], 'flow': ['выбранный день', 'opening = закрытие предыдущего дня', 'операции дня по порядку', 'текущий остаток'], 'storage': ['record.amount', 'gomonk settings'], 'depends': ['finance.ars', 'finance.gomonk', 'ui.main'], 'invariants': ['остаток с прошлого раза = фактический остаток на конец предыдущего дня', 'финансовый текст не переразбирается для восстановления суммы', 'переключение гомонковых не меняет ledger', 'день окна не меняется фоновым finalize'], 'tests': ['previous-day carry', '11.08→12.08 carry', 'remaining rows', 'gomonk ON/OFF idempotent']}, 'finance.gomonk': {'group': '💰 Финансы', 'title': 'Гомонковые ARS/USD', 'rev': 2, 'purpose': 'Отдельно учитывать резерв/гомонковые для ARS и USD.', 'entry': ['кнопки гомонковых', 'remaining SET ON/OFF', 'Инфо'], 'flow': ['явное состояние ON/OFF', 'вычет только при отображении/расчёте', 'persist setting'], 'storage': ['ARS gomonk settings', 'USD gomonk settings'], 'depends': ['finance.balance'], 'invariants': ['ARS/USD гомонковые независимы', 'toggle идемпотентный SET, не слепая инверсия', 'ledger не изменяется'], 'tests': ['SET ON twice', 'SET OFF twice', 'ARS/USD independence']}, 'finance.records': {'group': '💰 Финансы', 'title': 'Записи · редактирование/удаление', 'rev': 1, 'purpose': 'Безопасно изменять существующие финансовые записи.', 'entry': ['редактор записей', 'edited Telegram message', 'delete/bulk delete'], 'flow': ['выбор записи', 'изменение', 'integrity ledger', 'rebuild derived state'], 'storage': ['records', 'finance integrity ledger'], 'depends': ['finance.ars', 'storage.constitution'], 'invariants': ['каждое изменение имеет witness', 'удаление не затрагивает чужие записи', 'derived indexes перестраиваются'], 'tests': ['edit', 'delete', 'bulk delete', 'integrity event']}, 'export.excel': {'group': '📊 Таблицы', 'title': 'Excel · единый ARS/USD', 'rev': 4, 'purpose': 'Строить все XLSX из одного канонического набора финансовых данных.', 'entry': ['Excel', 'Excel статьи', '/tabl_lsx', 'monthly XLSX', 'Telegram download'], 'flow': ['period bounds', 'canonical ARS/USD', 'opening balance', 'formulas', 'OOXML validation', 'delivery'], 'storage': ['finance ledgers', 'category overrides'], 'depends': ['finance.ars', 'finance.usd', 'finance.balance'], 'invariants': ['исправление Excel применяется ко всем Excel-путям и всем контурам', 'ARS/USD рассчитываются отдельно', 'остаток начала периода един для Excel/CSV/Google/UI', 'USD формулы не ссылаются на ARS-блок', 'операция с описанием «приход/расход» не является служебной итоговой строкой'], 'tests': ['all periods', 'formula refs', 'opening carry', 'category override', 'Telegram workbook']}, 'export.csv': {'group': '📊 Таблицы', 'title': 'CSV · единый расчёт', 'rev': 2, 'purpose': 'Выгружать CSV с тем же каноническим расчётом, что Excel.', 'entry': ['CSV день/неделя/месяц/Чт–Ср/всё'], 'flow': ['period → canonical records → opening/totals → file'], 'storage': ['finance ledgers'], 'depends': ['export.excel'], 'invariants': ['CSV не имеет отдельной бухгалтерской логики', 'ARS/USD не смешиваются', 'opening совпадает с Excel'], 'tests': ['period parity with Excel', 'delivery']}, 'export.google': {'group': '📊 Таблицы', 'title': 'Google Sheets / Drive', 'rev': 3, 'purpose': 'Заливать тот же отчёт, который скачивается в Telegram.', 'entry': ['Залить в Google Sheets', 'Google Drive', 'авто Чт–Ср'], 'flow': ['canonical workbook/data → Google upload → delivery proof'], 'storage': ['Google config', 'same export dataset'], 'depends': ['export.excel', 'export.csv'], 'invariants': ['Google и Telegram одного периода получают один источник данных', 'Google не пересчитывает ошибочные межблочные ссылки', 'успех подтверждается отдельно от Telegram send_document'], 'tests': ['Telegram/Google parity', 'external delivery proof', 'Thu-Wed 7 days']}, 'ui.main': {'group': '🪟 Интерфейс', 'title': 'Основное окно · единственный источник UI-даты', 'rev': 11, 'purpose': 'Маршрутизировать основной UI по контуру и применять per-chat директивную owner-политику без второго набора business mode flags.', 'entry': ['/start', 'день ←/→', 'календарь', 'возврат в осн. окно'], 'flow': ['open day → primary main window', 'new main retires old', 'stale callback redirects'], 'storage': ['primary main window id/day', 'window registry'], 'depends': ['finance.ars'], 'invariants': ['одно каноническое основное окно', 'старое окно не выполняет бизнес-действие', 'finance finalize не меняет UI-день'], 'tests': ['stale main redirect', 'day navigation', 'background refresh does not resurrect old window', 'directive OFF legacy parity', 'directive enabled-only menu', 'directive stale mode block']}, 'ui.info': {'group': '🪟 Интерфейс', 'title': 'Инфо / служебные меню', 'rev': 8, 'purpose': 'Безопасно открывать диагностику и owner-настройки, включая управление директивной политикой конкретных чатов Контур 1/2.', 'entry': ['ℹ️ Инфо', 'служебные callbacks'], 'flow': ['Info → submenu → back/close'], 'storage': ['owner/global settings'], 'depends': ['ui.main', 'diagnostics.journal'], 'invariants': ['права владельца соблюдаются', 'служебное меню не меняет финансы', 'ветки доступны из Инфо', 'Ф233 — единое служебное окно для файлового прогресса и коротких helper-сообщений; новые Ф234 не создаются'], 'tests': ['owner menu', 'back/close', 'branches entry', 'F233 unified service window', 'directive owner-only list/card', 'directive mode mutation', 'local annotation gate']}, 'ui.chat_identity': {'group': '🪟 Интерфейс', 'title': 'Чаты · реальные имена / полная проверка', 'rev': 2, 'purpose': 'Хранить и показывать реальную Telegram-идентичность каждого известного чата и по кнопке полностью синхронизировать доступные изменения.', 'entry': ['Пересылка → 📡 Проверить чаты', 'getChat', 'обычные Telegram updates'], 'flow': ['known chat ids', 'getChat including primary owner', 'detect migration/unreachable state', 'canonicalize old→new chat id across control-plane data', 'canonical title/username/type', 'bot-visible metadata/rights', 'persist + one config backup'], 'storage': ['chat.info', 'owner known_chats', 'last_chat_probe_summary_v197', 'chat_id_aliases_v199', 'tenant/reminder/task references'], 'depends': ['forward.core', 'multitenant.core'], 'invariants': ['роль владельца не подменяет имя чата emoji', 'owner chat тоже проходит полную проверку', 'группа/канал используют Telegram title, private — реальное имя/username', 'проверка не переименовывает Telegram-чат — только синхронизирует локальную карточку', 'недоступный чат помечается отдельно, его последнее известное имя не заменяется ID без необходимости', 'upgrade basic group→supergroup переносит старый ID на новый во всех известных control-plane ссылках и убирает старый дубль из активных меню', 'fallback по одинаковому названию используется только после явного Telegram upgraded-error и только при одном уникальном supergroup-кандидате; при неоднозначности бот не угадывает'], 'tests': ['owner title replaces legacy basketball', 'all-known includes owner', 'group/private title authority', 'metadata refresh', 'removed/access state', 'ResponseParameters migration', 'upgraded-error unique successor', 'ambiguous successor no-guess', 'tenant/reminder/task migration']}, 'restore.strict': {'group': '♻️ Восстановление', 'title': '/restore · REPLACE FROM FILE', 'rev': 3, 'purpose': 'Восстанавливать выбранный scope ровно из backup без merge с live-состоянием.', 'entry': ['/restore', 'JSON/ISON', 'GZ/SQLite', 'CSV finance'], 'flow': ['validate', 'mandatory pre_restore', 'clear scope', 'replace from file', 'rehydrate', 'Constitution checkpoint'], 'storage': ['pre_restore', 'SQLite', 'generation/checkpoint'], 'depends': ['storage.constitution', 'storage.mega'], 'invariants': ['никакого автоматического merge', 'pre_restore обязателен', 'восстановленный файл — источник истины', 'derived caches можно пересчитать, бизнес-данные нельзя подмешать'], 'tests': ['JSON exact replace', 'GZ schema validation', 'forward edges exact', 'pre_restore gate']}, 'restore.careful': {'group': '♻️ Восстановление', 'title': 'Аккуратное восстановление', 'rev': 2, 'purpose': 'Ручное дозаполнение отсутствующих дней после строгого restore.', 'entry': ['Инфо → 🩹 Аккуратное восстановление', 'ручной финансовый ввод'], 'flow': ['enable', 'target = primary main day', 'accepted finance → target day', '120s inactivity → OFF'], 'storage': ['RAM-only mode', 'normal finance ledger for accepted values'], 'depends': ['ui.main', 'finance.ars'], 'invariants': ['не является merge', 'target только канонический день main window', 'restart выключает режим', 'каждая принятая сумма продлевает 120s'], 'tests': ['target day', 'timeout', 'normal input outside mode']}, 'storage.sqlite': {'group': '💾 Хранилище', 'title': 'SQLite · рабочее состояние', 'rev': 1, 'purpose': 'Хранить материализованное рабочее состояние на текущем экземпляре Render.', 'entry': ['load/save state', 'snapshot'], 'flow': ['RAM ↔ SQLite', 'snapshot → MEGA'], 'storage': ['SQLite tables kv/chats/meta/cold_fields'], 'depends': [], 'invariants': ['локальный Render disk не считается долговечным', 'SQLite integrity проверяется', 'low-RAM cold fields сохраняются'], 'tests': ['quick_check', 'save/load', 'cold field roundtrip']}, 'storage.mega': {'group': '💾 Хранилище', 'title': 'MEGA · durable storage', 'rev': 3, 'purpose': 'Переживать deploy/restart и хранить долговечные snapshots/tasks/deltas.', 'entry': ['durable witness', 'delta', 'generation', 'runtime backup'], 'flow': ['small witness → background ledger/delta → verified full snapshot'], 'storage': [str(globals().get('MEGA_BACKUP_DIR') or '')], 'depends': ['storage.sqlite'], 'invariants': ['единственный immutable canonical root = MEGA_BACKUP_DIR', 'runtime не меняет root после load_data', 'пропавший active path пересоздаётся'], 'tests': ['root self-heal', 'one-put hot path', 'restart recovery']}, 'storage.delta': {'group': '💾 Хранилище', 'title': 'MEGA delta · compact WAL', 'rev': 2, 'purpose': 'Закрывать промежуток между полными SQLite generations маленькими изменениями.', 'entry': ['state change', 'scheduled delta'], 'flow': ['coalesce → compact payload → MEGA → prune after verified snapshot'], 'storage': [str(globals().get('MEGA_BACKUP_DIR') or '') + '/deltas'], 'depends': ['storage.mega', 'storage.constitution'], 'invariants': ['не копировать растущие operation ledger histories', 'delta остаётся компактной', 'не удалять recovery bridge до проверенного snapshot'], 'tests': ['real delta size', 'coalescing', 'retention']}, 'storage.constitution': {'group': '💾 Хранилище', 'title': 'DATA CONSTITUTION', 'rev': 3, 'purpose': 'Защищать финансовую историю от тихой семантической потери.', 'entry': ['finance mutation', 'snapshot publish', 'boot restore', 'manual restore'], 'flow': ['immutable witness', 'semantic manifest', 'generation', 'quarantine on unexplained loss'], 'storage': ['ledger', 'database/generations', 'manifests/current_manifest'], 'depends': ['storage.sqlite', 'storage.mega'], 'invariants': ['SQLite integrity недостаточно — нужна semantic completeness', 'unexplained history loss → quarantine', 'restore creates checkpoint/reanchor'], 'tests': ['semantic loss rejection', 'generation fallback', 'restore reanchor', 'protected symbols']}, 'forward.core': {'group': '🔁 Пересылка', 'title': 'Пересылка · правила/доставка', 'rev': 2, 'purpose': 'Пересылать разрешённый контент между настроенными чатами без дублей.', 'entry': ['forward rules', 'message router'], 'flow': ['source message → rule → durable task → destination', 'delivery error → independent chat probe → migrate / suspend / transient', 'terminal dead target leaves durable ambiguity loop'], 'storage': ['forward_rules/edges', 'durable tasks', 'forward_suspended_targets_v199', 'chat_id_aliases_v199'], 'depends': ['storage.mega'], 'invariants': ['нет дублей', 'правила других чатов не повреждаются', 'restore edges exact', 'одиночная ошибка отправки не удаляет правило: недоступность подтверждается отдельным Telegram getChat', 'подтверждённо мёртвый destination приостанавливается один раз; правило хранится обратимо и не создаёт бесконечный durable retry', 'при подтверждённой миграции old chat id все связи переходят на canonical new chat id'], 'tests': ['single forward', 'duplicate guard', 'restore edges', 'chat-not-found independent confirmation', 'suspend once/no spam', 'durable terminal completion', 'reactivate after successful probe', 'group→supergroup forwarding migration']}, 'forward.media': {'group': '🔁 Пересылка', 'title': 'Пересылка · media groups', 'rev': 1, 'purpose': 'Собирать и доставлять Telegram media_group как логическую группу.', 'entry': ['photo/video album'], 'flow': ['collect media_group → finalize → durable delivery'], 'storage': ['media group state/tasks'], 'depends': ['forward.core'], 'invariants': ['группа не дробится на дубли', 'restart не теряет durable delivery'], 'tests': ['album collect', 'restart', 'duplicate group']}, 'tasks.dispatcher': {'group': '📋 Задачи', 'title': 'Диспетчер задач', 'rev': 1, 'purpose': 'Создавать, вести и завершать задачи в выбранных чатах.', 'entry': ['Task Dispatcher buttons', 'task messages'], 'flow': ['create → active → action/result → close/archive'], 'storage': ['task state', 'durable task metadata'], 'depends': ['storage.mega', 'multitenant.core'], 'invariants': ['каждая задача имеет начало/состояние/завершение', 'выбор чатов соблюдается', 'restart не теряет критическое состояние'], 'tests': ['create', 'selected chats', 'close', 'restart']}, 'reminders.core': {'group': '⏰ Напоминания', 'title': 'Напоминания', 'rev': 1, 'purpose': 'Надёжно планировать и доставлять напоминания.', 'entry': ['reminder commands/UI', 'scheduler'], 'flow': ['create → scheduler → delivery → next/complete'], 'storage': ['reminders state'], 'depends': ['storage.sqlite', 'storage.mega'], 'invariants': ['не теряются после restart', 'не дублируются при replay', 'очередь имеет завершение'], 'tests': ['one-shot', 'recurring', 'restart', 'dedupe']}, 'multitenant.core': {'group': '🏢 Доступ', 'title': 'Пространства / круги / роли', 'rev': 3, 'purpose': 'Изолировать владельца, пространства и доступные пользователям функции; per-chat directive policy остаётся строго chat_id/contour scoped.', 'entry': ['space menu', 'permissions', 'circle views'], 'flow': ['actor → tenant/role → permission → operation'], 'storage': ['tenant/owner scope', 'permissions'], 'depends': [], 'invariants': ['данные пространств не смешиваются', 'глобальные исправления функций действуют во всех контурах где функция доступна', 'owner-only операции закрыты'], 'tests': ['owner', 'circle1', 'circle2', 'permission deny', 'directive chat isolation', 'circle1/circle2 directive independence', 'owner-only directive mutation']}, 'diagnostics.journal': {'group': '🩺 Диагностика', 'title': 'Журналы / диагностика', 'rev': 3, 'purpose': 'Фиксировать ошибки, события, скорость и давать скачиваемые журналы.', 'entry': ['Инфо → Журнал', 'runtime events', 'download'], 'flow': ['event → runtime journal → optional MEGA → download'], 'storage': ['journal buffers/files', 'journal_download_base_name'], 'depends': ['storage.mega'], 'invariants': ['диагностика не выключается Fast Test/Minimum автоматически', 'имя скачиваемого журнала сохраняется', 'битая remote строка не ломает runtime', 'технические аварийные уведомления и 🚨 видит только основной OWNER_ID; другие контуры не получают внутренние W/Ф/диагностические helper-сообщения'], 'tests': ['current/full journal', 'custom filename', 'warm tail', 'owner-only technical alerts', 'non-owner contour has no W/Ф/🚨 diagnostic helper']}, 'runtime.performance': {'group': '🩺 Диагностика', 'title': 'Процессы / скорость', 'rev': 1, 'purpose': 'Измерять UI latency и управлять необязательными тяжёлыми процессами.', 'entry': ['Инфо → Процессы / скорость'], 'flow': ['toggle optional process → repeat transitions → P50/P90'], 'storage': ['process_control_v176'], 'depends': ['diagnostics.journal'], 'invariants': ['ядро бота нельзя выключить диагностикой', 'финансы/пересылка/SQLite остаются core', 'diagnostics remain available in test profiles'], 'tests': ['profile fast', 'profile minimal', 'locked core']}, 'secret.core': {'group': '🔐 Прочее', 'title': 'SECRET / скрытые функции', 'rev': 1, 'purpose': 'Сохранять штатную SECRET-функциональность и её доступы.', 'entry': ['SECRET controls/messages'], 'flow': ['permission → action → persist'], 'storage': ['secret settings/notes'], 'depends': ['multitenant.core'], 'invariants': ['не отключается меню диагностики', 'доступы соблюдаются'], 'tests': ['permission', 'persistence']}, 'system.branch_registry': {'group': '🛡 Защита', 'title': 'Ветки функций / контракты', 'rev': 1, 'purpose': 'Позволять владельцу фиксировать проверенные функциональные ветки как защищённые контракты.', 'entry': ['Инфо → 🌿 Ветки', 'галочка ветки', 'скачать журнал веток'], 'flow': ['карточка → пользователь проверил → ✅ fix → persistent contract snapshot → regression gate'], 'storage': ['_global_settings.protected_branches_registry', 'downloadable branch journal'], 'depends': ['ui.info', 'storage.sqlite', 'storage.mega'], 'invariants': ['галочка переживает restart/deploy/restore', 'фиксируется семантический контракт, не только hash кода', 'будущая смена contract rev видна как ⚠️', 'снятие защиты — только явной кнопкой владельца'], 'tests': ['toggle/persist', 'contract hash', 'journal export', 'future-version carry']}, 'system.release_gate': {'group': '🛡 Защита', 'title': 'Release Gate · проверка А→Я', 'rev': 1, 'purpose': 'Не выпускать релиз, пока изменённые функции не проверены от точки входа до конечного результата в финальном runtime namespace.', 'entry': ['сборка каждого релиза', 'изменённые callback/command/background пути'], 'flow': ['STATIC → final runtime namespace/signatures → call-sites → E2E route → background completion/failure → protected regression → package verify'], 'storage': ['RUNTIME_CONTRACTS.json', 'END_TO_END_REPORT_v199.json', 'TEST_REPORT release'], 'depends': ['system.branch_registry', 'diagnostics.journal'], 'invariants': ['позднее переопределение публичной функции не может пройти незамеченным', 'реальная финальная сигнатура совместима со всеми call-sites', 'изменённая ветка проверяется до конечного результата, включая background', 'любое нарушение защищённого контракта блокирует PASS релиза'], 'tests': ['loader-order namespace', 'signature/callsite compatibility', 'changed-route E2E', 'negative/failure path', 'protected branch regression', 'fresh ZIP verify']}}
V196_CURRENT_BRANCH_CHANGES = [('ui.chat_identity', 'Чаты получили полный lifecycle: old group→supergroup migration, canonical ID, удаление дублей из активных реестров и исправление финальной runtime-сигнатуры массовой проверки.'), ('forward.core', 'Недоступная цель пересылки теперь независимо проверяется: миграция переносится, подтверждённо мёртвый target приостанавливается один раз с обратимым сохранением правил и без бесконечного durable retry.'), ('ui.info', 'Ф233 и Ф234 объединены: файловый прогресс и короткие служебные сообщения используют одно служебное окно Ф233; новые Ф234 не создаются.'), ('system.release_gate', 'Добавлен обязательный Release Gate А→Я: финальный loader-order namespace, сигнатуры/call-sites, E2E и failure-path тесты, protected-branch regression и fresh-ZIP verify.')]
V196_BRANCH_REGRESSION_RESULTS = {'ui.chat_identity': 'PASS', 'forward.core': 'PASS', 'ui.info': 'PASS', 'system.release_gate': 'PASS'}

def _v196_branch_contract_payload(code: str) -> dict:
    row = V196_BRANCH_CATALOG.get(str(code)) or {}
    return {'id': str(code), 'group': row.get('group'), 'title': row.get('title'), 'rev': int(row.get('rev', 1) or 1), 'purpose': row.get('purpose'), 'entry': list(row.get('entry') or []), 'flow': list(row.get('flow') or []), 'storage': list(row.get('storage') or []), 'depends': list(row.get('depends') or []), 'invariants': list(row.get('invariants') or []), 'tests': list(row.get('tests') or [])}

def _v196_branch_contract_hash(code: str) -> str:
    raw = _v176_json.dumps(_v196_branch_contract_payload(code), ensure_ascii=False, sort_keys=True, separators=(',', ':'))
    return _v196_hashlib.sha256(raw.encode('utf-8')).hexdigest()

def _v196_branch_root() -> dict:
    try:
        gs = data.setdefault('_global_settings', {})
        root = gs.setdefault(V196_BRANCH_REGISTRY_KEY, {})
    except Exception:
        return {'schema': V196_BRANCH_SCHEMA, 'protected': {}, 'history': []}
    if not isinstance(root, dict):
        root = {}
        gs[V196_BRANCH_REGISTRY_KEY] = root
    root.setdefault('schema', V196_BRANCH_SCHEMA)
    root.setdefault('protected', {})
    root.setdefault('history', [])
    return root

def _v196_branch_is_protected(code: str) -> bool:
    try:
        return str(code) in (_v196_branch_root().get('protected') or {})
    except Exception:
        return False

def _v196_branch_contract_changed(code: str) -> bool:
    try:
        saved = (_v196_branch_root().get('protected') or {}).get(str(code)) or {}
        if not saved:
            return False
        return str(saved.get('contract_hash') or '') != _v196_branch_contract_hash(code)
    except Exception:
        return True

def _v196_branch_status_icon(code: str) -> str:
    if not _v196_branch_is_protected(code):
        return '☐'
    return '⚠️' if _v196_branch_contract_changed(code) else '✅'

def _v196_branch_persist(reason: str='branches') -> None:
    try:
        SQLITE.save_root(_sqlite_pack_root(data))
    except Exception:
        try:
            save_data(data, root_only=True)
        except Exception:
            pass
    try:
        schedule_config_backup_for_chats(int(OWNER_ID or 0), delay=0.2)
    except Exception:
        pass
    try:
        schedule_delta_backup(int(OWNER_ID or 0), delay=0.5, reason=f'protected_branches:{reason}')
    except Exception:
        pass

def _v196_branch_set(code: str, enabled: bool) -> bool:
    code = str(code)
    if code not in V196_BRANCH_CATALOG:
        return False
    root = _v196_branch_root()
    protected = root.setdefault('protected', {})
    now_s = now_local().isoformat(timespec='seconds') if 'now_local' in globals() else ''
    if enabled:
        snapshot = _v196_branch_contract_payload(code)
        snapshot.update({'contract_hash': _v196_branch_contract_hash(code), 'confirmed_version': str(globals().get('VERSION') or ''), 'confirmed_at': now_s, 'confirmed_by': int(OWNER_ID or 0)})
        protected[code] = snapshot
        action = 'protect'
    else:
        protected.pop(code, None)
        action = 'unprotect'
    hist = root.setdefault('history', [])
    hist.append({'ts': now_s, 'action': action, 'branch': code, 'version': str(globals().get('VERSION') or '')})
    if len(hist) > 200:
        del hist[:-200]
    root['last_changed_at'] = now_s
    root['last_changed_version'] = str(globals().get('VERSION') or '')
    _v196_branch_persist(f'{action}:{code}')
    try:
        bot_journal('protected_branch_v196', int(OWNER_ID or 0), f'action={action}; branch={code}; hash={_v196_branch_contract_hash(code)[:12]}')
    except Exception:
        pass
    return True

def protected_branches_contract_mismatches() -> list[str]:
    out = []
    for code in list((_v196_branch_root().get('protected') or {}).keys()):
        if code not in V196_BRANCH_CATALOG or _v196_branch_contract_changed(code):
            out.append(str(code))
    return out

def _v196_current_change_codes() -> set[str]:
    return {str(code) for code, _text in V196_CURRENT_BRANCH_CHANGES}

def build_protected_branches_text(page: int=0) -> str:
    codes = list(V196_BRANCH_CATALOG.keys())
    pages = max(1, (len(codes) + V196_BRANCH_PAGE_SIZE - 1) // V196_BRANCH_PAGE_SIZE)
    page = max(0, min(int(page or 0), pages - 1))
    protected = _v196_branch_root().get('protected') or {}
    mismatches = protected_branches_contract_mismatches()
    lines = ['🌿 ВЕТКИ ФУНКЦИЙ / ЗАЩИТА', f"Версия: {globals().get('VERSION') or ''}", f'Зафиксировано: {len(protected)}/{len(V196_BRANCH_CATALOG)} · страница {page + 1}/{pages}', '', '✅ защищено · ☐ не зафиксировано · ⚠️ контракт изменился после фиксации', 'Галочка = вы подтвердили ветку тестами. В будущих версиях она остаётся защищённой.', '', '🛠 ВЕТКИ ПРАВОК ТЕКУЩЕЙ ВЕРСИИ:']
    for code, text in V196_CURRENT_BRANCH_CHANGES:
        row = V196_BRANCH_CATALOG.get(code) or {}
        result = str(V196_BRANCH_REGRESSION_RESULTS.get(code) or 'NO TEST')
        lines.append(f"{_v196_branch_status_icon(code)} {row.get('title') or code} · regression {result}\n   {text}")
    if mismatches:
        lines += ['', '⚠️ ВНИМАНИЕ: изменились подтверждённые контракты: ' + ', '.join(mismatches[:8])]
    lines += ['', 'Ветки на этой странице:']
    for code in codes[page * V196_BRANCH_PAGE_SIZE:(page + 1) * V196_BRANCH_PAGE_SIZE]:
        row = V196_BRANCH_CATALOG[code]
        touched = ' 🛠' if code in _v196_current_change_codes() else ''
        lines.append(f"{_v196_branch_status_icon(code)}{touched} {row['group']} / {row['title']} · contract r{row.get('rev', 1)}")
    return '\n'.join(lines)[:3900]

def build_protected_branches_keyboard(page: int=0):
    codes = list(V196_BRANCH_CATALOG.keys())
    pages = max(1, (len(codes) + V196_BRANCH_PAGE_SIZE - 1) // V196_BRANCH_PAGE_SIZE)
    page = max(0, min(int(page or 0), pages - 1))
    kb = types.InlineKeyboardMarkup(row_width=2)
    for code in codes[page * V196_BRANCH_PAGE_SIZE:(page + 1) * V196_BRANCH_PAGE_SIZE]:
        row = V196_BRANCH_CATALOG[code]
        short = str(row.get('title') or code)
        if len(short) > 27:
            short = short[:26] + '…'
        kb.row(IB(f'{_v196_branch_status_icon(code)} {short}', callback_data=f'br:t:{code}'), IB('📄', callback_data=f'br:c:{code}'))
    nav = []
    if page > 0:
        nav.append(IB('⬅️', callback_data=f'br:p:{page - 1}'))
    nav.append(IB(f'{page + 1}/{pages}', callback_data='none'))
    if page + 1 < pages:
        nav.append(IB('➡️', callback_data=f'br:p:{page + 1}'))
    kb.row(*nav)
    kb.row(IB('🛠 Правки версии', callback_data='br:changes'), IB('📥 Скачать ветки', callback_data='br:dl'))
    day = get_chat_store(int(OWNER_ID or 0)).get('current_view_day', today_key())
    kb.row(IB('🔙 Назад в Инфо', callback_data=f'd:{day}:info'), IB('❌ Закрыть', callback_data='info_close'))
    return kb

def build_protected_branch_card(code: str) -> str:
    code = str(code)
    row = V196_BRANCH_CATALOG.get(code)
    if not row:
        return '❌ Неизвестная ветка.'
    saved = (_v196_branch_root().get('protected') or {}).get(code) or {}
    lines = [f"{_v196_branch_status_icon(code)} 🌿 {row['title']}", f"ID: {code} · {row['group']} · contract r{row.get('rev', 1)}", f"Статус: {('ЗАЩИЩЕНО' if saved else 'не зафиксировано')}"]
    if saved:
        lines.append(f"Подтверждено: {saved.get('confirmed_version', '')} · {saved.get('confirmed_at', '')}")
        lines.append(f"Contract hash: {str(saved.get('contract_hash') or '')[:16]}")
    lines += ['', 'Суть:', str(row.get('purpose') or ''), '', 'Входы:']
    lines += [f'• {x}' for x in row.get('entry') or []]
    lines += ['', 'Рабочая цепочка:'] + [f'• {x}' for x in row.get('flow') or []]
    lines += ['', 'НЕЛЬЗЯ ЛОМАТЬ:'] + [f'• {x}' for x in row.get('invariants') or []]
    lines += ['', 'Регрессия:'] + [f'• {x}' for x in row.get('tests') or []]
    if row.get('depends'):
        lines += ['', 'Зависимости: ' + ', '.join(row.get('depends') or [])]
    return '\n'.join(lines)[:3900]

def build_protected_branch_card_keyboard(code: str, page: int=0):
    code = str(code)
    kb = types.InlineKeyboardMarkup()
    protected = _v196_branch_is_protected(code)
    label = '☐ Снять защиту' if protected else '✅ Зафиксировать ветку'
    kb.row(IB(label, callback_data=f'br:t:{code}'))
    kb.row(IB('🔙 К списку веток', callback_data=f'br:p:{max(0, int(page or 0))}'), IB('📥 Скачать', callback_data='br:dl'))
    return kb

def build_protected_branches_changes_text() -> str:
    lines = ['🛠 ВЕТКИ ПРАВОК ТЕКУЩЕЙ ВЕРСИИ', f"Версия: {globals().get('VERSION') or ''}", '']
    for code, text in V196_CURRENT_BRANCH_CHANGES:
        row = V196_BRANCH_CATALOG.get(code) or {}
        lines += [f"{_v196_branch_status_icon(code)} {row.get('title') or code}", f"Regression: {V196_BRANCH_REGRESSION_RESULTS.get(code, 'NO TEST')}", text, '']
    lines += ['✅ в этой строке означает: ветка была ранее/сейчас зафиксирована владельцем и продолжает идти в следующих версиях с защитой.']
    return '\n'.join(lines)[:3900]

def _v196_branch_export_payload() -> dict:
    root = _v196_branch_root()
    branches = []
    for code, row in V196_BRANCH_CATALOG.items():
        current = _v196_branch_contract_payload(code)
        current['current_contract_hash'] = _v196_branch_contract_hash(code)
        current['protected'] = _v196_branch_is_protected(code)
        current['contract_changed_since_confirmation'] = _v196_branch_contract_changed(code)
        current['confirmed_snapshot'] = (root.get('protected') or {}).get(code)
        branches.append(current)
    return {'format': 'telegram_bot_protected_branches_journal_v1', 'schema': V196_BRANCH_SCHEMA, 'generated_at': now_local().isoformat(timespec='seconds') if 'now_local' in globals() else '', 'bot_version': str(globals().get('VERSION') or ''), 'current_version_changes': [{'branch': c, 'summary': t, 'regression': V196_BRANCH_REGRESSION_RESULTS.get(c)} for c, t in V196_CURRENT_BRANCH_CHANGES], 'registry': root, 'branches': branches}

def build_protected_branches_journal_text() -> str:
    payload = _v196_branch_export_payload()
    lines = ['🌿 ЖУРНАЛ ЗАЩИЩЁННЫХ ВЕТОК TELEGRAM-БОТА', f"Версия: {payload['bot_version']}", f"Создан: {payload['generated_at']}", f"Зафиксировано: {sum((1 for b in payload['branches'] if b['protected']))}/{len(payload['branches'])}", '=' * 78, '', 'ПРАВКИ ТЕКУЩЕЙ ВЕРСИИ:']
    for item in payload['current_version_changes']:
        lines.append(f"- {item['branch']} [{item.get('regression')}] — {item['summary']}")
    lines += ['', 'КАРТОЧКИ ВЕТОК:']
    for b in payload['branches']:
        lines += ['', '-' * 78, f"{('✅' if b['protected'] else '☐')} {b['id']} — {b['title']} · {b['group']} · r{b['rev']}", f"Суть: {b['purpose']}"]
        if b['protected']:
            snap = b.get('confirmed_snapshot') or {}
            lines.append(f"Подтверждено: {snap.get('confirmed_version', '')} · {snap.get('confirmed_at', '')} · hash {str(snap.get('contract_hash') or '')[:16]}")
        lines.append('Нельзя ломать:')
        lines += [f'  • {x}' for x in b.get('invariants') or []]
        lines.append('Регрессионные тесты:')
        lines += [f'  • {x}' for x in b.get('tests') or []]
    lines += ['', '=' * 78, 'MACHINE_JSON', _v176_json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True)]
    return '\n'.join(lines) + '\n'

def send_protected_branches_journal(chat_id: int) -> bool:
    path = None
    try:
        stamp = now_local().strftime('%Y-%m-%d_%H-%M-%S') if 'now_local' in globals() else str(int(_v176_time.time()))
        path = _v196_os.path.join(_v196_tempfile.gettempdir(), f'Журнал_защищённых_веток_{stamp}.txt')
        with open(path, 'w', encoding='utf-8') as fh:
            fh.write(build_protected_branches_journal_text())
        with open(path, 'rb') as fh:
            bot.send_document(int(chat_id), fh, caption='🌿 Журнал защищённых веток. Этот файл можно передать ChatGPT как контракт бота.')
        try:
            bot_journal('protected_branches_download_v196', int(chat_id), f'file={_v196_os.path.basename(path)}')
        except Exception:
            pass
        return True
    except Exception as exc:
        try:
            log_error(f'protected branches journal export: {exc}')
        except Exception:
            pass
        try:
            send_and_auto_delete(int(chat_id), f'❌ Не удалось скачать журнал веток: {str(exc)[:300]}', 15)
        except Exception:
            pass
        return False
    finally:
        if path:
            try:
                _v196_os.remove(path)
            except Exception:
                pass

def _v196_branch_owner_ok(call) -> bool:
    try:
        return int(call.message.chat.id) == int(OWNER_ID or 0) and int(getattr(getattr(call, 'from_user', None), 'id', 0) or 0) == int(OWNER_ID or 0)
    except Exception:
        return False

def _v196_branch_callback_filter(call) -> bool:
    return str(getattr(call, 'data', '') or '').startswith('br:')

def _v196_branch_callback(call):
    raw = str(getattr(call, 'data', '') or '')
    if not _v196_branch_owner_ok(call):
        try:
            bot.answer_callback_query(call.id, 'Только основной владелец.', show_alert=True)
        except Exception:
            pass
        return
    chat_id = int(call.message.chat.id)
    if raw == 'br:open':
        try:
            bot.answer_callback_query(call.id)
        except Exception:
            pass
        safe_edit(bot, call, build_protected_branches_text(0), reply_markup=build_protected_branches_keyboard(0))
        return
    if raw.startswith('br:p:'):
        try:
            page = int(raw.split(':', 2)[2])
        except Exception:
            page = 0
        try:
            bot.answer_callback_query(call.id)
        except Exception:
            pass
        safe_edit(bot, call, build_protected_branches_text(page), reply_markup=build_protected_branches_keyboard(page))
        return
    if raw.startswith('br:c:'):
        code = raw.split(':', 2)[2]
        codes = list(V196_BRANCH_CATALOG.keys())
        try:
            page = codes.index(code) // V196_BRANCH_PAGE_SIZE
        except Exception:
            page = 0
        try:
            bot.answer_callback_query(call.id)
        except Exception:
            pass
        safe_edit(bot, call, build_protected_branch_card(code), reply_markup=build_protected_branch_card_keyboard(code, page))
        return
    if raw.startswith('br:t:'):
        code = raw.split(':', 2)[2]
        if code not in V196_BRANCH_CATALOG:
            return
        new_state = not _v196_branch_is_protected(code)
        _v196_branch_set(code, new_state)
        try:
            bot.answer_callback_query(call.id, 'Ветка зафиксирована ✅' if new_state else 'Защита снята ☐', show_alert=False)
        except Exception:
            pass
        codes = list(V196_BRANCH_CATALOG.keys())
        try:
            page = codes.index(code) // V196_BRANCH_PAGE_SIZE
        except Exception:
            page = 0
        safe_edit(bot, call, build_protected_branches_text(page), reply_markup=build_protected_branches_keyboard(page))
        return
    if raw == 'br:changes':
        kb = types.InlineKeyboardMarkup()
        kb.row(IB('🔙 К веткам', callback_data='br:p:0'), IB('📥 Скачать', callback_data='br:dl'))
        try:
            bot.answer_callback_query(call.id)
        except Exception:
            pass
        safe_edit(bot, call, build_protected_branches_changes_text(), reply_markup=kb)
        return
    if raw == 'br:dl':
        try:
            bot.answer_callback_query(call.id, 'Формирую журнал веток…', show_alert=False)
        except Exception:
            pass
        try:
            pool = globals().get('GENERAL_TASK_POOL')
            if pool is not None:
                pool.submit('protected-branches-journal', send_protected_branches_journal, chat_id)
            else:
                send_protected_branches_journal(chat_id)
        except Exception:
            send_protected_branches_journal(chat_id)
        return
_V177_INFO_BASE_TEXT = globals().get('_v177_legacy_0054_build_info_text')
_V177_INFO_BASE_KB = globals().get('_v177_legacy_0216_build_info_keyboard')

def _canon_build_info_text__001(chat_id: int, *args, **kwargs) -> str:
    cid = int(chat_id)
    try:
        base = str(_V177_INFO_BASE_TEXT(cid) if callable(_V177_INFO_BASE_TEXT) else '')
    except Exception:
        base = ''
    try:
        if not tenant_is_platform_owner_context(cid):
            forbidden = ('/errors', '/runtime_export', '/mega_', '/queues', '/journal', '/sqlite', '/db', '/restore_guard', 'MEGA:')
            base = '\n'.join((line for line in base.splitlines() if not any((token in line for token in forbidden))))
    except Exception:
        pass
    try:
        tid = tenant_id_for_chat(cid, create=False)
        row = tenant_get(tid) or {}
        suffix = f"\n\n🏢 Пространство: {row.get('name') or tid}\n/space — чаты, пользователи и ссылки подключения"
        if tid:
            base = str(base).rstrip() + suffix
    except Exception:
        pass
    if cid == int(OWNER_ID or 0):
        rows = [r for r in str(base).splitlines() if not r.strip().startswith(('🧱 Тяжёлые процессы:', '⚡ Тяжёлые процессы:', '⚙️ Процессы / скорость:'))]
        off = sum((1 for c in _V176_PROCESS_DEFS if not v176_process_enabled(c)))
        rows += ['', f'⚙️ Процессы / скорость: отключено {off}/{len(_V176_PROCESS_DEFS)}']
        try:
            cr = careful_restore_status(cid)
            if cr.get('active'):
                rows.append(f"🩹 Аккуратное восстановление: ВКЛ → {fmt_date_ddmmyy(cr.get('day_key') or today_key())}; осталось {_format_duration_short(cr.get('remaining', 0))}")
            else:
                rows.append('🩹 Аккуратное восстановление: ВЫКЛ')
        except Exception:
            pass
        try:
            _root = _v196_branch_root()
            _protected = _root.get('protected') or {}
            _mm = protected_branches_contract_mismatches()
            rows.append(f'🌿 Ветки: защищено {len(_protected)}/{len(V196_BRANCH_CATALOG)}' + (f' · ⚠️ контрактов изменено {len(_mm)}' if _mm else ''))
        except Exception:
            pass
        base = '\n'.join(rows).strip()
    return str(base)[:3900]

def _v177_info_rows(kb):
    return list(getattr(kb, 'keyboard', None) or getattr(kb, 'inline_keyboard', None) or [])

def _v177_info_set_rows(kb, rows):
    try:
        kb.keyboard = rows
    except Exception:
        try:
            kb.inline_keyboard = rows
        except Exception:
            pass
    return kb

def _v177_info_btn_cb(btn) -> str:
    if isinstance(btn, dict):
        return str(btn.get('callback_data') or '')
    return str(getattr(btn, 'callback_data', '') or '')

def _v177_info_btn_text(btn) -> str:
    if isinstance(btn, dict):
        return str(btn.get('text') or '')
    return str(getattr(btn, 'text', '') or '')

def _canon_build_info_keyboard__001(chat_id: int):
    cid = int(chat_id)
    try:
        kb = _V177_INFO_BASE_KB(cid) if callable(_V177_INFO_BASE_KB) else types.InlineKeyboardMarkup()
    except Exception:
        kb = types.InlineKeyboardMarkup()
    rows = _v177_info_rows(kb)
    try:
        if not tenant_is_platform_owner_context(cid):
            blocked_prefixes = ('journal_', 'restore_guard', 'mega_manual_restore', 'mega_priority', 'keepalive_', 'process_center', 'safety_profile', 'problem_tasks', 'integrity_status', 'info_queues', 'runtime_watcher', 'info_delta_status', 'traffic_audit', 'additional_owners', 'addown:', 'expense_')
            clean = []
            for row in rows:
                kept = [b for b in row or [] if not _v177_info_btn_cb(b).startswith(blocked_prefixes)]
                if kept:
                    clean.append(kept)
            rows = clean
        actor = tenant_current_actor_user_id()
        role = tenant_role_for_user(actor, chat_id=cid) if actor else 'tenant_owner' if is_owner_chat(cid) else 'standard'
        if role in {'platform_owner', 'tenant_owner', 'tenant_admin', 'operator', 'viewer'}:
            if not any((_v177_info_btn_cb(b) == 'sp:dashboard' for row in rows for b in row or [])):
                rows.append([IB('🏢 Пространство', callback_data='sp:dashboard')])
    except Exception:
        pass
    for row in rows:
        for btn in row or []:
            try:
                if _v177_info_btn_cb(btn) == 'safety_profile_toggle':
                    if isinstance(btn, dict):
                        btn['callback_data'] = 'safety_profile_open'
                    else:
                        btn.callback_data = 'safety_profile_open'
            except Exception:
                pass
    blocked_process = {'v156:process_visual_toggle', 'v157:process_menu', 'v157:process_owner_toggle', 'v157:process_others_toggle'}
    clean = []
    for row in rows:
        kept = []
        for btn in row or []:
            cb = _v177_info_btn_cb(btn)
            txt = _v177_info_btn_text(btn).strip().casefold()
            if cb in blocked_process or txt.startswith('👁 окно процессов') or txt.startswith('👁️ окно процессов'):
                continue
            kept.append(btn)
        if kept:
            clean.append(kept)
    rows = clean
    start = None
    for idx, row in enumerate(rows):
        if any(('перес:' in _v177_info_btn_text(btn).casefold() for btn in row or [])):
            start = idx
            break
    if start is not None:
        rows = rows[:start] + [[btn] for row in rows[start:] for btn in row or []]
    if rows and is_owner_chat(cid):
        order = ('diag', 'storage', 'finance', 'forward', 'reminder', 'access', 'help', 'other', 'nav')
        buckets = {k: [] for k in order}
        for row in rows:
            try:
                group = _v171_info_group(row)
            except Exception:
                group = 'other'
            buckets.setdefault(group, []).append(row)
        grouped = []
        first = True
        for group in order:
            block = buckets.get(group) or []
            if not block:
                continue
            if not first and group != 'nav':
                grouped.append([IB('ㅤ', callback_data='none')])
            grouped.extend(block)
            first = False
        rows = grouped
    if cid == int(OWNER_ID or 0):
        if not any((_v177_info_btn_cb(b) == 'br:open' for row in rows for b in row or [])):
            insert_at = len(rows)
            for idx, row in enumerate(rows):
                labels = ' '.join((_v177_info_btn_text(b) for b in row or [])).casefold()
                callbacks = ' '.join((_v177_info_btn_cb(b) for b in row or []))
                if 'назад' in labels or 'закры' in labels or 'info_close' in callbacks or ('back_main' in callbacks):
                    insert_at = idx
                    break
            _pcount = len(_v196_branch_root().get('protected') or {})
            rows.insert(insert_at, [IB(f'🌿 Ветки ✅{_pcount}', callback_data='br:open')])
    if cid == int(OWNER_ID or 0):
        if not any((_v177_info_btn_cb(b) == 'careful_restore_toggle' for row in rows for b in row or [])):
            insert_at = len(rows)
            for idx, row in enumerate(rows):
                labels = ' '.join((_v177_info_btn_text(b) for b in row or [])).casefold()
                callbacks = ' '.join((_v177_info_btn_cb(b) for b in row or []))
                if 'назад' in labels or 'закры' in labels or 'info_close' in callbacks or ('back_main' in callbacks):
                    insert_at = idx
                    break
            rows.insert(insert_at, [IB(careful_restore_button_label(cid), callback_data='careful_restore_toggle')])
    if cid == int(OWNER_ID or 0):
        if not any((_v177_info_btn_cb(b).startswith('traffic_audit') for row in rows for b in row or [])):
            insert_at = len(rows)
            for idx, row in enumerate(rows):
                labels = ' '.join((_v177_info_btn_text(b) for b in row or [])).casefold()
                callbacks = ' '.join((_v177_info_btn_cb(b) for b in row or []))
                if 'назад' in labels or 'закры' in labels or 'info_close' in callbacks or ('back_main' in callbacks):
                    insert_at = idx
                    break
            rows.insert(insert_at, [IB('📶 Аудит трафика', callback_data='traffic_audit:month')])
    if cid == int(OWNER_ID or 0):
        found = False
        for row in rows:
            for btn in row or []:
                cb = _v177_info_btn_cb(btn)
                if cb in {'v175:heavy_toggle', 'v176:menu'}:
                    try:
                        if isinstance(btn, dict):
                            btn['text'] = '⚙️ Процессы / скорость'
                            btn['callback_data'] = 'v176:menu'
                        else:
                            btn.text = '⚙️ Процессы / скорость'
                            btn.callback_data = 'v176:menu'
                    except Exception:
                        pass
                    found = True
        if not found:
            insert_at = len(rows)
            for idx, row in enumerate(rows):
                labels = ' '.join((_v177_info_btn_text(b) for b in row or [])).casefold()
                callbacks = ' '.join((_v177_info_btn_cb(b) for b in row or []))
                if 'назад' in labels or 'закры' in labels or 'info_close' in callbacks or ('back_main' in callbacks):
                    insert_at = idx
                    break
            rows.insert(insert_at, [IB('⚙️ Процессы / скорость', callback_data='v176:menu')])
    return _v177_info_set_rows(kb, rows)

def _v176_owner_ok(call) -> bool:
    try:
        return int(call.message.chat.id) == int(OWNER_ID or 0) and int(getattr(getattr(call, 'from_user', None), 'id', 0) or 0) == int(OWNER_ID or 0)
    except Exception:
        return False

def _v176_filter(call):
    raw = str(getattr(call, 'data', '') or '')
    return raw.startswith('v176:') or raw == 'v175:heavy_toggle'

def _v176_callback(call):
    raw = str(getattr(call, 'data', '') or '')
    if not _v176_owner_ok(call):
        try:
            bot.answer_callback_query(call.id, 'Только основной владелец.', show_alert=True)
        except Exception:
            pass
        return
    chat_id = int(call.message.chat.id)
    if raw in {'v175:heavy_toggle', 'v176:menu'}:
        try:
            bot.answer_callback_query(call.id)
        except Exception:
            pass
        safe_edit(bot, call, _v176_menu_text('ui'), reply_markup=_v176_menu_keyboard('ui'))
        return
    if raw.startswith('v176:p:'):
        page = raw.split(':', 2)[2]
        try:
            bot.answer_callback_query(call.id)
        except Exception:
            pass
        safe_edit(bot, call, _v176_menu_text(page), reply_markup=_v176_menu_keyboard(page))
        return
    if raw.startswith('v176:t:'):
        code = raw.split(':', 2)[2]
        if code not in _V176_PROCESS_DEFS:
            return
        new_state = not v176_process_enabled(code)
        v176_set_process(code, new_state, int(OWNER_ID or 0))
        try:
            bot.answer_callback_query(call.id, f"{_V176_PROCESS_DEFS[code][1]}: {('✅ ВКЛ' if new_state else '⬜ ВЫКЛ')}")
        except Exception:
            pass
        page = _V176_PROCESS_DEFS[code][0]
        safe_edit(bot, call, _v176_menu_text(page), reply_markup=_v176_menu_keyboard(page))
        return
    if raw.startswith('v176:profile:'):
        profile = raw.split(':', 2)[2]
        v176_apply_profile(profile, int(OWNER_ID or 0))
        labels = {'all': 'Всё включено', 'fast': 'Быстрый тест', 'minimal': 'Минимальный диагностический режим'}
        try:
            bot.answer_callback_query(call.id, labels.get(profile, profile))
        except Exception:
            pass
        safe_edit(bot, call, _v176_menu_text('ui'), reply_markup=_v176_menu_keyboard('ui'))
        return
    if raw == 'v176:speed':
        try:
            bot.answer_callback_query(call.id)
        except Exception:
            pass
        safe_edit(bot, call, _v176_speed_text(), reply_markup=_v176_speed_keyboard())
        return
    if raw == 'v176:speed_clear':
        v177_perf_clear()
        try:
            bot.answer_callback_query(call.id, 'Замер очищен')
        except Exception:
            pass
        safe_edit(bot, call, _v176_speed_text(), reply_markup=_v176_speed_keyboard())
        return
    if raw == 'v176:back_info':
        try:
            bot.answer_callback_query(call.id)
        except Exception:
            pass
        safe_edit(bot, call, build_info_text(chat_id), reply_markup=build_info_keyboard(chat_id))
        return

def _v178_migrate_global_speed_defaults() -> bool:
    """One-time v178 migration: disable diagnostic noise globally, keep business durability on."""
    root = _v176_root()
    if bool(root.get('v178_global_speed_defaults_migrated', False)):
        return False
    for code in ('win_diag', 'btn_chain', 'btn_press', 'win_journal', 'failed_repair', 'failed_diag'):
        root[code] = False
    root['v178_global_speed_defaults_migrated'] = True
    try:
        root['v178_migrated_at'] = now_local().isoformat(timespec='seconds')
    except Exception:
        pass
    try:
        SQLITE.save_root(_sqlite_pack_root(data))
    except Exception:
        pass
    return True
_V178_SPEED_MIGRATED = _v178_migrate_global_speed_defaults()
_v176_root()
_v176_apply_runtime_flags()
_V176_CALLBACK = 0
_V176_PERF_WRAPPERS = 0
try:
    _V176_ORIG_BOT_JOURNAL('v179_clean_final_installed', int(OWNER_ID or 0) or None, f'managed={len(_V176_PROCESS_DEFS)} callback={_V176_CALLBACK} perf_wrappers={_V176_PERF_WRAPPERS} speed_defaults={int(_V178_SPEED_MIGRATED)}')
except Exception:
    pass
V179_RUNTIME_REMOTE_HEARTBEAT_SECONDS = max(300.0, min(3600.0, float(os.getenv('RUNTIME_REMOTE_HEARTBEAT_SECONDS', '900') or '900')))
_V179_LEASE_LAST = 0.0
_V179_LEASE_LOCK = _v176_threading.RLock()

def _v179_runtime_lease_check(force: bool=False) -> dict:
    """Lease is checked by the runtime watcher, not by a separate 30-second loop."""
    global _V179_LEASE_LAST
    if not v176_process_enabled('lease') or not mega_is_configured():
        return {'active': True, 'skipped': True}
    now_m = _v176_time.monotonic()
    with _V179_LEASE_LOCK:
        if not force and now_m - float(_V179_LEASE_LAST or 0.0) < V179_RUNTIME_REMOTE_HEARTBEAT_SECONDS - 5:
            return {'active': True, 'cached': True}
        _V179_LEASE_LAST = now_m
    base = globals().get('_v179_base_instance_lease_check') or globals().get('_V176_ORIG_INSTANCE_LEASE')
    if callable(base):
        try:
            return dict(base() or {})
        except Exception as exc:
            try:
                runtime_event('lease_check_error', str(exc), 'WARN')
            except Exception:
                pass
    return {'active': True}

def _canon_runtime_heartbeat_job__001():
    if runtime_is_shutting_down():
        return
    next_delay = V179_RUNTIME_REMOTE_HEARTBEAT_SECONDS
    try:
        lease = _v179_runtime_lease_check(False)
        if lease.get('superseded'):
            return
        if v176_process_enabled('runtime_upload'):
            busy_fn = globals().get('_runtime_watcher_should_yield_to_critical_mega')
            if callable(busy_fn) and busy_fn():
                try:
                    runtime_event('watcher_heartbeat_deferred', 'critical MEGA work has priority')
                except Exception:
                    pass
                next_delay = min(90.0, V179_RUNTIME_REMOTE_HEARTBEAT_SECONDS)
            else:
                GENERAL_TASK_POOL.submit_unique('runtime-heartbeat-upload', runtime_upload_snapshot, 'heartbeat', False)
    finally:
        try:
            DELAYED_SCHEDULER.schedule('runtime-heartbeat', next_delay, _runtime_heartbeat_job)
        except Exception:
            pass

def _canon_v153_instance_lease_check__001(*args, **kwargs):
    return _v179_runtime_lease_check(bool(kwargs.get('force', False)))

def _canon_v153_schedule_migration__001(*args, **kwargs):
    return False

def _canon_v153_reconcile_windows__001():
    fn = globals().get('v179_window_registry_lazy_cleanup')
    return fn(True) if callable(fn) and v176_process_enabled('win_rec') else {'skipped': 'v179_lazy_registry'}
try:
    TRAFFIC_AUDIT_CHECKPOINT_SECONDS = max(300.0, min(3600.0, float(os.getenv('TRAFFIC_AUDIT_CHECKPOINT_SECONDS', '600') or '600')))
except Exception:
    TRAFFIC_AUDIT_CHECKPOINT_SECONDS = 600.0

def _traffic_audit_checkpoint_job():
    if runtime_is_shutting_down():
        return None
    try:
        fn = globals().get('traffic_audit_checkpoint_to_mega')
        if callable(fn) and mega_is_configured():
            GENERAL_TASK_POOL.submit_unique('traffic-audit-checkpoint', fn, 'periodic')
        else:
            log_fn = globals().get('traffic_audit_render_log_summary')
            if callable(log_fn):
                log_fn('periodic_no_mega')
    finally:
        try:
            DELAYED_SCHEDULER.schedule('traffic-audit-checkpoint', TRAFFIC_AUDIT_CHECKPOINT_SECONDS, _traffic_audit_checkpoint_job)
        except Exception:
            pass
    return True

def _v203_apply_traffic_economy_defaults() -> bool:
    """One-time post-restore migration for installations whose v202 process flags are already persisted."""
    try:
        root = _v176_root()
        if bool(root.get('v203_traffic_economy_defaults_migrated', False)):
            return False
        root['source_archive'] = False
        root['full_chat'] = False
        root['journal_mega'] = False
        root['runtime_upload'] = False
        root['v203_traffic_economy_defaults_migrated'] = True
        root['v203_traffic_economy'] = {'source_archive': False, 'full_chat_auto': False, 'journal_mega_auto': False, 'runtime_heartbeat_upload': False, 'self_keepalive_default': True, 'smart_auto_keepalive_default': True, 'smart_auto_idle_seconds': 720, 'telegram_getme_keepalive_removed': True, 'lease_check_seconds': V179_RUNTIME_REMOTE_HEARTBEAT_SECONDS, 'full_chat_idle_seconds_if_reenabled': float(globals().get('BACKUP_MIN_DELAY_SECONDS', 0) or 0), 'full_sqlite_idle_seconds': float(globals().get('MEGA_GLOBAL_QUIET_SECONDS', 0) or 0), 'full_sqlite_max_seconds': float(globals().get('MEGA_GLOBAL_MAX_INTERVAL_SECONDS', 0) or 0), 'legacy_db_mirror_default': False}
        try:
            root['v203_traffic_economy_migrated_at'] = now_local().isoformat(timespec='seconds')
        except Exception:
            pass
        try:
            _v176_persist('v203_traffic_economy_defaults')
        except Exception:
            pass
        return True
    except Exception as exc:
        try:
            log_error(f'v203 traffic economy migration: {exc}')
        except Exception:
            pass
        return False

def _canon_v153_validate_restore_gz__001(gz_path: str):
    """FINAL v235 restore validator.

    Accepts both explicit full-state exports and normal immutable MEGA generation snapshots.
    A working generation may legitimately contain an OLD v153_export manifest copied from the
    live SQLite.  Such a stale manifest must never override the newer db_snapshot/main identity.
    True full-state exports still keep strict logical-checksum validation.
    """
    import gzip as _gz, shutil as _shutil, sqlite3 as _sqlite3, tempfile as _tempfile, json as _json, os as _os
    from datetime import datetime as _dt
    folder = _tempfile.mkdtemp(prefix='v235_restore_validate_')
    raw = _os.path.join(folder, 'restore.sqlite3')

    def _ts(value):
        s = str(value or '').strip()
        if not s:
            return 0.0
        try:
            if s.endswith('Z'):
                s = s[:-1] + '+00:00'
            return float(_dt.fromisoformat(s).timestamp())
        except Exception:
            return 0.0
    try:
        with _gz.open(gz_path, 'rb') as fin, open(raw, 'wb') as fout:
            _shutil.copyfileobj(fin, fout, 1024 * 1024)
        conn = _sqlite3.connect(raw)
        try:
            integrity = str(conn.execute('PRAGMA integrity_check').fetchone()[0])
            if integrity.lower() != 'ok':
                raise RuntimeError(f'SQLite integrity_check: {integrity}')
            tables = {str(r[0]) for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
            required = {'kv', 'chats', 'meta'}
            if not required.issubset(tables):
                raise RuntimeError('SQLite не похож на snapshot бота (нет kv/chats/meta)')
            snapshot_meta = {}
            try:
                mrow = conn.execute("SELECT v FROM meta WHERE kind='db_snapshot' AND k='main'").fetchone()
                snapshot_meta = _json.loads(mrow[0]) if mrow and mrow[0] else {}
                if not isinstance(snapshot_meta, dict):
                    snapshot_meta = {}
            except Exception:
                snapshot_meta = {}
            export_manifest = {}
            try:
                row = conn.execute("SELECT v FROM meta WHERE kind='v153_export' AND k='manifest'").fetchone()
                export_manifest = _json.loads(row[0]) if row and row[0] else {}
                if not isinstance(export_manifest, dict):
                    export_manifest = {}
            except Exception:
                export_manifest = {}
        finally:
            conn.close()
        stale_export_ignored = False
        if export_manifest:
            if str(export_manifest.get('kind')) != 'telegram_bot_full_state_v153':
                raise RuntimeError('unknown export kind')
            if int(export_manifest.get('schema_version') or 0) != int(V153_EXPORT_SCHEMA):
                raise RuntimeError('unsupported export schema')
            expected = str(export_manifest.get('checksum') or '')
            actual = _v153_db_logical_checksum(raw)
            if expected and actual == expected:
                manifest = dict(export_manifest)
                manifest['snapshot_format'] = 'full_state_export'
                return (manifest, raw)
            snap_ts = _ts(snapshot_meta.get('created_at'))
            export_ts = _ts(export_manifest.get('created_at'))
            if snapshot_meta and snap_ts > 0 and (export_ts > 0) and (snap_ts > export_ts + 60.0):
                stale_export_ignored = True
                try:
                    runtime_event('restore_stale_v153_manifest_ignored_v235', f"snapshot={snapshot_meta.get('created_at')}; export={export_manifest.get('created_at')}; file={_os.path.basename(gz_path)}", 'WARN')
                except Exception:
                    pass
            else:
                raise RuntimeError('checksum mismatch')
        created_at = str(snapshot_meta.get('created_at') or '')
        bot_version = str(snapshot_meta.get('bot_version') or '')
        chat_ids = []
        conn = _sqlite3.connect(raw)
        try:
            try:
                chat_ids = [int(r[0]) for r in conn.execute('SELECT chat_id FROM chats ORDER BY chat_id').fetchall()]
            except Exception:
                chat_ids = []
            record_count = 0
            if 'cold_fields' in tables:
                try:
                    for value, in conn.execute("SELECT v FROM cold_fields WHERE k='records'").fetchall():
                        try:
                            rows = _json.loads(value) if value else []
                            if isinstance(rows, list):
                                record_count += len(rows)
                        except Exception:
                            pass
                except Exception:
                    pass
            if not record_count:
                try:
                    for value, in conn.execute('SELECT v FROM chats').fetchall():
                        try:
                            payload = _json.loads(value) if value else {}
                            rows = payload.get('records') if isinstance(payload, dict) else []
                            if isinstance(rows, list):
                                record_count += len(rows)
                        except Exception:
                            pass
                except Exception:
                    pass
            embedded = {}
            try:
                erow = conn.execute("SELECT v FROM meta WHERE kind='data_constitution_snapshot' AND k='main'").fetchone()
                embedded = _json.loads(erow[0]) if erow and erow[0] else {}
                if not isinstance(embedded, dict):
                    embedded = {}
            except Exception:
                embedded = {}
            semantic_fn = globals().get('constitution_semantic_manifest_from_sqlite')
            if callable(semantic_fn):
                semantic = semantic_fn(raw) or {}
                if int(semantic.get('total_records') or 0) >= 0:
                    record_count = int(semantic.get('total_records') or 0)
                if embedded and int(embedded.get('total_records') or 0) != int(semantic.get('total_records') or 0):
                    raise RuntimeError(f"embedded semantic mismatch: {semantic.get('total_records')} != {embedded.get('total_records')}")
        finally:
            conn.close()
        manifest = {'kind': 'telegram_bot_working_sqlite_snapshot', 'schema_version': 1, 'bot_version': bot_version or 'working_snapshot', 'created_at': created_at, 'scope': 'global', 'tenant_id': '', 'chat_ids': chat_ids, 'chat_count': len(chat_ids), 'record_count': int(record_count), 'failed_tasks': 0, 'checksum': '', 'snapshot_format': 'working_sqlite_generation', 'stale_v153_manifest_ignored': bool(stale_export_ignored)}
        return (manifest, raw)
    except Exception:
        _shutil.rmtree(folder, ignore_errors=True)
        raise

def _v182_download_restore_document(document) -> tuple[str, str]:
    import os as _os, tempfile as _tempfile
    name = str(getattr(document, 'file_name', '') or 'backup.sqlite3.gz')
    folder = _tempfile.mkdtemp(prefix='v182_restore_upload_')
    safe_name = _os.path.basename(name).replace('/', '_').replace('\\', '_') or 'backup.sqlite3.gz'
    path = _os.path.join(folder, safe_name)
    info = bot.get_file(document.file_id)
    stream_fn = globals().get('telegram_download_to_file')
    if callable(stream_fn):
        max_restore = max(1024 * 1024, int(os.getenv('RESTORE_FILE_MAX_BYTES', str(250 * 1024 * 1024)) or str(250 * 1024 * 1024)))
        stream_fn(info.file_path, path, max_bytes=max_restore)
    else:
        raw = bot.download_file(info.file_path)
        with open(path, 'wb') as fh:
            fh.write(raw)
    return (path, folder)

def v182_prepare_gz_restore_document(msg, document=None) -> bool:
    """Prepare a .gz restore from a document sent after /restore or replied to by /restore."""
    uid = _v153_actor_id(msg)
    chat_id = int(msg.chat.id)
    document = document or getattr(getattr(msg, 'reply_to_message', None), 'document', None)
    if not document:
        raise RuntimeError('Не найден GZ-файл')
    name = str(getattr(document, 'file_name', '') or '').lower()
    if not name.endswith('.gz'):
        raise RuntimeError('Нужен файл .gz (обычно .sqlite3.gz)')
    gz = folder = raw = None
    try:
        gz, folder = _v182_download_restore_document(document)
        manifest, raw = _v153_validate_restore_gz(gz)
        scope = str(manifest.get('scope') or 'global')
        tenant_id = str(manifest.get('tenant_id') or _v153_tenant_for_chat(chat_id))
        if scope == 'global' and (not _v153_platform_owner(uid)):
            raise RuntimeError('Глобальное восстановление доступно только владельцу платформы')
        if scope == 'tenant' and (not _v153_can_manage_tenant(uid, tenant_id)):
            current = _v153_tenant_for_chat(chat_id)
            if not _v153_can_manage_tenant(uid, current):
                raise RuntimeError('Нельзя восстановить чужое пространство')
            tenant_id = current
        token = _v153_hashlib.sha256(f'v182:{uid}:{chat_id}:{_v153_time.time_ns()}'.encode()).hexdigest()[:16]
        with _V153_LOCK:
            _V153_RESTORE_PENDING[token] = {'uid': uid, 'chat_id': chat_id, 'gz': gz, 'raw': raw, 'manifest': manifest, 'tenant_id': tenant_id, 'created': _v153_time.time(), 'upload_folder': folder}
        fmt = str(manifest.get('snapshot_format') or 'sqlite')
        text = f"🧪 GZ-файл проверен.\n\nФормат: {fmt}\nВерсия: {manifest.get('bot_version') or 'не указана'}\nОбласть: {('весь бот' if scope == 'global' else 'пространство')}\nЧатов: {manifest.get('chat_count', 0)}\nФинансовых записей: {manifest.get('record_count', 'см. snapshot')}\nСоздан: {manifest.get('created_at') or 'не указано'}\n\nПеред применением будет создан pre_restore backup текущей базы.\nПосле подтверждения текущий scope будет ЗАМЕНЁН данными GZ без объединения."
        bot.reply_to(msg, text, reply_markup=_v153_restore_keyboard(token, scope))
        global restore_mode
        restore_mode = None
        data.pop('_restore_mode_chat_v150', None)
        return True
    except Exception:
        if folder and (not raw):
            try:
                _v176_shutil.rmtree(folder, ignore_errors=True)
            except Exception:
                pass
        raise

def v182_cmd_restore(msg):
    """Unified historical /restore: reply to GZ, or enter upload mode for GZ/JSON/ISON/CSV."""
    try:
        update_chat_info_from_message(msg)
    except Exception:
        pass
    try:
        schedule_command_delete(msg)
    except Exception:
        pass
    uid = _v153_actor_id(msg)
    chat_id = int(msg.chat.id)
    if not (_v153_platform_owner(uid) or _v153_can_manage_tenant(uid, _v153_tenant_for_chat(chat_id))):
        bot.reply_to(msg, '⛔ Недостаточно прав для восстановления.')
        return
    replied_doc = getattr(getattr(msg, 'reply_to_message', None), 'document', None)
    if replied_doc is not None and str(getattr(replied_doc, 'file_name', '') or '').lower().endswith('.gz'):
        try:
            v182_prepare_gz_restore_document(msg, replied_doc)
        except Exception as exc:
            bot.reply_to(msg, f'❌ GZ не подготовлен к восстановлению:\n{v153_redact_text(exc)[:700]}')
        return
    global restore_mode
    restore_mode = chat_id
    data.pop('_restore_mode_chat_v150', None)
    send_and_auto_delete(chat_id, '📥 Режим восстановления включён — СТРОГАЯ ЗАМЕНА ИЗ ФАЙЛА.\n\nТекущее состояние будет сначала сохранено в pre_restore, затем выбранный scope будет заменён ровно данными файла. Никакого merge.\n\nТеперь отправьте ОДИН файл:\n• *.sqlite3.gz / *.gz — полный SQLite snapshot\n• *.json / *.ison — полный JSON/ISON backup (включая chat_<id>.json)\n• *.csv — CSV чата\n\nДля следующего файла снова отправьте /restore.\nОтмена: /restore_off', 30)

def _v182_install_restore_handler() -> int:
    replaced = 0
    for handler in list(getattr(bot, 'message_handlers', []) or []):
        if not isinstance(handler, dict):
            continue
        filters = handler.get('filters') or {}
        commands = [str(x).lower() for x in filters.get('commands') or []]
        if 'restore' in commands:
            handler['function'] = v182_cmd_restore
            replaced += 1
    if not replaced:
        try:
            bot.message_handler(commands=['restore'])(v182_cmd_restore)
            replaced = 1
        except Exception:
            pass
    return replaced
_V182_RESTORE_HANDLER_COUNT = _v182_install_restore_handler()
_V179_BASE_REGISTER_OPEN_WINDOW = globals().get('_v179_base_register_open_window') or _v179_base_register_open_window
_V179_BASE_GET_OPEN_WINDOW = globals().get('_v179_base_get_registered_open_window') or _v179_base_get_registered_open_window

def _v179_touch_window_registry():
    try:
        fn = globals().get('v179_window_registry_lazy_cleanup')
        if callable(fn) and v176_process_enabled('win_cleanup'):
            fn(False)
    except Exception:
        pass

def _canon_register_open_window__001(chat_id: int, message_id: int, window_type: str, code: str='', day_key=None, params=None):
    _v179_touch_window_registry()
    return _V179_BASE_REGISTER_OPEN_WINDOW(chat_id, message_id, window_type, code=code, day_key=day_key, params=params)

def _canon_get_registered_open_window__001(chat_id: int, message_id: int):
    _v179_touch_window_registry()
    return _V179_BASE_GET_OPEN_WINDOW(chat_id, message_id)

def _v211_mega_node_housekeeping_job():
    """Incremental post-READY cleanup; never blocks boot or critical persistence."""
    delay = 21600.0
    try:
        if runtime_is_shutting_down() or not runtime_is_ready():
            return
        if _runtime_watcher_should_yield_to_critical_mega():
            delay = 900.0
            return
        fn = globals().get('mega_diagnostic_node_housekeeping')
        if callable(fn):
            report = fn(50) or {}
            removed = int(report.get('journal_removed', 0) or 0) + int(report.get('critical_removed', 0) or 0)
            delay = 120.0 if removed else 21600.0
            if removed:
                runtime_event('mega_node_housekeeping_v211', f'removed={removed}; next={int(delay)}s')
    except Exception as exc:
        delay = 1800.0
        try:
            runtime_event('mega_node_housekeeping_error_v211', str(exc), 'WARN')
        except Exception:
            pass
    finally:
        try:
            DELAYED_SCHEDULER.schedule('mega-node-housekeeping-v211', delay, _v211_mega_node_housekeeping_job)
        except Exception:
            pass

def _canon_runtime_mark_ready__001(detail: str=''):
    """One FINAL READY path replacing v153/v160/v167/v171/v172/v175 wrapper chain."""
    _v203_apply_traffic_economy_defaults()
    _v176_apply_runtime_flags()
    with _RUNTIME_LOCK:
        if _RUNTIME_STATE.get('ready'):
            return
        _RUNTIME_STATE['ready'] = True
        _RUNTIME_STATE['phase'] = 'ready'
        _RUNTIME_STATE['ready_at'] = now_local().isoformat(timespec='seconds')
        _RUNTIME_STATE['boot_completed_at'] = _RUNTIME_STATE['ready_at']
        _RUNTIME_STATE['boot_duration_seconds'] = round(max(0.0, _v176_time.monotonic() - _RUNTIME_STARTED_MONO), 3)
    runtime_event('ready', detail or 'BOOT completed')
    try:
        data.setdefault(V172_TASKS_KEY, {})
        data.setdefault(V172_TASK_SETTINGS_KEY, {})
        data.setdefault(V172_TASK_SOURCE_INDEX_KEY, {})
    except Exception:
        pass
    try:
        _DELTA_ROOT_MAP_KEYS.update({V172_TASKS_KEY, V172_TASK_SETTINGS_KEY, V172_TASK_SOURCE_INDEX_KEY})
    except Exception:
        pass
    try:
        GENERAL_TASK_POOL.submit_unique('runtime-ready-lease', _v179_runtime_lease_check, True)
    except Exception:
        pass
    try:
        _tr = globals().get('traffic_audit_restore_from_mega')
        if callable(_tr):
            GENERAL_TASK_POOL.submit_unique('traffic-audit-restore', _tr)
        DELAYED_SCHEDULER.schedule('traffic-audit-checkpoint', min(600.0, TRAFFIC_AUDIT_CHECKPOINT_SECONDS), _traffic_audit_checkpoint_job)
    except Exception:
        pass
    if v176_process_enabled('runtime_upload'):
        try:
            GENERAL_TASK_POOL.submit_unique('runtime-ready-snapshot', runtime_upload_snapshot, 'boot_ready', True)
        except Exception:
            pass
    try:
        DELAYED_SCHEDULER.schedule('runtime-heartbeat', V179_RUNTIME_REMOTE_HEARTBEAT_SECONDS, _runtime_heartbeat_job)
    except Exception:
        pass
    if not RESTORE_GUARD_ACTIVE:
        try:
            schedule_startup_main_windows(delay=1.0)
        except Exception as exc:
            runtime_event('startup_windows_error', str(exc), 'WARN')
    try:
        schedule_restored_secret_media_recovery(1.5)
    except Exception:
        pass
    try:
        DELAYED_SCHEDULER.schedule('journal-warm-tail', 12.0, _journal_warm_tail_job)
    except Exception:
        pass
    try:
        DELAYED_SCHEDULER.schedule('mega-node-housekeeping-v211', 90.0, _v211_mega_node_housekeeping_job)
    except Exception:
        pass
    try:
        DELAYED_SCHEDULER.schedule('lowram-idle-sweep', 45.0, _lowram_idle_sweep_job)
    except Exception:
        pass
    try:
        DELAYED_SCHEDULER.schedule('v160-transient-cleanup', 2.0, _v160_cleanup_legacy_transient_windows)
    except Exception:
        pass
    try:
        if _v168_mark_resolved_tz_rows():
            _v160_persist_annotations(int(OWNER_ID or 0))
    except Exception:
        pass
    try:
        _v167_archive_old_tz_once(force=True)
    except Exception:
        pass
    try:
        _v171_mark_all_v169_tz_fixed()
    except Exception:
        pass
    try:
        _v171_reminder_global_mode(True)
        forward_copy_edit_mode(int(OWNER_ID or 0))
    except Exception:
        pass
    try:
        if OWNER_ID:
            _v167_google_schedule_cfg(int(OWNER_ID), create=True)
            _v167_persist_schedule(int(OWNER_ID))
    except Exception:
        pass
    try:
        bot_journal('v179_ready', int(OWNER_ID or 0) or None, f"single_ready_path=1; mega_root={globals().get('MEGA_BACKUP_DIR', '')}")
    except Exception:
        pass
    try:
        _start_post_ready = globals().get('_v211_start_post_ready_runtime')
        if callable(_start_post_ready):
            _start_post_ready()
    except Exception:
        pass
    try:
        _notify = globals().get('_v211_notify_owner_ready_once')
        if callable(_notify):
            GENERAL_TASK_POOL.submit_unique('owner-ready-notice-v211', _notify)
    except Exception:
        pass
_V217_INFO_KB_PREV = _canon_build_info_keyboard__001

def _v217_build_info_keyboard(chat_id: int):
    kb = _V217_INFO_KB_PREV(int(chat_id))
    cid = int(chat_id)
    if cid != int(OWNER_ID or 0):
        return kb
    try:
        rows = _v177_info_rows(kb)
        if not any((_v177_info_btn_cb(b) == 'v217:cmenu:open' for row in rows for b in row or [])):
            insert_at = len(rows)
            for idx, row in enumerate(rows):
                labels = ' '.join((_v177_info_btn_text(b) for b in row or [])).casefold()
                callbacks = ' '.join((_v177_info_btn_cb(b) for b in row or []))
                if 'назад' in labels or 'закры' in labels or 'info_close' in callbacks or ('back_main' in callbacks):
                    insert_at = idx
                    break
            rows.insert(insert_at, [IB('🎛 Меню контуров 1/2', callback_data='v217:cmenu:open')])
            _v177_info_set_rows(kb, rows)
    except Exception:
        pass
    return kb

def _v217_cmenu_variant_name(value: int) -> str:
    return {1: 'Список', 2: 'Плитка 2×2', 3: 'Компактный'}.get(int(value or 1), 'Список')

def build_v217_contour_menu_admin_text(level: int | None=None) -> str:
    root = _v217_menu_variant_root()
    if level in {1, 2}:
        current = int(root.get(str(level), 1) or 1)
        return window_mark(f"🎛 МЕНЮ КОНТУРОВ 1/2\n\nНастраивается: {('1️⃣ первый' if int(level) == 1 else '2️⃣ второй')} контур\nТекущий вариант: {current} — {_v217_cmenu_variant_name(current)}\n\n1 — список: четыре режима вертикально.\n2 — плитка 2×2: те же режимы компактно.\n3 — компактный: состояния текстом, ниже отдельные кнопки входа.\n\nИзменение влияет только на стартовое меню выбранного контура и не меняет бизнес-режимы.", 'Ф259')
    v1 = int(root.get('1', 1) or 1)
    v2 = int(root.get('2', 1) or 1)
    return window_mark(f'🎛 МЕНЮ КОНТУРОВ 1/2\n\n1️⃣ Первый контур: вариант {v1} — {_v217_cmenu_variant_name(v1)}\n2️⃣ Второй контур: вариант {v2} — {_v217_cmenu_variant_name(v2)}\n\nВыберите контур для настройки.', 'Ф259')

def build_v217_contour_menu_admin_keyboard(level: int | None=None):
    kb = types.InlineKeyboardMarkup(row_width=1)
    root = _v217_menu_variant_root()
    if level in {1, 2}:
        current = int(root.get(str(level), 1) or 1)
        for variant in (1, 2, 3):
            kb.row(IB(('✅ ' if current == variant else '⬜ ') + f'Вариант {variant} — {_v217_cmenu_variant_name(variant)}', callback_data=f'v217:cmenu:set:{int(level)}:{variant}'))
        kb.row(IB('🔙 К выбору контура', callback_data='v217:cmenu:open'))
    else:
        kb.row(IB(f"1️⃣ Первый контур · {_v217_cmenu_variant_name(int(root.get('1', 1) or 1))}", callback_data='v217:cmenu:circle:1'))
        kb.row(IB(f"2️⃣ Второй контур · {_v217_cmenu_variant_name(int(root.get('2', 1) or 1))}", callback_data='v217:cmenu:circle:2'))
        kb.row(IB('🔙 Назад в Инфо', callback_data=f'd:{today_key()}:info'))
    return kb
_V217_CALLBACK_PREV = _canon_v217_callback_final__001

def _canon_v217_callback_final__002(call, resolved: str) -> bool:
    raw = str(resolved or '')
    if raw.startswith('v217:cmenu:'):
        try:
            cid = int(call.message.chat.id)
            uid = int(getattr(getattr(call, 'from_user', None), 'id', 0) or 0)
        except Exception:
            return True
        if cid != int(OWNER_ID or 0) or uid != int(OWNER_ID or 0):
            try:
                bot.answer_callback_query(call.id, 'Только основной владелец.', show_alert=True)
            except Exception:
                pass
            return True
        parts = raw.split(':')
        action = parts[2] if len(parts) > 2 else ''
        if action == 'open':
            try:
                bot.answer_callback_query(call.id)
            except Exception:
                pass
            safe_edit(bot, call, build_v217_contour_menu_admin_text(), reply_markup=build_v217_contour_menu_admin_keyboard())
            return True
        if action == 'circle':
            try:
                bot.answer_callback_query(call.id)
            except Exception:
                pass
            try:
                level = 2 if int(parts[3]) == 2 else 1
            except Exception:
                level = 1
            safe_edit(bot, call, build_v217_contour_menu_admin_text(level), reply_markup=build_v217_contour_menu_admin_keyboard(level))
            return True
        if action == 'set':
            try:
                level = 2 if int(parts[3]) == 2 else 1
                variant = int(parts[4])
            except Exception:
                return True
            set_contour_start_menu_variant_v217(level, variant)
            try:
                bot.answer_callback_query(call.id, f'Контур {level}: вариант {variant}')
            except Exception:
                pass
            safe_edit(bot, call, build_v217_contour_menu_admin_text(level), reply_markup=build_v217_contour_menu_admin_keyboard(level))
            return True
        return True
    if callable(_V217_CALLBACK_PREV):
        return bool(_V217_CALLBACK_PREV(call, raw))
    return False
try:
    WINDOW_MARKER_CONSTANTS.setdefault('v217:cmenu:*', 'Ф259')
except Exception:
    pass
_V218_INFO_KB_PREV = _v217_build_info_keyboard

def _v218_info_is_nav(btn) -> bool:
    text = _v177_info_btn_text(btn).strip().casefold()
    cb = _v177_info_btn_cb(btn)
    return 'назад' in text or 'закры' in text or 'основное' in text or (cb == 'info_close') or cb.endswith(':back_main') or (cb in {'nav_prev', 'aux_close'})

def _v218_build_info_keyboard(chat_id: int):
    kb = _V218_INFO_KB_PREV(int(chat_id))
    rows = _v177_info_rows(kb)
    out = []
    for row in rows:
        row = list(row or [])
        if not row:
            continue
        functional = [b for b in row if not _v218_info_is_nav(b)]
        nav = [b for b in row if _v218_info_is_nav(b)]
        out.extend([[b] for b in functional])
        if nav:
            back_main = [b for b in nav if _v177_info_btn_cb(b).endswith(':back_main') or 'основное' in _v177_info_btn_text(b).casefold()]
            close = [b for b in nav if _v177_info_btn_cb(b) in {'info_close', 'aux_close'} or 'закры' in _v177_info_btn_text(b).casefold()]
            other = [b for b in nav if b not in back_main and b not in close]
            out.extend([[b] for b in other])
            if back_main and close:
                out.append([back_main[0], close[0]])
                out.extend([[b] for b in back_main[1:]])
                out.extend([[b] for b in close[1:]])
            else:
                out.extend([[b] for b in back_main + close])
    return _v177_info_set_rows(kb, out)
try:
    _canon_bot_journal__001('v218_info_vertical_ready', int(OWNER_ID or 0), 'functional_buttons=one_per_row; nav_pair_allowed=1')
except Exception:
    pass
V219_CIRCLE_ANNOTATION_KEY = 'circle_annotation_buttons_v219'

def _v219_annotation_settings() -> dict:
    gs = data.setdefault('_global_settings', {})
    row = gs.setdefault(V219_CIRCLE_ANNOTATION_KEY, {})
    if not isinstance(row, dict):
        row = {}
        gs[V219_CIRCLE_ANNOTATION_KEY] = row
    row.setdefault('tz', True)
    row.setdefault('iz_mr', True)
    return row

def circle_annotation_button_enabled_v219(kind: str, chat_id: int | None=None) -> bool:
    key = 'iz_mr' if str(kind or '').replace('-', '_').casefold() in {'iz_mr', 'izmr', 'marker'} else 'tz'
    base = bool(_v219_annotation_settings().get(key, True))
    if chat_id is None or not base:
        return base
    fn = globals().get('annotation_effective_v229')
    if callable(fn):
        try:
            return bool(fn(key, int(chat_id)))
        except Exception:
            pass
    try:
        cid = int(chat_id)
        if not _v215_circle_business_chat(cid):
            return base
        directive_fn = globals().get('directive_chat_enabled_v223')
        local_fn = globals().get('directive_annotation_allowed_v223')
        if callable(directive_fn) and directive_fn(cid) and callable(local_fn):
            return bool(base and local_fn(cid, key))
    except Exception:
        pass
    return base

def set_circle_annotation_button_v219(kind: str, enabled: bool) -> bool:
    key = 'iz_mr' if str(kind or '').replace('-', '_').casefold() in {'iz_mr', 'izmr', 'marker'} else 'tz'
    row = _v219_annotation_settings()
    row[key] = bool(enabled)
    try:
        save_data(data, root_only=True)
    except Exception:
        pass
    try:
        schedule_delta_backup(int(OWNER_ID or 0), delay=0.2, reason=f'v219_annotation_{key}')
    except Exception:
        pass
    return bool(row[key])
_V219_INFO_KB_PREV = _v218_build_info_keyboard

def _v219_build_info_keyboard(chat_id: int):
    kb = _V219_INFO_KB_PREV(int(chat_id))
    if int(chat_id) != int(OWNER_ID or 0):
        return kb
    rows = _v177_info_rows(kb)
    callbacks = {_v177_info_btn_cb(b) for row in rows for b in row or []}
    insert_at = len(rows)
    for i, row in enumerate(rows):
        if any((_v218_info_is_nav(b) for b in row or [])):
            insert_at = i
            break
    additions = []
    if 'v219:annot:toggle:tz' not in callbacks:
        additions.append([IB(('✅ ВКЛ' if circle_annotation_button_enabled_v219('tz') else '⬜ ВЫКЛ') + ' · ТЗ окон /tz · Весь бот', callback_data='v219:annot:toggle:tz')])
    if 'v219:annot:toggle:izmr' not in callbacks:
        additions.append([IB(('✅ ВКЛ' if circle_annotation_button_enabled_v219('iz_mr') else '⬜ ВЫКЛ') + ' · Маркеры /iz-mr · Весь бот', callback_data='v219:annot:toggle:izmr')])
    rows[insert_at:insert_at] = additions
    return _v177_info_set_rows(kb, rows)

def _canon_v219_annotation_callback_final__001(call, resolved: str) -> bool:
    raw = str(resolved or '')
    if not raw.startswith('v219:annot:toggle:'):
        return False
    try:
        cid = int(call.message.chat.id)
        uid = int(getattr(getattr(call, 'from_user', None), 'id', 0) or 0)
    except Exception:
        return True
    if cid != int(OWNER_ID or 0) or uid != int(OWNER_ID or 0):
        try:
            bot.answer_callback_query(call.id, 'Только основной владелец.', show_alert=True)
        except Exception:
            pass
        return True
    kind = raw.rsplit(':', 1)[-1]
    key = 'iz_mr' if kind == 'izmr' else 'tz'
    new_value = set_circle_annotation_button_v219(key, not circle_annotation_button_enabled_v219(key))
    try:
        bot.answer_callback_query(call.id, 'Включено' if new_value else 'Выключено')
    except Exception:
        pass
    safe_edit(bot, call, build_info_text(cid), reply_markup=build_info_keyboard(cid))
    return True
try:
    WINDOW_MARKER_CONSTANTS.setdefault('v219:annot:*', 'Ф89')
    _canon_bot_journal__001('v219_annotation_switches_ready', int(OWNER_ID or 0), 'tz=default_on; iz_mr=default_on; scope=circle1+circle2')
except Exception:
    pass
_V220_INFO_KB_PREV = _v219_build_info_keyboard

def _v220_build_info_keyboard(chat_id: int):
    kb = _V220_INFO_KB_PREV(int(chat_id))
    if int(chat_id) != int(OWNER_ID or 0):
        return kb
    rows = _v177_info_rows(kb)
    callbacks = {_v177_info_btn_cb(b) for row in rows for b in row or []}
    insert_at = len(rows)
    for i, row in enumerate(rows):
        if any((_v218_info_is_nav(b) for b in row or [])):
            insert_at = i
            break
    additions = []
    for level in (1, 2):
        cb = f'v220:contour_access:toggle:{level}'
        if cb in callbacks:
            continue
        enabled = bool(contour_menu_access_enabled_v220(level=level))
        additions.append([IB(('✅ ВКЛ' if enabled else '⬜ ВЫКЛ') + f' · Меню режимов · Контур {level}', callback_data=cb)])
    rows[insert_at:insert_at] = additions
    return _v177_info_set_rows(kb, rows)

def _canon_v220_contour_access_callback_final__001(call, resolved: str) -> bool:
    raw = str(resolved or '')
    if not raw.startswith('v220:contour_access:toggle:'):
        return False
    try:
        cid = int(call.message.chat.id)
        uid = int(getattr(getattr(call, 'from_user', None), 'id', 0) or 0)
        level = 2 if int(raw.rsplit(':', 1)[-1]) == 2 else 1
    except Exception:
        return True
    if cid != int(OWNER_ID or 0) or uid != int(OWNER_ID or 0):
        try:
            bot.answer_callback_query(call.id, 'Только основной владелец.', show_alert=True)
        except Exception:
            pass
        return True
    current = bool(contour_menu_access_enabled_v220(level=level))
    value = set_contour_menu_access_v220(level, not current)
    try:
        bot.answer_callback_query(call.id, 'Доступ включён' if value else 'Доступ выключен')
    except Exception:
        pass
    _r10_kb = build_info_keyboard(cid)
    safe_edit(bot, call, build_info_text(cid), reply_markup=_r10_kb)
    try:
        bot.edit_message_reply_markup(chat_id=cid, message_id=int(call.message.message_id), reply_markup=_r10_kb)
    except Exception:
        pass
    try:
        refresh_circle_menu_access_v220(level)
    except Exception as exc:
        try:
            log_error(f'v220 contour menu immediate refresh: {exc}')
        except Exception:
            pass
    try:
        bot_journal('contour_menu_access_toggle_v220', cid, f'level={level}; enabled={int(value)}')
    except Exception:
        pass
    return True
_V220_PREV_ANNOTATION_CALLBACK = _canon_v219_annotation_callback_final__001

def _v220_annotation_callback_final(call, resolved: str) -> bool:
    raw = str(resolved or '')
    handled = bool(_V220_PREV_ANNOTATION_CALLBACK(call, raw))
    if handled and raw.startswith('v219:annot:toggle:'):
        try:
            refresh_circle_annotation_windows_v220()
        except Exception as exc:
            try:
                log_error(f'v220 annotation immediate refresh: {exc}')
            except Exception:
                pass
    return handled
try:
    WINDOW_MARKER_CONSTANTS.setdefault('v220:contour_access:*', 'Ф89')
    _canon_bot_journal__001('v220_owner_contour_controls_ready', int(OWNER_ID or 0), 'menu_access=circle1+circle2 independent; annotation_refresh=immediate_primary')
except Exception:
    pass
_V221_INFO_KB_PREV = _v220_build_info_keyboard

def _v221_build_info_keyboard(chat_id: int):
    kb = _V221_INFO_KB_PREV(int(chat_id))
    if int(chat_id) != int(OWNER_ID or 0):
        return kb
    rows = _v177_info_rows(kb)
    callbacks = {_v177_info_btn_cb(b) for row in rows for b in row or []}
    if 'v221:req:list:new:0' not in callbacks:
        insert_at = len(rows)
        for i, row in enumerate(rows):
            if any((_v218_info_is_nav(b) for b in row or [])):
                insert_at = i
                break
        try:
            count = int(v221_owner_requests_new_count())
        except Exception:
            count = 0
        rows.insert(insert_at, [IB(f'📨 Сообщения от пользователей ({count})', callback_data='v221:req:list:new:0')])
    return _v177_info_set_rows(kb, rows)
_V221_PREV_CONTOUR_ACCESS_CALLBACK = _canon_v220_contour_access_callback_final__001

def _v221_contour_access_callback_final(call, resolved: str) -> bool:
    raw = str(resolved or '')
    handled = bool(_V221_PREV_CONTOUR_ACCESS_CALLBACK(call, raw))
    if handled and raw.startswith('v220:contour_access:toggle:'):
        try:
            level = 2 if int(raw.rsplit(':', 1)[-1]) == 2 else 1
            v221_refresh_live_contour_policy(level)
        except Exception as exc:
            try:
                log_error(f'v221 contour access live refresh: {exc}')
            except Exception:
                pass
    return handled
_V221_PREV_ANNOTATION_CALLBACK = _v220_annotation_callback_final

def _v221_annotation_callback_final(call, resolved: str) -> bool:
    raw = str(resolved or '')
    handled = bool(_V221_PREV_ANNOTATION_CALLBACK(call, raw))
    if handled and raw.startswith('v219:annot:toggle:'):
        try:
            v221_refresh_live_contour_policy(None)
        except Exception as exc:
            try:
                log_error(f'v221 annotation live refresh: {exc}')
            except Exception:
                pass
    return handled
try:
    _canon_bot_journal__001('v221_owner_info_ready', int(OWNER_ID or 0), 'user_requests=1; live_policy_refresh=all_observed_windows')
except Exception:
    pass
V223_DIRECTIVE_ADMIN_MARKER = 'Ф265'
V223_DIRECTIVE_PAGE_SIZE = 12
try:
    WINDOW_MARKER_CONSTANTS.setdefault('v223:directive:*', V223_DIRECTIVE_ADMIN_MARKER)
except Exception:
    pass

def circle_annotation_global_enabled_v219(kind: str, chat_id: int | None=None) -> bool:
    key = 'iz_mr' if str(kind or '').replace('-', '_').casefold() in {'iz_mr', 'izmr', 'marker'} else 'tz'
    if chat_id is not None:
        try:
            if not _v215_circle_business_chat(int(chat_id)):
                return True
        except Exception:
            return True
    return bool(_v219_annotation_settings().get(key, True))

def _v223_directive_admin_text() -> str:
    c1 = list(_v174_circle_ids(1))
    c2 = list(_v174_circle_ids(2))
    d1 = sum((1 for cid in c1 if directive_chat_enabled_v223(cid)))
    d2 = sum((1 for cid in c2 if directive_chat_enabled_v223(cid)))
    return window_mark(f'🔒 ДИРЕКТИВНЫЕ ЧАТЫ\n\nPRIMARY OWNER может жёстко задать функциональный состав каждого отдельного чата.\nСами Финансы / Пересылка / Напоминания / Задачи используют прежние канонические mode flags — второй набор состояний не создаётся.\n\n1️⃣ Контур 1: {d1}/{len(c1)} директивных\n2️⃣ Контур 2: {d2}/{len(c2)} директивных\n\nВыберите контур, затем чат.', V223_DIRECTIVE_ADMIN_MARKER)

def _v223_directive_admin_keyboard():
    kb = types.InlineKeyboardMarkup(row_width=1)
    kb.row(IB('1️⃣ Контур 1', callback_data='v223:directive:circle:1:0'))
    kb.row(IB('2️⃣ Контур 2', callback_data='v223:directive:circle:2:0'))
    kb.row(IB('🔙 В Инфо', callback_data='v223:directive:info'), IB('❌ Закрыть', callback_data='aux_close'))
    return kb

def _v223_directive_circle_text(level: int, page: int=0) -> str:
    level = 2 if int(level) == 2 else 1
    ids = list(_v174_circle_ids(level))
    total = len(ids)
    pages = max(1, (total + V223_DIRECTIVE_PAGE_SIZE - 1) // V223_DIRECTIVE_PAGE_SIZE)
    page = max(0, min(int(page or 0), pages - 1))
    return window_mark(f'🔒 ДИРЕКТИВНЫЕ ЧАТЫ · Контур {level}\n\nЧатов: {total}\nСтраница: {page + 1}/{pages}\n\n🔒 — директивный режим включён.\nВыберите чат для настройки.', V223_DIRECTIVE_ADMIN_MARKER)

def _v223_directive_circle_keyboard(level: int, page: int=0):
    level = 2 if int(level) == 2 else 1
    ids = list(_v174_circle_ids(level))
    total = len(ids)
    pages = max(1, (total + V223_DIRECTIVE_PAGE_SIZE - 1) // V223_DIRECTIVE_PAGE_SIZE)
    page = max(0, min(int(page or 0), pages - 1))
    start = page * V223_DIRECTIVE_PAGE_SIZE
    kb = types.InlineKeyboardMarkup(row_width=1)
    for cid in ids[start:start + V223_DIRECTIVE_PAGE_SIZE]:
        name = str(get_chat_display_name(int(cid)) or f'Чат {int(cid)}').replace('\n', ' ')[:42]
        icon = '🔒' if directive_chat_enabled_v223(int(cid)) else '▫️'
        kb.row(IB(f'{icon} {name}', callback_data=f'v223:directive:chat:{int(cid)}:{page}'))
    nav = []
    if page > 0:
        nav.append(IB('⬅️', callback_data=f'v223:directive:circle:{level}:{page - 1}'))
    if page + 1 < pages:
        nav.append(IB('➡️', callback_data=f'v223:directive:circle:{level}:{page + 1}'))
    if nav:
        kb.row(*nav)
    kb.row(IB('🔙 К контурам', callback_data='v223:directive:home'), IB('❌ Закрыть', callback_data='aux_close'))
    return kb

def _v223_directive_card_text(chat_id: int) -> str:
    cid = int(chat_id)
    level = 2 if int(circle_level_for_chat(cid)) == 2 else 1
    row = _v223_directive_policy(cid, False)
    directive = bool(row.get('enabled', False))
    modes = {m: bool(_v215_mode_enabled(cid, m)) for m in V223_DIRECTIVE_MODES}
    local = dict(row.get('annotations') or {})
    try:
        global_tz = bool(circle_annotation_global_enabled_v219('tz', cid))
    except Exception:
        global_tz = True
    try:
        global_marker = bool(circle_annotation_global_enabled_v219('iz_mr', cid))
    except Exception:
        global_marker = True
    try:
        menu_global = bool(contour_menu_access_enabled_v220(cid))
    except Exception:
        menu_global = True
    return window_mark(f"🔒 ДИРЕКТИВНАЯ ПОЛИТИКА ЧАТА\n\n{get_chat_display_name(cid)}\nID: {cid}\nКонтур: {level}\n\nДирективный режим: {('✅ ВКЛ' if directive else '⬜ ВЫКЛ')}\nГлобальный доступ к меню контура: {('✅ ВКЛ' if menu_global else '⬜ ВЫКЛ')}\n\nРабочие режимы (канонические):\n{('✅ ВКЛ' if modes['finance'] else '⬜ ВЫКЛ')} · 💰 Финансы\n{('✅ ВКЛ' if modes['forward'] else '⬜ ВЫКЛ')} · 📤 Пересылка\n{('✅ ВКЛ' if modes['reminders'] else '⬜ ВЫКЛ')} · ⏰ Напоминания\n{('✅ ВКЛ' if modes['tasks'] else '⬜ ВЫКЛ')} · 📋 Задачи\n\nЛокальные кнопки директивного чата:\nТЗ окон: локально {('✅ ВКЛ' if bool(local.get('tz', True)) else '⬜ ВЫКЛ')} · глобально {('✅ ВКЛ' if global_tz else '⬜ ВЫКЛ')} · итог {('✅ ВКЛ' if circle_annotation_button_enabled_v219('tz', cid) else '⬜ ВЫКЛ')}\nМаркеры: локально {('✅ ВКЛ' if bool(local.get('iz_mr', True)) else '⬜ ВЫКЛ')} · глобально {('✅ ВКЛ' if global_marker else '⬜ ВЫКЛ')} · итог {('✅ ВКЛ' if circle_annotation_button_enabled_v219('iz_mr', cid) else '⬜ ВЫКЛ')}\n\nГлобальный запрет контура сильнее локального разрешения.\nПри директивном режиме пользователи видят только включённые рабочие разделы и не могут менять их набор.", V223_DIRECTIVE_ADMIN_MARKER)

def _v223_directive_card_keyboard(chat_id: int, page: int=0):
    cid = int(chat_id)
    level = 2 if int(circle_level_for_chat(cid)) == 2 else 1
    policy = _v223_directive_policy(cid, False)
    kb = types.InlineKeyboardMarkup(row_width=1)
    kb.row(IB(('✅ ВКЛ' if directive_chat_enabled_v223(cid) else '⬜ ВЫКЛ') + ' · 🔒 Директивный режим', callback_data=f'v223:directive:toggle:{cid}:{page}'))
    for mode in V223_DIRECTIVE_MODES:
        kb.row(IB(('✅ ВКЛ' if _v215_mode_enabled(cid, mode) else '⬜ ВЫКЛ') + ' · ' + _v215_mode_title(mode), callback_data=f'v223:directive:mode:{mode}:{cid}:{page}'))
    local = dict(policy.get('annotations') or {})
    kb.row(IB(('✅ ВКЛ' if bool(local.get('tz', True)) else '⬜ ВЫКЛ') + ' · ТЗ окон · локально', callback_data=f'v223:directive:annot:tz:{cid}:{page}'))
    kb.row(IB(('✅ ВКЛ' if bool(local.get('iz_mr', True)) else '⬜ ВЫКЛ') + ' · Маркеры · локально', callback_data=f'v223:directive:annot:izmr:{cid}:{page}'))
    kb.row(IB('🔙 К списку', callback_data=f'v223:directive:circle:{level}:{page}'), IB('❌ Закрыть', callback_data='aux_close'))
    return kb
_V223_INFO_KB_PREV = _v221_build_info_keyboard

def _v223_build_info_keyboard(chat_id: int):
    kb = _V223_INFO_KB_PREV(int(chat_id))
    if int(chat_id) != int(OWNER_ID or 0):
        return kb
    rows = _v177_info_rows(kb)
    callbacks = {_v177_info_btn_cb(b) for row in rows for b in row or []}
    if 'v223:directive:home' not in callbacks:
        insert_at = len(rows)
        for i, row in enumerate(rows):
            if any((_v218_info_is_nav(b) for b in row or [])):
                insert_at = i
                break
        rows.insert(insert_at, [IB('🔒 Директивные чаты', callback_data='v223:directive:home')])
    return _v177_info_set_rows(kb, rows)

def v223_directive_callback_final(call, resolved: str) -> bool:
    raw = str(resolved or '')
    if not raw.startswith('v223:directive:'):
        return False
    try:
        cid = int(call.message.chat.id)
        uid = int(getattr(getattr(call, 'from_user', None), 'id', 0) or 0)
    except Exception:
        return True
    if cid != int(OWNER_ID or 0) or uid != int(OWNER_ID or 0):
        try:
            bot.answer_callback_query(call.id, 'Только основной владелец.', show_alert=True)
        except Exception:
            pass
        return True
    parts = raw.split(':')
    action = parts[2] if len(parts) > 2 else 'home'
    try:
        bot.answer_callback_query(call.id)
    except Exception:
        pass
    try:
        if action == 'info':
            safe_edit(bot, call, build_info_text(cid), reply_markup=build_info_keyboard(cid))
            return True
        if action == 'home':
            safe_edit(bot, call, _v223_directive_admin_text(), reply_markup=_v223_directive_admin_keyboard())
            return True
        if action == 'circle':
            level = 2 if int(parts[3]) == 2 else 1
            page = int(parts[4] or 0) if len(parts) > 4 else 0
            safe_edit(bot, call, _v223_directive_circle_text(level, page), reply_markup=_v223_directive_circle_keyboard(level, page))
            return True
        if action == 'chat':
            target = int(parts[3])
            page = int(parts[4] or 0) if len(parts) > 4 else 0
            safe_edit(bot, call, _v223_directive_card_text(target), reply_markup=_v223_directive_card_keyboard(target, page))
            return True
        if action == 'toggle':
            target = int(parts[3])
            page = int(parts[4] or 0) if len(parts) > 4 else 0
            value = set_directive_chat_enabled_v223(target, not directive_chat_enabled_v223(target))
            try:
                bot_journal('directive_admin_toggle_v224', target, f'enabled={int(value)}; ui_first=1; targeted_refresh=1')
            except Exception:
                pass
            _r10_kb = _v223_directive_card_keyboard(target, page)
            safe_edit(bot, call, _v223_directive_card_text(target), reply_markup=_r10_kb)
            try:
                bot.edit_message_reply_markup(chat_id=cid, message_id=int(call.message.message_id), reply_markup=_r10_kb)
            except Exception:
                pass
            try:
                v224_schedule_targeted_policy_refresh(target, markup_only=False)
            except Exception:
                pass
            return True
        if action == 'mode':
            mode = str(parts[3])
            target = int(parts[4])
            page = int(parts[5] or 0) if len(parts) > 5 else 0
            if mode not in V223_DIRECTIVE_MODES:
                return True
            value = v223_set_business_mode(target, mode, not _v215_mode_enabled(target, mode))
            try:
                bot_journal('directive_admin_mode_v224', target, f'mode={mode}; enabled={int(value)}; ui_first=1; targeted_refresh=1')
            except Exception:
                pass
            _r10_kb = _v223_directive_card_keyboard(target, page)
            safe_edit(bot, call, _v223_directive_card_text(target), reply_markup=_r10_kb)
            try:
                bot.edit_message_reply_markup(chat_id=cid, message_id=int(call.message.message_id), reply_markup=_r10_kb)
            except Exception:
                pass
            try:
                v224_schedule_targeted_policy_refresh(target, markup_only=False)
            except Exception:
                pass
            return True
        if action == 'annot':
            kind = 'iz_mr' if str(parts[3]) == 'izmr' else 'tz'
            target = int(parts[4])
            page = int(parts[5] or 0) if len(parts) > 5 else 0
            current = bool((_v223_directive_policy(target, False).get('annotations') or {}).get(kind, True))
            set_directive_annotation_v223(target, kind, not current)
            _r10_kb = _v223_directive_card_keyboard(target, page)
            safe_edit(bot, call, _v223_directive_card_text(target), reply_markup=_r10_kb)
            try:
                bot.edit_message_reply_markup(chat_id=cid, message_id=int(call.message.message_id), reply_markup=_r10_kb)
            except Exception:
                pass
            try:
                v224_schedule_targeted_policy_refresh(target, markup_only=True)
            except Exception:
                pass
            try:
                bot_journal('directive_admin_annotation_v224', target, f'kind={kind}; ui_first=1; markup_only=1')
            except Exception:
                pass
            return True
    except Exception as exc:
        try:
            log_error(f'v223 directive admin callback: {exc}')
        except Exception:
            pass
        try:
            bot.answer_callback_query(call.id, 'Не удалось применить настройку.', show_alert=True)
        except Exception:
            pass
        return True
    return True
try:
    _canon_bot_journal__001('v223_directive_admin_ready', int(OWNER_ID or 0), 'owner_private_admin=1; per_chat_modes=canonical; global_annotation_gate_wins=1')
except Exception:
    pass

def annotation_visibility_state_v226(kind: str, chat_id: int) -> dict:
    cid = int(chat_id)
    key = 'iz_mr' if str(kind or '').replace('-', '_').casefold() in {'iz_mr', 'izmr', 'marker'} else 'tz'
    try:
        global_on = bool(circle_annotation_global_enabled_v219(key, cid))
    except Exception:
        global_on = bool(_v219_annotation_settings().get(key, True))
    try:
        directive = bool(directive_chat_enabled_v223(cid))
    except Exception:
        directive = False
    local_on = True
    if directive:
        try:
            local_on = bool(directive_annotation_allowed_v223(cid, key))
        except Exception:
            local_on = True
    try:
        circle = bool(_v215_circle_business_chat(cid))
    except Exception:
        circle = False
    return {'kind': key, 'circle': circle, 'global': global_on, 'directive': directive, 'local': local_on, 'effective': bool(global_on and local_on)}

def v226_refresh_annotation_markup_all() -> int:
    changed = 0
    try:
        with _V221_LIVE_MARKUP_LOCK:
            rows = [(k, dict(v or {})) for k, v in _V221_LIVE_MARKUP.items()]
    except Exception:
        rows = []
    for (cid, mid), row in rows:
        try:
            before = row.get('markup')
            source = row.get('source_markup') if row.get('source_markup') is not None else before
            render = globals().get('v227_render_effective_contour_markup')
            after = render(source, str(row.get('text') or ''), int(cid)) if callable(render) else v221_finalize_contour_markup(source, int(cid))
            if _v221_markup_fingerprint(before) == _v221_markup_fingerprint(after):
                continue
            bot.edit_message_reply_markup(chat_id=int(cid), message_id=int(mid), reply_markup=after)
            v221_record_live_markup(int(cid), int(mid), after, str(row.get('text') or ''), source_markup=source)
            changed += 1
        except Exception:
            continue
    try:
        bot_journal('annotation_markup_refresh_v226', int(OWNER_ID or 0), f'changed={changed}; markup_only=1')
    except Exception:
        pass
    return changed

def v226_schedule_annotation_markup_refresh_all() -> None:

    def _job():
        try:
            v226_refresh_annotation_markup_all()
        except Exception as exc:
            try:
                bot_journal('annotation_markup_refresh_failed_v226', int(OWNER_ID or 0), str(exc)[:300], 'WARN')
            except Exception:
                pass
    try:
        pool = globals().get('GENERAL_TASK_POOL')
        if pool is not None and pool.submit_unique('v226-annotation-global-markup', _job):
            return
    except Exception:
        pass
    try:
        DELAYED_SCHEDULER.schedule('v226-annotation-global-markup', 0.05, _job)
    except Exception:
        pass

def _v226_annotation_callback_final(call, resolved: str) -> bool:
    raw = str(resolved or '')
    if not raw.startswith('v219:annot:toggle:'):
        return False
    try:
        cid = int(call.message.chat.id)
        uid = int(getattr(getattr(call, 'from_user', None), 'id', 0) or 0)
    except Exception:
        return True
    if cid != int(OWNER_ID or 0) or uid != int(OWNER_ID or 0):
        try:
            bot.answer_callback_query(call.id, 'Только основной владелец.', show_alert=True)
        except Exception:
            pass
        return True
    kind = 'iz_mr' if raw.rsplit(':', 1)[-1] == 'izmr' else 'tz'
    value = set_circle_annotation_button_v219(kind, not bool(circle_annotation_global_enabled_v219(kind)))
    try:
        bot.answer_callback_query(call.id, 'ВКЛ — кнопка доступна' if value else 'ВЫКЛ — кнопка скрыта и заблокирована')
    except Exception:
        pass
    _r10_kb = build_info_keyboard(cid)
    safe_edit(bot, call, build_info_text(cid), reply_markup=_r10_kb)
    try:
        bot.edit_message_reply_markup(chat_id=cid, message_id=int(call.message.message_id), reply_markup=_r10_kb)
    except Exception:
        pass
    v226_schedule_annotation_markup_refresh_all()
    try:
        bot_journal('annotation_global_toggle_v226', cid, f'kind={kind}; enabled={int(value)}; ui_first=1; async_markup_only=1')
    except Exception:
        pass
    return True
_V229_INFO_KB_PREV = _v223_build_info_keyboard

def _v229_build_info_keyboard(chat_id: int):
    cid = int(chat_id)
    kb = _V229_INFO_KB_PREV(cid)
    rows = _v177_info_rows(kb)
    cleaned = []
    for row in rows:
        keep = [b for b in row or [] if not _v177_info_btn_cb(b).startswith('gomonk_open')]
        if keep:
            cleaned.append(keep)
    rows = cleaned
    insert_at = len(rows)
    for i, row in enumerate(rows):
        if any((_v218_info_is_nav(b) for b in row or [])):
            insert_at = i
            break
    additions = []
    additions.append([IB(('✅ ВКЛ' if gomonk_enabled(cid, 'ars') else '⬜ ВЫКЛ') + ' · 🧳 Гомонковые ARS', callback_data='gomonk_open:ars')])
    additions.append([IB(('✅ ВКЛ' if gomonk_enabled(cid, 'usd') else '⬜ ВЫКЛ') + ' · 🧳 Гомонковые USD', callback_data='gomonk_open:usd')])
    if cid == int(OWNER_ID or 0):
        additions.append([IB(('✅ ВКЛ' if tasks_single_window_enabled_v229() else '⬜ ВЫКЛ') + ' · Задачи в одном окне', callback_data='v229:tasks:single_window')])
        try:
            additions.append([IB(('✅ ВКЛ' if constitution_protection_enabled_v232() else '⬜ ВЫКЛ') + ' · Защита Data Constitution', callback_data='v232:constitution:toggle')])
            additions.append([IB('🏛 Data Constitution · управление', callback_data='v232:constitution:open')])
        except Exception:
            pass
    rows[insert_at:insert_at] = additions
    return _v177_info_set_rows(kb, rows)
try:
    _canon_bot_journal__001('v229_info_ui_ready', int(OWNER_ID or 0), 'tasks_single_window_toggle=1; gomonk_ars_usd_rows=1; constitution_soft_guard=1; annotations_all_modes=1')
except Exception:
    pass
_V233_INFO_TEXT_PREV = _canon_build_info_text__001
_V233_INFO_KB_PREV = _v229_build_info_keyboard

def external_local_only_status_text_v233() -> str:
    active = storage_profile_v237_1() == STORAGE_PROFILE_LOCAL_V237_1
    env_forced = str(os.getenv('RENDER_TELEGRAM_ONLY', '') or '').strip().casefold() in {'1', 'true', 'yes', 'on', 'вкл'}
    return (f"🏠 ТОЛЬКО RENDER · выс-262\n\nПрофиль: {('✅ АКТИВЕН' if active else '⬜ не выбран')}" + (' · Render ENV' if env_forced else '') + '\n📡 Telegram backup-канал: ⬜ ВЫКЛ\n☁️ MEGA backup: ⬜ ВЫКЛ\n✅ Обычный Telegram API / команды / окна: ВКЛ\n✅ Google / курс валют / пользовательские функции: ВКЛ\n\nНа старте разрешено только чтение источника восстановления. После READY оба remote backup-контура остаются выключены. MEGA storage_control.json используется как маленький служебный маркер выбранного режима.')[:3900]

def external_local_only_keyboard_v233():
    kb = types.InlineKeyboardMarkup()
    kb.row(IB(('✅ ВКЛ' if external_local_only_v233_enabled() else '⬜ ВЫКЛ') + ' · Только Render', callback_data='v233:external:toggle'))
    kb.row(IB('🔙 Назад в Инфо', callback_data=f"d:{get_chat_store(int(OWNER_ID or 0)).get('current_view_day', today_key())}:info"))
    kb.row(IB('❌ Закрыть', callback_data='info_close'))
    return kb

def _v233_build_info_text(chat_id: int, *args, **kwargs) -> str:
    base = str(_V233_INFO_TEXT_PREV(int(chat_id), *args, **kwargs))
    if int(chat_id) == int(OWNER_ID or 0):
        line = ('✅ ВКЛ' if external_local_only_v233_enabled() else '⬜ ВЫКЛ') + ' · 🏠 Только Render (v234)'
        if line not in base:
            base = (base.rstrip() + '\n' + line).strip()
    return base[:3900]

def _v233_build_info_keyboard(chat_id: int):
    cid = int(chat_id)
    kb = _V233_INFO_KB_PREV(cid)
    if cid != int(OWNER_ID or 0):
        return kb
    rows = _v177_info_rows(kb)
    rows = [[b for b in row or [] if not _v177_info_btn_cb(b).startswith('v233:external:')] for row in rows]
    rows = [row for row in rows if row]
    insert_at = len(rows)
    for i, row in enumerate(rows):
        if any((_v218_info_is_nav(b) for b in row or [])):
            insert_at = i
            break
    label = ('✅ ВКЛ' if external_local_only_v233_enabled() else '⬜ ВЫКЛ') + ' · 🏠 Только Render (v234)'
    rows.insert(insert_at, [IB(label, callback_data='v233:external:open')])
    return _v177_info_set_rows(kb, rows)
try:
    V196_BRANCH_CATALOG['finance.ars'].update({'rev': 2, 'purpose': 'Принимать/считать ARS; в явном OWNER local-only продолжать работу на SQLite без внешней durability.', 'flow': ['ввод → распознавание', 'record.amount → SQLite', 'normal → MEGA/Constitution witness', 'local-only → SQLite + queued ledger', 'UI']})
    V196_BRANCH_CATALOG['export.google'].update({'rev': 6, 'purpose': 'Google export/catch-up продолжает работать в Только Render; режим блокирует только MEGA backup и Telegram backup-канал.'})
    V196_BRANCH_CATALOG['ui.info'].update({'rev': 14, 'purpose': 'Owner INFO + diagnostics + взаимоисключающие режимы хранения выс-262.'})
    V196_BRANCH_CATALOG['storage.mega'].update({'rev': 5, 'purpose': 'MEGA durable storage только в MEGA-профиле; в Только Render разрешён лишь control-plane marker/read для выбора восстановления.'})
    V196_BRANCH_CATALOG['storage.constitution'].update({'rev': 5, 'purpose': 'Semantic backup/restore protection + local-only immutable ledger queue/resume sync.'})
except Exception:
    pass
try:
    _canon_bot_journal__001('external_master_gate_ready_v246', int(OWNER_ID or 0), 'render_only blocks=mega_backup,telegram_backup; google/currency/telegram_api=allow')
except Exception:
    pass
_V234_INFO_TEXT_PREV = _v233_build_info_text
_V234_INFO_KB_PREV = _v233_build_info_keyboard

def config_guard_keyboard_v234():
    kb = types.InlineKeyboardMarkup()
    kb.row(IB('🔄 Проверить / восстановить настройки', callback_data='v234:config:verify'))
    kb.row(IB('✅ Принять текущее состояние', callback_data='v234:config:accept'))
    kb.row(IB('🗄 Базы MEGA / восстановление', callback_data='v242:mdb:list'))
    kb.row(IB('🔙 Назад в Инфо', callback_data=f"d:{get_chat_store(int(OWNER_ID or 0)).get('current_view_day', today_key())}:info"))
    kb.row(IB('❌ Закрыть', callback_data='info_close'))
    return kb

def _v234_build_info_text(chat_id: int, *args, **kwargs) -> str:
    base = str(_V234_INFO_TEXT_PREV(int(chat_id), *args, **kwargs))
    if int(chat_id) == int(OWNER_ID or 0):
        cp = config_guard_latest_local_v234() if callable(globals().get('config_guard_latest_local_v234')) else {}
        line = f"✅ · 🧩 Настройки после деплоя · gen {int((cp or {}).get('generation') or 0)}"
        if '🧩 Настройки после деплоя' not in base:
            base = (base.rstrip() + '\n' + line).strip()
    return base[:3900]

def _v234_build_info_keyboard(chat_id: int):
    cid = int(chat_id)
    kb = _V234_INFO_KB_PREV(cid)
    if cid != int(OWNER_ID or 0):
        return kb
    rows = _v177_info_rows(kb)
    rows = [[b for b in row or [] if not _v177_info_btn_cb(b).startswith('v234:config:')] for row in rows]
    rows = [r for r in rows if r]
    insert_at = len(rows)
    for i, row in enumerate(rows):
        if any((_v218_info_is_nav(b) for b in row or [])):
            insert_at = i
            break
    rows.insert(insert_at, [IB('✅ · 🧩 Настройки после деплоя', callback_data='v234:config:open')])
    return _v177_info_set_rows(kb, rows)
try:
    V196_BRANCH_CATALOG['ui.info'].update({'rev': 14, 'purpose': 'Owner INFO + Data Constitution + external master gate + configuration/deploy recovery status.'})
    V196_BRANCH_CATALOG['storage.constitution'].update({'rev': 6, 'purpose': 'Finance semantic guard + independent configuration constitution/checkpoints/transparent deploy recovery.'})
except Exception:
    pass
try:
    _canon_bot_journal__001('config_guard_ui_ready_v234', int(OWNER_ID or 0), 'config checkpoint/verify/accept controls ready')
except Exception:
    pass
_V237_1_STORAGE_INFO_TEXT_PREV = _v234_build_info_text
_V237_1_STORAGE_INFO_KB_PREV = _v234_build_info_keyboard

def storage_profiles_status_text_v237_1() -> str:
    st = storage_profile_status_v237_1()
    p = st.get('profile')
    return f"🗄 ХРАНИЛИЩЕ / BACKUP · выс-262\n\n{('✅' if p == STORAGE_PROFILE_LOCAL_V237_1 else '⬜')} 🏠 Только Render\n{('✅' if p == STORAGE_PROFILE_TELEGRAM_V237_1 else '⬜')} 📡 Telegram durable\n{('✅' if p == STORAGE_PROFILE_MEGA_V237_1 else '⬜')} ☁️ Вернуть Мегу\n\nTelegram backup-канал: {('✅ настроен' if st.get('telegram_available') else '⛔ не настроен')}\nMEGA credentials: {('✅ есть' if st.get('mega_configured') else '⛔ нет/MEGA_ENABLED=0')}\nMEGA active root: {st.get('mega_root') or '—'}\nБыстрый shard save: ~{(MEGA_DELTA_PRIORITY_DELAY_SECONDS if mega_backup_priority_enabled() else MEGA_DELTA_DELAY_SECONDS):g} сек.\nSYSTEM SQLite generation: каждые {system_snapshot_hours_v242()} ч. при наличии изменений.\n\nПрофили взаимоисключающие: включение одного автоматически отключает два остальных. MEGA использует один канонический root; business shard сохраняются быстро, а полный SQLite generation создаётся редко."[:3900]

def storage_profiles_keyboard_v237_1():
    p = storage_profile_v237_1()
    kb = types.InlineKeyboardMarkup()
    kb.row(IB(('✅ ' if p == STORAGE_PROFILE_LOCAL_V237_1 else '⬜ ') + '🏠 Только Render', callback_data='v237:storage:profile_local'))
    kb.row(IB(('✅ ' if p == STORAGE_PROFILE_TELEGRAM_V237_1 else '⬜ ') + '📡 Telegram durable', callback_data='v237:storage:profile_tg'))
    kb.row(IB(('✅ ' if p == STORAGE_PROFILE_MEGA_V237_1 else '⬜ ') + '☁️ Вернуть Мегу', callback_data='v237:storage:profile_mega'))
    if p == STORAGE_PROFILE_TELEGRAM_V237_1:
        kb.row(IB('🗄 SQLite snapshot сейчас', callback_data='v237:storage:tg_snapshot'), IB('♻️ HEAD', callback_data='v237:storage:tg_refresh'))
    kb.row(IB(f'🕕 SYSTEM generation: {system_snapshot_hours_v242()} ч · переключить', callback_data='v242:system_snapshot:toggle'))
    kb.row(IB('🔐 SECRET backend', callback_data='v237:storage:secret_open'))
    kb.row(IB('🔙 Назад в Инфо', callback_data=f"d:{get_chat_store(int(OWNER_ID or 0)).get('current_view_day', today_key())}:info"))
    kb.row(IB('❌ Закрыть', callback_data='info_close'))
    return kb

def secret_storage_status_text_v234() -> str:
    requested = str(globals().get('secret_storage_backend_v234', lambda: 'telegram')())
    effective = str(globals().get('secret_storage_effective_backend_v234', lambda: requested)())
    return f"🔐 SECRET STORAGE · выс-262\n\nПрофиль backup: {storage_profile_v237_1()}\nSECRET выбран: {('☁️ MEGA' if requested == 'mega' else '📡 Telegram')}\nЭффективно: {('☁️ MEGA' if effective == 'mega' else '📡 Telegram')}\n\nПри выборе общего профиля MEGA SECRET автоматически переводится в MEGA; при двух других профилях — в Telegram."[:3900]

def secret_storage_keyboard_v234():
    kb = types.InlineKeyboardMarkup()
    req = secret_storage_backend_v234()
    p = storage_profile_v237_1()
    kb.row(IB(('✅ ' if req == 'telegram' else '⬜ ') + '📡 Telegram', callback_data='v237:storage:secret_tg'))
    kb.row(IB(('✅ ' if req == 'mega' else '⬜ ') + '☁️ MEGA', callback_data='v237:storage:secret_mega'))
    kb.row(IB('🔙 Хранилище', callback_data='v237:storage:open'))
    kb.row(IB('❌ Закрыть', callback_data='info_close'))
    return kb

def telegram_durable_status_text_v236() -> str:
    st = telegram_durable_status_v234()
    slots = telegram_stable_slot_status_v236() if telegram_durable_primary_v234() else {'count': 0, 'chat_backup_count': 0, 'durable_count': 0}
    return f"📡 TELEGRAM DURABLE · выс-262\n\nПрофиль: {('✅ АКТИВЕН' if telegram_durable_primary_v234() else '⬜ ВЫКЛ')}\nКанал: {('✅ настроен' if st.get('configured') else '⛔ нет')}\nHEAD gen: {int(st.get('generation') or 0)} · slots {int(slots.get('count') or 0)}\nФайлы используют постоянные message-slots: create once → edit; после удаления → recreate once → дальше edit."[:3900]

def telegram_durable_keyboard_v234():
    return storage_profiles_keyboard_v237_1()

def mega_contour_status_text_v234() -> str:
    return storage_profiles_status_text_v237_1()

def mega_contour_keyboard_v234():
    return storage_profiles_keyboard_v237_1()

def _v237_1_storage_build_info_text(chat_id: int, *args, **kwargs) -> str:
    base = str(_V237_1_STORAGE_INFO_TEXT_PREV(int(chat_id), *args, **kwargs))
    if int(chat_id) == int(OWNER_ID or 0):
        p = storage_profile_v237_1()
        extra = [('✅' if p == STORAGE_PROFILE_LOCAL_V237_1 else '⬜') + ' · 🏠 Только Render', ('✅' if p == STORAGE_PROFILE_TELEGRAM_V237_1 else '⬜') + ' · 📡 Telegram durable', ('✅' if p == STORAGE_PROFILE_MEGA_V237_1 else '⬜') + ' · ☁️ Вернуть Мегу', f"📂 MEGA: {str(globals().get('MEGA_BACKUP_DIR') or '—')}"]
        for line in extra:
            if line not in base:
                base = (base.rstrip() + '\n' + line).strip()

    # v246 visual identity contract: the bot name/version is literally the first
    # and the last non-empty line of the main INFO window. Older wrappers may
    # append diagnostics after the historical footer, so normalize only this
    # presentation boundary without changing any business/status content.
    identity = f"🤖 {BOT_DISPLAY_NAME} | {version_animal_badge()} | {VERSION}"
    body_lines = [line for line in base.splitlines() if line.strip() != identity]
    body = '\n'.join(body_lines).strip()
    max_chars = 3900
    fixed = len(identity) * 2 + 4
    if len(body) > max(0, max_chars - fixed):
        body = body[:max(0, max_chars - fixed)].rstrip()
    return f"{identity}\n\n{body}\n\n{identity}" if body else f"{identity}\n\n{identity}"

def _v237_1_storage_build_info_keyboard(chat_id: int):
    cid = int(chat_id)
    kb = _V237_1_STORAGE_INFO_KB_PREV(cid)
    if cid != int(OWNER_ID or 0):
        return kb
    rows = _v177_info_rows(kb)
    prefixes = ('v236:storage:', 'v234:storage:', 'v237:storage:', 'v233:external:')
    rows = [[b for b in row or [] if not any((_v177_info_btn_cb(b).startswith(x) for x in prefixes))] for row in rows]
    rows = [r for r in rows if r]
    insert_at = len(rows)
    for i, row in enumerate(rows):
        if any((_v218_info_is_nav(b) for b in row or [])):
            insert_at = i
            break
    p = storage_profile_v237_1()
    additions = [[IB(('✅ ' if p == STORAGE_PROFILE_LOCAL_V237_1 else '⬜ ') + '🏠 Только Render', callback_data='v237:storage:profile_local')], [IB(('✅ ' if p == STORAGE_PROFILE_TELEGRAM_V237_1 else '⬜ ') + '📡 Telegram durable', callback_data='v237:storage:profile_tg')], [IB(('✅ ' if p == STORAGE_PROFILE_MEGA_V237_1 else '⬜ ') + '☁️ Вернуть Мегу', callback_data='v237:storage:profile_mega')], [IB('🗄 Хранилище · подробно', callback_data='v237:storage:open')]]
    rows[insert_at:insert_at] = additions
    return _v177_info_set_rows(kb, rows)
try:
    _canon_bot_journal__001('v237_1_storage_profiles_ready', int(OWNER_ID or 0), f"profile={storage_profile_v237_1()}; mega_root={globals().get('MEGA_BACKUP_DIR', '')}")
except Exception:
    pass

def _v240_mode_name(mode: str) -> str:
    mode = _storage_profile_normalize_v237_1(mode)
    return {STORAGE_PROFILE_LOCAL_V237_1: '🏠 Только Render', STORAGE_PROFILE_TELEGRAM_V237_1: '📡 Telegram durable', STORAGE_PROFILE_MEGA_V237_1: '☁️ Вернуть Мегу'}.get(mode, mode)

def storage_modes_text_v240() -> str:
    p = storage_profile_v237_1()
    return f"⚙️ РЕЖИМЫ · выс-262\n\nАктивный режим: {_v240_mode_name(p)}\n\n{('✅' if p == STORAGE_PROFILE_LOCAL_V237_1 else '⬜')} 🏠 Только Render\n{('✅' if p == STORAGE_PROFILE_TELEGRAM_V237_1 else '⬜')} 📡 Telegram durable\n{('✅' if p == STORAGE_PROFILE_MEGA_V237_1 else '⬜')} ☁️ Вернуть Мегу\n\nВ «Только Render» работают все обычные функции бота, Google, курс валют, команды, окна и переключатели; отключены только MEGA-хранилище и Telegram backup-канал. После deploy режим берётся из MEGA storage_control.json. Если сохранён Render, источник восстановления выбирается отдельно: сначала полнота snapshot, затем свежесть."[:3900]

def storage_modes_keyboard_v240():
    p = storage_profile_v237_1()
    kb = types.InlineKeyboardMarkup()
    kb.row(IB(('✅ ' if p == STORAGE_PROFILE_LOCAL_V237_1 else '⬜ ') + '🏠 Только Render', callback_data='v240:modes:render'))
    kb.row(IB(('✅ ' if p == STORAGE_PROFILE_TELEGRAM_V237_1 else '⬜ ') + '📡 Telegram durable', callback_data='v240:modes:telegram'))
    kb.row(IB(('✅ ' if p == STORAGE_PROFILE_MEGA_V237_1 else '⬜ ') + '☁️ Вернуть Мегу', callback_data='v240:modes:mega'))
    kb.row(IB('⚙️ Процессы / скорость', callback_data='v176:menu'))
    kb.row(IB('⬅️ Назад в INFO', callback_data='v176:back_info'), IB('✖️ Закрыть', callback_data='info_close'))
    return kb

def storage_mode_detail_text_v240(mode: str) -> str:
    mode = _storage_profile_normalize_v237_1(mode)
    active = storage_profile_v237_1() == mode
    f = storage_mode_features_v240(mode)
    lines = [f'{_v240_mode_name(mode)} · v240', '', f"{('✅ Режим ВКЛ' if active else '⬜ Режим ВЫКЛ')}", '', 'Состав режима:']
    labels = {'render': {'local_sqlite': 'SQLite', 'local_queues': 'Локальные очереди', 'local_runtime': 'Local runtime state'}, 'telegram_durable': {'snapshot': 'SQLite snapshot', 'delta': 'Delta', 'config': 'Config checkpoint', 'tasks': 'Durable tasks', 'boot_restore': 'Restore при deploy'}, 'mega': {'delta': 'Shard delta + HEAD', 'config': 'Config checkpoint', 'tasks': 'Durable tasks', 'system_generation': 'SYSTEM generation 6/12 ч', 'boot_restore': 'Restore при deploy', 'cleanup': 'MEGA cleanup'}}
    locked = _STORAGE_MODE_LOCKED_FEATURES_V240.get(mode, set())
    for key, label in labels.get(mode, {}).items():
        lines.append(f"{('🔒' if key in locked else '✅' if f.get(key) else '⬜')} {label}")
    if mode == STORAGE_PROFILE_LOCAL_V237_1:
        lines += ['', '✅ Только Render сохраняет все обычные функции и внешние пользовательские сервисы. Отключены только MEGA backup и Telegram backup-канал. При deploy разрешён одноразовый Recovery Authority: восстановление из лучшего remote snapshot, затем remote storage снова выключается.']
    return '\n'.join(lines)[:3900]

def storage_mode_detail_keyboard_v240(mode: str):
    mode = _storage_profile_normalize_v237_1(mode)
    active = storage_profile_v237_1() == mode
    f = storage_mode_features_v240(mode)
    kb = types.InlineKeyboardMarkup()
    kb.row(IB('✅ ВКЛ' if active else '⬜ ВЫКЛ · Включить режим', callback_data=f'v240:modes:activate:{mode}'))
    labels = {'render': {'local_sqlite': 'SQLite', 'local_queues': 'Локальные очереди', 'local_runtime': 'Local runtime state'}, 'telegram_durable': {'snapshot': 'SQLite snapshot', 'delta': 'Delta', 'config': 'Config checkpoint', 'tasks': 'Durable tasks', 'boot_restore': 'Restore при deploy'}, 'mega': {'delta': 'Shard delta + HEAD', 'config': 'Config checkpoint', 'tasks': 'Durable tasks', 'system_generation': 'SYSTEM generation', 'boot_restore': 'Restore при deploy', 'cleanup': 'MEGA cleanup'}}
    locked = _STORAGE_MODE_LOCKED_FEATURES_V240.get(mode, set())
    for key, label in labels.get(mode, {}).items():
        if key in locked:
            kb.row(IB(f'🔒 {label}', callback_data='none'))
        else:
            kb.row(IB(('✅ ' if f.get(key) else '⬜ ') + label, callback_data=f'v240:modes:feature:{mode}:{key}'))
    if mode == STORAGE_PROFILE_MEGA_V237_1:
        kb.row(IB(f'🕕 SYSTEM generation: {system_snapshot_hours_v242()} ч', callback_data='v242:system_snapshot:toggle'))
    kb.row(IB('⚙️ Процессы / скорость', callback_data='v176:menu'))
    kb.row(IB('⬅️ Режимы', callback_data='v240:modes:open'), IB('✖️ Закрыть', callback_data='info_close'))
    return kb
_V240_INFO_KB_PREV = _v237_1_storage_build_info_keyboard

def _canon_build_info_keyboard__002(chat_id: int):
    kb = _V240_INFO_KB_PREV(int(chat_id))
    if int(chat_id) != int(OWNER_ID or 0):
        return kb
    rows = _v177_info_rows(kb)

    def drop(btn):
        cb = _v177_info_btn_cb(btn)
        return cb.startswith(('v237:storage:', 'v236:storage:', 'v234:storage:', 'v233:external:')) or cb in {'v176:menu', 'v175:heavy_toggle', 'v240:modes:open', 'v232:constitution:toggle', 'v255:constitution:loss_toggle'}
    rows = [[b for b in r or [] if not drop(b)] for r in rows]
    rows = [r for r in rows if r]
    insert = len(rows)
    for i, r in enumerate(rows):
        if any((_v218_info_is_nav(b) for b in r or [])):
            insert = i
            break
    # v261: three explicit Google sync engines directly in INFO. The historical
    # incremental engine is the default, as requested; switching is per Google space.
    rows = [[b for b in r or [] if not _v177_info_btn_cb(b).startswith('v261:gsync:')] for r in rows]
    rows = [r for r in rows if r]
    ginsert = None
    for i, r in enumerate(rows):
        if any(_v177_info_btn_cb(b).startswith('v169:gmenu:') for b in (r or [])):
            ginsert = i + 1
            break
    if ginsert is None:
        ginsert = insert
    smode = _v261_google_sync_engine(int(chat_id)) if callable(globals().get('_v261_google_sync_engine')) else 'previous'
    sync_rows = [
        [IB(('✅ ' if smode == 'previous' else '⬜ ') + 'Sync · ПРЕДЫДУЩАЯ', callback_data=f'v261:gsync:{int(chat_id)}:previous')],
        [IB(('✅ ' if smode == 'fixed' else '⬜ ') + 'Sync · ИСПРАВЛЕННАЯ', callback_data=f'v261:gsync:{int(chat_id)}:fixed')],
        [IB(('✅ ' if smode == 'new' else '⬜ ') + 'Sync · НОВАЯ', callback_data=f'v261:gsync:{int(chat_id)}:new')],
    ]
    rows[ginsert:ginsert] = sync_rows
    # Recompute tail insertion after adding sync rows so the service controls stay near navigation.
    insert = len(rows)
    for i, r in enumerate(rows):
        if any((_v218_info_is_nav(b) for b in r or [])):
            insert = i
            break
    loss_label = ('✅ ВКЛ' if constitution_loss_guard_enabled_v255() else '⬜ ВЫКЛ') + ' · 🛡 Защита потери записей'
    rows.insert(insert, [IB(loss_label, callback_data='v255:constitution:loss_toggle')])
    rows.insert(insert + 1, [IB('⚙️ Режимы', callback_data='v240:modes:open')])
    return _v177_info_set_rows(kb, rows)

def mega_database_browser_text_v242() -> str:
    rows = _v242_mega_database_catalog(14) if callable(globals().get('_v242_mega_database_catalog')) else []
    active = sum((1 for r in rows if r.get('active')))
    return f'🗄 БАЗЫ MEGA / ВОССТАНОВЛЕНИЕ\n\nПорядок обычного старта: current_manifest → последняя generation → legacy latest.\nЗдесь можно вручную выбрать конкретную SQLite-базу. Перед заменой бот создаст pre_restore, затем после подтверждённого восстановления сразу опубликует НОВУЮ canonical generation в MEGA.\n\nНайдено файлов: {len(rows)} · текущая active: {active}'[:3900]

def mega_database_browser_keyboard_v242():
    kb = types.InlineKeyboardMarkup()
    rows = _v242_mega_database_catalog(14) if callable(globals().get('_v242_mega_database_catalog')) else []
    if not rows:
        kb.row(IB('🔄 Повторить поиск', callback_data='v242:mdb:list'))
    for i, row in enumerate(rows, 1):
        flag = '✅ ' if row.get('active') else ''
        kind = {'generation': 'GEN', 'legacy_latest': 'LATEST', 'legacy_history': 'HIST', 'pre_restore': 'PRE'}.get(str(row.get('kind')), 'DB')
        name = str(row.get('name') or '')
        short = name if len(name) <= 42 else name[:39] + '…'
        kb.row(IB(f'{flag}{i}. {kind} · {short}', callback_data=f"v242:mdb:pick:{row.get('token')}"))
    kb.row(IB('🔄 Обновить', callback_data='v242:mdb:list'))
    kb.row(IB('🔙 Настройки после деплоя', callback_data='v234:config:open'))
    kb.row(IB('❌ Закрыть', callback_data='info_close'))
    return kb

def mega_database_confirm_text_v242(token: str) -> str:
    row = _v242_mega_catalog_entry(token) if callable(globals().get('_v242_mega_catalog_entry')) else {}
    return f"⚠️ ВОССТАНОВЛЕНИЕ БАЗЫ ИЗ MEGA\n\nФайл: {row.get('name') or 'не найден'}\nТип: {row.get('kind') or '—'}\nActive сейчас: {('да' if row.get('active') else 'нет')}\n\nБудет создан pre_restore текущей базы. Затем выбранная SQLite полностью заменит рабочую базу без merge. После успешной замены бот сразу создаст новую canonical generation в MEGA."[:3900]

def mega_database_confirm_keyboard_v242(token: str):
    kb = types.InlineKeyboardMarkup()
    kb.row(IB('✅ ПОДТВЕРДИТЬ восстановление', callback_data=f'v242:mdb:confirm:{token}'))
    kb.row(IB('⬅️ Назад к базам', callback_data='v242:mdb:list'))
    kb.row(IB('❌ Закрыть', callback_data='info_close'))
    return kb
# v262
