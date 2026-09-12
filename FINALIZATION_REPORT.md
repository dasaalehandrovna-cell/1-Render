# R67 — Forwarding + window runtime finalization

## Forwarding
- Explicit stored `forward_rules` are the runtime source of truth. Runtime delivery no longer silently vetoes configured edges through a second `tenant_same_space` filter.
- Chat forwarding permission is sender-independent: owner and ordinary users are treated identically once Telegram delivers the message.
- Two-way A⇄B enable/disable is atomic and persists once, preventing half-configured pairs after a crash/redeploy.
- Forwarding config persistence is root-only instead of a full all-chat save.
- Normal messages, channel posts, edits, albums/media groups, reply mapping, exact-once delivery index, copy→forward→typed-send fallback and finance-copy sync remain wired.
- Full chat probe records `can_read_all_group_messages`; the forwarding menu explicitly warns when BotFather Group Privacy prevents ordinary group messages from reaching the bot.

## Windows
- Compact finance-window restore keeps every persisted latest-per-day pointer instead of collapsing to one selected day.
- Same-day parallel Telegram windows remain owned by the durable open-window registry.
- Back/Main edits only the clicked message and never redirects a transient failure into another sibling window.
- Back, Previous, Info and `/start` reuse obtain the real Telegram edit result in their async lane; missing messages can be recovered immediately.
- Ordinary redraws remain latest-wins/asynchronous.
- Active-window persistence no longer performs the same chat SQLite save twice.

## Verification
- FAST finalization gate: 96/96 PASS.
- HEAVY unchanged gate: 34/34 PASS.
- Behavioral tests PASS: explicit two-way resolution, sender-consistent permission, atomic pair, multi-day window restore, direct critical navigation.
- Full startup import could not be executed in this offline build environment because `pyTelegramBotAPI/telebot` is not installed and package download DNS is unavailable. Static compile/gates and behavior tests passed.
