# R65 — Priority navigation, isolated chat probe, all-MEGA manual recovery

## FAST/UI
- Safe navigation (`Назад`, `Инфо`, `Главное`, close/page/list navigation) uses dedicated `nav-ui` pool.
- Per-window navigation epoch prevents an older slow callback/render from repainting over a newer navigation result.
- Telegram callback admission/ACK remains fast and separate from render.

## Chat probe
- Full chat check performs Telegram network I/O in a bounded pool (`CHAT_PROBE_WORKERS`, default 4, range 2..6).
- Network workers do not mutate/persist the central state.
- Results are merged locally after network completion.
- Persistence is targeted to checked chats + owner and deferred until interactive callback/nav/render queues are idle.
- The old full `save_data(data)` from the probe path is removed.

## Manual MEGA recovery
- FAST may keep `MEGA_ENABLED=0`.
- `Настройки после деплоя -> Базы MEGA / восстановление` browses the whole MEGA account through authenticated FAST -> HEAVY HTTP.
- HEAVY lists only the current folder with `mega-ls -l`; folder navigation is paged in Telegram.
- Selected files are downloaded through HEAVY, validated as gzip/raw SQLite with `PRAGMA quick_check`, then replace the live DB only after explicit confirmation.
- After successful selected restore FAST seals a verified full SQLite snapshot into Redis (R64 recovery contract).
- Automatic HEAVY MEGA backup/restore remains strictly locked to Render `MEGA_BACKUP_DIR`; the whole-account browser is manual read-only recovery access only.

## Finalization
- No PREV/ORIG/BASE compatibility chain added.
- FAST finalization gate includes explicit R65 contracts.
- Release manifest hashes refreshed after all runtime edits.
