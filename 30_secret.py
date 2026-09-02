# v262
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
# v262
