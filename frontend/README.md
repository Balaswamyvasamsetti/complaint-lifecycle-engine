# Executive Control Plane Frontend

This folder contains the **Complaint Lifecycle Engine Frontend** UI.

## Structure
* `index.html`: The interactive single-page dashboard.
  * Clean, high-contrast **white background** theme.
  * Interactive business workspace:
    * Ingest & AI Triage new complaints
    * Complaint queue with multi-filter search (priority, status, query)
    * Real-time Operations Telemetry (Category distribution & Priority allocation charts)
    * Action Workspace for selected ticket:
      * Overview & live SLA countdown
      * Pause & Resume SLA clock
      * Reassign & escalate ticket to specialist teams
      * Update lifecycle states
      * Settle & resolve ticket (with > £250 Approver authorization check)
      * Live customer communication thread & internal agent notes
      * Customer CSAT (1-5) and NPS (0-10) post-resolution surveys
      * Full immutable event sourcing audit timeline

## How to Run

### Method 1: Served Directly via FastAPI Backend (Recommended)
Start the backend:
```bash
python -m uvicorn src.api:app --reload --host 127.0.0.1 --port 8000
```
Open in your browser:
**[http://localhost:8000/dashboard](http://localhost:8000/dashboard)** or **[http://localhost:8000/](http://localhost:8000/)**

### Method 2: Direct File / Live Server
Because CORS middleware is enabled on the backend, you can open `frontend/index.html` directly in your browser or with VS Code Live Server (`http://127.0.0.1:5500`). The frontend automatically detects the protocol and connects to `http://127.0.0.1:8000`.
