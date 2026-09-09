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
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .

# R48 STARTUPFIX: fail the image build if the compact runtime cannot be imported.
# This catches definition-order, semantic-owner and startup-contract regressions
# before Render switches traffic to the new instance.
RUN python FINALIZATION_GATE.py \
 && B_T=123456:STARTUPSMOKE DB_FILE=/tmp/r48_build_smoke.sqlite3 \
    REDIS_URL= PEER_PRIVATE_URL= PEER_SERVICE_URL= PEER_SHARED_SECRET= \
    MEGA_EMAIL= MEGA_PASSWORD= TRAFFIC_AUDIT_ENABLED=0 \
    python -c "import bot; assert bot.r29_assert_r28_fast_ui_contract() is True; print('R48 FAST IMPORT SMOKE PASS')" \
 && rm -f /tmp/r48_build_smoke.sqlite3 /tmp/r48_build_smoke.sqlite3-wal /tmp/r48_build_smoke.sqlite3-shm

CMD ["python", "start_front.py"]
