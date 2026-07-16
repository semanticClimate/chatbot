# Temporary VPS hosting runbook (~1 month)

This guide replaces **Cloudflare Quick Tunnels** (`trycloudflare.com` URLs that change) with a **small always-on VPS** and **stable hostnames** until a permanent server is ready.

It is written for developers who are comfortable with code but **rusty on bash**: commands are copy-paste oriented, and a long one-off setup is expected.

**Related docs (local / tunnel testing):**

- [macOS quick tunnel runbook](mac-quick-tunnel-runbook.md)
- [Windows quick tunnel runbook](windows-quick-tunnel-runbook.md)
- [Remote testing with Cloudflare](remote-testing-with-cloudflare.md)

---

## What you are hosting (this repo)

| Service | How it runs locally today | Port |
|---------|---------------------------|------|
| **API** | `uvicorn fastapi_app.main:app` | `8800` |
| **Web UI** | Static files in `web_client/` (`python -m http.server` in quick-tunnel scripts) | `8081` |
| **Secret** | `GROQ_API_KEY` in the environment (never commit) | — |

Quick tunnels write `web_client/tunnel-api-base.txt` so Team B’s browser knows the API URL. On a VPS you replace that with a **fixed** file (see [Permanent API URL for the web UI](#permanent-api-url-for-the-web-ui)).

---

## Goals and constraints

| Requirement | Approach |
|-------------|----------|
| **Stable public URL** | Fixed VPS IP + DNS (or provider subdomain) |
| **~1 month, low cost** | Oracle Always Free ($0) or Hetzner CX22 (~€4–5) |
| **Performance optional** | Smallest VM is fine |
| **Easy edits / fast reboot** | `git pull` + `docker compose up -d --build` or `systemctl restart` (2–3 min) |
| **Easy cancellation** | **Delete the VM** in the provider console — not a SaaS “subscription” |
| **Month-by-month OK** | Leave the VM running and pay the next invoice, or delete when done |
| **Docker optional** | Compose path below; no Docker Hub account required |

---

## Provider comparison

### Cheap / free options (stable URL)

| Option | Cost | Stable URL | Cancel / stop paying |
|--------|------|------------|----------------------|
| **Oracle Cloud Always Free** | $0 | Your IP + DNS | Delete VM |
| **Hetzner Cloud CX22** (or smallest) | ~€4–5/month usage invoice | Your IP + DNS | Delete server in console |
| **Vultr / DigitalOcean** | Similar; often hourly | Your IP + DNS | Destroy droplet |
| **Fly.io / Railway** | Card + usage / hobby credit | `*.fly.dev`, `*.railway.app` | Account / service delete |

**Recommendation:** Try **Oracle free** first if $0 matters (budget 2–3 hours for signup/quotas). If that blocks you, use **Hetzner CX22** the same day for predictable setup.

### Billing: “one-off” vs subscription

VPS providers are **not** Netflix-style monthly plans:

- You add a card and get **invoices for resources that existed** that month.
- **Cancellation = delete the server.** No separate “cancel subscription” step on Hetzner/DO/Vultr.
- **Renew month-by-month:** do nothing; the VM keeps running until you delete it.

### Options that are usually a poor fit here

| Option | Why skip |
|--------|----------|
| **ngrok free** | Unstable or limited fixed URLs |
| **Tailscale Funnel** | Fine for internal testers; awkward for “browser only” Team B |
| **PythonAnywhere free** | Awkward for FastAPI/uvicorn |
| **Glitch / Render free** | Sleeps; bad for always-on API |

### Named Cloudflare Tunnel (alternative)

If the pain is **changing URLs**, not tunnels themselves: keep Cloudflare but use a **named tunnel** + your domain (`api.example.com`, `chat.example.com`) pointing at any always-on host. Still “tunnel messy” if the origin is a laptop; better once the origin is the VPS.

---

## Architecture (one VPS, two URLs)

```text
Internet
   │
   ▼
┌─────────────────────────────────────┐
│  VPS (Hetzner or Oracle)            │
│  Caddy (HTTPS, optional)            │
│    chat.example.com  → :8081 web    │
│    api.example.com   → :8800 API    │
│  Docker: api + web containers       │
│  (or systemd + venv instead)        │
└─────────────────────────────────────┘
```

Team B opens **`https://chat.yourdomain.com`**. The UI loads the API base from `api-base.txt` (or `tunnel-api-base.txt` via symlink).

---

## Docker and Docker Hub

**You do not need a Docker Hub sign-up** for this setup.

- **Docker Hub limits** apply when pulling many images from `hub.docker.com` as an anonymous user.
- This runbook **builds the API image on the server** from the repo (`docker compose build`) — image stays on the VM.
- The web service uses `nginx:alpine` (one pull per VM; rate limits are rare in practice).
- If pull fails, use **Path A (no Docker)** below.

**Docker Engine** on the VPS is free. No Docker “subscription.”

---

## Path A vs Path B

| | **Path A: No Docker (systemd)** | **Path B: Docker Compose** |
|---|--------------------------------|----------------------------|
| **After code change** | `git pull` && `sudo systemctl restart chatbot-api chatbot-web` | `git pull` && `docker compose up -d --build` |
| **Day-to-day** | More files (units, venv paths) | Fewer moving parts once compose works |
| **Artifacts in repo** | systemd units in this doc | [vps/docker-compose.yml](vps/docker-compose.yml), [vps/Dockerfile.api](vps/Dockerfile.api) |

For rusty bash after the first day, **Path B (Docker Compose)** is often easier.

---

## Phase 0 — Before the server

1. **Domain (recommended):** Two DNS **A** records pointing at the VPS public IPv4:
   - `api.yourdomain.com`
   - `chat.yourdomain.com`  
   You can skip DNS at first and use `http://YOUR_IP:8081` (still stable while the VM exists).

2. **Create the VM**
   - **Hetzner:** Cloud Console → project → payment method → **Create server** — Ubuntu 24.04 LTS, smallest CX, your SSH key. Note **public IPv4**.
   - **Oracle:** Always Free ARM or AMD VM in your home region; open ports 22, 80, 443 in the security list / `ufw` later.

3. **Cancellation:** When the permanent server is ready → provider console → **Delete** the VM.

---

## Phase 1 — First login

On your Mac (or Windows with OpenSSH):

```bash
ssh root@YOUR_VPS_IP
```

On the server:

```bash
apt update && apt upgrade -y
apt install -y git docker.io docker-compose-v2
systemctl enable --now docker
```

Optional: non-root deploy user:

```bash
adduser deploy
usermod -aG docker deploy
# Log in as: ssh deploy@YOUR_VPS_IP
```

Firewall (allow SSH, HTTP, HTTPS):

```bash
apt install -y ufw
ufw allow OpenSSH
ufw allow 80/tcp
ufw allow 443/tcp
ufw enable
```

---

## Phase 2 — Clone repo and secrets

```bash
cd ~
git clone https://github.com/YOUR_ORG/chatbot.git
cd chatbot
```

Create `.env` on the server only (never commit):

```bash
nano .env
```

Example:

```bash
GROQ_API_KEY=gsk_your_key_here
CLIMATE_API_HOST=0.0.0.0
CLIMATE_API_PORT=8800
```

Save in nano: `Ctrl+O`, Enter, `Ctrl+X`.

### Permanent API URL for the web UI

The quick-tunnel flow writes `web_client/tunnel-api-base.txt`. On the VPS, set a **fixed** API base once.

**Option 1 — symlink (no app code change):**

```bash
echo 'https://api.yourdomain.com' > web_client/api-base.txt
ln -sf api-base.txt web_client/tunnel-api-base.txt
```

**Option 2 — only `tunnel-api-base.txt`:**

```bash
echo 'https://api.yourdomain.com' > web_client/tunnel-api-base.txt
```

Use `http://YOUR_VPS_IP:8800` until HTTPS and DNS are ready; then update the file and restart the web container or nginx.

---

## Phase 3 — Path B: Docker Compose

Copy or use the checked-in files under [vps/](vps/):

```bash
cd ~/chatbot
# Files: docs/installation/vps/docker-compose.yml → repo root, or:
cp docs/installation/vps/docker-compose.yml .
cp docs/installation/vps/Dockerfile.api .
```

Start:

```bash
docker compose up -d --build
docker compose ps
curl -s http://127.0.0.1:8800/docs | head
```

Open in a browser (after DNS or via IP): `http://YOUR_VPS_IP:8081` (map host ports in compose if you expose 8081 publicly before Caddy).

**Daily reboot / deploy after edits:**

```bash
cd ~/chatbot
git pull
docker compose up -d --build
```

Expect **2–3 minutes**.

---

## Phase 4 — HTTPS with Caddy

Install Caddy on Ubuntu:

```bash
apt install -y debian-keyring debian-archive-keyring apt-transport-https curl
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' | tee /etc/apt/sources.list.d/caddy-stable.list
apt update && apt install -y caddy
nano /etc/caddy/Caddyfile
```

Example (API and web reverse-proxied to localhost services from compose):

```caddy
api.yourdomain.com {
    reverse_proxy 127.0.0.1:8800
}

chat.yourdomain.com {
    reverse_proxy 127.0.0.1:8081
}
```

```bash
systemctl reload caddy
```

Update `web_client/api-base.txt` (or symlink target) to `https://api.yourdomain.com`, then restart web if needed:

```bash
cd ~/chatbot
docker compose restart web
```

Team B uses: **`https://chat.yourdomain.com`**

---

## Path A: No Docker (systemd + venv)

```bash
apt install -y python3.11-venv
cd ~/chatbot
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

**API unit** — `/etc/systemd/system/chatbot-api.service`:

```ini
[Unit]
Description=Climate chatbot FastAPI
After=network.target

[Service]
Type=simple
User=deploy
WorkingDirectory=/home/deploy/chatbot
EnvironmentFile=/home/deploy/chatbot/.env
ExecStart=/home/deploy/chatbot/.venv/bin/python -m uvicorn fastapi_app.main:app --host 0.0.0.0 --port 8800
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

**Web unit** — `/etc/systemd/system/chatbot-web.service`:

```ini
[Unit]
Description=Climate chatbot static web UI
After=network.target

[Service]
Type=simple
User=deploy
WorkingDirectory=/home/deploy/chatbot/web_client
ExecStart=/home/deploy/chatbot/.venv/bin/python -m http.server 8081 --bind 127.0.0.1
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

Enable and start:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now chatbot-api chatbot-web
sudo systemctl status chatbot-api chatbot-web
```

After `git pull`:

```bash
source .venv/bin/activate && pip install -r requirements.txt
sudo systemctl restart chatbot-api chatbot-web
```

Use the same [Caddy](#phase-4--https-with-caddy) block; bind API/web on `127.0.0.1` as above.

---

## Oracle vs Hetzner (quick choice)

| | **Oracle Always Free** | **Hetzner CX22** |
|---|------------------------|------------------|
| **Cost** | $0 | ~€4–5 for the month |
| **Cancel** | Delete VM | Delete server |
| **Setup** | Higher (signup, quotas, VCN/firewall) | Lower |
| **Card** | Often verification only | Required |
| **Best when** | $0 is worth signup friction | You want it working the same day |

---

## Suggested plan

1. Try **Oracle free** VM (2–3 hour budget). If blocked, create **Hetzner CX22**.
2. Use **Path B: Docker Compose + Caddy** (or Path A systemd if you prefer no Docker).
3. Point **two DNS names** at the VM; set **`api-base.txt`** or symlink to `tunnel-api-base.txt`.
4. Keep [quick tunnel scripts](start-quick-tunnel.sh) for **local dev only**.
5. Calendar reminder: **delete the VM** when the permanent server is live.

---

## Checklist

- [ ] VPS created; SSH works
- [ ] `ufw` (or cloud firewall): 22, 80, 443
- [ ] Repo cloned; `.env` with `GROQ_API_KEY`
- [ ] API responds on `127.0.0.1:8800`
- [ ] Web UI on `127.0.0.1:8081`; `tunnel-api-base.txt` or symlink points at API URL
- [ ] DNS A records → VPS IP
- [ ] Caddy HTTPS for `api.` and `chat.` hostnames
- [ ] Team B tested in browser (no Quick Tunnel URLs)
- [ ] Reminder to delete VM after migration

---

## Troubleshooting

| Symptom | Things to check |
|---------|-----------------|
| Browser can’t reach API | `curl http://127.0.0.1:8800/docs` on server; Caddyfile hostnames; `api-base.txt` uses `https://` after Caddy |
| 502 from Caddy | `docker compose ps` or `systemctl status chatbot-api`; API listening on `127.0.0.1:8800` |
| UI shows tunnel hint errors | `web_client/tunnel-api-base.txt` missing or wrong; recreate symlink |
| Docker build fails | `pip install` errors in build log; ensure `requirements.txt` at repo root |
| Oracle: no SSH | Security list ingress port 22; correct public IP |

---

## Files in this folder

| File | Purpose |
|------|---------|
| [vps/docker-compose.yml](vps/docker-compose.yml) | API + nginx static web (copy to repo root on server) |
| [vps/Dockerfile.api](vps/Dockerfile.api) | Build API image locally on VPS (no Docker Hub) |
