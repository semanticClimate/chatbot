# Cloudflare Installation & Semantic Climate Chatbot Setup Guide

## Overview

This guide explains how to fully set up the Semantic Climate Chatbot locally and expose both backend and frontend using Cloudflare Quick Tunnels.

You will use **4 terminals**:

* **Terminal 1:** FastAPI Backend
* **Terminal 2:** Frontend Web Client
* **Terminal 3:** Cloudflare Tunnel for Backend
* **Terminal 4:** Cloudflare Tunnel for Frontend

---

# Branch Version Notice

This setup guide is based on the **server GitHub branch** version being worked on as of **May 8, 2026**.

If newer commits significantly modify project structure, commands, or deployment flow, some steps may require adjustment.

---

# Cloudflared Installation Setup (Windows)

Before creating tunnels, install Cloudflare Tunnel globally.

## Installation Steps:

Open **Command Prompt (CMD)** and run:

```powershell
winget install --id Cloudflare.cloudflared
```

---

## Important:

After installation:

* Restart your system completely
* Do NOT just open another CMD window

A full restart helps ensure system PATH updates correctly.

---

## Verify Installation:

After restarting, open CMD or terminal and run:

```powershell
cloudflared --version
```

If installed correctly, Cloudflare version details will appear.

---

# Prerequisites

Before starting, ensure you have:

* Python installed
* VSCode / Cursor / Antigravity
* `cloudflared` installed
* Project files downloaded
* GROQ API Key

---

# STEP 1 — Open Project in VSCode / Cursor / Antigravity

Open your project folder:



Then:

**View → Terminal**

---

# STEP 2 — Terminal 1 (Backend Setup)

Navigate to project root:

```powershell
cd chatbot
```

Run these commands one by one:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
$env:GROQ_API_KEY="gsk_your_api_key"
$env:CLIMATE_API_CORS_ORIGINS="*"
python -m uvicorn fastapi_app.main:app --host 127.0.0.1 --port 8800
```

---

## Copy-Paste Version:

```powershell
python -m venv .venv

.venv\Scripts\Activate.ps1

pip install -r requirements.txt

$env:GROQ_API_KEY="gsk_your_api_key"

$env:CLIMATE_API_CORS_ORIGINS="*"

python -m uvicorn fastapi_app.main:app --host 127.0.0.1 --port 8800
```

---

## Expected Result:

Backend will run at:

```txt
http://127.0.0.1:8800
```

If this appears, Terminal 1 is working correctly.

---

# STEP 3 — Terminal 2 (Frontend Setup)

Click the **+ icon** in terminal panel to open a new terminal.

---

## Check Virtual Environment

If `(.venv)` is visible, continue.

If not, run:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

---

## Navigate to Web Client:

```powershell
cd web_client
```

Then run:

```powershell
python -m http.server 8081
```

---

## Expected Result:

Frontend will generate:

```txt
http://[::]:8081/
```

Use instead:

```txt
http://127.0.0.1:8081/
```

---

## Test Frontend:

Open browser and verify frontend loads.

If chatbot responds to queries, setup is functioning properly.

---

# STEP 4 — Terminal 3 (Cloudflare Tunnel for Backend)

Open a new terminal.

Navigate to:

```powershell
cd docs\installation
```

Run:

```powershell
cloudflared tunnel --url http://127.0.0.1:8800 --no-autoupdate
```

---

## Expected Result:

Cloudflare generates:

```txt
Your quick Tunnel has been created! Visit it at:
https://random-backend-url.trycloudflare.com
```

**Copy this backend URL.**

---

# STEP 5 — Terminal 4 (Cloudflare Tunnel for Frontend)

Open another terminal.

Navigate to:

```powershell
cd docs\installation
```

Run:

```powershell
cloudflared tunnel --url http://127.0.0.1:8081 --no-autoupdate
```

---

## Expected Result:

Cloudflare generates:

```txt
Your quick Tunnel has been created! Visit it at:
https://random-frontend-url.trycloudflare.com
```

Open this frontend tunnel link.

---

# STEP 6 — Configure API Base URL

When frontend opens:

* Locate **API Base URL** field
* Paste the **backend Cloudflare tunnel URL** from Terminal 3

Example:

```txt
https://random-backend-url.trycloudflare.com
```

---

# STEP 7 — Final Test

Ask chatbot a question.

If everything is configured properly:

* Frontend works
* Backend responds
* Cloudflare tunnels connect externally

---

# Common Errors & Fixes

## 1. Invalid API Key

Error:

```txt
AuthenticationError / 401 Invalid API Key
```

### Fix:

Ensure:

```powershell
$env:GROQ_API_KEY="your_actual_key"
```

---

## 2. Virtual Environment Missing

### Fix:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

---

## 3. Cloudflared Not Found

### Fix:

Install Cloudflare Tunnel:

```powershell
winget install --id Cloudflare.cloudflared
```

---

## 4. Frontend Not Connecting to Backend

### Fix:

* Confirm backend tunnel URL is pasted correctly
* Ensure Terminal 1 is still running
* Ensure Terminal 3 is still active

---

# Security Warning

## NEVER share:

* GROQ API Key
* `.env` files
* Terminal screenshots containing secret keys
* Public videos exposing credentials

If recording setup videos, blur or hide:

```txt
$env:GROQ_API_KEY
```

---

# Full Terminal Summary

| Terminal   | Purpose         | Command                                                          |
| ---------- | --------------- | ---------------------------------------------------------------- |
| Terminal 1 | Backend         | `uvicorn fastapi_app.main:app`                                   |
| Terminal 2 | Frontend        | `python -m http.server 8081`                                     |
| Terminal 3 | Backend Tunnel  | `cloudflared tunnel --url http://127.0.0.1:8800 --no-autoupdate` |
| Terminal 4 | Frontend Tunnel | `cloudflared tunnel --url http://127.0.0.1:8081 --no-autoupdate` |

---

# Final Notes

Once complete:

* Local chatbot runs
* Frontend accessible online
* Backend accessible online
* Others can test remotely using Cloudflare links

---

# Pro Tip

If something breaks:

* Check which terminal failed
* Restart only that terminal
* Avoid restarting everything unless necessary

This saves a ridiculous amount of time.
