# PROJECT_RULES — выс-262 / R47 FINALIZED

## Неподвижное правило релиза

`PATCH → FINALIZE → TEST → PACKAGE`

После начала FINALIZE нельзя добавлять ещё один compatibility/override слой. Любое новое изменение возвращает работу в PATCH, после чего FINALIZE и TEST выполняются заново.

## FINALIZATION ONLY

1. Один публичный владелец каждого hot-path действия.
2. Нельзя оборачивать финальный runtime через `PREV/ORIG/BASE` цепочку ради новой правки.
3. Нельзя временно перепривязывать `bot.send_*`, `bot.edit_*`, `bot.delete_message`, `bot.process_new_updates`.
4. Нельзя перепривязывать hot-path функции через `globals()[name] = ...`; финальный владелец объявляется напрямую.
5. Compatibility допустима только как чтение старого формата данных/ключа. Compatibility не должна быть исполняемой цепочкой вызовов.
6. FAST: webhook, ACK, callback/UI, короткие локальные транзакции, durable outbox. FAST не строит тяжёлые архивы/Excel/полные SQLite snapshots по пользовательскому callback.
7. HEAVY: export/archive/Google/MEGA/full-state/SQLite-heavy work. Telegram UI не переносится на HEAVY.
8. `job_id` неизменяем. Повторная доставка того же job — idempotent/deduplicated; неоднозначная ошибка Telegram не разрешает слепую повторную отправку готового результата.
9. `POST /internal/state/events` остаётся подтверждаемым транспортом состояния; отказ/перезапуск HEAVY не должен блокировать Telegram hot path.
10. Перед упаковкой обязательны compile, FINALIZATION_GATE, manifest hash check и ZIP CRC test.

## RAM / threads budget FAST

- Python thread stack: 512 KiB.
- UI / FAST-UI / window render: по 2 workers.
- callback ACK, cleanup, delete, delta, background: по 1 worker.
- scheduler: 2 workers.
- diagnostic pools: по 1 worker.
- журнал, trace и event rings всегда bounded.
- При emergency RAM запрещено создавать тяжёлый export на FAST.

## Запрет на «патч поверх патча»

Если исправление требует заменить функцию, изменяется её канонический владелец. Новый wrapper поверх старого владельца не создаётся. Исключение — отдельный семантический core, который вызывается напрямую единственным публичным владельцем и не перепривязывает себя обратно.
