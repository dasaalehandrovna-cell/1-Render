# PATCH_PROTOCOL — PATCH → FINALIZE → TEST → PACKAGE

## 1. PATCH

- Менять только канонический owner функции/маршрута.
- Для FAST/HEAVY сначала определить сторону ответственности.
- Не добавлять `PREV/ORIG/BASE` monkey-patch, временный `bot.method = ...` или `globals()[public_name] = ...`.
- Сохранять wire-contract FAST↔HEAVY и `job_id`.

## 2. FINALIZE

- Удалить заменённые wrappers, captures и compatibility-call-through.
- Проверить один вход Telegram, один callback extension dispatcher, один Telegram output transport, один MEGA runner и один durable outbox dispatcher.
- Проверить, что обычный `on_any_message` не обёрнут runtime-wrapper'ами.
- Ограничить workers/buffers, если новый код создаёт фоновые очереди.
- Обновить manifest hashes и release metadata.

## 3. TEST

Запускать из корня ZIP до упаковки:

```bash
python -m compileall -q .
python FINALIZATION_GATE.py
```

После упаковки:

```bash
unzip -t <package>.zip
```

Production acceptance после deploy: READY без OOM/cgroup max growth, callback ACK/UI без многосекундного wrapper stack, durable outbox сохраняет job при временной недоступности HEAVY.

## 4. PACKAGE

Упаковывать только после PASS gate. ZIP должен открываться с файлами сервиса прямо в корне, без лишнего внешнего каталога. После PACKAGE код в этом артефакте не изменяется.
