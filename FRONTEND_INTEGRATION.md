# Frontend Integration Guide (Async Jobs)

This backend uses **async jobs** for file-heavy endpoints. File uploads return a `job_id` immediately; the frontend polls `GET /jobs/{job_id}` until `status` is `completed` (or `failed`) and then uses `job.result`.

## Base URL
- Local: `http://localhost:8000`

## Worker Setup (Celery + Redis)
Start Redis:
```bash
redis-server
```

Start Celery worker (thread pool; avoids macOS fork issues):
```bash
celery -A jobs.celery_app.celery_app worker -P threads -c 4 -l info --without-gossip --without-mingle --without-heartbeat
```

Optional Redis URL override:
```bash
CELERY_REDIS_URL=redis://localhost:6379/0
```

## Job Model
### Create job (example response)
```json
{ "job_id": "4d6f...", "status": "pending" }
```

### Poll job
`GET /jobs/{job_id}`

Response:
```json
{
  "id": "4d6f...",
  "status": "pending|processing|completed|failed",
  "progress": "optional text",
  "result": {},
  "error": null
}
```

Frontend rules:
- If `status === "completed"` → use `result`
- If `status === "failed"` → show `error`
- Otherwise keep polling (with timeout + backoff)

---

## Pitch Deck (PDF) — Recommended Flow

### 1) Upload PDF for deck analysis (async)
`POST /analyze-pitch-deck` (multipart)
- Body: `file` (PDF)

Response:
```json
{ "job_id": "deck_job_id", "status": "pending" }
```

Poll `GET /jobs/deck_job_id` → when completed, `job.result` contains (example shape):
```json
{
  "summary": { "...": "..." },
  "scorecard": [{ "category": "Market", "score": 6, "justification": "..." }],
  "overall_score": 65,
  "claim_assumptions": { "...": "..." },
  "investor_simulation": { "...": "..." }
}
```

### 2) Market research (sync)
`POST /analyze-market-size` (JSON)
- Body: pass the best available overview (from deck summary or user input)

Response:
```json
{ "market_research": { "...": "..." } }
```

### 3) Final scoring (sync, combined)
`POST /score-startup` (JSON)
- Body:
```json
{
  "claim_assumptions": { "...": "..." },
  "market_research": { "...": "..." }
}
```

Response includes everything for scoring + verdict UI:
```json
{
  "claim_vs_reality": { "...": "..." },
  "investor_simulation": { "...": "..." },
  "skepticism_flags": [{ "statement": "...", "why_investors_doubt": "..." }],
  "final_verdict": { "status": "Not Investor Ready", "summary": "..." },
  "top_blockers": ["..."],
  "next_actions": ["..."],
  "likely_rejection": "..."
}
```

---

## Video Pitch (Video/Audio) — Recommended Flow

### 1) Upload video/audio (async)
`POST /analyze-video-pitch` (multipart)
- Body: `file` (mp4/mov/mp3/wav…)

Response:
```json
{ "job_id": "video_job_id", "status": "pending" }
```

Poll `GET /jobs/video_job_id` → `job.result` contains:
```json
{
  "transcript": "full transcript...",
  "analysis": {
    "summary": "...",
    "strengths": ["..."],
    "weaknesses": ["..."],
    "claim_assumptions": { "...": "..." },
    "investor_simulation": { "...": "..." },
    "investor_modes": { "...": "..." }
  }
}
```

### 2) Investor personas (optional, sync)
If you want personas without full video analysis:
`POST /investor-personas` (JSON)
```json
{ "transcript": "..." }
```

### 3) Market research (sync)
`POST /analyze-market-size` (JSON)
- Body: derived from transcript/claims (problem, target users, geography) or user form inputs

### 4) Final scoring (sync)
`POST /score-startup` (JSON)
```json
{
  "claim_assumptions": { "...": "..." },
  "market_research": { "...": "..." }
}
```

---

## Claims Only (File) — Optional Flow
If you want claims without full analysis:
1) `POST /extract-claims` (multipart) → returns `job_id`
2) Poll `GET /jobs/{job_id}` → use `job.result.claim_assumptions`
3) Then call `/analyze-market-size` → `/score-startup`

---

## UI Mapping (Quick)
- **What We Understood**: from deck job `result.summary` OR video job `result.analysis.summary`
- **Claim Confidence Map**: `claim_assumptions.evidence_present` + `claim_assumptions.claims`
- **Investor Personas**: video job `result.analysis.investor_modes` OR `POST /investor-personas`
- **Snapshot / Verdict / Scores / Fixes**: `POST /score-startup` response
- **Transcript (video only)**: video job `result.transcript`
