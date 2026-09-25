# v266
"""ОЧНИСЬ 12.35 · physical owner: finance_forward.

Этот файл — единственное физическое место тел функций домена.
Он НЕ запускается отдельно и НЕ импортируется как Python-модуль.
bot.py читает его как каталог исходников и устанавливает нужную стадию в исторической точке runtime.
Последняя версия каждого публичного символа сохраняет обычное имя; старые стадии помечены _legacy_sXXXX_.
"""

# --- finance_forward:0001 · from 01_core_data.py:1989 · public _wait_for_finance_priority_before_forward ---
def _wait_for_finance_priority_before_forward(kind: str='forward') -> float:
    """
    v110: финансовая очередь имеет приоритет над пересылкой.
    Пересылка не блокирует finance-worker: она только коротко уступает CPU, пока
    в FINANCE_TASK_POOL есть pending/active работа. Есть жёсткий потолок ожидания,
    чтобы длинный поток финансов не мог навсегда остановить пересылку.
    """
    started = time.monotonic()
    limit = float(FORWARD_FINANCE_PRIORITY_MAX_WAIT_SECONDS or 0.0)
    if limit <= 0:
        return 0.0
    while True:
        try:
            fs = FINANCE_TASK_POOL.stats()
            busy = int(fs.get('pending', 0) or 0) > 0 or int(fs.get('active', 0) or 0) > 0
        except Exception:
            busy = False
        if not busy:
            break
        elapsed = time.monotonic() - started
        if elapsed >= limit:
            try:
                bot_journal('forward_priority_timeout', None, f'kind={kind} waited={elapsed:.3f}s finance still busy', 'WARN')
            except Exception:
                pass
            break
        time.sleep(0.02)
    waited = time.monotonic() - started
    if waited >= 0.05:
        try:
            bot_journal('forward_yielded_to_finance', None, f'kind={kind} waited={waited:.3f}s')
        except Exception:
            pass
    return waited

# --- finance_forward:0002 · from 01_core_data.py:2024 · public _forward_with_finance_priority ---
def _forward_with_finance_priority(source_chat_id: int, msg):
    _wait_for_finance_priority_before_forward('message')
    return forward_any_message(source_chat_id, msg)

# --- finance_forward:0003 · from 01_core_data.py:2028 · public _forward_edit_with_finance_priority ---
def _forward_edit_with_finance_priority(msg):
    _wait_for_finance_priority_before_forward('edit')
    return propagate_edited_to_copies(msg)

# --- finance_forward:0004 · from 01_core_data.py:2032 · public _forward_delete_with_finance_priority ---
def _forward_delete_with_finance_priority(source_chat_id: int, source_msg_id: int):
    _wait_for_finance_priority_before_forward('delete')
    return delete_forward_copies_for_source(source_chat_id, source_msg_id)

# --- finance_forward:0005 · from 01_core_data.py:2036 · public _current_bot_id_for_forwarding ---
def _current_bot_id_for_forwarding() -> int:
    """Return this bot's Telegram user id without a network call when possible."""
    try:
        token = str(globals().get('BOT_TOKEN') or '').strip()
        head = token.split(':', 1)[0].strip()
        if head.isdigit():
            return int(head)
    except Exception:
        pass
    try:
        me = bot.get_me()
        return int(getattr(me, 'id', 0) or 0)
    except Exception:
        return 0

# --- finance_forward:0006 · from 01_core_data.py:2051 · public _forward_anonymous_admin_message ---
def _forward_anonymous_admin_message(msg) -> bool:
    """Telegram represents anonymous/send-as-group admins as a bot-like sender.

    Such messages are human-originated and must be eligible for configured forwarding.
    """
    try:
        sender = getattr(msg, 'from_user', None)
        if not sender or not bool(getattr(sender, 'is_bot', False)):
            return False
        username = str(getattr(sender, 'username', '') or '').lstrip('@').lower()
        if username == 'groupanonymousbot':
            return True
        sender_chat = getattr(msg, 'sender_chat', None)
        chat = getattr(msg, 'chat', None)
        if sender_chat is not None and chat is not None:
            return int(getattr(sender_chat, 'id', 0) or 0) == int(getattr(chat, 'id', 0) or 0) != 0
    except Exception:
        pass
    return False

# --- finance_forward:0007 · from 01_core_data.py:2071 · public _forward_sender_skip_reason ---
def _forward_sender_skip_reason(msg) -> str:
    """R12: accept delivered messages from other bots; skip only this bot itself.

    The self-sender guard prevents forwarding loops. Anonymous/send-as-chat admins and
    genuine third-party bots are eligible for the same configured forwarding rules as
    human senders whenever Telegram delivers the update to us.
    """
    try:
        sender = getattr(msg, 'from_user', None)
        if not sender or not bool(getattr(sender, 'is_bot', False)):
            return ''
        sender_id = int(getattr(sender, 'id', 0) or 0)
        self_id = _current_bot_id_for_forwarding()
        if self_id and sender_id == self_id:
            return 'bot_sender'
        return ''
    except Exception:
        return ''

# --- finance_forward:0008 · from 01_core_data.py:2090 · public _forward_sender_skip_reason_raw ---
def _forward_sender_skip_reason_raw(raw: dict) -> str:
    """Raw-payload twin: third-party bots are forwardable; our own bot is not."""
    if not isinstance(raw, dict):
        return ''
    try:
        sender = raw.get('from') or {}
        if not isinstance(sender, dict) or not bool(sender.get('is_bot')):
            return ''
        sender_id = int(sender.get('id') or 0)
        self_id = _current_bot_id_for_forwarding()
        if self_id and sender_id == self_id:
            return 'bot_sender'
        return ''
    except Exception:
        return ''

# --- finance_forward:0009 · from 01_core_data.py:2106 · public _v177_legacy_0001_schedule_forward_any_message ---
def _v177_legacy_0001_schedule_forward_any_message(source_chat_id: int, msg):
    """Пересылка: порядок по исходному чату сохраняется; finance имеет приоритет.

    v121 keeps an explicit live outcome for the asynchronous worker. This prevents a
    successful handler from becoming MEGA/failed merely because forwarding was skipped
    by design or an album was still waiting for its delayed media-group flush.
    """
    try:
        sender_skip_reason = _forward_sender_skip_reason(msg)
        if sender_skip_reason:
            _forward_outcome_skip(source_chat_id, msg, sender_skip_reason)
            return
        if _forward_anonymous_admin_message(msg):
            try:
                bot_journal('anonymous_admin_forward_allowed', int(source_chat_id), f"msg={int(getattr(msg, 'message_id', 0) or 0)} sender_chat={int(getattr(getattr(msg, 'sender_chat', None), 'id', 0) or 0)}")
            except Exception:
                pass
        if getattr(msg, 'edit_date', None):
            _forward_outcome_skip(source_chat_id, msg, 'edited_source')
            return
    except Exception:
        pass
    _durable_note_forward_decision(int(source_chat_id), direct=False)
    try:
        mid = int(getattr(msg, 'message_id', 0) or 0)
        if mid:
            _forward_outcome_update(source_chat_id, mid, state='scheduled')
    except Exception:
        pass
    pipeline = globals().get('schedule_financial_forward_pipeline')
    if callable(pipeline):
        pipeline(int(source_chat_id), msg)
        return
    if not FIN_FORWARD_TASK_POOL.submit(int(source_chat_id), _forward_with_finance_priority, source_chat_id, msg):
        log_error(f'FIN-FORWARD QUEUE FULL, INLINE FALLBACK: {source_chat_id}')
        _forward_with_finance_priority(source_chat_id, msg)

# --- finance_forward:0010 · from 01_core_data.py:2153 · public schedule_delete_forward_copies_for_source ---
def schedule_delete_forward_copies_for_source(source_chat_id: int, source_msg_id: int):
    if not FORWARD_TASK_POOL.submit(int(source_chat_id), _forward_delete_with_finance_priority, source_chat_id, source_msg_id):
        log_error(f'FORWARD DELETE QUEUE FULL, INLINE FALLBACK: {source_chat_id}')
        _forward_delete_with_finance_priority(source_chat_id, source_msg_id)

# --- finance_forward:0011 · from 01_core_data.py:2317 · public _forward_outcome_key ---
def _forward_outcome_key(source_chat_id: int, source_msg_id: int):
    return (int(source_chat_id), int(source_msg_id))

# --- finance_forward:0012 · from 01_core_data.py:2320 · public _forward_outcome_prune_locked ---
def _forward_outcome_prune_locked():
    if len(_FORWARD_OUTCOMES) <= _FORWARD_OUTCOME_MAX:
        return
    ordered = sorted(_FORWARD_OUTCOMES.items(), key=lambda kv: float((kv[1] or {}).get('updated_at', 0.0) or 0.0))
    for key, _item in ordered[:max(1, len(ordered) - _FORWARD_OUTCOME_MAX)]:
        _FORWARD_OUTCOMES.pop(key, None)

# --- finance_forward:0013 · from 01_core_data.py:2327 · public _forward_outcome_update ---
def _forward_outcome_update(source_chat_id: int, source_msg_id: int, state: str | None=None, dst_chat_id: int | None=None, dst_state: str | None=None, dst_msg_id: int | None=None, error: str=''):
    try:
        key = _forward_outcome_key(source_chat_id, source_msg_id)
        with _FORWARD_OUTCOME_LOCK:
            item = _FORWARD_OUTCOMES.setdefault(key, {'state': '', 'targets': {}, 'updated_at': time.time()})
            if state:
                item['state'] = str(state)
            if dst_chat_id is not None:
                dst = int(dst_chat_id)
                target = item.setdefault('targets', {}).setdefault(dst, {})
                if dst_state:
                    target['state'] = str(dst_state)
                if dst_msg_id:
                    target['dst_msg_id'] = int(dst_msg_id)
                if error:
                    target['error'] = str(error)[:500]
            item['updated_at'] = time.time()
            _forward_outcome_prune_locked()
    except Exception:
        pass

# --- finance_forward:0014 · from 01_core_data.py:2348 · public _forward_outcome_snapshot ---
def _forward_outcome_snapshot(source_chat_id: int, source_msg_id: int) -> dict:
    try:
        key = _forward_outcome_key(source_chat_id, source_msg_id)
        with _FORWARD_OUTCOME_LOCK:
            return copy.deepcopy(_FORWARD_OUTCOMES.get(key) or {})
    except Exception:
        return {}

# --- finance_forward:0015 · from 01_core_data.py:2356 · public _forward_outcome_skip ---
def _forward_outcome_skip(source_chat_id: int, msg, reason: str):
    try:
        mid = int(getattr(msg, 'message_id', 0) or 0)
        if mid:
            _forward_outcome_update(source_chat_id, mid, state=f'skip:{reason}')
            bot_journal('forward_not_expected', source_chat_id, f'msg={mid} reason={reason}')
    except Exception:
        pass

# --- finance_forward:0016 · from 01_core_data.py:3856 · public forward_menu_new_style_enabled ---
def forward_menu_new_style_enabled(chat_id: int | None=None) -> bool:
    return bool(_owner_setting_value('forward_menu_new_style', False, chat_id))

# --- finance_forward:0017 · from 01_core_data.py:3859 · public _v177_legacy_0004_set_forward_menu_new_style_enabled ---
def _v177_legacy_0004_set_forward_menu_new_style_enabled(enabled: bool, chat_id: int | None=None):
    try:
        _set_owner_setting_value('forward_menu_new_style', bool(enabled), chat_id)
    except Exception as e:
        log_error(f'set_forward_menu_new_style_enabled: {e}')

# --- finance_forward:0018 · from 01_core_data.py:3869 · public _v177_legacy_0005_toggle_forward_menu_new_style ---
def _v177_legacy_0005_toggle_forward_menu_new_style(chat_id: int | None=None) -> bool:
    new_value = not forward_menu_new_style_enabled(chat_id)
    set_forward_menu_new_style_enabled(new_value, chat_id)
    return new_value

# --- finance_forward:0019 · from 01_core_data.py:3878 · public forward_menu_style_label ---
def forward_menu_style_label(chat_id: int | None=None) -> str:
    return '🧩 Пересылка: по-новому' if forward_menu_new_style_enabled(chat_id) else '🔁 Пересылка: обычно'

# --- finance_forward:0020 · from 01_core_data.py:5824 · public is_forwarded_telegram_message ---
def is_forwarded_telegram_message(msg) -> bool:
    """True only for Telegram-forwarded input; ordinary fresh finance text is untouched."""
    if msg is None:
        return False
    for attr in ('forward_origin', 'forward_date', 'forward_from', 'forward_from_chat', 'forward_sender_name'):
        try:
            if getattr(msg, attr, None):
                return True
        except Exception:
            pass
    return False

# --- finance_forward:0021 · from 01_core_data.py:8915 · public _forward_arrow_icon ---
def _forward_arrow_icon(ab_on: bool, ba_on: bool) -> str:
    if ab_on and ba_on:
        return '🔄'
    if ab_on:
        return '⏩️'
    if ba_on:
        return '⏪️'
    return '⬜'

# --- finance_forward:0022 · from 01_core_data.py:8924 · public _forward_fin_icon ---
def _forward_fin_icon(ab_fin: bool, ba_fin: bool) -> str:
    if ab_fin and ba_fin:
        return '💰🔄'
    if ab_fin:
        return '💰▶️'
    if ba_fin:
        return '💰◀️'
    return '⬜'

# --- finance_forward:0023 · from 01_core_data.py:8933 · public _v177_legacy_0060_build_forward_status_lines ---
def _v177_legacy_0060_build_forward_status_lines() -> list[str]:
    """Статус В22: короткая схема связей.
    Всегда показываем Чат A первым:
    Чат A -(⏩️/⏪️/🔄/⬜)-(💰▶️/💰◀️/💰🔄/⬜)-Чат B
    """
    lines = []
    fr = data.get('forward_rules', {}) or {}
    ff = data.get('forward_finance', {}) or {}
    seen_pairs = set()

    def _sorted_pair(a: int, b: int):
        name_a = get_chat_display_name(a).lower()
        name_b = get_chat_display_name(b).lower()
        if (name_a, a) <= (name_b, b):
            return (a, b)
        return (b, a)
    all_pairs = set()
    for src, dsts in fr.items():
        try:
            src_id = int(src)
        except Exception:
            continue
        for dst in (dsts or {}).keys():
            try:
                dst_id = int(dst)
            except Exception:
                continue
            all_pairs.add(_sorted_pair(src_id, dst_id))
    for a_id, b_id in sorted(all_pairs, key=lambda p: (get_chat_display_name(p[0]).lower(), get_chat_display_name(p[1]).lower())):
        pair_key = (a_id, b_id)
        if pair_key in seen_pairs:
            continue
        seen_pairs.add(pair_key)
        ab_on = str(b_id) in (fr.get(str(a_id), {}) or {})
        ba_on = str(a_id) in (fr.get(str(b_id), {}) or {})
        if not (ab_on or ba_on):
            continue
        ab_fin = bool((ff.get(str(a_id), {}) or {}).get(str(b_id), False))
        ba_fin = bool((ff.get(str(b_id), {}) or {}).get(str(a_id), False))
        name_a = chat_button_title(a_id)
        name_b = chat_button_title(b_id)
        lines.append(f'• {name_a} -({_forward_arrow_icon(ab_on, ba_on)})-({_forward_fin_icon(ab_fin, ba_fin)})-{name_b}')
    if not lines:
        lines.append('• Связи пересылки не настроены')
    return lines

# --- finance_forward:0024 · from 01_core_data.py:8983 · public build_forward_status_text ---
def build_forward_status_text(title: str | None=None) -> str:
    lines = []
    if title:
        lines.append(title)
        lines.append('')
    if title and 'Пересылка' in str(title):
        lines.append('Шаги: 1) выберите чат A → 2) выберите чат B → 3) включите 📨 пересылку и 💰 финучёт пересылки по нужным направлениям.')
        lines.append('')
    lines.append('Текущие связи:')
    lines.extend(build_forward_status_lines())
    # R70: visual rules are not enough.  Show whether the production resolver
    # would actually route messages now (mode/status/tenant/suspension included).
    try:
        pair_fn = globals().get('collect_forward_pairs_for_menu')
        resolver = globals().get('resolve_forward_targets')
        pairs = list(pair_fn() or []) if callable(pair_fn) else []
        blocked=[]; active=0
        if callable(resolver):
            for a,b in pairs:
                ab = int(b) in {int(x) for x in (resolver(int(a)) or [])}
                ba = int(a) in {int(x) for x in (resolver(int(b)) or [])}
                active += int(ab) + int(ba)
                if not ab and not ba:
                    blocked.append((int(a),int(b)))
        if pairs:
            lines.append('')
            lines.append(f'Runtime-маршруты: ✅ {active} направлений · ⚠️ полностью заблокированных пар {len(blocked)}')
            for a,b in blocked[:6]:
                lines.append(f'⚠️ {chat_button_title(a)} ↔ {chat_button_title(b)}: правило есть, но resolve_forward_targets() сейчас не даёт маршрут')
            if len(blocked)>6:
                lines.append(f'…ещё {len(blocked)-6}')
    except Exception:
        pass
    return '\n'.join(lines)

# --- finance_forward:0025 · from 01_core_data.py:9018 · public _find_forward_origin_by_copied_message ---
def _find_forward_origin_by_copied_message(chat_id: int, msg_id: int):
    """
    Ищет origin (source_chat_id, source_msg_id) по копии сообщения в конкретном чате.
    Нужно для правильного reply, когда пользователь отвечает на сообщение,
    которое бот ранее переслал из другого чата.
    """
    try:
        for (src_chat_id, src_msg_id), pairs in forward_map.items():
            for pair_chat_id, pair_msg_id in pairs:
                if int(pair_chat_id) == int(chat_id) and int(pair_msg_id) == int(msg_id):
                    return (int(src_chat_id), int(src_msg_id))
    except Exception:
        pass
    return (None, None)

# --- finance_forward:0026 · from 01_core_data.py:11018 · public _durable_forward_targets ---
def _durable_forward_targets(source_chat_id: int | None) -> list[tuple]:
    if source_chat_id is None:
        return []
    try:
        return list(resolve_forward_targets(int(source_chat_id)) or [])
    except Exception as e:
        log_error(f'DURABLE resolve targets {source_chat_id}: {e}')
        return []

# --- finance_forward:0027 · from 01_core_data.py:11377 · public _durable_live_forward_outcome ---
def _durable_live_forward_outcome(payload: dict) -> dict:
    raw, source_chat_id, source_msg_id, _group_id = _durable_payload_message(payload or {})
    if not isinstance(raw, dict) or source_chat_id is None or source_msg_id is None:
        return {}
    return _forward_outcome_snapshot(int(source_chat_id), int(source_msg_id))

# --- finance_forward:0028 · from 01_core_data.py:11383 · public _durable_apply_live_forward_outcome ---
def _durable_apply_live_forward_outcome(payload: dict, expected: dict | None) -> dict:
    """Use only concrete live worker evidence; never guesses a Telegram delivery.

    skip:* means the worker deliberately did not send. delivered carries the Telegram
    destination message id and can safely rebuild a missing local forward index. Failed or
    pending targets remain expected and therefore cannot be silently lost.
    """
    adjusted = _delta_json_clone(expected or {}) if isinstance(expected, dict) else {}
    raw, source_chat_id, source_msg_id, _group_id = _durable_payload_message(payload or {})
    if not isinstance(raw, dict) or source_chat_id is None or source_msg_id is None:
        return adjusted
    outcome = _forward_outcome_snapshot(int(source_chat_id), int(source_msg_id))
    state = str(outcome.get('state') or '')
    if state.startswith('skip:') or state == 'no_targets':
        adjusted['forward_targets'] = []
        adjusted['forward_suppressed_by_live_outcome'] = state
        return adjusted
    targets = outcome.get('targets') or {}
    terminal = set()
    for dst_raw, info in list(targets.items()):
        try:
            dst = int(dst_raw)
            info = info or {}
            target_state = str(info.get('state') or '')
            if target_state in {'suspended', 'migrated', 'unavailable_terminal'}:
                terminal.add(dst)
                continue
            if target_state != 'delivered':
                continue
            dst_msg_id = int(info.get('dst_msg_id') or 0)
            if not dst_msg_id:
                continue
            current = {int(d): int(m) for d, m in get_forward_links(int(source_chat_id), int(source_msg_id))}
            if int(current.get(dst) or 0) != dst_msg_id:
                _store_forward_link(int(source_chat_id), int(source_msg_id), dst, dst_msg_id)
                try:
                    _persist_forward_index_in_data(data)
                    save_data(data, root_only=True)
                except Exception as e:
                    log_error(f'[FORWARD OUTCOME LINK REPAIR] {source_chat_id}:{source_msg_id}->{dst}:{dst_msg_id}: {e}')
        except Exception as e:
            log_error(f'durable live forward outcome repair: {e}')
    if terminal:
        adjusted['forward_targets'] = [row for row in adjusted.get('forward_targets') or [] if int((row or {}).get('dst_chat_id') or 0) not in terminal]
        adjusted['forward_terminal_targets_v199'] = sorted(terminal)
    return adjusted

# --- finance_forward:0029 · from 01_core_data.py:11430 · public _durable_forward_work_still_pending ---
def _durable_forward_work_still_pending(payload: dict) -> bool:
    """True only when this live process has positive evidence that forwarding is not finished yet."""
    try:
        raw, source_chat_id, source_msg_id, group_id = _durable_payload_message(payload or {})
        if not isinstance(raw, dict) or source_chat_id is None or source_msg_id is None:
            return False
        if group_id and _durable_media_group_in_memory(payload):
            return True
        outcome = _forward_outcome_snapshot(int(source_chat_id), int(source_msg_id))
        state = str(outcome.get('state') or '')
        if state in {'scheduled', 'dispatching', 'media_group_pending'}:
            return True
        for info in (outcome.get('targets') or {}).values():
            if str((info or {}).get('state') or '') in {'pending', 'attempted'}:
                return True
    except Exception:
        return False
    return False

# --- finance_forward:0030 · from 01_core_data.py:11612 · public _durable_forward_effect_complete ---
def _durable_forward_effect_complete(payload: dict, expected: dict | None=None) -> bool:
    """Verify only forwarding effects explicitly expected for this task."""
    expected = expected if isinstance(expected, dict) else _durable_expected_effects(payload)
    report = _durable_effect_report(payload, expected)
    for item in (report.get('missing') or []) + (report.get('ambiguous') or []):
        if str(item).startswith('forward'):
            return False
    return True

# --- finance_forward:0031 · from 01_core_data.py:11680 · public _repair_missing_durable_forward ---
def _repair_missing_durable_forward(payload: dict) -> bool:
    """Best-effort repair of missing forwarding directions without duplicating delivered ones.

    Albums are normally sent together by the 0.8s collector. If that collector vanished because
    Render deployed, each persisted album part can be resent individually to only the missing
    destinations. The important invariant is no lost message; already-linked destinations are skipped.
    """
    raw, source_chat_id, source_msg_id, group_id = _durable_payload_message(payload)
    if not isinstance(raw, dict) or source_chat_id is None or source_msg_id is None:
        return True
    targets = _durable_forward_targets(source_chat_id)
    if not targets:
        return True
    if group_id and _durable_media_group_in_memory(payload):
        return False
    links = {}
    try:
        links = {int(dst): int(mid) for dst, mid in get_forward_links(source_chat_id, source_msg_id)}
    except Exception:
        links = {}
    missing = [(int(dst), mode, bool(fin)) for dst, mode, fin in targets if int(dst) not in links]
    if not missing:
        return True
    msg = _durable_payload_to_message(payload)
    if msg is None:
        return False
    all_ok = True
    for dst_chat_id, _mode, finance_enabled in missing:
        try:
            result = _forward_single_to_target(source_chat_id, msg, dst_chat_id, finance_enabled)
            if not result:
                all_ok = False
        except Exception as e:
            all_ok = False
            log_error(f'DURABLE FORWARD REPAIR {source_chat_id}:{source_msg_id}->{dst_chat_id}: {e}')
    return bool(all_ok and _durable_forward_effect_complete(payload))

# --- finance_forward:0032 · from 01_core_data.py:11981 · public _durable_note_forward_decision ---
def _durable_note_forward_decision(source_chat_id: int, direct: bool=False):
    """Record the ACTUAL handler decision, not the potential configuration.

    This stays in the current update thread only.  The finalizer uses it after the handler
    returns, so a text consumed by SECRET/edit/category/wait state is not falsely marked
    as three missing forwards merely because forwarding is configured for the chat.
    """
    try:
        ctx = getattr(_TELEGRAM_UPDATE_CONTEXT, 'value', None)
        if not isinstance(ctx, dict):
            return
        if ctx.get('chat_id') is not None and int(ctx.get('chat_id')) != int(source_chat_id):
            return
        ctx['forward_decision_reached'] = True
        ctx['forward_direct'] = bool(direct)
        ctx['actual_forward_targets'] = _durable_target_specs_for_source(int(source_chat_id))
    except Exception as e:
        try:
            log_error(f'durable forward decision note {source_chat_id}: {e}')
        except Exception:
            pass

# --- finance_forward:0033 · from 01_core_data.py:12003 · public _durable_note_forward_target_migration ---
def _durable_note_forward_target_migration(source_chat_id: int, old_chat_id: int, new_chat_id: int):
    """Keep the live durable witness aligned with Telegram basic-group -> supergroup migration.

    The forwarding worker may discover the new destination only after the handler has already
    captured its original target list. Without this rewrite the finalizer keeps waiting for the
    obsolete chat_id and can move a successfully delivered task to MEGA/failed.
    """
    try:
        ctx = getattr(_TELEGRAM_UPDATE_CONTEXT, 'value', None)
        if not isinstance(ctx, dict):
            return False
        if ctx.get('chat_id') is not None and int(ctx.get('chat_id')) != int(source_chat_id):
            return False
        changed = False
        specs = ctx.get('actual_forward_targets') or []
        for spec in specs:
            if not isinstance(spec, dict):
                continue
            try:
                if int(spec.get('dst_chat_id')) != int(old_chat_id):
                    continue
            except Exception:
                continue
            spec['dst_chat_id'] = int(new_chat_id)
            try:
                spec['secret_expected'] = bool(is_total_secret_mode(int(new_chat_id)))
            except Exception:
                pass
            changed = True
        if changed:
            try:
                bot_journal('durable_forward_target_migrated', int(source_chat_id), f'{int(old_chat_id)}->{int(new_chat_id)}')
            except Exception:
                pass
        return changed
    except Exception as e:
        try:
            log_error(f'durable forward target migration {old_chat_id}->{new_chat_id}: {e}')
        except Exception:
            pass
        return False

# --- finance_forward:0034 · from 01_core_data.py:16715 · public _v177_legacy_0088_collect_forward_menu_chats ---
def _v177_legacy_0088_collect_forward_menu_chats() -> dict:
    """
    Собирает список чатов для меню пересылки:
    1) из known_chats владельца
    2) из data["chats"] как резерв
    """
    result = {}
    if OWNER_ID:
        try:
            owner_store = get_chat_store(int(OWNER_ID))
            known = owner_store.get('known_chats', {}) or {}
            for cid, info in known.items():
                result[str(cid)] = {'title': info.get('title') or f'Чат {cid}', 'username': info.get('username'), 'type': info.get('type')}
        except Exception as e:
            log_error(f'collect_forward_menu_chats known_chats: {e}')
    try:
        for cid, store in (data.get('chats', {}) or {}).items():
            if OWNER_ID and str(cid) == str(OWNER_ID):
                continue
            info = store.get('info', {}) or {}
            prev = result.get(str(cid), {})
            result[str(cid)] = {'title': info.get('title') or prev.get('title') or f'Чат {cid}', 'username': info.get('username') or prev.get('username'), 'type': info.get('type') or prev.get('type')}
    except Exception as e:
        log_error(f'collect_forward_menu_chats data.chats: {e}')
    deduped = {}
    seen = set()
    for cid, info in sorted(result.items(), key=lambda kv: (str((kv[1] or {}).get('title') or '').lower(), str(kv[0]))):
        try:
            key = _chat_identity_key(int(cid), info if isinstance(info, dict) else {})
        except Exception:
            key = 'id:' + str(cid)
        if key in seen:
            continue
        seen.add(key)
        deduped[str(cid)] = info
    return deduped

# --- finance_forward:0035 · from 01_core_data.py:17833 · public restore_forward_edges_exact ---
def restore_forward_edges_exact(root_key: str, chat_id: int, outgoing: dict, incoming: dict) -> dict:
    """STRICT restore of forwarding edges belonging to one chat, without merge or per-edge side effects."""
    if root_key not in {'forward_rules', 'forward_finance'}:
        raise ValueError(f'Unsupported forwarding root: {root_key}')
    cid = str(int(chat_id))
    outgoing = outgoing if isinstance(outgoing, dict) else {}
    incoming = incoming if isinstance(incoming, dict) else {}
    lock = globals().get('_V166_FORWARD_STATE_LOCK')

    def _apply():
        root = data.setdefault(root_key, {})
        if not isinstance(root, dict):
            root = {}
            data[root_key] = root
        root.pop(cid, None)
        for src in list(root.keys()):
            row = root.get(src)
            if not isinstance(row, dict):
                continue
            row.pop(cid, None)
            if not row:
                root.pop(src, None)
        if outgoing:
            root[cid] = _v184_copy(outgoing)
        for src, value in incoming.items():
            ss = str(src)
            if ss == cid:
                if cid not in root and outgoing:
                    root[cid] = _v184_copy(outgoing)
                continue
            root.setdefault(ss, {})[cid] = _v184_copy(value)
    if lock is not None:
        with data_lock, lock:
            _apply()
    else:
        with data_lock:
            _apply()
    try:
        order = data.get('forward_pair_order')
        if isinstance(order, list):
            kept = []
            for key in order:
                try:
                    a, b = str(key).split(':', 1)
                except Exception:
                    kept.append(key)
                    continue
                if a == cid or b == cid:
                    continue
                kept.append(key)
            data['forward_pair_order'] = kept
    except Exception:
        pass
    return {'root': root_key, 'chat_id': int(chat_id), 'outgoing': len(outgoing), 'incoming': len(incoming)}

# --- finance_forward:0036 · from 04_messages_features.py:4253 · public sync_forwarded_finance_message ---
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
    added_by_hotpath = False
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
        # _finance_add_record_base already performed the authoritative local SQLite commit.
        # Do not immediately deep-copy and persist the same chat a second time.
        added_by_hotpath = isinstance(result_rec, dict)
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
        if (not added_by_hotpath) and 'persist_finance_chat_local_fast' in globals() and not persist_finance_chat_local_fast(dst_chat_id):
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
    _r77_reconcile = globals().get('schedule_finance_reconcile_r77')
    if callable(_r77_reconcile):
        _r77_reconcile(dst_chat_id, entry_day, reason='forward_finance', delay=0.55)
    else:
        schedule_finalize(dst_chat_id,entry_day)
    return result_rec if isinstance(result_rec,dict) else False

# --- finance_forward:0037 · from 04_messages_features.py:4592 · public load_forward_rules ---
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

# --- finance_forward:0038 · from 04_messages_features.py:4629 · public persist_forward_rules_to_owner ---
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

# --- finance_forward:0039 · from 04_messages_features.py:4687 · public is_forward_target_suspended_v199 ---
def is_forward_target_suspended_v199(chat_id: int) -> bool:
    try:
        cid = int(chat_id)
        if str(cid) in _v199_suspended_root():
            return True
        canonical = resolve_canonical_chat_id_v199(cid)
        return str(canonical) in _v199_suspended_root()
    except Exception:
        return False

# --- finance_forward:0040 · from 04_messages_features.py:4736 · public suspend_forward_target_v199 ---
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

# --- finance_forward:0041 · from 04_messages_features.py:4820 · public reactivate_forward_target_v199 ---
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

# --- finance_forward:0042 · from 04_messages_features.py:4863 · public _v199_confirm_failed_forward_target ---
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

# --- finance_forward:0043 · from 04_messages_features.py:4888 · public _v177_legacy_0140_resolve_forward_targets ---
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

# --- finance_forward:0044 · from 04_messages_features.py:4917 · public _v177_legacy_0141_add_forward_link ---
def _v177_legacy_0141_add_forward_link(src_chat_id: int, dst_chat_id: int, mode: str):
    fr = data.setdefault('forward_rules', {})
    src = str(src_chat_id)
    dst = str(dst_chat_id)
    fr.setdefault(src, {})[dst] = mode
    persist_forward_rules_to_owner()
    save_data(data)
    schedule_config_backup_for_chats(src_chat_id, dst_chat_id)

# --- finance_forward:0045 · from 04_messages_features.py:4930 · public _v177_legacy_0144_remove_forward_link ---
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

# --- finance_forward:0046 · from 04_messages_features.py:4947 · public _v177_legacy_0145_clear_forward_all ---
def _v177_legacy_0145_clear_forward_all():
    """Полностью отключает всю пересылку."""
    data['forward_rules'] = {}
    data['forward_finance'] = {}
    persist_forward_rules_to_owner()
    save_data(data)
    schedule_config_backup_for_chats()

# --- finance_forward:0047 · from 04_messages_features.py:4959 · public get_forward_finance ---
def get_forward_finance(src_chat_id: int, dst_chat_id: int) -> bool:
    ff = data.setdefault('forward_finance', {})
    return bool(ff.get(str(src_chat_id), {}).get(str(dst_chat_id), False))

# --- finance_forward:0048 · from 04_messages_features.py:4964 · public _v177_legacy_0146_forward_copy_edit_mode ---
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

# --- finance_forward:0049 · from 04_messages_features.py:5001 · public _v177_legacy_0148_set_forward_copy_edit_mode ---
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

# --- finance_forward:0050 · from 04_messages_features.py:5030 · public _v177_legacy_0150_cycle_forward_copy_edit_mode ---
def _v177_legacy_0150_cycle_forward_copy_edit_mode(chat_id: int) -> str:
    current = forward_copy_edit_mode(int(chat_id))
    try:
        idx = FORWARD_COPY_EDIT_MODES.index(current)
    except ValueError:
        idx = 0
    return set_forward_copy_edit_mode(int(chat_id), FORWARD_COPY_EDIT_MODES[(idx + 1) % len(FORWARD_COPY_EDIT_MODES)])

# --- finance_forward:0051 · from 04_messages_features.py:5042 · public _v177_legacy_0151_forward_copy_edit_mode_label ---
def _v177_legacy_0151_forward_copy_edit_mode_label(chat_id: int) -> str:
    mode = forward_copy_edit_mode(int(chat_id))
    return {'normal': '💰Перес: обычно', 'button': '💰Перес: кнопка', 'slash': '💰Перес: слеш'}.get(mode, '💰Перес: обычно')

# --- finance_forward:0052 · from 04_messages_features.py:5064 · public _begin_forward_copy_retro_refresh ---
def _begin_forward_copy_retro_refresh(owner_chat_id: int) -> int:
    scope = 0
    with _FORWARD_COPY_RETRO_LOCK:
        generation = int(_FORWARD_COPY_RETRO_GENERATION.get(scope, 0) or 0) + 1
        _FORWARD_COPY_RETRO_GENERATION[scope] = generation
        return generation

# --- finance_forward:0053 · from 04_messages_features.py:5071 · public _forward_copy_retro_is_stale ---
def _forward_copy_retro_is_stale(owner_chat_id: int, generation: int | None) -> bool:
    if generation is None:
        return False
    with _FORWARD_COPY_RETRO_LOCK:
        return int(_FORWARD_COPY_RETRO_GENERATION.get(0, 0) or 0) != int(generation)

# --- finance_forward:0054 · from 04_messages_features.py:5077 · public _forward_copy_record_identity ---
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

# --- finance_forward:0055 · from 04_messages_features.py:5110 · public _hydrate_legacy_forward_copy_metadata ---
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

# --- finance_forward:0056 · from 04_messages_features.py:5146 · public _forward_copy_retro_record_is_recent ---
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

# --- finance_forward:0057 · from 04_messages_features.py:5164 · public refresh_existing_forward_copy_ui ---
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
                    fast_ui_edit_reply_markup(cid, msg_id, markup, purpose='forward_copy_retro_markup_fast', attempts=1)
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

# --- finance_forward:0058 · from 04_messages_features.py:5376 · public _strip_forward_copy_edit_command ---
def _strip_forward_copy_edit_command(text: str) -> str:
    raw = str(text or '').rstrip()
    return re.sub('(?:\\n|\\s)+/izm_[RU]\\d+(?:_u[A-F0-9]{12})?\\s*$', '', raw, flags=re.I).rstrip()

# --- finance_forward:0059 · from 04_messages_features.py:5380 · public _forward_copy_record_command ---
def _forward_copy_record_command(rec: dict) -> str:
    sid = str((rec or {}).get('short_id') or f"R{(rec or {}).get('id', '')}").strip().upper()
    if not re.fullmatch('[RU]\\d+', sid):
        sid = 'R' + re.sub('\\D+', '', sid)
    uid = str((rec or {}).get('record_uid') or '').strip().upper()
    return f'/izm_{sid}_u{uid}' if re.fullmatch('[A-F0-9]{12}', uid) else f'/izm_{sid}'

# --- finance_forward:0060 · from 04_messages_features.py:5387 · public _v169_forward_uid_for_copy ---
def _v169_forward_uid_for_copy(dst_chat_id: int, source_msg) -> str:
    """Deterministic UID known before Telegram creates the destination copy."""
    try:
        src_chat_id = int(getattr(getattr(source_msg, 'chat', None), 'id', 0) or 0)
        src_msg_id = int(getattr(source_msg, 'forward_source_msg_id', 0) or getattr(source_msg, 'message_id', 0) or 0)
        raw = f'forward-copy:{src_chat_id}:{src_msg_id}:{int(dst_chat_id)}'
        return hashlib.sha256(raw.encode('utf-8', errors='replace')).hexdigest()[:12].upper()
    except Exception:
        return ''

# --- finance_forward:0061 · from 04_messages_features.py:5397 · public _predict_forward_copy_record_command ---
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

# --- finance_forward:0062 · from 04_messages_features.py:5471 · public _forward_copy_display_text ---
def _forward_copy_display_text(base_text: str, rec: dict | None, mode: str) -> str:
    base = _strip_forward_copy_edit_command(base_text)
    if mode == 'slash' and rec:
        return (base + '\n' + _forward_copy_record_command(rec)).strip()
    return base

# --- finance_forward:0063 · from 04_messages_features.py:5477 · public _forward_copy_edit_keyboard ---
def _forward_copy_edit_keyboard(mode: str):
    if mode != 'button':
        return None
    kb = types.InlineKeyboardMarkup()
    kb.row(IB('✏️ Изменить', callback_data='fwdcopy_edit'))
    return kb

# --- finance_forward:0064 · from 04_messages_features.py:5484 · public _forward_copy_origin_source_chat ---
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

# --- finance_forward:0065 · from 04_messages_features.py:5496 · public _set_forward_record_metadata ---
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

# --- finance_forward:0066 · from 04_messages_features.py:5516 · public apply_forward_copy_edit_ui ---
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
            fast_ui_edit_reply_markup(int(dst_chat_id), int(dst_msg_id), reply_markup, purpose='forward_copy_edit_apply_markup', attempts=3)
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

# --- finance_forward:0067 · from 04_messages_features.py:5569 · public schedule_forward_copy_edit_ui_retry ---
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

# --- finance_forward:0068 · from 04_messages_features.py:5581 · public _forward_copy_edit_wait_scheduler_key ---
def _forward_copy_edit_wait_scheduler_key(chat_id: int) -> str:
    return f'forward-copy-edit-wait:{int(chat_id)}'

# --- finance_forward:0069 · from 04_messages_features.py:5584 · public _forward_copy_clean_copy_button ---
def _forward_copy_clean_copy_button(text: str):
    """Compatibility helper kept for old code paths; v125 uses the main edit insert UX."""
    return make_copy_or_inline_button('✍️ Вставить текст', '\n' + str(text or ''), viewer_chat_id=None)

# --- finance_forward:0070 · from 04_messages_features.py:5588 · public _forward_copy_edit_prompt_text ---
def _forward_copy_edit_prompt_text(rec: dict, current: str) -> str:
    sid = str(rec.get('short_id') or 'R' + str(rec.get('id')))
    return wm_common(f'✏️ Редактирование записи {sid}\n\nТекущие данные:\n{current}\n\n✍️ Напишите новые данные.\nБудет изменена эта бот-копия и связанная финансовая запись.\n\n⏳ Это сообщение и режим редактирования будут автоматически отменены через 40 секунд.', 10)

# --- finance_forward:0071 · from 04_messages_features.py:5592 · public _forward_copy_edit_prompt_keyboard ---
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

# --- finance_forward:0072 · from 04_messages_features.py:5606 · public refresh_active_forward_copy_edit_prompt ---
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

# --- finance_forward:0073 · from 04_messages_features.py:5637 · public clear_forward_copy_edit_wait ---
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

# --- finance_forward:0074 · from 04_messages_features.py:5653 · public schedule_forward_copy_edit_wait_cancel ---
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

# --- finance_forward:0075 · from 04_messages_features.py:5670 · public start_forward_copy_edit ---
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

# --- finance_forward:0076 · from 04_messages_features.py:5702 · public _v177_legacy_0152_ensure_hidden_finance_for_forward_dst ---
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

# --- finance_forward:0077 · from 04_messages_features.py:5721 · public _v177_legacy_0153_set_forward_finance ---
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

# --- finance_forward:0078 · from 04_messages_features.py:5736 · public _v177_legacy_0154_remove_forward_finance ---
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

# --- finance_forward:0079 · from 04_messages_features.py:5752 · public _forward_key ---
def _forward_key(src_chat_id: int, src_msg_id: int) -> str:
    return f'{int(src_chat_id)}:{int(src_msg_id)}'

# --- finance_forward:0080 · from 04_messages_features.py:5755 · public _schedule_persist_forward_state ---
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

# --- finance_forward:0081 · from 04_messages_features.py:5767 · public _persist_forward_index_in_data ---
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

# --- finance_forward:0082 · from 04_messages_features.py:5781 · public _load_forward_index_from_data ---
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

# --- finance_forward:0083 · from 04_messages_features.py:5803 · public _store_forward_link ---
def _store_forward_link(src_chat_id: int, src_msg_id: int, dst_chat_id: int, dst_msg_id: int):
    with forward_map_lock:
        key = (int(src_chat_id), int(src_msg_id))
        pair = (int(dst_chat_id), int(dst_msg_id))
        items = forward_map.setdefault(key, [])
        if pair not in items:
            items.append(pair)
    _schedule_persist_forward_state()

# --- finance_forward:0084 · from 04_messages_features.py:5812 · public _v177_legacy_0155_persist_forward_finance_delivery_now ---
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

# --- finance_forward:0085 · from 04_messages_features.py:5858 · public _rebuild_forward_index_from_finance_records ---
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

# --- finance_forward:0086 · from 04_messages_features.py:5900 · public get_forward_links ---
def _legacy_s0086_get_forward_links(src_chat_id: int, src_msg_id: int):
    with forward_map_lock:
        return list(forward_map.get((int(src_chat_id), int(src_msg_id)), []))

# --- finance_forward:0087 · from 04_messages_features.py:5904 · public delete_forward_copies_for_source ---
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

# --- finance_forward:0088 · from 04_messages_features.py:5922 · public is_forward_delete_command ---
def is_forward_delete_command(text: str) -> bool:
    t = (text or '').strip().lower()
    return t in ('/del', '/дел', '/д')

# --- finance_forward:0089 · from 04_messages_features.py:6041 · public delete_forwarded_finance_record_by_msg_id ---
def delete_forwarded_finance_record_by_msg_id(chat_id: int, msg_id: int) -> bool:
    with locked_chat(chat_id):
        rec = find_record_by_message_id(chat_id, msg_id)
        if not rec: return False
        rid = int(rec['id']); day_key = rec.get('day_key') or today_key()
    delete_record_in_chat(chat_id, rid)
    schedule_finalize(chat_id, day_key)
    return True

# --- finance_forward:0090 · from 04_messages_features.py:6052 · public rebind_forwarded_finance_record ---
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

# --- finance_forward:0091 · from 04_messages_features.py:6085 · public _replace_forward_link_pair ---
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

# --- finance_forward:0092 · from 04_messages_features.py:6117 · public _v260_forward_finance_op_key ---
def _v260_forward_finance_op_key(source_chat_id: int, source_msg_id: int, dst_chat_id: int) -> str:
    return f"{int(source_chat_id)}:{int(source_msg_id)}:{int(dst_chat_id)}"

# --- finance_forward:0093 · from 04_messages_features.py:6120 · public _v260_forward_finance_operation_key ---
def _v260_forward_finance_operation_key(source_chat_id: int, source_msg_id: int, dst_chat_id: int) -> str:
    return f"fwd-fin:{int(source_chat_id)}:{int(source_msg_id)}:{int(dst_chat_id)}"

# --- finance_forward:0094 · from 04_messages_features.py:6123 · public _v260_forward_finance_op_get ---
def _v260_forward_finance_op_get(source_chat_id: int, source_msg_id: int, dst_chat_id: int) -> dict:
    try:
        return SQLITE.get_meta('forward_finance_ops_v260', _v260_forward_finance_op_key(source_chat_id, source_msg_id, dst_chat_id), {}) or {}
    except Exception:
        return {}

# --- finance_forward:0095 · from 04_messages_features.py:6129 · public _v260_forward_finance_op_mark ---
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

# --- finance_forward:0096 · from 04_messages_features.py:6145 · public _v260_find_forward_finance_record ---
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

# --- finance_forward:0097 · from 04_messages_features.py:6178 · public _v260_bind_forward_finance_record ---
def _legacy_s0097_v260_bind_forward_finance_record(rec: dict, source_msg, dst_chat_id: int, dst_msg_id: int) -> dict:
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

# --- finance_forward:0098 · from 04_messages_features.py:6202 · public _v260_make_forward_shadow ---
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

# --- finance_forward:0099 · from 04_messages_features.py:6218 · public _v260_finance_forward_repair ---
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

# --- finance_forward:0100 · from 04_messages_features.py:6244 · public _v260_schedule_finance_forward_repair ---
def _v260_schedule_finance_forward_repair(source_chat_id: int, source_msg_id: int, dst_chat_id: int, dst_msg_id: int, text: str, owner: int=0, source_date=None, attempt: int=0):
    _v260_forward_finance_op_mark(source_chat_id, source_msg_id, dst_chat_id, 'partial_finance_missing', dst_msg_id=int(dst_msg_id), text=str(text or '')[:4000], owner=int(owner or 0), source_date=source_date)
    try:
        DELAYED_SCHEDULER.schedule(f'finfwd-v260:{source_chat_id}:{source_msg_id}:{dst_chat_id}', 0.6, _v260_finance_forward_repair, source_chat_id, source_msg_id, dst_chat_id, dst_msg_id, text, owner, source_date, attempt)
        return True
    except Exception as exc:
        log_error(f'[FWD FIN V260] repair schedule: {exc}')
        return False

# --- finance_forward:0101 · from 04_messages_features.py:6253 · public recover_partial_finance_forwards_v260 ---
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

# --- finance_forward:0102 · from 04_messages_features.py:6352 · public _cleanup_forward_storage_for_chat ---
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

# --- finance_forward:0103 · from 04_messages_features.py:6716 · public _note_forward_target_migrated ---
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

# --- finance_forward:0104 · from 04_messages_features.py:6732 · public _notify_forward_failure ---
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

# --- finance_forward:0105 · from 04_messages_features.py:6806 · public _forward_single_to_target ---
def _legacy_s0105_forward_single_to_target(source_chat_id: int, msg, dst_chat_id: int, finance_enabled: bool, _migration_retry: bool=False):
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

# --- finance_forward:0106 · from 04_messages_features.py:6983 · public _flush_media_group_forward ---
def _flush_media_group_forward(source_chat_id: int, media_group_id: str):
    if not FORWARD_TASK_POOL.submit(int(source_chat_id), _flush_media_group_forward_locked, source_chat_id, media_group_id):
        log_error(f'MEDIA GROUP FORWARD QUEUE FULL: {source_chat_id}')

# --- finance_forward:0107 · from 04_messages_features.py:6987 · public _flush_media_group_forward_locked ---
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

# --- finance_forward:0108 · from 04_messages_features.py:7085 · public _collect_media_group_for_forward ---
def _collect_media_group_for_forward(source_chat_id: int, msg):
    cache_key = (int(source_chat_id), str(msg.media_group_id))
    bucket = _media_group_cache.setdefault(cache_key, [])
    if not any((m.message_id == msg.message_id for m in bucket)):
        bucket.append(msg)
    scheduler_key = f'media-group:{int(source_chat_id)}:{str(msg.media_group_id)}'
    DELAYED_SCHEDULER.cancel(scheduler_key)
    deadline = DELAYED_SCHEDULER.schedule(scheduler_key, 0.8, _flush_media_group_forward, source_chat_id, msg.media_group_id)
    _media_group_timers[cache_key] = deadline

# --- finance_forward:0109 · from 04_messages_features.py:7097 · public _fin_forward_batch_id ---
def _fin_forward_batch_id(source_chat_id: int, source_msg_id: int) -> str:
    return f'{int(source_chat_id)}:{int(source_msg_id)}'

# --- finance_forward:0110 · from 04_messages_features.py:7100 · public _v177_legacy_0157_fin_forward_batch_finish_target ---
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

# --- finance_forward:0111 · from 04_messages_features.py:7138 · public _fin_forward_target_job ---
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

# --- finance_forward:0112 · from 04_messages_features.py:7150 · public _start_financial_forward_batch ---
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

# --- finance_forward:0113 · from 04_messages_features.py:7166 · public _forward_targets_stage ---
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

# --- finance_forward:0114 · from 04_messages_features.py:7177 · public _forward_normal_stage ---
def _forward_normal_stage(source_chat_id: int, msg, targets: list) -> None:
    _forward_targets_stage(source_chat_id, msg, targets, final_stage=True)

# --- finance_forward:0115 · from 04_messages_features.py:7180 · public _forward_financial_stage ---
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

# --- finance_forward:0116 · from 04_messages_features.py:7194 · public schedule_financial_forward_pipeline ---
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

# --- finance_forward:0117 · from 04_messages_features.py:7225 · public _canon_forward_any_message__001 ---
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

# --- finance_forward:0118 · from 05_finance_ui.py:2039 · public build_forward_root_menu ---
def build_forward_root_menu(day_key: str):
    """Корневое меню пересылки: старый режим или новый визуальный режим пары A/B."""
    if forward_menu_new_style_enabled():
        return build_forward_new_menu(day_key)
    return build_forward_source_menu(day_key)

# --- finance_forward:0119 · from 05_finance_ui.py:2045 · public _v177_legacy_0180_collect_forward_picker_items ---
def _v177_legacy_0180_collect_forward_picker_items(include_owner: bool=True, include_removed: bool=False):
    known = collect_forward_menu_chats()
    items = []
    owner_item = None
    for cid, ch in sorted(known.items(), key=lambda x: (x[1].get('title') or '').lower()):
        try:
            int_cid = int(cid)
        except Exception:
            continue
        title = ch.get('title') or f'Чат {cid}'
        if OWNER_ID and str(int_cid) == str(OWNER_ID):
            owner_item = (int_cid, title)
        else:
            if not include_removed and is_chat_bot_removed(int_cid):
                continue
            items.append((int_cid, title))
    if include_owner and OWNER_ID:
        try:
            owner_id = int(OWNER_ID)
            if owner_item is None:
                owner_item = (owner_id, get_chat_display_name(owner_id))
        except Exception:
            owner_item = None
    return (items, owner_item)

# --- finance_forward:0120 · from 05_finance_ui.py:2247 · public _v177_legacy_0185_build_forward_source_menu ---
def _v177_legacy_0185_build_forward_source_menu(day_key: str | None=None):
    if forward_menu_new_style_enabled():
        return build_forward_new_menu(day_key)
    kb = types.InlineKeyboardMarkup(row_width=3)
    if not OWNER_ID:
        return kb
    items, owner_item = _collect_forward_picker_items(include_owner=True)
    buttons = [IB(chat_button_title(cid, title), callback_data=f'fw_src:{cid}') for cid, title in items]
    add_buttons_in_rows(kb, buttons, 2)
    if owner_item:
        kb.row(IB(chat_button_title(owner_item[0], owner_item[1]), callback_data=f'fw_src:{owner_item[0]}'))
    kb.row(IB('ℹ️ Описание чатов', callback_data='chat_desc_menu:forward'))
    kb.row(IB('📡 Проверить чаты', callback_data='fw_probe_all'), IB('🗑 Удалённые', callback_data='fw_removed_list'))
    if day_key:
        kb.row(IB('🔙 Назад', callback_data=f'd:{day_key}:back_main'))
    else:
        kb.row(IB('🔙 Назад', callback_data='fw_back_root'))
    return kb

# --- finance_forward:0121 · from 05_finance_ui.py:2270 · public _v177_legacy_0186_build_forward_target_menu ---
def _v177_legacy_0186_build_forward_target_menu(src_id: int):
    kb = types.InlineKeyboardMarkup()
    if not OWNER_ID:
        return kb
    items, owner_item = _collect_forward_picker_items(include_owner=True)
    buttons = []
    for int_cid, title in items:
        if int_cid == src_id:
            continue
        buttons.append(IB(chat_button_title(int_cid, title), callback_data=f'fw_tgt:{src_id}:{int_cid}'))
    add_buttons_in_rows(kb, buttons, 2)
    if owner_item and owner_item[0] != src_id:
        kb.row(IB(chat_button_title(owner_item[0], owner_item[1]), callback_data=f'fw_tgt:{src_id}:{owner_item[0]}'))
    kb.row(IB('🔙 Назад', callback_data='fw_back_src'))
    return kb

# --- finance_forward:0122 · from 05_finance_ui.py:2290 · public _forward_pair_key ---
def _forward_pair_key(A: int, B: int) -> str:
    return f'{int(A)}:{int(B)}'

# --- finance_forward:0123 · from 05_finance_ui.py:2293 · public _forward_pair_undirected_key ---
def _forward_pair_undirected_key(A: int, B: int) -> tuple[int, int]:
    A = int(A)
    B = int(B)
    return (A, B) if A <= B else (B, A)

# --- finance_forward:0124 · from 05_finance_ui.py:2298 · public _v177_legacy_0187_remember_forward_pair ---
def _v177_legacy_0187_remember_forward_pair(A: int, B: int):
    """Сохраняет порядок создания пар для нового В22. Старую логику пересылки не трогает."""
    try:
        A, B = (int(A), int(B))
        if A == B:
            return
        key = _forward_pair_key(A, B)
        rev = _forward_pair_key(B, A)
        order = data.setdefault('forward_pair_order', [])
        if not isinstance(order, list):
            order = []
            data['forward_pair_order'] = order
        if key not in order and rev not in order:
            order.append(key)
            save_data(data)
    except Exception as e:
        log_error(f'_remember_forward_pair({A},{B}): {e}')

# --- finance_forward:0125 · from 05_finance_ui.py:2320 · public _v177_legacy_0188_forget_forward_pair_if_empty ---
def _v177_legacy_0188_forget_forward_pair_if_empty(A: int, B: int):
    """Убирает пару из порядка, только если уже нет ни пересылки, ни 💰 финучёта в обе стороны."""
    try:
        A, B = (int(A), int(B))
        arrow, fin, ab_on, ba_on, ab_fin, ba_fin = _forward_pair_icons(A, B)
        if ab_on or ba_on or ab_fin or ba_fin:
            return
        key = _forward_pair_key(A, B)
        rev = _forward_pair_key(B, A)
        order = data.setdefault('forward_pair_order', [])
        if isinstance(order, list) and (key in order or rev in order):
            data['forward_pair_order'] = [x for x in order if x not in {key, rev}]
            save_data(data)
    except Exception as e:
        log_error(f'_forget_forward_pair_if_empty({A},{B}): {e}')

# --- finance_forward:0126 · from 05_finance_ui.py:2340 · public _forward_pair_sort_key ---
def _forward_pair_sort_key(pair):
    try:
        order = data.get('forward_pair_order', []) or []
        key = _forward_pair_key(pair[0], pair[1])
        rev = _forward_pair_key(pair[1], pair[0])
        if key in order:
            return (0, order.index(key))
        if rev in order:
            return (0, order.index(rev))
        a, b = pair
        return (1, get_chat_display_name(int(a)).lower(), get_chat_display_name(int(b)).lower(), int(a), int(b))
    except Exception:
        return (9, str(pair))

# --- finance_forward:0127 · from 05_finance_ui.py:2354 · public _sorted_forward_pair ---
def _sorted_forward_pair(a: int, b: int):
    """Старый helper оставлен для совместимости. Новый В22 порядок выбора не сортирует."""
    a = int(a)
    b = int(b)
    ka = (get_chat_display_name(a).lower(), a)
    kb = (get_chat_display_name(b).lower(), b)
    return (a, b) if ka <= kb else (b, a)

# --- finance_forward:0128 · from 05_finance_ui.py:2362 · public _v177_legacy_0189_collect_forward_pairs_for_menu ---
def _v177_legacy_0189_collect_forward_pairs_for_menu() -> list[tuple[int, int]]:
    """Все пары, где есть пересылка или 💰 финучёт пересылки. Порядок пары берём из создания/первого обнаружения."""
    relation_pairs = []
    seen = set()
    fr = data.get('forward_rules', {}) or {}
    ff = data.get('forward_finance', {}) or {}

    def _add_pair(a, b):
        try:
            a = int(a)
            b = int(b)
        except Exception:
            return
        if a == b:
            return
        uk = _forward_pair_undirected_key(a, b)
        if uk in seen:
            return
        seen.add(uk)
        relation_pairs.append((a, b))
    order = data.get('forward_pair_order', []) or []
    if isinstance(order, list):
        for key in order:
            try:
                a_s, b_s = str(key).split(':', 1)
                a, b = (int(a_s), int(b_s))
            except Exception:
                continue
            arrow, fin, ab_on, ba_on, ab_fin, ba_fin = _forward_pair_icons(a, b)
            if ab_on or ba_on or ab_fin or ba_fin:
                _add_pair(a, b)
    for src, dsts in fr.items():
        for dst in (dsts or {}).keys():
            _add_pair(src, dst)
    for src, dsts in ff.items():
        for dst, enabled in (dsts or {}).items():
            if enabled:
                _add_pair(src, dst)
    try:
        order = data.setdefault('forward_pair_order', [])
        if not isinstance(order, list):
            order = []
            data['forward_pair_order'] = order
        changed = False
        for A, B in relation_pairs:
            key = _forward_pair_key(A, B)
            rev = _forward_pair_key(B, A)
            if key not in order and rev not in order:
                order.append(key)
                changed = True
        if changed:
            save_data(data)
    except Exception:
        pass
    return sorted(relation_pairs, key=_forward_pair_sort_key)

# --- finance_forward:0129 · from 05_finance_ui.py:2422 · public _forward_pair_icons ---
def _forward_pair_icons(A: int, B: int):
    fr = data.get('forward_rules', {}) or {}
    ff = data.get('forward_finance', {}) or {}
    ab_on = str(B) in (fr.get(str(A), {}) or {})
    ba_on = str(A) in (fr.get(str(B), {}) or {})
    ab_fin = bool((ff.get(str(A), {}) or {}).get(str(B), False))
    ba_fin = bool((ff.get(str(B), {}) or {}).get(str(A), False))
    return (_forward_arrow_icon(ab_on, ba_on), _forward_fin_icon(ab_fin, ba_fin), ab_on, ba_on, ab_fin, ba_fin)

# --- finance_forward:0130 · from 05_finance_ui.py:2431 · public _forward_new_pair_buttons ---
def _forward_new_pair_buttons(A: int, B: int):
    """Две кнопки пары сверху в новом В22.

    По уточнённому ТЗ:
    • кнопка Чата A сверху остаётся выбором этого чата как нового Чата A;
    • кнопка Чата B сверху открывает настройки именно этой пары и помечается 🛠️ перед именем;
    • ниже разделителя Чаты A из готовых пар не дублируются, чтобы список не захламлялся.
    """
    arrow, fin, *_ = _forward_pair_icons(A, B)
    return (IB(f'{chat_button_title(A)} ({arrow})', callback_data=f'fw_new_src:{A}'), IB(f'({fin}) 🛠️ {chat_button_title(B)}', callback_data=f'fw_new_pair:{A}:{B}'))

# --- finance_forward:0131 · from 05_finance_ui.py:2442 · public _forward_new_toggle_label ---
def _forward_new_toggle_label(enabled: bool, icon: str) -> str:
    return ('✅' if enabled else '⬜') + icon

# --- finance_forward:0132 · from 05_finance_ui.py:2445 · public _visible_forward_items_for_new_menu ---
def _visible_forward_items_for_new_menu(include_owner: bool=True):
    items, owner_item = _collect_forward_picker_items(include_owner=include_owner)
    all_items = list(items)
    if owner_item:
        all_items.append(owner_item)
    visible = []
    for cid, title in all_items:
        try:
            if is_chat_bot_removed(int(cid)):
                continue
        except Exception:
            pass
        visible.append((int(cid), title))
    return visible

# --- finance_forward:0133 · from 05_finance_ui.py:2460 · public build_forward_new_text ---
def build_forward_new_text(A: int | None=None, B: int | None=None) -> str:
    """В22 новый режим: пары сверху, выбор A/B и настройка шести кнопок."""
    lines = ['🔁 Пересылка / В22', 'Режим: по-новому', '']
    if A and B:
        arrow, fin, *_ = _forward_pair_icons(A, B)
        lines.append(f'Чат А: {get_chat_display_name(A)} ({arrow})')
        lines.append(f'Чат Б: ({fin}) {get_chat_display_name(B)}')
        lines.append('Ниже выбери направление пересылки и 💰 финучёт.')
    elif A:
        lines.append(f'Чат А выбран: {get_chat_display_name(A)}')
        lines.append('Теперь выбери Чат Б. Остальные чаты остаются ниже по 2 кнопки в ряд.')
    else:
        lines.append('Сверху пары со связями. Ниже — все доступные чаты. Любой чат можно снова выбрать как Чат А.')
    return '\n'.join(lines)

# --- finance_forward:0134 · from 05_finance_ui.py:2475 · public _v177_legacy_0193_build_forward_new_menu ---
def _v177_legacy_0193_build_forward_new_menu(day_key: str | None=None, A: int | None=None, B: int | None=None):
    """
    Новый В22 по уточнённому ТЗ:
    • старт: пары сверху по 2 кнопки (A слева, B справа), потом пустой разделитель, потом свободные чаты по 2 кнопки;
    • выбран A: кнопка Чат А сверху, остальные чаты остаются ниже по 2 кнопки;
    • выбран B: сверху Чат А / Чат Б, ниже 6 кнопок режимов, ниже кнопка возврата к выбору чатов.
    """
    kb = types.InlineKeyboardMarkup(row_width=2)
    if not OWNER_ID:
        return kb
    visible_items = _visible_forward_items_for_new_menu(include_owner=True)
    pair_rows = collect_forward_pairs_for_menu()
    if A and B:
        A, B = (int(A), int(B))
        arrow, fin, ab_on, ba_on, ab_fin, ba_fin = _forward_pair_icons(A, B)
        kb.row(IB(f'Чат А: {chat_button_title(A)}', callback_data=f'fw_new_pair:{A}:{B}'), IB(f'Чат Б: {chat_button_title(B)}', callback_data=f'fw_new_pair:{A}:{B}'))
        kb.row(IB(_forward_new_toggle_label(ba_on, '⏪️'), callback_data=f'fw_new_mode:{A}:{B}:from'), IB(_forward_new_toggle_label(ab_on, '⏩️'), callback_data=f'fw_new_mode:{A}:{B}:to'), IB(_forward_new_toggle_label(ab_on and ba_on, '🔄'), callback_data=f'fw_new_mode:{A}:{B}:two'), IB(_forward_new_toggle_label(ba_fin, '◀️'), callback_data=f'fw_new_fin:{A}:{B}:ba'), IB(_forward_new_toggle_label(ab_fin, '▶️'), callback_data=f'fw_new_fin:{A}:{B}:ab'), IB('❌', callback_data=f'fw_new_clear:{A}:{B}'))
        kb.row(IB('🔙 Назад в окно выбора чатов', callback_data='fw_new_back_src'))
        return kb
    if A:
        A = int(A)
        kb.row(IB(f'Чат А: {chat_button_title(A)}', callback_data=f'fw_new_src:{A}'))
        buttons = []
        for cid, title in visible_items:
            if int(cid) == int(A):
                continue
            buttons.append(IB(f'Чат Б: {chat_button_title(cid, title)}', callback_data=f'fw_new_tgt:{A}:{int(cid)}'))
        if buttons:
            add_buttons_in_rows(kb, buttons, 2)
        else:
            kb.row(IB('Нет чатов для выбора Чата Б', callback_data='none'))
        kb.row(IB('🔙 Назад в окно выбора чатов', callback_data='fw_new_back_src'))
        return kb
    shown_pairs = 0
    top_pair_a_ids = set()
    for A0, B0 in pair_rows:
        try:
            if is_chat_bot_removed(A0) or is_chat_bot_removed(B0):
                continue
        except Exception:
            pass
        top_pair_a_ids.add(int(A0))
        left_btn, right_btn = _forward_new_pair_buttons(A0, B0)
        kb.row(left_btn, right_btn)
        shown_pairs += 1
    chat_buttons = []
    for cid, title in visible_items:
        if int(cid) in top_pair_a_ids:
            continue
        chat_buttons.append(IB(chat_button_title(cid, title), callback_data=f'fw_new_src:{cid}'))
    if shown_pairs and chat_buttons:
        kb.row(IB('⠀', callback_data='none'))
    if chat_buttons:
        add_buttons_in_rows(kb, chat_buttons, 2)
    elif not shown_pairs:
        kb.row(IB('Нет доступных чатов', callback_data='none'))
    kb.row(IB('ℹ️ Описание чатов', callback_data='chat_desc_menu:forward'))
    kb.row(IB('📡 Проверить чаты', callback_data='fw_probe_all'), IB('🗑 Удалённые', callback_data='fw_removed_list'))
    if day_key:
        kb.row(IB('🔙 Назад', callback_data=f'd:{day_key}:back_main'))
    else:
        kb.row(IB('🔙 Назад', callback_data='fw_back_root'))
    return kb

# --- finance_forward:0135 · from 05_finance_ui.py:2543 · public _v177_legacy_0194_build_forward_menu_text_for_current_mode ---
def _v177_legacy_0194_build_forward_menu_text_for_current_mode(title: str | None=None, A: int | None=None, B: int | None=None) -> str:
    if forward_menu_new_style_enabled():
        return build_forward_new_text(A, B)
    return build_forward_status_text(title or 'Пересылка:\nВыберите чат A:')

# --- finance_forward:0136 · from 05_finance_ui.py:2552 · public _v177_legacy_0195_build_forward_menu_keyboard_for_current_mode ---
def _v177_legacy_0195_build_forward_menu_keyboard_for_current_mode(day_key: str | None=None, A: int | None=None, B: int | None=None):
    if forward_menu_new_style_enabled():
        return build_forward_new_menu(day_key, A, B)
    if A and B:
        return build_forward_mode_menu(A, B)
    if A:
        return build_forward_target_menu(A)
    return build_forward_source_menu(day_key)

# --- finance_forward:0137 · from 05_finance_ui.py:3837 · public build_forward_mode_menu ---
def build_forward_mode_menu(A: int, B: int):
    """
    Меню выбора режима пересылки между чатами A и B.
    """
    kb = types.InlineKeyboardMarkup()
    name_a = chat_button_title(A)
    name_b = chat_button_title(B)
    fr = data.get('forward_rules', {}) or {}
    ab_link = str(B) in fr.get(str(A), {})
    ba_link = str(A) in fr.get(str(B), {})
    two_on = ab_link and ba_link
    ab_state = '✅ ВКЛ' if ab_link else '⬜ ВЫКЛ'
    ba_state = '✅ ВКЛ' if ba_link else '⬜ ВЫКЛ'
    two_state = '✅ ВКЛ' if two_on else '⬜ ВЫКЛ'
    ab_fin = '✅ ВКЛ' if get_forward_finance(A, B) else '⬜ ВЫКЛ'
    ba_fin = '✅ ВКЛ' if get_forward_finance(B, A) else '⬜ ВЫКЛ'
    kb.row(IB(f'➡️ {ab_state} {name_a} → {name_b}', callback_data=f'fw_mode:{A}:{B}:to'))
    kb.row(IB(f'⬅️ {ba_state} {name_b} → {name_a}', callback_data=f'fw_mode:{A}:{B}:from'))
    kb.row(IB(f'↔️ {two_state} {name_a} ⇄ {name_b}', callback_data=f'fw_mode:{A}:{B}:two'))
    kb.row(IB(f'💰 {ab_fin} Учёт {name_a} → {name_b}', callback_data=f'fw_finpair:{A}:{B}:ab'))
    kb.row(IB(f'💰 {ba_fin} Учёт {name_b} → {name_a}', callback_data=f'fw_finpair:{A}:{B}:ba'))
    kb.row(IB('❌ Удалить все связи A-B', callback_data=f'fw_mode:{A}:{B}:del'))
    kb.row(IB('🔙 Назад', callback_data=f'fw_back_tgt:{A}'))
    return kb

# --- finance_forward:0138 · from 06_commands_callbacks.py:4 · public _forward_probe_all_background ---
def _forward_probe_all_background(owner_chat_id: int, message_id: int):
    try:
        ok, bad = probe_all_known_chats()
        owner_store = get_chat_store(int(OWNER_ID))
        owner_day_key = owner_store.get('current_view_day', today_key())
        summary = (data.get('_global_settings', {}) or {}).get('last_chat_probe_summary_v197') or {}
        checked = int(summary.get('checked') or ok + bad)
        changed = int(summary.get('changed') or 0)
        renamed = int(summary.get('renamed') or 0)
        errors = int(summary.get('errors') or 0)
        text = build_forward_status_text(f'📡 Полная проверка чатов завершена.\nПроверено: {checked} · доступно: {ok} · нет доступа: {bad} · ошибок API: {errors}\nОбновлено карточек: {changed} · изменено имён: {renamed}\n\nНазвания, username, тип и доступные Telegram-параметры синхронизированы и сохранены.\n\nПересылка:\nВыберите чат A:')
        fast_ui_edit_message_text(int(owner_chat_id), int(message_id), text, reply_markup=build_forward_source_menu(owner_day_key), purpose='forward_probe_all_done')
    except Exception as exc:
        log_error(f'forward_probe_all_background: {exc}')
        try:
            send_owner_technical_alert('❌ Проверка чатов завершилась с ошибкой. Смотрите журнал.', 20, source_chat_id=int(owner_chat_id))
        except Exception:
            pass

# --- finance_forward:0139 · from 06_commands_callbacks.py:23 · public _forward_probe_one_background ---
def _forward_probe_one_background(owner_chat_id: int, message_id: int, target_chat_id: int):
    try:
        ok = probe_bot_in_chat(int(target_chat_id))
        status = '✅ бот снова доступен' if ok else '➖ бот удалён/нет доступа'
        owner_store = get_chat_store(int(OWNER_ID))
        owner_day_key = owner_store.get('current_view_day', today_key())
        fast_ui_edit_message_text(int(owner_chat_id), int(message_id), build_forward_status_text(f'🗑 Удалённые чаты\n{get_chat_display_name(int(target_chat_id))}: {status}'), reply_markup=build_removed_chats_menu(owner_day_key), purpose='forward_probe_one_done')
    except Exception as exc:
        log_error(f'forward_probe_one_background({target_chat_id}): {exc}')

# --- finance_forward:0140 · from 06_commands_callbacks.py:5198 · public cleanup_forward_links ---
def cleanup_forward_links(chat_id: int):
    """
    Удаляет все связи пересылки для чата из памяти и из сохранённого индекса.
    """
    _cleanup_forward_storage_for_chat(chat_id)

# --- finance_forward:0141 · from 07_state_web.py:408 · public _canon_persist_forward_finance_delivery_now__001 ---
def _canon_persist_forward_finance_delivery_now__001(src_chat_id: int, src_msg_id: int, dst_chat_id: int, dst_msg_id: int, rec: dict | None=None):
    batch_id = _fin_forward_batch_id(int(src_chat_id), int(src_msg_id)) if '_fin_forward_batch_id' in globals() else ''
    with _FIN_FORWARD_BATCH_LOCK:
        in_batch = batch_id in _FIN_FORWARD_BATCHES
    if not in_batch or not callable(_V146_ORIG_PERSIST_FORWARD_FINANCE):
        return _V146_ORIG_PERSIST_FORWARD_FINANCE(src_chat_id, src_msg_id, dst_chat_id, dst_msg_id, rec) if callable(_V146_ORIG_PERSIST_FORWARD_FINANCE) else False
    try:
        if isinstance(rec, dict):
            tags = {'forwarded_by_bot': True, 'forward_source_chat_id': int(src_chat_id), 'forward_source_msg_id': int(src_msg_id), 'forward_dst_chat_id': int(dst_chat_id), 'forward_dst_msg_id': int(dst_msg_id)}
            rec.update(tags)
            store = get_chat_store(int(dst_chat_id))
            rid = rec.get('id')
            for arr in (store.get('daily_records', {}) or {}).values():
                for rr in arr or []:
                    if isinstance(rr, dict) and rr.get('id') == rid:
                        rr.update(tags)
        _persist_forward_index_in_data(data)
        save_data(data, chat_ids=[int(dst_chat_id)])
        schedule_quick_backup(int(dst_chat_id), 0.5)
        with _FIN_FORWARD_BATCH_LOCK:
            row = _FIN_FORWARD_BATCHES.get(batch_id)
            if isinstance(row, dict):
                row.setdefault('durable_chats', set()).add(int(dst_chat_id))
        bot_journal('forward_finance_local_committed', int(dst_chat_id), f'batch={batch_id} src={src_chat_id}:{src_msg_id} dst_msg={dst_msg_id}; combined_delta=1')
        return True
    except Exception as exc:
        log_error(f'[V146 FWD FINANCE LOCAL ERROR] {src_chat_id}:{src_msg_id}->{dst_chat_id}:{dst_msg_id}: {exc}')
        return False

# --- finance_forward:0142 · from 07_state_web.py:437 · public _v146_finish_forward_follow ---
def _v146_finish_forward_follow(follow: dict, durable_ok: bool, durable_error: str=''):
    source_chat_id = int(follow.get('source_chat_id'))
    source_msg_id = int(follow.get('source_msg_id'))
    normal_targets = list(follow.get('normal_targets') or [])
    if durable_ok:
        if normal_targets:
            if not FORWARD_TASK_POOL.submit(source_chat_id, _forward_normal_stage, source_chat_id, follow.get('msg'), normal_targets):
                _forward_normal_stage(source_chat_id, follow.get('msg'), normal_targets)
        elif source_msg_id:
            _forward_outcome_update(source_chat_id, source_msg_id, state='completed')
    else:
        _forward_outcome_update(source_chat_id, source_msg_id, state='durable_pending', error=str(durable_error or 'delta upload failed')[:300])

        def _retry():
            ok = False
            try:
                ok = bool(durable_run_pending_delta_now_v234())
            except Exception as exc:
                log_error(f'V146 FIN BATCH DELTA RETRY {source_chat_id}:{source_msg_id}: {exc}')
            if ok:
                _v146_finish_forward_follow(follow, True)
            else:
                DELAYED_SCHEDULER.schedule(f'v146-fin-batch-delta:{source_chat_id}:{source_msg_id}', 5.0, _retry)
        DELAYED_SCHEDULER.schedule(f'v146-fin-batch-delta:{source_chat_id}:{source_msg_id}', 5.0, _retry)

# --- finance_forward:0143 · from 07_state_web.py:462 · public _canon_fin_forward_batch_finish_target__001 ---
def _canon_fin_forward_batch_finish_target__001(batch_id: str, dst_chat_id: int, ok: bool, elapsed: float, error: str='') -> None:
    follow = None
    with _FIN_FORWARD_BATCH_LOCK:
        row = _FIN_FORWARD_BATCHES.get(str(batch_id))
        if not isinstance(row, dict):
            return
        row.setdefault('targets', {})[str(int(dst_chat_id))] = {'ok': bool(ok), 'elapsed': round(float(elapsed), 3), 'error': str(error or '')[:300]}
        row['remaining'] = max(0, int(row.get('remaining', 0)) - 1)
        if row['remaining'] == 0:
            follow = dict(row)
            if isinstance(row.get('durable_chats'), set):
                follow['durable_chats'] = sorted(row.get('durable_chats'))
            _FIN_FORWARD_BATCHES.pop(str(batch_id), None)
    try:
        bot_journal('finance_forward_target_done', (follow or {}).get('source_chat_id'), f"batch={batch_id} dst={int(dst_chat_id)} ok={bool(ok)} elapsed={elapsed:.3f}s error={str(error or '')[:180]}", 'INFO' if ok else 'ERROR')
    except Exception:
        pass
    if not follow:
        return
    started = float(follow.get('started_mono') or time.monotonic())
    durable_started = time.monotonic()
    durable_ok = False
    durable_error = ''
    try:
        durable_ok = bool(durable_run_pending_delta_now_v234())
        if not durable_ok:
            durable_error = 'combined delta returned false'
    except Exception as exc:
        durable_error = str(exc)
        log_error(f'V146 FIN BATCH COMBINED DELTA {batch_id}: {exc}')
    _v146_finish_forward_follow(follow, durable_ok, durable_error)
    try:
        target_rows = follow.get('targets') or {}
        failed = sum((1 for x in target_rows.values() if not bool((x or {}).get('ok'))))
        bot_journal('finance_forward_batch_done', int(follow.get('source_chat_id')), f'batch={batch_id} targets={len(target_rows)} failed={failed} durable={int(durable_ok)} delta_elapsed={time.monotonic() - durable_started:.3f}s total_elapsed={time.monotonic() - started:.3f}s')
    except Exception:
        pass

# --- finance_forward:0144 · from 07_state_web.py:1224 · public _canon_collect_forward_menu_chats__001 ---
def _canon_collect_forward_menu_chats__001() -> dict:
    tid = tenant_current_id()
    result = {}
    resolver = globals().get('resolve_canonical_chat_id_v199')
    suspended = globals().get('is_forward_target_suspended_v199')
    for raw_cid in tenant_chat_ids(tid):
        try:
            cid = int(resolver(int(raw_cid))) if callable(resolver) else int(raw_cid)
            if callable(suspended) and suspended(cid):
                continue
            store = get_chat_store(cid)
            info = store.get('info') or {}
            result[str(cid)] = {'title': info.get('title') or get_chat_display_name(cid) or f'Чат {cid}', 'username': info.get('username'), 'type': info.get('type')}
        except Exception:
            continue
    return result

# --- finance_forward:0145 · from 07_state_web.py:1257 · public _canon_resolve_forward_targets__001 ---
def _canon_resolve_forward_targets__001(source_chat_id: int):
    resolver = globals().get('resolve_canonical_chat_id_v199')
    suspended = globals().get('is_forward_target_suspended_v199')
    src = int(resolver(int(source_chat_id))) if callable(resolver) else int(source_chat_id)
    rows = _V148_ORIG_RESOLVE_FORWARD_TARGETS(src) if callable(_V148_ORIG_RESOLVE_FORWARD_TARGETS) else []
    out = []
    seen = set()
    for dst, mode, fin in rows or []:
        dst = int(resolver(int(dst))) if callable(resolver) else int(dst)
        if dst in seen or (callable(suspended) and suspended(dst)):
            continue
        if tenant_same_space(src, dst):
            out.append((dst, mode, bool(fin)))
            seen.add(dst)
        else:
            try:
                bot_journal('tenant_cross_forward_blocked', src, f'dst={dst}')
            except Exception:
                pass
    return out

# --- finance_forward:0146 · from 07_state_web.py:1279 · public _v177_legacy_0142_add_forward_link ---
def _v177_legacy_0142_add_forward_link(src_chat_id: int, dst_chat_id: int, mode: str):
    if not tenant_same_space(int(src_chat_id), int(dst_chat_id)):
        raise PermissionError('Нельзя связать пересылкой чаты из разных пространств')
    return _V148_ORIG_ADD_FORWARD_LINK(int(src_chat_id), int(dst_chat_id), mode)

# --- finance_forward:0147 · from 07_state_web.py:1288 · public _canon_clear_forward_all__001 ---
def _canon_clear_forward_all__001():
    """v148: очищает связи только текущего пространства, а не чужие контуры."""
    allowed = {str(x) for x in tenant_chat_ids(tenant_current_id())}
    fr = data.setdefault('forward_rules', {})
    ff = data.setdefault('forward_finance', {})
    for src in list(fr.keys()):
        if str(src) in allowed:
            fr.pop(src, None)
            ff.pop(src, None)
            continue
        for dst in list((fr.get(src) or {}).keys()):
            if str(dst) in allowed:
                (fr.get(src) or {}).pop(dst, None)
                (ff.get(src) or {}).pop(dst, None)
    data['forward_pair_order'] = [key for key in data.get('forward_pair_order') or [] if not any((part in allowed for part in str(key).split(':', 1)))]
    persist_forward_rules_to_owner()
    save_data(data, full=True)

# --- finance_forward:0148 · from 07_state_web.py:1307 · public _v177_legacy_0190_collect_forward_pairs_for_menu ---
def _v177_legacy_0190_collect_forward_pairs_for_menu() -> list[tuple[int, int]]:
    rows = _V148_ORIG_COLLECT_FORWARD_PAIRS() if callable(_V148_ORIG_COLLECT_FORWARD_PAIRS) else []
    tid = tenant_current_id()
    allowed = set(tenant_chat_ids(tid))
    return [(int(a), int(b)) for a, b in rows if int(a) in allowed and int(b) in allowed]

# --- finance_forward:0149 · from 07_state_web.py:1325 · public _v177_legacy_0147_forward_copy_edit_mode ---
def _v177_legacy_0147_forward_copy_edit_mode(chat_id: int | None=None) -> str:
    mode = str(_tenant_settings_for_context(chat_id).get('forward_copy_edit_mode') or 'normal').lower()
    return mode if mode in FORWARD_COPY_EDIT_MODES and version_mode_feature('forward_copy_edit') else 'normal'

# --- finance_forward:0150 · from 07_state_web.py:1333 · public _v177_legacy_0149_set_forward_copy_edit_mode ---
def _v177_legacy_0149_set_forward_copy_edit_mode(chat_id: int, mode: str):
    mode = str(mode or 'normal').lower()
    if mode not in FORWARD_COPY_EDIT_MODES:
        mode = 'normal'
    _tenant_settings_for_context(chat_id)['forward_copy_edit_mode'] = mode
    save_data(data, root_only=True)
    return mode

# --- finance_forward:0151 · from 07_state_web.py:2060 · public _v177_legacy_0061_build_forward_status_lines ---
def _v177_legacy_0061_build_forward_status_lines() -> list[str]:
    lines = []
    fr = data.get('forward_rules', {}) or {}
    ff = data.get('forward_finance', {}) or {}
    allowed = set(tenant_chat_ids(tenant_current_id()))
    pairs = set()
    for src, dsts in fr.items():
        try:
            a = int(src)
        except Exception:
            continue
        if a not in allowed:
            continue
        for dst in (dsts or {}).keys():
            try:
                b = int(dst)
            except Exception:
                continue
            if b not in allowed:
                continue
            pairs.add(tuple(sorted((a, b))))
    for a, b in sorted(pairs, key=lambda p: (get_chat_display_name(p[0]).casefold(), get_chat_display_name(p[1]).casefold())):
        ab = str(b) in (fr.get(str(a), {}) or {})
        ba = str(a) in (fr.get(str(b), {}) or {})
        if not (ab or ba):
            continue
        ab_fin = bool((ff.get(str(a), {}) or {}).get(str(b), False))
        ba_fin = bool((ff.get(str(b), {}) or {}).get(str(a), False))
        lines.append(f'• {chat_button_title(a)} -({_forward_arrow_icon(ab, ba)})-({_forward_fin_icon(ab_fin, ba_fin)})-{chat_button_title(b)}')
    return lines or ['• Связи пересылки не настроены']

# --- finance_forward:0152 · from 07_state_web.py:2149 · public tenant_v148_enforce_forward_isolation ---
def tenant_v148_enforce_forward_isolation() -> int:
    removed = 0
    fr = data.setdefault('forward_rules', {})
    ff = data.setdefault('forward_finance', {})
    for src, dsts in list(fr.items()):
        try:
            src_id = int(src)
        except Exception:
            fr.pop(src, None)
            ff.pop(str(src), None)
            continue
        if not isinstance(dsts, dict):
            fr.pop(src, None)
            ff.pop(str(src_id), None)
            continue
        for dst in list(dsts.keys()):
            try:
                dst_id = int(dst)
            except Exception:
                dsts.pop(dst, None)
                (ff.get(str(src_id)) or {}).pop(str(dst), None)
                removed += 1
                continue
            if not tenant_same_space(src_id, dst_id):
                dsts.pop(dst, None)
                (ff.get(str(src_id)) or {}).pop(str(dst_id), None)
                removed += 1
        if not dsts:
            fr.pop(str(src), None)
            ff.pop(str(src_id), None)
    if removed:
        persist_forward_rules_to_owner()
        try:
            bot_journal('tenant_cross_links_removed', OWNER_ID, f'count={removed}', 'WARN')
        except Exception:
            pass
    return removed

# --- finance_forward:0153 · from 07_state_web.py:8678 · public _canon_schedule_forward_any_message__001 ---
def _canon_schedule_forward_any_message__001(chat_id: int, msg):
    cid = int(chat_id)
    uid = _v152_actor_id(msg)
    capability = 'forward.media_groups' if getattr(msg, 'media_group_id', None) else 'forward.messages'
    if not _v152_actor_is_platform_owner(uid) and (not v152_chat_permission_allowed(cid, capability)):
        try:
            bot_journal('chat_permission_forward_blocked', cid, f'user={uid}; capability={capability}', 'WARN')
        except Exception:
            pass
        return None
    return _V152_ORIG_SCHEDULE_FORWARD(cid, msg) if callable(_V152_ORIG_SCHEDULE_FORWARD) else None

# --- finance_forward:0154 · from 08_reliability_tasks.py:5700 · public _v163_forward_scope_ids ---
def _v163_forward_scope_ids() -> list[int]:
    ids = set()
    try:
        tid = str(tenant_current_id())
    except Exception:
        tid = 'platform'
    try:
        for cid in tenant_chat_ids(tid) or []:
            ids.add(int(cid))
    except Exception:
        pass
    try:
        for cid in (data.get('chats', {}) or {}).keys():
            ic = int(cid)
            if str(tenant_id_for_chat(ic, create=False)) == tid:
                ids.add(ic)
    except Exception:
        pass
    try:
        scope = owner_scope_id(current_state_chat_id())
        known = get_chat_store(int(scope)).get('known_chats') or {}
        for cid in known.keys():
            ic = int(cid)
            if str(tenant_id_for_chat(ic, create=False)) == tid:
                ids.add(ic)
    except Exception:
        pass
    try:
        for src, dsts in (data.get('forward_rules', {}) or {}).items():
            for cid in [src] + list((dsts or {}).keys()):
                ic = int(cid)
                if str(tenant_id_for_chat(ic, create=False)) == tid:
                    ids.add(ic)
    except Exception:
        pass
    try:
        root = int(owner_scope_id(current_state_chat_id()))
        if root:
            ids.add(root)
    except Exception:
        pass
    return sorted(ids, key=lambda cid: get_chat_display_name(cid).casefold())

# --- finance_forward:0155 · from 08_reliability_tasks.py:5743 · public _v177_legacy_0181_collect_forward_picker_items ---
def _v177_legacy_0181_collect_forward_picker_items(include_owner: bool=True, include_removed: bool=False):
    items = []
    owner_item = None
    try:
        root_id = int(owner_scope_id(current_state_chat_id()))
    except Exception:
        root_id = int(OWNER_ID or 0)
    for cid in _v163_forward_scope_ids():
        try:
            if not include_removed and is_chat_bot_removed(int(cid)):
                continue
        except Exception:
            pass
        title = get_chat_display_name(int(cid)) or f'Чат {cid}'
        if root_id and int(cid) == root_id:
            owner_item = (int(cid), title)
        else:
            items.append((int(cid), title))
    if include_owner and root_id and (owner_item is None):
        owner_item = (root_id, get_chat_display_name(root_id) or f'Чат {root_id}')
    if not include_owner:
        owner_item = None
    return (items, owner_item)

# --- finance_forward:0156 · from 08_reliability_tasks.py:6446 · public _v177_legacy_0143_add_forward_link ---
def _v177_legacy_0143_add_forward_link(src_chat_id: int, dst_chat_id: int, mode: str):
    src, dst = (int(src_chat_id), int(dst_chat_id))
    actor = 0
    try:
        actor = int(tenant_current_actor_user_id() or 0)
    except Exception:
        pass
    if not tenant_same_space(src, dst):
        if not tenant_is_platform_owner_user(actor):
            raise PermissionError('Можно связывать только свой 1-й круг и его 2-й круг')
        key = f'{min(src, dst)}:{max(src, dst)}'
        _v164_root().setdefault('global_forward_pairs', {})[key] = {'src': src, 'dst': dst, 'created_by': actor, 'created_at': _v164_now()}
        try:
            save_data(data, root_only=True)
        except Exception:
            pass
    base = globals().get('_V148_ORIG_ADD_FORWARD_LINK')
    if callable(base):
        return base(src, dst, mode)
    if callable(_V164_PREV_ADD_FORWARD_LINK):
        return _V164_PREV_ADD_FORWARD_LINK(src, dst, mode)
    raise RuntimeError('add_forward_link is unavailable')

# --- finance_forward:0157 · from 08_reliability_tasks.py:6763 · public _v177_legacy_0182_collect_forward_picker_items ---
def _v177_legacy_0182_collect_forward_picker_items(include_owner: bool=True, include_removed: bool=False):
    level = _v164_current_window_circle('forward', 1)
    items = []
    for cid in _v164_scoped_picker_ids('forward', level):
        try:
            if not include_removed and is_chat_bot_removed(int(cid)):
                continue
        except Exception:
            pass
        items.append((int(cid), get_chat_display_name(int(cid)) or f'Чат {cid}'))
    return (items, None)

# --- finance_forward:0158 · from 08_reliability_tasks.py:6779 · public _v177_legacy_0191_collect_forward_pairs_for_menu ---
def _v177_legacy_0191_collect_forward_pairs_for_menu() -> list[tuple[int, int]]:
    rows = _V164_PREV_COLLECT_FORWARD_PAIRS() if callable(_V164_PREV_COLLECT_FORWARD_PAIRS) else []
    allowed = set(_v164_scoped_picker_ids('forward'))
    out = []
    for pair in rows or []:
        try:
            a, b = (int(pair[0]), int(pair[1]))
        except Exception:
            continue
        if a in allowed:
            out.append((a, b))
    return out

# --- finance_forward:0159 · from 08_reliability_tasks.py:6807 · public _canon_build_forward_new_menu__001 ---
def _canon_build_forward_new_menu__001(day_key: str | None=None, A: int | None=None, B: int | None=None):
    level = _v164_current_window_circle('forward', circle_level_for_chat(A) if A else 1)
    kb = _V164_PREV_BUILD_FORWARD_NEW_MENU(day_key, A, B)
    if not B:
        _v164_insert_before_nav(kb, _v164_circle_switch_button('forward', level, int(A or 0)))
    return kb

# --- finance_forward:0160 · from 08_reliability_tasks.py:6814 · public _canon_build_forward_source_menu__001 ---
def _canon_build_forward_source_menu__001(day_key: str | None=None):
    if forward_menu_new_style_enabled():
        return build_forward_new_menu(day_key)
    level = _v164_current_window_circle('forward', 1)
    kb = _V164_PREV_BUILD_FORWARD_SOURCE_MENU(day_key)
    _v164_insert_before_nav(kb, _v164_circle_switch_button('forward', level))
    return kb

# --- finance_forward:0161 · from 08_reliability_tasks.py:6822 · public _canon_build_forward_target_menu__001 ---
def _canon_build_forward_target_menu__001(src_id: int):
    src = int(src_id)
    if circle_level_for_chat(src) in {1, 2}:
        key = _v164_window_key('forward')
        with _V164_WINDOW_VIEW_LOCK:
            if key not in _V164_WINDOW_VIEW:
                _V164_WINDOW_VIEW[key] = {'circle': circle_level_for_chat(src), 'at': _v164_time.time()}
    level = _v164_current_window_circle('forward', circle_level_for_chat(src))
    kb = _V164_PREV_BUILD_FORWARD_TARGET_MENU(src)
    _v164_insert_before_nav(kb, _v164_circle_switch_button('forward', level, src))
    return kb

# --- finance_forward:0162 · from 08_reliability_tasks.py:6834 · public _canon_build_forward_menu_text_for_current_mode__001 ---
def _canon_build_forward_menu_text_for_current_mode__001(title: str | None=None, A: int | None=None, B: int | None=None) -> str:
    level = _v164_current_window_circle('forward', circle_level_for_chat(A) if A else 1)
    prefix = '1️⃣ 1-й круг' if level == 1 else '2️⃣ 2-й круг'
    if forward_menu_new_style_enabled():
        body = build_forward_new_text(A, B)
    else:
        body = build_forward_status_text(title or 'Пересылка:\nВыберите чат A:')
    return f'{prefix}\n{body}'

# --- finance_forward:0163 · from 08_reliability_tasks.py:6843 · public _canon_build_forward_menu_keyboard_for_current_mode__001 ---
def _canon_build_forward_menu_keyboard_for_current_mode__001(day_key: str | None=None, A: int | None=None, B: int | None=None):
    if forward_menu_new_style_enabled():
        return build_forward_new_menu(day_key, A, B)
    if A and B:
        return build_forward_mode_menu(A, B)
    if A:
        return build_forward_target_menu(A)
    return build_forward_source_menu(day_key)

# --- finance_forward:0164 · from 08_reliability_tasks.py:7054 · public _canon_collect_forward_picker_items__001 ---
def _canon_collect_forward_picker_items__001(include_owner: bool=True, include_removed: bool=False):
    """v165: v163-compatible owner row + v164 circle-scoped ordinary chats."""
    level = _v164_current_window_circle('forward', 1)
    items = []
    owner_item = None
    for cid in _v164_scope_ids(level, current_state_chat_id()):
        try:
            icid = int(cid)
        except Exception:
            continue
        try:
            if not include_removed and is_chat_bot_removed(icid):
                continue
        except Exception:
            pass
        items.append((icid, get_chat_display_name(icid) or f'Чат {icid}'))
    if include_owner and int(level) == 1 and _v165_is_platform_owner_context():
        owner_item = _v165_owner_item(include_removed=include_removed)
    if owner_item:
        items = [(cid, title) for cid, title in items if int(cid) != int(owner_item[0])]
    items.sort(key=lambda row: (str(row[1]).casefold(), int(row[0])))
    return (items, owner_item)

# --- finance_forward:0165 · from 08_reliability_tasks.py:7077 · public _v177_legacy_0192_collect_forward_pairs_for_menu ---
def _v177_legacy_0192_collect_forward_pairs_for_menu() -> list[tuple[int, int]]:
    """Show historical owner pairs again on the 1st-circle page without mixing tenant storage."""
    try:
        rows = _V164_PREV_COLLECT_FORWARD_PAIRS() if callable(_V164_PREV_COLLECT_FORWARD_PAIRS) else []
    except Exception:
        rows = []
    level = _v164_current_window_circle('forward', 1)
    allowed = set((int(x) for x in _v164_scope_ids(level, current_state_chat_id()) or []))
    if int(level) == 1 and _v165_is_platform_owner_context():
        try:
            allowed.add(int(OWNER_ID))
        except Exception:
            pass
    out = []
    for pair in rows or []:
        try:
            a, b = (int(pair[0]), int(pair[1]))
        except Exception:
            continue
        if a in allowed:
            out.append((a, b))
    return out

# --- finance_forward:0166 · from 08_reliability_tasks.py:7204 · public _v166_forward_pair_from_callback ---
def _v166_forward_pair_from_callback(raw: str):
    raw = str(raw or '')
    prefixes = ('fw_new_mode:', 'fw_new_fin:', 'fw_new_clear:', 'fw_mode:', 'fw_finpair:', 'fw_clear:')
    if not raw.startswith(prefixes):
        return None
    nums = []
    for part in raw.split(':')[1:]:
        try:
            nums.append(int(part))
        except Exception:
            continue
        if len(nums) >= 2:
            break
    if len(nums) < 2:
        return None
    a, b = (nums[0], nums[1])
    return (a, b) if a <= b else (b, a)

# --- finance_forward:0167 · from 08_reliability_tasks.py:7465 · public _v166_raw_forward_pairs ---
def _v166_raw_forward_pairs():
    with data_lock:
        fr = {str(k): dict(v or {}) for k, v in (data.get('forward_rules', {}) or {}).items()}
        ff = {str(k): dict(v or {}) for k, v in (data.get('forward_finance', {}) or {}).items()}
        order = list(data.get('forward_pair_order', []) or [])
    pairs = []
    seen = set()

    def add(a, b):
        try:
            a, b = (int(a), int(b))
        except Exception:
            return
        if a == b:
            return
        key = _v166_pair_key(a, b)
        if key in seen:
            return
        ab = str(b) in (fr.get(str(a), {}) or {})
        ba = str(a) in (fr.get(str(b), {}) or {})
        af = bool((ff.get(str(a), {}) or {}).get(str(b), False))
        bf = bool((ff.get(str(b), {}) or {}).get(str(a), False))
        if not (ab or ba or af or bf):
            return
        seen.add(key)
        pairs.append((a, b))
    if isinstance(order, list):
        for raw in order:
            try:
                a_s, b_s = str(raw).split(':', 1)
                add(int(a_s), int(b_s))
            except Exception:
                continue
    for src, dsts in fr.items():
        for dst in (dsts or {}).keys():
            add(src, dst)
    for src, dsts in ff.items():
        for dst, enabled in (dsts or {}).items():
            if enabled:
                add(src, dst)
    return pairs

# --- finance_forward:0168 · from 08_reliability_tasks.py:7507 · public _v166_forward_allowed_ids ---
def _v166_forward_allowed_ids():
    level = _v164_current_window_circle('forward', 1)
    try:
        ctx = int(current_state_chat_id() or 0)
    except Exception:
        ctx = 0
    allowed = set((int(x) for x in _v164_scope_ids(level, ctx) or []))
    if int(level) == 1 and _v165_is_platform_owner_context():
        try:
            allowed.add(int(OWNER_ID))
        except Exception:
            pass
    return (int(level), allowed)

# --- finance_forward:0169 · from 08_reliability_tasks.py:7521 · public _canon_collect_forward_pairs_for_menu__001 ---
def _canon_collect_forward_pairs_for_menu__001() -> list[tuple[int, int]]:
    level, allowed = _v166_forward_allowed_ids()
    out = []
    for a, b in _v166_raw_forward_pairs():
        if a in allowed:
            out.append((a, b))
        elif b in allowed:
            out.append((b, a))
    try:
        bot_journal('v166_forward_pairs_menu', current_state_chat_id(), f'circle={level} raw={len(_v166_raw_forward_pairs())} shown={len(out)}')
    except Exception:
        pass
    return out

# --- finance_forward:0170 · from 08_reliability_tasks.py:7535 · public _canon_build_forward_status_lines__001 ---
def _canon_build_forward_status_lines__001() -> list[str]:
    lines = []
    for a, b in collect_forward_pairs_for_menu():
        try:
            arrow, fin, ab_on, ba_on, ab_fin, ba_fin = _forward_pair_icons(a, b)
            if ab_on or ba_on or ab_fin or ba_fin:
                lines.append(f'• {chat_button_title(a)} -({arrow})-({fin})-{chat_button_title(b)}')
        except Exception:
            continue
    return lines

# --- finance_forward:0171 · from 08_reliability_tasks.py:7546 · public _v166_schedule_forward_persist ---
def _v166_schedule_forward_persist(*chat_ids):
    with _V166_FORWARD_DIRTY_LOCK:
        for cid in chat_ids:
            try:
                _V166_FORWARD_DIRTY_CHATS.add(int(cid))
            except Exception:
                pass

    def _fire():

        def _persist():
            with _V166_FORWARD_DIRTY_LOCK:
                ids = sorted(_V166_FORWARD_DIRTY_CHATS)
                _V166_FORWARD_DIRTY_CHATS.clear()
            try:
                save_data(data, full=True)
            except Exception as exc:
                try:
                    log_error(f'v166 forward local persist: {exc}')
                except Exception:
                    pass
            try:
                path = _owner_data_file()
                if path:
                    payload = _load_json(path, {}) or {}
                    if not isinstance(payload, dict):
                        payload = {}
                    payload['forward_rules'] = data.get('forward_rules', {}) or {}
                    payload['forward_finance'] = data.get('forward_finance', {}) or {}
                    payload['forward_pair_order'] = data.get('forward_pair_order', []) or []
                    _save_json(path, payload)
            except Exception as exc:
                try:
                    log_error(f'v166 forward legacy persist: {exc}')
                except Exception:
                    pass
            try:
                if ids:
                    schedule_config_backup_for_chats(*ids, delay=0.3)
                else:
                    schedule_config_backup_for_chats(delay=0.3)
            except Exception:
                pass
        if not V166_CONFIG_IO_TASK_POOL.submit('forward-persist', _persist):
            try:
                log_error('V166 CONFIG IO QUEUE FULL: forward-persist')
            except Exception:
                pass
    try:
        V166_CONFIG_IO_SCHEDULER.cancel('v166-forward-persist')
        V166_CONFIG_IO_SCHEDULER.schedule('v166-forward-persist', 0.12, _fire)
    except Exception:
        _fire()

# --- finance_forward:0172 · from 08_reliability_tasks.py:7648 · public _canon_ensure_hidden_finance_for_forward_dst__001 ---
def _canon_ensure_hidden_finance_for_forward_dst__001(dst_chat_id: int):
    try:
        _v166_enable_hidden_finance_memory(int(dst_chat_id))
        bot_journal('forward_finance_auto_hidden', int(dst_chat_id), 'v166 fast: hidden finance enabled; durable config queued')
    except Exception as exc:
        log_error(f'v166 ensure_hidden_finance_for_forward_dst({dst_chat_id}): {exc}')

# --- finance_forward:0173 · from 08_reliability_tasks.py:7655 · public _canon_add_forward_link__001 ---
def _canon_add_forward_link__001(src_chat_id: int, dst_chat_id: int, mode: str):
    src, dst = (int(src_chat_id), int(dst_chat_id))
    _v166_authorize_pair(src, dst)
    with data_lock, _V166_FORWARD_STATE_LOCK:
        data.setdefault('forward_rules', {}).setdefault(str(src), {})[str(dst)] = str(mode)
    _v166_schedule_forward_persist(src, dst)

# --- finance_forward:0174 · from 08_reliability_tasks.py:7662 · public _canon_remove_forward_link__001 ---
def _canon_remove_forward_link__001(src_chat_id: int, dst_chat_id: int):
    src, dst = (int(src_chat_id), int(dst_chat_id))
    with data_lock, _V166_FORWARD_STATE_LOCK:
        fr = data.setdefault('forward_rules', {})
        ff = data.setdefault('forward_finance', {})
        (fr.get(str(src)) or {}).pop(str(dst), None)
        if str(src) in fr and (not fr.get(str(src))):
            fr.pop(str(src), None)
        (ff.get(str(src)) or {}).pop(str(dst), None)
        if str(src) in ff and (not ff.get(str(src))):
            ff.pop(str(src), None)
    _v166_cleanup_global_pair(src, dst)
    _v166_schedule_forward_persist(src, dst)

# --- finance_forward:0175 · from 08_reliability_tasks.py:7676 · public _canon_set_forward_finance__001 ---
def _canon_set_forward_finance__001(src_chat_id: int, dst_chat_id: int, enabled: bool):
    src, dst = (int(src_chat_id), int(dst_chat_id))
    _v166_authorize_pair(src, dst)
    with data_lock, _V166_FORWARD_STATE_LOCK:
        data.setdefault('forward_finance', {}).setdefault(str(src), {})[str(dst)] = bool(enabled)
    if enabled:
        ensure_hidden_finance_for_forward_dst(dst)
    _v166_schedule_forward_persist(src, dst)

# --- finance_forward:0176 · from 08_reliability_tasks.py:7685 · public _canon_remove_forward_finance__001 ---
def _canon_remove_forward_finance__001(src_chat_id: int, dst_chat_id: int):
    src, dst = (int(src_chat_id), int(dst_chat_id))
    with data_lock, _V166_FORWARD_STATE_LOCK:
        ff = data.setdefault('forward_finance', {})
        (ff.get(str(src)) or {}).pop(str(dst), None)
        if str(src) in ff and (not ff.get(str(src))):
            ff.pop(str(src), None)
    _v166_cleanup_global_pair(src, dst)
    _v166_schedule_forward_persist(src, dst)

# --- finance_forward:0177 · from 08_reliability_tasks.py:7695 · public _canon_remember_forward_pair__001 ---
def _canon_remember_forward_pair__001(A: int, B: int):
    A, B = (int(A), int(B))
    if A == B:
        return
    key, rev = (f'{A}:{B}', f'{B}:{A}')
    with data_lock, _V166_FORWARD_STATE_LOCK:
        order = data.setdefault('forward_pair_order', [])
        if not isinstance(order, list):
            order = []
            data['forward_pair_order'] = order
        if key not in order and rev not in order:
            order.append(key)
    _v166_schedule_forward_persist(A, B)

# --- finance_forward:0178 · from 08_reliability_tasks.py:7709 · public _canon_forget_forward_pair_if_empty__001 ---
def _canon_forget_forward_pair_if_empty__001(A: int, B: int):
    A, B = (int(A), int(B))
    try:
        arrow, fin, ab_on, ba_on, ab_fin, ba_fin = _forward_pair_icons(A, B)
        if ab_on or ba_on or ab_fin or ba_fin:
            return
    except Exception:
        return
    key, rev = (f'{A}:{B}', f'{B}:{A}')
    with data_lock, _V166_FORWARD_STATE_LOCK:
        order = data.setdefault('forward_pair_order', [])
        if isinstance(order, list):
            data['forward_pair_order'] = [x for x in order if x not in {key, rev}]
    _v166_cleanup_global_pair(A, B)
    _v166_schedule_forward_persist(A, B)

# --- finance_forward:0179 · from 08_reliability_tasks.py:7725 · public _canon_set_forward_menu_new_style_enabled__001 ---
def _canon_set_forward_menu_new_style_enabled__001(enabled: bool, chat_id: int | None=None):
    cid = int(chat_id) if chat_id is not None else current_state_chat_id()
    if cid is not None:
        owner_scoped_settings(int(cid))['forward_menu_new_style'] = bool(enabled)

        def _persist():
            try:
                save_data(data, chat_ids=[int(cid)])
                schedule_config_backup_for_chats(int(cid), delay=0.3)
            except Exception as exc:
                try:
                    log_error(f'v166 forward style persist: {exc}')
                except Exception:
                    pass
        V166_CONFIG_IO_TASK_POOL.submit(f'style:{int(cid)}', _persist)
    else:
        data.setdefault('_global_settings', {})['forward_menu_new_style'] = bool(enabled)
        V166_CONFIG_IO_TASK_POOL.submit('style:global', save_data, data)

# --- finance_forward:0180 · from 08_reliability_tasks.py:7744 · public _canon_toggle_forward_menu_new_style__001 ---
def _canon_toggle_forward_menu_new_style__001(chat_id: int | None=None) -> bool:
    new_value = not forward_menu_new_style_enabled(chat_id)
    set_forward_menu_new_style_enabled(new_value, chat_id)
    return new_value

# --- finance_forward:0181 · from 08_reliability_tasks.py:11162 · public _v171_forward_mode_root ---
def _v171_forward_mode_root() -> dict:
    try:
        return data.setdefault('_global_settings', {})
    except Exception:
        return {}

# --- finance_forward:0182 · from 08_reliability_tasks.py:11168 · public _canon_forward_copy_edit_mode__001 ---
def _canon_forward_copy_edit_mode__001(chat_id: int | None=None) -> str:
    gs = _v171_forward_mode_root()
    mode = str(gs.get('forward_copy_edit_mode_global') or '').strip().lower()
    if mode not in V171_FORWARD_COPY_EDIT_MODES:
        candidates = [str(gs.get('forward_copy_edit_mode') or '').strip().lower()]
        try:
            owner = int(OWNER_ID or 0)
            if owner:
                candidates.append(str(owner_scoped_settings(owner).get('forward_copy_edit_mode') or '').strip().lower())
                candidates.append(str(get_chat_store(owner).setdefault('settings', {}).get('forward_copy_edit_mode') or '').strip().lower())
        except Exception:
            pass
        mode = next((x for x in candidates if x in V171_FORWARD_COPY_EDIT_MODES), 'normal')
        gs['forward_copy_edit_mode_global'] = mode
        gs['forward_copy_edit_mode'] = mode
    try:
        if not version_mode_feature('forward_copy_edit'):
            return 'normal'
    except Exception:
        pass
    return mode if mode in V171_FORWARD_COPY_EDIT_MODES else 'normal'

# --- finance_forward:0183 · from 08_reliability_tasks.py:11190 · public _canon_set_forward_copy_edit_mode__001 ---
def _canon_set_forward_copy_edit_mode__001(chat_id: int, mode: str):
    mode = str(mode or 'normal').strip().lower()
    if mode not in V171_FORWARD_COPY_EDIT_MODES:
        mode = 'normal'
    gs = _v171_forward_mode_root()
    gs['forward_copy_edit_mode_global'] = mode
    gs['forward_copy_edit_mode'] = mode
    try:
        for cid in collect_all_known_chat_ids(include_owner=True):
            try:
                get_chat_store(int(cid)).setdefault('settings', {})['forward_copy_edit_mode'] = mode
            except Exception:
                pass
    except Exception:
        pass
    try:
        scheduler = globals().get('V166_CONFIG_IO_SCHEDULER')
        if scheduler is not None:
            scheduler.schedule('v171-forward-mode', 0.05, lambda: save_data(data, root_only=True))
        else:
            save_data(data, root_only=True)
    except Exception:
        pass
    try:
        schedule_config_backup_for_chats(delay=1.0)
    except Exception:
        pass
    return mode

# --- finance_forward:0184 · from 08_reliability_tasks.py:11219 · public _canon_cycle_forward_copy_edit_mode__001 ---
def _canon_cycle_forward_copy_edit_mode__001(chat_id: int) -> str:
    current = forward_copy_edit_mode(chat_id)
    try:
        idx = V171_FORWARD_COPY_EDIT_MODES.index(current)
    except ValueError:
        idx = 0
    return set_forward_copy_edit_mode(int(chat_id), V171_FORWARD_COPY_EDIT_MODES[(idx + 1) % len(V171_FORWARD_COPY_EDIT_MODES)])

# --- finance_forward:0185 · from 08_reliability_tasks.py:11227 · public _canon_forward_copy_edit_mode_label__001 ---
def _canon_forward_copy_edit_mode_label__001(chat_id: int) -> str:
    return {'normal': '💰фин.пересылка: обычно', 'button': '💰фин.пересылка: кнопка', 'slash': '💰фин.пересылка: слеш'}.get(forward_copy_edit_mode(chat_id), '💰фин.пересылка: обычно')

# --- finance_forward:0186 · from 08_reliability_tasks.py:14792 · public _v224_show_forward_home ---
def _v224_show_forward_home(chat_id: int, user_id: int=0, current_message_id: int=0) -> int:
    cid = int(chat_id)
    mid = int(current_message_id or 0)
    text = window_mark('📤 ПЕРЕСЫЛКА\n\n✅ Пересылка разрешена владельцем для этого чата.\nПравила работают автоматически; пользовательские настройки режима заблокированы директивной политикой.', V217_FORWARD_SCOPE_MARKER if 'V217_FORWARD_SCOPE_MARKER' in globals() else 'Ф258')
    kb = types.InlineKeyboardMarkup()
    kb.row(IB('❌ Закрыть', callback_data='aux_close'))
    return _v215_edit_or_send(cid, mid, text, kb, 'directive_forward_home_v224')

# --- finance_forward:0187 · from 08_reliability_tasks.py:15868 · public _v215_forward_rules_present ---
def _v215_forward_rules_present(chat_id: int) -> bool:
    try:
        src = str(int(chat_id))
        return bool((data.get('forward_rules', {}) or {}).get(src) or {})
    except Exception:
        return False

# --- finance_forward:0188 · from 08_reliability_tasks.py:15875 · public contour_forwarding_mode_enabled ---
def contour_forwarding_mode_enabled(chat_id: int) -> bool:
    cid = int(chat_id)
    settings = _v215_mode_settings(cid)
    if V215_FORWARD_MODE_KEY not in settings:
        return _v215_forward_rules_present(cid)
    return bool(settings.get(V215_FORWARD_MODE_KEY))

# --- finance_forward:0189 · from 08_reliability_tasks.py:15923 · public _v215_set_forward_mode ---
def _v215_set_forward_mode(chat_id: int, enabled: bool, *, persist: bool=True) -> bool:
    cid = int(chat_id)
    value = bool(enabled)
    _v215_mode_settings(cid)[V215_FORWARD_MODE_KEY] = value
    if persist:
        _v215_persist_mode(cid, 'forward_mode')
    return value

# --- finance_forward:0190 · from 08_reliability_tasks.py:16202 · public _canon_forward_any_message__002 ---
def _canon_forward_any_message__002(source_chat_id: int, msg):
    cid = int(source_chat_id)
    if _v215_circle_business_chat(cid) and (not contour_forwarding_mode_enabled(cid)):
        try:
            bot_journal('forward_mode_off_skip_v215', cid, f"message_id={int(getattr(msg, 'message_id', 0) or 0)}", 'INFO')
        except Exception:
            pass
        return
    return _V215_PREV_FORWARD_ANY_MESSAGE(cid, msg)

# --- finance_forward:0191 · from 08_reliability_tasks.py:16213 · public _canon_add_forward_link__002 ---
def _canon_add_forward_link__002(src_chat_id: int, dst_chat_id: int, mode: str):
    result = _V215_PREV_ADD_FORWARD_LINK(int(src_chat_id), int(dst_chat_id), mode)
    if _v215_circle_business_chat(int(src_chat_id)):
        _v215_set_forward_mode(int(src_chat_id), True, persist=True)
    return result

# --- finance_forward:0192 · from 08_reliability_tasks.py:16220 · public _canon_remove_forward_link__002 ---
def _canon_remove_forward_link__002(src_chat_id: int, dst_chat_id: int):
    result = _V215_PREV_REMOVE_FORWARD_LINK(int(src_chat_id), int(dst_chat_id))
    cid = int(src_chat_id)
    if _v215_circle_business_chat(cid) and (not _v215_forward_rules_present(cid)):
        _v215_set_forward_mode(cid, False, persist=True)
    return result

# --- finance_forward:0193 · from 08_reliability_tasks.py:16494 · public _canon_collect_forward_picker_items__002 ---
def _canon_collect_forward_picker_items__002(include_owner: bool=True, include_removed: bool=False):
    rows, extra = _V217_PREV_FORWARD_PICKER_ITEMS(include_owner=include_owner, include_removed=include_removed) if callable(_V217_PREV_FORWARD_PICKER_ITEMS) else ([], None)
    try:
        ctx = int(current_state_chat_id() or 0)
        if not _v215_circle_business_chat(ctx):
            return (rows, extra)
        tid = str(tenant_id_for_chat(ctx, create=False) or '')
        allowed = set((int(x) for x in tenant_chat_ids(tid)))
        clean = [(int(cid), title) for cid, title in rows if int(cid) in allowed]
        return (clean, None)
    except Exception:
        return ([], None)

# --- finance_forward:0194 · from 08_reliability_tasks.py:16508 · public _canon_collect_forward_pairs_for_menu__002 ---
def _canon_collect_forward_pairs_for_menu__002() -> list[tuple[int, int]]:
    rows = _V217_PREV_FORWARD_PAIRS() if callable(_V217_PREV_FORWARD_PAIRS) else []
    try:
        ctx = int(current_state_chat_id() or 0)
        if not _v215_circle_business_chat(ctx):
            return [(int(a), int(b)) for a, b in rows]
        tid = str(tenant_id_for_chat(ctx, create=False) or '')
        allowed = set((int(x) for x in tenant_chat_ids(tid)))
        return [(int(a), int(b)) for a, b in rows if int(a) in allowed and int(b) in allowed]
    except Exception:
        return []

# --- finance_forward:0195 · from 08_reliability_tasks.py:16520 · public _v217_forward_scope_guard ---
def _v217_forward_scope_guard(src_chat_id: int, dst_chat_id: int) -> None:
    try:
        ctx = int(current_state_chat_id() or 0)
    except Exception:
        ctx = 0
    if not ctx or not _v215_circle_business_chat(ctx):
        return
    tid = str(tenant_id_for_chat(ctx, create=False) or '')
    allowed = set((int(x) for x in tenant_chat_ids(tid)))
    if int(src_chat_id) not in allowed or int(dst_chat_id) not in allowed or (not tenant_same_space(int(src_chat_id), int(dst_chat_id))):
        raise PermissionError('Связь пересылки находится вне текущего пространства')

# --- finance_forward:0196 · from 08_reliability_tasks.py:16533 · public _v217_add_forward_link ---
def _v217_add_forward_link(src_chat_id: int, dst_chat_id: int, mode: str):
    _v217_forward_scope_guard(int(src_chat_id), int(dst_chat_id))
    return _V217_PREV_ADD_FORWARD_LINK(int(src_chat_id), int(dst_chat_id), mode)

# --- finance_forward:0197 · from 08_reliability_tasks.py:16538 · public _v217_remove_forward_link ---
def _v217_remove_forward_link(src_chat_id: int, dst_chat_id: int):
    _v217_forward_scope_guard(int(src_chat_id), int(dst_chat_id))
    return _V217_PREV_REMOVE_FORWARD_LINK(int(src_chat_id), int(dst_chat_id))

# --- finance_forward:0198 · from 08_reliability_tasks.py:16543 · public _canon_set_forward_finance__002 ---
def _canon_set_forward_finance__002(src_chat_id: int, dst_chat_id: int, enabled: bool):
    _v217_forward_scope_guard(int(src_chat_id), int(dst_chat_id))
    return _V217_PREV_SET_FORWARD_FINANCE(int(src_chat_id), int(dst_chat_id), bool(enabled))

# --- finance_forward:0199 · from 08_reliability_tasks.py:16548 · public _canon_remove_forward_finance__002 ---
def _canon_remove_forward_finance__002(src_chat_id: int, dst_chat_id: int):
    _v217_forward_scope_guard(int(src_chat_id), int(dst_chat_id))
    return _V217_PREV_REMOVE_FORWARD_FINANCE(int(src_chat_id), int(dst_chat_id))

# --- finance_forward:0200 · from 08_reliability_tasks.py:16553 · public _canon_build_forward_menu_keyboard_for_current_mode__002 ---
def _canon_build_forward_menu_keyboard_for_current_mode__002(day_key: str | None=None, A: int | None=None, B: int | None=None):
    kb = _V217_PREV_FORWARD_MENU_KB(day_key, A, B)
    try:
        cid = int(current_state_chat_id() or 0)
        if _v215_circle_business_chat(cid):
            rows = []
            for row in _v217_rows(kb):
                kept = [b for b in row or [] if not _v217_btn_cb(b).startswith('v164:circle:forward:')]
                if kept:
                    rows.append(kept)
            _v217_set_rows(kb, rows)
            _v217_insert_before_nav(kb, IB('☰ Меню', callback_data='v217:contour:menu'))
    except Exception:
        pass
    return kb

# --- finance_forward:0201 · from 08_reliability_tasks.py:16569 · public _v217_forward_scope_rows ---
def _v217_forward_scope_rows(chat_id: int) -> tuple[list[int], list[tuple[int, int, str, bool]]]:
    cid = int(chat_id)
    tid = str(tenant_id_for_chat(cid, create=False) or '')
    allowed = sorted(set((int(x) for x in tenant_chat_ids(tid))), key=lambda x: str(get_chat_display_name(x) or x).casefold())
    pairs = []
    fr = data.get('forward_rules', {}) or {}
    ff = data.get('forward_finance', {}) or {}
    seen = set()
    for src_raw, dsts in fr.items():
        try:
            src = int(src_raw)
        except Exception:
            continue
        if src not in allowed:
            continue
        for dst_raw, mode in (dsts or {}).items():
            try:
                dst = int(dst_raw)
            except Exception:
                continue
            if dst not in allowed:
                continue
            key = (src, dst)
            if key in seen:
                continue
            seen.add(key)
            pairs.append((src, dst, str(mode or 'copy'), bool((ff.get(str(src)) or {}).get(str(dst), False))))
    return (allowed, pairs)

# --- finance_forward:0202 · from 08_reliability_tasks.py:16598 · public build_v217_forward_scope_text ---
def build_v217_forward_scope_text(chat_id: int) -> str:
    allowed, pairs = _v217_forward_scope_rows(int(chat_id))
    lines = ['📤 ПЕРЕСЫЛКА ЭТОГО ПРОСТРАНСТВА', '', f'Чатов: {len(allowed)} · связей: {len(pairs)}', '']
    if not pairs:
        lines.append('Связи пересылки для этого пространства пока не настроены.')
    else:
        for src, dst, mode, fin in pairs[:30]:
            lines.append(f'• {get_chat_display_name(src)} → {get_chat_display_name(dst)} · {mode}' + (' · 💰' if fin else ''))
    lines += ['', 'Здесь никогда не показываются связи других контуров.']
    return window_mark('\n'.join(lines)[:3900], V217_FORWARD_SCOPE_MARKER)

# --- finance_forward:0203 · from 08_reliability_tasks.py:16609 · public _canon_build_v217_forward_scope_keyboard__001 ---
def _canon_build_v217_forward_scope_keyboard__001(chat_id: int, user_id: int):
    kb = types.InlineKeyboardMarkup(row_width=1)
    can_manage = False
    try:
        can_manage = bool(security_user_allowed(int(user_id or 0), 'forward_manage'))
    except Exception:
        pass
    if can_manage:
        kb.row(IB('⚙️ Открыть настройки пересылки', callback_data='v217:fwdscope:manage'))
    kb.row(IB('🔙 К режиму', callback_data='v215:mode:open:forward'))
    kb.row(IB('☰ Меню', callback_data='v217:contour:menu'))
    return kb

# --- finance_forward:0204 · from 08_reliability_tasks.py:17667 · public _v220_forward_menu_keyboard ---
def _v220_forward_menu_keyboard(day_key: str | None=None, A: int | None=None, B: int | None=None):
    kb = _V220_PREV_FORWARD_MENU(day_key, A, B)
    try:
        cid = int(current_state_chat_id() or 0)
    except Exception:
        cid = 0
    return _v220_remove_contour_menu_button(kb, cid)

# --- finance_forward:0205 · from 08_reliability_tasks.py:17676 · public _v220_forward_scope_keyboard ---
def _v220_forward_scope_keyboard(chat_id: int, user_id: int):
    return _v220_remove_contour_menu_button(_V220_PREV_FORWARD_SCOPE_KB(int(chat_id), int(user_id or 0)), int(chat_id))

# --- finance_forward:0206 · from 10_split_policy_offload.py:155 · public _v260_bind_forward_finance_record ---
def _v260_bind_forward_finance_record(rec: dict, source_msg, dst_chat_id: int, dst_msg_id: int) -> dict:
    if callable(_V262_BASE_BIND_FORWARD):
        rec = _V262_BASE_BIND_FORWARD(rec, source_msg, int(dst_chat_id), int(dst_msg_id))
    if isinstance(rec, dict):
        _ensure_finance_origin_key_v262(int(dst_chat_id), rec, int(dst_msg_id))
    return rec

# --- finance_forward:0207 · from 10_split_policy_offload.py:563 · public edit_forward_copy_and_record ---
def edit_forward_copy_and_record(chat_id: int, dst_msg_id: int, new_text: str) -> bool:
    clean_text = sanitize_telegram_inserted_text(str(new_text or '').strip())
    try:
        comp = parse_financial_components(clean_text)
    except Exception:
        return False
    rec = find_record_by_message_id(int(chat_id), int(dst_msg_id))
    if not isinstance(rec, dict):
        return False
    try:
        is_copy, _mid, source_chat_id, source_msg_id = _forward_copy_record_identity(int(chat_id), rec)
        if not is_copy:
            return False
        _hydrate_legacy_forward_copy_metadata(int(chat_id), rec, int(dst_msg_id), source_chat_id, source_msg_id)
    except Exception:
        return False
    ok = apply_linked_finance_edit_v262(int(chat_id), rec, update_ars=True, amount=float(comp.get('amount') or 0), note=str(comp.get('note') or ''), replace_usd=True, usd_amount=comp.get('usd_amount'), usd_note=str(comp.get('usd_note') or ''), usd_only=bool(comp.get('usd_only', False)), source_text=str(comp.get('source_finance_text') or clean_text), full_text_replace=True, repaint_copies=True, source_kind='slash_forward_copy')
    if ok:
        try:
            _durable_note_source_consumed('forward_copy_manual_edit_v262')
        except Exception:
            pass
    return bool(ok)

# --- finance_forward:0208 · from 10_split_policy_offload.py:8480 · public _r70_forward_dry_run ---
def _r70_forward_dry_run(chat_id):
    cid=int(chat_id);pairs=[]
    try:pairs=list(collect_forward_pairs_for_menu() or [])
    except Exception:pairs=[]
    rows=[];ok_count=0;bad_count=0
    for src,dst in pairs[:40]:
        try:
            effective=set(int(x) for x in (resolve_forward_targets(int(src)) or []));ok=int(dst) in effective
        except Exception:ok=False
        ok_count+=int(ok);bad_count+=int(not ok)
        try:sname=get_chat_display_name(int(src));dname=get_chat_display_name(int(dst))
        except Exception:sname=str(src);dname=str(dst)
        rows.append(f'{"✅" if ok else "⛔"} {_r44_html.escape(str(sname)[:28])} → {_r44_html.escape(str(dname)[:28])}')
    lines=['➡️ <b>R70 · DRY-RUN ПЕРЕСЫЛКИ</b>','',f'Настроено пар: {len(pairs)} · реально активны: {ok_count} · заблокированы: {bad_count}']
    if rows:lines+=['']+rows
    else:lines+=['','Пар пересылки сейчас нет.']
    if len(pairs)>40:lines.append(f'…ещё {len(pairs)-40}')
    lines+=['','Проверка использует тот же <code>resolve_forward_targets()</code>, что и реальная доставка. Сообщения не отправляются.']
    return window_mark('\n'.join(lines),'Ф4071')

# --- finance_forward:0209 · from 10_split_policy_offload.py:12364 · public _och129_forward_op_rows ---
def _och129_forward_op_rows(force: bool=False):
    global _OCH129_FORWARD_OP_ROWS, _OCH129_FORWARD_OP_ROWS_AT
    now = _v262_time.time()
    with _OCH129_FORWARD_REPAIR_LOCK:
        if (not force) and isinstance(_OCH129_FORWARD_OP_ROWS, list) and (now - float(_OCH129_FORWARD_OP_ROWS_AT or 0.0) < 15.0):
            return list(_OCH129_FORWARD_OP_ROWS)
        rows = []
        try:
            raw_rows = SQLITE._read_all("SELECT k,v FROM meta WHERE kind='forward_finance_ops_v260'")
            for _key, raw in raw_rows or []:
                try:
                    row = json.loads(raw) if isinstance(raw, str) else raw
                except Exception:
                    continue
                if isinstance(row, dict):
                    rows.append(row)
        except Exception as exc:
            try: log_error(f'[FWD EDIT V263] op-ledger read: {exc}')
            except Exception: pass
        _OCH129_FORWARD_OP_ROWS = rows
        _OCH129_FORWARD_OP_ROWS_AT = now
        return list(rows)

# --- finance_forward:0210 · from 10_split_policy_offload.py:12419 · public _och129_install_forward_pairs ---
def _och129_install_forward_pairs(src_chat_id: int, src_msg_id: int, pairs, reason: str='local-repair'):
    src = (int(src_chat_id), int(src_msg_id))
    clean = []
    for pair in pairs or []:
        try:
            p = (int(pair[0]), int(pair[1]))
        except Exception:
            continue
        if p[0] and p[1] and p not in clean:
            clean.append(p)
    if not clean:
        return []
    changed = False
    try:
        with forward_map_lock:
            current = forward_map.setdefault(src, [])
            for p in clean:
                if p not in current:
                    current.append(p); changed = True
            resolved = list(current)
    except Exception:
        resolved = clean
    if changed:
        try:
            _persist_forward_index_in_data(data)
        except Exception:
            pass
        try:
            # OCH12.14: every forward-link repair mutates the same root forward_index.
            # Hundreds of per-message save_data tasks are redundant and previously
            # amplified the single background lane.  Keep at most one running plus
            # one newest root persistence task.
            pool = globals().get('PERSIST_LATEST_TASK_POOL')
            if pool is not None and hasattr(pool, 'submit_latest'):
                pool.submit_latest('v263-fwd-index-root-v214', save_data, data, root_only=True)
            else:
                fallback = globals().get('BACKGROUND_TASK_POOL') or globals().get('GENERAL_TASK_POOL')
                if fallback is not None and hasattr(fallback, 'submit_unique'):
                    fallback.submit_unique('v263-fwd-index-root-v214', save_data, data, root_only=True)
        except Exception:
            pass
        try:
            bot_journal('forward_index_self_healed_v263', int(src[0]), f'msg={src[1]}; pairs={len(clean)}; reason={reason}')
        except Exception:
            pass
    return resolved

# --- finance_forward:0211 · from 10_split_policy_offload.py:12467 · public _och129_recover_forward_links_local ---
def _och129_recover_forward_links_local(src_chat_id: int, src_msg_id: int, target_chat_id: int | None=None, *, scan_records: bool=True):
    """Network-free forward identity recovery used by every finance edit path."""
    src_chat_id = int(src_chat_id); src_msg_id = int(src_msg_id)
    target = int(target_chat_id) if target_chat_id is not None else None
    pairs = []
    # 1) Durable operation ledger: O(ledger rows), no network, survives deploy/full SQLite restore.
    for row in _och129_forward_op_rows(False):
        try:
            if int(row.get('source_chat_id') or 0) != src_chat_id or int(row.get('source_msg_id') or 0) != src_msg_id:
                continue
            dst_chat = int(row.get('dst_chat_id') or 0); dst_mid = int(row.get('dst_msg_id') or 0)
            state = str(row.get('state') or '')
            if target is not None and dst_chat != target:
                continue
            if dst_chat and dst_mid and state not in {'deleted', 'cancelled', 'removed'}:
                p = (dst_chat, dst_mid)
                if p not in pairs: pairs.append(p)
        except Exception:
            continue
    # 2) Finance rows: immutable v262 origin key / fwd-fin operation key is a second witness.
    # For a known destination this is one-chat only; general scans happen only on a cache miss.
    if scan_records and (not pairs or target is None):
        miss_key = (src_chat_id, src_msg_id, target)
        do_scan = True
        with _OCH129_FORWARD_REPAIR_LOCK:
            if miss_key in _OCH129_FORWARD_RECORD_SCAN_MISS:
                do_scan = False
        if do_scan:
            if target is not None:
                chat_ids = [target]
            else:
                chat_ids = []
                try:
                    chat_ids.extend(int(x) for x in ((data or {}).get('chats', {}) or {}).keys())
                except Exception:
                    pass
                try:
                    # Root finance chat may exist outside the currently materialized LOW-RAM dict.
                    chat_ids.append(int(src_chat_id))
                except Exception:
                    pass
                chat_ids = list(dict.fromkeys(chat_ids))
            for cid in chat_ids:
                try:
                    store = get_chat_store(int(cid))
                    seen = set()
                    for ledger in ('records', 'ars_records', 'usd_records'):
                        rows = store.get(ledger, []) or []
                        for rec in rows:
                            if not isinstance(rec, dict) or id(rec) in seen:
                                continue
                            seen.add(id(rec))
                            p = _och129_pair_from_record(int(cid), rec, src_chat_id, src_msg_id)
                            if p and (target is None or p[0] == target) and p not in pairs:
                                pairs.append(p)
                except Exception:
                    continue
            if not pairs:
                with _OCH129_FORWARD_REPAIR_LOCK:
                    _OCH129_FORWARD_RECORD_SCAN_MISS.add(miss_key)
    if pairs:
        # Recreate missing durable op rows from record witnesses as well.
        for dst_chat, dst_mid in pairs:
            try:
                row = _v260_forward_finance_op_get(src_chat_id, src_msg_id, dst_chat)
                if not int((row or {}).get('dst_msg_id') or 0):
                    _v260_forward_finance_op_mark(src_chat_id, src_msg_id, dst_chat, 'committed', dst_msg_id=int(dst_mid), recovered_v263=True)
            except Exception:
                pass
        return _och129_install_forward_pairs(src_chat_id, src_msg_id, pairs, 'sqlite-op+records')
    return []

# --- finance_forward:0212 · from 10_split_policy_offload.py:12540 · public get_forward_links ---
def get_forward_links(src_chat_id: int, src_msg_id: int):
    links = []
    try:
        if callable(_OCH129_PARENT_GET_FORWARD_LINKS):
            links = list(_OCH129_PARENT_GET_FORWARD_LINKS(int(src_chat_id), int(src_msg_id)) or [])
    except Exception:
        links = []
    if links:
        return links
    return list(_och129_recover_forward_links_local(int(src_chat_id), int(src_msg_id), None, scan_records=True) or [])

# --- finance_forward:0213 · from 10_split_policy_offload.py:12552 · public _och129_reconcile_existing_forward_copy ---
def _och129_reconcile_existing_forward_copy(source_chat_id: int, msg, dst_chat_id: int, dst_msg_id: int, finance_enabled: bool):
    """A repeated pre-deploy message is reconcile/edit, never a second Telegram copy."""
    try:
        new_mid = sync_edited_copy_to_target(int(source_chat_id), msg, int(dst_chat_id), int(dst_msg_id), bool(finance_enabled))
    except Exception as exc:
        try: log_error(f'[FWD EDIT V263] reconcile {source_chat_id}:{getattr(msg,"message_id",0)}->{dst_chat_id}:{dst_msg_id}: {exc}')
        except Exception: pass
        return None
    if not new_mid:
        return None
    try:
        _store_forward_link(int(source_chat_id), int(getattr(msg, 'message_id', 0) or 0), int(dst_chat_id), int(new_mid))
    except Exception:
        pass
    if finance_enabled:
        try:
            rec = find_record_by_message_id(int(dst_chat_id), int(new_mid))
            if isinstance(rec, dict):
                _persist_forward_finance_delivery_now(int(source_chat_id), int(getattr(msg, 'message_id', 0) or 0), int(dst_chat_id), int(new_mid), rec)
            else:
                _v260_forward_finance_op_mark(int(source_chat_id), int(getattr(msg, 'message_id', 0) or 0), int(dst_chat_id), 'copy_delivered', dst_msg_id=int(new_mid), recovered_v263=True)
        except Exception:
            pass
    try:
        bot_journal('forward_existing_copy_reconciled_v263', int(dst_chat_id), f'src={source_chat_id}:{getattr(msg,"message_id",0)}; dst={dst_chat_id}:{new_mid}')
    except Exception:
        pass
    return int(new_mid)

# --- finance_forward:0214 · from 10_split_policy_offload.py:12582 · public _forward_single_to_target ---
def _forward_single_to_target(source_chat_id: int, msg, dst_chat_id: int, finance_enabled: bool, _migration_retry: bool=False):
    src_mid = int(getattr(msg, 'message_id', 0) or 0)
    # Resolve the exact destination before the legacy create-copy branch.  This makes
    # post-deploy redelivery idempotent even when the RAM/root forward_index vanished.
    links = list(get_forward_links(int(source_chat_id), src_mid) or [])
    match = next(((dc, dm) for dc, dm in links if int(dc) == int(dst_chat_id)), None)
    if match is None and finance_enabled:
        healed = _och129_recover_forward_links_local(int(source_chat_id), src_mid, int(dst_chat_id), scan_records=True)
        match = next(((dc, dm) for dc, dm in healed if int(dc) == int(dst_chat_id)), None)
    if match is not None:
        reconciled = _och129_reconcile_existing_forward_copy(int(source_chat_id), msg, int(dst_chat_id), int(match[1]), bool(finance_enabled))
        if reconciled:
            return int(reconciled)
        # If Telegram edit/replacement itself fails, preserve exact-once: do not blindly
        # create another copy while a durable destination identity still exists.
        try:
            bot_journal('forward_existing_copy_reconcile_deferred_v263', int(dst_chat_id), f'src={source_chat_id}:{src_mid}; dst={dst_chat_id}:{match[1]}', 'WARN')
        except Exception:
            pass
        return int(match[1])
    if callable(_OCH129_PARENT_FORWARD_SINGLE):
        return _OCH129_PARENT_FORWARD_SINGLE(int(source_chat_id), msg, int(dst_chat_id), bool(finance_enabled), _migration_retry=_migration_retry)
    return None

# --- finance_forward:0215 · from 10_split_policy_offload.py:12663 · public _och129_boot_rebuild_forward_identity ---
def _och129_boot_rebuild_forward_identity():
    repaired = 0
    try:
        # Merge durable op-ledger links even when root forward_index exists but is stale/partial.
        grouped = {}
        for row in _och129_forward_op_rows(True):
            try:
                sc = int(row.get('source_chat_id') or 0); sm = int(row.get('source_msg_id') or 0)
                dc = int(row.get('dst_chat_id') or 0); dm = int(row.get('dst_msg_id') or 0)
                if sc and sm and dc and dm and str(row.get('state') or '') not in {'deleted','cancelled','removed'}:
                    grouped.setdefault((sc, sm), []).append((dc, dm))
            except Exception:
                continue
        for (sc, sm), pairs in grouped.items():
            before = []
            try:
                before = list(_OCH129_PARENT_GET_FORWARD_LINKS(sc, sm) or []) if callable(_OCH129_PARENT_GET_FORWARD_LINKS) else []
            except Exception:
                pass
            after = _och129_install_forward_pairs(sc, sm, pairs, 'boot-op-ledger')
            repaired += max(0, len(after) - len(before))
        try:
            legacy = globals().get('_rebuild_forward_index_from_finance_records')
            if callable(legacy):
                repaired += int(legacy(data) or 0)
        except Exception:
            pass
        try: bot_journal('forward_identity_boot_rebuild_v263', int(OWNER_ID or 0), f'repaired={repaired}; sources={len(grouped)}')
        except Exception: pass
    except Exception as exc:
        try: log_error(f'[FWD EDIT V263] boot rebuild: {exc}')
        except Exception: pass
    return repaired

# v266
