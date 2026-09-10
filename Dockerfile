FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates curl gnupg openssl \
 && mkdir -p /etc/apt/keyrings \
 && curl -fsSL https://mega.nz/linux/repo/Debian_12/Release.key | gpg --dearmor -o /etc/apt/keyrings/mega.gpg \
 && echo "deb [signed-by=/etc/apt/keyrings/mega.gpg] https://mega.nz/linux/repo/Debian_12/ ./" > /etc/apt/sources.list.d/mega.list \
 && apt-get update \
 && apt-get install -y --no-install-recommends megacmd \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# R49 FINAL CLEAN BUILD: explicit allowlist. Never COPY the whole repository.
# Stale legacy modules (00_core.py, 89_callback_final.py, 97_r29_policy_ui.py, etc.)
# therefore cannot coexist with the compact runtime inside /app.
COPY bot.py start_front.py runtime_config.py modules_manifest.json FINALIZATION_GATE.py ./
COPY 01_core_data.py 02_transport_safety.py 03_diagnostics_memory.py \
     04_messages_features.py 05_finance_ui.py 06_commands_callbacks.py \
     07_state_web.py 08_reliability_tasks.py 09_final_transport.py \
     10_split_policy_offload.py ./
# INFO/ is release documentation and is intentionally NOT copied into the runtime image.
# Missing docs in a Render/Git build context must never prevent the bot from starting.

# Fail the image build before Deploy if runtime structure/startup is broken.
RUN B_T=123456:STARTUPSMOKE DB_FILE=/tmp/r49_build_smoke.sqlite3 \
    REDIS_URL= PEER_PRIVATE_URL= PEER_SERVICE_URL= PEER_SHARED_SECRET= \
    MEGA_EMAIL= MEGA_PASSWORD= TRAFFIC_AUDIT_ENABLED=0 \
    FINALIZATION_REQUIRE_INFO=0 FINALIZATION_RUNTIME_BUILD=1 FINALIZATION_STARTUP_SMOKE=1 \
    python FINALIZATION_GATE.py \
 && rm -f /tmp/r49_build_smoke.sqlite3 /tmp/r49_build_smoke.sqlite3-wal /tmp/r49_build_smoke.sqlite3-shm

CMD ["python", "start_front.py"]
