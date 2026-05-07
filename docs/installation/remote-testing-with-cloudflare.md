# Remote testing with Cloudflare Tunnel (P, M, J)

This runbook is a consolidated guide for the scenario:

- **P** (developer) runs the app on a laptop with the project code.
- **M/J** are remote, non-technical testers with only a browser.
- Testing is light/intermittent; P starts in the morning and stops at night.

## What this setup does

P runs the API and web UI locally, then exposes both through Cloudflare Tunnel with public HTTPS URLs.

- M/J open only the web URL in their browsers.
- No app deployment to a cloud VM is required for this test phase.
- P can stop everything overnight and restart next day.

## Requirements

- Local repo checked out on P's laptop
- Python env ready (`.venv`)
- `GROQ_API_KEY` available
- `cloudflared` installed
- A domain managed in Cloudflare DNS (recommended for stable hostnames)

## Pick your hostnames

Choose two DNS hostnames in your Cloudflare domain:

- Web UI hostname (example): `chat.example.com`
- API hostname (example): `api-chat.example.com`

These are your real values for environment variables and tunnel configs.

## One-time Cloudflare setup

### 1) Install and login

```bash
brew install cloudflared
cloudflared tunnel login
```

### 2) Create tunnels

```bash
cloudflared tunnel create climate-api
cloudflared tunnel create climate-web
```

### 3) Route DNS records

```bash
cloudflared tunnel route dns climate-api api-chat.example.com
cloudflared tunnel route dns climate-web chat.example.com
```

### 4) Create tunnel config files

`~/.cloudflared/climate-api.yml`

```yaml
tunnel: climate-api
credentials-file: /Users/you/.cloudflared/<API_TUNNEL_UUID>.json
ingress:
  - hostname: api-chat.example.com
    service: http://localhost:8800
  - service: http_status:404
```

`~/.cloudflared/climate-web.yml`

```yaml
tunnel: climate-web
credentials-file: /Users/you/.cloudflared/<WEB_TUNNEL_UUID>.json
ingress:
  - hostname: chat.example.com
    service: http://localhost:8080
  - service: http_status:404
```

## Local env template (already added in repo)

Copy once from repo root:

```bash
cp .env.remote-test.template .env.remote-test
```

Then edit `.env.remote-test` with real values:

```bash
export GROQ_API_KEY='REPLACE_WITH_REAL_KEY'
export CLIMATE_API_CORS_ORIGINS='https://chat.example.com'
export CLIMATE_PUBLIC_CHAT_URL='https://chat.example.com'
```

Notes:
- `CLIMATE_API_CORS_ORIGINS` must be the browser UI origin(s).
- `CLIMATE_PUBLIC_CHAT_URL` is used by the start script for friendly output.
- `.env.remote-test` is gitignored.

## Daily operation

### Morning start

From repo root:

```bash
source .venv/bin/activate
source .env.remote-test
bash scripts/start_remote_test.sh
```

This starts 4 background processes:
- FastAPI API server (`127.0.0.1:8800`)
- Static web server (`127.0.0.1:8080`)
- Cloudflare API tunnel
- Cloudflare web tunnel

Runtime files:
- Logs: `.remote-test-runtime/logs/`
- PIDs: `.remote-test-runtime/pids/`

### Share with testers

Send M/J only:

- `https://chat.example.com`

### Evening stop

From repo root:

```bash
bash scripts/stop_remote_test.sh
```

## Operational answers

### Is the server running continuously on P's machine while P is logged in?

Yes. Remote access works only while local processes are running (API/web/tunnels).

### Can P launch-and-forget for an evening?

Yes. If laptop stays awake/online and processes remain running, M/J can use it without active supervision.

### Does M/J usage continuously create resources on P's machine?

Not usually. Typical effects are:
- log growth,
- temporary runtime caches,
- possible `chroma_db/` updates if indexing logic is triggered.

No continuous cloud infrastructure provisioning occurs from normal tester usage.

## Troubleshooting quick checks

- Confirm API: `curl http://127.0.0.1:8800/health`
- Check process logs in `.remote-test-runtime/logs/`
- Verify both `cloudflared` tunnels are running
- Re-check `CLIMATE_API_CORS_ORIGINS` matches exact UI origin

## Related docs

- `docs/installation/cloudflare-tunnel-testing.md`
- `docs/installation/installation-architecture.md`
