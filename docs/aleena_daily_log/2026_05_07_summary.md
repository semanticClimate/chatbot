# ALEENA Daily Log

This folder is my day-by-day working log for the `chatbot` project.

I am using it to document:
- what I tested,
- what worked,
- what failed,
- what I changed to fix issues,
- and what I should do next.

## Why this folder exists

I am still learning, so I need a clear trail of what I tried and what I learned each day.  
This helps me avoid repeating the same mistakes and gives the team an honest view of progress.

## Naming format

I will create one file per day in this format:

- `YYYY_MM_DD_summary.md`

Examples:
- `2026_05_07_summary.md`
- `2026_05_08_summary.md`

## Suggested structure for each daily summary

Use this structure so entries stay useful and easy to review:

1. **Context**
   - What I was trying to do that day.
2. **Environment**
   - OS, ports, API URL, frontend URL, branch/folder if relevant.
3. **Smoke tests run**
   - Exact checks performed (health, ready, question tests, etc.).
4. **Problems faced**
   - Error message + when it happened.
5. **Fix applied**
   - What command/change fixed it.
6. **Result**
   - Pass/fail and confidence level.
7. **Follow-ups**
   - Anything still unclear or worth improving later.

## Notes for this project

- Backend (FastAPI) usually runs on `http://127.0.0.1:8800`
- Frontend static client can run on `http://127.0.0.1:8081`
- `GET /health` and `GET /ready` are the first checks before UI testing
- Citation cards are expected and should map to source text from the climate book content

## Personal note

This is intentionally written in plain language so I can read it later and immediately understand what happened.
