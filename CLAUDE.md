# Annie — AI Calculus Visualization Tool

Hackathon project. Student accessibility theme. Backend renders Manim animations from natural language math questions and serves them to a React frontend.

## Stack

- **Backend:** Python 3.11, Flask, Manim, LangChain + OpenRouter
- **Frontend:** React 18, TypeScript (separate team)
- **Repo:** https://github.com/JacobTDang/Annie

## Project structure

```
backend/
├── app.py              # Flask entry point (application factory)
├── requirements.txt
├── .env                # secrets (gitignored) — see .env.example
├── agent/
│   └── classifier.py   # LangChain classifier: NL question → visualization schema
├── scenes/
│   ├── array_scene.py      # BubbleSortScene (render pipeline smoke test)
│   └── calculus_scene.py   # FunctionPlotScene, LimitScene, TangentLineScene,
│                           # RiemannSumScene, CriticalPointsScene
├── renderer/worker.py  # Thread pool + subprocess Manim runner, in-memory job state
├── schemas/types.py    # Pydantic models for each visualization type
├── tests/              # pytest — see Testing section
└── media/              # Rendered videos served at /media/<path> (gitignored)
```

## Dev setup

```bash
# Activate venv
.\venv\Scripts\Activate.ps1          # PowerShell
source venv/bin/activate             # Git Bash

# Install deps
pip install -r backend/requirements.txt

# Run fast unit tests (no Manim/API needed)
pytest backend/tests/ -v -m "not integration"

# Run full suite including renders + real API calls (slow)
pytest backend/tests/ -v -m integration

# Run Flask dev server
cd backend && python app.py
```

## API — Frontend contract

Base URL (dev): `http://localhost:5000`

### Primary endpoint — natural language question

```
POST /ask
Content-Type: application/json

{ "question": "show me the derivative of sin(x) at x = 1" }
```

Response `202`:
```json
{ "job_id": "uuid-string", "scene": "tangent_line" }
```

Response `400` — missing question:
```json
{ "error": "question is required" }
```

Response `422` — classifier failure:
```json
{ "error": "classification failed: <reason>" }
```

---

### Poll for render status

```
GET /status/<job_id>
```

Response while rendering:
```json
{ "status": "pending", "url": null, "error": null }
```

Response on success:
```json
{ "status": "done", "url": "/media/videos/calculus_scene/480p15/TangentLineScene.mp4", "error": null }
```

Response on failure:
```json
{ "status": "error", "url": null, "error": "description of what went wrong" }
```

---

### Serve video

```
GET /media/<path>          → video/mp4 stream
```

Use the `url` field from the status response directly as the `src` for a `<video>` tag.

---

### Direct render (bypass agent, for testing)

```
POST /render
{ "scene": "limit", "params": { "expression": "sin(x)/x", "limit_point": 0, "domain": [-5, 5] } }
```

Response `202`: `{ "job_id": "uuid-string" }`

---

### Health check

```
GET /health  →  { "status": "ok" }
```

---

## Typical frontend flow

```
1. User types question
2. POST /ask  →  receive job_id
3. Poll GET /status/<job_id> every 1–2s
4. When status === "done" → render <video src={url} autoPlay loop />
5. When status === "error" → show error message
```

Polling recommendation: 1-second interval, 90-second timeout, show a loading spinner.

---

## Scene types

| Scene key | Covers |
|-----------|--------|
| `function_plot` | General function graphing, evaluate at a point |
| `limit` | One/two-sided limits, continuity, L'Hospital's rule |
| `tangent_line` | Derivative, tangent line, secant → tangent animation |
| `riemann_sum` | Riemann sums animating toward definite integral |
| `critical_points` | Max/min, first/second derivative tests |

To add a new scene: implement the class in `scenes/`, register in `renderer/worker.py::SCENE_REGISTRY`.

## Environment variables

```
OPENROUTER_API_KEY=      # OpenRouter key
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
OPENROUTER_MODEL=nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free
```

## Testing

```
pytest backend/tests/ -v -m "not integration"   # fast, no external deps (~1s)
pytest backend/tests/ -v -m integration          # slow: real Manim + real API
```

| File | What it tests |
|------|--------------|
| `test_routes.py` | Flask route shapes and status codes |
| `test_renderer.py` | Worker job state, unknown scene handling |
| `test_classifier.py` | LLM classification (mocked + real API) |
| `test_calculus_scenes.py` | Each Manim scene actually renders |
| `test_integration.py` | Full pipeline: /ask → render → video on disk |

**Always run unit tests before committing.**

## Git workflow

Branch: `Jacob_MAMIN_Implementation`
Remote: `origin` → `https://github.com/JacobTDang/Annie.git`

```bash
git add backend/
git commit -m "short imperative description"
git push origin Jacob_MAMIN_Implementation
```

- Commit messages: short imperative subject line
- No AI attribution in commits
- Always run tests before pushing
- Open a PR to `main` when a phase is complete
