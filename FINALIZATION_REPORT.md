# FINALIZATION_REPORT — выс-262 / R47 FINALIZED STUCKFIX2

## Source

Finalized from the latest STUCKFIX2 FAST+HEAVY source artifact available in project storage. Wire protocol generation `Пер-R43` is intentionally retained where it is part of the FAST↔HEAVY compatibility barrier; the package release itself is R47 FINALIZED.

## What was flattened

### Telegram ingress

Old active shape contained repeated `process_new_updates` wrappers (`v221 → v219 → v218 → v217 → v162 → TeleBot`). The final shape has one public dispatcher in `89_callback_final.py`; task/command interceptors run once before native TeleBot dispatch.

### Callback extension route

Old observed stack crossed R29/R7/v196/v171/v153 predecessor callbacks. Final route is one `v149_extension_callback` in module 100. Feature handlers are standalone and return `False` when the callback does not belong to them; there is no callback call-through chain.

### Ordinary message route

The runtime wrappers around `on_any_message` for v172/v174 were removed. Their task hooks are inline in the canonical `40_message_router.py::on_any_message`. Permission wrapping skips this non-command catch-all and remains only on command handlers.

### Telegram output

All application-level Telegram send/edit/delete/document/ACK bindings are owned by `89_callback_final.py`. Earlier send/edit wrapper bindings were removed. Runtime export uses a thread-local document transform hook instead of temporarily replacing `bot.send_document`.

### MEGA

One public `_mega_run` validates/sanitizes and calls `_mega_exec_raw`. The previous canonical/original MEGA wrapper chain is removed from the active path.

### FAST↔HEAVY durable transport

R39/R41 durable-outbox semantics were merged into final owners instead of replacing `_r38_*` repeatedly. Diagnostic R44 transport/log monkey-patches were removed; diagnostics now log explicit events only. Outbox thread starts only after final owners are defined.

### HEAVY

R35/R39/R40/R41/R42/R43 `BASE/PREV` process/admission captures were removed from `worker_service.py`. Final R43 owners call named semantic cores directly. Exact job identity, semantic dedup, provisional admission, direct FAST snapshot and compute-slot serialization are retained.

## Memory changes

The supplied Watcher was at 496.5 MB / 512 MB container RAM (97%), Python RSS 431 MB and 74 threads. This build reduces permanently prestarted FAST pool capacity from roughly 45 worker threads to roughly 26 before library/internal helper threads; R45 diagnostic pools are 1+1; Python thread stack is capped at 512 KiB. Journal/trace/event/integrity histories are bounded more aggressively.

Key FAST limits: UI=2, FAST_UI=2, WINDOW_RENDER=2, ACK=1, cleanup=1, delete=1, delta=1, background=1, scheduler=2, R21 heavy-dispatch=2; journal=600; R32 queue=5000; R26 ring=1200; finance integrity history=800.

This is expected to lower steady RSS/thread overhead, but exact production RSS cannot be asserted by static tests because restored chat/state volume and Python allocator fragmentation are deployment-dependent.

## Acceptance after deploy

- No `PREV_PROCESS_NEW_UPDATES`/`ORIGINAL_PROCESS_NEW_UPDATES` in stack traces.
- No R29→R7→v196→v171→v153 fallback callback chain.
- No repeated application Telegram transport wrappers before native TeleBot.
- Threads materially below the previous 74 under the same idle workload.
- Container does not sit at ~97% of 512 MB during READY idle.
- `/internal/state/events` continues to ACK and replay safely.
- Repeated export taps converge on one canonical job; result is delivered once.

## FINALIZATION ONLY

This package passed from PATCH into FINALIZE. Any later code change must start a new PATCH cycle and rerun the gate; do not append a new override layer to this package.
