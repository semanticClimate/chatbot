# Cloudflare tunnels at NIPGR (#21)

Some institutional networks (including NIPGR) block or intercept Cloudflare Quick Tunnel traffic. Symptoms match [issue #21](https://github.com/semanticClimate/chatbot/issues/21): the tunnel URL never loads or TLS fails from campus Wi‑Fi.

## What to try

1. **Confirm local stack works** — on the host machine, open `http://127.0.0.1:8081` (web) and `http://127.0.0.1:8800/docs` (API) before involving Cloudflare.
2. **Use a non-campus network** for the tunnel egress (mobile hotspot, home broadband) while keeping the laptop on the same machine running FastAPI + static web client.
3. **Named Cloudflare tunnel** (account required) instead of Quick Tunnel — see `docs/installation/cloudflare-tunnel-testing.md` if your org allows outbound HTTPS to Cloudflare.
4. **VPN** — only if your institution provides one that does not block `*.trycloudflare.com` or Cloudflare edge IPs.

## What we cannot fix in this repo

- Firewall rules on the NIPGR network
- Proxy MITM on HTTPS without installing trust roots

Document the working URL and network used when you find a path that works, and attach it to issue #21.
