# Cloudflare Tunnel for remote testing

This guide lets one developer laptop host the chatbot for two remote browser-only testers.

For a consolidated operator runbook (including env template usage and daily start/stop), see [`docs/installation/remote-testing-with-cloudflare.md`](./remote-testing-with-cloudflare.md).

Scenario:
- **P** runs the server and tunnel on a laptop.
- **M/J** only open a web link in their browsers.
- Usage is intermittent, and P can stop everything overnight.

## What runs on P's machine

During a test session, P runs four processes:

1. FastAPI server (`uvicorn`) on localhost
2. Static web client server (`python -m http.server`)
3. Cloudflare Tunnel for API
4. Cloudflare Tunnel for web UI

If any of these stop, remote access is impacted.

## One-time setup

### 1) Install Cloudflare Tunnel client

Install `cloudflared` on P's machine:

- macOS (Homebrew): `brew install cloudflared`
- Or use Cloudflare install instructions for your OS

### 2) Authenticate with Cloudflare

```bash
cloudflared tunnel login
```

This opens a browser so P can authorize the device.

### 3) Create two named tunnels

Create one for the API and one for the web UI:

```bash
cloudflared tunnel create climate-api
cloudflared tunnel create climate-web
```

### 4) Create DNS routes

Assuming a domain in Cloudflare DNS (example: `example.com`):

```bash
cloudflared tunnel route dns climate-api api-chat.example.com
cloudflared tunnel route dns climate-web chat.example.com
```

Now `api-chat.example.com` and `chat.example.com` will point to the tunnels.

### 5) Save tunnel config files

Create config files (paths can vary by OS; `~/.cloudflared/` is common).

Example `~/.cloudflared/climate-api.yml`:

```yaml
tunnel: climate-api
credentials-file: /Users/you/.cloudflared/<API_TUNNEL_UUID>.json
ingress:
  - hostname: api-chat.example.com
    service: http://localhost:8800
  - service: http_status:404
```

Example `~/.cloudflared/climate-web.yml`:

```yaml
tunnel: climate-web
credentials-file: /Users/you/.cloudflared/<WEB_TUNNEL_UUID>.json
ingress:
  - hostname: chat.example.com
    service: http://localhost:8081
  - service: http_status:404
```

## Per-session usage (morning start)

Open terminals and run:

### 1) Start API

From repo root:

```bash
source .venv/bin/activate
export GROQ_API_KEY='YOUR_KEY'
export CLIMATE_API_CORS_ORIGINS='https://chat.example.com'
python -m uvicorn fastapi_app.main:app --host 127.0.0.1 --port 8800
```

### 2) Start web UI

From repo root:

```bash
cd frontend
python -m http.server 8081
```

### 3) Start API tunnel

```bash
cloudflared tunnel --config ~/.cloudflared/climate-api.yml run
```

### 4) Start web tunnel

```bash
cloudflared tunnel --config ~/.cloudflared/climate-web.yml run
```

### 5) Share URL

Give testers only:

- `https://chat.example.com`

The web app should call:

- `https://api-chat.example.com`

## One-command morning start / evening stop

You can use the helper scripts in `scripts/` to run all four services in background:

### Create local env file once

From repo root:

```bash
cp .env.remote-test.template .env.remote-test
```

Edit `.env.remote-test` and set real values (API key + hostnames). This file is gitignored.

### Morning start

From repo root:

```bash
source .venv/bin/activate
source .env.remote-test
bash scripts/start_remote_test.sh
```

What this starts:
- API (`uvicorn`) on `127.0.0.1:8800`
- Web UI (`python -m http.server`) on `127.0.0.1:8081`
- Cloudflare API tunnel
- Cloudflare web tunnel

Runtime files:
- PID files: `.remote-test-runtime/pids/`
- Logs: `.remote-test-runtime/logs/`

### Evening stop

From repo root:

```bash
bash scripts/stop_remote_test.sh
```

This stops all four background processes and removes their PID files.

## Evening shutdown

P can stop everything nightly:

- `Ctrl+C` in each terminal (or stop from a process manager)
- Close laptop if desired

Next morning, restart the same four processes.

## Answers to common operations questions

### Is the server running continuously on P's machine while logged in?

Yes, during active testing the API/web/tunnel processes must keep running. If they are stopped, remote users lose access.

### Can P launch and forget for an evening?

Yes. If P starts all processes and keeps laptop awake/online, M/J can use it for the evening without P actively watching it.

### Does M/J usage keep creating new resources on P's machine?

Usually minimal. Typical chat traffic reuses existing code and index data.

What can change over time:
- App logs
- Temporary runtime cache files
- `chroma_db/` updates if index rebuild/rewrite logic is triggered

For normal testing, M/J are not continuously provisioning new infrastructure; they are using P's existing running process.

## Practical cautions

- Keep the laptop awake (disable sleep for test window).
- Keep terminals open (or use a process manager such as `tmux` later).
- Protect `GROQ_API_KEY` (never commit it).
- If links fail, verify: API process, web process, and both tunnels are still running.
