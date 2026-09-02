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
CMD ["python", "start_front.py"]
