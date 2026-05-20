# Installation Troubleshooting & Fixes

This document tracks the technical issues encountered while setting up the Semantic Climate chatbot (specifically the Cloudflare Quick Tunnel environment) and the corresponding solutions applied.

## 1. Git Pull Overwrite Error
- **Issue**: Running `git pull` failed with the error: `Your local changes to the following files would be overwritten by merge`.
- **Cause**: Uncommitted changes in `climate_streamlit/api_server.py` and `climate_streamlit/app.py` conflicted with incoming remote changes.
- **Fix**: 
  1. Ran `git stash` to save local modifications.
  2. Ran `git pull` to successfully update the local repository.
  3. Ran `git stash pop` to re-apply the local changes on top of the updated code.

## 2. Missing `cloudflared` Dependency
- **Issue**: The script `start-quick-tunnel.ps1` failed with the error: `cloudflared not found in PATH`.
- **Fix**:
  - Installed the Cloudflare daemon using the Windows Package Manager: `winget install --id Cloudflare.cloudflared`.
  - Updated the script to automatically search common installation paths (like `C:\Program Files (x86)\cloudflared`) and append them to the session `$env:PATH` if missing.

## 3. PowerShell Encoding & Parser Errors
- **Issue**: Syntax errors like `Missing closing ')' in expression` occurred when running `start-quick-tunnel.ps1`.
- **Cause**: The script contained non-ASCII characters (e.g., `…`, `·`, `—`) which caused parsing failures in Windows PowerShell when interpreted as different encodings.
- **Fix**: Replaced all special characters with standard ASCII equivalents (e.g., replaced `…` with `...`).

## 4. Quoting Issues with Paths Containing Spaces
- **Issue**: Commands failed with errors like `out-file : The process cannot access the file 'W:\Semantic' because it is being used by another process`.
- **Cause**: `Start-Process -Command` was stripping double quotes from the command string, causing paths like `W:\Semantic Climate` to be truncated at the first space.
- **Fix**: Updated the script to use `-EncodedCommand` with a Base64-encoded version of the command string. This ensures that the entire command, including spaces and internal quotes, is preserved exactly as intended.

## 5. Virtual Environment Naming Conflict
- **Issue**: The script failed with `Missing venv activate script` because it was looking for a `.venv/` directory.
- **Cause**: The project was using the directory name `venv/` instead of the hardcoded `.venv/`.
- **Fix**: Updated `start-quick-tunnel.ps1` to check for both `venv/` and `.venv/` activation paths.

## 6. Read-Only Variable Conflict in Stop Script
- **Issue**: `stop-quick-tunnel.ps1` failed with `VariableNotWritable` when trying to set the `$pid` variable.
- **Cause**: `$pid` is an automatic, read-only variable in PowerShell that refers to the current process ID.
- **Fix**: Renamed the local variable in the script from `$pid` to `$procId` to avoid the naming collision.

## 7. Missing API Key in Session
- **Issue**: The script threw an error if the `GROQ_API_KEY` was not manually exported in the terminal session.
- **Fix**: Added logic to the start script to automatically detect and load the API key from the `venv/.env` file if it is not already present in the environment variables.
