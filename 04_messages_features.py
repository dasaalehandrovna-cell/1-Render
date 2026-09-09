# v262

# --- ИСТОЧНИК: 30_secret.py ---
SECRET_CODEWORDS = {'секрет', 'сикрет', 'secret', 'sicret', 'sekret', 'sikret', 'cekret', 'cikret', '🤫', '🙊', '🤐', '🔐', '🔏'}
OWNER_ACTIVATION_RE = re.compile('^/(?:владелец|vladelec)(?:1904|-1904|_1904)(?:@\\w+)?$', re.I)
SECRET_ACCESS_RE = re.compile('^/(?:секрет|secret|sekret|cekret)(?:(?:1904|-1904|_1904))?(?:@\\w+)?$', re.I)
_secret_sequence_state = {}
_secret_calendar_timers = {}
_secret_calendar_lock = threading.RLock()
_secret_mega_locks = defaultdict(threading.Lock)
_secret_media_timer_lock = threading.RLock()
_secret_media_timer_generation = {}
SECRET_AUTO_CLOSE_SECONDS = 90
SECRET_COUNTDOWN_STEP_SECONDS = 30

def _secret_countdown_text(seconds: int) -> str:
    seconds = max(0, int(seconds))
    return f'{seconds // 60:02d}:{seconds % 60:02d}'

def _secret_close_label(remaining: int=SECRET_AUTO_CLOSE_SECONDS) -> str:
    return f'❌ Закрыть {_secret_countdown_text(remaining)}'

def _secret_records(chat_id: int) -> list:
    store = get_chat_store(int(chat_id))
    records = store.setdefault('secret_messages', [])
    if not isinstance(records, list):
        records = []
        store['secret_messages'] = records
    return records

def _is_secret_media_record(record: dict) -> bool:
    return str((record or {}).get('content_type') or 'text') != 'text'

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

def _next_secret_media_number(chat_id: int) -> int:
    _ensure_secret_media_numbers(chat_id)
    numbers = [int(record.get('media_number') or 0) for record in _secret_records(int(chat_id)) if _is_secret_media_record(record)]
    return max(numbers or [0]) + 1

def _secret_media_record_by_number(chat_id: int, number: int) -> dict | None:
    if _ensure_secret_media_numbers(chat_id):
        save_data(data)
    return next((record for record in _secret_records(int(chat_id)) if _is_secret_media_record(record) and int(record.get('media_number') or 0) == int(number)), None)

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

def _secret_file_id(msg):
    try:
        ct = getattr(msg, 'content_type', '')
        value = getattr(msg, ct, None)
        if ct == 'photo' and value:
            return value[0].file_id
        return getattr(value, 'file_id', None)
    except Exception:
        return None

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

def _secret_message_text(msg, cleaned_text: str | None=None) -> str:
    if cleaned_text is not None:
        return cleaned_text.strip()
    text = (getattr(msg, 'text', None) or getattr(msg, 'caption', None) or '').strip()
    if text:
        return text
    return f"[{getattr(msg, 'content_type', 'message')}]"

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

def _secret_chat_payload(chat_id: int) -> dict:
    return {'kind': 'chat_secret_messages_plain_text', 'version': VERSION, 'chat_id': int(chat_id), 'chat_name': get_chat_display_name(int(chat_id)), 'updated_at': now_local().isoformat(), 'messages': list(_secret_records(int(chat_id)))}

def _secret_media_remote_name(record: dict, telegram_path: str) -> str:
    content = record.get('content') or {}
    original = str(content.get('file_name') or os.path.basename(telegram_path or '') or '')
    ext = os.path.splitext(original)[1].lower()
    if not ext:
        ext = {'photo': '.jpg', 'video': '.mp4', 'animation': '.mp4', 'video_note': '.mp4', 'voice': '.ogg', 'audio': '.mp3', 'sticker': '.webp'}.get(str(record.get('content_type') or ''), '.bin')
    stem = mega_safe_name(os.path.splitext(original)[0], str(record.get('content_type') or 'file'))
    return f"{int(record.get('id') or 0)}_{int(record.get('source_msg_id') or 0)}_{stem}{ext[:10]}"

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
_secret_mega_upload_timers = {}
_secret_mega_upload_lock = threading.RLock()

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

def is_total_secret_mode(chat_id: int) -> bool:
    return bool(get_chat_store(int(chat_id)).setdefault('settings', {}).get('total_secret_mode', False))

def set_total_secret_mode(chat_id: int, enabled: bool):
    store = get_chat_store(int(chat_id))
    store.setdefault('settings', {})['total_secret_mode'] = bool(enabled)
    save_data(data)
    schedule_config_backup_for_chats(chat_id)
TOTAL_SECRET_DECOY_PHRASES = ['Внимание и покой.', 'Осознанность здесь.', 'Тишина внутри.', 'Путь сердца.', 'Наблюдай себя.', 'Дыши глубже.', 'Присутствуй сейчас.', 'Свет внутри.', 'Любовь сильнее.', 'Мир в сердце.', 'Благодарность растёт.', 'Внутренняя работа.', 'Помни себя.', 'Будь свидетелем.', 'Не спи внутри.', 'Шаг к свету.', 'Сознание расширяется.', 'Тело помнит.', 'Душа учится.', 'Сердце открыто.', 'Молчание лечит.', 'Принятие есть.', 'Путь продолжается.', 'Воля и внимание.', 'Сила в тишине.', 'Радость без причины.', 'Любовь без условий.', 'Свидетель молчит.', 'Энергия вверх.', 'Чистое намерение.', 'Здесь и сейчас.', 'Осознанный выбор.', 'Божественное рядом.', 'Внутренний свет.', 'Учись видеть.', 'Покой глубже слов.', 'Смотри внутрь.', 'Развитие души.', 'Практика внимания.', 'Тишина ума.', 'Сердце знает.', 'Пусть будет свет.', 'Благость и мир.', 'Память о себе.', 'Человек пробуждается.', 'Дух ведёт.', 'Созерцай спокойно.', 'Истина проста.', 'Мягкая сила.', 'Светлая мысль.', 'Пробуждение рядом.', 'Душевный рост.', 'Путь любви.', 'Молитва сердца.', 'Чистое сознание.', 'Терпение и вера.', 'Гармония внутри.', 'Служение добру.', 'Внутренний учитель.', 'Свобода ума.', 'Осознай момент.', 'Сохрани тишину.', 'Открой сердце.', 'Иди глубже.', 'Будь настоящим.', 'Свети спокойно.', 'Доверяй пути.', 'Живи осознанно.']

def total_secret_decoy_text(msg) -> str:
    try:
        seed = int(getattr(msg, 'message_id', 0) or 0) + int(getattr(getattr(msg, 'chat', None), 'id', 0) or 0)
        return TOTAL_SECRET_DECOY_PHRASES[abs(seed) % len(TOTAL_SECRET_DECOY_PHRASES)]
    except Exception:
        return 'Тишина внутри.'

def maybe_send_total_secret_decoy(msg):
    try:
        if not total_secret_mask_enabled(msg.chat.id):
            return
        if not is_total_secret_mode(msg.chat.id):
            return
        _tg_call_retry(bot.send_message, msg.chat.id, total_secret_decoy_text(msg), purpose='total_secret_decoy')
    except Exception as e:
        log_error(f"maybe_send_total_secret_decoy({getattr(getattr(msg, 'chat', None), 'id', '?')}): {e}")

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

def secret_chats() -> list[int]:
    out = []
    for cid, store in (data.get('chats', {}) or {}).items():
        try:
            if (store.get('secret_messages') or []) or bool((store.get('settings') or {}).get('total_secret_mode', False)):
                out.append(int(cid))
        except Exception:
            continue
    return sorted(set(out), key=lambda x: get_chat_display_name(x).casefold())

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

def build_secret_media_timer_keyboard(remaining: int=SECRET_AUTO_CLOSE_SECONDS):
    kb = types.InlineKeyboardMarkup(row_width=2)
    kb.row(IB(_secret_close_label(remaining), callback_data='secmclose'), IB(f'⏳ {_secret_countdown_text(remaining)} Закроется', callback_data='secmwait'))
    return kb

def cancel_secret_media_timer(chat_id: int, message_id: int):
    key = (int(chat_id), int(message_id))
    with _secret_media_timer_lock:
        _secret_media_timer_generation.pop(key, None)
    DELAYED_SCHEDULER.cancel(f'secret-media-close:{chat_id}:{message_id}')

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

def _send_secret_media_caption_message(viewer_chat_id: int, caption: str):
    try:
        sent = bot.send_message(viewer_chat_id, caption)
        delete_message_later(viewer_chat_id, sent.message_id, SECRET_AUTO_CLOSE_SECONDS)
    except Exception:
        pass

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

def send_secret_records(chat_id: int, target_chat_id: int, day_key: str | None=None):
    for chunk in format_secret_records(int(target_chat_id), day_key):
        bot.send_message(int(chat_id), chunk)
SECRET_EDIT_TOKEN = 'EDITSECRET'

def _secret_day_records(target_chat_id: int, day_key: str) -> list[dict]:
    return [r for r in _secret_records(target_chat_id) if str(r.get('day_key')) == str(day_key)]

def _default_secret_day(target_chat_id: int) -> str:
    days = sorted({str(r.get('day_key')) for r in _secret_records(target_chat_id) if r.get('day_key')})
    return days[-1] if days else today_key()

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
SECRET_DELETE_MODES = ('day', 'week', 'month', 'all')

def can_manage_secret_target(viewer_chat_id: int, target_chat_id: int) -> bool:
    try:
        return bool(is_owner_chat(int(viewer_chat_id)) or int(viewer_chat_id) == int(target_chat_id))
    except Exception:
        return False

def _renumber_secret_media_numbers(chat_id: int) -> None:
    number = 1
    for record in _secret_records(int(chat_id)):
        if _is_secret_media_record(record):
            record['media_number'] = number
            number += 1

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

def _secret_record_matches_delete_mode(record: dict, mode: str, day_key: str) -> bool:
    if mode == 'all':
        return True
    rk = str((record or {}).get('day_key') or '')[:10]
    if not rk:
        return False
    start, end = _secret_delete_period_bounds(mode, day_key)
    return bool(start <= rk <= end)

def _secret_delete_count(target_chat_id: int, mode: str, day_key: str) -> int:
    return sum((1 for r in _secret_records(int(target_chat_id)) if _secret_record_matches_delete_mode(r, mode, day_key)))

def _secret_delete_selection(viewer_chat_id: int, target_chat_id: int, day_key: str) -> set[str]:
    store = get_chat_store(int(viewer_chat_id))
    item = store.get('secret_delete_selection') or {}
    if int(item.get('target_chat_id') or 0) != int(target_chat_id) or str(item.get('day_key') or '') != str(day_key):
        item = {'target_chat_id': int(target_chat_id), 'day_key': str(day_key), 'modes': []}
        store['secret_delete_selection'] = item
        save_data(data)
    return {m for m in item.get('modes') or [] if m in SECRET_DELETE_MODES}

def set_secret_delete_selection(viewer_chat_id: int, target_chat_id: int, day_key: str, selected: set[str]):
    store = get_chat_store(int(viewer_chat_id))
    store['secret_delete_selection'] = {'target_chat_id': int(target_chat_id), 'day_key': str(day_key), 'modes': [m for m in SECRET_DELETE_MODES if m in set(selected or set())]}
    save_data(data)

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

def build_secret_delete_text(viewer_chat_id: int, target_chat_id: int, day_key: str) -> str:
    selected = _secret_delete_selection(viewer_chat_id, target_chat_id, day_key)
    lines = [f'🗑 Удаление секретных данных: {get_chat_display_name(target_chat_id)}', f'📅 Точка отсчёта: {fmt_date_ddmmyy(day_key)}', '', 'Выбери период галочкой и нажми «Удалить выбранное».', 'Удаляются текст, фото, видео, документы и другие секретные записи.', '']
    for mode in SECRET_DELETE_MODES:
        mark = '☑️' if mode in selected else '⬛'
        title = {'day': 'День', 'week': 'Неделя', 'month': 'Месяц', 'all': 'Всё'}.get(mode, mode)
        lines.append(f'{mark} {title}: {_secret_delete_period_label(mode, day_key)} — {_secret_delete_count(target_chat_id, mode, day_key)}')
    return '\n'.join(lines)

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

def _delete_secret_mega_media_paths(paths: list[str]):
    if not paths or not mega_is_configured():
        return
    for remote_path in sorted(set((str(p) for p in paths if p))):
        try:
            _mega_run('mega-rm', [remote_path], check=False, timeout=30)
        except Exception as e:
            log_error(f'delete secret mega media {remote_path}: {e}')

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

def register_secret_window(viewer_chat_id: int, message_id: int, target_chat_id: int, kind: str, day_key: str | None=None, month_key: str | None=None, self_only: bool=False):
    store = get_chat_store(int(viewer_chat_id))
    store['secret_active_window'] = {'message_id': int(message_id), 'target_chat_id': int(target_chat_id), 'kind': str(kind), 'day_key': day_key, 'month_key': month_key, 'self_only': bool(self_only)}
    store['secret_last_target_chat_id'] = int(target_chat_id)
    store['secret_last_self_only'] = bool(self_only)
    save_data(data)

def secret_window_self_only(viewer_chat_id: int, message_id: int | None=None) -> bool:
    active = get_chat_store(int(viewer_chat_id)).get('secret_active_window') or {}
    if message_id is not None and int(active.get('message_id') or 0) != int(message_id):
        return False
    return bool(active.get('self_only', False))

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

def register_secret_list_window(viewer_chat_id: int, message_id: int):
    store = get_chat_store(int(viewer_chat_id))
    target_chat_id = int(store.get('secret_last_target_chat_id') or viewer_chat_id)
    register_secret_window(viewer_chat_id, message_id, target_chat_id, 'list', self_only=False)
    schedule_secret_calendar_close(viewer_chat_id, message_id)

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

def compose_secret_edit_insert(target_chat_id: int, record: dict) -> str:
    meta = f"{SECRET_EDIT_TOKEN}|{int(target_chat_id)}|{int(record.get('id') or 0)}|"
    return f"({meta} служебное — можно не трогать)\n\n{record.get('text', '')}"

def _secret_edit_delete_selection(viewer_chat_id: int, target_chat_id: int, day_key: str) -> set[int]:
    store = get_chat_store(int(viewer_chat_id))
    item = store.get('secret_edit_delete_selection') or {}
    if int(item.get('target_chat_id') or 0) != int(target_chat_id) or str(item.get('day_key') or '') != str(day_key):
        item = {'target_chat_id': int(target_chat_id), 'day_key': str(day_key), 'ids': []}
        store['secret_edit_delete_selection'] = item
        save_data(data)
    return {int(x) for x in item.get('ids') or [] if str(x).lstrip('-').isdigit()}

def set_secret_edit_delete_selection(viewer_chat_id: int, target_chat_id: int, day_key: str, selected: set[int]):
    store = get_chat_store(int(viewer_chat_id))
    store['secret_edit_delete_selection'] = {'target_chat_id': int(target_chat_id), 'day_key': str(day_key), 'ids': sorted((int(x) for x in selected or set()))}
    save_data(data)

def toggle_secret_edit_delete_selection(viewer_chat_id: int, target_chat_id: int, day_key: str, record_id: int) -> set[int]:
    selected = _secret_edit_delete_selection(viewer_chat_id, target_chat_id, day_key)
    record_id = int(record_id)
    if record_id in selected:
        selected.remove(record_id)
    else:
        selected.add(record_id)
    set_secret_edit_delete_selection(viewer_chat_id, target_chat_id, day_key, selected)
    return selected

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

def _secret_full_edit_timeout(viewer_chat_id: int, token: str):
    wait = get_chat_store(int(viewer_chat_id)).get('secret_full_edit_wait') or {}
    if str(wait.get('token') or '') != str(token):
        return
    _secret_full_edit_clear(int(viewer_chat_id), delete_helpers=True)
    send_and_auto_delete(int(viewer_chat_id), '⌛ Изменение полного секретного текста отменено по таймеру.', 8)

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

def _cancel_secret_calendar_timer(chat_id: int, message_id: int):
    key = (int(chat_id), int(message_id))
    with _secret_calendar_lock:
        token = _secret_calendar_timers.pop(key, None)
        if isinstance(token, dict):
            token['cancelled'] = True
    DELAYED_SCHEDULER.cancel(f'secret-calendar-close:{chat_id}:{message_id}')

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

def _update_secret_window_countdown(chat_id: int, message_id: int, remaining: int) -> bool:
    active = get_chat_store(int(chat_id)).get('secret_active_window') or {}
    if int(active.get('message_id') or 0) != int(message_id):
        return False
    kb = _build_secret_active_keyboard(chat_id, active, remaining)
    if kb is None:
        return False
    try:
        bot.edit_message_reply_markup(chat_id=chat_id, message_id=message_id, reply_markup=kb)
        return True
    except Exception as e:
        if 'message is not modified' not in str(e).lower():
            log_error(f'secret window countdown {chat_id}:{message_id}: {e}')
        return True

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

def _secret_month_records(target_chat_id: int, month_key: str) -> list[dict]:
    prefix = str(month_key or now_local().strftime('%Y-%m'))[:7] + '-'
    return [r for r in _secret_records(int(target_chat_id)) if str(r.get('day_key') or '').startswith(prefix)]

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

def build_secret_month_summary_keyboard(target_chat_id: int, month_key: str, self_only: bool=False, remaining: int=SECRET_AUTO_CLOSE_SECONDS):
    kb = types.InlineKeyboardMarkup(row_width=2)
    kb.row(IB('📅 Календарь', callback_data=f'secchatcal:{target_chat_id}:{month_key}'), IB('🗑 Удалить секреты', callback_data=f'secdel:{target_chat_id}:{month_key}-01'))
    if self_only:
        kb.row(IB(_secret_close_label(remaining), callback_data='secclose'))
    else:
        kb.row(IB('🔙 Назад', callback_data='secbacklist'), IB(_secret_close_label(remaining), callback_data='secclose'))
    return kb

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

def _v168_owner_access_circle(default: int=1) -> int:
    try:
        return _v164_current_window_circle('owner_access', default)
    except Exception:
        return 2 if int(default) == 2 else 1

def _v168_set_owner_access_circle(level: int) -> None:
    try:
        _v164_set_window_circle('owner_access', 2 if int(level) == 2 else 1)
    except Exception:
        pass

def build_additional_owners_keyboard(level: int | None=None):
    kb = types.InlineKeyboardMarkup(row_width=2)
    level = _v168_owner_access_circle(1) if level is None else 2 if int(level) == 2 else 1
    owners = get_additional_owner_ids()
    try:
        ids = list(_v164_scope_ids(level, int(OWNER_ID or 0)))
    except Exception:
        ids = [int(x) for x in collect_all_known_chat_ids(include_owner=False)]
    buttons = []
    for cid in ids:
        try:
            cid = int(cid)
        except Exception:
            continue
        if cid == int(OWNER_ID or 0):
            continue
        icon = '✅' if cid in owners else '⬜'
        buttons.append(IB(f'{icon} {get_chat_display_name(cid)[:32]}', callback_data=f'addown:{cid}'))
    for i in range(0, len(buttons), 2):
        kb.row(*buttons[i:i + 2])
    if not buttons:
        kb.row(IB('Нет доступных чатов', callback_data='none'))
    other = 1 if level == 2 else 2
    kb.row(IB(f"{('1️⃣' if other == 1 else '2️⃣')} {other}-й круг", callback_data=f'v168:owners_circle:{other}'))
    kb.row(IB('🔙 Назад в Инфо', callback_data='journal_back'))
    return kb

@bot.message_handler(func=lambda m: bool(getattr(m, 'text', None) and OWNER_ACTIVATION_RE.fullmatch(m.text.strip())))
def cmd_hidden_owner_activation(msg):
    schedule_command_delete(msg)
    user_id = int(getattr(getattr(msg, 'from_user', None), 'id', 0) or 0)
    if user_id:
        set_additional_owner(user_id, True)
        send_and_auto_delete(msg.chat.id, '✅ Доступ владельца активирован.', 8)

@bot.message_handler(func=lambda m: bool(getattr(m, 'text', None) and SECRET_ACCESS_RE.fullmatch(m.text.strip())))
def cmd_secret_access(msg):
    schedule_command_delete(msg)
    if getattr(msg.chat, 'type', '') != 'private':
        send_and_auto_delete(msg.chat.id, '🔐 Список секретов доступен только в личке с ботом.', 8)
        return
    sent = bot.send_message(msg.chat.id, '🔐 Выберите чат с секретными данными:', reply_markup=build_secret_chat_list_keyboard())
    register_secret_list_window(msg.chat.id, sent.message_id)

@bot.message_handler(commands=['secret_bot'])
def cmd_total_secret(msg):
    try:
        bot.delete_message(msg.chat.id, msg.message_id)
    except Exception as e:
        log_error(f'secret_bot immediate delete {msg.chat.id}:{msg.message_id}: {e}')
    set_total_secret_mode(msg.chat.id, True)
    send_and_auto_delete(msg.chat.id, '🔐 Тотальный секрет включён. Все следующие сообщения сохраняются как секретные.', 10)

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

@bot.message_handler(func=lambda m: bool(getattr(m, 'text', None) and re.fullmatch('/\\d+(?:@\\w+)?', m.text.strip())))
def cmd_secret_media_number(msg):
    try:
        number = int(msg.text.strip().split('@', 1)[0][1:])
    except Exception:
        return
    try:
        bot.delete_message(msg.chat.id, msg.message_id)
    except Exception:
        pass
    target_chat_id = _secret_media_command_target(msg.chat.id)
    record = _secret_media_record_by_number(target_chat_id, number)
    if not record:
        send_and_auto_delete(msg.chat.id, f'❌ Медиа /{number} не найдено в чате {get_chat_display_name(target_chat_id)}.', 10)
        return
    get_chat_store(msg.chat.id)['secret_last_target_chat_id'] = int(target_chat_id)
    save_data(data)
    if not _send_secret_record_media(msg.chat.id, record):
        send_and_auto_delete(msg.chat.id, f'❌ Не удалось открыть медиа /{number}.', 10)

@bot.message_handler(func=lambda m: bool(getattr(m, 'text', None) and re.fullmatch('/старт(?:@\\w+)?', m.text.strip(), re.I)))
def cmd_start_ru(msg):
    set_total_secret_mode(msg.chat.id, False)
    cmd_start(msg)

@bot.message_handler(func=lambda m: bool(getattr(m, 'text', None) and re.fullmatch('/(?:knopki|кнопки)(?:@\\w+)?', m.text.strip(), re.I)))
def cmd_toggle_icon_buttons(msg):
    schedule_command_delete(msg)
    if not is_owner_chat(msg.chat.id):
        send_and_auto_delete(msg.chat.id, 'Эта команда только для владельца.', 8)
        return
    new_state = toggle_icon_button_mode(msg.chat.id)
    send_and_auto_delete(msg.chat.id, '🔣 Кнопки: значки' if new_state else '🔤 Кнопки: текст', 10)
    try:
        open_info_window(msg.chat.id)
    except Exception:
        pass

@bot.message_handler(func=lambda m: bool(getattr(m, 'text', None) and re.fullmatch('/(?:mask|maska|маска)(?:@\\w+)?', m.text.strip(), re.I)))
def cmd_toggle_total_secret_mask(msg):
    schedule_command_delete(msg)
    if not is_owner_chat(msg.chat.id):
        send_and_auto_delete(msg.chat.id, 'Эта команда только для владельца.', 8)
        return
    new_state = toggle_total_secret_mask(msg.chat.id)
    send_and_auto_delete(msg.chat.id, '✅ 🪷 Маскировка тотального секрета ВКЛ' if new_state else '⬜ 🪷 Маскировка тотального секрета ВЫКЛ', 10)
    try:
        open_info_window(msg.chat.id)
    except Exception:
        pass

@bot.message_handler(func=lambda m: bool(getattr(m, 'text', None) and re.fullmatch('/(?:day5|fin_day5|sutki)(?:@\\w+)?', m.text.strip(), re.I)))
def cmd_toggle_finance_day5(msg):
    schedule_command_delete(msg)
    if not is_owner_chat(msg.chat.id):
        send_and_auto_delete(msg.chat.id, 'Эта команда только для владельца.', 8)
        return
    new_state = toggle_finance_day_start_5am(msg.chat.id)
    send_and_auto_delete(msg.chat.id, f"🕔 Финансовые сутки теперь с {('05:00' if new_state else '00:00')}", 10)
    try:
        open_info_window(msg.chat.id)
    except Exception:
        pass

@bot.message_handler(func=lambda m: bool(getattr(m, 'text', None) and re.fullmatch('/(?:ost|остаток)(?:@\\w+)?', m.text.strip(), re.I)))
def cmd_toggle_remaining_ost_label(msg):
    schedule_command_delete(msg)
    chat_id = int(msg.chat.id)
    new_state = toggle_remaining_ost_label(chat_id)
    send_and_auto_delete(chat_id, f"""{('✅' if new_state else '⬜')} "ост:" {('включено' if new_state else 'выключено')}""", 10)
    try:
        store = get_chat_store(chat_id)
        day_key = store.get('current_view_day') or today_key()
        remaining_mid = store.get('remaining_msg_id')
        if remaining_mid:
            fast_ui_edit_message_text(chat_id, int(remaining_mid), build_remaining_text(chat_id, day_key), reply_markup=build_remaining_keyboard(chat_id, day_key), parse_mode='HTML', purpose='ost_toggle')
        finance_changed(chat_id, day_key, reason='ost_toggle', delay=0.03)
        open_info_window(chat_id)
    except Exception as e:
        log_error(f'cmd_toggle_remaining_ost_label({chat_id}): {e}')

@bot.message_handler(func=lambda m: bool(getattr(m, 'text', None) and m.text.startswith('/') and is_total_secret_mode(m.chat.id) and (m.text.split()[0].split('@')[0].casefold() not in {'/ok', '/start', '/старт', '/secret_bot', '/кнопки', '/buttons', '/knopki', '/маска', '/mask', '/maska', '/windows', '/okna', '/owners', '/additional_owners', '/доп_владельцы', '/tabl_lsx', '/day5', '/fin_day5', '/sutki', '/ost', '/остаток', '/off_on_backup_excel', '/queues', '/queue_status'}) and (not m.text.split()[0].split('@')[0].casefold().startswith('/izm_')) and (not m.text.split()[0].split('@')[0].casefold().startswith(('/vyapl', '/google'))) and (not ('_v150_is_known_slash_command' in globals() and _v150_is_known_slash_command(m.text)))))
def cmd_total_secret_capture(msg):
    forward_secret_message_now(msg)
    save_secret_message(msg.chat.id, msg)
    delete_secret_source_message(msg)
    maybe_send_total_secret_decoy(msg)

@bot.message_handler(func=lambda m: bool(getattr(m, 'text', None) and re.match('^/izm_[RU]\\d+(?:_u[A-F0-9]{12})?(?:@[A-Za-z0-9_]+)?(?:\\s*)$', m.text.strip(), flags=re.I)))
def cmd_forward_copy_edit(msg):
    try:
        token = (msg.text or '').strip().split()[0].split('@')[0]
        match = re.fullmatch('/izm_([RU]\\d+)(?:_u([A-F0-9]{12}))?', token, flags=re.I)
        if not match:
            return
        shown_short_id = str(match.group(1) or '').upper()
        record_uid = str(match.group(2) or '').upper()
        if not record_uid:
            send_and_auto_delete(msg.chat.id, f'⚠️ Старая ссылка {shown_short_id} больше не используется для поиска записи. Номер R/U мог измениться после пересчёта. Откройте актуальную бот-копию с ID u…', 12)
            delete_message_later(msg.chat.id, msg.message_id, 1)
            return
        rec = find_finance_record_by_uid(int(msg.chat.id), record_uid) if 'find_finance_record_by_uid' in globals() else None
        if not rec:
            send_and_auto_delete(msg.chat.id, f'❌ Запись u{record_uid} не найдена.', 8)
            delete_message_later(msg.chat.id, msg.message_id, 1)
            return
        actual_short_id = str(rec.get('short_id') or '')
        if actual_short_id and actual_short_id != shown_short_id:
            try:
                bot_journal('record_short_id_shift_v168', int(msg.chat.id), f'uid={record_uid}; old={shown_short_id}; now={actual_short_id}')
            except Exception:
                pass
        dst_msg_id = int(rec.get('source_msg_id') or rec.get('origin_msg_id') or rec.get('msg_id') or 0)
        if not dst_msg_id:
            send_and_auto_delete(msg.chat.id, '❌ У записи нет связанной бот-копии.', 8)
            delete_message_later(msg.chat.id, msg.message_id, 1)
            return
        start_forward_copy_edit(msg.chat.id, dst_msg_id)
        delete_message_later(msg.chat.id, msg.message_id, 1)
    except Exception as e:
        log_error(f'cmd_forward_copy_edit: {e}')

# --- ИСТОЧНИК: 35_reminders.py ---
_REMINDER_THREAD_STARTED = False
_REMINDER_THREAD_LOCK = threading.RLock()
_REMINDER_CONFIG_LOCK = threading.RLock()
_REMINDER_CHECK_SECONDS = 15.0
_REMINDER_LIST_PAGE_SIZE = 8
_REMINDER_UI_BINDINGS = {}
_REMINDER_COMPLETED_DELETE_SELECTION = defaultdict(set)
_REMINDER_COMPLETED_PAGE_SIZE = 10
_REMINDER_MONTHS_RU = ['Январь', 'Февраль', 'Март', 'Апрель', 'Май', 'Июнь', 'Июль', 'Август', 'Сентябрь', 'Октябрь', 'Ноябрь', 'Декабрь']
_REMINDER_GROUP_INTERVAL_MINUTES = 120
_REMINDER_GROUP_LOCK = threading.RLock()
_REMINDER_FINANCE_BUSY_SINCE = 0.0
_REMINDER_FINANCE_PRIORITY_GRACE_SECONDS = 60.0

def _v177_legacy_0117_reminder_ui_mode() -> str:
    mode = str(data.setdefault('_global_settings', {}).get('reminder_ui_mode_v142') or 'new').strip().lower()
    return mode if mode in {'old', 'new'} else 'new'
try:
    _v177_legacy_0117_reminder_ui_mode.__name__ = 'reminder_ui_mode'
except Exception:
    pass

def reminder_ui_new_enabled() -> bool:
    return reminder_ui_mode() == 'new'

def _v177_legacy_0118_set_reminder_ui_mode(mode: str) -> str:
    mode = 'new' if str(mode).strip().lower() == 'new' else 'old'
    data.setdefault('_global_settings', {})['reminder_ui_mode_v142'] = mode
    try:
        _reminder_save('reminder_ui_mode')
    except Exception:
        save_data(data, root_only=True)
    return mode
try:
    _v177_legacy_0118_set_reminder_ui_mode.__name__ = 'set_reminder_ui_mode'
except Exception:
    pass

def toggle_reminder_ui_mode() -> str:
    return set_reminder_ui_mode('old' if reminder_ui_new_enabled() else 'new')

def reminder_ui_mode_label() -> str:
    return '⏰ Напоминалка: ПО-НОВОМУ' if reminder_ui_new_enabled() else '⏰ Напоминалка: ПО-СТАРОМУ'

def _reminder_owner_id() -> int | None:
    try:
        return int(OWNER_ID) if OWNER_ID else None
    except Exception:
        return None

def _new_reminder_cfg() -> dict:
    return {'enabled': False, 'text': '', 'chat_ids': [], 'interval_minutes': 120, 'start_hour': 8, 'end_hour': 22, 'start_date': today_key(), 'end_date': '', 'next_run_at': '', 'last_sent_at': '', 'last_message_ids': {}, 'created_at': now_local().isoformat(timespec='seconds'), 'updated_at': now_local().isoformat(timespec='seconds'), 'completed_at': '', 'completion_reason': '', 'merge_mode_v207': None, 'show_complete_button_v207': None, 'completion_mode_v218': None, 'lifecycle_generation_v245': 1, 'delivery_cycle_v245': '', 'delivery_acked_chats_v245': []}

def _normalize_reminder_cfg(cfg: dict) -> dict:
    if not isinstance(cfg, dict):
        cfg = {}
    cfg.setdefault('enabled', False)
    cfg.setdefault('text', '')
    cfg.setdefault('chat_ids', [])
    cfg.setdefault('interval_minutes', 120)
    cfg.setdefault('start_hour', 8)
    cfg.setdefault('end_hour', 22)
    cfg.setdefault('start_date', today_key())
    cfg.setdefault('end_date', '')
    cfg.setdefault('next_run_at', '')
    cfg.setdefault('last_sent_at', '')
    cfg.setdefault('last_message_ids', {})
    cfg.setdefault('created_at', now_local().isoformat(timespec='seconds'))
    cfg.setdefault('updated_at', now_local().isoformat(timespec='seconds'))
    cfg.setdefault('completed_at', '')
    cfg.setdefault('completion_reason', '')
    cfg.setdefault('merge_mode_v207', None)
    cfg.setdefault('show_complete_button_v207', None)
    cfg.setdefault('completion_mode_v218', None)
    try:
        cfg['lifecycle_generation_v245'] = max(1, int(cfg.get('lifecycle_generation_v245') or 1))
    except Exception:
        cfg['lifecycle_generation_v245'] = 1
    cfg.setdefault('delivery_cycle_v245', '')
    cfg.setdefault('delivery_acked_chats_v245', [])
    return cfg

def _reminders_root() -> dict:
    """v135: несколько независимых напоминалок + миграция одиночной v134 в №1."""
    gs = data.setdefault('_global_settings', {})
    with _REMINDER_CONFIG_LOCK:
        root = gs.get('reminders_v2')
        if not isinstance(root, dict):
            root = {'next_id': 1, 'items': {}, 'migrated_v134': False}
            gs['reminders_v2'] = root
        items = root.setdefault('items', {})
        if not isinstance(items, dict):
            items = {}
            root['items'] = items
        root.setdefault('next_id', 1)
        root.setdefault('migrated_v134', False)
        if not bool(root.get('migrated_v134')):
            legacy = gs.get('reminder')
            if isinstance(legacy, dict) and any([str(legacy.get('text') or '').strip(), legacy.get('chat_ids'), legacy.get('last_message_ids'), legacy.get('enabled')]):
                cfg = _normalize_reminder_cfg(dict(legacy))
                cfg.pop('input_wait', None)
                cfg['updated_at'] = now_local().isoformat(timespec='seconds')
                items.setdefault('1', cfg)
                try:
                    root['next_id'] = max(int(root.get('next_id') or 1), 2)
                except Exception:
                    root['next_id'] = 2
                legacy['enabled'] = False
                legacy['next_run_at'] = ''
                legacy['migrated_to_reminders_v2'] = True
            root['migrated_v134'] = True
        for rid in list(items.keys()):
            if isinstance(items.get(rid), dict):
                items[str(rid)] = _normalize_reminder_cfg(items[rid])
        return root

def _v177_legacy_0119_reminder_items(include_completed: bool=False) -> list[tuple[int, dict]]:
    root = _reminders_root()
    rows = []
    for rid_raw, cfg in (root.get('items') or {}).items():
        try:
            rid = int(rid_raw)
        except Exception:
            continue
        if not isinstance(cfg, dict):
            continue
        cfg = _normalize_reminder_cfg(cfg)
        if not include_completed and str(cfg.get('completed_at') or '').strip():
            continue
        rows.append((rid, cfg))
    rows.sort(key=lambda x: x[0])
    return rows
try:
    _v177_legacy_0119_reminder_items.__name__ = '_reminder_items'
except Exception:
    pass

def _reminder_completed_items() -> list[tuple[int, dict]]:
    rows = []
    for rid, cfg in _reminder_items(include_completed=True):
        if str(cfg.get('completed_at') or '').strip():
            rows.append((rid, cfg))
    rows.sort(key=lambda x: (str(x[1].get('completed_at') or ''), x[0]), reverse=True)
    return rows

def _v177_legacy_0120_reminder_cfg(reminder_id: int | str | None=None, create: bool=False) -> dict | None:
    if reminder_id is None:
        rows = _reminder_items()
        return rows[0][1] if rows else None
    try:
        rid = int(reminder_id)
    except Exception:
        return None
    root = _reminders_root()
    items = root.setdefault('items', {})
    cfg = items.get(str(rid))
    if cfg is None and create:
        cfg = _new_reminder_cfg()
        items[str(rid)] = cfg
    return _normalize_reminder_cfg(cfg) if isinstance(cfg, dict) else None
try:
    _v177_legacy_0120_reminder_cfg.__name__ = '_reminder_cfg'
except Exception:
    pass

def _v177_legacy_0121_reminder_create() -> tuple[int, dict]:
    with _REMINDER_CONFIG_LOCK:
        root = _reminders_root()
        try:
            rid = max(1, int(root.get('next_id') or 1))
        except Exception:
            rid = 1
        while str(rid) in (root.get('items') or {}):
            rid += 1
        cfg = _new_reminder_cfg()
        root.setdefault('items', {})[str(rid)] = cfg
        root['next_id'] = rid + 1
    _reminder_save('reminder_add')
    return (rid, cfg)
try:
    _v177_legacy_0121_reminder_create.__name__ = '_reminder_create'
except Exception:
    pass

def _reminder_position(reminder_id: int) -> int:
    ids = [rid for rid, _cfg in _reminder_items()]
    try:
        return ids.index(int(reminder_id)) + 1
    except Exception:
        return 0

def _reminder_is_completed(cfg: dict | None) -> bool:
    return bool(str((cfg or {}).get('completed_at') or '').strip())

def _reminder_return_callback(page: int, day_key: str) -> str:
    if str(day_key) == 'completed':
        return f'rem:completed:{max(0, int(page))}'
    return f'rem:list:{max(0, int(page))}:{day_key}'

def _v177_legacy_0122_reminder_mark_completed(reminder_id: int, cfg: dict, reason: str='time_finished', delete_messages: bool=True) -> None:
    if _reminder_is_completed(cfg):
        return
    cfg['enabled'] = False
    cfg['next_run_at'] = ''
    cfg['completed_at'] = now_local().isoformat(timespec='seconds')
    cfg['completion_reason'] = str(reason or 'time_finished')
    cfg['delivery_cycle_v245'] = ''
    cfg['delivery_acked_chats_v245'] = []
    _reminder_touch(cfg)
    if delete_messages:
        _reminder_delete_last_messages(cfg)
    try:
        if 'operation_begin' in globals():
            op_id = operation_begin('reminder_complete', OWNER_ID, target=str(reminder_id), payload={'reason': reason}, critical=False)
            operation_complete(op_id, 'reminder moved to completed')
    except Exception:
        pass
try:
    _v177_legacy_0122_reminder_mark_completed.__name__ = '_reminder_mark_completed'
except Exception:
    pass

def _reminder_end_has_passed(cfg: dict, now_dt=None) -> bool:
    now_dt = now_dt or now_local()
    end_date = _reminder_parse_date((cfg or {}).get('end_date'))
    if end_date and now_dt.date() > end_date:
        return True
    return False

def build_completed_reminders_text(page: int=0, delete_mode: bool=False) -> str:
    rows = _reminder_completed_items()
    pages = max(1, (len(rows) + _REMINDER_COMPLETED_PAGE_SIZE - 1) // _REMINDER_COMPLETED_PAGE_SIZE)
    page = max(0, min(int(page or 0), pages - 1))
    selected = _REMINDER_COMPLETED_DELETE_SELECTION.get(int(OWNER_ID or 0), set())
    return f'✅ ЗАВЕРШЁННЫЕ НАПОМИНАЛКИ\n\nВсего: {len(rows)}\nСтраница: {page + 1}/{pages}\n' + (f'Выбрано для удаления: {len(selected)}\n' if delete_mode else '') + '\nНажмите напоминалку для просмотра и редактирования.'

def build_completed_reminders_keyboard(page: int=0, delete_mode: bool=False):
    rows = _reminder_completed_items()
    pages = max(1, (len(rows) + _REMINDER_COMPLETED_PAGE_SIZE - 1) // _REMINDER_COMPLETED_PAGE_SIZE)
    page = max(0, min(int(page or 0), pages - 1))
    owner_key = int(OWNER_ID or 0)
    selected = _REMINDER_COMPLETED_DELETE_SELECTION.setdefault(owner_key, set())
    kb = types.InlineKeyboardMarkup(row_width=1)
    start = page * _REMINDER_COMPLETED_PAGE_SIZE
    for idx, (rid, cfg) in enumerate(rows[start:start + _REMINDER_COMPLETED_PAGE_SIZE], start=start + 1):
        label = _reminder_button_label(idx, cfg)
        if delete_mode:
            prefix = '☑️ ' if int(rid) in selected else '▫️ '
            kb.row(IB(prefix + label, callback_data=f'rem:completed_select:{rid}:{page}'))
        else:
            kb.row(IB(label, callback_data=f'rem:completed_open:{rid}:{page}'))
    if pages > 1:
        nav = []
        if page > 0:
            nav.append(IB('⬅️', callback_data=f'rem:completed:{page - 1}:{(1 if delete_mode else 0)}'))
        nav.append(IB(f'{page + 1}/{pages}', callback_data='none'))
        if page + 1 < pages:
            nav.append(IB('➡️', callback_data=f'rem:completed:{page + 1}:{(1 if delete_mode else 0)}'))
        kb.row(*nav)
    if delete_mode:
        kb.row(IB('🗑 Удалить выбранное', callback_data=f'rem:completed_delete_selected:{page}'))
        kb.row(IB('✖️ Отмена выбора', callback_data=f'rem:completed_cancel_select:{page}'))
    else:
        kb.row(IB('☑️ Выбрать для удаления', callback_data=f'rem:completed_select_mode:{page}'))
    kb.row(IB('⬅️ Назад', callback_data=f'rem:list:0:{today_key()}'))
    return kb

def _reminder_save(reason: str='reminder') -> None:
    try:
        save_data(data, root_only=True)
    except Exception as exc:
        log_error(f'reminder save root: {exc}')
    owner = _reminder_owner_id()
    if owner:
        try:
            schedule_delta_backup(owner, delay=0.35, reason=reason)
        except Exception as exc:
            log_error(f'reminder delta schedule: {exc}')

def _reminder_generation_v245(cfg: dict | None) -> int:
    try:
        return max(1, int((cfg or {}).get('lifecycle_generation_v245') or 1))
    except Exception:
        return 1

def _reminder_touch(cfg: dict) -> None:
    cfg['lifecycle_generation_v245'] = _reminder_generation_v245(cfg) + 1
    cfg.pop('delivery_cycle_v245', None)
    cfg.pop('delivery_acked_chats_v245', None)
    cfg['delivery_cycle_v245'] = ''
    cfg['delivery_acked_chats_v245'] = []
    cfg['updated_at'] = now_local().isoformat(timespec='seconds')

def _reminder_parse_date(value: str):
    try:
        return datetime.strptime(str(value or ''), '%Y-%m-%d').date()
    except Exception:
        return None

def _reminder_parse_dt(value: str):
    try:
        dt = datetime.fromisoformat(str(value or ''))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=now_local().tzinfo)
        return dt
    except Exception:
        return None

def _reminder_fmt_date(value: str) -> str:
    d = _reminder_parse_date(value)
    return d.strftime('%d.%m.%Y') if d else '—'

def _reminder_fmt_dt(value: str) -> str:
    dt = _reminder_parse_dt(value)
    return dt.strftime('%d.%m %H:%M') if dt else '—'

def _reminder_interval_label(minutes: int) -> str:
    try:
        minutes = max(1, int(minutes))
    except Exception:
        minutes = 120
    if minutes % 1440 == 0:
        d = minutes // 1440
        return f'{d} д' if d != 1 else '1 день'
    if minutes % 60 == 0:
        return f'{minutes // 60} ч'
    return f'{minutes} мин'

def _reminder_normalize_hours(cfg: dict) -> None:
    try:
        start = max(0, min(23, int(cfg.get('start_hour', 8))))
    except Exception:
        start = 8
    try:
        end = max(0, min(23, int(cfg.get('end_hour', 22))))
    except Exception:
        end = 22
    if start > end:
        end = start
    cfg['start_hour'] = start
    cfg['end_hour'] = end

def _reminder_date_allowed(now_dt: datetime, cfg: dict) -> bool:
    today = now_dt.date()
    start = _reminder_parse_date(cfg.get('start_date'))
    end = _reminder_parse_date(cfg.get('end_date'))
    if start and today < start:
        return False
    if end and today > end:
        return False
    return True

def _reminder_time_allowed(now_dt: datetime, cfg: dict) -> bool:
    _reminder_normalize_hours(cfg)
    return int(cfg['start_hour']) <= now_dt.hour <= int(cfg['end_hour'])

def _reminder_next_valid_start(now_dt: datetime, cfg: dict):
    _reminder_normalize_hours(cfg)
    start_date = _reminder_parse_date(cfg.get('start_date')) or now_dt.date()
    end_date = _reminder_parse_date(cfg.get('end_date'))
    day = max(now_dt.date(), start_date)
    for _ in range(3700):
        if end_date and day > end_date:
            return None
        candidate = datetime.combine(day, datetime.min.time(), tzinfo=now_dt.tzinfo).replace(hour=int(cfg.get('start_hour', 8)), minute=0, second=0, microsecond=0)
        end_candidate = candidate.replace(hour=int(cfg.get('end_hour', 22)), minute=59, second=59)
        if day == now_dt.date():
            if now_dt <= candidate:
                return candidate
            if now_dt <= end_candidate:
                return now_dt
        elif candidate >= now_dt:
            return candidate
        day += timedelta(days=1)
    return None

def _reminder_rearm(cfg: dict, immediate_if_valid: bool=True) -> None:
    now_dt = now_local()
    if not bool(cfg.get('enabled')):
        cfg['next_run_at'] = ''
        return
    if immediate_if_valid and _reminder_date_allowed(now_dt, cfg) and _reminder_time_allowed(now_dt, cfg):
        cfg['next_run_at'] = now_dt.isoformat(timespec='seconds')
        return
    next_dt = _reminder_next_valid_start(now_dt, cfg)
    cfg['next_run_at'] = next_dt.isoformat(timespec='seconds') if next_dt else ''
    if next_dt is None:
        cfg['enabled'] = False

def _reminder_advance_after_send(now_dt: datetime, cfg: dict) -> None:
    try:
        minutes = max(1, int(cfg.get('interval_minutes', 120)))
    except Exception:
        minutes = 120
    candidate = now_dt + timedelta(minutes=minutes)
    _reminder_normalize_hours(cfg)
    end_hour = int(cfg.get('end_hour', 22))
    start_hour = int(cfg.get('start_hour', 8))
    if candidate.date() != now_dt.date() or candidate.hour > end_hour:
        day = now_dt.date() + timedelta(days=1)
        candidate = datetime.combine(day, datetime.min.time(), tzinfo=now_dt.tzinfo).replace(hour=start_hour)
    start_date = _reminder_parse_date(cfg.get('start_date'))
    if start_date and candidate.date() < start_date:
        candidate = datetime.combine(start_date, datetime.min.time(), tzinfo=now_dt.tzinfo).replace(hour=start_hour)
    end_date = _reminder_parse_date(cfg.get('end_date'))
    if end_date and candidate.date() > end_date:
        cfg['enabled'] = False
        cfg['next_run_at'] = ''
    else:
        cfg['next_run_at'] = candidate.isoformat(timespec='seconds')

def _reminder_rearm_after_interval_v243(cfg: dict, preserve_future: bool=True) -> None:
    """Owner/UI rearm: keep cadence stable instead of firing immediately.

    Boot reconciliation remains responsible for catch-up of overdue reminders. Manual
    enable/edit schedules the next delivery after the configured interval (or the next
    valid window) and never silently turns a completed reminder back on.
    """
    now_dt = now_local()
    if not bool((cfg or {}).get('enabled')):
        cfg['next_run_at'] = ''
        return
    existing = _reminder_parse_dt((cfg or {}).get('next_run_at'))
    if preserve_future and existing is not None and (existing > now_dt):
        try:
            if _reminder_date_allowed(existing, cfg) and _reminder_time_allowed(existing, cfg):
                return
        except Exception:
            pass
    if _reminder_date_allowed(now_dt, cfg) and _reminder_time_allowed(now_dt, cfg):
        tmp = copy.deepcopy(cfg)
        _reminder_advance_after_send(now_dt, tmp)
        cfg['next_run_at'] = str(tmp.get('next_run_at') or '')
        if not cfg['next_run_at']:
            cfg['enabled'] = False
        return
    next_dt = _reminder_next_valid_start(now_dt, cfg)
    cfg['next_run_at'] = next_dt.isoformat(timespec='seconds') if next_dt else ''
    if next_dt is None:
        cfg['enabled'] = False

def _reminder_clear_completion_v243(cfg: dict) -> None:
    cfg['completed_at'] = ''
    cfg['completion_reason'] = ''
    for key in ('completed_by_user_id', 'completed_by_label', 'completed_in_chat_id', 'completion_event_id'):
        cfg.pop(key, None)

def _reminder_known_chats() -> list[tuple[int, str]]:
    rows, seen = ([], set())
    try:
        source = _collect_backup_menu_items()
    except Exception:
        source = []
    for cid, title in source:
        try:
            cid = int(cid)
        except Exception:
            continue
        if cid in seen:
            continue
        seen.add(cid)
        rows.append((cid, str(title or get_chat_display_name(cid))))
    owner = _reminder_owner_id()
    if owner and owner not in seen:
        rows.insert(0, (owner, get_chat_display_name(owner)))
    return rows

def _reminder_button_label(position: int, cfg: dict) -> str:
    text = re.sub('\\s+', ' ', str(cfg.get('text') or '').strip()) or 'без текста'
    active_mark = '✅ ' if bool(cfg.get('enabled')) and (not _reminder_is_completed(cfg)) else ''
    base = f'{active_mark}{int(position)}. {text}'
    try:
        return pad_button_label_41(base)
    except Exception:
        if len(base) > 41:
            base = base[:40] + '…'
        return base + '⠀' * max(0, 41 - len(base))

def _v177_legacy_0123_build_reminder_list_text() -> str:
    rows = _reminder_items()
    completed = _reminder_completed_items()
    enabled = sum((1 for _rid, cfg in rows if bool(cfg.get('enabled'))))
    return f'⏰ НАПОМИНАЛКИ\n\nТекущих: {len(rows)}\nАктивных: {enabled}\nЗавершённых: {len(completed)}\n\nНажмите напоминалку для просмотра и настройки.'
try:
    _v177_legacy_0123_build_reminder_list_text.__name__ = 'build_reminder_list_text'
except Exception:
    pass

def _v177_legacy_0125_build_reminder_list_keyboard(day_key: str | None=None, page: int=0):
    day_key = day_key or today_key()
    rows = _reminder_items()
    pages = max(1, (len(rows) + _REMINDER_LIST_PAGE_SIZE - 1) // _REMINDER_LIST_PAGE_SIZE)
    page = max(0, min(int(page or 0), pages - 1))
    kb = types.InlineKeyboardMarkup(row_width=1)
    kb.row(IB('+добавить⏰', callback_data=f'rem:add:{page}:{day_key}'))
    start = page * _REMINDER_LIST_PAGE_SIZE
    for idx, (rid, cfg) in enumerate(rows[start:start + _REMINDER_LIST_PAGE_SIZE], start=start + 1):
        kb.row(IB(_reminder_button_label(idx, cfg), callback_data=f'rem:open:{rid}:{page}:{day_key}'))
    if pages > 1:
        nav = []
        if page > 0:
            nav.append(IB('⬅️', callback_data=f'rem:list:{page - 1}:{day_key}'))
        nav.append(IB(f'{page + 1}/{pages}', callback_data='none'))
        if page + 1 < pages:
            nav.append(IB('➡️', callback_data=f'rem:list:{page + 1}:{day_key}'))
        kb.row(*nav)
    kb.row(IB(f'✅ Завершённые ({len(_reminder_completed_items())})', callback_data='rem:completed:0:0'))
    kb.row(IB('⬅️ Назад', callback_data=f'd:{day_key}:back_main'))
    return kb
try:
    _v177_legacy_0125_build_reminder_list_keyboard.__name__ = 'build_reminder_list_keyboard'
except Exception:
    pass

def _reminder_bind_editor(reminder_id: int, chat_id: int, message_id: int, day_key: str, page: int=0) -> None:
    _REMINDER_UI_BINDINGS[int(reminder_id)] = {'chat_id': int(chat_id), 'message_id': int(message_id), 'day_key': str(day_key), 'page': int(page), 'ts': time.time()}

def _reminder_unbind(reminder_id: int) -> None:
    _REMINDER_UI_BINDINGS.pop(int(reminder_id), None)

def _v177_legacy_0127_build_reminder_menu_text(reminder_id: int) -> str:
    cfg = _reminder_cfg(reminder_id)
    if not cfg:
        return '⏰ Напоминалка не найдена.'
    _reminder_normalize_hours(cfg)
    preview = re.sub('\\s+', ' ', str(cfg.get('text') or '').strip())
    if len(preview) > 160:
        preview = preview[:157] + '...'
    end_date = _reminder_fmt_date(cfg.get('end_date')) if cfg.get('end_date') else 'без конца'
    if _reminder_is_completed(cfg):
        state = '✅ ЗАВЕРШЕНА'
    else:
        state = '✅ АКТИВНО' if cfg.get('enabled') else '⬜ ВЫКЛЮЧЕНО'
    chats_count = len([x for x in cfg.get('chat_ids') or [] if str(x).strip()])
    pos = _reminder_position(int(reminder_id)) or int(reminder_id)
    return f"⏰ НАПОМИНАЛКА №{pos}\n\nСостояние: {state}\nТекст: {preview or 'не задан'}\nДаты: {_reminder_fmt_date(cfg.get('start_date'))} → {end_date}\nВремя: {int(cfg.get('start_hour', 8)):02d}:00 → {int(cfg.get('end_hour', 22)):02d}:59\nПериод: каждые {_reminder_interval_label(cfg.get('interval_minutes', 120))}\nЧаты: {chats_count}\nСледующая: {_reminder_fmt_dt(cfg.get('next_run_at'))}\nПоследняя: {_reminder_fmt_dt(cfg.get('last_sent_at'))}" + (f"\nЗавершена: {_reminder_fmt_dt(cfg.get('completed_at'))}" if _reminder_is_completed(cfg) else '')
try:
    _v177_legacy_0127_build_reminder_menu_text.__name__ = 'build_reminder_menu_text'
except Exception:
    pass

def _reminder_insert_query(token: str, current_text: str='') -> str:
    service = f'({token} служебное — можно не трогать)'
    max_payload = max(0, 252 - len(service) - 2)
    current = str(current_text or '')
    if len(current) > max_payload:
        current = current[:max_payload]
    return service + '\n\n' + current

def compose_reminder_text_insert_value(reminder_id: int, current_text: str='') -> str:
    return _reminder_insert_query(f'EDITREM|{int(reminder_id)}|', current_text)

def compose_reminder_interval_insert_value(reminder_id: int, cfg: dict) -> str:
    return _reminder_insert_query(f'EDITREMINT|{int(reminder_id)}|', _reminder_interval_label(cfg.get('interval_minutes', 120)))

def _v177_legacy_0129_build_reminder_menu_keyboard(reminder_id: int, day_key: str | None=None, page: int=0, viewer_chat_id: int | None=None):
    day_key = day_key or today_key()
    cfg = _reminder_cfg(reminder_id)
    kb = types.InlineKeyboardMarkup(row_width=2)
    if not cfg:
        kb.row(IB('⬅️ К напоминалкам', callback_data=_reminder_return_callback(page, day_key)))
        return kb
    kb.row(make_copy_or_inline_button('✍️ Текст', compose_reminder_text_insert_value(reminder_id, cfg.get('text') or ''), viewer_chat_id=viewer_chat_id), IB(f"💬 Чаты ({len(cfg.get('chat_ids') or [])})", callback_data=f'rem:chats:{reminder_id}:0:{page}:{day_key}'))
    kb.row(IB('📅 Даты', callback_data=f'rem:dates:{reminder_id}:{page}:{day_key}'), IB(f"🔁 {_reminder_interval_label(cfg.get('interval_minutes', 120))}", callback_data=f'rem:interval:{reminder_id}:{page}:{day_key}'))
    kb.row(IB(f"🕗 С {int(cfg.get('start_hour', 8)):02d}:00", callback_data=f'rem:hours:start:{reminder_id}:{page}:{day_key}'), IB(f"🕙 До {int(cfg.get('end_hour', 22)):02d}:59", callback_data=f'rem:hours:end:{reminder_id}:{page}:{day_key}'))
    state_label = '✅ Активно' if cfg.get('enabled') and (not _reminder_is_completed(cfg)) else '⬜ Выключено'
    kb.row(IB(state_label, callback_data=f'rem:toggle:{reminder_id}:{page}:{day_key}'), IB('Изменить📝', callback_data=f'rem:editmenu:{reminder_id}:{page}:{day_key}'))
    kb.row(IB('⬅️ К напоминалкам', callback_data=_reminder_return_callback(page, day_key)))
    return kb
try:
    _v177_legacy_0129_build_reminder_menu_keyboard.__name__ = 'build_reminder_menu_keyboard'
except Exception:
    pass

def _reminder_edit_menu_keyboard(reminder_id: int, page: int, day_key: str, viewer_chat_id: int):
    cfg = _reminder_cfg(reminder_id) or {}
    kb = types.InlineKeyboardMarkup(row_width=1)
    kb.row(make_copy_or_inline_button('✍️ Вставить текст', compose_reminder_text_insert_value(reminder_id, cfg.get('text') or ''), viewer_chat_id=viewer_chat_id))
    kb.row(IB('🗑 Удалить', callback_data=f'rem:delete_confirm:{reminder_id}:{page}:{day_key}'))
    kb.row(IB('⬅️ Назад', callback_data=f'rem:open:{reminder_id}:{page}:{day_key}'), IB('✖️ Отмена', callback_data=f'rem:open:{reminder_id}:{page}:{day_key}'))
    return kb

def _reminder_dates_text(reminder_id: int) -> str:
    cfg = _reminder_cfg(reminder_id) or {}
    end = _reminder_fmt_date(cfg.get('end_date')) if cfg.get('end_date') else 'без конца'
    return f"📅 ДАТЫ НАПОМИНАЛКИ\n\nНачало: {_reminder_fmt_date(cfg.get('start_date'))}\nКонец: {end}"

def _reminder_dates_keyboard(reminder_id: int, page: int, day_key: str):
    cfg = _reminder_cfg(reminder_id) or {}
    kb = types.InlineKeyboardMarkup(row_width=2)
    now_ym = now_local().strftime('%Y-%m')
    start_label = '📅 Начало✅' if str(cfg.get('start_date') or '').strip() else '📅 Начало'
    end_label = '🏁 Конец✅' if str(cfg.get('end_date') or '').strip() else '🏁 Конец'
    kb.row(IB(start_label, callback_data=f'rem:calendar:start:{now_ym}:{reminder_id}:{page}:{day_key}'), IB(end_label, callback_data=f'rem:calendar:end:{now_ym}:{reminder_id}:{page}:{day_key}'))
    kb.row(IB('♾ Без конца', callback_data=f'rem:noend:{reminder_id}:{page}:{day_key}'))
    kb.row(IB('⬅️ Назад', callback_data=f'rem:open:{reminder_id}:{page}:{day_key}'))
    return kb

def _reminder_calendar_text(which: str, year: int, month: int) -> str:
    target = 'начала' if which == 'start' else 'окончания'
    return f'📅 Выберите дату {target}\n\n{_REMINDER_MONTHS_RU[month - 1]} {year}'

def _reminder_calendar_keyboard(which: str, year: int, month: int, reminder_id: int, page: int, day_key: str):
    kb = types.InlineKeyboardMarkup(row_width=7)
    kb.row(*[IB(x, callback_data='none') for x in ('Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс')])
    cal = calendar.Calendar(firstweekday=0)
    for week in cal.monthdayscalendar(year, month):
        row = []
        for d in week:
            if not d:
                row.append(IB(' ', callback_data='none'))
            else:
                date_key = f'{year:04d}-{month:02d}-{d:02d}'
                row.append(IB(str(d), callback_data=f'rem:date:{which}:{date_key}:{reminder_id}:{page}:{day_key}'))
        kb.row(*row)
    prev_month, prev_year = (month - 1, year)
    if prev_month < 1:
        prev_month, prev_year = (12, prev_year - 1)
    next_month, next_year = (month + 1, year)
    if next_month > 12:
        next_month, next_year = (1, next_year + 1)
    kb.row(IB('⬅️', callback_data=f'rem:calendar:{which}:{prev_year:04d}-{prev_month:02d}:{reminder_id}:{page}:{day_key}'), IB('📅 Даты', callback_data=f'rem:dates:{reminder_id}:{page}:{day_key}'), IB('➡️', callback_data=f'rem:calendar:{which}:{next_year:04d}-{next_month:02d}:{reminder_id}:{page}:{day_key}'))
    return kb

def _reminder_interval_keyboard(reminder_id: int, page: int, day_key: str, viewer_chat_id: int):
    cfg = _reminder_cfg(reminder_id) or {}
    current = int(cfg.get('interval_minutes', 120) or 120)
    kb = types.InlineKeyboardMarkup(row_width=3)
    buttons = []
    for minutes in [30, 60, 120, 180, 240, 360, 720, 1440]:
        mark = '✅ ' if minutes == current else ''
        buttons.append(IB(mark + _reminder_interval_label(minutes), callback_data=f'rem:intset:{minutes}:{reminder_id}:{page}:{day_key}'))
    for i in range(0, len(buttons), 3):
        kb.row(*buttons[i:i + 3])
    kb.row(make_copy_or_inline_button('✍️ Свой интервал', compose_reminder_interval_insert_value(reminder_id, cfg), viewer_chat_id=viewer_chat_id))
    kb.row(IB('⬅️ Назад', callback_data=f'rem:open:{reminder_id}:{page}:{day_key}'))
    return kb

def _reminder_hours_keyboard(which: str, reminder_id: int, page: int, day_key: str):
    cfg = _reminder_cfg(reminder_id) or {}
    current = int(cfg.get('start_hour' if which == 'start' else 'end_hour', 8 if which == 'start' else 22))
    kb = types.InlineKeyboardMarkup(row_width=4)
    buttons = []
    for hour in range(24):
        mark = '✅ ' if hour == current else ''
        buttons.append(IB(f'{mark}{hour:02d}:00', callback_data=f'rem:hourset:{which}:{hour}:{reminder_id}:{page}:{day_key}'))
    for i in range(0, 24, 4):
        kb.row(*buttons[i:i + 4])
    kb.row(IB('⬅️ Назад', callback_data=f'rem:open:{reminder_id}:{page}:{day_key}'))
    return kb

def _reminder_chats_keyboard(reminder_id: int, chat_page: int, list_page: int, day_key: str):
    cfg = _reminder_cfg(reminder_id) or {}
    selected = {int(x) for x in cfg.get('chat_ids') or [] if str(x).lstrip('-').isdigit()}
    rows = _reminder_known_chats()
    per_page = 8
    pages = max(1, (len(rows) + per_page - 1) // per_page)
    chat_page = max(0, min(int(chat_page), pages - 1))
    kb = types.InlineKeyboardMarkup(row_width=1)
    for cid, title in rows[chat_page * per_page:(chat_page + 1) * per_page]:
        mark = '✅' if cid in selected else '⬜'
        name = chat_button_title(cid, title) if 'chat_button_title' in globals() else str(title)
        kb.row(IB(f'{mark} {name}', callback_data=f'rem:chat:{cid}:{reminder_id}:{chat_page}:{list_page}:{day_key}'))
    nav = []
    if chat_page > 0:
        nav.append(IB('⬅️', callback_data=f'rem:chats:{reminder_id}:{chat_page - 1}:{list_page}:{day_key}'))
    nav.append(IB(f'{chat_page + 1}/{pages}', callback_data='none'))
    if chat_page + 1 < pages:
        nav.append(IB('➡️', callback_data=f'rem:chats:{reminder_id}:{chat_page + 1}:{list_page}:{day_key}'))
    kb.row(*nav)
    kb.row(IB('⬅️ Назад', callback_data=f'rem:open:{reminder_id}:{list_page}:{day_key}'))
    return kb

def _reminder_parse_custom_interval(text: str) -> int | None:
    value = str(text or '').strip().lower().replace(',', '.')
    m = re.fullmatch('\\s*(\\d+(?:\\.\\d+)?)\\s*(мин|м|min|m|ч|час|часа|часов|h|д|дн|день|дня|дней|d)?\\s*', value)
    if not m:
        return None
    num = float(m.group(1))
    unit = m.group(2) or 'мин'
    if unit in {'ч', 'час', 'часа', 'часов', 'h'}:
        minutes = int(round(num * 60))
    elif unit in {'д', 'дн', 'день', 'дня', 'дней', 'd'}:
        minutes = int(round(num * 1440))
    else:
        minutes = int(round(num))
    return minutes if 5 <= minutes <= 43200 else None

def _v177_legacy_0131_reminder_delete_message_map(last_map: dict) -> None:
    for cid_raw, mid_raw in list((last_map or {}).items()):
        try:
            bot.delete_message(int(cid_raw), int(mid_raw))
        except Exception:
            pass
try:
    _v177_legacy_0131_reminder_delete_message_map.__name__ = '_reminder_delete_message_map'
except Exception:
    pass

def _reminder_delete_last_messages(cfg: dict) -> None:
    """Очищаем ссылки сразу, а Telegram-удаление выполняем вне UI/config-lock."""
    last_map = dict(cfg.get('last_message_ids') or {})
    cfg['last_message_ids'] = {}
    if not last_map:
        return
    key_seed = '|'.join((f'{k}:{v}' for k, v in sorted(last_map.items())))
    key = 'reminder-cleanup:' + hashlib.sha1(key_seed.encode('utf-8')).hexdigest()[:16]
    pool = globals().get('GENERAL_TASK_POOL') or globals().get('REMINDER_TASK_POOL')
    try:
        if pool is not None and pool.submit_unique(key, _reminder_delete_message_map, last_map):
            return
    except Exception:
        pass
    try:
        _reminder_delete_message_map(last_map)
    except Exception:
        pass

def _canon_reminder_send_cycle__001(reminder_id: int, cfg: dict) -> bool:
    text = str(cfg.get('text') or '').strip()
    chat_ids = []
    for raw in cfg.get('chat_ids') or []:
        try:
            chat_ids.append(int(raw))
        except Exception:
            pass
    if not text or not chat_ids:
        return False
    message_text = f'НАПОМИНАЛКА🕰️\n\n{text}'
    last_map = cfg.setdefault('last_message_ids', {})
    sent_any = False
    for cid in chat_ids:
        old_mid = last_map.get(str(cid))
        try:
            sent = bot.send_message(cid, message_text)
            last_map[str(cid)] = int(sent.message_id)
            if old_mid and int(old_mid) != int(sent.message_id):
                try:
                    bot.delete_message(cid, int(old_mid))
                except Exception:
                    pass
            sent_any = True
            try:
                bot_journal('reminder_sent', cid, f'reminder_id={int(reminder_id)} message_id={sent.message_id}')
            except Exception:
                pass
        except Exception as exc:
            log_error(f'reminder {reminder_id} send {cid}: {exc}')
            try:
                bot_journal('reminder_send_error', cid, f'reminder_id={int(reminder_id)} {exc}', 'ERROR')
            except Exception:
                pass
    return sent_any

def _reminder_tick_one(reminder_id: int, cfg: dict) -> bool:
    if not bool(cfg.get('enabled')):
        return False
    now_dt = now_local()
    if not str(cfg.get('text') or '').strip() or not (cfg.get('chat_ids') or []):
        return False
    due = _reminder_parse_dt(cfg.get('next_run_at'))
    if due is None:
        _reminder_rearm(cfg, immediate_if_valid=True)
        due = _reminder_parse_dt(cfg.get('next_run_at'))
    if due is None or now_dt < due:
        return False
    if not _reminder_date_allowed(now_dt, cfg) or not _reminder_time_allowed(now_dt, cfg):
        next_dt = _reminder_next_valid_start(now_dt, cfg)
        cfg['next_run_at'] = next_dt.isoformat(timespec='seconds') if next_dt else ''
        if next_dt is None:
            cfg['enabled'] = False
        _reminder_touch(cfg)
        return True
    if _reminder_send_cycle(reminder_id, cfg):
        cfg['last_sent_at'] = now_dt.isoformat(timespec='seconds')
    _reminder_advance_after_send(now_dt, cfg)
    _reminder_touch(cfg)
    return True

def _reminder_due_now(cfg: dict, now_dt=None) -> bool:
    if not bool((cfg or {}).get('enabled')):
        return False
    if not str((cfg or {}).get('text') or '').strip() or not ((cfg or {}).get('chat_ids') or []):
        return False
    now_dt = now_dt or now_local()
    due = _reminder_parse_dt((cfg or {}).get('next_run_at'))
    return due is None or now_dt >= due

def _reminder_tick_job(reminder_id: int) -> None:
    """One reminder per keyed worker; completion also removes the last chat message."""
    reminder_id = int(reminder_id)
    snapshot = None
    now_dt = now_local()
    changed_without_send = False
    completed = False
    with _REMINDER_CONFIG_LOCK:
        cfg = _reminder_cfg(reminder_id)
        if not cfg or _reminder_is_completed(cfg):
            return
        if _reminder_end_has_passed(cfg, now_dt):
            _reminder_mark_completed(reminder_id, cfg, 'end_date_finished', delete_messages=True)
            completed = True
        elif not _reminder_due_now(cfg, now_dt):
            return
        else:
            due = _reminder_parse_dt(cfg.get('next_run_at'))
            if due is None:
                _reminder_rearm(cfg, immediate_if_valid=True)
                due = _reminder_parse_dt(cfg.get('next_run_at'))
            if due is None:
                _reminder_mark_completed(reminder_id, cfg, 'no_next_time', delete_messages=True)
                completed = True
            elif now_dt < due:
                return
            elif not _reminder_date_allowed(now_dt, cfg) or not _reminder_time_allowed(now_dt, cfg):
                next_dt = _reminder_next_valid_start(now_dt, cfg)
                cfg['next_run_at'] = next_dt.isoformat(timespec='seconds') if next_dt else ''
                if next_dt is None:
                    _reminder_mark_completed(reminder_id, cfg, 'schedule_finished', delete_messages=True)
                    completed = True
                else:
                    _reminder_touch(cfg)
                    changed_without_send = True
            else:
                snapshot = copy.deepcopy(cfg)
    if completed:
        _reminder_save('reminder_completed')
        return
    if changed_without_send:
        _reminder_save('reminders_tick_window')
        return
    if snapshot is None:
        return
    sent_ok = _reminder_send_cycle(reminder_id, snapshot)
    updated = False
    with _REMINDER_CONFIG_LOCK:
        cfg = _reminder_cfg(reminder_id)
        if cfg and (not _reminder_is_completed(cfg)):
            cfg['last_message_ids'] = dict(snapshot.get('last_message_ids') or {})
            if sent_ok:
                cfg['last_sent_at'] = now_dt.isoformat(timespec='seconds')
            _reminder_advance_after_send(now_dt, cfg)
            if not cfg.get('next_run_at') or _reminder_end_has_passed(cfg, now_local()):
                _reminder_mark_completed(reminder_id, cfg, 'schedule_finished', delete_messages=True)
            else:
                _reminder_touch(cfg)
            updated = True
    if updated:
        _reminder_save('reminders_tick')

def _v177_legacy_0132_reminder_tick() -> None:
    now_dt = now_local()
    due_ids = []
    with _REMINDER_CONFIG_LOCK:
        for rid, cfg in _reminder_items():
            try:
                if _reminder_due_now(cfg, now_dt):
                    due_ids.append(int(rid))
            except Exception as exc:
                log_error(f'reminder {rid} due check: {exc}')
    for rid in due_ids:
        if not REMINDER_TASK_POOL.submit_unique(f'reminder:{rid}', _reminder_tick_job, rid):
            try:
                bot_journal('reminder_dispatch_coalesced', None, f'reminder_id={rid}')
            except Exception:
                pass
try:
    _v177_legacy_0132_reminder_tick.__name__ = '_reminder_tick'
except Exception:
    pass

def _reminder_boot_reconcile_v241() -> dict:
    """Rebuild runnable reminder timing after deploy/restore.

    Durable reminder settings are authoritative; queued scheduler state is not.  An
    enabled reminder that survived deploy must always have a valid next_run_at.  If
    the stored deadline is overdue, arm it for the next scheduler tick; if the bot is
    outside the configured date/hour window, move it to the next valid window.
    Completed reminders are never resurrected by boot reconciliation.
    """
    now_dt = now_local()
    changed = 0
    active = 0
    overdue = 0
    repaired = 0
    invalid = 0
    completed_fixed = 0
    with _REMINDER_CONFIG_LOCK:
        rows_fn = globals().get('reminder_items_global_for_completion')
        all_rows = rows_fn(include_completed=True) if callable(rows_fn) else _reminder_items(include_completed=True)
        for rid, cfg in all_rows:
            cfg = _normalize_reminder_cfg(cfg)
            if _reminder_is_completed(cfg):
                if cfg.get('enabled') or cfg.get('next_run_at'):
                    cfg['enabled'] = False
                    cfg['next_run_at'] = ''
                    _reminder_touch(cfg)
                    changed += 1
                    completed_fixed += 1
                continue
            if not bool(cfg.get('enabled')):
                continue
            active += 1
            if not str(cfg.get('text') or '').strip() or not (cfg.get('chat_ids') or []):
                if cfg.get('next_run_at'):
                    cfg['next_run_at'] = ''
                    _reminder_touch(cfg)
                    changed += 1
                invalid += 1
                continue
            if _reminder_end_has_passed(cfg, now_dt):
                _reminder_mark_completed(rid, cfg, 'end_date_finished', delete_messages=False)
                changed += 1
                completed_fixed += 1
                continue
            due = _reminder_parse_dt(cfg.get('next_run_at'))
            allowed_now = _reminder_date_allowed(now_dt, cfg) and _reminder_time_allowed(now_dt, cfg)
            new_due = due
            if allowed_now:
                if due is None:
                    last = _reminder_parse_dt(cfg.get('last_sent_at'))
                    try:
                        interval = max(1, int(cfg.get('interval_minutes', 120)))
                    except Exception:
                        interval = 120
                    candidate = last + timedelta(minutes=interval) if last is not None else None
                    if candidate is not None and candidate > now_dt:
                        new_due = candidate
                    else:
                        new_due = now_dt
                        overdue += 1
                elif due <= now_dt:
                    new_due = now_dt
                    overdue += 1
                elif not (_reminder_date_allowed(due, cfg) and _reminder_time_allowed(due, cfg)):
                    new_due = _reminder_next_valid_start(now_dt, cfg)
            elif due is None or due <= now_dt or (not (_reminder_date_allowed(due, cfg) and _reminder_time_allowed(due, cfg))):
                new_due = _reminder_next_valid_start(now_dt, cfg)
            new_text = new_due.isoformat(timespec='seconds') if new_due else ''
            if str(cfg.get('next_run_at') or '') != new_text:
                cfg['next_run_at'] = new_text
                if new_due is None:
                    cfg['enabled'] = False
                _reminder_touch(cfg)
                changed += 1
                repaired += 1
        state_root = data.setdefault('_global_settings', {}).get('reminder_groups_v149')
        if isinstance(state_root, dict):
            for cid, row in list(state_root.items()):
                if not isinstance(row, dict):
                    continue
                next_rows = []
                try:
                    chat_id = int(cid)
                except Exception:
                    chat_id = 0
                active_rows = rows_fn(include_completed=False) if callable(rows_fn) else _reminder_items()
                for _rid, cfg in active_rows:
                    try:
                        ids = {int(x) for x in cfg.get('chat_ids') or []}
                    except Exception:
                        ids = set()
                    if chat_id and chat_id in ids and cfg.get('enabled') and (not _reminder_is_completed(cfg)):
                        dt = _reminder_parse_dt(cfg.get('next_run_at'))
                        if dt is not None:
                            next_rows.append(dt)
                rebuilt = min(next_rows).isoformat(timespec='seconds') if next_rows else ''
                if str(row.get('next_run_at') or '') != rebuilt:
                    row['next_run_at'] = rebuilt
                    changed += 1
    if changed:
        _reminder_save('reminder_boot_reconcile_v241')
    detail = {'active': active, 'repaired': repaired, 'overdue': overdue, 'invalid': invalid, 'completed_fixed': completed_fixed, 'changed': changed}
    try:
        runtime_event('reminder_boot_reconciled_v241', json.dumps(detail, ensure_ascii=False), 'INFO')
    except Exception:
        try:
            bot_journal('reminder_boot_reconciled_v241', int(OWNER_ID or 0) or None, str(detail))
        except Exception:
            pass
    return detail

def _reminder_scheduler_tick() -> None:
    try:
        if runtime_is_ready():
            _reminder_tick()
    except Exception as exc:
        log_error(f'reminder scheduler: {exc}')
    finally:
        try:
            DELAYED_SCHEDULER.schedule('reminder-scheduler', _REMINDER_CHECK_SECONDS, _reminder_scheduler_tick)
        except Exception:
            pass

def start_reminder_scheduler() -> None:
    global _REMINDER_THREAD_STARTED
    with _REMINDER_THREAD_LOCK:
        if _REMINDER_THREAD_STARTED:
            return
        _REMINDER_THREAD_STARTED = True
        _reminders_root()
        try:
            _reminder_boot_reconcile_v241()
        except Exception as exc:
            log_error(f'reminder boot reconcile v241: {exc}')
            try:
                runtime_event('reminder_boot_reconcile_error_v241', str(exc)[:500], 'WARN')
            except Exception:
                pass
        try:
            save_data(data, root_only=True)
        except Exception as exc:
            log_error(f'reminder migration save: {exc}')
        try:
            DELAYED_SCHEDULER.schedule('reminder-scheduler', 1.0, _reminder_scheduler_tick)
        except Exception:
            pass

def _reminder_direct_input_predicate(msg) -> bool:
    try:
        actor = int(getattr(getattr(msg, 'from_user', None), 'id', 0) or 0)
        owner_actor = actor == int(OWNER_ID or 0)
        if getattr(msg, 'content_type', None) != 'text' or not (is_owner_chat(int(msg.chat.id)) or owner_actor):
            return False
        text = str(getattr(msg, 'text', '') or '')
        return bool(re.search('\\((?:EDITREM|EDITREMINT)\\|\\d+\\|', text))
    except Exception:
        return False

def _reminder_extract_insert(text: str, kind: str):
    raw = str(text or '')
    m = re.search(f'\\(({re.escape(kind)}\\|(\\d+)\\|)[^)]*\\)', raw)
    if not m:
        return (None, '')
    try:
        rid = int(m.group(2))
    except Exception:
        return (None, '')
    value = (raw[:m.start()] + ' ' + raw[m.end():]).strip()
    try:
        value = sanitize_telegram_inserted_text(value)
    except Exception:
        value = re.sub('(?m)^\\s*@[A-Za-z0-9_]{3,}\\s+', '', value).strip()
    return (rid, value.strip())

def _reminder_refresh_bound_editor(reminder_id: int) -> None:
    binding = _REMINDER_UI_BINDINGS.get(int(reminder_id)) or {}
    try:
        chat_id = int(binding.get('chat_id'))
        message_id = int(binding.get('message_id'))
    except Exception:
        return
    cfg = _reminder_cfg(reminder_id)
    if not cfg:
        return
    day_key = str(binding.get('day_key') or today_key())
    page = int(binding.get('page') or 0)
    try:
        bot.edit_message_text(build_reminder_menu_text(reminder_id), chat_id=chat_id, message_id=message_id, reply_markup=build_reminder_menu_keyboard(reminder_id, day_key, page, viewer_chat_id=chat_id))
    except Exception as exc:
        if 'message is not modified' not in str(exc).lower():
            log_error(f'reminder refresh bound editor {reminder_id}: {exc}')

@bot.message_handler(func=_reminder_direct_input_predicate, content_types=['text'])
def reminder_direct_input_message(msg):
    chat_id = int(msg.chat.id)
    text = str(msg.text or '')
    if 'EDITREMINT|' in text:
        rid, value = _reminder_extract_insert(text, 'EDITREMINT')
        cfg = _reminder_cfg(rid) if rid is not None else None
        if not cfg:
            send_and_auto_delete(chat_id, '❌ Напоминалка не найдена.', 8)
            return
        minutes = _reminder_parse_custom_interval(value)
        if minutes is None:
            send_and_auto_delete(chat_id, '❌ Пример: 90 мин, 2 ч, 1 день. Минимум 5 минут.', 10)
            return
        _durable_note_source_consumed('reminder_interval_insert')
        cfg['interval_minutes'] = int(minutes)
        _durable_note_reminder_edit_witness({'reminder_id': int(rid), 'kind': 'interval', 'interval_minutes': int(minutes)})
        if cfg.get('enabled'):
            _reminder_rearm_after_interval_v243(cfg, preserve_future=False)
        _reminder_touch(cfg)
        _reminder_save('reminder_interval_insert')
        try:
            bot.delete_message(chat_id, msg.message_id)
        except Exception:
            pass
        _reminder_refresh_bound_editor(rid)
        return
    rid, value = _reminder_extract_insert(text, 'EDITREM')
    cfg = _reminder_cfg(rid) if rid is not None else None
    if not cfg:
        send_and_auto_delete(chat_id, '❌ Напоминалка не найдена.', 8)
        return
    if not value:
        send_and_auto_delete(chat_id, '❌ Текст пустой.', 8)
        return
    if len(value) > 4000:
        send_and_auto_delete(chat_id, '❌ Текст слишком длинный. Максимум 4000 символов.', 10)
        return
    _durable_note_source_consumed('reminder_text_insert')
    cfg['text'] = value
    _durable_note_reminder_edit_witness({'reminder_id': int(rid), 'kind': 'text', 'text': str(value)})
    if cfg.get('enabled'):
        _reminder_rearm_after_interval_v243(cfg, preserve_future=True)
    _reminder_touch(cfg)
    _reminder_save('reminder_text_insert')
    try:
        bot.delete_message(chat_id, msg.message_id)
    except Exception:
        pass
    _reminder_refresh_bound_editor(rid)

def reminder_callback(call):
    chat_id = int(call.message.chat.id)
    actor = int(getattr(getattr(call, 'from_user', None), 'id', 0) or 0)
    if not is_owner_chat(chat_id) and actor != int(OWNER_ID or 0):
        try:
            bot.answer_callback_query(call.id, 'Напоминалка доступна только владельцу', show_alert=True)
        except Exception:
            pass
        return
    raw = str(call.data or '')
    parts = raw.split(':')
    action = parts[1] if len(parts) > 1 else 'menu'
    try:
        bot.answer_callback_query(call.id)
    except Exception:
        pass
    if action == 'schedule':
        rid = int(parts[2])
        page = int(parts[3])
        day_key = parts[4]
        safe_edit(bot, call, reminder_schedule_text(rid), reply_markup=reminder_schedule_keyboard(rid, page, day_key))
        return
    if action == 'preview':
        rid = int(parts[2])
        page = int(parts[3])
        day_key = parts[4]
        safe_edit(bot, call, reminder_preview_text(rid), reply_markup=reminder_preview_keyboard(rid, page, day_key, chat_id))
        return
    if action == 'group_open':
        target_chat_id = int(parts[2])
        page = int(parts[3])
        day_key = parts[4]
        safe_edit(bot, call, reminder_group_text(target_chat_id, day_key), reply_markup=reminder_group_keyboard(target_chat_id, page, day_key))
        return
    if action == 'group_set2h':
        target_chat_id = int(parts[2])
        page = int(parts[3])
        day_key = parts[4]
        reminder_group_set_two_hours(target_chat_id, day_key)
        safe_edit(bot, call, reminder_group_text(target_chat_id, day_key), reply_markup=reminder_group_keyboard(target_chat_id, page, day_key))
        return
    if action == 'group_sync':
        target_chat_id = int(parts[2])
        page = int(parts[3])
        day_key = parts[4]
        reminder_group_sync_from_first(target_chat_id, day_key)
        safe_edit(bot, call, reminder_group_text(target_chat_id, day_key), reply_markup=reminder_group_keyboard(target_chat_id, page, day_key))
        return
    if action == 'group_toggle':
        target_chat_id = int(parts[2])
        page = int(parts[3])
        day_key = parts[4]
        reminder_group_toggle_all(target_chat_id, day_key)
        safe_edit(bot, call, reminder_group_text(target_chat_id, day_key), reply_markup=reminder_group_keyboard(target_chat_id, page, day_key))
        return
    if action == 'group_test':
        target_chat_id = int(parts[2])
        page = int(parts[3])
        day_key = parts[4]
        REMINDER_TASK_POOL.submit_unique(f'reminder-group-test:{target_chat_id}', _reminder_group_send_job, target_chat_id, day_key, True)
        try:
            bot.answer_callback_query(call.id, 'Объединённая напоминалка отправляется')
        except Exception:
            pass
        return
    if action == 'completed':
        page = int(parts[2]) if len(parts) > 2 else 0
        delete_mode = bool(int(parts[3])) if len(parts) > 3 and str(parts[3]).isdigit() else False
        safe_edit(bot, call, build_completed_reminders_text(page, delete_mode), reply_markup=build_completed_reminders_keyboard(page, delete_mode))
        return
    if action == 'completed_open':
        rid = int(parts[2])
        page = int(parts[3]) if len(parts) > 3 else 0
        if not _reminder_cfg(rid):
            safe_edit(bot, call, build_completed_reminders_text(page), reply_markup=build_completed_reminders_keyboard(page))
            return
        _reminder_bind_editor(rid, chat_id, call.message.message_id, 'completed', page)
        safe_edit(bot, call, build_reminder_menu_text(rid), reply_markup=build_reminder_menu_keyboard(rid, 'completed', page, viewer_chat_id=chat_id))
        return
    if action == 'completed_select_mode':
        page = int(parts[2]) if len(parts) > 2 else 0
        _REMINDER_COMPLETED_DELETE_SELECTION[int(OWNER_ID or chat_id)].clear()
        safe_edit(bot, call, build_completed_reminders_text(page, True), reply_markup=build_completed_reminders_keyboard(page, True))
        return
    if action == 'completed_select':
        rid = int(parts[2])
        page = int(parts[3]) if len(parts) > 3 else 0
        selected = _REMINDER_COMPLETED_DELETE_SELECTION.setdefault(int(OWNER_ID or chat_id), set())
        if rid in selected:
            selected.remove(rid)
        else:
            selected.add(rid)
        safe_edit(bot, call, build_completed_reminders_text(page, True), reply_markup=build_completed_reminders_keyboard(page, True))
        return
    if action == 'completed_cancel_select':
        page = int(parts[2]) if len(parts) > 2 else 0
        _REMINDER_COMPLETED_DELETE_SELECTION[int(OWNER_ID or chat_id)].clear()
        safe_edit(bot, call, build_completed_reminders_text(page, False), reply_markup=build_completed_reminders_keyboard(page, False))
        return
    if action == 'completed_delete_selected':
        page = int(parts[2]) if len(parts) > 2 else 0
        selected = set(_REMINDER_COMPLETED_DELETE_SELECTION.get(int(OWNER_ID or chat_id), set()))
        root = _reminders_root()
        for rid in selected:
            cfg = _reminder_cfg(rid)
            if cfg:
                _reminder_delete_last_messages(cfg)
            root.setdefault('items', {}).pop(str(rid), None)
            _reminder_unbind(rid)
        _REMINDER_COMPLETED_DELETE_SELECTION[int(OWNER_ID or chat_id)].clear()
        _reminder_save('reminder_completed_bulk_delete')
        rows = _reminder_completed_items()
        pages = max(1, (len(rows) + _REMINDER_COMPLETED_PAGE_SIZE - 1) // _REMINDER_COMPLETED_PAGE_SIZE)
        page = min(page, pages - 1)
        safe_edit(bot, call, build_completed_reminders_text(page, False), reply_markup=build_completed_reminders_keyboard(page, False))
        return
    if action == 'menu':
        day_key = parts[2] if len(parts) > 2 else today_key()
        safe_edit(bot, call, build_reminder_list_text(), reply_markup=build_reminder_list_keyboard(day_key, 0))
        return
    legacy_min_parts = {'dates': 5, 'calendar': 7, 'date': 7, 'noend': 5, 'interval': 5, 'intset': 6, 'hours': 6, 'hourset': 7, 'chats': 6, 'chat': 7, 'toggle': 5, 'delete_confirm': 5, 'delete': 5}
    if action in {'text', 'intcustom', 'cancelinput'} or (action in legacy_min_parts and len(parts) < legacy_min_parts[action]):
        old_day = next((x for x in reversed(parts) if re.fullmatch('\\d{4}-\\d{2}-\\d{2}', str(x or ''))), today_key())
        safe_edit(bot, call, build_reminder_list_text(), reply_markup=build_reminder_list_keyboard(old_day, 0))
        return
    if action == 'list':
        page = int(parts[2]) if len(parts) > 2 else 0
        day_key = parts[3] if len(parts) > 3 else today_key()
        safe_edit(bot, call, build_reminder_list_text(), reply_markup=build_reminder_list_keyboard(day_key, page))
        return
    if action == 'add':
        page = int(parts[2]) if len(parts) > 2 else 0
        day_key = parts[3] if len(parts) > 3 else today_key()
        rid, _cfg = _reminder_create()
        _reminder_bind_editor(rid, chat_id, call.message.message_id, day_key, page)
        safe_edit(bot, call, build_reminder_menu_text(rid), reply_markup=build_reminder_menu_keyboard(rid, day_key, page, viewer_chat_id=chat_id))
        return
    if action == 'open':
        rid = int(parts[2])
        page = int(parts[3]) if len(parts) > 3 else 0
        day_key = parts[4] if len(parts) > 4 else today_key()
        if not _reminder_cfg(rid):
            if str(day_key) == 'completed':
                safe_edit(bot, call, build_completed_reminders_text(page), reply_markup=build_completed_reminders_keyboard(page))
                return
            safe_edit(bot, call, build_reminder_list_text(), reply_markup=build_reminder_list_keyboard(day_key, page))
            return
        _reminder_bind_editor(rid, chat_id, call.message.message_id, day_key, page)
        safe_edit(bot, call, build_reminder_menu_text(rid), reply_markup=build_reminder_menu_keyboard(rid, day_key, page, viewer_chat_id=chat_id))
        return
    if action == 'editmenu':
        rid = int(parts[2])
        page = int(parts[3])
        day_key = parts[4] if len(parts) > 4 else today_key()
        _reminder_bind_editor(rid, chat_id, call.message.message_id, day_key, page)
        safe_edit(bot, call, f'Изменить📝 напоминалку №{_reminder_position(rid) or rid}', reply_markup=_reminder_edit_menu_keyboard(rid, page, day_key, chat_id))
        return
    if action == 'dates':
        rid = int(parts[2])
        page = int(parts[3])
        day_key = parts[4]
        safe_edit(bot, call, _reminder_dates_text(rid), reply_markup=_reminder_dates_keyboard(rid, page, day_key))
        return
    if action == 'calendar':
        which = parts[2] if len(parts) > 2 else 'start'
        ym = parts[3]
        rid = int(parts[4])
        page = int(parts[5])
        day_key = parts[6]
        try:
            year, month = [int(x) for x in ym.split('-', 1)]
        except Exception:
            year, month = (now_local().year, now_local().month)
        safe_edit(bot, call, _reminder_calendar_text(which, year, month), reply_markup=_reminder_calendar_keyboard(which, year, month, rid, page, day_key))
        return
    if action == 'date':
        which, date_key = (parts[2], parts[3])
        rid = int(parts[4])
        page = int(parts[5])
        day_key = parts[6]
        cfg = _reminder_cfg(rid)
        selected = _reminder_parse_date(date_key)
        if not cfg or selected is None:
            return
        if which == 'start':
            cfg['start_date'] = date_key
            end = _reminder_parse_date(cfg.get('end_date'))
            if end and end < selected:
                cfg['end_date'] = date_key
        else:
            start = _reminder_parse_date(cfg.get('start_date')) or selected
            cfg['end_date'] = date_key if selected >= start else start.strftime('%Y-%m-%d')
        if cfg.get('enabled'):
            _reminder_rearm_after_interval_v243(cfg, preserve_future=False)
        _reminder_touch(cfg)
        _reminder_save('reminder_dates')
        safe_edit(bot, call, _reminder_dates_text(rid), reply_markup=_reminder_dates_keyboard(rid, page, day_key))
        return
    if action == 'noend':
        rid = int(parts[2])
        page = int(parts[3])
        day_key = parts[4]
        cfg = _reminder_cfg(rid)
        if not cfg:
            return
        cfg['end_date'] = ''
        if cfg.get('enabled'):
            _reminder_rearm_after_interval_v243(cfg, preserve_future=True)
        _reminder_touch(cfg)
        _reminder_save('reminder_noend')
        safe_edit(bot, call, _reminder_dates_text(rid), reply_markup=_reminder_dates_keyboard(rid, page, day_key))
        return
    if action == 'interval':
        rid = int(parts[2])
        page = int(parts[3])
        day_key = parts[4]
        safe_edit(bot, call, '🔁 ПЕРИОДИЧНОСТЬ\n\nКак часто присылать напоминание?', reply_markup=_reminder_interval_keyboard(rid, page, day_key, chat_id))
        return
    if action == 'intset':
        minutes = int(parts[2])
        rid = int(parts[3])
        page = int(parts[4])
        day_key = parts[5]
        cfg = _reminder_cfg(rid)
        if not cfg:
            return
        cfg['interval_minutes'] = max(5, int(minutes))
        if cfg.get('enabled'):
            _reminder_rearm_after_interval_v243(cfg, preserve_future=False)
        _reminder_touch(cfg)
        _reminder_save('reminder_interval')
        safe_edit(bot, call, build_reminder_menu_text(rid), reply_markup=build_reminder_menu_keyboard(rid, day_key, page, viewer_chat_id=chat_id))
        return
    if action == 'hours':
        which = parts[2]
        rid = int(parts[3])
        page = int(parts[4])
        day_key = parts[5]
        label = 'С КАКОГО ЧАСА' if which == 'start' else 'ДО КАКОГО ЧАСА'
        safe_edit(bot, call, f'🕐 {label}\n\nВыберите час.', reply_markup=_reminder_hours_keyboard(which, rid, page, day_key))
        return
    if action == 'hourset':
        which = parts[2]
        hour = max(0, min(23, int(parts[3])))
        rid = int(parts[4])
        page = int(parts[5])
        day_key = parts[6]
        cfg = _reminder_cfg(rid)
        if not cfg:
            return
        if which == 'start':
            cfg['start_hour'] = hour
            if int(cfg.get('end_hour', 22)) < hour:
                cfg['end_hour'] = hour
        else:
            cfg['end_hour'] = hour
            if int(cfg.get('start_hour', 8)) > hour:
                cfg['start_hour'] = hour
        if cfg.get('enabled'):
            _reminder_rearm_after_interval_v243(cfg, preserve_future=False)
        _reminder_touch(cfg)
        _reminder_save('reminder_hours')
        safe_edit(bot, call, build_reminder_menu_text(rid), reply_markup=build_reminder_menu_keyboard(rid, day_key, page, viewer_chat_id=chat_id))
        return
    if action == 'chats':
        rid = int(parts[2])
        chat_page = int(parts[3])
        list_page = int(parts[4])
        day_key = parts[5]
        safe_edit(bot, call, '💬 ЧАТЫ ДЛЯ НАПОМИНАЛКИ\n\nНажимайте — ✅ выбран / ⬜ не выбран.', reply_markup=_reminder_chats_keyboard(rid, chat_page, list_page, day_key))
        return
    if action == 'chat':
        target = int(parts[2])
        rid = int(parts[3])
        chat_page = int(parts[4])
        list_page = int(parts[5])
        day_key = parts[6]
        cfg = _reminder_cfg(rid)
        if not cfg:
            return
        selected = {int(x) for x in cfg.get('chat_ids') or [] if str(x).lstrip('-').isdigit()}
        if target in selected:
            selected.remove(target)
            old_mid = (cfg.get('last_message_ids') or {}).pop(str(target), None)
            if old_mid:
                try:
                    bot.delete_message(target, int(old_mid))
                except Exception:
                    pass
        else:
            selected.add(target)
        cfg['chat_ids'] = sorted(selected)
        if cfg.get('enabled'):
            _reminder_rearm_after_interval_v243(cfg, preserve_future=True)
        _reminder_touch(cfg)
        _reminder_save('reminder_chats')
        safe_edit(bot, call, '💬 ЧАТЫ ДЛЯ НАПОМИНАЛКИ\n\nНажимайте — ✅ выбран / ⬜ не выбран.', reply_markup=_reminder_chats_keyboard(rid, chat_page, list_page, day_key))
        return
    if action == 'toggle':
        rid = int(parts[2])
        page = int(parts[3])
        day_key = parts[4]
        cfg = _reminder_cfg(rid)
        if not cfg:
            return
        if _reminder_is_completed(cfg):
            send_and_auto_delete(chat_id, '✅ Эта напоминалка завершена. Для повторного запуска используйте «♻️ Возобновить».', 10)
            safe_edit(bot, call, build_reminder_menu_text(rid), reply_markup=build_reminder_menu_keyboard(rid, day_key, page, viewer_chat_id=chat_id))
            return
        if not cfg.get('enabled'):
            if not str(cfg.get('text') or '').strip():
                send_and_auto_delete(chat_id, '❌ Сначала задайте текст напоминания.', 8)
                return
            if not (cfg.get('chat_ids') or []):
                send_and_auto_delete(chat_id, '❌ Сначала выберите хотя бы один чат.', 8)
                return
            if _reminder_parse_date(cfg.get('end_date')) and _reminder_parse_date(cfg.get('end_date')) < now_local().date():
                cfg['end_date'] = ''
            cfg['enabled'] = True
            _reminder_rearm_after_interval_v243(cfg, preserve_future=False)
        else:
            cfg['enabled'] = False
            cfg['next_run_at'] = ''
        _reminder_touch(cfg)
        _reminder_save('reminder_toggle_v243')
        safe_edit(bot, call, build_reminder_menu_text(rid), reply_markup=build_reminder_menu_keyboard(rid, day_key, page, viewer_chat_id=chat_id))
        return
    if action == 'resume_confirm':
        rid = int(parts[2])
        page = int(parts[3])
        day_key = parts[4]
        cfg = _reminder_cfg(rid)
        if not cfg:
            return
        kb = types.InlineKeyboardMarkup(row_width=1)
        kb.row(IB('✅ Да, возобновить', callback_data=f'rem:resume:{rid}:{page}:{day_key}'))
        kb.row(IB('⬅️ Отмена', callback_data=f'rem:open:{rid}:{page}:{day_key}'))
        safe_edit(bot, call, '♻️ Возобновить завершённую напоминалку?\n\nСледующая отправка будет поставлена по её текущему интервалу, а не немедленно.', reply_markup=kb)
        return
    if action == 'resume':
        rid = int(parts[2])
        page = int(parts[3])
        day_key = parts[4]
        cfg = _reminder_cfg(rid)
        if not cfg:
            return
        if not str(cfg.get('text') or '').strip() or not (cfg.get('chat_ids') or []):
            send_and_auto_delete(chat_id, '❌ Для возобновления нужен текст и хотя бы один чат.', 10)
            return
        _reminder_clear_completion_v243(cfg)
        if _reminder_parse_date(cfg.get('end_date')) and _reminder_parse_date(cfg.get('end_date')) < now_local().date():
            cfg['end_date'] = ''
        cfg['enabled'] = True
        _reminder_rearm_after_interval_v243(cfg, preserve_future=False)
        _reminder_touch(cfg)
        _reminder_save('reminder_resume_v243')
        safe_edit(bot, call, build_reminder_menu_text(rid), reply_markup=build_reminder_menu_keyboard(rid, day_key, page, viewer_chat_id=chat_id))
        return
    if action == 'delete_confirm':
        rid = int(parts[2])
        page = int(parts[3])
        day_key = parts[4]
        kb = types.InlineKeyboardMarkup(row_width=2)
        kb.row(IB('🗑 Да, удалить', callback_data=f'rem:delete:{rid}:{page}:{day_key}'), IB('✖️ Отмена', callback_data=f'rem:open:{rid}:{page}:{day_key}'))
        safe_edit(bot, call, '🗑 Удалить напоминалку?\n\nПоследние отправленные сообщения этой напоминалки тоже будут удалены из выбранных чатов.', reply_markup=kb)
        return
    if action == 'delete':
        rid = int(parts[2])
        page = int(parts[3])
        day_key = parts[4]
        root = _reminders_root()
        cfg = _reminder_cfg(rid)
        if cfg:
            _reminder_delete_last_messages(cfg)
        root.setdefault('items', {}).pop(str(rid), None)
        _reminder_unbind(rid)
        _reminder_save('reminder_delete')
        if str(day_key) == 'completed':
            rows = _reminder_completed_items()
            pages = max(1, (len(rows) + _REMINDER_COMPLETED_PAGE_SIZE - 1) // _REMINDER_COMPLETED_PAGE_SIZE)
            page = min(page, pages - 1)
            safe_edit(bot, call, build_completed_reminders_text(page), reply_markup=build_completed_reminders_keyboard(page))
            return
        rows = _reminder_items()
        pages = max(1, (len(rows) + _REMINDER_LIST_PAGE_SIZE - 1) // _REMINDER_LIST_PAGE_SIZE)
        page = min(page, pages - 1)
        safe_edit(bot, call, build_reminder_list_text(), reply_markup=build_reminder_list_keyboard(day_key, page))
        return
_BUILD_REMINDER_LIST_TEXT_V141 = _v177_legacy_0123_build_reminder_list_text
_BUILD_REMINDER_LIST_KEYBOARD_V141 = _v177_legacy_0125_build_reminder_list_keyboard
_BUILD_REMINDER_MENU_TEXT_V141 = _v177_legacy_0127_build_reminder_menu_text
_BUILD_REMINDER_MENU_KEYBOARD_V141 = _v177_legacy_0129_build_reminder_menu_keyboard

def _reminder_date_allowed_for_day(cfg: dict, day_key: str) -> bool:
    try:
        d = datetime.strptime(str(day_key), '%Y-%m-%d').date()
    except Exception:
        d = now_local().date()
    start = _reminder_parse_date((cfg or {}).get('start_date'))
    end = _reminder_parse_date((cfg or {}).get('end_date'))
    return not (start and d < start or (end and d > end))

def _reminder_single_chat_id(cfg: dict) -> int | None:
    ids = []
    for raw in (cfg or {}).get('chat_ids') or []:
        try:
            ids.append(int(raw))
        except Exception:
            pass
    ids = list(dict.fromkeys(ids))
    return ids[0] if len(ids) == 1 else None

def reminder_group_members(target_chat_id: int, day_key: str | None=None, enabled_only: bool=False) -> list[tuple[int, dict]]:
    target_chat_id = int(target_chat_id)
    day_key = str(day_key or today_key())
    rows = []
    for rid, cfg in _reminder_items():
        if _reminder_single_chat_id(cfg) != target_chat_id:
            continue
        if enabled_only and (not bool(cfg.get('enabled'))):
            continue
        if not _reminder_date_allowed_for_day(cfg, day_key):
            continue
        rows.append((int(rid), cfg))
    rows.sort(key=lambda row: row[0])
    return rows

def _reminder_group_map(day_key: str | None=None, enabled_only: bool=False) -> dict[int, list[tuple[int, dict]]]:
    day_key = str(day_key or today_key())
    grouped = defaultdict(list)
    for rid, cfg in _reminder_items():
        cid = _reminder_single_chat_id(cfg)
        if cid is None:
            continue
        if enabled_only and (not bool(cfg.get('enabled'))):
            continue
        if not _reminder_date_allowed_for_day(cfg, day_key):
            continue
        grouped[int(cid)].append((int(rid), cfg))
    return {cid: sorted(rows, key=lambda row: row[0]) for cid, rows in grouped.items() if len(rows) >= 2}

def _reminder_new_list_entries(day_key: str) -> list[tuple[str, int, object]]:
    groups = _reminder_group_map(day_key, enabled_only=False)
    grouped_ids = {rid for rows in groups.values() for rid, _cfg in rows}
    entries = []
    for cid, rows in groups.items():
        entries.append(('group', min((rid for rid, _ in rows)), (cid, rows)))
    for rid, cfg in _reminder_items():
        if rid not in grouped_ids:
            entries.append(('item', int(rid), (int(rid), cfg)))
    entries.sort(key=lambda row: row[1])
    return entries

def _v177_legacy_0124_build_reminder_list_text() -> str:
    if not reminder_ui_new_enabled():
        return _BUILD_REMINDER_LIST_TEXT_V141()
    rows = _reminder_items()
    groups = _reminder_group_map(today_key(), enabled_only=False)
    enabled = sum((1 for _rid, cfg in rows if bool(cfg.get('enabled'))))
    return f'⏰ НАПОМИНАЛКИ · ПРОСТОЙ РЕЖИМ\n\nТекущих: {len(rows)} · активных: {enabled}\nОбъединённых чатов: {len(groups)}\nЗавершённых: {len(_reminder_completed_items())}\n\nНастройка идёт по шагам: текст → чаты → период → расписание → проверка.\nЕсли в одном чате несколько напоминалок, бот объединяет их в одно сообщение каждые 2 часа.'
try:
    _v177_legacy_0124_build_reminder_list_text.__name__ = 'build_reminder_list_text'
except Exception:
    pass

def _v177_legacy_0126_build_reminder_list_keyboard(day_key: str | None=None, page: int=0):
    if not reminder_ui_new_enabled():
        return _BUILD_REMINDER_LIST_KEYBOARD_V141(day_key, page)
    day_key = str(day_key or today_key())
    entries = _reminder_new_list_entries(day_key)
    pages = max(1, (len(entries) + _REMINDER_LIST_PAGE_SIZE - 1) // _REMINDER_LIST_PAGE_SIZE)
    page = max(0, min(int(page or 0), pages - 1))
    kb = types.InlineKeyboardMarkup(row_width=1)
    kb.row(IB('+добавить⏰', callback_data=f'rem:add:{page}:{day_key}'))
    start = page * _REMINDER_LIST_PAGE_SIZE
    for kind, _order, payload in entries[start:start + _REMINDER_LIST_PAGE_SIZE]:
        if kind == 'group':
            cid, members = payload
            title = chat_button_title(int(cid)) if 'chat_button_title' in globals() else get_chat_display_name(int(cid))
            active = sum((1 for _rid, cfg in members if bool(cfg.get('enabled'))))
            label = pad_button_label_41(f'👥 {title} · {len(members)} шт · {active} акт')
            kb.row(IB(label, callback_data=f'rem:group_open:{int(cid)}:{page}:{day_key}'))
        else:
            rid, cfg = payload
            pos = _reminder_position(rid) or rid
            kb.row(IB(_reminder_button_label(pos, cfg), callback_data=f'rem:open:{rid}:{page}:{day_key}'))
    if pages > 1:
        nav = []
        if page > 0:
            nav.append(IB('⬅️', callback_data=f'rem:list:{page - 1}:{day_key}'))
        nav.append(IB(f'{page + 1}/{pages}', callback_data='none'))
        if page + 1 < pages:
            nav.append(IB('➡️', callback_data=f'rem:list:{page + 1}:{day_key}'))
        kb.row(*nav)
    kb.row(IB(f'✅ Завершённые ({len(_reminder_completed_items())})', callback_data='rem:completed:0:0'))
    kb.row(IB('⬅️ Назад', callback_data=f'd:{day_key}:back_main'))
    return kb
try:
    _v177_legacy_0126_build_reminder_list_keyboard.__name__ = 'build_reminder_list_keyboard'
except Exception:
    pass

def _reminder_step_state(cfg: dict) -> list[str]:
    return ['✅' if str(cfg.get('text') or '').strip() else '❌', '✅' if cfg.get('chat_ids') or [] else '❌', '✅' if int(cfg.get('interval_minutes', 0) or 0) >= 5 else '❌', '✅' if str(cfg.get('start_date') or '').strip() else '❌']

def _v177_legacy_0128_build_reminder_menu_text(reminder_id: int) -> str:
    if not reminder_ui_new_enabled():
        return _BUILD_REMINDER_MENU_TEXT_V141(reminder_id)
    cfg = _reminder_cfg(reminder_id)
    if not cfg:
        return '⏰ Напоминалка не найдена.'
    steps = _reminder_step_state(cfg)
    preview = re.sub('\\s+', ' ', str(cfg.get('text') or '').strip())
    if len(preview) > 110:
        preview = preview[:107] + '...'
    state = '✅ АКТИВНО' if cfg.get('enabled') and (not _reminder_is_completed(cfg)) else '⬜ ВЫКЛЮЧЕНО'
    if _reminder_is_completed(cfg):
        state = '✅ ЗАВЕРШЕНО'
    return f"⏰ НАПОМИНАЛКА №{_reminder_position(reminder_id) or reminder_id}\n\n{steps[0]} 1. Текст: {preview or 'не задан'}\n{steps[1]} 2. Чаты: {len(cfg.get('chat_ids') or [])}\n{steps[2]} 3. Период: {_reminder_interval_label(cfg.get('interval_minutes', 120))}\n{steps[3]} 4. Расписание: {_reminder_fmt_date(cfg.get('start_date'))} · {int(cfg.get('start_hour', 8)):02d}:00–{int(cfg.get('end_hour', 22)):02d}:59\n\nСостояние: {state}\nСледующая: {_reminder_fmt_dt(cfg.get('next_run_at'))}"
try:
    _v177_legacy_0128_build_reminder_menu_text.__name__ = 'build_reminder_menu_text'
except Exception:
    pass

def _v177_legacy_0130_build_reminder_menu_keyboard(reminder_id: int, day_key: str | None=None, page: int=0, viewer_chat_id: int | None=None):
    if not reminder_ui_new_enabled():
        return _BUILD_REMINDER_MENU_KEYBOARD_V141(reminder_id, day_key, page, viewer_chat_id)
    day_key = str(day_key or today_key())
    cfg = _reminder_cfg(reminder_id)
    kb = types.InlineKeyboardMarkup(row_width=2)
    if not cfg:
        kb.row(IB('⬅️ К напоминалкам', callback_data=_reminder_return_callback(page, day_key)))
        return kb
    kb.row(make_copy_or_inline_button('1️⃣ Текст', compose_reminder_text_insert_value(reminder_id, cfg.get('text') or ''), viewer_chat_id=viewer_chat_id), IB(f"2️⃣ Чаты · {len(cfg.get('chat_ids') or [])}", callback_data=f'rem:chats:{reminder_id}:0:{page}:{day_key}'))
    kb.row(IB(f"3️⃣ Период · {_reminder_interval_label(cfg.get('interval_minutes', 120))}", callback_data=f'rem:interval:{reminder_id}:{page}:{day_key}'), IB('4️⃣ Расписание', callback_data=f'rem:schedule:{reminder_id}:{page}:{day_key}'))
    kb.row(IB('5️⃣ Проверить и включить', callback_data=f'rem:preview:{reminder_id}:{page}:{day_key}'))
    try:
        merge_fn = globals().get('_v207_reminder_merge_mode')
        merge_mode = str(merge_fn(cfg, viewer_chat_id) if callable(merge_fn) else 'off')
    except Exception:
        merge_mode = 'off'
    merge_label = {'off': '🚫 Отдельно', 'smart': '🧠 SMART: объединять 2+', 'single': '📌 Всегда 1 сообщение'}.get(merge_mode, '🚫 Отдельно')
    try:
        complete_fn = globals().get('_v207_reminder_complete_button_enabled')
        complete_on = bool(complete_fn(cfg, viewer_chat_id)) if callable(complete_fn) else False
    except Exception:
        complete_on = False
    kb.row(IB(merge_label, callback_data=f'v149:rem:item_merge:{reminder_id}:{page}:{day_key}'))
    kb.row(IB(f"{('✅' if complete_on else '⬜')} Кнопка «Выполнить»: {('ВКЛ' if complete_on else 'ВЫКЛ')}", callback_data=f'v149:rem:item_complete:{reminder_id}:{page}:{day_key}'))
    if _reminder_is_completed(cfg):
        kb.row(IB('♻️ Возобновить', callback_data=f'rem:resume_confirm:{reminder_id}:{page}:{day_key}'), IB('Изменить📝', callback_data=f'rem:editmenu:{reminder_id}:{page}:{day_key}'))
    else:
        state_label = '✅ Активно' if cfg.get('enabled') else '⬜ Выключено'
        kb.row(IB(state_label, callback_data=f'rem:toggle:{reminder_id}:{page}:{day_key}'), IB('Изменить📝', callback_data=f'rem:editmenu:{reminder_id}:{page}:{day_key}'))
    kb.row(IB('⬅️ К напоминалкам', callback_data=_reminder_return_callback(page, day_key)))
    return kb
try:
    _v177_legacy_0130_build_reminder_menu_keyboard.__name__ = 'build_reminder_menu_keyboard'
except Exception:
    pass

def reminder_schedule_text(reminder_id: int) -> str:
    cfg = _reminder_cfg(reminder_id) or {}
    end = _reminder_fmt_date(cfg.get('end_date')) if cfg.get('end_date') else 'без конца'
    return f"4️⃣ РАСПИСАНИЕ\n\nДаты: {_reminder_fmt_date(cfg.get('start_date'))} → {end}\nВремя: {int(cfg.get('start_hour', 8)):02d}:00 → {int(cfg.get('end_hour', 22)):02d}:59"

def reminder_schedule_keyboard(reminder_id: int, page: int, day_key: str):
    cfg = _reminder_cfg(reminder_id) or {}
    kb = types.InlineKeyboardMarkup(row_width=2)
    kb.row(IB('📅 Даты', callback_data=f'rem:dates:{reminder_id}:{page}:{day_key}'))
    kb.row(IB(f"🕗 С {int(cfg.get('start_hour', 8)):02d}:00", callback_data=f'rem:hours:start:{reminder_id}:{page}:{day_key}'), IB(f"🕙 До {int(cfg.get('end_hour', 22)):02d}:59", callback_data=f'rem:hours:end:{reminder_id}:{page}:{day_key}'))
    kb.row(IB('⬅️ Назад', callback_data=f'rem:open:{reminder_id}:{page}:{day_key}'))
    return kb

def _reminder_preview_times(cfg: dict, count: int=3) -> list[datetime]:
    tmp = copy.deepcopy(cfg or {})
    now_dt = now_local()
    due = _reminder_parse_dt(tmp.get('next_run_at'))
    if due is None or due < now_dt:
        due = _reminder_next_valid_start(now_dt, tmp)
    out = []
    for _ in range(max(1, int(count))):
        if due is None:
            break
        out.append(due)
        _reminder_advance_after_send(due, tmp)
        due = _reminder_parse_dt(tmp.get('next_run_at'))
    return out

def reminder_preview_text(reminder_id: int) -> str:
    cfg = _reminder_cfg(reminder_id) or {}
    errors = []
    if not str(cfg.get('text') or '').strip():
        errors.append('не задан текст')
    if not (cfg.get('chat_ids') or []):
        errors.append('не выбран чат')
    times = _reminder_preview_times(cfg, 3)
    lines = ['5️⃣ ПРОВЕРКА НАПОМИНАЛКИ', '']
    lines.append('Сообщение:')
    lines.append('НАПОМИНАЛКА🕰️')
    lines.append(str(cfg.get('text') or 'не задано')[:900])
    lines += ['', 'Чаты:']
    for raw in (cfg.get('chat_ids') or [])[:12]:
        try:
            lines.append('• ' + get_chat_display_name(int(raw)))
        except Exception:
            pass
    lines += ['', 'Ближайшие отправки:']
    lines.extend(('• ' + dt.strftime('%d.%m %H:%M') for dt in times))
    if errors:
        lines += ['', '❌ Нельзя включить: ' + ', '.join(errors)]
    else:
        lines += ['', '✅ Настройки готовы.']
    return '\n'.join(lines)

def reminder_preview_keyboard(reminder_id: int, page: int, day_key: str, viewer_chat_id: int):
    cfg = _reminder_cfg(reminder_id) or {}
    kb = types.InlineKeyboardMarkup(row_width=1)
    valid = bool(str(cfg.get('text') or '').strip() and (cfg.get('chat_ids') or []))
    if valid:
        label = '✅ ВКЛ' if cfg.get('enabled') else '⬜ ВЫКЛ'
        kb.row(IB(label, callback_data=f'rem:toggle:{reminder_id}:{page}:{day_key}'))
    kb.row(IB('⬅️ Назад', callback_data=f'rem:open:{reminder_id}:{page}:{day_key}'))
    return kb

def _reminder_group_state_root() -> dict:
    return data.setdefault('_global_settings', {}).setdefault('reminder_groups_v142', {})

def _reminder_group_key(target_chat_id: int, day_key: str) -> str:
    return f'{str(day_key)}:{int(target_chat_id)}'

def reminder_group_text(target_chat_id: int, day_key: str) -> str:
    members = reminder_group_members(target_chat_id, day_key, enabled_only=False)
    active = sum((1 for _rid, cfg in members if bool(cfg.get('enabled'))))
    lines = ['👥 ОБЪЕДИНЁННАЯ НАПОМИНАЛКА', '', f'Чат: {get_chat_display_name(int(target_chat_id))}', f'Напоминалок: {len(members)} · активных: {active}', 'Общий ритм при совместной работе: каждые 2 часа.', '']
    for idx, (_rid, cfg) in enumerate(members, 1):
        text = re.sub('\\s+', ' ', str(cfg.get('text') or 'без текста').strip())
        lines.append(f'{idx}. {text[:180]}')
    lines += ['', 'Можно открыть каждую отдельно или применить общие настройки ко всем.']
    return '\n'.join(lines)

def reminder_group_keyboard(target_chat_id: int, page: int, day_key: str):
    members = reminder_group_members(target_chat_id, day_key, enabled_only=False)
    kb = types.InlineKeyboardMarkup(row_width=1)
    for idx, (rid, cfg) in enumerate(members, 1):
        kb.row(IB(_reminder_button_label(idx, cfg), callback_data=f'rem:open:{rid}:{page}:{day_key}'))
    any_disabled = any((not bool(cfg.get('enabled')) for _rid, cfg in members))
    kb.row(IB('⬜ Все напоминания' if any_disabled else '✅ Все напоминания', callback_data=f'rem:group_toggle:{int(target_chat_id)}:{page}:{day_key}'))
    kb.row(IB('🔁 Всем каждые 2 часа', callback_data=f'rem:group_set2h:{int(target_chat_id)}:{page}:{day_key}'))
    kb.row(IB('🧩 Настройки первой → всем', callback_data=f'rem:group_sync:{int(target_chat_id)}:{page}:{day_key}'))
    kb.row(IB('🧪 Напомнить сейчас', callback_data=f'rem:group_test:{int(target_chat_id)}:{page}:{day_key}'))
    kb.row(IB('⬅️ К напоминалкам', callback_data=f'rem:list:{page}:{day_key}'))
    return kb

def reminder_group_set_two_hours(target_chat_id: int, day_key: str) -> None:
    with _REMINDER_CONFIG_LOCK:
        for _rid, cfg in reminder_group_members(target_chat_id, day_key, enabled_only=False):
            cfg['interval_minutes'] = _REMINDER_GROUP_INTERVAL_MINUTES
            if cfg.get('enabled'):
                _reminder_rearm_after_interval_v243(cfg, preserve_future=False)
            _reminder_touch(cfg)
    _reminder_save('reminder_group_2h')

def reminder_group_sync_from_first(target_chat_id: int, day_key: str) -> None:
    with _REMINDER_CONFIG_LOCK:
        members = reminder_group_members(target_chat_id, day_key, enabled_only=False)
        if not members:
            return
        src = members[0][1]
        shared = {'start_date': src.get('start_date') or today_key(), 'end_date': src.get('end_date') or '', 'start_hour': int(src.get('start_hour', 8)), 'end_hour': int(src.get('end_hour', 22)), 'interval_minutes': _REMINDER_GROUP_INTERVAL_MINUTES}
        for _rid, cfg in members:
            cfg.update(shared)
            if cfg.get('enabled'):
                _reminder_rearm_after_interval_v243(cfg, preserve_future=False)
            _reminder_touch(cfg)
    _reminder_save('reminder_group_sync')

def reminder_group_toggle_all(target_chat_id: int, day_key: str) -> None:
    with _REMINDER_CONFIG_LOCK:
        members = reminder_group_members(target_chat_id, day_key, enabled_only=False)
        enable = any((not bool(cfg.get('enabled')) for _rid, cfg in members))
        for _rid, cfg in members:
            if enable and str(cfg.get('text') or '').strip():
                if _reminder_is_completed(cfg):
                    continue
                cfg['enabled'] = True
                cfg['interval_minutes'] = _REMINDER_GROUP_INTERVAL_MINUTES
                _reminder_rearm_after_interval_v243(cfg, preserve_future=False)
            elif not enable:
                cfg['enabled'] = False
                cfg['next_run_at'] = ''
            _reminder_touch(cfg)
    _reminder_save('reminder_group_toggle')

def _reminder_group_message_text(members: list[tuple[int, dict]]) -> str:
    lines = ['НАПОМИНАЛКА🕰️', '']
    budget = 3850
    for idx, (_rid, cfg) in enumerate(members, 1):
        text = str(cfg.get('text') or '').strip()
        block = f'{idx}. {text}'
        if sum((len(x) + 1 for x in lines)) + len(block) > budget:
            remain = max(0, budget - sum((len(x) + 1 for x in lines)) - 2)
            if remain:
                lines.append(block[:remain] + '…')
            break
        lines.append(block)
    return '\n'.join(lines)

def _reminder_group_next_time(now_dt: datetime, members: list[tuple[int, dict]]):
    candidate = now_dt + timedelta(minutes=_REMINDER_GROUP_INTERVAL_MINUTES)
    for _ in range(16):
        if any((_reminder_date_allowed(candidate, cfg) and _reminder_time_allowed(candidate, cfg) for _rid, cfg in members)):
            return candidate
        next_day = candidate.date() + timedelta(days=1)
        start_hour = min((int(cfg.get('start_hour', 8)) for _rid, cfg in members))
        candidate = datetime.combine(next_day, datetime.min.time(), tzinfo=now_dt.tzinfo).replace(hour=start_hour)
    return None

def _v177_legacy_0134_reminder_group_delete_message(target_chat_id: int, message_id: int) -> None:
    if not message_id:
        return
    try:
        bot.delete_message(int(target_chat_id), int(message_id))
    except Exception:
        pass
try:
    _v177_legacy_0134_reminder_group_delete_message.__name__ = '_reminder_group_delete_message'
except Exception:
    pass

def _v177_legacy_0135_reminder_group_send_job(target_chat_id: int, day_key: str, force: bool=False) -> None:
    target_chat_id = int(target_chat_id)
    day_key = str(day_key or today_key())
    now_dt = now_local()
    with _REMINDER_CONFIG_LOCK:
        members = reminder_group_members(target_chat_id, day_key, enabled_only=not force)
        if not force:
            members = [row for row in members if _reminder_date_allowed(now_dt, row[1]) and _reminder_time_allowed(now_dt, row[1]) and _reminder_due_now(row[1], now_dt)]
        if len(members) < 2:
            return
        state = _reminder_group_state_root().setdefault(_reminder_group_key(target_chat_id, day_key), {})
        old_group_mid = int(state.get('last_message_id') or 0)
        old_individual = []
        for _rid, cfg in members:
            old = (cfg.get('last_message_ids') or {}).pop(str(target_chat_id), None)
            if old:
                old_individual.append(int(old))
        snapshot = [(rid, copy.deepcopy(cfg)) for rid, cfg in members]
    try:
        sent = bot.send_message(target_chat_id, _reminder_group_message_text(snapshot))
    except Exception as exc:
        log_error(f'reminder group send {target_chat_id}: {exc}')
        with _REMINDER_GROUP_LOCK:
            state = _reminder_group_state_root().setdefault(_reminder_group_key(target_chat_id, day_key), {})
            state['next_run_at'] = (now_dt + timedelta(minutes=5)).isoformat(timespec='seconds')
            state['last_error'] = str(exc)[:300]
        _reminder_save('reminder_group_retry')
        return
    for mid in set(old_individual + ([old_group_mid] if old_group_mid else [])):
        if mid and int(mid) != int(sent.message_id):
            _reminder_group_delete_message(target_chat_id, mid)
    next_dt = _reminder_group_next_time(now_dt, snapshot)
    with _REMINDER_CONFIG_LOCK:
        state = _reminder_group_state_root().setdefault(_reminder_group_key(target_chat_id, day_key), {})
        state.update({'target_chat_id': target_chat_id, 'day_key': day_key, 'member_ids': [rid for rid, _cfg in snapshot], 'last_message_id': int(sent.message_id), 'last_sent_at': now_dt.isoformat(timespec='seconds'), 'next_run_at': next_dt.isoformat(timespec='seconds') if next_dt else '', 'last_error': ''})
        for rid, _old_cfg in snapshot:
            cfg = _reminder_cfg(rid)
            if not cfg:
                continue
            cfg['last_sent_at'] = now_dt.isoformat(timespec='seconds')
            cfg['next_run_at'] = next_dt.isoformat(timespec='seconds') if next_dt else ''
            cfg['interval_minutes'] = _REMINDER_GROUP_INTERVAL_MINUTES
            _reminder_touch(cfg)
    _reminder_save('reminder_group_sent')
    try:
        bot_journal('reminder_group_sent', target_chat_id, f'members={[rid for rid, _ in snapshot]} message_id={sent.message_id}')
    except Exception:
        pass
try:
    _v177_legacy_0135_reminder_group_send_job.__name__ = '_reminder_group_send_job'
except Exception:
    pass

def _reminder_finance_priority_busy() -> bool:
    try:
        for pool in (FINANCE_TASK_POOL, FIN_FORWARD_TASK_POOL):
            st = pool.stats()
            if int(st.get('pending', 0) or 0) > 0 or int(st.get('active', 0) or 0) > 0:
                return True
    except Exception:
        pass
    return False

def _reminder_cleanup_stale_groups(active_keys: set[str]) -> None:
    root = _reminder_group_state_root()
    for key in list(root.keys()):
        if key in active_keys:
            continue
        row = root.pop(key, {}) or {}
        mid = int(row.get('last_message_id') or 0)
        cid = int(row.get('target_chat_id') or 0)
        if mid and cid:
            pool = globals().get('GENERAL_TASK_POOL')
            if pool:
                pool.submit_unique(f'reminder-group-clean:{cid}:{mid}', _reminder_group_delete_message, cid, mid)

def _v177_legacy_0133_reminder_tick() -> None:
    """Old mode sends every reminder individually; new mode groups only reminders due now.

    A configured same-day group no longer suppresses a single reminder whose partner is not
    currently due or is outside its active hours. Finance has a bounded 60-second priority
    window so reminders cannot starve forever.
    """
    global _REMINDER_FINANCE_BUSY_SINCE
    now_dt = now_local()
    day_key = now_dt.strftime('%Y-%m-%d')
    finance_busy = _reminder_finance_priority_busy()
    if finance_busy:
        if not _REMINDER_FINANCE_BUSY_SINCE:
            _REMINDER_FINANCE_BUSY_SINCE = time.monotonic()
        busy_for = time.monotonic() - _REMINDER_FINANCE_BUSY_SINCE
        if busy_for < _REMINDER_FINANCE_PRIORITY_GRACE_SECONDS:
            return
        try:
            bot_journal('reminder_finance_priority_expired', None, f'busy_for={busy_for:.1f}s; overdue reminders allowed')
        except Exception:
            pass
    else:
        _REMINDER_FINANCE_BUSY_SINCE = 0.0
    completed_changed = False
    due_rows = []
    with _REMINDER_CONFIG_LOCK:
        for rid, cfg in _reminder_items():
            if _reminder_end_has_passed(cfg, now_dt):
                _reminder_mark_completed(rid, cfg, 'end_date_finished', delete_messages=True)
                completed_changed = True
                continue
            try:
                if _reminder_due_now(cfg, now_dt):
                    due_rows.append((int(rid), cfg))
            except Exception as exc:
                log_error(f'reminder {rid} due check: {exc}')
    if not reminder_ui_new_enabled():
        _reminder_cleanup_stale_groups(set())
        for rid, _cfg in due_rows:
            if not REMINDER_TASK_POOL.submit_unique(f'reminder:{rid}', _reminder_tick_job, rid):
                bot_journal('reminder_dispatch_coalesced', None, f'reminder_id={rid}')
        if completed_changed:
            _reminder_save('reminder_completed_tick')
        return
    configured_groups = _reminder_group_map(day_key, enabled_only=True)
    active_group_keys = {_reminder_group_key(cid, day_key) for cid in configured_groups}
    _reminder_cleanup_stale_groups(active_group_keys)
    due_by_chat = defaultdict(list)
    for rid, cfg in due_rows:
        cid = _reminder_single_chat_id(cfg)
        if cid is None:
            continue
        if _reminder_date_allowed(now_dt, cfg) and _reminder_time_allowed(now_dt, cfg):
            due_by_chat[int(cid)].append((rid, cfg))
    grouped_ids = set()
    grouped_count = 0
    for cid, members in due_by_chat.items():
        if len(members) < 2:
            continue
        grouped_ids.update((rid for rid, _cfg in members))
        grouped_count += 1
        REMINDER_TASK_POOL.submit_unique(f'reminder-group:{cid}:{day_key}', _reminder_group_send_job, cid, day_key, False)
    individual_count = 0
    for rid, _cfg in due_rows:
        if rid in grouped_ids:
            continue
        individual_count += 1
        if not REMINDER_TASK_POOL.submit_unique(f'reminder:{rid}', _reminder_tick_job, rid):
            bot_journal('reminder_dispatch_coalesced', None, f'reminder_id={rid}')
    if due_rows:
        try:
            bot_journal('reminder_tick_dispatch', None, f'mode=new due={len(due_rows)} groups={grouped_count} individual={individual_count} finance_busy={int(finance_busy)}')
        except Exception:
            pass
    if completed_changed:
        _reminder_save('reminder_completed_tick')
try:
    _v177_legacy_0133_reminder_tick.__name__ = '_reminder_tick'
except Exception:
    pass

# --- ИСТОЧНИК: 40_message_router.py ---
@bot.message_handler(func=lambda m: not (m.text and m.text.startswith('/')), content_types=['text', 'photo', 'video', 'animation', 'audio', 'voice', 'video_note', 'document', 'sticker', 'location', 'venue', 'contact', 'dice', 'poll', 'game', 'story', 'paid_media', 'invoice'])
def on_any_message(msg):
    chat_id = msg.chat.id
    # R47 FINALIZATION: task input/auto hooks are inline; no message-handler wrappers.
    try:
        fn = globals().get('_v174_handle_own_input')
        if callable(fn) and fn(msg):
            return
    except Exception as exc:
        try: log_error(f'v174 keyword input: {exc}')
        except Exception: pass
    try:
        fn = globals().get('_v174_auto_process')
        if callable(fn): fn(msg)
    except Exception as exc:
        try: log_error(f'v174 auto process: {exc}')
        except Exception: pass
    try:
        fn = globals().get('_v172_task_message_input')
        if callable(fn) and fn(msg):
            return
    except Exception as exc:
        try: log_error(f'v172 task input: {exc}')
        except Exception: pass
    # R29: RAM-only input-source gate. Never wait for SQLite/Redis/network here.
    try:
        _r29_gate = globals().get('r29_inbound_message_allowed')
        if callable(_r29_gate):
            _r29_allowed, _r29_reason = _r29_gate(msg)
            if not _r29_allowed:
                try: bot_journal('r29_input_source_skip', chat_id, f'reason={_r29_reason}; message_id={int(getattr(msg, "message_id", 0) or 0)}')
                except Exception: pass
                return
    except Exception:
        pass
    if is_owner_chat(chat_id):
        finance_active_chats.add(chat_id)
    try:
        update_chat_info_from_message(msg)
    except Exception:
        pass
    try:
        bot_journal('message_received', chat_id, describe_msg_for_log(msg))
    except Exception:
        pass
    if msg.content_type == 'document':
        try:
            _restore_chat = globals().get('restore_mode')
            _doc = getattr(msg, 'document', None)
            _fname = str(getattr(_doc, 'file_name', '') or '').lower()
            _restore_ext = _fname.endswith(('.json', '.ison', '.csv', '.gz'))
            _owner_json_prompt = _restore_chat is None and is_owner_chat(chat_id) and _fname.endswith(('.json', '.ison'))
            if _restore_chat is not None and int(_restore_chat) == int(chat_id) and _restore_ext or _owner_json_prompt:
                _restore_doc_handler = globals().get('handle_document')
                if callable(_restore_doc_handler):
                    bot_journal('restore_document_routed_v183', chat_id, f'file={_fname}; mode={_restore_chat}')
                    return _restore_doc_handler(msg)
                raise RuntimeError('restore document handler is unavailable')
        except Exception as _restore_route_exc:
            log_error(f'v183 restore document route failed: {_restore_route_exc}')
            try:
                send_and_auto_delete(chat_id, f'❌ Файл восстановления не обработан: {_restore_route_exc}', 15)
            except Exception:
                pass
            return
    if msg.content_type == 'text':
        try:
            fn = globals().get('handle_journal_filename_input')
            if callable(fn) and fn(msg):
                return
        except Exception as _journal_name_exc:
            log_error(f'journal filename route: {_journal_name_exc}')
    if msg.content_type == 'text':
        try:
            _keepalive_input = globals().get('keepalive_handle_message')
            if callable(_keepalive_input) and _keepalive_input(msg):
                return
        except Exception as _keepalive_input_exc:
            log_error(f'v205 keepalive input route: {_keepalive_input_exc}')
        try:
            _constructor_input = globals().get('ui_constructor_handle_message')
            if callable(_constructor_input) and _constructor_input(msg):
                return
        except Exception as _constructor_input_exc:
            log_error(f'v205 constructor input route: {_constructor_input_exc}')
    try:
        _tenant_google_input = globals().get('tenant_google_handle_message')
        if callable(_tenant_google_input) and _tenant_google_input(msg):
            return
    except Exception as e:
        log_error(f'tenant google input handler error: {e}')
    if handle_secret_full_edit_reply(msg):
        return
    if handle_secret_sequence(msg):
        return
    if handle_secret_edit_insert_message(msg):
        return
    if handle_secret_input_message(msg):
        return
    try:
        if not getattr(getattr(msg, 'from_user', None), 'is_bot', False):
            bump_quick_balance_recreate_counter(chat_id)
    except Exception:
        pass
    if msg.content_type == 'text':
        try:
            if handle_secret_note_message(msg):
                return
            if handle_direct_edit_insert_message(msg):
                return
            if handle_gomonk_insert_message(msg):
                return
            if handle_category_edit_message(msg):
                return
            if handle_category_add_message(msg):
                return
        except Exception as e:
            log_error(f'secret/category_add/edit/direct-edit message handler error: {e}')
    if msg.content_type == 'text':
        try:
            store = get_chat_store(chat_id)
            if store.get('reset_wait'):
                text_up = (msg.text or '').strip().upper()
                if text_up == 'ДА':
                    _durable_note_source_consumed('reset_wait')
                    store['reset_wait'] = False
                    store['reset_time'] = 0
                    save_data(data)
                    cleanup_forward_links(chat_id)
                    reset_chat_data(chat_id)
                    send_and_auto_delete(chat_id, '✅ Данные чата обнулены.', 10)
                    try:
                        bot.delete_message(chat_id, msg.message_id)
                    except Exception:
                        pass
                    return
        except Exception as e:
            log_error(f'reset_wait handler error: {e}')
    if msg.content_type == 'text':
        try:
            store = get_chat_store(chat_id)
            finwin_reset_wait = store.get('finwin_reset_wait')
            if finwin_reset_wait and finwin_reset_wait.get('type') == 'finwin_reset':
                text_up = (msg.text or '').strip().upper()
                target_chat_id = int(finwin_reset_wait.get('target_chat_id'))
                fin_window_msg_id = finwin_reset_wait.get('fin_window_msg_id')
                owner_day_key = finwin_reset_wait.get('owner_day_key') or today_key()
                if text_up == 'ДА':
                    _durable_note_source_consumed('finwin_reset_wait')
                    store['finwin_reset_wait'] = None
                    save_data(data)
                    cleanup_forward_links(target_chat_id)
                    reset_chat_data(target_chat_id)
                    send_and_auto_delete(chat_id, f'✅ Данные чата {get_chat_display_name(target_chat_id)} обнулены.', 10)
                    try:
                        bot.delete_message(chat_id, msg.message_id)
                    except Exception:
                        pass
                    if fin_window_msg_id:
                        try:
                            safe_txt = render_fin_window_text(target_chat_id, today_key())
                            bot.edit_message_text(safe_txt, chat_id=chat_id, message_id=int(fin_window_msg_id), reply_markup=build_fin_window_view_keyboard(target_chat_id, today_key(), owner_day_key), parse_mode='HTML')
                        except Exception as e:
                            log_error(f'finwin reset refresh failed: {e}')
                    return
                elif text_up in {'НЕТ', 'ОТМЕНА', 'CANCEL'}:
                    _durable_note_source_consumed('finwin_reset_wait')
                    store['finwin_reset_wait'] = None
                    save_data(data)
                    send_and_auto_delete(chat_id, '❎ Обнуление отменено.', 8)
                    try:
                        bot.delete_message(chat_id, msg.message_id)
                    except Exception:
                        pass
                    return
        except Exception as e:
            log_error(f'finwin_reset_wait handler error: {e}')
    if msg.content_type == 'text':
        try:
            store = get_chat_store(chat_id)
            wait = store.get('finance_toggle_wait')
            if wait:
                text_up = (msg.text or '').strip().upper()
                if text_up == 'ДА':
                    _durable_note_source_consumed('finance_toggle_wait')
                    target_chat_id = int(wait.get('target_chat_id'))
                    set_finance_mode(target_chat_id, not is_finance_mode(target_chat_id))
                    store['finance_toggle_wait'] = None
                    save_data(data)
                    send_and_auto_delete(chat_id, f'💰 Финансовый режим для {get_chat_display_name(target_chat_id)}: {format_finance_mode_label(target_chat_id)}', 10)
                    try:
                        bot.delete_message(chat_id, msg.message_id)
                    except Exception:
                        pass
                    return
                elif text_up in {'НЕТ', 'ОТМЕНА', 'CANCEL'}:
                    _durable_note_source_consumed('finance_toggle_wait')
                    store['finance_toggle_wait'] = None
                    save_data(data)
                    send_and_auto_delete(chat_id, '❎ Переключение финансового режима отменено.', 8)
                    try:
                        bot.delete_message(chat_id, msg.message_id)
                    except Exception:
                        pass
                    return
        except Exception as e:
            log_error(f'finance_toggle_wait handler error: {e}')
    if restore_mode is not None and restore_mode == chat_id:
        return
    if msg.content_type == 'text':
        try:
            store = get_chat_store(chat_id)
            fwd_wait = store.get('forward_copy_edit_wait') or {}
            if fwd_wait.get('type') == 'forward_copy_edit':
                _durable_note_source_consumed('forward_copy_edit_wait')
                dst_msg_id = int(fwd_wait.get('dst_msg_id'))
                text = (msg.text or '').strip()
                if not edit_forward_copy_and_record(chat_id, dst_msg_id, text):
                    send_and_auto_delete(chat_id, '❌ Неверный формат или бот-копия не найдена. Пример: 1500 продукты', 10)
                    return
                _edited_rec = find_record_by_message_id(int(chat_id), int(dst_msg_id))
                if isinstance(_edited_rec, dict):
                    _durable_note_record_edit_witness(_durable_record_edit_witness(int(chat_id), int(_edited_rec.get('id')), amount=_edited_rec.get('amount', 0), note=_edited_rec.get('note', ''), source_finance_text=_edited_rec.get('source_finance_text', ''), usd_amount=_edited_rec.get('usd_amount') if _edited_rec.get('usd_amount') is not None else None, usd_note=_edited_rec.get('usd_note') if _edited_rec.get('usd_amount') is not None else None, kind='forward_copy_edit'))
                clear_forward_copy_edit_wait(chat_id, delete_prompt=True)
                try:
                    bot.delete_message(chat_id, msg.message_id)
                except Exception:
                    pass
                send_and_auto_delete(chat_id, '✅ Бот-копия и финансовая запись изменены.', 8)
                return
        except Exception as e:
            log_error(f'forward_copy_edit_wait handler error: {e}')
    if msg.content_type == 'text':
        try:
            store = get_chat_store(chat_id)
            finwin_wait = store.get('finwin_edit_wait')
            if finwin_wait and finwin_wait.get('type') == 'finwin_edit':
                _durable_note_source_consumed('finwin_edit_wait')
                text = sanitize_telegram_inserted_text((msg.text or '').strip())
                target_chat_id = int(finwin_wait.get('target_chat_id'))
                rid = int(finwin_wait.get('rid'))
                day_key = finwin_wait.get('day_key') or today_key()
                owner_day_key = finwin_wait.get('owner_day_key') or today_key()
                fin_window_msg_id = finwin_wait.get('fin_window_msg_id')
                usd_mode = bool(finwin_wait.get('usd_mode')) or usd_transactions_view_enabled(target_chat_id)
                try:
                    if usd_mode:
                        amount, note = parse_usd_edit_value(text)
                    else:
                        amount, note = split_amount_and_note(text)
                except Exception:
                    example = '100 USD продукты' if usd_mode else '1500 продукты'
                    send_and_auto_delete(chat_id, f'❌ Неверный формат. Пример: {example}', 10)
                    return
                if usd_mode:
                    target_store = get_chat_store(target_chat_id)
                    rec = next((r for r in target_store.get('records', []) if int(r.get('id', -1)) == rid), None)
                    ok = bool(rec is not None and callable(globals().get('apply_linked_finance_edit_v262')) and apply_linked_finance_edit_v262(
                        target_chat_id, rec, update_ars=False, replace_usd=True, usd_amount=float(amount),
                        usd_note=str(note or rec.get('usd_note') or rec.get('note') or ''),
                        usd_only=bool(rec.get('usd_only', False) and (not float(rec.get('amount', 0) or 0))),
                        source_text=None, full_text_replace=False, repaint_copies=True, source_kind='finwin_edit_usd'))
                else:
                    ok = update_record_in_chat(target_chat_id, rid, amount, note, source_finance_text=text)
                if ok:
                    if usd_mode:
                        _durable_note_record_edit_witness(_durable_record_edit_witness(target_chat_id, rid, usd_amount=amount, usd_note=note, kind='finwin_edit_usd'))
                    else:
                        _durable_note_record_edit_witness(_durable_record_edit_witness(target_chat_id, rid, amount=amount, note=note, source_finance_text=text, kind='finwin_edit'))
                clear_finwin_edit_wait_state(chat_id, delete_prompt=True)
                try:
                    bot.delete_message(chat_id, msg.message_id)
                except Exception:
                    pass
                if not ok:
                    send_and_auto_delete(chat_id, '❌ Запись для редактирования не найдена.', 10)
                    return
                if fin_window_msg_id:
                    try:
                        edit_kb = build_usd_edit_records_keyboard(day_key, target_chat_id, prefix='fv', owner_day_key=owner_day_key) if usd_mode else build_edit_records_keyboard(day_key, target_chat_id, prefix='fv', owner_day_key=owner_day_key)
                        bot.edit_message_text(render_fin_window_text(target_chat_id, day_key), chat_id=chat_id, message_id=int(fin_window_msg_id), reply_markup=edit_kb, parse_mode='HTML')
                    except Exception as e:
                        log_error(f'finwin edit refresh failed: {e}')
                schedule_finalize(target_chat_id, day_key, delay=0.1)
                if usd_mode:
                    send_and_auto_delete(chat_id, f'✅ USD-запись обновлена: {fmt_num_plain(amount)} USD {note}', 8)
                else:
                    send_and_auto_delete(chat_id, f'✅ Запись обновлена: {fmt_num(amount)} {note}', 8)
                return
        except Exception as e:
            log_error(f'finwin_edit_wait handler error: {e}')
    if msg.content_type == 'text':
        try:
            store = get_chat_store(chat_id)
            edit_wait = store.get('edit_wait')
            if edit_wait and edit_wait.get('type') == 'edit':
                _durable_note_source_consumed('edit_wait')
                text = sanitize_telegram_inserted_text((msg.text or '').strip())
                if not text:
                    return
                try:
                    amount, note = split_amount_and_note(text)
                except Exception:
                    send_and_auto_delete(chat_id, '❌ Неверный формат.\nПример: 1500 продукты', 10)
                    return
                rid = edit_wait.get('rid')
                day_key = edit_wait.get('day_key') or store.get('current_view_day') or today_key()
                target = next((r for r in store.get('records', []) if r.get('id') == rid), None)
                if not target:
                    store['edit_wait'] = None
                    save_data(data)
                    send_and_auto_delete(chat_id, '❌ Запись для редактирования не найдена.', 10)
                    return
                ok = update_record_in_chat(chat_id, int(rid), amount, note, source_finance_text=text)
                if not ok:
                    send_and_auto_delete(chat_id, '❌ Запись для редактирования не найдена.', 10)
                    return
                _durable_note_record_edit_witness(_durable_record_edit_witness(chat_id, int(rid), amount=amount, note=note, source_finance_text=text, kind='edit_wait'))
                clear_edit_wait_state(chat_id)
                send_and_auto_delete(chat_id, f'✅ Запись R{rid} обновлена: {fmt_num(amount)} {note}', 10)
                try:
                    bot.delete_message(chat_id, msg.message_id)
                except Exception:
                    pass
                return
        except Exception as e:
            log_error(f'edit_wait handler error: {e}')
    if msg.content_type == 'text':
        try:
            if is_finance_mode(chat_id):
                handle_finance_text(msg)
        except Exception as e:
            log_error(f'handle_finance_text error: {e}')
    schedule_forward_any_message(chat_id, msg)

def _parse_explicit_usd_operations(text: str) -> list[dict]:
    """Извлекает явные суммы вида 300 USD / +1700 USD / USD 500 / US$ 500."""
    raw = str(text or '')
    patterns = [re.compile('(?P<num>[+-]?(?:\\d{1,3}(?:[ .]\\d{3})+|\\d+)(?:[.,]\\d+)?)\\s*(?P<cur>USD|U\\$S|US\\$)', re.I), re.compile('(?P<cur>USD|U\\$S|US\\$)\\s*(?P<num>[+-]?(?:\\d{1,3}(?:[ .]\\d{3})+|\\d+)(?:[.,]\\d+)?)', re.I)]
    found = []
    occupied = []
    for pat in patterns:
        for m in pat.finditer(raw):
            span = m.span()
            if any((not (span[1] <= a or span[0] >= b) for a, b in occupied)):
                continue
            try:
                amount = parse_amount(m.group('num'))
            except Exception:
                continue
            found.append({'amount': float(amount), 'span': span, 'raw': m.group(0)})
            occupied.append(span)
    found.sort(key=lambda x: x['span'][0])
    return found

def _text_without_spans(text: str, spans: list[tuple[int, int]]) -> str:
    chars = list(str(text or ''))
    for a, b in spans:
        for i in range(max(0, a), min(len(chars), b)):
            chars[i] = ' '
    return re.sub('\\s+', ' ', ''.join(chars)).strip()

def _base_add_currency_record(chat_id: int, ledger: str, amount: float, note: str, owner: int, source_msg=None, day_key: str | None=None):
    """Добавляет запись в ARS или USD, даже если этот контур сейчас не открыт на экране."""
    chat_id = int(chat_id)
    if globals().get('constitution_finance_write_blocked_v232') and constitution_finance_write_blocked_v232():
        raise RuntimeError('DATA CONSTITUTION: финансовые изменения заблокированы до восстановления целостности')
    ledger = 'usd' if str(ledger).lower() == 'usd' else 'ars'
    store = get_chat_store(chat_id)
    active = _ensure_currency_ledgers(store)
    if active == ledger:
        add_record_to_chat(chat_id, amount, note, owner, source_msg=source_msg, day_key=day_key)
        return
    if not day_key:
        day_key = day_key_from_message(source_msg)
    records_key = f'{ledger}_records'
    daily_key = f'{ledger}_daily_records'
    next_key = f'{ledger}_next_id'
    balance_key = f'{ledger}_balance'
    records = store.setdefault(records_key, [])
    daily = store.setdefault(daily_key, {})
    rid = int(store.get(next_key, 1) or 1)
    op_id = operation_begin('finance_add', chat_id, target=f'{ledger}:{rid}', payload={'amount': amount, 'note': note, 'currency': ledger}, critical=True) if 'operation_begin' in globals() else ''
    source_msg_id = getattr(source_msg, 'message_id', None) if source_msg else None
    source_order_msg_id = getattr(source_msg, 'source_order_msg_id', None) or getattr(source_msg, 'forward_source_msg_id', None) or source_msg_id
    rec = {'id': rid, 'short_id': '', 'timestamp': message_timestamp_iso(source_msg), 'amount': float(amount), 'note': str(note or '').strip().lower(), 'source_msg_id': source_msg_id, 'source_order_msg_id': source_order_msg_id, 'owner': owner, 'msg_id': source_msg_id, 'origin_msg_id': source_msg_id, 'day_key': day_key, 'currency': ledger.upper()}
    records.append(rec)
    records.sort(key=record_sort_key)
    store[next_key] = max([int(r.get('id', 0) or 0) for r in records] + [0]) + 1
    rebuilt = {}
    for r in records:
        rebuilt.setdefault(_record_day_key(r), []).append(r)
    store[daily_key] = rebuilt
    store[balance_key] = sum((float(r.get('amount', 0) or 0) for r in records))
    try:
        finance_cache_invalidate(chat_id, f'finance_add_{ledger}')
        finance_integrity_append(chat_id, 'add', rec, details={'currency': ledger})
    except Exception as _integrity_exc:
        log_error(f'finance currency add integrity: {_integrity_exc}')
    if op_id and 'operation_complete' in globals():
        operation_complete(op_id, f'record={rid} currency={ledger}')

def handle_finance_text(msg):
    """
    Обработка обычного ввода для финучёта.
    Теперь принимает сумму не только из text, но и из caption
    у фото/видео/документов/аудио и т.п.
    """
    chat_id = msg.chat.id
    if globals().get('constitution_finance_write_blocked_v232') and constitution_finance_write_blocked_v232():
        try:
            if _v198_primary_owner_chat(chat_id):
                send_and_auto_delete(chat_id, '🚨 DATA CONSTITUTION: финансовая запись временно отложена до проверки/восстановления. После снятия карантина Durable Tasks попробует безопасно завершить её. /data_constitution', 20)
            else:
                send_owner_technical_alert('🚨 DATA CONSTITUTION: финансовая запись временно отложена до проверки/восстановления. После снятия карантина Durable Tasks попробует безопасно завершить её. /data_constitution', 20, source_chat_id=chat_id)
                send_plain_and_auto_delete(chat_id, '⏳ Финансовая запись временно отложена до восстановления данных.', 8)
        except Exception:
            pass
        return True
    try:
        uid = int(getattr(getattr(msg, 'from_user', None), 'id', 0) or 0)
        if 'safety_profile_new_enabled' in globals() and safety_profile_new_enabled() and (not security_user_allowed(uid, 'finance_input')):
            send_and_auto_delete(chat_id, '⛔ У вас нет права добавлять финансовые записи.', 8)
            try:
                bot_journal('security_finance_input_blocked', chat_id, f'user={uid}', 'WARN')
            except Exception:
                pass
            return True
    except Exception:
        pass
    try:
        uid = int(getattr(getattr(msg, 'from_user', None), 'id', 0) or 0)
        if 'v152_chat_permission_allowed' in globals() and '_v152_actor_is_platform_owner' in globals():
            capability = 'finance.usd' if 'usd_transactions_view_enabled' in globals() and usd_transactions_view_enabled(chat_id) else 'finance.ars'
            if not _v152_actor_is_platform_owner(uid) and (not v152_chat_permission_allowed(chat_id, 'finance.mode') or not v152_chat_permission_allowed(chat_id, capability)):
                try:
                    send_and_auto_delete(chat_id, '⛔ Добавление финансовых операций запрещено правами этого чата.', 8)
                except Exception:
                    pass
                return True
    except Exception:
        pass
    bot_journal('finance_text_start', chat_id, describe_msg_for_log(msg))
    text = _message_text_for_finance(msg)
    if not text:
        return False
    if not is_finance_mode(chat_id):
        return False
    store = get_chat_store(chat_id)
    settings = store.get('settings', {})
    if not settings.get('auto_add', True):
        return False
    if not looks_like_amount(text):
        if text_has_any_digit(text):
            log_error(f'[FINANCE SKIP] amount not recognized: {describe_msg_for_log(msg)} text={text[:220]!r}')
        return False
    try:
        comp = parse_financial_components(text)
        amount, note = (comp['amount'], comp['note'])
    except Exception as e:
        log_error(f'[FINANCE PARSE ERROR] {describe_msg_for_log(msg)} text={text[:220]!r}: {e}')
        return False
    careful_forward = bool(careful_restore_active(chat_id))
    if careful_forward:
        try:
            fn = globals().get('canonical_main_day')
            entry_day = str(fn(chat_id) if callable(fn) else store.get('current_view_day') or finance_today_key(chat_id))[:10]
        except Exception:
            entry_day = str(store.get('current_view_day') or finance_today_key(chat_id))[:10]
        try:
            bot_journal('careful_restore_route', chat_id, f"msg={getattr(msg, 'message_id', 0)} day={entry_day}", 'INFO')
        except Exception:
            pass
    else:
        entry_day = finance_day_key_from_message(msg)
    try:
        rec = add_record_to_chat(chat_id, amount, note, getattr(getattr(msg, 'from_user', None), 'id', 0), source_msg=msg, day_key=entry_day, usd_amount=comp.get('usd_amount'), usd_note=comp.get('usd_note', ''), usd_only=comp.get('usd_only', False), source_finance_text=comp.get('source_finance_text', text))
        if careful_forward:
            careful_restore_touch_value(chat_id, entry_day, msg=msg, record=rec)
        # R15: repaint from the already committed in-memory/SQLite record immediately.
        # Heavy normalize/Gomonk/global finalize remains detached in FINANCE_TASK_POOL.
        try:
            schedule_financial_window_refresh(chat_id, entry_day, reason='record_commit_fast_r15', delay=0.01)
        except Exception:
            pass
        schedule_finalize(chat_id, entry_day)
        return True
    except Exception as e:
        log_error(f'[FINANCE ADD ERROR] {describe_msg_for_log(msg)} amount={amount} note={note!r}: {e}')
        return False

def handle_finance_edit(msg):
    chat_id = msg.chat.id
    try:
        uid = int(getattr(getattr(msg, 'from_user', None), 'id', 0) or 0)
        if 'v152_chat_permission_allowed' in globals() and '_v152_actor_is_platform_owner' in globals():
            if not _v152_actor_is_platform_owner(uid) and (not v152_chat_permission_allowed(chat_id, 'finance.edit')):
                try:
                    send_and_auto_delete(chat_id, '⛔ Редактирование операций запрещено правами этого чата.', 8)
                except Exception:
                    pass
                return False
    except Exception:
        pass
    if globals().get('constitution_finance_write_blocked_v232') and constitution_finance_write_blocked_v232():
        try:
            if _v198_primary_owner_chat(chat_id):
                send_and_auto_delete(chat_id, '🚨 DATA CONSTITUTION: финансовые изменения временно заблокированы. Используйте /data_constitution.', 20)
            else:
                send_owner_technical_alert('🚨 DATA CONSTITUTION: финансовые изменения временно заблокированы. Используйте /data_constitution.', 20, source_chat_id=chat_id)
                send_plain_and_auto_delete(chat_id, '⏳ Финансовая запись временно отложена до восстановления данных.', 8)
        except Exception:
            pass
        return True
    text = (msg.text or msg.caption or '').strip()
    store = get_chat_store(chat_id)
    target = find_record_by_message_id(chat_id, int(msg.message_id)) if 'find_record_by_message_id' in globals() else None
    if target is None:
        for r in store.get('records', []):
            try:
                if any(int(r.get(k) or 0) == int(msg.message_id) for k in ('source_msg_id','origin_msg_id','msg_id','source_order_msg_id')):
                    target = r
                    break
            except Exception:
                continue
    if isinstance(target, dict) and '_remember_finance_source_identity_v257' in globals():
        _remember_finance_source_identity_v257(int(chat_id), target, int(msg.message_id), 'records')
    if not target:
        log_info(f'[EDIT-FIN] record not found for msg_id={msg.message_id}')
        return False
    if text and looks_like_amount(text):
        try:
            comp = parse_financial_components(text)
            amount, note = (comp['amount'], comp['note'])
        except Exception:
            comp = {'usd_amount': 0.0, 'usd_note': '', 'usd_only': False}
            amount, note = (0, 'удалено')
    else:
        comp = {'usd_amount': 0.0, 'usd_note': '', 'usd_only': False}
        amount, note = (0, 'удалено')
    _constitution_before = copy.deepcopy(target)
    _next_source_text = str(comp.get('source_finance_text') or text)
    _next_usd_amount = float(comp.get('usd_amount') or 0) if comp.get('usd_amount') is not None else 0.0
    _next_usd_note = str(comp.get('usd_note') or '') if comp.get('usd_amount') is not None else ''
    _next_usd_only = bool(comp.get('usd_only', False)) if comp.get('usd_amount') is not None else False
    _same_edit = (
        float(target.get('amount') or 0) == float(amount or 0)
        and str(target.get('note') or '') == str(note or '')
        and str(target.get('source_finance_text') or '') == _next_source_text
        and float(target.get('usd_amount') or 0) == _next_usd_amount
        and str(target.get('usd_note') or '') == _next_usd_note
        and bool(target.get('usd_only', False)) == _next_usd_only
    )
    if _same_edit:
        log_info(f"[EDIT-FIN] no-op duplicate R{target.get('id')} ARS={float(amount or 0)} USD={_next_usd_amount} note={note}")
        return True
    target['amount'] = amount
    target['note'] = note
    target['source_finance_text'] = _next_source_text
    if comp.get('usd_amount') is not None:
        target['usd_amount'] = float(comp.get('usd_amount') or 0)
        target['usd_note'] = str(comp.get('usd_note') or '')
        target['usd_only'] = bool(comp.get('usd_only', False))
    elif target.get('usd_amount') is not None:
        target['usd_amount'] = 0.0
        target['usd_note'] = ''
        target['usd_only'] = False
    for day, arr in store.get('daily_records', {}).items():
        for r in arr:
            if r.get('id') == target.get('id'):
                r.update(target)
    store['balance'] = sum((r['amount'] for r in store.get('records', [])))
    _snapshot_active_currency_ledger(store, _ensure_currency_ledgers(store))
    log_info(f"[EDIT-FIN] updated record R{target['id']} ARS={float(amount or 0)} USD={float(target.get('usd_amount') or 0)} usd_only={bool(target.get('usd_only', False))} note={note}")
    save_data(data, chat_ids=[int(chat_id)])
    try:
        finance_integrity_append(int(chat_id), 'edit', target, details={'before': _constitution_before, 'source': 'telegram_edited_message'})
    except Exception as _constitution_edit_exc:
        log_error(f'DATA CONSTITUTION edited finance ledger: {_constitution_edit_exc}')
    return True


def sync_forwarded_finance_message(dst_chat_id: int, dst_msg_id: int, text: str, owner: int=0, source_msg=None):
    """R48: exact finance sync without holding chat_lock over SQLite/network."""
    dst_chat_id = int(dst_chat_id); dst_msg_id = int(dst_msg_id)
    if not is_finance_mode(dst_chat_id):
        if text_has_any_digit(text):
            log_error(f'[FWD FINANCE SKIP] finance mode off: dst={get_chat_display_name(dst_chat_id)} msg={dst_msg_id} text={str(text)[:220]!r}')
        return False
    entry_day = finance_day_key_from_message(source_msg) if source_msg is not None else finance_today_key()
    comp = None; amount = note = None
    if text and looks_like_amount(text):
        try:
            comp = parse_financial_components(text); amount, note = comp['amount'], comp['note']
        except Exception as e:
            log_error(f'[FWD FINANCE PARSE ERROR] dst={get_chat_display_name(dst_chat_id)} msg={dst_msg_id} text={str(text)[:220]!r}: {e}')
            return False
    finder = globals().get('_v260_find_forward_finance_record')
    need_add = False; changed = False; before = None; result_rec = None
    with locked_chat(dst_chat_id):
        store = get_chat_store(dst_chat_id)
        existing = finder(dst_chat_id, dst_msg_id, source_msg) if callable(finder) else (find_record_by_message_id(dst_chat_id, dst_msg_id) if 'find_record_by_message_id' in globals() else None)
        before = copy.deepcopy(existing) if isinstance(existing, dict) else None
        result_rec = existing
        if comp is not None:
            if isinstance(existing, dict):
                old_amount = float(existing.get('amount', 0) or 0); old_usd = float(existing.get('usd_amount', 0) or 0)
                next_usd = float(comp.get('usd_amount') or 0) if comp.get('usd_amount') is not None else 0.0
                next_usd_note = str(comp.get('usd_note') or '') if comp.get('usd_amount') is not None else ''
                next_usd_only = bool(comp.get('usd_only', False)) if comp.get('usd_amount') is not None else False
                next_text = str(comp.get('source_finance_text') or text)
                changed = not (float(existing.get('amount') or 0)==float(amount or 0) and str(existing.get('note') or '')==str(note or '') and str(existing.get('source_finance_text') or '')==next_text and float(existing.get('usd_amount') or 0)==next_usd and str(existing.get('usd_note') or '')==next_usd_note and bool(existing.get('usd_only',False))==next_usd_only)
                if changed:
                    existing.update({'amount':amount,'note':note,'source_finance_text':next_text,'usd_amount':next_usd,'usd_note':next_usd_note,'usd_only':next_usd_only,'timestamp':message_timestamp_iso(source_msg)})
                    try: store['balance']=float(store.get('balance',0) or 0)+float(amount or 0)-old_amount
                    except Exception: pass
                    if '_usd_balance_cache_r16' in store:
                        try: store['_usd_balance_cache_r16']=float(store.get('_usd_balance_cache_r16',0) or 0)+next_usd-old_usd
                        except Exception: store.pop('_usd_balance_cache_r16',None)
                entry_day = existing.get('day_key') or entry_day
            else:
                need_add = True
        elif isinstance(existing, dict):
            changed = not (float(existing.get('amount') or 0)==0.0 and str(existing.get('note') or '')=='удалено' and float(existing.get('usd_amount') or 0)==0.0)
            if changed:
                old_amount=float(existing.get('amount',0) or 0); old_usd=float(existing.get('usd_amount',0) or 0)
                existing.update({'amount':0,'note':'удалено','source_finance_text':str(text or '').strip(),'usd_amount':0.0,'usd_note':'','usd_only':False})
                try: store['balance']=float(store.get('balance',0) or 0)-old_amount
                except Exception: pass
                if '_usd_balance_cache_r16' in store:
                    try: store['_usd_balance_cache_r16']=float(store.get('_usd_balance_cache_r16',0) or 0)-old_usd
                    except Exception: store.pop('_usd_balance_cache_r16',None)
            entry_day = existing.get('day_key') or entry_day
        else:
            if text_has_any_digit(text):
                log_error(f'[FWD FINANCE SKIP] amount not recognized: dst={get_chat_display_name(dst_chat_id)} msg={dst_msg_id} text={str(text)[:220]!r}')
            return False
        if isinstance(existing, dict):
            store['_finance_hotpath_pending_normalize_r16']=True
            store['_finance_fast_generation_r16']=int(store.get('_finance_fast_generation_r16',0) or 0)+1
            store.pop('_finance_day_balance_cache_r16',None)
    if need_add:
        shadow_msg = None
        if source_msg is not None and callable(globals().get('_v260_make_forward_shadow')):
            try:
                src_chat=int(getattr(getattr(source_msg,'chat',None),'id',0) or 0); src_mid=int(getattr(source_msg,'forward_source_msg_id',0) or getattr(source_msg,'message_id',0) or 0)
                shadow_msg=_v260_make_forward_shadow(src_chat,src_mid,dst_chat_id,dst_msg_id,owner,getattr(source_msg,'date',None))
            except Exception: shadow_msg=None
        if shadow_msg is None:
            shadow_msg=type('ForwardShadowMsg',(),{'message_id':dst_msg_id,'date':getattr(source_msg,'date',int(time.time())) if source_msg is not None else int(time.time()),'forward_source_msg_id':getattr(source_msg,'message_id',dst_msg_id) if source_msg is not None else dst_msg_id})()
        result_rec=add_record_to_chat(dst_chat_id,amount,note,owner,source_msg=shadow_msg,day_key=entry_day,usd_amount=comp.get('usd_amount'),usd_note=comp.get('usd_note',''),usd_only=comp.get('usd_only',False),source_finance_text=comp.get('source_finance_text',text))
        changed=True
    if isinstance(result_rec, dict):
        with locked_chat(dst_chat_id):
            store=get_chat_store(dst_chat_id)
            if callable(globals().get('_v260_bind_forward_finance_record')) and source_msg is not None:
                _v260_bind_forward_finance_record(result_rec,source_msg,dst_chat_id,dst_msg_id)
            try:
                _snapshot_active_currency_ledger(store,_ensure_currency_ledgers(store))
                for _ledger,_rec in _finance_record_lists(int(dst_chat_id)):
                    if isinstance(_rec,dict): ensure_finance_record_uid(int(dst_chat_id),_rec)
            except Exception: pass
        if 'persist_finance_chat_local_fast' in globals() and not persist_finance_chat_local_fast(dst_chat_id):
            log_error(f'[FWD FINANCE LOCAL PERSIST FAILED] dst={get_chat_display_name(dst_chat_id)} msg={dst_msg_id}')
            return False
        if changed and before is not None:
            try: finance_integrity_append(dst_chat_id,'edit',result_rec,details={'before':before,'source':'forwarded_edited_message_v260'})
            except Exception as exc: log_error(f'[FWD FIN V260] integrity edit: {exc}')
    if not isinstance(result_rec,dict):
        result_rec=find_record_by_message_id(dst_chat_id,dst_msg_id)
    try: refresh_active_forward_copy_edit_prompt(dst_chat_id,dst_msg_id,result_rec)
    except Exception: pass
    try: schedule_financial_window_refresh(dst_chat_id,str(entry_day),reason='forward_finance_exact_once_v260')
    except Exception: pass
    schedule_finalize(dst_chat_id,entry_day)
    return result_rec if isinstance(result_rec,dict) else False


def export_global_csv(d: dict):
    """Legacy global CSV with all chats (for backup channel), date DD:MM:YY."""
    try:
        with open(CSV_FILE, 'w', newline='', encoding='utf-8') as f:
            w = csv.writer(f)
            w.writerow(['date', 'amount', 'note'])
            rows = []
            for cid, cdata in d.get('chats', {}).items():
                for dk, records in (cdata.get('daily_records', {}) or {}).items():
                    for r in records or []:
                        rows.append((fmt_date_table(dk), fmt_csv_amount(r.get('amount')), r.get('note', '')))
            rows.sort(key=lambda row: str(row[0]))
            write_csv_rows_with_day_gaps(w, rows, 3)
    except Exception as e:
        log_error(f'export_global_csv: {e}')
EMOJI_DIGITS = {'0': '0️⃣', '1': '1️⃣', '2': '2️⃣', '3': '3️⃣', '4': '4️⃣', '5': '5️⃣', '6': '6️⃣', '7': '7️⃣', '8': '8️⃣', '9': '9️⃣'}
backup_channel_notified_chats = set()

def format_chat_id_emoji(chat_id: int) -> str:
    """Преобразует chat_id в emoji-цифры. Роль владельца не подменяет идентичность чата."""
    return ''.join((EMOJI_DIGITS.get(ch, ch) for ch in str(chat_id)))

def _safe_chat_title_for_filename(title) -> str:
    """Делает короткое безопасное имя чата для имени файла."""
    if not title:
        return ''
    title = str(title).strip()
    title = title.replace(' ', '_')
    title = re.sub('[^0-9A-Za-zА-Яа-я_\\-]+', '', title)
    return title[:32]

def get_chat_name_for_filename(chat_id: int) -> str:
    """
    Выбор имени для файла:
        1) username
        2) title (имя чата)
        3) chat_id
    Всё преобразуется в короткое безопасное имя.
    """
    try:
        store = get_chat_store(chat_id)
        info = store.get('info', {})
        username = info.get('username')
        title = info.get('title')
        if title:
            base = title
        elif username:
            base = username.lstrip('@')
        else:
            base = str(chat_id)
        return _safe_chat_title_for_filename(base)
    except Exception as e:
        log_error(f'get_chat_name_for_filename({chat_id}): {e}')
        return _safe_chat_title_for_filename(str(chat_id))

def _safe_export_name_part(value, fallback: str='chat') -> str:
    try:
        value = str(value or '').strip()
    except Exception:
        value = ''
    if not value:
        value = fallback
    value = value.replace(' ', '_')
    value = re.sub('[^0-9A-Za-zА-Яа-я_@.\\-]+', '', value)
    value = value.strip('._-')
    return (value or fallback)[:70]

def export_period_date_label(mode: str, day_key: str) -> str:
    """Дата/период для имени экспортируемого файла: _(03.06.26-04.06.26)."""
    mode = str(mode or 'all').replace('csv_', '').replace('xlsx_', '')
    if mode == 'all_real':
        mode = 'all'

    def _d(dk: str) -> str:
        return fmt_date_backup(dk).replace(':', '.')
    try:
        if mode == 'day':
            return f'({_d(day_key)})'
        if mode == 'week':
            base = datetime.strptime(day_key, '%Y-%m-%d')
            start = base - timedelta(days=6)
            return f"({_d(start.strftime('%Y-%m-%d'))}-{_d(day_key)})"
        if mode == 'month':
            base = datetime.strptime(day_key, '%Y-%m-%d')
            start = base.replace(day=1)
            return f"({_d(start.strftime('%Y-%m-%d'))}-{_d(day_key)})"
        if mode == 'wedthu':
            base = datetime.strptime(day_key, '%Y-%m-%d')
            start = base - timedelta(days=(base.weekday() - 3) % 7)
            end = start + timedelta(days=6)
            return f"({_d(start.strftime('%Y-%m-%d'))}-{_d(end.strftime('%Y-%m-%d'))})"
    except Exception:
        pass
    return '(all)'

def export_display_filename(chat_id: int, mode: str, day_key: str, ext: str) -> str:
    """Имя файла для CSV/Excel: имя_чата + дата/период файла."""
    chat_name = _safe_export_name_part(get_chat_name_for_filename(chat_id) or get_chat_display_name(chat_id), f'chat_{chat_id}')
    date_part = export_period_date_label(mode, day_key)
    ext = str(ext or 'csv').lower().lstrip('.')
    return f'{chat_name}_{date_part}.{ext}'

def file_bytesio_named(path: str, file_name: str) -> io.BytesIO | None:
    try:
        with open(path, 'rb') as f:
            payload = f.read()
        if not payload:
            return None
        buf = io.BytesIO(payload)
        buf.name = file_name
        buf.seek(0)
        return buf
    except Exception as e:
        log_error(f'file_bytesio_named({path}): {e}')
        return None

def _get_chat_title_for_backup(chat_id: int) -> str:
    """Always derive the Telegram filename from the chat's current stored name."""
    try:
        current_name = get_chat_name_for_filename(chat_id)
        if current_name:
            return current_name
    except Exception as e:
        log_error(f'_get_chat_title_for_backup({chat_id}): {e}')
    return f'chat_{chat_id}'

def send_backup_to_channel_for_file(base_path: str, meta_key_prefix: str, chat_title: str=None):
    """One logical backup file = one Telegram message slot.

    v236 stores message_id/file_id in the pinned Telegram HEAD, not only in
    Render-local csv_meta.json. Repeated backups edit the same channel message.
    If that message was manually deleted, edit fails, the slot is recreated once,
    and the new message_id is committed to HEAD for future edits.
    """
    if not BACKUP_CHAT_ID:
        return
    if not bool(globals().get('telegram_durable_primary_v234', lambda: False)()):
        return
    if not os.path.exists(base_path):
        log_error(f'send_backup_to_channel_for_file: {base_path} not found')
        return
    try:
        meta = _load_csv_meta()
        msg_key = f'msg_{meta_key_prefix}'
        ts_key = f'timestamp_{meta_key_prefix}'
        base_name = os.path.basename(base_path)
        name_without_ext, dot, ext = base_name.partition('.')
        safe_title = _safe_chat_title_for_filename(chat_title)
        file_name = safe_title + (f'.{ext}' if dot else '') if safe_title else base_name
        caption = f"📦 {file_name} — {now_local().strftime('%Y-%m-%d %H:%M')}"
        with open(base_path, 'rb') as src:
            raw = src.read()
        if not raw:
            log_error(f'send_backup_to_channel_for_file: {base_path} is empty, skip')
            return
        stable = globals().get('telegram_stable_document_upsert_v236')
        if callable(stable) and bool(globals().get('telegram_durable_configured_v234', lambda: False)()):
            row = stable(raw, file_name, caption, slot_key=f'chat_backup:{meta_key_prefix}', preferred_message_id=int(meta.get(msg_key) or 0) or None, persist_head=True, reason=f'chat_backup:{meta_key_prefix}')
            meta[msg_key] = int((row or {}).get('message_id') or 0)
            meta[ts_key] = now_local().isoformat(timespec='seconds')
            _save_csv_meta(meta)
            log_info(f'[BACKUP] stable slot updated: {base_path} mid={meta[msg_key]}')
            return

        def _open_for_telegram():
            buf = io.BytesIO(raw)
            buf.name = file_name
            buf.seek(0)
            return buf
        sent = False
        if meta.get(msg_key):
            try:
                _tg_call_retry(bot.edit_message_media, chat_id=int(BACKUP_CHAT_ID), message_id=meta[msg_key], media=types.InputMediaDocument(media=_open_for_telegram(), caption=caption), purpose='backup_channel_edit_message_media')
                sent = True
            except Exception as exc:
                log_error(f'[BACKUP] edit failed, will recreate: {exc}')
        if not sent:
            sent_msg = _tg_call_retry(bot.send_document, int(BACKUP_CHAT_ID), _open_for_telegram(), caption=caption, purpose='backup_channel_send_document')
            meta[msg_key] = sent_msg.message_id
        meta[ts_key] = now_local().isoformat(timespec='seconds')
        _save_csv_meta(meta)
    except Exception as e:
        log_error(f'send_backup_to_channel_for_file({base_path}): {e}')

def send_backup_to_channel(chat_id: int, ensure_files: bool=True):
    bot_journal('backup_to_channel_start', chat_id, 'send_backup_to_channel')
    if not bool(globals().get('telegram_durable_primary_v234', lambda: False)()):
        return
    if not is_backup_to_channel_enabled(chat_id):
        return
    '\n    Общий бэкап файлов чата в BACKUP_CHAT_ID.\n    Делает:\n    • проверку флага backup_flags["channel"]\n    • один раз (на первый бэкап чата) отправляет chat_id эмодзи в канал\n    • обновляет/создаёт в канале только:\n        - data_<chat_id>.json\n        - data_<chat_id>.xlsx\n      CSV в backup-канал больше не отправляется.\n    '
    try:
        if not BACKUP_CHAT_ID:
            return
        if not backup_flags.get('channel', True):
            log_info('send_backup_to_channel: channel backup disabled by flag.')
            return
        try:
            backup_chat_id = int(BACKUP_CHAT_ID)
        except Exception:
            log_error('send_backup_to_channel: BACKUP_CHAT_ID не является числом.')
            return
        if ensure_files:
            save_chat_json(chat_id)
        chat_title = _get_chat_title_for_backup(chat_id)
        meta = _load_csv_meta()
        notify_key = f'emoji_notified_{chat_id}'
        markers_enabled = str(os.getenv('BACKUP_CHAT_MARKERS_ENABLED', '0') or '0').strip().casefold() in {'1', 'true', 'yes', 'on', 'вкл'}
        if markers_enabled and (not meta.get(notify_key)):
            try:
                emoji_id = format_chat_id_emoji(chat_id)
                _tg_call_retry(bot.send_message, backup_chat_id, emoji_id, purpose='backup_channel_send_chat_marker')
                backup_channel_notified_chats.add(chat_id)
                meta[notify_key] = True
                _save_csv_meta(meta)
            except Exception as e:
                log_error(f'send_backup_to_channel: не удалось отправить emoji chat_id в канал: {e}')
        json_path = chat_json_file(chat_id)
        xlsx_path = chat_xlsx_file(chat_id)
        send_backup_to_channel_for_file(json_path, f'json_{chat_id}', chat_title)
        if backup_excel_all_enabled(chat_id) and os.path.exists(xlsx_path):
            send_backup_to_channel_for_file(xlsx_path, f'xlsx_{chat_id}', chat_title)
    except Exception as e:
        log_error(f'send_backup_to_channel({chat_id}): {e}')

def _owner_data_file() -> str | None:
    """Legacy JSON snapshot file for owner-compatible backups."""
    if not OWNER_ID:
        return None
    try:
        return f'data_{int(OWNER_ID)}.json'
    except Exception:
        return None

# --- ИСТОЧНИК: 50_forwarding.py ---
def load_forward_rules():
    """
    Загружает forward_rules/forward_finance из SQLite,
    а если их там ещё нет — пытается импортировать из legacy owner JSON.
    """
    try:
        fr = data.get('forward_rules', {}) or {}
        ff = data.get('forward_finance', {}) or {}
        if fr or ff:
            data['forward_finance'] = ff if isinstance(ff, dict) else {}
            return fr if isinstance(fr, dict) else {}
        path = _owner_data_file()
        if not path or not os.path.exists(path):
            data['forward_finance'] = {}
            return {}
        payload = _load_json(path, {}) or {}
        raw_fr = payload.get('forward_rules', {})
        upgraded = {}
        for src, value in raw_fr.items():
            if isinstance(value, list):
                upgraded[src] = {}
                for dst in value:
                    upgraded[src][dst] = 'oneway_to'
            elif isinstance(value, dict):
                upgraded[src] = value
        ff = payload.get('forward_finance', {})
        if not isinstance(ff, dict):
            ff = {}
        data['forward_finance'] = ff
        data['forward_rules'] = upgraded
        save_data(data)
        return upgraded
    except Exception as e:
        log_error(f'load_forward_rules: {e}')
        data['forward_finance'] = {}
        return {}

def persist_forward_rules_to_owner():
    """
    Сохраняет forward_rules/forward_finance в SQLite
    и дополнительно пишет legacy owner JSON-снимок для совместимости.
    """
    try:
        save_data(data)
        path = _owner_data_file()
        if path:
            payload = _load_json(path, {}) or {}
            if not isinstance(payload, dict):
                payload = {}
            payload['forward_rules'] = data.get('forward_rules', {})
            payload['forward_finance'] = data.get('forward_finance', {})
            _save_json(path, payload)
            log_info(f'forward_rules snapshot persisted to {path}')
    except Exception as e:
        log_error(f'persist_forward_rules_to_owner: {e}')
V199_CHAT_ALIAS_KEY = 'chat_id_aliases_v199'
V199_FORWARD_SUSPENDED_KEY = 'forward_suspended_targets_v199'

def _v199_alias_root() -> dict:
    return data.setdefault('_global_settings', {}).setdefault(V199_CHAT_ALIAS_KEY, {})

def _v199_suspended_root() -> dict:
    return data.setdefault('_global_settings', {}).setdefault(V199_FORWARD_SUSPENDED_KEY, {})

def resolve_canonical_chat_id_v199(chat_id: int) -> int:
    """Follow persisted Telegram chat-id migrations with a loop guard."""
    current = int(chat_id)
    seen = set()
    root = _v199_alias_root()
    for _ in range(12):
        if current in seen:
            break
        seen.add(current)
        row = root.get(str(current))
        if not isinstance(row, dict):
            break
        try:
            nxt = int(row.get('new_chat_id') or 0)
        except Exception:
            nxt = 0
        if not nxt or nxt == current:
            break
        current = nxt
    return int(current)

def _v199_register_chat_alias(old_chat_id: int, new_chat_id: int, reason: str='telegram migration') -> bool:
    old_chat_id, new_chat_id = (int(old_chat_id), int(new_chat_id))
    if old_chat_id == new_chat_id:
        return False
    row = {'old_chat_id': old_chat_id, 'new_chat_id': new_chat_id, 'reason': str(reason or 'telegram migration')[:500], 'at': now_local().isoformat(timespec='seconds')}
    root = _v199_alias_root()
    changed = root.get(str(old_chat_id)) != row
    root[str(old_chat_id)] = row
    return changed

def is_forward_target_suspended_v199(chat_id: int) -> bool:
    try:
        cid = int(chat_id)
        if str(cid) in _v199_suspended_root():
            return True
        canonical = resolve_canonical_chat_id_v199(cid)
        return str(canonical) in _v199_suspended_root()
    except Exception:
        return False

def _v199_rewrite_pair_order_id(old_chat_id: int, new_chat_id: int | None=None, *, remove_only: bool=False) -> bool:
    old_chat_id = int(old_chat_id)
    changed = False
    order = data.get('forward_pair_order')
    if not isinstance(order, list):
        return False
    out = []
    seen = set()
    for raw in order:
        try:
            a_s, b_s = str(raw).split(':', 1)
            a, b = (int(a_s), int(b_s))
        except Exception:
            if raw not in seen:
                out.append(raw)
                seen.add(raw)
            continue
        if remove_only and old_chat_id in {a, b}:
            changed = True
            continue
        if new_chat_id is not None:
            na = int(new_chat_id) if a == old_chat_id else a
            nb = int(new_chat_id) if b == old_chat_id else b
            if (na, nb) != (a, b):
                changed = True
            if na == nb:
                changed = True
                continue
            key = f'{na}:{nb}'
        else:
            key = str(raw)
        if key not in seen:
            out.append(key)
            seen.add(key)
    if out != order:
        data['forward_pair_order'] = out
        changed = True
    return changed

def suspend_forward_target_v199(dst_chat_id: int, reason: str, *, persist: bool=True) -> bool:
    """Remove a confirmed-dead destination from live forwarding but keep a reversible audit copy."""
    dst_chat_id = int(dst_chat_id)
    key = str(dst_chat_id)
    root = _v199_suspended_root()
    existing = root.get(key) if isinstance(root.get(key), dict) else None
    # R17: even an already-suspended target is scrubbed again from live maps.  This
    # repairs stale R16 states where an audit row existed but a forwarding edge was
    # later reintroduced, which otherwise could keep hitting a removed chat forever.
    edges = list((existing or {}).get('edges') or [])
    changed_live = False
    fr = data.setdefault('forward_rules', {})
    ff = data.setdefault('forward_finance', {})
    for src, dsts in list(fr.items()):
        if not isinstance(dsts, dict) or key not in dsts:
            continue
        mode = dsts.pop(key)
        changed_live = True
        fin = bool((ff.get(str(src), {}) or {}).pop(key, False))
        edges.append({'src': int(src), 'mode': mode, 'finance': fin})
        if not dsts:
            fr.pop(str(src), None)
        frow = ff.get(str(src))
        if isinstance(frow, dict) and (not frow):
            ff.pop(str(src), None)
    for src, dsts in list(ff.items()):
        if not isinstance(dsts, dict) or key not in dsts:
            continue
        fin = bool(dsts.pop(key, False))
        changed_live = True
        if fin and (not any((int(e.get('src')) == int(src) for e in edges))):
            edges.append({'src': int(src), 'mode': 'oneway_to', 'finance': True, 'finance_only_legacy': True})
        if not dsts:
            ff.pop(str(src), None)
    pair_changed = bool(_v199_rewrite_pair_order_id(dst_chat_id, remove_only=True))
    changed_live = bool(changed_live or pair_changed)
    now_s = now_local().isoformat(timespec='seconds')
    if isinstance(existing, dict):
        existing['chat_id'] = dst_chat_id
        existing['title'] = existing.get('title') or get_chat_display_name(dst_chat_id)
        existing['reason'] = str(existing.get('reason') or reason or '')[:500]
        existing['last_reason'] = str(reason or '')[:500]
        existing['last_confirmed_at'] = now_s
        existing['edges'] = edges
        existing['auto_reactivate'] = True
        root[key] = existing
    else:
        root[key] = {'chat_id': dst_chat_id, 'title': get_chat_display_name(dst_chat_id), 'reason': str(reason or '')[:500], 'suspended_at': now_s, 'last_confirmed_at': now_s, 'edges': edges, 'auto_reactivate': True}
        changed_live = True
    try:
        fn = globals().get('set_chat_status_v150')
        lifecycle_fn = globals().get('_v150_lifecycle')
        current_status = ''
        if callable(lifecycle_fn):
            try:
                current_status = str((lifecycle_fn(dst_chat_id) or {}).get('status') or '')
            except Exception:
                current_status = ''
        # R17: a forwarding suspension must never downgrade a confirmed terminal
        # chat back to transient ``unreachable``.  The terminal lifecycle is the
        # authority that stops reminders/tasks/forwarding together.
        if callable(fn) and current_status not in {'bot_removed', 'migrated', 'archived'}:
            fn(dst_chat_id, 'unreachable', str(reason or '')[:500], source='forward_confirmed_unreachable')
    except Exception:
        pass
    if persist:
        try:
            persist_forward_rules_to_owner()
        except Exception:
            pass
        try:
            save_data(data, full=True)
        except Exception:
            save_data(data)
        try:
            schedule_config_backup_for_chats(dst_chat_id, int(OWNER_ID or 0), delay=0.5)
        except Exception:
            pass
    try:
        bot_journal('forward_target_suspended_v199', dst_chat_id, f'edges={len(edges)} reason={str(reason)[:240]}', 'WARN')
    except Exception:
        pass
    return bool(changed_live)

def reactivate_forward_target_v199(chat_id: int, *, migrated_to: int | None=None, persist: bool=True) -> bool:
    old_id = int(chat_id)
    target = int(migrated_to) if migrated_to is not None else resolve_canonical_chat_id_v199(old_id)
    root = _v199_suspended_root()
    row = root.pop(str(old_id), None)
    if row is None and target != old_id:
        row = root.pop(str(target), None)
    if not isinstance(row, dict):
        return False
    fr = data.setdefault('forward_rules', {})
    ff = data.setdefault('forward_finance', {})
    restored = 0
    for edge in row.get('edges') or []:
        try:
            src = resolve_canonical_chat_id_v199(int(edge.get('src')))
            if src == target:
                continue
            mode = edge.get('mode') or 'oneway_to'
            fr.setdefault(str(src), {})[str(target)] = mode
            if bool(edge.get('finance')):
                ff.setdefault(str(src), {})[str(target)] = True
            restored += 1
        except Exception:
            continue
    if persist:
        try:
            persist_forward_rules_to_owner()
        except Exception:
            pass
        try:
            save_data(data, full=True)
        except Exception:
            save_data(data)
    try:
        bot_journal('forward_target_reactivated_v199', target, f'from={old_id}; edges={restored}')
    except Exception:
        pass
    return True

def _v199_is_chat_not_found_error(err) -> bool:
    low = str(err or '').casefold()
    return 'chat not found' in low

def _v199_confirm_failed_forward_target(dst_chat_id: int, original_error: Exception) -> str:
    """Return migrated/suspended/transient. A single send error is never enough to suspend."""
    dst_chat_id = int(dst_chat_id)
    migrated = _handle_supergroup_migration_error(dst_chat_id, original_error)
    if migrated is not None:
        return f'migrated:{int(migrated)}'
    if not (_v199_is_chat_not_found_error(original_error) or _is_bot_removed_error(original_error)):
        return 'transient'
    try:
        bot.get_chat(dst_chat_id)
        return 'transient'
    except Exception as probe_error:
        migrated = _handle_supergroup_migration_error(dst_chat_id, probe_error)
        if migrated is not None:
            return f'migrated:{int(migrated)}'
        if _v199_is_chat_not_found_error(probe_error) or _is_bot_removed_error(probe_error):
            newly = suspend_forward_target_v199(dst_chat_id, str(probe_error)[:500], persist=True)
            if newly:
                try:
                    send_owner_technical_alert(f'⚠️ Пересылка на {get_chat_display_name(dst_chat_id)} приостановлена.\nID: {dst_chat_id}\nTelegram повторно подтвердил недоступность чата. Правила сохранены и восстановятся после успешной проверки/миграции чата.', 35)
                except Exception:
                    pass
            return 'suspended'
    return 'transient'

def _v177_legacy_0140_resolve_forward_targets(source_chat_id: int):
    with data_lock:
        fr = data.get('forward_rules', {})
        ff = data.get('forward_finance', {})
        source_raw = int(source_chat_id)
        source_canonical = resolve_canonical_chat_id_v199(source_raw)
        src = str(source_canonical if str(source_canonical) in fr else source_raw)
        if src not in fr:
            return []
        out = []
        seen = set()
        for dst, mode in list(fr[src].items()):
            try:
                raw_dst = int(dst)
                canonical_dst = resolve_canonical_chat_id_v199(raw_dst)
                if is_forward_target_suspended_v199(raw_dst) or is_forward_target_suspended_v199(canonical_dst):
                    continue
                if canonical_dst in seen:
                    continue
                seen.add(canonical_dst)
                out.append((canonical_dst, mode, bool(ff.get(src, {}).get(dst, ff.get(src, {}).get(str(canonical_dst), False)))))
            except Exception:
                continue
        return out
try:
    _v177_legacy_0140_resolve_forward_targets.__name__ = 'resolve_forward_targets'
except Exception:
    pass

def _v177_legacy_0141_add_forward_link(src_chat_id: int, dst_chat_id: int, mode: str):
    fr = data.setdefault('forward_rules', {})
    src = str(src_chat_id)
    dst = str(dst_chat_id)
    fr.setdefault(src, {})[dst] = mode
    persist_forward_rules_to_owner()
    save_data(data)
    schedule_config_backup_for_chats(src_chat_id, dst_chat_id)
try:
    _v177_legacy_0141_add_forward_link.__name__ = 'add_forward_link'
except Exception:
    pass

def _v177_legacy_0144_remove_forward_link(src_chat_id: int, dst_chat_id: int):
    fr = data.get('forward_rules', {})
    src = str(src_chat_id)
    dst = str(dst_chat_id)
    if src in fr and dst in fr[src]:
        del fr[src][dst]
    if src in fr and (not fr[src]):
        del fr[src]
    remove_forward_finance(src_chat_id, dst_chat_id)
    persist_forward_rules_to_owner()
    save_data(data)
    schedule_config_backup_for_chats(src_chat_id, dst_chat_id)
try:
    _v177_legacy_0144_remove_forward_link.__name__ = 'remove_forward_link'
except Exception:
    pass

def _v177_legacy_0145_clear_forward_all():
    """Полностью отключает всю пересылку."""
    data['forward_rules'] = {}
    data['forward_finance'] = {}
    persist_forward_rules_to_owner()
    save_data(data)
    schedule_config_backup_for_chats()
try:
    _v177_legacy_0145_clear_forward_all.__name__ = 'clear_forward_all'
except Exception:
    pass

def get_forward_finance(src_chat_id: int, dst_chat_id: int) -> bool:
    ff = data.setdefault('forward_finance', {})
    return bool(ff.get(str(src_chat_id), {}).get(str(dst_chat_id), False))
FORWARD_COPY_EDIT_MODES = ('normal', 'button', 'slash')

def _v177_legacy_0146_forward_copy_edit_mode(chat_id: int | None=None) -> str:
    """One GLOBAL 💰Перес mode for every chat/copy.

    v92-v123 stored this in owner/chat scopes. v124 imports that legacy value once and then
    keeps a single root value, so changing the mode in INFO changes all bot copies globally.
    """
    mode = ''
    try:
        gs = (data or {}).setdefault('_global_settings', {})
        mode = str(gs.get('forward_copy_edit_mode_global') or '').strip().lower()
        if mode not in FORWARD_COPY_EDIT_MODES:
            legacy = str(gs.get('forward_copy_edit_mode') or '').strip().lower()
            if legacy not in FORWARD_COPY_EDIT_MODES:
                try:
                    scope = owner_scope_id(chat_id)
                    legacy = str(owner_scoped_settings(scope).get('forward_copy_edit_mode') or '').strip().lower()
                except Exception:
                    legacy = ''
            if legacy not in FORWARD_COPY_EDIT_MODES:
                try:
                    scope = owner_scope_id(chat_id)
                    legacy = str(get_chat_store(scope).setdefault('settings', {}).get('forward_copy_edit_mode') or '').strip().lower()
                except Exception:
                    legacy = ''
            mode = legacy if legacy in FORWARD_COPY_EDIT_MODES else 'normal'
            gs['forward_copy_edit_mode_global'] = mode
            gs['forward_copy_edit_mode'] = mode
    except Exception:
        mode = 'normal'
    if mode not in FORWARD_COPY_EDIT_MODES or not version_mode_feature('forward_copy_edit'):
        return 'normal'
    return mode
try:
    _v177_legacy_0146_forward_copy_edit_mode.__name__ = 'forward_copy_edit_mode'
except Exception:
    pass

def _v177_legacy_0148_set_forward_copy_edit_mode(chat_id: int, mode: str):
    mode = str(mode or 'normal').strip().lower()
    if mode not in FORWARD_COPY_EDIT_MODES:
        mode = 'normal'
    gs = data.setdefault('_global_settings', {})
    gs['forward_copy_edit_mode_global'] = mode
    gs['forward_copy_edit_mode'] = mode
    scope_ids = []
    try:
        for scope in [int(OWNER_ID or 0)] + list(get_additional_owner_ids()):
            if not scope:
                continue
            try:
                scope = int(scope)
                owner_scoped_settings(scope)['forward_copy_edit_mode'] = mode
                get_chat_store(scope).setdefault('settings', {})['forward_copy_edit_mode'] = mode
                scope_ids.append(scope)
            except Exception:
                pass
    except Exception:
        pass
    save_data(data, chat_ids=scope_ids or None, root_only=not bool(scope_ids))
    schedule_config_backup_for_chats(*(scope_ids or []), delay=1.0)
    return mode
try:
    _v177_legacy_0148_set_forward_copy_edit_mode.__name__ = 'set_forward_copy_edit_mode'
except Exception:
    pass

def _v177_legacy_0150_cycle_forward_copy_edit_mode(chat_id: int) -> str:
    current = forward_copy_edit_mode(int(chat_id))
    try:
        idx = FORWARD_COPY_EDIT_MODES.index(current)
    except ValueError:
        idx = 0
    return set_forward_copy_edit_mode(int(chat_id), FORWARD_COPY_EDIT_MODES[(idx + 1) % len(FORWARD_COPY_EDIT_MODES)])
try:
    _v177_legacy_0150_cycle_forward_copy_edit_mode.__name__ = 'cycle_forward_copy_edit_mode'
except Exception:
    pass

def _v177_legacy_0151_forward_copy_edit_mode_label(chat_id: int) -> str:
    mode = forward_copy_edit_mode(int(chat_id))
    return {'normal': '💰Перес: обычно', 'button': '💰Перес: кнопка', 'slash': '💰Перес: слеш'}.get(mode, '💰Перес: обычно')
try:
    _v177_legacy_0151_forward_copy_edit_mode_label.__name__ = 'forward_copy_edit_mode_label'
except Exception:
    pass
try:
    FORWARD_COPY_RETRO_MIN_GAP_SECONDS = max(0.04, min(2.0, float(os.getenv('FORWARD_COPY_RETRO_MIN_GAP_SECONDS', '0.10') or '0.10')))
except Exception:
    FORWARD_COPY_RETRO_MIN_GAP_SECONDS = 0.1
try:
    FORWARD_COPY_RETRO_DAYS = max(1, min(7, int(os.getenv('FORWARD_COPY_RETRO_DAYS', '3') or '3')))
except Exception:
    FORWARD_COPY_RETRO_DAYS = 3
try:
    FORWARD_COPY_RETRO_MAX_PER_CHAT = max(3, min(30, int(os.getenv('FORWARD_COPY_RETRO_MAX_PER_CHAT', '12') or '12')))
except Exception:
    FORWARD_COPY_RETRO_MAX_PER_CHAT = 12
_FORWARD_COPY_RETRO_LOCK = threading.RLock()
_FORWARD_COPY_RETRO_GENERATION = {}

def _begin_forward_copy_retro_refresh(owner_chat_id: int) -> int:
    scope = 0
    with _FORWARD_COPY_RETRO_LOCK:
        generation = int(_FORWARD_COPY_RETRO_GENERATION.get(scope, 0) or 0) + 1
        _FORWARD_COPY_RETRO_GENERATION[scope] = generation
        return generation

def _forward_copy_retro_is_stale(owner_chat_id: int, generation: int | None) -> bool:
    if generation is None:
        return False
    with _FORWARD_COPY_RETRO_LOCK:
        return int(_FORWARD_COPY_RETRO_GENERATION.get(0, 0) or 0) != int(generation)

def _forward_copy_record_identity(chat_id: int, rec: dict):
    """Return (is_forward_copy, msg_id, src_chat_id, src_msg_id), including v92-era rows."""
    if not isinstance(rec, dict):
        return (False, 0, None, None)
    try:
        msg_id = int(rec.get('forward_dst_msg_id') or rec.get('source_msg_id') or rec.get('origin_msg_id') or rec.get('msg_id') or 0)
    except Exception:
        msg_id = 0
    if not msg_id:
        return (False, 0, None, None)
    src_chat_id = rec.get('forward_source_chat_id')
    src_msg_id = rec.get('forward_source_msg_id')
    try:
        src_chat_id = int(src_chat_id) if src_chat_id is not None else None
    except Exception:
        src_chat_id = None
    try:
        src_msg_id = int(src_msg_id) if src_msg_id is not None else None
    except Exception:
        src_msg_id = None
    if src_chat_id is None or src_msg_id is None:
        try:
            rev_chat, rev_msg = _find_forward_origin_by_copied_message(int(chat_id), int(msg_id))
            if rev_chat is not None:
                src_chat_id = int(rev_chat)
            if rev_msg is not None:
                src_msg_id = int(rev_msg)
        except Exception:
            pass
    legacy_flag = bool(rec.get('forwarded_by_bot') or rec.get('forwarded_finance') or rec.get('forward_source_chat_id') is not None)
    is_copy = bool(legacy_flag or src_chat_id is not None)
    return (is_copy, msg_id, src_chat_id, src_msg_id)

def _hydrate_legacy_forward_copy_metadata(chat_id: int, rec: dict, msg_id: int, src_chat_id=None, src_msg_id=None) -> bool:
    """Persist modern metadata when an old pre-deploy finance row is recognized as a copy."""
    changed = False
    try:
        if not rec.get('forwarded_by_bot'):
            rec['forwarded_by_bot'] = True
            changed = True
        if rec.get('forward_dst_chat_id') is None:
            rec['forward_dst_chat_id'] = int(chat_id)
            changed = True
        if rec.get('forward_dst_msg_id') is None:
            rec['forward_dst_msg_id'] = int(msg_id)
            changed = True
        if src_chat_id is not None and rec.get('forward_source_chat_id') is None:
            rec['forward_source_chat_id'] = int(src_chat_id)
            changed = True
        if src_msg_id is not None and rec.get('forward_source_msg_id') is None:
            rec['forward_source_msg_id'] = int(src_msg_id)
            changed = True
        if not rec.get('forward_copy_content_type'):
            rec['forward_copy_content_type'] = 'text'
            changed = True
        if changed:
            rid = rec.get('id')
            store = get_chat_store(int(chat_id))
            for daily_key in ('daily_records', 'ars_daily_records', 'usd_daily_records'):
                for arr in (store.get(daily_key, {}) or {}).values():
                    for rr in arr or []:
                        if not isinstance(rr, dict) or rr.get('id') != rid:
                            continue
                        if _record_has_message_id(rr, int(msg_id)):
                            rr.update(rec)
    except Exception:
        pass
    return changed

def _forward_copy_retro_record_is_recent(rec: dict, cutoff_key: str) -> bool:
    """True only for records in the bounded recent-history repaint window."""
    try:
        day = str((rec or {}).get('day_key') or '')[:10]
        if re.fullmatch('\\d{4}-\\d{2}-\\d{2}', day):
            return day >= cutoff_key
    except Exception:
        pass
    for key in ('timestamp', 'created_at', 'updated_at'):
        try:
            raw = str((rec or {}).get(key) or '')
            m = re.search('(20\\d{2}-\\d{2}-\\d{2})', raw)
            if m:
                return m.group(1) >= cutoff_key
        except Exception:
            pass
    return False

def refresh_existing_forward_copy_ui(owner_chat_id: int, mode: str | None=None, generation: int | None=None) -> int:
    """Quick repaint of only the newest bot copies.

    v124 could walk 600+ historical messages and Telegram answered 429/retry_after≈40s,
    making a cosmetic mode switch look frozen. v125 repaints at most the newest
    FORWARD_COPY_RETRO_MAX_PER_CHAT copies per chat from the last
    FORWARD_COPY_RETRO_DAYS calendar days, and interleaves chats round-robin.
    Old history is left untouched; newly created copies always use the selected mode.
    """
    owner_chat_id = int(owner_chat_id)
    mode = mode or forward_copy_edit_mode(owner_chat_id)
    try:
        today_dt = datetime.strptime(today_key(), '%Y-%m-%d').date()
        cutoff_key = (today_dt - timedelta(days=max(0, FORWARD_COPY_RETRO_DAYS - 1))).strftime('%Y-%m-%d')
    except Exception:
        cutoff_key = today_key()
    changed = 0
    attempted = 0
    hydrated = 0
    stopped_stale = False
    metadata_changed_chats = set()
    rate_limited_chats = set()
    candidates_by_chat = []
    try:
        bot_journal('forward_copy_retro_start', owner_chat_id, f'GLOBAL mode={mode} generation={generation} days={FORWARD_COPY_RETRO_DAYS} max_per_chat={FORWARD_COPY_RETRO_MAX_PER_CHAT} gap={FORWARD_COPY_RETRO_MIN_GAP_SECONDS}s')
    except Exception:
        pass
    for cid in collect_all_known_chat_ids(include_owner=True):
        if _forward_copy_retro_is_stale(owner_chat_id, generation):
            stopped_stale = True
            break
        try:
            store = get_chat_store(int(cid))
            rows = [rec for _ledger_key, rec in _finance_record_lists(store) if _forward_copy_retro_record_is_recent(rec, cutoff_key)]
            rows.sort(key=record_sort_key, reverse=True)
            seen = set()
            picked = []
            for rec in rows:
                is_copy, msg_id, src_chat_id, src_msg_id = _forward_copy_record_identity(int(cid), rec)
                if not is_copy or not msg_id or rec.get('forward_copy_deleted') or (int(msg_id) in seen):
                    continue
                seen.add(int(msg_id))
                picked.append((rec, int(msg_id), src_chat_id, src_msg_id))
                if len(picked) >= FORWARD_COPY_RETRO_MAX_PER_CHAT:
                    break
            if picked:
                candidates_by_chat.append((int(cid), picked))
        except Exception as e:
            log_error(f'refresh_existing_forward_copy_ui collect {cid}: {e}')
    max_depth = max((len(rows) for _cid, rows in candidates_by_chat), default=0)
    last_edit_mono = 0.0
    for depth in range(max_depth):
        for cid, picked in candidates_by_chat:
            if depth >= len(picked) or cid in rate_limited_chats:
                continue
            if _forward_copy_retro_is_stale(owner_chat_id, generation):
                stopped_stale = True
                break
            rec, msg_id, src_chat_id, src_msg_id = picked[depth]
            if _hydrate_legacy_forward_copy_metadata(cid, rec, msg_id, src_chat_id, src_msg_id):
                metadata_changed_chats.add(cid)
                hydrated += 1
            try:
                if last_edit_mono > 0:
                    wait = FORWARD_COPY_RETRO_MIN_GAP_SECONDS - (time.monotonic() - last_edit_mono)
                    if wait > 0:
                        time.sleep(wait)
                if _forward_copy_retro_is_stale(owner_chat_id, generation):
                    stopped_stale = True
                    break
                base_text = str(rec.get('source_finance_text') or '').strip() or compose_edit_input_value(rec.get('amount'), rec.get('note', ''))
                display_text = _forward_copy_display_text(base_text, rec, mode)
                markup = _forward_copy_edit_keyboard(mode)
                ct = str(rec.get('forward_copy_content_type') or 'text')
                attempted += 1
                last_edit_mono = time.monotonic()
                if ct == 'text':
                    _tg_call_retry(bot.edit_message_text, display_text, chat_id=cid, message_id=msg_id, reply_markup=markup, attempts=1, purpose='forward_copy_retro_text_fast')
                elif ct in {'photo', 'video', 'document', 'audio', 'animation', 'voice'}:
                    _tg_call_retry(bot.edit_message_caption, caption=display_text, chat_id=cid, message_id=msg_id, reply_markup=markup, attempts=1, purpose='forward_copy_retro_caption_fast')
                else:
                    _tg_call_retry(bot.edit_message_reply_markup, cid, msg_id, reply_markup=markup, attempts=1, purpose='forward_copy_retro_markup_fast')
                changed += 1
            except Exception as e:
                err = str(e).lower()
                if 'message is not modified' in err:
                    changed += 1
                elif 'message to edit not found' in err or 'message_id_invalid' in err or 'message not found' in err:
                    rec['forward_copy_deleted'] = True
                    metadata_changed_chats.add(cid)
                elif is_telegram_429(e):
                    rate_limited_chats.add(cid)
                    try:
                        bot_journal('forward_copy_retro_rate_skip', cid, f'msg={msg_id} mode={mode}; chat paused after 429', 'WARN')
                    except Exception:
                        pass
                else:
                    log_error(f"refresh_existing_forward_copy_ui {cid}:{rec.get('id')}: {e}")
        if stopped_stale:
            break
    for cid in metadata_changed_chats:
        try:
            store = get_chat_store(cid)
            _snapshot_active_currency_ledger(store, _ensure_currency_ledgers(store))
            save_data(data, chat_ids=[cid])
        except Exception:
            pass
    try:
        _persist_forward_index_in_data(data)
        save_data(data, root_only=True)
    except Exception:
        pass
    try:
        total_candidates = sum((len(rows) for _cid, rows in candidates_by_chat))
        bot_journal('forward_copy_retro_done', owner_chat_id, f'GLOBAL mode={mode} generation={generation} cutoff={cutoff_key} candidates={total_candidates} attempted={attempted} changed={changed} hydrated={hydrated} rate_limited_chats={len(rate_limited_chats)} stale={stopped_stale}')
    except Exception:
        pass
    return changed

def _v168_record_uid_seed(chat_id: int, rec: dict) -> str:
    """Stable seed that deliberately excludes mutable amount/note/short_id fields."""
    payload = {'chat_id': int(chat_id or 0), 'operation_key': str((rec or {}).get('operation_key') or ''), 'source_msg_id': int((rec or {}).get('source_msg_id') or 0), 'origin_msg_id': int((rec or {}).get('origin_msg_id') or 0), 'msg_id': int((rec or {}).get('msg_id') or 0), 'forward_source_chat_id': int((rec or {}).get('forward_source_chat_id') or 0), 'forward_source_msg_id': int((rec or {}).get('forward_source_msg_id') or 0), 'source_order_msg_id': int((rec or {}).get('source_order_msg_id') or 0), 'timestamp': str((rec or {}).get('timestamp') or ''), 'day_key': str((rec or {}).get('day_key') or ''), 'id': int((rec or {}).get('id') or 0), 'currency': 'usd' if bool((rec or {}).get('usd_only')) else 'ars'}
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(',', ':'))
    return hashlib.sha256(raw.encode('utf-8', errors='replace')).hexdigest()[:12].upper()

def ensure_finance_record_uid(chat_id: int, rec: dict) -> str:
    if not isinstance(rec, dict):
        return ''
    current = str(rec.get('record_uid') or '').strip().upper()
    if re.fullmatch('[A-F0-9]{12}', current):
        return current
    current = _v168_record_uid_seed(int(chat_id), rec)
    rec['record_uid'] = current
    return current

def find_finance_record_by_uid(chat_id: int, record_uid: str):
    uid = str(record_uid or '').strip().upper()
    if not re.fullmatch('[A-F0-9]{12}', uid):
        return None
    try:
        for _key, rec in _finance_record_lists(get_chat_store(int(chat_id))):
            if isinstance(rec, dict) and ensure_finance_record_uid(int(chat_id), rec) == uid:
                return rec
    except Exception:
        pass
    return None


def persist_finance_chat_local_fast(chat_id: int) -> bool:
    """R48 FINAL: one owner, short RAM snapshot, one SQLite commit, then split notification."""
    try:
        cid = int(chat_id)
        lock = chat_lock_for(cid)
        if hasattr(lock, 'held_by_current_thread') and lock.held_by_current_thread():
            raise RuntimeError('R48 invariant: finance persist called while chat_lock is held')
        with locked_chat(cid):
            store = get_chat_store(cid)
            if LOWRAM_ENABLED:
                payload, cold = _lowram_flush_chat(cid, store, evict=False)
            else:
                payload, cold = copy.deepcopy(dict(store)), {}
        saved = SQLITE.save_chat_bundle(cid, payload, cold)
        if saved:
            try:
                with _LOWRAM_LOCK:
                    _LOWRAM_STATS['cold_saves'] += int(saved)
            except Exception:
                pass
        # R48: folded former R11 wrapper into the single persistence owner.
        try:
            inside_fn = globals().get('_split_inside_telegram_update_v264')
            if callable(inside_fn) and inside_fn():
                ctx = globals().get('_SPLIT_UPDATE_CONTEXT')
                if ctx is not None:
                    ctx.finance_dirty = True
            else:
                mark_fn = globals().get('_split_mark_state_changed_v264')
                sync_fn = globals().get('split_schedule_worker_sync_v262')
                if callable(mark_fn):
                    mark_fn(f'finance_commit:{cid}')
                if callable(sync_fn):
                    sync_fn(reason=f'finance_commit:{cid}', delay=0.35)
        except Exception:
            pass
        return True
    except Exception as exc:
        try: log_error(f'R48 local finance persist {chat_id}: {exc}')
        except Exception: pass
        return False


def migrate_finance_record_uids(chat_id: int) -> int:
    changed = 0
    seen = set()
    try:
        for _key, rec in _finance_record_lists(get_chat_store(int(chat_id))):
            if not isinstance(rec, dict) or id(rec) in seen:
                continue
            seen.add(id(rec))
            before = str(rec.get('record_uid') or '')
            after = ensure_finance_record_uid(int(chat_id), rec)
            if after and after != before:
                changed += 1
        if changed:
            persist_finance_chat_local_fast(int(chat_id))
    except Exception as exc:
        try:
            log_error(f'v168 UID migration chat={chat_id}: {exc}')
        except Exception:
            pass
    return changed

def _strip_forward_copy_edit_command(text: str) -> str:
    raw = str(text or '').rstrip()
    return re.sub('(?:\\n|\\s)+/izm_[RU]\\d+(?:_u[A-F0-9]{12})?\\s*$', '', raw, flags=re.I).rstrip()

def _forward_copy_record_command(rec: dict) -> str:
    sid = str((rec or {}).get('short_id') or f"R{(rec or {}).get('id', '')}").strip().upper()
    if not re.fullmatch('[RU]\\d+', sid):
        sid = 'R' + re.sub('\\D+', '', sid)
    uid = str((rec or {}).get('record_uid') or '').strip().upper()
    return f'/izm_{sid}_u{uid}' if re.fullmatch('[A-F0-9]{12}', uid) else f'/izm_{sid}'

def _v169_forward_uid_for_copy(dst_chat_id: int, source_msg) -> str:
    """Deterministic UID known before Telegram creates the destination copy."""
    try:
        src_chat_id = int(getattr(getattr(source_msg, 'chat', None), 'id', 0) or 0)
        src_msg_id = int(getattr(source_msg, 'forward_source_msg_id', 0) or getattr(source_msg, 'message_id', 0) or 0)
        raw = f'forward-copy:{src_chat_id}:{src_msg_id}:{int(dst_chat_id)}'
        return hashlib.sha256(raw.encode('utf-8', errors='replace')).hexdigest()[:12].upper()
    except Exception:
        return ''

def _predict_forward_copy_record_command(dst_chat_id: int, source_msg, text: str) -> str | None:
    """Predict the final R/U + stable UID while caller holds locked_chat(dst_chat_id).

    The destination chat lock stays held through Telegram send + finance-row creation in
    _forward_single_to_target, so another finance insert cannot steal the predicted monthly
    position.  The UID is derived only from the immutable forwarding edge and is assigned to
    the concrete row immediately after it is created.
    """
    try:
        raw = str(text or '').strip()
        if not raw or not looks_like_amount(raw) or (not is_finance_mode(int(dst_chat_id))):
            return None
        comp = parse_financial_components(raw)
        store = get_chat_store(int(dst_chat_id))
        normalize_chat_records(int(dst_chat_id))
        day_key = finance_day_key_from_message(source_msg) if source_msg is not None else finance_today_key()
        month_key = str(day_key)[:7]
        temp = {'id': int(store.get('next_id', 1) or 1), 'day_key': str(day_key), 'timestamp': message_timestamp_iso(source_msg), 'source_order_msg_id': int(getattr(source_msg, 'message_id', 0) or 0), 'source_msg_id': 0, 'usd_only': bool(comp.get('usd_only', False)), 'usd_amount': float(comp.get('usd_amount', 0) or 0)}
        temp_key = record_sort_key(temp)
        rows = []
        for dk, arr in (store.get('daily_records', {}) or {}).items():
            if str(dk)[:7] != month_key:
                continue
            for rec in arr or []:
                if isinstance(rec, dict):
                    rows.append(rec)
        if bool(temp.get('usd_only')):
            relevant = [r for r in rows if bool(float(r.get('usd_amount', 0) or 0))]
            prefix = 'U'
        else:
            relevant = [r for r in rows if not bool(r.get('usd_only', False))]
            prefix = 'R'
        position = 1 + sum((1 for r in relevant if record_sort_key(r) < temp_key))
        uid = _v169_forward_uid_for_copy(int(dst_chat_id), source_msg)
        return f'/izm_{prefix}{position}_u{uid}' if uid else None
    except Exception as e:
        try:
            log_error(f'v169 predict forward copy command dst={dst_chat_id}: {e}')
        except Exception:
            pass
        return None

def _v169_apply_predicted_record_uid(dst_chat_id: int, rec: dict | None, command: str | None) -> dict | None:
    if not isinstance(rec, dict) or not command:
        return rec
    try:
        match = re.search('_u([A-F0-9]{12})$', str(command), flags=re.I)
        if not match:
            return rec
        uid = str(match.group(1)).upper()
        rec['record_uid'] = uid
        store = get_chat_store(int(dst_chat_id))
        rid = int(rec.get('id', -1) or -1)
        for _key, item in _finance_record_lists(store):
            try:
                if int(item.get('id', -2) or -2) == rid:
                    item['record_uid'] = uid
            except Exception:
                pass
        for arr in (store.get('daily_records', {}) or {}).values():
            for item in arr or []:
                try:
                    if int(item.get('id', -2) or -2) == rid:
                        item['record_uid'] = uid
                except Exception:
                    pass
        persist_finance_chat_local_fast(int(dst_chat_id))
    except Exception as exc:
        try:
            log_error(f'v169 apply predicted UID {dst_chat_id}: {exc}')
        except Exception:
            pass
    return rec

def _forward_copy_display_text(base_text: str, rec: dict | None, mode: str) -> str:
    base = _strip_forward_copy_edit_command(base_text)
    if mode == 'slash' and rec:
        return (base + '\n' + _forward_copy_record_command(rec)).strip()
    return base

def _forward_copy_edit_keyboard(mode: str):
    if mode != 'button':
        return None
    kb = types.InlineKeyboardMarkup()
    kb.row(IB('✏️ Изменить', callback_data='fwdcopy_edit'))
    return kb

def _forward_copy_origin_source_chat(dst_chat_id: int, dst_msg_id: int, rec: dict | None=None):
    try:
        if rec and rec.get('forward_source_chat_id') is not None:
            return int(rec.get('forward_source_chat_id'))
    except Exception:
        pass
    try:
        src_chat_id, _src_msg_id = _find_forward_origin_by_copied_message(int(dst_chat_id), int(dst_msg_id))
        return int(src_chat_id) if src_chat_id is not None else None
    except Exception:
        return None

def _set_forward_record_metadata(dst_chat_id: int, dst_msg_id: int, source_chat_id: int, source_msg):
    try:
        rec = find_record_by_message_id(int(dst_chat_id), int(dst_msg_id))
        if not rec:
            return None
        rec['forward_source_chat_id'] = int(source_chat_id)
        rec['forward_source_msg_id'] = int(getattr(source_msg, 'message_id', 0) or 0)
        rec['forward_copy_content_type'] = str(getattr(source_msg, 'content_type', 'text') or 'text')
        ensure_finance_record_uid(int(dst_chat_id), rec)
        for _key, item in _finance_record_lists(get_chat_store(int(dst_chat_id))):
            if int(item.get('id', -1)) == int(rec.get('id', -2)):
                item.update(rec)
                ensure_finance_record_uid(int(dst_chat_id), item)
        if not persist_finance_chat_local_fast(int(dst_chat_id)):
            return None
        return rec
    except Exception as e:
        log_error(f'_set_forward_record_metadata({dst_chat_id},{dst_msg_id}): {e}')
        return None

def apply_forward_copy_edit_ui(source_chat_id: int, dst_chat_id: int, dst_msg_id: int, source_msg, rec: dict | None=None) -> bool:
    """Apply edit UI only after the linked finance record is safely present in local SQLite."""
    if not version_mode_feature('forward_copy_edit'):
        return False
    mode = forward_copy_edit_mode(int(source_chat_id))
    if rec is None:
        rec = find_record_by_message_id(int(dst_chat_id), int(dst_msg_id))
    if not rec:
        rec = _set_forward_record_metadata(dst_chat_id, dst_msg_id, source_chat_id, source_msg)
    if not rec:
        log_error(f'[FWD COPY UI] record not found: {source_chat_id}->{dst_chat_id}:{dst_msg_id} mode={mode}')
        return False
    try:
        rec['forward_source_chat_id'] = int(source_chat_id)
        rec['forward_source_msg_id'] = int(getattr(source_msg, 'message_id', 0) or 0)
        rec['forward_copy_content_type'] = str(getattr(source_msg, 'content_type', 'text') or 'text')
        ensure_finance_record_uid(int(dst_chat_id), rec)
        for _key, item in _finance_record_lists(get_chat_store(int(dst_chat_id))):
            if not isinstance(item, dict):
                continue
            same_id = int(item.get('id', -1)) == int(rec.get('id', -2))
            same_msg = int(item.get('source_msg_id') or item.get('origin_msg_id') or item.get('msg_id') or 0) == int(dst_msg_id)
            if same_id or same_msg:
                item.update(rec)
                ensure_finance_record_uid(int(dst_chat_id), item)
        if not persist_finance_chat_local_fast(int(dst_chat_id)):
            log_error(f'[FWD COPY UI] local finance persist failed: {source_chat_id}->{dst_chat_id}:{dst_msg_id}')
            return False
    except Exception as exc:
        log_error(f'apply_forward_copy_edit_ui metadata {source_chat_id}->{dst_chat_id}:{dst_msg_id}: {exc}')
        return False
    try:
        base_text = _message_text_for_finance(source_msg) or compose_edit_input_value(rec.get('amount'), rec.get('note', ''))
        display_text = _forward_copy_display_text(base_text, rec, mode)
        reply_markup = _forward_copy_edit_keyboard(mode)
        ct = str(getattr(source_msg, 'content_type', None) or rec.get('forward_copy_content_type') or 'text')
        if ct == 'text':
            _tg_call_retry(bot.edit_message_text, display_text, chat_id=int(dst_chat_id), message_id=int(dst_msg_id), reply_markup=reply_markup, attempts=3, purpose='forward_copy_edit_apply_text')
        elif ct in {'photo', 'video', 'document', 'audio', 'animation', 'voice'}:
            _tg_call_retry(bot.edit_message_caption, caption=display_text, chat_id=int(dst_chat_id), message_id=int(dst_msg_id), reply_markup=reply_markup, attempts=3, purpose='forward_copy_edit_apply_caption')
        else:
            _tg_call_retry(bot.edit_message_reply_markup, chat_id=int(dst_chat_id), message_id=int(dst_msg_id), reply_markup=reply_markup, attempts=3, purpose='forward_copy_edit_apply_markup')
        try:
            schedule_config_backup_for_chats(int(dst_chat_id), delay=0.5)
        except Exception:
            pass
        return True
    except Exception as exc:
        if 'message is not modified' in str(exc).lower():
            return True
        log_error(f'apply_forward_copy_edit_ui Telegram {source_chat_id}->{dst_chat_id}:{dst_msg_id}: {exc}')
        return False

def schedule_forward_copy_edit_ui_retry(source_chat_id: int, dst_chat_id: int, dst_msg_id: int, source_msg, rec: dict | None=None, delay: float=0.8):
    """Одна отложенная повторная попытка, если Telegram ещё не дал изменить свежую copyMessage."""
    key = f'forward-copy-ui:{int(dst_chat_id)}:{int(dst_msg_id)}'

    def _job():
        try:
            apply_forward_copy_edit_ui(int(source_chat_id), int(dst_chat_id), int(dst_msg_id), source_msg, rec=rec)
        except Exception as e:
            log_error(f'schedule_forward_copy_edit_ui_retry {source_chat_id}->{dst_chat_id}:{dst_msg_id}: {e}')
    DELAYED_SCHEDULER.cancel(key)
    DELAYED_SCHEDULER.schedule(key, float(delay), _job)

def _forward_copy_edit_wait_scheduler_key(chat_id: int) -> str:
    return f'forward-copy-edit-wait:{int(chat_id)}'

def _forward_copy_clean_copy_button(text: str):
    """Compatibility helper kept for old code paths; v125 uses the main edit insert UX."""
    return make_copy_or_inline_button('✍️ Вставить текст', '\n' + str(text or ''), viewer_chat_id=None)

def _forward_copy_edit_prompt_text(rec: dict, current: str) -> str:
    sid = str(rec.get('short_id') or 'R' + str(rec.get('id')))
    return wm_common(f'✏️ Редактирование записи {sid}\n\nТекущие данные:\n{current}\n\n✍️ Напишите новые данные.\nБудет изменена эта бот-копия и связанная финансовая запись.\n\n⏳ Это сообщение и режим редактирования будут автоматически отменены через 40 секунд.', 10)

def _forward_copy_edit_prompt_keyboard(current: str, day_key: str | None=None, chat_id: int | None=None):
    kb = types.InlineKeyboardMarkup()
    day_key = str(day_key or today_key())[:10]
    chat_type = ''
    try:
        if chat_id is not None:
            chat_type = str((get_chat_store(int(chat_id)).get('info') or {}).get('type') or '').lower()
    except Exception:
        chat_type = ''
    if current:
        kb.row(make_copy_or_inline_button('✍️ Вставить текст', '\n' + str(current), viewer_chat_id=chat_id))
    kb.row(IB('❌ Закрыть', callback_data='fwdcopy_edit_cancel'), IB('⬅️ Назад осн. окно', callback_data=f'd:{day_key}:back_main'))
    return kb

def refresh_active_forward_copy_edit_prompt(chat_id: int, dst_msg_id: int, rec: dict | None=None) -> bool:
    """Keep an already-open 💰Перес edit window synchronized with auto-edited bot copies."""
    try:
        chat_id = int(chat_id)
        dst_msg_id = int(dst_msg_id)
        store = get_chat_store(chat_id)
        wait = store.get('forward_copy_edit_wait') or {}
        if wait.get('type') != 'forward_copy_edit' or int(wait.get('dst_msg_id') or 0) != dst_msg_id:
            return False
        rec = rec or find_record_by_message_id(chat_id, dst_msg_id)
        if not isinstance(rec, dict):
            return False
        current = str(rec.get('source_finance_text') or '').strip()
        if not current:
            current = compose_edit_input_value(rec.get('amount'), rec.get('note', ''))
        wait['insert_text'] = current
        prompt = _forward_copy_edit_prompt_text(rec, current)
        wait['countdown_base_text'] = prompt
        store['forward_copy_edit_wait'] = wait
        prompt_id = int(wait.get('prompt_msg_id') or 0)
        if prompt_id:
            try:
                _tg_call_retry(bot.edit_message_text, prompt, chat_id=chat_id, message_id=prompt_id, reply_markup=_forward_copy_edit_prompt_keyboard(current, rec.get('day_key'), chat_id=chat_id), purpose='forward_copy_edit_prompt_refresh')
            except Exception as e:
                if 'message is not modified' not in str(e).lower():
                    log_error(f'refresh_active_forward_copy_edit_prompt({chat_id},{dst_msg_id}): {e}')
        return True
    except Exception as e:
        log_error(f'refresh_active_forward_copy_edit_prompt({chat_id},{dst_msg_id}): {e}')
        return False

def clear_forward_copy_edit_wait(chat_id: int, delete_prompt: bool=True):
    store = get_chat_store(int(chat_id))
    wait = store.get('forward_copy_edit_wait') or {}
    prompt_id = wait.get('prompt_msg_id')
    force_reply_msg_id = wait.get('force_reply_msg_id')
    DELAYED_SCHEDULER.cancel(_forward_copy_edit_wait_scheduler_key(int(chat_id)))
    store['forward_copy_edit_wait'] = None
    if delete_prompt:
        for _mid in (prompt_id, force_reply_msg_id):
            if not _mid:
                continue
            try:
                bot.delete_message(int(chat_id), int(_mid))
            except Exception:
                pass

def schedule_forward_copy_edit_wait_cancel(chat_id: int, prompt_message_id: int, delay: float | None=None):
    if delay is None:
        delay = internal_timer_seconds('input_wait', 40)

    def _job():
        try:
            store = get_chat_store(int(chat_id))
            wait = store.get('forward_copy_edit_wait') or {}
            if int(wait.get('prompt_msg_id') or 0) != int(prompt_message_id):
                return
            clear_forward_copy_edit_wait(int(chat_id), delete_prompt=True)
            bot_journal('forward_copy_edit_timeout', int(chat_id), f'prompt={prompt_message_id}; window deleted')
        except Exception as e:
            log_error(f'schedule_forward_copy_edit_wait_cancel({chat_id}): {e}')
    DELAYED_SCHEDULER.cancel(_forward_copy_edit_wait_scheduler_key(int(chat_id)))
    DELAYED_SCHEDULER.schedule(_forward_copy_edit_wait_scheduler_key(int(chat_id)), float(delay), _job)

def start_forward_copy_edit(chat_id: int, dst_msg_id: int) -> bool:
    rec = find_record_by_message_id(int(chat_id), int(dst_msg_id))
    if not rec:
        send_and_auto_delete(int(chat_id), '❌ Связанная финансовая запись не найдена.', 8)
        return False
    is_copy, _msg_id, source_chat_id, source_msg_id = _forward_copy_record_identity(int(chat_id), rec)
    if not is_copy:
        send_and_auto_delete(int(chat_id), '❌ Это сообщение не связано с бот-копией пересылки.', 8)
        return False
    _hydrate_legacy_forward_copy_metadata(int(chat_id), rec, int(dst_msg_id), source_chat_id, source_msg_id)
    current = str(rec.get('source_finance_text') or '').strip()
    if not current:
        if float(rec.get('usd_amount', 0) or 0) and bool(rec.get('usd_only', False)):
            current = compose_edit_input_value(rec.get('usd_amount'), rec.get('usd_note') or rec.get('note', ''))
        else:
            current = compose_edit_input_value(rec.get('amount'), rec.get('note', ''))
    prompt = _forward_copy_edit_prompt_text(rec, current)
    sent = _tg_call_retry(bot.send_message, int(chat_id), prompt, reply_markup=_forward_copy_edit_prompt_keyboard(current, rec.get('day_key'), chat_id=int(chat_id)), purpose='forward_copy_edit_prompt')
    force_msg_id = 0
    get_chat_store(int(chat_id))['forward_copy_edit_wait'] = {'type': 'forward_copy_edit', 'dst_msg_id': int(dst_msg_id), 'rid': int(rec.get('id')), 'record_uid': ensure_finance_record_uid(int(chat_id), rec), 'source_chat_id': int(source_chat_id or 0), 'prompt_msg_id': int(sent.message_id), 'force_reply_msg_id': int(force_msg_id or 0), 'insert_text': current, 'countdown_base_text': prompt, 'expires_at': time.time() + 40}
    schedule_forward_copy_edit_wait_cancel(int(chat_id), int(sent.message_id), None)
    return True

# R48 FINAL: removed dead legacy owner edit_forward_copy_and_record; final owner is loaded later.

def _has_visible_fin_mode_selected(chat_id: int) -> bool:
    """v108: visible auto-window selection is independent from hidden accounting."""
    try:
        return bool(is_finance_mode(chat_id) and finance_window_mode(chat_id) in {'normal', 'open', 'first'})
    except Exception:
        return False

def _v177_legacy_0152_ensure_hidden_finance_for_forward_dst(dst_chat_id: int):
    """💰 forwarding enables hidden accounting without touching an already selected visible window mode."""
    try:
        dst_chat_id = int(dst_chat_id)
        was_finance = is_finance_mode(dst_chat_id)
        if not was_finance:
            set_finance_mode(dst_chat_id, True)
            set_finance_window_mode(dst_chat_id, 'off', persist_now=False)
        if not is_hidden_finance_mode(dst_chat_id):
            set_hidden_finance_mode(dst_chat_id, True)
        _persist_finance_window_mode_critical(dst_chat_id)
        bot_journal('forward_finance_auto_hidden', dst_chat_id, '💰 учёт пересылки включил скрытые финансы; оконный режим сохранён')
    except Exception as e:
        log_error(f'ensure_hidden_finance_for_forward_dst({dst_chat_id}): {e}')
try:
    _v177_legacy_0152_ensure_hidden_finance_for_forward_dst.__name__ = 'ensure_hidden_finance_for_forward_dst'
except Exception:
    pass

def _v177_legacy_0153_set_forward_finance(src_chat_id: int, dst_chat_id: int, enabled: bool):
    ff = data.setdefault('forward_finance', {})
    src = str(src_chat_id)
    dst = str(dst_chat_id)
    ff.setdefault(src, {})[dst] = bool(enabled)
    if bool(enabled):
        ensure_hidden_finance_for_forward_dst(int(dst_chat_id))
    persist_forward_rules_to_owner()
    save_data(data)
    schedule_config_backup_for_chats(src_chat_id, dst_chat_id)
try:
    _v177_legacy_0153_set_forward_finance.__name__ = 'set_forward_finance'
except Exception:
    pass

def _v177_legacy_0154_remove_forward_finance(src_chat_id: int, dst_chat_id: int):
    ff = data.setdefault('forward_finance', {})
    src = str(src_chat_id)
    dst = str(dst_chat_id)
    if src in ff and dst in ff[src]:
        del ff[src][dst]
    if src in ff and (not ff[src]):
        del ff[src]
    persist_forward_rules_to_owner()
    save_data(data)
    schedule_config_backup_for_chats(src_chat_id, dst_chat_id)
try:
    _v177_legacy_0154_remove_forward_finance.__name__ = 'remove_forward_finance'
except Exception:
    pass

def _forward_key(src_chat_id: int, src_msg_id: int) -> str:
    return f'{int(src_chat_id)}:{int(src_msg_id)}'

def _schedule_persist_forward_state(delay: float=0.25):
    global _forward_state_timer

    def _job():
        try:
            save_data(data, root_only=True)
        except Exception as e:
            log_error(f'_schedule_persist_forward_state: {e}')
    scheduler_key = 'forward-state-save'
    DELAYED_SCHEDULER.cancel(scheduler_key)
    _forward_state_timer = DELAYED_SCHEDULER.schedule(scheduler_key, delay, _job)

def _persist_forward_index_in_data(d: dict):
    with forward_map_lock:
        idx = {}
        for (src_chat_id, src_msg_id), pairs in forward_map.items():
            rows = []
            for pair in pairs:
                if not isinstance(pair, (list, tuple)) or len(pair) < 2:
                    continue
                dst_chat_id, dst_msg_id = (pair[0], pair[1])
                rows.append({'dst_chat_id': int(dst_chat_id), 'dst_msg_id': int(dst_msg_id), 'status': 'delivered'})
            if rows:
                idx[_forward_key(src_chat_id, src_msg_id)] = rows
        d['forward_index'] = idx

def _load_forward_index_from_data(d: dict):
    with forward_map_lock:
        forward_map.clear()
        idx = d.get('forward_index', {}) or {}
        for key, rows in idx.items():
            try:
                src_chat_id_s, src_msg_id_s = str(key).split(':', 1)
                src_chat_id = int(src_chat_id_s)
                src_msg_id = int(src_msg_id_s)
            except Exception:
                continue
            pairs = []
            for row in rows or []:
                try:
                    dst_chat_id = int(row.get('dst_chat_id'))
                    dst_msg_id = int(row.get('dst_msg_id'))
                    pairs.append((dst_chat_id, dst_msg_id))
                except Exception:
                    continue
            if pairs:
                forward_map[src_chat_id, src_msg_id] = pairs

def _store_forward_link(src_chat_id: int, src_msg_id: int, dst_chat_id: int, dst_msg_id: int):
    with forward_map_lock:
        key = (int(src_chat_id), int(src_msg_id))
        pair = (int(dst_chat_id), int(dst_msg_id))
        items = forward_map.setdefault(key, [])
        if pair not in items:
            items.append(pair)
    _schedule_persist_forward_state()

def _v177_legacy_0155_persist_forward_finance_delivery_now(src_chat_id: int, src_msg_id: int, dst_chat_id: int, dst_msg_id: int, rec: dict | None=None):
    """v260: synchronously commit only the local exact-once binding; remote backup is async."""
    try:
        if isinstance(rec, dict):
            tags = {'forwarded_by_bot': True, 'forward_source_chat_id': int(src_chat_id), 'forward_source_msg_id': int(src_msg_id), 'forward_dst_chat_id': int(dst_chat_id), 'forward_dst_msg_id': int(dst_msg_id), 'operation_key': _v260_forward_finance_operation_key(src_chat_id, src_msg_id, dst_chat_id)}
            rec.update(tags)
            store = get_chat_store(int(dst_chat_id)); rid = rec.get('id')
            for arr in (store.get('daily_records', {}) or {}).values():
                for rr in arr or []:
                    if isinstance(rr, dict) and rr.get('id') == rid: rr.update(tags)
            try: _remember_finance_source_identity_v257(int(dst_chat_id), rec, int(dst_msg_id), 'records')
            except Exception: pass
            if 'persist_finance_chat_local_fast' in globals() and not persist_finance_chat_local_fast(int(dst_chat_id)):
                raise RuntimeError('local finance SQLite commit failed')
            _v260_forward_finance_op_mark(src_chat_id, src_msg_id, dst_chat_id, 'committed', dst_msg_id=int(dst_msg_id), record_uid=str(rec.get('record_uid') or ''), record_id=int(rec.get('id') or 0))
        _persist_forward_index_in_data(data)
        try:
            pool = globals().get('BACKGROUND_TASK_POOL')
            if pool is not None:
                pool.submit_unique(f'fwd-root-v260:{src_chat_id}:{src_msg_id}:{dst_chat_id}', save_data, data, root_only=True)
        except Exception:
            pass
        def _remote_after_local():
            try:
                ok = persist_critical_delta_now(int(dst_chat_id))
                if not ok: schedule_quick_backup(int(dst_chat_id), MEGA_DELTA_PRIORITY_DELAY_SECONDS)
            except Exception as exc:
                log_error(f'[FWD FINANCE ASYNC BACKUP] {src_chat_id}:{src_msg_id}->{dst_chat_id}:{dst_msg_id}: {exc}')
        try:
            pool = globals().get('DELTA_TASK_POOL') or globals().get('BACKGROUND_TASK_POOL')
            if pool is not None:
                pool.submit_unique(f'fwd-delta-v260:{src_chat_id}:{src_msg_id}:{dst_chat_id}', _remote_after_local)
        except Exception:
            pass
        log_info(f'[FWD FINANCE DURABLE] local committed; remote async {src_chat_id}:{src_msg_id} -> {dst_chat_id}:{dst_msg_id}')
        return True
    except Exception as e:
        _v260_forward_finance_op_mark(src_chat_id, src_msg_id, dst_chat_id, 'partial_finance_missing', dst_msg_id=int(dst_msg_id), last_error=str(e)[:300])
        log_error(f'[FWD FINANCE DURABLE ERROR] {src_chat_id}:{src_msg_id} -> {dst_chat_id}:{dst_msg_id}: {e}')
        return False

try:
    _v177_legacy_0155_persist_forward_finance_delivery_now.__name__ = '_persist_forward_finance_delivery_now'
except Exception:
    pass

def _rebuild_forward_index_from_finance_records(d: dict) -> int:
    """После restore восстанавливает forward_index, сканируя по одному чату без удержания всей истории в RAM."""
    added = 0
    try:
        with forward_map_lock:
            for cid, store in ((d or {}).get('chats', {}) or {}).items():
                if not isinstance(store, dict):
                    continue
                try:
                    cid_i = int(cid)
                except Exception:
                    continue
                if LOWRAM_ENABLED and (not dict.__contains__(store, 'records')):
                    rows = SQLITE.get_cold(cid_i, 'records', []) or []
                else:
                    rows = store.get('records', []) or []
                for rec in rows:
                    if not isinstance(rec, dict) or not rec.get('forwarded_by_bot'):
                        continue
                    try:
                        src_chat = int(rec.get('forward_source_chat_id'))
                        src_msg = int(rec.get('forward_source_msg_id'))
                        dst_chat = int(rec.get('forward_dst_chat_id') or cid_i)
                        dst_msg = int(rec.get('forward_dst_msg_id') or rec.get('source_msg_id') or rec.get('msg_id'))
                    except Exception:
                        continue
                    key = (src_chat, src_msg)
                    pair = (dst_chat, dst_msg)
                    rows_map = forward_map.setdefault(key, [])
                    if pair not in rows_map:
                        rows_map.append(pair)
                        added += 1
                rows = None
            if added:
                _persist_forward_index_in_data(d)
        if added:
            log_info(f'[FORWARD INDEX RECOVERY] rebuilt {added} links from SQLite finance records')
        return added
    except Exception as e:
        log_error(f'_rebuild_forward_index_from_finance_records: {e}')
        return 0

def get_forward_links(src_chat_id: int, src_msg_id: int):
    with forward_map_lock:
        return list(forward_map.get((int(src_chat_id), int(src_msg_id)), []))

def delete_forward_copies_for_source(src_chat_id: int, src_msg_id: int):
    key = (int(src_chat_id), int(src_msg_id))
    with forward_map_lock:
        links = list(forward_map.get(key, []))
    for dst_chat_id, dst_msg_id in links:
        try:
            bot.delete_message(dst_chat_id, dst_msg_id)
        except Exception as e:
            log_error(f'delete_forward_copies_for_source {src_chat_id}:{src_msg_id} -> {dst_chat_id}:{dst_msg_id}: {e}')
        try:
            delete_forwarded_finance_record_by_msg_id(dst_chat_id, dst_msg_id)
        except Exception as e:
            log_error(f'delete_forwarded_finance_record_by_msg_id {dst_chat_id}:{dst_msg_id}: {e}')
    with forward_map_lock:
        if key in forward_map:
            del forward_map[key]
            _schedule_persist_forward_state()

def is_forward_delete_command(text: str) -> bool:
    t = (text or '').strip().lower()
    return t in ('/del', '/дел', '/д')

def _finance_record_lists(store: dict):
    """Active + persistent currency ledgers, active first; duplicate objects are skipped."""
    seen = set()
    for key in ('records', 'ars_records', 'usd_records'):
        arr = store.get(key, []) or []
        if not isinstance(arr, list):
            continue
        for rec in arr:
            if not isinstance(rec, dict):
                continue
            oid = id(rec)
            if oid in seen:
                continue
            seen.add(oid)
            yield (key, rec)

def _finance_source_index_v257(store: dict) -> dict:
    idx = store.setdefault('_finance_source_index_v257', {})
    if not isinstance(idx, dict):
        idx = {}
        store['_finance_source_index_v257'] = idx
    return idx


def _record_message_ids_v257(rec: dict) -> set[int]:
    out = set()
    for key in ('forward_dst_msg_id', 'source_msg_id', 'origin_msg_id', 'msg_id', 'source_order_msg_id'):
        try:
            value = int((rec or {}).get(key) or 0)
            if value: out.add(value)
        except Exception:
            pass
    try:
        op = str((rec or {}).get('operation_key') or '')
        m = re.fullmatch(r'finance:-?\d+:[^:]+:(\d+)', op)
        if m: out.add(int(m.group(1)))
    except Exception:
        pass
    return out


def _remember_finance_source_identity_v257(chat_id: int, rec: dict, msg_id: int | None=None, ledger: str='records') -> bool:
    if not isinstance(rec, dict):
        return False
    try:
        cid = int(chat_id)
        mid = int(msg_id or 0)
    except Exception:
        return False
    if not mid:
        mids = _record_message_ids_v257(rec)
        mid = min(mids) if mids else 0
    if not mid:
        return False
    store = get_chat_store(cid)
    try:
        uid = ensure_finance_record_uid(cid, rec) if 'ensure_finance_record_uid' in globals() else str(rec.get('record_uid') or '')
    except Exception:
        uid = str(rec.get('record_uid') or '')
    row = {'record_uid': str(uid or ''), 'id': int(rec.get('id') or 0), 'ledger': str(ledger or 'records'), 'operation_key': str(rec.get('operation_key') or '')}
    _finance_source_index_v257(store)[str(mid)] = row
    # Heal old restored records: message identity is immutable and must not vanish.
    for key in ('source_msg_id', 'origin_msg_id', 'msg_id'):
        if not rec.get(key): rec[key] = mid
    if not rec.get('source_order_msg_id'): rec['source_order_msg_id'] = mid
    if not rec.get('operation_key') and 'finance_operation_key' in globals():
        try: rec['operation_key'] = finance_operation_key(cid, mid, 'main')
        except Exception: pass
    return True


def _record_has_message_id(rec: dict, msg_id: int) -> bool:
    try:
        mid = int(msg_id)
    except Exception:
        return False
    return mid in _record_message_ids_v257(rec)


def find_record_by_message_id(chat_id: int, msg_id: int):
    cid = int(chat_id); mid = int(msg_id)
    store = get_chat_store(cid)
    for key, r in _finance_record_lists(store):
        if _record_has_message_id(r, mid):
            _remember_finance_source_identity_v257(cid, r, mid, key)
            return r
    # Redundant persistent index survives deployment and heals a partially
    # normalized/restored record that lost one of its legacy message-id aliases.
    ref = _finance_source_index_v257(store).get(str(mid)) or {}
    uid = str(ref.get('record_uid') or '').strip().upper()
    rid = int(ref.get('id') or 0) if str(ref.get('id') or '').lstrip('-').isdigit() else 0
    ledger = str(ref.get('ledger') or '')
    for key, r in _finance_record_lists(store):
        try:
            if uid and str(r.get('record_uid') or '').strip().upper() == uid:
                _remember_finance_source_identity_v257(cid, r, mid, key); return r
            if rid and key == ledger and int(r.get('id') or 0) == rid:
                _remember_finance_source_identity_v257(cid, r, mid, key); return r
        except Exception:
            pass
    return None


def migrate_finance_source_index_v257(chat_id: int) -> int:
    cid=int(chat_id); store=get_chat_store(cid); changed=0
    for key, rec in _finance_record_lists(store):
        mids=_record_message_ids_v257(rec)
        for mid in mids:
            before=dict(_finance_source_index_v257(store).get(str(mid)) or {})
            if _remember_finance_source_identity_v257(cid, rec, mid, key):
                after=_finance_source_index_v257(store).get(str(mid)) or {}
                if before != after: changed += 1
    return changed


def delete_forwarded_finance_record_by_msg_id(chat_id: int, msg_id: int) -> bool:
    with locked_chat(chat_id):
        rec = find_record_by_message_id(chat_id, msg_id)
        if not rec: return False
        rid = int(rec['id']); day_key = rec.get('day_key') or today_key()
    delete_record_in_chat(chat_id, rid)
    schedule_finalize(chat_id, day_key)
    return True



def rebind_forwarded_finance_record(chat_id: int, old_msg_id: int, new_msg_id: int, text: str, owner: int=0, source_msg=None):
    found=False; day_key=None
    with locked_chat(chat_id):
        store=get_chat_store(chat_id)
        rec=find_record_by_message_id(chat_id,old_msg_id)
        if rec is None and source_msg is not None:
            rec=_v260_find_forward_finance_record(int(chat_id),int(old_msg_id),source_msg)
        if rec:
            found=True
            rec['source_msg_id']=new_msg_id; rec['origin_msg_id']=new_msg_id; rec['msg_id']=new_msg_id; rec['source_finance_text']=str(text or '').strip()
            if text and looks_like_amount(text):
                try:
                    comp=parse_financial_components(text); rec['amount']=comp.get('amount',0.0); rec['note']=comp.get('note','')
                    if comp.get('usd_amount') is not None:
                        rec['usd_amount']=float(comp.get('usd_amount') or 0); rec['usd_note']=str(comp.get('usd_note') or ''); rec['usd_only']=bool(comp.get('usd_only',False))
                    elif rec.get('usd_amount') is not None:
                        rec['usd_amount']=0.0; rec['usd_note']=''; rec['usd_only']=False
                except Exception: pass
            rec_id=rec.get('id')
            for _day,arr in store.get('daily_records',{}).items():
                for item in arr:
                    if item.get('id')==rec_id: item.update(rec)
            store['balance']=sum((r.get('amount',0) for r in store.get('records',[])))
            day_key=rec.get('day_key') or today_key()
    if found:
        persist_finance_chat_local_fast(int(chat_id))
        schedule_finalize(chat_id,day_key)
        return True
    if text and looks_like_amount(text):
        return bool(sync_forwarded_finance_message(chat_id,new_msg_id,text,owner,source_msg=source_msg))
    return False


def _replace_forward_link_pair(src_chat_id: int, src_msg_id: int, old_dst_chat_id: int, old_dst_msg_id: int, new_dst_chat_id: int, new_dst_msg_id: int):
    with forward_map_lock:
        key = (int(src_chat_id), int(src_msg_id))
        pairs = list(forward_map.get(key, []))
        updated = []
        replaced = False
        for pair in pairs:
            if int(pair[0]) == int(old_dst_chat_id) and int(pair[1]) == int(old_dst_msg_id):
                updated.append((int(new_dst_chat_id), int(new_dst_msg_id)))
                replaced = True
            else:
                updated.append(pair)
        if not replaced:
            updated.append((int(new_dst_chat_id), int(new_dst_msg_id)))
        forward_map[key] = updated
    _schedule_persist_forward_state()

def _v212_task_reconcile_forward_copy(dst_chat_id: int, dst_msg_id: int, source_chat_id: int, source_msg, *, is_edit: bool=False, previous_message_id: int=0):
    fn = globals().get('task_reconcile_source_message')
    if not callable(fn):
        return None
    try:
        body = str(_message_text_for_finance(source_msg) or getattr(source_msg, 'caption', None) or getattr(source_msg, 'text', None) or '')
        sender = getattr(source_msg, 'from_user', None)
        return fn(int(dst_chat_id), int(dst_msg_id), body, original_date=(globals().get('_v172_now')() if callable(globals().get('_v172_now')) else now_local()) if not is_edit else getattr(source_msg, 'date', None), sender_id=int(getattr(sender, 'id', 0) or 0), sender_name=getattr(sender, 'first_name', '') or getattr(sender, 'username', '') or '', sender_is_bot=True, trusted_forwarding_copy=True, origin_chat_id=int(source_chat_id), origin_message_id=int(getattr(source_msg, 'message_id', 0) or 0), is_edit=bool(is_edit), previous_message_id=int(previous_message_id or 0), content_type=str(getattr(source_msg, 'content_type', '') or 'text'))
    except Exception as exc:
        try:
            log_error(f'v212 forwarding task reconcile {dst_chat_id}:{dst_msg_id}: {exc}')
        except Exception:
            pass
        return None

def _v260_forward_finance_op_key(source_chat_id: int, source_msg_id: int, dst_chat_id: int) -> str:
    return f"{int(source_chat_id)}:{int(source_msg_id)}:{int(dst_chat_id)}"

def _v260_forward_finance_operation_key(source_chat_id: int, source_msg_id: int, dst_chat_id: int) -> str:
    return f"fwd-fin:{int(source_chat_id)}:{int(source_msg_id)}:{int(dst_chat_id)}"

def _v260_forward_finance_op_get(source_chat_id: int, source_msg_id: int, dst_chat_id: int) -> dict:
    try:
        return SQLITE.get_meta('forward_finance_ops_v260', _v260_forward_finance_op_key(source_chat_id, source_msg_id, dst_chat_id), {}) or {}
    except Exception:
        return {}

def _v260_forward_finance_op_mark(source_chat_id: int, source_msg_id: int, dst_chat_id: int, state: str, **extra) -> dict:
    key = _v260_forward_finance_op_key(source_chat_id, source_msg_id, dst_chat_id)
    row = _v260_forward_finance_op_get(source_chat_id, source_msg_id, dst_chat_id)
    row.update({
        'source_chat_id': int(source_chat_id), 'source_msg_id': int(source_msg_id),
        'dst_chat_id': int(dst_chat_id), 'state': str(state or ''),
        'updated_at': now_local().isoformat(timespec='milliseconds'),
        'operation_key': _v260_forward_finance_operation_key(source_chat_id, source_msg_id, dst_chat_id),
    })
    row.update({k:v for k,v in extra.items() if v is not None})
    try:
        SQLITE.set_meta('forward_finance_ops_v260', key, row)
    except Exception as exc:
        log_error(f'[FWD FIN V260] op persist {key}: {exc}')
    return row

def _v260_find_forward_finance_record(dst_chat_id: int, dst_msg_id: int, source_msg=None):
    try:
        rec = find_record_by_message_id(int(dst_chat_id), int(dst_msg_id))
        if isinstance(rec, dict):
            return rec
    except Exception:
        pass
    if source_msg is None:
        return None
    try:
        src_chat_id = int(getattr(getattr(source_msg, 'chat', None), 'id', 0) or 0)
        src_msg_id = int(getattr(source_msg, 'forward_source_msg_id', 0) or getattr(source_msg, 'message_id', 0) or 0)
    except Exception:
        return None
    if not src_chat_id or not src_msg_id:
        return None
    op_key = _v260_forward_finance_operation_key(src_chat_id, src_msg_id, int(dst_chat_id))
    try:
        rec = find_record_by_operation_key(int(dst_chat_id), op_key)
        if isinstance(rec, dict):
            return rec
    except Exception:
        pass
    try:
        for _ledger, rec in _finance_record_lists(int(dst_chat_id)):
            if not isinstance(rec, dict):
                continue
            if int(rec.get('forward_source_chat_id') or 0) == src_chat_id and int(rec.get('forward_source_msg_id') or 0) == src_msg_id:
                return rec
    except Exception:
        pass
    return None

def _v260_bind_forward_finance_record(rec: dict, source_msg, dst_chat_id: int, dst_msg_id: int) -> dict:
    if not isinstance(rec, dict) or source_msg is None:
        return rec
    try:
        src_chat_id = int(getattr(getattr(source_msg, 'chat', None), 'id', 0) or 0)
        src_msg_id = int(getattr(source_msg, 'forward_source_msg_id', 0) or getattr(source_msg, 'message_id', 0) or 0)
    except Exception:
        return rec
    if not src_chat_id or not src_msg_id:
        return rec
    rec.update({
        'forwarded_by_bot': True,
        'forward_source_chat_id': src_chat_id,
        'forward_source_msg_id': src_msg_id,
        'forward_dst_chat_id': int(dst_chat_id),
        'forward_dst_msg_id': int(dst_msg_id),
        'operation_key': _v260_forward_finance_operation_key(src_chat_id, src_msg_id, int(dst_chat_id)),
    })
    try:
        _remember_finance_source_identity_v257(int(dst_chat_id), rec, int(dst_msg_id), 'records')
    except Exception:
        pass
    return rec

def _v260_make_forward_shadow(source_chat_id: int, source_msg_id: int, dst_chat_id: int, dst_msg_id: int, owner: int=0, source_date=None):
    chat = type('ForwardSourceChatV260', (), {'id': int(source_chat_id)})()
    user = type('ForwardSourceUserV260', (), {'id': int(owner or 0)})()
    return type('ForwardShadowMsgV260', (), {
        'message_id': int(dst_msg_id),
        'date': source_date if source_date is not None else int(time.time()),
        'forward_source_msg_id': int(source_msg_id),
        'source_order_msg_id': int(source_msg_id),
        'forward_source_chat_id': int(source_chat_id),
        'forward_dst_chat_id': int(dst_chat_id),
        'forward_dst_msg_id': int(dst_msg_id),
        'finance_operation_key_override': _v260_forward_finance_operation_key(source_chat_id, source_msg_id, dst_chat_id),
        'chat': chat,
        'from_user': user,
    })()

def _v260_finance_forward_repair(source_chat_id: int, source_msg_id: int, dst_chat_id: int, dst_msg_id: int, text: str, owner: int=0, source_date=None, attempt: int=0):
    try:
        current = _v260_find_forward_finance_record(int(dst_chat_id), int(dst_msg_id), _v260_make_forward_shadow(source_chat_id, source_msg_id, dst_chat_id, dst_msg_id, owner, source_date))
        if isinstance(current, dict):
            _v260_bind_forward_finance_record(current, _v260_make_forward_shadow(source_chat_id, source_msg_id, dst_chat_id, dst_msg_id, owner, source_date), dst_chat_id, dst_msg_id)
            persist_finance_chat_local_fast(int(dst_chat_id))
            _v260_forward_finance_op_mark(source_chat_id, source_msg_id, dst_chat_id, 'committed', dst_msg_id=int(dst_msg_id), record_uid=str(current.get('record_uid') or ''), repaired=True)
            return True
        shadow = _v260_make_forward_shadow(source_chat_id, source_msg_id, dst_chat_id, dst_msg_id, owner, source_date)
        rec = sync_forwarded_finance_message(int(dst_chat_id), int(dst_msg_id), str(text or ''), int(owner or 0), source_msg=shadow)
        if isinstance(rec, dict):
            _persist_forward_finance_delivery_now(source_chat_id, source_msg_id, dst_chat_id, dst_msg_id, rec)
            bot_journal('forward_finance_partial_repaired_v260', int(dst_chat_id), f'src={source_chat_id}:{source_msg_id}; dst={dst_chat_id}:{dst_msg_id}; attempt={attempt}')
            return True
    except Exception as exc:
        log_error(f'[FWD FIN V260] repair attempt={attempt} {source_chat_id}:{source_msg_id}->{dst_chat_id}:{dst_msg_id}: {exc}')
    if int(attempt) < 5:
        delay = (1.0, 3.0, 8.0, 20.0, 45.0, 90.0)[min(int(attempt), 5)]
        try:
            DELAYED_SCHEDULER.schedule(f'finfwd-v260:{source_chat_id}:{source_msg_id}:{dst_chat_id}', delay, _v260_finance_forward_repair, source_chat_id, source_msg_id, dst_chat_id, dst_msg_id, text, owner, source_date, int(attempt)+1)
        except Exception:
            pass
    else:
        _v260_forward_finance_op_mark(source_chat_id, source_msg_id, dst_chat_id, 'needs_review', dst_msg_id=int(dst_msg_id), last_error='repair exhausted')
    return False

def _v260_schedule_finance_forward_repair(source_chat_id: int, source_msg_id: int, dst_chat_id: int, dst_msg_id: int, text: str, owner: int=0, source_date=None, attempt: int=0):
    _v260_forward_finance_op_mark(source_chat_id, source_msg_id, dst_chat_id, 'partial_finance_missing', dst_msg_id=int(dst_msg_id), text=str(text or '')[:4000], owner=int(owner or 0), source_date=source_date)
    try:
        DELAYED_SCHEDULER.schedule(f'finfwd-v260:{source_chat_id}:{source_msg_id}:{dst_chat_id}', 0.6, _v260_finance_forward_repair, source_chat_id, source_msg_id, dst_chat_id, dst_msg_id, text, owner, source_date, attempt)
        return True
    except Exception as exc:
        log_error(f'[FWD FIN V260] repair schedule: {exc}')
        return False

def recover_partial_finance_forwards_v260(limit: int=200) -> int:
    rows=[]
    try:
        raw_rows=SQLITE._read_all("SELECT k,v FROM meta WHERE kind='forward_finance_ops_v260'")
        for _k,_v in raw_rows:
            try: row=json.loads(_v) if isinstance(_v,str) else _v
            except Exception: continue
            if isinstance(row,dict) and row.get('state') in {'copy_delivered','partial_finance_missing','repairing'}:
                rows.append(row)
    except Exception:
        return 0
    submitted=0
    for row in rows[:max(1,int(limit))]:
        try:
            if _v260_schedule_finance_forward_repair(int(row['source_chat_id']),int(row['source_msg_id']),int(row['dst_chat_id']),int(row.get('dst_msg_id') or 0),str(row.get('text') or ''),int(row.get('owner') or 0),row.get('source_date'),0): submitted+=1
        except Exception: pass
    return submitted

def sync_edited_copy_to_target(source_chat_id: int, msg, dst_chat_id: int, dst_msg_id: int, finance_enabled: bool):
    text = _message_text_for_finance(msg)
    ct = getattr(msg, 'content_type', None)
    owner_id = msg.from_user.id if getattr(msg, 'from_user', None) else 0
    rec = find_record_by_message_id(dst_chat_id, dst_msg_id) if finance_enabled else None
    edit_mode = forward_copy_edit_mode(source_chat_id) if finance_enabled else 'normal'
    display_text = _forward_copy_display_text(text, rec, edit_mode) if rec else text
    edit_markup = _forward_copy_edit_keyboard(edit_mode) if finance_enabled else None
    try:
        if is_total_secret_mode(int(dst_chat_id)):
            hidden_ok = sync_forwarded_secret_bot_copy_edit(int(dst_chat_id), int(dst_msg_id), int(source_chat_id), msg)
            if hidden_ok:
                if finance_enabled and text and is_finance_mode(int(dst_chat_id)):
                    sync_forwarded_finance_message(int(dst_chat_id), int(dst_msg_id), text, owner_id, source_msg=msg)
                return int(dst_msg_id)
            raise RuntimeError(f'TOTAL SECRET edit could not be stored safely for {dst_chat_id}:{dst_msg_id}')
    except Exception as secret_exc:
        try:
            if is_total_secret_mode(int(dst_chat_id)):
                log_error(f'sync_edited_copy_to_target secret-safe failed {dst_chat_id}:{dst_msg_id}: {secret_exc}')
                _notify_forward_failure(source_chat_id, msg.message_id, dst_chat_id, secret_exc)
                return None
        except Exception:
            pass
    try:
        if ct == 'text':
            try:
                bot.edit_message_text(display_text, chat_id=dst_chat_id, message_id=dst_msg_id, reply_markup=edit_markup)
            except Exception as e:
                err = str(e).lower()
                if 'message is not modified' not in err:
                    raise
        elif ct in ('photo', 'video', 'document', 'audio', 'animation'):
            media = _build_input_media_from_message(msg)
            if not media:
                raise RuntimeError(f'Unsupported edited media content_type={ct}')
            try:
                bot.edit_message_media(media=media, chat_id=dst_chat_id, message_id=dst_msg_id)
            except Exception as e:
                err = str(e).lower()
                if 'message is not modified' not in err:
                    raise
        elif getattr(msg, 'caption', None):
            try:
                bot.edit_message_caption(caption=display_text, chat_id=dst_chat_id, message_id=dst_msg_id, reply_markup=edit_markup)
            except Exception as e:
                err = str(e).lower()
                if 'message is not modified' not in err:
                    raise
        else:
            raise RuntimeError(f'Edited sync unsupported for content_type={ct}')
        if finance_enabled and text and is_finance_mode(dst_chat_id):
            sync_forwarded_finance_message(dst_chat_id, dst_msg_id, text, owner_id, source_msg=msg)
            apply_forward_copy_edit_ui(source_chat_id, dst_chat_id, dst_msg_id, msg)
        _v212_task_reconcile_forward_copy(dst_chat_id, dst_msg_id, source_chat_id, msg, is_edit=True)
        return dst_msg_id
    except Exception as e:
        log_error(f'sync_edited_copy_to_target direct edit failed {dst_chat_id}:{dst_msg_id}: {e}')
    reply_to_target_id = None
    try:
        reply_to_msg = getattr(msg, 'reply_to_message', None)
        if reply_to_msg is not None:
            reply_to_target_id = resolve_reply_target_message_id(source_chat_id, getattr(reply_to_msg, 'message_id', None), dst_chat_id)
    except Exception:
        pass
    try:
        try:
            bot.delete_message(dst_chat_id, dst_msg_id)
        except Exception:
            pass
        sent_msg = _fallback_send_single(dst_chat_id, msg, reply_to_message_id=reply_to_target_id)
        new_dst_msg_id = sent_msg.message_id
        _replace_forward_link_pair(source_chat_id, msg.message_id, dst_chat_id, dst_msg_id, dst_chat_id, new_dst_msg_id)
        if finance_enabled and is_finance_mode(dst_chat_id):
            rebind_forwarded_finance_record(dst_chat_id, dst_msg_id, new_dst_msg_id, text, owner_id, source_msg=msg)
        _v212_task_reconcile_forward_copy(dst_chat_id, new_dst_msg_id, source_chat_id, msg, is_edit=True, previous_message_id=dst_msg_id)
        return new_dst_msg_id
    except Exception as e:
        _notify_forward_failure(source_chat_id, msg.message_id, dst_chat_id, e)
        return None

def _cleanup_forward_storage_for_chat(chat_id: int):
    chat_id = int(chat_id)
    with forward_map_lock:
        for key in list(forward_map.keys()):
            src_chat_id, _ = key
            if src_chat_id == chat_id:
                del forward_map[key]
                continue
            pairs = [pair for pair in forward_map.get(key, []) if int(pair[0]) != chat_id]
            if pairs:
                forward_map[key] = pairs
            elif key in forward_map:
                del forward_map[key]
    _schedule_persist_forward_state()

def _telegram_migrate_to_chat_id(err: Exception):
    """Возвращает новый chat_id, когда Telegram сообщает migration group -> supergroup."""
    try:
        result_json = getattr(err, 'result_json', None) or {}
        params = result_json.get('parameters') or {}
        value = params.get('migrate_to_chat_id')
        if value is not None:
            return int(value)
    except Exception:
        pass
    text = str(err or '')
    for pat in ('"migrate_to_chat_id"\\s*:\\s*(-?\\d+)', 'migrate_to_chat_id\\s*[=:]\\s*(-?\\d+)'):
        m = re.search(pat, text, re.I)
        if m:
            try:
                return int(m.group(1))
            except Exception:
                pass
    return None

def _merge_chat_store_for_migration(old_id: int, new_id: int):
    chats = data.setdefault('chats', {})
    old_key, new_key = (str(int(old_id)), str(int(new_id)))
    old_store = chats.get(old_key)
    new_store = chats.get(new_key)
    if not isinstance(old_store, dict):
        return
    if not isinstance(new_store, dict):
        chats[new_key] = old_store
    else:
        for k, v in old_store.items():
            if k not in new_store or new_store.get(k) in (None, '', [], {}):
                new_store[k] = v
        for list_key in ('records', 'ars_records', 'usd_records'):
            old_rows = old_store.get(list_key) or []
            new_rows = new_store.setdefault(list_key, [])
            seen = {(r.get('id'), r.get('source_msg_id'), r.get('origin_msg_id')) for r in new_rows if isinstance(r, dict)}
            for r in old_rows:
                if not isinstance(r, dict):
                    continue
                sig = (r.get('id'), r.get('source_msg_id'), r.get('origin_msg_id'))
                if sig not in seen:
                    new_rows.append(r)
                    seen.add(sig)
        for daily_key in ('daily_records', 'ars_daily_records', 'usd_daily_records'):
            od = old_store.get(daily_key) or {}
            nd = new_store.setdefault(daily_key, {})
            for day, rows in od.items():
                dest = nd.setdefault(day, [])
                seen = {(r.get('id'), r.get('source_msg_id'), r.get('origin_msg_id')) for r in dest if isinstance(r, dict)}
                for r in rows or []:
                    if not isinstance(r, dict):
                        continue
                    sig = (r.get('id'), r.get('source_msg_id'), r.get('origin_msg_id'))
                    if sig not in seen:
                        dest.append(r)
                        seen.add(sig)
    chats.pop(old_key, None)

def _v177_legacy_0156_migrate_chat_id_everywhere(old_chat_id: int, new_chat_id: int, reason: str='telegram supergroup migration') -> bool:
    """Атомарно переносит известный chat_id старой group на новый supergroup chat_id."""
    old_chat_id, new_chat_id = (int(old_chat_id), int(new_chat_id))
    if old_chat_id == new_chat_id:
        return True
    try:
        with data_lock:
            _merge_chat_store_for_migration(old_chat_id, new_chat_id)
            for root_key in ('forward_rules', 'forward_finance'):
                root = data.setdefault(root_key, {})
                oldk, newk = (str(old_chat_id), str(new_chat_id))
                if oldk in root:
                    src_payload = root.pop(oldk) or {}
                    dst_payload = root.setdefault(newk, {})
                    if isinstance(src_payload, dict) and isinstance(dst_payload, dict):
                        dst_payload.update(src_payload)
                    elif src_payload:
                        root[newk] = src_payload
                for src, dsts in list(root.items()):
                    if not isinstance(dsts, dict):
                        continue
                    if oldk in dsts:
                        val = dsts.pop(oldk)
                        if newk not in dsts:
                            dsts[newk] = val
            try:
                for _cid, st in (data.get('chats', {}) or {}).items():
                    if not isinstance(st, dict):
                        continue
                    kc = st.get('known_chats')
                    if isinstance(kc, dict) and str(old_chat_id) in kc:
                        info = kc.pop(str(old_chat_id))
                        kc.setdefault(str(new_chat_id), info)
            except Exception:
                pass
            for root_key in ('active_messages',):
                root = data.get(root_key)
                if isinstance(root, dict) and str(old_chat_id) in root:
                    oldv = root.pop(str(old_chat_id))
                    root.setdefault(str(new_chat_id), oldv)
            reg = data.get('open_window_registry') or {}
            if isinstance(reg, dict):
                for item in reg.values():
                    if not isinstance(item, dict):
                        continue
                    if int(item.get('chat_id', 0) or 0) == old_chat_id:
                        item['chat_id'] = new_chat_id
                    params = item.get('params') or {}
                    if isinstance(params, dict):
                        for k in ('target_chat_id', 'source_chat_id', 'dst_chat_id'):
                            try:
                                if int(params.get(k, 0) or 0) == old_chat_id:
                                    params[k] = new_chat_id
                            except Exception:
                                pass
            for _cid, st in (data.get('chats', {}) or {}).items():
                if not isinstance(st, dict):
                    continue
                pools = [st.get('records') or [], st.get('ars_records') or [], st.get('usd_records') or []]
                for daily_key in ('daily_records', 'ars_daily_records', 'usd_daily_records'):
                    for rows in (st.get(daily_key) or {}).values():
                        pools.append(rows or [])
                for rows in pools:
                    for rec in rows:
                        if not isinstance(rec, dict):
                            continue
                        for k in ('forward_source_chat_id', 'forward_dst_chat_id'):
                            try:
                                if int(rec.get(k, 0) or 0) == old_chat_id:
                                    rec[k] = new_chat_id
                            except Exception:
                                pass
            try:
                if old_chat_id in finance_active_chats:
                    finance_active_chats.discard(old_chat_id)
                    finance_active_chats.add(new_chat_id)
            except Exception:
                pass
            fac = data.get('finance_active_chats')
            if isinstance(fac, list):
                data['finance_active_chats'] = [new_chat_id if int(x) == old_chat_id else x for x in fac]
            with forward_map_lock:
                rebuilt = {}
                for (src, mid), pairs in list(forward_map.items()):
                    nsrc = new_chat_id if int(src) == old_chat_id else int(src)
                    npairs = []
                    for dcid, dmid in pairs:
                        ndcid = new_chat_id if int(dcid) == old_chat_id else int(dcid)
                        pair = (ndcid, int(dmid))
                        if pair not in npairs:
                            npairs.append(pair)
                    key = (nsrc, int(mid))
                    rebuilt.setdefault(key, [])
                    for pair in npairs:
                        if pair not in rebuilt[key]:
                            rebuilt[key].append(pair)
                forward_map.clear()
                forward_map.update(rebuilt)
                _persist_forward_index_in_data(data)
            _v199_register_chat_alias(old_chat_id, new_chat_id, reason)
            _v199_rewrite_pair_order_id(old_chat_id, new_chat_id)
            gs = data.setdefault('_global_settings', {})
            try:
                tenants_root = gs.get('tenants_v148') or {}
                mapping = tenants_root.get('chat_to_tenant') or {}
                tenants = tenants_root.get('tenants') or {}
                old_tid = str(mapping.pop(str(old_chat_id), None) or '')
                new_tid = str(mapping.get(str(new_chat_id)) or '')
                canonical_tid = new_tid or old_tid
                if old_tid and new_tid and (old_tid != new_tid):
                    old_row = tenants.get(old_tid) if isinstance(tenants, dict) else None
                    new_row = tenants.get(new_tid) if isinstance(tenants, dict) else None
                    if isinstance(old_row, dict) and isinstance(new_row, dict):
                        merged_chats = []
                        for raw in list(new_row.get('chat_ids') or []) + list(old_row.get('chat_ids') or []):
                            try:
                                cid = int(raw)
                            except Exception:
                                continue
                            cid = new_chat_id if cid == old_chat_id else cid
                            if cid not in merged_chats:
                                merged_chats.append(cid)
                        new_row['chat_ids'] = merged_chats
                        old_users = old_row.get('users') or {}
                        if isinstance(old_users, dict):
                            nu = new_row.setdefault('users', {})
                            for uid, urow in old_users.items():
                                if uid not in nu:
                                    nu[uid] = urow
                        old_settings = old_row.get('settings') or {}
                        if isinstance(old_settings, dict):
                            ns = new_row.setdefault('settings', {})
                            for k, v in old_settings.items():
                                ns.setdefault(k, v)
                        if not int(new_row.get('owner_user_id') or 0):
                            new_row['owner_user_id'] = int(old_row.get('owner_user_id') or 0)
                        for cid in merged_chats:
                            mapping[str(cid)] = new_tid
                        tenants.pop(old_tid, None)
                    canonical_tid = new_tid
                elif canonical_tid:
                    mapping[str(new_chat_id)] = canonical_tid
                for tid, trow in list(tenants.items()) if isinstance(tenants, dict) else []:
                    if not isinstance(trow, dict):
                        continue
                    chats = []
                    for raw in trow.get('chat_ids') or []:
                        try:
                            cid = int(raw)
                        except Exception:
                            continue
                        if cid == old_chat_id:
                            cid = new_chat_id if str(tid) == str(canonical_tid) else 0
                        if cid and cid not in chats:
                            chats.append(cid)
                    trow['chat_ids'] = chats
                    try:
                        if int(trow.get('root_chat_id') or 0) == old_chat_id:
                            if str(tid) == str(canonical_tid):
                                trow['root_chat_id'] = new_chat_id
                            elif chats:
                                trow['root_chat_id'] = int(chats[0])
                            else:
                                trow['root_chat_id'] = 0
                    except Exception:
                        pass
                if canonical_tid:
                    mapping[str(new_chat_id)] = canonical_tid
            except Exception as exc:
                log_error(f'v199 tenant migration {old_chat_id}->{new_chat_id}: {exc}')
            try:
                reminders = (gs.get('reminders_v2') or {}).get('items') or {}
                legacy_rows = list(reminders.values())
                if isinstance(gs.get('reminder'), dict):
                    legacy_rows.append(gs.get('reminder'))
                for cfg in legacy_rows:
                    if not isinstance(cfg, dict):
                        continue
                    out_ids = []
                    for raw in cfg.get('chat_ids') or []:
                        try:
                            cid = int(raw)
                        except Exception:
                            continue
                        cid = new_chat_id if cid == old_chat_id else cid
                        if cid not in out_ids:
                            out_ids.append(cid)
                    cfg['chat_ids'] = out_ids
                    lm = cfg.get('last_message_ids')
                    if isinstance(lm, dict) and str(old_chat_id) in lm:
                        old_mid = lm.pop(str(old_chat_id))
                        lm.setdefault(str(new_chat_id), old_mid)
            except Exception as exc:
                log_error(f'v199 reminder migration {old_chat_id}->{new_chat_id}: {exc}')
            try:
                settings_root = data.get('_task_settings_v172')
                if isinstance(settings_root, dict) and str(old_chat_id) in settings_root:
                    old_settings = settings_root.pop(str(old_chat_id))
                    if str(new_chat_id) not in settings_root:
                        settings_root[str(new_chat_id)] = old_settings
                    elif isinstance(old_settings, dict) and isinstance(settings_root.get(str(new_chat_id)), dict):
                        for k, v in old_settings.items():
                            settings_root[str(new_chat_id)].setdefault(k, v)
                for task in (data.get('_tasks_v172') or {}).values():
                    if not isinstance(task, dict):
                        continue
                    for field in ('chat_id', 'source_chat_id', 'target_chat_id'):
                        try:
                            if int(task.get(field) or 0) == old_chat_id:
                                task[field] = new_chat_id
                        except Exception:
                            pass
                src_index = data.get('_task_source_index_v172')
                if isinstance(src_index, dict):
                    for key0 in list(src_index.keys()):
                        if str(key0).startswith(str(old_chat_id) + ':'):
                            newkey = str(new_chat_id) + str(key0)[len(str(old_chat_id)):]
                            src_index.setdefault(newkey, src_index.pop(key0))
            except Exception as exc:
                log_error(f'v199 task migration {old_chat_id}->{new_chat_id}: {exc}')
            try:
                ctor = gs.get('ui_constructor_v196') or {} if isinstance(gs, dict) else {}
                scopes = ctor.get('scopes') if isinstance(ctor, dict) else None
                if isinstance(scopes, dict) and str(old_chat_id) in scopes:
                    old_scope = scopes.pop(str(old_chat_id))
                    if str(new_chat_id) not in scopes:
                        scopes[str(new_chat_id)] = old_scope
                    elif isinstance(old_scope, dict) and isinstance(scopes.get(str(new_chat_id)), dict):
                        dst_scope = scopes[str(new_chat_id)]
                        for k, v in old_scope.items():
                            if k == 'windows' and isinstance(v, dict):
                                dst_scope.setdefault('windows', {}).update({wk: wv for wk, wv in v.items() if wk not in dst_scope.setdefault('windows', {})})
                            else:
                                dst_scope.setdefault(k, v)
                if isinstance(ctor, dict) and str(ctor.get('last_target_scope') or '') == str(old_chat_id):
                    ctor['last_target_scope'] = str(new_chat_id)
            except Exception as exc:
                log_error(f'v212 constructor scope migration {old_chat_id}->{new_chat_id}: {exc}')
            try:
                owners = gs.get('owner_access_chat_ids_v168')
                if isinstance(owners, list):
                    gs['owner_access_chat_ids_v168'] = sorted({new_chat_id if int(x) == old_chat_id else int(x) for x in owners})
            except Exception:
                pass
        # R49: forward reactivation can persist/normalize; run it only after releasing data_lock.
        try:
            reactivate_forward_target_v199(old_chat_id, migrated_to=new_chat_id, persist=False)
        except Exception:
            pass
        save_data(data, full=True)
        persist_forward_rules_to_owner()
        try:
            schedule_config_backup_for_chats(new_chat_id, delay=0.1)
            if OWNER_ID:
                schedule_config_backup_for_chats(int(OWNER_ID), delay=0.1)
        except Exception:
            pass
        try:
            schedule_delta_backup(new_chat_id, delay=0.5, reason='chat_id_migration')
        except Exception:
            pass
        log_info(f'[CHAT MIGRATION] {old_chat_id} -> {new_chat_id}: {reason}')
        try:
            bot_journal('chat_id_migration', new_chat_id, f'{old_chat_id} -> {new_chat_id}; {reason}')
        except Exception:
            pass
        return True
    except Exception as e:
        log_error(f'migrate_chat_id_everywhere({old_chat_id}->{new_chat_id}): {e}')
        return False
try:
    _v177_legacy_0156_migrate_chat_id_everywhere.__name__ = 'migrate_chat_id_everywhere'
except Exception:
    pass

def _handle_supergroup_migration_error(old_chat_id: int, err: Exception):
    new_id = _telegram_migrate_to_chat_id(err)
    if new_id is None:
        resolver = globals().get('_v199_migration_target_from_probe_error')
        if callable(resolver):
            try:
                new_id = resolver(int(old_chat_id), err, None)
            except Exception:
                new_id = None
    if new_id is None:
        return None
    if migrate_chat_id_everywhere(int(old_chat_id), int(new_id), reason=str(err)[:300]):
        return int(new_id)
    return None

def _note_forward_target_migrated(source_chat_id: int, source_msg_id: int, old_chat_id: int, new_chat_id: int):
    """Mark old target as migrated so live/durable witnesses do not wait on it forever."""
    try:
        _forward_outcome_update(int(source_chat_id), int(source_msg_id), dst_chat_id=int(old_chat_id), dst_state='migrated')
    except Exception:
        pass
    try:
        fn = globals().get('_durable_note_forward_target_migration')
        if callable(fn):
            fn(int(source_chat_id), int(old_chat_id), int(new_chat_id))
    except Exception as e:
        try:
            log_error(f'forward migration witness {old_chat_id}->{new_chat_id}: {e}')
        except Exception:
            pass

def _notify_forward_failure(source_chat_id: int, msg_id: int, dst_chat_id: int, err: Exception):
    state = _v199_confirm_failed_forward_target(int(dst_chat_id), err)
    if state.startswith('migrated:'):
        return state
    if state == 'suspended':
        log_error(f'FORWARD TARGET SUSPENDED: {source_chat_id}:{msg_id}->{dst_chat_id}: {err}')
        return state
    if _is_bot_removed_error(err):
        set_chat_bot_removed(dst_chat_id, True, str(err)[:240])
    src_name = get_chat_display_name(source_chat_id)
    dst_name = get_chat_display_name(dst_chat_id)
    text = f'⚠️ Пересылка не доставлена\nиз: {src_name}\nсообщение: {msg_id}\nв: {dst_name}\n{err}'
    log_error(text)
    try:
        send_owner_technical_alert(text, 25, source_chat_id=int(source_chat_id))
    except Exception:
        if OWNER_ID:
            try:
                bot.send_message(int(OWNER_ID), text)
            except Exception:
                pass
    return 'transient'

def _message_text_for_finance(msg) -> str:
    return (getattr(msg, 'text', None) or getattr(msg, 'caption', None) or '').strip()

def _build_input_media_from_message(msg):
    caption = getattr(msg, 'caption', None)
    ct = getattr(msg, 'content_type', None)
    if ct == 'photo' and getattr(msg, 'photo', None):
        return InputMediaPhoto(msg.photo[-1].file_id, caption=caption)
    if ct == 'video' and getattr(msg, 'video', None):
        return InputMediaVideo(msg.video.file_id, caption=caption)
    if ct == 'document' and getattr(msg, 'document', None):
        return InputMediaDocument(msg.document.file_id, caption=caption)
    if ct == 'audio' and getattr(msg, 'audio', None):
        return InputMediaAudio(msg.audio.file_id, caption=caption)
    if ct == 'animation' and getattr(msg, 'animation', None):
        return InputMediaAnimation(msg.animation.file_id, caption=caption)
    return None

def _fallback_send_single(dst_chat_id: int, msg, reply_to_message_id=None):
    ct = getattr(msg, 'content_type', None)
    if ct == 'text':
        return _call_with_optional_reply(bot.send_message, dst_chat_id, msg.text or '', reply_to_message_id=reply_to_message_id)
    if ct == 'photo' and getattr(msg, 'photo', None):
        return _call_with_optional_reply(bot.send_photo, dst_chat_id, msg.photo[-1].file_id, caption=getattr(msg, 'caption', None), reply_to_message_id=reply_to_message_id)
    if ct == 'video' and getattr(msg, 'video', None):
        return _call_with_optional_reply(bot.send_video, dst_chat_id, msg.video.file_id, caption=getattr(msg, 'caption', None), reply_to_message_id=reply_to_message_id)
    if ct == 'audio' and getattr(msg, 'audio', None):
        return _call_with_optional_reply(bot.send_audio, dst_chat_id, msg.audio.file_id, caption=getattr(msg, 'caption', None), reply_to_message_id=reply_to_message_id)
    if ct == 'document' and getattr(msg, 'document', None):
        return _call_with_optional_reply(bot.send_document, dst_chat_id, msg.document.file_id, caption=getattr(msg, 'caption', None), reply_to_message_id=reply_to_message_id)
    if ct == 'voice' and getattr(msg, 'voice', None):
        return _call_with_optional_reply(bot.send_voice, dst_chat_id, msg.voice.file_id, caption=getattr(msg, 'caption', None), reply_to_message_id=reply_to_message_id)
    if ct == 'video_note' and getattr(msg, 'video_note', None):
        return _call_with_optional_reply(bot.send_video_note, dst_chat_id, msg.video_note.file_id, reply_to_message_id=reply_to_message_id)
    if ct == 'sticker' and getattr(msg, 'sticker', None):
        return _call_with_optional_reply(bot.send_sticker, dst_chat_id, msg.sticker.file_id, reply_to_message_id=reply_to_message_id)
    if ct == 'animation' and getattr(msg, 'animation', None):
        return _call_with_optional_reply(bot.send_animation, dst_chat_id, msg.animation.file_id, caption=getattr(msg, 'caption', None), reply_to_message_id=reply_to_message_id)
    if ct == 'location' and getattr(msg, 'location', None):
        return _call_with_optional_reply(bot.send_location, dst_chat_id, msg.location.latitude, msg.location.longitude, reply_to_message_id=reply_to_message_id)
    if ct == 'venue' and getattr(msg, 'venue', None):
        return _call_with_optional_reply(bot.send_venue, dst_chat_id, msg.venue.location.latitude, msg.venue.location.longitude, msg.venue.title, msg.venue.address, foursquare_id=getattr(msg.venue, 'foursquare_id', None), reply_to_message_id=reply_to_message_id)
    if ct == 'contact' and getattr(msg, 'contact', None):
        return _call_with_optional_reply(bot.send_contact, dst_chat_id, msg.contact.phone_number, msg.contact.first_name, last_name=getattr(msg.contact, 'last_name', None), reply_to_message_id=reply_to_message_id)
    if ct == 'dice' and getattr(msg, 'dice', None):
        return _call_with_optional_reply(bot.send_dice, dst_chat_id, emoji=getattr(msg.dice, 'emoji', None), reply_to_message_id=reply_to_message_id)
    if ct == 'poll' and getattr(msg, 'poll', None):
        options = [opt.text for opt in getattr(msg.poll, 'options', [])]
        return _call_with_optional_reply(bot.send_poll, dst_chat_id, msg.poll.question, options, is_anonymous=getattr(msg.poll, 'is_anonymous', True), allows_multiple_answers=getattr(msg.poll, 'allows_multiple_answers', False), type=getattr(msg.poll, 'type', 'regular'), reply_to_message_id=reply_to_message_id)
    raise RuntimeError(f'Unsupported fallback content_type={ct}')

def _forward_single_to_target(source_chat_id: int, msg, dst_chat_id: int, finance_enabled: bool, _migration_retry: bool=False):
    try:
        _src_mid_v260 = int(getattr(msg, 'message_id', 0) or 0)
        for _existing_dst_chat, _existing_dst_mid in list(get_forward_links(int(source_chat_id), _src_mid_v260) or []):
            if int(_existing_dst_chat) != int(dst_chat_id):
                continue
            if finance_enabled:
                _txt_v260 = _message_text_for_finance(msg)
                _owner_v260 = int(getattr(getattr(msg, 'from_user', None), 'id', 0) or 0)
                _rec_v260 = sync_forwarded_finance_message(int(dst_chat_id), int(_existing_dst_mid), _txt_v260, _owner_v260, source_msg=msg) if _txt_v260 else None
                if isinstance(_rec_v260, dict):
                    _persist_forward_finance_delivery_now(int(source_chat_id), _src_mid_v260, int(dst_chat_id), int(_existing_dst_mid), _rec_v260)
                elif _txt_v260 and text_has_any_digit(_txt_v260):
                    _v260_schedule_finance_forward_repair(int(source_chat_id), _src_mid_v260, int(dst_chat_id), int(_existing_dst_mid), _txt_v260, _owner_v260, getattr(msg, 'date', None))
            bot_journal('forward_duplicate_copy_blocked_v260', int(dst_chat_id), f'src={source_chat_id}:{_src_mid_v260}; reuse={dst_chat_id}:{_existing_dst_mid}')
            return int(_existing_dst_mid)
    except Exception as _v260_existing_exc:
        try: log_error(f'[FWD V260] existing-link exact-once check: {_v260_existing_exc}')
        except Exception: pass
    try:
        _forward_outcome_update(source_chat_id, int(getattr(msg, 'message_id', 0) or 0), state='dispatching', dst_chat_id=int(dst_chat_id), dst_state='attempted')
    except Exception:
        pass
    reply_to_target_id = None
    try:
        reply_to_msg = getattr(msg, 'reply_to_message', None)
        if reply_to_msg is not None:
            reply_to_target_id = resolve_reply_target_message_id(source_chat_id, getattr(reply_to_msg, 'message_id', None), dst_chat_id)
    except Exception as e:
        log_error(f'_forward_single_to_target reply resolve {source_chat_id}->{dst_chat_id}: {e}')
    pre_copy_markup = None
    initial_slash_command = None
    initial_slash_synced_rec = None
    initial_slash_sent = False
    text_for_finance = _message_text_for_finance(msg)
    copy_edit_mode = 'normal'
    try:
        if finance_enabled:
            copy_edit_mode = forward_copy_edit_mode(source_chat_id)
            if copy_edit_mode == 'button':
                pre_copy_markup = _forward_copy_edit_keyboard('button')
    except Exception:
        pre_copy_markup = None
        copy_edit_mode = 'normal'
    try:
        use_initial_slash = False
        try:
            use_initial_slash = bool(finance_enabled and copy_edit_mode == 'slash' and (str(getattr(msg, 'content_type', '') or '') == 'text') and text_for_finance and is_finance_mode(int(dst_chat_id)) and looks_like_amount(text_for_finance))
        except Exception:
            use_initial_slash = False
        if use_initial_slash:
            with locked_chat(int(dst_chat_id)):
                initial_slash_command = _predict_forward_copy_record_command(int(dst_chat_id), msg, text_for_finance)
            if initial_slash_command:
                display_text = (_strip_forward_copy_edit_command(text_for_finance) + '\n' + initial_slash_command).strip()
                send_kwargs = {}
                entities = getattr(msg, 'entities', None)
                if entities: send_kwargs['entities'] = entities
                if reply_to_target_id:
                    send_kwargs['reply_to_message_id'] = int(reply_to_target_id); send_kwargs['allow_sending_without_reply'] = True
                try:
                    sent = _tg_call_retry(bot.send_message, int(dst_chat_id), display_text, purpose='forward_send_text_initial_slash', **send_kwargs)
                except TypeError:
                    send_kwargs.pop('allow_sending_without_reply', None); sent = _tg_call_retry(bot.send_message, int(dst_chat_id), display_text, purpose='forward_send_text_initial_slash', **send_kwargs)
                dst_msg_id = int(sent.message_id); initial_slash_sent = True
                _store_forward_link(source_chat_id, msg.message_id, dst_chat_id, dst_msg_id)
                _forward_outcome_update(source_chat_id, int(msg.message_id), dst_chat_id=int(dst_chat_id), dst_state='delivered', dst_msg_id=int(dst_msg_id))
                try:
                    _persist_forward_index_in_data(data); save_data(data, root_only=True)
                except Exception as e:
                    log_error(f'[FORWARD LINK DURABLE initial slash] {source_chat_id}:{msg.message_id}->{dst_chat_id}:{dst_msg_id}: {e}')
                owner_id = msg.from_user.id if getattr(msg, 'from_user', None) else 0
                initial_slash_synced_rec = sync_forwarded_finance_message(int(dst_chat_id), int(dst_msg_id), text_for_finance, owner_id, source_msg=msg)
                if isinstance(initial_slash_synced_rec, dict): initial_slash_synced_rec = _v169_apply_predicted_record_uid(int(dst_chat_id), initial_slash_synced_rec, initial_slash_command)
        if not initial_slash_sent:
            if reply_to_target_id:
                try:
                    sent = _tg_call_retry(bot.copy_message, dst_chat_id, source_chat_id, msg.message_id, reply_to_message_id=reply_to_target_id, allow_sending_without_reply=True, reply_markup=pre_copy_markup, purpose='forward_copy_message')
                except TypeError:
                    try:
                        sent = _tg_call_retry(bot.copy_message, dst_chat_id, source_chat_id, msg.message_id, reply_to_message_id=reply_to_target_id, reply_markup=pre_copy_markup, purpose='forward_copy_message')
                    except TypeError:
                        sent = _tg_call_retry(bot.copy_message, dst_chat_id, source_chat_id, msg.message_id, reply_markup=pre_copy_markup, purpose='forward_copy_message')
            else:
                sent = _tg_call_retry(bot.copy_message, dst_chat_id, source_chat_id, msg.message_id, reply_markup=pre_copy_markup, purpose='forward_copy_message')
            dst_msg_id = sent.message_id
    except Exception as e_copy:
        migrated_id = None if _migration_retry else _handle_supergroup_migration_error(dst_chat_id, e_copy)
        if migrated_id is not None:
            _note_forward_target_migrated(source_chat_id, int(getattr(msg, 'message_id', 0) or 0), dst_chat_id, migrated_id)
            return _forward_single_to_target(source_chat_id, msg, migrated_id, finance_enabled, _migration_retry=True)
        try:
            sent_forward = _tg_call_retry(bot.forward_message, dst_chat_id, source_chat_id, msg.message_id, purpose='forward_message_fallback')
            dst_msg_id = sent_forward.message_id
        except Exception as e_forward:
            migrated_id = None if _migration_retry else _handle_supergroup_migration_error(dst_chat_id, e_forward)
            if migrated_id is not None:
                _note_forward_target_migrated(source_chat_id, int(getattr(msg, 'message_id', 0) or 0), dst_chat_id, migrated_id)
                return _forward_single_to_target(source_chat_id, msg, migrated_id, finance_enabled, _migration_retry=True)
            try:
                sent_msg = _fallback_send_single(dst_chat_id, msg, reply_to_message_id=reply_to_target_id)
                dst_msg_id = sent_msg.message_id
            except Exception as e_send:
                migrated_id = None if _migration_retry else _handle_supergroup_migration_error(dst_chat_id, e_send)
                if migrated_id is not None:
                    _note_forward_target_migrated(source_chat_id, int(getattr(msg, 'message_id', 0) or 0), dst_chat_id, migrated_id)
                    return _forward_single_to_target(source_chat_id, msg, migrated_id, finance_enabled, _migration_retry=True)
                final_error = e_forward if 'Unsupported fallback content_type' in str(e_send) else e_send
                failure_state = _notify_forward_failure(source_chat_id, msg.message_id, dst_chat_id, final_error)
                if str(failure_state).startswith('migrated:') and (not _migration_retry):
                    try:
                        migrated_id = int(str(failure_state).split(':', 1)[1])
                        _note_forward_target_migrated(source_chat_id, int(getattr(msg, 'message_id', 0) or 0), dst_chat_id, migrated_id)
                        return _forward_single_to_target(source_chat_id, msg, migrated_id, finance_enabled, _migration_retry=True)
                    except Exception:
                        pass
                terminal_state = 'suspended' if failure_state == 'suspended' else 'failed'
                _forward_outcome_update(source_chat_id, int(getattr(msg, 'message_id', 0) or 0), dst_chat_id=int(dst_chat_id), dst_state=terminal_state, error=str(final_error))
                return None
    _store_forward_link(source_chat_id, msg.message_id, dst_chat_id, dst_msg_id)
    try:
        _v260_forward_finance_op_mark(int(source_chat_id), int(msg.message_id), int(dst_chat_id), 'copy_delivered', dst_msg_id=int(dst_msg_id), text=str(text_for_finance or '')[:4000], owner=int(getattr(getattr(msg,'from_user',None),'id',0) or 0), source_date=getattr(msg,'date',None))
    except Exception:
        pass
    _forward_outcome_update(source_chat_id, int(msg.message_id), dst_chat_id=int(dst_chat_id), dst_state='delivered', dst_msg_id=int(dst_msg_id))
    try:
        _persist_forward_index_in_data(data)
        save_data(data, root_only=True)
    except Exception as e:
        log_error(f'[FORWARD LINK DURABLE] {source_chat_id}:{msg.message_id}->{dst_chat_id}:{dst_msg_id}: {e}')
    bump_quick_balance_recreate_counter(dst_chat_id)
    _v212_task_reconcile_forward_copy(dst_chat_id, dst_msg_id, source_chat_id, msg, is_edit=False)
    if finance_enabled and text_for_finance:
        try:
            owner_id = msg.from_user.id if getattr(msg, 'from_user', None) else 0
            ok_fin = initial_slash_synced_rec or sync_forwarded_finance_message(dst_chat_id, dst_msg_id, text_for_finance, owner_id, source_msg=msg)
            if ok_fin:
                _rec = ok_fin if isinstance(ok_fin, dict) else find_record_by_message_id(dst_chat_id, dst_msg_id)
                if isinstance(_rec, dict) and initial_slash_sent:
                    _rec['forward_copy_content_type'] = 'text'
                _persist_forward_finance_delivery_now(source_chat_id, msg.message_id, dst_chat_id, dst_msg_id, _rec)
                if initial_slash_sent and isinstance(_rec, dict):
                    actual_command = _forward_copy_record_command(_rec)
                    if actual_command == initial_slash_command:
                        _ui_ok = True
                        try:
                            bot_journal('forward_copy_initial_slash', int(dst_chat_id), f'src={source_chat_id}:{msg.message_id} dst_msg={dst_msg_id} command={actual_command}')
                        except Exception:
                            pass
                    else:
                        _ui_ok = apply_forward_copy_edit_ui(source_chat_id, dst_chat_id, dst_msg_id, msg, rec=_rec)
                else:
                    _ui_ok = apply_forward_copy_edit_ui(source_chat_id, dst_chat_id, dst_msg_id, msg, rec=_rec)
                if not _ui_ok and forward_copy_edit_mode(source_chat_id) != 'normal':
                    schedule_forward_copy_edit_ui_retry(source_chat_id, dst_chat_id, dst_msg_id, msg, rec=_rec, delay=0.8)
            elif text_has_any_digit(text_for_finance):
                try:
                    _dst_fin_mode = bool(is_finance_mode(dst_chat_id))
                except Exception:
                    _dst_fin_mode = False
                if _dst_fin_mode:
                    log_error(f'[FWD FINANCE NOT RECORDED] {get_chat_display_name(source_chat_id)}:{msg.message_id} -> {get_chat_display_name(dst_chat_id)}:{dst_msg_id} text={text_for_finance[:220]!r}')
                    _v260_schedule_finance_forward_repair(int(source_chat_id), int(msg.message_id), int(dst_chat_id), int(dst_msg_id), text_for_finance, int(owner_id or 0), getattr(msg, 'date', None))
                else:
                    bot_journal('forward_finance_not_expected', dst_chat_id, f'src={source_chat_id}:{msg.message_id} dst_msg={dst_msg_id}')
        except Exception as e:
            log_error(f'_forward_single_to_target finance sync {get_chat_display_name(source_chat_id)}->{get_chat_display_name(dst_chat_id)}: {e}')
            try:
                _v260_schedule_finance_forward_repair(int(source_chat_id), int(msg.message_id), int(dst_chat_id), int(dst_msg_id), text_for_finance, int(getattr(getattr(msg,'from_user',None),'id',0) or 0), getattr(msg, 'date', None))
            except Exception:
                pass
    try:
        capture_forwarded_bot_copy_as_secret(dst_chat_id, dst_msg_id, msg)
    except Exception as e:
        log_error(f'forward secret capture {source_chat_id}->{dst_chat_id}:{dst_msg_id}: {e}')
    return dst_msg_id

def _flush_media_group_forward(source_chat_id: int, media_group_id: str):
    if not FORWARD_TASK_POOL.submit(int(source_chat_id), _flush_media_group_forward_locked, source_chat_id, media_group_id):
        log_error(f'MEDIA GROUP FORWARD QUEUE FULL: {source_chat_id}')

def _flush_media_group_forward_locked(source_chat_id: int, media_group_id: str):
    cache_key = (int(source_chat_id), str(media_group_id))
    messages = _media_group_cache.pop(cache_key, [])
    _media_group_timers.pop(cache_key, None)
    DELAYED_SCHEDULER.cancel(f'media-group:{int(source_chat_id)}:{str(media_group_id)}')
    if not messages:
        return
    messages = sorted(messages, key=lambda m: m.message_id)
    targets = sorted(list(resolve_forward_targets(source_chat_id) or []), key=lambda row: 0 if bool(row[2]) else 1)
    if not targets:
        for src_msg in messages:
            try:
                _forward_outcome_update(source_chat_id, int(src_msg.message_id), state='no_targets')
            except Exception:
                pass
        return
    for src_msg in messages:
        try:
            _forward_outcome_update(source_chat_id, int(src_msg.message_id), state='dispatching')
        except Exception:
            pass
    media = []
    for msg in messages:
        item = _build_input_media_from_message(msg)
        if not item:
            media = []
            break
        media.append(item)
    group_reply_source_id = None
    try:
        first_reply = getattr(messages[0], 'reply_to_message', None)
        if first_reply is not None:
            group_reply_source_id = getattr(first_reply, 'message_id', None)
    except Exception:
        pass
    for dst_chat_id, mode, finance_enabled in targets:
        for src_msg in messages:
            try:
                _forward_outcome_update(source_chat_id, int(src_msg.message_id), dst_chat_id=int(dst_chat_id), dst_state='attempted')
            except Exception:
                pass
        sent_ids = []
        reply_to_target_id = resolve_reply_target_message_id(source_chat_id, group_reply_source_id, dst_chat_id) if group_reply_source_id else None
        if media:
            try:
                if reply_to_target_id:
                    try:
                        sent_group = _tg_call_retry(bot.send_media_group, dst_chat_id, media, reply_to_message_id=reply_to_target_id, allow_sending_without_reply=True, purpose='forward_media_group')
                    except TypeError:
                        try:
                            sent_group = _tg_call_retry(bot.send_media_group, dst_chat_id, media, reply_to_message_id=reply_to_target_id, purpose='forward_media_group')
                        except TypeError:
                            sent_group = _tg_call_retry(bot.send_media_group, dst_chat_id, media, purpose='forward_media_group')
                else:
                    sent_group = _tg_call_retry(bot.send_media_group, dst_chat_id, media, purpose='forward_media_group')
                sent_ids = [m.message_id for m in sent_group]
            except Exception as e:
                migrated_id = _handle_supergroup_migration_error(dst_chat_id, e)
                if migrated_id is not None:
                    log_info(f'[MEDIA GROUP MIGRATION RETRY] {dst_chat_id} -> {migrated_id}')
                    for src_msg in messages:
                        _note_forward_target_migrated(source_chat_id, int(getattr(src_msg, 'message_id', 0) or 0), dst_chat_id, migrated_id)
                        _forward_single_to_target(source_chat_id, src_msg, migrated_id, finance_enabled, _migration_retry=True)
                    continue
                log_error(f'_flush_media_group_forward send_media_group failed {get_chat_display_name(source_chat_id)}->{get_chat_display_name(dst_chat_id)}: {e}')
        if len(sent_ids) == len(messages):
            for src_msg, dst_msg_id in zip(messages, sent_ids):
                _store_forward_link(source_chat_id, src_msg.message_id, dst_chat_id, dst_msg_id)
                _forward_outcome_update(source_chat_id, int(src_msg.message_id), dst_chat_id=int(dst_chat_id), dst_state='delivered', dst_msg_id=int(dst_msg_id))
                bump_quick_balance_recreate_counter(dst_chat_id)
                _v212_task_reconcile_forward_copy(dst_chat_id, dst_msg_id, source_chat_id, src_msg, is_edit=False)
                text_for_finance = _message_text_for_finance(src_msg)
                if finance_enabled and text_for_finance:
                    try:
                        owner_id = src_msg.from_user.id if getattr(src_msg, 'from_user', None) else 0
                        ok_fin = sync_forwarded_finance_message(dst_chat_id, dst_msg_id, text_for_finance, owner_id, source_msg=src_msg)
                        if ok_fin:
                            _rec = ok_fin if isinstance(ok_fin, dict) else None
                            _ui_ok = apply_forward_copy_edit_ui(source_chat_id, dst_chat_id, dst_msg_id, src_msg, rec=_rec)
                            if not _ui_ok and forward_copy_edit_mode(source_chat_id) != 'normal':
                                schedule_forward_copy_edit_ui_retry(source_chat_id, dst_chat_id, dst_msg_id, src_msg, rec=_rec, delay=0.8)
                        elif text_has_any_digit(text_for_finance):
                            log_error(f'[FWD MEDIA FINANCE NOT RECORDED] {get_chat_display_name(source_chat_id)}:{src_msg.message_id} -> {get_chat_display_name(dst_chat_id)}:{dst_msg_id} text={text_for_finance[:220]!r}')
                    except Exception as e:
                        log_error(f'_flush_media_group_forward finance sync {get_chat_display_name(source_chat_id)}->{get_chat_display_name(dst_chat_id)}: {e}')
                try:
                    capture_forwarded_bot_copy_as_secret(dst_chat_id, dst_msg_id, src_msg)
                except Exception as e:
                    log_error(f'media-group secret capture {source_chat_id}->{dst_chat_id}:{dst_msg_id}: {e}')
            continue
        for src_msg in messages:
            _forward_single_to_target(source_chat_id, src_msg, dst_chat_id, finance_enabled)
    for src_msg in messages:
        try:
            _forward_outcome_update(source_chat_id, int(src_msg.message_id), state='completed')
        except Exception:
            pass

def _collect_media_group_for_forward(source_chat_id: int, msg):
    cache_key = (int(source_chat_id), str(msg.media_group_id))
    bucket = _media_group_cache.setdefault(cache_key, [])
    if not any((m.message_id == msg.message_id for m in bucket)):
        bucket.append(msg)
    scheduler_key = f'media-group:{int(source_chat_id)}:{str(msg.media_group_id)}'
    DELAYED_SCHEDULER.cancel(scheduler_key)
    deadline = DELAYED_SCHEDULER.schedule(scheduler_key, 0.8, _flush_media_group_forward, source_chat_id, msg.media_group_id)
    _media_group_timers[cache_key] = deadline
_FIN_FORWARD_BATCH_LOCK = threading.RLock()
_FIN_FORWARD_BATCHES = {}

def _fin_forward_batch_id(source_chat_id: int, source_msg_id: int) -> str:
    return f'{int(source_chat_id)}:{int(source_msg_id)}'

def _v177_legacy_0157_fin_forward_batch_finish_target(batch_id: str, dst_chat_id: int, ok: bool, elapsed: float, error: str='') -> None:
    follow = None
    with _FIN_FORWARD_BATCH_LOCK:
        row = _FIN_FORWARD_BATCHES.get(str(batch_id))
        if not isinstance(row, dict):
            return
        row.setdefault('targets', {})[str(int(dst_chat_id))] = {'ok': bool(ok), 'elapsed': round(float(elapsed), 3), 'error': str(error or '')[:300]}
        row['remaining'] = max(0, int(row.get('remaining', 0)) - 1)
        if row['remaining'] == 0:
            follow = dict(row)
            _FIN_FORWARD_BATCHES.pop(str(batch_id), None)
    try:
        bot_journal('finance_forward_target_done', follow.get('source_chat_id') if follow else None, f"batch={batch_id} dst={int(dst_chat_id)} ok={bool(ok)} elapsed={elapsed:.3f}s error={str(error or '')[:180]}", 'INFO' if ok else 'ERROR')
    except Exception:
        pass
    if not follow:
        return
    source_chat_id = int(follow.get('source_chat_id'))
    source_msg_id = int(follow.get('source_msg_id'))
    normal_targets = list(follow.get('normal_targets') or [])
    started = float(follow.get('started_mono') or time.monotonic())
    if normal_targets:
        if not FORWARD_TASK_POOL.submit(source_chat_id, _forward_normal_stage, source_chat_id, follow.get('msg'), normal_targets):
            log_error(f'FORWARD QUEUE FULL AFTER FIN BATCH, INLINE FALLBACK: {source_chat_id}')
            _forward_normal_stage(source_chat_id, follow.get('msg'), normal_targets)
    elif source_msg_id:
        _forward_outcome_update(source_chat_id, source_msg_id, state='completed')
    try:
        target_rows = follow.get('targets') or {}
        failed = sum((1 for x in target_rows.values() if not bool((x or {}).get('ok'))))
        bot_journal('finance_forward_batch_done', source_chat_id, f'batch={batch_id} targets={len(target_rows)} failed={failed} elapsed={time.monotonic() - started:.3f}s')
    except Exception:
        pass
try:
    _v177_legacy_0157_fin_forward_batch_finish_target.__name__ = '_fin_forward_batch_finish_target'
except Exception:
    pass

def _fin_forward_target_job(batch_id: str, source_chat_id: int, msg, dst_chat_id: int, finance_enabled: bool) -> None:
    started = time.monotonic()
    ok = False
    err = ''
    try:
        ok = bool(_forward_single_to_target(int(source_chat_id), msg, int(dst_chat_id), bool(finance_enabled)))
    except Exception as exc:
        err = str(exc)
        log_error(f'FIN-FORWARD TARGET {source_chat_id}->{dst_chat_id}: {exc}')
    finally:
        _fin_forward_batch_finish_target(batch_id, int(dst_chat_id), ok, time.monotonic() - started, err)

def _start_financial_forward_batch(source_chat_id: int, msg, finance_targets: list, normal_targets: list) -> None:
    source_chat_id = int(source_chat_id)
    source_msg_id = int(getattr(msg, 'message_id', 0) or 0)
    batch_id = _fin_forward_batch_id(source_chat_id, source_msg_id)
    with _FIN_FORWARD_BATCH_LOCK:
        _FIN_FORWARD_BATCHES[batch_id] = {'source_chat_id': source_chat_id, 'source_msg_id': source_msg_id, 'msg': msg, 'normal_targets': list(normal_targets or []), 'remaining': len(finance_targets or []), 'targets': {}, 'started_mono': time.monotonic()}
    try:
        bot_journal('finance_forward_batch_started', source_chat_id, f'batch={batch_id} finance_targets={len(finance_targets or [])} normal_targets={len(normal_targets or [])}')
    except Exception:
        pass
    for dst_chat_id, _mode, finance_enabled in list(finance_targets or []):
        task_key = f'{source_chat_id}:{int(dst_chat_id)}'
        if not FIN_FORWARD_TASK_POOL.submit(task_key, _fin_forward_target_job, batch_id, source_chat_id, msg, int(dst_chat_id), bool(finance_enabled)):
            log_error(f'FIN-FORWARD TARGET QUEUE FULL, INLINE FALLBACK: {task_key}')
            _fin_forward_target_job(batch_id, source_chat_id, msg, int(dst_chat_id), bool(finance_enabled))

def _forward_targets_stage(source_chat_id: int, msg, targets: list, final_stage: bool=False) -> None:
    """Выполняет уже выбранную часть направлений, не смешивая очереди."""
    source_chat_id = int(source_chat_id)
    source_msg_id = int(getattr(msg, 'message_id', 0) or 0)
    try:
        for dst_chat_id, _mode, finance_enabled in list(targets or []):
            _forward_single_to_target(source_chat_id, msg, int(dst_chat_id), bool(finance_enabled))
    finally:
        if final_stage and source_msg_id:
            _forward_outcome_update(source_chat_id, source_msg_id, state='completed')

def _forward_normal_stage(source_chat_id: int, msg, targets: list) -> None:
    _forward_targets_stage(source_chat_id, msg, targets, final_stage=True)

def _forward_financial_stage(source_chat_id: int, msg, finance_targets: list, normal_targets: list) -> None:
    """Сначала финансовые копии и записи, затем обычные/секретные назначения."""
    source_chat_id = int(source_chat_id)
    source_msg_id = int(getattr(msg, 'message_id', 0) or 0)
    try:
        _forward_targets_stage(source_chat_id, msg, finance_targets, final_stage=False)
    finally:
        if normal_targets:
            if not FORWARD_TASK_POOL.submit(source_chat_id, _forward_normal_stage, source_chat_id, msg, list(normal_targets)):
                log_error(f'FORWARD QUEUE FULL AFTER FIN STAGE, INLINE FALLBACK: {source_chat_id}')
                _forward_normal_stage(source_chat_id, msg, list(normal_targets))
        elif source_msg_id:
            _forward_outcome_update(source_chat_id, source_msg_id, state='completed')

def schedule_financial_forward_pipeline(source_chat_id: int, msg) -> None:
    """Финансовые назначения идут раньше всех остальных, без потери exact-once защиты."""
    source_chat_id = int(source_chat_id)
    source_msg_id = int(getattr(msg, 'message_id', 0) or 0)
    try:
        if getattr(msg, 'media_group_id', None) and getattr(msg, 'content_type', None) in ('photo', 'video', 'document', 'audio'):
            if not FORWARD_TASK_POOL.submit(source_chat_id, _forward_with_finance_priority, source_chat_id, msg):
                log_error(f'MEDIA FORWARD QUEUE FULL, INLINE FALLBACK: {source_chat_id}')
                _forward_with_finance_priority(source_chat_id, msg)
            return
        targets = list(resolve_forward_targets(source_chat_id) or [])
        if not targets:
            if source_msg_id:
                _forward_outcome_update(source_chat_id, source_msg_id, state='no_targets')
            return
        finance_targets = [row for row in targets if bool(row[2])]
        normal_targets = [row for row in targets if not bool(row[2])]
        if source_msg_id:
            _forward_outcome_update(source_chat_id, source_msg_id, state='dispatching')
        if finance_targets:
            _start_financial_forward_batch(source_chat_id, msg, list(finance_targets), list(normal_targets))
        else:
            ok = FORWARD_TASK_POOL.submit(source_chat_id, _forward_normal_stage, source_chat_id, msg, list(normal_targets))
            if not ok:
                log_error(f'FORWARD QUEUE FULL, INLINE FALLBACK: {source_chat_id}')
                _forward_normal_stage(source_chat_id, msg, list(normal_targets))
    except Exception as exc:
        log_error(f'schedule_financial_forward_pipeline {source_chat_id}: {exc}')
        if source_msg_id:
            _forward_outcome_update(source_chat_id, source_msg_id, state='failed')

def _canon_forward_any_message__001(source_chat_id: int, msg):
    try:
        source_msg_id = int(getattr(msg, 'message_id', 0) or 0)
        sender_skip_reason = _forward_sender_skip_reason(msg)
        if sender_skip_reason:
            _forward_outcome_skip(source_chat_id, msg, sender_skip_reason)
            return
        if getattr(msg, 'edit_date', None):
            _forward_outcome_skip(source_chat_id, msg, 'edited_source')
            return
        targets = sorted(list(resolve_forward_targets(source_chat_id) or []), key=lambda row: 0 if bool(row[2]) else 1)
        if not targets:
            if source_msg_id:
                _forward_outcome_update(source_chat_id, source_msg_id, state='no_targets')
            return
        if getattr(msg, 'media_group_id', None) and getattr(msg, 'content_type', None) in ('photo', 'video', 'document', 'audio'):
            if source_msg_id:
                _forward_outcome_update(source_chat_id, source_msg_id, state='media_group_pending')
            _collect_media_group_for_forward(source_chat_id, msg)
            return
        if source_msg_id:
            _forward_outcome_update(source_chat_id, source_msg_id, state='dispatching')
        for dst_chat_id, mode, finance_enabled in targets:
            _forward_single_to_target(source_chat_id, msg, dst_chat_id, finance_enabled)
        if source_msg_id:
            _forward_outcome_update(source_chat_id, source_msg_id, state='completed')
    except Exception as e:
        log_error(f'forward_any_message fatal: {e}')

# v262
