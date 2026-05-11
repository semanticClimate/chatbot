# Session summary — Quick tunnels, scripts, and Eduroam (2026-05-11)

Date: **2026-05-11** (workspace context).

This note captures **Cloudflare Quick Tunnel** troubleshooting, **script fixes**, and why **Eduroam** explains “works at home on the weekend, fails on campus.”

---

## Symptom: wrong or empty public URLs

Both tunnels printed **`https://api.trycloudflare.com`** — that host is Cloudflare’s **registration API**, not your randomized quick-tunnel URL. It appears in error lines such as:

`Post "https://api.trycloudflare.com/tunnel": context deadline exceeded …`

**Fix (in repo):** `docs/installation/start-quick-tunnel.sh` (and PowerShell / runbook snippets) **exclude** `https://api.trycloudflare.com` when grepping for public URLs, so only **`https://<random>.trycloudflare.com`** counts.

---

## Symptom: script looked hung or crashed

- **Sequential waits** (API log then web log) made worst-case waits very long with no feedback.
- **`set -u`:** referencing unset `QUICK_TUNNEL_URL_TIMEOUT_SECONDS` or unset `ApiPublic` after `read` caused **unbound variable** exits mid-run.
- **Progress:** combined polling of both tunnel logs, **stderr lines every ~10s**, **seconds left** in the line.

**Fixes:** parallel wait for both URLs; `QuickTunnelDeadlineSeconds="${QUICK_TUNNEL_URL_TIMEOUT_SECONDS:-300}"`; initialize `ApiPublic`/`WebPublic` before `read`; end-of-script **local** URL list + **`curl` `/health`** so you can see the API is up even when tunnels fail.

---

## Symptom: “consistent timeout” / full wait when registration already failed

Waiting the full deadline when **both** logs already show **`failed to request quick Tunnel`** rarely helps.

**Fixes:**

- Default **max wait** **`QUICK_TUNNEL_URL_TIMEOUT_SECONDS=300`** (bash + PowerShell), overridable (e.g. `600`).
- **`QUICK_TUNNEL_EARLY_EXIT_SECONDS=90`** (default): if **both** tunnel logs contain the registration failure string, **neither** URL has appeared, and **≥90s** elapsed → **stop waiting** and print a clear message. Set **`QUICK_TUNNEL_EARLY_EXIT_SECONDS=0`** to always wait the full max.

---

## Is Cloudflare simply overloaded?

**Possible, but not the only explanation.** Timeouts to `api.trycloudflare.com` mean “no timely response on **your path** to that host,” which includes Cloudflare load **and** campus firewalls, proxies, DNS, and TLS policies.

---

## Eduroam vs home Wi‑Fi

You confirmed use of **Eduroam** (not home). That aligns strongly with:

- **`failed to request quick Tunnel`** / client timeouts registering quick tunnels  
- **Same machine fine over the weekend** on a different network  

Campus networks often restrict or shape traffic that anonymous quick tunnels need (HTTPS to **`api.trycloudflare.com`**, then persistent outbound tunnel sessions).

**Practical mitigations:** phone hotspot or home network for demos; ask IT about allowlisting; or move toward **named tunnels + DNS** (`docs/installation/remote-testing-with-cloudflare.md`) if policy allows.

---

## Files touched (tunnel / install docs)

- `docs/installation/start-quick-tunnel.sh` — URL parsing, waits, early exit, `set -u`, health echo  
- `docs/installation/start-quick-tunnel.ps1` — parity  
- `docs/installation/mac-quick-tunnel-runbook.md` — troubleshooting + env tuning  
- `docs/installation/windows-quick-tunnel-runbook.md` — same  

---

## Related (same repo day, different topic)

Multilingual chat + Team B deploy handoff lives in **`docs/deploy/team-b-multilingual-release-2026-05-11.md`** and earlier commits on branch `server` (prompt + `web_client/js/examples.js`, etc.).

The separate summary **`docs/summary/2026-05-11.md`** documents the **Groq `rate_limit`** user-facing message (not Cloudflare tunnels).
