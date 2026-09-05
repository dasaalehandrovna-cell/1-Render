# v262
"""Render Key Value / Valkey fast ephemeral layer (v248).

No third-party Redis client is imported: this module implements the tiny RESP2 subset
needed by the bot.  The store is optional.  If no URL is configured or the service is
briefly unavailable, callers fall back to the existing local/SQLite behaviour.
"""

KEY_VALUE_URL = str(
    os.getenv('RENDER_KEY_VALUE_URL')
    or os.getenv('KEY_VALUE_URL')
    or os.getenv('REDIS_URL')
    or os.getenv('VALKEY_URL')
    or ''
).strip()
KEY_VALUE_ENABLED = str(os.getenv('KEY_VALUE_ENABLED', '1') or '1').strip().casefold() not in {'0', 'false', 'no', 'off'}
KEY_VALUE_PREFIX = str(os.getenv('KEY_VALUE_PREFIX', 'vysbot:kv1') or 'vysbot:kv1').strip(': ') or 'vysbot:kv1'
KEY_VALUE_CONNECT_TIMEOUT = max(0.05, min(1.0, float(os.getenv('KEY_VALUE_CONNECT_TIMEOUT_SECONDS', '0.18') or '0.18')))
KEY_VALUE_SOCKET_TIMEOUT = max(0.05, min(1.5, float(os.getenv('KEY_VALUE_SOCKET_TIMEOUT_SECONDS', '0.22') or '0.22')))
KEY_VALUE_FAILURE_COOLDOWN = max(2.0, min(120.0, float(os.getenv('KEY_VALUE_FAILURE_COOLDOWN_SECONDS', '20') or '20')))
KEY_VALUE_NAV_TTL_SECONDS = max(300, min(86400, int(os.getenv('KEY_VALUE_NAV_TTL_SECONDS', '7200') or '7200')))
KEY_VALUE_CALLBACK_TTL_SECONDS = max(900, min(86400, int(os.getenv('KEY_VALUE_CALLBACK_TTL_SECONDS', str(6 * 60 * 60)) or str(6 * 60 * 60))))


def key_value_configured_v248() -> bool:
    return bool(KEY_VALUE_ENABLED and KEY_VALUE_URL and KEY_VALUE_URL.startswith(('redis://', 'rediss://')))


def _kv_safe_endpoint_v248() -> str:
    if not key_value_configured_v248():
        return ''
    try:
        parsed = urllib.parse.urlparse(KEY_VALUE_URL)
        return f"{parsed.hostname or ''}:{parsed.port or (6380 if parsed.scheme == 'rediss' else 6379)}"
    except Exception:
        return 'configured'


class _RenderKeyValueRESPClientV248:
    def __init__(self, url: str):
        self.url = str(url or '')
        self._lock = threading.RLock()
        self._sock = None
        self._parsed = urllib.parse.urlparse(self.url) if self.url else None
        self._disabled_until = 0.0
        self._stats = {
            'commands': 0, 'pipelines': 0, 'hits': 0, 'misses': 0, 'writes': 0,
            'errors': 0, 'connects': 0, 'last_error': '', 'last_ok_at': '', 'last_error_at': '',
        }

    @staticmethod
    def _part_bytes(value):
        if isinstance(value, bytes):
            return value
        if value is None:
            return b''
        if isinstance(value, bool):
            return b'1' if value else b'0'
        return str(value).encode('utf-8')

    @classmethod
    def _frame(cls, parts) -> bytes:
        out = [f"*{len(parts)}\r\n".encode('ascii')]
        for part in parts:
            raw = cls._part_bytes(part)
            out.append(f"${len(raw)}\r\n".encode('ascii'))
            out.append(raw)
            out.append(b'\r\n')
        return b''.join(out)

    @staticmethod
    def _read_line(sock) -> bytes:
        buf = bytearray()
        while True:
            chunk = sock.recv(1)
            if not chunk:
                raise ConnectionError('Key Value connection closed')
            buf.extend(chunk)
            if len(buf) >= 2 and buf[-2:] == b'\r\n':
                return bytes(buf[:-2])

    @classmethod
    def _read_exact(cls, sock, size: int) -> bytes:
        out = bytearray()
        while len(out) < size:
            chunk = sock.recv(size - len(out))
            if not chunk:
                raise ConnectionError('Key Value connection closed')
            out.extend(chunk)
        return bytes(out)

    @classmethod
    def _read_resp(cls, sock):
        lead = cls._read_exact(sock, 1)
        if lead == b'+':
            return cls._read_line(sock).decode('utf-8', errors='replace')
        if lead == b'-':
            msg = cls._read_line(sock).decode('utf-8', errors='replace')
            raise RuntimeError(f'Key Value error: {msg[:220]}')
        if lead == b':':
            return int(cls._read_line(sock) or b'0')
        if lead == b'$':
            size = int(cls._read_line(sock) or b'-1')
            if size < 0:
                return None
            raw = cls._read_exact(sock, size)
            tail = cls._read_exact(sock, 2)
            if tail != b'\r\n':
                raise ConnectionError('Key Value malformed bulk reply')
            return raw
        if lead == b'*':
            count = int(cls._read_line(sock) or b'-1')
            if count < 0:
                return None
            return [cls._read_resp(sock) for _ in range(count)]
        raise ConnectionError(f'Key Value unsupported RESP lead={lead!r}')

    def _close_locked(self):
        sock, self._sock = self._sock, None
        if sock is not None:
            try:
                sock.close()
            except Exception:
                pass

    def _mark_error_locked(self, exc):
        self._stats['errors'] = int(self._stats.get('errors', 0) or 0) + 1
        self._stats['last_error'] = str(exc)[:220]
        self._stats['last_error_at'] = now_local().isoformat(timespec='seconds') if 'now_local' in globals() else datetime.now(timezone.utc).isoformat(timespec='seconds')
        self._disabled_until = time.monotonic() + KEY_VALUE_FAILURE_COOLDOWN
        self._close_locked()

    def _send_auth_and_select_locked(self, sock):
        parsed = self._parsed
        username = urllib.parse.unquote(parsed.username or '') if parsed else ''
        password = urllib.parse.unquote(parsed.password or '') if parsed else ''
        if password:
            parts = ('AUTH', username or 'default', password) if username else ('AUTH', password)
            sock.sendall(self._frame(parts))
            self._read_resp(sock)
        path = (parsed.path or '').strip('/') if parsed else ''
        if path and path.isdigit() and int(path) > 0:
            sock.sendall(self._frame(('SELECT', int(path))))
            self._read_resp(sock)

    def _connect_locked(self):
        if self._sock is not None:
            return self._sock
        if not key_value_configured_v248():
            raise ConnectionError('Key Value not configured')
        if time.monotonic() < float(self._disabled_until or 0):
            raise ConnectionError('Key Value circuit open')
        parsed = self._parsed
        host = parsed.hostname
        port = int(parsed.port or (6380 if parsed.scheme == 'rediss' else 6379))
        if not host:
            raise ConnectionError('Key Value host missing')
        sock = socket.create_connection((host, port), timeout=KEY_VALUE_CONNECT_TIMEOUT)
        sock.settimeout(KEY_VALUE_SOCKET_TIMEOUT)
        if parsed.scheme == 'rediss':
            import ssl as _kv_ssl
            sock = _kv_ssl.create_default_context().wrap_socket(sock, server_hostname=host)
            sock.settimeout(KEY_VALUE_SOCKET_TIMEOUT)
        self._send_auth_and_select_locked(sock)
        self._sock = sock
        self._stats['connects'] = int(self._stats.get('connects', 0) or 0) + 1
        return sock

    def command(self, *parts):
        if not key_value_configured_v248():
            raise ConnectionError('Key Value not configured')
        with self._lock:
            if time.monotonic() < float(self._disabled_until or 0):
                raise ConnectionError('Key Value circuit open')
            try:
                sock = self._connect_locked()
                sock.sendall(self._frame(parts))
                result = self._read_resp(sock)
                self._stats['commands'] = int(self._stats.get('commands', 0) or 0) + 1
                self._stats['last_ok_at'] = now_local().isoformat(timespec='seconds') if 'now_local' in globals() else datetime.now(timezone.utc).isoformat(timespec='seconds')
                return result
            except Exception as exc:
                self._mark_error_locked(exc)
                raise

    def pipeline(self, commands):
        commands = [tuple(x) for x in commands if x]
        if not commands:
            return []
        if not key_value_configured_v248():
            raise ConnectionError('Key Value not configured')
        with self._lock:
            if time.monotonic() < float(self._disabled_until or 0):
                raise ConnectionError('Key Value circuit open')
            try:
                sock = self._connect_locked()
                sock.sendall(b''.join(self._frame(parts) for parts in commands))
                result = [self._read_resp(sock) for _ in commands]
                self._stats['commands'] = int(self._stats.get('commands', 0) or 0) + len(commands)
                self._stats['pipelines'] = int(self._stats.get('pipelines', 0) or 0) + 1
                self._stats['last_ok_at'] = now_local().isoformat(timespec='seconds') if 'now_local' in globals() else datetime.now(timezone.utc).isoformat(timespec='seconds')
                return result
            except Exception as exc:
                self._mark_error_locked(exc)
                raise

    def reset_circuit(self):
        with self._lock:
            self._disabled_until = 0.0
            self._close_locked()

    def stats(self):
        with self._lock:
            row = dict(self._stats)
            row['configured'] = key_value_configured_v248()
            row['endpoint'] = _kv_safe_endpoint_v248()
            row['connected'] = self._sock is not None
            row['circuit_open_seconds'] = round(max(0.0, float(self._disabled_until or 0) - time.monotonic()), 2)
            return row


KEY_VALUE_CLIENT_V248 = _RenderKeyValueRESPClientV248(KEY_VALUE_URL)


def _kv_key_v248(suffix: str) -> str:
    clean = str(suffix or '').strip().replace(' ', '_')
    return f'{KEY_VALUE_PREFIX}:{clean}'


def key_value_ping_v248(force: bool=False) -> bool:
    if not key_value_configured_v248():
        return False
    if force:
        KEY_VALUE_CLIENT_V248.reset_circuit()
    try:
        return str(KEY_VALUE_CLIENT_V248.command('PING')).upper() == 'PONG'
    except Exception:
        return False


def key_value_status_v248() -> dict:
    row = KEY_VALUE_CLIENT_V248.stats()
    row['enabled'] = bool(KEY_VALUE_ENABLED)
    row['prefix'] = KEY_VALUE_PREFIX
    return row


def kv_get_text_v248(suffix: str):
    if not key_value_configured_v248():
        return None
    try:
        raw = KEY_VALUE_CLIENT_V248.command('GET', _kv_key_v248(suffix))
        if raw is None:
            KEY_VALUE_CLIENT_V248._stats['misses'] = int(KEY_VALUE_CLIENT_V248._stats.get('misses', 0) or 0) + 1
            return None
        KEY_VALUE_CLIENT_V248._stats['hits'] = int(KEY_VALUE_CLIENT_V248._stats.get('hits', 0) or 0) + 1
        return raw.decode('utf-8', errors='replace') if isinstance(raw, (bytes, bytearray)) else str(raw)
    except Exception:
        return None


def kv_set_text_v248(suffix: str, value, ttl_seconds: int | None=None) -> bool:
    if not key_value_configured_v248():
        return False
    try:
        parts = ['SET', _kv_key_v248(suffix), str(value)]
        if ttl_seconds:
            parts += ['EX', max(1, int(ttl_seconds))]
        ok = str(KEY_VALUE_CLIENT_V248.command(*parts)).upper() == 'OK'
        if ok:
            KEY_VALUE_CLIENT_V248._stats['writes'] = int(KEY_VALUE_CLIENT_V248._stats.get('writes', 0) or 0) + 1
        return ok
    except Exception:
        return False


def kv_get_json_v248(suffix: str, default=None):
    raw = kv_get_text_v248(suffix)
    if raw is None:
        return default
    try:
        return json.loads(raw)
    except Exception:
        return default


def kv_set_json_v248(suffix: str, value, ttl_seconds: int | None=None) -> bool:
    try:
        raw = json.dumps(value, ensure_ascii=False, separators=(',', ':'), default=str)
    except Exception:
        return False
    return kv_set_text_v248(suffix, raw, ttl_seconds)


def kv_delete_v248(suffix: str) -> bool:
    if not key_value_configured_v248():
        return False
    try:
        return bool(KEY_VALUE_CLIENT_V248.command('DEL', _kv_key_v248(suffix)))
    except Exception:
        return False


def kv_exists_v248(suffix: str) -> bool:
    if not key_value_configured_v248():
        return False
    try:
        return bool(KEY_VALUE_CLIENT_V248.command('EXISTS', _kv_key_v248(suffix)))
    except Exception:
        return False


def kv_nav_suffix_v248(chat_id: int, message_id: int) -> str:
    return f'ui:nav:{int(chat_id)}:{int(message_id)}'


def kv_nav_push_v248(chat_id: int, message_id: int, snapshot: dict, limit: int=12) -> bool:
    if not key_value_configured_v248():
        return False
    try:
        raw = json.dumps(snapshot, ensure_ascii=False, separators=(',', ':'), default=str)
        key = _kv_key_v248(kv_nav_suffix_v248(chat_id, message_id))
        index_key = _kv_key_v248(f'ui:navindex:{int(chat_id)}')
        KEY_VALUE_CLIENT_V248.pipeline([
            ('RPUSH', key, raw),
            ('LTRIM', key, -max(1, int(limit)), -1),
            ('EXPIRE', key, KEY_VALUE_NAV_TTL_SECONDS),
            ('SADD', index_key, key),
            ('EXPIRE', index_key, KEY_VALUE_NAV_TTL_SECONDS),
        ])
        KEY_VALUE_CLIENT_V248._stats['writes'] = int(KEY_VALUE_CLIENT_V248._stats.get('writes', 0) or 0) + 1
        return True
    except Exception:
        return False


def kv_nav_peek_v248(chat_id: int, message_id: int):
    if not key_value_configured_v248():
        return None
    try:
        raw = KEY_VALUE_CLIENT_V248.command('LINDEX', _kv_key_v248(kv_nav_suffix_v248(chat_id, message_id)), -1)
        if raw is None:
            return None
        text = raw.decode('utf-8', errors='replace') if isinstance(raw, (bytes, bytearray)) else str(raw)
        value = json.loads(text)
        return value if isinstance(value, dict) else None
    except Exception:
        return None


def kv_nav_pop_v248(chat_id: int, message_id: int) -> bool:
    if not key_value_configured_v248():
        return False
    try:
        raw = KEY_VALUE_CLIENT_V248.command('RPOP', _kv_key_v248(kv_nav_suffix_v248(chat_id, message_id)))
        return raw is not None
    except Exception:
        return False


def kv_nav_has_v248(chat_id: int, message_id: int) -> bool:
    return kv_exists_v248(kv_nav_suffix_v248(chat_id, message_id))


def kv_nav_clear_v248(chat_id: int, message_id: int) -> bool:
    return kv_delete_v248(kv_nav_suffix_v248(chat_id, message_id))


def kv_nav_clear_chat_v248(chat_id: int) -> int:
    if not key_value_configured_v248():
        return 0
    index_key = _kv_key_v248(f'ui:navindex:{int(chat_id)}')
    try:
        members = KEY_VALUE_CLIENT_V248.command('SMEMBERS', index_key) or []
        keys = []
        for raw in members:
            if isinstance(raw, (bytes, bytearray)):
                keys.append(raw.decode('utf-8', errors='replace'))
            elif raw:
                keys.append(str(raw))
        if keys:
            KEY_VALUE_CLIENT_V248.command('DEL', *keys)
        KEY_VALUE_CLIENT_V248.command('DEL', index_key)
        return len(keys)
    except Exception:
        return 0


def kv_callback_store_v248(token: str, callback_data: str) -> bool:
    return kv_set_text_v248(f'cb:{str(token)}', str(callback_data), KEY_VALUE_CALLBACK_TTL_SECONDS)


def kv_callback_resolve_v248(token: str):
    return kv_get_text_v248(f'cb:{str(token)}')


def kv_distributed_lock_try_v248(name: str, ttl_seconds: int=600):
    """Return (allowed, token, backend). Fallback is fail-open because local locks remain authoritative."""
    if not key_value_configured_v248():
        return (True, None, 'local')
    token = secrets.token_hex(12)
    try:
        result = KEY_VALUE_CLIENT_V248.command('SET', _kv_key_v248(f'lock:{name}'), token, 'NX', 'EX', max(2, int(ttl_seconds)))
    except Exception:
        return (True, None, 'local_fallback')
    if str(result or '').upper() == 'OK':
        return (True, token, 'key_value')
    return (False, None, 'key_value')


def kv_distributed_lock_release_v248(name: str, token) -> bool:
    if not token or not key_value_configured_v248():
        return True
    script = "if redis.call('get',KEYS[1]) == ARGV[1] then return redis.call('del',KEYS[1]) else return 0 end"
    try:
        return bool(KEY_VALUE_CLIENT_V248.command('EVAL', script, 1, _kv_key_v248(f'lock:{name}'), str(token)))
    except Exception:
        return False


def _key_value_warmup_v248():
    if not key_value_configured_v248():
        return False
    ok = key_value_ping_v248(force=True)
    try:
        bot_journal('key_value_ready' if ok else 'key_value_unavailable', None, f'endpoint={_kv_safe_endpoint_v248() or "—"}; fallback=local_sqlite', 'INFO' if ok else 'WARN')
    except Exception:
        pass
    return ok


try:
    if key_value_configured_v248() and 'GENERAL_TASK_POOL' in globals():
        GENERAL_TASK_POOL.submit_unique('v248-key-value-warmup', _key_value_warmup_v248)
except Exception:
    pass
# v262
