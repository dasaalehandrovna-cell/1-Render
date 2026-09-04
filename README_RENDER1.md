# Render #1 FAST — R13 Event Journal

R13 adds a pre-commit remote Telegram event witness and monotonic operation states `RECEIVED → COMMITTED → MIRRORED`. Normal changes use compact SQLite page deltas. A full database moves from Front only after a rare hash mismatch or explicit deploy/shutdown checkpoint. Worker creates its own periodic checkpoints from the mirrored SQLite.

Recommended cadence: hash reconciliation every 6h, Worker Redis checkpoint every 6h/threshold, MEGA full checkpoint once per 24h.

---

# Render #1 — FAST front — R9.2 RUNTIME CONTRACT FIX

Deploy this ZIP as the Telegram/front service. Start command: `python start_front.py`.

R6 fixes the deploy continuity problem system-wide:
- Full SQLite is still canonical, but a `user_state_shadow_v265` is also persisted in SQLite for all non-financial user state: global/tenant settings, per-chat settings, active windows, modes, Google destination, task/reminder/UI metadata, forwarding/config state and similar control-plane state.
- The shadow is restored inside the BASE `load_data()` before `99_web_runtime.py` can apply factory defaults. This fixes the loader-order bug where the late split module restored settings too late.
- Every successfully handled Telegram update checkpoints current chat/root + user-state shadow + serializable RAM continuity, even if a feature forgot its own save hook.
- Additional interaction sessions (timer input, careful restore, dial/session state, category ordering/sorting, ready exports and UI caches) are included in continuity.
- On rolling deploy, preboot health stays HTTP 200 while the new instance watches worker `cache_revision`; if the old instance publishes a newer final SIGTERM snapshot, the new instance adopts it before starting the bot.
- A stale worker/MEGA snapshot can no longer overwrite a newer local SQLite revision.
- The exact restored/current DB is seeded to shared Redis before normal bot startup. If worker is unavailable, background sync/shutdown also writes the newest snapshot to Redis as a fallback.
- `/` is liveness HTTP 200; `/readyz` remains the strict readiness endpoint.
- Current literal callback audit has zero undeclared marker callbacks, including `v229:tasks:single_window`.

Google service-account JSON must NOT be placed on Render #1.
Use the SAME `REDIS_URL`, `WORKER_REDIS_SNAPSHOT_KEY` and `PEER_SHARED_SECRET` on both services.


## R7 system polish
- finance derived calculations are coalesced after the local SQLite commit;
- deep chat audit moves confirmed left/kicked chats to removed;
- Google setup is a 3-step menu and auto-tests the pasted table;
- CSV/XLSX serialization and Drive upload execute on Render #2.

### R7.1 finance/chat/google cleanup
- Finance mutations commit locally first; duplicate synchronous global rebuilds were removed from add, edit, bulk delete, USD delete, forwarded edits and linked edits.
- Telegram chat audit treats `left`/`kicked` as removed; the first explicit deep `chat not found` becomes removed, while timeout/429 stays temporary/unreachable.
- `/google` is a guided 3-step flow; opening the menu does not synchronously wake the worker just to render status.
- Normal CSV/XLSX serialization and Drive upload are delegated to Render #2. Front keeps only emergency local file fallback if the worker is unavailable; Google OAuth/Drive hooks on Front are blocked.


R8 chat lifecycle fix: for an already-known chat, Telegram 400 `Bad Request: chat not found` during explicit probing is classified immediately as `bot_removed`; the chat moves to the Removed menu. Timeout/429/connection failures remain temporary `unreachable`.

## R9 Google style + concise startup note
- Startup `Бот запущен` shows a short four-line list of the important recent changes.
- Google formatting itself is owned by Render #2 and now matches original vys-262 styling.

## R9.2 runtime-contract correction
- `probe_bot_in_chat` remains canonically owned by `00_core.py`, as required by bot.py runtime contract v223.
- The late override from `98_split_front.py` was removed.
- `left`/`kicked` membership and explicit Telegram `400 chat not found` removal classification now live inside the canonical probe path.
- Manifest hashes are regenerated only after all source edits.

## R10 unified UI / contours / Excel
- Service progress is human-readable; internal W/Ф232/Ф233 ids are hidden from ordinary users.
- All XLSX/Google Sheet outputs use the colored vys-262 financial palette.
- /ok is blocked in contour 1/2; disabled business-mode callbacks return to the mode menu.
- Owner UI has Google Excel and Render #2 health controls; peer health is bidirectional.
- Contour toggles force immediate keyboard redraw after state changes.


## R11 fast finance
Финансовый источник истины остаётся на Render #1: запись сначала фиксируется в локальном SQLite. Производные Gomonk/валютные расчёты выполняются после commit в FINANCE_TASK_POOL, чтобы не блокировать следующие Telegram finance messages. После завершения update полный SQLite асинхронно передаётся Render #2. Для новых чатов журнал чата включён по умолчанию.

## R13 event journal + delta mirror
- Normal changes send only changed SQLite pages to Render #2; repeated `/internal/split/state` full downloads are no longer the normal path.
- Finance durability delta is scheduled immediately after the completed local transaction/update; old 5-second minimum is capped to 1 second for finance/critical changes.
- Full SQLite is used only for deploy shutdown, first/mismatched base, oversized delta or emergency recovery.
- Forwarding allows messages delivered by Telegram from third-party bots. This bot's own messages remain excluded to prevent loops.


## R14 internal configuration
All runtime tuning values (intervals, limits, ports, feature switches and internal Redis key names) are packaged in `runtime_config.py`. Render Environment should contain only credentials, remote addresses and external Telegram/Google/MEGA identifiers. Stale tuning variables left in Render are ignored/overwritten at service startup.

## R15 FAST HOTPATH
- Finance add no longer performs a full-history normalize/dedupe before the local SQLite commit; records/day/balance are updated incrementally and the full normalize runs in FINANCE_TASK_POOL after commit.
- The first finance-window repaint is scheduled directly from the committed record and skips redundant read-normalization while the finalizer is pending.
- Oversized/mismatched deltas never trigger an immediate full upload from the mutation path. Full rebase waits for 5 minutes of inactivity or graceful shutdown/reconcile.
- User-state shadow and RAM continuity are coalesced in background instead of being rebuilt inline after every Telegram update.
- RAW event witness remains before Telegram 200; Worker acknowledges its local fsynced journal quickly and flushes Redis asynchronously with retry.


## R16 FAST FINANCE + ALL COLOR XLSX
See FIXES_R16_FAST_FINANCE_ALL_COLOR_XLSX.txt.

## R17 FAST TERMINAL CHAT + FULL RESTORE
See FIXES_R17_FAST_TERMINAL_CHAT_FULL_RESTORE.txt.

Key rule: Render #1 / FAST must stay responsive. Terminal-chat cleanup is local and event-driven; remote durability and heavy restore/snapshot work remain asynchronous / Render #2.


## R18 INSTANT CALLBACK + EXACT DEPLOY RESTORE
See `FIXES_R18_INSTANT_CALLBACK_EXACT_DEPLOY_RESTORE.txt`.

R18 supersedes the R15 quiet-only full-rebase rule: a delta/hash mismatch now queues an immediate HEAVY-driven full rebase without blocking Telegram. Callback receipt ACK starts before journaling/parsing/durability work, and rolling deploy has a preboot old-front capture plus Redis/Worker freshness arbitration. SIGTERM publishes a fresh restore point before slow legacy/MEGA shutdown work.


## R19 FAST CALLBACK + AUTHORITATIVE RESTORE
See `FIXES_R19_FAST_CALLBACK_AUTHORITATIVE_RESTORE.txt`.

R19 removes the second legacy boot restore on FAST, gives lightweight navigation callbacks their own dedicated FAST UI lane, moves post-update cleanup off the UI lane, fixes the repeated full-state rebase loop by promoting the exact served full snapshot as the next delta baseline, and pauses automatic Google sync cleanly when no target table is configured.

## R20 DURABLE CONFIG + TRUE FAST LANE
See `FIXES_R20_DURABLE_CONFIG_FAST_LANE.txt`.

R20 restores the original выс-262 principle of an independent monotonic settings checkpoint, but routes its durable storage to HEAVY/Redis/MEGA. FAST only schedules the checkpoint after the local config generation changes. Heavy export/file actions are excluded from the FAST navigation lane.
