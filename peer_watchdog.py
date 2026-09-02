# v262
"""Tiny Render peer watchdog for bot_v206.

Deploy this file as a separate Render Web Service. It exposes /keepalive so the main
bot can ping it, and periodically sends a tiny HEAD request to the main bot.
"""
import os
import threading
import time
from urllib.parse import urlsplit, urlunsplit

import requests
from flask import Flask, request

app = Flask(__name__)
VERSION = "peer_watchdog_v2"


def _env_bool(name: str, default: bool = True) -> bool:
    return str(os.getenv(name, "1" if default else "0") or "").strip().lower() in {"1", "true", "yes", "on", "y", "да"}


def _interval() -> int:
    try:
        return max(60, min(3600, int(os.getenv("PING_INTERVAL_SECONDS", "600") or "600")))
    except Exception:
        return 600


def _target() -> str:
    raw = str(os.getenv("TARGET_URL", "") or "").strip().rstrip("/")
    if raw and not raw.lower().startswith(("http://", "https://")):
        raw = "https://" + raw
    if not raw:
        return ""
    try:
        p = urlsplit(raw)
        if not p.hostname:
            return ""
        return urlunsplit((p.scheme or "https", p.netloc, p.path.rstrip("/"), "", "")).rstrip("/")
    except Exception:
        return ""


STATE = {
    "started_at": time.time(),
    "last_attempt_at": 0.0,
    "last_ok_at": 0.0,
    "last_error": "",
    "last_status": None,
    "incoming_at": 0.0,
    "ok_count": 0,
    "fail_count": 0,
}


def _ping_once():
    base = _target()
    STATE["last_attempt_at"] = time.time()
    if not base:
        STATE["last_error"] = "TARGET_URL is empty"
        STATE["fail_count"] += 1
        return False
    url = base if base.endswith("/keepalive") else base + "/keepalive"
    headers = {"User-Agent": f"{VERSION}-peer-watchdog", "Cache-Control": "no-cache"}
    try:
        r = requests.head(url, timeout=12, headers=headers, allow_redirects=True)
        if not (200 <= r.status_code < 500):
            r = requests.get(url, timeout=12, headers=headers, allow_redirects=True)
        STATE["last_status"] = int(r.status_code)
        if 200 <= r.status_code < 500:
            STATE["last_ok_at"] = time.time(); STATE["last_error"] = ""; STATE["ok_count"] += 1
            print(f"[PEER] OK -> {url} HTTP {r.status_code}; next in {_interval()}s", flush=True)
            return True
        STATE["last_error"] = f"HTTP {r.status_code}"
    except Exception as exc:
        STATE["last_status"] = None; STATE["last_error"] = str(exc)[:400]
    STATE["fail_count"] += 1
    print(f"[PEER] ERROR -> {url if base else 'TARGET_URL'}: {STATE['last_error']}; retry in {_interval()}s", flush=True)
    return False


def _loop():
    # Give the web server a few seconds to bind, then establish mutual ping quickly.
    time.sleep(5)
    while True:
        if _env_bool("PING_ENABLED", True):
            _ping_once()
            time.sleep(_interval())
        else:
            time.sleep(30)


@app.route("/", methods=["GET", "HEAD"])
@app.route("/healthz", methods=["GET", "HEAD"])
@app.route("/keepalive", methods=["GET", "HEAD"])
def health():
    STATE["incoming_at"] = time.time()
    if request.method == "HEAD":
        return "", 200
    return {
        "ok": True,
        "version": VERSION,
        "target_configured": bool(_target()),
        "ping_enabled": _env_bool("PING_ENABLED", True),
        "interval_seconds": _interval(),
        "last_ok_at": STATE["last_ok_at"],
        "last_status": STATE["last_status"],
        "last_error": STATE["last_error"],
        "ok_count": STATE["ok_count"],
        "fail_count": STATE["fail_count"],
    }, 200


if __name__ == "__main__":
    threading.Thread(target=_loop, name="peer-watchdog", daemon=True).start()
    port = int(os.getenv("PORT", "10000") or "10000")
    app.run(host="0.0.0.0", port=port, threaded=True)
# v262
