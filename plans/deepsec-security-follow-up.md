# DeepSec Security Follow-up Plan

Date: 2026-06-28

## #1 Review `.env.example` secret placeholders

DeepSec fast scan found 4 `env-exposure` candidates in `.env.example`:

- `SMTP_PASSWORD=your_app_password_here`
- `WG_API_KEY=your_wireguard_api_key_here`
- `TAILSCALE_API_KEY=your_tailscale_api_key_here`
- `TAILSCALE_WEBHOOK_KEY=your_tailscale_webhook_key_here`

These look like placeholders, not confirmed leaked secrets, but this repo is public and handles VPN/Tailscale/WireGuard automation, so keep the plan explicit.

Repair checklist:

1. Confirm no real secrets exist in tracked history.
2. Keep `.env.example` values obviously fake; consider using empty values plus comments instead of `*_here` strings if scanners keep flagging them.
3. Ensure `.env`, local config, token dumps, logs, and generated state files are ignored.
4. Add or verify secret scanning before future pushes.
5. Run full DeepSec AI processing when gateway auth is restored; current result is matcher-only.
