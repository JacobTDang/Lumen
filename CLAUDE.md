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
├── agent/              # LangChain classifier: user input → visualization schema
├── scenes/             # Manim scene classes, one file per pattern group
├── renderer/worker.py  # Thread pool + subprocess Manim runner, in-memory job state
├── schemas/types.py    # Pydantic models for each visualization type
├── tests/              # pytest, run with: pytest backend/tests/ -v
└── media/              # Rendered videos served at /media/<path> (gitignored)
```

## Dev setup

```bash
# Activate venv
.\venv\Scripts\Activate.ps1          # PowerShell
source venv/bin/activate             # Git Bash

# Install deps
pip install -r backend/requirements.txt

# Run tests (always before committing)
pytest backend/tests/ -v

# Run Flask dev server
cd backend && python app.py
```

## API

| Method | Route | Description |
|--------|-------|-------------|
| GET | `/health` | Liveness check |
| POST | `/render` | Submit render job — body: `{"scene": "...", "params": {...}}` → `{"job_id": "..."}` |
| GET | `/status/<job_id>` | Poll job — returns `{"status": "pending\|done\|error", "url": "...", "error": "..."}` |
| GET | `/media/<path>` | Serve rendered video file |

## Render flow

1. POST `/render` → `renderer/worker.py` spawns daemon thread, returns `job_id` immediately
2. Thread writes params to `media/temp/<job_id>.json`, calls `manim -ql` via subprocess
3. Scene reads params via `MANIM_JOB_ID` env var → `media/temp/<job_id>.json`
4. On completion, job state updates to `done` with video URL
5. Frontend polls `/status/<job_id>` until done, then renders `<video src={url} />`

## Scene types

Each scene class lives in `backend/scenes/` and reads its config from the temp JSON file.

| Scene key | File | Class | Covers |
|-----------|------|-------|--------|
| `bubble_sort` | `array_scene.py` | `BubbleSortScene` | Sorting visualization (render pipeline test) |
| `function_plot` | `calculus_scene.py` | `FunctionPlotScene` | General function graphing |
| `limit` | `calculus_scene.py` | `LimitScene` | One/two-sided limits, continuity, L'Hospital |
| `tangent_line` | `calculus_scene.py` | `TangentLineScene` | Derivative, tangent line, Newton's method |
| `riemann_sum` | `calculus_scene.py` | `RiemannSumScene` | Riemann sums → definite integral |
| `critical_points` | `calculus_scene.py` | `CriticalPointsScene` | Max/min, first/second derivative tests |

To add a new scene: implement the class, register it in `renderer/worker.py::SCENE_REGISTRY`.

## Environment variables

```
OPENROUTER_API_KEY=      # OpenRouter key for LangChain
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
OPENROUTER_MODEL=mistralai/mistral-7b-instruct:free
```

## Testing

- **Always run `pytest backend/tests/ -v` before committing**
- Unit tests mock subprocess and threading — no Manim install needed to run
- Integration tests (render pipeline) are marked slow and run separately

## Git workflow

Branch: `Jacob_MAMIN_Implementation`
Remote: `origin` → `https://github.com/JacobTDang/Annie.git`

```bash
# Stage and commit
git add backend/
git commit -m "short imperative description of what changed"

# Push to your branch
git push origin Jacob_MAMIN_Implementation
```

- Commit messages: short imperative subject line (e.g. `add RiemannSumScene`, `fix render output path`)
- No AI attribution in commits
- Always run tests before pushing
- Open a PR to `main` when a phase is complete
