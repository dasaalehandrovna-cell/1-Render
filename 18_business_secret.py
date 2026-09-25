# v267
"""ОЧНИСЬ 12.35 · physical owner: secret.

Этот файл — единственное физическое место тел функций домена.
Он НЕ запускается отдельно и НЕ импортируется как Python-модуль.
bot.py читает его как каталог исходников и устанавливает нужную стадию в исторической точке runtime.
Последняя версия каждого публичного символа сохраняет обычное имя; старые стадии помечены _legacy_sXXXX_.
"""

# --- secret:0001 · from 01_core_data.py:3905 · public total_secret_mask_enabled ---
def total_secret_mask_enabled(chat_id: int | None=None) -> bool:
    try:
        if chat_id is not None:
            scoped = owner_scoped_settings(int(chat_id))
            if 'total_secret_mask_enabled' in scoped:
                return bool(scoped.get('total_secret_mask_enabled'))
        gs = (data or {}).setdefault('_global_settings', {})
        return bool(gs.get('total_secret_mask_enabled', False))
    except Exception:
        return False

# --- secret:0002 · from 01_core_data.py:3916 · public set_total_secret_mask_enabled ---
def set_total_secret_mask_enabled(enabled: bool, chat_id: int | None=None):
    try:
        if chat_id is not None:
            owner_scoped_settings(int(chat_id))['total_secret_mask_enabled'] = bool(enabled)
            save_data(data, chat_ids=[int(chat_id)])
            schedule_config_backup_for_chats(int(chat_id), delay=0.3)
        else:
            data.setdefault('_global_settings', {})['total_secret_mask_enabled'] = bool(enabled)
            save_data(data)
    except Exception as e:
        log_error(f'set_total_secret_mask_enabled: {e}')

# --- secret:0003 · from 01_core_data.py:3928 · public toggle_total_secret_mask ---
def toggle_total_secret_mask(chat_id: int | None=None) -> bool:
    new_value = not total_secret_mask_enabled(chat_id)
    set_total_secret_mask_enabled(new_value, chat_id)
    return new_value

# --- secret:0004 · from 01_core_data.py:3933 · public total_secret_mask_label ---
def total_secret_mask_label(chat_id: int | None=None) -> str:
    return '✅ 🪷 Маска: ВКЛ' if total_secret_mask_enabled(chat_id) else '⬜ 🪷 Маска: ВЫКЛ'

# --- secret:0005 · from 01_core_data.py:5160 · public _secret_notes_list ---
def _secret_notes_list() -> list:
    try:
        arr = data.setdefault('_secret_notes', [])
        if not isinstance(arr, list):
            data['_secret_notes'] = []
            arr = data['_secret_notes']
        return arr
    except Exception:
        return []

# --- secret:0006 · from 01_core_data.py:5170 · public _secret_notes_local_path ---
def _secret_notes_local_path() -> str:
    try:
        os.makedirs(MEGA_LOCAL_TMP_DIR, exist_ok=True)
        return os.path.join(MEGA_LOCAL_TMP_DIR, 'secret_notes_owner.json')
    except Exception:
        return 'secret_notes_owner.json'

# --- secret:0007 · from 01_core_data.py:5177 · public _save_secret_notes_plain_to_file ---
def _save_secret_notes_plain_to_file() -> str | None:
    try:
        payload = {'kind': 'owner_secret_notes_plain_text', 'version': VERSION, 'created_at': now_local().isoformat(timespec='seconds'), 'warning': 'plain text, not encrypted', 'notes': _secret_notes_list()}
        path = _secret_notes_local_path()
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        return path
    except Exception as e:
        log_error(f'_save_secret_notes_plain_to_file: {e}')
        return None

# --- secret:0008 · from 01_core_data.py:5188 · public upload_secret_notes_to_mega ---
def upload_secret_notes_to_mega() -> bool:
    """Совместимость: секреты О9 теперь идут в единый файл чата владельца."""
    try:
        return bool(OWNER_ID and upload_chat_secrets_to_mega(int(OWNER_ID)))
    except Exception as e:
        log_error(f'upload_secret_notes_to_mega: {e}')
        return False

# --- secret:0009 · from 01_core_data.py:5216 · public _cancel_o9_secret_timer ---
def _cancel_o9_secret_timer(key):
    try:
        _o9_secret_action_timers.pop(key, None)
        DELAYED_SCHEDULER.cancel(_o9_action_scheduler_key(key))
    except Exception:
        pass

# --- secret:0010 · from 01_core_data.py:5227 · public _secret_wait_keyboard ---
def _secret_wait_keyboard(chat_id: int, remaining: int=O9_SECRET_WAIT_SECONDS):
    kb = types.InlineKeyboardMarkup()
    store = get_chat_store(chat_id)
    kb.row(IB(f'❌ Закрыть {_format_mmss(remaining)}', callback_data='secret_cancel'), IB('⬅️ Назад осн. окно', callback_data=f"d:{store.get('current_view_day', today_key())}:back_main"))
    return kb

# --- secret:0011 · from 01_core_data.py:5233 · public _secret_wait_prompt_text ---
def _secret_wait_prompt_text(remaining: int | None=None) -> str:
    tail = ''
    if remaining is not None:
        tail = f'\n\n⏳ Осталось: {_format_mmss(remaining)}'
    return wm_common('🔐 Секретные данные\n\nОтправь одним сообщением текст, который нужно сохранить.\nБот удалит твоё сообщение после сохранения.\n\nВажно: сейчас хранение обычным текстом, без шифрования.' + tail, 9)

# --- secret:0012 · from 01_core_data.py:5239 · public _cancel_o9_secret_wait_timer ---
def _cancel_o9_secret_wait_timer(chat_id: int):
    key = int(chat_id)
    with _o9_secret_click_lock:
        item = _o9_secret_wait_timers.get(key)
        if isinstance(item, dict):
            item['cancelled'] = True
        _o9_secret_wait_timers.pop(key, None)
    try:
        DELAYED_SCHEDULER.cancel(f'o9-secret-wait:{key}')
    except Exception:
        pass

# --- secret:0013 · from 01_core_data.py:5251 · public schedule_o9_secret_wait_timeout ---
def schedule_o9_secret_wait_timeout(chat_id: int, prompt_message_id: int, delay: int=O9_SECRET_WAIT_SECONDS):
    """Автоотмена ожидания секрета без частого редактирования таймера."""
    key = int(chat_id)
    with _o9_secret_click_lock:
        prev = _o9_secret_wait_timers.get(key)
        if isinstance(prev, dict):
            prev['cancelled'] = True
        generation = int(time.time() * 1000)
        token = {'generation': generation, 'cancelled': False}
        _o9_secret_wait_timers[key] = token

    def _job():
        try:
            with _o9_secret_click_lock:
                current = _o9_secret_wait_timers.get(key)
                if current is not token or token.get('cancelled'):
                    return
                _o9_secret_wait_timers.pop(key, None)
            _clear_secret_wait(chat_id, delete_prompt=True)
            send_and_auto_delete(chat_id, '⌛ Время принятия секретных данных истекло.', 8)
        except Exception as e:
            log_error(f'schedule_o9_secret_wait_timeout({chat_id},{prompt_message_id}): {e}')
    DELAYED_SCHEDULER.schedule(f'o9-secret-wait:{key}', int(delay), _job)

# --- secret:0014 · from 01_core_data.py:5336 · public _start_secret_wait ---
def _start_secret_wait(chat_id: int, message_id: int | None=None):
    try:
        store = get_chat_store(chat_id)
        store['secret_wait'] = {'type': 'secret_note_add', 'started_at': now_local().isoformat(timespec='seconds'), 'window_msg_id': int(message_id or 0)}
        save_data(data)
        kb = _secret_wait_keyboard(chat_id, O9_SECRET_WAIT_SECONDS)
        text = _secret_wait_prompt_text(O9_SECRET_WAIT_SECONDS)
        if message_id:
            try:
                bot.edit_message_text(text, chat_id=chat_id, message_id=message_id, reply_markup=kb)
                store['secret_wait']['prompt_msg_id'] = int(message_id)
                save_data(data)
                schedule_o9_secret_wait_timeout(chat_id, int(message_id), O9_SECRET_WAIT_SECONDS)
                return
            except Exception:
                pass
        sent = _tg_call_retry(bot.send_message, chat_id, text, reply_markup=kb, purpose='secret_prompt')
        store['secret_wait']['prompt_msg_id'] = sent.message_id
        save_data(data)
        schedule_o9_secret_wait_timeout(chat_id, sent.message_id, O9_SECRET_WAIT_SECONDS)
    except Exception as e:
        log_error(f'_start_secret_wait({chat_id}): {e}')

# --- secret:0015 · from 01_core_data.py:5359 · public _format_secret_notes_text ---
def _format_secret_notes_text() -> str:
    notes = _secret_notes_list()
    if not notes:
        return '🔐 Секретные данные\n\nПока пусто.'
    lines = ['🔐 Секретные данные', '']
    for i, item in enumerate(notes, start=1):
        ts = str((item or {}).get('ts') or '')
        body = str((item or {}).get('text') or '')
        lines.append(f'{i}. {ts}\n{body}')
        lines.append('')
    text = '\n'.join(lines).strip()
    if len(text) > 3900:
        text = text[-3900:]
        text = '🔐 Секретные данные (последняя часть)\n\n' + text
    return text

# --- secret:0016 · from 01_core_data.py:5375 · public _send_secret_notes_to_owner ---
def _send_secret_notes_to_owner(chat_id: int, message_id: int | None=None):
    try:
        open_secret_day_window(chat_id, chat_id, message_id=message_id)
    except Exception as e:
        log_error(f'_send_secret_notes_to_owner({chat_id}): {e}')

# --- secret:0017 · from 01_core_data.py:5381 · public _clear_secret_wait ---
def _clear_secret_wait(chat_id: int, delete_prompt: bool=False):
    try:
        _cancel_o9_secret_wait_timer(chat_id)
        store = get_chat_store(chat_id)
        wait = store.get('secret_wait') or {}
        msg_id = int(wait.get('prompt_msg_id') or wait.get('window_msg_id') or 0)
        store['secret_wait'] = None
        save_data(data)
        if delete_prompt and msg_id:
            try:
                bot.delete_message(chat_id, msg_id)
            except Exception:
                pass
            try:
                _clear_stored_window(chat_id, 'info_msg_id', msg_id)
            except Exception:
                pass
    except Exception as e:
        log_error(f'_clear_secret_wait({chat_id}): {e}')

# --- secret:0018 · from 01_core_data.py:5401 · public handle_secret_note_message ---
def handle_secret_note_message(msg) -> bool:
    """Сохраняет секретное сообщение владельца и удаляет исходный текст."""
    try:
        if getattr(msg, 'content_type', None) != 'text':
            return False
        chat_id = int(msg.chat.id)
        if not is_owner_chat(chat_id):
            return False
        store = get_chat_store(chat_id)
        wait = store.get('secret_wait')
        if not wait or wait.get('type') != 'secret_note_add':
            return False
        text = (msg.text or '').strip()
        if not text:
            return True
        save_secret_message(chat_id, msg, cleaned_text=text)
        delete_secret_source_message(msg)
        _clear_secret_wait(chat_id, delete_prompt=True)
        status = '✅ Секрет сохранён в единый файл чата и поставлен в очередь MEGA.'
        sent = _tg_call_retry(bot.send_message, chat_id, status, purpose='secret_saved_notice')
        try:
            delete_message_later(chat_id, sent.message_id, 12)
        except Exception:
            pass
        return True
    except Exception as e:
        log_error(f'handle_secret_note_message: {e}')
        return True

# --- secret:0019 · from 01_core_data.py:5430 · public _v177_legacy_0020_handle_o9_secret_triple_click ---
def _v177_legacy_0020_handle_o9_secret_triple_click(call, data_str: str) -> bool:
    """Перехватывает О9: Закрыть ×3 = ввод секрета, Назад ×3 = показать секреты."""
    try:
        if not _is_o9_owner_call(call):
            return False
        chat_id = int(call.message.chat.id)
        msg_id = int(call.message.message_id)
        kind = None
        day_key = get_chat_store(chat_id).get('current_view_day', today_key())
        if data_str == 'info_close':
            kind = 'close'
        elif str(data_str or '').startswith('d:'):
            parts = str(data_str).split(':', 2)
            action = parts[2] if len(parts) >= 3 else ''
            if action == 'back_main':
                kind = 'back'
                day_key = parts[1] or day_key
        if not kind:
            return False
        key = (chat_id, msg_id, kind)
        now_ts = time.time()
        with _o9_secret_click_lock:
            item = _o9_secret_clicks.get(key) or {'count': 0, 'ts': 0}
            if now_ts - float(item.get('ts', 0) or 0) > O9_SECRET_CLICK_WINDOW_SECONDS:
                item = {'count': 0, 'ts': 0}
            item['count'] = int(item.get('count', 0) or 0) + 1
            item['ts'] = now_ts
            _o9_secret_clicks[key] = item
            _cancel_o9_secret_timer(key)
            count = int(item['count'])
            if count < 3:
                scheduler_key = _o9_action_scheduler_key(key)
                if kind == 'close':
                    deadline = DELAYED_SCHEDULER.schedule(scheduler_key, O9_SECRET_CLICK_WINDOW_SECONDS + 0.2, _o9_delayed_close, chat_id, msg_id, key)
                else:
                    deadline = DELAYED_SCHEDULER.schedule(scheduler_key, O9_SECRET_CLICK_WINDOW_SECONDS + 0.2, _o9_delayed_back_main, chat_id, msg_id, day_key, key)
                _o9_secret_action_timers[key] = deadline
        if count >= 3:
            _cancel_o9_secret_timer(key)
            with _o9_secret_click_lock:
                _o9_secret_clicks.pop(key, None)
            if kind == 'close':
                _start_secret_wait(chat_id, msg_id)
                try:
                    bot.answer_callback_query(call.id, '🔐 Секретные данные')
                except Exception:
                    pass
            else:
                _send_secret_notes_to_owner(chat_id, msg_id)
                try:
                    bot.answer_callback_query(call.id, '🔐 Отправил секретные данные')
                except Exception:
                    pass
            return True
        try:
            bot.answer_callback_query(call.id, f'Секрет: {count}/3', show_alert=False)
        except Exception:
            pass
        return True
    except Exception as e:
        log_error(f'handle_o9_secret_triple_click: {e}')
        return False

# --- secret:0020 · from 01_core_data.py:11041 · public _durable_secret_edit_witness ---
def _durable_secret_edit_witness(chat_id: int, record_id: int, text: str) -> dict:
    return {'chat_id': int(chat_id), 'record_id': int(record_id), 'text': str(text or '').strip()}

# --- secret:0021 · from 01_core_data.py:11621 · public _durable_secret_effect_complete ---
def _durable_secret_effect_complete(payload: dict) -> bool:
    raw, source_chat_id, source_msg_id, _group_id = _durable_payload_message(payload)
    if not isinstance(raw, dict) or source_chat_id is None or source_msg_id is None:
        return True
    text = str(raw.get('text') or raw.get('caption') or '')
    secret_expected = False
    try:
        secret_expected = bool(is_total_secret_mode(source_chat_id))
    except Exception:
        pass
    if not secret_expected:
        try:
            marked, _cleaned = _extract_secret_codeword(text)
            secret_expected = bool(marked)
        except Exception:
            secret_expected = False
    if not secret_expected:
        return True
    try:
        return any((int(r.get('source_msg_id') or 0) == int(source_msg_id) for r in _secret_records(source_chat_id) if isinstance(r, dict)))
    except Exception:
        return False

# --- secret:0022 · from 01_core_data.py:12057 · public _durable_note_secret_edit_witness ---
def _durable_note_secret_edit_witness(witness: dict):
    try:
        ctx = getattr(_TELEGRAM_UPDATE_CONTEXT, 'value', None)
        if not isinstance(ctx, dict) or not isinstance(witness, dict):
            return
        rows = ctx.setdefault('secret_edits', [])
        key = (int(witness.get('chat_id')), int(witness.get('record_id')))
        rows[:] = [r for r in rows if (int(r.get('chat_id')), int(r.get('record_id'))) != key]
        rows.append(_delta_json_clone(witness))
    except Exception:
        pass

# --- secret:0023 · from 01_core_data.py:12641 · public _repair_safe_missing_forward_secret_effects ---
def _repair_safe_missing_forward_secret_effects(payload: dict, expected_effects: dict | None=None) -> bool:
    """Repair only SECRET metadata for an already-confirmed Telegram copy.

    No copy_message/forward_message call is made here, so this cannot create a duplicate.
    """
    expected = expected_effects if isinstance(expected_effects, dict) else _durable_expected_effects(payload)
    raw, source_chat_id, source_msg_id, _group_id = _durable_payload_message(payload)
    if not isinstance(raw, dict) or source_chat_id is None or source_msg_id is None:
        return True
    try:
        links = {int(dst): int(mid) for dst, mid in get_forward_links(source_chat_id, source_msg_id)}
    except Exception:
        links = {}
    msg = None
    for target in expected.get('forward_targets', []) or []:
        if not bool(target.get('secret_expected')):
            continue
        try:
            dst = int(target.get('dst_chat_id'))
            dst_msg_id = int(links.get(dst) or 0)
        except Exception:
            continue
        if not dst_msg_id:
            continue
        try:
            exists = any((isinstance(r, dict) and int(r.get('source_msg_id') or 0) == dst_msg_id and (int(r.get('forward_source_msg_id') or source_msg_id) == int(source_msg_id)) for r in _secret_records(dst)))
        except Exception:
            exists = False
        if exists:
            continue
        if msg is None:
            msg = _durable_payload_to_message(payload)
        if msg is None:
            return False
        try:
            save_secret_bot_copy(dst, dst_msg_id, msg)
            try:
                bot.delete_message(dst, dst_msg_id)
            except Exception:
                pass
            bot_journal('durable_forward_secret_repaired', dst, f'src={source_chat_id}:{source_msg_id} dst_msg={dst_msg_id}')
        except Exception as e:
            log_error(f'DURABLE SAFE SECRET REPAIR {source_chat_id}:{source_msg_id}->{dst}:{dst_msg_id}: {e}')
            return False
    return True

# --- secret:0024 · from 01_core_data.py:13027 · public schedule_restored_secret_media_recovery ---
def schedule_restored_secret_media_recovery(delay: float=60.0):
    """Resume only missing SECRET media when runtime is idle and memory is safe."""

    def _defer(seconds: float, reason: str):
        try:
            bot_journal('secret_media_recovery_deferred_v210', None, reason)
        except Exception:
            pass
        DELAYED_SCHEDULER.cancel('secret-media-startup-recovery')
        DELAYED_SCHEDULER.schedule('secret-media-startup-recovery', max(30.0, float(seconds)), _job)

    def _interactive_busy() -> bool:
        for name in ('FAST_UI_TASK_POOL', 'UI_TASK_POOL', 'FINANCE_TASK_POOL', 'FORWARD_TASK_POOL', 'CONTENT_TASK_POOL'):
            pool = globals().get(name)
            if pool is None or not hasattr(pool, 'stats'):
                continue
            try:
                st = pool.stats() or {}
                if int(st.get('active', 0) or 0) > 0 or int(st.get('pending', 0) or 0) > 0:
                    return True
            except Exception:
                continue
        return False

    def _job():
        try:
            pressure_fn = globals().get('_runtime_memory_pressure')
            pressure = pressure_fn() if callable(pressure_fn) else {}
            level = str((pressure or {}).get('level') or 'normal')
            if level in {'high', 'critical', 'emergency'}:
                _defer(120.0, f'memory={level}')
                return
            if _interactive_busy():
                _defer(45.0, 'interactive queues busy')
                return
            for cid in secret_chats():
                try:
                    pending_media = any((isinstance(r, dict) and r.get('file_id') and (not r.get('mega_media_path')) for r in _secret_records(cid)))
                    if pending_media:
                        if not BACKUP_TASK_POOL.submit(f'secret-media-recover:{cid}', upload_chat_secrets_to_mega, cid):
                            schedule_secret_mega_upload(cid, BACKUP_BUSY_RETRY_SECONDS)
                except Exception as e:
                    log_error(f'SECRET MEDIA RECOVERY chat={cid}: {e}')
        except Exception as e:
            log_error(f'schedule_restored_secret_media_recovery: {e}')
    DELAYED_SCHEDULER.cancel('secret-media-startup-recovery')
    DELAYED_SCHEDULER.schedule('secret-media-startup-recovery', max(30.0, float(delay)), _job)

# --- secret:0025 · from 02_transport_safety.py:364 · public secret_storage_backend_v234 ---
def secret_storage_backend_v234() -> str:
    raw_env = str(os.getenv('SECRET_STORAGE_BACKEND', '') or '').strip().casefold()
    if raw_env in {'telegram', 'tg', 'channel', 'канал'}:
        return 'telegram'
    if raw_env in {'mega', 'мега'}:
        return 'mega'
    try:
        raw = str(_tg_v234_root_settings().get('secret_storage_backend_v234') or 'telegram').strip().casefold()
    except Exception:
        raw = 'telegram'
    return 'mega' if raw == 'mega' else 'telegram'

# --- secret:0026 · from 02_transport_safety.py:376 · public _secret_storage_migration_state_v234 ---
def _secret_storage_migration_state_v234() -> dict:
    try:
        row = _tg_v234_root_settings().get('secret_storage_migration_v234') or {}
        return dict(row) if isinstance(row, dict) else {}
    except Exception:
        return {}

# --- secret:0027 · from 02_transport_safety.py:383 · public _secret_mega_prerequisites_v234 ---
def _secret_mega_prerequisites_v234() -> bool:
    try:
        return bool(mega_contour_enabled_v234() and (not callable(globals().get('external_access_allowed_v233')) or external_access_allowed_v233('mega')) and MEGA_ENABLED and MEGA_EMAIL and MEGA_PASSWORD)
    except Exception:
        return False

# --- secret:0028 · from 02_transport_safety.py:389 · public secret_storage_effective_backend_v234 ---
def secret_storage_effective_backend_v234() -> str:
    requested = secret_storage_backend_v234()
    if requested != 'mega':
        return 'telegram'
    if not _secret_mega_prerequisites_v234():
        return 'telegram' if telegram_durable_configured_v234() else 'mega'
    migration = _secret_storage_migration_state_v234()
    if str(migration.get('target') or '') == 'mega' and str(migration.get('state') or '') not in {'done', 'not_needed'}:
        return 'telegram'
    return 'mega'

# --- secret:0029 · from 02_transport_safety.py:770 · public _run_secret_storage_migration_v234 ---
def _run_secret_storage_migration_v234(target: str) -> bool:
    target = 'mega' if str(target or '').casefold() == 'mega' else 'telegram'
    root = _tg_v234_root_settings()
    state = {'target': target, 'state': 'running', 'started_at': now_local().isoformat(timespec='seconds'), 'error': ''}
    root['secret_storage_migration_v234'] = state
    try:
        save_data(data, root_only=True)
    except Exception:
        pass
    try:
        chats_fn = globals().get('secret_chats')
        chats = list(chats_fn() or []) if callable(chats_fn) else []
        if target == 'mega':
            if not _secret_mega_prerequisites_v234():
                state.update({'state': 'blocked', 'error': 'MEGA contour/master/config is not available'})
                root['secret_storage_migration_v234'] = state
                try:
                    save_data(data, root_only=True)
                except Exception:
                    pass
                return False
            uploader = globals().get('upload_chat_secrets_to_mega')
            if not callable(uploader):
                raise RuntimeError('MEGA secret uploader unavailable')
            failed = []
            for cid in chats:
                if not bool(uploader(int(cid))):
                    failed.append(int(cid))
            if failed:
                raise RuntimeError('MEGA secret migration failed for chats: ' + ','.join(map(str, failed[:20])))
        else:
            global _delta_generation
            with _delta_state_lock:
                for cid in chats:
                    _delta_generation += 1
                    _delta_pending_chats.add(int(cid))
                    _delta_chat_generation[int(cid)] = _delta_generation
            if chats and (not durable_run_pending_delta_now_v234()):
                raise RuntimeError('Telegram secret migration delta failed')
            telegram_schedule_full_snapshot_v234('secret_backend_migration', delay=30.0)
        state.update({'state': 'done', 'completed_at': now_local().isoformat(timespec='seconds'), 'chats': len(chats), 'error': ''})
        root['secret_storage_migration_v234'] = state
        try:
            save_data(data, root_only=True)
        except Exception:
            pass
        try:
            telegram_durable_persist_controls_v234()
        except Exception:
            pass
        try:
            bot_journal('secret_storage_migration_done_v234', int(OWNER_ID or 0) or None, f'target={target}; chats={len(chats)}')
        except Exception:
            pass
        return True
    except Exception as exc:
        state.update({'state': 'failed', 'completed_at': now_local().isoformat(timespec='seconds'), 'error': str(exc)[:500]})
        root['secret_storage_migration_v234'] = state
        try:
            save_data(data, root_only=True)
        except Exception:
            pass
        try:
            bot_journal('secret_storage_migration_failed_v234', int(OWNER_ID or 0) or None, f'target={target}; {exc}', 'ERROR')
        except Exception:
            pass
        return False

# --- secret:0030 · from 02_transport_safety.py:838 · public schedule_secret_storage_migration_v234 ---
def schedule_secret_storage_migration_v234(target: str) -> bool:
    target = 'mega' if str(target or '').casefold() == 'mega' else 'telegram'
    state = _secret_storage_migration_state_v234()
    if str(state.get('target') or '') == target and str(state.get('state') or '') in {'running', 'done'}:
        return True
    row = {'target': target, 'state': 'pending', 'requested_at': now_local().isoformat(timespec='seconds'), 'error': ''}
    _tg_v234_root_settings()['secret_storage_migration_v234'] = row
    try:
        save_data(data, root_only=True)
    except Exception:
        pass
    pool = globals().get('RECOVERY_TASK_POOL') or globals().get('BACKUP_TASK_POOL')
    try:
        if pool is not None and pool.submit_unique(f'secret-storage-migrate:{target}', _run_secret_storage_migration_v234, target):
            return True
    except Exception:
        pass
    try:
        DELAYED_SCHEDULER.schedule(f'secret-storage-migrate:{target}', 0.2, _run_secret_storage_migration_v234, target)
        return True
    except Exception:
        return False

# --- secret:0031 · from 02_transport_safety.py:861 · public set_secret_storage_backend_v234 ---
def set_secret_storage_backend_v234(backend: str) -> str:
    backend = 'mega' if str(backend or '').strip().casefold() == 'mega' else 'telegram'
    _tg_v234_root_settings()['secret_storage_backend_v234'] = backend
    state = _secret_storage_migration_state_v234()
    if str(state.get('target') or '') != backend:
        _tg_v234_root_settings()['secret_storage_migration_v234'] = {'target': backend, 'state': 'pending', 'requested_at': now_local().isoformat(timespec='seconds'), 'error': ''}
    try:
        save_data(data, root_only=True)
    except Exception:
        pass
    try:
        telegram_durable_persist_controls_v234()
    except Exception:
        pass
    if backend == 'telegram' or _secret_mega_prerequisites_v234():
        schedule_secret_storage_migration_v234(backend)
    else:
        row = _secret_storage_migration_state_v234()
        row.update({'target': 'mega', 'state': 'blocked', 'error': 'MEGA is blocked or not configured'})
        _tg_v234_root_settings()['secret_storage_migration_v234'] = row
        try:
            save_data(data, root_only=True)
        except Exception:
            pass
    try:
        bot_journal('secret_storage_backend_v234', int(OWNER_ID or 0) or None, f'requested={backend}; effective={secret_storage_effective_backend_v234()}')
    except Exception:
        pass
    return backend

# --- secret:0032 · from 02_transport_safety.py:1599 · public telegram_secret_checkpoint_v234 ---
def telegram_secret_checkpoint_v234(chat_id: int) -> bool:
    if not telegram_durable_primary_v234():
        return False
    return telegram_schedule_delta_backup_v234(int(chat_id), delay=0.5, reason='secret')

# --- secret:0033 · from 04_messages_features.py:16 · public _secret_countdown_text ---
def _secret_countdown_text(seconds: int) -> str:
    seconds = max(0, int(seconds))
    return f'{seconds // 60:02d}:{seconds % 60:02d}'

# --- secret:0034 · from 04_messages_features.py:20 · public _secret_close_label ---
def _secret_close_label(remaining: int=SECRET_AUTO_CLOSE_SECONDS) -> str:
    return f'❌ Закрыть {_secret_countdown_text(remaining)}'

# --- secret:0035 · from 04_messages_features.py:23 · public _secret_records ---
def _secret_records(chat_id: int) -> list:
    store = get_chat_store(int(chat_id))
    records = store.setdefault('secret_messages', [])
    if not isinstance(records, list):
        records = []
        store['secret_messages'] = records
    return records

# --- secret:0036 · from 04_messages_features.py:31 · public _is_secret_media_record ---
def _is_secret_media_record(record: dict) -> bool:
    return str((record or {}).get('content_type') or 'text') != 'text'

# --- secret:0037 · from 04_messages_features.py:34 · public _ensure_secret_media_numbers ---
def _ensure_secret_media_numbers(chat_id: int) -> bool:
    """Назначает старым и новым медиа постоянные номера /1, /2, /3."""
    changed = False
    used = set()
    next_number = 1
    for record in _secret_records(int(chat_id)):
        if not _is_secret_media_record(record):
            continue
        try:
            number = int(record.get('media_number') or 0)
        except Exception:
            number = 0
        if number <= 0 or number in used:
            while next_number in used:
                next_number += 1
            number = next_number
            record['media_number'] = number
            changed = True
        used.add(number)
        next_number = max(next_number, number + 1)
    return changed

# --- secret:0038 · from 04_messages_features.py:56 · public _next_secret_media_number ---
def _next_secret_media_number(chat_id: int) -> int:
    _ensure_secret_media_numbers(chat_id)
    numbers = [int(record.get('media_number') or 0) for record in _secret_records(int(chat_id)) if _is_secret_media_record(record)]
    return max(numbers or [0]) + 1

# --- secret:0039 · from 04_messages_features.py:61 · public _secret_media_record_by_number ---
def _secret_media_record_by_number(chat_id: int, number: int) -> dict | None:
    if _ensure_secret_media_numbers(chat_id):
        save_data(data)
    return next((record for record in _secret_records(int(chat_id)) if _is_secret_media_record(record) and int(record.get('media_number') or 0) == int(number)), None)

# --- secret:0040 · from 04_messages_features.py:66 · public migrate_legacy_owner_secrets ---
def migrate_legacy_owner_secrets():
    """One-time merge of old O9 notes into the owner's per-chat secret file."""
    if not OWNER_ID:
        return
    legacy = data.get('_secret_notes') or []
    settings = data.setdefault('_global_settings', {})
    if settings.get('legacy_o9_secrets_merged') or not isinstance(legacy, list):
        return
    records = _secret_records(int(OWNER_ID))
    for item in legacy:
        if not isinstance(item, dict):
            continue
        ts = str(item.get('ts') or now_local().isoformat(timespec='seconds'))
        records.append({'id': int(time.time() * 1000) + len(records), 'day_key': ts[:10] if re.fullmatch('\\d{4}-\\d{2}-\\d{2}.*', ts) else today_key(), 'timestamp': ts, 'text': str(item.get('text') or ''), 'content_type': 'text', 'file_id': None, 'source_msg_id': 0, 'user_id': int(OWNER_ID), 'user_name': ''})
    settings['legacy_o9_secrets_merged'] = True
    data['_secret_notes'] = []
    save_data(data)
    schedule_secret_mega_upload(int(OWNER_ID))

# --- secret:0041 · from 04_messages_features.py:85 · public _secret_file_id ---
def _secret_file_id(msg):
    try:
        ct = getattr(msg, 'content_type', '')
        value = getattr(msg, ct, None)
        if ct == 'photo' and value:
            return value[0].file_id
        return getattr(value, 'file_id', None)
    except Exception:
        return None

# --- secret:0042 · from 04_messages_features.py:95 · public _secret_content_payload ---
def _secret_content_payload(msg) -> dict:
    """JSON-описание сообщения, включая типы без файлового вложения."""
    ct = str(getattr(msg, 'content_type', 'text') or 'text')
    value = getattr(msg, ct, None)
    payload = {}
    try:
        if ct == 'photo':
            photos = list(value or [])
            if photos:
                photo = photos[0]
                payload.update({'width': int(getattr(photo, 'width', 0) or 0), 'height': int(getattr(photo, 'height', 0) or 0), 'file_size': int(getattr(photo, 'file_size', 0) or 0), 'quality': 'telegram_smallest'})
        elif ct in {'video', 'animation', 'video_note'}:
            payload.update({'duration': int(getattr(value, 'duration', 0) or 0), 'width': int(getattr(value, 'width', 0) or 0), 'height': int(getattr(value, 'height', 0) or 0), 'file_size': int(getattr(value, 'file_size', 0) or 0), 'mime_type': str(getattr(value, 'mime_type', '') or ''), 'file_name': str(getattr(value, 'file_name', '') or '')})
        elif ct in {'audio', 'voice'}:
            payload.update({'duration': int(getattr(value, 'duration', 0) or 0), 'file_size': int(getattr(value, 'file_size', 0) or 0), 'mime_type': str(getattr(value, 'mime_type', '') or ''), 'file_name': str(getattr(value, 'file_name', '') or ''), 'performer': str(getattr(value, 'performer', '') or ''), 'title': str(getattr(value, 'title', '') or '')})
        elif ct == 'document':
            payload.update({'file_name': str(getattr(value, 'file_name', '') or ''), 'mime_type': str(getattr(value, 'mime_type', '') or ''), 'file_size': int(getattr(value, 'file_size', 0) or 0)})
        elif ct == 'sticker':
            payload.update({'emoji': str(getattr(value, 'emoji', '') or ''), 'set_name': str(getattr(value, 'set_name', '') or ''), 'width': int(getattr(value, 'width', 0) or 0), 'height': int(getattr(value, 'height', 0) or 0), 'is_animated': bool(getattr(value, 'is_animated', False)), 'is_video': bool(getattr(value, 'is_video', False))})
        elif ct == 'location':
            payload.update({'latitude': getattr(value, 'latitude', None), 'longitude': getattr(value, 'longitude', None), 'horizontal_accuracy': getattr(value, 'horizontal_accuracy', None)})
        elif ct == 'venue':
            location = getattr(value, 'location', None)
            payload.update({'title': str(getattr(value, 'title', '') or ''), 'address': str(getattr(value, 'address', '') or ''), 'latitude': getattr(location, 'latitude', None), 'longitude': getattr(location, 'longitude', None)})
        elif ct == 'contact':
            payload.update({'phone_number': str(getattr(value, 'phone_number', '') or ''), 'first_name': str(getattr(value, 'first_name', '') or ''), 'last_name': str(getattr(value, 'last_name', '') or ''), 'user_id': getattr(value, 'user_id', None), 'vcard': str(getattr(value, 'vcard', '') or '')})
        elif ct == 'dice':
            payload.update({'emoji': str(getattr(value, 'emoji', '') or ''), 'value': int(getattr(value, 'value', 0) or 0)})
        elif ct == 'poll':
            payload.update({'question': str(getattr(value, 'question', '') or ''), 'type': str(getattr(value, 'type', '') or ''), 'is_anonymous': bool(getattr(value, 'is_anonymous', False)), 'options': [{'text': str(getattr(option, 'text', '') or ''), 'voter_count': int(getattr(option, 'voter_count', 0) or 0)} for option in getattr(value, 'options', None) or []]})
    except Exception as e:
        log_error(f'_secret_content_payload({ct}): {e}')
    return payload

# --- secret:0043 · from 04_messages_features.py:129 · public _secret_message_text ---
def _secret_message_text(msg, cleaned_text: str | None=None) -> str:
    if cleaned_text is not None:
        return cleaned_text.strip()
    text = (getattr(msg, 'text', None) or getattr(msg, 'caption', None) or '').strip()
    if text:
        return text
    return f"[{getattr(msg, 'content_type', 'message')}]"

# --- secret:0044 · from 04_messages_features.py:137 · public _extract_secret_codeword ---
def _extract_secret_codeword(text: str):
    raw = str(text or '').strip()
    if not raw:
        return (False, raw)
    emoji_words = {'🤫', '🙊', '🤐', '🔐', '🔏'}
    marked = False
    for symbol in emoji_words:
        if raw.startswith(symbol):
            raw = raw[len(symbol):].lstrip(' :;,.-–—')
            marked = True
        if raw.endswith(symbol):
            raw = raw[:-len(symbol)].rstrip(' :;,.-–—')
            marked = True
    word_codes = SECRET_CODEWORDS - emoji_words
    alternatives = '|'.join(sorted((re.escape(x) for x in word_codes), key=len, reverse=True))
    start_re = re.compile(f'^(?:{alternatives})(?=$|[^\\w])\\s*[:;,.\\-–—]?\\s*', re.I)
    end_re = re.compile(f'\\s*[:;,.\\-–—]?\\s*(?:{alternatives})$', re.I)
    cleaned, count_start = start_re.subn('', raw, count=1)
    cleaned, count_end = end_re.subn('', cleaned, count=1)
    return (bool(marked or count_start or count_end), cleaned.strip())

# --- secret:0045 · from 04_messages_features.py:158 · public _secret_chat_payload ---
def _secret_chat_payload(chat_id: int) -> dict:
    return {'kind': 'chat_secret_messages_plain_text', 'version': VERSION, 'chat_id': int(chat_id), 'chat_name': get_chat_display_name(int(chat_id)), 'updated_at': now_local().isoformat(), 'messages': list(_secret_records(int(chat_id)))}

# --- secret:0046 · from 04_messages_features.py:161 · public _secret_media_remote_name ---
def _secret_media_remote_name(record: dict, telegram_path: str) -> str:
    content = record.get('content') or {}
    original = str(content.get('file_name') or os.path.basename(telegram_path or '') or '')
    ext = os.path.splitext(original)[1].lower()
    if not ext:
        ext = {'photo': '.jpg', 'video': '.mp4', 'animation': '.mp4', 'video_note': '.mp4', 'voice': '.ogg', 'audio': '.mp3', 'sticker': '.webp'}.get(str(record.get('content_type') or ''), '.bin')
    stem = mega_safe_name(os.path.splitext(original)[0], str(record.get('content_type') or 'file'))
    return f"{int(record.get('id') or 0)}_{int(record.get('source_msg_id') or 0)}_{stem}{ext[:10]}"

# --- secret:0047 · from 04_messages_features.py:170 · public _compress_secret_video_low ---
def _compress_secret_video_low(input_path: str, output_path: str) -> bool:
    """Сжимает секретное видео для MEGA, сохраняя пропорции и чётные размеры."""
    if not shutil.which('ffmpeg'):
        return False
    try:
        pressure_fn = globals().get('_runtime_memory_pressure')
        pressure = pressure_fn() if callable(pressure_fn) else {}
        if str(pressure.get('level') or 'normal') in {'critical', 'emergency'}:
            bot_journal('secret_video_compress_skipped_memory', None, json.dumps(pressure, ensure_ascii=False, default=str), 'WARN')
            return False

        def _run_ffmpeg():
            return subprocess.run(['ffmpeg', '-y', '-i', input_path, '-vf', "scale='min(640,iw)':-2", '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '33', '-maxrate', '700k', '-bufsize', '1400k', '-c:a', 'aac', '-b:a', '64k', '-movflags', '+faststart', output_path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=max(180, MEGA_TIMEOUT * 2), check=False)
        mem_ctx = globals().get('memory_operation')
        if callable(mem_ctx):
            with mem_ctx('ffmpeg:secret_video', {'input_mb': round(os.path.getsize(input_path) / 1024 / 1024, 1) if os.path.exists(input_path) else None}, heavy=True):
                result = _run_ffmpeg()
        else:
            result = _run_ffmpeg()
        return bool(result.returncode == 0 and os.path.exists(output_path) and (os.path.getsize(output_path) > 0))
    except Exception as e:
        log_error(f'_compress_secret_video_low: {e}')
        return False

# --- secret:0048 · from 04_messages_features.py:194 · public _upload_secret_record_media ---
def _upload_secret_record_media(chat_id: int, record: dict, remote_dir: str, allow_recompress: bool=False) -> bool:
    file_id = record.get('file_id')
    if not file_id:
        return True
    content_type = str(record.get('content_type') or '')
    old_remote_path = str(record.get('mega_media_path') or '')
    saved_quality = str((record.get('content') or {}).get('quality') or '')
    needs_video_recompress = bool(allow_recompress and content_type in {'video', 'video_note', 'animation'} and (saved_quality != 'low_640p_crf33'))
    if old_remote_path and (not needs_video_recompress):
        return True
    if record.get('mega_media_skip_reason'):
        return True
    try:
        file_size = int((record.get('content') or {}).get('file_size') or 0)
    except Exception:
        file_size = 0
    telegram_bot_download_limit = max(1, int(os.getenv('TELEGRAM_BOT_DOWNLOAD_LIMIT_BYTES', '19900000') or '19900000'))
    if file_size > telegram_bot_download_limit:
        record['mega_media_skip_reason'] = 'telegram_bot_file_too_big'
        record['mega_media_error'] = f'file is too big for Bot API download: {file_size} bytes'
        record['mega_saved_at'] = now_local().isoformat(timespec='seconds')
        bot_journal('secret_media_mega_skipped', chat_id, f"record={record.get('id')} size={file_size} reason=file_too_big")
        return True
    local_dir = None
    try:
        file_info = bot.get_file(file_id)
        telegram_path = str(getattr(file_info, 'file_path', '') or '')
        remote_name = _secret_media_remote_name(record, telegram_path)
        os.makedirs(MEGA_LOCAL_TMP_DIR, exist_ok=True)
        local_dir = tempfile.mkdtemp(prefix=f'secret_{chat_id}_{threading.get_ident()}_', dir=MEGA_LOCAL_TMP_DIR)
        local_path = os.path.join(local_dir, remote_name)
        stream_fn = globals().get('telegram_download_to_file')
        if callable(stream_fn):
            stream_fn(telegram_path, local_path, max_bytes=telegram_bot_download_limit)
        else:
            raw = bot.download_file(telegram_path)
            with open(local_path, 'wb') as media_file:
                media_file.write(raw)
            raw = None
        upload_path = local_path
        if content_type in {'video', 'video_note', 'animation'}:
            compressed_name = os.path.splitext(remote_name)[0] + '_low.mp4'
            compressed_path = os.path.join(local_dir, compressed_name)
            if _compress_secret_video_low(local_path, compressed_path):
                upload_path = compressed_path
                remote_name = compressed_name
                record.setdefault('content', {})['quality'] = 'low_640p_crf33'
                record['content']['mega_file_size'] = os.path.getsize(compressed_path)
            else:
                record.setdefault('content', {})['quality'] = 'original_fallback'
        if not mega_put_replace(upload_path, remote_dir, remote_name):
            return False
        record['mega_media_path'] = remote_dir.rstrip('/') + '/' + remote_name
        record['mega_saved_at'] = now_local().isoformat(timespec='seconds')
        record.pop('mega_media_error', None)
        if old_remote_path and old_remote_path != record['mega_media_path']:
            try:
                _mega_run('mega-rm', [old_remote_path], check=False, timeout=30)
            except Exception as e:
                log_error(f'secret old media cleanup {old_remote_path}: {e}')
        return True
    except Exception as e:
        error_text = str(e)
        record['mega_media_error'] = error_text[:300]
        if 'file is too big' in error_text.lower():
            record['mega_media_skip_reason'] = 'telegram_bot_file_too_big'
            record['mega_saved_at'] = now_local().isoformat(timespec='seconds')
            bot_journal('secret_media_mega_skipped', chat_id, f"record={record.get('id')} reason=file_too_big_api")
            return True
        log_error(f'_upload_secret_record_media({chat_id}): {e}')
        return False
    finally:
        if local_dir:
            try:
                shutil.rmtree(local_dir, ignore_errors=True)
            except Exception:
                pass

# --- secret:0049 · from 04_messages_features.py:272 · public upload_chat_secrets_to_mega ---
def upload_chat_secrets_to_mega(chat_id: int) -> bool:
    if not mega_is_configured():
        return False
    chat_id = int(chat_id)
    with _secret_mega_locks[chat_id]:
        try:
            os.makedirs(MEGA_LOCAL_TMP_DIR, exist_ok=True)
            slug = mega_chat_slug(chat_id)
            filename = f'secret_{slug}.json'
            path = os.path.join(MEGA_LOCAL_TMP_DIR, filename)
            remote_dir = f"{MEGA_BACKUP_DIR.rstrip('/')}/secrets/{slug}"
            media_dir = remote_dir.rstrip('/') + '/media'
            media_ok = True
            for record in list(_secret_records(chat_id)):
                if record.get('file_id'):
                    media_ok = _upload_secret_record_media(chat_id, record, media_dir) and media_ok
            save_data(data)
            _save_json(path, _secret_chat_payload(chat_id))
            json_ok = bool(mega_put_replace(path, remote_dir, filename))
            return bool(media_ok and json_ok)
        except Exception as e:
            log_error(f'upload_chat_secrets_to_mega({chat_id}): {e}')
            return False

# --- secret:0050 · from 04_messages_features.py:298 · public schedule_secret_mega_upload ---
def schedule_secret_mega_upload(chat_id: int, delay: float=45.0):
    """v234 SECRET router: Telegram durable checkpoint by default; MEGA only when explicitly selected."""
    try:
        backend_fn = globals().get('secret_storage_effective_backend_v234')
        if callable(backend_fn) and backend_fn() == 'telegram':
            checkpoint = globals().get('telegram_secret_checkpoint_v234')
            return bool(checkpoint(int(chat_id))) if callable(checkpoint) else False
        if not mega_is_configured():
            return False
        chat_id = int(chat_id)
        delay = max(float(delay or 0), 30.0)
    except Exception:
        return False
    generation = time.time_ns()
    scheduler_key = f'secret-mega-upload:{chat_id}'

    def _job():
        try:
            with _secret_mega_upload_lock:
                if _secret_mega_upload_timers.get(chat_id) != generation:
                    return
            if not BACKUP_TASK_POOL.submit(f'secret-mega:{chat_id}', upload_chat_secrets_to_mega, chat_id):
                log_error(f'SECRET MEGA QUEUE FULL, RETRY: {chat_id}')
                schedule_secret_mega_upload(chat_id, BACKUP_BUSY_RETRY_SECONDS)
        finally:
            with _secret_mega_upload_lock:
                if _secret_mega_upload_timers.get(chat_id) == generation:
                    _secret_mega_upload_timers.pop(chat_id, None)
    with _secret_mega_upload_lock:
        DELAYED_SCHEDULER.cancel(scheduler_key)
        _secret_mega_upload_timers[chat_id] = generation
        DELAYED_SCHEDULER.schedule(scheduler_key, delay, _job)
    return True

# --- secret:0051 · from 04_messages_features.py:332 · public save_secret_message ---
def save_secret_message(chat_id: int, msg, cleaned_text: str | None=None) -> dict:
    chat_id = int(chat_id)
    user = getattr(msg, 'from_user', None)
    content_type = getattr(msg, 'content_type', 'text')
    record = {'id': int(time.time() * 1000), 'day_key': day_key_from_message(msg), 'timestamp': message_timestamp_iso(msg), 'text': _secret_message_text(msg, cleaned_text), 'content_type': content_type, 'file_id': _secret_file_id(msg), 'content': _secret_content_payload(msg), 'source_msg_id': int(getattr(msg, 'message_id', 0) or 0), 'user_id': int(getattr(user, 'id', 0) or 0), 'user_name': getattr(user, 'username', None) or getattr(user, 'first_name', None) or ''}
    if content_type != 'text':
        record['media_number'] = _next_secret_media_number(chat_id)
    _secret_records(chat_id).append(record)
    settings = get_chat_store(chat_id).setdefault('settings', {})
    settings['auto_backup_to_mega_enabled'] = bool(globals().get('mega_contour_enabled_v234', lambda: False)())
    save_data(data)
    schedule_config_backup_for_chats(chat_id, delay=0.2)
    schedule_secret_mega_upload(chat_id)
    refresh_secret_windows(chat_id)
    return record

# --- secret:0052 · from 04_messages_features.py:348 · public save_secret_bot_copy ---
def save_secret_bot_copy(chat_id: int, copied_message_id: int, source_msg) -> dict | None:
    """Store a message created by the bot itself in a total-secret destination chat.

    Telegram does not send the bot an update for its own copy_message/send_* result,
    so forwarded bot-copies must be captured explicitly here.
    """
    chat_id = int(chat_id)
    copied_message_id = int(copied_message_id)
    try:
        for existing in _secret_records(chat_id):
            if int(existing.get('source_msg_id') or 0) == copied_message_id and existing.get('is_bot_copy'):
                return existing
    except Exception:
        pass
    user = getattr(source_msg, 'from_user', None)
    content_type = str(getattr(source_msg, 'content_type', 'text') or 'text')
    record = {'id': int(time.time() * 1000), 'day_key': day_key_from_message(source_msg), 'timestamp': message_timestamp_iso(source_msg), 'text': _secret_message_text(source_msg), 'content_type': content_type, 'file_id': _secret_file_id(source_msg), 'content': _secret_content_payload(source_msg), 'source_msg_id': copied_message_id, 'forward_source_msg_id': int(getattr(source_msg, 'message_id', 0) or 0), 'forward_source_chat_id': int(getattr(getattr(source_msg, 'chat', None), 'id', 0) or 0), 'user_id': int(getattr(user, 'id', 0) or 0), 'user_name': getattr(user, 'username', None) or getattr(user, 'first_name', None) or '', 'is_bot_copy': True}
    if content_type != 'text':
        record['media_number'] = _next_secret_media_number(chat_id)
    _secret_records(chat_id).append(record)
    settings = get_chat_store(chat_id).setdefault('settings', {})
    settings['auto_backup_to_mega_enabled'] = bool(globals().get('mega_contour_enabled_v234', lambda: False)())
    save_data(data, chat_ids=[chat_id])
    schedule_config_backup_for_chats(chat_id, delay=0.2)
    schedule_secret_mega_upload(chat_id)
    refresh_secret_windows(chat_id)
    return record

# --- secret:0053 · from 04_messages_features.py:376 · public capture_forwarded_bot_copy_as_secret ---
def capture_forwarded_bot_copy_as_secret(chat_id: int, copied_message_id: int, source_msg) -> bool:
    """Apply total-secret behavior to a bot-created forwarded copy."""
    if not is_total_secret_mode(int(chat_id)):
        return False
    try:
        save_secret_bot_copy(int(chat_id), int(copied_message_id), source_msg)
    except Exception as e:
        log_error(f'save bot-copy secret {chat_id}:{copied_message_id}: {e}')
        return False
    try:
        bot.delete_message(int(chat_id), int(copied_message_id))
    except Exception as e:
        log_error(f'delete bot-copy secret {chat_id}:{copied_message_id}: {e}')
        DELAYED_SCHEDULER.schedule(f'secret-bot-copy-delete:{int(chat_id)}:{int(copied_message_id)}', 1.0, lambda: bot.delete_message(int(chat_id), int(copied_message_id)))
    return True

# --- secret:0054 · from 04_messages_features.py:392 · public sync_forwarded_secret_bot_copy_edit ---
def sync_forwarded_secret_bot_copy_edit(chat_id: int, copied_message_id: int, source_chat_id: int, source_msg) -> bool:
    """Обновляет скрытую bot-copy при редактировании исходника БЕЗ видимого Telegram fallback.

    Критично для TOTAL SECRET: исходная копия была удалена сразу после сохранения, поэтому
    обычный edit_message_* получает ``message to edit not found``. Старый fallback после этого
    создавал новую видимую копию и фактически ломал секретность.
    """
    chat_id = int(chat_id)
    copied_message_id = int(copied_message_id)
    source_chat_id = int(source_chat_id)
    if not is_total_secret_mode(chat_id):
        return False
    source_msg_id = int(getattr(source_msg, 'message_id', 0) or 0)
    records = _secret_records(chat_id)
    record = None
    for row in records:
        if not isinstance(row, dict) or not bool(row.get('is_bot_copy')):
            continue
        try:
            if int(row.get('source_msg_id') or 0) == copied_message_id:
                record = row
                break
            if int(row.get('forward_source_chat_id') or 0) == source_chat_id and int(row.get('forward_source_msg_id') or 0) == source_msg_id:
                record = row
                break
        except Exception:
            continue
    if record is None:
        try:
            record = save_secret_bot_copy(chat_id, copied_message_id, source_msg)
        except Exception as exc:
            log_error(f'secret bot-copy edit create {chat_id}:{copied_message_id}: {exc}')
            return False
    if not isinstance(record, dict):
        return False
    try:
        content_type = str(getattr(source_msg, 'content_type', 'text') or 'text')
        record['text'] = _secret_message_text(source_msg)
        record['content_type'] = content_type
        record['file_id'] = _secret_file_id(source_msg)
        record['content'] = _secret_content_payload(source_msg)
        record['forward_source_chat_id'] = source_chat_id
        record['forward_source_msg_id'] = source_msg_id
        record['source_msg_id'] = copied_message_id
        record['is_bot_copy'] = True
        record['edited_at'] = now_local().isoformat(timespec='seconds')
        if content_type != 'text' and (not int(record.get('media_number') or 0)):
            record['media_number'] = _next_secret_media_number(chat_id)
        settings = get_chat_store(chat_id).setdefault('settings', {})
        settings['auto_backup_to_mega_enabled'] = bool(globals().get('mega_contour_enabled_v234', lambda: False)())
        save_data(data, chat_ids=[chat_id])
        schedule_config_backup_for_chats(chat_id, delay=0.2)
        schedule_secret_mega_upload(chat_id)
        refresh_secret_windows(chat_id)
        try:
            _durable_note_secret_edit_witness(_durable_secret_edit_witness(chat_id, int(record.get('id')), str(record.get('text') or '')))
        except Exception:
            pass
        try:
            bot_journal('secret_forward_edit_hidden', chat_id, f'src={source_chat_id}:{source_msg_id} copy={copied_message_id}')
        except Exception:
            pass
    except Exception as exc:
        log_error(f'secret bot-copy edit update {chat_id}:{copied_message_id}: {exc}')
        return False
    try:
        bot.delete_message(chat_id, copied_message_id)
    except Exception:
        pass
    return True

# --- secret:0055 · from 04_messages_features.py:463 · public delete_secret_source_message ---
def delete_secret_source_message(msg):
    try:
        bot.delete_message(msg.chat.id, msg.message_id)
    except Exception as e:
        log_error(f'secret source delete {msg.chat.id}:{msg.message_id}: {e}')

        def retry():
            try:
                bot.delete_message(msg.chat.id, msg.message_id)
            except Exception as retry_error:
                log_error(f'secret source delete retry {msg.chat.id}:{msg.message_id}: {retry_error}')
        DELAYED_SCHEDULER.schedule(f'secret-source-delete-retry:{int(msg.chat.id)}:{int(msg.message_id)}', 1.0, retry)

# --- secret:0056 · from 04_messages_features.py:476 · public is_total_secret_mode ---
def is_total_secret_mode(chat_id: int) -> bool:
    return bool(get_chat_store(int(chat_id)).setdefault('settings', {}).get('total_secret_mode', False))

# --- secret:0057 · from 04_messages_features.py:479 · public set_total_secret_mode ---
def set_total_secret_mode(chat_id: int, enabled: bool):
    store = get_chat_store(int(chat_id))
    settings = store.setdefault('settings', {})
    target = bool(enabled)
    if bool(settings.get('total_secret_mode', False)) == target:
        return False
    settings['total_secret_mode'] = target
    save_data(data, chat_ids=[int(chat_id)])
    schedule_config_backup_for_chats(chat_id)
    return True

# --- secret:0058 · from 04_messages_features.py:491 · public total_secret_decoy_text ---
def total_secret_decoy_text(msg) -> str:
    try:
        seed = int(getattr(msg, 'message_id', 0) or 0) + int(getattr(getattr(msg, 'chat', None), 'id', 0) or 0)
        return TOTAL_SECRET_DECOY_PHRASES[abs(seed) % len(TOTAL_SECRET_DECOY_PHRASES)]
    except Exception:
        return 'Тишина внутри.'

# --- secret:0059 · from 04_messages_features.py:498 · public maybe_send_total_secret_decoy ---
def maybe_send_total_secret_decoy(msg):
    try:
        if not total_secret_mask_enabled(msg.chat.id):
            return
        if not is_total_secret_mode(msg.chat.id):
            return
        _tg_call_retry(bot.send_message, msg.chat.id, total_secret_decoy_text(msg), purpose='total_secret_decoy')
    except Exception as e:
        log_error(f"maybe_send_total_secret_decoy({getattr(getattr(msg, 'chat', None), 'id', '?')}): {e}")

# --- secret:0060 · from 04_messages_features.py:508 · public forward_secret_message_now ---
def forward_secret_message_now(msg):
    """Секретный режим удаляет оригинал, поэтому пересылку делаем до удаления."""
    try:
        source_chat_id = int(msg.chat.id)
        source_msg_id = int(getattr(msg, 'message_id', 0) or 0)
        _durable_note_forward_decision(source_chat_id, direct=True)
        targets = resolve_forward_targets(source_chat_id)
        if not targets:
            if source_msg_id:
                _forward_outcome_update(source_chat_id, source_msg_id, state='no_targets')
            return
        for dst_chat_id, mode, finance_enabled in targets:
            _forward_single_to_target(source_chat_id, msg, dst_chat_id, finance_enabled)
        if source_msg_id:
            _forward_outcome_update(source_chat_id, source_msg_id, state='completed')
    except Exception as e:
        log_error(f"forward_secret_message_now({getattr(getattr(msg, 'chat', None), 'id', '?')}): {e}")

# --- secret:0061 · from 04_messages_features.py:526 · public handle_secret_input_message ---
def handle_secret_input_message(msg) -> bool:
    text = getattr(msg, 'text', None) or getattr(msg, 'caption', None) or ''
    marked, cleaned = _extract_secret_codeword(text)
    total_mode = is_total_secret_mode(msg.chat.id)
    if not marked and (not total_mode):
        return False
    forward_secret_message_now(msg)
    save_secret_message(msg.chat.id, msg, cleaned_text=cleaned if marked else None)
    delete_secret_source_message(msg)
    if total_mode:
        maybe_send_total_secret_decoy(msg)
    return True

# --- secret:0062 · from 04_messages_features.py:539 · public handle_secret_edited_message ---
def handle_secret_edited_message(msg) -> bool:
    """Update an existing secret by Telegram message_id, or capture an edit that became secret."""
    chat_id = int(msg.chat.id)
    message_id = int(getattr(msg, 'message_id', 0) or 0)
    record = next((r for r in _secret_records(chat_id) if int(r.get('source_msg_id') or 0) == message_id), None)
    if record is None:
        return handle_secret_input_message(msg)
    raw_text = getattr(msg, 'text', None) or getattr(msg, 'caption', None) or ''
    marked, cleaned = _extract_secret_codeword(raw_text)
    record['text'] = _secret_message_text(msg, cleaned_text=cleaned if marked else raw_text)
    record['content_type'] = getattr(msg, 'content_type', record.get('content_type', 'text'))
    previous_file_id = record.get('file_id')
    new_file_id = _secret_file_id(msg)
    record['file_id'] = new_file_id or previous_file_id
    record['content'] = _secret_content_payload(msg) or record.get('content', {})
    if new_file_id and new_file_id != previous_file_id:
        record.pop('mega_media_path', None)
        record.pop('mega_saved_at', None)
    record['edited_at'] = now_local().isoformat(timespec='seconds')
    save_data(data)
    schedule_config_backup_for_chats(chat_id, delay=0.2)
    schedule_secret_mega_upload(chat_id)
    refresh_secret_windows(chat_id)
    delete_secret_source_message(msg)
    return True

# --- secret:0063 · from 04_messages_features.py:565 · public secret_chats ---
def secret_chats() -> list[int]:
    out = []
    for cid, store in (data.get('chats', {}) or {}).items():
        try:
            if (store.get('secret_messages') or []) or bool((store.get('settings') or {}).get('total_secret_mode', False)):
                out.append(int(cid))
        except Exception:
            continue
    return sorted(set(out), key=lambda x: get_chat_display_name(x).casefold())

# --- secret:0064 · from 04_messages_features.py:575 · public format_secret_records ---
def format_secret_records(chat_id: int, day_key: str | None=None) -> list[str]:
    if _ensure_secret_media_numbers(chat_id):
        save_data(data)
    records = _secret_records(chat_id)
    if day_key:
        records = [r for r in records if str(r.get('day_key')) == str(day_key)]
    title = f'🔐 Секретные данные: {get_chat_display_name(chat_id)}'
    if day_key:
        title += f'\n📅 {fmt_date_ddmmyy(day_key)}'
    lines = [title, '']
    if not records:
        lines.append('Нет секретных сообщений.')
    else:
        for idx, item in enumerate(records, 1):
            ts = str(item.get('timestamp') or '')
            stamp = ts[11:19] if len(ts) >= 19 else ''
            shown_day = fmt_date_ddmmyy(str(item.get('day_key') or ''))
            lines.append(f'{idx}. {shown_day} {stamp} — {_secret_record_display_text(item)}'.strip())
    chunks, current = ([], '')
    for line in lines:
        candidate = (current + '\n' + line).strip('\n')
        if len(candidate) > 3800 and current:
            chunks.append(current)
            current = line
        else:
            current = candidate
    if current:
        chunks.append(current)
    return chunks

# --- secret:0065 · from 04_messages_features.py:605 · public _secret_record_display_text ---
def _secret_record_display_text(record: dict) -> str:
    text = str(record.get('text') or '').strip()
    ct = str(record.get('content_type') or 'message')
    placeholders = {f'[{ct}]', '[message]', ''}
    if _is_secret_media_record(record):
        label = {'photo': '📷 Фото', 'video': '🎥 Видео', 'animation': '🎞️ Анимация', 'video_note': '⭕ Видеосообщение', 'audio': '🎵 Аудио', 'voice': '🎤 Голосовое', 'document': '📎 Файл', 'sticker': '🖼️ Стикер', 'location': '📍 Геолокация', 'venue': '📍 Место', 'contact': '👤 Контакт', 'dice': '🎲 Кубик', 'poll': '📊 Опрос'}.get(ct, f'📦 {ct}')
        text = label if text in placeholders else f'{label}: {text}'
        number = int(record.get('media_number') or 0)
        if number:
            text = f'{text} /{number}'
    elif text in placeholders:
        text = 'Сообщение'
    return text

# --- secret:0066 · from 04_messages_features.py:619 · public _secret_media_caption ---
def _secret_media_caption(record: dict) -> str:
    ts = str(record.get('timestamp') or '')
    stamp = ts[11:19] if len(ts) >= 19 else ''
    day = fmt_date_ddmmyy(str(record.get('day_key') or ''))
    text = str(record.get('text') or '').strip()
    if text.startswith('[') and text.endswith(']'):
        text = ''
    caption = f'🔐 {day} {stamp}'.strip()
    if text:
        caption += '\n' + text
    number = int(record.get('media_number') or 0)
    if number:
        caption += f'\n/{number}'
    return caption[:1024]

# --- secret:0067 · from 04_messages_features.py:634 · public build_secret_media_timer_keyboard ---
def build_secret_media_timer_keyboard(remaining: int=SECRET_AUTO_CLOSE_SECONDS):
    kb = types.InlineKeyboardMarkup(row_width=2)
    kb.row(IB(_secret_close_label(remaining), callback_data='secmclose'), IB(f'⏳ {_secret_countdown_text(remaining)} Закроется', callback_data='secmwait'))
    return kb

# --- secret:0068 · from 04_messages_features.py:639 · public cancel_secret_media_timer ---
def cancel_secret_media_timer(chat_id: int, message_id: int):
    key = (int(chat_id), int(message_id))
    with _secret_media_timer_lock:
        _secret_media_timer_generation.pop(key, None)
    DELAYED_SCHEDULER.cancel(f'secret-media-close:{chat_id}:{message_id}')

# --- secret:0069 · from 04_messages_features.py:645 · public schedule_secret_media_close ---
def schedule_secret_media_close(chat_id: int, message_id: int):
    """Запускает или продлевает удаление медиа на 90 секунд без лишних edit-таймеров."""
    key = (int(chat_id), int(message_id))
    with _secret_media_timer_lock:
        generation = int(_secret_media_timer_generation.get(key, 0)) + 1
        _secret_media_timer_generation[key] = generation

    def run():
        with _secret_media_timer_lock:
            if _secret_media_timer_generation.get(key) != generation:
                return
        try:
            bot.delete_message(chat_id, message_id)
        except Exception:
            pass
        with _secret_media_timer_lock:
            if _secret_media_timer_generation.get(key) == generation:
                _secret_media_timer_generation.pop(key, None)
    DELAYED_SCHEDULER.schedule(f'secret-media-close:{chat_id}:{message_id}', SECRET_AUTO_CLOSE_SECONDS, run)

# --- secret:0070 · from 04_messages_features.py:665 · public _send_secret_media_caption_message ---
def _send_secret_media_caption_message(viewer_chat_id: int, caption: str):
    try:
        sent = bot.send_message(viewer_chat_id, caption)
        delete_message_later(viewer_chat_id, sent.message_id, SECRET_AUTO_CLOSE_SECONDS)
    except Exception:
        pass

# --- secret:0071 · from 04_messages_features.py:672 · public _send_secret_record_media ---
def _send_secret_record_media(viewer_chat_id: int, record: dict):
    ct = str(record.get('content_type') or '')
    file_id = record.get('file_id')
    content = record.get('content') or {}
    caption = _secret_media_caption(record)
    kb = build_secret_media_timer_keyboard()
    sent = None
    try:
        if ct == 'photo' and file_id:
            sent = bot.send_photo(viewer_chat_id, file_id, caption=caption, reply_markup=kb)
        elif ct == 'video' and file_id:
            sent = bot.send_video(viewer_chat_id, file_id, caption=caption, supports_streaming=True, reply_markup=kb)
        elif ct == 'animation' and file_id:
            sent = bot.send_animation(viewer_chat_id, file_id, caption=caption, reply_markup=kb)
        elif ct == 'video_note' and file_id:
            _send_secret_media_caption_message(viewer_chat_id, caption)
            sent = bot.send_video_note(viewer_chat_id, file_id, reply_markup=kb)
        elif ct == 'audio' and file_id:
            sent = bot.send_audio(viewer_chat_id, file_id, caption=caption, reply_markup=kb)
        elif ct == 'voice' and file_id:
            sent = bot.send_voice(viewer_chat_id, file_id, caption=caption, reply_markup=kb)
        elif ct == 'document' and file_id:
            sent = bot.send_document(viewer_chat_id, file_id, caption=caption, reply_markup=kb)
        elif ct == 'sticker' and file_id:
            _send_secret_media_caption_message(viewer_chat_id, caption)
            sent = bot.send_sticker(viewer_chat_id, file_id, reply_markup=kb)
        elif ct == 'location' and content.get('latitude') is not None:
            _send_secret_media_caption_message(viewer_chat_id, caption)
            sent = bot.send_location(viewer_chat_id, content['latitude'], content['longitude'], reply_markup=kb)
        elif ct == 'venue' and content.get('latitude') is not None:
            _send_secret_media_caption_message(viewer_chat_id, caption)
            sent = bot.send_venue(viewer_chat_id, content['latitude'], content['longitude'], content.get('title') or 'Место', content.get('address') or '', reply_markup=kb)
        elif ct == 'contact' and content.get('phone_number'):
            _send_secret_media_caption_message(viewer_chat_id, caption)
            sent = bot.send_contact(viewer_chat_id, content['phone_number'], content.get('first_name') or 'Контакт', last_name=content.get('last_name') or None, vcard=content.get('vcard') or None, reply_markup=kb)
        elif ct == 'dice':
            _send_secret_media_caption_message(viewer_chat_id, f"{caption}\n🎲 Выпало: {content.get('value', '')}".strip())
            sent = bot.send_dice(viewer_chat_id, emoji=content.get('emoji') or '🎲', reply_markup=kb)
        elif ct == 'poll':
            options = [str(x.get('text') or '') for x in content.get('options') or [] if str(x.get('text') or '')]
            if len(options) >= 2:
                _send_secret_media_caption_message(viewer_chat_id, caption)
                sent = bot.send_poll(viewer_chat_id, str(content.get('question') or 'Опрос')[:300], options[:10], is_anonymous=bool(content.get('is_anonymous', True)), reply_markup=kb)
            else:
                sent = bot.send_message(viewer_chat_id, caption, reply_markup=kb)
        else:
            return None
        if sent:
            schedule_secret_media_close(viewer_chat_id, sent.message_id)
        return sent
    except Exception as e:
        log_error(f'_send_secret_record_media({viewer_chat_id},{ct}): {e}')
        return None

# --- secret:0072 · from 04_messages_features.py:726 · public send_secret_media ---
def send_secret_media(viewer_chat_id: int, target_chat_id: int, day_key: str | None=None):
    if _ensure_secret_media_numbers(target_chat_id):
        save_data(data)
    records = list(_secret_records(int(target_chat_id)))
    if day_key:
        records = [record for record in records if str(record.get('day_key')) == str(day_key)]
    records = [record for record in records if str(record.get('content_type') or '') != 'text']
    title = get_chat_display_name(int(target_chat_id))
    period = fmt_date_ddmmyy(day_key) if day_key else 'за всё время'
    if not records:
        send_and_auto_delete(viewer_chat_id, f'🎞️ Медиа нет: {title}, {period}.', 10)
        return
    header = bot.send_message(viewer_chat_id, f'🎞️ {title}\n📅 {period}\nФайлов: {len(records)}')
    delete_message_later(viewer_chat_id, header.message_id, SECRET_AUTO_CLOSE_SECONDS)
    sent = 0
    for record in records:
        if _send_secret_record_media(viewer_chat_id, record):
            sent += 1
        time.sleep(0.12)
    if sent != len(records):
        send_and_auto_delete(viewer_chat_id, f'🎞️ Отправлено: {sent}/{len(records)}. Некоторые старые записи не содержат файла.', 15)

# --- secret:0073 · from 04_messages_features.py:748 · public send_secret_records ---
def send_secret_records(chat_id: int, target_chat_id: int, day_key: str | None=None):
    for chunk in format_secret_records(int(target_chat_id), day_key):
        bot.send_message(int(chat_id), chunk)

# --- secret:0074 · from 04_messages_features.py:753 · public _secret_day_records ---
def _secret_day_records(target_chat_id: int, day_key: str) -> list[dict]:
    return [r for r in _secret_records(target_chat_id) if str(r.get('day_key')) == str(day_key)]

# --- secret:0075 · from 04_messages_features.py:756 · public _default_secret_day ---
def _default_secret_day(target_chat_id: int) -> str:
    days = sorted({str(r.get('day_key')) for r in _secret_records(target_chat_id) if r.get('day_key')})
    return days[-1] if days else today_key()

# --- secret:0076 · from 04_messages_features.py:760 · public build_secret_day_text ---
def build_secret_day_text(target_chat_id: int, day_key: str) -> str:
    if _ensure_secret_media_numbers(target_chat_id):
        save_data(data)
    lines = [f'🔐 Секретные данные: {get_chat_display_name(target_chat_id)}', f'📅 {fmt_date_ddmmyy(day_key)}', '']
    records = _secret_day_records(target_chat_id, day_key)
    if not records:
        lines.append('Нет секретных сообщений.')
    for idx, item in enumerate(records, 1):
        ts = str(item.get('timestamp') or '')
        stamp = ts[11:19] if len(ts) >= 19 else ''
        lines.append(f'{idx}. {stamp} — {_secret_record_display_text(item)}'.rstrip())
    text = '\n'.join(lines)
    return text if len(text) <= 3900 else text[:3890] + '\n…'

# --- secret:0077 · from 04_messages_features.py:775 · public can_manage_secret_target ---
def can_manage_secret_target(viewer_chat_id: int, target_chat_id: int) -> bool:
    try:
        return bool(is_owner_chat(int(viewer_chat_id)) or int(viewer_chat_id) == int(target_chat_id))
    except Exception:
        return False

# --- secret:0078 · from 04_messages_features.py:781 · public _renumber_secret_media_numbers ---
def _renumber_secret_media_numbers(chat_id: int) -> None:
    number = 1
    for record in _secret_records(int(chat_id)):
        if _is_secret_media_record(record):
            record['media_number'] = number
            number += 1

# --- secret:0079 · from 04_messages_features.py:788 · public _secret_delete_period_bounds ---
def _secret_delete_period_bounds(mode: str, day_key: str):
    mode = str(mode or 'day')
    try:
        base = datetime.strptime(str(day_key)[:10], '%Y-%m-%d').date()
    except Exception:
        base = now_local().date()
    if mode == 'all':
        return (None, None)
    if mode == 'week':
        start = datetime.strptime(week_start_monday(base.strftime('%Y-%m-%d')), '%Y-%m-%d').date()
        end = start + timedelta(days=6)
        return (start.strftime('%Y-%m-%d'), end.strftime('%Y-%m-%d'))
    if mode == 'month':
        start = base.replace(day=1)
        last_day = calendar.monthrange(base.year, base.month)[1]
        end = base.replace(day=last_day)
        return (start.strftime('%Y-%m-%d'), end.strftime('%Y-%m-%d'))
    return (base.strftime('%Y-%m-%d'), base.strftime('%Y-%m-%d'))

# --- secret:0080 · from 04_messages_features.py:807 · public _secret_delete_period_label ---
def _secret_delete_period_label(mode: str, day_key: str) -> str:
    start, end = _secret_delete_period_bounds(mode, day_key)
    if mode == 'all':
        return 'Всё'
    if mode == 'month':
        try:
            return datetime.strptime(str(day_key)[:10], '%Y-%m-%d').strftime('%m.%y')
        except Exception:
            return str(day_key)[:7]
    if start == end:
        return fmt_date_ddmmyy(start)
    return f'{fmt_date_ddmmyy(start)}–{fmt_date_ddmmyy(end)}'

# --- secret:0081 · from 04_messages_features.py:820 · public _secret_record_matches_delete_mode ---
def _secret_record_matches_delete_mode(record: dict, mode: str, day_key: str) -> bool:
    if mode == 'all':
        return True
    rk = str((record or {}).get('day_key') or '')[:10]
    if not rk:
        return False
    start, end = _secret_delete_period_bounds(mode, day_key)
    return bool(start <= rk <= end)

# --- secret:0082 · from 04_messages_features.py:829 · public _secret_delete_count ---
def _secret_delete_count(target_chat_id: int, mode: str, day_key: str) -> int:
    return sum((1 for r in _secret_records(int(target_chat_id)) if _secret_record_matches_delete_mode(r, mode, day_key)))

# --- secret:0083 · from 04_messages_features.py:832 · public _secret_delete_selection ---
def _secret_delete_selection(viewer_chat_id: int, target_chat_id: int, day_key: str) -> set[str]:
    store = get_chat_store(int(viewer_chat_id))
    item = store.get('secret_delete_selection') or {}
    if int(item.get('target_chat_id') or 0) != int(target_chat_id) or str(item.get('day_key') or '') != str(day_key):
        item = {'target_chat_id': int(target_chat_id), 'day_key': str(day_key), 'modes': []}
        store['secret_delete_selection'] = item
        save_data(data)
    return {m for m in item.get('modes') or [] if m in SECRET_DELETE_MODES}

# --- secret:0084 · from 04_messages_features.py:841 · public set_secret_delete_selection ---
def set_secret_delete_selection(viewer_chat_id: int, target_chat_id: int, day_key: str, selected: set[str]):
    store = get_chat_store(int(viewer_chat_id))
    store['secret_delete_selection'] = {'target_chat_id': int(target_chat_id), 'day_key': str(day_key), 'modes': [m for m in SECRET_DELETE_MODES if m in set(selected or set())]}
    save_data(data)

# --- secret:0085 · from 04_messages_features.py:846 · public toggle_secret_delete_selection ---
def toggle_secret_delete_selection(viewer_chat_id: int, target_chat_id: int, day_key: str, mode: str) -> set[str]:
    selected = _secret_delete_selection(viewer_chat_id, target_chat_id, day_key)
    if mode in selected:
        selected.discard(mode)
    elif mode in SECRET_DELETE_MODES:
        if mode == 'all':
            selected = {'all'}
        else:
            selected.discard('all')
            selected.add(mode)
    set_secret_delete_selection(viewer_chat_id, target_chat_id, day_key, selected)
    return selected

# --- secret:0086 · from 04_messages_features.py:859 · public build_secret_delete_text ---
def build_secret_delete_text(viewer_chat_id: int, target_chat_id: int, day_key: str) -> str:
    selected = _secret_delete_selection(viewer_chat_id, target_chat_id, day_key)
    lines = [f'🗑 Удаление секретных данных: {get_chat_display_name(target_chat_id)}', f'📅 Точка отсчёта: {fmt_date_ddmmyy(day_key)}', '', 'Выбери период галочкой и нажми «Удалить выбранное».', 'Удаляются текст, фото, видео, документы и другие секретные записи.', '']
    for mode in SECRET_DELETE_MODES:
        mark = '☑️' if mode in selected else '⬛'
        title = {'day': 'День', 'week': 'Неделя', 'month': 'Месяц', 'all': 'Всё'}.get(mode, mode)
        lines.append(f'{mark} {title}: {_secret_delete_period_label(mode, day_key)} — {_secret_delete_count(target_chat_id, mode, day_key)}')
    return '\n'.join(lines)

# --- secret:0087 · from 04_messages_features.py:868 · public build_secret_delete_keyboard ---
def build_secret_delete_keyboard(viewer_chat_id: int, target_chat_id: int, day_key: str, self_only: bool=False, remaining: int=SECRET_AUTO_CLOSE_SECONDS):
    selected = _secret_delete_selection(viewer_chat_id, target_chat_id, day_key)
    kb = types.InlineKeyboardMarkup(row_width=2)
    for mode in SECRET_DELETE_MODES:
        mark = '☑️' if mode in selected else '⬛'
        title = {'day': '🗑 День', 'week': '🗑 Неделя', 'month': '🗑 Месяц', 'all': '🗑 Всё'}.get(mode, mode)
        count = _secret_delete_count(target_chat_id, mode, day_key)
        kb.row(IB(f'{mark} {title} ({count})', callback_data=f'secdelt:{target_chat_id}:{day_key}:{mode}'))
    kb.row(IB('🗑 Удалить выбранное', callback_data=f'secdelgo:{target_chat_id}:{day_key}'))
    kb.row(IB('🔙 Назад', callback_data=f'secchatcal:{target_chat_id}:{day_key[:7]}'), IB(_secret_close_label(remaining), callback_data='secclose'))
    return kb

# --- secret:0088 · from 04_messages_features.py:880 · public _delete_secret_mega_media_paths ---
def _delete_secret_mega_media_paths(paths: list[str]):
    if not paths or not mega_is_configured():
        return
    for remote_path in sorted(set((str(p) for p in paths if p))):
        try:
            _mega_run('mega-rm', [remote_path], check=False, timeout=30)
        except Exception as e:
            log_error(f'delete secret mega media {remote_path}: {e}')

# --- secret:0089 · from 04_messages_features.py:889 · public delete_secret_records_by_modes ---
def delete_secret_records_by_modes(target_chat_id: int, modes: set[str], day_key: str) -> int:
    target_chat_id = int(target_chat_id)
    modes = {m for m in modes or set() if m in SECRET_DELETE_MODES}
    if not modes:
        return 0
    records = _secret_records(target_chat_id)
    kept = []
    deleted = []
    for record in records:
        if any((_secret_record_matches_delete_mode(record, mode, day_key) for mode in modes)):
            deleted.append(record)
        else:
            kept.append(record)
    if not deleted:
        return 0
    media_paths = [str(r.get('mega_media_path') or '') for r in deleted if r.get('mega_media_path')]
    records[:] = kept
    _renumber_secret_media_numbers(target_chat_id)
    save_data(data)
    schedule_config_backup_for_chats(target_chat_id, delay=0.2)
    if media_paths:
        BACKUP_TASK_POOL.submit(f'secret-media-delete:{target_chat_id}', _delete_secret_mega_media_paths, media_paths)
    schedule_secret_mega_upload(target_chat_id)
    refresh_secret_windows(target_chat_id)
    return len(deleted)

# --- secret:0090 · from 04_messages_features.py:915 · public delete_secret_records_by_ids ---
def delete_secret_records_by_ids(target_chat_id: int, record_ids: set[int]) -> int:
    target_chat_id = int(target_chat_id)
    record_ids = {int(x) for x in record_ids or set()}
    if not record_ids:
        return 0
    records = _secret_records(target_chat_id)
    deleted = [record for record in records if int(record.get('id') or 0) in record_ids]
    if not deleted:
        return 0
    records[:] = [record for record in records if int(record.get('id') or 0) not in record_ids]
    media_paths = [str(record.get('mega_media_path') or '') for record in deleted if record.get('mega_media_path')]
    _renumber_secret_media_numbers(target_chat_id)
    save_data(data)
    schedule_config_backup_for_chats(target_chat_id, delay=0.2)
    if media_paths:
        BACKUP_TASK_POOL.submit(f'secret-media-delete:{target_chat_id}', _delete_secret_mega_media_paths, media_paths)
    schedule_secret_mega_upload(target_chat_id)
    refresh_secret_windows(target_chat_id)
    return len(deleted)

# --- secret:0091 · from 04_messages_features.py:935 · public build_secret_day_keyboard ---
def build_secret_day_keyboard(target_chat_id: int, day_key: str, self_only: bool=False, remaining: int=SECRET_AUTO_CLOSE_SECONDS):
    base = datetime.strptime(day_key, '%Y-%m-%d')
    prev_day = (base - timedelta(days=1)).strftime('%Y-%m-%d')
    next_day = (base + timedelta(days=1)).strftime('%Y-%m-%d')
    kb = types.InlineKeyboardMarkup(row_width=3)
    kb.row(IB('⬅️ День', callback_data=f'secview:{target_chat_id}:{prev_day}'), IB('📅 Сегодня', callback_data=f'secview:{target_chat_id}:{today_key()}'), IB('День ➡️', callback_data=f'secview:{target_chat_id}:{next_day}'))
    kb.row(IB('📅 Календарь', callback_data=f'secchatcal:{target_chat_id}:{day_key[:7]}'), IB('🎞️', callback_data=f'secmedia:{target_chat_id}:{day_key}'), IB('✏️ Изменить', callback_data=f'secedit:{target_chat_id}:{day_key}'))
    if self_only:
        kb.row(IB(_secret_close_label(remaining), callback_data='secclose'))
    else:
        kb.row(IB('🔙 Назад', callback_data='secbacklist'), IB(_secret_close_label(remaining), callback_data='secclose'))
    return kb

# --- secret:0092 · from 04_messages_features.py:948 · public register_secret_window ---
def register_secret_window(viewer_chat_id: int, message_id: int, target_chat_id: int, kind: str, day_key: str | None=None, month_key: str | None=None, self_only: bool=False):
    store = get_chat_store(int(viewer_chat_id))
    store['secret_active_window'] = {'message_id': int(message_id), 'target_chat_id': int(target_chat_id), 'kind': str(kind), 'day_key': day_key, 'month_key': month_key, 'self_only': bool(self_only)}
    store['secret_last_target_chat_id'] = int(target_chat_id)
    store['secret_last_self_only'] = bool(self_only)
    save_data(data)

# --- secret:0093 · from 04_messages_features.py:955 · public secret_window_self_only ---
def secret_window_self_only(viewer_chat_id: int, message_id: int | None=None) -> bool:
    active = get_chat_store(int(viewer_chat_id)).get('secret_active_window') or {}
    if message_id is not None and int(active.get('message_id') or 0) != int(message_id):
        return False
    return bool(active.get('self_only', False))

# --- secret:0094 · from 04_messages_features.py:961 · public clear_secret_window ---
def clear_secret_window(viewer_chat_id: int, message_id: int | None=None):
    store = get_chat_store(int(viewer_chat_id))
    active = store.get('secret_active_window') or {}
    if message_id is None or int(active.get('message_id') or 0) == int(message_id):
        try:
            if message_id is not None:
                _cancel_secret_calendar_timer(int(viewer_chat_id), int(message_id))
        except Exception:
            pass
        store['secret_active_window'] = None
        save_data(data)

# --- secret:0095 · from 04_messages_features.py:973 · public register_secret_list_window ---
def register_secret_list_window(viewer_chat_id: int, message_id: int):
    store = get_chat_store(int(viewer_chat_id))
    target_chat_id = int(store.get('secret_last_target_chat_id') or viewer_chat_id)
    register_secret_window(viewer_chat_id, message_id, target_chat_id, 'list', self_only=False)
    schedule_secret_calendar_close(viewer_chat_id, message_id)

# --- secret:0096 · from 04_messages_features.py:979 · public refresh_secret_windows ---
def refresh_secret_windows(target_chat_id: int):
    target_chat_id = int(target_chat_id)
    for viewer_s, viewer_store in list((data.get('chats', {}) or {}).items()):
        active = (viewer_store or {}).get('secret_active_window') or {}
        if int(active.get('target_chat_id') or 0) != target_chat_id:
            continue
        try:
            viewer_id = int(viewer_s)
            message_id = int(active.get('message_id') or 0)
            kind = active.get('kind')
            self_only = bool(active.get('self_only', False))
            updated = False
            if not message_id:
                continue
            if kind == 'day':
                day_key = active.get('day_key') or _default_secret_day(target_chat_id)
                fast_ui_edit_message_text(viewer_id, message_id, build_secret_day_text(target_chat_id, day_key), reply_markup=build_secret_day_keyboard(target_chat_id, day_key, self_only=self_only), purpose='refresh_secret_windows')
                updated = True
            elif kind == 'edit':
                day_key = active.get('day_key') or _default_secret_day(target_chat_id)
                fast_ui_edit_message_text(viewer_id, message_id, build_secret_edit_text(target_chat_id, day_key), reply_markup=build_secret_edit_keyboard(viewer_id, target_chat_id, day_key, self_only=self_only), purpose='refresh_secret_windows')
                updated = True
            elif kind == 'delete':
                day_key = active.get('day_key') or _default_secret_day(target_chat_id)
                fast_ui_edit_message_text(viewer_id, message_id, build_secret_delete_text(viewer_id, target_chat_id, day_key), reply_markup=build_secret_delete_keyboard(viewer_id, target_chat_id, day_key, self_only=self_only), purpose='refresh_secret_windows')
                updated = True
            elif kind == 'calendar':
                month_key = active.get('month_key') or now_local().strftime('%Y-%m')
                fast_ui_edit_message_text(viewer_id, message_id, f'🔐 Секретные сообщения\n{get_chat_display_name(target_chat_id)}\n📅 {month_key}', reply_markup=build_secret_calendar_keyboard(target_chat_id, month_key, self_only=self_only), purpose='refresh_secret_windows')
                updated = True
            elif kind == 'month_list':
                month_key = active.get('month_key') or now_local().strftime('%Y-%m')
                fast_ui_edit_message_text(viewer_id, message_id, build_secret_month_summary_text(target_chat_id, month_key), reply_markup=build_secret_month_summary_keyboard(target_chat_id, month_key, self_only=self_only), purpose='refresh_secret_windows')
                updated = True
            if updated:
                schedule_secret_calendar_close(viewer_id, message_id)
        except Exception as e:
            if 'message is not modified' not in str(e).lower():
                log_error(f'refresh_secret_windows({target_chat_id}): {e}')

# --- secret:0097 · from 04_messages_features.py:1019 · public open_secret_day_window ---
def open_secret_day_window(chat_id: int, target_chat_id: int, day_key: str | None=None, message_id: int | None=None, self_only: bool=False):
    day_key = day_key or _default_secret_day(target_chat_id)
    text = build_secret_day_text(target_chat_id, day_key)
    kb = build_secret_day_keyboard(target_chat_id, day_key, self_only=self_only)
    if message_id:
        fast_ui_edit_message_text(chat_id, message_id, text, reply_markup=kb, purpose='secret_open_window')
        register_secret_window(chat_id, message_id, target_chat_id, 'day', day_key=day_key, self_only=self_only)
        schedule_secret_calendar_close(chat_id, message_id)
        return message_id
    sent = bot.send_message(chat_id, text, reply_markup=kb)
    register_secret_window(chat_id, sent.message_id, target_chat_id, 'day', day_key=day_key, self_only=self_only)
    schedule_secret_calendar_close(chat_id, sent.message_id)
    return sent.message_id

# --- secret:0098 · from 04_messages_features.py:1033 · public compose_secret_edit_insert ---
def compose_secret_edit_insert(target_chat_id: int, record: dict) -> str:
    meta = f"{SECRET_EDIT_TOKEN}|{int(target_chat_id)}|{int(record.get('id') or 0)}|"
    return f"({meta} служебное — можно не трогать)\n\n{record.get('text', '')}"

# --- secret:0099 · from 04_messages_features.py:1037 · public _secret_edit_delete_selection ---
def _secret_edit_delete_selection(viewer_chat_id: int, target_chat_id: int, day_key: str) -> set[int]:
    store = get_chat_store(int(viewer_chat_id))
    item = store.get('secret_edit_delete_selection') or {}
    if int(item.get('target_chat_id') or 0) != int(target_chat_id) or str(item.get('day_key') or '') != str(day_key):
        item = {'target_chat_id': int(target_chat_id), 'day_key': str(day_key), 'ids': []}
        store['secret_edit_delete_selection'] = item
        save_data(data)
    return {int(x) for x in item.get('ids') or [] if str(x).lstrip('-').isdigit()}

# --- secret:0100 · from 04_messages_features.py:1046 · public set_secret_edit_delete_selection ---
def set_secret_edit_delete_selection(viewer_chat_id: int, target_chat_id: int, day_key: str, selected: set[int]):
    store = get_chat_store(int(viewer_chat_id))
    store['secret_edit_delete_selection'] = {'target_chat_id': int(target_chat_id), 'day_key': str(day_key), 'ids': sorted((int(x) for x in selected or set()))}
    save_data(data)

# --- secret:0101 · from 04_messages_features.py:1051 · public toggle_secret_edit_delete_selection ---
def toggle_secret_edit_delete_selection(viewer_chat_id: int, target_chat_id: int, day_key: str, record_id: int) -> set[int]:
    selected = _secret_edit_delete_selection(viewer_chat_id, target_chat_id, day_key)
    record_id = int(record_id)
    if record_id in selected:
        selected.remove(record_id)
    else:
        selected.add(record_id)
    set_secret_edit_delete_selection(viewer_chat_id, target_chat_id, day_key, selected)
    return selected

# --- secret:0102 · from 04_messages_features.py:1061 · public build_secret_edit_text ---
def build_secret_edit_text(target_chat_id: int, day_key: str) -> str:
    lines = ['✏️ Изменить секретные данные', get_chat_display_name(target_chat_id), f'📅 {fmt_date_ddmmyy(day_key)}', '']
    records = _secret_day_records(target_chat_id, day_key)
    if not records:
        lines.append('Нет данных для изменения.')
    for idx, item in enumerate(records, 1):
        ts = str(item.get('timestamp') or '')
        stamp = ts[11:19] if len(ts) >= 19 else ''
        body = re.sub('\\s+', ' ', _secret_record_display_text(item)).strip()
        if len(body) > 220:
            body = body[:217].rstrip() + '…'
        lines.append(f'{idx}. {stamp} — {body}')
    text = '\n'.join(lines)
    return text if len(text) <= 3900 else text[:3890] + '\n…'

# --- secret:0103 · from 04_messages_features.py:1076 · public build_secret_edit_keyboard ---
def build_secret_edit_keyboard(viewer_chat_id: int, target_chat_id: int, day_key: str, self_only: bool=False, remaining: int=SECRET_AUTO_CLOSE_SECONDS):
    kb = types.InlineKeyboardMarkup(row_width=2)
    selected = _secret_edit_delete_selection(viewer_chat_id, target_chat_id, day_key)
    for idx, item in enumerate(_secret_day_records(target_chat_id, day_key), 1):
        ts = str(item.get('timestamp') or '')
        stamp = ts[11:19] if len(ts) >= 19 else ''
        record_id = int(item.get('id') or 0)
        label = f'{idx}. {fmt_date_ddmmyy(day_key)} {stamp} ✏️'
        delete_label = '☑️ Удалить' if record_id in selected else '⬛ Удалить'
        kb.row(IB(label, callback_data=f'secedfull:{target_chat_id}:{day_key}:{record_id}'), IB(delete_label, callback_data=f'secedtoggle:{target_chat_id}:{day_key}:{record_id}'))
    if not _secret_day_records(target_chat_id, day_key):
        kb.row(IB('Нет данных для изменения', callback_data='none'))
    if selected:
        kb.row(IB('🗑 Удалить выбранное', callback_data=f'secedselected:{target_chat_id}:{day_key}'))
    kb.row(IB('🔙 Назад', callback_data=f'secview:{target_chat_id}:{day_key}'))
    kb.row(IB(_secret_close_label(remaining), callback_data='secclose'))
    return kb

# --- secret:0104 · from 04_messages_features.py:1094 · public _secret_full_edit_clear ---
def _secret_full_edit_clear(viewer_chat_id: int, delete_helpers: bool=True):
    store = get_chat_store(int(viewer_chat_id))
    wait = store.get('secret_full_edit_wait') or {}
    store['secret_full_edit_wait'] = None
    save_data(data, chat_ids=[int(viewer_chat_id)])
    try:
        DELAYED_SCHEDULER.cancel(f'secret-full-edit-timeout:{int(viewer_chat_id)}')
    except Exception:
        pass
    if delete_helpers:
        for mid in list(wait.get('helper_message_ids') or []) + [wait.get('prompt_message_id')]:
            try:
                if mid:
                    bot.delete_message(int(viewer_chat_id), int(mid))
            except Exception:
                pass
    return wait

# --- secret:0105 · from 04_messages_features.py:1112 · public _secret_full_edit_timeout ---
def _secret_full_edit_timeout(viewer_chat_id: int, token: str):
    wait = get_chat_store(int(viewer_chat_id)).get('secret_full_edit_wait') or {}
    if str(wait.get('token') or '') != str(token):
        return
    _secret_full_edit_clear(int(viewer_chat_id), delete_helpers=True)
    send_and_auto_delete(int(viewer_chat_id), '⌛ Изменение полного секретного текста отменено по таймеру.', 8)

# --- secret:0106 · from 04_messages_features.py:1119 · public _canon_begin_secret_full_edit__001 ---
def _canon_begin_secret_full_edit__001(viewer_chat_id: int, target_chat_id: int, day_key: str, record_id: int, source_window_msg_id=None) -> bool:
    viewer_chat_id = int(viewer_chat_id)
    target_chat_id = int(target_chat_id)
    record_id = int(record_id)
    if not can_manage_secret_target(viewer_chat_id, target_chat_id):
        return False
    record = next((r for r in _secret_records(target_chat_id) if int(r.get('id') or 0) == record_id), None)
    if not isinstance(record, dict):
        send_and_auto_delete(viewer_chat_id, '❌ Секретная запись не найдена.', 8)
        return False
    _secret_full_edit_clear(viewer_chat_id, delete_helpers=True)
    helper_ids = []
    full_text = str(record.get('text') or '')
    chunks = [full_text[i:i + 3300] for i in range(0, len(full_text), 3300)] or ['']
    for idx, chunk in enumerate(chunks, 1):
        sent = bot.send_message(viewer_chat_id, f'📄 Текущий полный текст ({idx}/{len(chunks)})\n\n{chunk}')
        helper_ids.append(int(sent.message_id))
    try:
        txt = io.BytesIO(full_text.encode('utf-8'))
        txt.name = f'secret_{record_id}_full_text.txt'
        sent_file = bot.send_document(viewer_chat_id, txt, caption='📎 Полный текст одним файлом. Его можно отредактировать и прислать ответом на запрос ниже.')
        helper_ids.append(int(sent_file.message_id))
    except Exception as exc:
        bot_journal('secret_full_edit_txt_send_failed', viewer_chat_id, str(exc), 'WARN')
    prompt = bot.send_message(viewer_chat_id, '✏️ Ответьте на это сообщение ПОЛНОСТЬЮ новым текстом.\nДо 4000 символов — обычным сообщением. Более длинный текст — UTF-8 файлом .txt.\nСтарый текст выше показан без обрезания и приложен одним файлом.', reply_markup=types.ForceReply(selective=True, input_field_placeholder='Вставьте весь новый текст'))
    token = f'{viewer_chat_id}:{target_chat_id}:{record_id}:{time.time_ns()}'
    store = get_chat_store(viewer_chat_id)
    store['secret_full_edit_wait'] = {'type': 'secret_full_edit', 'token': token, 'target_chat_id': target_chat_id, 'record_id': record_id, 'day_key': str(day_key), 'prompt_message_id': int(prompt.message_id), 'helper_message_ids': helper_ids, 'source_window_msg_id': int(source_window_msg_id or 0), 'expires_at': time.time() + internal_timer_seconds('input_wait', 40)}
    save_data(data, chat_ids=[viewer_chat_id])
    DELAYED_SCHEDULER.schedule(f'secret-full-edit-timeout:{viewer_chat_id}', internal_timer_seconds('input_wait', 40), _secret_full_edit_timeout, viewer_chat_id, token)
    return True

# --- secret:0107 · from 04_messages_features.py:1151 · public handle_secret_full_edit_reply ---
def handle_secret_full_edit_reply(msg) -> bool:
    content_type = str(getattr(msg, 'content_type', None) or '')
    if content_type not in {'text', 'document'}:
        return False
    viewer_chat_id = int(msg.chat.id)
    wait = get_chat_store(viewer_chat_id).get('secret_full_edit_wait') or {}
    if wait.get('type') != 'secret_full_edit':
        return False
    reply_id = int(getattr(getattr(msg, 'reply_to_message', None), 'message_id', 0) or 0)
    if reply_id != int(wait.get('prompt_message_id') or 0):
        return False
    _durable_note_source_consumed('secret_full_edit_reply')
    target_chat_id = int(wait.get('target_chat_id'))
    record_id = int(wait.get('record_id'))
    if not can_manage_secret_target(viewer_chat_id, target_chat_id):
        _secret_full_edit_clear(viewer_chat_id, delete_helpers=True)
        return True
    new_text = ''
    if content_type == 'text':
        new_text = str(msg.text or '')
        if len(new_text) > 4000:
            send_and_auto_delete(viewer_chat_id, '❌ Текст длиннее 4000 символов. Пришлите его UTF-8 файлом .txt ответом на тот же запрос.', 12)
            return True
    else:
        document = getattr(msg, 'document', None)
        file_name = str(getattr(document, 'file_name', '') or '').lower()
        mime_type = str(getattr(document, 'mime_type', '') or '').lower()
        if not (file_name.endswith('.txt') or mime_type.startswith('text/')):
            send_and_auto_delete(viewer_chat_id, '❌ Нужен обычный UTF-8 файл .txt.', 10)
            return True
        try:
            file_info = bot.get_file(document.file_id)
            raw = bot.download_file(file_info.file_path)
            if len(raw) > 512000:
                raise ValueError('TXT больше 500 КБ')
            new_text = raw.decode('utf-8-sig')
        except Exception as exc:
            bot_journal('secret_full_edit_txt_read_failed', viewer_chat_id, str(exc), 'WARN')
            send_and_auto_delete(viewer_chat_id, '❌ Не удалось прочитать TXT. Сохраните файл в UTF-8 и повторите.', 12)
            return True
    if not str(new_text).strip():
        send_and_auto_delete(viewer_chat_id, '❌ Новый текст пустой. Ответьте на то же сообщение ещё раз.', 10)
        return True
    record = next((r for r in _secret_records(target_chat_id) if int(r.get('id') or 0) == record_id), None)
    if not isinstance(record, dict):
        _secret_full_edit_clear(viewer_chat_id, delete_helpers=True)
        send_and_auto_delete(viewer_chat_id, '❌ Запись уже не найдена.', 8)
        return True
    record['text'] = new_text
    record['edited_at'] = now_local().isoformat(timespec='seconds')
    _durable_note_secret_edit_witness(_durable_secret_edit_witness(target_chat_id, record_id, new_text))
    try:
        bot.delete_message(viewer_chat_id, int(msg.message_id))
    except Exception:
        pass
    _secret_full_edit_clear(viewer_chat_id, delete_helpers=True)
    save_data(data, chat_ids=[target_chat_id, viewer_chat_id])
    schedule_config_backup_for_chats(target_chat_id, viewer_chat_id, delay=0.2)
    schedule_secret_mega_upload(target_chat_id)
    refresh_secret_windows(target_chat_id)
    send_and_auto_delete(viewer_chat_id, '✅ Полный секретный текст изменён.', 8)
    return True

# --- secret:0108 · from 04_messages_features.py:1214 · public handle_secret_edit_insert_message ---
def handle_secret_edit_insert_message(msg) -> bool:
    if getattr(msg, 'content_type', None) != 'text':
        return False
    text = (msg.text or '').strip()
    if SECRET_EDIT_TOKEN + '|' not in text:
        return False
    _durable_note_source_consumed('secret_edit_insert')
    try:
        delete_secret_source_message(msg)
    except Exception:
        pass
    try:
        match = re.search('\\((%s\\|[^)]*)\\)' % re.escape(SECRET_EDIT_TOKEN), text)
        if not match:
            return False
        parts = match.group(1).split('|', 3)
        target_chat_id = int(parts[1])
        record_id = int(parts[2])
        if not is_owner_chat(msg.chat.id) and int(msg.chat.id) != target_chat_id:
            return True
        new_text = sanitize_telegram_inserted_text((text[:match.start()] + ' ' + text[match.end():]).strip())
        target = next((r for r in _secret_records(target_chat_id) if int(r.get('id') or 0) == record_id), None)
        if not target or not new_text:
            send_and_auto_delete(msg.chat.id, '❌ Секретная запись не найдена или текст пуст.', 8)
            return True
        target['text'] = new_text
        target['edited_at'] = now_local().isoformat(timespec='seconds')
        _durable_note_secret_edit_witness(_durable_secret_edit_witness(target_chat_id, record_id, new_text))
        save_data(data)
        schedule_config_backup_for_chats(target_chat_id, delay=0.2)
        schedule_secret_mega_upload(target_chat_id)
        refresh_secret_windows(target_chat_id)
        send_and_auto_delete(msg.chat.id, '✅ Секретные данные изменены.', 8)
        return True
    except Exception as e:
        log_error(f'handle_secret_edit_insert_message: {e}')
        return True

# --- secret:0109 · from 04_messages_features.py:1252 · public build_secret_chat_list_keyboard ---
def build_secret_chat_list_keyboard(remaining: int=SECRET_AUTO_CLOSE_SECONDS):
    kb = types.InlineKeyboardMarkup(row_width=3)
    chats = collect_all_known_chat_ids(include_owner=True)
    for cid in chats:
        mode = '✅' if is_total_secret_mode(cid) else '⬜'
        kb.row(IB(get_chat_display_name(cid)[:28], callback_data=f'seclist:{cid}'), IB(f'{mode} Секрет', callback_data=f'sectoggle:{cid}'), IB('📅', callback_data=f'secchatcal:{cid}'))
    if not chats:
        kb.row(IB('Нет чатов с секретами', callback_data='none'))
    kb.row(IB('🔙 Назад осн. окно', callback_data=f'd:{today_key()}:back_main'), IB(_secret_close_label(remaining), callback_data='secclose'))
    return kb

# --- secret:0110 · from 04_messages_features.py:1263 · public _cancel_secret_calendar_timer ---
def _cancel_secret_calendar_timer(chat_id: int, message_id: int):
    key = (int(chat_id), int(message_id))
    with _secret_calendar_lock:
        token = _secret_calendar_timers.pop(key, None)
        if isinstance(token, dict):
            token['cancelled'] = True
    DELAYED_SCHEDULER.cancel(f'secret-calendar-close:{chat_id}:{message_id}')

# --- secret:0111 · from 04_messages_features.py:1271 · public _build_secret_active_keyboard ---
def _build_secret_active_keyboard(viewer_chat_id: int, active: dict, remaining: int):
    target_chat_id = int(active.get('target_chat_id') or viewer_chat_id)
    kind = str(active.get('kind') or '')
    self_only = bool(active.get('self_only', False))
    if kind == 'list':
        return build_secret_chat_list_keyboard(remaining=remaining)
    if kind == 'day':
        day_key = active.get('day_key') or _default_secret_day(target_chat_id)
        return build_secret_day_keyboard(target_chat_id, day_key, self_only=self_only, remaining=remaining)
    if kind == 'edit':
        day_key = active.get('day_key') or _default_secret_day(target_chat_id)
        return build_secret_edit_keyboard(viewer_chat_id, target_chat_id, day_key, self_only=self_only, remaining=remaining)
    if kind == 'delete':
        day_key = active.get('day_key') or _default_secret_day(target_chat_id)
        return build_secret_delete_keyboard(viewer_chat_id, target_chat_id, day_key, self_only=self_only, remaining=remaining)
    if kind == 'calendar':
        month_key = active.get('month_key') or now_local().strftime('%Y-%m')
        return build_secret_calendar_keyboard(target_chat_id, month_key, self_only=self_only, remaining=remaining)
    if kind == 'month_list':
        month_key = active.get('month_key') or now_local().strftime('%Y-%m')
        return build_secret_month_summary_keyboard(target_chat_id, month_key, self_only=self_only, remaining=remaining)
    return None

# --- secret:0112 · from 04_messages_features.py:1294 · public _update_secret_window_countdown ---
def _update_secret_window_countdown(chat_id: int, message_id: int, remaining: int) -> bool:
    active = get_chat_store(int(chat_id)).get('secret_active_window') or {}
    if int(active.get('message_id') or 0) != int(message_id):
        return False
    kb = _build_secret_active_keyboard(chat_id, active, remaining)
    if kb is None:
        return False
    try:
        fast_ui_edit_reply_markup(chat_id, message_id, kb, purpose='message_feature_markup')
        return True
    except Exception as e:
        if 'message is not modified' not in str(e).lower():
            log_error(f'secret window countdown {chat_id}:{message_id}: {e}')
        return True

# --- secret:0113 · from 04_messages_features.py:1309 · public schedule_secret_calendar_close ---
def schedule_secret_calendar_close(chat_id: int, message_id: int):
    """Быстрое автозакрытие секретного окна.

    Важно: больше НЕ редактируем кнопку таймера каждые 5 секунд.
    Частые edit_message_reply_markup ловили Telegram 429 и тормозили все кнопки.
    Любой клик просто создаёт новый токен и отсчёт 90 секунд заново.
    """
    _cancel_secret_calendar_timer(chat_id, message_id)
    key = (int(chat_id), int(message_id))
    token = {'cancelled': False, 'generation': time.time_ns()}
    with _secret_calendar_lock:
        _secret_calendar_timers[key] = token

    def close():
        try:
            with _secret_calendar_lock:
                if _secret_calendar_timers.get(key) is not token or token.get('cancelled'):
                    return
            try:
                bot.delete_message(chat_id, message_id)
            except Exception:
                pass
            clear_secret_window(chat_id, message_id)
        finally:
            with _secret_calendar_lock:
                if _secret_calendar_timers.get(key) is token:
                    _secret_calendar_timers.pop(key, None)
    DELAYED_SCHEDULER.schedule(f'secret-calendar-close:{chat_id}:{message_id}', SECRET_AUTO_CLOSE_SECONDS, close)

# --- secret:0114 · from 04_messages_features.py:1338 · public _secret_month_records ---
def _secret_month_records(target_chat_id: int, month_key: str) -> list[dict]:
    prefix = str(month_key or now_local().strftime('%Y-%m'))[:7] + '-'
    return [r for r in _secret_records(int(target_chat_id)) if str(r.get('day_key') or '').startswith(prefix)]

# --- secret:0115 · from 04_messages_features.py:1342 · public build_secret_month_summary_text ---
def build_secret_month_summary_text(target_chat_id: int, month_key: str) -> str:
    if _ensure_secret_media_numbers(target_chat_id):
        save_data(data)
    records = _secret_month_records(target_chat_id, month_key)
    lines = [f'🪬 Секреты за месяц: {get_chat_display_name(target_chat_id)}', f'📅 {month_key}', '']
    if not records:
        lines.append('Нет секретных сообщений за этот месяц.')
    for idx, item in enumerate(records, 1):
        day = fmt_date_ddmmyy(str(item.get('day_key') or ''))
        ts = str(item.get('timestamp') or '')
        stamp = ts[11:16] if len(ts) >= 16 else ''
        body = re.sub('\\s+', ' ', _secret_record_display_text(item)).strip()
        if len(body) > 74:
            body = body[:74].rstrip()
        lines.append(f'{idx}. {day} {stamp} — {body}...')
    text = '\n'.join(lines)
    return text if len(text) <= 3900 else text[:3890] + '\n…'

# --- secret:0116 · from 04_messages_features.py:1360 · public build_secret_month_summary_keyboard ---
def build_secret_month_summary_keyboard(target_chat_id: int, month_key: str, self_only: bool=False, remaining: int=SECRET_AUTO_CLOSE_SECONDS):
    kb = types.InlineKeyboardMarkup(row_width=2)
    kb.row(IB('📅 Календарь', callback_data=f'secchatcal:{target_chat_id}:{month_key}'), IB('🗑 Удалить секреты', callback_data=f'secdel:{target_chat_id}:{month_key}-01'))
    if self_only:
        kb.row(IB(_secret_close_label(remaining), callback_data='secclose'))
    else:
        kb.row(IB('🔙 Назад', callback_data='secbacklist'), IB(_secret_close_label(remaining), callback_data='secclose'))
    return kb

# --- secret:0117 · from 04_messages_features.py:1369 · public open_secret_month_summary ---
def open_secret_month_summary(chat_id: int, target_chat_id: int, month_key: str | None=None, message_id: int | None=None, self_only: bool=False):
    month_key = month_key or now_local().strftime('%Y-%m')
    text = build_secret_month_summary_text(target_chat_id, month_key)
    kb = build_secret_month_summary_keyboard(target_chat_id, month_key, self_only=self_only)
    if message_id:
        fast_ui_edit_message_text(chat_id, message_id, text, reply_markup=kb, purpose='secret_open_window')
        register_secret_window(chat_id, message_id, target_chat_id, 'month_list', month_key=month_key, self_only=self_only)
        schedule_secret_calendar_close(chat_id, message_id)
        return message_id
    sent = bot.send_message(chat_id, text, reply_markup=kb)
    register_secret_window(chat_id, sent.message_id, target_chat_id, 'month_list', month_key=month_key, self_only=self_only)
    schedule_secret_calendar_close(chat_id, sent.message_id)
    return sent.message_id

# --- secret:0118 · from 04_messages_features.py:1383 · public touch_secret_window_timer_for_callback ---
def touch_secret_window_timer_for_callback(chat_id: int, message_id: int, data_str: str | None=None) -> bool:
    """Продлевает автозакрытие любого активного секретного окна при любом нажатии."""
    try:
        active = get_chat_store(int(chat_id)).get('secret_active_window') or {}
        if int(active.get('message_id') or 0) == int(message_id):
            schedule_secret_calendar_close(int(chat_id), int(message_id))
            return True
    except Exception as e:
        log_error(f'touch_secret_window_timer_for_callback({chat_id},{message_id},{data_str}): {e}')
    return False

# --- secret:0119 · from 04_messages_features.py:1394 · public build_secret_calendar_keyboard ---
def build_secret_calendar_keyboard(target_chat_id: int, month_key: str, self_only: bool=False, remaining: int=SECRET_AUTO_CLOSE_SECONDS):
    year, month = (int(x) for x in month_key.split('-', 1))
    marked = {str(r.get('day_key')) for r in _secret_records(target_chat_id)}
    kb = types.InlineKeyboardMarkup(row_width=7)
    kb.row(*[IB(x, callback_data='none') for x in ('Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс')])
    for week in calendar.Calendar(firstweekday=0).monthdayscalendar(year, month):
        row = []
        for day in week:
            if not day:
                row.append(IB(' ', callback_data='none'))
                continue
            day_key = f'{year:04d}-{month:02d}-{day:02d}'
            label = f'🔐{day}' if day_key in marked else str(day)
            row.append(IB(label, callback_data=f'secday:{target_chat_id}:{day_key}' if day_key in marked else 'none'))
        kb.row(*row)
    first = datetime(year, month, 1)
    prev = (first - timedelta(days=1)).strftime('%Y-%m')
    nxt = (first.replace(day=28) + timedelta(days=4)).replace(day=1).strftime('%Y-%m')
    kb.row(IB('⬅️ Месяц', callback_data=f'secmon:{target_chat_id}:{prev}'), IB('📅 Сегодня', callback_data=f'secview:{target_chat_id}:{today_key()}'), IB('Месяц ➡️', callback_data=f'secmon:{target_chat_id}:{nxt}'))
    anchor_day = today_key() if month_key == now_local().strftime('%Y-%m') else f'{month_key}-01'
    kb.row(IB('🪬', callback_data=f'secmonthlist:{target_chat_id}:{month_key}'), IB('🗑 Удалить секреты', callback_data=f'secdel:{target_chat_id}:{anchor_day}'))
    if self_only:
        kb.row(IB(_secret_close_label(remaining), callback_data='secclose'))
    else:
        kb.row(IB('🔙 Назад', callback_data='secbacklist'), IB(_secret_close_label(remaining), callback_data='secclose'))
    return kb

# --- secret:0120 · from 04_messages_features.py:1421 · public open_secret_calendar ---
def open_secret_calendar(chat_id: int, target_chat_id: int, month_key: str | None=None, message_id: int | None=None, self_only: bool=False):
    month_key = month_key or now_local().strftime('%Y-%m')
    text = f'🔐 Секретные сообщения\n{get_chat_display_name(target_chat_id)}\n📅 {month_key}'
    kb = build_secret_calendar_keyboard(target_chat_id, month_key, self_only=self_only)
    if message_id:
        fast_ui_edit_message_text(chat_id, message_id, text, reply_markup=kb, purpose='secret_open_window')
        register_secret_window(chat_id, message_id, target_chat_id, 'calendar', month_key=month_key, self_only=self_only)
        schedule_secret_calendar_close(chat_id, message_id)
        return message_id
    sent = bot.send_message(chat_id, text, reply_markup=kb)
    register_secret_window(chat_id, sent.message_id, target_chat_id, 'calendar', month_key=month_key, self_only=self_only)
    schedule_secret_calendar_close(chat_id, sent.message_id)
    return sent.message_id

# --- secret:0121 · from 04_messages_features.py:1435 · public handle_secret_sequence ---
def handle_secret_sequence(msg) -> bool:
    text = (getattr(msg, 'text', None) or '').strip()
    if text not in {'11', '22', '33'}:
        return False
    user_id = int(getattr(getattr(msg, 'from_user', None), 'id', 0) or 0)
    key = (int(msg.chat.id), user_id)
    now_ts = time.time()
    item = _secret_sequence_state.get(key, {'step': 0, 'ts': 0.0, 'message_ids': []})
    if now_ts - float(item.get('ts', 0)) > 10:
        item = {'step': 0, 'ts': 0.0, 'message_ids': []}
    expected = ('11', '22', '33')[int(item.get('step', 0))]
    if text != expected:
        _secret_sequence_state.pop(key, None)
        return False
    step = int(item.get('step', 0)) + 1
    message_ids = list(item.get('message_ids') or []) + [int(msg.message_id)]
    _durable_note_source_consumed('secret_sequence')
    if step == 3:
        _secret_sequence_state.pop(key, None)
        open_secret_calendar(msg.chat.id, msg.chat.id, self_only=True)
        for message_id in message_ids:
            try:
                bot.delete_message(msg.chat.id, message_id)
            except Exception as e:
                log_error(f'secret sequence delete {msg.chat.id}:{message_id}: {e}')
                delete_message_later(msg.chat.id, message_id, 1)
        return True
    _secret_sequence_state[key] = {'step': step, 'ts': now_ts, 'message_ids': message_ids}
    return True

# --- secret:0122 · from 04_messages_features.py:1530 · public _secret_media_command_target ---
def _secret_media_command_target(viewer_chat_id: int) -> int:
    store = get_chat_store(int(viewer_chat_id))
    active = store.get('secret_active_window') or {}
    target = active.get('target_chat_id') or store.get('secret_last_target_chat_id') or viewer_chat_id
    try:
        target = int(target)
    except Exception:
        target = int(viewer_chat_id)
    if not is_owner_chat(viewer_chat_id) and target != int(viewer_chat_id):
        target = int(viewer_chat_id)
    return target

# --- secret:0123 · from 05_finance_ui.py:6274 · public schedule_secret_edit_refresh_window ---
def schedule_secret_edit_refresh_window(viewer_chat_id: int, message_id: int, target_chat_id: int, day_key: str, self_only: bool=False, delay: float=0.7):
    key = (int(viewer_chat_id), int(message_id))
    generation = time.time_ns()
    scheduler_key = f'secret-edit-refresh:{key[0]}:{key[1]}'

    def _job():
        try:
            with _secret_edit_refresh_lock:
                if _secret_edit_refresh_timers.get(key) != generation:
                    return
            text = build_secret_edit_text(int(target_chat_id), day_key)
            kb = build_secret_edit_keyboard(int(viewer_chat_id), int(target_chat_id), day_key, self_only=bool(self_only))
            try:
                fast_ui_edit_message_text(int(viewer_chat_id), int(message_id), text, reply_markup=kb, purpose='secret_edit_debounce')
            except Exception as e:
                if not is_telegram_429(e) and 'message is not modified' not in str(e).lower():
                    log_error(f'secret edit debounce refresh {viewer_chat_id}:{message_id}: {e}')
            register_secret_window(int(viewer_chat_id), int(message_id), int(target_chat_id), 'edit', day_key=day_key, self_only=bool(self_only))
            schedule_secret_calendar_close(int(viewer_chat_id), int(message_id))
        finally:
            with _secret_edit_refresh_lock:
                if _secret_edit_refresh_timers.get(key) == generation:
                    _secret_edit_refresh_timers.pop(key, None)
    with _secret_edit_refresh_lock:
        DELAYED_SCHEDULER.cancel(scheduler_key)
        _secret_edit_refresh_timers[key] = generation
        DELAYED_SCHEDULER.schedule(scheduler_key, float(delay), _job)

# --- secret:0124 · from 07_state_web.py:2391 · public _v149_seal_secret ---
def _v149_seal_secret(raw: str) -> str:
    master = _v149_google_master_key()
    nonce = _v149_secrets.token_bytes(16)
    enc_key = _v149_hmac.new(master, b'enc:' + nonce, _v149_hashlib.sha256).digest()
    mac_key = _v149_hmac.new(master, b'mac:' + nonce, _v149_hashlib.sha256).digest()
    cipher = _v149_stream_xor(str(raw).encode('utf-8'), enc_key, nonce)
    tag = _v149_hmac.new(mac_key, b'v1:' + nonce + cipher, _v149_hashlib.sha256).digest()
    return 'v1.' + _v149_base64.urlsafe_b64encode(nonce + tag + cipher).decode('ascii')

# --- secret:0125 · from 07_state_web.py:2400 · public _v149_open_secret ---
def _v149_open_secret(sealed: str) -> str:
    if not str(sealed or '').startswith('v1.'):
        raise RuntimeError('Формат зашифрованного Google-ключа не поддерживается')
    try:
        blob = _v149_base64.urlsafe_b64decode(str(sealed).split('.', 1)[1].encode('ascii'))
        nonce, tag, cipher = (blob[:16], blob[16:48], blob[48:])
    except Exception as exc:
        raise RuntimeError(f'Google-ключ повреждён: {exc}')
    master = _v149_google_master_key()
    enc_key = _v149_hmac.new(master, b'enc:' + nonce, _v149_hashlib.sha256).digest()
    mac_key = _v149_hmac.new(master, b'mac:' + nonce, _v149_hashlib.sha256).digest()
    expected = _v149_hmac.new(mac_key, b'v1:' + nonce + cipher, _v149_hashlib.sha256).digest()
    if not _v149_hmac.compare_digest(tag, expected):
        raise RuntimeError('Google-ключ не прошёл проверку целостности')
    try:
        return _v149_stream_xor(cipher, enc_key, nonce).decode('utf-8')
    except Exception as exc:
        raise RuntimeError(f'Google-ключ не расшифрован: {exc}')

# --- secret:0126 · from 07_state_web.py:9023 · public _v153_secret_values ---
def _v153_secret_values() -> list[str]:
    values = set()
    for key, value in _v153_os.environ.items():
        if _V153_ENV_SECRET_RE.search(str(key)) and value and (len(str(value)) >= 6):
            values.add(str(value))
    for name in ('MEGA_EMAIL', 'MEGA_PASSWORD', 'BOT_TOKEN', 'B_T', 'GOOGLE_SERVICE_ACCOUNT_JSON', 'TENANT_GOOGLE_MASTER_KEY', 'GOOGLE_TENANT_MASTER_KEY', 'WEBHOOK_SECRET'):
        value = str(globals().get(name) or _v153_os.getenv(name) or '')
        if value and len(value) >= 6:
            values.add(value)
    return sorted(values, key=len, reverse=True)

# --- secret:0127 · from 08_reliability_tasks.py:145 · public _canon_handle_o9_secret_triple_click__001 ---
def _canon_handle_o9_secret_triple_click__001(call, data_str: str) -> bool:
    return False

# --- secret:0128 · from 08_reliability_tasks.py:15350 · public _canon_begin_secret_full_edit__002 ---
def _canon_begin_secret_full_edit__002(viewer_chat_id: int, target_chat_id: int, day_key: str, record_id: int, source_window_msg_id=None) -> bool:
    ok = _V213_PREV_SECRET_BEGIN(viewer_chat_id, target_chat_id, day_key, record_id, source_window_msg_id)
    if not ok:
        return ok
    try:
        wait = get_chat_store(int(viewer_chat_id)).get('secret_full_edit_wait') or {}
        sid = _v213_input_sid()
        wait['v213_session_id'] = sid
        sent = bot.send_message(int(viewer_chat_id), _v213_prompt_text('Редактирование полного SECRET-текста активно.'), reply_markup=_v213_cancel_markup('secret', sid))
        wait.setdefault('helper_message_ids', []).append(int(getattr(sent, 'message_id', 0) or 0))
        save_data(data, chat_ids=[int(viewer_chat_id)])
    except Exception:
        pass
    return ok

# --- secret:0129 · from 09_final_transport.py:2622 · public secret_storage_status_text_v234 ---
def secret_storage_status_text_v234() -> str:
    requested = str(globals().get('secret_storage_backend_v234', lambda: 'telegram')())
    effective = str(globals().get('secret_storage_effective_backend_v234', lambda: requested)())
    return f"🔐 SECRET STORAGE · выс-264\n\nПрофиль backup: {storage_profile_v237_1()}\nSECRET выбран: {('☁️ MEGA' if requested == 'mega' else '📡 Telegram')}\nЭффективно: {('☁️ MEGA' if effective == 'mega' else '📡 Telegram')}\n\nПри выборе общего профиля MEGA SECRET автоматически переводится в MEGA; при двух других профилях — в Telegram."[:3900]

# --- secret:0130 · from 09_final_transport.py:2627 · public secret_storage_keyboard_v234 ---
def secret_storage_keyboard_v234():
    kb = types.InlineKeyboardMarkup()
    req = secret_storage_backend_v234()
    p = storage_profile_v237_1()
    kb.row(IB(('✅ ' if req == 'telegram' else '⬜ ') + '📡 Telegram', callback_data='v237:storage:secret_tg'))
    kb.row(IB(('✅ ' if req == 'mega' else '⬜ ') + '☁️ MEGA', callback_data='v237:storage:secret_mega'))
    kb.row(IB('🔙 Хранилище', callback_data='v237:storage:open'))
    kb.row(IB('❌ Закрыть', callback_data='info_close'))
    return kb

# --- secret:0131 · from 10_split_policy_offload.py:1134 · public _split_secret ---
def _split_secret():
    return str(_split_os.getenv("PEER_SHARED_SECRET", "") or "").strip()

# v267
