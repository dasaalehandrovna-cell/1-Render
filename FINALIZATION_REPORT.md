# R68 — Forwarding ingress / Telegram preflight finalization

## Root cause addressed
- The R67 UI could show an explicit forwarding pair while runtime still had independent veto layers.
- `schedule_forward_any_message` could reject delivery through `forward.messages` / `forward.media_groups` permissions even though the edge already existed.
- A stale contour `forward mode off` flag could suppress a persisted edge.
- Owner callback workers could lose thread-local actor/tenant context and fail cross-space pair authorization inconsistently.
- Pair UI did not live-check Telegram endpoint visibility when a pair was opened/toggled.

## R68 behavior
- Explicit stored `forward_rules` are the final runtime delivery authority.
- Runtime forwarding no longer re-checks the V152 forwarding capability once an edge exists.
- R68 logs `forward_ingress_r68` with message id and resolved target count for every delivered Telegram message that reaches forwarding admission.
- Persisted explicit targets auto-heal a stale contour forwarding-mode flag instead of being silently skipped.
- Owner forwarding console remains global even if callback thread-local actor context is absent.
- Opening/toggling a pair performs a live Telegram preflight: `getMe`, `getChat` and self `getChatMember` for group endpoints.
- Pair screen shows whether either chat is unreachable and whether BotFather Group Privacy blocks ordinary group-message ingress.

## Telegram limit
- If `can_read_all_group_messages=false`, Telegram does not deliver ordinary group messages to the bot. This cannot be repaired in application code. `/setprivacy -> Disable` and re-adding the bot to the group are required for existing groups.

## Verification
- FAST finalization gate: 100/100 PASS.
- Python compile: PASS.
- Behavioral forwarding-authority test: PASS (explicit edge dispatch, stale-mode auto-heal, owner cross-space context fallback).
- HEAVY is unchanged from R65/R67 and remains outside this FAST-only patch.
